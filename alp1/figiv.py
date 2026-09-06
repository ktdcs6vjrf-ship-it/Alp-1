"""Les planches de « la volatilité implicite ».

Seize planches, douze à plat et quatre en relief. La cinquième porte le
résultat structurant de la partie — un an de séances vaut deux observations —
et la septième porte la loi nulle du test que le guide publie lui-même.

Comme les modules d'options qui précèdent, celui-ci importe ses fonctions
d'échine, de graduation et de pourcentage de `fignv`.
"""

from __future__ import annotations

import math

from . import implicite as I
from .figdisc import W, _plate, _source, _surface
from .fignv import _dec, _echine, _pct, _ticks
from .figterm import Board, Panel, _num, _signed

PW = (W - 74.0) / 2.0 - 30.0
PX1 = 74.0
PX2 = 74.0 + (W - 74.0) / 2.0

S = I.S_REF
V = I.VOL_REF
AN = I.JOURS_AN


def _t(jours: float) -> float:
    return jours / AN


# ---------------------------------------------------------------------------
# I. L'inversion, et ce qui la borne
# ---------------------------------------------------------------------------


def fig_iv_inversion() -> str:
    """Le prix contre la volatilité, et la fonction qu'on inverse vraiment."""
    b = _plate(500, "Implicite · l'inversion",
               "Monotone, donc inversible — et presque affine à la monnaie",
               "trente jours, à la monnaie")

    t = _t(30.0)
    vols = [0.01 + 0.0079 * i for i in range(101)]

    p1 = Panel(b, PX1, 92, PW, 214, title="Le prix contre la volatilité",
               readout="points d'indice")
    series = [("hm7", "", 1.00), ("hm5", "6 3", 1.15), ("hm3", "2 3", 0.90)]
    courbes = [(cls, dash, m, [(v, I.call(S, S / m, v, t)) for v in vols])
               for cls, dash, m in series]
    hi = max(y for _, _, _, c in courbes for _, y in c)
    p1.domain(vols[0], vols[-1], 0.0, hi * 1.10)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi * 1.10, 4.0), lambda v: _num(v, 0), dx=22.0)
    p1.grid_x([0.1, 0.3, 0.5, 0.7], lambda v: _num(v, 1),
              label="volatilité")
    plancher = I.bornes_d_arbitrage(S, S / 1.15, t)[0]
    p1.hline(plancher, "lvl")
    for cls, dash, m, c in courbes:
        p1.path(c, cls, dash=dash, tip="S/K = " + _num(m, 2))
    p1.label(vols[-1], plancher, "le plancher du strike dans la monnaie",
             dx=-8, dy=-9, anchor="end")

    # La fonction que l'on inverse réellement : la volatilité contre le
    # prix, rapportée à sa propre course pour que deux strikes se
    # superposent. Le premier jet de ce cadre annonçait une pente qui
    # diverge, et la mesure a rendu **une droite** : à la monnaie le véga
    # ne dépend presque pas de la volatilité, donc la réciproque est
    # affine à un pour cent près. La légende dit maintenant ce que le
    # cadre montre.
    p2 = Panel(b, PX2, 92, PW, 214,
               title="La fonction qu'on inverse vraiment",
               readout="volatilité")
    p2.domain(0.0, 1.0, 0.0, 0.95)
    p2.frame()
    p2.grid_y([0.0, 0.2, 0.4, 0.6, 0.8], lambda v: _num(v, 1), dx=24.0)
    p2.grid_x([0.0, 0.25, 0.5, 0.75, 1.0], lambda v: _num(v, 2),
              label="part de la course du prix")
    for cls, dash, m in (("hm4", "", 1.00), ("hm2", "5 4", 1.25)):
        k = S / m
        bas, _ = I.bornes_d_arbitrage(S, k, t)
        haut = I.call(S, k, 0.90, t)
        pts = []
        for i in range(1, 161):
            prix = bas + (haut - bas) * i / 160.0
            v = I.implicite(prix, S, k, t)
            if v == v:
                pts.append(((prix - bas) / (haut - bas), v))
        p2.path(pts, cls, dash=dash, tip="S/K = " + _num(m, 2))
    p2.path([(0.0, 0.0), (1.0, 0.90)], "hm0", dash="1 3", tip="la corde")
    p2.label(0.0, 0.88,
             "à la monnaie : " + _pct(I.ecart_a_la_droite(S, t), 1)
             + " de la corde", dx=10, dy=0)
    p2.label(1.0, 0.30,
             "à 1,25 : " + _pct(I.ecart_a_la_droite(S / 1.25, t), 0),
             dx=-10, dy=0, anchor="end")

    b.legend(0.0, 352.0,
             [("hm7", "à la monnaie"), ("hm5", "S/K = 1,15", "6 3"),
              ("hm3", "S/K = 0,90", "2 3"),
              ("hm4", "l'inverse"), ("hm2", "l'inverse à 1,25", "5 4")],
             step=112.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le prix croît strictement avec la volatilité : c'est le "
                 "véga positif, et c'est ce qui rend la solution unique")
    b.annotation(0.0, 392.0,
                 "hors de la fenêtre d'arbitrage aucune volatilité ne rend "
                 "le prix, et un outil qui en rend une rend du bruit")
    b.annotation(0.0, 408.0,
                 "à la monnaie la réciproque est une droite à un pour cent "
                 "près ; dans l'aile elle s'en écarte quarante fois plus")

    _source(b, "Le guide écrit que la fonction est monotone en volatilité et "
               "que la solution est donc unique quand elle existe. Le cadre "
               "de gauche montre la monotonie et le plancher d'arbitrage du "
               "strike dans la monnaie, seul des trois à être franchement "
               "positif. Le cadre de droite retourne la fonction et donne "
               "celle qu'un moteur d'inversion calcule réellement. Le "
               "premier jet de ce cadre annonçait une pente qui diverge, et "
               "la mesure a rendu une droite : à la monnaie le véga ne "
               "dépend presque pas de la volatilité, donc la réciproque est "
               "affine à un pour cent de sa corde sur toute la plage "
               "négociée. C'est ce qui autorise un opérateur à raisonner en "
               "volatilité comme il raisonnerait en prix — et c'est faux "
               "dans l'aile, où l'écart est quarante-cinq fois plus grand. "
               "La section suivante mesure le même fait en unités de pas de "
               "cotation.")
    return b.render("Le prix d une option contre la volatilite, et la "
                    "fonction inverse que le moteur calcule.")


