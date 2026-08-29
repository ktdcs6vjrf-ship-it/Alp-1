"""Marchenko-Pastur, et la transition qui décide si un facteur se voit.

Ces tests gardent deux choses. D'abord que la forme fermée dit vrai : les
bords, la densité, la continuité de la transition. Ensuite, et c'est le point
que le document doit porter honnêtement, que le bord asymptotique `λ₊` est
**conservateur** à `k` fini — la plus grande valeur propre d'un spectre
simulé lui reste inférieure, et présenter `λ₊` comme une barrière atteinte
serait une exagération.
"""

from __future__ import annotations

import math
import unittest

from alp1 import spectrum as sp


class TestFormeFermee(unittest.TestCase):

    def test_les_bords_se_referment_quand_les_observations_abondent(self) -> None:
        """À γ → 0, toute valeur propre différente de un est réelle."""
        lo, hi = sp.mp_edges(1e-6)
        self.assertAlmostEqual(lo, 1.0, places=2)
        self.assertAlmostEqual(hi, 1.0, places=2)

    def test_a_gamma_un_le_bord_bas_touche_zero(self) -> None:
        lo, hi = sp.mp_edges(1.0)
        self.assertAlmostEqual(lo, 0.0, places=12)
        self.assertAlmostEqual(hi, 4.0, places=12)

    def test_les_bords_s_ecartent_avec_gamma(self) -> None:
        precedent = 1.0
        for g in (0.01, 0.05, 0.1, 0.3, 0.6):
            hi = sp.mp_edges(g)[1]
            self.assertGreater(hi, precedent)
            precedent = hi

    def test_la_densite_integre_a_un(self) -> None:
        """Contrôle numérique : la loi est une loi.

        L'intégrale est prise par la règle du point milieu sur quatre mille
        pas, ce qui suffit à trois décimales malgré les racines aux bords.
        """
        for g in (0.02, 0.1, 0.4):
            lo, hi = sp.mp_edges(g)
            pas = (hi - lo) / 4000.0
            total = sum(sp.mp_density(lo + (i + 0.5) * pas, g) * pas
                        for i in range(4000))
            self.assertAlmostEqual(total, 1.0, places=2)

    def test_la_densite_est_nulle_hors_des_bords(self) -> None:
        lo, hi = sp.mp_edges(0.1)
        self.assertEqual(sp.mp_density(lo - 0.01, 0.1), 0.0)
        self.assertEqual(sp.mp_density(hi + 0.01, 0.1), 0.0)


class TestTransition(unittest.TestCase):
    """Sous le seuil, le facteur ne sort pas du bruit — pas faiblement."""

    def test_la_valeur_propre_est_plate_sous_le_seuil(self) -> None:
        g = 7 / 250
        hi = sp.mp_edges(g)[1]
        seuil = sp.bbp_threshold(g)
        for s in (0.01, 0.05, 0.10, seuil * 0.999):
            self.assertAlmostEqual(sp.spiked_eigenvalue(s, g), hi, places=12)

    def test_la_transition_est_continue_au_seuil(self) -> None:
        """`(1+√γ)(1+√γ)` vaut exactement `λ₊` : la formule se recolle."""
        for g in (0.01, 0.05, 0.2, 0.5):
            seuil = sp.bbp_threshold(g)
            self.assertAlmostEqual(sp.spiked_eigenvalue(seuil, g),
                                   sp.mp_edges(g)[1], places=12)

    def test_elle_croit_strictement_au_dessus(self) -> None:
        g = 7 / 250
        seuil = sp.bbp_threshold(g)
        precedent = sp.mp_edges(g)[1]
        for s in (seuil * 1.2, 0.3, 0.5, 1.0):
            val = sp.spiked_eigenvalue(s, g)
            self.assertGreater(val, precedent)
            precedent = val

    def test_l_echantillon_requis_est_l_inverse_du_seuil(self) -> None:
        """À `N = k/s²`, le facteur est exactement au seuil, jamais au-dessus."""
        for k, s in ((7, 0.25), (20, 0.4), (4, 0.1)):
            n = sp.observations_for_spike(s, k)
            self.assertAlmostEqual(sp.bbp_threshold(k / n), s, places=12)

    def test_regarder_deux_fois_plus_coute_deux_fois_plus(self) -> None:
        """Et diviser la force par deux en coûte quatre fois plus.

        C'est tout le contenu opérationnel de la transition, et il ne dépend
        d'aucune propriété du marché.
        """
        self.assertAlmostEqual(sp.observations_for_spike(0.3, 14)
                               / sp.observations_for_spike(0.3, 7), 2.0,
                               places=12)
        self.assertAlmostEqual(sp.observations_for_spike(0.15, 7)
                               / sp.observations_for_spike(0.30, 7), 4.0,
                               places=12)


class TestSpectreEmpirique(unittest.TestCase):

    def test_jacobi_retrouve_des_valeurs_propres_connues(self) -> None:
        vals = sp._jacobi_eigenvalues([[2.0, 1.0], [1.0, 2.0]])
        self.assertAlmostEqual(vals[0], 1.0, places=10)
        self.assertAlmostEqual(vals[1], 3.0, places=10)

    def test_la_trace_est_conservee(self) -> None:
        m = [[4.0, 1.0, 0.5], [1.0, 3.0, -0.2], [0.5, -0.2, 2.0]]
        self.assertAlmostEqual(sum(sp._jacobi_eigenvalues(m)), 9.0, places=10)

    def test_les_valeurs_propres_d_une_correlation_somment_a_k(self) -> None:
        """La diagonale d'une matrice de corrélation vaut un partout."""
        from alp1.mc import Rng
        rng = Rng(7)
        series = [[rng.gauss() for _ in range(120)] for _ in range(6)]
        self.assertAlmostEqual(sum(sp.correlation_eigenvalues(series)), 6.0,
                               places=8)

    def test_le_bord_asymptotique_est_conservateur_a_k_fini(self) -> None:
        """Et le document doit le dire plutôt que de vendre λ₊ comme atteint.

        À sept séries sur deux cent cinquante observations, la plus grande
        valeur propre d'un spectre de bruit reste **sous** `λ₊`, y compris à
        son quantile à quatre-vingt-quinze pour cent. Le bord fermé est une
        limite quand `k` grandit, pas une barre que le bruit vient toucher.
        """
        loi = sp.null_spectrum(7, 250, draws=80)
        self.assertLess(loi.lambda_max_q95, loi.edge)
        self.assertGreater(loi.lambda_max_mean, 1.0)

    def test_la_loi_nulle_est_reproductible(self) -> None:
        self.assertEqual(sp.null_spectrum(5, 120, draws=30),
                         sp.null_spectrum(5, 120, draws=30))


if __name__ == "__main__":
    unittest.main()
