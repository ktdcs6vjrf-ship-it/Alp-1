"""Les planches de « là où le delta et la volatilité se rencontrent ».

Quinze planches, onze à plat et quatre en relief. La première montre un
contrôle qui manquait à ce dépôt, et la neuvième une formule qui nomme le
mauvais grec ; entre les deux, tout se mesure contre une réévaluation.

Comme `figgra`, `figth`, `figvg` et `figrh`, ce module importe ses fonctions
d'échine, de graduation et de décade de `fignv` plutôt que de les recopier.
"""

from __future__ import annotations

import math

from . import grandeurs as G
from . import niveaux as nv
from . import quant as q
from . import vanna as VA
from . import vega as vg
from .figdisc import W, _plate, _source, _surface
from .fignv import _dec, _echine, _pct, _ticks
from .figterm import Board, Panel, _num, _signed


PW = (W - 74.0) / 2.0 - 30.0
PX1 = 74.0
PX2 = 74.0 + (W - 74.0) / 2.0

S = VA.S_REF
V = VA.VOL_REF
AN = VA.JOURS_AN


def _va(m: float, j: float, vol: float = V) -> float:
    return VA.vanna(S * m, S, vol, j / AN)


# ---------------------------------------------------------------------------
# I. Deux lectures, un nombre
# ---------------------------------------------------------------------------


def fig_va_deux() -> str:
    """Le vanna par ses deux routes, et le facteur que le dépôt publiait."""
    b = _plate(500, "Vanna · les deux routes",
               "Une forme fermée que rien ne consommait, donc que rien ne contrôlait",
               _num(100 * V, 0) + " % de volatilité")

    ms = [0.70 + 0.0025 * i for i in range(241)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Le vanna contre le comptant",
               readout="par unité de volatilité")
    series = [("hm7", "", 7.0), ("hm5", "6 3", 30.0), ("hm3", "2 3", 90.0),
              ("hm1", "1 4", 365.0)]
    courbes = [(cls, dash, j, [(m, _va(m, j)) for m in ms])
               for cls, dash, j in series]
    hi = max(y for _, _, _, c in courbes for _, y in c) * 1.35
    lo = min(y for _, _, _, c in courbes for _, y in c) * 1.35
    p1.domain(ms[0], ms[-1], lo, hi)
    p1.frame()
    p1.grid_y(_ticks(lo, hi, 0.5), lambda v: _signed(v, 1), dx=26.0)
    p1.grid_x([0.8, 0.9, 1.0, 1.1, 1.2, 1.3], lambda v: _num(v, 1),
              label="spot sur strike")
    p1.hline(0.0, "lvl")
    p1.vline(1.0, "lvl")
    for cls, dash, j, c in courbes:
        p1.path(c, cls, dash=dash, tip=_num(j, 0) + " jours")
    p1.label(ms[0], hi * 0.88, "positif sous le zéro", dx=8, dy=0)
    p1.label(ms[-1], lo * 0.55, "négatif au-dessus", dx=-8, dy=0, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Le facteur que le module portait",
               readout="rapport à la vérité")
    js = [3.0 + 4.0 * i for i in range(181)]
    faux = [(j, math.sqrt(j / AN)) for j in js]
    p2.domain(0.0, js[-1], 0.0, 1.45)
    p2.frame()
    p2.grid_y(_ticks(0.0, 1.45, 0.25), lambda v: _num(v, 2), dx=30.0)
    p2.grid_x([0, 180, 360, 540, 720], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.hline(1.0, "lvl")
    p2.path(faux, "hm2", tip="racine de l'échéance")
    p2.dot(30.0, math.sqrt(30.0 / AN), "hm2", "trente jours", r=4.5)
    p2.label(0.0, 1.0, "la valeur juste", dx=8, dy=-6)
    p2.label(30.0, math.sqrt(30.0 / AN),
             "à trente jours, un facteur "
             + _num(1.0 / math.sqrt(30.0 / AN), 1), dx=10, dy=6)

    b.legend(0.0, 352.0,
             [("hm7", "sept jours"), ("hm5", "trente jours", "6 3"),
              ("hm3", "quatre-vingt-dix jours", "2 3"),
              ("hm1", "un an", "1 4")],
             step=166.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le vanna a deux lectures — la sensibilité du delta à la "
                 "volatilité, celle du véga au comptant — et un seul nombre")
    b.annotation(0.0, 392.0,
                 "leur égalité est la symétrie des dérivées croisées, donc "
                 "elle ne peut échouer que si le code est faux")
    b.annotation(0.0, 408.0,
                 "elle l'était : la forme fermée du dépôt oubliait une "
                 "racine de l'échéance, et rien ne la consommait")

    _source(b, "Le cadre de gauche montre l'objet : une courbe en S qui "
               "traverse zéro un peu au-dessus de la monnaie, positive "
               "au-dessous et négative au-dessus, et qui s'aplatit aux deux "
               "bouts. Le cadre de droite montre le défaut que la "
               "vérification a trouvé dans ce dépôt même. La forme fermée y "
               "portait le véga divisé par le comptant et la volatilité, sans "
               "la racine de l'échéance, donc elle rendait le vanna "
               "multiplié par cette racine — trop petit d'un facteur trois "
               "et demi à trente jours, juste à un an, trop grand au-delà. "
               "Aucune table, aucune figure et aucun test ne s'en servait, "
               "et c'est exactement pour ce cas que la règle du dépôt "
               "existe : une forme fermée se contrôle contre une route "
               "indépendante, y compris quand personne ne s'en sert encore.")
    return b.render("Le vanna contre le comptant a quatre echeances, et le "
                    "facteur que la forme fermee du depot portait.")


def fig_va_zero() -> str:
    """Le lieu du zéro, et le taux qui décide de son côté."""
    b = _plate(490, "Vanna · le zéro",
               "Le vanna s'annule au-dessus de la monnaie, et pas toujours",
               "`d₂ = 0`")

    js = [3.0 + 6.0 * i for i in range(180)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Le lieu du zéro contre l'échéance",
               readout="points de base")
    courbe = [(j, 10000.0 * (VA.moneyness_du_zero(j / AN) - 1.0)) for j in js]
    hi = max(y for _, y in courbe) * 1.25
    p1.domain(0.0, js[-1], 0.0, hi)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi, 25.0), lambda v: _num(v, 0), dx=26.0)
    p1.grid_x([0, 250, 500, 750, 1000], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.path(courbe, "hm5", tip="écart à la monnaie")
    p1.label(0.0, hi * 0.86, "au-dessus de la monnaie", dx=8, dy=0)
    p1.dot(30.0, 10000.0 * (VA.moneyness_du_zero(30.0 / AN) - 1.0), "hm5",
           "trente jours", r=4.2)

    p2 = Panel(b, PX2, 92, PW, 214, title="Le côté que le taux décide",
               readout="points de base")
    taux = [0.0 + 0.0018 * i for i in range(51)]
    ligne = [(100 * r, 10000.0 * (VA.moneyness_du_zero(1.0, V, r, VA.DIVIDENDE)
                                  - 1.0)) for r in taux]
    ylo = min(y for _, y in ligne) * 1.20
    yhi = max(y for _, y in ligne) * 1.20
    p2.domain(0.0, 100 * taux[-1], ylo, yhi)
    p2.frame()
    p2.grid_y(_ticks(ylo, yhi, 200.0), lambda v: _signed(v, 0), dx=30.0)
    p2.grid_x([0, 2, 4, 6, 8], lambda v: _num(v, 0), label="taux (%)")
    p2.hline(0.0, "lvl")
    p2.path(ligne, "hm3", tip="à un an")
    rstar = VA.R.taux_du_pic_exact()
    p2.vline(100 * rstar, "lvl")
    p2.dot(100 * rstar, 0.0, "hm3", "le seul point d accord", r=4.5)
    p2.label(100 * rstar, yhi * 0.82, _pct(rstar, 2), dx=7, dy=0)
    p2.label(0.0, yhi * 0.55, "le zéro est au-dessus", dx=8, dy=0)
    p2.label(100 * taux[-1], ylo * 0.70, "au-dessous", dx=-8, dy=0,
             anchor="end")

    b.legend(0.0, 342.0,
             [("hm5", "le lieu du zéro, à gauche"),
              ("hm3", "contre le taux, à droite")],
             step=240.0)
    b.annotation(0.0, 366.0,
                 "le guide écrit que le zéro tombe légèrement au-dessus de "
                 "la monnaie, et c'est exact au taux déclaré")
    b.annotation(0.0, 382.0,
                 "la condition se calcule : le zéro est au-dessus tant que "
                 "le taux reste sous le rendement plus la demi-variance")
    b.annotation(0.0, 398.0,
                 "ce taux vaut " + _pct(rstar, 2) + ", et c'est le même que "
                 "la partie XXIII a trouvé sur le maximum du rho")

    _source(b, "Le vanna s'annule où la probabilité risque-neutre d'exercice "
               "passe par un demi, c'est-à-dire où d₂ s'annule. Le cadre de "
               "gauche donne la distance à la monnaie, qui croît avec "
               "l'échéance et reste minuscule aux horizons négociés. Le "
               "cadre de droite donne la condition : le zéro passe sous la "
               "monnaie dès que le taux dépasse le rendement du sous-jacent "
               "plus la moitié de sa variance, et la phrase du guide "
               "s'inverse. Ce taux-là est exactement celui que la partie "
               "XXIII a trouvé par une route entièrement différente, en "
               "cherchant où le maximum du rho tombe sur l'inverse du taux. "
               "Les deux fois, la condition est la même égalité, et la "
               "décennie des taux nuls la rendait vraie sans qu'on ait à la "
               "connaître.")
    return b.render("Le lieu du zero du vanna contre l echeance, et le cote "
                    "de la monnaie que le taux decide.")


def fig_va_relief_vanna() -> str:
    """Le relief de l'amplitude, et l'arête qui migre."""
    z = [list(l) for l in VA.surface_vanna()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Vanna · le relief de l'amplitude",
               "L'arête ne s'arrête à aucune échéance, elle sort du cadre",
               "hauteur : module du vanna")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(j / AN, 1) for j in VA.SURF_ECHEANCE],
             col_labels=[_num(m, 2) for m in VA.SURF_MONEYNESS],
             z_ticks=[(t, _num(t, 2)) for t in _echine(zlo, zhi)],
             tip="{v:.3f}", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : l'échéance en années · arête droite : le "
                 "rapport du spot au strike · hauteur : le module du vanna")
    b.annotation(0.0, 424.0,
                 "la crête suit un delta presque constant, donc elle "
                 "s'éloigne de la monnaie comme la racine du temps")
    b.annotation(0.0, 440.0,
                 "le sommet est au fond, à l'échéance la plus longue : rien "
                 "ne culmine à mi-chemin")

    _source(b, "Le guide écrit que le vanna est le plus grand aux échéances "
               "intermédiaires. Le relief dit autre chose : la crête monte "
               "jusqu'au fond du domaine, et ce qui se déplace est sa "
               "position en moneyness, pas sa hauteur. La crête suit un "
               "delta presque constant — seize pour cent à un jour, vingt et "
               "un à cinq ans — donc elle s'éloigne de la monnaie comme la "
               "racine du temps. Sur une fenêtre de moneyness fixée, elle "
               "finit par sortir par le côté, et ce qu'on voit alors décroître "
               "est la fenêtre, pas la grandeur. C'est le piège que ce "
               "dépôt a trouvé six fois dans ses propres figures, sous le nom "
               "de la légende écrite devant un cadre borné.")
    return b.render("Relief du module du vanna, en echeance et en moneyness.")


