"""Tests de la discipline chiffrée en preuve.

Une dérogation est une configuration explorée de plus ; la famille double à
chaque fois, et le seuil de sélection suit. Ces tests vérifient l'algèbre, le
point de rupture, et le fait qui décide : la croissance est exponentielle, donc
la borne se franchit d'un coup plutôt que progressivement.
"""

from __future__ import annotations

import math
import unittest

from alp1.costs import deflated_threshold_sharpe
from alp1.discipline import (
    SEALED_BUDGET,
    breaking_deviations,
    breaking_rate,
    deviation_cost,
    effective_trials,
    grid,
)

N = 7012
SR = 0.0332


class TestConfigurations(unittest.TestCase):
    def test_sans_derogation_le_budget_est_celui_du_sceau(self):
        self.assertAlmostEqual(effective_trials(0.0), SEALED_BUDGET, places=12)

    def test_chaque_derogation_double_la_famille(self):
        for k in (0, 1, 5, 10):
            with self.subTest(k=k):
                self.assertAlmostEqual(effective_trials(k + 1),
                                       2.0 * effective_trials(k), places=9)

    def test_dix_derogations_depassent_le_millier(self):
        """Le nombre que la section cite."""
        self.assertGreater(effective_trials(10), 1000.0)

    def test_un_compte_negatif_est_refuse(self):
        with self.assertRaises(ValueError):
            effective_trials(-1.0)


class TestSeuil(unittest.TestCase):
    def test_sans_derogation_le_seuil_est_celui_du_sceau(self):
        d = deviation_cost(0.0, N)
        self.assertAlmostEqual(d.threshold, d.sealed_threshold, places=12)
        self.assertAlmostEqual(d.inflation, 1.0, places=12)

    def test_le_seuil_croit_avec_le_taux(self):
        seuils = [d.threshold for d in grid(SR, N)]
        self.assertEqual(seuils, sorted(seuils))

    def test_l_inflation_est_le_rapport_des_seuils(self):
        for d in grid(SR, N):
            with self.subTest(taux=d.rate):
                self.assertAlmostEqual(d.inflation,
                                       d.threshold / d.sealed_threshold,
                                       places=9)

    def test_le_seuil_reproduit_la_formule_deflatee(self):
        d = deviation_cost(0.001, N)
        self.assertAlmostEqual(
            d.threshold,
            deflated_threshold_sharpe(d.effective_trials, N), places=12)

    def test_un_taux_hors_bornes_est_refuse(self):
        for mauvais in (-0.1, 1.5):
            with self.subTest(taux=mauvais):
                with self.assertRaises(ValueError):
                    deviation_cost(mauvais, N)


class TestRupture(unittest.TestCase):
    def test_la_rupture_amene_le_seuil_au_sharpe(self):
        k = breaking_deviations(SR, N)
        seuil = deflated_threshold_sharpe(SEALED_BUDGET * 2.0 ** k, N)
        self.assertAlmostEqual(seuil, SR, places=6)

    def test_la_rupture_est_atteinte_en_peu_de_derogations(self):
        """Le fait qui donne son intérêt à la section."""
        self.assertLess(breaking_deviations(SR, N), 10.0)

    def test_le_taux_de_rupture_est_le_compte_rapporte_a_l_echantillon(self):
        k = breaking_deviations(SR, N)
        self.assertAlmostEqual(breaking_rate(SR, N), k / N, places=12)

    def test_un_sharpe_nul_rompt_immediatement(self):
        self.assertEqual(breaking_deviations(0.0, N), 0.0)

    def test_la_rupture_recule_quand_l_echantillon_grandit(self):
        ks = [breaking_deviations(SR, n) for n in (2000, 7012, 20000)]
        self.assertEqual(ks, sorted(ks))

    def test_le_franchissement_bascule_au_point_de_rupture(self):
        k = breaking_deviations(SR, N)
        avant = deviation_cost(max(0.0, k - 1.0) / N, N)
        apres = deviation_cost((k + 1.0) / N, N)
        self.assertTrue(avant.clears(SR))
        self.assertFalse(apres.clears(SR))


if __name__ == "__main__":
    unittest.main()
