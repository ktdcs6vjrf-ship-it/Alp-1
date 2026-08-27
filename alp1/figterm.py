"""Figures des couches d'ALP-1, en panneaux de terminal.

Même contrat que `alp1.figures` : chaque figure est une chaîne SVG produite par
les fonctions du noyau, sans dépendance ni binaire, et sans couleur écrite en
dur — tout passe par les jetons CSS du document, de sorte que les deux thèmes
sont corrects sans duplication.

La différence est de mise en page. Les figures de ce module suivent la
convention des terminaux financiers : plusieurs cadres sur une même planche,
un intitulé et une lecture chiffrée en tête de chaque cadre, une grille
discrète, des étiquettes de niveau posées directement sur les traits. Cette
densité n'est pas décorative — elle permet de mettre côte à côte la grandeur
observée et la conséquence qu'elle a sur le trade, ce que deux figures
séparées ne font jamais aussi bien.

Les trajectoires de prix qui apparaissent dans certaines planches sont des
**simulations déterministes** produites par le générateur reproductible
ci-dessous. Aucune donnée de marché n'entre dans ce dépôt ; elles servent de
support de lecture aux grandeurs calculées, jamais de preuve.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import dow, fib, gex, orderflow, vprofile
from .barriers import prob_touch_single_barrier
from .costs import COST_BASE, ES, stop_points
from .horizon import outcome_scaled

INDEX_LEVEL = 6000.0
SIGMA_1MIN = 1.25
SESSION_MIN = 390.0
HURST = 0.6489
STOP_PCT = 0.010
STOP_PTS = stop_points(INDEX_LEVEL, STOP_PCT)
FRICTION = COST_BASE.friction_points(ES)
ADV_USD = 4.0e11          # volume quotidien du complexe indiciel, ordre de grandeur


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _num(value: float, nd: int = 2) -> str:
    return f"{value:,.{nd}f}".replace(",", " ").replace(".", ",")


def _signed(value: float, nd: int = 2) -> str:
    return ("+" if value >= 0 else "−") + _num(abs(value), nd)


class _Noise:
    """Générateur gaussien déterministe : mêmes figures à chaque exécution.

    Congruence linéaire de Lehmer puis transformation de Box-Muller. Le but
    n'est pas la qualité statistique — c'est la reproductibilité d'une
    illustration, propriété qu'un générateur ensemencé par l'horloge n'aurait
    pas.
    """

    def __init__(self, seed: int = 20260820) -> None:
        self._s = seed % 2147483647 or 1
        self._spare: float | None = None

    def _uniform(self) -> float:
        self._s = (self._s * 48271) % 2147483647
        return self._s / 2147483647.0

    def gauss(self) -> float:
        if self._spare is not None:
            out, self._spare = self._spare, None
            return out
        u1 = max(self._uniform(), 1e-12)
        u2 = self._uniform()
        r = math.sqrt(-2.0 * math.log(u1))
        self._spare = r * math.sin(2.0 * math.pi * u2)
        return r * math.cos(2.0 * math.pi * u2)


# --- Planche et panneaux ------------------------------------------------------


@dataclass
class Board:
    """Planche SVG : une ou plusieurs cadres, un seul système de coordonnées."""

    width: float
    height: float
    parts: list[str] = field(default_factory=list)

    def add(self, markup: str) -> None:
        self.parts.append(markup)

    def caption(self, x: float, y: float, text: str, anchor: str = "middle") -> None:
        self.add(f'<text class="lg" x="{x:.1f}" y="{y:.1f}" '
                 f'text-anchor="{anchor}">{_esc(text)}</text>')

    def legend(self, x: float, y: float, items: list[tuple[str, str]],
               step: float = 132.0, kind: str = "swatch") -> None:
        for i, (cls, text) in enumerate(items):
            cx = x + i * step
            if kind == "line":
                self.add(f'<line class="ln {cls}" x1="{cx:.1f}" y1="{y:.1f}" '
                         f'x2="{cx + 14:.1f}" y2="{y:.1f}"/>')
                off = 20.0
            else:
                self.add(f'<rect class="{cls}" x="{cx:.1f}" y="{y - 5.5:.1f}" '
                         f'width="11" height="11" rx="2"/>')
                off = 17.0
            self.add(f'<text class="lg" x="{cx + off:.1f}" y="{y + 3.5:.1f}">'
                     f'{_esc(text)}</text>')

    def render(self, aria: str) -> str:
        body = "\n".join(self.parts)
        return (f'<svg class="fig" viewBox="0 0 {self.width:g} {self.height:g}" '
                f'role="img" aria-label="{_esc(aria)}" '
                f'preserveAspectRatio="xMidYMid meet">\n{body}\n</svg>')


@dataclass
class Panel:
    """Un cadre de la planche : en-tête, zone de tracé, échelles propres."""

    board: Board
    x: float
    y: float
    w: float
    h: float
    title: str = ""
    readout: str = ""

    x0: float = 0.0
    x1: float = 1.0
    y0: float = 0.0
    y1: float = 1.0
    xlog: bool = False
    ylog: bool = False

    def __post_init__(self) -> None:
        if not self.title:
            return
        # Intitulé à gauche, lecture chiffrée à droite ; si les deux ne tiennent
        # pas sur la largeur du cadre, la lecture passe sur la ligne du dessus.
        title_w = 8.3 * len(self.title)
        read_w = 5.9 * len(self.readout)
        stacked = bool(self.readout) and title_w + read_w + 14.0 > self.w
        base = self.y - 12.0
        self.board.add(f'<text class="hdr" x="{self.x:.1f}" y="{base:.1f}">'
                       f'{_esc(self.title)}</text>')
        if self.readout:
            ry = base - 13.0 if stacked else base
            self.board.add(
                f'<text class="{"sub" if stacked else "read"}" '
                f'x="{self.x + self.w:.1f}" y="{ry:.1f}" '
                f'text-anchor="end">{_esc(self.readout)}</text>')
        self.board.add(f'<line class="hsep" x1="{self.x:.1f}" y1="{self.y - 6:.1f}" '
                       f'x2="{self.x + self.w:.1f}" y2="{self.y - 6:.1f}"/>')

    # --- échelles ---------------------------------------------------------

    def domain(self, x0, x1, y0, y1, xlog=False, ylog=False) -> "Panel":
        self.x0, self.x1, self.y0, self.y1 = x0, x1, y0, y1
        self.xlog, self.ylog = xlog, ylog
        return self

    def sx(self, v: float) -> float:
        if self.xlog:
            u = (math.log(v) - math.log(self.x0)) / (math.log(self.x1) - math.log(self.x0))
        else:
            u = (v - self.x0) / (self.x1 - self.x0)
        return self.x + u * self.w

    def sy(self, v: float) -> float:
        if self.ylog:
            u = (math.log(v) - math.log(self.y0)) / (math.log(self.y1) - math.log(self.y0))
        else:
            u = (v - self.y0) / (self.y1 - self.y0)
        return self.y + (1.0 - u) * self.h

    # --- décor ------------------------------------------------------------

    def frame(self) -> None:
        self.board.add(f'<rect class="frame" x="{self.x:.1f}" y="{self.y:.1f}" '
                       f'width="{self.w:.1f}" height="{self.h:.1f}"/>')

    def grid_y(self, ticks, fmt=lambda v: f"{v:g}", label: str | None = None,
               side: str = "left") -> None:
        for v in ticks:
            yy = self.sy(v)
            self.board.add(f'<line class="gl" x1="{self.x:.1f}" y1="{yy:.1f}" '
                           f'x2="{self.x + self.w:.1f}" y2="{yy:.1f}"/>')
            if side == "left":
                self.board.add(f'<text class="tk" x="{self.x - 5:.1f}" y="{yy + 3:.1f}" '
                               f'text-anchor="end">{_esc(fmt(v))}</text>')
            else:
                self.board.add(f'<text class="tk" x="{self.x + self.w + 5:.1f}" '
                               f'y="{yy + 3:.1f}">{_esc(fmt(v))}</text>')
        if label:
            cy = self.y + self.h / 2
            dx = self.x - 34 if side == "left" else self.x + self.w + 32
            self.board.add(f'<text class="ax" transform="translate({dx:.1f},{cy:.1f}) '
                           f'rotate(-90)" text-anchor="middle">{_esc(label)}</text>')

    def grid_x(self, ticks, fmt=lambda v: f"{v:g}", label: str | None = None,
               rules: bool = False) -> None:
        base = self.y + self.h
        for v in ticks:
            xx = self.sx(v)
            if rules:
                self.board.add(f'<line class="gl" x1="{xx:.1f}" y1="{self.y:.1f}" '
                               f'x2="{xx:.1f}" y2="{base:.1f}"/>')
            self.board.add(f'<text class="tk" x="{xx:.1f}" y="{base + 13:.1f}" '
                           f'text-anchor="middle">{_esc(fmt(v))}</text>')
        self.board.add(f'<line class="ba" x1="{self.x:.1f}" y1="{base:.1f}" '
                       f'x2="{self.x + self.w:.1f}" y2="{base:.1f}"/>')
        if label:
            self.board.add(f'<text class="ax" x="{self.x + self.w / 2:.1f}" '
                           f'y="{base + 28:.1f}" text-anchor="middle">{_esc(label)}</text>')

    # --- marques ----------------------------------------------------------

    def _in_domain(self, x: float, y: float) -> bool:
        xlo, xhi = sorted((self.x0, self.x1))
        ylo, yhi = sorted((self.y0, self.y1))
        return xlo <= x <= xhi and ylo <= y <= yhi

    def path(self, pts, cls: str, dash: str = "", tip: str = "") -> None:
        """Polyligne, découpée aux bords du cadre.

        Le découpage évite le défaut le plus visible d'une planche à plusieurs
        cadres : une courbe qui sort de son domaine et vient se superposer au
        cadre voisin ou à la légende.
        """
        segments: list[list[tuple[float, float]]] = []
        current: list[tuple[float, float]] = []
        for x, y in pts:
            if self._in_domain(x, y):
                current.append((x, y))
            elif current:
                segments.append(current)
                current = []
        if current:
            segments.append(current)
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        t = f"<title>{_esc(tip)}</title>" if tip else ""
        for seg in segments:
            if len(seg) < 2:
                continue
            d = " ".join(("M" if i == 0 else "L") + f"{self.sx(x):.2f},{self.sy(y):.2f}"
                         for i, (x, y) in enumerate(seg))
            self.board.add(f'<path class="ln {cls}" d="{d}"{extra}>{t}</path>')

    def area(self, pts_top, baseline: float, cls: str, tip: str = "") -> None:
        if not pts_top:
            return
        d = " ".join(("M" if i == 0 else "L") + f"{self.sx(x):.2f},{self.sy(y):.2f}"
                     for i, (x, y) in enumerate(pts_top))
        d += (f" L{self.sx(pts_top[-1][0]):.2f},{self.sy(baseline):.2f}"
              f" L{self.sx(pts_top[0][0]):.2f},{self.sy(baseline):.2f} Z")
        t = f"<title>{_esc(tip)}</title>" if tip else ""
        self.board.add(f'<path class="{cls}" d="{d}">{t}</path>')

    def hbar(self, y_center: float, x_from: float, x_to: float, thickness: float,
             cls: str, tip: str = "") -> None:
        """Barre horizontale : les profils de prix se lisent verticalement."""
        xa, xb = sorted((self.sx(x_from), self.sx(x_to)))
        yy = self.sy(y_center) - thickness / 2.0
        t = f"<title>{_esc(tip)}</title>" if tip else ""
        self.board.add(f'<rect class="{cls}" x="{xa:.2f}" y="{yy:.2f}" '
                       f'width="{max(xb - xa, 0.4):.2f}" height="{thickness:.2f}">{t}</rect>')

    def vbar(self, x_center: float, y_from: float, y_to: float, thickness: float,
             cls: str, tip: str = "") -> None:
        ya, yb = sorted((self.sy(y_from), self.sy(y_to)))
        xx = self.sx(x_center) - thickness / 2.0
        t = f"<title>{_esc(tip)}</title>" if tip else ""
        self.board.add(f'<rect class="{cls}" x="{xx:.2f}" y="{ya:.2f}" '
                       f'width="{thickness:.2f}" height="{max(yb - ya, 0.4):.2f}">{t}</rect>')

    def band_y(self, lo: float, hi: float, cls: str = "wash") -> None:
        ya, yb = sorted((self.sy(lo), self.sy(hi)))
        self.board.add(f'<rect class="{cls}" x="{self.x:.1f}" y="{ya:.1f}" '
                       f'width="{self.w:.1f}" height="{yb - ya:.1f}"/>')

    def band_x(self, lo: float, hi: float, cls: str = "wash") -> None:
        xa, xb = sorted((self.sx(lo), self.sx(hi)))
        self.board.add(f'<rect class="{cls}" x="{xa:.1f}" y="{self.y:.1f}" '
                       f'width="{xb - xa:.1f}" height="{self.h:.1f}"/>')

    def hline(self, y: float, cls: str = "lvl") -> None:
        yy = self.sy(y)
        self.board.add(f'<line class="{cls}" x1="{self.x:.1f}" y1="{yy:.1f}" '
                       f'x2="{self.x + self.w:.1f}" y2="{yy:.1f}"/>')

    def vline(self, x: float, cls: str = "lvl") -> None:
        xx = self.sx(x)
        self.board.add(f'<line class="{cls}" x1="{xx:.1f}" y1="{self.y:.1f}" '
                       f'x2="{xx:.1f}" y2="{self.y + self.h:.1f}"/>')

    def dot(self, x: float, y: float, cls: str, tip: str = "", r: float = 4.0) -> None:
        t = f"<title>{_esc(tip)}</title>" if tip else ""
        self.board.add(f'<circle class="pt {cls}" cx="{self.sx(x):.2f}" '
                       f'cy="{self.sy(y):.2f}" r="{r:g}">{t}</circle>')

    def label(self, x: float, y: float, text: str, dx: float = 6.0, dy: float = 3.0,
              anchor: str = "start", cls: str = "dl halo") -> None:
        self.board.add(f'<text class="{cls}" x="{self.sx(x) + dx:.1f}" '
                       f'y="{self.sy(y) + dy:.1f}" text-anchor="{anchor}">{_esc(text)}</text>')

    def tag(self, y: float, text: str, side: str = "right") -> None:
        """Étiquette encadrée posée sur un niveau, à la manière d'un terminal."""
        width = 6.0 * len(text) + 10.0
        yy = self.sy(y)
        xx = self.x + self.w - width - 2 if side == "right" else self.x + 2
        self.board.add(f'<rect class="tag" x="{xx:.1f}" y="{yy - 7:.1f}" '
                       f'width="{width:.1f}" height="14" rx="2"/>')
        self.board.add(f'<text class="tagtx" x="{xx + width / 2:.1f}" y="{yy + 3.5:.1f}" '
                       f'text-anchor="middle">{_esc(text)}</text>')


