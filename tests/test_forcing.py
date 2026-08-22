"""Tests du risque réel : géométrie serrée, spread, forçage, capital.

Trois propriétés portent l'essentiel de la partie et sont testées comme
telles, parce qu'un arrondi les rendrait fausses sans les rendre visibles.
Le brut d'une séquence forcée vaut **exactement** zéro sous la loi nulle, à
tout ratio. La probabilité de premier passage ne dépend **pas** de l'exposant
d'échelle. Et la fraction de Kelly vaut **exactement** zéro sans dérive.

Les autres tests vérifient ce qu'on demande à une borne : qu'elle s'inverse
sans dériver, qu'elle refuse ce qu'elle doit refuser, et qu'elle reste
cohérente avec les fonctions du noyau dont elle se réclame.
"""

from __future__ import annotations

import math
import unittest

from alp1 import figrisk, forcing as F, report8
from alp1.barriers import prob_touch_single_barrier
from alp1.costs import COST_BASE, ES, MES, MNQ, NQ, stop_points
from alp1.report import STOP_PCT, STOP_PCT_BOX, Table


class TestGeometrie(unittest.TestCase):
    def test_la_largeur_declaree_est_bien_celle_du_document(self):
        self.assertIn(STOP_PCT, STOP_PCT_BOX)
        self.assertEqual(STOP_PCT_BOX, (0.005, 0.010))

    def test_le_stop_en_ticks_est_la_conversion_du_pourcentage(self):
        for pct in STOP_PCT_BOX:
            attendu = stop_points(6000.0, pct) / ES.tick_size
            self.assertAlmostEqual(F.stop_ticks(ES, 6000.0, pct), attendu,
                                   places=12)

    def test_le_stop_de_l_operateur_tient_dans_trois_ticks(self):
        for pct in STOP_PCT_BOX:
            self.assertLess(F.stop_ticks(ES, 6000.0, pct), 3.0)

    def test_les_contrats_micro_franchissent_le_mur(self):
        """Sur les micros, l'aller-retour coûte plus que le risque nominal."""
        for contrat, niveau in ((MES, 6000.0), (MNQ, 22000.0)):
            with self.subTest(contrat=contrat.symbol):
                self.assertGreater(
                    F.friction_over_stop(contrat, COST_BASE, niveau, STOP_PCT),
                    1.0)

    def test_le_nasdaq_est_le_moins_defavorable(self):
        cl = {c.symbol: F.friction_over_stop(c, COST_BASE, lvl, STOP_PCT)
              for c, lvl in ((ES, 6000.0), (NQ, 22000.0),
                             (MES, 6000.0), (MNQ, 22000.0))}
        self.assertEqual(min(cl, key=cl.get), "NQ")

    def test_un_pas_de_cotation_nul_est_refuse(self):
        from dataclasses import replace
        with self.assertRaises(ValueError):
            F.stop_ticks(replace(ES, tick_size=0.0), 6000.0, 0.01)


class TestLevier(unittest.TestCase):
    def test_le_levier_est_le_quotient_des_deux_choix(self):
        self.assertAlmostEqual(F.leverage(0.02, 0.010), 200.0, places=9)
        self.assertAlmostEqual(F.leverage(0.02, 0.005), 400.0, places=9)

    def test_l_ecart_emporte_le_levier_fois_l_ecart(self):
        self.assertAlmostEqual(F.gap_wipeout(0.02, 0.010, 0.5), 1.0, places=9)

    def test_un_stop_nul_est_refuse(self):
        with self.assertRaises(ValueError):
            F.leverage(0.02, 0.0)


