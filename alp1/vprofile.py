"""Profil de volume : POC, aire de valeur, HVN et LVN comme densité d'occupation.

Le profil de volume est un histogramme du volume échangé par niveau de prix,
et non par unité de temps. Les sigles qui en dérivent nomment des points de
cet histogramme.

Vocabulaire
-----------
``POC`` — *Point of Control*
    Prix du maximum de l'histogramme : le niveau où le plus de volume s'est
    échangé sur la période de construction.

``VA`` — *Value Area*, ``VAH`` / ``VAL`` — *Value Area High* / *Low*
    Plus petit intervalle contigu centré sur le POC contenant une fraction
    fixée du volume total, traditionnellement 70 %. Ses bornes sont VAH en
    haut, VAL en bas. Certains logiciels les notent HVA et LVA — c'est le même
    objet sous un autre sigle.

``HVN`` / ``LVN`` — *High* / *Low Volume Node*
    Maximum ou minimum local de l'histogramme. Un HVN est une zone où le prix
    a longtemps échangé ; un LVN une zone qu'il a traversée sans y traiter.

Ce que l'histogramme mesure réellement
--------------------------------------
Un profil de volume est, à la vitesse d'échange près, un estimateur de la
**densité d'occupation** du prix — le temps passé par niveau. Cette lecture
n'est pas une image : c'est un théorème de la théorie des diffusions. Pour une
diffusion de volatilité locale ``σ(x)``, la densité d'occupation d'un niveau
est inversement proportionnelle à ``σ(x)²`` : le prix s'attarde là où il bouge
lentement et traverse vite là où il bouge vite.

Trois conséquences suivent, et toutes trois sont mesurables :

1. Un LVN n'est pas un « vide » que le prix « comble » : c'est un intervalle de
    **volatilité locale élevée**. La traversée rapide n'est pas la prédiction,
    c'est la définition.
2. Un stop exprimé en pourcentage fixe du prix — {stop} % dans ce papier —
    n'a donc pas la même largeur *en écarts-types* selon le nœud où l'entrée
    a lieu. Sur un LVN il peut valoir la moitié de ce qu'il vaut sur un HVN, et
    la probabilité de le toucher par bruit seul double.
3. Le POC est le mode de la densité d'occupation, donc le point de volatilité
    locale minimale. « Le prix revient au POC » est un énoncé sur le temps de
    séjour, pas sur une force de rappel : un prix qui erre sans dérive y passe
    plus de temps parce qu'il y avance moins vite.

L'inversion densité → volatilité locale est implémentée ci-dessous. Elle donne
au profil de volume un contenu quantitatif — une carte de la volatilité locale
— là où la lecture usuelle n'en tire qu'un jeu de niveaux.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_EPS = 1e-12


@dataclass(frozen=True)
class Node:
    """Un pas de l'histogramme : centre, largeur, volume."""

    price: float
    width: float
    volume: float


@dataclass(frozen=True)
class ValueArea:
    """Aire de valeur : bornes, volume couvert, fraction visée."""

    low: float
    high: float
    covered: float
    fraction: float

    @property
    def width(self) -> float:
        return self.high - self.low


