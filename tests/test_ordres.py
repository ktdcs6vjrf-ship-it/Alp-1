"""Les tests de la partie XXVIII — les grecs du troisième ordre.

Trois tests portent ici plus que les autres. Le premier contrôle les cinq
formes fermées contre la dérivée qu'elles prétendent être, ce qu'aucun des
neuf guides ne fait et que la partie XXIV a montré indispensable. Le
deuxième exige que la racine négative d'Ultima soit **inatteignable**, ce qui
règle le nombre de ses changements de signe sans balayage. Le troisième exige
que les trois bandes du même produit soient **emboîtées** dans le bon ordre :
c'est la structure qui relie quatre parties d'options.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import grandeurs as G
from alp1 import ordres as O
from alp1 import vanna as va
from alp1 import vega as vg
from alp1 import volga as vo


S, V = O.S_REF, O.VOL_REF


class TestLesFormesFermees(unittest.TestCase):
    def test_speed_egale_la_derivee_du_gamma(self):
        for j in (1.0, 7.0, 30.0, 90.0):
            t = j / O.JOURS_AN
            for m in (0.90, 0.97, 1.0, 1.03, 1.10):
                k = S / m
                a, b = O.speed(S, k, V, t), O.speed_numerique(S, k, V, t)
                self.assertLess(abs(a - b), 1e-5 * max(1e-6, abs(a)),
                                (j, m, a, b))

    def test_zomma_egale_la_derivee_du_gamma_en_vol(self):
        for j in (7.0, 30.0, 90.0):
            t = j / O.JOURS_AN
            for m in (0.90, 1.0, 1.10):
                k = S / m
                self.assertAlmostEqual(O.zomma(S, k, V, t),
                                       O.zomma_numerique(S, k, V, t),
                                       places=6, msg=(j, m))

    def test_ultima_egale_la_derivee_du_volga(self):
        for j in (7.0, 30.0, 90.0, 365.0):
            t = j / O.JOURS_AN
            for m in (0.80, 0.95, 1.0, 1.05, 1.25):
                k = S / m
                a, b = O.ultima(S, k, V, t), O.ultima_numerique(S, k, V, t)
                self.assertLess(abs(a - b), 1e-3 * max(1.0, abs(a)),
                                (j, m, a, b))

    def test_color_et_veta_sont_les_derivees_en_temps(self):
        for j in (7.0, 30.0, 90.0):
            t = j / O.JOURS_AN
            k = S
            h = 1e-6
            co = -(O.gamma(S, k, V, t + h) - O.gamma(S, k, V, t - h)) \
                / (2 * h) / O.JOURS_AN
            ve = -(vg.vega(S, k, V, t + h, O.TAUX, O.DIVIDENDE)
                   - vg.vega(S, k, V, t - h, O.TAUX, O.DIVIDENDE)) \
                / (2 * h) / O.JOURS_AN
            self.assertAlmostEqual(O.color(S, k, V, t), co, places=8, msg=j)
            self.assertAlmostEqual(O.veta(S, k, V, t), ve, places=6, msg=j)


class TestLesSignes(unittest.TestCase):
    """La table de référence du guide, vérifiée ligne par ligne."""

    def test_speed_change_de_signe_autour_du_strike(self):
        t = 7.0 / O.JOURS_AN
        self.assertGreater(O.speed(S, S / 0.95, V, t), 0.0)
        self.assertLess(O.speed(S, S / 1.05, V, t), 0.0)

    def test_zomma_est_negatif_a_la_monnaie(self):
        for j in (7.0, 30.0, 90.0):
            self.assertLess(O.zomma(S, S, V, j / O.JOURS_AN), 0.0, j)

    def test_color_est_positif_a_la_monnaie(self):
        for j in (2.0, 7.0, 30.0, 90.0):
            self.assertGreater(O.color(S, S, V, j / O.JOURS_AN), 0.0, j)

    def test_veta_est_negatif_partout(self):
        for j in (7.0, 30.0, 90.0, 365.0):
            for m in (0.95, 1.0, 1.05):
                self.assertLess(O.veta(S, S / m, V, j / O.JOURS_AN), 0.0,
                                (j, m))

    def test_ultima_est_negatif_pres_de_la_monnaie_et_positif_aux_ailes(self):
        for j in (30.0, 90.0):
            t = j / O.JOURS_AN
            lo, hi = O.bande_ultima(t)
            self.assertLess(O.ultima(S, S, V, t), 0.0, j)
            self.assertGreater(O.ultima(S, S / (lo * 0.9), V, t), 0.0, j)
            self.assertGreater(O.ultima(S, S / (hi * 1.1), V, t), 0.0, j)


class TestLHorloge(unittest.TestCase):
    """Color et Veta à la monnaie n'ont aucun paramètre libre."""

    def test_les_deux_lois_sont_exactes_a_portage_nul(self):
        """La forme fermée n'approxime rien quand le portage est nul."""
        for j in (2.0, 7.0, 30.0, 90.0, 365.0):
            self.assertAlmostEqual(O.gamma_demain(j),
                                   O.gamma_demain_mesure_sans_portage(j),
                                   places=9, msg=j)
            self.assertAlmostEqual(O.vega_perdu(j),
                                   O.vega_perdu_mesure_sans_portage(j),
                                   places=9, msg=j)

    def test_la_lecture_simple_n_a_aucun_parametre(self):
        """Le fait de la section, et il vaut pour la lecture qu'on retient."""
        self.assertEqual(O.gamma_demain_simple(30.0), math.sqrt(30.0 / 29.0))
        self.assertEqual(O.vega_perdu_simple(30.0),
                         1.0 - math.sqrt(29.0 / 30.0))

    def test_elle_serre_la_forme_exacte_aux_echeances_courtes(self):
        for j in (2.0, 7.0, 30.0):
            self.assertLess(abs(O.gamma_demain_simple(j) / O.gamma_demain(j)
                                - 1.0), 1e-4, j)
            self.assertLess(abs(O.vega_perdu_simple(j) / O.vega_perdu(j)
                                - 1.0), 2e-3, j)

    def test_le_portage_est_le_plus_grand_des_deux_ecarts(self):
        """Troisième fois que la question de la partie XXIII se pose."""
        for j in (7.0, 30.0, 90.0):
            simple = abs(O.vega_perdu_simple(j) / O.vega_perdu(j) - 1.0)
            self.assertGreater(abs(O.ecart_de_portage(j)), simple, j)
            self.assertLess(abs(O.ecart_de_portage(j)), 0.02, j)

    def test_le_vega_court_se_volatilise_et_le_long_est_stable(self):
        self.assertGreater(O.facteur_veta(), 40.0)
        self.assertLess(O.vega_perdu_mesure(365.0), 0.002)
        self.assertGreater(O.vega_perdu_mesure(7.0), 0.07)


