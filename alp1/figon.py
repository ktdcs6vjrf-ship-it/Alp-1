"""Les planches de l'affirmation venue du dehors.

Cinq planches, dans l'ordre de l'argument. La première montre d'où vient le
nombre — la loi de la position d'ouverture dans son propre range. La deuxième
montre que le conditionnel annoncé **est** la loi d'arrêt. La troisième porte
le verdict, et c'est la seule qui compte : l'espérance en fonction du taux de
réussite, avec le taux d'équilibre et les deux lectures possibles du chiffre
publié posés dessus. Les deux surfaces rangent ce qui reste — l'amplitude que
deux paramètres non observables donnent au résidu, et le plan de jeu équitable
sur lequel toute cette affaire se résume.
"""

from __future__ import annotations

import math

from . import overnight as O
from .figdisc import W, _plate, _source, _surface
from .figterm import Board, Panel, _num, _signed


def _pct(v: float, nd: int = 0) -> str:
    return _num(100.0 * v, nd) + " %"


# ---------------------------------------------------------------------------


def fig_on_position() -> str:
    """Où une marche sans dérive finit dans son propre range.

    C'est la planche qui contient déjà la réponse, avant tout marché. La loi
    de la position d'ouverture n'est pas uniforme, elle est en **U** : les
    bords sont chargés et le milieu creusé, parce que l'instant où une marche
    atteint son maximum suit une loi de l'arc sinus.

    La conséquence se lit dans le cadre de droite. La distance médiane de
    l'ouverture au bord le plus proche vaut un cinquième du range. Le bord
    opposé est donc quatre fois plus loin — et la loi d'arrêt donne alors
    quatre chances sur cinq de toucher le proche en premier.
    """
    us = sorted(u for u, _ in O.nuits())
    n = len(us)
    proche, loin = O.distance_au_bord()

    b = _plate(430, "Extrêmes overnight · la position",
               "Où le prix ouvre dans le range qu'il vient de creuser",
               _num(O.N_NUITS / 1000.0, 0) + " mille nuits simulées")

    # --- densité de u, par vingtièmes ---
    seaux = [0] * 20
    for u in us:
        seaux[min(int(u * 20.0), 19)] += 1
    dens = [c / n * 20.0 for c in seaux]

    pw = (W - 74.0) / 2.0 - 30.0
    p1 = Panel(b, 74.0, 92, pw, 214, title="Densité de la position",
               readout="1,0 = loi uniforme")
    p1.domain(0.0, 1.0, 0.0, max(dens) * 1.12)
    p1.frame()
    p1.grid_y([0.0, 0.5, 1.0, 1.5, 2.0], lambda v: _num(v, 1), dx=36.0)
    p1.grid_x([0.0, 0.25, 0.5, 0.75, 1.0], lambda v: _pct(v))
    p1.hline(1.0, "lvl")
    for i, d in enumerate(dens):
        p1.vbar((i + 0.5) / 20.0, 0.0, d, 11.0, "hm4",
                tip=_pct((i + 0.5) / 20.0) + " du range : "
                    + _num(d, 2) + " fois la densité uniforme")
    p1.label(0.5, 1.0, "loi uniforme", dx=0, dy=-8, anchor="middle",
             cls="dl halo")

    # --- distance au bord le plus proche ---
    d = sorted(min(u, 1.0 - u) for u in us)
    cum = [(d[int(q * (n - 1))], q) for q in
           [i / 60.0 for i in range(1, 61)]]
    p2 = Panel(b, 74.0 + (W - 74.0) / 2.0, 92, pw, 214,
               title="Distance au bord le plus proche",
               readout="fréquence cumulée")
    p2.domain(0.0, 0.5, 0.0, 1.0)
    p2.frame()
    p2.grid_y([0.0, 0.25, 0.5, 0.75, 1.0], lambda v: _pct(v), dx=40.0)
    p2.grid_x([0.0, 0.1, 0.2, 0.3, 0.4, 0.5], lambda v: _pct(v))
    p2.path(cum, "ln hm5", tip="fréquence cumulée")
    p2.hline(0.5, "lvl")
    p2.dot(proche, 0.5, "hm7",
           "médiane : " + _pct(proche, 1) + " du range", r=4.5)
    p2.label(proche, 0.5, "médiane " + _pct(proche, 1), dx=8, dy=14,
             cls="dl halo")

    b.annotation(0.0, 340.0,
                 "la loi est en U : le prix finit bien plus souvent près d'un "
                 "bord de son range que du milieu,")
    b.annotation(0.0, 356.0,
                 "parce que l'instant où une marche atteint son maximum suit "
                 "une loi de l'arc sinus")
    b.annotation(0.0, 380.0,
                 "bord proche à " + _pct(proche, 1) + " du range, bord opposé "
                 "à " + _pct(loin, 1) + " : un rapport de un à "
                 + _num(loin / proche, 1))

    _source(b, "La position d'ouverture est une grandeur sans dimension : "
               "elle ne dépend d'aucune volatilité, d'aucun instrument et "
               "d'aucune époque, puisque l'ouverture de 9:30 est le dernier "
               "point de la session overnight et que le range est celui de "
               "cette même session. Ce que cette planche montre n'est donc pas "
               "une propriété du contrat NQ : c'est une propriété des marches "
               "aléatoires. " + _pct(O.part_extremes(), 1) + " des séances "
               "ouvrent dans le dernier sixième d'un bord.")
    # Un libellé ARIA vit dans un attribut : la passe typographique ne visite
    # pas l'intérieur des balises, si bien qu'une apostrophe droite y survit,
    # et une apostrophe courbe y est refusée. On rédige donc sans aucune.
    return b.render("Densité de la position dans le range overnight au moment "
                    "de la réouverture, et distance au bord le plus proche, "
                    "sous une marche sans dérive.")


