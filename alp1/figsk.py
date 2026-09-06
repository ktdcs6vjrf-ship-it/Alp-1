"""Les planches de « le skew et le sourire ».

Seize planches, douze à plat et quatre en relief. La cinquième porte le
résultat de la partie — le décalage d'un demi entre deux exposants — et la
huitième porte la puissance que le résultat négatif du guide n'a pas
publiée.

Comme les modules d'options qui précèdent, celui-ci importe ses fonctions
d'échine, de graduation et de pourcentage de `fignv`.
"""

from __future__ import annotations

import math

from . import skew as K
from .figdisc import W, _plate, _source, _surface
from .fignv import _dec, _echine, _pct, _ticks
from .figterm import Board, Panel, _num, _signed

PW = (W - 74.0) / 2.0 - 30.0
PX1 = 74.0
PX2 = 74.0 + (W - 74.0) / 2.0

S = K.S_REF
V = K.VOL_REF
AN = K.JOURS_AN


def _t(jours: float) -> float:
    return jours / AN


# ---------------------------------------------------------------------------
# I. La forme, et les trois conventions
# ---------------------------------------------------------------------------


def fig_sk_forme() -> str:
    """La peau déclarée, et les trois conventions posées dessus."""
    b = _plate(500, "Skew · la forme",
               "Trois conventions posées sur une seule surface",
               "trente jours")

    t = _t(30.0)
    ks = [-0.28 + 0.0056 * i for i in range(101)]

    p1 = Panel(b, PX1, 92, PW, 214, title="La peau à trois échéances",
               readout="volatilité implicite")
    series = [("hm7", "", 7.0), ("hm5", "6 3", 30.0), ("hm3", "2 3", 365.0)]
    courbes = [(cls, dash, j, [(k, K.peau(k, _t(j))) for k in ks])
               for cls, dash, j in series]
    hi = max(y for _, _, _, c in courbes for _, y in c)
    lo = min(y for _, _, _, c in courbes for _, y in c)
    p1.domain(ks[0], ks[-1], lo * 0.94, hi * 1.06)
    p1.frame()
    p1.grid_y(_ticks(lo * 0.94, hi * 1.06, 0.05), lambda v: _pct(v, 0),
              dx=28.0)
    p1.grid_x([-0.2, -0.1, 0.0, 0.1, 0.2], lambda v: _num(v, 1),
              label="logarithme de moneyness")
    p1.vline(0.0, "lvl")
    for cls, dash, j, c in courbes:
        p1.path(c, cls, dash=dash, tip=_num(j, 0) + " jours")
    p1.label(ks[0], hi * 1.02, "le skew descend vers la droite", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Ce que chaque convention sonde",
               readout="volatilité implicite")
    c30 = [(k, K.peau(k, t)) for k in ks]
    p2.domain(ks[0], ks[-1], lo * 0.94, hi * 1.06)
    p2.frame()
    kp = K.moneyness_du_delta(0.75, t)
    kc = K.moneyness_du_delta(0.25, t)
    p2.band_x(kp, kc, "wash")
    p2.grid_y(_ticks(lo * 0.94, hi * 1.06, 0.05), lambda v: _pct(v, 0),
              dx=28.0)
    p2.grid_x([-0.2, -0.1, 0.0, 0.1, 0.2], lambda v: _num(v, 1),
              label="logarithme de moneyness")
    p2.path(c30, "hm3", tip="la peau à trente jours")
    for k in (math.log(0.90), math.log(1.10)):
        p2.dot(k, K.peau(k, t), "hm2", "moneyness fixe", r=5.0)
    for k, nom in ((kp, "put 25Δ"), (kc, "call 25Δ")):
        p2.dot(k, K.peau(k, t), "hm7", nom, r=5.0)
    p2.label(0.0, hi * 1.02, "la bande du risk reversal", dx=0, dy=0,
             anchor="middle")
    p2.label(math.log(0.90), K.peau(math.log(0.90), t),
             "90 %", dx=-8, dy=-9, anchor="end")
    p2.label(math.log(1.10), K.peau(math.log(1.10), t),
             "110 %", dx=8, dy=14)

    b.legend(0.0, 352.0,
             [("hm7", "sept jours, et les strikes 25Δ"),
              ("hm5", "trente jours", "6 3"),
              ("hm3", "un an, et la peau du cadre de droite", "2 3")],
             step=190.0, kind="line")
    b.annotation(0.0, 376.0,
                 "les deux points clairs sont les strikes à vingt-cinq "
                 "deltas, les deux sombres les strikes à 90 et 110 pour cent")
    b.annotation(0.0, 392.0,
                 "la bande claire est celle du risk reversal : elle croît "
                 "en sigma racine T, quand la bande sombre ne bouge jamais")
    b.annotation(0.0, 408.0,
                 "la pente locale est la tangente à la monnaie : la plus "
                 "propre en théorie, la plus bruitée en pratique")

    _source(b, "La surface est déclarée et non ajustée — le dépôt n'a "
               "aucune donnée de marché — mais tout ce que la partie en "
               "tire porte sur la façon dont on la mesure, pas sur sa "
               "forme. Les trois conventions du guide sont posées dessus : "
               "la bande claire est celle que sonde le risk reversal à "
               "vingt-cinq deltas, dont les strikes se déplacent avec le "
               "marché ; les deux points sombres sont ceux de la "
               "convention à moneyness fixe, qui ne se déplacent jamais. "
               "Tout le reste de la partie découle de cette différence de "
               "largeur, et de ce qu'elle fait quand l'échéance ou la "
               "volatilité change.")
    return b.render("La peau declaree a trois echeances, et les trois "
                    "conventions de mesure du skew posees dessus.")


