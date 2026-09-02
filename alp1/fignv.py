"""Les planches de la largeur d'un niveau.

Dix planches, six à plat et quatre en relief. Aucune ne montre un niveau qui
marche : toutes montrent ce qu'un niveau doit battre, et la place qu'il occupe.

L'ordre suit celui de la partie. Le témoin d'abord, parce que c'est la seule
chose contre laquelle un niveau se mesure. La définition ensuite, parce que
c'est là que la statistique publiée se fabrique. Puis l'exigence, puis la
largeur, puis ce que la largeur force. L'identité gamma-thêta ferme la
mécanique, et le niveau de bascule ferme la partie sur ce que la
reconstruction jette.
"""

from __future__ import annotations

import math

from . import niveaux as V
from . import quant as q
from . import seuil
from .figdisc import W, _plate, _source, _surface
from .figterm import Board, Panel, _num, _signed


PW = (W - 74.0) / 2.0 - 30.0
PX1 = 74.0
PX2 = 74.0 + (W - 74.0) / 2.0


def _pct(v: float, nd: int = 0) -> str:
    return _num(100.0 * v, nd) + " %"


def _ticks(lo: float, hi: float, pas: float) -> list[float]:
    out, v = [], math.ceil(lo / pas) * pas
    while v <= hi + 1e-12:
        out.append(round(v, 10))
        v += pas
    return out


_EXPOSANTS = "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079"


def _dec(v: float) -> str:
    """Une décade en puissance de dix, pour une gouttière étroite.

    « 1 000 000 000 » mesure treize glyphes et déborde de la marge d'axe,
    jusque dans le cadre voisin ; la puissance en mesure trois.
    """
    k = int(round(math.log10(v)))
    return "10" + "".join(_EXPOSANTS[int(c)] for c in str(abs(k)))


def _echine(zlo: float, zhi: float, mini: int = 3,
            maxi: int = 4) -> list[float]:
    """Les graduations d'une échine, déduites du relief qu'elle gradue.

    Même règle que la partie XVIII, et pour les mêmes deux raisons : une
    graduation hors domaine est ramenée au sol par la projection, où elle se
    lit comme une valeur du sol ; et une échine dont la dernière graduation
    tombe loin sous le sommet ne gradue plus la moitié haute du relief.
    """
    candidats: list[list[float]] = []
    for k in range(-6, 9):
        for m in (1.0, 2.0, 2.5, 5.0):
            pas = m * 10.0 ** k
            if (zhi - zlo) / pas > maxi + 1:
                continue
            t = _ticks(zlo, zhi, pas)
            if t:
                candidats.append(t)
    if not candidats:
        return []
    vises = [t for t in candidats if mini <= len(t) <= maxi]
    return min(vises or candidats, key=lambda t: (zhi - t[-1], -len(t)))


# ---------------------------------------------------------------------------
# I. Le témoin
# ---------------------------------------------------------------------------


def fig_nv_temoin() -> str:
    """Ce que la seule distance rend, avant qu'aucun niveau n'existe.

    À gauche, le taux de touche : c'est une fonction de la distance et de
    rien d'autre, et toute statistique de niveau qui ne la publie pas confond
    la fréquence d'un motif avec sa portée.

    À droite, la grandeur qui décide : le taux de réussite d'un trade pris sur
    le niveau. Il est plat. Il ne bouge ni avec la distance, ni avec ce que le
    niveau prétend marquer.
    """
    b = _plate(494, "Niveaux · le témoin apparié",
               "Ce que la distance rend, sans aucun niveau",
               "prix sans dérive")

    ds = [0.05 + 0.01 * i for i in range(171)]

    p1 = Panel(b, PX1, 92, PW, 214, title="Touché avant la clôture",
               readout="probabilité")
    p1.domain(0.05, 1.80, 0.0, 1.0)
    p1.frame()
    p1.grid_y(_ticks(0.0, 1.0, 0.25), lambda v: _num(v, 2), dx=32.0)
    p1.grid_x(_ticks(0.25, 1.75, 0.5), lambda v: _num(v, 2),
              label="distance, en sigma de séance")
    p1.path([(d, V.taux_de_touche(d * V.SIGMA_SEANCE)) for d in ds], "hm6",
            tip="principe de reflexion")
    for k in (0.5, 1.0):
        y = V.taux_de_touche(k * V.SIGMA_SEANCE)
        p1.dot(k, y, "hm7", _num(k, 1) + " sigma : " + _pct(y, 1), r=4.0)
        p1.label(k, y, _pct(y, 0), dx=8, dy=-7)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Ce que le niveau doit battre", readout="probabilité")
    plat = V.taux_de_reussite_ferme(q.STOP_PTS, q.RR_REF * q.STOP_PTS)
    g0 = seuil.geometry(0.010)
    g1 = seuil.geometry(0.150)
    exige0 = plat + V.exces_requis(g0.friction_ratio)
    exige1 = plat + V.exces_requis(g1.friction_ratio)
    p2.domain(0.05, 1.80, 0.040, 0.080)
    p2.frame()
    p2.grid_y(_ticks(0.040, 0.080, 0.010), lambda v: _num(v, 3), dx=38.0)
    p2.grid_x(_ticks(0.25, 1.75, 0.5), lambda v: _num(v, 2),
              label="distance, en sigma de séance")
    p2.path([(d, plat) for d in ds], "hm3",
            tip="taux du temoin, sous prix sans derive")
    p2.path([(d, exige0) for d in ds], "hm6",
            tip="taux exige a la geometrie declaree")
    p2.path([(d, exige1) for d in ds], "hm5", dash="5 3",
            tip="taux exige au stop elargi")
    # L'ecart se mesure au lieu de se laver : un rectangle plein sur les deux
    # tiers du cadre ne se lit plus comme une bande, il se lit comme le fond.
    p2.vbar(1.45, plat, exige0, 9.0, "hm7",
            tip="excès requis : " + _num(100 * (exige0 - plat), 2)
                + " points de taux")
    p2.label(1.45, 0.5 * (plat + exige0),
             "+" + _num(100 * (exige0 - plat), 2), dx=10, dy=4)
    p2.label(0.10, plat, "témoin, " + _pct(plat, 2), dx=0, dy=13)
    p2.label(0.10, exige0, "exigé au stop déclaré, " + _pct(exige0, 2),
             dx=0, dy=-8)
    p2.label(0.10, exige1, "exigé au stop élargi", dx=0, dy=-8)

    b.annotation(0.0, 352.0,
                 "à gauche, la distance décide de tout ; à droite, elle ne "
                 "décide de rien")
    b.annotation(0.0, 368.0,
                 "le témoin vaut " + _pct(plat, 2) + " à toute distance")
    b.annotation(0.0, 384.0,
                 "la barre verticale est ce qu'un niveau doit y ajouter "
                 "pour payer sa seule friction, à la géométrie déclarée")
    b.annotation(0.0, 400.0,
                 "un niveau ne se juge donc que contre un témoin placé à la "
                 "même distance de l'ouverture")

    _source(b, "Les deux cadres sont mesurés sur un prix sans dérive, et "
               "aucun niveau n'y figure. Celui de gauche est le principe de "
               "réflexion : un niveau proche est presque toujours touché, un "
               "niveau lointain presque jamais, et cela seul suffit à "
               "fabriquer des fréquences très différentes selon l'endroit où "
               "on place la ligne. Celui de droite est la grandeur qui décide "
               "d'une décision, et il est plat. Toute la question d'une "
               "méthode de niveaux tient dans l'écart entre sa courbe et "
               "cette droite — un écart que le guide d'options extérieur a "
               "cherché sur plusieurs années de séances, avec ce protocole, "
               "sans le trouver.")
    return b.render("Taux de touche contre distance, et taux de reussite du "
                    "trade pris sur le niveau, qui reste constant.")


