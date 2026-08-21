"""Planches des instruments de validation — surfaces 3D et panneaux 2D.

Même contrat que `alp1.figures` et `alp1.figterm` : chaque figure est une
chaîne SVG produite par les fonctions du noyau, sans dépendance, sans binaire
et sans couleur écrite en dur. Les classes de mise en page — `Board`, `Panel`
— sont celles de `alp1.figterm`, réutilisées telles quelles pour que les deux
moitiés du document aient la même grammaire graphique.

Ce module ajoute une primitive que les précédents n'avaient qu'en un
exemplaire : la **surface isométrique**. Un instrument de validation dépend
presque toujours de deux réglages à la fois — le nombre d'essais et la
longueur de l'historique, la largeur du stop et l'intensité des sauts, la
fraction misée et l'edge supposé — et c'est la *forme* de la surface, non un
point de celle-ci, qui porte le résultat. Chaque planche du module montre
donc au moins une surface.
"""

from __future__ import annotations

import math

from .figterm import Board, Panel, _esc, _num, _signed


# --- Primitive : surface isométrique ---------------------------------------

def surface(
    board: Board,
    ox: float,
    oy: float,
    z: list[list[float]],
    zlo: float,
    zhi: float,
    *,
    cx: float = 23.0,
    cy: float = 12.5,
    cz: float = 150.0,
    row_labels: list[str] | None = None,
    col_labels: list[str] | None = None,
    row_axis: str = "",
    col_axis: str = "",
    zero: float = 0.0,
    z_ticks: list[tuple[float, str]] | None = None,
    tip: str = "{v:+.3f}",
    classify=None,
) -> None:
    """Trace une surface en projection isométrique dans la planche.

    `z[i][j]` est la hauteur à la ligne `i` et la colonne `j`. Les mailles
    sont peintes de l'arrière vers l'avant — tri par profondeur `i + j` — ce
    qui donne l'occultation correcte sans moteur de rendu. `classify(v)`
    choisit la classe CSS d'une maille ; par défaut le signe décide, ce qui
    fait lire au premier coup d'œil la frontière `z = 0`.

    Les montants verticaux aux quatre coins ne sont pas décoratifs : sans
    référence au sol, une projection isométrique est ambiguë en hauteur.
    """
    ni, nj = len(z), len(z[0])
    if classify is None:
        def classify(v: float) -> str:
            return "up" if v > 1e-12 else ("dn" if v < -1e-12 else "ze")

    def proj(i: float, j: float, val: float) -> tuple[float, float]:
        val = min(max(val, zlo), zhi)
        return (ox + (i - j) * cx,
                oy + (i + j) * cy - (val - zlo) * cz / (zhi - zlo))

    def poly(points, cls, title=""):
        t = f"<title>{_esc(title)}</title>" if title else ""
        return (f'<polygon class="{cls}" points="'
                + " ".join(f"{x:.1f},{y:.1f}" for x, y in points) + f'">{t}</polygon>')

    floor_z = min(max(zero, zlo), zhi)
    board.add(poly([proj(0, 0, floor_z), proj(ni - 1, 0, floor_z),
                    proj(ni - 1, nj - 1, floor_z), proj(0, nj - 1, floor_z)], "floor"))

    for (i, j) in ((0, 0), (ni - 1, 0), (ni - 1, nj - 1), (0, nj - 1)):
        fx, fy = proj(i, j, floor_z)
        sxp, syp = proj(i, j, z[i][j])
        board.add(f'<line class="post" x1="{fx:.1f}" y1="{fy:.1f}" '
                  f'x2="{sxp:.1f}" y2="{syp:.1f}"/>')

    quads = []
    for i in range(ni - 1):
        for j in range(nj - 1):
            corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            pts = [proj(a, b, z[a][b]) for a, b in corners]
            mean = sum(z[a][b] for a, b in corners) / 4.0
            quads.append((i + j, pts, mean))
    for _, pts, val in sorted(quads, key=lambda q: -q[0]):
        board.add(poly(pts, f"mesh {classify(val)}", tip.format(v=val)))

    if row_labels:
        for k, lab in enumerate(row_labels):
            if not lab:
                continue
            x, y = proj(k, nj - 1, floor_z)
            board.add(f'<text class="tk halo" x="{x - 7:.1f}" y="{y + 12:.1f}" '
                      f'text-anchor="end">{_esc(lab)}</text>')
    if col_labels:
        for k, lab in enumerate(col_labels):
            if not lab:
                continue
            x, y = proj(ni - 1, k, floor_z)
            board.add(f'<text class="tk halo" x="{x + 7:.1f}" y="{y + 11:.1f}">'
                      f'{_esc(lab)}</text>')

    if z_ticks:
        edge = ox - (nj - 1) * cx
        for val, lab in z_ticks:
            _, yy = proj(0, nj - 1, val)
            board.add(f'<text class="tk" x="{edge - 40:.1f}" y="{yy + 3:.1f}" '
                      f'text-anchor="end">{_esc(lab)}</text>')
            board.add(f'<line class="gl" x1="{edge - 35:.1f}" y1="{yy:.1f}" '
                      f'x2="{edge - 24:.1f}" y2="{yy:.1f}"/>')

    if row_axis or col_axis:
        legend = " · ".join(p for p in (f"axe gauche : {row_axis}" if row_axis else "",
                                        f"axe droit : {col_axis}" if col_axis else "") if p)
        board.add(f'<text class="lg" x="{ox:.1f}" y="{oy + (ni + nj) * cy / 2 + 30:.1f}" '
                  f'text-anchor="middle">{_esc(legend)}</text>')


def ticks_within(lo: float, hi: float, candidates) -> list[float]:
    """Graduations retenues dans le domaine — évite les étiquettes hors cadre."""
    a, b = min(lo, hi), max(lo, hi)
    return [v for v in candidates if a <= v <= b]


def heat_class(u: float) -> str:
    """Classe de rampe séquentielle pour une valeur normalisée dans [0, 1]."""
    return f"hm{min(7, max(0, int(round(u * 7))))}"


def histogram(panel: Panel, values: list[float], n_bins: int, cls: str,
              lo: float | None = None, hi: float | None = None,
              width_frac: float = 0.86) -> list[tuple[float, float]]:
    """Histogramme normalisé en densité, tracé dans un panneau déjà cadré.

    Retourne les couples (centre, densité) pour que l'appelant puisse y
    superposer une forme fermée — c'est la comparaison qui fait l'intérêt
    de la figure, jamais l'histogramme seul.
    """
    if not values:
        return []
    lo = min(values) if lo is None else lo
    hi = max(values) if hi is None else hi
    if hi <= lo:
        return []
    w = (hi - lo) / n_bins
    counts = [0] * n_bins
    for v in values:
        if lo <= v <= hi:
            k = min(n_bins - 1, int((v - lo) / w))
            counts[k] += 1
    n = len(values)
    out = []
    for k, c in enumerate(counts):
        centre = lo + (k + 0.5) * w
        dens = c / (n * w)
        out.append((centre, dens))
        if dens > 0:
            top = min(dens, max(panel.y0, panel.y1))
            panel.vbar(centre, 0.0, top,
                       max(1.2, panel.w / n_bins * width_frac), cls)
    return out


