"""Les planches de la robustesse : ce que la forme des queues déplace, et ce qu'elle ne déplace pas.

Cinq planches, et elles répondent dans l'ordre à une seule objection : « votre
théorème suppose une loi normale ». Les deux premières montrent que les queues
sont bien différentes — comptées, pas dessinées. La troisième montre que
l'espérance ne bouge pas. La quatrième montre ce qui bouge. Les deux surfaces
mettent les deux constats sur leurs axes.

Le langage graphique est celui du dépôt : fond de terminal, jetons de couleur
de `figcss`, aucune couleur en dur. Les six lois sont rangées de la plus fine
à la plus épaisse et prennent la rampe séquentielle dans cet ordre : la teinte
porte donc une grandeur, et non une identité arbitraire.
"""

from __future__ import annotations

import math

from . import robustesse as R
from .figdisc import W, _plate, _ramp, _source, _surface
from .figterm import Board, Panel, _num, _signed

#: La rampe, du plus clair au plus foncé, dans l'ordre des lois.
CLASSES = ("ln hm1", "ln hm2", "ln hm3", "ln hm4", "ln hm5", "ln hm7")
POINTS = ("hm1", "hm2", "hm3", "hm4", "hm5", "hm7")


def _p(v: float) -> str:
    """Une probabilité en pour-cent, courte."""
    if v >= 0.01:
        return _num(100.0 * v, 0) + " %"
    if v >= 0.001:
        return _num(100.0 * v, 1) + " %"
    return _num(100.0 * v, 2) + " %"


# ---------------------------------------------------------------------------
# 1. Les queues, comptées
# ---------------------------------------------------------------------------


#: Sous ce nombre d'observations dans une queue, un rapport de queues cesse
#: d'être une estimation et devient un tirage. Le seuil est appliqué, pas
#: commenté : la courbe s'arrête là où le comptage devient trop mince.
MIN_COMPTE = 100


