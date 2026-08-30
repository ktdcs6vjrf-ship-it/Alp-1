"""Sortir d'une position : ce que douze concepts font, et sur quel seul axe.

Deux planches. La première montre la mesure, la seconde l'identité sur
laquelle elle tombe.

`sortiewald` porte trois cadres qui partagent une abscisse — le temps de
position, en minutes. À gauche, l'espérance sous une dérive déclarée : les
douze concepts se posent sur une droite, et cette droite est l'identité de
Wald, tracée sans être ajustée. Au centre, la même mesure sous un prix sans
dérive : les douze se confondent, et l'échelle du cadre le dit en toutes
lettres, car elle vaut un cent-quarantième de celle du voisin. À droite, la
dispersion, qui suit la racine du temps — c'est elle qui explique pourquoi le
Sharpe par trade décroît quand on raccourcit.

`sortiesurface` porte le plan (temps de position, dérive) et la frontière du
zéro qui le traverse. La hauteur n'est pas ajustée non plus : c'est
`(µ·t/60 − c)/a`, et les douze concepts se lisent comme douze abscisses sur
l'arête gauche. La frontière est l'hyperbole `µ = 60c/t` — le seuil de
rentabilité vu depuis le temps plutôt que depuis la géométrie.
"""

from __future__ import annotations

import math

from .figquant import surface
from .figterm import Board, Panel, _num, _signed
from . import horloge as H
from . import sorties as S
from . import seuil as SE
from .report11 import DERIVE_TRAVAIL

#: Dérives balayées par la surface, en points d'indice par heure.
#:
#: Le domaine se déduit de ce que la figure existe pour montrer, et non d'une
#: envie de couvrir large. La frontière du zéro est `µ = 60c/t` : elle vaut
#: 0,79 pt/h à vingt-cinq minutes de position et 0,05 à la séance entière.
#: Une grille montant à quatre points par heure la rejetait hors du cadre —
#: une seule maille sur vingt y était négative, et la légende décrivait alors
#: une frontière que la figure ne portait pas. Celle-ci l'encadre.
#:
#: La grille ne part pas de zéro, et c'est délibéré. À dérive nulle
#: l'espérance vaut `−c/a` pour tout temps de position — c'est la table de la
#: loi nulle, pas cette surface. En gardant la colonne, la maille de bord
#: mélangeait cette valeur constante à sa voisine et passait au positif par
#: moyenne des quatre coins : la figure affichait alors une bande claire le
#: long de l'arête la plus défavorable du plan.
DERIVES_3D = (0.1, 0.2, 0.4, 0.8, 1.6)

#: Temps de position balayés par la surface, en minutes.
TEMPS_3D = (25.0, 60.0, 120.0, 240.0, 390.0)


def _wald(t_min: float, drift_per_hour: float) -> float:
    a, c = S.stop_points_declare(), S.friction()
    return (drift_per_hour / 60.0 * t_min - c) / a


