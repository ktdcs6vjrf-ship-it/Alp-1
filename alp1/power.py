"""Le protocole à horizon borné : puissance, information, séquentialité.

Un protocole de vérification a deux propriétés distinctes, et les confondre
est l'erreur qui rend les papiers de stratégie inutilisables. La première est
sa **validité** : la fréquence à laquelle il conclut à tort. La seconde est sa
**durée** : le temps de marché qu'il faut lui donner pour qu'il conclue tout
court. Le document précédent chiffrait la seconde sur le dispositif le plus
naïf qui soit — un marché, une entrée par séance, une moyenne non pondérée,
un seuil corrigé de Bonferroni, une décision unique en fin d'échantillon — et
en tirait dix à vingt-cinq années. Ce chiffre est exact pour ce dispositif. Il
n'est pas une propriété de la stratégie.

Ce module construit le dispositif qui atteint la même validité en cinq années
au plus. Il repose sur cinq leviers, et aucun d'eux ne touche à l'hypothèse
d'edge : la dérive supposée reste celle du document, ni relevée, ni réécrite.

  1. **La statistique porte sur la dérive par unité d'exposition**, pas sur la
     moyenne par trade. L'information sur `µ` est portée par le temps de
     marché cumulé `Στ`, non par le nombre de tickets ; deux trades de dix
     minutes ne valent pas un trade de vingt s'ils sont comptés comme deux
     observations d'une moyenne.

  2. **La pondération est celle des moindres carrés généralisés**, par la
     volatilité de séance estimée *avant* l'entrée. La volatilité d'une
     séance d'indice varie d'un facteur deux entre ses quantiles à 15 % et
     85 % ; une moyenne non pondérée paie cette dispersion en variance. Le
     gain est majoré exactement par `E[σ²]·E[1/σ²] = e^{4ν²}`, soit 1,63 à
     `ν = 0,35`, et le Monte-Carlo mesure ce qu'il en reste quand la
     volatilité est estimée et non connue.

  3. **La multiplicité est traitée en séquence fixée** plutôt que par
     Bonferroni. Trois configurations ordonnées d'avance, la deuxième examinée
     seulement si la première rejette : le taux d'erreur par famille reste
     `α` sans qu'aucune des trois ne perde de niveau. Le seuil de la
     configuration de référence redescend de `z_{1−α/3}` à `z_{1−α}`, ce qui
     retire trente pour cent de l'échantillon requis, gratuitement.

  4. **Le dispositif est un panel** : la même règle, scellée une fois, portée
     sur cinq contrats indiciels de trois fuseaux. Ce qui compte n'est pas le
     nombre de marchés mais leur corrélation de date à date, et c'est la
     variance groupée par date — non une hypothèse sur `ρ` — qui en décide.

  5. **La décision est séquentielle**, à quatre examens jalonnés en
     information et non en calendrier. Les frontières sont celles de la
     fonction de dépense d'O'Brien-Fleming, et la borne de futilité vient
     d'une dépense de `β` symétrique. La durée espérée tombe d'un tiers ; le
     maximum ne monte que de quelques pour cent.

Le point qui donne au dispositif sa validité est le jalonnement **en
information**. Les examens ne tombent pas à date fixe : ils tombent quand
`1/Var(µ̂)` franchit une fraction pré-enregistrée de l'information maximale.
La corrélation entre marchés, la cadence des entrées et la persistance de la
volatilité changent alors la *date* des examens, jamais leur niveau. Aucune
des cinq hypothèses de calibration n'entre donc dans le taux d'erreur du
protocole ; elles n'entrent que dans sa durée prévisible, et le Monte-Carlo
du module `alp1.mcprotocol` mesure les deux séparément.

Ce que le module ne fait pas : il ne rend aucune dérive plus détectable
qu'elle ne l'est. À information donnée, la dérive minimale détectable est une
identité, et elle est publiée — c'est le seul chiffre qui rende un échec du
protocole informatif.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache

from .costs import _norm_ppf, norm_cdf

# --- Constantes du dispositif ----------------------------------------------

#: Niveau du test, unilatéral, et puissance visée. Ils ne bougent pas : le but
#: du module est de réduire la durée à validité constante, et céder sur l'un
#: des deux serait exactement la triche que le reste du dépôt s'interdit.
ALPHA = 0.05
POWER = 0.80

#: Fractions d'information auxquelles la décision est examinée.
LOOKS: tuple[float, ...] = (0.25, 0.50, 0.75, 1.00)

#: Horizon calendaire maximal du protocole, en séances. Cinq années de bourse.
SESSIONS_PER_YEAR = 252
HORIZON_SESSIONS = 5 * SESSIONS_PER_YEAR

#: Budget d'information du protocole, en séances : quatre années et demie,
#: pour cinq années d'horizon. L'écart n'est pas une marge de confort mais une
#: nécessité de plan. L'information ne s'accumule pas à cadence fixe — une
#: année pauvre en cassures en apporte moins qu'une année riche —, et un
#: budget calé sur l'horizon exact laisserait une part des histoires atteindre
#: le plafond sans avoir atteint leur dernier examen : le protocole ne
#: conclurait pas, non parce que la dérive est absente, mais parce que le
#: calendrier a manqué. Un budget à 90 % de l'horizon ramène ce risque sous
#: trois pour cent, et le Monte-Carlo le mesure.
DESIGN_SESSIONS = 1134

#: Nombre minimal de séances avant le premier examen : une année pleine, pour
#: qu'aucune décision ne repose sur une seule saison.
MIN_SESSIONS_BEFORE_LOOK = SESSIONS_PER_YEAR


# --- Frontières de groupe séquentiel ---------------------------------------


def obf_spend(t: float, level: float) -> float:
    """Fonction de dépense d'O'Brien-Fleming, version Lan-DeMets.

    ``α*(t) = 2·(1 − Φ(z_{1−α/2}/√t))`` : presque rien n'est dépensé tôt, ce qui
    est la propriété qu'on cherche. Un protocole qui dépense son niveau au
    premier examen achète une réponse rapide au prix d'un seuil final si haut
    que l'échantillon complet ne le franchit plus.
    """
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return level
    z = _norm_ppf(1.0 - 0.5 * level)
    return min(level, 2.0 * (1.0 - norm_cdf(z / math.sqrt(t))))


@dataclass(frozen=True)
class Boundaries:
    """Frontières d'un plan séquentiel, sur l'échelle des `Z`.

    `efficacy` est la suite des seuils de rejet, `futility` celle des seuils
    d'abandon. `inflation` est le facteur par lequel l'information maximale
    dépasse celle d'un plan à décision unique — le prix du droit de regarder
    en cours de route.
    """

    fractions: tuple[float, ...]
    efficacy: tuple[float, ...]
    futility: tuple[float, ...]
    inflation: float
    power: float
    expected_fraction_h1: float
    expected_fraction_h0: float
    stop_probs_h1: tuple[float, ...]
    stop_probs_h0: tuple[float, ...]
    futility_probs_h1: tuple[float, ...]
    futility_probs_h0: tuple[float, ...]


# Grille de la récursion d'Armitage-McPherson-Rowe. Le pas est le seul réglage
# numérique du module ; il est vérifié dans les tests contre les frontières
# publiées d'O'Brien-Fleming.
_GRID_LO, _GRID_HI, _GRID_H = -9.0, 9.0, 0.02


def _grid(theta: float) -> tuple[list[float], float]:
    lo, hi = _GRID_LO, _GRID_HI + max(theta, 0.0)
    n = int(round((hi - lo) / _GRID_H))
    return [lo + i * _GRID_H for i in range(n + 1)], _GRID_H


def _normal_kernel(delta: float, drift: float, h: float) -> tuple[list[float], int]:
    """Noyau de transition ``N(drift·δ, δ)`` discrétisé, tronqué à 8 σ."""
    sd = math.sqrt(delta)
    reach = int(math.ceil(8.0 * sd / h))
    shift = drift * delta
    ker = []
    for k in range(-reach, reach + 1):
        z = (k * h - shift) / sd
        ker.append(math.exp(-0.5 * z * z) / (sd * math.sqrt(2.0 * math.pi)) * h)
    return ker, reach


def _propagate(dens: list[float], delta: float, drift: float,
               h: float) -> list[float]:
    """Convolue la sous-densité par le noyau de transition."""
    ker, reach = _normal_kernel(delta, drift, h)
    n = len(dens)
    out = [0.0] * n
    for i, w in enumerate(dens):
        if w <= 1e-18:
            continue
        lo = max(0, i - reach)
        hi = min(n - 1, i + reach)
        base = reach - i
        for j in range(lo, hi + 1):
            out[j] += w * ker[base + j]
    return out


def _initial(xs: list[float], t: float, drift: float, h: float) -> list[float]:
    sd = math.sqrt(t)
    mu = drift * t
    return [math.exp(-0.5 * ((x - mu) / sd) ** 2) / (sd * math.sqrt(2.0 * math.pi)) * h
            for x in xs]


def _upper_cut(xs: list[float], dens: list[float], mass: float) -> float:
    """Abscisse `b` telle que la masse au-delà vaille `mass`."""
    total = 0.0
    for i in range(len(xs) - 1, -1, -1):
        total += dens[i]
        if total >= mass:
            excess = total - mass
            frac = excess / dens[i] if dens[i] > 0 else 0.0
            return xs[i] + (frac - 0.5) * _GRID_H
    return xs[0]


def _lower_cut(xs: list[float], dens: list[float], mass: float) -> float:
    total = 0.0
    for i, w in enumerate(dens):
        total += w
        if total >= mass:
            excess = total - mass
            frac = excess / w if w > 0 else 0.0
            return xs[i] - (frac - 0.5) * _GRID_H
    return xs[-1]


def _run(fractions: tuple[float, ...], theta: float,
         eff_b: tuple[float, ...] | None,
         fut_b: tuple[float, ...] | None,
         alpha: float, beta: float,
         solve_eff: bool, solve_fut: bool):
    """Un passage de la récursion, sur l'échelle des `B` = `Z·√t`.

    Selon les drapeaux, résout les frontières au fil de l'eau ou se contente
    de les appliquer. Retourne ``(efficacité, futilité, sorties hautes,
    sorties basses)``.
    """
    xs, h = _grid(theta)
    dens = None
    eff: list[float] = []
    fut: list[float] = []
    up: list[float] = []
    dn: list[float] = []
    prev_t = 0.0
    for k, t in enumerate(fractions):
        delta = t - prev_t
        dens = (_initial(xs, t, theta, h) if dens is None
                else _propagate(dens, delta, theta, h))
        prev_t = t

        if solve_eff:
            want = obf_spend(t, alpha) - obf_spend(fractions[k - 1] if k else 0.0, alpha)
            b = _upper_cut(xs, dens, want)
        else:
            b = eff_b[k] * math.sqrt(t)
        if solve_fut:
            want_b = obf_spend(t, beta) - obf_spend(fractions[k - 1] if k else 0.0, beta)
            l = _lower_cut(xs, dens, want_b) if k < len(fractions) - 1 else b
        else:
            l = (fut_b[k] * math.sqrt(t)) if fut_b is not None else -1e9

        hi_mass = sum(w for x, w in zip(xs, dens) if x >= b)
        lo_mass = sum(w for x, w in zip(xs, dens) if x <= l)
        up.append(hi_mass)
        dn.append(lo_mass)
        eff.append(b / math.sqrt(t))
        fut.append(l / math.sqrt(t))
        dens = [0.0 if (x >= b or x <= l) else w for x, w in zip(xs, dens)]
    return tuple(eff), tuple(fut), tuple(up), tuple(dn)


@lru_cache(maxsize=None)
def boundaries(fractions: tuple[float, ...] = LOOKS, alpha: float = ALPHA,
               power: float = POWER) -> Boundaries:
    """Plan séquentiel complet : frontières, inflation, durée espérée.

    Les frontières d'efficacité sont résolues sous `θ = 0` **sans** borne
    inférieure : la futilité est donc non contraignante, et le niveau reste
    inférieur ou égal à `α` même si l'opérateur choisit de poursuivre après
    avoir franchi la borne d'abandon. C'est la convention prudente, et la
    seule qui laisse l'abandon au jugement sans abîmer l'inférence.
    """
    beta = 1.0 - power
    eff, _, _, _ = _run(fractions, 0.0, None, None, alpha, beta, True, False)

    def achieved(inflation: float):
        theta = (_norm_ppf(1.0 - alpha) + _norm_ppf(power)) * math.sqrt(inflation)
        _, fut, up, dn = _run(fractions, theta, eff, None, alpha, beta, False, True)
        return sum(up), fut, up, dn, theta

    lo, hi = 1.0, 1.60
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if achieved(mid)[0] < power:
            lo = mid
        else:
            hi = mid
    inflation = 0.5 * (lo + hi)
    pw, fut, up1, dn1, _ = achieved(inflation)
    _, _, up0, dn0 = _run(fractions, 0.0, eff, fut, alpha, beta, False, False)

    def expected(up, dn) -> float:
        stopped = 0.0
        acc = 0.0
        for t, u, d in zip(fractions, up, dn):
            acc += t * (u + d)
            stopped += u + d
        return acc + fractions[-1] * max(0.0, 1.0 - stopped)

    return Boundaries(
        fractions=fractions,
        efficacy=eff,
        futility=fut,
        inflation=inflation,
        power=pw,
        expected_fraction_h1=expected(up1, dn1),
        expected_fraction_h0=expected(up0, dn0),
        stop_probs_h1=up1,
        stop_probs_h0=up0,
        futility_probs_h1=dn1,
        futility_probs_h0=dn0,
    )


# --- Le panel : combien d'information une année de marché apporte ----------


@dataclass(frozen=True)
class Market:
    """Un contrat du panel, et sa place dans la structure de corrélation."""

    symbol: str
    name: str
    region: str
    session_min: float


#: Le panel scellé. Le critère de sélection est énoncé d'avance et ne laisse
#: aucune latitude : les cinq contrats indiciels les plus traités, un au plus
#: par indice, couvrant trois fuseaux. Il n'y a pas de choix à optimiser ici,
#: et c'est le but : un panel choisi après coup se choisirait sur ses
#: résultats.
PANEL: tuple[Market, ...] = (
    Market("ES", "S&P 500 (CME)", "US", 390.0),
    Market("NQ", "Nasdaq-100 (CME)", "US", 390.0),
    Market("FESX", "Euro Stoxx 50 (Eurex)", "EU", 510.0),
    Market("FDAX", "DAX (Eurex)", "EU", 510.0),
    Market("NK", "Nikkei 225 (OSE)", "JP", 300.0),
)

#: Corrélation des résultats de trade de même date, par paire de régions. Ce
#: sont des ordres de grandeur posés, non des mesures — et le protocole est
#: construit pour que sa validité n'en dépende pas : la variance est groupée
#: par date, donc estimée sur les données. Ils ne servent qu'à *prévoir* la
#: durée, et la sensibilité est balayée par le Monte-Carlo.
RHO_SAME_REGION = 0.80
RHO_CROSS_REGION = {("US", "EU"): 0.40, ("US", "JP"): 0.25, ("EU", "JP"): 0.30}

#: Corrélation entre deux entrées d'une même séance sur un même marché : elles
#: ne se chevauchent pas — la seconde n'ouvre qu'après la sortie de la
#: première — mais partagent la volatilité de la séance.
RHO_SAME_SESSION = 0.30

#: Écart-type du log de la volatilité de séance, repris de `alp1.microstructure`.
VOL_LOG_SD = 0.35

#: Entrées effectivement produites par séance et par marché, cadence de trois
#: autorisée. Ce n'est pas un réglage : c'est ce que la règle scellée produit
#: sur le marché simulé de `alp1.mcprotocol`, et un test vérifie que les deux
#: nombres ne divergent pas. La règle de ré-armement — le prix doit rentrer
#: dans la bande avant qu'une nouvelle cassure compte — explique l'écart au
#: plafond de trois.
ENTRIES_PER_SESSION = 1.113


def pair_correlation(a: Market, b: Market) -> float:
    if a.symbol == b.symbol:
        return RHO_SAME_SESSION
    if a.region == b.region:
        return RHO_SAME_REGION
    key = (a.region, b.region) if (a.region, b.region) in RHO_CROSS_REGION \
        else (b.region, a.region)
    return RHO_CROSS_REGION[key]


def gls_gain(nu: float = VOL_LOG_SD) -> float:
    """Majorant du gain d'information de la pondération GLS, ``e^{4ν²}``.

    Sous ``σ = σ̄·exp(νZ − ν²)``, on a ``E[σ²] = σ̄²`` et
    ``E[1/σ²] = σ̄⁻²e^{4ν²}`` ; le rapport des variances d'estimateur entre
    moyenne simple et moyenne pondérée par `1/σ²` vaut donc exactement
    ``E[σ²]·E[1/σ²] = e^{4ν²}``. C'est un **majorant** : il suppose la
    volatilité de séance connue, alors qu'elle est estimée sur les quatorze
    séances précédentes. Le Monte-Carlo mesure la part réellement obtenue.
    """
    return math.exp(4.0 * nu * nu)


@dataclass(frozen=True)
class PanelDesign:
    """Le dispositif de mesure, et l'information qu'il produit par année."""

    markets: tuple[Market, ...] = PANEL
    entries_per_session: float = ENTRIES_PER_SESSION
    sessions_per_year: int = SESSIONS_PER_YEAR
    gls: float = field(default_factory=gls_gain)

    @property
    def cluster_size(self) -> float:
        """Nombre de trades ouverts sur une même date, tous marchés confondus."""
        return len(self.markets) * self.entries_per_session

    @property
    def mean_correlation(self) -> float:
        """Corrélation moyenne des paires d'une même date.

        Les paires d'entrées d'un même marché comptent pour leur poids dans le
        cluster : c'est la moyenne qui entre dans la taille effective, pas la
        corrélation d'une paire particulière.
        """
        m, k = self.entries_per_session, len(self.markets)
        n = self.cluster_size
        if n <= 1.0:
            return 0.0
        same = k * m * (m - 1.0)
        acc = same * RHO_SAME_SESSION
        for i, a in enumerate(self.markets):
            for j, b in enumerate(self.markets):
                if i != j:
                    acc += m * m * pair_correlation(a, b)
        return acc / (n * (n - 1.0))

    @property
    def effective_trades_per_date(self) -> float:
        """Taille effective d'un cluster équicorrélé : ``n/(1 + (n−1)ρ̄)``."""
        n = self.cluster_size
        return n / (1.0 + (n - 1.0) * self.mean_correlation)

    def effective_trades(self, sessions: int) -> float:
        """Trades effectifs accumulés sur `sessions` dates, pondération comprise."""
        return sessions * self.effective_trades_per_date * self.gls

    def sessions_for(self, effective_trades: float) -> float:
        per = self.effective_trades_per_date * self.gls
        return effective_trades / per if per > 0 else math.inf

    def years_for(self, effective_trades: float) -> float:
        return self.sessions_for(effective_trades) / self.sessions_per_year


