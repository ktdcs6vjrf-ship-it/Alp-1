"""Les tests de la feuille de spéculation.

Trois tests portent ici plus que les autres. Le premier exige la **symétrie
exacte des deux sens à dérive nulle** : elle est la propriété qui rend tout le
reste lisible, puisqu'elle garantit que le moindre écart publié est la dérive
et rien d'autre. Le deuxième exige que `a/(a+b)` tienne **exactement** tant que
l'objectif reste dans la portée de la séance, et qu'il décroche au-delà — sans
quoi le module publierait le théorème là où il ne s'applique plus. Le
troisième exige que l'horizon optimal tombe là où la portée vaut un, ce qui
est le seul résultat négociable de la partie.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import concepts as C
from alp1 import quant as q
from alp1 import seuil
from alp1 import speculation as S


class TestLaSymetrie(unittest.TestCase):
    def test_les_deux_sens_coincident_a_derive_nulle(self):
        for pct in S.GEOMETRIES:
            h = S.lire(pct, 0.0, 1)
            b = S.lire(pct, 0.0, -1)
            self.assertEqual(h.p_objectif, b.p_objectif, pct)
            self.assertEqual(h.p_stop, b.p_stop, pct)
            self.assertEqual(h.esperance_r, b.esperance_r, pct)

    def test_l_ecart_directionnel_est_nul_a_derive_nulle(self):
        for t in (5.0, 60.0, 102.0, 390.0):
            self.assertEqual(S.ecart_directionnel(t, 0.0), 0.0, t)

    def test_la_derive_favorise_le_sens_de_son_signe(self):
        for pct in S.GEOMETRIES:
            for d in S.DERIVES[1:]:
                self.assertGreater(S.lire(pct, d, 1).p_objectif,
                                   S.lire(pct, d, -1).p_objectif, (pct, d))

    def test_les_trois_issues_font_un(self):
        for pct in S.GEOMETRIES:
            for d in S.DERIVES:
                for sens in S.SENS:
                    i = S.lire(pct, d, sens)
                    self.assertAlmostEqual(
                        i.p_objectif + i.p_stop + i.p_ouvert, 1.0, places=9,
                        msg=(pct, d, sens))


class TestLePortee(unittest.TestCase):
    """`a/(a+b)` ne tient que tant que la séance ne borne rien."""

    def test_le_theoreme_est_exact_quand_l_objectif_tient(self):
        for t in (5.0, 15.0):
            a = S.SIGMA_MIN * math.sqrt(t)
            b = C.RR_LECTURE * a
            p = S._issues(a, b, 0.0, S.SEANCE_MIN)[0]
            self.assertAlmostEqual(p, 1.0 / (1.0 + C.RR_LECTURE), places=4,
                                   msg=t)

    def test_il_decroche_quand_elle_borne(self):
        a = S.SIGMA_MIN * math.sqrt(S.SEANCE_MIN)
        b = C.RR_LECTURE * a
        p = S._issues(a, b, 0.0, S.SEANCE_MIN)[0]
        self.assertLess(p, 0.25 / (1.0 + C.RR_LECTURE))

    def test_la_portee_croit_avec_le_stop(self):
        vals = [S.portee_de_seance(p) for p in seuil.SURFACE_STOP_PCT]
        for x, y in zip(vals, vals[1:]):
            self.assertLess(x, y)

    def test_l_objectif_declare_sort_de_la_seance_des_le_stop_moyen(self):
        self.assertLess(S.portee_de_seance(S.GEOMETRIES[0]), 1.0)
        self.assertGreater(S.portee_de_seance(S.GEOMETRIES[1]), 1.0)
        self.assertGreater(S.portee_de_seance(S.GEOMETRIES[2]), 5.0)

    def test_le_rapport_atteignable_decroit_avec_le_stop(self):
        vals = [S.rr_atteignable(p, 0.05) for p in seuil.SURFACE_STOP_PCT]
        for x, y in zip(vals, vals[1:]):
            self.assertGreaterEqual(x, y)

    def test_il_rend_bien_la_probabilite_demandee(self):
        """Exactement au seuil quand la racine est intérieure, au-dessus sinon.

        Au stop le plus serré la bissection bute sur sa borne haute : aucun
        rapport de la fenêtre ne fait descendre la probabilité jusqu'à un
        pour cent. Le module rend alors la borne, ce qui est le bon
        comportement — mais le test doit le dire plutôt que de l'ignorer.
        """
        for pct in (0.010, 0.050, 0.150):
            for seuil_p in (0.01, 0.05, 0.10):
                rr = S.rr_atteignable(pct, seuil_p)
                p = S.lire(pct, 0.0, 1, rr).p_objectif
                self.assertGreaterEqual(p, seuil_p - 1e-6, (pct, seuil_p))
                if rr < 59.0:
                    self.assertAlmostEqual(p, seuil_p, places=3,
                                           msg=(pct, seuil_p))


class TestLesDeuxRoutes(unittest.TestCase):
    """Le seuil borné par la séance, et celui qui ne l'est pas."""

    def test_la_route_non_bornee_est_toujours_la_plus_optimiste(self):
        for pct in seuil.SURFACE_STOP_PCT:
            self.assertLess(S.derive_non_bornee(pct), S.derive_de_wald(pct),
                            pct)

    def test_l_ecart_croit_quand_la_seance_borne(self):
        vals = [S.ecart_des_routes(p) for p in seuil.SURFACE_STOP_PCT]
        for x, y in zip(vals, vals[1:]):
            self.assertLess(x, y)

    def test_le_raccourci_ne_retourne_pas_le_verdict_mais_le_rend_discutable(
            self):
        """Une affirmation écrite d'avance, et réfutée par la mesure.

        On attendait que le raccourci non borné range la géométrie déclarée
        dans le domaine plausible quand la route bornée l'en exclut — un
        retournement de verdict. Il n'en est rien : les deux routes excluent
        la géométrie déclarée sur toute la grille. Ce que le raccourci change
        est l'ampleur du dépassement, et c'est déjà beaucoup : dix-sept pour
        cent au-dessus du plafond se discute, un facteur deux et demi non.
        """
        pct = S.GEOMETRIES[0]
        haut = seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]
        self.assertFalse(S.dans_le_domaine(S.derive_de_wald(pct)))
        self.assertFalse(S.dans_le_domaine(S.derive_non_bornee(pct)))
        self.assertLess(S.derive_non_bornee(pct) / haut, 1.25)
        self.assertGreater(S.derive_de_wald(pct) / haut, 2.0)

    def test_les_deux_routes_s_accordent_sur_le_verdict_partout(self):
        for pct in seuil.SURFACE_STOP_PCT:
            self.assertEqual(S.dans_le_domaine(S.derive_de_wald(pct)),
                             S.dans_le_domaine(S.derive_non_bornee(pct)), pct)

    def test_wald_est_celui_de_la_partie_X(self):
        for pct in seuil.SURFACE_STOP_PCT:
            self.assertEqual(S.derive_de_wald(pct),
                             seuil.geometry(pct).break_even_per_hour, pct)


