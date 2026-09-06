"""Le skew, et les trois nombres que trois pupitres appellent du même nom.

Onzième document de la série d'options, et le **troisième des onze à publier
le résultat de son propre test négatif** — après ceux du vanna et de
l'implicite. Le skew de put comme prédicteur, écrit-il, n'a pas survécu :
la corrélation de rang entre l'écart d'implicite put-call à vingt-cinq
deltas et l'amplitude réalisée de la séance suivante vaut **−0,014 sur 495
séances**, indiscernable de zéro. Et l'encadré qui suit est le meilleur des
onze documents : *ce n'est pas une preuve que le skew ne veut rien dire ; le
skew est excellent à ce qu'il est — une description du prix de la protection
de queue, maintenant. Ce n'est simplement pas une prévision de direction ni
d'amplitude à court horizon, et on le vend comme telle constamment.*

Le dépôt n'a rien à réfuter sur ce point. Il a trois choses à ajouter, et la
première est celle qui manque à tout résultat négatif publié.

I. Un résultat négatif sans sa puissance ne dit presque rien
---------------------------------------------------------------
Sur 495 séances, le seuil à quatre-vingt-quinze pour cent d'une corrélation
de rang vaut **0,088**. Le nombre publié en est à un sixième d'écart-type :
le test ne rejette rien, et — c'est le point — *il n'aurait pas non plus
détecté un effet de la taille qu'on cherche*. Établir une corrélation de
0,05, qui serait déjà un avantage considérable sur cet objet, demande 1 537
séances, soit six ans. **Le guide a raison de ne rien conclure ; ce qu'il
n'écrit pas est que son échantillon ne pouvait pas conclure autrement.** La
loi nulle est simulée ici et publie sa propre dispersion.

II. Les trois conventions ne mesurent pas le même objet
---------------------------------------------------------
Le guide en donne trois — risk reversal à vingt-cinq deltas, pente à
moneyness fixe, pente locale — et dit qu'elles sont toutes en usage et
toutes différentes. Elles le sont d'une façon qui se calcule. Les strikes à
vingt-cinq deltas se tiennent à `d₁ = ±0,6745`, donc le risk reversal sonde
une bande **proportionnelle à `σ√T`**, quand la convention à moneyness fixe
sonde une bande constante. *Deux pupitres qui publient « le skew » publient
deux nombres dont le rapport dépend de la volatilité et de l'échéance*, et
la partie chiffre ce rapport.

III. « Le skew s'aplatit avec le ténor » dépend de la convention
------------------------------------------------------------------
C'est le résultat de la partie, et il tombe d'une ligne d'algèbre. Si la
pente locale décroît comme `T^{−H}`, la pente à moneyness fixe décroît
comme `T^{−H}` aussi, mais le risk reversal se comporte comme
`T^{1/2−H}` — parce que sa bande s'élargit en `√T` pendant que la pente
s'aplatit. **Il ne décroît donc que si `H` dépasse un demi**, et à la valeur
que la littérature retient — la pente à la monnaie décroît en `1/√T` — son
exposant mesuré vaut **−0,02**, c'est-à-dire plat. Le décalage d'un demi
entre les deux exposants est stable à quatre millièmes sur toute la grille
de `H`, ce qui en fait un résultat et non une coïncidence de paramètres.
L'affirmation la plus consensuelle du document est vraie dans deux
conventions sur trois, et fausse dans celle du pupitre.

IV. Vendre du skew, c'est prendre une position directionnelle
----------------------------------------------------------------
Un risk reversal à vingt-cinq deltas porte un delta net d'environ un demi.
Le seuil de rentabilité de cette position se calcule comme celui de toutes
les autres de ce document, et la partie le publie : *l'objet par lequel on
prétend négocier la forme de la surface est, en delta, une position
directionnelle déguisée.*

V. Les trois forces, et laquelle est établissable
----------------------------------------------------
Le guide donne trois mécanismes avec, pour chacun, une conséquence
testable — ce qu'aucun des dix guides précédents n'avait fait. Le dépôt n'a
pas de données de marché et ne peut donc en tester aucune. Il peut faire
autre chose, et de plus utile : **calculer combien de séances chacune
demande**. Le verdict est un renversement — la force la plus citée est la
moins établissable, et l'écart entre les trois vaut deux ordres de grandeur.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from functools import lru_cache

from . import grandeurs as G
from . import implicite as I
from . import seuil
from . import theta as th
from . import vanna as va
from . import vega as vg
from . import volga as vo
from .costs import norm_cdf
from .report import Table, num

SEED = 20260906

S_REF = vo.S_REF
VOL_REF = vo.VOL_REF
TAUX = vo.TAUX
DIVIDENDE = vo.DIVIDENDE
JOURS_AN = vo.JOURS_AN
SEANCES_AN = I.SEANCES_AN

Z_95 = I.Z_95

#: Les trois nombres publiés par le guide sur son propre test, cités une
#: seule fois — comme les annonces des parties XV, XVII, XVIII et XXVIII.
TEST_PUBLIE: dict[str, float] = {
    "correlation": -0.014,
    "seances": 495.0,
}

#: Le `d₁` d'un strike à vingt-cinq deltas, en valeur absolue. `N(0,6745)`
#: vaut 0,75 : c'est le quartile de la loi normale, et c'est pour cela que
#: la convention de pupitre s'appelle « vingt-cinq deltas ».
D1_25 = 0.6744897501960817

#: La pente de la peau à la monnaie, en volatilité par unité de logarithme
#: de moneyness, à l'échéance de référence. Négative : c'est un indice
#: actions, et le guide le dit.
PENTE_REF = -0.35

#: L'échéance à laquelle `PENTE_REF` est déclarée, en jours.
TENOR_REF = 30.0

#: L'exposant d'aplatissement de la pente locale, `b(T) = b₀·T^{−H}`. **Il
#: n'est pas observable dans ce dépôt** et c'est le seul paramètre libre de
#: la partie : il est donc balayé partout où il décide d'un nombre. Un demi
#: est la valeur que la littérature retient, et c'est précisément celle où
#: le résultat de la partie III bascule.
H_REF = 0.5
H_GRILLE: tuple[float, ...] = (0.0, 0.25, 0.50, 0.75, 1.00)

#: La courbure de la peau, en volatilité par carré de logarithme de
#: moneyness. Elle ne change aucun résultat de la partie — tous portent sur
#: la pente — et elle est là pour que la surface ait une forme plausible.
COURBURE = 0.60


def _phi(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def call(s: float, k: float, vol: float, t: float) -> float:
    return th.call(s, max(k, 1e-12), max(vol, 1e-12), max(t, 1e-12),
                   TAUX, DIVIDENDE)


def forward(s: float, t: float) -> float:
    return s * math.exp((TAUX - DIVIDENDE) * t)


# ---------------------------------------------------------------------------
# I. La peau déclarée
# ---------------------------------------------------------------------------


def pente_locale(t: float, h: float = H_REF, pente: float = PENTE_REF) -> float:
    """`b(T) = b₀·(T/T₀)^{−H}` — la pente à la monnaie, par log-moneyness.

    L'exposant est **balayé et jamais choisi** : il n'est pas observable
    dans ce dépôt, et c'est lui qui décide du résultat de la partie.
    """
    return pente * (t / (TENOR_REF / JOURS_AN)) ** (-h)


def peau(k_log: float, t: float, h: float = H_REF,
         vol_atm: float = VOL_REF) -> float:
    """La volatilité implicite au logarithme de moneyness `k_log`.

    `σ(k, T) = σ_atm·(1 + b(T)·k + c(T)·k²)`, avec `k = ln(K/F)`. La forme
    est déclarée, elle n'est pas ajustée sur des données — le dépôt n'en a
    pas — et tout ce que la partie en tire est **invariant par changement de
    l'amplitude** de la courbure, ce qu'un test exige.

    La courbure porte **le même exposant d'aplatissement que la pente**, et
    le premier jet ne le faisait pas. La conséquence était mesurable et
    fausse : à grand `H` la pente d'un an devenait minuscule, la courbure y
    dominait l'aile, et le décalage d'un demi entre l'exposant du risk
    reversal et celui de la pente locale — le résultat de la partie — se
    dégradait de moitié. *Une surface où la pente s'aplatit et où la
    courbure reste ne décrit aucun marché ; elle décrit un modèle qu'on a
    écrit sans le relire.*
    """
    b = pente_locale(t, h)
    c = COURBURE * (t / (TENOR_REF / JOURS_AN)) ** (-h)
    return max(vol_atm * (1.0 + b * k_log + c * k_log * k_log), 1e-6)


def strike_de_moneyness(k_log: float, t: float, s: float = S_REF) -> float:
    return forward(s, t) * math.exp(k_log)


# ---------------------------------------------------------------------------
# II. Les trois conventions, et ce qui les sépare
# ---------------------------------------------------------------------------


def moneyness_du_delta(delta: float, t: float, h: float = H_REF,
                       vol_atm: float = VOL_REF, n_max: int = 200) -> float:
    """Le logarithme de moneyness d'un strike de delta donné, **sur la peau**.

    Il faut un point fixe : le delta dépend de la volatilité, qui dépend du
    strike, qui dépend du delta. La récurrence converge en quelques tours
    parce que la peau est douce ; on la borne tout de même.
    """
    s = S_REF
    k_log = 0.0
    for _ in range(n_max):
        vol = peau(k_log, t, h, vol_atm)
        k = strike_de_moneyness(k_log, t, s)
        d = G.delta_comptant(s, k, vol, t, TAUX, DIVIDENDE)
        if abs(d - delta) < 1e-12:
            break
        # Une descente amortie : le delta décroît avec le strike, donc on
        # déplace la moneyness dans le sens de l'erreur.
        k_log += 0.6 * (d - delta) / max(_phi(0.0) / (vol * math.sqrt(t)), 1e-9)
        k_log = max(min(k_log, 3.0), -3.0)
    return k_log


def risk_reversal(t: float, h: float = H_REF, delta: float = 0.25,
                  vol_atm: float = VOL_REF) -> float:
    """`IV(25Δ put) − IV(25Δ call)` — la convention du pupitre.

    Les deux strikes se déplacent avec le marché, ce qui rend la mesure
    stable quand le comptant dérive : c'est l'argument du guide, et il est
    juste. Ce qu'il n'écrit pas est que les strikes se déplacent aussi avec
    la **volatilité**, donc la bande sondée est proportionnelle à `σ√T`.
    """
    kc = moneyness_du_delta(delta, t, h, vol_atm)
    kp = moneyness_du_delta(1.0 - delta, t, h, vol_atm)
    return peau(kp, t, h, vol_atm) - peau(kc, t, h, vol_atm)


def risk_reversal_ferme(t: float, h: float = H_REF, delta: float = 0.25,
                        vol_atm: float = VOL_REF) -> float:
    """La forme fermée du même nombre, au premier ordre — **le contrôle**.

    Au premier ordre en la pente, les deux strikes tombent à
    `k = ∓d·σ√T + σ²T/2` avec `d = 0,6745`, la courbure s'annule par
    symétrie, et le risk reversal vaut `2·d·σ√T·|b|·σ_atm`. La route exacte
    résout le point fixe ; leur accord est ce qui autorise à publier
    l'exposant de la section suivante.
    """
    b = pente_locale(t, h)
    return -2.0 * D1_25 * vol_atm * math.sqrt(t) * b * vol_atm


def pente_moneyness_fixe(t: float, h: float = H_REF, bas: float = 0.90,
                         haut: float = 1.10,
                         vol_atm: float = VOL_REF) -> float:
    """`IV(90 %) − IV(110 %)` — la convention reproductible.

    Simple et refaisable depuis des données publiques, dit le guide, mais
    les strikes dérivent par rapport à la distribution quand la volatilité
    change. La bande sondée, elle, est **constante**, et c'est exactement ce
    qui la sépare de la précédente.
    """
    return (peau(math.log(bas), t, h, vol_atm)
            - peau(math.log(haut), t, h, vol_atm))


def pente_a_la_monnaie(t: float, h: float = H_REF,
                       vol_atm: float = VOL_REF, eps: float = 1e-5) -> float:
    """`∂σ/∂k` à la monnaie, par différence finie — la convention théorique.

    La plus propre en théorie et la plus bruitée en pratique, dit le guide,
    parce qu'elle dépend d'une dérivée ajustée. Ici elle est exacte, ce qui
    en fait la référence des deux autres.
    """
    return (peau(eps, t, h, vol_atm) - peau(-eps, t, h, vol_atm)) / (2.0 * eps)


def largeur_sondee(t: float, h: float = H_REF, delta: float = 0.25,
                   vol_atm: float = VOL_REF) -> float:
    """L'écart de log-moneyness entre les deux strikes du risk reversal.

    C'est le nombre qui explique tout le reste : il croît en `√T` et avec la
    volatilité, quand la bande de la convention à moneyness fixe vaut
    `ln(1,10/0,90)` quoi qu'il arrive.
    """
    return (moneyness_du_delta(delta, t, h, vol_atm)
            - moneyness_du_delta(1.0 - delta, t, h, vol_atm))


LARGEUR_FIXE = math.log(1.10 / 0.90)


def rapport_des_conventions(t: float, h: float = H_REF,
                            vol_atm: float = VOL_REF) -> float:
    """Le risk reversal rapporté à la pente à moneyness fixe.

    Un si les deux conventions mesuraient la même chose. Elles ne la
    mesurent pas, et ce rapport est ce qui les sépare : il vaut le rapport
    des deux bandes sondées, donc il croît en `√T` et avec la volatilité.
    """
    p = pente_moneyness_fixe(t, h, vol_atm=vol_atm)
    return math.inf if p == 0.0 else risk_reversal(t, h, vol_atm=vol_atm) / p


#: Les échéances balayées, en jours.
TENORS: tuple[float, ...] = (7.0, 30.0, 90.0, 180.0, 365.0)

#: Les volatilités à la monnaie balayées.
VOLS: tuple[float, ...] = (0.12, 0.20, 0.30, 0.45)


# ---------------------------------------------------------------------------
# III. L'exposant, et l'affirmation qui bascule dessus
# ---------------------------------------------------------------------------


def exposant_mesure(fonction, h: float = H_REF, t0: float = 14.0,
                    t1: float = 365.0, vol_atm: float = VOL_REF) -> float:
    """L'exposant local d'une convention en échéance, mesuré et non postulé.

    `d ln(mesure)/d ln T` entre deux ténors. La partie XVIII a payé pour la
    règle : un exposant se mesure, il ne s'écrit pas.
    """
    a = abs(fonction(t0 / JOURS_AN, h, vol_atm=vol_atm))
    b = abs(fonction(t1 / JOURS_AN, h, vol_atm=vol_atm))
    if a <= 0.0 or b <= 0.0:
        return 0.0
    return math.log(b / a) / math.log(t1 / t0)


def exposant_du_risk_reversal(h: float = H_REF,
                              vol_atm: float = VOL_REF) -> float:
    return exposant_mesure(lambda t, hh, vol_atm=VOL_REF:
                           risk_reversal(t, hh, vol_atm=vol_atm),
                           h, vol_atm=vol_atm)


def exposant_de_la_pente_fixe(h: float = H_REF,
                              vol_atm: float = VOL_REF) -> float:
    return exposant_mesure(lambda t, hh, vol_atm=VOL_REF:
                           pente_moneyness_fixe(t, hh, vol_atm=vol_atm),
                           h, vol_atm=vol_atm)


def exposant_de_la_pente_locale(h: float = H_REF,
                                vol_atm: float = VOL_REF) -> float:
    return exposant_mesure(lambda t, hh, vol_atm=VOL_REF:
                           pente_a_la_monnaie(t, hh, vol_atm=vol_atm),
                           h, vol_atm=vol_atm)


def h_du_basculement() -> float:
    """L'exposant au-delà duquel le risk reversal s'aplatit enfin.

    Un demi, exactement, et le calcul tient en une ligne : le risk reversal
    vaut la pente locale multipliée par une bande qui croît en `√T`, donc
    son exposant vaut `1/2 − H`. *À la valeur que la littérature retient, la
    mesure du pupitre est exactement constante en échéance.*
    """
    return 0.5


#: Le seuil au-delà duquel on accepte de dire qu'une convention s'aplatit.
#: Cinq centièmes d'exposant, et pas zéro : la route exacte porte le
#: portage et la courbure, qui décalent l'exposant de quelques centièmes
#: sans que rien ne s'aplatisse. *Un verdict posé sur un signe strict
#: bascule sur du bruit de second ordre.*
SEUIL_APLATISSEMENT = 0.05


def s_aplatit(convention, h: float, vol_atm: float = VOL_REF) -> bool:
    """Verdict calculé : la convention décroît-elle avec l'échéance ?"""
    return exposant_mesure(convention, h,
                           vol_atm=vol_atm) < -SEUIL_APLATISSEMENT


