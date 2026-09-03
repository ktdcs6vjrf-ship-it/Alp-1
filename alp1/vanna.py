"""Là où le delta et la volatilité se rencontrent.

Sixième document de la série d'options, consacré au vanna. Il est le seul des
six à publier **son propre résultat négatif** avec le contrôle qui le rend
lisible — un niveau témoin placé à la même distance de l'ouverture — et c'est
exactement le contrôle que la partie XIX avait dû ajouter au guide du gamma.
Sur ce point le dépôt n'a rien à corriger ; il a de quoi chiffrer.

Sur le reste, sept affirmations sont reprises. Deux tiennent, une se
**renforce**, quatre se corrigent, et la correction la plus lourde porte sur
une formule qui nomme le mauvais grec.

Avant tout cela, la vérification a trouvé un défaut **dans ce dépôt**, et il
est du genre que la règle du dépôt existe pour attraper : `vega.vanna`
écrivait `−V·d₂/(Sσ)`, où le dénominateur oublie `√T`. Elle rendait donc le
vanna multiplié par la racine de l'échéance — un facteur trois et demi à
trente jours. Rien ne l'avait vu parce que **rien ne la consommait** : aucune
table, aucune figure, aucun test. Une forme fermée se contrôle contre une
route indépendante, y compris quand personne ne s'en sert encore.

I. Deux lectures, un nombre
-----------------------------
`vanna = ∂Δ/∂σ = ∂V/∂S = −e^{−qT}φ(d₁)·d₂/σ`. Les deux dérivées croisées sont
le même nombre par la symétrie des dérivées secondes, et cette égalité est le
contrôle du module. Le vanna s'annule où `d₂ = 0`, donc au comptant
`S/K = e^{−(r−q−σ²/2)T}` — **au-dessus de la monnaie si et seulement si
`r < q + σ²/2`**, la borne exacte que la partie XXIII a trouvée sur le maximum
du rho. Les deux parties tombent sur le même taux, `4,42 %`, par deux routes
qui n'ont rien en commun.

II. « Le vanna ramène le delta vers un demi », et les deux endroits où non
---------------------------------------------------------------------------
La règle vaut si et seulement si `d₁` et `d₂` ont le même signe. Elle échoue
sur `d₂ < 0 < d₁`, c'est-à-dire **exactement là où la volga est négative** —
la bande de courbure de la partie XXII, retrouvée par un chemin entièrement
différent, à la même largeur `σ²T` : `0,52 %` du comptant à trente jours.

Et elle échoue une seconde fois, pour une autre raison : à volatilité qui
croît, le delta d'un call tend vers `e^{−qT}`, pas vers un demi. Le
retournement se calcule — `σ* = √(2·ln(F/K)/T)` — et le plancher aussi :
`e^{−qT}·N(√(2 ln(F/K)))`. Sur un call à cinq pour cent dans la monnaie et un
an d'échéance, le delta descend à `0,643` puis remonte, et il le fait à
`38,9 %` de volatilité — **dans le domaine plausible**.

III. Le déplacement annoncé
------------------------------
« Monter la volatilité de 15 % à 45 % porte un call de vingt deltas à trente
environ. » La mesure rend **quarante et un**. Le premier ordre — le vanna lui
même, multiplié par le choc — en rend soixante-neuf. Le nombre du guide n'est
donc ni la mesure ni sa propre approximation : trente deltas s'atteignent à
`23,2 %`, soit huit points de volatilité et non trente.

IV. Où le vanna est le plus grand, et pourquoi la réponse dépend de la fenêtre
--------------------------------------------------------------------------------
Le lieu du pic est en forme fermée, `d₁* = (σ√T − √(σ²T + 4))/2`, et c'est
**la même racine que le pic du charm** de la partie XX : les deux grandeurs
valent `φ(d₁)` fois une fonction affine de `d₁`, donc elles culminent au même
endroit. Le dépôt importe la fonction plutôt que de la recopier.

Le pic se tient à un **delta presque constant** — seize pour cent à un jour,
vingt et un à cinq ans — et il migre donc vers l'extérieur en moneyness comme
la racine du temps. Le module d'amplitude, lui, **croît de bout en bout** avec
l'échéance. « Le vanna est le plus grand aux échéances intermédiaires » n'est
donc pas une propriété du vanna : c'est une propriété de la fenêtre de
moneyness que la planche du guide a fixée à `0,80–1,20`, et d'où l'arête sort
par le côté. C'est le piège que ce dépôt a trouvé six fois dans ses propres
figures, et il le trouve ici dans une figure qui n'est pas la sienne.

V. La section 2 nomme le mauvais grec
----------------------------------------
Le guide écrit `Δ_effectif ≈ Δ + vanna·∂σ/∂S`. Le membre de droite n'est pas
un delta : `vanna` est en inverse de volatilité, `∂σ/∂S` en volatilité par
point, leur produit en inverse de point. La correction juste porte le **véga**
— `Δ + 𝒱·∂σ/∂S` — et elle reproduit une réévaluation complète le long de la
peau à la cinquième décimale, quand la formule du guide en capte **six
centièmes de pour cent**.

La formule du guide est celle du **gamma** effectif portant le nom du delta,
et même là il lui manque un facteur deux et le terme de volga :
`Γ + 2·vanna·σ′ + volga·σ′²` reproduit le gamma réévalué à la sixième
décimale. Le graphique posé sous la formule, lui, est juste : l'écart entre
ses deux courbes de delta est le terme de véga.

VI. Ce que le test rend, et pourquoi le dépôt le croit
---------------------------------------------------------
Le guide publie un résultat négatif contrôlé par un niveau témoin placé à la
même distance de l'ouverture. C'est le contrôle de la partie XIX, et le dépôt
n'a qu'à le rejouer : le taux de touche est celui du principe de réflexion et
ne dit que la distance, le taux de réussite d'un trade pris sur le niveau vaut
`1/(1+R:R)` à toute distance. Un niveau agrégé ne peut donc battre son témoin
qu'en déplaçant `µ`, et l'excès requis comme l'échantillon sortent de
l'identité de la partie XIX.

Reste le mécanisme que le guide nomme : l'agrégation. Le GEX de la partie XIX
avait **un** inobservable, le signe de l'inventaire. Le vanna en a **deux**,
le signe et la volatilité vraie de chaque strike. La bande s'élargit d'autant,
et la part des configurations sans aucune ligne de bascule avec elle.

VII. Le décompte, sur six parties
------------------------------------
Sur les quarante-deux affirmations des six parties d'options, aucune ne donne
un sens.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from . import entropy
from . import grandeurs as G
from . import niveaux as nv
from . import quant as q
from . import rho as R
from . import seuil
from . import theta as th
from . import vega as vg
from .costs import COST_BASE, ES, norm_cdf
from .quant import Rng
from .report import Table, num

SEED = 20260916

S_REF = vg.S_REF
VOL_REF = vg.VOL_REF
TAUX = vg.TAUX
DIVIDENDE = vg.DIVIDENDE
JOURS_AN = nv.JOURS_AN

FRICTION = COST_BASE.friction_points(ES)


def _phi(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


# ---------------------------------------------------------------------------
# I. Deux lectures, un nombre
# ---------------------------------------------------------------------------


def vanna(s: float, k: float, vol: float, t: float, r: float = TAUX,
          div: float = DIVIDENDE) -> float:
    """`−e^{−qT}φ(d₁)·d₂/σ`, la forme fermée. Elle vit dans `vega`."""
    return vg.vanna(s, k, vol, t, r, div)


def vanna_par_delta(s: float, k: float, vol: float, t: float, r: float = TAUX,
                    div: float = DIVIDENDE, h: float = 1e-5) -> float:
    """La première route : `∂Δ/∂σ`, par différence finie sur la volatilité."""
    return (G.delta_comptant(s, k, vol + h, t, r, div)
            - G.delta_comptant(s, k, vol - h, t, r, div)) / (2.0 * h)


def vanna_par_vega(s: float, k: float, vol: float, t: float, r: float = TAUX,
                   div: float = DIVIDENDE, h: float = 0.01) -> float:
    """La seconde route : `∂V/∂S`, par différence finie sur le comptant.

    L'égalité des deux est la symétrie des dérivées secondes croisées, donc
    elle n'a pas à être vérifiée en théorie — et c'est précisément pour cela
    qu'elle fait un bon contrôle : elle ne peut échouer que si l'une des deux
    implémentations est fausse.
    """
    return (vg.vega(s + h, k, vol, t, r, div)
            - vg.vega(s - h, k, vol, t, r, div)) / (2.0 * h)


def moneyness_du_zero(t: float, vol: float = VOL_REF, r: float = TAUX,
                      div: float = DIVIDENDE) -> float:
    """`S/K = e^{−(r−q−σ²/2)T}` — le comptant où le vanna s'annule."""
    return math.exp(-(r - div - 0.5 * vol * vol) * t)


