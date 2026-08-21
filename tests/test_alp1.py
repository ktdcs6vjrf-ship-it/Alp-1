"""Tests du noyau quantitatif ALP-1.

Exécution : python -m tests.test_alp1  (ou pytest)
"""

from __future__ import annotations

import math
import re
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
from alp1 import (calib, dataset, dow, drawdown, fib, figquant, figterm, figures,
                  friction, gex, grading, hmm, horizon, lexicon, mc, measure,
                  microstructure, momentum, orderflow, overfit, paper, pathstats,
                  prereg, quant, report, report2, stress, vprofile)
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
        """À R:R constant, Δp est proportionnel à c/a.

        Élargir le stop d'un facteur k divise donc le lift conditionnel requis
        par ce même facteur k, quel que soit le ratio gain/risque retenu.
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


class TestHorizon(unittest.TestCase):
    """Premier passage sous contrainte de durée."""

    SIGMA = 1.25
    A, B = 3.0, 60.0

    def test_optional_stopping_holds_under_time_cap(self):
        # τ ∧ T est borné : E[X] doit être nul à la précision machine, quelle
        # que soit la géométrie — c'est la Proposition 2 du paper.
        for a, b, t in ((3.0, 60.0, 15.0), (3.0, 90.0, 390.0), (0.3, 90.0, 60.0),
                        (6.0, 12.0, 5.0)):
            with self.subTest(a=a, b=b, t=t):
                o = horizon.outcome(a, b, t, self.SIGMA)
                self.assertAlmostEqual(o.mean_gross, 0.0, places=9)

    def test_probabilities_sum_to_one(self):
        o = horizon.outcome(self.A, self.B, 90.0, self.SIGMA)
        self.assertAlmostEqual(o.p_target + o.p_stop + o.p_open, 1.0, places=12)

    def test_long_horizon_recovers_gamblers_ruin(self):
        p_up, p_down, p_open = horizon.absorption_probabilities(
            self.A, self.B, 1e7, 0.0, self.SIGMA)
        self.assertAlmostEqual(p_up, self.A / (self.A + self.B), places=10)
        self.assertAlmostEqual(p_open, 0.0, places=12)

    def test_long_horizon_with_drift_matches_closed_form(self):
        for mu in (-0.01, -0.002, 0.002, 0.01):
            with self.subTest(mu=mu):
                p_up, _, _ = horizon.absorption_probabilities(
                    self.A, self.B, 1e7, mu, self.SIGMA)
                self.assertAlmostEqual(
                    p_up, prob_target_before_stop(self.A, self.B, mu, self.SIGMA),
                    places=9)

    def test_expected_time_converges_to_ab_over_variance(self):
        for a, b in ((3.0, 60.0), (3.0, 9.0), (0.3, 90.0)):
            with self.subTest(a=a, b=b):
                self.assertAlmostEqual(
                    horizon.expected_exit_time(a, b, 1e7, self.SIGMA),
                    a * b / self.SIGMA**2, places=6)

    def test_time_cap_reduces_target_probability(self):
        short = horizon.outcome(self.A, self.B, 30.0, self.SIGMA)
        long = horizon.outcome(self.A, self.B, 390.0, self.SIGMA)
        self.assertLess(short.p_target, long.p_target)
        self.assertGreater(short.p_open, long.p_open)

    def test_exposure_saturates_with_distant_targets(self):
        # Au-delà d'un certain éloignement, la séance décide de la sortie et
        # l'exposition cesse de croître : c'est le coude de la Figure 4.
        taus = [horizon.expected_exit_time(self.A, r * self.A, 390.0, self.SIGMA)
                for r in (10, 20, 30, 50, 80)]
        self.assertTrue(all(x <= y + 1e-9 for x, y in zip(taus, taus[1:])))
        self.assertLess(taus[-1] - taus[-2], 0.05 * taus[-1])

    def test_hurst_is_pinned_by_two_dispersions(self):
        h = horizon.hurst_from_dispersions(1.25, 60.0, 390.0)
        self.assertAlmostEqual(1.25 * 390.0**h, 60.0, places=9)
        self.assertGreater(h, 0.5)

    def test_scaled_reduces_to_diffusive_case(self):
        ref = horizon.outcome(self.A, self.B, 390.0, self.SIGMA)
        got = horizon.outcome_scaled(self.A, self.B, 390.0, self.SIGMA, 0.5)
        self.assertAlmostEqual(got.p_target, ref.p_target, places=12)
        self.assertAlmostEqual(got.expected_time, ref.expected_time, places=9)

    def test_superdiffusive_scaling_makes_distant_targets_reachable(self):
        h = horizon.hurst_from_dispersions(1.25, 60.0, 390.0)
        diff = horizon.outcome(self.A, 90.0, 390.0, self.SIGMA)
        scaled = horizon.outcome_scaled(self.A, 90.0, 390.0, self.SIGMA, h)
        self.assertGreater(scaled.p_target, 50 * diff.p_target)
        self.assertLess(scaled.expected_time, diff.expected_time)


class TestMasterCriterion(unittest.TestCase):
    """Dérive × exposition − friction : le critère de la Proposition 4."""

    SIGMA = 1.25

    def test_required_drift_matches_friction_over_exposure(self):
        # µ* = c/E[τ] au premier ordre : on compare la racine exacte de
        # l'équation d'espérance à la forme fermée cσ²/(ab).
        for a, b in ((3.0, 60.0), (3.0, 90.0), (1.5, 30.0)):
            with self.subTest(a=a, b=b):
                c = 0.05                      # friction faible : régime local
                exact = required_drift(a, b, self.SIGMA, c)
                closed = c * self.SIGMA**2 / (a * b)
                self.assertLess(abs(exact - closed) / closed, 0.05)

    def test_information_ratio_closed_form(self):
        a, b, c = 3.0, 60.0, 0.33
        tau = a * b / self.SIGMA**2
        self.assertAlmostEqual(c / (self.SIGMA * math.sqrt(tau)),
                               c / math.sqrt(a * b), places=12)

    def test_relative_lift_is_invariant_in_reward_risk(self):
        a, c = 3.0, 0.33
        for rr in (2.0, 5.0, 20.0, 30.0, 100.0):
            with self.subTest(rr=rr):
                geom = TradeGeometry(a, rr * a, c)
                p0 = 1.0 / (rr + 1.0)
                self.assertAlmostEqual(
                    required_conditional_lift(geom) / p0, c / a, places=12)

    def test_displayed_ratio_times_probability_is_bounded(self):
        # Proposition 6 : le produit vaut d/(r+d) et tend vers 1.
        d = 87.0
        for r in (6.0, 3.0, 0.3, 0.05):
            with self.subTest(r=r):
                p = r / (r + d)
                self.assertAlmostEqual(p * (d / r), d / (r + d), places=12)
                self.assertLess(p * (d / r), 1.0)


class TestReportAndPaper(unittest.TestCase):
    """Cohérence des tables, des figures et du document produit."""

    def test_all_tables_are_well_formed(self):
        for key, table in report.all_tables().items():
            with self.subTest(table=key):
                self.assertTrue(table.rows)
                for row in table.rows:
                    self.assertEqual(len(row), len(table.headers))
                    for cell in row:
                        self.assertNotIn("nan", cell.lower())
                        self.assertNotIn("None", cell)

    def test_figures_are_well_formed_svg(self):
        import xml.etree.ElementTree as ET

        for key, svg in figures.render_all().items():
            with self.subTest(figure=key):
                root = ET.fromstring(svg)
                self.assertIn("viewBox", root.attrib)
                self.assertIn("aria-label", root.attrib)
                # Aucune couleur en dur : les marques passent par les jetons CSS.
                self.assertNotIn("#", svg.split(">", 1)[1])

    def test_paper_builds_without_leftover_placeholders(self):
        html = paper.build()
        self.assertNotIn("{{", html)
        self.assertEqual(html.count('<span class="lab">Table '),
                         len(report.TABLES) + len(lexicon.TABLES) + len(quant.TABLES))
        self.assertEqual(html.count('<span class="lab">Figure '),
                         len(figures.ALL_FIGURES) + len(figterm.ALL_FIGURES)
                         + len(figquant.ALL_FIGURES))

    def test_paper_values_are_consistent_with_tables(self):
        v = paper.values()
        # Le lift relatif cité dans le texte est bien c/L.
        self.assertEqual(v["lift_rel"], report.num(100 * report.FRICTION / report.STOP_PTS, 1))
        # Le ratio affiché cité dans le texte est celui de la Table 6.
        table = report.all_tables()["displayed"]
        self.assertIn("1:" + v["displayed_ratio"], [row[2] for row in table.rows])


# --- Les sept couches -------------------------------------------------------


class TestGex(unittest.TestCase):
    """Exposition gamma : formules, niveaux, et chaîne vers la loi d'échelle."""

    def test_gamma_peaks_at_the_money(self):
        tau = gex.years_to_expiry(195.0)
        atm = gex.bs_gamma(6000.0, 6000.0, 0.12, tau)
        for k in (5900.0, 5950.0, 6050.0, 6100.0):
            self.assertLess(gex.bs_gamma(6000.0, k, 0.12, tau), atm)

    def test_gamma_grows_as_inverse_root_of_time(self):
        g_short = gex.bs_gamma(6000.0, 6000.0, 0.12, gex.years_to_expiry(60.0))
        g_long = gex.bs_gamma(6000.0, 6000.0, 0.12, gex.years_to_expiry(240.0))
        self.assertAlmostEqual(g_short / g_long, 2.0, delta=1e-4)

    def test_dealer_sign_is_a_convention_that_flips(self):
        self.assertEqual(gex.dealer_sign(gex.Kind.CALL, True), 1.0)
        self.assertEqual(gex.dealer_sign(gex.Kind.PUT, True), -1.0)
        self.assertEqual(gex.dealer_sign(gex.Kind.CALL, False), -1.0)

    def test_reference_chain_has_a_sign_change_at_the_hvl(self):
        chain = gex.reference_chain()
        lv = gex.levels(chain, 6000.0)
        self.assertIsNotNone(lv.hvl)
        self.assertLess(chain.gex(lv.hvl - 20.0), 0.0)
        self.assertGreater(chain.gex(lv.hvl + 20.0), 0.0)
        self.assertAlmostEqual(chain.gex(lv.hvl), 0.0, delta=1e6)

    def test_levels_are_on_the_expected_side_of_spot(self):
        chain = gex.reference_chain()
        lv = gex.levels(chain, 6000.0)
        for level in lv.call_resistance:
            self.assertGreater(level, 6000.0)
        for level in lv.put_support:
            self.assertLess(level, 6000.0)
        # Le classement porte sur la taille, pas sur la distance.
        conc = chain.potential_notional_by_strike()
        self.assertGreaterEqual(conc[lv.cr1], conc[lv.cr2])
        self.assertGreaterEqual(conc[lv.ps1], conc[lv.ps2])

    def test_the_two_wall_conventions_can_disagree(self):
        chain = gex.reference_chain()
        near = gex.levels(chain, 6000.0, mode="spot")
        far = gex.levels(chain, 6000.0, mode="potential")
        self.assertNotEqual(near.put_support, far.put_support)

    def test_feedback_maps_to_hurst_and_back(self):
        for h in (0.52, 0.58, 0.6489):
            k = gex.feedback_from_hurst(h, 390.0)
            self.assertAlmostEqual(gex.hurst_from_feedback(k, 390.0), h, places=9)

    def test_positive_gamma_damps_and_negative_amplifies(self):
        self.assertEqual(gex.vol_multiplier(0.0), 1.0)
        self.assertLess(gex.vol_multiplier(0.2), 1.0)
        self.assertGreater(gex.vol_multiplier(-0.2), 1.0)
        self.assertLess(gex.autocorrelation_from_feedback(0.2), 0.0)
        self.assertGreater(gex.autocorrelation_from_feedback(-0.2), 0.0)
        self.assertLess(gex.hurst_from_feedback(0.2), 0.5)
        self.assertGreater(gex.hurst_from_feedback(-0.2), 0.5)

    def test_unit_root_threshold_is_enforced(self):
        with self.assertRaises(ValueError):
            gex.autocorrelation_from_feedback(-0.5)

    def test_required_gex_for_calibrated_hurst_is_implausible(self):
        adv = 4.0e11
        req = gex.required_gex_for_hurst(0.6489, adv, horizon_min=390.0)
        # Négatif — il faudrait du gamma court — et d'un ordre de grandeur
        # au-dessus de tout gamma indiciel observable.
        self.assertLess(req, 0.0)
        self.assertGreater(abs(req) / adv, 0.3)

    def test_hedge_flow_is_the_variation_of_delta(self):
        chain = gex.reference_chain()
        flow = gex.hedge_flow_between(chain, 5990.0, 6010.0)
        back = gex.hedge_flow_between(chain, 6010.0, 5990.0)
        self.assertAlmostEqual(flow, -back, places=6)


