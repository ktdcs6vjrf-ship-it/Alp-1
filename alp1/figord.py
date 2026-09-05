"""Les planches de « les grecs du troisième ordre ».

Quinze planches, onze à plat et quatre en relief. La sixième porte le seul
résultat de la partie qui se démontre plutôt qu'il ne se balaie, et la
douzième porte la seule affirmation chiffrée de la section honnête du guide.

Comme les modules d'options qui précèdent, celui-ci importe ses fonctions
d'échine, de graduation et de pourcentage de `fignv`.
"""

from __future__ import annotations

import math

from . import grandeurs as G
from . import ordres as O
from . import vanna as va
from . import vega as vg
from .figdisc import W, _plate, _source, _surface
from .fignv import _dec, _echine, _pct, _ticks
from .figterm import Board, Panel, _num, _signed

PW = (W - 74.0) / 2.0 - 30.0
PX1 = 74.0
PX2 = 74.0 + (W - 74.0) / 2.0

S = O.S_REF
V = O.VOL_REF
AN = O.JOURS_AN


def _t(jours: float) -> float:
    return jours / AN


# ---------------------------------------------------------------------------
# I. La famille, et son contrôle
# ---------------------------------------------------------------------------


def fig_ord_famille() -> str:
    """Les cinq grandeurs, et ce qu'elles ont en commun."""
    b = _plate(500, "Ordres supérieurs · la famille",
               "Toutes les cinq s'aiguisent quand l'échéance se referme",
               "trois échéances")

    ms = [0.86 + 0.0028 * i for i in range(101)]
    series = [("hm7", "", 7.0), ("hm5", "6 3", 30.0), ("hm3", "2 3", 90.0)]

    p1 = Panel(b, PX1, 92, PW, 214, title="Speed contre le comptant",
               readout="par point")
    courbes = [(cls, dash, j,
                [(m, O.speed(S, S / m, V, _t(j))) for m in ms])
               for cls, dash, j in series]
    hi = max(y for _, _, _, c in courbes for _, y in c)
    lo = min(y for _, _, _, c in courbes for _, y in c)
    p1.domain(ms[0], ms[-1], lo * 1.20, hi * 1.20)
    p1.frame()
    p1.grid_y(_ticks(lo * 1.20, hi * 1.20, 0.01), lambda v: _signed(v, 2),
              dx=34.0)
    p1.grid_x([0.90, 0.95, 1.00, 1.05, 1.10], lambda v: _num(v, 2),
              label="spot sur strike")
    p1.hline(0.0, "lvl")
    p1.vline(1.0, "lvl")
    for cls, dash, j, c in courbes:
        p1.path(c, cls, dash=dash, tip=_num(j, 0) + " jours")
    p1.label(ms[0], hi * 1.05, "positif sous le strike", dx=8, dy=0)
    p1.label(ms[-1], lo * 1.05, "négatif au-dessus", dx=-8, dy=0, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Zomma contre le comptant",
               readout="par point de volatilité")
    cz = [(cls, dash, j, [(m, O.zomma(S, S / m, V, _t(j))) for m in ms])
          for cls, dash, j in series]
    hi2 = max(y for _, _, _, c in cz for _, y in c)
    lo2 = min(y for _, _, _, c in cz for _, y in c)
    p2.domain(ms[0], ms[-1], lo2 * 1.15, hi2 * 1.35)
    p2.frame()
    p2.grid_y(_ticks(lo2 * 1.15, hi2 * 1.35, 0.2), lambda v: _signed(v, 1),
              dx=30.0)
    p2.grid_x([0.90, 0.95, 1.00, 1.05, 1.10], lambda v: _num(v, 2),
              label="spot sur strike")
    p2.hline(0.0, "lvl")
    for cls, dash, j, c in cz:
        p2.path(c, cls, dash=dash, tip=_num(j, 0) + " jours")
    p2.label(1.0, lo2 * 1.05, "négatif à la monnaie", dx=8, dy=0)

    b.legend(0.0, 352.0,
             [("hm7", "sept jours"), ("hm5", "trente jours", "6 3"),
              ("hm3", "trois mois", "2 3")],
             step=200.0, kind="line")
    b.annotation(0.0, 376.0,
                 "les deux changent de signe, et le guide donne les deux "
                 "signes justes près de la monnaie")
    b.annotation(0.0, 392.0,
                 "les trois courbes de chaque cadre sont la même forme, "
                 "d'autant plus aiguë que l'échéance est courte")
    b.annotation(0.0, 408.0,
                 "c'est le fil commun de la famille : ce sont des phénomènes "
                 "de fin de vie, et rien d'autre")

    _source(b, "Les cinq grandeurs de ce guide sont des dérivées troisièmes, "
               "et elles partagent une propriété que le guide nomme "
               "correctement : elles s'aiguisent toutes dramatiquement quand "
               "l'échéance se referme. C'est ce qui explique pourquoi un "
               "livre du jour en a besoin et un livre mensuel presque pas. "
               "Le cadre de gauche donne Speed, qui est positif sous le "
               "strike et négatif au-dessus, exactement comme la table de "
               "référence du guide l'annonce ; le cadre de droite donne "
               "Zomma, négatif près de la monnaie pour la même raison que le "
               "volga y est négatif, et sa frontière est le produit des deux "
               "arguments égal à un.")
    return b.render("Speed et Zomma contre le comptant a trois echeances.")