def fig_sk_conventions() -> str:
    """Les trois conventions contre l'échéance."""
    b = _plate(500, "Skew · les trois conventions",
               "Trois nombres que trois pupitres appellent du même nom",
               "en points de volatilité")

    js = [5.0 + 4.0 * i for i in range(91)]

    p1 = Panel(b, PX1, 92, PW, 214,
               title="Le risk reversal et sa forme fermée",
               readout="points de volatilité")
    exact = [(j, 100.0 * K.risk_reversal(_t(j))) for j in js]
    ferme = [(j, 100.0 * K.risk_reversal_ferme(_t(j))) for j in js]
    fixe = [(j, 100.0 * K.pente_moneyness_fixe(_t(j))) for j in js]
    hi = max(y for _, y in fixe)
    p1.domain(js[0], js[-1], 0.0, hi * 1.15)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi * 1.15, 0.5), lambda v: _num(v, 1), dx=24.0)
    p1.grid_x([50, 150, 250, 350], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.path(fixe, "hm3", dash="5 4", tip="pente 90/110")
    p1.path(exact, "hm7", tip="risk reversal, route exacte")
    p1.path(ferme, "hm1", dash="2 3", tip="sa forme fermée")
    p1.label(js[-1], 100.0 * K.pente_moneyness_fixe(_t(365.0)) * 1.10,
             "la pente à moneyness fixe", dx=-8, dy=0, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214,
               title="La bande que chacune sonde",
               readout="logarithme de moneyness")
    bande = [(j, K.largeur_sondee(_t(j))) for j in js]
    hi2 = max(max(y for _, y in bande), K.LARGEUR_FIXE) * 1.20
    p2.domain(js[0], js[-1], 0.0, hi2)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2, 0.05), lambda v: _num(v, 2), dx=26.0)
    p2.grid_x([50, 150, 250, 350], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.hline(K.LARGEUR_FIXE, "lvl")
    p2.path(bande, "hm7", tip="la bande du risk reversal")
    p2.label(js[0], K.LARGEUR_FIXE, "la bande fixe : "
             + _num(K.LARGEUR_FIXE, 3), dx=8, dy=-9)
    p2.label(js[-1], 0.04, "celle du RR croît en racine de T", dx=-8, dy=0,
             anchor="end")

    b.legend(0.0, 352.0,
             [("hm7", "risk reversal 25Δ"), ("hm1", "sa forme fermée", "2 3"),
              ("hm3", "pente 90/110", "5 4")],
             step=200.0, kind="line")
    b.annotation(0.0, 376.0,
                 "la route exacte résout un point fixe : le delta dépend de "
                 "la volatilité, qui dépend du strike, qui dépend du delta")
    b.annotation(0.0, 392.0,
                 "la forme fermée du premier ordre est constante en "
                 "échéance à l'exposant déclaré, et la mesure la suit")
    b.annotation(0.0, 408.0,
                 "les deux conventions se croisent : leur rapport passe de "
                 + _num(K.rapport_des_conventions(_t(30.0)), 2) + " à "
                 + _num(K.rapport_des_conventions(_t(365.0)), 2))

    _source(b, "Le guide donne trois conventions et dit qu'elles sont "
               "toutes en usage et toutes différentes. Le cadre de gauche "
               "montre à quel point : les deux courbes ne se croisent pas "
               "par accident, elles portent des exposants différents. Le "
               "cadre de droite dit pourquoi — les strikes à vingt-cinq "
               "deltas se tiennent à un argument fixe, donc leur écart en "
               "logarithme de moneyness croît en racine du temps, quand "
               "celui de la convention à moneyness fixe ne bouge pas d'un "
               "centième. La forme fermée est le contrôle de la route "
               "exacte, et leur accord est ce qui autorise l'exposant de "
               "la section suivante.")
    return b.render("Les trois conventions contre l echeance, et la bande "
                    "que chacune sonde.")


def fig_sk_vol() -> str:
    """La même mesure à quatre volatilités."""
    b = _plate(490, "Skew · la volatilité",
               "La convention insensible au comptant, sensible à la vol",
               "peau inchangée")

    vols = [0.08 + 0.005 * i for i in range(81)]
    t = _t(30.0)

    p1 = Panel(b, PX1, 92, PW, 214,
               title="Les deux mesures contre la volatilité",
               readout="points de volatilité")
    rr = [(v, 100.0 * K.risk_reversal(t, vol_atm=v)) for v in vols]
    fx = [(v, 100.0 * K.pente_moneyness_fixe(t, vol_atm=v)) for v in vols]
    hi = max(max(y for _, y in rr), max(y for _, y in fx)) * 1.15
    p1.domain(vols[0], vols[-1], 0.0, hi)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi, 1.0), lambda v: _num(v, 0), dx=22.0)
    p1.grid_x([0.10, 0.20, 0.30, 0.40, 0.48], lambda v: _pct(v, 0),
              label="volatilité à la monnaie")
    p1.path(fx, "hm3", dash="5 4", tip="pente 90/110")
    p1.path(rr, "hm7", tip="risk reversal 25Δ")
    p1.label(vols[0], hi * 0.92, "la peau ne bouge pas", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="La bande sondée, contre la volatilité",
               readout="logarithme de moneyness")
    bd = [(v, K.largeur_sondee(t, vol_atm=v)) for v in vols]
    hi2 = max(max(y for _, y in bd), K.LARGEUR_FIXE) * 1.20
    p2.domain(vols[0], vols[-1], 0.0, hi2)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2, 0.05), lambda v: _num(v, 2), dx=26.0)
    p2.grid_x([0.10, 0.20, 0.30, 0.40, 0.48], lambda v: _pct(v, 0),
              label="volatilité à la monnaie")
    p2.hline(K.LARGEUR_FIXE, "lvl")
    p2.path(bd, "hm7", tip="la bande du risk reversal")
    p2.label(vols[0], K.LARGEUR_FIXE, "la bande fixe", dx=8, dy=-9)

    b.legend(0.0, 352.0,
             [("hm7", "risk reversal 25Δ"), ("hm3", "pente 90/110", "5 4")],
             step=240.0, kind="line")
    b.annotation(0.0, 376.0,
                 "la peau est rigoureusement inchangée sur toute la "
                 "planche : seule la façon de la mesurer varie")
    b.annotation(0.0, 392.0,
                 "le guide défend le risk reversal parce que ses strikes "
                 "suivent le comptant, et c'est juste")
    b.annotation(0.0, 408.0,
                 "les mêmes strikes suivent aussi la volatilité, d'un "
                 "facteur " + _num(K.largeur_sondee(t, vol_atm=0.45)
                                   / K.largeur_sondee(t, vol_atm=0.12), 1)
                 + " sur cette plage")

    _source(b, "Toute cette planche est tracée sur une seule peau, qui "
               "ne change pas d'un centième d'un bout à l'autre. Ce qui "
               "change est la volatilité à la monnaie, donc la position des "
               "strikes à vingt-cinq deltas, donc la bande que le risk "
               "reversal sonde. L'argument du guide — la convention de "
               "pupitre est stable quand le comptant dérive — est juste et "
               "muet sur cet axe-là. La conséquence pratique tient en une "
               "phrase : un skew qui « se raidit » peut n'être qu'une "
               "volatilité qui monte, et la convention à moneyness fixe, "
               "que le guide donne comme la moins bonne, est la seule qui "
               "ne confonde pas les deux.")
    return b.render("Les deux conventions contre la volatilite, sur une "
                    "peau rigoureusement inchangee.")


def fig_sk_relief_rapport() -> str:
    """Le relief du rapport des conventions."""
    z = [list(l) for l in K.surface_rapport()]
    vals = [v for l in z for v in l]

    b = _plate(486, "Skew · le relief du rapport",
               "Deux pupitres, deux nombres, et le rapport n'est pas un",
               "hauteur : RR sur pente à moneyness fixe")

    _surface(b, 0.52 * W, 232.0, z, min(vals), max(vals), cx=42.0, cy=13.0,
             cz=158.0,
             row_labels=[_num(j, 0) + " j" for j in K.SURF_JOURS],
             col_labels=[_pct(v, 0) for v in K.SURF_VOLS],
             z_ticks=[(t, _num(t, 1)) for t in _echine(min(vals), max(vals))],
             tip="{v:.2f}", zero=1.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : l'échéance · arête droite : la volatilité "
                 "à la monnaie · hauteur : le rapport des deux conventions")
    b.annotation(0.0, 424.0,
                 "un si les deux mesuraient le même objet : le sol de "
                 "référence est posé à un, et la surface le traverse")
    b.annotation(0.0, 440.0,
                 "les deux axes agissent dans le même sens, parce que la "
                 "bande du risk reversal croît avec le produit sigma racine T")

    _source(b, "La hauteur est le risk reversal divisé par la pente à "
               "moneyness fixe, mesurés sur la même peau. Un si les deux "
               "conventions mesuraient le même objet ; le repère de "
               "hauteur est posé à un et la surface le traverse. Les deux "
               "axes agissent dans le même sens et pour la même raison — "
               "la bande sondée croît avec le produit de la volatilité "
               "par la racine du temps — de sorte qu'un pupitre "
               "qui compare son skew à celui d'un autre compare deux "
               "nombres dont le rapport dépend d'un produit qu'aucun des "
               "deux n'a écrit.")
    return b.render("Relief du rapport des deux conventions, en echeance "
                    "et en volatilite.")