class TestVolumeProfile(unittest.TestCase):
    """Profil de volume lu comme densité d'occupation."""

    def setUp(self):
        self.prof = vprofile.reference_profile()

    def test_poc_is_the_argmax(self):
        idx = self.prof.volumes.index(max(self.prof.volumes))
        self.assertEqual(self.prof.poc, self.prof.prices[idx])

    def test_value_area_covers_the_target_fraction(self):
        for frac in (0.5, 0.7, 0.9):
            va = self.prof.value_area(frac)
            self.assertGreaterEqual(va.covered, frac)
            self.assertLess(va.low, self.prof.poc)
            self.assertGreater(va.high, self.prof.poc)

    def test_nodes_alternate_and_are_ordered(self):
        hvn, lvn = self.prof.hvn(), self.prof.lvn()
        self.assertEqual(len(hvn), 3)
        self.assertEqual(len(lvn), 2)
        for low in lvn:
            self.assertTrue(any(h < low for h in hvn))
            self.assertTrue(any(h > low for h in hvn))

    def test_local_volatility_inverts_the_density(self):
        sig = self.prof.local_volatility(1.25)
        mean_v = self.prof.total / len(self.prof.volumes)
        for v, s in zip(self.prof.volumes, sig):
            expected = min(1.25 * math.sqrt(mean_v / v), 5.0)
            self.assertAlmostEqual(s, expected, places=9)

    def test_low_volume_means_high_local_volatility(self):
        lvn = self.prof.lvn()[0]
        self.assertGreater(self.prof.sigma_at(lvn, 1.25),
                           self.prof.sigma_at(self.prof.poc, 1.25))

    def test_a_constant_stop_is_not_a_constant_risk(self):
        poc = self.prof.effective_stop_sigma(self.prof.poc, 3.0, 1.25)
        lvn = self.prof.effective_stop_sigma(self.prof.lvn()[-1], 3.0, 1.25)
        self.assertGreater(poc, lvn)
        self.assertGreater(poc / lvn, 1.3)

    def test_traversal_is_faster_across_a_low_volume_node(self):
        step = self.prof.step
        lvn = self.prof.lvn()[-1]
        hvn = self.prof.hvn()[1]
        t_lvn = self.prof.traversal_time(lvn - step, lvn + step, 1.25)
        t_hvn = self.prof.traversal_time(hvn - step, hvn + step, 1.25)
        self.assertLess(t_lvn, t_hvn)

    def test_profile_from_a_path_counts_visits(self):
        path = [100.0, 100.4, 100.8, 100.4, 100.0, 100.4]
        prof = vprofile.from_path(path, 0.4)
        self.assertAlmostEqual(prof.total, len(path))
        self.assertIn(prof.poc, (100.4,))

    def test_composite_sums_matching_grids(self):
        comp = vprofile.composite([self.prof, self.prof])
        self.assertAlmostEqual(comp.total, 2 * self.prof.total)
        self.assertEqual(comp.poc, self.prof.poc)


class TestDow(unittest.TestCase):
    """Théorie de Dow : identités exactes et traduction en dérive."""

    def test_dominant_wick_law(self):
        self.assertAlmostEqual(dow.p_dominant_wick(1.0), 1 / 3, places=12)
        self.assertAlmostEqual(dow.p_dominant_wick(2.0), 0.2, places=12)
        self.assertAlmostEqual(dow.p_dominant_wick(0.0), 1.0, places=12)
        for k in (0.5, 1.0, 2.0, 4.5):
            self.assertAlmostEqual(
                dow.wick_threshold_for_frequency(dow.p_dominant_wick(k)), k, places=9)

    def test_close_beyond_body_partitions_the_unit(self):
        up, down, inside = dow.p_close_beyond_body()
        self.assertAlmostEqual(up, 0.375, places=12)
        self.assertAlmostEqual(down, 0.375, places=12)
        self.assertAlmostEqual(up + down + inside, 1.0, places=12)

    def test_structure_continuation_is_purely_geometric(self):
        self.assertAlmostEqual(dow.p_higher_high_null(4.0, 4.0), 0.5, places=12)
        self.assertAlmostEqual(dow.p_higher_high_null(8.0, 4.0), 1 / 3, places=12)
        # Sans dérive, la formule de premier passage retrouve la forme fermée.
        self.assertAlmostEqual(dow.p_higher_high(8.0, 4.0, 0.0, 1.25),
                               dow.p_higher_high_null(8.0, 4.0), places=9)

    def test_implied_drift_inverts_the_frequency(self):
        for p in (0.40, 0.50, 0.62):
            mu = dow.implied_drift(p, 8.0, 4.0, 1.25)
            self.assertAlmostEqual(dow.p_higher_high(8.0, 4.0, mu, 1.25), p, places=8)
        self.assertAlmostEqual(dow.implied_drift(1 / 3, 8.0, 4.0, 1.25), 0.0, places=8)

    def test_required_daily_bias_composes_the_master_criterion(self):
        bias = dow.required_daily_bias(0.33, 28.9, 390.0)
        self.assertAlmostEqual(bias, 0.33 / 28.9 * 390.0, places=12)
        self.assertAlmostEqual(dow.drift_transfer(bias, 390.0), 0.33 / 28.9, places=12)

    def test_swing_detection_is_causal_and_alternating(self):
        path = [0, 2, 5, 9, 6, 3, 1, 4, 8, 12, 9, 6]
        sw = dow.swings([float(x) for x in path], threshold=3.0)
        self.assertTrue(sw)
        for a, b in zip(sw, sw[1:]):
            self.assertNotEqual(a.is_high, b.is_high)
        pivots = dow.classify(sw)
        self.assertTrue(all(isinstance(p, dow.Pivot) for p in pivots))

    def test_confirmation_reduces_frequency(self):
        joint = dow.confirmation_lift(0.375, 0.8)
        self.assertLess(joint, 0.375)
        self.assertGreater(joint, 0.375 ** 2)


