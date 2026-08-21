"""Simulation de Monte-Carlo, ré-échantillonnage et tests de permutation.

Le Monte-Carlo n'est pas ici un substitut au calcul : toutes les grandeurs
centrales du papier ont une forme fermée. Il sert à trois choses que la forme
fermée ne fait pas.

**Il donne des lois, pas des moyennes.** `E[MDD]` se calcule ; la probabilité
qu'un drawdown dépasse `D` sur exactement `N` trades, non — c'est le
quantile qui décide de l'allocation, pas l'espérance.

**Il vérifie les formes fermées.** Chaque identité du module est confrontée à
sa simulation dans la suite de tests ; un écart signale une erreur d'algèbre,
et c'est le seul contrôle qui ne partage pas les hypothèses de la dérivation.

**Il produit la loi nulle empirique** des statistiques qui n'en ont pas —
Sharpe maximal sur `k` essais, drawdown maximal, durée sous les eaux — et
c'est cette loi nulle qui décide si un backtest est un edge ou un artefact.

Le générateur est déterministe et ensemencé explicitement : deux exécutions
du dépôt produisent le même papier, au bit près. Une simulation dont la graine
n'est pas publiée n'est pas un résultat, c'est une anecdote.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .drawdown import drawdown_series, equity_curve
from .pathstats import TradeLaw


# --- Générateur reproductible ----------------------------------------------


class Rng:
    """SplitMix64 : générateur déterministe, rapide, sans dépendance.

    Un état de 64 bits, un mélange avalanche à chaque tirage. Sa période est
    de 2⁶⁴ et il passe les tests usuels d'uniformité — largement au-delà de ce
    qu'exige la production de figures et de quantiles à trois décimales. Le
    point qui compte n'est pas la qualité statistique mais la
    **reproductibilité** : la même graine donne la même simulation, sur toute
    machine et à toute date.
    """

    _MASK = (1 << 64) - 1

    def __init__(self, seed: int = 20260821) -> None:
        self._s = seed & self._MASK
        self._spare: float | None = None

    def next_u64(self) -> int:
        self._s = (self._s + 0x9E3779B97F4A7C15) & self._MASK
        z = self._s
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & self._MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & self._MASK
        return z ^ (z >> 31)

    def uniform(self) -> float:
        """Uniforme sur [0, 1) — 53 bits de mantisse, comme un double."""
        return (self.next_u64() >> 11) * (1.0 / (1 << 53))

    def gauss(self) -> float:
        """Normale centrée réduite, par Box-Muller avec réserve."""
        if self._spare is not None:
            out, self._spare = self._spare, None
            return out
        u1 = max(self.uniform(), 1e-300)
        u2 = self.uniform()
        r = math.sqrt(-2.0 * math.log(u1))
        self._spare = r * math.sin(2.0 * math.pi * u2)
        return r * math.cos(2.0 * math.pi * u2)

    def randint(self, n: int) -> int:
        """Entier uniforme dans [0, n)."""
        if n <= 0:
            raise ValueError("n doit être > 0")
        return self.next_u64() % n


# --- Tirage dans la loi d'un trade -----------------------------------------


def _cumulative(law: TradeLaw) -> tuple[list[float], list[float]]:
    order = sorted(zip(law.values, law.probs))
    vals, acc, total = [], [], 0.0
    for v, p in order:
        total += p
        vals.append(v)
        acc.append(total)
    acc[-1] = 1.0
    return vals, acc


def draw(law: TradeLaw, rng: Rng) -> float:
    """Un tirage dans la loi, par inversion de la fonction de répartition."""
    vals, acc = _cumulative(law)
    u = rng.uniform()
    for v, a in zip(vals, acc):
        if u <= a:
            return v
    return vals[-1]


def sample(law: TradeLaw, n: int, rng: Rng) -> list[float]:
    """`n` résultats de trade indépendants, en unités de risque `R`."""
    vals, acc = _cumulative(law)

    def one() -> float:
        u = rng.uniform()
        for v, a in zip(vals, acc):
            if u <= a:
                return v
        return vals[-1]

    return [one() for _ in range(n)]


# --- Simulation de trajectoires --------------------------------------------


@dataclass(frozen=True)
class PathSummary:
    """Résumé d'une trajectoire simulée, en unités de risque `R`."""

    terminal: float
    max_drawdown: float
    sharpe: float
    time_under_water: float


def simulate(law: TradeLaw, n_trades: int, n_paths: int,
             rng: Rng | None = None) -> list[PathSummary]:
    """`n_paths` trajectoires indépendantes de `n_trades` trades chacune."""
    rng = rng or Rng()
    out: list[PathSummary] = []
    for _ in range(n_paths):
        rets = sample(law, n_trades, rng)
        curve = equity_curve(rets)
        dd = drawdown_series(curve)
        mean = sum(rets) / n_trades
        var = sum((r - mean) ** 2 for r in rets) / max(n_trades - 1, 1)
        sd = math.sqrt(var)
        under = sum(1 for d in dd if d > 1e-12) / len(dd)
        out.append(PathSummary(
            terminal=curve[-1],
            max_drawdown=max(dd),
            sharpe=(mean / sd if sd > 0 else 0.0),
            time_under_water=under,
        ))
    return out


def quantile(values: list[float], q: float) -> float:
    """Quantile empirique par interpolation linéaire entre ordres."""
    if not values:
        raise ValueError("échantillon vide")
    if not 0.0 <= q <= 1.0:
        raise ValueError("q doit être dans [0, 1]")
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    pos = q * (len(s) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(s) - 1)
    frac = pos - lo
    return s[lo] * (1.0 - frac) + s[hi] * frac


