"""Ce qu'un fonds sans opérateur fait, et ce qui en reste à un seul homme.

Le cas examiné
--------------
Un fonds quantitatif de référence n'embauche aucun opérateur de marché. Trois
nombres le concernant circulent largement : un rendement brut annualisé
d'environ deux tiers sur une trentaine d'années, avancé par une étude
académique ; une part de transactions gagnantes « d'un peu plus de la
moitié », rapportée par un livre d'enquête sous la forme d'une phrase de l'un
de ses dirigeants ; et une capacité plafonnée à une dizaine de milliards de
dollars, largement commentée.

Ces nombres sont repris **tels quels**, comme des données à expliquer et non
comme des résultats à défendre — exactement la posture de la partie XV. La
question posée n'est jamais « sont-ils vrais ? » mais : *que faut-il pour
qu'ils le soient, et lequel de ces prérequis un opérateur seul possède-t-il ?*

Ce que la loi fondamentale dit, et ce qu'elle ne dit pas
--------------------------------------------------------
La relation de Grinold, `IR = IC·√N`, gouverne tout : la qualité d'un
gestionnaire est le produit de la finesse de sa prévision par la racine du
nombre de paris indépendants qu'il prend. Elle est presque toujours citée à
l'envers. Elle ne dit **pas** qu'un grand nombre de transactions rend la
preuve plus facile — le nombre d'années requis pour établir un ratio
d'information donné ne dépend pas de `N`, comme la partie XVI l'a montré sur
une autre route. Elle dit que la **fraction d'information par décision**
devient minuscule, et donc plausible.

C'est tout le retournement. Un opérateur à deux décisions par séance qui vise
un ratio d'information de deux doit avoir raison dans une proportion
franchement visible des cas — une exigence qu'aucun marché liquide ne laisse
survivre. Le même ratio, à dix mille décisions par séance, ne demande qu'un
écart au hasard de quelques centièmes de point, invisible, incontesté, et
défendable. **L'ampleur ne facilite pas la démonstration : elle rend
l'hypothèse crédible.**

Les quatre pratiques, et celles qui transfèrent
-----------------------------------------------
*L'ampleur.* Ne transfère pas : elle exige une infrastructure, pas une
opinion. Le module chiffre le seuil de décisions annuelles au-dessous duquel
l'exigence cesse d'être crédible, et il tombe autour de dix par séance.

*La combinaison de signaux faibles.* Transfère mal, et pour une raison qui
n'est pas le talent : le plafond d'un panier de lectures est fixé par leur
**corrélation**, pas par leur nombre. Quinze lectures corrélées à quinze
pour cent ne valent pas quinze fois une lecture, ni même quatre — elles en
valent un peu plus de deux, et le reste du panier ne sert à rien.

*La capacité.* Transfère, et c'est le seul terrain où l'opérateur seul est
**structurellement supérieur**. L'impact de marché croît en racine de la
taille ; à un contrat, il est de deux centièmes de point quand la friction en
vaut un tiers. Le fonds paie une taxe que l'opérateur ne paie pas, et cette
taxe est ce qui plafonne sa capacité.

*L'exécution.* Transfère entièrement, et c'est le levier le plus mal employé.
Passer d'une entrée agressive à une entrée passive retire un spread complet
de `c`, donc divise `µ*` d'autant. Sous prix sans dérive, ce gain est
**intégral** : les ordres non remplis ne coûtent rien, ils réduisent
seulement le nombre d'occasions, et le document a déjà chiffré ce que coûte
de diviser un échantillon. Ce qui peut le reprendre est la sélection adverse,
qui n'existe pas dans la loi nulle — et le module calcule la dérive adverse
exacte qui annulerait le gain, pour qu'on sache ce qu'il faudrait mesurer.

Ce que la partie ne fait pas
----------------------------
Elle ne prétend pas décrire des méthodes propriétaires que personne n'a
publiées. Elle prend les nombres publics, en déduit ce qu'ils exigent, et
sépare par un verdict **calculé** ce qu'un opérateur seul peut exercer de ce
qu'il ne peut pas. Le résultat est celui de tout le document : trois des cinq
pratiques transférables agissent sur la friction et la taille, aucune n'agit
sur le sens.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from . import seuil
from .costs import (COST_BASE, COST_OPTIMISTIC, COST_REALISTIC, ES, CostModel,
                    _norm_ppf, norm_cdf, stop_points)
from .entropy import kl_bernoulli, trades_for_information
from .horizon import outcome_scaled
from .mc import Rng
from .report import (HURST, INDEX_LEVEL, SESSION_DISPERSION, SESSION_MIN,
                     SIGMA_1MIN, Table, num)

SEED = 20260903

SIGMA = SIGMA_1MIN
SESSION = SESSION_MIN
SESSIONS_PAR_AN = 252.0

#: La géométrie de travail, celle des parties XIII, XIV et XVI.
STOP_PCT = 0.150
RR = 2.0
GEOM = seuil.geometry(STOP_PCT, reward_risk=RR)
STOP_PTS = GEOM.stop_points

# ---------------------------------------------------------------------------
# Les nombres publics — recopiés une seule fois, ici
# ---------------------------------------------------------------------------
#
# Ils viennent de deux sources publiques et rien dans ce qui suit ne les
# conteste. Ils servent de données d'entrée à un raisonnement, comme les sept
# nombres de la partie XV.

ANNONCES: dict[str, float] = {
    "brut": 0.66,             # rendement brut annualisé, sur la période
    "annees": 31.0,           # 1988–2018
    "taux": 0.5075,           # part des transactions gagnantes rapportée
    "capacite_musd": 10000.0,  # capacité, en millions de dollars
}

#: Ratio d'information de référence. Deux : c'est ce qu'un programme
#: systématique sérieux revendique, et c'est **déclaré**, jamais ajusté sur
#: ce que la partie évalue ensuite.
IR_REF = 2.0

#: Au-dessus de ce taux de réussite, un avantage sur un marché liquide serait
#: visible de tous et compété. Le seuil est posé **avant** les mesures et
#: sert au seul verdict de vraisemblance de la première table.
TAUX_INVRAISEMBLABLE = 0.52

ALPHA = 0.05
PUISSANCE = 0.80


# ---------------------------------------------------------------------------
# I. La loi fondamentale : IR = IC·√N
# ---------------------------------------------------------------------------

#: Décisions par an balayées. De deux par séance — un opérateur — à cent mille
#: par séance — une infrastructure.
N_GRID: tuple[float, ...] = (
    2.0 * SESSIONS_PAR_AN, 10.0 * SESSIONS_PAR_AN, 100.0 * SESSIONS_PAR_AN,
    1000.0 * SESSIONS_PAR_AN, 10000.0 * SESSIONS_PAR_AN,
    100000.0 * SESSIONS_PAR_AN,
)


def ic_requis(ir: float, n: float) -> float:
    """`IC = IR/√N` — la finesse de prévision qu'un ratio donné exige."""
    if n <= 0.0:
        return math.inf
    return ir / math.sqrt(n)