class TestLeMouvementDeDemiGamma(unittest.TestCase):
    def test_la_forme_fermee_serre_la_mesure_aux_echeances_courtes(self):
        for j in (0.25, 0.5, 1.0, 2.0):
            a = O.mouvement_de_demi_gamma(j)
            b = O.mouvement_de_demi_gamma_mesure(j)
            self.assertLess(abs(a / b - 1.0), 0.05, j)

    def test_la_constante_est_celle_de_la_partie_XIX(self):
        self.assertAlmostEqual(O.DEMI_HAUTEUR, math.sqrt(2.0 * math.log(2.0)),
                               places=12)
        self.assertAlmostEqual(O.DEMI_HAUTEUR, 1.1774100226, places=8)

    def test_l_affirmation_du_guide_est_surestimee(self):
        """Une fraction de pour cent, mais pas le dernier jour."""
        self.assertGreater(O.mouvement_de_demi_gamma_mesure(1.0), 0.01 * S)
        self.assertLess(O.mouvement_de_demi_gamma_mesure(0.25), 0.01 * S)

    def test_le_seuil_tombe_dans_les_dernieres_heures(self):
        h = 24.0 * O.echeance_du_pour_cent()
        self.assertGreater(h, 6.0)
        self.assertLess(h, 14.0)

    def test_le_mouvement_croit_avec_l_echeance(self):
        vals = [O.mouvement_de_demi_gamma_mesure(j) for j in O.COURTES]
        for a, b in zip(vals, vals[1:]):
            self.assertLess(a, b)


