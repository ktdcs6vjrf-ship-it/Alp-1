"""Les planches de « la saignée du delta, et les deux horloges d'un week-end ».

Quinze planches, onze à plat et quatre en relief. La cinquième refait la
planche du guide sous les deux horloges, et la quatorzième est la seule de la
série d'options où le dépôt donne raison à un guide sans réserve.

Comme `figgra`, `figth`, `figvg`, `figrh` et `figva`, ce module importe ses
fonctions d'échine, de graduation et de décade de `fignv`.
"""

from __future__ import annotations

import math

from . import charm as CH
from . import grandeurs as G
from . import niveaux as nv
from . import quant as q
from . import seuil
from . import theta as th
from . import vanna as va
from .figdisc import W, _plate, _source, _surface
from .fignv import _dec, _echine, _pct, _ticks
from .figterm import Board, Panel, _num, _signed


PW = (W - 74.0) / 2.0 - 30.0
PX1 = 74.0
PX2 = 74.0 + (W - 74.0) / 2.0

S = CH.S_REF
V = CH.VOL_REF
AN = CH.JOURS_AN


def _bl(m: float, j: float) -> float:
    return CH.bleed(S * m, S, j / AN)


# ---------------------------------------------------------------------------
# I. L'accélération
# ---------------------------------------------------------------------------