def taux_de_ic(ic: float) -> float:
    """Le taux de réussite d'un pari binaire symétrique portant cet `IC`.

    Pour un pari à deux issues équiprobables, la corrélation entre la
    prévision et l'issue vaut exactement `2p − 1`. La conversion est donc
    exacte et non approchée, ce qui compte : elle permet de lire la loi
    fondamentale dans l'unité qu'un opérateur reconnaît.
    """
    return 0.5 + ic / 2.0


def ic_de_taux(p: float) -> float:
    return 2.0 * p - 1.0


def annees_pour_ir(ir: float, alpha: float = ALPHA,
                   puissance: float = PUISSANCE) -> float:
    """Années requises pour établir un ratio d'information — sans `N`.

    C'est le même fait que la première section de la partie XVI, écrit dans
    l'unité de la gestion : `((z_{α/2} + z_β)/IR)²`. Le nombre de décisions
    n'y entre pas. Une infrastructure qui prend dix millions de décisions par
    an ne démontre donc pas son ratio d'information plus vite qu'un opérateur
    qui en prend cinq cents — **elle a besoin de bien moins d'avantage par
    décision, ce qui n'est pas la même chose du tout.**
    """
    if ir <= 0.0:
        return math.inf
    return ((_norm_ppf(1.0 - alpha / 2.0) + _norm_ppf(puissance)) / ir) ** 2


def decisions_pour_taux(p: float) -> float:
    """Décisions requises pour établir un taux de réussite contre le hasard."""
    if p <= 0.5:
        return math.inf
    return trades_for_information(kl_bernoulli(p, 0.5))


def seuil_de_credibilite(ir: float = IR_REF,
                         taux_max: float = TAUX_INVRAISEMBLABLE) -> float:
    """Décisions annuelles au-dessous desquelles l'exigence cesse d'être crédible.

    En résolvant `taux_de_ic(IR/√N) = taux_max`, soit
    `N = (IR / (2·(taux_max − ½)))²`. Ce n'est pas une opinion sur les
    marchés : c'est l'arithmétique de la loi fondamentale, lue à l'envers,
    sous un seuil de vraisemblance déclaré d'avance.
    """
    ecart = taux_max - 0.5
    if ecart <= 0.0:
        return math.inf
    return (ir / (2.0 * ecart)) ** 2


def table_ampleur() -> Table:
    rows = []
    for n in N_GRID:
        ic = ic_requis(IR_REF, n)
        p = taux_de_ic(ic)
        rows.append([
            num(n, 0),
            num(n / SESSIONS_PAR_AN, 0),
            num(ic, 4),
            num(100 * p, 3),
            num(100 * (p - 0.5), 3),
            "plausible" if p <= TAUX_INVRAISEMBLABLE else "invraisemblable",
        ])
    n_seuil = seuil_de_credibilite()
    return Table(
        key="fonds_ampleur",
        caption="Ce que la loi fondamentale exige, décision par décision",
        headers=["Décisions par an", "Par séance", "IC requis",
                 "Taux de réussite équivalent (%)", "Écart au hasard (points)",
                 "Verdict"],
        rows=rows,
        note="Relation de Grinold `IR = IC·√N`, à ratio d'information "
             "déclaré " + num(IR_REF, 0) + ". La conversion en taux de "
             "réussite est **exacte** pour un pari binaire symétrique, où "
             "l'IC vaut `2p − 1`. Le verdict compare l'exigence au seuil de "
             "vraisemblance posé avant les mesures, "
             + num(100 * TAUX_INVRAISEMBLABLE, 0) + " % : au-dessus, un "
             "avantage sur un marché liquide serait visible de tous. Le "
             "basculement tombe à " + num(n_seuil, 0) + " décisions par an, "
             "soit " + num(n_seuil / SESSIONS_PAR_AN, 1) + " par séance — "
             "*c'est le nombre au-dessous duquel un opérateur qui revendique "
             "ce ratio revendique aussi un avantage que personne d'autre "
             "n'aurait remarqué.*",
    )


def table_invariance() -> Table:
    """Le nombre d'années ne dépend pas de N — et c'est le retournement."""
    rows = []
    for n in N_GRID:
        ic = ic_requis(IR_REF, n)
        p = taux_de_ic(ic)
        dec = decisions_pour_taux(p)
        rows.append([
            num(n, 0),
            num(100 * p, 3),
            num(kl_bernoulli(p, 0.5) * 1e6, 2),
            num(dec, 0),
            num(dec / n, 2),
            num(annees_pour_ir(IR_REF), 2),
        ])
    return Table(
        key="fonds_invariance",
        caption="Le nombre d'années ne dépend pas du nombre de décisions",
        headers=["Décisions par an", "Taux requis (%)",
                 "Information par décision (µbit)",
                 "Décisions pour l'établir", "Années par cette route",
                 "Années par la route du Sharpe"],
        rows=rows,
        note="Deux routes indépendantes, et c'est leur **invariance** qui "
             "est le résultat, pas leur égalité. La quatrième colonne vient "
             "du test du rapport de vraisemblance sur la table de "
             "contingence — de l'information — et la sixième d'un test de "
             "moyenne sur le ratio d'information ; elles diffèrent de "
             + num(100 * abs(annees_pour_ir(IR_REF)
                             - decisions_pour_taux(
                                 taux_de_ic(ic_requis(IR_REF, N_GRID[0])))
                             / N_GRID[0])
                   / annees_pour_ir(IR_REF), 0)
             + " % parce qu'elles ne testent pas la même statistique. Ce qui "
             "compte est qu'aucune des deux ne bouge d'une ligne à l'autre. **Ce que l'ampleur achète n'est pas la vitesse de "
             "la preuve, c'est la petitesse de l'exigence** : l'information "
             "par décision tombe de quatre ordres de grandeur d'une ligne à "
             "l'autre, la durée ne bouge pas d'un centième d'année.",
    )


