"""Les graphiques de la version mobile — direction artistique de l'app Lueur.

Même contrat que les autres modules de figures du dépôt — aucune couleur écrite
en dur (tout passe par des classes que la feuille de la page définit), domaines
déduits des données, libellés ARIA sans apostrophe — mais un autre format :

- une boîte de 340 unités de large, pensée pour un téléphone. Une planche de
  660 rendue sur 330 pixels divise ses textes par deux ; ici, une unité vaut à
  peu près un pixel, et aucun texte ne descend sous 11 ;
- la 3D est celle de l'app : des **blocs isométriques** (projection de
  `components/formation/iso.tsx`, faces dessus, gauche et droite ombrées par la
  feuille), et non des nuages de points ;
- chaque marque porte `data-tip` : la page montre sa valeur au toucher, et un
  `<title>` la montre au survol.
"""

from __future__ import annotations

import math
from functools import lru_cache

from alp1.figterm import _num

from . import (calendrier, choisir, demander, mesurer, negocier, offrir, persuader,
               registre, revenir, stats, synthese)
from .figures import COURT

W = 340.0
COS = math.cos(math.pi / 6)
FIGURES: dict = {}


def _fig(cle: str):
    def deco(f):
        FIGURES[cle] = f
        return f
    return deco


def _esc(t: str) -> str:
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _pct(v: float, nd: int = 1) -> str:
    return _num(v * 100, nd) + " %"


class Fig:
    """Une planche SVG mobile : une boîte de 340 de large, hauteur au choix."""

    def __init__(self, h: float, aria: str):
        if "'" in aria or "’" in aria:
            raise ValueError("libellé ARIA avec apostrophe : " + aria)
        self.h = h
        self.aria = aria
        self.parts: list[str] = []

    def add(self, s: str) -> None:
        self.parts.append(s)

    def text(self, x, y, s, cls="t-ax", anchor="start") -> None:
        self.add(f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}">'
                 f'{_esc(s)}</text>')

    def render(self) -> str:
        return (f'<svg class="mv" viewBox="0 0 {W:g} {self.h:.0f}" role="img" '
                f'aria-label="{_esc(self.aria)}">' + "".join(self.parts) + "</svg>")


def _bulle(tip: str) -> str:
    """Le texte d'une valeur au toucher : il vit dans un attribut, que la passe
    typographique ne visite pas — on y met donc soi-même l'apostrophe courbe."""
    return _esc(tip.replace("'", "\u2019"))


def _marque(tag: str, attrs: str, tip: str) -> str:
    if not tip:
        return f"<{tag} {attrs}/>"
    t = _bulle(tip)
    return f'<{tag} {attrs} data-tip="{t}" tabindex="0"><title>{t}</title></{tag}>'


class Axes:
    """Un cadre 2D : échelles, grille discrète, marques découpées au domaine."""

    def __init__(self, fig: Fig, x, y, w, h, x0, x1, y0, y1, xlog=False, ylog=False):
        self.f, self.x, self.y, self.w, self.h = fig, x, y, w, h
        self.x0, self.x1, self.y0, self.y1 = x0, x1, y0, y1
        self.xlog, self.ylog = xlog, ylog

    def sx(self, v):
        if self.xlog:
            u = (math.log(v) - math.log(self.x0)) / (math.log(self.x1) - math.log(self.x0))
        else:
            u = (v - self.x0) / (self.x1 - self.x0)
        return self.x + min(max(u, 0.0), 1.0) * self.w

    def sy(self, v):
        if self.ylog:
            u = (math.log(v) - math.log(self.y0)) / (math.log(self.y1) - math.log(self.y0))
        else:
            u = (v - self.y0) / (self.y1 - self.y0)
        return self.y + (1.0 - min(max(u, 0.0), 1.0)) * self.h

    def grid_y(self, ticks, fmt, label=None):
        for t in ticks:
            if not min(self.y0, self.y1) - 1e-12 <= t <= max(self.y0, self.y1) + 1e-12:
                continue
            yy = self.sy(t)
            self.f.add(f'<line class="m-grid" x1="{self.x:.1f}" y1="{yy:.1f}" '
                       f'x2="{self.x + self.w:.1f}" y2="{yy:.1f}"/>')
            self.f.text(self.x - 5, yy + 3.8, fmt(t), "t-ax", "end")
        if label:
            self.f.text(self.x, self.y - 8, label, "t-sub")

    def ticks_x(self, ticks, fmt, label=None):
        base = self.y + self.h
        self.f.add(f'<line class="m-axis" x1="{self.x:.1f}" y1="{base:.1f}" '
                   f'x2="{self.x + self.w:.1f}" y2="{base:.1f}"/>')
        for t in ticks:
            if not min(self.x0, self.x1) - 1e-12 <= t <= max(self.x0, self.x1) + 1e-12:
                continue
            self.f.text(self.sx(t), base + 14, fmt(t), "t-ax", "middle")
        if label:
            self.f.text(self.x + self.w, base + 29, label, "t-sub", "end")

    def bar(self, xc, v0, v1, width, cls, tip=""):
        ya, yb = sorted((self.sy(v0), self.sy(v1)))
        self.f.add(_marque("rect", f'class="{cls}" x="{self.sx(xc) - width / 2:.1f}" '
                                   f'y="{ya:.1f}" width="{width:.1f}" '
                                   f'height="{max(yb - ya, 0.8):.1f}" rx="2"', tip))

    def hbar(self, yc, v0, v1, th, cls, tip=""):
        xa, xb = sorted((self.sx(v0), self.sx(v1)))
        self.f.add(_marque("rect", f'class="{cls}" x="{xa:.1f}" y="{self.sy(yc) - th / 2:.1f}" '
                                   f'width="{max(xb - xa, 0.8):.1f}" height="{th:.1f}" rx="3"', tip))

    def line(self, pts, cls, dash=""):
        d = " ".join(("M" if k == 0 else "L") + f"{self.sx(x):.1f},{self.sy(y):.1f}"
                     for k, (x, y) in enumerate(pts))
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.f.add(f'<path class="{cls}" d="{d}"{extra}/>')

    def dot(self, x, y, cls, tip="", r=3.4):
        self.f.add(_marque("circle", f'class="{cls}" cx="{self.sx(x):.1f}" cy="{self.sy(y):.1f}" '
                                     f'r="{r:g}"', tip))

    def band(self, lo_pts, hi_pts, cls="m-band"):
        pts = hi_pts + list(reversed(lo_pts))
        d = " ".join(("M" if k == 0 else "L") + f"{self.sx(x):.1f},{self.sy(y):.1f}"
                     for k, (x, y) in enumerate(pts)) + " Z"
        self.f.add(f'<path class="{cls}" d="{d}"/>')

    def vline(self, x, cls="m-zero"):
        xx = self.sx(x)
        self.f.add(f'<line class="{cls}" x1="{xx:.1f}" y1="{self.y:.1f}" x2="{xx:.1f}" '
                   f'y2="{self.y + self.h:.1f}"/>')

    def hline(self, y, cls="m-zero"):
        yy = self.sy(y)
        self.f.add(f'<line class="{cls}" x1="{self.x:.1f}" y1="{yy:.1f}" '
                   f'x2="{self.x + self.w:.1f}" y2="{yy:.1f}"/>')