def zero_au_dessus(vol: float = VOL_REF, r: float = TAUX,
                   div: float = DIVIDENDE) -> bool:
    """Le zéro est-il au-dessus de la monnaie ?

    Il l'est si et seulement si `r < q + σ²/2`, c'est-à-dire au-dessous du
    taux que la partie XXIII a trouvé sur un objet entièrement différent — le
    seul taux où le maximum du rho tombe sur l'inverse du taux. Le module
    importe ce taux plutôt que de le récrire.
    """
    return r < R.taux_du_pic_exact(vol, div)


#: Échéances balayées, en jours.
ECHEANCES: tuple[float, ...] = (7.0, 30.0, 90.0, 180.0, 365.0, 730.0)

#: Moneyness balayées.
MONEYNESS: tuple[float, ...] = (0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15)


def table_deux_routes() -> Table:
    rows = []
    for j in ECHEANCES:
        t = j / JOURS_AN
        for m in (0.90, 1.00, 1.10):
            s = S_REF * m
            rows.append([
                num(j, 0),
                num(m, 2),
                num(vanna(s, S_REF, VOL_REF, t), 5, signed=True),
                num(vanna_par_delta(s, S_REF, VOL_REF, t), 5, signed=True),
                num(vanna_par_vega(s, S_REF, VOL_REF, t), 5, signed=True),
                num(vg.vanna(s, S_REF, VOL_REF, t) * math.sqrt(t), 5,
                    signed=True),
            ])
    return Table(
        key="va_deux_routes",
        caption="Le vanna par ses deux dérivées croisées, et ce que le dépôt publiait",
        headers=["Jours", "S/K", "Forme fermée", "Par `∂Δ/∂σ`", "Par `∂V/∂S`",
                 "Ce que le module rendait avant"],
        rows=rows,
        note="Les deux routes du milieu sont les deux façons de lire le même "
             "nombre — la sensibilité du delta à la volatilité, et celle du "
             "véga au comptant — et leur égalité est la symétrie des dérivées "
             "secondes croisées. Elle n'a donc pas à être vérifiée en "
             "théorie, ce qui en fait un bon contrôle : elle ne peut échouer "
             "que si une implémentation est fausse. **Elle l'a été.** La "
             "dernière colonne est ce que `vega.vanna` rendait avant cette "
             "partie : la forme fermée y portait `−V·d₂/(Sσ)`, dont le "
             "dénominateur oublie `√T`, donc elle rendait le vanna multiplié "
             "par la racine de l'échéance — un facteur "
             + num(1.0 / math.sqrt(30.0 / JOURS_AN), 1) + " à trente jours. "
             "*Rien ne l'avait vu parce que rien ne la consommait* : aucune "
             "table, aucune figure, aucun test. C'est le cas exact que la "
             "règle du dépôt vise, et elle avait été appliquée au véga et à "
             "la volga mais pas à leur dérivée croisée. Une forme fermée se "
             "contrôle contre une route indépendante, y compris quand "
             "personne ne s'en sert encore.",
    )


def table_zero() -> Table:
    rows = []
    for j in ECHEANCES:
        t = j / JOURS_AN
        m = moneyness_du_zero(t)
        rows.append([
            num(j, 0),
            num(m, 5),
            num(10000.0 * (m - 1.0), 1),
            num(vanna(S_REF * (m - 0.01), S_REF, VOL_REF, t), 4, signed=True),
            num(vanna(S_REF * (m + 0.01), S_REF, VOL_REF, t), 4, signed=True),
        ])
    return Table(
        key="va_zero",
        caption="Le lieu où le vanna change de signe, et le taux qui le décide",
        headers=["Jours", "S/K du zéro", "Écart à la monnaie (points de base)",
                 "Vanna un pour cent au-dessous",
                 "Vanna un pour cent au-dessus"],
        rows=rows,
        note="Le guide écrit que le vanna s'annule « légèrement au-dessus de "
             "la monnaie », qu'il est positif au-dessous et négatif "
             "au-dessus. C'est exact, et la condition se calcule : le zéro "
             "est au-dessus de la monnaie **si et seulement si** "
             "`r < q + σ²/2`. Ce taux vaut "
             + num(100 * R.taux_du_pic_exact(), 2) + " %, et c'est le même "
             "nombre que la partie XXIII a trouvé sur un objet entièrement "
             "différent — le seul taux auquel le maximum du rho tombe sur "
             "l'inverse du taux. *Deux routes qui n'ont rien en commun "
             "butent sur la même égalité entre le taux, le rendement et la "
             "moitié de la variance*, et c'est la même chose qu'elles "
             "disent : à ce taux-là, une option à la monnaie a la même "
             "chance d'être exercée à toute échéance. Au-dessus, le zéro "
             "passe **sous** la monnaie et la phrase du guide s'inverse ; la "
             "décennie de taux nuls la rendait vraie sans condition.",
    )


# ---------------------------------------------------------------------------
# II. « Le vanna ramène le delta vers un demi », et les deux endroits où non
# ---------------------------------------------------------------------------


def bande_de_desobeissance(t: float, vol: float = VOL_REF, r: float = TAUX,
                           div: float = DIVIDENDE) -> tuple[float, float]:
    """La bande `d₂ < 0 < d₁`, en `S/K`, où la règle du guide s'inverse.

    La règle « le vanna ramène le delta vers un demi » vaut si et seulement si
    `d₁` et `d₂` ont le même signe. Comme `d₂ < d₁` toujours, elle échoue
    exactement sur `d₂ < 0 < d₁` — c'est-à-dire sur `d₁d₂ < 0`, qui est la
    condition de **volga négative** de la partie XXII. Les deux guides
    décrivent le même intervalle sans le savoir, et sa largeur en logarithme
    vaut `σ²T` dans les deux cas.
    """
    return (math.exp(-(r - div + 0.5 * vol * vol) * t),
            math.exp(-(r - div - 0.5 * vol * vol) * t))


def largeur_de_desobeissance(t: float, vol: float = VOL_REF) -> float:
    """La largeur relative de cette bande — `e^{σ²T} − 1`."""
    lo, hi = bande_de_desobeissance(t, vol)
    return hi / lo - 1.0


def vol_du_retournement(moneyness: float, t: float, r: float = TAUX,
                        div: float = DIVIDENDE) -> float:
    """`σ* = √(2·ln(F/K)/T)` — la volatilité où le delta cesse de baisser.

    Second endroit où la règle du guide tombe, et pour une autre raison. Le
    delta vaut `e^{−qT}N(d₁)` avec `d₁ = m/(σ√T) + σ√T/2` et
    `m = ln(F/K)`. Sur une option dans la monnaie, `m > 0` et `d₁` passe par
    un **minimum** : le delta descend, s'arrête, puis remonte vers un. Il ne
    tend donc pas vers un demi, il tend vers `e^{−qT}`.
    """
    m = math.log(moneyness) + (r - div) * t
    if m <= 0.0:
        return math.inf
    return math.sqrt(2.0 * m / t)


def plancher_du_delta(moneyness: float, t: float, r: float = TAUX,
                      div: float = DIVIDENDE) -> float:
    """`e^{−qT}·N(√(2·ln(F/K)))` — le delta le plus bas qu'une volatilité atteint.

    Forme fermée : au minimum, `d₁ = √(2m)`. Elle se contrôle contre un
    balayage sur la volatilité, comme toutes les formes fermées de ce dépôt.
    """
    m = math.log(moneyness) + (r - div) * t
    if m <= 0.0:
        return 0.0
    return math.exp(-div * t) * norm_cdf(math.sqrt(2.0 * m))


def plancher_balaye(moneyness: float, t: float, n: int = 4000,
                    r: float = TAUX, div: float = DIVIDENDE) -> float:
    """Le contrôle : le minimum du delta sur un balayage de volatilité."""
    return min(G.delta_comptant(S_REF * moneyness, S_REF, 0.01 + 3.0 * i / n,
                                t, r, div) for i in range(n + 1))


#: Moneyness dans la monnaie balayées pour le retournement.
MONEYNESS_ITM: tuple[float, ...] = (1.02, 1.05, 1.10, 1.20, 1.35)


