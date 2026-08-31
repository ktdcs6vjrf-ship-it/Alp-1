"""Les planches des cinq disciplines empruntées.

Quinze planches, sept en deux dimensions et six en relief, plus les deux qui
ouvrent et ferment la partie. L'ordre est celui de l'argument, pas celui des
disciplines : d'abord ce que l'unité d'observation permet, puis chaque
discipline avec sa loi nulle, enfin le tableau de ce qui transfère.

Chaque relief obéit à la règle du dépôt — maximum au fond de la projection —
et chaque plan porte sa loi nulle dessinée, jamais seulement citée. Une
planche qui montrerait un motif sans montrer ce à quoi il se compare
n'apprendrait rien qu'un joli tracé.
"""

from __future__ import annotations

import math

from . import emprunts as E
from .figdisc import W, _plate, _scale_legend, _source, _surface
from .figterm import Board, Panel, _num, _signed


def _pct(v: float, nd: int = 0) -> str:
    return _num(100.0 * v, nd) + " %"


#: Largeur d'un cadre quand la planche en porte deux côte à côte.
PW = (W - 74.0) / 2.0 - 30.0
PX1 = 74.0
PX2 = 74.0 + (W - 74.0) / 2.0


# ---------------------------------------------------------------------------
# I. L'unité d'observation
# ---------------------------------------------------------------------------


def fig_emp_unite() -> str:
    """Ce que le pas de temps change, et ce qu'il ne change pas.

    Le cadre de gauche est celui qu'on attend : plus l'unité est fine, plus
    l'effet détectable est petit, et la pente est la racine carrée. Le cadre
    de droite est celui qui compte : la même exigence, écrite en Sharpe
    annuel, ne dépend plus que du nombre d'années. Les six unités s'y empilent
    sur une seule verticale.
    """
    b = _plate(430, "Unité d'observation · ce qui décide",
               "L'effet minimal détectable, et sa traduction en Sharpe",
               _num(E.HORIZON_ANS, 0) + " ans d'archive")

    p1 = Panel(b, PX1, 92, PW, 214, title="Effet détectable sur une unité",
               readout="d minimal")
    p1.domain(20.0, 1.5e6, 0.002, 1.0, xlog=True, ylog=True)
    p1.frame()
    p1.grid_y([0.002, 0.01, 0.05, 0.2, 1.0], lambda v: _num(v, 3), dx=44.0)
    p1.grid_x([100.0, 1e4, 1e6], lambda v: _num(v, 0))
    courbe = []
    n = 20.0
    while n <= 1.5e6:
        courbe.append((n, E.FACTEUR / math.sqrt(n)))
        n *= 1.12
    p1.path(courbe, "hm5", tip="d = 2,802 sur racine de n")
    for u in E.UNITES:
        p1.dot(u.n, u.d_min, "hm7",
               u.nom + " : n = " + _num(u.n, 0) + ", d = " + _num(u.d_min, 4),
               r=3.6)
    p1.label(E.UNITES[0].n, E.UNITES[0].d_min, "la minute",
             dx=-6, dy=-8, anchor="end")
    p1.label(E.UNITES[-1].n, E.UNITES[-1].d_min, "le relevé réel",
             dx=8, dy=4)

    p2 = Panel(b, PX2, 92, PW, 214, title="La même exigence, en Sharpe annuel",
               readout="Sharpe minimal")
    p2.domain(0.0, 7.0, 0.0, 7.5)
    p2.frame()
    p2.grid_y([0.0, 2.0, 4.0, 6.0], lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([0.5, 1.5, 2.5, 3.5, 4.5, 5.5],
              lambda v: ["min", "épis", "extr", "déci", "séan", "relevé"]
              [int(v)])
    for i, u in enumerate(E.UNITES):
        p2.vbar(i + 0.5, 0.0, u.sharpe_min, 26.0,
                "hm7" if u.cle == "releve" else "hm4",
                tip=u.nom + " : Sharpe minimal " + _num(u.sharpe_min, 2))
    p2.hline(E.SHARPE_REF, "lvl")
    p2.label(6.9, E.SHARPE_REF, "Sharpe de référence", dx=0, dy=-7,
             anchor="end")
    p2.label(0.5, E.UNITES[0].sharpe_min, _num(E.UNITES[0].sharpe_min, 2),
             dx=0, dy=-9, anchor="middle")

    b.annotation(0.0, 336.0,
                 "cinq unités, cinq exigences très différentes à gauche, une "
                 "seule et même exigence à droite")
    b.annotation(0.0, 352.0,
                 "seule la dernière barre sort du lot, et pour une raison qui "
                 "n'est pas le pas de temps :")
    b.annotation(0.0, 368.0,
                 "le relevé ne compte que " + _num(E.RELEVE_REEL, 0)
                 + " décisions, soit deux mois")

    _source(b, "Effet minimal détectable à " + _pct(E.ALPHA)
            + " et " + _pct(E.PUISSANCE) + " de puissance. L'exigence par "
              "unité parcourt quatre ordres de grandeur ; annualisée, elle "
              "vaut " + _num(E.FACTEUR, 3) + " divisé par la racine du nombre "
              "d'années, et rien d'autre. Choisir un pas de temps plus fin "
              "n'achète donc aucune preuve — c'est un résultat, pas une "
              "limitation de la méthode employée ici, et il vaut pour tout "
              "estimateur sans mémoire.")
    return b.render("Effet minimal detectable par unite d observation, et la "
                    "meme exigence traduite en Sharpe annuel.")


def fig_emp_puissance() -> str:
    """La puissance d'un test de Sharpe, sur deux axes et rien d'autre.

    Le relief ne contient ni instrument, ni loi de rendement, ni géométrie :
    seulement le Sharpe vrai et le nombre d'années. C'est ce qui le rend
    utilisable comme borne — aucune méthode ne peut le contourner, et une
    méthode qui prétendrait le faire aurait un défaut ailleurs.
    """
    z = E.surface_puissance()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Unité d'observation · la puissance",
               "Ce qu'il faut d'années pour voir un Sharpe donné",
               "hauteur : probabilité de le détecter")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(s, 1) for s in E.SURF_SHARPE],
             col_labels=[_num(t, 0) for t in E.SURF_ANNEES],
             z_ticks=[(t, _pct(t)) for t in (0.2, 0.5, 0.8)],
             tip="{v:.3f}", zero=zlo)

    b.annotation(0.0, 408.0,
                 "arête gauche : Sharpe annuel vrai · arête droite : années "
                 "d'observation")
    b.annotation(0.0, 424.0,
                 "un Sharpe de " + _num(E.SHARPE_REF, 0) + " demande "
                 + _num(E.annees_pour(E.SHARPE_REF), 1) + " ans pour être vu "
                 "quatre fois sur cinq")
    b.annotation(0.0, 440.0,
                 "le versant est raide en années, doux en Sharpe : le temps "
                 "achète la preuve mieux que le talent")

    _source(b, "Puissance d'un test bilatéral au risque " + _pct(E.ALPHA)
            + " : la probabilité de conclure quand la conclusion est vraie. "
              "Le relief est de l'arithmétique pure et ne se discute pas ; ce "
              "qui se discute est le point où l'on se tient dessus. Un "
              "opérateur qui revendique un Sharpe de deux et deux ans de "
              "relevé se tient dans la région haute, un opérateur qui "
              "revendique un demi et deux ans se tient dans le creux — et "
              "aucune analyse de ses trades ne l'en sortira.")
    return b.render("Surface de puissance sur le plan du Sharpe annuel vrai "
                    "et du nombre d annees observees.")


