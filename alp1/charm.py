"""La saignée du delta, et les deux horloges d'un week-end.

Septième document de la série d'options, consacré au charm. C'est le premier
des sept dont l'usage recommandé **ne demande aucun signe** : il dit comment
votre propre exposition bougera si vous ne faites rien, ce qui est un outil de
planification et non une prévision. Sur ce point le dépôt n'a rien à
corriger — et il le dit, parce que les parties XIX et XXIV ont mesuré ce qu'il
en coûte quand il faut deviner le signe de quelqu'un d'autre.

Sur le reste, sept affirmations sont reprises. Une tient, six se corrigent, et
la plus lourde n'oppose pas ce guide à ce dépôt : **elle l'oppose au guide du
thêta de la même série.**

I. L'accélération, et la puissance qu'on lui prête
----------------------------------------------------
Le guide écrit que le `T^{3/2}` du dénominateur fait que le charm « accélère
fort dans les dernières séances ». Le dénominateur porte bien cette puissance,
mais le numérateur porte `d₂σ√T`, qui en annule une moitié : l'amplitude au
pic croît comme **`1/T`**, exposant mesuré `−0,99`, et sa limite est
`φ(1)/(2T)` — la forme fermée que la partie XX avait déjà établie.

II. Le pic n'est pas à vingt-cinq deltas
------------------------------------------
« Le charm est le plus grand vers vingt-cinq et soixante-quinze deltas. » La
mesure rend **seize et quatre-vingt-cinq**, et le lieu est en forme fermée :
`d₁* = (σ√T − √(σ²T + 4))/2`, la racine de la partie XX, **la même que le pic
du vanna** de la partie XXIV.

Le guide illustre par ailleurs son propre mécanisme au mauvais strike : à un
jour de l'échéance, un call à quatre pour cent hors de la monnaie porte
`0,0009` de delta. *Il n'a plus rien à perdre.* Le phénomène vit à un pour
cent trois de la monnaie, où l'option perd les trois quarts de son delta dans
la nuit.

III. « La ligne à la monnaie est proche de zéro »
---------------------------------------------------
Elle n'est pas nulle, et elle **diverge** aussi — en `1/√T` quand le pic
diverge en `1/T`. Le rapport des deux vaut cinquante et un à un jour et onze à
trente : « proche de zéro » décrit un rapport qui s'effondre avec l'échéance.
L'explication donnée — une option exactement à la monnaie garde un demi delta
jusqu'au coup de cloche — est juste sur la limite et fausse sur la vitesse.

IV. Le week-end, et les deux horloges de la même série
--------------------------------------------------------
« Le charm court sur le temps calendaire, le gamma paie sur le temps de
bourse. » C'est le résultat structurant du guide, et **le guide du thêta de la
même série a publié l'observation qui le contredit** : on voit passer plutôt
un jour de décroissance sur un week-end, pas trois. La partie XXI a employé
cette observation pour calibrer le seul paramètre non observable du modèle,
`ω = 0,2566`. Sous cette horloge, la saignée d'un week-end vaut **le tiers au
quart** de ce que le calendrier annonce — et l'écart est le plus grand sur les
ailes, c'est-à-dire exactement là où le guide dit que les positions dérivent
le plus.

V. Ce que coûte de couvrir au delta du soir
----------------------------------------------
« Calculez le delta de demain, pas celui d'aujourd'hui ; pour tout ce qui est
à moins de deux semaines, réévaluez à `T − 1`. » La règle est juste et le
seuil est trop court : le coût attendu de couvrir au delta du soir tombe sous
la friction de la géométrie déclarée à **trente et un jours**, pas à
quatorze. C'est la troisième fois de la série qu'un guide se sous-estime.

VI. Le strangle ne saigne pas symétriquement
-----------------------------------------------
« Un strangle saigne son delta symétriquement vers l'extérieur. » Le charm net
d'un strangle symétrique en delta vaut **`−φ(z)·σ/√T`**, une forme fermée qui
n'est nulle à aucun delta et à aucune échéance. Les deux jambes perdent bien
leur delta, mais le livre devient **plus court** en le faisant, et la part non
compensée passe de sept à quatre-vingt-neuf pour cent selon le delta et
l'échéance.

VII. Le décompte, sur sept parties
-------------------------------------
Sur les cinquante et une affirmations des sept parties d'options, aucune ne
donne un sens. Ce septième guide est pourtant le seul dont l'usage recommandé ne
dépende d'aucun signe, et le dépôt le dit sans réserve.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from . import grandeurs as G
from . import niveaux as nv
from . import quant as q
from . import theta as th
from . import vanna as va
from . import vega as vg
from .costs import COST_BASE, ES, norm_cdf
from .report import Table, num

SEED = 20260918

S_REF = va.S_REF
VOL_REF = va.VOL_REF
TAUX = va.TAUX
DIVIDENDE = va.DIVIDENDE
JOURS_AN = nv.JOURS_AN

FRICTION = COST_BASE.friction_points(ES)

#: L'écart-type d'une séance, sur `JOURS_BOURSE` séances par an.
ECART_SEANCE = VOL_REF / math.sqrt(th.JOURS_BOURSE)

#: `E|Z|` pour une normale centrée réduite.
ESPERANCE_ABS = math.sqrt(2.0 / math.pi)


def _phi(x : float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


# ---------------------------------------------------------------------------
# I. L'accélération, et la puissance qu'on lui prête
# ---------------------------------------------------------------------------


def bleed(s : float, k : float, t : float, vol : float = VOL_REF,
          r : float = TAUX, div : float = DIVIDENDE) -> float:
    """`∂Δ/∂t` rapporté à la journée. La forme fermée vit dans `grandeurs`."""
    return G.charm(s, k, vol, t, r, div) / JOURS_AN


def bleed_numerique(s : float, k : float, t : float, vol : float = VOL_REF,
                    r : float = TAUX, div : float = DIVIDENDE,
                    h : float = 1e-6) -> float:
    """Le contrôle : une différence finie sur l'échéance, de signe renversé.

    Le temps calendaire s'écoule dans le sens inverse de l'échéance ; c'est la
    seule subtilité de cette dérivée, et c'est pour cela qu'on la contrôle.
    """
    return (G.delta_comptant(s, k, vol, t - h, r, div)
            - G.delta_comptant(s, k, vol, t + h, r, div)) / (2.0 * h
                                                             * JOURS_AN)


def exposant_du_pic(jours : float, vol : float = VOL_REF) -> float:
    """`d ln|charm au pic| / d ln T` — l'exposant mesuré, et non postulé."""
    t = jours / JOURS_AN
    h = 1e-3
    a = math.log(G.bleed_du_pic(vol, t * (1.0 - h)))
    b = math.log(G.bleed_du_pic(vol, t * (1.0 + h)))
    return (b - a) / (2.0 * h)


