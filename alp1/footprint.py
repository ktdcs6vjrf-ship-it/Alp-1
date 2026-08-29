"""Le footprint : ce que le carnet laisse comme trace une fois exécuté.

Un graphique en chandelles dit *où* le prix est allé. Un footprint dit *qui
l'y a poussé* : pour chaque niveau de prix d'une barre, le volume échangé à
la vente au marché — c'est-à-dire au **bid**, un vendeur qui traverse le
spread — et le volume échangé à l'achat au marché, au **ask**. La différence
est le delta du niveau ; sa somme sur la barre est le delta de barre.

Trois lectures, et ce que chacune vaut
--------------------------------------
**Le déséquilibre diagonal.** On compare le volume à l'ask d'un niveau au
volume au bid du niveau *inférieur* — jamais du même niveau. La raison est
mécanique : à un instant donné, l'ask d'un prix et le bid de ce même prix ne
sont pas en concurrence, ils sont les deux côtés de deux spreads différents.
La diagonale met en regard les deux ordres qui, eux, se disputaient la même
file. Un rapport de trois pour un est le seuil d'usage.

**L'absorption.** Un volume important sans progrès de prix. C'est la lecture
la plus utile et la plus mal mesurée : « important » ne veut rien dire hors
d'une échelle, et la bonne échelle est celle de l'impact. Sous une loi
d'impact en racine, le déplacement d'une barre vaut `λ·σ·√V` à un aléa près,
et la question devient un `z` : `z = Δprix / (λ·σ·√V)`. Une absorption est un
`|z|` anormalement **petit**, et sa p-valeur est exacte.

**L'épuisement.** Le volume s'effondre au dernier niveau atteint, dans le
sens du mouvement. C'est le seul des trois qui n'a pas de forme fermée : le
volume au niveau extrême d'une excursion est un temps local, et sa loi se
simule. Elle est simulée ici, à graine déclarée.

Ce que ce module ne prétend pas
-------------------------------
Aucune de ces trois lectures n'est un signal. Chacune est une **statistique**
munie de sa loi nulle, et c'est tout ce que le dépôt autorise à publier. Un
déséquilibre à trois pour un arrive sous martingale ; la question n'est
jamais s'il est arrivé, mais s'il est arrivé plus souvent que sa fréquence
nulle, et de combien.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from .costs import ES, norm_cdf
from .mc import Rng
from .orderflow import kyle_lambda

#: Seuil d'usage du déséquilibre diagonal, en rapport de volumes. Trois pour
#: un est la convention des plateformes ; il est déclaré ici pour que la loi
#: nulle porte sur le même seuil que la lecture.
IMBALANCE_RATIO = 3.0

#: Volume minimal exigé du côté dominant pour qu'un déséquilibre compte. Sans
#: lui, un niveau à 3 contre 0 vaut un niveau à 300 contre 60, et la lecture
#: se remplit de bruit de bord.
IMBALANCE_MIN_VOLUME = 10

#: Taille de grappe : nombre de contrats qu'un même participant fait passer
#: d'un coup. C'est le paramètre qui décide **entièrement** de la loi nulle du
#: déséquilibre, et il n'est pas observable sur un flux agrégé.
#:
#: La raison est arithmétique. Si les contrats arrivaient un à un et
#: indépendamment, l'ask d'un niveau à deux cents contrats suivrait une
#: binomiale d'écart-type sept ; un rapport de trois pour un exigerait un
#: écart de plus de quinze écarts-types, c'est-à-dire jamais. Le déséquilibre
#: diagonal serait alors un signal parfait, ce qu'il n'est manifestement pas.
#: Ce qui sauve la lecture — et ce qui la limite — est que les contrats
#: n'arrivent pas un à un : un ordre de vingt lots est **un** tirage, pas
#: vingt. L'échantillon effectif d'un niveau est son volume divisé par la
#: taille de grappe.
#:
#: Vingt est une valeur déclarée, pas mesurée. Le module expose la sensibilité
#: à ce choix, parce qu'elle est le vrai sujet : la fréquence nulle d'un
#: déséquilibre passe de l'impossible au banal sur la plage plausible.
CLUMP_DEFAULT = 20

#: Profondeur au premier niveau, en contrats. Ordre de grandeur du haut de
#: carnet d'un future indiciel liquide ; elle sert à fixer l'échelle d'impact
#: et n'est utilisée que pour cela.
DEPTH_CONTRACTS = 60.0

#: Déplacement attendu d'une barre par racine de son volume, en points
#: d'indice. C'est `λ` de Kyle, repris de `orderflow` plutôt que posé ici :
#: une échelle d'impact écrite deux fois finirait par diverger de l'autre.
IMPACT_PER_ROOT_VOLUME = kyle_lambda(ES.tick_size, DEPTH_CONTRACTS)


@dataclass(frozen=True)
class Cell:
    """Un niveau de prix d'une barre : ce qui s'est vendu, ce qui s'est acheté."""

    price: float
    bid: int      # exécuté au bid — vendeur au marché
    ask: int      # exécuté à l'ask — acheteur au marché

    @property
    def volume(self) -> int:
        return self.bid + self.ask

    @property
    def delta(self) -> int:
        return self.ask - self.bid