def fig_queues() -> str:
    """Les deux queues de chaque loi, comptées puis rapportées l'une à l'autre.

    L'affirmation «&nbsp;les queues ne sont pas les mêmes&nbsp;» est vraie, et
    cette planche est la seule du document à la montrer plutôt qu'à la
    répéter. Elle compte, sur quatre cent mille tirages par loi, la fréquence
    d'un incrément au-delà de `x` écarts-types.

    Le cadre de gauche porte les niveaux&nbsp;: à variance égale, la queue
    gauche de la Student à trois degrés est deux ordres de grandeur au-dessus
    de celle de la gaussienne à six écarts-types.

    Le cadre de droite porte ce que le débat vise vraiment — **le rapport des
    deux queues d'une même loi**. Une loi symétrique y trace une ligne plate
    sur un, et quatre des six lois y sont indiscernables. Deux ne le sont pas,
    et elles vont en sens contraire.

    La loi à sauts, celle qui imite un indice actions, décolle&nbsp;: sa queue
    gauche vaut plusieurs fois sa queue droite à trois écarts-types, et le
    facteur exact est calculé, jamais écrit.
    **L'asymétrie d'un indice est négative.** Ce qui est illimité, sur un
    indice, c'est la baisse rapide.

    La loi à plancher, elle, prend au mot «&nbsp;la baisse est plafonnée&nbsp;»
    et sa queue gauche s'arrête net à un écart-type&nbsp;: son rapport n'existe
    plus au-delà, et aucune courbe ne peut donc en être tracée. C'est une
    absence exacte, pas une absence d'observation, et la planche le dit plutôt
    que de laisser un vide muet.
    """
    q = R.queues()
    ls = R.lois()
    n = R.N_MOMENTS
    seuil = MIN_COMPTE / n

    b = _plate(452, "Robustesse · les queues",
               "À quelle fréquence un incrément dépasse x écarts-types ?",
               "400 mille tirages par loi")

    lo = 2.0e-5
    p1 = Panel(b, 66.0, 92, (W - 66.0) / 2.0 - 34.0, 214,
               title="Queue gauche : P(incrément ≤ −x)", readout="vers la perte")
    p1.domain(0.5, 6.0, lo, 0.35, ylog=True)
    p1.frame()
    p1.grid_y([10.0 ** e for e in range(-4, 0)], _p, "fréquence", dx=46.0)
    p1.grid_x([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], lambda v: _num(v, 0) + " σ")
    for i, loi in enumerate(ls):
        pts = [(x, bas) for x, bas, _ in q[loi.cle] if bas > lo]
        if len(pts) >= 2:
            p1.path(pts, CLASSES[i], tip=loi.nom)
    # Aucun nom posé sur une courbe dans ce cadre : les six s'y croisent et
    # toute étiquette y tombe sur un tracé voisin — ce qui ne se voit pas au
    # balayage, qui ne croise que les boîtes de texte entre elles. La légende
    # sous la planche porte les six noms, et le cadre de droite porte la
    # lecture. Ce qui reste ici est la seule phrase que le cadre établit.
    # Rien n'est écrit dans ce cadre. Les six courbes le traversent de part en
    # part et une étiquette y tombe forcément sur un tracé — défaut qu'aucun
    # des trois balayages ne voit, puisqu'ils ne croisent que des boîtes de
    # texte entre elles. La phrase que le cadre établit est donc posée sous la
    # planche, où elle a de la place.

    p2 = Panel(b, 66.0 + (W - 66.0) / 2.0, 92, (W - 66.0) / 2.0 - 34.0, 214,
               title="Rapport des deux queues", readout="gauche ÷ droite")
    p2.domain(0.9, 4.6, 0.55, 24.0, ylog=True)
    p2.frame()
    # « symétrique » est porté par la graduation et non par une étiquette
    # posée dans le cadre : à un pour un, les quatre lois symétriques se
    # superposent, et toute étiquette posée là tombe sur elles.
    p2.grid_y([1.0, 2.0, 5.0, 10.0, 20.0],
              lambda v: _num(v, 0) + (" × symétrique" if v == 1.0 else " ×"),
              dx=92.0)
    p2.grid_x([1.0, 2.0, 3.0, 4.0], lambda v: _num(v, 0) + " σ")
    p2.hline(1.0, "lvl")
    for i, loi in enumerate(ls):
        pts = [(x, bas / haut) for x, bas, haut in q[loi.cle]
               if bas >= seuil and haut >= seuil]
        if len(pts) >= 2:
            p2.path(pts, CLASSES[i], tip=loi.nom)
    saut = [(x, bas / haut) for x, bas, haut in q["merton"]
            if bas >= seuil and haut >= seuil]
    p2.label(saut[-1][0], saut[-1][1], "sauts", dx=-6, dy=-8, anchor="end",
             cls="dl halo")
    p2.label(2.6, 0.60, "plancher : plus aucune baisse au-delà de 1 σ",
             dx=0, dy=0, anchor="middle", cls="dl halo")

    b.legend(0.0, 340.0, [(POINTS[i], ls[i].court) for i in range(len(ls))],
             step=110.0)

    v = R.values()
    ql = {loi.cle: {x: (bb, hh) for x, bb, hh in q[loi.cle]} for loi in ls}
    g, d = ql["merton"][3.0]
    b.annotation(0.0, 372.0,
                 "les six lois ont la même variance par minute : seule la "
                 "forme de leurs queues change")
    b.annotation(0.0, 396.0,
                 "à trois écarts-types, la loi à sauts tombe " + _num(g / d, 1)
                 + " fois plus souvent à gauche qu'à droite :")
    b.annotation(0.0, 412.0,
                 "l'asymétrie d'un indice est négative, pas positive")
    b.annotation(0.0, 428.0,
                 "et la loi à plancher n'a plus aucune queue gauche au-delà de "
                 + v["r_plancher_plafonnee"].replace("−", "") + " σ")

    _source(b, "Chaque courbe est une fréquence comptée, jamais une densité "
               "tracée : c'est ce qui autorise à comparer six lois dont trois "
               "n'ont pas de forme fermée. Les six ont la même variance par "
               "minute — la différence visible ici est donc de forme, et "
               "d'elle seule. Le cadre de droite s'arrête là où l'une des deux "
               "queues compte moins de " + _num(MIN_COMPTE, 0) + " observations : "
               "au-delà, un rapport de queues n'est plus une estimation mais "
               "un tirage, et le seuil est appliqué plutôt que commenté. La "
               "loi à plancher n'y figure pas du tout, et c'est exact : son "
               "numérateur est nul au-delà d'un écart-type. Asymétrie "
               "mesurée : " + v["r_asym_merton"] + " pour les sauts, "
             + v["r_asym_plafonnee"] + " pour le plancher.")
    # Un libellé ARIA vit dans un attribut : il ne peut porter ni apostrophe
    # droite — la passe typographique ne visite pas l'intérieur des balises —
    # ni apostrophe courbe, qui casserait le balisage à la relecture. Les deux
    # tests le vérifient, et la seule sortie est de n'en écrire aucune.
    return b.render("Fréquence des incréments au-delà de x écarts-types, "
                    "et rapport des deux queues, pour six lois de même "
                    "variance.")