def fig_ord_controle() -> str:
    """Les formes fermées contre la dérivée qu'elles prétendent être."""
    b = _plate(490, "Ordres supérieurs · le contrôle",
               "Aucun des neuf guides ne contrôle ce qu'il écrit",
               "forme fermée contre différence finie")

    ms = [0.88 + 0.0024 * i for i in range(101)]
    t = _t(30.0)

    p1 = Panel(b, PX1, 92, PW, 214, title="Speed, deux routes",
               readout="par point")
    ferme = [(m, O.speed(S, S / m, V, t)) for m in ms]
    num_ = [(m, O.speed_numerique(S, S / m, V, t)) for m in ms]
    hi = max(y for _, y in ferme)
    lo = min(y for _, y in ferme)
    p1.domain(ms[0], ms[-1], lo * 1.20, hi * 1.20)
    p1.frame()
    p1.grid_y(_ticks(lo * 1.20, hi * 1.20, 0.005), lambda v: _signed(v, 3),
              dx=40.0)
    p1.grid_x([0.90, 0.95, 1.00, 1.05, 1.10], lambda v: _num(v, 2),
              label="spot sur strike")
    p1.hline(0.0, "lvl")
    p1.path(num_, "hm4", tip="différence finie du gamma")
    p1.path(ferme, "hm1", dash="2 3", tip="forme fermée")
    p1.label(ms[0], lo * 1.08, "les deux se superposent", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Ultima, deux routes",
               readout="par point de volatilité au cube")
    fe = [(m, O.ultima(S, S / m, V, t)) for m in ms]
    nu = [(m, O.ultima_numerique(S, S / m, V, t)) for m in ms]
    hi2 = max(y for _, y in fe)
    lo2 = min(y for _, y in fe)
    p2.domain(ms[0], ms[-1], lo2 * 1.15, hi2 * 1.30)
    p2.frame()
    p2.grid_y(_ticks(lo2 * 1.15, hi2 * 1.30, 100.0), lambda v: _signed(v, 0),
              dx=36.0)
    p2.grid_x([0.90, 0.95, 1.00, 1.05, 1.10], lambda v: _num(v, 2),
              label="spot sur strike")
    p2.hline(0.0, "lvl")
    p2.path(nu, "hm4", tip="différence finie du volga")
    p2.path(fe, "hm1", dash="2 3", tip="forme fermée")
    p2.label(1.0, lo2 * 1.05, "négatif à la monnaie", dx=8, dy=0)

    b.legend(0.0, 352.0,
             [("hm4", "la différence finie"),
              ("hm1", "la forme fermée, par-dessus", "2 3")],
             step=240.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le trait clair est la mesure, le pointillé sombre la "
                 "formule : les deux se superposent sur toute la plage")
    b.annotation(0.0, 392.0,
                 "c'est le résultat du cadre : une forme fermée qu'aucune "
                 "route ne contrôle est une hypothèse")
    b.annotation(0.0, 408.0,
                 "la partie XXIV a trouvé dans ce dépôt une dérivée croisée "
                 "fausse d'une racine, restée invisible faute de contrôle")

    _source(b, "Le pointillé sombre est posé par-dessus le trait clair, et "
               "c'est délibéré : la superposition exacte est ce que le cadre "
               "montre, et l'ordre inverse la cacherait — la partie XXIII "
               "avait perdu une courbe de contrôle exactement ainsi. Aucun "
               "des neuf guides de cette série ne publie ce contrôle, et ce "
               "n'est pas un reproche de forme. La partie XXIV a trouvé dans "
               "ce dépôt une dérivée croisée dont le dénominateur oubliait "
               "une racine, restée fausse pendant une partie entière parce "
               "qu'aucune table et aucune figure ne la consommait. Une forme "
               "fermée se contrôle contre une route indépendante, et le "
               "contrôle coûte quatre lignes.")
    return b.render("Les formes fermees de Speed et d Ultima contre leur "
                    "difference finie.")


def fig_ord_relief_speed() -> str:
    """Le relief de Speed."""
    z = [list(l) for l in O.surface_speed()]
    vals = [v for l in z for v in l]

    b = _plate(486, "Ordres supérieurs · le relief de Speed",
               "La couverture de gamma se périme dans un seul coin du plan",
               "hauteur : speed")

    _surface(b, 0.52 * W, 232.0, z, min(vals), max(vals), cx=42.0, cy=13.0,
             cz=158.0,
             row_labels=[_num(j, 0) + " j" for j in O.SURF_JOURS_CROISSANT],
             col_labels=[_num(m, 3) for m in O.SURF_MONEYNESS],
             z_ticks=[(t, _num(t, 3)) for t in _echine(min(vals), max(vals))],
             tip="{v:.5f}", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : l'échéance · arête droite : le spot sur le "
                 "strike · hauteur : la vitesse à laquelle le gamma fuit")
    b.annotation(0.0, 424.0,
                 "le sommet est à la monnaie la veille de l'échéance, et "
                 "la surface s'effondre dès qu'on s'en éloigne")
    b.annotation(0.0, 440.0,
                 "c'est la définition d'un phénomène de fin de vie : il "
                 "n'existe que dans un coin du plan")

    _source(b, "La hauteur est la vitesse à laquelle une couverture de gamma "
               "se périme. Le relief dit en une image pourquoi le guide "
               "répond non à sa propre question : la grandeur n'est pas "
               "petite partout, elle est nulle partout sauf dans un coin, et "
               "ce coin est la dernière journée à la monnaie. Un opérateur "
               "qui tient des options quelques heures sur un produit liquide "
               "ne visite ce coin que s'il le cherche. La partie ne conteste "
               "donc pas l'objet ; elle chiffre à quelle distance du coin il "
               "cesse d'exister.")
    return b.render("Relief de la vitesse a laquelle le gamma fuit, en "
                    "echeance et en moneyness.")


# ---------------------------------------------------------------------------
# II. L'horloge
# ---------------------------------------------------------------------------


