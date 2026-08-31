"""Les planches de la partie qui regarde un fonds, puis se retourne.

Dix planches, six en deux dimensions et quatre en relief. L'ordre est celui de
l'argument : d'abord ce que la loi fondamentale exige, puis le prix de la
preuve, puis le plafond d'un panier de lectures, puis les deux terrains où un
opérateur seul est en avance — la taille et l'exécution — et enfin le
décompte de ce qui transfère.

Chaque planche porte sa loi nulle ou son seuil dessiné, jamais seulement cité.
Une figure qui montrerait une exigence sans montrer où elle cesse d'être
crédible n'apprendrait rien.
"""

from __future__ import annotations

import math

from . import fonds as F
from . import seuil as S
from .figdisc import W, _plate, _source, _surface
from .figterm import Board, Panel, _num, _signed


def _pct(v: float, nd: int = 0) -> str:
    return _num(100.0 * v, nd) + " %"


PW = (W - 74.0) / 2.0 - 30.0
PX1 = 74.0
PX2 = 74.0 + (W - 74.0) / 2.0


def _ticks(lo: float, hi: float, pas: float) -> list[float]:
    """Graduations strictement dans le domaine — `grid_y` ne découpe pas."""
    out, v = [], math.ceil(lo / pas) * pas
    while v <= hi + 1e-12:
        out.append(round(v, 10))
        v += pas
    return out


# ---------------------------------------------------------------------------
# I. La loi fondamentale
# ---------------------------------------------------------------------------


def fig_fds_ampleur() -> str:
    """Ce que la loi fondamentale exige, et où l'exigence cesse d'être crédible.

    À gauche, la relation elle-même : la finesse de prévision requise tombe
    comme la racine du nombre de décisions. À droite, la même chose écrite
    dans l'unité qu'un opérateur reconnaît — le taux de réussite — avec le
    seuil de vraisemblance posé dessus.

    Le point où la courbe traverse ce seuil est le seul chiffre de la planche
    qui décide de quelque chose.
    """
    b = _plate(446, "Loi fondamentale · IR = IC racine de N",
               "Ce qu'un ratio d'information exige, décision par décision",
               "ratio déclaré : " + _num(F.IR_REF, 0))

    p1 = Panel(b, PX1, 92, PW, 214, title="Finesse de prévision requise",
               readout="IC")
    p1.domain(300.0, 4e7, 2e-4, 0.4, xlog=True, ylog=True)
    p1.frame()
    p1.grid_y([1e-3, 1e-2, 1e-1], lambda v: _num(v, 3), dx=44.0)
    p1.grid_x([1e3, 1e5, 1e7], lambda v: _num(v, 0))
    for ir, cls, dash in ((1.0, "hm3", "3 3"), (2.0, "hm7", ""),
                          (4.0, "hm5", "7 3")):
        pts = []
        n = 300.0
        while n <= 4e7:
            pts.append((n, F.ic_requis(ir, n)))
            n *= 1.25
        p1.path(pts, cls, dash=dash, tip="IR = " + _num(ir, 0))
    p1.dot(F.OPERATEUR_DECISIONS, F.ic_requis(F.IR_REF, F.OPERATEUR_DECISIONS),
           "hm7", "un opérateur : " + _num(F.OPERATEUR_DECISIONS, 0)
           + " décisions par an", r=4.0)
    p1.dot(F.RYTHME_FONDS, F.ic_requis(F.IR_REF, F.RYTHME_FONDS), "hm7",
           "une infrastructure : " + _num(F.RYTHME_FONDS, 0)
           + " décisions par an", r=4.0)
    p1.tag(F.ic_requis(F.IR_REF, F.OPERATEUR_DECISIONS), "un opérateur")
    p1.tag(F.ic_requis(F.IR_REF, F.RYTHME_FONDS), "une infrastructure")

    p2 = Panel(b, PX2, 92, PW, 214, title="La même exigence, en taux",
               readout="part des décisions gagnantes")
    p2.domain(300.0, 4e7, 0.499, 0.56, xlog=True)
    p2.frame()
    p2.grid_y(_ticks(0.50, 0.56, 0.02), lambda v: _pct(v, 0), dx=40.0)
    p2.grid_x([1e3, 1e5, 1e7], lambda v: _num(v, 0))
    pts = []
    n = 300.0
    while n <= 4e7:
        pts.append((n, F.taux_de_ic(F.ic_requis(F.IR_REF, n))))
        n *= 1.25
    p2.path(pts, "hm6", tip="taux requis à IR = " + _num(F.IR_REF, 0))
    p2.hline(F.TAUX_INVRAISEMBLABLE, "lvl")
    p2.hline(0.5, "lvl")
    n_seuil = F.seuil_de_credibilite()
    p2.dot(n_seuil, F.TAUX_INVRAISEMBLABLE, "hm7",
           "bascule : " + _num(n_seuil, 0) + " décisions par an", r=4.4)
    p2.label(4e5, F.TAUX_INVRAISEMBLABLE, "seuil de vraisemblance",
             dx=0, dy=-7)
    p2.label(4e5, 0.5, "le hasard", dx=0, dy=-7)

    b.legend(PX1, 336.0,
             [("hm3", "IR = 1", "3 3"), ("hm7", "IR = 2"),
              ("hm5", "IR = 4", "7 3")],
             step=96.0, kind="line")
    b.annotation(0.0, 358.0,
                 "la bascule tombe à " + _num(n_seuil, 0) + " décisions par "
                 "an, soit " + _num(n_seuil / F.SESSIONS_PAR_AN, 1)
                 + " par séance")
    b.annotation(0.0, 374.0,
                 "au-dessous, revendiquer ce ratio revient à revendiquer un "
                 "avantage que personne d'autre n'aurait remarqué")

    _source(b, "Relation de Grinold, tracée sans aucune donnée. La conversion "
               "en taux de réussite est exacte pour un pari binaire "
               "symétrique, où l'IC vaut deux fois l'écart au hasard. Le "
               "seuil de vraisemblance de "
            + _pct(F.TAUX_INVRAISEMBLABLE, 0) + " est déclaré avant les "
              "mesures et il n'est pas une opinion sur la difficulté du "
              "métier : c'est le niveau au-dessus duquel un avantage sur un "
              "marché liquide serait visible de tous, donc compété. Ce que la "
              "planche établit est un ordre de grandeur, et il est brutal : "
              "au rythme d'un opérateur discrétionnaire, la loi fondamentale "
              "exige un taux de réussite qu'aucun marché ne laisse traîner.")
    return b.render("Finesse de prevision et taux de reussite exiges par la "
                    "loi fondamentale, selon le nombre de decisions.")


