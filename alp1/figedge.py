"""Figures des trois bornes venues d'ailleurs.

    infceiling  — combien de bits la géométrie exige-t-elle ?
    inforoutes  — trois routes indépendantes, un seul mur
    inffloor    — le plancher de bruit des instruments contre le signal cherché
    discipline  — ce qu'une dérogation coûte au seuil de sélection
"""

from __future__ import annotations

import math

from .costs import deflated_threshold_sharpe
from .discipline import SEALED_BUDGET, breaking_deviations, deviation_cost
from .entropy import null_mutual_information, required_bits, trades_for_information
from .figures import Canvas, _bulle, _esc, _legend, _num, _swatches
from .nonlinear import EMBED, null_permutation
from .report6 import (
    C_OVER_L_V1,
    C_OVER_L_V2,
    N_SESSIONS,
    NULL_DRAWS,
    RR_REF,
    SEALED_SR,
    SEALED_TRADES,
    _edge_bits,
)


# ---------------------------------------------------------------------------
# 1 — le plafond d'information
# ---------------------------------------------------------------------------

def fig_information_ceiling() -> str:
    """Bits requis selon le ratio visé, pour les deux frictions relatives.

    La question tranchée : de combien d'information un signal a-t-il besoin,
    et de combien la géométrie abaisse-t-elle cette exigence ?
    """
    c = Canvas(640, 262, left=62, right=132, top=20, bottom=44)
    rrs = [2.0 + i * 0.5 for i in range(97)]

    def bits(rr: float, cl: float) -> float:
        return max(required_bits(rr, cl).bits, 1e-9)

    lo = min(bits(r, C_OVER_L_V2) for r in rrs)
    hi = max(bits(r, C_OVER_L_V1) for r in rrs)
    c.domain(rrs[0], rrs[-1], lo * 0.75, hi * 1.8, ylog=True)
    c.grid_y([1e-5, 1e-4, 1e-3],
             fmt=lambda v: {1e-6: "10⁻⁶", 1e-5: "10⁻⁵",
                            1e-4: "10⁻⁴", 1e-3: "10⁻³"}[v],
             label="bits par trade requis du signal")
    c.ticks_x([2, 10, 20, 30, 40, 50],
              fmt=lambda v: f"1:{v:.0f}", label="ratio gain/risque visé")

    for cl, cls, nom in ((C_OVER_L_V1, "s2", "ALP-1"),
                         (C_OVER_L_V2, "s1", "ALP-2")):
        c.path([(r, bits(r, cl)) for r in rrs], cls)
        b = bits(RR_REF, cl)
        c.dot(RR_REF, b, cls,
              f"{nom} · 1:{RR_REF:.0f} · {b * 1e6:.1f}×10⁻⁶ bit par trade")

    edge = _edge_bits()
    ye = c.sy(edge)
    c.add(f'<line class="hl" x1="{c.left:.1f}" y1="{ye:.1f}" '
          f'x2="{c.left + c.pw:.1f}" y2="{ye:.1f}"/>')
    c.add(f'<text class="dl halo" x="{c.left + 8:.1f}" y="{ye - 8:.1f}">'
          f'dérive documentée · {_esc(_num(edge * 1e6, 1))}×10⁻⁶</text>')

    c.add(_legend(c.left + c.pw + 12, c.top + 20,
                  [("s2", "ALP-1, c/L = 11,0 %"),
                   ("s1", "ALP-2, c/L = 1,43 %")]))
    f = required_bits(RR_REF, C_OVER_L_V1).bits / required_bits(RR_REF, C_OVER_L_V2).bits
    c.add(f'<text class="lg" x="{c.left + c.pw + 12:.1f}" y="{c.top + 66:.1f}">'
          f'écart {_esc(_num(f, 1))}×</text>')
    return c.render(
        "Information par trade qu'un signal doit porter, selon le ratio visé "
        "et la friction relative de la géométrie")


# ---------------------------------------------------------------------------
# 2 — trois routes, un seul mur
# ---------------------------------------------------------------------------