# ---------------------------------------------------------------------------
# 2. L'invariance
# ---------------------------------------------------------------------------


def _barres(b: Board, px: float, py: float, pw: float, ph: float,
            titre: str, lecture: str, drift: float, ls) -> Panel:
    """Un cadre d'espérances mesurées, chacune contre sa propre prédiction."""
    ms = {m.cle: m for m in R.mesurer(drift)}
    vals = [ms[l.cle] for l in ls]
    bas = min(min(m.esperance - 2.5 * m.erreur_type, m.wald) for m in vals)
    haut = max(max(m.esperance + 2.5 * m.erreur_type, m.wald) for m in vals)
    marge = (haut - bas) * 0.28 or 0.02
    p = Panel(b, px, py, pw, ph, title=titre, readout=lecture)
    p.domain(-0.6, len(ls) - 0.4, bas - marge, haut + marge)
    p.frame()
    pas = (haut - bas + 2 * marge) / 4.0
    ordre = 10.0 ** math.floor(math.log10(pas))
    pas = ordre * max(1.0, round(pas / ordre))
    depart = math.ceil((bas - marge) / pas) * pas
    ticks = [depart + i * pas for i in range(9)
             if depart + i * pas <= haut + marge]
    p.grid_y(ticks, lambda v: _signed(v, 3), "E[R]", dx=54.0)
    p.grid_x(list(range(len(ls))), lambda v: ls[int(v)].court)
    for i, m in enumerate(vals):
        # La prédiction d'abord : le point mesuré doit se poser dessus.
        p.hbar(m.wald, i - 0.34, i + 0.34, 1.4, "lvl",
               tip="prédiction de Wald : " + _signed(m.wald, 4))
        p.vbar(float(i), m.esperance - 2.0 * m.erreur_type,
               m.esperance + 2.0 * m.erreur_type, 2.2, POINTS[i],
               tip="deux erreurs types")
        p.dot(float(i), m.esperance, POINTS[i],
              ls[i].nom + " — mesurée " + _signed(m.esperance, 4)
              + ", prédite " + _signed(m.wald, 4), r=4.2)
    return p


