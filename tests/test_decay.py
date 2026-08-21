"""Tests de la décote post-publication et de la durée de vie résiduelle.

Ce module produit le seul nombre daté du document — l'année où la conclusion
cesse de tenir. Trois familles de tests l'encadrent : les identités qui lient
niveau, taux et demi-vie ; la cohérence entre le point de rupture exprimé en
décote et le même point exprimé en dérive ; et les cas limites, où une décote
nulle doit donner une durée de vie infinie et non une division par zéro.
"""

from __future__ import annotations

import math
import unittest

from alp1 import decay
from alp1.decay import (
    DECAY_POST_PUBLICATION,
    DECAY_WINDOW_YEARS,
    breaking_decay,
    breaking_rate,
    decay_rate,
    half_life,
    rate_box,
    runways,
    scenario_grid,
    surviving_edge,
    surviving_fraction,
    years_to_breaking,
)


class TestIdentites(unittest.TestCase):
    def test_le_taux_reproduit_la_decote_sur_sa_fenetre(self):
        """Par construction, λ perd exactement `level` en `window` années."""
        lam = decay_rate()
        reste = surviving_fraction(DECAY_WINDOW_YEARS, lam)
        self.assertAlmostEqual(reste, 1.0 - DECAY_POST_PUBLICATION, places=12)

    def test_la_demi_vie_divise_par_deux(self):
        lam = decay_rate()
        self.assertAlmostEqual(surviving_fraction(half_life(lam), lam), 0.5,
                               places=12)

    def test_la_decroissance_est_multiplicative(self):
        """Deux décroissances successives valent une décroissance de la somme."""
        lam = decay_rate()
        a = surviving_fraction(3.0, lam) * surviving_fraction(4.0, lam)
        self.assertAlmostEqual(a, surviving_fraction(7.0, lam), places=12)

    def test_la_borne_haute_du_taux_consomme_la_decote_en_trois_ans(self):
        _, _, hi = rate_box()
        self.assertAlmostEqual(surviving_fraction(3.0, hi),
                               1.0 - DECAY_POST_PUBLICATION, places=12)


class TestPointDeRupture(unittest.TestCase):
    def test_la_decote_de_rupture_amene_exactement_au_seuil(self):
        d = breaking_decay(6.0, 1.16)
        self.assertAlmostEqual(6.0 * (1.0 - d), 1.16, places=12)

    def test_les_annees_de_rupture_amenent_exactement_au_seuil(self):
        y = years_to_breaking(6.0, 1.16)
        self.assertAlmostEqual(surviving_edge(6.0, y), 1.16, places=10)

    def test_le_taux_de_rupture_amene_exactement_au_seuil(self):
        r = breaking_rate(6.0, 1.16, 8.0)
        self.assertAlmostEqual(surviving_edge(6.0, 8.0, r), 1.16, places=10)

    def test_un_seuil_deja_atteint_ne_laisse_aucune_marge(self):
        self.assertEqual(breaking_decay(1.0, 2.0), 0.0)
        self.assertEqual(years_to_breaking(1.0, 2.0), 0.0)

    def test_un_taux_nul_ne_rompt_jamais(self):
        self.assertEqual(years_to_breaking(6.0, 1.16, rate=0.0), math.inf)


class TestRunway(unittest.TestCase):
    def setUp(self):
        self.rws = runways(6.0, 1.16, 2026)

    def test_une_entree_par_travail_source(self):
        self.assertEqual(len(self.rws), len(decay.PUBLICATION_YEARS))

    def test_les_sources_sont_ordonnees_par_annee(self):
        annees = [r.published for r in self.rws]
        self.assertEqual(annees, sorted(annees))

    def test_le_travail_le_plus_ancien_a_le_moins_de_marge(self):
        """Plus la publication est ancienne, plus la décote a couru."""
        marges = [r.margin for r in self.rws]
        self.assertEqual(marges, sorted(marges))

    def test_expiration_et_annees_restantes_concordent(self):
        for r in self.rws:
            with self.subTest(source=r.source):
                self.assertAlmostEqual(r.expiry - r.asof, r.remaining, places=9)

    def test_la_derive_a_l_expiration_vaut_le_seuil(self):
        for r in self.rws:
            with self.subTest(source=r.source):
                reste = surviving_edge(r.edge_bps, r.expiry - r.published, r.rate)
                self.assertAlmostEqual(reste, r.breaking_bps, places=9)

    def test_tenir_equivaut_a_une_marge_superieure_a_un(self):
        for r in self.rws:
            with self.subTest(source=r.source):
                self.assertEqual(r.holds, r.margin > 1.0)

    def test_un_age_negatif_est_ramene_a_zero(self):
        """Un travail publié après la date d'observation n'a pas décru."""
        r = runways(6.0, 1.16, 2010)[0]
        self.assertEqual(r.age, 0.0)
        self.assertAlmostEqual(r.edge_today, 6.0, places=12)


class TestGrille(unittest.TestCase):
    def test_la_grille_couvre_la_boite_de_taux(self):
        lo, _, hi = rate_box()
        g = scenario_grid(6.0, 1.16, 2026, 2018)
        self.assertAlmostEqual(g[0][0], lo, places=12)
        self.assertAlmostEqual(g[-1][0], hi, places=12)

    def test_la_derive_decroit_avec_le_taux(self):
        restes = [e for _, e, _, _ in scenario_grid(6.0, 1.16, 2026, 2018)]
        self.assertEqual(restes, sorted(restes, reverse=True))

    def test_le_verdict_suit_la_marge(self):
        for _, _, marge, tient in scenario_grid(6.0, 1.16, 2026, 2018):
            self.assertEqual(tient, marge > 1.0)

    def test_un_taux_nul_conserve_la_derive_publiee(self):
        _, edge, _, _ = scenario_grid(6.0, 1.16, 2026, 2018)[0]
        self.assertAlmostEqual(edge, 6.0, places=12)


class TestEntrees(unittest.TestCase):
    def test_un_niveau_hors_bornes_est_refuse(self):
        for mauvais in (-0.1, 1.0, 1.5):
            with self.subTest(niveau=mauvais):
                with self.assertRaises(ValueError):
                    decay_rate(mauvais)

    def test_une_fenetre_nulle_est_refusee(self):
        with self.assertRaises(ValueError):
            decay_rate(0.5, 0.0)

    def test_un_age_negatif_est_refuse(self):
        with self.assertRaises(ValueError):
            surviving_fraction(-1.0)


if __name__ == "__main__":
    unittest.main()
