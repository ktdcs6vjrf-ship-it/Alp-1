"""Les planches de « le loyer de la convexité ».

Quinze planches, onze à plat et quatre en relief. Aucune ne montre un signal :
toutes montrent une fréquence élevée posée sur une espérance nulle, et la
distance entre les deux.

Comme `figgra`, ce module importe ses fonctions d'échine, de graduation et de
décade de `fignv` plutôt que de les recopier.
"""

from __future__ import annotations

import math

from . import niveaux as nv
from . import quant as q
from . import theta as V
from .figdisc import W, _plate, _source, _surface
from .fignv import _dec, _echine, _pct, _ticks
from .figterm import Board, Panel, _num, _signed


PW = (W - 74.0) / 2.0 - 30.0
PX1 = 74.0
PX2 = 74.0 + (W - 74.0) / 2.0


# ---------------------------------------------------------------------------
# I. Le loyer, et ses trois termes
# ---------------------------------------------------------------------------


def fig_th_termes() -> str:
    """Les trois termes du thêta, et le mot qui n'en désigne qu'un.

    À gauche les trois, contre la moneyness. À droite le total pour un call
    et pour un put, et le passage du second au-dessus de zéro.
    """
    jours = 30.0
    t = jours / 365.0
    ms = [0.60 + 0.01 * i for i in range(81)]

    b = _plate(514, "Thêta · les trois termes",
               "Un mot pour un terme, et il y en a trois",
               _num(100 * V.TAUX, 1) + " % de taux")

    p1 = Panel(b, PX1, 92, PW, 214, title="Les trois, pour un call",
               readout="par jour")
    vals = [[getattr(V.termes_call(m * V.S_REF, V.S_REF, V.VOL_REF, t), champ)
             / 365.0 for m in ms]
            for champ in ("decroissance", "interet", "portage")]
    lo = min(min(x) for x in vals) * 1.15
    hi = max(max(x) for x in vals) * 1.35
    p1.domain(0.60, 1.40, lo, hi)
    p1.frame()
    p1.grid_y(_ticks(lo, hi, 0.01), lambda v: _signed(v, 2), dx=32.0)
    p1.grid_x([0.7, 0.9, 1.1, 1.3], lambda v: _num(v, 1),
              label="moneyness S/K")
    p1.hline(0.0, "lvl")
    for cls, dash, serie, nom in (("hm7", "", vals[0], "decroissance"),
                                  ("hm5", "6 3", vals[1], "interet"),
                                  ("hm3", "2 3", vals[2], "portage")):
        p1.path(list(zip(ms, serie)), cls, dash=dash, tip=nom)

    p2 = Panel(b, PX2, 92, PW, 214, title="Le total, call et put",
               readout="par jour")
    tc = [V.termes_call(m * V.S_REF, V.S_REF, V.VOL_REF, t).total / 365.0
          for m in ms]
    tp = [V.termes_put(m * V.S_REF, V.S_REF, V.VOL_REF, t).total / 365.0
          for m in ms]
    lo2 = min(min(tc), min(tp)) * 1.15
    hi2 = max(max(tc), max(tp), 0.004) * 1.6
    p2.domain(0.60, 1.40, lo2, hi2)
    p2.frame()
    p2.grid_y(_ticks(lo2, hi2, 0.01), lambda v: _signed(v, 2), dx=32.0)
    p2.grid_x([0.7, 0.9, 1.1, 1.3], lambda v: _num(v, 1),
              label="moneyness S/K")
    p2.hline(0.0, "lvl")
    # Deux teintes que la legende du bas n emploie pas : celle-ci decrit les
    # trois termes du cadre de gauche, et un lecteur qui la reporterait sur
    # ce cadre-ci lirait « decroissance de valeur temps » pour un total.
    p2.path(list(zip(ms, tc)), "hm6", tip="theta du call")
    p2.path(list(zip(ms, tp)), "hm1", dash="6 3", tip="theta du put")
    p2.label(1.30, tc[ms.index(1.30)], "call", dx=-6, dy=-8, anchor="end")
    p2.label(1.30, tp[ms.index(1.30)], "put", dx=-6, dy=-8, anchor="end")
    f = V.frontiere_signe(t)
    if 0.60 < f < 1.40:
        p2.dot(f, 0.0, "hm3", "frontière du signe", r=4.2)
        p2.label(0.62, -0.010, "à gauche du point, le put paie", dx=0, dy=4)

    b.legend(0.0, 352.0,
             [("hm7", "décroissance de valeur temps", ""),
              ("hm5", "intérêt sur le strike", "6 3"),
              ("hm3", "portage du dividende", "2 3")],
             step=222.0, kind="line")
    b.annotation(0.0, 368.0,
                 "les trois teintes ci-dessus sont celles du cadre de "
                 "gauche ; le cadre de droite porte ses deux noms")
    b.annotation(0.0, 390.0,
                 "le premier terme est celui que tout le monde appelle « le "
                 "thêta », et il suit le gamma exactement")
    b.annotation(0.0, 406.0,
                 "les deux autres ne sont pas des raffinements : ils pèsent "
                 + _pct((abs(V.termes_call(V.S_REF, V.S_REF, V.VOL_REF,
                                           1.0).interet)
                         + abs(V.termes_call(V.S_REF, V.S_REF, V.VOL_REF,
                                             1.0).portage))
                        / abs(V.termes_call(V.S_REF, V.S_REF, V.VOL_REF,
                                            1.0).total), 0)
                 + " du total à un an")
    b.annotation(0.0, 422.0,
                 "et c'est le terme d'intérêt, de signe opposé sur un put, "
                 "qui rend un thêta positif possible")

    _source(b, "Sur un indice à " + _num(100 * V.TAUX, 1) + " % de taux et "
               + _num(100 * V.DIVIDENDE, 1) + " % de dividende, à trente "
               "jours. Le terme de décroissance est commun au call et au "
               "put — la courbure ne connaît pas le sens de l'option — et "
               "c'est lui qui domine à la monnaie. Les deux autres changent "
               "de signe avec le sens, et deviennent majoritaires dans la "
               "monnaie et à échéance longue, là où la courbure a disparu. "
               "Le point marqué sur le cadre de droite est la frontière du "
               "signe, que la cinquième section cartographie.")
    return b.render("Les trois termes du theta contre la moneyness, et le "
                    "total pour un call et pour un put.")


