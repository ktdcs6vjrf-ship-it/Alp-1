"""Les planches de « le taux, et la variable qu'on tient fixe ».

Quinze planches, onze à plat et quatre en relief. Aucune ne montre un signal :
elles montrent une sensibilité exacte, et ce qu'il faut lui adjoindre pour
qu'elle devienne un risque.

Comme `figgra`, `figth` et `figvg`, ce module importe ses fonctions d'échine,
de graduation et de décade de `fignv` plutôt que de les recopier : une
quatrième copie serait une quatrième occasion de les faire diverger.
"""

from __future__ import annotations

import math

from . import rho as R
from . import theta as th
from . import vega as vg
from .figdisc import W, _plate, _source, _surface
from .fignv import _dec, _echine, _pct, _ticks
from .figterm import Board, Panel, _num, _signed


PW = (W - 74.0) / 2.0 - 30.0
PX1 = 74.0
PX2 = 74.0 + (W - 74.0) / 2.0

S = R.S_REF
V = R.VOL_REF
AN = R.JOURS_AN


def _rp(j: float, r: float = R.TAUX) -> float:
    return R.rho_par_point(S, S, V, j / AN, r, R.DIVIDENDE)


# ---------------------------------------------------------------------------
# I. L'échelle et la proportionnalité
# ---------------------------------------------------------------------------


