"""Les tests de « le loyer de la convexité » — la partie XXI.

Trois familles s'y trouvent, et elles ne se remplacent pas. Les formes
fermées sont contrôlées contre autre chose qu'elles-mêmes — une différence
finie, une simulation, une seconde route algébrique — parce que la règle du
dépôt l'exige sans exception. Les verdicts sont recalculés plutôt que relus,
parce qu'un compte écrit à la main dans une planche a déjà menti une fois
dans cette partie. Et les planches sont balayées pour ce qu'aucun rendu ne
montre : une graduation hors domaine, un tracé réduit à rien, une marque de
gras publiée telle quelle.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import figth
from alp1 import grandeurs as G
from alp1 import niveaux as nv
from alp1 import theta as T
from alp1.costs import norm_cdf


class TestLesTroisTermes(unittest.TestCase):
    """Le thêta a trois termes, et les deux formes fermées se contrôlent."""

    def test_le_call_tombe_sur_la_difference_finie(self):
        for jours in (7.0, 30.0, 365.0):
            t = jours / nv.JOURS_AN
            for m in (0.85, 1.0, 1.15):
                ferme = T.termes_call(m * T.S_REF, T.S_REF, T.VOL_REF, t).total
                numer = T.theta_numerique(T.call, m * T.S_REF, T.S_REF,
                                          T.VOL_REF, t)
                self.assertAlmostEqual(ferme, numer, delta=1e-3 * max(
                    1.0, abs(ferme)))

    def test_le_put_tombe_sur_la_difference_finie(self):
        for jours in (7.0, 30.0, 365.0):
            t = jours / nv.JOURS_AN
            for m in (0.85, 1.0, 1.15):
                ferme = T.termes_put(m * T.S_REF, T.S_REF, T.VOL_REF, t).total
                numer = T.theta_numerique(T.put, m * T.S_REF, T.S_REF,
                                          T.VOL_REF, t)
                self.assertAlmostEqual(ferme, numer, delta=1e-3 * max(
                    1.0, abs(numer)))

    def test_la_decroissance_est_commune_au_call_et_au_put(self):
        """La courbure ne connaît pas le sens de l'option."""
        for m in (0.8, 1.0, 1.2):
            t = 30.0 / nv.JOURS_AN
            self.assertAlmostEqual(
                T.termes_call(m * T.S_REF, T.S_REF, T.VOL_REF, t).decroissance,
                T.termes_put(m * T.S_REF, T.S_REF, T.VOL_REF, t).decroissance,
                places=12)

    def test_les_deux_autres_termes_changent_de_signe(self):
        t = 30.0 / nv.JOURS_AN
        c = T.termes_call(T.S_REF, T.S_REF, T.VOL_REF, t)
        p = T.termes_put(T.S_REF, T.S_REF, T.VOL_REF, t)
        self.assertLess(c.interet, 0.0)
        self.assertGreater(p.interet, 0.0)
        self.assertGreater(c.portage, 0.0)
        self.assertLess(p.portage, 0.0)

    def test_le_rapport_au_gamma_est_l_invariant(self):
        """`|Θ₁|/Γ = ½σ²S²`, à toute échéance et sans exception."""
        cible = T.rapport_theta_gamma(T.S_REF, T.VOL_REF)
        for jours in T.ECHEANCES:
            t = jours / nv.JOURS_AN
            g = nv.gamma(T.S_REF, T.S_REF, T.VOL_REF, t)
            t1 = T.termes_call(T.S_REF, T.S_REF, T.VOL_REF, t, 0.0,
                               0.0).decroissance
            self.assertAlmostEqual(abs(t1) / g / cible, 1.0, places=9)

    def test_la_parite_tient(self):
        t = 30.0 / nv.JOURS_AN
        for m in (0.8, 1.0, 1.2):
            s = m * T.S_REF
            gauche = T.call(s, T.S_REF, T.VOL_REF, t) - T.put(
                s, T.S_REF, T.VOL_REF, t)
            droite = (s * math.exp(-T.DIVIDENDE * t)
                      - T.S_REF * math.exp(-T.TAUX * t))
            self.assertAlmostEqual(gauche, droite, places=10)


