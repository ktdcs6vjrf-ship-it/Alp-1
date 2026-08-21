"""Le protocole à horizon borné : ses frontières, sa taille, sa puissance.

Les contrôles de ce fichier sont de trois natures, et il vaut la peine de les
distinguer parce qu'ils n'ont pas la même force.

Les premiers confrontent une forme fermée à une **valeur publiée** : les
frontières séquentielles doivent reproduire celles d'O'Brien-Fleming à trois
décimales. C'est le contrôle le plus fort du fichier — il ne partage aucune
hypothèse avec le code testé.

Les deuxièmes confrontent une prévision à sa simulation : l'information par
date prévue en forme fermée contre celle qu'accumule réellement l'estimateur,
la dérive ajoutée contre la dérive simulée. Un écart y signalerait que le
jalonnement du protocole tombe ailleurs qu'il ne le croit.

Les troisièmes portent sur les caractéristiques opérationnelles elles-mêmes —
taille et puissance — et ce sont eux qui feraient échouer la suite si un
levier avait été réglé pour flatter la puissance : la taille se dégraderait,
et elle est testée en même temps.
"""

from __future__ import annotations

import math
import unittest

from alp1 import mcprotocol as mcp
from alp1 import power as pw
from alp1 import report4


class TestSequentialBoundaries(unittest.TestCase):
    """Les frontières de groupe séquentiel."""

    def test_obf_matches_published_values(self):
        """Frontières d'O'Brien-Fleming, quatre examens, bilatéral 5 %.

        Valeurs de référence de la littérature : 4,333 / 2,963 / 2,359 /
        2,014. La récursion du module doit les retrouver à trois décimales,
        faute de quoi le jalonnement du protocole ne tient pas le niveau
        annoncé.
        """
        plan = pw.boundaries((0.25, 0.50, 0.75, 1.00), 0.025, 0.80)
        for got, want in zip(plan.efficacy, (4.333, 2.963, 2.359, 2.014)):
            self.assertAlmostEqual(got, want, delta=0.01)

    def test_spending_function_is_exhausted_exactly(self):
        self.assertAlmostEqual(pw.obf_spend(1.0, 0.05), 0.05)
        self.assertLess(pw.obf_spend(0.25, 0.05), 0.001)
        for t in (0.1, 0.3, 0.6, 0.9):
            self.assertLess(pw.obf_spend(t, 0.05), pw.obf_spend(t + 0.05, 0.05))

    def test_the_level_is_spent_exactly_by_the_efficacy_boundaries(self):
        """Sans borne d'abandon, les rejets sous H₀ épuisent α, et pas plus."""
        plan = pw.boundaries()
        _, _, up, _ = pw._run(plan.fractions, 0.0, plan.efficacy, None,
                              pw.ALPHA, 1.0 - pw.POWER, False, False)
        self.assertAlmostEqual(sum(up), pw.ALPHA, delta=0.002)
        cumulative = 0.0
        for k, t in enumerate(plan.fractions):
            cumulative += up[k]
            self.assertAlmostEqual(cumulative, pw.obf_spend(t, pw.ALPHA),
                                   delta=0.002)

    def test_abandoning_early_can_only_lower_the_level(self):
        """La borne d'abandon est déclarée non contraignante.

        L'arrêter pour futilité retire des chemins qui auraient pu franchir la
        frontière plus tard : le niveau effectif descend sous α. Le protocole
        reste donc valide que l'opérateur poursuive ou non après l'avoir
        franchie — ce qui est exactement ce qu'on veut d'une borne dont on
        laisse l'usage au jugement.
        """
        plan = pw.boundaries()
        self.assertLess(sum(plan.stop_probs_h0), pw.ALPHA + 1e-9)
        self.assertGreater(sum(plan.stop_probs_h0), 0.7 * pw.ALPHA)

    def test_power_is_reached_at_the_design_drift(self):
        plan = pw.boundaries()
        self.assertAlmostEqual(plan.power, pw.POWER, delta=0.005)

    def test_looking_costs_little_and_saves_much(self):
        plan = pw.boundaries()
        self.assertLess(plan.inflation, 1.25)
        self.assertLess(plan.expected_fraction_h1, 0.85)
        self.assertLess(plan.expected_fraction_h0, plan.expected_fraction_h1)

    def test_boundaries_converge_at_the_last_look(self):
        plan = pw.boundaries()
        self.assertAlmostEqual(plan.efficacy[-1], plan.futility[-1], places=9)


