"""La décomposition doit trouver l'avantage là où il est planté.

C'est le seul contrôle qui vaille pour une attribution : on plante la
compétence dans un levier connu, et la décomposition doit l'y désigner —
sans la répartir sur les autres. Une méthode d'attribution qu'on ne sait pas
mettre en défaut ne mesure rien.
"""

from __future__ import annotations

import unittest

from alp1.attribution import KEYS, coalition_value, decompose
from alp1.journal import Journal, synthesise

SESSIONS = 400
FORTE = 0.45


class TestProprietesDeShapley(unittest.TestCase):
    """Les trois axiomes qui rendent l'attribution unique."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.d = decompose(synthesise(skill=FORTE, size_skill=0.30,
                                     n_sessions=SESSIONS))

    def test_exhaustive(self) -> None:
        """Les parts somment exactement au total. C'est la propriété qui
        définit Shapley, et le contrôle le moins cher d'une erreur."""
        self.assertTrue(self.d.exhaustive)
        self.assertAlmostEqual(sum(s.value for s in self.d.shares),
                               self.d.total, places=12)

    def test_fractions_somment_a_un(self) -> None:
        self.assertAlmostEqual(sum(s.fraction for s in self.d.shares),
                               1.0, places=9)

    def test_un_levier_par_cle(self) -> None:
        self.assertEqual(tuple(s.key for s in self.d.shares), KEYS)

    def test_total_est_bien_lecart_a_la_regle(self) -> None:
        self.assertAlmostEqual(self.d.total,
                               self.d.realised - self.d.baseline, places=12)


class TestVeriteRetrouvee(unittest.TestCase):
    """L'avantage planté est attribué au bon levier."""

    def test_clairvoyance_dentree_attribuee_a_lentree(self) -> None:
        d = decompose(synthesise(skill=FORTE, n_sessions=SESSIONS))
        self.assertEqual(d.carrier.key, "entree")
        part = next(s for s in d.shares if s.key == "entree")
        self.assertGreater(part.fraction, 0.60)

    def test_clairvoyance_de_taille_attribuee_a_la_taille(self) -> None:
        d = decompose(synthesise(skill=0.0, size_skill=FORTE,
                                 n_sessions=SESSIONS))
        self.assertEqual(d.carrier.key, "taille")
        part = next(s for s in d.shares if s.key == "taille")
        self.assertGreater(part.fraction, 0.60)

    def test_les_deux_se_partagent(self) -> None:
        d = decompose(synthesise(skill=FORTE, size_skill=FORTE,
                                 n_sessions=SESSIONS))
        parts = {s.key: s.fraction for s in d.shares}
        self.assertGreater(parts["entree"], 0.20)
        self.assertGreater(parts["taille"], 0.20)

    def test_la_sortie_est_nulle_faute_de_gestion(self) -> None:
        """Le journal synthétique ne gère aucune sortie. La part doit être
        exactement zéro — c'est la vérité, pas une approximation, et il
        importe que la décomposition le dise au lieu de bruiter."""
        d = decompose(synthesise(skill=FORTE, n_sessions=SESSIONS))
        part = next(s for s in d.shares if s.key == "sortie")
        self.assertEqual(part.value, 0.0)

    def test_sans_clairvoyance_aucun_levier_ne_domine(self) -> None:
        """Sans compétence, le total est proche de zéro et aucune part ne
        peut être déclarée porteuse d'un avantage."""
        d = decompose(synthesise(skill=0.0, n_sessions=SESSIONS))
        self.assertLess(abs(d.total), 0.10)


class TestCoalitions(unittest.TestCase):
    """Les contrefactuels sont ceux que le tableau annonce."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.j = synthesise(skill=FORTE, n_sessions=SESSIONS)

    def test_coalition_vide_est_la_regle_scellee(self) -> None:
        """Tous leviers fermés, on prend tout à une unité : c'est exactement
        l'espérance de la règle sur l'univers entier."""
        v = coalition_value(self.j, frozenset())
        mecanique = sum(d.net_r for d in self.j.decisions
                        if d.net_r is not None) / self.j.n_eligible
        self.assertAlmostEqual(v, mecanique, places=9)

    def test_coalition_pleine_est_loperateur(self) -> None:
        v = coalition_value(self.j, frozenset(KEYS))
        realise = sum(d.weighted_r for d in self.j.decisions) / self.j.n_eligible
        self.assertAlmostEqual(v, realise, places=9)

    def test_deterministe(self) -> None:
        a = decompose(self.j)
        b = decompose(self.j)
        self.assertEqual([s.value for s in a.shares],
                         [s.value for s in b.shares])


class TestGardes(unittest.TestCase):

    def test_journal_vide_refuse(self) -> None:
        with self.assertRaises(ValueError):
            decompose(Journal(decisions=(), levers=KEYS))


if __name__ == "__main__":
    unittest.main()