def fig_ord_horloge() -> str:
    """Color et Veta à la monnaie sont l'horloge et rien d'autre."""
    b = _plate(500, "Ordres supérieurs · l'horloge",
               "Deux des cinq n'ont aucun paramètre libre",
               "à la monnaie")

    # L'axe des jours est **logarithmique**, et ce n'est pas un ornement :
    # les deux grandeurs sont des puissances de l'échéance, donc elles
    # s'effondrent contre le bord gauche d'un axe linéaire — quatre-vingt-dix
    # pour cent du cadre y était vide et toute la forme tenait dans une
    # lisière de deux jours. Le balayage d'occupation ne le voit pas : le
    # cadre est plein, c'est la donnée qui est écrasée.
    js = [2.0 * (365.0 / 2.0) ** (i / 139.0) for i in range(140)]

    p1 = Panel(b, PX1, 92, PW, 214, title="Le gamma qu'on aura demain",
               readout="rapporté à celui d'aujourd'hui")
    ferme = [(j, O.gamma_demain_simple(j)) for j in js]
    mes = [(j, O.gamma_demain_mesure(j)) for j in js]
    hi = max(y for _, y in ferme)
    p1.domain(js[0], js[-1], 1.0, hi * 1.03, xlog=True)
    p1.frame()
    p1.grid_y(_ticks(1.0, hi * 1.03, 0.2), lambda v: _num(v, 1), dx=26.0)
    p1.grid_x([2, 7, 30, 90, 365], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.path(mes, "hm4", tip="mesure")
    p1.path(ferme, "hm1", dash="2 3", tip="racine du rapport des échéances")
    p1.hline(1.0, "lvl")
    p1.dot(2.0, O.gamma_demain_mesure(2.0), "hm4", "la veille", r=4.5)
    p1.label(2.0, O.gamma_demain_mesure(2.0),
             "la veille : " + _num(100 * (O.gamma_demain_mesure(2.0) - 1.0), 1)
             + " % de gamma en plus", dx=10, dy=4)

    p2 = Panel(b, PX2, 92, PW, 214, title="Le véga qu'une journée emporte",
               readout="% du véga")
    fv = [(j, 100.0 * O.vega_perdu_simple(j)) for j in js]
    mv = [(j, 100.0 * O.vega_perdu_mesure(j)) for j in js]
    hi2 = max(y for _, y in fv)
    p2.domain(js[0], js[-1], 0.0, hi2 * 1.10, xlog=True)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2 * 1.10, 5.0), lambda v: _num(v, 0) + " %",
              dx=32.0)
    p2.grid_x([2, 7, 30, 90, 365], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.path(mv, "hm4", tip="mesure")
    p2.path(fv, "hm1", dash="2 3", tip="un moins la racine")
    for j in (7.0, 365.0):
        if j <= js[-1]:
            p2.dot(j, 100.0 * O.vega_perdu_mesure(j), "hm4",
                   _num(j, 0) + " jours", r=4.5)
    p2.label(7.0, 100.0 * O.vega_perdu_mesure(7.0),
             "une semaine : " + _num(100 * O.vega_perdu_mesure(7.0), 2) + " %",
             dx=10, dy=6)

    b.legend(0.0, 352.0,
             [("hm4", "la mesure"),
              ("hm1", "la forme fermée, par-dessus", "2 3")],
             step=240.0, kind="line")
    b.annotation(0.0, 376.0,
                 "à la monnaie le gamma vaut une constante sur la racine de "
                 "l'échéance, et le véga cette constante fois la racine")
    b.annotation(0.0, 392.0,
                 "leurs dérivées en temps ne dépendent donc ni de la "
                 "volatilité, ni du niveau, ni du taux")
    b.annotation(0.0, 408.0,
                 "le véga perd " + _num(100 * O.vega_perdu_mesure(7.0), 2)
                 + " % par jour à une semaine et "
                 + _num(100 * O.vega_perdu_mesure(365.0), 2)
                 + " % à un an, un facteur " + _num(O.facteur_veta(), 0))

    _source(b, "Le guide dit substantiellement plus de gamma demain, et le "
               "véga du mois avant qui se volatilise. Les deux sont justes, "
               "et ce que la mesure ajoute est qu'ils se calculent sans rien "
               "savoir du marché. À la monnaie, la seule dépendance en "
               "échéance du gamma est une racine au dénominateur, celle du "
               "véga la même racine au numérateur ; leurs dérivées en temps "
               "sont donc des identités d'horloge. Color et Veta décrivent "
               "un calendrier, et un calendrier ne se prévoit pas.")
    return b.render("Le gamma de demain et le vega perdu contre l echeance, "
                    "forme fermee et mesure.")


def fig_ord_corrections() -> str:
    """Les deux corrections que la lecture simple laisse."""
    b = _plate(490, "Ordres supérieurs · les deux écarts",
               "La lecture simple est fausse de deux choses, et les deux se nomment",
               "en relatif")

    js = [3.0 + 3.0 * i for i in range(130)]

    p1 = Panel(b, PX1, 92, PW, 214, title="Ce qui sépare les trois lectures",
               readout="écart relatif")
    a = [(j, 1e4 * abs(O.vega_perdu_simple(j) / O.vega_perdu(j) - 1.0))
         for j in js]
    c = [(j, 1e4 * abs(O.ecart_de_portage(j))) for j in js]
    hi = max(y for _, y in c)
    p1.domain(0.0, js[-1], 0.0, hi * 1.15)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi * 1.15, 200.0), lambda v: _num(v, 0), dx=30.0)
    p1.grid_x([0, 100, 200, 300], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.path(c, "hm7", tip="le portage")
    p1.path(a, "hm3", dash="5 4", tip="le terme en sigma carré")
    p1.label(js[0], hi * 1.06, "le portage domine", dx=8, dy=0,
             anchor="start")

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce que cela vaut aux ténors courts",
               readout="dix-millièmes")
    tenors = (7.0, 30.0, 90.0, 365.0)
    n = len(tenors)
    haut = max(1e4 * abs(O.ecart_de_portage(j)) for j in tenors) * 1.35
    p2.domain(0.0, haut, -0.6, n - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, haut, 200.0), lambda v: _num(v, 0))
    for i, j in enumerate(tenors):
        y = n - 1 - i
        pa = 1e4 * abs(O.vega_perdu_simple(j) / O.vega_perdu(j) - 1.0)
        pc = 1e4 * abs(O.ecart_de_portage(j))
        p2.hbar(y + 0.17, 0.0, pc, 10.0, "hm7", tip="portage")
        p2.hbar(y - 0.17, 0.0, pa, 10.0, "hm3", tip="terme en sigma carré")
        p2.label(0.0, y + 0.36, _num(j, 0) + " jours", dx=4, dy=0)
        p2.label(pc, y + 0.17, _num(pc, 0), dx=6, dy=4)

    b.legend(0.0, 352.0,
             [("hm7", "le portage"),
              ("hm3", "le terme en sigma carré T sur huit", "5 4")],
             step=240.0)
    b.annotation(0.0, 376.0,
                 "la loi en racine est exacte à portage nul et à volatilité "
                 "nulle ; hors de là elle laisse deux termes")
    b.annotation(0.0, 392.0,
                 "les deux valent quelques dix-millièmes aux ténors courts, "
                 "là où le guide place son propos")
    b.annotation(0.0, 408.0,
                 "et le portage domine partout : c'est la question de la "
                 "partie XXIII posée sur un troisième objet")

    _source(b, "La lecture simple — le gamma de demain vaut la racine du "
               "rapport des échéances — est celle qu'un pupitre retient, et "
               "elle est juste à deux cent-millièmes près sur une journée. "
               "Elle n'est pourtant exacte ni tout à fait : deux termes la "
               "séparent de la mesure, et les nommer vaut mieux que les "
               "ignorer. Le premier vient de ce que l'argument de la densité "
               "n'est pas nul à la monnaie mais vaut la moitié de la racine "
               "de la variance ; le second est le portage, qui déplace la "
               "monnaie elle-même. Le second domine partout, et c'est la "
               "troisième partie de suite où la question décisive est celle "
               "de la variable qu'on tient fixe.")
    return b.render("Les deux ecarts que la lecture simple laisse, contre "
                    "l echeance et par tenor.")