class TestLaLoiNulleDuVendeur(unittest.TestCase):
    """Une fréquence élevée posée sur une espérance nulle."""

    def test_la_frequence_d_un_intervalle_est_deux_phi_un_moins_un(self):
        self.assertAlmostEqual(T.taux_par_intervalle(),
                               2.0 * norm_cdf(1.0) - 1.0, places=12)
        self.assertAlmostEqual(T.taux_par_intervalle(), 0.6827, places=3)

    def test_la_mediane_du_khi_deux_est_sous_sa_moyenne(self):
        m = T.mediane_khi2()
        self.assertAlmostEqual(2.0 * norm_cdf(math.sqrt(m)) - 1.0, 0.5,
                               places=9)
        self.assertLess(m, 0.5)

    def test_la_simulation_confirme_la_frequence_d_un_intervalle(self):
        """La forme fermée, contrôlée sur le premier intervalle de chaque
        chemin — celui où l'option a toute sa courbure."""
        c = T.simuler_vendeur()
        self.assertAlmostEqual(c.taux_premier, T.taux_par_intervalle(),
                               delta=0.02)

    def test_la_frequence_sur_la_vie_est_sous_celle_d_un_intervalle(self):
        """Le quart d'intervalles sans courbure rend un pile ou face."""
        c = T.simuler_vendeur()
        self.assertLess(c.taux_intervalle, T.taux_par_intervalle())
        self.assertGreater(c.taux_intervalle, 0.60)

    def test_le_vendeur_nu_a_sa_forme_fermee(self):
        c = T.simuler_vendeur()
        self.assertAlmostEqual(c.nu.taux, T.taux_du_vendeur_nu(), delta=0.02)

    def test_les_deux_esperances_sont_nulles(self):
        """L'hypothèse du guide, reprise telle quelle et vérifiée."""
        c = T.simuler_vendeur()
        self.assertAlmostEqual(c.couvert.moyenne, 0.0, delta=0.01)
        self.assertAlmostEqual(c.nu.moyenne, 0.0, delta=0.03)

    def test_les_deux_medianes_sont_positives(self):
        c = T.simuler_vendeur()
        self.assertGreater(c.nu.mediane, 0.05)
        self.assertGreaterEqual(c.couvert.mediane, 0.0)

    def test_la_position_couverte_est_un_pile_ou_face(self):
        c = T.simuler_vendeur()
        self.assertLess(abs(c.couvert.taux - 0.5), 0.05)

    def test_le_vendeur_nu_ne_gagne_jamais_plus_que_la_prime(self):
        for x in T._echantillon(1, True):
            self.assertLessEqual(x, 1.0 + 1e-9)

    def test_la_frequence_accumulee_descend_vers_un_demi(self):
        suite = [T.taux_de_m_intervalles(m) for m in T.INTERVALLES]
        self.assertAlmostEqual(suite[0], T.taux_par_intervalle(), places=9)
        for a, b in zip(suite, suite[1:]):
            self.assertLess(b, a)
        self.assertLess(suite[-1], 0.52)
        self.assertGreater(suite[-1], 0.5)

    def test_la_loi_du_khi_deux_est_controlee_par_simulation(self):
        """Une forme fermée ne se publie pas sans être confrontée."""
        from alp1.mc import Rng

        rng = Rng(T.SEED + 3)
        for m in (1, 5, 30):
            k = sum(1 for _ in range(20000)
                    if sum(rng.gauss() ** 2 for _ in range(m)) < m)
            self.assertAlmostEqual(k / 20000, T.taux_de_m_intervalles(m),
                                   delta=0.015)

    def test_l_histogramme_est_une_densite(self):
        for nu, borne in ((False, 0.7), (True, 3.0)):
            h = T.histogramme(1, 41, nu, borne)
            pas = 2.0 * borne / 41
            self.assertAlmostEqual(sum(f for _, f in h) * pas, 1.0, delta=0.02)

    def test_la_simulation_est_reproductible(self):
        T.simuler_vendeur.cache_clear()
        un = T.simuler_vendeur()
        T.simuler_vendeur.cache_clear()
        deux = T.simuler_vendeur()
        self.assertEqual(un, deux)