def fig_nv_definition() -> str:
    """Le taux de tenue d'un niveau qui n'existe pas.

    La statistique publiée d'un niveau dépend entièrement de la définition du
    retournement, et la définition est presque toujours asymétrique. La courbe
    est `e/(r+e)` ; les cinq définitions déclarées y sont posées.
    """
    b = _plate(494, "Niveaux · la définition fabrique le taux",
               "Le taux de tenue d'un niveau qui n'existe pas",
               "prix sans dérive")

    # La courbe couvre le domaine : arretee a quatre quand le cadre va a
    # vingt, elle laissait le dernier point flotter sans rien sous lui.
    rs = [0.2 * (1.06 ** i) for i in range(80)]
    rs = [x for x in rs if x <= 20.0]

    p1 = Panel(b, PX1, 92, PW, 214, title="Taux de tenue contre asymétrie",
               readout="probabilité")
    p1.domain(0.2, 20.0, 0.0, 1.0, xlog=True)
    p1.frame()
    p1.grid_y(_ticks(0.0, 1.0, 0.25), lambda v: _num(v, 2), dx=32.0)
    p1.grid_x([0.25, 0.5, 1, 2, 4, 8, 16], lambda v: _num(v, 2),
              label="extension exigée sur recul exigé")
    p1.hline(0.5, "lvl")
    p1.path([(x, x / (1.0 + x)) for x in rs], "hm6",
            tip="e sur (r + e), forme fermee")
    for nom, r, e in V.DEFINITIONS:
        x = e / r
        if 0.2 <= x <= 20.0:
            p1.dot(x, V.taux_de_tenue_ferme(r, e), "hm7",
                   nom + " : " + _pct(V.taux_de_tenue_ferme(r, e), 1), r=4.2)
    p1.label(0.22, 0.5, "un demi", dx=0, dy=-8)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Les cinq définitions déclarées", readout="taux nul")
    n = len(V.DEFINITIONS)
    p2.domain(0.0, 1.0, -0.6, n - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, 1.0, 0.25), lambda v: _num(v, 2))
    p2.vline(0.5, "lvl")
    for i, (nom, r, e) in enumerate(V.DEFINITIONS):
        y = n - 1 - i
        t = V.taux_de_tenue_ferme(r, e)
        p2.hbar(y, 0.0, t, 13.0, "hm5",
                tip=nom + " : " + _pct(t, 1))
        p2.label(t, y, _pct(t, 1), dx=6, dy=4)
        p2.label(0.0, y + 0.34,
                 _num(r, 2) + " contre " + _num(e, 2), dx=4, dy=0)

    b.annotation(0.0, 352.0,
                 "recul exigé contre extension exigée, en points, sous le "
                 "libellé de chaque barre")
    b.annotation(0.0, 368.0,
                 "un recul d'un tick avant une extension de quatre points "
                 "rend "
                 + _pct(V.taux_de_tenue_ferme(0.25, 4.0), 0)
                 + " de tenue sur du bruit pur")
    b.annotation(0.0, 384.0,
                 "une statistique de niveau qui ne publie pas ses deux "
                 "distances ne publie rien")

    _source(b, "Le taux auquel un niveau tient vaut exactement le rapport de "
               "l'extension exigée à la somme des deux distances, par arrêt "
               "optionnel, et il dépasse un demi dès que l'extension exigée "
               "dépasse le recul. C'est pour cette raison que toute méthode "
               "de niveaux publie de bons taux : le retournement y est "
               "presque toujours défini de façon asymétrique, un petit recul "
               "suffisant à valider quand une grande extension est exigée "
               "pour invalider. Le résultat ne vient alors pas du niveau, il "
               "vient de la définition, et il se retrouve à l'identique sur "
               "un prix sans dérive.")
    return b.render("Taux de tenue contre asymetrie des deux distances, et "
                    "les cinq definitions declarees.")