def fig_ord_relief_color() -> str:
    """Le relief de Color."""
    z = [list(l) for l in O.surface_color()]
    vals = [v for l in z for v in l]

    b = _plate(486, "Ordres supérieurs · le relief de Color",
               "Le gamma de demain, et où il grandit vraiment",
               "hauteur : gamma gagné par jour")

    _surface(b, 0.52 * W, 232.0, z, min(vals), max(vals), cx=42.0, cy=13.0,
             cz=158.0,
             row_labels=[_num(j, 0) + " j" for j in O.SURF_JOURS_CROISSANT],
             col_labels=[_num(m, 3) for m in O.SURF_MONEYNESS],
             z_ticks=[(t, _num(t, 4)) for t in _echine(min(vals), max(vals))],
             tip="{v:.5f}", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : l'échéance · arête droite : le spot sur le "
                 "strike · hauteur : le gamma gagné en une journée")
    b.annotation(0.0, 424.0,
                 "la bande claire du fond est la région que le guide appelle "
                 "la gestion du risque du jour même")
    b.annotation(0.0, 440.0,
                 "elle est étroite dans les deux directions : quelques jours "
                 "et quelques dixièmes de pour cent de prix")

    _source(b, "Le guide écrit que la bande à la monnaie des trois derniers "
               "jours est le lieu où vit la gestion du risque du jour même, "
               "et que le gamma n'y est pas seulement grand mais croissant, "
               "dans une bande de prix large d'une fraction de pour cent. Le "
               "relief le confirme et le chiffre : la région où Color est "
               "matériel occupe quelques jours sur l'axe du temps et "
               "quelques dixièmes de pour cent sur celui du prix. C'est un "
               "coin, pas une plage, et le reste de la surface est un sol. "
               "L'objet existe et il est petit — deux choses que le guide "
               "dit lui-même.")
    return b.render("Relief du gamma gagne en une journee, en echeance et "
                    "en moneyness.")


# ---------------------------------------------------------------------------
# III. Le mouvement qui divise le gamma par deux
# ---------------------------------------------------------------------------


