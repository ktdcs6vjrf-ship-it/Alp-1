"""Le noyau statistique contrôlé contre des vérités connues."""

import math
import random
import unittest

from ofm import stats


class TestLois(unittest.TestCase):
    def test_quantile_normal(self):
        for p in (1e-6, 0.01, 0.025, 0.3, 0.5, 0.9, 0.975, 0.999999):
            self.assertAlmostEqual(stats.Phi(stats.Phi_inv(p)), p, places=11)

    def test_graine_stable(self):
        # Un CRC, pas le hash intégré : la même chaîne donne la même graine
        # dans tous les processus.
        self.assertEqual(stats.graine("raop"), stats.graine("raop"))
        self.assertNotEqual(stats.graine("raop"), stats.graine("speed"))
        self.assertEqual(stats.graine("a"), (stats.GRAINE ^ 0xE8B7BE43) & 0x7FFFFFFF)


class TestModeles(unittest.TestCase):
    def test_logit_retrouve_ses_coefficients(self):
        r = random.Random(7)
        X, y = [], []
        for _ in range(6000):
            x = r.gauss(0, 1)
            p = 1 / (1 + math.exp(-(-0.5 + 0.8 * x)))
            X.append([1.0, x])
            y.append(1.0 if r.random() < p else 0.0)
        fit = stats.logit(X, y, ["c", "x"])
        self.assertAlmostEqual(fit.b("x"), 0.8, delta=4 * fit.e("x"))
        self.assertAlmostEqual(fit.b("c"), -0.5, delta=4 * fit.e("c"))

    def test_mco_et_grappes(self):
        # Une grappe qui recopie dix fois la même observation ne doit pas
        # diviser l'écart-type par trois : c'est ce que la grappe corrige.
        r = random.Random(3)
        X, y, g = [], [], []
        for k in range(300):
            x, e = r.gauss(0, 1), r.gauss(0, 1)
            for _ in range(10):
                X.append([1.0, x]); y.append(0.5 * x + e); g.append(k)
        naif = stats.mco(X, y, ["c", "x"])
        grappe = stats.mco(X, y, ["c", "x"], grappes=g)
        self.assertGreater(grappe.e("x") / naif.e("x"), 2.5)


class TestCorrections(unittest.TestCase):
    def test_bh(self):
        q = stats.bh([0.01, 0.04, 0.03, 0.5])
        self.assertAlmostEqual(q[0], 0.04)
        self.assertAlmostEqual(q[1], 0.04 * 4 / 3, places=12)
        self.assertAlmostEqual(q[3], 0.5)

    def test_permutation_sans_lien(self):
        r = random.Random(11)
        y = [r.random() for _ in range(400)]
        g = [r.randint(0, 1) for _ in range(400)]
        _, p, nul = stats.permutation(y, g, tirages=400, nom="t")
        self.assertGreater(p, 0.01)
        self.assertEqual(len(nul), 400)

    def test_rayleigh(self):
        r = random.Random(5)
        uni = [r.uniform(0, 2 * math.pi) for _ in range(500)]
        self.assertGreater(stats.rayleigh(uni)[2], 0.01)
        conc = [r.vonmisesvariate(1.0, 2.0) for _ in range(500)]
        rbar, mu, p = stats.rayleigh(conc)
        self.assertLess(p, 1e-10)
        self.assertAlmostEqual(mu, 1.0, delta=0.1)


class TestBudget(unittest.TestCase):
    def test_taille_classique(self):
        # 10 % contre 11 % : environ 14 750 envois par bras, valeur de manuel.
        n = stats.n_par_bras(0.10, 0.10)
        self.assertTrue(14000 < n < 15500, n)
        self.assertAlmostEqual(stats.effet_detectable(n, 0.10), 0.10, places=3)


if __name__ == "__main__":
    unittest.main()