# ---------------------------------------------------------------------------
# II. Les deux endroits où la règle tombe
# ---------------------------------------------------------------------------


def fig_va_retournement() -> str:
    """Le delta contre la volatilité : il ne va pas vers un demi."""
    b = _plate(500, "Vanna · le retournement",
               "Le delta ne tend pas vers un demi, il tend vers un",
               "un an d'échéance")

    t = 1.0
    vols = [0.03 + 0.008 * i for i in range(300)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Le delta contre la volatilité",
               readout="call, un an")
    series = [("hm7", "", 1.20), ("hm5", "6 3", 1.10), ("hm3", "2 3", 1.05),
              ("hm1", "1 4", 0.95)]
    courbes = [(cls, dash, m,
                [(v, G.delta_comptant(S * m, S, v, t, VA.TAUX, VA.DIVIDENDE))
                 for v in vols]) for cls, dash, m in series]
    p1.domain(0.0, vols[-1], 0.0, 1.06)
    p1.frame()
    p1.grid_y([0.0, 0.25, 0.50, 0.75, 1.0], lambda v: _num(v, 2), dx=30.0)
    p1.grid_x([0.0, 0.6, 1.2, 1.8, 2.4], lambda v: _pct(v, 0),
              label="volatilité")
    p1.hline(0.50, "lvl")
    for cls, dash, m, c in courbes:
        p1.path(c, cls, dash=dash, tip="S/K " + _num(m, 2))
    for cls, dash, m in series:
        if m > 1.0:
            sig = VA.vol_du_retournement(m, t)
            p1.dot(sig, VA.plancher_du_delta(m, t), cls, "le plancher", r=4.0)
    p1.label(0.0, 0.50, "un demi", dx=8, dy=-6)
    p1.label(vols[-1], 0.98, "toutes montent vers un", dx=-8, dy=8,
             anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Le plancher et son contrôle",
               readout="delta minimal")
    ms = [1.01 + 0.005 * i for i in range(80)]
    ferme = [(m, VA.plancher_du_delta(m, t)) for m in ms]
    balaye = [(m, VA.plancher_balaye(m, t, 800)) for m in ms]
    p2.domain(ms[0], ms[-1], 0.45, 0.90)
    p2.frame()
    p2.grid_y(_ticks(0.45, 0.90, 0.10), lambda v: _num(v, 2), dx=30.0)
    p2.grid_x([1.05, 1.15, 1.25, 1.35], lambda v: _num(v, 2),
              label="spot sur strike")
    p2.hline(0.50, "lvl")
    p2.path(balaye, "hm7", tip="le balayage")
    p2.path(ferme, "hm2", dash="5 4", tip="la forme fermée")
    p2.label(ms[0], 0.86, "trait clair : le balayage", dx=8, dy=0)
    p2.label(ms[0], 0.81, "pointillé sombre : la forme fermée", dx=8, dy=0)
    p2.label(ms[-1], 0.50, "jamais atteint", dx=-8, dy=-8, anchor="end")

    b.legend(0.0, 352.0,
             [("hm7", "S/K 1,20"), ("hm5", "S/K 1,10", "6 3"),
              ("hm3", "S/K 1,05", "2 3"), ("hm1", "S/K 0,95", "1 4")],
             step=166.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le guide écrit que la volatilité haute fait ressembler "
                 "toute option à un tirage à pile ou face")
    b.annotation(0.0, 392.0,
                 "elle fait l'inverse : le delta descend, s'arrête sur un "
                 "plancher au-dessus d'un demi, puis remonte vers un")
    b.annotation(0.0, 408.0,
                 "sur un call à cinq pour cent dans la monnaie, le "
                 "retournement tombe à "
                 + _pct(VA.vol_du_retournement(1.05, 1.0), 1))

    _source(b, "Le delta vaut la loi normale prise en d un, et cet argument est la "
               "somme d'un terme qui décroît en volatilité et d'un terme qui "
               "croît. Sur une option dans la monnaie, cette somme passe par "
               "un minimum : le delta descend, s'arrête, puis remonte. Le "
               "lieu et le plancher sont tous deux en forme fermée, et le "
               "cadre de droite les contrôle contre un balayage de huit "
               "cents volatilités. Aucune option dans la monnaie n'atteint "
               "jamais un demi, et le retournement n'est pas hors de "
               "portée : à un an d'échéance et cinq pour cent dans la "
               "monnaie il tombe sous quarante pour cent de volatilité, un "
               "régime qu'un indice a visité plusieurs fois.")
    return b.render("Le delta contre la volatilite a quatre moneyness, et le "
                    "plancher du delta contre son controle par balayage.")


