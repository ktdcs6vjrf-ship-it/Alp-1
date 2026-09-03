"""Les tests de la partie XXV — la saignée du delta, et les deux horloges.

Le test central de ce module n'est pas une forme fermée : c'est celui qui
exige que le désaccord entre deux guides de la même série se réduise à un
paramètre, et que ce paramètre vienne de la partie XXI plutôt que d'ici.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import charm as CH
from alp1 import figch
from alp1 import grandeurs as G
from alp1 import niveaux as nv
from alp1 import theta as th
from alp1 import vanna as va


S, V = CH.S_REF, CH.VOL_REF


class TestLaFormeFermee(unittest.TestCase):
    def test_la_saignee_egale_sa_difference_finie(self):
        for j in (1.0, 3.0, 10.0, 30.0, 90.0):
            t = j / CH.JOURS_AN
            for m in (0.90, 0.97, 1.0, 1.03, 1.10):
                self.assertAlmostEqual(CH.bleed(S * m, S, t),
                                       CH.bleed_numerique(S * m, S, t),
                                       places=6, msg=(j, m))

    def test_le_call_hors_de_la_monnaie_perd_et_l_autre_gagne(self):
        for j in (3.0, 30.0):
            t = j / CH.JOURS_AN
            self.assertLess(CH.bleed(S * 0.95, S, t), 0.0)
            self.assertGreater(CH.bleed(S * 1.05, S, t), 0.0)


class TestLAcceleration(unittest.TestCase):
    def test_l_exposant_tend_vers_moins_un(self):
        for j in (0.5, 1.0, 3.0):
            self.assertLess(abs(CH.exposant_du_pic(j) + 1.0), 0.02)

    def test_il_n_est_jamais_celui_qu_on_annonce(self):
        for j in CH.JOURS:
            self.assertGreater(CH.exposant_du_pic(j), -CH.PUISSANCE_ANNONCEE
                               + 0.4)

    def test_l_asymptote_serre_la_mesure(self):
        for j in (0.5, 1.0, 3.0, 7.0):
            t = j / CH.JOURS_AN
            self.assertLess(abs(G.bleed_du_pic(V, t)
                                / G.amplitude_asymptotique(t) - 1.0), 0.05)

    def test_elle_serre_de_mieux_en_mieux(self):
        ecarts = [abs(G.bleed_du_pic(V, j / CH.JOURS_AN)
                      / G.amplitude_asymptotique(j / CH.JOURS_AN) - 1.0)
                  for j in (60.0, 30.0, 14.0, 7.0, 3.0, 1.0)]
        for a, b in zip(ecarts, ecarts[1:]):
            self.assertLess(b, a)


class TestLePic(unittest.TestCase):
    def test_le_lieu_du_pic_est_celui_du_balaye(self):
        for j in (1.0, 7.0, 30.0, 60.0):
            t = j / CH.JOURS_AN
            m, _ = CH.pic_balaye(t)
            self.assertLess(abs(G.moneyness_du_pic(V, t) / m - 1.0), 0.003)

    def test_le_delta_au_pic_n_est_pas_celui_qu_on_annonce(self):
        for j in CH.JOURS:
            d = CH.delta_du_pic(j / CH.JOURS_AN)
            self.assertLess(d, CH.DELTA_ANNONCE - 0.05)
            self.assertGreater(d, 0.14)

    def test_le_pic_partage_la_racine_du_vanna(self):
        """La même équation du second degré, dans deux modules."""
        for j in (1.0, 30.0, 365.0):
            t = j / CH.JOURS_AN
            d1 = G.d1_du_pic(V, t)
            v = V * math.sqrt(t)
            self.assertAlmostEqual(d1 * d1 - v * d1 - 1.0, 0.0, places=12)
            self.assertAlmostEqual(d1, va.G.d1_du_pic(V, t), places=12)

    def test_le_strike_de_l_illustration_ne_porte_plus_rien(self):
        t = 1.0 / CH.JOURS_AN
        d = G.delta_comptant(S * (1.0 - CH.ECART_ILLUSTRATION), S, V, t,
                             CH.TAUX, CH.DIVIDENDE)
        self.assertLess(d, 0.01)

    def test_le_pic_se_rapproche_de_la_monnaie(self):
        ms = [G.moneyness_du_pic(V, j / CH.JOURS_AN)
              for j in (60.0, 30.0, 7.0, 1.0)]
        for a, b in zip(ms, ms[1:]):
            self.assertGreater(b, a)


class TestLaLigneALaMonnaie(unittest.TestCase):
    def test_elle_n_est_pas_nulle(self):
        for j in CH.JOURS:
            self.assertGreater(abs(CH.bleed(S, S, j / CH.JOURS_AN)), 1e-5)

    def test_elle_diverge_en_racine_inverse(self):
        for j in (0.5, 1.0, 3.0):
            self.assertLess(abs(CH.exposant_a_la_monnaie(j) + 0.5), 0.02)

    def test_le_rapport_s_effondre_avec_l_echeance(self):
        raps = [G.bleed_du_pic(V, j / CH.JOURS_AN)
                / abs(CH.bleed(S, S, j / CH.JOURS_AN))
                for j in (0.5, 1.0, 3.0, 7.0, 30.0, 60.0)]
        for a, b in zip(raps, raps[1:]):
            self.assertLess(b, a)


class TestLesDeuxHorloges(unittest.TestCase):
    def test_le_poids_vient_de_la_partie_XXI(self):
        self.assertAlmostEqual(CH.POIDS_CALIBRE,
                               th.poids_pour_apparents(1.0), places=12)
        self.assertAlmostEqual(th.jours_apparents(CH.POIDS_CALIBRE), 1.0,
                               places=9)

    def test_le_temps_de_marche_est_exact(self):
        w = CH.POIDS_CALIBRE
        self.assertAlmostEqual(CH.temps_de_marche(0.0, 10.0, w), 0.0,
                               places=12)
        self.assertAlmostEqual(CH.temps_de_marche(4.0, 10.0, w), 4.0,
                               places=12)
        self.assertAlmostEqual(CH.temps_de_marche(7.0, 10.0, w),
                               4.0 + 3.0 * w, places=12)
        self.assertAlmostEqual(CH.temps_de_marche(10.0, 10.0, w),
                               7.0 + 3.0 * w, places=12)

    def test_a_poids_un_on_retrouve_le_calendrier(self):
        for j in (5.0, 10.0, 30.0):
            for m in (0.97, 1.0, 1.03):
                self.assertAlmostEqual(CH.facteur_du_calendrier(m, j, 1.0),
                                       1.0, places=6, msg=(j, m))

    def test_le_calendrier_surestime_partout_ailleurs(self):
        for w in (0.05, 0.2566, 0.5, 0.8):
            for j in (7.0, 14.0, 30.0):
                self.assertGreater(CH.facteur_du_calendrier(0.97, j, w), 1.0)

    def test_le_facteur_est_le_plus_grand_sur_les_ailes(self):
        for j in (7.0, 14.0, 30.0):
            self.assertGreater(CH.facteur_du_calendrier(0.97, j),
                               CH.facteur_du_calendrier(1.0, j))
            self.assertGreater(CH.facteur_du_calendrier(1.03, j),
                               CH.facteur_du_calendrier(1.0, j))

    def test_le_facteur_calibre_est_de_l_ordre_de_trois(self):
        f = CH.facteur_du_calendrier(0.97, 10.0)
        self.assertGreater(f, 2.0)
        self.assertLess(f, 5.0)

    def test_le_chemin_reproduit_la_saignee_sur_le_week_end(self):
        """Le chemin de la planche et le saut de la table sont le même objet."""
        for w in (1.0, CH.POIDS_CALIBRE):
            for m in (0.97, 1.03):
                a = (CH.delta_sur_horloge(m, CH.DEBUT_WEEKEND
                                          + CH.JOURS_WEEKEND, 10.0, w)
                     - CH.delta_sur_horloge(m, CH.DEBUT_WEEKEND, 10.0, w))
                self.assertLess(abs(a), 0.30)
                self.assertGreater(abs(a), 1e-4)

    def test_le_chemin_a_poids_un_est_le_chemin_calendaire(self):
        for e in (0.0, 2.0, 5.0, 8.0):
            for m in (0.97, 1.0, 1.03):
                self.assertAlmostEqual(
                    CH.delta_sur_horloge(m, e, 10.0, 1.0),
                    G.delta_comptant(S * m, S, V,
                                     max(1e-9, (10.0 - e) / CH.JOURS_AN),
                                     CH.TAUX, CH.DIVIDENDE), places=6)


class TestLeCout(unittest.TestCase):
    def test_le_seuil_mesure_depasse_celui_qu_on_annonce(self):
        self.assertGreater(CH.echeance_du_seuil(), CH.SEUIL_ANNONCE)

    def test_a_deux_semaines_le_cout_depasse_encore_la_friction(self):
        self.assertGreater(
            CH.cout_du_delta_du_soir(CH.SEUIL_ANNONCE) / CH.FRICTION, 1.0)

    def test_le_seuil_est_bien_le_lieu_de_l_egalite(self):
        j = CH.echeance_du_seuil()
        self.assertAlmostEqual(CH.cout_du_delta_du_soir(j), CH.FRICTION,
                               places=5)

    def test_le_cout_decroit_avec_l_echeance(self):
        vals = [CH.cout_du_delta_du_soir(j) for j in CH.JOURS_COUT]
        for a, b in zip(vals, vals[1:]):
            self.assertLess(b, a)

    def test_il_est_bien_plus_petit_a_la_monnaie(self):
        for j in (7.0, 14.0, 30.0):
            self.assertLess(CH.cout_du_delta_du_soir(j, 1.0),
                            0.25 * CH.cout_du_delta_du_soir(j))

    def test_la_friction_est_celle_de_la_geometrie_declaree(self):
        from alp1.costs import COST_BASE, ES
        self.assertAlmostEqual(CH.FRICTION, COST_BASE.friction_points(ES),
                               places=12)


class TestLeStrangle(unittest.TestCase):
    def test_la_forme_fermee_egale_la_mesure_a_portage_nul(self):
        for j in CH.JOURS_STR:
            for d in CH.DELTAS:
                self.assertAlmostEqual(CH.strangle(d, j, V, 0.0, 0.0)[2],
                                       CH.strangle_ferme(d, j), places=8,
                                       msg=(j, d))

    def test_le_net_n_est_nul_nulle_part(self):
        for j in (5.0, 14.0, 60.0, 180.0):
            for d in (0.05, 0.15, 0.25, 0.35, 0.45):
                self.assertLess(CH.strangle(d, j)[2], -1e-6, msg=(j, d))

    def test_le_livre_devient_plus_court(self):
        """Le call perd plus de delta que le put n'en regagne."""
        for j in CH.JOURS_STR:
            a, b, net, _ = CH.strangle(0.25, j)
            self.assertLess(a, 0.0)
            self.assertGreater(b, 0.0)
            self.assertGreater(abs(a), abs(b))

    def test_la_part_non_compensee_croit_avec_le_delta(self):
        for j in CH.JOURS_STR:
            parts = [abs(CH.strangle(d, j)[2]) / CH.strangle(d, j)[3]
                     for d in CH.DELTAS]
            for a, b in zip(parts, parts[1:]):
                self.assertGreater(b, a)

    def test_le_portage_amplifie_sans_creer(self):
        for j in (14.0, 90.0):
            avec = abs(CH.strangle(0.25, j)[2])
            sans = abs(CH.strangle(0.25, j, V, 0.0, 0.0)[2])
            self.assertGreater(avec, sans)
            self.assertGreater(sans, 0.0)

    def test_le_vertical_ne_compense_rien_non_plus(self):
        for j in CH.JOURS_STR:
            net, brut = CH.vertical(0.40, 0.20, j)
            self.assertGreater(abs(net) / brut, 0.20)


