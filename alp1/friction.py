"""La friction comme loi, et la marge qu'elle laisse.

Dans `alp1.costs`, la friction est un paramètre : on pose une commission, un
nombre de ticks de glissement, et on en déduit `c`. C'est suffisant pour poser
le critère maître, et insuffisant pour décider si un signal peut le franchir,
pour trois raisons.

**La friction n'est pas un nombre, c'est une loi.** La profondeur du carnet
varie d'une séance à l'autre dans un rapport de un à trois ; le glissement
payé sur un stop dépend du mouvement qui l'a déclenché. Une espérance de
friction ne dit rien du trade qui décide de l'année.

**Elle n'est pas exogène.** Le glissement de sortie est proportionnel à la
taille et inversement proportionnel à la profondeur : doubler la position ne
double pas seulement le risque, elle déplace le seuil que le signal doit
franchir. Il existe donc une taille au-delà de laquelle la stratégie n'a plus
d'espérance, et c'est une grandeur calculable.

**Elle n'est pas symétrique.** Une sortie à la clôture est un ordre au marché
programmé, exécuté dans un carnet normal. Une sortie au stop est un ordre au
marché déclenché *par* le mouvement qui traverse le carnet : la volatilité y
est élevée, la profondeur amincie, et le délai entre le déclenchement et
l'exécution se paie au prix du moment.

Ce module reconstruit `c` à partir de ces trois faits — commission publiée,
profondeur du carnet, latence, volatilité — au lieu de le poser, en donne la
loi complète, et répond à la seule question qui intéresse l'opérateur : de
combien la dérive documentée dépasse-t-elle la friction, non pas en moyenne,
mais au quantile où l'on perd.

Le contrôle de cohérence tient en une ligne : le glissement de sortie que ce
modèle **déduit** — latence, volatilité de déclenchement, profondeur — retombe
sur l'ordre de grandeur du tick unique que `alp1.costs` **posait**. Les deux
routes ne partagent aucun paramètre.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .costs import ES, Contract, _norm_ppf, norm_cdf
from .orderflow import impact_ticks

_SQRT_2_PI = math.sqrt(2.0 / math.pi)


# --- Le lieu d'exécution ----------------------------------------------------


@dataclass(frozen=True)
class Venue:
    """Ce qu'il faut savoir du carnet et du courtier pour déduire la friction.

    Attributes
    ----------
    contract:
        Le contrat, pour la valeur du point et le pas de cotation.
    commission_rt:
        Commission aller-retour, frais d'échange compris, en dollars.
    depth_median:
        Profondeur médiane au meilleur niveau, en contrats.
    depth_log_sd:
        Écart-type du logarithme de la profondeur d'une séance à l'autre. 0,5
        correspond à un rapport de un à trois entre les séances calmes et les
        séances tendues.
    thinning_at_stop:
        Fraction de la profondeur habituelle encore présente au moment où le
        stop se déclenche. Le stop part pendant le mouvement : le carnet du
        côté où l'on sort est, par construction, celui qui vient d'être
        consommé.
    latency_s:
        Délai entre le déclenchement et l'exécution, en secondes.
    trigger_vol_factor:
        Multiplicateur de volatilité pendant le déclenchement. Un stop ne part
        pas à un instant tiré au hasard de la séance : il part au moment d'un
        mouvement, et la volatilité conditionnelle y est supérieure.
    """

    contract: Contract = ES
    commission_rt: float = 4.00
    depth_median: float = 40.0
    depth_log_sd: float = 0.50
    thinning_at_stop: float = 0.35
    latency_s: float = 0.50
    trigger_vol_factor: float = 2.0

    def __post_init__(self) -> None:
        if self.depth_median <= 0 or self.depth_log_sd < 0:
            raise ValueError("profondeur > 0 et dispersion >= 0 requises")
        if not 0.0 < self.thinning_at_stop <= 1.0:
            raise ValueError("thinning_at_stop doit être dans ]0, 1]")
        if self.latency_s < 0 or self.trigger_vol_factor <= 0:
            raise ValueError("latence >= 0 et facteur de volatilité > 0 requis")

    @property
    def half_spread_points(self) -> float:
        """Demi-écart bid/ask, en points : un demi-tick sur un marché à un tick."""
        return 0.5 * self.contract.tick_size

    @property
    def commission_points(self) -> float:
        return self.commission_rt / self.contract.point_value


# Le lieu de référence : ES sur un courtier de détail, carnet ordinaire.
RETAIL_ES = Venue()


# --- La loi de la friction ---------------------------------------------------


@dataclass(frozen=True)
class FrictionLaw:
    """Loi de la friction aller-retour, en points d'indice.

    Trois briques, et une seule d'entre elles est déterministe :

        c = c₀ + K·e^{−νZ} + 1{sortie au stop}·s·|Y|

    - `c₀` : commission plus les deux demi-écarts, payés dans tous les cas ;
    - `K·e^{−νZ}` : impact de la taille, entrée et sortie, où `Z` est l'état de
      profondeur de la séance — une seule variable pour les deux jambes, parce
      que c'est le même carnet ;
    - `s·|Y|` : le déplacement subi pendant la latence, en valeur absolue, payé
      seulement sur les sorties au stop.

    La loi est donc un mélange, et son quantile haut n'est pas celui d'une
    gaussienne : il est porté par la conjonction d'un carnet mince et d'un
    déclenchement rapide, ce qui est exactement la conjonction qui se produit.
    """

    deterministic: float
    impact_scale: float
    depth_log_sd: float
    latency_scale: float
    p_stop_exit: float

    def _impact(self, z: float) -> float:
        return self.impact_scale * math.exp(-self.depth_log_sd * z)

    def _z_critical(self, x: float) -> float:
        """État de profondeur au-delà duquel l'impact seul dépasse déjà `x`.

        L'intégrande est nul en deçà et régulier au-delà : l'intégrale est
        donc découpée exactement à ce point plutôt que balayée à travers. Une
        quadrature de Simpson traversant une discontinuité converge en `h`, pas
        en `h⁴` — c'est la différence entre trois décimales et neuf.
        """
        slack = x - self.deterministic
        if self.impact_scale <= 0.0 or self.depth_log_sd <= 0.0:
            return -math.inf if slack >= self.impact_scale else math.inf
        if slack <= 0.0:
            return math.inf
        return -math.log(slack / self.impact_scale) / self.depth_log_sd

    def cdf(self, x: float, n_quad: int = 200, z_max: float = 8.0) -> float:
        """`P(c ≤ x)`, par quadrature de Simpson sur l'état de profondeur."""
        lo = max(self._z_critical(x), -z_max)
        if lo >= z_max:
            return 0.0
        n = n_quad if n_quad % 2 == 0 else n_quad + 1
        h = (z_max - lo) / n
        acc = 0.0
        for i in range(n + 1):
            z = lo + i * h
            w = 1.0 if i in (0, n) else (4.0 if i % 2 else 2.0)
            phi = math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
            slack = x - self.deterministic - self._impact(z)
            if slack < 0.0:
                p = 0.0
            elif self.latency_scale <= 0.0:
                p = 1.0
            else:
                # Demi-normale : P(|Y|·s ≤ slack) = 2Φ(slack/s) − 1.
                hn = 2.0 * norm_cdf(slack / self.latency_scale) - 1.0
                p = self.p_stop_exit * hn + (1.0 - self.p_stop_exit)
            acc += w * phi * p
        return min(1.0, max(0.0, acc * h / 3.0))

    def quantile(self, q: float, tol: float = 1e-9) -> float:
        """Quantile de la friction, par bissection sur la répartition."""
        if not 0.0 < q < 1.0:
            raise ValueError("q doit être dans ]0, 1[")
        lo = self.deterministic
        hi = self.deterministic + max(self.impact_scale, 1e-9) * 200.0 \
            + max(self.latency_scale, 1e-9) * 20.0
        for _ in range(300):
            mid = 0.5 * (lo + hi)
            if hi - lo <= tol:
                break
            if self.cdf(mid) < q:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    @property
    def mean(self) -> float:
        """`E[c]` en forme fermée.

        `E[e^{−νZ}] = e^{ν²/2}` pour la brique d'impact, `E[|Y|] = √(2/π)` pour
        la latence, pondérée par la probabilité de sortir au stop.
        """
        impact = self.impact_scale * math.exp(0.5 * self.depth_log_sd ** 2)
        latency = self.p_stop_exit * _SQRT_2_PI * self.latency_scale
        return self.deterministic + impact + latency

    def exceedance(self, x: float) -> float:
        """`P(c > x)` — la fréquence à laquelle la friction dépasse `x`."""
        return max(0.0, 1.0 - self.cdf(x))

    def components(self) -> list[tuple[str, float, str]]:
        """Décomposition de `E[c]` : nom, points, origine du chiffre."""
        impact = self.impact_scale * math.exp(0.5 * self.depth_log_sd ** 2)
        latency = self.p_stop_exit * _SQRT_2_PI * self.latency_scale
        return [
            ("Commission et demi-écarts", self.deterministic,
             "barème publié du courtier et pas de cotation"),
            ("Impact de la taille", impact,
             "taille rapportée à la profondeur du carnet, deux jambes"),
            ("Latence au déclenchement", latency,
             "volatilité conditionnelle × √latence, sur les seules sorties au stop"),
        ]


