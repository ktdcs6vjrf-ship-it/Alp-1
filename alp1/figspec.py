"""Les planches de « ce qu'une position coûte, dans les deux sens ».

Quatorze planches, dix à plat et quatre en relief. La cinquième porte le seul
réglage que ce document recommande explicitement, et son cadre est borné à la
séance parce que l'affirmation l'est.

Comme les modules d'options qui précèdent, celui-ci importe ses fonctions
d'échine, de graduation et de pourcentage de `fignv`.
"""

from __future__ import annotations

import math

from . import concepts as C
from . import seuil
from . import speculation as SP
from .figdisc import W, _plate, _source, _surface
from .fignv import _echine, _pct, _ticks
from .figterm import Board, Panel, _num, _signed

PW = (W - 74.0) / 2.0 - 30.0
PX1 = 74.0
PX2 = 74.0 + (W - 74.0) / 2.0

HAUTE = SP.DERIVES[-1]
BASSE = SP.DERIVES[1]


def _stops(n: int = 120) -> list[float]:
    """Une grille de stops en pour cent, du plus serré au plus large."""
    lo, hi = math.log(0.005), math.log(0.30)
    return [math.exp(lo + (hi - lo) * i / n) for i in range(n + 1)]


# ---------------------------------------------------------------------------
# I. Les trois issues, et la portée de la séance
# ---------------------------------------------------------------------------


def fig_spec_issues() -> str:
    """Ce qu'une position rend vraiment, séance comprise."""
    b = _plate(500, "Spéculation · les trois issues",
               "Une position a trois fins, et la troisième ne se déclare pas",
               "à dérive nulle")

    p1 = Panel(b, PX1, 92, PW, 214, title="Les trois issues par géométrie",
               readout="% des positions")
    p1.domain(0.0, 100.0, -0.6, len(SP.GEOMETRIES) - 0.4)
    p1.frame()
    p1.grid_x([0, 25, 50, 75, 100], lambda v: _num(v, 0))
    for i, pct in enumerate(SP.GEOMETRIES):
        y = len(SP.GEOMETRIES) - 1 - i
        it = SP.lire(pct)
        a = 100.0 * it.p_objectif
        c = 100.0 * (it.p_objectif + it.p_stop)
        p1.hbar(y, 0.0, a, 13.0, "hm7", tip="objectif")
        p1.hbar(y, a, c, 13.0, "hm3", tip="stop")
        p1.hbar(y, c, 100.0, 13.0, "hm1", tip="ouvert à la clôture")
        p1.label(0.0, y + 0.32, "stop " + _num(pct, 3) + " %", dx=4, dy=0)
        p1.label(100.0, y + 0.32,
                 _pct(it.p_ouvert, 1) + " ouvert", dx=-4, dy=0, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214,
               title="La portée que la séance autorise",
               readout="objectif en σ de séance")
    ss = _stops()
    courbe = [(s, SP.portee_de_seance(s)) for s in ss]
    hi = max(y for _, y in courbe)
    p2.domain(0.0, ss[-1], 0.0, hi * 1.08)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi * 1.08, 4.0), lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([0.1, 0.2, 0.3], lambda v: _num(v, 1) + " %",
              label="largeur du stop")
    p2.hline(1.0, "lvl")
    p2.path(courbe, "hm4", tip="portée de l'objectif")
    p2.label(ss[-1], 1.0, "ce qu'une séance parcourt", dx=-8, dy=-8,
             anchor="end")
    for pct in SP.GEOMETRIES:
        p2.dot(pct, SP.portee_de_seance(pct), "hm4",
               _num(pct, 3) + " %", r=4.5)
    p2.label(SP.GEOMETRIES[2], SP.portee_de_seance(SP.GEOMETRIES[2]),
             _num(SP.portee_de_seance(SP.GEOMETRIES[2]), 2) + " σ", dx=-9,
             dy=6, anchor="end")

    b.legend(0.0, 352.0,
             [("hm7", "objectif atteint"), ("hm3", "stop touché"),
              ("hm1", "ouvert à la clôture"),
              ("hm4", "la portée, à droite")],
             step=150.0)
    b.annotation(0.0, 376.0,
                 "le rapport déclaré est un pour "
                 + _num(SP.RR, 0) + " : au stop élargi, cela demande à la "
                 "séance " + _num(SP.portee_de_seance(SP.GEOMETRIES[2]), 2)
                 + " fois ce qu'elle parcourt")
    b.annotation(0.0, 392.0,
                 "la probabilité d'objectif n'y est pas petite, elle est "
                 "nulle, et la position finit "
                 + _pct(SP.lire(SP.GEOMETRIES[2]).p_ouvert, 1)
                 + " du temps ouverte")
    b.annotation(0.0, 408.0,
                 "au stop déclaré, l'objectif tient dans "
                 + _num(SP.portee_de_seance(SP.GEOMETRIES[0]), 2)
                 + " écart-type et le théorème s'applique exactement")

    _source(b, "Le cadre de gauche est la seule chose qu'un opérateur ait "
               "besoin de savoir avant d'entrer, et c'est celle que la "
               "littérature de dispositif ne donne jamais : une position "
               "n'a pas deux fins mais trois. Le stop et l'objectif sont "
               "déclarés ; la troisième ne l'est pas, et c'est la sortie au "
               "marché parce que la séance se ferme. Elle vaut zéro au stop "
               "déclaré, dont l'objectif est proche, et près d'une position "
               "sur trois au stop élargi. Le cadre de droite dit pourquoi : "
               "l'objectif croît comme le stop, la portée de la séance ne "
               "croît pas du tout, et le rapport déclaré finit par demander "
               "à une séance sept fois ce qu'elle parcourt.")
    return b.render("Les trois issues d une position par geometrie, et la "
                    "portee que la seance autorise.")