class TestLaCouvertureDiscrete(unittest.TestCase):
    """L'exposant est ajusté, jamais postulé."""

    def test_l_exposant_est_proche_d_un_demi(self):
        _, p = T.loi_de_dispersion()
        self.assertAlmostEqual(p, 0.5, delta=0.06)

    def test_l_ajustement_suit_la_mesure(self):
        for n in T.PAS_GRILLE:
            self.assertAlmostEqual(T.dispersion_ajustee(n), T.dispersion(n),
                                   delta=0.12 * T.dispersion(n))

    def test_la_dispersion_decroit_avec_la_couverture(self):
        vals = [T.dispersion(n) for n in T.PAS_GRILLE]
        for a, b in zip(vals, vals[1:]):
            self.assertLess(b, a)

    def test_l_esperance_ne_bouge_pas_avec_la_couverture(self):
        """Ce que la couverture n'achète pas, et c'est le sujet."""
        for n in T.PAS_GRILLE:
            c = T.simuler_vendeur(par_jour=n, n=T.N_GRILLE)
            self.assertAlmostEqual(c.couvert.moyenne, 0.0, delta=0.02)

    def test_le_nombre_de_couvertures_requis_inverse_la_loi(self):
        n = T.couvertures_pour_bruit(0.05)
        self.assertAlmostEqual(T.dispersion_ajustee(n), 0.05, places=6)

    def test_le_relief_a_son_maximum_au_fond(self):
        z = T.surface_dispersion()
        vals = [v for ligne in z for v in ligne]
        self.assertEqual(z[0][0], max(vals))


class TestLesDeuxHorloges(unittest.TestCase):
    """Le paramètre non observable, et ce que la calibration en fait."""

    def test_les_deux_conventions_sont_les_deux_bouts_du_parametre(self):
        self.assertAlmostEqual(T.jours_apparents(1.0), 3.0, places=9)
        self.assertAlmostEqual(T.jours_apparents(0.0), 0.0, places=12)

    def test_les_jours_apparents_ne_dependent_pas_de_l_echeance(self):
        """La prédiction de la section, et elle est exacte."""
        poids = T.poids_pour_apparents(1.0)
        self.assertAlmostEqual(T.jours_apparents(poids), 1.0, places=9)

    def test_la_calibration_inverse_les_jours_apparents(self):
        for cible in (0.5, 1.0, 1.5, 2.0):
            w = T.poids_pour_apparents(cible)
            self.assertAlmostEqual(T.jours_apparents(w), cible, places=9)

    def test_la_derive_a_poids_calibre_a_sa_forme_fermee(self):
        """`√((D−1)/(D−3)) − 1`, par une seconde route entièrement
        différente."""
        poids = T.poids_pour_apparents(1.0)
        for j in (4.0, 7.0, 14.0, 30.0, 90.0, 365.0):
            self.assertAlmostEqual(
                T.derive_implicite(j, poids),
                math.sqrt((j - 1.0) / (j - 3.0)) - 1.0, places=9)

    def test_la_convention_calendaire_n_exige_aucune_derive(self):
        for j in (7.0, 30.0, 180.0):
            self.assertAlmostEqual(T.derive_implicite(j, 1.0), 0.0, places=12)

    def test_la_derive_decroit_avec_l_echeance(self):
        poids = T.poids_pour_apparents(1.0)
        vals = [T.derive_implicite(j, poids) for j in (5.0, 10.0, 30.0, 90.0)]
        for a, b in zip(vals, vals[1:]):
            self.assertLess(b, a)

    def test_l_echeance_critique_est_le_point_de_croisement(self):
        poids = T.poids_pour_apparents(1.0)
        crit = T.echeance_critique(T.SPREAD_VOL, poids)
        self.assertAlmostEqual(T.derive_implicite(crit, poids), T.SPREAD_VOL,
                               places=5)

    def test_la_decote_observee_est_sous_l_annoncee(self):
        poids = T.poids_pour_apparents(1.0)
        for j in T.ECHEANCES_HORLOGE:
            self.assertLess(T.decote_observee(j, poids),
                            T.decote_calendaire(j))

    def test_le_rapport_des_deux_decotes_est_presque_constant(self):
        """C'est la racine qui le rend constant, et c'est le fait publié."""
        poids = T.poids_pour_apparents(1.0)
        rap = [T.decote_observee(j, poids) / T.decote_calendaire(j)
               for j in (14.0, 30.0, 90.0, 365.0)]
        self.assertLess(max(rap) - min(rap), 0.02)

    def test_le_relief_a_son_maximum_au_fond(self):
        z = T.surface_horloges()
        vals = [v for ligne in z for v in ligne]
        self.assertEqual(z[0][0], max(vals))
        self.assertEqual(min(vals), 0.0)