class TestFibonacci(unittest.TestCase):
    """Grille de retracement : loi nulle et arbitrage d'exécution."""

    def test_ratio_provenance_is_arithmetic(self):
        self.assertAlmostEqual(1.0 / fib.PHI, 0.618, places=3)
        self.assertAlmostEqual(1.0 / fib.PHI ** 2, 0.382, places=3)
        self.assertAlmostEqual(math.sqrt(1.0 / fib.PHI), 0.786, places=3)

    def test_retracement_law_is_a_ratio_of_thresholds(self):
        self.assertAlmostEqual(fib.p_retrace_null(0.1, 0.1), 0.5, places=12)
        self.assertAlmostEqual(fib.p_retrace_null(0.618, 0.10),
                               0.10 / 0.718, places=12)
        prev = 1.0
        for ratio, _ in fib.RATIOS:
            p = fib.p_retrace_null(ratio)
            self.assertLess(p, prev)
            prev = p

    def test_drifted_fill_rate_matches_the_null_at_zero_drift(self):
        q = fib.p_retrace(0.618, 0.10, 40.0, 0.0, 1.25)
        self.assertAlmostEqual(q, fib.p_retrace_null(0.618, 0.10), places=8)

    def test_waiting_pays_exactly_when_the_signal_loses(self):
        """Proposition 11, à exposition inchangée : Δ = −(1 − q)·E_marché."""
        tau = 28.9
        for mu_h in (0.0, 0.4, 0.685, 1.5, 3.0):
            mu = mu_h / 60.0
            cmp = fib.compare(40.0, 3.0, 60.0, 0.33, mu, 1.25, tau, tau)
            e_market = mu * tau - 0.33
            self.assertAlmostEqual(cmp.edge, -(1.0 - cmp.fill_rate) * e_market,
                                   places=9)
            self.assertEqual(cmp.edge > 0, e_market < 0)

    def test_critical_drift_equals_mu_star_when_exposure_is_unchanged(self):
        tau = 28.9
        cmp = fib.compare(40.0, 3.0, 60.0, 0.33, 0.0, 1.25, tau, tau)
        self.assertAlmostEqual(cmp.critical_drift, 0.33 / tau, places=9)

    def test_longer_exposure_raises_the_critical_drift(self):
        cmp = fib.compare(40.0, 3.0, 60.0, 0.33, 0.0, 1.25, 28.9, 32.0)
        self.assertGreater(cmp.critical_drift, 0.33 / 28.9)

    def test_breakeven_fill_rate_is_demanding(self):
        q_star = fib.breakeven_fill_rate(20.0, 24.1)
        self.assertGreater(q_star, fib.expected_ote_fill())

    def test_ote_zone_brackets_the_grid(self):
        leg = fib.Leg(5960.0, 6000.0)
        lo, hi = leg.ote()
        self.assertLess(lo, leg.level(fib.OTE_LOW))
        self.assertGreaterEqual(hi, leg.level(fib.OTE_LOW) - 1e-9)


class TestOrderFlow(unittest.TestCase):
    """Liquidité : échelles, persistance, discrimination, impact."""

    def test_capture_grows_with_the_half_life(self):
        prev = 0.0
        for hl in (0.05, 0.5, 5.0, 30.0, 390.0):
            cap = orderflow.captured_drift(1.0, hl, 28.9)
            self.assertGreater(cap, prev)
            self.assertLessEqual(cap, 1.0)
            prev = cap

    def test_required_drift_inverts_the_capture(self):
        for hl in (0.05, 0.5, 30.0):
            need = orderflow.required_instant_drift(0.33, hl, 28.9)
            self.assertAlmostEqual(
                orderflow.captured_drift(need, hl, 28.9) * 28.9, 0.33, places=9)

    def test_book_scales_demand_implausible_drift(self):
        quote = orderflow.required_instant_drift(0.33, 0.05, 28.9)
        structural = orderflow.required_instant_drift(0.33, 390.0, 28.9)
        self.assertGreater(quote / 1.25, 2.0)          # plusieurs σ par minute
        self.assertLess(structural / 1.25, 0.05)
        self.assertGreater(quote / structural, 100.0)

    def test_queue_survival_and_half_life(self):
        self.assertAlmostEqual(orderflow.lpr_expected(0.0, 5.0), 1.0, places=12)
        h = 2.0
        self.assertAlmostEqual(
            orderflow.lpr_expected(h, orderflow.half_life_from_hazard(h)), 0.5,
            places=12)

    def test_auc_saturates_with_depth(self):
        prev = 0.5
        for depth in (1.0, 5.0, 20.0, 200.0):
            auc = orderflow.lpr_auc(depth, 1.0, 4.0, 0.5)
            self.assertGreater(auc, prev)
            self.assertLess(auc, 1.0)
            prev = auc
        # Au-delà d'une dizaine de contrats, le gain devient marginal.
        self.assertLess(orderflow.lpr_auc(1000.0, 1.0, 4.0, 0.5)
                        - orderflow.lpr_auc(20.0, 1.0, 4.0, 0.5), 0.03)

    def test_required_separation_is_out_of_reach(self):
        d_req = orderflow.required_separation_for_auc(0.90)
        d_have = orderflow.lpr_discriminability(200.0, 1.0, 4.0, 0.5)
        self.assertGreater(d_req, d_have)

    def test_impact_is_linear_and_inverse_to_depth(self):
        self.assertAlmostEqual(orderflow.impact_ticks(20.0, 40.0), 0.5, places=12)
        self.assertAlmostEqual(orderflow.impact_ticks(40.0, 40.0), 1.0, places=12)
        self.assertAlmostEqual(orderflow.kyle_lambda(0.25, 50.0), 0.005, places=12)

    def test_friction_rises_when_the_book_thins(self):
        thick = orderflow.effective_friction(ES, 4.0, 5.0, 120.0, 120.0)
        thin = orderflow.effective_friction(ES, 4.0, 5.0, 120.0, 3.0)
        self.assertGreater(thin, thick)
        self.assertGreater(thin / thick, 1.5)

    def test_cvd_divergence_null_follows_sheppard(self):
        self.assertAlmostEqual(orderflow.p_sign_divergence(0.0), 0.5, places=12)
        self.assertAlmostEqual(orderflow.p_sign_divergence(0.8),
                               0.5 - math.asin(0.8) / math.pi, places=12)
        self.assertGreater(orderflow.p_sign_divergence(0.5),
                           orderflow.p_sign_divergence(0.9))

    def test_detecting_a_small_excess_needs_a_large_sample(self):
        n = orderflow.trades_to_detect_excess(0.02, 0.205)
        self.assertGreater(n, 1000.0)
        self.assertEqual(orderflow.trades_to_detect_excess(0.0, 0.205), math.inf)


class TestLayerFiguresAndTables(unittest.TestCase):
    """Les planches et les tables de la seconde partie du document."""

    def test_terminal_figures_are_well_formed_svg(self):
        import xml.etree.ElementTree as ET

        for key, svg in figterm.render_all().items():
            with self.subTest(figure=key):
                root = ET.fromstring(svg)
                self.assertIn("viewBox", root.attrib)
                self.assertIn("aria-label", root.attrib)
                self.assertNotIn("#", svg.split(">", 1)[1])

    def test_deterministic_noise_is_reproducible(self):
        a = [figterm._Noise(7).gauss() for _ in range(3)]
        b = [figterm._Noise(7).gauss() for _ in range(3)]
        self.assertEqual(a, b)

    def test_layer_tables_are_well_formed(self):
        for key, table in lexicon.all_tables().items():
            with self.subTest(table=key):
                self.assertTrue(table.rows)
                for row in table.rows:
                    self.assertEqual(len(row), len(table.headers))
                    for cell in row:
                        # « nan » comme mot isolé, pas comme syllabe de « dominante ».
                        self.assertIsNone(re.search(r"(?<![^\W\d_])nan(?![^\W\d_])",
                                                    cell.lower()))
                        self.assertNotIn("None", cell)
                for col in table.wrapping():
                    self.assertLess(col, len(table.headers))

    def test_lexicon_covers_every_sigil_used_in_the_text(self):
        keys = {row[0] for row in lexicon.table_lexicon().rows}
        for sigil in ("GEX", "0GW", "HVL", "POC", "VAH / VAL", "HVN", "LVN",
                      "VWAP", "OTE", "LPR", "CVD"):
            self.assertIn(sigil, keys)

    def test_layer_values_reach_the_document(self):
        v = paper.values()
        for key in ("gex_req_bn", "daily_bias", "fill_618", "auc_max",
                    "stop_sigma_lvn", "mu0_quote", "cvd_div"):
            self.assertIn(key, v)
            self.assertTrue(v[key])


# ---------------------------------------------------------------------------
# Troisième partie : les instruments de validation
# ---------------------------------------------------------------------------

