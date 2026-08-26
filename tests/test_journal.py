"""Le journal de décision, et la vérité qu'on y plante."""

from __future__ import annotations

import math
import unittest

from alp1.journal import (
    CONVICTION_MAX,
    CONVICTION_MIN,
    LEVERS,
    Decision,
    Journal,
    audit,
    planted_bits,
    synthesise,
    universe,
)

#: Assez de séances pour que le signe de l'espérance mécanique soit stable.
#: En dessous de ~400, le bruit d'échantillonnage domine et le signe bascule —
#: ce n'est pas un défaut du générateur mais le sujet même du papier, et
#: `TestBruitDeLInstrument` le garde explicitement.
SESSIONS = 400


class TestUnivers(unittest.TestCase):
    """L'univers des setups pose la vérité de référence."""

    def test_univers_non_vide(self) -> None:
        u = universe(SESSIONS)
        self.assertGreater(len(u), 30)

    def test_univers_deterministe(self) -> None:
        a = universe(SESSIONS)
        b = universe(SESSIONS)
        self.assertEqual([t.net_r for t in a], [t.net_r for t in b])

    def test_esperance_mecanique_negative(self) -> None:
        """Sans dérive, la règle scellée perd la friction, et rien d'autre.

        C'est le théorème d'arrêt optionnel : E[R] = µ·E[τ] − c, avec µ = 0.
        Si ce contrôle tombe, ce n'est pas l'opérateur qu'il faut regarder
        mais le générateur de prix.
        """
        u = universe(SESSIONS)
        mean = sum(t.net_r for t in u) / len(u)
        self.assertLess(mean, 0.0)

    def test_esperance_mecanique_jamais_significativement_positive(self) -> None:
        """Le contrôle qui tient à toute taille d'échantillon.

        Le signe de l'espérance n'est stable qu'au-delà de quelques centaines
        de séances ; ce qui est garanti partout, c'est qu'aucune dérive
        positive ne peut être *démontrée*, puisqu'il n'y en a pas.
        """
        for n in (200, SESSIONS):
            r = [t.net_r for t in universe(n)]
            m = sum(r) / len(r)
            sd = math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1))
            t_stat = m / (sd / math.sqrt(len(r)))
            self.assertLess(t_stat, 2.0, f"{n} séances : t = {t_stat:+.2f}")

    def test_refuse_zero_seance(self) -> None:
        with self.assertRaises(ValueError):
            universe(0)


class TestVeritePlantee(unittest.TestCase):
    """`planted_bits` est la vérité connue que l'appareil doit retrouver."""

    def test_sans_clairvoyance_aucun_bit(self) -> None:
        self.assertAlmostEqual(planted_bits(0.0, 0.5, 0.42), 0.0, places=12)

    def test_croissante_en_clairvoyance(self) -> None:
        bits = [planted_bits(s, 0.5, 0.42)
                for s in (0.0, 0.1, 0.2, 0.4, 0.8)]
        for a, b in zip(bits, bits[1:]):
            self.assertLess(a, b)

    def test_bornee_par_un_bit(self) -> None:
        """L'information d'une décision binaire sur une issue binaire ne peut
        pas dépasser un bit."""
        self.assertLessEqual(planted_bits(1.0, 0.5, 0.5), 1.0 + 1e-9)

    def test_refuse_clairvoyance_hors_bornes(self) -> None:
        for bad in (-0.1, 1.1):
            with self.assertRaises(ValueError):
                planted_bits(bad, 0.5, 0.5)