def fig_spec_portee() -> str:
    """Le rapport que la séance autorise, contre celui qu'on déclare."""
    b = _plate(500, "Spéculation · le rapport",
               "Le rapport se déclare, mais c'est la séance qui le fixe",
               "à dérive nulle")

    ss = _stops(60)
    p1 = Panel(b, PX1, 92, PW, 214,
               title="Le rapport atteignable", readout="objectif sur risque")
    series = [("hm7", "", 0.10), ("hm5", "6 3", 0.05), ("hm3", "2 3", 0.01)]
    courbes = [(cls, dash, s0,
                [(s, SP.rr_atteignable(s, s0)) for s in ss])
               for cls, dash, s0 in series]
    hi = max(y for _, _, _, c in courbes for _, y in c)
    p1.domain(0.0, ss[-1], 0.0, hi * 1.10)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi * 1.10, 10.0), lambda v: _num(v, 0), dx=26.0)
    p1.grid_x([0.0, 0.1, 0.2, 0.3], lambda v: _num(v, 1) + " %",
              label="largeur du stop")
    p1.hline(SP.RR, "lvl")
    for cls, dash, _s0, c in courbes:
        p1.path(c, cls, dash=dash, tip="rapport atteignable")
    p1.label(ss[-1], SP.RR, "le rapport déclaré", dx=-8, dy=-8,
             anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Ce que le rapport déclaré devient",
               readout="P(objectif)")
    courbe = [(s, 100.0 * SP.lire(s).p_objectif) for s in ss]
    hi2 = max(y for _, y in courbe)
    p2.domain(0.0, ss[-1], 0.0, hi2 * 1.18)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2 * 1.18, 1.0), lambda v: _num(v, 0) + " %",
              dx=30.0)
    p2.grid_x([0.0, 0.1, 0.2, 0.3], lambda v: _num(v, 1) + " %",
              label="largeur du stop")
    p2.path(courbe, "hm4", tip="probabilité d'objectif")
    p2.hline(100.0 / (1.0 + SP.RR), "lvl")
    p2.label(ss[-1], 100.0 / (1.0 + SP.RR),
             "ce que le théorème annonce", dx=-8, dy=-8, anchor="end")
    for pct in SP.GEOMETRIES:
        p2.dot(pct, 100.0 * SP.lire(pct).p_objectif, "hm4",
               _num(pct, 3) + " %", r=4.5)

    b.legend(0.0, 352.0,
             [("hm7", "à P ≥ 10 %"), ("hm5", "à P ≥ 5 %", "6 3"),
              ("hm3", "à P ≥ 1 %", "2 3"),
              ("hm4", "le rapport déclaré, à droite")],
             step=150.0, kind="line")
    b.annotation(0.0, 376.0,
                 "les trois courbes donnent le plus grand rapport dont "
                 "l'objectif garde la probabilité annoncée, séance comprise")
    b.annotation(0.0, 392.0,
                 "à cinq pour cent, le stop élargi n'autorise plus qu'un "
                 "pour " + _num(SP.rr_atteignable(SP.GEOMETRIES[2], 0.05), 1)
                 + " quand le dispositif en déclare un pour "
                 + _num(SP.RR, 0))
    b.annotation(0.0, 408.0,
                 "élargir le stop et garder le rapport sont deux gestes que "
                 "la séance interdit de faire ensemble")

    _source(b, "Élargir le stop divise le seuil de rentabilité par "
               "cinquante-trois, et c'est le résultat de la partie X. Ce "
               "que ces deux cadres ajoutent est que le même geste rend "
               "l'objectif inatteignable si l'on garde le rapport. Les deux "
               "leviers que le dispositif traite comme indépendants sont "
               "liés par une quantité qu'il ne déclare nulle part, la "
               "distance qu'une séance parcourt. Le cadre de droite montre "
               "la conséquence sur la probabilité d'objectif : elle suit le "
               "théorème tant que la portée reste sous un écart-type, puis "
               "elle décroche et tombe à zéro. La ligne horizontale est ce "
               "que le théorème annonce, et la distance entre la courbe et "
               "la ligne est exactement ce que la séance reprend.")
    return b.render("Le rapport que la seance autorise contre la largeur du "
                    "stop, et ce que le rapport declare devient.")


def fig_spec_relief_survie() -> str:
    """La part du théorème qui survit à la séance."""
    z = [list(l) for l in SP.surface_survie()]
    vals = [v for l in z for v in l]

    b = _plate(486, "Spéculation · le relief de la survie",
               "Où le théorème s'applique encore, et où la séance le reprend",
               "hauteur : part du théorème")

    _surface(b, 0.52 * W, 232.0, z, min(vals), max(vals), cx=42.0, cy=13.0,
             cz=158.0,
             row_labels=[_num(s, 3) + " %" for s in SP.SURF_STOP_CROISSANT],
             col_labels=[_num(r, 0) for r in SP.SURF_RR_CROISSANT],
             z_ticks=[(t, _num(t, 1)) for t in _echine(min(vals), max(vals))],
             tip="{v:.2f}", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : le stop · arête droite : le rapport · "
                 "hauteur : la part du théorème qui survit")
    b.annotation(0.0, 424.0,
                 "elle vaut un sur le plateau du fond, où l'objectif tient "
                 "dans la portée d'une séance")
    b.annotation(0.0, 440.0,
                 _num(sum(1 for l in z for v in l if v > 0.99), 0)
                 + " des " + _num(len(z) * len(z[0]), 0)
                 + " cellules valent un, et "
                 + _num(sum(1 for l in z for v in l if v < 1e-3), 0)
                 + " tombent sous un millième — la falaise est nette")

    _source(b, "La hauteur est la probabilité d'objectif rapportée à ce que "
               "le théorème d'arrêt optionnel annonce. Publier le rapport "
               "plutôt que la probabilité est ce qui rend le relief "
               "lisible : la probabilité brute varie d'un demi à zéro et son "
               "plateau écrase tout le reste, quand le rapport a un plafond "
               "à un et le touche partout où le théorème s'applique. Le "
               "plateau du fond est la région où ce document a raison sans "
               "réserve ; la falaise est l'endroit, et le seul, où il faut "
               "corriger ce qu'il dit. Elle tombe exactement là où "
               "l'objectif franchit la portée d'une séance, et c'est "
               "pourquoi la partie ne recommande pas une géométrie mais une "
               "contrainte entre deux de ses réglages.")
    return b.render("Relief de la part du theoreme qui survit a la seance, "
                    "en largeur de stop et en rapport.")


# ---------------------------------------------------------------------------
# II. Les deux sens
# ---------------------------------------------------------------------------