class TestLeSigne(unittest.TestCase):
    """À taux nul la région n'existe pas, et pas approximativement."""

    def test_a_taux_nul_la_region_est_vide(self):
        self.assertEqual(T.part_positive(0.0), 0.0)
        for jours in (7.0, 30.0, 365.0):
            self.assertEqual(T.frontiere_signe(jours / nv.JOURS_AN, r=0.0),
                             0.0)

    def test_la_frontiere_separe_bien_les_deux_signes(self):
        t = 90.0 / nv.JOURS_AN
        f = T.frontiere_signe(t, r=0.04)
        self.assertGreater(f, 0.0)
        self.assertGreater(T.termes_put(f * 0.98, 1.0, T.VOL_REF, t,
                                        0.04).total, 0.0)
        self.assertLess(T.termes_put(f * 1.02, 1.0, T.VOL_REF, t, 0.04).total,
                        0.0)

    def test_la_part_du_plan_croit_avec_le_taux(self):
        vals = [T.part_positive(r) for r in T.TAUX_GRILLE]
        for a, b in zip(vals, vals[1:]):
            self.assertLess(a, b)

    def test_la_frontiere_recule_avec_l_echeance(self):
        for r in (0.02, 0.04, 0.06):
            vals = [T.frontiere_signe(j / nv.JOURS_AN, r=r)
                    for j in (21.0, 90.0, 365.0)]
            for a, b in zip(vals, vals[1:]):
                self.assertLess(b, a)

    def test_le_relief_a_son_maximum_au_fond_et_son_arete_au_sol(self):
        z = T.surface_signe()
        vals = [v for ligne in z for v in ligne]
        self.assertEqual(z[0][0], max(vals))
        self.assertEqual(list(z[-1]), [0.0] * len(z[-1]))


class TestLaPreuve(unittest.TestCase):
    """Le budget d'information, appliqué à une prime de variance."""

    def test_un_avantage_reel_deplace_l_esperance(self):
        for pts in T.PRIMES:
            self.assertGreater(T.campagne_prime(pts).moyenne, 0.0)

    def test_la_dispersion_ne_bouge_pas_avec_l_avantage(self):
        """C'est ce qui rend le nombre d'expirations aussi sensible."""
        base = T.simuler_vendeur().couvert.ecart_type
        for pts in T.PRIMES:
            self.assertAlmostEqual(T.campagne_prime(pts).ecart_type, base,
                                   delta=0.15 * base)

    def test_le_cout_decroit_comme_le_carre_de_l_avantage(self):
        un = T.campagne_prime(1.0).annees
        deux = T.campagne_prime(2.0).annees
        self.assertAlmostEqual(deux, un / 4.0, delta=0.35 * un / 4.0)

    def test_l_avantage_qui_egale_la_soiree_est_dans_la_grille(self):
        seuil = T.avantage_pour_egaler_la_soiree()
        self.assertGreater(seuil, T.PRIMES_FINES[0])
        self.assertLess(seuil, T.PRIMES_FINES[-1])
        self.assertGreater(seuil, 1.0)

    def test_la_frequence_croit_avec_l_avantage(self):
        vals = [T.simuler_vendeur().couvert.taux] + [
            T.campagne_prime(p).taux for p in T.PRIMES]
        for a, b in zip(vals, vals[1:]):
            self.assertLess(a, b)

    def test_le_relief_a_son_maximum_au_fond(self):
        z = T.surface_preuve()
        vals = [v for ligne in z for v in ligne]
        self.assertEqual(z[0][0], max(vals))