def fig_sortie_wald() -> str:
    """Les douze concepts, leur espérance, leur loi nulle et leur dispersion.

    Le cadre du milieu demande une précaution que le dépôt a déjà payée une
    fois : une fenêtre étroite décrit son bornage, pas la donnée. Son étendue
    est donc écrite dans sa lecture chiffrée, et rapportée à celle du cadre
    voisin. Sans cela, douze points confondus se liraient comme douze points
    distincts.
    """
    nul = {m.cle: m for m in S.mesurer(0.0)}
    der = {m.cle: m for m in S.mesurer(DERIVE_TRAVAIL)}
    rs = S.regles()
    ratio = S.friction() / S.stop_points_declare()
    b = Board(660, 488)

    # --- Cadre 1 : sous dérive déclarée, les points tombent sur la droite ---
    ys = [der[r.cle].esperance for r in rs]
    p1 = Panel(b, 78, 52, 236, 156, title="Sous dérive déclarée",
               readout=f"µ = {_num(DERIVE_TRAVAIL, 1)} pt/h")
    p1.domain(0.0, 410.0, -0.2, 1.6)
    p1.frame()
    p1.grid_y([0.0, 0.5, 1.0, 1.5], lambda v: _signed(v, 1), label="E[R] (R)")
    p1.grid_x([0, 130, 260, 390], lambda v: _num(v, 0),
              label="temps de position (min)")
    p1.hline(0.0, "zero")
    p1.path([(t, _wald(t, DERIVE_TRAVAIL)) for t in (0.0, 410.0)], "s2")
    for r in rs:
        m = der[r.cle]
        p1.dot(m.exposition, m.esperance, "s1",
               f"{r.nom} — {m.exposition:.0f} min, {m.esperance:+.3f} R")
    p1.label(20.0, 1.30, "identité de Wald", dx=0, dy=0, cls="dl halo")

    # --- Cadre 2 : sous prix sans dérive, ils se confondent ------------------
    vals = [nul[r.cle].esperance for r in rs]
    etendue = max(vals) - min(vals)
    p2 = Panel(b, 372, 52, 220, 156, title="Sous prix sans dérive",
               readout=f"étendue {_num(etendue, 3)} R")
    # Le domaine se déduit des barres, pas des points. Écrit à la main, il
    # laissait la moitié des barres d'erreur au-dessus du cadre, où `vbar` les
    # traçait tout de même : le découpage n'est pas une dispense de calculer
    # un domaine, et c'est le piège que le dépôt a déjà payé huit fois.
    bornes = [m.esperance + s * 2.0 * m.ecart_ref_se
              for m in (nul[r.cle] for r in rs) for s in (-1.0, 1.0)]
    marge = (max(bornes) - min(bornes)) * 0.08
    lo, hi = min(bornes) - marge, max(bornes) + marge
    p2.domain(0.0, 410.0, lo, hi)
    p2.frame()
    p2.grid_y([0.01 * k for k in range(math.ceil(lo / 0.01),
                                       math.floor(hi / 0.01) + 1)],
              lambda v: _signed(v, 2), label="E[R] (R)")
    p2.grid_x([0, 130, 260, 390], lambda v: _num(v, 0),
              label="temps de position (min)")
    p2.hline(-ratio, "lvl strong")
    for r in rs:
        m = nul[r.cle]
        p2.dot(m.exposition, m.esperance, "s1",
               f"{r.nom} — {m.esperance:+.4f} R")
        demi = 2.0 * m.ecart_ref_se
        if demi > 0:
            p2.vbar(m.exposition, m.esperance - demi, m.esperance + demi,
                    1.6, "s1f", f"± 2 erreurs types : {demi:.4f}")
    # À gauche, l'étiquette tombait sur la première barre d'erreur ; le bord
    # droit du cadre n'en porte aucune.
    p2.label(405.0, -ratio, "−c/a = " + _num(-ratio, 4), dx=0, dy=-7,
             anchor="end", cls="dl halo")

    # --- Cadre 3 : la dispersion suit la racine du temps --------------------
    p3 = Panel(b, 78, 288, 514, 108, title="La dispersion achetée",
               readout="σ[R] contre √t")
    p3.domain(0.0, 410.0, 0.0, 3.0)
    p3.frame()
    p3.grid_y([0.0, 1.0, 2.0, 3.0], lambda v: _num(v, 0), label="σ[R] (R)")
    p3.grid_x([0, 130, 260, 390], lambda v: _num(v, 0),
              label="temps de position (min)")
    ref = nul["clot"]
    p3.path([(t, ref.ecart_type * math.sqrt(t / ref.exposition))
             for t in (1.0 + 4.0 * k for k in range(103))], "s2")
    for r in rs:
        m = nul[r.cle]
        p3.dot(m.exposition, m.ecart_type, "s1",
               f"{r.nom} — σ = {m.ecart_type:.2f} R")
    p3.label(150.0, 0.55, "σ ∝ √t, ancrée sur la clôture sèche", dx=0, dy=0,
             cls="dl halo")

    # Dix-huit points sous l'axe du troisième cadre : posée à 424, la
    # légende tombait exactement sur l'intitulé « temps de position ».
    # `s1` et `s2` sont des classes de trait : en pastille elles se rendent
    # en carrés vides. La légende de trait est celle qui les montre.
    b.legend(78, 442, [("s1", "un concept de sortie"),
                       ("s2", "l'identité, non ajustée")],
             step=250, kind="line")
    b.caption(330, 464, "les douze concepts se rangent sur la droite de Wald "
                        "sous dérive, et se confondent sans elle,")
    b.caption(330, 478, "ce qui ne laisse au choix d'une sortie qu'un seul "
                        "axe : le temps de position")
    return b.render(
        "Espérance des douze concepts de sortie selon le temps de position, "
        "sous dérive déclarée puis sous prix sans dérive, et dispersion "
        "associée")


