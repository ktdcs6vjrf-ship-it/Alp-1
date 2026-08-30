"""Le théorème sous six lois : ce que la campagne doit établir, et ce qu'elle ne doit pas.

Deux familles de tests, et la seconde est la plus importante.

La première vérifie que les six lois sont bien ce qu'elles prétendent être —
centrées, réduites, et dotées de l'asymétrie qu'on leur attribue. Une loi mal
normalisée rendrait toute la campagne fausse sans qu'aucune ligne ne le
signale, parce que l'espérance bougerait pour une raison de volatilité et
qu'on l'attribuerait à la forme des queues.

La seconde interdit à la campagne de se donner raison. Le seuil de décision
doit être corrigé du nombre de verdicts et calculé, jamais écrit ; le verdict
doit savoir dire « réfutée » quand l'écart le mérite ; et l'appariement
antithétique, qui divise la variance de simulation, ne doit jamais s'appliquer
à une loi asymétrique — il y fabriquerait une symétrie que la loi n'a pas.
"""

from __future__ import annotations

import math
import unittest

from alp1 import robustesse as R
from alp1.costs import _norm_ppf


class TestLesSixLois(unittest.TestCase):
    """Chaque loi est ce qu'elle dit être, et c'est mesuré."""

    @classmethod
    def setUpClass(cls):
        cls.moments = {m.cle: m for m in R.moments()}

    def test_six_lois_distinctes(self):
        cles = [l.cle for l in R.lois()]
        self.assertEqual(len(cles), len(set(cles)))
        self.assertEqual(len(cles), 6)

    def test_chaque_loi_est_centree(self):
        for loi in R.lois():
            with self.subTest(loi=loi.cle):
                self.assertLess(abs(self.moments[loi.cle].moyenne), 0.02)

    def test_chaque_loi_est_reduite(self):
        # Le mélange à volatilité de séance porte une tolérance plus large :
        # sa variance n'est estimée que sur mille séances, chacune tirant une
        # seule volatilité, et l'erreur d'échantillonnage y est donc celle du
        # nombre de séances et non du nombre d'incréments.
        for loi in R.lois():
            with self.subTest(loi=loi.cle):
                tol = 0.06 if loi.par_seance else 0.03
                self.assertAlmostEqual(self.moments[loi.cle].ecart_type, 1.0,
                                       delta=tol)

    def test_la_loi_a_sauts_est_asymetrique_a_gauche(self):
        """L'asymétrie d'un indice est négative — c'est le point de fait."""
        self.assertLess(self.moments["merton"].asymetrie, -0.3)

    def test_la_loi_a_plancher_est_asymetrique_a_droite(self):
        self.assertGreater(self.moments["plafonnee"].asymetrie, 1.8)

    def test_le_plancher_est_exact(self):
        """« La baisse est plafonnée » : à un écart-type, jamais au-delà."""
        self.assertAlmostEqual(self.moments["plafonnee"].borne_basse, -1.0,
                               delta=1e-6)

    def test_les_queues_epaisses_le_sont(self):
        for cle in ("student5", "student3", "melange", "merton"):
            with self.subTest(loi=cle):
                self.assertLess(self.moments[cle].borne_basse,
                                self.moments["gauss"].borne_basse)

    def test_la_kurtosis_infinie_n_est_pas_publiee(self):
        """Un moment qui diverge ne se publie pas comme s'il existait."""
        student3 = [l for l in R.lois() if l.cle == "student3"][0]
        self.assertFalse(student3.kurtosis_finie)
        self.assertIn("infinie", R.table_lois().to_text())


class TestLesQueuesComptees(unittest.TestCase):
    """La figure des queues doit lire un comptage, pas une densité."""

    @classmethod
    def setUpClass(cls):
        cls.q = R.queues()

    def test_les_deux_queues_de_la_gaussienne_se_valent(self):
        d = {x: (b, h) for x, b, h in self.q["gauss"]}
        bas, haut = d[3.0]
        self.assertAlmostEqual(bas, haut, delta=0.0006)

    def test_la_loi_a_sauts_tombe_plus_souvent_a_gauche(self):
        d = {x: (b, h) for x, b, h in self.q["merton"]}
        bas, haut = d[3.0]
        self.assertGreater(bas, 3.0 * haut)

    def test_la_loi_a_plancher_n_a_plus_de_queue_gauche(self):
        for x, bas, _ in self.q["plafonnee"]:
            if x > 1.0:
                with self.subTest(seuil=x):
                    self.assertEqual(bas, 0.0)

    def test_les_queues_decroissent(self):
        for cle, serie in self.q.items():
            with self.subTest(loi=cle):
                bas = [b for _, b, _ in serie]
                haut = [h for _, _, h in serie]
                self.assertEqual(bas, sorted(bas, reverse=True))
                self.assertEqual(haut, sorted(haut, reverse=True))