# ---------------------------------------------------------------------------
# Les niveaux de gamma : 0GW, CR, PS, HVL
# ---------------------------------------------------------------------------

def fig_gex_levels() -> str:
    """Trois lectures d'une même chaîne 0DTE, sur un axe de prix commun.

    À gauche la concentration potentielle par strike — celle qui nomme les
    murs. Au centre le gamma net réellement porté au spot du jour, qui n'a ni
    la même forme ni le même classement. À droite le profil ``GEX(S)``, dont
    le passage par zéro définit le HVL.
    """
    chain = gex.reference_chain()
    spot = INDEX_LEVEL
    lv = gex.levels(chain, spot)
    lo, hi = 5890.0, 6110.0

    b = Board(640, 348)
    price_ticks = [5900, 5925, 5950, 5975, 6000, 6025, 6050, 6075, 6100]

    pot = {k: v / 1e9 for k, v in chain.potential_notional_by_strike().items()
           if lo <= k <= hi}
    net = {k: v / 1e9 for k, v in chain.gex_by_strike(spot).items() if lo <= k <= hi}
    pmax = max(pot.values())
    nlo, nhi = min(net.values()), max(net.values())

    tags = {lv.gamma_wall: "0GW", lv.cr1: "CR1", lv.cr2: "CR2",
            lv.ps1: "PS1", lv.ps2: "PS2"}

    # --- P1 : concentration potentielle, le classement qui nomme les murs ---
    p1 = Panel(b, 54, 46, 168, 232,
               title="Concentration", readout="milliards $ / 1 %")
    p1.domain(0.0, pmax * 1.55, lo, hi)
    p1.frame()
    p1.grid_y(price_ticks, lambda v: f"{v:g}")
    p1.grid_x([0, 5, 10, 15], lambda v: f"{v:g}")
    p1.hline(spot, "lvl strong")
    for k, v in pot.items():
        p1.hbar(k, 0.0, v, 7.0, "up", f"strike {k:g} · concentration {v:.1f} Md$ / 1 %")
    for level, name in tags.items():
        if level is not None:
            p1.tag(level, name)

    # --- P2 : gamma net au spot, diverging ---------------------------------
    p2 = Panel(b, 246, 46, 168, 232,
               title="Gamma net au spot", readout="Md$ / 1 %")
    p2.domain(min(nlo * 1.25, -1.5), nhi * 1.18, lo, hi)
    p2.frame()
    p2.grid_y(price_ticks, lambda v: "")
    p2.grid_x([0, 3, 6, 9], lambda v: f"{v:g}")
    p2.vline(0.0, "zero")
    p2.hline(spot, "lvl strong")
    for k, v in net.items():
        p2.hbar(k, 0.0, v, 7.0, "up" if v >= 0 else "dn",
                f"strike {k:g} · gamma net {v:+.2f} Md$ / 1 %")
    p2.label(nhi * 1.18, spot, "spot", dx=-4, dy=-6, anchor="end", cls="dl halo")

    # --- P3 : profil GEX(S) et passage par zéro ----------------------------
    prof = [(v / 1e9, s) for s, v in chain.profile(lo, hi, 161)]
    xs = [x for x, _ in prof]
    p3 = Panel(b, 438, 46, 168, 232,
               title="Profil GEX(S)", readout=f"HVL {_num(lv.hvl or 0, 0)}")
    p3.domain(min(xs) * 1.15, max(xs) * 1.25, lo, hi)
    p3.frame()
    p3.grid_y(price_ticks, lambda v: f"{v:g}", side="right")
    p3.grid_x([-20, -10, 0, 10, 20], lambda v: f"{v:g}")
    p3.vline(0.0, "zero")
    if lv.hvl is not None:
        p3.band_y(lv.hvl, hi, "wash")
    p3.path(prof, "s1")
    if lv.hvl is not None:
        p3.hline(lv.hvl, "lvl")
        p3.tag(lv.hvl, f"HVL {_num(lv.hvl, 0)}", side="left")
        p3.label(max(xs) * 1.25, (lv.hvl + hi) / 2, "Γ > 0", dx=-11, dy=0,
                 anchor="end", cls="lg halo")
        p3.label(max(xs) * 1.25, (lo + lv.hvl) / 2, "Γ < 0", dx=-11, dy=0,
                 anchor="end", cls="lg halo")
    p3.hline(spot, "lvl strong")
    p3.dot(chain.gex(spot) / 1e9, spot, "s1",
           f"spot {spot:g} · GEX net {chain.gex(spot) / 1e9:+.1f} Md$ / 1 %")

    b.caption(320, 320, "concentration potentielle : chaque strike évalué à la monnaie · "
                        "gamma net : la chaîne évaluée au spot du jour")
    b.caption(320, 336, "chaîne 0DTE synthétique — aucune donnée de marché")
    return b.render("Niveaux de gamma d une chaîne 0DTE : murs, résistances, "
                    "supports et niveau de bascule")