def fig_sortie_surface() -> str:
    """L'espérance sur le plan (temps de position, dérive), et sa frontière.

    La hauteur est l'identité, pas un ajustement : la planche précédente a
    montré que les douze mesures y tombent. Ce que cette surface ajoute est la
    **forme de la frontière du zéro**, qui est l'hyperbole `µ = 60c/t`. Elle
    dit la chose que le chapitre existe pour dire : raccourcir une position
    relève le seuil de dérive qu'il faut pour la rentabiliser, et le relève
    d'autant plus vite qu'on raccourcit déjà.
    """
    z = [[_wald(t, d) for d in DERIVES_3D] for t in TEMPS_3D]
    plat = [v for ligne in z for v in ligne]
    marge = (max(plat) - min(plat)) * 0.06
    zlo, zhi = min(plat) - marge, max(plat) + marge

    def signe(v: float) -> str:
        return "dn" if v < 0.0 else "up"

    b = Board(660, 398)
    b.add('<text class="hdr" x="0" y="18">L\'espérance sur le plan du temps '
          'et de la dérive</text>')
    b.add('<text class="sub" x="0" y="34">hauteur et couleur : '
          '(µ·t/60 − c)/a · la frontière rouge-vert est µ = 60c/t</text>')
    b.add('<line class="ba" x1="0" y1="46" x2="660" y2="46"/>')
    surface(
        b, 356.0, 150.0, z, zlo, zhi, cx=40.0, cy=13.0, cz=150.0,
        row_labels=[_num(t, 0) for t in TEMPS_3D[:-1]]
                   + [_num(TEMPS_3D[-1], 0) + " min"],
        col_labels=[_num(d, 1) for d in DERIVES_3D[:-1]]
                   + [_num(DERIVES_3D[-1], 1) + " pt/h"],
        z_ticks=[(0.25 * k, _signed(0.25 * k, 2))
                 for k in range(math.ceil(zlo / 0.25),
                                math.floor(zhi / 0.25) + 1)],
        tip="E[R] = {v:+.3f} R", classify=signe, zero=0.0,
    )
    b.annotation(0, 300, "la frontière recule vers les fortes dérives")
    b.annotation(0, 314, "à mesure que la position se raccourcit")
    b.legend(0, 338, [("dn", "espérance négative — µ < 60c/t"),
                      ("up", "espérance positive")], step=330, kind="swatch")
    # Chaque ligne de pied sauf la dernière doit finir sur une virgule : le
    # raccord pose un point partout ailleurs, et la phrase se coupe en deux.
    b.caption(330, 362, "l'arête gauche est le temps de position, l'arête "
                        "droite la dérive du marché,")
    b.caption(330, 376, "la hauteur l'espérance nette que leur produit "
                        "commande,")
    b.caption(330, 390, "et la couleur la moyenne des quatre coins de chaque "
                        "maille — l'arête de plus faible dérive n'y est donc "
                        "pas lisible")
    return b.render(
        "Surface de l espérance nette sur le plan du temps de position et de "
        "la dérive du marché, avec la frontière du signe")


#: Largeurs de stop et exposants de la carte du régime.
STOPS_3D = (0.010, 0.015, 0.020, 0.030, 0.050)
EXPOSANTS_3D = (0.46, 0.50, 0.55, 0.60, 0.70)