def fig_on_conditionnel() -> str:
    """Le conditionnel annoncé, posé sur la loi d'arrêt.

    La ligne droite n'est pas un ajustement : c'est le théorème d'arrêt
    optionnel, qui donne la probabilité de toucher une barrière avant l'autre
    comme le rapport des distances inverses. Les points mesurés s'y posent.

    Les deux traits horizontaux sont les deux lectures possibles du nombre
    publié. Ils tombent tous deux dans la bande où la loi nulle passe déjà :
    **il n'y a pas de place, entre la loi d'arrêt et le chiffre annoncé, pour
    une information sur le marché.**
    """
    c = O.retenue()
    lectures = O._lectures()

    b = _plate(432, "Extrêmes overnight · le conditionnel",
               "Le taux annoncé est-il autre chose que la distance ?",
               "loi d'arrêt optionnel")

    p = Panel(b, 82.0, 92, W - 110.0, 196,
              title="Probabilité de toucher le bord proche en premier",
              readout="parmi les séances qui cassent")
    p.domain(0.0, 0.5, 0.45, 1.0)
    p.frame()
    p.grid_y([0.5, 0.6, 0.7, 0.8, 0.9, 1.0], lambda v: _pct(v), dx=42.0)
    p.grid_x([0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
             lambda v: _pct(v), "distance au bord proche, en part du range")
    # La loi d'arrêt, tracée sans simulation.
    p.path([(x / 100.0, 1.0 - x / 100.0) for x in range(0, 51)], "ln hm2",
           tip="loi d'arrêt : 1 − distance")
    # Au ras du plancher, à gauche : partout ailleurs la droite ou un point
    # passe dessous, et un texte barré par un tracé ne se voit à aucun balayage.
    p.label(0.03, 0.53, "loi d'arrêt : 1 − distance", dx=0, dy=0,
            cls="dl halo")
    # Le cadre annonce « parmi les séances qui cassent » : il doit tracer cette
    # colonne-là et pas l'autre. Une planche qui affiche une série sous
    # l'intitulé d'une autre est indétectable à la relecture.
    for i, v in enumerate(c.par_decile_casse):
        p.dot((i + 0.5) * 0.05, v, "hm6",
              "mesuré : " + _pct(v, 1) + " à "
              + _pct((i + 0.5) * 0.05, 1) + " du bord", r=4.0)
    for nom, taux, _nul, _esp, _v in lectures:
        p.hline(taux, "lvl")
        # À droite : le faisceau de points occupe toute la moitié gauche.
        p.label(0.49, taux, "publié, lecture " + nom.split(" ")[0]
                + " : " + _pct(taux, 1), dx=0, dy=-7, anchor="end",
                cls="dl halo")

    b.annotation(0.0, 346.0,
                 "les points sont la loi nulle mesurée, la droite est le "
                 "théorème — la probabilité de toucher une barrière")
    b.annotation(0.0, 362.0,
                 "avant l'autre vaut le rapport des distances inverses, et "
                 "rien d'autre n'entre dans le calcul")

    _source(b, "Les deux traits horizontaux sont les deux lectures possibles "
               "du nombre publié, selon que son dénominateur compte toutes les "
               "séances ou les seules qui cassent quelque chose — la "
               "publication ne le dit pas, et l'écart entre les deux vaut "
             + _num((lectures[0][1] - lectures[1][1]) * 100.0, 1) + " points. "
               "Les deux tombent dans la bande que la loi d'arrêt traverse "
               "déjà. Les points s'en écartent de "
             + _num(O._ecart_arret()[0] * 100.0, 1) + " point en moyenne, et le "
               "décrochage se concentre aux deux premières positions : la "
               "trajectoire avance par minute, et la première minute de séance "
               "porte une amplitude comparable aux distances mesurées là. La "
               "loi continue est la limite d'un pas qui tend vers zéro.")
    return b.render("Probabilité de toucher le bord proche en premier selon la "
                    "distance à ce bord, mesurée sous loi nulle et comparée "
                    "à la loi de barrière.")


def fig_on_lecture() -> str:
    """Le verdict, et il tient dans une droite.

    L'espérance d'un pari à deux issues est **linéaire** en son taux de
    réussite. La droite coupe zéro au taux d'équilibre, et ce taux est
    entièrement fixé par la géométrie : viser un bord à un cinquième du range
    en risquant les quatre autres cinquièmes.

    Trois points sont posés dessus. La loi nulle, le chiffre publié lu d'une
    façon, le même chiffre lu de l'autre. **Deux tombent du mauvais côté de
    zéro et un du bon** — et ce qui les sépare n'est pas une propriété du
    marché, c'est une phrase que la publication n'écrit pas.
    """
    c = O.retenue()
    seuil = c.taux_equilibre()
    lectures = O._lectures()
    nul_casse = (c.haut_si_dessus_casse + c.bas_si_dessous_casse) / 2.0

    b = _plate(424, "Extrêmes overnight · le verdict",
               "Ce taux paie-t-il la géométrie qu'il impose ?",
               "cible sur le bord proche, stop sur l'autre")

    lo, hi = 0.60, 0.90
    p = Panel(b, 82.0, 92, W - 110.0, 200,
              title="Espérance par décision, selon le taux de réussite",
              readout="rapport gain-risque : 1 pour " + _num(1.0 / c.rapport, 1))
    ys = [c.esperance_au_taux(x / 1000.0) for x in range(int(lo * 1000),
                                                         int(hi * 1000) + 1, 5)]
    p.domain(lo, hi, min(ys) * 1.1, max(ys) * 1.15)
    p.frame()
    p.grid_y([-0.2, -0.1, 0.0, 0.1, 0.2], lambda v: _signed(v, 2) + " R",
             dx=52.0)
    p.grid_x([0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90], lambda v: _pct(v))
    p.hline(0.0, "lvl")
    p.path([(lo + i * (hi - lo) / 200.0,
             c.esperance_au_taux(lo + i * (hi - lo) / 200.0))
            for i in range(201)], "ln hm5", tip="espérance")
    p.vline(seuil, "lvl")
    p.label(seuil, max(ys) * 1.05, "équilibre " + _pct(seuil, 1), dx=6, dy=0,
            cls="dl halo")
    # La loi nulle et la lecture B tombent au même endroit à un dixième de
    # point près : deux marques y seraient illisibles, et surtout elles
    # cacheraient le fait. On en pose une seule, et on le dit.
    for taux in (nul_casse, lectures[1][1]):
        p.dot(taux, c.esperance_au_taux(taux), "hm7",
              "loi nulle " + _pct(nul_casse, 1) + " et lecture B "
              + _pct(lectures[1][1], 1) + " : le même point", r=5.0)
    p.label(lectures[1][1], c.esperance_au_taux(lectures[1][1]),
            "loi nulle = publié, lecture B", dx=0, dy=26.0, anchor="middle",
            cls="dl halo")
    ta = lectures[0][1]
    p.dot(ta, c.esperance_au_taux(ta), "hm7",
          "publié, lecture A : " + _pct(ta, 1) + " → "
          + _signed(c.esperance_au_taux(ta), 4) + " R", r=5.0)
    p.label(ta, c.esperance_au_taux(ta), "publié, lecture A", dx=-10, dy=-12,
            anchor="end", cls="dl halo")

    b.annotation(0.0, 328.0,
                 "l'espérance d'un pari à deux issues est linéaire en son taux "
                 "de réussite, et la droite coupe zéro")
    b.annotation(0.0, 344.0,
                 "au taux que la géométrie exige — ici " + _pct(seuil, 1)
                 + ", parce que le bord visé est quatre fois plus près que le stop")

    _source(b, "Les deux points « publié » sont le même chiffre, lu de deux "
               "façons : selon que son dénominateur compte toutes les séances "
               "ou les seules qui cassent quelque chose. La publication ne le "
               "précise pas. L'écart vaut "
             + _num((lectures[0][1] - lectures[1][1]) * 100.0, 1) + " points de "
               "taux, quand l'effet revendiqué au-dessus de la loi nulle en "
               "vaut au mieux "
             + _num((lectures[0][1] - nul_casse) * 100.0, 1) + ". Sous la lecture B, la "
               "loi nulle rend le chiffre publié à un dixième de point près et "
               "il n'y a rien à expliquer ; sous la lecture A, il reste un "
               "résidu — mais la boîte des paramètres non observables lui donne "
               "à elle seule une amplitude comparable.")
    return b.render("Espérance par décision en fonction du taux de réussite, "
                    "avec le seuil de rentabilité de la géométrie et les "
                    "deux lectures du chiffre publié.")


def fig_on_boite() -> str:
    """L'amplitude que deux réglages non observables donnent au résidu.

    Le rapport de volatilité entre la nuit et le jour n'est pas dans les
    nombres publiés, ni la dispersion de volatilité d'une séance à l'autre. Le
    relief montre ce que la prédiction nulle devient quand on parcourt leur
    boîte plausible : elle se promène sur une amplitude comparable à l'effet
    revendiqué.

    C'est la figure que le dépôt connaît déjà sous d'autres noms — la taille de
    grappe qui décide de la rareté d'un déséquilibre de footprint, la hauteur
    de rangée qui décide de celle d'un extrême pauvre. **Un résidu plus petit
    que l'amplitude de son hypothèse n'est pas un résultat.**
    """
    z = O.surface_boite()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)
    c = O.retenue()

    b = _plate(486, "Extrêmes overnight · la boîte",
               "Ce que le résidu doit à deux réglages que personne n'observe",
               "hauteur : conditionnel prédit")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(k, 2) for k in O.SURF_K],
             col_labels=[_num(s, 2) for s in O.SURF_S],
             z_ticks=[(t, _pct(t, 0)) for t in (0.64, 0.69, 0.74)],
             tip="{v:.3f}", zero=zlo)

    b.annotation(0.0, 408.0,
                 "arête gauche : rapport de volatilité nuit/jour · arête "
                 "droite : dispersion de volatilité par séance")
    b.annotation(0.0, 424.0,
                 "la prédiction nulle parcourt " + _num((zhi - zlo) * 100.0, 1)
                 + " points sur la boîte, quand l'effet revendiqué en vaut "
                   "quelques-uns")
    b.annotation(0.0, 440.0,
                 "le couple retenu est " + _num(c.k, 2) + " et "
                 + _num(c.s_vol, 2) + ", calibré sur deux nombres sans direction")

    _source(b, "Aucun des deux axes n'est observable dans les sept nombres "
               "publiés, et aucun n'est arbitraire : la nuit échange moins que "
               "le jour, et toutes les séances n'ont pas la même volatilité. "
               "Le couple retenu est calibré sur les deux nombres qui ne "
               "portent aucune direction — la part des séances qui cassent les "
               "deux côtés, celle qui n'en casse aucun — de sorte qu'il ne "
               "reste aucun degré de liberté pour les nombres de direction. "
               "C'est la seule façon de rendre la prédiction non circulaire, et "
               "c'est aussi ce qui rend cette planche lisible : le relief est "
               "ce que l'hypothèse permet, pas ce qu'on a choisi.")
    return b.render("Conditionnel prédit par la loi nulle sur la boîte des "
                    "deux paramètres non observables.")


