"""Stress-tests : queues, sauts, scénarios, et le test de stress inversé.

Un stop n'est pas une garantie de perte maximale. C'est un ordre au marché
conditionnel, et sa protection ne vaut que tant que le prix passe par tous
les niveaux intermédiaires. Un saut ne le fait pas. Sur une stratégie dont
tout le dimensionnement repose sur un risque de trois points, c'est **le**
risque du dispositif, et il est absent de toute la première partie du papier,
qui suppose une diffusion continue.

Ce module le chiffre, et chiffre avec lui les autres formes de stress que la
diffusion ne représente pas :

* **VaR et ES paramétriques**, gaussiens puis corrigés par Cornish-Fisher —
  la correction est ici indispensable, la loi d'un trade 1:20 ayant une
  asymétrie proche de 4 et un excès de kurtosis proche de 16 ;
* **théorie des valeurs extrêmes** : dépassement de seuil, loi de Pareto
  généralisée, estimateur de Hill, et la lecture de l'indice de queue ;
* **sauts** : modèle de Merton, probabilité de franchir le stop sans y être
  exécuté, et surcoût espéré ;
* **scénarios historiques**, ramenés en unités de risque de la stratégie ;
* **stress inversé** : non pas « que perd-on dans tel scénario ? » mais
  « quel scénario efface une année d'espérance ? » — la seule formulation qui
  ne dépende pas du choix des scénarios.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .costs import _norm_ppf, norm_cdf
from .pathstats import TradeLaw


# --- VaR et Expected Shortfall ---------------------------------------------


def var_gaussian(mean: float, sd: float, confidence: float = 0.99) -> float:
    """VaR gaussienne, exprimée en perte positive.

    `VaR_α = −(µ + σ·Φ⁻¹(1 − α))`. Sur une loi asymétrique elle est fausse
    dans les deux sens à la fois : elle surestime le risque d'une loi à
    droite longue en niveau courant, et sous-estime celui de ses queues.
    """
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence doit être dans ]0, 1[")
    return -(mean + sd * _norm_ppf(1.0 - confidence))


def es_gaussian(mean: float, sd: float, confidence: float = 0.99) -> float:
    """Expected Shortfall gaussienne : `−µ + σ·φ(Φ⁻¹(α))/(1 − α)`.

    Sous-additive, contrairement à la VaR, donc cohérente au sens d'Artzner :
    c'est la mesure que retient la réglementation bancaire depuis 2016, et la
    seule des deux qui ne récompense pas la concentration du risque.
    """
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence doit être dans ]0, 1[")
    z = _norm_ppf(confidence)
    phi = math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
    return -mean + sd * phi / (1.0 - confidence)


def cornish_fisher_quantile(confidence: float, skew: float,
                            excess_kurtosis: float) -> float:
    """Quantile corrigé de Cornish-Fisher, en écarts-types.

        z_cf = z + (z² − 1)γ₃/6 + (z³ − 3z)γ₄/24 − (2z³ − 5z)γ₃²/36

    Développement d'Edgeworth inversé à l'ordre 4. Il n'est valable que pour
    des asymétries et des excès modérés ; au-delà, le développement cesse
    d'être monotone en `z` et la « correction » produit des quantiles qui se
    croisent. C'est précisément ce qui arrive à la loi d'un trade 1:20, et le
    module le signale plutôt que de le masquer — voir
    `cornish_fisher_is_valid`.
    """
    z = _norm_ppf(1.0 - confidence)
    return (z
            + (z * z - 1.0) * skew / 6.0
            + (z**3 - 3.0 * z) * excess_kurtosis / 24.0
            - (2.0 * z**3 - 5.0 * z) * skew**2 / 36.0)


def cornish_fisher_is_valid(skew: float, excess_kurtosis: float) -> bool:
    """Le développement est-il monotone sur la plage utile des quantiles ?

    Contrôle direct : on vérifie que `z ↦ z_cf(z)` est croissante sur
    `[−4, 4]`. Une réponse négative signifie que la correction ne définit pas
    une loi, et qu'aucun de ses quantiles n'est interprétable.
    """
    prev = -math.inf
    for k in range(-40, 41):
        z = k / 10.0
        v = (z + (z * z - 1.0) * skew / 6.0 + (z**3 - 3.0 * z) * excess_kurtosis / 24.0
             - (2.0 * z**3 - 5.0 * z) * skew**2 / 36.0)
        if v < prev:
            return False
        prev = v
    return True


def var_cornish_fisher(mean: float, sd: float, skew: float,
                       excess_kurtosis: float, confidence: float = 0.99) -> float:
    """VaR corrigée des moments d'ordre 3 et 4."""
    return -(mean + sd * cornish_fisher_quantile(confidence, skew, excess_kurtosis))


