"""Tests des deux mesures venues d'autres disciplines.

Le test décisif est celui du plancher : sur une série sans aucune structure,
l'entropie de permutation doit rendre **moins de un**. Si elle rendait un, le
module ne mesurerait pas le biais d'échantillon fini qu'il existe pour
signaler, et une martingale passerait pour structurée.
"""

from __future__ import annotations

import math
import unittest

from alp1.dataset import Bar, Session, synthetic_sessions
from alp1.mc import Rng
from alp1.nonlinear import (
    EMBED,
    dfa,
    null_dfa,
    null_permutation,
    permutation_counts,
    permutation_entropy,
)


def _monotone(n: int = 400) -> list[Session]:
    """Séances strictement croissantes : un seul motif ordinal possible."""
    out = []
    for d in range(6):
        bars = tuple(Bar(f"d{d}", m, 100.0 + m, 100.0 + m, 100.0 + m,
                         100.0 + m, 0.0) for m in range(n))
        out.append(Session(f"d{d}", bars))
    return out


class TestMotifs(unittest.TestCase):
    def test_le_nombre_de_fenetres_est_juste(self):
        c = permutation_counts([1.0, 2.0, 3.0, 4.0, 5.0], 3)
        self.assertEqual(sum(c.values()), 3)

    def test_une_serie_croissante_n_a_qu_un_motif(self):
        c = permutation_counts([1.0, 2.0, 3.0, 4.0, 5.0], 3)
        self.assertEqual(len(c), 1)

    def test_une_longueur_inferieure_a_deux_est_refusee(self):
        with self.assertRaises(ValueError):
            permutation_counts([1.0, 2.0], 1)


class TestEntropieDePermutation(unittest.TestCase):
    def test_une_serie_deterministe_a_une_entropie_nulle(self):
        """Le cas de vérité connue : un seul motif, donc zéro bit."""
        pe = permutation_entropy(_monotone(), 3)
        self.assertAlmostEqual(pe.entropy, 0.0, places=9)
        self.assertEqual(pe.n_patterns, 1)

    def test_une_serie_sans_structure_approche_un(self):
        pe = permutation_entropy(synthetic_sessions(120, seed=1), 3)
        self.assertGreater(pe.entropy, 0.999)
        self.assertLess(pe.entropy, 1.0)

    def test_tous_les_motifs_apparaissent_sur_une_serie_aleatoire(self):
        for d in EMBED:
            with self.subTest(d=d):
                pe = permutation_entropy(synthetic_sessions(120, seed=3), d)
                self.assertEqual(pe.n_patterns, math.factorial(d))

    def test_le_deficit_est_en_bits(self):
        pe = permutation_entropy(synthetic_sessions(60, seed=5), 3)
        attendu = (1.0 - pe.entropy) * math.log2(6)
        self.assertAlmostEqual(pe.deficit, attendu, places=12)

    def test_un_echantillon_trop_court_est_refuse(self):
        court = [Session("j", (Bar("j", 0, 1.0, 1.0, 1.0, 1.0, 0.0),))]
        with self.assertRaises(ValueError):
            permutation_entropy(court, 3)


class TestPlancher(unittest.TestCase):
    """Le fait qui justifie tout le module."""

    @classmethod
    def setUpClass(cls):
        cls.nuls = {d: null_permutation(d, n_sessions=100, draws=5)
                    for d in EMBED}

    def test_le_plancher_est_sous_un(self):
        for d, n in self.nuls.items():
            with self.subTest(d=d):
                self.assertLess(n.mean, 1.0)
                self.assertGreater(n.sd, 0.0)

    def test_le_plancher_se_creuse_avec_la_longueur_du_motif(self):
        """Plus il y a de motifs, moins ils peuvent être équiprobables."""
        moyennes = [self.nuls[d].mean for d in sorted(EMBED)]
        self.assertEqual(moyennes, sorted(moyennes, reverse=True))

    def test_une_serie_sans_structure_n_est_pas_declaree_structuree(self):
        for d, n in self.nuls.items():
            with self.subTest(d=d):
                pe = permutation_entropy(
                    synthetic_sessions(100, seed=20260821), d)
                self.assertFalse(n.structured(pe.entropy))

    def test_une_serie_deterministe_est_declaree_structuree(self):
        for d, n in self.nuls.items():
            with self.subTest(d=d):
                self.assertTrue(n.structured(permutation_entropy(
                    _monotone(), d).entropy))

    def test_un_tirage_unique_est_refuse(self):
        with self.assertRaises(ValueError):
            null_permutation(3, n_sessions=20, draws=1)


class TestDFA(unittest.TestCase):
    def test_une_marche_aleatoire_donne_un_demi(self):
        a = dfa(synthetic_sessions(150, seed=20260821))
        self.assertAlmostEqual(a.alpha, 0.5, delta=0.02)
        self.assertTrue(a.diffusive)

    def test_l_ajustement_est_bon(self):
        self.assertGreater(dfa(synthetic_sessions(120, seed=9)).r2, 0.99)

    def test_le_biais_est_plus_faible_que_celui_du_ratio_de_variance(self):
        """Le résultat que la section cite : la physiologie bat l'économétrie."""
        m, _ = null_dfa(n_sessions=120, draws=4)
        self.assertLess(abs(m - 0.5), 0.5208 - 0.5)

    def test_le_plancher_du_dfa_est_positif_mais_petit(self):
        m, sd = null_dfa(n_sessions=120, draws=4)
        self.assertGreater(m, 0.5)
        self.assertLess(m, 0.52)
        self.assertGreater(sd, 0.0)

    def test_trop_peu_d_echelles_est_refuse(self):
        with self.assertRaises(ValueError):
            dfa(synthetic_sessions(5, seed=1), scales=(8, 16))

    def test_un_tirage_unique_est_refuse(self):
        with self.assertRaises(ValueError):
            null_dfa(n_sessions=20, draws=1)


if __name__ == "__main__":
    unittest.main()
