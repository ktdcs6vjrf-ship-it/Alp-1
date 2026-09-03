"""Les planches de « le prix de l'incertitude ».

Quinze planches, onze à plat et quatre en relief. Aucune ne montre un signal :
toutes montrent un nombre résumé qui annonce zéro, et ce que la réévaluation
répond.

Comme `figgra` et `figth`, ce module importe ses fonctions d'échine, de
graduation et de décade de `fignv` plutôt que de les recopier.
"""

from __future__ import annotations

import math

from . import niveaux as nv
from . import vega as V
from .figdisc import W, _plate, _source, _surface
from .fignv import _dec, _echine, _pct, _ticks
from .figterm import Board, Panel, _num, _signed


PW = (W - 74.0) / 2.0 - 30.0
PX1 = 74.0
PX2 = 74.0 + (W - 74.0) / 2.0


# ---------------------------------------------------------------------------
# I. L'échelle
# ---------------------------------------------------------------------------


def fig_vg_echelle() -> str:
    """Le véga contre le spot et contre le temps.

    Les deux cadres du guide, recalculés. Celui de gauche montre la colline ;
    celui de droite montre qu'elle grandit en racine du temps, et le point de
    la table y est posé.
    """
    b = _plate(500, "Véga · l'échelle",
               "Le véga contre le spot, et contre le temps",
               _num(100 * V.VOL_REF, 0) + " % de volatilité")

    p1 = Panel(b, PX1, 92, PW, 214, title="Contre le spot",
               readout="par point de vol")
    spots = [55.0 + 0.5 * i for i in range(191)]
    series = [("hm7", "", 7.0), ("hm5", "6 3", 30.0), ("hm3", "2 3", 90.0),
              ("hm1", "1 4", 365.0)]
    courbes = [(cls, dash, j,
                [(s, V.vega_par_point(s, V.S_REF, V.VOL_REF, j / 365.0))
                 for s in spots]) for cls, dash, j in series]
    hi = max(y for _, _, _, c in courbes for _, y in c) * 1.25
    p1.domain(55.0, 150.0, 0.0, hi)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi, 0.1), lambda v: _num(v, 1), dx=30.0)
    p1.grid_x([60, 80, 100, 120, 140], lambda v: _num(v, 0), label="spot")
    p1.vline(V.S_REF, "lvl")
    for cls, dash, j, c in courbes:
        p1.path(c, cls, dash=dash, tip=_num(j, 0) + " jours")

    # Le cadre de droite porte une autre grandeur que le cadre de gauche, et
    # ses courbes sont nommees sur place : la legende du bas decrit quatre
    # echeances, et une teinte ne doit pas designer deux choses sur la meme
    # planche.
    p2 = Panel(b, PX2, 92, PW, 214, title="La croissance en racine",
               readout="rapport au mois")
    js = [1.0 + 2.0 * i2 for i2 in range(183)]
    ref = V.vega(V.S_REF, V.S_REF, V.VOL_REF, 30.0 / 365.0)
    mesure = [(jj, V.vega(V.S_REF, V.S_REF, V.VOL_REF, jj / 365.0) / ref)
              for jj in js]
    yhi = max(y for _, y in mesure) * 1.30
    p2.domain(0.0, 365.0, 0.0, yhi)
    p2.frame()
    p2.grid_y(_ticks(0.0, yhi, 1.0), lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([0, 90, 180, 270, 365], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.path([(jj, math.sqrt(jj / 30.0)) for jj in js], "hm0", dash="2 3",
            tip="racine du temps")
    p2.path(mesure, "hm6", tip="mesure")
    p2.dot(365.0, V.rapport_de_tenors() * V.vega(V.S_REF, V.S_REF, V.VOL_REF,
                                                 14.0 / 365.0) / ref, "hm6",
           "un an", r=4.2)
    p2.label(6.0, yhi * 0.90, "trait plein : la mesure", dx=0, dy=0)
    p2.label(6.0, yhi * 0.78, "pointillé : la racine du temps", dx=0, dy=0)
    p2.label(365.0, 1.0, "l'ancrage du mois", dx=-6, dy=-8, anchor="end")
    p2.hline(1.0, "lvl")

    b.legend(0.0, 352.0,
             [("hm7", "sept jours", ""), ("hm5", "trente jours", "6 3"),
              ("hm3", "quatre-vingt-dix jours", "2 3"),
              ("hm1", "un an", "1 4")],
             step=166.0, kind="line")
    b.annotation(0.0, 376.0,
                 "à droite, la mesure et la racine du temps sont "
                 "indiscernables à l'œil sur toute la plage")
    b.annotation(0.0, 392.0,
                 "le véga d'un an vaut " + _num(V.rapport_de_tenors(), 2)
                 + " fois celui de deux semaines, quand le guide annonce "
                 + _num(V.RAPPORT_ANNONCE, 1))
    b.annotation(0.0, 408.0,
                 "la racine du temps est une excellente approximation ; le "
                 "nombre publié ne l'est pas")

    _source(b, "Le cadre de gauche est celui du guide, recalculé dans "
               "l'unité du pupitre — par point de volatilité, c'est-à-dire la "
               "forme fermée divisée par cent. Le cadre de droite superpose "
               "la croissance mesurée et la racine du temps, calées toutes "
               "deux sur le mois : les deux courbes sont indiscernables, "
               "parce que la seule chose qui les sépare est le facteur de "
               "densité, qui bouge peu. La conclusion du guide est donc juste "
               "et le nombre qu'il en tire ne l'est pas : un an vaut "
               + _num(V.rapport_de_tenors(), 2) + " fois deux semaines, et "
               "non " + _num(V.RAPPORT_ANNONCE, 1) + ".")
    return b.render("Le vega contre le spot a quatre echeances, et contre le "
                    "temps a trois moneyness.")


def fig_vg_colline() -> str:
    """La colline et la pointe, et le fait qu'elles ont la même largeur.

    Le guide écrit que le gamma est une pointe et le véga une colline. Les
    deux normalisés se superposent presque : ce qui va en sens inverse n'est
    pas la largeur, c'est la hauteur, et leur rapport est une identité.
    """
    b = _plate(500, "Véga · la colline et la pointe",
               "Deux courbes de même largeur, et un rapport qui est exact",
               "à trente jours")

    p1 = Panel(b, PX1, 92, PW, 214, title="Les deux, à leur maximum",
               readout="fraction du maximum")
    t = 30.0 / 365.0
    spots = [70.0 + 0.25 * i for i in range(281)]
    vg = [(s, V.vega(s, V.S_REF, V.VOL_REF, t)) for s in spots]
    ga = [(s, nv.gamma(s, V.S_REF, V.VOL_REF, t)) for s in spots]
    mv = max(y for _, y in vg)
    mg = max(y for _, y in ga)
    p1.domain(70.0, 140.0, 0.0, 1.18)
    p1.frame()
    p1.grid_y(_ticks(0.0, 1.0, 0.25), lambda v: _num(v, 2), dx=32.0)
    p1.grid_x([80, 100, 120, 140], lambda v: _num(v, 0), label="spot")
    p1.hline(0.5, "lvl")
    p1.path([(s, y / mv) for s, y in vg], "hm7", tip="vega normalise")
    p1.path([(s, y / mg) for s, y in ga], "hm3", dash="6 3",
            tip="gamma normalise")
    p1.label(70.0, 0.5, "mi-hauteur", dx=6, dy=-8)

    p2 = Panel(b, PX2, 92, PW, 214, title="Leur rapport",
               readout="gamma sur véga")
    js = [3.0 * (1.06 ** i) for i in range(90)]
    js = [j for j in js if j <= 365.0]
    lo = min(nv.gamma(V.S_REF, V.S_REF, V.VOL_REF, j / 365.0)
             / V.vega(V.S_REF, V.S_REF, V.VOL_REF, j / 365.0) for j in js)
    hi = max(nv.gamma(V.S_REF, V.S_REF, V.VOL_REF, j / 365.0)
             / V.vega(V.S_REF, V.S_REF, V.VOL_REF, j / 365.0) for j in js)
    p2.domain(3.0, 365.0, lo / 1.6, hi * 1.6, xlog=True, ylog=True)
    p2.frame()
    p2.grid_y([t for t in (1e-4, 1e-3, 1e-2, 1e-1) if lo / 1.6 <= t <= hi * 1.6],
              _dec, dx=34.0)
    p2.grid_x([3, 10, 30, 100, 365], lambda v: _num(v, 0),
              label="jours à l'échéance")
    for cls, dash, m in (("hm7", "", 0.85), ("hm5", "6 3", 1.00),
                         ("hm3", "2 3", 1.20)):
        p2.path([(j, nv.gamma(m * V.S_REF, V.S_REF, V.VOL_REF, j / 365.0)
                  / V.vega(m * V.S_REF, V.S_REF, V.VOL_REF, j / 365.0))
                 for j in js], cls, dash=dash,
                tip="moneyness " + _num(m, 2))

    b.legend(0.0, 352.0,
             [("hm7", "véga, à gauche · S/K 0,85 à droite", ""),
              ("hm3", "gamma, à gauche · S/K 1,20 à droite", "6 3")],
             step=290.0, kind="line")
    b.annotation(0.0, 376.0,
                 "les deux pics font " + _pct(V.largeur_du_pic(t), 0)
                 + " et " + _pct(V.largeur_du_pic_gamma(t), 0)
                 + " du spot à mi-hauteur : la même largeur")
    b.annotation(0.0, 392.0,
                 "ce qui s'inverse est la hauteur, et leur rapport vaut "
                 "1/(S²σT) exactement, à tout strike")
    b.annotation(0.0, 408.0,
                 "il chute d'un facteur "
                 + _num(nv.gamma(V.S_REF, V.S_REF, V.VOL_REF, 7.0 / 365.0)
                        / V.vega(V.S_REF, V.S_REF, V.VOL_REF, 7.0 / 365.0)
                        / (nv.gamma(V.S_REF, V.S_REF, V.VOL_REF, 1.0)
                           / V.vega(V.S_REF, V.S_REF, V.VOL_REF, 1.0)), 0)
                 + " entre la semaine et l'année")

    _source(b, "Le cadre de gauche superpose les deux courbes ramenées à "
               "leur maximum, et il réfute la formule du guide : les deux "
               "pics partagent le facteur de densité et mesurent la même "
               "largeur à un pour cent près. Le cadre de droite dit ce qui "
               "les sépare vraiment, et c'est une identité — le rapport du "
               "gamma au véga vaut un sur S carré sigma T, sans dépendance au "
               "strike, ce que les trois courbes vérifient en restant "
               "parallèles. Une option courte est presque du gamma pur, une "
               "option longue presque du véga pur, et le mot « presque » se "
               "chiffre ici.")
    return b.render("Les pics de vega et de gamma normalises, et le rapport "
                    "des deux contre l echeance.")


# ---------------------------------------------------------------------------
# II. Le véga n'est pas un risque
# ---------------------------------------------------------------------------


def fig_vg_modes() -> str:
    """Deux livres à véga net nul, et trois modes de surface.

    Les barres sont le résultat par réévaluation ; le trait fin posé dessus
    est ce que le véga seul annonce. Là où les deux diffèrent, la différence
    est la courbure, et elle n'a aucun véga.
    """
    b = _plate(500, "Véga · deux livres neutres",
               "Le nombre résumé dit zéro, la réévaluation ne le dit plus",
               "choc de dix points")

    for k, (nom, faire) in enumerate(V.LIVRES):
        lignes = faire()
        px = PX1 if k == 0 else PX2
        pan = Panel(b, px, 92, PW, 214, title="Livre " + nom.lower(),
                    readout="points d'indice")
        vals = [(m, V.pl_livre(lignes, mode, 10.0),
                 V.pl_au_premier_ordre(lignes, mode, 10.0))
                for m, mode in V.MODES]
        hi = max(max(abs(a), abs(c)) for _, a, c in vals) * 1.30
        n = len(vals)
        pan.domain(0.0, hi, -0.6, n - 0.4)
        pan.frame()
        pan.grid_x(_ticks(0.0, hi, hi / 3.0), lambda v: _num(v, 1))
        for i, (nom_m, exact, ordre1) in enumerate(vals):
            y = n - 1 - i
            pan.hbar(y, 0.0, abs(exact), 13.0, "hm6",
                     tip=nom_m + " : " + _num(exact, 4))
            pan.vbar(abs(ordre1), y - 0.22, y + 0.22, 2.4, "hm3",
                     tip="au véga seul : " + _num(ordre1, 4))
            pan.label(0.0, y + 0.36, nom_m, dx=4, dy=0)
            pan.label(abs(exact), y, _num(abs(exact), 3), dx=7, dy=4)

    b.legend(0.0, 352.0,
             [("hm6", "résultat par réévaluation"),
              ("hm3", "ce que le véga seul annonce")],
             step=250.0)
    b.annotation(0.0, 376.0,
                 "les deux livres ont un véga net calculé nul, à la huitième "
                 "décimale")
    b.annotation(0.0, 392.0,
                 "chacun vit d'un mode et reste aveugle à celui de l'autre, "
                 "sans que le nombre résumé en dise rien")
    b.annotation(0.0, 408.0,
                 "sur le choc de niveau, le trait est à zéro et la barre ne "
                 "l'est pas : cette perte-là n'a aucun véga")

    _source(b, "Le livre calendrier est long le mois et court l'année ; le "
               "livre de peau est long les deux ailes et court la monnaie. "
               "Les deux quantités de couverture sont résolues pour "
               "annuler le véga net, jamais écrites — la partie XX a publié "
               "un zéro à la main sur deux livres qui n'étaient pas neutres. "
               "Le trait fin est le premier ordre, la barre la réévaluation "
               "exacte, et l'écart entre les deux est la courbure. Elle croît "
               "comme le carré du choc : au point de volatilité elle est "
               "invisible, aux dix points de l'exemple du guide elle vaut "
               "un cinquième de point d'indice sur un livre dont le résumé "
               "annonce zéro.")
    return b.render("Le resultat de deux livres a vega net nul sous trois "
                    "modes de surface, exact et au premier ordre.")


def fig_vg_courbure() -> str:
    """Ce que le véga annonce, et ce que la réévaluation rend, contre le choc.

    Une droite et une parabole. Le véga est la pente de la parabole à
    l'origine, et il a raison exactement là : partout ailleurs il manque un
    terme qui croît comme le carré.
    """
    b = _plate(500, "Véga · la droite et la parabole",
               "Le véga est exact en un point, et en un seul",
               "livre de peau, véga net nul")

    lignes = V.livre_peau()
    chocs = [-20.0 + 0.25 * i for i in range(161)]

    p1 = Panel(b, PX1, 92, PW, 214, title="Sous un choc de niveau",
               readout="points d'indice")
    exact = [(c, V.pl_livre(lignes, V.mode_niveau, c)) for c in chocs]
    ordre = [(c, V.pl_au_premier_ordre(lignes, V.mode_niveau, c))
             for c in chocs]
    lo = min(y for _, y in exact)
    hi = max(y for _, y in exact) * 1.25
    p1.domain(-20.0, 20.0, min(lo, -0.05), hi)
    p1.frame()
    p1.grid_y(_ticks(min(lo, -0.05), hi, 0.4), lambda v: _signed(v, 1),
              dx=32.0)
    p1.grid_x([-20, -10, 0, 10, 20], lambda v: _signed(v, 0),
              label="choc d'implicite, en points")
    p1.hline(0.0, "lvl")
    p1.path(ordre, "hm3", dash="6 3", tip="au vega seul")
    p1.path(exact, "hm7", tip="par reevaluation")
    p1.dot(0.0, 0.0, "hm5", "le seul point où le véga a raison", r=4.4)

    p2 = Panel(b, PX2, 92, PW, 214, title="Sous un choc de peau",
               readout="points d'indice")
    exact2 = [(c, V.pl_livre(lignes, V.mode_peau, c)) for c in chocs]
    ordre2 = [(c, V.pl_au_premier_ordre(lignes, V.mode_peau, c))
              for c in chocs]
    lo2 = min(min(y for _, y in exact2), min(y for _, y in ordre2)) * 1.15
    hi2 = max(max(y for _, y in exact2), max(y for _, y in ordre2)) * 1.15
    p2.domain(-20.0, 20.0, lo2, hi2)
    p2.frame()
    p2.grid_y(_ticks(lo2, hi2, 5.0), lambda v: _signed(v, 0), dx=30.0)
    p2.grid_x([-20, -10, 0, 10, 20], lambda v: _signed(v, 0),
              label="choc d'implicite, en points")
    p2.hline(0.0, "lvl")
    p2.path(ordre2, "hm3", dash="6 3", tip="au vega seul")
    p2.path(exact2, "hm7", tip="par reevaluation")

    b.legend(0.0, 352.0,
             [("hm7", "par réévaluation exacte", ""),
              ("hm3", "ce que le véga seul annonce", "6 3")],
             step=250.0, kind="line")
    b.annotation(0.0, 376.0,
                 "à gauche le véga annonce une droite plate à zéro, et la "
                 "réévaluation rend une parabole")
    b.annotation(0.0, 392.0,
                 "à droite le véga annonce la bonne pente, et manque la "
                 "courbure des deux côtés")
    b.annotation(0.0, 408.0,
                 "la courbure est ce que le guide appelle la volga, et elle "
                 "est ce qui rend une aile plus chère qu'elle n'en a l'air")

    _source(b, "Le livre est celui de la planche précédente, à véga net nul, "
               "et le cadre de gauche est donc censé ne rien faire. Sa "
               "parabole a son sommet exactement au choc nul, ce qui n'est "
               "pas un hasard : le véga est la dérivée première, il est juste "
               "à l'origine et faux partout ailleurs, et la seule chose qu'il "
               "manque est un terme en carré. Un pupitre qui couvre au véga "
               "seul est donc couvert pour les mouvements qui n'arrivent pas "
               "et découvert pour ceux qui arrivent — les dix points de "
               "l'exemple du guide tombent à mi-chemin du bord droit. Noter "
               "aussi que la parabole de gauche n'est pas symétrique : une "
               "baisse de vingt points rapporte trois fois ce que la même "
               "hausse rapporte, et cet écart-là est le troisième ordre.")
    return b.render("Le resultat d un livre a vega nul contre l amplitude du "
                    "choc, exact et au premier ordre.")


# ---------------------------------------------------------------------------
# III. La pondération
# ---------------------------------------------------------------------------


def fig_vg_ponderation() -> str:
    """La règle en racine, contre la seule surface qui ait une échelle.

    À gauche les deux poids en échelle logarithmique — c'est là qu'une loi de
    puissance est une droite, et la règle en est une. À droite l'exposant
    effectif, qui n'est constant nulle part.
    """
    k_opt, e_opt = V.kappa_minimax()
    js = [5.0 * (1.05 ** i) for i in range(100)]
    js = [j for j in js if j <= 365.0]

    b = _plate(500, "Véga · la pondération",
               "Une règle sans échelle, et une surface qui en a une",
               "meilleur retour : " + _num(k_opt, 2) + " par an")

    p1 = Panel(b, PX1, 92, PW, 214, title="Les deux poids", readout="poids")
    p1.domain(5.0, 365.0, 0.10, 3.0, xlog=True, ylog=True)
    p1.frame()
    p1.grid_y([0.1, 0.3, 1.0, 3.0], lambda v: _num(v, 1), dx=30.0)
    p1.grid_x([7, 14, 30, 90, 180, 365], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.path([(j, V.poids_regle(j)) for j in js], "hm7", tip="regle en racine")
    # Le cadre de gauche ne porte que deux courbes, et le cadre de droite
    # trois vitesses : une teinte ne doit designer qu une seule chose sur la
    # planche entiere, sans quoi la legende ment dans l un des deux cadres.
    p1.path([(j, V.poids_modele(j, k_opt)) for j in js], "hm3", dash="6 3",
            tip="modele au meilleur retour")
    p1.dot(V.TENOR_REF, 1.0, "hm5", "le ténor d'ancrage", r=4.4)
    p1.label(V.TENOR_REF, 1.0, "l'ancrage", dx=8, dy=-7)

    p2 = Panel(b, PX2, 92, PW, 214, title="L'exposant effectif",
               readout="sans dimension")
    p2.domain(5.0, 365.0, 0.0, 1.15, xlog=True)
    p2.frame()
    p2.grid_y(_ticks(0.0, 1.0, 0.25), lambda v: _num(v, 2), dx=32.0)
    p2.grid_x([7, 14, 30, 90, 180, 365], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.hline(0.5, "lvl")
    for cls, dash, k in (("hm5", "", 2.0), ("hm3", "6 3", k_opt),
                         ("hm1", "2 3", 16.0)):
        p2.path([(j, V.exposant_effectif(j, k)) for j in js], cls, dash=dash,
                tip="retour " + _num(k, 1) + " par an")
    p2.label(5.2, 0.5, "l'exposant que la règle suppose", dx=0, dy=-8)

    b.legend(0.0, 352.0,
             [("hm7", "la règle, à gauche", ""),
              ("hm3", "le meilleur retour", "6 3"),
              ("hm5", "un retour lent", ""),
              ("hm1", "un retour rapide", "2 3")],
             step=166.0, kind="line")
    b.annotation(0.0, 376.0,
                 "en échelle logarithmique la règle est une droite, et la "
                 "surface une courbe : aucun réglage ne les superpose")
    b.annotation(0.0, 392.0,
                 "l'exposant effectif passe de zéro à un et ne vaut un demi "
                 "qu'à un seul ténor, "
                 + _num(V.tenor_de_l_exposant(0.5, k_opt), 0) + " jours ici")
    b.annotation(0.0, 408.0,
                 "au mieux la règle manque de " + _pct(e_opt, 0)
                 + " aux deux bouts de la plage")

    _source(b, "La règle du guide pondère chaque seau par la racine de "
               "trente sur T. C'est un exposant postulé, et la partie XVIII a "
               "payé pour cette faute — une demi-largeur y était supposée "
               "décroître en racine, la mesure a rendu 0,61. Ici le verdict "
               "porte plus loin que la valeur : sous la seule famille de "
               "surfaces qui ait un sens, la sensibilité d'un ténor vaut "
               "un moins e moins kappa T, sur kappa T, dont l'exposant local "
               "passe de zéro aux ténors courts à un aux ténors longs. Une "
               "loi de puissance n'a pas d'échelle et cette courbe en a une ; "
               "les deux ne se rencontrent qu'en un point, et c'est le point "
               "d'ancrage que le pupitre a choisi.")
    return b.render("Les deux poids en echelle logarithmique, et l exposant "
                    "effectif contre le tenor.")


def fig_vg_kappa() -> str:
    """Le paramètre non observable, et ce qu'aucune de ses valeurs ne sauve.

    À gauche l'écart maximal de la règle contre la vitesse de retour : une
    courbe en U dont le fond est encore haut. À droite le ténor où la règle
    est exacte, qui est inversement proportionnel à la vitesse.
    """
    k_opt, e_opt = V.kappa_minimax()
    ks = [0.5 * (1.06 ** i) for i in range(90)]
    ks = [k for k in ks if k <= 40.0]

    b = _plate(494, "Véga · le paramètre non observable",
               "Aucune vitesse de retour ne sauve la règle",
               "plage de sept jours à un an")

    p1 = Panel(b, PX1, 92, PW, 214, title="L'écart maximal",
               readout="écart relatif")
    # Le domaine se deduit de la courbe : borne a 105 %, elle affichait un
    # plateau qui n existait pas et que rien ne signalait.
    courbe = [(k, V.ecart_maximal(k)) for k in ks]
    yhi = max(y for _, y in courbe) * 1.12
    p1.domain(0.5, 40.0, 0.0, yhi, xlog=True)
    p1.frame()
    p1.grid_y(_ticks(0.0, yhi, 0.5), lambda v: _pct(v, 0), dx=34.0)
    p1.grid_x([0.5, 1, 2, 4, 8, 16, 32], lambda v: _num(v, 1),
              label="retour à la moyenne, par an")
    p1.path(courbe, "hm7", tip="ecart maximal")
    p1.dot(k_opt, e_opt, "hm3", "le meilleur cas possible", r=4.6)
    p1.label(k_opt, e_opt, "le meilleur cas : " + _pct(e_opt, 0),
             dx=-9, dy=4, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Le ténor où la règle est exacte",
               readout="jours")
    p2.domain(0.5, 40.0, 10.0, 3000.0, xlog=True, ylog=True)
    p2.frame()
    p2.grid_y([10, 100, 1000], _dec, dx=34.0)
    p2.grid_x([0.5, 1, 2, 4, 8, 16, 32], lambda v: _num(v, 1),
              label="retour à la moyenne, par an")
    p2.path([(k, V.tenor_de_l_exposant(0.5, k)) for k in ks], "hm6",
            tip="tenor ou l exposant vaut un demi")
    p2.hline(V.TENOR_REF, "lvl")
    p2.label(0.55, V.TENOR_REF, "les trente jours de la règle", dx=0, dy=-8)

    b.annotation(0.0, 352.0,
                 "à gauche, le fond de la courbe est le meilleur cas "
                 "possible pour la règle, et il vaut encore " + _pct(e_opt, 0))
    b.annotation(0.0, 368.0,
                 "à droite, le ténor exact est inversement proportionnel à "
                 "la vitesse : la règle en désigne un, la surface un autre")
    b.annotation(0.0, 384.0,
                 "pour que les deux coïncident il faudrait une demi-vie de "
                 + _num(365.0 * math.log(2.0) / (458.6 / 30.0), 0)
                 + " jours, ce qui ne décrit pas un indice")
    b.annotation(0.0, 400.0,
                 "le dépôt balaie donc le paramètre au lieu de le choisir, "
                 "comme la taille de grappe du footprint")

    _source(b, "Le fond de la courbe de gauche est le contrôle de la "
               "section : il ne suffit pas de dire que la règle est fausse "
               "pour une vitesse donnée, il faut montrer qu'aucune vitesse ne "
               "la sauve. Le minimum est atteint et il reste haut, parce que "
               "le désaccord n'est pas de réglage mais de forme — une loi de "
               "puissance est droite en échelle logarithmique et la courbe du "
               "modèle a un genou. Le cadre de droite dit où ce genou tombe, "
               "et la ligne horizontale est l'ancrage que le guide a "
               "choisi ; les deux ne se croisent que pour une demi-vie de "
               "seize jours, ce qui décrirait une surface beaucoup plus "
               "nerveuse que celle d'un indice.")
    return b.render("L ecart maximal de la regle contre la vitesse de retour, "
                    "et le tenor ou elle est exacte.")


def fig_vg_relief_poids() -> str:
    """Le relief de l'écart de la règle, en vitesse de retour et en ténor."""
    z = [list(l) for l in V.surface_poids()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Véga · le relief de la pondération",
               "Ce que la règle en racine manque, partout sauf en un point",
               "hauteur : écart relatif")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(k, 0) for k in V.SURF_KAPPA],
             col_labels=[_num(j, 0) for j in V.SURF_TENOR],
             z_ticks=[(t, _pct(t, 0)) for t in _echine(zlo, zhi)],
             tip="{v:.1%} d ecart", zero=zlo)

    b.annotation(0.0, 408.0,
                 "arête gauche : retour à la moyenne · arête droite : ténor "
                 "· hauteur : écart de la règle au modèle")
    b.annotation(0.0, 424.0,
                 "la vallée qui traverse le relief est le lieu des ténors où "
                 "la règle tombe juste, un par vitesse de retour")
    b.annotation(0.0, 440.0,
                 "elle est étroite, et le relief remonte des deux côtés : "
                 "une règle exacte en un point est fausse ailleurs")

    _source(b, "Le relief porte l'écart relatif entre la règle en racine et "
               "le poids qu'une surface à retour à la moyenne impose. Sa "
               "forme est celle d'une vallée : pour chaque vitesse de retour "
               "il existe exactement un ténor où la règle est exacte, et "
               "l'écart croît de part et d'autre. Le coin du fond est celui "
               "d'un retour lent lu sur un ténor long, où la règle sous-pèse "
               "d'un facteur qui dépasse l'unité. Aucune coupe de ce relief "
               "n'est plate, et c'est le contenu de la section : la règle "
               "n'approxime pas mal une surface, elle en décrit une autre.")
    return b.render("Relief de l ecart de la regle en racine, en vitesse de "
                    "retour et en tenor.")


# ---------------------------------------------------------------------------
# IV. La bande de courbure
# ---------------------------------------------------------------------------


def fig_vg_bande() -> str:
    """La courbure contre la moneyness, et la bande où elle est négative.

    La bande est peinte **avant** la courbe : une bande posée après recouvre
    ce qu'elle commente, et le dépôt a déjà publié une loi unimodale qui se
    lisait bimodale pour cette raison.
    """
    b = _plate(500, "Véga · la bande de courbure",
               "La zone où le véga est linéaire, et sa largeur",
               "en milliemes, par point carré")

    # Le cadre est **zoomé sur la bande** : sur la plage entiere, la partie
    # negative vaut un quarantieme du maximum positif et se reduit a un
    # pixel — la planche affirmerait alors une chose qu elle ne montre pas.
    p1 = Panel(b, PX1, 92, PW, 214, title="La courbure, au ras de la monnaie",
               readout="en millièmes")
    ms = [0.955 + 0.0005 * i2 for i2 in range(181)]
    series = [("hm7", "", 30.0), ("hm5", "6 3", 90.0), ("hm3", "2 3", 365.0)]
    courbes = [(cls, dash, jj,
                [(m, V.volga(m * V.S_REF, V.S_REF, V.VOL_REF, jj / 365.0)
                  / 10000.0) for m in ms]) for cls, dash, jj in series]
    lo = min(y for _, _, _, c in courbes for _, y in c)
    hi = max(y for _, _, _, c in courbes for _, y in c)
    marge = 0.22 * (hi - lo)
    p1.domain(0.955, 1.045, lo - marge, hi + 2.0 * marge)
    p1.frame()
    lo_b, hi_b = V.bande_de_courbure(1.0)
    p1.band_x(lo_b, hi_b)
    p1.grid_y(_ticks(lo - marge, hi + 2.0 * marge, 0.0005),
              lambda v: _signed(1000.0 * v, 2), dx=36.0)
    p1.grid_x([0.96, 0.98, 1.0, 1.02, 1.04], lambda v: _num(v, 2),
              label="moneyness S/K")
    p1.hline(0.0, "lvl")
    for cls, dash, jj, c in courbes:
        p1.path(c, cls, dash=dash, tip=_num(jj, 0) + " jours")
    lo30, hi30 = V.bande_de_courbure(30.0 / 365.0)
    p1.vline(lo30, "lvl")
    p1.vline(hi30, "lvl")
    # Courts, et arretes avant les deux filets : le libelle long les
    # traversait tous les deux.
    p1.label(0.957, hi + 1.6 * marge, "teinté : l'année", dx=0, dy=0)
    p1.label(0.957, hi + 0.9 * marge, "filets : le mois", dx=0, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="La largeur de la bande",
               readout="% du spot")
    js = [3.0 * (1.06 ** i) for i in range(90)]
    js = [j for j in js if j <= 365.0]
    p2.domain(3.0, 365.0, 0.0005, 0.12, xlog=True, ylog=True)
    p2.frame()
    p2.grid_y([0.001, 0.01, 0.1], lambda v: _pct(v, 1), dx=38.0)
    p2.grid_x([3, 10, 30, 90, 365], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.path([(j, V.largeur_de_bande(j / 365.0)) for j in js], "hm6",
            tip="largeur de bande")
    for pas, cls in ((0.005, "hm3"), (0.01, "hm1")):
        p2.hline(pas, "lvl")
        p2.label(3.2, pas, "pas de grille à " + _pct(pas, 1), dx=0, dy=-7)

    b.legend(0.0, 352.0,
             [("hm7", "trente jours", ""),
              ("hm5", "quatre-vingt-dix jours", "6 3"),
              ("hm3", "un an", "2 3")],
             step=222.0, kind="line")
    b.annotation(0.0, 376.0,
                 "la courbure est négative dans une bande étroite autour de "
                 "la monnaie, et positive partout ailleurs")
    b.annotation(0.0, 392.0,
                 "sa largeur vaut " + _pct(V.largeur_de_bande(30.0 / 365.0), 2)
                 + " du spot à trente jours, et croît comme le produit de la "
                 "variance par le temps")
    b.annotation(0.0, 408.0,
                 "au-dessous de quinze jours, aucun strike d'une grille au "
                 "pas d'un pour cent n'y tombe")

    _source(b, "La bande est bornée par les deux racines de la courbure, "
               "donc par e moins sigma carré T sur deux et son inverse : une "
               "forme fermée sans paramètre libre. Le guide écrit que le véga "
               "est quasi linéaire près de la monnaie et convexe dans les "
               "ailes ; c'est exact, et la mesure dit à quel point « près de "
               "la monnaie » est près. Le cadre de droite pose la largeur "
               "contre deux pas de grille de strikes : aux échéances courtes "
               "la bande est plus fine que l'écart entre deux strikes cotés, "
               "de sorte qu'au sens de la courbure il n'existe pas d'option à "
               "la monnaie sur le tableau.")
    return b.render("La courbure contre la moneyness a trois echeances, et la "
                    "largeur de la bande contre l echeance.")


def fig_vg_relief_bande() -> str:
    """Le relief de la largeur de bande, en volatilité et en échéance."""
    z = [list(l) for l in V.surface_bande()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Véga · le relief de la bande",
               "Où la courbure change de signe, et sur quelle largeur",
               "hauteur : largeur en % du spot")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_pct(v, 0) for v in V.SURF_VOL],
             col_labels=[_num(j, 0) for j in V.SURF_ECHEANCE],
             z_ticks=[(t, _pct(t, 0)) for t in _echine(zlo, zhi)],
             tip="{v:.2%} du spot", zero=zlo)

    b.annotation(0.0, 408.0,
                 "arête gauche : volatilité · arête droite : jours à "
                 "l'échéance · hauteur : largeur de la bande")
    b.annotation(0.0, 424.0,
                 "la largeur vaut le produit de la variance par le temps : "
                 "le relief est donc un plan en coordonnées logarithmiques")
    b.annotation(0.0, 440.0,
                 "l'arête de devant est au ras du sol, et c'est là que vivent "
                 "les options que tout le monde négocie")

    _source(b, "Le relief est celui de sigma carré T, et sa forme n'a rien de "
               "surprenant ; ce qui compte est l'échelle. Au coin du fond — "
               "une volatilité de soixante pour cent sur un an — la bande "
               "occupe le tiers du spot, et la notion d'option à la monnaie a "
               "un sens large. Au coin du devant — vingt pour cent de "
               "volatilité à une semaine — elle occupe trois centièmes de "
               "pour cent, soit moins qu'un tick sur la plupart des grilles. "
               "Le mot « à la monnaie » ne désigne donc pas le même ensemble "
               "d'instruments selon l'endroit du relief où l'on se trouve, "
               "et le guide l'emploie sans le dire.")
    return b.render("Relief de la largeur de la bande de courbure negative, "
                    "en volatilite et en echeance.")


# ---------------------------------------------------------------------------
# V. Le seuil
# ---------------------------------------------------------------------------


def fig_vg_seuil() -> str:
    """Le seuil d'un vendeur de véga, en forme fermée et mesuré.

    À gauche le seuil contre la moneyness, par les deux routes. À droite
    l'espérance contre la dérive, dont le zéro **est** le seuil : c'est le
    contrôle de la section, et il montre où la forme fermée se trompe.
    """
    b = _plate(500, "Véga · le seuil d'un vendeur",
               "Ce qu'il faut d'implicite en baisse rien que pour ne rien perdre",
               _num(100 * V.NU_REF, 0) + " % de vol de vol")

    ms = [0.78 + 0.002 * i for i in range(221)]

    p1 = Panel(b, PX1, 92, PW, 214, title="Contre la moneyness",
               readout="points par mois")
    ferme = [(m, V.derive_equilibre(V.Ligne(-1.0, m, 90.0))) for m in ms]
    lo = min(y for _, y in ferme) * 1.35
    p1.domain(0.78, 1.22, lo, 0.12)
    p1.frame()
    p1.grid_y(_ticks(lo, 0.12, 0.5), lambda v: _signed(v, 1), dx=32.0)
    p1.grid_x([0.8, 0.9, 1.0, 1.1, 1.2], lambda v: _num(v, 1),
              label="moneyness S/K")
    p1.hline(0.0, "lvl")
    p1.path(ferme, "hm7", tip="forme fermee")
    for m in (0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15):
        p1.dot(m, V.derive_equilibre_exacte(m, 90.0), "hm3",
               "mesuré : " + _num(V.derive_equilibre_exacte(m, 90.0), 3),
               r=3.8)
    # Le nom se pose sous le sommet, ou le cadre est vide : pose en haut, il
    # se faisait traverser par le filet du zero et par la courbe elle-meme.
    p1.label(1.0, 0.0, "aucun seuil à la monnaie", dx=0, dy=20,
             anchor="middle")
    p1.label(0.79, lo * 0.92, "points : la mesure · trait : la forme fermée",
             dx=0, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="L'espérance contre la dérive",
               readout="points d'indice")
    ds = [-2.0 + 0.05 * i for i in range(81)]
    courbe = [(d, V._resume(V.simuler_vendeur(0.90, 90.0, V.NU_REF, d)).moyenne)
              for d in ds]
    lo2 = min(y for _, y in courbe) * 1.2
    hi2 = max(y for _, y in courbe) * 1.35
    p2.domain(-2.0, 2.0, lo2, hi2)
    p2.frame()
    p2.grid_y(_ticks(lo2, hi2, 0.1), lambda v: _signed(v, 1), dx=32.0)
    p2.grid_x([-2, -1, 0, 1, 2], lambda v: _signed(v, 0),
              label="dérive d'implicite, en points par mois")
    p2.hline(0.0, "lvl")
    p2.path(courbe, "hm6", tip="esperance mesuree")
    x = V.derive_equilibre_exacte(0.90, 90.0)
    p2.dot(x, 0.0, "hm3", "le seuil mesuré", r=4.6)
    p2.dot(V.derive_equilibre(V.Ligne(-1.0, 0.90, 90.0)), 0.0, "hm7",
           "le seuil en forme fermée", r=4.0)
    p2.label(-2.0, lo2, "l'aile basse à quatre-vingt-dix jours",
             dx=6, dy=-8)

    b.annotation(0.0, 376.0,
                 "le seuil est nul à la monnaie, où la courbure change de "
                 "signe, et croît vers les ailes des deux côtés")
    b.annotation(0.0, 392.0,
                 "il vaut " + _num(abs(V.derive_equilibre_exacte(0.90, 90.0)),
                                   2)
                 + " point par mois sur l'aile basse, et ne dépend d'aucune "
                 "vue sur la volatilité")
    b.annotation(0.0, 408.0,
                 "la forme fermée est du second ordre et le sous-estime de "
                 + _pct(abs(V.derive_equilibre_exacte(0.90, 90.0)
                            / V.derive_equilibre(V.Ligne(-1.0, 0.90, 90.0))
                            - 1.0), 0))

    _source(b, "Le seuil est l'identité du document rencontrée sur un "
               "quatrième objet : à espérance nulle sur la variation "
               "d'implicite, un vendeur perd la moitié de sa courbure fois la "
               "variance de cette variation, et il lui faut une baisse "
               "d'implicite de ce montant pour revenir à zéro. Comme le seuil "
               "de rentabilité de la dixième partie, il est une propriété de "
               "la position et non du marché. Le cadre de droite est le "
               "contrôle : la courbe y coupe le zéro, et l'abscisse de ce "
               "point est le seuil mesuré. La forme fermée le manque d'un "
               "sixième, parce que la variation d'un mois n'est pas petite "
               "devant l'implicite elle-même et que le troisième ordre pèse — "
               "le même défaut que la partie XIX a trouvé sur le mouvement "
               "d'équilibre, et au même endroit : là où la courbure est la "
               "plus grande.")
    return b.render("Le seuil d un vendeur de vega contre la moneyness, et "
                    "l esperance contre la derive d implicite.")


def fig_vg_relief_seuil() -> str:
    """Le relief du seuil, en vol de vol et en écart à la monnaie."""
    z = [list(l) for l in V.surface_seuil()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Véga · le relief du seuil",
               "Ce qu'une position réclame avant même d'avoir une vue",
               "hauteur : points par mois")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(n, 2) for n in V.SURF_NU],
             col_labels=[_pct(e, 0) for e in V.SURF_ECART],
             z_ticks=[(t, _num(t, 1)) for t in _echine(zlo, zhi)],
             tip="{v:.2f} point par mois", zero=zlo)

    b.annotation(0.0, 408.0,
                 "arête gauche : volatilité de la volatilité · arête droite : "
                 "écart à la monnaie · hauteur : seuil")
    b.annotation(0.0, 424.0,
                 "le seuil croît comme le carré de la vol de vol : c'est la "
                 "seule façon dont un terme de courbure peut entrer")
    b.annotation(0.0, 440.0,
                 "l'arête de devant est au sol, et c'est la monnaie : là, il "
                 "n'y a pas de seuil du tout")

    _source(b, "Le relief a deux propriétés que la table ne rend pas. La "
               "première est son arête de devant, posée au sol : à la monnaie "
               "la courbure change de signe et le seuil s'annule, de sorte "
               "qu'un livre qui compense une aile par une position à la "
               "monnaie compense un péage par un zéro. La seconde est sa "
               "pente le long de la volatilité de la volatilité, qui est "
               "quadratique : doubler ce paramètre — que ce dépôt ne peut pas "
               "mesurer et qu'il balaie donc — quadruple ce qu'il faut "
               "d'implicite en baisse pour ne rien gagner.")
    return b.render("Relief du seuil d un vendeur de vega, en volatilite de "
                    "la volatilite et en ecart a la monnaie.")