def fig_ch_accel() -> str:
    """La saignée contre le comptant, et l'exposant qu'on lui prête."""
    b = _plate(500, "Charm · l'accélération",
               "L'accélération est réelle, la puissance ne l'est pas",
               _num(100 * V, 0) + " % de volatilité")

    ms = [0.80 + 0.002 * i for i in range(201)]
    p1 = Panel(b, PX1, 92, PW, 214, title="La saignée contre le comptant",
               readout="delta par jour")
    series = [("hm7", "", 1.0), ("hm5", "6 3", 3.0), ("hm3", "2 3", 7.0),
              ("hm1", "1 4", 30.0)]
    courbes = [(cls, dash, j, [(m, _bl(m, j)) for m in ms])
               for cls, dash, j in series]
    hi = max(y for _, _, _, c in courbes for _, y in c) * 1.30
    lo = min(y for _, _, _, c in courbes for _, y in c) * 1.30
    p1.domain(ms[0], ms[-1], lo, hi)
    p1.frame()
    p1.grid_y(_ticks(lo, hi, 0.05), lambda v: _signed(v, 2), dx=30.0)
    p1.grid_x([0.85, 0.95, 1.05, 1.15], lambda v: _num(v, 2),
              label="spot sur strike")
    p1.hline(0.0, "lvl")
    p1.vline(1.0, "lvl")
    for cls, dash, j, c in courbes:
        p1.path(c, cls, dash=dash, tip=_num(j, 0) + " jours")
    p1.label(ms[0], lo * 0.72, "le call hors de la monnaie perd", dx=8, dy=0)
    p1.label(ms[-1], hi * 0.80, "celui dans la monnaie gagne", dx=-8, dy=0,
             anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="L'exposant de l'amplitude",
               readout="d ln pic / d ln T")
    js = [0.4 + 0.4 * i for i in range(200)]
    mesure = [(j, CH.exposant_du_pic(j)) for j in js]
    p2.domain(0.0, js[-1], -1.6, -0.85)
    p2.frame()
    p2.grid_y(_ticks(-1.6, -0.85, 0.15), lambda v: _num(v, 2), dx=30.0)
    p2.grid_x([0, 20, 40, 60, 80], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.hline(-1.0, "lvl")
    p2.hline(-CH.PUISSANCE_ANNONCEE, "lvl")
    p2.path(mesure, "hm4", tip="exposant mesuré")
    p2.label(0.0, -1.0, "moins un : la mesure y tend", dx=8, dy=-6)
    p2.label(0.0, -CH.PUISSANCE_ANNONCEE, "moins trois demis : l'annonce",
             dx=8, dy=12)

    b.legend(0.0, 352.0,
             [("hm7", "un jour"), ("hm5", "trois jours", "6 3"),
              ("hm3", "sept jours", "2 3"), ("hm1", "trente jours", "1 4"),
              ("hm4", "l'exposant")],
             step=132.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le dénominateur porte bien la puissance trois demis, et "
                 "le numérateur porte une racine qui en annule la moitié")
    b.annotation(0.0, 392.0,
                 "l'amplitude au pic croît donc comme l'inverse du temps, "
                 "pas comme sa puissance trois demis")
    b.annotation(0.0, 408.0,
                 "la mesure serre moins un de plus en plus près quand "
                 "l'échéance raccourcit")

    _source(b, "Le cadre de gauche montre l'objet : deux lobes de part et "
               "d'autre de la monnaie, de signes opposés, qui se resserrent "
               "et grandissent quand l'échéance raccourcit. Le cadre de "
               "droite met à l'épreuve la phrase que le guide bâtit sur sa "
               "propre formule. La puissance trois demis est bien au "
               "dénominateur, et elle serait la bonne réponse si le "
               "numérateur ne portait pas lui aussi une racine du temps. "
               "L'exposant local le dit sans qu'on ait à en juger, et il "
               "tend vers moins un. L'écart entre les deux lectures est un "
               "facteur racine de l'échéance sur toute la description du "
               "phénomène.")
    return b.render("La saignee du delta contre le comptant a quatre "
                    "echeances, et l exposant mesure de son amplitude.")


def fig_ch_pic() -> str:
    """Le lieu du pic, et le strike que le guide choisit."""
    b = _plate(500, "Charm · le pic",
               "Le pic est à seize deltas, et le guide illustre à quatre pour cent",
               "forme fermée")

    js = [0.5 + 0.5 * i for i in range(120)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Le lieu du pic",
               readout="spot sur strike")
    ferme = [(j, G.moneyness_du_pic(V, j / AN)) for j in js]
    balaye = [(j, CH.pic_balaye(j / AN, V, 3000)[0]) for j in js]
    ylo = min(min(y for _, y in ferme), 1.0 - CH.ECART_ILLUSTRATION) - 0.006
    p1.domain(0.0, js[-1], ylo, 1.004)
    p1.frame()
    p1.grid_y(_ticks(ylo, 1.004, 0.01), lambda v: _num(v, 2), dx=30.0)
    p1.grid_x([0, 15, 30, 45, 60], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.hline(1.0, "lvl")
    p1.hline(1.0 - CH.ECART_ILLUSTRATION, "lvl")
    p1.path(balaye, "hm7", tip="le balayage")
    p1.path(ferme, "hm2", dash="5 4", tip="la forme fermée")
    p1.label(0.0, 1.0, "la monnaie", dx=8, dy=-6)
    p1.label(js[-1], 1.0 - CH.ECART_ILLUSTRATION,
             "le strike de l'illustration du guide", dx=-8, dy=-8,
             anchor="end")
    p1.label(0.0, ylo + 0.004, "trait clair : le balayage", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Le delta au pic",
               readout="pour cent")
    delta = [(j, 100.0 * CH.delta_du_pic(j / AN)) for j in js]
    p2.domain(0.0, js[-1], 12.0, 28.0)
    p2.frame()
    p2.grid_y([12, 16, 20, 24, 28], lambda v: _num(v, 0) + " %", dx=30.0)
    p2.grid_x([0, 15, 30, 45, 60], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.hline(100.0 * CH.DELTA_ANNONCE, "lvl")
    p2.path(delta, "hm4", tip="le delta au pic")
    p2.label(0.0, 100.0 * CH.DELTA_ANNONCE, "le delta annoncé", dx=8, dy=-6)
    p2.label(js[-1], 100.0 * CH.delta_du_pic(js[-1] / AN), "le delta mesuré",
             dx=-8, dy=14, anchor="end")

    b.legend(0.0, 352.0,
             [("hm7", "le balayage, à gauche"),
              ("hm2", "la forme fermée, à gauche", "5 4"),
              ("hm4", "le delta au pic, à droite")],
             step=200.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le lieu du pic est la racine de la partie XX, celle que la "
                 "partie XXIV a retrouvée sur le pic du vanna")
    b.annotation(0.0, 392.0,
                 "il se tient entre seize et dix-huit deltas, jamais "
                 "vingt-cinq, et son image est vers quatre-vingt-cinq")
    b.annotation(0.0, 408.0,
                 "à un jour, le guide illustre son mécanisme sur un strike "
                 "qui ne porte plus que "
                 + _num(G.delta_comptant(S * (1.0 - CH.ECART_ILLUSTRATION), S,
                                         V, 1.0 / AN, CH.TAUX, CH.DIVIDENDE),
                        4) + " de delta")

    _source(b, "Le cadre de gauche superpose la forme fermée et un balayage "
               "de la moneyness : ils coïncident. La ligne basse est le "
               "strike que le guide choisit pour illustrer son propre "
               "mécanisme, quatre pour cent hors de la monnaie, et l'on voit "
               "qu'à moins de trois semaines le pic n'y est plus. À un jour "
               "il est à un pour cent trois, et l'option qui s'y tient perd "
               "tout son delta dans la nuit ; celle que le guide montre n'en "
               "a plus à perdre. Le cadre de droite convertit le lieu en "
               "delta, la seule coordonnée qu'un pupitre emploie, et la "
               "comparaison avec le nombre annoncé est directe.")
    return b.render("Le lieu du pic de la saignee contre son controle par "
                    "balayage, et le delta de l option qui s y tient.")


def fig_ch_relief_saignee() -> str:
    """Le relief de la saignée."""
    z = [list(l) for l in CH.surface_saignee()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Charm · le relief de la saignée",
               "Deux lobes qui se resserrent sur le strike en grandissant",
               "hauteur : delta par jour")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(j, 0) for j in CH.SURF_ECHEANCE],
             col_labels=[_num(m, 2) for m in CH.SURF_MONEYNESS],
             z_ticks=[(t, _num(t, 2)) for t in _echine(zlo, zhi)],
             tip="{v:.4f} delta par jour", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : l'échéance en jours · arête droite : le "
                 "spot sur le strike · hauteur : le module de la saignée")
    b.annotation(0.0, 424.0,
                 "la crête suit un delta presque constant, donc elle "
                 "s'approche de la monnaie quand l'échéance raccourcit")
    b.annotation(0.0, 440.0,
                 "elle monte comme l'inverse du temps, et le sommet est au "
                 "fond, au dernier jour")

    _source(b, "La hauteur est ce qu'une séance retire au delta d'une "
               "option, à prix immobile. Le relief a la forme que le guide "
               "décrit — une crête qui se resserre sur le strike en "
               "grandissant — et il la contredit sur deux points que le "
               "chiffre porte. La crête ne se tient pas à vingt-cinq deltas "
               "mais à seize, et elle monte comme l'inverse du temps et non "
               "comme sa puissance trois demis. Le coin du fond est le "
               "dernier jour, où une option de seize deltas perd tout ce qui "
               "lui reste ; le sol est le mois, où la même option ne perd "
               "que quelques millièmes par séance.")
    return b.render("Relief du module de la saignee du delta, en echeance et "
                    "en moneyness.")


def fig_ch_monnaie() -> str:
    """La ligne à la monnaie diverge aussi, deux fois moins vite."""
    b = _plate(500, "Charm · la ligne à la monnaie",
               "Elle n'est pas nulle, elle diverge deux fois moins vite",
               "échelle logarithmique")

    js = [0.4 + 0.3 * i for i in range(200)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Les deux amplitudes",
               readout="delta par jour")
    pic = [(math.log10(j), math.log10(G.bleed_du_pic(V, j / AN))) for j in js]
    atm = [(math.log10(j), math.log10(abs(CH.bleed(S, S, j / AN))))
           for j in js]
    xlo, xhi = math.log10(js[0]) - 0.1, math.log10(js[-1]) + 0.1
    ylo = min(y for _, y in atm) - 0.25
    yhi = max(y for _, y in pic) + 0.25
    p1.domain(xlo, xhi, ylo, yhi)
    p1.frame()
    p1.grid_y([v for v in range(int(math.ceil(ylo)), int(math.floor(yhi)) + 1)],
              lambda v: _dec(10.0 ** v), dx=30.0)
    p1.grid_x([-0.3, 0.0, 0.5, 1.0, 1.5], lambda v: _dec(10.0 ** v),
              label="jours à l'échéance")
    p1.path(pic, "hm6", tip="au pic")
    p1.path(atm, "hm2", dash="5 4", tip="à la monnaie")
    p1.label(xlo, math.log10(G.bleed_du_pic(V, js[0] / AN)), "au pic", dx=8,
             dy=10)
    p1.label(xlo, math.log10(abs(CH.bleed(S, S, js[0] / AN))),
             "à la monnaie", dx=8, dy=10)

    p2 = Panel(b, PX2, 92, PW, 214, title="Le rapport des deux",
               readout="facteur")
    rap = [(j, G.bleed_du_pic(V, j / AN) / abs(CH.bleed(S, S, j / AN)))
           for j in js]
    hi = max(y for _, y in rap) * 1.15
    p2.domain(0.0, js[-1], 0.0, hi)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi, 20.0), lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([0, 15, 30, 45, 60], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.path(rap, "hm4", tip="pic sur monnaie")
    p2.dot(1.0, G.bleed_du_pic(V, 1.0 / AN) / abs(CH.bleed(S, S, 1.0 / AN)),
           "hm4", "un jour", r=4.5)
    p2.dot(30.0, G.bleed_du_pic(V, 30.0 / AN)
           / abs(CH.bleed(S, S, 30.0 / AN)), "hm4", "trente jours", r=4.5)
    p2.label(30.0, G.bleed_du_pic(V, 30.0 / AN)
             / abs(CH.bleed(S, S, 30.0 / AN)),
             "à trente jours : "
             + _num(G.bleed_du_pic(V, 30.0 / AN)
                    / abs(CH.bleed(S, S, 30.0 / AN)), 0), dx=-10, dy=-8,
             anchor="end")

    b.legend(0.0, 352.0,
             [("hm6", "au pic, à gauche"),
              ("hm2", "à la monnaie, à gauche", "5 4"),
              ("hm4", "le rapport, à droite")],
             step=200.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le guide explique que sa ligne à la monnaie reste près de "
                 "zéro parce que le delta y vaut un demi jusqu'au bout")
    b.annotation(0.0, 392.0,
                 "la limite est juste, la vitesse ne l'est pas : à la "
                 "monnaie la saignée diverge en racine inverse du temps")
    b.annotation(0.0, 408.0,
                 "ce qui reste près de zéro n'est pas une quantité mais un "
                 "rapport, et ce rapport s'effondre avec l'échéance")

    _source(b, "Les deux axes du cadre de gauche sont logarithmiques, parce "
               "que les deux grandeurs parcourent trois ordres. Deux droites "
               "de pentes différentes s'y lisent d'un coup : l'une descend "
               "comme l'inverse du temps, l'autre comme sa racine inverse, "
               "et aucune ne s'aplatit. La ligne à la monnaie du guide n'est "
               "donc pas plate — elle est petite devant l'autre, et de moins "
               "en moins. Le cadre de droite donne ce rapport, et il "
               "l'exprime dans les termes où la phrase du guide compte : sur "
               "une option d'un mois, négliger la saignée à la monnaie "
               "revient à négliger un dixième de l'objet.")
    return b.render("Les amplitudes au pic et a la monnaie en echelle "
                    "logarithmique, et le rapport des deux.")


# ---------------------------------------------------------------------------
# II. Le week-end
# ---------------------------------------------------------------------------


def fig_ch_plan() -> str:
    """La planche du guide refaite sous les deux horloges."""
    b = _plate(510, "Charm · trois positions, aucun trade",
               "La planche du guide, refaite sous l'horloge de sa série",
               "dix jours")

    # Le trace s arrete un dixieme de jour avant l echeance : au dernier
    # instant le delta est une marche, et la valeur qu une formule y rend
    # depend du portage plutot que de la position.
    jours = [0.0 + 0.2475 * i for i in range(41)]
    positions = [("hm7", "", 1.03, "3 % dans la monnaie"),
                 ("hm5", "6 3", 1.00, "à la monnaie"),
                 ("hm3", "2 3", 0.97, "3 % hors de la monnaie")]

    p1 = Panel(b, PX1, 92, PW, 214, title="Sur l'horloge calendaire",
               readout="delta d'un call")
    p1.domain(0.0, jours[-1], 0.0, 1.05)
    p1.frame()
    p1.band_x(CH.DEBUT_WEEKEND, CH.DEBUT_WEEKEND + CH.JOURS_WEEKEND,
              "band")
    p1.grid_y([0.0, 0.25, 0.50, 0.75, 1.0], lambda v: _num(v, 2), dx=30.0)
    p1.grid_x([0, 2, 4, 6, 8], lambda v: _num(v, 0),
              label="jours écoulés")
    for cls, dash, m, _nom in positions:
        c = [(e, CH.delta_sur_horloge(m, e, 10.0, 1.0)) for e in jours]
        p1.path(c, cls, dash=dash, tip=_nom)
    p1.label(0.0, 1.02, "la bande pâle est le week-end", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Sur l'horloge calibrée",
               readout="delta d'un call")
    p2.domain(0.0, jours[-1], 0.0, 1.05)
    p2.frame()
    p2.band_x(CH.DEBUT_WEEKEND, CH.DEBUT_WEEKEND + CH.JOURS_WEEKEND,
              "band")
    p2.grid_y([0.0, 0.25, 0.50, 0.75, 1.0], lambda v: _num(v, 2), dx=30.0)
    p2.grid_x([0, 2, 4, 6, 8], lambda v: _num(v, 0),
              label="jours écoulés")
    for cls, dash, m, _nom in positions:
        c = [(e, CH.delta_sur_horloge(m, e, 10.0, CH.POIDS_CALIBRE))
             for e in jours]
        p2.path(c, cls, dash=dash, tip=_nom)
    p2.label(0.0, 1.02, "le week-end n'y consomme qu'un jour apparent",
             dx=8, dy=0)

    b.legend(0.0, 362.0,
             [("hm7", "trois pour cent dans la monnaie"),
              ("hm5", "à la monnaie", "6 3"),
              ("hm3", "trois pour cent hors de la monnaie", "2 3")],
             step=200.0, kind="line")
    b.annotation(0.0, 386.0,
                 "trois positions, aucun trade, aucun mouvement de prix : "
                 "tout ce qui bouge est le calendrier")
    b.annotation(0.0, 402.0,
                 "à gauche, l'horloge que le guide suppose ; à droite, celle "
                 "que le guide du thêta de la même série a calibrée")
    b.annotation(0.0, 418.0,
                 "sur le week-end, la marche du cadre de gauche vaut "
                 + _num(CH.facteur_du_calendrier(0.97, 10.0), 1)
                 + " fois celle du cadre de droite, hors de la monnaie")

    _source(b, "C'est la planche du guide, refaite deux fois. À gauche, son "
               "hypothèse : le week-end consomme trois jours de calendrier à "
               "volatilité implicite inchangée, et les trois deltas font une "
               "marche visible en le traversant. À droite, l'hypothèse que "
               "le guide du thêta de la même série a publiée comme une "
               "observation — on ne voit passer qu'un jour — portée par la "
               "hausse d'implicite que la partie XXI en déduit. La marche "
               "s'écrase. Les deux planches ne peuvent pas décrire le même "
               "marché, et l'une des deux a été calibrée sur une mesure. La "
               "bande pâle est peinte avant les tracés, faute de quoi elle "
               "recouvrirait ce qu'elle commente.")
    return b.render("Le delta de trois positions sur dix jours sous les deux "
                    "horloges, calendaire et calibree.")


def fig_ch_horloges() -> str:
    """Le facteur de surestimation contre le paramètre qu'on n'observe pas."""
    b = _plate(500, "Charm · les deux horloges",
               "Le désaccord n'est pas un fait, c'est un paramètre",
               "et l'un des deux guides l'a mesuré")

    ws = [0.02 + 0.005 * i for i in range(197)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Ce que le calendrier surestime",
               readout="facteur")
    courbe = [(w, min(30.0, CH.facteur_du_calendrier(0.97, 10.0, w)))
              for w in ws]
    p1.domain(0.0, 1.0, 0.0, 12.0)
    p1.frame()
    p1.grid_y([0, 3, 6, 9, 12], lambda v: _num(v, 0), dx=26.0)
    p1.grid_x([0.0, 0.25, 0.50, 0.75, 1.0], lambda v: _num(v, 2),
              label="poids d'un jour non ouvré")
    p1.hline(1.0, "lvl")
    p1.path(courbe, "hm6", tip="facteur")
    p1.vline(CH.POIDS_CALIBRE, "lvl")
    p1.dot(CH.POIDS_CALIBRE, CH.facteur_du_calendrier(0.97, 10.0), "hm6",
           "le poids calibre", r=4.5)
    p1.dot(1.0, 1.0, "hm3", "la lecture du guide", r=4.5)
    p1.label(CH.POIDS_CALIBRE, 10.6, "calibré sur l'observation du thêta",
             dx=7, dy=0)
    p1.label(1.0, 1.0, "la lecture du guide du charm", dx=-8, dy=-8,
             anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Les jours qu'un week-end fait voir",
               readout="jours apparents")
    apparents = [(w, th.jours_apparents(w)) for w in ws]
    p2.domain(0.0, 1.0, 0.0, 3.2)
    p2.frame()
    p2.grid_y([0, 1, 2, 3], lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([0.0, 0.25, 0.50, 0.75, 1.0], lambda v: _num(v, 2),
              label="poids d'un jour non ouvré")
    p2.hline(1.0, "lvl")
    p2.hline(3.0, "lvl")
    p2.path(apparents, "hm4", tip="jours apparents")
    p2.dot(CH.POIDS_CALIBRE, 1.0, "hm4", "un jour apparent", r=4.5)
    p2.label(0.0, 1.0, "un jour : ce que le guide du thêta observe", dx=8,
             dy=-6)
    p2.label(0.0, 3.0, "trois jours : ce que le guide du charm suppose",
             dx=8, dy=-6)

    b.legend(0.0, 352.0,
             [("hm6", "le facteur, à gauche"),
              ("hm3", "la lecture du guide du charm"),
              ("hm4", "les jours apparents, à droite")],
             step=200.0)
    b.annotation(0.0, 376.0,
                 "le poids d'un jour non ouvré n'est pas observable ici, "
                 "donc il est balayé plutôt que choisi")
    b.annotation(0.0, 392.0,
                 "à un, on retrouve exactement la lecture calendaire, et le "
                 "facteur vaut un par construction")
    b.annotation(0.0, 408.0,
                 "au poids que la partie XXI calibre sur l'observation "
                 "publiée du guide du thêta, il vaut "
                 + _num(CH.facteur_du_calendrier(0.97, 10.0), 1))

    _source(b, "Les deux documents de cette série supposent deux horloges "
               "différentes pour le même week-end, et le paramètre qui les "
               "sépare n'est pas observable dans ce dépôt. Il est donc "
               "balayé, comme la taille de grappe du footprint et la "
               "volatilité de la volatilité. Ce que la planche ajoute est "
               "que le désaccord n'est pas symétrique : la lecture "
               "calendaire est le bout de la plage, celui où le week-end "
               "consomme tout et où la volatilité implicite ne bouge pas. "
               "Un pupitre qui l'emploie surestime sa dérive de delta quel "
               "que soit le vrai poids, et il la surestime d'autant plus que "
               "le marché reprice davantage.")
    return b.render("Le facteur de surestimation du calendrier contre le "
                    "poids d un jour non ouvre, et les jours apparents.")


def fig_ch_relief_horloge() -> str:
    """Le relief du facteur de surestimation."""
    z = [list(l) for l in CH.surface_horloge()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Charm · le relief des horloges",
               "Le sol est la lecture du guide, et il n'y a rien au-dessous",
               "hauteur : facteur de surestimation")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(w, 2) for w in CH.SURF_POIDS],
             col_labels=[_num(j, 0) for j in CH.SURF_ECHEANCE_WE],
             z_ticks=[(t, _num(t, 0)) for t in _echine(zlo, zhi)],
             tip="{v:.1f} fois", zero=zlo)

    b.annotation(0.0, 408.0,
                 "arête gauche : le poids d'un jour non ouvré · arête "
                 "droite : l'échéance en jours · hauteur : le facteur")
    b.annotation(0.0, 424.0,
                 "la dernière rangée vaut un partout : c'est la lecture du "
                 "guide, et elle est le plancher du relief")
    b.annotation(0.0, 440.0,
                 "le sommet est au fond, sur une option courte dans un "
                 "marché qui reprice presque tout le week-end")

    _source(b, "La hauteur est le rapport entre la saignée que l'horloge "
               "calendaire annonce et celle que l'horloge de bourse rend, "
               "sur une option hors de la monnaie. La rangée du fond du "
               "relief est le poids un — le week-end vaut trois jours "
               "pleins, la volatilité implicite ne bouge pas, et le rapport "
               "vaut un par construction. C'est la lecture du guide du "
               "charm, et c'est le plancher : aucune valeur du paramètre ne "
               "descend au-dessous. Tout le reste du relief est au-dessus, "
               "donc toute autre hypothèse rend la saignée calendaire "
               "surestimée. Le sommet réunit une option courte et un marché "
               "qui reprice presque tout le week-end.")
    return b.render("Relief du facteur de surestimation du calendrier, en "
                    "poids d un jour non ouvre et en echeance.")