class TestTradeLaw(unittest.TestCase):
    """La loi d'un trade doit reproduire *exactement* le noyau dont elle sort."""

    def setUp(self):
        self.a = stop_points(6000.0, 0.050)
        self.b = 20.0 * self.a
        self.c = COST_BASE.friction_points(ES)
        self.out = horizon.outcome_scaled(self.a, self.b, 390.0, 1.25, 0.6489)
        self.law = pathstats.law_from_outcome(self.out, self.a, self.b, self.c)

    def test_mean_is_exactly_minus_friction_over_risk(self):
        # Théorème d'invariance : sans dérive, l'espérance vaut −c/L, point.
        self.assertAlmostEqual(self.law.mean, -self.c / self.a, places=12)

    def test_variance_matches_the_kernel(self):
        self.assertAlmostEqual(self.law.sd, self.out.sd_gross / self.a, places=10)

    def test_probabilities_sum_to_one(self):
        self.assertAlmostEqual(sum(self.law.probs), 1.0, places=12)

    def test_tilting_hits_the_requested_mean(self):
        for target in (-0.05, 0.0, 0.11, 0.5, 2.0):
            with self.subTest(target=target):
                self.assertAlmostEqual(self.law.tilted_to_mean(target).mean,
                                       target, places=9)

    def test_tilting_preserves_the_support(self):
        tilted = self.law.tilted_to_mean(0.11)
        self.assertEqual(tilted.values, self.law.values)

    def test_tilting_outside_the_support_is_refused(self):
        with self.assertRaises(ValueError):
            self.law.tilted_to_mean(max(self.law.values) + 1.0)

    def test_sortino_over_sharpe_is_exactly_sigma_over_downside(self):
        # C'est l'équation (27) : le rapport ne dépend que de la loi, pas du signe.
        law = self.law.tilted_to_mean(0.11)
        self.assertAlmostEqual(law.sortino() / law.sharpe_per_trade,
                               law.sd / law.downside_deviation(), places=10)

    def test_downside_deviation_is_bounded_by_the_stop_plus_friction(self):
        worst = abs(min(self.law.values))
        self.assertLessEqual(self.law.downside_deviation(), worst + 1e-12)

    def test_omega_crosses_one_exactly_at_zero_expectancy(self):
        self.assertLess(self.law.omega(), 1.0)                       # E[R] < 0
        self.assertGreater(self.law.tilted_to_mean(0.1).omega(), 1.0)
        self.assertAlmostEqual(self.law.tilted_to_mean(1e-9).omega(), 1.0, places=6)

    def test_kelly_is_zero_without_edge_and_positive_with_one(self):
        self.assertEqual(self.law.kelly_fraction(), 0.0)
        f = self.law.tilted_to_mean(0.11).kelly_fraction()
        self.assertGreater(f, 0.0)

    def test_kelly_maximises_the_growth_rate(self):
        law = self.law.tilted_to_mean(0.11)
        f = law.kelly_fraction()
        best = law.growth_rate(f)
        for delta in (-0.4, -0.1, 0.1, 0.4):
            self.assertLessEqual(law.growth_rate(f * (1.0 + delta)), best + 1e-12)

    def test_moments_of_a_two_point_law_are_elementary(self):
        law = pathstats.TradeLaw((-1.0, 1.0), (0.5, 0.5))
        self.assertAlmostEqual(law.mean, 0.0)
        self.assertAlmostEqual(law.sd, 1.0)
        self.assertAlmostEqual(law.skewness, 0.0)
        self.assertAlmostEqual(law.excess_kurtosis, -2.0)

    def test_lo_adjustment_is_neutral_without_autocorrelation(self):
        for q in (1, 12, 252):
            self.assertAlmostEqual(pathstats.lo_adjustment(0.0, q), math.sqrt(q),
                                   places=9)

    def test_lo_adjustment_penalises_positive_autocorrelation(self):
        # Une autocorrélation positive gonfle le Sharpe annualisé naïf.
        self.assertLess(pathstats.lo_adjustment(0.2, 252), math.sqrt(252))
        self.assertGreater(pathstats.lo_adjustment(-0.2, 252), math.sqrt(252))

    def test_psr_is_one_half_exactly_at_the_benchmark(self):
        self.assertAlmostEqual(pathstats.probabilistic_sharpe(0.05, 500, 0.05),
                               0.5, places=12)

    def test_psr_approaches_the_student_case_for_small_sharpe(self):
        # Le terme de variance vaut 1 + ½ŜR² sous gaussienne : l'écart au test
        # de Student est du second ordre en ŜR, et disparaît à la limite.
        for sr in (0.05, 0.005):
            with self.subTest(sr=sr):
                self.assertAlmostEqual(pathstats.probabilistic_sharpe(sr, 500),
                                       norm_cdf(sr * math.sqrt(499)),
                                       delta=0.6 * sr**2)

    def test_psr_is_monotone_in_the_estimated_sharpe(self):
        vals = [pathstats.probabilistic_sharpe(sr, 500) for sr in (0.0, 0.02, 0.05, 0.1)]
        self.assertEqual(vals, sorted(vals))

    def test_negative_skew_and_fat_tails_reduce_the_psr(self):
        base = pathstats.probabilistic_sharpe(0.05, 500)
        self.assertLess(pathstats.probabilistic_sharpe(0.05, 500, 0.0, -1.5, 6.0),
                        base)

    def test_min_track_record_length_grows_as_sharpe_shrinks(self):
        # Dominée par 1/ŜR², à la correction de second ordre du terme de variance.
        a = pathstats.min_track_record_length(0.10)
        b = pathstats.min_track_record_length(0.05)
        self.assertAlmostEqual(b / a, 4.0, delta=0.05)
        self.assertEqual(pathstats.min_track_record_length(-0.01), math.inf)


class TestDrawdown(unittest.TestCase):
    def test_expected_max_drawdown_null_matches_levy(self):
        self.assertAlmostEqual(drawdown.expected_max_drawdown_null(1.0, 1),
                               math.sqrt(math.pi / 2.0), places=12)

    def test_reflected_max_cdf_integrates_to_the_known_mean(self):
        # E[sup|W|] = ∫(1 − F) = √(π/2) : le quantile et l'espérance sont la
        # même propriété, lue deux fois.
        step, total, x = 1e-3, 0.0, 1e-3
        while x < 12.0:
            total += (1.0 - drawdown.reflected_max_cdf(x)) * step
            x += step
        self.assertAlmostEqual(total, math.sqrt(math.pi / 2.0), places=3)

    def test_reflected_max_cdf_is_a_distribution(self):
        prev = 0.0
        for k in range(1, 120):
            v = drawdown.reflected_max_cdf(k / 20.0)
            self.assertGreaterEqual(v, prev - 1e-12)
            self.assertLessEqual(v, 1.0)
            prev = v

    def test_drawdown_quantiles_are_ordered(self):
        vals = [drawdown.drawdown_quantile_null(1.0, 100, q)
                for q in (0.5, 0.9, 0.95, 0.99)]
        self.assertEqual(vals, sorted(vals))

    def test_arcsine_law(self):
        self.assertAlmostEqual(drawdown.time_under_water_quantile_null(0.5), 0.5,
                               places=12)
        self.assertAlmostEqual(drawdown.prob_time_under_water_exceeds(0.5), 0.5,
                               places=12)
        # Densité minimale au centre : les bords sont les modes.
        self.assertGreater(drawdown.prob_time_under_water_exceeds(0.8), 0.25)

    def test_adjustment_coefficient_solves_its_own_equation(self):
        law = quant.edge_law()
        theta = drawdown.adjustment_coefficient(law)
        self.assertGreater(theta, 0.0)
        mgf = sum(p * math.exp(-theta * v) for v, p in zip(law.values, law.probs))
        self.assertAlmostEqual(mgf, 1.0, places=9)

    def test_no_adjustment_coefficient_without_edge(self):
        self.assertEqual(drawdown.adjustment_coefficient(quant.null_law()), 0.0)
        self.assertEqual(drawdown.risk_of_ruin(quant.null_law(), 100.0), 1.0)

    def test_ruin_depth_inverts_risk_of_ruin(self):
        law = quant.edge_law()
        for p in (0.5, 0.05, 0.01):
            depth = drawdown.ruin_depth_for_probability(law, p)
            self.assertAlmostEqual(drawdown.risk_of_ruin(law, depth), p, places=9)

    def test_drift_never_deepens_the_drawdown(self):
        law = quant.edge_law()
        for n in (10, 100, 504, 5040):
            self.assertLessEqual(drawdown.expected_max_drawdown_drift(law, n),
                                 drawdown.expected_max_drawdown_null(law.sd, n) + 1e-9)

    def test_profile_reads_a_hand_checked_curve(self):
        # Courbe : 0, 1, −2, −1, 3, 2. Sommet 1 avant le creux −2, donc un
        # drawdown de 3 R au troisième point, effacé deux trades plus tard.
        curve = drawdown.equity_curve([1.0, -3.0, 1.0, 4.0, -1.0])
        self.assertEqual(curve, [0.0, 1.0, -2.0, -1.0, 3.0, 2.0])
        prof = drawdown.profile(curve)
        self.assertAlmostEqual(prof.max_drawdown, 3.0)
        self.assertEqual(prof.recovery, 2)
        self.assertEqual(prof.max_duration, 2)      # les deux points sous 1
        self.assertAlmostEqual(prof.time_under_water, 0.5)
        self.assertGreater(prof.ulcer_index, 0.0)


class TestMonteCarlo(unittest.TestCase):
    def test_generator_is_reproducible(self):
        a = [mc.Rng(11).uniform() for _ in range(3)]
        b = [mc.Rng(11).uniform() for _ in range(3)]
        self.assertEqual(a, b)
        self.assertNotEqual(mc.Rng(11).uniform(), mc.Rng(12).uniform())

    def test_uniform_stays_in_the_unit_interval(self):
        r = mc.Rng(3)
        for _ in range(4000):
            u = r.uniform()
            self.assertGreaterEqual(u, 0.0)
            self.assertLess(u, 1.0)

    def test_gaussian_moments(self):
        r = mc.Rng(5)
        xs = [r.gauss() for _ in range(60000)]
        mean = sum(xs) / len(xs)
        var = sum((x - mean) ** 2 for x in xs) / len(xs)
        self.assertAlmostEqual(mean, 0.0, delta=0.02)
        self.assertAlmostEqual(var, 1.0, delta=0.03)

    def test_sampling_reproduces_the_law(self):
        law = quant.edge_law()
        draws = mc.sample(law, 40000, mc.Rng(7))
        mean = sum(draws) / len(draws)
        self.assertAlmostEqual(mean, law.mean, delta=0.12)

    def test_monte_carlo_confirms_the_driftless_drawdown_formula(self):
        # Le contrôle qui ne partage pas les hypothèses de la dérivation :
        # une marche gaussienne pure, contre l'équation (28).
        r = mc.Rng(13)
        n, paths = 400, 1200
        total = 0.0
        for _ in range(paths):
            peak = cur = worst = 0.0
            for _ in range(n):
                cur += r.gauss()
                peak = max(peak, cur)
                worst = max(worst, peak - cur)
            total += worst
        closed = drawdown.expected_max_drawdown_null(1.0, n)
        # Le suivi discret sous-estime le maximum continu de quelques pour cent.
        self.assertLess(total / paths, closed)
        self.assertGreater(total / paths, 0.90 * closed)

    def test_drift_drawdown_formula_tracks_the_simulation(self):
        law = quant.edge_law()
        summaries = mc.simulate(law, 504, 900, mc.Rng(17))
        simulated = sum(s.max_drawdown for s in summaries) / len(summaries)
        closed = drawdown.expected_max_drawdown_drift(law, 504)
        self.assertAlmostEqual(closed / simulated, 1.0, delta=0.15)

    def test_quantiles_are_ordered_and_bracketed(self):
        xs = [float(k) for k in range(101)]
        self.assertAlmostEqual(mc.quantile(xs, 0.0), 0.0)
        self.assertAlmostEqual(mc.quantile(xs, 0.5), 50.0)
        self.assertAlmostEqual(mc.quantile(xs, 1.0), 100.0)

    def test_stationary_bootstrap_preserves_length_and_support(self):
        data = [1.0, -2.0, 3.0, -4.0]
        out = mc.stationary_bootstrap(data, mc.Rng(2), 2.0, n=50)
        self.assertEqual(len(out), 50)
        self.assertTrue(set(out).issubset(set(data)))

    def test_both_bootstraps_agree_on_an_independent_series(self):
        # Contrôle de l'instrument : sans dépendance, les deux dispersions
        # doivent coïncider. C'est ce qui rend leur écart interprétable ailleurs.
        r = mc.Rng(23)
        data = mc.sample(quant.edge_law(), 400, r)

        def spread(fn):
            means = [sum(fn()) / len(data) for _ in range(400)]
            m = sum(means) / len(means)
            return math.sqrt(sum((x - m) ** 2 for x in means) / len(means))

        a = spread(lambda: mc.iid_bootstrap(data, r))
        b = spread(lambda: mc.stationary_bootstrap(data, r, 10.0))
        self.assertAlmostEqual(a / b, 1.0, delta=0.25)

    def test_sign_permutation_is_uninformative_on_a_symmetric_sample(self):
        p = mc.sign_permutation_pvalue([1.0, -1.0, 2.0, -2.0], mc.Rng(29), 600)
        self.assertGreater(p, 0.15)

    def test_block_length_grows_with_autocorrelation(self):
        self.assertEqual(mc.block_length_for_autocorrelation(0.0), 1.0)
        self.assertLess(mc.block_length_for_autocorrelation(0.3),
                        mc.block_length_for_autocorrelation(0.8))