def fig_va_bande() -> str:
    """La bande où la règle s'inverse, et celle de la partie XXII."""
    b = _plate(500, "Vanna · la bande",
               "L'exception à la règle est la bande de courbure de la partie XXII",
               "largeur : sigma carré T")

    js = [3.0 + 6.0 * i for i in range(180)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Les deux largeurs",
               readout="en logarithme")
    ici = [(j, math.log(VA.bande_de_desobeissance(j / AN)[1]
                        / VA.bande_de_desobeissance(j / AN)[0])) for j in js]
    la = [(j, V * V * j / AN) for j in js]
    hi = max(y for _, y in ici) * 1.30
    p1.domain(0.0, js[-1], 0.0, hi)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi, 0.02), lambda v: _num(v, 2), dx=30.0)
    p1.grid_x([0, 250, 500, 750, 1000], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.path(la, "hm7", tip="sigma carré T")
    p1.path(ici, "hm2", dash="5 4", tip="la bande mesurée")
    p1.label(0.0, hi * 0.86, "trait clair : sigma carré T", dx=8, dy=0)
    p1.label(0.0, hi * 0.74, "pointillé sombre : la bande mesurée", dx=8,
             dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce qu'elle vaut sur un tableau",
               readout="% du comptant")
    courbe = [(j, 100.0 * VA.largeur_de_desobeissance(j / AN)) for j in js]
    hi2 = max(y for _, y in courbe) * 1.25
    p2.domain(0.0, js[-1], 0.0, hi2)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2, 4.0), lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([0, 250, 500, 750, 1000], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.path(courbe, "hm5", tip="largeur relative")
    p2.hline(1.0, "lvl")
    p2.label(js[-1], 1.0, "un pour cent : le pas d'une grille de strikes",
             dx=-8, dy=-8, anchor="end")
    p2.dot(30.0, 100.0 * VA.largeur_de_desobeissance(30.0 / AN), "hm5",
           "trente jours", r=4.2)
    p2.label(30.0, 100.0 * VA.largeur_de_desobeissance(30.0 / AN),
             _num(100 * VA.largeur_de_desobeissance(30.0 / AN), 2) + " %",
             dx=10, dy=10)

    b.legend(0.0, 352.0,
             [("hm7", "sigma carré T, à gauche"),
              ("hm2", "la bande mesurée, à gauche", "5 4"),
              ("hm5", "en pour cent du comptant, à droite")],
             step=200.0, kind="line")
    b.annotation(0.0, 376.0,
                 "la règle du guide vaut si et seulement si les deux d ont "
                 "le même signe ; elle échoue entre eux")
    b.annotation(0.0, 392.0,
                 "cette condition est celle de la volga négative : les deux "
                 "guides décrivent le même intervalle sans le savoir")
    b.annotation(0.0, 408.0,
                 "il vaut "
                 + _num(100 * VA.largeur_de_desobeissance(30.0 / AN), 2)
                 + " % du comptant à trente jours, sous le pas d'une grille "
                 "de strikes")

    _source(b, "Le vanna pousse le delta vers un demi tant que les deux d "
               "ont le même signe ; entre eux, le delta est déjà au-dessus "
               "d'un demi et le vanna le pousse plus haut encore. Cette "
               "condition — le produit des deux d négatif — est exactement "
               "celle de la volga négative que la partie XXII avait mesurée "
               "pour un tout autre motif, et le cadre de gauche le vérifie : "
               "la largeur en logarithme vaut sigma carré T dans les deux cas, à "
               "toutes les échéances. Les deux bandes ne sont pas seulement "
               "de même largeur, c'est le même ensemble, la partie XXII "
               "l'ayant publié dans sa forme à taux nul. Le cadre de droite "
               "donne la portée pratique : sous quinze jours, aucun strike "
               "d'une grille au pas d'un pour cent n'y tombe. L'exception "
               "existe et personne ne peut la négocier.")
    return b.render("La largeur de la bande ou la regle s inverse, comparee a "
                    "sigma carre T, et sa portee sur un tableau de strikes.")


def fig_va_relief_bande() -> str:
    """Le relief de la bande, en volatilité et échéance."""
    z = [list(l) for l in VA.surface_desobeissance()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Vanna · le relief de la bande",
               "Là où l'exception devient assez large pour se négocier",
               "hauteur : % du comptant")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_pct(v, 0) for v in VA.SURF_VOL],
             col_labels=[_num(j, 0) for j in VA.SURF_ECHEANCE_BANDE],
             z_ticks=[(t, _num(t, 0)) for t in _echine(zlo, zhi)],
             tip="{v:.1f} % du comptant", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : la volatilité · arête droite : l'échéance "
                 "en jours · hauteur : la largeur de la bande")
    b.annotation(0.0, 424.0,
                 "le sol couvre tout ce qui se négocie : la bande y vaut "
                 "moins que le pas d'une grille de strikes")
    b.annotation(0.0, 440.0,
                 "elle ne devient large qu'au fond, à deux ans et soixante "
                 "pour cent de volatilité")

    _source(b, "La hauteur est la largeur de l'intervalle où "
               "la règle du guide s'inverse, en pour cent du comptant. Le "
               "relief est au sol sur presque toute son étendue, et c'est le "
               "résultat : l'exception à la règle existe, elle est exacte, et "
               "elle est plus étroite que le pas d'une grille de strikes "
               "partout où l'on négocie. Elle ne devient un objet qu'au coin "
               "du fond, où deux ans d'échéance rencontrent soixante pour "
               "cent de volatilité — une combinaison qui existe, et sur "
               "laquelle personne ne prend une décision intrajournalière. "
               "Une réfutation qui confirme est un résultat comme un "
               "autre, à condition de la publier chiffrée.")
    return b.render("Relief de la largeur de la bande ou la regle s inverse, "
                    "en volatilite et en echeance.")


# ---------------------------------------------------------------------------
# III. Le déplacement annoncé
# ---------------------------------------------------------------------------