# ---------------------------------------------------------------------------
# III. Le coût, le strangle, et le décompte
# ---------------------------------------------------------------------------


def fig_ch_cout() -> str:
    """Ce que coûte de couvrir au delta du soir."""
    b = _plate(500, "Charm · le coût du delta du soir",
               "La règle est juste et son seuil est trop court",
               "friction : " + _num(CH.FRICTION, 2) + " point")

    js = [0.6 + 0.6 * i for i in range(200)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Le coût contre l'échéance",
               readout="en unités de friction")
    pic = [(math.log10(j), math.log10(CH.cout_du_delta_du_soir(j)
                                      / CH.FRICTION)) for j in js]
    atm = [(math.log10(j), math.log10(CH.cout_du_delta_du_soir(j, 1.0)
                                      / CH.FRICTION)) for j in js]
    xlo, xhi = math.log10(js[0]) - 0.1, math.log10(js[-1]) + 0.1
    ylo = min(y for _, y in atm) - 0.3
    yhi = max(y for _, y in pic) + 0.3
    p1.domain(xlo, xhi, ylo, yhi)
    p1.frame()
    p1.grid_y([v for v in range(int(math.ceil(ylo)), int(math.floor(yhi)) + 1)],
              lambda v: _dec(10.0 ** v), dx=30.0)
    p1.grid_x([0.0, 0.7, 1.3, 2.0], lambda v: _dec(10.0 ** v),
              label="jours à l'échéance")
    p1.hline(0.0, "lvl")
    p1.path(pic, "hm6", tip="au pic")
    p1.path(atm, "hm2", dash="5 4", tip="à la monnaie")
    seuil_j = CH.echeance_du_seuil()
    p1.vline(math.log10(seuil_j), "lvl")
    p1.vline(math.log10(CH.SEUIL_ANNONCE), "lvl")
    p1.label(xlo, 0.0, "la friction déclarée", dx=8, dy=-6)
    p1.label(math.log10(seuil_j), yhi - 0.15, _num(seuil_j, 0) + " j", dx=7,
             dy=0)
    p1.label(math.log10(CH.SEUIL_ANNONCE), yhi - 0.45,
             _num(CH.SEUIL_ANNONCE, 0) + " j", dx=-7, dy=0, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="L'erreur de delta d'une séance",
               readout="au pic")
    err = [(j, abs(CH.bleed(S * G.moneyness_du_pic(V, j / AN), S, j / AN)))
           for j in js if j <= 40.0]
    hi = max(y for _, y in err) * 1.20
    p2.domain(0.0, 40.0, 0.0, hi)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi, 0.02), lambda v: _num(v, 2), dx=30.0)
    p2.grid_x([0, 10, 20, 30, 40], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.path(err, "hm4", tip="erreur de delta")
    p2.dot(CH.SEUIL_ANNONCE,
           abs(CH.bleed(S * G.moneyness_du_pic(V, CH.SEUIL_ANNONCE / AN), S,
                        CH.SEUIL_ANNONCE / AN)), "hm4", "deux semaines",
           r=4.5)
    p2.label(0.0, hi * 0.88, "à deux semaines, le coût vaut encore "
             + _num(CH.cout_du_delta_du_soir(CH.SEUIL_ANNONCE) / CH.FRICTION,
                    1) + " frictions", dx=8, dy=0)

    b.legend(0.0, 352.0,
             [("hm6", "au pic, à gauche"),
              ("hm2", "à la monnaie, à gauche", "5 4"),
              ("hm4", "l'erreur de delta, à droite")],
             step=200.0, kind="line")
    b.annotation(0.0, 376.0,
                 "l'erreur de couverture est la saignée d'une séance ; son "
                 "coût est cette erreur fois le déplacement du lendemain")
    b.annotation(0.0, 392.0,
                 "il ne tombe sous la friction de la géométrie déclarée qu'à "
                 + _num(seuil_j, 0) + " jours, pas à "
                 + _num(CH.SEUIL_ANNONCE, 0))
    b.annotation(0.0, 408.0,
                 "à la monnaie le même coût est dix fois plus petit : c'est "
                 "bien sur les ailes qu'il faut réévaluer")

    _source(b, "Les deux axes du cadre de gauche sont logarithmiques, parce "
               "que le coût parcourt trois ordres entre le dernier jour et "
               "le trimestre. La ligne horizontale est la friction de la "
               "géométrie déclarée, celle qui gouverne tout le reste du "
               "document : au-dessus, l'erreur de couverture compte ; "
               "au-dessous, elle ne compte pas. Les deux verticales sont le "
               "seuil que le guide donne et celui que la mesure rend, et "
               "elles ne coïncident pas. La règle est bonne ; elle "
               "s'applique à un mois, pas à deux semaines. La distance entre "
               "les deux courbes dit où l'appliquer d'abord.")
    return b.render("Le cout de couvrir au delta du soir en unites de "
                    "friction, et l erreur de delta d une seance.")


def fig_ch_relief_cout() -> str:
    """Le relief du coût du delta du soir."""
    z = [list(l) for l in CH.surface_cout()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Charm · le relief du coût",
               "Où il faut réévaluer avant de couvrir, et où c'est inutile",
               "hauteur : en unités de friction")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(j, 0) for j in CH.SURF_ECHEANCE_COUT],
             col_labels=[_num(m, 2) for m in CH.SURF_MONEYNESS_COUT],
             z_ticks=[(t, _num(t, 0)) for t in _echine(zlo, zhi)],
             tip="{v:.2f} friction", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : l'échéance en jours · arête droite : le "
                 "spot sur le strike · hauteur : le coût d'une nuit")
    b.annotation(0.0, 424.0,
                 "le plan de hauteur un est la friction : au-dessus il faut "
                 "réévaluer, au-dessous c'est inutile")
    b.annotation(0.0, 440.0,
                 "presque tout le domaine est au sol, et le sommet tient "
                 "dans le dernier jour près de la monnaie")

    _source(b, "La hauteur est ce que coûte, en unités de la friction "
               "déclarée, de couvrir au delta du soir plutôt qu'à celui du "
               "lendemain. Le relief est au sol partout où l'échéance "
               "dépasse le mois ou le strike s'éloigne, et il monte "
               "abruptement dans le coin du dernier jour près de la monnaie, "
               "où il atteint des dizaines de frictions. La règle du guide "
               "est donc juste et sa formulation est trop plate : il ne "
               "s'agit pas de réévaluer « tout ce qui est à moins de deux "
               "semaines », il s'agit de réévaluer ce qui est à la fois "
               "court et proche du strike, et de ne pas s'en occuper "
               "ailleurs. Le relief donne le domaine, ce qu'une règle en "
               "jours ne peut pas faire.")
    return b.render("Relief du cout de couvrir au delta du soir, en echeance "
                    "et en moneyness.")