def fig_spec_sens() -> str:
    """Les deux sens, et ce que la dérive les sépare."""
    b = _plate(500, "Spéculation · les deux sens",
               "À dérive nulle les deux sens sont le même pari, exactement",
               "hausse contre baisse")

    ds = [0.0 + 4.0 * i / 120 for i in range(121)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Les deux sens contre la dérive",
               readout="P(objectif)")
    pct = SP.GEOMETRIES[1]
    haut = [(d, 100.0 * SP.lire(pct, d, 1).p_objectif) for d in ds]
    bas = [(d, 100.0 * SP.lire(pct, d, -1).p_objectif) for d in ds]
    hi = max(y for _, y in haut)
    p1.domain(0.0, ds[-1], 0.0, hi * 1.15)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi * 1.15, 2.0), lambda v: _num(v, 0) + " %",
              dx=30.0)
    p1.grid_x([0, 1, 2, 3, 4], lambda v: _num(v, 0),
              label="dérive (points par heure)")
    p1.band_x(SP.DERIVES[1], SP.DERIVES[2], "wash")
    p1.path(haut, "hm7", tip="à la hausse")
    p1.path(bas, "hm3", dash="5 4", tip="à la baisse")
    p1.label(0.0, 100.0 * SP.lire(pct, 0.0, 1).p_objectif,
             "le même nombre, exactement", dx=8, dy=-8)
    p1.label(ds[-1], hi * 1.02, "le domaine plausible", dx=-8, dy=0,
             anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="L'écart, par géométrie",
               readout="points de taux")
    series = [("hm7", "", SP.GEOMETRIES[0]), ("hm5", "6 3", SP.GEOMETRIES[1]),
              ("hm3", "2 3", SP.GEOMETRIES[2])]
    courbes = [(cls, dash, s,
                [(d, 100.0 * (SP.lire(s, d, 1).p_objectif
                              - SP.lire(s, d, -1).p_objectif)) for d in ds])
               for cls, dash, s in series]
    hi2 = max(y for _, _, _, c in courbes for _, y in c)
    p2.domain(0.0, ds[-1], 0.0, hi2 * 1.20)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2 * 1.20, 5.0), lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([0, 1, 2, 3, 4], lambda v: _num(v, 0),
              label="dérive (points par heure)")
    p2.band_x(SP.DERIVES[1], SP.DERIVES[2], "wash")
    for cls, dash, _s, c in courbes:
        p2.path(c, cls, dash=dash, tip="écart entre les deux sens")
    p2.label(0.0, 0.0, "nul à dérive nulle, aux trois géométries", dx=8,
             dy=-10)

    b.legend(0.0, 352.0,
             [("hm7", "à la hausse"), ("hm3", "à la baisse", "5 4"),
              ("hm5", "stop moyen, à droite", "6 3")],
             step=200.0, kind="line")
    b.annotation(0.0, 376.0,
                 "les deux courbes de gauche partent du même point, et c'est "
                 "exact à la précision machine plutôt qu'approché")
    b.annotation(0.0, 392.0,
                 "tout écart entre les deux sens est donc, par "
                 "construction, la dérive et rien d'autre")
    b.annotation(0.0, 408.0,
                 "dans le domaine plausible il vaut de "
                 + _num(100.0 * (SP.lire(SP.GEOMETRIES[1], BASSE, 1).p_objectif
                                 - SP.lire(SP.GEOMETRIES[1], BASSE, -1)
                                 .p_objectif), 1)
                 + " à "
                 + _num(100.0 * (SP.lire(SP.GEOMETRIES[1], HAUTE, 1).p_objectif
                                 - SP.lire(SP.GEOMETRIES[1], HAUTE, -1)
                                 .p_objectif), 1)
                 + " points de taux au stop moyen")

    _source(b, "La symétrie du cadre de gauche n'est pas une observation, "
               "c'est une identité : le sens d'une position entre dans la "
               "dérive et jamais dans la géométrie, si bien qu'à dérive "
               "nulle les deux paris sont le même objet vu des deux côtés. "
               "C'est ce qui rend tout le reste lisible. Un document qui "
               "publie un taux de réussite directionnel sans publier son "
               "symétrique ne dit rien du marché : il dit sa géométrie. La "
               "bande est le domaine de dérive que la partie X déclare "
               "plausible, et le cadre de droite montre que l'écart y reste "
               "modeste, quelques dizaines de points de taux, quand le "
               "discours de dispositif en promet couramment le double.")
    return b.render("Les deux sens contre la derive, et l ecart entre eux "
                    "par geometrie.")


def fig_spec_optimum() -> str:
    """L'horizon qui sépare le plus les deux sens."""
    b = _plate(510, "Spéculation · l'horizon",
               "Il existe un horizon optimal, et la séance le fixe",
               "à la dérive haute")

    opt = SP.horizon_optimal()
    ts = [2.0 + (SP.SEANCE_MIN - 2.0) * i / 160 for i in range(161)]
    p1 = Panel(b, PX1, 92, PW, 214, title="L'écart contre l'horizon",
               readout="points de taux")
    courbe = [(t, SP.ecart_directionnel(t)) for t in ts]
    hi = max(y for _, y in courbe)
    p1.domain(0.0, ts[-1], 0.0, hi * 1.18)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi * 1.18, 10.0), lambda v: _num(v, 0), dx=26.0)
    p1.grid_x([0, 100, 200, 300], lambda v: _num(v, 0),
              label="horizon de la lecture (minutes)")
    p1.path(courbe, "hm7", tip="écart entre les deux sens")
    p1.vline(opt, "lvl")
    p1.dot(opt, SP.ecart_directionnel(opt), "hm7", "l'optimum", r=4.5)
    p1.label(opt, SP.ecart_directionnel(opt),
             _num(opt, 0) + " min, " + _num(SP.ecart_directionnel(opt), 1)
             + " points", dx=9, dy=4)
    p1.label(0.0, 0.0, "sous cet horizon, la dérive n'a pas le temps", dx=8,
             dy=-10)

    p2 = Panel(b, PX2, 92, PW, 214, title="Pourquoi il tombe là",
               readout="objectif en σ de séance")
    portees = [(t, C.RR_LECTURE * SP.SIGMA_MIN * math.sqrt(t)
                / SP.ECART_SEANCE) for t in ts]
    hi2 = max(y for _, y in portees)
    p2.domain(0.0, ts[-1], 0.0, hi2 * 1.10)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2 * 1.10, 0.5), lambda v: _num(v, 1), dx=26.0)
    p2.grid_x([0, 100, 200, 300], lambda v: _num(v, 0),
              label="horizon de la lecture (minutes)")
    p2.hline(1.0, "lvl")
    p2.path(portees, "hm4", tip="portée de l'objectif")
    p2.vline(opt, "lvl")
    p2.dot(opt, SP.portee_de_l_optimum(), "hm4", "l'optimum", r=4.5)
    p2.label(ts[-1], 1.0, "ce qu'une séance parcourt", dx=-8, dy=-9,
             anchor="end")
    p2.label(opt, SP.portee_de_l_optimum(),
             _num(SP.portee_de_l_optimum(), 3) + " σ", dx=9, dy=10)

    b.legend(0.0, 352.0,
             [("hm7", "l'écart entre les deux sens"),
              ("hm4", "la portée de l'objectif, à droite")],
             step=240.0, kind="line")
    b.annotation(0.0, 376.0,
                 "l'écart passe par un maximum : il vaut "
                 + _num(SP.ecart_directionnel(5.0), 1)
                 + " points à cinq minutes, "
                 + _num(SP.ecart_directionnel(opt), 1) + " au sommet et "
                 + _num(SP.ecart_directionnel(SP.SEANCE_MIN), 1)
                 + " sur la séance entière")
    b.annotation(0.0, 392.0,
                 "le sommet tombe là où l'objectif vaut "
                 + _num(SP.portee_de_l_optimum(), 3)
                 + " écart-type de séance, et les deux verticales sont le "
                 "même horizon")
    b.annotation(0.0, 408.0,
                 "c'est la seule échelle où la dérive dispose de toute la "
                 "séance sans que la séance lui reprenne l'objectif")

    _source(b, "Le compromis a deux côtés et les deux se mesurent. Sous "
               "l'horizon optimal, la dérive n'a pas le temps d'agir : elle "
               "déplace le prix proportionnellement au temps quand le bruit "
               "le déplace comme la racine du temps, et à cinq minutes le "
               "bruit gagne. Au-dessus, l'objectif sort de la portée de la "
               "séance et la position se ferme avant de l'atteindre. Entre "
               "les deux se trouve un maximum, et le cadre de droite dit "
               "où : exactement là où l'objectif vaut un écart-type de "
               "séance. L'affirmation a une frontière, et elle est nommée "
               "plutôt que cachée : au-delà de la séance la position n'est "
               "plus fermée au coup de cloche, la dérive agit plus longtemps "
               "que la volatilité ne s'étale, et l'écart remonte sans "
               "limite. L'optimum est celui d'un opérateur intrajournalier.")
    return b.render("L ecart directionnel contre l horizon de la lecture, et "
                    "la portee qui explique son maximum.")