def fig_va_deplacement() -> str:
    """Ce que trente points de volatilité font à un call de vingt deltas."""
    t = 30.0 / AN
    k, exact, lin, v30 = VA.deplacement(t)

    b = _plate(500, "Vanna · le déplacement",
               "Trois nombres pour un seul mouvement, et le guide prend le mauvais",
               "trente jours")

    vols = [0.05 + 0.006 * i for i in range(150)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Le delta contre la volatilité",
               readout="call de vingt deltas")
    courbe = [(v, G.delta_comptant(S, k, v, t, VA.TAUX, VA.DIVIDENDE))
              for v in vols]
    tangente = [(v, VA.DELTA_DEPART + VA.vanna(S, k, VA.VOL_BASSE, t)
                 * (v - VA.VOL_BASSE)) for v in vols
                if VA.DELTA_DEPART + VA.vanna(S, k, VA.VOL_BASSE, t)
                * (v - VA.VOL_BASSE) <= 1.0]
    p1.domain(0.0, vols[-1], 0.0, 1.0)
    p1.frame()
    p1.grid_y([0.0, 0.20, 0.40, 0.60, 0.80, 1.0], lambda v: _num(v, 2),
              dx=30.0)
    p1.grid_x([0.0, 0.25, 0.50, 0.75], lambda v: _pct(v, 0),
              label="volatilité")
    p1.path(tangente, "hm1", dash="2 3", tip="le premier ordre")
    p1.path(courbe, "hm6", tip="la mesure")
    p1.vline(VA.VOL_BASSE, "lvl")
    p1.vline(VA.VOL_HAUTE, "lvl")
    p1.dot(VA.VOL_BASSE, VA.DELTA_DEPART, "hm6", "le départ", r=4.5)
    p1.dot(VA.VOL_HAUTE, exact, "hm6", "la mesure", r=4.5)
    p1.dot(VA.VOL_HAUTE, VA.DELTA_ANNONCE, "hm3", "l annonce", r=4.5)
    p1.label(VA.VOL_HAUTE, exact, "mesuré : " + _num(100 * exact, 0),
             dx=10, dy=-4)
    p1.label(VA.VOL_HAUTE, VA.DELTA_ANNONCE, "annoncé : 30", dx=10, dy=10)
    p1.label(0.0, 0.92, "pointillé : la tangente du vanna", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Le choc qui rend trente deltas",
               readout="points de volatilité")
    js = [7.0 + 8.0 * i for i in range(120)]
    besoin = [(j, 100.0 * (VA.deplacement(j / AN)[3] - VA.VOL_BASSE))
              for j in js]
    annonce = 100.0 * (VA.VOL_HAUTE - VA.VOL_BASSE)
    hi = annonce * 1.12
    p2.domain(0.0, js[-1], 0.0, hi)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi, 5.0), lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([0, 250, 500, 750, 950], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.hline(annonce, "lvl")
    p2.path([(j, annonce) for j in js], "hm1", dash="2 3",
            tip="le choc annoncé")
    p2.path(besoin, "hm4", tip="choc requis")
    p2.label(0.0, annonce, "le choc annoncé : trente points", dx=8, dy=-6)
    p2.dot(30.0, 100.0 * (v30 - VA.VOL_BASSE), "hm4", "trente jours", r=4.5)
    p2.label(30.0, 100.0 * (v30 - VA.VOL_BASSE),
             _num(100 * (v30 - VA.VOL_BASSE), 1) + " points", dx=10, dy=10)

    b.legend(0.0, 352.0,
             [("hm6", "la mesure, à gauche"),
              ("hm1", "le premier ordre, à gauche", "2 3"),
              ("hm3", "le nombre annoncé"),
              ("hm4", "le choc requis, à droite")],
             step=166.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le guide illustre le mécanisme par un nombre : de 15 % à "
                 "45 %, un vingt-deltas en vaut trente environ")
    b.annotation(0.0, 392.0,
                 "la mesure rend " + _num(100 * exact, 0) + ", et la propre "
                 "tangente du guide en rendrait " + _num(100 * lin, 0))
    b.annotation(0.0, 408.0,
                 "trente deltas s'atteignent à " + _pct(v30, 1)
                 + ", soit " + _num(100 * (v30 - VA.VOL_BASSE), 1)
                 + " points de choc et non trente")

    _source(b, "Le cadre de gauche porte les trois nombres au même endroit. "
               "La courbe pleine est la mesure ; la tangente pointillée est "
               "ce que la formule du guide prédit, et elle surestime parce "
               "que le vanna décroît vite quand la volatilité monte ; le "
               "point isolé est le nombre publié. Il ne coïncide avec "
               "aucun des deux. Le cadre de droite donne le chiffre juste à "
               "toutes les échéances : le choc de volatilité qui porte "
               "réellement un vingt-deltas à trente vaut moins d'un tiers de "
               "celui que le guide annonce. L'effet qu'il décrit est donc "
               "plus grand que ce qu'il en dit, et c'est la seconde fois "
               "de la série qu'un guide se sous-estime.")
    return b.render("Le delta d un call de vingt deltas contre la "
                    "volatilite, et le choc qui le porte a trente deltas.")


# ---------------------------------------------------------------------------
# IV. Le pic, et la fenêtre
# ---------------------------------------------------------------------------


def fig_va_pic() -> str:
    """Le pic migre, et la fenêtre du guide le perd."""
    b = _plate(510, "Vanna · le pic",
               "Ce que la planche du guide montre est sa fenêtre, pas le vanna",
               "fenêtre 0,80–1,20")

    ms = [0.40 + 0.004 * i for i in range(240)]
    p1 = Panel(b, PX1, 92, PW, 214, title="L'arête et la fenêtre",
               readout="module du vanna")
    series = [("hm7", "", 30.0), ("hm5", "6 3", 180.0), ("hm3", "2 3", 730.0),
              ("hm1", "1 4", 1825.0)]
    courbes = [(cls, dash, j, [(m, abs(_va(m, j))) for m in ms])
               for cls, dash, j in series]
    hi = max(y for _, _, _, c in courbes for _, y in c) * 1.30
    p1.domain(ms[0], ms[-1], 0.0, hi)
    p1.frame()
    p1.band_x(VA.FENETRE[0], VA.FENETRE[1], "band")
    p1.grid_y(_ticks(0.0, hi, 0.4), lambda v: _num(v, 1), dx=26.0)
    p1.grid_x([0.5, 0.7, 0.9, 1.1, 1.3], lambda v: _num(v, 1),
              label="spot sur strike")
    for cls, dash, j, c in courbes:
        p1.path(c, cls, dash=dash, tip=_num(j, 0) + " jours")
    for cls, dash, j in series:
        t = j / AN
        p1.dot(VA.moneyness_du_pic(t), abs(VA.vanna_du_pic(t)), cls,
               "le pic", r=3.8)
    p1.label(VA.FENETRE[0], hi * 0.90, "la fenêtre du guide", dx=6, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Le pic, vu et non vu",
               readout="module du vanna")
    js = [10.0 + 20.0 * i for i in range(120)]
    vrai = [(j / AN, abs(VA.vanna_du_pic(j / AN))) for j in js]
    vu = [(j / AN, VA.vanna_max_fenetre(j / AN, V, 600)) for j in js]
    hi2 = max(y for _, y in vrai) * 1.25
    p2.domain(0.0, js[-1] / AN, 0.0, hi2)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2, 0.3), lambda v: _num(v, 1), dx=26.0)
    p2.grid_x([0, 2, 4, 6], lambda v: _num(v, 0),
              label="années à l'échéance")
    p2.path(vrai, "hm6", tip="le vrai maximum")
    p2.path(vu, "hm2", dash="5 4", tip="vu par la fenêtre")
    p2.label(js[-1] / AN, vrai[-1][1], "le vrai maximum", dx=-8, dy=-8,
             anchor="end")
    p2.label(js[-1] / AN, vu[-1][1], "vu par la fenêtre", dx=-8, dy=14,
             anchor="end")

    b.legend(0.0, 362.0,
             [("hm7", "trente jours"), ("hm5", "six mois", "6 3"),
              ("hm3", "deux ans", "2 3"), ("hm1", "cinq ans", "1 4")],
             step=166.0, kind="line")
    b.annotation(0.0, 386.0,
                 "le lieu du pic est en forme fermée, et c'est la même "
                 "racine que le pic du charm de la partie XX")
    b.annotation(0.0, 402.0,
                 "il se tient à un delta presque constant — "
                 + _num(100 * VA.delta_du_pic(1.0 / AN), 0) + " % à un jour, "
                 + _num(100 * VA.delta_du_pic(5.0), 0) + " % à cinq ans")
    b.annotation(0.0, 418.0,
                 "le maximum croît de bout en bout ; ce qui décroît est ce "
                 "que la fenêtre laisse voir")

    _source(b, "La bande pâle du cadre de gauche est la fenêtre de moneyness "
               "que la planche du guide fixe. L'arête du vanna la traverse "
               "aux courtes échéances puis en sort par la gauche, parce "
               "qu'elle suit un delta presque constant et s'éloigne donc de "
               "la monnaie comme la racine du temps. Le cadre de droite "
               "sépare les deux lectures : le vrai maximum monte sans "
               "s'arrêter, celui qu'on voit à travers la fenêtre passe par "
               "une bosse et redescend. « Aux échéances intermédiaires » "
               "décrit la seconde courbe, et le guide la présente comme une "
               "propriété de la première. La bande est peinte avant les "
               "tracés : un fond posé après recouvrirait ce qu'il commente, "
               "et ce dépôt a déjà payé pour cette faute.")
    return b.render("Le module du vanna contre la moneyness a quatre "
                    "echeances, et le maximum vrai contre celui que la "
                    "fenetre du guide laisse voir.")


