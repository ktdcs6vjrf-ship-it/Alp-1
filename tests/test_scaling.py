"""Tests de la calibration sous exposant d'échelle imposé.

Le test décisif est le premier : à H = ½, la chaîne refaite doit rendre
*exactement* les cinq nombres du document. Sans cela, les écarts rapportés
aux autres exposants mesureraient une erreur d'implémentation et non une
propriété du modèle.

Les suivants portent sur les identités de la calibration, sur le sens dans
lequel la conclusion se déplace, et sur le fait que l'optimum d'heure d'entrée
est intérieur — ce qui est la raison pour laquelle il vaut la peine d'être
cherché.
"""

from __future__ import annotations

import math
import unittest

from alp1.calib import REFERENCE, derive
from alp1.scaling import (
    HURST_ASSUMED,
    HURST_HI,
    HURST_LO,
    HURST_MARTINGALE,
    calibrate,
    coherence_gap,
    robust_entry,
    sensitivity,
    worst_case,
)


class TestAncrage(unittest.TestCase):
    """À H = ½, le changement de temps est l'identité."""

    def setUp(self):
        self.doc = derive(REFERENCE)
        self.s = calibrate(HURST_MARTINGALE,
                           session_dispersion=REFERENCE.session_dispersion,
                           session_min=REFERENCE.session_min,
                           entry_min=REFERENCE.entry_min,
                           friction=REFERENCE.friction)

    def test_la_volatilite_par_minute_est_celle_du_document(self):
        self.assertAlmostEqual(self.s.sigma_1min, self.doc.sigma_1min, places=12)

    def test_la_bande_de_bruit_est_celle_du_document(self):
        self.assertAlmostEqual(self.s.band, self.doc.stop, places=12)

    def test_la_probabilite_d_arret_est_celle_du_document(self):
        self.assertAlmostEqual(self.s.p_stop, self.doc.p_stop, places=12)

    def test_l_exposition_est_celle_du_document(self):
        self.assertAlmostEqual(self.s.exposure, self.doc.exposure, places=9)

    def test_le_seuil_de_signal_est_celui_du_document(self):
        self.assertAlmostEqual(self.s.ir_star, self.doc.ir_star, places=12)

    def test_la_derive_requise_est_celle_du_document(self):
        self.assertAlmostEqual(self.s.mu_star_per_hour,
                               self.doc.mu_star_per_hour, places=9)


class TestIdentites(unittest.TestCase):
    def test_la_dispersion_de_seance_est_reconstituee(self):
        """σ₁·T^H doit rendre la dispersion posée, quel que soit H."""
        for h in (0.5, 0.55, 0.6, 0.65, 0.7):
            with self.subTest(H=h):
                s = calibrate(h)
                self.assertAlmostEqual(
                    s.sigma_1min * (s.session_min ** h),
                    s.session_dispersion, places=10)

    def test_la_bande_est_le_deplacement_absolu_moyen(self):
        for h in (0.5, 0.6, 0.65):
            with self.subTest(H=h):
                s = calibrate(h)
                attendu = (s.sigma_1min * (s.entry_min ** h)
                           * math.sqrt(2.0 / math.pi))
                self.assertAlmostEqual(s.band, attendu, places=12)

    def test_la_derive_requise_est_la_friction_sur_l_exposition(self):
        for h in (0.5, 0.6, 0.65):
            with self.subTest(H=h):
                s = calibrate(h)
                self.assertAlmostEqual(s.mu_star * s.exposure, s.friction,
                                       places=12)

    def test_l_exposition_ne_depasse_pas_la_seance_restante(self):
        for h in (0.5, 0.55, 0.6, 0.65):
            with self.subTest(H=h):
                s = calibrate(h)
                self.assertLessEqual(s.exposure, s.horizon + 1e-9)


class TestSens(unittest.TestCase):
    """La persistance joue contre la stratégie, et non pour elle."""

    def test_le_seuil_monte_avec_l_exposant(self):
        irs = [s.ir_star for s in sensitivity(HURST_LO, HURST_HI, 9)]
        self.assertEqual(irs, sorted(irs))

    def test_la_probabilite_d_arret_monte_avec_l_exposant(self):
        ps = [s.p_stop for s in sensitivity(HURST_LO, HURST_HI, 9)]
        self.assertEqual(ps, sorted(ps))

    def test_la_volatilite_par_minute_baisse_avec_l_exposant(self):
        """Une même dispersion de séance sur un exposant plus grand tient en
        une volatilité par minute plus faible."""
        sig = [s.sigma_1min for s in sensitivity(HURST_LO, HURST_HI, 9)]
        self.assertEqual(sig, sorted(sig, reverse=True))

    def test_le_pire_cas_est_a_la_borne_haute(self):
        self.assertAlmostEqual(worst_case().hurst, HURST_HI, places=9)

    def test_l_ecart_de_coherence_est_defavorable(self):
        a, b, facteur = coherence_gap()
        self.assertGreater(b, a)
        self.assertGreater(facteur, 1.0)
        self.assertAlmostEqual(facteur, b / a, places=12)

    def test_l_ecart_de_coherence_est_celui_de_l_exposant_invoque(self):
        _, b, _ = coherence_gap()
        self.assertAlmostEqual(b, calibrate(HURST_ASSUMED).ir_star, places=12)


class TestHeureDEntree(unittest.TestCase):
    def test_l_optimum_est_interieur(self):
        """Ni la première ni la dernière heure explorée ne minimise le seuil."""
        r = robust_entry()
        mus = [m for _, _, m, _ in r]
        i = mus.index(min(mus))
        self.assertNotIn(i, (0, len(mus) - 1))

    def test_le_seuil_et_la_derive_requise_designent_la_meme_heure(self):
        r = robust_entry()
        par_mu = min(r, key=lambda x: x[2])[0]
        par_ir = min(r, key=lambda x: x[3])[0]
        self.assertEqual(par_mu, par_ir)

    def test_l_heure_du_protocole_est_evaluee(self):
        heures = [t for t, _, _, _ in robust_entry()]
        self.assertIn(REFERENCE.entry_min, heures)

    def test_l_optimum_bat_l_heure_du_protocole(self):
        r = robust_entry()
        meilleur = min(x[2] for x in r)
        protocole = [x[2] for x in r if x[0] == REFERENCE.entry_min][0]
        self.assertLess(meilleur, protocole)

    def test_chaque_heure_est_evaluee_au_pire_cas(self):
        for t, expo, mu, ir in robust_entry():
            with self.subTest(entree=t):
                w = worst_case(entry_min=t)
                self.assertAlmostEqual(ir, w.ir_star, places=12)
                self.assertAlmostEqual(expo, w.exposure, places=12)


class TestEntrees(unittest.TestCase):
    def test_un_exposant_hors_bornes_est_refuse(self):
        for mauvais in (0.0, 1.0, -0.2, 1.4):
            with self.subTest(H=mauvais):
                with self.assertRaises(ValueError):
                    calibrate(mauvais)

    def test_une_entree_apres_la_cloture_est_refusee(self):
        with self.assertRaises(ValueError):
            calibrate(0.5, entry_min=400.0, session_min=390.0)

    def test_une_dispersion_negative_est_refusee(self):
        with self.assertRaises(ValueError):
            calibrate(0.5, session_dispersion=-1.0)


if __name__ == "__main__":
    unittest.main()