def fan(law: TradeLaw, n_trades: int, n_paths: int, levels: tuple[float, ...],
        rng: Rng | None = None, step: int = 1) -> dict[float, list[float]]:
    """Faisceau de quantiles de la courbe d'équité, trade par trade.

    Retourne, pour chaque niveau demandé, la trajectoire du quantile
    correspondant. C'est la représentation honnête d'un backtest : non pas
    *une* courbe, mais l'enveloppe des courbes que le même processus peut
    produire — dont celle qu'on a effectivement observée n'est qu'un tirage.
    """
    rng = rng or Rng()
    curves = [equity_curve(sample(law, n_trades, rng)) for _ in range(n_paths)]
    idx = list(range(0, n_trades + 1, step))
    if idx[-1] != n_trades:
        idx.append(n_trades)
    out: dict[float, list[float]] = {lv: [] for lv in levels}
    for i in idx:
        column = [c[i] for c in curves]
        for lv in levels:
            out[lv].append(quantile(column, lv))
    return out


def fan_index(n_trades: int, step: int = 1) -> list[int]:
    """Abscisses correspondant aux colonnes produites par `fan`."""
    idx = list(range(0, n_trades + 1, step))
    if idx[-1] != n_trades:
        idx.append(n_trades)
    return idx


# --- Ré-échantillonnage -----------------------------------------------------


def iid_bootstrap(data: list[float], rng: Rng, n: int | None = None) -> list[float]:
    """Bootstrap élémentaire : tirage avec remise, indépendance supposée.

    Correct pour des trades effectivement indépendants ; il **détruit** toute
    dépendance sérielle, et sous-estime donc l'incertitude d'une stratégie
    dont les positions se chevauchent ou dont les régimes persistent.
    """
    n = n or len(data)
    return [data[rng.randint(len(data))] for _ in range(n)]


def stationary_bootstrap(data: list[float], rng: Rng, mean_block: float,
                         n: int | None = None) -> list[float]:
    """Bootstrap stationnaire de Politis & Romano (1994).

    Blocs de longueur géométrique de moyenne `mean_block`, recollés en boucle
    sur la série. À la différence du bootstrap par blocs de longueur fixe, la
    série ré-échantillonnée est **stationnaire**, ce qui rend les quantiles
    obtenus interprétables sans correction de bord.

    C'est le ré-échantillonnage à retenir dès que les rendements sont
    autocorrélés — ce qu'ils sont dès que `H ≠ ½`, c'est-à-dire dans toute
    l'hypothèse de persistance sur laquelle repose ce papier.
    """
    if not data:
        raise ValueError("échantillon vide")
    if mean_block <= 0:
        raise ValueError("mean_block doit être > 0")
    n = n or len(data)
    p = 1.0 / mean_block
    out: list[float] = []
    i = rng.randint(len(data))
    while len(out) < n:
        out.append(data[i])
        if rng.uniform() < p:
            i = rng.randint(len(data))
        else:
            i = (i + 1) % len(data)
    return out


def block_length_for_autocorrelation(rho: float) -> float:
    """Longueur de bloc moyenne conseillée pour un AR(1) de coefficient `ρ`.

    La règle usuelle prend la longueur de bloc de l'ordre du temps de
    décorrélation `−1/ln|ρ|`, arrondi vers le haut : au-delà, l'information
    sur la dépendance est conservée ; en deçà, le bootstrap la casse.
    """
    if abs(rho) < 1e-9:
        return 1.0
    if abs(rho) >= 1.0:
        raise ValueError("rho doit être dans ]−1, 1[")
    return max(1.0, -1.0 / math.log(abs(rho)))


# --- Tests de randomisation -------------------------------------------------


def sign_permutation_pvalue(returns: list[float], rng: Rng,
                            n_draws: int = 2000) -> float:
    """p-valeur du test de signes randomisés sur la moyenne.

    Chaque rendement voit son signe tiré à pile ou face ; la loi nulle
    engendrée est celle d'une stratégie qui aurait pris les mêmes positions
    dans un sens aléatoire. La p-valeur est la fréquence des moyennes
    simulées au moins aussi grandes que l'observée.

    Ce test ne suppose **ni normalité ni indépendance des amplitudes** : il ne
    randomise que la direction, ce qui est exactement l'hypothèse « la pile de
    couches ne prédit pas le sens ».
    """
    if not returns:
        raise ValueError("échantillon vide")
    observed = sum(returns) / len(returns)
    hits = 0
    for _ in range(n_draws):
        total = 0.0
        for r in returns:
            total += r if rng.next_u64() & 1 else -r
        if total / len(returns) >= observed:
            hits += 1
    return (hits + 1) / (n_draws + 1)


def null_best_sharpe(law: TradeLaw, n_trades: int, n_trials: int,
                     n_draws: int, rng: Rng | None = None) -> list[float]:
    """Loi du **meilleur** Sharpe sur `n_trials` essais sans edge.

    C'est la loi nulle correcte pour un backtest sélectionné : on ne publie
    jamais un jeu de paramètres tiré au hasard, on publie le meilleur d'un
    ensemble. Comparer le Sharpe retenu à la loi du Sharpe d'un essai unique
    est l'erreur d'inférence la plus répandue de la profession, et cette
    fonction en donne la mesure directe.
    """
    rng = rng or Rng()
    out: list[float] = []
    for _ in range(n_draws):
        best = -math.inf
        for _ in range(n_trials):
            rets = sample(law, n_trades, rng)
            mean = sum(rets) / n_trades
            var = sum((r - mean) ** 2 for r in rets) / max(n_trades - 1, 1)
            sd = math.sqrt(var)
            best = max(best, mean / sd if sd > 0 else 0.0)
        out.append(best)
    return out