# ---------------------------------------------------------------------------
# V. Le mauvais grec
# ---------------------------------------------------------------------------


def fig_va_grec() -> str:
    """Les quatre deltas, et celui que le guide écrit."""
    t = VA.JOURS_PEAU / AN
    b = _plate(500, "Vanna · le delta effectif",
               "La correction de peau porte le véga, et le guide écrit le vanna",
               _num(VA.JOURS_PEAU, 0) + " jours")

    spots = [84.0 + 0.25 * i for i in range(129)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Les quatre lectures du delta",
               readout="delta d'un call")
    bs = [(s, G.delta_comptant(s, S, VA.peau(s), t, VA.TAUX, VA.DIVIDENDE))
          for s in spots]
    vrai = [(s, VA.delta_reevalue(s, S, t)) for s in spots]
    pv = [(s, VA.delta_par_vega(s, S, t)) for s in spots]
    pa = [(s, VA.delta_par_vanna(s, S, t)) for s in spots]
    p1.domain(spots[0], spots[-1], 0.0, 1.0)
    p1.frame()
    p1.grid_y([0.0, 0.25, 0.50, 0.75, 1.0], lambda v: _num(v, 2), dx=30.0)
    p1.grid_x([85, 95, 105, 115], lambda v: _num(v, 0), label="comptant")
    p1.path(pv, "hm7", tip="avec le véga")
    p1.path(vrai, "hm2", dash="5 4", tip="la réévaluation")
    p1.path(bs, "hm4", dash="2 3", tip="le delta de la formule")
    p1.path(pa, "hm5", dash="1 4", tip="la formule du guide")
    p1.label(spots[0], 0.97, "en bas, confondues : la correction au véga",
             dx=8, dy=0)
    p1.label(spots[0], 0.90, "et la réévaluation complète", dx=8, dy=0)
    p1.label(spots[0], 0.80, "en haut, confondues : le delta nu", dx=8, dy=0)
    p1.label(spots[0], 0.73, "et la formule du guide", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="La part de la correction captée",
               readout="pour cent")
    part = [(s, 100.0 * (VA.delta_par_vanna(s, S, t)
                         - G.delta_comptant(s, S, VA.peau(s), t, VA.TAUX,
                                            VA.DIVIDENDE))
             / (VA.delta_reevalue(s, S, t)
                - G.delta_comptant(s, S, VA.peau(s), t, VA.TAUX,
                                   VA.DIVIDENDE)))
            for s in spots]
    ylo = min(y for _, y in part) * 1.35
    yhi = max(y for _, y in part) * 1.60
    p2.domain(spots[0], spots[-1], ylo, max(yhi, 12.0))
    p2.frame()
    p2.grid_y(_ticks(ylo, max(yhi, 12.0), 5.0), lambda v: _signed(v, 0),
              dx=30.0)
    p2.grid_x([85, 95, 105, 115], lambda v: _num(v, 0), label="comptant")
    p2.hline(0.0, "lvl")
    p2.path(part, "hm5", tip="part captée")
    p2.label(spots[0], max(yhi, 12.0) * 0.70,
             "la correction juste vaudrait cent,", dx=8, dy=0)
    p2.label(spots[0], max(yhi, 12.0) * 0.52,
             "très au-dessus de ce cadre", dx=8, dy=0)
    p2.label(spots[-1], part[-1][1], "elle change de signe", dx=-8, dy=-8,
             anchor="end")

    b.legend(0.0, 352.0,
             [("hm7", "avec le véga"), ("hm2", "la réévaluation", "5 4"),
              ("hm4", "le delta nu", "2 3"),
              ("hm5", "la formule du guide", "1 4")],
             step=166.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le membre de droite du guide n'est pas un delta : ses deux "
                 "facteurs donnent un inverse de point")
    b.annotation(0.0, 392.0,
                 "la correction juste porte le véga, et elle reproduit la "
                 "réévaluation à la quatrième décimale")
    b.annotation(0.0, 408.0,
                 "la formule du guide en capte "
                 + _num(100 * (VA.delta_par_vanna(S, S, t)
                               - G.delta_comptant(S, S, VA.peau(S), t,
                                                  VA.TAUX, VA.DIVIDENDE))
                        / (VA.delta_reevalue(S, S, t)
                           - G.delta_comptant(S, S, VA.peau(S), t, VA.TAUX,
                                              VA.DIVIDENDE)), 2)
                 + " % au comptant de référence")

    _source(b, "Quatre courbes, et deux se superposent : la correction au "
               "véga et la réévaluation complète le long de la peau. C'est "
               "le résultat du cadre, et c'est pour cela que le contrôle "
               "passe dessous en trait clair, la référence par-dessus en "
               "pointillé sombre — l'ordre inverse effacerait ce qu'il faut "
               "voir. Les deux autres courbes sont le delta nu et la formule "
               "du guide, qui reste collée à lui. Le cadre de droite dit de "
               "combien : la formule capte quelques centièmes de pour cent "
               "de la correction, et elle change de signe au-dessus de "
               "la monnaie, là où le vanna change de signe. Elle ne corrige "
               "donc pas trop peu, elle corrige dans la mauvaise direction "
               "sur la moitié du domaine.")
    return b.render("Les quatre lectures du delta le long de la peau, et la "
                    "part de la correction que la formule du guide capte.")