# ---------------------------------------------------------------------------
# II. L'exigence
# ---------------------------------------------------------------------------


def fig_nv_exigence() -> str:
    """Ce qu'un niveau doit battre, et ce que la preuve coûte.

    Les deux courbes vont dans des sens opposés et c'est tout le propos :
    élargir le stop abaisse l'excès requis et fait exploser l'échantillon,
    parce que le second dépend du premier par un carré.
    """
    b = _plate(462, "Niveaux · l'exigence et son prix",
               "Ce qu'un niveau doit battre, et ce que la preuve coûte",
               "z = " + _num(V.FACTEUR, 3))

    pcts = [0.008 * (1.09 ** i) for i in range(60)]
    pcts = [p for p in pcts if p <= 0.45]

    p1 = Panel(b, PX1, 92, PW, 214, title="Excès requis sur le témoin",
               readout="points de taux")
    p1.domain(0.008, 0.45, 0.05, 4.0, xlog=True, ylog=True)
    p1.frame()
    p1.grid_y([0.1, 0.3, 1.0, 3.0], lambda v: _num(v, 1), dx=32.0)
    p1.grid_x([0.01, 0.03, 0.1, 0.3], lambda v: _num(v, 2),
              label="largeur du stop, en % du niveau")
    p1.path([(p, 100 * V.exces_requis(seuil.geometry(p).friction_ratio))
             for p in pcts], "hm6", tip="exces requis")
    for pct, cls in ((0.010, "hm7"), (0.150, "hm3")):
        g = seuil.geometry(pct)
        y = 100 * V.exces_requis(g.friction_ratio)
        p1.dot(pct, y, cls, _num(pct, 3) + " % : " + _num(y, 3)
               + " points de taux", r=4.4)

    p2 = Panel(b, PX2, 92, PW, 214, title="Touches requises pour l'établir",
               readout="décisions")
    p2.domain(0.008, 0.45, 100.0, 1e6, xlog=True, ylog=True)
    p2.frame()
    p2.grid_y([1e2, 1e3, 1e4, 1e5, 1e6],
              lambda v: _num(v, 0), dx=46.0)
    p2.grid_x([0.01, 0.03, 0.1, 0.3], lambda v: _num(v, 2),
              label="largeur du stop, en % du niveau")
    p2.path([(p, V.touches_requises(seuil.geometry(p).friction_ratio))
             for p in pcts], "hm6", tip="forme fermee du module")
    p2.path([(p, V.touches_par_information(seuil.geometry(p).friction_ratio))
             for p in pcts], "hm3", dash="5 3",
            tip="route d information de la partie IV")
    p2.hline(V.TOUCHES_CARRIERE, "lvl")
    p2.label(0.0085, V.TOUCHES_CARRIERE, "une carrière", dx=0, dy=-8)

    b.legend(PX1, 352.0,
             [("hm6", "forme fermée du module", ""),
              ("hm3", "route d'information de la partie IV", "5 3")],
             step=250.0, kind="line")
    b.annotation(0.0, 372.0,
                 "les deux routes s'accordent à "
                 + _num(100 * abs(V.touches_requises(
                     seuil.geometry(0.010).friction_ratio)
                     / V.touches_par_information(
                         seuil.geometry(0.010).friction_ratio) - 1.0), 0)
                 + " % à la géométrie déclarée et restent parallèles "
                 "au-delà")
    b.annotation(0.0, 388.0,
                 "élargir le stop divise l'exigence et multiplie "
                 "l'échantillon par son carré")

    _source(b, "L'excès qu'un niveau doit montrer sur son témoin vaut la "
               "friction relative divisée par un plus le rapport gain sur "
               "risque, et l'échantillon qui l'établit croît comme le carré "
               "de l'inverse de cette même friction relative. Les deux "
               "courbes sont donc la même quantité lue dans les deux sens, et "
               "le piège est là : rendre l'exigence petite est facile, il "
               "suffit d'élargir le stop, mais la preuve devient alors hors "
               "d'atteinte. La courbe tiretée est le budget d'information de "
               "la quatrième partie, calculé par une route entièrement "
               "différente ; leur accord est ce qui autorise à publier la "
               "forme fermée.")
    return b.render("Exces requis sur le temoin et touches requises pour "
                    "l etablir, contre la largeur du stop.")


def fig_nv_relief() -> str:
    """Le relief de la preuve, sur le stop et le rapport gain sur risque.

    Les deux axes agissent dans le même sens, et pour la même raison : un stop
    large et un objectif ambitieux rendent tous deux l'exigence petite, donc
    la preuve longue.
    """
    z = V.surface_exigence()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Niveaux · le relief de la preuve",
               "Ce que coûte une exigence qu'on a rendue petite",
               "hauteur : touches requises")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(p, 3) for p in V.SURF_STOP],
             col_labels=[_num(r, 0) for r in V.SURF_RR],
             z_ticks=[(math.log10(t), _num(t, 0))
                      for t in (1e2, 1e3, 1e4, 1e5, 1e6, 1e7)
                      if zlo <= math.log10(t) <= zhi],
             tip="{v:.0f} touches", zero=zlo,
             tip_value=lambda v: 10.0 ** v)

    b.annotation(0.0, 408.0,
                 "arête gauche : largeur du stop en % · arête droite : "
                 "rapport gain sur risque · hauteur logarithmique")
    b.annotation(0.0, 424.0,
                 "le coin du fond est celui des stops larges et des objectifs "
                 "ambitieux, là où l'exigence est la plus petite")
    b.annotation(0.0, 440.0,
                 "la géométrie déclarée du document est au coin opposé, et "
                 "c'est le seul endroit du relief où la preuve tient")

    _source(b, "Hauteur logarithmique, parce que la quantité parcourt cinq "
               "ordres de grandeur sur cette boîte ; les graduations et les "
               "infobulles restent en touches. Ce que le relief ajoute aux "
               "tables est la forme de la dépendance : les deux axes "
               "n'agissent pas par des mécanismes différents mais par le même "
               "— ils réduisent tous deux l'écart que le signal doit "
               "financer, et l'échantillon croît comme le carré de l'inverse "
               "de cet écart. Une méthode qui vise loin avec un stop large "
               "demande donc, mécaniquement, une carrière entière de données "
               "avant de pouvoir être distinguée de son témoin.")
    return b.render("Surface des touches requises sur le plan de la largeur "
                    "du stop et du rapport gain sur risque.")