# ---------------------------------------------------------------------------
# Ratios : Sharpe, Sortino, Omega, et le facteur que la géométrie fabrique
# ---------------------------------------------------------------------------

def fig_ratios() -> str:
    """Trois lectures d'un même edge, et l'écart entre elles.

    À gauche, la surface du rapport Sortino/Sharpe sur la grille des ratios
    gain/risque et des multiples de dérive : elle ne dépend presque pas de la
    dérive et monte régulièrement avec le ratio visé. Ce n'est donc pas une
    propriété du signal, c'est une propriété de la **géométrie**. Au centre,
    les trois ratios côte à côte sur la calibration de référence. À droite, la
    décomposition qui l'explique : la dispersion totale et la dispersion à la
    baisse, et le fait que la seconde ne bouge pas.
    """
    from . import quant as q

    rr_grid = [5.0, 10.0, 20.0, 30.0]
    mults = [1.5, 2.0, 3.0, 5.0]
    o20 = q.geometry(q.RR_REF)
    mu_star = q.FRICTION / o20.expected_time

    # On trace σ/DD, qui **est** le rapport Sortino/Sharpe partout où les deux
    # sont définis, et qui reste défini quand l'espérance est négative — ce
    # qui est le cas des géométries serrées à faible dérive.
    z: list[list[float]] = []
    for rr in rr_grid:
        row = []
        o = q.geometry(rr)
        base = q.null_law(rr)
        for k in mults:
            target = (k * mu_star * o.expected_time - q.FRICTION) / q.STOP_PTS
            law = base.tilted_to_mean(target)
            row.append(law.sd / law.downside_deviation())
        z.append(row)

    _zlo = min(min(r) for r in z)
    _zhi = max(max(r) for r in z)
    b = Board(660, 348)
    surface(
        b, 166.0, 210.0, z, 0.0, 7.0, cx=23.0, cy=12.5, cz=162.0,
        row_labels=[f"1:{r:g}" for r in rr_grid],
        col_labels=["1,5 µ*", "", "", "5 µ*"],
        z_ticks=[(0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6")],
        tip="Sortino / Sharpe = {v:.2f}",
        classify=lambda v: heat_class((v - _zlo) / (_zhi - _zlo)),
    )
    # L'intitulé de panneau est mis en capitales par la feuille de style : le
    # sigma minuscule appartient donc à la ligne de sous-titre, pas au titre.
    b.add('<text class="hdr" x="56" y="30">Rapport Sortino / Sharpe</text>')
    b.add('<text class="sub" x="56" y="44">il vaut exactement σ/DD : un facteur que '
          'la géométrie fabrique,</text>')
    b.add('<text class="sub" x="56" y="57">et que la dérive ne change presque pas</text>')

    # --- P2 : les trois ratios sur la calibration de référence -------------
    e0, n0 = q.edge_law(), q.null_law()
    entries = [
        ("Sharpe", n0.sharpe_per_trade, e0.sharpe_per_trade),
        ("Sortino", n0.sortino(), e0.sortino()),
        ("Omega − 1", n0.omega() - 1.0, e0.omega() - 1.0),
    ]
    p2 = Panel(b, 384, 74, 124, 168, title="Par trade", readout="R:R 1:20")
    p2.domain(-0.5, len(entries) - 0.5, -0.16, 0.16)
    p2.frame()
    p2.grid_y([-0.15, -0.10, -0.05, 0.0, 0.05, 0.10, 0.15], lambda v: _num(v, 2))
    p2.hline(0.0, "zero")
    for i, (lab, vn, ve) in enumerate(entries):
        p2.vbar(i - 0.17, 0.0, vn, 15.0, "dn", f"{lab} · µ = 0 · {vn:+.3f}")
        p2.vbar(i + 0.17, 0.0, ve, 15.0, "s1f", f"{lab} · µ = 2µ* · {ve:+.3f}")
        p2.board.add(f'<text class="tk" transform="translate({p2.sx(i):.1f},'
                     f'{p2.y + p2.h + 30:.1f}) rotate(-38)" text-anchor="middle">'
                     f'{_esc(lab)}</text>')

    # --- P3 : dispersion totale contre dispersion à la baisse --------------
    p3 = Panel(b, 546, 74, 90, 168, title="Dispersion",
               readout=f"σ/DD = {_num(e0.sd / e0.downside_deviation(), 2)}")
    p3.domain(-0.5, 1.5, 0.0, 6.0)
    p3.frame()
    p3.grid_y([0, 1, 2, 3, 4, 5, 6], lambda v: f"{v:g}")
    p3.vbar(0.0, 0.0, e0.sd, 34.0, "s2f", f"écart-type total {e0.sd:.2f} R")
    p3.vbar(1.0, 0.0, e0.downside_deviation(), 34.0, "s3f",
            f"déviation à la baisse {e0.downside_deviation():.2f} R")
    for i, lab in ((0, "σ total"), (1, "baisse")):
        p3.board.add(f'<text class="tk" transform="translate({p3.sx(i):.1f},'
                     f'{p3.y + p3.h + 30:.1f}) rotate(-38)" text-anchor="middle">'
                     f'{_esc(lab)}</text>')
    p3.label(1.0, e0.downside_deviation(), "borné par le stop", dx=2, dy=-10,
             anchor="middle", cls="lg halo")

    b.legend(384, 302, [("dn", "µ = 0"), ("s1f", "µ = 2 µ*")], step=88)
    b.caption(330, 332, "la dispersion à la baisse est bornée par le stop : "
                        "tout l'écart entre les deux ratios vient de la queue de gain")
    return b.render("Sharpe, Sortino et Omega, et le facteur que la géométrie "
                    "impose au rapport des deux premiers")


# ---------------------------------------------------------------------------
# Drawdown : √N sans dérive, ln N avec, et la loi de l'arcsinus
# ---------------------------------------------------------------------------

def fig_drawdown() -> str:
    """Ce que le drawdown dit, et ce qu'il ne dit pas.

    Le panneau de gauche oppose les deux lois de croissance : `√N` sans
    dérive, `ln N` avec. C'est l'écart entre les deux courbes — et non le
    niveau de l'une d'elles — qui contient l'information. Au centre, la loi
    simulée du drawdown annuel confrontée à sa forme fermée. À droite, la loi
    de l'arcsinus, qui explique pourquoi la durée passée sous les eaux ne
    prouve jamais rien.
    """
    from . import quant as q
    from .drawdown import (
        expected_max_drawdown_drift,
        expected_max_drawdown_null,
        reflected_max_cdf,
    )
    from .mc import quantile

    n0, e0 = q.null_law(), q.edge_law()
    b = Board(660, 306)

    # --- P1 : deux lois de croissance -------------------------------------
    ns = [int(round(10 ** (1.0 + 0.05 * k))) for k in range(0, 61)]
    ns = sorted({n for n in ns if n >= 10})
    p1 = Panel(b, 56, 46, 172, 168, title="Croissance du drawdown",
               readout="en R, échelle log")
    p1.domain(10, 20000, 1.0, 400.0, xlog=True, ylog=True)
    p1.frame()
    p1.grid_y([1, 3, 10, 30, 100, 300], lambda v: f"{v:g}")
    p1.grid_x([10, 100, 1000, 10000], lambda v: f"{v:g}", label="trades")
    # Les deux courbes portent sur la **même** loi : seule la dérive est
    # retirée pour la première. L'écart ne peut donc venir que d'elle.
    p1.path([(n, expected_max_drawdown_null(e0.sd, n)) for n in ns], "s2")
    p1.path([(n, expected_max_drawdown_drift(e0, n)) for n in ns], "s1")
    p1.path([(n, n * e0.mean) for n in ns if n * e0.mean >= 1.0], "s3", dash="4 3")
    p1.vline(q.TRADES_PER_YEAR, "lvl")
    p1.label(q.TRADES_PER_YEAR, 260.0, "1 an", dx=5, dy=0, cls="lg halo")

    # --- P2 : loi simulée du drawdown annuel ------------------------------
    dd = [p.max_drawdown for p in q.mc_paths("edge")]
    dd_null = [p.max_drawdown for p in q.mc_paths("null")]
    hi = quantile(dd_null, 0.995)
    p2 = Panel(b, 280, 46, 164, 168, title="Drawdown annuel",
               readout=f"{_num(q.MC_PATHS, 0)} années simulées")
    # orange : loi sans dérive ; bleu : sous dérive — mêmes couleurs qu'en P1.
    p2.domain(0.0, hi, 0.0, 0.016)
    p2.frame()
    p2.grid_y([0.005, 0.010, 0.015], lambda v: _num(v * 100, 1))
    p2.grid_x([v for v in (0, 100, 200, 300, 400) if v <= hi],
              lambda v: f"{v:g}", label="R")
    histogram(p2, dd_null, 34, "area ar3", 0.0, hi, width_frac=0.94)
    histogram(p2, dd, 34, "area ar1", 0.0, hi, width_frac=0.62)
    marks = ((expected_max_drawdown_null(e0.sd, q.MC_TRADES), "lvl", "√N", 0.0148),
             (expected_max_drawdown_drift(e0, q.MC_TRADES), "lvl strong", "ln N", 0.0128))
    for val, cls, lab, ly in marks:
        if val < hi:
            p2.vline(val, cls)
            p2.label(val, ly, lab, dx=4, dy=0, cls="lg halo")

    # --- P3 : loi de l'arcsinus -------------------------------------------
    p3 = Panel(b, 504, 46, 132, 168, title="Temps sous les eaux",
               readout="loi de l'arcsinus")
    p3.domain(0.0, 1.0, 0.0, 1.0)
    p3.frame()
    p3.grid_y([0, 0.25, 0.5, 0.75, 1.0], lambda v: _num(v, 2))
    p3.grid_x([0, 0.5, 1.0], lambda v: _num(v, 1), label="fraction du temps")
    xs = [k / 200.0 for k in range(1, 200)]
    p3.path([(x, (2.0 / math.pi) * math.asin(math.sqrt(x))) for x in xs], "s1")
    p3.path([(x, x) for x in xs], "s2", dash="4 3")
    p3.band_x(0.8, 1.0, "wash")
    p3.label(0.80, 0.62, "30 % des années", dx=-6, dy=0, anchor="end", cls="dl halo")

    b.legend(56, 268, [("s2", "même loi, dérive retirée : √N"),
                       ("s1", "avec dérive : ln N"),
                       ("s3", "gain cumulé espéré")], step=142, kind="line")
    b.legend(496, 268, [("s1", "arcsinus"), ("s2", "uniforme")], step=76, kind="line")
    b.caption(330, 296, "les deux lois de croissance se séparent d'autant plus que "
                        "l'historique s'allonge : c'est l'écart, non le niveau, qui informe")
    return b.render("Drawdown : loi de croissance sans dérive et sous dérive, loi "
                    "simulée du drawdown annuel, loi de l'arcsinus du temps sous les eaux")


# ---------------------------------------------------------------------------
# Monte-Carlo : le faisceau des courbes qu'un même processus peut produire
# ---------------------------------------------------------------------------

def fig_montecarlo() -> str:
    """Un backtest est un tirage, et cette figure montre les autres.

    Les deux faisceaux sont construits sur la même géométrie et la même
    friction ; seule la dérive change. Leur recouvrement est le résultat : la
    courbe médiane d'une stratégie sans edge et le décile bas d'une stratégie
    avec edge occupent la même région du plan pendant toute l'année.
    """
    from . import quant as q
    from .mc import Rng, fan, fan_index, quantile

    levels = (0.05, 0.25, 0.50, 0.75, 0.95)
    step = 12
    idx = fan_index(q.MC_TRADES, step)
    fans = {
        "null": fan(q.null_law(), q.MC_TRADES, 900, levels, Rng(q.SEED + 31), step),
        "edge": fan(q.edge_law(), q.MC_TRADES, 900, levels, Rng(q.SEED + 32), step),
    }
    lo = min(min(f[0.05]) for f in fans.values())
    hi = max(max(f[0.95]) for f in fans.values())

    b = Board(660, 308)
    titles = {"null": ("Sans dérive", "µ = 0"), "edge": ("Sous dérive", "µ = 2 µ*")}
    for k, key in enumerate(("null", "edge")):
        f = fans[key]
        title, readout = titles[key]
        p = Panel(b, 56 + k * 232, 46, 196, 186, title=title, readout=readout)
        p.domain(0, q.MC_TRADES, lo, hi)
        p.frame()
        p.grid_y(ticks_within(lo, hi, (-300, -200, -100, 0, 100, 200, 300)),
                 lambda v: f"{v:g}", label="R cumulés" if k == 0 else None)
        p.grid_x([0, 126, 252, 378, 504], lambda v: f"{v:g}", label="trades")
        p.hline(0.0, "zero")
        top = list(zip(idx, f[0.95]))
        bottom = list(zip(reversed(idx), reversed(f[0.05])))
        d = " ".join(("M" if i == 0 else "L") + f"{p.sx(x):.1f},{p.sy(y):.1f}"
                     for i, (x, y) in enumerate(top + bottom)) + " Z"
        p.board.add(f'<path class="wash" d="{d}"/>')
        series = "s1" if key == "edge" else "s2"
        for lv in (0.25, 0.75):
            p.path(list(zip(idx, f[lv])), series, dash="3 3")
        p.path(list(zip(idx, f[0.50])), series)
        p.label(q.MC_TRADES, f[0.50][-1], _num(f[0.50][-1], 0) + " R",
                dx=-6, dy=-6, anchor="end", cls="dl halo")

    # --- P3 : lois terminales superposées ---------------------------------
    tn = [x.terminal for x in q.mc_paths("null")]
    te = [x.terminal for x in q.mc_paths("edge")]
    p3 = Panel(b, 528, 46, 108, 186, title="P&L annuel", readout="densité ‰")
    p3.domain(lo, hi, 0.0, 0.0075)
    p3.frame()
    p3.grid_y([0.002, 0.004, 0.006], lambda v: _num(v * 1000, 0))
    p3.grid_x(ticks_within(lo, hi, (-200, 0, 200)), lambda v: f"{v:g}", label="R")
    histogram(p3, tn, 30, "area ar3", lo, hi, width_frac=0.96)
    histogram(p3, te, 30, "area ar1", lo, hi, width_frac=0.62)
    p3.vline(0.0, "zero")

    b.legend(56, 272, [("s2", "médiane sans dérive"), ("s1", "médiane sous dérive")],
             step=182, kind="line")
    b.legend(430, 272, [("swatch-wash", "intervalle 90 %")], step=1)
    b.caption(330, 296, "traits pleins : médianes ; tirets : quartiles ; "
                        "chaque faisceau enveloppe 900 années simulées — un backtest en est une")
    return b.render("Faisceaux de courbes d équité simulées sans dérive puis sous "
                    "dérive, et lois du P&L annuel")


# ---------------------------------------------------------------------------
# Ré-échantillonnage : bootstrap i.i.d., bootstrap par blocs, permutation
# ---------------------------------------------------------------------------

def fig_resampling() -> str:
    """Trois façons de fabriquer une loi nulle, et ce qui les sépare.

    Le bootstrap i.i.d. et le bootstrap stationnaire produisent, sur une série
    **indépendante**, la même dispersion : c'est le contrôle de l'instrument.
    Sur une série autocorrélée, ils divergent, et le premier sous-estime
    l'incertitude — la surface de droite chiffre l'écart en fonction de la
    longueur de bloc et de l'autocorrélation. Au centre, le test de
    permutation de signe, qui ne suppose ni loi ni indépendance des
    amplitudes.
    """
    from . import quant as q
    from .mc import (
        Rng, iid_bootstrap, quantile, sample, sign_permutation_pvalue,
        stationary_bootstrap,
    )
    from .pathstats import lo_adjustment

    rng = Rng(q.SEED + 41)
    data = sample(q.edge_law(), 504, rng)
    n_rep = 900
    iid_means = [sum(iid_bootstrap(data, rng)) / len(data) for _ in range(n_rep)]
    blk_means = [sum(stationary_bootstrap(data, rng, 20.0)) / len(data)
                 for _ in range(n_rep)]

    lo = min(min(iid_means), min(blk_means))
    hi = max(max(iid_means), max(blk_means))
    b = Board(660, 312)

    p1 = Panel(b, 56, 46, 176, 176, title="Bootstrap de la moyenne",
               readout="504 trades, 900 tirages")
    p1.domain(lo, hi, 0.0, 2.6)
    p1.frame()
    p1.grid_y([0.5, 1.0, 1.5, 2.0, 2.5], lambda v: _num(v, 1))
    p1.grid_x([-0.2, 0.0, 0.2, 0.4], lambda v: _num(v, 1), label="E[R] rééchantillonnée")
    histogram(p1, iid_means, 32, "area ar3", lo, hi, width_frac=0.96)
    histogram(p1, blk_means, 32, "area ar1", lo, hi, width_frac=0.60)
    p1.vline(0.0, "zero")
    p1.vline(sum(data) / len(data), "lvl strong")
    p1.label(sum(data) / len(data), 2.35, "observée", dx=5, dy=0, cls="lg halo")

    # --- P2 : permutation de signe ----------------------------------------
    observed = sum(data) / len(data)
    perm = []
    for _ in range(n_rep):
        total = 0.0
        for r in data:
            total += r if rng.next_u64() & 1 else -r
        perm.append(total / len(data))
    plo, phi = min(min(perm), observed), max(max(perm), observed)
    pval = sign_permutation_pvalue(data, Rng(q.SEED + 42), 2000)
    p2 = Panel(b, 280, 46, 176, 176, title="Permutation de signe",
               readout=f"p = {_num(pval, 3)}")
    p2.domain(plo, phi, 0.0, 3.0)
    p2.frame()
    p2.grid_y([1.0, 2.0, 3.0], lambda v: _num(v, 0))
    p2.grid_x([-0.4, -0.2, 0.0, 0.2, 0.4], lambda v: _num(v, 1),
              label="E[R] sous signes aléatoires")
    histogram(p2, perm, 32, "area ar2", plo, phi, width_frac=0.96)
    p2.vline(observed, "lvl strong")
    p2.label(observed, 2.7, "observée", dx=5, dy=0, cls="lg halo")

    # --- P3 : surface du biais d'annualisation ----------------------------
    rhos = [0.0, 0.1, 0.2, 0.4]
    qs = [21, 63, 126, 252]
    z = [[lo_adjustment(rho, qq) / math.sqrt(qq) for qq in qs] for rho in rhos]
    surface(
        b, 566.0, 212.0, z, 0.5, 1.05, cx=15.0, cy=8.0, cz=112.0,
        row_labels=["ρ = 0", "", "", "ρ = 0,4"],
        col_labels=["q 21", "", "", "252"],
        z_ticks=[(0.6, "0,6"), (0.8, "0,8"), (1.0, "1,0")],
        tip="facteur réel / √q = {v:.3f}",
        classify=lambda v: heat_class((1.0 - v) / 0.5),
    )
    b.add('<text class="hdr" x="490" y="30">Annualisation</text>')
    b.add('<text class="sub" x="490" y="44">facteur réel rapporté à √q ;</text>')
    b.add('<text class="sub" x="490" y="57">sous 1, le Sharpe publié est gonflé</text>')

    b.legend(56, 276, [("s2f", "bootstrap i.i.d."),
                       ("s1f", "blocs stationnaires"),
                       ("s3f", "signes permutés")], step=150)
    b.caption(240, 300, "sur une série indépendante les deux bootstraps coïncident : "
                        "c'est le contrôle de l'instrument, pas le résultat")
    return b.render("Bootstrap i.i.d. et par blocs, test de permutation de signe, "
                    "et biais d annualisation du Sharpe sous autocorrélation")


# ---------------------------------------------------------------------------
# HMM : ce que Baum-Welch trouve quand il n'y a rien à trouver
# ---------------------------------------------------------------------------

def fig_hmm() -> str:
    """Un régime réel, un régime inventé, et la grandeur qui les sépare.

    En haut, la série à deux régimes et le chemin de Viterbi qui la décode
    correctement. Au milieu, la même procédure sur cent vingt points de bruit
    indépendant : deux régimes apparaissent, nets, persistants, et faux. En
    bas à droite, la seule quantité qui tranche — la séparabilité — et le
    nombre d'observations qu'elle exige, qui croît en `1/d′²`.
    """
    from . import quant as q
    from .hmm import bayes_error, observations_to_separate, separability, viterbi

    b = Board(660, 396)

    def regime_panel(py: float, kind: str, title: str, n_show: int) -> None:
        fitted, _, _, _, _ = q.hmm_fit(kind)
        obs, _ = q.hmm_series(kind)
        path = viterbi(fitted, list(obs))
        d = separability(fitted.means[0], fitted.means[1],
                         0.5 * (fitted.sds[0] + fitted.sds[1]))
        show = min(n_show, len(obs))
        p = Panel(b, 56, py, 396, 118, title=title,
                  readout=f"d′ = {_num(d, 2)} · ΔBIC = {_signed(_bic_delta(kind), 1)}")
        p.domain(0, show, -4.2, 4.2)
        p.frame()
        p.grid_y([-3, 0, 3], lambda v: f"{v:g}")
        p.grid_x([0, show // 2, show], lambda v: f"{v:g}")
        hot = 0 if fitted.means[0] >= fitted.means[1] else 1
        run_start, run_state = 0, path[0]
        for i in range(1, show + 1):
            state = path[i] if i < show else None
            if state != run_state:
                if run_state == hot:
                    p.band_x(run_start, i, "wash")
                run_start, run_state = i, state
        p.hline(0.0, "zero")
        p.path([(i, max(-4.2, min(4.2, obs[i]))) for i in range(show)], "px")
        for st in (0, 1):
            p.hline(fitted.means[st], "lvl")

    regime_panel(46, "regime", "Deux régimes réels", 150)
    regime_panel(212, "short", "Bruit pur, série courte", 120)

    p3 = Panel(b, 498, 46, 104, 284, title="Séparabilité",
               readout="d′ décide de tout")
    p3.domain(0.05, 2.5, 3.0, 40000.0, ylog=True)
    p3.frame()
    p3.grid_y([10, 100, 1000, 10000],
              lambda v: {10: "10", 100: "100", 1000: "1 k", 10000: "10 k"}[int(v)],
              side="right")
    p3.grid_x([0.5, 1.0, 1.5, 2.0], lambda v: _num(v, 1), label="d′")
    ds = [0.05 + 0.02 * k for k in range(0, 123)]
    p3.path([(d, observations_to_separate(d)) for d in ds], "s1")
    for kind, cls, lab in (("regime", "s2", "réels"), ("short", "s3", "inventés")):
        fitted = q.hmm_fit(kind)[0]
        d = separability(fitted.means[0], fitted.means[1],
                         0.5 * (fitted.sds[0] + fitted.sds[1]))
        if 0.05 <= d <= 2.5:
            n = observations_to_separate(d)
            p3.dot(d, n, cls, f"d′ = {d:.2f} · {n:.0f} observations")
            p3.label(d, n, lab, dx=-7, dy=-9, anchor="end", cls="dl halo")

    b.legend(56, 356, [("s2f", "régimes réels"), ("s3f", "régimes inventés")],
             step=150)
    b.caption(56, 380, "la bande claire est l'état de moyenne haute selon Viterbi ; "
                       "dans le panneau du bas elle ne recouvre rien de réel — "
                       f"l'erreur de Bayes à d′ = 0,5 vaut {_num(100 * bayes_error(0.5), 0)} %",
              anchor="start")
    return b.render("HMM ajusté sur une série à deux régimes puis sur du bruit pur, "
                    "et séparabilité requise")


def _bic_delta(kind: str) -> float:
    from . import quant as q
    from .hmm import bic
    fitted, loglik, _, _, ll1 = q.hmm_fit(kind)
    n = len(q.hmm_series(kind)[0])
    return bic(loglik, fitted.n_free_parameters, n) - bic(ll1, 2, n)


# ---------------------------------------------------------------------------
# Sélection : la barre que le nombre d'essais fait monter
# ---------------------------------------------------------------------------

def fig_selection() -> str:
    """Le Sharpe déflaté sur le plan (essais, longueur d'historique).

    En haut, le Sharpe attendu du meilleur essai **sans aucun edge**, et le
    Sharpe de l'edge de référence : leur croisement, atteint avant le
    troisième essai, est la frontière de déclarabilité. En bas, la surface du
    Sharpe déflaté — la probabilité que l'edge survive à la déflation. Elle
    tombe d'une falaise dès la dizaine d'essais et ne remonte qu'avec des
    historiques que la stratégie n'aura pas.
    """
    from . import quant as q
    from .overfit import deflated_sharpe, expected_max_sharpe
    from .pathstats import annualise

    e0 = q.edge_law()
    sr = e0.sharpe_per_trade
    sd_tr = 1.0 / math.sqrt(q.TRADES_PER_YEAR)
    b = Board(660, 524)

    p1 = Panel(b, 92, 46, 480, 146, title="La barre de sélection",
               readout="Sharpe annualisé, un an d'historique")
    p1.domain(1, 2000, 0.0, 4.0, xlog=True)
    p1.frame()
    p1.grid_y([1, 2, 3, 4], lambda v: f"{v:g}")
    p1.grid_x([1, 3, 10, 30, 100, 300, 1000], lambda v: f"{v:g}",
              label="configurations essayées")
    ks = sorted({int(round(10 ** (0.05 * j))) for j in range(0, 67)})
    p1.path([(k, annualise(expected_max_sharpe(k, sd_tr), q.TRADES_PER_YEAR))
             for k in ks if k >= 1], "s2")
    ref = annualise(sr, q.TRADES_PER_YEAR)
    p1.path([(1, ref), (2000, ref)], "s1", dash="4 3")
    p1.label(1600, ref, "edge de référence", dx=-6, dy=-8, anchor="end", cls="dl halo")
    for k in (10, 100, 1000):
        v = annualise(expected_max_sharpe(k, sd_tr), q.TRADES_PER_YEAR)
        p1.dot(k, v, "s2", f"{k} essais · Sharpe attendu {v:.2f}")
        p1.label(k, v, _num(v, 2), dx=0, dy=-10, anchor="middle", cls="dl halo")
    # Croisement des deux courbes : premier k dont le maximum attendu dépasse l'edge.
    cross = next((k for k in ks if annualise(expected_max_sharpe(k, sd_tr),
                                             q.TRADES_PER_YEAR) >= ref), None)
    if cross:
        p1.vline(cross, "lvl strong")
        p1.label(cross, 3.3, f"{cross} essais suffisent", dx=6, dy=0, cls="lg halo")

    years = [1.0, 3.0, 10.0, 30.0]
    trials = [1, 10, 100, 1000]
    z = [[deflated_sharpe(sr, int(round(y * q.TRADES_PER_YEAR)), k,
                          e0.skewness, e0.excess_kurtosis) for y in years]
         for k in trials]
    surface(
        b, 330.0, 424.0, z, 0.0, 1.0, cx=25.0, cy=11.0, cz=118.0,
        row_labels=["1 essai", "10 essais", "100 essais", ""],
        col_labels=["", "", "", "30 ans"],
        z_ticks=[(0.0, "0"), (0.5, "0,5"), (0.95, "0,95"), (1.0, "1")],
        tip="DSR = {v:.3f}",
        classify=lambda v: heat_class(v),
    )
    b.add('<text class="hdr" x="56" y="256">Sharpe déflaté</text>')
    b.add('<text class="sub" x="56" y="270">probabilité que l\'edge de référence '
          'survive à la déflation</text>')
    b.add('<text class="sub" x="56" y="283">axe gauche : essais · axe droit : '
          'historique (1, 3, 10, 30 ans)</text>')

    b.legend(92, 232, [("s2", "meilleur essai sans edge"),
                       ("s1", "edge de référence")], step=210, kind="line")
    b.caption(330, 444, "seule la face « un seul essai, historique long » dépasse "
                        "0,95 ; partout ailleurs la sélection explique le résultat")
    return b.render("Barre de sélection en Sharpe annualisé et surface du Sharpe "
                    "déflaté sur le plan essais × historique")


# ---------------------------------------------------------------------------
# PBO : la probabilité de surajustement, et sa propre dispersion
# ---------------------------------------------------------------------------

def fig_pbo() -> str:
    """La PBO est un instrument de mesure, et il a lui-même une précision.

    À gauche, les deux lois d'échantillonnage de la PBO — familles sans edge,
    puis famille contenant un edge unique — obtenues en répétant l'expérience
    sur des backtests synthétiques indépendants. Leur recouvrement délimite la
    zone où une lecture isolée ne conclut rien. À droite, la dégradation
    apprentissage → test, qui est la même information lue en performance
    plutôt qu'en rang.
    """
    from . import quant as q
    from .mc import quantile

    flat, real = q.cscv_distribution()
    b = Board(660, 276)

    p1 = Panel(b, 56, 46, 268, 170, title="Loi d'échantillonnage de la PBO",
               readout=f"{_num(q.CSCV_REPS, 0)} backtests synthétiques")
    p1.domain(0.0, 1.0, 0.0, 4.0)
    p1.frame()
    p1.grid_y([1, 2, 3, 4], lambda v: f"{v:g}")
    p1.grid_x([0, 0.25, 0.5, 0.75, 1.0], lambda v: _num(v, 2), label="PBO")
    histogram(p1, list(flat), 20, "area ar3", 0.0, 1.0, width_frac=0.96)
    histogram(p1, list(real), 20, "area ar1", 0.0, 1.0, width_frac=0.60)
    p1.vline(0.5, "lvl strong")
    p1.label(0.5, 3.7, "½ — symétrie", dx=5, dy=0, cls="lg halo")
    q05, q95 = quantile(list(flat), 0.05), quantile(list(real), 0.95)
    p1.band_x(q95, q05, "wash")
    p1.label(0.5 * (q95 + q05), 2.9, "zone indécise", dx=0, dy=0,
             anchor="middle", cls="dl halo")

    # --- P2 : dégradation apprentissage → test ----------------------------
    p2 = Panel(b, 372, 46, 264, 170, title="Dégradation hors échantillon",
               readout="performance par sous-période")
    entries = [("sans edge", q.cscv_null()), ("un edge réel", q.cscv_edge())]
    p2.domain(-0.5, 1.5, -0.05, 0.30)
    p2.frame()
    p2.grid_y([0.0, 0.1, 0.2, 0.3], lambda v: _num(v, 2))
    p2.hline(0.0, "zero")
    for i, (lab, res) in enumerate(entries):
        p2.vbar(i, 0.0, res.degradation, 62.0, "dn" if res.degradation > 0 else "s1f",
                f"{lab} · dégradation {res.degradation:+.3f}")
        p2.board.add(f'<text class="tk" x="{p2.sx(i):.1f}" y="{p2.y + p2.h + 14:.1f}" '
                     f'text-anchor="middle">{_esc(lab)}</text>')
        p2.label(i, res.degradation, _signed(res.degradation, 3), dx=0, dy=-8,
                 anchor="middle", cls="dl halo")

    b.legend(56, 246, [("s2f", "aucune configuration n'a d'edge"),
                       ("s1f", "une seule en possède un")], step=250)
    b.caption(330, 268, "sous la zone claire, une PBO isolée ne sépare pas les deux "
                        "hypothèses")
    return b.render("Loi d échantillonnage de la probabilité de surajustement et "
                    "dégradation hors échantillon")


# ---------------------------------------------------------------------------
# Validation croisée : purge, embargo, marche avant
# ---------------------------------------------------------------------------

def fig_crossval() -> str:
    """La géométrie des plis, et le coût de l'honnêteté.

    Les deux bandeaux montrent, pli par pli, ce qui reste d'apprentissage
    après purge et embargo, puis ce que la marche avant autorise. La surface
    donne la fuite d'une validation croisée naïve en fonction du nombre de
    plis et de la durée d'exposition d'un trade : elle sature à 1, et cette
    saturation est le point — au-delà, la validation croisée ne valide plus
    rien du tout.
    """
    from . import quant as q
    from .overfit import leakage_fraction, purged_folds, walk_forward_windows

    n_obs = int(q.SESSION_MIN)
    horizon = int(round(q.geometry(q.RR_REF).expected_time))
    folds = purged_folds(n_obs, 5, horizon=horizon, embargo_pct=0.01)
    wf = walk_forward_windows(n_obs, 5)

    b = Board(660, 340)

    def ribbon(px: float, py: float, w: float, title: str, sub: str,
               plan: list[tuple[tuple[int, ...], tuple[int, ...]]]) -> None:
        b.add(f'<text class="hdr" x="{px:.1f}" y="{py - 12:.1f}">{_esc(title)}</text>')
        b.add(f'<text class="sub" x="{px + w:.1f}" y="{py - 12:.1f}" '
              f'text-anchor="end">{_esc(sub)}</text>')
        b.add(f'<line class="hsep" x1="{px:.1f}" y1="{py - 6:.1f}" '
              f'x2="{px + w:.1f}" y2="{py - 6:.1f}"/>')
        rh, gap = 15.0, 5.0
        for k, (test, train) in enumerate(plan):
            y = py + k * (rh + gap)
            b.add(f'<rect class="floor" x="{px:.1f}" y="{y:.1f}" '
                  f'width="{w:.1f}" height="{rh:.1f}"/>')
            tr = set(train)
            te = set(test)
            runs: list[tuple[int, int, str]] = []
            start, cur = 0, None
            for i in range(n_obs + 1):
                kind = ("train" if i in tr else "test" if i in te else "purge") \
                    if i < n_obs else None
                if kind != cur:
                    if cur is not None:
                        runs.append((start, i, cur))
                    start, cur = i, kind
            cls = {"train": "s1f", "test": "s2f", "purge": "ze"}
            for a, c, kind in runs:
                b.add(f'<rect class="{cls[kind]}" x="{px + w * a / n_obs:.1f}" '
                      f'y="{y + 1:.1f}" width="{max(w * (c - a) / n_obs, 0.6):.1f}" '
                      f'height="{rh - 2:.1f}"><title>{_esc(kind)} : '
                      f'{c - a} observations</title></rect>')
            b.add(f'<text class="tk" x="{px - 6:.1f}" y="{y + rh - 3:.1f}" '
                  f'text-anchor="end">{k + 1}</text>')

    kept = sum(len(f.train) for f in folds) / (5 * n_obs)
    ribbon(56, 46, 296, "Validation croisée purgée",
           f"apprentissage {_num(100 * kept, 0)} %",
           [(f.test, f.train) for f in folds])
    wf_kept = sum(len(f.train) for f in wf) / (5 * n_obs)
    ribbon(56, 190, 296, "Marche avant",
           f"apprentissage {_num(100 * wf_kept, 0)} %",
           [(f.test, f.train) for f in wf])

    horizons = [1, 3, 6, 12, 20, 30]
    fold_grid = [2, 3, 5, 8, 12, 20]
    z = [[leakage_fraction(n_obs, nf, h) for h in horizons] for nf in fold_grid]
    surface(
        b, 520.0, 236.0, z, 0.0, 1.0, cx=11.5, cy=6.2, cz=134.0,
        row_labels=["2 plis", "", "", "", "", "20"],
        col_labels=["1 min", "", "", "", "", "30"],
        z_ticks=[(0.0, "0"), (0.5, "½"), (1.0, "1")],
        tip="fuite = {v:.2f}",
        classify=lambda v: heat_class(v),
    )
    b.add('<text class="hdr" x="404" y="30">Fuite sans purge</text>')
    b.add('<text class="sub" x="404" y="44">part de l\'apprentissage</text>')
    b.add('<text class="sub" x="404" y="57">qui recouvre le test</text>')

    b.legend(56, 300, [("s1f", "apprentissage"), ("s2f", "test"),
                       ("ze", "purge et embargo")], step=104)
    b.caption(200, 328, "une observation par minute, séance de 390 minutes, "
                        f"exposition de {horizon} minutes")
    return b.render("Géométrie des plis purgés et de la marche avant, et surface de "
                    "fuite d une validation croisée naïve")


# ---------------------------------------------------------------------------
# Stress : scénarios, queues, sauts
# ---------------------------------------------------------------------------

def fig_stress() -> str:
    """Ce que le stop ne protège pas, en trois lectures.

    À gauche, l'échelle des scénarios ramenée en unités de risque et en années
    d'espérance : la seule échelle qui permette de comparer un choc de marché
    à un edge. Au centre, les mesures de queue d'un trade — l'écart entre la
    version gaussienne et la version exacte est d'un ordre de grandeur. À
    droite, la surface de l'espérance corrigée du risque de saut, sur le plan
    de la largeur du stop et de l'intensité des sauts.
    """
    from . import quant as q
    from .stress import (
        JumpModel, SCENARIOS, es_from_law, es_gaussian, jump_adjusted_expectancy,
        scenario_loss_r, var_from_law, var_gaussian,
    )
    from .horizon import outcome_scaled
    from .pathstats import law_from_outcome

    e0 = q.edge_law()
    annual = q.TRADES_PER_YEAR * e0.mean
    b = Board(660, 510)

    # --- P1 : échelle des scénarios ---------------------------------------
    losses = [(s.label, scenario_loss_r(s, q.INDEX_LEVEL, q.STOP_PTS))
              for s in SCENARIOS]
    losses.sort(key=lambda t: t[1])
    p1 = Panel(b, 148, 46, 220, 168, title="Scénarios",
               readout="en années d'espérance")
    p1.domain(0.0, max(v for _, v in losses) / annual * 1.14, -0.6, len(losses) - 0.4)
    p1.frame()
    p1.grid_x([0, 2, 4, 6, 8], lambda v: f"{v:g}", label="années de gain espéré")
    for i, (lab, v) in enumerate(losses):
        p1.hbar(i, 0.0, v / annual, 13.0, "dn",
                f"{lab} · {v:.0f} R · {v / annual:.1f} années")
        p1.board.add(f'<text class="tk" x="{p1.x - 6:.1f}" '
                     f'y="{p1.sy(i) + 3.5:.1f}" text-anchor="end">{_esc(lab)}</text>')
    p1.vline(1.0, "lvl strong")
    p1.label(1.0, len(losses) - 0.72, "une année", dx=4, dy=0, cls="lg halo")

    # --- P2 : mesures de queue --------------------------------------------
    tail = [
        ("VaR exacte", var_from_law(e0, 0.99), "s1f"),
        ("VaR gauss.", var_gaussian(e0.mean, e0.sd, 0.99), "dn"),
        ("ES exacte", es_from_law(e0, 0.99), "s1f"),
        ("ES gauss.", es_gaussian(e0.mean, e0.sd, 0.99), "dn"),
    ]
    p2 = Panel(b, 448, 46, 188, 168, title="Queue d'un trade", readout="99 %, en R")
    p2.domain(-0.6, len(tail) - 0.4, 0.0, 14.0)
    p2.frame()
    p2.grid_y([0, 4, 8, 12], lambda v: f"{v:g}")
    for i, (lab, v, cls) in enumerate(tail):
        p2.vbar(i, 0.0, v, 26.0, cls, f"{lab} · {v:.2f} R")
        p2.board.add(f'<text class="tk" transform="translate({p2.sx(i):.1f},'
                     f'{p2.y + p2.h + 32:.1f}) rotate(-32)" text-anchor="middle">'
                     f'{_esc(lab)}</text>')
    p2.hline(1.0, "lvl strong")
    p2.label(0.0, 1.0, "le stop", dx=0, dy=-9, anchor="middle", cls="lg halo")

    # --- P3 : surface de l'espérance corrigée du saut ---------------------
    stops_pct = [0.025, 0.050, 0.100, 0.200]
    intensities = [0.0, 0.05, 0.15, 0.40]
    mu = q.reference_drift()
    z = []
    for pct in stops_pct:
        a = q.INDEX_LEVEL * pct / 100.0
        o = outcome_scaled(a, q.RR_REF * a, q.SESSION_MIN, q.SIGMA_1MIN, q.HURST)
        base = law_from_outcome(o, a, q.RR_REF * a, q.FRICTION)
        target = (mu * o.expected_time - q.FRICTION) / a
        row = []
        for lam in intensities:
            law = base.tilted_to_mean(target)
            model = JumpModel(lam, 0.0, q.JUMP.sd_jump)
            row.append(jump_adjusted_expectancy(law, model, a, o.expected_time,
                                                q.SESSION_MIN))
        z.append(row)
    surface(
        b, 330.0, 424.0, z, -0.15, 0.25, cx=25.0, cy=11.0, cz=118.0,
        row_labels=["stop 0,025 %", "0,050 %", "0,100 %", ""],
        col_labels=["", "", "", "λ = 0,40"],
        z_ticks=[(-0.15, "−0,15"), (0.0, "0"), (0.20, "+0,20")],
        tip="E[R] corrigée = {v:+.3f} R",
    )
    b.add('<text class="hdr" x="56" y="266">Espérance après correction de saut</text>')
    b.add('<text class="sub" x="56" y="281">axe gauche : largeur du stop · '
          'axe droit : intensité de saut (0 ; 0,05 ; 0,15 ; 0,40 par séance)</text>')

    b.legend(148, 236, [("s1f", "loi exacte"), ("dn", "approximation gaussienne")],
             step=160)
    b.caption(330, 500, "un stop plus large coûte plus par trade mais encaisse le "
                        "saut : la surface change de signe dans les deux directions")
    return b.render("Échelle des scénarios de choc, mesures de queue d un trade, et "
                    "espérance corrigée du risque de saut")


# ---------------------------------------------------------------------------
# Dimensionnement : Kelly, croissance, ruine
# ---------------------------------------------------------------------------

def fig_sizing() -> str:
    """La mise, la croissance qu'elle produit, et la ruine qu'elle expose.

    La courbe de croissance logarithmique est plate au voisinage de son
    optimum et brutale au-delà : miser le double de Kelly annule la
    croissance sans rien ajouter au rendement espéré. La surface du bas
    montre la même chose sur le plan (edge supposé, fraction misée), et son
    message est le seul qui compte en pratique : **l'erreur d'estimation de
    l'edge se paie sur l'axe de la mise**, pas sur celui du rendement.
    """
    from . import quant as q
    from .drawdown import adjustment_coefficient, risk_of_ruin

    e0 = q.edge_law()
    f_star = e0.kelly_fraction()
    b = Board(660, 508)

    p1 = Panel(b, 92, 46, 224, 146, title="Croissance par trade",
               readout=f"f* = {_num(100 * f_star, 2)} %")
    fmax = 3.0 * f_star
    p1.domain(0.0, fmax, -0.004, 0.002)
    p1.frame()
    p1.grid_y([-0.004, -0.002, 0.0, 0.002], lambda v: _num(v * 1000, 0),
              label="‰ par trade")
    p1.grid_x([0, f_star, 2 * f_star, 3 * f_star],
              lambda v: _num(100 * v, 1) + " %", label="fraction misée")
    p1.hline(0.0, "zero")
    xs = [fmax * k / 200.0 for k in range(0, 201)]
    p1.path([(x, e0.growth_rate(x)) for x in xs], "s1")
    p1.vline(f_star, "lvl strong")
    p1.dot(f_star, e0.growth_rate(f_star), "s1", f"optimum f* = {f_star:.4f}")
    p1.label(f_star, e0.growth_rate(f_star), "Kelly", dx=7, dy=-6, cls="dl halo")
    p1.vline(2 * f_star, "lvl")
    p1.label(2 * f_star, -0.0032, "2× Kelly", dx=-6, dy=0, anchor="end", cls="lg halo")

    theta = adjustment_coefficient(e0)
    p2 = Panel(b, 380, 46, 192, 146, title="Ruine de Lundberg",
               readout=f"θ* = {_num(theta, 4)}")
    p2.domain(0.0, 600.0, 0.001, 1.0, ylog=True)
    p2.frame()
    p2.grid_y([0.001, 0.01, 0.1, 1.0], lambda v: _num(v, 3))
    p2.grid_x([0, 200, 400, 600], lambda v: f"{v:g}", label="profondeur (R)")
    p2.path([(d, max(risk_of_ruin(e0, d), 1e-4)) for d in range(1, 601, 3)], "s1")
    for p_lvl, lab in ((0.05, "1 an sur 20"), (0.01, "1 sur 100")):
        depth = -math.log(p_lvl) / theta
        if depth <= 600:
            p2.dot(depth, p_lvl, "s2", f"{lab} : {depth:.0f} R")
            p2.label(depth, p_lvl, f"{lab} : {_num(depth, 0)} R", dx=8, dy=13,
                     anchor="start", cls="dl halo")

    mults = [1.0, 2.0, 3.0, 5.0]
    fracs = [0.5 * f_star, f_star, 2.0 * f_star, 3.0 * f_star]
    o20 = q.geometry(q.RR_REF)
    mu_star = q.FRICTION / o20.expected_time
    base = q.null_law()
    z = []
    for k in mults:
        target = (k * mu_star * o20.expected_time - q.FRICTION) / q.STOP_PTS
        law = base.tilted_to_mean(target)
        z.append([law.growth_rate(fr) for fr in fracs])
    surface(
        b, 330.0, 412.0, z, -0.0022, 0.0038, cx=25.0, cy=11.0, cz=118.0,
        row_labels=["edge µ*", "", "", "5 µ*"],
        col_labels=["", "", "", "3 f*"],
        z_ticks=[(-0.002, "−2"), (0.0, "0"), (0.002, "+2")],
        tip="croissance = {v:+.5f} par trade",
    )
    b.add('<text class="hdr" x="56" y="248">Croissance (‰ par trade)</text>')
    b.add('<text class="sub" x="56" y="263">axe gauche : edge supposé (µ*, 2 µ*, '
          '3 µ*, 5 µ*) · axe droit : fraction misée (½ f*, f*, 2 f*, 3 f*)</text>')
    b.caption(330, 484, "la surface est presque plate le long de l'axe de l'edge et "
                        "abrupte le long de celui de la mise")
    b.caption(330, 498, "surmiser un edge correct ruine plus vite que sous-miser un "
                        "edge fort n'appauvrit")
    return b.render("Croissance logarithmique et fraction de Kelly, probabilité de "
                    "ruine de Lundberg, et surface de croissance")


ALL_FIGURES = {
    "qratios": fig_ratios,
    "qdrawdown": fig_drawdown,
    "qmontecarlo": fig_montecarlo,
    "qresampling": fig_resampling,
    "qhmm": fig_hmm,
    "qselection": fig_selection,
    "qpbo": fig_pbo,
    "qcrossval": fig_crossval,
    "qstress": fig_stress,
    "qsizing": fig_sizing,
}


def render_all() -> dict[str, str]:
    """Toutes les planches de ce module, prêtes à être insérées dans le document."""
    return {name: fn() for name, fn in ALL_FIGURES.items()}
