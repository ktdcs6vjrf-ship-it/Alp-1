"""Le TPO, ou profil de marché : le temps comme axe, et non le volume.

Un profil de volume compte les contrats échangés à chaque prix. Un profil
TPO — *Time Price Opportunity* — compte les **périodes** pendant lesquelles
le prix a visité chaque niveau. La séance est découpée en tranches de trente
minutes, chacune reçoit une lettre, et la lettre est imprimée à tous les prix
que la tranche a traversés. Le graphique qui en résulte est un histogramme
couché, et son vocabulaire est ancien : Steidlmayer l'a publié en 1984 pour
le Chicago Board of Trade.

Ce que la lecture prétend
-------------------------
**Le POC** est le prix le plus longtemps visité. **L'aire de valeur** est la
tranche de prix contenant soixante-dix pour cent des TPO autour du POC —
soixante-dix parce qu'une gaussienne y met un écart-type, et pour aucune
autre raison. **Un tirage simple** est un prix qu'une seule période a
touché : le marché y est passé sans s'y arrêter. **Un extrême pauvre** est
un haut ou un bas où deux périodes au moins ont imprimé, donc sans mèche —
la lecture d'usage dit qu'il sera revisité. **L'extension de séance** est le
dépassement de la fourchette des deux premières périodes, la *balance
initiale*.

Ce que ce module en fait
------------------------
Chacune de ces cinq lectures reçoit sa loi nulle, simulée sous un prix sans
dérive à graine déclarée. Le résultat est celui qu'on attendait de ce dépôt :
**aucune des cinq n'est rare**. Une séance sans aucune intention produit des
tirages simples, un extrême pauvre une fois sur deux ou trois, et étend sa
balance initiale presque toujours. Ce ne sont donc pas des événements, ce
sont des propriétés d'une marche aléatoire découpée en tranches.

Cela ne les rend pas inutiles — un vocabulaire qui décrit la forme d'une
séance a sa valeur — mais cela interdit de les traiter comme des signaux
sans mesurer d'abord de combien leur fréquence observée dépasse celle-ci.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from .mc import Rng

#: Découpage de séance, en minutes. Trente est la convention de Steidlmayer,
#: reprise par toutes les plateformes ; elle est déclarée ici pour que la loi
#: nulle porte sur le même découpage que la lecture.
PERIOD_MIN = 30.0

#: Part des TPO que l'aire de valeur contient. Soixante-dix pour cent parce
#: qu'une gaussienne y met un écart-type — c'est la seule justification, et
#: elle ne survit pas à une distribution non gaussienne.
VALUE_AREA = 0.70

#: Lettres des périodes, dans l'ordre. Une séance de 390 minutes en compte
#: treize à trente minutes.
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@dataclass(frozen=True)
class Profile:
    """Un profil TPO : pour chaque niveau, les périodes qui l'ont visité."""

    prices: tuple[float, ...]           # du bas vers le haut
    periods: tuple[frozenset[int], ...]  # index de période par niveau
    n_periods: int
    tick: float

    @property
    def counts(self) -> tuple[int, ...]:
        return tuple(len(p) for p in self.periods)

    @property
    def total(self) -> int:
        return sum(self.counts)

    @property
    def poc(self) -> float:
        """Le prix le plus longtemps visité, le plus proche du milieu à égalité."""
        milieu = 0.5 * (self.prices[0] + self.prices[-1])
        return max(zip(self.counts, self.prices),
                   key=lambda cp: (cp[0], -abs(cp[1] - milieu)))[1]

    @property
    def single_prints(self) -> tuple[float, ...]:
        """Les prix qu'une seule période a touchés."""
        return tuple(p for p, c in zip(self.prices, self.counts) if c == 1)

    @property
    def poor_high(self) -> bool:
        """Deux périodes au moins ont imprimé au plus haut : pas de mèche."""
        return self.counts[-1] >= 2

    @property
    def poor_low(self) -> bool:
        return self.counts[0] >= 2

    def value_area(self, part: float = VALUE_AREA) -> tuple[float, float]:
        """L'aire de valeur, construite par extension alternée depuis le POC.

        La règle d'usage compare les deux niveaux voisins **par paires** et
        retient la paire la plus fournie. Elle est reprise telle quelle, y
        compris son arbitraire : une aire de valeur n'est pas un quantile, et
        deux plateformes qui l'implémentent différemment publient des bornes
        différentes sans qu'aucune se trompe.
        """
        cible = part * self.total
        i = self.prices.index(self.poc)
        bas = haut = i
        acquis = self.counts[i]
        while acquis < cible and (bas > 0 or haut < len(self.prices) - 1):
            sous = (self.counts[bas - 1] + (self.counts[bas - 2] if bas > 1 else 0)
                    if bas > 0 else -1)
            sur = (self.counts[haut + 1]
                   + (self.counts[haut + 2] if haut < len(self.prices) - 2 else 0)
                   if haut < len(self.prices) - 1 else -1)
            if sur >= sous:
                haut = min(haut + 2, len(self.prices) - 1)
                acquis = sum(self.counts[bas:haut + 1])
            else:
                bas = max(bas - 2, 0)
                acquis = sum(self.counts[bas:haut + 1])
        return self.prices[bas], self.prices[haut]

    def initial_balance(self) -> tuple[float, float]:
        """La fourchette des deux premières périodes."""
        niveaux = [p for p, s in zip(self.prices, self.periods)
                   if s & {0, 1}]
        return (min(niveaux), max(niveaux)) if niveaux else (self.prices[0],
                                                             self.prices[-1])

    def range_extension(self) -> tuple[bool, bool]:
        """La séance a-t-elle dépassé sa balance initiale, en haut, en bas ?"""
        bas, haut = self.initial_balance()
        return self.prices[-1] > haut, self.prices[0] < bas