def fig_th_invariant() -> str:
    """Le rapport du thêta au gamma, et le fait qu'il ne bouge pas.

    Une colonne constante est un signal, dit le dépôt, et il faut la relire.
    Celle-ci est relue : elle est constante parce que c'est un théorème, et
    la planche existe pour montrer que les deux courbes qui la composent,
    elles, parcourent trois ordres de grandeur.
    """
    js = [1.0 * (1.09 ** i) for i in range(80)]
    js = [j for j in js if j <= 365.0]

    b = _plate(494, "Thêta · l'invariant",
               "Deux courbes qui explosent, un rapport qui ne bouge pas",
               "à la monnaie, taux nul")

    p1 = Panel(b, PX1, 92, PW, 214, title="Le thêta et le gamma",
               readout="échelle log")
    th = [abs(V.termes_call(V.S_REF, V.S_REF, V.VOL_REF, j / 365.0, 0.0,
                            0.0).decroissance) / 365.0 for j in js]
    ga = [1000.0 * nv.gamma(V.S_REF, V.S_REF, V.VOL_REF, j / 365.0)
          for j in js]
    # Le domaine se deduit des deux series, jamais d une intuition : ecrit a
    # la main, il posait la courbe de gamma **entierement hors du cadre**, et
    # ni le balayage de debordement ni celui d occupation ne le voyaient.
    ylo = min(min(th), min(ga)) / 1.6
    yhi = max(max(th), max(ga)) * 1.6
    p1.domain(1.0, 365.0, ylo, yhi, xlog=True, ylog=True)
    p1.frame()
    p1.grid_y([t for t in (0.01, 0.1, 1.0, 10.0, 100.0)
               if ylo <= t <= yhi], _dec, dx=34.0)
    p1.grid_x([1, 3, 10, 30, 100, 365], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p1.path(list(zip(js, th)), "hm7", tip="theta par jour")
    p1.path(list(zip(js, ga)), "hm4", dash="6 3", tip="gamma, en millieme")

    # Le titre d un cadre est mis en capitales par la feuille : une lettre
    # grecque y devient sa majuscule, et « σ » se publie « Σ ». La formule
    # va donc dans la lecture chiffree, qui reste en bas de casse.
    p2 = Panel(b, PX2, 92, PW, 214, title="Leur rapport",
               readout="rapporté à ½σ²S²")
    cible = V.rapport_theta_gamma(V.S_REF, V.VOL_REF)
    exact = [(j, (t * 365.0 / (g / 1000.0)) / cible)
             for j, t, g in zip(js, th, ga)]
    # Le loyer d une journee entiere, contre le loyer instantane. L identite
    # est exacte a l instant ; sur la journee qu un vendeur detient vraiment,
    # elle vaut le double au dernier jour. C est le resultat de la partie XIX,
    # rencontre ici sur le loyer lui-meme au lieu du mouvement d equilibre.
    fini = []
    for j in js:
        t = j / 365.0
        g = nv.gamma(V.S_REF, V.S_REF, V.VOL_REF, t)
        d = (nv.call(V.S_REF, V.S_REF, V.VOL_REF, t)
             - nv.call(V.S_REF, V.S_REF, V.VOL_REF, max(1e-9, t - 1.0 / 365.0)))
        fini.append((j, d * 365.0 / g / cible))
    hi2 = max(y for _, y in fini) * 1.10
    p2.domain(1.0, 365.0, 0.90, hi2, xlog=True)
    p2.frame()
    p2.grid_y(_ticks(0.90, hi2, 0.25), lambda v: _num(v, 2), dx=32.0)
    p2.grid_x([1, 3, 10, 30, 100, 365], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.hline(1.0, "lvl")
    p2.path(fini, "hm3", dash="2 3", tip="loyer d une journee entiere")
    p2.path(exact, "hm6", tip="loyer instantane")
    p2.label(365.0, 1.0, "l'identité", dx=-6, dy=-8, anchor="end")
    p2.dot(1.0, fini[0][1], "hm3", "au dernier jour, le double", r=4.4)

    b.legend(0.0, 352.0,
             [("hm7", "thêta par jour", ""),
              ("hm4", "gamma en millièmes", "6 3"),
              ("hm6", "rapport instantané", ""),
              ("hm3", "loyer d'une journée", "2 3")],
             step=166.0, kind="line")
    b.annotation(0.0, 376.0,
                 "les deux courbes de gauche parcourent trois ordres de "
                 "grandeur entre un an et un jour")
    b.annotation(0.0, 392.0,
                 "leur rapport instantané est plat à la huitième décimale, "
                 "et c'est une identité, non une observation")
    b.annotation(0.0, 408.0,
                 "mais le loyer d'une journée entière vaut le double de "
                 "l'instantané au dernier jour")

    _source(b, "Le rapport du premier terme du thêta au gamma vaut ½σ²S² "
               "exactement, sans dépendance à l'échéance ni au strike. La "
               "partie XIX l'établit par trois routes et en tire le "
               "mouvement d'équilibre quotidien ; il est repris ici pour ce "
               "qu'il interdit. Une colonne constante est en général le "
               "signe d'un défaut, et le dépôt en a trouvé plusieurs ainsi ; "
               "celle-ci est constante parce que c'est un théorème. La "
               "seconde courbe du cadre de droite dit ce que l'identité ne "
               "dit pas : elle est exacte à l'instant, et le loyer d'une "
               "journée entière — celle qu'un vendeur détient réellement — "
               "vaut le double de l'instantané au dernier jour. C'est le "
               "résultat de la partie XIX, rencontré ici sur le loyer au "
               "lieu du mouvement d'équilibre.")
    return b.render("Le theta et le gamma sur trois ordres de grandeur, et "
                    "leur rapport constant.")


# ---------------------------------------------------------------------------
# II. La loi nulle d'un vendeur de prime
# ---------------------------------------------------------------------------


def fig_th_exemple() -> str:
    """Trois vies d'un vendeur couvert, et celle qui rend tout en une séance.

    Le mécanisme entier tient dans une trajectoire : le loyer rentre tous les
    jours, en ligne presque droite, et il repart en un après-midi. Aucune
    courbe de distribution ne fait comprendre cela.
    """
    temoins = V.chemins_temoins()
    c = V.simuler_vendeur()
    classes = {"gagnant": "hm7", "median": "hm5", "perdant": "hm3"}
    dashes = {"gagnant": "", "median": "6 3", "perdant": "2 3"}
    jours = int(V.JOURS_OPTION)

    b = _plate(516, "Thêta · trois vies d'un vendeur",
               "Le loyer rentre en un mois et repart en une séance",
               _pct(c.couvert.taux, 1) + " de vies gagnantes")

    p1 = Panel(b, PX1, 92, PW, 214, title="Le résultat cumulé",
               readout="en prime")
    vals = [v for _, cum, _ in temoins for v in cum]
    ylo, yhi = min(vals) * 1.15, max(vals) * 1.25
    p1.domain(0.0, jours, ylo, yhi)
    p1.frame()
    p1.grid_y(_ticks(ylo, yhi, 0.5), lambda v: _signed(v, 1), dx=32.0)
    p1.grid_x([0, 10, 20, 30], lambda v: _num(v, 0),
              label="jours depuis la vente")
    p1.hline(0.0, "lvl")
    for cle, cum, _ in temoins:
        p1.path(list(enumerate(cum)), classes[cle], dash=dashes[cle],
                tip=V.LIBELLES[cle])
    _, cum_perdant, _ = temoins[2]
    jp = V.jour_de_la_perte(cum_perdant)
    p1.dot(jp, cum_perdant[jp], "hm3",
           "la séance qui rend le loyer", r=4.4)

    p2 = Panel(b, PX2, 92, PW, 214, title="Les trois sous-jacents",
               readout="points d'indice")
    prix = [x for _, _, ch in temoins for x in ch]
    plo, phi = min(prix) * 0.995, max(prix) * 1.005
    p2.domain(0.0, jours, plo, phi)
    p2.frame()
    p2.grid_y(_ticks(plo, phi, 4.0), lambda v: _num(v, 0), dx=30.0)
    p2.grid_x([0, 10, 20, 30], lambda v: _num(v, 0),
              label="jours depuis la vente")
    p2.hline(V.S_REF, "lvl")
    for cle, _, ch in temoins:
        p2.path(list(enumerate(ch)), classes[cle], dash=dashes[cle],
                tip=V.LIBELLES[cle])
    p2.label(0.0, V.S_REF, "strike", dx=4, dy=-7)

    b.legend(0.0, 358.0,
             [(classes[c], V.LIBELLES[c], dashes[c]) for c, _, _ in temoins],
             step=222.0, kind="line")
    b.annotation(0.0, 382.0,
                 "trois chemins sans dérive, à réalisée égale à "
                 "l'implicite : l'espérance des trois est nulle")
    b.annotation(0.0, 398.0,
                 "le chemin en pointillés court perd "
                 + _pct(cum_perdant[jp - 1] - cum_perdant[jp], 0)
                 + " de la prime dans la seule séance " + _num(jp, 0))
    b.annotation(0.0, 414.0,
                 "la ligne du haut monte presque droit, et c'est cette "
                 "régularité-là qui se prend pour un revenu")

    _source(b, "Trois chemins choisis par une règle calculée : le premier "
               "dont le résultat dépasse la moitié de la prime, le premier "
               "qui en perd plus de la moitié, et celui dont le résultat est "
               "le plus proche de la médiane. Le vendeur est couvert en delta "
               "une fois par jour, et la volatilité réalisée est exactement "
               "celle qu'il a facturée : aucun des trois n'a d'avantage ni de "
               "désavantage. Le point marqué est la plus forte baisse d'une "
               "séance à la suivante — calculée, jamais la séance du minimum. "
               "Le cadre de droite montre que rien d'extraordinaire n'arrive "
               "au sous-jacent ce jour-là. Le chemin médian se fige à zéro "
               "après la vingt-cinquième séance, et ce n'est pas un défaut "
               "de tracé : son sous-jacent est parti loin du strike, "
               "l'option n'a plus de courbure, et un vendeur sans courbure "
               "ne gagne ni ne perd plus rien — il a cessé de percevoir un "
               "loyer parce qu'il a cessé de porter un risque.")
    return b.render("Trois resultats cumules de vendeur couvert, et les trois "
                    "chemins de sous-jacent correspondants.")


def fig_th_frequence() -> str:
    """La loi du résultat, couvert et nu, avec sa moyenne et sa médiane.

    Les deux cadres portent la même espérance, nulle, et deux formes qui
    n'ont rien à voir. La bande de la région gagnante est peinte **avant**
    les barres : une bande posée après recouvre ce qu'elle commente, et le
    dépôt a déjà publié une loi unimodale qui se lisait bimodale pour cette
    raison.
    """
    c = V.simuler_vendeur()

    b = _plate(500, "Thêta · la loi du vendeur",
               "Deux lois, une seule espérance, et elle est nulle",
               _num(V.N_CHEMINS, 0) + " chemins")

    # Chaque cadre porte son propre domaine : le vendeur nu ne peut pas
    # gagner plus que la prime, et un domaine symetrique laisserait un tiers
    # de cadre vide a droite pour cacher le seul plafond de la planche.
    for k, (titre, nu, borne, dlo, dhi, cls) in enumerate(
            (("Couvert chaque jour", False, 0.7, -0.7, 0.7, "hm6"),
             ("Vendu nu", True, 3.0, -3.0, 1.18, "hm4"))):
        h = V.histogramme(1, 41, nu, borne)
        v = c.nu if nu else c.couvert
        px = PX1 if k == 0 else PX2
        pan = Panel(b, px, 92, PW, 214, title=titre, readout="densité")
        hi = max(f for x, f in h if dlo <= x <= dhi) * 1.25
        pan.domain(dlo, dhi, 0.0, hi)
        pan.frame()
        pan.grid_y(_ticks(0.0, hi, hi / 3.0), lambda x: _num(x, 1), dx=30.0)
        pan.grid_x(_ticks(dlo, dhi, borne / 2.0), lambda x: _signed(x, 1),
                   label="résultat, en fractions de la prime")
        pan.band_x(0.0, dhi)
        # L epaisseur d une barre est en **pixels**, jamais en unites de
        # donnee : passee en unites de donnee elle vaut trois centiemes de
        # pixel, l histogramme se reduit a des cheveux, et aucun balayage ne
        # le voit — ni debordement, ni chevauchement, ni cadre vide.
        pas = 2.0 * borne / 41.0
        largeur = PW * pas / (dhi - dlo) * 0.86
        for centre, dens in h:
            if dens > 0.0 and dlo <= centre <= dhi:
                pan.vbar(centre, 0.0, dens, largeur, cls,
                         tip=_signed(centre, 2) + " : " + _num(dens, 2))
        pan.vline(v.moyenne, "lvl")
        pan.vline(v.mediane, "lvl")
        pan.label(v.mediane, hi, "médiane " + _pct(v.mediane, 1),
                  dx=5, dy=14)
        pan.label(v.moyenne, hi, "moyenne " + _pct(v.moyenne, 2),
                  dx=-5, dy=28, anchor="end")
        if nu:
            pan.vline(1.0, "lvl")
            pan.label(1.0, hi, "le plafond : la prime", dx=-5, dy=44,
                      anchor="end")

    b.legend(0.0, 352.0,
             [("hm6", "couvert chaque jour"), ("hm4", "vendu nu")],
             step=222.0)
    b.annotation(0.0, 376.0,
                 "la zone teintée porte les résultats gagnants : "
                 + _pct(c.couvert.taux, 1) + " de la masse à gauche, "
                 + _pct(c.nu.taux, 1) + " à droite")
    b.annotation(0.0, 392.0,
                 "moyenne nulle des deux côtés, médiane positive des "
                 "deux : l'écart est payé par la queue de gauche")
    b.annotation(0.0, 408.0,
                 "couvrir resserre la loi d'un facteur "
                 + _num(c.nu.ecart_type / c.couvert.ecart_type, 1)
                 + " sans déplacer son centre")

    _source(b, "Les deux lois viennent des mêmes chemins, à volatilité "
               "réalisée égale à l'implicite — l'hypothèse que le guide pose "
               "lui-même pour conclure à l'espérance nulle. Noter les deux "
               "échelles d'abscisse : le vendeur nu joue sur une plage quatre "
               "fois plus large, et son pire chemin perd "
               + _pct(abs(c.nu.pire), 0) + " de la prime encaissée. Ce que la "
               "couverture achète est la largeur, jamais le centre.")
    return b.render("Les lois du resultat d un vendeur couvert et d un "
                    "vendeur nu, avec leurs moyennes et medianes.")


def fig_th_intervalle() -> str:
    """Le mécanisme : un khi-deux à un degré, et ce qu'il devient en s'accumulant.

    À gauche la loi d'une séance de vendeur, dont la médiane est sous la
    moyenne de plus de moitié. À droite ce que la fréquence devient quand on
    empile les séances, et le fait que le relevé du soir n'est pas la
    position.
    """
    b = _plate(494, "Thêta · le relevé et la position",
               "Deux séances sur trois, et pourtant un pile ou face",
               "loi exacte")

    p1 = Panel(b, PX1, 92, PW, 214,
               title="La variance réalisée d'une séance", readout="densité")
    xs = [0.001 + 0.03 * i for i in range(140)]
    dens = [math.exp(-x / 2.0) / math.sqrt(2.0 * math.pi * x) for x in xs]
    p1.domain(0.0, 4.2, 0.0, 1.05)
    p1.frame()
    p1.grid_y(_ticks(0.0, 1.0, 0.25), lambda v: _num(v, 2), dx=30.0)
    p1.grid_x([0, 1, 2, 3, 4], lambda v: _num(v, 0),
              label="variance réalisée / variance facturée")
    p1.band_x(0.0, 1.0)
    p1.path(list(zip(xs, dens)), "hm7", tip="densite du khi-deux a un degre")
    p1.vline(V.mediane_khi2(), "lvl")
    p1.vline(1.0, "lvl")
    p1.label(V.mediane_khi2(), 1.05, "médiane " + _num(V.mediane_khi2(), 3),
             dx=6, dy=14)
    p1.label(1.0, 1.05, "moyenne 1", dx=6, dy=28)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="La fréquence, en empilant les séances",
               readout="fréquence de gain")
    ms = list(range(1, 241))
    p2.domain(1.0, 240.0, 0.45, 0.72, xlog=True)
    p2.frame()
    p2.grid_y(_ticks(0.45, 0.70, 0.05), lambda v: _pct(v, 0), dx=36.0)
    p2.grid_x([1, 3, 10, 30, 100, 240], lambda v: _num(v, 0),
              label="séances accumulées")
    p2.hline(0.5, "lvl")
    p2.path([(m, V.taux_de_m_intervalles(m)) for m in ms], "hm6",
            tip="frequence a poids egaux")
    c = V.simuler_vendeur()
    p2.dot(1.0, V.taux_par_intervalle(), "hm7", "une séance", r=4.4)
    p2.dot(30.0, c.couvert.taux, "hm3", "la position mesurée", r=4.4)
    p2.label(1.0, V.taux_par_intervalle(), "une séance", dx=9, dy=4)
    p2.label(30.0, c.couvert.taux, "la position de trente jours",
             dx=-9, dy=4, anchor="end")
    p2.tag(0.5, "le pile ou face", side="right")

    b.legend(0.0, 352.0,
             [("hm6", "forme fermée, à poids égaux", "")],
             step=222.0, kind="line")
    b.annotation(0.0, 376.0,
                 "la variance réalisée tombe sous celle qu'on facture "
                 + _pct(V.taux_par_intervalle(), 1) + " du temps : médiane "
                 + _num(V.mediane_khi2(), 3) + " contre moyenne un")
    b.annotation(0.0, 392.0,
                 "la fréquence descend vers un demi quand les séances "
                 "s'empilent, et trente jours y suffisent")
    b.annotation(0.0, 408.0,
                 "le point mesuré est sous la courbe : les poids ne sont "
                 "pas égaux et dépendent du chemin")

    _source(b, "La loi de gauche est celle du carré d'une gaussienne : elle "
               "est exacte, elle ne dépend d'aucun paramètre de marché, et "
               "toute la partie en découle. Un vendeur gagne sa séance si la "
               "variance réalisée tombe sous celle qu'il a facturée, "
               "c'est-à-dire si un khi-deux à un degré tombe sous sa "
               "moyenne. La courbe de droite est le même calcul pour une "
               "somme : la médiane remonte vers la moyenne comme la "
               "distribution se symétrise, et la fréquence rejoint le pile "
               "ou face. Le relevé du soir et la position ne sont pas le "
               "même objet, et c'est le premier qu'on regarde.")
    return b.render("La densite du khi-deux a un degre et la frequence de "
                    "gain en fonction du nombre de seances accumulees.")


# ---------------------------------------------------------------------------
# III. Ce que coûte la couverture discrète
# ---------------------------------------------------------------------------


def fig_th_couverture() -> str:
    """La dispersion contre la fréquence de couverture, et l'exposant mesuré.

    À gauche l'ajustement en échelle logarithmique — c'est là qu'une loi de
    puissance se lit. À droite les deux grandeurs que la couverture ne
    déplace pas, et c'est le sujet.
    """
    k, p = V.loi_de_dispersion()

    b = _plate(500, "Thêta · ce que la couverture achète",
               "La dispersion décroît en racine, l'espérance ne bouge pas",
               "exposant mesuré " + _num(p, 3))

    p1 = Panel(b, PX1, 92, PW, 214, title="La dispersion",
               readout="en prime")
    p1.domain(0.8, 40.0, 0.02, 0.25, xlog=True, ylog=True)
    p1.frame()
    p1.grid_y([0.02, 0.05, 0.1, 0.2], lambda v: _pct(v, 0), dx=36.0)
    p1.grid_x([1, 2, 4, 8, 16, 32], lambda v: _num(v, 0),
              label="couvertures par jour")
    xs = [1.0 * (1.06 ** i) for i in range(70)]
    xs = [x for x in xs if x <= 34.0]
    # Deux teintes absentes de la legende du bas, qui decrit le cadre de
    # droite : hm7 y designe une frequence, et le lecteur la reporterait ici
    # sur une dispersion.
    p1.path([(x, V.dispersion_ajustee(x)) for x in xs], "hm4", dash="6 3",
            tip="ajustement k n^-p")
    for n in V.PAS_GRILLE:
        p1.dot(n, V.dispersion(n), "hm6", _num(n, 0) + " par jour : "
               + _pct(V.dispersion(n), 2), r=4.2)
    # A droite du cadre de gauche vit la gouttiere d axe du cadre de droite :
    # elle mord de six pixels sur lui, et tout texte pose la s y heurte.
    p1.label(1.6, 0.235, "points : la mesure", dx=0, dy=0)
    p1.label(1.6, 0.185, "trait : l'ajustement", dx=0, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="Ce qui ne bouge pas",
               readout="fréquences et espérance")
    p2.domain(0.8, 40.0, -0.06, 0.75, xlog=True)
    p2.frame()
    p2.grid_y(_ticks(0.0, 0.7, 0.2), lambda v: _pct(v, 0), dx=36.0)
    p2.grid_x([1, 2, 4, 8, 16, 32], lambda v: _num(v, 0),
              label="couvertures par jour")
    p2.hline(0.0, "lvl")
    moyennes = [(float(n),
                 V.simuler_vendeur(par_jour=n, n=V.N_GRILLE).couvert.moyenne)
                for n in V.PAS_GRILLE]
    taux = [(float(n),
             V.simuler_vendeur(par_jour=n, n=V.N_GRILLE).couvert.taux)
            for n in V.PAS_GRILLE]
    inter = [(float(n),
              V.simuler_vendeur(par_jour=n, n=V.N_GRILLE).taux_intervalle)
             for n in V.PAS_GRILLE]
    p2.path(inter, "hm7", tip="frequence d un intervalle")
    p2.path(taux, "hm5", dash="6 3", tip="frequence de la position")
    p2.path(moyennes, "hm3", dash="2 3", tip="esperance")
    p2.label(0.8, 0.0, "zéro", dx=4, dy=-7)

    b.legend(0.0, 352.0,
             [("hm7", "fréquence de gain d'un intervalle", ""),
              ("hm5", "fréquence de gain de la position", "6 3"),
              ("hm3", "espérance", "2 3")],
             step=222.0, kind="line")
    b.annotation(0.0, 376.0,
                 "l'exposant est ajusté, non postulé : " + _num(p, 3)
                 + ", donc diviser la dispersion par deux coûte quatre fois "
                 "plus")
    b.annotation(0.0, 392.0,
                 "à droite, deux courbes plates et une haute : seule "
                 "celle d'un intervalle ne descend pas")
    b.annotation(0.0, 408.0,
                 "il faut " + _num(V.couvertures_pour_bruit(0.05), 0)
                 + " couvertures par jour pour ramener la dispersion à "
                 "cinq pour cent de la prime")

    _source(b, "Sur " + _num(V.N_GRILLE, 0) + " chemins par point, à "
               "volatilité réalisée égale à l'implicite. L'exposant est "
               "mesuré, et non postulé : la partie XVIII a publié une demi-largeur "
               "supposée décroître en racine, la mesure y a rendu 0,61, et "
               "la racine manquait les points de dix-neuf pour cent. Ici la "
               "racine est la bonne réponse, mais elle est vérifiée avant "
               "d'être écrite. Le cadre de droite est le résultat de la "
               "section : la couverture resserre la loi et ne déplace ni "
               "l'espérance ni la fréquence de gain de la position.")
    return b.render("La dispersion du vendeur contre la frequence de "
                    "couverture, et les grandeurs que la couverture ne "
                    "deplace pas.")


def fig_th_relief() -> str:
    """Le relief de la dispersion, en couvertures et en échéance."""
    z = [list(ligne) for ligne in V.surface_dispersion()]
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Thêta · le relief de la dispersion",
               "Ce qu'un vendeur ne contrôle qu'à moitié",
               "hauteur : écart-type, en prime")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(n, 0) for n in V.SURF_PAS],
             col_labels=[_num(j, 0) for j in V.SURF_JOURS],
             z_ticks=[(t, _pct(t, 0)) for t in _echine(zlo, zhi)],
             tip="{v:.3f} de prime", zero=zlo)

    b.annotation(0.0, 408.0,
                 "arête gauche : couvertures par jour · arête droite : "
                 "jours à l'échéance · hauteur : écart-type")
    b.annotation(0.0, 424.0,
                 "le coin du fond est la couverture quotidienne à une "
                 "semaine, où la dispersion vaut " + _pct(zhi, 0)
                 + " de la prime")
    b.annotation(0.0, 440.0,
                 "les deux axes agissent dans le même sens : moins "
                 "d'occasions de recoller la couverture")

    _source(b, "L'espérance est nulle en tout point de ce relief, et c'est "
               "ce qui le rend lisible : il ne montre que du risque. Les "
               "deux axes sont le même paramètre vu de deux côtés — le "
               "nombre total de rééquilibrages sur la vie de l'option — et "
               "la surface est donc, à peu de chose près, une fonction de "
               "leur produit. Un vendeur d'options courtes qui couvre une "
               "fois par jour porte une dispersion de l'ordre de la moitié "
               "de sa prime ; le même vendeur sur trois mois, couvert huit "
               "fois par jour, la ramène sous le vingtième.")
    return b.render("Relief de la dispersion du vendeur, en couvertures par "
                    "jour et en jours a l echeance.")


