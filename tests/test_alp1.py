"""Tests du noyau quantitatif ALP-1.

Exécution : python -m tests.test_alp1  (ou pytest)
"""

from __future__ import annotations

import math
import unittest

from alp1.barriers import (
    prob_target_before_stop,
    prob_touch_single_barrier,
    required_drift,
)
from alp1.costs import (
    COST_BASE,
    ES,
    breakeven_hit_rate,
    expectancy_r,
    required_reward_risk,
    stop_points,
    trades_for_significance,
    _norm_ppf,
    norm_cdf,
)
from alp1.regime import GammaState, Regime, classify, playbook_for
from alp1.stops import (
    TradeGeometry,
    be_expectancy_cost_r,
    expectancy_r as expectancy_r_managed,
    neutral_post_trigger_drift,
    outcome_probabilities,
    outcome_probabilities_fixed_stop,
    required_conditional_lift,
    sd_r,
    sharpe_per_trade,
    trades_for_t_stat,
)
from alp1.signals import (
    DailyBar,
    Direction,
    VolumeProfile,
    dow_continuation,
    dow_rejection,
    liquidity_persistence_ratio,
    ote_execution_edge,
    ote_zone,
    vwap_band_signal,
)


class TestCosts(unittest.TestCase):
    def test_stop_points(self):
        self.assertAlmostEqual(stop_points(6000, 0.010), 0.60)
        self.assertAlmostEqual(stop_points(6000, 0.005), 0.30)

    def test_breakeven_inverts_required_rr(self):
        for r in (2.0, 3.0, 7.5, 20.0):
            for f in (0.0, 0.1, 0.55, 1.1):
                p = breakeven_hit_rate(r, f)
                self.assertAlmostEqual(required_reward_risk(p, f), r, places=9)

    def test_breakeven_frictionless_is_classic(self):
        for r in (1.0, 2.0, 5.0, 10.0):
            self.assertAlmostEqual(breakeven_hit_rate(r, 0.0), 1.0 / (r + 1.0))

    def test_expectancy_zero_at_breakeven(self):
        for r in (2.0, 5.0, 12.0):
            for f in (0.0, 0.3, 0.9):
                p = breakeven_hit_rate(r, f)
                self.assertAlmostEqual(expectancy_r(p, r, f), 0.0, places=12)

    def test_norm_ppf_cdf_roundtrip(self):
        for p in (0.01, 0.1, 0.5, 0.8, 0.975, 0.999):
            self.assertAlmostEqual(norm_cdf(_norm_ppf(p)), p, places=7)

    def test_sample_size_scales_with_variance(self):
        small = trades_for_significance(0.2, 1.0)
        large = trades_for_significance(0.2, 2.0)
        self.assertAlmostEqual(large / small, 4.0, delta=0.05)


class TestZeroDriftIdentity(unittest.TestCase):
    """Le résultat central du paper.

    Sous un brownien sans drift, l'espérance par trade vaut exactement −c/L,
    indépendamment du ratio R:R retenu.

    Démonstration : avec p = 1/(R+1),
        E = p(R − f) − (1−p)(1 + f)
          = [R − f − R(1 + f)]/(R+1)
          = −f(1 + R)/(R+1) = −f
    """

    def test_expectancy_equals_minus_friction_ratio(self):
        for f in (0.02, 0.11, 0.55, 1.10):
            for r in (1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0):
                p = 1.0 / (r + 1.0)
                self.assertAlmostEqual(expectancy_r(p, r, f), -f, places=12)

    def test_gamblers_ruin_matches_frictionless_breakeven(self):
        a = 0.60
        for r in (2.0, 3.0, 10.0):
            p = prob_target_before_stop(a, r * a, drift_per_min=0.0, sigma_per_min=1.25)
            self.assertAlmostEqual(p, 1.0 / (r + 1.0), places=12)