def var_from_law(law: TradeLaw, confidence: float = 0.99) -> float:
    """VaR exacte de la loi discrète du trade — sans approximation gaussienne."""
    return -law.quantile(1.0 - confidence)


def es_from_law(law: TradeLaw, confidence: float = 0.99) -> float:
    """Expected Shortfall exacte : moyenne des pertes au-delà de la VaR.

    Calculée sur la loi elle-même, avec traitement correct de l'atome qui
    chevauche le seuil : sa probabilité est scindée au prorata, faute de quoi
    l'ES d'une loi discrète saute d'un atome à l'autre.
    """
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence doit être dans ]0, 1[")
    tail = 1.0 - confidence
    ordered = sorted(zip(law.values, law.probs))
    acc, total = 0.0, 0.0
    for v, p in ordered:
        take = min(p, tail - acc)
        if take <= 0:
            break
        total += take * v
        acc += take
    return -total / tail if tail > 0 else 0.0


# --- Théorie des valeurs extrêmes ------------------------------------------


@dataclass(frozen=True)
class GPDFit:
    """Ajustement de Pareto généralisée sur les dépassements d'un seuil."""

    threshold: float
    shape: float        # ξ — indice de queue ; > 0 = queue lourde
    scale: float        # β
    n_exceed: int
    n_total: int

    @property
    def exceedance_rate(self) -> float:
        return self.n_exceed / self.n_total if self.n_total else 0.0

    @property
    def has_finite_variance(self) -> bool:
        """La variance n'existe que si `ξ < ½`. L'espérance, que si `ξ < 1`."""
        return self.shape < 0.5


def fit_gpd(losses: list[float], threshold: float) -> GPDFit:
    """Ajustement d'une Pareto généralisée par la méthode des moments.

    Sur les dépassements `y = x − u`, la GPD a pour moyenne `β/(1 − ξ)` et
    pour variance `β²/((1 − ξ)²(1 − 2ξ))`. L'inversion donne des estimateurs
    explicites, sans optimisation :

        ξ̂ = ½(1 − ȳ²/s²),   β̂ = ½·ȳ·(ȳ²/s² + 1).

    Moins efficaces que le maximum de vraisemblance, mais fermés, stables sur
    petits échantillons, et sans point de départ à choisir — ce qui est la
    propriété qui compte dans un dépôt qui doit se reconstruire à l'identique.
    """
    exceed = [x - threshold for x in losses if x > threshold]
    n_ex = len(exceed)
    if n_ex < 2:
        raise ValueError("il faut au moins deux dépassements du seuil")
    mean = sum(exceed) / n_ex
    var = sum((y - mean) ** 2 for y in exceed) / (n_ex - 1)
    if var <= 0:
        raise ValueError("dépassements dégénérés")
    ratio = mean * mean / var
    shape = 0.5 * (1.0 - ratio)
    scale = 0.5 * mean * (ratio + 1.0)
    return GPDFit(threshold, shape, max(scale, 1e-12), n_ex, len(losses))


def var_evt(fit: GPDFit, confidence: float = 0.999) -> float:
    """VaR extrapolée par la GPD, au-delà du plus grand point observé.

        VaR_α = u + (β/ξ)·[((n/N_u)(1 − α))^(−ξ) − 1]

    C'est le seul estimateur du module qui autorise une extrapolation hors de
    l'échantillon, et c'est sa raison d'être : une VaR à 99,9 % lue sur mille
    observations est un maximum empirique déguisé, pas une estimation.
    """
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence doit être dans ]0, 1[")
    rate = fit.exceedance_rate
    if rate <= 0:
        raise ValueError("aucun dépassement")
    ratio = (1.0 - confidence) / rate
    if abs(fit.shape) < 1e-9:
        return fit.threshold - fit.scale * math.log(ratio)
    return fit.threshold + (fit.scale / fit.shape) * (ratio ** (-fit.shape) - 1.0)


def es_evt(fit: GPDFit, confidence: float = 0.999) -> float:
    """ES extrapolée : `(VaR + β − ξ·u)/(1 − ξ)`. Infinie si `ξ ≥ 1`."""
    if fit.shape >= 1.0:
        return math.inf
    v = var_evt(fit, confidence)
    return (v + fit.scale - fit.shape * fit.threshold) / (1.0 - fit.shape)


def hill_estimator(losses: list[float], k: int) -> float:
    """Indice de queue de Hill sur les `k` plus grandes pertes.

        ξ̂ = (1/k)·Σ_{i=1}^{k} ln(X_(i)) − ln(X_(k+1))

    Estimateur de référence pour les queues de Pareto. Sa sensibilité au
    choix de `k` est bien connue et n'est pas un défaut d'implémentation :
    c'est le compromis biais-variance de toute estimation de queue, et il
    doit être exposé, non réglé une fois pour toutes.
    """
    s = sorted((x for x in losses if x > 0), reverse=True)
    if k < 1 or k + 1 > len(s):
        raise ValueError("k hors bornes")
    log_k1 = math.log(s[k])
    return sum(math.log(s[i]) - log_k1 for i in range(k)) / k


# --- Sauts : ce que le stop ne protège pas ---------------------------------


@dataclass(frozen=True)
class JumpModel:
    """Sauts de Merton : intensité de Poisson, amplitude gaussienne.

    `intensity_per_day` est le nombre moyen de sauts par séance,
    `mean_jump` et `sd_jump` l'amplitude en points d'indice.
    """

    intensity_per_day: float
    mean_jump: float
    sd_jump: float

    def intensity_per_min(self, session_min: float) -> float:
        return self.intensity_per_day / session_min


def prob_jump_during_trade(model: JumpModel, exposure_min: float,
                           session_min: float) -> float:
    """`P(au moins un saut pendant l'exposition)` : `1 − e^{−λτ}`.

    L'exposition, et non la durée de séance, est la bonne échelle : c'est
    l'identité du critère maître (équation 6) qui revient — tout se paie à
    l'exposition, le risque de saut compris.
    """
    lam = model.intensity_per_min(session_min)
    return 1.0 - math.exp(-lam * exposure_min)


def expected_slippage_beyond_stop(model: JumpModel, stop_points: float) -> float:
    """Surcoût espéré d'un saut qui franchit le stop, en points.

    `E[(|J| − a)⁺]` pour `J ~ N(m, s)`, calculé exactement des deux côtés :

        E[(J − a)⁺] = (m − a)·Φ((m − a)/s) + s·φ((m − a)/s)

    et symétriquement pour la queue basse. Ce surcoût **s'ajoute** à la perte
    nominale : le trade ne perd pas `a`, il perd `a` plus cette quantité.
    """
    if stop_points <= 0:
        raise ValueError("stop_points doit être > 0")
    m, s = model.mean_jump, model.sd_jump
    if s <= 0:
        raise ValueError("sd_jump doit être > 0")

    def upper(a: float) -> float:
        z = (m - a) / s
        return (m - a) * norm_cdf(z) + s * math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)

    def lower(a: float) -> float:
        z = (-a - m) / s
        return (-a - m) * norm_cdf(z) + s * math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)

    return upper(stop_points) + lower(stop_points)