def decalage_des_exposants(h: float = H_REF,
                           vol_atm: float = VOL_REF) -> float:
    """L'écart entre l'exposant du risk reversal et celui de la pente locale.

    Un demi en théorie, et deux centièmes de moins à la mesure de
    référence — l'écart vient du portage et de la courbure, que la forme
    fermée du premier ordre néglige. Il croît avec la volatilité, et pour
    la raison qu'on attend : le premier ordre suppose une bande étroite, et
    la bande du risk reversal s'élargit avec `σ√T`. À douze pour cent de
    volatilité le décalage vaut un demi à trois dix-millièmes ; à
    quarante-cinq, il en manque un dixième. Ce qui en fait le résultat de la partie n'est pas sa
    valeur exacte mais sa **stabilité** : il ne bouge pas d'un centième sur
    toute la grille de `H`, ce qui le sépare d'une coïncidence de
    paramètres. La bande sondée croît en `√T` quelle que soit la vitesse à
    laquelle la pente s'aplatit.
    """
    return (exposant_du_risk_reversal(h, vol_atm)
            - exposant_de_la_pente_locale(h, vol_atm))


# ---------------------------------------------------------------------------
# IV. Le test du guide, sa loi nulle et sa puissance
# ---------------------------------------------------------------------------


def seuil_de_correlation(n: float, z: float = Z_95) -> float:
    """La corrélation de rang qu'il faut dépasser pour rejeter le hasard.

    `z/√(n−1)`, la loi de Fisher au premier ordre. C'est le nombre qui
    manque à tout résultat négatif publié sans lui : *sans le seuil, « nous
    n'avons rien trouvé » et « nous ne pouvions rien trouver » se lisent
    pareil.*
    """
    return z / math.sqrt(max(n - 1.0, 1.0))