class TestBarriers(unittest.TestCase):
    def test_drift_increases_target_probability(self):
        a, b = 1.0, 3.0
        p0 = prob_target_before_stop(a, b, 0.0, 1.0)
        p1 = prob_target_before_stop(a, b, 0.5, 1.0)
        p2 = prob_target_before_stop(a, b, 2.0, 1.0)
        self.assertLess(p0, p1)
        self.assertLess(p1, p2)
        self.assertLessEqual(p2, 1.0)

    def test_negative_drift_lowers_probability(self):
        p_neg = prob_target_before_stop(1.0, 3.0, -0.5, 1.0)
        p_zero = prob_target_before_stop(1.0, 3.0, 0.0, 1.0)
        self.assertLess(p_neg, p_zero)
        self.assertGreaterEqual(p_neg, 0.0)

    def test_probability_stable_for_large_drift(self):
        """Pas d'overflow ni de NaN sur drift extrême."""
        for mu in (10.0, 100.0, 1000.0):
            p = prob_target_before_stop(0.3, 0.9, mu, 0.1)
            self.assertFalse(math.isnan(p))
            self.assertTrue(0.0 <= p <= 1.0)

    def test_tight_stop_is_noise_dominated(self):
        """Un stop de ~1 tick est balayé par le bruit avec forte probabilité."""
        p = prob_touch_single_barrier(0.30, sigma_per_min=1.25, horizon_min=1.0)
        self.assertGreater(p, 0.75)

    def test_wide_stop_survives_noise(self):
        p = prob_touch_single_barrier(15.0, sigma_per_min=1.25, horizon_min=5.0)
        self.assertLess(p, 0.05)

    def test_required_drift_decreases_with_stop_width(self):
        fric = COST_BASE.friction_points(ES)
        mus = [
            required_drift(a, 3 * a, 1.25, fric)
            for a in (0.30, 0.60, 3.00, 6.00)
        ]
        self.assertEqual(mus, sorted(mus, reverse=True))

    def test_required_drift_infinite_when_target_below_friction(self):
        self.assertEqual(required_drift(0.05, 0.10, 1.25, friction_points=0.5), math.inf)

    def test_required_drift_achieves_breakeven(self):
        fric = COST_BASE.friction_points(ES)
        a, b = 3.0, 9.0
        mu = required_drift(a, b, 1.25, fric)
        p = prob_target_before_stop(a, b, mu, 1.25)
        self.assertAlmostEqual(p * (b - fric) - (1 - p) * (a + fric), 0.0, places=4)


class TestRegime(unittest.TestCase):
    def test_positive_gamma_is_reversion(self):
        st = GammaState(net_gamma=5e9, spot=6000, flip_level=5900)
        self.assertIs(classify(st), Regime.REVERSION)
        self.assertTrue(playbook_for(st).allow_vwap_fade)
        self.assertFalse(playbook_for(st).allow_breakout)

    def test_negative_gamma_is_momentum(self):
        st = GammaState(net_gamma=-3e9, spot=6000, flip_level=6100)
        self.assertIs(classify(st), Regime.MOMENTUM)
        self.assertFalse(playbook_for(st).allow_vwap_fade)
        self.assertTrue(playbook_for(st).allow_dow_continuation)

    def test_near_flip_is_transition_no_trade(self):
        st = GammaState(net_gamma=1e9, spot=6000, flip_level=5995)
        self.assertIs(classify(st), Regime.TRANSITION)
        pb = playbook_for(st)
        self.assertFalse(any([pb.allow_vwap_fade, pb.allow_dow_continuation,
                              pb.allow_lvn_reversion, pb.allow_breakout]))

    def test_distance_to_flip(self):
        st = GammaState(net_gamma=1.0, spot=6000, flip_level=5940)
        self.assertAlmostEqual(st.distance_to_flip_pct(), 1.0)