def table_desobeissance() -> Table:
    rows = []
    for j in ECHEANCES:
        t = j / JOURS_AN
        lo, hi = bande_de_desobeissance(t)
        rows.append([
            num(j, 0),
            num(lo, 5),
            num(hi, 5),
            num(100 * largeur_de_desobeissance(t), 3),
            num(math.log(hi / lo), 6),
            num(VOL_REF * VOL_REF * t, 6),
        ])
    return Table(
        key="va_desobeissance",
        caption="La bande où la règle s'inverse, et celle où la volga est négative",
        headers=["Jours", "Borne basse (S/K)", "Borne haute (S/K)",
                 "Largeur (%)", "Largeur en logarithme", "`σ²T`"],
        rows=rows,
        note="« Le vanna ramène toujours le delta vers un demi » vaut si et "
             "seulement si `d₁` et `d₂` ont le même signe. Comme `d₂` est "
             "toujours plus petit que `d₁`, la règle échoue exactement sur "
             "`d₂ < 0 < d₁`, où le delta dépasse un demi et où le vanna le "
             "pousse encore plus haut. Cette condition est `d₁d₂ < 0`, "
             "c'est-à-dire **la volga négative de la partie XXII** : les deux "
             "guides décrivent le même intervalle sans le savoir, et les "
             "deux dernières colonnes le vérifient — la largeur en "
             "logarithme vaut `σ²T` à toutes les échéances, exactement comme "
             "celle de la partie XXII. Les deux bandes ne sont pas "
             "seulement de même largeur : *c'est le même ensemble*, la "
             "partie XXII l'ayant publié dans sa forme à taux nul, centrée "
             "sur la monnaie, quand le taux et le rendement le décalent de "
             "`(r−q)T`. *La partie XXII avait mesuré cette "
             "bande pour dire qu'aucun strike d'une grille au pas d'un pour "
             "cent n'y tombe au-dessous de quinze jours ;* la même mesure dit "
             "ici que l'exception à la règle du guide existe et qu'elle est "
             "invisible sur un tableau d'options. C'est une réfutation qui "
             "confirme : la règle est fausse sur un ensemble que personne ne "
             "peut négocier.",
    )


def table_retournement() -> Table:
    rows = []
    for m in MONEYNESS_ITM:
        for j in (90.0, 365.0):
            t = j / JOURS_AN
            sig = vol_du_retournement(m, t)
            rows.append([
                num(m, 2),
                num(j, 0),
                num(100 * sig, 1),
                num(plancher_du_delta(m, t), 4),
                num(plancher_balaye(m, t), 4),
                num(G.delta_comptant(S_REF * m, S_REF, 0.15, t, TAUX,
                                     DIVIDENDE), 4),
                num(G.delta_comptant(S_REF * m, S_REF, 3.0, t, TAUX,
                                     DIVIDENDE), 4),
            ])
    return Table(
        key="va_retournement",
        caption="Le delta ne tend pas vers un demi, et le lieu où il se retourne",
        headers=["S/K", "Jours", "Volatilité du retournement (%)",
                 "Plancher du delta (forme fermée)",
                 "Plancher balayé (contrôle)", "Delta à 15 %",
                 "Delta à 300 %"],
        rows=rows,
        note="Le guide écrit que le vanna « ramène toujours le delta vers "
             "0,50, la volatilité haute faisant ressembler toute option à un "
             "tirage à pile ou face ». La seconde moitié de la phrase est "
             "l'inverse de ce qui se passe : à volatilité qui croît, `d₁` "
             "part vers l'infini **positif** et le delta d'un call tend vers "
             "`e^{−qT}`, donc vers un. Il descend d'abord, s'arrête, puis "
             "remonte. Le lieu du retournement est en forme fermée — "
             "`σ* = √(2·ln(F/K)/T)` — et le plancher aussi, "
             "`e^{−qT}·N(√(2·ln(F/K)))` ; les deux colonnes du milieu les "
             "comparent, la seconde étant un balayage sur trois cents points "
             "de volatilité. **Aucune option dans la monnaie n'atteint jamais "
             "un demi.** Et le retournement n'est pas une curiosité de "
             "laboratoire : sur un call à cinq pour cent dans la monnaie et "
             "un an d'échéance, il tombe à "
             + num(100 * vol_du_retournement(1.05, 1.0), 1) + " % de "
             "volatilité, à l'intérieur du domaine qu'un indice a visité "
             "plusieurs fois.",
    )


# ---------------------------------------------------------------------------
# III. Le déplacement annoncé
# ---------------------------------------------------------------------------

#: Le couple de volatilités du guide, en fraction.
VOL_BASSE = 0.15
VOL_HAUTE = 0.45

#: Le delta de départ, et le delta d'arrivée annoncé.
DELTA_DEPART = 0.20
DELTA_ANNONCE = 0.30


def strike_du_delta(cible: float, t: float, vol: float = VOL_BASSE,
                    r: float = TAUX, div: float = DIVIDENDE) -> float:
    """Le strike d'un call de delta donné, par bissection."""
    lo, hi = S_REF, 20.0 * S_REF
    for _ in range(200):
        k = 0.5 * (lo + hi)
        if G.delta_comptant(S_REF, k, vol, t, r, div) > cible:
            lo = k
        else:
            hi = k
    return 0.5 * (lo + hi)


def vol_pour_le_delta(k: float, cible: float, t: float, r: float = TAUX,
                      div: float = DIVIDENDE) -> float:
    """La volatilité qui porte un strike donné au delta visé."""
    lo, hi = 0.005, 5.0
    for _ in range(200):
        v = 0.5 * (lo + hi)
        if G.delta_comptant(S_REF, k, v, t, r, div) < cible:
            lo = v
        else:
            hi = v
    return 0.5 * (lo + hi)


def deplacement(t: float, depart: float = DELTA_DEPART,
                basse: float = VOL_BASSE,
                haute: float = VOL_HAUTE) -> tuple[float, float, float, float]:
    """(strike, delta exact à la volatilité haute, premier ordre, vol du 30)."""
    k = strike_du_delta(depart, t, basse)
    exact = G.delta_comptant(S_REF, k, haute, t, TAUX, DIVIDENDE)
    lineaire = depart + vanna(S_REF, k, basse, t) * (haute - basse)
    v30 = vol_pour_le_delta(k, DELTA_ANNONCE, t)
    return (k, exact, lineaire, v30)


def table_deplacement() -> Table:
    rows = []
    for j in ECHEANCES:
        t = j / JOURS_AN
        k, exact, lin, v30 = deplacement(t)
        rows.append([
            num(j, 0),
            num(k, 2),
            num(100 * exact, 1),
            num(100 * DELTA_ANNONCE, 0),
            num(100 * lin, 1),
            num(100 * v30, 1),
            num(100 * (v30 - VOL_BASSE), 1),
        ])
    k30, e30, l30, v30 = deplacement(30.0 / JOURS_AN)
    return Table(
        key="va_deplacement",
        caption="Ce que trente points de volatilité font vraiment à un call de vingt deltas",
        headers=["Jours", "Strike du vingt-deltas", "Delta mesuré à 45 % (%)",
                 "Delta annoncé (%)", "Premier ordre (%)",
                 "Volatilité qui rend trente deltas (%)",
                 "Choc requis (points)"],
        rows=rows,
        note="Le guide illustre le mécanisme par un nombre : monter la "
             "volatilité de " + num(100 * VOL_BASSE, 0) + " % à "
             + num(100 * VOL_HAUTE, 0) + " % porte un call de vingt deltas à "
             "« trente environ ». La mesure rend "
             + num(100 * e30, 0) + " à trente jours, et la colonne suivante "
             "montre que ce n'est pas non plus ce que sa propre formule "
             "prédit : le premier ordre — le vanna multiplié par le choc — en "
             "donne " + num(100 * l30, 0) + ", parce que le vanna décroît "
             "vite quand la volatilité monte et qu'une tangente prise au "
             "point de départ surestime. *Le nombre publié n'est donc ni la "
             "mesure ni son approximation ; il tombe entre les deux.* Les "
             "deux dernières colonnes donnent le chiffre juste : trente "
             "deltas s'atteignent à " + num(100 * v30, 1) + " % de "
             "volatilité, soit " + num(100 * (v30 - VOL_BASSE), 1) + " points "
             "de choc et non trente. L'effet que le guide décrit est **plus "
             "grand** que ce qu'il en dit, et c'est la seconde fois de la "
             "série qu'un guide se sous-estime : la partie XX avait trouvé "
             "l'écart des trois deltas à 22,3 points quand son document "
             "annonçait « plus de 15 ».",
    )


# ---------------------------------------------------------------------------
# IV. Où le vanna est le plus grand, et pourquoi la réponse dépend de la fenêtre
# ---------------------------------------------------------------------------


