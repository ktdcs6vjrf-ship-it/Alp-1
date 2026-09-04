"""Les planches de « la convexité en volatilité, et le sourire qu'on en tire ».

Quinze planches, onze à plat et quatre en relief. La quatrième refait la
planche du guide par trois routes, et montre que le retournement qu'elle
affiche appartient à son approximation.

Comme les cinq modules d'options qui précèdent, celui-ci importe ses fonctions
d'échine, de graduation et de décade de `fignv`.
"""

from __future__ import annotations

import math

from . import grandeurs as G
from . import theta as th
from . import vega as vg
from . import volga as VO
from .figdisc import W, _plate, _source, _surface
from .fignv import _dec, _echine, _pct, _ticks
from .figterm import Board, Panel, _num, _signed


PW = (W - 74.0) / 2.0 - 30.0
PX1 = 74.0
PX2 = 74.0 + (W - 74.0) / 2.0

S = VO.S_REF
V = VO.VOL_REF
AN = VO.JOURS_AN


def _vo(m: float, j: float) -> float:
    return VO.volga(S * m, S, V, j / AN)


# ---------------------------------------------------------------------------
# I. Les deux bosses, et la bande entre elles
# ---------------------------------------------------------------------------


def fig_vo_profil() -> str:
    """Le profil à deux bosses, et le rapport qui gouverne tout."""
    b = _plate(500, "Volga · le profil",
               "Deux bosses, et un creux si étroit que rien n'y tombe",
               _num(100 * V, 0) + " % de volatilité")

    ms = [0.55 + 0.0045 * i for i in range(201)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Le volga contre le comptant",
               readout="par unité de volatilité")
    series = [("hm7", "", 30.0), ("hm5", "6 3", 90.0), ("hm3", "2 3", 180.0),
              ("hm1", "1 4", 365.0)]
    courbes = [(cls, dash, j, [(m, _vo(m, j)) for m in ms])
               for cls, dash, j in series]
    hi = max(y for _, _, _, c in courbes for _, y in c) * 1.30
    p1.domain(ms[0], ms[-1], -0.06 * hi, hi)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi, 30.0), lambda v: _num(v, 0), dx=26.0)
    p1.grid_x([0.6, 0.8, 1.0, 1.2, 1.4], lambda v: _num(v, 1),
              label="spot sur strike")
    p1.hline(0.0, "lvl")
    p1.vline(1.0, "lvl")
    for cls, dash, j, c in courbes:
        p1.path(c, cls, dash=dash, tip=_num(j, 0) + " jours")
    p1.label(1.0, hi * 0.94, "nul à la monnaie", dx=8, dy=0)
    p1.label(ms[0], hi * 0.72, "deux bosses, une par aile", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="La bande où il est négatif",
               readout="% du comptant")
    js = [3.0 + 3.6 * i for i in range(120)]
    largeur = [(j, 100.0 * VO.largeur_de_bande(j / AN)) for j in js]
    hi2 = max(y for _, y in largeur) * 1.25
    p2.domain(0.0, js[-1], 0.0, hi2)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2, 2.0), lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([0, 100, 200, 300, 400], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.path(largeur, "hm4", tip="largeur de la bande")
    p2.hline(1.0, "lvl")
    p2.label(js[-1], 1.0, "le pas d'une grille de strikes", dx=-8, dy=-8,
             anchor="end")
    p2.dot(30.0, 100.0 * VO.largeur_de_bande(30.0 / AN), "hm4",
           "trente jours", r=4.5)
    p2.label(30.0, 100.0 * VO.largeur_de_bande(30.0 / AN),
             _num(100 * VO.largeur_de_bande(30.0 / AN), 2) + " %", dx=10,
             dy=8)

    b.legend(0.0, 352.0,
             [("hm7", "trente jours"), ("hm5", "trois mois", "6 3"),
              ("hm3", "six mois", "2 3"), ("hm1", "un an", "1 4"),
              ("hm4", "la bande, à droite")],
             step=132.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le facteur est le produit des deux arguments : petits et "
                 "opposés au centre, grands et de même signe aux ailes")
    b.annotation(0.0, 392.0,
                 "elle porte trois noms dans trois parties, a exactement la "
                 "même largeur, et deux centres que le portage sépare")
    b.annotation(0.0, 408.0,
                 "elle mesure " + _num(100 * VO.largeur_de_bande(30.0 / AN),
                                       2) + " % du comptant à trente jours, "
                 "sous le pas d'une grille de strikes")

    _source(b, "Le cadre de gauche montre l'objet que le guide décrit : un "
               "profil à deux bosses, nul à la monnaie, dont les sommets "
               "s'éloignent et s'aplatissent quand l'échéance s'allonge. Le "
               "creux central, lui, ne se voit pas à cette échelle, et c'est "
               "le sujet du cadre de droite. Le guide parle de « près de la "
               "monnaie » sans le chiffrer ; ce document l'a déjà chiffré "
               "deux fois, pour deux motifs sans rapport — la partie XXII "
               "comme la bande où l'on ne peut pas compenser une aile par "
               "une option à la monnaie, la partie XXIV comme celle où le "
               "vanna cesse d'obéir à sa règle. C'est le même intervalle, et "
               "sa largeur en logarithme vaut sigma carré T dans les trois "
               "cas.")
    return b.render("Le volga contre le comptant a quatre echeances, et la "
                    "largeur de la bande ou il est negatif.")


def fig_vo_courbure() -> str:
    """La droite et la crosse de hockey, mesurées à la corde."""
    b = _plate(500, "Volga · la droite et la crosse",
               "Le prix d'une option à la monnaie est une droite, pas presque",
               "trois mois")

    t = 90.0 / AN
    vols = [VO.VOL_BASSE + (VO.VOL_HAUTE - VO.VOL_BASSE) * i / 200
            for i in range(201)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Le prix contre la volatilité",
               readout="rapporté à son maximum")
    series = [("hm7", "", 1.00), ("hm5", "6 3", 1.15), ("hm3", "2 3", 1.30)]
    p1.domain(vols[0], vols[-1], 0.0, 1.08)
    p1.frame()
    for cls, dash, m in series:
        k = S * m
        ps = [th.call(S, k, v, t, VO.TAUX, VO.DIVIDENDE) for v in vols]
        haut = ps[-1]
        p1.path([(v, p / haut) for v, p in zip(vols, ps)], cls, dash=dash,
                tip=_num(100 * (m - 1.0), 0) + " % hors de la monnaie")
    p1.grid_y([0.0, 0.25, 0.50, 0.75, 1.0], lambda v: _num(v, 2), dx=30.0)
    p1.grid_x([0.1, 0.3, 0.5, 0.7], lambda v: _pct(v, 0), label="volatilité")
    p1.label(vols[0], 1.02, "trait plein : à la monnaie, une droite", dx=8,
             dy=0)
    p1.label(vols[-1], 0.10, "tirets serrés : trente pour cent", dx=-8, dy=0,
             anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="L'écart à la corde",
               readout="% du prix")
    ecarts = [0.0 + 0.0018 * i for i in range(201)]
    courbe = [(100 * e, 100.0 * VO.ecart_a_la_corde(1.0 + e, t, 120))
              for e in ecarts]
    hi = max(y for _, y in courbe) * 1.22
    p2.domain(0.0, 100 * ecarts[-1], 0.0, hi)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi, 10.0), lambda v: _num(v, 0) + " %", dx=30.0)
    p2.grid_x([0, 10, 20, 30], lambda v: _num(v, 0),
              label="écart hors de la monnaie (%)")
    p2.path(courbe, "hm4", tip="écart à la corde")
    p2.dot(0.0, 100.0 * VO.ecart_a_la_corde(1.0, t), "hm4", "à la monnaie",
           r=4.5)
    p2.label(0.0, 100.0 * VO.ecart_a_la_corde(1.0, t),
             "à la monnaie : " + _num(100 * VO.ecart_a_la_corde(1.0, t), 2)
             + " %", dx=10, dy=-6)

    b.legend(0.0, 352.0,
             [("hm7", "à la monnaie"),
              ("hm5", "quinze pour cent hors", "6 3"),
              ("hm3", "trente pour cent hors", "2 3"),
              ("hm4", "l'écart, à droite")],
             step=166.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le guide dit que la ligne à la monnaie est proche d'une "
                 "droite et que celle des ailes est une crosse de hockey")
    b.annotation(0.0, 392.0,
                 "les deux moitiés tiennent, et la première se renforce : "
                 "l'écart à la corde y vaut un dixième de pour cent")
    b.annotation(0.0, 408.0,
                 "il monte à "
                 + _num(100 * VO.ecart_a_la_corde(1.30, t), 0)
                 + " % à trente pour cent de la monnaie, et c'est cela que "
                 "le marché facture")

    _source(b, "Le cadre de gauche est la planche de droite du guide, "
               "refaite : chaque prix est rapporté à sa propre valeur au "
               "bout haut, pour que trois options de tailles très "
               "différentes se lisent sur le même axe. La ligne à la monnaie "
               "est une droite, et pas une approximation de droite. Le cadre "
               "de droite mesure ce que « proche » veut dire, par l'écart "
               "maximal à la corde qui joint les deux bouts : un dixième de "
               "pour cent à la monnaie, un tiers du prix à trente pour cent "
               "hors. C'est la convexité que le guide dit que le marché "
               "facture, et il a raison de le dire.")
    return b.render("Le prix contre la volatilite a trois moneyness, et "
                    "l ecart maximal a la corde.")


