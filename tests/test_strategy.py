"""Tests de la stratégie scellée et de sa batterie.

Trois exigences. La **spécification** ne doit rien laisser d'ajustable : le
budget de configurations se déduit des portes ouvertes, et l'ouvrir se paie.
La **règle** doit être exécutable et déterministe : mêmes séances, mêmes
trades, au prix de sortie près. La **batterie** doit refuser une série sans
dérive — un contrôle qui accepte tout ne contrôle rien, et c'est le seul test
qui distingue une batterie d'une décoration.
"""

from __future__ import annotations

import math
import unittest

from alp1.costs import deflated_threshold_sharpe
from alp1.dataset import Bar, Session, synthetic_sessions
from alp1.strategy import (
    ENTRY_MIN,
    EXIT_MIN,
    GATES,
    MAX_ENTRIES,
    REFERENCE_BITS,
    SEALED,
    Spec,
    gate_cost,
    lag1_autocorrelation,
    local_volatility_factor,
    run,
    scan_session,
    validate,
)


class TestSpecification(unittest.TestCase):
    def test_seules_deux_portes_sont_ouvertes_par_defaut(self):
        cles = {g.key for g in SEALED.open_gates}
        self.assertEqual(cles, {"band", "localvol"})

    def test_le_declencheur_et_la_correction_ne_coutent_rien(self):
        """Ni l'un ni l'autre ne décide d'une entrée optionnelle."""
        self.assertEqual(SEALED.optional_open, ())
        self.assertEqual(SEALED.budget, 1.0)

    def test_chaque_porte_ouverte_double_la_famille(self):
        s = SEALED
        for i, cle in enumerate(("dow", "vwapband", "ote"), start=1):
            s = s.with_gate(cle, True)
            with self.subTest(porte=cle):
                self.assertEqual(s.budget, 2.0 ** i)

    def test_une_configuration_unique_ne_paie_aucune_taxe(self):
        self.assertEqual(deflated_threshold_sharpe(SEALED.budget, 7012), 0.0)

    def test_ouvrir_une_porte_cree_un_seuil(self):
        """Le fait que la section cite : le seuil passe de zéro à non nul."""
        s = SEALED.with_gate("dow", True)
        self.assertGreater(deflated_threshold_sharpe(s.budget, 7012), 0.0)

    def test_ouvrir_toutes_les_portes_consomme_l_essentiel_du_sharpe(self):
        s = SEALED
        for g in GATES:
            if g.key not in ("band", "localvol"):
                s = s.with_gate(g.key, True)
        seuil = deflated_threshold_sharpe(s.budget, 7012)
        self.assertGreater(seuil / 0.0332, 0.9)

    def test_une_porte_inconnue_est_refusee(self):
        with self.assertRaises(KeyError):
            SEALED.with_gate("inexistante", True)

    def test_chaque_porte_declare_ce_qu_elle_exige(self):
        for g in GATES:
            with self.subTest(porte=g.key):
                self.assertTrue(g.needs)
                self.assertTrue(g.rationale)
                self.assertEqual(g.available, g.needs == ("minute",))

    def test_le_cout_des_portes_couvre_toutes_les_fermees(self):
        fermees = {g.key for g in GATES
                   if not g.enabled and g.key not in ("band", "localvol")}
        self.assertEqual({g.key for g, _, _ in gate_cost()}, fermees)


class TestRegle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sessions = synthetic_sessions(80, seed=20260822)

    def test_la_regle_est_deterministe(self):
        a = run(self.sessions)
        b = run(self.sessions)
        self.assertEqual([t.net_points for t in a], [t.net_points for t in b])

    def test_aucune_entree_avant_l_heure_scellee(self):
        for t in run(self.sessions):
            with self.subTest(jour=t.day):
                self.assertGreaterEqual(t.entry_minute, ENTRY_MIN)

    def test_aucune_entree_apres_l_heure_de_sortie(self):
        for t in run(self.sessions):
            with self.subTest(jour=t.day):
                self.assertLess(t.entry_minute, EXIT_MIN)

    def test_le_plafond_d_entrees_est_respecte(self):
        compte: dict[str, int] = {}
        for t in run(self.sessions):
            compte[t.day] = compte.get(t.day, 0) + 1
        for jour, n in compte.items():
            with self.subTest(jour=jour):
                self.assertLessEqual(n, MAX_ENTRIES)

    def test_la_sortie_suit_toujours_l_entree(self):
        for t in run(self.sessions):
            with self.subTest(jour=t.day):
                self.assertGreaterEqual(t.exit_minute, t.entry_minute)

    def test_le_pire_remplissage_n_est_jamais_meilleur(self):
        opt = run(self.sessions, fill="stop")
        bad = run(self.sessions, fill="extreme")
        self.assertEqual(len(opt), len(bad))
        moy = lambda ts: sum(t.net_points for t in ts) / len(ts)
        self.assertGreaterEqual(moy(opt), moy(bad))

    def test_un_remplissage_inconnu_est_refuse(self):
        with self.assertRaises(ValueError):
            scan_session(self.sessions[0], 3.0, 0.5, fill="worst")

    def test_une_seance_vide_ne_produit_rien(self):
        self.assertEqual(scan_session(Session("j", ()), 3.0, 0.5), [])


