"""Les tests de la partie XXIII — le taux, et la variable qu'on tient fixe.

Chaque forme fermée y est contrôlée contre une route indépendante, comme la
règle du dépôt l'exige sans exception : `ρ = KTe^{−rT}N(d₂)` contre une
différence finie à spot fixe, `−T·V` contre une différence finie à forward
fixe (le spot compensé de `e^{−hT}`), et le lieu du maximum contre un balayage.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import figrh
from alp1 import grandeurs as G
from alp1 import niveaux as nv
from alp1 import rho as R
from alp1 import theta as th
from alp1 import vega as vg


S, V = R.S_REF, R.VOL_REF


class TestLesFormesFermees(unittest.TestCase):
    def test_le_rho_ferme_egale_la_difference_finie(self):
        for j in (7.0, 30.0, 180.0, 365.0, 1095.0):
            t = j / R.JOURS_AN
            for m in (0.85, 1.0, 1.15):
                self.assertAlmostEqual(
                    R.rho_call(S * m, S, V, t),
                    R.rho_numerique(S * m, S, V, t), places=3)

    def test_la_parite_relie_les_deux_rhos(self):
        """`ρ_call − ρ_put = KTe^{−rT}` — la parité, dérivée en taux."""
        for j in (30.0, 365.0, 1095.0):
            t = j / R.JOURS_AN
            self.assertAlmostEqual(
                R.rho_call(S, S, V, t) - R.rho_put(S, S, V, t),
                S * t * math.exp(-R.TAUX * t), places=8)

    def test_le_call_gagne_et_le_put_perd(self):
        for j in R.ECHEANCES:
            t = j / R.JOURS_AN
            self.assertGreater(R.rho_call(S, S, V, t), 0.0)
            self.assertLess(R.rho_put(S, S, V, t), 0.0)

    def test_le_rho_forward_est_moins_t_fois_la_valeur(self):
        for j in (7.0, 90.0, 365.0, 1095.0):
            t = j / R.JOURS_AN
            self.assertAlmostEqual(
                R.rho_forward_fixe(S, S, V, t),
                R.rho_forward_numerique(S, S, V, t), places=5)

    def test_les_deux_rhos_sont_de_signes_opposes(self):
        """Le résultat de la section IV, exigé du module et non du texte."""
        for j in R.ECHEANCES:
            t = j / R.JOURS_AN
            self.assertGreater(R.rho_par_point(S, S, V, t), 0.0)
            self.assertLess(R.rho_forward_fixe(S, S, V, t), 0.0)

    def test_le_rho_ne_depasse_jamais_son_plafond(self):
        for j in (30.0, 365.0, 1825.0):
            t = j / R.JOURS_AN
            for m in (0.5, 1.0, 2.0, 5.0):
                self.assertLessEqual(R.rho_call(S * m, S, V, t),
                                     R.rho_plafond(S, t) + 1e-9)

    def test_le_rho_tend_vers_son_plafond_dans_la_monnaie(self):
        t = R.T_FINANCEE
        self.assertGreater(R.rho_call(5 * S, S, V, t) / R.rho_plafond(S, t),
                           0.999)

    def test_le_rho_est_nul_a_echeance_nulle(self):
        self.assertEqual(R.rho_call(S, S, V, 0.0), 0.0)
        self.assertEqual(R.rho_put(S, S, V, 0.0), 0.0)
        self.assertEqual(R.rho_forward_fixe(S, S, V, 0.0), 0.0)


class TestLExposant(unittest.TestCase):
    def test_l_exposant_vaut_un_aux_echeances_courtes(self):
        for j in (3.0, 7.0, 21.0):
            self.assertAlmostEqual(R.exposant_effectif(j), 1.0, places=1)

    def test_l_exposant_decroit_avec_l_echeance(self):
        vals = [R.exposant_effectif(j) for j in (90.0, 365.0, 730.0, 1825.0)]
        for a, b in zip(vals, vals[1:]):
            self.assertGreater(a, b)

    def test_l_exposant_s_annule_au_maximum(self):
        pic = R.echeance_du_pic()
        self.assertAlmostEqual(R.exposant_effectif(pic * R.JOURS_AN), 0.0,
                               places=2)

    def test_le_maximum_est_celui_d_un_balayage(self):
        """La forme fermée n'en est pas une ici : la bissection se contrôle."""
        js = [0.5 + 0.05 * i for i in range(1000)]
        meilleur = max(js, key=lambda a: R.rho_call(S, S, V, a))
        self.assertLess(abs(meilleur - R.echeance_du_pic()), 0.1)

    def test_le_maximum_vaut_l_inverse_du_taux_en_un_seul_point(self):
        """`r* = q + σ²/2`, et la forme fermée se contrôle sur trois vols."""
        for vol in (0.15, 0.20, 0.25, 0.30):
            r = R.taux_du_pic_exact(vol, R.DIVIDENDE)
            self.assertAlmostEqual(
                R.echeance_du_pic(S, S, vol, r, R.DIVIDENDE), 1.0 / r,
                places=6)

    def test_le_maximum_n_est_pas_l_inverse_du_taux_ailleurs(self):
        """La phrase du premier jet, refusée par la mesure."""
        pic = R.echeance_du_pic(S, S, V, 0.02, R.DIVIDENDE)
        self.assertGreater(abs(pic / 50.0 - 1.0), 0.30)

    def test_le_maximum_vient_plus_tot_sous_le_taux_exact(self):
        r_etoile = R.taux_du_pic_exact()
        for r in (0.01, 0.02, 0.03):
            self.assertLess(R.echeance_du_pic(S, S, V, r, R.DIVIDENDE),
                            1.0 / r)
        for r in (0.06, 0.08):
            self.assertGreater(R.echeance_du_pic(S, S, V, r, R.DIVIDENDE),
                               1.0 / r)
        self.assertLess(0.03, r_etoile)
        self.assertLess(r_etoile, 0.06)

    def test_le_maximum_recule_quand_le_taux_baisse(self):
        vals = [R.echeance_du_pic(S, S, V, r, R.DIVIDENDE)
                for r in (0.01, 0.02, 0.04, 0.08)]
        for a, b in zip(vals, vals[1:]):
            self.assertGreater(a, b)

    def test_l_ecart_croit_avec_la_tolerance(self):
        self.assertLess(R.echeance_de_l_ecart(0.05),
                        R.echeance_de_l_ecart(0.10))

    def test_l_ecart_est_bien_celui_qu_il_annonce(self):
        for tol in (0.05, 0.10):
            j = R.echeance_de_l_ecart(tol)
            ref = (R.rho_call(S, S, V, 30.0 / R.JOURS_AN)
                   / (30.0 / R.JOURS_AN))
            t = j / R.JOURS_AN
            self.assertAlmostEqual(
                abs(R.rho_call(S, S, V, t) / (ref * t) - 1.0), tol, places=3)

    def test_le_rapport_publie_n_est_pas_deux_ordres(self):
        self.assertLess(R.rapport_des_echeances(), 30.0)
        self.assertGreater(R.rapport_des_echeances(), 15.0)