def fig_invariance() -> str:
    """L'espérance mesurée de six lois, chacune contre sa propre prédiction.

    C'est la planche du résultat. Chaque point est une espérance simulée sur
    des dizaines de milliers de décisions ; chaque trait horizontal est ce que
    l'identité de Wald prédit **avant** de simuler. Le point tombe sur le
    trait, six fois, dans les deux cadres.

    À gauche, sous prix sans dérive, le trait est le même pour les six lois :
    `−c/a`. La kurtosis infinie de la Student à trois degrés ne l'écarte pas,
    la queue gauche épaisse de la loi à sauts non plus, et le plancher de la
    loi asymétrique non plus. **La forme des queues ne crée ni ne détruit
    d'espérance.**

    À droite, sous la dérive haute du domaine plausible, le trait n'est plus
    commun : il vaut `(µ·E[τ∧T] − c)/a`, et `E[τ∧T]` dépend de la loi. Les
    traits se déplacent donc, et les points se déplacent avec eux. C'est
    exactement la façon dont la forme des queues entre dans le résultat : par
    le temps de marché, et par rien d'autre.
    """
    ls = R.lois()
    v = R.values()
    b = _plate(534, "Robustesse · l'invariance",
               "L'espérance mesurée tombe-t-elle sur ce que Wald prédit ?",
               "barre : deux erreurs types")

    # Deux cadres **empilés** et non côte à côte : à six lois par cadre, une
    # demi-largeur ne laisse que quarante pixels par intitulé d'axe et les
    # noms se chevauchent. La pleine largeur en laisse quatre-vingt-quinze.
    pw = W - 88.0
    _barres(b, 78.0, 96, pw, 146, "Sans dérive",
            "prédiction commune : " + v["r_prediction"] + " R", 0.0, ls)
    _barres(b, 78.0, 300, pw, 146,
            "Sous " + v["r_derive_haute"] + " point par heure",
            "prédiction propre à chaque loi", R.DERIVE_HAUTE, ls)

    b.annotation(0.0, 486.0,
                 "trait horizontal : la prédiction, écrite avant de simuler · "
                 "point : la mesure · barre : deux erreurs types")
    b.annotation(0.0, 502.0,
                 "en haut la prédiction est la même pour les six lois ; en "
                 "bas elle suit le temps de marché de chacune")

    _source(b, "Aucun point ne s'écarte de sa prédiction de plus de "
               + v["r_ecart_max_derive"] + " erreurs types, pour un seuil de "
               "décision de " + v["r_z_seuil"] + " — celui de Bonferroni sur "
               "les " + v["r_tests"] + " verdicts de la campagne. La "
               "correction n'est pas une indulgence : à cinq pour cent et "
               + v["r_tests"] + " tests, la probabilité qu'au moins un écart "
               "dépasse deux erreurs types alors même que le théorème tient "
               "partout vaut " + v["r_faux_positif"] + " %. Publier une "
               "réfutation sur cette base reviendrait à annoncer une "
               "découverte au premier faux positif, faute que ce document "
               "reproche ailleurs et qu'il s'applique donc à lui-même.")
    return b.render("Espérance simulée de six lois de prix, comparée à la "
                    "prédiction de Wald, sans dérive puis sous dérive.")


# ---------------------------------------------------------------------------
# 3. Ce qui bouge
# ---------------------------------------------------------------------------


