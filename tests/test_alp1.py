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
from alp1 import dow, fib, figterm, figures, gex, horizon, lexicon, orderflow, paper, report, vprofile
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
                         len(report.TABLES) + len(lexicon.TABLES))
        self.assertEqual(html.count('<span class="lab">Figure '),
                         len(figures.ALL_FIGURES) + len(figterm.ALL_FIGURES))

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
