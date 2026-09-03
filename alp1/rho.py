"""Le taux, et la variable qu'on tient fixe.

Cinquième et dernier document de la série d'options, consacré au rho. Il est
le plus honnête des cinq sur son propre objet : il commence par dire que pour
un opérateur intrajournalier sur indice liquide, *rho est négligeable et le
traiter comme tel est correct*, puis il explique où ce raisonnement casse.

Le dépôt en reprend cinq affirmations. Deux tiennent, trois se corrigent, et
la correction la plus lourde ne porte pas sur un nombre : elle porte sur la
comparaison de deux sensibilités sans pondérer par la dispersion de leurs
moteurs.

I. Le facteur T, qui n'en est pas tout à fait un
--------------------------------------------------
`ρ = KTe^{−rT}N(d₂)`. Le guide écrit que rho est proportionnel au temps et
non à sa racine — ce qui, dans la même série, oppose rho au véga de la partie
XXII. C'est vrai là où l'on négocie et faux au-delà : l'exposant local vaut
un jusqu'à trois mois, 0,95 à un an, 0,91 à deux ans, et **rho passe par un
maximum** vers vingt-quatre ans. Ce maximum n'est pas l'inverse du taux — la
première version de ce module l'a écrit et un test l'a refusé — et il existe
encore à taux nul. Il ne vaut `1/r` qu'au seul taux `r* = q + σ²/2`, celui
auquel une option à la monnaie a la même chance d'être exercée à toute
échéance.

Deux nombres publiés sont justes — quatre centimes à un mois, un dollar à
deux ans — et le rapport qu'on en tire ne l'est pas : il vaut **23**, quand
le guide annonce deux ordres de grandeur.

II. Quand rho rivalise avec véga, et sous quelle unité
--------------------------------------------------------
Le guide dit qu'au-delà d'un an, rho peut rivaliser avec le véga comme
risque dominant. Trois routes le vérifient et **elles ne donnent pas le même
siècle**. Point de taux contre point de volatilité, le croisement tombe à
huit mois — mais cette comparaison-là n'a pas d'unité, car les deux moteurs
ne se produisent pas à la même fréquence. Pondérée par la dispersion
mensuelle de chacun, elle sort de toute échéance négociée. Elle n'y revient
qu'en tenant compte de ce que le guide n'écrit pas : *l'implicite d'une
option longue ne bouge pas autant que celle du mois*. Le croisement tombe
alors entre **un et quatre ans**, et l'affirmation est vraie — sur cette
route seulement, que le guide ne nomme pas.

III. Ce qui a changé entre zéro et cinq pour cent
---------------------------------------------------
« Un risque ignoré à 0 % n'est pas ignorable à 5 % ». La sensibilité, elle,
n'a presque pas bougé : rho croît de 23 % sur toute la plage de taux
plausible. Ce qui a changé de plusieurs ordres est la **volatilité du
moteur**, pas la dérivée — et la phrase du guide attribue au grec ce qui
appartient au taux.

IV. À spot fixe ou à forward fixe
-----------------------------------
Le guide propose la bonne lecture : une option d'indice est écrite sur le
forward, `F = Se^{(r−q)T}`, et rien n'y entre que la combinaison `r − q`. Le
dépôt en tire le fait que le guide n'écrit pas : **le rho change de signe**
selon la variable qu'on tient fixe. À spot fixe il vaut +0,91 sur une option
de deux ans ; à forward fixe il vaut −0,32, et cette seconde forme est
exactement `−T·V`, du pur escompte.

V. Une option très dans la monnaie est une action financée
-------------------------------------------------------------
C'est exact, et la vitesse de convergence se mesure : à deux fois le strike,
l'écart entre le call et l'action financée vaut trois millièmes de sa valeur,
et le rho atteint 97 % de son maximum `KTe^{−rT}`.

VI. Ce que rho coûte à l'opérateur de ce document
---------------------------------------------------
Le guide s'ouvre sur la phrase la plus honnête des cinq : pour un opérateur
intrajournalier sur indice liquide, rho est négligeable et le traiter comme
tel est **correct**. Ce dépôt ne la conteste pas, il la chiffre — vingt-deux
mille fois sous la friction déclarée. Une négligence chiffrée est une
décision ; une négligence affirmée est un pari.

VII. Le décompte, sur cinq parties
------------------------------------
Quatre affirmations déplacent le risque, une l'horloge, deux rien, et
**aucune ne touche à la direction** : c'est la première des cinq parties
d'options dont cette colonne est vide, et rho est aussi le seul des grecs
dont le moteur ne soit pas le prix. Sur les trente-cinq affirmations de la
série, aucune ne donne un sens.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from . import grandeurs as G
from . import niveaux as nv
from . import quant as q
from . import theta as th
from . import vega as vg
from .costs import COST_BASE, ES, norm_cdf
from .report import Table, num

SEED = 20260914

S_REF = vg.S_REF
VOL_REF = vg.VOL_REF
TAUX = vg.TAUX
DIVIDENDE = vg.DIVIDENDE
JOURS_AN = nv.JOURS_AN

#: La friction de la géométrie déclarée, en points d'indice. Elle sert d'unité
#: à la sixième section : tout ce que ce document mesure finit par se comparer
#: à elle.
FRICTION = COST_BASE.friction_points(ES)


# ---------------------------------------------------------------------------
# I. Le facteur T, qui n'en est pas tout à fait un
# ---------------------------------------------------------------------------


def rho_call(s: float, k: float, vol: float, t: float, r: float = TAUX,
             div: float = DIVIDENDE) -> float:
    """`ρ = KTe^{−rT}N(d₂)` — **par unité de taux**, donc par cent points."""
    if t <= 0.0:
        return 0.0
    _, d2 = G._d(s, k, vol, t, r, div)
    return k * t * math.exp(-r * t) * norm_cdf(d2)


def rho_put(s: float, k: float, vol: float, t: float, r: float = TAUX,
            div: float = DIVIDENDE) -> float:
    """`−KTe^{−rT}N(−d₂)`. Un call diffère un paiement, un put une recette."""
    if t <= 0.0:
        return 0.0
    _, d2 = G._d(s, k, vol, t, r, div)
    return -k * t * math.exp(-r * t) * norm_cdf(-d2)


def rho_par_point(s: float, k: float, vol: float, t: float, r: float = TAUX,
                  div: float = DIVIDENDE) -> float:
    """L'unité du pupitre : par point de taux."""
    return rho_call(s, k, vol, t, r, div) / 100.0


