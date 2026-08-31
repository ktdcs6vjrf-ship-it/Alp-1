"""Les cinq disciplines empruntées : ce que chaque estimateur doit rendre.

Trois familles de tests, et la deuxième est la seule qui compte vraiment.

*La forme.* Les tables existent, leurs lignes ont la bonne largeur, les
verdicts sont calculés et non écrits.

*L'accord avec une vérité connue.* Chaque discipline est éprouvée sur un cas
dont la réponse est fermée : la survie contre le principe de réflexion, le
rapport de Fano contre `1/(1−n)²`, l'amplitude de Palm contre ce même rapport
intégré, la loi de l'arc sinus contre sa forme fermée, l'indice de queue
contre l'indice vrai de la loi qui a produit l'échantillon. Un estimateur qui
ne retrouve pas une vérité connue n'a rien à faire dans un document.

*Les pièges du dépôt.* Le maximum de chaque relief au fond de la projection,
aucune apostrophe dans un libellé ARIA, aucune marque de gras dans un pied de
figure.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import emprunts as E
from alp1 import figemp, spectrum, stress


class TestUniteDObservation(unittest.TestCase):

    def test_le_sharpe_minimal_ne_depend_pas_du_pas_de_temps(self):
        """Le résultat de la section : cinq unités, une seule exigence."""
        memes = [u.sharpe_min for u in E.UNITES if u.annees == E.HORIZON_ANS]
        self.assertGreaterEqual(len(memes), 5)
        for s in memes[1:]:
            self.assertAlmostEqual(s, memes[0], places=9)

    def test_l_effet_par_unite_varie_de_quatre_ordres(self):
        ds = [u.d_min for u in E.UNITES]
        self.assertGreater(max(ds) / min(ds), 100.0)

    def test_le_releve_reel_est_le_seul_hors_norme(self):
        releve = E.UNITES[-1]
        self.assertEqual(releve.n, float(E.RELEVE_REEL))
        self.assertGreater(releve.sharpe_min, 3.0 * E.SHARPE_REF)

    def test_annees_pour_est_l_inverse_du_carre(self):
        self.assertAlmostEqual(E.annees_pour(2.0) * 4.0,
                               E.annees_pour(1.0), places=9)

    def test_le_cout_de_la_multiplicite_est_logarithmique(self):
        """Deux cent mille candidats ne coûtent qu'un facteur cinq."""
        un = E.annees_pour_avec(1.0, 1.0)
        beaucoup = E.annees_pour_avec(1.0, 2.0 ** 18)
        self.assertLess(beaucoup / un, 6.0)
        self.assertGreater(beaucoup / un, 3.0)

    def test_le_quantile_deflate_croit_avec_le_nombre(self):
        zs = [E.seuil_deflate(2.0 ** k) for k in E.LEVIERS_GRID]
        self.assertEqual(zs, sorted(zs))


class TestSurvie(unittest.TestCase):

    def test_la_survie_fermee_a_les_bonnes_limites(self):
        self.assertEqual(E.survie_nulle(0.0, 10.0), 0.0)
        self.assertEqual(E.survie_nulle(5.0, 0.0), 1.0)
        self.assertAlmostEqual(E.survie_nulle(1e6, 10.0), 1.0, places=9)

    def test_la_survie_decroit_avec_le_temps(self):
        vals = [E.survie_nulle(9.0, m) for m in (1, 5, 20, 60, 200)]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_la_correction_de_continuite_releve_la_survie(self):
        for m in (5.0, 30.0, 270.0):
            self.assertGreater(E.survie_minute(6.0, m), E.survie_nulle(6.0, m))

    def test_le_pic_de_hasard_tombe_bien_ou_la_formule_le_dit(self):
        """La formule doit rendre le maximum balayé, pas un voisin."""
        for d in (4.0, 9.0, 16.0):
            pic = E.pic_hasard(d)
            h_pic = E.hasard_nul(d, pic)
            for k in range(1, 400):
                m = k * pic / 40.0
                self.assertLessEqual(E.hasard_nul(d, m), h_pic + 1e-12)

    def test_la_constante_du_pic_ne_vaut_pas_trois(self):
        """L'erreur de dérivation que le balayage a trouvée."""
        self.assertAlmostEqual(E.coef_pic(), 2.6087, places=3)
        self.assertNotAlmostEqual(E.coef_pic(), 3.0, places=1)

    def test_le_hasard_decroit_en_un_sur_deux_m_au_loin(self):
        for m in (400.0, 800.0):
            self.assertAlmostEqual(E.hasard_nul(3.0, m) * m, 0.5, places=2)

    def test_kaplan_meier_part_de_un_et_decroit(self):
        courbe = E.kaplan_meier(list(E.observations()))
        self.assertEqual(courbe[0], (0.0, 1.0))
        vals = [s for _, s in courbe]
        self.assertEqual(vals, sorted(vals, reverse=True))
        self.assertGreaterEqual(vals[-1], 0.0)

    def test_kaplan_meier_retrouve_la_forme_fermee(self):
        """L'estimateur sans hypothèse contre la loi, à cinq points près."""
        courbe = E.kaplan_meier(list(E.observations()))
        for cible in (30.0, 90.0, 200.0):
            estime = [s for t, s in courbe if t <= cible][-1]
            self.assertAlmostEqual(estime, E.survie_moyenne(cible), delta=0.05)

    def test_ecarter_les_censures_sous_estime_lourdement(self):
        obs = E.observations()
        gardes = [o for o in obs if not o.censure]
        rmst = sum(min(o.duree, E.RESTE) for o in gardes) / len(gardes)
        self.assertLess(rmst, 0.4 * E.rmst_exact())

    def test_la_censure_vient_surtout_de_la_sortie(self):
        obs = E.observations()
        par_sortie = sum(1 for o in obs if o.censure and o.sortie < E.RESTE)
        censures = sum(1 for o in obs if o.censure)
        self.assertGreater(par_sortie / censures, 0.9)

    def test_la_duree_observee_ne_depasse_jamais_ses_bornes(self):
        for o in E.observations():
            self.assertLessEqual(o.duree, E.RESTE)
            self.assertLessEqual(o.duree, min(o.sortie, E.RESTE) + 1e-9)
            if not o.censure:
                self.assertAlmostEqual(o.duree, o.duree_vraie, places=9)


