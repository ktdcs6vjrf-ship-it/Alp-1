"""Figures propres à ALP-2, en SVG autonome.

Mêmes conventions que `alp1.figures` : la toile et les primitives en sont
réutilisées, les couleurs passent par les variables CSS du document, et chaque
point est calculé par la fonction qui produit la table correspondante — un
chiffre du texte et un point de graphique ne peuvent donc pas diverger.

Les cinq figures répondent chacune à une question que la prose pose :

    a2exposure  — jusqu'où élargir le stop achète-t-il du temps de marché ?
    a2threshold — de combien la géométrie abaisse-t-elle le seuil de signal ?
    a2friction  — à quel quantile la friction efface-t-elle la dérive ?
    a2breaking  — que faudrait-il croire pour renverser la conclusion ?
    a2power     — à partir de quel échantillon la mesure décide-t-elle ?
"""

from __future__ import annotations

import math

from .calib import BOX, REFERENCE, breaking_points, derive
from .costs import COST_BASE, COST_REALISTIC, ES, deflated_threshold_sharpe
from .figures import Canvas, _esc, _legend, _num
from .friction import RETAIL_ES, friction_law
from .momentum import (
    edge_points_from_bps,
    mean_abs_move,
    required_ir,
    sharpe_per_trade,
    time_exit_outcome,
)

D = derive(REFERENCE)
SIGMA_1MIN = D.sigma_1min
SESSION_MIN = REFERENCE.session_min
ENTRY_MIN = REFERENCE.entry_min
HORIZON_MIN = SESSION_MIN - ENTRY_MIN
BAND = mean_abs_move(SIGMA_1MIN, ENTRY_MIN)
FRICTION = COST_BASE.friction_points(ES)
FRICTION_REAL = COST_REALISTIC.friction_points(ES)
EDGE_PTS = edge_points_from_bps(REFERENCE.edge_bps, REFERENCE.index_level)

AXIS_LABELS = {
    "index_level": "niveau d'indice",
    "session_dispersion": "dispersion de séance",
    "entry_min": "heure d'entrée",
    "friction": "friction par aller-retour",
    "edge_bps": "dérive captée",
}


# ---------------------------------------------------------------------------
# 1 — l'exposition sature
# ---------------------------------------------------------------------------


def fig_exposure_saturation() -> str:
    """Exposition et seuil de signal en fonction de la largeur du stop.

    La question que tranche cette figure : élargir le stop achète du temps de
    marché, mais jusqu'où ? La courbe d'exposition sature en approchant la
    durée restante de la séance, tandis que le risque, lui, croît sans borne.
    La bande de bruit est le seul point de l'axe qui ne soit pas choisi.
    """
    c = Canvas(640, 250, left=54, right=150, top=18, bottom=38)
    stops = [4.0 + 0.5 * i for i in range(int((50.0 - 4.0) / 0.5) + 1)]

    expo = [(s, time_exit_outcome(s, HORIZON_MIN, SIGMA_1MIN).expected_time) for s in stops]
    c.domain(4.0, 50.0, 0.0, HORIZON_MIN * 1.02)

    c.grid_y([0, 60, 120, 180, 240, 300],
             fmt=lambda v: f"{v:g}", label="exposition E[τ∧T] (min)")
    c.ticks_x([10, 20, 30, 40, 50], fmt=lambda v: f"{v:g}",
              label="largeur du stop (points d'indice)")

    # Plafond : la séance restante.
    y_cap = c.sy(HORIZON_MIN)
    c.add(f'<line class="zero" x1="{c.left:.1f}" y1="{y_cap:.1f}" '
          f'x2="{c.left + c.pw:.1f}" y2="{y_cap:.1f}" stroke-dasharray="4 3"/>')
    c.add(f'<text class="lg" x="{c.left + c.pw - 4:.1f}" y="{y_cap - 6:.1f}" '
          f'text-anchor="end">séance restante — {_num(HORIZON_MIN, 0)} min</text>')

    c.path(expo, "s1")

    o = time_exit_outcome(BAND, HORIZON_MIN, SIGMA_1MIN)
    c.dot(BAND, o.expected_time, "s1", f"bande {_num(BAND, 1)} pt → {_num(o.expected_time, 0)} min")
    c.add(f'<line class="mark" x1="{c.sx(BAND):.1f}" y1="{c.sy(0):.1f}" '
          f'x2="{c.sx(BAND):.1f}" y2="{c.sy(o.expected_time):.1f}" stroke-dasharray="3 3"/>')
    c.label(BAND, o.expected_time, f"bande de bruit — {_num(BAND, 1)} pt", dx=9, dy=-8)

    # Rendement marginal : minutes gagnées par point de stop supplémentaire.
    marg = []
    for i in range(1, len(expo)):
        (s0, e0), (s1, e1) = expo[i - 1], expo[i]
        marg.append(((s0 + s1) / 2, (e1 - e0) / (s1 - s0)))
    m_max = max(v for _, v in marg)
    scaled = [(s, v / m_max * HORIZON_MIN * 0.92) for s, v in marg]
    c.path(scaled, "s2", dash="5 3")

    legend = _legend(c.left + c.pw + 12, c.top + 26, [
        ("s1", "exposition"),
        ("s2", "minutes gagnées"),
    ])
    c.add(legend)
    c.add(f'<text class="lg" x="{c.left + c.pw + 12:.1f}" y="{c.top + 72:.1f}">'
          f'par point de stop</text>')
    c.add(f'<text class="lg" x="{c.left + c.pw + 12:.1f}" y="{c.top + 87:.1f}">'
          f'ajouté (échelle libre)</text>')

    return c.render("Exposition et rendement marginal selon la largeur du stop")