def rho_numerique(s: float, k: float, vol: float, t: float, r: float = TAUX,
                  div: float = DIVIDENDE) -> float:
    """Le contrôle, par différence finie sur le taux, **à spot fixe**."""
    h = 1e-6
    return (th.call(s, k, vol, t, r + h, div)
            - th.call(s, k, vol, t, r - h, div)) / (2.0 * h)


def exposant_effectif(jours: float, s: float = S_REF, k: float = S_REF,
                      vol: float = VOL_REF, r: float = TAUX,
                      div: float = DIVIDENDE) -> float:
    """`d ln ρ / d ln T` — l'exposant local, mesuré et non postulé.

    Le guide écrit que rho est proportionnel à `T`. L'exposant vaut un aux
    échéances courtes, et il décroît : trois facteurs se composent, `T` qui
    croît, `e^{−rT}` qui décroît, et `N(d₂)` qui dérive.
    """
    t = jours / JOURS_AN
    h = 1e-4
    a = math.log(rho_call(s, k, vol, t * (1.0 - h), r, div))
    b = math.log(rho_call(s, k, vol, t * (1.0 + h), r, div))
    return (b - a) / (2.0 * h)


def taux_du_pic_exact(vol: float = VOL_REF, div: float = DIVIDENDE) -> float:
    """`r* = q + σ²/2` — le seul taux où le maximum de rho tombe **à `1/r`**.

    Le premier jet de ce module affirmait que le maximum tombe « à peu près à
    l'inverse du taux », et c'est un test qui a refusé la phrase : à 2 % elle
    se trompe d'un tiers. La raison est que trois facteurs se composent dans
    `KTe^{−rT}N(d₂)`, pas deux. Si la probabilité d'exercice ne bouge pas avec
    l'échéance, le maximum de `Te^{−rT}` tombe exactement à `1/r` ; et à la
    monnaie elle ne bouge pas quand `d₂` est nul pour toute échéance,
    c'est-à-dire quand `r − q − σ²/2 = 0`. Au-dessous de ce taux, la
    probabilité d'exercice décroît et le maximum vient plus tôt ; au-dessus,
    elle croît et il vient plus tard.
    """
    return div + 0.5 * vol * vol


def echeance_du_pic(s: float = S_REF, k: float = S_REF, vol: float = VOL_REF,
                    r: float = TAUX, div: float = DIVIDENDE) -> float:
    """L'échéance, en années, où rho est maximal.

    Le maximum existe toujours, y compris **à taux nul** : ce n'est pas
    l'escompte seul qui retourne la courbe, c'est aussi la décroissance de la
    probabilité d'exercice. Il ne vaut `1/r` qu'au taux de
    `taux_du_pic_exact`, et la bissection le trouve partout ailleurs.
    """
    lo, hi = 0.5, 400.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        h = 1e-5
        if (rho_call(s, k, vol, mid * (1.0 + h), r, div)
                > rho_call(s, k, vol, mid * (1.0 - h), r, div)):
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def echeance_de_l_ecart(tolerance: float, s: float = S_REF, k: float = S_REF,
                        vol: float = VOL_REF, r: float = TAUX,
                        div: float = DIVIDENDE) -> float:
    """L'échéance, en jours, où la proportionnalité s'écarte de `tolerance`.

    On cale la droite sur le mois — l'échéance où la règle est vraie — et on
    cherche où la mesure s'en éloigne de la tolérance donnée. C'est la façon
    dont ce dépôt chiffre une approximation plutôt que de la qualifier.
    """
    ref = rho_call(s, k, vol, 30.0 / JOURS_AN, r, div) / (30.0 / JOURS_AN)
    lo, hi = 30.0, 20000.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        t = mid / JOURS_AN
        if abs(rho_call(s, k, vol, t, r, div) / (ref * t) - 1.0) < tolerance:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


#: Échéances balayées, en jours.
ECHEANCES: tuple[float, ...] = (7.0, 30.0, 90.0, 180.0, 365.0, 730.0, 1095.0)

#: Les deux nombres que le guide publie, et l'ordre de grandeur qu'il en tire.
JOURS_COURT = 30.0
JOURS_LONG = 730.0
RAPPORT_ANNONCE = 100.0


def rapport_des_echeances(court: float = JOURS_COURT,
                          long_: float = JOURS_LONG) -> float:
    """Le rapport des deux rhos que le guide chiffre correctement."""
    return (rho_call(S_REF, S_REF, VOL_REF, long_ / JOURS_AN)
            / rho_call(S_REF, S_REF, VOL_REF, court / JOURS_AN))


def table_echelle() -> Table:
    rows = []
    ref = rho_par_point(S_REF, S_REF, VOL_REF, 30.0 / JOURS_AN)
    for j in ECHEANCES:
        t = j / JOURS_AN
        rows.append([
            num(j, 0),
            num(rho_par_point(S_REF, S_REF, VOL_REF, t), 4),
            num(rho_put(S_REF, S_REF, VOL_REF, t) / 100.0, 4, signed=True),
            num(rho_par_point(S_REF, S_REF, VOL_REF, t) / ref, 2),
            num(j / 30.0, 2),
            num(exposant_effectif(j), 3),
        ])
    return Table(
        key="rh_echelle",
        caption="Rho contre l'échéance, et la proportionnalité qui s'use",
        headers=["Jours", "Rho d'un call (par point de taux)",
                 "Rho d'un put", "Rapport au mois", "T/30",
                 "Exposant effectif"],
        rows=rows,
        note="Le guide écrit que rho est proportionnel au temps et non à sa "
             "racine, ce qui l'oppose au véga de la partie précédente. Les "
             "deux colonnes du milieu comparent la mesure à cette "
             "proportionnalité, et la dernière donne l'exposant local. Il "
             "vaut un jusqu'à trois mois, "
             + num(exposant_effectif(365.0), 3) + " à un an et "
             + num(exposant_effectif(730.0), 3) + " à deux ans : *la règle "
             "est excellente là où le guide dit qu'elle sert, et elle s'use "
             "exactement là où il dit qu'il faut la regarder.* Trois facteurs "
             "s'y composent — `T` qui croît, `e^{−rT}` qui décroît, `N(d₂)` "
             "qui dérive — et leur produit passe par un **maximum** vers "
             + num(echeance_du_pic(), 0) + " ans, soit à peu près l'inverse "
             "du taux. La colonne du put rappelle le mécanisme : un call "
             "diffère un paiement et gagne à la hausse des taux, un put "
             "diffère une recette et y perd.",
    )


