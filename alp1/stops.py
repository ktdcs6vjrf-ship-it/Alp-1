"""Gestion dynamique du stop : mise à breakeven, et son coût exact.

Ce module traite la règle de gestion du stop d'ALP-1 :

    stop initial à `a` points, puis déplacement du stop au point d'entrée
    (« mise à BE ») dès qu'une confirmation d'orderflow est prise — apparition
    d'un mur de liquidité protecteur, ou prise de liquidité visible en L2.

La confirmation est modélisée par un *niveau déclencheur* `g` situé entre
l'entrée et le target. C'est une modélisation volontairement favorable à la
règle : elle suppose que la confirmation coïncide avec un progrès du prix en
faveur de la position. Une confirmation qui arriverait sans progrès de prix
laisserait le stop initial actif plus longtemps, donc dégraderait davantage le
résultat.

Résultat central du module — et extension du théorème d'invariance d'ALP-1 :

    Sous un mouvement brownien sans drift, l'espérance nette d'un trade géré
    par mise à BE vaut exactement −c, quels que soient a, g et b.

Preuve directe (théorème d'arrêt optionnel). Le prix est une martingale, les
barrières bornent le processus et le temps de sortie est fini presque sûrement ;
donc E[X_τ] = X_0 = 0 pour *toute* règle d'arrêt. La mise à BE est une règle
d'arrêt. Il en va de même du stop suiveur, des prises partielles et de tout
autre schéma de gestion : aucun ne crée d'espérance, tous laissent −c par
aller-retour. Ils ne font que redistribuer la masse de probabilité entre les
issues.

La conséquence pratique est contre-intuitive et importante : la mise à BE
n'améliore pas l'espérance, elle *abaisse le taux de réussite affiché* (elle
transforme des gagnants potentiels en trades nuls) tout en abaissant le taux de
perte pleine. Sous drift positif — c'est-à-dire précisément quand le signal
fonctionne — elle coûte strictement de l'espérance. Sa justification est donc
un arbitrage de variance, jamais un argument d'edge.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .barriers import prob_target_before_stop


@dataclass(frozen=True)
class TradeGeometry:
    """Géométrie d'un trade, en points d'indice.

    Parameters
    ----------
    stop:
        `a` — distance du stop initial sous l'entrée.
    target:
        `b` — distance du target au-dessus de l'entrée.
    friction:
        `c` — friction aller-retour, en points. Payée dans *toutes* les issues,
        y compris la sortie à BE.
    be_trigger:
        `g` — progrès de prix, en points, à partir duquel la confirmation
        d'orderflow est prise et le stop remonté à l'entrée. `None` désactive
        la règle et redonne un trade à barrières fixes.
    """

    stop: float
    target: float
    friction: float = 0.0
    be_trigger: float | None = None

    def __post_init__(self) -> None:
        if self.stop <= 0 or self.target <= 0:
            raise ValueError("stop et target doivent être > 0")
        if self.friction < 0:
            raise ValueError("friction doit être >= 0")
        if self.be_trigger is not None and not 0.0 < self.be_trigger < self.target:
            raise ValueError("be_trigger doit être dans ]0, target[")

    @property
    def reward_risk(self) -> float:
        return self.target / self.stop

    @property
    def friction_ratio(self) -> float:
        """c/L — la friction rapportée au risque nominal."""
        return self.friction / self.stop


@dataclass(frozen=True)
class Outcomes:
    """Distribution des issues d'un trade géré.

    `p_breakeven` est nulle quand la règle de BE est désactivée.
    """

    p_target: float
    p_breakeven: float
    p_stop: float

    @property
    def apparent_hit_rate(self) -> float:
        """Taux de réussite affiché : gagnants / trades tranchés.

        Les trades sortis à BE sont comptés comme neutres et retirés du
        dénominateur — la convention usuelle d'un journal de trading, et la
        raison pour laquelle un hit rate publié n'est pas comparable d'une
        gestion à l'autre.
        """
        decided = self.p_target + self.p_stop
        return self.p_target / decided if decided > 0 else 0.0


def outcome_probabilities(
    geom: TradeGeometry,
    drift_per_min: float = 0.0,
    sigma_per_min: float = 1.0,
    drift_post_trigger: float | None = None,
) -> Outcomes:
    """Probabilités des trois issues sous X_t = µt + σW_t, avec mise à BE.

    Le processus se décompose en deux phases par la propriété de Markov forte,
    le déclencheur `g` servant de frontière :

      phase 1 — de l'entrée, barrières en −a (stop initial) et +g (déclencheur)
      phase 2 — de +g, barrières en 0 (stop remonté à BE) et +b (target)

    d'où p_TP = P₁·P₂, p_BE = P₁·(1−P₂), p_SL = 1−P₁.

    `drift_post_trigger` est le drift **conditionnel à la confirmation**. C'est
    le paramètre qui décide seul de la valeur de la règle, et il doit être
    distingué du drift d'entrée : la confirmation d'orderflow ne se réduit pas à
    un progrès de prix, elle prétend apporter de l'information. Laissé à `None`,
    il vaut `drift_per_min` — hypothèse d'un déclencheur non informatif.

    Quand `be_trigger` vaut `None`, le trade est à barrières fixes et la règle
    ne s'applique pas ; `drift_post_trigger` est alors ignoré.
    """
    a, b, g = geom.stop, geom.target, geom.be_trigger
    mu1 = drift_per_min
    mu2 = mu1 if drift_post_trigger is None else drift_post_trigger

    if g is None:
        p = prob_target_before_stop(a, b, mu1, sigma_per_min)
        return Outcomes(p_target=p, p_breakeven=0.0, p_stop=1.0 - p)

    p1 = prob_target_before_stop(a, g, mu1, sigma_per_min)
    p2 = prob_target_before_stop(g, b - g, mu2, sigma_per_min)
    return Outcomes(
        p_target=p1 * p2,
        p_breakeven=p1 * (1.0 - p2),
        p_stop=1.0 - p1,
    )


def outcome_probabilities_fixed_stop(
    geom: TradeGeometry,
    drift_per_min: float = 0.0,
    sigma_per_min: float = 1.0,
    drift_post_trigger: float | None = None,
) -> Outcomes:
    """Contrefactuel de la règle : même trade, stop laissé en place.

    Même géométrie et même trajectoire de drift que `outcome_probabilities` —
    le déclencheur `g` reste la frontière entre les deux régimes de drift — mais
    le stop demeure en −a au lieu d'être remonté. En phase 2, les barrières sont
    donc en −a (à g + a sous le niveau atteint) et +b.

    C'est la seule comparaison qui isole l'effet de la règle : à drift identique,
    seule la position du stop diffère. Comparer la gestion à BE sous drift
    conditionnel à un trade à barrières fixes sous drift *inconditionnel*
    attribuerait à la règle un mérite qui revient au signal de confirmation.
    """
    a, b, g = geom.stop, geom.target, geom.be_trigger
    mu1 = drift_per_min
    mu2 = mu1 if drift_post_trigger is None else drift_post_trigger

    if g is None:
        p = prob_target_before_stop(a, b, mu1, sigma_per_min)
        return Outcomes(p_target=p, p_breakeven=0.0, p_stop=1.0 - p)

    p1 = prob_target_before_stop(a, g, mu1, sigma_per_min)
    p2 = prob_target_before_stop(g + a, b - g, mu2, sigma_per_min)
    return Outcomes(p_target=p1 * p2, p_breakeven=0.0, p_stop=1.0 - p1 * p2)


def _moments(o: Outcomes, geom: TradeGeometry) -> tuple[float, float]:
    """(espérance, écart-type) en R, pour une distribution d'issues donnée."""
    a, b, c = geom.stop, geom.target, geom.friction
    values = ((b - c) / a, -c / a, -(a + c) / a)
    probs = (o.p_target, o.p_breakeven, o.p_stop)
    mean = sum(p * v for p, v in zip(probs, values))
    var = sum(p * (v - mean) ** 2 for p, v in zip(probs, values))
    return mean, math.sqrt(max(0.0, var))