def fig_spec_relief_ecart() -> str:
    """Le relief de l'écart directionnel."""
    z = [list(l) for l in SP.surface_ecart()]
    vals = [v for l in z for v in l]

    b = _plate(486, "Spéculation · le relief de l'écart",
               "Ce que la dérive sépare les deux sens, et où elle le sépare",
               "hauteur : points de taux")

    _surface(b, 0.52 * W, 232.0, z, min(vals), max(vals), cx=42.0, cy=13.0,
             cz=158.0,
             row_labels=[_num(s, 3) + " %" for s in SP.SURF_STOP_CROISSANT],
             col_labels=[_num(d, 1) for d in SP.SURF_DERIVE],
             z_ticks=[(t, _num(t, 1)) for t in _echine(min(vals), max(vals))],
             tip="{v:.2f}", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : le stop · arête droite : la dérive · "
                 "hauteur : l'écart entre les deux sens")
    b.annotation(0.0, 424.0,
                 "le sol est l'arête de dérive nulle, et il est plat à zéro "
                 "sur toute sa longueur — la symétrie, vue en relief")
    b.annotation(0.0, 440.0,
                 "la crête ne suit pas l'arête du stop le plus large : "
                 "elle culmine à "
                 + _num(SP.SURF_STOP_CROISSANT[
                     max(range(len(z)), key=lambda i: max(z[i]))], 3)
                 + " %")

    _source(b, "Le sol de ce relief est un résultat et non un artefact : "
               "l'arête de dérive nulle est plate à zéro sur toute sa "
               "longueur, quelle que soit la largeur du stop, parce que les "
               "deux sens y sont le même pari. Ce qu'une spéculation "
               "directionnelle achète est la hauteur au-dessus de ce sol, et "
               "elle ne s'achète pas en élargissant le stop indéfiniment : "
               "la crête culmine à une largeur intermédiaire, là où "
               "l'objectif tient encore dans la portée d'une séance. Au-delà "
               "la surface redescend, non parce que la dérive cesse d'agir "
               "mais parce que la séance se ferme avant qu'elle ait agi.")
    return b.render("Relief de l ecart entre les deux sens, en largeur de "
                    "stop et en derive.")


# ---------------------------------------------------------------------------
# III. Les deux routes du seuil
# ---------------------------------------------------------------------------


def fig_spec_routes() -> str:
    """La dérive d'équilibre, par deux routes qui ne s'accordent pas."""
    b = _plate(500, "Spéculation · les deux routes",
               "Le seuil se calcule de deux façons, et l'une oublie la séance",
               "dérive d'équilibre")

    ss = _stops(80)
    p1 = Panel(b, PX1, 92, PW, 214, title="Les deux seuils",
               readout="points par heure")
    wald = [(math.log10(s), math.log10(SP.derive_de_wald(s)))
            for s in ss]
    libre = [(math.log10(s), math.log10(SP.derive_non_bornee(s)))
             for s in ss]
    lo = min(y for _, y in libre)
    hi = max(y for _, y in wald)
    p1.domain(math.log10(ss[0]), math.log10(ss[-1]),
              lo - 0.15, hi + 0.15)
    p1.frame()
    p1.grid_y([-2.0, -1.0, 0.0, 1.0],
              lambda v: _num(10.0 ** v, 2 if v < 0 else 0), dx=30.0)
    p1.grid_x([math.log10(0.005), math.log10(0.02),
               math.log10(0.08), math.log10(0.30)],
              lambda v: _num(10.0 ** v, 3) + " %",
              label="largeur du stop")
    p1.hline(math.log10(seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]), "lvl")
    p1.path(wald, "hm7", tip="borné par la séance")
    p1.path(libre, "hm3", dash="5 4", tip="non borné")
    p1.label(math.log10(ss[-1]),
             math.log10(seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]),
             "le plafond plausible", dx=-8, dy=-8, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Le facteur qui les sépare",
               readout="rapport des deux")
    rap = [(s, SP.ecart_des_routes(s)) for s in ss]
    hi2 = max(y for _, y in rap)
    p2.domain(0.0, ss[-1], 0.0, hi2 * 1.10)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2 * 1.10, 5.0), lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([0.1, 0.2, 0.3], lambda v: _num(v, 1) + " %",
              label="largeur du stop")
    p2.hline(1.0, "lvl")
    p2.path(rap, "hm4", tip="rapport des deux routes")
    p2.label(0.0, 1.0, "un : les deux routes s'accorderaient", dx=8, dy=-8)
    for pct in SP.GEOMETRIES:
        p2.dot(pct, SP.ecart_des_routes(pct), "hm4",
               _num(pct, 3) + " %", r=4.5)

    b.legend(0.0, 352.0,
             [("hm7", "borné par la séance"),
              ("hm3", "non borné", "5 4"),
              ("hm4", "le rapport, à droite")],
             step=200.0, kind="line")
    b.annotation(0.0, 376.0,
                 "la route non bornée suppose que le prix a tout le temps "
                 "qu'il lui faut, ce qu'une séance ne donne pas")
    b.annotation(0.0, 392.0,
                 "elle est plus optimiste partout, d'un facteur "
                 + _num(SP.ecart_des_routes(SP.GEOMETRIES[0]), 2)
                 + " au stop déclaré et "
                 + _num(SP.ecart_des_routes(0.200), 1) + " au plus large")
    b.annotation(0.0, 408.0,
                 "elle ne retourne le verdict sur aucune largeur, mais elle "
                 "le rend discutable, ce qui suffit")

    _source(b, "Deux façons de calculer la même chose, et l'écart entre "
               "elles est un facteur. La route non bornée a une forme fermée "
               "et ne demande pas de choisir un horizon, ce qui est "
               "exactement pourquoi on l'emploie sans y penser. Elle place "
               "l'exigence de la géométrie déclarée à quelques dizaines de "
               "pour cent au-dessus du plafond plausible, un dépassement "
               "dont on argumente. La route bornée par la séance, celle de "
               "la partie X, la place à un facteur deux et demi au-dessus, "
               "dont on n'argumente pas. Le verdict ne bascule sur aucune "
               "largeur de la grille ; ce qui bascule est ce qu'un opérateur "
               "est prêt à discuter, et c'est ainsi qu'une géométrie que la "
               "mesure condamne continue de vivre.")
    return b.render("La derive d equilibre par deux routes contre la largeur "
                    "du stop, et le facteur qui les separe.")