def table_deux_nombres() -> Table:
    """Les deux nombres publiés, et le rapport qu'on en tire."""
    court = rho_par_point(S_REF, S_REF, VOL_REF, JOURS_COURT / JOURS_AN)
    long_ = rho_par_point(S_REF, S_REF, VOL_REF, JOURS_LONG / JOURS_AN)
    rows = [
        ["Un mois, à la monnaie", num(JOURS_COURT, 0), num(court, 4),
         "quatre centimes", "oui"],
        ["Deux ans, à la monnaie", num(JOURS_LONG, 0), num(long_, 4),
         "environ un dollar", "oui"],
        ["Le rapport des deux", "—", num(long_ / court, 1),
         "deux ordres de grandeur", "non"],
    ]
    return Table(
        key="rh_deux_nombres",
        caption="Deux nombres justes, et un rapport qui ne l'est pas",
        headers=["Ce qui est publié", "Jours", "Mesuré (par point de taux)",
                 "Ce que le guide annonce", "Vérifié"],
        rows=rows,
        note="Sur un sous-jacent à cent, à " + num(100 * VOL_REF, 0) + " % de "
             "volatilité et " + num(100 * TAUX, 1) + " % de taux. Les deux "
             "premières lignes sont **exactes** : un point de taux déplace un "
             "call d'un mois de quatre centimes et un call de deux ans d'à "
             "peu près un dollar. La troisième ne l'est pas. Le rapport de "
             "ces deux nombres vaut " + num(long_ / court, 1) + ", soit un "
             "peu plus d'un ordre de grandeur, quand le guide en annonce "
             "deux — un facteur "
             + num(RAPPORT_ANNONCE / (long_ / court), 1) + " sur la "
             "conclusion. *C'est le mode de défaillance le plus discret de la "
             "série : deux mesures justes, et une comparaison fausse écrite "
             "entre elles.* Le dépôt le note parce qu'il a commis la même "
             "faute dans sa propre partie XXI, où un décompte annoncé « cinq »"
             " valait quatre.",
    )


# ---------------------------------------------------------------------------
# II. Quand rho rivalise avec véga, et sous quelle unité
# ---------------------------------------------------------------------------
#
# Le guide compare deux sensibilités sans les rapporter à la fréquence de
# leurs moteurs. C'est la faute la plus coûteuse de la série, parce qu'elle ne
# porte sur aucun nombre : les deux grandeurs comparées sont exactes, et la
# comparaison n'a pas d'unité.

#: La dispersion mensuelle de la volatilité implicite du mois, en points de
#: volatilité. Elle vient de la partie XXII, où elle est construite sur la
#: volatilité de la volatilité déclarée — non observable ici, et balayée là-bas.
DISPERSION_VOL = 100.0 * vg.ecart_type_implicite()

#: Dispersions mensuelles du taux balayées, en points de taux. Aucune n'est
#: observable dans ce dépôt ; elles encadrent ce qu'un taux à deux ans fait
#: dans un régime calme et dans un régime de resserrement.
DISPERSIONS_TAUX: tuple[float, ...] = (0.10, 0.20, 0.30, 0.45, 0.60)

#: Celle qui chiffre le texte.
DISPERSION_TAUX = 0.30


def risque_rho(jours: float, sigma_r: float = DISPERSION_TAUX) -> float:
    """Ce qu'un mois de taux déplace, en points d'indice."""
    return rho_par_point(S_REF, S_REF, VOL_REF, jours / JOURS_AN) * sigma_r


def risque_vega(jours: float, structure: bool = True,
                sigma_v: float = DISPERSION_VOL) -> float:
    """Ce qu'un mois de volatilité déplace, en points d'indice.

    `structure` décide de la seule hypothèse qui sépare les deux dernières
    routes : la volatilité implicite d'une option de deux ans ne bouge **pas**
    autant que celle du mois. Le poids est celui de la partie XXII, ajusté par
    minimax et non postulé.
    """
    v = vg.vega_par_point(S_REF, S_REF, VOL_REF, jours / JOURS_AN,
                          TAUX, DIVIDENDE)
    if not structure:
        return v * sigma_v
    kappa, _ = vg.kappa_minimax()
    return v * sigma_v * vg.poids_modele(jours, kappa)


def _croisement(f, lo: float = 1.0, hi: float = 40000.0) -> float:
    """Le premier zéro croissant de `f`, en jours ; `inf` s'il n'y en a pas."""
    if f(lo) > 0.0 or f(hi) < 0.0:
        return math.inf
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def croisement_unite() -> float:
    """Route 1 : un point de taux contre un point de volatilité, en jours."""
    return _croisement(
        lambda j: rho_par_point(S_REF, S_REF, VOL_REF, j / JOURS_AN)
        - vg.vega_par_point(S_REF, S_REF, VOL_REF, j / JOURS_AN,
                            TAUX, DIVIDENDE))


def croisement_brut(sigma_r: float = DISPERSION_TAUX) -> float:
    """Route 2 : pondéré par la dispersion des moteurs, sans terme."""
    return _croisement(lambda j: risque_rho(j, sigma_r)
                       - risque_vega(j, structure=False))


def croisement_structure(sigma_r: float = DISPERSION_TAUX) -> float:
    """Route 3 : pondéré, et la volatilité longue bouge moins que la courte."""
    return _croisement(lambda j: risque_rho(j, sigma_r)
                       - risque_vega(j, structure=True))


def _jours_texte(j: float) -> str:
    if not math.isfinite(j):
        return "jamais"
    if j < 730.0:
        return num(j, 0) + " j"
    return num(j / JOURS_AN, 1) + " ans"