# ---------------------------------------------------------------------------
# III. La largeur
# ---------------------------------------------------------------------------


def fig_nv_largeur() -> str:
    """La largeur de ce que chaque lecture marque, et les deux stops.

    L'échelle est logarithmique parce que les largeurs parcourent quatre
    ordres de grandeur, d'un tick à huit pour cent du niveau. Les deux traits
    verticaux sont les deux géométries du document.
    """
    lst = V.niveaux()
    a0 = q.STOP_PTS
    a1 = seuil.geometry(0.150).stop_points

    b = _plate(526, "Niveaux · la largeur de ce qu'on marque",
               "Un niveau a une largeur, et le stop doit la contenir",
               "échelle logarithmique")

    # Les noms passent dans une gouttiere : poses dans le cadre, ils etaient
    # barres par les deux traits verticaux, ce qu'aucun balayage ne voit.
    GX = 152.0
    p1 = Panel(b, GX, 92, W - GX, 240,
               title="Demi-largeur de chaque lecture", readout="points")
    n = len(lst)
    p1.domain(0.15, 1800.0, -0.7, n - 0.3, xlog=True)
    p1.frame()
    p1.grid_x([0.25, 1, 4, 16, 64, 256, 1024], lambda v: _num(v, 2),
              label="demi-largeur, en points du contrat")
    p1.vline(a0, "lvl")
    p1.vline(a1, "lvl")
    for i, x in enumerate(lst):
        y = n - 1 - i
        p1.hbar(y, 0.15, x.largeur_pts, 11.0, "hm5",
                tip=x.nom + " : " + _num(x.largeur_pts, 2) + " points")
        p1.label(x.largeur_pts, y, _num(x.largeur_pts, 2), dx=7, dy=4)
        p1.label(0.15, y, x.court, dx=-9, dy=4, anchor="end")
    p1.label(a0, -0.58, "stop déclaré", dx=-5, dy=0, anchor="end")
    p1.label(a1, -0.58, "stop élargi", dx=5, dy=0, anchor="start")

    b.annotation(0.0, 394.0,
                 "les deux traits verticaux sont les deux géométries du "
                 "document, " + _num(a0, 2) + " et " + _num(a1, 1) + " points")
    b.annotation(0.0, 410.0,
                 "toute barre qui dépasse un trait décrit un niveau plus "
                 "large que le stop qui prétend le trader")
    b.annotation(0.0, 426.0,
                 "la bande de gamma à un jour vaut "
                 + _num(V.largeur_gamma(1.0) / a0, 0) + " fois la géométrie "
                 "déclarée")

    _source(b, "Trois natures de largeur, et elles ne se corrigent pas de la "
               "même façon. Une largeur mécanique est une propriété du "
               "phénomène : la courbure d'une option vit à moins de "
               + _num(V.DEMI_HAUTEUR, 3) + " sigma racine de T du strike, et "
               "cela ne se négocie pas. Un réglage d'affichage est une "
               "largeur qu'on choisit sans le savoir, et la partie sur le "
               "profil de marché a déjà montré qu'il décide de la rareté de "
               "ce qu'on lit. Un choix d'ancrage est une largeur que la "
               "méthode fabrique elle-même : un retracement est un prix "
               "exact, mais le balancement qu'on retient ne l'est pas, et "
               "l'écart entre les balancements plausibles se mesure.")
    return b.render("Demi-largeur de chaque lecture en points, en echelle "
                    "logarithmique, contre les deux geometries du document.")


def fig_nv_invalidation() -> str:
    """Le relief de l'invalidation prématurée.

    La ligne de niveau à un demi est la diagonale où le stop vaut la largeur.
    Au-dessus, ce n'est plus le marché qui invalide.
    """
    z = V.surface_invalidation()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Niveaux · qui invalide, le marché ou la bande",
               "La probabilité que le stop parle avant le niveau",
               "hauteur : probabilité")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(w, 1) for w in V.SURF_LARGEUR],
             col_labels=[_num(a, 1) for a in V.SURF_STOP_PTS],
             z_ticks=[(t, _pct(t, 0)) for t in _echine(zlo, zhi)
                      if t > zlo + 0.12 * (zhi - zlo)],
             tip="{v:.1%} de chances que le stop parle en premier", zero=zlo)

    b.annotation(0.0, 408.0,
                 "arête gauche : demi-largeur du niveau · arête droite : "
                 "largeur du stop · les deux en points")
    b.annotation(0.0, 424.0,
                 "la ligne de niveau à un demi est la diagonale où le stop "
                 "vaut exactement la largeur du niveau")
    b.annotation(0.0, 440.0,
                 "au-dessus d'elle, l'invalidation appartient à la bande et "
                 "non au marché, et la géométrie déclarée y est partout")

    _source(b, "Depuis le niveau, sous prix sans dérive, la probabilité de "
               "toucher le stop avant de sortir de la bande vaut la largeur "
               "divisée par la somme des deux, par arrêt optionnel. Ce "
               "nombre-là est celui qu'aucune méthode de niveaux ne publie, "
               "et il décide pourtant de ce que le stop mesure. Quand il "
               "dépasse un demi, l'invalidation ne dit plus que le niveau a "
               "cédé : elle dit que le prix a bougé à l'intérieur d'une bande "
               "où il était de toute façon libre de bouger. La conclusion "
               "n'est pas qu'il faut renoncer au niveau, c'est que le stop "
               "doit valoir sa largeur — et la partie mesure ce que cela "
               "coûte.")
    return b.render("Surface de la probabilite d invalidation prematuree sur "
                    "le plan de la largeur du niveau et de celle du stop.")


