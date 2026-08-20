"""Géométrie « stop seul + sortie à l'heure », noyau quantitatif d'ALP-2.

Le module `horizon` traite le trade à deux barrières : un stop, un target, une
clôture. ALP-2 supprime le target. Il ne reste qu'une barrière basse et une
sortie au marché à la clôture, ce qui change complètement l'économie du trade :

  - l'exposition E[τ ∧ T] n'est plus bornée par l'atteinte d'un target, elle
    tend vers la séance entière quand le stop s'élargit ;
  - la friction rapportée au risque, c/L, s'effondre puisque L n'est plus de
    quelques ticks mais de quelques dizaines de points ;
  - la variance du résultat admet une forme fermée, ``σ²·E[τ ∧ T]`` (identité
    de Wald du second ordre), d'où un ratio de Sharpe par trade lisible.

C'est cette dernière propriété qui donne le résultat opérationnel du papier :

    SR_trade ≈ IR_signal − IR*,   IR* = c/(σ√E[τ ∧ T])

le Sharpe par trade est l'écart entre la qualité du signal et le seuil imposé
par la friction, tous deux mesurés en écarts-types de déplacement sur la durée
d'exposition. Élargir le stop et tenir jusqu'à la clôture abaisse IR* ; c'est
la seule chose que la géométrie sache faire.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .costs import Contract, norm_cdf

_SQRT_2_PI = math.sqrt(2.0 / math.pi)


# --- Calibration ------------------------------------------------------------

def sigma_from_session(session_dispersion: float, session_min: float) -> float:
    """Volatilité par racine de minute impliquée par la dispersion de séance.

    La seule calibration cohérente d'un brownien : si la dispersion d'une
    séance de `session_min` minutes vaut `session_dispersion` points, alors
    σ₁ = dispersion/√(session_min). Fixer les deux indépendamment revient à
    imposer une loi d'échelle, et l'exposant obtenu mesure alors l'écart entre
    les deux hypothèses, pas une propriété du prix.
    """
    if session_dispersion <= 0 or session_min <= 0:
        raise ValueError("dispersion et durée de séance doivent être > 0")
    return session_dispersion / math.sqrt(session_min)


def mean_abs_move(sigma_per_min: float, minutes: float) -> float:
    """E[|X_t|] pour un brownien sans dérive : σ√t·√(2/π).

    C'est la définition de la *bande de bruit* d'ALP-2 : le déplacement absolu
    moyen depuis l'ouverture, à une heure donnée de la séance. Un déplacement
    qui l'excède est, par construction, plus grand que le mouvement usuel de
    la séance à cette heure-là.
    """
    if sigma_per_min < 0 or minutes < 0:
        raise ValueError("sigma_per_min et minutes doivent être >= 0")
    return _SQRT_2_PI * sigma_per_min * math.sqrt(minutes)


def band_pct(index_level: float, sigma_per_min: float, minutes: float) -> float:
    """Demi-largeur de la bande de bruit, en pourcentage du niveau d'indice."""
    if index_level <= 0:
        raise ValueError("index_level doit être > 0")
    return 100.0 * mean_abs_move(sigma_per_min, minutes) / index_level


# --- Premier passage à une seule barrière ----------------------------------

def survival(stop_distance: float, minutes: float, sigma_per_min: float) -> float:
    """P(le stop n'a pas été touché avant `minutes`), sous martingale.

    Principe de réflexion : P(min_{[0,t]} X < −a) = 2Φ(−a/σ√t), d'où une
    survie qui vaut ``erf(a/(σ√(2t)))``.
    """
    a = stop_distance
    if a <= 0:
        return 0.0
    if minutes <= 0:
        return 1.0
    if sigma_per_min <= 0:
        raise ValueError("sigma_per_min doit être > 0")
    return math.erf(a / (sigma_per_min * math.sqrt(2.0 * minutes)))


def prob_stop(stop_distance: float, horizon_min: float, sigma_per_min: float) -> float:
    """P(stop touché avant la clôture), sous martingale."""
    return 1.0 - survival(stop_distance, horizon_min, sigma_per_min)


def expected_exposure(
    stop_distance: float,
    horizon_min: float,
    sigma_per_min: float,
) -> float:
    """E[τ ∧ T] en minutes pour un stop unique et une sortie à l'heure.

    Forme fermée obtenue en intégrant la survie, avec ``k = a/(σ√2)`` :

        E[τ ∧ T] = T·erf(k/√T) + (2k√T/√π)·e^(−k²/T) − 2k²·erfc(k/√T)

    Deux limites contrôlent le résultat : ``a → ∞`` donne `T` (le stop n'est
    jamais touché, la position vit toute la séance) et ``a → 0`` donne 0.
    Contrairement au cas à deux barrières, cette espérance diverge quand
    `T → ∞` : c'est la clôture, et elle seule, qui borne l'exposition.
    """
    a, T = stop_distance, horizon_min
    if a <= 0:
        return 0.0
    if T <= 0:
        return 0.0
    if sigma_per_min <= 0:
        raise ValueError("sigma_per_min doit être > 0")

    k = a / (sigma_per_min * math.sqrt(2.0))
    z = k / math.sqrt(T)
    return (T * math.erf(z)
            + (2.0 * k * math.sqrt(T) / math.sqrt(math.pi)) * math.exp(-z * z)
            - 2.0 * k * k * math.erfc(z))