def fig_iv_routes() -> str:
    """Les deux routes d'inversion, et là où l'une échoue."""
    b = _plate(490, "Implicite · les deux routes",
               "Newton s'appuie sur le véga, la bissection sur rien",
               "forme fermée contre mesure")

    t = _t(30.0)
    ms = [0.80 + 0.008 * i for i in range(76)]

    p1 = Panel(b, PX1, 92, PW, 214, title="Le véga, qui décide de tout",
               readout="par point de volatilité")
    c = [(m, I.vega(S, S / m, V, t) / 100.0) for m in ms]
    hi = max(y for _, y in c)
    p1.domain(ms[0], ms[-1], 0.0, hi * 1.15)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi * 1.15, 0.03), lambda v: _num(v, 2), dx=28.0)
    p1.grid_x([0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4], lambda v: _num(v, 1),
              label="spot sur strike")
    p1.path(c, "hm7", tip="véga par point")
    p1.label(ms[-1], hi * 0.92, "il s'annule dans l'aile", dx=-8, dy=0,
             anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Ce que les deux routes rendent",
               readout="écart en volatilité")
    ecarts = []
    for m in ms:
        k = S / m
        p = I.call(S, k, V, t)
        a = I.implicite(p, S, k, t)
        n = I.implicite_newton(p, S, k, t)
        ecarts.append((m, abs(a - n) if n == n else 0.0))
    p2.domain(ms[0], ms[-1], 0.0, 2.4e-9)
    p2.frame()
    p2.grid_y([0.0, 6e-10, 1.2e-9, 1.8e-9, 2.4e-9],
              lambda v: _num(v * 1e9, 1), dx=24.0)
    p2.grid_x([0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4], lambda v: _num(v, 1),
              label="spot sur strike")
    p2.path(ecarts, "hm5", tip="écart des deux routes")
    p2.label(ms[0], 2.1e-9, "en milliardièmes de volatilité", dx=8, dy=0)

    b.legend(0.0, 352.0,
             [("hm7", "le véga par point"),
              ("hm5", "l'écart des deux routes, à droite")],
             step=240.0, kind="line")
    b.annotation(0.0, 376.0,
                 "les deux routes se referment à neuf décimales sur toute "
                 "la plage, et c'est ce qui autorise à publier la table")
    b.annotation(0.0, 392.0,
                 "Newton divise par le véga du cadre de gauche : là où il "
                 "s'annule, la route échoue et la bissection tient")
    b.annotation(0.0, 408.0,
                 "aucun des dix guides ne publie ce contrôle, et la partie "
                 "XXIV a montré ce qu'il coûte de ne pas le faire")

    _source(b, "Deux routes indépendantes vers le même nombre : une "
               "bissection, qui ne demande que la monotonie, et un Newton, "
               "qui demande le véga. Leur accord est le contrôle de la "
               "section. Le cadre de gauche dit pourquoi la seconde est "
               "fragile — son diviseur s'annule dans l'aile — et cette "
               "fragilité n'est pas un détail d'implémentation : elle est "
               "la même quantité que la section suivante mesure, vue par "
               "l'autre bout. Une inversion numériquement fragile et une "
               "cotation imprécise sont un seul fait.")
    return b.render("Le vega contre la moneyness, et l ecart entre les deux "
                    "routes d inversion.")


# ---------------------------------------------------------------------------
# II. Le tick, et ce qu'il vaut en volatilité
# ---------------------------------------------------------------------------


def fig_iv_tick() -> str:
    """Un pas de cotation, traduit en points de volatilité."""
    b = _plate(500, "Implicite · le pas de cotation",
               "Un tick ne vaut pas le même nombre de points partout",
               "un tick de " + _num(I.TICK, 2) + " point")

    # L'abscisse est le **delta** et non la moneyness : à sept jours,
    # `S/K = 0,90` est au-delà de la frontière où l'option cesse de coter,
    # et une courbe tracée là ne dit rien. Le delta décrit le même objet à
    # toute échéance, ce qui est la raison même pour laquelle le guide le
    # recommande.
    ds = [0.02 + 0.007 * i for i in range(70)]
    series = [("hm7", "", 365.0), ("hm5", "6 3", 90.0), ("hm3", "2 3", 30.0),
              ("hm1", "1 3", 7.0)]

    p1 = Panel(b, PX1, 92, PW, 214,
               title="Points de volatilité par tick",
               readout="échelle logarithmique")
    courbes = [(cls, dash, j,
                [(d, I.points_de_vol_par_tick(
                    S, I.strike_du_delta(d, _t(j)), V, _t(j)))
                 for d in ds])
               for cls, dash, j in series]
    lo = min(y for _, _, _, c in courbes for _, y in c)
    hi = max(y for _, _, _, c in courbes for _, y in c)
    p1.domain(ds[0], ds[-1], lo * 0.75, hi * 1.4, ylog=True)
    p1.frame()
    p1.grid_y([0.1, 1.0, 10.0], _dec, dx=26.0)
    p1.grid_x([0.05, 0.15, 0.25, 0.35, 0.45], lambda v: _num(100.0 * v, 0),
              label="delta du strike")
    p1.hline(1.0, "lvl")
    for cls, dash, j, c in courbes:
        p1.path(c, cls, dash=dash, tip=_num(j, 0) + " jours")
    p1.label(ds[-1], 1.0, "un point de volatilité", dx=-8, dy=-9,
             anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Le même nombre, par delta",
               readout="points de volatilité")
    n = len(I.DELTAS)
    t30 = _t(30.0)
    vals = [(d, I.points_de_vol_par_tick(S, I.strike_du_delta(d, t30), V,
                                         t30))
            for d in I.DELTAS]
    haut = max(v for _, v in vals) * 1.45
    p2.domain(0.0, haut, -0.6, n - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, haut, 0.5), lambda v: _num(v, 1))
    p2.vline(1.0, "lvl")
    for i, (d, v) in enumerate(vals):
        y = n - 1 - i
        p2.hbar(y, 0.0, v, 13.0, "hm7",
                tip=_pct(d, 0) + " de delta : " + _num(v, 2))
        p2.label(0.0, y + 0.34, _num(100.0 * d, 0) + " deltas", dx=4, dy=0)
        p2.label(v, y, _num(v, 2), dx=7, dy=4)
    p2.label(1.0, -0.44, "un point", dx=6, dy=0)

    b.legend(0.0, 352.0,
             [("hm7", "un an"), ("hm5", "trois mois", "6 3"),
              ("hm3", "un mois", "2 3"), ("hm1", "une semaine", "1 3")],
             step=150.0, kind="line")
    b.annotation(0.0, 376.0,
                 "si l'implicite est un changement d'unités, la précision "
                 "de la traduction vaut cent fois le tick sur le véga")
    b.annotation(0.0, 392.0,
                 "elle diverge dans l'aile et près de l'échéance, donc "
                 "dans un marché parfaitement étroit")
    b.annotation(0.0, 408.0,
                 "le guide place sa remarque sur les marchés larges : la "
                 "mesure dit qu'elle vaut d'abord loin de la monnaie")

    _source(b, "Le guide fait de l'implicite un changement d'unités, et il "
               "a raison. Ce qu'il n'écrit pas est que la précision de la "
               "traduction se calcule et qu'elle n'est pas la même partout. "
               "Un pas de cotation vaut cent fois lui-même divisé par le "
               "véga, donc il diverge exactement là où le véga s'annule — "
               "dans l'aile et près de l'échéance. Sa remarque sur les "
               "fourchettes larges est donc juste et incomplète : la "
               "largeur en points de volatilité peut valoir plusieurs "
               "points sur un marché dont la fourchette en prix est d'un "
               "seul tick.")
    return b.render("Ce qu un pas de cotation vaut en points de volatilite, "
                    "par moneyness et par delta.")