# ---------------------------------------------------------------------------
# Du gamma à la loi d'échelle, et de la loi d'échelle au target
# ---------------------------------------------------------------------------

def fig_gamma_feedback() -> str:
    """La chaîne causale complète : Γ → λΓ → ρ → H → P(target).

    Le panneau de gauche montre l'exposant d'échelle qu'un niveau de gamma peut
    produire ; le domaine grisé est celui des GEX plausibles sur un indice. Le
    panneau de droite montre ce que l'exposant décide : l'atteignabilité des
    targets à 1:20 et 1:30.
    """
    b = Board(640, 320)

    # --- P1 : H(GEX) -------------------------------------------------------
    p1 = Panel(b, 58, 46, 240, 208, title="Exposant impliqué par le gamma",
               readout="H = ½ + ln κ / ln T")
    p1.domain(-2.0e11, 1.0e11, 0.46, 0.70)
    p1.frame()
    p1.grid_y([0.50, 0.55, 0.60, 0.65, 0.70], lambda v: _num(v, 2),
              "exposant d'échelle H")
    p1.grid_x([-2e11, -1e11, 0, 1e11], lambda v: f"{v / 1e11:g}",
              "GEX net (centaines de milliards $ / 1 %)")
    p1.band_x(-6.0e10, 6.0e10, "wash")

    pts = []
    for i in range(241):
        g = -2.0e11 + 3.0e11 * i / 240.0
        k = gex.gamma_feedback_coefficient(g, ADV_USD)
        if k <= -0.499:
            continue
        pts.append((g, gex.hurst_from_feedback(k, SESSION_MIN)))
    p1.path(pts, "s1")
    p1.hline(0.5, "lvl")
    p1.label(1.0e11, 0.5, "H = ½", dx=-4, dy=-5, anchor="end", cls="lg halo")
    p1.hline(HURST, "lvl")
    req = gex.required_gex_for_hurst(HURST, ADV_USD, horizon_min=SESSION_MIN)
    p1.label(-2.0e11, HURST, f"H calibré = {_num(HURST, 3)}", dx=5, dy=-6, cls="dl halo")
    p1.dot(req, HURST, "s2", f"GEX requis {req / 1e11:.2f}×10¹¹ $ / 1 %")
    p1.label(req, HURST, "GEX requis", dx=-7, dy=14, anchor="end", cls="dl halo")
    p1.label(0.0, 0.468, "gamma plausible", dx=0, dy=0, anchor="middle", cls="lg halo")

    # --- P2 : P(target) selon H -------------------------------------------
    a = STOP_PTS
    p2 = Panel(b, 372, 46, 226, 208, title="Ce que l'exposant décide",
               readout="stop 0,050 %")
    p2.domain(0.50, 0.70, 0.0, 8.0)
    p2.frame()
    p2.grid_y([0, 2, 4, 6, 8], lambda v: f"{v:g}", "P(target atteint) en %", side="right")
    p2.grid_x([0.50, 0.55, 0.60, 0.65, 0.70], lambda v: _num(v, 2),
              "exposant d'échelle H")
    for rr, cls in ((20.0, "s1"), (30.0, "s3")):
        curve = []
        for i in range(41):
            hh = 0.50 + 0.20 * i / 40.0
            o = outcome_scaled(a, rr * a, SESSION_MIN, SIGMA_1MIN, hh)
            curve.append((hh, 100.0 * o.p_target))
        p2.path(curve, cls)
        p2.label(0.70, curve[-1][1], f"1:{rr:g}", dx=-26, dy=-6, cls="dl halo")
    p2.vline(HURST, "lvl")
    o20 = outcome_scaled(a, 20 * a, SESSION_MIN, SIGMA_1MIN, HURST)
    o30 = outcome_scaled(a, 30 * a, SESSION_MIN, SIGMA_1MIN, HURST)
    p2.dot(HURST, 100 * o20.p_target, "s1", f"1:20 · {100 * o20.p_target:.2f} %")
    p2.dot(HURST, 100 * o30.p_target, "s3", f"1:30 · {100 * o30.p_target:.2f} %")
    p2.label(HURST, 7.4, "H calibré", dx=-5, dy=0, anchor="end", cls="lg halo")

    b.caption(320, 296, "le gamma agit sur l'espérance par un seul canal : "
                        "l'exposant d'échelle, donc l'atteignabilité du target")
    b.caption(320, 312, "volume quotidien de référence 400 Md$ · impact d'un pourcent par volume quotidien")
    return b.render("Du gamma dealer à l atteignabilité du target, par l exposant d échelle")