def fig_ch_strangle() -> str:
    """Le strangle ne saigne pas symétriquement, et la forme fermée le dit."""
    b = _plate(500, "Charm · le strangle",
               "Les deux jambes ne se compensent pas, et la forme fermée le dit",
               "quatorze jours")

    ds = [0.03 + 0.002 * i for i in range(226)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Les deux jambes et leur somme",
               readout="delta par jour")
    jam_c = [(d, CH.strangle(d, 14.0)[0]) for d in ds]
    jam_p = [(d, CH.strangle(d, 14.0)[1]) for d in ds]
    net = [(d, CH.strangle(d, 14.0)[2]) for d in ds]
    hi = max(y for _, y in jam_p) * 1.35
    lo = min(y for _, y in jam_c) * 1.35
    p1.domain(ds[0], ds[-1], lo, hi)
    p1.frame()
    p1.grid_y(_ticks(lo, hi, 0.005), lambda v: _signed(v, 3), dx=34.0)
    p1.grid_x([0.1, 0.2, 0.3, 0.4], lambda v: _num(v, 1),
              label="delta de chaque jambe")
    p1.hline(0.0, "lvl")
    p1.path(jam_c, "hm6", tip="le call")
    p1.path(jam_p, "hm2", dash="6 3", tip="le put")
    p1.path(net, "hm4", tip="la somme")
    p1.label(ds[-1], jam_c[-1][1], "le call", dx=-8, dy=-8, anchor="end")
    p1.label(ds[-1], jam_p[-1][1], "le put", dx=-8, dy=-8, anchor="end")
    p1.label(ds[0], net[0][1], "la somme, jamais nulle", dx=8, dy=-8)

    p2 = Panel(b, PX2, 92, PW, 214, title="La somme et sa forme fermée",
               readout="portage nul")
    mes = [(d, CH.strangle(d, 14.0, V, 0.0, 0.0)[2]) for d in ds]
    fer = [(d, CH.strangle_ferme(d, 14.0)) for d in ds]
    lo2 = min(y for _, y in mes) * 1.30
    p2.domain(ds[0], ds[-1], lo2, 0.0)
    p2.frame()
    p2.grid_y(_ticks(lo2, 0.0, 0.0005), lambda v: _signed(v, 4), dx=38.0)
    p2.grid_x([0.1, 0.2, 0.3, 0.4], lambda v: _num(v, 1),
              label="delta de chaque jambe")
    p2.path(mes, "hm7", tip="la mesure")
    p2.path(fer, "hm2", dash="5 4", tip="la forme fermée")
    p2.label(ds[0], lo2 * 0.30, "trait clair : la mesure", dx=8, dy=0)
    p2.label(ds[0], lo2 * 0.46, "pointillé sombre : la forme fermée", dx=8,
             dy=0)

    b.legend(0.0, 352.0,
             [("hm6", "le call, à gauche"), ("hm2", "le put, à gauche", "6 3"),
              ("hm4", "la somme, à gauche"),
              ("hm7", "la mesure, à droite")],
             step=166.0, kind="line")
    b.annotation(0.0, 376.0,
                 "les deux jambes d'un strangle symétrique en delta ont des "
                 "arguments opposés, et leur somme laisse un terme entier")
    b.annotation(0.0, 392.0,
                 "elle n'est nulle à aucun delta : les deux jambes perdent "
                 "leur delta, et le livre raccourcit en le faisant")
    b.annotation(0.0, 408.0,
                 "la part non compensée passe de "
                 + _num(100 * abs(CH.strangle(0.10, 7.0)[2])
                        / CH.strangle(0.10, 7.0)[3], 0) + " % à "
                 + _num(100 * abs(CH.strangle(0.40, 90.0)[2])
                        / CH.strangle(0.40, 90.0)[3], 0) + " % selon le "
                 "delta et l'échéance")

    _source(b, "Le cadre de gauche pose les deux jambes et leur somme sur le "
               "même axe : la somme est visiblement au-dessous de zéro sur "
               "toute la plage, et elle s'en éloigne quand les jambes se "
               "rapprochent de la monnaie. Le cadre de droite est le "
               "contrôle, fait à portage nul pour que la forme fermée soit "
               "comparable : la mesure et la forme se superposent, et c'est "
               "pour cela que le contrôle passe dessous en trait clair et la "
               "forme fermée par-dessus en pointillé sombre. Le taux et le "
               "dividende doublent l'effet sans le créer.")
    return b.render("Les deux jambes d un strangle et leur somme contre le "
                    "delta, et le controle de la forme fermee a portage nul.")