def fig_nv_forcee() -> str:
    """Ce que la largeur force, et la fenêtre où les deux verdicts passent.

    Les deux courbes se croisent, et l'endroit où elles se croisent est le
    seul où une lecture de niveau peut être à la fois rentable et prouvable.
    """
    lst = V.niveaux()
    lo, hi = seuil.PLAUSIBLE_DRIFT_PER_HOUR

    b = _plate(494, "Niveaux · la géométrie que la largeur impose",
               "Rentable et prouvable ne se rencontrent presque jamais",
               _num(len(V.passe_les_deux()), 0) + " lecture sur "
               + _num(len(lst), 0))

    ws = [0.2 * (1.13 ** i) for i in range(60)]
    ws = [w for w in ws if w <= 700.0]

    p1 = Panel(b, PX1, 92, PW, 214, title="Seuil de rentabilité forcé",
               readout="points par heure")
    p1.domain(0.2, 700.0, 0.02, 60.0, xlog=True, ylog=True)
    p1.frame()
    p1.grid_y([0.03, 0.3, 3.0, 30.0], lambda v: _num(v, 2), dx=36.0)
    p1.grid_x([0.25, 1, 4, 16, 64, 256], lambda v: _num(v, 2),
              label="demi-largeur du niveau, en points")
    p1.band_y(lo, hi)
    p1.path([(w, V.geometrie_forcee(w).break_even_per_hour) for w in ws],
            "hm6", tip="mu etoile force par la largeur")
    # Le nom se pose la ou la donnee n'est pas : a gauche, la courbe traverse
    # la bande et barrait le mot.
    p1.label(650.0, hi, "domaine plausible", dx=0, dy=-8, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Touches requises",
               readout="décisions")
    p2.domain(0.2, 700.0, 10.0, 1e9, xlog=True, ylog=True)
    p2.frame()
    p2.grid_y([1e1, 1e3, 1e5, 1e7, 1e9], _dec, dx=30.0)
    p2.grid_x([0.25, 1, 4, 16, 64, 256], lambda v: _num(v, 2),
              label="demi-largeur du niveau, en points")
    p2.path([(w, V.touches_requises(V.geometrie_forcee(w).friction_ratio))
             for w in ws], "hm6", tip="touches requises")
    p2.hline(V.TOUCHES_CARRIERE, "lvl")
    p2.label(0.22, V.TOUCHES_CARRIERE, "une carrière", dx=0, dy=-8)
    for x in V.passe_les_deux():
        p2.dot(x.largeur_pts,
               V.touches_requises(
                   V.geometrie_forcee(x.largeur_pts).friction_ratio),
               "hm7", x.nom, r=4.4)

    b.annotation(0.0, 352.0,
                 "à gauche, la bande grisée est le domaine de dérive "
                 "plausible ; une lecture n'est rentable qu'en y entrant")
    b.annotation(0.0, 368.0,
                 "à droite, la ligne est une carrière de "
                 + _num(V.TOUCHES_CARRIERE, 0) + " occasions ; une lecture "
                 "n'est prouvable qu'en restant dessous")
    b.annotation(0.0, 384.0,
                 "les deux conditions se croisent sur "
                 + _num(len(V.passe_les_deux()), 0) + " des "
                 + _num(len(lst), 0) + " lectures du catalogue")

    _source(b, "Si l'invalidation doit appartenir au marché, le stop vaut la "
               "largeur du niveau, et la largeur choisit alors tout le reste. "
               "Les deux cadres montrent les deux conséquences, et elles vont "
               "en sens contraire. Un niveau large abaisse le seuil de "
               "rentabilité, parce qu'un stop large achète du temps de marché "
               "— c'est le levier que la partie sur le seuil a déjà établi. "
               "Mais il fait exploser l'échantillon, parce que l'exigence "
               "devient minuscule et que la preuve croît comme son carré. La "
               "fenêtre où les deux conditions tiennent ensemble est étroite, "
               "et le compte est recalculé à chaque construction du document.")
    return b.render("Seuil de rentabilite force par la largeur, et touches "
                    "requises pour l etablir, contre la demi-largeur.")