def fig_iv_frontiere() -> str:
    """Les deux frontières : celle du point de vol, et celle du zéro coté."""
    b = _plate(500, "Implicite · les deux frontières",
               "L'option cesse de coter avant que l'arbitrage la borne",
               "du côté hors de la monnaie")

    js = [1.5 + 4.0 * i for i in range(92)]

    p1 = Panel(b, PX1, 92, PW, 214,
               title="Les deux frontières contre l'échéance",
               readout="spot sur strike")
    point = [(j, I.strike_du_point_de_vol(_t(j))) for j in js]
    cote = [(j, I.moneyness_cotable(_t(j))) for j in js]
    lo = min(y for _, y in cote)
    p1.domain(js[0], js[-1], lo * 0.94, 1.02)
    p1.frame()
    p1.grid_y(_ticks(lo * 0.94, 1.02, 0.1), lambda v: _num(v, 1), dx=24.0)
    p1.grid_x([50, 150, 250, 350], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.hline(1.0, "lvl")
    p1.path(point, "hm7", tip="un tick vaut un point de volatilité")
    p1.path(cote, "hm3", dash="5 4", tip="l'option cesse de coter")
    p1.dot(30.0, I.strike_du_point_de_vol(_t(30.0)), "hm7", "un mois",
           r=4.5)
    p1.label(30.0, I.strike_du_point_de_vol(_t(30.0)),
             "un mois : " + _num(I.strike_du_point_de_vol(_t(30.0)), 3),
             dx=12, dy=-9)
    p1.label(js[0], 0.995, "la monnaie", dx=8, dy=14)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Le delta de ces deux frontières",
               readout="delta du strike")
    dpoint = [(j, I.delta_du_strike(
        S, S / I.strike_du_point_de_vol(_t(j)), V, _t(j))) for j in js]
    dcote = [(j, I.delta_du_strike(
        S, S / I.moneyness_cotable(_t(j)), V, _t(j))) for j in js]
    p2.domain(js[0], js[-1], 0.0, 0.62)
    p2.frame()
    p2.grid_y([0.0, 0.15, 0.30, 0.45, 0.60], lambda v: _num(v, 2), dx=26.0)
    p2.grid_x([50, 150, 250, 350], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.path(dpoint, "hm7", tip="delta de la frontière du point")
    p2.path(dcote, "hm3", dash="5 4", tip="delta du zéro coté")
    p2.label(js[-1], 0.55, "on attendait une horizontale",
             dx=-8, dy=0, anchor="end")

    b.legend(0.0, 352.0,
             [("hm7", "un tick vaut un point de volatilité"),
              ("hm3", "l'option cesse de coter", "5 4")],
             step=280.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le guide borne l'existence de la solution par "
                 "l'arbitrage : une borne plus proche est celle du zéro coté")
    b.annotation(0.0, 392.0,
                 "une option dont le prix tombe sous un demi-tick s'affiche "
                 "à zéro, et zéro est sous le plancher d'arbitrage")
    b.annotation(0.0, 408.0,
                 "on attendait un lieu à delta constant, par analogie avec "
                 "le pic du vanna : la mesure le réfute franchement")

    _source(b, "Deux frontières, et le guide n'en nomme aucune. La "
               "première est le lieu où un seul pas de cotation vaut un "
               "point entier de volatilité, c'est-à-dire où l'objet coté "
               "cesse d'avoir deux chiffres significatifs. La seconde est "
               "plus radicale : au-delà, le prix théorique tombe sous un "
               "demi-tick, l'écran affiche zéro, et zéro est sous le "
               "plancher d'arbitrage — il n'y a donc aucune volatilité "
               "implicite, à aucune précision. Le cadre de droite porte une "
               "affirmation écrite d'avance et réfutée : on attendait un "
               "delta constant, par analogie avec le pic du vanna de la "
               "partie XXIV, et la mesure donne une décroissance d'un "
               "facteur dix. Le mécanisme est dans la formule — un seuil "
               "absolu sur une densité qui s'aplatit ne peut pas rendre un "
               "argument constant.")
    return b.render("Les deux frontieres de la cotation contre l echeance, "
                    "en moneyness et en delta.")


def fig_iv_relief_tick() -> str:
    """Le relief du pas de cotation."""
    z = [list(l) for l in I.surface_tick()]
    vals = [v for l in z for v in l]

    b = _plate(486, "Implicite · le relief du pas de cotation",
               "La précision de la traduction s'effondre dans un coin",
               "hauteur : points de volatilité par tick")

    _surface(b, 0.52 * W, 232.0, z, min(vals), max(vals), cx=42.0, cy=13.0,
             cz=158.0,
             row_labels=[_num(j, 0) + " j"
                         for j in I.SURF_JOURS_CROISSANT],
             col_labels=[_num(100.0 * d, 0) + " Δ" for d in I.SURF_DELTAS],
             z_ticks=[(t, _dec(10.0 ** t))
                      for t in _echine(min(vals), max(vals))],
             tip="{v:.2f}", tip_value=lambda v: 10.0 ** v, zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : l'échéance · arête droite : le delta du "
                 "strike · hauteur : ce qu'un tick vaut, en logarithme")
    b.annotation(0.0, 424.0,
                 "les deux axes sont ceux que le guide recommande, et le "
                 "delta est le seul qui décrive le même objet à toute échéance")
    b.annotation(0.0, 440.0,
                 "le sommet est le coin des échéances courtes et des ailes "
                 "lointaines, où le véga meurt et l'infobulle donne l'unité")

    _source(b, "La hauteur est le logarithme de ce qu'un seul pas de "
               "cotation vaut en points de volatilité, et l'infobulle "
               "publie la valeur dans son unité. L'axe des strikes est un "
               "delta et non une moneyness, pour la raison que le guide "
               "donne lui-même : une moneyness fixe ne décrit pas le même "
               "objet à deux échéances. Le premier jet la portait tout de "
               "même, et une cellule de sa grille rendait dix millions de "
               "points de volatilité par tick — un strike qui, à deux "
               "jours, ne cote plus du tout.")
    return b.render("Relief de ce qu un tick vaut en points de volatilite, "
                    "en echeance et en moneyness.")


# ---------------------------------------------------------------------------
# III. La fenêtre, son échantillon et son budget
# ---------------------------------------------------------------------------


def fig_iv_effectif() -> str:
    """Ce qu'une fenêtre de classement porte vraiment."""
    b = _plate(500, "Implicite · l'échantillon effectif",
               "Une année de séances porte deux observations",
               "sous retour à la moyenne")

    ns = [20 + 20 * i for i in range(63)]
    series = [("hm7", "", 8.0), ("hm5", "6 3", 4.0), ("hm3", "2 3", 2.0),
              ("hm1", "1 3", 1.0)]

    p1 = Panel(b, PX1, 92, PW, 214,
               title="L'échantillon effectif d'une fenêtre",
               readout="observations indépendantes")
    courbes = [(cls, dash, k,
                [(n, I.echantillon_effectif(n, k)) for n in ns])
               for cls, dash, k in series]
    hi = max(y for _, _, _, c in courbes for _, y in c)
    p1.domain(ns[0], ns[-1], 0.0, hi * 1.12)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi * 1.12, 5.0), lambda v: _num(v, 0), dx=22.0)
    p1.grid_x([252, 504, 756, 1008, 1260], lambda v: _num(v / 252.0, 0),
              label="années de séances")
    for cls, dash, k, c in courbes:
        p1.path(c, cls, dash=dash, tip="κ = " + _num(k, 0))
    p1.dot(252, I.echantillon_effectif(252, 4.0), "hm5", "un an à κ = 4",
           r=4.5)
    p1.label(ns[-1], 3.0,
             "un an à kappa quatre : "
             + _num(I.echantillon_effectif(252, 4.0), 1) + " observations",
             dx=-8, dy=0, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214,
               title="La forme fermée contre la mesure",
               readout="observations indépendantes")
    n2 = len(I.FENETRES)
    haut = max(I.echantillon_effectif(n, 4.0) for n in I.FENETRES) * 1.6
    p2.domain(0.0, haut, -0.6, n2 - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, haut, 3.0), lambda v: _num(v, 0))
    for i, n in enumerate(I.FENETRES):
        y = n2 - 1 - i
        a = I.echantillon_effectif(n, 4.0)
        m = I.echantillon_effectif_mesure(n, 4.0)
        p2.hbar(y + 0.19, 0.0, a, 8.0, "hm7", tip="forme fermée")
        p2.hbar(y - 0.19, 0.0, m, 8.0, "hm3", tip="mesuré")
        p2.label(0.0, y + 0.42, _num(n, 0) + " séances", dx=4, dy=0)
        p2.label(a, y + 0.19, _num(a, 1), dx=6, dy=4)
        p2.label(m, y - 0.19, _num(m, 1), dx=6, dy=4)

    b.legend(0.0, 352.0,
             [("hm7", "κ = 8 par an"), ("hm5", "κ = 4", "6 3"),
              ("hm3", "κ = 2", "2 3"), ("hm1", "κ = 1", "1 3")],
             step=150.0, kind="line")
    b.annotation(0.0, 376.0,
                 "la volatilité est persistante, donc une fenêtre de n "
                 "séances porte n fois un moins rho sur un plus rho")
    b.annotation(0.0, 392.0,
                 "cela vaut kappa T sur deux : le nombre d'observations "
                 "disparaît, seule la durée compte")
    b.annotation(0.0, 408.0,
                 "regarder la volatilité plus souvent n'apprend rien ; il "
                 "faut la regarder plus longtemps")

    _source(b, "C'est le résultat structurant de la partie, et il vient "
               "d'un fait que le guide ne mentionne pas. Une fenêtre de "
               "classement d'une année ne porte pas deux cent cinquante-deux "
               "observations mais deux, parce que la volatilité met environ "
               "un trimestre à oublier où elle était. Le cadre de droite "
               "compare la forme fermée à la dispersion mesurée d'un "
               "percentile sur quatre cents fenêtres tirées ; les deux se "
               "referment, ce qui autorise la première. La vitesse de retour "
               "à la moyenne n'est pas observable dans ce dépôt, donc elle "
               "est balayée et jamais choisie.")
    return b.render("L echantillon effectif d une fenetre de classement, "
                    "contre sa longueur et la vitesse de retour.")