class TestLeCroisement(unittest.TestCase):
    def test_les_trois_routes_ne_donnent_pas_le_meme_croisement(self):
        a = R.croisement_unite()
        c = R.croisement_structure()
        self.assertLess(a, c)
        self.assertGreater(R.croisement_brut(), c)

    def test_le_croisement_unite_est_un_vrai_croisement(self):
        j = R.croisement_unite()
        self.assertAlmostEqual(
            R.rho_par_point(S, S, V, j / R.JOURS_AN),
            vg.vega_par_point(S, S, V, j / R.JOURS_AN, R.TAUX, R.DIVIDENDE),
            places=5)

    def test_le_croisement_structure_est_un_vrai_croisement(self):
        j = R.croisement_structure()
        self.assertAlmostEqual(R.risque_rho(j), R.risque_vega(j), places=5)

    def test_le_croisement_recule_quand_le_taux_est_calme(self):
        vals = [R.croisement_structure(s) for s in R.DISPERSIONS_TAUX]
        for a, b in zip(vals, vals[1:]):
            self.assertGreater(a, b)

    def test_la_dispersion_de_l_implicite_vient_de_la_partie_precedente(self):
        self.assertAlmostEqual(R.DISPERSION_VOL,
                               100.0 * vg.ecart_type_implicite(), places=9)

    def test_le_poids_de_terme_abaisse_le_risque_vega(self):
        for j in (365.0, 730.0, 1825.0):
            self.assertLess(R.risque_vega(j, structure=True),
                            R.risque_vega(j, structure=False))

    def test_le_poids_de_terme_est_neutre_au_tenor_de_reference(self):
        self.assertAlmostEqual(R.risque_vega(vg.TENOR_REF, structure=True),
                               R.risque_vega(vg.TENOR_REF, structure=False),
                               places=9)