#: Le nombre de séances sous lequel l'approximation de Fisher cesse de
#: valoir. La transformation est asymptotique ; à dix observations elle
#: rend un nombre qui a l'air d'une réponse et n'en est pas une. La table
#: publie donc une colonne qui dit **laquelle des deux bornes lie**.
SEANCES_MINIMALES = 30.0


def seances_pour_correlation(rho: float, z: float = Z_95) -> float:
    """Les séances qu'il faut pour établir une corrélation de `rho`.

    La transformation de Fisher, `n = (z/atanh ρ)² + 3`, et non son
    approximation au premier ordre : les deux coïncident pour les petites
    corrélations qui intéressent la partie, et divergent franchement pour
    les grosses — là où la question n'est de toute façon plus
    l'information mais la validité de l'approximation.
    """
    if rho == 0.0:
        return math.inf
    return (z / math.atanh(min(abs(rho), 0.999))) ** 2 + 3.0


def borne_de_l_approximation(rho: float) -> bool:
    """Vrai quand c'est la validité de l'approximation qui lie, pas l'information.

    Une corrélation de sept dixièmes « s'établit en une dizaine de
    séances » : le calcul est juste et la phrase ne l'est pas, parce qu'à
    dix observations la loi asymptotique n'a pas encore lieu. *Publier le
    nombre sans dire laquelle des deux bornes mord serait exactement le
    défaut que cette partie reproche au résultat négatif du guide.*
    """
    return seances_pour_correlation(rho) < SEANCES_MINIMALES


def annees_pour_correlation(rho: float) -> float:
    return seances_pour_correlation(rho) / SEANCES_AN


def ecarts_types_du_publie() -> float:
    """À combien d'écarts-types de zéro tombe le nombre que le guide publie."""
    n = TEST_PUBLIE["seances"]
    return TEST_PUBLIE["correlation"] / (seuil_de_correlation(n) / Z_95)


@lru_cache(maxsize=16)
def loi_nulle_du_test(n: int = 495, tirages: int = 4000) -> tuple[float, ...]:
    """La distribution de la corrélation de rang **sous absence totale de lien**.

    Deux séries indépendantes de `n` points, corrélation de Spearman, répété
    `tirages` fois. La forme fermée du seuil est contrôlée contre les
    quantiles de cette loi, et leur accord est ce qui autorise à publier la
    première — la règle du dépôt sur un onzième objet.
    """
    rng = random.Random(SEED + 17)
    out = []
    for _ in range(tirages):
        xs = [rng.random() for _ in range(n)]
        ys = [rng.random() for _ in range(n)]
        rx = _rangs(xs)
        ry = _rangs(ys)
        out.append(_pearson(rx, ry))
    return tuple(sorted(out))


def _rangs(xs: list[float]) -> list[float]:
    ordre = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    for position, i in enumerate(ordre):
        r[i] = float(position)
    return r


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    if sxx <= 0.0 or syy <= 0.0:
        return 0.0
    return sxy / math.sqrt(sxx * syy)


def quantile_de_la_loi_nulle(p: float, n: int = 495) -> float:
    loi = loi_nulle_du_test(n)
    i = min(len(loi) - 1, max(0, int(round(p * (len(loi) - 1)))))
    return loi[i]


def seuil_mesure(n: int = 495) -> float:
    """Le seuil bilatéral à quatre-vingt-quinze pour cent, **mesuré**."""
    return 0.5 * (abs(quantile_de_la_loi_nulle(0.025, n))
                  + quantile_de_la_loi_nulle(0.975, n))


#: Les corrélations qu'on pourrait vouloir établir, de la plus grosse à la
#: plus fine. Un dixième serait un avantage considérable sur cet objet.
CORRELATIONS: tuple[float, ...] = (0.20, 0.10, 0.05, 0.03, 0.014)


# ---------------------------------------------------------------------------
# V. Les trois régimes de collage, et le coût de se tromper
# ---------------------------------------------------------------------------


def pente_par_point(t: float, h: float = H_REF, s: float = S_REF,
                    vol_atm: float = VOL_REF) -> float:
    """`∂σ/∂S` sous le régime **sticky strike**, en volatilité par point.

    Quand le comptant monte d'un point sans que la surface bouge, un strike
    fixe voit sa moneyness baisser de `1/S` en logarithme, donc sa
    volatilité change de `−b/S`.
    """
    return -pente_locale(t, h) * vol_atm / s