# ---------------------------------------------------------------------------
# II. L'analyse de survie
# ---------------------------------------------------------------------------


def fig_emp_survie() -> str:
    """La courbe de survie d'un sommet, et le risque instantané qui la porte.

    À gauche, quatre réponses à la même question, dont deux fausses. La
    censure n'est pas un détail de méthode : écarter les observations qui
    n'ont pas fini raccourcit la durée moyenne des quatre cinquièmes.

    À droite, le fait que la table ne peut pas montrer — le risque
    instantané n'est pas maximal quand le sommet vient d'être posé. Chaque
    courbe porte son pic, et les pics tombent sur `d²/u*²σ²`.
    """
    obs = E.observations()
    courbe = E.kaplan_meier(list(obs))
    exact = [(m, E.survie_moyenne(float(m))) for m in range(0, 271, 5)]

    b = _plate(430, "Analyse de survie · le sommet du jour",
               "Combien de temps un extrême tient, et quand il risque le plus",
               _num(E.N_SEANCES_SURVIE, 0) + " séances sans dérive")

    p1 = Panel(b, PX1, 92, PW, 214, title="Survie du sommet",
               readout="part encore intacte")
    p1.domain(0.0, E.RESTE, 0.0, 1.0)
    p1.frame()
    p1.grid_y([0.0, 0.25, 0.5, 0.75, 1.0], lambda v: _pct(v), dx=40.0)
    p1.grid_x([0.0, 90.0, 180.0, 270.0], lambda v: _num(v, 0),
              label="minutes écoulées")
    p1.path([(t, s) for t, s in courbe], "hm5", tip="Kaplan-Meier")
    p1.path(exact, "hm2", dash="5 3", tip="forme fermée moyennée")
    gardes = [o for o in obs if not o.censure]
    med_ignore = sorted(o.duree for o in gardes)[len(gardes) // 2]
    p1.hline(0.5, "lvl")
    p1.dot(E._mediane(courbe), 0.5, "hm7",
           "médiane Kaplan-Meier : " + _num(E._mediane(courbe), 0) + " min",
           r=4.2)
    p1.dot(med_ignore, 0.5, "hm0",
           "médiane si l'on écarte les censurés : " + _num(med_ignore, 0)
           + " min", r=4.2)
    p1.label(med_ignore, 0.5, "en écartant les censurés", dx=6, dy=16)
    p1.label(E._mediane(courbe), 0.5, "Kaplan-Meier", dx=-6, dy=-8,
             anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Risque instantané",
               readout="par heure")
    pics = []
    series = []
    for k, d in enumerate((4.0, 9.0, 16.0)):
        pts = [(m, 60.0 * E.hasard_nul(d, float(m)))
               for m in range(1, 121)]
        series.append((d, pts))
        pics.append((d, E.pic_hasard(d), 60.0 * E.hasard_nul(d, E.pic_hasard(d))))
        _ = k
    haut = max(v for _, pts in series for _, v in pts)
    p2.domain(0.0, 120.0, 0.0, haut * 1.15)
    p2.frame()
    p2.grid_y([0.0, 0.5, 1.0, 1.5], lambda v: _num(v, 1), dx=26.0)
    p2.grid_x([0.0, 30.0, 60.0, 90.0, 120.0], lambda v: _num(v, 0),
              label="minutes écoulées")
    for (d, pts), cls in zip(series, ("hm7", "hm5", "hm3")):
        p2.path(pts, cls, tip="sommet à " + _num(d, 0) + " points")
    for (d, m, h), cls in zip(pics, ("hm7", "hm5", "hm3")):
        p2.dot(m, h, cls, "pic à " + _num(m, 0) + " min pour un sommet à "
               + _num(d, 0) + " points", r=3.8)
    p2.label(pics[1][1], pics[1][2], "pic en d² sur " + _num(E.coef_pic(), 2) + "σ²", dx=8, dy=-6)

    b.legend(PX2, 352.0,
             [("hm7", "sommet à 4 pt"), ("hm5", "à 9 pt"), ("hm3", "à 16 pt")],
             step=96.0, kind="line")
    b.legend(PX1, 352.0,
             [("hm5", "Kaplan-Meier"), ("hm2", "forme fermée", "5 3")],
             step=118.0, kind="line")
    b.annotation(0.0, 374.0,
                 "les deux courbes de gauche se superposent : l'estimateur "
                 "sans hypothèse retrouve la loi fermée")

    _source(b, "Sommet relevé à la " + _num(E.T0, 0) + "e minute, suivi "
              "jusqu'à la clôture ou jusqu'à la sortie de l'opérateur. La "
              "courbe pleine est Kaplan-Meier, qui traite la censure ; la "
              "tiretée est la forme fermée moyennée sur les distances "
              "observées, qui sert de vérité. Le point clair marque ce que "
              "donne la facilité la plus répandue — ne garder que les cas "
              "résolus — et il tombe à "
            + _num(med_ignore, 0) + " minutes contre "
            + _num(E.mediane_exacte(), 0) + ". À droite, le risque "
              "instantané : il monte, culmine, puis décroît en un sur deux "
              "fois le temps écoulé. Un sommet vieux est un sommet sûr, mais "
              "un sommet jeune ne l'est pas non plus.")
    return b.render("Courbe de survie d un sommet de seance et taux de "
                    "hasard instantane pour trois distances.")


def fig_emp_calibration() -> str:
    """Une probabilité annoncée vaut ce que vaut sa calibration.

    Le cadre de gauche est l'épreuve : on annonce, on range par annonce, on
    compte. La diagonale est la seule chose à regarder. Deux annonces y sont
    posées — celle du temps continu, qui dérive systématiquement, et celle
    corrigée du pas d'observation, qui ne dérive plus.

    Le cadre de droite dit d'où vient l'annonce : la distance du prix à son
    sommet, seule entrée de la formule.
    """
    cal = E.calibration()
    obs = E.observations()

    b = _plate(446, "Analyse de survie · la calibration",
               "Ce qui est annoncé, et ce qui arrive",
               _num(len(obs), 0) + " séances rangées par annonce")

    p1 = Panel(b, PX1, 92, PW, 214, title="Annoncé contre observé",
               readout="la diagonale est la cible")
    p1.domain(0.0, 0.9, 0.0, 0.9)
    p1.frame()
    p1.grid_y([0.0, 0.3, 0.6, 0.9], lambda v: _pct(v), dx=40.0)
    p1.grid_x([0.0, 0.3, 0.6, 0.9], lambda v: _pct(v))
    p1.path([(0.0, 0.0), (0.9, 0.9)], "hm1", dash="4 3",
            tip="calibration parfaite")
    p1.path([(pc, f) for pc, _, f, _ in cal], "hm3",
            tip="annonce en temps continu")
    p1.path([(pm, f) for _, pm, f, _ in cal], "hm6",
            tip="annonce corrigée du pas d'observation")
    for pm, _, f, _ in [(c[1], c[0], c[2], c[3]) for c in cal]:
        p1.dot(pm, f, "hm6", "annoncé " + _pct(pm, 1) + ", observé "
               + _pct(f, 1), r=3.2)

    p2 = Panel(b, PX2, 92, PW, 214, title="D'où vient l'annonce",
               readout="distance du prix à son sommet")
    ds = sorted(o.distance for o in obs)
    seaux = [0] * 24
    hautd = ds[int(0.99 * len(ds))]
    for d in ds:
        i = int(d / hautd * 24)
        if 0 <= i < 24:
            seaux[i] += 1
    dens = [c / len(ds) for c in seaux]
    p2.domain(0.0, hautd, 0.0, max(dens) * 1.15)
    p2.frame()
    p2.grid_y([t for t in (0.0, 0.05, 0.10, 0.15) if t <= max(dens) * 1.15],
              lambda v: _pct(v, 0), dx=34.0)
    p2.grid_x([0.0, 10.0, 20.0, 30.0], lambda v: _num(v, 0) + " pt")
    for i, v in enumerate(dens):
        p2.vbar((i + 0.5) * hautd / 24.0, 0.0, v, 8.0, "hm4",
                tip=_num((i + 0.5) * hautd / 24.0, 1) + " pt : " + _pct(v, 1))
    med = ds[len(ds) // 2]
    p2.vline(med, "lvl")
    p2.label(med, max(dens) * 0.9, "médiane " + _num(med, 1) + " pt", dx=7)
    p2.label(hautd, max(dens) * 0.62, "1 % au-delà", dx=-6, dy=0,
             anchor="end")

    b.legend(PX1, 336.0,
             [("hm3", "temps continu"), ("hm6", "corrigé du pas"),
              ("hm1", "calibration parfaite", "4 3")],
             step=132.0, kind="line")
    b.annotation(0.0, 358.0,
                 "la courbe du temps continu passe systématiquement "
                 "au-dessus de la diagonale :")
    b.annotation(0.0, 374.0,
                 "une barrière surveillée à la minute est franchie moins "
                 "souvent qu'une barrière continue")

    _source(b, "Chaque séance reçoit sa probabilité annoncée que son sommet "
              "tienne jusqu'à la clôture, puis les séances sont rangées par "
              "cette probabilité et la fréquence réelle est relevée par "
              "tranche. La correction du pas d'observation vaut "
            + _num(E.BETA_CONTINUITE, 3) + " fois l'écart-type d'une minute, "
              "soit " + _num(E.BETA_CONTINUITE * E.SIGMA, 2) + " point ; elle "
              "n'est pas ajustée, c'est une constante universelle. Ce que la "
              "planche établit n'est pas que la formule marche — elle est "
              "exacte — mais qu'elle marche sans rien savoir du marché : une "
              "lecture qui se contente de la retrouver n'a donc rien "
              "démontré.")
    return b.render("Courbe de calibration de la probabilite de survie "
                    "annoncee, et loi de la distance au sommet.")


def fig_emp_hasard() -> str:
    """Le risque instantané sur tout le plan distance × temps écoulé.

    La crête du relief est la courbe `m = d²/u*²σ²`. Elle ne se voit dans
    aucune colonne d'une table parce qu'elle vit dans le plan : à chaque
    distance correspond un instant de danger maximal, et cet instant recule
    comme le carré de la distance.
    """
    z = E.surface_hasard()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Analyse de survie · le relief du risque",
               "Quand un sommet est le plus menacé, et de combien",
               "hauteur : part du risque maximal")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(d, 0) + " pt" for d in E.SURF_DISTANCE],
             col_labels=[_num(m, 0) for m in E.SURF_MINUTES],
             z_ticks=[(t, _pct(t)) for t in (0.0, 0.5, 1.0)],
             tip="{v:.2f} de son maximum", zero=zlo)

    b.annotation(0.0, 408.0,
                 "arête gauche : distance du prix à son sommet · arête "
                 "droite : minutes écoulées depuis qu'il est posé")
    b.annotation(0.0, 424.0,
                 "l'arête traverse le plan : chaque distance a son instant de "
                 "danger maximal, et il recule en d²")
    b.annotation(0.0, 440.0,
                 "un sommet à " + _num(9.0, 0) + " points est le plus menacé "
                 "à la " + _num(E.pic_hasard(9.0), 0) + "e minute, un sommet "
                 "à " + _num(17.0, 0) + " points à la "
                 + _num(E.pic_hasard(17.0), 0) + "e")

    _source(b, "Forme fermée φ(u)·u/(m·(2Φ(u)−1)) avec u = d/σ√m, tracée "
              "sans aucune simulation, puis rapportée à son maximum distance "
              "par distance. La normalisation n'est pas un choix "
              "d'esthétique : le risque absolu parcourt deux ordres de "
              "grandeur sur cette boîte, et le relief brut se réduisait à une "
              "aiguille au coin des sommets proches, où l'arête que la "
              "section décrit n'était pas visible. Les niveaux absolus sont "
              "dans la table. Ce relief est la raison pour laquelle une règle "
              "du type « si le haut tient dix minutes, il tiendra » n'a pas de "
              "sens général : dix minutes est très long pour un sommet à deux "
              "points et très court pour un sommet à quinze.")
    return b.render("Surface du taux de hasard d un sommet sur le plan de la "
                    "distance et du temps ecoule.")