def fig_nv_bande() -> str:
    """Le relief de la bande de gamma, sur l'échéance et la volatilité.

    Les deux axes entrent par le même produit, et c'est le fait de la
    planche : une échéance courte et une volatilité basse font exactement la
    même chose au lieu qu'occupe la courbure.
    """
    z = V.surface_bande()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Niveaux · où vit la courbure",
               "Gamma n'est pas un nombre, c'est un lieu",
               "hauteur : demi-largeur en points")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(j, 1) for j in V.SURF_JOURS],
             col_labels=[_pct(v, 0) for v in V.SURF_VOL],
             z_ticks=[(t, _num(t, 0)) for t in _echine(zlo, zhi)],
             tip="{v:.0f} points de demi-largeur", zero=zlo)

    b.annotation(0.0, 408.0,
                 "arête gauche : jours à l'échéance · arête droite : "
                 "volatilité annuelle · hauteur : demi-largeur en points")
    b.annotation(0.0, 424.0,
                 "les deux axes n'entrent que par le produit sigma racine de "
                 "T, et c'est pourquoi le relief est une seule pente")
    b.annotation(0.0, 440.0,
                 "à deux heures de l'échéance la bande vaut encore "
                 + _num(V.largeur_gamma(2.0 / 24.0), 0) + " points, soit "
                 + _num(V.largeur_gamma(2.0 / 24.0) / q.STOP_PTS, 0)
                 + " fois la géométrie déclarée")

    _source(b, "La courbure d'une option tombe à la moitié de son sommet "
               "quand le log-moneyness atteint racine de deux fois le "
               "logarithme de deux, fois sigma racine de T. C'est la phrase "
               "que tout le monde répète — gamma vit à un écart-type du "
               "strike — rendue opposable, et elle porte une conséquence que "
               "personne n'en tire. Même au dernier jour, la bande où la "
               "courbure agit reste large de dizaines de points, c'est-à-dire "
               "de plusieurs fois la géométrie avec laquelle on prétend "
               "trader le niveau. Un strike n'est pas un prix, c'est une "
               "région.")
    return b.render("Surface de la demi-largeur de la bande de gamma sur le "
                    "plan de l echeance et de la volatilite.")


# ---------------------------------------------------------------------------
# IV. L'identité
# ---------------------------------------------------------------------------


