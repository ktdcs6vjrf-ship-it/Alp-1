"""Tests de l'encadrement par remplissage du stop.

Des barres d'une minute ne disent pas à quel prix un stop touché à l'intérieur
d'une barre a été exécuté. Le protocole retient le niveau du stop ; l'extrême
de la barre est le pire compatible avec ce qu'on observe. Ces tests vérifient
que les deux règles sont bien celles annoncées, que l'encadrement va dans le
sens qu'il doit, et que le verdict d'indécision se déclenche quand le seuil
tombe entre les bornes.

Le fait que ces tests établissent — l'écart entre les deux remplissages est du
même ordre que la friction elle-même — est la raison d'être du module : il
interdit de publier la borne optimiste seule comme si c'était une mesure.
"""

from __future__ import annotations

import unittest

from alp1.dataset import Bar, Session, synthetic_sessions
from alp1.measure import Bounds, bounds, measure, scan_session


def _session(day: str, bars: list[tuple[int, float, float, float, float]]):
    return Session(day, tuple(Bar(day, m, o, h, l, c, 0.0)
                              for m, o, h, l, c in bars))


class TestRemplissage(unittest.TestCase):
    def test_une_valeur_inconnue_est_refusee(self):
        s = synthetic_sessions(3, seed=1)[0]
        for mauvais in ("worst", "", "STOP", "extrême"):
            with self.subTest(fill=mauvais):
                with self.assertRaises(ValueError):
                    scan_session(s, 3.0, 90, 0.33, fill=mauvais)

    def test_le_pire_cas_sort_au_plus_bas_de_la_barre_a_l_achat(self):
        """Une barre à longue mèche basse doit remplir au bas, pas au stop."""
        bars = [(m, 6000.0, 6000.5, 5999.5, 6000.0) for m in range(95)]
        bars.append((95, 6000.0, 6040.0, 6000.0, 6040.0))       # cassure haussière
        for m in range(96, 120):
            bars.append((m, 6040.0, 6041.0, 6039.0, 6040.0))
        bars.append((120, 6040.0, 6040.0, 5900.0, 6035.0))      # mèche basse
        for m in range(121, 390):
            bars.append((m, 6035.0, 6036.0, 6034.0, 6035.0))
        s = _session("j", bars)

        opt = scan_session(s, 3.0, 90, 0.0, fill="stop")
        bad = scan_session(s, 3.0, 90, 0.0, fill="extreme")
        self.assertTrue(opt and bad, "la règle doit se déclencher")
        self.assertTrue(opt[0].stopped and bad[0].stopped)
        self.assertGreater(opt[0].exit_price, bad[0].exit_price)
        self.assertAlmostEqual(bad[0].exit_price, 5900.0, places=6)

    def test_les_deux_remplissages_donnent_les_memes_trades(self):
        """Seul le prix de sortie change ; la règle, elle, ne bouge pas."""
        sess = synthetic_sessions(120, seed=20260821)
        opt = measure(sess, fill="stop")
        bad = measure(sess, fill="extreme")
        self.assertEqual(opt.n_trades, bad.n_trades)
        self.assertEqual(opt.stop_rate, bad.stop_rate)
        for a, b in zip(opt.trades, bad.trades):
            with self.subTest(jour=a.day, entree=a.entry_minute):
                self.assertEqual(a.direction, b.direction)
                self.assertEqual(a.entry_minute, b.entry_minute)
                self.assertEqual(a.exit_minute, b.exit_minute)
                self.assertEqual(a.stopped, b.stopped)