def fig_ord_demigamma() -> str:
    """Le mouvement qui divise le gamma par deux."""
    b = _plate(500, "Ordres supérieurs · la demi-hauteur",
               "Une fraction de pour cent, mais pas le dernier jour",
               "à la monnaie")

    js = [0.05 + 0.05 * i for i in range(120)]

    p1 = Panel(b, PX1, 92, PW, 214, title="Le mouvement qui divise par deux",
               readout="% du comptant")
    mes = [(j, 100.0 * O.mouvement_de_demi_gamma_mesure(j) / S) for j in js]
    fer = [(j, 100.0 * O.mouvement_de_demi_gamma(j) / S) for j in js]
    hi = max(y for _, y in fer)
    p1.domain(0.0, js[-1], 0.0, hi * 1.10)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi * 1.10, 1.0), lambda v: _num(v, 0) + " %",
              dx=30.0)
    p1.grid_x([0, 2, 4, 6], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.hline(1.0, "lvl")
    p1.path(mes, "hm4", tip="mesure")
    p1.path(fer, "hm1", dash="2 3", tip="racine de deux fois le logarithme")
    p1.vline(1.0, "lvl")
    p1.dot(1.0, 100.0 * O.mouvement_de_demi_gamma_mesure(1.0) / S, "hm4",
           "un jour", r=4.5)
    p1.label(1.0, 100.0 * O.mouvement_de_demi_gamma_mesure(1.0) / S,
             "un jour : "
             + _num(100 * O.mouvement_de_demi_gamma_mesure(1.0) / S, 2) + " %",
             dx=10, dy=-6)
    p1.label(js[-1], 1.0, "le pour cent du guide", dx=-8, dy=-8, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Quand le seuil est franchi",
               readout="heures avant l'échéance")
    hs = [1.0 + 29.0 * i / 79.0 for i in range(80)]
    courbe = [(h, 100.0 * O.mouvement_de_demi_gamma_mesure(h / 24.0) / S)
              for h in hs]
    hi2 = max(y for _, y in courbe)
    p2.domain(0.0, hs[-1], 0.0, hi2 * 1.12)
    p2.frame()
    p2.grid_y(_ticks(0.0, hi2 * 1.12, 0.5), lambda v: _num(v, 1) + " %",
              dx=34.0)
    p2.grid_x([0, 10, 20, 30], lambda v: _num(v, 0),
              label="heures avant l'échéance")
    p2.hline(1.0, "lvl")
    p2.path(courbe, "hm6", tip="mouvement de demi-gamma")
    hstar = 24.0 * O.echeance_du_pour_cent()
    p2.vline(hstar, "lvl")
    p2.dot(hstar, 1.0, "hm6", "le franchissement", r=4.5)
    p2.label(hstar, 1.0, _num(hstar, 1) + " heures", dx=10, dy=10)

    b.legend(0.0, 352.0,
             [("hm4", "la mesure"),
              ("hm1", "la forme fermée", "2 3"),
              ("hm6", "les dernières heures, à droite")],
             step=200.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le gamma est proportionnel à une densité normale, donc il "
                 "est divisé par deux quand son argument vaut "
                 + _num(O.DEMI_HAUTEUR, 3))
    b.annotation(0.0, 392.0,
                 "c'est exactement la constante de la largeur d'un niveau de "
                 "gamma, établie par la partie XIX sur un autre objet")
    b.annotation(0.0, 408.0,
                 "le guide dit le dernier jour ; la mesure dit les "
                 + _num(hstar, 1) + " dernières heures")

    _source(b, "Le mouvement se résout et la constante est connue : c'est la "
               "demi-largeur à mi-hauteur d'une gaussienne, la même que la "
               "partie XIX avait rencontrée en mesurant la largeur d'un "
               "niveau de gamma. Le guide écrit que le dernier jour, le "
               "gamma peut être divisé par deux sur un mouvement d'une "
               "fraction de pour cent ; à un jour de l'échéance il en faut "
               "une fois et demie le pour cent, et le seuil n'est franchi "
               "que dans les dernières heures. C'est le premier des neuf "
               "guides de la série qui surestime son propre objet — les "
               "quatre qui l'ont précédé le sous-estimaient, chacun d'une "
               "manière différente.")
    return b.render("Le mouvement qui divise le gamma par deux contre "
                    "l echeance, et l heure ou il passe sous un pour cent.")


# ---------------------------------------------------------------------------
# IV. Ultima et les trois bandes
# ---------------------------------------------------------------------------


def fig_ord_ultima() -> str:
    """Ultima, ses deux bascules, et la racine qu'on n'atteint jamais."""
    b = _plate(500, "Ordres supérieurs · Ultima",
               "Deux changements de signe, et cela se démontre",
               "trente jours")

    t = _t(30.0)
    ms = [0.55 + 0.009 * i for i in range(101)]

    p1 = Panel(b, PX1, 92, PW, 214, title="Ultima contre le comptant",
               readout="par point de volatilité au cube")
    c = [(m, O.ultima(S, S / m, V, t)) for m in ms]
    hi = max(y for _, y in c)
    lo = min(y for _, y in c)
    p1.domain(ms[0], ms[-1], lo * 1.20, hi * 1.30)
    p1.frame()
    p1.grid_y(_ticks(lo * 1.20, hi * 1.30, 200.0), lambda v: _signed(v, 0),
              dx=36.0)
    p1.grid_x([0.6, 0.8, 1.0, 1.2, 1.4], lambda v: _num(v, 1),
              label="spot sur strike")
    p1.hline(0.0, "lvl")
    p1.path(c, "hm7", tip="ultima")
    blo, bhi = O.bande_ultima(t)
    for m in (blo, bhi):
        p1.dot(m, 0.0, "hm7", "changement de signe", r=4.5)
    atm = O.ultima(S, S, V, t)
    p1.label(ms[0], lo * 1.08, "négatif entre les deux points", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="La racine négative n'est jamais atteinte",
               readout="produit, en millièmes")
    blo2, bhi2 = va.bande_de_desobeissance(t)
    marge = 0.35 * (bhi2 - blo2)
    mz = [blo2 - marge + (bhi2 - blo2 + 2.0 * marge) * i / 160
          for i in range(161)]
    prod = []
    for m in mz:
        d1, d2 = G._d(S, S / m, V, t, O.TAUX, O.DIVIDENDE)
        prod.append((m, 1e3 * d1 * d2))
    rac = 1e3 * O.racines_ultima(t)[0]
    mini = 1e3 * O.minimum_de_d1d2(t)
    hi2 = max(y for _, y in prod)
    p2.domain(mz[0], mz[-1], rac * 1.60, hi2 * 1.35)
    p2.frame()
    p2.grid_y(_ticks(rac * 1.60, hi2 * 1.35, 0.5), lambda v: _signed(v, 1),
              dx=34.0)
    p2.grid_x([mz[0], 1.0, mz[-1]],
              lambda v: _num(v, 4), label="spot sur strike")
    p2.hline(0.0, "lvl")
    p2.hline(rac, "lvl")
    p2.path(prod, "hm5", tip="produit des deux arguments")
    mmin = O.moneyness_du_minimum(t)
    p2.dot(mmin, mini, "hm5", "le minimum", r=4.5)
    p2.label(mz[-1], rac, "la racine négative : " + _signed(rac, 2), dx=-8,
             dy=15, anchor="end")
    p2.label(mmin, mini, "le minimum : " + _signed(mini, 2), dx=10, dy=-9)

    b.legend(0.0, 352.0,
             [("hm7", "Ultima"),
              ("hm5", "le produit des deux arguments, à droite")],
             step=240.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le signe bascule où le produit vaut "
                 + _num(O.racines_ultima(t)[1], 3)
                 + ", une forme fermée en racine de neuf plus quatre sigma "
                 "carré T")
    b.annotation(0.0, 392.0,
                 "les deux points de la ligne de zéro sont les deux "
                 "bascules : la bosse centrale la frôle sans traverser")
    b.annotation(0.0, 408.0,
                 "à la monnaie Ultima vaut " + _signed(atm, 1) + ", soit "
                 + _num(hi / abs(atm), 0) + " fois moins que son pic : à "
                 "cette échelle, c'est zéro")
    b.annotation(0.0, 424.0,
                 "le cadre de droite zoome mille fois : le minimum du "
                 "produit tombe au-dessus de la racine négative")

    _source(b, "Le facteur d'Ultima se réduit à un trinôme du second degré "
               "en le produit des deux arguments, dès qu'on remarque que la "
               "somme de leurs carrés vaut la variance plus deux fois leur "
               "produit. Ses deux racines sont donc en forme fermée. La "
               "seconde est atteinte, et c'est elle qui borne la bande "
               "négative ; la première ne l'est jamais, parce que le produit "
               "a lui-même un minimum et que ce minimum tombe au-dessus "
               "d'elle. Le cadre de droite le montre : la courbe du produit "
               "reste au-dessus de la ligne basse sur toute la plage. "
               "L'affirmation du guide se démontre donc plutôt qu'elle ne se "
               "vérifie, ce qui est une meilleure façon d'avoir raison.")
    return b.render("Ultima contre le comptant, et le produit des deux "
                    "arguments qui explique ses deux bascules.")


def fig_ord_bandes() -> str:
    """Les trois bandes du même produit, emboîtées."""
    b = _plate(500, "Ordres supérieurs · les trois bandes",
               "Un seul produit, trois seuils, trois bandes emboîtées",
               "% du comptant")

    js = [3.0 + 3.6 * i for i in range(101)]

    p1 = Panel(b, PX1, 92, PW, 214, title="Les trois largeurs",
               readout="% du comptant")
    vo_ = [(j, 100.0 * (va.bande_de_desobeissance(_t(j))[1]
                        - va.bande_de_desobeissance(_t(j))[0])) for j in js]
    zo = [(j, 100.0 * O.largeur_zomma(_t(j))) for j in js]
    ul = [(j, 100.0 * O.largeur_ultima(_t(j))) for j in js]
    hi = max(y for _, y in ul)
    p1.domain(0.0, js[-1], 0.0, hi * 1.10)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi * 1.10, 20.0), lambda v: _num(v, 0) + " %",
              dx=32.0)
    p1.grid_x([0, 100, 200, 300], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.path(ul, "hm7", tip="Ultima")
    p1.path(zo, "hm5", dash="6 3", tip="Zomma")
    p1.path(vo_, "hm3", dash="2 3", tip="volga")
    p1.hline(1.0, "lvl")
    p1.label(js[-1], 1.0, "le pas d'une grille de strikes", dx=-8, dy=-15,
             anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="À trente jours",
               readout="% du comptant")
    t30 = _t(30.0)
    lo30, hi30 = va.bande_de_desobeissance(t30)
    lignes = [
        ("Ultima · produit sous " + _num(O.racines_ultima(t30)[1], 2),
         100.0 * O.largeur_ultima(t30)),
        ("Zomma · produit sous un", 100.0 * O.largeur_zomma(t30)),
        ("volga · produit sous zéro", 100.0 * (hi30 - lo30)),
    ]
    n = len(lignes)
    haut = max(v for _, v in lignes) * 1.35
    p2.domain(0.0, haut, -0.6, n - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, haut, 10.0), lambda v: _num(v, 0) + " %")
    p2.vline(1.0, "lvl")
    for i, (nom, v) in enumerate(lignes):
        y = n - 1 - i
        p2.hbar(y, 0.0, v, 13.0, "hm7" if i == 0 else "hm3", tip=nom)
        p2.label(0.0, y + 0.34, nom, dx=4, dy=0)
        p2.label(v, y, _num(v, 2) + " %", dx=7, dy=4)
    p2.label(1.0, -0.35, "une grille au pour cent", dx=7, dy=0)

    b.legend(0.0, 352.0,
             [("hm7", "Ultima"), ("hm5", "Zomma", "6 3"),
              ("hm3", "volga", "2 3")],
             step=200.0, kind="line")
    b.annotation(0.0, 376.0,
                 "les trois bandes bornent le même produit à trois seuils : "
                 "zéro, un, et "
                 + _num(O.racines_ultima(t30)[1], 2))
    b.annotation(0.0, 392.0,
                 "elles sont donc emboîtées par construction, et le rapport "
                 "de la plus large à la plus étroite vaut "
                 + _num(O.rapport_au_volga(t30), 0) + " à trente jours")
    b.annotation(0.0, 408.0,
                 "seule celle d'Ultima dépasse le pas d'une grille de "
                 "strikes : c'est la première de la famille qui soit cotable")

    _source(b, "Les parties XXII, XXIV et XXVI ont chacune rencontré une "
               "bande bornée par le produit des deux arguments, et chacune a "
               "conclu qu'elle tombait sous le pas d'une grille de strikes. "
               "Cette partie en ajoute deux, et la conclusion change. Les "
               "trois seuils sont zéro pour le volga, un pour Zomma, et une "
               "racine voisine de trois pour Ultima ; les bandes sont donc "
               "emboîtées et non semblables, et la dernière est cotable. "
               "Le guide écrit qu'Ultima reflète la structure du volga : "
               "c'est vrai de la forme et faux de l'échelle, et l'échelle "
               "est ce qui décide si un objet existe sur un tableau de "
               "cotation.")
    return b.render("Les trois largeurs de bande contre l echeance, et leur "
                    "comparaison a trente jours.")


