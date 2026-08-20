"""Premier passage à deux barrières sous contrainte de temps.

Le module `barriers` traite le problème classique sans limite de durée : le
trade se termine forcément au stop ou au target. Cette idéalisation est
inoffensive tant que la distance au target est petite devant la dispersion de
la séance. Elle cesse de l'être dès que le target est éloigné : la position
peut alors atteindre la clôture sans qu'aucune barrière ait été touchée, et
cette troisième issue devient dominante.

Le processus est ramené à ses coordonnées naturelles : on note ``u`` la
position du prix dans l'intervalle ``[0, l]`` avec ``l = a + b``, le stop en
``u = 0``, le target en ``u = l`` et l'entrée en ``u = a``. Le résultat brut
d'une sortie en ``u`` vaut ``u − a`` points.

Toutes les formules dérivent du développement en modes propres de l'équation
de la chaleur sur ``[0, l]`` avec conditions absorbantes :

    p(t, u) = (2/l) Σ sin(nπa/l) sin(nπu/l) exp(−λ_n t),
    λ_n = n²π²σ²/(2l²)

Le cas avec drift s'en déduit par changement de mesure (Girsanov) :
``p_µ(t, u) = exp(θ(u − a) − νt)·p_0(t, u)`` avec ``θ = µ/σ²`` et
``ν = µ²/(2σ²)``. Les séries sont réécrites de façon à ne conserver que des
termes amortis, ce qui les rend absolument convergentes à tout horizon.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_PI = math.pi
_MAX_TERMS = 200_000
_TOL = 1e-15


@dataclass(frozen=True)
class HorizonOutcome:
    """Issues d'un trade à barrières fixes tronqué par un horizon `T`.

    `p_target` et `p_stop` sont les probabilités d'absorption avant `T`,
    `p_open` la probabilité que la position soit encore ouverte à `T` et
    liquidée au marché. Les moments sont exprimés en points d'indice, avant
    friction, et rapportés à l'entrée.
    """

    p_target: float
    p_stop: float
    p_open: float
    mean_open: float          # E[X_T · 1{position encore ouverte}]
    expected_time: float      # E[τ ∧ T], en minutes
    mean_gross: float         # E[X_{τ∧T}]
    sd_gross: float           # écart-type de X_{τ∧T}

    @property
    def apparent_hit_rate(self) -> float:
        """Gagnants rapportés aux seuls trades tranchés par une barrière."""
        decided = self.p_target + self.p_stop
        return self.p_target / decided if decided > 0 else 0.0


def _check(a: float, b: float, horizon_min: float, sigma_per_min: float) -> None:
    if a <= 0 or b <= 0:
        raise ValueError("a et b doivent être > 0")
    if horizon_min <= 0:
        raise ValueError("horizon_min doit être > 0")
    if sigma_per_min <= 0:
        raise ValueError("sigma_per_min doit être > 0")


def _n_terms(l: float, horizon_min: float, sigma_per_min: float) -> int:
    """Rang de troncature : au-delà, exp(−λ_n T) est numériquement nul.

    λ_n T > 40 suffit pour que le terme disparaisse en double précision. Un
    plancher garantit la convergence de la part algébrique des séries.
    """
    lam1 = (_PI * sigma_per_min / l) ** 2 / 2.0
    n_exp = math.sqrt(40.0 / max(lam1 * horizon_min, 1e-18))
    return int(min(_MAX_TERMS, max(40_000.0, math.ceil(n_exp) + 8)))


def absorption_probabilities(
    stop_distance: float,
    target_distance: float,
    horizon_min: float,
    drift_per_min: float = 0.0,
    sigma_per_min: float = 1.0,
) -> tuple[float, float, float]:
    """(P(target avant stop et avant T), P(stop d'abord), P(encore ouvert)).

    Limite `horizon_min → ∞` : on retrouve la ruine du joueur du module
    `barriers`. Limite `drift_per_min → 0` : les deux premières probabilités
    tendent vers a/(a+b) et b/(a+b) pondérées par la troncature temporelle.
    """
    a, b = stop_distance, target_distance
    _check(a, b, horizon_min, sigma_per_min)

    l = a + b
    var = sigma_per_min**2
    theta = drift_per_min / var
    nu = drift_per_min**2 / (2.0 * var)
    alpha = _PI * a / l

    up_corr = 0.0
    down_corr = 0.0
    n_max = _n_terms(l, horizon_min, sigma_per_min)
    quiet = 0
    for n in range(1, n_max + 1):
        lam = (n * _PI * sigma_per_min / l) ** 2 / 2.0
        damp = lam + nu
        # Part algébrique (ν/λ) + part amortie : les deux tendent vite vers 0.
        weight = nu / damp + (lam / damp) * math.exp(-damp * horizon_min)
        base = (2.0 / (n * _PI)) * math.sin(n * alpha) * weight
        down_corr += base
        up_corr += base if n % 2 else -base
        if abs(base) < _TOL:
            quiet += 1
            if quiet > 24:
                break
        else:
            quiet = 0

    p_up = math.exp(theta * b) * (a / l - up_corr)
    p_down = math.exp(-theta * a) * (b / l - down_corr)
    p_up = min(max(p_up, 0.0), 1.0)
    p_down = min(max(p_down, 0.0), 1.0)
    p_open = max(0.0, 1.0 - p_up - p_down)
    return p_up, p_down, p_open


def expected_exit_time(
    stop_distance: float,
    target_distance: float,
    horizon_min: float,
    sigma_per_min: float = 1.0,
) -> float:
    """E[τ ∧ T] en minutes, sous martingale.

    Obtenue en intégrant la probabilité de survie ``S(t) = Σ_impairs
    (4/nπ)·sin(nπa/l)·exp(−λ_n t)``. Limite `T → ∞` : ``a·b/σ²``, le temps
    moyen d'un trade à barrières fixes — la quantité qui gouverne, seule,
    l'exposition au drift.
    """
    a, b = stop_distance, target_distance
    _check(a, b, horizon_min, sigma_per_min)

    l = a + b
    alpha = _PI * a / l
    total = 0.0
    quiet = 0
    n_max = _n_terms(l, horizon_min, sigma_per_min)
    for n in range(1, n_max + 1, 2):
        lam = (n * _PI * sigma_per_min / l) ** 2 / 2.0
        term = (4.0 / (n * _PI)) * math.sin(n * alpha) * (1.0 - math.exp(-lam * horizon_min)) / lam
        total += term
        # Un terme isolé peut s'annuler (sin(nπa/l) = 0) sans que la série
        # ait convergé : on n'arrête que sur une plage de termes négligeables.
        if abs(term) < _TOL * max(1.0, abs(total)):
            quiet += 1
            if quiet > 32:
                break
        else:
            quiet = 0
    return total


def outcome(
    stop_distance: float,
    target_distance: float,
    horizon_min: float,
    sigma_per_min: float = 1.0,
) -> HorizonOutcome:
    """Distribution complète des issues sous martingale, horizon `T` compris.

    Le contrôle interne le plus utile du module : ``mean_gross`` doit être nul
    à la précision machine — c'est le théorème d'arrêt optionnel appliqué à
    ``τ ∧ T``, qui est borné par construction.
    """
    a, b = stop_distance, target_distance
    _check(a, b, horizon_min, sigma_per_min)

    l = a + b
    alpha = _PI * a / l
    p_up, p_down, p_open = absorption_probabilities(a, b, horizon_min, 0.0, sigma_per_min)

    # Moments de la densité résiduelle : ∫ u^k p(T,u) du, k = 0, 1, 2.
    m0 = m1 = m2 = 0.0
    n_max = _n_terms(l, horizon_min, sigma_per_min)
    for n in range(1, n_max + 1):
        lam = (n * _PI * sigma_per_min / l) ** 2 / 2.0
        decay = math.exp(-lam * horizon_min)
        if decay < 1e-300:
            break
        k = n * _PI / l
        amp = (2.0 / l) * math.sin(n * alpha) * decay
        sign = -1.0 if n % 2 == 0 else 1.0            # (−1)^(n+1)
        i0 = (1.0 - (-sign)) / k                       # ∫ sin = (1 − cos nπ)/k
        i1 = l**2 * sign / (n * _PI)                   # ∫ u·sin
        i2 = (-sign) * (-(l**2) / k + 2.0 / k**3) - 2.0 / k**3
        m0 += amp * i0
        m1 += amp * i1
        m2 += amp * i2

    mean_open = m1 - a * m0
    mean_gross = p_up * b + p_down * (-a) + mean_open
    second = p_up * b**2 + p_down * a**2 + (m2 - 2.0 * a * m1 + a**2 * m0)
    var = max(0.0, second - mean_gross**2)
    return HorizonOutcome(
        p_target=p_up,
        p_stop=p_down,
        p_open=p_open,
        mean_open=mean_open,
        expected_time=expected_exit_time(a, b, horizon_min, sigma_per_min),
        mean_gross=mean_gross,
        sd_gross=math.sqrt(var),
    )


def survival_probability(
    stop_distance: float,
    target_distance: float,
    horizon_min: float,
    sigma_per_min: float = 1.0,
) -> float:
    """P(aucune barrière touchée avant `T`), sous martingale."""
    a, b = stop_distance, target_distance
    _check(a, b, horizon_min, sigma_per_min)
    l = a + b
    alpha = _PI * a / l
    total = 0.0
    quiet = 0
    for n in range(1, _n_terms(l, horizon_min, sigma_per_min) + 1, 2):
        lam = (n * _PI * sigma_per_min / l) ** 2 / 2.0
        term = (4.0 / (n * _PI)) * math.sin(n * alpha) * math.exp(-lam * horizon_min)
        total += term
        if abs(term) < _TOL:
            quiet += 1
            if quiet > 32:
                break
        else:
            quiet = 0
    return min(1.0, max(0.0, total))


def effective_time(horizon_min: float, hurst: float = 0.5) -> float:
    """Temps effectif d'un brownien à changement de temps déterministe.

    On suppose que la dispersion croît en ``σ(T) = σ₁·T^H`` plutôt qu'en
    racine du temps. Le processus ``X_t = σ₁·W_{t^{2H}}`` reproduit exactement
    cette loi d'échelle tout en restant une martingale : toutes les formules
    de premier passage s'appliquent en remplaçant l'horizon réel `T` par le
    temps effectif ``T^{2H}``. `H = 0.5` redonne le cas diffusif.

    Deux observables suffisent à fixer `H` : la volatilité à une minute et la
    dispersion de la séance. Le paramètre n'est donc pas libre, il se mesure.
    """
    if hurst <= 0.0 or hurst >= 1.0:
        raise ValueError("hurst doit être dans ]0, 1[")
    return horizon_min ** (2.0 * hurst)


def hurst_from_dispersions(
    sigma_short: float,
    sigma_long: float,
    horizon_min: float,
) -> float:
    """Exposant d'échelle impliqué par deux dispersions observées.

    ``σ_long = σ_short · T^H``  =>  ``H = ln(σ_long/σ_short)/ln(T)``.
    """
    if sigma_short <= 0 or sigma_long <= 0 or horizon_min <= 1:
        raise ValueError("dispersions > 0 et horizon > 1 min requis")
    return math.log(sigma_long / sigma_short) / math.log(horizon_min)


def outcome_scaled(
    stop_distance: float,
    target_distance: float,
    horizon_min: float,
    sigma_per_min: float = 1.0,
    hurst: float = 0.5,
    n_quad: int = 512,
) -> HorizonOutcome:
    """Issues sous loi d'échelle ``σ(T) = σ₁·T^H``, horizon `T` compris.

    Les probabilités se lisent directement en temps effectif. L'espérance de
    durée, elle, doit être ramenée au temps réel : on intègre la fonction de
    survie ``E[τ∧T] = ∫₀^T S(t^{2H}) dt`` par la règle de Simpson.

    L'identité de Wald ``E[X_{τ∧T}] = µ·E[τ∧T]`` reste valide sous ce
    changement de temps, qui est déterministe : le critère maître du papier
    n'est pas affecté, seules les valeurs numériques de l'exposition le sont.
    """
    a, b = stop_distance, target_distance
    _check(a, b, horizon_min, sigma_per_min)
    if abs(hurst - 0.5) < 1e-12:
        return outcome(a, b, horizon_min, sigma_per_min)

    base = outcome(a, b, effective_time(horizon_min, hurst), sigma_per_min)

    n = n_quad if n_quad % 2 == 0 else n_quad + 1
    h = horizon_min / n
    acc = 0.0
    for i in range(n + 1):
        t = i * h
        s = 1.0 if t <= 0 else survival_probability(
            a, b, effective_time(t, hurst), sigma_per_min
        )
        w = 1.0 if i in (0, n) else (4.0 if i % 2 else 2.0)
        acc += w * s
    expected = acc * h / 3.0

    return HorizonOutcome(
        p_target=base.p_target,
        p_stop=base.p_stop,
        p_open=base.p_open,
        mean_open=base.mean_open,
        expected_time=expected,
        mean_gross=base.mean_gross,
        sd_gross=base.sd_gross,
    )