# ---------------------------------------------------------------------------
# II. Le prix de la preuve, appliqué aux nombres publics
# ---------------------------------------------------------------------------

#: Taux de réussite examinés. Le premier est celui que la publication avance ;
#: les suivants sont ceux d'un opérateur, du plus modeste au plus revendiqué.
TAUX_GRID: tuple[float, ...] = (0.5075, 0.5200, 0.5450, 0.5800, 0.6500)

#: Deux rythmes de décision, et ce sont les deux mondes de la partie.
RYTHME_OPERATEUR = 2.0 * SESSIONS_PAR_AN
RYTHME_FONDS = 10000.0 * SESSIONS_PAR_AN


def table_preuve() -> Table:
    rows = []
    for p in TAUX_GRID:
        bits = kl_bernoulli(p, 0.5)
        dec = decisions_pour_taux(p)
        rows.append([
            num(100 * p, 2),
            num(100 * (p - 0.5), 2),
            num(bits * 1e6, 2),
            num(dec, 0),
            num(dec / RYTHME_OPERATEUR, 1),
            num(dec / RYTHME_FONDS, 3),
        ])
    p_pub = ANNONCES["taux"]
    dec_pub = decisions_pour_taux(p_pub)
    return Table(
        key="fonds_preuve",
        caption="Le même avantage, indémontrable pour l'un, acquis pour l'autre",
        headers=["Taux de réussite (%)", "Écart au hasard (points)",
                 "Information par décision (µbit)",
                 "Décisions pour l'établir",
                 "Années à " + num(RYTHME_OPERATEUR, 0) + " par an",
                 "Années à " + num(RYTHME_FONDS, 0) + " par an"],
        rows=rows,
        note="La première ligne est le taux qu'un livre d'enquête rapporte, "
             "cité une seule fois et non contesté ici. Il demande "
             + num(dec_pub, 0) + " décisions pour être distingué du hasard à "
             + num(100 * ALPHA, 0) + " % et "
             + num(100 * PUISSANCE, 0) + " % de puissance — soit "
             + num(dec_pub / RYTHME_OPERATEUR, 0) + " ans pour un opérateur "
             "à deux décisions par séance, et "
             + num(365.0 * dec_pub / RYTHME_FONDS, 1) + " jours pour une "
             "infrastructure. **L'avantage n'est pas différent : c'est le "
             "dénominateur qui l'est.** La dernière ligne dit l'inverse, et "
             "il faut la lire aussi : un taux franchement élevé s'établit en "
             "quelques centaines de décisions, mais aucun marché liquide n'en "
             "laisse traîner un.",
    )


# ---------------------------------------------------------------------------
# III. La combinaison de signaux faibles, et son plafond
# ---------------------------------------------------------------------------

#: Corrélations moyennes balayées entre deux lectures d'un même panier.
RHO_GRID: tuple[float, ...] = (0.0, 0.05, 0.15, 0.35)

#: Tailles de panier. Quinze est le nombre du catalogue de la partie III.
K_GRID: tuple[int, ...] = (1, 2, 3, 5, 8, 15, 30, 60)

#: Corrélation retenue pour les phrases du texte. Quinze pour cent : deux
#: lectures d'un même flux d'ordres partagent inévitablement une part de leur
#: information, et c'est un ordre de grandeur, pas une mesure.
RHO_REF = 0.15


def ic_combine(k: int, rho: float, ic1: float = 1.0) -> float:
    """`IC₁·√(k/(1 + (k−1)ρ))` — le panier, contre la lecture unique.

    C'est le gain d'un portefeuille de signaux de qualité égale et de
    corrélation moyenne `ρ`. À `ρ = 0` il vaut `√k`, la promesse habituelle.
    Dès que `ρ > 0`, il **sature** : la limite est `1/√ρ`, atteinte quel que
    soit le nombre de lectures ajoutées ensuite.
    """
    if k < 1:
        raise ValueError("k doit être au moins 1")
    denom = 1.0 + (k - 1) * rho
    return ic1 * math.sqrt(k / denom) if denom > 0.0 else math.inf


def plafond(rho: float, ic1: float = 1.0) -> float:
    """`IC₁/√ρ` — ce qu'un panier infini ne dépassera pas."""
    return math.inf if rho <= 0.0 else ic1 / math.sqrt(rho)


def k_pour_fraction(rho: float, fraction: float = 0.90) -> float:
    """Nombre de lectures pour atteindre une fraction du plafond.

    En posant `√(k/(1+(k−1)ρ)) = f/√ρ`, on trouve
    `k = f²(1−ρ)/(ρ(1−f²))`. Le nombre est petit, et c'est le point : passé
    quelques lectures, l'essentiel du gain est acquis et le reste du panier ne
    sert qu'à multiplier les configurations à déflater.
    """
    if rho <= 0.0 or fraction >= 1.0:
        return math.inf
    f2 = fraction * fraction
    return f2 * (1.0 - rho) / (rho * (1.0 - f2))