def _graduations(lo: float, hi: float, n: int = 4) -> list[float]:
    """Graduations rondes dans le domaine, **trois au moins** : un pas arrondi
    vers le haut en laissait une seule sur l'axe du prix final."""
    if hi <= lo:
        return [lo]
    brut = (hi - lo) / max(n - 1, 1)
    e = 10 ** math.floor(math.log10(brut))
    pas_possibles = sorted({m * e * f for m in (1, 2, 2.5, 5) for f in (0.1, 1, 10)})
    pas = min((x for x in pas_possibles if x >= brut), default=10 * e)
    while True:
        out, v = [], math.ceil(lo / pas - 1e-9) * pas
        while v <= hi + 1e-9 * pas:
            out.append(round(v, 10))
            v += pas
        plus_petit = [x for x in pas_possibles if x < pas]
        if len(out) >= 3 or not plus_petit:
            return out
        pas = max(plus_petit)


# ---------------------------------------------------------------------------
# La 3D de l'app : des blocs isométriques
# ---------------------------------------------------------------------------

class Scene:
    """Des blocs isométriques posés dans l'espace, puis cadrés dans la planche.

    Projection de l'app : x part en bas à droite, y en bas à gauche, z monte.
    Les blocs se peignent du fond vers l'avant (x + y croissant), et la scène
    entière est mise à l'échelle pour tenir dans la largeur du téléphone, les
    étiquettes comprises — leur taille de police, elle, ne change pas.
    """

    def __init__(self):
        self.blocs = []      # (profondeur, tone, ghost, [faces], tip)
        self.textes = []     # (x, y, texte, cls, ancre) en coordonnées projetées

    @staticmethod
    def p(x, y, z):
        return ((x - y) * COS, (x + y) * 0.5 - z)

    def bloc(self, x, y, w, d, h, tone, tip="", z=0.0, ghost=False):
        P = self.p
        top = [P(x, y, z + h), P(x + w, y, z + h), P(x + w, y + d, z + h), P(x, y + d, z + h)]
        left = [P(x, y + d, z), P(x + w, y + d, z), P(x + w, y + d, z + h), P(x, y + d, z + h)]
        right = [P(x + w, y, z), P(x + w, y + d, z), P(x + w, y + d, z + h), P(x + w, y, z + h)]
        self.blocs.append((x + y + z * 0.001, tone, ghost, (right, left, top), tip))

    def texte(self, x, y, z, s, cls="t-ax", ancre="middle", dx=0.0, dy=0.0, groupe=None):
        px, py = self.p(x, y, z)
        self.textes.append((px, py, dx, dy, s, cls, ancre, groupe))

    @staticmethod
    def _largeur(s: str, cls: str) -> float:
        return (6.9 if cls in ("t-lab", "t-val") else 6.2) * len(s)

    def _eclaircir(self, k: float) -> list:
        """Garde une étiquette sur m le long d'une arête, m le plus petit pas qui
        les sépare à l'écran. Deux voisines ne sont écartées que d'une fraction de
        bloc ; au-delà d'une certaine densité, elles se recouvrent."""
        gardes, groupes = [], {}
        for t in self.textes:
            if t[7] is None:
                gardes.append(t)
            else:
                groupes.setdefault(t[7], []).append(t)
        for g in groupes.values():
            if len(g) < 2:
                gardes += g
                continue
            dx = abs(g[1][0] - g[0][0]) * k
            dy = abs(g[1][1] - g[0][1]) * k
            larg = max(self._largeur(t[4], t[5]) for t in g) + 4
            m = 1
            while m * dy < 13.5 and m * dx < larg:
                m += 1
            for j, t in enumerate(g):
                dernier = j == len(g) - 1
                if j % m == 0 or (dernier and (j % m) * dy >= 13.5):
                    gardes.append(t)
        return gardes

    def _bornes(self, k: float, textes) -> tuple[float, float, float, float]:
        xs, ys = [], []
        for *_, faces, _ in self.blocs:
            for face in faces:
                for a, b in face:
                    xs.append(a * k)
                    ys.append(b * k)
        for px, py, dx, dy, s, cls, ancre, _ in textes:
            lw = self._largeur(s, cls)
            gauche = {"start": 0.0, "middle": lw / 2, "end": lw}[ancre]
            x = px * k + dx - gauche
            y = py * k + dy
            xs += [x, x + lw]
            ys += [y - 11, y + 3]
        return min(xs), max(xs), min(ys), max(ys)

    def rendre(self, fig: Fig, x0: float, y0: float, largeur: float, hauteur: float) -> None:
        """Cadre la scène : l'échelle des blocs diminue jusqu'à ce que blocs **et**
        étiquettes tiennent — une étiquette garde sa taille de police, si bien
        qu'un cadrage calculé sur les blocs seuls la faisait sortir de la boîte."""
        bx = [a for *_, faces, _ in self.blocs for face in faces for a, _ in face]
        by = [b for *_, faces, _ in self.blocs for face in faces for _, b in face]
        k = min((largeur - 8) / max(max(bx) - min(bx), 1e-9),
                (hauteur - 8) / max(max(by) - min(by), 1e-9))
        for _ in range(200):
            textes = self._eclaircir(k)
            x_lo, x_hi, y_lo, y_hi = self._bornes(k, textes)
            if x_hi - x_lo <= largeur - 8 and y_hi - y_lo <= hauteur - 8:
                break
            k *= 0.97
        ox = x0 + (largeur - (x_hi - x_lo)) / 2 - x_lo
        oy = y0 + 4 - y_lo

        def T(a, b):
            return f"{ox + a * k:.1f},{oy + b * k:.1f}"

        fig.add('<ellipse class="iso-floor" cx="{:.1f}" cy="{:.1f}" rx="{:.1f}" ry="{:.1f}"/>'.format(
            ox + (min(bx) + max(bx)) / 2 * k, oy + max(by) * k - 6,
            (max(bx) - min(bx)) * k / 2, 9.0))
        for _, tone, ghost, faces, tip in sorted(self.blocs, key=lambda b: b[0]):
            cls = f"iso t-{tone}" + (" is-ghost" if ghost else "")
            polys = "".join(f'<polygon class="iso-{n}" points="{" ".join(T(a, b) for a, b in face)}"/>'
                            for n, face in zip(("r", "l", "t"), faces))
            if tip:
                t = _bulle(tip)
                fig.add(f'<g class="{cls}" data-tip="{t}" tabindex="0"><title>{t}</title>{polys}</g>')
            else:
                fig.add(f'<g class="{cls}">{polys}</g>')
        for px, py, dx, dy, s, cls, ancre, _ in textes:
            fig.text(ox + px * k + dx, oy + py * k + dy, s, cls, ancre)
        return oy + y_hi