class TestEncadrement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sessions = synthetic_sessions(250, seed=20260821)
        cls.b = bounds(cls.sessions)

    def test_le_pire_cas_n_est_jamais_meilleur(self):
        self.assertLessEqual(self.b.worst.mean_net, self.b.optimistic.mean_net)
        self.assertGreaterEqual(self.b.spread_points, 0.0)

    def test_l_ecart_est_du_meme_ordre_que_la_friction(self):
        """Le fait qui interdit de publier la borne optimiste seule.

        L'écart entre les deux remplissages n'est pas un raffinement de
        second ordre : il pèse autant que la friction elle-même, c'est-à-dire
        autant que la grandeur que la mesure cherche à franchir.
        """
        self.assertGreater(self.b.spread_points,
                           0.5 * self.b.optimistic.friction_used)

    def test_le_seuil_par_defaut_est_zero(self):
        """`net_points` retranche déjà la friction : la compter deux fois
        serait la placer des deux côtés de l'inégalité."""
        self.assertEqual(self.b.threshold, 0.0)
        explicite = bounds(self.sessions, threshold=1.5)
        self.assertEqual(explicite.threshold, 1.5)

    def test_verdict_et_indecision_sont_exclusifs(self):
        self.assertEqual(self.b.conclusive, not self.b.straddles)
        self.assertIn("remplissages", self.b.verdict)

    def test_l_ecart_depasse_la_friction_sur_tous_les_tirages(self):
        """La partie **robuste** du résultat, et celle qui se généralise.

        L'écart entre les deux remplissages ne dépend pas du tirage : il vaut
        environ un point sur toutes les graines essayées, soit davantage que
        la friction que la mesure cherche à franchir. C'est ce fait, et non le
        renversement de signe qui l'accompagne parfois, qui interdit de
        publier la borne optimiste seule.
        """
        for seed in (20260821, 11, 4242):
            with self.subTest(graine=seed):
                b = bounds(synthetic_sessions(250, seed=seed))
                self.assertGreater(b.spread_points,
                                   b.optimistic.friction_used)

    def test_le_remplissage_seul_peut_renverser_le_signe(self):
        """La partie **illustrative**, vraie sur ce tirage, non sur tous.

        Sur la série que la documentation cite — 250 séances, graine par
        défaut —, l'espérance nette est positive sous le remplissage du
        protocole et négative sous le pire cas : le signe de la conclusion y
        est décidé par une hypothèse d'exécution que les barres ne tranchent
        pas. Sur d'autres tirages les deux bornes tombent du même côté ; ce
        qui se généralise est la largeur de la bande, pas le renversement.
        """
        self.assertGreater(self.b.optimistic.mean_net, 0.0)
        self.assertLess(self.b.worst.mean_net, 0.0)
        self.assertTrue(self.b.straddles)
        self.assertFalse(self.b.conclusive)

    def test_le_biais_du_remplissage_optimiste_est_positif(self):
        """Le stop est rempli exactement au stop, jamais plus bas ; rien ne
        tronque symétriquement le côté gagnant."""
        self.assertGreater(self.b.optimistic.mean_net, self.b.worst.mean_net)

    def test_un_seuil_entre_les_bornes_rend_la_mesure_indecise(self):
        milieu = (self.b.worst.mean_net + self.b.optimistic.mean_net) / 2.0
        b = Bounds(self.b.optimistic, self.b.worst, milieu)
        self.assertTrue(b.straddles)
        self.assertFalse(b.conclusive)
        self.assertIn("ne conclut pas", b.verdict)

    def test_un_seuil_sous_les_deux_bornes_est_franchi(self):
        bas = self.b.worst.mean_net - 1.0
        b = Bounds(self.b.optimistic, self.b.worst, bas)
        self.assertTrue(b.conclusive)
        self.assertIn("franchi sous les deux", b.verdict)

    def test_un_seuil_au_dessus_des_deux_bornes_n_est_pas_franchi(self):
        haut = self.b.optimistic.mean_net + 1.0
        b = Bounds(self.b.optimistic, self.b.worst, haut)
        self.assertTrue(b.conclusive)
        self.assertIn("non franchi sous les deux", b.verdict)


if __name__ == "__main__":
    unittest.main()