class TestSynthese(unittest.TestCase):
    """Le journal synthétique se comporte comme l'opérateur qu'il imite."""

    def test_leviers_par_defaut(self) -> None:
        j = synthesise(n_sessions=SESSIONS)
        self.assertEqual(j.levers, tuple(k for k, _ in LEVERS))
        self.assertEqual(j.budget, 16.0)

    def test_budget_suit_les_leviers(self) -> None:
        """k leviers valent 2^k configurations — l'algèbre de `discipline`."""
        for k in range(5):
            j = synthesise(n_sessions=SESSIONS,
                           levers=tuple(f"l{i}" for i in range(k)))
            self.assertEqual(j.budget, 2.0 ** k)

    def test_abstentions_presentes(self) -> None:
        j = synthesise(n_sessions=SESSIONS)
        self.assertGreater(len(j.skipped), 0)
        self.assertGreater(len(j.taken), 0)
        self.assertEqual(j.n_eligible, len(j.taken) + len(j.skipped))

    def test_taux_de_prise_stable_en_clairvoyance(self) -> None:
        """La paramétrisation tient la cadence constante : sans quoi on ne
        saurait pas démêler la compétence de la simple sélectivité."""
        taux = [synthesise(skill=s, n_sessions=SESSIONS).take_rate
                for s in (0.0, 0.3, 0.6)]
        self.assertLess(max(taux) - min(taux), 0.12)

    def test_esperance_croit_avec_la_clairvoyance(self) -> None:
        means = [synthesise(skill=s, n_sessions=SESSIONS).mean_r
                 for s in (0.0, 0.25, 0.50)]
        for a, b in zip(means, means[1:]):
            self.assertLess(a, b)

    def test_sans_clairvoyance_aucun_avantage_demontrable(self) -> None:
        """Sans information, aucune sélection ne rachète la friction.

        L'énoncé testable n'est pas « l'espérance est négative » — à quelques
        centaines de décisions ce signe n'est pas garanti — mais « aucune
        espérance positive n'est démontrable ». C'est la forme qui tient, et
        c'est aussi la seule que le papier a le droit d'affirmer.
        """
        j = synthesise(skill=0.0, n_sessions=SESSIONS)
        se = j.sd_r / math.sqrt(j.n_taken)
        self.assertLess(j.mean_r / se, 2.0)

    def test_deterministe(self) -> None:
        a = synthesise(skill=0.3, n_sessions=SESSIONS)
        b = synthesise(skill=0.3, n_sessions=SESSIONS)
        self.assertEqual([d.taken for d in a.decisions],
                         [d.taken for d in b.decisions])

    def test_abstention_ne_rapporte_rien(self) -> None:
        j = synthesise(skill=0.4, n_sessions=SESSIONS)
        for d in j.skipped:
            self.assertEqual(d.weighted_r, 0.0)
            self.assertEqual(d.direction, 0)
            self.assertEqual(d.size, 0.0)

    def test_contingence_complete(self) -> None:
        j = synthesise(skill=0.3, n_sessions=SESSIONS)
        table = j.contingency()
        self.assertEqual(sum(sum(r) for r in table), j.n_eligible)
        for row in table:
            for cell in row:
                self.assertGreater(cell, 0)

    def test_conviction_dans_les_bornes(self) -> None:
        j = synthesise(skill=0.3, size_skill=0.5, n_sessions=SESSIONS)
        for d in j.decisions:
            self.assertGreaterEqual(d.conviction, CONVICTION_MIN)
            self.assertLessEqual(d.conviction, CONVICTION_MAX)

    def test_refuse_parametres_hors_bornes(self) -> None:
        with self.assertRaises(ValueError):
            synthesise(skill=1.5, n_sessions=SESSIONS)
        with self.assertRaises(ValueError):
            synthesise(size_skill=-0.1, n_sessions=SESSIONS)
        with self.assertRaises(ValueError):
            synthesise(timing_noise=-1, n_sessions=SESSIONS)


class TestBruitDeLInstrument(unittest.TestCase):
    """Le corollaire central du dépôt, appliqué au journal.

    Le bruit propre de la mesure dépasse l'effet qu'elle doit établir. Ce
    n'est pas une faiblesse du dispositif : c'est le résultat que le papier
    publie, et il mérite d'être gardé comme tel.
    """

    def test_le_bruit_domine_la_cible(self) -> None:
        """Même à plusieurs milliers de décisions, l'espérance mécanique
        reste à moins de deux erreurs types de zéro : l'instrument ne résout
        pas la valeur qu'il vise, à savoir −c/L."""
        r = [t.net_r for t in universe(1600)]
        m = sum(r) / len(r)
        sd = math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1))
        self.assertLess(abs(m / (sd / math.sqrt(len(r)))), 2.0)

    def test_le_signe_bascule_en_petit_echantillon(self) -> None:
        """À 200 séances le signe de l'espérance n'est pas fiable, à 800 il
        l'est. Ce contraste est la justification de tout le chapitre sur le
        mur d'échantillon."""
        petit = [t.net_r for t in universe(200)]
        grand = [t.net_r for t in universe(800)]
        self.assertGreater(sum(petit) / len(petit), 0.0)
        self.assertLess(sum(grand) / len(grand), 0.0)


class TestAudit(unittest.TestCase):
    """L'audit refuse un registre avant qu'on ne le mesure."""

    def _decision(self, **kw) -> Decision:
        base = dict(seq=0, day="2026-01-05", minute=120, taken=True,
                    direction=1, size=1.0, conviction=3, offset_min=0,
                    managed=False, net_r=0.5, win=True)
        base.update(kw)
        return Decision(**base)

    def test_journal_vide(self) -> None:
        j = Journal(decisions=(), levers=("entree",))
        self.assertEqual(audit(j), ["journal vide"])

    def test_sans_abstention(self) -> None:
        j = Journal(decisions=(self._decision(),), levers=("entree",))
        self.assertTrue(any("abstention" in f for f in audit(j)))

    def test_direction_sur_abstention(self) -> None:
        """Une abstention qui porte une direction a été remplie après coup."""
        j = Journal(decisions=(self._decision(),
                               self._decision(seq=1, taken=False,
                                              direction=-1, size=0.0)),
                    levers=("entree",))
        self.assertTrue(any("direction" in f for f in audit(j)))

    def test_rangs_dupliques(self) -> None:
        j = Journal(decisions=(self._decision(),
                               self._decision(taken=False, direction=0,
                                              size=0.0)),
                    levers=("entree",))
        self.assertTrue(any("dupliqu" in f for f in audit(j)))

    def test_journal_synthetique_sain(self) -> None:
        """Le seul défaut admis est la conviction constante, qui découle de
        l'absence de compétence de dimensionnement plantée."""
        j = synthesise(skill=0.3, size_skill=0.4, n_sessions=SESSIONS)
        self.assertEqual(audit(j), [])


if __name__ == "__main__":
    unittest.main()