def fig_iv_budget() -> str:
    """Les années qu'il faut pour séparer deux percentiles."""
    b = _plate(490, "Implicite · le budget",
               "Le plus lourd des dix budgets d'information",
               "à quatre-vingt-quinze pour cent")

    ps = [0.52 + 0.005 * i for i in range(96)]
    series = [("hm7", "", 8.0), ("hm5", "6 3", 4.0), ("hm3", "2 3", 2.0)]

    p1 = Panel(b, PX1, 92, PW, 214,
               title="Contre l'écart de percentile",
               readout="échelle logarithmique")
    courbes = [(cls, dash, k,
                [(p, I.annees_pour_distinguer(p, 0.50, k)) for p in ps])
               for cls, dash, k in series]
    p1.domain(ps[0], ps[-1], 0.3, 900.0, ylog=True)
    p1.frame()
    p1.grid_y([1.0, 10.0, 100.0], _dec, dx=26.0)
    p1.grid_x([0.6, 0.7, 0.8, 0.9], lambda v: _num(100.0 * v, 0),
              label="percentile observé, contre cinquante")
    p1.hline(10.0, "lvl")
    for cls, dash, k, c in courbes:
        p1.path(c, cls, dash=dash, tip="κ = " + _num(k, 0))
    p1.label(ps[0], 13.0, "dix ans", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Quatre-vingts contre cinquante",
               readout="années requises")
    ks = [(k, I.annees_pour_distinguer(0.80, 0.50, k))
          for k in I.KAPPA_GRILLE]
    n = len(ks)
    haut = max(v for _, v in ks) * 1.42
    p2.domain(0.0, haut, -0.6, n - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, haut, 10.0), lambda v: _num(v, 0))
    for i, (k, v) in enumerate(ks):
        y = n - 1 - i
        p2.hbar(y, 0.0, v, 13.0, "hm7",
                tip="κ = " + _num(k, 0) + " : " + _num(v, 1) + " ans")
        p2.label(0.0, y + 0.34, "κ = " + _num(k, 0), dx=4, dy=0)
        p2.label(v, y, _num(v, 1), dx=7, dy=4)

    b.legend(0.0, 352.0,
             [("hm7", "κ = 8 par an"), ("hm5", "κ = 4", "6 3"),
              ("hm3", "κ = 2", "2 3")],
             step=200.0, kind="line")
    b.annotation(0.0, 376.0,
                 "l'échantillon requis vaut le carré de l'inverse de "
                 "l'écart, et la persistance le multiplie encore")
    b.annotation(0.0, 392.0,
                 "séparer quatre-vingts de cinquante demande "
                 + _num(I.annees_pour_distinguer(0.80, 0.50), 1)
                 + " ans à la vitesse de référence")
    b.annotation(0.0, 408.0,
                 "annoncer la fenêtre est juste et insuffisant : elle ne "
                 "dit pas l'échantillon qu'elle porte")

    _source(b, "Le budget d'information de la partie IV, rencontré sur un "
               "dixième objet, et le plus lourd des dix. Le guide "
               "recommande d'annoncer la fenêtre de classement, ce qui est "
               "la bonne recommandation et ne suffit pas : deux outils qui "
               "annoncent la même fenêtre sur deux actifs de vitesses "
               "différentes publient deux nombres qui n'ont pas la même "
               "précision, et rien dans leur affichage ne le dit. La "
               "vitesse est le paramètre qu'il faudrait annoncer, et "
               "personne ne l'observe.")
    return b.render("Les annees requises pour separer deux percentiles, "
                    "contre l ecart et la vitesse de retour.")