def fig_vo_relief_volga() -> str:
    """Le relief du volga."""
    z = [list(l) for l in VO.surface_volga()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Volga · le relief de la convexité",
               "La crête s'éloigne de la monnaie quand l'échéance s'allonge",
               "hauteur : volga")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(j, 0) for j in VO.SURF_ECHEANCE],
             col_labels=[_num(m, 2) for m in VO.SURF_MONEYNESS],
             z_ticks=[(t, _num(t, 0)) for t in _echine(zlo, zhi)],
             tip="{v:.1f}", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : l'échéance en jours · arête droite : le "
                 "spot sur le strike · hauteur : le volga")

    b.annotation(0.0, 424.0,
                 "le sol court le long de la monnaie, où le volga s'annule "
                 "et où le prix est linéaire en volatilité")
    b.annotation(0.0, 440.0,
                 "et la crête s'éloigne de la monnaie quand l'échéance "
                 "s'allonge : "
                 + _num(VO.crete_du_volga(10.0 / AN), 2) + " à dix jours, "
                 + _num(VO.crete_du_volga(180.0 / AN), 2) + " à six mois")

    _source(b, "La hauteur est la courbure du prix en volatilité, sur une "
               "seule option. Le sol longe la monnaie, et ce n'est pas un "
               "artefact de la grille : le volga y est exactement nul, et "
               "c'est ce qui rend le prix d'une option à la monnaie linéaire "
               "en volatilité. La crête monte vers l'aile, où le prix "
               "devient une crosse de hockey, et elle s'en éloigne à "
               "mesure que l'échéance s'allonge, parce que la largeur de la "
               "zone convexe croît comme la racine du temps. C'est ce relief "
               "que le guide convertit en sourire : l'incertitude sur la "
               "volatilité vaut cher là où la hauteur est grande, et rien là "
               "où elle est nulle.")
    return b.render("Relief du volga, en echeance et en moneyness.")


# ---------------------------------------------------------------------------
# II. Le sourire, et les trois routes
# ---------------------------------------------------------------------------


def fig_vo_sourire() -> str:
    """La planche du guide, refaite par trois routes."""
    b = _plate(510, "Volga · le sourire",
               "Trois routes vers le même sourire, et trois sourires",
               "un mois, vol de vol " + _num(100 * VO.NU, 0) + " %")

    t = 30.0 / AN
    ks = [70.0 + 0.6 * i for i in range(101)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Les trois lectures",
               readout="volatilité implicite")
    naif = [(k, 100.0 * VO.sourire_naif(k, t)) for k in ks]
    o2 = [(k, 100.0 * VO.sourire_second_ordre(k, t)) for k in ks]
    ex = [(k, 100.0 * VO.sourire_exact(k, t)) for k in ks]
    hi = max(y for _, y in naif) * 1.12
    p1.domain(ks[0], ks[-1], 20.0, hi)
    p1.frame()
    p1.grid_y(_ticks(20.0, hi, 10.0), lambda v: _num(v, 0) + " %", dx=34.0)
    p1.grid_x([70, 90, 110, 130], lambda v: _num(v, 0), label="strike")
    p1.hline(100.0 * V, "lvl")
    p1.path(naif, "hm1", dash="2 3", tip="inversion au premier ordre")
    p1.path(ex, "hm7", tip="espérance exacte")
    p1.path(o2, "hm3", dash="6 3", tip="second ordre inversé")
    p1.label(ks[0], 100.0 * V, "la volatilité d'entrée", dx=8, dy=-6)
    p1.label(ks[0], naif[0][1], "premier ordre", dx=8, dy=10)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Chaque route rapportée à l'exact",
               readout="au strike soixante-dix")
    j0 = VO.tenor_inversible(70.0)
    js = [j0 * (730.0 / j0) ** (i / 120.0) for i in range(121)]
    rn, ro = [], []
    for j in js:
        tt = j / AN
        e = VO.sourire_exact(70.0, tt)
        rn.append((math.log10(j), VO.sourire_naif(70.0, tt) / e))
        ro.append((math.log10(j), VO.sourire_second_ordre(70.0, tt) / e))
    hi2 = max(y for _, y in rn) * 1.10
    lo2 = min(y for _, y in ro) * 0.92
    p2.domain(math.log10(js[0]), math.log10(js[-1]), lo2, hi2)
    p2.frame()
    p2.grid_y(_ticks(lo2, hi2, 0.5), lambda v: _num(v, 1), dx=26.0)
    p2.grid_x([math.log10(30.0), 2.0, math.log10(730.0)],
              lambda v: _num(10.0 ** v, 0), label="jours à l'échéance")
    p2.hline(1.0, "lvl")
    p2.path(rn, "hm1", dash="2 3", tip="premier ordre sur exact")
    p2.path(ro, "hm3", dash="6 3", tip="second ordre sur exact")
    p2.label(math.log10(js[-1]), 1.0, "l'exact", dx=-8, dy=-8, anchor="end")
    p2.dot(math.log10(j0), rn[0][1], "hm1", "le plus court ténor inversible",
           r=4.5)
    p2.label(math.log10(j0), rn[0][1],
             _num(100 * VO.sourire_naif(70.0, j0 / AN), 0) + " % au lieu de "
             + _num(100 * VO.sourire_exact(70.0, j0 / AN), 0), dx=9, dy=4)

    b.legend(0.0, 362.0,
             [("hm7", "espérance exacte"),
              ("hm3", "second ordre inversé", "6 3"),
              ("hm1", "inversion au premier ordre", "2 3")],
             step=200.0, kind="line")
    b.annotation(0.0, 386.0,
                 "le mécanisme du guide est juste : la convexité en "
                 "volatilité monte le prix des ailes et pas celui du corps")
    b.annotation(0.0, 402.0,
                 "les trois routes rendent "
                 + _num(100 * VO.sourire_naif(70.0, t), 0) + ", "
                 + _num(100 * VO.sourire_second_ordre(70.0, t), 0) + " et "
                 + _num(100 * VO.sourire_exact(70.0, t), 0)
                 + " pour cent au strike soixante-dix")
    b.annotation(0.0, 418.0,
                 "sous "
                 + _num(VO.tenor_inversible(70.0), 0)
                 + " jours le second ordre ne corrige plus rien : sa "
                 "correction tombe sous le plancher d'un flottant")

    _source(b, "Le guide dérive le sourire d'une inégalité de Jensen, sans "
               "peau supposée et sans flux modélisé, et c'est le seul des "
               "huit documents qui explique une observation de marché au "
               "lieu de la décrire. Le mécanisme tient. Ce que le cadre de "
               "gauche montre est que la route compte autant que lui : "
               "diviser la correction de prix par le véga suppose le prix "
               "linéaire en volatilité, ce que la section précédente du même "
               "guide vient de réfuter, et cela double la volatilité "
               "d'entrée sur une aile. Le cadre de droite donne le résultat "
               "honnête, par ténor : le sourire que ce mécanisme produit "
               "vaut neuf points sur un mois et deux sur un an, et il est "
               "réel.")
    return b.render("Le sourire par trois routes au strike de la planche du "
                    "guide, et ce qu il vaut vraiment par tenor.")