class TestLeDecompte(unittest.TestCase):
    def test_aucune_affirmation_ne_touche_a_la_direction(self):
        self.assertEqual(CH.compte_par_grandeur().get("la direction", 0), 0)

    def test_le_compte_se_referme(self):
        self.assertEqual(sum(CH.compte_par_grandeur().values()),
                         len(CH.affirmations()))

    def test_les_sept_familles_sont_comptees_dans_leurs_modules(self):
        fam = dict(CH.familles())
        self.assertEqual(fam["Vanna, partie XXIV"], len(va.affirmations()))
        self.assertEqual(fam["Charm, partie XXV"], len(CH.affirmations()))
        self.assertEqual(sum(n for _, n in CH.familles()),
                         sum(n for _, n in va.familles())
                         + len(CH.affirmations()))

    def test_chaque_affirmation_porte_sa_mesure(self):
        for a in CH.affirmations():
            self.assertGreater(len(a.enonce), 20)
            self.assertGreater(len(a.mesure), 20)
            self.assertIn(a.grandeur,
                          ("l'horloge", "le risque", "rien", "la direction"))


class TestLesSurfaces(unittest.TestCase):
    def test_les_quatre_reliefs_ont_leur_maximum_au_fond(self):
        for nom in ("surface_saignee", "surface_horloge", "surface_cout",
                    "surface_strangle"):
            z = getattr(CH, nom)()
            haut = max(max(l) for l in z)
            self.assertAlmostEqual(z[0][0], haut, places=9, msg=nom)

    def test_les_reliefs_sont_carres_et_pleins(self):
        for nom in ("surface_saignee", "surface_horloge", "surface_cout",
                    "surface_strangle"):
            z = getattr(CH, nom)()
            self.assertEqual(len(z), 6, nom)
            for l in z:
                self.assertEqual(len(l), 6, nom)
                for v in l:
                    self.assertTrue(math.isfinite(v), nom)

    def test_le_relief_des_horloges_a_pour_plancher_la_lecture_du_guide(self):
        z = CH.surface_horloge()
        for v in z[-1]:
            self.assertAlmostEqual(v, 1.0, places=5)
        for l in z[:-1]:
            for v in l:
                self.assertGreaterEqual(v, 1.0)