def fig_nv_identite() -> str:
    """Les trois routes vers le mouvement d'équilibre.

    L'identité est plate — c'est le théorème. Les deux autres routes sont deux
    façons de tenir compte d'une nuit de détention, et elles encadrent la
    vérité par les deux côtés. Leur écart s'ouvre exactement là où gamma est
    le plus grand.
    """
    b = _plate(478, "Niveaux · l'identité gamma-thêta",
               "La courbure reçue est exactement le thêta payé",
               "volatilité " + _pct(V.VOL_ANNUELLE, 0))

    js = [1.0 * (1.10 ** i) for i in range(60)]
    js = [j for j in js if j <= 200.0]
    inst = V.equilibre_instantane()

    p1 = Panel(b, PX1, 92, PW, 214, title="Mouvement quotidien d'équilibre",
               readout="% du comptant")
    p1.domain(1.0, 200.0, 0.9, 2.0, xlog=True)
    p1.frame()
    p1.grid_y(_ticks(1.0, 2.0, 0.25), lambda v: _num(v, 2), dx=32.0)
    p1.grid_x([1, 3, 10, 30, 100], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.path([(j, 100 * inst) for j in js], "hm3", dash="6 3",
            tip="identite : sigma sur racine de 365")
    p1.path([(j, 100 * V.equilibre_quadratique(j)) for j in js], "hm5",
            tip="approximation quadratique")
    p1.path([(j, 100 * V.equilibre_exact(j)) for j in js], "hm6",
            tip="reevaluation exacte")

    p2 = Panel(b, PX2, 92, PW, 214, title="Gamma par un pour cent",
               readout="points")
    p2.domain(1.0, 200.0, 100.0, 3000.0, xlog=True, ylog=True)
    p2.frame()
    p2.grid_y([100, 300, 1000, 3000], lambda v: _num(v, 0), dx=42.0)
    p2.grid_x([1, 3, 10, 30, 100], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.path([(j, V.gamma(q.INDEX_LEVEL, q.INDEX_LEVEL, V.VOL_ANNUELLE,
                         j / V.JOURS_AN) * q.INDEX_LEVEL ** 2 * 0.01)
             for j in js], "hm6", tip="gamma par un pour cent")

    b.legend(PX1, 352.0,
             [("hm3", "identité, plate", "6 3"),
              ("hm5", "approximation quadratique", ""),
              ("hm6", "réévaluation exacte", "")],
             step=190.0, kind="line")
    b.annotation(0.0, 372.0,
                 "la droite tiretée est le théorème : sigma sur racine de "
                 "365, à toute échéance et à tout strike")
    b.annotation(0.0, 388.0,
                 "les deux autres routes encadrent la vérité, et leur rapport "
                 "vaut " + _num(V.equilibre_quadratique(1.0)
                                / V.equilibre_exact(1.0), 2)
                 + " au dernier jour contre "
                 + _num(V.equilibre_quadratique(180.0)
                        / V.equilibre_exact(180.0), 2) + " à six mois")

    _source(b, "Pour un livre couvert en delta à taux nul, l'équation de "
               "Black-Scholes se réduit à une seule identité : le thêta payé "
               "est exactement la courbure reçue, facturée au prix de la "
               "volatilité implicite. Le mouvement d'équilibre ne dépend donc "
               "ni de l'échéance, ni du strike, ni du niveau — c'est le "
               "théorème d'arrêt optionnel du marché d'options, et il dit la "
               "même chose que l'identité de ce document : aucune géométrie "
               "ne crée d'espérance, elle achète du temps. Les deux autres "
               "courbes tiennent compte d'une nuit de détention, et leur "
               "écart s'ouvre exactement au dernier jour, là où la courbure "
               "est la plus grande et où l'approximation quadratique qui "
               "fonde tout le discours cesse de valoir.")
    return b.render("Trois routes vers le mouvement quotidien d equilibre, et "
                    "gamma par un pour cent contre l echeance.")


# ---------------------------------------------------------------------------
# V. Le signe
# ---------------------------------------------------------------------------


def fig_nv_gex() -> str:
    """Le profil d'intérêt ouvert, la bascule, et la bande que l'ignorance ouvre.

    À gauche l'objet dont on part, à droite ce qu'il devient quand le signe
    n'est pas observé. Rien de ce qui est tracé ici n'est une donnée de
    marché : tout est de l'arithmétique sur un profil déclaré.
    """
    b = _plate(510, "Niveaux · le signe que la reconstruction jette",
               "Le niveau de bascule, et la bande qu'il occupe vraiment",
               "profil synthétique déclaré")

    prof = V.profil_oi()
    ref = V.bascule()
    lo, med, hi, absent = V.bande_de_bascule(0.0)

    p1 = Panel(b, PX1, 92, PW, 214, title="Intérêt ouvert par strike",
               readout="contrats")
    p1.domain(0.85 * q.INDEX_LEVEL, 1.16 * q.INDEX_LEVEL, 0.0,
              1.15 * V.OI_MAX)
    p1.frame()
    p1.grid_y(_ticks(0.0, 10000.0, 2500.0), lambda v: _num(v, 0), dx=44.0)
    p1.grid_x([5200, 5600, 6000, 6400, 6800], lambda v: _num(v, 0),
              label="strike")
    # Les deux cloches se posent de part et d'autre du strike : superposees,
    # la plus claire cachait l'autre, et le profil se lisait comme une seule
    # bosse a deux sommets.
    ecart = 0.35 * (V.STRIKES[1] - V.STRIKES[0])
    for k, oi_c, oi_p in prof:
        p1.vbar(k - ecart, 0.0, oi_p, 3.4, "hm3",
                tip="put " + _num(k, 0) + " : " + _num(oi_p, 0))
        p1.vbar(k + ecart, 0.0, oi_c, 3.4, "hm6",
                tip="call " + _num(k, 0) + " : " + _num(oi_c, 0))
    p1.vline(q.INDEX_LEVEL, "lvl")
    p1.label(q.INDEX_LEVEL, 1.09 * V.OI_MAX, "comptant", dx=5, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Exposition nette et sa bande",
               readout="millions par 1 %")
    spots = [(0.85 + 0.0031 * i) * q.INDEX_LEVEL for i in range(101)]
    ys = [V.gex(s) for s in spots]
    borne = max(abs(min(ys)), abs(max(ys))) * 1.25
    pas = 10.0 ** math.floor(math.log10(borne)) * 2.0
    p2.domain(spots[0], spots[-1], -borne, borne)
    p2.frame()
    p2.grid_y(_ticks(-borne, borne, pas), lambda v: _signed(v, 0), dx=44.0)
    p2.grid_x([5200, 5600, 6000, 6400, 6800], lambda v: _num(v, 0),
              label="comptant")
    # Le lavis avant la courbe, sans quoi il la recouvre.
    p2.band_x(lo, hi)
    p2.hline(0.0, "lvl")
    p2.path(list(zip(spots, ys)), "hm6", tip="exposition nette supposee")
    p2.vline(lo, "lvl")
    p2.vline(hi, "lvl")
    p2.dot(ref, 0.0, "hm7", "bascule supposée : " + _num(ref, 0), r=4.4)
    p2.label(ref, 0.0, _num(ref, 0), dx=8, dy=-9)
    p2.label(lo, -0.88 * borne, _num(lo, 0), dx=4, dy=0)
    p2.label(hi, -0.88 * borne, _num(hi, 0), dx=-4, dy=0, anchor="end")

    b.legend(PX1, 368.0,
             [("hm3", "intérêt ouvert put"),
              ("hm6", "intérêt ouvert call")], step=200.0)

    b.annotation(0.0, 388.0,
                 "la bande grisée est l'intervalle où la bascule se promène "
                 "quand aucun signe n'est observé : " + _num(hi - lo, 0)
                 + " points")
    b.annotation(0.0, 404.0,
                 "soit " + _num((hi - lo) / seuil.geometry(0.150).stop_points,
                                0) + " fois le stop élargi du document")
    b.annotation(0.0, 420.0,
                 "et dans " + _pct(absent, 0) + " des tirages, il n'existe "
                 "aucune bascule du tout")

    _source(b, "Le profil de gauche est synthétique et déclaré, construit "
               "pour être lisible : deux cloches décalées, les puts sous le "
               "comptant et les calls au-dessus. Tout ce qui suit en est de "
               "l'arithmétique. La courbe de droite est l'exposition nette "
               "sous l'hypothèse habituelle, celle qui fait exister une "
               "bascule : teneur long les calls, court les puts, à tous les "
               "strikes. La bande grisée est ce que cette hypothèse vaut. "
               "L'intérêt ouvert ne porte aucun signe, et retourner les "
               "signes inconnus déplace le passage à zéro sur des centaines "
               "de points, quand il ne le fait pas disparaître. Un niveau "
               "dont l'incertitude propre dépasse de deux ordres la géométrie "
               "qui prétend le trader ne porte rien à cette résolution.")
    return b.render("Profil d interet ouvert par strike, exposition nette "
                    "supposee, et bande de la bascule sous signe inconnu.")


def fig_nv_bascule() -> str:
    """Le relief de la bande de bascule.

    Deux façons de réduire l'incertitude, et une seule est à la portée d'un
    opérateur — aucune, en fait, ce qui est le résultat.
    """
    z = V.surface_absence()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Niveaux · ce que vaut une supposition",
               "Quand la bascule n'existe pas du tout",
               "hauteur : tirages sans bascule")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_pct(f, 0) for f in V.SURF_PART],
             col_labels=[_num(j, 0) for j in V.SURF_JOURS_GEX],
             z_ticks=[(t, _pct(t / 100.0, 0)) for t in _echine(zlo, zhi)],
             tip="{v:.0f} % des tirages sans aucune bascule", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : part des strikes dont le signe est connu · "
                 "arête droite : jours à l'échéance")
    b.annotation(0.0, 424.0,
                 "loin de l'échéance la courbure s'étale sur tous les "
                 "strikes, et la somme devient une quasi-égalité")
    b.annotation(0.0, 440.0,
                 "le coin du fond est celui de l'ignorance complète à "
                 "longue échéance, et neuf tirages sur dix n'y ont pas de "
                 "bascule")

    _source(b, "La grandeur portée n'est pas la largeur de la bande, et le "
               "choix vient d'une mesure qui a réfuté la première version de "
               "cette planche. On attendait qu'un profil très asymétrique "
               "resserre l'incertitude, la masse d'un côté devant finir par "
               "dominer ; le balayage rend une surface plate sur cet axe, et "
               "l'axe a donc été remplacé par l'échéance, qui agit. Près de "
               "l'échéance la courbure se concentre sur quelques strikes et "
               "le passage à zéro y est tenu par le déséquilibre local ; loin "
               "de l'échéance elle s'étale, tous les strikes pèsent à peu "
               "près pareil, et la somme devient une quasi-égalité que "
               "n'importe quel signe retourné fait basculer. La part "
               "d'absence est en outre la seule grandeur que la censure ne "
               "fausse pas : une configuration sans bascule ne peut entrer "
               "dans aucun quantile, mais elle entre dans ce compte-là.")
    return b.render("Surface de la part des tirages sans aucune bascule, sur "
                    "le plan des signes connus et de l echeance.")