def moneyness_du_pic(t: float, vol: float = VOL_REF, r: float = TAUX,
                     div: float = DIVIDENDE) -> float:
    """Le `S/K` où `|vanna|` est maximal, déduit de `d₁*`.

    `d₁*` vient de `grandeurs.d1_du_pic`, écrite pour le charm : maximiser
    `φ(d₁)·(d₁ − σ√T)` et maximiser `φ(d₁)·d₂` donnent **la même équation du
    second degré**, `d₁² − σ√T·d₁ − 1 = 0`, parce que les deux grandeurs sont
    `φ(d₁)` multipliée par une fonction affine de `d₁`. Le dépôt importe donc
    la racine plutôt que de la recopier — une seconde copie serait une seconde
    occasion de la faire diverger.
    """
    v = vol * math.sqrt(t)
    return math.exp(G.d1_du_pic(vol, t) * v - (r - div + 0.5 * vol * vol) * t)


def vanna_du_pic(t: float, vol: float = VOL_REF, r: float = TAUX,
                 div: float = DIVIDENDE) -> float:
    """L'amplitude du vanna en son maximum."""
    return vanna(S_REF * moneyness_du_pic(t, vol, r, div), S_REF, vol, t,
                 r, div)


def delta_du_pic(t: float, vol: float = VOL_REF, r: float = TAUX,
                 div: float = DIVIDENDE) -> float:
    """Le delta de l'option où le vanna culmine."""
    return G.delta_comptant(S_REF * moneyness_du_pic(t, vol, r, div), S_REF,
                            vol, t, r, div)


def pic_balaye(t: float, vol: float = VOL_REF, n: int = 60000,
               r: float = TAUX, div: float = DIVIDENDE) -> tuple[float, float]:
    """Le contrôle : le maximum de `vanna` sur un balayage de moneyness."""
    best = (0.0, -math.inf)
    for i in range(n + 1):
        m = 0.30 + 1.40 * i / n
        v = vanna(S_REF * m, S_REF, vol, t, r, div)
        if v > best[1]:
            best = (m, v)
    return best


#: La fenêtre de moneyness que la planche du guide fixe.
FENETRE = (0.80, 1.20)

#: Échéances balayées pour le pic, en jours. Elles couvrent la planche du
#: guide, qui va d'un jour à cent quatre-vingts, et vont au-delà — c'est ce
#: au-delà qui montre que la fenêtre décide de la réponse.
JOURS_PIC: tuple[float, ...] = (1.0, 7.0, 30.0, 90.0, 180.0, 365.0, 730.0,
                                1825.0)


def dans_la_fenetre(t: float, vol: float = VOL_REF) -> bool:
    """Le pic tombe-t-il encore dans la fenêtre de la planche du guide ?"""
    return FENETRE[0] <= moneyness_du_pic(t, vol) <= FENETRE[1]


def vanna_max_fenetre(t: float, vol: float = VOL_REF, n: int = 4000) -> float:
    """Le maximum de `|vanna|` **vu à travers la fenêtre du guide**."""
    return max(vanna(S_REF * (FENETRE[0] + (FENETRE[1] - FENETRE[0]) * i / n),
                     S_REF, vol, t)
               for i in range(n + 1))


def table_pic() -> Table:
    rows = []
    for j in JOURS_PIC:
        t = j / JOURS_AN
        m = moneyness_du_pic(t)
        mb, vb = pic_balaye(t)
        rows.append([
            num(j, 0),
            num(m, 4),
            num(mb, 4),
            num(100 * delta_du_pic(t), 1),
            num(vanna_du_pic(t), 4),
            num(vanna_max_fenetre(t), 4),
            "oui" if dans_la_fenetre(t) else "non",
        ])
    return Table(
        key="va_pic",
        caption="Le lieu du maximum, et la fenêtre qui décide de la réponse",
        headers=["Jours", "S/K du pic (forme fermée)", "S/K balayé (contrôle)",
                 "Delta au pic (%)", "Vanna au pic",
                 "Vanna maximal dans la fenêtre 0,80–1,20",
                 "Le pic est-il dans la fenêtre"],
        rows=rows,
        note="Le guide écrit que le vanna est le plus grand « dans la bande "
             "des vingt à quatre-vingts deltas, aux échéances intermédiaires, "
             "ni à la monnaie ni dans les ailes lointaines ». Les trois "
             "premières colonnes donnent le lieu exact : la forme fermée est "
             "`d₁* = (σ√T − √(σ²T + 4))/2`, **la même racine que le pic du "
             "charm** de la partie XX, parce que les deux grandeurs sont "
             "`φ(d₁)` multipliée par une fonction affine de `d₁` ; le "
             "balayage la confirme. Le pic se tient à un **delta presque "
             "constant** — " + num(100 * delta_du_pic(1.0 / JOURS_AN), 0)
             + " % à un jour, " + num(100 * delta_du_pic(5.0), 0) + " % à "
             "cinq ans — donc légèrement en dehors de la bande que le guide "
             "nomme, et symétriquement à son image au-dessus. *À la monnaie "
             "le vanna est nul, donc « le plus grand dans la bande » se lit "
             "mal : il est le plus grand sur les deux bords de la bande et "
             "nul en son centre.*\n\nLa cinquième colonne est le résultat de "
             "la table. Le vanna au pic **croît de bout en bout** avec "
             "l'échéance : il n'y a pas d'échéance intermédiaire "
             "privilégiée. Ce qui décroît est la sixième colonne, celle qu'on "
             "voit à travers la fenêtre `0,80–1,20` que la planche du guide a "
             "fixée — parce que le pic migre vers l'extérieur comme la racine "
             "du temps et **sort de la fenêtre** au-delà de six mois. *« Aux "
             "échéances intermédiaires » n'est pas une propriété du vanna, "
             "c'est une propriété du cadre.* C'est le piège que ce dépôt a "
             "trouvé six fois dans ses propres figures, sous le nom de la "
             "légende écrite devant un cadre borné, et il le retrouve ici "
             "dans une figure qui n'est pas la sienne.",
    )


# ---------------------------------------------------------------------------
# V. La section 2 nomme le mauvais grec
# ---------------------------------------------------------------------------

#: La peau du guide, lue sur son propre graphique : trente pour cent de
#: volatilité implicite à quatre-vingt-cinq, vingt à cent quinze, linéaire.
PEAU_HAUTE = 0.30
PEAU_BASSE = 0.20
PEAU_SPOT_BAS = 85.0
PEAU_SPOT_HAUT = 115.0


def pente_de_peau() -> float:
    """`∂σ/∂S` — la pente de la peau du guide, par point d'indice."""
    return (PEAU_BASSE - PEAU_HAUTE) / (PEAU_SPOT_HAUT - PEAU_SPOT_BAS)


def peau(s: float) -> float:
    """La volatilité implicite au comptant `s`, sur la peau déclarée."""
    return PEAU_HAUTE + pente_de_peau() * (s - PEAU_SPOT_BAS)


def delta_reevalue(s: float, k: float, t: float, h: float = 0.005) -> float:
    """La dérivée totale du prix par rapport au comptant, **peau comprise**.

    C'est la seule référence qui ne suppose rien : on réévalue l'option de
    part et d'autre du comptant en laissant la volatilité implicite suivre la
    peau, et on divise. Tout le reste de la section se compare à elle.
    """
    return (th.call(s + h, k, peau(s + h), t, TAUX, DIVIDENDE)
            - th.call(s - h, k, peau(s - h), t, TAUX, DIVIDENDE)) / (2.0 * h)


def delta_par_vega(s: float, k: float, t: float) -> float:
    """`Δ + 𝒱·∂σ/∂S` — la correction juste, celle que le graphique montre."""
    return (G.delta_comptant(s, k, peau(s), t, TAUX, DIVIDENDE)
            + vg.vega(s, k, peau(s), t, TAUX, DIVIDENDE) * pente_de_peau())


def delta_par_vanna(s: float, k: float, t: float) -> float:
    """`Δ + vanna·∂σ/∂S` — la formule du guide, écrite telle quelle."""
    return (G.delta_comptant(s, k, peau(s), t, TAUX, DIVIDENDE)
            + vanna(s, k, peau(s), t) * pente_de_peau())


def gamma_reevalue(s: float, k: float, t: float, h: float = 0.05) -> float:
    """La dérivée totale du delta, peau comprise — le gamma effectif mesuré."""
    return (delta_reevalue(s + h, k, t) - delta_reevalue(s - h, k, t)) / (2.0 * h)


def gamma_bs(s: float, k: float, vol: float, t: float) -> float:
    """`Γ = e^{−qT}φ(d₁)/(Sσ√T)`."""
    d1, _ = G._d(s, k, vol, t, TAUX, DIVIDENDE)
    return math.exp(-DIVIDENDE * t) * _phi(d1) / (s * vol * math.sqrt(t))


def gamma_par_vanna(s: float, k: float, t: float) -> float:
    """`Γ + 2·vanna·σ′ + volga·σ′²` — la formule dont le vanna est le grec."""
    v = peau(s)
    p = pente_de_peau()
    return (gamma_bs(s, k, v, t) + 2.0 * vanna(s, k, v, t) * p
            + vg.volga(s, k, v, t, TAUX, DIVIDENDE) * p * p)