def fig_vo_retournement() -> str:
    """Le retournement appartient à l'approximation, pas au modèle."""
    b = _plate(500, "Volga · le retournement",
               "La planche du guide se retourne, et son modèle non",
               "second ordre contre exact")

    ks = [70.0 + 0.3 * i for i in range(101)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Un mois, les deux lectures",
               readout="volatilité implicite")
    t = 30.0 / AN
    o2 = [(k, 100.0 * VO.sourire_second_ordre(k, t)) for k in ks]
    ex = [(k, 100.0 * VO.sourire_exact(k, t)) for k in ks]
    hi = max(y for _, y in ex) * 1.10
    p1.domain(ks[0], ks[-1], 24.0, hi)
    p1.frame()
    p1.grid_y(_ticks(24.0, hi, 3.0), lambda v: _num(v, 0) + " %", dx=34.0)
    p1.grid_x([70, 80, 90, 100], lambda v: _num(v, 0), label="strike")
    p1.path(ex, "hm7", tip="espérance exacte")
    p1.path(o2, "hm2", dash="6 3", tip="second ordre")
    k30, v30 = VO.retournement(t)
    p1.vline(k30, "lvl")
    p1.dot(k30, 100.0 * v30, "hm2", "le sommet du second ordre", r=4.5)
    p1.label(k30, hi - 0.6, _num(k30, 1), dx=-7, dy=0, anchor="end")
    p1.label(ks[0], ex[0][1], "l'exact monte encore", dx=8, dy=10)
    p1.label(ks[0], o2[0][1], "le second ordre redescend", dx=8, dy=12)

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce que l'approximation ajoute",
               readout="points de volatilité")
    series = [("hm4", "", 30.0), ("hm4", "6 3", 90.0), ("hm4", "2 3", 365.0)]
    courbes = []
    for cls, dash, j in series:
        tt = j / AN
        courbes.append((cls, dash, j,
                        [(k, 100.0 * (VO.sourire_naif(k, tt)
                                      - VO.sourire_exact(k, tt)))
                         for k in ks]))
    hi2 = max(y for _, _, _, c in courbes for _, y in c) * 1.25
    lo2 = min(y for _, _, _, c in courbes for _, y in c) * 1.60 - 0.2
    p2.domain(ks[0], ks[-1], lo2, hi2)
    p2.frame()
    p2.grid_y([0.0] + _ticks(5.0, hi2, 5.0), lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([70, 80, 90, 100], lambda v: _num(v, 0), label="strike")
    p2.hline(0.0, "lvl")
    for cls, dash, j, c in courbes:
        p2.path(c, cls, dash=dash, tip=_num(j, 0) + " jours")

    b.legend(0.0, 352.0,
             [("hm7", "l'exacte, à gauche"),
              ("hm2", "le second ordre", "6 3"),
              ("hm4", "un mois, à droite"),
              ("hm4", "trois mois", "6 3"),
              ("hm4", "un an", "2 3")],
             step=132.0, kind="line")
    b.annotation(0.0, 376.0,
                 "la correction de prix est bornée, le véga par lequel on la "
                 "reconvertit décroît plus vite : leur rapport se retourne")
    b.annotation(0.0, 392.0,
                 "le sommet tombe à "
                 + _num(100 * (1.0 - k30 / S), 0) + " % de la monnaie sur un "
                 "mois, dans la fenêtre que la planche du guide dessine")
    b.annotation(0.0, 408.0,
                 "l'espérance exacte, elle, continue de monter : un sourire "
                 "réel ne redescend pas dans les ailes")

    _source(b, "La planche du guide montre trois sourires qui atteignent un "
               "sommet et redescendent, et sa légende dit que cette forme "
               "correspond à ce qu'on observe sur les marchés. Un sourire "
               "réel ne redescend pas dans les ailes, et le modèle du guide "
               "non plus : le cadre de gauche superpose son développement du "
               "second ordre et l'espérance exacte du prix sous la même loi "
               "de volatilité. Le premier se retourne, la seconde monte. Le "
               "cadre de droite donne ce que la route la plus courte ajoute "
               "par-dessus, ténor par ténor, et le ténor le plus court est "
               "celui où elle ajoute le plus — l'inverse de ce que la "
               "légende revendique en parlant de sourires qui se raidissent "
               "aux échéances courtes.")
    return b.render("Le sourire du second ordre et l esperance exacte au meme "
                    "tenor, et ce que l inversion au premier ordre ajoute.")


def fig_vo_relief_sourire() -> str:
    """Le relief du sourire exact."""
    z = [list(l) for l in VO.surface_sourire()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Volga · le relief du sourire",
               "Ce que la convexité vaut en points de volatilité implicite",
               "hauteur : points")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(j, 0) for j in VO.SURF_ECHEANCE_SOURIRE],
             col_labels=[_num(m, 2) for m in VO.SURF_MONEYNESS_SOURIRE],
             z_ticks=[(t, _num(t, 0)) for t in _echine(zlo, zhi)],
             tip="{v:+.1f} points", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : l'échéance en jours · arête droite : le "
                 "spot sur le strike · hauteur : le sourire en points")
    b.annotation(0.0, 424.0,
                 "le sol est la monnaie, où la convexité ne vaut rien et où "
                 "le sourire est nul par construction")
    b.annotation(0.0, 440.0,
                 "il monte vers l'aile et vers l'échéance courte, où la même "
                 "incertitude pèse le plus lourd")

    _source(b, "La hauteur est l'espérance exacte du prix sous une "
               "volatilité incertaine, reconvertie en points de volatilité "
               "implicite. C'est le sourire que le mécanisme du guide "
               "produit, sans approximation d'aucune sorte. Il est nul à la "
               "monnaie — le volga y est nul, donc l'incertitude n'y vaut "
               "rien — et il monte vers l'aile. Ce que le relief ajoute à la "
               "planche du guide est le second axe : le sourire se raidit "
               "quand l'échéance raccourcit, et c'est bien la forme "
               "qualitative que les marchés montrent. Le mécanisme est donc "
               "juste ; c'est la route qui ne l'était pas.")
    return b.render("Relief du sourire exact en points de volatilite "
                    "implicite, en echeance et en moneyness.")