# ---------------------------------------------------------------------------
# III. L'auto-excitation
# ---------------------------------------------------------------------------


def fig_emp_hawkes() -> str:
    """L'auto-excitation, montrée puis mesurée.

    À gauche, la même durée et le même taux moyen, deux fois : le processus
    auto-excitant et son Poisson témoin. Les deux fenêtres sont les **plus
    chargées** de chacun des deux processus — la comparaison est donc extrême
    contre extrême, et non amas contre moyenne, ce qui serait truqué.

    À droite, la mesure qui remplace l'impression : le taux d'événements après
    un événement, contre la forme fermée et contre le un plat du Poisson.
    """
    largeur = 60.0
    inst = E.hawkes()
    taux = len(inst) / E.T_HAWKES
    poi = E.poisson_temoin(taux, E.T_HAWKES)
    t_h = E.fenetre_temoin(largeur)
    t_p = E.fenetre_temoin(largeur, poi)
    ev_h = [t - t_h for t in inst if t_h <= t < t_h + largeur]
    ev_p = [t - t_p for t in poi if t_p <= t < t_p + largeur]
    chemin = [(t - t_h, v) for t, v in E.chemin_intensite(t_h, t_h + largeur)]

    b = _plate(462, "Auto-excitation · le processus",
               "Le même taux moyen, et deux mondes différents",
               _num(largeur, 0) + " minutes, fenêtres les plus chargées")

    p1 = Panel(b, PX1, 92, PW, 214, title="Intensité et instants",
               readout="événements par minute")
    haut = max(v for _, v in chemin) * 1.2
    p1.domain(0.0, largeur, -0.55 * haut, haut)
    p1.frame()
    p1.grid_y([0.0, 2.0, 4.0, 6.0], lambda v: _num(v, 0), dx=26.0)
    p1.grid_x([0.0, 20.0, 40.0, 60.0], lambda v: _num(v, 0),
              label="minutes")
    p1.hline(0.0, "lvl")
    p1.path(chemin, "hm6", tip="intensité conditionnelle du Hawkes")
    p1.path([(0.0, taux), (largeur, taux)], "hm1", dash="4 3",
            tip="taux moyen commun aux deux processus")
    for t in ev_h:
        p1.vbar(t, -0.10 * haut, -0.02 * haut, 1.6, "hm7")
    for t in ev_p:
        p1.vbar(t, -0.42 * haut, -0.34 * haut, 1.6, "hm3")
    p1.label(1.0, -0.22 * haut, _num(len(ev_h), 0) + " événements, Hawkes",
             dx=0, dy=0)
    p1.label(1.0, -0.52 * haut, _num(len(ev_p), 0) + " événements, Poisson",
             dx=0, dy=0)
    p1.label(33.0, haut * 0.62, "taux moyen commun", dx=0, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce qui suit un événement",
               readout="taux rapporté au fond")
    mes = []
    fer = []
    for lo, hi in E.APRES:
        milieu = 0.5 * (lo + hi)
        mes.append((milieu, E.reponse_mesuree(inst, (lo, hi)) / taux))
        fer.append((milieu, E.reponse_moyenne(lo, hi, lam_bar=taux) / taux))
    p2.domain(0.0, 30.0, 0.8, max(v for _, v in mes) * 1.12)
    p2.frame()
    p2.grid_y([1.0, 2.0, 3.0, 4.0], lambda v: _num(v, 0) + " ×", dx=32.0)
    p2.grid_x([0.0, 10.0, 20.0, 30.0], lambda v: _num(v, 0),
              label="minutes après un événement")
    lisse = [(t / 4.0, E.reponse_fermee(t / 4.0, lam_bar=taux) / taux)
             for t in range(0, 121)]
    p2.path(lisse, "hm5", tip="forme fermée, intensité de Palm")
    for x, y in mes:
        p2.dot(x, y, "hm7", _num(x, 1) + " min après : " + _num(y, 2)
               + " fois le fond", r=3.6)
    _ = fer
    p2.path([(0.0, 1.0), (30.0, 1.0)], "hm1", dash="4 3",
            tip="loi nulle : le Poisson ne relève rien")
    p2.label(0.6, 1.0, "loi nulle du Poisson", dx=2, dy=-7)

    b.legend(PX2, 352.0,
             [("hm5", "forme fermée"), ("hm7", "mesuré")],
             step=118.0, kind="line")
    b.annotation(0.0, 374.0,
                 "l'amplitude du relèvement vaut α(2β−α)/2(β−α) et non α :")
    b.annotation(0.0, 390.0,
                 "conditionner sur un événement choisit aussi un instant où "
                 "l'intensité était déjà haute")

    _source(b, "Processus de Hawkes exponentiel simulé par amincissement "
              "d'Ogata, ratio de branchement déclaré " + _num(E.HAWKES_N, 2)
            + ", et son Poisson de même taux. Les deux fenêtres de gauche "
              "sont les plus chargées de chaque processus sur "
            + _num(E.T_HAWKES, 0) + " minutes, choisies par balayage et non à "
              "la main : " + _num(len(ev_h), 0) + " événements contre "
            + _num(len(ev_p), 0) + ". Le cadre de droite remplace cette "
              "impression par une mesure, et la forme fermée la rend à "
              "quelques pour-cent près sans aucun ajustement.")
    return b.render("Intensite conditionnelle d un processus auto-excitant "
                    "et decroissance du taux apres un evenement.")