def friction_law(sigma_per_min: float, p_stop_exit: float,
                 size_contracts: float = 1.0,
                 venue: Venue = RETAIL_ES) -> FrictionLaw:
    """Construit la loi de friction à partir des observables du lieu.

    Le glissement de latence a pour échelle ``κ·σ₁·√(δ/60)`` : la volatilité
    par racine de minute, ramenée à la latence exprimée en minutes, multipliée
    par le facteur de volatilité conditionnelle au déclenchement. Aucun tick de
    glissement n'est posé — il est déduit, et l'on vérifie ensuite qu'il
    retombe sur l'ordre de grandeur que `alp1.costs` posait.
    """
    if sigma_per_min <= 0:
        raise ValueError("sigma_per_min doit être > 0")
    if not 0.0 <= p_stop_exit <= 1.0:
        raise ValueError("p_stop_exit doit être dans [0, 1]")
    c = venue.contract
    det = venue.commission_points + 2.0 * venue.half_spread_points
    impact_entry = impact_ticks(size_contracts, venue.depth_median) * c.tick_size
    impact_exit = (impact_ticks(size_contracts,
                                venue.depth_median * venue.thinning_at_stop)
                   * c.tick_size)
    latency = (venue.trigger_vol_factor * sigma_per_min
               * math.sqrt(venue.latency_s / 60.0))
    return FrictionLaw(
        deterministic=det,
        impact_scale=impact_entry + impact_exit,
        depth_log_sd=venue.depth_log_sd,
        latency_scale=latency,
        p_stop_exit=p_stop_exit,
    )