#: Échéances balayées, en jours.
JOURS : tuple[float, ...] = (0.5, 1.0, 3.0, 7.0, 14.0, 30.0, 60.0)

#: La puissance que le guide met au dénominateur.
PUISSANCE_ANNONCEE = 1.5


def table_acceleration() -> Table:
    rows = []
    for j in JOURS:
        t = j / JOURS_AN
        rows.append([
            num(j, 1),
            num(G.bleed_du_pic(VOL_REF, t), 5),
            num(G.amplitude_asymptotique(t), 5),
            num(100 * (G.bleed_du_pic(VOL_REF, t)
                       / G.amplitude_asymptotique(t) - 1.0), 1),
            num(exposant_du_pic(j), 3),
            num(-PUISSANCE_ANNONCEE, 1),
        ])
    return Table(
        key="ch_acceleration",
        caption="À quelle vitesse la saignée accélère, et la puissance qu'on lui prête",
        headers=["Jours", "Saignée au pic (delta par jour)",
                 "Asymptote `φ(1)/2T`", "Écart à l'asymptote (%)",
                 "Exposant mesuré", "Exposant annoncé"],
        rows=rows,
        note="Le guide écrit que le `T^{3/2}` du dénominateur fait que le "
             "charm « accélère fort dans les dernières séances ». Le "
             "dénominateur porte bien cette puissance — la forme fermée est "
             "recopiée telle quelle dans `grandeurs.charm` — mais le "
             "numérateur porte `d₂σ√T`, et le `√T` en annule la moitié. "
             "L'exposant local de l'amplitude au pic vaut "
             + num(exposant_du_pic(30.0), 2) + " à trente jours et "
             + num(exposant_du_pic(1.0), 2) + " à un jour : c'est "
             "**`1/T`**, pas `T^{−3/2}`, et la différence est un facteur "
             "`√T` sur toute la description. La colonne de l'asymptote est "
             "la forme fermée que la partie XX avait établie, `φ(1)/(2T)` par "
             "an : elle serre la mesure à quelques pour cent, et de "
             "mieux en mieux quand l'échéance raccourcit. *L'accélération que "
             "le guide décrit est réelle ; c'est sa puissance qui est "
             "fausse, et il l'a lue dans une formule sans la dériver.*",
    )


# ---------------------------------------------------------------------------
# II. Le pic n'est pas à vingt-cinq deltas
# ---------------------------------------------------------------------------

#: Les deltas où le guide place le pic.
DELTA_ANNONCE = 0.25

#: Le strike que le guide choisit pour son illustration, en écart relatif.
ECART_ILLUSTRATION = 0.04


def delta_du_pic(t : float, vol : float = VOL_REF) -> float:
    """Le delta de l'option où la saignée culmine."""
    return G.delta_comptant(S_REF * G.moneyness_du_pic(vol, t), S_REF, vol, t,
                            TAUX, DIVIDENDE)


def pic_balaye(t : float, vol : float = VOL_REF,
               n : int = 120000) -> tuple[float, float]:
    """Le contrôle : le minimum de la saignée sur un balayage de moneyness."""
    best = (0.0, math.inf)
    for i in range(n + 1):
        m = 0.50 + 1.0 * i / n
        c = bleed(S_REF * m, S_REF, t, vol)
        if c < best[1]:
            best = (m, c)
    return best


def part_perdue_dans_la_nuit(moneyness : float, t : float,
                             vol : float = VOL_REF) -> float:
    """La part du delta qu'une option perd en une séance, à prix immobile."""
    d = G.delta_comptant(S_REF * moneyness, S_REF, vol, t, TAUX, DIVIDENDE)
    if d <= 0.0:
        return 0.0
    suite = G.delta_comptant(S_REF * moneyness, S_REF, vol,
                             max(1e-9, t - 1.0 / JOURS_AN), TAUX, DIVIDENDE)
    return (d - suite) / d


def table_pic() -> Table:
    rows = []
    for j in JOURS:
        t = j / JOURS_AN
        m = G.moneyness_du_pic(VOL_REF, t)
        mb, cb = pic_balaye(t)
        rows.append([
            num(j, 1),
            num(m, 4),
            num(mb, 4),
            num(100 * delta_du_pic(t), 1),
            num(100 * DELTA_ANNONCE, 0),
            num(100 * part_perdue_dans_la_nuit(m, t), 1),
        ])
    t1 = 1.0 / JOURS_AN
    return Table(
        key="ch_pic",
        caption="Où la saignée culmine, et le strike que le guide choisit pour l'illustrer",
        headers=["Jours", "S/K du pic (forme fermée)", "S/K balayé (contrôle)",
                 "Delta au pic (%)", "Delta annoncé (%)",
                 "Part du delta perdue en une séance (%)"],
        rows=rows,
        note="« Le charm est le plus grand vers vingt-cinq et soixante-quinze "
             "deltas, pas à la monnaie. » La première moitié de la phrase "
             "est fausse et la seconde est juste. Le lieu du pic est en forme "
             "fermée — `d₁* = (σ√T − √(σ²T + 4))/2`, la racine que la partie "
             "XX avait établie et que la partie XXIV a retrouvée sur le pic "
             "du **vanna**, les deux grandeurs étant `φ(d₁)` multipliée par "
             "une fonction affine de `d₁` — et le balayage la confirme. Le "
             "delta au pic vaut " + num(100 * delta_du_pic(t1), 0) + " % à un "
             "jour et " + num(100 * delta_du_pic(60.0 / JOURS_AN), 0)
             + " % à deux mois, jamais vingt-cinq ; le second pic est à "
             "son image au-dessus, vers quatre-vingt-cinq.\n\nLa dernière "
             "colonne dit ce que le pic vaut : à un jour de l'échéance, "
             "l'option qui y est porte "
             + num(G.delta_comptant(S_REF * G.moneyness_du_pic(VOL_REF, t1),
                                    S_REF, VOL_REF, t1, TAUX, DIVIDENDE), 3)
             + " de delta au soir et **rien** au matin. *Le guide illustre "
             "pourtant ce mécanisme sur un "
             "call à quatre pour cent hors de la monnaie*, qui à un jour "
             "porte " + num(G.delta_comptant(
                 S_REF * (1.0 - ECART_ILLUSTRATION), S_REF, VOL_REF, t1,
                 TAUX, DIVIDENDE), 4) + " de delta : il n'a plus rien à "
             "perdre, et la phrase « il perd l'essentiel de son delta » y est "
             "vraie sans rien dire. Le phénomène vit à "
             + num(100 * (1.0 - G.moneyness_du_pic(VOL_REF, t1)), 1)
             + " % de la monnaie, pas à quatre.",
    )