def table_combinaison() -> Table:
    rows = []
    for k in K_GRID:
        rows.append([num(k, 0)]
                    + [num(ic_combine(k, r), 3) for r in RHO_GRID])
    rows.append(["plafond"] + [("∞" if r <= 0.0 else num(plafond(r), 3))
                               for r in RHO_GRID])
    return Table(
        key="fonds_combinaison",
        caption="Ce qu'un panier de lectures ajoute, et où il s'arrête",
        headers=["Lectures"] + ["ρ = " + num(r, 2) for r in RHO_GRID],
        rows=rows,
        note="Gain d'IC d'un panier de lectures de qualité égale et de "
             "corrélation moyenne `ρ`, rapporté à une lecture seule. La "
             "colonne de gauche est la promesse habituelle, `√k`, et elle "
             "n'est vraie qu'à corrélation **exactement nulle** — ce qui "
             "n'arrive pas entre deux lectures d'un même flux. Dès "
             "`ρ = " + num(RHO_REF, 2) + "`, les quinze lectures du catalogue "
             "de la partie III valent " + num(ic_combine(15, RHO_REF), 2)
             + " fois une lecture seule et non " + num(math.sqrt(15), 2)
             + ", et " + num(k_pour_fraction(RHO_REF), 0) + " lectures "
             "suffisent déjà à en capter 90 %. **Le plafond est fixé par la "
             "corrélation, jamais par le nombre**, et les lectures "
             "supplémentaires ne font plus que gonfler le budget de "
             "configurations à déflater.",
        rules_after=[len(K_GRID) - 1],
    )


# ---------------------------------------------------------------------------
# IV. La capacité, et le seul terrain où l'opérateur seul gagne
# ---------------------------------------------------------------------------
#
# L'impact d'un ordre de taille `Q` exécuté contre un volume quotidien `V` ne
# croît pas comme `Q` mais comme `√Q`. La loi est empirique, robuste d'un
# marché à l'autre, et c'est elle qui plafonne la capacité d'un programme :
# doubler la taille ne double pas le coût, il le multiplie par 1,41 — mais il
# le multiplie, et la friction finit par dépasser ce que la géométrie peut
# porter.

#: Coefficient de la loi en racine. La littérature de microstructure le place
#: entre 0,3 et 1 selon les marchés et les protocoles de mesure ; la valeur
#: retenue est le milieu de cette boîte, **déclarée** et balayée par la
#: surface, jamais ajustée.
Y_IMPACT = 0.50
Y_IMPACT_BOX = (0.30, 1.00)

#: Volume quotidien du contrat, en contrats. Ordre de grandeur d'un future
#: d'indice majeur, déclaré.
VOLUME_JOUR = 1_500_000.0

#: Volatilité quotidienne en points — celle du reste du document.
SIGMA_JOUR = SESSION_DISPERSION

#: Tailles balayées, en contrats.
TAILLE_GRID: tuple[float, ...] = (1.0, 5.0, 25.0, 100.0, 400.0, 1600.0, 6400.0)


def notionnel(taille: float) -> float:
    """Notionnel d'une position, en dollars."""
    return taille * INDEX_LEVEL * ES.point_value


def impact_racine(taille: float, y: float = Y_IMPACT,
                  volume: float = VOLUME_JOUR) -> float:
    """`Y·σ_jour·√(Q/V)` — l'impact d'un ordre, en points d'indice.

    La forme en racine n'est pas un choix de modélisation parmi d'autres :
    c'est le résultat empirique le plus reproduit de la microstructure, vérifié
    sur des actions, des futures et des devises, et il ne dépend ni du
    protocole d'exécution ni de l'horizon. Le module `orderflow` en donne la
    limite des petites tailles — l'impact linéaire de Kyle sur un carnet
    uniforme — qui coïncide avec elle tant que l'ordre ne traverse qu'un
    niveau.
    """
    if taille <= 0.0:
        return 0.0
    return y * SIGMA_JOUR * math.sqrt(taille / volume)


def friction_a_la_taille(taille: float, y: float = Y_IMPACT) -> float:
    """Friction aller-retour à une taille donnée, impact compris."""
    return GEOM.friction_points + 2.0 * impact_racine(taille, y)


def seuil_a_la_taille(taille: float, stop_pct: float = STOP_PCT,
                      y: float = Y_IMPACT) -> float:
    """`µ*` à une taille donnée, en points par heure."""
    a = stop_points(INDEX_LEVEL, stop_pct)
    o = outcome_scaled(a, RR * a, SESSION, SIGMA, HURST)
    c = GEOM.friction_points + 2.0 * impact_racine(taille, y)
    return c / o.expected_time * 60.0


@lru_cache(maxsize=8)
def capacite(stop_pct: float = STOP_PCT, y: float = Y_IMPACT) -> float:
    """La taille où `µ*` quitte le domaine de dérive plausible.

    Elle se trouve par bissection et non par formule, parce que la friction de
    base s'ajoute à l'impact. C'est la définition la plus honnête d'une
    capacité : non pas la taille où le programme cesse de gagner — cela
    dépendrait d'une dérive qu'on ne connaît pas — mais celle où il cesse de
    pouvoir gagner sous **aucune** dérive que le document appelle plausible.
    """
    haut = seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]
    lo, hi = 1.0, 1e7
    if seuil_a_la_taille(lo, stop_pct, y) > haut:
        return 0.0
    for _ in range(80):
        mid = math.sqrt(lo * hi)
        if seuil_a_la_taille(mid, stop_pct, y) <= haut:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


def table_capacite() -> Table:
    rows = []
    base = GEOM.friction_points
    lo_d, hi_d = seuil.PLAUSIBLE_DRIFT_PER_HOUR
    for q in TAILLE_GRID:
        imp = impact_racine(q)
        c = friction_a_la_taille(q)
        mu = seuil_a_la_taille(q)
        if mu <= lo_d:
            verdict = "payant sous toute dérive plausible"
        elif mu <= hi_d:
            verdict = "payant seulement au-delà de µ*"
        else:
            verdict = "hors du domaine plausible"
        rows.append([
            num(q, 0),
            num(notionnel(q) / 1e6, 1),
            num(1e6 * q / VOLUME_JOUR, 1),
            num(imp, 3),
            num(100 * 2.0 * imp / c, 0),
            num(mu, 3),
            verdict,
        ])
    cap = capacite()
    return Table(
        key="fonds_capacite",
        caption="Ce que la taille coûte, et où elle tue la géométrie",
        headers=["Contrats", "Notionnel (M$)", "Participation (ppm)",
                 "Impact par sens (pt)", "Part de l'impact dans c (%)",
                 "µ* (pt/h)", "Verdict"],
        rows=rows,
        note="Loi en racine `Y·σ_jour·√(Q/V)` avec `Y = " + num(Y_IMPACT, 2)
             + "` déclaré, volume quotidien " + num(VOLUME_JOUR, 0)
             + " contrats, friction de base " + num(base, 2) + " point. La "
             "cinquième colonne porte le fait de la section : **à un contrat, "
             "l'impact pèse " + num(100 * 2.0 * impact_racine(1.0)
                                    / friction_a_la_taille(1.0), 0)
             + " % de la friction ; à " + num(TAILLE_GRID[-1], 0)
             + ", il en pèse " + num(100 * 2.0 * impact_racine(TAILLE_GRID[-1])
                                     / friction_a_la_taille(TAILLE_GRID[-1]), 0)
             + " %.** La capacité de cette géométrie — la taille où `µ*` sort "
             "du domaine plausible — vaut " + num(cap, 0) + " contrats, soit "
             + num(notionnel(cap) / 1e6, 0) + " millions de dollars de "
             "notionnel. Un opérateur seul travaille quatre ordres de grandeur "
             "au-dessous, dans un régime où la taille est gratuite. *C'est la "
             "seule chose qu'un fonds ne peut pas lui acheter.*",
    )