class TestCalibration(unittest.TestCase):

    def test_la_correction_du_pas_divise_le_biais(self):
        cal = E.calibration()
        biais_c = sum(f - pc for pc, _, f, _ in cal) / len(cal)
        biais_m = sum(f - pm for _, pm, f, _ in cal) / len(cal)
        self.assertGreater(biais_c, 0.01)
        self.assertLess(abs(biais_m), abs(biais_c) / 3.0)

    def test_les_tranches_sont_croissantes_et_peuplees(self):
        cal = E.calibration()
        self.assertEqual(len(cal), E.N_TRANCHES)
        preds = [pm for _, pm, _, _ in cal]
        self.assertEqual(preds, sorted(preds))
        for _, _, _, n in cal:
            self.assertGreater(n, 500)


class TestAutoExcitation(unittest.TestCase):

    def test_le_taux_simule_est_celui_de_la_theorie(self):
        inst = E.hawkes()
        taux = len(inst) / E.T_HAWKES
        self.assertAlmostEqual(taux, E.intensite_moyenne(), delta=0.03)

    def test_le_rapport_de_fano_converge_vers_un_sur_un_moins_n_au_carre(self):
        inst = E.hawkes()
        cible = 1.0 / (1.0 - E.HAWKES_N) ** 2
        self.assertAlmostEqual(E.fano(inst, 200.0), cible, delta=0.12 * cible)

    def test_le_branchement_implicite_retrouve_le_declare(self):
        inst = E.hawkes()
        self.assertAlmostEqual(E.branchement_implicite(E.fano(inst, 200.0)),
                               E.HAWKES_N, delta=0.03)

    def test_le_poisson_temoin_a_un_fano_de_un(self):
        taux = len(E.hawkes()) / E.T_HAWKES
        poi = E.poisson_temoin(taux, E.T_HAWKES)
        self.assertAlmostEqual(E.fano(poi, 200.0), 1.0, delta=0.25)

    def test_l_amplitude_de_palm_rend_le_rapport_de_fano(self):
        """Le contrôle exact : `1 + 2A/(β−α) = 1/(1−n)²`."""
        a = E.amplitude_palm()
        g = E.HAWKES_BETA - E.HAWKES_ALPHA
        self.assertAlmostEqual(1.0 + 2.0 * a / g,
                               1.0 / (1.0 - E.HAWKES_N) ** 2, places=9)

    def test_l_amplitude_de_palm_n_est_pas_alpha(self):
        self.assertGreater(E.amplitude_palm() / E.HAWKES_ALPHA, 2.0)

    def test_la_reponse_mesuree_suit_la_forme_fermee(self):
        inst = E.hawkes()
        taux = len(inst) / E.T_HAWKES
        for lo, hi in E.APRES:
            mes = E.reponse_mesuree(inst, (lo, hi))
            fer = E.reponse_moyenne(lo, hi, lam_bar=taux)
            self.assertAlmostEqual(mes / fer, 1.0, delta=0.06)

    def test_la_direction_reste_un_demi(self):
        part, sd, n = E.direction_apres()
        self.assertGreater(n, 5000)
        self.assertLess(abs(part - 0.5), 3.0 * sd)

    def test_l_excitation_leve_le_seuil(self):
        seuils = [E.horloge_excitee(t)[3] for t in E.INSTANTS_APRES]
        self.assertEqual(seuils, sorted(seuils, reverse=True))
        self.assertGreater(seuils[0] / seuils[-1], 2.0)

    def test_la_fenetre_temoin_est_bien_la_plus_chargee(self):
        largeur = 60.0
        t0 = E.fenetre_temoin(largeur)
        n0 = len(E.evenements_entre(t0, t0 + largeur))
        for autre in (t0 + 3000.0, t0 - 5000.0, 100.0):
            if 0.0 <= autre < E.T_HAWKES - largeur:
                self.assertGreaterEqual(
                    n0, len(E.evenements_entre(autre, autre + largeur)))