def fig_emp_excitation() -> str:
    """Ce que l'auto-excitation fait au seuil, sur tout le plan.

    L'axe qui compte est celui du ratio de branchement, parce que personne ne
    l'observe directement et que la littérature le place très haut. Le relief
    montre que la question « le marché est-il auto-excité ? » n'a pas d'effet
    sur la direction, mais un effet considérable sur le seuil qu'il faut
    franchir pour gagner.
    """
    z = E.surface_seuil()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)
    lo, hi = E.seuil.PLAUSIBLE_DRIFT_PER_HOUR

    b = _plate(486, "Auto-excitation · le seuil",
               "Le seuil de rentabilité après une bouffée d'activité",
               "hauteur : µ* en points par heure")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(n, 2) for n in E.SURF_BRANCHEMENT],
             col_labels=[_num(t, 0) for t in E.SURF_APRES],
             z_ticks=[(t, _num(t, 1)) for t in (0.6, 1.0, 1.4, 1.8)],
             tip="{v:.3f} pt/h", zero=zlo)

    b.annotation(0.0, 408.0,
                 "arête gauche : ratio de branchement · arête droite : "
                 "minutes écoulées depuis l'événement")
    b.annotation(0.0, 424.0,
                 "le sol est à " + _num(zlo, 2) + " point par heure, le "
                 "sommet à " + _num(zhi, 2) + " : le domaine plausible va de "
                 + _num(lo, 1) + " à " + _num(hi, 1))
    part, _, n_dir = E.direction_apres()
    b.annotation(0.0, 440.0,
                 "part de hausses après un événement : " + _pct(part, 1)
                 + " sur " + _num(n_dir, 0) + " occasions")

    _source(b, "Une hypothèse déclarée, et une seule : chaque événement "
              "déplace le prix d'un pas de taille fixe, donc la variance par "
              "minute suit l'intensité. Le temps de marché diminue alors comme "
              "l'inverse de la variance, et le seuil µ* monte d'autant. "
              "La lecture courante — ça bouge, c'est le moment d'agir — a "
              "donc le signe exact du contraire : une bouffée d'activité "
              "n'améliore pas l'espérance, elle relève la barre. Ce que "
              "l'excitation offre est ailleurs, dans la vitesse de "
              "résolution, et cela se paie au comptant.")
    return b.render("Surface du seuil de rentabilite sur le plan du ratio de "
                    "branchement et du temps ecoule depuis un evenement.")


# ---------------------------------------------------------------------------
# IV. Les valeurs extrêmes
# ---------------------------------------------------------------------------