# ---------------------------------------------------------------------------
# III. La ligne à la monnaie
# ---------------------------------------------------------------------------


def exposant_a_la_monnaie(jours : float, vol : float = VOL_REF) -> float:
    """`d ln|charm à la monnaie| / d ln T`."""
    t = jours / JOURS_AN
    h = 1e-3
    a = math.log(abs(bleed(S_REF, S_REF, t * (1.0 - h), vol)))
    b = math.log(abs(bleed(S_REF, S_REF, t * (1.0 + h), vol)))
    return (b - a) / (2.0 * h)


def table_monnaie() -> Table:
    rows = []
    for j in JOURS:
        t = j / JOURS_AN
        atm = abs(bleed(S_REF, S_REF, t))
        pic = G.bleed_du_pic(VOL_REF, t)
        rows.append([
            num(j, 1),
            num(atm, 5),
            num(pic, 5),
            num(pic / atm, 1),
            num(exposant_a_la_monnaie(j), 3),
            num(exposant_du_pic(j), 3),
        ])
    t1, t30 = 1.0 / JOURS_AN, 30.0 / JOURS_AN
    return Table(
        key="ch_monnaie",
        caption="La ligne à la monnaie n'est pas nulle, et elle diverge aussi",
        headers=["Jours", "Saignée à la monnaie (delta par jour)",
                 "Saignée au pic", "Rapport",
                 "Exposant à la monnaie", "Exposant au pic"],
        rows=rows,
        note="Le guide explique que sa courbe à la monnaie « reste près de "
             "zéro parce qu'une vraie option à la monnaie garde 0,50 delta "
             "jusqu'au coup de cloche ». La conclusion sur la **limite** est "
             "juste ; celle sur la **vitesse** ne l'est pas. À la "
             "monnaie, `d₁` vaut `(r − q + σ²/2)√T/σ` et la dérivée du delta "
             "en échéance porte un `1/√T`: elle **diverge**, comme "
             "celle du pic, simplement deux fois moins vite. Les deux "
             "dernières colonnes le donnent chiffré — exposant "
             + num(exposant_a_la_monnaie(1.0), 2) + " contre "
             + num(exposant_du_pic(1.0), 2) + " à un jour. *Ce qui « reste "
             "près de zéro » n'est donc pas une quantité, c'est un "
             "rapport*, et ce rapport s'effondre : il vaut "
             + num(G.bleed_du_pic(VOL_REF, t1) / abs(bleed(S_REF, S_REF, t1)),
                   0) + " à un jour et seulement "
             + num(G.bleed_du_pic(VOL_REF, t30)
                   / abs(bleed(S_REF, S_REF, t30)), 0) + " à trente. Sur une "
             "option d'un mois, la saignée à la monnaie est du même ordre "
             "que celle du pic, et un livre qui la néglige néglige un dixième "
             "de son objet.",
    )


# ---------------------------------------------------------------------------
# IV. Le week-end, et les deux horloges de la même série
# ---------------------------------------------------------------------------
#
# C'est le résultat structurant du guide, et il n'oppose pas ce guide à ce
# dépôt : il l'oppose au guide du thêta de la même série, dont l'observation
# publiée a servi à la partie XXI pour calibrer le seul paramètre non
# observable du modèle.

#: Les jours calendaires qu'un week-end consomme.
JOURS_WEEKEND = 3.0

#: Le poids d'un jour non ouvré, calibré dans la partie XXI sur l'observation
#: que le guide du thêta publie : on voit passer plutôt un jour, pas trois.
POIDS_CALIBRE = th.poids_pour_apparents(1.0)

#: Poids balayés. À un, on retrouve exactement l'horloge que le guide du charm
#: suppose ; à zéro, l'horloge de bourse pure. Le paramètre n'est pas
#: observable et le dépôt le balaie plutôt que de le choisir.
POIDS_GRILLE: tuple[float, ...] = th.POIDS_GRILLE

#: Échéances balayées pour le week-end, en jours calendaires.
JOURS_WE: tuple[float, ...] = (5.0, 7.0, 10.0, 14.0, 21.0, 30.0)

#: Moneyness balayées pour le week-end.
MONEYNESS_WE: tuple[float, ...] = (0.97, 1.00, 1.03)


def saignee_calendaire(moneyness: float, jours: float,
                       vol: float = VOL_REF) -> float:
    """La variation de delta d'un week-end, volatilité tenue fixe."""
    t = jours / JOURS_AN
    s = S_REF * moneyness
    return (G.delta_comptant(s, S_REF, vol, t - JOURS_WEEKEND / JOURS_AN,
                             TAUX, DIVIDENDE)
            - G.delta_comptant(s, S_REF, vol, t, TAUX, DIVIDENDE))


def saignee_horloge(moneyness: float, jours: float, poids: float,
                    vol: float = VOL_REF) -> float:
    """La même variation, la volatilité implicite montant comme la partie XXI.

    Si le marché ne consomme sur un week-end que `3ω` jours de bourse, il
    remonte l'implicite d'autant pour que la variance restant à courir ne
    tombe que de ce qu'elle doit. C'est exactement la hausse que la partie XXI
    calcule, et le module l'importe plutôt que de la récrire.
    """
    hausse = th.derive_implicite(jours, poids)
    if not math.isfinite(hausse):
        return math.nan
    t = jours / JOURS_AN
    s = S_REF * moneyness
    return (G.delta_comptant(s, S_REF, vol * (1.0 + hausse),
                             t - JOURS_WEEKEND / JOURS_AN, TAUX, DIVIDENDE)
            - G.delta_comptant(s, S_REF, vol, t, TAUX, DIVIDENDE))