class TestUltima(unittest.TestCase):
    def test_la_racine_negative_n_est_jamais_atteinte(self):
        """Ce qui règle le nombre de changements de signe sans balayage."""
        for j in (1.0, 7.0, 30.0, 90.0, 365.0, 1825.0):
            t = j / O.JOURS_AN
            self.assertLess(O.racines_ultima(t)[0], O.minimum_de_d1d2(t), j)

    def test_le_minimum_du_produit_vaut_moins_sigma_carre_T_sur_quatre(self):
        for j in (7.0, 30.0, 365.0):
            t = j / O.JOURS_AN
            mesure = min((lambda d: d * (d + V * math.sqrt(t)))(-3.0 + 6.0 * i
                                                                / 20000)
                         for i in range(20001))
            self.assertAlmostEqual(mesure, O.minimum_de_d1d2(t), places=7,
                                   msg=j)

    def test_la_bascule_tombe_sur_la_racine_positive(self):
        for j in (7.0, 30.0, 90.0, 365.0):
            t = j / O.JOURS_AN
            for m in O.bande_ultima(t):
                d1, d2 = G._d(S, S / m, V, t, O.TAUX, O.DIVIDENDE)
                self.assertAlmostEqual(d1 * d2, O.racines_ultima(t)[1],
                                       places=6, msg=(j, m))

    def test_il_y_a_exactement_deux_changements_de_signe(self):
        for j in (7.0, 30.0, 90.0):
            t = j / O.JOURS_AN
            prev, n = None, 0
            for i in range(6001):
                m = 0.20 + 3.3 * i / 6000
                v = O.ultima(S, S / m, V, t)
                if prev is not None and prev * v < 0.0:
                    n += 1
                prev = v
            self.assertEqual(n, 2, j)


class TestLesTroisBandes(unittest.TestCase):
    """Le même produit, trois seuils, trois bandes emboîtées."""

    def test_elles_sont_emboitees_dans_le_bon_ordre(self):
        for j in (7.0, 30.0, 90.0, 365.0):
            t = j / O.JOURS_AN
            lo, hi = va.bande_de_desobeissance(t)
            self.assertLess(hi - lo, O.largeur_zomma(t), j)
            self.assertLess(O.largeur_zomma(t), O.largeur_ultima(t), j)

    def test_la_bande_du_volga_est_bien_celle_du_module_volga(self):
        for j in (7.0, 30.0):
            t = j / O.JOURS_AN
            a = va.bande_de_desobeissance(t)
            b = vo.bande_negative(t)
            self.assertAlmostEqual(a[0], b[0], places=12, msg=j)

    def test_seule_la_troisieme_est_cotable(self):
        """Une grille de strikes au pour cent ne voit que celle d'Ultima."""
        t = 30.0 / O.JOURS_AN
        lo, hi = va.bande_de_desobeissance(t)
        self.assertLess(hi - lo, 0.01)
        self.assertGreater(O.largeur_ultima(t), 0.05)

    def test_le_rapport_decroit_avec_l_echeance(self):
        vals = [O.rapport_au_volga(j / O.JOURS_AN)
                for j in (7.0, 30.0, 90.0, 365.0)]
        for a, b in zip(vals, vals[1:]):
            self.assertGreater(a, b)


