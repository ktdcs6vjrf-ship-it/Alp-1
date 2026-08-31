"""Ce qu'un fonds fait, et ce qui en reste : les contrôles de la partie XVII.

La partie est presque entièrement de l'arithmétique fermée, et c'est ce qui
décide de la forme des tests. Il n'y a rien à valider contre une simulation —
il y a des identités à vérifier, des limites à contrôler, et des verdicts qui
doivent rester calculés.

Trois familles. Les identités de la loi fondamentale et du panier, qu'on
vérifie contre leurs formes limites connues. Les invariances, qui sont le
résultat de la partie et qui doivent donc tenir exactement. Et les pièges du
dépôt : le maximum de chaque relief au fond, aucune apostrophe dans un libellé
ARIA, aucune marque dans un pied de figure, aucune graduation hors domaine.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import figfds
from alp1 import fonds as F
from alp1 import seuil as S


class TestLoiFondamentale(unittest.TestCase):

    def test_l_identite_de_grinold_se_referme(self):
        for n in F.N_GRID:
            for ir in (0.5, 1.0, 2.0, 4.0):
                self.assertAlmostEqual(
                    F.ic_requis(ir, n) * math.sqrt(n), ir, places=9)

    def test_la_conversion_en_taux_est_exacte(self):
        for p in (0.5, 0.5075, 0.52, 0.6, 0.75):
            self.assertAlmostEqual(F.taux_de_ic(F.ic_de_taux(p)), p, places=12)

    def test_l_exigence_decroit_en_racine(self):
        """Cent fois plus de décisions divisent l'exigence par dix."""
        self.assertAlmostEqual(
            F.ic_requis(2.0, 1000.0) / F.ic_requis(2.0, 100000.0), 10.0,
            places=9)

    def test_les_annees_ne_dependent_pas_du_nombre_de_decisions(self):
        """Le résultat de la partie, et il doit tenir exactement."""
        ref = F.annees_pour_ir(F.IR_REF)
        self.assertGreater(ref, 0.0)
        for n in F.N_GRID:
            _ = n
            self.assertAlmostEqual(F.annees_pour_ir(F.IR_REF), ref, places=12)

    def test_les_deux_routes_tombent_au_meme_ordre(self):
        """L'information et le Sharpe butent sur le même mur."""
        for n in F.N_GRID:
            p = F.taux_de_ic(F.ic_requis(F.IR_REF, n))
            par_info = F.decisions_pour_taux(p) / n
            par_sharpe = F.annees_pour_ir(F.IR_REF)
            self.assertLess(abs(par_info - par_sharpe) / par_sharpe, 0.35)

    def test_la_duree_par_l_information_ne_bouge_pas_avec_n(self):
        durees = [F.decisions_pour_taux(
            F.taux_de_ic(F.ic_requis(F.IR_REF, n))) / n for n in F.N_GRID]
        self.assertLess((max(durees) - min(durees)) / min(durees), 0.02)

    def test_le_seuil_de_credibilite_est_la_solution_exacte(self):
        n = F.seuil_de_credibilite()
        self.assertAlmostEqual(
            F.taux_de_ic(F.ic_requis(F.IR_REF, n)),
            F.TAUX_INVRAISEMBLABLE, places=12)

    def test_un_operateur_est_au_dessous_du_seuil(self):
        self.assertLess(F.OPERATEUR_DECISIONS, F.seuil_de_credibilite())