def expectancy_r(
    geom: TradeGeometry,
    drift_per_min: float = 0.0,
    sigma_per_min: float = 1.0,
    drift_post_trigger: float | None = None,
) -> float:
    """Espérance nette par trade, en multiples du risque nominal L = a.

        E[R] = p_TP·(b − c)/a + p_BE·(−c/a) + p_SL·(−(a + c)/a)

    À µ = 0 et déclencheur non informatif, cette expression vaut exactement
    −c/a, pour tout (a, g, b) — c'est le théorème d'invariance du module.
    """
    o = outcome_probabilities(geom, drift_per_min, sigma_per_min, drift_post_trigger)
    return _moments(o, geom)[0]


def sd_r(
    geom: TradeGeometry,
    drift_per_min: float = 0.0,
    sigma_per_min: float = 1.0,
    drift_post_trigger: float | None = None,
) -> float:
    """Écart-type du résultat par trade, en R.

    C'est la seule dimension sur laquelle la mise à BE agit sous martingale :
    elle comprime la dispersion. Encore faut-il que l'espérance soit positive
    pour que cette compression soit un gain plutôt qu'une perte de lisibilité.
    """
    o = outcome_probabilities(geom, drift_per_min, sigma_per_min, drift_post_trigger)
    return _moments(o, geom)[1]