def _tone(v: float, lo: float, hi: float) -> str:
    """Quatre bleus de l'app, du plus sombre (bas) au plus clair (haut)."""
    u = (v - lo) / (hi - lo) if hi > lo else 0.5
    return ("deep", "blue", "sky", "pale")[min(3, max(0, int(u * 4)))]


def _grille_iso(z, rows, cols, fmt, quoi, hmax=96.0, taille=26.0, pas=34.0,
                log=False, plancher=None):
    """Une grille de blocs : lignes le long de y, colonnes le long de x.

    La hauteur est proportionnelle à la valeur, depuis zéro — sauf pour une
    grandeur en logarithme, dont le plancher est déclaré et écrit en légende.
    """
    sc = Scene()
    plat = [v for l in z for v in l]
    lo, hi = min(plat), max(plat)
    if log:
        base = plancher if plancher is not None else lo
        hval = lambda v: 6 + (math.log10(v) - math.log10(base)) / (math.log10(hi) - math.log10(base)) * hmax
    else:
        hval = lambda v: max(3.0, v / hi * hmax)
    ni, nj = len(z), len(z[0])
    for i in range(ni):
        for j in range(nj):
            v = z[i][j]
            sc.bloc(j * pas, i * pas, taille, taille, hval(v), _tone(v, lo, hi),
                    tip=f"{rows[i]} · {cols[j]} : {fmt(v)} {quoi}".strip())
    X, Y = (nj - 1) * pas + taille, (ni - 1) * pas + taille
    for i, lab in enumerate(rows):
        if lab:
            sc.texte(X, i * pas + taille / 2, 0, lab, "t-lab", "start", dx=8, dy=8, groupe="lignes")
    for j, lab in enumerate(cols):
        if lab:
            sc.texte(j * pas + taille / 2, Y, 0, lab, "t-lab", "end", dx=-8, dy=12, groupe="colonnes")
    return sc, lo, hi


def _legende(fig: Fig, y: float, items) -> None:
    """Légende en pastilles : (classe de remplissage, texte), sur une ou deux lignes."""
    x = 0.0
    for cls, t in items:
        lw = 6.2 * len(t) + 22
        if x + lw > W:
            x, y = 0.0, y + 18
        fig.add(f'<rect class="{cls}" x="{x:.1f}" y="{y - 9:.1f}" width="11" height="11" rx="3"/>')
        fig.text(x + 16, y, t, "t-ax")
        x += lw + 10