# ---------------------------------------------------------------------------
# V. L'exécution : payer le spread, ou l'encaisser
# ---------------------------------------------------------------------------

#: Glissement payé sur un stop, en ticks. Un stop est un ordre au marché, et
#: il part dans le mouvement même qui l'a déclenché : un tick et demi est la
#: valeur réaliste du module `costs`, reprise sans retouche.
GLISSEMENT_STOP = 1.5

#: Les trois conduites d'entrée, en ticks payés par rapport au milieu de
#: fourchette. La troisième est négative et ce n'est pas une coquille : un
#: ordre limite posté au meilleur prix est rempli **mieux** que le milieu.
ENTREES: tuple[tuple[str, float, str], ...] = (
    ("Entrée au marché", 0.5,
     "on traverse la fourchette pour être sûr d'être servi"),
    ("Entrée limite touchée", 0.0,
     "l'ordre attend au milieu et le prix vient le chercher"),
    ("Entrée postée au meilleur prix", -0.5,
     "l'ordre attend au meilleur prix et encaisse un demi-spread"),
)


@lru_cache(maxsize=4)
def _issue(stop_pct: float = STOP_PCT):
    a = stop_points(INDEX_LEVEL, stop_pct)
    return outcome_scaled(a, RR * a, SESSION, SIGMA, HURST)


def glissement_sortie(stop_pct: float = STOP_PCT) -> float:
    """Le glissement de sortie **moyen**, pondéré par les deux issues.

    Il n'a aucune raison d'être posé à la main : une sortie sur la cible est
    un ordre limite et ne glisse pas, une sortie sur le stop est un ordre au
    marché et glisse. La moyenne est donc `(1 − p_cible)·glissement_stop`,
    avec `p_cible` la probabilité d'atteindre la cible en premier — que le
    module `horizon` calcule exactement.

    Écrire un glissement de sortie plus faible que celui-là, c'est
    sous-facturer le stop, et c'est l'erreur la plus fréquente d'un budget de
    friction : elle porte précisément sur l'issue la plus probable.
    """
    o = _issue(stop_pct)
    return (1.0 - o.p_target) * GLISSEMENT_STOP


def cout_de_conduite(entree_ticks: float, stop_pct: float = STOP_PCT,
                     commission: float = 4.00) -> float:
    """Friction aller-retour d'une conduite d'exécution, en points."""
    ticks = entree_ticks + glissement_sortie(stop_pct)
    return (commission + ticks * ES.tick_value) / ES.point_value


def seuil_de_conduite(entree_ticks: float, stop_pct: float = STOP_PCT) -> float:
    return cout_de_conduite(entree_ticks, stop_pct) / _issue(
        stop_pct).expected_time * 60.0


def derive_adverse_annulante(entree_ticks: float,
                             reference: float = 0.5) -> float:
    """La dérive adverse, conditionnelle au remplissage, qui annule le gain.

    Un ordre passif est rempli **parce que** le prix est venu le chercher.
    Sous prix sans dérive, cela n'apprend rien sur la suite — la propriété de
    Markov forte l'interdit — et l'économie de spread est donc intégrale. Sur
    un marché réel, un flux informé peut rendre le remplissage sélectif, et
    c'est ce que le nombre rendu ici chiffre : la dérive défavorable, en
    points par heure, qui reprendrait exactement ce que l'exécution a fait
    gagner.

    Le nombre n'est pas mesurable sur le relevé d'un opérateur sans un
    protocole écrit d'avance — comparer les issues des ordres remplis à celles
    des ordres annulés — et c'est précisément pourquoi il faut le publier.
    """
    gain = cout_de_conduite(reference) - cout_de_conduite(entree_ticks)
    return gain / _issue().expected_time * 60.0