def dispersion_pour_un_an() -> float:
    """La dispersion du taux qui ramène le croisement à un an, par bissection.

    Elle sort de la plage balayée, et c'est le chiffre qui manque à la phrase
    du guide : il faudrait un taux à deux ans plus agité qu'aucune des cinq
    colonnes pour que rho rejoigne le véga avant l'an.
    """
    lo, hi = 0.02, 5.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if croisement_structure(mid) > JOURS_AN:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def table_croisement() -> Table:
    rows = []
    for s in DISPERSIONS_TAUX:
        rows.append([
            num(s, 2),
            num(DISPERSION_VOL, 2),
            _jours_texte(croisement_unite()),
            _jours_texte(croisement_brut(s)),
            _jours_texte(croisement_structure(s)),
            num(risque_rho(730.0, s) / risque_vega(730.0), 2),
        ])
    return Table(
        key="rh_croisement",
        caption="Où rho rejoint le véga, par trois routes qui ne s'accordent pas",
        headers=["Dispersion du taux (points par mois)",
                 "Dispersion de l'implicite (points par mois)",
                 "Croisement — point contre point",
                 "Croisement — pondéré, sans terme",
                 "Croisement — pondéré, avec terme",
                 "Rapport des deux risques à deux ans"],
        rows=rows,
        note="Le guide écrit qu'au-delà d'un an, rho peut rivaliser avec le "
             "véga. Trois façons de vérifier, et *elles ne donnent pas le "
             "même siècle*. Comparés unité contre unité — un point de taux "
             "contre un point de volatilité — les deux se croisent à "
             + _jours_texte(croisement_unite()) + ", bien avant l'an. Mais "
             "cette comparaison n'a pas d'unité : un point de taux et un "
             "point d'implicite ne se produisent pas à la même fréquence, et "
             "l'implicite du mois bouge ici "
             + num(DISPERSION_VOL / DISPERSION_TAUX, 0) + " fois plus. "
             "Pondérée par la dispersion de chaque moteur, la comparaison "
             "renverse le verdict : le croisement sort de toute échéance "
             "négociée. Il n'y revient qu'en tenant compte du fait que "
             "*l'implicite d'une option longue ne bouge pas autant que celle "
             "du mois* — le poids ajusté de la partie XXII — et il tombe "
             "alors entre "
             + num(croisement_structure(DISPERSIONS_TAUX[-1]) / JOURS_AN, 1)
             + " et "
             + num(croisement_structure(DISPERSIONS_TAUX[0]) / JOURS_AN, 1)
             + " ans. **L'affirmation du guide est vraie sur la troisième "
             "route et fausse sur les deux autres**, et il n'écrit pas "
             "laquelle il emprunte. La leçon dépasse le rho : *comparer deux "
             "sensibilités, c'est comparer deux moteurs, et une sensibilité "
             "seule ne dit rien du risque qu'elle porte.*",
    )


# ---------------------------------------------------------------------------
# III. Ce qui a changé entre zéro et cinq pour cent
# ---------------------------------------------------------------------------

#: Taux balayés. Le premier est la décennie qui a rendu l'avertissement du
#: guide inutile ; le dernier est au-dessus de tout ce que la période couvre.
TAUX_BALAYES: tuple[float, ...] = (0.0, 0.01, 0.02, 0.03, 0.04, 0.05,
                                   0.06, 0.08)


def table_regime() -> Table:
    rows = []
    ref = rho_par_point(S_REF, S_REF, VOL_REF, 2.0, 0.0, DIVIDENDE)
    for r in TAUX_BALAYES:
        rows.append([
            num(100 * r, 1),
            num(rho_par_point(S_REF, S_REF, VOL_REF, 30.0 / JOURS_AN, r,
                              DIVIDENDE), 4),
            num(rho_par_point(S_REF, S_REF, VOL_REF, 2.0, r, DIVIDENDE), 4),
            num(rho_par_point(S_REF, S_REF, VOL_REF, 2.0, r, DIVIDENDE) / ref,
                3),
            num(echeance_du_pic(S_REF, S_REF, VOL_REF, max(r, 1e-9),
                                DIVIDENDE), 1),
            num(1.0 / r, 1) if r > 0.0 else "sans objet",
        ])
    haut = rho_par_point(S_REF, S_REF, VOL_REF, 2.0, TAUX_BALAYES[-1],
                         DIVIDENDE)
    return Table(
        key="rh_regime",
        caption="Ce que le passage de zéro à cinq pour cent a déplacé",
        headers=["Taux (%)", "Rho à un mois", "Rho à deux ans",
                 "Rapport au taux nul", "Échéance du maximum (ans)",
                 "L'inverse du taux (ans)"],
        rows=rows,
        note="« Un risque ignoré à 0 % n'est pas ignorable à 5 % » est la "
             "phrase la plus citable du guide, et la table dit ce qu'elle "
             "vaut. La **sensibilité** n'a presque pas bougé : le rho d'une "
             "option de deux ans croît de "
             + num(100 * (haut / ref - 1.0), 0) + " % sur toute la plage de "
             "taux que la période couvre, et le sens de la variation est "
             "l'inverse de ce que la phrase suggère — *rho est plus grand "
             "quand les taux sont hauts, pas quand ils viennent de monter.* "
             "Ce qui a changé de plusieurs ordres est la volatilité du "
             "moteur, pas la dérivée : le taux à deux ans a passé une "
             "décennie à ne rien faire, puis une année à bouger. La phrase "
             "est donc juste dans sa conclusion et fausse dans son sujet — "
             "*elle attribue au grec ce qui appartient à son moteur*, et "
             "c'est exactement la faute que la table précédente mesure sur "
             "le croisement avec le véga. Les deux dernières colonnes "
             "enterrent un piège que ce module a d'abord publié : le "
             "maximum de rho **n'est pas** l'inverse du taux, et il existe "
             "encore à taux nul — "
             + num(echeance_du_pic(S_REF, S_REF, VOL_REF, 1e-9, DIVIDENDE), 0)
             + " ans, poussé par la seule décroissance de la probabilité "
             "d'exercice. Les deux colonnes ne se rejoignent qu'en un point, "
             "et il se calcule : `r* = q + σ²/2` = "
             + num(100 * taux_du_pic_exact(), 2) + " %, le taux auquel une "
             "option à la monnaie a la même chance d'être exercée à toute "
             "échéance. Au-dessous le maximum vient plus tôt, au-dessus plus "
             "tard.",
    )


# ---------------------------------------------------------------------------
# IV. À spot fixe ou à forward fixe
# ---------------------------------------------------------------------------