#: Le dispositif de référence : le panel complet, trois entrées autorisées par
#: séance dont 1,6 réalisées en moyenne — ce dernier nombre est **mesuré** par
#: le Monte-Carlo, pas posé.
DESIGN = PanelDesign()

#: Le repli à un seul marché, pour l'opérateur qui n'a qu'un historique ES.
SOLO = PanelDesign(markets=(PANEL[0],))

#: Le dispositif du document précédent : un marché, une entrée par séance,
#: aucune pondération, décision unique, seuil de Bonferroni.
NAIVE = PanelDesign(markets=(PANEL[0],), entries_per_session=1.0, gls=1.0)


# --- L'information, et le budget de cinq années -----------------------------


def information_per_date(design: PanelDesign, exposure_min: float,
                         sd_trade: float) -> float:
    """Information sur la dérive nette qu'une date de panel apporte.

    Un trade indépendant d'exposition `τ̄` et d'écart-type `σ_R` porte sur la
    dérive par minute une information ``τ̄²/σ_R²`` — c'est l'inverse de la
    variance qu'il laisse à l'estimateur. Une date en apporte autant de fois
    qu'elle contient de trades **effectifs**, corrélation et pondération
    comprises.

    La formule est une prévision, faite avant toute donnée et avant toute
    simulation de procédure. Le Monte-Carlo la confronte à l'information
    réellement accumulée par l'estimateur à variance groupée ; les deux
    coïncident à un pour cent, ce qui est le contrôle qui autorise à jalonner
    le protocole sur elle.
    """
    if sd_trade <= 0.0:
        raise ValueError("l'écart-type du trade doit être > 0")
    return (design.effective_trades_per_date * design.gls
            * (exposure_min / sd_trade) ** 2)