#: Le jour où le week-end commence, dans la planche de dix jours du guide.
DEBUT_WEEKEND = 4.0


def temps_de_marche(ecoule: float, jours: float, poids: float,
                    debut: float = DEBUT_WEEKEND) -> float:
    """Le temps de marché restant, en jours de bourse équivalents.

    Une séance en consomme un, un jour non ouvré en consomme `ω`. Le total sur
    la vie de l'option est fixé — l'option expire sur le calendrier, pas sur
    l'horloge de marché — donc ce que le week-end fait n'est pas de raccourcir
    la vie mais de **redistribuer** quand la variance se consomme.
    """
    e = min(max(ecoule, 0.0), jours)
    avant = min(e, debut)
    pendant = min(max(e - debut, 0.0), JOURS_WEEKEND)
    apres = max(e - debut - JOURS_WEEKEND, 0.0)
    return avant + poids * pendant + apres


def delta_sur_horloge(moneyness: float, ecoule: float, jours: float,
                      poids: float, vol: float = VOL_REF,
                      debut: float = DEBUT_WEEKEND) -> float:
    """Le delta après `ecoule` jours, la variance suivant l'horloge de marché.

    La variance restante est la fraction de temps de marché qui reste,
    multipliée par la variance totale. La volatilité implicite s'ajuste donc
    pour que le produit `σ²·(T − t)` suive cette fraction — c'est la même
    hypothèse que `saignee_horloge`, écrite en chemin plutôt qu'en saut.
    """
    total = temps_de_marche(jours, jours, poids, debut)
    reste = total - temps_de_marche(ecoule, jours, poids, debut)
    t = max(1e-9, (jours - ecoule) / JOURS_AN)
    var = vol * vol * (jours / JOURS_AN) * max(0.0, reste) / total
    return G.delta_comptant(S_REF * moneyness, S_REF,
                            max(1e-6, math.sqrt(var / t)), t, TAUX, DIVIDENDE)


def facteur_du_calendrier(moneyness: float, jours: float,
                          poids: float = POIDS_CALIBRE) -> float:
    """De combien l'horloge calendaire surestime la saignée d'un week-end."""
    a = saignee_calendaire(moneyness, jours)
    b = saignee_horloge(moneyness, jours, poids)
    if not math.isfinite(b) or abs(b) < 1e-12:
        return math.nan
    return a / b


def table_weekend() -> Table:
    rows = []
    for j in JOURS_WE:
        hausse = th.derive_implicite(j, POIDS_CALIBRE)
        for m in MONEYNESS_WE:
            rows.append([
                num(j, 0),
                num(m, 2),
                num(saignee_calendaire(m, j), 4, signed=True),
                num(saignee_horloge(m, j, POIDS_CALIBRE), 4, signed=True),
                num(facteur_du_calendrier(m, j), 2),
                num(100 * hausse, 1),
            ])
    return Table(
        key="ch_weekend",
        caption="La saignée d'un week-end, sous les deux horloges de la même série",
        headers=["Jours à l'échéance", "S/K",
                 "Sur l'horloge calendaire", "Sur l'horloge calibrée",
                 "Facteur de surestimation",
                 "Hausse d'implicite qu'elle impose (%)"],
        rows=rows,
        note="« Le charm court sur le temps calendaire, le gamma paie sur le "
             "temps de bourse. Sur un week-end les deux se découplent : un "
             "livre de vendredi après-midi porte trois jours de saignée de "
             "delta jusqu'à lundi pour un seul jour de variance. » C'est le "
             "résultat structurant du guide, et **le guide du thêta de la "
             "même série a publié l'observation qui le contredit** : sur un "
             "week-end on voit passer plutôt un jour de décroissance, pas "
             "trois. La partie XXI a employé cette observation pour calibrer "
             "le seul paramètre non observable du modèle, `ω = "
             + num(POIDS_CALIBRE, 4) + "`, et le module l'importe ici plutôt "
             "que de le récrire.\n\nLes deux horloges ne diffèrent pas d'un "
             "détail. Sur l'horloge calibrée, la volatilité implicite monte "
             "de la dernière colonne pour que la variance restant à courir ne "
             "tombe que d'un jour apparent, et cette hausse **relève** `σ√T`, "
             "donc elle retient le delta. La saignée mesurée vaut alors le "
             "tiers au quart de ce que le calendrier annonce, et le facteur "
             "est le plus grand **sur les ailes** — c'est-à-dire exactement "
             "là où le guide dit que les positions dérivent le plus. À la "
             "monnaie il tombe à un, parce que le delta y est immobile de "
             "toute façon. *Les deux documents de cette série ne peuvent pas "
             "avoir raison ensemble, et c'est celui du thêta qui a publié une "
             "mesure.*",
    )


def table_horloges() -> Table:
    rows = []
    for w in POIDS_GRILLE:
        f = facteur_du_calendrier(0.97, 10.0, w)
        rows.append([
            num(w, 4),
            num(th.jours_apparents(w), 2),
            num(100 * th.derive_implicite(10.0, w), 1),
            num(saignee_horloge(0.97, 10.0, w), 4, signed=True),
            num(f, 2),
        ])
    return Table(
        key="ch_horloges",
        caption="Le paramètre qu'on ne peut pas observer, et ce qu'il décide",
        headers=["Poids d'un jour non ouvré", "Jours apparents d'un week-end",
                 "Hausse d'implicite (%)",
                 "Saignée sur dix jours, trois pour cent hors de la monnaie",
                 "Facteur de surestimation du calendrier"],
        rows=rows,
        note="Le poids d'un jour non ouvré n'est pas observable dans ce "
             "dépôt, et il est donc balayé plutôt que choisi — la règle "
             "appliquée à la taille de grappe du footprint, à la hauteur de "
             "rangée du TPO et à la volatilité de la volatilité de la partie "
             "XXII. Les deux bouts de la table sont les deux conventions : à "
             "un, le week-end vaut trois jours pleins, la hausse "
             "d'implicite est nulle et **on retrouve exactement la lecture "
             "du guide du charm**, facteur un ; à zéro, il ne consomme aucun "
             "temps de marché et la saignée tombe à un vingt-septième. Entre "
             "les deux, la "
             "ligne calibrée sur l'observation du guide du thêta — un jour "
             "apparent — rend un facteur "
             + num(facteur_du_calendrier(0.97, 10.0), 1) + ". *Le désaccord "
             "entre les deux documents n'est donc pas une question de fait "
             "mais de paramètre, et l'un des deux a publié la mesure qui le "
             "fixe.* Il reste que la lecture calendaire est le cas limite le "
             "plus défavorable de toute la plage, et qu'un pupitre qui "
             "l'emploie surestime sa dérive de delta quoi qu'il arrive.",
    )