def fig_va_gamma() -> str:
    """Le grec du guide est le bon, mais c'est le gamma qu'il corrige."""
    t = VA.JOURS_PEAU / AN
    b = _plate(490, "Vanna · le gamma effectif",
               "Le bon grec, dans la bonne équation",
               "la correction complète du gamma")

    spots = [86.0 + 0.5 * i for i in range(57)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Le gamma le long de la peau",
               readout="par point d'indice")
    vrai = [(s, VA.gamma_reevalue(s, S, t)) for s in spots]
    nu = [(s, VA.gamma_bs(s, S, VA.peau(s), t)) for s in spots]
    corr = [(s, VA.gamma_par_vanna(s, S, t)) for s in spots]
    hi = max(y for _, y in nu) * 1.30
    p1.domain(spots[0], spots[-1], 0.0, hi)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi, 0.01), lambda v: _num(v, 3), dx=34.0)
    p1.grid_x([90, 100, 110], lambda v: _num(v, 0), label="comptant")
    p1.path(corr, "hm7", tip="la correction complète")
    p1.path(vrai, "hm2", dash="5 4", tip="la réévaluation")
    p1.path(nu, "hm4", dash="2 3", tip="le gamma nu")
    p1.label(spots[0], hi * 0.90, "trait clair : la correction complète",
             dx=8, dy=0)
    p1.label(spots[0], hi * 0.80, "pointillé sombre : la réévaluation",
             dx=8, dy=0)
    p1.label(spots[0], hi * 0.70, "tirets : le gamma nu", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce que chaque terme apporte",
               readout="écart à la réévaluation")
    p = VA.pente_de_peau()
    sans = [(s, VA.gamma_bs(s, S, VA.peau(s), t) - VA.gamma_reevalue(s, S, t))
            for s in spots]
    demi = [(s, VA.gamma_bs(s, S, VA.peau(s), t)
             + VA.vanna(s, S, VA.peau(s), t) * p - VA.gamma_reevalue(s, S, t))
            for s in spots]
    deux = [(s, VA.gamma_bs(s, S, VA.peau(s), t)
             + 2.0 * VA.vanna(s, S, VA.peau(s), t) * p
             - VA.gamma_reevalue(s, S, t)) for s in spots]
    ylo = min(y for _, y in sans) * 1.35
    yhi = max(y for _, y in sans) * 1.35
    p2.domain(spots[0], spots[-1], ylo, yhi)
    p2.frame()
    p2.grid_y(_ticks(ylo, yhi, 0.004), lambda v: _signed(v, 3), dx=34.0)
    p2.grid_x([90, 100, 110], lambda v: _num(v, 0), label="comptant")
    p2.hline(0.0, "lvl")
    p2.path(sans, "hm6", tip="sans correction")
    p2.path(demi, "hm3", dash="6 3", tip="avec un seul vanna")
    p2.path(deux, "hm1", dash="1 4", tip="avec deux vannas")
    p2.label(spots[0], ylo * 0.72, "plus on ajoute, plus on tombe sur zéro",
             dx=8, dy=0)

    b.legend(0.0, 342.0,
             [("hm6", "sans correction, à droite"),
              ("hm3", "un seul vanna", "6 3"),
              ("hm1", "deux vannas", "1 4"),
              ("hm7", "avec la volga, à gauche")],
             step=166.0, kind="line")
    b.annotation(0.0, 366.0,
                 "dériver la correction du delta donne celle du gamma, et le "
                 "vanna y entre avec un facteur deux")
    b.annotation(0.0, 382.0,
                 "le terme de volga referme l'écart : la correction complète "
                 "reproduit la réévaluation à la sixième décimale")
    b.annotation(0.0, 398.0,
                 "le guide a pris le bon grec et l'a mis dans la mauvaise "
                 "équation, et sa figure ne le signale pas")

    _source(b, "Le vanna entre bien dans une correction de peau, mais dans "
               "celle du gamma. Le cadre de droite le montre terme par "
               "terme : sans correction l'écart à la réévaluation est "
               "franc, avec un seul vanna il se réduit de moitié, avec deux "
               "il s'approche, et le terme de volga — celui de la partie "
               "XXII — le referme. Le facteur deux n'est pas un détail : il "
               "vient de ce que la peau entre à la fois par le delta et par "
               "le véga, et c'est lui qui manque à la formule du guide, en "
               "plus du grec. Un code juste et une figure fausse, ou "
               "l'inverse : c'est le mode de défaillance que ce dépôt "
               "connaît le mieux, et il ne se voit qu'en calculant les "
               "deux.")
    return b.render("Le gamma le long de la peau contre sa reevaluation, et "
                    "l apport de chaque terme de la correction.")


def fig_va_relief_peau() -> str:
    """Le relief de la correction de peau."""
    z = [list(l) for l in VA.surface_peau()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Vanna · le relief de la correction",
               "Ce qu'un livre couvert au delta nu ignore",
               "hauteur : deltas")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(1000 * abs(p), 1) for p in VA.SURF_PENTE],
             col_labels=[_num(j, 0) for j in VA.SURF_ECHEANCE_PEAU],
             z_ticks=[(t, _num(t, 2)) for t in _echine(zlo, zhi)],
             tip="{v:.3f} delta", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : la pente de la peau, en millièmes de "
                 "volatilité par point · arête droite : l'échéance en jours")
    b.annotation(0.0, 424.0,
                 "hauteur : le delta que la peau ajoute, et que le delta nu "
                 "ne porte pas")
    b.annotation(0.0, 440.0,
                 "il croît avec la pente et avec la racine du temps, donc "
                 "aucune coupe n'est plate")

    _source(b, "La hauteur est le terme de véga fois la pente de la peau, "
               "c'est-à-dire l'écart entre le delta qu'un modèle à "
               "volatilité constante affiche et celui qu'une réévaluation "
               "rend. C'est un delta entier, sur une seule option, et il "
               "croît des deux côtés : avec la pente de la peau, qui est le "
               "moteur, et avec la racine de l'échéance, qui est le véga. "
               "Aux échéances courtes il est petit et un livre "
               "intrajournalier peut l'ignorer ; au fond du relief il "
               "dépasse le tiers d'un delta, et un livre couvert au delta nu "
               "y est court d'un tiers de contrat par option, ce qu'il "
               "découvre en baisse.")
    return b.render("Relief de la correction de peau du delta, en pente de "
                    "peau et en echeance.")


# ---------------------------------------------------------------------------
# VI. Le témoin, et l'agrégation
# ---------------------------------------------------------------------------