@dataclass(frozen=True)
class Profile:
    """Profil de volume à pas constant.

    `prices` sont les centres des pas, `volumes` les volumes correspondants.
    Les grandeurs dérivées — POC, aire de valeur, HVN, LVN — sont calculées,
    jamais choisies : c'est ce qui distingue cette couche d'une lecture
    visuelle, où le nœud retenu est celui qui sert la thèse du moment.
    """

    prices: tuple[float, ...]
    volumes: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.prices) != len(self.volumes):
            raise ValueError("prices et volumes doivent avoir la même longueur")
        if len(self.prices) < 3:
            raise ValueError("au moins 3 pas requis")
        if any(v < 0 for v in self.volumes):
            raise ValueError("volumes négatifs interdits")

    @property
    def step(self) -> float:
        return self.prices[1] - self.prices[0]

    @property
    def total(self) -> float:
        return sum(self.volumes)

    @property
    def poc_index(self) -> int:
        return max(range(len(self.volumes)), key=lambda i: self.volumes[i])

    @property
    def poc(self) -> float:
        return self.prices[self.poc_index]

    def value_area(self, fraction: float = 0.70) -> ValueArea:
        """Aire de valeur par la règle d'extension usuelle.

        On part du POC et on étend l'intervalle du côté qui apporte le plus de
        volume, jusqu'à couvrir `fraction` du total. C'est la règle du *Market
        Profile* d'origine ; elle diffère marginalement d'un intervalle de plus
        haute densité au sens statistique, sans conséquence pratique.
        """
        if not 0.0 < fraction < 1.0:
            raise ValueError("fraction doit être dans ]0, 1[")
        lo = hi = self.poc_index
        covered = self.volumes[lo]
        target = fraction * self.total
        n = len(self.volumes)
        while covered < target and (lo > 0 or hi < n - 1):
            down = self.volumes[lo - 1] if lo > 0 else -1.0
            up = self.volumes[hi + 1] if hi < n - 1 else -1.0
            if up >= down:
                hi += 1
                covered += up
            else:
                lo -= 1
                covered += down
        half = self.step / 2.0
        return ValueArea(low=self.prices[lo] - half, high=self.prices[hi] + half,
                         covered=covered / self.total, fraction=fraction)

    # --- nœuds ------------------------------------------------------------

    def _prominence(self, i: int, high: bool) -> float:
        """Proéminence topographique du pas `i`, en volume.

        Définition standard : pour un sommet, hauteur au-dessus du plus haut
        des deux cols qui le séparent d'un sommet plus élevé. Pour un creux,
        la même chose à l'envers. C'est la seule mesure qui distingue un nœud
        d'une ondulation de bruit, et elle ne dépend d'aucune fenêtre choisie
        après coup.
        """
        vols = self.volumes
        v = vols[i]
        best = []
        for direction in (-1, 1):
            j = i + direction
            saddle = v
            found = False
            while 0 <= j < len(vols):
                if (high and vols[j] > v) or (not high and vols[j] < v):
                    found = True
                    break
                saddle = min(saddle, vols[j]) if high else max(saddle, vols[j])
                j += direction
            # Bord du profil atteint sans sommet plus élevé : le col est le bord.
            best.append(saddle if found else (min(saddle, vols[max(0, min(j, len(vols) - 1))])
                                              if high else
                                              max(saddle, vols[max(0, min(j, len(vols) - 1))])))
        return (v - max(best)) if high else (min(best) - v)

    def _extrema(self, high: bool, prominence: float) -> list[int]:
        """Extrema locaux dont la proéminence dépasse un seuil relatif.

        Le seuil est exprimé en fraction du volume maximal du profil. Sans ce
        filtre, le moindre créneau de bruit devient un « nœud » : c'est la
        principale source de surajustement de cette couche, et la seule façon
        de la contenir est de fixer le seuil avant de regarder le profil.
        """
        peak = max(self.volumes)
        if peak <= 0:
            return []
        out: list[int] = []
        for i in range(1, len(self.volumes) - 1):
            v, left, right = self.volumes[i], self.volumes[i - 1], self.volumes[i + 1]
            if high and not (v >= left and v >= right and (v > left or v > right)):
                continue
            if not high and not (v <= left and v <= right and (v < left or v < right)):
                continue
            if self._prominence(i, high) / peak >= prominence:
                out.append(i)
        return out

    def hvn(self, prominence: float = 0.05) -> list[float]:
        """Nœuds de haut volume : maxima locaux suffisamment proéminents."""
        return [self.prices[i] for i in self._extrema(True, prominence)]

    def lvn(self, prominence: float = 0.05) -> list[float]:
        """Nœuds de bas volume : minima locaux suffisamment proéminents."""
        return [self.prices[i] for i in self._extrema(False, prominence)]

    # --- inversion : densité d'occupation -> volatilité locale -------------

    def local_volatility(self, sigma_reference: float) -> tuple[float, ...]:
        """Volatilité locale impliquée par la densité d'occupation.

        Pour une diffusion ``dX = σ(x)dW`` sur un intervalle, la densité
        d'occupation vérifie ``m(x) ∝ 1/σ(x)²``. En normalisant sur le profil
        entier, la volatilité locale au pas `i` vaut

            σ(x_i) = σ_ref · √(v̄ / v_i)

        où ``v̄`` est le volume moyen par pas. Le facteur de normalisation
        `sigma_reference` est la volatilité mesurée sur la période de
        construction, en points par racine de minute : l'inversion ne crée pas
        d'information de niveau, elle redistribue une volatilité connue selon
        la forme du profil.

        Un pas vide donnerait une volatilité infinie ; il est plafonné au
        quadruple de la référence, ce qui borne aussi l'usage qu'on peut faire
        d'un profil trop finement discrétisé.
        """
        if sigma_reference <= 0:
            raise ValueError("sigma_reference doit être > 0")
        mean_v = self.total / len(self.volumes)
        out = []
        for v in self.volumes:
            ratio = mean_v / max(v, _EPS)
            out.append(min(sigma_reference * math.sqrt(ratio), 4.0 * sigma_reference))
        return tuple(out)

    def sigma_at(self, price: float, sigma_reference: float) -> float:
        """Volatilité locale au niveau de prix donné."""
        sig = self.local_volatility(sigma_reference)
        idx = min(range(len(self.prices)),
                  key=lambda i: abs(self.prices[i] - price))
        return sig[idx]

    def traversal_time(self, price_from: float, price_to: float,
                       sigma_reference: float) -> float:
        """Temps moyen de traversée d'un intervalle, en minutes.

        Pour une diffusion sans dérive, le temps moyen passé dans une bande de
        largeur ``dx`` autour de ``x`` avant d'en sortir croît comme
        ``dx²/σ(x)²``. En sommant sur les pas franchis, on obtient un temps de
        traversée qui est le contenu prédictif réel des sigles HVN et LVN :

            HVN — volume élevé, σ locale basse, traversée lente ;
            LVN — volume faible, σ locale haute, traversée rapide.

        La grandeur est un ordre de grandeur, pas un temps d'arrêt exact : elle
        ignore les allers-retours. Elle suffit à ce qu'on lui demande, à savoir
        comparer deux nœuds du même profil.
        """
        sig = self.local_volatility(sigma_reference)
        lo, hi = sorted((price_from, price_to))
        step = self.step
        total = 0.0
        for i, p in enumerate(self.prices):
            if lo - step / 2 <= p <= hi + step / 2:
                total += (step / sig[i]) ** 2
        return total

    def effective_stop_sigma(self, price: float, stop_points: float,
                             sigma_reference: float, minutes: float = 1.0) -> float:
        """Largeur du stop en écarts-types locaux, au niveau donné.

        C'est la conséquence opérationnelle du profil, et la seule que ce
        papier retienne. Un stop fixé en pourcentage du prix est une constante
        en points ; il n'est pas une constante en unités de risque. Entrer sur
        un LVN avec le même stop qu'un HVN, c'est accepter en silence une
        probabilité de sortie par bruit sensiblement plus élevée.
        """
        sigma = self.sigma_at(price, sigma_reference) * math.sqrt(minutes)
        if sigma <= 0:
            return math.inf
        return stop_points / sigma