# ---------------------------------------------------------------------------
# La chasse
# ---------------------------------------------------------------------------

def _cls(v: str) -> str:
    return {"tient": "m-ok", "contraire": "m-ko", "non établi": "m-nul"}[v]


@_fig("chasse")
def m_chasse() -> str:
    res, q = synthese.tous(), synthese.q_valeurs()
    reg = registre.par_id()
    passes = [r.p for i, r in res.items() if q[i] < synthese.SEUIL_Q]
    zbh = abs(stats.Phi_inv(max(passes) / 2))
    fams = list(registre.FAMILLES)
    rang = 34.0
    f = Fig(len(fams) * rang + 64, "Les cinquante neuf hypotheses placees selon leur z oriente, "
                                   "famille par famille, avec le seuil corrige")
    ax = Axes(f, 84, 22, W - 102, len(fams) * rang, -5, 12, -0.5, len(fams) - 0.5)
    ax.band([(-1.96, -0.5), (1.96, -0.5)], [(-1.96, len(fams) - 0.5), (1.96, len(fams) - 0.5)])
    ax.vline(0.0, "m-axis")
    ax.vline(zbh, "m-seuil")
    ax.vline(-zbh, "m-seuil")
    for k, fa in enumerate(fams):
        yrow = len(fams) - 1 - k
        f.text(ax.x - 8, ax.sy(yrow) + 4, registre.FAMILLES[fa], "t-lab", "end")
        ids = [i for i in res if i.startswith(fa)]
        for j, i in enumerate(ids):
            z = synthese.z_oriente(i)
            v = synthese.verdict(i)
            ax.dot(min(max(z, -5), 12), yrow + ((j % 3) - 1) * 0.16, _cls(v),
                   tip=f"{i} {COURT[i]} — z {_num(z, 1)}, {v}", r=4.2)
    ax.ticks_x([-4, 0, 4, 8, 12], lambda v: ("12+" if v == 12 else _num(v, 0)), "z orienté")
    return f.render()


@_fig("chasse3d")
def m_chasse3d() -> str:
    fams = list(registre.FAMILLES)
    sc = Scene()
    pas, taille, unite = 30.0, 22.0, 6.0
    for k, fa in enumerate(fams):
        ids = [i for i in synthese.tous() if i.startswith(fa)]
        t = sum(1 for i in ids if synthese.verdict(i) == "tient")
        c = sum(1 for i in ids if synthese.verdict(i) == "contraire")
        n = len(ids) - t - c
        z0 = 0.0
        for nb, tone, ghost, nom in ((t, "blue", False, "tiennent"), (c, "red", False, "contraire"),
                                     (n, "gray", True, "non établies")):
            if nb:
                sc.bloc(0, k * pas, taille, taille, nb * unite, tone, z=z0, ghost=ghost,
                        tip=f"{registre.FAMILLES[fa]} : {nb} {nom}")
                z0 += nb * unite
        sc.texte(taille, k * pas + taille / 2, 0, f"{registre.FAMILLES[fa]}  {t + c}/{len(ids)}",
                 "t-lab", "start", dx=10, dy=6)
    f = Fig(300, "Colonnes isometriques des hypotheses par famille, ce qui tient en bleu")
    bas = sc.rendre(f, 0, 0, W, 268)
    _legende(f, bas + 22, [("m-ok", "tient"), ("m-ko", "contraire"), ("m-nul", "non établi")])
    f.h = bas + 32
    return f.render()


@_fig("pvaleurs")
def m_pvaleurs() -> str:
    ps = [r.p for r in synthese.tous().values()]
    c = [0] * 10
    for v in ps:
        c[min(int(v * 10), 9)] += 1
    att = len(ps) / 10
    f = Fig(200, "Histogramme des valeurs p des cinquante neuf tests contre la loi uniforme")
    hi = max(c) * 1.12
    ax = Axes(f, 30, 24, W - 40, 130, 0, 1, 0, hi)
    ax.grid_y(_graduations(0, hi, 4), lambda v: _num(v, 0), "tests")
    for k, n in enumerate(c):
        ax.bar((k + 0.5) / 10, 0, n, ax.w / 10 * 0.74, "m-bar",
               tip=f"p de {_num(k / 10, 1)} à {_num((k + 1) / 10, 1)} : {n} tests")
    ax.hline(att, "m-seuil")
    f.text(ax.sx(0.98), ax.sy(att) - 6, f"hasard seul : {_num(att, 1)}", "t-sub", "end")
    ax.ticks_x([0.2, 0.4, 0.6, 0.8, 1.0], lambda v: _num(v, 1), "valeur p")
    return f.render()


# ---------------------------------------------------------------------------
# Demander
# ---------------------------------------------------------------------------

@_fig("raop_heures")
def m_raop_heures() -> str:
    base = demander.base_globale()
    serie = demander.taux_par("heure", range(24))
    f = Fig(222, "Part des demandes servies heure par heure contre la bande du hasard")
    hi = max(t for _, t, _, _ in serie) * 1.15
    ax = Axes(f, 42, 24, W - 52, 150, -0.6, 23.6, 0, hi)
    lo_p = [(h, base - 1.96 * math.sqrt(base * (1 - base) / n)) for h, _, n, _ in serie]
    hi_p = [(h, base + 1.96 * math.sqrt(base * (1 - base) / n)) for h, _, n, _ in serie]
    ax.band(lo_p, hi_p)
    ax.grid_y(_graduations(0, hi, 4), lambda v: _pct(v, 0), "servies")
    for h, t, n, _ in serie:
        ax.bar(h, 0, t, 8.6, "m-bar-nuit" if h < 6 else "m-bar",
               tip=f"{h} h : {_pct(t)} servies ({n} demandes)")
    ax.hline(base, "m-seuil")
    ax.ticks_x([0, 6, 12, 18, 23], lambda v: f"{v:.0f} h", "heure de New York")
    return f.render()