class TestHMM(unittest.TestCase):
    def test_stationary_distribution_is_invariant(self):
        m = hmm.two_state_from_persistence(0.95, 0.90, 0.5, -0.5, 1.0, 1.0)
        pi = m.stationary()
        for j in range(2):
            self.assertAlmostEqual(sum(pi[i] * m.trans[i][j] for i in range(2)),
                                   pi[j], places=10)

    def test_expected_sojourn_is_the_geometric_mean(self):
        m = hmm.two_state_from_persistence(0.95, 0.90, 0.5, -0.5, 1.0, 1.0)
        self.assertAlmostEqual(m.expected_sojourn(0), 20.0, places=9)
        self.assertAlmostEqual(m.expected_sojourn(1), 10.0, places=9)

    def test_free_parameter_count(self):
        m = hmm.two_state_from_persistence(0.9, 0.9, 1.0, -1.0, 1.0, 1.0)
        self.assertEqual(m.n_free_parameters, 7)

    def test_forward_backward_posteriors_are_probabilities(self):
        m = hmm.two_state_from_persistence(0.9, 0.85, 0.6, -0.6, 1.0, 1.2)
        obs, _ = quant.hmm_series("regime")
        _, gamma, xi = hmm.forward_backward(m, list(obs[:200]))
        for row in gamma:
            self.assertAlmostEqual(sum(row), 1.0, places=9)
        for mat in xi:
            self.assertAlmostEqual(sum(sum(r) for r in mat), 1.0, places=9)

    def test_baum_welch_never_decreases_the_likelihood(self):
        obs, _ = quant.hmm_series("regime")
        seq = list(obs[:300])
        start = hmm.log_likelihood(quant.HMM_INIT, seq)
        fitted, end, _ = hmm.baum_welch(seq, quant.HMM_INIT, n_iter=25)
        self.assertGreaterEqual(end, start - 1e-9)

    def test_baum_welch_recovers_a_real_two_regime_structure(self):
        fitted = quant.hmm_fit("regime")[0]
        means = sorted(fitted.means)
        self.assertLess(means[0], 0.0)
        self.assertGreater(means[1], 0.0)

    def test_baum_welch_invents_regimes_on_short_pure_noise(self):
        # Le résultat que la section existe pour établir : sur du bruit court,
        # l'ajustement produit une séparation nette, et seul le BIC la récuse.
        fitted, loglik, _, _, ll1 = quant.hmm_fit("short")
        d = hmm.separability(fitted.means[0], fitted.means[1],
                             0.5 * (fitted.sds[0] + fitted.sds[1]))
        self.assertGreater(d, 1.0)
        self.assertGreater(loglik, ll1)
        n = len(quant.hmm_series("short")[0])
        delta_bic = (hmm.bic(loglik, fitted.n_free_parameters, n)
                     - hmm.bic(ll1, 2, n))
        self.assertGreater(delta_bic, 0.0)

    def test_bic_accepts_the_real_structure_it_rejects_on_noise(self):
        fitted, loglik, _, _, ll1 = quant.hmm_fit("regime")
        n = len(quant.hmm_series("regime")[0])
        self.assertLess(hmm.bic(loglik, fitted.n_free_parameters, n)
                        - hmm.bic(ll1, 2, n), 0.0)

    def test_viterbi_returns_a_full_path_of_valid_states(self):
        fitted = quant.hmm_fit("regime")[0]
        obs, _ = quant.hmm_series("regime")
        path = hmm.viterbi(fitted, list(obs))
        self.assertEqual(len(path), len(obs))
        self.assertTrue(set(path).issubset({0, 1}))

    def test_bayes_error_is_one_half_at_zero_separation(self):
        self.assertAlmostEqual(hmm.bayes_error(0.0), 0.5, places=12)
        self.assertLess(hmm.bayes_error(2.0), 0.20)

    def test_observations_needed_scale_as_one_over_d_prime_squared(self):
        a = hmm.observations_to_separate(0.4)
        b = hmm.observations_to_separate(0.2)
        self.assertAlmostEqual(b / a, 4.0, places=6)


class TestOverfit(unittest.TestCase):
    def test_expected_max_sharpe_grows_with_trials(self):
        vals = [overfit.expected_max_sharpe(k, 1.0) for k in (2, 10, 100, 1000)]
        self.assertEqual(vals, sorted(vals))
        self.assertEqual(overfit.expected_max_sharpe(1, 1.0), 0.0)

    def test_deflated_sharpe_falls_as_trials_rise(self):
        law = quant.edge_law()
        sr, n = law.sharpe_per_trade, 504
        vals = [overfit.deflated_sharpe(sr, n, k, law.skewness, law.excess_kurtosis)
                for k in (1, 10, 100, 1000)]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_minimum_backtest_length_scales_as_one_over_sharpe_squared(self):
        a = overfit.minimum_backtest_length(0.10, 100)
        b = overfit.minimum_backtest_length(0.05, 100)
        self.assertAlmostEqual(b / a, 4.0, places=6)

    def test_multiple_testing_thresholds_are_ordered_by_severity(self):
        # Bonferroni est le plus sévère, BHY le plus permissif au rang 1.
        self.assertLess(overfit.bonferroni_threshold(0.05, 50),
                        overfit.bhy_threshold(0.05, 50, rank=50))
        self.assertEqual(overfit.holm_thresholds(0.05, 50)[0],
                         overfit.bonferroni_threshold(0.05, 50))

    def test_haircut_is_zero_for_a_single_test_and_total_for_many(self):
        self.assertAlmostEqual(overfit.haircut_sharpe(0.10, 504, 1), 0.0, places=9)
        self.assertEqual(overfit.haircut_sharpe(0.10, 504, 100000), 1.0)

    def test_haircut_grows_with_the_number_of_tests(self):
        vals = [overfit.haircut_sharpe(0.10, 5040, k) for k in (1, 10, 100, 1000)]
        self.assertEqual(vals, sorted(vals))

    def test_pbo_is_one_half_on_average_without_edge(self):
        # La symétrie de la construction l'impose : c'est le contrôle de l'outil.
        flat, real = quant.cscv_distribution()
        self.assertAlmostEqual(sum(flat) / len(flat), 0.5, delta=0.08)
        self.assertLess(sum(real) / len(real), 0.20)

    def test_cscv_evaluates_every_symmetric_partition(self):
        res = quant.cscv_null()
        self.assertEqual(res.n_splits, 70)          # C(8, 4) = 70

    def test_cscv_rejects_an_odd_block_count(self):
        with self.assertRaises(ValueError):
            overfit.cscv([[0.0] * 20, [1.0] * 20], n_blocks=7)

    def test_purged_folds_never_leak_across_the_boundary(self):
        folds = overfit.purged_folds(200, 5, horizon=7, embargo_pct=0.02)
        self.assertEqual(len(folds), 5)
        for f in folds:
            self.assertFalse(set(f.train) & set(f.test))
            for i in f.train:
                for j in f.test:
                    self.assertGreaterEqual(abs(i - j), 1)
            lo, hi = min(f.test), max(f.test)
            for i in f.train:
                self.assertFalse(lo - 7 <= i < hi + 1 + 7)

    def test_purging_costs_training_data(self):
        naive = overfit.purged_folds(200, 5, horizon=0, embargo_pct=0.0)
        purged = overfit.purged_folds(200, 5, horizon=7, embargo_pct=0.02)
        self.assertLess(sum(len(f.train) for f in purged),
                        sum(len(f.train) for f in naive))

    def test_walk_forward_never_trains_on_the_future(self):
        for f in overfit.walk_forward_windows(200, 4):
            self.assertLess(max(f.train), min(f.test))

    def test_leakage_saturates_at_one(self):
        self.assertEqual(overfit.leakage_fraction(390, 20, 60), 1.0)
        self.assertAlmostEqual(overfit.leakage_fraction(390, 1, 0), 0.0)

    def test_effective_trials_collapse_under_correlation(self):
        self.assertAlmostEqual(overfit.effective_trials(100, 0.0), 100.0)
        self.assertLess(overfit.effective_trials(100, 0.5), 3.0)