class TestLHorizonOptimal(unittest.TestCase):
    def test_l_ecart_passe_par_un_maximum_dans_la_seance(self):
        opt = S.horizon_optimal()
        pic = S.ecart_directionnel(opt)
        for t in (5.0, 30.0, 60.0, 240.0, 390.0):
            self.assertLessEqual(S.ecart_directionnel(t), pic + 1e-9, t)

    def test_l_objectif_optimal_vaut_un_ecart_type_de_seance(self):
        """Le fait de la partie, et il n'est pas un artefact de balayage."""
        self.assertAlmostEqual(S.portee_de_l_optimum(), 1.0, delta=0.05)

    def test_le_balayage_est_stable_au_pas_dix_fois_plus_fin(self):
        self.assertAlmostEqual(S.horizon_optimal(), S.horizon_optimal(n=7800),
                               delta=1.0)

    def test_il_tombe_dans_la_seance(self):
        self.assertGreater(S.horizon_optimal(), 30.0)
        self.assertLess(S.horizon_optimal(), S.SEANCE_MIN)

    def test_la_frontiere_est_reelle(self):
        """Au-delà de la séance, l'écart remonte — l'optimum est contraint."""
        self.assertGreater(S.ecart_directionnel(780.0),
                           S.ecart_directionnel(390.0))


class TestLesVerdicts(unittest.TestCase):
    def test_aucune_des_trois_geometries_ne_passe_les_deux_conditions(self):
        for pct in S.GEOMETRIES:
            self.assertNotEqual(S.verdict(pct), "négociable", pct)

    def test_le_stop_declare_echoue_sur_la_derive(self):
        self.assertIn("domaine", S.verdict(S.GEOMETRIES[0]))

    def test_les_stops_elargis_echouent_sur_la_portee(self):
        for pct in S.GEOMETRIES[1:]:
            self.assertIn("portée", S.verdict(pct))

    def test_l_esperance_a_derive_nulle_vaut_moins_c_sur_a(self):
        for pct in S.GEOMETRIES:
            g = seuil.geometry(pct)
            self.assertAlmostEqual(S.lire(pct).esperance_r,
                                   -g.friction_points / g.stop_points,
                                   places=12, msg=pct)