def fig_vo_relief_artefact() -> str:
    """Le relief de ce que la route la plus courte ajoute."""
    z = [list(l) for l in VO.surface_artefact()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Volga · le relief de l'artefact",
               "Ce que la route la plus courte ajoute au-dessus du vrai",
               "hauteur : points de volatilité")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(j, 0) for j in VO.SURF_ECHEANCE_ART],
             col_labels=[_num(m, 2) for m in VO.SURF_MONEYNESS_ART],
             z_ticks=[(t, _num(t, 0)) for t in _echine(zlo, zhi)],
             tip="{v:+.1f} points de trop", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : l'échéance en jours · arête droite : le "
                 "spot sur le strike · hauteur : l'excès de la route courte")
    b.annotation(0.0, 424.0,
                 "il vaut zéro à la monnaie, où le prix est linéaire en "
                 "volatilité et où diviser par le véga est exact")
    b.annotation(0.0, 440.0,
                 "il explose au coin du fond, où le prix est le moins "
                 "linéaire : l'erreur y dépasse la volatilité d'entrée")

    _source(b, "La hauteur est ce que l'inversion au premier ordre ajoute "
               "par-dessus l'espérance exacte, en points de volatilité "
               "implicite. Elle est nulle à la monnaie, et ce n'est pas un "
               "hasard : c'est exactement là que le prix est linéaire en "
               "volatilité, donc là que diviser une correction de prix par "
               "le véga est légitime. Elle explose dans l'aile courte, où le "
               "prix est le moins linéaire, et l'erreur y dépasse la "
               "volatilité qu'on a mise en entrée. Le raccourci est valide "
               "précisément là où il ne sert à rien, et faux partout où on "
               "l'emploie — c'est la forme la plus pure du défaut que ce "
               "document cherche, et il vient d'un guide qui a par ailleurs "
               "raison sur le fond.")
    return b.render("Relief de ce que l inversion au premier ordre ajoute a "
                    "l esperance exacte, en echeance et en moneyness.")


# ---------------------------------------------------------------------------
# III. Les chocs, le papillon, et le décompte
# ---------------------------------------------------------------------------