# ---------------------------------------------------------------------------
# IV. Les deux horloges
# ---------------------------------------------------------------------------


def fig_th_horloges() -> str:
    """Le week-end sur les deux horloges, et la hausse d'implicite qu'il impose.

    À gauche ce que le thêta calendaire annonce et ce qu'on observe. À droite
    la hausse d'implicite qui rend les deux compatibles, et sa forme fermée.
    """
    poids = V.poids_pour_apparents(1.0)
    js = [4.2 + 0.6 * i for i in range(300)]
    js = [j for j in js if j <= 180.0]

    b = _plate(500, "Thêta · les deux horloges",
               "Ce qu'un week-end coûte, et ce qu'il faut ajouter lundi",
               "poids calibré " + _num(poids, 4))

    p1 = Panel(b, PX1, 92, PW, 214, title="La décote d'un week-end",
               readout="en prime")
    p1.domain(4.0, 180.0, 0.0, 0.30, xlog=True)
    p1.frame()
    p1.grid_y(_ticks(0.0, 0.30, 0.10), lambda v: _pct(v, 0), dx=34.0)
    p1.grid_x([5, 10, 20, 40, 90, 180], lambda v: _num(v, 0),
              label="jours calendaires à l'échéance")
    p1.path([(j, V.decote_calendaire(j)) for j in js], "hm7",
            tip="annonce du theta calendaire")
    p1.path([(j, V.decote_observee(j, poids)) for j in js], "hm4",
            dash="6 3", tip="decote observee")
    # Les deux courbes sont nommees par la legende ; une etiquette flottante
    # au coin du cadre ne designerait rien.
    p1.label(20.0, V.decote_calendaire(20.0), "annoncé", dx=6, dy=-8)
    p1.label(20.0, V.decote_observee(20.0, poids), "observé", dx=6, dy=14)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="La hausse d'implicite du lundi", readout="en relatif")
    p2.domain(4.0, 180.0, 0.0, 0.80, xlog=True)
    p2.frame()
    p2.grid_y(_ticks(0.0, 0.8, 0.2), lambda v: _pct(v, 0), dx=34.0)
    p2.grid_x([5, 10, 20, 40, 90, 180], lambda v: _num(v, 0),
              label="jours calendaires à l'échéance")
    p2.band_y(0.0, V.SPREAD_VOL)
    p2.path([(j, V.derive_implicite(j, poids)) for j in js], "hm6",
            tip="hausse requise")
    # La forme fermee tombe exactement sur la courbe mesuree : tracee en
    # trait, elle serait invisible sous elle et la legende decrirait une
    # courbe qu on ne voit pas. Elle est donc posee en points, aux echeances
    # de la table.
    for j in V.ECHEANCES_HORLOGE:
        if 4.0 <= j <= 180.0:
            p2.dot(j, math.sqrt((j - 1.0) / (j - 3.0)) - 1.0, "hm3",
                   "forme fermée : " + _pct(
                       math.sqrt((j - 1.0) / (j - 3.0)) - 1.0, 1), r=3.6)
    crit = V.echeance_critique(V.SPREAD_VOL, poids)
    p2.dot(crit, V.SPREAD_VOL, "hm7", "seuil de visibilité", r=4.4)
    p2.label(4.2, 0.5 * V.SPREAD_VOL, "une fourchette d'un point",
             dx=6, dy=4)

    b.legend(0.0, 352.0,
             [("hm7", "annoncé par le thêta calendaire", ""),
              ("hm4", "observé sur l'horloge de bourse", "6 3"),
              ("hm3", "forme fermée √((D−1)/(D−3)) − 1", "")],
             step=222.0, kind="line")
    b.annotation(0.0, 376.0,
                 "le rapport des deux courbes de gauche est constant : "
                 + _num(V.jours_apparents(poids), 2)
                 + " jour observé pour trois annoncés")
    b.annotation(0.0, 392.0,
                 "le guide écrit « plutôt un jour » ; c'est ce qui "
                 "calibre le poids, et la constance est prédite")
    b.annotation(0.0, 408.0,
                 "la hausse d'implicite dépasse une fourchette d'un point "
                 "sous " + _num(crit, 0) + " jours, et vaut "
                 + _pct(V.derive_implicite(4.0, poids), 0) + " à quatre jours")

    _source(b, "Le poids d'un jour non ouvré n'est pas observable : à un, "
               "l'horloge est calendaire et le week-end coûte trois jours ; à "
               "zéro, elle est de bourse et il ne coûte rien. Les deux "
               "conventions que le guide oppose sont les deux bouts du même "
               "paramètre, et le dépôt le calibre sur l'observation que le "
               "guide publie lui-même plutôt que de le choisir. La forme "
               "fermée du cadre de droite tombe alors exactement sur la "
               "courbe mesurée, ce qui est le contrôle de la section : deux "
               "routes indépendantes, un seul nombre.")
    return b.render("La decote de week-end sur les deux horloges, et la "
                    "hausse d implicite qu elle impose au lundi.")