def fig_ch_relief_strangle() -> str:
    """Le relief de la part non compensée."""
    z = [list(l) for l in CH.surface_strangle()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Charm · le relief du strangle",
               "Il n'existe aucune structure symétrique neutre en charm",
               "hauteur : part non compensée")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(100 * d, 0) for d in CH.SURF_DELTA],
             col_labels=[_num(j, 0) for j in CH.SURF_ECHEANCE_STR],
             z_ticks=[(t, _num(t, 0)) for t in _echine(zlo, zhi)],
             tip="{v:.0f} % non compense", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : le delta de chaque jambe · arête droite : "
                 "l'échéance en jours · hauteur : la part non compensée")
    b.annotation(0.0, 424.0,
                 "elle ne descend nulle part à zéro : aucune combinaison ne "
                 "rend le strangle neutre")
    b.annotation(0.0, 440.0,
                 "elle atteint cent au coin du fond, où les deux jambes ne "
                 "se compensent plus du tout")

    _source(b, "La hauteur est la part du charm brut qui reste après que les "
               "deux jambes se sont compensées. Si la phrase du guide était "
               "juste, ce relief serait au sol partout. Il ne l'est nulle "
               "part : il monte du dixième au tout, et le coin du fond — des "
               "jambes proches de la monnaie sur une option longue — est "
               "celui où la compensation n'existe plus du tout. La bonne "
               "formulation n'est pas qu'un strangle se compense et qu'un "
               "vertical non ; c'est qu'aucune structure symétrique en delta "
               "n'est neutre en charm, et qu'il faut le calculer pour "
               "chacune plutôt que de le déduire de sa forme.")
    return b.render("Relief de la part non compensee du charm d un strangle, "
                    "en delta et en echeance.")