def fig_vo_chocs() -> str:
    """Vingt points contre deux fois dix, et le ténor que le guide choisit."""
    b = _plate(500, "Volga · les chocs",
               "Le fait est réel, et le ténor choisi est le plus faible",
               "call vendu à " + _num(100 * VO.ECART_VENDU, 0) + " % hors")

    chocs = [0.0 + 0.0018 * i for i in range(201)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Ce qu'un choc coûte au vendeur",
               readout="points d'indice")
    series = [("hm7", "", 14.0), ("hm5", "6 3", 60.0), ("hm3", "2 3", 180.0)]
    courbes = [(cls, dash, j,
                [(100 * c, -VO.perte_du_vendeur(j, c)) for c in chocs])
               for cls, dash, j in series]
    lo = min(y for _, _, _, cc in courbes for _, y in cc) * 1.20
    p1.domain(0.0, 100 * chocs[-1], lo, 0.4)
    p1.frame()
    p1.grid_y(_ticks(lo, 0.4, 2.0), lambda v: _signed(v, 0), dx=26.0)
    p1.grid_x([0, 10, 20, 30], lambda v: _num(v, 0),
              label="hausse de volatilité (points)")
    p1.hline(0.0, "lvl")
    for cls, dash, j, cc in courbes:
        p1.path(cc, cls, dash=dash, tip=_num(j, 0) + " jours")
    p1.vline(100 * VO.CHOC_PETIT, "lvl")
    p1.vline(100 * VO.CHOC_GRAND, "lvl")
    p1.label(0.0, lo * 0.86, "la courbure est le volga", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Le rapport des deux chocs",
               readout="vingt sur dix")
    js = [14.0 + 2.0 * i for i in range(116)]
    rap = [(j, VO.rapport_des_chocs(j)) for j in js]
    hi = max(y for _, y in rap) * 1.15
    p2.domain(js[0], js[-1], 1.8, hi)
    p2.frame()
    p2.grid_y([2.0] + _ticks(2.5, hi, 0.5), lambda v: _num(v, 1), dx=26.0)
    p2.grid_x([40, 120, 200], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.hline(2.0, "lvl")
    p2.path(rap, "hm4", tip="rapport")
    for j in VO.TENORS_CHOC:
        p2.dot(j, VO.rapport_des_chocs(j), "hm4", _num(j, 0) + " jours",
               r=4.0)
    p2.label(js[0], VO.rapport_des_chocs(js[0]),
             "deux semaines : " + _num(VO.rapport_des_chocs(14.0), 2), dx=9,
             dy=4)
    p2.label(180.0, VO.rapport_des_chocs(180.0),
             "six mois : " + _num(VO.rapport_des_chocs(180.0), 2), dx=-10,
             dy=-8, anchor="end")

    b.legend(0.0, 352.0,
             [("hm7", "deux semaines"), ("hm5", "deux mois", "6 3"),
              ("hm3", "six mois", "2 3"),
              ("hm4", "le rapport, à droite")],
             step=166.0, kind="line")
    b.annotation(0.0, 376.0,
                 "un modèle de risque linéaire en véga donnerait exactement "
                 "deux : tout ce qui dépasse est du volga")
    b.annotation(0.0, 392.0,
                 "le rapport vaut " + _num(VO.rapport_des_chocs(180.0), 2)
                 + " à six mois et " + _num(VO.rapport_des_chocs(14.0), 2)
                 + " à deux semaines")
    b.annotation(0.0, 408.0,
                 "le guide illustre son mécanisme au ténor où il est le "
                 "moins marqué, comme celui du charm choisissait son strike")

    _source(b, "Le cadre de gauche est la planche de gauche du guide : trois "
               "courbes de perte contre la hausse de volatilité, et leur "
               "courbure est le volga. Les deux verticales sont les deux "
               "chocs qu'il compare. Le cadre de droite donne directement le "
               "rapport de leurs pertes, ténor par ténor, avec la ligne à "
               "deux qu'un modèle linéaire en véga rendrait. Le fait que le "
               "guide énonce est vrai partout ; ce qu'il ne dit pas est que "
               "sa propre planche montre le ténor où il est le plus faible. "
               "À deux semaines, la perte à vingt points vaut plus de quatre "
               "fois celle à dix.")
    return b.render("La perte d un vendeur d aile contre la hausse de "
                    "volatilite a trois tenors, et le rapport des deux "
                    "chocs contre l echeance.")


def fig_vo_papillon() -> str:
    """Le papillon n'est pas neutre en véga, et le corriger l'améliore."""
    b = _plate(500, "Volga · le papillon",
               "Le trade de volga pur est une vente de véga d'un cinquième",
               "trois mois")

    ds = [0.03 + 0.0021 * i for i in range(201)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Le véga net d'un papillon",
               readout="% du véga du corps")
    series = [("hm7", "", 30.0), ("hm5", "6 3", 90.0), ("hm3", "2 3", 180.0)]
    courbes = [(cls, dash, j,
                [(d, 100.0 * VO.papillon(d, j).part_de_vega) for d in ds])
               for cls, dash, j in series]
    lo = min(y for _, _, _, c in courbes for _, y in c) * 1.15
    p1.domain(ds[0], ds[-1], lo, 6.0)
    p1.frame()
    p1.grid_y(_ticks(lo, 6.0, 20.0), lambda v: _signed(v, 0), dx=30.0)
    p1.grid_x([0.1, 0.2, 0.3, 0.4], lambda v: _num(v, 1),
              label="delta des ailes")
    p1.hline(0.0, "lvl")
    for cls, dash, j, c in courbes:
        p1.path(c, cls, dash=dash, tip=_num(j, 0) + " jours")
    p1.label(ds[0], lo * 0.80, "zéro serait le trade de volga pur", dx=8,
             dy=0)
    p1.label(ds[0], lo * 0.62, "les trois échéances se superposent", dx=8,
             dy=0)
    p1.dot(0.25, 100.0 * VO.papillon(0.25, 90.0).part_de_vega, "hm5",
           "vingt-cinq deltas", r=4.5)
    p1.label(0.25, 100.0 * VO.papillon(0.25, 90.0).part_de_vega,
             "vingt-cinq deltas : "
             + _signed(100 * VO.papillon(0.25, 90.0).part_de_vega, 0)
             + " %", dx=-10, dy=-8, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce que la correction rapporte",
               readout="volga net")
    t = 90.0
    simple = [(d, VO.papillon(d, t).volga_net) for d in ds]
    neutre = [(d, VO.papillon(d, t).volga_neutre) for d in ds]
    hi = max(y for _, y in neutre) * 1.15
    p2.domain(ds[0], ds[-1], 0.0, hi)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi, 100.0), lambda v: _num(v, 0), dx=30.0)
    p2.grid_x([0.1, 0.2, 0.3, 0.4], lambda v: _num(v, 1),
              label="delta des ailes")
    p2.path(neutre, "hm6", tip="pondéré en véga")
    p2.path(simple, "hm2", dash="5 4", tip="un-deux-un")
    p2.label(ds[0], neutre[0][1], "pondéré en véga", dx=8, dy=10)
    p2.label(ds[0], simple[0][1], "un-deux-un", dx=8, dy=14)

    b.legend(0.0, 352.0,
             [("hm7", "trente jours"), ("hm5", "trois mois", "6 3"),
              ("hm3", "six mois", "2 3"),
              ("hm6", "pondéré, à droite")],
             step=166.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le véga est maximal à la monnaie, donc deux ailes ne "
                 "valent jamais deux corps : le papillon vend du véga")
    b.annotation(0.0, 392.0,
                 "il en vend "
                 + _num(100 * abs(VO.papillon(0.25, 90.0).part_de_vega), 0)
                 + " % à vingt-cinq deltas et "
                 + _num(100 * abs(VO.papillon(0.10, 90.0).part_de_vega), 0)
                 + " % à dix")
    b.annotation(0.0, 408.0,
                 "pondérer les ailes par le rapport des végas annule le "
                 "véga net et augmente le volga")

    _source(b, "Le guide appelle le papillon le trade de volga pur, et la "
               "seconde moitié de sa phrase tient : le volga net est grand "
               "et positif. La première non. Le véga vaut le comptant fois "
               "la densité normale prise en son argument, il est maximal à "
               "la monnaie, et deux ailes ne valent donc jamais deux corps. "
               "Le cadre de gauche donne le défaut, qui grandit à mesure que "
               "les ailes s'éloignent — précisément quand on croit acheter "
               "le plus de convexité. Le cadre de droite montre que la "
               "correction ne coûte rien : en achetant les ailes dans le "
               "rapport des végas, le véga net devient exactement nul et le "
               "volga net monte. Le papillon pondéré est à la fois plus "
               "propre et plus exposé à ce qu'il prétend acheter.")
    return b.render("Le vega net d un papillon contre le delta de ses ailes, "
                    "et le volga net avant et apres ponderation.")


def fig_vo_relief_papillon() -> str:
    """Le relief du défaut de véga."""
    z = [list(l) for l in VO.surface_papillon()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Volga · le relief du papillon",
               "Plus les ailes sont lointaines, moins le trade est pur",
               "hauteur : % du véga du corps")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(100 * d, 0) for d in VO.SURF_DELTA],
             col_labels=[_num(j, 0) for j in VO.SURF_ECHEANCE_PAP],
             z_ticks=[(t, _num(t, 0)) for t in _echine(zlo, zhi)],
             tip="{v:.0f} % de vega vendu", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : le delta des ailes · arête droite : "
                 "l'échéance en jours · hauteur : le véga vendu sans le "
                 "vouloir")
    b.annotation(0.0, 424.0,
                 "le sol est le papillon serré, presque neutre, et dont le "
                 "volga est presque nul lui aussi")
    b.annotation(0.0, 440.0,
                 "le sommet est le papillon large, celui qu'on achète en "
                 "croyant acheter de la convexité pure")

    _source(b, "La hauteur est la part du véga du corps qu'un papillon "
               "un-deux-un vend sans que personne l'ait voulu, en fonction "
               "du delta de ses ailes et de son échéance. Elle ne dépend "
               "presque pas de l'échéance — la surface est plate le long de "
               "cette arête — et elle dépend fortement du delta. Le défaut "
               "est donc gouverné par la seule chose qu'un pupitre croit "
               "choisir librement. Le coin du fond est le papillon large, "
               "celui qu'on achète précisément pour sa convexité, et c'est "
               "là que trois quarts du véga du corps partent sans qu'on les "
               "compte. La correction est immédiate et elle augmente le "
               "volga : il n'y a aucune raison de ne pas la faire.")
    return b.render("Relief du vega net d un papillon un-deux-un, en delta "
                    "des ailes et en echeance.")