def rho_forward_fixe(s: float, k: float, vol: float, t: float,
                     r: float = TAUX, div: float = DIVIDENDE) -> float:
    """`−T·V` — le rho d'une option d'indice **à forward fixe**, par point.

    Une option d'indice est écrite sur le forward, et rien n'entre dans son
    prix que la combinaison `r − q` et l'escompte. À forward tenu fixe, le
    taux ne touche donc plus que l'escompte, et la dérivée vaut `−T` fois la
    valeur : *elle change de signe*.
    """
    if t <= 0.0:
        return 0.0
    return -t * th.call(s, k, vol, t, r, div) / 100.0


def rho_forward_numerique(s: float, k: float, vol: float, t: float,
                          r: float = TAUX, div: float = DIVIDENDE) -> float:
    """Le contrôle : on bouge le taux **en tenant le forward** par le spot.

    `F = Se^{(r−q)T}` reste fixe si le spot se déplace de `e^{−hT}` quand le
    taux se déplace de `h`. C'est la seule façon de vérifier que la forme
    fermée ci-dessus est bien la dérivée qu'elle prétend être, et non une
    identité écrite de mémoire.
    """
    h = 1e-6
    haut = th.call(s * math.exp(-h * t), k, vol, t, r + h, div)
    bas = th.call(s * math.exp(h * t), k, vol, t, r - h, div)
    return (haut - bas) / (2.0 * h) / 100.0


def table_forward() -> Table:
    rows = []
    for j in ECHEANCES:
        t = j / JOURS_AN
        spot = rho_par_point(S_REF, S_REF, VOL_REF, t)
        fwd = rho_forward_fixe(S_REF, S_REF, VOL_REF, t)
        ctl = rho_forward_numerique(S_REF, S_REF, VOL_REF, t)
        rows.append([
            num(j, 0),
            num(spot, 4, signed=True),
            num(fwd, 4, signed=True),
            num(ctl, 4, signed=True),
            num(spot - fwd, 4),
            num(spot / fwd, 2, signed=True),
        ])
    s2 = rho_par_point(S_REF, S_REF, VOL_REF, 2.0)
    f2 = rho_forward_fixe(S_REF, S_REF, VOL_REF, 2.0)
    return Table(
        key="rh_forward",
        caption="Le même rho, deux signes, selon la variable qu'on tient fixe",
        headers=["Jours", "À spot fixe", "À forward fixe",
                 "Contrôle par différence finie", "Écart",
                 "Rapport des deux"],
        rows=rows,
        note="Le guide propose la bonne lecture — une option d'indice est "
             "écrite sur le forward `F = Se^{(r−q)T}`, et rien n'y entre que "
             "la combinaison `r − q` — puis il s'arrête avant d'en tirer la "
             "conséquence. La voici : **le rho change de signe** selon la "
             "variable qu'on tient fixe. À spot fixe, monter le taux monte le "
             "forward et le call vaut plus : " + num(s2, 3, signed=True)
             + " à deux ans. À forward fixe, le taux ne touche plus que "
             "l'escompte et le call vaut moins : " + num(f2, 3, signed=True)
             + ", soit exactement `−T·V`, ce que la troisième colonne "
             "vérifie en bougeant le taux et le spot ensemble. *Un pupitre "
             "qui couvre son rho sans dire laquelle des deux il tient fixe "
             "couvre dans une direction sur deux*, et l'écart entre les deux "
             "vaut " + num(s2 - f2, 3) + " point d'indice par point de taux "
             "sur une seule option. Le rapport de la dernière colonne se "
             "resserre avec l'échéance sans jamais changer de signe : les "
             "deux lectures ne convergent pas, elles restent opposées.",
    )


# ---------------------------------------------------------------------------
# V. Une option très dans la monnaie est une action financée
# ---------------------------------------------------------------------------

#: Moneyness balayées pour la convergence, en `S/K`.
MONEYNESS: tuple[float, ...] = (1.0, 1.1, 1.2, 1.5, 2.0, 3.0)

#: L'échéance de la démonstration, en années.
T_FINANCEE = 2.0


def action_financee(s: float, k: float, t: float, r: float = TAUX,
                    div: float = DIVIDENDE) -> float:
    """`Se^{−qT} − Ke^{−rT}` — l'action, achetée à crédit et détenue."""
    return s * math.exp(-div * t) - k * math.exp(-r * t)


def rho_plafond(k: float, t: float, r: float = TAUX) -> float:
    """`KTe^{−rT}` — le rho d'une option certaine d'être exercée."""
    return k * t * math.exp(-r * t)


def table_financee() -> Table:
    rows = []
    for m in MONEYNESS:
        s = S_REF * m
        c = th.call(s, S_REF, VOL_REF, T_FINANCEE)
        fin = action_financee(s, S_REF, T_FINANCEE)
        rmax = rho_plafond(S_REF, T_FINANCEE)
        rows.append([
            num(m, 2),
            num(c, 3),
            num(fin, 3),
            num(c - fin, 4),
            num(100 * (c - fin) / c, 2),
            num(100 * rho_call(s, S_REF, VOL_REF, T_FINANCEE) / rmax, 1),
        ])
    c2 = th.call(2 * S_REF, S_REF, VOL_REF, T_FINANCEE)
    f2 = action_financee(2 * S_REF, S_REF, T_FINANCEE)
    return Table(
        key="rh_financee",
        caption="À quelle vitesse un call profond devient une action financée",
        headers=["S/K", "Le call", "L'action financée", "Écart",
                 "Écart relatif (%)", "Part du rho maximal (%)"],
        rows=rows,
        note="À " + num(T_FINANCEE, 0) + " ans, "
             + num(100 * VOL_REF, 0) + " % de volatilité, "
             + num(100 * TAUX, 1) + " % de taux et "
             + num(100 * DIVIDENDE, 1) + " % de rendement. L'affirmation du "
             "guide est **exacte**, et ce document la chiffre plutôt que de "
             "l'illustrer : à deux fois le strike, l'écart entre le call et "
             "l'action achetée à crédit vaut " + num(c2 - f2, 3) + " point "
             "sur " + num(c2, 1) + ", soit "
             + num(100 * (c2 - f2) / c2, 2) + " % — et le rho a rejoint "
             + num(100 * rho_call(2 * S_REF, S_REF, VOL_REF, T_FINANCEE)
                   / rho_plafond(S_REF, T_FINANCEE), 0) + " % de son "
             "plafond `KTe^{−rT}`, celui d'une option certaine d'être "
             "exercée. *Ce qui reste du call à ce niveau n'est plus une "
             "option, c'est un emprunt* : le rho ne mesure alors aucune "
             "optionalité, il mesure la durée d'un prêt. C'est le seul "
             "endroit de la série d'options où un grec cesse d'être une "
             "sensibilité pour devenir une quantité comptable.",
    )