def fig_va_temoin() -> str:
    """Le contrôle apparié en distance, rejoué pour le vanna."""
    b = _plate(500, "Vanna · le témoin",
               "Le seul des six guides à publier le protocole qui l'aurait réfuté",
               "témoin apparié en distance")

    ds = [0.0005 + 0.00008 * i for i in range(300)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Ce que la distance décide",
               readout="pour cent")
    touche = [(100 * d, 100.0 * nv.taux_de_touche(d * q.INDEX_LEVEL))
              for d in ds]
    reussite = [(100 * d, 100.0 * nv.taux_de_reussite_ferme(
        d * q.INDEX_LEVEL, q.RR_REF * d * q.INDEX_LEVEL)) for d in ds]
    p1.domain(0.0, 100 * ds[-1], 0.0, 108.0)
    p1.frame()
    p1.grid_y([0, 25, 50, 75, 100], lambda v: _num(v, 0) + " %", dx=30.0)
    p1.grid_x([0.0, 0.8, 1.6, 2.4], lambda v: _num(v, 1),
              label="distance à l'ouverture (%)")
    p1.path(touche, "hm6", tip="taux de touche")
    p1.path(reussite, "hm2", dash="5 4", tip="taux de réussite")
    p1.label(0.4, 92.0, "le taux de touche : il ne dit que la distance",
             dx=0, dy=0)
    p1.label(100 * ds[-1], 4.8, "le taux de réussite : constant", dx=-8,
             dy=-8, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce qu'il faudrait pour le battre",
               readout="touches requises")
    pts = [(100 * d, math.log10(nv.touches_requises(
        VA.FRICTION / (d * q.INDEX_LEVEL)))) for d in ds]
    ylo = min(y for _, y in pts) - 0.3
    yhi = max(y for _, y in pts) + 0.3
    p2.domain(0.0, 100 * ds[-1], ylo, yhi)
    p2.frame()
    p2.grid_y([v for v in range(int(math.ceil(ylo)), int(math.floor(yhi)) + 1)],
              lambda v: _dec(10.0 ** v), dx=30.0)
    p2.grid_x([0.0, 0.8, 1.6, 2.4], lambda v: _num(v, 1),
              label="distance à l'ouverture (%)")
    p2.path(pts, "hm4", tip="touches requises")
    p2.dot(0.5, math.log10(nv.touches_requises(
        VA.FRICTION / (0.005 * q.INDEX_LEVEL))), "hm4", "un demi pour cent",
        r=4.5)
    p2.label(0.5, math.log10(nv.touches_requises(
        VA.FRICTION / (0.005 * q.INDEX_LEVEL))),
        _num(nv.touches_requises(VA.FRICTION / (0.005 * q.INDEX_LEVEL)), 0),
        dx=10, dy=-4)

    b.legend(0.0, 352.0,
             [("hm6", "taux de touche, à gauche"),
              ("hm2", "taux de réussite, à gauche", "5 4"),
              ("hm4", "touches requises, à droite")],
             step=200.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le guide dit que ses niveaux de vanna agrégé n'ont pas "
                 "battu un témoin placé à la même distance de l'ouverture")
    b.annotation(0.0, 392.0,
                 "le taux de touche ne dit que la distance, et le taux de "
                 "réussite vaut un sur un plus le rapport, à toute distance")
    b.annotation(0.0, 408.0,
                 "un niveau ne bat donc son témoin qu'en déplaçant la "
                 "dérive, et l'échantillon croît comme le carré de la "
                 "distance")

    _source(b, "C'est le contrôle que la partie XIX avait dû ajouter au "
               "guide du gamma, et celui-ci le produit de lui-même. Les deux "
               "courbes de gauche disent pourquoi il est le bon : le taux de "
               "touche est celui du principe de réflexion et ne dépend que "
               "de la distance, donc deux niveaux à la même distance sont "
               "touchés aussi souvent ; et le taux de réussite d'un trade "
               "pris sur le niveau est constant, parce qu'il ne dépend que "
               "de la géométrie de sortie. Un niveau agrégé ne peut battre "
               "son témoin qu'en déplaçant la dérive du prix, et la courbe "
               "de droite dit à quel prix cela se démontre. Le résultat "
               "négatif du guide n'est pas une surprise à expliquer : c'est "
               "ce que la loi nulle prédisait avant l'expérience.")
    return b.render("Le taux de touche et le taux de reussite contre la "
                    "distance, et les touches requises pour battre le "
                    "temoin.")


def fig_va_agregation() -> str:
    """Le profil agrégé, ses lignes, et le décompte sous signes inconnus."""
    b = _plate(510, "Vanna · l'agrégation",
               "Le gamma agrégé échoue par absence, le vanna par abondance",
               "chaîne à sept jours")

    ms = [0.86 + 0.002 * i for i in range(141)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Les deux profils agrégés",
               readout="ramenés à leur maximum")
    vx = [(m, VA.vex(m * q.INDEX_LEVEL)) for m in ms]
    gx = [(m, nv.gex(m * q.INDEX_LEVEL)) for m in ms]
    nv_max = max(abs(y) for _, y in vx)
    ng_max = max(abs(y) for _, y in gx)
    vxn = [(m, y / nv_max) for m, y in vx]
    gxn = [(m, y / ng_max) for m, y in gx]
    p1.domain(ms[0], ms[-1], -1.15, 1.15)
    p1.frame()
    p1.grid_y([-1.0, -0.5, 0.0, 0.5, 1.0], lambda v: _signed(v, 1), dx=30.0)
    p1.grid_x([0.88, 0.94, 1.00, 1.06, 1.12], lambda v: _num(v, 2),
              label="spot sur strike")
    p1.hline(0.0, "lvl")
    p1.path(gxn, "hm2", dash="5 4", tip="le gamma agrégé")
    p1.path(vxn, "hm6", tip="le vanna agrégé")
    for x in VA.lignes_de_vex():
        p1.dot(x / q.INDEX_LEVEL, 0.0, "hm6", "une ligne de vanna", r=4.2)
    p1.dot(nv.bascule() / q.INDEX_LEVEL, 0.0, "hm2", "la bascule de gamma",
           r=4.2)
    p1.label(ms[0], 1.02, "trait plein : le vanna, deux traversées", dx=8,
             dy=0)
    p1.label(ms[0], 0.88, "pointillé : le gamma, une seule", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Combien de lignes, signe inconnu",
               readout="part des tirages")
    hist, _, _, _ = VA.compte_de_lignes(0.0, 0.0)
    haut = max(hist) / VA.N_TIRAGES * 1.35
    p2.domain(-0.6, 3.6, 0.0, 100.0 * haut)
    p2.frame()
    p2.grid_y(_ticks(0.0, 100.0 * haut, 20.0), lambda v: _num(v, 0) + " %",
              dx=30.0)
    etiquettes = ("aucune", "une", "deux", "trois ou plus")
    for i, n in enumerate(hist):
        part = 100.0 * n / VA.N_TIRAGES
        p2.vbar(i, 0.0, part, 46.0, "hm7" if i == 0 else "hm4",
                tip=etiquettes[i])
        p2.label(i, part, _num(part, 0) + " %", dx=0, dy=-8, anchor="middle")
        p2.label(i, 0.0, etiquettes[i], dx=0, dy=16, anchor="middle")

    b.legend(0.0, 362.0,
             [("hm6", "le vanna agrégé, à gauche"),
              ("hm2", "le gamma agrégé, à gauche", "5 4"),
              ("hm7", "aucune ligne"), ("hm4", "une ou plusieurs")],
             step=166.0, kind="line")
    b.annotation(0.0, 386.0,
                 "sous l'hypothèse de signe du guide, le profil de vanna "
                 "traverse zéro deux fois quand celui de gamma en traverse "
                 "une")
    b.annotation(0.0, 402.0,
                 "le gamma est positif à tous les strikes ; le vanna change "
                 "de signe en chacun, donc l'agrégat en a plusieurs")
    b.annotation(0.0, 418.0,
                 "signe inconnu, il y en a presque toujours et souvent "
                 "trois ou plus : le niveau ne manque pas, il se choisit")

    _source(b, "Les deux profils sont ramenés à leur maximum, parce que "
               "leurs unités n'ont rien à voir et que seul le lieu des "
               "traversées est en question. Le gamma agrégé est une bosse "
               "unique et il traverse zéro une fois : c'est la bascule que "
               "la partie XIX a mesurée. Le vanna agrégé en traverse deux, "
               "parce que le vanna change de signe en chaque strike quand le "
               "gamma n'en change jamais. « La » ligne de vanna n'est donc "
               "pas un objet défini, et le premier jet de ce module est "
               "tombé dans le trou que cela creuse : sa bissection a rendu "
               "« pas de ligne » là où il y en avait deux, les deux bouts de "
               "la boîte étant du même signe. Le cadre de droite ajoute "
               "l'ignorance du signe, et le résultat est l'inverse de celui "
               "de la partie XIX : le gamma y échouait par absence, le vanna "
               "échoue par abondance.")
    return b.render("Les profils agreges de vanna et de gamma ramenes a leur "
                    "maximum, et le decompte des lignes sous signe inconnu.")