@dataclass(frozen=True)
class Bar:
    """Une barre en footprint. Les niveaux sont ordonnés du bas vers le haut."""

    cells: tuple[Cell, ...]
    open_price: float
    close_price: float

    @property
    def volume(self) -> int:
        return sum(c.volume for c in self.cells)

    @property
    def delta(self) -> int:
        return sum(c.delta for c in self.cells)

    @property
    def displacement(self) -> float:
        return self.close_price - self.open_price

    @property
    def poc(self) -> float:
        """Le niveau le plus échangé de la barre."""
        return max(self.cells, key=lambda c: (c.volume, -c.price)).price

    @property
    def high(self) -> float:
        return self.cells[-1].price

    @property
    def low(self) -> float:
        return self.cells[0].price


# ---------------------------------------------------------------------------
# Déséquilibre diagonal, et sa loi nulle exacte
# ---------------------------------------------------------------------------


def diagonal_imbalances(bar: Bar, ratio: float = IMBALANCE_RATIO,
                        min_volume: int = IMBALANCE_MIN_VOLUME
                        ) -> tuple[tuple[float, str], ...]:
    """Les déséquilibres diagonaux de la barre, du bas vers le haut.

    Un déséquilibre acheteur au niveau `p` compare l'ask de `p` au bid de
    `p−1` ; un déséquilibre vendeur compare le bid de `p` à l'ask de `p+1`.
    Le côté dominant doit atteindre `min_volume`, faute de quoi le rapport ne
    mesure que du bruit de bord.
    """
    out = []
    for i, cell in enumerate(bar.cells):
        if i > 0:
            dessous = bar.cells[i - 1]
            if (cell.ask >= min_volume
                    and cell.ask >= ratio * max(dessous.bid, 1)):
                out.append((cell.price, "acheteur"))
        if i + 1 < len(bar.cells):
            dessus = bar.cells[i + 1]
            if (cell.bid >= min_volume
                    and cell.bid >= ratio * max(dessus.ask, 1)):
                out.append((cell.price, "vendeur"))
    return tuple(out)


@lru_cache(maxsize=4096)
def _binomial_pmf(n: int, k: int) -> float:
    """`P(X = k)` pour `X ~ Binomiale(n, ½)`, en exact."""
    if k < 0 or k > n:
        return 0.0
    return math.comb(n, k) / (2.0 ** n)