# ---------------------------------------------------------------------------
# V. Ce que coûte de couvrir au delta du soir
# ---------------------------------------------------------------------------

#: Le seuil que le guide donne, en jours.
SEUIL_ANNONCE = 14.0


def cout_du_delta_du_soir(jours: float, moneyness: float | None = None,
                          vol: float = VOL_REF) -> float:
    """Le coût attendu, en points d'indice, d'une couverture posée au soir.

    L'erreur de couverture est la saignée d'une séance ; ce qu'elle coûte est
    cette erreur multipliée par le déplacement du lendemain, dont l'espérance
    absolue vaut `√(2/π)` écart-type. Le résultat se compare à la friction de
    la géométrie déclarée, qui est l'unité de tout ce document.
    """
    t = jours / JOURS_AN
    m = G.moneyness_du_pic(vol, t) if moneyness is None else moneyness
    err = abs(bleed(S_REF * m, S_REF, t, vol))
    return err * ECART_SEANCE * q.INDEX_LEVEL * ESPERANCE_ABS


def echeance_du_seuil(cible: float = FRICTION, vol: float = VOL_REF) -> float:
    """L'échéance, en jours, où ce coût tombe sous la friction."""
    lo, hi = 0.5, 4000.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if cout_du_delta_du_soir(mid, None, vol) > cible:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


#: Échéances balayées pour le coût, en jours.
JOURS_COUT: tuple[float, ...] = (1.0, 3.0, 7.0, 14.0, 21.0, 30.0, 60.0, 90.0)


def table_cout() -> Table:
    rows = []
    for j in JOURS_COUT:
        t = j / JOURS_AN
        m = G.moneyness_du_pic(VOL_REF, t)
        rows.append([
            num(j, 0),
            num(abs(bleed(S_REF * m, S_REF, t)), 5),
            num(cout_du_delta_du_soir(j), 4),
            num(cout_du_delta_du_soir(j) / FRICTION, 2),
            num(cout_du_delta_du_soir(j, 1.0), 4),
        ])
    seuil = echeance_du_seuil()
    return Table(
        key="ch_cout",
        caption="Ce que coûte de couvrir au delta du soir, en unités de la friction",
        headers=["Jours", "Erreur de delta (une séance)",
                 "Coût attendu (points d'indice)", "En unités de friction",
                 "Le même coût à la monnaie"],
        rows=rows,
        note="« Calculez le delta de demain, pas celui d'aujourd'hui : pour "
             "tout ce qui est à moins de deux semaines, réévaluez le livre à "
             "`T − 1` avant de décider la couverture du soir. » C'est la "
             "seule note de pupitre des sept documents qui se convertisse "
             "directement dans l'unité de celui-ci, et la table la convertit. "
             "L'erreur de couverture est la saignée d'une séance ; ce qu'elle "
             "coûte est cette erreur multipliée par le déplacement du "
             "lendemain, dont l'espérance absolue vaut `√(2/π)` écart-type. "
             "Le résultat se lit contre la friction de la géométrie "
             "déclarée, " + num(FRICTION, 2) + " point d'indice.\n\nLa règle "
             "est juste et **son seuil est trop court**. Le coût ne tombe "
             "sous la friction qu'à " + num(seuil, 0) + " jours, pas à "
             + num(SEUIL_ANNONCE, 0) + " : à deux semaines il vaut encore "
             + num(cout_du_delta_du_soir(SEUIL_ANNONCE) / FRICTION, 1)
             + " fois ce que l'opérateur paie déjà sans y penser. *C'est la "
             "troisième fois de la série qu'un guide se sous-estime* — la "
             "partie XX avait trouvé vingt-deux points de delta quand son "
             "document annonçait « plus de quinze », la partie XXIV "
             "quarante et un deltas quand le sien annonçait trente. La "
             "dernière colonne dit pourquoi la règle vaut la peine d'être "
             "élargie : à la monnaie, le même coût est dix fois plus petit, "
             "donc c'est bien sur les ailes qu'il faut réévaluer, et les "
             "ailes sont ce qu'un pupitre regarde en dernier.",
    )


# ---------------------------------------------------------------------------
# VI. Le strangle ne saigne pas symétriquement
# ---------------------------------------------------------------------------


def strike_du_delta(cible: float, t: float, vol: float = VOL_REF,
                    put: bool = False) -> float:
    """Le strike d'un call ou d'un put de delta donné, par bissection."""
    lo, hi = 1.0, 20.0 * S_REF
    ecart = math.exp(-DIVIDENDE * t) if put else 0.0
    for _ in range(200):
        k = 0.5 * (lo + hi)
        d = G.delta_comptant(S_REF, k, vol, t, TAUX, DIVIDENDE) - ecart
        if d > cible:
            lo = k
        else:
            hi = k
    return 0.5 * (lo + hi)


