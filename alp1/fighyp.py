"""L'hypothèse d'edge du document nº 1, imagée sur ses deux faces.

La troisième partie du document nº 1 publie ses résultats sous une hypothèse
unique, `µ = 2 µ*`, et le module `report15` montre qu'elle n'est pas un
paramètre du marché mais une fonction de la friction. Les tables le disent en
chiffres ; ces deux planches le donnent à voir, ce qui n'est pas la même
chose : **la table ne montre pas que la région où l'hypothèse est plausible
et la région où elle est démontrable sont disjointes.** Une figure, si.

`hyphypothese` porte trois cadres plans. Le premier trace le délai
d'établissement selon la dérive supposée, en échelle logarithmique parce
qu'il couvre quatre ordres de grandeur, avec le domaine plausible posé
derrière : la courbe n'existe pas là où le domaine plausible tombe, et c'est
tout le propos. Le deuxième décompose l'espérance publiée en ce que la dérive
apporte et ce que la friction prend — à l'hypothèse du document, la barre
nette est exactement la hauteur de la barre de friction, ce qui est
l'identité `E[R] = c/a` rendue visible. Le troisième suit le rapport
Sortino/Sharpe, donné pour insensible au signal par une phrase que ce constat
a fait retirer, et qui se déplace de moitié sur le domaine.

`hyphypothese3d` porte la surface du délai sur le plan (géométrie × dérive),
c'est-à-dire la table de détectabilité de la partie, dépliée le long de l'axe
que cette table tient fixe. Le plateau de la couleur d'alerte n'est pas un
artefact de bornage : c'est la région où aucun horizon de carrière ne suffit,
et la borne existe pour qu'elle se voie comme un mur plutôt que comme une
falaise sans fond.
"""

from __future__ import annotations

import math

from .figquant import heat_class, surface
from .figterm import Board, Panel, _num, _signed
from .overfit import minimum_backtest_length
from .pathstats import min_track_record_length
from . import quant as q
from . import seuil

#: Plafond de délai porté par la surface, en années. Ce n'est pas un réglage
#: d'affichage : c'est une durée de carrière, et la surface existe pour dire
#: où elle ne suffit pas. Les mailles qui le touchent portent un délai
#: supérieur ou infini, et la couleur d'alerte les désigne comme telles.
PLAFOND_ANS = 40.0

#: Dérives balayées par la surface, en points d'indice par heure.
DERIVES_3D = (10.0, 14.0, 18.0, 22.0, 26.0)


def _law(mu_per_hour: float, rr: float = q.RR_REF):
    """Loi du trade sous une dérive **déclarée**, à la géométrie `1:rr`."""
    o = q.geometry(rr)
    cible = (mu_per_hour / 60.0 * o.expected_time - q.FRICTION) / q.STOP_PTS
    return q.null_law(rr).tilted_to_mean(cible)


def _annees(mu_per_hour: float, rr: float = q.RR_REF,
            essais: int = 0) -> float:
    """Délai d'établissement en années. `essais` = 0 donne le MinTRL nu."""
    law = _law(mu_per_hour, rr)
    sr = law.sharpe_per_trade
    n = (minimum_backtest_length(sr, essais) if essais
         else min_track_record_length(sr, 0.0, law.skewness,
                                      law.excess_kurtosis))
    return n / q.TRADES_PER_YEAR


def _mu_star() -> float:
    return 60.0 * q.FRICTION / q.geometry(q.RR_REF).expected_time