def fig_iv_relief_effectif() -> str:
    """Le relief de l'échantillon effectif."""
    z = [list(l) for l in I.surface_effectif()]
    vals = [v for l in z for v in l]

    b = _plate(486, "Implicite · le relief de l'échantillon",
               "La longueur de la fenêtre n'achète presque rien",
               "hauteur : observations indépendantes")

    _surface(b, 0.52 * W, 232.0, z, min(vals), max(vals), cx=42.0, cy=13.0,
             cz=158.0,
             row_labels=[_num(k, 1) for k in I.SURF_KAPPA],
             col_labels=[_num(n / 252.0, 0) + " an" for n in I.SURF_FENETRE],
             z_ticks=[(t, _num(t, 0)) for t in _echine(min(vals), max(vals))],
             tip="{v:.1f}", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : la vitesse de retour à la moyenne · arête "
                 "droite : la fenêtre · hauteur : l'échantillon effectif")
    b.annotation(0.0, 424.0,
                 "la surface est un plan : l'échantillon vaut kappa fois "
                 "la durée sur deux, un simple produit")
    b.annotation(0.0, 440.0,
                 "le coin lointain porte cinq ans à seize par an, et il ne "
                 "monte encore qu'à quarante observations")

    _source(b, "La hauteur est le nombre d'observations indépendantes que "
               "porte une fenêtre. Le relief dit ce que la table chiffre : "
               "la surface est un produit, donc allonger la fenêtre et "
               "accélérer le retour à la moyenne comptent exactement pareil, "
               "et aucune des deux ne rachète l'autre. Le coin proche est "
               "celui d'un outil ordinaire — un an de fenêtre sur un actif "
               "lent — et il y porte moins d'une observation.")
    return b.render("Relief de l echantillon effectif, en vitesse de retour "
                    "et en longueur de fenetre.")


def fig_iv_relief_budget() -> str:
    """Le relief du budget."""
    z = [list(l) for l in I.surface_budget()]
    vals = [v for l in z for v in l]

    b = _plate(486, "Implicite · le relief du budget",
               "Ce qu'un percentile coûte pour se distinguer de la médiane",
               "hauteur : années requises")

    _surface(b, 0.52 * W, 232.0, z, min(vals), max(vals), cx=42.0, cy=13.0,
             cz=158.0,
             row_labels=[_num(k, 1) for k in I.SURF_KAPPA_BUDGET],
             col_labels=[_num(100.0 * p, 0) for p in I.SURF_PERCENTILES],
             z_ticks=[(t, _dec(10.0 ** t))
                      for t in _echine(min(vals), max(vals))],
             tip="{v:.1f}", tip_value=lambda v: 10.0 ** v, zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : la vitesse de retour · arête droite : le "
                 "percentile observé · hauteur : les années requises")
    b.annotation(0.0, 424.0,
                 "le mur est du côté des percentiles proches de la médiane, "
                 "parce que le budget croît comme le carré de l'inverse")
    b.annotation(0.0, 440.0,
                 "la hauteur porte le logarithme, et l'infobulle publie "
                 "les années : un plafond ferait un plateau, pas un sommet")

    _source(b, "La hauteur est le nombre d'années de données qu'il faut "
               "pour affirmer qu'un percentile diffère de la médiane. Le "
               "relief montre les deux façons d'être ruiné : un actif lent, "
               "et un percentile qui n'est pas extrême. Un outil qui affiche "
               "« percentile 62 » sur une fenêtre d'un an ne publie pas une "
               "mesure, il publie un tirage. C'est la même conclusion que la "
               "partie XVIII tire de la bande d'un ratio de Calmar, et elle "
               "vient de la même cause : une statistique qu'on lit sur trop "
               "peu d'observations effectives.")
    return b.render("Relief des annees requises pour distinguer un "
                    "percentile de la mediane.")


# ---------------------------------------------------------------------------
# IV. Le pic, et le look-ahead
# ---------------------------------------------------------------------------


def fig_iv_pic() -> str:
    """Ce qu'un seul jour de crise fait aux deux statistiques."""
    b = _plate(510, "Implicite · le rang et le percentile",
               "Le rang est hostage d'un point, le percentile d'un sur n",
               "un pic qui double le maximum")

    s = I.serie(I.SEANCES_AN + 1, graine=I.SEED + 31)
    fen, val = s[:-1], s[-1]

    p1 = Panel(b, PX1, 92, PW, 214, title="Une année de volatilité",
               readout="volatilité, en points")
    c = [(i, 100.0 * v) for i, v in enumerate(fen)]
    hi = max(y for _, y in c)
    lo = min(y for _, y in c)
    p1.domain(0.0, len(fen) - 1.0, lo * 0.90, hi * 1.30)
    p1.frame()
    p1.grid_y(_ticks(lo * 0.90, hi * 1.30, 10.0), lambda v: _num(v, 0),
              dx=22.0)
    p1.grid_x([0, 63, 126, 189, 251], lambda v: _num(v, 0),
              label="séances")
    p1.hline(100.0 * val, "lvl")
    p1.path(c, "hm5", tip="volatilité simulée")
    p1.label(0.0, lo * 0.96,
             "le jour classé : " + _num(100.0 * val, 1) + " points",
             dx=8, dy=0)
    p1.label(len(fen) - 1.0, hi * 1.22, "le maximum décide du rang", dx=-8,
             dy=0, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Ce qu'un pic déplace",
               readout="échelle logarithmique")
    n = len(I.FENETRES)
    p2.domain(0.0004, 0.9, -0.6, n - 0.4, xlog=True)
    p2.frame()
    p2.grid_x([0.001, 0.01, 0.1], _dec)
    for i, f in enumerate(I.FENETRES):
        y = n - 1 - i
        a = I.sensibilite_moyenne_du_rang(f)
        p2.hbar(y + 0.19, 0.0004, a, 8.0, "hm7",
                tip="le rang recule de " + _num(a, 3))
        p2.hbar(y - 0.19, 0.0004, 1.0 / f, 8.0, "hm1",
                tip="le percentile bouge au plus de " + _num(1.0 / f, 5))
        p2.label(0.0004, y + 0.42, _num(f, 0) + " séances", dx=4, dy=0)
        p2.label(a, y, "×" + _num(I.borne_du_rapport(f), 0), dx=7, dy=4)

    b.legend(0.0, 362.0,
             [("hm5", "la volatilité simulée"),
              ("hm7", "le recul du rang, à droite"),
              ("hm1", "le maximum du percentile, un sur n")],
             step=180.0)
    b.annotation(0.0, 386.0,
                 "le rang a le maximum de la fenêtre au dénominateur, donc "
                 "un seul point le déplace de tout ce qu'il ajoute")
    b.annotation(0.0, 402.0,
                 "le percentile ne peut pas bouger de plus d'un point sur "
                 "n, et dans la plupart des tirages il ne bouge pas du tout")
    b.annotation(0.0, 418.0,
                 "allonger la fenêtre stabilise l'un et déstabilise l'autre "
                 "dans la même proportion")
    b.annotation(0.0, 434.0,
                 "c'est le défaut du Calmar de la partie XVIII, sur un "
                 "troisième objet : il n'y a qu'un maximum dans une série")

    _source(b, "Le guide recommande le percentile plutôt que le rang, et il "
               "donne la bonne raison : un jour de crise peut tenir le rang "
               "artificiellement bas pendant un an. La mesure ajoute le "
               "facteur. Le rang a un maximum au dénominateur et le "
               "percentile un comptage, donc leurs sensibilités à un point "
               "isolé sont dans le rapport de la taille de la fenêtre. "
               "Allonger la fenêtre, geste par lequel on croit stabiliser "
               "une statistique, aggrave le rang exactement autant qu'il "
               "améliore le percentile.")
    return b.render("Une annee de volatilite simulee, et ce qu un pic "
                    "deplace sur le rang et sur le percentile.")