def fig_th_poids() -> str:
    """Le paramètre que personne n'observe, et l'écart qu'il ouvre.

    Une seule courbe, parce qu'une seule grandeur compte : les jours de
    décroissance qu'on croit voir passer, contre le poids d'un jour non
    ouvré. Les deux conventions sont ses deux extrémités.
    """
    poids = V.poids_pour_apparents(1.0)
    ws = [0.002 * i for i in range(501)]

    b = _plate(494, "Thêta · le paramètre non observable",
               "Deux conventions, et ce sont les deux bouts d'un curseur",
               "trois jours calendaires")

    p1 = Panel(b, PX1, 92, PW, 214, title="Les jours apparents",
               readout="jours")
    p1.domain(0.0, 1.0, 0.0, 3.2)
    p1.frame()
    p1.grid_y(_ticks(0.0, 3.0, 1.0), lambda v: _num(v, 0), dx=26.0)
    # Les deux conventions se nomment dans la gouttiere d abscisse, sous
    # leur propre valeur : posees dans le cadre, elles atterrissaient chacune
    # a la hauteur de l autre et le lecteur les attachait au mauvais bout.
    p1.grid_x([0.0, 0.25, 0.5, 0.75, 1.0], lambda v: _num(v, 2),
              label="poids : 0 = bourse, 1 = calendrier")
    p1.path([(w, V.jours_apparents(w)) for w in ws], "hm7",
            tip="jours apparents")
    p1.dot(poids, 1.0, "hm3", "calibré sur l'observation du guide", r=4.4)
    p1.dot(1.0, 3.0, "hm5", "convention calendaire", r=4.2)
    p1.dot(0.0, 0.0, "hm5", "convention de bourse", r=4.2)
    p1.label(poids, 1.0, "calibré sur le guide", dx=9, dy=4)

    p2 = Panel(b, PX2, 92, PW, 214,
               title="La hausse d'implicite qui en découle", readout="à 7 et 30 jours")
    yhi = V.derive_implicite(7.0, 0.0) * 1.12
    p2.domain(0.0, 1.0, 0.0, yhi)
    p2.frame()
    p2.grid_y(_ticks(0.0, yhi, 0.1), lambda v: _pct(v, 0), dx=34.0)
    p2.grid_x([0.0, 0.25, 0.5, 0.75, 1.0], lambda v: _num(v, 2),
              label="poids d'un jour non ouvré")
    p2.band_y(0.0, V.SPREAD_VOL)
    for cls, dash, jour in (("hm7", "", 7.0), ("hm4", "6 3", 30.0)):
        p2.path([(w, min(yhi, V.derive_implicite(jour, w))) for w in ws],
                cls, dash=dash, tip="a " + _num(jour, 0) + " jours")
    p2.vline(poids, "lvl")
    p2.label(poids, yhi, "poids calibré", dx=6, dy=14)

    b.legend(0.0, 352.0,
             [("hm7", "échéance de sept jours", ""),
              ("hm4", "échéance de trente jours", "6 3")],
             step=222.0, kind="line")
    b.annotation(0.0, 376.0,
                 "à poids un le week-end coûte trois jours et aucune "
                 "hausse n'est requise : c'est cohérent")
    b.annotation(0.0, 392.0,
                 "à poids nul, il ne coûte rien, et la hausse requise du "
                 "lundi devient la plus grande")
    b.annotation(0.0, 408.0,
                 "c'est la situation de la taille de grappe du "
                 "footprint : un réglage décide de ce qu'on lit")

    _source(b, "Le dépôt refuse de choisir un paramètre non observable et le "
               "balaie. Deux couches du document en souffrent déjà — la "
               "fréquence nulle d'un déséquilibre de footprint passe de "
               "moins d'un pour mille à près d'un sur dix selon la taille de "
               "grappe, celle d'un extrême pauvre de cinq à trente-sept pour "
               "cent selon la hauteur de rangée — et l'horloge des options "
               "est la troisième. Le point marqué est la seule valeur que "
               "l'observation du guide autorise, et rien d'autre dans son "
               "texte ne la contraint.")
    return b.render("Les jours apparents de decroissance et la hausse d "
                    "implicite requise, contre le poids d un jour non ouvre.")