def fig_ch_agregation() -> str:
    """Ce que le charm ne demande pas, et ce que les deux autres demandaient."""
    a1 = seuil.geometry(0.150).stop_points
    lo_g, _, hi_g, abs_g = nv.bande_de_bascule(0.0)
    hist, lo_v, _, hi_v = va.compte_de_lignes(0.0, 0.0)

    b = _plate(490, "Charm · l'agrégation",
               "La seule affirmation d'agrégation des sept parties qui tienne",
               "trois grecs, trois verdicts")

    familles = [("Gamma, XIX", 1.0, (hi_g - lo_g) / a1),
                ("Vanna, XXIV", 2.0, (hi_v - lo_v) / a1),
                ("Charm, XXV", 0.0, 0.0)]

    p1 = Panel(b, PX1, 92, PW, 214, title="Ce qu'il faut deviner",
               readout="paramètres non observables")
    p1.domain(-0.6, len(familles) - 0.4, 0.0, 2.6)
    p1.frame()
    p1.grid_y([0, 1, 2], lambda v: _num(v, 0), dx=26.0)
    for i, (nom, n, _) in enumerate(familles):
        cls = "hm7" if n == 0 else "hm4"
        if n:
            p1.vbar(i, 0.0, n, 52.0, cls, tip=nom)
        p1.label(i, n, _num(n, 0), dx=0, dy=-8, anchor="middle")
        p1.label(i, 0.0, nom, dx=0, dy=16, anchor="middle")
    p1.label(0.0, 2.35, "le charm n'en demande aucun", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce que cela coûte",
               readout="en stops élargis")
    haut = max(v for _, _, v in familles) * 1.30
    p2.domain(-0.6, len(familles) - 0.4, 0.0, haut)
    p2.frame()
    p2.grid_y(_ticks(0.0, haut, 50.0), lambda v: _num(v, 0), dx=26.0)
    for i, (nom, n, v) in enumerate(familles):
        cls = "hm7" if n == 0 else "hm4"
        if v:
            p2.vbar(i, 0.0, v, 52.0, cls, tip=nom)
        p2.label(i, v, _num(v, 0), dx=0, dy=-8, anchor="middle")
        p2.label(i, 0.0, nom, dx=0, dy=16, anchor="middle")
    p2.label(0.0, haut * 0.86, "largeur de la bande du niveau", dx=8, dy=0)

    b.legend(0.0, 342.0,
             [("hm4", "il faut deviner un signe"),
              ("hm7", "il ne faut rien deviner")],
             step=240.0)
    b.annotation(0.0, 366.0,
                 "le gamma agrégé demandait le signe d'un inventaire, le "
                 "vanna en demandait deux, le charm n'en demande aucun")
    b.annotation(0.0, 382.0,
                 "parce qu'il s'emploie sur son propre livre : il dit "
                 "comment une exposition connue bougera si l'on ne fait rien")
    b.annotation(0.0, 398.0,
                 "employé comme niveau de marché, il hérite de tout ce que "
                 "les parties XIX et XXIV ont chiffré")

    _source(b, "Le guide écrit que le charm, contrairement aux agrégats de "
               "gamma et de vanna, ne demande pas de savoir qui est long ou "
               "court : il dit comment votre propre exposition bougera si "
               "vous ne faites rien, ce qui est un outil de planification et "
               "non une prévision. C'est exact, et c'est la seule "
               "affirmation d'agrégation des sept documents que ce dépôt "
               "reprenne sans réserve. Les deux cadres disent pourquoi. Le "
               "gamma agrégé de la partie XIX demandait un paramètre "
               "inobservable et faisait errer son niveau sur cent trente-cinq "
               "stops élargis ; le vanna de la partie XXIV en demandait deux "
               "et rendait le plus souvent trois lignes au lieu d'une. La "
               "question que le charm pose n'en comporte aucun, parce qu'elle "
               "porte sur un livre qu'on connaît. Le guide ajoute que le même "
               "objet employé comme niveau de marché hérite de tout, et il a "
               "raison là aussi.")
    return b.render("Le nombre de parametres non observables des trois "
                    "agregats, et la largeur de bande qui en resulte.")


