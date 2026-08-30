"""Planches du protocole à horizon borné.

Deux planches, et elles répondent à deux questions différentes. La première
montre ce que le dispositif **obtient** : une courbe de puissance, une loi de
durée, le décompte des leviers qui a permis d'y arriver, et la vérification que
la corrélation du panel ne déplace que la durée. La seconde montre ce qui rend
ces chiffres croyables : les trajectoires de décision elles-mêmes, contre leurs
frontières, et le contraste entre une famille lue dans l'ordre scellé et la
même famille lue par son meilleur élément.

Même contrat graphique que le reste du dépôt : aucune couleur écrite en dur,
aucune dépendance, et chaque point vient du noyau qui produit les tables.
"""

from __future__ import annotations

from . import mcprotocol as mcp
from . import power as pw
from .figquant import ticks_within
from .figterm import Board, Panel, _num


def _bps(mult: float) -> float:
    return mcp.bps_of_net_drift(mult * mcp.design_drift())


# ---------------------------------------------------------------------------
# Planche 1 : ce que le dispositif obtient
# ---------------------------------------------------------------------------

def fig_bounded() -> str:
    """Puissance, durée, décompte des leviers, robustesse à la corrélation."""
    b = Board(660, 614)
    ref = round(mcp.reference_multiple(), 3)
    curve = list(mcp.CURVE) + [ref]
    points = [(mult, mcp.operating_point(mcp.exact_pool(mult), mult))
              for mult in curve]

    # --- P1 : la courbe de puissance --------------------------------------
    xs = [_bps(m) for m, _ in points]
    p1 = Panel(b, 56, 46, 262, 192, title="Puissance du protocole",
               readout=f"{_num(mcp.REPLICATES, 0)} exécutions par point")
    p1.domain(0.0, 6.6, 0.0, 1.0)
    p1.frame()
    p1.grid_y([0.0, 0.25, 0.5, 0.8, 1.0], lambda v: _num(v, 2))
    p1.grid_x([0, 2, 4, 6], lambda v: f"{v:g}",
              label="dérive captée, en points de base")
    p1.hline(pw.POWER, "lvl strong")
    p1.label(0.15, pw.POWER, "puissance visée", dx=0, dy=-6, cls="lg halo")
    p1.hline(pw.ALPHA, "lvl")
    for mult, lab, ly, anchor, dx in (
            (0.0, "seuil de rentabilité", 0.72, "start", 6),
            (1.0, "θ₁ dimensionnante", 0.13, "end", -5),
            (ref, "hypothèse empruntée", 0.40, "end", -5)):
        p1.vline(_bps(mult), "lvl")
        p1.label(_bps(mult), ly, lab, dx=dx, dy=0, anchor=anchor, cls="lg halo")
    # Les barres verticales sont l'erreur-type de Monte-Carlo, pas un
    # intervalle de confiance sur le marché : elles disent la précision du
    # calcul, pas celle du monde.
    for x, (_, op) in zip(xs, points):
        p1.vbar(x, max(0.0, op.reject - 2 * op.standard_error),
                min(1.0, op.reject + 2 * op.standard_error), 2.4, "area ar3")
    p1.path([(x, op.reject) for x, (_, op) in zip(xs, points)], "s1")
    for x, (mult, op) in zip(xs, points):
        p1.dot(x, op.reject, "s1f", f"{_num(x, 2)} pdb → {_num(op.reject, 3)}")

    # --- P2 : la loi de la durée du verdict --------------------------------
    p2 = Panel(b, 372, 46, 244, 192, title="Durée du verdict",
               readout="loi sur les exécutions")
    p2.domain(0.5, 5.3, 0.0, 1.05)
    p2.frame()
    p2.grid_y([0.0, 0.5, 1.0], lambda v: _num(v, 1))
    p2.grid_x([1, 2, 3, 4, 5], lambda v: f"{v:g}", label="années de données")
    for mult, cls in ((0.0, "s3"), (1.0, "s2"), (ref, "s1")):
        op = mcp.operating_point(mcp.exact_pool(mult), mult)
        ys = _duration_cdf(mult)
        p2.path(ys, cls)
    p2.vline(pw.HORIZON_SESSIONS / pw.SESSIONS_PER_YEAR, "lvl strong")
    p2.label(5.0, 0.44, "plafond", dx=-6, dy=0, anchor="end", cls="lg halo")
    p2.vline(pw.DESIGN_SESSIONS / pw.SESSIONS_PER_YEAR, "lvl")
    p2.label(pw.DESIGN_SESSIONS / pw.SESSIONS_PER_YEAR, 0.20, "budget",
             dx=-6, dy=0, anchor="end", cls="lg halo")
    b.legend(376, 278, [("s3", "sans dérive"), ("s2", "à θ₁"),
                        ("s1", "empruntée")], step=84, kind="line")

    # --- P3 : le décompte des leviers -------------------------------------
    st = mcp.pool_statistics(0.0)
    sr = (mcp.EDGE_BPS * 1e-4 * mcp.INDEX_LEVEL - mcp.friction()) / st["sd"]
    levers = pw.ledger(sr)
    p3 = Panel(b, 56, 330, 262, 204, title="Le décompte des leviers",
               readout="durée du verdict, en années")
    hi = max(l.years_after for l in levers) * 1.30
    p3.domain(0.0, hi, -0.55, len(levers) - 0.45)
    p3.frame()
    p3.grid_x(ticks_within(0, hi, [0, 1, 2, 3, 4, 5]), lambda v: f"{v:g}",
              label="années")
    for i, lev in enumerate(levers):
        y = len(levers) - 1 - i
        previous = levers[i - 1].years_after if i else lev.years_after
        # Barre claire : la durée qui reste. Barre sombre : le morceau que ce
        # levier vient de retirer. Les deux se lisent d'un coup.
        p3.hbar(y, 0.0, lev.years_after, 9.0, "area ar3",
                f"{lev.name} : {_num(lev.years_after, 2)} ans")
        if i:
            p3.hbar(y, lev.years_after, previous, 9.0, "ba",
                    f"retiré : {_num(previous - lev.years_after, 2)} ans")
        p3.label(max(lev.years_after, previous), y,
                 _num(lev.years_after, 2), dx=6, dy=4, cls="tk")
        p3.label(0.0, y + 0.36, _short(lev.name), dx=2, dy=0, cls="lg halo")

    # --- P4 : la corrélation ne déplace que la durée -----------------------
    rho = mcp.rho_sensitivity()
    p4 = Panel(b, 372, 330, 244, 204, title="Robustesse à la corrélation",
               readout="taille à gauche, durée à droite")
    p4.domain(0.45, 1.0, 0.0, 0.10)
    p4.frame()
    p4.grid_y([0.0, 0.05, 0.10], lambda v: _num(v, 2))
    p4.grid_x([0.5, 0.65, 0.8, 0.95], lambda v: _num(v, 2),
              label="corrélation intra-fuseau")
    p4.hline(pw.ALPHA, "lvl strong")
    p4.label(0.45, pw.ALPHA, "niveau nominal", dx=4, dy=-9, cls="lg halo")
    for r in rho:
        p4.vbar(r["rho_within"], max(0.0, r["size"] - 2 * r["standard_error"]),
                r["size"] + 2 * r["standard_error"], 3.0, "area ar3")
        p4.dot(r["rho_within"], r["size"], "s1f",
               f"ρ = {_num(r['rho_within'], 2)} → taille {_num(r['size'], 3)}")
    p4.path([(r["rho_within"], r["size"]) for r in rho], "s1")
    lo, hi_y = 2.0, 4.0
    p5 = Panel(b, 372, 330, 244, 204)
    p5.domain(0.45, 1.0, lo, hi_y)
    p5.grid_y([2.0, 2.5, 3.0, 3.5, 4.0], lambda v: _num(v, 1), side="right")
    p5.path([(r["rho_within"], r["median_years"]) for r in rho], "s2", dash="5 3")
    for r in rho:
        p5.dot(r["rho_within"], r["median_years"], "s2f",
               f"durée médiane {_num(r['median_years'], 2)} ans")

    b.caption(338, 582,
              "La taille reste au niveau nominal sur toute la plage de "
              "corrélation ; seule la durée du verdict s'allonge.")
    b.caption(338, 600,
              "C'est la propriété que le jalonnement en information achète, "
              "et la raison pour laquelle ρ n'a pas à être connu.")
    return b.render("Puissance, durée, leviers et robustesse du protocole borné")