# ---------------------------------------------------------------------------
# II. L'exposant, et l'affirmation qui bascule dessus
# ---------------------------------------------------------------------------


def fig_sk_exposant() -> str:
    """« Le skew s'aplatit avec le ténor » — dans quelle convention ?"""
    b = _plate(510, "Skew · l'exposant",
               "L'affirmation la plus consensuelle dépend de la convention",
               "exposant en échéance")

    hs = [0.0 + 0.02 * i for i in range(66)]

    p1 = Panel(b, PX1, 92, PW, 214,
               title="Les trois exposants contre H",
               readout="d ln(mesure) / d ln T")
    rr = [(h, K.exposant_du_risk_reversal(h)) for h in hs]
    loc = [(h, K.exposant_de_la_pente_locale(h)) for h in hs]
    p1.domain(hs[0], hs[-1], -1.4, 0.65)
    p1.frame()
    p1.grid_y([-1.2, -0.8, -0.4, 0.0, 0.4], lambda v: _signed(v, 1), dx=28.0)
    p1.grid_x([0.0, 0.25, 0.5, 0.75, 1.0, 1.25], lambda v: _num(v, 2),
              label="H déclaré")
    p1.hline(0.0, "lvl")
    p1.vline(K.h_du_basculement(), "lvl")
    p1.path(loc, "hm3", dash="5 4", tip="pente locale")
    p1.path(rr, "hm7", tip="risk reversal")
    p1.dot(K.h_du_basculement(),
           K.exposant_du_risk_reversal(K.h_du_basculement()), "hm7",
           "le basculement", r=4.5)
    p1.label(hs[0], 0.55, "au-dessus de zéro, le skew se raidit", dx=8, dy=0)
    p1.label(K.h_du_basculement(), -1.30, "H = 0,5 : la valeur retenue",
             dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Le décalage des deux exposants",
               readout="risk reversal moins pente locale")
    dec = [(h, K.decalage_des_exposants(h)) for h in hs]
    p2.domain(hs[0], hs[-1], 0.40, 0.60)
    p2.frame()
    p2.grid_y([0.40, 0.45, 0.50, 0.55, 0.60], lambda v: _num(v, 2), dx=26.0)
    p2.grid_x([0.0, 0.25, 0.5, 0.75, 1.0, 1.25], lambda v: _num(v, 2),
              label="H déclaré")
    p2.hline(0.5, "lvl")
    p2.path(dec, "hm5", tip="le décalage")
    p2.label(hs[0], 0.575,
             "mesuré " + _num(K.decalage_des_exposants(), 3)
             + ", et il ne bouge pas", dx=8, dy=0)

    b.legend(0.0, 362.0,
             [("hm7", "l'exposant du risk reversal"),
              ("hm3", "celui de la pente locale", "5 4"),
              ("hm5", "leur décalage, à droite")],
             step=180.0, kind="line")
    b.annotation(0.0, 386.0,
                 "le risk reversal vaut la pente locale fois une bande en "
                 "racine de T : son exposant vaut un demi moins H")
    b.annotation(0.0, 402.0,
                 "il ne s'aplatit qu'au-delà de H égal un demi, et à cette "
                 "valeur son exposant mesuré vaut deux centièmes")
    b.annotation(0.0, 418.0,
                 "le décalage théorique vaut un demi ; mesuré il vaut "
                 + _num(K.decalage_des_exposants(), 3)
                 + ", et il ne bouge pas d'un centième")
    b.annotation(0.0, 434.0,
                 "l'affirmation est donc vraie dans deux conventions sur "
                 "trois, et rien dans sa formulation ne dit lesquelles")

    _source(b, "C'est le résultat de la partie, et il tient en une ligne "
               "d'algèbre. Le risk reversal vaut la pente locale multipliée "
               "par une bande qui croît en racine du temps ; son exposant "
               "est donc décalé d'un demi vers le haut par rapport à celui "
               "des deux conventions à bande fixe. Le cadre de droite est "
               "ce qui fait de cette phrase un résultat plutôt qu'une "
               "coïncidence de réglage : le décalage vaut un demi à quatre "
               "millièmes près sur toute la grille du seul paramètre libre "
               "de la partie. À la valeur que la littérature retient, la "
               "mesure du pupitre ne s'aplatit pas.")
    return b.render("Les trois exposants en echeance contre le parametre "
                    "d aplatissement, et leur decalage.")