class TestLeRegime(unittest.TestCase):
    def test_la_sensibilite_bouge_peu_avec_le_niveau_du_taux(self):
        bas = R.rho_par_point(S, S, V, 2.0, 0.0, R.DIVIDENDE)
        haut = R.rho_par_point(S, S, V, 2.0, 0.08, R.DIVIDENDE)
        self.assertLess(haut / bas, 1.35)
        self.assertGreater(haut / bas, 1.05)

    def test_le_rho_croit_avec_le_taux(self):
        vals = [R.rho_par_point(S, S, V, 2.0, r, R.DIVIDENDE)
                for r in R.TAUX_BALAYES]
        for a, b in zip(vals, vals[1:]):
            self.assertGreater(b, a)

    def test_le_maximum_existe_encore_a_taux_nul(self):
        """Le piège de la section I : ce n'est pas l'escompte seul.

        La probabilité d'exercice d'une option à la monnaie décroît avec
        l'échéance dès que `r < q + σ²/2`, donc la courbe se retourne même
        sans escompte. La première version du module affirmait le contraire.
        """
        pic = R.echeance_du_pic(S, S, V, 1e-9, R.DIVIDENDE)
        self.assertGreater(pic, 20.0)
        self.assertLess(pic, 200.0)
        self.assertGreater(R.rho_call(S, S, V, pic, 0.0, R.DIVIDENDE),
                           R.rho_call(S, S, V, 2.5 * pic, 0.0, R.DIVIDENDE))


class TestLActionFinancee(unittest.TestCase):
    def test_le_call_converge_vers_l_action_financee(self):
        ecarts = [abs(th.call(S * m, S, V, R.T_FINANCEE)
                      - R.action_financee(S * m, S, R.T_FINANCEE))
                  for m in R.MONEYNESS]
        for a, b in zip(ecarts, ecarts[1:]):
            self.assertLess(b, a)

    def test_l_ecart_a_deux_fois_le_strike_est_sous_un_pour_cent(self):
        c = th.call(2 * S, S, V, R.T_FINANCEE)
        f = R.action_financee(2 * S, S, R.T_FINANCEE)
        self.assertLess(100.0 * (c - f) / c, 1.0)

    def test_l_action_financee_borne_le_call_par_le_bas(self):
        for m in R.MONEYNESS:
            self.assertGreaterEqual(
                th.call(S * m, S, V, R.T_FINANCEE),
                R.action_financee(S * m, S, R.T_FINANCEE))

    def test_la_part_du_plafond_est_la_probabilite_d_exercice(self):
        t = R.T_FINANCEE
        for m in (0.8, 1.0, 1.5, 2.5):
            _, d2 = G._d(S * m, S, V, t, R.TAUX, R.DIVIDENDE)
            self.assertAlmostEqual(
                R.rho_call(S * m, S, V, t) / R.rho_plafond(S, t),
                nv.norm_cdf(d2) if hasattr(nv, "norm_cdf") else
                __import__("alp1.costs", fromlist=["norm_cdf"]).norm_cdf(d2),
                places=9)


class TestLeCout(unittest.TestCase):
    def test_le_cout_intrajournalier_est_negligeable(self):
        self.assertGreater(R.FRICTION / R.cout_de_rho(R.JOURS_INTRA), 1000.0)

    def test_le_cout_croit_avec_l_echeance_avant_le_maximum(self):
        vals = [R.cout_de_rho(j) for j in (1.0, 30.0, 365.0, 1825.0)]
        for a, b in zip(vals, vals[1:]):
            self.assertGreater(b, a)

    def test_la_dispersion_croit_en_racine_du_nombre_de_seances(self):
        self.assertAlmostEqual(R.dispersion_seance(0.30, 4.0)
                               / R.dispersion_seance(0.30, 1.0), 2.0,
                               places=9)

    def test_aucune_echeance_n_egale_la_friction_en_regime_calme(self):
        self.assertFalse(math.isfinite(R.echeance_du_cout(0.10)))
        self.assertFalse(math.isfinite(R.echeance_du_cout(0.30)))

    def test_une_echeance_l_egale_en_regime_agite(self):
        j = R.echeance_du_cout(0.60)
        self.assertTrue(math.isfinite(j))
        self.assertAlmostEqual(R.cout_de_rho(j, 0.60), R.FRICTION, places=5)

    def test_la_friction_est_celle_de_la_geometrie_declaree(self):
        from alp1.costs import COST_BASE, ES
        self.assertAlmostEqual(R.FRICTION, COST_BASE.friction_points(ES),
                               places=12)