class TestLesLectures(unittest.TestCase):
    def test_les_quinze_lectures_y_sont(self):
        self.assertEqual(len(S.lignes()), len(C.CATALOGUE))

    def test_elles_suivent_l_ordre_calcule_du_catalogue(self):
        self.assertEqual([l.cle for l in S.lignes()],
                         [l.cle for l in C.ordre()])

    def test_les_courtes_rendent_exactement_le_theoreme(self):
        for lg in S.lignes():
            if lg.portee < 0.40:
                self.assertAlmostEqual(lg.p_nulle,
                                       1.0 / (1.0 + C.RR_LECTURE), places=4,
                                       msg=lg.cle)

    def test_la_probabilite_decroit_avec_la_portee(self):
        par_portee = sorted(S.lignes(), key=lambda l: l.portee)
        for x, y in zip(par_portee, par_portee[1:]):
            self.assertGreaterEqual(x.p_nulle + 1e-9, y.p_nulle,
                                    (x.cle, y.cle))

    def test_la_derive_requise_vient_du_catalogue(self):
        for lg in S.lignes():
            self.assertEqual(lg.derive_requise,
                             C.exigence(lg.cle).derive_requise, lg.cle)


class TestLesBandeaux(unittest.TestCase):
    def test_aucune_famille_ne_declare_un_avantage(self):
        """Le zéro vient des modules qui l'ont mesuré, pas d'ici."""
        for cle, h in S.HYPOTHESES.items():
            self.assertEqual(h.avantage, 0.0, cle)
            self.assertTrue(h.source, cle)
            self.assertTrue(h.objet, cle)

    def test_chaque_bandeau_est_symetrique_a_derive_nulle(self):
        for cle in S.HYPOTHESES:
            self.assertTrue(S.bandeau(cle).symetrique, cle)

    def test_les_familles_sans_direction_prennent_la_geometrie_declaree(self):
        b = S.bandeau("figvo")
        g = seuil.geometry(S.GEOMETRIES[0])
        self.assertAlmostEqual(b.stop, g.stop_points, places=12)

    def test_le_prefixe_d_une_figure_retrouve_son_module(self):
        for cle, attendu in (("vosourire", "figvo"), ("chreliefs", "figch"),
                             ("varelief", "figva"), ("setfoot", "figsetup"),
                             ("catordre", "figcat"), ("nvbande", "fignv")):
            self.assertEqual(S.module_d_une_figure(cle), attendu, cle)

    def test_chaque_module_declare_est_atteignable_par_un_prefixe(self):
        modules = {m for _, m in S._PREFIXES}
        self.assertEqual(modules, set(S.HYPOTHESES))


class TestLesSurfaces(unittest.TestCase):
    def test_les_quatre_surfaces_sont_rectangulaires(self):
        for z in (S.surface_survie(), S.surface_portee(),
                  S.surface_ecart(), S.surface_esperance()):
            self.assertEqual(len({len(l) for l in z}), 1)

    def test_le_maximum_se_met_au_fond(self):
        for nom, z in (("survie", S.surface_survie()),
                       ("portee", S.surface_portee()),
                       ("ecart", S.surface_ecart()),
                       ("esperance", S.surface_esperance())):
            haut = max(max(l) for l in z)
            lignes, cols = len(z), len(z[0])
            i, j = next((i, j) for i in range(lignes) for j in range(cols)
                        if z[i][j] == haut)
            self.assertLess(i, lignes / 2 + 1, nom)
            self.assertLess(j, cols / 2 + 1, nom)


    def test_la_survie_vaut_un_la_ou_le_theoreme_s_applique(self):
        z = S.surface_survie()
        self.assertAlmostEqual(z[0][0], 1.0, places=3)

    def test_elle_s_effondre_au_coin_ou_la_seance_borne(self):
        z = S.surface_survie()
        self.assertLess(z[-1][-1], 0.05)

    def test_elle_ne_depasse_jamais_un(self):
        for ligne in S.surface_survie():
            for v in ligne:
                self.assertLessEqual(v, 1.0 + 1e-9)


class TestLesTables(unittest.TestCase):
    def setUp(self):
        self.tables = S.all_tables()

    def test_les_neuf_tables_sont_la(self):
        self.assertEqual(len(self.tables), 9)

    def test_chaque_table_a_ses_colonnes(self):
        for cle, t in self.tables.items():
            for ligne in t.rows:
                self.assertEqual(len(ligne), len(t.headers), cle)

    def test_chaque_table_a_une_note_et_une_legende(self):
        for cle, t in self.tables.items():
            self.assertTrue(t.caption, cle)
            self.assertGreater(len(t.note or ""), 120, cle)

    def test_les_valeurs_sont_des_chaines_francaises(self):
        for cle, v in S.values().items():
            self.assertIsInstance(v, str, cle)
            self.assertNotIn(".", v.replace("&nbsp;", ""), cle)

    def test_aucune_note_ne_publie_un_zero_trompeur(self):
        """Un « 0,00 » efface un résultat au lieu de le montrer."""
        for cle, t in self.tables.items():
            self.assertNotIn("0,00 %,", t.note or "", cle)


if __name__ == "__main__":
    unittest.main()