# ---------------------------------------------------------------------------
# VI. Ce que rho coûte à l'opérateur de ce document
# ---------------------------------------------------------------------------
#
# Le guide s'ouvre sur la phrase la plus honnête de la série : pour un
# opérateur intrajournalier sur indice liquide, rho est négligeable et le
# traiter comme tel est correct. Ce dépôt ne la conteste pas — il la chiffre,
# parce qu'une négligence chiffrée est une décision et une négligence
# affirmée est un pari.

#: Séances de bourse par mois, pour convertir une dispersion mensuelle.
SEANCES_PAR_MOIS = 21.0

#: L'échéance de l'opérateur de ce document, en jours : une position ouverte
#: et fermée dans la séance.
JOURS_INTRA = 4.0 / 24.0

#: Échéances balayées pour le coût, en jours.
ECHEANCES_COUT: tuple[float, ...] = (JOURS_INTRA, 1.0, 30.0, 365.0, 730.0,
                                     1825.0, 3650.0, 7665.0)


def dispersion_seance(sigma_r: float = DISPERSION_TAUX,
                      seances: float = 1.0) -> float:
    """La dispersion du taux sur `seances` séances, en points de taux."""
    return sigma_r * math.sqrt(seances / SEANCES_PAR_MOIS)


def cout_de_rho(jours: float, sigma_r: float = DISPERSION_TAUX,
                seances: float = 1.0) -> float:
    """Ce que rho déplace sur une séance, en points d'indice."""
    return (rho_par_point(S_REF, S_REF, VOL_REF, jours / JOURS_AN)
            * dispersion_seance(sigma_r, seances))


def echeance_du_cout(sigma_r: float = DISPERSION_TAUX, seances: float = 1.0,
                     cible: float = FRICTION) -> float:
    """L'échéance, en jours, où le coût de rho égale la friction ; `inf` sinon.

    Le maximum de rho étant atteint puis dépassé, cette équation n'a pas
    toujours de solution — et c'est le résultat de la section : *sous une
    dispersion de taux ordinaire, aucune échéance ne rend rho comparable à la
    friction sur une séance.*
    """
    return _croisement(lambda j: cout_de_rho(j, sigma_r, seances) - cible,
                       lo=0.01, hi=7665.0)


def _part(x: float) -> str:
    """Une part de friction, écrite avec deux chiffres significatifs.

    Un format à quatre décimales publiait « 0,0000 » sur la ligne de
    l'opérateur de ce document — c'est-à-dire qu'il effaçait le résultat de
    la table au lieu de le montrer.
    """
    if x <= 0.0:
        return num(0.0, 2)
    d = max(2, 1 - int(math.floor(math.log10(x))))
    return num(x, min(d, 8))


def table_cout() -> Table:
    rows = []
    for j in ECHEANCES_COUT:
        etiquette = ("Dans la séance" if j < 1.0
                     else num(j, 0) + " jours")
        rows.append([etiquette]
                    + [_part(cout_de_rho(j, s) / FRICTION)
                       for s in DISPERSIONS_TAUX])
    rows.append(["Échéance qui égale la friction"]
                + [_jours_texte(echeance_du_cout(s))
                   for s in DISPERSIONS_TAUX])
    intra = cout_de_rho(JOURS_INTRA) / FRICTION
    return Table(
        key="rh_cout",
        caption="Le coût de rho, en unités de la friction déclarée",
        headers=["Échéance de l'option"]
                + [num(s, 2) + " pt/mois" for s in DISPERSIONS_TAUX],
        rows=rows,
        note="La friction de la géométrie déclarée vaut "
             + num(FRICTION, 2) + " point d'indice ; toutes les cases sont "
             "rapportées à elle, et les colonnes balaient la dispersion "
             "mensuelle du taux — non observable ici, comme la taille de "
             "grappe du footprint et la volatilité de la volatilité de la "
             "partie XXII. Le guide s'ouvre en disant que pour un opérateur "
             "intrajournalier sur indice liquide, rho est négligeable et le "
             "traiter comme tel est correct. **C'est la phrase la plus juste "
             "des cinq documents**, et la première ligne dit de combien : le "
             "rho d'une position ouverte et fermée dans la séance déplace "
             + num(1.0 / intra, 0) + " fois moins que la friction ne coûte. "
             "Ce n'est pas un petit terme, *c'est un terme qui n'existe "
             "pas*. La dernière ligne renverse la lecture : même à dix ans "
             "d'échéance et dans un régime de taux agité, le coût d'une "
             "séance reste sous la friction, et il n'y a d'échéance "
             "comparable que dans les deux colonnes de droite. Un opérateur "
             "qui tient une option longue plusieurs semaines change de "
             "régime — la dispersion croît en racine du nombre de séances — "
             "mais ce n'est plus le même métier, et ce document n'en parle "
             "pas.",
    )


# ---------------------------------------------------------------------------
# VII. Le décompte, sur cinq parties
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Affirmation:
    enonce: str
    grandeur: str
    mesure: str