#: Comptants balayés pour la table du delta effectif.
SPOTS: tuple[float, ...] = (88.0, 94.0, 100.0, 106.0, 112.0)

#: L'échéance de la démonstration, en jours.
JOURS_PEAU = 90.0


def table_mauvais_grec() -> Table:
    t = JOURS_PEAU / JOURS_AN
    rows = []
    for s in SPOTS:
        vrai = delta_reevalue(s, S_REF, t)
        bs = G.delta_comptant(s, S_REF, peau(s), t, TAUX, DIVIDENDE)
        pv = delta_par_vega(s, S_REF, t)
        pa = delta_par_vanna(s, S_REF, t)
        rows.append([
            num(s, 0),
            num(100 * peau(s), 1),
            num(bs, 4),
            num(vrai, 4),
            num(pv, 4),
            num(pa, 4),
            num(100 * (pa - bs) / (vrai - bs), 2),
        ])
    s0 = 100.0
    vrai0 = delta_reevalue(s0, S_REF, t)
    bs0 = G.delta_comptant(s0, S_REF, peau(s0), t, TAUX, DIVIDENDE)
    pa0 = delta_par_vanna(s0, S_REF, t)
    return Table(
        key="va_mauvais_grec",
        caption="La correction de peau, et le grec que la formule du guide nomme",
        headers=["Comptant", "Volatilité de la peau (%)", "Delta de la formule",
                 "Delta réévalué (référence)", "Avec le véga",
                 "Avec le vanna (la formule du guide)",
                 "Part de la correction captée (%)"],
        rows=rows,
        note="La section 2 du guide écrit `Δ_effectif ≈ Δ + vanna·∂σ/∂S`. Le "
             "membre de droite n'est pas un delta : `vanna` se compte en "
             "inverse de volatilité, `∂σ/∂S` en volatilité par point, et leur "
             "produit en inverse de point. La correction juste porte le "
             "**véga** — la dérivée du prix par rapport à la volatilité — et "
             "la colonne « avec le véga » reproduit la réévaluation complète "
             "à la quatrième décimale, sur toute la plage. La formule du "
             "guide, elle, capte "
             + num(100 * (pa0 - bs0) / (vrai0 - bs0), 2) + " % de la "
             "correction au comptant de référence. *Ce n'est pas une "
             "approximation grossière, c'est une grandeur d'une autre "
             "espèce.*\n\nLa formule est en réalité celle du **gamma** "
             "effectif portant le nom du delta, et la table suivante le "
             "vérifie. Le graphique posé sous elle, lui, est juste : l'écart "
             "entre ses deux courbes de delta est bien ce que la colonne "
             "« avec le véga » mesure — "
             + num(abs(vrai0 - bs0), 4) + " de delta au comptant de "
             "référence, sur une option à trois mois. Sur un contrat à "
             + num(nv.MULTIPLICATEUR, 0) + " dollars le point, un livre "
             "couvert au delta de la formule est court de cette fraction "
             "d'un contrat par option, et il le découvre en baisse.",
    )


def table_gamma_effectif() -> Table:
    t = JOURS_PEAU / JOURS_AN
    rows = []
    for s in SPOTS:
        v = peau(s)
        p = pente_de_peau()
        rows.append([
            num(s, 0),
            num(gamma_bs(s, S_REF, v, t), 6),
            num(gamma_reevalue(s, S_REF, t), 6),
            num(gamma_bs(s, S_REF, v, t) + 2.0 * vanna(s, S_REF, v, t) * p, 6),
            num(gamma_par_vanna(s, S_REF, t), 6),
        ])
    return Table(
        key="va_gamma_effectif",
        caption="Le grec du guide est le bon, mais c'est le gamma qu'il corrige",
        headers=["Comptant", "Gamma de la formule",
                 "Gamma réévalué (référence)", "Avec `2·vanna·σ′`",
                 "Avec `2·vanna·σ′ + volga·σ′²`"],
        rows=rows,
        note="Le vanna entre bel et bien dans une correction de peau, mais "
             "dans celle du **gamma** : dériver `Δ + 𝒱·σ′` par rapport au "
             "comptant donne `Γ + 2·vanna·σ′ + volga·σ′²`, et la dernière "
             "colonne reproduit la réévaluation à la sixième décimale. Deux "
             "détails séparent cette identité de la formule du guide, et ils "
             "ne sont pas décoratifs : le facteur **deux**, qui vient de ce "
             "que la peau entre à la fois par le véga et par le delta, et le "
             "terme de **volga**, qui est celui de la partie XXII. *Le guide "
             "a pris le bon grec et l'a mis dans la mauvaise équation ;* et "
             "comme il a par ailleurs tracé la bonne courbe, rien dans sa "
             "page ne le signale. C'est le mode de défaillance que ce dépôt "
             "connaît le mieux — un code juste et une figure fausse, ou "
             "l'inverse — et il ne se voit qu'en calculant les deux.",
    )


# ---------------------------------------------------------------------------
# VI. Ce que le test rend, et pourquoi le dépôt le croit
# ---------------------------------------------------------------------------
#
# Le guide fait ici ce que la vulgarisation ne fait jamais : il publie le
# résultat de son propre test, contrôlé par un niveau témoin placé à la même
# distance de l'ouverture, et il ne trouve rien. C'est exactement le contrôle
# que la partie XIX avait dû ajouter au guide du gamma, donc le dépôt n'a rien
# à corriger — il a de quoi chiffrer.

#: Les distances balayées pour le témoin, en fraction du niveau. Ce sont
#: celles de la partie XIX, reprises telles quelles pour que les deux parties
#: se lisent l'une contre l'autre.
DISTANCES: tuple[float, ...] = (0.0010, 0.0025, 0.0050, 0.0100, 0.0200)


def table_temoin() -> Table:
    """Le témoin apparié en distance, rejoué pour le vanna."""
    rows = []
    for d in DISTANCES:
        pts = d * q.INDEX_LEVEL
        ratio = FRICTION / pts
        rows.append([
            num(100 * d, 2),
            num(pts, 2),
            num(100 * nv.taux_de_touche(pts), 1),
            num(100 * nv.taux_de_reussite_ferme(pts, q.RR_REF * pts), 1),
            num(100 * nv.exces_requis(ratio), 2),
            num(nv.touches_requises(ratio), 0),
        ])
    ref = 0.0050 * q.INDEX_LEVEL
    return Table(
        key="va_temoin",
        caption="Le contrôle que le guide s'impose, et ce qu'il aurait fallu pour le battre",
        headers=["Distance à l'ouverture (%)", "Distance (points)",
                 "Taux de touche (%)", "Taux de réussite du trade (%)",
                 "Excès requis sur le témoin (points de taux)",
                 "Touches requises"],
        rows=rows,
        note="Le guide écrit que les niveaux tirés du vanna agrégé n'ont pas "
             "battu **un niveau témoin placé à la même distance de "
             "l'ouverture**, sur plusieurs années de séances de contrats à "
             "terme d'indice. C'est le contrôle que la partie XIX avait dû "
             "ajouter au guide du gamma, et le dépôt n'a qu'à le rejouer. La "
             "troisième colonne est le taux de touche du principe de "
             "réflexion : *il ne dit que la distance*, et deux niveaux à la "
             "même distance ont le même. La quatrième est le taux de "
             "réussite d'un trade pris sur le niveau, `1/(1+R:R)` — "
             "**constant à toute distance**. Un niveau agrégé ne peut donc "
             "battre son témoin qu'en déplaçant `µ`, et les deux dernières "
             "colonnes disent de combien et à quel prix : à "
             + num(ref, 1) + " points de l'ouverture, il faudrait "
             + num(100 * nv.exces_requis(FRICTION / ref), 2) + " point de "
             "taux de réussite en plus et "
             + num(nv.touches_requises(FRICTION / ref), 0) + " touches pour "
             "l'établir. *Le résultat négatif du guide n'est donc pas une "
             "surprise à expliquer : c'est ce que la loi nulle prédit, et "
             "l'aurait prédit avant l'expérience.*",
    )


# --- l'agrégation, et ses deux inobservables ------------------------------

#: L'échéance de la chaîne, en jours.
JOURS_CHAINE = 7.0

#: Nombre de tirages de signes et de volatilités.
N_TIRAGES = 240

#: Dispersions de la volatilité vraie par strike, en fraction de la
#: volatilité affichée. La reconstruction courante en emploie **une seule**
#: pour toute la chaîne ; aucune de ces valeurs n'est observable ici.
DISPERSIONS_VOL: tuple[float, ...] = (0.00, 0.05, 0.10, 0.20, 0.35)