def jump_adjusted_expectancy(law: TradeLaw, model: JumpModel,
                             stop_points: float, exposure_min: float,
                             session_min: float) -> float:
    """Espérance par trade corrigée du risque de saut, en `R`.

        E[R]_ajustée = E[R] − P(saut)·E[(|J| − a)⁺]/a

    Le saut ne déplace pas la moyenne du prix — il est centré — mais il
    déplace celle du **trade**, parce que le stop tronque le gain et non la
    perte. C'est une asymétrie de la géométrie, pas du marché : elle survit à
    un saut d'espérance nulle, et c'est ce qui la rend inéliminable.
    """
    p = prob_jump_during_trade(model, exposure_min, session_min)
    excess = expected_slippage_beyond_stop(model, stop_points)
    return law.mean - p * excess / stop_points


# --- Scénarios et stress inversé -------------------------------------------


@dataclass(frozen=True)
class Scenario:
    """Un scénario de marché, en variation d'indice sur la fenêtre indiquée."""

    label: str
    move_pct: float          # variation de l'indice, en pourcentage
    window: str              # fenêtre sur laquelle elle se produit


# Ordres de grandeur publics des mouvements d'indice les plus cités. Ils
# servent d'échelle, non de prévision : le papier ne contient aucune donnée de
# marché, et ces valeurs sont des amplitudes de référence arrondies.
SCENARIOS: tuple[Scenario, ...] = (
    Scenario("Krach de 1987", -20.5, "séance"),
    Scenario("Octobre 2008", -9.0, "séance"),
    Scenario("Flash crash 2010", -5.7, "trente minutes"),
    Scenario("Février 2018", -4.1, "séance"),
    Scenario("Mars 2020", -12.0, "séance"),
    Scenario("Ouverture en écart", -2.0, "instantané"),
)