def fig_iv_look_ahead() -> str:
    """La loi nulle du test que le guide publie."""
    b = _plate(510, "Implicite · le look-ahead",
               "Le motif que le guide a vu disparaître, sous loi nulle",
               "sans prévisibilité")

    hs = list(I.HORIZONS)

    p1 = Panel(b, PX1, 92, PW, 214,
               title="Les deux classements contre l'horizon",
               readout="corrélation au résultat")
    gliss = [(h, I.biais_de_look_ahead(horizon=h).glissant) for h in hs]
    fuite = [(h, I.biais_de_look_ahead(horizon=h).fuite) for h in hs]
    seuil = [(h, I.biais_de_look_ahead(horizon=h).seuil) for h in hs]
    hi = max(y for _, y in fuite) * 1.30
    p1.domain(hs[0], hs[-1], -0.06, hi)
    p1.frame()
    p1.grid_y(_ticks(-0.06, hi, 0.1), lambda v: _signed(v, 1), dx=26.0)
    p1.grid_x([5, 21, 42, 63], lambda v: _num(v, 0),
              label="séances de détention")
    p1.hline(0.0, "lvl")
    p1.path(seuil, "hm1", dash="2 3", tip="seuil à 95 %")
    p1.path(fuite, "hm7", tip="fenêtre fuitée")
    p1.path(gliss, "hm3", tip="fenêtre glissante")
    p1.dot(21, I.biais_de_look_ahead(horizon=21).fuite, "hm7", "un mois",
           r=4.5)
    p1.label(hs[0], hi * 0.90, "la fuite grandit avec l'horizon", dx=8, dy=0)
    p1.label(hs[-1], -0.038, "le classement glissant ne prédit rien",
             dx=-8, dy=0, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214,
               title="L'espérance du gain, qui doit être nulle",
               readout="en écarts-types de sa moyenne")
    n = len(hs)
    p2.domain(-2.4, 2.4, -0.6, n - 0.4)
    p2.frame()
    p2.grid_x([-2, -1, 0, 1, 2], lambda v: _signed(v, 0))
    p2.band_x(-2.0, 2.0, "wash")
    p2.vline(0.0, "lvl")
    for i, h in enumerate(hs):
        y = n - 1 - i
        e = I.biais_de_look_ahead(horizon=h).esperance
        p2.hbar(y, 0.0, e, 12.0, "hm5",
                tip=_num(h, 0) + " séances : " + _num(e, 2))
        p2.label(-2.3, y + 0.34, _num(h, 0) + " séances", dx=4, dy=0)
    p2.label(2.0, -0.44, "la bande à deux écarts-types", dx=-6, dy=0,
             anchor="end")

    b.legend(0.0, 362.0,
             [("hm7", "fenêtre fuitée"), ("hm3", "fenêtre glissante"),
              ("hm1", "le seuil à 95 %", "2 3")],
             step=200.0, kind="line")
    b.annotation(0.0, 386.0,
                 "la volatilité simulée n'a aucune prévisibilité, et le "
                 "gain d'un vendeur y est d'espérance nulle par construction")
    b.annotation(0.0, 402.0,
                 "le cadre de droite le contrôle : les cinq espérances "
                 "tiennent dans la bande à deux écarts-types")
    b.annotation(0.0, 418.0,
                 "classer contre une fenêtre qui contient l'avenir fabrique "
                 "une corrélation franche, et elle grandit avec l'horizon")
    b.annotation(0.0, 434.0,
                 "le guide a publié le résultat négatif ; voici le résultat "
                 "positif que le bug fabrique")

    _source(b, "Le guide écrit qu'une relation monotone entre le rang et "
               "les résultats à venir disparaît entièrement dès que la "
               "fenêtre de classement est rendue strictement glissante, et "
               "que le motif était un artefact du classement. C'est le "
               "second des dix guides à publier le résultat de son propre "
               "test négatif, et c'est le seul dont ce résultat porte sur "
               "un outil qu'il recommande par ailleurs. La loi nulle est "
               "reproduite ici : une volatilité sans la moindre "
               "prévisibilité, un gain d'espérance nulle par construction, "
               "et un classement fuité qui prédit tout de même.")
    return b.render("Les deux classements contre l horizon, et le controle "
                    "de l esperance nulle du gain.")


# ---------------------------------------------------------------------------
# V. La prime, et l'unité qui la fabrique
# ---------------------------------------------------------------------------


def fig_iv_prime() -> str:
    """La prime annoncée, et ce qu'il faut pour l'établir."""
    b = _plate(500, "Implicite · la prime",
               "Deux à quatre points, et le temps qu'ils coûtent",
               "une expiration d'un mois")

    ps = [0.2 + 0.1 * i for i in range(59)]

    p1 = Panel(b, PX1, 92, PW, 214,
               title="Les années contre l'avantage",
               readout="échelle logarithmique")
    c = [(p, I.campagne(round(p, 1)).annees) for p in ps]
    p1.domain(ps[0], ps[-1], 0.05, 200.0, ylog=True)
    p1.frame()
    p1.grid_y([0.1, 1.0, 10.0, 100.0], _dec, dx=26.0)
    p1.grid_x([1, 2, 3, 4, 5, 6], lambda v: _num(v, 0),
              label="avantage, en points de volatilité")
    p1.band_x(I.PRIME_ANNONCEE[0], I.PRIME_ANNONCEE[1], "wash")
    p1.path(c, "hm7", tip="années requises")
    for p in I.PRIME_ANNONCEE:
        p1.dot(p, I.campagne(p).annees, "hm7", _num(p, 0) + " points", r=4.5)
    p1.label(ps[0], 90.0, "la fourchette annoncée", dx=8, dy=0)
    p1.label(I.PRIME_ANNONCEE[1], I.campagne(2.0).annees,
             _num(I.campagne(2.0).annees, 1) + " an à deux points",
             dx=10, dy=-9)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="La fréquence de gain",
               readout="part des expirations gagnantes")
    f = [(p, I.campagne(round(p, 1)).taux) for p in ps]
    p2.domain(0.0, ps[-1], 0.45, 1.02)
    p2.frame()
    p2.grid_y([0.5, 0.6, 0.7, 0.8, 0.9, 1.0], lambda v: _num(100.0 * v, 0),
              dx=26.0)
    p2.grid_x([0, 2, 4, 6], lambda v: _num(v, 0),
              label="avantage, en points de volatilité")
    p2.hline(0.5, "lvl")
    p2.path(f, "hm5", tip="fréquence de gain")
    p2.dot(0.0, I.taux_d_equilibre(), "hm5", "sans avantage", r=4.5)
    p2.label(0.0, I.taux_d_equilibre(),
             "sans avantage : " + _pct(I.taux_d_equilibre()), dx=10, dy=-8)
    p2.label(ps[-1], 0.52, "un demi", dx=-8, dy=0, anchor="end")

    b.legend(0.0, 352.0,
             [("hm7", "les années requises"),
              ("hm5", "la fréquence de gain, à droite")],
             step=240.0, kind="line")
    b.annotation(0.0, 376.0,
                 "un vendeur sans avantage gagne "
                 + _pct(I.taux_d_equilibre()) + " de ses expirations : la "
                 "médiane d'un khi-deux tombe sous sa moyenne")
    b.annotation(0.0, 392.0,
                 "c'est le mécanisme de la partie XXI sur un autre "
                 "estimateur, et c'est ce qui fait vivre la prime courte")
    b.annotation(0.0, 408.0,
                 "établir le bas de la fourchette annoncée demande "
                 + _num(I.campagne(2.0).annees, 1) + " an, un seul point "
                 + _num(I.campagne(1.0).annees, 1) + " ans")

    _source(b, "Le guide annonce deux à quatre points de prime en indice "
               "actions et décrit l'asymétrie exactement. Les deux moitiés "
               "se mesurent. La fréquence de gain sans avantage est le "
               "chiffre à retenir : plus d'une expiration sur deux se solde "
               "positivement pour un vendeur qui n'a rien, parce que la "
               "réalisée d'un échantillon tombe sous sa valeur vraie plus "
               "souvent qu'elle ne la dépasse. Un relevé de performance sur "
               "quelques trimestres ne distingue donc pas un vendeur qui a "
               "un avantage d'un vendeur qui n'en a aucun.")
    return b.render("Les annees requises et la frequence de gain d un "
                    "vendeur de prime, contre son avantage.")