def table_execution() -> Table:
    rows = []
    ref = seuil_de_conduite(ENTREES[0][1])
    lo_d, hi_d = seuil.PLAUSIBLE_DRIFT_PER_HOUR
    for nom, ticks, quoi in ENTREES:
        c = cout_de_conduite(ticks)
        mu = seuil_de_conduite(ticks)
        rows.append([
            nom,
            num(ticks, 1, signed=True),
            num(c, 3),
            num(c / STOP_PTS, 4),
            num(mu, 3),
            num(ref / mu, 2),
            num(derive_adverse_annulante(ticks), 3),
        ])
    passif = seuil_de_conduite(ENTREES[-1][1])
    o = _issue()
    return Table(
        key="fonds_execution",
        caption="Le seul levier que l'opérateur contrôle entièrement",
        headers=["Conduite d'entrée", "Ticks à l'entrée", "c (pt)", "c/a",
                 "µ* (pt/h)", "Facteur sur µ*",
                 "Dérive adverse qui l'annule (pt/h)"],
        rows=rows,
        note="Même géométrie partout — stop " + num(STOP_PCT, 3)
             + " %, rapport " + num(RR, 0) + " — et seule l'entrée change. La "
             "sortie est identique sur les trois lignes et elle n'est pas "
             "posée à la main : elle vaut `(1 − p_cible)·"
             + num(GLISSEMENT_STOP, 1) + "` tick, soit "
             + num(glissement_sortie(), 2) + ", parce qu'une sortie sur la "
             "cible est une limite qui ne glisse pas et une sortie sur le "
             "stop un ordre au marché qui glisse — et que la cible n'est "
             "atteinte que " + num(100 * o.p_target, 1) + " % du temps. "
             "Changer d'entrée, et rien d'autre, divise `µ*` par "
             + num(ref / passif, 2) + " : **c'est plus que ce que le reste du "
             "document obtient en changeant de signal.** La dernière colonne "
             "est la contrepartie honnête. Un ordre passif est rempli parce "
             "que le prix est venu le chercher ; si ce remplissage est "
             "sélectif, une dérive défavorable de "
             + num(derive_adverse_annulante(ENTREES[-1][1]), 2) + " point par "
             "heure reprend tout. Ce chiffre est **au-dessous** du plancher "
             "du domaine plausible, " + num(lo_d, 1) + " à " + num(hi_d, 1)
             + " — la sélection adverse peut donc manger le gain sans "
             "qu'aucune mesure ordinaire ne s'en aperçoive, et il faut un "
             "protocole écrit d'avance pour la voir : comparer les issues des "
             "ordres remplis à celles des ordres annulés.",
    )


#: Profondeurs d'ordre limite balayées, en ticks sous le prix courant.
PROFONDEURS: tuple[float, ...] = (0.5, 1.0, 2.0, 4.0, 8.0, 16.0)

#: Fenêtres d'attente, en minutes.
FENETRES_ATTENTE: tuple[float, ...] = (1.0, 5.0, 15.0, 60.0)


def taux_remplissage(profondeur_ticks: float, fenetre_min: float) -> float:
    """`2Φ(−d/(σ√w))` — la probabilité qu'une limite soit touchée.

    Principe de réflexion, encore : la probabilité que le minimum d'une marche
    sans dérive descende de `d` en `w` minutes. C'est la même forme fermée que
    la partie XVI, lue par l'autre bout — là elle disait qu'un sommet tient,
    ici elle dit qu'un ordre est rempli.
    """
    d = profondeur_ticks * ES.tick_size
    if fenetre_min <= 0.0:
        return 0.0
    return min(1.0, 2.0 * norm_cdf(-d / (SIGMA * math.sqrt(fenetre_min))))


def table_remplissage() -> Table:
    rows = []
    for p in PROFONDEURS:
        rows.append([num(p, 1), num(p * ES.tick_size, 2)]
                    + [num(100 * taux_remplissage(p, w), 1)
                       for w in FENETRES_ATTENTE])
    return Table(
        key="fonds_remplissage",
        caption="Ce qu'un ordre limite attend, et ce qu'il manque",
        headers=["Profondeur (ticks)", "En points"]
                + [num(w, 0) + " min" for w in FENETRES_ATTENTE],
        rows=rows,
        note="Forme fermée `2Φ(−d/σ√w)`, sans simulation — c'est le principe "
             "de réflexion de la partie XVI, lu par l'autre bout. Une limite "
             "posée au meilleur prix est touchée "
             + num(100 * taux_remplissage(0.5, 5.0), 0) + " % du temps en "
             "cinq minutes : l'entrée passive ne coûte donc presque aucune "
             "occasion, et c'est ce qui la rend intéressante. Une limite "
             "posée à " + num(PROFONDEURS[-1], 0) + " ticks n'est touchée que "
             + num(100 * taux_remplissage(PROFONDEURS[-1], 5.0), 0)
             + " % du temps, et **les occasions manquées ne sont pas un "
             "échantillon quelconque** : ce sont exactement les séances où le "
             "prix est parti sans revenir. Attendre un meilleur prix, c'est "
             "choisir de ne pas être là quand le mouvement a lieu.",
    )


# ---------------------------------------------------------------------------
# VI. Les surfaces — ce que deux axes montrent et qu'une colonne cache
# ---------------------------------------------------------------------------
#
# Même règle que partout : le maximum au **fond** de la projection, coin
# `(0, 0)`. Les grilles sont donc écrites dans l'ordre que cette règle impose.

SURF_IR: tuple[float, ...] = (4.0, 3.0, 2.5, 2.0, 1.5, 1.0)
SURF_N: tuple[float, ...] = (504.0, 2520.0, 25200.0, 252000.0,
                             2520000.0, 25200000.0)


def surface_exigence() -> list[list[float]]:
    """L'écart au hasard exigé, en points de taux, sur (IR, décisions par an).

    Le relief tombe d'un facteur mille de l'arête gauche à l'arête droite, et
    c'est le fait de la partie : **ce que l'ampleur achète est la petitesse de
    l'exigence.** La hauteur est en points de pourcentage de taux de réussite,
    la seule unité dans laquelle un opérateur peut juger si l'exigence est
    crédible.
    """
    return [[100.0 * (taux_de_ic(ic_requis(ir, n)) - 0.5) for n in SURF_N]
            for ir in SURF_IR]


SURF_K: tuple[int, ...] = (60, 30, 15, 8, 4, 2)
SURF_RHO: tuple[float, ...] = (0.01, 0.03, 0.08, 0.15, 0.30, 0.50)


def surface_panier() -> list[list[float]]:
    """Le gain d'un panier de lectures, sur (nombre, corrélation).

    Le versant de gauche est la promesse — `√k` — et il n'existe que sur
    l'arête où la corrélation est presque nulle. Dès qu'on avance sur l'autre
    axe, la surface s'aplatit en un plateau bas : c'est le plafond `1/√ρ`, et
    aucune quantité de lectures ne le franchit.
    """
    return [[ic_combine(k, r) for r in SURF_RHO] for k in SURF_K]


SURF_TAILLE: tuple[float, ...] = (6400.0, 1600.0, 400.0, 100.0, 25.0, 5.0)
SURF_STOP: tuple[float, ...] = (0.010, 0.025, 0.050, 0.100, 0.200, 0.400)