def fig_fds_exigence() -> str:
    """L'exigence par décision, sur tout le plan.

    Le relief tombe d'un facteur mille de l'arête gauche à l'arête droite. Ce
    qu'il montre n'est pas que l'ampleur rende la preuve plus rapide — la
    partie XVI a établi le contraire — mais qu'elle rende l'hypothèse
    plausible : un écart au hasard de deux centièmes de point ne se conteste
    pas, un écart de quatre points et demi se conteste tout seul.
    """
    z = F.surface_exigence()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Loi fondamentale · le relief de l'exigence",
               "Ce qu'il faut avoir raison de plus que le hasard",
               "hauteur : points de taux")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(ir, 1) for ir in F.SURF_IR],
             col_labels=[_num(n, 0) for n in F.SURF_N],
             z_ticks=[(t, _num(t, 0) + " pt") for t in (0.0, 3.0, 6.0, 9.0)],
             tip="{v:.3f} point de taux", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : ratio d'information visé · arête droite : "
                 "décisions par an")
    b.annotation(0.0, 424.0,
                 "le versant s'effondre le long de l'ampleur : "
                 + _num(zhi, 1) + " point au fond, " + _num(zlo, 2)
                 + " au bord")
    b.annotation(0.0, 440.0,
                 "le ratio visé, lui, ne fait que quadrupler l'exigence d'une "
                 "arête à l'autre")

    _source(b, "Hauteur en points de pourcentage de taux de réussite, "
               "au-dessus du hasard. Les deux axes n'agissent pas du tout de "
               "la même façon, et c'est le fait de la planche : viser deux "
               "fois mieux double l'exigence, prendre cent fois plus de "
               "décisions la divise par dix. Un programme qui ne peut pas "
               "augmenter son nombre de décisions n'a donc qu'un levier, et "
               "c'est le plus cher des deux. Le relief ne dit rien de la "
               "durée nécessaire pour établir quoi que ce soit : elle ne "
               "dépend ni de l'un ni de l'autre axe, seulement du ratio visé.")
    return b.render("Surface de l exigence par decision sur le plan du ratio "
                    "d information et du nombre de decisions annuelles.")