def max_information(design: PanelDesign, exposure_min: float, sd_trade: float,
                    sessions: int = DESIGN_SESSIONS) -> float:
    """Information maximale du protocole : celle que l'horizon peut fournir.

    C'est le sens exact du plafond de cinq années. Le protocole ne se donne
    pas une taille d'échantillon puis un calendrier : il se donne un budget de
    temps de marché, et en déduit ce qu'il pourra trancher.
    """
    return sessions * information_per_date(design, exposure_min, sd_trade)


#: Information maximale du protocole, scellée. En inverse de (point par
#: minute) au carré — l'unité de la dérive nette que le test principal borne.
#:
#: Le nombre n'est pas choisi : c'est ``DESIGN_SESSIONS × information_per_date``
#: évalué sur la géométrie scellée et sur le marché simulé de `alp1.mcprotocol`,
#: arrondi à la dizaine. Il est figé ici en toutes lettres pour une raison de
#: fond : un protocole dont la borne d'arrêt se recalculerait à chaque
#: exécution ne serait pas scellé. Un test vérifie qu'il n'a pas dérivé de plus
#: d'un pour cent par rapport à sa dérivation.
SEALED_MAX_INFORMATION = 54_130.0


def design_drift(i_max: float = SEALED_MAX_INFORMATION,
                 plan: Boundaries | None = None,
                 alpha: float = ALPHA, power: float = POWER) -> float:
    """Dérive nette par minute que le budget d'information détecte.

    ``θ₁ = (z_{1−α} + z_puissance)·√(inflation/I_max)``. Sous cette dérive, le
    protocole rejette avec la puissance visée ; en dessous, il ne conclut pas,
    et c'est ce nombre — publié — qui rend un échec informatif.
    """
    plan = plan or boundaries()
    if i_max <= 0.0:
        return math.inf
    return (_norm_ppf(1.0 - alpha) + _norm_ppf(power)) * math.sqrt(plan.inflation / i_max)