def fig_ord_relief_ultima() -> str:
    """Le relief d'Ultima."""
    z = [list(l) for l in O.surface_ultima()]
    vals = [v for l in z for v in l]

    b = _plate(486, "Ordres supérieurs · le relief d'Ultima",
               "La seule des cinq dont la structure occupe le tableau",
               "hauteur : ultima en valeur absolue")

    _surface(b, 0.52 * W, 232.0, z, min(vals), max(vals), cx=42.0, cy=13.0,
             cz=158.0,
             row_labels=[_num(j, 0) + " j" for j in O.SURF_JOURS],
             col_labels=[_num(m, 2) for m in O.SURF_MONEYNESS_LARGE],
             z_ticks=[(t, _num(t, 0)) for t in _echine(min(vals), max(vals))],
             tip="{v:.1f}", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : l'échéance · arête droite : le spot sur le "
                 "strike · hauteur : Ultima en valeur absolue")
    b.annotation(0.0, 424.0,
                 "la crête n'est pas à la monnaie : elle suit la frontière "
                 "où le produit des deux arguments vaut trois")
    b.annotation(0.0, 440.0,
                 "c'est ce qui distingue Ultima des quatre autres, qui "
                 "culminent toutes au même coin")

    _source(b, "Les quatre autres grandeurs de ce guide culminent au même "
               "endroit : la monnaie, la veille de l'échéance. Ultima non. "
               "Sa crête suit la frontière où le produit des deux arguments "
               "vaut trois, donc elle s'éloigne de la monnaie quand "
               "l'échéance s'allonge, exactement comme la crête du volga de "
               "la partie XXVI. C'est la raison pour laquelle le guide dit "
               "qu'Ultima ne compte que pour les livres exotiques et "
               "fortement convexes : ce n'est pas une grandeur de fin de "
               "vie, c'est une grandeur d'aile, et une aile se tient sur "
               "toute la courbe.")
    return b.render("Relief d Ultima en valeur absolue, en echeance et en "
                    "moneyness.")


# ---------------------------------------------------------------------------
# V. La variance de P/L
# ---------------------------------------------------------------------------


