"""Le seuil de rentabilité, et la circularité qu’il remplace.

Ces tests gardent deux choses distinctes. D'abord que le module dit vrai :
loi nulle, identité de Wald, optimum intérieur. Ensuite, et c'est le plus
important, que le défaut qu'il corrige ne revienne pas en silence — la dérive
de référence du document nº 1 est définie à partir de la friction, donc
suppose l'avantage qu'elle sert à évaluer.
"""

from __future__ import annotations

import unittest

from alp1 import quant as q, seuil
from alp1.costs import COST_BASE, COST_OPTIMISTIC, COST_REALISTIC, MES


class TestLoiNulle(unittest.TestCase):
    """Sans dérive, aucune géométrie ne crée d'espérance."""

    def test_toute_geometrie_est_negative_a_derive_nulle(self) -> None:
        """C'est le théorème d'arrêt optionnel, et il reste vrai ici.

        Le module ne prétend pas fabriquer un avantage à partir de rien. Si
        ce test tombait, c'est que le calcul aurait cessé de payer la friction
        quelque part.
        """
        for g in seuil.scan():
            with self.subTest(stop=g.stop_pct):
                self.assertLess(g.expectancy_r(0.0), 0.0)

    def test_l_esperance_vaut_exactement_moins_c_sur_L(self) -> None:
        for g in seuil.scan():
            with self.subTest(stop=g.stop_pct):
                self.assertAlmostEqual(g.expectancy_r(0.0), -g.friction_ratio,
                                       places=12)


class TestWald(unittest.TestCase):
    """L'identité qui porte tout le module."""

    def test_esperance_et_seuil_sont_coherents(self) -> None:
        """À `µ = µ*`, l'espérance est exactement nulle : c'est la définition."""
        for g in seuil.scan():
            with self.subTest(stop=g.stop_pct):
                self.assertAlmostEqual(
                    g.expectancy_r(g.break_even_per_hour), 0.0, places=10)

    def test_l_esperance_croit_avec_la_derive(self) -> None:
        for g in seuil.scan():
            with self.subTest(stop=g.stop_pct):
                self.assertLess(g.expectancy_r(1.0), g.expectancy_r(2.0))


class TestSeuil(unittest.TestCase):
    """Ce que la géométrie fait au seuil à franchir."""

    def test_le_seuil_decroit_quand_le_stop_s_elargit(self) -> None:
        """`µ* = c/E[τ]`, et `E[τ]` croît comme `a²` : la décroissance est
        quadratique, et c'est ce qui rend le levier si puissant."""
        seuils = [g.break_even_per_hour for g in seuil.scan()]
        for avant, apres in zip(seuils, seuils[1:]):
            self.assertLess(apres, avant)

    def test_la_geometrie_declaree_est_hors_domaine(self) -> None:
        """Au stop déclaré, la rentabilité est arithmétiquement impossible.

        Ce n'est pas un jugement sur le signal : quelle que soit la dérive
        réelle, si elle reste dans le domaine que le document appelle
        plausible, elle ne franchit pas ce seuil.
        """
        g = seuil.geometry(0.010)
        self.assertFalse(g.reachable)
        self.assertGreater(g.break_even_per_hour,
                           seuil.PLAUSIBLE_DRIFT_PER_HOUR[1])

    def test_l_optimum_est_interieur(self) -> None:
        """Ni le plus serré ni le plus large : les deux forces se croisent.

        Trop serré, la friction domine ; trop large, l'exposition sature
        contre la séance pendant que le risque nominal continue de croître.
        """
        grille = seuil.STOP_GRID_PCT
        meilleur = seuil.best(2.0)
        self.assertNotEqual(meilleur.stop_pct, grille[0])
        self.assertNotEqual(meilleur.stop_pct, grille[-1])

    def test_l_optimum_est_atteignable(self) -> None:
        self.assertTrue(seuil.best(2.0).reachable)

    def test_le_pire_et_le_meilleur_choix_sont_separes_d_un_ordre(self) -> None:
        """L'écart entre le pire et le meilleur choix de géométrie, de contrat
        et d'exécution dépasse deux ordres de grandeur sur le seuil."""
        pire = seuil.geometry(0.010, COST_REALISTIC, MES).break_even_per_hour
        meilleur = seuil.geometry(0.150, COST_OPTIMISTIC).break_even_per_hour
        self.assertGreater(pire / meilleur, 100.0)


class TestCircularite(unittest.TestCase):
    """Le défaut que ce module remplace, et qui ne doit pas revenir.

    `quant.reference_drift()` vaut `DRIFT_MULTIPLE × c / E[τ]`. La dérive y
    est dérivée de la friction, donc l'avantage est supposé et non mesuré.
    Ces deux tests inscrivent le fait dans la suite pour qu'il soit visible.
    """

    def test_la_derive_de_reference_est_definie_par_la_friction(self) -> None:
        attendu = (q.DRIFT_MULTIPLE * q.FRICTION
                   / q.geometry(q.RR_REF).expected_time)
        self.assertAlmostEqual(q.reference_drift(), attendu, places=12)

    def test_la_derive_de_reference_sort_du_domaine_plausible(self) -> None:
        """Elle vaut plusieurs fois la borne haute que le document déclare.

        Tant que ce test passe, les chapitres qui tournent « sous la dérive de
        référence » tournent sous une dérive que le document juge lui-même
        invraisemblable, et leurs conclusions doivent se lire ainsi.
        """
        haut = seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]
        self.assertGreater(q.reference_drift() * 60.0, 4.0 * haut)

    def test_le_module_ne_derive_jamais_sa_derive_de_la_friction(self) -> None:
        """La dérive est un paramètre déclaré, jamais calculé depuis `c`.

        Deux frictions différentes doivent donner deux seuils différents mais
        la même dérive — sans quoi la circularité serait reconduite ici.
        """
        a = seuil.geometry(0.100, COST_BASE)
        b = seuil.geometry(0.100, COST_OPTIMISTIC)
        self.assertNotAlmostEqual(a.break_even_per_hour, b.break_even_per_hour)
        self.assertAlmostEqual(a.expectancy_r(2.0) - b.expectancy_r(2.0),
                               (b.friction_points - a.friction_points)
                               / a.stop_points, places=12)


if __name__ == "__main__":
    unittest.main()