def fig_gamma_horloge() -> str:
    """Ce que le régime de gamma déplace, et la colonne qui ne bouge pas.

    Le premier cadre porte la probabilité d'atteindre le target selon
    l'exposant d'échelle. Elle est plate, et son domaine va de zéro à dix
    pour cent — une fenêtre étroite ferait passer la platitude pour un choix
    de cadrage, et le dépôt a déjà payé ce défaut une fois, sur une figure
    qui affirmait le contraire de ce théorème.
    """
    exps = list(H.EXPOSANTS)
    b = Board(660, 464)

    # Les deux grandeurs partagent le cadre, et c'est le contraste qui est le
    # contenu. Seule, la courbe plate occupait cinq pour cent de la hauteur —
    # le balayage d'occupation l'a signalée — et la resserrer aurait fait
    # passer sa platitude pour un cadrage. Elles tiennent toutes deux entre
    # zéro et dix, l'une en pour-cent et l'autre en minutes.
    p1 = Panel(b, 78, 52, 236, 156, title="Plate, et pas plate",
               readout=f"p(target) = {_num(100.0 / (1.0 + H.RR), 3)} %")
    p1.domain(0.44, 0.72, 0.0, 10.0)
    p1.frame()
    p1.grid_y([0, 2, 4, 6, 8, 10], lambda v: _num(v, 0),
              label="p(target) en %  ·  E[τ] en min")
    p1.grid_x([0.45, 0.55, 0.65], lambda v: _num(v, 2),
              label="exposant d'échelle H")
    hs = [0.44 + 0.28 * k / 60.0 for k in range(61)]
    p1.path([(h, H.regime(h).exposition) for h in hs], "s2")
    p1.path([(h, 100.0 * H.regime(h).p_target) for h in hs], "s1")
    for h in exps:
        r = H.regime(h)
        p1.dot(h, 100.0 * r.p_target, "s1",
               f"H = {h:.2f} : p(target) = {100 * r.p_target:.3f} %")
        p1.dot(h, r.exposition, "s2",
               f"H = {h:.2f} : E[τ] = {r.exposition:.2f} min")
    p1.label(0.448, 8.6, "temps de position", dx=0, dy=0, cls="dl halo")
    p1.label(0.448, 3.1, "probabilité de touche", dx=0, dy=0, cls="dl halo")

    p2 = Panel(b, 372, 52, 220, 156, title="Ce qu'il déplace",
               readout="µ* à la géométrie déclarée")
    p2.domain(0.44, 0.72, 0.0, 10.5)
    p2.frame()
    p2.grid_y([0, 2, 4, 6, 8, 10], lambda v: _num(v, 0),
              label="seuil µ* (pt/h)")
    p2.grid_x([0.45, 0.55, 0.65], lambda v: _num(v, 2),
              label="exposant d'échelle H")
    p2.band_y(SE.PLAUSIBLE_DRIFT_PER_HOUR[0], SE.PLAUSIBLE_DRIFT_PER_HOUR[1],
              "wash")
    p2.path([(0.44 + 0.28 * k / 60.0, H.regime(0.44 + 0.28 * k / 60.0).seuil)
             for k in range(61)], "s2")
    for h in exps:
        p2.dot(h, H.regime(h).seuil, "s2", f"H = {h:.2f}")
    p2.label(0.70, SE.PLAUSIBLE_DRIFT_PER_HOUR[1], "dérive plausible",
             dx=-4, dy=14, anchor="end", cls="lg halo")

    p3 = Panel(b, 78, 288, 514, 108, title="La fenêtre où la lecture décide",
               readout=f"dérive de travail {_num(DERIVE_TRAVAIL, 1)} pt/h")
    p3.domain(0.008, 0.06, 0.05, 20.0, xlog=True, ylog=True)
    p3.frame()
    p3.grid_y([0.1, 1.0, 10.0], lambda v: _num(v, 1), label="µ* (pt/h)")
    p3.grid_x([0.01, 0.02, 0.03, 0.05],
              lambda v: _num(v, 3) + " %", label="largeur de stop")
    # La bande vient **avant** les tracés. Posée après, elle recouvrait les
    # deux courbes dans la seule région que ce cadre existe pour montrer.
    bas, haut = H.fenetre()
    p3.band_x(bas, haut, "wash")
    pcts = [0.008 * (0.06 / 0.008) ** (k / 60.0) for k in range(61)]
    p3.path([(x, H.seuil_par_stop(x, min(exps))) for x in pcts], "s1")
    p3.path([(x, H.seuil_par_stop(x, max(exps))) for x in pcts], "s2")
    p3.hline(DERIVE_TRAVAIL, "lvl strong")
    p3.label(0.0092, 12.0, "perdue", dx=0, dy=0, cls="lg halo")
    p3.label(haut, 12.0, "gagnée", dx=6, dy=0, cls="lg halo")
    p3.label(bas, 0.075, "la fenêtre", dx=2, dy=0, cls="dl halo")
    # Les couleurs ne portent pas la même chose ici que dans le premier
    # cadre : les courbes se nomment donc sur place, et la légende de pied
    # ne décrit plus que le premier.
    p3.label(0.058, H.seuil_par_stop(0.058, min(exps)), "chop",
             dx=-4, dy=-6, anchor="end", cls="dl halo")
    p3.label(0.058, H.seuil_par_stop(0.058, max(exps)), "tendance",
             dx=-4, dy=-6, anchor="end", cls="dl halo")

    # Pas de légende de pied ici. Les quatre courbes se nomment déjà sur
    # place, et une pastille commune aux trois cadres aurait fait porter à
    # une même couleur deux grandeurs différentes — la probabilité de touche
    # dans le premier cadre, le régime de chop dans le troisième.
    b.caption(330, 442, "le régime déplace le temps de position et le seuil, "
                        "jamais la probabilité de touche,")
    b.caption(330, 456, "et il ne décide du signe de l'espérance que dans la "
                        "bande étroite du troisième cadre")
    return b.render(
        "Probabilité d atteindre le target et seuil de rentabilité selon "
        "l exposant d échelle, et fenêtre de largeur de stop où le régime "
        "décide du signe de l espérance")