# --- Taille d'échantillon et dérive minimale détectable --------------------


def fixed_sample(sharpe_trade: float, alpha: float = ALPHA,
                 power: float = POWER, n_tests: int = 1) -> float:
    """Trades effectifs d'un plan à décision unique.

    ``N = ((z_{1−α/k} + z_{puissance})/SR)²``. `n_tests` vaut 1 en séquence
    fixée — c'est tout le gain de la séquence fixée — et le budget entier sous
    correction de Bonferroni.
    """
    if sharpe_trade <= 0.0:
        return math.inf
    z_a = _norm_ppf(1.0 - alpha / n_tests)
    z_b = _norm_ppf(power)
    return ((z_a + z_b) / sharpe_trade) ** 2


def detectable_sharpe(effective_trades: float, alpha: float = ALPHA,
                      power: float = POWER, n_tests: int = 1) -> float:
    """Sharpe par trade minimal détectable sur une information donnée."""
    if effective_trades <= 0.0:
        return math.inf
    z_a = _norm_ppf(1.0 - alpha / n_tests)
    z_b = _norm_ppf(power)
    return (z_a + z_b) / math.sqrt(effective_trades)


@dataclass(frozen=True)
class Horizon:
    """Ce que coûte, en temps de marché, une hypothèse de dérive donnée."""

    label: str
    edge_bps: float
    net_points: float
    sharpe_trade: float
    fixed_effective: float
    max_effective: float
    expected_effective: float
    years_fixed: float
    years_max: float
    years_expected: float
    decidable: bool