def fig_fds_preuve() -> str:
    """Le même avantage, indémontrable pour l'un, acquis pour l'autre.

    La courbe est la même dans les deux cadres — le nombre de décisions
    requises pour distinguer un taux du hasard — et seule l'échelle de droite
    change, qui le convertit en années au rythme de chacun.

    Le taux qu'une publication rapporte y est posé. À deux décisions par
    séance il demande plus qu'une carrière ; à dix mille, moins d'une semaine.
    """
    b = _plate(446, "Le prix de la preuve · deux dénominateurs",
               "Ce qu'il faut de décisions, et ce que cela fait en années",
               "seuil " + _pct(F.ALPHA, 0) + ", puissance "
               + _pct(F.PUISSANCE, 0))

    taux = [0.5005 + 0.0005 * i for i in range(280)]

    p1 = Panel(b, PX1, 92, PW, 214, title="Décisions pour établir le taux",
               readout="contre le hasard")
    p1.domain(0.5, 0.64, 30.0, 4e6, ylog=True)
    p1.frame()
    p1.grid_y([1e2, 1e3, 1e4, 1e5, 1e6], lambda v: _num(v, 0), dx=46.0)
    p1.grid_x(_ticks(0.50, 0.64, 0.04), lambda v: _pct(v, 0))
    p1.path([(p, F.decisions_pour_taux(p)) for p in taux], "hm6",
            tip="décisions requises")
    pub = F.ANNONCES["taux"]
    p1.dot(pub, F.decisions_pour_taux(pub), "hm7",
           "taux rapporté : " + _pct(pub, 2), r=4.4)
    p1.label(pub, F.decisions_pour_taux(pub), "le taux rapporté", dx=9, dy=-4)
    exi = F.taux_de_ic(F.ic_requis(F.IR_REF, F.OPERATEUR_DECISIONS))
    p1.dot(exi, F.decisions_pour_taux(exi), "hm3",
           "exigé d'un opérateur à IR = " + _num(F.IR_REF, 0) + " : "
           + _pct(exi, 2), r=4.0)
    p1.label(exi, F.decisions_pour_taux(exi), "exigé d'un opérateur",
             dx=9, dy=4)

    p2 = Panel(b, PX2, 92, PW, 214, title="Le même axe, en années",
               readout="au rythme de chacun")
    p2.domain(0.5, 0.64, 3e-4, 3000.0, ylog=True)
    p2.frame()
    p2.grid_y([1e-3, 1e-1, 1e1, 1e3],
              lambda v: _num(v, 3) if v < 1.0 else _num(v, 0), dx=52.0)
    p2.grid_x(_ticks(0.50, 0.64, 0.04), lambda v: _pct(v, 0))
    for rythme, cls, dash, nom in (
            (F.OPERATEUR_DECISIONS, "hm7", "", "un opérateur"),
            (F.RYTHME_FONDS, "hm3", "5 3", "une infrastructure")):
        p2.path([(p, F.decisions_pour_taux(p) / rythme) for p in taux], cls,
                dash=dash,
                tip=nom + " : " + _num(rythme, 0) + " décisions par an")
    p2.hline(1.0, "lvl")
    p2.label(0.635, 1.0, "un an", dx=0, dy=-7, anchor="end")
    p2.hline(40.0, "lvl")
    p2.label(0.635, 40.0, "une carrière", dx=0, dy=-7, anchor="end")
    p2.vline(pub, "lvl")

    b.legend(PX2, 336.0,
             [("hm7", "un opérateur"),
              ("hm3", "une infrastructure", "5 3")],
             step=150.0, kind="line")
    b.annotation(0.0, 358.0,
                 "le trait vertical du cadre de droite est le taux rapporté :")
    b.annotation(0.0, 374.0,
                 "il coupe une courbe au-dessus d'une carrière et l'autre "
                 "au-dessous d'une semaine")

    _source(b, "Nombre de décisions requis pour distinguer un taux de "
               "réussite du hasard, par le test du rapport de vraisemblance "
               "sur la table de contingence. Rien dans ce calcul ne dépend de "
               "la géométrie, du Sharpe ou de la loi des rendements : c'est "
               "de l'information pure, et c'est ce qui le rend opposable. Le "
               "taux rapporté par la publication demande "
            + _num(F.decisions_pour_taux(pub), 0) + " décisions, soit "
            + _num(F.decisions_pour_taux(pub) / F.OPERATEUR_DECISIONS, 0)
            + " ans à deux décisions par séance et "
            + _num(365.0 * F.decisions_pour_taux(pub) / F.RYTHME_FONDS, 1)
            + " jours à dix mille. L'avantage n'est pas différent : le "
              "dénominateur l'est.")
    return b.render("Decisions et annees requises pour etablir un taux de "
                    "reussite, aux deux rythmes de decision.")


# ---------------------------------------------------------------------------
# II. Le panier de lectures
# ---------------------------------------------------------------------------