def fig_vo_reste() -> str:
    """Le décompte des huit affirmations, et le cumul des huit parties."""
    aff = VO.affirmations()
    compte = VO.compte_par_grandeur()
    ordre = sorted(compte, key=lambda g: (-compte[g], g))
    fam = VO.familles()
    total = sum(n for _, n in fam)

    b = _plate(490, "Volga · le décompte",
               "Cinquante-neuf affirmations, et aucune ne donne un sens",
               _num(len(aff), 0) + " ici")

    p1 = Panel(b, PX1, 92, PW, 214, title="Ce qu'elles déplacent",
               readout="affirmations")
    lignes = list(ordre) + [g for g in ("l'horloge", "la direction")
                            if g not in ordre]
    p1.domain(0.0, 8.0, -0.6, len(lignes) - 0.4)
    p1.frame()
    p1.grid_x(_ticks(0.0, 8.0, 2.0), lambda v: _num(v, 0))
    for i, g in enumerate(lignes):
        y = len(lignes) - 1 - i
        n = compte.get(g, 0)
        cls = {"la direction": "hm7", "rien": "hm1"}.get(g, "hm5")
        if n:
            p1.hbar(y, 0.0, n, 13.0, cls, tip=g + " : " + _num(n, 0))
        p1.label(0.0, y + 0.34, g, dx=4, dy=0)
        p1.label(max(n, 0.0), y, _num(n, 0), dx=7, dy=4)

    p2 = Panel(b, PX2, 92, PW, 214, title="Les huit parties",
               readout="affirmations")
    haut = max(n for _, n in fam) * 1.35
    p2.domain(0.0, haut, -0.6, len(fam) - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, haut, 3.0), lambda v: _num(v, 0))
    for i, (nom, n) in enumerate(fam):
        y = len(fam) - 1 - i
        p2.hbar(y, 0.0, n, 8.0, "hm3", tip=nom)
        p2.label(0.0, y + 0.26, nom, dx=4, dy=0)
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
                 + _num(compte.get("rien", 0), 0) + " ne déplacent rien, "
                 "aucune l'horloge")
    b.annotation(0.0, 392.0,
                 "la barre de la direction est vide pour la quatrième partie "
                 "d'options consécutive")
    b.annotation(0.0, 408.0,
                 "sur les " + _num(total, 0) + " affirmations des huit "
                 "parties, aucune ne donne un sens")

    _source(b, "Huit documents, cinquante-neuf affirmations, et la colonne "
               "de la direction reste vide. Celui-ci est pourtant le plus "
               "ambitieux des huit : il ne décrit pas une grandeur, il "
               "dérive une observation de marché — le sourire — d'une "
               "inégalité de Jensen appliquée à une fonction convexe, sans "
               "peau supposée et sans flux modélisé. Aucun des sept autres "
               "n'a tenté cela, et le mécanisme tient : la mesure lui donne "
               "neuf points de volatilité implicite à trente pour cent de la "
               "monnaie sur un mois. Ce que ce dépôt corrige n'est pas le "
               "raisonnement mais la route, et c'est une leçon de méthode "
               "plutôt qu'une leçon de marché : un développement du second "
               "ordre a un domaine, et l'inverser au premier ordre en a un "
               "autre, plus petit encore.")
    return b.render("Le decompte des affirmations par ce qu elles deplacent, "
                    "et le cumul des huit parties d options.")


def fig_vo_jensen() -> str:
    """L inegalite de Jensen, dessinee sur l objet qu elle concerne."""
    b = _plate(500, "Volga · l'inégalité de Jensen",
               "Le mécanisme tient dans une corde au-dessus d'une courbe",
               "un mois, quinze pour cent hors")

    t = 30.0 / AN
    k = S * 1.15
    sd = VO.ecart_type_vol()
    vols = [max(0.01, V - 3.2 * sd) + (6.4 * sd) * i / 200 for i in range(201)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Le prix contre la volatilité",
               readout="points d'indice")
    courbe = [(v, th.call(S, k, v, t, VO.TAUX, VO.DIVIDENDE)) for v in vols]
    hi = max(y for _, y in courbe) * 1.20
    p1.domain(vols[0], vols[-1], 0.0, hi)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi, 0.5), lambda v: _num(v, 1), dx=26.0)
    p1.grid_x([0.15, 0.25, 0.35, 0.45], lambda v: _pct(v, 0),
              label="volatilité")
    a, bb = V - 2.0 * sd, V + 2.0 * sd
    pa = th.call(S, k, a, t, VO.TAUX, VO.DIVIDENDE)
    pb = th.call(S, k, bb, t, VO.TAUX, VO.DIVIDENDE)
    p1.path([(a, pa), (bb, pb)], "hm1", dash="2 3", tip="la corde")
    p1.path(courbe, "hm7", tip="le prix")
    p1.vline(V, "lvl")
    p1.dot(V, th.call(S, k, V, t, VO.TAUX, VO.DIVIDENDE), "hm7",
           "le prix a la volatilite moyenne", r=4.5)
    p1.dot(V, 0.5 * (pa + pb), "hm1", "le milieu de la corde", r=4.5)
    p1.label(V, 0.5 * (pa + pb), "la corde est au-dessus", dx=10, dy=-6)
    p1.label(vols[0], hi * 0.88, "trait plein : le prix", dx=8, dy=0)
    p1.label(vols[0], hi * 0.78, "pointillé : la corde", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce que la convexité ajoute",
               readout="points d'indice")
    nus = [0.0 + 0.004 * i for i in range(151)]
    exact = [(n, VO.prix_exact(k, t, n) - th.call(S, k, V, t, VO.TAUX,
                                                  VO.DIVIDENDE))
             for n in nus]
    ordre2 = [(n, 0.5 * VO.volga(S, k, V, t)
               * (VO.ecart_type_vol(n) ** 2)) for n in nus]
    hi2 = max(y for c in (exact, ordre2) for _, y in c) * 1.12
    p2.domain(0.0, nus[-1], 0.0, hi2)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2, 0.1), lambda v: _num(v, 1), dx=26.0)
    p2.grid_x([0.0, 0.2, 0.4, 0.6], lambda v: _pct(v, 0),
              label="volatilité de la volatilité")
    p2.path(exact, "hm6", tip="l esperance exacte")
    p2.path(ordre2, "hm2", dash="5 4", tip="le terme de volga")
    p2.vline(VO.NU, "lvl")
    p2.label(VO.NU, hi2 * 0.90, _pct(VO.NU, 0), dx=7, dy=0)
    p2.label(0.0, hi2 * 0.72, "trait clair : l'espérance exacte", dx=8, dy=0)
    p2.label(0.0, hi2 * 0.60, "tirets : le terme de volga seul", dx=8,
             dy=0)

    b.legend(0.0, 352.0,
             [("hm7", "le prix, à gauche"), ("hm1", "la corde", "2 3"),
              ("hm6", "l'exacte, à droite"),
              ("hm2", "le terme de volga", "5 4")],
             step=166.0, kind="line")
    b.annotation(0.0, 376.0,
                 "une fonction convexe est au-dessous de ses cordes, donc "
                 "son espérance est au-dessus de sa valeur en la moyenne")
    b.annotation(0.0, 392.0,
                 "c'est tout le mécanisme du guide, et il n'a besoin de rien "
                 "d'autre : ni peau supposée, ni flux modélisé")
    b.annotation(0.0, 408.0,
                 "le terme de volga en est le premier morceau, et il suffit "
                 "tant que la volatilité de la volatilité reste petite")

    _source(b, "Le cadre de gauche est l'inégalité de Jensen dessinée sur "
               "l'objet qu'elle concerne. Le prix d'une aile est convexe en "
               "volatilité, donc la corde qui joint deux volatilités "
               "possibles passe au-dessus de la courbe, et le milieu de la "
               "corde — l'espérance du prix si les deux sont également "
               "probables — dépasse le prix pris à la volatilité moyenne. "
               "L'écart entre les deux points est exactement ce que le guide "
               "appelle la prime de convexité, et c'est ce qui devient le "
               "sourire une fois reconverti en volatilité implicite. Le "
               "cadre de droite montre jusqu'où le terme de volga suffit à "
               "le décrire : il colle à l'espérance exacte tant que "
               "l'incertitude reste modeste, et s'en écarte ensuite. La "
               "verticale est la valeur que le guide déclare.")
    return b.render("L inegalite de Jensen sur le prix d une aile, et "
                    "l esperance exacte contre le terme de volga.")