class TestPrixDeLaPreuve(unittest.TestCase):

    def test_le_hasard_exige_un_echantillon_infini(self):
        self.assertEqual(F.decisions_pour_taux(0.5), math.inf)
        self.assertEqual(F.decisions_pour_taux(0.49), math.inf)

    def test_les_decisions_requises_decroissent_avec_l_ecart(self):
        vals = [F.decisions_pour_taux(p) for p in F.TAUX_GRID]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_les_decisions_croissent_comme_l_inverse_du_carre(self):
        """`D(p‖½) ≈ 2(p−½)²/ln2`, donc l'échantillon suit `1/(p−½)²`."""
        a = F.decisions_pour_taux(0.5010)
        b = F.decisions_pour_taux(0.5020)
        self.assertAlmostEqual(a / b, 4.0, delta=0.05)

    def test_le_taux_publie_est_hors_de_portee_d_un_operateur(self):
        dec = F.decisions_pour_taux(F.ANNONCES["taux"])
        self.assertGreater(dec / F.OPERATEUR_DECISIONS, 40.0)
        self.assertLess(365.0 * dec / F.RYTHME_FONDS, 30.0)


class TestPanierDeLectures(unittest.TestCase):

    def test_a_correlation_nulle_le_gain_est_la_racine(self):
        for k in F.K_GRID:
            self.assertAlmostEqual(F.ic_combine(k, 0.0), math.sqrt(k),
                                   places=9)

    def test_une_lecture_seule_ne_gagne_rien(self):
        for rho in F.RHO_GRID:
            self.assertAlmostEqual(F.ic_combine(1, rho), 1.0, places=12)

    def test_le_gain_sature_sur_son_plafond(self):
        for rho in F.RHO_GRID[1:]:
            self.assertLess(F.ic_combine(100000, rho), F.plafond(rho))
            self.assertAlmostEqual(F.ic_combine(100000, rho), F.plafond(rho),
                                   delta=0.01 * F.plafond(rho))

    def test_le_gain_croit_avec_le_nombre_et_decroit_avec_la_correlation(self):
        for rho in F.RHO_GRID:
            vals = [F.ic_combine(k, rho) for k in F.K_GRID]
            self.assertEqual(vals, sorted(vals))
        for k in F.K_GRID[1:]:
            vals = [F.ic_combine(k, r) for r in F.RHO_GRID]
            self.assertEqual(vals, sorted(vals, reverse=True))

    def test_la_fraction_du_plafond_est_la_solution_exacte(self):
        for rho in F.RHO_GRID[1:]:
            k = F.k_pour_fraction(rho, 0.90)
            self.assertAlmostEqual(F.ic_combine(k, rho) / F.plafond(rho), 0.90,
                                   places=9)

    def test_quinze_lectures_correlees_ne_valent_pas_racine_de_quinze(self):
        self.assertLess(F.ic_combine(15, F.RHO_REF), 0.7 * math.sqrt(15.0))


class TestCapacite(unittest.TestCase):

    def test_l_impact_croit_en_racine_de_la_taille(self):
        self.assertAlmostEqual(
            F.impact_racine(400.0) / F.impact_racine(100.0), 2.0, places=9)

    def test_un_ordre_nul_n_a_aucun_impact(self):
        self.assertEqual(F.impact_racine(0.0), 0.0)

    def test_le_seuil_croit_avec_la_taille(self):
        vals = [F.seuil_a_la_taille(q) for q in F.TAILLE_GRID]
        self.assertEqual(vals, sorted(vals))

    def test_a_un_contrat_l_impact_est_marginal(self):
        part = 2.0 * F.impact_racine(1.0) / F.friction_a_la_taille(1.0)
        self.assertLess(part, 0.20)

    def test_la_capacite_est_le_point_de_sortie_du_domaine(self):
        cap = F.capacite()
        haut = S.PLAUSIBLE_DRIFT_PER_HOUR[1]
        self.assertAlmostEqual(F.seuil_a_la_taille(cap), haut, delta=0.02)
        self.assertGreater(F.seuil_a_la_taille(cap * 1.5), haut)
        self.assertLess(F.seuil_a_la_taille(cap * 0.5), haut)

    def test_l_operateur_est_tres_au_dessous_de_la_capacite(self):
        self.assertLess(F.OPERATEUR_TAILLE, 0.01 * F.capacite())