def fig_ord_variance() -> str:
    """Ce que quatre grecs expliquent, et ce qu'ils laissent."""
    b = _plate(520, "Ordres supérieurs · les quatre-vingt-dix-neuf pour cent",
               "La seule affirmation chiffrée de la note, et elle est prudente",
               "part de variance de P/L")

    couples = O.COUPLES
    n = len(couples)
    parts = [(100.0 * O.campagne(e, d, False).part,
              100.0 * O.campagne(e, d, True).part) for e, d in couples]
    p1 = Panel(b, PX1, 92, PW, 214, title="Ce que quatre grecs expliquent",
               readout="% de la variance")
    bas = min(c for _, c in parts) - 0.6
    p1.domain(bas, 100.35, -0.6, n - 0.4)
    p1.frame()
    p1.grid_x(_ticks(bas, 100.35, 1.0), lambda v: _num(v, 0) + " %")
    p1.vline(99.0, "lvl")
    for i, ((e, d), (libre, cvt)) in enumerate(zip(couples, parts)):
        y = n - 1 - i
        p1.path([(cvt, y), (libre, y)], "hm4", tip="ce que la couverture coûte")
        p1.dot(cvt, y, "hm3", "livre couvert en delta", r=4.5)
        p1.dot(libre, y, "hm7", "livre nu", r=4.5)
        p1.label(bas, y + 0.30,
                 _num(e, 2) + " j, tenu " + _num(24.0 * d, 0) + " h",
                 dx=4, dy=0)
    p1.label(99.0, -0.42, "ce que le guide annonce", dx=-7, dy=0,
             anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Ce que les termes supérieurs laissent",
               readout="écart-type, en points")
    ecarts = [(O.campagne(e, d, True).ecart_pl,
               O.campagne(e, d, True).ecart_residu) for e, d in couples]
    lo2 = min(r for _, r in ecarts) / 2.4
    hi2 = max(v for v, _ in ecarts) * 2.4
    p2.domain(lo2, hi2, -0.6, n - 0.4, xlog=True)
    p2.frame()
    p2.grid_x([1e-4, 1e-3, 1e-2, 1e-1], _dec)
    for i, (pl, res) in enumerate(ecarts):
        y = n - 1 - i
        p2.path([(res, y), (pl, y)], "hm4", tip="ce que les quatre laissent")
        p2.dot(res, y, "hm1", "le résidu", r=4.5)
        p2.dot(pl, y, "hm5", "le P/L couvert", r=4.5)
        p2.label(res, y, _num(res, 4), dx=-8, dy=17, anchor="end")

    b.legend(0.0, 362.0,
             [("hm7", "livre nu"), ("hm3", "livre couvert en delta"),
              ("hm5", "le P/L couvert, à droite"), ("hm1", "son résidu")],
             step=180.0)
    b.annotation(0.0, 386.0,
                 "le résidu porte vanna, volga, charm, veta, speed, zomma, "
                 "color, ultima et tous les ordres au-delà")
    b.annotation(0.0, 402.0,
                 "l'affirmation tient partout : jamais moins de "
                 + _num(100 * O.pire_part(False), 1) + " % pour un livre nu, "
                 + _num(100 * O.pire_part(True), 1) + " % pour un livre couvert")
    b.annotation(0.0, 418.0,
                 "dans le cas que le guide décrit, le résidu vaut "
                 + _num(1e6 * (1.0 - O.campagne(7.0, 4.0 / 24.0).part), 1)
                 + " millionièmes de la variance")
    b.annotation(0.0, 434.0,
                 "mêmes couples dans les deux cadres, et les deux axes sont "
                 "tronqués : ce sont des points, pas des barres")

    _source(b, "Le guide écrit que delta, gamma, thêta et véga décrivent "
               "plus de quatre-vingt-dix-neuf pour cent de la variance de "
               "P/L pour un opérateur directionnel. C'est la seule "
               "affirmation chiffrée de sa section honnête, et elle est "
               "prudente : sur toute la grille d'échéances et de durées de "
               "détention, la part expliquée ne descend jamais sous le seuil "
               "qu'il annonce, et dans le cas qu'il décrit lui-même le "
               "résidu se compte en millionièmes. Le livre couvert en delta, "
               "qu'il donne comme le premier des trois cas où les termes "
               "supérieurs comptent, se dégrade réellement — et pas jusqu'à "
               "l'effondrement. Retirer le delta ne fait pas apparaître les "
               "termes supérieurs ; cela retire le terme qui les écrasait.")
    return b.render("La part de variance de P/L expliquee par quatre grecs, "
                    "livre nu et livre couvert.")


def fig_ord_residu() -> str:
    """Où le résidu devient matériel, et à quelle vitesse."""
    b = _plate(490, "Ordres supérieurs · le résidu",
               "Le résidu grandit avec la détention, pas avec l'échéance",
               "livre couvert en delta")

    p1 = Panel(b, PX1, 92, PW, 214, title="Contre la durée de détention",
               readout="part non expliquée")
    detentions = (1.0 / 24.0, 3.0 / 24.0, 6.0 / 24.0, 12.0 / 24.0, 1.0)
    series = [("hm7", "", 2.0), ("hm5", "6 3", 7.0), ("hm3", "2 3", 30.0)]
    courbes = []
    for cls, dash, e in series:
        pts = [(24.0 * d, 1e4 * (1.0 - O.campagne(e, d, True).part))
               for d in detentions if d < e]
        courbes.append((cls, dash, e, pts))
    hi = max(y for _, _, _, c in courbes for _, y in c)
    p1.domain(0.0, 25.0, 0.0, hi * 1.15)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi * 1.15, 50.0), lambda v: _num(v, 0), dx=30.0)
    p1.grid_x([0, 6, 12, 18, 24], lambda v: _num(v, 0),
              label="heures de détention")
    for cls, dash, e, c in courbes:
        p1.path(c, cls, dash=dash, tip=_num(e, 0) + " jours")
        for x, y in c:
            p1.dot(x, y, cls, _num(e, 0) + " j, " + _num(x, 0) + " h", r=3.4)
    p1.label(0.0, hi * 1.05, "en dix-millièmes de la variance", dx=8, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce que cela vaut en points",
               readout="écart-type du résidu")
    haut = max(O.campagne(e, d, True).ecart_residu
               for _, _, e in series for d in detentions if d < e) * 1.25
    p2.domain(0.0, 25.0, 0.0, haut)
    p2.frame()
    p2.grid_y(_ticks(0.0, haut, 0.01), lambda v: _num(v, 2), dx=34.0)
    p2.grid_x([0, 6, 12, 18, 24], lambda v: _num(v, 0),
              label="heures de détention")
    for cls, dash, e in series:
        pts = [(24.0 * d, O.campagne(e, d, True).ecart_residu)
               for d in detentions if d < e]
        p2.path(pts, cls, dash=dash, tip=_num(e, 0) + " jours")
    p2.label(0.0, haut * 0.92, "sur un indice à cent points", dx=8, dy=0)

    b.legend(0.0, 352.0,
             [("hm7", "deux jours"), ("hm5", "sept jours", "6 3"),
              ("hm3", "trente jours", "2 3")],
             step=200.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le résidu croît avec la durée de détention et décroît avec "
                 "l'échéance : les deux axes n'ont pas le même rôle")
    b.annotation(0.0, 392.0,
                 "c'est ce qui rend le conseil du guide exact : ce qui "
                 "compte n'est pas l'option tenue mais le temps qu'on la tient")
    b.annotation(0.0, 408.0,
                 "à une heure de détention, le résidu est sous le "
                 "dix-millième à toutes les échéances")

    _source(b, "Le résidu ne dépend pas de l'échéance de la même façon que "
               "de la durée de détention, et c'est la nuance qui manque à la "
               "formulation courante. Une option très courte tenue une heure "
               "laisse un résidu négligeable ; la même option tenue une "
               "journée en laisse cent fois plus. Ce que la section honnête "
               "du guide décrit comme un opérateur tenant des options "
               "quelques heures est donc la bonne variable : c'est la durée "
               "de détention qui décide, et non la maturité du contrat. Le "
               "cadre de droite donne la même chose en points d'indice, "
               "parce qu'une part de variance ne se compare à aucun budget.")
    return b.render("La part non expliquee et l ecart-type du residu contre "
                    "la duree de detention.")