class TestValeursExtremes(unittest.TestCase):

    def test_l_arc_sinus_a_les_bonnes_valeurs(self):
        self.assertAlmostEqual(E.arc_sinus(0.0), 0.0, places=12)
        self.assertAlmostEqual(E.arc_sinus(1.0), 1.0, places=12)
        self.assertAlmostEqual(E.arc_sinus(0.5), 0.5, places=12)

    def test_la_loi_mesuree_est_celle_de_l_arc_sinus(self):
        args = E.argmax_seances()
        n = len(args)
        for i in range(10):
            a, b = i / 10.0, (i + 1) / 10.0
            mesure = sum(1 for t in args if a <= t < b) / n
            self.assertAlmostEqual(mesure, E.arc_sinus(b) - E.arc_sinus(a),
                                   delta=0.006)

    def test_la_loi_mesuree_est_symetrique(self):
        args = E.argmax_seances()
        n = len(args)
        bas = sum(1 for t in args if t < 0.1) / n
        haut = sum(1 for t in args if t >= 0.9) / n
        self.assertAlmostEqual(bas, haut, delta=0.01)

    def test_les_bords_portent_deux_fois_l_uniforme(self):
        self.assertGreater(E.arc_sinus(0.1), 0.19)

    def test_les_lois_d_increment_sont_a_variance_un(self):
        for cle in E.CLES_QUEUES:
            ech = E.incrementales(cle)
            moy = sum(ech) / len(ech)
            var = sum((x - moy) ** 2 for x in ech) / (len(ech) - 1)
            self.assertAlmostEqual(var, 1.0, delta=0.12)

    def test_l_indice_de_queue_estime_retrouve_le_vrai(self):
        """Là où la queue est vraiment de Pareto, l'ajustement la rend."""
        for cle in ("gauss", "student5", "student3"):
            ech = [abs(x) for x in E.incrementales(cle)]
            tri = sorted(ech)
            u = tri[int((1.0 - E.PART_SEUIL) * len(tri))]
            fit = stress.fit_gpd(ech, u)
            self.assertAlmostEqual(fit.shape, E.XI_VRAI[cle], delta=0.06)

    def test_hill_attribue_une_queue_lourde_a_la_gaussienne(self):
        """Le piège de la section, et il doit rester visible."""
        ech = [abs(x) for x in E.incrementales("gauss")]
        for frac in E.GRILLE_HILL:
            k = max(2, int(frac * len(ech)))
            self.assertGreater(stress.hill_estimator(ech, k), 0.05)

    def test_hill_depend_du_reglage(self):
        ech = [abs(x) for x in E.incrementales("student3")]
        vals = [stress.hill_estimator(ech, max(2, int(f * len(ech))))
                for f in E.GRILLE_HILL]
        self.assertGreater(max(vals) - min(vals), 0.08)

    def test_la_var_de_pareto_croit_avec_l_indice(self):
        for c in E.SURF_CONFIANCE:
            vals = [E.var_pareto(x, c) for x in E.SURF_XI]
            self.assertEqual(vals, sorted(vals, reverse=True))