def fig_three_routes() -> str:
    """Échantillon exigé par trois méthodes sans hypothèse commune."""
    c = Canvas(640, 250, left=196, right=96, top=24, bottom=46)
    bits = _edge_bits()
    routes = [
        ("Seuil de sélection déflaté", 1993.0, "s3"),
        ("Direction · information mutuelle", trades_for_information(bits), "s1"),
        ("Espérance · test t", 17434.0, "s2"),
    ]
    hi = max(v for _, v, _ in routes) * 1.18
    c.domain(0.0, hi, 0.0, float(len(routes)))
    c.ticks_x([0, 5000, 10000, 15000],
              fmt=lambda v: f"{v:,.0f}".replace(",", " "),
              label="trades nécessaires pour décider")

    h = c.ph / len(routes)
    for i, (nom, val, cls) in enumerate(routes):
        y = c.top + i * h + h * 0.24
        w = (val / hi) * c.pw
        c.add(f'<rect class="area ar{ {"s3": 2, "s1": 1, "s2": 3}[cls] }" '
              f'x="{c.left:.1f}" y="{y:.1f}" width="{w:.1f}" '
              f'height="{h * 0.52:.1f}" rx="2">'
              f'<title>{_bulle(nom)} · {val:,.0f} trades</title></rect>')
        c.add(f'<text class="lg" x="{c.left - 8:.1f}" '
              f'y="{y + h * 0.34:.1f}" text-anchor="end">{_esc(nom)}</text>')
        c.add(f'<text class="dl halo" x="{c.left + w + 7:.1f}" '
              f'y="{y + h * 0.34:.1f}">'
              f'{_esc(f"{val:,.0f}".replace(",", chr(8239)))}</text>')

    xh = c.sx(SEALED_TRADES)
    c.add(f'<line class="hl" x1="{xh:.1f}" y1="{c.top:.1f}" '
          f'x2="{xh:.1f}" y2="{c.top + c.ph:.1f}" stroke-dasharray="4 3"/>')
    c.add(f'<text class="dl halo" x="{xh + 7:.1f}" y="{c.top + 12:.1f}">'
          f'protocole scellé · {_esc(f"{SEALED_TRADES:,}".replace(",", chr(8239)))}</text>')
    return c.render(
        "Nombre de trades exigé par trois méthodes ne partageant aucune "
        "hypothèse, comparé à ce que le protocole scellé produit")


# ---------------------------------------------------------------------------
# 3 — le plancher de bruit contre le signal cherché
# ---------------------------------------------------------------------------

def fig_noise_floor() -> str:
    """Le bruit propre de chaque instrument, face à l'information requise."""
    c = Canvas(640, 258, left=214, right=76, top=24, bottom=48)
    besoin = required_bits(RR_REF, C_OVER_L_V2).bits

    barres = []
    for d in EMBED:
        nul = null_permutation(d, n_sessions=N_SESSIONS, draws=NULL_DRAWS)
        barres.append((f"Entropie de permutation, d = {d}",
                       (1.0 - nul.mean) * math.log2(math.factorial(d))))
    barres.append(("Information mutuelle, 1 000 obs.",
                   null_mutual_information(2, 2, 1000, draws=200).mean))

    # Les planchers s'étalent sur deux ordres de grandeur ; une échelle
    # linéaire écraserait les deux premiers contre l'axe.
    lo, hi = besoin * 0.55, max(v for _, v in barres) * 2.2
    c.domain(lo * 1e6, hi * 1e6, 0.0, float(len(barres)), xlog=True)
    c.ticks_x([10, 100, 1000],
              fmt=lambda v: {10: "10", 100: "100", 1000: "1 000"}[v],
              label="bits par trade  (×10⁻⁶), échelle logarithmique")

    # Sur une échelle logarithmique une barre n'a pas d'origine : elle
    # partirait du bord du cadre, qui ne vaut pas zéro. Chaque plancher est
    # donc un point, relié au seuil par un trait — ce qui se lit comme « voici
    # l'exigence, et voilà de combien l'instrument la dépasse ».
    x0 = c.sx(besoin * 1e6)
    h = c.ph / len(barres)
    for i, (nom, val) in enumerate(barres):
        y = c.top + i * h + h * 0.5
        x1 = c.sx(val * 1e6)
        c.add(f'<line class="ln s2" x1="{x0:.1f}" y1="{y:.1f}" '
              f'x2="{x1:.1f}" y2="{y:.1f}" stroke-width="3" '
              f'stroke-linecap="round" opacity="0.34"/>')
        c.add(f'<circle class="pt s2" cx="{x1:.2f}" cy="{y:.2f}" r="5">'
              f'<title>{_bulle(nom + " · plancher " + _num(val * 1e6, 1))}'
              f'×10⁻⁶ bit, {_num(val / besoin, 0)} fois l\'exigence'
              f'</title></circle>')
        c.add(f'<text class="lg" x="{c.left - 8:.1f}" y="{y + 3.5:.1f}" '
              f'text-anchor="end">{_esc(nom)}</text>')
        c.add(f'<text class="dl halo" x="{x1 + 10:.1f}" y="{y + 3.5:.1f}">'
              f'{_esc(_num(val / besoin, 0))}×</text>')

    xb = c.sx(besoin * 1e6)
    c.add(f'<line class="hl" x1="{xb:.1f}" y1="{c.top:.1f}" '
          f'x2="{xb:.1f}" y2="{c.top + c.ph:.1f}"/>')
    c.add(f'<text class="dl halo" x="{xb + 7:.1f}" y="{c.top + 12:.1f}">'
          f'requis par ALP-2</text>')
    return c.render(
        "Plancher de bruit de trois instruments sur une série sans structure, "
        "comparé à l'information que la stratégie exige")