def fig_rh_echelle() -> str:
    """Rho contre l'échéance, et l'exposant qui s'use.

    Les deux cadres portent deux grandeurs différentes ; leurs teintes sont
    donc choisies pour ne pas se répondre, et chaque tracé est nommé sur
    place.
    """
    b = _plate(500, "Rho · l'échelle",
               "La proportionnalité au temps, et là où elle s'use",
               _num(100 * V, 0) + " % de volatilité, "
               + _num(100 * R.TAUX, 1) + " % de taux")

    js = [7.0 + 6.0 * i for i in range(200)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Le rho d'un call et d'un put",
               readout="par point de taux")
    call = [(j, _rp(j)) for j in js]
    put = [(j, R.rho_put(S, S, V, j / AN) / 100.0) for j in js]
    ylo = min(y for _, y in put) * 1.25
    yhi = max(y for _, y in call) * 1.25
    p1.domain(0.0, js[-1], ylo, yhi)
    p1.frame()
    p1.grid_y(_ticks(ylo, yhi, 0.5), lambda v: _signed(v, 1), dx=26.0)
    p1.grid_x([0, 300, 600, 900, 1200], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.hline(0.0, "lvl")
    p1.path(call, "hm6", tip="call")
    p1.path(put, "hm2", dash="5 4", tip="put")
    p1.label(js[-1], _rp(js[-1]), "le call gagne", dx=-6, dy=-8, anchor="end")
    p1.label(js[-1], R.rho_put(S, S, V, js[-1] / AN) / 100.0,
             "le put perd", dx=-6, dy=14, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="L'exposant local",
               readout="d ln rho / d ln T")
    mesure = [(j, R.exposant_effectif(j)) for j in js]
    e_lo = min(y for _, y in mesure)
    p2.domain(0.0, js[-1], min(0.80, e_lo - 0.04), 1.06)
    p2.frame()
    p2.grid_y(_ticks(0.80, 1.06, 0.05), lambda v: _num(v, 2), dx=26.0)
    p2.grid_x([0, 300, 600, 900, 1200], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.hline(1.0, "lvl")
    p2.path(mesure, "hm4", tip="exposant")
    p2.dot(365.0, R.exposant_effectif(365.0), "hm4", "un an", r=4.2)
    p2.dot(730.0, R.exposant_effectif(730.0), "hm4", "deux ans", r=4.2)
    p2.label(0.0, 1.0, "la proportionnalité stricte", dx=6, dy=-6)
    p2.label(730.0, R.exposant_effectif(730.0),
             _num(R.exposant_effectif(730.0), 2) + " à deux ans",
             dx=-8, dy=14, anchor="end")

    b.legend(0.0, 352.0,
             [("hm6", "le call, à gauche"),
              ("hm2", "le put, à gauche", "5 4"),
              ("hm4", "l'exposant, à droite")],
             step=200.0)
    b.annotation(0.0, 376.0,
                 "le guide écrit que rho est proportionnel au temps, quand "
                 "le véga l'est à sa racine")
    b.annotation(0.0, 392.0,
                 "l'exposant vaut un jusqu'à trois mois, "
                 + _num(R.exposant_effectif(365.0), 2) + " à un an et "
                 + _num(R.exposant_effectif(730.0), 2) + " à deux ans")
    b.annotation(0.0, 408.0,
                 "la règle est excellente là où le guide dit qu'elle sert, "
                 "et elle s'use là où il dit de regarder")

    _source(b, "Trois facteurs se composent dans le rho — le strike "
               "actualisé, le temps qui croît, la probabilité d exercice qui "
               "dérive. Leur produit n'est proportionnel au "
               "temps qu'aux échéances courtes, et l'exposant local le dit "
               "sans qu'on ait à en juger. Le cadre de gauche rappelle le "
               "mécanisme par le signe : un call diffère un paiement et "
               "gagne à la hausse des taux, un put diffère une recette et y "
               "perd. Les deux courbes ne sont pas symétriques, le report "
               "sur dividende les décalant.")
    return b.render("Le rho d un call et d un put contre l echeance, et "
                    "l exposant local de la proportionnalite au temps.")


def fig_rh_pic() -> str:
    """Le maximum de rho, et son lieu en `1/r`."""
    b = _plate(500, "Rho · le maximum",
               "La proportionnalité ne s'use pas seulement, elle se retourne",
               "jusqu'à cinquante ans")

    js = [30.0 + 120.0 * i for i in range(160)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Rho sur une échelle longue",
               readout="par point de taux")
    mesure = [(j / AN, _rp(j)) for j in js]
    ref = _rp(30.0) / (30.0 / AN)
    yhi = max(y for _, y in mesure) * 1.35
    # La droite du mois quitte le cadre bien avant la fin de l axe : on
    # l arrete au bord plutot que de la laisser au decoupage, qui en ferait
    # un trace reduit a quelques points.
    droite = [(j / AN, ref * j / AN) for j in js if ref * j / AN <= yhi]
    p1.domain(0.0, js[-1] / AN, 0.0, yhi)
    p1.frame()
    p1.grid_y(_ticks(0.0, yhi, 1.0), lambda v: _num(v, 0), dx=22.0)
    p1.grid_x([0, 10, 20, 30, 40, 50], lambda v: _num(v, 0),
              label="années à l'échéance")
    p1.path(droite, "hm0", dash="2 3", tip="la proportionnalité")
    p1.path(mesure, "hm6", tip="la mesure")
    pic = R.echeance_du_pic()
    p1.dot(pic, _rp(pic * AN), "hm6", "le maximum", r=4.5)
    p1.vline(pic, "lvl")
    p1.label(pic, yhi * 0.90, _num(pic, 0) + " ans", dx=6, dy=0)
    p1.label(0.0, yhi * 0.60, "pointillé : la droite du mois", dx=6, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Le lieu du maximum",
               readout="années")
    taux = [0.005 + 0.0015 * i for i in range(51)]
    lieu = [(100 * r, R.echeance_du_pic(S, S, V, r, R.DIVIDENDE))
            for r in taux]
    inv = [(100 * r, 1.0 / r) for r in taux]
    yhi2 = max(y for _, y in inv) * 1.10
    p2.domain(0.0, 100 * taux[-1], 0.0, yhi2)
    p2.frame()
    p2.grid_y(_ticks(0.0, yhi2, 50.0), lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([0, 2, 4, 6, 8], lambda v: _num(v, 0), label="taux (%)")
    p2.path(inv, "hm0", dash="2 3", tip="un sur r")
    p2.path(lieu, "hm3", tip="mesuré")
    rstar = R.taux_du_pic_exact()
    p2.dot(100 * rstar, 1.0 / rstar, "hm3", "le seul point d accord", r=4.5)
    p2.vline(100 * rstar, "lvl")
    p2.label(100 * rstar, yhi2 * 0.88, _pct(rstar, 2), dx=7, dy=0)
    p2.label(1.0, 1.0 / 0.01, "un sur r", dx=8, dy=-6)
    p2.label(1.0, R.echeance_du_pic(S, S, V, 0.01, R.DIVIDENDE),
             "mesuré", dx=8, dy=14)

    b.annotation(0.0, 352.0,
                 "rho croît, puis décroît : l'escompte finit par l'emporter "
                 "sur le temps")
    b.annotation(0.0, 368.0,
                 "le maximum tombe à " + _num(pic, 1) + " ans au taux "
                 "déclaré, et il n'égale l'inverse du taux qu'en un point")
    b.annotation(0.0, 384.0,
                 "ce point se calcule : le taux vaut alors le rendement plus "
                 "la moitié de la variance, soit "
                 + _pct(R.taux_du_pic_exact(), 2))
    b.annotation(0.0, 400.0,
                 "la droite du mois s'écarte de cinq pour cent dès "
                 + _num(R.echeance_de_l_ecart(0.05), 0) + " jours")

    _source(b, "Une proportionnalité qui se retourne n'est plus une "
               "approximation, c'est une autre forme. Le cadre de gauche "
               "pose la droite calée sur le mois — l'échéance où la règle "
               "est vraie — et la mesure s'en détache lentement puis "
               "franchement. Le cadre de droite enterre un piège que la "
               "première version de ce module avait publié : le lieu du "
               "maximum n'est pas l'inverse du taux. Les deux courbes ne se "
               "touchent qu'en un point, et ce point se calcule — le taux y "
               "vaut le rendement du sous-jacent plus la moitié de sa "
               "variance, c est-à-dire le taux auquel une option à la "
               "monnaie a la même chance d être exercée à toute échéance. "
               "Au-dessous, la probabilité d exercice décroît et le maximum "
               "vient plus tôt ; au-dessus, elle croît et il vient plus "
               "tard. Le maximum existe encore à taux nul, à quarante-cinq "
               "ans, et rien de ce que le guide écrit ne le laisse "
               "prévoir.")
    return b.render("Le maximum de rho contre l echeance, et son lieu "
                    "contre le niveau du taux.")


def fig_rh_deux() -> str:
    """Les deux nombres publiés, et le rapport qu'on en tire."""
    court = _rp(R.JOURS_COURT)
    long_ = _rp(R.JOURS_LONG)
    mesure = long_ / court

    b = _plate(470, "Rho · les deux nombres",
               "Deux mesures justes, et une comparaison fausse entre elles",
               "par point de taux")

    p1 = Panel(b, PX1, 92, PW, 214, title="Ce que le guide publie",
               readout="points d'indice")
    p1.domain(-0.6, 1.6, 0.0, long_ * 1.30)
    p1.frame()
    p1.grid_y(_ticks(0.0, long_ * 1.30, 0.2), lambda v: _num(v, 1), dx=30.0)
    p1.vbar(0.0, 0.0, court, 62.0, "hm2", tip="un mois")
    p1.vbar(1.0, 0.0, long_, 62.0, "hm6", tip="deux ans")
    p1.label(0.0, court, _num(court, 4), dx=0, dy=-8, anchor="middle")
    p1.label(1.0, long_, _num(long_, 4), dx=0, dy=-8, anchor="middle")
    p1.label(0.0, 0.0, "un mois", dx=0, dy=16, anchor="middle")
    p1.label(1.0, 0.0, "deux ans", dx=0, dy=16, anchor="middle")

    p2 = Panel(b, PX2, 92, PW, 214, title="Le rapport des deux",
               readout="facteur")
    p2.domain(-0.6, 1.6, 0.0, R.RAPPORT_ANNONCE * 1.30)
    p2.frame()
    p2.grid_y(_ticks(0.0, R.RAPPORT_ANNONCE * 1.30, 25.0),
              lambda v: _num(v, 0), dx=26.0)
    p2.vbar(0.0, 0.0, mesure, 62.0, "hm4", tip="mesuré")
    p2.vbar(1.0, 0.0, R.RAPPORT_ANNONCE, 62.0, "hm7", tip="annoncé")
    p2.label(0.0, mesure, _num(mesure, 1), dx=0, dy=-8, anchor="middle")
    p2.label(1.0, R.RAPPORT_ANNONCE, _num(R.RAPPORT_ANNONCE, 0), dx=0,
             dy=-8, anchor="middle")
    p2.label(0.0, 0.0, "mesuré", dx=0, dy=16, anchor="middle")
    p2.label(1.0, 0.0, "annoncé", dx=0, dy=16, anchor="middle")
    p2.hline(mesure, "lvl")

    b.annotation(0.0, 352.0,
                 "les deux nombres du guide sont exacts : quatre centimes à "
                 "un mois, un dollar à deux ans")
    b.annotation(0.0, 368.0,
                 "leur rapport vaut " + _num(mesure, 1) + " et non cent — un "
                 "facteur " + _num(R.RAPPORT_ANNONCE / mesure, 1)
                 + " sur la conclusion")
    b.annotation(0.0, 384.0,
                 "c'est le mode de défaillance le plus discret de la série, "
                 "et ce dépôt y est tombé aussi")

    _source(b, "Deux mesures justes ne font pas une comparaison juste. Les "
               "barres de gauche portent exactement ce que le guide publie ; "
               "celles de droite comparent le rapport que l'on en tire à "
               "celui qu'il annonce. Un ordre de grandeur sépare les deux, "
               "et rien dans le texte ne le signale, parce qu'une phrase "
               "comme « deux ordres de grandeur » ne se vérifie qu'en la "
               "calculant. La partie XXI de ce document a publié un décompte "
               "annoncé cinq qui valait quatre, et il a fallu regarder la "
               "planche pour le voir.")
    return b.render("Les deux rhos publies par le guide, et le rapport "
                    "mesure contre le rapport annonce.")


def fig_rh_relief_usure() -> str:
    """Le relief de l'usure de la proportionnalité."""
    z = [list(l) for l in R.surface_usure()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Rho · le relief de l'usure",
               "Où la proportionnalité au temps cesse d'être vraie",
               "hauteur : un moins l'exposant")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_pct(r, 0) for r in R.SURF_TAUX],
             col_labels=[_num(j / AN, 1) for j in R.SURF_ECHEANCE_USURE],
             z_ticks=[(t, _num(t, 2)) for t in _echine(zlo, zhi)],
             tip="{v:+.3f} d ecart a un", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : le taux · arête droite : l'échéance en "
                 "années · hauteur : l'usure de la règle")
    b.annotation(0.0, 424.0,
                 "le sol est le domaine où la règle du guide est exacte : "
                 "toute la bordure des échéances courtes")
    b.annotation(0.0, 440.0,
                 "le relief ne monte que dans un coin, et c'est celui que le "
                 "guide dit d'aller regarder")

    _source(b, "La hauteur porte un moins l exposant local, c'est-à-dire ce qui "
               "manque à la proportionnalité stricte. Le relief est plat sur "
               "presque toute son étendue : la règle du guide est bonne, et "
               "la surface le dit mieux qu'une phrase. Il ne monte qu'au "
               "coin des taux élevés et des échéances longues, où l'escompte "
               "prend le pas sur le temps ; l'usure y dépasse les trois "
               "quarts, c'est-à-dire que rho croît quatre fois moins vite "
               "que le temps. Une frange du relief passe légèrement sous "
               "zéro aux échéances courtes et aux taux hauts, où rho croît "
               "un peu plus vite que le temps : c'est la dérive de la "
               "probabilité d'exercice, et elle est du signe opposé.")
    return b.render("Relief de l usure de la proportionnalite au temps, en "
                    "taux et en echeance.")


# ---------------------------------------------------------------------------
# II. Le croisement avec le véga
# ---------------------------------------------------------------------------


def fig_rh_croisement() -> str:
    """Les deux sensibilités, sans unité puis pondérées."""
    b = _plate(510, "Rho · le croisement",
               "La même question posée deux fois, et deux réponses opposées",
               "rho contre véga")

    js = [7.0 + 12.0 * i for i in range(150)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Unité contre unité",
               readout="par point")
    cr = [(j, _rp(j)) for j in js]
    cv = [(j, vg.vega_par_point(S, S, V, j / AN, R.TAUX, R.DIVIDENDE))
          for j in js]
    yhi = max(max(y for _, y in cr), max(y for _, y in cv)) * 1.30
    p1.domain(0.0, js[-1], 0.0, yhi)
    p1.frame()
    p1.grid_y(_ticks(0.0, yhi, 0.5), lambda v: _num(v, 1), dx=26.0)
    p1.grid_x([0, 400, 800, 1200, 1600], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.path(cv, "hm2", tip="véga")
    p1.path(cr, "hm6", tip="rho")
    x0 = R.croisement_unite()
    p1.vline(x0, "lvl")
    p1.dot(x0, _rp(x0), "hm6", "croisement", r=4.5)
    p1.label(x0, yhi * 0.92, _num(x0, 0) + " j", dx=7, dy=0)
    p1.label(js[-1], _rp(js[-1]), "rho", dx=-6, dy=-8, anchor="end")
    p1.label(js[-1], cv[-1][1], "véga", dx=-6, dy=16, anchor="end")

    # Les trois risques parcourent trois ordres de grandeur : traces en
    # echelle lineaire, le plus grand ecrase les deux qui se croisent et le
    # croisement — le sujet du cadre — devient invisible. L axe est donc
    # logarithmique, et chaque courbe est nommee a son extremite.
    p2 = Panel(b, PX2, 92, PW, 214, title="Pondéré par les moteurs",
               readout="points d'indice par mois")
    rr = [(j, math.log10(R.risque_rho(j))) for j in js]
    rb = [(j, math.log10(R.risque_vega(j, structure=False))) for j in js]
    rs = [(j, math.log10(R.risque_vega(j, structure=True))) for j in js]
    ylo2 = min(y for _, y in rr) - 0.25
    yhi2 = max(y for _, y in rb) + 0.35
    p2.domain(0.0, js[-1], ylo2, yhi2)
    p2.frame()
    p2.grid_y([v for v in range(int(math.ceil(ylo2)),
                                int(math.floor(yhi2)) + 1)],
              lambda v: _dec(10.0 ** v), dx=30.0)
    p2.grid_x([0, 400, 800, 1200, 1600], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.path(rb, "hm1", dash="6 3", tip="véga, sans terme")
    p2.path(rs, "hm3", tip="véga, avec terme")
    p2.path(rr, "hm6", tip="rho")
    x1 = R.croisement_structure()
    p2.vline(x1, "lvl")
    p2.label(x1, yhi2 - 0.12, _num(x1 / AN, 1) + " ans", dx=7, dy=0)
    p2.label(js[-1], rb[-1][1], "véga sans terme", dx=-6, dy=-8, anchor="end")
    p2.label(js[-1], rr[-1][1], "rho", dx=-6, dy=-8, anchor="end")
    p2.label(js[-1], rs[-1][1], "véga avec terme", dx=-6, dy=16, anchor="end")

    b.legend(0.0, 362.0,
             [("hm6", "rho"), ("hm2", "véga, à gauche"),
              ("hm3", "véga pondéré, avec terme"),
              ("hm1", "véga pondéré, sans terme", "6 3")],
             step=158.0)
    b.annotation(0.0, 386.0,
                 "à gauche, un point de taux contre un point de volatilité : "
                 "le croisement tombe à " + _num(x0, 0) + " jours")
    b.annotation(0.0, 402.0,
                 "mais les deux moteurs ne se produisent pas à la même "
                 "fréquence, et l'implicite bouge ici "
                 + _num(R.DISPERSION_VOL / R.DISPERSION_TAUX, 0)
                 + " fois plus")
    b.annotation(0.0, 418.0,
                 "pondéré sans terme, le rho ne rejoint jamais le véga ; "
                 "avec terme, il le rejoint à " + _num(x1 / AN, 1) + " ans")

    _source(b, "Le guide écrit qu'au-delà d'un an, rho peut rivaliser avec "
               "le véga. Le cadre de gauche lui donne raison trop tôt, et "
               "pour une mauvaise raison : il compare deux dérivées sans "
               "rapporter chacune à ce que son moteur fait en un mois. Le "
               "cadre de droite les rapporte, et le verdict dépend alors "
               "d'une hypothèse que le guide n'écrit pas — la volatilité "
               "implicite d'une option de deux ans bouge-t-elle autant que "
               "celle du mois ? Elle ne le fait pas, et le poids ajusté de "
               "la partie XXII le chiffre. C'est cette hypothèse, et non le "
               "rho, qui décide de la réponse.")
    return b.render("Le croisement entre rho et vega, compare unite contre "
                    "unite puis pondere par la dispersion des moteurs.")


def fig_rh_moteurs() -> str:
    """La dispersion des deux moteurs, et le croisement qui en dépend."""
    b = _plate(490, "Rho · les moteurs",
               "Une sensibilité ne devient un risque qu'au contact de son moteur",
               "dispersion mensuelle")

    p1 = Panel(b, PX1, 92, PW, 214, title="Ce que fait chaque moteur",
               readout="points par mois")
    p1.domain(-0.6, 1.6, 0.0, R.DISPERSION_VOL * 1.30)
    p1.frame()
    p1.grid_y(_ticks(0.0, R.DISPERSION_VOL * 1.30, 1.0),
              lambda v: _num(v, 0), dx=26.0)
    p1.vbar(0.0, 0.0, R.DISPERSION_TAUX, 62.0, "hm6", tip="le taux")
    p1.vbar(1.0, 0.0, R.DISPERSION_VOL, 62.0, "hm2", tip="l'implicite")
    p1.label(0.0, R.DISPERSION_TAUX, _num(R.DISPERSION_TAUX, 2), dx=0,
             dy=-8, anchor="middle")
    p1.label(1.0, R.DISPERSION_VOL, _num(R.DISPERSION_VOL, 2), dx=0, dy=-8,
             anchor="middle")
    p1.label(0.0, 0.0, "le taux", dx=0, dy=16, anchor="middle")
    p1.label(1.0, 0.0, "l'implicite du mois", dx=0, dy=16, anchor="middle")

    p2 = Panel(b, PX2, 92, PW, 214, title="Le croisement qui en sort",
               readout="années")
    sigmas = [0.06 + 0.01 * i for i in range(60)]
    avec = [(s, R.croisement_structure(s) / AN) for s in sigmas]
    yhi = max(y for _, y in avec) * 1.20
    p2.domain(sigmas[0], sigmas[-1], 0.0, yhi)
    p2.frame()
    p2.grid_y(_ticks(0.0, yhi, 2.0), lambda v: _num(v, 0), dx=22.0)
    p2.grid_x([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], lambda v: _num(v, 1),
              label="dispersion du taux (points par mois)")
    p2.path(avec, "hm3", tip="croisement")
    p2.hline(1.0, "lvl")
    p2.label(sigmas[0], 1.0, "un an", dx=8, dy=-6)
    for s in R.DISPERSIONS_TAUX:
        p2.dot(s, R.croisement_structure(s) / AN, "hm3",
               _num(s, 2) + " pt/mois", r=3.6)

    b.legend(0.0, 342.0,
             [("hm6", "le taux"), ("hm2", "la volatilité implicite"),
              ("hm3", "le croisement, à droite")],
             step=200.0)
    b.annotation(0.0, 366.0,
                 "aucun des deux moteurs n'est observable dans ce dépôt : "
                 "les deux sont déclarés et balayés")
    b.annotation(0.0, 382.0,
                 "il ne passe sous un an qu'à "
                 + _num(R.dispersion_pour_un_an(), 2) + " point de taux par "
                 "mois, au-delà de toute la plage balayée")
    b.annotation(0.0, 398.0,
                 "la courbe décroît, mais lentement : la réponse est robuste "
                 "au paramètre non observable")

    _source(b, "Deux paramètres non observables décident de cette section, "
               "et ce document les balaie plutôt que de les choisir — comme "
               "la taille de grappe du footprint et la volatilité de la "
               "volatilité de la partie XXII. Le cadre de gauche montre "
               "l'ordre de grandeur qui sépare les deux moteurs : un point "
               "de volatilité implicite est une petite chose, un point de "
               "taux à deux ans est un événement. Le cadre de droite montre "
               "que le croisement dépend d'eux sans en dépendre "
               "violemment : il reste entre un et six ans sur toute la "
               "plage, ce qui suffit à trancher.")
    return b.render("La dispersion mensuelle des deux moteurs, et le "
                    "croisement rho-vega qui en depend.")


def fig_rh_relief_croisement() -> str:
    """Le relief du croisement, en dispersion de taux et en vitesse de retour."""
    z = [list(l) for l in R.surface_croisement()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Rho · le relief du croisement",
               "Le siècle où rho rejoint le véga, et ce dont il dépend",
               "hauteur : années")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(s, 2) for s in R.SURF_SIGMA],
             col_labels=[_num(k, 0) for k in R.SURF_KAPPA],
             z_ticks=[(t, _num(t, 0)) for t in _echine(zlo, zhi)],
             tip="{v:.1f} ans", zero=zlo)

    b.annotation(0.0, 408.0,
                 "arête gauche : la dispersion du taux · arête droite : la "
                 "vitesse de retour de la surface · hauteur : le croisement")
    b.annotation(0.0, 424.0,
                 "il court de " + _num(min(vals), 1) + " à "
                 + _num(max(vals), 1) + " ans, un facteur "
                 + _num(max(vals) / min(vals), 0)
                 + " pour deux paramètres qu'on ne peut pas observer ici")
    b.annotation(0.0, 440.0,
                 "un rang sur douze passe sous l'an, trois quarts du "
                 "domaine sous cinq ans")

    _source(b, "La hauteur est l'échéance où le risque de taux d'une option "
               "rejoint son risque de volatilité, les deux pondérés par la "
               "dispersion mensuelle de leur moteur. Deux paramètres non "
               "observables la gouvernent : ce que fait le taux, et à quelle "
               "vitesse la volatilité implicite d'une option longue oublie "
               "un choc sur le mois. Le coin du fond réunit le taux le plus "
               "calme et la surface la plus rigide, où le véga long reste "
               "grand et rho ne le rejoint jamais dans une vie ; le coin le "
               "plus proche réunit un taux agité et une surface qui oublie "
               "vite, où rho l'emporte avant l'an. L'affirmation du guide "
               "n'est pas fausse : elle est une coupe de ce relief, et il ne "
               "dit pas laquelle.")
    return b.render("Relief du croisement rho-vega, en dispersion du taux et "
                    "en vitesse de retour de la surface.")


# ---------------------------------------------------------------------------
# III. Le régime de taux
# ---------------------------------------------------------------------------


def fig_rh_regime() -> str:
    """Ce que le passage de zéro à cinq pour cent a déplacé."""
    b = _plate(490, "Rho · le régime",
               "La sensibilité n'a presque pas bougé, le moteur oui",
               "de zéro à huit pour cent")

    # Une courbe plate seule occupe le sixieme d un cadre et ne dit rien de
    # sa platitude : elle se lit contre une grandeur qui bouge, sur le meme
    # axe et dans le meme cadre. Les deux sont rapportees a leur valeur au
    # taux nul, donc les deux partent de un.
    taux = [0.0 + 0.0016 * i for i in range(51)]
    ref = R.rho_par_point(S, S, V, 2.0, 0.0, R.DIVIDENDE)
    ref_pic = R.echeance_du_pic(S, S, V, 1e-9, R.DIVIDENDE)
    p1 = Panel(b, PX1, 92, PW, 214, title="Ce que le niveau du taux gouverne",
               readout="rapport au taux nul")
    mesure = [(100 * r, R.rho_par_point(S, S, V, 2.0, r, R.DIVIDENDE) / ref)
              for r in taux]
    forme = [(100 * r,
              R.echeance_du_pic(S, S, V, max(r, 1e-9), R.DIVIDENDE) / ref_pic)
             for r in taux]
    p1.domain(0.0, 100 * taux[-1], 0.0, 1.45)
    p1.frame()
    p1.grid_y(_ticks(0.0, 1.45, 0.25), lambda v: _num(v, 2), dx=30.0)
    p1.grid_x([0, 2, 4, 6, 8], lambda v: _num(v, 0), label="taux (%)")
    p1.path(forme, "hm1", dash="2 3", tip="l'échéance du maximum")
    p1.path(mesure, "hm6", tip="rho à deux ans")
    p1.hline(1.0, "lvl")
    p1.dot(5.0, R.rho_par_point(S, S, V, 2.0, 0.05, R.DIVIDENDE) / ref,
           "hm6", "cinq pour cent", r=4.5)
    p1.label(0.0, 0.06, "les deux sont rapportées au taux nul", dx=8, dy=0)
    p1.label(100 * taux[-1],
             R.rho_par_point(S, S, V, 2.0, taux[-1], R.DIVIDENDE) / ref,
             "la sensibilité", dx=-6, dy=-8, anchor="end")
    p1.label(100 * taux[-1], forme[-1][1], "l'échéance du maximum",
             dx=-6, dy=-8, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce que le moteur déplace",
               readout="points d'indice par mois")
    p2.domain(-0.6, len(R.DISPERSIONS_TAUX) - 0.4, 0.0,
              R.risque_rho(730.0, R.DISPERSIONS_TAUX[-1]) * 1.35)
    p2.frame()
    p2.grid_y(_ticks(0.0, R.risque_rho(730.0, R.DISPERSIONS_TAUX[-1]) * 1.35,
                     0.10), lambda v: _num(v, 2), dx=30.0)
    for i, s in enumerate(R.DISPERSIONS_TAUX):
        p2.vbar(i, 0.0, R.risque_rho(730.0, s), 34.0, "hm4",
                tip=_num(s, 2) + " pt/mois")
        p2.label(i, 0.0, _num(s, 2), dx=0, dy=16, anchor="middle")
    p2.label(0.0, R.risque_rho(730.0, R.DISPERSIONS_TAUX[-1]) * 1.20,
             "dispersion mensuelle du taux (points)", dx=4, dy=0)

    b.legend(0.0, 342.0,
             [("hm6", "la sensibilité"),
              ("hm1", "l'échéance du maximum", "2 3"),
              ("hm4", "le risque, à droite")],
             step=200.0)
    b.annotation(0.0, 366.0,
                 "« un risque ignoré à 0 % n'est pas ignorable à 5 % » : la "
                 "sensibilité croît de "
                 + _num(100 * (R.rho_par_point(S, S, V, 2.0, 0.08,
                                               R.DIVIDENDE) / ref - 1.0), 0)
                 + " % sur toute la plage")
    b.annotation(0.0, 382.0,
                 "la seule grandeur que le niveau du taux gouverne vraiment "
                 "est la forme, c'est-à-dire le lieu du maximum")
    b.annotation(0.0, 398.0,
                 "ce qui a changé de plusieurs ordres est la dispersion du "
                 "moteur, que le cadre de droite balaie")

    _source(b, "La phrase la plus citable du guide est juste dans sa "
               "conclusion et fausse dans son sujet. Le cadre de gauche "
               "montre une sensibilité presque plate : entre le taux nul et "
               "huit pour cent, le rho d'une option de deux ans gagne moins "
               "d'un quart. Le cadre de droite montre ce qui a réellement "
               "changé — la dispersion du taux, qui a passé une décennie à "
               "ne rien faire puis une année à bouger. Attribuer au grec ce "
               "qui appartient à son moteur est exactement la faute que la "
               "section précédente mesure sur le croisement avec le véga, "
               "et c'est la même phrase qui la porte deux fois.")
    return b.render("Le rho contre le niveau du taux, et le risque contre la "
                    "dispersion du moteur.")


# ---------------------------------------------------------------------------
# IV. À spot fixe ou à forward fixe
# ---------------------------------------------------------------------------


def fig_rh_forward() -> str:
    """Les deux rhos, et le contrôle qui les sépare."""
    b = _plate(500, "Rho · les deux variables",
               "Le même grec, deux signes, selon ce qu'on tient fixe",
               "par point de taux")

    js = [7.0 + 8.0 * i for i in range(140)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Les deux dérivées",
               readout="points d'indice")
    spot = [(j, _rp(j)) for j in js]
    fwd = [(j, R.rho_forward_fixe(S, S, V, j / AN)) for j in js]
    ylo = min(y for _, y in fwd) * 1.30
    yhi = max(y for _, y in spot) * 1.25
    p1.domain(0.0, js[-1], ylo, yhi)
    p1.frame()
    p1.grid_y(_ticks(ylo, yhi, 0.4), lambda v: _signed(v, 1), dx=26.0)
    p1.grid_x([0, 300, 600, 900, 1100], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.hline(0.0, "lvl")
    p1.path(spot, "hm6", tip="à spot fixe")
    p1.path(fwd, "hm2", tip="à forward fixe")
    # Les deux noms se posent au ras des bords, ou la donnee n est pas : une
    # etiquette au bout d une courbe descendante est barree par elle.
    p1.label(0.0, yhi * 0.90, "trait haut : à spot fixe", dx=8, dy=0)
    p1.label(0.0, ylo * 0.82, "trait bas : à forward fixe", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Le contrôle par différence finie",
               readout="à forward fixe")
    ferme = [(j, R.rho_forward_fixe(S, S, V, j / AN)) for j in js]
    ctl = [(j, R.rho_forward_numerique(S, S, V, j / AN)) for j in js]
    ylo2 = min(y for _, y in ferme) * 1.30
    p2.domain(0.0, js[-1], ylo2, 0.06)
    p2.frame()
    p2.grid_y(_ticks(ylo2, 0.06, 0.2), lambda v: _signed(v, 1), dx=26.0)
    p2.grid_x([0, 300, 600, 900, 1100], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.hline(0.0, "lvl")
    # Le controle et la forme fermee se superposent exactement, et c est le
    # resultat du cadre : trace en pointille sombre sous un trait clair, il
    # devient invisible et la planche ne montre plus qu une courbe. Le
    # controle passe donc dessous en trait large et clair, la forme fermee
    # par-dessus en pointille sombre.
    p2.path(ctl, "hm7", tip="la différence finie")
    p2.path(ferme, "hm2", dash="5 4", tip="moins T fois la valeur")
    p2.label(60.0, ylo2 * 0.45, "trait clair : la différence finie", dx=0,
             dy=0)
    p2.label(60.0, ylo2 * 0.60, "pointillé sombre : la forme fermée",
             dx=0, dy=0)
    p2.label(60.0, ylo2 * 0.75, "le taux et le spot bougés ensemble", dx=0,
             dy=0)

    b.legend(0.0, 352.0,
             [("hm6", "à spot fixe"), ("hm2", "à forward fixe"),
              ("hm7", "le contrôle, à droite"),
              ("hm2", "la forme fermée, à droite", "5 4")],
             step=158.0)
    b.annotation(0.0, 376.0,
                 "une option d'indice est écrite sur le forward, et le guide "
                 "le dit sans en tirer la conséquence")
    b.annotation(0.0, 392.0,
                 "à spot fixe, monter le taux monte le forward et le call "
                 "vaut plus ; à forward fixe il ne reste que l'escompte")
    b.annotation(0.0, 408.0,
                 "un pupitre qui couvre son rho sans dire laquelle il tient "
                 "fixe couvre dans une direction sur deux")

    _source(b, "Le cadre de droite est le contrôle que ce dépôt s'impose "
               "sans exception : la forme fermée, moins T fois la valeur, prétend être la "
               "dérivée du prix par rapport au taux quand le forward reste "
               "fixe, et la seule façon de le vérifier est de bouger le taux "
               "en compensant le spot par le facteur d escompte. Les deux tracés se "
               "superposent sur toute l'étendue. Le résultat de la section "
               "n'est pas ce nombre mais son signe : deux lectures "
               "également légitimes du même grec sont opposées, et rien dans "
               "le mot « rho » ne dit laquelle on emploie.")
    return b.render("Le rho a spot fixe et a forward fixe, et le controle de "
                    "la forme fermee par difference finie.")


def fig_rh_relief_ecart() -> str:
    """Le relief de l'écart entre les deux rhos."""
    z = [list(l) for l in R.surface_ecart()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Rho · le relief des deux lectures",
               "Ce que coûte de ne pas dire quelle variable on tient fixe",
               "hauteur : points par point de taux")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(j / AN, 1) for j in R.SURF_ECHEANCE_ECART],
             col_labels=[_num(m, 2) for m in R.SURF_MONEYNESS],
             z_ticks=[(t, _num(t, 1)) for t in _echine(zlo, zhi)],
             tip="{v:.2f} points", zero=zlo)

    b.annotation(0.0, 408.0,
                 "arête gauche : l'échéance en années · arête droite : le "
                 "rapport du spot au strike · hauteur : l'écart")

    b.annotation(0.0, 424.0,
                 "le relief ne redescend nulle part au sol : les deux "
                 "lectures ne convergent en aucun point du domaine")
    b.annotation(0.0, 440.0,
                 "il monte avec l'échéance et avec la monnaie, c'est-à-dire "
                 "avec tout ce qui rend l'option lourde")

    _source(b, "La hauteur est la différence entre les deux dérivées, celle "
               "à spot fixe et celle à forward fixe, sur une seule option. "
               "Elle vaut la somme de leurs valeurs absolues, les deux étant "
               "de signes opposés, et c'est ce qu'un pupitre se trompe de "
               "couvrir s'il ne dit pas laquelle il emploie. Le coin du fond "
               "réunit l'échéance longue et l'option profondément dans la "
               "monnaie, où le call est devenu un emprunt : l'écart y "
               "dépasse neuf points d'indice par point de taux. Aucune "
               "région du relief ne tombe au sol, donc aucune géométrie ne "
               "rend la question sans objet.")
    return b.render("Relief de l ecart entre le rho a spot fixe et le rho a "
                    "forward fixe, en echeance et en moneyness.")


# ---------------------------------------------------------------------------
# V. L'action financée
# ---------------------------------------------------------------------------


def fig_rh_financee() -> str:
    """La convergence du call vers l'action financée."""
    b = _plate(500, "Rho · l'action financée",
               "À quelle vitesse un call cesse d'être une option",
               _num(R.T_FINANCEE, 0) + " ans à l'échéance")

    ms = [0.70 + 0.01 * i for i in range(241)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Le call et l'action financée",
               readout="points d'indice")
    call = [(m, th.call(S * m, S, V, R.T_FINANCEE)) for m in ms]
    fin = [(m, R.action_financee(S * m, S, R.T_FINANCEE)) for m in ms]
    ylo = min(y for _, y in fin) * 1.10
    yhi = max(y for _, y in call) * 1.20
    p1.domain(ms[0], ms[-1], ylo, yhi)
    p1.frame()
    p1.grid_y(_ticks(ylo, yhi, 50.0), lambda v: _num(v, 0), dx=26.0)
    p1.grid_x([0.8, 1.2, 1.6, 2.0, 2.4, 2.8], lambda v: _num(v, 1),
              label="spot sur strike")
    p1.hline(0.0, "lvl")
    p1.path(fin, "hm0", dash="2 3", tip="l'action financée")
    p1.path(call, "hm6", tip="le call")
    p1.label(ms[0], yhi * 0.92, "trait plein : le call", dx=6, dy=0)
    p1.label(ms[0], yhi * 0.82, "pointillé : l'action financée", dx=6, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce qui reste d'optionalité",
               readout="part du rho maximal")
    ecart = [(m, 100.0 * (th.call(S * m, S, V, R.T_FINANCEE)
                          - R.action_financee(S * m, S, R.T_FINANCEE))
              / th.call(S * m, S, V, R.T_FINANCEE)) for m in ms if m >= 0.85]
    part = [(m, 100.0 * R.rho_call(S * m, S, V, R.T_FINANCEE)
             / R.rho_plafond(S, R.T_FINANCEE)) for m in ms if m >= 0.85]
    p2.domain(0.85, ms[-1], 0.0, 108.0)
    p2.frame()
    p2.grid_y([0, 25, 50, 75, 100], lambda v: _num(v, 0) + " %", dx=30.0)
    p2.grid_x([1.0, 1.4, 1.8, 2.2, 2.6, 3.0], lambda v: _num(v, 1),
              label="spot sur strike")
    p2.path(ecart, "hm2", tip="l'écart relatif")
    p2.path(part, "hm4", tip="la part du rho maximal")
    p2.hline(100.0, "lvl")
    p2.dot(2.0, 100.0 * R.rho_call(2 * S, S, V, R.T_FINANCEE)
           / R.rho_plafond(S, R.T_FINANCEE), "hm4", "deux fois le strike",
           r=4.5)
    p2.label(ms[-1], 8.0, "l'écart relatif", dx=-6, dy=0, anchor="end")
    p2.label(1.55, 78.0, "la part du rho maximal", dx=0, dy=0)

    b.legend(0.0, 352.0,
             [("hm6", "le call"), ("hm0", "l'action financée", "2 3"),
              ("hm2", "l'écart relatif, à droite"),
              ("hm4", "la part du plafond")],
             step=158.0)
    b.annotation(0.0, 376.0,
                 "l'affirmation du guide est exacte, et ce document la "
                 "chiffre au lieu de l'illustrer")
    b.annotation(0.0, 392.0,
                 "à deux fois le strike, l'écart vaut "
                 + _pct((th.call(2 * S, S, V, R.T_FINANCEE)
                         - R.action_financee(2 * S, S, R.T_FINANCEE))
                        / th.call(2 * S, S, V, R.T_FINANCEE), 2)
                 + " et le rho a rejoint "
                 + _num(100.0 * R.rho_call(2 * S, S, V, R.T_FINANCEE)
                        / R.rho_plafond(S, R.T_FINANCEE), 0)
                 + " % de son plafond")
    b.annotation(0.0, 408.0,
                 "ce qui reste du call n'est plus une option, c'est un "
                 "emprunt, et rho en mesure la durée")

    _source(b, "Le plafond du rho est le strike actualisé fois la durée, celui d'une option "
               "certaine d'être exercée : le prix actualisé du strike, "
               "multiplié par la durée pendant laquelle on diffère de le "
               "payer. La courbe de droite est donc littéralement la "
               "probabilité risque-neutre d'exercice, et sa lecture est "
               "comptable : à deux fois le strike, l'option est exercée dans "
               "presque tous les états du monde et le contrat s'est réduit à "
               "un prêt. C'est le seul endroit des cinq parties d'options où "
               "un grec cesse de mesurer une sensibilité.")
    return b.render("La convergence du call vers l action financee, et la "
                    "part du rho maximal atteinte.")


def fig_rh_plafond() -> str:
    """Le rho et son plafond, contre la moneyness et contre l'échéance."""
    b = _plate(490, "Rho · le plafond",
               "Rho ne dépasse jamais la durée d'un prêt",
               "le strike actualisé fois la durée")

    ms = [0.60 + 0.01 * i for i in range(241)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Contre la monnaie",
               readout="par unité de taux")
    plafond = R.rho_plafond(S, R.T_FINANCEE)
    mesure = [(m, R.rho_call(S * m, S, V, R.T_FINANCEE)) for m in ms]
    p1.domain(ms[0], ms[-1], 0.0, plafond * 1.18)
    p1.frame()
    p1.grid_y(_ticks(0.0, plafond * 1.18, 50.0), lambda v: _num(v, 0),
              dx=26.0)
    p1.grid_x([0.8, 1.2, 1.6, 2.0, 2.4, 2.8], lambda v: _num(v, 1),
              label="spot sur strike")
    p1.hline(plafond, "lvl")
    p1.path(mesure, "hm5", tip="le rho")
    p1.label(ms[0], plafond, "le plafond du rho", dx=6, dy=-6)
    p1.label(1.0, R.rho_call(S, S, V, R.T_FINANCEE), "à la monnaie",
             dx=8, dy=8)

    p2 = Panel(b, PX2, 92, PW, 214, title="Contre l'échéance",
               readout="part du plafond")
    js = [30.0 + 30.0 * i for i in range(120)]
    # Une seule courbe a la monnaie occupait le huitieme du cadre : la part
    # du plafond varie peu avec l echeance et beaucoup avec la monnaie, donc
    # c est l eventail qu il faut montrer.
    familles = [("hm6", "", 1.30), ("hm3", "2 3", 1.00), ("hm1", "1 4", 0.80)]
    p2.domain(0.0, js[-1] / AN, 0.0, 100.0)
    p2.frame()
    p2.grid_y([0, 25, 50, 75, 100], lambda v: _num(v, 0) + " %", dx=30.0)
    p2.grid_x([0, 2, 4, 6, 8], lambda v: _num(v, 0),
              label="années à l'échéance")
    for cls, dash, m in familles:
        courbe = [(j / AN, 100.0 * R.rho_call(S * m, S, V, j / AN)
                   / R.rho_plafond(S, j / AN)) for j in js]
        p2.path(courbe, cls, dash=dash, tip="spot sur strike " + _num(m, 2))
        p2.label(js[-1] / AN, courbe[-1][1], _num(m, 2), dx=-6, dy=-6,
                 anchor="end")
    p2.label(0.4, 92.0, "spot sur strike, en bout de courbe", dx=0, dy=0)

    b.legend(0.0, 342.0,
             [("hm5", "le rho contre la monnaie"),
              ("hm6", "dans la monnaie, à droite"),
              ("hm3", "à la monnaie, à droite", "2 3"),
              ("hm1", "hors de la monnaie, à droite", "1 4")],
             step=158.0)
    b.annotation(0.0, 366.0,
                 "le plafond est le rho d'une option certaine d'être "
                 "exercée : le strike actualisé, fois la durée du report")
    b.annotation(0.0, 382.0,
                 "la part atteinte est exactement la probabilité "
                 "risque-neutre d'exercice, et le cadre de droite en montre "
                 "l'éventail")
    b.annotation(0.0, 398.0,
                 "il se referme : à trente ans les trois moneyness ne sont "
                 "plus séparées que de "
                 + _num(100.0 * (R.rho_call(1.3 * S, S, V, 30.0)
                                 / R.rho_plafond(S, 30.0)
                                 - R.rho_call(0.8 * S, S, V, 30.0)
                                 / R.rho_plafond(S, 30.0)), 0)
                 + " points, contre "
                 + _num(100.0 * (R.rho_call(1.3 * S, S, V, 0.25)
                                 / R.rho_plafond(S, 0.25)
                                 - R.rho_call(0.8 * S, S, V, 0.25)
                                 / R.rho_plafond(S, 0.25)), 0)
                 + " à trois mois")

    _source(b, "Les deux cadres portent la même identité vue de deux côtés. "
               "Rho vaut le plafond multiplié par la probabilité "
               "risque-neutre d'exercice, donc il ne peut jamais le "
               "dépasser, et toute la forme du grec est celle de cette "
               "probabilité. Le cadre de droite montre ce que le temps lui "
               "fait, et c'est le fait le moins attendu de la section : "
               "l'éventail se referme. Le terme de moneyness est divisé par "
               "la racine de l'échéance, donc il s'efface, et une option de "
               "trente ans profondément dans la monnaie n'a plus qu'une "
               "chance sur deux d'être exercée — la même qu'une option à la "
               "monnaie. La courbe du milieu, elle, décroît de deux points "
               "seulement sur trente ans, et ce petit nombre est exactement "
               "celui de la section précédente : il vaut zéro au taux où le "
               "maximum de rho tombe sur l'inverse du taux.")
    return b.render("Le rho contre son plafond, en monnaie et en echeance.")


# ---------------------------------------------------------------------------
# VI. Ce que rho coûte à l'opérateur de ce document
# ---------------------------------------------------------------------------


def fig_rh_cout() -> str:
    """Le coût d'une séance, rapporté à la friction déclarée."""
    b = _plate(500, "Rho · le coût",
               "La phrase la plus juste des cinq guides, chiffrée",
               "friction : " + _num(R.FRICTION, 2) + " point")

    p1 = Panel(b, PX1, 92, PW, 214, title="Le coût d'une séance",
               readout="en unités de friction")
    js = [R.JOURS_INTRA, 1.0, 7.0, 30.0, 90.0, 365.0, 730.0, 1825.0,
          3650.0, 7665.0]
    pts = [(math.log10(j), math.log10(R.cout_de_rho(j) / R.FRICTION))
           for j in js]
    xlo, xhi = math.log10(R.JOURS_INTRA) - 0.3, math.log10(7665.0) + 0.3
    ylo = min(y for _, y in pts) - 0.4
    yhi = max(0.3, max(y for _, y in pts) + 0.3)
    p1.domain(xlo, xhi, ylo, yhi)
    p1.frame()
    p1.grid_y([v for v in range(int(math.ceil(ylo)), int(math.floor(yhi)) + 1)],
              lambda v: _dec(10.0 ** v), dx=30.0)
    p1.grid_x([-1, 0, 1, 2, 3, 4], lambda v: _dec(10.0 ** v),
              label="jours à l'échéance")
    p1.hline(0.0, "lvl")
    p1.path(pts, "hm6", tip="le coût")
    for j in js:
        p1.dot(math.log10(j),
               math.log10(R.cout_de_rho(j) / R.FRICTION), "hm6",
               _num(j, 0) + " jours : "
               + _num(R.cout_de_rho(j) / R.FRICTION, 5), r=3.6)
    p1.label(xlo, 0.0, "la friction déclarée", dx=6, dy=-6)
    p1.label(math.log10(R.JOURS_INTRA),
             math.log10(R.cout_de_rho(R.JOURS_INTRA) / R.FRICTION),
             "dans la séance", dx=6, dy=-8)

    p2 = Panel(b, PX2, 92, PW, 214, title="L'échéance qui égale la friction",
               readout="années")
    sig = [0.30 + 0.01 * i for i in range(41)]
    lieu = [(s, R.echeance_du_cout(s) / AN) for s in sig
            if math.isfinite(R.echeance_du_cout(s))]
    if lieu:
        yhi2 = max(y for _, y in lieu) * 1.15
        p2.domain(sig[0], sig[-1], 0.0, yhi2)
        p2.frame()
        p2.grid_y(_ticks(0.0, yhi2, 5.0), lambda v: _num(v, 0), dx=22.0)
        p2.grid_x([0.3, 0.4, 0.5, 0.6, 0.7], lambda v: _num(v, 1),
                  label="dispersion du taux (points par mois)")
        p2.path(lieu, "hm3", tip="l'échéance")
        p2.label(lieu[0][0], lieu[0][1], "au-dessous, jamais", dx=8, dy=-8)
        p2.label(sig[-1], lieu[-1][1], _num(lieu[-1][1], 1) + " ans", dx=-6,
                 dy=-8, anchor="end")

    b.legend(0.0, 352.0,
             [("hm6", "le coût d'une séance, à gauche"),
              ("hm3", "l'échéance qui égale la friction, à droite")],
             step=240.0)
    b.annotation(0.0, 376.0,
                 "le guide s'ouvre en disant que rho est négligeable pour un "
                 "intrajournalier, et que le traiter ainsi est correct")
    b.annotation(0.0, 392.0,
                 "il l'est de " + _num(R.FRICTION / R.cout_de_rho(
                     R.JOURS_INTRA), 0) + " fois : ce n'est pas un petit "
                 "terme, c'est un terme qui n'existe pas")
    b.annotation(0.0, 408.0,
                 "il faut dépasser dix ans d'échéance et un régime de taux "
                 "agité pour qu'il atteigne la friction")

    _source(b, "Les deux axes du cadre de gauche sont logarithmiques, parce "
               "que la grandeur parcourt cinq ordres. La ligne pleine "
               "horizontale est la friction de la géométrie déclarée, celle "
               "qui gouverne tout le reste de ce document : au-dessus, rho "
               "compte ; au-dessous, il ne compte pas. La position de "
               "l'opérateur de ce document est à cinq ordres de grandeur "
               "sous cette ligne. Le cadre de droite dit ce qu'il faudrait "
               "pour l'y amener, et la réponse est un autre métier — une "
               "option de plus de dix ans dans un régime de taux que la "
               "période récente n'a connu qu'une fois.")
    return b.render("Le cout de rho sur une seance rapporte a la friction "
                    "declaree, et l echeance qui l egale.")


def fig_rh_relief_cout() -> str:
    """Le relief du coût, en dispersion de taux et en échéance."""
    z = [list(l) for l in R.surface_cout()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Rho · le relief du coût",
               "Où rho cesse d'être négligeable, et ce que cela demande",
               "hauteur : en unités de friction")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(s, 2) for s in R.SURF_SIGMA_COUT],
             col_labels=[_num(j / AN, 1) for j in R.SURF_ECHEANCE],
             z_ticks=[(t, _num(t, 1)) for t in _echine(zlo, zhi)],
             tip="{v:.3f} friction", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : la dispersion du taux · arête droite : "
                 "l'échéance en années · hauteur : le coût d'une séance")
    b.annotation(0.0, 424.0,
                 "le plan de hauteur un est la friction : le relief ne le "
                 "franchit que dans le coin du fond")
    b.annotation(0.0, 440.0,
                 "presque tout le domaine est au sol, et c'est le résultat "
                 "de la section")

    _source(b, "La hauteur est ce qu'un mouvement de taux d'une séance fait "
               "à une option, rapporté à la friction que la géométrie "
               "déclarée paie sur chaque décision. Le relief est plat sur "
               "presque toute son étendue : quelle que soit la dispersion du "
               "taux, une option de moins d'un an ne coûte rien en rho à "
               "l'échelle d'une séance. Il ne monte que dans le coin des "
               "échéances de plusieurs années et des taux agités, et il n'y "
               "dépasse l'unité qu'au tout dernier rang. Un opérateur "
               "intrajournalier n'a donc pas à couvrir son rho — non parce "
               "que c'est difficile, mais parce que la grandeur est cinq "
               "ordres sous ce qu'il paie déjà sans y penser.")
    return b.render("Relief du cout de rho sur une seance, en dispersion du "
                    "taux et en echeance.")