class TestDetection(unittest.TestCase):

    def test_l_aire_roc_vaut_un_demi_a_sensibilite_nulle(self):
        self.assertAlmostEqual(E.aire_roc(0.0), 0.5, places=12)

    def test_le_taux_affiche_monte_avec_le_critere(self):
        vals = [E.precision(E.D_REF, c) for c in E.CRITERES]
        self.assertEqual(vals, sorted(vals))

    def test_la_frequence_baisse_avec_le_critere(self):
        vals = [E.frequence(E.D_REF, c) for c in E.CRITERES]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_a_sensibilite_nulle_le_taux_est_le_taux_de_base(self):
        for c in E.CRITERES:
            self.assertAlmostEqual(E.precision(0.0, c), E.BASE_RATE, places=9)

    def test_a_sensibilite_nulle_rien_n_est_rentable(self):
        c = -3.0
        while c <= 6.0:
            self.assertLessEqual(E.esperance_an(0.0, c), 1e-9)
            c += 0.1

    def test_le_critere_optimal_est_interieur_et_calcule(self):
        c_opt, v_opt = E.critere_optimal(E.D_REF)
        self.assertGreater(v_opt, 0.0)
        self.assertGreater(c_opt, -0.5)
        self.assertLess(c_opt, 2.0)
        for c in (c_opt - 0.4, c_opt + 0.4):
            self.assertLessEqual(E.esperance_an(E.D_REF, c), v_opt + 1e-9)

    def test_le_critere_optimal_se_relache_quand_la_sensibilite_monte(self):
        cs = [E.critere_optimal(d)[0] for d in (0.15, 0.30, 0.50, 0.80)]
        self.assertEqual(cs, sorted(cs, reverse=True))

    def test_le_seuil_de_rentabilite_est_celui_de_la_geometrie(self):
        self.assertAlmostEqual(
            E.BREAK_EVEN_P,
            (1.0 + E.FRICTION_RATIO) / (1.0 + E.RR), places=12)
        self.assertAlmostEqual(E.esperance_r(E.BREAK_EVEN_P), 0.0, places=12)

    def test_la_loi_nulle_de_d_prime_est_centree(self):
        med, q95, _ = E.dprime_nul(1008)
        self.assertLess(abs(med), 0.02)
        self.assertGreater(q95, 0.0)

    def test_le_bruit_d_un_court_releve_depasse_l_effet_cherche(self):
        self.assertGreater(E.dprime_nul(30)[1], E.D_REF)

    def test_le_bruit_decroit_avec_la_taille_du_releve(self):
        q = [E.dprime_nul(n)[1] for n in E.TAILLES_RELEVE]
        self.assertEqual(q, sorted(q, reverse=True))


class TestSpectre(unittest.TestCase):

    def test_le_bord_ferme_borne_la_simulation(self):
        n = int(E.SESSIONS_PAR_AN)
        for k in E.LECTURES_GRID:
            nul = spectrum.null_spectrum(k, n, E.N_TIRAGES_SPECTRE, E.SEED + 7)
            self.assertLess(nul.lambda_max_q95, spectrum.mp_edges(k / n)[1])

    def test_le_seuil_bbp_croit_avec_le_nombre_de_lectures(self):
        n = E.SESSIONS_PAR_AN
        vals = [spectrum.bbp_threshold(k / n) for k in E.LECTURES_GRID]
        self.assertEqual(vals, sorted(vals))

    def test_une_annee_suffit_pour_quinze_lectures(self):
        besoin = spectrum.observations_for_spike(E.S_REF, max(E.LECTURES_GRID))
        self.assertLess(besoin, E.SESSIONS_PAR_AN)


class TestTransfert(unittest.TestCase):

    def test_une_seule_discipline_touche_au_sens(self):
        self.assertEqual(sum(1 for t in E.transferts() if t.sur_le_sens), 1)

    def test_le_verdict_suit_la_regle_declaree(self):
        for t in E.transferts():
            self.assertEqual(t.transfere, abs(t.effet) >= E.SEUIL_TRANSFERT)

    def test_les_effets_sont_relus_des_mesures(self):
        """Aucun nombre de la table n'est écrit à la main."""
        par_cle = {t.nom: t for t in E.transferts()}
        excitation = par_cle["Processus auto-excitants"]
        attendu = E.horloge_excitee(0.0)[3] / E.horloge_excitee(40.0)[3] - 1.0
        self.assertAlmostEqual(excitation.effet, attendu, places=9)

    def test_la_discipline_qui_touche_au_sens_est_la_detection(self):
        seule = [t for t in E.transferts() if t.sur_le_sens][0]
        self.assertEqual(seule.terme, "µ")