def fig_va_relief_retournement() -> str:
    """Le relief de la volatilité du retournement."""
    z = [list(l) for l in VA.surface_retournement()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Vanna · le relief du retournement",
               "Où le delta cesse de descendre, et où c'est atteignable",
               "hauteur : % de volatilité")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(m, 2) for m in VA.SURF_MONEYNESS_RET],
             col_labels=[_num(j, 0) for j in VA.SURF_ECHEANCE_RET],
             z_ticks=[(t, _num(t, 0)) for t in _echine(zlo, zhi)],
             tip="{v:.0f} % de volatilite", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : le spot sur le strike · arête droite : "
                 "l'échéance en jours · hauteur : la volatilité du "
                 "retournement")
    b.annotation(0.0, 424.0,
                 "elle décroît comme la racine de l'échéance, donc le "
                 "retournement est un fait des options longues")
    b.annotation(0.0, 440.0,
                 "au coin proche, il tombe sous trente pour cent : la règle "
                 "du guide y est fausse dans un régime ordinaire")

    _source(b, "La hauteur est la volatilité à laquelle le delta d'une "
               "option dans la monnaie cesse de descendre et se met à "
               "remonter vers un. Elle vaut la racine de deux fois le "
               "logarithme de la monnaie divisé par l'échéance, donc elle "
               "monte avec la monnaie et descend comme la racine du temps. "
               "Le coin du fond est celui d'une option très dans la monnaie "
               "et très courte, où le retournement demande une volatilité "
               "que rien n'atteint. Le coin proche est le fait de la "
               "section : sur une option longue et peu dans la monnaie, il "
               "tombe sous trente pour cent, c'est-à-dire dans un régime "
               "que l'indice traverse plusieurs fois par décennie. La règle "
               "du guide n'y est pas approximative, elle y est fausse.")
    return b.render("Relief de la volatilite du retournement du delta, en "
                    "moneyness et en echeance.")


# ---------------------------------------------------------------------------
# VII. Le décompte
# ---------------------------------------------------------------------------


def fig_va_reste() -> str:
    """Le décompte des huit affirmations, et le cumul des six parties."""
    aff = VA.affirmations()
    compte = VA.compte_par_grandeur()
    ordre = sorted(compte, key=lambda g: (-compte[g], g))
    fam = VA.familles()
    total = sum(n for _, n in fam)

    b = _plate(470, "Vanna · le décompte",
               "Quarante-trois affirmations, et aucune ne donne un sens",
               _num(len(aff), 0) + " ici")

    p1 = Panel(b, PX1, 92, PW, 214, title="Ce qu'elles déplacent",
               readout="affirmations")
    lignes = list(ordre) + [g for g in ("l'horloge", "la direction")
                            if g not in ordre]
    p1.domain(0.0, 6.0, -0.6, len(lignes) - 0.4)
    p1.frame()
    p1.grid_x(_ticks(0.0, 6.0, 2.0), lambda v: _num(v, 0))
    for i, g in enumerate(lignes):
        y = len(lignes) - 1 - i
        n = compte.get(g, 0)
        cls = {"la direction": "hm7", "rien": "hm1"}.get(g, "hm5")
        if n:
            p1.hbar(y, 0.0, n, 13.0, cls, tip=g + " : " + _num(n, 0))
        p1.label(0.0, y + 0.34, g, dx=4, dy=0)
        p1.label(max(n, 0.0), y, _num(n, 0), dx=7, dy=4)

    p2 = Panel(b, PX2, 92, PW, 214, title="Les six parties",
               readout="affirmations")
    haut = max(n for _, n in fam) * 1.35
    p2.domain(0.0, haut, -0.6, len(fam) - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, haut, 3.0), lambda v: _num(v, 0))
    for i, (nom, n) in enumerate(fam):
        y = len(fam) - 1 - i
        p2.hbar(y, 0.0, n, 10.0, "hm3", tip=nom)
        p2.label(0.0, y + 0.30, nom, dx=4, dy=0)
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
                 + " ne déplacent rien, aucune l'horloge")
    b.annotation(0.0, 392.0,
                 "la barre de la direction est vide pour la deuxième partie "
                 "d'options consécutive")
    b.annotation(0.0, 408.0,
                 "sur les " + _num(total, 0) + " affirmations des six "
                 "parties, aucune ne donne un sens")

    _source(b, "Ce guide est le meilleur des six sur le point qui compte "
               "plus que ses formules : il publie le résultat de son propre "
               "test, contre un témoin apparié en distance, et il ne trouve "
               "rien. C'est le contrôle que la partie XIX avait dû ajouter "
               "au guide du gamma, et qu'aucun des quatre autres n'a "
               "produit. Le décompte, lui, ne change pas de forme : cinq "
               "affirmations déplacent le risque, trois n'en déplacent "
               "aucun, et la colonne de la direction reste vide. La série "
               "d'options se ferme donc là où la partie IV l'avait posée — "
               "ce qui se récupère d'un document extérieur est une méthode "
               "de lecture, jamais une direction — et ce sixième document "
               "rend en plus la seule chose qui vaille dans une note de "
               "marché : le protocole qui l'aurait réfutée, et son "
               "résultat.")
    return b.render("Le decompte des affirmations par ce qu elles deplacent, "
                    "et le cumul des six parties d options.")


def render_all() -> dict[str, str]:
    """Les quinze planches, dans l'ordre du document."""
    return {
        "vadeux": fig_va_deux(),
        "vazero": fig_va_zero(),
        "vareliefv": fig_va_relief_vanna(),
        "varetournement": fig_va_retournement(),
        "vabande": fig_va_bande(),
        "vareliefb": fig_va_relief_bande(),
        "vadeplacement": fig_va_deplacement(),
        "vapic": fig_va_pic(),
        "vagrec": fig_va_grec(),
        "vagamma": fig_va_gamma(),
        "vareliefp": fig_va_relief_peau(),
        "vatemoin": fig_va_temoin(),
        "vaagregation": fig_va_agregation(),
        "vareliefr": fig_va_relief_retournement(),
        "vareste": fig_va_reste(),
    }