def surface_capacite() -> list[list[float]]:
    """Le **logarithme** de `µ*` sur (taille, largeur de stop), impact compris.

    Deux versants pour deux raisons différentes, et c'est ce qui rend le
    relief utile. Vers les grandes tailles, `µ*` monte parce que l'impact
    gonfle `c`. Vers les stops serrés, il monte parce que `E[τ∧T]` s'effondre.
    Un opérateur qui serre son stop *et* grossit sa taille additionne les deux
    versants, et c'est le coin du relief que personne ne regarde.

    La hauteur est logarithmique, et ce n'est pas un choix d'esthétique : le
    seuil parcourt trois ordres et demi de grandeur sur cette boîte, et tracé
    brut le relief se réduirait à une aiguille au coin des stops serrés — le
    défaut que la partie XVI a rencontré sur le relief du hasard. Les
    graduations de l'échine et les infobulles restent en points par heure.
    """
    return [[math.log10(seuil_a_la_taille(q, p)) for p in SURF_STOP]
            for q in SURF_TAILLE]


#: Dérive déclarée pour la surface d'exécution : le milieu du domaine
#: plausible. Elle est **déclarée**, jamais dérivée de ce que la surface sert
#: à évaluer — c'est la règle 6 du dépôt.
DERIVE_DECLAREE = 0.5 * (seuil.PLAUSIBLE_DRIFT_PER_HOUR[0]
                         + seuil.PLAUSIBLE_DRIFT_PER_HOUR[1])

#: Occasions examinées par an, deux par séance.
OCCASIONS_AN = 2.0 * SESSIONS_PAR_AN

SURF_REMPLI: tuple[float, ...] = (1.0, 0.9, 0.75, 0.6, 0.4, 0.2)
SURF_ADVERSE: tuple[float, ...] = (0.0, 0.40, 0.80, 1.20, 1.70, 2.20)


def gain_annuel(remplissage: float, adverse: float,
                entree_ticks: float = -0.5) -> float:
    """Points gagnés dans l'année par une conduite passive, sous deux réserves.

    `remplissage` est la part des ordres effectivement servis, `adverse` la
    dérive défavorable conditionnelle au remplissage. Le reste est
    l'arithmétique de Wald : `(µ − adverse)·E[τ∧T] − c`, multiplié par le
    nombre d'occasions servies.
    """
    o = _issue()
    par_decision = ((DERIVE_DECLAREE - adverse) / 60.0 * o.expected_time
                    - cout_de_conduite(entree_ticks))
    return OCCASIONS_AN * remplissage * par_decision


def surface_execution() -> list[list[float]]:
    """Le gain annuel d'une entrée passive, sur (remplissage, sélection adverse).

    Le sol est posé à zéro : ce qui dépasse gagne, ce qui s'enfonce perd. La
    ligne de niveau zéro est la seule chose à regarder, et elle dit à quelle
    dérive adverse la conduite bascule — pour chaque taux de remplissage.
    """
    return [[gain_annuel(r, d) for d in SURF_ADVERSE] for r in SURF_REMPLI]


# ---------------------------------------------------------------------------
# VII. Le décompte : ce qui transfère à un opérateur seul
# ---------------------------------------------------------------------------

#: Ce dont dispose un opérateur seul, déclaré avant les mesures : deux
#: décisions par séance et un contrat.
OPERATEUR_DECISIONS = OCCASIONS_AN
OPERATEUR_TAILLE = 1.0

#: Un effet compte s'il déplace d'au moins dix pour cent le terme qu'il
#: touche. Même règle que la partie XVI, et posée avant les mesures.
SEUIL_TRANSFERT = 0.10


@dataclass(frozen=True)
class Pratique:
    """Une pratique du fonds, ce qu'elle exige, et ce qu'il en reste."""

    nom: str
    exige: str
    accessible: bool
    effet: float          # facteur sur le terme touché
    lecture: str

    @property
    def transfere(self) -> bool:
        return self.accessible and abs(self.effet - 1.0) >= SEUIL_TRANSFERT


def pratiques() -> tuple[Pratique, ...]:
    """Les cinq pratiques, avec leurs effets **relus** des sections précédentes.

    Aucun nombre n'est réécrit ici. Corriger une mesure en amont change donc
    la ligne et le verdict sans qu'on ait à y penser, ce qui est la seule
    façon d'empêcher une table de synthèse de dériver de ce qu'elle résume.
    """
    n_min = seuil_de_credibilite()
    exigence_operateur = taux_de_ic(ic_requis(IR_REF, OPERATEUR_DECISIONS)) - 0.5
    exigence_fonds = taux_de_ic(ic_requis(IR_REF, RYTHME_FONDS)) - 0.5

    cap = capacite()
    mu_operateur = seuil_a_la_taille(OPERATEUR_TAILLE)
    mu_capacite = seuil_a_la_taille(cap)

    ref = seuil_de_conduite(ENTREES[0][1])
    passif = seuil_de_conduite(ENTREES[-1][1])

    # Un budget de friction qui oublie le stop ne retient que la commission et
    # l'entrée : c'est l'erreur la plus fréquente, et elle se chiffre.
    c_naif = (4.00 + 0.0) / ES.point_value
    c_vrai = cout_de_conduite(0.0)

    return (
        Pratique(
            "L'ampleur",
            num(n_min, 0) + " décisions par an au minimum",
            OPERATEUR_DECISIONS >= n_min,
            exigence_operateur / exigence_fonds,
            "l'exigence par décision, rapportée à celle d'une infrastructure"),
        Pratique(
            "La combinaison de lectures",
            "des lectures décorrélées, et de quoi estimer leur corrélation",
            True,
            ic_combine(15, RHO_REF),
            "le gain d'un panier de quinze lectures sur une seule"),
        Pratique(
            "La capacité",
            "une taille très inférieure à " + num(cap, 0) + " contrats",
            OPERATEUR_TAILLE <= cap,
            mu_capacite / mu_operateur,
            "le seuil payé à la capacité, rapporté à celui payé à un contrat"),
        Pratique(
            "L'exécution",
            "de la patience, et un carnet qui accepte les ordres limite",
            True,
            ref / passif,
            "le facteur sur µ* entre entrée au marché et entrée postée"),
        Pratique(
            "Le coût comme premier modèle",
            "compter le stop dans le budget de friction",
            True,
            c_vrai / c_naif,
            "la friction réelle, rapportée à celle qui oublie le stop"),
    )