class TestSurfaces(unittest.TestCase):

    SURFACES = (
        ("puissance", E.surface_puissance, E.SURF_SHARPE, E.SURF_ANNEES),
        ("hasard", E.surface_hasard, E.SURF_DISTANCE, E.SURF_MINUTES),
        ("seuil", E.surface_seuil, E.SURF_BRANCHEMENT, E.SURF_APRES),
        ("queue", E.surface_queue, E.SURF_XI, E.SURF_CONFIANCE),
        ("detection", E.surface_detection, E.SURF_DPRIME, E.SURF_CRITERE),
        ("bbp", E.surface_bbp, E.SURF_FORCE, E.SURF_GAMMA),
    )

    def test_les_dimensions_suivent_les_grilles(self):
        for nom, fn, lignes, colonnes in self.SURFACES:
            z = fn()
            self.assertEqual(len(z), len(lignes), nom)
            for ligne in z:
                self.assertEqual(len(ligne), len(colonnes), nom)

    def test_le_maximum_est_au_fond_de_la_projection(self):
        """Règle du dépôt : le sommet ne se pose jamais au premier plan."""
        for nom, fn, _, _ in self.SURFACES:
            z = fn()
            i, j, _ = max(((i, j, z[i][j])
                           for i in range(len(z)) for j in range(len(z[0]))),
                          key=lambda t: t[2])
            self.assertLessEqual(i, 1, nom)
            self.assertLessEqual(j, 1, nom)

    def test_la_surface_bbp_est_plate_sous_le_seuil(self):
        """La transition est une arête, pas une pente."""
        z = E.surface_bbp()
        for j, g in enumerate(E.SURF_GAMMA):
            sous = [z[i][j] for i, s in enumerate(E.SURF_FORCE)
                    if s < spectrum.bbp_threshold(g)]
            for v in sous[1:]:
                self.assertAlmostEqual(v, sous[0], places=12)


class TestLesTables(unittest.TestCase):

    def setUp(self):
        self.tables = E.all_tables()

    def test_les_seize_tables_sont_la(self):
        self.assertEqual(len(self.tables), 16)
        for cle in self.tables:
            self.assertTrue(cle.startswith("emp_"), cle)

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
        for cle in E.values():
            self.assertTrue(cle.startswith("e_"), cle)


class TestLesPlanches(unittest.TestCase):

    def setUp(self):
        self.rendus = figemp.render_all()

    def test_les_quinze_planches_sont_la(self):
        self.assertEqual(len(self.rendus), 15)

    def test_aucun_libelle_aria_ne_porte_d_apostrophe(self):
        """Une apostrophe dans un attribut passe les deux passes et casse."""
        for cle, svg in self.rendus.items():
            for aria in re.findall(r'aria-label="([^"]*)"', svg):
                self.assertNotIn("'", aria, cle)
                self.assertNotIn("’", aria, cle)

    def test_aucun_pied_ne_porte_de_marque(self):
        """Un pied ne passe pas par `report.inline`.

        Ni l'astérisque de gras ni l'apostrophe inverse de code n'y sont
        rendues : elles se publient telles quelles, en caractères, sous la
        figure. Le contrôle porte sur les deux marques et sur les deux
        familles de texte qui survivent au rendu — le pied, sorti du SVG et
        recomposé sous la légende, et l'annotation, qui reste dedans.
        """
        for cle, svg in self.rendus.items():
            for classe in ("lg cap", "lg keep"):
                for texte in re.findall(
                        r'<text[^>]*class="' + classe + r'"[^>]*>([^<]*)<',
                        svg):
                    self.assertNotIn("**", texte, cle)
                    self.assertNotIn("`", texte, cle)

    def test_chaque_planche_a_un_viewbox_et_un_libelle(self):
        for cle, svg in self.rendus.items():
            self.assertIn("viewBox=", svg, cle)
            self.assertRegex(svg, r'aria-label="[^"]{20,}"', cle)

    def test_les_six_reliefs_portent_leur_echine(self):
        for cle in ("emppuissance", "emphasard", "empexcitation", "empqueue",
                    "empcritere", "empbbp"):
            self.assertIn('class="post"', self.rendus[cle], cle)
            self.assertIn('class="nuage', self.rendus[cle], cle)


if __name__ == "__main__":
    unittest.main()


class TestAucuneGraduationHorsDomaine(unittest.TestCase):
    """Une graduation écrite hors du domaine est tout de même tracée.

    `Panel.grid_y` et `Panel.grid_x` ne découpent pas — contrairement à
    `path` et `dot`. Une graduation posée à la main au-delà du domaine sort
    donc du cadre et se pose ailleurs sur la planche, souvent au-dessus de
    l'en-tête, là où aucun balayage de débordement ne la voit puisqu'elle
    reste dans la boîte du SVG. Ce test remplace le balayage manquant.
    """

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
            figemp.render_all()
        finally:
            Panel.grid_y, Panel.grid_x = og_y, og_x
        self.assertEqual(hits, [])