@dataclass(frozen=True)
class Regime:
    """Un des trois régimes, et le delta qu'il donne."""
    nom: str
    facteur: float
    quand: str


#: Les trois régimes du guide, et le multiple de la pente que chacun
#: applique. Sticky delta translate la surface avec le comptant, donc un
#: strike fixe garde sa vol : la correction est nulle. Sticky strike laisse
#: le strike glisser le long du sourire. Sticky local vol double la pente,
#: et c'est le choix conservateur pour un livre court gamma.
REGIMES: tuple[Regime, ...] = (
    Regime("Sticky delta (moneyness)", 0.0,
           "marchés en tendance : le sourire suit le comptant"),
    Regime("Sticky strike", 1.0,
           "marchés calmes et sans direction"),
    Regime("Sticky local vol", 2.0,
           "le choix conservateur pour couvrir un livre court gamma"),
)


def delta_du_regime(regime: Regime, k: float, t: float, h: float = H_REF,
                    s: float = S_REF, vol_atm: float = VOL_REF) -> float:
    """`Δ + facteur·𝒱·∂σ/∂S` — le delta effectif sous un régime.

    **La correction porte le véga, pas le vanna**, et ce n'est pas un
    détail de notation : la partie XXIV a montré que la formule du guide du
    vanna nommait le mauvais grec et se trompait d'un facteur. Le résultat y
    est importé, non recopié.
    """
    k_log = math.log(k / forward(s, t))
    vol = peau(k_log, t, h, vol_atm)
    d = G.delta_comptant(s, k, vol, t, TAUX, DIVIDENDE)
    return d + regime.facteur * vg.vega(s, k, vol, t, TAUX,
                                        DIVIDENDE) * pente_par_point(
        t, h, s, vol_atm)


def ecart_des_regimes(k: float, t: float, h: float = H_REF,
                      s: float = S_REF, vol_atm: float = VOL_REF) -> float:
    """L'étendue des trois deltas, en points de delta."""
    ds = [delta_du_regime(r, k, t, h, s, vol_atm) for r in REGIMES]
    return 100.0 * (max(ds) - min(ds))


def etendue_a_la_monnaie_ferme(t: float, h: float = H_REF,
                               vol_atm: float = VOL_REF) -> float:
    """`2·φ(0)·σ·|b(T)|·√T·100` — l'étendue à la monnaie, en points de delta.

    Un seul `σ` et non deux : le véga porte le comptant et la pente par
    point le porte au dénominateur, donc il s'annule et il reste une seule
    volatilité. Le premier jet en écrivait deux et rendait le quart du
    nombre mesuré ; le contrôle contre la mesure l'a trouvé.

    Elle ne dépend **pas de l'échéance** à l'exposant que la littérature
    retient, et le mécanisme est exactement celui du reste de la partie : le
    véga croît en `√T`, la pente locale décroît en `T^{−H}`, et à `H = 1/2`
    les deux s'annulent. *L'erreur de régime, à la monnaie, coûte le même
    nombre de points de delta sur une hebdomadaire et sur une annuelle.*

    Une affirmation écrite d'avance disait que le sommet de la surface était
    aux échéances longues, où le véga est le plus grand ; la mesure l'a
    réfutée — la surface est plate à la monnaie, et ce qui monte avec
    l'échéance est l'aile, qui rattrape son retard.
    """
    return (2.0 * _phi(0.0) * vol_atm * abs(pente_locale(t, h))
            * math.sqrt(t) * 100.0)


def cout_du_mauvais_regime(k: float, t: float, h: float = H_REF,
                           s: float = S_REF, vol_atm: float = VOL_REF,
                           minutes: float = 390.0) -> float:
    """Ce que coûte une erreur de régime sur une séance, en points d'indice.

    L'erreur de delta multipliée par le déplacement moyen absolu du
    comptant, `√(2/π)·σ√Δt` — la constante de la partie XXV, importée. Le
    guide dit « plusieurs deltas sur chaque strike simultanément » et ne
    convertit pas ; le convertir est ce qui permet de le comparer à la
    friction déclarée.
    """
    dt = minutes / (JOURS_AN * 24.0 * 60.0)
    bouge = math.sqrt(2.0 / math.pi) * s * vol_atm * math.sqrt(dt)
    return 0.01 * ecart_des_regimes(k, t, h, s, vol_atm) * bouge


def cout_en_frictions(k: float, t: float, h: float = H_REF) -> float:
    """Le même coût, rapporté à la friction déclarée — **par option**."""
    return cout_du_mauvais_regime(k, t, h) / vo.FRICTION


def options_pour_une_friction(k: float, t: float, h: float = H_REF) -> float:
    """Combien d'options il faut pour qu'une erreur de régime coûte un aller-retour.

    C'est le nombre que le guide ne donne pas et qui rend sa phrase
    lisible. « Plusieurs deltas sur chaque strike simultanément » est exact
    par option — la mesure rend un peu plus d'un point et demi de delta —
    et **le coût d'une seule option est négligeable** : cinq centièmes de
    friction par séance. Une affirmation écrite d'avance dans ce module
    disait le contraire, et la mesure l'a réfutée.

    Ce qui rend la remarque du guide juste est qu'un pupitre ne tient pas
    une option : le mot « simultanément » de sa phrase porte tout le sens,
    et cette fonction le chiffre. Au-delà de cette taille de livre,
    l'erreur de régime coûte plus cher qu'un aller-retour complet par
    séance.
    """
    c = cout_en_frictions(k, t, h)
    return math.inf if c <= 0.0 else 1.0 / c


# ---------------------------------------------------------------------------
# VI. Le risk reversal est une position directionnelle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Position:
    """Un risk reversal, et ce qu'il porte réellement."""
    delta_net: float
    vega_net: float
    prime: float
    seuil_derive: float
    part_du_plancher: float


def delta_net_ferme(delta: float = 0.25) -> float:
    """`2δ` — le delta net d'un risk reversal, en forme fermée.

    Le put à `δ` deltas est le strike où le **call** en porte `1 − δ` ;
    vendre ce put ajoute `1 − (1 − δ) = δ` au delta, et acheter le call à
    `δ` en ajoute autant. Le delta net vaut donc exactement deux fois le
    delta de la convention, sans aucune dépendance à l'échéance, à la
    volatilité, au taux ni à la forme de la peau.

    *L'objet par lequel un pupitre prétend négocier la forme de la surface
    porte un delta que la surface ne touche pas.*
    """
    return 2.0 * delta


@lru_cache(maxsize=64)
def risk_reversal_position(t: float, h: float = H_REF, delta: float = 0.25,
                           s: float = S_REF,
                           vol_atm: float = VOL_REF) -> Position:
    """Acheter le call à vingt-cinq deltas, vendre le put du même delta.

    C'est l'objet par lequel un pupitre négocie « le skew ». Son véga net
    est nul par la parité que la partie XXIV a établie — le véga ne dépend
    de `d₁` que par une fonction **paire**, et les deux strikes ont des `d₁`
    opposés — mais **son delta net ne l'est pas** : il vaut la somme des
    deux deltas, soit un demi à vingt-cinq deltas.

    Le seuil de dérive est celui de tout le document : ce que le marché
    devrait porter, en points par heure, pour que la position couvre sa
    propre friction sur une séance.
    """
    kc = strike_de_moneyness(moneyness_du_delta(delta, t, h, vol_atm), t, s)
    kp = strike_de_moneyness(moneyness_du_delta(1.0 - delta, t, h, vol_atm),
                             t, s)
    vc = peau(math.log(kc / forward(s, t)), t, h, vol_atm)
    vp = peau(math.log(kp / forward(s, t)), t, h, vol_atm)
    dc = G.delta_comptant(s, kc, vc, t, TAUX, DIVIDENDE)
    dp = G.delta_comptant(s, kp, vp, t, TAUX, DIVIDENDE) - 1.0
    net = dc - dp
    veg = (vg.vega(s, kc, vc, t, TAUX, DIVIDENDE)
           - vg.vega(s, kp, vp, t, TAUX, DIVIDENDE))
    prime = call(s, kc, vc, t) - (call(s, kp, vp, t) - s
                                  * math.exp(-DIVIDENDE * t)
                                  + kp * math.exp(-TAUX * t))
    # Le seuil d'une position **sans barrière**, tenue jusqu'à la clôture :
    # `E[τ∧T]` vaut alors la séance entière, et le delta est supposé
    # constant sur elle. C'est une approximation, et elle va dans le sens
    # défavorable à l'argument — un delta qui bouge ne fait qu'ajouter du
    # risque à une position dont on dit déjà qu'elle en porte trop.
    heures = 6.5
    mu = vo.FRICTION / (net * heures) if net > 0.0 else math.inf
    plancher = seuil.PLAUSIBLE_DRIFT_PER_HOUR[0]
    return Position(net, veg / 100.0, prime, mu, mu / plancher)