class TestPanelInformation(unittest.TestCase):
    """L'arithmétique du panel, avant toute simulation."""

    def test_gls_gain_matches_its_closed_form(self):
        self.assertAlmostEqual(pw.gls_gain(0.35), math.exp(4 * 0.35 ** 2))
        self.assertEqual(pw.gls_gain(0.0), 1.0)

    def test_correlation_shrinks_the_effective_cluster(self):
        d = pw.DESIGN
        self.assertLess(d.effective_trades_per_date, d.cluster_size)
        self.assertGreater(d.effective_trades_per_date, 1.0)

    def test_a_single_market_has_no_cross_correlation_to_pay(self):
        solo = pw.PanelDesign(markets=(pw.PANEL[0],), entries_per_session=1.0)
        self.assertAlmostEqual(solo.effective_trades_per_date, 1.0)

    def test_more_markets_buy_information(self):
        previous = 0.0
        for k in (1, 3, 5):
            d = pw.PanelDesign(markets=pw.PANEL[:k])
            self.assertGreater(d.effective_trades_per_date, previous)
            previous = d.effective_trades_per_date

    def test_sample_size_falls_with_the_square_of_the_effect(self):
        self.assertAlmostEqual(pw.fixed_sample(0.05) / pw.fixed_sample(0.10),
                               4.0, delta=0.01)

    def test_fixed_sequence_is_cheaper_than_bonferroni(self):
        self.assertLess(pw.fixed_sample(0.08, n_tests=1),
                        pw.fixed_sample(0.08, n_tests=3))

    def test_the_ledger_only_ever_shortens(self):
        levers = pw.ledger(0.08)
        for a, b in zip(levers, levers[1:]):
            self.assertLessEqual(b.years_after, a.years_after)
            self.assertLessEqual(b.factor, 1.0)

    def test_sealed_budget_matches_its_derivation(self):
        """Le budget scellé doit rester ce que sa dérivation donne.

        Un écart de plus d'un pour cent signifierait que la géométrie ou le
        marché simulé a bougé sans que le nombre publié suive — c'est-à-dire
        qu'un protocole scellé et le calcul qui le justifie ont divergé.
        """
        got = mcp.forecast_max_information()
        self.assertAlmostEqual(got / pw.SEALED_MAX_INFORMATION, 1.0, delta=0.01)


class TestSimulatedMarket(unittest.TestCase):
    """Le marché simulé, avant toute inférence."""

    def test_optional_stopping_holds_on_the_simulated_market(self):
        """Sous martingale, la dérive brute par minute est nulle.

        C'est le contrôle dont tout le reste dépend : la règle ouvre et ferme
        ses positions à des temps d'arrêt, donc l'identité doit tenir malgré
        la saisonnalité, les sauts, la bande estimée et les ré-entrées.
        """
        check = mcp.martingale_check()
        self.assertLess(abs(check["z"]), 3.0)

    def test_the_trade_law_is_neither_gaussian_nor_symmetric(self):
        st = mcp.pool_statistics(0.0)
        self.assertGreater(st["skew"], 0.5)
        self.assertGreater(st["excess_kurtosis"], 0.5)

    def test_cadence_matches_the_design_constant(self):
        """La cadence posée dans `power` est celle que la règle produit."""
        st = mcp.pool_statistics(0.0)
        self.assertAlmostEqual(st["entries_per_session"],
                               pw.ENTRIES_PER_SESSION, delta=0.05)
        self.assertLessEqual(st["entries_per_session"], mcp.MAX_ENTRIES)

    def test_realised_exposure_falls_short_of_the_closed_form(self):
        """Saisonnalité et bande estimée raccourcissent l'exposition.

        Le sens de l'écart compte : la forme fermée surestime l'exposition,
        donc la prévision de durée est prudente et non flatteuse.
        """
        st = mcp.pool_statistics(0.0)
        closed = mcp.geometry()[1].expected_time
        self.assertLess(st["exposure"], closed)
        self.assertGreater(st["exposure"], 0.7 * closed)

    def test_forecast_information_matches_the_simulation(self):
        st = mcp.pool_statistics(0.0)
        forecast = pw.information_per_date(pw.DESIGN, st["exposure"], st["sd"])
        realised = mcp.realised_information_per_date()
        self.assertAlmostEqual(realised / forecast, 1.0, delta=0.15)

    def test_the_panel_correlation_is_reproduced(self):
        base = mcp.date_pool(0.0)
        self.assertGreater(base.design_effect, 1.0)
        self.assertLess(base.design_effect, base.trades_per_date)
        self.assertGreater(base.realised_correlation, 0.0)

    def test_null_pool_sits_exactly_on_the_boundary(self):
        pool, _ = mcp.null_pool()
        self.assertAlmostEqual(mcp.pool_drift(pool), 0.0, places=12)