def table_transfert() -> Table:
    rows = []
    for p in pratiques():
        rows.append([
            p.nom,
            p.exige,
            "oui" if p.accessible else "non",
            num(p.effet, 2),
            p.lecture,
            "oui" if p.transfere else "non",
        ])
    combien = sum(1 for p in pratiques() if p.transfere)
    return Table(
        key="fonds_transfert",
        caption="Ce qu'un opérateur seul peut prendre, et ce qu'il ne peut pas",
        headers=["Pratique", "Ce qu'elle exige", "À sa portée", "Facteur",
                 "Sur quoi", "Transfère"],
        rows=rows,
        note="Le verdict de la dernière colonne est **calculé** : une pratique "
             "transfère si elle est à la portée d'un opérateur à "
             + num(OPERATEUR_DECISIONS, 0) + " décisions par an et "
             + num(OPERATEUR_TAILLE, 0) + " contrat, *et* si elle déplace son "
             "terme d'au moins " + num(100 * SEUIL_TRANSFERT, 0) + " %. "
             + num(combien, 0) + " des cinq y parviennent. La seule qui "
             "échoue est celle qui fait le rendement du fonds, et elle "
             "échoue sur un critère que ni le talent ni le travail ne "
             "déplacent : le nombre de décisions. Les quatre qui réussissent "
             "agissent sur la friction, sur la taille, ou sur le plafond d'un "
             "panier de lectures — jamais sur la direction. **Rien de ce "
             "qui transfère ne touche au sens du prochain mouvement**, et "
             "c'est la même conclusion que les seize parties précédentes, "
             "obtenue cette fois en partant d'un objet extérieur au document.",
        wrap_last=False,
        wrap_cols=[1, 4],
    )


# ---------------------------------------------------------------------------
# Ce que le document consomme
# ---------------------------------------------------------------------------


def values() -> dict[str, str]:
    n_min = seuil_de_credibilite()
    cap = capacite()
    ref = seuil_de_conduite(ENTREES[0][1])
    passif = seuil_de_conduite(ENTREES[-1][1])
    dec_pub = decisions_pour_taux(ANNONCES["taux"])
    o = _issue()
    return {
        "f_ir_ref": num(IR_REF, 0),
        "f_taux_pub": num(100 * ANNONCES["taux"], 2),
        "f_brut": num(100 * ANNONCES["brut"], 0),
        "f_annees_pub": num(ANNONCES["annees"], 0),
        "f_capacite_pub": num(ANNONCES["capacite_musd"] / 1000.0, 0),
        "f_seuil_taux": num(100 * TAUX_INVRAISEMBLABLE, 0),
        "f_n_min": num(n_min, 0),
        "f_n_min_seance": num(n_min / SESSIONS_PAR_AN, 1),
        "f_exigence_operateur": num(
            100 * (taux_de_ic(ic_requis(IR_REF, OPERATEUR_DECISIONS)) - 0.5), 2),
        "f_exigence_fonds": num(
            100 * (taux_de_ic(ic_requis(IR_REF, RYTHME_FONDS)) - 0.5), 3),
        "f_annees_ir": num(annees_pour_ir(IR_REF), 2),
        "f_decisions_pub": num(dec_pub, 0),
        "f_annees_pub_operateur": num(dec_pub / OPERATEUR_DECISIONS, 0),
        "f_jours_pub_fonds": num(365.0 * dec_pub / RYTHME_FONDS, 1),
        "f_rho_ref": num(RHO_REF, 2),
        "f_panier_quinze": num(ic_combine(15, RHO_REF), 2),
        "f_panier_promesse": num(math.sqrt(15.0), 2),
        "f_plafond": num(plafond(RHO_REF), 2),
        "f_k_quatre_vingt_dix": num(k_pour_fraction(RHO_REF), 0),
        "f_y_impact": num(Y_IMPACT, 2),
        "f_volume": num(VOLUME_JOUR, 0),
        "f_impact_un": num(impact_racine(1.0), 3),
        "f_part_impact_un": num(100 * 2.0 * impact_racine(1.0)
                                / friction_a_la_taille(1.0), 0),
        "f_capacite": num(cap, 0),
        "f_capacite_musd": num(notionnel(cap) / 1e6, 0),
        "f_mu_un": num(seuil_a_la_taille(1.0), 3),
        "f_mu_capacite": num(seuil_a_la_taille(cap), 2),
        "f_glissement_sortie": num(glissement_sortie(), 2),
        "f_p_cible": num(100 * o.p_target, 1),
        "f_c_marche": num(cout_de_conduite(0.5), 3),
        "f_c_passif": num(cout_de_conduite(-0.5), 3),
        "f_mu_marche": num(ref, 3),
        "f_mu_passif": num(passif, 3),
        "f_facteur_execution": num(ref / passif, 2),
        "f_adverse": num(derive_adverse_annulante(-0.5), 2),
        "f_remplissage_court": num(100 * taux_remplissage(0.5, 5.0), 0),
        "f_remplissage_profond": num(
            100 * taux_remplissage(PROFONDEURS[-1], 5.0), 0),
        "f_derive_declaree": num(DERIVE_DECLAREE, 1),
        "f_occasions": num(OCCASIONS_AN, 0),
        "f_transferts": num(sum(1 for p in pratiques() if p.transfere), 0),
        "f_seuil_transfert": num(100 * SEUIL_TRANSFERT, 0),
        "f_stop_pct": num(STOP_PCT, 3),
        "f_rr": num(RR, 0),
    }


def all_tables() -> dict[str, Table]:
    tables = [
        table_ampleur(), table_invariance(), table_preuve(),
        table_combinaison(), table_capacite(), table_execution(),
        table_remplissage(), table_transfert(),
    ]
    return {t.key: t for t in tables}


def main() -> None:
    for t in all_tables().values():
        print(t.to_text())
        print()
    for k, v in values().items():
        print(f"{k:26s} {v}")


if __name__ == "__main__":
    main()
