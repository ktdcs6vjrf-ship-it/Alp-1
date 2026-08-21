"""Tests de la loi d'échelle mesurée.

Trois familles. Les **identités** : VR(1) vaut un, l'exposant se retrouve à
partir du VR, une martingale donne ½. Les **cas de vérité connue** : le VR d'un
AR(1) a une forme fermée, et l'estimateur doit la retrouver — c'est le seul
test qui prouve que le code mesure ce qu'il prétend. Le **découpage** : aucun
rendement ne doit enjamber un trou ni une frontière de séance.

Le test le plus important est celui du biais : sur une marche aléatoire de
390 minutes, l'estimateur brut dérive vers le haut et le z asymptotique rejette
la marche aléatoire. La correction par loi nulle doit ramener l'exposant à ½ à
tous les horizons, faute de quoi le module ferait passer une martingale pour un
marché persistant — exactement l'erreur qu'il est écrit pour empêcher.
"""

from __future__ import annotations

import math
import unittest

from alp1.dataset import Bar, Session, synthetic_sessions
from alp1.mc import Rng
from alp1.varratio import (
    Q_GRID,
    hurst_from_vr,
    hurst_regression,
    log_returns,
    null_grid,
    null_reference,
    scan,
    variance_ratio,
)


def vr_ar1(rho: float, q: int) -> float:
    """VR(q) exact d'un AR(1) : 1 + 2 Σ_{j<q} (1 − j/q) ρ^j."""
    return 1.0 + 2.0 * sum((1 - j / q) * rho ** j for j in range(1, q))


def sessions_ar1(rho: float, n_days: int = 400, n_min: int = 390,
                 sigma: float = 5e-4, seed: int = 7) -> list[Session]:
    """Séances dont les rendements suivent un AR(1) de coefficient connu."""
    rng = Rng(seed)
    out = []
    for d in range(n_days):
        px, r, bars = 6000.0, 0.0, []
        for m in range(n_min):
            r = rho * r + rng.gauss() * sigma
            px *= math.exp(r)
            bars.append(Bar(f"d{d}", m, px, px, px, px, 0.0))
        out.append(Session(f"d{d}", tuple(bars)))
    return out


class TestIdentites(unittest.TestCase):
    def test_un_ratio_unitaire_donne_un_demi(self):
        for q in (2, 5, 10, 60):
            with self.subTest(q=q):
                self.assertAlmostEqual(hurst_from_vr(1.0, q), 0.5, places=12)

    def test_l_exposant_s_inverse(self):
        """VR = q^(2H−1) doit se retrouver à partir de H."""
        for h in (0.40, 0.50, 0.55, 0.65):
            for q in (2, 10, 30):
                with self.subTest(H=h, q=q):
                    vr = q ** (2 * h - 1)
                    self.assertAlmostEqual(hurst_from_vr(vr, q), h, places=10)

    def test_un_horizon_inferieur_a_deux_est_refuse(self):
        for q in (0, 1, -3):
            with self.subTest(q=q):
                with self.assertRaises(ValueError):
                    hurst_from_vr(1.0, q)


class TestVeriteConnue(unittest.TestCase):
    """Le VR d'un AR(1) a une forme fermée ; l'estimateur doit la retrouver."""

    def test_l_estimateur_retrouve_le_vr_d_un_ar1_persistant(self):
        s = sessions_ar1(0.15)
        for q in (2, 5):
            with self.subTest(q=q):
                mesure = variance_ratio(s, q).vr
                self.assertAlmostEqual(mesure, vr_ar1(0.15, q), delta=0.02)

    def test_l_estimateur_retrouve_le_vr_d_un_ar1_anti_persistant(self):
        s = sessions_ar1(-0.15, seed=11)
        for q in (2, 5):
            with self.subTest(q=q):
                mesure = variance_ratio(s, q).vr
                self.assertAlmostEqual(mesure, vr_ar1(-0.15, q), delta=0.02)

    def test_le_signe_de_l_autocorrelation_donne_le_sens_de_l_exposant(self):
        pos = variance_ratio(sessions_ar1(0.15), 2)
        neg = variance_ratio(sessions_ar1(-0.15, seed=11), 2)
        self.assertGreater(pos.hurst, 0.5)
        self.assertLess(neg.hurst, 0.5)