class TestLaVariance(unittest.TestCase):
    def test_les_quatre_grecs_expliquent_plus_de_quatre_vingt_dix_neuf(self):
        for e, d in O.COUPLES:
            self.assertGreater(O.campagne(e, d, False).part, 0.99, (e, d))

    def test_le_livre_couvert_se_degrade_sans_s_effondrer(self):
        for e, d in O.COUPLES:
            libre = O.campagne(e, d, False).part
            cvt = O.campagne(e, d, True).part
            self.assertLessEqual(cvt, libre + 1e-9, (e, d))
            self.assertGreater(cvt, 0.95, (e, d))

    def test_dans_le_cas_que_le_guide_decrit_le_residu_est_infime(self):
        c = O.campagne(7.0, 4.0 / 24.0, False)
        self.assertLess(1.0 - c.part, 1e-4)

    def test_la_campagne_est_deterministe(self):
        a = O.campagne(30.0, 1.0, False)
        O.campagne.cache_clear()
        b = O.campagne(30.0, 1.0, False)
        self.assertEqual(a.part, b.part)

    def test_la_correlation_declaree_n_est_pas_ajustee(self):
        """Un paramètre ajusté sur ce qu'il évalue est le piège de la partie X."""
        self.assertEqual(O.RHO, -0.60)
        self.assertEqual(O.NU, vo.NU)


class TestLeDecompte(unittest.TestCase):
    def test_aucune_affirmation_ne_touche_a_la_direction(self):
        self.assertEqual(O.compte_par_grandeur().get("la direction", 0), 0)

    def test_le_decompte_se_referme(self):
        self.assertEqual(sum(O.compte_par_grandeur().values()),
                         len(O.affirmations()))

    def test_le_cumul_reprend_celui_du_volga(self):
        self.assertEqual(sum(n for _, n in O.familles()),
                         sum(n for _, n in vo.familles())
                         + len(O.affirmations()))

    def test_les_grandeurs_sont_celles_du_document(self):
        for a in O.affirmations():
            self.assertIn(a.grandeur,
                          ("la direction", "l'horloge", "le risque", "rien"),
                          a.enonce)


class TestLesSurfaces(unittest.TestCase):
    def test_les_quatre_surfaces_ont_leur_maximum_au_fond(self):
        for nom, z in (("color", O.surface_color()),
                       ("speed", O.surface_speed()),
                       ("ultima", O.surface_ultima()),
                       ("veta", O.surface_veta())):
            haut = max(max(l) for l in z)
            lignes, cols = len(z), len(z[0])
            i, j = next((i, j) for i in range(lignes) for j in range(cols)
                        if z[i][j] == haut)
            self.assertLess(i, lignes / 2 + 1, nom)
            self.assertLess(j, cols / 2 + 1, nom)

    def test_chaque_surface_est_rectangulaire(self):
        for z in (O.surface_color(), O.surface_speed(), O.surface_ultima(),
                  O.surface_veta()):
            self.assertEqual(len({len(l) for l in z}), 1)


class TestLesTables(unittest.TestCase):
    def setUp(self):
        self.tables = O.all_tables()

    def test_les_six_tables_sont_la(self):
        self.assertEqual(len(self.tables), 6)

    def test_chaque_table_a_ses_colonnes(self):
        for cle, t in self.tables.items():
            for ligne in t.rows:
                self.assertEqual(len(ligne), len(t.headers), cle)

    def test_chaque_table_a_une_note_et_une_legende(self):
        for cle, t in self.tables.items():
            self.assertTrue(t.caption, cle)
            self.assertGreater(len(t.note or ""), 120, cle)

    def test_les_valeurs_sont_des_chaines_francaises(self):
        for cle, v in O.values().items():
            self.assertIsInstance(v, str, cle)
            self.assertNotIn(".", v.replace("&nbsp;", ""), cle)

    def test_aucune_valeur_ne_publie_un_zero_trompeur(self):
        for cle, v in O.values().items():
            self.assertNotIn("100,000", v, cle)


if __name__ == "__main__":
    unittest.main()
