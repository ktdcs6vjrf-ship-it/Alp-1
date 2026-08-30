"""Le régime de gamma déplace l'horloge, et rien d'autre.

Trois faits publiés, trois familles de tests. La colonne constante est le
plus important : elle porte le théorème d'arrêt optionnel appliqué à une
couche que la vulgarisation lit comme directionnelle.
"""

from __future__ import annotations

import unittest

from alp1 import horloge as H
from alp1 import seuil
from alp1.report11 import DERIVE_TRAVAIL


class TestColonneConstante(unittest.TestCase):
    """La probabilité de touche ne dépend pas du régime — sous condition.

    La première version de ces tests exigeait l'invariance partout, et quatre
    d'entre eux ont refusé. Ils avaient raison : le théorème porte sur le
    problème **non borné**, et une séance finit. La troisième issue —  sortir
    à la clôture sans avoir touché de barrière — dépend, elle, du régime.
    """

    def test_la_probabilite_de_target_est_la_meme_a_tout_regime(self):
        """À la géométrie déclarée, où la séance ne borne rien."""
        attendu = 1.0 / (1.0 + H.RR)
        for h in (0.46, 0.50, 0.55, 0.60, 0.6489, 0.70, 0.74):
            with self.subTest(hurst=h):
                self.assertAlmostEqual(H.regime(h).p_target, attendu, places=4)

    def test_c_est_la_sortie_a_la_cloture_qui_porte_la_condition(self):
        """Elle est négligeable à la géométrie déclarée, et c'est pourquoi.

        Le stop fait six dixièmes de point : les barrières se résolvent en
        quelques minutes et presque aucun trade n'atteint la clôture. Le test
        chiffre ce « presque » plutôt que de le supposer.
        """
        for h in (0.46, 0.50, 0.6489, 0.70):
            with self.subTest(hurst=h):
                self.assertLess(H.regime(h).p_open, 1e-3)

    def test_a_stop_elargi_le_regime_deplace_la_probabilite_de_touche(self):
        """Et c'est le fait que la première version du module manquait.

        Le régime n'a pas cessé de n'agir que sur l'horloge ; c'est l'horloge
        qui décide désormais si la séance est assez longue pour atteindre le
        target. À 0,050 % de stop, un huitième des trades atteint la clôture
        en chop, et la probabilité de target passe d'un facteur vingt au
        moins entre les deux régimes extrêmes du module.
        """
        chop = H.regime(min(H.EXPOSANTS), 0.050)
        trend = H.regime(max(H.EXPOSANTS), 0.050)
        self.assertGreater(chop.p_open, 0.05)
        self.assertLess(trend.p_open, 1e-3)
        self.assertGreater(trend.p_target, 20.0 * chop.p_target)
        self.assertAlmostEqual(trend.p_target, 1.0 / (1.0 + H.RR), places=4)

    def test_les_trois_issues_somment_a_un(self):
        """Contrôle de cohérence : rien ne se perd entre les trois sorties."""
        from alp1.costs import stop_points
        from alp1.horizon import outcome_scaled
        from alp1 import quant as q
        for pct in (0.010, 0.050):
            for h in (0.46, 0.70):
                a = stop_points(q.INDEX_LEVEL, pct)
                o = outcome_scaled(a, H.RR * a, H.SESSION_MIN, H.SIGMA_1MIN, h)
                with self.subTest(stop=pct, hurst=h):
                    self.assertAlmostEqual(
                        o.p_target + o.p_stop + o.p_open, 1.0, places=9)


class TestHorloge(unittest.TestCase):
    """Ce que le régime déplace : le temps, donc le seuil."""

    def test_le_temps_decroit_quand_l_exposant_croit(self):
        temps = [H.regime(h).exposition for h in sorted(H.EXPOSANTS)]
        self.assertEqual(temps, sorted(temps, reverse=True))
        self.assertGreater(temps[0] / temps[-1], 2.0)

    def test_le_seuil_est_la_friction_sur_le_temps(self):
        """`µ* = 60c/E[τ∧T]` : la table doit être cette division, pas une autre."""
        for h in H.EXPOSANTS:
            r = H.regime(h)
            with self.subTest(hurst=h):
                self.assertAlmostEqual(r.seuil * r.exposition,
                                       60.0 * H.friction(), places=9)

    def test_l_inversion_le_jour_de_tendance_a_la_pire_esperance(self):
        """Le résultat que la lecture courante manque, réduit à une inégalité."""
        chop = H.regime(min(H.EXPOSANTS))
        trend = H.regime(max(H.EXPOSANTS))
        self.assertLess(trend.esperance, chop.esperance)

    def test_aucun_regime_ne_rentre_dans_le_plausible_a_la_geometrie_declaree(self):
        plafond = seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]
        for h in H.EXPOSANTS:
            with self.subTest(hurst=h):
                self.assertGreater(H.regime(h).seuil, plafond)

    def test_le_gamma_implique_change_de_signe_au_demi(self):
        """Gamma long en deçà d'un demi, gamma court au-delà."""
        self.assertGreater(H.regime(0.46).gex_implique, 0.0)
        self.assertLess(H.regime(0.60).gex_implique, 0.0)


class TestFenetre(unittest.TestCase):
    """La bande où la lecture du régime change une décision."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.bas, cls.haut = H.fenetre()

    def test_la_bande_est_bornee_et_etroite(self):
        self.assertLess(self.bas, self.haut)
        self.assertLess(self.haut / self.bas, 4.0)

    def test_la_geometrie_declaree_tombe_sous_la_bande(self):
        """Le régime n'y décide rien, parce que rien n'y est à décider."""
        self.assertLess(0.010, self.bas)
        self.assertEqual(H.verdict(0.010), "perdue à tout régime")

    def test_les_trois_etats_se_suivent_dans_l_ordre(self):
        self.assertEqual(H.verdict(0.5 * self.bas), "perdue à tout régime")
        self.assertTrue(H.verdict(0.5 * (self.bas + self.haut)).startswith("**"))
        self.assertEqual(H.verdict(2.0 * self.haut), "gagnée à tout régime")

    def test_dans_la_bande_les_deux_extremes_encadrent_la_derive(self):
        milieu = 0.5 * (self.bas + self.haut)
        self.assertLessEqual(H.seuil_par_stop(milieu, min(H.EXPOSANTS)),
                             DERIVE_TRAVAIL)
        self.assertGreater(H.seuil_par_stop(milieu, max(H.EXPOSANTS)),
                           DERIVE_TRAVAIL)


class TestTables(unittest.TestCase):
    def test_les_deux_tables_sont_exposees(self):
        self.assertEqual(set(H.all_tables()), {"horloge", "fenetre_gamma"})

    def test_chaque_ligne_a_le_bon_nombre_de_cases(self):
        for t in H.all_tables().values():
            for row in t.rows:
                with self.subTest(table=t.key):
                    self.assertEqual(len(row), len(t.headers))

    def test_les_valeurs_citees_existent(self):
        v = H.values()
        for cle in ("g_p_target", "g_facteur", "g_mu_chop", "g_mu_trend",
                    "g_er_chop", "g_er_trend", "g_fenetre_bas",
                    "g_fenetre_haut"):
            self.assertIn(cle, v)


if __name__ == "__main__":
    unittest.main(verbosity=2)