def fig_th_relief_horloge() -> str:
    """Le relief de la hausse d'implicite, en poids et en échéance.

    La hauteur porte un logarithme parce que la grandeur parcourt deux ordres
    et demi ; l'infobulle publie la grandeur d'origine, jamais l'échelle
    interne.
    """
    brut = V.surface_horloges()
    z = [[math.log1p(v) for v in ligne] for ligne in brut]
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Thêta · le relief des horloges",
               "Ce qu'un lundi doit ajouter à une implicite courte",
               "hauteur logarithmique")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(w, 2) for w in V.SURF_HORLOGE_POIDS],
             col_labels=[_num(j, 0) for j in V.SURF_HORLOGE_JOURS],
             z_ticks=[(math.log1p(t), _pct(t, 0))
                      for t in (0.0, 0.05, 0.15, 0.35, 0.55)
                      if zlo <= math.log1p(t) <= zhi],
             tip="{v:.1%} d implicite", zero=zlo,
             tip_value=lambda v: math.expm1(v))

    b.annotation(0.0, 408.0,
                 "arête gauche : poids d'un jour non ouvré · arête "
                 "droite : échéance · hauteur : hausse requise")
    b.annotation(0.0, 424.0,
                 "l'arête de devant est au sol : à poids un, l'horloge "
                 "calendaire n'exige aucune hausse")
    b.annotation(0.0, 440.0,
                 "le relief monte vers le fond, où l'horloge de bourse "
                 "rencontre l'échéance de cinq jours")

    _source(b, "La surface a une propriété qu'une table ne rend pas : elle "
               "est plate au sol sur toute une arête, et cette arête est "
               "la convention calendaire. Ce n'est pas un effet de bord, "
               "c'est la définition — un thêta calendaire n'exige aucune "
               "correction de volatilité parce qu'il compte déjà les trois "
               "jours. Tout le reste du relief est ce que cette convention "
               "sous-estime. La hauteur porte un logarithme, sans quoi la "
               "colonne des échéances courtes réduirait le reste à un plat ; "
               "l'infobulle publie la hausse elle-même.")
    return b.render("Relief de la hausse d implicite de week-end, en poids "
                    "de jour non ouvre et en jours a l echeance.")