def _short(name: str) -> str:
    return name if len(name) <= 46 else name[:44] + "…"


def _duration_cdf(multiple: float) -> list[tuple[float, float]]:
    """Fonction de répartition empirique de la durée du verdict."""
    op = mcp.operating_point(mcp.exact_pool(multiple), multiple)
    years = sorted(_durations(multiple))
    n = len(years)
    pts = [(0.5, 0.0)]
    for i, y in enumerate(years):
        pts.append((y, (i + 1) / n))
    pts.append((5.3, pts[-1][1]))
    # Une répartition à mille cinq cents marches ne se lit pas : on la
    # sous-échantillonne à un point sur vingt, marches comprises.
    return [pts[i] for i in range(0, len(pts), max(1, n // 60))] + [pts[-1]]


def _durations(multiple: float) -> list[float]:
    from .mc import Rng

    plan = pw.boundaries()
    i_max = mcp.max_information(plan)
    pool = mcp.exact_pool(multiple)
    rng = Rng(mcp.SEED + 971)
    return [mcp.run_protocol(pool, rng, plan, i_max).years for _ in range(800)]


# ---------------------------------------------------------------------------
# Planche 2 : ce qui rend ces chiffres croyables
# ---------------------------------------------------------------------------

def fig_mcnull() -> str:
    """Trajectoires de décision, loi nulle du verdict, coût de la sélection."""
    b = Board(660, 348)
    plan = pw.boundaries()
    ref = round(mcp.reference_multiple(), 3)

    # --- P1 : les trajectoires contre leurs frontières ---------------------
    p1 = Panel(b, 56, 46, 292, 214, title="Trajectoires de décision",
               readout="Z contre les frontières d'O'Brien-Fleming")
    p1.domain(0.20, 1.02, -3.0, 5.0)
    p1.frame()
    p1.grid_y([-2, 0, 2, 4], lambda v: f"{v:g}")
    p1.grid_x([0.25, 0.5, 0.75, 1.0], lambda v: _num(v, 2),
              label="fraction d'information")
    fr = list(plan.fractions)
    # Les frontières d'abord, les trajectoires par-dessus : c'est la
    # rencontre des deux qui est le sujet de la figure.
    p1.path([(t, min(z, 5.0)) for t, z in zip(fr, plan.efficacy)], "s1", dash="5 3")
    p1.path([(t, z) for t, z in zip(fr, plan.futility)], "s1", dash="5 3")
    for t, z in zip(fr, plan.efficacy):
        p1.dot(t, min(z, 5.0), "s1f", f"rejet à t = {_num(t, 2)} : z ≥ {_num(z, 3)}",
               r=3.0)
    for t, z in list(zip(fr, plan.futility))[:-1]:
        p1.dot(t, z, "s1f", f"abandon à t = {_num(t, 2)} : z ≤ {_num(z, 3)}", r=3.0)
    # Une trajectoire qui s'arrête à la première analyse ne porte qu'un point,
    # et une polyligne d'un point ne trace rien : ces essais-là — ceux que le
    # protocole abandonne le plus tôt, donc les plus intéressants — étaient
    # absents de la figure. On les marque d'un point.
    for cls, derive in (("s3", 0.0), ("s2", ref)):
        for chemin in mcp.trace_paths(derive):
            pts = [(t, max(-3.0, min(5.0, z))) for t, z in chemin]
            if len(pts) < 2:
                p1.dot(pts[0][0], pts[0][1], cls + "f", r=2.2)
            else:
                p1.path(pts, cls)
    b.legend(56, 300, [("s1", "frontières"), ("s3", "sans dérive"),
                       ("s2", "hypothèse empruntée")], step=104, kind="line")

    # --- P2 : le coût de la sélection --------------------------------------
    sel = mcp.selection_contrast()
    p2 = Panel(b, 402, 46, 214, 214, title="Le coût de la sélection",
               readout="taux d'erreur sous H₀")
    p2.domain(-0.62, 2.62, 0.0, 0.14)
    p2.frame()
    p2.grid_y([0.0, 0.05, 0.10], lambda v: _num(v, 2))
    p2.hline(pw.ALPHA, "lvl strong")
    bars = ((0, sel["sealed"], "ba", "ordre scellé"),
            (1, sel["best_of_three"], "area ar1", "meilleur de 3"),
            (2, pw.ALPHA, "area ar3", "nominal"))
    for x, v, cls, lab in bars:
        p2.vbar(x, 0.0, v, 40.0, cls, f"{lab} : {_num(v, 3)}")
        p2.label(x, v, _num(v, 3), dx=0, dy=-7, anchor="middle", cls="tk halo")
        p2.label(x, 0.0, lab, dx=0, dy=15, anchor="middle", cls="lg")
    b.caption(509, 300, "Mêmes données, même procédure\u00a0:")
    b.caption(509, 318, "seul l'ordre de lecture change.")
    return b.render("Trajectoires séquentielles et coût de la sélection")


def render_all() -> dict[str, str]:
    return {
        "qbounded": fig_bounded(),
        "qmcnull": fig_mcnull(),
    }


def main() -> None:
    for key, svg in render_all().items():
        print(f"{key}: {len(svg):,} octets")


if __name__ == "__main__":
    main()
