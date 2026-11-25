"""Le noyau statistique — bibliothèque standard seulement.

Tout ce que le document publie passe par ces fonctions : lois, tests, modèles,
corrections. Aucune n'a de dépendance, et chaque aléa est amorcé par une
graine **dérivée d'un digest explicite** — jamais du `hash` intégré, qui est
randomisé par processus (le piège est raconté dans `docs/memoire/pieges.md`).
"""

from __future__ import annotations

import math
import random
import zlib
from dataclasses import dataclass

GRAINE = 20261119


def graine(nom: str) -> int:
    """Graine stable dérivée d'un nom, par CRC32 — identique d'un processus à l'autre."""
    return (GRAINE ^ zlib.crc32(nom.encode("utf-8"))) & 0x7FFFFFFF


def rng(nom: str) -> random.Random:
    return random.Random(graine(nom))


# ---------------------------------------------------------------------------
# Lois
# ---------------------------------------------------------------------------

def phi(z: float) -> float:
    return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def Phi(z: float) -> float:
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


def Phi_inv(p: float) -> float:
    """Quantile normal (Acklam), raffiné d'un pas de Halley : erreur < 1e-12."""
    if not 0.0 < p < 1.0:
        raise ValueError(p)
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    lo = 0.02425
    if p < lo:
        q = math.sqrt(-2 * math.log(p))
        x = (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
            ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    elif p <= 1 - lo:
        q = p - 0.5
        r = q * q
        x = (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
            (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    else:
        q = math.sqrt(-2 * math.log(1 - p))
        x = -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
            ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    e = Phi(x) - p
    u = e * math.sqrt(2 * math.pi) * math.exp(x * x / 2)
    return x - u / (1 + x * u / 2)


def p_bilateral(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2.0))


def lbeta(a: float, b: float) -> float:
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def logsumexp(xs) -> float:
    xs = [x for x in xs if x != -math.inf]
    if not xs:
        return -math.inf
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


# ---------------------------------------------------------------------------
# Descriptif
# ---------------------------------------------------------------------------

def moyenne(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs)


def variance(xs) -> float:
    xs = list(xs)
    m = sum(xs) / len(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def quantile(xs, q: float) -> float:
    s = sorted(xs)
    if not s:
        raise ValueError("vide")
    pos = q * (len(s) - 1)
    i = int(math.floor(pos))
    j = min(i + 1, len(s) - 1)
    return s[i] + (s[j] - s[i]) * (pos - i)


def correlation(xs, ys) -> float:
    xs, ys = list(xs), list(ys)
    mx, my = moyenne(xs), moyenne(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy)


# ---------------------------------------------------------------------------
# Algèbre linéaire minimale
# ---------------------------------------------------------------------------

def inverse(m: list[list[float]]) -> list[list[float]]:
    """Gauss-Jordan avec pivot partiel. Lève si la matrice est singulière."""
    n = len(m)
    a = [list(row) + [1.0 if i == j else 0.0 for j in range(n)]
         for i, row in enumerate(m)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[piv][col]) < 1e-14:
            raise ZeroDivisionError("matrice singulière")
        a[col], a[piv] = a[piv], a[col]
        p = a[col][col]
        a[col] = [v / p for v in a[col]]
        for r in range(n):
            if r != col and a[r][col] != 0.0:
                f = a[r][col]
                ar, ac = a[r], a[col]
                a[r] = [x - f * y for x, y in zip(ar, ac)]
    return [row[n:] for row in a]


def _sandwich(bread: list[list[float]], scores: dict, n_groupes: int,
              n_obs: int, k: int) -> list[list[float]]:
    meat = [[0.0] * k for _ in range(k)]
    for s in scores.values():
        for i in range(k):
            si = s[i]
            if si == 0.0:
                continue
            row = meat[i]
            for j in range(k):
                row[j] += si * s[j]
    g = n_groupes
    corr = (g / (g - 1.0)) * ((n_obs - 1.0) / (n_obs - k)) if g > 1 else 1.0
    tmp = [[sum(bread[i][l] * meat[l][j] for l in range(k)) for j in range(k)]
           for i in range(k)]
    return [[corr * sum(tmp[i][l] * bread[l][j] for l in range(k)) for j in range(k)]
            for i in range(k)]


@dataclass
class Ajustement:
    noms: list[str]
    coef: list[float]
    se: list[float]
    n: int
    groupes: int

    def z(self, nom: str) -> float:
        i = self.noms.index(nom)
        return self.coef[i] / self.se[i]

    def p(self, nom: str) -> float:
        return p_bilateral(self.z(nom))

    def b(self, nom: str) -> float:
        return self.coef[self.noms.index(nom)]

    def e(self, nom: str) -> float:
        return self.se[self.noms.index(nom)]

    def ic(self, nom: str, niveau: float = 0.95) -> tuple[float, float]:
        q = Phi_inv(0.5 + niveau / 2)
        b, s = self.b(nom), self.e(nom)
        return b - q * s, b + q * s


def logit(X: list[list[float]], y: list[float], noms: list[str],
          grappes: list | None = None, iterations: int = 60) -> Ajustement:
    """Régression logistique par IRLS, écarts-types robustes par grappe.

    Sans grappe, chaque observation est sa propre grappe (sandwich HC0 corrigé).
    Une décision de speed dating n'est pas indépendante de la suivante du même
    décideur : les grappes sont alors les décideurs, sinon l'écart-type ment.
    """
    n, k = len(X), len(X[0])
    beta = [0.0] * k
    for _ in range(iterations):
        grad = [0.0] * k
        hess = [[0.0] * k for _ in range(k)]
        for xi, yi in zip(X, y):
            eta = sum(b * x for b, x in zip(beta, xi))
            p = 1.0 / (1.0 + math.exp(-eta)) if eta > -700 else 0.0
            w = p * (1.0 - p)
            r = yi - p
            for a in range(k):
                xa = xi[a]
                if xa == 0.0:
                    continue
                grad[a] += xa * r
                ha = hess[a]
                wxa = w * xa
                for c in range(a, k):
                    ha[c] += wxa * xi[c]
        for a in range(k):
            for c in range(a):
                hess[a][c] = hess[c][a]
        inv = inverse(hess)
        pas = [sum(inv[a][c] * grad[c] for c in range(k)) for a in range(k)]
        beta = [b + s for b, s in zip(beta, pas)]
        if max(abs(s) for s in pas) < 1e-10:
            break
    scores: dict = {}
    for idx, (xi, yi) in enumerate(zip(X, y)):
        eta = sum(b * x for b, x in zip(beta, xi))
        p = 1.0 / (1.0 + math.exp(-eta))
        g = grappes[idx] if grappes is not None else idx
        s = scores.setdefault(g, [0.0] * k)
        r = yi - p
        for a in range(k):
            s[a] += xi[a] * r
    v = _sandwich(inv, scores, len(scores), n, k)
    return Ajustement(noms, beta, [math.sqrt(max(v[i][i], 0.0)) for i in range(k)],
                      n, len(scores))


def mco(X: list[list[float]], y: list[float], noms: list[str],
        grappes: list | None = None) -> Ajustement:
    """Moindres carrés ordinaires, écarts-types robustes (par grappe si donnée)."""
    n, k = len(X), len(X[0])
    xtx = [[0.0] * k for _ in range(k)]
    xty = [0.0] * k
    for xi, yi in zip(X, y):
        for a in range(k):
            xa = xi[a]
            if xa == 0.0:
                continue
            xty[a] += xa * yi
            for c in range(k):
                xtx[a][c] += xa * xi[c]
    inv = inverse(xtx)
    beta = [sum(inv[a][c] * xty[c] for c in range(k)) for a in range(k)]
    scores: dict = {}
    for idx, (xi, yi) in enumerate(zip(X, y)):
        r = yi - sum(b * x for b, x in zip(beta, xi))
        g = grappes[idx] if grappes is not None else idx
        s = scores.setdefault(g, [0.0] * k)
        for a in range(k):
            s[a] += xi[a] * r
    v = _sandwich(inv, scores, len(scores), n, k)
    return Ajustement(noms, beta, [math.sqrt(max(v[i][i], 0.0)) for i in range(k)],
                      n, len(scores))


# ---------------------------------------------------------------------------
# Tests élémentaires
# ---------------------------------------------------------------------------

@dataclass
class Ecart:
    """Un écart de proportions ou de moyennes, avec son incertitude."""
    a: float
    b: float
    na: int
    nb: int
    diff: float
    se: float

    @property
    def z(self) -> float:
        return self.diff / self.se if self.se > 0 else 0.0

    @property
    def p(self) -> float:
        return p_bilateral(self.z)

    @property
    def relatif(self) -> float:
        return self.diff / self.b if self.b else math.nan

    def ic(self, niveau: float = 0.95) -> tuple[float, float]:
        q = Phi_inv(0.5 + niveau / 2)
        return self.diff - q * self.se, self.diff + q * self.se


def deux_proportions(xa: int, na: int, xb: int, nb: int) -> Ecart:
    """A contre B (référence). Écart-type non poolé, pour l'intervalle."""
    pa, pb = xa / na, xb / nb
    se = math.sqrt(pa * (1 - pa) / na + pb * (1 - pb) / nb)
    return Ecart(pa, pb, na, nb, pa - pb, se)


def deux_moyennes(a: list[float], b: list[float]) -> Ecart:
    ma, mb = moyenne(a), moyenne(b)
    se = math.sqrt(variance(a) / len(a) + variance(b) / len(b))
    return Ecart(ma, mb, len(a), len(b), ma - mb, se)


def permutation(y: list[float], g: list[int], strates: list | None = None,
                tirages: int = 2000, nom: str = "perm") -> tuple[float, float, list[float]]:
    """Écart de moyennes entre g=1 et g=0, et sa loi nulle par permutation.

    Les étiquettes sont permutées **à l'intérieur de chaque strate** : la loi
    nulle conserve ce qui ne doit pas bouger (la vague, le décideur, le mois),
    et ne détruit que le lien testé. Rend (écart observé, p bilatéral, loi nulle).
    """
    alea = rng(nom)
    if strates is None:
        strates = [0] * len(y)
    blocs: dict = {}
    for i, s in enumerate(strates):
        blocs.setdefault(s, []).append(i)

    def ecart(lab: list[int]) -> float:
        s1 = s0 = n1 = n0 = 0.0
        for yi, li in zip(y, lab):
            if li:
                s1 += yi
                n1 += 1
            else:
                s0 += yi
                n0 += 1
        return s1 / n1 - s0 / n0

    obs = ecart(g)
    nul = []
    lab = list(g)
    for _ in range(tirages):
        for idx in blocs.values():
            vals = [lab[i] for i in idx]
            alea.shuffle(vals)
            for i, v in zip(idx, vals):
                lab[i] = v
        nul.append(ecart(lab))
    extremes = sum(1 for v in nul if abs(v) >= abs(obs) - 1e-15)
    return obs, (extremes + 1) / (tirages + 1), nul


def bh(pvals: list[float]) -> list[float]:
    """Valeurs q de Benjamini-Hochberg (taux de fausses découvertes)."""
    m = len(pvals)
    ordre = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m
    courant = 1.0
    for rang in range(m, 0, -1):
        i = ordre[rang - 1]
        courant = min(courant, pvals[i] * m / rang)
        q[i] = courant
    return q


def rayleigh(angles: list[float]) -> tuple[float, float, float]:
    """Test de Rayleigh d'uniformité circulaire : (R moyen, direction, p).

    La loi nulle d'un rythme est l'horloge uniforme : un fan qui écrit à toute
    heure n'a pas d'heure. p approché au second ordre (Zar, 1999).
    """
    n = len(angles)
    c = sum(math.cos(a) for a in angles) / n
    s = sum(math.sin(a) for a in angles) / n
    rbar = math.hypot(c, s)
    z = n * rbar * rbar
    p = math.exp(math.sqrt(1 + 4 * n + 4 * (n * n - (n * rbar) ** 2)) - (1 + 2 * n))
    return rbar, math.atan2(s, c), min(1.0, max(p, 0.0))


# ---------------------------------------------------------------------------
# Optimisation
# ---------------------------------------------------------------------------

def nelder_mead(f, x0: list[float], pas: float = 0.5, tol: float = 1e-10,
                iterations: int = 4000) -> tuple[list[float], float]:
    n = len(x0)
    simplex = [list(x0)]
    for i in range(n):
        x = list(x0)
        x[i] += pas
        simplex.append(x)
    vals = [f(x) for x in simplex]
    for _ in range(iterations):
        ordre = sorted(range(n + 1), key=lambda i: vals[i])
        simplex = [simplex[i] for i in ordre]
        vals = [vals[i] for i in ordre]
        if abs(vals[-1] - vals[0]) < tol * (1 + abs(vals[0])):
            break
        centre = [sum(simplex[i][j] for i in range(n)) / n for j in range(n)]
        pire = simplex[-1]
        xr = [c + (c - p) for c, p in zip(centre, pire)]
        fr = f(xr)
        if fr < vals[0]:
            xe = [c + 2 * (c - p) for c, p in zip(centre, pire)]
            fe = f(xe)
            simplex[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            simplex[-1], vals[-1] = xr, fr
        else:
            xc = [c + 0.5 * (p - c) for c, p in zip(centre, pire)]
            fc = f(xc)
            if fc < vals[-1]:
                simplex[-1], vals[-1] = xc, fc
            else:
                meilleur = simplex[0]
                simplex = [meilleur] + [[m + 0.5 * (x - m) for m, x in zip(meilleur, s)]
                                        for s in simplex[1:]]
                vals = [vals[0]] + [f(x) for x in simplex[1:]]
    i = min(range(n + 1), key=lambda i: vals[i])
    return simplex[i], vals[i]


# ---------------------------------------------------------------------------
# Budget d'information
# ---------------------------------------------------------------------------

def n_par_bras(p0: float, hausse_relative: float, alpha: float = 0.05,
               puissance: float = 0.80) -> float:
    """Envois par variante pour détecter p0 → p0·(1+h), test bilatéral."""
    p1 = p0 * (1.0 + hausse_relative)
    za, zb = Phi_inv(1 - alpha / 2), Phi_inv(puissance)
    pm = (p0 + p1) / 2
    num = (za * math.sqrt(2 * pm * (1 - pm)) + zb * math.sqrt(p0 * (1 - p0) + p1 * (1 - p1))) ** 2
    return num / (p1 - p0) ** 2


def effet_detectable(n: float, p0: float, alpha: float = 0.05,
                     puissance: float = 0.80) -> float:
    """Hausse relative minimale détectable avec n envois par variante."""
    lo, hi = 1e-4, 50.0
    for _ in range(100):
        mid = math.sqrt(lo * hi)
        if n_par_bras(p0, mid, alpha, puissance) > n:
            lo = mid
        else:
            hi = mid
    return hi