def fig_gamma_carte() -> str:
    """La carte du régime sur le plan (largeur de stop, exposant).

    La couleur ne code pas la hauteur mais le verdict : une maille verte est
    une configuration dont le seuil tombe sous la dérive de travail. La
    frontière entre les deux est ce que la figure existe pour montrer, et la
    rangée du stop déclaré reste entièrement rouge.
    """
    z = [[math.log10(H.seuil_par_stop(p, h)) for h in EXPOSANTS_3D]
         for p in STOPS_3D]
    plat = [v for ligne in z for v in ligne]
    marge = (max(plat) - min(plat)) * 0.06
    zlo, zhi = min(plat) - marge, max(plat) + marge
    limite = math.log10(DERIVE_TRAVAIL)

    def verdict(v: float) -> str:
        return "dn" if v > limite else "up"

    b = Board(660, 398)
    b.add('<text class="hdr" x="0" y="18">Le seuil sur le plan du stop et du '
          'régime</text>')
    b.add('<text class="sub" x="0" y="34">hauteur : logarithme de µ* · '
          'couleur : le seuil tombe-t-il sous la dérive de travail ?</text>')
    b.add('<line class="ba" x1="0" y1="46" x2="660" y2="46"/>')
    # Hauteur ramenée de 150 à 105, largeur de 40 à 32 : la nappe descendait
    # vers l'avant-droit, c'est-à-dire exactement là où l'aide place les
    # libellés de l'arête des colonnes, et les deux se chevauchaient sans
    # qu'aucune boîte de texte n'en croise une autre — le balayage ne pouvait
    # pas le voir, seul l'œil le pouvait.
    surface(
        b, 356.0, 158.0, z, zlo, zhi, cx=32.0, cy=13.0, cz=105.0,
        row_labels=[_num(p, 3) for p in STOPS_3D[:-1]]
                   + [_num(STOPS_3D[-1], 3) + " %"],
        col_labels=[_num(h, 2) for h in EXPOSANTS_3D[:-1]]
                   + ["H = " + _num(EXPOSANTS_3D[-1], 2)],
        z_ticks=[(math.log10(v), _num(v, 1) + " pt/h")
                 for v in (0.2, 1.0, DERIVE_TRAVAIL, 10.0)
                 if zlo <= math.log10(v) <= zhi],
        tip="µ* = {v:.2f} (log₁₀ des pt/h)", classify=verdict, zero=limite,
    )
    b.annotation(0, 300, "la rangée du stop déclaré reste rouge")
    b.annotation(0, 314, "d'un bout à l'autre de la plage de régimes")
    b.legend(0, 338, [("dn", "seuil au-dessus de la dérive de travail"),
                      ("up", "seuil en dessous")], step=330, kind="swatch")
    b.caption(330, 362, "l'arête gauche est la largeur du stop, l'arête "
                        "droite le régime de gamma,")
    b.caption(330, 376, "et la couleur dit si la configuration passe — le "
                        "régime ne décide qu'où la frontière traverse une "
                        "rangée")
    return b.render(
        "Surface du seuil de rentabilité sur le plan de la largeur de stop et "
        "de l exposant d échelle, colorée par le verdict")


ALL_FIGURES = {
    "sortiewald": fig_sortie_wald,
    "sortiesurface": fig_sortie_surface,
    "gammahorloge": fig_gamma_horloge,
    "gammacarte": fig_gamma_carte,
}


def render_all() -> dict[str, str]:
    return {name: fn() for name, fn in ALL_FIGURES.items()}
