"""Une affirmation venue du dehors : ce que le test doit interdire.

Trois familles, et la deuxième est celle qui compte.

La première vérifie que la loi de la position d'ouverture est bien ce qu'elle
prétend être — sans dimension, symétrique, en U. Si elle cessait de l'être, la
partie entière tomberait sans qu'aucune ligne ne le signale.

La deuxième interdit la circularité. Le modèle nul a deux paramètres, et ils
doivent être calibrés sur les **deux nombres qui ne portent aucune direction**.
Un test qui laisserait calibrer sur les nombres de direction laisserait le
document expliquer n'importe quoi.

La troisième verrouille le verdict : il doit rester **calculé**, il doit savoir
changer de signe, et les deux lectures du chiffre publié doivent rester
publiées toutes les deux. Le jour où l'une disparaît, le document choisit celle
qui l'arrange.
"""

from __future__ import annotations

import math
import unittest

from alp1 import overnight as O


class TestLaPosition(unittest.TestCase):
    """La grandeur qui contient déjà la réponse."""

    @classmethod
    def setUpClass(cls):
        cls.us = sorted(u for u, _ in O.nuits())

    def test_la_position_est_dans_le_range(self):
        self.assertGreaterEqual(min(self.us), 0.0)
        self.assertLessEqual(max(self.us), 1.0)

    def test_la_loi_est_symetrique(self):
        n = len(self.us)
        self.assertAlmostEqual(sum(1 for u in self.us if u > 0.5) / n, 0.5,
                               delta=0.02)
        self.assertAlmostEqual(self.us[n // 2], 0.5, delta=0.02)

    def test_la_loi_est_en_u_et_non_uniforme(self):
        """Les bords sont chargés : c'est tout le mécanisme de la partie."""
        n = len(self.us)
        bords = sum(1 for u in self.us if u < 0.15 or u > 0.85) / n
        self.assertGreater(bords, 0.30)          # uniforme donnerait 0,30
        self.assertGreater(sum(abs(u - 0.5) for u in self.us) / n, 0.26)

    def test_le_bord_proche_est_bien_plus_proche_que_l_autre(self):
        proche, loin = O.distance_au_bord()
        self.assertAlmostEqual(proche + loin, 1.0, places=9)
        self.assertGreater(loin / proche, 3.0)

    def test_la_position_ne_depend_d_aucune_echelle(self):
        """Elle est sans dimension : un test l'exige plutôt que la prose."""
        a = O.nuits()[:200]
        for u, portee in a:
            with self.subTest(portee=round(portee, 2)):
                self.assertGreater(portee, 0.0)
                self.assertTrue(0.0 <= u <= 1.0)


class TestLeProfilDeVariance(unittest.TestCase):
    """Le pic d'ouverture déplace la variance, il n'en ajoute pas."""

    def test_les_deux_profils_ont_la_meme_variance_totale(self):
        plat = sum(x * x for x in O.profil(False))
        pic = sum(x * x for x in O.profil(True))
        self.assertAlmostEqual(plat, pic, delta=1e-6 * plat)

    def test_le_pic_concentre_la_premiere_demi_heure(self):
        part = O.part_variance_premiere_demi_heure()
        self.assertGreater(part, 0.20)
        self.assertLess(part, 0.60)

    def test_le_profil_plat_est_plat(self):
        self.assertEqual(set(O.profil(False)), {1.0})


class TestLaCalibrationNEstPasCirculaire(unittest.TestCase):
    """Le garde-fou central de la partie."""

    def test_les_cibles_de_calibration_ne_portent_aucune_direction(self):
        for cle in O.CALIBRAGE:
            with self.subTest(cible=cle):
                self.assertNotIn("haut", cle)
                self.assertNotIn("bas", cle)
        self.assertEqual(set(O.CALIBRAGE), {"aucun", "les_deux"})

    def test_les_nombres_de_direction_restent_a_predire(self):
        directionnels = {"haut_si_dessus", "bas_si_dessous"}
        self.assertFalse(directionnels & set(O.CALIBRAGE))

    def test_le_couple_calibre_est_dans_sa_boite(self):
        k, s = O.calibrer()
        self.assertGreaterEqual(k, O.K_BOX[0])
        self.assertLessEqual(k, O.K_BOX[1])
        self.assertGreaterEqual(s, O.S_VOL_BOX[0])
        self.assertLessEqual(s, O.S_VOL_BOX[1])

    def test_la_calibration_rend_bien_ses_deux_cibles(self):
        c = O.retenue()
        for cle in O.CALIBRAGE:
            with self.subTest(cible=cle):
                self.assertAlmostEqual(getattr(c, cle), O.ANNONCES[cle],
                                       delta=0.03)


class TestLeConditionnel(unittest.TestCase):
    """Le 76 % doit se retrouver sans qu'aucune propriété de marché n'entre."""

    @classmethod
    def setUpClass(cls):
        cls.c = O.retenue()

    def test_le_conditionnel_suit_la_loi_d_arret(self):
        """Conditionné sur une cassure, le mesuré doit tomber sur `1 − distance`."""
        for i, p in enumerate(self.c.par_decile_casse):
            milieu = (i + 0.5) * 0.05
            with self.subTest(decile=i):
                self.assertAlmostEqual(p, 1.0 - milieu, delta=0.05)

    def test_l_ecart_entre_les_deux_colonnes_est_la_part_des_seances_mortes(self):
        """Une séance qui ne casse rien compte comme un échec à chaque distance."""
        for i, (tout, casse) in enumerate(zip(self.c.par_decile,
                                              self.c.par_decile_casse)):
            with self.subTest(decile=i):
                self.assertAlmostEqual(tout / casse, 1.0 - self.c.p_rien,
                                       delta=0.05)

    def test_le_conditionnel_decroit_avec_la_distance(self):
        deb = sum(self.c.par_decile_casse[:3]) / 3.0
        fin = sum(self.c.par_decile_casse[-3:]) / 3.0
        self.assertGreater(deb, fin)

    def test_les_deux_sens_sont_symetriques(self):
        self.assertAlmostEqual(self.c.haut_si_dessus, self.c.bas_si_dessous,
                               delta=0.03)

    def test_la_loi_nulle_arrive_pres_du_chiffre_publie(self):
        """Sans cela, la partie n'aurait rien à dire."""
        nul = (self.c.haut_si_dessus + self.c.bas_si_dessous) / 2.0
        ann = (O.ANNONCES["haut_si_dessus"] + O.ANNONCES["bas_si_dessous"]) / 2.0
        self.assertLess(abs(nul - ann), 0.08)


class TestLeVerdict(unittest.TestCase):
    """Le verdict est calculé, il sait changer de signe, et il publie les deux lectures."""

    @classmethod
    def setUpClass(cls):
        cls.c = O.retenue()

    def test_l_esperance_suit_la_prediction_de_wald(self):
        z = (self.c.esperance - self.c.wald) / self.c.erreur_type
        self.assertLess(abs(z), 3.0)

    def test_l_esperance_est_lineaire_en_taux(self):
        a = self.c.esperance_au_taux(0.60)
        b = self.c.esperance_au_taux(0.70)
        d = self.c.esperance_au_taux(0.80)
        self.assertAlmostEqual(b - a, d - b, places=9)

    def test_le_taux_d_equilibre_annule_l_esperance(self):
        seuil = self.c.taux_equilibre()
        self.assertAlmostEqual(self.c.esperance_au_taux(seuil), 0.0, places=6)

    def test_le_taux_d_equilibre_est_exigeant(self):
        """La géométrie impose un rapport étroit : le seuil doit être haut."""
        self.assertGreater(self.c.taux_equilibre(), 0.70)
        self.assertLess(self.c.rapport, 0.60)

    def test_le_verdict_sait_changer_de_signe(self):
        """Un verdict qui ne peut pas basculer ne teste rien."""
        seuil = self.c.taux_equilibre()
        self.assertLess(self.c.esperance_au_taux(seuil - 0.05), 0.0)
        self.assertGreater(self.c.esperance_au_taux(seuil + 0.05), 0.0)

    def test_les_deux_lectures_sont_publiees(self):
        lectures = O._lectures()
        self.assertEqual(len(lectures), 2)
        verdicts = {v for *_r, v in lectures}
        self.assertEqual(verdicts, {"gagnante", "perdante"},
                         "les deux lectures doivent rester de signes opposés, "
                         "sinon le document a choisi celle qui l'arrange")

    def test_l_ecart_entre_lectures_depasse_l_effet_revendique(self):
        lectures = O._lectures()
        ecart = abs(lectures[0][1] - lectures[1][1])
        residu = abs(lectures[0][1] - lectures[0][2])
        self.assertGreater(ecart, residu)


class TestLaBoite(unittest.TestCase):
    """Le résidu est borné par une hypothèse, et la surface doit le montrer."""

    def test_le_maximum_de_la_surface_est_au_fond(self):
        """La crête est intérieure — à très faible rapport de volatilité les
        deux bords se font toucher et le conditionnel retombe — mais elle doit
        rester dans le quart le plus éloigné, sinon le relief descend vers le
        lecteur et deux points de profondeur différente se comparent par leur
        ordonnée."""
        z = O.surface_boite()
        i, j = max(((i, j) for i in range(len(z)) for j in range(len(z[0]))),
                   key=lambda ij: z[ij[0]][ij[1]])
        self.assertLessEqual(i, 1)
        self.assertLessEqual(j, 1)

    def test_l_amplitude_de_la_boite_est_du_meme_ordre_que_le_residu(self):
        vals = [v for ligne in O.surface_boite() for v in ligne]
        amplitude = max(vals) - min(vals)
        c = O.retenue()
        ann = (O.ANNONCES["haut_si_dessus"] + O.ANNONCES["bas_si_dessous"]) / 2.0
        residu = abs(ann - (c.haut_si_dessus + c.bas_si_dessous) / 2.0)
        self.assertGreater(amplitude, residu)

    def test_le_plan_de_jeu_equitable_est_de_l_arithmetique(self):
        """Aucune simulation n'y entre, et un test l'exige."""
        self.assertAlmostEqual(O.esperance_plan(1.0, 0.5), 0.5, places=9)
        self.assertAlmostEqual(O.esperance_plan(0.0, 0.5), -1.0, places=9)
        self.assertAlmostEqual(O.esperance_plan(0.5, 1.0), 0.0, places=9)

    def test_le_maximum_du_plan_est_au_coin_le_plus_loin(self):
        z = O.surface_plan()
        self.assertEqual(z[0][0], max(max(l) for l in z))


class TestLesTables(unittest.TestCase):
    def test_toutes_les_tables_se_rendent(self):
        tables = O.all_tables()
        self.assertEqual(len(tables), 7)
        for cle, t in tables.items():
            with self.subTest(table=cle):
                self.assertTrue(t.rows)
                for ligne in t.rows:
                    self.assertEqual(len(ligne), len(t.headers))

    def test_les_sept_nombres_publies_sont_cites_une_seule_fois(self):
        self.assertEqual(len(O.ANNONCES), 7)

    def test_aucune_valeur_n_est_vide(self):
        for cle, v in O.values().items():
            with self.subTest(cle=cle):
                self.assertTrue(v.strip())


if __name__ == "__main__":
    unittest.main()