# ---------------------------------------------------------------------------
# VII. Les trois forces, et laquelle est établissable
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Force:
    """Un des trois mécanismes du guide, et son budget d'information."""
    nom: str
    consequence: str
    effet: float
    unite: str
    seances: float


def forces() -> tuple[Force, ...]:
    """Les trois forces, chacune avec le nombre de séances qu'elle demande.

    Le guide fait ce qu'aucun des dix précédents n'avait fait : il donne,
    pour chaque mécanisme, une conséquence **testable**. Le dépôt n'a pas de
    données de marché et ne peut en tester aucune. Il peut chiffrer ce
    qu'elles coûteraient, et le classement qui en sort est un renversement :
    *la force que tout le monde cite en premier est la plus facile à
    établir, et celle sur laquelle repose l'argument économique du skew est
    la plus difficile.*

    Les tailles d'effet sont les valeurs communément citées, et chacune est
    déclarée ici plutôt qu'ajustée — le dépôt n'ajuste rien qu'il ne
    mesure.
    """
    return (
        Force("Levier et corrélation",
              "corrélation vol-rendement fortement négative",
              -0.70, "corrélation de rang",
              seances_pour_correlation(0.70)),
        Force("Prime de risque de crash",
              "la vente de puts gagne un excès de rendement",
              0.35, "ratio de Sharpe annuel",
              seances_pour_sharpe(0.35)),
        Force("Offre et demande",
              "le skew se raidit quand la demande de couverture monte",
              0.05, "corrélation de rang",
              seances_pour_correlation(0.05)),
    )


def seances_pour_sharpe(sharpe: float, z: float = Z_95) -> float:
    """Les séances qu'il faut pour distinguer un ratio de Sharpe de zéro.

    `(z/S)²` années, converties en séances. C'est la même identité que la
    partie XVI établissait pour l'unité d'observation, et elle rend ici le
    même service : *le nombre d'années ne dépend pas du pas de temps
    observé.*
    """
    return math.inf if sharpe == 0.0 else (z / sharpe) ** 2 * SEANCES_AN


def force_la_plus_chere() -> Force:
    return max(forces(), key=lambda f: f.seances)


def rapport_des_budgets() -> float:
    fs = [f.seances for f in forces()]
    return max(fs) / min(fs)


# ---------------------------------------------------------------------------
# VIII. Le décompte
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Affirmation:
    enonce: str
    grandeur: str
    verdict: str


def affirmations() -> tuple[Affirmation, ...]:
    t30 = 30.0 / JOURS_AN
    p = risk_reversal_position(t30)
    return (
        Affirmation(
            "Le skew n'est pas une erreur de prix : c'est le marché disant "
            "que les rendements ne sont pas lognormaux, et disant comment",
            "rien",
            "**exact, et c'est la meilleure phrase des onze guides** — elle "
            "fait du skew un prix, ce qu'il est, et non une prévision"),
        Affirmation(
            "Trois conventions, toutes en usage, toutes différentes",
            "le risque",
            "**sous-estimé** : le risk reversal sonde une bande "
            "proportionnelle à sigma racine T, l'autre une bande fixe, et "
            "leur rapport vaut " + num(rapport_des_conventions(t30), 2)
            + " à trente jours contre "
            + num(rapport_des_conventions(365.0 / JOURS_AN), 2) + " à un an"),
        Affirmation(
            "Le skew s'aplatit avec le ténor",
            "l'horloge",
            "**vrai dans deux conventions sur trois** : l'exposant du risk "
            "reversal vaut un demi moins H, donc il ne décroît qu'au-delà "
            "de H = 0,5 — et à cette valeur il est exactement constant"),
        Affirmation(
            "Le risk reversal à vingt-cinq deltas est le standard de "
            "pupitre parce que ses strikes suivent le marché",
            "le risque",
            "exact du comptant, **et faux de la volatilité** : les mêmes "
            "strikes suivent aussi la volatilité, ce qui fait varier la "
            "bande sondée d'un facteur " + num(
                largeur_sondee(t30, vol_atm=0.45)
                / largeur_sondee(t30, vol_atm=0.12), 1) + " sur la plage"),
        Affirmation(
            "Le skew de put comme prédicteur n'a pas survécu à notre "
            "test : −0,014 sur 495 séances",
            "rien",
            "**c'est le troisième des onze guides à publier son propre "
            "résultat négatif** — et le seuil de ce test vaut "
            + num(seuil_de_correlation(TEST_PUBLIE["seances"]), 3)
            + ", donc l'échantillon ne pouvait pas conclure autrement"),
        Affirmation(
            "Ce n'est pas une preuve que le skew ne veut rien dire : il "
            "décrit le prix de la protection de queue, maintenant",
            "rien",
            "**exact, et c'est la thèse de ce document** : un prix n'est pas "
            "une prévision, et le confondre est l'erreur que les onze "
            "guides examinent chacun à sa façon"),
        Affirmation(
            "Choisir le mauvais régime de collage ne produit pas une petite "
            "erreur : plusieurs deltas sur chaque strike simultanément",
            "le risque",
            "exact **par option** — "
            + num(ecart_des_regimes(strike_de_moneyness(-0.05, t30), t30), 1)
            + " points de delta à cinq pour cent sous la monnaie — et le "
            "mot « simultanément » porte tout le sens : une option seule "
            "coûte "
            + num(cout_en_frictions(strike_de_moneyness(-0.05, t30), t30), 3)
            + " friction par séance, et il en faut "
            + num(options_pour_une_friction(
                strike_de_moneyness(-0.05, t30), t30), 0)
            + " pour en coûter une"),
        Affirmation(
            "Sticky local vol est le choix conservateur pour un livre court "
            "gamma",
            "le risque",
            "exact : c'est le régime dont la correction est la plus grande, "
            "donc celui qui surcouvre — et surcouvrir un livre court gamma "
            "est l'erreur la moins chère des deux"),
        Affirmation(
            "Trois forces produisent le skew, et elles ne s'excluent pas",
            "rien",
            "**c'est le seul des onze guides à donner une conséquence "
            "testable par mécanisme** — et leurs budgets d'information "
            "diffèrent d'un facteur " + num(rapport_des_budgets(), 0)),
    )


def compte_par_grandeur() -> dict[str, int]:
    out: dict[str, int] = {}
    for a in affirmations():
        out[a.grandeur] = out.get(a.grandeur, 0) + 1
    return out


def familles() -> tuple[tuple[str, int], ...]:
    return I.familles() + (("Skew, partie XXIX", len(affirmations())),)


# ---------------------------------------------------------------------------
# IX. Les tables
# ---------------------------------------------------------------------------


def _pc(x: float, n: int = 1) -> str:
    return num(100.0 * x, n)