class TestExecution(unittest.TestCase):

    def test_le_glissement_de_sortie_vient_de_la_geometrie(self):
        """Il n'est pas posé à la main : c'est `(1 − p_cible)·glissement`."""
        o = F._issue()
        self.assertAlmostEqual(
            F.glissement_sortie(),
            (1.0 - o.p_target) * F.GLISSEMENT_STOP, places=12)

    def test_la_probabilite_de_cible_est_celle_du_theoreme(self):
        """`a/(a+b) = 1/(1+RR)` — le contrôle qui relie la partie au reste."""
        self.assertAlmostEqual(F._issue().p_target, 1.0 / (1.0 + F.RR),
                               delta=0.005)

    def test_une_entree_passive_coute_moins_qu_une_entree_au_marche(self):
        couts = [F.cout_de_conduite(t) for _, t, _ in F.ENTREES]
        self.assertEqual(couts, sorted(couts, reverse=True))

    def test_le_seuil_suit_le_cout(self):
        for _, t, _ in F.ENTREES:
            self.assertAlmostEqual(
                F.seuil_de_conduite(t),
                F.cout_de_conduite(t) / F._issue().expected_time * 60.0,
                places=12)

    def test_la_reference_a_une_derive_annulante_nulle(self):
        self.assertAlmostEqual(F.derive_adverse_annulante(0.5), 0.0, places=12)

    def test_la_derive_annulante_est_sous_le_plancher_plausible(self):
        """Le fait qui rend la mesure obligatoire, et il doit rester vrai."""
        self.assertLess(F.derive_adverse_annulante(-0.5),
                        S.PLAUSIBLE_DRIFT_PER_HOUR[0])

    def test_le_taux_de_remplissage_a_les_bonnes_limites(self):
        self.assertEqual(F.taux_remplissage(1.0, 0.0), 0.0)
        self.assertAlmostEqual(F.taux_remplissage(0.001, 60.0), 1.0, delta=0.01)

    def test_le_remplissage_decroit_avec_la_profondeur(self):
        for w in F.FENETRES_ATTENTE:
            vals = [F.taux_remplissage(d, w) for d in F.PROFONDEURS]
            self.assertEqual(vals, sorted(vals, reverse=True))

    def test_le_remplissage_croit_avec_l_attente(self):
        for d in F.PROFONDEURS:
            vals = [F.taux_remplissage(d, w) for w in F.FENETRES_ATTENTE]
            self.assertEqual(vals, sorted(vals))

    def test_le_gain_annuel_bascule_sous_zero(self):
        self.assertGreater(F.gain_annuel(1.0, 0.0), 0.0)
        self.assertLess(F.gain_annuel(1.0, F.SURF_ADVERSE[-1]), 0.0)

    def test_la_derive_declaree_est_le_milieu_du_domaine(self):
        lo, hi = S.PLAUSIBLE_DRIFT_PER_HOUR
        self.assertAlmostEqual(F.DERIVE_DECLAREE, 0.5 * (lo + hi), places=12)


class TestTransfert(unittest.TestCase):

    def test_une_seule_pratique_reste_hors_de_portee(self):
        self.assertEqual(sum(1 for p in F.pratiques() if not p.accessible), 1)

    def test_celle_qui_echoue_est_l_ampleur(self):
        hors = [p for p in F.pratiques() if not p.transfere]
        self.assertEqual(len(hors), 1)
        self.assertEqual(hors[0].nom, "L'ampleur")

    def test_le_verdict_suit_la_regle_declaree(self):
        for p in F.pratiques():
            attendu = p.accessible and abs(p.effet - 1.0) >= F.SEUIL_TRANSFERT
            self.assertEqual(p.transfere, attendu, p.nom)

    def test_les_effets_sont_relus_des_mesures(self):
        """Aucun nombre de la table de synthèse n'est écrit à la main."""
        par_nom = {p.nom: p for p in F.pratiques()}
        self.assertAlmostEqual(
            par_nom["L'exécution"].effet,
            F.seuil_de_conduite(F.ENTREES[0][1])
            / F.seuil_de_conduite(F.ENTREES[-1][1]), places=9)
        self.assertAlmostEqual(
            par_nom["La combinaison de lectures"].effet,
            F.ic_combine(15, F.RHO_REF), places=9)