def fig_sk_tenor() -> str:
    """Le skew contre l'échéance, dans les trois conventions."""
    b = _plate(490, "Skew · le ténor",
               "Les mêmes courbes, à trois exposants déclarés",
               "rapportées à leur valeur d'un mois")

    js = [5.0 + 4.0 * i for i in range(91)]
    series = [("hm7", "", 0.25), ("hm5", "6 3", 0.50), ("hm3", "2 3", 0.75)]

    p1 = Panel(b, PX1, 92, PW, 214,
               title="Le risk reversal, normalisé",
               readout="un à trente jours")
    courbes = []
    for cls, dash, h in series:
        base = K.risk_reversal(_t(30.0), h)
        courbes.append((cls, dash, h,
                        [(j, K.risk_reversal(_t(j), h) / base) for j in js]))
    hi = max(y for _, _, _, c in courbes for _, y in c) * 1.10
    p1.domain(js[0], js[-1], 0.0, hi)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi, 0.5), lambda v: _num(v, 1), dx=22.0)
    p1.grid_x([50, 150, 250, 350], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.hline(1.0, "lvl")
    for cls, dash, h, c in courbes:
        p1.path(c, cls, dash=dash, tip="H = " + _num(h, 2))
    p1.label(js[-1], 1.06, "un à trente jours", dx=-8, dy=0, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214,
               title="La pente locale, normalisée",
               readout="un à trente jours")
    c2 = []
    for cls, dash, h in series:
        base = K.pente_a_la_monnaie(_t(30.0), h)
        c2.append((cls, dash, h,
                   [(j, K.pente_a_la_monnaie(_t(j), h) / base) for j in js]))
    hi2 = max(y for _, _, _, c in c2 for _, y in c) * 1.10
    p2.domain(js[0], js[-1], 0.0, hi2)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2, 0.5), lambda v: _num(v, 1), dx=22.0)
    p2.grid_x([50, 150, 250, 350], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.hline(1.0, "lvl")
    for cls, dash, h, c in c2:
        p2.path(c, cls, dash=dash, tip="H = " + _num(h, 2))
    p2.label(js[-1], 0.12, "les trois descendent", dx=-8, dy=0, anchor="end")

    b.legend(0.0, 352.0,
             [("hm7", "H = 0,25"), ("hm5", "H = 0,50", "6 3"),
              ("hm3", "H = 0,75", "2 3")],
             step=200.0, kind="line")
    b.annotation(0.0, 376.0,
                 "les deux cadres portent la même surface, mesurée de deux "
                 "façons, et normalisée au même point")
    b.annotation(0.0, 392.0,
                 "à droite les trois courbes descendent ; à gauche l'une "
                 "monte, une est plate et une descend")
    b.annotation(0.0, 408.0,
                 "c'est la question de la partie XXIII sur un cinquième "
                 "objet : quelle variable tient-on fixe")

    _source(b, "La même peau, la même échéance, deux façons de la mesurer, "
               "et les deux cadres racontent deux histoires. À droite — la "
               "pente locale, la convention théorique — le skew s'aplatit "
               "aux trois exposants, sans exception. À gauche — le risk "
               "reversal, la convention de pupitre — il se raidit au "
               "premier, ne bouge pas au deuxième et ne s'aplatit qu'au "
               "troisième. Les deux courbes normalisées partent du même "
               "point par construction, ce qui rend la divergence "
               "entièrement attribuable à la convention et à rien d'autre.")
    return b.render("Le skew normalise contre l echeance, dans deux "
                    "conventions et a trois exposants.")


def fig_sk_relief_exposant() -> str:
    """Le relief de l'exposant du risk reversal."""
    z = [list(l) for l in K.surface_exposant()]
    vals = [v for l in z for v in l]

    b = _plate(486, "Skew · le relief de l'exposant",
               "Le signe bascule sur une ligne que la volatilité ne déplace pas",
               "hauteur : exposant")

    _surface(b, 0.52 * W, 232.0, z, min(vals), max(vals), cx=42.0, cy=13.0,
             cz=158.0,
             row_labels=[_num(h, 2) for h in K.SURF_H],
             col_labels=[_pct(v, 0) for v in K.SURF_VOLS],
             z_ticks=[(t, _signed(t, 1))
                      for t in _echine(min(vals), max(vals))],
             tip="{v:+.3f}", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : l'exposant d'aplatissement déclaré · arête "
                 "droite : la volatilité · hauteur : l'exposant mesuré")
    b.annotation(0.0, 424.0,
                 "le sol est posé à zéro : au-dessus le skew de pupitre se "
                 "raidit, au-dessous il s'aplatit")
    b.annotation(0.0, 440.0,
                 "elle penche faiblement le long de la volatilité, et dans "
                 "le sens que le mécanisme prédit : la bande s'élargit")

    _source(b, "La hauteur est l'exposant en échéance du risk reversal, "
               "mesuré et non postulé. Le repère de hauteur est posé à "
               "zéro : au-dessus la mesure de pupitre se raidit avec "
               "l'échéance, au-dessous elle s'aplatit, et la ligne qui "
               "sépare les deux tombe à un demi. Ce que le relief ajoute "
               "aux tables est l'axe de la volatilité, sur lequel la "
               "surface est plate : le résultat ne dépend donc pas du "
               "niveau où l'on se place, seulement de la convention et de "
               "l'exposant. Une propriété de la façon de mesurer, pas du "
               "marché mesuré.")
    return b.render("Relief de l exposant du risk reversal, en parametre "
                    "d aplatissement et en volatilite.")


# ---------------------------------------------------------------------------
# III. Le test du guide, sa loi nulle et sa puissance
# ---------------------------------------------------------------------------


def fig_sk_loi_nulle() -> str:
    """La loi nulle d'une corrélation de rang, et le nombre publié dedans."""
    b = _plate(500, "Skew · la loi nulle",
               "Le nombre publié tombe au milieu de ce que le hasard produit",
               "quatre mille tirages")

    loi = K.loi_nulle_du_test(495)
    n = len(loi)

    p1 = Panel(b, PX1, 92, PW, 214,
               title="Sous absence totale de lien",
               readout="densité des tirages")
    lo, hi = -0.16, 0.16
    nb = 40
    pas = (hi - lo) / nb
    comptes = [0] * nb
    for v in loi:
        i = int((v - lo) / pas)
        if 0 <= i < nb:
            comptes[i] += 1
    haut = max(comptes) * 1.28
    p1.domain(lo, hi, 0.0, haut)
    p1.frame()
    p1.band_x(-K.seuil_de_correlation(495), K.seuil_de_correlation(495),
              "wash")
    p1.grid_y(_ticks(0.0, haut, 100.0), lambda v: _num(v, 0), dx=26.0)
    p1.grid_x([-0.15, -0.05, 0.05, 0.15], lambda v: _signed(v, 2),
              label="corrélation de rang")
    # L'épaisseur d'une barre est en **pixels**, jamais en unités de
    # donnée : c'est le piège de la partie XXI, où l'histogramme se
    # réduisait à des cheveux qu'aucun balayage ne voyait.
    largeur = PW * pas / (hi - lo) * 0.86
    for i, c in enumerate(comptes):
        x0 = lo + i * pas
        if c > 0:
            p1.vbar(x0 + 0.5 * pas, 0.0, c, largeur, "hm5",
                    tip=_signed(x0, 3) + " : " + _num(c, 0) + " tirages")
    p1.vline(K.TEST_PUBLIE["correlation"], "lvl")
    p1.label(K.TEST_PUBLIE["correlation"], haut * 0.86,
             "le nombre publié : " + _signed(K.TEST_PUBLIE["correlation"], 3),
             dx=-8, dy=0, anchor="end")
    p1.label(lo, haut * 0.60, "la bande à 95 %", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Le seuil, forme fermée contre mesure",
               readout="corrélation de rang")
    ns = [80 + 40 * i for i in range(66)]
    ferme = [(m, K.seuil_de_correlation(m)) for m in ns]
    mesure = [(m, K.seuil_mesure(m))
              for m in (120, 252, 495, 1000, 2520) if m <= ns[-1]]
    hi2 = max(y for _, y in ferme) * 1.12
    p2.domain(ns[0], ns[-1], 0.0, hi2)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2, 0.05), lambda v: _num(v, 2), dx=26.0)
    p2.grid_x([500, 1000, 1500, 2000, 2500], lambda v: _num(v, 0),
              label="séances")
    p2.path(ferme, "hm4", tip="z sur racine de n moins un")
    for m, v in mesure:
        p2.dot(m, v, "hm1", _num(m, 0) + " séances : " + _num(v, 4), r=4.0)
    p2.vline(K.TEST_PUBLIE["seances"], "lvl")
    p2.label(ns[-1], hi2 * 0.62, "les points sont la mesure", dx=-8, dy=0,
             anchor="end")

    b.legend(0.0, 352.0,
             [("hm5", "la loi nulle simulée"),
              ("hm4", "le seuil de Fisher"), ("hm1", "sa mesure")],
             step=180.0)
    b.annotation(0.0, 376.0,
                 "deux séries indépendantes, corrélation de Spearman, "
                 "quatre mille fois : voilà ce que le hasard produit")
    b.annotation(0.0, 392.0,
                 "le nombre que le guide publie tombe au milieu de cette "
                 "loi, à " + _num(abs(K.ecarts_types_du_publie()), 2)
                 + " écart-type de zéro")
    b.annotation(0.0, 408.0,
                 "la forme fermée du seuil est contrôlée contre les "
                 "quantiles simulés, et les deux se referment")

    _source(b, "Un résultat négatif publié sans sa loi nulle demande au "
               "lecteur de croire que l'auteur connaissait la sienne. La "
               "voici : deux séries indépendantes de quatre cent "
               "quatre-vingt-quinze points, corrélation de rang de "
               "Spearman, quatre mille tirages. Le nombre que le guide "
               "publie tombe au milieu, ce qui confirme entièrement sa "
               "conclusion — il n'a rien trouvé, et il a raison de le "
               "dire. Le cadre de droite donne le seuil, en forme fermée et "
               "mesuré, et c'est lui qui manque au document examiné : sans "
               "seuil, un résultat négatif ne se distingue pas d'un test "
               "sans puissance.")
    return b.render("La loi nulle d une correlation de rang sur quatre cent "
                    "quatre-vingt-quinze seances, et le seuil de Fisher.")