@_fig("raop_iso")
def m_raop_iso() -> str:
    z, _, _ = demander.grille_statut_effort()
    z = [list(reversed(l)) for l in reversed(z)]
    rows = ["karma Q5", "Q4", "Q3", "Q2", "Q1"]
    cols = ["long Q5", "Q4", "Q3", "Q2", "court Q1"]
    sc, lo, hi = _grille_iso(z, rows, cols, lambda v: _pct(v), "servies")
    f = Fig(300, "Blocs isometriques de la part servie selon le karma et la longueur")
    f.h = sc.rendre(f, 0, 0, W, 292) + 6
    return f.render()


# ---------------------------------------------------------------------------
# Offrir
# ---------------------------------------------------------------------------

@_fig("karlan_bras")
def m_karlan_bras() -> str:
    bras = offrir.taux_bras()
    f = Fig(210, "Taux de don par bras de la lettre avec intervalles")
    hi = max(t + h for _, t, h, _ in bras) * 1.12
    ax = Axes(f, 38, 24, W - 48, 140, -0.5, 3.5, 0, hi)
    ax.grid_y(_graduations(0, hi, 4), lambda v: _pct(v, 1), "ont donné")
    for k, (nom, t, h, n) in enumerate(bras):
        ax.bar(k, 0, t, 38, "m-bar2" if k == 0 else "m-bar",
               tip=f"{nom} : {_pct(t, 2)} sur {n} lettres")
        ax.line([(k, t - h), (k, t + h)], "m-ci")
        f.text(ax.sx(k), ax.y + ax.h + 15, nom, "t-lab", "middle")
    return f.render()


@_fig("karlan_ronds")
def m_karlan_ronds() -> str:
    c = offrir.comptes_montants(105)
    f = Fig(196, "Montants donnes au dollar pres, les multiples de cinq en bleu")
    mx = max(c.values()) * 1.08
    ax = Axes(f, 30, 24, W - 40, 130, 0, 106, 0, mx)
    ax.grid_y(_graduations(0, mx, 4), lambda v: _num(v, 0), "dons")
    for a, n in sorted(c.items()):
        ax.bar(a, 0, n, 2.2, "m-bar" if a % 5 == 0 else "m-bar-pale", tip=f"{a} $ : {n} dons")
    ax.ticks_x([5, 25, 50, 75, 100], lambda v: f"{v:.0f} $", "montant donné")
    return f.render()


@_fig("karlan_iso")
def m_karlan_iso() -> str:
    z, rows, cols = offrir.grille_ratio_recence()
    z = [list(reversed(l)) for l in z]
    sc, _, _ = _grille_iso(z, rows, list(reversed(cols)), lambda v: _pct(v, 2), "de dons",
                           taille=28, pas=36)
    f = Fig(300, "Blocs isometriques du taux de don selon la recence et le bras de la lettre")
    f.h = sc.rendre(f, 0, 0, W, 292) + 6
    return f.render()


# ---------------------------------------------------------------------------
# Persuader
# ---------------------------------------------------------------------------

@_fig("p4g_diag")
def m_p4g_diag() -> str:
    d = persuader.diagnostic_reponse()
    f = Fig(212, "Part des messages precedes dune hesitation ou dun accord, avant la tactique "
                 "et en general")
    ax = Axes(f, 36, 24, W - 46, 140, -0.6, 1.6, 0, 0.32)
    ax.grid_y([0, 0.1, 0.2, 0.3], lambda v: _pct(v, 0), "messages précédés")
    for k, (cle, quoi, nom) in enumerate((("libre", "hésitation", "« vous êtes libre »"),
                                          ("merci", "accord", "« merci »"))):
        apres, base, n = d[cle]
        ax.bar(k - 0.2, 0, base, 30, "m-bar2", tip=f"tous les messages : {_pct(base)} après un {quoi}")
        ax.bar(k + 0.2, 0, apres, 30, "m-bar", tip=f"messages {nom} : {_pct(apres)} après un {quoi}")
        f.text(ax.sx(k), ax.y + ax.h + 15, nom, "t-lab", "middle")
        f.text(ax.sx(k), ax.y + ax.h + 29, f"après un {quoi}", "t-sub", "middle")
    return f.render()


@_fig("p4g_iso")
def m_p4g_iso() -> str:
    d = persuader.diagnostic_reponse()
    sc = Scene()
    vals = [(d["libre"][1], "gray", "tous", "hésitation"), (d["libre"][0], "blue", "« libre »", "hésitation"),
            (d["merci"][1], "gray", "tous", "accord"), (d["merci"][0], "blue", "« merci »", "accord")]
    hi = max(v for v, *_ in vals)
    for k, (v, tone, nom, quoi) in enumerate(vals):
        x, y = k * 30.0, -k * 30.0
        h = v / hi * 110
        sc.bloc(x, y, 24, 24, h, tone, tip=f"{nom} : {_pct(v)} après un {quoi}")
        sc.texte(x + 12, y + 12, h, _pct(v, 0), "t-val", "middle", dy=-8)
        sc.texte(x + 24, y + 24, 0, nom, "t-lab", "middle", dx=-10, dy=22)
    f = Fig(250, "Colonnes isometriques des messages precedes dune hesitation ou dun accord")
    f.h = sc.rendre(f, 0, 0, W, 246) + 6
    return f.render()