def from_path(path: list[float] | tuple[float, ...], n_periods: int,
              tick: float = 0.25) -> Profile:
    """Construit le profil d'une trajectoire découpée en `n_periods` tranches.

    Chaque tranche imprime à tous les niveaux qu'elle a traversés, bornes
    comprises — c'est ce que fait une plateforme, et c'est ce qui rend le TPO
    sensible à la granularité du tick autant qu'au prix lui-même.
    """
    n = len(path)
    taille = max(n // n_periods, 1)
    niveaux: dict[int, set[int]] = {}
    for k in range(n_periods):
        seg = path[k * taille: (k + 1) * taille if k + 1 < n_periods else n]
        if not seg:
            continue
        lo = int(math.floor(min(seg) / tick))
        hi = int(math.floor(max(seg) / tick))
        for idx in range(lo, hi + 1):
            niveaux.setdefault(idx, set()).add(k)
    cles = sorted(niveaux)
    return Profile(tuple(k * tick for k in cles),
                   tuple(frozenset(niveaux[k]) for k in cles),
                   n_periods, tick)


# ---------------------------------------------------------------------------
# Les lois nulles des cinq lectures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NullProfile:
    """Ce qu'une séance sans dérive produit, sur chacune des cinq lectures."""

    singles_mean: float
    singles_q95: float
    p_poor_high: float
    p_poor_low: float
    p_extension: float
    value_width_mean: float      # aire de valeur / étendue de séance
    draws: int


@lru_cache(maxsize=16)
def null_profile(n_minutes: int = 390, sigma_1min: float = 1.25,
                 tick: float = 0.25, draws: int = 1200,
                 seed: int = 20260829) -> NullProfile:
    """Les cinq lectures, mesurées sur des séances sans dérive.

    Rien n'est ajouté à la marche : pas de saut, pas de saisonnalité, pas de
    régime. C'est le minimum contre lequel une lecture de profil doit se
    comparer, et il suffit à établir qu'aucune des cinq n'est rare.
    """
    rng = Rng(seed)
    n_periods = max(int(round(n_minutes / PERIOD_MIN)), 1)
    singles: list[int] = []
    poor_h = poor_l = ext = 0
    largeurs: list[float] = []
    for _ in range(draws):
        prix, x = [0.0], 0.0
        for _ in range(n_minutes):
            x += sigma_1min * rng.gauss()
            prix.append(x)
        prof = from_path(prix, n_periods, tick)
        singles.append(len(prof.single_prints))
        poor_h += prof.poor_high
        poor_l += prof.poor_low
        haut, bas = prof.range_extension()
        ext += (haut or bas)
        va_bas, va_haut = prof.value_area()
        etendue = prof.prices[-1] - prof.prices[0]
        largeurs.append((va_haut - va_bas) / etendue if etendue > 0 else 0.0)
    singles.sort()
    return NullProfile(
        singles_mean=sum(singles) / len(singles),
        singles_q95=singles[min(len(singles) - 1, int(0.95 * len(singles)))],
        p_poor_high=poor_h / draws,
        p_poor_low=poor_l / draws,
        p_extension=ext / draws,
        value_width_mean=sum(largeurs) / len(largeurs),
        draws=draws,
    )


def null_by_tick(ticks: tuple[float, ...] = (0.25, 0.5, 1.0, 2.0, 4.0),
                 n_minutes: int = 390, sigma_1min: float = 1.25,
                 draws: int = 400) -> tuple[tuple[float, float, float], ...]:
    """La sensibilité des lectures d'extrême à la granularité du prix.

    C'est au TPO ce que la taille de grappe est au footprint : un paramètre
    déclaré dont la loi nulle dépend entièrement. Un extrême pauvre est rare
    quand la séance compte cent trente niveaux, banal quand elle en compte
    dix — et le nombre de niveaux ne dit rien du marché, seulement du pas de
    cotation rapporté à la volatilité.

    Rend, par pas : `(tick, P(extrême haut pauvre), tirages simples moyens)`.
    """
    out = []
    for t in ticks:
        loi = null_profile(n_minutes, sigma_1min, t, draws)
        out.append((t, loi.p_poor_high, loi.singles_mean))
    return tuple(out)


def synthesise(n_minutes: int = 390, sigma_1min: float = 1.25,
               drift_per_min: float = 0.0, tick: float = 0.25,
               base: float = 6000.0, seed: int = 20260829) -> Profile:
    """Une séance déterministe, pour la figure.

    La dérive est un paramètre déclaré, jamais dérivée de quoi que ce soit —
    même règle que partout ailleurs dans le dépôt.
    """
    rng = Rng(seed)
    prix, x = [base], base
    for _ in range(n_minutes):
        x += drift_per_min + sigma_1min * rng.gauss()
        prix.append(x)
    return from_path(prix, max(int(round(n_minutes / PERIOD_MIN)), 1), tick)


def main() -> None:
    loi = null_profile()
    print("loi nulle du profil TPO, séance sans dérive :")
    print(f"  tirages simples          : {loi.singles_mean:.1f} en moyenne, "
          f"{loi.singles_q95:.0f} au quantile 95 %")
    print(f"  P(extrême haut pauvre)   : {loi.p_poor_high:.3f}")
    print(f"  P(extrême bas pauvre)    : {loi.p_poor_low:.3f}")
    print(f"  P(extension de séance)   : {loi.p_extension:.3f}")
    print(f"  aire de valeur / étendue : {loi.value_width_mean:.3f}")
    print()
    print("sensibilité au pas de cotation :")
    for t, pph, sm in null_by_tick():
        print(f"  tick {t:4.2f}  →  P(haut pauvre) {pph:.3f}  "
              f"tirages simples {sm:5.1f}")
    print()
    prof = synthesise()
    va = prof.value_area()
    print(f"séance construite : {len(prof.prices)} niveaux, POC {prof.poc:.2f}, "
          f"aire {va[0]:.2f}–{va[1]:.2f}, "
          f"{len(prof.single_prints)} tirages simples, "
          f"haut pauvre {prof.poor_high}, extension {prof.range_extension()}")