def fig_emp_arcsin() -> str:
    """À quelle heure le haut du jour se pose, sans aucun marché.

    Le cadre de gauche est la densité, et elle est en U. Le cadre de droite
    est la fréquence cumulée, où la loi de l'arc sinus et la loi uniforme se
    séparent de vingt points dès le premier dixième de séance.

    Aucune donnée de marché n'entre dans cette planche. C'est tout son objet :
    une affirmation du type « le haut se fait à l'ouverture ou en clôture »
    est vraie, et ne dit rien.
    """
    args = E.argmax_seances()
    n = len(args)
    seaux = [0] * 26
    for t in args:
        seaux[min(int(t * 26), 25)] += 1
    dens = [c / n * 26.0 for c in seaux]

    b = _plate(430, "Valeurs extrêmes · la loi de l'arc sinus",
               "L'heure du plus haut, et ce que le hasard en décide",
               _num(n, 0) + " séances sans dérive")

    p1 = Panel(b, PX1, 92, PW, 214, title="Densité de l'heure du sommet",
               readout="1,0 = loi uniforme")
    p1.domain(0.0, 1.0, 0.0, max(dens) * 1.12)
    p1.frame()
    p1.grid_y([0.0, 1.0, 2.0, 3.0], lambda v: _num(v, 0), dx=26.0)
    p1.grid_x([0.0, 0.25, 0.5, 0.75, 1.0],
              lambda v: _num(v * E.SESSION / 60.0, 1) + " h")
    for i, d in enumerate(dens):
        p1.vbar((i + 0.5) / 26.0, 0.0, d, 8.0, "hm4",
                tip=_pct((i + 0.5), 0) + " de la séance : " + _num(d, 2)
                    + " fois l'uniforme")
    loi = []
    for k in range(1, 260):
        t = k / 260.0
        loi.append((t, 1.0 / (math.pi * math.sqrt(t * (1.0 - t)))))
    p1.path(loi, "hm7", tip="densité de l'arc sinus")
    p1.hline(1.0, "lvl")
    p1.label(0.5, 1.0, "loi uniforme", dx=0, dy=-8, anchor="middle")

    p2 = Panel(b, PX2, 92, PW, 214, title="Fréquence cumulée",
               readout="part des séances")
    tri = sorted(args)
    cum = [(tri[int(q * (n - 1))], q) for q in
           [i / 80.0 for i in range(1, 81)]]
    p2.domain(0.0, 1.0, 0.0, 1.0)
    p2.frame()
    p2.grid_y([0.0, 0.25, 0.5, 0.75, 1.0], lambda v: _pct(v), dx=40.0)
    p2.grid_x([0.0, 0.25, 0.5, 0.75, 1.0], lambda v: _pct(v))
    p2.path([(0.0, 0.0), (1.0, 1.0)], "hm1", dash="4 3", tip="loi uniforme")
    p2.path([(k / 200.0, E.arc_sinus(k / 200.0)) for k in range(201)], "hm5",
            tip="loi de l'arc sinus")
    p2.path(cum, "hm7", tip="fréquence mesurée")
    p2.dot(0.1, E.arc_sinus(0.1), "hm7",
           "premier dixième : " + _pct(E.arc_sinus(0.1), 1)
           + " contre 10 % sous l'uniforme", r=4.0)
    p2.label(0.1, E.arc_sinus(0.1), _pct(E.arc_sinus(0.1), 1), dx=8, dy=6)

    b.legend(PX2, 336.0,
             [("hm7", "mesuré"), ("hm5", "arc sinus"),
              ("hm1", "uniforme", "4 3")],
             step=96.0, kind="line")
    b.annotation(0.0, 358.0,
                 "les deux dixièmes de bord portent chacun "
                 + _pct(E.arc_sinus(0.1), 1) + " des sommets, deux fois "
                 "l'uniforme")

    _source(b, "Le maximum d'une marche sans dérive tombe près des bords de "
              "l'intervalle bien plus souvent qu'au milieu, et la loi est "
              "exacte depuis 1939. La conséquence pratique est brutale : "
              "toute règle horaire tirée d'un relevé de hauts et de bas de "
              "séance doit d'abord battre cette courbe, pas la courbe plate. "
              "Le document nº 3 a déjà rencontré cette loi à la partie XV, "
              "où elle expliquait la position d'ouverture dans le range "
              "overnight ; c'est la même, lue sur l'axe du temps.")
    return b.render("Densite et frequence cumulee de l heure du plus haut de "
                    "seance, comparees a la loi de l arc sinus.")


def fig_emp_hill() -> str:
    """Le réglage qui décide de la queue.

    Le tracé de Hill est l'outil standard pour estimer un indice de queue, et
    sa forme est l'aveu de sa faiblesse : il n'a pas de plateau. Chaque loi
    donne une valeur différente selon le nombre d'observations retenues, et
    la gaussienne — dont l'indice vrai est nul — en rend une lourde partout.
    """
    from . import stress

    b = _plate(446, "Valeurs extrêmes · le tracé de Hill",
               "L'indice de queue, et le réglage qui le fabrique",
               _num(E.N_EVT, 0) + " incréments par loi")

    p = Panel(b, 74.0, 92, W - 148.0, 214,
              title="Indice de queue estimé",
              readout="selon la fraction retenue")
    p.domain(0.0015, 0.30, -0.02, 0.52, xlog=True)
    p.frame()
    p.grid_y([0.0, 0.1, 0.2, 0.3, 0.4, 0.5], lambda v: _num(v, 1), dx=30.0)
    p.grid_x([0.002, 0.005, 0.02, 0.05, 0.20], lambda v: _pct(v, 1))
    style = {"gauss": ("hm1", "1 3"), "student5": ("hm3", "7 3"),
             "student3": ("hm7", ""), "merton": ("hm5", "3 3")}
    for cle in E.CLES_QUEUES:
        ech = [abs(x) for x in E.incrementales(cle)]
        pts = []
        for frac in [0.0015 * (1.35 ** i) for i in range(20)]:
            if frac > 0.30:
                break
            k = max(2, int(frac * len(ech)))
            pts.append((frac, stress.hill_estimator(ech, k)))
        cls, dash = style[cle]
        p.path(pts, cls, dash=dash, tip=cle)
    for cle, nom in (("gauss", "ξ vrai : gaussienne"),
                     ("student5", "ξ vrai : Student 5"),
                     ("student3", "ξ vrai : Student 3")):
        vrai = E.XI_VRAI[cle]
        p.hline(vrai, "lvl")
        p.tag(vrai, nom)

    b.legend(74.0, 336.0,
             [("hm1", "gaussienne", "1 3"), ("hm3", "Student 5", "7 3"),
              ("hm7", "Student 3"), ("hm5", "sauts de Merton", "3 3")],
             step=132.0, kind="line")
    b.annotation(0.0, 358.0,
                 "aucune des quatre courbes n'a de plateau : il n'existe pas "
                 "de fraction canonique,")
    b.annotation(0.0, 374.0,
                 "et toutes celles du tracé sont défendables")

    _source(b, "Estimateur de Hill sur les k plus grandes valeurs absolues. "
              "La gaussienne, dont l'indice vrai est nul, se voit attribuer "
              "une queue lourde à toute fraction retenue, et les sauts de "
              "Merton — dont les queues sont gaussiennes elles aussi — plus "
              "encore. C'est le troisième visage d'un même piège du dépôt : "
              "la taille de grappe décide de la rareté d'un déséquilibre de "
              "footprint, la hauteur de rangée décide de celle d'un extrême "
              "pauvre, la fraction retenue décide ici de l'épaisseur d'une "
              "queue. Un réglage non observable ne se choisit pas, il se "
              "déclare et se balaye.")
    return b.render("Trace de Hill de l indice de queue pour quatre lois "
                    "d increment, avec les indices vrais en tirets.")


