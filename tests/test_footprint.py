"""Le footprint, et ce que chacune de ses trois lectures vaut contre sa loi nulle.

Ces tests gardent surtout une chose : que la fréquence nulle d'un
déséquilibre diagonal dépend entièrement d'un paramètre non observable, la
taille de grappe. C'est le fait inconfortable de cette couche, et il doit
rester visible dans le code plutôt que dans une note de bas de page.
"""

from __future__ import annotations

import unittest

from alp1 import footprint as fp
from alp1.costs import ES
from alp1.orderflow import kyle_lambda


class TestStructure(unittest.TestCase):

    def test_le_delta_de_barre_est_la_somme_des_deltas_de_niveau(self) -> None:
        for kind in ("neutre", "absorption", "epuisement", "desequilibre"):
            bar = fp.synthesise(kind)
            self.assertEqual(bar.delta, sum(c.delta for c in bar.cells))
            self.assertEqual(bar.volume, sum(c.volume for c in bar.cells))

    def test_l_echelle_d_impact_n_est_pas_redefinie_ici(self) -> None:
        """Elle vient de `orderflow` : écrite deux fois, elle divergerait."""
        self.assertAlmostEqual(
            fp.IMPACT_PER_ROOT_VOLUME,
            kyle_lambda(ES.tick_size, fp.DEPTH_CONTRACTS), places=12)

    def test_les_niveaux_montent(self) -> None:
        bar = fp.synthesise("neutre")
        prix = [c.price for c in bar.cells]
        self.assertEqual(prix, sorted(prix))
        self.assertEqual(bar.low, prix[0])
        self.assertEqual(bar.high, prix[-1])


class TestDesequilibre(unittest.TestCase):
    """La lecture la plus répandue, et la plus dépendante d'un inobservable."""

    def test_la_comparaison_est_diagonale_et_jamais_de_meme_niveau(self) -> None:
        """Un niveau à 400 contre 400 ne déclenche rien, seul.

        La confusion est courante et elle est grave : l'ask et le bid d'un
        même prix ne se disputaient pas la même file, ils sont les deux côtés
        de deux spreads différents.
        """
        cellules = tuple(fp.Cell(6000.0 + 0.25 * i, 400, 400) for i in range(5))
        bar = fp.Bar(cellules, 6000.0, 6000.5)
        self.assertEqual(fp.diagonal_imbalances(bar), ())

    def test_un_contrat_a_la_fois_rend_le_desequilibre_impossible(self) -> None:
        """Et c'est pourquoi le modèle de grappe est indispensable.

        Si les contrats arrivaient indépendamment, l'ask d'un niveau à deux
        cents suivrait une binomiale d'écart-type sept : trois pour un
        exigerait plus de quinze écarts-types. Le déséquilibre serait un
        signal parfait, ce qu'il n'est manifestement pas.
        """
        self.assertLess(fp.null_imbalance_probability(200, 200, clump=1), 1e-9)

    def test_la_frequence_nulle_va_de_l_impossible_au_banal(self) -> None:
        """Le fait de cette couche : la loi nulle dépend d'un inobservable."""
        table = dict(fp.null_imbalance_by_clump(200, 200))
        self.assertLess(table[5], 1e-4)
        self.assertGreater(table[20], 0.01)
        self.assertGreater(table[50], 0.05)

    def test_une_grappe_trop_grosse_interdit_le_rapport(self) -> None:
        """Deux grappes par niveau ne peuvent pas faire trois pour un.

        Ce n'est pas un défaut de calcul mais une borne : le rapport exige au
        moins trois grappes du côté dominant. Le test le fixe pour qu'un
        futur lecteur du tableau ne le prenne pas pour un zéro suspect.
        """
        self.assertEqual(fp.null_imbalance_probability(200, 200, clump=100), 0.0)

    def test_une_barre_sans_intention_en_produit_environ_un(self) -> None:
        """Voir un déséquilibre ne veut rien dire ; c'est la mesure du propos.

        Sur neuf niveaux et aux volumes construits ici, la loi nulle en
        attend à peu près un par barre. Un opérateur qui en relève un n'a
        rien relevé.
        """
        attendu = fp.expected_imbalances(fp.synthesise("neutre"))
        self.assertGreater(attendu, 0.4)
        self.assertLess(attendu, 2.0)

    def test_la_barre_construite_en_montre_bien_plus_que_sa_loi(self) -> None:
        bar = fp.synthesise("desequilibre")
        observes = len(fp.diagonal_imbalances(bar))
        self.assertGreaterEqual(observes, 3)
        self.assertGreater(observes, 3.0 * fp.expected_imbalances(bar))
        self.assertTrue(all(cote == "acheteur"
                            for _, cote in fp.diagonal_imbalances(bar)))