def fig_fds_combinaison() -> str:
    """Ce qu'un panier de lectures ajoute, et où il s'arrête.

    La courbe du haut est la promesse habituelle — la racine du nombre de
    lectures — et elle n'existe qu'à corrélation exactement nulle. Les trois
    autres saturent, chacune sur son plafond, et le plafond ne dépend que de
    la corrélation.

    Les quinze lectures du catalogue y sont posées : elles valent un peu plus
    de deux lectures, pas quinze, et pas non plus la racine de quinze.
    """
    b = _plate(462, "Le panier de lectures · le plafond",
               "Ce que la corrélation retire au nombre",
               "gain rapporté à une lecture seule")

    p = Panel(b, 74.0, 92, W - 148.0, 214, title="Gain d'un panier",
              readout="IC du panier sur IC d'une lecture")
    p.domain(1.0, 60.0, 1.0, 8.0, xlog=True)
    p.frame()
    p.grid_y(_ticks(1.0, 8.0, 1.0), lambda v: _num(v, 0), dx=26.0)
    p.grid_x([1, 2, 3, 5, 8, 15, 30, 60], lambda v: _num(v, 0),
             label="nombre de lectures")
    styles = (("hm1", "1 3"), ("hm3", "7 3"), ("hm7", ""), ("hm5", "3 3"))
    for (rho, (cls, dash)) in zip(F.RHO_GRID, styles):
        pts = [(k, F.ic_combine(k, rho))
               for k in range(1, 61)]
        p.path(pts, cls, dash=dash, tip="ρ = " + _num(rho, 2))
        if rho > 0.0:
            p.hline(F.plafond(rho), "lvl")
    for rho in F.RHO_GRID[1:]:
        p.tag(F.plafond(rho), "plafond ρ = " + _num(rho, 2))
    p.dot(15, F.ic_combine(15, F.RHO_REF), "hm7",
          "quinze lectures à ρ = " + _num(F.RHO_REF, 2) + " : "
          + _num(F.ic_combine(15, F.RHO_REF), 2), r=4.4)
    p.label(15, 1.85, "le catalogue", dx=0, dy=0, anchor="middle")

    b.legend(74.0, 352.0,
             [("hm1", "ρ = 0,00", "1 3"), ("hm3", "0,05", "7 3"),
              ("hm7", "0,15"), ("hm5", "0,35", "3 3")],
             step=132.0, kind="line")
    b.annotation(0.0, 374.0,
                 "la promesse en racine de k n'existe qu'à corrélation "
                 "exactement nulle,")
    b.annotation(0.0, 390.0,
                 "ce qui n'arrive jamais entre deux lectures d'un même flux")

    _source(b, "Gain d'IC d'un panier de lectures de qualité égale et de "
               "corrélation moyenne donnée. Le plafond vaut l'inverse de la "
               "racine de la corrélation, et il est atteint à quelques unités "
               "près bien avant que le panier ne soit plein : à "
            + _num(F.RHO_REF, 2) + ", " + _num(F.k_pour_fraction(F.RHO_REF), 0)
            + " lectures en captent déjà neuf dixièmes. Les suivantes "
              "n'ajoutent rien à l'IC et ajoutent tout au budget de "
              "configurations à déflater — c'est la comptabilité de la partie "
              "XVI, et elle joue ici contre le collectionneur de lectures.")
    return b.render("Gain d un panier de lectures selon leur nombre et leur "
                    "correlation, avec les plafonds.")


def fig_fds_panier() -> str:
    """Le gain d'un panier, sur tout le plan.

    Le relief a une arête et un plateau. L'arête est le bord où la corrélation
    s'annule, et c'est le seul endroit où ajouter des lectures paie encore. Le
    plateau est tout le reste, et il est bas.
    """
    z = F.surface_panier()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Le panier de lectures · le relief",
               "Ce qu'ajoute une lecture de plus, selon la corrélation",
               "hauteur : gain sur une lecture seule")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(k, 0) for k in F.SURF_K],
             col_labels=[_num(r, 2) for r in F.SURF_RHO],
             z_ticks=[(t, _num(t, 0) + " ×") for t in (1.0, 3.0, 5.0)],
             tip="{v:.2f} fois une lecture", zero=1.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : nombre de lectures · arête droite : "
                 "corrélation moyenne entre deux d'entre elles")
    b.annotation(0.0, 424.0,
                 "le sol est posé à un : c'est la lecture unique, et tout ce "
                 "qui ne dépasse pas ne sert à rien")
    b.annotation(0.0, 440.0,
                 "à corrélation " + _num(F.SURF_RHO[-1], 2) + ", soixante "
                 "lectures valent " + _num(F.ic_combine(60, F.SURF_RHO[-1]), 2)
                 + " fois une seule")

    _source(b, "Le versant abrupt du bord gauche est la promesse en racine du "
               "nombre ; elle ne survit qu'à corrélation presque nulle. Dès "
               "qu'on avance d'un pas sur l'autre axe, la surface s'effondre "
               "sur un plateau dont la hauteur ne dépend plus que de la "
               "corrélation. C'est le même genre de frontière que la "
               "transition de la partie XVI, et la conséquence pratique est "
               "la même : ce qui limite un opérateur n'est pas le nombre de "
               "choses qu'il regarde, c'est le fait qu'elles se ressemblent.")
    return b.render("Surface du gain d un panier sur le plan du nombre de "
                    "lectures et de leur correlation.")