# ---------------------------------------------------------------------------
# Profil de volume : POC, aire de valeur, HVN, LVN — et leur conséquence
# ---------------------------------------------------------------------------

def fig_volume_profile() -> str:
    """Le profil, la volatilité locale qu'il implique, et le risque qui en découle.

    Les trois cadres partagent l'axe des prix. Le premier est l'histogramme
    usuel ; le deuxième en est l'inversion — la volatilité locale, plus élevée
    là où le volume manque ; le troisième traduit cette volatilité en la seule
    grandeur qui intéresse le trade : la probabilité de sortir au stop par le
    bruit seul, pour un stop nominal identique partout.
    """
    prof = vprofile.reference_profile()
    va = prof.value_area()
    poc = prof.poc
    hvn = prof.hvn()
    lvn = prof.lvn()
    sig = prof.local_volatility(SIGMA_1MIN)
    lo, hi = 5950.0, 6044.0
    vmax = max(prof.volumes)

    b = Board(640, 376)
    ticks = [5960, 5980, 6000, 6020, 6040]
    thick = 3.0

    p1 = Panel(b, 56, 58, 156, 236, title="Profil de volume",
               readout="contrats par pas de 2 pts")
    p1.domain(0.0, vmax * 1.55, lo, hi)
    p1.frame()
    p1.band_y(va.low, va.high, "wash")
    p1.grid_y(ticks, lambda v: f"{v:g}")
    p1.grid_x([0, 5000, 10000], lambda v: f"{v / 1000:g}k")
    for pr, vol in zip(prof.prices, prof.volumes):
        if not lo <= pr <= hi:
            continue
        cls = "up"
        if pr in lvn:
            cls = "s2f"
        elif pr in hvn:
            cls = "s3f"
        p1.hbar(pr, 0.0, vol, thick, cls, f"{pr:g} · {vol:,.0f} contrats")
    p1.hline(poc, "lvl strong")
    p1.tag(poc, f"POC {poc:g}")
    p1.tag(va.high, f"VAH {va.high:g}")
    p1.tag(va.low, f"VAL {va.low:g}")

    p2 = Panel(b, 246, 58, 148, 236, title="Volatilité locale",
               readout="σ(x) = σ̄·√(v̄/v)")
    p2.domain(0.78, 2.55, lo, hi)
    p2.frame()
    p2.grid_y(ticks, lambda v: "")
    p2.grid_x([1.0, 1.5, 2.0, 2.5], lambda v: _num(v, 1), "points par √minute")
    p2.path([(s, pr) for s, pr in zip(sig, prof.prices)], "s1")
    p2.label(2.55, 6040, "traversée", dx=-6, dy=0, anchor="end", cls="lg halo")
    p2.label(2.55, 5956, "traversée", dx=-6, dy=0, anchor="end", cls="lg halo")
    for lvl in lvn:
        p2.dot(prof.sigma_at(lvl, SIGMA_1MIN), lvl, "s2f",
               f"LVN {lvl:g} · σ = {prof.sigma_at(lvl, SIGMA_1MIN):.2f}", r=3.4)
    for lvl in hvn:
        p2.dot(prof.sigma_at(lvl, SIGMA_1MIN), lvl, "s3f",
               f"HVN {lvl:g} · σ = {prof.sigma_at(lvl, SIGMA_1MIN):.2f}", r=3.4)
    p2.hline(poc, "lvl strong")

    p3 = Panel(b, 428, 58, 168, 236, title="Risque du même stop",
               readout="stop 3 pts · 30 min")
    risks = [(100.0 * prob_touch_single_barrier(STOP_PTS, s, 30.0), pr)
             for s, pr in zip(sig, prof.prices)]
    p3.domain(48.0, 86.0, lo, hi)
    p3.frame()
    p3.grid_y(ticks, lambda v: f"{v:g}", side="right")
    p3.grid_x([50, 60, 70, 80], lambda v: f"{v:g}", "P(stop touché en 30 min), %")
    p3.path(risks, "s1")
    r_poc = 100.0 * prob_touch_single_barrier(STOP_PTS, prof.sigma_at(poc, SIGMA_1MIN), 30.0)
    p3.dot(r_poc, poc, "s3f", f"POC · {r_poc:.0f} %")
    p3.vline(r_poc, "lvl")
    for lvl in lvn:
        r = 100.0 * prob_touch_single_barrier(STOP_PTS, prof.sigma_at(lvl, SIGMA_1MIN), 30.0)
        p3.dot(r, lvl, "s2f", f"LVN {lvl:g} · {r:.0f} %")
        # Posée à gauche du point : à droite, elle sortirait du cadre, le
        # point se trouvant déjà près du bord.
        p3.label(r, lvl, "LVN", dx=-7, dy=3.5, anchor="end", cls="dl halo")
    p3.hline(poc, "lvl strong")

    b.legend(56, 344, [("s3f", "haut volume (HVN)"),
                       ("s2f", "bas volume (LVN)"),
                       ("swatch-wash", "aire de valeur, 70 %")], step=190.0)
    b.caption(320, 366, "un stop en pourcentage fixe du prix n'est pas un risque fixe : "
                        "il vaut 2,3 σ locaux sur un LVN contre 3,6 sur le POC")
    return b.render("Profil de volume, volatilité locale impliquée et probabilité "
                    "de sortie au stop selon le nœud d entrée")


# ---------------------------------------------------------------------------
# Théorie de Dow : la fréquence des motifs sous marche aléatoire
# ---------------------------------------------------------------------------

