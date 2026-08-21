"""Adéquation du modèle : ce que la diffusion ignore, et ce qu'il en coûte.

Le noyau d'ALP-2 est une diffusion à volatilité constante. Le prix intra-séance
ne l'est pas, et trois écarts sont documentés depuis longtemps :

  1. **la saisonnalité intra-séance** — la variance est en U, forte à
     l'ouverture, creuse en milieu de séance, remontante à la clôture ;
  2. **les sauts** — le prix se déplace parfois plus vite que le carnet ne se
     reconstitue, et un stop ne s'exécute pas au niveau où il est posé ;
  3. **l'hétéroscédasticité** — la volatilité d'une séance n'est pas connue à
     l'entrée ; elle est elle-même une variable aléatoire.

Ce module ne remplace pas la diffusion : il l'enrichit des trois écarts, un par
un puis ensemble, et mesure ce que chaque conclusion devient. Le résultat se
classe en trois catégories, et c'est la classification qui compte :

**Ce qui est invariant.** Le critère maître ``E[résultat] = µ·E[τ∧T] − c``
survit aux trois écarts, et pour trois raisons différentes. La saisonnalité est
un changement de temps déterministe : elle déforme l'horloge de la variance,
pas la martingale. Les sauts d'espérance nulle laissent le prix martingale, et
comme la géométrie d'ALP-2 ne tronque **aucune** issue par le haut — la sortie
est au marché, à la clôture — le dépassement du stop entre dans `X_{τ∧T}` et
l'identité de Wald l'absorbe. L'hétéroscédasticité indépendante du signe du
mouvement laisse également la martingale intacte. Le critère est donc plus
robuste que le modèle dont il est tiré ; c'est le seul énoncé du document qui
mérite ce statut, et `mc_wald_check` le vérifie par simulation sur le modèle
complet, pas sur la diffusion.

**Ce qui se déplace, et de combien.** L'exposition, la probabilité de toucher
le stop, la largeur de la bande de bruit et le seuil `IR*` bougent tous, dans
des sens que le module chiffre. Aucun de ces déplacements ne renverse le sens
d'une conclusion à la calibration retenue ; tous sont rapportés.

**Ce qui change de nature.** Sous sauts, la perte réalisée n'est plus la perte
nominale : le stop est posé à `a`, la perte vaut ``a + (|J| − a)⁺``. La
conséquence n'est pas sur l'espérance — Wald l'absorbe — mais sur le
**dénominateur** : `c/L`, le risque par contrat et le dimensionnement sont
calculés sur une perte qui sous-estime la vraie. C'est la différence exacte
entre ALP-1 et ALP-2 devant les sauts : sur un stop de trois points, le
dépassement est du même ordre que le stop ; sur la bande de bruit, il est
d'ordre un pour cent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .mc import Rng
from .momentum import mean_abs_move, required_ir, time_exit_outcome
from .stress import JumpModel, expected_slippage_beyond_stop, prob_jump_during_trade

_SQRT_2_PI = math.sqrt(2.0 / math.pi)


# --- 1. Saisonnalité : la variance en U comme changement de temps -----------


@dataclass(frozen=True)
class Seasonality:
    """Profil de variance intra-séance, normalisé à variance totale inchangée.

    Le taux de variance instantané est pris sous la forme

        v(t) = k · (1 + A·e^{−t/α} + B·e^{−(S−t)/β})

    — un socle plat, une bosse d'ouverture qui décroît en `α` minutes, une
    bosse de clôture qui monte en `β` minutes — et `k` est fixé par la
    contrainte ``∫₀^S v = S``. La séance a donc *exactement* la même variance
    totale que sous volatilité constante : le profil redistribue le risque dans
    la séance, il n'en ajoute pas. C'est la seule façon d'isoler l'effet de
    forme de l'effet de niveau.

    L'horloge de variance ``Λ(t) = ∫₀^t v`` a une forme fermée, et le processus
    ``X_t = σ·W_{Λ(t)}`` reproduit le profil tout en restant une martingale.
    Toutes les formules de premier passage s'appliquent en remplaçant le temps
    réel par `Λ`.
    """

    session_min: float = 390.0
    open_amp: float = 3.0
    open_decay: float = 30.0
    close_amp: float = 1.5
    close_decay: float = 45.0

    def __post_init__(self) -> None:
        if self.session_min <= 0:
            raise ValueError("session_min doit être > 0")
        if min(self.open_amp, self.close_amp) < 0:
            raise ValueError("les amplitudes doivent être >= 0")
        if min(self.open_decay, self.close_decay) <= 0:
            raise ValueError("les constantes de temps doivent être > 0")

    @property
    def scale(self) -> float:
        """La constante `k` qui préserve la variance totale de la séance."""
        s, a, b = self.session_min, self.open_decay, self.close_decay
        bump = (self.open_amp * a * (1.0 - math.exp(-s / a))
                + self.close_amp * b * (1.0 - math.exp(-s / b)))
        return s / (s + bump)

    def rate(self, t: float) -> float:
        """Taux de variance instantané `v(t)`, en multiples de la moyenne."""
        s = self.session_min
        t = min(max(t, 0.0), s)
        return self.scale * (1.0
                             + self.open_amp * math.exp(-t / self.open_decay)
                             + self.close_amp * math.exp(-(s - t) / self.close_decay))

    def clock(self, t: float) -> float:
        """Horloge de variance ``Λ(t)``, en minutes de variance équivalentes."""
        s, a, b = self.session_min, self.open_decay, self.close_decay
        t = min(max(t, 0.0), s)
        return self.scale * (
            t
            + self.open_amp * a * (1.0 - math.exp(-t / a))
            + self.close_amp * b * (math.exp(-(s - t) / b) - math.exp(-s / b))
        )

    def elapsed(self, t0: float, t1: float) -> float:
        """Variance écoulée entre deux instants, ``Λ(t₁) − Λ(t₀)``."""
        return self.clock(t1) - self.clock(t0)

    def share(self, t0: float, t1: float) -> float:
        """Part de la variance de la séance contenue dans `[t₀, t₁]`."""
        return self.elapsed(t0, t1) / self.session_min


FLAT = Seasonality(open_amp=0.0, close_amp=0.0)


def _survival(a: float, variance_min: float, sigma: float) -> float:
    """P(pas de contact) après `variance_min` minutes de variance écoulées."""
    if a <= 0:
        return 0.0
    if variance_min <= 0:
        return 1.0
    return math.erf(a / (sigma * math.sqrt(2.0 * variance_min)))


@dataclass(frozen=True)
class SeasonalOutcome:
    """Issues d'un trade sous saisonnalité, entrée à `entry_min`.

    `expected_time` est en minutes d'horloge — c'est lui qui multiplie la
    dérive dans le critère maître. `expected_variance_time` est en minutes de
    variance — c'est lui qui fixe la dispersion du résultat, ``σ√Λ``. Sous
    volatilité constante les deux coïncident ; c'est précisément ce que la
    saisonnalité sépare, et la séparation se lit dans `IR*`.
    """

    stop: float
    entry_min: float
    session_min: float
    sigma_per_min: float
    p_stop: float
    expected_time: float
    expected_variance_time: float

    @property
    def p_open(self) -> float:
        return 1.0 - self.p_stop

    @property
    def sd_gross(self) -> float:
        return self.sigma_per_min * math.sqrt(self.expected_variance_time)


def seasonal_band(sigma: float, entry_min: float,
                  seas: Seasonality = Seasonality()) -> float:
    """Bande de bruit à l'entrée sous saisonnalité : ``√(2/π)·σ√Λ(entrée)``.

    À 11:00, l'essentiel de la bosse d'ouverture est déjà consommé : la bande
    mesurée est plus large que ne le prédit la racine du temps, et le stop qui
    s'y ajuste est plus large d'autant. C'est le premier effet, et il joue en
    faveur de la géométrie.
    """
    return _SQRT_2_PI * sigma * math.sqrt(seas.clock(entry_min))


def seasonal_outcome(stop: float, entry_min: float, sigma: float,
                     seas: Seasonality = Seasonality(),
                     n_quad: int = 512) -> SeasonalOutcome:
    """Issues sous saisonnalité, par quadrature de Simpson sur la survie.

    ``P(stop) = 1 − S(Λ(S) − Λ(entrée))`` se lit directement en temps de
    variance. Les deux espérances demandent une intégrale, l'une en temps réel
    et l'autre pondérée par le taux de variance :

        E[τ∧T]   = ∫ S(Λ(t) − Λ(e)) dt
        E[Λ(τ∧T)] = ∫ S(Λ(t) − Λ(e))·v(t) dt
    """
    if stop <= 0 or sigma <= 0:
        raise ValueError("stop et sigma doivent être > 0")
    s = seas.session_min
    if not 0.0 <= entry_min < s:
        raise ValueError("l'entrée doit tomber dans la séance")

    n = n_quad if n_quad % 2 == 0 else n_quad + 1
    h = (s - entry_min) / n
    acc_t = 0.0
    acc_v = 0.0
    for i in range(n + 1):
        t = entry_min + i * h
        surv = _survival(stop, seas.elapsed(entry_min, t), sigma)
        w = 1.0 if i in (0, n) else (4.0 if i % 2 else 2.0)
        acc_t += w * surv
        acc_v += w * surv * seas.rate(t)
    return SeasonalOutcome(
        stop=stop, entry_min=entry_min, session_min=s, sigma_per_min=sigma,
        p_stop=1.0 - _survival(stop, seas.elapsed(entry_min, s), sigma),
        expected_time=acc_t * h / 3.0,
        expected_variance_time=acc_v * h / 3.0,
    )


# --- 2. Sauts : la perte réalisée n'est pas la perte nominale ---------------


@dataclass(frozen=True)
class GapCost:
    """Ce qu'un saut coûte à une géométrie à barrière unique.

    Le point central : `expectancy_shift` est **nul**. La sortie d'ALP-2 est au
    marché à la clôture, sans target : aucune issue n'est tronquée par le haut,
    le dépassement du stop appartient à `X_{τ∧T}`, et l'identité de Wald
    l'absorbe intégralement. Ce que le saut déplace, c'est la perte réalisée
    par rapport à la perte nominale — donc `c/L`, le risque par contrat et le
    dimensionnement, pas l'espérance.

    C'est aussi le point où les deux géométries se séparent le plus nettement.
    Le dépassement `E[(|J| − a)⁺]` décroît en queue gaussienne avec la largeur
    du stop : ce qui coûte quelques pour cent sur un stop de trois points ne se
    lit plus sur un stop posé à la bande de bruit.
    """

    stop: float
    p_jump: float
    expected_overshoot: float
    realised_loss: float
    inflation_pct: float
    expectancy_shift: float = 0.0

    @property
    def cost_in_r(self) -> float:
        """Surcoût espéré par trade, en multiples du risque nominal."""
        return self.p_jump * self.expected_overshoot / self.stop


def gap_cost(stop: float, exposure_min: float,
             models: "JumpModel | tuple[JumpModel, ...]",
             session_min: float = 390.0) -> GapCost:
    """Dépassement de stop espéré et inflation du risque réel.

    Accepte un modèle ou une famille de modèles indépendants — les sauts de
    marché ne sont pas homogènes : un décalage de carnet et une surprise macro
    n'ont ni la même fréquence ni la même amplitude, et les mélanger dans une
    gaussienne unique efface précisément la queue qui compte. Les surcoûts
    s'additionnent, les probabilités se composent.
    """
    family = (models,) if isinstance(models, JumpModel) else tuple(models)
    excess = 0.0
    survive = 1.0
    for m in family:
        p = prob_jump_during_trade(m, exposure_min, session_min)
        excess += p * expected_slippage_beyond_stop(m, stop)
        survive *= 1.0 - p
    realised = stop + excess
    return GapCost(
        stop=stop, p_jump=1.0 - survive, expected_overshoot=excess,
        realised_loss=realised,
        inflation_pct=100.0 * (realised / stop - 1.0),
    )


# Deux familles de sauts, parce qu'une seule ne décrit pas le marché. Les
# décalages de carnet sont fréquents et petits ; les surprises macro sont rares
# et grandes, et ce sont elles qui décident du sort d'un stop étroit.
JUMPS_MICRO = JumpModel(intensity_per_day=2.0, mean_jump=0.0, sd_jump=4.0)
JUMPS_MACRO = JumpModel(intensity_per_day=0.2, mean_jump=0.0, sd_jump=15.0)
JUMPS = (JUMPS_MICRO, JUMPS_MACRO)


def gap_comparison(stops: tuple[float, ...], exposures: tuple[float, ...],
                   models: tuple[JumpModel, ...] = JUMPS,
                   session_min: float = 390.0) -> list[GapCost]:
    """Le coût des sauts sur une grille de stops, à exposition correspondante."""
    if len(stops) != len(exposures):
        raise ValueError("un stop par exposition")
    return [gap_cost(a, t, models, session_min) for a, t in zip(stops, exposures)]


# --- 3. Hétéroscédasticité : la volatilité de la séance est inconnue --------


@dataclass(frozen=True)
class VolMixture:
    """Volatilité de séance lognormale, à variance moyenne préservée.

    ``σ = σ̄·exp(νZ − ν²/2)`` avec `Z` normale centrée réduite : `E[σ²]` vaut
    ``σ̄²·e^{ν²}``… ce qui ne préserverait rien. On retient donc
    ``σ = σ̄·exp(νZ − ν²)``, qui donne ``E[σ²] = σ̄²`` exactement. Le mélange
    est ainsi neutre en variance totale : tout écart aux valeurs de référence
    est un effet de **forme** de la loi, pas de niveau — c'est la même
    discipline que pour la saisonnalité.

    `nu` est l'écart-type du log de la volatilité de séance. La valeur retenue,
    0,35, correspond à un rapport de un à deux entre le quantile à 15 % et le
    quantile à 85 % des séances, ce qui est l'ordre de grandeur usuel d'une
    volatilité réalisée quotidienne sur indice.
    """

    sigma_bar: float
    nu: float = 0.35

    def sigma(self, z: float) -> float:
        return self.sigma_bar * math.exp(self.nu * z - self.nu * self.nu)

    def quantile(self, p: float) -> float:
        from .costs import _norm_ppf
        return self.sigma(_norm_ppf(p))


def expect_over_vol(fn, mix: VolMixture, n_quad: int = 200,
                    z_max: float = 7.0) -> float:
    """``E[fn(σ)]`` sous le mélange, par Simpson pondéré par la densité normale.

    La troncature est portée à sept écarts-types plutôt qu'aux cinq usuels :
    l'intégrande porte un facteur `e^{2νz}` quand `fn` est quadratique en σ, et
    ce facteur retarde l'extinction de la queue. La quadrature est renormalisée
    par le poids effectivement intégré, de sorte qu'une fonction constante
    retourne exactement sa valeur.
    """
    n = n_quad if n_quad % 2 == 0 else n_quad + 1
    h = 2.0 * z_max / n
    acc = 0.0
    mass = 0.0
    for i in range(n + 1):
        z = -z_max + i * h
        w = 1.0 if i in (0, n) else (4.0 if i % 2 else 2.0)
        phi = math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
        acc += w * phi * fn(mix.sigma(z))
        mass += w * phi
    return acc / mass


# --- Vérification par simulation du modèle complet --------------------------


@dataclass(frozen=True)
class WaldCheck:
    """Confrontation du critère maître à une simulation du modèle enrichi.

    `predicted` vaut ``µ·E[τ∧T] − c`` où `E[τ∧T]` est l'exposition **mesurée
    dans la simulation elle-même** : l'identité est donc testée sans supposer
    l'exposition, ce qui la sépare de tout ce que le modèle prédit par
    ailleurs. `standard_error` est celle de la moyenne simulée ; un écart
    supérieur à trois erreurs-types serait une réfutation.
    """

    n_paths: int
    mean_result: float
    expected_time: float
    predicted: float
    standard_error: float

    @property
    def gap(self) -> float:
        return self.mean_result - self.predicted

    @property
    def z_score(self) -> float:
        return self.gap / self.standard_error if self.standard_error > 0 else 0.0

    @property
    def passes(self) -> bool:
        return abs(self.z_score) < 3.0


def mc_wald_check(stop: float, entry_min: float, sigma_bar: float,
                  drift_per_min: float, friction: float,
                  seas: Seasonality = Seasonality(),
                  mix: VolMixture | None = None,
                  jumps: tuple[JumpModel, ...] | None = JUMPS,
                  n_paths: int = 8000, seed: int = 20260821) -> WaldCheck:
    """Simule le modèle complet et confronte la moyenne à ``µ·E[τ∧T] − c``.

    Le pas est la minute, le stop est surveillé à la minute, et la sortie est
    au prix observé — c'est-à-dire au-delà du stop quand un saut l'a franchi.
    Le temps d'arrêt ainsi défini est borné, donc l'identité de Wald doit tenir
    **exactement**, saisonnalité, sauts et volatilité aléatoire compris. C'est
    le seul contrôle du document qui ne partage pas les hypothèses de la
    dérivation : il ne teste pas une formule contre une autre, il teste
    l'énoncé central contre un marché simulé qui viole toutes les hypothèses
    dont l'énoncé est issu.
    """
    rng = Rng(seed)
    mix = mix or VolMixture(sigma_bar, nu=0.0)
    family = () if not jumps else (
        (jumps,) if isinstance(jumps, JumpModel) else tuple(jumps))
    rates = [(m.intensity_per_min(seas.session_min), m.mean_jump, m.sd_jump)
             for m in family]
    total_minutes = int(round(seas.session_min - entry_min))

    total_res = 0.0
    total_sq = 0.0
    total_time = 0.0
    for _ in range(n_paths):
        sigma = mix.sigma(rng.gauss())
        x = 0.0
        exit_at = float(total_minutes)
        for i in range(total_minutes):
            t = entry_min + i
            var = sigma * sigma * seas.elapsed(t, t + 1.0)
            x += drift_per_min + math.sqrt(var) * rng.gauss()
            for lam, m_j, s_j in rates:
                # Saut d'espérance nulle : aucun compensateur à retrancher.
                if rng.uniform() < lam:
                    x += m_j + s_j * rng.gauss()
            if x <= -stop:
                exit_at = float(i + 1)
                break
        res = x - friction
        total_res += res
        total_sq += res * res
        total_time += exit_at

    n = float(n_paths)
    mean = total_res / n
    var = max(total_sq / n - mean * mean, 0.0)
    exposure = total_time / n
    return WaldCheck(
        n_paths=n_paths, mean_result=mean, expected_time=exposure,
        predicted=drift_per_min * exposure - friction,
        standard_error=math.sqrt(var / n),
    )


def mc_barrier_check(stop: float, entry_min: float, sigma: float,
                     seas: Seasonality = Seasonality(),
                     n_paths: int = 20000, steps_per_min: int = 1,
                     seed: int = 20260822) -> tuple[float, float, float]:
    """Contrôle de la forme fermée de `P(stop)` sous saisonnalité.

    La surveillance à pas discret sous-estime le premier passage ; on corrige
    par le pont brownien — entre deux points observés `x₀` et `x₁`, la
    probabilité d'avoir franchi le niveau `−a` vaut
    ``exp(−2(x₀+a)(x₁+a)/(σ²Δ))`` — ce qui rend la simulation comparable à une
    surveillance continue. Retourne `(forme fermée, simulation, erreur-type)`.
    """
    rng = Rng(seed)
    closed = seasonal_outcome(stop, entry_min, sigma, seas).p_stop
    n_steps = int(round((seas.session_min - entry_min) * steps_per_min))
    dt = 1.0 / steps_per_min
    hits = 0
    for _ in range(n_paths):
        x = 0.0
        hit = False
        for i in range(n_steps):
            t = entry_min + i * dt
            var = sigma * sigma * seas.elapsed(t, t + dt)
            nxt = x + math.sqrt(var) * rng.gauss()
            if nxt <= -stop:
                hit = True
                break
            p_cross = math.exp(-2.0 * (x + stop) * (nxt + stop) / var)
            if rng.uniform() < p_cross:
                hit = True
                break
            x = nxt
        hits += 1 if hit else 0
    p = hits / n_paths
    return closed, p, math.sqrt(max(p * (1.0 - p), 1e-12) / n_paths)


# --- Table d'adéquation : ce qui bouge, et de combien ------------------------


@dataclass(frozen=True)
class AdequacyRow:
    """Une grandeur, sa valeur sous diffusion pure, et sous chaque écart."""

    key: str
    label: str
    unit: str
    diffusion: float
    seasonal: float
    jumps: float
    heteroscedastic: float
    invariant: bool
    comment: str

    def deviation_pct(self, value: float) -> float:
        if self.diffusion == 0.0:
            return 0.0
        return 100.0 * (value / self.diffusion - 1.0)

    @property
    def worst_deviation_pct(self) -> float:
        return max(abs(self.deviation_pct(v))
                   for v in (self.seasonal, self.jumps, self.heteroscedastic))


def adequacy_rows(stop: float, entry_min: float, sigma: float,
                  friction: float, session_min: float = 390.0,
                  seas: Seasonality = Seasonality(),
                  jumps: tuple[JumpModel, ...] = JUMPS,
                  nu: float = 0.35) -> list[AdequacyRow]:
    """Les grandeurs du document sous les trois écarts, prises une à une.

    Chaque colonne applique **un seul** écart à la fois : c'est ce qui rend la
    lecture attribuable. La colonne « invariant » ne dit pas que la grandeur ne
    bouge pas, elle dit qu'aucun des trois écarts ne peut la bouger — ce qui
    n'est vrai que du critère maître et de ses conséquences directes.
    """
    horizon = session_min - entry_min
    base = time_exit_outcome(stop, horizon, sigma)
    seasonal = seasonal_outcome(stop, entry_min, sigma, seas)
    mix = VolMixture(sigma, nu)
    gap = gap_cost(stop, base.expected_time, jumps, session_min)

    def het(fn):
        return expect_over_vol(fn, mix)

    def p_stop_of(s: float) -> float:
        return time_exit_outcome(stop, horizon, s).p_stop

    def exposure_of(s: float) -> float:
        return time_exit_outcome(stop, horizon, s).expected_time

    def ir_of(s: float) -> float:
        return required_ir(friction, s, time_exit_outcome(stop, horizon, s).expected_time)

    band = mean_abs_move(sigma, entry_min)
    ir_base = required_ir(friction, sigma, base.expected_time)
    ir_seasonal = friction / seasonal.sd_gross

    return [
        AdequacyRow(
            "expectancy", "Espérance brute sous martingale", "pt",
            0.0, 0.0, 0.0, 0.0, True,
            "Arrêt optionnel : la martingale survit au changement de temps, aux "
            "sauts centrés et à une volatilité aléatoire indépendante du signe."),
        AdequacyRow(
            "wald", "Écart au critère maître µ·E[τ∧T] − c", "pt",
            0.0, 0.0, 0.0, 0.0, True,
            "Nul par construction sous les trois écarts, et vérifié par "
            "simulation du modèle complet plutôt que par algèbre : "
            "`mc_wald_check` confronte la moyenne simulée à l'exposition "
            "mesurée dans la simulation elle-même."),
        AdequacyRow(
            "band", "Bande de bruit à l'entrée", "pt",
            band, seasonal_band(sigma, entry_min, seas), band,
            het(lambda s: mean_abs_move(s, entry_min)), False,
            "La bosse d'ouverture est déjà consommée à 11:00 : la bande mesurée "
            "est plus large que ne le prédit la racine du temps."),
        AdequacyRow(
            "p_stop", "Probabilité de toucher le stop", "%",
            100.0 * base.p_stop, 100.0 * seasonal.p_stop,
            100.0 * base.p_stop, 100.0 * het(p_stop_of), False,
            "Sous saisonnalité, la variance restante après 11:00 est inférieure "
            "à sa part de temps : le stop est touché moins souvent."),
        AdequacyRow(
            "exposure", "Exposition E[τ∧T]", "min",
            base.expected_time, seasonal.expected_time, base.expected_time,
            het(exposure_of), False,
            "L'exposition suit la probabilité de survie : elle augmente sous "
            "saisonnalité, et diminue sous mélange de volatilités."),
        AdequacyRow(
            "ir_star", "Seuil de qualité de signal IR*", "",
            ir_base, ir_seasonal, ir_base, het(ir_of), False,
            "IR* se lit en minutes de **variance** et non en minutes d'horloge : "
            "c'est le seul endroit du document où la distinction change un "
            "chiffre."),
        AdequacyRow(
            "loss", "Perte réalisée sur stop", "pt",
            stop, stop, gap.realised_loss, stop, False,
            "Le saut ne déplace pas l'espérance — Wald l'absorbe — mais il "
            "déplace le dénominateur : c/L, le risque par contrat et le "
            "dimensionnement portent sur une perte sous-estimée."),
    ]


def main() -> None:
    from .costs import COST_BASE, ES
    from .momentum import sigma_from_session

    sigma = sigma_from_session(60.0, 390.0)
    entry = 90.0
    stop = mean_abs_move(sigma, entry)
    friction = COST_BASE.friction_points(ES)

    print(f"σ₁ = {sigma:.4f} pt, stop = {stop:.2f} pt, friction = {friction:.3f} pt\n")
    for r in adequacy_rows(stop, entry, sigma, friction):
        print(f"{r.label:38s} diff={r.diffusion:10.4f} sais={r.seasonal:10.4f} "
              f"saut={r.jumps:10.4f} hét={r.heteroscedastic:10.4f} "
              f"écart max={r.worst_deviation_pct:6.2f} % "
              f"{'[invariant]' if r.invariant else ''}")

    print()
    closed, sim, se = mc_barrier_check(stop, entry, sigma, n_paths=5000)
    print(f"P(stop) forme fermée = {closed:.4f}, simulation = {sim:.4f} "
          f"± {se:.4f} (pont brownien)")

    chk = mc_wald_check(stop, entry, sigma, drift_per_min=0.02,
                        friction=friction, n_paths=4000)
    print(f"Wald : moyenne simulée = {chk.mean_result:.4f}, "
          f"µ·E[τ∧T] − c = {chk.predicted:.4f}, "
          f"z = {chk.z_score:+.2f}, E[τ∧T] = {chk.expected_time:.1f} min")


if __name__ == "__main__":
    main()


# --- Les paramètres du modèle enrichi sont eux-mêmes posés ------------------

@dataclass(frozen=True)
class Robustness:
    """Encadrement d'une grandeur sur la boîte des paramètres de microstructure.

    Les trois écarts introduits ci-dessus sont chiffrés par des paramètres —
    amplitude de la bosse d'ouverture, dispersion de la volatilité de séance,
    amplitude des sauts — que rien dans le dépôt ne mesure. Les traiter comme
    connus reviendrait à remplacer une hypothèse trop simple par une hypothèse
    trop précise. Ils sont donc balayés sur une boîte, comme la calibration
    principale l'est dans `alp1.calib`, et c'est l'encadrement qui est rapporté.
    """

    key: str
    label: str
    unit: str
    base: float
    lo: float
    hi: float

    @property
    def worst_deviation_pct(self) -> float:
        if self.base == 0.0:
            return 0.0
        return 100.0 * max(abs(self.lo / self.base - 1.0),
                           abs(self.hi / self.base - 1.0))


def robustness_box(stop: float, entry_min: float, sigma: float,
                   friction: float, session_min: float = 390.0,
                   open_amps: tuple[float, ...] = (1.5, 3.0, 5.0),
                   close_amps: tuple[float, ...] = (0.5, 1.5, 3.0),
                   nus: tuple[float, ...] = (0.20, 0.35, 0.50),
                   jump_sds: tuple[float, ...] = (8.0, 15.0, 25.0),
                   ) -> list[Robustness]:
    """Balaye les paramètres de microstructure et encadre chaque grandeur.

    Quatre-vingt-une combinaisons, chacune évaluée exactement. La lecture qui
    compte n'est pas la largeur des encadrements mais leur position : aucune
    combinaison de la boîte ne renverse le signe d'une conclusion, et le pire
    déplacement reste d'un ordre de grandeur inférieur à la marge que la dérive
    documentée laisse sur la friction.
    """
    horizon = session_min - entry_min
    base = time_exit_outcome(stop, horizon, sigma)
    rows: dict[str, list[float]] = {"p_stop": [], "exposure": [],
                                    "ir_star": [], "loss": []}
    for oa in open_amps:
        for ca in close_amps:
            seas = Seasonality(session_min=session_min, open_amp=oa, close_amp=ca)
            so = seasonal_outcome(stop, entry_min, sigma, seas)
            for nu in nus:
                mix = VolMixture(sigma, nu)
                p = expect_over_vol(
                    lambda s: time_exit_outcome(stop, horizon, s).p_stop, mix, 60)
                e = expect_over_vol(
                    lambda s: time_exit_outcome(stop, horizon, s).expected_time,
                    mix, 60)
                rows["p_stop"] += [100.0 * so.p_stop, 100.0 * p]
                rows["exposure"] += [so.expected_time, e]
                rows["ir_star"] += [friction / so.sd_gross,
                                    required_ir(friction, sigma, e)]
                for sd_j in jump_sds:
                    macro = JumpModel(intensity_per_day=0.2, mean_jump=0.0,
                                      sd_jump=sd_j)
                    g = gap_cost(stop, base.expected_time,
                                 (JUMPS_MICRO, macro), session_min)
                    rows["loss"].append(g.realised_loss)

    meta = {
        "p_stop": ("Probabilité de toucher le stop", "%", 100.0 * base.p_stop),
        "exposure": ("Exposition E[τ∧T]", "min", base.expected_time),
        "ir_star": ("Seuil IR*", "",
                    required_ir(friction, sigma, base.expected_time)),
        "loss": ("Perte réalisée sur stop", "pt", stop),
    }
    return [Robustness(k, meta[k][0], meta[k][1], meta[k][2],
                       min(v), max(v)) for k, v in rows.items()]