# ---------------------------------------------------------------------------
# VII. Le décompte
# ---------------------------------------------------------------------------


def fig_rh_reste() -> str:
    """Le décompte des sept affirmations, et le cumul des cinq parties."""
    aff = R.affirmations()
    compte = R.compte_par_grandeur()
    ordre = sorted(compte, key=lambda g: (-compte[g], g))
    fam = R.familles()
    total = sum(n for _, n in fam)

    b = _plate(470, "Rho · le décompte",
               "Trente-cinq affirmations, et aucune ne donne un sens",
               _num(len(aff), 0) + " ici")

    p1 = Panel(b, PX1, 92, PW, 214, title="Ce qu'elles déplacent",
               readout="affirmations")
    p1.domain(0.0, 6.0, -0.6, len(ordre) + 0.6)
    p1.frame()
    p1.grid_x(_ticks(0.0, 6.0, 2.0), lambda v: _num(v, 0))
    lignes = list(ordre) + ["la direction"]
    for i, g in enumerate(lignes):
        y = len(lignes) - 1 - i
        n = compte.get(g, 0)
        cls = {"la direction": "hm7", "rien": "hm1"}.get(g, "hm5")
        if n:
            p1.hbar(y, 0.0, n, 13.0, cls, tip=g + " : " + _num(n, 0))
        p1.label(0.0, y + 0.34, g, dx=4, dy=0)
        p1.label(max(n, 0.0), y, _num(n, 0), dx=7, dy=4)

    p2 = Panel(b, PX2, 92, PW, 214, title="Les cinq parties",
               readout="affirmations")
    haut = max(n for _, n in fam) * 1.35
    p2.domain(0.0, haut, -0.6, len(fam) - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, haut, 3.0), lambda v: _num(v, 0))
    for i, (nom, n) in enumerate(fam):
        y = len(fam) - 1 - i
        p2.hbar(y, 0.0, n, 11.0, "hm3", tip=nom)
        p2.label(0.0, y + 0.32, nom, dx=4, dy=0)
        p2.label(n, y, _num(n, 0), dx=7, dy=4)

    b.legend(0.0, 352.0,
             [("hm7", "touche à la direction"),
              ("hm5", "l'horloge ou le risque"),
              ("hm1", "ne déplace rien"),
              ("hm3", "les totaux, à droite")],
             step=166.0)
    b.annotation(0.0, 376.0,
                 _num(compte.get("le risque", 0), 0) + " affirmations "
                 "déplacent le risque, " + _num(compte.get("rien", 0), 0)
                 + " ne déplacent rien, "
                 + _num(compte.get("l'horloge", 0), 0) + " l'horloge")
    b.annotation(0.0, 392.0,
                 "la barre de la direction est vide, et c'est la première "
                 "des cinq parties d'options dans ce cas")
    b.annotation(0.0, 408.0,
                 "sur les " + _num(total, 0) + " affirmations des cinq "
                 "parties, aucune ne donne un sens")

    _source(b, "Rho est le seul des cinq grecs dont le moteur ne soit pas le "
               "prix, et c'est probablement pour cela que sa colonne de "
               "direction est vide : un guide qui parle du taux n'a aucune "
               "occasion de suggérer où va le marché. Les quatre "
               "affirmations qui déplacent le risque sont toutes utiles, et "
               "deux d'entre elles — le forward et l'action financée — sont "
               "exactes telles qu'écrites. Elles disent comment compter, "
               "jamais où aller. La série d'options se ferme donc là où la "
               "partie IV l'avait posée, et le décompte de cette planche "
               "n'est écrit nulle part : il est compté dans les cinq "
               "modules qui portent ces affirmations.")
    return b.render("Le decompte des affirmations de la partie et le cumul "
                    "des cinq parties d options.")


def render_all() -> dict[str, str]:
    """Les quinze planches, dans l'ordre du document."""
    return {
        "rhechelle": fig_rh_echelle(),
        "rhpic": fig_rh_pic(),
        "rhdeux": fig_rh_deux(),
        "rhreliefu": fig_rh_relief_usure(),
        "rhcroisement": fig_rh_croisement(),
        "rhmoteurs": fig_rh_moteurs(),
        "rhreliefc": fig_rh_relief_croisement(),
        "rhregime": fig_rh_regime(),
        "rhforward": fig_rh_forward(),
        "rhreliefe": fig_rh_relief_ecart(),
        "rhfinancee": fig_rh_financee(),
        "rhplafond": fig_rh_plafond(),
        "rhcout": fig_rh_cout(),
        "rhreliefco": fig_rh_relief_cout(),
        "rhreste": fig_rh_reste(),
    }