class TestLesTables(unittest.TestCase):
    def setUp(self):
        self.tables = CH.all_tables()

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
        for cle, v in CH.values().items():
            self.assertIsInstance(v, str, cle)
            self.assertNotIn(".", v.replace("&nbsp;", ""), cle)


class TestLesPlanches(unittest.TestCase):
    def setUp(self):
        self.rendus = figch.render_all()

    def test_les_quinze_planches_sont_la(self):
        self.assertEqual(len(self.rendus), 15)

    def test_aucune_couleur_n_est_ecrite_en_dur(self):
        for cle, svg in self.rendus.items():
            self.assertEqual(re.findall(r"#[0-9a-fA-F]{6}", svg), [], cle)

    def test_aucune_entite_html_n_est_ecrite(self):
        for cle, svg in self.rendus.items():
            self.assertEqual(re.findall(r"&#\d+;", svg), [], cle)

    def test_aucun_libelle_aria_ne_porte_d_apostrophe(self):
        for cle, svg in self.rendus.items():
            for aria in re.findall(r'aria-label="([^"]*)"', svg):
                self.assertNotIn("'", aria, cle)
                self.assertNotIn("’", aria, cle)

    def test_aucun_pied_ne_porte_de_marque(self):
        for cle, svg in self.rendus.items():
            for classe in ("lg cap", "lg keep"):
                for texte in re.findall(
                        r'<text[^>]*class="' + classe + r'"[^>]*>([^<]*)<',
                        svg):
                    self.assertNotIn("**", texte, cle)
                    self.assertNotIn("*", texte, cle)
                    self.assertNotIn("`", texte, cle)

    def test_les_quatre_reliefs_portent_leur_echine(self):
        for cle in ("chreliefs", "chreliefh", "chreliefc", "chreliefstr"):
            self.assertIn('class="post"', self.rendus[cle], cle)
            self.assertIn('class="nuage', self.rendus[cle], cle)

    def test_toutes_les_graduations_tombent_dans_leur_domaine(self):
        from alp1.figterm import Panel

        hits = []
        og_y, og_x = Panel.grid_y, Panel.grid_x

        def enveloppe(nom, orig, lo_a, hi_a):
            def f(self, ticks, *a, **k):
                lo, hi = sorted((getattr(self, lo_a), getattr(self, hi_a)))
                dehors = [t for t in ticks
                          if not (lo - 1e-9 <= t <= hi + 1e-9)]
                if dehors:
                    hits.append((nom, self.title, dehors, (lo, hi)))
                return orig(self, ticks, *a, **k)
            return f

        Panel.grid_y = enveloppe("grid_y", og_y, "y0", "y1")
        Panel.grid_x = enveloppe("grid_x", og_x, "x0", "x1")
        try:
            figch.render_all()
        finally:
            Panel.grid_y, Panel.grid_x = og_y, og_x
        self.assertEqual(hits, [])

    def test_aucun_trace_n_est_reduit_par_le_decoupage(self):
        from alp1.figterm import Panel

        hits = []
        og = Panel.path

        def f(self, pts, *a, **k):
            pts = list(pts)
            dedans = [p for p in pts if self._in_domain(*p)]
            if len(pts) > 2 and len(dedans) < 0.5 * len(pts):
                hits.append((self.title, len(pts), len(dedans)))
            return og(self, pts, *a, **k)

        Panel.path = f
        try:
            figch.render_all()
        finally:
            Panel.path = og
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
