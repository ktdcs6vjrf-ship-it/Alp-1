"""Loi d'un trade et statistiques de trajectoire.

Ce module fournit le socle commun de tous les instruments de validation du
papier : une *loi de trade* explicite, en multiples du risque nominal `L`, sur
laquelle se calculent en forme fermée les ratios que les grands fonds
publient — Sharpe, Sortino, Calmar, Omega, Kelly, ratio de queue.

La loi n'est pas postulée. Elle est déduite de la distribution d'issues déjà
établie par `alp1.horizon` : deux atomes de barrière, plus une branche de
clôture de séance discrétisée en deux points qui reproduisent *exactement* sa
moyenne et sa variance conditionnelles. La loi obtenue a donc, sans dérive,
une moyenne de −`c/L` et une variance égale à `sd_gross²/L²` : c'est le
théorème d'invariance, transporté tel quel dans l'appareil de mesure.

Une dérive s'impose ensuite par *inclinaison exponentielle* (transformée
d'Esscher) : on repondère les atomes par `exp(θ·v)` et l'on résout `θ` pour
que la moyenne atteigne `µ·E[τ] − c`. C'est la déformation d'entropie
minimale qui produit la moyenne visée ; elle laisse le support inchangé, donc
la géométrie du trade inchangée, et ne présuppose rien de plus que le critère
maître de l'équation (6).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .costs import _norm_ppf, norm_cdf
from .horizon import HorizonOutcome

EULER_GAMMA = 0.5772156649015329


# --- La loi d'un trade ------------------------------------------------------


@dataclass(frozen=True)
class TradeLaw:
    """Loi discrète du résultat net d'un trade, en multiples du risque `L`.

    `values` sont les résultats possibles en R, `probs` leurs probabilités.
    Toutes les statistiques du module se calculent sur cette loi, de sorte
    qu'un ratio publié et un chiffre du texte ne peuvent pas diverger.
    """

    values: tuple[float, ...]
    probs: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.values) != len(self.probs):
            raise ValueError("values et probs doivent avoir la même longueur")
        if any(p < -1e-12 for p in self.probs):
            raise ValueError("probabilité négative")
        total = sum(self.probs)
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"les probabilités somment à {total}, pas à 1")

    # --- moments --------------------------------------------------------

    def moment(self, k: int, center: float = 0.0) -> float:
        return sum(p * (v - center) ** k for v, p in zip(self.values, self.probs))

    @property
    def mean(self) -> float:
        return self.moment(1)

    @property
    def variance(self) -> float:
        return max(0.0, self.moment(2, self.mean))

    @property
    def sd(self) -> float:
        return math.sqrt(self.variance)

    @property
    def skewness(self) -> float:
        s = self.sd
        return self.moment(3, self.mean) / s**3 if s > 0 else 0.0

    @property
    def excess_kurtosis(self) -> float:
        """Kurtosis en excès : 0 pour une gaussienne."""
        s = self.sd
        return self.moment(4, self.mean) / s**4 - 3.0 if s > 0 else 0.0

    # --- ratios de performance -----------------------------------------

    @property
    def sharpe_per_trade(self) -> float:
        """Sharpe par trade : `E[R]/σ[R]`. Sans unité, additif en racine."""
        s = self.sd
        return self.mean / s if s > 0 else 0.0

    def downside_deviation(self, mar: float = 0.0) -> float:
        """Écart-type des seules pertes sous le seuil `mar` (Sortino, 1991).

        `√E[min(R − mar, 0)²]`. Le dénominateur du ratio de Sortino ne divise
        pas par le nombre de dépassements mais par l'effectif total : c'est la
        semi-déviation *de la loi*, pas la dispersion des pertes seules.
        """
        return math.sqrt(sum(p * min(v - mar, 0.0) ** 2
                             for v, p in zip(self.values, self.probs)))

    def sortino(self, mar: float = 0.0) -> float:
        """Ratio de Sortino par trade : `(E[R] − mar)/DD(mar)`.

        Il ne pénalise que la dispersion à la baisse. Sur une loi à forte
        asymétrie négative — ce qu'est un trade à ratio 1:20, qui perd
        souvent peu et gagne rarement beaucoup —, il est *inférieur* au
        Sharpe, ce qui est l'inverse de l'intuition courante.
        """
        dd = self.downside_deviation(mar)
        return (self.mean - mar) / dd if dd > 0 else math.inf

    def omega(self, threshold: float = 0.0) -> float:
        """Ratio d'Omega (Keating & Shadwick, 2002) : gains sur pertes.

        `E[(R − θ)⁺] / E[(θ − R)⁻]`. Il utilise la loi entière et non ses
        deux premiers moments ; `Ω(θ) > 1` équivaut à `E[R] > θ`.
        """
        up = sum(p * max(v - threshold, 0.0) for v, p in zip(self.values, self.probs))
        dn = sum(p * max(threshold - v, 0.0) for v, p in zip(self.values, self.probs))
        return up / dn if dn > 0 else math.inf

    @property
    def gain_to_pain(self) -> float:
        """Somme des gains rapportée à la somme des pertes, en valeur absolue."""
        return self.omega(0.0)

    def tail_ratio(self, q: float = 0.05) -> float:
        """Quantile haut sur quantile bas, en valeur absolue.

        Mesure d'asymétrie des queues indépendante de la variance ; > 1
        signale une loi à droite longue, ce qu'un ratio gain/risque élevé
        produit mécaniquement.
        """
        hi, lo = self.quantile(1.0 - q), self.quantile(q)
        return abs(hi) / abs(lo) if lo != 0 else math.inf

    def quantile(self, q: float) -> float:
        """Quantile inférieur de la loi discrète."""
        if not 0.0 <= q <= 1.0:
            raise ValueError("q doit être dans [0, 1]")
        acc = 0.0
        for v, p in sorted(zip(self.values, self.probs)):
            acc += p
            if acc >= q - 1e-12:
                return v
        return max(self.values)

    @property
    def prob_win(self) -> float:
        return sum(p for v, p in zip(self.values, self.probs) if v > 0)

    # --- dimensionnement ------------------------------------------------

    def kelly_fraction(self, max_iter: int = 200, tol: float = 1e-12) -> float:
        """Fraction de Kelly : `f*` maximisant `E[ln(1 + f·R)]`.

        Résolue par bissection sur `g(f) = E[R/(1 + f·R)]`, décroissante en
        `f`. Bornée par la ruine : `f < 1/|R_min|`. Retourne 0 si la loi est
        d'espérance négative — aucune fraction positive ne fait croître le
        capital, ce qui est la lecture correcte d'un edge absent.
        """
        if self.mean <= 0:
            return 0.0
        worst = min(self.values)
        if worst >= 0:
            return math.inf
        lo, hi = 0.0, 1.0 / abs(worst) * (1.0 - 1e-9)

        def g(f: float) -> float:
            return sum(p * v / (1.0 + f * v) for v, p in zip(self.values, self.probs))

        if g(hi) > 0:
            return hi
        for _ in range(max_iter):
            mid = 0.5 * (lo + hi)
            if g(mid) > 0:
                lo = mid
            else:
                hi = mid
            if hi - lo < tol:
                break
        return 0.5 * (lo + hi)

    def growth_rate(self, fraction: float) -> float:
        """Taux de croissance logarithmique par trade à mise fractionnaire."""
        return sum(p * math.log(1.0 + fraction * v)
                   for v, p in zip(self.values, self.probs)
                   if 1.0 + fraction * v > 0)

    # --- transformations -------------------------------------------------

    def shifted(self, delta: float) -> "TradeLaw":
        """Translation de tous les résultats — sert à changer la friction."""
        return TradeLaw(tuple(v + delta for v in self.values), self.probs)

    def tilted_to_mean(self, target: float, tol: float = 1e-13,
                       max_iter: int = 400) -> "TradeLaw":
        """Inclinaison exponentielle vers une moyenne visée (Esscher).

        `p_i ∝ p_i·exp(θ·v_i)`, `θ` résolu pour que `E[R] = target`. La
        moyenne inclinée est strictement croissante en `θ`, la racine est
        donc unique dans l'intervalle ouvert des valeurs extrêmes du support.
        C'est la repondération d'entropie relative minimale sous contrainte
        de moyenne : elle ajoute exactement l'information « la moyenne vaut
        `target` », et rien d'autre.
        """
        lo_v, hi_v = min(self.values), max(self.values)
        if not lo_v < target < hi_v:
            raise ValueError("moyenne visée hors du support de la loi")

        def mean_at(theta: float) -> float:
            m = max(theta * v for v in self.values)
            w = [p * math.exp(theta * v - m) for v, p in zip(self.values, self.probs)]
            z = sum(w)
            return sum(wi * v for wi, v in zip(w, self.values)) / z

        lo, hi = -1.0, 1.0
        for _ in range(200):
            if mean_at(lo) <= target:
                break
            lo *= 2.0
        for _ in range(200):
            if mean_at(hi) >= target:
                break
            hi *= 2.0
        for _ in range(max_iter):
            mid = 0.5 * (lo + hi)
            if mean_at(mid) < target:
                lo = mid
            else:
                hi = mid
            if hi - lo < tol * max(1.0, abs(hi)):
                break
        theta = 0.5 * (lo + hi)
        m = max(theta * v for v in self.values)
        w = [p * math.exp(theta * v - m) for v, p in zip(self.values, self.probs)]
        z = sum(w)
        return TradeLaw(self.values, tuple(wi / z for wi in w))


def law_from_outcome(
    out: HorizonOutcome,
    stop_points: float,
    target_points: float,
    friction_points: float,
) -> TradeLaw:
    """Loi du trade en R, déduite de la distribution d'issues sous martingale.

    Quatre atomes : target touché, stop touché, et deux points pour la branche
    de clôture de séance, placés en `µ_o ± σ_o` avec poids égaux. Cette
    discrétisation à deux points reproduit *exactement* la moyenne et la
    variance conditionnelles de la branche ouverte ; la loi obtenue a donc les
    deux premiers moments exacts de `X_{τ∧T}`, et non une approximation.

    La friction est retranchée à tous les atomes : elle est certaine, c'est la
    seule quantité du modèle qui ne dépende d'aucune issue.
    """
    a, b, c = stop_points, target_points, friction_points
    if a <= 0 or b <= 0:
        raise ValueError("stop et target doivent être > 0")
    p_t, p_s, p_o = out.p_target, out.p_stop, out.p_open

    values = [(b - c) / a, (-a - c) / a]
    probs = [p_t, p_s]

    if p_o > 1e-12:
        mu_o = out.mean_open / p_o
        second_total = out.sd_gross**2 + out.mean_gross**2
        second_open = second_total - p_t * b**2 - p_s * a**2
        var_o = max(0.0, second_open / p_o - mu_o**2)
        sd_o = math.sqrt(var_o)
        for sign in (+1.0, -1.0):
            values.append((mu_o + sign * sd_o - c) / a)
            probs.append(p_o / 2.0)

    total = sum(probs)
    return TradeLaw(tuple(values), tuple(p / total for p in probs))


# --- Agrégation temporelle --------------------------------------------------


def annualise(sharpe_per_trade: float, trades_per_year: float) -> float:
    """Sharpe annualisé : `SR₁·√N`. Valable si les trades sont indépendants."""
    return sharpe_per_trade * math.sqrt(max(trades_per_year, 0.0))


def lo_adjustment(rho: float, q: int) -> float:
    """Facteur d'annualisation corrigé de l'autocorrélation (Lo, 2002).

    Sous un AR(1) de coefficient `ρ`, agréger `q` périodes ne multiplie pas
    le Sharpe par `√q` mais par

        q / √(q + 2·Σ_{k=1}^{q−1} (q − k)·ρᵏ).

    Une autocorrélation positive — celle que produit toute stratégie dont les
    positions se chevauchent ou dont les gains sont lissés — **gonfle** le
    Sharpe annualisé publié. À `ρ = 0,2` et `q = 252`, le facteur naïf `√q`
    surestime le Sharpe d'environ un cinquième.
    """
    if q < 1:
        raise ValueError("q doit être >= 1")
    if abs(rho) >= 1.0:
        raise ValueError("rho doit être dans ]−1, 1[")
    s = sum((q - k) * rho**k for k in range(1, q))
    denom = math.sqrt(q + 2.0 * s)
    return q / denom if denom > 0 else 0.0


def _psr_variance(sharpe_hat: float, skew: float, excess_kurtosis: float) -> float:
    """Variance asymptotique de l'estimateur de Sharpe, en unités de 1/(n−1).

    `1 − γ₃·ŜR + ((γ₄ − 1)/4)·ŜR²`, où `γ₄` est le kurtosis **non centré**
    (3 pour une gaussienne). Sous gaussienne et Sharpe nul elle vaut 1 : le
    Sharpe estimé a alors l'écart-type `1/√(n − 1)`, ce que retrouve le test
    de Student.
    """
    kurtosis = excess_kurtosis + 3.0
    return 1.0 - skew * sharpe_hat + 0.25 * (kurtosis - 1.0) * sharpe_hat**2


def probabilistic_sharpe(
    sharpe_hat: float,
    n_obs: int,
    benchmark: float = 0.0,
    skew: float = 0.0,
    excess_kurtosis: float = 0.0,
) -> float:
    """Probabilistic Sharpe Ratio (Bailey & López de Prado, 2012).

    Probabilité que le Sharpe vrai dépasse `benchmark`, sachant un Sharpe
    estimé `sharpe_hat` sur `n_obs` observations d'une loi asymétrique et
    leptokurtique :

        PSR = Φ( (ŜR − SR*)·√(n − 1) / √(1 − γ₃·ŜR + ((γ₄ − 1)/4)·ŜR²) )

    Tous les Sharpe sont exprimés **par observation**, jamais annualisés :
    l'annualisation est une convention d'affichage, pas une information.
    L'asymétrie négative et les queues épaisses réduisent la probabilité à
    Sharpe estimé égal — c'est le seul terme du papier qui pénalise
    explicitement la forme de la loi.
    """
    if n_obs < 2:
        return 0.0
    var = _psr_variance(sharpe_hat, skew, excess_kurtosis)
    if var <= 0:
        return 1.0 if sharpe_hat > benchmark else 0.0
    z = (sharpe_hat - benchmark) * math.sqrt(n_obs - 1) / math.sqrt(var)
    return norm_cdf(z)


def min_track_record_length(
    sharpe_hat: float,
    benchmark: float = 0.0,
    skew: float = 0.0,
    excess_kurtosis: float = 0.0,
    confidence: float = 0.95,
) -> float:
    """Longueur minimale d'historique (MinTRL, Bailey & López de Prado).

        MinTRL = 1 + (1 − γ₃·ŜR + ((γ₄ − 1)/4)·ŜR²)·(z_α / (ŜR − SR*))²

    Nombre d'observations en deçà duquel un Sharpe de `sharpe_hat` ne peut
    pas être déclaré supérieur à `benchmark` au niveau `confidence`. C'est la
    forme correcte de la question « combien de trades faut-il ? » : elle tient
    compte de la forme de la loi, ce que le test de Student ne fait pas.
    """
    if sharpe_hat <= benchmark:
        return math.inf
    z = _norm_ppf(confidence)
    var = _psr_variance(sharpe_hat, skew, excess_kurtosis)
    return 1.0 + max(0.0, var) * (z / (sharpe_hat - benchmark)) ** 2