def fig_sk_puissance() -> str:
    """Ce que l'échantillon pouvait détecter, et ce qu'il ne pouvait pas."""
    b = _plate(500, "Skew · la puissance",
               "Le guide ne pouvait pas conclure autrement",
               "à quatre-vingt-quinze pour cent")

    rhos = [0.008 + 0.004 * i for i in range(61)]

    p1 = Panel(b, PX1, 92, PW, 214,
               title="Les séances requises contre l'effet",
               readout="échelle logarithmique")
    c = [(r, K.seances_pour_correlation(r)) for r in rhos]
    p1.domain(rhos[0], rhos[-1], 60.0, 90000.0, ylog=True)
    p1.frame()
    p1.grid_y([100.0, 1000.0, 10000.0], _dec, dx=28.0)
    p1.grid_x([0.05, 0.10, 0.15, 0.20], lambda v: _num(v, 2),
              label="corrélation à établir")
    p1.hline(K.TEST_PUBLIE["seances"], "lvl")
    p1.path(c, "hm7", tip="séances requises")
    p1.dot(0.05, K.seances_pour_correlation(0.05), "hm7", "cinq centièmes",
           r=4.5)
    p1.label(0.05, K.seances_pour_correlation(0.05),
             "0,05 → " + _num(K.annees_pour_correlation(0.05), 1) + " ans",
             dx=10, dy=-9)
    p1.label(rhos[-1], K.TEST_PUBLIE["seances"] * 1.35,
             "l'échantillon du guide", dx=-8, dy=0, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Ce que 495 séances peuvent voir",
               readout="part du seuil atteinte")
    part = [(r, min(1.6, abs(r) / K.seuil_de_correlation(495)))
            for r in rhos]
    p2.domain(rhos[0], rhos[-1], 0.0, 1.7)
    p2.frame()
    p2.grid_y([0.0, 0.5, 1.0, 1.5], lambda v: _num(v, 1), dx=24.0)
    p2.grid_x([0.05, 0.10, 0.15, 0.20], lambda v: _num(v, 2),
              label="corrélation vraie")
    p2.hline(1.0, "lvl")
    p2.path(part, "hm5", tip="part du seuil")
    p2.dot(abs(K.TEST_PUBLIE["correlation"]),
           abs(K.TEST_PUBLIE["correlation"]) / K.seuil_de_correlation(495),
           "hm5", "le nombre publié", r=4.5)
    p2.label(rhos[0], 1.08, "au-dessus, l'effet serait vu", dx=8, dy=0)
    p2.label(rhos[-1], 0.12, "le nombre publié est ici", dx=-8, dy=0,
             anchor="end")

    b.legend(0.0, 352.0,
             [("hm7", "les séances requises"),
              ("hm5", "la part du seuil, à droite")],
             step=240.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le seuil de ce test vaut "
                 + _num(K.seuil_de_correlation(K.TEST_PUBLIE["seances"]), 3)
                 + ", et le guide ne le publie pas")
    b.annotation(0.0, 392.0,
                 "une corrélation de cinq centièmes, qui serait "
                 "considérable ici, demande "
                 + _num(K.annees_pour_correlation(0.05), 1) + " ans")
    b.annotation(0.0, 408.0,
                 "sans le seuil, « nous n'avons rien trouvé » et « nous ne "
                 "pouvions rien trouver » se lisent pareil")

    _source(b, "Le guide publie un résultat négatif honnête, et le dépôt "
               "n'a rien à y redire sur le fond. Ce qu'il ajoute est le "
               "nombre qui rend ce résultat lisible. Sur quatre cent "
               "quatre-vingt-quinze séances, le seuil à quatre-vingt-quinze "
               "pour cent d'une corrélation de rang vaut huit centièmes et "
               "demi : un effet réel de cinq centièmes — qui serait "
               "considérable sur cet objet — serait passé inaperçu, et il "
               "aurait fallu six ans de données pour l'établir. C'est le "
               "budget d'information de la partie IV, rencontré sur un "
               "onzième objet, et la conclusion vaut au-delà de ce guide : "
               "un résultat négatif sans sa puissance ne dit presque rien.")
    return b.render("Les seances requises contre la taille de l effet, et "
                    "ce que l echantillon du guide pouvait voir.")


def fig_sk_relief_puissance() -> str:
    """Le relief de la puissance."""
    z = [list(l) for l in K.surface_puissance()]
    vals = [v for l in z for v in l]

    b = _plate(486, "Skew · le relief de la puissance",
               "Ce qu'un échantillon peut voir, et ce qui lui échappe",
               "hauteur : part du seuil atteinte")

    _surface(b, 0.52 * W, 232.0, z, min(vals), max(vals), cx=42.0, cy=13.0,
             cz=158.0,
             row_labels=[_num(n, 0) for n in K.SURF_SEANCES],
             col_labels=[_num(r, 3) for r in K.SURF_RHO],
             z_ticks=[(t, _num(t, 1)) for t in _echine(min(vals), max(vals))],
             tip="{v:.2f}", zero=1.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : les séances · arête droite : la "
                 "corrélation vraie · hauteur : la part du seuil atteinte")
    b.annotation(0.0, 424.0,
                 "le sol de référence est posé à un : au-dessus l'effet est "
                 "détecté, au-dessous il passe inaperçu")
    b.annotation(0.0, 440.0,
                 "elle n'est pas plafonnée : un plafond ferait un plateau "
                 "d'ex aequo au sommet plutôt qu'une pente lisible")

    _source(b, "La hauteur est la corrélation vraie divisée par le seuil "
               "qu'un échantillon de cette taille impose : au-dessus de un, "
               "l'effet est détecté ; au-dessous, il existe et personne ne "
               "le voit. Le plateau est la région où l'on conclut, la "
               "pente celle où l'on ne conclut pas, et la ligne qui les "
               "sépare est la seule chose qu'un résultat négatif ait besoin "
               "de publier. La surface n'est pas plafonnée : un plafond "
               "ferait un plateau d'ex aequo au sommet, et le dépôt a payé "
               "cette leçon deux fois avant d'en faire une habitude.")
    return b.render("Relief de la part du seuil atteinte, en nombre de "
                    "seances et en taille d effet.")


# ---------------------------------------------------------------------------
# IV. Les régimes de collage
# ---------------------------------------------------------------------------