# ---------------------------------------------------------------------------
# III. La capacité
# ---------------------------------------------------------------------------


def fig_fds_capacite() -> str:
    """Ce que la taille coûte, et où elle tue la géométrie.

    À gauche, la loi en racine : l'impact d'un ordre rapporté à la friction de
    base. Le croisement des deux courbes est le moment où la taille cesse
    d'être un détail comptable et devient le premier poste du budget.

    À droite, la conséquence sur le seuil de rentabilité, avec le domaine de
    dérive plausible posé dessus. La capacité de cette géométrie est le point
    où la courbe sort du domaine par le haut.
    """
    b = _plate(446, "La capacité · ce que la taille coûte",
               "L'impact croît en racine, et il finit par tout manger",
               "loi en racine, Y = " + _num(F.Y_IMPACT, 2))

    tailles = [1.0 * (1.35 ** i) for i in range(40)]
    tailles = [t for t in tailles if t <= 2e4]

    p1 = Panel(b, PX1, 92, PW, 214, title="Impact contre friction de base",
               readout="points, aller-retour")
    p1.domain(1.0, 2e4, 0.0, 1.3, xlog=True)
    p1.frame()
    p1.grid_y(_ticks(0.0, 1.3, 0.4), lambda v: _num(v, 1), dx=30.0)
    p1.grid_x([1, 10, 100, 1000, 10000], lambda v: _num(v, 0),
              label="contrats")
    p1.path([(t, 2.0 * F.impact_racine(t)) for t in tailles], "hm7",
            tip="impact aller-retour")
    p1.path([(1.0, F.GEOM.friction_points), (2e4, F.GEOM.friction_points)],
            "hm3", dash="4 3", tip="friction de base")
    croise = F.VOLUME_JOUR * (F.GEOM.friction_points
                              / (2.0 * F.Y_IMPACT * F.SIGMA_JOUR)) ** 2
    p1.dot(croise, F.GEOM.friction_points, "hm7",
           "croisement : " + _num(croise, 0) + " contrats", r=4.2)
    p1.label(1.2, F.GEOM.friction_points, "friction de base", dx=0, dy=-8)
    p1.label(croise, F.GEOM.friction_points, "l'impact égale la friction",
             dx=-8, dy=17, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Le seuil, à la taille",
               readout="µ* en points par heure")
    p2.domain(1.0, 2e4, 0.3, 20.0, xlog=True, ylog=True)
    p2.frame()
    p2.grid_y([0.5, 1.0, 2.0, 5.0, 10.0, 20.0], lambda v: _num(v, 1), dx=32.0)
    p2.grid_x([1, 10, 100, 1000, 10000], lambda v: _num(v, 0),
              label="contrats")
    lo_d, hi_d = S.PLAUSIBLE_DRIFT_PER_HOUR
    p2.band_y(lo_d, hi_d)
    p2.path([(t, F.seuil_a_la_taille(t)) for t in tailles], "hm6",
            tip="seuil de rentabilité")
    cap = F.capacite()
    p2.dot(cap, F.seuil_a_la_taille(cap), "hm7",
           "capacité : " + _num(cap, 0) + " contrats", r=4.4)
    p2.label(1.2, hi_d, "domaine de dérive plausible", dx=0, dy=-8)
    p2.label(cap, F.seuil_a_la_taille(cap), "capacité", dx=-8, dy=14,
             anchor="end")

    b.annotation(0.0, 352.0,
                 "à un contrat, l'impact pèse "
                 + _num(100 * 2.0 * F.impact_racine(1.0)
                        / F.friction_a_la_taille(1.0), 0)
                 + " % de la friction ; la capacité de cette géométrie vaut "
                 + _num(cap, 0) + " contrats")
    b.annotation(0.0, 368.0,
                 "un opérateur seul travaille quatre ordres de grandeur "
                 "au-dessous, dans un régime où la taille est gratuite")

    _source(b, "Loi en racine de la taille, forme empirique la plus reproduite "
               "de la microstructure, avec un coefficient déclaré et balayé "
               "par la surface suivante. La capacité est définie ici comme la "
               "taille où le seuil de rentabilité sort du domaine de dérive "
               "plausible — non comme la taille où le programme cesse de "
               "gagner, ce qui dépendrait d'une dérive que personne ne "
               "connaît. C'est le seul axe du document où un opérateur seul "
               "est structurellement en avance sur une institution, et "
               "l'avance ne se gagne pas : elle se perd en grossissant.")
    return b.render("Impact de marche et seuil de rentabilite selon la taille "
                    "de la position, avec la capacite de la geometrie.")