class TestSpread(unittest.TestCase):
    def test_le_stop_utile_retranche_le_spread_entier(self):
        self.assertAlmostEqual(F.effective_stop(0.60, 0.25), 0.35, places=12)

    def test_un_stop_sous_le_spread_est_touche_sans_mouvement(self):
        self.assertLessEqual(F.effective_stop(0.20, 0.25), 0.0)
        self.assertEqual(F.noise_stop_probability(0.20, 0.25, 1.25), 1.0)

    def test_la_probabilite_de_bruit_est_celle_du_premier_passage(self):
        """Le module ne recalcule pas la loi : il appelle celle du noyau."""
        attendu = prob_touch_single_barrier(0.35, 1.25, 1.0)
        self.assertAlmostEqual(
            F.noise_stop_probability(0.60, 0.25, 1.25, 1.0), attendu, places=12)

    def test_la_part_du_spread_decroit_avec_la_largeur(self):
        parts = [F.spread_share(stop_points(6000.0, p), 0.25)
                 for p in (0.005, 0.010, 0.050)]
        self.assertEqual(parts, sorted(parts, reverse=True))
        self.assertLessEqual(parts[0], 1.0)

    def test_le_bruit_sort_plus_de_trois_fois_sur_quatre_a_la_largeur_declaree(self):
        p = F.noise_stop_probability(stop_points(6000.0, STOP_PCT), 0.25, 1.25)
        self.assertGreater(p, 0.75)


class TestForcage(unittest.TestCase):
    def test_le_brut_est_exactement_nul_sous_la_loi_nulle(self):
        """Le théorème, et il ne souffre pas d'exception."""
        for rr in (1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 100.0):
            with self.subTest(ratio=rr):
                f = F.force_until_success(rr, 0.55)
                self.assertAlmostEqual(f.gross_r, 0.0, places=9)

    def test_le_net_vaut_R_plus_un_fois_la_friction(self):
        for rr in (5.0, 20.0, 30.0):
            for cl in (0.11, 0.55, 1.10):
                with self.subTest(ratio=rr, cl=cl):
                    f = F.force_until_success(rr, cl)
                    self.assertAlmostEqual(f.net_r, -(rr + 1.0) * cl, places=9)
                    self.assertAlmostEqual(f.cost_multiple, rr + 1.0, places=9)

    def test_le_taux_martingale_et_les_tentatives_sont_reciproques(self):
        for rr in (5.0, 20.0):
            p = F.martingale_hit_rate(rr)
            self.assertAlmostEqual(F.expected_attempts(p), rr + 1.0, places=9)

    def test_un_taux_de_reussite_impose_l_emporte_sur_la_loi_nulle(self):
        f = F.force_until_success(20.0, 0.55, hit_rate=0.5)
        self.assertAlmostEqual(f.attempts, 2.0, places=12)
        self.assertGreater(f.gross_r, 0.0)

    def test_le_point_mort_coute_la_friction_relative(self):
        for cl in (0.11, 0.55, 1.10):
            self.assertAlmostEqual(F.breakeven_exit_r(cl), -cl, places=12)

    def test_le_point_mort_serre_coute_plus_qu_un_stop_large(self):
        """À 0,005 %, sortir au point mort coûte le stop entier d'avant."""
        self.assertLess(F.breakeven_exit_r(1.10), -1.0 - 0.11 + 0.11)
        self.assertLessEqual(F.breakeven_exit_r(1.10), -(1.0 + 0.11) + 0.01)


class TestSeries(unittest.TestCase):
    def test_la_loi_des_series_est_geometrique(self):
        for p in (0.05, 0.25, 0.5):
            for k in (0, 1, 5, 20):
                self.assertAlmostEqual(F.streak_probability(p, k),
                                       (1 - p) ** k, places=12)

    def test_la_longueur_et_la_probabilite_sont_reciproques(self):
        for p in (0.05, 0.3):
            for q in (0.1, 0.5, 0.9):
                k = F.streak_for_probability(p, q)
                self.assertAlmostEqual(F.streak_probability(p, k), q, places=9)

    def test_six_echecs_a_un_pour_vingt_sont_la_majorite(self):
        p = F.martingale_hit_rate(20.0)
        self.assertGreater(F.streak_probability(p, 6), 0.5)

    def test_la_plus_longue_serie_croit_avec_le_nombre_de_tentatives(self):
        p = F.martingale_hit_rate(20.0)
        v = [F.expected_longest_streak(p, n) for n in (50, 200, 1000)]
        self.assertEqual(v, sorted(v))

    def test_le_drawdown_compose_au_lieu_de_sommer(self):
        self.assertLess(F.drawdown_after(0.02, 10), 0.20)
        self.assertAlmostEqual(F.drawdown_after(0.02, 1), 0.02, places=12)

    def test_pertes_et_drawdown_sont_reciproques(self):
        for f in (0.005, 0.02):
            for niveau in (0.2, 0.5, 0.8):
                k = F.losses_to_drawdown(f, niveau)
                self.assertAlmostEqual(F.drawdown_after(f, k), niveau, places=9)

    def test_une_fraction_hors_bornes_est_refusee(self):
        with self.assertRaises(ValueError):
            F.drawdown_after(1.5, 3)


