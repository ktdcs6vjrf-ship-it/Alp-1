"""First-passage brownien : survie du stop et P(TP avant SL).

Résultat structurant de ce module, et de tout ALP-1 :

    Sous un mouvement brownien *sans drift*, P(TP avant SL) = a/(a+b),
    exactement le hit rate d'équilibre sans friction pour R = b/a.

Autrement dit : aucun choix de stop et de target ne crée d'espérance. Le
placement des barrières ne fait que déplacer le compromis fréquence/amplitude
le long d'une même courbe d'espérance nulle. La *seule* source d'edge est le
drift µ au moment de l'entrée — et la friction est un prélèvement garanti sur
ce drift.

Toute la valeur des 7 couches d'ALP-1 se résume donc à une question mesurable :
produisent-elles, à l'instant de l'entrée, un drift µ suffisant ?
"""

from __future__ import annotations

import math

from .costs import norm_cdf


def sigma_over_horizon(sigma_per_min: float, horizon_min: float) -> float:
    """Écart-type du déplacement de prix sur un horizon, en points.

    Mise à l'échelle en racine du temps : σ_T = σ_1min · √T.
    """
    if sigma_per_min < 0 or horizon_min < 0:
        raise ValueError("sigma_per_min et horizon_min doivent être >= 0")
    return sigma_per_min * math.sqrt(horizon_min)


def prob_touch_single_barrier(
    distance: float,
    sigma_per_min: float,
    horizon_min: float,
) -> float:
    """P(toucher une barrière à `distance` points, dans l'un ou l'autre sens).

    Principe de réflexion pour un brownien sans drift :
        P(max_{[0,T]} |W| > a) ≈ 2·P(W_T > a) = 2·(1 − Φ(a / σ_T))

    C'est la probabilité qu'un stop symétrique à `distance` soit balayé par le
    seul bruit de marché, indépendamment de toute direction. Bornée à 1.
    """
    if distance <= 0:
        return 1.0
    sigma_t = sigma_over_horizon(sigma_per_min, horizon_min)
    if sigma_t <= 0:
        return 0.0
    return min(1.0, 2.0 * (1.0 - norm_cdf(distance / sigma_t)))


def prob_target_before_stop(
    stop_distance: float,
    target_distance: float,
    drift_per_min: float = 0.0,
    sigma_per_min: float = 1.0,
) -> float:
    """P(atteindre le target avant le stop) pour X_t = µt + σW_t.

    Barrières absorbantes en −a (stop) et +b (target).

        P = (1 − e^(−2µa/σ²)) / (1 − e^(−2µ(a+b)/σ²))

    Cas limite µ → 0 : P = a/(a+b) (ruine du joueur, espérance nulle).
    """
    a, b = stop_distance, target_distance
    if a <= 0 or b <= 0:
        raise ValueError("stop_distance et target_distance doivent être > 0")
    if sigma_per_min <= 0:
        raise ValueError("sigma_per_min doit être > 0")

    theta = 2.0 * drift_per_min / (sigma_per_min**2)
    if abs(theta) < 1e-12:
        return a / (a + b)

    # Formulation numériquement stable : on factorise l'exponentielle dominante
    # pour éviter tout overflow quand |theta|·(a+b) est grand.
    x, y = -theta * a, -theta * (a + b)
    if y > 0:
        # exp(y) domine : on divise numérateur et dénominateur par exp(y).
        num = math.exp(-y) - math.exp(x - y)
        den = math.exp(-y) - 1.0
    else:
        num = 1.0 - math.exp(x)
        den = 1.0 - math.exp(y)
    if abs(den) < 1e-300:
        return a / (a + b)
    return max(0.0, min(1.0, num / den))


def required_drift(
    stop_distance: float,
    target_distance: float,
    sigma_per_min: float,
    friction_points: float,
    tol: float = 1e-12,
    max_iter: int = 200,
) -> float:
    """Drift µ (points/min) requis pour une espérance nulle, friction incluse.

    On résout en µ :
        p(µ)·(b − c) − (1 − p(µ))·(a + c) = 0
    où p(µ) = P(target avant stop) et c la friction en points.

    Bissection sur µ ∈ [0, µ_max] : p est strictement croissante en µ, donc
    l'espérance l'est aussi — la racine est unique quand elle existe.
    """
    a, b, c = stop_distance, target_distance, friction_points

    def expectancy(mu: float) -> float:
        p = prob_target_before_stop(a, b, mu, sigma_per_min)
        return p * (b - c) - (1.0 - p) * (a + c)

    if b <= c:
        # Le target ne couvre même pas la friction : aucun drift ne sauve le trade.
        return math.inf

    lo, hi = 0.0, max(sigma_per_min, 1e-6)
    for _ in range(60):
        if expectancy(hi) >= 0:
            break
        hi *= 2.0
        if hi > 1e9:
            return math.inf

    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        if expectancy(mid) < 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol * max(1.0, hi):
            break
    return 0.5 * (lo + hi)


def drift_to_information_ratio(
    drift_per_min: float,
    sigma_per_min: float,
    horizon_min: float,
) -> float:
    """Traduit un drift requis en ratio d'information sur l'horizon du trade.

    IR = µ·T / (σ·√T) = (µ/σ)·√T

    C'est la lecture opérationnelle : « mon signal doit prévoir un déplacement
    de IR écarts-types sur la durée du trade ». Au-delà de ~0.3–0.5 sur des
    horizons intraday courts, l'exigence dépasse ce que la littérature
    documente pour des signaux publics.
    """
    if sigma_per_min <= 0 or horizon_min <= 0:
        raise ValueError("sigma_per_min et horizon_min doivent être > 0")
    return (drift_per_min / sigma_per_min) * math.sqrt(horizon_min)