def sharpe_per_trade(
    geom: TradeGeometry,
    drift_per_min: float = 0.0,
    sigma_per_min: float = 1.0,
    drift_post_trigger: float | None = None,
) -> float:
    """Ratio espérance / écart-type par trade.

    Multiplier par √N donne le t-statistique attendu sur N trades : c'est la
    quantité qui décide du nombre de trades nécessaires à la validation, et
    donc du temps calendaire avant qu'un edge supposé devienne démontrable.
    """
    o = outcome_probabilities(geom, drift_per_min, sigma_per_min, drift_post_trigger)
    mean, sd = _moments(o, geom)
    return mean / sd if sd > 0 else 0.0


def trades_for_t_stat(
    geom: TradeGeometry,
    drift_per_min: float = 0.0,
    sigma_per_min: float = 1.0,
    drift_post_trigger: float | None = None,
    t_target: float = 2.0,
) -> float:
    """Nombre de trades requis pour atteindre un t-statistique donné.

        N = (t / SR_par_trade)²

    Retourne l'infini si l'espérance n'est pas positive : aucun échantillon,
    si grand soit-il, ne rend significative une espérance nulle ou négative.
    """
    sr = sharpe_per_trade(geom, drift_per_min, sigma_per_min, drift_post_trigger)
    if sr <= 0:
        return math.inf
    return (t_target / sr) ** 2


def be_expectancy_cost_r(
    geom: TradeGeometry,
    drift_per_min: float = 0.0,
    sigma_per_min: float = 1.0,
    drift_post_trigger: float | None = None,
) -> float:
    """Coût en R de la mise à BE, face au même trade stop laissé en place.

        coût = E[R | stop fixe] − E[R | mise à BE]

    Les deux termes sont évalués sous la même trajectoire de drift (µ avant le
    déclencheur, `drift_post_trigger` après), de sorte que l'écart mesure la
    règle et non le contenu informatif de la confirmation.

    Nul sous martingale. Strictement positif quand le drift post-confirmation
    est positif : remonter le stop coupe alors des positions dont la
    continuation avait une espérance favorable. Négatif — la règle devient
    payante — seulement si la confirmation marque en réalité l'épuisement ou le
    retournement du drift.
    """
    if geom.be_trigger is None:
        return 0.0
    o_fix = outcome_probabilities_fixed_stop(
        geom, drift_per_min, sigma_per_min, drift_post_trigger
    )
    o_be = outcome_probabilities(geom, drift_per_min, sigma_per_min, drift_post_trigger)
    return _moments(o_fix, geom)[0] - _moments(o_be, geom)[0]


def neutral_post_trigger_drift(
    geom: TradeGeometry,
    drift_per_min: float = 0.0,
    sigma_per_min: float = 1.0,
    lo: float = -5.0,
    hi: float = 5.0,
    tol: float = 1e-10,
) -> float:
    """Drift post-confirmation qui rend la mise à BE exactement neutre.

    Résout `be_expectancy_cost_r(µ₂) = 0` par bissection. Le coût de la règle
    étant croissant en µ₂, la racine est unique sur l'intervalle.

    Lecture opérationnelle : c'est le seuil que la confirmation d'orderflow doit
    battre *par le bas* pour que remonter le stop soit justifié. Un déclencheur
    qui annonce un drift supérieur à ce seuil rend la règle coûteuse ; seul un
    déclencheur qui annonce un drift inférieur la rend profitable.
    """
    def f(mu2: float) -> float:
        return be_expectancy_cost_r(geom, drift_per_min, sigma_per_min, mu2)

    f_lo, f_hi = f(lo), f(hi)
    if f_lo * f_hi > 0:
        return math.nan
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


def required_conditional_lift(geom: TradeGeometry) -> float:
    """Hausse de P(TP avant SL) requise, au-dessus du référentiel martingale.

    À barrières fixes, la martingale donne p₀ = a/(a+b) et l'équilibre après
    friction exige p* = (1 + c/a)/(R + 1). La quantité

        Δp = p* − p₀ = (c/a)/(R + 1)

    est le *lift conditionnel* : le nombre de points de pourcentage que le
    signal doit ajouter au taux de touche du target pour seulement rembourser
    la friction.

    C'est la statistique la plus utile du dispositif de validation, parce
    qu'elle se mesure directement sur données historiques — compter, sur les
    signaux, la fréquence empirique de « +b touché avant −a » et la comparer à
    a/(a+b) — sans simuler aucun P&L, sans hypothèse de gestion, et sans
    aucun paramètre libre à ajuster.
    """
    p0 = geom.stop / (geom.stop + geom.target)
    p_star = (1.0 + geom.friction_ratio) / (geom.reward_risk + 1.0)
    return p_star - p0


def trades_per_day_to_significance(n_trades: int, trades_per_day: float) -> float:
    """Nombre de jours de bourse requis pour atteindre N trades."""
    if trades_per_day <= 0:
        raise ValueError("trades_per_day doit être > 0")
    return n_trades / trades_per_day
