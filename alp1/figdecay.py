"""Figures des deux corrections : décote post-publication, exposant d'échelle.

Mêmes conventions que les autres modules de figures — toile partagée, couleurs
par variables CSS, et chaque point calculé par la fonction qui produit la table
correspondante.

    decayrunway  — que reste-t-il de la dérive, et jusqu'à quand ?
    decayrate    — sur quelle part de la boîte de taux la conclusion survit-elle ?
    scalinghurst — dans quel sens l'exposant d'échelle déplace-t-il le seuil ?
"""

from __future__ import annotations

from .decay import breaking_rate, decay_rate, rate_box, runways, surviving_edge
from .figures import Canvas, _esc, _legend, _num
from .report3 import ASOF_YEAR, EDGE_BPS, _breaking_edge_bps
from .scaling import HURST_HI, HURST_LO, sensitivity

BRK = _breaking_edge_bps()


# ---------------------------------------------------------------------------
# 1 — la dérive s'arbitre, et la fenêtre se referme
# ---------------------------------------------------------------------------

def fig_decay_runway() -> str:
    """Dérive subsistante contre point de rupture, année par année.

    La question tranchée : combien de temps reste-t-il pour mesurer un effet
    qu'on n'a pas mesuré ? La réponse se lit à l'intersection de la courbe et
    de l'horizontale.
    """
    c = Canvas(640, 268, left=52, right=124, top=18, bottom=42)
    rws = runways(EDGE_BPS, BRK, ASOF_YEAR)
    first = rws[0]
    lam = decay_rate()

    y0, y1 = first.published, first.published + 14
    c.domain(y0, y1, 0.0, EDGE_BPS * 1.08)
    c.grid_y([0, 1.16, 2, 4, 6],
             fmt=lambda v: _num(v, 2) if abs(v - BRK) < 0.01 else _num(v, 0),
             label="dérive captée (points de base)")
    ticks = sorted({y0, y0 + 4, ASOF_YEAR, y0 + 10, y0 + 13})
    c.ticks_x(ticks, fmt=lambda v: str(int(round(v))), label="année")

    # seuil de rupture
    yb = c.sy(BRK)
    c.add(f'<line class="hl" x1="{c.left:.1f}" y1="{yb:.1f}" '
          f'x2="{c.left + c.pw:.1f}" y2="{yb:.1f}"/>')
    c.add(f'<text class="dl halo" x="{c.left + 6:.1f}" y="{yb - 7:.1f}">'
          f'rupture {_esc(_num(BRK, 2))} pdb</text>')

    # colonne du présent
    xn = c.sx(ASOF_YEAR)
    c.add(f'<line class="gl" x1="{xn:.1f}" y1="{c.top:.1f}" '
          f'x2="{xn:.1f}" y2="{c.top + c.ph:.1f}" stroke-dasharray="3 3"/>')

    # une courbe par date de publication : la décote court depuis celle-ci
    for r, cls in zip(rws, ("s1", "s2")):
        pts = [(y, surviving_edge(EDGE_BPS, y - r.published, lam))
               for y in [r.published + i * 0.25
                         for i in range(int((y1 - r.published) * 4) + 1)]]
        c.path(pts, cls)
        c.dot(r.published, EDGE_BPS, cls,
              f"{r.source} · dérive publiée {_num(EDGE_BPS, 2)} pdb")
        c.dot(ASOF_YEAR, r.edge_today, cls,
              f"{r.source} · restant en {ASOF_YEAR} : {_num(r.edge_today, 2)} pdb")
        c.dot(r.expiry, BRK, cls,
              f"{r.source} · rupture en {int(round(r.expiry))}")

    c.label(ASOF_YEAR, first.edge_today, f"{_num(first.edge_today, 2)} pdb",
            anchor="end", dx=-9, dy=-6)
    c.add(_legend(c.left + c.pw + 12, c.top + 18,
                  [("s1", "publié en " + str(rws[0].published)),
                   ("s2", "publié en " + str(rws[-1].published))]))
    c.add(f'<text class="lg" x="{c.left + c.pw + 12:.1f}" y="{c.top + 60:.1f}">'
          f'rupture en {_esc(str(int(round(first.expiry))))}</text>')
    c.add(f'<text class="lg" x="{c.left + c.pw + 12:.1f}" y="{c.top + 74:.1f}">'
          f'et en {_esc(str(int(round(rws[-1].expiry))))}</text>')
    return c.render(
        "Dérive subsistante après décote post-publication, comparée au point de "
        "rupture de l'espérance nette")


# ---------------------------------------------------------------------------
# 2 — la conclusion sur la boîte de taux
# ---------------------------------------------------------------------------