def table_conventions() -> Table:
    rows = []
    for jours in TENORS:
        t = jours / JOURS_AN
        rows.append([
            num(jours, 0),
            num(100.0 * risk_reversal(t), 3),
            num(100.0 * risk_reversal_ferme(t), 3),
            num(100.0 * pente_moneyness_fixe(t), 3),
            num(100.0 * pente_a_la_monnaie(t), 2),
            num(largeur_sondee(t), 3),
            num(rapport_des_conventions(t), 2),
        ])
    return Table(
        "sk_conventions",
        "Trois conventions, trois nombres, et le rapport qui les sépare",
        ["Jours", "Risk reversal 25Δ", "Sa forme fermée",
         "Pente 90/110", "Pente locale", "Bande sondée",
         "Rapport des deux premières"],
        rows,
        wide=True,
        note="Le guide donne les trois conventions et dit qu'elles sont "
             "toutes en usage et toutes différentes. Elles le sont d'une "
             "façon qui se calcule. Les strikes à vingt-cinq deltas se "
             "tiennent à `d₁ = ±0,6745` — le quartile de la loi normale, "
             "d'où le nom de la convention — donc le risk reversal sonde "
             "une bande **proportionnelle à `σ√T`**, quand la convention à "
             "moneyness fixe en sonde une constante de "
             + num(LARGEUR_FIXE, 3) + ". La colonne de la forme fermée "
             "contrôle la route exacte, qui résout un point fixe : le delta "
             "dépend de la volatilité, qui dépend du strike, qui dépend du "
             "delta. *Deux pupitres qui publient « le skew » publient deux "
             "nombres dont le rapport dépend de l'échéance*, et la dernière "
             "colonne dit de combien.")


def table_vol() -> Table:
    rows = []
    t = 30.0 / JOURS_AN
    for vol in VOLS:
        rows.append([
            _pc(vol, 0),
            num(100.0 * risk_reversal(t, vol_atm=vol), 3),
            num(100.0 * pente_moneyness_fixe(t, vol_atm=vol), 3),
            num(largeur_sondee(t, vol_atm=vol), 3),
            num(rapport_des_conventions(t, vol_atm=vol), 2),
        ])
    return Table(
        "sk_vol",
        "La même mesure, à quatre niveaux de volatilité",
        ["Volatilité à la monnaie (%)", "Risk reversal 25Δ",
         "Pente 90/110", "Bande sondée", "Rapport"],
        rows,
        note="Le guide défend le risk reversal parce que ses strikes se "
             "déplacent avec le marché, ce qui rend la mesure stable quand "
             "le comptant dérive. L'argument est juste et **incomplet** : "
             "les mêmes strikes se déplacent aussi avec la volatilité, donc "
             "la bande sondée varie d'un facteur "
             + num(largeur_sondee(t, vol_atm=VOLS[-1])
                   / largeur_sondee(t, vol_atm=VOLS[0]), 1)
             + " sur cette plage, et le risk reversal avec elle — à peau "
             "rigoureusement inchangée. *La convention qu'on choisit pour "
             "être insensible au comptant est la plus sensible à la "
             "volatilité*, et un skew qui « se raidit » peut n'être qu'une "
             "volatilité qui monte.")


def table_exposant() -> Table:
    rows = []
    for h in H_GRILLE:
        rr = exposant_du_risk_reversal(h)
        fixe = exposant_de_la_pente_fixe(h)
        loc = exposant_de_la_pente_locale(h)
        rows.append([
            num(h, 2),
            num(rr, 3), num(fixe, 3), num(loc, 3), num(rr - loc, 3),
            "oui" if rr < -SEUIL_APLATISSEMENT else "non",
            "oui" if fixe < -SEUIL_APLATISSEMENT else "non",
        ])
    return Table(
        "sk_exposant",
        "« Le skew s'aplatit avec le ténor » — dans quelle convention ?",
        ["H déclaré", "Exposant du risk reversal", "De la pente 90/110",
         "De la pente locale", "Décalage", "Le RR s'aplatit",
         "La pente s'aplatit"],
        rows,
        wide=True,
        note="C'est le résultat de la partie, et il tient en une ligne "
             "d'algèbre. Le risk reversal vaut la pente locale multipliée "
             "par une bande qui croît en `√T`, donc son exposant vaut "
             "`1/2 − H` quand celui des deux autres conventions vaut `−H`. "
             "**Il ne s'aplatit donc qu'au-delà de H = 0,5**, et à cette "
             "valeur — celle que la littérature retient, la pente à la "
             "monnaie décroissant en `1/√T` — son exposant mesuré vaut "
             "deux centièmes, c'est-à-dire plat. La colonne du décalage "
             "est ce qui fait de ce résultat autre chose qu'une "
             "coïncidence de paramètres : elle ne bouge pas d'un centième "
             "sur toute la grille, et vaut un demi en théorie contre "
             + num(decalage_des_exposants(), 3) + " à la mesure, l'écart "
             "venant du portage et de la courbure. "
             "Les deux dernières colonnes sont des verdicts calculés, "
             "jamais écrits. L'affirmation la plus consensuelle du document "
             "est donc vraie dans deux conventions sur trois et fausse dans "
             "celle du pupitre, et rien dans la façon dont on l'énonce ne "
             "dit laquelle. *C'est la question de la partie XXIII — quelle "
             "variable tient-on fixe — posée sur un cinquième objet.*")


def table_puissance() -> Table:
    rows = []
    for rho in CORRELATIONS:
        n = seances_pour_correlation(rho)
        rows.append([
            num(rho, 3),
            num(max(n, SEANCES_MINIMALES), 0),
            num(max(n, SEANCES_MINIMALES) / SEANCES_AN, 2),
            "l'approximation" if borne_de_l_approximation(rho)
            else "l'information",
            "oui" if abs(rho) > seuil_de_correlation(
                TEST_PUBLIE["seances"]) else "non",
        ])
    return Table(
        "sk_puissance",
        "Ce que l'échantillon du guide pouvait détecter, et ce qu'il ne "
        "pouvait pas",
        ["Corrélation à établir", "Séances requises", "Années",
         "Ce qui lie", "Détectable en 495 séances"],
        rows,
        note="Le guide publie un résultat négatif honnête : la corrélation "
             "de rang entre l'écart d'implicite put-call à vingt-cinq "
             "deltas et l'amplitude réalisée de la séance suivante vaut "
             + num(TEST_PUBLIE["correlation"], 3) + " sur "
             + num(TEST_PUBLIE["seances"], 0) + " séances, indiscernable de "
             "zéro. Il ne publie pas le nombre qui rend ce résultat "
             "lisible : le seuil à quatre-vingt-quinze pour cent, qui vaut "
             + num(seuil_de_correlation(TEST_PUBLIE["seances"]), 3)
             + ". Le nombre observé en est à "
             + num(abs(ecarts_types_du_publie()), 2) + " écart-type. **Sans "
             "le seuil, « nous n'avons rien trouvé » et « nous ne pouvions "
             "rien trouver » se lisent pareil**, et la dernière colonne dit "
             "lequel des deux s'applique : sur cet échantillon, un avantage "
             "de cinq centièmes — qui serait considérable sur cet objet — "
             "serait passé inaperçu. C'est le budget d'information de la "
             "partie IV, rencontré sur un onzième objet.")