def fig_vg_loi() -> str:
    """La loi du vendeur, et la fréquence qui vaut exactement un demi.

    La zone gagnante est peinte avant l'histogramme. Elle porte la moitié de
    la masse, ni plus ni moins, parce que le prix d'une option est monotone
    en volatilité.
    """
    vals = V.simuler_vendeur(0.90, 90.0)
    r = V._resume(vals)
    # Le domaine se deduit de l echantillon, et il est **asymetrique** parce
    # que la loi l est : le gain d un vendeur est borne par la prime, sa perte
    # ne l est pas. Une fenetre symetrique coupait quatre pour cent de la
    # masse, toute dans la queue gauche — c est-a-dire exactement ce que la
    # section montre.
    lo, hi_x = min(vals) * 1.04, max(vals) * 1.12
    classes = 52
    pas = (hi_x - lo) / classes
    comptes = [0] * classes
    for x in vals:
        k = min(classes - 1, max(0, int((x - lo) / pas)))
        comptes[k] += 1
    dens = [(lo + (i2 + 0.5) * pas, comptes[i2] / len(vals) / pas)
            for i2 in range(classes)]

    b = _plate(494, "Véga · la loi du vendeur",
               "Une fois sur deux, exactement, et une espérance négative",
               _num(20000, 0) + " tirages")

    p1 = Panel(b, PX1, 92, PW, 214, title="Le résultat d'un mois",
               readout="densité")
    hi = max(d for _, d in dens) * 1.32
    p1.domain(lo, hi_x, 0.0, hi)
    p1.frame()
    p1.grid_y(_ticks(0.0, hi, hi / 3.0), lambda v: _num(v, 1), dx=30.0)
    p1.grid_x(_ticks(lo, hi_x, 1.0), lambda v: _signed(v, 0),
              label="résultat, en points d'indice")
    p1.band_x(0.0, hi_x)
    largeur = PW * pas / (hi_x - lo) * 0.86
    for centre, d in dens:
        if d > 0.0:
            p1.vbar(centre, 0.0, d, largeur, "hm6",
                    tip=_signed(centre, 2) + " : " + _num(d, 2))
    p1.vline(r.moyenne, "lvl")
    p1.vline(max(vals), "lvl")
    # Court, et cale sur sa propre ligne : le libelle long traversait le
    # filet de la moyenne, quinze pour cent de cadre plus a gauche.
    p1.label(max(vals), hi, "le plafond", dx=-6, dy=14, anchor="end")
    p1.label(lo, hi, "pas de plancher", dx=6, dy=14)
    p1.label(lo, hi, "moyenne " + _num(r.moyenne, 3), dx=6, dy=28)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Ce que porte le pire dixième", readout="part des pertes")
    parts = [0.005 * i for i in range(1, 101)]
    p2.domain(0.0, 0.5, 0.0, 1.05)
    p2.frame()
    p2.grid_y(_ticks(0.0, 1.0, 0.25), lambda v: _pct(v, 0), dx=34.0)
    p2.grid_x([0.0, 0.1, 0.2, 0.3, 0.4, 0.5], lambda v: _pct(v, 0),
              label="part des mois, du pire au moins mauvais")
    p2.path([(x, V.concentration(vals, x)) for x in parts], "hm7",
            tip="vendeur mesure")
    p2.path([(x, V.concentration_temoin(round(x, 4))) for x in parts],
            "hm3", dash="10 5", tip="temoin normal")
    p2.dot(0.05, V.concentration(vals, 0.05), "hm5",
           "les cinq pour cent de pires mois", r=4.2)
    p2.label(0.05, V.concentration(vals, 0.05),
             _pct(V.concentration(vals, 0.05), 0) + " des pertes",
             dx=9, dy=4)

    b.annotation(0.0, 352.0,
                 "la zone teintée porte les résultats gagnants, et elle porte "
                 "exactement la moitié de la masse")
    b.annotation(0.0, 368.0,
                 "le prix d'une option est monotone en volatilité : un "
                 "vendeur gagne quand l'implicite baisse, un point c'est tout")
    b.annotation(0.0, 384.0,
                 "son gain est plafonné par la prime, sa perte ne l'est "
                 "pas, et la moyenne s'installe à gauche du zéro")
    b.annotation(0.0, 400.0,
                 "et les pertes ne sont pas plus concentrées que celles "
                 "d'une gaussienne : un point d'écart")

    _source(b, "Le guide écrit que vendre du véga paie la plupart du temps. "
               "La mesure corrige : la fréquence vaut un demi, exactement, à "
               "toute moneyness et à toute volatilité de la volatilité, parce "
               "que le prix d'une option croît avec la volatilité sans "
               "exception et qu'un vendeur gagne donc précisément quand "
               "l'implicite baisse. Ce qui paie la plupart du temps n'est pas "
               "la vente de véga : c'est le portage, c'est-à-dire une dérive "
               "qu'il faut supposer et que la section suivante fait payer. "
               "La loi montrée ici est celle d'un vendeur sans aucune vue, et "
               "elle perd en moyenne ce que la courbure lui prend.")
    return b.render("La loi du resultat d un vendeur de vega et sa frequence "
                    "de gain contre la volatilite de la volatilite.")