# --- La marge, au quantile où l'on perd -------------------------------------


@dataclass(frozen=True)
class Margin:
    """Marge de la dérive documentée sur la friction, à un quantile donné."""

    quantile: float
    friction: float
    edge_points: float
    stop_points: float

    @property
    def factor(self) -> float:
        return self.edge_points / self.friction if self.friction > 0 else math.inf

    @property
    def net_points(self) -> float:
        return self.edge_points - self.friction

    @property
    def c_over_l_pct(self) -> float:
        return 100.0 * self.friction / self.stop_points

    @property
    def survives(self) -> bool:
        return self.net_points > 0.0


def margins(law: FrictionLaw, edge_points: float, stop_points: float,
            quantiles: tuple[float, ...] = (0.50, 0.90, 0.99, 0.999)
            ) -> list[Margin]:
    """La marge à chaque quantile de la loi de friction, plus la moyenne."""
    out = [Margin(q, law.quantile(q), edge_points, stop_points) for q in quantiles]
    return out


def breakeven_friction(edge_points: float) -> float:
    """Friction qui annule exactement la dérive documentée."""
    return edge_points


def breakeven_exceedance(law: FrictionLaw, edge_points: float) -> float:
    """Fréquence des trades dont la seule friction efface la dérive espérée.

    C'est la lecture la plus directe de la marge : non pas « la friction vaut
    tant » mais « la friction dépasse la dérive une fois sur tant ». Elle est
    calculée sur la loi, pas sur son espérance.
    """
    return law.exceedance(edge_points)


# --- La taille, seule variable que l'opérateur contrôle ---------------------