def table_loi_nulle() -> Table:
    rows = []
    for n in (120, 252, 495, 1000, 2520):
        rows.append([
            num(n, 0),
            num(seuil_de_correlation(n), 4),
            num(seuil_mesure(n), 4),
            num(quantile_de_la_loi_nulle(0.50, n), 4),
            num(n / SEANCES_AN, 1),
        ])
    return Table(
        "sk_loi_nulle",
        "La loi nulle d'une corrélation de rang, simulée et en forme fermée",
        ["Séances", "Seuil de Fisher", "Seuil mesuré", "Médiane simulée",
         "Années"],
        rows,
        note="Quatre mille tirages de deux séries indépendantes, "
             "corrélation de rang de Spearman, et les quantiles de la loi "
             "obtenue. La forme fermée `z/√(n−1)` est contrôlée contre la "
             "mesure : les deux colonnes se referment partout, ce qui "
             "autorise à publier la première. La médiane simulée tombe sur "
             "zéro, ce qui est la définition d'une loi nulle et se vérifie "
             "plutôt qu'il ne se suppose. *Un résultat négatif publié sans "
             "sa loi nulle demande au lecteur de croire que l'auteur "
             "connaissait la sienne.*")


def table_regimes() -> Table:
    rows = []
    t = 30.0 / JOURS_AN
    for km in (-0.10, -0.05, 0.0, 0.05, 0.10):
        k = strike_de_moneyness(km, t)
        ds = [delta_du_regime(r, k, t) for r in REGIMES]
        rows.append([
            num(math.exp(km), 3),
            num(ds[0], 4), num(ds[1], 4), num(ds[2], 4),
            num(ecart_des_regimes(k, t), 2),
            num(cout_en_frictions(k, t), 4),
            num(options_pour_une_friction(k, t), 0),
        ])
    return Table(
        "sk_regimes",
        "Le même strike, trois régimes de collage, trois deltas",
        ["K/F", "Sticky delta", "Sticky strike", "Sticky local vol",
         "Étendue (points de delta)", "Frictions par option",
         "Options pour une friction"],
        rows,
        wide=True,
        note="Le guide écrit que choisir le mauvais régime ne produit pas "
             "une petite erreur mais plusieurs deltas sur chaque strike "
             "simultanément. C'est exact, et le convertir est ce qui permet "
             "de le comparer à quelque chose : l'erreur de delta "
             "multipliée par le déplacement moyen absolu d'une séance — "
             "`√(2/π)·σ√Δt`, la constante de la partie XXV, importée et non "
             "recopiée — donne un coût en points d'indice, puis en "
             "frictions déclarées **par option**. Une affirmation écrite "
             "d'avance dans ce module disait que le coût dépassait la "
             "friction, et la mesure l'a réfutée : une option seule en "
             "coûte quelques centièmes. Ce qui rend la remarque du guide "
             "juste est le mot *simultanément* — un pupitre ne tient pas "
             "une option — et la dernière colonne le chiffre : au-delà "
             "d'une trentaine de contrats sur le même strike, l'erreur de "
             "régime coûte plus qu'un aller-retour complet par séance. "
             "**La correction porte le véga et non le "
             "vanna**, et ce n'est pas une question de notation : la partie "
             "XXIV a montré que la formule usuelle nomme le mauvais grec et "
             "se trompe d'un facteur. Le résultat en est importé.")


def table_position() -> Table:
    rows = []
    for jours in TENORS:
        t = jours / JOURS_AN
        p = risk_reversal_position(t)
        rows.append([
            num(jours, 0),
            num(p.delta_net, 3),
            num(p.vega_net, 6),
            num(p.prime, 3),
            num(p.seuil_derive, 3),
            num(p.part_du_plancher, 2),
        ])
    return Table(
        "sk_position",
        "Ce qu'un risk reversal porte réellement",
        ["Jours", "Delta net", "Véga net (par point)", "Prime nette",
         "Dérive requise (pt/h)", "En part du plancher plausible"],
        rows,
        wide=True,
        note="C'est l'objet par lequel un pupitre négocie « le skew » : "
             "acheter le call à vingt-cinq deltas, vendre le put du même "
             "delta. Son véga net est **nul par parité** — le véga ne "
             "dépend de `d₁` que par une fonction paire et les deux strikes "
             "ont des `d₁` opposés, ce que la partie XXIV a établi — donc "
             "la position ne porte rien de ce qu'elle prétend négocier au "
             "premier ordre en volatilité. Ce qu'elle porte est un **delta "
             "net d'un demi**. La dérive requise est celle de tout ce "
             "document, `µ* = c/E[τ∧T]`, et la dernière colonne la rapporte "
             "au **plancher** du domaine plausible, et c'est là que la "
             "table devient un avertissement : le seuil tombe *sous* le "
             "plancher, donc la position paierait à la plus faible dérive "
             "que ce document juge plausible. Ce n'est pas une bonne "
             "nouvelle. *L'objet par lequel un pupitre prétend négocier la "
             "forme de la surface est, en delta, une position "
             "directionnelle — et la seule de ce document dont le seuil "
             "passe sous le plancher, parce qu'elle ne porte aucune "
             "barrière et achète donc la séance entière.*")


def table_forces() -> Table:
    rows = []
    for f in sorted(forces(), key=lambda x: x.seances):
        rows.append([
            f.nom, f.consequence, num(abs(f.effet), 2), f.unite,
            num(max(f.seances, SEANCES_MINIMALES), 0),
            num(max(f.seances, SEANCES_MINIMALES) / SEANCES_AN, 1),
        ])
    return Table(
        "sk_forces",
        "Les trois forces, et ce que chacune coûte à établir",
        ["La force", "La conséquence testable", "Taille d'effet",
         "Unité", "Séances requises", "Années"],
        rows,
        wrap_cols=[0, 1, 3],
        wide=True,
        note="Ce onzième guide fait ce qu'aucun des dix précédents n'avait "
             "fait : il donne, pour chaque mécanisme, une conséquence "
             "**testable**. Le dépôt n'a pas de données de marché et ne "
             "peut en tester aucune ; il peut chiffrer ce qu'elles "
             "coûteraient, et le classement est un renversement. La force "
             "que tout le monde cite en premier — le levier — est la plus "
             "facile à établir, parce que son effet est énorme — et si "
             "facile que ce n'est plus l'information qui la borne mais la "
             "validité de l'approximation, ce que la colonne des séances "
             "dit en s'arrêtant au plancher déclaré. Celle sur "
             "laquelle repose l'argument économique du skew, la prime de "
             "crash, demande "
             + num(forces()[1].seances / SEANCES_AN, 1) + " ans. Et « "
             + force_la_plus_chere().nom.lower() + " », le mécanisme que le "
             "guide donne comme le plus visible au quotidien, en demande "
             + num(force_la_plus_chere().seances / SEANCES_AN, 0) + " — un "
             "facteur " + num(rapport_des_budgets(), 0) + " entre les deux "
             "bouts, et le vrai facteur est plus grand encore puisque le "
             "premier est plafonné par son plancher. *Les tailles d'effet sont déclarées et non ajustées : "
             "le dépôt n'ajuste rien qu'il ne mesure.*")


def table_reste() -> Table:
    rows = [[a.enonce, a.grandeur, a.verdict] for a in affirmations()]
    c = compte_par_grandeur()
    return Table(
        "sk_reste",
        "Neuf affirmations, et le décompte des onze parties d'options",
        ["L'affirmation", "Ce qu'elle déplace", "Ce que la mesure en dit"],
        rows,
        wrap_cols=[0, 2],
        note=num(c.get("le risque", 0), 0) + " affirmations déplacent le "
             "risque, " + num(c.get("l'horloge", 0), 0) + " l'horloge, "
             + num(c.get("rien", 0), 0) + " rien, **aucune la direction** — "
             "huitième partie consécutive dans ce cas. Sur les "
             + num(sum(n for _, n in familles()), 0) + " affirmations des "
             "onze parties consacrées aux options, aucune ne donne un sens. "
             "Ce onzième guide est le troisième des onze à publier le "
             "résultat de son propre test négatif, et le seul des trois à "
             "expliquer *pourquoi* le résultat négatif ne condamne pas "
             "l'objet : le skew est un prix, pas une prévision, et le "
             "vendre comme une prévision est une erreur de catégorie. "
             "**C'est la thèse de la quatrième partie de ce document, "
             "formulée sur un onzième objet par un praticien qui n'avait "
             "aucune raison de la formuler.**")