@lru_cache(maxsize=4096)
def null_imbalance_probability(n_haut: int, n_bas: int,
                               ratio: float = IMBALANCE_RATIO,
                               min_volume: int = IMBALANCE_MIN_VOLUME,
                               clump: int = CLUMP_DEFAULT) -> float:
    """`P(déséquilibre)` sous martingale, en exact et sans simulation.

    Le volume total de chaque niveau est tenu pour donné — c'est une
    conditionnelle, et c'est la bonne : le footprint ne prétend rien sur la
    quantité échangée, seulement sur sa répartition entre les deux côtés.
    Sous martingale chaque **grappe** est aussi probablement initiée par un
    acheteur que par un vendeur, donc l'ask du niveau haut suit une binomiale
    de paramètre ½ sur `n_haut/clump` tirages, indépendante de celle du bid
    du niveau bas.

    La probabilité est alors une double somme finie, et elle est exacte.
    C'est ce qui distingue cette loi nulle des lois simulées du dépôt : ici il
    n'y a rien à simuler. Ce qui reste à déclarer, et qui décide de tout, est
    la taille de grappe.
    """
    k_haut = max(int(round(n_haut / max(clump, 1))), 0)
    k_bas = max(int(round(n_bas / max(clump, 1))), 0)
    seuil_grappes = min_volume / max(clump, 1)
    total = 0.0
    for a in range(k_haut + 1):
        if a < seuil_grappes:
            continue
        pa = _binomial_pmf(k_haut, a)
        if pa == 0.0:
            continue
        # `max(bid, 1)` dans la lecture : un bid nul se lit comme un bid de 1,
        # donc le seuil sur le niveau bas est `a/ratio`, jamais moins de 1.
        if a / ratio < 1.0:
            continue
        k_max = min(k_bas, int(math.floor(a / ratio)))
        total += pa * sum(_binomial_pmf(k_bas, b) for b in range(0, k_max + 1))
    return total


def null_imbalance_by_clump(n_haut: int, n_bas: int,
                            clumps: tuple[int, ...] = (1, 2, 5, 10, 20, 50, 100),
                            ratio: float = IMBALANCE_RATIO
                            ) -> tuple[tuple[int, float], ...]:
    """La sensibilité de la loi nulle à la taille de grappe.

    C'est la seule chose que ce module ait à dire d'important sur le
    déséquilibre diagonal, et elle est inconfortable : la fréquence nulle
    passe de zéro à plusieurs pour cent sur une plage de grappes toutes
    plausibles. Un opérateur qui lit un déséquilibre à trois pour un lit donc
    un événement dont la rareté dépend d'un paramètre qu'il n'observe pas.
    """
    return tuple((c, null_imbalance_probability(n_haut, n_bas, ratio,
                                                IMBALANCE_MIN_VOLUME, c))
                 for c in clumps)


def expected_imbalances(bar: Bar, ratio: float = IMBALANCE_RATIO,
                        min_volume: int = IMBALANCE_MIN_VOLUME,
                        clump: int = CLUMP_DEFAULT) -> float:
    """Nombre de déséquilibres attendu sur cette barre, sous martingale.

    C'est l'espérance à volumes de niveau inchangés : la barre est comparée à
    elle-même privée de toute information directionnelle. Une barre qui en
    montre deux quand sa loi nulle en attend deux ne montre rien.
    """
    total = 0.0
    for i, cell in enumerate(bar.cells):
        if i > 0:
            total += null_imbalance_probability(
                cell.volume, bar.cells[i - 1].volume, ratio, min_volume, clump)
        if i + 1 < len(bar.cells):
            total += null_imbalance_probability(
                cell.volume, bar.cells[i + 1].volume, ratio, min_volume, clump)
    return total


# ---------------------------------------------------------------------------
# Absorption : un volume qui ne déplace pas le prix
# ---------------------------------------------------------------------------


def absorption_z(bar: Bar, sigma_per_root_volume: float) -> float:
    """`z = Δprix / (λ·√V)` — le déplacement rapporté à celui qu'on attendait.

    Sous une loi d'impact en racine du volume, le déplacement d'une barre est
    de l'ordre de `λ·√V`. Le `z` rendu est donc sans dimension, et il se
    compare d'une barre à l'autre quel que soit le volume.
    """
    attendu = sigma_per_root_volume * math.sqrt(max(bar.volume, 1))
    return bar.displacement / attendu if attendu > 0 else 0.0


