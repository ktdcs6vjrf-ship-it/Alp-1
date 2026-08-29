"""Modèle de friction et arithmétique d'équilibre pour ALP-1.

Le point central de ce module : sur un stop de quelques ticks, la friction
(commission + spread + slippage) n'est pas une correction du second ordre,
elle domine l'économie du trade. Toutes les formules ci-dessous expriment
la friction en fraction du risque nominal, `c/L`, qui est le seul ratio
qui compte.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Contract:
    """Spécification d'un contrat futures.

    `point_value` est la valeur monétaire d'un point d'indice pour 1 contrat,
    `tick_size` le pas de cotation en points.
    """

    symbol: str
    point_value: float
    tick_size: float
    typical_spread_ticks: float = 1.0

    @property
    def tick_value(self) -> float:
        return self.point_value * self.tick_size

    def ticks(self, points: float) -> float:
        return points / self.tick_size

    def round_to_tick(self, points: float) -> float:
        """Arrondit une distance en points au tick représentable le plus proche."""
        return round(points / self.tick_size) * self.tick_size


# Spécifications au 2026. `typical_spread_ticks` = largeur bid/ask en RTH.
ES = Contract("ES", point_value=50.0, tick_size=0.25, typical_spread_ticks=1.0)
NQ = Contract("NQ", point_value=20.0, tick_size=0.25, typical_spread_ticks=1.0)
MES = Contract("MES", point_value=5.0, tick_size=0.25, typical_spread_ticks=1.0)
MNQ = Contract("MNQ", point_value=2.0, tick_size=0.25, typical_spread_ticks=1.0)

CONTRACTS = {c.symbol: c for c in (ES, NQ, MES, MNQ)}


@dataclass(frozen=True)
class CostModel:
    """Friction par aller-retour, en dollars et par contrat.

    Parameters
    ----------
    commission_rt:
        Commission + frais exchange + NFA, aller-retour. Retail : 2.00–4.50 $
        sur ES, ~0.75–1.50 $ sur les micros.
    entry_slippage_ticks:
        Ticks payés à l'entrée. 0.0 si l'entrée est passive (ordre limite dans
        la zone OTE qui est *touchée*), 0.5–1.0 si entrée au marché.
    exit_slippage_ticks:
        Ticks payés à la sortie. Un stop est un ordre marché : on paie au
        minimum la moitié du spread, et davantage sur le mouvement même qui
        déclenche le stop. 1.0 est optimiste en momentum.
    """

    commission_rt: float = 4.00
    entry_slippage_ticks: float = 0.0
    exit_slippage_ticks: float = 1.0

    def friction_usd(self, contract: Contract) -> float:
        slip_ticks = self.entry_slippage_ticks + self.exit_slippage_ticks
        return self.commission_rt + slip_ticks * contract.tick_value

    def friction_points(self, contract: Contract) -> float:
        return self.friction_usd(contract) / contract.point_value


# Trois scénarios d'exécution, du plus optimiste au plus réaliste.
COST_OPTIMISTIC = CostModel(commission_rt=2.00, entry_slippage_ticks=0.0, exit_slippage_ticks=0.5)
COST_BASE = CostModel(commission_rt=4.00, entry_slippage_ticks=0.0, exit_slippage_ticks=1.0)
COST_REALISTIC = CostModel(commission_rt=4.00, entry_slippage_ticks=0.5, exit_slippage_ticks=1.5)


def stop_points(index_level: float, stop_pct: float) -> float:
    """Convertit un stop exprimé en pourcentage du niveau d'indice en points.

    `stop_pct` est en pourcentage : 0.01 signifie 0.01 % (soit 1 point de base).
    """
    return index_level * stop_pct / 100.0


def breakeven_hit_rate(reward_risk: float, friction_ratio: float) -> float:
    """Hit rate d'équilibre p* pour un R:R donné et une friction c/L.

    Gain net d'un gagnant  : R·L − c
    Perte nette d'un perdant : L + c

    p(R·L − c) = (1−p)(L + c)  =>  p* = (1 + c/L) / (R + 1)

    Retourne une valeur > 1 si aucun hit rate ne peut compenser la friction.
    """
    if reward_risk <= 0:
        raise ValueError("reward_risk doit être > 0")
    return (1.0 + friction_ratio) / (reward_risk + 1.0)


def expectancy_r(hit_rate: float, reward_risk: float, friction_ratio: float) -> float:
    """Espérance par trade, exprimée en multiples du risque nominal L.

    E[R] = p·(R − c/L) − (1−p)·(1 + c/L)
    """
    p = hit_rate
    return p * (reward_risk - friction_ratio) - (1.0 - p) * (1.0 + friction_ratio)


def required_reward_risk(hit_rate: float, friction_ratio: float) -> float:
    """R:R minimal pour atteindre l'équilibre à un hit rate donné.

    Inverse de `breakeven_hit_rate` : R* = (1 + c/L)/p − 1
    """
    if not 0.0 < hit_rate <= 1.0:
        raise ValueError("hit_rate doit être dans ]0, 1]")
    return (1.0 + friction_ratio) / hit_rate - 1.0


def trades_for_significance(
    mean_r: float,
    sd_r: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """Nombre de trades requis pour distinguer une espérance de zéro.

    Test unilatéral sur la moyenne : N = (z_alpha + z_beta)² · σ² / μ²

    C'est la taille d'échantillon minimale avant de pouvoir affirmer qu'un
    edge existe. En dessous, un P&L positif reste indiscernable du bruit.
    """
    if mean_r <= 0:
        raise ValueError("mean_r doit être > 0 pour tester un edge positif")
    return math.ceil((significance_constant(alpha, power) ** 2)
                     * (sd_r**2) / (mean_r**2))


def significance_constant(alpha: float = 0.05, power: float = 0.80) -> float:
    """`z_α + z_β`, le facteur qui gouverne la route du test t.

    Il est exposé parce qu'une figure a besoin de la constante elle-même et
    non d'un nombre de trades : le seuil de significativité vaut
    `(z_α + z_β)/√N`, et c'est cette courbe que l'on trace contre le seuil
    déflaté `√(2·ln B/N)`. Les deux routes sont alors visiblement la même
    forme en `1/√N`, à une constante près — 2,49 contre 2,35 à seize
    configurations — ce qui est la raison pour laquelle elles s'accordent.
    """
    return _norm_ppf(1.0 - alpha) + _norm_ppf(power)


def deflated_threshold_sharpe(n_trials: int, n_obs: int) -> float:
    """Sharpe minimal (annualisé, approx.) attendu du *meilleur* essai sous H0.

    Approximation de Bailey & López de Prado : en testant `n_trials`
    configurations sans aucun edge réel, le meilleur Sharpe observé vaut en
    espérance environ

        E[max SR] ≈ sqrt(2·ln(n_trials)/n_obs)

    (en unités de Sharpe par observation, converti ici en Sharpe par racine
    d'observation). Tout Sharpe backtesté sous ce seuil est indiscernable de
    l'artefact de sélection.
    """
    if n_trials < 2:
        return 0.0
    return math.sqrt(2.0 * math.log(n_trials) / max(n_obs, 1))


def _norm_ppf(p: float) -> float:
    """Quantile de la loi normale standard (Acklam, précision ~1e-9)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p doit être dans ]0, 1[")
    a = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
         1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00]
    b = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
         6.680131188771972e01, -1.328068155288572e01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
         -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
         3.754408661907416e00]
    p_low, p_high = 0.02425, 1.0 - 0.02425
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    if p > p_high:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)


def norm_cdf(x: float) -> float:
    """Fonction de répartition de la loi normale standard."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