def horizon(design: PanelDesign, sharpe_trade: float, label: str = "",
            edge_bps: float = 0.0, net_points: float = 0.0,
            plan: Boundaries | None = None,
            cap_years: float = HORIZON_SESSIONS / SESSIONS_PER_YEAR) -> Horizon:
    """Durée d'un verdict sous une hypothèse d'edge, plan séquentiel compris."""
    plan = plan or boundaries()
    n_fixed = fixed_sample(sharpe_trade)
    n_max = n_fixed * plan.inflation
    n_exp = n_max * plan.expected_fraction_h1
    y_max = design.years_for(n_max)
    return Horizon(
        label=label,
        edge_bps=edge_bps,
        net_points=net_points,
        sharpe_trade=sharpe_trade,
        fixed_effective=n_fixed,
        max_effective=n_max,
        expected_effective=n_exp,
        years_fixed=design.years_for(n_fixed),
        years_max=y_max,
        years_expected=design.years_for(n_exp),
        decidable=y_max <= cap_years,
    )


def minimum_detectable_edge(design: PanelDesign, years: float, sd_trade: float,
                            exposure_min: float, friction: float,
                            index_level: float,
                            plan: Boundaries | None = None) -> dict[str, float]:
    """Dérive minimale détectable à l'horizon, en points et en points de base.

    Deux seuils, et ils ne répondent pas à la même question. Le premier porte
    sur l'**existence** — la dérive captée est-elle non nulle ? — et ignore la
    friction, qui est une constante connue déplaçant la moyenne. Le second
    porte sur la **viabilité** — la dérive nette est-elle positive ? — et
    supporte la friction en entier. Le second est toujours le plus exigeant,
    et c'est lui qui décide d'engager du capital.
    """
    plan = plan or boundaries()
    sessions = int(round(years * design.sessions_per_year))
    n_eff = design.effective_trades(sessions) / plan.inflation
    sr = detectable_sharpe(n_eff)
    gross_net = sr * sd_trade                    # dérive nette minimale, en points
    existence = gross_net                        # même bruit, friction connue
    viability = gross_net + friction
    return {
        "years": years,
        "effective_trades": n_eff,
        "sharpe": sr,
        "existence_points": existence,
        "existence_bps": 1e4 * existence / index_level,
        "existence_per_min": existence / exposure_min,
        "viability_points": viability,
        "viability_bps": 1e4 * viability / index_level,
        "viability_per_min": viability / exposure_min,
    }


