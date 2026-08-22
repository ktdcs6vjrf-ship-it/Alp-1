"""Deux mesures venues d'ailleurs : entropie de permutation, et DFA.

Le document mesure la mémoire d'un prix par ratio de variance, qui suppose
une structure linéaire — il détecte l'autocorrélation, et rien d'autre. Un
prix peut être imprévisible au second ordre et parfaitement structuré par
ailleurs : le ratio de variance ne le verrait pas. Deux instruments d'autres
disciplines comblent l'angle mort, et tous deux tournent sur les mêmes barres
d'une minute, sans un octet de données supplémentaire.

**L'entropie de permutation** (Bandt et Pompe, 2002) vient de l'analyse des
signaux non linéaires, où elle sert à l'électroencéphalographie. Elle
n'examine pas les valeurs mais leur **ordre** : pour chaque fenêtre de `d`
points consécutifs, on note lequel est le plus grand, lequel vient ensuite,
et ainsi de suite. Il y a `d!` ordres possibles ; leur entropie de Shannon,
normalisée, vaut 1 si tous sont équiprobables et moins dès qu'un motif
revient plus souvent que le hasard ne le voudrait.

Sa vertu est qu'elle ne suppose rien. Aucune loi, aucune stationnarité,
aucune linéarité, et elle est invariante par toute transformation monotone
du prix — le résultat ne change pas si l'on mesure en points, en pourcentage
ou en logarithme. Ce qu'elle mesure est la seule chose qui compte avant de
construire un signal : reste-t-il, dans cette série, une structure
exploitable par quiconque ?

**L'analyse des fluctuations redressées** (Peng et al., 1994) vient de la
physiologie, où elle a servi à mesurer la mémoire longue du rythme cardiaque
et des séquences d'ADN. Elle estime le même exposant d'échelle que le ratio
de variance, mais en retranchant la tendance locale de chaque fenêtre avant
de mesurer la fluctuation — ce qui la rend robuste à la non-stationnarité,
précisément là où le ratio de variance se trompe.

Les deux se comparent à leur loi nulle simulée, comme tout le reste du
document. C'est indispensable : l'entropie de permutation d'un échantillon
fini est **inférieure à 1** même sur une série parfaitement aléatoire, parce
que les `d!` motifs ne peuvent pas être équiprobables dans un tirage fini.
Lue sans sa loi nulle, elle annonce une structure qui n'existe pas.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from .dataset import Session
from .mc import Rng
from .varratio import _segments

LN2 = math.log(2.0)

#: Longueur des motifs ordinaux. Trois donne six motifs, quatre en donne
#: vingt-quatre : au-delà, le nombre d'observations par motif s'effondre et
#: le biais d'échantillon fini domine.
EMBED = (3, 4)


def _ordinal(window: tuple[float, ...]) -> tuple[int, ...]:
    """Le motif ordinal d'une fenêtre : le rang de chaque position."""
    return tuple(sorted(range(len(window)), key=lambda i: window[i]))


def permutation_counts(series: list[float], d: int) -> dict[tuple[int, ...], int]:
    """Fréquence de chaque motif ordinal de longueur `d`."""
    if d < 2:
        raise ValueError("d doit être ≥ 2")
    out: dict[tuple[int, ...], int] = {}
    for i in range(len(series) - d + 1):
        k = _ordinal(tuple(series[i:i + d]))
        out[k] = out.get(k, 0) + 1
    return out


@dataclass(frozen=True)
class Permutation:
    """Entropie de permutation d'une série, et ce qu'elle laisse ouvert."""

    d: int
    entropy: float          # normalisée, dans [0, 1]
    n_windows: int
    n_patterns: int

    @property
    def deficit(self) -> float:
        """Ce qui manque à l'aléa parfait, en bits par fenêtre.

        C'est le plafond de ce qu'un signal fondé sur la forme du prix peut
        extraire : au-delà, il n'y a rien à prendre. La comparaison avec le
        seuil d'`alp1.entropy` est directe, les deux étant en bits.
        """
        return (1.0 - self.entropy) * math.log2(math.factorial(self.d))


def permutation_entropy(sessions: list[Session], d: int = 3) -> Permutation:
    """Entropie de permutation normalisée des rendements, séance par séance.

    Les motifs sont comptés à l'intérieur de chaque segment continu, jamais à
    cheval sur un trou ni sur une frontière de séance — même règle que pour
    le ratio de variance, et pour la même raison.
    """
    if d < 2:
        raise ValueError("d doit être ≥ 2")
    total: dict[tuple[int, ...], int] = {}
    n = 0
    for seg in (s for sess in sessions for s in _segments(sess)):
        if len(seg) < d:
            continue
        for k, c in permutation_counts(seg, d).items():
            total[k] = total.get(k, 0) + c
            n += c
    if n == 0:
        raise ValueError("aucun segment assez long pour cette longueur de motif")
    h = -sum((c / n) * math.log(c / n) for c in total.values()) / LN2
    return Permutation(d=d, entropy=h / math.log2(math.factorial(d)),
                       n_windows=n, n_patterns=len(total))