def vex(spot: float, signes: tuple[float, ...] | None = None,
        vols: tuple[float, ...] | None = None, asymetrie: float = 1.0,
        jours: float = JOURS_CHAINE) -> float:
    """`VEX = Σ vannaᵢ·OIᵢ·m·S·signᵢ`, en milliers par point de volatilité.

    Même construction que le `GEX` de la partie XIX, avec le vanna à la place
    du gamma — et **un inobservable de plus**. Le gamma d'un strike ne demande
    que la volatilité de ce strike ; le vanna la demande aussi, mais il change
    de signe en son milieu, si bien qu'une erreur de volatilité ne déplace pas
    seulement l'amplitude, elle déplace le lieu du changement de signe.
    """
    t = jours / JOURS_AN
    total = 0.0
    for i, (k, oi_c, oi_p) in enumerate(nv.profil_oi(asymetrie)):
        v = nv.VOL_ANNUELLE if vols is None else vols[i]
        a = vanna(spot, k, v, t, TAUX, DIVIDENDE)
        s_c = nv.SIGNE_CALL if signes is None else signes[2 * i]
        s_p = nv.SIGNE_PUT if signes is None else signes[2 * i + 1]
        total += a * spot * 0.01 * nv.MULTIPLICATEUR * (s_c * oi_c
                                                        + s_p * oi_p)
    return total / 1e3


#: Le pas du balayage qui cherche les lignes, en fraction du niveau.
PAS_LIGNE = 0.0015

BORNES = (0.88, 1.14)


def lignes_de_vex(signes: tuple[float, ...] | None = None,
                  vols: tuple[float, ...] | None = None,
                  asymetrie: float = 1.0, bornes: tuple[float, float] = BORNES,
                  jours: float = JOURS_CHAINE) -> tuple[float, ...]:
    """**Toutes** les traversées de zéro de `VEX`, et non la première.

    C'est la différence de fond avec le `GEX` de la partie XIX, et le premier
    jet de ce module l'a manquée : le gamma est positif à tous les strikes,
    donc le profil agrégé est une bosse unique et une bissection le traverse
    une fois. Le vanna, lui, **change de signe en chaque strike**, si bien que
    le profil agrégé en traverse zéro plusieurs fois — ou aucune. Une
    bissection posée sur une boîte dont les deux bouts sont du même signe rend
    alors `nan` et fait croire qu'il n'y a pas de ligne, quand il y en a deux.
    """
    lo, hi = bornes
    n = int(round((hi - lo) / PAS_LIGNE))
    xs = [q.INDEX_LEVEL * (lo + (hi - lo) * i / n) for i in range(n + 1)]
    fs = [vex(x, signes, vols, asymetrie, jours) for x in xs]
    out: list[float] = []
    for i in range(n):
        if fs[i] == 0.0:
            out.append(xs[i])
        elif fs[i] * fs[i + 1] < 0.0:
            a, b, fa = xs[i], xs[i + 1], fs[i]
            for _ in range(50):
                m = 0.5 * (a + b)
                fm = vex(m, signes, vols, asymetrie, jours)
                if fa * fm <= 0.0:
                    b = m
                else:
                    a, fa = m, fm
            out.append(0.5 * (a + b))
    return tuple(out)


@lru_cache(maxsize=64)
def compte_de_lignes(part_connue: float, dispersion: float,
                     n: int = N_TIRAGES, seed: int = SEED + 3,
                     asymetrie: float = 1.0
                     ) -> tuple[tuple[int, ...], float, float, float]:
    """Le décompte des lignes, et la bande de leurs positions.

    Rend (histogramme du nombre de lignes de zéro à trois et plus, cinquième
    centile, médiane, quatre-vingt-quinzième centile des positions).
    """
    rng = Rng(seed)
    n_strikes = len(nv.STRIKES)
    hist = [0, 0, 0, 0]
    positions: list[float] = []
    for _ in range(n):
        signes: list[float] = []
        for _ in range(n_strikes):
            for suppose in (nv.SIGNE_CALL, nv.SIGNE_PUT):
                if rng.uniform() < part_connue:
                    signes.append(suppose)
                else:
                    signes.append(1.0 if rng.uniform() < 0.5 else -1.0)
        vols = tuple(max(0.02, nv.VOL_ANNUELLE * (1.0 + dispersion
                                                  * rng.gauss()))
                     for _ in range(n_strikes))
        xs = lignes_de_vex(tuple(signes), vols, asymetrie)
        hist[min(3, len(xs))] += 1
        positions.extend(xs)
    positions.sort()
    if not positions:
        return (tuple(hist), math.nan, math.nan, math.nan)

    def qt(p: float) -> float:
        return positions[min(len(positions) - 1,
                             int(p * (len(positions) - 1)))]

    return (tuple(hist), qt(0.05), qt(0.50), qt(0.95))


def table_agregation() -> Table:
    a1 = seuil.geometry(0.150).stop_points
    ref = lignes_de_vex()
    rows = []
    for d in DISPERSIONS_VOL:
        hist, lo, med, hi = compte_de_lignes(0.0, d)
        largeur = hi - lo
        rows.append([
            num(100 * d, 0),
            num(100 * hist[0] / N_TIRAGES, 0),
            num(100 * hist[1] / N_TIRAGES, 0),
            num(100 * hist[2] / N_TIRAGES, 0),
            num(100 * hist[3] / N_TIRAGES, 0),
            num(largeur, 0),
            num(largeur / a1, 0),
        ])
    return Table(
        key="va_agregation",
        caption="Combien de lignes le vanna agrégé porte, et où elles tombent",
        headers=["Dispersion de la volatilité vraie (%)", "Aucune ligne (%)",
                 "Une (%)", "Deux (%)", "Trois ou plus (%)",
                 "Bande des positions (points)", "En stops élargis"],
        rows=rows,
        note="Le guide nomme le mécanisme de son propre résultat négatif : "
             "calculer le vanna du teneur demande de connaître le **signe** "
             "de son inventaire et la **volatilité vraie** de chaque strike, "
             "et les reconstructions grand public emploient un intérêt "
             "ouvert sans signe et une volatilité unique. La table le chiffre "
             "sur la même chaîne que le `GEX` de la partie XIX, et le premier "
             "résultat vient avant tout tirage : **sous l'hypothèse de signe "
             "du guide lui-même, le profil agrégé traverse zéro "
             + num(len(ref), 0) + " fois**, à "
             + " et ".join(num(x, 0) for x in ref) + ". Le `GEX` n'en a "
             "qu'une parce que le gamma est positif à tous les strikes ; le "
             "vanna change de signe en chacun, donc le profil agrégé en a "
             "plusieurs. *« La » ligne de vanna n'est pas un objet défini, "
             "et une bissection posée sur une boîte en rend une au hasard "
             "des bornes.* Le premier jet de ce module est tombé dans ce "
             "trou : sa bissection a rendu « pas de ligne » là où il y en "
             "avait deux, parce que les deux bouts de la boîte étaient du "
             "même signe.\n\nLes colonnes du milieu ajoutent l'ignorance "
             "du signe, et le résultat est **l'inverse de celui de la partie "
             "XIX**. Le `GEX` y échouait par absence — dans la moitié des "
             "tirages il n'existait aucune bascule. Le vanna échoue par "
             "abondance : il en existe presque toujours, et le plus souvent "
             "trois ou plus. *Un niveau qui n'existe pas se remarque ; un "
             "niveau qui existe en trois exemplaires se choisit*, et le "
             "choix est le degré de liberté que la partie III appelle un "
             "levier. La bande où ils tombent vaut plus de cent fois le stop "
             "élargi de la partie X.\n\nUne hypothèse écrite d'avance est "
             "**réfutée par la mesure** et publiée telle quelle : on "
             "attendait que le second inobservable élargisse la bande. Il ne "
             "l'élargit pas — le signe la domine entièrement — mais il fait "
             "autre chose que la table montre, et qui n'avait pas été "
             "prévu : il **multiplie les lignes**, la part des tirages à "
             "trois lignes ou plus passant de "
             + num(100 * compte_de_lignes(0.0, 0.0)[0][3] / N_TIRAGES, 0)
             + " % à "
             + num(100 * compte_de_lignes(0.0, DISPERSIONS_VOL[-1])[0][3]
                   / N_TIRAGES, 0) + " %.",
    )


# ---------------------------------------------------------------------------
# Les quatre notes de pupitre du guide
# ---------------------------------------------------------------------------


def strike_du_delta_put(cible: float, t: float, vol: float = VOL_REF) -> float:
    """Le strike d'un put de delta donné (négatif), par bissection."""
    lo, hi = 1.0, 20.0 * S_REF
    for _ in range(200):
        k = 0.5 * (lo + hi)
        d = G.delta_comptant(S_REF, k, vol, t, TAUX,
                             DIVIDENDE) - math.exp(-DIVIDENDE * t)
        if d > cible:
            lo = k
        else:
            hi = k
    return 0.5 * (lo + hi)


