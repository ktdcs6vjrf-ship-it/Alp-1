"""Décote post-publication de la dérive empruntée, et durée de vie résiduelle.

Ce module répond à une objection que le reste du document ne traite pas, et
qui est la plus sérieuse qu'un lecteur puisse opposer à sa conclusion.

La dérive retenue ici n'a pas été mesurée : elle est **empruntée** à des
travaux publiés — Gao, Han, Li et Zhou (2018) pour le momentum intraséance,
Baltussen, Da, Lammers et Martens (2021) pour sa généralisation. Or un effet
publié n'est pas un effet permanent. McLean et Pontiff (2016) mesurent sur 97
anomalies que le rendement se contracte d'environ **26 % hors échantillon mais
avant publication** — la part imputable au surajustement du travail
d'origine — et d'environ **58 % après publication** — la part imputable à
l'arbitrage des lecteurs. La seconde décote est l'objet de ce module.

Trois questions se posent alors, et elles sont distinctes.

**Que reste-t-il de la dérive aujourd'hui ?** La décote de McLean et Pontiff
est un niveau, pas un taux. La transformer en taux annuel exige une hypothèse
de forme ; on retient la décroissance exponentielle, la seule à un paramètre
qui soit compatible avec une décote mesurée sur une fenêtre. Le paramètre est
posé, encadré, et son point de rupture est calculé.

**À partir de quelle décote la conclusion tombe-t-elle ?** Le document donne
déjà le point de rupture de la dérive en points de base ; il suffit de le lire
comme une décote. C'est la forme la plus utile, parce qu'elle se compare
directement au 58 % publié.

**Quand la conclusion tombera-t-elle ?** Si l'effet décroît au taux retenu, la
date à laquelle il passe sous le point de rupture est calculable. Elle borne
la durée de vie de la stratégie, et c'est un nombre qu'un opérateur doit
connaître avant d'engager du capital, non après.

Une réserve est portée au même rang que le reste : Jacobs et Müller (2020) ne
retrouvent **aucune** décote post-publication hors des États-Unis, sur 39
marchés. La décote n'est donc pas une loi de la nature, et la borne basse de
la boîte retenue ici est zéro.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# --- Ce que la littérature documente ----------------------------------------

#: Décote hors échantillon, avant publication (McLean & Pontiff 2016, table 3).
#: Part du rendement perdue entre l'échantillon d'origine et la période qui le
#: suit immédiatement. S'interprète comme la mesure du surajustement du travail
#: d'origine, et non comme un effet d'arbitrage.
DECAY_OUT_OF_SAMPLE = 0.26

#: Décote post-publication (McLean & Pontiff 2016). Part supplémentaire perdue
#: après que l'effet a été publié. C'est la décote pertinente ici, puisque les
#: deux travaux sur lesquels s'appuie ce document sont publiés.
DECAY_POST_PUBLICATION = 0.58

#: Fenêtre sur laquelle la décote post-publication est mesurée, en années.
#: McLean et Pontiff comparent la période post-publication à l'échantillon
#: d'origine sans imposer d'horizon ; cinq ans est la durée médiane de leur
#: fenêtre post-publication, et c'est la valeur retenue pour convertir un
#: niveau en taux.
DECAY_WINDOW_YEARS = 5.0

#: Bornes de plausibilité du taux de décroissance annuel, en 1/an.
#: La borne basse est zéro : Jacobs et Müller (2020) ne trouvent aucune décote
#: post-publication hors des États-Unis. La borne haute correspond à la décote
#: de 58 % consommée en trois ans au lieu de cinq.
DECAY_RATE_LO = 0.0
DECAY_RATE_HI = -math.log(1.0 - DECAY_POST_PUBLICATION) / 3.0

#: Années de publication des deux travaux dont la dérive est tirée.
PUBLICATION_YEARS = {
    "Gao, Han, Li et Zhou (2018)": 2018,
    "Baltussen, Da, Lammers et Martens (2021)": 2021,
}


def decay_rate(level: float = DECAY_POST_PUBLICATION,
               window_years: float = DECAY_WINDOW_YEARS) -> float:
    """Taux annuel λ tel qu'une décroissance exponentielle perde `level` en `window_years`.

    De ``e^(−λ·W) = 1 − level`` on tire ``λ = −ln(1 − level)/W``. Une décote de
    58 % consommée en cinq ans donne λ ≈ 0,174 par an, soit une demi-vie de
    quatre ans environ.
    """
    if not 0.0 <= level < 1.0:
        raise ValueError("level doit être dans [0, 1[")
    if window_years <= 0:
        raise ValueError("window_years doit être > 0")
    return -math.log(1.0 - level) / window_years


def half_life(rate: float) -> float:
    """Demi-vie en années d'une décroissance de taux `rate`."""
    if rate <= 0:
        return math.inf
    return math.log(2.0) / rate


def surviving_fraction(years: float, rate: float | None = None) -> float:
    """Part de l'effet subsistant après `years` années de décroissance."""
    if rate is None:
        rate = decay_rate()
    if years < 0:
        raise ValueError("years doit être ≥ 0")
    return math.exp(-rate * years)