def fig_dow_null() -> str:
    """Ce que produit une marche aléatoire quand on lui applique les règles de Dow.

    À gauche, la loi exacte ``P(mèche ≥ k·corps) = 1/(2k + 1)`` : la « mèche de
    rejet » usuelle apparaît un jour sur trois sans qu'aucune information ne
    soit en jeu. À droite, la continuation de structure ``δ/(d + δ)`` : sa
    fréquence est fixée par la profondeur du repli, et la dérive nécessaire
    pour la déplacer sensiblement se lit sur l'écart entre les courbes.
    """
    b = Board(640, 392)

    p1 = Panel(b, 58, 50, 236, 184, title="Fréquence d'une mèche dominante",
               readout="1/(2k + 1)")
    p1.domain(0.0, 5.0, 0.0, 1.0)
    p1.frame()
    p1.grid_y([0.0, 0.25, 0.5, 0.75, 1.0], lambda v: _num(v, 2),
              "part des journées sans dérive")
    p1.grid_x([0, 1, 2, 3, 4, 5], lambda v: f"{v:g}",
              "k — mèche haute rapportée au corps")
    p1.path([(k / 40.0, dow.p_dominant_wick(k / 40.0)) for k in range(1, 201)], "s1")
    for k, name in ((1.0, "règle usuelle"), (2.0, ""), (4.5, "un jour sur dix")):
        p1.dot(k, dow.p_dominant_wick(k), "s1",
               f"k = {k:g} · {100 * dow.p_dominant_wick(k):.1f} %")
        if name:
            p1.label(k, dow.p_dominant_wick(k), name, dx=8, dy=-7, cls="dl halo")
    p1.hline(1 / 3.0, "lvl")
    p1.label(5.0, 1 / 3.0, "1/3", dx=-4, dy=-6, anchor="end", cls="lg halo")

    p2 = Panel(b, 372, 50, 226, 184, title="Continuation de structure",
               readout="δ / (d + δ)")
    p2.domain(0.5, 4.0, 0.0, 0.8)
    p2.frame()
    p2.grid_y([0.0, 0.2, 0.4, 0.6, 0.8], lambda v: _num(v, 1),
              "P(nouveau sommet avant nouveau creux)", side="right")
    p2.grid_x([0.5, 1, 2, 3, 4], lambda v: _num(v, 1),
              "profondeur du repli, en multiples de δ")
    delta = 4.0
    mu_star = FRICTION / 28.9
    for mult, cls in ((0.0, "s1"), (1.0, "s2"), (3.0, "s3")):
        pts = []
        for i in range(71):
            ratio = 0.5 + 3.5 * i / 70.0
            pts.append((ratio, dow.p_higher_high(ratio * delta, delta,
                                                 mult * mu_star, SIGMA_1MIN)))
        p2.path(pts, cls, tip=f"µ = {mult:g} µ*")
    p2.dot(1.0, 0.5, "s1", "repli égal au seuil : une chance sur deux")
    p2.label(1.0, 0.5, "repli = δ → ½", dx=9, dy=-7, cls="dl halo")
    b.legend(376, 300, [("s1", "µ = 0"), ("s2", "µ = µ*"), ("s3", "µ = 3 µ*")],
             step=76.0, kind="line")
    # Ligne trop longue pour la place restante à droite de la légende : elle
    # se rognait au bord du cadre. Coupée en deux, elle tient.
    b.caption(376, 324, "trois dérives, trois courbes", anchor="start")
    b.caption(376, 338, "presque confondues : la géométrie", anchor="start")
    b.caption(376, 352, "du repli décide, non le signal", anchor="start")

    up, down, inside = dow.p_close_beyond_body()
    strip_y = 300.0
    b.add(f'<text class="hdr" x="58" y="{strip_y - 8:.0f}">'
          f'Clôture au-delà du corps de la veille</text>')
    seg_x, seg_w = 58.0, 236.0
    acc = 0.0
    for frac, cls, name in ((up, "up", "hausse"), (inside, "ze", "dedans"),
                            (down, "dn", "baisse")):
        w = seg_w * frac
        b.add(f'<rect class="{cls}" x="{seg_x + acc:.1f}" y="{strip_y:.0f}" '
              f'width="{max(w - 2, 1):.1f}" height="14" rx="2">'
              f'<title>{_esc(name)} · {100 * frac:.1f} %</title></rect>')
        b.add(f'<text class="lg" x="{seg_x + acc + w / 2:.1f}" y="{strip_y + 26:.0f}" '
              f'text-anchor="middle">{_esc(name)}</text>')
        b.add(f'<text class="dl halo" x="{seg_x + acc + w / 2:.1f}" '
              f'y="{strip_y + 39:.0f}" text-anchor="middle">'
              f'{_num(100 * frac, 1)} %</text>')
        acc += w
    b.caption(58, strip_y + 58, "trois jours sur quatre déclenchent un signal "
                                "de continuation", anchor="start")

    b.caption(320, 384, "seuil de détection δ = 4 points · σ = 1,25 point par racine "
                        "de minute · µ* = seuil de rentabilité du trade")
    return b.render("Fréquence des motifs de Dow sous marche aléatoire")


# ---------------------------------------------------------------------------
# Fibonacci : la grille, sa loi nulle, et l'arbitrage qu'elle produit
# ---------------------------------------------------------------------------

def fig_fib_retracement() -> str:
    """La grille de retracement et l'arbitrage d'exécution qu'elle impose.

    À gauche, l'impulsion et sa grille : chaque niveau porte la probabilité
    exacte qu'un prix sans dérive l'atteigne avant de prolonger de 10 % la
    jambe. À droite, l'écart d'espérance par signal entre entrée au marché et
    entrée en zone OTE, en fonction de la dérive : il change de signe au
    voisinage immédiat du seuil de rentabilité du trade lui-même.
    """
    leg_lo, leg_hi = 5960.0, 6000.0
    leg = fib.Leg(leg_lo, leg_hi)
    b = Board(640, 348)

    p1 = Panel(b, 58, 50, 250, 212, title="Grille de retracement",
               readout="jambe 40 points")
    p1.domain(0.0, 10.0, 5952.0, 6006.0)
    p1.frame()
    p1.grid_y([5960, 5970, 5980, 5990, 6000], lambda v: f"{v:g}")
    p1.grid_x([0, 2, 4, 6, 8, 10], lambda v: f"{v:g}", "temps (unités arbitraires)")

    ote_lo, ote_hi = leg.ote()
    p1.band_y(ote_lo, ote_hi, "wash")
    for ratio, _src in fib.RATIOS:
        if ratio in (0.236,):
            continue
        lvl = leg.level(ratio)
        p1.hline(lvl, "lvl")
        p1.label(0.0, lvl, f"{_num(ratio, 3)}", dx=3, dy=-3, cls="tk halo")
        p1.label(10.0, lvl, f"{100 * fib.p_retrace_null(ratio):.0f} %",
                 dx=-3, dy=-3, anchor="end", cls="tk halo")

    impulse = [(0.0, leg_lo), (1.2, leg_lo + 8.0), (2.0, leg_lo + 5.0),
               (3.4, leg_lo + 26.0), (4.0, leg_lo + 21.0), (5.0, leg_hi)]
    pull = [(5.0, leg_hi), (6.0, leg.level(0.35)), (6.8, leg.level(0.26)),
            (7.6, leg.level(0.70)), (8.4, leg.level(0.48)), (10.0, leg_hi + 4.0)]
    p1.path(impulse, "s1")
    p1.path(pull, "s1", dash="5 3")
    p1.dot(7.6, leg.level(0.70), "s2", "ordre limite touché dans la zone OTE")
    # Relevée d'une ligne : à hauteur du point, elle partageait sa ligne de
    # base avec le ratio à gauche et sa probabilité à droite.
    p1.label(7.6, leg.level(0.70), "ordre rempli", dx=-8, dy=-16,
             anchor="end", cls="dl halo")

    # --- arbitrage -------------------------------------------------------
    a = STOP_PTS
    target = 20.0 * a
    gain = fib.OTE_LOW * (leg_hi - leg_lo)
    om = outcome_scaled(a, target, SESSION_MIN, SIGMA_1MIN, HURST)
    oo = outcome_scaled(a, target + gain, SESSION_MIN, SIGMA_1MIN, HURST)
    mu_star = FRICTION / om.expected_time

    p2 = Panel(b, 380, 50, 218, 212, title="Écart d'espérance par signal",
               readout="Δ = E(OTE) − E(marché)")
    p2.domain(0.0, 3.0, -0.9, 0.4)
    p2.frame()
    p2.grid_y([-0.8, -0.4, 0.0, 0.4], lambda v: _num(v, 1),
              "Δ en points d'indice par signal", side="right")
    p2.grid_x([0, 1, 2, 3], lambda v: _num(v, 1), "dérive captée (points par heure)")
    pts = []
    for i in range(121):
        mu_h = 3.0 * i / 120.0
        cmp = fib.compare(leg_hi - leg_lo, a, target, FRICTION, mu_h / 60.0,
                          SIGMA_1MIN, om.expected_time, oo.expected_time)
        pts.append((mu_h, cmp.edge))
    p2.path(pts, "s1")
    p2.hline(0.0, "zero")
    crit = fib.compare(leg_hi - leg_lo, a, target, FRICTION, mu_star, SIGMA_1MIN,
                       om.expected_time, oo.expected_time).critical_drift * 60.0
    # Le changement de signe tombe au-delà de la dérive tracée : le marquer à
    # sa position projetterait le repère, la ligne et l'étiquette hors du
    # cadre. On le porte alors comme une lecture au bord, ce qui dit la même
    # chose sans mentir sur l'échelle.
    if crit <= p2.x1:
        p2.vline(crit, "lvl")
        p2.dot(crit, 0.0, "s2",
               f"changement de signe · {crit:.2f} point par heure")
        p2.label(crit, 0.30, "µ*", dx=5, dy=0, cls="dl halo")
    else:
        p2.tag(0.30, f"µ* = {crit:.1f} pt/h, hors cadre", side="right")
    p2.label(3.0, 0.16, "Δ > 0 : la grille paie", dx=-6, dy=0,
             anchor="end", cls="lg halo")
    p2.label(3.0, -0.14, "Δ < 0 : la grille coûte", dx=-6, dy=0,
             anchor="end", cls="lg halo")

    b.caption(320, 300, "trait plein : impulsion · pointillé : retracement · à gauche "
                        "le ratio, à droite sa probabilité nulle d'atteinte")
    b.caption(320, 316, "sous un prix sans dérive, attendre épargne une friction par "
                        "signal non exécuté ; au-delà du seuil,")
    b.caption(320, 332, "les signaux manqués sont ceux qui partaient")
    return b.render("Grille de Fibonacci : loi nulle des retracements et arbitrage "
                    "d exécution de la zone OTE")