def risk_reversal(delta: float = 0.25, jours: float = 90.0,
                  vol: float = VOL_REF) -> tuple[float, float, float, float]:
    """(strike call, strike put, véga net, vanna net) d'un risk reversal.

    Long un call de `delta`, court un put de `−delta`, tous deux hors de la
    monnaie. Le véga net est **identiquement nul**, et ce n'est pas une
    coïncidence numérique : le véga vaut `Se^{−qT}φ(d₁)√T`, il ne dépend de
    `d₁` que par la fonction **paire** `φ`, et les deux strikes ont des `d₁`
    opposés par construction. Le guide écrit « quasi nul » ; c'est exact.
    """
    t = jours / JOURS_AN
    kc = strike_du_delta(delta, t, vol)
    kp = strike_du_delta_put(-delta, t, vol)
    v = vg.vega(S_REF, kc, vol, t, TAUX, DIVIDENDE) - vg.vega(
        S_REF, kp, vol, t, TAUX, DIVIDENDE)
    a = vanna(S_REF, kc, vol, t) - vanna(S_REF, kp, vol, t)
    return (kc, kp, v, a)


def derive_de_couverture(delta: float, jours: float, basse: float = VOL_BASSE,
                         haute: float = VOL_HAUTE) -> float:
    """Ce qu'une couverture posée à `basse` doit à la volatilité `haute`.

    C'est la note du guide sur la couverture qui « se dégrade dans une
    panique » : la couverture a été calculée à l'ancienne volatilité, et
    l'écart est un delta entier, mesuré et non approché.
    """
    t = jours / JOURS_AN
    k = strike_du_delta(delta, t, basse)
    return (G.delta_comptant(S_REF, k, haute, t, TAUX, DIVIDENDE)
            - G.delta_comptant(S_REF, k, basse, t, TAUX, DIVIDENDE))


#: Deltas balayés pour la note de couverture.
DELTAS: tuple[float, ...] = (0.10, 0.20, 0.35, 0.50)


def table_pratique() -> Table:
    kc, kp, vnet, anet = risk_reversal()
    t = 90.0 / JOURS_AN
    brut = (vg.vega(S_REF, kc, VOL_REF, t, TAUX, DIVIDENDE)
            + vg.vega(S_REF, kp, VOL_REF, t, TAUX, DIVIDENDE))
    k_aile = strike_du_delta_put(-0.10, t)
    a_aile = vanna(S_REF, k_aile, VOL_REF, t)
    rows = [
        ["Le risk reversal est le trade de vanna pur : véga quasi nul, "
         "vanna grand",
         "véga net " + num(abs(vnet), 6) + " sur " + num(brut, 1) + " brut",
         "exact, et c'est une **identité**"],
        ["Une couverture posée en marché calme est fausse dans la panique",
         "un vingt-deltas dérive de "
         + num(100 * derive_de_couverture(0.20, 90.0), 0) + " deltas de "
         + num(100 * VOL_BASSE, 0) + " % à " + num(100 * VOL_HAUTE, 0) + " %",
         "exact, et le chiffre manquait"],
        ["Une aile de put vendue est **courte** de vanna dans la baisse",
         "vanna de l'option " + num(a_aile, 4, signed=True)
         + ", donc la position vendeuse est à "
         + num(-a_aile, 4, signed=True),
         "le signe est l'inverse sous la convention du guide"],
        ["La convention de signe varie : par point de volatilité ou par 1,00",
         "un facteur " + num(100.0, 0),
         "exact, et c'est la faute que la ligne du dessus commet"],
    ]
    return Table(
        key="va_pratique",
        caption="Les quatre notes de pupitre, passées à la mesure",
        headers=["La note", "Ce que la mesure rend", "Verdict"],
        rows=rows,
        note="La première note est la plus forte des six documents, et le "
             "dépôt la **renforce** au lieu de la corriger : le véga net d'un "
             "risk reversal symétrique en delta n'est pas « quasi nul », il "
             "est *identiquement* nul, à toute échéance et à toute "
             "volatilité. Le véga vaut `Se^{−qT}φ(d₁)√T`, il ne dépend de "
             "`d₁` que par la fonction **paire** `φ`, et les deux strikes ont "
             "par construction des `d₁` opposés. C'est une symétrie, pas une "
             "approximation.\n\nLa troisième note tombe sur le piège que la "
             "quatrième annonce. Sous la convention que le guide définit "
             "lui-même — `vanna = ∂Δ/∂σ` — une aile de put hors de la monnaie "
             "a un vanna **négatif**, donc le vendeur en est **long**. La "
             "phrase est juste sur le fond : le delta de sa position monte "
             "quand la volatilité monte, donc il se retrouve plus long qu'il "
             "ne croyait au moment où le marché tombe, et il y perd. Mais "
             "elle nomme ce risque « court de vanna », ce qui est le signe "
             "opposé. *Deux lignes plus bas, le guide met en garde contre "
             "les conventions de signe et demande de les vérifier avant de "
             "compenser.*",
        wrap_cols=[0, 1, 2],
    )


# ---------------------------------------------------------------------------
# VII. Le décompte, sur six parties
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Affirmation:
    enonce: str
    grandeur: str
    mesure: str


def affirmations() -> tuple[Affirmation, ...]:
    t90 = 90.0 / JOURS_AN
    _, _, vnet, _ = risk_reversal()
    k30, e30, _, v30 = deplacement(30.0 / JOURS_AN)
    return (
        Affirmation(
            "Le vanna s'annule légèrement au-dessus de la monnaie, positif "
            "au-dessous et négatif au-dessus",
            "le risque",
            "exact, et la condition se calcule : `r < q + σ²/2`, le taux de "
            "la partie XXIII"),
        Affirmation(
            "Le vanna ramène toujours le delta vers un demi",
            "rien",
            "faux deux fois : sur la bande de volga négative, et parce que "
            "le delta tend vers un"),
        Affirmation(
            "De 15 % à 45 %, un call de vingt deltas en vaut trente environ",
            "le risque",
            "la mesure rend " + num(100 * e30, 0) + " ; trente s'atteignent "
            "à " + num(100 * v30, 1) + " %"),
        Affirmation(
            "Le vanna est le plus grand dans la bande des vingt à "
            "quatre-vingts deltas, aux échéances intermédiaires",
            "rien",
            "le pic est à " + num(100 * delta_du_pic(t90), 0) + " deltas et "
            "croît de bout en bout ; « intermédiaires » décrit la fenêtre"),
        Affirmation(
            "Le delta effectif vaut `Δ + vanna·∂σ/∂S`",
            "le risque",
            "la correction porte le **véga** ; cette formule est celle du "
            "gamma effectif, à un facteur deux près"),
        Affirmation(
            "Le risk reversal est le trade de vanna pur : véga quasi nul",
            "le risque",
            "exact, et mieux : le véga net vaut " + num(abs(vnet), 6)
            + " — une identité de parité"),
        Affirmation(
            "Une aile de put vendue est courte de vanna dans la baisse",
            "le risque",
            "le mécanisme est réel, le signe est l'inverse sous la "
            "convention que le guide définit"),
        Affirmation(
            "Les niveaux de vanna agrégé n'ont pas battu un témoin apparié "
            "en distance",
            "rien",
            "exact, et c'est ce que la loi nulle prédisait avant "
            "l'expérience"),
    )


def compte_par_grandeur() -> dict[str, int]:
    out: dict[str, int] = {}
    for a in affirmations():
        out[a.grandeur] = out.get(a.grandeur, 0) + 1
    return out


def familles() -> tuple[tuple[str, int], ...]:
    """Les six parties d'options, comptées dans leurs propres modules."""
    return R.familles() + (("Vanna, partie XXIV", len(affirmations())),)


def table_reste() -> Table:
    rows = [[a.enonce, a.grandeur, a.mesure] for a in affirmations()]
    c = compte_par_grandeur()
    return Table(
        key="va_reste",
        caption="Huit affirmations, et le décompte des six parties d'options",
        headers=["L'affirmation", "Ce qu'elle déplace",
                 "Ce que la mesure en dit"],
        rows=rows,
        note="Le décompte se lit dans l'identité `E[R] = (µ·E[τ∧T] − c)/a` : "
             + num(c.get("le risque", 0), 0) + " affirmations déplacent le "
             "**risque**, " + num(c.get("rien", 0), 0) + " ne déplacent "
             "rien, aucune ne touche à l'horloge, et **aucune ne touche à la "
             "direction**. C'est la deuxième partie d'options consécutive "
             "dont cette colonne est vide. Sur les "
             + num(sum(n for _, n in familles()), 0) + " affirmations des "
             "six parties, *aucune ne donne un sens*.\n\nCe guide est "
             "pourtant le meilleur des six sur un point qui compte plus que "
             "ses formules : **il publie le résultat de son propre test, "
             "contre un témoin apparié en distance, et il ne trouve rien.** "
             "C'est le contrôle que la partie XIX avait dû ajouter au guide "
             "du gamma, et qu'aucun des quatre autres n'a produit. La "
             "conclusion de la série ne change pas — un guide rend une "
             "méthode de lecture, jamais une direction — mais celui-ci rend "
             "en plus la seule chose qui vaille dans un document de marché : "
             "*le protocole qui l'aurait réfuté, et son résultat.*",
        wrap_cols=[0, 2],
    )