def fig_vo_routes() -> str:
    """Le domaine de validite de chaque route."""
    b = _plate(490, "Volga · les domaines",
               "Chaque raccourci a un domaine, et le plus court le plus petit",
               "un mois")

    t = 30.0 / AN
    ks = [72.0 + 0.28 * i for i in range(101)]
    p1 = Panel(b, PX1, 92, PW, 214, title="L'écart à l'exact",
               readout="points de volatilité")
    naif = [(k, 100.0 * (VO.sourire_naif(k, t) - VO.sourire_exact(k, t)))
            for k in ks]
    o2 = [(k, 100.0 * (VO.sourire_second_ordre(k, t)
                       - VO.sourire_exact(k, t))) for k in ks]
    hi = max(y for _, y in naif) * 1.20
    lo = min(y for _, y in o2) * 1.35
    p1.domain(ks[0], ks[-1], lo, hi)
    p1.frame()
    p1.grid_y(_ticks(lo, hi, 5.0), lambda v: _signed(v, 0), dx=30.0)
    p1.grid_x([75, 85, 95], lambda v: _num(v, 0), label="strike")
    p1.hline(0.0, "lvl")
    p1.path(naif, "hm7", tip="premier ordre")
    p1.path(o2, "hm2", dash="5 4", tip="second ordre")
    p1.label(ks[0], naif[0][1], "premier ordre", dx=8, dy=10)
    p1.label(ks[0], o2[0][1], "second ordre", dx=8, dy=-8)
    p1.label(ks[-1], 0.0, "l'exact", dx=-8, dy=-8, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce que la correction pèse",
               readout="% du prix")
    part = [(k, 100.0 * VO.poids_de_la_correction(k, t)) for k in ks]
    kpic, ypic = VO.pic_du_poids(t)
    hi2 = max(y for _, y in part) * 1.30
    p2.domain(ks[0], ks[-1], 0.0, hi2)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2, 0.25), lambda v: _num(v, 2), dx=32.0)
    p2.grid_x([75, 85, 95], lambda v: _num(v, 0), label="strike")
    p2.path(part, "hm4", tip="poids de la correction")
    p2.dot(kpic, 100.0 * ypic, "hm4", "le maximum du poids", r=4.5)
    p2.label(kpic, 100.0 * ypic,
             _num(100 * ypic, 2) + " % du prix", dx=-8, dy=-8, anchor="end")
    p2.label(ks[0], 0.0, "et rien dans l'aile", dx=8, dy=-10)

    b.legend(0.0, 342.0,
             [("hm7", "premier ordre, à gauche"),
              ("hm2", "second ordre, à gauche", "5 4"),
              ("hm4", "le poids de la correction, à droite")],
             step=200.0, kind="line")
    b.annotation(0.0, 366.0,
                 "un développement du second ordre est réputé valide tant "
                 "que sa correction reste petite devant ce qu'elle corrige")
    b.annotation(0.0, 382.0,
                 "la mesure le retourne : elle pèse au plus "
                 + _num(100 * ypic, 2) + " % du prix, et ce maximum tombe là "
                 "où les routes sont exactes")
    b.annotation(0.0, 398.0,
                 "dans l'aile elle ne pèse rien, et le second ordre s'y "
                 "trompe de "
                 + _num(abs(100 * (VO.sourire_second_ordre(ks[0], t)
                                   - VO.sourire_exact(ks[0], t))), 1)
                 + " points : le véga s'annule plus vite qu'elle")

    _source(b, "Deux raccourcis se superposent dans la route la plus courte, "
               "et le critère qui devrait les borner pointe ici à l'envers. "
               "Ce critère dit qu'un développement du second ordre vaut tant "
               "que sa correction reste petite devant le prix qu'elle "
               "corrige ; le cadre de droite mesure ce rapport, et il ne "
               "dépasse jamais un pour cent, son maximum tombant au strike "
               "où les deux routes sont exactes à deux centièmes de point "
               "près. Dans l'aile, où elles se trompent de quatre et de "
               "seize points, la correction ne pèse plus rien du tout, "
               "quelques millionièmes du prix. La raison tient en une "
               "ligne : l'inversion divise par le véga, et le véga s'annule "
               "plus vite que la correction. Une erreur de prix invisible y "
               "devient une erreur de volatilité implicite énorme. Le cadre "
               "de gauche donne les deux erreurs, de signes opposés dans "
               "l'aile et d'ordres différents ; l'exact est la ligne à "
               "zéro.")
    return b.render("L ecart de chaque route a l esperance exacte, et le "
                    "poids de la correction dans le prix.")