def fig_hypothese() -> str:
    """Ce que le multiple de dérive décide, sur les trois axes qui comptent.

    Le premier cadre est celui qui décide de la lecture du document. Le délai
    d'établissement diverge au seuil de rentabilité — il n'y a rien à établir
    d'un Sharpe négatif — et le domaine que le document appelle plausible
    tombe entièrement à gauche de cette divergence. **Les deux courbes
    n'existent nulle part au-dessus du domaine plausible**, et la figure ne
    peut donc pas les y tracer : c'est l'absence de tracé qui porte le
    résultat, et l'annotation la nomme pour qu'on ne la lise pas comme un
    défaut de rendu.
    """
    mu_star = _mu_star()
    mu_ref = q.DRIFT_MULTIPLE * mu_star
    bas, haut = seuil.PLAUSIBLE_DRIFT_PER_HOUR
    b = Board(660, 502)

    # --- Cadre 1 : le délai ------------------------------------------------
    p1 = Panel(b, 84, 52, 244, 158, title="Le délai d'établissement",
               readout=f"µ* = {_num(mu_star, 2)} pt/h")
    p1.domain(0.0, 28.0, 0.1, 1000.0, ylog=True)
    p1.frame()
    p1.grid_y([0.1, 1.0, 10.0, 100.0, 1000.0],
              lambda v: _num(v, 1) if v < 1 else _num(v, 0), label="années")
    p1.grid_x([0, 7, 14, 21, 28], lambda v: _num(v, 0), label="dérive (pt/h)")
    p1.band_x(bas, haut, "wash")
    # Le tracé part juste au-dessus du seuil : en deçà le Sharpe est négatif
    # et le délai n'est pas un grand nombre, il n'existe pas. Le découpage du
    # cadre ferait passer les deux cas pour le même.
    xs = [mu_star * (1.0 + 0.004 * k) for k in range(1, 700)]
    xs = [x for x in xs if x <= 28.0]
    p1.path([(x, _annees(x)) for x in xs], "s1")
    p1.path([(x, _annees(x, essais=q.N_TRIALS_REF)) for x in xs], "s2")
    p1.vline(mu_star, "lvl strong")
    # Les deux points de l'hypothèse tombent à moins d'une demi-décade l'un
    # de l'autre : leurs étiquettes se chevauchaient, posées du même côté.
    # L'une passe donc à gauche du point et l'autre à droite.
    # Les deux points de l'hypothèse tombent à moins d'une demi-décade l'un de
    # l'autre. Posées du même côté leurs étiquettes se chevauchaient ; posées
    # l'une à gauche et l'autre à droite, elles tombaient sur les courbes.
    # Chacune part donc du côté que sa courbe laisse libre : la courbe basse
    # vers le bas et la gauche, la haute vers le haut et la droite.
    for cls, essais, dx, dy, ancre in (("s1", 0, -10.0, 16.0, "end"),
                                       ("s2", q.N_TRIALS_REF, 10.0, -9.0, "start")):
        y = _annees(mu_ref, essais=essais)
        p1.dot(mu_ref, y, cls, f"µ = 2 µ* : {y:.2f} an")
        p1.label(mu_ref, y, _num(y, 2) + " an", dx=dx, dy=dy, anchor=ancre,
                 cls="dl halo")
    p1.label(bas, 420.0, "plausible", dx=1, dy=0, cls="lg halo")
    # En bas de sa verticale, cette étiquette venait toucher celle du point
    # bas ; en haut, la verticale est seule.
    p1.label(mu_star, 620.0, "µ*", dx=5, dy=0, cls="dl halo")

    # --- Cadre 2 : d'où vient l'espérance ----------------------------------
    ratio = q.FRICTION / q.STOP_PTS
    o = q.geometry(q.RR_REF)
    cas = ((haut, "plausible"), (mu_star, "µ*"), (mu_ref, "2 µ*"))
    p2 = Panel(b, 402, 52, 190, 158, title="D'où vient l'espérance",
               readout=f"c/a = {_num(ratio, 2)} R")
    p2.domain(0.0, 3.0, -0.7, 1.25)
    p2.frame()
    p2.grid_y([-0.5, 0.0, 0.5, 1.0], lambda v: _signed(v, 1), label="R par trade")
    p2.grid_x([0.5, 1.5, 2.5], lambda v: cas[int(v)][1], label="dérive supposée")
    p2.hline(0.0, "zero")
    for i, (mu, _) in enumerate(cas):
        gain = mu / 60.0 * o.expected_time / q.STOP_PTS
        net = gain - ratio
        p2.vbar(i + 0.5 - 0.26, 0.0, gain, 15.0, "s1f",
                f"µ·E[τ]/a = {gain:+.3f} R")
        p2.vbar(i + 0.5, 0.0, -ratio, 15.0, "s2f", f"−c/a = {-ratio:+.3f} R")
        # Ni la classe de l'apport ni celle de la friction : la barre nette
        # est ce que la figure existe pour montrer, et la peindre comme
        # l'apport la faisait lire comme un second apport.
        p2.vbar(i + 0.5 + 0.26, 0.0, net, 15.0,
                "s3f" if net > 1e-9 else "dn", f"E[R] = {net:+.3f} R")
    p2.hline(ratio, "lvl")
    p2.label(0.06, ratio, "c/a", dx=0, dy=-5, cls="dl halo")

    # --- Cadre 3 : le facteur annoncé constant -----------------------------
    nul = q.null_law()
    r_nul = nul.sd / nul.downside_deviation()
    p3 = Panel(b, 84, 288, 508, 108, title="Le rapport Sortino/Sharpe",
               readout=f"de {_num(r_nul, 2)} à {_num(_law(28.0).sd / _law(28.0).downside_deviation(), 2)} sur le domaine")
    p3.domain(0.0, 28.0, 2.8, 5.2)
    p3.frame()
    p3.grid_y([3.0, 3.5, 4.0, 4.5, 5.0], lambda v: _num(v, 1), label="σ/DD")
    p3.grid_x([0, 7, 14, 21, 28], lambda v: _num(v, 0), label="dérive (pt/h)")
    p3.band_x(bas, haut, "wash")
    p3.path([(0.2 * k, (lambda L: L.sd / L.downside_deviation())(_law(0.2 * k)))
             for k in range(0, 141)], "s3")
    p3.hline(r_nul, "lvl")
    # La courbe monte de gauche à droite : au-dessus d'un point elle passe,
    # en dessous elle ne revient pas. Les trois étiquettes descendent donc.
    p3.label(27.6, r_nul, "sans dérive : " + _num(r_nul, 2), dx=0, dy=-7,
             anchor="end", cls="dl halo")
    for mu, lab in ((haut, "borne du plausible"), (mu_ref, "hypothèse")):
        L = _law(mu)
        v = L.sd / L.downside_deviation()
        p3.dot(mu, v, "s3", f"{lab} : σ/DD = {v:.2f}")
        # Le point de la borne basse a la ligne « sans dérive » juste sous
        # lui : son étiquette part vers la gauche, au-dessus d'une courbe qui
        # n'y est pas encore montée. Celle de l'hypothèse garde la droite.
        gauche = mu < 0.5 * mu_ref
        p3.label(mu, v, lab + " : " + _num(v, 2),
                 dx=-9 if gauche else 10, dy=-7 if gauche else 15,
                 anchor="end" if gauche else "start", cls="dl halo")

    # Quatre-vingt-dix points plus bas que l'axe du troisième cadre : posée à
    # 424, la légende tombait exactement sur l'intitulé « dérive (pt/h) ».
    b.legend(84, 448, [("s1", "délai nu (MinTRL)"),
                       ("s2", f"après {_num(q.N_TRIALS_REF, 0)} configurations"),
                       ("s3", "rapport σ/DD")], step=176, kind="line")
    b.caption(330, 474, "le domaine plausible et le domaine démontrable sont "
                        "disjoints, et entre les deux il y a le seuil,")
    b.caption(330, 490, "où l'apport de la dérive vaut la friction et où la "
                        "barre nette disparaît")
    return b.render(
        "Délai d établissement selon la dérive supposée, décomposition de "
        "l espérance publiée en apport de dérive et prélèvement de friction, "
        "et rapport Sortino sur Sharpe selon la dérive")