# ---------------------------------------------------------------------------
# 2 — le seuil que la géométrie impose au signal
# ---------------------------------------------------------------------------


def fig_threshold_drop() -> str:
    """Seuil de qualité de signal exigé par chaque géométrie.

    C'est l'argument central du document, réduit à une seule grandeur. Le stop
    large ne rend pas le signal meilleur : il abaisse la barre que le signal
    doit franchir. Les barres sont le seuil IR* ; le trait vertical est le
    ratio d'information qu'implique la dérive documentée.
    """
    c = Canvas(640, 216, left=190, right=110, top=22, bottom=42)

    # Chaque géométrie est évaluée sous sa propre calibration, exactement comme
    # dans la table qu'accompagne cette figure : ALP-1 sous le σ₁ qu'il pose,
    # ALP-2 sous celui que sa dispersion de séance implique.
    from .report2 import V1_SIGMA_1MIN, v1_outcome, v2_outcome

    o1, o2 = v1_outcome(), v2_outcome()

    rows = [
        ("ALP-1 · 1:20, friction réaliste",
         required_ir(FRICTION_REAL, V1_SIGMA_1MIN, o1.expected_time), "s2"),
        ("ALP-1 · 1:20, friction de référence",
         required_ir(FRICTION, V1_SIGMA_1MIN, o1.expected_time), "s2"),
        ("ALP-2 · bande, friction réaliste",
         required_ir(FRICTION_REAL, SIGMA_1MIN, o2.expected_time), "s1"),
        ("ALP-2 · bande, friction de référence",
         required_ir(FRICTION, SIGMA_1MIN, o2.expected_time), "s1"),
    ]
    ir_signal = EDGE_PTS / (SIGMA_1MIN * math.sqrt(o2.expected_time))
    top = max(max(v for _, v, _ in rows), ir_signal) * 1.18

    c.domain(0.0, top, 0.0, 1.0)
    band_h, gap = 22.0, 12.0
    y = c.top + 6

    for label, val, cls in rows:
        c.add(f'<rect class="area ar{"1" if cls == "s1" else "3"}" '
              f'x="{c.left:.1f}" y="{y:.1f}" width="{c.sx(val) - c.left:.2f}" '
              f'height="{band_h:.1f}"><title>IR* = {_num(val, 4)}</title></rect>')
        c.add(f'<text class="lg" x="{c.left - 8:.1f}" y="{y + band_h / 2 + 4:.1f}" '
              f'text-anchor="end">{_esc(label)}</text>')
        c.add(f'<text class="dl halo" x="{c.sx(val) + 7:.1f}" '
              f'y="{y + band_h / 2 + 4:.1f}">{_num(val, 4)}</text>')
        y += band_h + gap

    x_sig = c.sx(ir_signal)
    c.add(f'<line class="hl" x1="{x_sig:.1f}" y1="{c.top - 4:.1f}" '
          f'x2="{x_sig:.1f}" y2="{y - gap + 6:.1f}"/>')
    c.add(f'<text class="dl halo" x="{x_sig:.1f}" y="{c.top - 9:.1f}" '
          f'text-anchor="middle">signal documenté — IR = {_num(ir_signal, 3)}</text>')

    c.add(f'<line class="ba" x1="{c.left:.1f}" y1="{y - gap + 6:.1f}" '
          f'x2="{c.left + c.pw:.1f}" y2="{y - gap + 6:.1f}"/>')
    for v in (0.0, 0.02, 0.04, 0.06, 0.08):
        if v <= top:
            c.add(f'<text class="tk" x="{c.sx(v):.1f}" y="{y - gap + 20:.1f}" '
                  f'text-anchor="middle">{_num(v, 2)}</text>')
    c.add(f'<text class="ax" x="{c.left + c.pw / 2:.1f}" y="{c.height - 4:.1f}" '
          f'text-anchor="middle">ratio d\'information exigé du signal, IR*</text>')

    return c.render("Seuil de qualité de signal exigé par chaque géométrie")