def fig_fds_relief() -> str:
    """Le seuil sur le plan de la taille et de la largeur de stop.

    Deux versants, deux causes. Vers les grandes tailles, le seuil monte parce
    que l'impact gonfle la friction. Vers les stops serrés, il monte parce que
    le temps de marché s'effondre. Le coin du fond additionne les deux, et
    c'est exactement là que se tient l'opérateur qui a resserré son stop après
    avoir augmenté sa taille.
    """
    z = F.surface_capacite()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)
    hi_d = S.PLAUSIBLE_DRIFT_PER_HOUR[1]

    b = _plate(486, "La capacité · le relief",
               "Le seuil, quand la taille et la géométrie se composent",
               "hauteur : µ* en points par heure")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(q, 0) for q in F.SURF_TAILLE],
             col_labels=[_num(p, 3) for p in F.SURF_STOP],
             z_ticks=[(math.log10(t), _num(t, 1))
                      for t in (0.3, 3.0, 30.0)],
             tip="{v:.2f} pt/h", zero=zlo,
             tip_value=lambda v: 10.0 ** v)

    b.annotation(0.0, 408.0,
                 "arête gauche : taille en contrats · arête droite : largeur "
                 "de stop en pour-cent · hauteur logarithmique")
    b.annotation(0.0, 424.0,
                 "le domaine plausible s'arrête à " + _num(hi_d, 1)
                 + " point par heure : presque tout le relief est au-dessus")
    b.annotation(0.0, 440.0,
                 "les deux versants ont deux causes — l'impact d'un côté, "
                 "l'effondrement du temps de marché de l'autre")

    _source(b, "Hauteur logarithmique, et ce n'est pas une décoration : le "
               "seuil parcourt trois ordres et demi de grandeur sur cette "
               "boîte, et tracé brut le relief se réduirait à une aiguille au "
               "coin des stops serrés. Les graduations de l'échine et les "
               "infobulles restent en points par heure. Ce que la planche "
               "ajoute aux deux tables est la composition : un opérateur qui "
               "resserre son stop pour risquer moins et grossit sa taille "
               "pour gagner plus se déplace vers le coin du fond sur les deux "
               "axes à la fois, et le seuil qu'il doit franchir y est "
               "multiplié par plusieurs centaines.")
    return b.render("Surface du seuil de rentabilite sur le plan de la taille "
                    "de position et de la largeur de stop.")


# ---------------------------------------------------------------------------
# IV. L'exécution
# ---------------------------------------------------------------------------