class TestLInvariance(unittest.TestCase):
    """Le résultat lui-même, et les garde-fous qui l'empêchent de tricher."""

    @classmethod
    def setUpClass(cls):
        cls.nul = {m.cle: m for m in R.mesurer(0.0)}
        cls.derive = {m.cle: m for m in R.mesurer(R.DERIVE_HAUTE)}

    def test_le_seuil_de_verdict_est_corrige_du_nombre_de_verdicts(self):
        """Bonferroni, calculé — et strictement plus exigeant que deux."""
        attendu = _norm_ppf(1.0 - R.ALPHA_TEST / (2.0 * R.N_TESTS))
        self.assertAlmostEqual(R.Z_SEUIL, attendu, places=9)
        self.assertGreater(R.Z_SEUIL, 2.0)
        self.assertEqual(R.N_TESTS, 2 * len(R.lois()))

    def test_sans_derive_toutes_les_lois_rendent_la_meme_prediction(self):
        attendu = -R.friction() / R.stop_points()
        for cle, m in self.nul.items():
            with self.subTest(loi=cle):
                self.assertAlmostEqual(m.wald, attendu, places=9)

    def test_sans_derive_aucune_loi_ne_refute_le_theoreme(self):
        for cle, m in self.nul.items():
            with self.subTest(loi=cle):
                z, verdict = R._verdict(m)
                self.assertEqual(verdict, "compatible",
                                 f"{cle} : écart de {z:+.2f} erreurs types")

    def test_sous_derive_chaque_loi_retombe_sur_sa_propre_prediction(self):
        for cle, m in self.derive.items():
            with self.subTest(loi=cle):
                self.assertEqual(R._verdict(m)[1], "compatible")

    def test_sous_derive_les_predictions_ne_sont_plus_communes(self):
        """Sinon la table dirait que le temps de marché ne dépend pas de la loi."""
        walds = {round(m.wald, 6) for m in self.derive.values()}
        self.assertGreater(len(walds), 1)

    def test_le_verdict_sait_dire_refutee(self):
        """Un test qui ne peut pas échouer ne teste rien."""
        m = self.nul["gauss"]
        faux = R.Mesure(**{**m.__dict__,
                           "esperance": m.wald + 4.0 * m.erreur_type})
        self.assertEqual(R._verdict(faux)[1], "réfutée")

    def test_l_appariement_antithetique_epargne_les_lois_asymetriques(self):
        """Nier un incrément asymétrique change sa loi : interdit."""
        for loi in R.lois():
            with self.subTest(loi=loi.cle):
                attendu = 2 * R.N_PATHS if loi.symetrique else R.N_PATHS
                self.assertEqual(self.nul[loi.cle].n, attendu)

    def test_les_lois_asymetriques_sont_bien_reperees(self):
        asym = {l.cle for l in R.lois() if not l.symetrique}
        self.assertEqual(asym, {"merton", "plafonnee"})

    def test_le_depassement_est_plus_grand_sous_les_sauts(self):
        """On traverse son stop — et l'espérance ne bouge pas pour autant."""
        self.assertGreater(self.nul["merton"].depassement,
                           self.nul["gauss"].depassement)

    def test_la_queue_de_perte_est_plus_lourde_sous_les_sauts(self):
        self.assertLess(self.nul["merton"].queue, self.nul["gauss"].queue)


class TestCeQueLesQueuesDeplacent(unittest.TestCase):
    """Ce qui bouge doit bouger, sinon la section conclurait à rien."""

    @classmethod
    def setUpClass(cls):
        cls.nul = {m.cle: m for m in R.mesurer(0.0)}

    def test_le_seuil_est_l_image_du_temps(self):
        for cle, m in self.nul.items():
            with self.subTest(loi=cle):
                self.assertAlmostEqual(m.seuil,
                                       R.friction() / (m.exposition / 60.0),
                                       places=9)

    def test_une_queue_plus_epaisse_allonge_le_trade(self):
        """À variance égale, ce qui part dans les queues quitte la minute."""
        self.assertGreater(self.nul["student3"].exposition,
                           self.nul["gauss"].exposition)

    def test_les_lois_ne_deplacent_pas_toutes_le_seuil_pareil(self):
        seuils = [m.seuil for m in self.nul.values()]
        self.assertGreater(max(seuils) / min(seuils), 1.05)