def fig_decay_rate() -> str:
    """Marge sur le point de rupture en fonction du taux de décroissance."""
    c = Canvas(640, 244, left=54, right=118, top=18, bottom=42)
    rws = runways(EDGE_BPS, BRK, ASOF_YEAR)
    lo, mid, hi = rate_box()
    age0 = rws[0].age

    c.domain(lo, hi, 0.0, EDGE_BPS / BRK * 1.08)
    c.grid_y([0, 1, 2, 3, 4, 5], fmt=lambda v: _num(v, 0) + "×",
             label="marge sur le point de rupture")
    c.ticks_x([lo, 0.07, 0.145, 0.217, hi], fmt=lambda v: _num(v, 3),
              label="taux de décroissance annuel")

    y1 = c.sy(1.0)
    c.add(f'<line class="hl" x1="{c.left:.1f}" y1="{y1:.1f}" '
          f'x2="{c.left + c.pw:.1f}" y2="{y1:.1f}"/>')

    for age, cls, name in ((age0, "s1", str(rws[0].published)),
                           (rws[-1].age, "s2", str(rws[-1].published))):
        pts = [(lo + (hi - lo) * i / 80.0,
                surviving_edge(EDGE_BPS, age, lo + (hi - lo) * i / 80.0) / BRK)
               for i in range(81)]
        c.path(pts, cls)
        c.dot(mid, surviving_edge(EDGE_BPS, age, mid) / BRK, cls,
              f"publié en {name} · taux retenu · marge "
              f"{_num(surviving_edge(EDGE_BPS, age, mid) / BRK, 2)}×")

    xb = c.sx(breaking_rate(EDGE_BPS, BRK, age0))
    c.add(f'<line class="gl" x1="{xb:.1f}" y1="{c.top:.1f}" '
          f'x2="{xb:.1f}" y2="{c.top + c.ph:.1f}" stroke-dasharray="3 3"/>')
    c.add(f'<text class="dl halo" x="{xb - 6:.1f}" y="{c.top + 14:.1f}" '
          f'text-anchor="end">bascule</text>')

    c.add(_legend(c.left + c.pw + 10, c.top + 18,
                  [("s1", "publié en " + str(rws[0].published)),
                   ("s2", "publié en " + str(rws[-1].published))]))
    return c.render(
        "Marge sur le point de rupture selon le taux de décroissance annuel "
        "supposé de l'effet publié")


# ---------------------------------------------------------------------------
# 3 — l'exposant d'échelle joue contre la stratégie
# ---------------------------------------------------------------------------

def fig_scaling_hurst() -> str:
    """Seuil de signal et probabilité d'arrêt en fonction de l'exposant.

    Les deux courbes montent ensemble : la persistance que le document invoque
    pour rendre les targets atteignables rend aussi le stop plus fréquent et le
    seuil plus exigeant. Le second effet domine, parce que le target n'est
    presque jamais atteint.
    """
    c = Canvas(640, 250, left=56, right=126, top=20, bottom=42)
    pts = sensitivity(HURST_LO, HURST_HI, 25)

    ir_lo = min(s.ir_star for s in pts)
    ir_hi = max(s.ir_star for s in pts)
    pad = (ir_hi - ir_lo) * 0.35
    c.domain(HURST_LO, HURST_HI, ir_lo - pad, ir_hi + pad)
    c.grid_y([0.0085, 0.0090, 0.0095], fmt=lambda v: _num(v, 4),
             label="IR* requis du signal")
    c.ticks_x([0.50, 0.55, 0.60, 0.65], fmt=lambda v: _num(v, 2),
              label="exposant d'échelle H")

    c.path([(s.hurst, s.ir_star) for s in pts], "s1")
    for s in (pts[0], pts[-1]):
        c.dot(s.hurst, s.ir_star, "s1",
              f"H = {_num(s.hurst, 2)} · IR* {_num(s.ir_star, 4)} · "
              f"P(stop) {_num(s.p_stop * 100, 1)} %")

    # seconde échelle : probabilité d'arrêt, tracée en relatif
    p_lo = min(s.p_stop for s in pts)
    p_hi = max(s.p_stop for s in pts)
    span = c.ph
    top = c.top

    def py(p: float) -> float:
        return top + span * (1.0 - (p - p_lo) / (p_hi - p_lo)) * 0.92 + span * 0.04

    d = " ".join(("M" if i == 0 else "L") + f"{c.sx(s.hurst):.2f},{py(s.p_stop):.2f}"
                 for i, s in enumerate(pts))
    c.add(f'<path class="ln s3" d="{d}" stroke-dasharray="5 3"/>')
    # une seule annotation, posée dans le quadrant que ni l'une ni l'autre des
    # deux courbes ne traverse — les deux montent de gauche à droite.
    c.add(f'<text class="dl halo" x="{c.left + c.pw - 8:.1f}" '
          f'y="{c.top + c.ph - 16:.1f}" text-anchor="end">'
          f'P(stop) : {_esc(_num(p_lo * 100, 1))} % \u2192 '
          f'{_esc(_num(p_hi * 100, 1))} %</text>')

    c.add(_legend(c.left + c.pw + 10, c.top + 20,
                  [("s1", "IR* requis"), ("s3", "P(stop), échelle libre")]))
    return c.render(
        "Seuil de signal requis et probabilité d'arrêt en fonction de l'exposant "
        "d'échelle, calibration refaite à chaque point")


FIGURES = {
    "decayrunway": fig_decay_runway,
    "decayrate": fig_decay_rate,
    "scalinghurst": fig_scaling_hurst,
}


def render_all() -> dict[str, str]:
    return {k: fn() for k, fn in FIGURES.items()}