# ---------------------------------------------------------------------------
# Carnet d'ordres : carte de liquidité, absorption et leurre
# ---------------------------------------------------------------------------

def fig_liquidity_map() -> str:
    """Carte de liquidité au repos, trajectoire de prix et delta cumulé.

    Construction déterministe : un mur qui tient au contact et un mur qui se
    retire à l'approche, seule différence entre les deux. La planche montre ce
    que l'œil voit — deux murs identiques tant que le prix n'y est pas — et ce
    que le LPR mesure — deux comportements opposés au moment du contact.
    """
    n_t, n_p = 60, 25
    t_max, half = 30.0, 12.0
    prices = [(-half + 2.0 * half * j / (n_p - 1)) for j in range(n_p)]

    noise = _Noise(4242)
    path = [0.0]
    for i in range(1, n_t):
        pull_down = -0.42 if i < 34 else 0.55
        path.append(path[-1] + pull_down + 1.05 * noise.gauss())

    wall_hold, wall_pull = 6.0, -5.0

    def liquidity(ti: int, price: float) -> float:
        t = t_max * ti / (n_t - 1)
        base = 0.30 * math.exp(-abs(price - path[ti]) / 7.0)
        d_hold = abs(price - wall_hold)
        if d_hold < 1.2:
            base += 0.95
        d_pull = abs(price - wall_pull)
        if d_pull < 1.2:
            # Le mur se retire quand le prix s'approche : LPR effondré.
            approach = max(0.0, 1.0 - abs(path[ti] - wall_pull) / 5.0)
            base += 0.95 * (1.0 - approach ** 0.6)
        return min(base, 1.35)

    b = Board(640, 416)
    p1 = Panel(b, 58, 46, 500, 196, title="Liquidité au repos",
               readout="taille affichée par niveau")
    p1.domain(0.0, t_max, -half, half)
    cw = p1.w / n_t
    ch = p1.h / n_p
    for ti in range(n_t):
        for j, pr in enumerate(prices):
            v = liquidity(ti, pr)
            step = min(7, max(0, int(round(v / 1.35 * 7))))
            x = p1.x + cw * ti
            y = p1.sy(pr) - ch / 2
            b.add(f'<rect class="hm{step}" x="{x:.2f}" y="{y:.2f}" '
                  f'width="{cw + 0.4:.2f}" height="{ch + 0.4:.2f}"/>')
    p1.grid_y([-10, -5, 0, 5, 10], lambda v: _signed(v, 0), "points depuis l'entrée")
    p1.grid_x([0, 10, 20, 30], lambda v: f"{v:g}")
    p1.path([(t_max * i / (n_t - 1), path[i]) for i in range(n_t)], "px")
    p1.tag(wall_hold, "mur tenu — LPR 0,91")
    p1.tag(wall_pull, "mur retiré — LPR 0,05")
    p1.frame()

    cvd = [0.0]
    for i in range(1, n_t):
        cvd.append(cvd[-1] + (path[i] - path[i - 1]) * 0.8 + 0.55 * noise.gauss())
    p2 = Panel(b, 58, 296, 500, 56, title="Delta de volume cumulé (CVD)",
               readout="contrats agressifs nets")
    p2.domain(0.0, t_max, min(cvd) * 1.15, max(cvd) * 1.15)
    p2.frame()
    p2.grid_x([0, 10, 20, 30], lambda v: f"{v:g}", "minutes")
    p2.hline(0.0, "zero")
    p2.path([(t_max * i / (n_t - 1), cvd[i]) for i in range(n_t)], "s1")

    ramp_x, ramp_y = 58.0, 265.0
    for k in range(8):
        b.add(f'<rect class="hm{k}" x="{ramp_x + 15 * k:.1f}" y="{ramp_y:.1f}" '
              f'width="15" height="9"/>')
    b.add(f'<text class="lg" x="{ramp_x + 128:.1f}" y="{ramp_y + 8:.1f}">'
          f'taille au repos, du plus faible au plus fort</text>')
    b.caption(320, 408, "trajectoire et carnet simulés de façon déterministe — "
                        "aucune donnée de marché")
    return b.render("Carte de liquidité au repos, trajectoire de prix et delta "
                    "de volume cumulé")


# ---------------------------------------------------------------------------
# Ce que le LPR peut et ne peut pas séparer
# ---------------------------------------------------------------------------