class TestSignals(unittest.TestCase):
    def test_dow_continuation_long(self):
        y = DailyBar(5900, 5950, 5890, 5920)
        t = DailyBar(5925, 5980, 5920, 5975)
        self.assertIs(dow_continuation(t, y), Direction.LONG)

    def test_dow_continuation_none_inside_body(self):
        y = DailyBar(5900, 5950, 5890, 5940)
        t = DailyBar(5915, 5945, 5905, 5925)
        self.assertIsNone(dow_continuation(t, y))

    def test_dow_rejection_upper_wick(self):
        bar = DailyBar(open=6000, high=6060, low=5995, close=6010)
        self.assertIs(dow_rejection(bar), Direction.SHORT)

    def test_vwap_band_excludes_sd3(self):
        d, band = vwap_band_signal(price=6030, vwap=6000, sd=10.0)
        self.assertIsNone(d)
        self.assertEqual(band, 3.0)

    def test_vwap_band_signals_sd2(self):
        d, band = vwap_band_signal(price=6020, vwap=6000, sd=10.0)
        self.assertIs(d, Direction.SHORT)
        self.assertEqual(band, 2.0)

    def test_volume_profile_poc_and_nodes(self):
        vp = VolumeProfile({5990: 10, 5995: 100, 6000: 250, 6005: 40, 6010: 5})
        self.assertEqual(vp.poc, 6000)
        self.assertIn(6010, vp.lvn_levels())
        self.assertIn(6000, vp.hvn_levels())

    def test_ote_zone_long_is_below_wick_high(self):
        lo, hi = ote_zone(5980, 6000, Direction.LONG)
        self.assertLess(lo, hi)
        self.assertLess(hi, 6000)
        self.assertGreater(lo, 5980)

    def test_ote_execution_edge_sign(self):
        # 50 % de remplissage à 4R bat une entrée marché à 1.5R.
        self.assertGreater(ote_execution_edge(0.5, 4.0, 1.5), 0)
        # 20 % de remplissage à 4R ne la bat pas.
        self.assertLess(ote_execution_edge(0.2, 4.0, 1.5), 0)

    def test_lpr_detects_pulled_liquidity(self):
        from alp1.signals import BookSnapshot
        pre = BookSnapshot(level=6000, resting_size=2000, timestamp_s=0.0)
        at = BookSnapshot(level=6000, resting_size=200, timestamp_s=30.0)
        self.assertAlmostEqual(liquidity_persistence_ratio(pre, at), 0.1)