def max_size_for_margin(sigma_per_min: float, p_stop_exit: float,
                        edge_points: float, target_factor: float = 3.0,
                        quantile: float = 0.99,
                        venue: Venue = RETAIL_ES,
                        hi: float = 5000.0, tol: float = 1e-6) -> float:
    """Taille maximale, en contrats, préservant une marge donnée au quantile.

    La friction croît linéairement en taille par l'impact ; la dérive captée,
    elle, est proportionnelle à la taille comme le résultat entier. Rapportée
    au contrat, la dérive est donc constante et la friction croissante : la
    marge décroît, et l'équation `dérive = facteur × friction(taille)` a une
    solution unique, obtenue ici par bissection.

    C'est la contrainte de capacité de la stratégie, et elle est bien plus
    contraignante que le capital : elle ne dépend pas de ce qu'on possède mais
    de ce que le carnet porte.

    Retourne 0 si la marge visée n'est atteinte à aucune taille, même
    infinitésimale : la friction incompressible — commission, écart, latence —
    suffit alors à la refuser. Ce n'est pas un cas d'école : au quantile 99 %,
    un facteur de trois n'est atteint par aucune taille.
    """
    def margin_factor(size: float) -> float:
        law = friction_law(sigma_per_min, p_stop_exit, size, venue)
        return edge_points / law.quantile(quantile)

    if margin_factor(tol) < target_factor:
        return 0.0
    lo, high = tol, hi
    if margin_factor(high) >= target_factor:
        return high
    for _ in range(80):
        mid = 0.5 * (lo + high)
        if high - lo <= tol:
            break
        if margin_factor(mid) >= target_factor:
            lo = mid
        else:
            high = mid
    return 0.5 * (lo + high)


def implied_exit_slippage_ticks(law: FrictionLaw, venue: Venue = RETAIL_ES) -> float:
    """Glissement de sortie déduit, en ticks — le contrôle de cohérence.

    `alp1.costs` **pose** un tick de glissement de sortie en scénario de
    référence et un tick et demi en scénario réaliste. Ce module le **déduit**
    de la latence, de la volatilité conditionnelle et de la profondeur. Les
    deux chemins ne partagent aucun paramètre : leur rencontre est une
    vérification, pas une convention.
    """
    slip_points = law.mean - law.deterministic + venue.half_spread_points
    return slip_points / venue.contract.tick_size


def main() -> None:
    from .costs import COST_BASE, COST_REALISTIC
    from .momentum import mean_abs_move, sigma_from_session, time_exit_outcome

    sigma = sigma_from_session(60.0, 390.0)
    stop = mean_abs_move(sigma, 90.0)
    out = time_exit_outcome(stop, 300.0, sigma)
    edge = 6.0 / 1e4 * 6000.0

    law = friction_law(sigma, out.p_stop, size_contracts=1.0)
    print(f"σ₁ = {sigma:.3f} pt, stop = {stop:.2f} pt, P(stop) = {out.p_stop:.3f}")
    print(f"\nFriction posée   : référence {COST_BASE.friction_points(ES):.3f} pt, "
          f"réaliste {COST_REALISTIC.friction_points(ES):.3f} pt")
    print(f"Friction déduite : moyenne {law.mean:.3f} pt, "
          f"médiane {law.quantile(0.5):.3f} pt")
    print(f"Glissement de sortie déduit : "
          f"{implied_exit_slippage_ticks(law):.2f} tick(s)")

    print("\nComposantes de E[c] :")
    for name, pts, origin in law.components():
        print(f"  {name:32s} {pts:.4f} pt  ({origin})")

    print(f"\nMarge sur une dérive de {edge:.2f} pt :")
    for m in margins(law, edge, stop):
        print(f"  quantile {m.quantile:6.3f} : c = {m.friction:.3f} pt, "
              f"c/L = {m.c_over_l_pct:.2f} %, net = {m.net_points:+.3f} pt, "
              f"facteur = {m.factor:.1f}×")
    print(f"\nP(friction > dérive) = {breakeven_exceedance(law, edge):.3e}")
    print("\nCapacité — taille maximale en contrats ES :")
    for q in (0.50, 0.90, 0.99):
        row = [max_size_for_margin(sigma, out.p_stop, edge, f, q)
               for f in (1.0, 2.0, 3.0)]
        print(f"  quantile {q:4.2f} : marge 1× {row[0]:7.1f}   "
              f"2× {row[1]:7.1f}   3× {row[2]:7.1f}")


if __name__ == "__main__":
    main()


# --- Les paramètres du lieu sont eux aussi posés ----------------------------


