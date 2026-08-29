"""Les douze concepts de sortie, et les trois choses qui doivent tenir.

Un chapitre qui affirme « aucun concept de sortie ne crée d'espérance » ne
vaut que si le calcul le dit encore demain. Trois familles de tests le
gardent : la loi nulle, l'identité de Wald, et le fait qu'aucune règle ne
regarde au-delà de son index — sans quoi les deux premières seraient vraies
d'un objet qui n'est pas une règle de sortie.
"""

from __future__ import annotations

import unittest

from alp1 import sorties as S
from alp1.report11 import DERIVE_TRAVAIL

#: Assez de trajectoires pour trancher, assez peu pour que la batterie tienne.
#: Les chiffres publiés viennent du tirage complet, que le document construit.
N = 3000


class TestLoiNulle(unittest.TestCase):
    """Sous un prix sans dérive, les douze rendent `−c/a`."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ms = S.mesurer(0.0, N)
        cls.ratio = S.friction() / S.stop_points_declare()

    def test_la_cloture_seche_vaut_exactement_le_ratio_de_friction(self):
        """Elle est l'ancre, et elle l'est par construction, non par chance.

        Sa valeur terminale est la somme des incréments, dont l'appariement
        antithétique annule exactement la partie bruit. Si cette égalité
        cessait d'être exacte, c'est l'appariement qui serait cassé — et
        alors toute la table perdrait sa référence.
        """
        clot = next(m for m in self.ms if m.cle == "clot")
        self.assertAlmostEqual(clot.esperance, -self.ratio, places=12)

    def test_aucune_regle_ne_s_ecarte_de_la_prediction(self):
        for m in self.ms:
            with self.subTest(regle=m.cle):
                self.assertLess(abs(m.esperance - m.wald), 0.02 * 1.0,
                                f"{m.cle} : {m.esperance:+.4f} contre "
                                f"{m.wald:+.4f}")

    def test_aucun_ecart_a_l_ancre_n_est_significatif(self):
        """Trajectoires appariées : l'écart est la statistique qui tranche."""
        for m in self.ms:
            with self.subTest(regle=m.cle):
                self.assertLess(abs(m.ecart_ref), 3.0 * m.ecart_ref_se + 1e-12)

    def test_la_dispersion_et_le_taux_de_gain_bougent_beaucoup(self):
        """Ce que la table existe pour montrer : l'espérance seule est fixe."""
        sds = [m.ecart_type for m in self.ms]
        gains = [m.taux_gain for m in self.ms]
        self.assertGreater(max(sds) / min(sds), 3.0)
        self.assertGreater(max(gains) - min(gains), 0.25)


class TestWald(unittest.TestCase):
    """Sous dérive déclarée, l'espérance suit `(µ·E[τ] − c)/a`."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ms = S.mesurer(DERIVE_TRAVAIL, N)

    def test_chaque_regle_tombe_sur_la_prediction(self):
        for m in self.ms:
            with self.subTest(regle=m.cle):
                self.assertLess(abs(m.esperance - m.wald), 0.03,
                                f"{m.cle} : {m.esperance:+.4f} contre "
                                f"{m.wald:+.4f}")

    def test_le_classement_suit_l_exposition(self):
        """C'est le résultat du chapitre, réduit à une monotonie."""
        rangs = sorted(self.ms, key=lambda m: m.exposition)
        esperances = [m.esperance for m in rangs]
        self.assertEqual(esperances, sorted(esperances))

    def test_la_prise_partielle_est_la_seule_a_changer_de_taille(self):
        """Son temps écoulé et son temps exposé diffèrent ; les autres, non.

        C'est le défaut qui avait fait échouer sa prédiction : l'identité de
        Wald mesure le temps exposé, pas le temps écoulé.
        """
        for m in self.ms:
            with self.subTest(regle=m.cle):
                if m.cle == "part":
                    self.assertLess(m.exposition, m.ecoule - 1.0)
                else:
                    self.assertAlmostEqual(m.exposition, m.ecoule, places=9)


class TestTempsDArret(unittest.TestCase):
    """Aucune règle ne regarde au-delà de son index.

    Sans ce contrôle, une règle qui lirait le futur produirait une espérance
    positive sous prix sans dérive, et les deux tests précédents la
    déclareraient conforme à une prédiction qu'elle aurait truquée.
    """

    def _trajectoires(self, n: int = 60):
        from alp1.mc import Rng
        rng, sig = Rng(7), S.bruit_par_pas()
        for _ in range(n):
            x, p = 0.0, [0.0]
            for _ in range(S.SEANCE_MIN):
                x += sig * rng.gauss()
                p.append(x)
            yield p

    def test_perturber_l_apres_sortie_ne_change_rien(self):
        a = S.stop_points_declare()
        for r in S.regles():
            for p in self._trajectoires():
                i, prix, fills, expo = r.fn(p, a)
                if i >= len(p) - 1:
                    continue          # sortie à la clôture : rien après
                q = p[:i + 1] + [x + 1000.0 for x in p[i + 1:]]
                j, prix2, fills2, expo2 = r.fn(q, a)
                with self.subTest(regle=r.cle):
                    self.assertEqual(i, j)
                    self.assertAlmostEqual(prix, prix2, places=9)
                    self.assertEqual(fills, fills2)
                    self.assertAlmostEqual(expo, expo2, places=9)

    def test_la_sortie_tombe_toujours_dans_la_seance(self):
        a = S.stop_points_declare()
        for r in S.regles():
            for p in self._trajectoires(12):
                i, _, fills, expo = r.fn(p, a)
                with self.subTest(regle=r.cle):
                    self.assertGreaterEqual(i, 0)
                    self.assertLessEqual(i, S.SEANCE_MIN)
                    self.assertGreaterEqual(expo, 0.0)
                    self.assertLessEqual(expo, float(i) + 1e-9)
                    self.assertIn(fills, (0, 1))


class TestGeometrie(unittest.TestCase):
    def test_le_stop_declare_est_sous_le_bruit_d_une_minute(self):
        """La raison pour laquelle la simulation ne tourne pas à 0,010 %.

        À la géométrie déclarée il n'y a pas de concept de sortie : la
        position est close avant qu'aucune gestion n'ait pu agir.
        """
        self.assertGreater(S.bruit_sur_stop_declare(), 2.0)

    def test_les_douze_concepts_sont_exposes(self):
        rs = S.regles()
        self.assertEqual(len(rs), 12)
        self.assertEqual(len({r.cle for r in rs}), 12)
        self.assertEqual({r.famille for r in rs},
                         {"discrétionnaire", "quantitatif"})

    def test_les_deux_tables_sont_exposees(self):
        self.assertEqual(set(S.all_tables()),
                         {"sorties_nulles", "sorties_derive"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