def fig_spec_esperance() -> str:
    """Ce que chaque géométrie rend, par dérive et par sens."""
    b = _plate(500, "Spéculation · l'espérance",
               "Une dérive ne change pas la fréquence, elle change le gain",
               "en R par décision")

    ds = [0.0 + 4.0 * i / 120 for i in range(121)]
    p1 = Panel(b, PX1, 92, PW, 214, title="L'espérance contre la dérive",
               readout="R par décision")
    series = [("hm7", "", SP.GEOMETRIES[0]), ("hm5", "6 3", SP.GEOMETRIES[1]),
              ("hm3", "2 3", SP.GEOMETRIES[2])]
    courbes = [(cls, dash, s, [(d, SP.lire(s, d, 1).esperance_r) for d in ds])
               for cls, dash, s in series]
    hi = max(y for _, _, _, c in courbes for _, y in c)
    lo = min(y for _, _, _, c in courbes for _, y in c)
    p1.domain(0.0, ds[-1], lo * 1.15, hi * 1.15)
    p1.frame()
    p1.grid_y(_ticks(lo * 1.15, hi * 1.15, 0.5), lambda v: _signed(v, 1),
              dx=30.0)
    p1.grid_x([0, 1, 2, 3, 4], lambda v: _num(v, 0),
              label="dérive (points par heure)")
    p1.band_x(SP.DERIVES[1], SP.DERIVES[2], "wash")
    p1.hline(0.0, "lvl")
    for cls, dash, _s, c in courbes:
        p1.path(c, cls, dash=dash, tip="espérance à la hausse")
    p1.label(0.0, 0.0, "l'équilibre", dx=8, dy=-8)
    p1.label(ds[-1], hi * 1.05, "le domaine plausible", dx=-8, dy=0,
             anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Les deux sens à la dérive haute",
               readout="R par décision")
    p2.domain(-1.0, 1.0, -0.6, len(SP.GEOMETRIES) - 0.4)
    p2.frame()
    p2.grid_x([-1.0, -0.5, 0.0, 0.5, 1.0], lambda v: _signed(v, 1))
    p2.vline(0.0, "lvl")
    for i, pct in enumerate(SP.GEOMETRIES):
        y = len(SP.GEOMETRIES) - 1 - i
        h = SP.lire(pct, HAUTE, 1).esperance_r
        bb = SP.lire(pct, HAUTE, -1).esperance_r
        p2.hbar(y + 0.16, 0.0, h, 11.0, "hm7", tip="à la hausse")
        p2.hbar(y - 0.16, 0.0, bb, 11.0, "hm3", tip="à la baisse")
        p2.label(-1.0, y + 0.40, "stop " + _num(pct, 3) + " %", dx=4, dy=0)

    b.legend(0.0, 352.0,
             [("hm7", "stop déclaré"), ("hm5", "stop moyen", "6 3"),
              ("hm3", "stop élargi", "2 3")],
             step=200.0, kind="line")
    b.annotation(0.0, 376.0,
                 "à dérive nulle les trois courbes valent moins la friction "
                 "sur le stop, et c'est le résultat structurant du document")
    b.annotation(0.0, 392.0,
                 "l'espérance croît linéairement avec la dérive, et sa "
                 "pente est le temps d'exposition — l'identité de Wald")
    b.annotation(0.0, 408.0,
                 "à droite, les deux sens à la dérive haute : le pari "
                 "inverse coûte le double")

    _source(b, "L'espérance passe par l'identité de Wald, et le cadre de "
               "gauche en est le dessin : trois droites de même origine et "
               "de pentes différentes, la pente étant le temps que la "
               "position reste exposée. C'est pourquoi élargir le stop "
               "améliore l'espérance sans rien apprendre du marché — la "
               "position reste simplement exposée plus longtemps à la même "
               "dérive. Le cadre de droite montre ce que la même dérive "
               "fait aux deux sens, et l'asymétrie y est plus grande que "
               "dans les probabilités : une dérive déplace peu la fréquence "
               "des gains et beaucoup ce qu'ils rapportent.")
    return b.render("L esperance contre la derive aux trois geometries, et "
                    "les deux sens a la derive haute.")


def fig_spec_relief_esperance() -> str:
    """Le relief de l'espérance."""
    z = [list(l) for l in SP.surface_esperance()]
    vals = [v for l in z for v in l]

    b = _plate(486, "Spéculation · le relief de l'espérance",
               "Ce qu'une position rend, en largeur de stop et en dérive",
               "hauteur : R par décision")

    _surface(b, 0.52 * W, 232.0, z, min(vals), max(vals), cx=42.0, cy=13.0,
             cz=158.0,
             row_labels=[_num(s, 3) + " %" for s in SP.SURF_STOP],
             col_labels=[_num(d, 1) for d in SP.SURF_DERIVE],
             z_ticks=[(t, _signed(t, 1)) for t in _echine(min(vals),
                                                          max(vals))],
             tip="{v:.2f}", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : le stop · arête droite : la dérive · "
                 "hauteur : l'espérance en R")
    b.annotation(0.0, 424.0,
                 "la surface est monotone en dérive et non en stop : "
                 "elle culmine à "
                 + _num(SP.SURF_STOP[
                     max(range(len(z)), key=lambda i: max(z[i]))], 3)
                 + " % et redescend au-delà")
    b.annotation(0.0, 440.0,
                 "le point le plus bas est le stop le plus serré à dérive "
                 "faible, et c'est la géométrie que le dispositif déclare")

    _source(b, "La hauteur est l'espérance d'une décision, en unités de "
               "risque. La surface monte avec la dérive, ce qui est attendu, "
               "et elle monte avec la largeur du stop jusqu'à un maximum "
               "intermédiaire, ce qui l'est moins. La raison est que "
               "l'espérance en R divise par le stop : élargir allonge le "
               "temps d'exposition, donc le numérateur, mais agrandit aussi "
               "le dénominateur, et le second finit par l'emporter. Le "
               "coin le plus bas est la géométrie déclarée du dispositif "
               "sous une dérive faible, et c'est celle dont ce document "
               "montre depuis la partie X qu'elle est arithmétiquement "
               "invivable.")
    return b.render("Relief de l esperance d une position, en largeur de "
                    "stop et en derive.")


# ---------------------------------------------------------------------------
# IV. Le catalogue, pris comme des positions
# ---------------------------------------------------------------------------