def fig_deplacement() -> str:
    """Ce que la forme des queues déplace vraiment : le temps, donc le seuil.

    L'espérance ne bouge pas ; trois autres grandeurs bougent, et il faut les
    montrer sinon la section conclurait que la forme des queues n'a aucune
    conséquence, ce qui serait faux.

    Le cadre de gauche porte le temps de marché. Il varie d'un tiers entre la
    loi la plus rapide et la plus lente, et le sens surprend : **à variance
    égale, une loi à queues épaisses fait durer les trades**. La raison tient
    en une phrase — la variance étant fixée, ce que la loi met dans ses queues
    rares, elle le retire de son corps ; la minute typique bouge donc moins,
    et la barrière vient plus tard.

    Le cadre de droite convertit ce temps en seuil, `µ* = c/E[τ∧T]`, et c'est
    là que la lecture devient utile : le seuil de rentabilité varie de la même
    fraction, en sens inverse. La critique des queues épaisses atterrit donc,
    mais pas où elle visait — elle ne réfute pas l'invariance, elle déplace le
    seuil, et de bien moins que la géométrie ne le fait.
    """
    ls = R.lois()
    v = R.values()
    ms = {m.cle: m for m in R.mesurer(0.0)}
    ref = ms["gauss"]

    b = _plate(524, "Robustesse · ce qui bouge",
               "Ce que les queues déplacent, une fois l'espérance écartée",
               "sans dérive, stop " + v["r_stop_pct"] + " %")

    pw = W - 88.0
    taus = [ms[l.cle].exposition for l in ls]
    p1 = Panel(b, 78.0, 96, pw, 146, title="Temps de marché par décision",
               readout="E[τ∧T], en minutes")
    p1.domain(-0.6, len(ls) - 0.4, 0.0, max(taus) * 1.22)
    p1.frame()
    p1.grid_y([0.0, 40.0, 80.0, 120.0, 160.0],
              lambda x: _num(x, 0) + " min", dx=52.0)
    p1.grid_x(list(range(len(ls))), lambda x: ls[int(x)].court)
    p1.hline(ref.exposition, "lvl")
    for i, t in enumerate(taus):
        p1.vbar(float(i), 0.0, t, 34.0, POINTS[i],
                tip=ls[i].nom + " — " + _num(t, 1) + " min")
    p1.label(len(ls) - 1.0, ref.exposition, "gaussienne", dx=-4, dy=-7,
             cls="dl halo", anchor="end")

    seuils = [ms[l.cle].seuil for l in ls]
    p2 = Panel(b, 78.0, 300, pw, 146,
               title="Seuil de rentabilité", readout="µ* = c/E[τ∧T], en pt/h")
    p2.domain(-0.6, len(ls) - 0.4, 0.0, max(seuils) * 1.22)
    p2.frame()
    p2.grid_y([0.0, 0.05, 0.10, 0.15, 0.20],
              lambda x: _num(x, 2), dx=44.0)
    p2.grid_x(list(range(len(ls))), lambda x: ls[int(x)].court)
    p2.hline(ref.seuil, "lvl")
    for i, t in enumerate(seuils):
        p2.vbar(float(i), 0.0, t, 34.0, POINTS[i],
                tip=ls[i].nom + " — " + _num(t, 3) + " pt/h")
    p2.label(len(ls) - 1.0, ref.seuil, "gaussienne", dx=-4, dy=-7,
             cls="dl halo", anchor="end")

    b.annotation(0.0, 486.0,
                 "filet horizontal : la gaussienne, prise pour repère · à "
                 "variance égale, une queue plus épaisse allonge le trade,")
    b.annotation(0.0, 502.0,
                 "parce que ce qu'une loi met dans ses queues rares, elle le "
                 "retire de sa minute ordinaire")

    _source(b, "Le seuil est l'image exacte du temps, retournée : "
               "µ* = c/E[τ∧T], avec c = " + v["r_friction"] + " point de "
               "friction. Les six lois s'étalent sur "
             + v["r_seuil_ecart"] + " % de seuil, quand le seul passage du "
               "stop de " + v["r_surf_stop_min"] + " % à "
             + v["r_surf_stop_max"] + " % en déplace "
             + v["r_surf_seuil_geo"] + " fois plus. La forme des queues "
               "compte donc, et elle compte moins que la première décision de "
               "géométrie que l'opérateur prend.")
    return b.render("Temps de marché et seuil de rentabilité de six lois de "
                    "prix de même variance.")


# ---------------------------------------------------------------------------
# 4 et 5. Les deux surfaces
# ---------------------------------------------------------------------------


def fig_robu_esperance() -> str:
    """L'espérance sur le plan de l'épaisseur de queue et de la dérive.

    Un plan incliné, et sa pente n'a qu'une direction. Le relief monte le long
    de l'axe de la dérive et reste plat le long de l'axe des queues : c'est le
    théorème, dessiné.

    L'arête la plus proche du lecteur est la dérive nulle. Elle est
    horizontale à l'œil et le reste sur quatre ordres de grandeur de kurtosis,
    de zéro à trente-cinq : c'est là, et non dans une phrase, que se lit le
    fait qu'une queue épaisse ne fabrique pas d'espérance.
    """
    v = R.values()
    z = R.surface_esperance()
    plat = [ligne[-1] for ligne in z]
    zlo = min(min(l) for l in z)
    zhi = max(max(l) for l in z)

    b = _plate(470, "Robustesse · l'espérance",
               "Ce que la dérive ajoute, ce que les queues n'ajoutent pas",
               "hauteur : E[R] par décision")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(R.kurtosis_mixte(x), 1)
                         for x in sorted(R.SURF_V2, reverse=True)],
             # L'unité est portée par le libellé : sans elle, le « 0,0 » de la
             # dérive et le « 0,0 » de la kurtosis se touchent au coin le plus
             # proche et rien ne dit lequel appartient à quelle arête.
             col_labels=[_num(d, 1) + " pt/h"
                         for d in sorted(R.SURF_DERIVE, reverse=True)],
             z_ticks=[(t, _signed(t, 2))
                      for t in (-0.05, 0.2, 0.45, 0.7)],
             tip="{v:+.3f} R", zero=zlo)

    b.annotation(0.0, 396.0,
                 "arête gauche : kurtosis excédentaire, de 0 à "
                 + v["r_surf_kurt_max"] + " · arête droite : dérive du "
                   "marché, en points par heure")
    b.annotation(0.0, 412.0,
                 "la pente n'a qu'une direction : celle de la dérive")
    b.annotation(0.0, 428.0,
                 "sur l'arête la plus proche, la dérive est nulle et le "
                 "relief est plat")

    _source(b, "La famille de lois est continue : un mélange d'échelles à deux "
               "points, à variance constante, dont la kurtosis se règle par "
               "une formule. Toutes les cellules voient le même flux de "
               "nombres aléatoires — la graine ne dépend que de l'indice de "
               "trajectoire, jamais de la cellule — et c'est ce qui rend le "
               "relief lisse sans qu'aucun lissage soit appliqué. Le long de "
               "l'arête à dérive nulle, l'espérance moyenne vaut "
             + v["r_surf_esp_nulle"] + " R pour une prédiction de "
             + v["r_prediction"] + " R, et l'étendue de toute l'arête vaut "
             + v["r_surf_esp_etendue"] + " R.")
    return b.render("Espérance par décision sur le plan de la kurtosis et de "
                    "la dérive : un plan incliné dans la seule direction de "
                    "la dérive.")