@dataclass(frozen=True)
class FrictionBox:
    """Encadrement de la friction sur la boîte des paramètres du carnet.

    Profondeur, amincissement, latence et volatilité de déclenchement ne sont
    pas mesurés dans ce dépôt : ils sont posés, à partir d'ordres de grandeur
    publics. Les traiter comme connus donnerait une friction faussement
    précise. Ils sont donc balayés, et c'est l'encadrement qui décide — la
    conclusion retenue n'est pas « la friction vaut 0,65 point » mais « aucune
    combinaison défendable des paramètres du carnet ne porte la friction au
    niveau de la dérive documentée ».
    """

    mean_lo: float
    mean_hi: float
    q99_lo: float
    q99_hi: float
    worst_margin: float
    edge_points: float
    n_eval: int
    worst_corner: str = ""

    @property
    def mean_margin(self) -> float:
        """Marge au pire coin, sur la friction **moyenne** de ce coin."""
        return self.edge_points / self.mean_hi if self.mean_hi > 0 else math.inf

    @property
    def survives(self) -> bool:
        """L'espérance du trade survit-elle partout dans la boîte ?

        C'est la question du critère maître, et elle porte sur `E[c]`, pas sur
        son quantile : l'espérance d'une série de trades se calcule avec la
        friction moyenne.
        """
        return self.mean_margin > 1.0

    @property
    def tail_survives(self) -> bool:
        """Le trade du quantile 99 % survit-il, au pire coin de la boîte ?

        Non, et c'est un résultat à conserver tel quel plutôt qu'à faire
        disparaître en resserrant la boîte. La conjonction — carnet le plus
        mince, amincissement maximal, latence la plus lente, volatilité de
        déclenchement la plus forte, **et** le centième trade le plus coûteux —
        porte la friction au niveau de la dérive documentée. Elle ne détruit
        pas l'espérance ; elle dit que la queue de la loi de friction, dans un
        carnet dégradé, mange un trade entier. C'est précisément le régime où
        la taille doit être réduite, et `max_size_for_margin` le chiffre.
        """
        return self.worst_margin > 1.0


def friction_box(sigma_per_min: float, p_stop_exit: float, edge_points: float,
                 size_contracts: float = 1.0,
                 depths: tuple[float, ...] = (15.0, 40.0, 100.0),
                 log_sds: tuple[float, ...] = (0.30, 0.50, 0.80),
                 thinnings: tuple[float, ...] = (0.15, 0.35, 0.70),
                 latencies: tuple[float, ...] = (0.10, 0.50, 1.50),
                 vol_factors: tuple[float, ...] = (1.5, 2.0, 3.0),
                 quantile: float = 0.99,
                 venue: Venue = RETAIL_ES) -> FrictionBox:
    """Balaye les paramètres du lieu et encadre la friction et la marge.

    `worst_margin` est le rapport dérive/friction au **pire** coin de la boîte
    et au quantile demandé : c'est le seul chiffre de ce module qu'on ait le
    droit de citer sans le qualifier, parce qu'il ne suppose ni un carnet
    favorable ni une exécution moyenne.
    """
    mean_lo, mean_hi = math.inf, -math.inf
    q_lo, q_hi = math.inf, -math.inf
    worst = ""
    count = 0
    for d in depths:
        for sd in log_sds:
            for th in thinnings:
                for lat in latencies:
                    for vf in vol_factors:
                        v = Venue(contract=venue.contract,
                                  commission_rt=venue.commission_rt,
                                  depth_median=d, depth_log_sd=sd,
                                  thinning_at_stop=th, latency_s=lat,
                                  trigger_vol_factor=vf)
                        law = friction_law(sigma_per_min, p_stop_exit,
                                           size_contracts, v)
                        m, q = law.mean, law.quantile(quantile)
                        mean_lo, mean_hi = min(mean_lo, m), max(mean_hi, m)
                        q_lo = min(q_lo, q)
                        if q > q_hi:
                            q_hi = q
                            worst = (f"profondeur {d:.0f}, dispersion {sd:.2f}, "
                                     f"amincissement {th:.2f}, latence {lat:.2f} s, "
                                     f"volatilité ×{vf:.1f}")
                        count += 1
    return FrictionBox(
        mean_lo=mean_lo, mean_hi=mean_hi, q99_lo=q_lo, q99_hi=q_hi,
        worst_margin=edge_points / q_hi if q_hi > 0 else math.inf,
        edge_points=edge_points, n_eval=count, worst_corner=worst,
    )