# ---------------------------------------------------------------------------
# 4 — ce qu'une dérogation coûte
# ---------------------------------------------------------------------------

def fig_discipline() -> str:
    """Seuil de sélection selon le nombre de dérogations à la règle scellée."""
    c = Canvas(640, 254, left=58, right=124, top=22, bottom=44)
    ks = [i * 0.25 for i in range(49)]

    def seuil(k: float) -> float:
        # Le nombre de configurations n'est entier que pour k entier ; le
        # tronquer produirait un escalier là où la courbe est continue.
        return deflated_threshold_sharpe(max(2.0, SEALED_BUDGET * 2.0 ** k),
                                         SEALED_TRADES)

    hi = max(seuil(k) for k in ks) * 1.12
    c.domain(0.0, ks[-1], 0.0, hi)
    c.grid_y([0.0, 0.02, 0.04, 0.06], fmt=lambda v: _num(v, 2),
             label="seuil de sélection, Sharpe par trade")
    c.ticks_x([0, 3, 6, 9, 12], fmt=lambda v: _num(v, 0),
              label="dérogations à la règle scellée")

    c.path([(k, seuil(k)) for k in ks], "s2")

    ysr = c.sy(SEALED_SR)
    c.add(f'<line class="hl" x1="{c.left:.1f}" y1="{ysr:.1f}" '
          f'x2="{c.left + c.pw:.1f}" y2="{ysr:.1f}"/>')
    c.add(f'<text class="dl halo" x="{c.left + 8:.1f}" y="{ysr - 8:.1f}">'
          f'Sharpe attendu de la dérive documentée</text>')

    kb = breaking_deviations(SEALED_SR, SEALED_TRADES)
    xb = c.sx(kb)
    c.add(f'<line class="gl" x1="{xb:.1f}" y1="{c.top:.1f}" '
          f'x2="{xb:.1f}" y2="{c.top + c.ph:.1f}" stroke-dasharray="3 3"/>')
    c.dot(kb, SEALED_SR, "s2",
          f"rupture à {kb:.1f} dérogations sur {SEALED_TRADES:,} trades")
    c.add(f'<text class="dl halo" x="{xb + 8:.1f}" y="{c.top + 14:.1f}">'
          f'rupture : {_esc(_num(kb, 1))} dérogations</text>')

    c.add(f'<text class="lg" x="{c.left + c.pw + 10:.1f}" y="{c.top + 22:.1f}">'
          f'soit une tous</text>')
    c.add(f'<text class="lg" x="{c.left + c.pw + 10:.1f}" y="{c.top + 36:.1f}">'
          f'les {_esc(f"{SEALED_TRADES / kb:,.0f}".replace(",", chr(8239)))} trades</text>')
    return c.render(
        "Seuil de sélection déflaté selon le nombre de dérogations à la règle "
        "scellée, sur l'horizon du protocole")


FIGURES = {
    "infceiling": fig_information_ceiling,
    "inforoutes": fig_three_routes,
    "inffloor": fig_noise_floor,
    "discipline": fig_discipline,
}


def render_all() -> dict[str, str]:
    return {k: fn() for k, fn in FIGURES.items()}
