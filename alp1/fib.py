"""Fibonacci : provenance des ratios, loi nulle du retracement, zone OTE.

D'où viennent les nombres
-------------------------
La suite de Fibonacci ``1, 1, 2, 3, 5, 8, 13…`` a pour rapport limite le nombre
d'or ``φ = (1 + √5)/2 ≈ 1,618``. Les ratios tracés sur les graphiques en sont
des puissances ou des racines :

    0,618 = 1/φ          0,382 = 1/φ² = 1 − 0,618      0,236 = 1/φ³
    0,786 = √(1/φ)       0,886 = √0,786                1,618 = φ

Deux niveaux couramment tracés ne sont pas des ratios de Fibonacci :

    0,500 — la moitié. Elle vient de la théorie de Dow, qui observe que la
            tendance secondaire retrace du tiers aux deux tiers de la primaire.
    0,705 — moyenne de 0,618 et 0,786, à un millième près ``√0,5``. C'est une
            construction de praticien, sans généalogie mathématique.

La zone ``OTE`` (*Optimal Trade Entry*) désigne l'intervalle 0,618–0,79 du
retracement, où la pile ALP-1 place ses ordres limites.

Ce que ce module établit
------------------------
Aucune propriété du nombre d'or ne se transmet au prix : il n'existe aucun
mécanisme par lequel un rapport de suite entière contraindrait un carnet
d'ordres. Ce que la grille produit en revanche, et qui est réel, c'est un
**prix d'entrée meilleur, obtenu au prix de signaux non exécutés**. Cela n'est
pas une croyance, c'est un arbitrage chiffrable, et ce module le chiffre.

Sa conclusion a la même forme que celle de la remontée du stop, et c'est
frappant : sous un prix sans dérive, attendre un retracement **améliore**
l'espérance par signal — non parce que l'entrée est meilleure, mais parce que
les trades évités coûtaient chacun leur friction. Dès que la dérive dépasse un
seuil explicite, l'attente devient coûteuse, car les signaux manqués étaient
les bons. La grille de Fibonacci paie exactement quand le signal ne vaut rien.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .barriers import prob_target_before_stop

PHI = (1.0 + math.sqrt(5.0)) / 2.0

RATIOS: tuple[tuple[float, str], ...] = (
    (0.236, "1/φ³"),
    (0.382, "1/φ² = 1 − 0,618"),
    (0.500, "la moitié — origine Dow, pas Fibonacci"),
    (0.618, "1/φ"),
    (0.705, "moyenne de 0,618 et 0,79 ; ≈ √0,5"),
    (0.786, "√(1/φ)"),
    (0.886, "√0,786"),
)

OTE_LOW, OTE_HIGH = 0.618, 0.79


@dataclass(frozen=True)
class Leg:
    """Une impulsion : de `start` à `end`. Sa longueur sert d'unité."""

    start: float
    end: float

    @property
    def length(self) -> float:
        return abs(self.end - self.start)

    @property
    def is_up(self) -> bool:
        return self.end > self.start

    def level(self, ratio: float) -> float:
        """Niveau de retracement à la fraction donnée de l'impulsion."""
        return self.end - (self.end - self.start) * ratio

    def ote(self) -> tuple[float, float]:
        """Bornes de la zone OTE, ordonnées du bas vers le haut."""
        a, b = self.level(OTE_HIGH), self.level(OTE_LOW)
        return (min(a, b), max(a, b))


# --- Loi nulle du retracement -------------------------------------------------


def p_retrace_null(ratio: float, continuation: float = 0.10) -> float:
    """P(le prix retrace d'au moins `ratio` avant de prolonger de `continuation`).

    Après une impulsion de longueur ``R`` terminée en ``B``, on déclare la
    continuation acquise si le prix dépasse ``B + η·R``, et le retracement
    atteint s'il touche ``B − f·R``. Sous un prix sans dérive, c'est une ruine
    du joueur entre deux barrières distantes de ``f·R`` et ``η·R`` :

        P(retracement ≥ f) = η / (f + η).

    Le résultat ne dépend que du rapport des deux seuils — ni de la volatilité,
    ni de la durée, ni de l'échelle. Il fournit la fréquence exacte à laquelle
    un niveau de Fibonacci est « touché » sans qu'aucune information ne soit en
    jeu, c'est-à-dire la barre que doit franchir toute affirmation du type « le
    prix respecte le 0,618 ».

    Une conséquence utile : les niveaux profonds sont rarement atteints, et un
    taux de remplissage observé faible n'est donc pas en soi un défaut de la
    règle — c'est sa loi nulle.
    """
    if ratio <= 0 or continuation <= 0:
        raise ValueError("ratio et continuation doivent être > 0")
    return continuation / (ratio + continuation)


