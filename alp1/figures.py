"""Figures du paper, en SVG autonome.

Aucune dépendance, aucun binaire : chaque figure est une chaîne SVG produite
à partir des mêmes fonctions que les tables, de sorte qu'un chiffre du texte
et le point correspondant d'un graphique ne peuvent pas diverger.

Les couleurs ne sont jamais écrites en dur dans les marques : elles passent
par les variables CSS de la feuille de style du document (`--s1`, `--s2`,
`--s3`, `--hm0`…`--hm7`), ce qui rend les figures correctes en thème clair
comme en thème sombre sans duplication.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .barriers import prob_target_before_stop
from .costs import COST_BASE, ES, stop_points
from .horizon import outcome, outcome_scaled
from .stops import TradeGeometry, expectancy_r as managed_expectancy_r, sharpe_per_trade

INDEX_LEVEL = 6000.0
SIGMA_1MIN = 1.25
SESSION_MIN = 390.0
HURST = 0.6489
STOP_PCT = 0.010
FRICTION = COST_BASE.friction_points(ES)


#: Un point décimal encadré de deux chiffres, et rien d'autre.
_POINT_DECIMAL = re.compile(r"(?<=\d)\.(?=\d)")


def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _bulle(texte: str) -> str:
    """Le texte d'une infobulle, échappé **et mis à la française**.

    Une infobulle se compose au fil du code, souvent par une chaîne formatée
    plutôt que par `_num`. Deux mille deux cent huit d'entre elles publiaient
    « 33.3 % » quand l'étiquette dessinée juste à côté publiait « 33,3 % » :
    le même nombre, deux fois, de deux façons, dans un document français.
    Personne ne l'avait vu parce qu'une infobulle ne se lit qu'au survol.

    Corriger deux mille appels aurait été une occasion de plus de les faire
    diverger. La normalisation se fait donc **à l'endroit unique où une
    infobulle est écrite**, et elle ne touche qu'un point encadré de deux
    chiffres — jamais une abréviation, jamais une balise, jamais une
    coordonnée.
    """
    return _esc(_POINT_DECIMAL.sub(",", texte))


def _num(value: float, nd: int = 2) -> str:
    """Nombre à la française : virgule décimale, espace fine pour les milliers."""
    txt = f"{value:,.{nd}f}".replace(",", "\u202f").replace(".", ",")
    return txt


def _hrow(cx: float, cy: float, items: list[tuple[str, str]], step: float = 132.0) -> str:
    """Légende en ligne : pastille de couleur + libellé en encre de texte."""
    out = []
    for i, (cls, text) in enumerate(items):
        x = cx + i * step
        out.append(f'<rect class="{cls}" x="{x:.1f}" y="{cy - 8:.1f}" width="11" height="11" rx="2"/>')
        out.append(f'<text class="lg" x="{x + 17:.1f}" y="{cy + 1:.1f}">{_esc(text)}</text>')
    return "\n".join(out)


@dataclass
class Canvas:
    """Toile SVG minimale : échelles linéaires ou logarithmiques et primitives."""

    width: float
    height: float
    left: float = 46.0
    right: float = 14.0
    top: float = 14.0
    bottom: float = 34.0
    parts: list[str] = field(default_factory=list)

    x0: float = 0.0
    x1: float = 1.0
    y0: float = 0.0
    y1: float = 1.0
    xlog: bool = False
    ylog: bool = False

    def domain(self, x0, x1, y0, y1, xlog=False, ylog=False) -> "Canvas":
        self.x0, self.x1, self.y0, self.y1 = x0, x1, y0, y1
        self.xlog, self.ylog = xlog, ylog
        return self

    @property
    def pw(self) -> float:
        return self.width - self.left - self.right

    @property
    def ph(self) -> float:
        return self.height - self.top - self.bottom

    def sx(self, x: float) -> float:
        if self.xlog:
            u = (math.log(x) - math.log(self.x0)) / (math.log(self.x1) - math.log(self.x0))
        else:
            u = (x - self.x0) / (self.x1 - self.x0)
        return self.left + u * self.pw

    def sy(self, y: float) -> float:
        if self.ylog:
            u = (math.log(y) - math.log(self.y0)) / (math.log(self.y1) - math.log(self.y0))
        else:
            u = (y - self.y0) / (self.y1 - self.y0)
        return self.top + (1.0 - u) * self.ph

    # --- primitives -----------------------------------------------------

    def add(self, markup: str) -> None:
        self.parts.append(markup)

    def grid_y(self, ticks, fmt=lambda v: f"{v:g}", label: str | None = None) -> None:
        for v in ticks:
            y = self.sy(v)
            self.add(f'<line class="gl" x1="{self.left:.1f}" y1="{y:.1f}" '
                     f'x2="{self.left + self.pw:.1f}" y2="{y:.1f}"/>')
            self.add(f'<text class="tk" x="{self.left - 6:.1f}" y="{y + 3:.1f}" '
                     f'text-anchor="end">{_esc(fmt(v))}</text>')
        if label:
            cy = self.top + self.ph / 2
            self.add(f'<text class="ax" transform="translate(11,{cy:.1f}) rotate(-90)" '
                     f'text-anchor="middle">{_esc(label)}</text>')

    def ticks_x(self, ticks, fmt=lambda v: f"{v:g}", label: str | None = None,
                rule: bool = True) -> None:
        base = self.top + self.ph
        if rule:
            self.add(f'<line class="ba" x1="{self.left:.1f}" y1="{base:.1f}" '
                     f'x2="{self.left + self.pw:.1f}" y2="{base:.1f}"/>')
        for v in ticks:
            x = self.sx(v)
            self.add(f'<text class="tk" x="{x:.1f}" y="{base + 14:.1f}" '
                     f'text-anchor="middle">{_esc(fmt(v))}</text>')
        if label:
            self.add(f'<text class="ax" x="{self.left + self.pw / 2:.1f}" '
                     f'y="{self.height - 4:.1f}" text-anchor="middle">{_esc(label)}</text>')

    def in_domain(self, x: float, y: float) -> bool:
        xlo, xhi = sorted((self.x0, self.x1))
        ylo, yhi = sorted((self.y0, self.y1))
        return xlo <= x <= xhi and ylo <= y <= yhi

    def path(self, pts, cls: str, dash: str = "") -> None:
        """Polyligne, découpée aux bords du domaine.

        Sans ce découpage, une courbe qui sort du domaine sort de la planche
        et va se poser sur la légende, sur le titre, ou sur la figure
        suivante. C'est arrivé : la figure 5 traçait deux courbes allant de
        −576 à +475 dans un cadre de 272 points de haut. Le découpage est un
        filet ; il ne dispense pas de donner à la figure un domaine qui
        couvre ses données.
        """
        segments: list[list[tuple[float, float]]] = []
        courant: list[tuple[float, float]] = []
        for x, y in pts:
            if self.in_domain(x, y):
                courant.append((x, y))
            elif courant:
                segments.append(courant)
                courant = []
        if courant:
            segments.append(courant)
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        for seg in segments:
            if len(seg) < 2:
                continue
            d = " ".join(("M" if i == 0 else "L") + f"{self.sx(x):.2f},{self.sy(y):.2f}"
                         for i, (x, y) in enumerate(seg))
            self.add(f'<path class="ln {cls}" d="{d}"{extra}/>')

    def dot(self, x: float, y: float, cls: str, title: str = "") -> None:
        if not self.in_domain(x, y):
            return
        t = f"<title>{_bulle(title)}</title>" if title else ""
        self.add(f'<circle class="pt {cls}" cx="{self.sx(x):.2f}" cy="{self.sy(y):.2f}" '
                 f'r="4">{t}</circle>')

    def label(self, x: float, y: float, text: str, anchor: str = "start",
              dx: float = 6.0, dy: float = 3.0, cls: str = "dl") -> None:
        self.add(f'<text class="{cls}" x="{self.sx(x) + dx:.1f}" y="{self.sy(y) + dy:.1f}" '
                 f'text-anchor="{anchor}">{_esc(text)}</text>')

    def render(self, aria: str) -> str:
        body = "\n".join(self.parts)
        return (f'<svg class="fig" viewBox="0 0 {self.width:g} {self.height:g}" '
                f'role="img" aria-label="{_esc(aria)}" '
                f'preserveAspectRatio="xMidYMid meet">\n{body}\n</svg>')


def _legend(cx: float, cy: float, items: list[tuple[str, str]], gap: float = 15.0) -> str:
    out = []
    for i, (cls, text) in enumerate(items):
        y = cy + i * gap
        out.append(f'<line class="ln {cls}" x1="{cx:.1f}" y1="{y:.1f}" x2="{cx + 14:.1f}" y2="{y:.1f}"/>')
        out.append(f'<text class="lg" x="{cx + 20:.1f}" y="{y + 3.5:.1f}">{_esc(text)}</text>')
    return "\n".join(out)


def _swatches(cx: float, cy: float, items: list[tuple[str, str]], gap: float = 15.0) -> str:
    out = []
    for i, (cls, text) in enumerate(items):
        y = cy + i * gap
        out.append(f'<rect class="{cls}" x="{cx:.1f}" y="{y - 5:.1f}" width="11" height="11" rx="2"/>')
        out.append(f'<text class="lg" x="{cx + 17:.1f}" y="{y + 3.5:.1f}">{_esc(text)}</text>')
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Figure 1 — le plan d'espérance
# ---------------------------------------------------------------------------

def fig_expectancy_plane() -> str:
    """Surface E[R] sur (R:R, niveau de mise à BE), sans drift puis avec drift.

    Sans drift la surface est un plan horizontal situé à −c/L : aucun réglage
    de géométrie ni de gestion ne la déforme. Avec drift elle s'incline, et sa
    pente selon l'axe de la mise à breakeven est positive — plus le stop est
    remonté tard, plus il reste d'espérance.
    """
    rr_grid = [5.0, 10.0, 20.0, 30.0]
    trig = [0.5, 1.0, 2.0, 4.0]           # niveau de mise à BE, en R
    a = stop_points(INDEX_LEVEL, STOP_PCT)
    # Drift d'équilibre de la géométrie 1:20, par l'identité de Wald.
    mu_edge = FRICTION * SIGMA_1MIN**2 / (a * 20.0 * a)

    def surface(mu: float) -> list[list[float]]:
        return [[managed_expectancy_r(TradeGeometry(a, r * a, FRICTION, g * a),
                                      mu, SIGMA_1MIN, mu) for g in trig] for r in rr_grid]

    panels = [("µ = 0", "aucune dérive à l'entrée", surface(0.0)),
              ("µ = 1,5 µ*", "dérive supérieure au seuil d'équilibre", surface(1.5 * mu_edge))]

    # L'échelle de hauteur se déduit des deux surfaces, et elle leur est
    # commune : c'est ce partage qui rend la comparaison légitime. Fixée à
    # −0,13…0,10, elle laissait dehors sept des dix valeurs de maille — de
    # −0,550 à +0,484 — et la projection, qui ne borne pas, les envoyait à
    # quatre hauteurs de cadre au-dessus et au-dessous. La planche montrait
    # des échardes verticales au lieu d'une surface.
    _plat = [v for _, _, z in panels for ligne in z for v in ligne]
    _pas = 0.05
    zlo = _pas * math.floor(min(_plat + [-FRICTION / a, 0.0]) / _pas)
    zhi = _pas * math.ceil(max(_plat + [0.0]) / _pas)
    ni, nj = len(rr_grid), len(trig)
    w, h = 640.0, 286.0
    parts = [f'<svg class="fig" viewBox="0 0 {w:g} {h:g}" role="img" '
             f'aria-label="Surface d espérance par trade selon le ratio gain risque '
             f'et le niveau de mise à breakeven" preserveAspectRatio="xMidYMid meet">']

    for pi, (title, subtitle, z) in enumerate(panels):
        ox, oy = 150.0 + pi * 300.0, 188.0
        cx, cy, cz = 23.0, 12.5, 190.0

        def proj(i: float, j: float, val: float) -> tuple[float, float]:
            # Le bornage est une ceinture : le domaine couvre les données, mais
            # une valeur nouvelle ne doit jamais pouvoir sortir de la planche.
            val = min(max(val, zlo), zhi)
            return (ox + (i - j) * cx, oy + (i + j) * cy - (val - zlo) * cz / (zhi - zlo))

        def poly(points, cls, tip=""):
            t = f"<title>{_bulle(tip)}</title>" if tip else ""
            return (f'<polygon class="{cls}" points="' +
                    " ".join(f"{x:.1f},{y:.1f}" for x, y in points) + f'">{t}</polygon>')

        floor = [proj(0, 0, 0.0), proj(ni - 1, 0, 0.0), proj(ni - 1, nj - 1, 0.0),
                 proj(0, nj - 1, 0.0)]
        parts.append(poly(floor, "floor"))

        # Montants verticaux : ils rendent lisible la hauteur de la surface.
        for (i, j) in ((0, 0), (ni - 1, 0), (ni - 1, nj - 1), (0, nj - 1)):
            fx, fy = proj(i, j, 0.0)
            sxp, syp = proj(i, j, z[i][j])
            parts.append(f'<line class="post" x1="{fx:.1f}" y1="{fy:.1f}" '
                         f'x2="{sxp:.1f}" y2="{syp:.1f}"/>')

        quads = []
        for i in range(ni - 1):
            for j in range(nj - 1):
                corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                pts = [proj(ii, jj, z[ii][jj]) for ii, jj in corners]
                mean = sum(z[ii][jj] for ii, jj in corners) / 4.0
                quads.append((i + j, pts, mean))
        for depth, pts, val in sorted(quads, key=lambda q: -q[0]):
            cls = "up" if val > 1e-9 else ("dn" if val < -1e-9 else "ze")
            parts.append(poly(pts, f"mesh {cls}", f"E[R] = {val:+.3f} R"))

        for k, r in enumerate(rr_grid):
            x, y = proj(k, nj - 1, 0.0)
            parts.append(f'<text class="tk halo" x="{x - 16:.1f}" y="{y + 15:.1f}" '
                         f'text-anchor="end">1:{r:g}</text>')
        for k, g in enumerate(trig):
            if g not in (0.5, 4.0):
                continue
            x, y = proj(ni - 1, k, 0.0)
            parts.append(f'<text class="tk halo" x="{x + 16:.1f}" y="{y + 14:.1f}">BE {g:g} R</text>')

        edge = ox - (nj - 1) * cx
        for val, lab in ((0.0, "0"), (-FRICTION / a, "−c/L")):
            _, yy = proj(0, nj - 1, val)
            parts.append(f'<text class="tk" x="{edge - 46:.1f}" y="{yy + 3:.1f}" '
                         f'text-anchor="end">{_esc(lab)}</text>')
            parts.append(f'<line class="gl" x1="{edge - 41:.1f}" y1="{yy:.1f}" '
                         f'x2="{edge - 28:.1f}" y2="{yy:.1f}"/>')

        parts.append(f'<text class="ax" x="{ox:.1f}" y="16" text-anchor="middle">{_esc(title)}</text>')
        parts.append(f'<text class="lg" x="{ox:.1f}" y="31" text-anchor="middle">{_esc(subtitle)}</text>')

    parts.append(f'<text class="lg" x="{w / 2:.1f}" y="{h - 6:.1f}" text-anchor="middle">'
                 f'axe gauche : ratio gain / risque · axe droit : niveau de mise à breakeven</text>')
    parts.append('</svg>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Figure 2 — carte du ratio d'information requis
# ---------------------------------------------------------------------------

def fig_required_ir_heatmap() -> str:
    """IR requis = c/(σ·√E[τ∧T]) par largeur de stop et ratio gain/risque."""
    stops = [0.005, 0.010, 0.025, 0.050, 0.100, 0.200]
    rrs = [2, 5, 10, 20, 30, 50]
    vals: dict[tuple[int, int], float] = {}
    for i, pct in enumerate(stops):
        a = stop_points(INDEX_LEVEL, pct)
        for j, r in enumerate(rrs):
            o = outcome_scaled(a, r * a, SESSION_MIN, SIGMA_1MIN, HURST)
            vals[(i, j)] = FRICTION / (SIGMA_1MIN * math.sqrt(o.expected_time))

    lo, hi = min(vals.values()), max(vals.values())
    cw, ch = 74.0, 34.0
    left, top = 78.0, 32.0
    w = left + cw * len(rrs) + 16.0
    h = top + ch * len(stops) + 58.0
    parts = [f'<svg class="fig" viewBox="0 0 {w:g} {h:g}" role="img" '
             f'aria-label="Ratio d information requis par largeur de stop et ratio gain risque" '
             f'preserveAspectRatio="xMidYMid meet">']

    for j, r in enumerate(rrs):
        parts.append(f'<text class="tk" x="{left + cw * (j + 0.5):.1f}" y="{top - 10:.1f}" '
                     f'text-anchor="middle">1:{r}</text>')
    for i, pct in enumerate(stops):
        parts.append(f'<text class="tk" x="{left - 8:.1f}" y="{top + ch * (i + 0.5) + 4:.1f}" '
                     f'text-anchor="end">{("%.3f" % pct).replace(".", ",")} %</text>')
        for j, r in enumerate(rrs):
            v = vals[(i, j)]
            u = (math.log(v) - math.log(lo)) / (math.log(hi) - math.log(lo))
            step = min(7, max(0, int(round(u * 7))))
            x, y = left + cw * j, top + ch * i
            bulle = _bulle(f"stop {pct:.3f} % · R:R 1:{r} · "
                           f"IR requis {v:.3f}")
            parts.append(
                f'<rect class="hm hm{step}" x="{x + 1:.1f}" y="{y + 1:.1f}" '
                f'width="{cw - 2:.1f}" height="{ch - 2:.1f}">'
                f'<title>{bulle}</title></rect>')
            ink = "cl-hi" if step >= 4 else "cl-lo"
            parts.append(f'<text class="cell {ink}" x="{x + cw / 2:.1f}" y="{y + ch / 2 + 4:.1f}" '
                         f'text-anchor="middle">{_num(v, 3)}</text>')

    # Cadre du domaine de travail : stop 0,050 %, R:R 1:20 à 1:30.
    i0, j0, j1 = stops.index(0.050), rrs.index(20), rrs.index(30)
    parts.append(f'<rect class="hl" x="{left + cw * j0 + 1:.1f}" y="{top + ch * i0 + 1:.1f}" '
                 f'width="{cw * (j1 - j0 + 1) - 2:.1f}" height="{ch - 2:.1f}"/>')
    parts.append(f'<rect class="hl" x="{left:.1f}" y="{top + ch * len(stops) + 14:.1f}" '
                 f'width="11" height="11"/>')
    parts.append(f'<text class="lg" x="{left + 17:.1f}" y="{top + ch * len(stops) + 23:.1f}">'
                 f'domaine retenu</text>')
    parts.append(f'<text class="ax" x="{left + cw * len(rrs) / 2:.1f}" y="{h - 8:.1f}" '
                 f'text-anchor="middle">ratio gain / risque</text>')
    parts.append(f'<text class="ax" transform="translate(11,{top + ch * len(stops) / 2:.1f}) '
                 f'rotate(-90)" text-anchor="middle">stop (% de l\'indice)</text>')
    parts.append('</svg>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Figure 3 — composition des issues sous contrainte de séance
# ---------------------------------------------------------------------------

def fig_outcome_composition() -> str:
    """P(target), P(stop), P(clôture) en fonction du R:R, sous deux lois d'échelle."""
    a = stop_points(INDEX_LEVEL, STOP_PCT)
    rrs = list(range(2, 51))
    w, h = 640.0, 286.0
    parts = [f'<svg class="fig" viewBox="0 0 {w:g} {h:g}" role="img" '
             f'aria-label="Composition des issues d un trade selon le ratio gain risque" '
             f'preserveAspectRatio="xMidYMid meet">']

    for pi, (hurst, title) in enumerate(((0.5, "H = 0,50 — dispersion en racine du temps"),
                                         (HURST, "H = 0,65 — dispersion calibrée sur la séance"))):
        ox = 40.0 + pi * 312.0
        pw, ph, oy = 250.0, 170.0, 56.0
        def sx(r): return ox + (r - rrs[0]) / (rrs[-1] - rrs[0]) * pw
        def sy(v): return oy + (1.0 - v) * ph

        series = []
        for r in rrs:
            o = outcome_scaled(a, r * a, SESSION_MIN, SIGMA_1MIN, hurst)
            series.append((r, o.p_target, o.p_open, o.p_stop))

        # Empilement : target (bas), clôture, stop — 2 px de blanc entre les aires.
        cum_lo = [0.0] * len(series)
        for key, cls, name in ((1, "ar1", "target"), (2, "ar2", "clôture"), (3, "ar3", "stop")):
            top_line, bottom_line = [], []
            for k, row in enumerate(series):
                lo = cum_lo[k]
                hi = lo + row[key]
                bottom_line.append((row[0], lo))
                top_line.append((row[0], hi))
                cum_lo[k] = hi
            d = " ".join(("M" if i == 0 else "L") + f"{sx(x):.1f},{sy(y):.1f}"
                         for i, (x, y) in enumerate(top_line))
            d += " " + " ".join(f"L{sx(x):.1f},{sy(y):.1f}" for x, y in reversed(bottom_line)) + " Z"
            parts.append(f'<path class="area {cls}" d="{d}"><title>{name}</title></path>')

        for k, r in enumerate((20, 30)):
            parts.append(f'<line class="mark" x1="{sx(r):.1f}" y1="{oy:.1f}" '
                         f'x2="{sx(r):.1f}" y2="{oy + ph:.1f}"/>')
            o = outcome_scaled(a, r * a, SESSION_MIN, SIGMA_1MIN, hurst)
            parts.append(f'<text class="dl" x="{sx(r) + (-4 if k == 0 else 4):.1f}" '
                         f'y="{oy - 6 - 13 * (1 - k):.1f}" '
                         f'text-anchor="{"end" if k == 0 else "start"}">'
                         f'1:{r} → {_num(100 * o.p_target)}\u202f%</text>')

        for v in (0.0, 0.25, 0.5, 0.75, 1.0):
            parts.append(f'<text class="tk" x="{ox - 6:.1f}" y="{sy(v) + 3:.1f}" '
                         f'text-anchor="end">{int(v * 100)}</text>')
        parts.append(f'<line class="ba" x1="{ox:.1f}" y1="{oy + ph:.1f}" '
                     f'x2="{ox + pw:.1f}" y2="{oy + ph:.1f}"/>')
        for r in (2, 10, 20, 30, 40, 50):
            parts.append(f'<text class="tk" x="{sx(r):.1f}" y="{oy + ph + 14:.1f}" '
                         f'text-anchor="middle">1:{r}</text>')
        parts.append(f'<text class="ax" x="{ox + pw / 2:.1f}" y="{oy - 33:.1f}" '
                     f'text-anchor="middle">{_esc(title)}</text>')
        if pi == 0:
            parts.append(f'<text class="ax" transform="translate(13,{oy + ph / 2:.1f}) '
                         f'rotate(-90)" text-anchor="middle">part des trades (%)</text>')
        parts.append(f'<text class="ax" x="{ox + pw / 2:.1f}" y="{h - 20:.1f}" '
                     f'text-anchor="middle">ratio gain / risque</text>')

    parts.append(_hrow(52.0, h - 6.0, [("area ar1", "target atteint"),
                                       ("area ar2", "clôture de séance"),
                                       ("area ar3", "stop touché")], step=178.0))
    parts.append('</svg>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Figure 4 — exposition au drift
# ---------------------------------------------------------------------------

def fig_exposure_curve() -> str:
    """Durée moyenne d'exposition E[τ∧T] en fonction du ratio gain/risque.

    C'est la seule grandeur par laquelle la géométrie agit sur l'espérance :
    E[X] = µ·E[τ∧T]. La courbe sature — au-delà d'un certain éloignement du
    target, la séance se referme avant lui et l'exposition n'augmente plus.
    """
    a = stop_points(INDEX_LEVEL, STOP_PCT)
    rrs = [2 + i for i in range(49)]
    c = Canvas(640, 268, left=52, right=112, top=22, bottom=40).domain(2, 50, 0, 80)
    c.add(f'<rect class="band" x="{c.sx(20):.1f}" y="{c.top:.1f}" '
          f'width="{c.sx(30) - c.sx(20):.1f}" height="{c.ph:.1f}"/>')
    c.grid_y([0, 20, 40, 60, 80], lambda v: f"{v:g}", "exposition moyenne (min)")
    c.ticks_x([2, 10, 20, 30, 40, 50], lambda v: f"1:{v:g}", "ratio gain / risque")

    for hurst, cls, name in ((0.5, "s2", "H = 0,50"), (HURST, "s1", "H = 0,65")):
        pts = []
        for r in rrs:
            o = outcome_scaled(a, r * a, SESSION_MIN, SIGMA_1MIN, hurst)
            pts.append((r, o.expected_time))
        c.path(pts, cls)
        c.dot(pts[-1][0], pts[-1][1], cls, f"{name} · {pts[-1][1]:.1f} min")
        c.label(50, pts[-1][1], f"{name}", dx=9, dy=3)

    for hurst, cls in ((0.5, "s2"), (HURST, "s1")):
        for r in (20, 30):
            o = outcome_scaled(a, r * a, SESSION_MIN, SIGMA_1MIN, hurst)
            c.dot(r, o.expected_time, cls,
                  f"1:{r} · {o.expected_time:.1f} min · µ* = {FRICTION / o.expected_time:.4f} pt/min")
    o20 = outcome_scaled(a, 20 * a, SESSION_MIN, SIGMA_1MIN, HURST)
    c.label(20, o20.expected_time, f"1:20 — {_num(o20.expected_time, 1)} min", dx=-6, dy=-9,
            anchor="end")
    c.add(f'<text class="lg" x="{c.sx(25):.1f}" y="{c.top + 12:.1f}" '
          f'text-anchor="middle">domaine retenu</text>')
    return c.render("Exposition moyenne au marché selon le ratio gain risque")


# ---------------------------------------------------------------------------
# Figure 5 — coût de la mise à breakeven
# ---------------------------------------------------------------------------

def fig_be_cost() -> str:
    """Coût en R de la remontée du stop selon la dérive post-confirmation."""
    from .barriers import required_drift
    from .stops import be_expectancy_cost_r

    a = stop_points(INDEX_LEVEL, STOP_PCT)
    b = 20.0 * a
    mu_eq = required_drift(a, b, SIGMA_1MIN, FRICTION)
    # Le domaine en ordonnée se déduit des deux courbes. Fixé à −0,06…0,18, il
    # n'en montrait qu'un ruban : elles vont de −0,34 à +0,86, et le tracé,
    # qui ne se découpait pas alors, sortait de la planche par le haut et par
    # le bas jusqu'à recouvrir la légende et le libellé d'abscisse.
    def _cout(trig: float, k: float) -> float:
        return be_expectancy_cost_r(TradeGeometry(a, b, FRICTION, trig * a),
                                    mu_eq, SIGMA_1MIN, k * mu_eq)

    _ks = [-2.0 + 5.0 * i / 100.0 for i in range(101)]
    _plat = [_cout(t, k) for t in (1.0, 4.0) for k in _ks]
    _pas = 0.1
    _y0 = _pas * math.floor(min(_plat) / _pas)
    _y1 = _pas * math.ceil(max(_plat) / _pas)
    c = Canvas(640, 272, left=58, right=72, top=20, bottom=42).domain(-2, 3, _y0, _y1)

    c.add(f'<rect class="band" x="{c.sx(-2):.1f}" y="{c.top:.1f}" '
          f'width="{c.sx(0) - c.sx(-2):.1f}" height="{c.ph:.1f}"/>')
    # Une graduation tous les deux dixièmes : au pas du domaine, quatorze
    # filets se serraient sur deux cent dix points de haut.
    c.grid_y([0.2 * k for k in range(math.ceil(_y0 / 0.2), math.floor(_y1 / 0.2) + 1)],
             lambda v: _num(v, 2), "coût de la règle (R)")
    c.ticks_x([-2, -1, 0, 1, 2, 3], lambda v: f"{v:g}",
              "dérive post-confirmation µ₂, en multiples de la dérive d'équilibre")
    c.add(f'<line class="zero" x1="{c.left:.1f}" y1="{c.sy(0):.1f}" '
          f'x2="{c.left + c.pw:.1f}" y2="{c.sy(0):.1f}"/>')
    c.add(f'<line class="zero" x1="{c.sx(0):.1f}" y1="{c.top:.1f}" '
          f'x2="{c.sx(0):.1f}" y2="{c.top + c.ph:.1f}"/>')

    for trig, cls, name in ((1.0, "s1", "BE à +1 R"), (4.0, "s3", "BE à +4 R")):
        pts = [(k, _cout(trig, k)) for k in _ks]
        c.path(pts, cls)
        c.dot(3.0, pts[-1][1], cls, f"{name} · coût {pts[-1][1]:+.3f} R")
        c.label(3.0, pts[-1][1], name, dx=9, dy=3)

    c.dot(0.0, 0.0, "s1", "µ₂ = 0 : la règle est exactement neutre")
    c.label(0.0, 0.0, "neutralité", dx=10, dy=16)
    c.add(f'<text class="lg" x="{c.sx(-1):.1f}" y="{c.top + 13:.1f}" '
          f'text-anchor="middle">règle payante</text>')
    c.add(f'<text class="lg" x="{c.sx(1.5):.1f}" y="{c.top + 13:.1f}" '
          f'text-anchor="middle">règle coûteuse</text>')
    return c.render("Coût en R de la remontée du stop selon la dérive postérieure à la confirmation")


# ---------------------------------------------------------------------------
# Figure 6 — horizon de validation
# ---------------------------------------------------------------------------

def fig_sample_size() -> str:
    """Trades requis pour un t-statistique de 2, selon la dérive réellement captée."""
    a = stop_points(INDEX_LEVEL, STOP_PCT)
    geoms = [(5, "s3", 1.0e5), (20, "s1", 4.0e3), (30, "s2", 6.0e4)]
    data = {r: outcome_scaled(a, r * a, SESSION_MIN, SIGMA_1MIN, HURST) for r, _, _ in geoms}

    c = Canvas(640, 286, left=62, right=108, top=20, bottom=44).domain(
        0.6, 3.2, 3e2, 3e6, ylog=True)
    c.grid_y([1e3, 1e4, 1e5, 1e6],
             lambda v: {1e3: "1 000", 1e4: "10 000", 1e5: "100 000", 1e6: "1 000 000"}[v],
             "trades requis pour t = 2")
    c.ticks_x([0.6, 1.0, 1.5, 2.0, 2.5, 3.0], lambda v: _num(v, 1),
              "dérive captée à l'entrée (points d'indice par heure)")

    for r, cls, anchor in geoms:
        o = data[r]
        pts = []
        for i in range(241):
            mu_h = 0.6 + 2.6 * i / 240.0
            mu = mu_h / 60.0
            e = (mu * o.expected_time - FRICTION) / a
            sr = e / (o.sd_gross / a)
            if sr <= 0:
                continue
            n = (2.0 / sr) ** 2
            if n <= 3e6:
                pts.append((mu_h, n))
        if pts:
            c.path(pts, cls)
            c.dot(pts[-1][0], pts[-1][1], cls, f"1:{r} · {pts[-1][1]:,.0f} trades")
            anchor_pt = min(pts, key=lambda q: abs(q[1] - anchor))
            c.label(anchor_pt[0], anchor_pt[1], f"1:{r}", dx=9, dy=-6)

    # Les trois seuils d'équilibre tombent à droite du cadre — 6,4, 8,2 et
    # 20,3 points par heure contre un domaine qui s'arrête à 3,2. Les traits
    # étaient tout de même émis, à quelques milliers de points hors de la
    # planche, et la légende annonçait des traits verticaux que le lecteur ne
    # pouvait pas voir. Ce n'est pas un détail de rendu : que le domaine
    # entier de la figure soit sous le seuil d'équilibre est le fait que la
    # figure doit énoncer.
    dedans, dehors = [], []
    for r, cls, _ in geoms:
        mu_star_h = FRICTION / data[r].expected_time * 60.0
        if c.x0 <= mu_star_h <= c.x1:
            dedans.append(mu_star_h)
            c.add(f'<line class="mark" x1="{c.sx(mu_star_h):.1f}" y1="{c.top:.1f}" '
                  f'x2="{c.sx(mu_star_h):.1f}" y2="{c.top + c.ph:.1f}"/>')
        else:
            dehors.append((r, mu_star_h))
    if dedans:
        note = "traits verticaux : seuils d'équilibre µ*"
    else:
        note = ("seuils d'équilibre µ* tous hors cadre : "
                + " · ".join(f"1:{r} à {_num(m, 1)}" for r, m in dehors)
                + " pt/h")
    c.add(f'<text class="lg" x="{c.sx(3.15):.1f}" y="{c.top + 13:.1f}" '
          f'text-anchor="end">{_esc(note)}</text>')

    # Repère de faisabilité : 2 trades par séance pendant deux ans.
    c.add(f'<line class="zero" x1="{c.left:.1f}" y1="{c.sy(1000):.1f}" '
          f'x2="{c.left + c.pw:.1f}" y2="{c.sy(1000):.1f}"/>')
    c.add(f'<text class="lg" x="{c.left + 6:.1f}" y="{c.sy(1000) - 6:.1f}">'
          f'2 trades / séance pendant 2 ans</text>')
    return c.render("Nombre de trades requis pour démontrer un edge selon la dérive captée")


ALL_FIGURES = {
    "plan": fig_expectancy_plane,
    "ir": fig_required_ir_heatmap,
    "issues": fig_outcome_composition,
    "exposition": fig_exposure_curve,
    "be": fig_be_cost,
    "echantillon": fig_sample_size,
}


def render_all() -> dict[str, str]:
    """Toutes les figures, prêtes à être insérées dans le document."""
    return {name: fn() for name, fn in ALL_FIGURES.items()}