def scenario_loss_r(scenario: Scenario, index_level: float,
                    stop_points: float, fill_fraction: float = 1.0) -> float:
    """Perte d'une position, en unités de risque `R`, sous un scénario.

    `fill_fraction` est la part du mouvement effectivement subie avant
    exécution du stop : 0 si le stop est servi au niveau prévu, 1 si le prix
    franchit d'un bloc toute l'amplitude. Un stop de trois points face à un
    mouvement de 2 % de l'indice — 120 points — représente quarante fois le
    risque nominal si rien ne s'interpose, et le multiplicateur ne dépend que
    du rapport des deux distances.
    """
    if stop_points <= 0:
        raise ValueError("stop_points doit être > 0")
    move = abs(scenario.move_pct) / 100.0 * index_level
    return 1.0 + fill_fraction * max(0.0, move - stop_points) / stop_points


def reverse_stress_move_pct(law: TradeLaw, trades_per_year: float,
                            index_level: float, stop_points: float) -> float:
    """Amplitude du choc qui efface exactement une année d'espérance.

    On résout en `m` : `m·index/100 − a = N·E[R]·a`, soit

        m = 100·a·(1 + N·E[R])/index.

    C'est le stress-test inversé — la question posée dans le sens où elle est
    décidable. Elle ne demande pas de choisir des scénarios, elle produit le
    seul scénario qui compte, et le compare ensuite à ce que l'histoire
    documente. Retourne `+∞` si l'espérance est nulle ou négative, cas où
    aucune année de gain n'existe à effacer.
    """
    if law.mean <= 0:
        return math.inf
    if index_level <= 0 or stop_points <= 0:
        raise ValueError("index_level et stop_points doivent être > 0")
    return 100.0 * stop_points * (1.0 + trades_per_year * law.mean) / index_level


def stress_summary(law: TradeLaw, index_level: float, stop_points: float,
                   fill_fraction: float = 1.0) -> list[tuple[str, str, float]]:
    """Table de scénarios : libellé, fenêtre, perte en `R`."""
    return [(s.label, s.window, scenario_loss_r(s, index_level, stop_points,
                                                fill_fraction))
            for s in SCENARIOS]