# --- Construction ------------------------------------------------------------


def from_bins(prices: list[float] | tuple[float, ...],
              volumes: list[float] | tuple[float, ...]) -> Profile:
    """Profil construit depuis des pas déjà agrégés."""
    return Profile(tuple(float(p) for p in prices), tuple(float(v) for v in volumes))


def from_path(path: list[float] | tuple[float, ...], step: float,
              volume_per_visit: float = 1.0) -> Profile:
    """Profil construit par comptage des visites d'un chemin de prix.

    Chaque observation incrémente le pas qui la contient. Le profil obtenu est
    exactement la densité d'occupation empirique du chemin : c'est la façon la
    plus directe de vérifier que l'histogramme du volume et le temps de séjour
    sont la même chose dès que le volume par unité de temps est stable.
    """
    if step <= 0:
        raise ValueError("step doit être > 0")
    if len(path) < 3:
        raise ValueError("chemin trop court")
    lo = math.floor(min(path) / step) * step
    hi = math.ceil(max(path) / step) * step
    n = max(3, int(round((hi - lo) / step)) + 1)
    prices = tuple(lo + i * step for i in range(n))
    counts = [0.0] * n
    for x in path:
        idx = min(n - 1, max(0, int(round((x - lo) / step))))
        counts[idx] += volume_per_visit
    return Profile(prices, tuple(counts))


def composite(profiles: list[Profile]) -> Profile:
    """Profil composite : somme de profils partageant la même grille.

    Le profil *composite* couvre plusieurs séances et sert d'ancrage de long
    terme ; le profil de séance sert d'ancrage court. La distinction n'est pas
    cosmétique : leurs POC répondent à des questions différentes — où
    l'inventaire s'est accumulé sur la période longue, et où il s'échange
    aujourd'hui.
    """
    if not profiles:
        raise ValueError("aucun profil")
    grid = profiles[0].prices
    for p in profiles[1:]:
        if p.prices != grid:
            raise ValueError("grilles de prix différentes")
    totals = [sum(p.volumes[i] for p in profiles) for i in range(len(grid))]
    return Profile(grid, tuple(totals))


def reference_profile(center: float = 6000.0, step: float = 2.0,
                      span: float = 60.0) -> Profile:
    """Profil de séance synthétique servant d'illustration dans le document.

    Trois zones d'acceptation séparées par deux zones de traversée : c'est la
    forme la plus courante d'une séance en tendance qui s'est arrêtée deux fois
    en chemin. Aucune donnée de marché — le profil sert à rendre les
    définitions vérifiables et les figures reproductibles.
    """
    n = int(2 * span / step) + 1
    prices = tuple(center - span + i * step for i in range(n))
    humps = ((center - 34.0, 9.0, 0.62), (center - 2.0, 12.0, 1.00),
             (center + 30.0, 8.0, 0.48))
    volumes = []
    for p in prices:
        v = 0.02
        for mu, sd, amp in humps:
            v += amp * math.exp(-((p - mu) / sd) ** 2 / 2.0)
        volumes.append(round(v * 12_000.0))
    return Profile(prices, tuple(volumes))