def fig_sk_regimes() -> str:
    """Le même strike, trois régimes, trois deltas."""
    b = _plate(500, "Skew · les trois régimes",
               "Le même call, trois hypothèses, trois couvertures",
               "trente jours")

    t = _t(30.0)
    spots = [88.0 + 0.28 * i for i in range(101)]
    k = K.strike_de_moneyness(0.0, t)

    p1 = Panel(b, PX1, 92, PW, 214,
               title="Le delta du même strike",
               readout="delta du call")
    courbes = []
    for cls, dash, r in (("hm7", "", K.REGIMES[0]),
                         ("hm5", "6 3", K.REGIMES[1]),
                         ("hm3", "2 3", K.REGIMES[2])):
        courbes.append((cls, dash, r.nom,
                        [(s, K.delta_du_regime(r, k, t, s=s))
                         for s in spots]))
    hi = max(y for _, _, _, c in courbes for _, y in c)
    lo = min(y for _, _, _, c in courbes for _, y in c)
    p1.domain(spots[0], spots[-1], lo * 0.92, hi * 1.06)
    p1.frame()
    p1.grid_y(_ticks(lo * 0.92, hi * 1.06, 0.2), lambda v: _num(v, 1),
              dx=24.0)
    p1.grid_x([90, 95, 100, 105, 110], lambda v: _num(v, 0),
              label="comptant")
    for cls, dash, nom, c in courbes:
        p1.path(c, cls, dash=dash, tip=nom)
    p1.label(spots[0], hi * 1.02, "trois hypothèses, un seul strike",
             dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="L'étendue des trois, par moneyness",
               readout="points de delta")
    ms = [-0.14 + 0.0028 * i for i in range(101)]
    ec = [(m, K.ecart_des_regimes(K.strike_de_moneyness(m, t), t))
          for m in ms]
    hi2 = max(y for _, y in ec) * 1.18
    p2.domain(ms[0], ms[-1], 0.0, hi2)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2, 2.0), lambda v: _num(v, 0), dx=22.0)
    p2.grid_x([-0.10, -0.05, 0.0, 0.05, 0.10], lambda v: _num(v, 2),
              label="logarithme de moneyness")
    p2.path(ec, "hm6", tip="étendue des trois deltas")
    p2.dot(-0.05, K.ecart_des_regimes(K.strike_de_moneyness(-0.05, t), t),
           "hm6", "cinq pour cent sous la monnaie", r=4.5)
    p2.label(-0.05, K.ecart_des_regimes(K.strike_de_moneyness(-0.05, t), t),
             _num(K.ecart_des_regimes(K.strike_de_moneyness(-0.05, t), t), 1)
             + " points de delta", dx=10, dy=-9)

    b.legend(0.0, 352.0,
             [("hm7", "sticky delta"), ("hm5", "sticky strike", "6 3"),
              ("hm3", "sticky local vol", "2 3")],
             step=200.0, kind="line")
    b.annotation(0.0, 376.0,
                 "la correction porte le véga et non le vanna : la partie "
                 "XXIV a montré que la formule usuelle nomme le mauvais grec")
    b.annotation(0.0, 392.0,
                 "le guide dit plusieurs deltas sur chaque strike, et la "
                 "mesure le confirme sur toute la plage")
    b.annotation(0.0, 408.0,
                 "une option seule coûte "
                 + _num(K.cout_en_frictions(
                     K.strike_de_moneyness(-0.05, t), t), 3)
                 + " friction ; il en faut "
                 + _num(K.options_pour_une_friction(
                     K.strike_de_moneyness(-0.05, t), t), 0) + " pour une")

    _source(b, "Le guide pose la bonne question — quand le comptant bouge, "
               "le sourire bouge-t-il avec lui ? — et donne les trois "
               "réponses standard. Le cadre de gauche montre les trois "
               "deltas d'un même strike sous les trois hypothèses ; le "
               "cadre de droite leur étendue, en points de delta, par "
               "moneyness. La correction porte le véga et non le vanna, "
               "et ce n'est pas une question de notation : la partie XXIV "
               "a établi que la formule usuelle nomme le mauvais grec et se "
               "trompe d'un facteur. Le résultat en est importé plutôt que "
               "recopié.")
    return b.render("Le delta d un meme strike sous les trois regimes de "
                    "collage, et l etendue des trois.")


def fig_sk_cout() -> str:
    """Ce que coûte une erreur de régime, en friction."""
    b = _plate(490, "Skew · le coût",
               "Plusieurs deltas, convertis en ce que l'opérateur paie",
               "par séance")

    t = _t(30.0)
    ms = [-0.14 + 0.0028 * i for i in range(101)]

    p1 = Panel(b, PX1, 92, PW, 214,
               title="Le coût d'une seule option",
               readout="en frictions déclarées")
    c = [(m, K.cout_en_frictions(K.strike_de_moneyness(m, t), t))
         for m in ms]
    hi = max(y for _, y in c) * 1.20
    p1.domain(ms[0], ms[-1], 0.0, hi)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi, 0.01), lambda v: _num(v, 2), dx=26.0)
    p1.grid_x([-0.10, -0.05, 0.0, 0.05, 0.10], lambda v: _num(v, 2),
              label="logarithme de moneyness")
    p1.path(c, "hm7", tip="coût en frictions, par option")
    p1.label(ms[0], hi * 0.92, "quelques centièmes de friction", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Le livre qu'il faut pour en coûter une",
               readout="options sur le même strike")
    c2 = [(m, K.options_pour_une_friction(K.strike_de_moneyness(m, t), t))
          for m in ms]
    hi2 = max(y for _, y in c2) * 1.18
    p2.domain(ms[0], ms[-1], 0.0, hi2)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2, 50.0), lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([-0.10, -0.05, 0.0, 0.05, 0.10], lambda v: _num(v, 2),
              label="logarithme de moneyness")
    p2.path(c2, "hm5", tip="options pour une friction")
    k5 = K.strike_de_moneyness(-0.05, t)
    p2.dot(-0.05, K.options_pour_une_friction(k5, t), "hm5",
           "cinq pour cent sous la monnaie", r=4.5)
    p2.label(-0.05, K.options_pour_une_friction(k5, t),
             _num(K.options_pour_une_friction(k5, t), 0) + " contrats",
             dx=10, dy=-9)

    b.legend(0.0, 352.0,
             [("hm7", "le coût d'une option"),
              ("hm5", "le livre qui en coûte une")],
             step=240.0, kind="line")
    b.annotation(0.0, 376.0,
                 "l'erreur de delta multipliée par le déplacement moyen "
                 "absolu d'une séance, racine de deux sur pi fois sigma")
    b.annotation(0.0, 392.0,
                 "c'est la constante de la partie XXV, importée et non "
                 "recopiée, et elle rend le coût comparable à la friction")
    b.annotation(0.0, 408.0,
                 "une option seule coûte quelques centièmes : c'est le mot "
                 "« simultanément » du guide qui porte tout le sens")

    _source(b, "Le guide écrit que choisir le mauvais régime ne produit pas "
               "une petite erreur mais plusieurs deltas sur chaque strike "
               "simultanément. C'est exact, et le convertir est ce qui "
               "permet de le comparer à quelque chose. L'erreur de delta "
               "multipliée par le déplacement moyen absolu d'une séance "
               "donne un coût en points d'indice, puis en frictions "
               "déclarées. Une affirmation écrite d'avance ici disait que "
               "ce coût dépassait la friction ; la mesure l'a réfutée — "
               "une option seule en coûte quelques centièmes. Ce qui rend "
               "la remarque du guide juste est le mot simultanément : un "
               "pupitre ne tient pas une option, et le cadre de droite "
               "chiffre la taille de livre au-delà de laquelle l'erreur de "
               "régime coûte plus qu'un aller-retour complet par séance. "
               "Elle est modeste.")
    return b.render("Le cout d une erreur de regime en frictions declarees, "
                    "par moneyness et par echeance.")