def fig_iv_unite() -> str:
    """La prime qu'un changement d'unités fabrique."""
    b = _plate(500, "Implicite · l'unité",
               "Une part de la prime publiée est une propriété de l'unité",
               "à implicite égale à la vérité")

    hs = [3 + i for i in range(90)]

    p1 = Panel(b, PX1, 92, PW, 214,
               title="Le biais d'unité contre l'horizon",
               readout="points de volatilité")
    mes = [(h, I.biais_d_unite(h)) for h in (5, 10, 21, 42, 63, 90)]
    fer = [(h, I.biais_d_unite_ferme(h)) for h in hs]
    hi = max(y for _, y in fer)
    p1.domain(hs[0], hs[-1], 0.0, hi * 1.15)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi * 1.15, 0.4), lambda v: _num(v, 1), dx=26.0)
    p1.grid_x([21, 42, 63, 84], lambda v: _num(v, 0),
              label="séances jusqu'à l'expiration")
    p1.path(fer, "hm4", tip="forme fermée sigma sur quatre h")
    for h, v in mes:
        p1.dot(h, v, "hm1", _num(h, 0) + " séances : " + _num(v, 3), r=4.0)
    p1.label(hs[-1], hi * 0.55, "les points sont la mesure", dx=-8, dy=0,
             anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Les deux comptabilités du même livre",
               readout="espérance par expiration")
    n = len(I.PRIMES)
    vol = 100.0 * I.VOL_MOYENNE
    haut = max(I.campagne(p).moyenne for p in I.PRIMES) * 1.35
    p2.domain(0.0, haut, -0.6, n - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, haut, 2.0), lambda v: _num(v, 0))
    for i, p in enumerate(I.PRIMES):
        y = n - 1 - i
        c = I.campagne(p)
        p2.hbar(y + 0.19, 0.0, c.moyenne, 8.0, "hm7",
                tip="en volatilité : " + _num(c.moyenne, 3))
        p2.hbar(y - 0.19, 0.0, c.moyenne_variance / (2.0 * vol), 8.0, "hm3",
                tip="en variance, ramenée : "
                    + _num(c.moyenne_variance / (2.0 * vol), 3))
        p2.label(0.0, y + 0.40,
                 _num(p, 0) + (" point" if p < 2.0 else " points")
                 + " d'avantage", dx=4, dy=0)


    b.legend(0.0, 352.0,
             [("hm4", "la forme fermée"), ("hm1", "la mesure"),
              ("hm7", "en volatilité"), ("hm3", "en variance")],
             step=140.0)
    b.annotation(0.0, 376.0,
                 "implicite égale à la vérité, et le vendeur encaisse tout "
                 "de même " + _num(I.biais_d_unite(), 2) + " point")
    b.annotation(0.0, 392.0,
                 "la racine est concave, donc la réalisée d'un échantillon "
                 "tombe en moyenne sous sa valeur vraie")
    b.annotation(0.0, 408.0,
                 "en variance la même position rend zéro exactement : "
                 "l'écart est une propriété de l'unité de cotation")

    _source(b, "Le sous-titre du guide est qu'une option est un prix coté "
               "dans les mauvaises unités, exprès, et il ne va pas jusqu'au "
               "bout de sa propre remarque. Voici ce que l'unité coûte. Un "
               "vendeur dont l'implicite égale exactement la volatilité "
               "vraie a une espérance nulle en variance et une espérance "
               "positive en volatilité, parce que la racine est concave. Le "
               "biais vaut un neuvième du bas de la fourchette que le guide "
               "annonce, et sa forme fermée referme la mesure à quelques "
               "pour cent. Une part de la prime de risque de volatilité "
               "publiée est une propriété de la façon de coter.")
    return b.render("Le biais d unite contre l horizon, et les deux "
                    "comptabilites du meme livre.")


def fig_iv_relief_prime() -> str:
    """Le relief de la prime."""
    z = [list(l) for l in I.surface_prime()]
    vals = [v for l in z for v in l]

    b = _plate(486, "Implicite · le relief de la prime",
               "Ce qu'un avantage de volatilité coûte à établir",
               "hauteur : années requises")

    _surface(b, 0.52 * W, 232.0, z, min(vals), max(vals), cx=42.0, cy=13.0,
             cz=158.0,
             row_labels=[_num(h, 0) + " s" for h in I.SURF_HORIZONS],
             col_labels=[_num(p, 1) for p in I.SURF_PRIMES],
             z_ticks=[(t, _num(t, 0)) for t in _echine(min(vals), max(vals))],
             tip="{v:.1f}", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : la durée d'une expiration · arête droite : "
                 "l'avantage · hauteur : les années requises")
    b.annotation(0.0, 424.0,
                 "le mur est du côté des petits avantages, et il monte "
                 "comme le carré de leur inverse")
    b.annotation(0.0, 440.0,
                 "l'axe de la durée compte aussi : la même campagne prend "
                 "plus longtemps quand chaque décision dure plus longtemps")

    _source(b, "La hauteur est le nombre d'années qu'il faut pour "
               "distinguer un avantage de zéro à quatre-vingt-quinze pour "
               "cent. Les deux axes ne jouent pas le même rôle et c'est ce "
               "que le relief montre : l'avantage décide de la hauteur du "
               "mur, la durée d'une expiration décide de la vitesse à "
               "laquelle on l'escalade. Un vendeur d'hebdomadaires collecte "
               "quatre fois plus de décisions par an qu'un vendeur de "
               "mensuelles, et c'est le seul levier qu'il contrôle "
               "entièrement.")
    return b.render("Relief des annees requises pour etablir une prime, en "
                    "duree d expiration et en avantage.")


# ---------------------------------------------------------------------------
# VI. Les pièges, et le décompte
# ---------------------------------------------------------------------------


