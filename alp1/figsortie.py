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
from . import sorties as S
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

    b = Board(660, 406)
    b.add('<text class="hdr" x="0" y="18">L\'espérance sur le plan du temps '
          'et de la dérive</text>')
    b.add('<text class="sub" x="0" y="34">hauteur et couleur : '
          '(µ·t/60 − c)/a · la frontière rouge-vert est µ = 60c/t</text>')
    b.add('<line class="ba" x1="0" y1="46" x2="660" y2="46"/>')
    surface(
        b, 356.0, 172.0, z, zlo, zhi, cx=40.0, cy=13.0, cz=150.0,
        row_labels=[_num(t, 0) for t in TEMPS_3D[:-1]]
                   + [_num(TEMPS_3D[-1], 0) + " min"],
        col_labels=[_num(d, 1) for d in DERIVES_3D[:-1]]
                   + [_num(DERIVES_3D[-1], 1) + " pt/h"],
        z_ticks=[(0.25 * k, _signed(0.25 * k, 2))
                 for k in range(math.ceil(zlo / 0.25),
                                math.floor(zhi / 0.25) + 1)],
        tip="E[R] = {v:+.3f} R", classify=signe, zero=0.0,
    )
    b.annotation(0, 322, "la frontière recule vers les fortes dérives")
    b.annotation(0, 336, "à mesure que la position se raccourcit")
    b.legend(0, 360, [("dn", "espérance négative — µ < 60c/t"),
                      ("up", "espérance positive")], step=330, kind="swatch")
    b.caption(330, 384, "l'arête gauche est le temps de position, l'arête "
                        "droite la dérive du marché,")
    b.caption(330, 398, "et la hauteur l'espérance nette que leur produit "
                        "commande")
    return b.render(
        "Surface de l espérance nette sur le plan du temps de position et de "
        "la dérive du marché, avec la frontière du signe")


ALL_FIGURES = {
    "sortiewald": fig_sortie_wald,
    "sortiesurface": fig_sortie_surface,
}


def render_all() -> dict[str, str]:
    return {name: fn() for name, fn in ALL_FIGURES.items()}