class TestStress(unittest.TestCase):
    def test_gaussian_var_and_es_are_ordered(self):
        self.assertLess(stress.var_gaussian(0.0, 1.0, 0.99),
                        stress.es_gaussian(0.0, 1.0, 0.99))

    def test_exact_var_and_es_coincide_inside_the_stop_atom(self):
        # Sous le pour-cent extrême, toute la masse est dans l'atome du stop :
        # le stop *est* l'expected shortfall, jusqu'au premier saut.
        law = quant.edge_law()
        self.assertAlmostEqual(stress.var_from_law(law, 0.99),
                               stress.es_from_law(law, 0.99), places=9)

    def test_gaussian_var_grossly_overstates_a_lottery_shaped_law(self):
        law = quant.edge_law()
        self.assertGreater(stress.var_gaussian(law.mean, law.sd, 0.99),
                           5.0 * stress.var_from_law(law, 0.99))

    def test_cornish_fisher_is_flagged_invalid_at_this_asymmetry(self):
        law = quant.edge_law()
        self.assertFalse(stress.cornish_fisher_is_valid(law.skewness,
                                                        law.excess_kurtosis))
        self.assertTrue(stress.cornish_fisher_is_valid(0.0, 0.0))

    def test_es_of_a_two_point_law_is_its_worst_outcome(self):
        law = pathstats.TradeLaw((-1.0, 1.0), (0.02, 0.98))
        self.assertAlmostEqual(stress.es_from_law(law, 0.99), 1.0, places=9)

    def test_gpd_recovers_an_exponential_tail(self):
        # Une exponentielle est la GPD de forme ξ = 0 : l'ajustement doit le voir.
        r = mc.Rng(31)
        losses = [-math.log(max(r.uniform(), 1e-12)) for _ in range(8000)]
        fit = stress.fit_gpd(losses, 1.0)
        self.assertAlmostEqual(fit.shape, 0.0, delta=0.12)
        self.assertTrue(fit.has_finite_variance)

    def test_evt_var_exceeds_the_threshold_it_extrapolates_from(self):
        dd = [p.max_drawdown for p in quant.mc_paths("edge")]
        fit = stress.fit_gpd(dd, mc.quantile(dd, 0.90))
        self.assertGreater(stress.var_evt(fit, 0.999), fit.threshold)

    def test_hill_estimator_is_positive_on_a_pareto_tail(self):
        r = mc.Rng(37)
        losses = [max(r.uniform(), 1e-12) ** (-1.0 / 2.0) for _ in range(6000)]
        self.assertAlmostEqual(stress.hill_estimator(losses, 300), 0.5, delta=0.12)

    def test_jump_probability_follows_the_exposure(self):
        p_short = stress.prob_jump_during_trade(quant.JUMP, 10.0, 390.0)
        p_long = stress.prob_jump_during_trade(quant.JUMP, 60.0, 390.0)
        self.assertLess(p_short, p_long)
        self.assertAlmostEqual(stress.prob_jump_during_trade(quant.JUMP, 0.0, 390.0),
                               0.0, places=12)

    def test_a_centred_jump_still_costs_the_trade(self):
        # L'asymétrie est dans la géométrie, pas dans le marché.
        excess = stress.expected_slippage_beyond_stop(quant.JUMP, 3.0)
        self.assertGreater(excess, 0.0)
        law = quant.edge_law()
        adjusted = stress.jump_adjusted_expectancy(law, quant.JUMP, 3.0, 28.9, 390.0)
        self.assertLess(adjusted, law.mean)

    def test_wider_stops_absorb_more_of_the_jump(self):
        wide = stress.expected_slippage_beyond_stop(quant.JUMP, 12.0)
        narrow = stress.expected_slippage_beyond_stop(quant.JUMP, 3.0)
        self.assertLess(wide, narrow)

    def test_scenario_loss_is_the_ratio_of_the_two_distances(self):
        sc = stress.Scenario("test", -2.0, "instantané")
        # 2 % de 6000 = 120 points ; stop de 3 points ⇒ 1 + 117/3 = 40 R.
        self.assertAlmostEqual(stress.scenario_loss_r(sc, 6000.0, 3.0), 40.0, places=9)

    def test_reverse_stress_erases_exactly_one_year(self):
        # L'identité porte sur le *surcoût* du choc au-delà du stop : un trade
        # stoppé aurait perdu son R de toute façon.
        law = quant.edge_law()
        m = stress.reverse_stress_move_pct(law, 504.0, 6000.0, 3.0)
        loss = stress.scenario_loss_r(stress.Scenario("", -m, ""), 6000.0, 3.0)
        self.assertAlmostEqual(loss - 1.0, 504.0 * law.mean, places=6)

    def test_no_reverse_stress_without_an_edge(self):
        self.assertEqual(
            stress.reverse_stress_move_pct(quant.null_law(), 504.0, 6000.0, 3.0),
            math.inf)


class TestQuantCalibration(unittest.TestCase):
    def test_reference_edge_equals_the_friction_ratio(self):
        # µ = 2µ* ⇒ E[net] = c ⇒ E[R] = c/L. Aucun paramètre libre.
        self.assertAlmostEqual(quant.edge_law().mean,
                               quant.FRICTION / quant.STOP_PTS, places=9)

    def test_null_law_carries_the_invariance_theorem(self):
        self.assertAlmostEqual(quant.null_law().mean,
                               -quant.FRICTION / quant.STOP_PTS, places=9)

    def test_exposure_grows_with_the_reward_risk_ratio(self):
        taus = [quant.geometry(rr).expected_time for rr in quant.RR_GRID]
        self.assertEqual(taus, sorted(taus))

    def test_detectability_improves_with_exposure_but_never_enough(self):
        best = min(overfit.minimum_backtest_length(
            quant.edge_law(rr).sharpe_per_trade, quant.N_TRIALS_REF)
            for rr in quant.RR_GRID)
        self.assertGreater(best / quant.TRADES_PER_YEAR, 10.0)

    def test_required_multiple_is_far_above_the_reference(self):
        k = quant.required_multiple(1.0, quant.N_TRIALS_REF)
        self.assertGreater(k, 4.0 * quant.DRIFT_MULTIPLE)

    def test_required_multiple_actually_reaches_the_confidence(self):
        k = quant.required_multiple(1.0, quant.N_TRIALS_REF)
        law = quant.law_at_multiple(k)
        dsr = overfit.deflated_sharpe(law.sharpe_per_trade, int(quant.TRADES_PER_YEAR),
                                      quant.N_TRIALS_REF, law.skewness,
                                      law.excess_kurtosis)
        self.assertAlmostEqual(dsr, 0.95, places=4)

    def test_expected_drawdown_exceeds_the_expected_annual_gain(self):
        law = quant.edge_law()
        n = int(quant.TRADES_PER_YEAR)
        self.assertGreater(drawdown.expected_max_drawdown_drift(law, n), n * law.mean)

    def test_simulations_are_cached_and_reproducible(self):
        self.assertIs(quant.mc_paths("null"), quant.mc_paths("null"))
        self.assertEqual(quant.mc_paths("edge")[0], quant.mc_paths("edge")[0])

    def test_quant_tables_are_well_formed(self):
        for key, table in quant.all_tables().items():
            with self.subTest(table=key):
                self.assertTrue(table.rows)
                for row in table.rows:
                    self.assertEqual(len(row), len(table.headers))
                    for cell in row:
                        self.assertIsNone(re.search(r"(?<![^\W\d_])nan(?![^\W\d_])",
                                                    cell.lower()))
                        self.assertNotIn("None", cell)
                for col in table.wrapping():
                    self.assertLess(col, len(table.headers))

    def test_table_notes_use_html_not_markdown(self):
        # Les notes sont insérées en HTML brut : une paire d'astérisques y
        # resterait visible dans le document.
        for source in (report.all_tables(), lexicon.all_tables(), quant.all_tables()):
            for key, table in source.items():
                with self.subTest(table=key):
                    self.assertNotIn("**", table.note)
                    self.assertNotIn("**", table.caption)

    def test_quant_values_reach_the_document(self):
        v = paper.values()
        for key in ("q_sharpe_an", "q_sortino", "q_sd_dd", "q_mtrl_years",
                    "q_mbtl_years", "q_dsr", "q_pbo_null", "q_k100",
                    "q_reverse", "q_mdd_edge"):
            self.assertIn(key, v)
            self.assertTrue(v[key])

    def test_quant_figures_render_as_self_contained_svg(self):
        for key, svg in figquant.render_all().items():
            with self.subTest(figure=key):
                self.assertTrue(svg.startswith('<svg class="fig"'))
                self.assertTrue(svg.rstrip().endswith("</svg>"))
                self.assertIn("aria-label", svg)
                self.assertNotIn("#", svg)          # aucune couleur en dur
                self.assertNotIn("nan", svg.lower())

    def test_quant_figures_stay_inside_their_viewbox(self):
        for key, svg in figquant.render_all().items():
            with self.subTest(figure=key):
                m = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
                self.assertIsNotNone(m)
                limit = max(int(m.group(1)), int(m.group(2))) + 45
                for raw in re.findall(
                        r'(?:x|y|cx|cy|x1|y1|x2|y2)="(-?\d+\.?\d*)"', svg):
                    self.assertGreater(float(raw), -45)
                    self.assertLess(float(raw), limit)


# --- ALP-2 : géométrie stop-seul ------------------------------------------


class TestMomentumGeometry(unittest.TestCase):
    """Le noyau d'ALP-2 : une barrière, une sortie à l'heure."""

    def setUp(self):
        self.sigma = momentum.sigma_from_session(60.0, 390.0)
        self.stop = momentum.mean_abs_move(self.sigma, 90.0)

    def test_sigma_is_not_free(self):
        # σ₁ reconstruit exactement la dispersion posée : aucun degré de liberté.
        self.assertAlmostEqual(self.sigma * math.sqrt(390.0), 60.0, places=10)

    def test_survival_bounds(self):
        self.assertAlmostEqual(momentum.survival(self.stop, 0.0, self.sigma), 1.0)
        self.assertAlmostEqual(
            momentum.survival(1e9, 300.0, self.sigma), 1.0, places=9)
        self.assertAlmostEqual(momentum.survival(0.0, 300.0, self.sigma), 0.0)

    def test_exposure_limits(self):
        # a → ∞ : la position vit toute la séance ; a → 0 : elle meurt aussitôt.
        self.assertAlmostEqual(
            momentum.expected_exposure(1e7, 300.0, self.sigma), 300.0, places=4)
        self.assertAlmostEqual(
            momentum.expected_exposure(1e-9, 300.0, self.sigma), 0.0, places=6)

    def test_exposure_matches_quadrature(self):
        # La forme fermée contre l'intégrale de la survie, par Simpson.
        n, T = 2000, 300.0
        h = T / n
        acc = 0.0
        for i in range(n + 1):
            s = momentum.survival(self.stop, i * h, self.sigma)
            w = 1.0 if i in (0, n) else (4.0 if i % 2 else 2.0)
            acc += w * s
        self.assertAlmostEqual(
            momentum.expected_exposure(self.stop, T, self.sigma),
            acc * h / 3.0, places=4)

    def test_outcome_identities(self):
        o = momentum.time_exit_outcome(self.stop, 300.0, self.sigma)
        self.assertAlmostEqual(o.mean_gross, 0.0, places=12)
        self.assertAlmostEqual(o.p_stop + o.p_open, 1.0, places=12)
        self.assertAlmostEqual(o.p_stop * self.stop, o.p_open * o.mean_open,
                               places=9)
        self.assertAlmostEqual(
            o.sd_gross, self.sigma * math.sqrt(o.expected_time), places=12)

    def test_sharpe_is_ir_gap(self):
        o = momentum.time_exit_outcome(self.stop, 300.0, self.sigma)
        c = 0.33
        ir = momentum.required_ir(c, self.sigma, o.expected_time)
        self.assertAlmostEqual(
            momentum.sharpe_per_trade(0.0, c, self.sigma, o.expected_time),
            -ir, places=12)