def fig_hypothese_surface() -> str:
    """Le délai d'établissement sur le plan (géométrie × dérive).

    La table de détectabilité de la troisième partie tient la dérive fixe et
    balaie la géométrie. C'est la bonne lecture — la dérive appartient au
    signal, la géométrie à l'opérateur — mais elle laisse invisible ce qui se
    passe quand l'hypothèse bouge. Cette surface déplie le second axe.

    La hauteur est le logarithme du délai, parce qu'il couvre trois ordres de
    grandeur. Le plafond est une durée de carrière, et la couleur d'alerte
    marque les configurations qui le dépassent : le plateau au premier plan
    n'est pas un artefact de bornage, c'est un mur, et c'est là que tombe la
    géométrie déclarée par l'opérateur.
    """
    z, brut = [], []
    for rr in q.RR_GRID:
        ligne = [min(_annees(mu, rr, essais=q.N_TRIALS_REF), PLAFOND_ANS)
                 for mu in DERIVES_3D]
        brut.append(ligne)
        z.append([math.log10(v) for v in ligne])
    plat = [v for ligne in z for v in ligne]
    zlo, zhi = min(plat) - 0.06, max(plat) + 0.06

    def verdict(v: float) -> str:
        """Rouge au plafond, rampe en dessous : la couleur porte le verdict.

        Le seuil n'est pas décoratif. Une maille rouge est une configuration
        dont le délai dépasse la moitié du plafond, c'est-à-dire qu'aucune
        carrière ne l'établit ; les autres suivent une rampe de chaleur, où
        le clair est le délai court.
        """
        if v >= math.log10(PLAFOND_ANS / 2.0):
            return "dn"
        return heat_class(0.30 + 0.62 * (1.0 - (v - zlo) / (zhi - zlo)))

    b = Board(660, 412)
    b.add('<text class="hdr" x="0" y="18">Le délai d\'établissement, sur deux axes</text>')
    b.add('<text class="sub" x="0" y="34">après ' + _num(q.N_TRIALS_REF, 0)
          + ' configurations essayées · hauteur : logarithme du délai, en années</text>')
    b.add('<line class="ba" x1="0" y1="46" x2="660" y2="46"/>')
    surface(
        b, 356.0, 196.0, z, zlo, zhi, cx=30.0, cy=11.0, cz=126.0,
        row_labels=["1:" + _num(rr, 0) for rr in q.RR_GRID],
        col_labels=[_num(m, 0) for m in DERIVES_3D[:-1]]
                   + [_num(DERIVES_3D[-1], 0) + " pt/h"],
        z_ticks=[(math.log10(v), _num(v, 1) + " an" if v < 1
                  else _num(v, 0) + (" an" if v == 1 else " ans"))
                 for v in (0.5, 1.0, 5.0, 40.0)
                 if zlo <= math.log10(v) <= zhi],
        tip="délai = {v:.2f} (log₁₀ des années)", classify=verdict, zero=zlo,
    )
    # Deux lignes plutôt qu'une : posée dans la bande basse, une annotation
    # de plus de cinquante-cinq signes déclenche le secours de longueur de
    # `extraire_pieds`, et le contrôle du document l'exige donc courte.
    b.annotation(0, 322, "le mur occupe le coin des géométries serrées")
    b.annotation(0, 336, "et des dérives faibles, où tombe la géométrie déclarée")
    b.legend(0, 362, [("dn", f"au-delà de {_num(PLAFOND_ANS / 2, 0)} ans — "
                             "hors d'une carrière"),
                      ("hm6", "délai court")], step=330, kind="swatch")
    # Le pied ne dit que ce que le cadre montre. La colonne la plus à gauche
    # vaut déjà trois fois le plafond du plausible : le domaine plausible
    # n'est pas dans cette figure, et l'affirmer ici serait le décrire sans
    # le tracer. La table du multiple le porte, elle.
    b.caption(330, 388, "l'arête gauche est le ratio gain/risque, l'arête "
                        "droite la dérive supposée, et la hauteur le délai,")
    b.caption(330, 402, "dont la colonne la plus faible vaut déjà trois fois "
                        "le plafond du domaine plausible")
    return b.render(
        "Surface du délai d établissement sur le plan du ratio gain sur risque "
        "et de la dérive supposée, avec le plafond de carrière en couleur d alerte")


ALL_FIGURES = {
    "hyphypothese": fig_hypothese,
    "hyphypothese3d": fig_hypothese_surface,
}


def render_all() -> dict[str, str]:
    return {name: fn() for name, fn in ALL_FIGURES.items()}