def fig_vo_carte() -> str:
    """Les objets que les huit parties d options partagent."""
    b = _plate(470, "Volga · la carte",
               "Trois objets que huit parties partagent",
               "des routes sans rien de commun")

    t30 = 30.0 / AN
    objets = [
        ("la bande `d₁d₂ < 0`", ("XXII", "XXIV", "XXVI"),
         100.0 * VO.largeur_de_bande(t30), "% du comptant à trente jours"),
        ("la racine `d₁² − σ√T·d₁ = 1`", ("XX", "XXIV", "XXV"),
         abs(G.d1_du_pic(V, t30)), "argument du pic"),
        ("le taux `q + σ²/2`", ("XXIII", "XXIV", ""),
         100.0 * VO.va.R.taux_du_pic_exact(), "pour cent"),
    ]

    p1 = Panel(b, PX1, 92, PW, 214, title="Combien de parties le partagent",
               readout="parties")
    p1.domain(0.0, 4.0, -0.6, len(objets) - 0.4)
    p1.frame()
    p1.grid_x([0, 1, 2, 3, 4], lambda v: _num(v, 0))
    for i, (nom, parts, _v, _u) in enumerate(objets):
        y = len(objets) - 1 - i
        n = len([x for x in parts if x])
        p1.hbar(y, 0.0, n, 14.0, "hm5", tip=nom)
        p1.label(0.0, y + 0.34, nom.replace("`", ""), dx=4, dy=0)
        p1.label(0.0, y - 0.30, " · ".join(x for x in parts if x), dx=4,
                 dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="La valeur qu'elles trouvent",
               readout="chacune la sienne")
    haut = max(v for _, _, v, _ in objets) * 1.45
    p2.domain(0.0, haut, -0.6, len(objets) - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, haut, 1.0), lambda v: _num(v, 0))
    for i, (nom, _p, v, u) in enumerate(objets):
        y = len(objets) - 1 - i
        p2.hbar(y, 0.0, v, 14.0, "hm3", tip=nom)
        p2.label(0.0, y + 0.34, u, dx=4, dy=0)
        p2.label(v, y, _num(v, 2), dx=7, dy=4)

    b.legend(0.0, 352.0,
             [("hm5", "les parties qui le trouvent"),
              ("hm3", "la valeur mesurée, à droite")],
             step=240.0)
    b.annotation(0.0, 376.0,
                 "trois objets sont apparus plusieurs fois dans la série, "
                 "par des routes qui n'avaient rien en commun")
    b.annotation(0.0, 392.0,
                 "la bande où le produit des deux arguments est négatif "
                 "porte trois noms dans trois parties différentes")
    b.annotation(0.0, 408.0,
                 "la racine du pic est celle du charm, du vanna et du volga ; "
                 "le taux est celui du rho et du zéro de vanna")

    _source(b, "Huit guides écrits séparément, et trois objets qui reviennent "
               "sous des noms différents. La bande où le produit des deux "
               "arguments est négatif a été mesurée par la partie XXII comme "
               "la zone de courbure négative du véga, par la partie XXIV "
               "comme celle où le vanna cesse d'obéir à sa règle, et ici "
               "comme le creux du volga : c'est le même intervalle, large de "
               "sigma carré T. La racine d'une même équation du second degré "
               "donne le pic du charm, celui du vanna et la forme du volga. "
               "Et le taux où le rendement plus la demi-variance égale le "
               "taux sans risque décide à la fois du maximum du rho et du "
               "côté où le vanna s'annule. Ce ne sont pas des coïncidences "
               "de calcul : ce sont trois structures, et chaque guide en "
               "décrit une face sans savoir qu'il partage l'objet.")
    return b.render("Les trois objets que plusieurs parties d options "
                    "partagent, et la valeur que chacune mesure.")


def fig_vo_ratio() -> str:
    """Le rapport volga sur vega, la grandeur qui se convertit en points."""
    b = _plate(490, "Volga · le rapport",
               "La courbure par unité de pente, et ce qu'elle vaut en points",
               "volga sur véga")

    ms = [0.62 + 0.0038 * i for i in range(201)]
    p1 = Panel(b, PX1, 92, PW, 214, title="Le rapport contre le comptant",
               readout="par unité de volatilité")
    series = [("hm7", "", 30.0), ("hm5", "6 3", 90.0), ("hm3", "2 3", 365.0)]
    courbes = []
    for cls, dash, j in series:
        tt = j / AN
        c = [(m, VO.volga(S * m, S, V, tt)
              / max(vg.vega(S * m, S, V, tt, VO.TAUX, VO.DIVIDENDE), 1e-12))
             for m in ms]
        courbes.append((cls, dash, j, c))
    hi = max(y for _, _, _, c in courbes for _, y in c) * 1.20
    p1.domain(ms[0], ms[-1], -2.0, hi)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi, 50.0), lambda v: _num(v, 0), dx=26.0)
    p1.grid_x([0.7, 0.9, 1.1, 1.3], lambda v: _num(v, 1),
              label="spot sur strike")
    p1.hline(0.0, "lvl")
    p1.vline(1.0, "lvl")
    for cls, dash, j, c in courbes:
        p1.path(c, cls, dash=dash, tip=_num(j, 0) + " jours")
    p1.label(1.0, hi * 0.90, "nul à la monnaie", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Le sourire que cela donne",
               readout="points de volatilité")
    lift = []
    for cls, dash, j in series:
        tt = j / AN
        lift.append((cls, dash, j,
                     [(m, 100.0 * (VO.sourire_exact(S * m, tt) - V))
                      for m in ms if 0.70 <= m <= 1.30]))
    hi2 = max(y for _, _, _, c in lift for _, y in c) * 1.20
    p2.domain(0.70, 1.30, 0.0, hi2)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2, 3.0), lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([0.8, 1.0, 1.2], lambda v: _num(v, 1),
              label="spot sur strike")
    for cls, dash, j, c in lift:
        p2.path(c, cls, dash=dash, tip=_num(j, 0) + " jours")
    p2.label(0.70, lift[0][3][0][1], "un mois", dx=8, dy=10)
    p2.label(0.70, lift[2][3][0][1], "un an", dx=8, dy=14)

    b.legend(0.0, 342.0,
             [("hm7", "trente jours"), ("hm5", "trois mois", "6 3"),
              ("hm3", "un an", "2 3")],
             step=200.0, kind="line")
    b.annotation(0.0, 366.0,
                 "le rapport du volga au véga vaut le produit des deux "
                 "arguments divisé par la volatilité")
    b.annotation(0.0, 382.0,
                 "c'est lui qui se convertit en points de volatilité "
                 "implicite, et il est nul à la monnaie")
    b.annotation(0.0, 398.0,
                 "le cadre de droite donne le sourire exact que cela "
                 "produit, et il a la forme qu'un marché montre")

    _source(b, "Le rapport du volga au véga est la grandeur utile : la "
               "courbure par unité de pente, donc ce qui se convertit "
               "directement en points de volatilité implicite. Il vaut le "
               "produit des deux arguments divisé par la volatilité, il est "
               "nul à la monnaie, et il croît sans borne dans les ailes — "
               "c'est ce dernier fait qui rend l'inversion au premier ordre "
               "si trompeuse. Le cadre de droite montre ce que la conversion "
               "honnête en fait : un sourire qui monte de part et d'autre, "
               "plus raide au ténor court, sans se retourner. La forme est "
               "celle qu'un marché montre, et elle sort d'un raisonnement "
               "qui ne suppose ni peau ni flux.")
    return b.render("Le rapport du volga au vega contre le comptant, et le "
                    "sourire exact qui en resulte.")


def render_all() -> dict[str, str]:
    """Les quinze planches, dans l'ordre du document."""
    return {
        "voprofil": fig_vo_profil(),
        "voratio": fig_vo_ratio(),
        "vorelief": fig_vo_relief_volga(),
        "vocourbure": fig_vo_courbure(),
        "vojensen": fig_vo_jensen(),
        "vosourire": fig_vo_sourire(),
        "voreliefs": fig_vo_relief_sourire(),
        "voretournement": fig_vo_retournement(),
        "voroutes": fig_vo_routes(),
        "voreliefa": fig_vo_relief_artefact(),
        "vochocs": fig_vo_chocs(),
        "vopapillon": fig_vo_papillon(),
        "voreliefp": fig_vo_relief_papillon(),
        "vocarte": fig_vo_carte(),
        "voreste": fig_vo_reste(),
    }