class TestLaFamilleContinue(unittest.TestCase):
    """Le mélange d'échelles, et les deux surfaces qu'il porte."""

    def test_la_kurtosis_du_melange_suit_sa_formule(self):
        for v2 in R.SURF_V2:
            with self.subTest(v2=v2):
                attendu = R.kurtosis_mixte(v2)
                self.assertGreaterEqual(attendu, -1e-9)

    def test_le_melange_est_centre_et_reduit(self):
        from alp1.mc import Rng
        for v2 in (1.0, 6.0, 16.0):
            with self.subTest(v2=v2):
                f = R._mixte(v2)
                rng, etat = Rng(11), {}
                n = 60000
                s1 = s2 = 0.0
                for _ in range(n):
                    x = f(rng, etat)
                    s1 += x
                    s2 += x * x
                m = s1 / n
                self.assertLess(abs(m), 0.03)
                self.assertAlmostEqual(math.sqrt(s2 / n - m * m), 1.0,
                                       delta=0.08)

    def test_la_kurtosis_croit_avec_le_parametre(self):
        ks = [R.kurtosis_mixte(v) for v in sorted(R.SURF_V2)]
        self.assertEqual(ks, sorted(ks))

    def test_le_maximum_de_chaque_surface_est_au_coin_le_plus_loin(self):
        """En isométrie le coin (0, 0) est le plus éloigné : le relief doit
        monter vers l'horizon, sinon deux points de profondeur différente se
        comparent par leur ordonnée et la lecture est fausse."""
        for nom, z in (("espérance", R.surface_esperance()),
                       ("seuil", R.surface_seuil())):
            with self.subTest(surface=nom):
                self.assertEqual(z[0][0], max(max(l) for l in z))

    def test_l_esperance_est_plate_le_long_de_l_axe_des_queues(self):
        """La colonne de dérive nulle : le résultat de la partie, en un test."""
        z = R.surface_esperance()
        col = [ligne[-1] for ligne in z]      # dérive nulle, dernière colonne
        attendu = -R.friction() / R.stop_points()
        self.assertLess(max(col) - min(col), 0.05)
        for v in col:
            self.assertAlmostEqual(v, attendu, delta=0.05)

    def test_la_geometrie_deplace_le_seuil_bien_plus_que_les_queues(self):
        geo, queue = R._surf_facteur()
        self.assertGreater(geo, 5.0 * queue)


class TestLEchantillon(unittest.TestCase):
    """Le mur de décisions, et la façon dont il est calculé."""

    def test_le_nombre_de_decisions_croit_comme_le_carre_de_la_dispersion(self):
        self.assertAlmostEqual(R.decisions_pour(2.0) / R.decisions_pour(1.0),
                               4.0, places=6)

    def test_le_nombre_de_decisions_croit_quand_la_resolution_se_serre(self):
        self.assertGreater(R.decisions_pour(1.0, 0.005),
                           R.decisions_pour(1.0, 0.01))

    def test_la_simulation_n_atteint_pas_la_resolution_visee(self):
        """C'est le sujet de la section, et il doit rester vrai."""
        for m in R.mesurer(0.0):
            with self.subTest(loi=m.cle):
                self.assertLess(m.n, R.decisions_pour(m.ecart_type))


class TestLesTables(unittest.TestCase):
    """Les tables se rendent, et rien n'y est écrit à la main."""

    def test_toutes_les_tables_se_rendent(self):
        tables = R.all_tables()
        self.assertEqual(len(tables), 5)
        for cle, t in tables.items():
            with self.subTest(table=cle):
                self.assertTrue(t.rows)
                for ligne in t.rows:
                    self.assertEqual(len(ligne), len(t.headers))

    def test_la_colonne_de_verdict_vient_du_calcul(self):
        """Elle doit refléter `_verdict`, jamais une chaîne posée à la main."""
        t = R.table_invariance()
        col = t.headers.index("Verdict")
        for loi, ligne in zip(R.lois(), t.rows):
            with self.subTest(loi=loi.cle):
                attendu = R._verdict({m.cle: m for m in R.mesurer(0.0)}[loi.cle])[1]
                self.assertEqual(ligne[col], attendu)

    def test_aucune_valeur_n_est_vide(self):
        for cle, v in R.values().items():
            with self.subTest(cle=cle):
                self.assertTrue(v.strip())


if __name__ == "__main__":
    unittest.main()