class TestDimensionnement(unittest.TestCase):
    def test_kelly_est_exactement_nul_sous_la_loi_nulle(self):
        for rr in (1.0, 5.0, 20.0, 50.0):
            p = F.martingale_hit_rate(rr)
            self.assertAlmostEqual(F.kelly_fraction(p, rr), 0.0, places=12)

    def test_le_sur_engagement_est_infini_sans_derive(self):
        p = F.martingale_hit_rate(20.0)
        self.assertEqual(F.overbet(0.02, p, 20.0), math.inf)

    def test_kelly_est_positif_des_qu_un_avantage_existe(self):
        p = F.martingale_hit_rate(20.0) * 1.5
        self.assertGreater(F.kelly_fraction(p, 20.0), 0.0)
        self.assertGreater(F.overbet(0.02, p, 20.0), 0.0)

    def test_la_ruine_croit_avec_la_fraction_engagee(self):
        p = F.martingale_hit_rate(20.0)
        v = [F.risk_of_ruin(p, 20.0, 0.55, f, 60, paths=400) for f in (0.005, 0.02)]
        self.assertLessEqual(v[0], v[1])

    def test_la_ruine_est_reproductible(self):
        p = F.martingale_hit_rate(20.0)
        a = F.risk_of_ruin(p, 20.0, 0.55, 0.02, 50, paths=300)
        b = F.risk_of_ruin(p, 20.0, 0.55, 0.02, 50, paths=300)
        self.assertEqual(a, b)


class TestRegime(unittest.TestCase):
    def test_l_exposant_ne_deplace_pas_le_premier_passage(self):
        """La proposition : un changement d'échelle est un changement de temps."""
        d = F.persistence_cannot_help(20.0, 0.55, 1.25 / 0.6)
        valeurs = list(d["atteint"].values())
        for v in valeurs:
            self.assertAlmostEqual(v, d["plafond"], places=6)
        self.assertGreater(d["cible"], d["plafond"])

    def test_le_verdict_lit_la_persistance_avec_la_tolerance_du_biais(self):
        self.assertFalse(F.regime_verdict(0.5014).persistent)
        self.assertFalse(F.regime_verdict(0.505).persistent)
        self.assertTrue(F.regime_verdict(0.60).persistent)
        self.assertIn("moyenne", F.regime_verdict(0.40).reading)

    def test_le_sharpe_requis_monte_quand_le_stop_se_resserre(self):
        from alp1.horizon import outcome_scaled
        from alp1.report import HURST, SESSION_MIN, SIGMA_1MIN

        def exig(pct):
            L = stop_points(6000.0, pct)
            e = outcome_scaled(L, 20.0 * L, SESSION_MIN, SIGMA_1MIN, HURST)
            return F.required_sharpe_annual(COST_BASE.friction_points(ES),
                                            e.expected_time, SIGMA_1MIN)

        v = [exig(p) for p in (0.050, 0.010, 0.005)]
        self.assertEqual(v, sorted(v))
        self.assertGreater(v[1] / v[0], 10.0)

    def test_une_exposition_nulle_est_refusee(self):
        with self.assertRaises(ValueError):
            F.required_sharpe_annual(0.33, 0.0, 1.25)