def strangle(delta: float, jours: float, vol: float = VOL_REF,
             r: float = TAUX, div: float = DIVIDENDE
             ) -> tuple[float, float, float, float]:
    """(charm du call, charm du put, net, brut) d'un strangle symétrique."""
    t = jours / JOURS_AN
    lo, hi = 1.0, 20.0 * S_REF
    for _ in range(200):
        k = 0.5 * (lo + hi)
        if G.delta_comptant(S_REF, k, vol, t, r, div) > delta:
            lo = k
        else:
            hi = k
    kc = 0.5 * (lo + hi)
    lo, hi = 1.0, 20.0 * S_REF
    for _ in range(200):
        k = 0.5 * (lo + hi)
        if (G.delta_comptant(S_REF, k, vol, t, r, div)
                - math.exp(-div * t)) > -delta:
            lo = k
        else:
            hi = k
    kp = 0.5 * (lo + hi)
    a = G.charm(S_REF, kc, vol, t, r, div) / JOURS_AN
    b = G.charm(S_REF, kp, vol, t, r, div) / JOURS_AN
    return (a, b, a + b, abs(a) + abs(b))


def strangle_ferme(delta: float, jours: float, vol: float = VOL_REF) -> float:
    """`−φ(z)·σ/√T` — le charm net d'un strangle, **à portage nul**.

    Les deux jambes ont des `d₁` opposés par construction, et le charm y vaut
    `φ(d₁)(d₁ − σ√T)/2T`. Leur somme laisse `−φ(z)·σ√T/T`, où `z = N⁻¹(1−δ)` :
    elle **n'est nulle à aucun delta et à aucune échéance**. Un strangle ne
    saigne donc pas symétriquement — il raccourcit le livre.
    """
    t = jours / JOURS_AN
    lo, hi = -8.0, 8.0
    for _ in range(200):
        m = 0.5 * (lo + hi)
        if norm_cdf(m) < 1.0 - delta:
            lo = m
        else:
            hi = m
    z = 0.5 * (lo + hi)
    return -_phi(z) * vol / math.sqrt(t) / JOURS_AN


def vertical(haut: float, bas: float, jours: float,
             vol: float = VOL_REF) -> tuple[float, float]:
    """(net, brut) du charm d'un écart vertical de calls."""
    t = jours / JOURS_AN
    k1 = strike_du_delta(haut, t, vol)
    k2 = strike_du_delta(bas, t, vol)
    a = G.charm(S_REF, k1, vol, t, TAUX, DIVIDENDE) / JOURS_AN
    b = G.charm(S_REF, k2, vol, t, TAUX, DIVIDENDE) / JOURS_AN
    return (a - b, abs(a) + abs(b))


#: Deltas balayés pour le strangle.
DELTAS: tuple[float, ...] = (0.10, 0.25, 0.40)

#: Échéances balayées pour le strangle, en jours.
JOURS_STR: tuple[float, ...] = (7.0, 14.0, 30.0, 90.0)


def table_strangle() -> Table:
    rows = []
    for j in JOURS_STR:
        for d in DELTAS:
            a, b, net, brut = strangle(d, j)
            n0 = strangle(d, j, VOL_REF, 0.0, 0.0)[2]
            rows.append([
                num(j, 0),
                num(100 * d, 0),
                num(a, 5, signed=True),
                num(b, 5, signed=True),
                num(net, 5, signed=True),
                num(100 * abs(net) / brut, 1),
                num(n0, 5, signed=True),
                num(strangle_ferme(d, j), 5, signed=True),
            ])
    return Table(
        key="ch_strangle",
        caption="Un strangle ne saigne pas symétriquement, et la forme fermée le dit",
        headers=["Jours", "Delta de chaque jambe (%)", "Charm du call",
                 "Charm du put", "Net", "Part non compensée (%)",
                 "Net mesuré à portage nul", "Forme fermée à portage nul"],
        rows=rows,
        note="« Il s'inverse de part et d'autre du strike : un strangle "
             "saigne son delta symétriquement vers l'extérieur, un écart "
             "vertical non. » La première moitié est fausse et se démontre "
             "en une ligne. Les deux jambes d'un strangle symétrique en delta "
             "ont des `d₁` **opposés** par construction, et le charm vaut "
             "`φ(d₁)(d₁ − σ√T)/2T` à portage nul : leur somme laisse "
             "`−φ(z)·σ/√T`, où `z` est le quantile du delta. *Elle n'est "
             "nulle à aucun delta et à aucune échéance*, et les deux "
             "dernières colonnes la comparent à la mesure faite dans les "
             "mêmes conditions — l'accord est à huit décimales.\n\nLe fait qui en sort n'est pas décoratif. Les deux "
             "jambes perdent bien leur delta, mais **le livre devient plus "
             "court en le faisant**, parce que le call en perd davantage que "
             "le put n'en regagne. La part non compensée passe de "
             + num(100 * abs(strangle(0.10, 7.0)[2]) / strangle(0.10, 7.0)[3],
                   0) + " % sur un strangle lointain à sept jours à "
             + num(100 * abs(strangle(0.40, 90.0)[2])
                   / strangle(0.40, 90.0)[3], 0) + " % sur un strangle "
             "proche à trois mois — c'est-à-dire qu'à cet endroit-là il n'y a "
             "**aucune** compensation. Le portage double l'effet sans le "
             "créer : à taux et dividende nuls la forme fermée le donne déjà "
             "entier.",
    )


def table_vertical() -> Table:
    rows = []
    for j in JOURS_STR:
        net_s, brut_s = strangle(0.25, j)[2], strangle(0.25, j)[3]
        net_v, brut_v = vertical(0.40, 0.20, j)
        rows.append([
            num(j, 0),
            num(net_s, 5, signed=True),
            num(100 * abs(net_s) / brut_s, 1),
            num(net_v, 5, signed=True),
            num(100 * abs(net_v) / brut_v, 1),
            num(abs(net_v / net_s), 2),
        ])
    return Table(
        key="ch_vertical",
        caption="Ce qui reste vrai de la note : l'écart vertical ne compense rien du tout",
        headers=["Jours", "Net d'un strangle à vingt-cinq deltas",
                 "Part non compensée (%)",
                 "Net d'un vertical quarante contre vingt",
                 "Part non compensée (%)", "Rapport des deux"],
        rows=rows,
        note="La seconde moitié de la note du guide tient, et la table dit de "
             "combien. Un écart vertical porte deux jambes **du même côté** "
             "de la monnaie, donc deux charms de même signe qui se "
             "retranchent au lieu de s'ajouter : la part non compensée y est "
             "grande, comme annoncé. Ce que le guide n'écrit pas est que le "
             "strangle ne fait guère mieux. *La différence entre les deux "
             "structures n'est pas celle qu'il décrit — compensation contre "
             "absence de compensation — mais un rapport de deux ou trois*, et "
             "ce rapport se resserre avec l'échéance. La bonne formulation "
             "est celle-ci : aucune structure symétrique en delta n'est "
             "neutre en charm, et il faut le calculer pour chacune plutôt "
             "que de le déduire de sa forme.",
    )