def absorption_p_value(bar: Bar, sigma_per_root_volume: float) -> float:
    """`P(|Z| ≤ |z|)` sous martingale — petite quand l'absorption est nette.

    Une absorption est un déplacement **anormalement faible** pour le volume
    échangé. La p-valeur est donc celle d'une queue **centrale** et non d'une
    queue extrême, et elle se lit à l'envers de l'habitude : 0,02 veut dire
    qu'un déplacement aussi petit n'arrive que deux fois sur cent sans que
    quelqu'un ait tenu le prix.
    """
    z = abs(absorption_z(bar, sigma_per_root_volume))
    return 2.0 * norm_cdf(z) - 1.0


# ---------------------------------------------------------------------------
# Épuisement : le volume s'effondre au dernier niveau
# ---------------------------------------------------------------------------


def exhaustion_ratio(bar: Bar, sens: int) -> float:
    """Volume du niveau extrême rapporté à la médiane des niveaux de la barre.

    `sens` vaut +1 pour le haut de barre, −1 pour le bas. Un rapport petit
    est un épuisement : le prix a atteint le niveau, presque personne n'y a
    traité, et il n'y avait plus de flux pour l'y tenir.
    """
    volumes = sorted(c.volume for c in bar.cells)
    if not volumes:
        return 0.0
    n = len(volumes)
    mediane = (volumes[n // 2] if n % 2
               else 0.5 * (volumes[n // 2 - 1] + volumes[n // 2]))
    extreme = bar.cells[-1 if sens > 0 else 0].volume
    return extreme / mediane if mediane > 0 else 0.0


@dataclass(frozen=True)
class NullExhaustion:
    """La loi nulle du rapport d'épuisement, simulée à graine déclarée."""

    mean: float
    sd: float
    q05: float
    q50: float
    draws: int


@lru_cache(maxsize=32)
def null_exhaustion(n_levels: int = 9, volume: int = 900, draws: int = 4000,
                    seed: int = 20260829) -> NullExhaustion:
    """Loi du rapport d'épuisement sous martingale.

    Le volume au niveau extrême d'une excursion est un **temps local**, et il
    n'a pas de forme fermée commode. On le simule : une marche symétrique de
    `volume` pas sur `n_levels` niveaux, chaque pas déposant un contrat au
    niveau visité, puis le rapport du niveau extrême à la médiane.

    Le résultat est le seul chiffre qui donne un sens à « le volume
    s'effondre » : sous martingale il s'effondre déjà, parce que le prix
    passe peu de temps aux extrémités de son excursion.
    """
    rng = Rng(seed)
    echantillon = []
    demi = n_levels // 2
    for _ in range(draws):
        compte = [0] * n_levels
        pos = demi
        for _ in range(volume):
            compte[pos] += 1
            pos += 1 if rng.uniform() < 0.5 else -1
            pos = min(max(pos, 0), n_levels - 1)
        tries = sorted(compte)
        mediane = (tries[n_levels // 2] if n_levels % 2
                   else 0.5 * (tries[n_levels // 2 - 1] + tries[n_levels // 2]))
        haut = compte[-1]
        echantillon.append(haut / mediane if mediane > 0 else 0.0)
    echantillon.sort()
    moyenne = sum(echantillon) / len(echantillon)
    var = sum((v - moyenne) ** 2 for v in echantillon) / max(len(echantillon) - 1, 1)

    def q(p: float) -> float:
        i = min(len(echantillon) - 1, max(0, int(p * (len(echantillon) - 1))))
        return echantillon[i]

    return NullExhaustion(moyenne, math.sqrt(var), q(0.05), q(0.50), draws)


# ---------------------------------------------------------------------------
# Barres construites : trois lectures, montrées plutôt que décrites
# ---------------------------------------------------------------------------


#: Le `z` d'impact que chaque barre construite vise. Le déplacement n'est pas
#: posé en ticks mais en multiples de l'impact attendu, parce que c'est la
#: seule échelle sur laquelle « beaucoup de volume, peu de prix » veut dire
#: quelque chose. Une barre neutre se déplace d'un impact ; une absorption
#: d'un sixième ; une barre de déséquilibre de trois.
Z_CIBLE = {"neutre": -1.0, "absorption": 0.16, "epuisement": 2.0,
           "desequilibre": 3.0}

#: Multiplicateur de volume par lecture. L'absorption n'est pas seulement un
#: petit déplacement : c'est un petit déplacement **pour un gros volume**, et
#: une barre construite qui oublierait le second terme ne montrerait rien.
V_MULT = {"neutre": 1.0, "absorption": 3.2, "epuisement": 0.9,
          "desequilibre": 1.1}


def synthesise(kind: str, seed: int = 20260829, n_levels: int = 9,
               tick: float = 0.25, base: float = 6000.0) -> Bar:
    """Une barre déterministe portant nettement l'une des trois lectures.

    Les barres sont **construites**, et le document le dit à chaque fois. Leur
    rôle n'est pas de prouver qu'une lecture marche — aucune donnée de marché
    n'est atteignable depuis ce dépôt — mais de montrer à quoi elle ressemble
    quand elle est nette, pour que le lecteur sache ce qu'il cherche.

    Le déplacement de clôture est **déduit** d'un `z` d'impact visé et du
    volume effectivement construit, jamais écrit en ticks : c'est la seule
    façon que la barre d'absorption reste une absorption quand on change le
    nombre de niveaux ou la forme de la cloche.

    `kind` vaut `"neutre"`, `"absorption"`, `"epuisement"` ou `"desequilibre"`.
    """
    rng = Rng(seed + {"neutre": 0, "absorption": 1,
                      "epuisement": 2, "desequilibre": 3}[kind])
    prix = [base + tick * (i - n_levels // 2) for i in range(n_levels)]
    demi = n_levels // 2
    mult = V_MULT[kind]

    cells: list[Cell] = []
    for i, p in enumerate(prix):
        # Cloche de volume centrée sur le milieu de barre : c'est la forme
        # qu'une excursion produit sans qu'aucune intention n'y soit.
        forme = math.exp(-0.5 * ((i - demi) / 2.1) ** 2)
        total = int(mult * (40 + 260 * forme + 24 * rng.uniform()))
        part = 0.5
        if kind == "desequilibre" and i >= demi:
            part = 0.86          # acheteurs au marché sur la moitié haute
        elif kind == "absorption" and i >= n_levels - 3:
            part = 0.74          # ils achètent, et le prix ne monte pas
        elif kind == "epuisement" and i == n_levels - 1:
            total = int(total * 0.16)
            part = 0.58
        ask = int(round(total * part))
        cells.append(Cell(p, total - ask, ask))

    volume = sum(c.volume for c in cells)
    ecart = Z_CIBLE[kind] * IMPACT_PER_ROOT_VOLUME * math.sqrt(volume)
    ouverture = prix[demi] if kind != "epuisement" else prix[1]
    # La clôture est ramenée sur la grille de ticks, et bornée à la barre.
    cloture = min(max(ouverture + tick * round(ecart / tick), prix[0]), prix[-1])
    return Bar(tuple(cells), ouverture, cloture)


def main() -> None:
    lam = IMPACT_PER_ROOT_VOLUME
    print(f"impact par racine de volume : {lam:.5f} point d'indice")
    print()
    for kind in ("neutre", "absorption", "epuisement", "desequilibre"):
        bar = synthesise(kind)
        print(f"{kind:14} V={bar.volume:5d}  Δ={bar.delta:+5d}  "
              f"Δprix={bar.displacement:+5.2f}  "
              f"z={absorption_z(bar, lam):+6.2f}  "
              f"p_abs={absorption_p_value(bar, lam):.3f}  "
              f"desq={len(diagonal_imbalances(bar))}  "
              f"attendu={expected_imbalances(bar):.2f}  "
              f"epuis={exhaustion_ratio(bar, +1):.3f}")
    print()
    print("loi nulle de l'épuisement :", null_exhaustion())
    print()
    print("sensibilité du déséquilibre à la taille de grappe (200 vs 200) :")
    for c, prob in null_imbalance_by_clump(200, 200):
        print(f"  grappe {c:3d}  →  n_eff {200 / c:5.1f}  P(3:1) = {prob:.4f}")