class TestSurfaces(unittest.TestCase):

    SURFACES = (
        ("exigence", F.surface_exigence, F.SURF_IR, F.SURF_N),
        ("panier", F.surface_panier, F.SURF_K, F.SURF_RHO),
        ("capacite", F.surface_capacite, F.SURF_TAILLE, F.SURF_STOP),
        ("execution", F.surface_execution, F.SURF_REMPLI, F.SURF_ADVERSE),
    )

    def test_les_dimensions_suivent_les_grilles(self):
        for nom, fn, lignes, colonnes in self.SURFACES:
            z = fn()
            self.assertEqual(len(z), len(lignes), nom)
            for ligne in z:
                self.assertEqual(len(ligne), len(colonnes), nom)

    def test_le_maximum_est_au_fond_de_la_projection(self):
        for nom, fn, _, _ in self.SURFACES:
            z = fn()
            i, j, _ = max(((i, j, z[i][j])
                           for i in range(len(z)) for j in range(len(z[0]))),
                          key=lambda t: t[2])
            self.assertLessEqual(i, 1, nom)
            self.assertLessEqual(j, 1, nom)

    def test_la_surface_d_execution_traverse_le_sol(self):
        z = F.surface_execution()
        vals = [v for ligne in z for v in ligne]
        self.assertGreater(max(vals), 0.0)
        self.assertLess(min(vals), 0.0)

    def test_la_surface_de_capacite_est_logarithmique(self):
        """La hauteur est un logarithme : les infobulles doivent le défaire."""
        z = F.surface_capacite()
        self.assertAlmostEqual(10.0 ** z[0][0],
                               F.seuil_a_la_taille(F.SURF_TAILLE[0],
                                                   F.SURF_STOP[0]), places=9)


class TestLesTables(unittest.TestCase):

    def setUp(self):
        self.tables = F.all_tables()

    def test_les_huit_tables_sont_la(self):
        self.assertEqual(len(self.tables), 8)
        for cle in self.tables:
            self.assertTrue(cle.startswith("fonds_"), cle)

    def test_chaque_ligne_a_la_largeur_de_son_en_tete(self):
        for cle, t in self.tables.items():
            for ligne in t.rows:
                self.assertEqual(len(ligne), len(t.headers), cle)

    def test_chaque_table_porte_une_note_et_une_legende(self):
        for cle, t in self.tables.items():
            self.assertTrue(t.note.strip(), cle)
            self.assertTrue(t.caption.strip(), cle)

    def test_les_marques_de_gras_sont_appariees(self):
        for cle, t in self.tables.items():
            self.assertEqual(t.note.count("**") % 2, 0, cle)

    def test_les_scalaires_sont_prefixes(self):
        for cle in F.values():
            self.assertTrue(cle.startswith("f_"), cle)

    def test_les_nombres_publics_ne_sont_recopies_qu_une_fois(self):
        """`ANNONCES` est la seule source, et les tables s'y réfèrent."""
        self.assertEqual(sorted(F.ANNONCES),
                         ["annees", "brut", "capacite_musd", "taux"])
        self.assertEqual(F.TAUX_GRID[0], F.ANNONCES["taux"])


class TestLesPlanches(unittest.TestCase):

    def setUp(self):
        self.rendus = figfds.render_all()

    def test_les_dix_planches_sont_la(self):
        self.assertEqual(len(self.rendus), 10)

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
                    self.assertNotIn("`", texte, cle)

    def test_les_quatre_reliefs_portent_leur_echine(self):
        for cle in ("fdsexigence", "fdspanier", "fdsrelief", "fdsadverse"):
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
            figfds.render_all()
        finally:
            Panel.grid_y, Panel.grid_x = og_y, og_x
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