# ---------------------------------------------------------------------------
# VI. La preuve, et le décompte
# ---------------------------------------------------------------------------


def fig_vg_preuve() -> str:
    """Les années requises contre l'avantage, et ce que la fréquence en dit.

    L'avantage se compte **au-delà du seuil**, parce que la baisse qui ramène
    l'espérance à zéro n'est pas un gain, c'est un péage.
    """
    b = _plate(500, "Véga · le budget d'information",
               "Le péage d'abord, l'avantage ensuite, et il se démontre",
               "à une position par mois")

    p1 = Panel(b, PX1, 92, PW, 214, title="Les années requises",
               readout="années")
    p1.domain(0.18, 3.0, 0.2, 200.0, xlog=True, ylog=True)
    p1.frame()
    p1.grid_y([1, 10, 100], _dec, dx=34.0)
    p1.grid_x([0.25, 0.5, 1.0, 2.0], lambda v: _num(v, 2),
              label="avantage au-delà du seuil, en points par mois")
    ref = V.campagne(1.0)
    xs = [0.2 * (1.04 ** i) for i in range(80)]
    xs = [x for x in xs if x <= 2.8]
    p1.path([(x, ref.annees / x / x) for x in xs], "hm4", dash="6 3",
            tip="loi en carre inverse")
    for e in V.EXCES:
        c = V.campagne(e)
        p1.dot(e, c.annees, "hm7",
               _num(e, 2) + " point : " + _num(c.annees, 1) + " ans", r=4.2)

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce que la fréquence en montre",
               readout="fréquence de gain")
    p2.domain(0.0, 2.4, 0.45, 0.80)
    p2.frame()
    p2.grid_y(_ticks(0.45, 0.80, 0.10), lambda v: _pct(v, 0), dx=36.0)
    p2.grid_x([0.0, 0.5, 1.0, 1.5, 2.0], lambda v: _num(v, 1),
              label="avantage au-delà du seuil, en points par mois")
    p2.hline(0.5, "lvl")
    pts = [(0.0, V._resume(V.simuler_vendeur(0.90, 90.0, V.NU_REF,
                                             V.derive_equilibre_exacte(
                                                 0.90, 90.0))).taux)]
    pts += [(e, V.campagne(e).taux) for e in V.EXCES]
    p2.path(pts, "hm6", tip="frequence de gain")
    for x, y in pts:
        p2.dot(x, y, "hm7", _num(x, 2) + " point : " + _pct(y, 1), r=4.0)
    p2.label(0.05, 0.5, "au seuil, un demi", dx=0, dy=14)

    b.legend(0.0, 352.0,
             [("hm7", "campagnes simulées", ""),
              ("hm4", "loi en carré inverse", "6 3"),
              ("hm6", "fréquence de gain", "")],
             step=222.0, kind="line")
    b.annotation(0.0, 376.0,
                 "un point d'avantage par mois demande " + _num(ref.annees, 1)
                 + " ans, et un demi-point quatre fois plus")
    b.annotation(0.0, 392.0,
                 "c'est le budget le plus lourd des quatre parties "
                 "d'options, et pour une raison simple")
    b.annotation(0.0, 408.0,
                 "un résultat gouverné par une variation d'implicite a "
                 "une dérive minuscule devant son bruit")

    _source(b, "L'avantage se compte au-delà du seuil de la position, et "
               "c'est la seule définition honnête : la baisse d'implicite qui "
               "ramène l'espérance à zéro n'est pas un avantage, c'est un "
               "péage, et un vendeur qui l'encaisse croit gagner ce qu'il ne "
               "fait que rendre. Le nombre d'années se lit à côté de ceux des "
               "trois parties précédentes — quatre cent soixante-quatorze "
               "décisions pour une géométrie intrajournalière, cinquante-cinq "
               "expirations pour un point de prime de variance — et il dit la "
               "même chose une quatrième fois, en plus dur. Le cadre de "
               "droite est la raison pour laquelle on s'en aperçoit si "
               "tard : la fréquence de gain monte à peine, et un vendeur qui "
               "a un avantage réel ne le voit pas passer dans son taux de "
               "réussite.")
    return b.render("Les annees requises pour etablir un portage de "
                    "volatilite, et la frequence de gain correspondante.")