def fig_ch_reste() -> str:
    """Le décompte des huit affirmations, et le cumul des sept parties."""
    aff = CH.affirmations()
    compte = CH.compte_par_grandeur()
    ordre = sorted(compte, key=lambda g: (-compte[g], g))
    fam = CH.familles()
    total = sum(n for _, n in fam)

    b = _plate(480, "Charm · le décompte",
               "Cinquante et une affirmations, et aucune ne donne un sens",
               _num(len(aff), 0) + " ici")

    p1 = Panel(b, PX1, 92, PW, 214, title="Ce qu'elles déplacent",
               readout="affirmations")
    lignes = list(ordre) + [g for g in ("la direction",) if g not in ordre]
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

    p2 = Panel(b, PX2, 92, PW, 214, title="Les sept parties",
               readout="affirmations")
    haut = max(n for _, n in fam) * 1.35
    p2.domain(0.0, haut, -0.6, len(fam) - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, haut, 3.0), lambda v: _num(v, 0))
    for i, (nom, n) in enumerate(fam):
        y = len(fam) - 1 - i
        p2.hbar(y, 0.0, n, 9.0, "hm3", tip=nom)
        p2.label(0.0, y + 0.28, nom, dx=4, dy=0)
        p2.label(n, y, _num(n, 0), dx=7, dy=4)

    b.legend(0.0, 352.0,
             [("hm7", "touche à la direction"),
              ("hm5", "l'horloge ou le risque"),
              ("hm1", "ne déplace rien"),
              ("hm3", "les totaux, à droite")],
             step=166.0)
    b.annotation(0.0, 376.0,
                 _num(compte.get("le risque", 0), 0) + " affirmations "
                 "déplacent le risque, "
                 + _num(compte.get("l'horloge", 0), 0) + " l'horloge, "
                 + _num(compte.get("rien", 0), 0) + " ne déplacent rien")
    b.annotation(0.0, 392.0,
                 "la barre de la direction est vide pour la troisième partie "
                 "d'options consécutive")
    b.annotation(0.0, 408.0,
                 "sur les " + _num(total, 0) + " affirmations des sept "
                 "parties, aucune ne donne un sens")

    _source(b, "Sept documents, cinquante et une affirmations, et la colonne "
               "de la direction est vide. Ce n'est pas un reproche adressé à "
               "ces guides : ils décrivent correctement des grandeurs qui "
               "existent, et le dernier fait mieux que les six autres sur "
               "deux points. Il nomme l'usage où son objet est fiable — le "
               "livre qu'on connaît — et il nomme celui où il ne l'est pas, "
               "en renvoyant lui-même au document sur le gamma. C'est un "
               "protocole, et c'est ce que ce document demande depuis sa "
               "quatrième partie. Le décompte, lui, ne bouge pas : ces "
               "grandeurs sont des propriétés de la géométrie, de l'horloge "
               "et du risque, jamais du sens.")
    return b.render("Le decompte des affirmations par ce qu elles deplacent, "
                    "et le cumul des sept parties d options.")