def all_tables() -> dict[str, Table]:
    return {t.key: t for t in (
        table_conventions(), table_vol(), table_exposant(),
        table_puissance(), table_loi_nulle(), table_regimes(),
        table_position(), table_forces(), table_reste(),
    )}


# ---------------------------------------------------------------------------
# X. Les surfaces
# ---------------------------------------------------------------------------

#: Le maximum va au fond, donc chaque liste est écrite dans l'ordre qui l'y
#: met — et l'ordre n'est pas le même d'une surface à l'autre, parce que
#: leurs maxima ne sont pas au même bout.
SURF_JOURS: tuple[float, ...] = (365.0, 180.0, 90.0, 45.0, 21.0, 7.0)
SURF_JOURS_INVERSE: tuple[float, ...] = (7.0, 21.0, 45.0, 90.0, 180.0, 365.0)
#: Deux ordres de volatilité, et l'ordre n'est pas le même parce que les
#: deux surfaces ont leur maximum aux deux bouts : le rapport des
#: conventions croît avec la volatilité, l'exposant du risk reversal
#: décroît avec elle. La règle du maximum au fond se lit donc à l'envers
#: d'une surface à l'autre.
SURF_VOLS: tuple[float, ...] = (0.45, 0.36, 0.28, 0.21, 0.15, 0.10)
SURF_VOLS_EXPOSANT: tuple[float, ...] = (0.10, 0.15, 0.21, 0.28, 0.36, 0.45)
SURF_H: tuple[float, ...] = (0.0, 0.25, 0.50, 0.75, 1.00, 1.25)
#: L'axe de moneyness part de la monnaie et s'en éloigne : l'étendue des
#: trois régimes y est maximale, parce que le véga l'est, et une grille
#: centrée sur la monnaie mettrait sa crête au milieu de la surface.
SURF_MONEYNESS: tuple[float, ...] = (0.0, -0.03, -0.06, -0.09, -0.12, -0.15)
SURF_RHO: tuple[float, ...] = (0.18, 0.10, 0.06, 0.035, 0.02, 0.012)
SURF_SEANCES: tuple[float, ...] = (4000.0, 2000.0, 1000.0, 495.0, 252.0,
                                   120.0)


def surface_rapport() -> list[list[float]]:
    """Le rapport des deux conventions, en échéance et en volatilité."""
    return [[rapport_des_conventions(j / JOURS_AN, vol_atm=v)
             for v in SURF_VOLS] for j in SURF_JOURS]


def surface_exposant() -> list[list[float]]:
    """L'exposant du risk reversal, en H et en volatilité."""
    return [[exposant_du_risk_reversal(h, vol_atm=v)
             for v in SURF_VOLS_EXPOSANT] for h in SURF_H]


def surface_regimes() -> list[list[float]]:
    """L'étendue des trois deltas, en échéance et en moneyness."""
    return [[ecart_des_regimes(strike_de_moneyness(m, j / JOURS_AN),
                               j / JOURS_AN)
             for m in SURF_MONEYNESS] for j in SURF_JOURS_INVERSE]


def surface_puissance() -> list[list[float]]:
    """La part du seuil qu'un effet atteint, en séances et en taille d'effet.

    Non plafonnée : un plafond ferait un plateau d'ex æquo au sommet, et le
    dépôt a déjà payé cette leçon deux fois — partie XXVIII sur la surface
    du pas de cotation, et ici sur la première version de celle-ci.
    """
    return [[abs(r) / seuil_de_correlation(n) for r in SURF_RHO]
            for n in SURF_SEANCES]


# ---------------------------------------------------------------------------
# XI. Les valeurs du gabarit
# ---------------------------------------------------------------------------


def values() -> dict[str, str]:
    t30 = 30.0 / JOURS_AN
    t365 = 365.0 / JOURS_AN
    p = risk_reversal_position(t30)
    k5 = strike_de_moneyness(-0.05, t30)
    return {
        "sk_rr_30": num(100.0 * risk_reversal(t30), 2),
        "sk_rr_365": num(100.0 * risk_reversal(t365), 2),
        "sk_pente_30": num(100.0 * pente_moneyness_fixe(t30), 2),
        "sk_locale_30": num(100.0 * pente_a_la_monnaie(t30), 2),
        "sk_bande_30": num(largeur_sondee(t30), 3),
        "sk_bande_fixe": num(LARGEUR_FIXE, 3),
        "sk_rapport_30": num(rapport_des_conventions(t30), 2),
        "sk_rapport_365": num(rapport_des_conventions(t365), 2),
        "sk_bande_vol": num(largeur_sondee(t30, vol_atm=0.45)
                            / largeur_sondee(t30, vol_atm=0.12), 1),
        "sk_h": num(H_REF, 2),
        "sk_h_bascule": num(h_du_basculement(), 1),
        "sk_expo_rr": num(exposant_du_risk_reversal(), 3),
        "sk_expo_fixe": num(exposant_de_la_pente_fixe(), 3),
        "sk_expo_locale": num(exposant_de_la_pente_locale(), 3),
        "sk_decalage": num(decalage_des_exposants(), 3),
        "sk_decalage_min": num(min(decalage_des_exposants(h)
                                   for h in H_GRILLE), 3),
        "sk_decalage_max": num(max(decalage_des_exposants(h)
                                   for h in H_GRILLE), 3),
        "sk_test_rho": num(TEST_PUBLIE["correlation"], 3),
        "sk_test_n": num(TEST_PUBLIE["seances"], 0),
        "sk_seuil": num(seuil_de_correlation(TEST_PUBLIE["seances"]), 3),
        "sk_seuil_mesure": num(seuil_mesure(495), 3),
        "sk_ecarts_types": num(abs(ecarts_types_du_publie()), 2),
        "sk_seances_005": num(seances_pour_correlation(0.05), 0),
        "sk_annees_005": num(annees_pour_correlation(0.05), 1),
        "sk_delta_net": num(p.delta_net, 3),
        "sk_delta_net_10": num(delta_net_ferme(0.10), 2),
        "sk_delta_net_40": num(delta_net_ferme(0.40), 2),
        "sk_vega_net": num(p.vega_net, 6),
        "sk_derive_rr": num(p.seuil_derive, 2),
        "sk_part_plancher": num(p.part_du_plancher, 2),
        "sk_etendue_5": num(ecart_des_regimes(k5, t30), 1),
        "sk_etendue_atm_7": num(
            ecart_des_regimes(strike_de_moneyness(0.0, 7.0 / JOURS_AN),
                              7.0 / JOURS_AN), 2),
        "sk_etendue_atm_an": num(
            ecart_des_regimes(strike_de_moneyness(0.0, 1.0), 1.0), 2),
        "sk_cout_5": num(cout_en_frictions(k5, t30), 3),
        "sk_options_5": num(options_pour_une_friction(k5, t30), 0),
        "sk_force_chere": force_la_plus_chere().nom.lower(),
        "sk_force_annees": num(force_la_plus_chere().seances / SEANCES_AN, 0),
        "sk_rapport_budgets": num(rapport_des_budgets(), 0),
        "sk_affirmations": num(len(affirmations()), 0),
        "sk_total_options": num(sum(n for _, n in familles()), 0),
        "sk_pente_ref": num(PENTE_REF, 2),
        "sk_d1": num(D1_25, 4),
    }


def main() -> None:
    for t in all_tables().values():
        print(t.key, "—", t.caption)
    for k, v in values().items():
        print(f"  {k} = {v}")


if __name__ == "__main__":
    main()