def fig_lpr_power() -> str:
    """Décroissance des files et pouvoir discriminant du LPR.

    À gauche, la fraction survivante d'une file selon son taux d'annulation.
    À droite, la courbe ROC qui en résulte : la profondeur du niveau améliore
    la lecture jusqu'à une dizaine de contrats, puis plus rien — c'est le
    recouvrement des comportements, non l'échantillon, qui plafonne.
    """
    h_gen, h_spoof, dt = 1.0, 4.0, 0.5
    b = Board(640, 336)

    p1 = Panel(b, 58, 50, 236, 208, title="Survie de la file",
               readout="LPR = e^(−h·Δt)")
    p1.domain(0.0, 1.5, 0.0, 1.0)
    p1.frame()
    p1.grid_y([0.0, 0.25, 0.5, 0.75, 1.0], lambda v: _num(v, 2), "fraction restante")
    p1.grid_x([0, 0.5, 1.0, 1.5], lambda v: _num(v, 1),
              "minutes depuis l'affichage")
    for h, cls, name in ((h_gen, "s1", "file tenue"), (h_spoof, "s2", "file retirée")):
        pts = [(1.5 * i / 100.0, orderflow.lpr_expected(h, 1.5 * i / 100.0))
               for i in range(101)]
        p1.path(pts, cls)
        p1.label(1.5, pts[-1][1], name, dx=-6, dy=-7, anchor="end", cls="dl halo")
    p1.vline(dt, "lvl")
    p1.label(dt, 0.97, "contact", dx=5, dy=0, cls="dl halo")
    for h, cls in ((h_gen, "s1"), (h_spoof, "s2")):
        p1.dot(dt, orderflow.lpr_expected(h, dt), cls,
               f"LPR au contact {orderflow.lpr_expected(h, dt):.2f}")

    p2 = Panel(b, 372, 50, 208, 208, title="Pouvoir discriminant",
               readout="courbe ROC")
    p2.domain(0.0, 1.0, 0.0, 1.0)
    p2.frame()
    p2.grid_y([0, 0.25, 0.5, 0.75, 1.0], lambda v: _num(v, 2),
              "vrais positifs", side="right")
    p2.grid_x([0, 0.5, 1.0], lambda v: _num(v, 1), "faux positifs")
    p2.path([(0.0, 0.0), (1.0, 1.0)], "ln", dash="4 3")
    entries = []
    for depth, cls in ((200.0, "s1"), (10.0, "s2"), (2.0, "s3")):
        d = orderflow.lpr_discriminability(depth, h_gen, h_spoof, dt)
        auc = orderflow.lpr_auc(depth, h_gen, h_spoof, dt)
        pts = []
        for i in range(1, 200):
            fpr = i / 200.0
            pts.append((fpr, orderflow.norm_cdf(orderflow._inv_norm(fpr) + d)))
        p2.path(pts, cls, tip=f"profondeur {depth:g} · AUC {auc:.3f}")
        entries.append((cls, f"{depth:g} lots — AUC {_num(auc, 2)}"))
    for i, (cls, text) in enumerate(entries):
        yy = p2.y + p2.h - 46 + 14 * i
        b.add(f'<line class="ln {cls}" x1="{p2.x + 96:.1f}" y1="{yy:.1f}" '
              f'x2="{p2.x + 110:.1f}" y2="{yy:.1f}"/>')
        b.add(f'<text class="lg halo" x="{p2.x + 116:.1f}" y="{yy + 3.5:.1f}">'
              f'{_esc(text)}</text>')
    b.caption(320, 300, f"séparation exigée par une AUC de 0,90 : "
                        f"d' = {_num(orderflow.required_separation_for_auc(0.90), 2)} — "
                        f"hors de portée sous ces taux")
    b.caption(320, 316, "taux d'annulation 1 et 4 par minute · dispersion "
                        "comportementale 0,8 en logarithme")
    b.caption(320, 332, "la profondeur cesse d'apporter au-delà d'une dizaine de contrats")
    return b.render("Décroissance des files d ordres et pouvoir discriminant "
                    "du ratio de persistance de liquidité")


# ---------------------------------------------------------------------------
# Demi-vie d'un signal contre durée d'exposition
# ---------------------------------------------------------------------------

def fig_signal_horizon() -> str:
    """Ce qu'un signal doit valoir pour financer un aller-retour d'une demi-heure.

    À gauche, la part de l'information d'un signal qu'une exposition de trente
    minutes conserve, selon la demi-vie de ce signal. À droite, la dérive
    instantanée qu'il faudrait pour couvrir la friction : deux ordres de
    grandeur séparent les échelles du carnet des échelles structurelles.
    """
    exposure = 28.9
    b = Board(640, 344)

    p1 = Panel(b, 62, 50, 232, 212, title="Information conservée",
               readout=f"exposition {_num(exposure, 1)} min")
    p1.domain(0.02, 5000.0, 0.0, 1.0, xlog=True)
    p1.frame()
    p1.grid_y([0.0, 0.25, 0.5, 0.75, 1.0], lambda v: _num(v, 2),
              "part de la dérive captée")
    p1.grid_x([0.1, 1, 10, 100, 1000],
              lambda v: {0.1: "6 s", 1: "1 min", 10: "10 min",
                         100: "100 min", 1000: "1 j"}[v],
              "demi-vie du signal")
    pts = []
    for i in range(241):
        hl = 0.02 * (5000.0 / 0.02) ** (i / 240.0)
        pts.append((hl, orderflow.captured_drift(1.0, hl, exposure)))
    p1.path(pts, "s1")
    for rank, sc in enumerate(orderflow.SCALES, start=1):
        val = orderflow.captured_drift(1.0, sc.half_life_min, exposure)
        p1.dot(sc.half_life_min, val, "s2",
               f"{sc.name} · {100 * val:.1f} % de la dérive conservée")
        p1.label(sc.half_life_min, val, str(rank), dx=8, dy=-7, cls="tk halo")

    p2 = Panel(b, 372, 50, 226, 212, title="Dérive instantanée exigée",
               readout="pour couvrir c = 0,33 pt")
    p2.domain(0.02, 5000.0, 0.004, 20.0, xlog=True, ylog=True)
    p2.frame()
    p2.grid_y([0.01, 0.1, 1.0, 10.0],
              lambda v: {0.01: "0,01", 0.1: "0,1", 1.0: "1", 10.0: "10"}[v],
              "points par minute", side="right")
    p2.grid_x([0.1, 1, 10, 100, 1000],
              lambda v: {0.1: "6 s", 1: "1 min", 10: "10 min",
                         100: "100 min", 1000: "1 j"}[v],
              "demi-vie du signal")
    p2.band_y(0.005, SIGMA_1MIN, "wash")
    pts = []
    for i in range(241):
        hl = 0.02 * (5000.0 / 0.02) ** (i / 240.0)
        pts.append((hl, orderflow.required_instant_drift(FRICTION, hl, exposure)))
    p2.path(pts, "s1")
    for rank, sc in enumerate(orderflow.SCALES, start=1):
        need = orderflow.required_instant_drift(FRICTION, sc.half_life_min, exposure)
        p2.dot(sc.half_life_min, need, "s2",
               f"{sc.name} · {need:.2f} point par minute exigé")
        p2.label(sc.half_life_min, need, str(rank), dx=8, dy=-7, cls="tk halo")
    p2.label(5000.0, SIGMA_1MIN, "volatilité elle-même", dx=-6, dy=-6,
             anchor="end", cls="lg halo")
    p2.label(3000.0, 6.0, "irrecevable", dx=-6, dy=0, anchor="end", cls="lg halo")
    p2.label(0.02, 0.02, "domaine plausible", dx=6, dy=0, cls="lg halo")

    b.caption(320, 306, "1 cotation · 2 file d'ordres · 3 inventaire · "
                        "4 structurel · 5 positionnement")
    b.caption(320, 322, "bande grisée : dérives inférieures à la volatilité "
                        "d'une minute, seul domaine plausible")
    b.caption(320, 338, "un signal de carnet ne peut pas financer une position "
                        "d'une demi-heure ; il peut en améliorer l'exécution")
    return b.render("Demi-vie d un signal, information conservée sur l exposition "
                    "et dérive instantanée exigée")


# ---------------------------------------------------------------------------
# Bandes VWAP : ce qu'une séance sans dérive y produit
# ---------------------------------------------------------------------------