def fig_vg_relief_preuve() -> str:
    """Le relief des années requises, en avantage et en vol de vol."""
    z = [[math.log10(v) for v in l] for l in V.surface_preuve()]
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Véga · le relief de la preuve",
               "Ce que coûte un portage qu'on n'a pas rendu grand",
               "hauteur logarithmique : années")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(n, 2) for n in V.SURF_NU_PREUVE],
             col_labels=[_num(e, 2) for e in V.SURF_EXCES],
             z_ticks=[(math.log10(t), _num(t, 0))
                      for t in (1.0, 10.0, 100.0, 1000.0)
                      if zlo <= math.log10(t) <= zhi],
             tip="{v:.0f} annees", zero=zlo,
             tip_value=lambda v: 10.0 ** v)

    b.annotation(0.0, 408.0,
                 "arête gauche : volatilité de la volatilité · arête droite : "
                 "avantage · hauteur : années requises")
    b.annotation(0.0, 424.0,
                 "les deux axes agissent au carré et en sens contraire, ce "
                 "qui donne au relief sa pente régulière")
    b.annotation(0.0, 440.0,
                 "le coin du fond se compte en siècles, et il décrit une aile "
                 "vendue sur une surface nerveuse")

    _source(b, "La hauteur porte un logarithme parce que la grandeur "
               "parcourt trois ordres et demi ; l'infobulle publie les années "
               "elles-mêmes. Le relief n'a pas de plateau et pas de vallée : "
               "c'est un plan incliné, parce que les deux axes entrent tous "
               "deux au carré — l'avantage au dénominateur, la volatilité de "
               "la volatilité au numérateur par la dispersion qu'elle crée. "
               "Rien dans ce relief ne descend sous l'année, et une bonne "
               "part se compte en décennies.")
    return b.render("Relief des annees requises pour etablir un portage de "
                    "volatilite, en vol de vol et en avantage.")