# --- Le décompte des leviers ------------------------------------------------


@dataclass(frozen=True)
class Lever:
    """Un levier, son facteur sur la durée, et ce qu'il exige en échange."""

    name: str
    factor: float
    years_after: float
    assumption: str


def ledger(sharpe_trade: float, plan: Boundaries | None = None) -> list[Lever]:
    """Du dispositif naïf au dispositif borné, un levier à la fois.

    L'ordre est celui du coût en hypothèses, du plus gratuit au plus cher :
    on commence par ce qui ne suppose rien du marché, et on finit par ce qui
    en suppose le plus. Un lecteur qui refuse le dernier levier lit la durée
    à l'avant-dernière ligne, et ainsi de suite — c'est la raison d'être de la
    colonne des facteurs.
    """
    plan = plan or boundaries()
    naive_years = NAIVE.years_for(fixed_sample(sharpe_trade, n_tests=3))
    rows: list[Lever] = [Lever("Dispositif du document précédent", 1.0, naive_years,
                               "un marché, une entrée, Bonferroni, décision unique")]

    y = NAIVE.years_for(fixed_sample(sharpe_trade, n_tests=1))
    rows.append(Lever("Séquence fixée au lieu de Bonferroni", y / naive_years, y,
                      "un ordre de priorité déclaré avant les données ; "
                      "aucune hypothèse de marché"))

    gls_design = PanelDesign(markets=(PANEL[0],), entries_per_session=1.0)
    y2 = gls_design.years_for(fixed_sample(sharpe_trade))
    rows.append(Lever("Pondération GLS par la volatilité pré-entrée", y2 / y, y2,
                      "dérive constante en points par minute ; le gain est "
                      "majoré en forme fermée, et le réalisé est mesuré par "
                      "simulation"))

    solo = PanelDesign(markets=(PANEL[0],), entries_per_session=DESIGN.entries_per_session)
    y3 = solo.years_for(fixed_sample(sharpe_trade))
    rows.append(Lever("Cadence : jusqu'à trois entrées par séance", y3 / y2, y3,
                      "la dérive survit aux entrées de rang 2 et 3 ; "
                      "falsificateur de décroissance en rang"))

    y4 = DESIGN.years_for(fixed_sample(sharpe_trade))
    rows.append(Lever("Panel de cinq contrats, trois fuseaux", y4 / y3, y4,
                      "dérive commune au panel ; porte de non-homogénéité "
                      "avant lecture du test principal"))

    y5 = DESIGN.years_for(fixed_sample(sharpe_trade) * plan.inflation
                          * plan.expected_fraction_h1)
    inflation = f"{100 * (plan.inflation - 1):.1f}".replace(".", ",")
    rows.append(Lever("Décision séquentielle, quatre examens", y5 / y4, y5,
                      "aucune ; l'information maximale monte de "
                      + inflation + " % et la durée espérée baisse d'un tiers"))
    return rows


# --- Sortie texte -----------------------------------------------------------


def main() -> None:
    from . import report4

    report4.main()


if __name__ == "__main__":
    main()