def affirmations() -> tuple[Affirmation, ...]:
    court = rho_par_point(S_REF, S_REF, VOL_REF, JOURS_COURT / JOURS_AN)
    long_ = rho_par_point(S_REF, S_REF, VOL_REF, JOURS_LONG / JOURS_AN)
    ref0 = rho_par_point(S_REF, S_REF, VOL_REF, 2.0, 0.0, DIVIDENDE)
    haut = rho_par_point(S_REF, S_REF, VOL_REF, 2.0, 0.08, DIVIDENDE)
    return (
        Affirmation(
            "Rho est proportionnel au temps, et non à sa racine comme le véga",
            "l'horloge",
            "exact sous trois mois ; l'exposant vaut "
            + num(exposant_effectif(730.0), 2) + " à deux ans et rho passe "
            "par un maximum vers " + num(echeance_du_pic(), 0) + " ans"),
        Affirmation(
            "Quatre centimes à un mois, un dollar à deux ans : deux ordres "
            "de grandeur",
            "le risque",
            "les deux nombres sont justes, leur rapport vaut "
            + num(long_ / court, 1) + " et non cent"),
        Affirmation(
            "Au-delà d'un an, rho peut rivaliser avec le véga",
            "le risque",
            "vrai sur une route des trois : "
            + _jours_texte(croisement_unite()) + ", jamais, ou "
            + num(croisement_structure() / JOURS_AN, 1) + " ans"),
        Affirmation(
            "Un risque ignoré à 0 % n'est pas ignorable à 5 %",
            "rien",
            "la sensibilité croît de " + num(100 * (haut / ref0 - 1.0), 0)
            + " % sur toute la plage ; c'est le moteur qui a changé, pas le "
            "grec"),
        Affirmation(
            "Une option d'indice est écrite sur le forward, et seul `r − q` "
            "y entre",
            "le risque",
            "exact, et le rho **change de signe** selon la variable tenue "
            "fixe : " + num(rho_par_point(S_REF, S_REF, VOL_REF, 2.0), 2,
                            signed=True) + " contre "
            + num(rho_forward_fixe(S_REF, S_REF, VOL_REF, 2.0), 2,
                  signed=True)),
        Affirmation(
            "Une option très dans la monnaie est une action financée",
            "le risque",
            "exact : " + num(100 * (th.call(2 * S_REF, S_REF, VOL_REF,
                                            T_FINANCEE)
                                    - action_financee(2 * S_REF, S_REF,
                                                      T_FINANCEE))
                             / th.call(2 * S_REF, S_REF, VOL_REF,
                                       T_FINANCEE), 2)
            + " % d'écart à deux fois le strike"),
        Affirmation(
            "Pour un intrajournalier sur indice liquide, rho est négligeable "
            "et le traiter comme tel est correct",
            "rien",
            "exact, et de très loin : "
            + num(FRICTION / cout_de_rho(JOURS_INTRA), 0)
            + " fois sous la friction"),
    )


def compte_par_grandeur() -> dict[str, int]:
    out: dict[str, int] = {}
    for a in affirmations():
        out[a.grandeur] = out.get(a.grandeur, 0) + 1
    return out


def familles() -> tuple[tuple[str, int], ...]:
    """Les cinq parties d'options, comptées dans leurs propres modules."""
    return vg.familles() + (("Rho, partie XXIII", len(affirmations())),)


def table_reste() -> Table:
    rows = [[a.enonce, a.grandeur, a.mesure] for a in affirmations()]
    c = compte_par_grandeur()
    return Table(
        key="rh_reste",
        caption="Sept affirmations, et le décompte des cinq parties d'options",
        headers=["L'affirmation", "Ce qu'elle déplace",
                 "Ce que la mesure en dit"],
        rows=rows,
        note="Le décompte se lit dans l'identité `E[R] = (µ·E[τ∧T] − c)/a` : "
             + num(c.get("le risque", 0), 0) + " affirmations déplacent le "
             "**risque**, " + num(c.get("l'horloge", 0), 0) + " l'horloge, "
             + num(c.get("rien", 0), 0) + " ne déplacent rien, et **aucune "
             "ne touche à la direction**. C'est la première des cinq parties "
             "d'options dont la colonne de direction est vide, et ce n'est "
             "pas un hasard : rho est le seul des grecs dont le moteur ne "
             "soit pas le prix. Sur les "
             + num(sum(n for _, n in familles()), 0) + " affirmations des "
             "cinq parties, *aucune ne donne un sens* — et les trois qui "
             "prétendaient en donner un disaient toutes qu'il n'y en a pas. "
             "La série se ferme donc là où la partie IV l'avait posée : ce "
             "qui se récupère d'un guide est une méthode de lecture, jamais "
             "une direction. Deux des sept affirmations ci-dessus sont "
             "**justes et utiles** — le forward et l'action financée — et "
             "elles ne changent rien à ce verdict : elles disent comment "
             "compter, pas où aller.",
        wrap_cols=[0, 2],
    )


# ---------------------------------------------------------------------------
# Les quatre reliefs
# ---------------------------------------------------------------------------
#
# Comme partout dans ce document, les axes sont écrits de façon que le
# **maximum tombe au coin du fond** : en projection isométrique le coin (0, 0)
# est le plus éloigné, et un relief qui monte vers l'horizon se lit.

SURF_SIGMA: tuple[float, ...] = (0.08, 0.12, 0.20, 0.30, 0.45, 0.65)
SURF_KAPPA: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0, 16.0, 32.0)

SURF_SIGMA_COUT: tuple[float, ...] = (0.65, 0.45, 0.30, 0.20, 0.12, 0.08)
SURF_ECHEANCE: tuple[float, ...] = (7665.0, 3650.0, 1825.0, 730.0, 365.0,
                                    90.0)

SURF_ECHEANCE_ECART: tuple[float, ...] = (1825.0, 1095.0, 730.0, 365.0,
                                          180.0, 90.0)
SURF_MONEYNESS: tuple[float, ...] = (2.00, 1.60, 1.30, 1.10, 1.00, 0.85)

SURF_TAUX: tuple[float, ...] = (0.09, 0.07, 0.05, 0.035, 0.02, 0.01)
SURF_ECHEANCE_USURE: tuple[float, ...] = (3650.0, 1825.0, 1095.0, 730.0,
                                          365.0, 90.0)

#: Le plafond du relief de croisement, en années : au-delà, l'échéance n'est
#: plus négociée et la valeur exacte ne dit plus rien.
PLAFOND_CROISEMENT = 60.0


@lru_cache(maxsize=2)
def surface_croisement() -> tuple[tuple[float, ...], ...]:
    """Le croisement rho-véga en années, en dispersion de taux et en `κ`."""
    out = []
    for s in SURF_SIGMA:
        ligne = []
        for k in SURF_KAPPA:
            j = _croisement(
                lambda x: risque_rho(x, s)
                - vg.vega_par_point(S_REF, S_REF, VOL_REF, x / JOURS_AN,
                                    TAUX, DIVIDENDE)
                * DISPERSION_VOL * vg.poids_modele(x, k))
            ligne.append(min(PLAFOND_CROISEMENT, j / JOURS_AN))
        out.append(tuple(ligne))
    return tuple(out)


@lru_cache(maxsize=2)
def surface_cout() -> tuple[tuple[float, ...], ...]:
    """Le coût d'une séance en unités de friction, en dispersion et échéance."""
    return tuple(tuple(cout_de_rho(j, s) / FRICTION
                       for j in SURF_ECHEANCE)
                 for s in SURF_SIGMA_COUT)