# ---------------------------------------------------------------------------
# Les quatre reliefs
# ---------------------------------------------------------------------------
#
# Les axes sont écrits de façon que le **maximum tombe au coin du fond** : en
# projection isométrique le coin (0, 0) est le plus éloigné, et un relief qui
# monte vers l'horizon se lit.

SURF_ECHEANCE: tuple[float, ...] = (1825.0, 730.0, 365.0, 180.0, 90.0, 30.0)
SURF_MONEYNESS: tuple[float, ...] = (0.50, 0.62, 0.75, 0.87, 1.00, 1.12)

SURF_VOL: tuple[float, ...] = (0.60, 0.45, 0.35, 0.25, 0.18, 0.12)
SURF_ECHEANCE_BANDE: tuple[float, ...] = (730.0, 365.0, 180.0, 90.0, 30.0, 7.0)

SURF_PENTE: tuple[float, ...] = (-0.0060, -0.0045, -0.0033, -0.0022,
                                 -0.0012, -0.0005)
SURF_ECHEANCE_PEAU: tuple[float, ...] = (730.0, 365.0, 180.0, 90.0, 30.0, 7.0)

SURF_MONEYNESS_RET: tuple[float, ...] = (1.60, 1.40, 1.25, 1.15, 1.08, 1.03)
SURF_ECHEANCE_RET: tuple[float, ...] = (30.0, 60.0, 120.0, 250.0, 500.0,
                                        1000.0)


@lru_cache(maxsize=2)
def surface_vanna() -> tuple[tuple[float, ...], ...]:
    """`|vanna|` en échéance et en moneyness — l'arête qui migre."""
    return tuple(tuple(abs(vanna(S_REF * m, S_REF, VOL_REF, j / JOURS_AN))
                       for m in SURF_MONEYNESS)
                 for j in SURF_ECHEANCE)


@lru_cache(maxsize=2)
def surface_desobeissance() -> tuple[tuple[float, ...], ...]:
    """La largeur de la bande où la règle s'inverse, en volatilité et échéance."""
    return tuple(tuple(100.0 * largeur_de_desobeissance(j / JOURS_AN, v)
                       for j in SURF_ECHEANCE_BANDE)
                 for v in SURF_VOL)


@lru_cache(maxsize=2)
def surface_peau() -> tuple[tuple[float, ...], ...]:
    """La correction de peau du delta, en pente de peau et en échéance."""
    out = []
    for p in SURF_PENTE:
        ligne = []
        for j in SURF_ECHEANCE_PEAU:
            t = j / JOURS_AN
            ligne.append(abs(vg.vega(S_REF, S_REF, VOL_REF, t, TAUX,
                                     DIVIDENDE) * p))
        out.append(tuple(ligne))
    return tuple(out)


@lru_cache(maxsize=2)
def surface_retournement() -> tuple[tuple[float, ...], ...]:
    """La volatilité du retournement, en moneyness et en échéance."""
    return tuple(tuple(100.0 * vol_du_retournement(m, j / JOURS_AN)
                       for j in SURF_ECHEANCE_RET)
                 for m in SURF_MONEYNESS_RET)


# ---------------------------------------------------------------------------
# Valeurs, tables, et exécution directe
# ---------------------------------------------------------------------------


def values() -> dict[str, str]:
    t90 = 90.0 / JOURS_AN
    t30 = 30.0 / JOURS_AN
    k30, e30, l30, v30 = deplacement(t30)
    _, _, vnet, anet = risk_reversal()
    vrai = delta_reevalue(S_REF, S_REF, JOURS_PEAU / JOURS_AN)
    bs = G.delta_comptant(S_REF, S_REF, peau(S_REF), JOURS_PEAU / JOURS_AN,
                          TAUX, DIVIDENDE)
    pa = delta_par_vanna(S_REF, S_REF, JOURS_PEAU / JOURS_AN)
    ref = lignes_de_vex()
    hist0 = compte_de_lignes(0.0, 0.0)[0]
    hist1 = compte_de_lignes(0.0, DISPERSIONS_VOL[-1])[0]
    _, lo, med, hi = compte_de_lignes(0.0, 0.0)
    a1 = seuil.geometry(0.150).stop_points
    k_aile = strike_du_delta_put(-0.10, t90)
    return {
        "va_facteur_racine": num(1.0 / math.sqrt(t30), 1),
        "va_taux_pic": num(100 * R.taux_du_pic_exact(), 2),
        "va_zero_30": num(10000.0 * (moneyness_du_zero(t30) - 1.0), 1),
        "va_zero_365": num(10000.0 * (moneyness_du_zero(1.0) - 1.0), 0),
        "va_bande_30": num(100 * largeur_de_desobeissance(t30), 2),
        "va_bande_365": num(100 * largeur_de_desobeissance(1.0), 1),
        "va_sigma_t": num(VOL_REF * VOL_REF * t30, 6),
        "va_retour_vol": num(100 * vol_du_retournement(1.05, 1.0), 1),
        "va_retour_plancher": num(plancher_du_delta(1.05, 1.0), 3),
        "va_retour_controle": num(plancher_balaye(1.05, 1.0), 3),
        "va_delta_exact": num(100 * e30, 0),
        "va_delta_annonce": num(100 * DELTA_ANNONCE, 0),
        "va_delta_lineaire": num(100 * l30, 0),
        "va_vol_du_trente": num(100 * v30, 1),
        "va_choc_requis": num(100 * (v30 - VOL_BASSE), 1),
        "va_pic_delta_court": num(100 * delta_du_pic(1.0 / JOURS_AN), 0),
        "va_pic_delta_long": num(100 * delta_du_pic(5.0), 0),
        "va_pic_vanna_court": num(vanna_du_pic(1.0 / JOURS_AN), 3),
        "va_pic_vanna_long": num(vanna_du_pic(5.0), 3),
        "va_pic_fenetre_long": num(vanna_max_fenetre(5.0), 3),
        "va_pente_peau": num(1000 * abs(pente_de_peau()), 2),
        "va_correction": num(abs(vrai - bs), 4),
        "va_part_captee": num(100 * (pa - bs) / (vrai - bs), 2),
        "va_vega_net": num(abs(vnet), 6),
        "va_vanna_net": num(abs(anet), 3),
        "va_derive_couverture": num(100 * derive_de_couverture(0.20, 90.0), 0),
        "va_vanna_aile": num(vanna(S_REF, k_aile, VOL_REF, t90), 3,
                             signed=True),
        "va_lignes_ref": num(len(ref), 0),
        "va_lignes_trois": num(100 * hist0[3] / N_TIRAGES, 0),
        "va_lignes_trois_haut": num(100 * hist1[3] / N_TIRAGES, 0),
        "va_lignes_aucune": num(100 * hist0[0] / N_TIRAGES, 0),
        "va_bande_lignes": num(hi - lo, 0),
        "va_bande_stops": num((hi - lo) / a1, 0),
        "va_temoin_exces": num(100 * nv.exces_requis(
            FRICTION / (0.0050 * q.INDEX_LEVEL)), 2),
        "va_temoin_touches": num(nv.touches_requises(
            FRICTION / (0.0050 * q.INDEX_LEVEL)), 0),
        "va_affirmations": num(len(affirmations()), 0),
        "va_total_options": num(sum(n for _, n in familles()), 0),
        "va_vol": num(100 * VOL_REF, 0),
        "va_taux": num(100 * TAUX, 1),
    }


def all_tables() -> dict[str, Table]:
    tables = [table_deux_routes(), table_zero(), table_desobeissance(),
              table_retournement(), table_deplacement(), table_pic(),
              table_mauvais_grec(), table_gamma_effectif(), table_temoin(),
              table_agregation(), table_pratique(), table_reste()]
    return {t.key: t for t in tables}


def main() -> None:
    for t in all_tables().values():
        print(t.to_text())
        print()
    for k, v in values().items():
        print(f"{k:26s} {v}")


if __name__ == "__main__":
    main()