def fig_vwap_bands() -> str:
    """Enveloppe VWAP en écarts-types et temps de séjour au-delà de chaque bande.

    L'écart au VWAP rapporté à sa dispersion est, pour un prix sans dérive, une
    variable centrée réduite à chaque instant. La part de séance passée au-delà
    de ``k`` écarts-types vaut donc exactement ``2·Φ(−k)``, sans paramètre. Une
    règle d'entrée sur la bande 3 dispose ainsi d'environ une minute de séance
    par jour : sa rareté est une propriété de la définition, pas une découverte.
    """
    from .costs import norm_cdf

    b = Board(640, 352)
    n = 130
    noise = _Noise(90210)
    dev = [0.0]
    for i in range(1, n):
        dev.append(dev[-1] + SIGMA_1MIN * math.sqrt(SESSION_MIN / n) * noise.gauss())

    p1 = Panel(b, 58, 50, 320, 214, title="Écart au VWAP et bandes",
               readout="σ(t) = σ₁·√t")
    p1.domain(0.0, SESSION_MIN, -45.0, 45.0)
    p1.frame()
    p1.grid_y([-40, -20, 0, 20, 40], lambda v: _signed(v, 0), "points depuis le VWAP")
    p1.grid_x([0, 100, 200, 300, 390], lambda v: f"{v:g}", "minutes de séance")
    for k, cls in ((1.0, "s3"), (2.0, "s2"), (3.0, "s1")):
        for sign in (1.0, -1.0):
            band = [(SESSION_MIN * i / 200.0,
                     sign * k * SIGMA_1MIN * math.sqrt(SESSION_MIN * i / 200.0))
                    for i in range(1, 201)]
            p1.path(band, cls, dash="4 3")
        # Étiquette posée là où la bande quitte le cadre, ou à droite si elle y reste.
        t_edge = min(SESSION_MIN, (42.0 / (k * SIGMA_1MIN)) ** 2)
        y_edge = k * SIGMA_1MIN * math.sqrt(t_edge)
        p1.label(t_edge, y_edge, f"{k:g} σ", dx=-5, dy=-5, anchor="end", cls="tk halo")
    p1.hline(0.0, "zero")
    p1.path([(SESSION_MIN * i / (n - 1), dev[i]) for i in range(n)], "px")

    p2 = Panel(b, 434, 50, 164, 214, title="Séjour au-delà",
               readout="2·Φ(−k)")
    p2.domain(0.75, 3.25, 0.0, 148.0)
    p2.frame()
    p2.grid_y([0, 40, 80, 120], lambda v: f"{v:g}",
              "minutes de séance par jour", side="right")
    p2.grid_x([1.0, 1.5, 2.0, 2.5, 3.0], lambda v: _num(v, 1), "bande, en écarts-types")
    for k in (1.0, 1.5, 2.0, 2.5, 3.0):
        minutes = 2.0 * norm_cdf(-k) * SESSION_MIN
        p2.vbar(k, 0.0, minutes, 24.0, "up",
                f"{k:g} σ · {minutes:.1f} minutes de séance")
        p2.label(k, minutes, _num(minutes, 1) if minutes >= 1 else _num(minutes, 2),
                 dx=0, dy=-6, anchor="middle", cls="tk halo")

    b.caption(320, 306, "trajectoire simulée de façon déterministe — "
                        "aucune donnée de marché")
    b.caption(320, 322, "la bande 3 σ est dépassée environ une minute par séance : "
                        "toute règle qui s'y accroche est rare par construction,")
    b.caption(320, 338, "et son échantillon croît d'autant plus lentement")
    return b.render("Bandes VWAP en écarts-types et temps de séjour au-delà de "
                    "chaque bande sous un prix sans dérive")


# ---------------------------------------------------------------------------
# Tableau de bord : l'état de la pile et ce qu'il produit
# ---------------------------------------------------------------------------

def fig_cockpit() -> str:
    """État complet de la pile sur une configuration, et l'espérance qui en sort.

    Les six premiers cadres sont des lectures d'état — chacune produite par le
    module correspondant. Le septième est le seul qui compte : la décomposition
    de l'espérance par trade en dérive captée moins friction. On y voit que six
    lectures concordantes ne déplacent l'espérance que par un seul canal, et
    qu'aucune confluence ne dispense de l'inégalité ``µ·E[τ] > c``.
    """
    chain = gex.reference_chain()
    spot = INDEX_LEVEL
    lv = gex.levels(chain, spot)
    prof = vprofile.reference_profile()
    va = prof.value_area()
    a = STOP_PTS
    o20 = outcome_scaled(a, 20 * a, SESSION_MIN, SIGMA_1MIN, HURST)
    mu_star = FRICTION / o20.expected_time
    k_fb = gex.gamma_feedback_coefficient(lv.net_gex, ADV_USD)

    b = Board(640, 382)

    tiles = [
        ("Régime de gamma", "Γ > 0 — réversion",
         f"GEX {_signed(lv.net_gex / 1e9, 1)} Md$ / 1 %"),
        ("Niveau de bascule", f"HVL {_num(lv.hvl or 0, 0)}",
         f"{_signed(100 * ((lv.hvl or spot) - spot) / spot, 2)} % sous le spot"),
        ("Murs", f"0GW {lv.gamma_wall:g}",
         f"CR1 {lv.cr1:g} · PS1 {lv.ps1:g}"),
        ("Profil de volume", f"POC {prof.poc:g}",
         f"aire de valeur {va.low:g}–{va.high:g}"),
        ("Loi d'échelle impliquée", f"H = {_num(gex.hurst_from_feedback(k_fb, SESSION_MIN), 3)}",
         f"contre {_num(HURST, 3)} calibré"),
        ("Exposition attendue", f"{_num(o20.expected_time, 1)} min",
         f"P(target) {_num(100 * o20.p_target, 2)} %"),
    ]
    tw, th, gap = 190.0, 52.0, 10.0
    for i, (label, value, sub) in enumerate(tiles):
        col, row = i % 3, i // 3
        x = 34.0 + col * (tw + gap)
        y = 44.0 + row * (th + gap)
        b.add(f'<rect class="frame" x="{x:.1f}" y="{y:.1f}" '
              f'width="{tw:.1f}" height="{th:.1f}"/>')
        b.add(f'<text class="sub" x="{x + 9:.1f}" y="{y + 15:.1f}">{_esc(label)}</text>')
        b.add(f'<text class="read" x="{x + 9:.1f}" y="{y + 31:.1f}">{_esc(value)}</text>')
        b.add(f'<text class="lg" x="{x + 9:.1f}" y="{y + 45:.1f}">{_esc(sub)}</text>')

    p = Panel(b, 92, 214, 456, 104, title="Espérance par trade, géométrie 1:20",
              readout="µ·E[τ] − c, en points d'indice")
    p.domain(-0.5, 5.5, -0.68, 1.15)
    p.frame()
    p.grid_y([-0.4, 0.0, 0.4, 0.8], lambda v: _num(v, 1), "points")
    p.hline(0.0, "zero")

    scenarios = [("µ = 0", 0.0), ("µ = ½ µ*", 0.5), ("µ = µ*", 1.0),
                 ("µ = 2 µ*", 2.0), ("µ = 3 µ*", 3.0)]
    p.grid_x([i + 0.5 for i in range(5)], lambda v: scenarios[int(v)][0])
    for i, (name, mult) in enumerate(scenarios):
        gross = mult * mu_star * o20.expected_time
        net = gross - FRICTION
        p.vbar(i + 0.28, 0.0, gross, 26.0, "hm1",
               f"{name} · dérive captée {gross:+.2f} point")
        p.vbar(i + 0.72, 0.0, net, 26.0, "up" if net >= 0 else "dn",
               f"{name} · espérance nette {net:+.2f} point")
        p.label(i + 0.72, net, _signed(net, 2), dx=0,
                dy=-7 if net >= 0 else 14, anchor="middle", cls="tk halo")

    b.legend(92, 348, [("hm1", "dérive captée µ·E[τ]"),
                       ("up", "espérance nette"),
                       ("dn", "espérance nette négative")], step=160.0)
    b.caption(320, 372, "six lectures concordantes n'agissent que par un canal : "
                        "la dérive captée pendant l'exposition")
    return b.render("Tableau de bord de l état de la pile et décomposition "
                    "de l espérance par trade")


ALL_FIGURES = {
    "gexlevels": fig_gex_levels,
    "gammafeedback": fig_gamma_feedback,
    "vprofile": fig_volume_profile,
    "downull": fig_dow_null,
    "fibgrid": fig_fib_retracement,
    "liqmap": fig_liquidity_map,
    "lprpower": fig_lpr_power,
    "sighorizon": fig_signal_horizon,
    "vwapbands": fig_vwap_bands,
    "cockpit": fig_cockpit,
}


def render_all() -> dict[str, str]:
    """Toutes les figures de ce module, prêtes à être insérées dans le document."""
    return {name: fn() for name, fn in ALL_FIGURES.items()}
