"""Les cinq lois nulles, et la calibration de l'appareil.

Le contrôle qui compte n'est pas qu'un opérateur compétent soit détecté —
n'importe quelle statistique complaisante y arrive. C'est qu'un opérateur
**sans** compétence ne le soit pas. Un appareil qui ne sait pas dire non ne
mesure rien.
"""

from __future__ import annotations

import unittest

from alp1.journal import Journal, synthesise
from alp1.operator import (
    evaluate,
    null_abstention,
    null_bootstrap,
    null_mechanical,
    null_selection,
    null_timing,
)

SESSIONS = 400
DRAWS = 200

#: Clairvoyance largement au-dessus du mur : l'appareil doit conclure.
FORTE = 0.55
#: Clairvoyance nulle : l'appareil ne doit rien conclure.
NULLE = 0.0


class TestNiveau(unittest.TestCase):
    """Sans compétence plantée, aucune loi ne doit être battue."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.journal = synthesise(skill=NULLE, n_sessions=SESSIONS)
        cls.verdict = evaluate(cls.journal, draws=DRAWS)

    def test_aucun_avantage_declare(self) -> None:
        self.assertFalse(self.verdict.accepted)

    def test_refus_documente(self) -> None:
        self.assertIn("refusé", self.verdict.summary)

    def test_aucune_loi_battue(self) -> None:
        battues = [t.key for t in self.verdict.beaten]
        self.assertEqual(battues, [], f"lois battues à tort : {battues}")

    def test_information_dabstention_nulle(self) -> None:
        """Sans clairvoyance, la décision et l'issue sont indépendantes.

        La correction de Miller-Madow est ce qui rend ce contrôle possible :
        sans elle l'information mutuelle empirique est positive en espérance
        même sous indépendance, et le test déclarerait une compétence à tout
        coup.
        """
        test = null_abstention(self.journal)
        self.assertTrue(test.applicable)
        self.assertFalse(test.beats)


class TestPuissance(unittest.TestCase):
    """Avec une compétence franche, les cinq lois doivent tomber."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.journal = synthesise(skill=FORTE, n_sessions=SESSIONS)
        cls.verdict = evaluate(cls.journal, draws=DRAWS)

    def test_avantage_declare(self) -> None:
        self.assertTrue(self.verdict.accepted, self.verdict.summary)

    def test_toutes_les_lois_battues(self) -> None:
        restantes = [t.key for t in self.verdict.survived]
        self.assertEqual(restantes, [], f"lois non battues : {restantes}")

    def test_seuil_deflate_franchi(self) -> None:
        self.assertTrue(self.verdict.clears_deflation)

    def test_chaque_loi_applicable(self) -> None:
        for t in self.verdict.tests:
            self.assertTrue(t.applicable, f"{t.key} sans objet : {t.note}")


class TestMonotonie(unittest.TestCase):
    """Le nombre de lois battues croît avec la compétence plantée."""

    def test_croissance(self) -> None:
        battues = []
        for skill in (0.0, 0.25, 0.55):
            v = evaluate(synthesise(skill=skill, n_sessions=SESSIONS),
                         draws=DRAWS)
            battues.append(len(v.beaten))
        for a, b in zip(battues, battues[1:]):
            self.assertLessEqual(a, b, f"non monotone : {battues}")
        self.assertEqual(battues[0], 0)
        self.assertEqual(battues[-1], 5)


class TestTaxeDeMultiplicite(unittest.TestCase):
    """Le jugement se paie avant de rapporter."""

    def test_seuil_croit_avec_les_leviers(self) -> None:
        """Chaque levier double la famille de stratégies, donc relève le
        seuil déflaté. C'est l'algèbre de `discipline`, appliquée à
        l'opérateur."""
        seuils = []
        for k in (1, 2, 4, 6):
            j = synthesise(skill=0.3, n_sessions=SESSIONS,
                           levers=tuple(f"l{i}" for i in range(k)))
            seuils.append(evaluate(j, draws=20).threshold)
        for a, b in zip(seuils, seuils[1:]):
            self.assertLess(a, b, f"seuils non croissants : {seuils}")

    def test_quatre_leviers_valent_seize_configurations(self) -> None:
        v = evaluate(synthesise(skill=0.3, n_sessions=SESSIONS), draws=20)
        self.assertEqual(v.budget, 16.0)


class TestLoisSansObjet(unittest.TestCase):
    """Une loi intestable est comptée comme non battue, jamais comme réussie."""

    def _vide(self) -> Journal:
        return Journal(decisions=(), levers=("entree",))

    def test_journal_vide_toutes_sans_objet(self) -> None:
        j = self._vide()
        for fn in (null_selection, null_timing, null_bootstrap):
            t = fn(j, draws=10)
            self.assertFalse(t.applicable)
            self.assertFalse(t.beats)
        for t in (null_mechanical(j), null_abstention(j, draws=10)):
            self.assertFalse(t.applicable)
            self.assertFalse(t.beats)

    def test_sans_abstention_labstention_est_intestable(self) -> None:
        """Le point qui justifie d'exiger les refus dans le journal : sans
        eux, la moitié de la table de contingence est vide et la compétence
        d'abstention n'est pas identifiable."""
        plein = synthesise(skill=0.4, n_sessions=SESSIONS)
        tout_pris = Journal(
            decisions=tuple(d for d in plein.decisions if d.taken),
            levers=plein.levers)
        t = null_abstention(tout_pris, draws=10)
        self.assertFalse(t.applicable)
        self.assertIn("contingence", t.note)

    def test_lecture_mentionne_sans_objet(self) -> None:
        t = null_selection(self._vide(), draws=10)
        self.assertIn("sans objet", t.reading)


class TestDeterminisme(unittest.TestCase):
    """Même graine, même verdict — sur toute machine et à toute date."""

    def test_verdict_reproductible(self) -> None:
        j = synthesise(skill=0.3, n_sessions=SESSIONS)
        a = evaluate(j, draws=DRAWS)
        b = evaluate(j, draws=DRAWS)
        self.assertEqual([t.observed for t in a.tests],
                         [t.observed for t in b.tests])
        self.assertEqual([t.q95 for t in a.tests],
                         [t.q95 for t in b.tests])


if __name__ == "__main__":
    unittest.main()