# ---------------------------------------------------------------------------
# 3 — la friction déduite, et sa queue
# ---------------------------------------------------------------------------


def fig_friction_tail() -> str:
    """Quantiles de la friction déduite du carnet, face à la dérive documentée.

    La friction n'est pas un point mais une loi. Ce qui décide n'est pas sa
    moyenne mais le quantile auquel elle rejoint la dérive — et il est très
    loin dans la queue.
    """
    c = Canvas(640, 248, left=58, right=24, top=20, bottom=40)

    o = time_exit_outcome(BAND, HORIZON_MIN, SIGMA_1MIN)
    law = friction_law(SIGMA_1MIN, o.p_stop, 1.0, RETAIL_ES)

    qs = [0.50 + 0.499 * (i / 200) ** 0.35 for i in range(201)]
    pts = [(q, law.quantile(q)) for q in qs]
    top = max(EDGE_PTS * 1.15, max(v for _, v in pts) * 1.05)

    c.domain(0.5, 0.999, 0.0, top)
    c.grid_y([0, 1, 2, 3], fmt=lambda v: f"{v:g}", label="friction aller-retour (points)")
    c.ticks_x([0.5, 0.7, 0.9, 0.99],
              fmt=lambda v: f"{v * 100:g} %".replace(".", ","),
              label="quantile de la loi de friction")

    y_edge = c.sy(EDGE_PTS)
    c.add(f'<rect class="band" x="{c.left:.1f}" y="{c.top:.1f}" '
          f'width="{c.pw:.1f}" height="{y_edge - c.top:.1f}"/>')
    c.add(f'<line class="hl" x1="{c.left:.1f}" y1="{y_edge:.1f}" '
          f'x2="{c.left + c.pw:.1f}" y2="{y_edge:.1f}"/>')
    c.add(f'<text class="dl halo" x="{c.left + 8:.1f}" y="{y_edge - 8:.1f}">'
          f'dérive documentée — {_num(EDGE_PTS, 2)} pt '
          f'({_num(REFERENCE.edge_bps, 1)} pb)</text>')

    c.path(pts, "s2")

    # Les repères sont posés en alternance au-dessus et au-dessous de la
    # courbe : à l'approche du quantile 99 % la pente devient forte et deux
    # étiquettes du même côté se recouvriraient.
    for i, q in enumerate((0.50, 0.90, 0.99)):
        v = law.quantile(q)
        c.dot(q, v, "s2", f"q{q:.2f} → {_num(v, 3)} pt")
        c.label(q, v, _num(v, 2), dx=8, dy=(-9 if i % 2 == 0 else 15))

    c.add(f'<text class="lg" x="{c.left + c.pw - 6:.1f}" y="{c.top + 14:.1f}" '
          f'text-anchor="end">friction</text>')

    return c.render("Quantiles de la friction déduite face à la dérive documentée")