class TestStopManagement(unittest.TestCase):
    """La mise à breakeven, et le théorème d'invariance qui la gouverne."""

    A = 3.0        # stop 0.050 % d'un indice à 6000
    B = 9.0        # R:R = 3
    C = 0.33       # friction de référence, en points
    SIGMA = 1.25

    def geom(self, trigger=None):
        return TradeGeometry(self.A, self.B, self.C, trigger)

    def test_expectancy_is_minus_friction_ratio_for_any_trigger(self):
        """Le résultat central : sous martingale, E[R] = −c/L quel que soit g."""
        for trigger in (0.5, 1.0, 2.0, 4.0, 8.0):
            with self.subTest(trigger=trigger):
                e = expectancy_r_managed(self.geom(trigger), 0.0, self.SIGMA)
                self.assertAlmostEqual(e, -self.C / self.A, places=12)

    def test_apparent_hit_rate_is_also_invariant(self):
        """Le hit rate affiché ne bouge pas non plus : a/(a+b) dans tous les cas."""
        expected = self.A / (self.A + self.B)
        for trigger in (0.5, 1.0, 2.0, 4.0):
            with self.subTest(trigger=trigger):
                o = outcome_probabilities(self.geom(trigger), 0.0, self.SIGMA)
                self.assertAlmostEqual(o.apparent_hit_rate, expected, places=12)

    def test_probabilities_sum_to_one(self):
        o = outcome_probabilities(self.geom(3.0), 0.02, self.SIGMA)
        self.assertAlmostEqual(o.p_target + o.p_breakeven + o.p_stop, 1.0, places=12)

    def test_be_shifts_mass_from_loss_to_scratch(self):
        """Elle réduit les pertes pleines et les gagnants dans la même proportion."""
        fixed = outcome_probabilities(self.geom(None), 0.0, self.SIGMA)
        managed = outcome_probabilities(self.geom(3.0), 0.0, self.SIGMA)
        self.assertLess(managed.p_stop, fixed.p_stop)
        self.assertLess(managed.p_target, fixed.p_target)
        self.assertGreater(managed.p_breakeven, 0.0)

    def test_be_compresses_dispersion(self):
        self.assertLess(
            sd_r(self.geom(3.0), 0.0, self.SIGMA),
            sd_r(self.geom(None), 0.0, self.SIGMA),
        )

    def test_be_worsens_sharpe_under_martingale(self):
        """Espérance inchangée et dispersion réduite : le ratio empire."""
        self.assertLess(
            sharpe_per_trade(self.geom(3.0), 0.0, self.SIGMA),
            sharpe_per_trade(self.geom(None), 0.0, self.SIGMA),
        )

    def test_cost_is_zero_under_martingale(self):
        self.assertAlmostEqual(
            be_expectancy_cost_r(self.geom(3.0), 0.0, self.SIGMA), 0.0, places=12
        )

    def test_cost_is_positive_under_positive_post_trigger_drift(self):
        """La règle coûte précisément quand la confirmation annonce du drift."""
        cost = be_expectancy_cost_r(self.geom(3.0), 0.02, self.SIGMA, 0.02)
        self.assertGreater(cost, 0.0)

    def test_cost_is_negative_under_negative_post_trigger_drift(self):
        """Elle ne paie que si la confirmation annonce un retournement."""
        cost = be_expectancy_cost_r(self.geom(3.0), 0.02, self.SIGMA, -0.02)
        self.assertLess(cost, 0.0)

    def test_neutral_post_trigger_drift_is_zero(self):
        """Le seuil de neutralité de la règle est exactement µ₂ = 0."""
        mu2 = neutral_post_trigger_drift(self.geom(3.0), 0.02, self.SIGMA)
        self.assertAlmostEqual(mu2, 0.0, places=6)

    def test_earlier_trigger_destroys_more_edge(self):
        """Plus le stop remonte tôt, plus la part d'edge détruite est grande."""
        mu = 0.04
        costs = [
            be_expectancy_cost_r(self.geom(g), mu, self.SIGMA, mu)
            for g in (1.5, 3.0, 6.0)
        ]
        self.assertGreater(costs[0], costs[1])
        self.assertGreater(costs[1], costs[2])

    def test_fixed_stop_counterfactual_matches_gamblers_ruin(self):
        o = outcome_probabilities_fixed_stop(self.geom(3.0), 0.0, self.SIGMA)
        self.assertAlmostEqual(o.p_target, self.A / (self.A + self.B), places=12)
        self.assertEqual(o.p_breakeven, 0.0)

    def test_required_lift_matches_closed_form(self):
        """Δp = (c/a)/(R+1), la forme fermée du lift conditionnel."""
        g = self.geom()
        expected = (self.C / self.A) / (g.reward_risk + 1.0)
        self.assertAlmostEqual(required_conditional_lift(g), expected, places=12)

    def test_required_lift_scales_inversely_with_stop_width(self):
        """L'argument central du changement de paramétrage du stop.

        À R:R constant, Δp ∝ c/a : élargir le stop d'un facteur k divise le
        lift conditionnel requis par ce même facteur k. Passer de 0,010 % à
        0,050 % divise donc l'exigence par exactement cinq.
        """
        tight = TradeGeometry(0.6, 1.8, self.C)   # 0,010 % d'un indice à 6000
        wide = TradeGeometry(3.0, 9.0, self.C)    # 0,050 %
        self.assertAlmostEqual(
            required_conditional_lift(tight) / required_conditional_lift(wide),
            5.0,
            places=10,
        )

    def test_sample_size_infinite_without_edge(self):
        self.assertEqual(trades_for_t_stat(self.geom(3.0), 0.0, self.SIGMA), math.inf)

    def test_be_inflates_required_sample_size(self):
        mu = 0.04
        self.assertGreater(
            trades_for_t_stat(self.geom(3.0), mu, self.SIGMA, mu),
            trades_for_t_stat(self.geom(None), mu, self.SIGMA),
        )

    def test_invalid_trigger_rejected(self):
        with self.assertRaises(ValueError):
            TradeGeometry(self.A, self.B, self.C, self.B + 1.0)
        with self.assertRaises(ValueError):
            TradeGeometry(self.A, self.B, self.C, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