class TestDiagnostic(unittest.TestCase):
    def test_le_diagnostic_inverse_la_plus_longue_serie(self):
        for n in (100, 200, 500):
            for k in (4, 6, 10):
                p = F.implied_hit_rate(k, n)
                self.assertGreater(p, 0.0)
                self.assertAlmostEqual(F.expected_longest_streak(p, n),
                                       float(k), places=4)

    def test_une_serie_courte_implique_un_ratio_bas(self):
        rr = [F.implied_reward_risk(F.implied_hit_rate(k, 200))
              for k in (4, 8, 16)]
        self.assertEqual(rr, sorted(rr))
        self.assertLess(rr[0], 1.0)

    def test_une_serie_inatteignable_rend_zero(self):
        self.assertEqual(F.implied_hit_rate(40, 50), 0.0)

    def test_taux_et_ratio_sont_le_meme_parametre(self):
        for rr in (0.5, 1.0, 20.0):
            p = F.martingale_hit_rate(rr)
            self.assertAlmostEqual(F.implied_reward_risk(p), rr, places=9)

    def test_un_echantillon_trop_court_est_refuse(self):
        with self.assertRaises(ValueError):
            F.implied_hit_rate(3, 1)


class TestTablesEtFigures(unittest.TestCase):
    def setUp(self):
        self.tables = report8.all_tables()

    def test_chaque_table_a_des_lignes_de_meme_largeur(self):
        for cle, t in self.tables.items():
            with self.subTest(table=cle):
                self.assertIsInstance(t, Table)
                self.assertTrue(t.rows)
                for r in t.rows:
                    self.assertEqual(len(r), len(t.headers))

    def test_chaque_table_porte_une_lecture(self):
        for cle, t in self.tables.items():
            with self.subTest(table=cle):
                self.assertTrue(t.note.strip())

    def test_le_glossaire_definit_les_termes_du_document(self):
        termes = {t for t, _ in report8.GLOSSARY}
        for attendu in ("Tick", "Spread", "Friction (c)", "Forçage",
                        "Ratio de Sharpe", "Levier", "Loi nulle"):
            self.assertIn(attendu, termes)

    def test_chaque_entree_du_glossaire_est_unique_et_expliquee(self):
        termes = [t for t, _ in report8.GLOSSARY]
        self.assertEqual(len(set(termes)), len(termes))
        for terme, definition in report8.GLOSSARY:
            with self.subTest(terme=terme):
                # Une définition qui tient en trois mots n'explique rien, et
                # une qui commence par le terme lui-même est circulaire.
                self.assertGreater(len(definition.split()), 8)
                self.assertFalse(
                    definition.lower().startswith(terme.split()[0].lower()))

    def test_le_compte_du_glossaire_est_celui_que_le_document_annonce(self):
        self.assertEqual(report8.values()["frc_glossaire_n"],
                         str(len(report8.GLOSSARY)))

    def test_les_valeurs_sont_toutes_des_chaines_francaises(self):
        for cle, v in report8.values().items():
            with self.subTest(valeur=cle):
                self.assertIsInstance(v, str)
                self.assertNotIn(".", v.replace(" ", ""))

    def test_les_six_planches_sont_produites(self):
        figs = figrisk.render_all()
        self.assertEqual(len(figs), 6)
        for cle, svg in figs.items():
            with self.subTest(figure=cle):
                self.assertTrue(svg.startswith("<svg class=\"fig\""))
                self.assertIn("aria-label", svg)
                self.assertNotIn("#", svg.split("aria-label")[0])

    def test_aucune_planche_n_ecrit_de_couleur_en_dur(self):
        for cle, svg in figrisk.render_all().items():
            with self.subTest(figure=cle):
                self.assertNotIn("fill=\"#", svg)
                self.assertNotIn("stroke=\"#", svg)


if __name__ == "__main__":
    unittest.main()