# ---------------------------------------------------------------------------
# V. Le signe
# ---------------------------------------------------------------------------


def fig_th_signe() -> str:
    """La frontière du thêta positif, et le fait qu'à taux nul elle n'existe pas.

    À gauche le thêta d'un put contre la moneyness, à quatre taux. À droite
    la part du plan concernée, qui part **exactement** de zéro.
    """
    t = 90.0 / 365.0
    ms = [0.50 + 0.005 * i for i in range(181)]

    b = _plate(500, "Thêta · le signe",
               "Le thêta positif est un fait de taux", "à 90 jours")

    p1 = Panel(b, PX1, 92, PW, 214, title="Le thêta d'un put",
               readout="par jour")
    series = []
    for cls, dash, r in (("hm7", "", 0.0), ("hm5", "6 3", 0.02),
                         ("hm3", "2 3", 0.04), ("hm1", "1 4", 0.06)):
        serie = [(m, V.termes_put(m * V.S_REF, V.S_REF, V.VOL_REF, t,
                                  r).total / 365.0) for m in ms]
        series.append((cls, dash, r, serie))
    lo = min(y for _, _, _, s in series for _, y in s) * 1.1
    hi = max(y for _, _, _, s in series for _, y in s) * 2.4
    p1.domain(0.50, 1.40, lo, hi)
    p1.frame()
    p1.grid_y(_ticks(lo, hi, 0.01), lambda v: _signed(v, 2), dx=32.0)
    p1.grid_x([0.6, 0.8, 1.0, 1.2, 1.4], lambda v: _num(v, 1),
              label="moneyness S/K")
    p1.hline(0.0, "lvl")
    for cls, dash, r, serie in series:
        p1.path(serie, cls, dash=dash,
                tip="taux " + _pct(r, 0))
    # Entre deux graduations, jamais sur l une : un filet de grille traverse
    # un texte sans qu aucun balayage ne croise les deux.
    p1.label(0.52, 0.0235, "au-dessus du zéro, le temps paie le porteur",
             dx=0, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="La part du plan",
               readout="à thêta positif")
    rs = [0.001 * i for i in range(81)]
    p2.domain(0.0, 0.08, 0.0, 0.55)
    p2.frame()
    p2.grid_y(_ticks(0.0, 0.5, 0.1), lambda v: _pct(v, 0), dx=34.0)
    p2.grid_x([0.0, 0.02, 0.04, 0.06, 0.08], lambda v: _pct(v, 0),
              label="taux sans risque")
    p2.path([(r, V.part_positive(r)) for r in rs], "hm6",
            tip="part du plan")
    p2.dot(0.0, 0.0, "hm7", "à taux nul, la région est vide", r=4.6)
    p2.label(0.0, 0.0, "exactement zéro", dx=8, dy=-8)

    b.legend(0.0, 352.0,
             [("hm7", "taux nul", ""), ("hm5", "deux pour cent", "6 3"),
              ("hm3", "quatre pour cent", "2 3"),
              ("hm1", "six pour cent", "1 4")],
             step=166.0, kind="line")
    b.annotation(0.0, 376.0,
                 "la courbe du taux nul reste sous zéro partout : le "
                 "terme qui crée la région est proportionnel au taux")
    b.annotation(0.0, 392.0,
                 "à " + _pct(V.TAUX, 0) + " la frontière est à "
                 + _num(V.frontiere_signe(30.0 / 365.0), 3)
                 + " de moneyness à trente jours, ce qui n'est pas si "
                 "profond")
    b.annotation(0.0, 408.0,
                 "l'avertissement du guide n'a rien coûté à personne pendant "
                 "la décennie où les taux étaient nuls")

    _source(b, "Le thêta d'un put porte un terme d'intérêt positif, "
               "+rKe^(−rT)N(−d₂), qui l'emporte sur la décroissance de "
               "valeur temps dès que celle-ci s'annule — c'est-à-dire dans la "
               "monnaie, là où la courbure a disparu. La part du plan est "
               "mesurée sur une grille de "
               + _num(len(V.PLAN_MONEYNESS) * len(V.PLAN_JOURS), 0)
               + " points couvrant les moneyness de 0,40 à 1,40 et les "
               "échéances d'une semaine à un an. Elle part de zéro et n'en "
               "part pas approximativement : à taux nul, aucun point de la "
               "grille n'a un thêta positif.")
    return b.render("Le theta d un put contre la moneyness a quatre taux, et "
                    "la part du plan a theta positif contre le taux.")