def fig_spec_lectures() -> str:
    """Les quinze lectures du catalogue, prises comme des positions."""
    b = _plate(510, "Spéculation · le catalogue",
               "Le théorème tient jusqu'à une heure, puis la séance le reprend",
               "les quinze lectures")

    lignes = SP.lignes()
    p1 = Panel(b, PX1, 92, PW, 214,
               title="La probabilité contre la portée", readout="P(objectif)")
    ts = [2.0 + (2000.0 - 2.0) * i / 300 for i in range(301)]
    courbe = []
    for t in ts:
        a = SP.SIGMA_MIN * math.sqrt(t)
        bb = C.RR_LECTURE * a
        courbe.append((bb / SP.ECART_SEANCE,
                       100.0 * SP._issues(a, bb, 0.0,
                                          max(SP.SEANCE_MIN, t))[0]))
    p1.domain(0.0, 3.6, 0.0, 40.0)
    p1.frame()
    p1.grid_y([0, 10, 20, 30, 40], lambda v: _num(v, 0) + " %", dx=30.0)
    p1.grid_x([0, 1, 2, 3], lambda v: _num(v, 0),
              label="objectif en écarts-types de séance")
    p1.hline(100.0 / (1.0 + C.RR_LECTURE), "lvl")
    p1.vline(1.0, "lvl")
    p1.path(courbe, "hm7", tip="probabilité d'objectif")
    for lg in lignes:
        p1.dot(lg.portee, 100.0 * lg.p_nulle, "hm5", lg.nom, r=3.6)
    p1.label(0.0, 100.0 / (1.0 + C.RR_LECTURE), "ce que le théorème annonce",
             dx=8, dy=-8)
    p1.label(1.0, 38.0, "la portée d'une séance", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Les deux sens, lecture par lecture",
               readout="P(objectif) à la dérive haute")
    n = len(lignes)
    p2.domain(0.0, 60.0, -0.6, n - 0.4)
    p2.frame()
    p2.grid_x([20, 40, 60], lambda v: _num(v, 0) + " %")
    reperes = []
    vu = set()
    for i, lg in enumerate(lignes):
        if lg.horizon_min not in vu:
            vu.add(lg.horizon_min)
            reperes.append((n - 1 - i, lg.horizon_min))
    p2.grid_y([y for y, _ in reperes],
              lambda v: _num(dict(reperes)[v], 0), dx=26.0,
              label="horizon (min)")
    for i, lg in enumerate(lignes):
        y = n - 1 - i
        p2.hbar(y + 0.20, 0.0, 100.0 * lg.p_haute, 5.0, "hm7",
                tip=lg.nom + ", à la hausse")
        p2.hbar(y - 0.20, 0.0, 100.0 * lg.p_basse, 5.0, "hm3",
                tip=lg.nom + ", à la baisse")

    b.legend(0.0, 362.0,
             [("hm7", "à la hausse"), ("hm3", "à la baisse"),
              ("hm5", "une lecture du catalogue")],
             step=200.0)
    b.annotation(0.0, 386.0,
                 "les quinze lectures tombent toutes sur la même courbe, et "
                 "aucune n'est au-dessus : leur motif n'y change rien")
    b.annotation(0.0, 402.0,
                 "elle vaut " + _pct(1.0 / (1.0 + C.RR_LECTURE), 2)
                 + " exactement tant que l'objectif y tient, puis décroche "
                 "d'un facteur "
                 + _num((1.0 / (1.0 + C.RR_LECTURE)) / lignes[-1].p_nulle, 1))
    b.annotation(0.0, 418.0,
                 "les lectures longues ne sont pas moins fiables : à "
                 "rapport égal, elles sont innégociables dans une séance")

    _source(b, "Chaque point du cadre de gauche est une lecture du "
               "catalogue, placée par sa seule géométrie. Aucune ne se "
               "détache de la courbe, et c'est le résultat : à rapport fixé, "
               "la probabilité d'objectif ne dépend ni du motif reconnu ni "
               "de sa rareté, mais uniquement de la distance que l'objectif "
               "demande à la séance. La verticale est cette distance quand "
               "elle vaut un écart-type de séance, et c'est là que la courbe "
               "quitte l'horizontale du théorème. Le cadre de droite met les "
               "deux sens face à face sous la dérive haute : les barres "
               "s'écartent au milieu de la liste et se referment aux deux "
               "bouts, ce qui est l'horizon optimal vu autrement.")
    return b.render("Les quinze lectures du catalogue placees par leur "
                    "portee, et les deux sens lecture par lecture.")


def fig_spec_relief_portee() -> str:
    """Le relief de la portée."""
    z = [list(l) for l in SP.surface_portee()]
    vals = [v for l in z for v in l]

    b = _plate(486, "Spéculation · le relief de la portée",
               "Ce que la géométrie demande à la séance de parcourir",
               "hauteur : σ de séance")

    _surface(b, 0.52 * W, 232.0, z, min(vals), max(vals), cx=42.0, cy=13.0,
             cz=158.0,
             row_labels=[_num(s, 3) + " %" for s in SP.SURF_STOP],
             col_labels=[_num(r, 0) for r in SP.SURF_RR],
             z_ticks=[(t, _num(t, 0)) for t in _echine(min(vals), max(vals))],
             tip="{v:.2f}", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : le stop · arête droite : le rapport · "
                 "hauteur : ce que l'objectif demande")
    b.annotation(0.0, 424.0,
                 "la hauteur est un produit, le stop fois le rapport : la "
                 "surface est une nappe réglée")
    b.annotation(0.0, 440.0,
                 "au rapport déclaré, la frontière du négociable tombe à "
                 + _num(SP.stop_de_portee_un(), 3)
                 + " % de stop, plus serré que le stop déclaré")

    _source(b, "Ce relief n'a aucune subtilité et c'est pourquoi il "
               "convainc : la hauteur est le produit de deux réglages que "
               "l'opérateur choisit librement, et la seule chose qui ne se "
               "choisit pas est le plan horizontal à un écart-type où la "
               "séance coupe. Tout ce qui est au-dessus de ce plan est une "
               "géométrie dont l'objectif ne sera pas atteint dans la "
               "journée, quel que soit le motif d'entrée, quelle que soit la "
               "qualité de la lecture, et quel que soit le talent de "
               "l'opérateur. La surface dit donc où se trouve le domaine "
               "négociable, et il est plus petit que ce qu'un dispositif "
               "déclare d'ordinaire.")
    return b.render("Relief de ce que la geometrie demande a la seance de "
                    "parcourir, en stop et en rapport.")


# ---------------------------------------------------------------------------
# V. La feuille, et le décompte
# ---------------------------------------------------------------------------


def fig_spec_bandeau() -> str:
    """Ce que porte le bandeau, géométrie par géométrie."""
    b = _plate(490, "Spéculation · le bandeau",
               "Chaque planche du document porte désormais ce calcul",
               "les familles, groupées par géométrie")

    groupes = SP.familles_par_geometrie()
    n = len(groupes)
    p1 = Panel(b, PX1, 92, PW, 214, title="Les deux sens par géométrie",
               readout="P(objectif) à la dérive haute")
    p1.domain(0.0, 60.0, -0.6, n - 0.4)
    p1.frame()
    p1.grid_x([0, 20, 40, 60], lambda v: _num(v, 0) + " %")
    for i, (nom, compte, bd) in enumerate(groupes):
        y = n - 1 - i
        p1.hbar(y + 0.16, 0.0, 100.0 * bd.p_hausse[-1], 9.0, "hm7",
                tip=nom + ", à la hausse")
        p1.hbar(y - 0.16, 0.0, 100.0 * bd.p_baisse[-1], 9.0, "hm3",
                tip=nom + ", à la baisse")
        p1.label(0.0, y + 0.36,
                 nom + " · " + _num(compte, 0)
                 + (" familles" if compte > 1 else " famille"), dx=4, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="La dérive que chacune exigerait",
               readout="points par heure")
    plancher = math.log10(0.02)
    p2.domain(plancher, math.log10(20.0), -0.6, n - 0.4)
    p2.frame()
    p2.grid_x([math.log10(0.03), math.log10(0.3), math.log10(3.0),
               math.log10(20.0)],
              lambda v: _num(10.0 ** v, 2 if v < 0 else 1))
    p2.vline(math.log10(seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]), "lvl")
    for i, (nom, _c, bd) in enumerate(groupes):
        y = n - 1 - i
        d = bd.derive_requise
        p2.hbar(y, plancher, math.log10(max(d, 0.021)), 10.0,
                "hm1" if not SP.dans_le_domaine(d) else "hm5",
                tip=nom + " : " + _num(d, 2) + " pt/h")
        p2.label(plancher, y + 0.36,
                 "a = " + _num(bd.stop, 2) + " pt", dx=4, dy=0)
        p2.label(math.log10(max(d, 0.021)), y, _num(d, 2), dx=7, dy=4)
    p2.label(math.log10(seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]), -0.35,
             "le plafond plausible", dx=-7, dy=0, anchor="end")

    b.legend(0.0, 352.0,
             [("hm7", "à la hausse"), ("hm3", "à la baisse"),
              ("hm5", "dans le domaine"),
              ("hm1", "hors du domaine")],
             step=150.0)
    b.annotation(0.0, 376.0,
                 _num(len(SP.HYPOTHESES), 0) + " familles de figures, et "
                 "six géométries : deux familles se regroupent quand leur "
                 "horizon est le même")
    b.annotation(0.0, 392.0,
                 "aucune ne déclare d'avantage mesuré : le zéro vient des "
                 "modules qui l'ont mesuré, pas de celui-ci")
    b.annotation(0.0, 408.0,
                 "les huit parties d'options sont la seule ligne hors du "
                 "domaine : elles prennent la géométrie déclarée")

    _source(b, "Le bandeau que porte chaque planche du document est "
               "entièrement recalculé à la construction, depuis la géométrie "
               "de la lecture que la planche illustre. Ce cadre en donne la "
               "carte, et le regroupement n'est pas une commodité de mise en "
               "page : deux familles tombent sur la même ligne quand et "
               "seulement quand leur horizon de lecture est le même, donc "
               "quand leur bandeau porte les mêmes nombres. Ce qui sépare "
               "une ligne de la suivante n'est jamais le sujet traité mais "
               "la distance de son objectif, donc la part du théorème que la "
               "séance lui laisse. Les huit parties d'options sont au sommet "
               "parce qu'elles n'ont aucun objet directionnel et prennent la "
               "géométrie déclarée du dispositif, la plus exigeante des six.")
    return b.render("Les deux sens et la derive requise, par geometrie de "
                    "lecture.")