def fig_emp_queue() -> str:
    """Ce que l'indice de queue coûte, à mesure qu'on s'éloigne.

    Le relief est de l'arithmétique pure : le rapport entre la VaR d'une
    queue de Pareto d'indice `ξ` et celle d'une queue exponentielle, à seuil
    et échelle identiques. Sa forme dit l'essentiel — l'écart est nul près du
    seuil et explose loin de lui.
    """
    z = E.surface_queue()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Valeurs extrêmes · le prix de la queue",
               "Ce qu'un indice de queue coûte, selon la distance au seuil",
               "hauteur : rapport de VaR")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=48.0, cy=15.0, cz=158.0,
             row_labels=[_num(x, 2) for x in E.SURF_XI],
             col_labels=[_num(100.0 * c, 3) + " %" for c in E.SURF_CONFIANCE],
             z_ticks=[(t, _num(t, 1) + " ×") for t in (1.0, 2.0, 3.0)],
             tip="{v:.2f} fois", zero=1.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : indice de queue ξ · arête droite : niveau de "
                 "confiance")
    b.annotation(0.0, 424.0,
                 "le sol est posé à un : c'est le cas ξ = 0, où la Pareto se "
                 "réduit à une exponentielle")
    b.annotation(0.0, 440.0,
                 "à " + _num(99.0, 0) + " % les quatre indices sont "
                 "indiscernables ; à " + _num(99.999, 3) + " % ils diffèrent "
                 "d'un facteur " + _num(zhi, 1))

    _source(b, "Le relief ne contient aucune donnée : c'est la formule de la "
              "VaR d'une Pareto généralisée, à seuil et échelle tenus fixes "
              "pour que seul l'indice bouge. Il explique pourquoi l'indice de "
              "queue est à la fois si disputé et si peu important dans "
              "l'usage courant. Près du seuil il ne change rien, et c'est là "
              "que vivent les stops. Loin du seuil il change tout, et c'est "
              "là que vivent les faillites — mais c'est aussi là que le "
              "tracé de Hill ne sait plus l'estimer.")
    return b.render("Surface du rapport de VaR entre une queue de Pareto et "
                    "une queue exponentielle, selon l indice et la confiance.")


# ---------------------------------------------------------------------------
# V. La théorie de la détection
# ---------------------------------------------------------------------------


def fig_emp_detection() -> str:
    """La sensibilité et le critère, enfin séparés.

    À gauche, la courbe ROC : elle ne dépend que de la sensibilité, et le
    critère n'y est qu'un point où l'on se tient. Cinq opérateurs de même
    compétence occupent cinq points de la même courbe, et affichent cinq taux
    de réussite très différents.

    À droite, ce que ces cinq points rapportent réellement sur une année. La
    courbe a un maximum intérieur, et il n'est pas là où l'intuition le met.
    """
    b = _plate(478, "Détection · sensibilité contre critère",
               "Ce que le taux de réussite mélange, et que la ROC sépare",
               "d′ = " + _num(E.D_REF, 2) + " sur toute la planche")

    p1 = Panel(b, PX1, 92, PW, 214, title="Courbe ROC",
               readout="détections contre fausses alarmes")
    p1.domain(0.0, 1.0, 0.0, 1.0)
    p1.frame()
    p1.grid_y([0.0, 0.5, 1.0], lambda v: _pct(v), dx=40.0)
    p1.grid_x([0.0, 0.5, 1.0], lambda v: _pct(v))
    p1.path([(0.0, 0.0), (1.0, 1.0)], "hm1", dash="4 3",
            tip="sensibilité nulle : la diagonale")
    for d, cls in ((0.30, "hm5"), (0.60, "hm6"), (1.00, "hm7")):
        pts = []
        c = 4.0
        while c >= -4.0:
            h = E.taux_touche(d, c)
            f = E.taux_fausse(d, c)
            pts.append((f, h))
            c -= 0.05
        p1.path(pts, cls, tip="d′ = " + _num(d, 2))
    for c in E.CRITERES:
        p1.dot(E.taux_fausse(E.D_REF, c), E.taux_touche(E.D_REF, c), "hm3",
               "critère " + _signed(c, 2) + " : taux affiché "
               + _pct(E.precision(E.D_REF, c), 1), r=3.6)


    p2 = Panel(b, PX2, 92, PW, 214, title="Ce que rapporte le critère",
               readout="R par an")
    courbes = []
    for d, cls in ((0.15, "hm3"), (0.30, "hm5"), (0.50, "hm7")):
        pts = [(c / 20.0, E.esperance_an(d, c / 20.0))
               for c in range(-16, 61)]
        courbes.append((d, cls, pts))
    haut = max(v for _, _, pts in courbes for _, v in pts)
    p2.domain(-0.8, 3.2, -30.0, haut * 1.15)
    p2.frame()
    p2.grid_y([0.0, 50.0, 100.0], lambda v: _num(v, 0), dx=32.0)
    p2.grid_x([-0.5, 0.0, 1.0, 2.0, 3.0], lambda v: _signed(v, 1))
    p2.hline(0.0, "lvl")
    for d, cls, pts in courbes:
        p2.path(pts, cls, tip="d′ = " + _num(d, 2))
        c_opt, v_opt = E.critere_optimal(d)
        p2.dot(c_opt, v_opt, cls, "optimum à " + _signed(c_opt, 2)
               + " : " + _num(v_opt, 1) + " R par an", r=3.8)
    c_opt, v_opt = E.critere_optimal(E.D_REF)
    p2.label(1.05, haut * 0.96, "pic = critère optimal", dx=0, dy=0)

    b.legend(PX1, 352.0,
             [("hm5", "d′ = 0,30"), ("hm6", "0,60"), ("hm7", "1,00")],
             step=88.0, kind="line")
    b.legend(PX2, 352.0,
             [("hm3", "d′ = 0,15"), ("hm5", "0,30"), ("hm7", "0,50")],
             step=88.0, kind="line")
    b.annotation(0.0, 374.0,
                 "les cinq points du cadre de gauche sont les cinq critères "
                 "de la table, posés sur la courbe d′ = "
                 + _num(E.D_REF, 2))
    b.annotation(0.0, 390.0,
                 "plus la sensibilité est grande, plus le critère optimal "
                 "est lâche :")
    b.annotation(0.0, 406.0,
                 "une bonne lecture rend rentables des occasions qu'un "
                 "critère serré jetterait")

    _source(b, "Le modèle est celui de la psychophysique, avec un taux de "
              "base imposé par la géométrie : la cible tombe d'abord une fois "
              "sur " + _num(1.0 + E.RR, 0) + ". Les cinq points de la courbe "
              "ROC ont la même aire sous la courbe, "
            + _pct(E.aire_roc(E.D_REF), 1) + ", et la même erreur de Bayes, "
            + _pct(E.bayes_error(E.D_REF), 1) + " ; leurs taux de réussite "
              "affichés vont de " + _pct(min(E.precision(E.D_REF, c)
                                             for c in E.CRITERES), 1)
            + " à " + _pct(max(E.precision(E.D_REF, c) for c in E.CRITERES), 1)
            + ". Un relevé de trades ne distingue pas ces cinq opérateurs, et "
              "c'est pourquoi il ne mesure pas la compétence.")
    return b.render("Courbe ROC pour trois sensibilites et esperance annuelle "
                    "en fonction du critere de decision.")