class TestBiaisEtLoiNulle(unittest.TestCase):
    """Sans correction, une marche aléatoire paraît persistante."""

    @classmethod
    def setUpClass(cls):
        cls.sessions = synthetic_sessions(200, seed=20260821)
        cls.nulls = null_grid(n_sessions=200, draws=8)

    def test_le_biais_brut_croit_avec_l_horizon(self):
        """C'est le fait qui justifie tout le reste du module."""
        moyennes = [self.nulls[q].mean for q in Q_GRID]
        self.assertEqual(moyennes, sorted(moyennes))
        self.assertGreater(moyennes[-1], 1.05)

    def test_la_loi_nulle_est_au_dessus_de_un(self):
        for q, n in self.nulls.items():
            with self.subTest(q=q):
                self.assertGreater(n.mean, 1.0)
                self.assertGreater(n.sd, 0.0)

    def test_l_exposant_corrige_vaut_un_demi_a_tout_horizon(self):
        for r in scan(self.sessions):
            with self.subTest(q=r.q):
                self.assertAlmostEqual(
                    r.hurst_corrected(self.nulls[r.q]), 0.5, delta=0.01)

    def test_l_exposant_brut_derive_lui(self):
        """Le contraste avec le test précédent est le résultat du module."""
        brut = [r.hurst for r in scan(self.sessions)]
        self.assertGreater(max(brut), 0.51)

    def test_la_regression_corrigee_vaut_un_demi(self):
        corr = hurst_regression(self.sessions, nulls=self.nulls)
        self.assertAlmostEqual(corr.hurst, 0.5, delta=0.01)
        self.assertTrue(corr.diffusive)

    def test_le_z_nul_ne_rejette_pas_une_marche_aleatoire(self):
        """Le z asymptotique, lui, la rejette — c'est pourquoi il ne décide pas."""
        for r in scan(self.sessions):
            with self.subTest(q=r.q):
                self.assertLess(abs(r.z_null(self.nulls[r.q])), 4.0)

    def test_une_loi_nulle_a_un_seul_tirage_est_refusee(self):
        with self.assertRaises(ValueError):
            null_reference(5, n_sessions=20, draws=1)


class TestDecoupage(unittest.TestCase):
    """Aucun rendement n'enjambe un trou ni une frontière de séance."""

    def _seance(self, minutes, prix):
        bars = tuple(Bar("j", m, p, p, p, p, 0.0) for m, p in zip(minutes, prix))
        return Session("j", bars)

    def test_un_trou_coupe_la_serie(self):
        s = self._seance([0, 1, 5, 6], [100.0, 101.0, 200.0, 202.0])
        r = log_returns(s)
        self.assertEqual(len(r), 2)
        self.assertAlmostEqual(r[0], math.log(101 / 100), places=12)
        self.assertAlmostEqual(r[1], math.log(202 / 200), places=12)

    def test_le_saut_du_trou_n_est_pas_compte(self):
        """Un rendement de 100 à 200 apparaîtrait s'il l'était."""
        s = self._seance([0, 1, 5, 6], [100.0, 101.0, 200.0, 202.0])
        self.assertTrue(all(abs(x) < 0.1 for x in log_returns(s)))

    def test_deux_seances_ne_se_recollent_pas(self):
        """Deux séances à niveaux très différents donnent deux segments."""
        a = self._seance(list(range(6)), [100.0 + i for i in range(6)])
        b = Session("k", tuple(Bar("k", m, p, p, p, p, 0.0)
                               for m, p in enumerate(
                                   [500.0 + 5 * i for i in range(6)])))
        r = variance_ratio([a, b], 2)
        self.assertEqual(r.n_segments, 2)
        self.assertEqual(r.n_returns, 10)

    def test_un_segment_de_longueur_exactement_q_est_ecarte(self):
        """Son poids de correction ``(1 − q/n)`` est nul : il ne pèse rien."""
        court = self._seance([0, 1, 2], [100.0, 101.0, 102.0])
        with self.assertRaises(ValueError):
            variance_ratio([court], 2)

    def test_un_echantillon_trop_court_est_refuse(self):
        s = self._seance([0, 1], [100.0, 101.0])
        with self.assertRaises(ValueError):
            variance_ratio([s], 10)


if __name__ == "__main__":
    unittest.main()