def p_retrace(ratio: float, continuation: float, leg_points: float,
              drift_per_min: float, sigma_per_min: float) -> float:
    """Même probabilité sous dérive constante, par premier passage à deux barrières.

    La dérive éloigne le prix de la zone : le taux de remplissage baisse
    exactement quand le signal fonctionne. C'est la première moitié de
    l'arbitrage que ce module chiffre.
    """
    if leg_points <= 0:
        raise ValueError("leg_points doit être > 0")
    return prob_target_before_stop(
        stop_distance=continuation * leg_points,
        target_distance=ratio * leg_points,
        drift_per_min=-drift_per_min,
        sigma_per_min=sigma_per_min,
    )


def expected_ote_fill(continuation: float = 0.10) -> float:
    """Taux de remplissage nul de la zone OTE complète, borne 0,618 touchée."""
    return p_retrace_null(OTE_LOW, continuation)


# --- Arbitrage d'exécution ----------------------------------------------------


@dataclass(frozen=True)
class ExecutionComparison:
    """Comparaison, par signal émis, entre entrée au marché et entrée en OTE."""

    fill_rate: float
    r_market: float
    r_ote: float
    expectancy_market: float
    expectancy_ote: float
    critical_drift: float

    @property
    def edge(self) -> float:
        """Écart d'espérance par signal, en points d'indice."""
        return self.expectancy_ote - self.expectancy_market


def breakeven_fill_rate(r_market: float, r_ote: float) -> float:
    """Taux de remplissage au-delà duquel l'entrée en OTE domine, en R affiché.

        q* = R_marché / R_OTE

    C'est la version naïve du critère, celle qui ne compare que des ratios
    affichés. Elle est instructive parce qu'elle est presque toujours exigeante :
    améliorer l'entrée de quelques points sur un target éloigné ne fait guère
    bouger le ratio, donc ``q*`` reste proche de 1, alors que la loi nulle
    n'offre qu'un remplissage de l'ordre de 15 %. Le critère juste est celui de
    `compare`, qui raisonne en espérance et non en ratio affiché.
    """
    if r_ote <= 0:
        raise ValueError("r_ote doit être > 0")
    return r_market / r_ote


def compare(leg_points: float, stop_points: float, target_points: float,
            friction_points: float, drift_per_min: float, sigma_per_min: float,
            exposure_market: float, exposure_ote: float,
            ratio: float = OTE_LOW, continuation: float = 0.10) -> ExecutionComparison:
    """Espérance par *signal émis* des deux modes d'entrée.

    Par l'identité de Wald, un trade rapporte ``µ·E[τ] − c``. Un signal exécuté
    au marché rapporte donc cette quantité ; un signal travaillé en OTE ne
    rapporte rien s'il n'est pas rempli, et rapporte ``µ·E[τ_OTE] − c`` sinon,
    avec une exposition plus longue puisque le target, fixé en niveau de prix,
    est plus éloigné de l'entrée :

        E_marché = µ·E[τ_m] − c
        E_OTE    = q·(µ·E[τ_o] − c)
        Δ        = µ·(q·E[τ_o] − E[τ_m]) + c·(1 − q).

    Deux lectures. En ``µ = 0``, ``Δ = c(1 − q) > 0`` : l'attente est payante,
    et pour une raison qui n'a rien à voir avec Fibonacci — chaque trade évité
    est une friction épargnée. Sous dérive croissante, le premier terme devient
    négatif et finit par l'emporter : les signaux manqués sont ceux qui
    partaient.
    """
    if min(leg_points, stop_points, target_points) <= 0:
        raise ValueError("distances doivent être > 0")
    q = p_retrace(ratio, continuation, leg_points, drift_per_min, sigma_per_min)
    gain = ratio * leg_points                       # amélioration du prix d'entrée
    r_market = target_points / stop_points
    r_ote = (target_points + gain) / stop_points

    e_market = drift_per_min * exposure_market - friction_points
    e_ote = q * (drift_per_min * exposure_ote - friction_points)

    denom = exposure_market - q * exposure_ote
    crit = friction_points * (1.0 - q) / denom if denom > 0 else math.inf

    return ExecutionComparison(
        fill_rate=q,
        r_market=r_market,
        r_ote=r_ote,
        expectancy_market=e_market,
        expectancy_ote=e_ote,
        critical_drift=crit,
    )


def slippage_saving(entry_slippage_ticks: float, tick_value: float,
                    point_value: float) -> float:
    """Friction épargnée par une entrée passive, en points d'indice.

    C'est le seul gain de la grille qui soit certain et immédiat : un ordre
    limite touché ne paie pas le spread à l'entrée. Sur ES, une demi-tick
    épargnée vaut 6,25 $ par contrat, soit 0,125 point — à comparer aux 0,33
    point de friction de référence. L'effet est du même ordre que celui que
    tout le reste du module discute, ce qui mérite d'être dit : la contribution
    mesurable de la couche Fibonacci est un gain d'exécution, pas une
    prédiction.
    """
    return entry_slippage_ticks * tick_value / point_value


def level_table(leg: Leg, continuation: float = 0.10) -> list[tuple[float, str, float, float]]:
    """(ratio, provenance, niveau de prix, probabilité nulle d'atteinte)."""
    return [(r, src, leg.level(r), p_retrace_null(r, continuation)) for r, src in RATIOS]