def fig_sk_relief_regimes() -> str:
    """Le relief de l'étendue des trois régimes."""
    z = [list(l) for l in K.surface_regimes()]
    vals = [v for l in z for v in l]

    b = _plate(486, "Skew · le relief des régimes",
               "L'écart des trois hypothèses, sur tout le tableau",
               "hauteur : points de delta")

    _surface(b, 0.52 * W, 232.0, z, min(vals), max(vals), cx=42.0, cy=13.0,
             cz=158.0,
             row_labels=[_num(j, 0) + " j" for j in K.SURF_JOURS_INVERSE],
             col_labels=[_num(m, 2) for m in K.SURF_MONEYNESS],
             z_ticks=[(t, _num(t, 1)) for t in _echine(min(vals), max(vals))],
             tip="{v:.2f}", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : l'échéance · arête droite : le logarithme "
                 "de moneyness · hauteur : l'étendue des trois deltas")
    b.annotation(0.0, 424.0,
                 "l'arête de la monnaie est plate : le véga croît en "
                 "racine de T exactement autant que la pente décroît")
    b.annotation(0.0, 440.0,
                 "ce qui monte avec l'échéance est l'aile, qui rattrape "
                 "son retard : de "
                 + _num(K.ecart_des_regimes(
                     K.strike_de_moneyness(-0.06, _t(7.0)), _t(7.0)), 2)
                 + " à " + _num(K.ecart_des_regimes(
                     K.strike_de_moneyness(-0.06, 1.0), 1.0), 2) + " points")

    _source(b, "La hauteur est l'écart entre le delta le plus grand et le "
               "plus petit des trois régimes, en points de delta. Une "
               "affirmation écrite d'avance disait que le sommet était aux "
               "échéances longues, où le véga est le plus grand ; la mesure "
               "l'a réfutée. L'arête de la monnaie est plate, et le "
               "mécanisme est celui de toute la partie : le véga croît en "
               "racine du temps exactement autant que la pente locale "
               "décroît, donc leur produit ne dépend pas de l'échéance. Ce "
               "qui monte est l'aile, qui rattrape son retard. Une erreur "
               "de régime à la monnaie coûte le même nombre de points de "
               "delta sur une hebdomadaire et sur une annuelle.")
    return b.render("Relief de l etendue des trois deltas, en echeance et "
                    "en moneyness.")


# ---------------------------------------------------------------------------
# V. La position, les forces, le décompte
# ---------------------------------------------------------------------------


def fig_sk_position() -> str:
    """Ce qu'un risk reversal porte réellement."""
    b = _plate(500, "Skew · la position",
               "L'objet par lequel on négocie la forme est directionnel",
               "acheter le call 25Δ, vendre le put")

    # L'axe est le **delta de la convention** et non l'échéance : contre
    # l'échéance les deux quantités sont des horizontales, et une planche
    # de deux horizontales ne montre rien. Contre le delta, l'identité
    # `net = 2δ` se lit — et c'est elle, le fait de la section.
    ds = [0.03 + 0.0045 * i for i in range(100)]
    t = _t(30.0)

    p1 = Panel(b, PX1, 92, PW, 214,
               title="Delta net et véga net",
               readout="delta, et véga par point")
    dn = [(d, K.risk_reversal_position(t, delta=d).delta_net) for d in ds]
    vn = [(d, K.risk_reversal_position(t, delta=d).vega_net) for d in ds]
    ferme = [(d, K.delta_net_ferme(d)) for d in ds]
    p1.domain(ds[0], ds[-1], -0.08, 1.02)
    p1.frame()
    p1.grid_y([0.0, 0.25, 0.50, 0.75, 1.00], lambda v: _num(v, 2), dx=26.0)
    p1.grid_x([0.05, 0.15, 0.25, 0.35, 0.45], lambda v: _num(100.0 * v, 0),
              label="delta de la convention")
    p1.hline(0.0, "lvl")
    p1.path(vn, "hm3", dash="5 4", tip="véga net")
    p1.path(dn, "hm4", tip="delta net, mesuré")
    p1.path(ferme, "hm1", dash="2 3", tip="deux fois le delta")
    p1.dot(0.25, K.delta_net_ferme(0.25), "hm4", "la convention de pupitre",
           r=4.5)
    p1.label(0.25, K.delta_net_ferme(0.25), "à 25Δ : "
             + _num(K.delta_net_ferme(0.25), 2), dx=10, dy=12)
    p1.label(ds[-1], -0.05, "le véga net est nul par parité", dx=-8, dy=0,
             anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214,
               title="La dérive qu'elle demande",
               readout="points par heure")
    mu = [(d, K.risk_reversal_position(t, delta=d).seuil_derive)
          for d in ds]
    from . import seuil as SE
    plancher = SE.PLAUSIBLE_DRIFT_PER_HOUR[0]
    hi = max(max(y for _, y in mu), plancher) * 1.22
    p2.domain(ds[0], ds[-1], 0.0, hi)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi, 0.2), lambda v: _num(v, 1), dx=24.0)
    p2.grid_x([0.05, 0.15, 0.25, 0.35, 0.45], lambda v: _num(100.0 * v, 0),
              label="delta de la convention")
    p2.hline(plancher, "lvl")
    p2.path(mu, "hm6", tip="dérive requise")
    p2.dot(0.25, K.risk_reversal_position(t).seuil_derive, "hm6",
           "la convention de pupitre", r=4.5)
    p2.label(ds[0], plancher, "le plancher du domaine plausible : "
             + _num(plancher, 1), dx=8, dy=-9)
    p2.label(0.25, K.risk_reversal_position(t).seuil_derive,
             _num(K.risk_reversal_position(t).seuil_derive, 2) + " pt/h",
             dx=10, dy=-10)

    b.legend(0.0, 352.0,
             [("hm4", "delta net, mesuré"),
              ("hm1", "deux fois le delta", "2 3"),
              ("hm3", "véga net", "5 4"),
              ("hm6", "la dérive requise, à droite")],
             step=140.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le véga ne dépend de son argument que par une fonction "
                 "paire, et les deux strikes ont des arguments opposés")
    b.annotation(0.0, 392.0,
                 "le delta net vaut exactement deux fois le delta de la "
                 "convention, sans dépendre de la peau ni de l'échéance")
    b.annotation(0.0, 408.0,
                 "son seuil de rentabilité tombe sous le plancher du "
                 "domaine plausible : ce n'est pas une bonne nouvelle")

    _source(b, "C'est l'objet par lequel un pupitre négocie « le skew » : "
               "acheter le call à vingt-cinq deltas, vendre le put du même "
               "delta. Son véga net est nul par une parité que la partie "
               "XXIV a établie — le véga ne dépend de son argument que par "
               "une fonction paire, et les deux strikes ont des arguments "
               "opposés — donc la position ne porte rien de ce qu'elle "
               "prétend négocier au premier ordre. Ce qu'elle porte est un "
               "delta net qui vaut exactement deux fois le delta de sa "
               "convention, sans aucune dépendance à la peau, à l'échéance "
               "ni à la volatilité : le pointillé sombre est cette "
               "identité, et la mesure tombe dessus. Son seuil de "
               "rentabilité passe sous le plancher du domaine plausible "
               "parce que la position n'a aucune barrière et achète la "
               "séance entière. Ce n'est pas une bonne nouvelle : c'est un "
               "avertissement.")
    return b.render("Le delta net, le vega net et la derive requise d un "
                    "risk reversal, contre l echeance.")