# ---------------------------------------------------------------------------
# VI. Ce qui reste
# ---------------------------------------------------------------------------

#: Les quatre colonnes du verdict. La derniere est vide, et c'est la planche.
COLONNES = ("rien", "l'horloge", "le risque", "le sens")


def fig_nv_reste() -> str:
    """Ce que chaque affirmation déplace, et la colonne que rien ne remplit.

    Quatre colonnes et cinq lignes. La planche ne montre pas un résultat, elle
    montre un rangement — et le rangement est le résultat, parce que la
    dernière colonne reste vide.
    """
    lst = V.affirmations()
    b = _plate(494, "Niveaux · le décompte",
               "Cinq affirmations, et la colonne que rien ne remplit",
               _num(sum(1 for x in lst if x.directionnelle), 0)
               + " sur " + _num(len(lst), 0))

    n = len(lst)
    p1 = Panel(b, 214.0, 92, W - 214.0 - 12.0, 232,
               title="Ce que chaque affirmation déplace", readout="rangement")
    p1.domain(-0.5, len(COLONNES) - 0.5, -0.6, n - 0.4)
    p1.frame()
    p1.grid_x(list(range(len(COLONNES))), lambda v: COLONNES[int(round(v))])
    for j in range(1, len(COLONNES)):
        p1.vline(j - 0.5, "lvl")
    for i, x in enumerate(lst):
        y = n - 1 - i
        j = COLONNES.index(x.porte)
        cls = "hm3" if x.porte == "rien" else "hm6"
        p1.hbar(y, j - 0.42, j + 0.42, 15.0, cls,
                tip=x.quoi + " : déplace " + x.porte)
        p1.label(-0.5, y, x.court, dx=-9, dy=4, anchor="end")
    p1.label(len(COLONNES) - 1.0, -0.5, "aucune", dx=0, dy=0, anchor="middle")

    b.legend(0.0, 368.0,
             [("hm3", "ne déplace rien"),
              ("hm6", "déplace une grandeur")], step=300.0)
    b.annotation(0.0, 392.0,
                 "deux affirmations déplacent l'horloge, une déplace le "
                 "risque, deux ne déplacent rien")
    b.annotation(0.0, 408.0,
                 "la colonne du sens reste vide, et le verdict est calculé à "
                 "chaque construction du document")
    b.annotation(0.0, 424.0,
                 "ce n'est pas un verdict sur la mécanique, c'est un verdict "
                 "sur la reconstruction de détail")

    _source(b, "La mécanique de couverture des teneurs est réelle et son "
               "effet sur la volatilité réalisée est documenté dans la "
               "littérature. Ce que la planche range est autre chose : la "
               "reconstruction que le public en fait, à partir d'un intérêt "
               "ouvert non signé, d'une seule volatilité et d'un "
               "positionnement supposé. Cette reconstruction jette exactement "
               "l'information qui la rendrait utilisable, et le rangement le "
               "montre sans avoir rien à dire sur l'efficience du marché. "
               "Deux affirmations déplacent l'horloge, ce qui est le résultat "
               "structurant de ce document depuis sa première partie ; une "
               "déplace le risque ; deux ne déplacent rien à la résolution où "
               "on les trade. La dernière colonne reste vide.")
    return b.render("Rangement des cinq affirmations sur le gamma selon la "
                    "grandeur que chacune deplace.")


FIGURES = {
    "nvtemoin": fig_nv_temoin,
    "nvdefinition": fig_nv_definition,
    "nvexigence": fig_nv_exigence,
    "nvrelief": fig_nv_relief,
    "nvlargeur": fig_nv_largeur,
    "nvinvalidation": fig_nv_invalidation,
    "nvforcee": fig_nv_forcee,
    "nvbande": fig_nv_bande,
    "nvidentite": fig_nv_identite,
    "nvgex": fig_nv_gex,
    "nvbascule": fig_nv_bascule,
    "nvreste": fig_nv_reste,
}


def render_all() -> dict[str, str]:
    return {k: f() for k, f in FIGURES.items()}
