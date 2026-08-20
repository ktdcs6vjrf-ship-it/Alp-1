"""Théorie de Dow : les principes, la structure de swings, et leur loi nulle.

Ce que dit la théorie
---------------------
Charles Dow n'a jamais publié de théorie ; ses éditoriaux du *Wall Street
Journal*, parus entre 1899 et 1902, ont été codifiés après sa mort par William
Hamilton puis Robert Rhea. Six principes en sont issus :

1. **Le marché escompte tout.** Toute information connue est déjà dans le prix.
   Énoncé d'efficience faible, antérieur d'un demi-siècle à sa formulation
   académique — et, pris au sérieux, difficilement compatible avec les cinq
   principes suivants.
2. **Trois tendances coexistent.** Primaire (mois à années), secondaire
   (semaines), mineure (jours). La secondaire retrace typiquement du tiers aux
   deux tiers de la primaire — c'est de là, et non de Fibonacci, que vient
   l'attention portée aux retracements profonds.
3. **Trois phases.** Accumulation, participation du public, distribution.
4. **Les indices doivent se confirmer.** Chez Dow, l'indice industriel et
   l'indice des transports. C'est le seul principe qui ait une contrepartie
   moderne directement testable : la confirmation inter-marchés.
5. **Le volume confirme la tendance.** Le volume s'étend dans le sens de la
   tendance primaire.
6. **La tendance persiste jusqu'à un signal de retournement clair.** C'est le
   principe opérationnel, et le seul qu'ALP-1 utilise réellement.

Ce que la pile en retient
-------------------------
Une définition structurelle : une tendance haussière est une suite de sommets
et de creux croissants — *higher high*, *higher low* — et se retourne quand
cette suite se rompt. Plus la règle intraséance retenue par ALP-1 : une clôture
au-delà du **corps** de la veille vaut continuation ; une clôture avec mèche
dominante vaut rejet.

La question que pose ce module
------------------------------
Ces règles décrivent-elles autre chose qu'une marche aléatoire ? La question
n'est pas rhétorique, elle a une réponse exacte, et elle est surprenante :

    P(mèche haute ≥ k × corps) = 1/(2k + 1),
    P(clôture au-delà du corps de la veille) = 3/4, à parts égales.

Un jour sans dérive sur trois présente donc une « mèche de rejet » au sens de
la règle, et trois jours sur quatre déclenchent un signal de continuation. Ces
fréquences ne sont pas des estimations : ce sont des identités, démontrées plus
bas, et sans paramètre. Elles fixent la barre que toute mesure doit franchir.
Une règle qui se déclenche trois fois sur quatre ne sélectionne rien ; sa
valeur, s'il y en a une, tient entièrement dans la dérive conditionnelle
qu'elle isole — et c'est cette dérive, non la fréquence du motif, que le
protocole doit mesurer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .barriers import prob_target_before_stop
from .costs import norm_cdf


class Trend(str, Enum):
    UP = "up"
    DOWN = "down"
    UNDEFINED = "undefined"


class Pivot(str, Enum):
    HIGHER_HIGH = "HH"
    HIGHER_LOW = "HL"
    LOWER_HIGH = "LH"
    LOWER_LOW = "LL"


TENETS: tuple[tuple[str, str, str], ...] = (
    ("Escompte", "Le marché escompte toute information connue.",
     "non testable en l'état : énoncé d'efficience, pas de prédiction"),
    ("Trois tendances", "Primaire, secondaire, mineure ; la secondaire retrace "
     "du tiers aux deux tiers de la primaire.",
     "testable : distribution des profondeurs de retracement contre sa loi nulle"),
    ("Trois phases", "Accumulation, participation, distribution.",
     "non testable : les phases ne sont identifiables qu'a posteriori"),
    ("Confirmation", "Deux indices liés doivent confirmer le même signal.",
     "testable : lift conditionnel à la confirmation inter-marchés"),
    ("Volume", "Le volume s'étend dans le sens de la tendance primaire.",
     "testable : corrélation volume/rendement signé, effet documenté et faible"),
    ("Persistance", "La tendance se poursuit jusqu'à un signal de retournement.",
     "testable : fréquence de continuation contre la loi nulle de ce module"),
)


# --- Loi nulle des règles journalières ---------------------------------------


def p_dominant_wick(k: float = 1.0) -> float:
    """P(mèche haute ≥ k × corps) pour une journée sans dérive. Forme fermée.

    Démonstration. On modélise la séance par un brownien de volatilité σ partant
    de l'ouverture : ``O = 0``, ``C = X ~ N(0, σ²)``, ``M = max``. Conditionnellement
    à la clôture, le maximum suit la loi du maximum d'un pont brownien :

        P(M ≥ m | C = x) = exp(−2m(m − x)/σ²),   m ≥ max(0, x).

    La condition « mèche haute ≥ k × corps » s'écrit ``M ≥ (1 + k)x`` si x > 0
    et ``M ≥ −kx`` si x < 0. Dans les deux cas la probabilité conditionnelle
    vaut ``exp(−2k(k + 1)x²/σ²)``, et l'intégration contre la densité normale
    donne

        P = 1/√(1 + 4k(k + 1)) = 1/(2k + 1).

    La volatilité disparaît : le résultat est une propriété d'échelle, valable
    pour tout marché et tout horizon de barre. En particulier ``k = 1`` donne
    exactement **un tiers**. Une journée sans dérive sur trois affiche une
    mèche haute au moins aussi longue que son corps ; autant en bas.
    """
    if k < 0:
        raise ValueError("k doit être ≥ 0")
    return 1.0 / (2.0 * k + 1.0)


def p_close_beyond_body() -> tuple[float, float, float]:
    """(P(clôture au-dessus du corps), P(en dessous), P(à l'intérieur)).

    Deux journées browniennes indépendantes de même volatilité. La veille
    ouvre en 0 et clôture en ``X`` ; son corps couvre ``[min(0, X), max(0, X)]``.
    Aujourd'hui clôture en ``X + Y``. Le signal de continuation haussière
    demande ``X + Y > max(0, X)``, soit ``Y > max(−X, 0)``, d'où

        P = P(X > 0)·P(Y > 0) + ∫₀^∞ φ(u)[1 − Φ(u)] du = ¼ + ⅛ = 3/8.

    Par symétrie, 3/8 pour la baisse et 1/4 pour une clôture à l'intérieur du
    corps. La règle de continuation de la couche D1 se déclenche donc **trois
    jours sur quatre** sur un marché sans mémoire, et son signal est équilibré :
    sa fréquence n'apporte aucune information, seule une dérive conditionnelle
    en apporterait.
    """
    up = 0.375
    return up, up, 1.0 - 2.0 * up


def p_continuation_conditional_null() -> float:
    """P(la journée suivante prolonge le signal) sous marche aléatoire : ½.

    Énoncé trivial et pourtant central : sous la loi nulle, conditionner à un
    motif de Dow ne déplace pas la probabilité du rendement suivant. Tout écart
    mesuré à ½ *est* le contenu de la couche. C'est la seule statistique de la
    couche D1 qui mérite d'être collectée.
    """
    return 0.5


# --- Structure de swings ------------------------------------------------------


@dataclass(frozen=True)
class Swing:
    """Un pivot confirmé : indice dans la série, prix, et nature du pivot."""

    index: int
    price: float
    is_high: bool


def swings(path: list[float] | tuple[float, ...], threshold: float) -> list[Swing]:
    """Détection de pivots par renversement d'un seuil fixé (*zigzag*).

    Un extrême courant devient pivot dès que le prix s'en écarte de `threshold`
    en sens contraire. C'est la seule définition de « sommet » et de « creux »
    qui soit causale — elle n'utilise aucune information postérieure à sa date
    de confirmation — et c'est pour cela qu'elle est retenue ici : un pivot
    identifié à l'œil sur un graphe achevé n'aurait pas été identifiable au
    moment d'agir.

    `threshold` est en points de prix. Il n'existe pas de valeur canonique ;
    c'est le paramètre libre de la couche, et le protocole doit le fixer avant
    mesure pour éviter d'en faire un degré de liberté d'ajustement.
    """
    if threshold <= 0:
        raise ValueError("threshold doit être > 0")
    if len(path) < 2:
        return []

    out: list[Swing] = []
    hi_i, hi_p = 0, path[0]
    lo_i, lo_p = 0, path[0]
    direction = 0                      # 0 indéterminé, +1 hausse, −1 baisse
    for i, p in enumerate(path):
        # Les deux extrêmes courants sont suivis en parallèle : tant que la
        # direction n'est pas fixée, c'est le premier renversement confirmé qui
        # la décide, et suivre un seul extrême l'écraserait avant confirmation.
        if p > hi_p:
            hi_i, hi_p = i, p
        if p < lo_p:
            lo_i, lo_p = i, p
        if direction >= 0 and hi_p - p >= threshold:
            out.append(Swing(hi_i, hi_p, is_high=True))
            direction = -1
            hi_i, hi_p = i, p
            lo_i, lo_p = i, p
        elif direction <= 0 and p - lo_p >= threshold:
            out.append(Swing(lo_i, lo_p, is_high=False))
            direction = 1
            hi_i, hi_p = i, p
            lo_i, lo_p = i, p
    return out


def classify(sw: list[Swing]) -> list[Pivot]:
    """Suite HH / HL / LH / LL déduite des pivots successifs de même nature."""
    out: list[Pivot] = []
    last_high: float | None = None
    last_low: float | None = None
    for s in sw:
        if s.is_high:
            if last_high is not None:
                out.append(Pivot.HIGHER_HIGH if s.price > last_high else Pivot.LOWER_HIGH)
            last_high = s.price
        else:
            if last_low is not None:
                out.append(Pivot.HIGHER_LOW if s.price > last_low else Pivot.LOWER_LOW)
            last_low = s.price
    return out


def trend_of(pivots: list[Pivot]) -> Trend:
    """Tendance au sens de Dow : deux pivots concordants suffisent à la nommer."""
    if len(pivots) < 2:
        return Trend.UNDEFINED
    a, b = pivots[-2], pivots[-1]
    if {a, b} == {Pivot.HIGHER_HIGH, Pivot.HIGHER_LOW}:
        return Trend.UP
    if {a, b} == {Pivot.LOWER_HIGH, Pivot.LOWER_LOW}:
        return Trend.DOWN
    return Trend.UNDEFINED


def p_higher_high_null(pullback: float, threshold: float) -> float:
    """P(nouveau sommet avant nouveau creux) sous marche aléatoire, forme fermée.

    Configuration : un sommet confirmé en ``H``, puis un creux confirmé en
    ``P = H − d``. Depuis ``P``, la structure haussière se poursuit si le prix
    atteint ``H`` avant de tomber de `threshold` sous ``P`` — ce qui créerait un
    creux plus bas. C'est un problème de ruine du joueur à deux barrières,
    distantes de ``d`` vers le haut et de ``δ`` vers le bas :

        P(continuation) = δ / (d + δ).

    Le résultat est purement géométrique : il ne dépend ni de la volatilité, ni
    de l'échelle de temps. Un repli égal au seuil de détection donne ½ ; un
    repli deux fois plus profond donne ⅓. **La profondeur du repli, et elle
    seule, fixe la fréquence attendue de la continuation** — ce qui explique
    pourquoi une tendance « qui respire peu » paraît si fiable sans qu'aucune
    information ne soit en jeu.
    """
    if pullback <= 0 or threshold <= 0:
        raise ValueError("pullback et threshold doivent être > 0")
    return threshold / (pullback + threshold)


def p_higher_high(pullback: float, threshold: float, drift_per_min: float,
                  sigma_per_min: float) -> float:
    """Même probabilité sous dérive constante, par la formule de premier passage."""
    return prob_target_before_stop(threshold, pullback, drift_per_min, sigma_per_min)


def implied_drift(p_observed: float, pullback: float, threshold: float,
                  sigma_per_min: float, tol: float = 1e-12) -> float:
    """Dérive qu'exigerait une fréquence de continuation observée.

    Inversion numérique de `p_higher_high`. C'est la traduction dont la couche
    D1 a besoin pour entrer dans le critère maître du papier : une fréquence de
    continuation n'est pas comparable à un seuil de rentabilité, une dérive
    l'est. Une continuation mesurée à 58 % là où la loi nulle en prévoit 50 %
    devient ainsi un nombre de points par minute, à comparer directement à
    ``µ* = c/E[τ]``.
    """
    if not 0.0 < p_observed < 1.0:
        raise ValueError("p_observed doit être dans ]0, 1[")
    lo, hi = -10.0 * sigma_per_min, 10.0 * sigma_per_min
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if p_higher_high(pullback, threshold, mid, sigma_per_min) < p_observed:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


# --- Transfert d'un biais journalier vers une exposition intraséance ---------


def drift_transfer(daily_bias_points: float, session_min: float = 390.0) -> float:
    """Dérive par minute correspondant à un biais journalier, réparti uniformément.

    L'hypothèse de répartition uniforme est optimiste — la dérive intraséance
    se concentre en ouverture et en clôture — mais elle donne la borne la plus
    favorable au signal, ce qui est la bonne convention pour un seuil de
    rejet.
    """
    if session_min <= 0:
        raise ValueError("session_min doit être > 0")
    return daily_bias_points / session_min


def required_daily_bias(friction_points: float, expected_time_min: float,
                        session_min: float = 390.0) -> float:
    """Biais journalier minimal pour qu'une exposition intraséance soit rentable.

    Composition du critère maître et du transfert ci-dessus :

        µ* = c / E[τ]  puis  biais = µ*·T_séance.

    C'est la façon la plus parlante d'exprimer l'exigence portée sur la couche
    D1. Le résultat ne se lit pas en probabilité de continuation mais en points
    d'indice de dérive journalière, et il se compare à ce qu'un biais
    directionnel journalier peut plausiblement valoir.
    """
    if expected_time_min <= 0:
        raise ValueError("expected_time_min doit être > 0")
    return friction_points / expected_time_min * session_min


def wick_threshold_for_frequency(frequency: float) -> float:
    """Seuil `k` de mèche dont la fréquence nulle vaut `frequency`. Inverse exact.

    Utile pour calibrer la sélectivité d'une règle *avant* de la mesurer : une
    règle qu'on souhaite voir se déclencher un jour sur dix demande
    ``k = (1/0,1 − 1)/2 = 4,5`` — une mèche quatre fois et demie plus longue que
    le corps, ce qui est une exigence tout autre que celle du « rejet » usuel.
    """
    if not 0.0 < frequency <= 1.0:
        raise ValueError("frequency doit être dans ]0, 1]")
    return (1.0 / frequency - 1.0) / 2.0


def confirmation_lift(p_single: float, correlation: float) -> float:
    """Probabilité conjointe de deux signaux corrélés — principe de confirmation.

    Le quatrième principe de Dow demande la confirmation d'un second indice.
    Sous un modèle gaussien à deux facteurs de corrélation `correlation`, la
    probabilité que deux signaux de seuil identique se produisent ensemble est
    donnée par la normale bivariée. La formule sert ici à un seul usage : voir
    de combien la confirmation *réduit* la fréquence d'occurrence, donc la
    taille d'échantillon disponible. Un filtre plus rare n'est pas un filtre
    meilleur — il est seulement plus difficile à valider.
    """
    if not 0.0 < p_single < 1.0:
        raise ValueError("p_single doit être dans ]0, 1[")
    if not -1.0 < correlation < 1.0:
        raise ValueError("correlation doit être dans ]−1, 1[")
    # Approximation de Drezner-Wesolowsky par quadrature de Gauss-Legendre.
    z = _inv_norm(1.0 - p_single)
    n = 96
    acc = 0.0
    for i in range(n):
        t = correlation * (i + 0.5) / n
        acc += (correlation / n) * math.exp(
            -(z * z) / (1.0 + t)) / (2.0 * math.pi * math.sqrt(1.0 - t * t))
    return p_single * p_single + acc


def _inv_norm(p: float) -> float:
    """Quantile normal, par bissection sur `norm_cdf` — précision suffisante ici."""
    lo, hi = -12.0, 12.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