def fig_sk_forces() -> str:
    """Les trois forces, et ce que chacune coûte à établir."""
    b = _plate(500, "Skew · les trois forces",
               "Le seul guide des onze à donner une conséquence testable",
               "séances requises")

    fs = sorted(K.forces(), key=lambda x: x.seances)
    n = len(fs)

    p1 = Panel(b, PX1, 92, PW, 214,
               title="Ce que chaque force coûte",
               readout="échelle logarithmique")
    haut = max(f.seances for f in fs) * 3.0
    p1.domain(15.0, haut, -0.6, n - 0.4, xlog=True)
    p1.frame()
    p1.grid_x([100.0, 1000.0, 10000.0], _dec)
    p1.vline(K.SEANCES_AN, "lvl")
    for i, f in enumerate(fs):
        y = n - 1 - i
        v = max(f.seances, K.SEANCES_MINIMALES)
        p1.hbar(y, 15.0, v, 13.0, "hm7",
                tip=f.nom + " : " + _num(v, 0) + " séances")
        p1.label(15.0, y + 0.34, f.nom, dx=4, dy=0)
        p1.label(v, y, _num(v / K.SEANCES_AN, 1) + " an"
                 + ("s" if v / K.SEANCES_AN >= 2.0 else ""), dx=-8, dy=4,
                 anchor="end")
    p1.label(K.SEANCES_AN, -0.44, "une année", dx=6, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Le budget contre la taille d'effet",
               readout="échelle logarithmique")
    rhos = [0.01 + 0.005 * i for i in range(140)]
    c = [(r, K.seances_pour_correlation(r)) for r in rhos]
    p2.domain(rhos[0], rhos[-1], 20.0, 60000.0, ylog=True)
    p2.frame()
    p2.grid_y([100.0, 1000.0, 10000.0], _dec, dx=28.0)
    p2.grid_x([0.2, 0.4, 0.6], lambda v: _num(v, 1),
              label="corrélation à établir")
    p2.hline(K.SEANCES_MINIMALES, "lvl")
    p2.path(c, "hm5", tip="séances requises")
    for f in fs:
        if "corrélation" in f.unite:
            p2.dot(abs(f.effet), max(f.seances, K.SEANCES_MINIMALES), "hm5",
                   f.nom, r=4.5)
    p2.label(rhos[-1], K.SEANCES_MINIMALES * 1.9,
             "sous ce plancher, l'approximation ne vaut plus", dx=-8, dy=0,
             anchor="end")

    b.legend(0.0, 352.0,
             [("hm7", "les trois forces"),
              ("hm5", "le budget d'une corrélation, à droite")],
             step=240.0)
    b.annotation(0.0, 376.0,
                 "ce onzième guide donne pour chaque mécanisme une "
                 "conséquence testable, et c'est le seul des onze")
    b.annotation(0.0, 392.0,
                 "le dépôt n'a pas de données de marché : il chiffre ce que "
                 "chacune coûterait, ce qui suffit à les classer")
    b.annotation(0.0, 408.0,
                 "un facteur " + _num(K.rapport_des_budgets(), 0)
                 + " entre les deux bouts, et l'argument économique du "
                 "skew est au bout le plus cher")

    _source(b, "Le guide fait ce qu'aucun des dix précédents n'avait fait : "
               "il donne, pour chaque mécanisme, une conséquence testable. "
               "Le dépôt n'a aucune donnée de marché et ne peut en tester "
               "aucune ; il peut chiffrer ce qu'elles coûteraient, et le "
               "classement est un renversement. Le levier se voit en "
               "quelques semaines parce que son effet est énorme — si "
               "énorme que ce n'est plus l'information qui borne mais la "
               "validité de l'approximation. La prime de risque de crash, "
               "sur laquelle repose tout l'argument économique du skew, "
               "demande trente ans. Les tailles d'effet sont déclarées et "
               "non ajustées : le dépôt n'ajuste rien qu'il ne mesure.")
    return b.render("Le budget d information des trois forces, et celui "
                    "d une correlation contre sa taille.")


def fig_sk_reste() -> str:
    """Le décompte, et le cumul des onze parties d'options."""
    b = _plate(530, "Skew · le décompte",
               "Onze documents, et le troisième qui teste ce qu'il vend",
               "onze parties d'options")

    grandeurs = ("la direction", "l'horloge", "le risque", "rien")
    compte = K.compte_par_grandeur()
    n = len(grandeurs)
    p1 = Panel(b, PX1, 92, PW, 274, title="Ce qu'elles déplacent",
               readout="affirmations")
    haut = max(4.0, max(compte.values()) + 1.0)
    p1.domain(0.0, haut, -0.6, n - 0.4)
    p1.frame()
    p1.grid_x(_ticks(0.0, haut, 1.0), lambda v: _num(v, 0))
    for i, g in enumerate(grandeurs):
        y = n - 1 - i
        v = compte.get(g, 0)
        p1.hbar(y, 0.0, v, 13.0,
                "hm1" if g == "la direction" else "hm7", tip=g)
        p1.label(0.0, y + 0.34, g, dx=4, dy=0)
        p1.label(v, y, _num(v, 0), dx=7, dy=4)
    p1.label(haut, n - 1.0, "la direction reste vide", dx=-8, dy=4,
             anchor="end")

    fam = K.familles()
    m = len(fam)
    p2 = Panel(b, PX2, 92, PW, 274, title="Le cumul des onze parties",
               readout="affirmations examinées")
    hautf = max(v for _, v in fam) * 1.45
    p2.domain(0.0, hautf, -0.6, m - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, hautf, 3.0), lambda v: _num(v, 0))
    for i, (nom, v) in enumerate(fam):
        y = m - 1 - i
        p2.hbar(y, 0.0, v, 6.0, "hm5", tip=nom + " : " + _num(v, 0))
        p2.label(0.0, y + 0.38, nom, dx=4, dy=0)
        p2.label(v, y, _num(v, 0), dx=7, dy=4)

    b.legend(0.0, 412.0,
             [("hm7", "ce qu'elles déplacent"),
              ("hm1", "la direction, vide"),
              ("hm5", "par partie, à droite")],
             step=200.0)
    b.annotation(0.0, 436.0,
                 "sur les " + _num(sum(v for _, v in fam), 0)
                 + " affirmations des onze parties d'options, aucune ne "
                 "donne un sens")
    b.annotation(0.0, 452.0,
                 "c'est le troisième des onze à publier son propre résultat "
                 "négatif, et le seul à dire pourquoi il ne condamne rien")
    b.annotation(0.0, 468.0,
                 "le skew est un prix, pas une prévision, et le vendre "
                 "comme une prévision est une erreur de catégorie")

    _source(b, "La colonne de la direction est vide pour la huitième "
               "partie consécutive. Ce onzième guide est le troisième à "
               "publier le résultat de son propre test négatif, après ceux "
               "du vanna et de l'implicite, et il est le seul des trois à "
               "expliquer pourquoi ce résultat ne condamne pas l'objet : le "
               "skew décrit le prix de la protection de queue maintenant, "
               "et ce n'est pas une prévision de direction ni d'amplitude. "
               "C'est la thèse de la quatrième partie de ce document, "
               "formulée sur un onzième objet par un praticien qui n'avait "
               "aucune raison de la formuler.")
    return b.render("Le decompte des affirmations par ce qu elles "
                    "deplacent, et le cumul des onze parties d options.")


# ---------------------------------------------------------------------------
# Le catalogue
# ---------------------------------------------------------------------------


def render_all() -> dict[str, str]:
    return {
        "skforme": fig_sk_forme(),
        "skconventions": fig_sk_conventions(),
        "skvol": fig_sk_vol(),
        "skreliefra": fig_sk_relief_rapport(),
        "skexposant": fig_sk_exposant(),
        "sktenor": fig_sk_tenor(),
        "skreliefex": fig_sk_relief_exposant(),
        "sklois": fig_sk_loi_nulle(),
        "skpuissance": fig_sk_puissance(),
        "skreliefpu": fig_sk_relief_puissance(),
        "skregimes": fig_sk_regimes(),
        "skcout": fig_sk_cout(),
        "skreliefre": fig_sk_relief_regimes(),
        "skposition": fig_sk_position(),
        "skforces": fig_sk_forces(),
        "skreste": fig_sk_reste(),
    }