class TestCalibrationBox(unittest.TestCase):
    """Cohérence des entrées et survie des conclusions."""

    def test_reference_matches_report(self):
        # calib et report2 ne peuvent pas diverger sur la calibration.
        self.assertAlmostEqual(calib.REFERENCE.index_level, report2.INDEX_LEVEL)
        self.assertAlmostEqual(calib.REFERENCE.session_dispersion,
                               report2.SESSION_DISPERSION)
        self.assertAlmostEqual(calib.REFERENCE.session_min, report2.SESSION_MIN)
        self.assertAlmostEqual(calib.REFERENCE.entry_min, report2.ENTRY_MIN)
        self.assertAlmostEqual(calib.REFERENCE.friction, report2.FRICTION)
        d = calib.derive(calib.REFERENCE)
        self.assertAlmostEqual(d.sigma_1min, report2.SIGMA_1MIN, places=12)
        self.assertAlmostEqual(d.stop, report2.STOP_PTS, places=12)

    def test_all_identities_hold(self):
        for c in calib.identity_checks():
            self.assertTrue(c.ok, f"identité violée : {c.label} ({c.gap:g})")

    def test_all_plausibility_checks_hold(self):
        for r in calib.plausibility_checks():
            self.assertTrue(r.ok, f"hors fourchette : {r.label} = {r.obtained:g}")

    def test_box_contains_reference(self):
        self.assertTrue(calib.BOX.contains(calib.REFERENCE))

    def test_conclusions_survive_the_box(self):
        for v in calib.verdicts(n=5):
            self.assertTrue(v.holds,
                            f"conclusion renversée : {v.conclusion.claim}")
            self.assertGreater(v.margin, 0.0)

    def test_enclosure_contains_reference_value(self):
        for v in calib.verdicts(n=5):
            e = v.enclosure
            self.assertLessEqual(e.lo, e.reference + 1e-9)
            self.assertGreaterEqual(e.hi, e.reference - 1e-9)

    def test_corner_count(self):
        # Cinq axes libres : trente-deux sommets, la durée de séance étant gelée.
        self.assertEqual(len(calib.BOX.free_axes()), 5)
        self.assertEqual(len(list(calib.BOX.corners())), 32)

    def test_no_breaking_point_inside_the_box(self):
        net = [c for c in calib.CONCLUSIONS if c.key == "net_points"][0]
        for b in calib.breaking_points(net):
            self.assertFalse(b.inside_box,
                             f"rupture atteinte dans la boîte sur {b.axis}")

    def test_breaking_point_is_a_zero_of_the_margin(self):
        import dataclasses

        net = [c for c in calib.CONCLUSIONS if c.key == "net_points"][0]
        worst = calib._worst_inputs(net, calib.BOX)
        x = calib.breaking_point(net, "friction")
        self.assertIsNotNone(x)
        # À la rupture, la friction égale exactement la dérive captée, et le
        # résultat net s'annule : c'est la définition du point de rupture.
        at_break = calib.derive(dataclasses.replace(worst, friction=x))
        self.assertAlmostEqual(at_break.net_points, 0.0, places=6)
        self.assertAlmostEqual(x, at_break.edge_points, places=6)
        # Il faut sortir de la boîte, et d'un facteur supérieur à deux.
        self.assertGreater(x, calib.BOX.friction.hi * 2.0)

    def test_degenerate_axis_is_frozen(self):
        self.assertTrue(calib.BOX.session_min.degenerate)
        for inp in calib.BOX.points(3):
            self.assertEqual(inp.session_min, 390.0)


class TestMicrostructure(unittest.TestCase):
    """Saisonnalité, sauts, hétéroscédasticité."""

    def setUp(self):
        self.sigma = momentum.sigma_from_session(60.0, 390.0)
        self.stop = momentum.mean_abs_move(self.sigma, 90.0)
        self.seas = microstructure.Seasonality()

    def test_seasonality_preserves_total_variance(self):
        # Le profil redistribue le risque, il n'en ajoute pas.
        self.assertAlmostEqual(self.seas.clock(390.0), 390.0, places=8)
        self.assertAlmostEqual(self.seas.clock(0.0), 0.0, places=12)

    def test_clock_is_the_integral_of_the_rate(self):
        n, T = 4000, 390.0
        h = T / n
        acc = 0.0
        for i in range(n + 1):
            w = 1.0 if i in (0, n) else (4.0 if i % 2 else 2.0)
            acc += w * self.seas.rate(i * h)
        self.assertAlmostEqual(acc * h / 3.0, self.seas.clock(T), places=4)

    def test_rate_is_u_shaped(self):
        self.assertGreater(self.seas.rate(0.0), self.seas.rate(195.0))
        self.assertGreater(self.seas.rate(390.0), self.seas.rate(195.0))

    def test_flat_seasonality_reduces_to_diffusion(self):
        flat = microstructure.FLAT
        o = microstructure.seasonal_outcome(self.stop, 90.0, self.sigma, flat)
        base = momentum.time_exit_outcome(self.stop, 300.0, self.sigma)
        self.assertAlmostEqual(o.p_stop, base.p_stop, places=9)
        self.assertAlmostEqual(o.expected_time, base.expected_time, places=3)
        self.assertAlmostEqual(o.expected_variance_time, base.expected_time,
                               places=3)

    def test_closed_form_matches_simulation(self):
        closed, sim, se = microstructure.mc_barrier_check(
            self.stop, 90.0, self.sigma, n_paths=4000)
        self.assertLess(abs(closed - sim), 3.5 * se + 0.01)

    def test_master_criterion_survives_the_full_model(self):
        # Wald sous saisonnalité, sauts et volatilité aléatoire réunis.
        for mu, seed in ((0.0, 11), (0.02, 12)):
            chk = microstructure.mc_wald_check(
                self.stop, 90.0, self.sigma, mu, 0.33,
                mix=microstructure.VolMixture(self.sigma, 0.35),
                n_paths=3000, seed=seed)
            self.assertTrue(chk.passes, f"z = {chk.z_score:+.2f} à µ = {mu}")

    def test_vol_mixture_preserves_variance(self):
        mix = microstructure.VolMixture(3.0, 0.4)
        got = microstructure.expect_over_vol(lambda s: s * s, mix, 400)
        self.assertAlmostEqual(got, 9.0, places=4)

    def test_expect_over_vol_is_exact_on_constants(self):
        mix = microstructure.VolMixture(3.0, 0.4)
        self.assertAlmostEqual(
            microstructure.expect_over_vol(lambda s: 7.0, mix), 7.0, places=12)

    def test_gap_cost_falls_with_stop_width(self):
        wide = microstructure.gap_cost(23.0, 158.0, microstructure.JUMPS)
        tight = microstructure.gap_cost(3.0, 28.9, microstructure.JUMPS)
        self.assertGreater(tight.inflation_pct, 10.0 * wide.inflation_pct)
        self.assertEqual(wide.expectancy_shift, 0.0)

    def test_adequacy_marks_the_invariants(self):
        rows = microstructure.adequacy_rows(self.stop, 90.0, self.sigma, 0.33)
        invariants = [r for r in rows if r.invariant]
        self.assertEqual(len(invariants), 2)
        for r in invariants:
            self.assertEqual(r.worst_deviation_pct, 0.0)

    def test_robustness_box_brackets_the_reference(self):
        for r in microstructure.robustness_box(self.stop, 90.0, self.sigma, 0.33):
            self.assertLess(r.worst_deviation_pct, 25.0)