class TestAbsorption(unittest.TestCase):
    """Un volume qui ne déplace pas le prix, mesuré sur l'échelle d'impact."""

    def test_la_p_valeur_est_centrale_et_non_extreme(self) -> None:
        """Elle croît avec `|z|`, à l'inverse d'une p-valeur ordinaire.

        Une absorption est un déplacement anormalement **faible** : c'est la
        masse centrale qui la mesure, pas la queue.
        """
        lam = fp.IMPACT_PER_ROOT_VOLUME
        plate = fp.Bar(fp.synthesise("neutre").cells, 6000.0, 6000.0)
        self.assertAlmostEqual(fp.absorption_p_value(plate, lam), 0.0, places=9)
        loin = fp.Bar(plate.cells, 6000.0, 6002.0)
        self.assertGreater(fp.absorption_p_value(loin, lam), 0.99)

    def test_la_barre_d_absorption_porte_un_gros_volume(self) -> None:
        """Un petit déplacement seul n'est pas une absorption.

        Sans le second terme, une barre morte à faible volume se lirait comme
        une absorption. Le `z` le dit déjà — il divise par la racine du
        volume — mais la barre construite doit le montrer.
        """
        abs_ = fp.synthesise("absorption")
        neutre = fp.synthesise("neutre")
        self.assertGreater(abs_.volume, 2.5 * neutre.volume)
        lam = fp.IMPACT_PER_ROOT_VOLUME
        self.assertLess(abs(fp.absorption_z(abs_, lam)), 0.3)
        self.assertGreater(abs(fp.absorption_z(neutre, lam)), 0.9)


class TestEpuisement(unittest.TestCase):
    """La seule des trois lectures dont la loi nulle se simule."""

    def test_le_volume_s_effondre_deja_sans_intention(self) -> None:
        """La médiane nulle vaut environ un, mais son quantile bas est bas.

        Sous martingale le prix passe peu de temps aux extrémités de son
        excursion : un niveau extrême à la moitié de la médiane arrive une
        fois sur vingt. « Le volume s'effondre » n'est donc pas une
        observation tant qu'on n'a pas dit à quel quantile.
        """
        loi = fp.null_exhaustion()
        self.assertGreater(loi.mean, 0.7)
        self.assertLess(loi.mean, 1.4)
        self.assertLess(loi.q05, 0.75)

    def test_la_barre_construite_tombe_sous_le_quantile_a_cinq_pour_cent(self) -> None:
        loi = fp.null_exhaustion()
        self.assertLess(fp.exhaustion_ratio(fp.synthesise("epuisement"), +1),
                        loi.q05)
        self.assertGreater(fp.exhaustion_ratio(fp.synthesise("neutre"), +1),
                           0.30)

    def test_la_loi_nulle_est_reproductible(self) -> None:
        """Même graine, même loi — sur toute machine et à toute date."""
        self.assertEqual(fp.null_exhaustion(), fp.null_exhaustion())


if __name__ == "__main__":
    unittest.main()