def fig_emp_critere() -> str:
    """L'espérance annuelle sur le plan de la sensibilité et du critère.

    La crête de ce relief est le critère optimal, et elle se déplace : plus
    la sensibilité est grande, plus le critère qui paie est lâche. Le fait
    est contraire à l'intuition de salle de marché — on croit qu'un bon
    lecteur doit être plus sélectif — et il est mécanique.
    """
    z = E.surface_detection()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Détection · le relief du gain",
               "Ce que la sensibilité et le critère rapportent ensemble",
               "hauteur : R par an")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(d, 2) for d in E.SURF_DPRIME],
             col_labels=[_signed(c, 1) for c in E.SURF_CRITERE],
             z_ticks=[(t, _num(t, 0)) for t in (0.0, 60.0, 120.0, 180.0)],
             tip="{v:+.1f} R par an", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : sensibilité d′ · arête droite : critère de "
                 "décision · le sol est posé à l'espérance nulle")
    b.annotation(0.0, 424.0,
                 "la rangée du fond est la loi nulle : à d′ nul, tout le "
                 "profil est sous le sol")
    b.annotation(0.0, 440.0,
                 "le critère optimal passe de "
                 + _signed(E.critere_optimal(0.15)[0], 2) + " à d′ = 0,15 à "
                 + _signed(E.critere_optimal(0.80)[0], 2) + " à d′ = 0,80 : "
                 "mieux on lit, moins il faut trier")

    _source(b, "Espérance annuelle sur " + _num(E.OCCASIONS_AN, 0)
            + " occasions examinées, au stop de " + _num(E.STOP_PCT, 3)
            + " % et au rapport " + _num(E.RR, 0) + " pour un. Ce relief "
              "explique analytiquement ce que la grammaire du setup mesurait sur "
              "douze setups : la confirmation ne déplace pas l'espérance par "
              "décision, elle divise le nombre de décisions — et le produit "
              "des deux a un maximum qu'on peut calculer au lieu de le "
              "chercher à tâtons. Le versant du fond porte la loi nulle et "
              "elle est entièrement négative, ce qui est la seule façon "
              "honnête de dessiner un gain.")
    return b.render("Surface de l esperance annuelle sur le plan de la "
                    "sensibilite et du critere de decision.")


# ---------------------------------------------------------------------------
# VI. Le spectre en grande dimension
# ---------------------------------------------------------------------------


def fig_emp_spectre() -> str:
    """Ce que le bruit produit tout seul, et ce qu'il faut dépasser.

    À gauche, le spectre d'une matrice de corrélation de quinze séries
    **indépendantes** : il n'est pas concentré sur un, il occupe toute une
    plage, et la forme fermée de Marchenko-Pastur la décrit exactement.

    À droite, la transition de Baik-Ben Arous-Péché : au-dessous du seuil, la
    valeur propre d'un vrai facteur reste collée au bord du bruit. Ce n'est
    pas une perte de puissance, c'est une disparition.
    """
    from . import spectrum

    k, n = max(E.LECTURES_GRID), int(E.SESSIONS_PAR_AN)
    gamma = k / n
    nul = spectrum.null_spectrum(k, n, E.N_TIRAGES_SPECTRE, E.SEED + 7)
    lo, hi = spectrum.mp_edges(gamma)

    b = _plate(430, "Spectre · le bruit et le seuil",
               "Combien de lectures peut-on suivre avant que le bruit compose",
               _num(k, 0) + " lectures sur " + _num(n, 0) + " séances")

    p1 = Panel(b, PX1, 92, PW, 214, title="Spectre de séries indépendantes",
               readout="densité des valeurs propres")
    vals = nul.eigenvalues
    seaux = [0] * 30
    for v in vals:
        i = int((v - lo * 0.9) / (hi * 1.15 - lo * 0.9) * 30)
        if 0 <= i < 30:
            seaux[i] += 1
    larg = (hi * 1.15 - lo * 0.9) / 30.0
    dens = [c / (len(vals) * larg) for c in seaux]
    p1.domain(lo * 0.9, hi * 1.15, 0.0, max(dens) * 1.15)
    p1.frame()
    p1.grid_y([t for t in (0.0, 0.5, 1.0, 1.5, 2.0)
               if t <= max(dens) * 1.15], lambda v: _num(v, 1), dx=26.0)
    p1.grid_x([0.6, 0.8, 1.0, 1.2, 1.4, 1.6], lambda v: _num(v, 1))
    for i, d in enumerate(dens):
        p1.vbar(lo * 0.9 + (i + 0.5) * larg, 0.0, d, 9.0, "hm3",
                tip="valeur propre " + _num(lo * 0.9 + (i + 0.5) * larg, 2)
                    + " : densité " + _num(d, 2))
    courbe = []
    for i in range(1, 300):
        x = lo * 0.9 + i * (hi * 1.15 - lo * 0.9) / 300.0
        courbe.append((x, spectrum.mp_density(x, gamma)))
    p1.path(courbe, "hm7", tip="densité de Marchenko-Pastur")
    p1.vline(hi, "lvl")
    p1.label(hi, max(dens) * 0.85, "bord λ₊", dx=-6, dy=0, anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Transition BBP",
               readout="valeur propre observée")
    pts = []
    s = 0.02
    while s <= 1.2:
        pts.append((s, spectrum.spiked_eigenvalue(s, gamma)))
        s += 0.01
    y1 = max(v for _, v in pts) * 1.05
    y0 = hi * 0.96
    p2.domain(0.0, 1.2, y0, y1)
    p2.frame()
    pas = 0.2
    ticks = [y0 + i * pas for i in range(1, int((y1 - y0) / pas) + 1)]
    p2.grid_y(ticks, lambda v: _num(v, 1), dx=30.0)
    p2.grid_x([0.0, 0.3, 0.6, 0.9, 1.2], lambda v: _num(v, 1))
    p2.path(pts, "hm6", tip="valeur propre du facteur")
    seuil_bbp = spectrum.bbp_threshold(gamma)
    p2.vline(seuil_bbp, "lvl")
    p2.label(seuil_bbp, y0 + 0.78 * (y1 - y0),
             "seuil √γ = " + _num(seuil_bbp, 3), dx=8, dy=0)
    p2.hline(hi, "lvl")
    p2.label(1.15, hi, "bord du bruit", dx=0, dy=-7, anchor="end")

    b.annotation(0.0, 336.0,
                 "à gauche, aucune structure : quinze séries indépendantes "
                 "produisent tout de même des valeurs propres jusqu'à "
                 + _num(nul.lambda_max_q95, 2))
    b.annotation(0.0, 352.0,
                 "à droite, la courbe est exactement plate sous le seuil : un "
                 "facteur plus faible que √γ ne laisse aucune trace")

    _source(b, "Matrice de corrélation de " + _num(k, 0) + " lectures sur "
            + _num(n, 0) + " séances, soit γ = " + _num(gamma, 3)
            + ". La densité de Marchenko-Pastur est la forme fermée ; les "
              "barres sont la simulation à k fini, et l'accord est le "
              "contrôle qui autorise à se servir de la forme fermée ailleurs. "
              "Le fait rassurant de cette section est la petitesse du "
              "nombre : suivre quinze lectures ne demande que "
            + _num(spectrum.observations_for_spike(E.S_REF, k), 0)
            + " séances pour distinguer un facteur de force "
            + _num(E.S_REF, 2) + ". Ce qui coûte, quand on suit quinze "
              "lectures, n'est pas le spectre — c'est la multiplicité, et la "
              "première section de cette partie l'a chiffrée.")
    return b.render("Densite des valeurs propres de series independantes et "
                    "transition de Baik-Ben Arous-Peche.")