class TestVolatiliteLocale(unittest.TestCase):
    def _seance(self, volumes):
        bars = tuple(Bar("j", m, 6000.0 + m * 0.1, 6000.0 + m * 0.1 + 0.5,
                         6000.0 + m * 0.1 - 0.5, 6000.0 + m * 0.1, v)
                     for m, v in enumerate(volumes))
        return Session("j", bars)

    def test_le_facteur_est_borne(self):
        for v in ([1.0] * 200, [0.0] * 200, list(range(1, 201))):
            with self.subTest():
                f = local_volatility_factor(self._seance(v), 199)
                self.assertGreaterEqual(f, 0.6)
                self.assertLessEqual(f, 1.8)

    def test_sans_volume_le_facteur_est_neutre(self):
        self.assertEqual(local_volatility_factor(self._seance([0.0] * 200), 199),
                         1.0)

    def test_trop_peu_de_barres_donne_un_facteur_neutre(self):
        self.assertEqual(local_volatility_factor(self._seance([5.0] * 10), 9),
                         1.0)


class TestAutocorrelation(unittest.TestCase):
    def test_une_serie_constante_n_est_pas_correlee(self):
        self.assertEqual(lag1_autocorrelation([2.0] * 50), 0.0)

    def test_une_alternance_est_anti_correlee(self):
        self.assertLess(lag1_autocorrelation([1.0, -1.0] * 40), -0.5)

    def test_une_serie_croissante_est_correlee(self):
        self.assertGreater(lag1_autocorrelation([float(i) for i in range(60)]),
                           0.5)

    def test_le_resultat_reste_dans_l_intervalle_ouvert(self):
        for xs in ([1.0, -1.0] * 40, [float(i) for i in range(60)]):
            with self.subTest():
                self.assertLess(abs(lag1_autocorrelation(xs)), 1.0)

    def test_une_serie_trop_courte_rend_zero(self):
        self.assertEqual(lag1_autocorrelation([1.0, 2.0]), 0.0)


class TestBatterie(unittest.TestCase):
    """Le test qui compte : une série sans dérive doit être refusée."""

    @classmethod
    def setUpClass(cls):
        sessions = synthetic_sessions(300, seed=20260822)
        cls.v = validate(run(sessions), draws=200)

    def test_une_serie_sans_derive_est_refusee(self):
        self.assertFalse(self.v.accepted)
        self.assertIn("refusé", self.v.summary)

    def test_l_echantillon_est_juge_sur_l_effet_a_detecter(self):
        """Et non sur l'effet observé, qui inverserait le test."""
        c = next(c for c in self.v.checks if c.key == "echantillon")
        self.assertGreater(c.threshold, 10000)
        self.assertFalse(c.passed)

    def test_le_seuil_de_reference_ne_depend_pas_des_donnees(self):
        a = validate(run(synthetic_sessions(120, seed=1)), draws=50)
        b = validate(run(synthetic_sessions(120, seed=2)), draws=50)
        seuil = lambda v: next(c.threshold for c in v.checks
                               if c.key == "echantillon")
        self.assertAlmostEqual(seuil(a), seuil(b), places=9)

    def test_la_pbo_est_sans_objet_sur_une_configuration_unique(self):
        c = next(c for c in self.v.checks if c.key == "pbo")
        self.assertTrue(c.passed)
        self.assertIn("sans objet", c.reading)

    def test_chaque_controle_porte_une_lecture(self):
        for c in self.v.checks:
            with self.subTest(controle=c.key):
                self.assertTrue(c.reading)
                self.assertTrue(c.label)

    def test_un_seul_controle_manque_suffit_a_refuser(self):
        self.assertEqual(self.v.accepted, not self.v.failed)
        self.assertTrue(self.v.failed)

    def test_les_controles_passes_et_manques_partitionnent(self):
        self.assertEqual(len(self.v.passed) + len(self.v.failed),
                         len(self.v.checks))

    def test_l_information_de_reference_est_celle_du_document(self):
        self.assertAlmostEqual(REFERENCE_BITS * 1e6, 422.0, delta=1.0)


if __name__ == "__main__":
    unittest.main()