# ---------------------------------------------------------------------------
# VII. Le décompte, sur sept parties
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Affirmation:
    enonce: str
    grandeur: str
    mesure: str


def affirmations() -> tuple[Affirmation, ...]:
    t1 = 1.0 / JOURS_AN
    return (
        Affirmation(
            "Le `T^{3/2}` du dénominateur fait accélérer le charm dans les "
            "dernières séances",
            "l'horloge",
            "l'accélération est réelle et la puissance est fausse : "
            "l'exposant mesuré vaut " + num(exposant_du_pic(1.0), 2)),
        Affirmation(
            "Le charm est le plus grand vers vingt-cinq et soixante-quinze "
            "deltas",
            "le risque",
            "le pic est à " + num(100 * delta_du_pic(t1), 0) + " et "
            + num(100 * (1.0 - delta_du_pic(t1)), 0) + " deltas, en forme "
            "fermée"),
        Affirmation(
            "La ligne à la monnaie reste près de zéro",
            "rien",
            "elle diverge aussi, en racine inverse du temps ; le rapport "
            "s'effondre de 51 à 10 entre un jour et trente"),
        Affirmation(
            "Le charm court sur le calendrier, le gamma sur le temps de "
            "bourse",
            "l'horloge",
            "le guide du thêta de la même série a publié la mesure qui "
            "contredit : facteur "
            + num(facteur_du_calendrier(0.97, 10.0), 1) + " sur les ailes"),
        Affirmation(
            "Calculez le delta de demain sous deux semaines d'échéance",
            "le risque",
            "la règle est juste et le seuil trop court : le coût passe sous "
            "la friction à " + num(echeance_du_seuil(), 0) + " jours"),
        Affirmation(
            "Un strangle saigne son delta symétriquement vers l'extérieur",
            "le risque",
            "le net vaut `−φ(z)σ/√T`, nul à aucun delta ni à aucune "
            "échéance"),
        Affirmation(
            "Un long week-end compose l'effet : trois ou quatre jours de "
            "saignée contre un de gamma",
            "l'horloge",
            "vrai de la saignée mesurée sur l'horloge calibrée, à un facteur "
            "trois près de ce que le guide annonce"),
        Affirmation(
            "Le charm ne demande pas de savoir qui est long ou court",
            "rien",
            "**exact**, et c'est la seule affirmation d'agrégation des sept "
            "parties qui tienne"),
    )


def compte_par_grandeur() -> dict[str, int]:
    out: dict[str, int] = {}
    for a in affirmations():
        out[a.grandeur] = out.get(a.grandeur, 0) + 1
    return out


def familles() -> tuple[tuple[str, int], ...]:
    """Les sept parties d'options, comptées dans leurs propres modules."""
    return va.familles() + (("Charm, partie XXV", len(affirmations())),)


def table_reste() -> Table:
    rows = [[a.enonce, a.grandeur, a.mesure] for a in affirmations()]
    c = compte_par_grandeur()
    return Table(
        key="ch_reste",
        caption="Huit affirmations, et le décompte des sept parties d'options",
        headers=["L'affirmation", "Ce qu'elle déplace",
                 "Ce que la mesure en dit"],
        rows=rows,
        note="Le décompte se lit dans l'identité `E[R] = (µ·E[τ∧T] − c)/a` : "
             + num(c.get("le risque", 0), 0) + " affirmations déplacent le "
             "**risque**, " + num(c.get("l'horloge", 0), 0) + " l'horloge, "
             + num(c.get("rien", 0), 0) + " ne déplacent rien, et **aucune "
             "ne touche à la direction**. C'est la troisième partie "
             "d'options consécutive dont cette colonne est vide. Sur les "
             + num(sum(n for _, n in familles()), 0) + " affirmations des "
             "sept parties, *aucune ne donne un sens*.\n\nLa dernière ligne "
             "est la seule de toute la série qui survive intacte à une "
             "question d'agrégation, et il faut le dire sans réserve. Le "
             "gamma agrégé de la partie XIX demandait le signe d'un "
             "inventaire qu'on n'observe pas ; le vanna agrégé de la partie "
             "XXIV en demandait deux, et rendait trois lignes là où il en "
             "fallait une. Le charm, lui, est employé sur **son propre "
             "livre** : il dit comment une exposition qu'on connaît bougera "
             "si l'on ne fait rien, et cette question-là ne comporte aucun "
             "paramètre caché. *Un outil de planification, et non une "
             "prévision* — le guide le formule ainsi, et c'est exact. Il "
             "ajoute que le même objet employé comme niveau de marché hérite "
             "de tous les défauts du document sur le gamma, ce que les "
             "parties XIX et XXIV ont chiffré. **Sur les sept documents, "
             "c'est la seule affirmation d'agrégation que ce dépôt "
             "reprend.**",
        wrap_cols=[0, 2],
    )


# ---------------------------------------------------------------------------
# Les quatre reliefs
# ---------------------------------------------------------------------------
#
# Les axes sont écrits de façon que le **maximum tombe au coin du fond** : en
# projection isométrique le coin (0, 0) est le plus éloigné, et un relief qui
# monte vers l'horizon se lit.

SURF_ECHEANCE: tuple[float, ...] = (1.0, 3.0, 7.0, 14.0, 30.0, 60.0)
SURF_MONEYNESS: tuple[float, ...] = (0.99, 0.97, 0.95, 0.93, 0.90, 0.86)

SURF_POIDS: tuple[float, ...] = (0.02, 0.08, 0.18, 0.35, 0.60, 1.00)
SURF_ECHEANCE_WE: tuple[float, ...] = (5.0, 7.0, 10.0, 14.0, 21.0, 30.0)

SURF_ECHEANCE_COUT: tuple[float, ...] = (1.0, 3.0, 7.0, 14.0, 30.0, 90.0)
SURF_MONEYNESS_COUT: tuple[float, ...] = (0.99, 0.97, 0.95, 0.92, 0.88, 0.82)