def fig_th_relief_signe() -> str:
    """Le relief de la frontière du signe, en taux et en échéance."""
    z = [list(ligne) for ligne in V.surface_signe()]
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Thêta · le relief du signe",
               "La frontière du signe, et l'arête où elle disparaît",
               "hauteur : la frontière")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_pct(r, 0) for r in V.SURF_SIGNE_TAUX],
             col_labels=[_num(j, 0) for j in V.SURF_SIGNE_JOURS],
             z_ticks=[(t, _num(t, 2)) for t in (0.0, 0.3, 0.6, 0.9)
                      if zlo <= t <= zhi],
             tip="frontiere {v:.3f}", zero=zlo)

    b.annotation(0.0, 408.0,
                 "arête gauche : taux · arête droite : échéance · "
                 "hauteur : moneyness de la frontière")
    b.annotation(0.0, 424.0,
                 "l'arête de devant est au sol : à taux nul la région "
                 "n'existe à aucune échéance")
    b.annotation(0.0, 440.0,
                 "le relief monte vers le fond, où un taux de six pour cent "
                 "rencontre une échéance de trois semaines")

    _source(b, "Une hauteur nulle ne veut pas dire ici « petit » mais "
               "« vide » : quand la frontière n'existe pas, la fonction rend "
               "zéro, et l'arête entière du taux nul se pose donc au sol. "
               "C'est la façon dont le dépôt publie une absence, et elle est "
               "préférable à une table où la même chose s'écrirait « aucune » "
               "six fois de suite. Le relief monte vers les taux élevés et "
               "les échéances courtes, c'est-à-dire là où le terme d'intérêt "
               "pèse le plus contre une valeur temps qui a déjà fondu.")
    return b.render("Relief de la frontiere du theta positif, en taux sans "
                    "risque et en jours a l echeance.")


# ---------------------------------------------------------------------------
# VI. Ce qu'il faudrait pour établir une prime de variance
# ---------------------------------------------------------------------------


def fig_th_preuve() -> str:
    """Ce qu'il faut d'expirations pour établir un avantage réel.

    À gauche les années requises contre l'avantage, en échelle
    logarithmique. À droite la fréquence de gain, qui monte à peine — et
    c'est le fait de la section.
    """
    seuil = V.avantage_pour_egaler_la_soiree()
    b = _plate(500, "Thêta · le budget d'information",
               "Sans avantage, la soirée affiche mieux que le mois avec",
               "sous " + _num(seuil, 1) + " point d'avantage")

    p1 = Panel(b, PX1, 92, PW, 214, title="Les années requises",
               readout="années")
    p1.domain(0.4, 5.0, 0.2, 40.0, xlog=True, ylog=True)
    p1.frame()
    p1.grid_y([0.3, 1.0, 3.0, 10.0, 30.0], lambda v: _num(v, 1), dx=32.0)
    p1.grid_x([0.5, 1.0, 2.0, 4.0], lambda v: _num(v, 1),
              label="écart implicite-réalisé, en points de volatilité")
    xs = [0.5 * (1.05 ** i) for i in range(60)]
    xs = [x for x in xs if x <= 4.6]
    ref = V.campagne_prime(1.0)
    p1.path([(x, ref.annees / x / x) for x in xs], "hm4", dash="6 3",
            tip="loi en carre inverse")
    for pts in V.PRIMES:
        c = V.campagne_prime(pts)
        p1.dot(pts, c.annees, "hm7",
               _num(pts, 1) + " point : " + _num(c.annees, 1) + " ans", r=4.2)

    p2 = Panel(b, PX2, 92, PW, 214, title="La fréquence de gain",
               readout="par expiration")
    c0 = V.simuler_vendeur()
    p2.domain(0.0, 4.6, 0.45, 0.95)
    p2.frame()
    p2.grid_y(_ticks(0.45, 0.95, 0.10), lambda v: _pct(v, 0), dx=36.0)
    p2.grid_x([0, 1, 2, 3, 4], lambda v: _num(v, 0),
              label="écart implicite-réalisé, en points de volatilité")
    p2.hline(0.5, "lvl")
    pts_serie = [(0.0, c0.couvert.taux)] + [(p, V.campagne_prime(p).taux)
                                            for p in V.PRIMES]
    p2.path(pts_serie, "hm6", tip="frequence de gain")
    for x, y in pts_serie:
        p2.dot(x, y, "hm7", _num(x, 1) + " point : " + _pct(y, 1), r=4.0)
    p2.hline(V.taux_par_intervalle(), "lvl")
    # Les deux references se nomment a gauche, ou la courbe monte encore de
    # bas en haut : posee a droite, une etiquette se ferait traverser.
    p2.label(0.05, V.taux_par_intervalle(), "une soirée sans avantage",
             dx=0, dy=-8)
    p2.label(0.05, 0.5, "un mois sans avantage", dx=0, dy=14)
    p2.dot(seuil, V.taux_par_intervalle(), "hm3",
           "le mois rejoint la soirée", r=4.4)

    b.legend(0.0, 352.0,
             [("hm7", "campagnes simulées", ""),
              ("hm4", "loi en carré inverse", "6 3"),
              ("hm6", "fréquence de gain par expiration", "")],
             step=222.0, kind="line")
    b.annotation(0.0, 376.0,
                 "un point d'avantage demande " + _num(ref.annees, 1)
                 + " ans à une expiration par mois, et le coût décroît en "
                 "carré")
    b.annotation(0.0, 392.0,
                 "sans aucun avantage, un vendeur gagne "
                 + _pct(V.taux_par_intervalle(), 0) + " de ses soirées et "
                 + _pct(c0.couvert.taux, 0) + " de ses mois")
    b.annotation(0.0, 408.0,
                 "il faut " + _num(seuil, 1) + " point d'avantage pour "
                 "qu'un mois affiche ce qu'une soirée affiche sans rien")

    _source(b, "La dispersion employée est celle de la troisième section, "
               "mesurée et non postulée, et elle ne bouge pas avec "
               "l'avantage : c'est ce qui rend le nombre d'expirations aussi "
               "sensible. Le résultat vaut d'être comparé au budget "
               "d'information de la quatrième partie, obtenu sur un objet "
               "entièrement différent — une décision intrajournalière, une "
               "géométrie déclarée, quatre cent soixante-quatorze décisions. "
               "Ici l'unité est l'expiration, et le compte se lit en années. "
               "La leçon est la même dans les deux cas : une fréquence de "
               "gain ne dit rien d'un avantage. Le croisement marqué sur le "
               "cadre de droite est le fait de la section — il faut un "
               "avantage réel de plus d'un point et demi de volatilité pour "
               "qu'un mois affiche ce qu'une soirée sans le moindre avantage "
               "affiche déjà, parce que les deux nombres ne comptent pas le "
               "même objet.")
    return b.render("Les annees requises pour etablir un avantage contre son "
                    "ampleur, et la frequence de gain correspondante.")