class TestLeDecompte(unittest.TestCase):
    """Les verdicts sont comptés, jamais écrits."""

    def test_une_seule_affirmation_touche_a_la_direction(self):
        aff = T.affirmations()
        directions = [a for a in aff if a.grandeur == "la direction"]
        self.assertEqual(len(directions), 1)
        self.assertTrue(directions[0].negociable)

    def test_le_compte_par_grandeur_couvre_toutes_les_affirmations(self):
        self.assertEqual(sum(T.compte_par_grandeur().values()),
                         len(T.affirmations()))

    def test_les_familles_viennent_de_leurs_propres_modules(self):
        """Un total recopié est un total qui finit par mentir."""
        fam = dict(T.familles())
        self.assertEqual(fam["Gamma, partie XIX"], len(nv.affirmations()))
        self.assertEqual(fam["Delta, partie XX"], len(G.confusions()))
        self.assertEqual(fam["Thêta, partie XXI"], len(T.affirmations()))

    def test_aucune_affirmation_ne_donne_un_sens_negociable_ailleurs(self):
        """Le verdict de la série, vérifié sur les deux parties qui
        l'exposent."""
        self.assertEqual(sum(1 for a in nv.affirmations()
                             if a.directionnelle), 0)


class TestLesTables(unittest.TestCase):
    def setUp(self):
        self.tables = T.all_tables()

    def test_les_dix_tables_sont_la(self):
        self.assertEqual(len(self.tables), 10)

    def test_chaque_table_a_ses_colonnes(self):
        for cle, t in self.tables.items():
            for ligne in t.rows:
                self.assertEqual(len(ligne), len(t.headers), cle)

    def test_les_valeurs_sont_des_chaines_francaises(self):
        for cle, v in T.values().items():
            self.assertIsInstance(v, str, cle)
            self.assertNotIn(".", v.replace("&nbsp;", ""), cle)

    def test_chaque_table_a_une_note_et_une_legende(self):
        """Une table sans note est une table qu'on lira de travers."""
        for cle, t in self.tables.items():
            self.assertTrue(t.caption, cle)
            self.assertGreater(len(t.note or ""), 120, cle)


class TestLesPlanches(unittest.TestCase):
    def setUp(self):
        self.rendus = figth.render_all()

    def test_les_quinze_planches_sont_la(self):
        self.assertEqual(len(self.rendus), 15)

    def test_aucune_couleur_n_est_ecrite_en_dur(self):
        for cle, svg in self.rendus.items():
            self.assertEqual(re.findall(r"#[0-9a-fA-F]{6}", svg), [], cle)

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
        for cle in ("threlief", "threliefh", "threliefs", "threliefp"):
            self.assertIn('class="post"', self.rendus[cle], cle)
            self.assertIn('class="nuage', self.rendus[cle], cle)

    def test_toutes_les_graduations_tombent_dans_leur_domaine(self):
        """Une graduation hors domaine est tracée hors du cadre mais dans la
        boîte du SVG : aucun balayage de débordement ne la voit."""
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
            figth.render_all()
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
            figth.render_all()
        finally:
            Panel.path = og
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