def fig_emp_bbp() -> str:
    """La transition, vue sur tout le plan.

    Le relief porte une arête vive, et c'est la seule figure du document où
    une surface est exactement plate sur une région entière : sous le seuil
    `√γ`, ce que le facteur ajoute au bord du bruit est **exactement nul**,
    quelle que soit sa force. Une méthode qui prétendrait lire quelque chose
    dans cette région lirait le bruit.

    La hauteur est l'excès sur le bord et non la valeur propre elle-même :
    tracée brute, la surface était un versant lisse où le plat disparaissait,
    parce que le bord du bruit varie avec `γ` et masque ce qu'on veut voir.
    """
    z = E.surface_bbp()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Spectre · la transition",
               "Ce qu'un facteur ajoute au bruit, force contre dimension",
               "hauteur : λ observée moins le bord")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(s, 2) for s in E.SURF_FORCE],
             col_labels=[_num(g, 2) for g in E.SURF_GAMMA],
             z_ticks=[(t, _num(t, 1)) for t in (0.0, 0.5, 1.0)],
             tip="{v:+.3f} au-dessus du bord", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : force du facteur · arête droite : rapport de "
                 "dimension γ = lectures sur observations")
    b.annotation(0.0, 424.0,
                 "le plat posé au sol est la région où le facteur existe et "
                 "ne se voit pas du tout")
    b.annotation(0.0, 440.0,
                 "sa frontière est s = √γ, une arête et non une pente : il "
                 "n'y a pas de transition douce")

    _source(b, "Formule de Baik-Ben Arous-Péché, sans simulation, "
              "hauteur rapportée au bord du bruit λ₊. Ce que le relief "
              "ajoute à la table est la forme de la frontière : elle n'est "
              "pas une pente, c'est une arête. Sous le seuil, deux facteurs "
              "de forces très différentes donnent exactement la même valeur "
              "propre, et aucune finesse d'estimation ne les sépare. "
              "La conséquence pour un opérateur est directe : ajouter des "
              "lectures sans ajouter des séances déplace la frontière vers la "
              "droite et fait disparaître ce qu'il voyait la veille.")
    return b.render("Surface de la valeur propre observee sur le plan de la "
                    "force du facteur et du rapport de dimension.")


# ---------------------------------------------------------------------------
# VII. Le transfert
# ---------------------------------------------------------------------------


def fig_emp_transfert() -> str:
    """Ce que chaque discipline déplace, et sur quel terme.

    La planche range les cinq disciplines par l'ampleur de ce qu'elles
    déplacent, et marque celle qui touche au sens. Une seule le fait, et
    c'est la plus difficile à mesurer des cinq.
    """
    ts = E.transferts()
    b = _plate(400, "Le transfert · ce que chaque discipline déplace",
               "Quel terme de E[τ∧T], de a, de c ou de µ, et de combien",
               "règle de verdict : " + _pct(E.SEUIL_TRANSFERT, 0))

    p = Panel(b, 196.0, 92, W - 236.0, 176,
              title="Déplacement du terme touché",
              readout="en valeur absolue")
    haut = max(abs(t.effet) for t in ts) * 1.55
    p.domain(0.0, haut, -0.5, len(ts) - 0.5)
    p.frame()
    p.grid_x([0.0, 0.5, 1.0, 1.5], lambda v: _pct(v, 0))
    for i, t in enumerate(ts):
        y = len(ts) - 1 - i
        p.hbar(y, 0.0, abs(t.effet), 17.0,
               "hm7" if t.sur_le_sens else ("hm4" if t.transfere else "hm1"),
               tip=t.nom + " : " + _signed(100 * t.effet, 1) + " % sur "
                   + t.terme)
        p.label(abs(t.effet), y, _signed(100 * t.effet, 1) + " %", dx=7, dy=4)
        b.add('<text class="lg" x="188" y="%.1f" text-anchor="end">%s</text>'
              % (p.sy(y) - 2.0, t.nom))
        b.add('<text class="tk" x="188" y="%.1f" text-anchor="end">%s</text>'
              % (p.sy(y) + 11.0, t.terme))
    p.vline(E.SEUIL_TRANSFERT, "lvl")
    p.label(E.SEUIL_TRANSFERT, -0.42, "seuil de verdict", dx=6, dy=4)

    b.legend(74.0, 300.0,
             [("hm7", "sur le sens"),
              ("hm4", "sur l'horloge ou le risque"),
              ("hm1", "ne contraint pas")],
             step=200.0)
    b.annotation(0.0, 324.0,
                 "une seule barre est de la teinte forte, et c'est la plus "
                 "courte des quatre qui transfèrent")

    _source(b, "Chaque déplacement est relu des mesures des sections "
              "précédentes, jamais réécrit ici : corriger une mesure en amont "
              "change donc la barre et le verdict sans intervention. Le seuil "
              "de verdict est déclaré à " + _pct(E.SEUIL_TRANSFERT, 0)
            + " avant les mesures. La lecture est celle de toute la partie : "
              "quatre disciplines déplacent l'horloge, le risque ou le budget "
              "de preuve, une seule touche au sens — et c'est celle dont "
              "l'estimation demande le plus de décisions. L'ordre de "
              "difficulté est exactement inverse de l'ordre d'utilité.")
    return b.render("Deplacement mesure de chaque discipline sur le terme de "
                    "l identite qu elle touche.")


FIGURES = {
    "empunite": fig_emp_unite,
    "emppuissance": fig_emp_puissance,
    "empsurvie": fig_emp_survie,
    "empcalibration": fig_emp_calibration,
    "emphasard": fig_emp_hasard,
    "emphawkes": fig_emp_hawkes,
    "empexcitation": fig_emp_excitation,
    "emparcsin": fig_emp_arcsin,
    "emphill": fig_emp_hill,
    "empqueue": fig_emp_queue,
    "empdetection": fig_emp_detection,
    "empcritere": fig_emp_critere,
    "empspectre": fig_emp_spectre,
    "empbbp": fig_emp_bbp,
    "emptransfert": fig_emp_transfert,
}


def render_all() -> dict[str, str]:
    return {k: f() for k, f in FIGURES.items()}
