"""Le profil TPO, et ce que chacune de ses cinq lectures vaut contre sa loi nulle.

Le résultat que ces tests fixent est double. Trois des cinq lectures — les
tirages simples, l'extension de séance, la largeur de l'aire de valeur — sont
l'état par défaut d'une marche sans dérive découpée en tranches ; les
observer ne dit rien. La quatrième, l'extrême pauvre, est réellement rare
sous sa loi nulle — mais sa rareté dépend entièrement du pas de cotation
rapporté à la volatilité, qui est un paramètre déclaré.
"""

from __future__ import annotations

import unittest

from alp1 import tpo


class TestConstruction(unittest.TestCase):

    def test_une_periode_imprime_a_tous_les_niveaux_traverses(self) -> None:
        """Bornes comprises : c'est ce que fait une plateforme."""
        prof = tpo.from_path([100.0, 100.5, 101.0], n_periods=1, tick=0.25)
        self.assertEqual(prof.counts, (1, 1, 1, 1, 1))
        self.assertEqual(prof.prices[0], 100.0)
        self.assertEqual(prof.prices[-1], 101.0)

    def test_les_niveaux_montent_et_le_total_compte_les_tpo(self) -> None:
        prof = tpo.synthesise()
        self.assertEqual(list(prof.prices), sorted(prof.prices))
        self.assertEqual(prof.total, sum(prof.counts))
        self.assertEqual(prof.n_periods, 13)

    def test_le_poc_est_le_niveau_le_plus_visite(self) -> None:
        prof = tpo.synthesise()
        i = prof.prices.index(prof.poc)
        self.assertEqual(prof.counts[i], max(prof.counts))

    def test_l_aire_de_valeur_contient_le_poc_et_la_part_visee(self) -> None:
        prof = tpo.synthesise()
        bas, haut = prof.value_area()
        self.assertLessEqual(bas, prof.poc)
        self.assertGreaterEqual(haut, prof.poc)
        dedans = sum(c for p, c in zip(prof.prices, prof.counts)
                     if bas <= p <= haut)
        self.assertGreaterEqual(dedans, tpo.VALUE_AREA * prof.total)

    def test_un_extreme_pauvre_est_un_extreme_a_deux_periodes(self) -> None:
        """Sans mèche : deux tranches au moins ont imprimé au plus haut."""
        prof = tpo.from_path([100.0, 100.25, 100.0, 100.25], n_periods=2,
                             tick=0.25)
        self.assertTrue(prof.poor_high)
        self.assertTrue(prof.poor_low)


class TestLoisNulles(unittest.TestCase):
    """Trois lectures sur cinq sont l'état par défaut d'une marche."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.loi = tpo.null_profile(draws=400)

    def test_l_extension_de_seance_est_quasi_certaine_sans_derive(self) -> None:
        """Une séance sans aucune intention dépasse presque toujours sa balance.

        C'est la lecture la plus citée du profil, et elle n'est pas un
        événement : elle est ce qui arrive quand rien n'arrive.
        """
        self.assertGreater(self.loi.p_extension, 0.95)

    def test_les_tirages_simples_sont_nombreux_sans_derive(self) -> None:
        """En compter dix ne dit rien quand la loi nulle en attend trente."""
        self.assertGreater(self.loi.singles_mean, 10.0)
        self.assertGreater(self.loi.singles_q95, self.loi.singles_mean)

    def test_l_aire_de_valeur_couvre_la_moitie_de_l_etendue(self) -> None:
        """Soixante-dix pour cent des TPO tiennent dans la moitié du parcours."""
        self.assertGreater(self.loi.value_width_mean, 0.35)
        self.assertLess(self.loi.value_width_mean, 0.75)

    def test_l_extreme_pauvre_est_la_seule_lecture_rare(self) -> None:
        """Et il faut le dire : toutes les lectures ne se valent pas.

        Le dépôt n'a pas pour objet de tout démolir. Sur les cinq, celle-ci
        passe le contrôle — sous le pas de cotation déclaré.
        """
        self.assertLess(self.loi.p_poor_high, 0.15)
        self.assertLess(self.loi.p_poor_low, 0.15)

    def test_la_rarete_de_l_extreme_pauvre_tient_au_pas_de_cotation(self) -> None:
        """Et c'est la limite de la lecture, pas une objection de détail.

        De 0,25 à 4 points de pas, la fréquence nulle passe d'une séance sur
        vingt à près d'une sur deux. Le pas ne dit rien du marché ; il dit le
        rapport du tick à la volatilité de la séance.
        """
        table = {t: p for t, p, _ in tpo.null_by_tick(draws=200)}
        self.assertLess(table[0.25], 0.12)
        self.assertGreater(table[4.0], 3.0 * table[0.25])

    def test_la_loi_nulle_est_reproductible(self) -> None:
        self.assertEqual(tpo.null_profile(draws=200),
                         tpo.null_profile(draws=200))


if __name__ == "__main__":
    unittest.main()