def fig_th_relief_preuve() -> str:
    """Le relief des années requises, en avantage et en couverture."""
    z = [[math.log10(v) for v in ligne] for ligne in V.surface_preuve()]
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Thêta · le relief de la preuve",
               "Ce que coûte un avantage qu'on n'a pas rendu grand",
               "hauteur logarithmique : années")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(n, 0) for n in V.SURF_PRIME_PAS],
             col_labels=[_num(p, 1) for p in V.SURF_PRIME_POINTS],
             z_ticks=[(math.log10(t), _num(t, 1))
                      for t in (0.1, 1.0, 10.0, 100.0)
                      if zlo <= math.log10(t) <= zhi],
             tip="{v:.1f} annees", zero=zlo,
             tip_value=lambda v: 10.0 ** v)

    b.annotation(0.0, 408.0,
                 "arête gauche : couvertures par jour · arête droite : "
                 "avantage en points · hauteur : années")
    b.annotation(0.0, 424.0,
                 "les deux axes diffèrent : l'avantage entre au carré, "
                 "la couverture ne réduit que la dispersion")
    b.annotation(0.0, 440.0,
                 "le coin du fond est un demi-point d'avantage couvert "
                 "une fois par jour : des décennies")

    _source(b, "Le relief dit ce qu'une table ne dit pas : les deux leviers "
               "ne sont pas comparables. Passer d'une couverture quotidienne "
               "à seize par jour divise la dispersion par quatre, donc le "
               "nombre d'expirations par seize ; mais doubler l'avantage le "
               "divise déjà par quatre à lui seul, et l'avantage n'est pas un "
               "réglage — il se subit. La hauteur porte un logarithme parce "
               "que la grandeur parcourt trois ordres, et l'infobulle publie "
               "les années elles-mêmes.")
    return b.render("Relief des annees requises pour etablir un avantage, en "
                    "couvertures par jour et en points de volatilite.")


# ---------------------------------------------------------------------------
# VII. Le décompte
# ---------------------------------------------------------------------------


def fig_th_reste() -> str:
    """Le décompte des neuf affirmations, et la seule qui parle de direction.

    La planche n'est pas une table déguisée : la barre porte une grandeur
    calculée — l'écart entre la fréquence qu'une affirmation fait espérer et
    l'espérance qu'elle rend — et les affirmations qui n'en portent aucune
    sont rangées à part.
    """
    aff = V.affirmations()
    compte = V.compte_par_grandeur()
    groupes = {}
    for a in aff:
        groupes.setdefault(a.grandeur, []).append(a)
    ordre = sorted(groupes, key=lambda g: (-len(groupes[g]), g))

    b = _plate(470, "Thêta · le décompte",
               "Neuf affirmations, et une seule parle de direction",
               _num(len(aff), 0) + " affirmations")

    p1 = Panel(b, PX1, 92, PW, 214, title="Ce qu'elles déplacent",
               readout="affirmations")
    p1.domain(0.0, 6.0, -0.6, len(ordre) - 0.4)
    p1.frame()
    p1.grid_x(_ticks(0.0, 6.0, 2.0), lambda v: _num(v, 0))
    for i, g in enumerate(ordre):
        y = len(ordre) - 1 - i
        cls = {"la direction": "hm7", "rien": "hm1"}.get(g, "hm5")
        p1.hbar(y, 0.0, len(groupes[g]), 13.0, cls,
                tip=g + " : " + _num(len(groupes[g]), 0))
        p1.label(0.0, y + 0.34, g, dx=4, dy=0)
        p1.label(len(groupes[g]), y, _num(len(groupes[g]), 0), dx=7, dy=4)

    p2 = Panel(b, PX2, 92, PW, 214, title="Les trois parties",
               readout="affirmations")
    fam = V.familles()
    haut = max(n for _, n in fam) * 1.35
    p2.domain(0.0, haut, -0.6, len(fam) - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, haut, 3.0), lambda v: _num(v, 0))
    for i, (nom, total) in enumerate(fam):
        y = len(fam) - 1 - i
        p2.hbar(y, 0.0, total, 13.0, "hm3", tip=nom)
        p2.label(0.0, y + 0.34, nom, dx=4, dy=0)
        p2.label(total, y, _num(total, 0), dx=7, dy=4)

    b.legend(0.0, 352.0,
             [("hm7", "touche à la direction"),
              ("hm5", "l'horloge ou le risque"),
              ("hm1", "ne déplace rien"),
              ("hm3", "les totaux, à droite")],
             step=166.0)
    b.annotation(0.0, 376.0,
                 _num(compte.get("l'horloge", 0), 0) + " affirmations "
                 "déplacent l'horloge, " + _num(compte.get("le risque", 0), 0)
                 + " le risque, une ne déplace rien")
    b.annotation(0.0, 392.0,
                 "la seule qui touche à la direction dit qu'il n'y en a "
                 "pas : à implicite égale au réalisé, zéro")
    b.annotation(0.0, 408.0,
                 "sur les " + _num(sum(n for _, n in V.familles()), 0)
                 + " affirmations des trois parties d'options, c'est la "
                 "seule")

    _source(b, "Le décompte se lit dans l'identité E[R] = (µ·E[τ∧T] − c)/a, "
               "qui est celle du document entier : une affirmation déplace "
               "l'horloge E[τ∧T], le risque a, ou la direction µ. Les "
               "trois parties consacrées aux options ont examiné des "
               "affirmations venues de guides extérieurs — "
               + _num(sum(n for _, n in V.familles()), 0) + " en tout — et "
               "le compte est "
               "toujours le même. Ce n'est pas un reproche adressé à ces "
               "guides : ils décrivent correctement des grandeurs qui "
               "existent. C'est un fait sur ce que ces grandeurs sont — des "
               "propriétés de la géométrie et de l'horloge, jamais du sens.")
    return b.render("Le decompte des affirmations par ce qu elles deplacent, "
                    "et le cumul des trois parties d options.")


def render_all() -> dict[str, str]:
    """Les quinze planches, dans l'ordre du document."""
    return {
        "thtermes": fig_th_termes(),
        "thinvariant": fig_th_invariant(),
        "thexemple": fig_th_exemple(),
        "thfrequence": fig_th_frequence(),
        "thintervalle": fig_th_intervalle(),
        "thcouverture": fig_th_couverture(),
        "threlief": fig_th_relief(),
        "thhorloges": fig_th_horloges(),
        "thpoids": fig_th_poids(),
        "threliefh": fig_th_relief_horloge(),
        "thsigne": fig_th_signe(),
        "threliefs": fig_th_relief_signe(),
        "thpreuve": fig_th_preuve(),
        "threliefp": fig_th_relief_preuve(),
        "threste": fig_th_reste(),
    }