def fig_iv_pieges() -> str:
    """Les cinq pièges, tous dans la même unité."""
    b = _plate(500, "Implicite · les cinq pièges",
               "Le classement n'est pas celui de la liste",
               "points de volatilité")

    ps = sorted(I.pieges(), key=lambda x: -x.cout)
    n = len(ps)

    p1 = Panel(b, PX1, 92, PW, 214, title="Ce que chacun coûte",
               readout="échelle logarithmique")
    haut = max(p.cout for p in ps) * 2.2
    p1.domain(0.25, haut, -0.6, n - 0.4, xlog=True)
    p1.frame()
    p1.grid_x([1.0, 10.0], _dec)
    p1.vline(1.0, "lvl")
    for i, p in enumerate(ps):
        y = n - 1 - i
        cls = "hm1" if p.nom.startswith("Grecs") else "hm7"
        p1.hbar(y, 0.25, p.cout, 13.0, cls,
                tip=p.nom + " : " + _num(p.cout, 2))
        p1.label(0.25, y + 0.34, p.nom.split(" :")[0], dx=4, dy=0)
        p1.label(p.cout, y, _num(p.cout, 2), dx=7, dy=4)
    p1.label(1.0, -0.44, "un point", dx=6, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Le forward faux et le prix périmé",
               readout="points de volatilité")
    dss = [0.0002 * S * (i + 1) for i in range(50)]
    t = _t(30.0)
    ferme = [(d / S, abs(I.derive_par_deplacement(S, S, V, t, d)))
             for d in dss]
    mesure = [(d / S, abs(I.derive_par_deplacement_mesure(S, S, V, t, d)))
              for d in dss]
    hi = max(y for _, y in mesure) * 1.15
    p2.domain(0.0, dss[-1] / S, 0.0, hi)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi, 1.0), lambda v: _num(v, 0), dx=22.0)
    p2.grid_x([0.0, 0.005, 0.01], lambda v: _num(100.0 * v, 1),
              label="déplacement du comptant, en pour cent")
    p2.path(mesure, "hm4", tip="par réinversion")
    p2.path(ferme, "hm1", dash="2 3", tip="delta fois delta S sur véga")
    p2.label(0.0, hi * 0.90,
             "le premier ordre manque "
             + _pct(I.ecart_du_premier_ordre(S, S, V, t, 0.01 * S), 1)
             + " à un pour cent", dx=8, dy=0)

    b.legend(0.0, 352.0,
             [("hm7", "quatre pièges"), ("hm1", "leur somme"),
              ("hm4", "par réinversion, à droite")],
             step=180.0)
    b.annotation(0.0, 376.0,
                 "un grec calculé ailleurs ne cache pas un des quatre "
                 "autres : il les cache tous, donc son coût est leur somme")
    b.annotation(0.0, 392.0,
                 "un forward faux et un prix périmé sont le même nombre, "
                 "delta fois le déplacement sur le véga")
    b.annotation(0.0, 408.0,
                 "la forme fermée n'est que le premier ordre : le second "
                 "porte le gamma et se voit dès le demi pour cent")

    _source(b, "Le guide nomme cinq pièges pratiques et n'en chiffre aucun. "
               "Les mettre tous dans la même unité est ce qui les rend "
               "comparables, et le classement qui en sort n'est pas celui "
               "de la liste : le cinquième arrive en tête parce qu'il est "
               "la somme des quatre autres. Un grec qu'on n'a pas calculé "
               "soi-même cache le forward employé, le taux, la convention "
               "de prix et l'âge de la cotation, et le remède que le guide "
               "propose — réinverser depuis la prime brute — est le seul "
               "qui les traite ensemble. Le cadre de droite contrôle la "
               "forme fermée contre une réinversion complète au comptant "
               "faux : les deux partent ensemble et se séparent au-delà du "
               "demi pour cent, parce que la forme fermée est un premier "
               "ordre et que le second porte le gamma. La légende publie "
               "l'écart plutôt que d'annoncer une superposition que la "
               "figure contredirait.")
    return b.render("Le cout des cinq pieges en points de volatilite, et le "
                    "controle de la forme fermee du deplacement.")


def fig_iv_reste() -> str:
    """Le décompte, et le cumul des dix parties d'options."""
    b = _plate(500, "Implicite · le décompte",
               "Dix documents, et le dixième publie son propre résultat négatif",
               "dix parties d'options")

    grandeurs = ("la direction", "l'horloge", "le risque", "rien")
    compte = I.compte_par_grandeur()
    n = len(grandeurs)
    p1 = Panel(b, PX1, 92, PW, 246, title="Ce qu'elles déplacent",
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

    fam = I.familles()
    m = len(fam)
    p2 = Panel(b, PX2, 92, PW, 246, title="Le cumul des dix parties",
               readout="affirmations examinées")
    hautf = max(v for _, v in fam) * 1.45
    p2.domain(0.0, hautf, -0.6, m - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, hautf, 3.0), lambda v: _num(v, 0))
    for i, (nom, v) in enumerate(fam):
        y = m - 1 - i
        p2.hbar(y, 0.0, v, 7.0, "hm5", tip=nom + " : " + _num(v, 0))
        p2.label(0.0, y + 0.40, nom, dx=4, dy=0)
        p2.label(v, y, _num(v, 0), dx=7, dy=4)

    b.legend(0.0, 384.0,
             [("hm7", "ce qu'elles déplacent"),
              ("hm1", "la direction, vide"),
              ("hm5", "par partie, à droite")],
             step=200.0)
    b.annotation(0.0, 408.0,
                 "sur les " + _num(sum(v for _, v in fam), 0)
                 + " affirmations des dix parties d'options, aucune ne "
                 "donne un sens")
    b.annotation(0.0, 424.0,
                 "c'est le second des dix guides à publier le résultat de "
                 "son propre test négatif, après celui du vanna")
    b.annotation(0.0, 440.0,
                 "et le seul des deux dont ce résultat porte sur un outil "
                 "qu'il recommande par ailleurs")

    _source(b, "La colonne de la direction est vide pour la septième partie "
               "consécutive. Ce qui distingue ce dixième guide n'est pas la "
               "qualité de ses formules mais son honnêteté sur un point "
               "précis : il a testé sa propre statistique préférée, trouvé "
               "que la relation disparaissait dès que le classement cessait "
               "de regarder l'avenir, et publié ce résultat. Un guide qui "
               "écrit que son outil ne prédit rien une fois calculé "
               "proprement est un guide qu'on peut lire.")
    return b.render("Le decompte des affirmations par ce qu elles deplacent, "
                    "et le cumul des dix parties d options.")


# ---------------------------------------------------------------------------
# Le catalogue
# ---------------------------------------------------------------------------


def render_all() -> dict[str, str]:
    return {
        "ivinversion": fig_iv_inversion(),
        "ivroutes": fig_iv_routes(),
        "ivtick": fig_iv_tick(),
        "ivfrontiere": fig_iv_frontiere(),
        "ivrelieftk": fig_iv_relief_tick(),
        "iveffectif": fig_iv_effectif(),
        "ivbudget": fig_iv_budget(),
        "ivreliefef": fig_iv_relief_effectif(),
        "ivreliefbu": fig_iv_relief_budget(),
        "ivpic": fig_iv_pic(),
        "ivlookahead": fig_iv_look_ahead(),
        "ivprime": fig_iv_prime(),
        "ivunite": fig_iv_unite(),
        "ivreliefpr": fig_iv_relief_prime(),
        "ivpieges": fig_iv_pieges(),
        "ivreste": fig_iv_reste(),
    }