def fig_spec_feuille() -> str:
    """La feuille : trois géométries, deux conditions, aucun laissez-passer."""
    b = _plate(470, "Spéculation · la feuille",
               "Trois géométries, deux conditions, et aucune ne passe",
               "ce qu'il reste à déclarer")

    p1 = Panel(b, PX1, 92, PW, 214, title="La dérive requise",
               readout="points par heure")
    plancher = math.log10(0.1)
    p1.domain(plancher, math.log10(12.0), -0.6, len(SP.GEOMETRIES) - 0.4)
    p1.frame()
    p1.grid_x([math.log10(0.1), math.log10(1.0), math.log10(10.0)],
              lambda v: _num(10.0 ** v, 1))
    p1.band_x(math.log10(seuil.PLAUSIBLE_DRIFT_PER_HOUR[0]),
              math.log10(seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]), "wash")
    for i, pct in enumerate(SP.GEOMETRIES):
        y = len(SP.GEOMETRIES) - 1 - i
        d = SP.derive_de_wald(pct)
        p1.hbar(y, plancher, math.log10(d), 13.0,
                "hm3" if SP.dans_le_domaine(d) else "hm1",
                tip=_num(d, 2) + " pt/h")
        p1.label(plancher, y + 0.32, "stop " + _num(pct, 3) + " %", dx=4,
                 dy=0)
        p1.label(math.log10(d), y, _num(d, 2), dx=7, dy=4)
    p1.label(math.log10(seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]),
             len(SP.GEOMETRIES) - 1.34, "le domaine plausible", dx=-7, dy=0,
             anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="La portée demandée",
               readout="σ de séance")
    haut = max(SP.portee_de_seance(p) for p in SP.GEOMETRIES) * 1.30
    p2.domain(0.0, haut, -0.6, len(SP.GEOMETRIES) - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, haut, 2.0), lambda v: _num(v, 0))
    p2.band_x(0.0, 1.0, "wash")
    for i, pct in enumerate(SP.GEOMETRIES):
        y = len(SP.GEOMETRIES) - 1 - i
        v = SP.portee_de_seance(pct)
        p2.hbar(y, 0.0, v, 13.0, "hm3" if v <= 1.0 else "hm1",
                tip=_num(v, 2) + " σ")
        p2.label(0.0, y + 0.32,
                 "un pour " + _num(SP.rr_atteignable(pct, 0.05), 1)
                 + " serait tenable", dx=4, dy=0)
        p2.label(v, y, _num(v, 2), dx=7, dy=4)
    p2.label(1.0, len(SP.GEOMETRIES) - 1.35, "ce qu'une séance parcourt",
             dx=7, dy=0)

    b.legend(0.0, 352.0,
             [("hm3", "la condition est remplie"),
              ("hm1", "la condition échoue")],
             step=240.0)
    b.annotation(0.0, 376.0,
                 "le stop déclaré échoue sur la dérive : il en demande "
                 + _num(SP.derive_de_wald(SP.GEOMETRIES[0]), 2)
                 + " points par heure quand le domaine s'arrête à "
                 + _num(seuil.PLAUSIBLE_DRIFT_PER_HOUR[1], 1))
    b.annotation(0.0, 392.0,
                 "les deux stops élargis passent la dérive et échouent sur "
                 "la portée : leur objectif sort de la séance")
    b.annotation(0.0, 408.0,
                 "un opérateur n'a donc pas trois paramètres à choisir mais "
                 "deux — la séance fixe le troisième")

    _source(b, "Deux conditions indépendantes, et il faut les deux. La "
               "dérive requise doit tomber dans le domaine que le document "
               "appelle plausible, et l'objectif doit rester dans la portée "
               "d'une séance. Les trois géométries que le document compare "
               "depuis sa partie X échouent chacune sur une condition, et "
               "jamais sur la même : la déclarée sur la dérive, les deux "
               "élargies sur la portée. Ce n'est donc pas qu'une des trois "
               "soit meilleure que les autres — c'est que le réglage se "
               "cherche à deux dimensions et non à une, et que le domaine "
               "où les deux conditions tiennent ensemble est plus étroit que "
               "ce qu'un dispositif déclare d'ordinaire. Les étiquettes du "
               "cadre de droite disent le rapport qui serait tenable à "
               "chaque largeur.")
    return b.render("La derive requise et la portee demandee par les trois "
                    "geometries, et les deux conditions.")