@dataclass(frozen=True)
class TimeExitOutcome:
    """Issues d'un trade « stop seul, sortie à la clôture », sous martingale.

    `mean_gross` doit être nul à la précision machine — c'est le théorème
    d'arrêt optionnel appliqué à un temps d'arrêt borné, exactement comme dans
    `alp1.horizon`. `sd_gross` vaut ``σ√E[τ ∧ T]`` par l'identité de Wald du
    second ordre : la dispersion du résultat est celle du temps passé exposé.
    """

    stop_distance: float
    horizon_min: float
    sigma_per_min: float
    p_stop: float
    p_open: float
    expected_time: float
    mean_gross: float
    sd_gross: float

    @property
    def mean_open(self) -> float:
        """Gain moyen des trades qui atteignent la clôture, en points.

        L'espérance totale étant nulle, la branche « encore ouverte » doit
        compenser exactement les stops : ``p_stop·a / p_open``.
        """
        return self.p_stop * self.stop_distance / self.p_open if self.p_open > 0 else 0.0


def time_exit_outcome(
    stop_distance: float,
    horizon_min: float,
    sigma_per_min: float,
) -> TimeExitOutcome:
    """Distribution complète des issues sous martingale."""
    p_stop = prob_stop(stop_distance, horizon_min, sigma_per_min)
    exposure = expected_exposure(stop_distance, horizon_min, sigma_per_min)
    return TimeExitOutcome(
        stop_distance=stop_distance,
        horizon_min=horizon_min,
        sigma_per_min=sigma_per_min,
        p_stop=p_stop,
        p_open=1.0 - p_stop,
        expected_time=exposure,
        mean_gross=0.0,
        sd_gross=sigma_per_min * math.sqrt(exposure),
    )


# --- Seuils : le critère maître appliqué à cette géométrie ------------------

def required_drift(friction_points: float, expected_time: float) -> float:
    """Dérive minimale rentable µ* = c/E[τ], en points par minute."""
    if expected_time <= 0:
        return math.inf
    return friction_points / expected_time


def required_ir(friction_points: float, sigma_per_min: float, expected_time: float) -> float:
    """Ratio d'information requis IR* = c/(σ√E[τ ∧ T]).

    Nombre d'écarts-types de déplacement que le signal doit prévoir sur la
    durée d'exposition pour que le trade franchisse simplement la friction.
    """
    if expected_time <= 0 or sigma_per_min <= 0:
        return math.inf
    return friction_points / (sigma_per_min * math.sqrt(expected_time))


def sharpe_per_trade(
    edge_points: float,
    friction_points: float,
    sigma_per_min: float,
    expected_time: float,
) -> float:
    """Sharpe par trade = (dérive captée − friction)/σ√E[τ ∧ T].

    `edge_points` est le déplacement moyen capté par le signal sur la durée du
    trade, µ·E[τ], exprimé en points. À l'ordre dominant en µ, la variance du
    résultat reste ``σ²E[τ ∧ T]`` : la correction due à la dérive est d'ordre
    µ²·Var(τ), négligeable aux dérives dont il est question ici.
    """
    if expected_time <= 0 or sigma_per_min <= 0:
        return 0.0
    return (edge_points - friction_points) / (sigma_per_min * math.sqrt(expected_time))


def annualised_sharpe(sharpe_trade: float, trades_per_year: float) -> float:
    """Sharpe annualisé pour des trades indépendants."""
    if trades_per_year <= 0:
        return 0.0
    return sharpe_trade * math.sqrt(trades_per_year)


def trades_for_t_stat(sharpe_trade: float, t_target: float = 2.0) -> float:
    """Nombre de trades requis pour atteindre un t-statistique donné."""
    if sharpe_trade <= 0:
        return math.inf
    return (t_target / sharpe_trade) ** 2


def edge_points_from_bps(basis_points: float, index_level: float) -> float:
    """Convertit une espérance par trade exprimée en points de base en points."""
    return basis_points / 1e4 * index_level


def expectancy_r(win_rate: float, payoff: float) -> float:
    """Espérance par trade en multiples du risque, à partir du couple observé.

    `payoff` est le rapport gain moyen / perte moyenne. Sert à traduire les
    statistiques publiées par les réplications (taux de réussite, payoff) dans
    l'unité du papier.
    """
    if not 0.0 <= win_rate <= 1.0:
        raise ValueError("win_rate doit être dans [0, 1]")
    return win_rate * payoff - (1.0 - win_rate)


# --- Dimensionnement --------------------------------------------------------

def contracts_for_risk(
    equity: float,
    risk_pct: float,
    stop_distance: float,
    contract: Contract,
) -> float:
    """Nombre de contrats pour risquer `risk_pct` % du capital sur le stop.

    Valeur fractionnaire : à l'opérateur d'arrondir *vers le bas*. Un stop de
    plusieurs dizaines de points impose le micro-contrat en dessous de
    quelques dizaines de milliers de dollars de capital — c'est une contrainte
    d'instrument, pas une préférence.
    """
    if equity <= 0 or risk_pct <= 0 or stop_distance <= 0:
        raise ValueError("equity, risk_pct et stop_distance doivent être > 0")
    risk_usd = equity * risk_pct / 100.0
    return risk_usd / (stop_distance * contract.point_value)


def risk_per_contract(stop_distance: float, contract: Contract,
                      friction_points: float = 0.0) -> float:
    """Perte en dollars d'un stop touché, friction comprise, pour 1 contrat."""
    return (stop_distance + friction_points) * contract.point_value


def kelly_fraction(sharpe_trade: float) -> float:
    """Fraction de Kelly approchée pour un résultat continu : SR par trade.

    Pour un pari de Sharpe faible, f* ≈ µ/σ² en unités de risque, soit le
    Sharpe par trade rapporté à l'écart-type. La pratique retient une fraction
    de cette valeur ; le papier retient un quart.
    """
    return max(0.0, sharpe_trade)