# ---------------------------------------------------------------------------
# Négocier
# ---------------------------------------------------------------------------

@_fig("barg_ancre")
def m_barg_ancre() -> str:
    an = negocier.ancrage()
    f = Fig(214, "Prix final selon la premiere offre de lacheteur, par decile")
    lo = min(y for _, y, _ in an) - 0.03
    hi = max(y for _, y, _ in an) + 0.03
    ax = Axes(f, 38, 24, W - 48, 140, 0.35, 1.05, lo, hi)
    ax.grid_y(_graduations(lo, hi, 4), lambda v: _pct(v, 0), "prix final / annonce")
    ax.line([(x, y) for x, y, _ in an], "m-line")
    for x, y, n in an:
        ax.dot(x, y, "m-dot", tip=f"1re offre à {_pct(x, 0)} : prix final {_pct(y)} ({n} accords)")
    ax.ticks_x([0.4, 0.6, 0.8, 1.0], lambda v: _pct(v, 0), "1re offre de l'acheteur / annonce")
    return f.render()


@_fig("barg_iso")
def m_barg_iso() -> str:
    t = [l for l in negocier.table() if l["valide"] and l["prem_ach"] is not None
         and 0.05 <= l["prem_ach"] <= 1.5]
    k = 5
    qa = [stats.quantile([l["prem_ach"] for l in t], (i + 1) / k) for i in range(k - 1)]
    qp = [stats.quantile([l["annonce"] for l in t], (i + 1) / k) for i in range(k - 1)]
    s = [[0.0] * k for _ in range(k)]
    n = [[0] * k for _ in range(k)]
    for l in t:
        a = sum(1 for x in qa if l["prem_ach"] > x)
        c = sum(1 for x in qp if l["annonce"] > x)
        s[a][c] += l["ratio"]
        n[a][c] += 1
    z = [[s[a][c] / n[a][c] for c in range(k)] for a in range(k)]
    z = [list(reversed(l)) for l in reversed(z)]
    sc, _, _ = _grille_iso(z, ["offre haute", "Q4", "Q3", "Q2", "offre basse"],
                           ["prix Q5", "Q4", "Q3", "Q2", "prix Q1"],
                           lambda v: _pct(v), "de l'annonce", hmax=96)
    f = Fig(300, "Blocs isometriques du prix final selon la premiere offre et le prix affiche")
    f.h = sc.rendre(f, 0, 0, W, 292) + 6
    return f.render()


# ---------------------------------------------------------------------------
# Choisir
# ---------------------------------------------------------------------------

@_fig("speed_prob")
def m_speed_prob() -> str:
    par: dict = {}
    for s in choisir.sequences():
        if s["prob"] is not None:
            par.setdefault(int(round(s["prob"])), []).append(s["y"])
    pts = [(k, sum(v) / len(v), len(v)) for k, v in sorted(par.items()) if len(v) >= 20 and 1 <= k <= 10]
    f = Fig(214, "Taux de oui des hommes selon la probabilite percue dun oui en retour")
    ax = Axes(f, 46, 24, W - 56, 140, 0.5, 10.5, 0, 1)
    ax.grid_y([0, 0.25, 0.5, 0.75, 1.0], lambda v: _pct(v, 0), "disent oui")
    ax.line([(k, m) for k, m, _ in pts], "m-line")
    for k, m, n in pts:
        ax.dot(k, m, "m-dot", tip=f"« elle dira oui » à {k}/10 : {_pct(m)} de oui ({n})")
    ax.ticks_x([1, 3, 5, 7, 10], lambda v: f"{v:.0f}", "« elle dira oui », de 1 à 10")
    return f.render()


@_fig("speed_iso")
def m_speed_iso() -> str:
    z, _, _ = choisir.contraste_grille()
    z = [list(l) for l in reversed(z)]
    sc, _, _ = _grille_iso(z, ["courante Q4", "Q3", "Q2", "courante Q1"],
                           ["précédente Q1", "Q2", "Q3", "précéd. Q4"],
                           lambda v: _pct(v), "de oui", taille=30, pas=40)
    f = Fig(300, "Blocs isometriques du oui selon lattrait de la partenaire courante et de la "
                 "precedente")
    f.h = sc.rendre(f, 0, 0, W, 292) + 6
    return f.render()


# ---------------------------------------------------------------------------
# Revenir
# ---------------------------------------------------------------------------

@_fig("cd_suivi")
def m_cd_suivi() -> str:
    s = revenir.suivi()
    hi = max(max(a, e) for _, a, e in s) * 1.05
    f = Fig(220, "Achats repetes cumules realises et attendus par le modele sur soixante dix "
                 "huit semaines")
    ax = Axes(f, 38, 24, W - 48, 140, 0, 78, 0, hi)
    ax.band([(39, 0), (78, 0)], [(39, hi), (78, hi)], "m-band")
    ax.grid_y(_graduations(0, hi, 4), lambda v: _num(v / 1000, 0) + " k", "achats répétés")
    ax.line([(w, e) for w, _, e in s], "m-line-gris", dash="5 4")
    ax.line([(w, a) for w, a, _ in s], "m-line-b")
    for w, a, e in s[38::39]:
        ax.dot(w, a, "m-dot-b", tip=f"semaine {w} : {_num(a, 0)} réalisés, {_num(e, 0)} prévus")
    f.text(ax.sx(41), ax.y + 14, "prédiction", "t-sub")
    ax.ticks_x([0, 13, 26, 39, 52, 65, 78], lambda v: f"{v:.0f}", "semaine")
    return f.render()