def fig_spec_wald() -> str:
    """L'identité de Wald, dessinée."""
    b = _plate(490, "Spéculation · l'identité",
               "Une géométrie n'achète pas de l'espérance, elle achète du temps",
               "E[R] = (µ·E[τ∧T] − c)/a")

    ss = _stops(80)
    p1 = Panel(b, PX1, 92, PW, 214, title="Le temps que la géométrie achète",
               readout="minutes d'exposition")
    courbe = [(s, seuil.geometry(s).exposure_min) for s in ss]
    hi = max(max(y for _, y in courbe), SP.SEANCE_MIN) * 1.10
    p1.domain(0.0, ss[-1], 0.0, hi)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi, 100.0), lambda v: _num(v, 0), dx=30.0)
    p1.grid_x([0.0, 0.1, 0.2, 0.3], lambda v: _num(v, 1) + " %",
              label="largeur du stop")
    p1.hline(SP.SEANCE_MIN, "lvl")
    p1.path(courbe, "hm7", tip="temps d'exposition")
    p1.label(0.0, SP.SEANCE_MIN, "la séance entière", dx=8, dy=-8)
    for pct in SP.GEOMETRIES:
        p1.dot(pct, seuil.geometry(pct).exposure_min, "hm7",
               _num(pct, 3) + " %", r=4.5)

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce que ce temps coûte à prouver",
               readout="dérive requise")
    req = [(s, SP.derive_de_wald(s)) for s in ss]
    hi2 = max(y for _, y in req)
    p2.domain(0.0, ss[-1], 0.0, min(hi2, 20.0) * 1.05)
    p2.frame()
    p2.grid_y(_ticks(0.0, min(hi2, 20.0) * 1.05, 5.0), lambda v: _num(v, 0),
              dx=26.0)
    p2.grid_x([0.1, 0.2, 0.3], lambda v: _num(v, 1) + " %",
              label="largeur du stop")
    p2.band_y(0.0, seuil.PLAUSIBLE_DRIFT_PER_HOUR[1], "wash")
    p2.path(req, "hm4", tip="dérive requise")
    p2.label(ss[-1], seuil.PLAUSIBLE_DRIFT_PER_HOUR[1] + 0.6,
             "le domaine plausible", dx=-8, dy=0, anchor="end")

    b.legend(0.0, 352.0,
             [("hm7", "le temps d'exposition"),
              ("hm4", "la dérive requise, à droite")],
             step=240.0, kind="line")
    b.annotation(0.0, 376.0,
                 "l'identité de Wald : à dérive nulle, toute géométrie "
                 "rend moins la friction sur le stop, et aucune n'en crée")
    b.annotation(0.0, 392.0,
                 "ce qu'une géométrie achète est le temps du cadre de "
                 "gauche, et il sature à la séance")
    b.annotation(0.0, 408.0,
                 "le seuil du cadre de droite est ce temps à l'envers : "
                 "c'est pourquoi il tombe si vite et pourquoi il plafonne")

    _source(b, "Les deux cadres sont la même quantité lue dans les deux "
               "sens. À gauche, le temps qu'une position reste exposée, qui "
               "croît avec la largeur du stop et sature quand la séance "
               "prend le relais du stop comme cause de sortie. À droite, la "
               "dérive qu'il faut pour couvrir la friction, qui est ce temps "
               "à l'envers. C'est toute l'identité de Wald, et c'est ce que "
               "ce document répète depuis sa dixième partie : une géométrie "
               "de sortie ne crée aucune espérance, elle achète du temps de "
               "marché, et le seul choix qu'elle offre est celui de "
               "l'exigence qu'on se donne.")
    return b.render("Le temps d exposition contre la largeur du stop, et la "
                    "derive requise qui en est l inverse.")


def fig_spec_reste() -> str:
    """Ce que la feuille laisse à déclarer."""
    b = _plate(470, "Spéculation · le décompte",
               "Ce que la feuille tranche, et ce qu'elle laisse ouvert",
               "deux conditions, trois géométries")

    p1 = Panel(b, PX1, 92, PW, 214, title="Ce que la feuille tranche",
               readout="par géométrie")
    lignes_p = [
        ("l'objectif tient dans la séance",
         [SP.portee_de_seance(p) <= 1.0 for p in SP.GEOMETRIES]),
        ("la dérive requise est plausible",
         [SP.dans_le_domaine(SP.derive_de_wald(p)) for p in SP.GEOMETRIES]),
        ("les deux sens sont symétriques",
         [True for _ in SP.GEOMETRIES]),
        ("une lecture apporte une dérive",
         [False for _ in SP.GEOMETRIES]),
    ]
    n = len(lignes_p)
    p1.domain(0.0, 3.0, -0.6, n - 0.4)
    p1.frame()
    p1.grid_x([0.5, 1.5, 2.5],
              lambda v: _num(SP.GEOMETRIES[int(v)], 3) + " %")
    for i, (nom, etats) in enumerate(lignes_p):
        y = n - 1 - i
        p1.label(0.0, y + 0.34, nom, dx=4, dy=0)
        for j, ok in enumerate(etats):
            p1.dot(j + 0.5, y, "hm7" if ok else "hm1",
                   nom + " : " + ("oui" if ok else "non"), r=5.0)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Ce que chaque réglage rendrait visible",
               readout="écart entre les deux sens")
    opt = SP.horizon_optimal()
    valeurs = [
        ("le réglage proposé · " + _num(opt, 0) + " min, un pour "
         + _num(C.RR_LECTURE, 0), SP.ecart_directionnel(opt)),
    ] + [("le stop " + _num(pct, 3) + " %, un pour " + _num(SP.RR, 0),
          SP.ecart_d_un_stop(pct)) for pct in SP.GEOMETRIES]
    m = len(valeurs)
    haut = max(v for _, v in valeurs) * 1.32
    p2.domain(0.0, haut, -0.6, m - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, haut, 10.0), lambda v: _num(v, 0),
              label="points de taux")
    for i, (nom, v) in enumerate(valeurs):
        y = m - 1 - i
        p2.hbar(y, 0.0, v, 11.0, "hm7" if i == 0 else "hm3", tip=nom)
        p2.label(0.0, y + 0.32, nom, dx=4, dy=0)
        p2.label(v, y, _num(v, 1), dx=7, dy=4)

    b.legend(0.0, 352.0,
             [("hm7", "la condition tient"), ("hm1", "elle échoue"),
              ("hm3", "les géométries déclarées, à droite")],
             step=200.0)
    b.annotation(0.0, 376.0,
                 "la troisième ligne est vraie partout et la quatrième "
                 "fausse partout, et ce sont les deux résultats du document")
    b.annotation(0.0, 392.0,
                 "à droite, ce qu'une même dérive rendrait visible : "
                 + _num(SP.ecart_directionnel(SP.horizon_optimal()), 1)
                 + " points de taux contre "
                 + _num(max(SP.ecart_d_un_stop(p) for p in SP.GEOMETRIES), 1)
                 + " au mieux des trois")
    b.annotation(0.0, 408.0,
                 "le réglage proposé ne promet aucun avantage : il dit "
                 "seulement où une dérive, si elle existait, se verrait")

    _source(b, "La quatrième ligne du cadre de gauche est la seule qui "
               "compte vraiment, et elle est fausse aux trois géométries "
               "comme elle l'est aux quinze lectures du catalogue, aux douze "
               "setups et aux cinquante-neuf affirmations des huit parties "
               "d'options. Ce document n'a jamais trouvé de dérive. Ce qu'il "
               "propose à la place est le cadre de droite : le réglage où "
               "une dérive, si un opérateur en avait une, serait la plus "
               "visible — et donc la plus vite prouvée ou réfutée. C'est "
               "moins qu'une stratégie et c'est plus qu'un avis, parce que "
               "c'est le seul des deux qui se calcule.")
    return b.render("Ce que la feuille tranche par geometrie, et le reglage "
                    "qu elle propose.")


FIGURES = {
    "specissues": fig_spec_issues,
    "specportee": fig_spec_portee,
    "specreliefsurvie": fig_spec_relief_survie,
    "specsens": fig_spec_sens,
    "specoptimum": fig_spec_optimum,
    "specreliefecart": fig_spec_relief_ecart,
    "specroutes": fig_spec_routes,
    "specesperance": fig_spec_esperance,
    "specreliefesp": fig_spec_relief_esperance,
    "speclectures": fig_spec_lectures,
    "specreliefportee": fig_spec_relief_portee,
    "specbandeau": fig_spec_bandeau,
    "specfeuille": fig_spec_feuille,
    "specwald": fig_spec_wald,
    "specreste": fig_spec_reste,
}


def render_all() -> dict[str, str]:
    return {k: f() for k, f in FIGURES.items()}