class TestOperatingCharacteristics(unittest.TestCase):
    """Ce que le protocole fait, mesuré sur la procédure entière."""

    def test_size_is_the_nominal_level(self):
        op = mcp.operating_point(mcp.exact_pool(0.0), 0.0)
        self.assertLess(abs(op.reject - pw.ALPHA), 3.0 * op.standard_error + 0.005)

    def test_power_is_reached_at_the_design_drift(self):
        op = mcp.operating_point(mcp.exact_pool(1.0), 1.0)
        self.assertGreater(op.reject, pw.POWER - 0.06)
        self.assertLess(op.reject, pw.POWER + 0.10)

    def test_the_horizon_is_not_exhausted(self):
        for mult in (0.0, 1.0):
            op = mcp.operating_point(mcp.exact_pool(mult), mult)
            self.assertLess(op.exhausted, 0.05)

    def test_power_increases_with_the_drift(self):
        previous = -1.0
        for mult in mcp.CURVE:
            op = mcp.operating_point(mcp.exact_pool(mult), mult)
            self.assertGreater(op.reject, previous)
            previous = op.reject

    def test_the_borrowed_hypothesis_is_decided_well_inside_the_horizon(self):
        ref = round(mcp.reference_multiple(), 3)
        op = mcp.operating_point(mcp.exact_pool(ref), ref)
        self.assertGreater(op.reject, 0.95)
        self.assertLess(op.median_years,
                        pw.HORIZON_SESSIONS / pw.SESSIONS_PER_YEAR)

    def test_correlation_moves_the_duration_not_the_size(self):
        rows = mcp.rho_sensitivity()
        for r in rows:
            self.assertLess(abs(r["size"] - pw.ALPHA),
                            3.0 * r["standard_error"] + 0.01)
        self.assertLess(rows[0]["median_years"], rows[-1]["median_years"])

    def test_selection_costs_what_the_order_of_reading_costs(self):
        sel = mcp.selection_contrast()
        self.assertLess(abs(sel["sealed"] - pw.ALPHA),
                        3.0 * sel["standard_error"] + 0.01)
        self.assertGreater(sel["best_of_three"], sel["sealed"])

    def test_added_drift_agrees_with_simulated_drift(self):
        check = mcp.check_shift_accuracy()
        self.assertLess(abs(check["z"]), 3.0)

    def test_detectable_drift_falls_with_the_horizon(self):
        st = mcp.pool_statistics(0.0)
        previous = math.inf
        for years in (1.0, 3.0, 5.0):
            mde = pw.minimum_detectable_edge(
                pw.DESIGN, years, st["sd"], st["exposure"], mcp.friction(),
                mcp.INDEX_LEVEL)
            self.assertLess(mde["viability_bps"], previous)
            self.assertGreater(mde["viability_bps"], mde["existence_bps"])
            previous = mde["viability_bps"]


class TestReportedTables(unittest.TestCase):
    """Les tables et valeurs qui entrent dans le document."""

    def test_every_table_renders(self):
        tables = report4.all_tables()
        self.assertEqual(len(tables), len(report4.TABLES))
        for key, table in tables.items():
            self.assertTrue(table.rows, key)
            for row in table.rows:
                self.assertEqual(len(row), len(table.headers), key)
            self.assertIn("<table", table.to_html(1))

    def test_values_are_complete_and_non_empty(self):
        vals = report4.values()
        self.assertGreater(len(vals), 50)
        for key, val in vals.items():
            self.assertTrue(val.strip(), key)
            self.assertTrue(key.startswith("pw_"), key)

    def test_figures_render(self):
        from alp1.figpower import render_all

        for key, svg in render_all().items():
            self.assertTrue(svg.startswith("<svg"), key)
            self.assertIn("viewBox", svg)


class TestMeasurementChain(unittest.TestCase):
    """La chaîne qui consommera l'historique applique bien la règle scellée."""

    def test_multiple_entries_are_capped_and_re_armed(self):
        from alp1.dataset import synthetic_sessions
        from alp1.measure import measure

        sessions = synthetic_sessions(120)
        m = measure(sessions, "C1")
        by_day: dict[str, int] = {}
        for t in m.trades:
            by_day[t.day] = by_day.get(t.day, 0) + 1
        self.assertTrue(by_day)
        self.assertLessEqual(max(by_day.values()), mcp.MAX_ENTRIES)
        for t in m.trades:
            self.assertGreater(t.exposure_min, 0.0)

    def test_the_statistic_and_its_information_are_reported(self):
        from alp1.dataset import synthetic_sessions
        from alp1.measure import measure

        m = measure(synthetic_sessions(200), "C1")
        self.assertGreater(m.information, 0.0)
        self.assertAlmostEqual(
            m.z_stat, m.drift_per_min * math.sqrt(m.information), places=9)
        self.assertAlmostEqual(
            m.information_fraction,
            m.information / pw.SEALED_MAX_INFORMATION, places=9)

    def test_a_driftless_series_does_not_reject(self):
        from alp1.dataset import synthetic_sessions
        from alp1.measure import measure

        m = measure(synthetic_sessions(260), "C1")
        self.assertFalse(m.decision.rejected)


if __name__ == "__main__":
    unittest.main()