@_fig("cd_paradoxe")
def m_cd_paradoxe() -> str:
    par = revenir.paradoxe()
    f = Fig(218, "Silencieux depuis vingt six semaines, achats futurs reels et predits selon la "
                 "frequence passee")
    hi = max(max(h, p) for _, h, p, _ in par) * 1.15
    ax = Axes(f, 30, 24, W - 40, 140, 0.4, len(par) + 0.6, 0, hi)
    ax.grid_y(_graduations(0, hi, 4), lambda v: _num(v, 1), "achats futurs")
    for x, h, p, n in par:
        lab = f"{x}+" if x == par[-1][0] else f"{x}"
        ax.bar(x - 0.17, 0, h, 15, "m-bar", tip=f"{lab} achats passés : {_num(h, 2)} réalisés ({n} clients)")
        ax.bar(x + 0.17, 0, p, 15, "m-bar2", tip=f"{lab} achats passés : {_num(p, 2)} prévus")
        f.text(ax.sx(x), ax.y + ax.h + 14, lab, "t-ax", "middle")
    f.text(ax.x + ax.w, ax.y + ax.h + 29, "achats passés avant le silence", "t-sub", "end")
    return f.render()


@_fig("cd_iso")
def m_cd_iso() -> str:
    par = revenir.paradoxe()
    sc = Scene()
    hi = max(max(h, p) for _, h, p, _ in par)
    pas = 32.0
    # Les anciens gros acheteurs ont les plus hautes colonnes : ils vont au
    # fond, sinon ils cachent les rangées de derrière.
    for k, (x, h, p, n) in enumerate(reversed(par)):
        lab = f"{x}+" if x == par[-1][0] else f"{x}"
        sc.bloc(0, k * pas, 22, 22, max(2.0, h / hi * 120), "blue",
                tip=f"{lab} achats passés : {_num(h, 2)} achats futurs réalisés")
        sc.bloc(28, k * pas, 22, 22, max(2.0, p / hi * 120), "gray", ghost=True,
                tip=f"{lab} achats passés : {_num(p, 2)} prévus par le modèle")
        sc.texte(50, k * pas + 11, 0, f"{lab} achat{'s' if x > 1 else ''}", "t-lab", "start", dx=8, dy=6)
    f = Fig(318, "Colonnes isometriques appariees des achats futurs reels et predits chez les "
                 "silencieux")
    bas = sc.rendre(f, 0, 0, W, 286)
    _legende(f, bas + 22, [("m-bar", "réalisé"), ("m-bar2", "prévu par le modèle")])
    f.h = bas + 32
    return f.render()


# ---------------------------------------------------------------------------
# Le calendrier
# ---------------------------------------------------------------------------

@_fig("naissances")
def m_naissances() -> str:
    pr = calendrier.profil()
    lo = min(m - h for _, m, h, _ in pr) * 1.1
    hi = max(m + h for _, m, h, _ in pr) * 1.1
    f = Fig(214, "Ecart des naissances par date du mois au meme jour de la semaine")
    ax = Axes(f, 34, 24, W - 44, 140, 0.4, 31.6, lo, hi)
    ax.grid_y(_graduations(lo, hi, 4), lambda v: _num(v * 100, 0) + " %", "écart au même jour de la semaine")
    ax.hline(0.0, "m-axis")
    for k, m, h, n in pr:
        cls = "m-dot-r" if k == 13 else "m-dot"
        ax.line([(k, m - h), (k, m + h)], "m-ci-r" if k == 13 else "m-ci")
        ax.dot(k, m, cls, tip=f"le {k} : {_num(m * 100, 2)} %", r=3.0)
    ax.ticks_x([1, 7, 13, 20, 27, 31], lambda v: f"{v:.0f}", "date du mois")
    return f.render()


@_fig("paie_iso")
def m_paie_iso() -> str:
    d = mesurer.paie()
    z = [list(reversed(l)) for l in d["puissance"]]
    rows = [f"×{_num(1 + a, 1)}" for a in mesurer.AMPLITUDES]
    cols = [f"{n} achats" if k in (0, 6) else f"{n}" for k, n in enumerate(reversed(mesurer.ACHATS))]
    sc, _, _ = _grille_iso(z, rows, cols, lambda v: _pct(v, 0), "détectées", taille=20, pas=26,
                           hmax=100)
    f = Fig(300, "Blocs isometriques de la part des jours de paie detectes selon lintensite et "
                 "les achats")
    f.h = sc.rendre(f, 0, 0, W, 292) + 6
    return f.render()


@_fig("horloge")
def m_horloge() -> str:
    h = mesurer.horloge()
    f = Fig(222, "Erreur mediane sur lheure dun fan selon le nombre de messages")
    msgs = list(mesurer.MESSAGES)
    hi = max(max(l) for l in h["erreur"]) * 1.08
    ax = Axes(f, 34, 24, W - 44, 140, min(msgs), max(msgs), 0, hi, xlog=True)
    ax.grid_y(_graduations(0, hi, 4), lambda v: _num(v, 0) + " h", "erreur médiane")
    styles = {4.0: ("m-line-b", ""), 1.0: ("m-line", ""), 0.25: ("m-line-gris", "5 4")}
    for kap, (cls, dash) in styles.items():
        i = mesurer.CONCENTRATIONS.index(kap)
        pts = sorted(zip(msgs, h["erreur"][i]))
        ax.line(pts, cls, dash)
        for n, e in pts:
            ax.dot(n, e, "m-dot-b" if kap == 4.0 else ("m-dot" if kap == 1.0 else "m-dot-g"),
                   tip=f"κ {_num(kap, 2)}, {n} messages : {_num(e * 60, 0)} min", r=2.8)
    ax.ticks_x([5, 10, 20, 40, 80, 160], lambda v: f"{v:.0f}", "messages observés")
    _legende(f, 214, [("m-ok", "net (κ 4)"), ("m-blanc", "moyen (κ 1)"), ("m-nul", "diffus (κ 0,25)")])
    return f.render()