# ---------------------------------------------------------------------------
# 4 — ce qu'il faudrait croire pour renverser la conclusion
# ---------------------------------------------------------------------------


def fig_breaking_points() -> str:
    """Points de rupture rapportés à la boîte de plausibilité.

    Chaque ligne est une entrée du modèle. Le segment est la fourchette
    admise ; le repère est la valeur qui annulerait l'espérance, les autres
    entrées étant placées au plus défavorable. Aucun repère ne tombe dans son
    segment — c'est la lecture utile d'un test de sensibilité.
    """
    c = Canvas(640, 226, left=210, right=118, top=28, bottom=36)

    from .calib import CONCLUSIONS

    net = next(c_ for c_ in CONCLUSIONS if c_.key == "net_points")
    rows = breaking_points(net, BOX)

    c.domain(0.0, 1.0, 0.0, 1.0)
    row_h = (c.ph - 10) / max(len(rows), 1)

    for i, b in enumerate(rows):
        y = c.top + 6 + i * row_h + row_h / 2
        lo, hi = b.box_lo, b.box_hi
        span = max(hi - lo, 1e-12)
        # Échelle locale : la boîte occupe la moitié gauche, la rupture se
        # place relativement à elle. Chaque ligne a donc sa propre unité, ce
        # que la légende dit explicitement.
        def px(v: float) -> float:
            u = (v - lo) / span
            return c.left + 0.10 * c.pw + u * 0.46 * c.pw

        c.add(f'<line class="ba" x1="{px(lo):.1f}" y1="{y:.1f}" '
              f'x2="{px(hi):.1f}" y2="{y:.1f}" stroke-width="3"/>')
        for v in (lo, hi):
            c.add(f'<line class="mark" x1="{px(v):.1f}" y1="{y - 6:.1f}" '
                  f'x2="{px(v):.1f}" y2="{y + 6:.1f}"/>')

        if b.value is None:
            c.add(f'<text class="dl halo" x="{px(hi) + 16:.1f}" y="{y + 3.5:.1f}">'
                  f'aucune rupture</text>')
            note = "∞"
        else:
            raw = px(b.value)
            xb = min(max(raw, c.left + 8), c.left + c.pw - 8)
            c.add(f'<circle class="pt dn" cx="{xb:.1f}" cy="{y:.1f}" r="4.5">'
                  f'<title>rupture à {_num(b.value, 3)}</title></circle>')
            arrow = "←" if raw < c.left + 8 else ("→" if raw > c.left + c.pw - 8 else "")
            if arrow:
                dx = 10 if arrow == "←" else -10
                anch = "start" if arrow == "←" else "end"
                c.add(f'<text class="dl halo" x="{xb + dx:.1f}" y="{y + 3.5:.1f}" '
                      f'text-anchor="{anch}">{arrow}</text>')
            note = f"×{_num(b.factor, 2)}"

        c.add(f'<text class="lg" x="{c.left - 8:.1f}" y="{y + 3.5:.1f}" '
              f'text-anchor="end">{_esc(AXIS_LABELS.get(b.axis, b.axis))}</text>')
        c.add(f'<text class="dl halo" x="{c.left + c.pw + 6:.1f}" y="{y + 3.5:.1f}">'
              f'{note}</text>')

    c.add(f'<text class="lg" x="{c.left + 0.10 * c.pw:.1f}" y="{c.top + 2:.1f}">'
          f'boîte de plausibilité</text>')
    c.add(f'<text class="lg" x="{c.left + c.pw + 6:.1f}" y="{c.top + 2:.1f}">'
          f'facteur</text>')
    c.add(f'<text class="ax" x="{c.left + c.pw / 2:.1f}" y="{c.height - 4:.1f}" '
          f'text-anchor="middle">chaque ligne a son unité ; le point rouge est la rupture</text>')

    return c.render("Points de rupture rapportés à la boîte de plausibilité")