class TestFrictionLaw(unittest.TestCase):
    """La friction comme loi, et la marge qu'elle laisse."""

    def setUp(self):
        self.sigma = momentum.sigma_from_session(60.0, 390.0)
        self.stop = momentum.mean_abs_move(self.sigma, 90.0)
        self.p_stop = momentum.time_exit_outcome(
            self.stop, 300.0, self.sigma).p_stop
        self.law = friction.friction_law(self.sigma, self.p_stop)
        self.edge = 6.0 / 1e4 * 6000.0

    def test_cdf_is_a_distribution(self):
        self.assertAlmostEqual(self.law.cdf(self.law.deterministic - 1e-9), 0.0,
                               places=9)
        self.assertAlmostEqual(self.law.cdf(50.0), 1.0, places=6)
        prev = -1.0
        for x in [0.3 + 0.1 * i for i in range(30)]:
            v = self.law.cdf(x)
            self.assertGreaterEqual(v + 1e-12, prev)
            prev = v

    def test_quantile_inverts_the_cdf(self):
        for q in (0.1, 0.5, 0.9, 0.99):
            self.assertAlmostEqual(self.law.cdf(self.law.quantile(q)), q,
                                   places=6)

    def test_closed_form_mean_matches_numeric_integration(self):
        # E[c] = ∫ (1 − F) sur le support, la friction étant positive.
        lo = self.law.deterministic
        n, hi = 4000, lo + 30.0
        h = (hi - lo) / n
        acc = 0.0
        for i in range(n + 1):
            w = 1.0 if i in (0, n) else (4.0 if i % 2 else 2.0)
            acc += w * (1.0 - self.law.cdf(lo + i * h))
        self.assertAlmostEqual(lo + acc * h / 3.0, self.law.mean, places=3)

    def test_deduced_slippage_recovers_the_posed_one(self):
        # Deux routes sans paramètre commun : le glissement déduit tombe entre
        # le tick posé en référence et deux ticks.
        ticks = friction.implied_exit_slippage_ticks(self.law)
        self.assertGreater(ticks, 1.0)
        self.assertLess(ticks, 2.5)

    def test_friction_grows_with_size(self):
        small = friction.friction_law(self.sigma, self.p_stop, 1.0)
        large = friction.friction_law(self.sigma, self.p_stop, 50.0)
        self.assertGreater(large.mean, small.mean)
        self.assertGreater(large.quantile(0.99), small.quantile(0.99))

    def test_margin_decreases_with_quantile(self):
        ms = friction.margins(self.law, self.edge, self.stop)
        for a, b in zip(ms, ms[1:]):
            self.assertGreater(a.factor, b.factor)
        self.assertTrue(all(m.survives for m in ms))

    def test_capacity_is_monotone(self):
        sizes = [friction.max_size_for_margin(self.sigma, self.p_stop,
                                              self.edge, 2.0, q)
                 for q in (0.50, 0.90, 0.99)]
        self.assertGreater(sizes[0], sizes[1])
        self.assertGreater(sizes[1], sizes[2])

    def test_expectation_survives_the_venue_box_but_the_tail_does_not(self):
        b = friction.friction_box(self.sigma, self.p_stop, self.edge)
        self.assertTrue(b.survives)
        self.assertGreater(b.mean_margin, 2.0)
        self.assertFalse(b.tail_survives)
        self.assertIn("profondeur", b.worst_corner)


class TestPreregistration(unittest.TestCase):
    """Le protocole scellé."""

    def test_fingerprint_is_deterministic(self):
        self.assertEqual(prereg.PROTOCOL.fingerprint(),
                         prereg.PROTOCOL.fingerprint())
        self.assertEqual(len(prereg.PROTOCOL.fingerprint()), 64)
        self.assertEqual(prereg.SEAL, prereg.PROTOCOL.fingerprint()[:16])

    def test_any_change_changes_the_seal(self):
        import dataclasses

        base = prereg.PROTOCOL.fingerprint()
        for field_name, value in (("alpha", 0.01), ("min_trades", 999),
                                  ("sealed_on", "2026-08-22")):
            other = dataclasses.replace(prereg.PROTOCOL, **{field_name: value})
            self.assertNotEqual(other.fingerprint(), base, field_name)
        trimmed = dataclasses.replace(
            prereg.PROTOCOL, configurations=prereg.CONFIGURATIONS[:2])
        self.assertNotEqual(trimmed.fingerprint(), base)

    def test_budget_is_enforced_by_the_code(self):
        for key in ("C1", "C2", "C3"):
            self.assertEqual(prereg.spend(key).key, key)
        with self.assertRaises(prereg.BudgetExceeded):
            prereg.spend("C4")

    def test_hurdle_falls_with_sample_size(self):
        p = prereg.PROTOCOL
        self.assertGreater(p.hurdle(200), p.hurdle(1000))
        self.assertGreater(p.hurdle(1000), p.hurdle(5000))

    def test_decision_requires_all_three_conditions(self):
        p = prereg.PROTOCOL
        self.assertFalse(prereg.decide(p, 0.090, 400).accepted)      # trop court
        self.assertFalse(prereg.decide(p, 0.040, 1000).accepted)     # sélection
        self.assertTrue(prereg.decide(p, 0.090, 1000).accepted)
        d = prereg.decide(p, 0.090, 1000)
        self.assertTrue(d.beats_selection and d.significant and d.enough_trades)

    def test_degrees_of_freedom_are_enumerated(self):
        dof = prereg.degrees_of_freedom()
        self.assertGreaterEqual(len(dof), 10)
        self.assertTrue(all(len(x) == 2 for x in dof))


class TestDatasetAndMeasurement(unittest.TestCase):
    """La chaîne de mesure, contrôlée sur une série de vérité connue."""

    def test_csv_round_trip(self):
        import tempfile

        sessions = dataset.synthetic_sessions(8, seed=5)
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
            path = fh.name
        dataset.write_csv(sessions, path)
        back = dataset.load_csv(path)
        self.assertEqual(len(back), len(sessions))
        self.assertEqual(sum(s.n_bars for s in back),
                         sum(s.n_bars for s in sessions))
        self.assertAlmostEqual(dataset.session_dispersion(back),
                               dataset.session_dispersion(sessions), places=1)

    def test_audit_accepts_a_complete_history(self):
        a = dataset.audit(dataset.synthetic_sessions(30, seed=6))
        self.assertTrue(a.usable)
        self.assertAlmostEqual(a.completeness, 1.0, places=6)
        self.assertEqual(a.invalid_bars, 0)

    def test_audit_rejects_an_incomplete_history(self):
        sessions = dataset.synthetic_sessions(10, seed=7)
        cut = [dataset.Session(s.day, s.bars[:150]) for s in sessions]
        a = dataset.audit(cut)
        self.assertFalse(a.usable)
        self.assertTrue(a.problems())

    def test_timestamp_parsing_variants(self):
        want = "2026-01-02 09:31"
        for raw in ("2026-01-02T09:31:00Z", "2026-01-02 09:31:00",
                    "2026-01-02 09:31", "2026/01/02 09:31"):
            ts = dataset._parse_timestamp(raw)
            self.assertEqual(ts.strftime("%Y-%m-%d %H:%M"), want)
        # Le format ambigu jour/mois est refusé, pas deviné.
        with self.assertRaises(ValueError):
            dataset._parse_timestamp("01/02/2026 09:31")

    def test_measurement_recovers_minus_friction_under_martingale(self):
        # Sans dérive conditionnelle, le résultat net moyen doit valoir −c.
        m = measure.measure(
            dataset.synthetic_sessions(300, momentum_points_per_min=0.0,
                                       seed=99), "C1")
        se = m.sd_net / math.sqrt(m.n_trades)
        self.assertLess(abs(m.mean_net + m.friction_used), 3.0 * se)

    def test_measurement_recovers_an_injected_conditional_drift(self):
        m = measure.measure(
            dataset.synthetic_sessions(300, momentum_points_per_min=0.03,
                                       seed=99), "C1")
        expected = 0.03 * m.mean_exposure - m.friction_used
        self.assertGreater(m.mean_net, 0.0)
        self.assertLess(abs(m.mean_net - expected), 0.35 * expected)

    def test_unconditional_drift_is_not_captured(self):
        # Une dérive constante n'est presque pas captée par une règle qui prend
        # position dans les deux sens : c'est le contrôle négatif du dispositif.
        m = measure.measure(
            dataset.synthetic_sessions(300, drift_points_per_min=0.03,
                                       seed=99), "C1")
        self.assertLess(m.mean_net, 0.03 * m.mean_exposure / 3.0)

    def test_calibration_window_is_strictly_prior(self):
        sessions = dataset.synthetic_sessions(20, seed=8)
        self.assertIsNone(measure._rolling_sigma(sessions, 13))
        self.assertIsNotNone(measure._rolling_sigma(sessions, 14))

    def test_measurement_refuses_unregistered_configuration(self):
        sessions = dataset.synthetic_sessions(20, seed=9)
        with self.assertRaises(prereg.BudgetExceeded):
            measure.measure(sessions, "C9")

    def test_c2_requires_a_gamma_file(self):
        sessions = dataset.synthetic_sessions(20, seed=10)
        with self.assertRaises(ValueError):
            measure.measure(sessions, "C2")

    def test_protocol_run_reports_every_stage(self):
        run = measure.run_protocol(dataset.synthetic_sessions(120, seed=11))
        self.assertTrue(run.stages)
        self.assertIn("Test 1", measure.format_run(run))
        for s in run.stages:
            self.assertTrue(s.name and s.measured and s.criterion)

    def test_half_hour_split_covers_every_trade(self):
        m = measure.measure(dataset.synthetic_sessions(120, seed=12), "C1")
        splits = measure.by_half_hour(m)
        self.assertEqual(sum(s.n for s in splits), m.n_trades)
        self.assertLessEqual(measure.concentration(splits), 1.0)


class TestGradingAndReport2(unittest.TestCase):
    """La grille, et les tables du document ALP-2."""

    def test_weights_sum_to_one_hundred(self):
        self.assertAlmostEqual(sum(c.weight for c in grading.CRITERIA), 100.0)

    def test_scores_are_on_the_anchored_scale(self):
        for a in grading.ASSESSMENTS.values():
            self.assertEqual(set(a.scores), {c.key for c in grading.CRITERIA})
            self.assertEqual(set(a.evidence), set(a.scores))
            for k, v in a.scores.items():
                self.assertIn(v, range(0, 6))
                self.assertTrue(a.evidence[k].strip())

    def test_family_totals_add_up(self):
        for a in grading.ASSESSMENTS.values():
            got = sum(a.family_total(f)[0] for f in grading.families())
            self.assertAlmostEqual(got, a.total(), places=9)

    def test_alp2_scores_top_marks_where_no_data_is_needed(self):
        # Les seuls critères sous le maximum sont ceux qu'une mesure lèverait.
        below = {k for k, v in grading.ALP2.scores.items() if v < 5}
        self.assertEqual(below, {"b1", "b3"})

    def test_all_tables_render(self):
        tables = report2.all_tables()
        self.assertGreaterEqual(len(tables), 20)
        for key, t in tables.items():
            self.assertTrue(t.caption)
            self.assertTrue(t.rows)
            for r in t.rows:
                self.assertEqual(len(r), len(t.headers), key)
            self.assertTrue(t.to_text())
            self.assertTrue(t.to_html(1))