SURF_DELTA: tuple[float, ...] = (0.45, 0.40, 0.32, 0.24, 0.16, 0.08)
SURF_ECHEANCE_STR: tuple[float, ...] = (180.0, 90.0, 45.0, 21.0, 10.0, 5.0)


@lru_cache(maxsize=2)
def surface_saignee() -> tuple[tuple[float, ...], ...]:
    """`|charm|` par jour, en échéance et en moneyness."""
    return tuple(tuple(abs(bleed(S_REF * m, S_REF, j / JOURS_AN))
                       for m in SURF_MONEYNESS)
                 for j in SURF_ECHEANCE)


@lru_cache(maxsize=2)
def surface_horloge() -> tuple[tuple[float, ...], ...]:
    """Le facteur de surestimation du calendrier, en poids et en échéance."""
    return tuple(tuple(min(30.0, facteur_du_calendrier(0.97, j, w))
                       for j in SURF_ECHEANCE_WE)
                 for w in SURF_POIDS)


@lru_cache(maxsize=2)
def surface_cout() -> tuple[tuple[float, ...], ...]:
    """Le coût du delta du soir en unités de friction, échéance et moneyness."""
    return tuple(tuple(cout_du_delta_du_soir(j, m) / FRICTION
                       for m in SURF_MONEYNESS_COUT)
                 for j in SURF_ECHEANCE_COUT)


@lru_cache(maxsize=2)
def surface_strangle() -> tuple[tuple[float, ...], ...]:
    """La part non compensée d'un strangle, en delta et en échéance."""
    out = []
    for d in SURF_DELTA:
        ligne = []
        for j in SURF_ECHEANCE_STR:
            _, _, net, brut = strangle(d, j)
            ligne.append(100.0 * abs(net) / brut)
        out.append(tuple(ligne))
    return tuple(out)


# ---------------------------------------------------------------------------
# Valeurs, tables, et exécution directe
# ---------------------------------------------------------------------------


def values() -> dict[str, str]:
    t1 = 1.0 / JOURS_AN
    t30 = 30.0 / JOURS_AN
    m1 = G.moneyness_du_pic(VOL_REF, t1)
    return {
        "ch_exposant_1": num(exposant_du_pic(1.0), 3),
        "ch_exposant_30": num(exposant_du_pic(30.0), 3),
        "ch_exposant_annonce": num(-PUISSANCE_ANNONCEE, 1),
        "ch_asymptote_1": num(G.amplitude_asymptotique(t1), 4),
        "ch_pic_1": num(G.bleed_du_pic(VOL_REF, t1), 4),
        "ch_pic_delta_1": num(100 * delta_du_pic(t1), 0),
        "ch_pic_delta_60": num(100 * delta_du_pic(60.0 / JOURS_AN), 0),
        "ch_pic_delta_haut": num(100 * (1.0 - delta_du_pic(t1)), 0),
        "ch_delta_annonce": num(100 * DELTA_ANNONCE, 0),
        "ch_pic_ecart_1": num(100 * (1.0 - m1), 1),
        "ch_delta_illustration": num(
            G.delta_comptant(S_REF * (1.0 - ECART_ILLUSTRATION), S_REF,
                             VOL_REF, t1, TAUX, DIVIDENDE), 4),
        "ch_delta_du_pic_soir": num(
            G.delta_comptant(S_REF * m1, S_REF, VOL_REF, t1, TAUX,
                             DIVIDENDE), 3),
        "ch_atm_1": num(abs(bleed(S_REF, S_REF, t1)), 5),
        "ch_atm_exposant": num(exposant_a_la_monnaie(1.0), 2),
        "ch_rapport_1": num(G.bleed_du_pic(VOL_REF, t1)
                            / abs(bleed(S_REF, S_REF, t1)), 0),
        "ch_rapport_30": num(G.bleed_du_pic(VOL_REF, t30)
                             / abs(bleed(S_REF, S_REF, t30)), 0),
        "ch_omega": num(POIDS_CALIBRE, 4),
        "ch_jours_apparents": num(th.jours_apparents(POIDS_CALIBRE), 2),
        "ch_we_calendaire": num(saignee_calendaire(0.97, 10.0), 4,
                                signed=True),
        "ch_we_horloge": num(saignee_horloge(0.97, 10.0, POIDS_CALIBRE), 4,
                             signed=True),
        "ch_we_facteur": num(facteur_du_calendrier(0.97, 10.0), 1),
        "ch_we_facteur_haut": num(facteur_du_calendrier(1.03, 30.0), 1),
        "ch_we_facteur_atm": num(facteur_du_calendrier(1.0, 10.0), 2),
        "ch_we_hausse": num(100 * th.derive_implicite(10.0, POIDS_CALIBRE), 1),
        "ch_seuil": num(echeance_du_seuil(), 0),
        "ch_seuil_annonce": num(SEUIL_ANNONCE, 0),
        "ch_cout_14": num(cout_du_delta_du_soir(SEUIL_ANNONCE) / FRICTION, 1),
        "ch_cout_1": num(cout_du_delta_du_soir(1.0) / FRICTION, 0),
        "ch_friction": num(FRICTION, 2),
        "ch_str_net": num(abs(strangle(0.25, 14.0)[2]), 5),
        "ch_str_part_basse": num(
            100 * abs(strangle(0.10, 7.0)[2]) / strangle(0.10, 7.0)[3], 0),
        "ch_str_part_haute": num(
            100 * abs(strangle(0.40, 90.0)[2]) / strangle(0.40, 90.0)[3], 0),
        "ch_affirmations": num(len(affirmations()), 0),
        "ch_total_options": num(sum(n for _, n in familles()), 0),
        "ch_vol": num(100 * VOL_REF, 0),
    }


def all_tables() -> dict[str, Table]:
    tables = [table_acceleration(), table_pic(), table_monnaie(),
              table_weekend(), table_horloges(), table_cout(),
              table_strangle(), table_vertical(), table_reste()]
    return {t.key: t for t in tables}


def main() -> None:
    for t in all_tables().values():
        print(t.to_text())
        print()
    for k, v in values().items():
        print(f"{k:26s} {v}")


if __name__ == "__main__":
    main()