@lru_cache(maxsize=2)
def surface_ecart() -> tuple[tuple[float, ...], ...]:
    """L'écart entre les deux rhos, en échéance et en moneyness."""
    out = []
    for j in SURF_ECHEANCE_ECART:
        t = j / JOURS_AN
        out.append(tuple(
            rho_par_point(S_REF * m, S_REF, VOL_REF, t)
            - rho_forward_fixe(S_REF * m, S_REF, VOL_REF, t)
            for m in SURF_MONEYNESS))
    return tuple(out)


@lru_cache(maxsize=2)
def surface_usure() -> tuple[tuple[float, ...], ...]:
    """L'usure de la proportionnalité — `1 − exposant` — en taux et échéance."""
    return tuple(tuple(1.0 - exposant_effectif(j, S_REF, S_REF, VOL_REF, r,
                                               DIVIDENDE)
                       for j in SURF_ECHEANCE_USURE)
                 for r in SURF_TAUX)


# ---------------------------------------------------------------------------
# Valeurs, tables, et exécution directe
# ---------------------------------------------------------------------------


def values() -> dict[str, str]:
    court = rho_par_point(S_REF, S_REF, VOL_REF, JOURS_COURT / JOURS_AN)
    long_ = rho_par_point(S_REF, S_REF, VOL_REF, JOURS_LONG / JOURS_AN)
    ref0 = rho_par_point(S_REF, S_REF, VOL_REF, 2.0, 0.0, DIVIDENDE)
    haut = rho_par_point(S_REF, S_REF, VOL_REF, 2.0, 0.08, DIVIDENDE)
    c2 = th.call(2 * S_REF, S_REF, VOL_REF, T_FINANCEE)
    f2 = action_financee(2 * S_REF, S_REF, T_FINANCEE)
    return {
        "rh_court": num(court, 4),
        "rh_long": num(long_, 4),
        "rh_rapport": num(long_ / court, 1),
        "rh_rapport_annonce": num(RAPPORT_ANNONCE, 0),
        "rh_facteur_annonce": num(RAPPORT_ANNONCE / (long_ / court), 1),
        "rh_exposant_90": num(exposant_effectif(90.0), 3),
        "rh_exposant_365": num(exposant_effectif(365.0), 3),
        "rh_exposant_730": num(exposant_effectif(730.0), 3),
        "rh_pic": num(echeance_du_pic(), 1),
        "rh_pic_inverse": num(1.0 / TAUX, 1),
        "rh_pic_nul": num(echeance_du_pic(S_REF, S_REF, VOL_REF, 1e-9,
                                          DIVIDENDE), 0),
        "rh_taux_pic": num(100 * taux_du_pic_exact(), 2),
        "rh_eventail_long": num(
            100.0 * (rho_call(1.3 * S_REF, S_REF, VOL_REF, 30.0)
                     - rho_call(0.8 * S_REF, S_REF, VOL_REF, 30.0))
            / rho_plafond(S_REF, 30.0), 0),
        "rh_eventail_court": num(
            100.0 * (rho_call(1.3 * S_REF, S_REF, VOL_REF, 0.25)
                     - rho_call(0.8 * S_REF, S_REF, VOL_REF, 0.25))
            / rho_plafond(S_REF, 0.25), 0),
        "rh_ecart5": num(echeance_de_l_ecart(0.05), 0),
        "rh_ecart10": num(echeance_de_l_ecart(0.10), 0),
        "rh_dispersion_vol": num(DISPERSION_VOL, 2),
        "rh_dispersion_taux": num(DISPERSION_TAUX, 2),
        "rh_rapport_moteurs": num(DISPERSION_VOL / DISPERSION_TAUX, 0),
        "rh_croisement_unite": num(croisement_unite(), 0),
        "rh_croisement_mois": num(croisement_unite() / 30.0, 1),
        "rh_croisement_structure": num(croisement_structure() / JOURS_AN, 1),
        "rh_croisement_bas": num(
            croisement_structure(DISPERSIONS_TAUX[-1]) / JOURS_AN, 1),
        "rh_croisement_haut": num(
            croisement_structure(DISPERSIONS_TAUX[0]) / JOURS_AN, 1),
        "rh_sigma_un_an": num(dispersion_pour_un_an(), 2),
        "rh_regime_bas": num(ref0, 4),
        "rh_regime_haut": num(haut, 4),
        "rh_regime_hausse": num(100 * (haut / ref0 - 1.0), 0),
        "rh_spot_2ans": num(rho_par_point(S_REF, S_REF, VOL_REF, 2.0), 3,
                            signed=True),
        "rh_fwd_2ans": num(rho_forward_fixe(S_REF, S_REF, VOL_REF, 2.0), 3,
                           signed=True),
        "rh_ecart_2ans": num(rho_par_point(S_REF, S_REF, VOL_REF, 2.0)
                             - rho_forward_fixe(S_REF, S_REF, VOL_REF, 2.0),
                             3),
        "rh_financee_ecart": num(c2 - f2, 3),
        "rh_financee_call": num(c2, 1),
        "rh_financee_relatif": num(100 * (c2 - f2) / c2, 2),
        "rh_financee_part": num(
            100 * rho_call(2 * S_REF, S_REF, VOL_REF, T_FINANCEE)
            / rho_plafond(S_REF, T_FINANCEE), 0),
        "rh_friction": num(FRICTION, 2),
        "rh_intra": num(FRICTION / cout_de_rho(JOURS_INTRA), 0),
        "rh_cout_10ans": num(cout_de_rho(3650.0) / FRICTION, 2),
        "rh_affirmations": num(len(affirmations()), 0),
        "rh_total_options": num(sum(n for _, n in familles()), 0),
        "rh_vol": num(100 * VOL_REF, 0),
        "rh_taux": num(100 * TAUX, 1),
    }


def all_tables() -> dict[str, Table]:
    tables = [table_echelle(), table_deux_nombres(), table_croisement(),
              table_regime(), table_forward(), table_financee(),
              table_cout(), table_reste()]
    return {t.key: t for t in tables}


def main() -> None:
    for t in all_tables().values():
        print(t.to_text())
        print()
    for k, v in values().items():
        print(f"{k:26s} {v}")


if __name__ == "__main__":
    main()