def fig_ord_relief_veta() -> str:
    """Le relief de Veta."""
    z = [list(l) for l in O.surface_veta()]
    vals = [v for l in z for v in l]

    b = _plate(486, "Ordres supérieurs · le relief de Veta",
               "Le véga du mois avant se volatilise, celui du long terme non",
               "hauteur : véga perdu par jour")

    _surface(b, 0.52 * W, 232.0, z, min(vals), max(vals), cx=42.0, cy=13.0,
             cz=158.0,
             row_labels=[_num(j, 0) + " j" for j in O.SURF_JOURS_CROISSANT],
             col_labels=[_num(m, 3) for m in O.SURF_MONEYNESS],
             z_ticks=[(t, _num(t, 2)) for t in _echine(min(vals), max(vals))],
             tip="{v:.4f}", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : l'échéance · arête droite : le spot sur le "
                 "strike · hauteur : le véga perdu en une journée")
    b.annotation(0.0, 424.0,
                 "la surface est presque plate le long de l'axe du prix et "
                 "raide le long de celui du temps")
    b.annotation(0.0, 440.0,
                 "c'est la signature d'une grandeur d'horloge : le prix n'y "
                 "entre presque pas")

    _source(b, "Ce relief dit la même chose que la planche de l'horloge, et "
               "il la dit d'une manière qu'un tableau ne peut pas. La "
               "surface est raide le long de l'axe du temps et presque plate "
               "le long de celui du prix : Veta ne dépend guère de l'endroit "
               "où le marché se trouve, seulement du temps qu'il reste. "
               "C'est la signature d'une grandeur d'horloge, et c'est ce qui "
               "la rend inutilisable comme signal — une grandeur qui ne "
               "regarde pas le prix ne peut rien en dire.")
    return b.render("Relief du vega perdu en une journee, en echeance et en "
                    "moneyness.")


# ---------------------------------------------------------------------------
# VI. Le décompte
# ---------------------------------------------------------------------------


def fig_ord_reste() -> str:
    """Le décompte, et le cumul des neuf parties d'options."""
    b = _plate(470, "Ordres supérieurs · le décompte",
               "Neuf documents, et le neuvième dit lui-même qu'il n'y a pas de sens",
               "neuf parties d'options")

    grandeurs = ("la direction", "l'horloge", "le risque", "rien")
    compte = O.compte_par_grandeur()
    n = len(grandeurs)
    p1 = Panel(b, PX1, 92, PW, 214, title="Ce qu'elles déplacent",
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

    fam = O.familles()
    m = len(fam)
    p2 = Panel(b, PX2, 92, PW, 214, title="Le cumul des neuf parties",
               readout="affirmations examinées")
    hautf = max(v for _, v in fam) * 1.45
    p2.domain(0.0, hautf, -0.6, m - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, hautf, 3.0), lambda v: _num(v, 0))
    for i, (nom, v) in enumerate(fam):
        y = m - 1 - i
        p2.hbar(y, 0.0, v, 7.0, "hm5", tip=nom + " : " + _num(v, 0))
        p2.label(0.0, y + 0.42, nom, dx=4, dy=0)
        p2.label(v, y, _num(v, 0), dx=6, dy=3)

    b.legend(0.0, 352.0,
             [("hm7", "ce qu'elles déplacent"),
              ("hm1", "la direction, vide"),
              ("hm5", "par partie, à droite")],
             step=200.0)
    b.annotation(0.0, 376.0,
                 "sur les " + _num(sum(v for _, v in fam), 0)
                 + " affirmations des neuf parties d'options, aucune ne "
                 "donne un sens")
    b.annotation(0.0, 392.0,
                 "ce neuvième guide est le seul des neuf à l'écrire "
                 "lui-même, et il l'écrit mieux que ce document")
    b.annotation(0.0, 408.0,
                 "ces grandeurs disent comment votre exposition va changer, "
                 "pas où le prix va")

    _source(b, "La colonne de la direction est vide pour la sixième partie "
               "consécutive, et le cumul des neuf parties d'options n'en "
               "contient aucune non plus. Ce qui distingue ce neuvième "
               "guide des huit autres n'est pas la qualité de ses formules, "
               "qui est comparable, mais le fait qu'il publie lui-même la "
               "conclusion : vendre ces grandeurs comme un signal "
               "intrajournalier est une erreur de catégorie, elles décrivent "
               "comment une exposition va changer et ne disent rien de la "
               "direction du prix. C'est la thèse de la quatrième partie de "
               "ce document, écrite par un praticien, dans une note "
               "destinée à vendre l'objet qu'elle refuse de survendre.")
    return b.render("Le decompte des affirmations et le cumul des neuf "
                    "parties d options.")


FIGURES = {
    "ordfamille": fig_ord_famille,
    "ordcontrole": fig_ord_controle,
    "ordreliefsp": fig_ord_relief_speed,
    "ordhorloge": fig_ord_horloge,
    "ordcorrections": fig_ord_corrections,
    "ordreliefco": fig_ord_relief_color,
    "orddemigamma": fig_ord_demigamma,
    "ordultima": fig_ord_ultima,
    "ordbandes": fig_ord_bandes,
    "ordrelieful": fig_ord_relief_ultima,
    "ordvariance": fig_ord_variance,
    "ordresidu": fig_ord_residu,
    "ordreliefve": fig_ord_relief_veta,
    "ordreste": fig_ord_reste,
}


def render_all() -> dict[str, str]:
    return {k: f() for k, f in FIGURES.items()}