# ---------------------------------------------------------------------------
# Mesurer
# ---------------------------------------------------------------------------

@_fig("budget_iso")
def m_budget_iso() -> str:
    z = mesurer.surface_budget()
    z = [[10 ** v for v in reversed(l)] for l in reversed(z)]
    rows = [_pct(v, 0) for v in reversed(mesurer.BASES)]
    cols = ["+" + _pct(v, 0) for v in reversed(mesurer.HAUSSES)]
    sc, _, _ = _grille_iso(z, [f"base {r}" if k == 0 else r for k, r in enumerate(rows)],
                           [f"hausse {c}" if k == 0 else c for k, c in enumerate(cols)],
                           lambda v: _num(v, 0), "envois par variante", taille=22, pas=28,
                           log=True, hmax=110)
    f = Fig(300, "Blocs isometriques du nombre denvois par variante selon la base et la hausse")
    f.h = sc.rendre(f, 0, 0, W, 292) + 6
    return f.render()


@_fig("regarder")
def m_regarder() -> str:
    r = mesurer.regarder()
    ks = list(mesurer.REGARDS)
    hi = max(r["naif"].values()) * 1.12
    f = Fig(230, "Faux positifs selon le nombre de regards sur un test A A")
    ax = Axes(f, 34, 24, W - 44, 140, 1, 100, 0, hi, xlog=True)
    ax.grid_y(_graduations(0, hi, 4), lambda v: _pct(v, 0), "fausses victoires")
    ax.hline(0.05, "m-seuil")
    ax.line([(k, r["naif"][k]) for k in ks], "m-line")
    ax.line([(k, r["msprt"][k]) for k in ks], "m-line-b")
    for k in ks:
        ax.dot(k, r["naif"][k], "m-dot", tip=f"{k} regards, test classique : {_pct(r['naif'][k])}")
        ax.dot(k, r["msprt"][k], "m-dot-b", tip=f"{k} regards, test toujours valide : {_pct(r['msprt'][k], 2)}")
    ax.ticks_x(ks, lambda v: f"{v:.0f}", "regards sur le test")
    _legende(f, 222, [("m-blanc", "test classique"), ("m-ok", "test toujours valide")])
    return f.render()


@_fig("gagnant")
def m_gagnant() -> str:
    z = mesurer.surface_gagnant()
    j = mesurer.ENVOIS.index(500)
    vals = [(k, z[i][j]) for i, k in enumerate(mesurer.VARIANTES)][::-1]
    f = Fig(206, "Hausse affichee par la meilleure de k variantes sans effet a cinq cents envois")
    hi = max(v for _, v in vals) * 1.15
    ax = Axes(f, 48, 24, W - 58, 136, -0.5, len(vals) - 0.5, 0, hi)
    ax.grid_y(_graduations(0, hi, 4), lambda v: "+" + _pct(v, 0), "hausse affichée")
    for k, (n, v) in enumerate(vals):
        ax.bar(k, 0, v, 30, "m-bar", tip=f"meilleure de {n} variantes nulles : +{_pct(v)}")
        f.text(ax.sx(k), ax.y + ax.h + 14, f"{n}", "t-lab", "middle")
    f.text(ax.x + ax.w, ax.y + ax.h + 29, "variantes comparées, 500 envois chacune", "t-sub", "end")
    return f.render()


@_fig("classement")
def m_classement() -> str:
    items = [(i, n / synthese.ENVOIS_SEMAINE) for i, _, n in synthese.classement() if n is not None]
    rang = 30.0
    f = Fig(len(items) * rang + 58, "Semaines de test necessaires pour reverifier chaque effet "
                                    "etabli dans une agence")
    lo, hi = 0.1, max(s for _, s in items) * 1.5
    ax = Axes(f, 10, 18, W - 20, len(items) * rang, lo, hi, -0.5, len(items) - 0.5, xlog=True)
    for t in (0.1, 1, 10, 100):
        if lo <= t <= hi:
            ax.vline(t, "m-grid")
    for k, (i, s) in enumerate(items):
        y = len(items) - 1 - k
        cls = "m-bar" if synthese.verdict(i) == "tient" else "m-bar-r"
        f.text(10, ax.sy(y) - 6, f"{COURT[i]}", "t-lab")
        f.text(W - 10, ax.sy(y) - 6, f"{_num(s, 1)} sem.", "t-val", "end")
        ax.hbar(y - 0.18, lo, s, 7, cls, tip=f"{i} {COURT[i]} : {_num(s, 1)} semaines")
    ax.ticks_x([t for t in (0.1, 1, 10, 100) if lo <= t <= hi],
               lambda v: _num(v, 1 if v < 1 else 0), "semaines de test (échelle log)")
    return f.render()


@lru_cache(maxsize=1)
def rendre() -> dict[str, str]:
    return {k: f() for k, f in FIGURES.items()}