def fig_fds_execution() -> str:
    """Le seul levier que l'opérateur contrôle entièrement.

    À gauche, trois conduites d'entrée et rien d'autre qui change : le seuil
    de rentabilité y varie plus que dans tout le reste du document. La barre
    claire est la dérive adverse qui reprendrait exactement le gain.

    À droite, ce qu'un ordre limite attend. Une limite posée au meilleur prix
    est presque toujours servie ; une limite posée loin ne l'est que les jours
    où le prix revient — c'est-à-dire pas ceux qui comptent.
    """
    b = _plate(462, "L'exécution · payer le spread ou l'encaisser",
               "Trois conduites d'entrée, une seule géométrie",
               "stop " + _num(F.STOP_PCT, 3) + " %, rapport "
               + _num(F.RR, 0))

    p1 = Panel(b, PX1, 92, PW, 214, title="Le seuil, par conduite",
               readout="points par heure")
    n = len(F.ENTREES)
    mus = [F.seuil_de_conduite(t) for _, t, _ in F.ENTREES]
    adv = [F.derive_adverse_annulante(t) for _, t, _ in F.ENTREES]
    p1.domain(0.0, max(mus) * 1.32, -0.5, n - 0.5)
    p1.frame()
    p1.grid_x(_ticks(0.0, max(mus) * 1.32, 0.2), lambda v: _num(v, 1))
    for i, (nom, ticks, _) in enumerate(F.ENTREES):
        y = n - 1 - i
        p1.hbar(y + 0.16, 0.0, mus[i], 12.0, "hm5",
                tip=nom + " : µ* = " + _num(mus[i], 3))
        p1.hbar(y - 0.16, 0.0, adv[i], 12.0, "hm2",
                tip="dérive adverse qui annule le gain : " + _num(adv[i], 3))
        p1.label(mus[i], y + 0.16, _num(mus[i], 3), dx=6, dy=4)
        p1.label(0.0, y + 0.40, nom.replace("Entrée ", ""), dx=3, dy=0)
        b.add('<text class="tk" x="68" y="%.1f" text-anchor="end">%s</text>'
              % (p1.sy(y) + 4.0, _signed(ticks, 1) + " tick"))
    lo_d = S.PLAUSIBLE_DRIFT_PER_HOUR[0]
    p1.vline(lo_d, "lvl")
    p1.label(lo_d, -0.42, "plancher plausible", dx=6, dy=4)

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce qu'un ordre limite attend",
               readout="part des ordres servis")
    p2.domain(0.4, 16.0, 0.0, 1.0, xlog=True)
    p2.frame()
    p2.grid_y(_ticks(0.0, 1.0, 0.25), lambda v: _pct(v, 0), dx=40.0)
    p2.grid_x([0.5, 1, 2, 4, 8, 16], lambda v: _num(v, 1),
              label="profondeur, en ticks")
    for w, cls, dash in zip(F.FENETRES_ATTENTE, ("hm2", "hm4", "hm6", "hm7"),
                            ("1 3", "7 3", "3 3", "")):
        p2.path([(d, F.taux_remplissage(d, w)) for d in
                 [0.4 * (1.12 ** i) for i in range(35)]], cls, dash=dash,
                tip=_num(w, 0) + " minutes d'attente")

    b.legend(PX2, 352.0,
             [("hm2", "1 min", "1 3"), ("hm4", "5 min", "7 3"),
              ("hm6", "15 min", "3 3"), ("hm7", "60 min")],
             step=72.0, kind="line")
    b.legend(PX1, 352.0,
             [("hm5", "seuil µ*"), ("hm2", "dérive adverse qui l'annule")],
             step=112.0)
    b.annotation(0.0, 382.0,
                 "changer d'entrée, et rien d'autre, divise le seuil par "
                 + _num(mus[0] / mus[-1], 2))
    b.annotation(0.0, 398.0,
                 "la dérive adverse qui reprendrait ce gain vaut "
                 + _num(adv[-1], 2) + " point par heure, au-dessous du "
                 "plancher du domaine plausible")

    _source(b, "Sous prix sans dérive, "
              "l'économie d'une entrée passive est intégrale — un ordre "
              "rempli parce que le prix est venu le chercher n'apprend rien "
              "sur la suite, la propriété de Markov forte l'interdit. Ce qui "
              "peut la reprendre est un flux informé, que la loi nulle ne "
              "contient pas et qu'un relevé ordinaire ne voit pas. Le seul "
              "protocole qui le mesure est écrit d'avance : comparer les "
              "issues des ordres remplis à celles des ordres annulés.")
    return b.render("Seuil de rentabilite par conduite d entree et taux de "
                    "remplissage d un ordre limite.")


def fig_fds_adverse() -> str:
    """Ce que l'exécution passive rapporte, et ce qui peut le reprendre.

    Le sol est posé à zéro et la ligne de niveau zéro est la seule chose à
    regarder : elle dit, pour chaque taux de remplissage, à quelle dérive
    adverse la conduite bascule. Le relief est presque plat le long de
    l'arête du remplissage et raide le long de celle de la sélection adverse,
    ce qui range les deux risques dans le bon ordre.
    """
    z = F.surface_execution()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "L'exécution · ce qui peut la reprendre",
               "Le gain annuel, remplissage contre sélection adverse",
               "hauteur : points par an")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_pct(r, 0) for r in F.SURF_REMPLI],
             col_labels=[_num(d, 2) for d in F.SURF_ADVERSE],
             z_ticks=[(t, _signed(t, 0)) for t in (-150.0, 0.0, 200.0, 400.0)],
             tip="{v:+.0f} points par an", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : part des ordres servis · arête droite : "
                 "dérive adverse conditionnelle, en points par heure")
    b.annotation(0.0, 424.0,
                 "dérive déclarée : " + _num(F.DERIVE_DECLAREE, 1)
                 + " point par heure, le milieu du domaine plausible, posée "
                 "avant la mesure")
    b.annotation(0.0, 440.0,
                 "le relief bascule sous le sol bien avant que la sélection "
                 "adverse n'égale la dérive : la friction reste due")

    _source(b, "Arithmétique de Wald, sans simulation : la dérive nette "
               "multipliée par le temps de marché, moins la friction, le tout "
               "multiplié par le nombre d'occasions servies. Les deux axes ne "
               "coûtent pas la même chose et c'est le fait de la planche. "
               "Perdre la moitié des remplissages divise le gain par deux ; "
               "une sélection adverse de quelques dixièmes de point par heure "
               "le fait passer sous zéro. Ce n'est donc pas le taux de "
               "remplissage qu'il faut surveiller, c'est ce qui arrive après "
               "les remplissages — et c'est la mesure que personne ne fait.")
    return b.render("Surface du gain annuel d une entree passive sur le plan "
                    "du taux de remplissage et de la selection adverse.")


