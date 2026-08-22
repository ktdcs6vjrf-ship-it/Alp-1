"""Tests du plafond d'information.

Les identités d'abord — entropie binaire, divergence, inversion — puis les cas
de vérité connue, puis le biais. Le test décisif est celui du biais : un
estimateur d'information mutuelle appliqué à deux variables indépendantes doit
rendre une valeur **strictement positive**, faute de quoi le module ne
mesurerait pas le piège qu'il existe pour signaler.
"""

from __future__ import annotations

import math
import unittest

from alp1.entropy import (
    binary_entropy,
    growth_from_bits,
    kl_bernoulli,
    miller_madow,
    mutual_information,
    null_mutual_information,
    observations_for_bits,
    required_bits,
    trades_for_information,
)


class TestIdentites(unittest.TestCase):
    def test_l_entropie_est_maximale_a_un_demi(self):
        self.assertAlmostEqual(binary_entropy(0.5), 1.0, places=12)
        for p in (0.1, 0.3, 0.7, 0.9):
            with self.subTest(p=p):
                self.assertLess(binary_entropy(p), 1.0)

    def test_l_entropie_est_nulle_aux_bords(self):
        for p in (0.0, 1.0):
            with self.subTest(p=p):
                self.assertAlmostEqual(binary_entropy(p), 0.0, places=12)

    def test_l_entropie_est_symetrique(self):
        for p in (0.1, 0.25, 0.4):
            with self.subTest(p=p):
                self.assertAlmostEqual(binary_entropy(p),
                                       binary_entropy(1 - p), places=12)

    def test_la_divergence_est_nulle_si_les_lois_coincident(self):
        for p in (0.05, 0.5, 0.95):
            with self.subTest(p=p):
                self.assertAlmostEqual(kl_bernoulli(p, p), 0.0, places=12)

    def test_la_divergence_est_positive_sinon(self):
        for p, q in ((0.5, 0.4), (0.05, 0.048), (0.9, 0.5)):
            with self.subTest(p=p, q=q):
                self.assertGreater(kl_bernoulli(p, q), 0.0)

    def test_la_divergence_n_est_pas_symetrique(self):
        """Ce n'est pas une distance, et le document s'en sert comme telle.

        Le couple doit être choisi hors de l'axe ``q = 1 − p``, où les deux
        sens coïncident par symétrie de la loi binaire — une coïncidence qui
        ne dit rien de la divergence en général.
        """
        self.assertNotAlmostEqual(kl_bernoulli(0.5, 0.1),
                                  kl_bernoulli(0.1, 0.5), places=6)

    def test_la_divergence_est_symetrique_sur_l_axe_complementaire(self):
        """Le cas particulier qui a failli tromper le test précédent."""
        self.assertAlmostEqual(kl_bernoulli(0.6, 0.4),
                               kl_bernoulli(0.4, 0.6), places=12)

    def test_le_plafond_de_kelly_est_l_information(self):
        for b in (0.0, 1e-6, 0.5, 3.0):
            with self.subTest(bits=b):
                self.assertEqual(growth_from_bits(b), b)

    def test_une_valeur_hors_bornes_est_refusee(self):
        for mauvais in (-0.1, 1.1):
            with self.subTest(p=mauvais):
                with self.assertRaises(ValueError):
                    binary_entropy(mauvais)


class TestExigence(unittest.TestCase):
    def test_la_reussite_martingale_est_la_probabilite_de_premier_passage(self):
        for rr in (2.0, 5.0, 20.0, 50.0):
            with self.subTest(rr=rr):
                self.assertAlmostEqual(required_bits(rr, 0.01).hit_null,
                                       1.0 / (rr + 1.0), places=12)

    def test_sans_friction_aucune_information_n_est_requise(self):
        r = required_bits(20.0, 0.0)
        self.assertAlmostEqual(r.bits, 0.0, places=12)
        self.assertAlmostEqual(r.hit_needed, r.hit_null, places=12)

    def test_l_exigence_croit_avec_la_friction(self):
        bits = [required_bits(20.0, c).bits
                for c in (0.005, 0.0143, 0.05, 0.11)]
        self.assertEqual(bits, sorted(bits))

    def test_l_exigence_decroit_avec_le_ratio_vise(self):
        bits = [required_bits(rr, 0.0143).bits for rr in (2, 5, 20, 50)]
        self.assertEqual(bits, sorted(bits, reverse=True))

    def test_la_geometrie_du_document_divise_l_exigence(self):
        """Le fait que la section cite : le facteur dépasse celui du IR."""
        v1 = required_bits(20.0, 0.1100).bits
        v2 = required_bits(20.0, 0.0143).bits
        self.assertGreater(v1 / v2, 20.0)

    def test_un_ratio_negatif_est_refuse(self):
        with self.assertRaises(ValueError):
            required_bits(-1.0, 0.01)


class TestEchantillon(unittest.TestCase):
    def test_l_echantillon_est_inversement_proportionnel_a_l_information(self):
        a = trades_for_information(1e-4)
        b = trades_for_information(2e-4)
        self.assertAlmostEqual(a / b, 2.0, places=6)

    def test_une_information_nulle_exige_un_echantillon_infini(self):
        self.assertEqual(trades_for_information(0.0), math.inf)
        self.assertEqual(observations_for_bits(0.0), math.inf)

    def test_la_decision_est_plus_exigeante_que_l_estimation(self):
        """Sortir du biais ne suffit pas à décider."""
        for b in (1e-5, 1e-4, 1e-3):
            with self.subTest(bits=b):
                self.assertGreater(trades_for_information(b),
                                   observations_for_bits(b))

    def test_une_puissance_hors_bornes_est_refusee(self):
        with self.assertRaises(ValueError):
            trades_for_information(1e-4, power=1.5)


class TestBiais(unittest.TestCase):
    """L'estimateur voit de la dépendance là où il n'y en a aucune."""

    def test_l_information_d_une_table_independante_est_positive(self):
        nul = null_mutual_information(2, 2, 1000, draws=120)
        self.assertGreater(nul.mean, 0.0)
        self.assertGreater(nul.q95, nul.mean)

    def test_le_biais_decroit_avec_l_echantillon(self):
        moyennes = [null_mutual_information(2, 2, n, draws=80).mean
                    for n in (500, 2000, 8000)]
        self.assertEqual(moyennes, sorted(moyennes, reverse=True))

    def test_le_biais_est_de_l_ordre_de_la_formule(self):
        """(r−1)(c−1)/(2N ln 2) : l'ordre de grandeur doit être retrouvé."""
        n = 2000
        attendu = 1.0 / (2.0 * n * math.log(2.0))
        mesure = null_mutual_information(2, 2, n, draws=150).mean
        self.assertGreater(mesure, attendu * 0.4)
        self.assertLess(mesure, attendu * 2.5)

    def test_la_correction_reduit_le_biais(self):
        from alp1.mc import Rng
        rng = Rng(7)
        t = [[0, 0], [0, 0]]
        for _ in range(1500):
            t[rng.randint(2)][rng.randint(2)] += 1
        self.assertLess(miller_madow(t), mutual_information(t))

    def test_une_table_parfaitement_dependante_donne_un_bit(self):
        self.assertAlmostEqual(mutual_information([[500, 0], [0, 500]]),
                               1.0, places=9)

    def test_une_table_vide_est_refusee(self):
        with self.assertRaises(ValueError):
            mutual_information([[0, 0], [0, 0]])

    def test_une_table_degeneree_est_refusee(self):
        with self.assertRaises(ValueError):
            null_mutual_information(1, 2, 100)


if __name__ == "__main__":
    unittest.main()