class TestLeDecompte(unittest.TestCase):
    def test_aucune_affirmation_ne_touche_a_la_direction(self):
        """Le résultat de la partie, exigé du module et non de sa prose."""
        self.assertEqual(R.compte_par_grandeur().get("la direction", 0), 0)

    def test_le_compte_se_referme(self):
        self.assertEqual(sum(R.compte_par_grandeur().values()),
                         len(R.affirmations()))

    def test_les_cinq_familles_sont_comptees_dans_leurs_modules(self):
        fam = dict(R.familles())
        self.assertEqual(fam["Gamma, partie XIX"], len(nv.affirmations()))
        self.assertEqual(fam["Delta, partie XX"], len(G.confusions()))
        self.assertEqual(fam["Thêta, partie XXI"], len(th.affirmations()))
        self.assertEqual(fam["Véga, partie XXII"], len(vg.affirmations()))
        self.assertEqual(fam["Rho, partie XXIII"], len(R.affirmations()))

    def test_chaque_affirmation_porte_sa_mesure(self):
        for a in R.affirmations():
            self.assertGreater(len(a.enonce), 20)
            self.assertGreater(len(a.mesure), 20)
            self.assertIn(a.grandeur,
                          ("l'horloge", "le risque", "rien", "la direction"))


class TestLesSurfaces(unittest.TestCase):
    def test_les_quatre_reliefs_ont_leur_maximum_au_fond(self):
        """Le coin (0, 0) est le plus éloigné en projection isométrique."""
        for nom in ("surface_croisement", "surface_cout", "surface_ecart",
                    "surface_usure"):
            z = getattr(R, nom)()
            haut = max(max(l) for l in z)
            self.assertAlmostEqual(z[0][0], haut, places=9, msg=nom)

    def test_les_reliefs_sont_carres_et_pleins(self):
        for nom in ("surface_croisement", "surface_cout", "surface_ecart",
                    "surface_usure"):
            z = getattr(R, nom)()
            self.assertEqual(len(z), 6, nom)
            for l in z:
                self.assertEqual(len(l), 6, nom)
                for v in l:
                    self.assertTrue(math.isfinite(v), nom)

    def test_le_relief_du_croisement_est_plafonne(self):
        for l in R.surface_croisement():
            for v in l:
                self.assertLessEqual(v, R.PLAFOND_CROISEMENT + 1e-9)


class TestLesTables(unittest.TestCase):
    def setUp(self):
        self.tables = R.all_tables()

    def test_les_huit_tables_sont_la(self):
        self.assertEqual(len(self.tables), 8)

    def test_chaque_table_a_ses_colonnes(self):
        for cle, t in self.tables.items():
            for ligne in t.rows:
                self.assertEqual(len(ligne), len(t.headers), cle)

    def test_chaque_table_a_une_note_et_une_legende(self):
        for cle, t in self.tables.items():
            self.assertTrue(t.caption, cle)
            self.assertGreater(len(t.note or ""), 120, cle)

    def test_les_valeurs_sont_des_chaines_francaises(self):
        for cle, v in R.values().items():
            self.assertIsInstance(v, str, cle)
            self.assertNotIn(".", v.replace("&nbsp;", ""), cle)

    def test_la_part_ne_publie_jamais_un_zero_trompeur(self):
        """Un format à quatre décimales effaçait la ligne de l'opérateur."""
        for s in R.DISPERSIONS_TAUX:
            texte = R._part(R.cout_de_rho(R.JOURS_INTRA, s) / R.FRICTION)
            self.assertNotEqual(texte.rstrip("0").rstrip(","), "0")


class TestLesPlanches(unittest.TestCase):
    def setUp(self):
        self.rendus = figrh.render_all()

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
        for cle in ("rhreliefu", "rhreliefc", "rhreliefe", "rhreliefco"):
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
            figrh.render_all()
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
            figrh.render_all()
        finally:
            Panel.path = og
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