# ---------------------------------------------------------------------------
# V. Le décompte
# ---------------------------------------------------------------------------


def fig_fds_transfert() -> str:
    """Ce qu'un opérateur seul peut prendre, et ce qu'il ne peut pas.

    Cinq pratiques, rangées par ce qu'elles déplacent. La barre claire est la
    seule qui ne transfère pas, et elle échoue sur un critère que ni le talent
    ni le travail ne changent : le nombre de décisions.
    """
    ps = F.pratiques()
    b = _plate(416, "Le décompte · ce qui transfère",
               "Cinq pratiques, et celle qui reste hors de portée",
               "règle de verdict : " + _pct(F.SEUIL_TRANSFERT, 0))

    p = Panel(b, 214.0, 92, W - 254.0, 176,
              title="Facteur mesuré sur le terme touché",
              readout="échelle logarithmique")
    haut = max(x.effet for x in ps) * 1.6
    p.domain(0.9, haut, -0.5, len(ps) - 0.5, xlog=True)
    p.frame()
    p.grid_x([1, 2, 5, 10, 20, 50], lambda v: _num(v, 0) + " ×")
    for i, x in enumerate(ps):
        y = len(ps) - 1 - i
        p.hbar(y, 0.9, x.effet, 17.0, "hm5" if x.transfere else "hm1",
               tip=x.nom + " : facteur " + _num(x.effet, 2))
        p.label(x.effet, y, _num(x.effet, 2) + " ×", dx=7, dy=4)
        b.add('<text class="lg" x="206" y="%.1f" text-anchor="end">%s</text>'
              % (p.sy(y) - 2.0, x.nom))
        b.add('<text class="tk" x="206" y="%.1f" text-anchor="end">%s</text>'
              % (p.sy(y) + 11.0,
                 "à sa portée" if x.accessible else "hors de portée"))

    b.legend(74.0, 300.0,
             [("hm5", "transfère à un opérateur seul"),
              ("hm1", "reste hors de portée")],
             step=280.0)
    b.annotation(0.0, 324.0,
                 "les quatre pratiques qui transfèrent agissent sur la "
                 "friction, la taille ou le plafond d'un panier")
    b.annotation(0.0, 340.0, "aucune n'agit sur la direction")

    _source(b, "Chaque facteur est relu des sections précédentes, jamais "
               "réécrit ici : corriger une mesure en amont change la barre et "
               "le verdict sans intervention. Le verdict combine deux "
               "conditions déclarées avant les mesures — la pratique doit "
               "être à la portée d'un opérateur à "
            + _num(F.OPERATEUR_DECISIONS, 0) + " décisions par an et un "
              "contrat, et déplacer son terme d'au moins "
            + _pct(F.SEUIL_TRANSFERT, 0) + ". L'échelle est logarithmique "
              "parce que les facteurs vont de deux à soixante-dix ; la "
              "longueur d'une barre ne se compare donc pas à celle d'une "
              "autre, seule sa position sur l'axe compte.")
    return b.render("Facteur mesure de chaque pratique et verdict de "
                    "transfert a un operateur seul.")


FIGURES = {
    "fdsampleur": fig_fds_ampleur,
    "fdsexigence": fig_fds_exigence,
    "fdspreuve": fig_fds_preuve,
    "fdscombinaison": fig_fds_combinaison,
    "fdspanier": fig_fds_panier,
    "fdscapacite": fig_fds_capacite,
    "fdsrelief": fig_fds_relief,
    "fdsexecution": fig_fds_execution,
    "fdsadverse": fig_fds_adverse,
    "fdstransfert": fig_fds_transfert,
}


def render_all() -> dict[str, str]:
    return {k: f() for k, f in FIGURES.items()}