# ---------------------------------------------------------------------------
# 5 — à partir de quand la mesure décide
# ---------------------------------------------------------------------------


def fig_decision_power() -> str:
    """Seuil de sélection déflaté et Sharpe attendu, selon la taille d'échantillon.

    Le point d'intersection est la seule chose qui compte : en deçà, un Sharpe
    mesuré au niveau attendu reste indiscernable du meilleur de trois essais
    sous l'hypothèse nulle. Il fixe l'échantillon minimal du protocole.
    """
    c = Canvas(640, 244, left=58, right=132, top=20, bottom=40)

    o = time_exit_outcome(BAND, HORIZON_MIN, SIGMA_1MIN)
    sr = sharpe_per_trade(EDGE_PTS, FRICTION, SIGMA_1MIN, o.expected_time)

    ns = [100 * 1.06**i for i in range(70)]
    ns = [n for n in ns if n <= 4000]
    curves = [
        (3, "s2", "3 essais"),
        (10, "s3", "10 essais"),
        (100, "s1", "100 essais"),
    ]
    top = max(deflated_threshold_sharpe(100, int(ns[0])), sr) * 1.2

    c.domain(ns[0], ns[-1], 0.0, top, xlog=True)
    c.grid_y([0, 0.05, 0.10, 0.15, 0.20],
             fmt=lambda v: _num(v, 2), label="Sharpe par trade")
    c.ticks_x([100, 200, 500, 1000, 2000, 4000],
              fmt=lambda v: f"{v:,.0f}".replace(",", " "),
              label="nombre de trades mesurés")

    y_sr = c.sy(sr)
    c.add(f'<line class="hl" x1="{c.left:.1f}" y1="{y_sr:.1f}" '
          f'x2="{c.left + c.pw:.1f}" y2="{y_sr:.1f}"/>')
    c.add(f'<text class="dl halo" x="{c.left + 8:.1f}" y="{y_sr - 8:.1f}">'
          f'Sharpe attendu de la dérive documentée — {_num(sr, 3)}</text>')

    for trials, cls, _lab in curves:
        c.path([(n, deflated_threshold_sharpe(trials, int(n))) for n in ns], cls)

    # Intersection à 3 essais : l'échantillon minimal du protocole.
    lo, hi = ns[0], ns[-1]
    for _ in range(80):
        mid = math.sqrt(lo * hi)
        if deflated_threshold_sharpe(3, int(mid)) > sr:
            lo = mid
        else:
            hi = mid
    n_star = math.sqrt(lo * hi)
    c.add(f'<line class="mark" x1="{c.sx(n_star):.1f}" y1="{c.sy(0):.1f}" '
          f'x2="{c.sx(n_star):.1f}" y2="{y_sr:.1f}" stroke-dasharray="3 3"/>')
    c.dot(n_star, sr, "s2", f"croisement à {_num(n_star, 0)} trades")
    c.label(n_star, sr, f"{_num(n_star, 0)} trades", dx=8, dy=14)

    c.add(_legend(c.left + c.pw + 12, c.top + 26, [
        (cls, lab) for _, cls, lab in curves
    ]))
    c.add(f'<text class="lg" x="{c.left + c.pw + 12:.1f}" y="{c.top + 84:.1f}">'
          f'seuil du meilleur</text>')
    c.add(f'<text class="lg" x="{c.left + c.pw + 12:.1f}" y="{c.top + 99:.1f}">'
          f'essai sous H₀</text>')

    return c.render("Seuil de sélection déflaté et Sharpe attendu selon l'échantillon")


FIGURES = {
    "a2exposure": fig_exposure_saturation,
    "a2threshold": fig_threshold_drop,
    "a2friction": fig_friction_tail,
    "a2breaking": fig_breaking_points,
    "a2power": fig_decision_power,
}


def render_all() -> dict[str, str]:
    """Toutes les figures d'ALP-2, prêtes à être injectées dans le gabarit."""
    return {key: fn() for key, fn in FIGURES.items()}