def fig_robu_seuil() -> str:
    """Le seuil sur le plan de l'épaisseur de queue et de la largeur de stop.

    La planche qui range les deux effets. Les deux axes déplacent le seuil ;
    ils ne le déplacent pas du tout dans le même rapport, et c'est le seul
    point que la figure existe pour établir.

    Le long de l'axe de la géométrie, du stop le plus serré au plus large, le
    seuil est divisé par près de treize. Le long de l'axe des queues, de la
    gaussienne à une kurtosis excédentaire de trente-cinq, il est divisé par
    moins de deux. **L'opérateur déplace donc son seuil sept fois plus en
    choisissant sa géométrie qu'en changeant de marché.**
    """
    v = R.values()
    z = R.surface_seuil()
    zlo = min(min(l) for l in z)
    zhi = max(max(l) for l in z)

    b = _plate(470, "Robustesse · le seuil",
               "Les queues déplacent le seuil, la géométrie bien plus",
               "hauteur : µ* en pt/h")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(R.kurtosis_mixte(x), 1) for x in sorted(R.SURF_V2)],
             col_labels=[_num(p, 3) + " %" for p in sorted(R.SURF_STOP_PCT)],
             z_ticks=[(t, _num(t, 2)) for t in (0.1, 0.4, 0.7, 1.0, 1.2)],
             tip="{v:.3f} pt/h", zero=zlo)

    b.annotation(0.0, 396.0,
                 "arête gauche : kurtosis excédentaire · arête droite : "
                 "largeur de stop, en pour-cent de l'indice")
    b.annotation(0.0, 412.0,
                 "le relief tombe " + v["r_surf_domine"] + " fois plus vite "
                 "quand on élargit le stop que quand on épaissit les queues")

    _source(b, "Le seuil est mesuré, non calculé : chaque cellule simule le "
               "temps de marché sous sa propre loi et sa propre géométrie, "
               "puis rend µ* = c/E[τ∧T]. Le long de l'arête de la géométrie "
               "le seuil est divisé par " + v["r_surf_seuil_geo"] + " ; le "
               "long de l'arête des queues, par "
             + v["r_surf_seuil_queue"] + " seulement. Le domaine de dérive que "
               "le document nº 1 appelle plausible s'arrête à "
             + v["r_derive_haute"] + " point par heure : le coin le plus "
               "haut du relief reste donc sous ce plafond, ce qui veut dire "
               "qu'aucune de ces configurations n'est impossible — c'est le "
               "stop de " + v["r_stop_pct"] + " % qui les sauve toutes, et "
               "non la forme du marché.")
    return b.render("Seuil de rentabilité sur le plan de la kurtosis et de la "
                    "largeur de stop.")


FIGURES = {
    "rqueues": fig_queues,
    "rinvariance": fig_invariance,
    "rdeplacement": fig_deplacement,
    "resperance": fig_robu_esperance,
    "rseuil": fig_robu_seuil,
}


def render_all() -> dict[str, str]:
    return {k: f() for k, f in FIGURES.items()}