@dataclass(frozen=True)
class NullPermutation:
    """Loi de l'entropie de permutation sous absence totale de structure."""

    d: int
    mean: float
    sd: float
    q05: float
    draws: int

    def z(self, observed: float) -> float:
        return (observed - self.mean) / self.sd if self.sd > 0 else math.nan

    def structured(self, observed: float) -> bool:
        """Sous le quantile 5 % de la loi nulle : structure détectée."""
        return observed < self.q05


@lru_cache(maxsize=32)
def null_permutation(d: int = 3, n_sessions: int = 250, draws: int = 20,
                     seed: int = 20260821) -> NullPermutation:
    """Entropie de permutation attendue d'une série sans aucune structure.

    Elle vaut **moins de un**, et c'est tout l'intérêt de la mesurer : les
    ``d!`` motifs ne peuvent pas être équiprobables dans un échantillon fini,
    de sorte qu'une série parfaitement aléatoire affiche un déficit
    d'entropie. Le prendre pour de la structure serait l'erreur que ce module
    existe pour empêcher.

    Mémorisée par ses arguments : elle ne dépend que de la longueur de séance
    et de la longueur de motif, jamais des données mesurées, et le document
    l'appelle une dizaine de fois par assemblage.
    """
    from .dataset import synthetic_sessions
    if draws < 2:
        raise ValueError("draws doit être ≥ 2")
    vals = []
    for k in range(draws):
        sess = synthetic_sessions(n_sessions, seed=seed + k * 7919)
        vals.append(permutation_entropy(sess, d).entropy)
    m = sum(vals) / len(vals)
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
    vals.sort()
    q05 = vals[max(0, int(0.05 * len(vals)) - 1)]
    return NullPermutation(d=d, mean=m, sd=sd, q05=q05, draws=len(vals))


# --- Analyse des fluctuations redressées ------------------------------------


def _detrended_fluctuation(profile: list[float], scale: int) -> float:
    """Fluctuation résiduelle après retrait de la tendance linéaire locale."""
    n = len(profile) // scale
    if n < 1:
        return math.nan
    total = 0.0
    for b in range(n):
        seg = profile[b * scale:(b + 1) * scale]
        m = scale
        sx = (m - 1) * m / 2.0
        sxx = (m - 1) * m * (2 * m - 1) / 6.0
        sy = sum(seg)
        sxy = sum(i * v for i, v in enumerate(seg))
        det = m * sxx - sx * sx
        if det == 0:
            continue
        a = (m * sxy - sx * sy) / det
        b0 = (sy - a * sx) / m
        total += sum((v - (a * i + b0)) ** 2 for i, v in enumerate(seg)) / m
    return math.sqrt(total / n) if n else math.nan


@dataclass(frozen=True)
class DFA:
    """Exposant d'échelle par analyse des fluctuations redressées."""

    alpha: float
    r2: float
    points: tuple[tuple[int, float], ...]

    @property
    def diffusive(self) -> bool:
        return abs(self.alpha - 0.5) < 0.02


def dfa(sessions: list[Session],
        scales: tuple[int, ...] = (8, 16, 32, 64, 128)) -> DFA:
    """Exposant d'échelle robuste à la tendance locale.

    Le profil est la somme cumulée des rendements centrés ; à chaque échelle,
    la tendance linéaire est retirée fenêtre par fenêtre avant de mesurer la
    fluctuation résiduelle. La pente de ``ln F(n)`` contre ``ln n`` est
    l'exposant.

    C'est la raison d'être de la méthode : une dérive locale — une saisonnalité
    intraséance, une tendance de séance — gonfle le ratio de variance et lui
    fait annoncer de la persistance. Le redressement la retire.
    """
    segs = [s for sess in sessions for s in _segments(sess)]
    if not segs:
        raise ValueError("aucun segment exploitable")
    pts = []
    for n in scales:
        fs = []
        for seg in segs:
            if len(seg) < 2 * n:
                continue
            mu = sum(seg) / len(seg)
            prof, acc = [], 0.0
            for v in seg:
                acc += v - mu
                prof.append(acc)
            f = _detrended_fluctuation(prof, n)
            if f == f and f > 0:
                fs.append(f)
        if fs:
            pts.append((n, sum(fs) / len(fs)))
    if len(pts) < 3:
        raise ValueError("trop peu d'échelles exploitables")

    xs = [math.log(n) for n, _ in pts]
    ys = [math.log(f) for _, f in pts]
    k = len(pts)
    mx, my = sum(xs) / k, sum(ys) / k
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    inter = my - slope * mx
    sst = sum((y - my) ** 2 for y in ys)
    ssr = sum((y - (inter + slope * x)) ** 2 for x, y in zip(xs, ys))
    return DFA(alpha=slope, r2=1.0 - ssr / sst if sst > 0 else 1.0,
               points=tuple(pts))


@lru_cache(maxsize=32)
def null_dfa(n_sessions: int = 250, draws: int = 12,
             seed: int = 20260821,
             scales: tuple[int, ...] = (8, 16, 32, 64, 128)) -> tuple[float, float]:
    """Exposant DFA attendu sous marche aléatoire : (moyenne, écart-type)."""
    from .dataset import synthetic_sessions
    if draws < 2:
        raise ValueError("draws doit être ≥ 2")
    vals = [dfa(synthetic_sessions(n_sessions, seed=seed + k * 7919),
                scales).alpha for k in range(draws)]
    m = sum(vals) / len(vals)
    return m, math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