def surviving_edge(edge_bps: float, years: float,
                   rate: float | None = None) -> float:
    """Dérive subsistante après `years` années, en points de base."""
    return edge_bps * surviving_fraction(years, rate)


# --- Ce que la décote fait à la conclusion ----------------------------------


def breaking_decay(edge_bps: float, breaking_bps: float) -> float:
    """Décote qui amène la dérive publiée exactement à son point de rupture.

    Retourne une part dans [0, 1[. Se lit directement contre les 58 % publiés :
    une valeur supérieure signifie que la conclusion survit à la décote
    documentée, une valeur inférieure qu'elle n'y survit pas.
    """
    if edge_bps <= 0:
        raise ValueError("edge_bps doit être > 0")
    if breaking_bps <= 0:
        return 1.0
    if breaking_bps >= edge_bps:
        return 0.0
    return 1.0 - breaking_bps / edge_bps


def years_to_breaking(edge_bps: float, breaking_bps: float,
                      rate: float | None = None) -> float:
    """Années de décroissance avant que la dérive n'atteigne son point de rupture.

    C'est la durée de vie résiduelle de la conclusion sous l'hypothèse de
    décroissance retenue, comptée depuis la publication et non depuis
    aujourd'hui. `inf` si le taux est nul ou si le point de rupture est déjà
    au-dessus de la dérive publiée.
    """
    if rate is None:
        rate = decay_rate()
    if edge_bps <= 0 or breaking_bps <= 0:
        return math.inf
    if breaking_bps >= edge_bps:
        return 0.0
    if rate <= 0:
        return math.inf
    return math.log(edge_bps / breaking_bps) / rate


@dataclass(frozen=True)
class Runway:
    """Durée de vie résiduelle d'un effet publié, vue depuis une année donnée."""

    source: str
    published: int
    asof: int
    edge_bps: float
    breaking_bps: float
    rate: float

    @property
    def age(self) -> float:
        """Années écoulées depuis la publication."""
        return float(max(0, self.asof - self.published))

    @property
    def edge_today(self) -> float:
        """Dérive subsistante à la date d'observation, en points de base."""
        return surviving_edge(self.edge_bps, self.age, self.rate)

    @property
    def margin(self) -> float:
        """Rapport de la dérive subsistante à son point de rupture."""
        if self.breaking_bps <= 0:
            return math.inf
        return self.edge_today / self.breaking_bps

    @property
    def holds(self) -> bool:
        """La conclusion tient-elle encore à la date d'observation ?"""
        return self.edge_today > self.breaking_bps

    @property
    def expiry(self) -> float:
        """Année où la dérive passe sous le point de rupture."""
        y = years_to_breaking(self.edge_bps, self.breaking_bps, self.rate)
        return math.inf if y == math.inf else self.published + y

    @property
    def remaining(self) -> float:
        """Années restantes à la date d'observation. Négatif si déjà dépassé."""
        e = self.expiry
        return math.inf if e == math.inf else e - self.asof


def runways(edge_bps: float, breaking_bps: float, asof: int,
            rate: float | None = None) -> list[Runway]:
    """Durée de vie résiduelle, une entrée par travail source."""
    if rate is None:
        rate = decay_rate()
    return [Runway(src, yr, asof, edge_bps, breaking_bps, rate)
            for src, yr in sorted(PUBLICATION_YEARS.items(),
                                  key=lambda kv: kv[1])]


def breaking_rate(edge_bps: float, breaking_bps: float, age: float) -> float:
    """Taux annuel qui amène la dérive exactement à son point de rupture.

    À `age` années de décroissance, la dérive subsistante vaut le seuil pour
    ``λ = ln(edge/seuil)/age``. Au-delà de ce taux, la conclusion est déjà
    tombée à la date d'observation. Se lit contre la boîte de plausibilité :
    une valeur intérieure à la boîte signifie que la survie de la conclusion
    dépend du taux, et non plus seulement de la dérive publiée.
    """
    if age <= 0 or edge_bps <= 0 or breaking_bps <= 0:
        return math.inf
    if breaking_bps >= edge_bps:
        return 0.0
    return math.log(edge_bps / breaking_bps) / age


def rate_box() -> tuple[float, float, float]:
    """Encadrement du taux de décroissance : (bas, retenu, haut), en 1/an."""
    return DECAY_RATE_LO, decay_rate(), DECAY_RATE_HI


def scenario_grid(edge_bps: float, breaking_bps: float, asof: int,
                  published: int) -> list[tuple[float, float, float, bool]]:
    """Grille (taux, dérive subsistante, marge, tient) sur la boîte de taux.

    Cinq taux répartis entre les deux bornes de plausibilité, pour lire d'un
    coup d'œil sur quelle part de la boîte la conclusion survit.
    """
    lo, _, hi = rate_box()
    age = float(max(0, asof - published))
    out = []
    for i in range(5):
        r = lo + (hi - lo) * i / 4.0
        e = surviving_edge(edge_bps, age, r)
        m = e / breaking_bps if breaking_bps > 0 else math.inf
        out.append((r, e, m, e > breaking_bps))
    return out