def fig_vg_reste() -> str:
    """Le décompte des neuf affirmations, et le cumul des quatre parties."""
    aff = V.affirmations()
    compte = V.compte_par_grandeur()
    ordre = sorted(compte, key=lambda g: (-compte[g], g))

    b = _plate(470, "Véga · le décompte",
               "Vingt-huit affirmations, et aucune ne donne un sens",
               _num(len(aff), 0) + " ici")

    p1 = Panel(b, PX1, 92, PW, 214, title="Ce qu'elles déplacent",
               readout="affirmations")
    p1.domain(0.0, 6.0, -0.6, len(ordre) - 0.4)
    p1.frame()
    p1.grid_x(_ticks(0.0, 6.0, 2.0), lambda v: _num(v, 0))
    for i, g in enumerate(ordre):
        y = len(ordre) - 1 - i
        cls = {"la direction": "hm7", "rien": "hm1"}.get(g, "hm5")
        p1.hbar(y, 0.0, compte[g], 13.0, cls,
                tip=g + " : " + _num(compte[g], 0))
        p1.label(0.0, y + 0.34, g, dx=4, dy=0)
        p1.label(compte[g], y, _num(compte[g], 0), dx=7, dy=4)

    p2 = Panel(b, PX2, 92, PW, 214, title="Les quatre parties",
               readout="affirmations")
    fam = V.familles()
    haut = max(n for _, n in fam) * 1.35
    p2.domain(0.0, haut, -0.6, len(fam) - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, haut, 3.0), lambda v: _num(v, 0))
    for i, (nom, total) in enumerate(fam):
        y = len(fam) - 1 - i
        p2.hbar(y, 0.0, total, 11.0, "hm3", tip=nom)
        p2.label(0.0, y + 0.32, nom, dx=4, dy=0)
        p2.label(total, y, _num(total, 0), dx=7, dy=4)

    b.legend(0.0, 352.0,
             [("hm7", "touche à la direction"),
              ("hm5", "l'horloge ou le risque"),
              ("hm1", "ne déplace rien"),
              ("hm3", "les totaux, à droite")],
             step=166.0)
    b.annotation(0.0, 376.0,
                 _num(compte.get("le risque", 0), 0) + " affirmations "
                 "déplacent le risque, " + _num(compte.get("rien", 0), 0)
                 + " ne déplacent rien, une l'horloge")
    b.annotation(0.0, 392.0,
                 "la seule qui touche à la direction dit que vendre du véga "
                 "paie, et la mesure la corrige")
    b.annotation(0.0, 408.0,
                 "sur les " + _num(sum(n for _, n in fam), 0)
                 + " affirmations des quatre parties d'options, aucune ne "
                 "donne un sens")

    _source(b, "Le décompte se lit dans l'identité du document : une "
               "affirmation déplace l'horloge, le risque, ou la direction. "
               "Les quatre parties consacrées aux options ont examiné vingt-"
               "huit affirmations venues de guides extérieurs, et le compte "
               "est toujours le même. Ce n'est pas un reproche adressé à ces "
               "guides — ils décrivent correctement des grandeurs qui "
               "existent, et le dernier va jusqu'à nommer la circularité de "
               "la sienne, ce que ce dépôt a mis longtemps à faire pour la "
               "sienne propre. C'est un fait sur ce que ces grandeurs sont : "
               "des propriétés de la géométrie, de l'horloge et du risque, "
               "jamais du sens.")
    return b.render("Le decompte des affirmations par ce qu elles deplacent, "
                    "et le cumul des quatre parties d options.")


def render_all() -> dict[str, str]:
    """Les quinze planches, dans l'ordre du document."""
    return {
        "vgechelle": fig_vg_echelle(),
        "vgcolline": fig_vg_colline(),
        "vgmodes": fig_vg_modes(),
        "vgcourbure": fig_vg_courbure(),
        "vgponderation": fig_vg_ponderation(),
        "vgkappa": fig_vg_kappa(),
        "vgreliefp": fig_vg_relief_poids(),
        "vgbande": fig_vg_bande(),
        "vgreliefb": fig_vg_relief_bande(),
        "vgseuil": fig_vg_seuil(),
        "vgreliefs": fig_vg_relief_seuil(),
        "vgloi": fig_vg_loi(),
        "vgpreuve": fig_vg_preuve(),
        "vgreliefpr": fig_vg_relief_preuve(),
        "vgreste": fig_vg_reste(),
    }