def fig_on_plan() -> str:
    """Le plan de jeu équitable, où toute l'affaire se résume.

    Deux axes suffisent : le taux de réussite et le rapport gain-risque. Rien
    d'autre n'entre — ni le niveau, ni l'instrument, ni l'heure. Le relief est
    un plan incliné, et le sol est posé exactement à l'espérance nulle : ce qui
    dépasse gagne, ce qui s'enfonce perd.

    L'affirmation examinée demande un taux élevé sur un rapport étroit. C'est
    le coin où le plan passe sous le sol, et il y passe **quel que soit le
    marché** — puisque aucune propriété du marché n'a servi à le tracer.
    """
    z = O.surface_plan()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)
    c = O.retenue()

    b = _plate(486, "Extrêmes overnight · le plan",
               "Le taux et la géométrie, et rien d'autre",
               "hauteur : E[R] par décision")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_pct(t) for t in O.SURF_TAUX],
             col_labels=["1 pour " + _num(1.0 / r, 1) for r in O.SURF_RAPPORT],
             z_ticks=[(t, _signed(t, 1)) for t in (-0.4, 0.0, 0.4)],
             tip="{v:+.3f} R", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : taux de réussite · arête droite : rapport "
                 "gain-risque · le sol est posé à l'espérance nulle")
    b.annotation(0.0, 424.0,
                 "l'affirmation examinée demande " + _pct(0.759, 1)
                 + " sur un rapport de 1 pour " + _num(1.0 / c.rapport, 1)
                 + " : le plan y passe sous le sol")
    b.annotation(0.0, 440.0,
                 "aucune propriété du marché n'entre dans ce relief")

    _source(b, "Ce relief n'est pas simulé : c'est l'arithmétique d'un pari à "
               "deux issues, augmentée de la friction mesurée — "
             + _signed(c.wald, 4) + " R par décision à la géométrie de "
               "l'affirmation. Il suffit à trancher, et c'est le point : un "
               "taux de réussite ne s'interprète jamais seul. Le même "
             + _pct(0.759, 1) + " est excellent sur un rapport de un pour un "
               "et perdant sur un rapport de un pour " + _num(1.0 / c.rapport, 1)
             + ". La publication donne le taux et tait le rapport.")
    return b.render("Espérance par décision sur le plan du taux de réussite et "
                    "du rapport gain-risque, sol posé au niveau zéro.")


FIGURES = {
    "onposition": fig_on_position,
    "onconditionnel": fig_on_conditionnel,
    "onlecture": fig_on_lecture,
    "onboite": fig_on_boite,
    "onplan": fig_on_plan,
}


def render_all() -> dict[str, str]:
    return {k: f() for k, f in FIGURES.items()}