def fig_ch_vertical() -> str:
    """Le strangle et le vertical, et la différence qui n'est pas celle qu'on dit."""
    b = _plate(490, "Charm · le vertical",
               "La différence entre les deux structures est un facteur, non un contraste",
               "")

    js = [3.0 + 1.5 * i for i in range(120)]
    p1 = Panel(b, PX1, 92, PW, 214, title="La part non compensée",
               readout="pour cent du brut")
    stra = [(j, 100.0 * abs(CH.strangle(0.25, j)[2]) / CH.strangle(0.25, j)[3])
            for j in js]
    vert = [(j, 100.0 * abs(CH.vertical(0.40, 0.20, j)[0])
             / CH.vertical(0.40, 0.20, j)[1]) for j in js]
    hi = max(max(y for _, y in stra), max(y for _, y in vert)) * 1.30
    p1.domain(0.0, js[-1], 0.0, hi)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi, 10.0), lambda v: _num(v, 0) + " %", dx=30.0)
    p1.grid_x([0, 50, 100, 150], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.path(vert, "hm6", tip="l'écart vertical")
    p1.path(stra, "hm2", dash="5 4", tip="le strangle")
    p1.label(js[-1], vert[-1][1], "l'écart vertical", dx=-8, dy=-8,
             anchor="end")
    p1.label(js[-1], stra[-1][1], "le strangle", dx=-8, dy=14, anchor="end")
    p1.label(0.0, hi * 0.92, "cent pour cent : aucune compensation", dx=8,
             dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Le rapport des deux nets",
               readout="facteur")
    rap = [(j, abs(CH.vertical(0.40, 0.20, j)[0] / CH.strangle(0.25, j)[2]))
           for j in js]
    hi2 = max(y for _, y in rap) * 1.25
    p2.domain(0.0, js[-1], 0.0, hi2)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2, 1.0), lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([0, 50, 100, 150], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.hline(1.0, "lvl")
    p2.path(rap, "hm4", tip="vertical sur strangle")
    p2.label(0.0, 1.0, "un : les deux saignent autant", dx=8, dy=-6)
    p2.label(js[-1], rap[-1][1], "au-delà, le strangle saigne plus", dx=-8,
             dy=14, anchor="end")

    b.legend(0.0, 342.0,
             [("hm6", "l'écart vertical, à gauche"),
              ("hm2", "le strangle, à gauche", "5 4"),
              ("hm4", "le rapport, à droite")],
             step=200.0, kind="line")
    b.annotation(0.0, 366.0,
                 "la seconde moitié de la note du guide tient : un vertical "
                 "porte deux jambes du même côté et ne compense rien")
    b.annotation(0.0, 382.0,
                 "ce qu'il n'écrit pas est que le strangle ne fait guère "
                 "mieux, et qu'il fait pire au-delà de quelques mois")
    b.annotation(0.0, 398.0,
                 "aucune structure symétrique en delta n'est neutre en "
                 "charm : il faut le calculer pour chacune")

    _source(b, "Le guide oppose deux structures — le strangle qui "
               "compenserait, le vertical qui ne compenserait pas — et la "
               "planche montre que le contraste n'existe pas. Les deux "
               "courbes du cadre de gauche se rejoignent, et elles se "
               "croisent : au-delà de quelques mois c'est le strangle qui "
               "laisse la plus grande part non compensée. Le cadre de droite "
               "donne le rapport des deux nets, et il traverse un. La "
               "distinction utile n'est donc pas celle de la forme mais "
               "celle du calcul, et c'est la conclusion que ce dépôt tire de "
               "toutes ses parties d'options : un nombre résumé se vérifie, "
               "il ne se déduit pas d'une figure.")
    return b.render("La part non compensee du charm d un strangle et d un "
                    "ecart vertical contre l echeance, et le rapport des "
                    "deux nets.")


def fig_ch_weekend() -> str:
    """La saignée d'un week-end, par moneyness, sous les deux horloges."""
    b = _plate(500, "Charm · le week-end",
               "Trois jours de saignée, ou un — la série ne s'accorde pas",
               "dix jours à l'échéance")

    ms = [0.92 + 0.0016 * i for i in range(101)]
    p1 = Panel(b, PX1, 92, PW, 214, title="La saignée d'un week-end",
               readout="delta")
    cal = [(m, CH.saignee_calendaire(m, 10.0)) for m in ms]
    hor = [(m, CH.saignee_horloge(m, 10.0, CH.POIDS_CALIBRE)) for m in ms]
    hi = max(y for _, y in cal) * 1.30
    lo = min(y for _, y in cal) * 1.30
    p1.domain(ms[0], ms[-1], lo, hi)
    p1.frame()
    p1.grid_y(_ticks(lo, hi, 0.02), lambda v: _signed(v, 2), dx=34.0)
    p1.grid_x([0.94, 0.98, 1.02, 1.06], lambda v: _num(v, 2),
              label="spot sur strike")
    p1.hline(0.0, "lvl")
    p1.vline(1.0, "lvl")
    p1.path(cal, "hm6", tip="sur le calendrier")
    p1.path(hor, "hm2", dash="5 4", tip="sur l'horloge calibrée")
    p1.label(ms[0], hi * 0.84, "trait plein : le calendrier", dx=8, dy=0)
    p1.label(ms[0], hi * 0.68, "pointillé : l'horloge calibrée", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="De combien le calendrier surestime",
               readout="facteur")
    js = [4.5 + 0.4 * i for i in range(120)]
    series = [("hm7", "", 0.97, "hors de la monnaie"),
              ("hm4", "6 3", 1.00, "à la monnaie"),
              ("hm1", "2 3", 1.03, "dans la monnaie")]
    courbes = [(cls, dash, [(j, CH.facteur_du_calendrier(m, j)) for j in js])
               for cls, dash, m, _n in series]
    hi2 = max(y for _, _, c in courbes for _, y in c) * 1.20
    p2.domain(js[0], js[-1], 0.0, hi2)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2, 1.0), lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([10, 20, 30, 40, 50], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.hline(1.0, "lvl")
    for cls, dash, c in courbes:
        p2.path(c, cls, dash=dash, tip="facteur")
    p2.label(js[0], 1.0, "un : les deux horloges s'accordent", dx=8, dy=-6)

    b.legend(0.0, 352.0,
             [("hm6", "le calendrier, à gauche"),
              ("hm2", "l'horloge calibrée, à gauche", "5 4"),
              ("hm7", "hors de la monnaie, à droite"),
              ("hm4", "à la monnaie, à droite", "6 3")],
             step=166.0, kind="line")
    b.annotation(0.0, 376.0,
                 "les deux lobes du cadre de gauche sont la saignée d'un "
                 "week-end, et le pointillé est le même week-end reprice")
    b.annotation(0.0, 392.0,
                 "l'écart est le plus grand sur les ailes, où le guide dit "
                 "que les positions dérivent le plus")
    b.annotation(0.0, 408.0,
                 "à la monnaie les deux horloges s'accordent, parce que le "
                 "delta y est immobile de toute façon")

    _source(b, "Le cadre de gauche superpose la même grandeur sous les deux "
               "hypothèses : la variation de delta qu'un week-end produit, à "
               "prix immobile, sur une option de dix jours. Le trait plein "
               "est l'horloge calendaire du guide du charm ; le pointillé "
               "est celle que le guide du thêta de la même série a permis de "
               "calibrer, où la volatilité implicite monte assez pour que la "
               "variance restant à courir ne tombe que d'un jour apparent. "
               "Le cadre de droite donne le rapport des deux par échéance et "
               "par moneyness. Il vaut un à la monnaie et trois à quatre sur "
               "les ailes, et il ne descend jamais au-dessous d'un : quelle "
               "que soit la valeur du paramètre, la lecture calendaire "
               "surestime.")
    return b.render("La saignee d un week-end contre la moneyness sous les "
                    "deux horloges, et le facteur de surestimation par "
                    "echeance.")


def render_all() -> dict[str, str]:
    """Les quinze planches, dans l'ordre du document."""
    return {
        "chaccel": fig_ch_accel(),
        "chpic": fig_ch_pic(),
        "chreliefs": fig_ch_relief_saignee(),
        "chmonnaie": fig_ch_monnaie(),
        "chplan": fig_ch_plan(),
        "chweekend": fig_ch_weekend(),
        "chhorloges": fig_ch_horloges(),
        "chreliefh": fig_ch_relief_horloge(),
        "chcout": fig_ch_cout(),
        "chreliefc": fig_ch_relief_cout(),
        "chstrangle": fig_ch_strangle(),
        "chreliefstr": fig_ch_relief_strangle(),
        "chvertical": fig_ch_vertical(),
        "chagregation": fig_ch_agregation(),
        "chreste": fig_ch_reste(),
    }
