"""Les tests de « le prix de l'incertitude » — la partie XXII.

Trois familles, comme pour les trois parties d'options précédentes. Les
formes fermées sont contrôlées contre une différence finie ou contre une
réévaluation exacte. Les verdicts sont recalculés plutôt que relus. Et les
planches sont balayées pour ce qu'aucun rendu ne montre : une graduation hors
domaine, un tracé réduit à rien, une marque de gras publiée telle quelle.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import figvg
from alp1 import grandeurs as G
from alp1 import niveaux as nv
from alp1 import theta as th
from alp1 import vega as V


class TestLesFormesFermees(unittest.TestCase):
    """Rien ne se publie sans être confronté à autre chose que soi."""

    def test_le_vega_tombe_sur_la_difference_finie(self):
        for j in (7.0, 30.0, 365.0):
            t = j / V.JOURS_AN
            for m in (0.85, 1.0, 1.15):
                self.assertAlmostEqual(
                    V.vega(m * V.S_REF, V.S_REF, V.VOL_REF, t),
                    V.vega_numerique(m * V.S_REF, V.S_REF, V.VOL_REF, t),
                    delta=1e-4)

    def test_la_volga_tombe_sur_la_difference_finie(self):
        for j in (30.0, 365.0):
            t = j / V.JOURS_AN
            for m in (0.85, 1.0, 1.15):
                self.assertAlmostEqual(
                    V.volga(m * V.S_REF, V.S_REF, V.VOL_REF, t),
                    V.volga_numerique(m * V.S_REF, V.S_REF, V.VOL_REF, t),
                    delta=1e-3)

    def test_le_vega_est_le_meme_pour_un_call_et_un_put(self):
        """Par la parité, et c'est ce que le guide écrit."""
        h = 1e-6
        for m in (0.85, 1.0, 1.15):
            s = m * V.S_REF
            t = 90.0 / V.JOURS_AN
            dput = (th.put(s, V.S_REF, V.VOL_REF + h, t)
                    - th.put(s, V.S_REF, V.VOL_REF - h, t)) / (2.0 * h)
            self.assertAlmostEqual(V.vega(s, V.S_REF, V.VOL_REF, t,
                                          V.TAUX, V.DIVIDENDE),
                                   dput, delta=1e-4)

    def test_l_unite_du_pupitre_est_la_forme_fermee_sur_cent(self):
        t = 90.0 / V.JOURS_AN
        self.assertAlmostEqual(V.vega_par_point(V.S_REF, V.S_REF, V.VOL_REF, t)
                               * 100.0,
                               V.vega(V.S_REF, V.S_REF, V.VOL_REF, t),
                               places=12)

    def test_le_rapport_gamma_vega_est_exact_et_sans_strike(self):
        """`Γ/V = 1/(S²σT)`, à tout strike, et c'est une identité."""
        for j in (7.0, 90.0, 365.0):
            t = j / V.JOURS_AN
            for m in (0.85, 1.0, 1.2):
                s = m * V.S_REF
                mesure = (nv.gamma(s, V.S_REF, V.VOL_REF, t)
                          / V.vega(s, V.S_REF, V.VOL_REF, t))
                self.assertAlmostEqual(
                    mesure, V.rapport_gamma_vega(s, V.VOL_REF, t), places=12)

    def test_les_deux_identites_se_composent(self):
        """`|Θ₁|/V = σ/2T`, obtenu en composant avec la partie XIX."""
        for j in (30.0, 365.0):
            t = j / V.JOURS_AN
            t1 = abs(th.termes_call(V.S_REF, V.S_REF, V.VOL_REF, t, 0.0,
                                    0.0).decroissance)
            self.assertAlmostEqual(
                t1 / V.vega(V.S_REF, V.S_REF, V.VOL_REF, t),
                V.rapport_theta_vega(V.VOL_REF, t), places=10)

    def test_le_rapport_de_tenors_dement_le_nombre_publie(self):
        """La racine tient, le nombre non."""
        self.assertAlmostEqual(V.rapport_de_tenors(), 5.07, delta=0.02)
        self.assertLess(V.rapport_de_tenors(), math.sqrt(365.0 / 14.0))
        self.assertLess(V.rapport_de_tenors(), V.RAPPORT_ANNONCE - 0.3)

    def test_les_deux_pics_ont_la_meme_largeur(self):
        """La réfutation de la formule du guide, et elle se mesure."""
        for j in (7.0, 30.0, 90.0):
            t = j / V.JOURS_AN
            r = V.largeur_du_pic(t) / V.largeur_du_pic_gamma(t)
            self.assertLess(abs(r - 1.0), 0.06, j)


    def test_le_vanna_egale_ses_deux_derivees_croisees(self):
        """Le contrôle qui manquait : `∂Δ/∂σ` et `∂V/∂S` sont le même nombre.

        La première version de `vanna` oubliait un `√T` au dénominateur, et
        rien ne l'avait vu — la fonction n'était consommée par aucune table,
        aucune figure et aucun test. C'est le cas que la règle du dépôt vise :
        une forme fermée se contrôle contre une route indépendante, même
        quand personne ne s'en sert encore.
        """
        h = 1e-5
        for j in (7.0, 30.0, 90.0, 365.0):
            t = j / V.JOURS_AN
            for m in (0.85, 0.95, 1.0, 1.05, 1.15):
                s = V.S_REF * m
                par_delta = (G.delta_comptant(s, V.S_REF, V.VOL_REF + h, t,
                                              V.TAUX, V.DIVIDENDE)
                             - G.delta_comptant(s, V.S_REF, V.VOL_REF - h, t,
                                                V.TAUX, V.DIVIDENDE)) / (2 * h)
                par_vega = (V.vega(s + 0.01, V.S_REF, V.VOL_REF, t, V.TAUX,
                                   V.DIVIDENDE)
                            - V.vega(s - 0.01, V.S_REF, V.VOL_REF, t, V.TAUX,
                                     V.DIVIDENDE)) / 0.02
                ferme = V.vanna(s, V.S_REF, V.VOL_REF, t, V.TAUX,
                                V.DIVIDENDE)
                self.assertAlmostEqual(ferme, par_delta, places=4)
                self.assertAlmostEqual(ferme, par_vega, places=4)


class TestLesModes(unittest.TestCase):
    """Un véga net nul ne protège de rien."""

    def test_les_deux_livres_ont_un_vega_net_nul(self):
        for _, faire in V.LIVRES:
            self.assertAlmostEqual(V.vega_net(faire()), 0.0, places=8)

    def test_chaque_livre_est_aveugle_au_mode_de_l_autre(self):
        cal, peau = V.livre_calendrier(), V.livre_peau()
        self.assertGreater(abs(V.pl_livre(cal, V.mode_terme, 10.0)), 1.0)
        self.assertLess(abs(V.pl_livre(cal, V.mode_peau, 10.0)), 0.05)
        self.assertGreater(abs(V.pl_livre(peau, V.mode_peau, 10.0)), 1.0)
        self.assertLess(abs(V.pl_livre(peau, V.mode_terme, 10.0)), 0.05)

    def test_le_premier_ordre_est_nul_sous_un_choc_de_niveau(self):
        for _, faire in V.LIVRES:
            self.assertAlmostEqual(
                V.pl_au_premier_ordre(faire(), V.mode_niveau, 10.0), 0.0,
                places=8)

    def test_la_courbure_croit_comme_le_carre_du_choc(self):
        peau = V.livre_peau()
        un = V.pl_livre(peau, V.mode_niveau, 1.0)
        dix = V.pl_livre(peau, V.mode_niveau, 10.0)
        # Le carre est la loi dominante, pas la loi exacte : le troisieme
        # ordre en retire un cinquieme sur dix points, et le test le dit.
        self.assertGreater(dix / un, 60.0)
        self.assertLess(dix / un, 100.0)

    def test_le_sommet_de_la_parabole_est_au_choc_nul(self):
        peau = V.livre_peau()
        for c in (-3.0, -1.0, 1.0, 3.0):
            self.assertGreater(V.pl_livre(peau, V.mode_niveau, c),
                               V.pl_livre(peau, V.mode_niveau, 0.0))


class TestLaPonderation(unittest.TestCase):
    """La règle est sans échelle, la surface en a une."""

    def test_l_exposant_va_de_zero_a_un(self):
        for k in V.KAPPA_GRILLE:
            self.assertLess(V.exposant_effectif(1.0, k), 0.05)
            self.assertGreater(V.exposant_effectif(3650.0, k), 0.95)

    def test_l_exposant_croit_avec_le_tenor(self):
        for k in V.KAPPA_GRILLE:
            vals = [V.exposant_effectif(j, k) for j in V.ECHEANCES]
            for a, b in zip(vals, vals[1:]):
                self.assertLess(a, b)

    def test_le_tenor_de_l_exposant_est_inverse_de_la_vitesse(self):
        """Le produit ne dépend pas de la vitesse, et c'est le fait."""
        produits = [k * V.tenor_de_l_exposant(0.5, k) for k in V.KAPPA_GRILLE]
        self.assertLess(max(produits) / min(produits) - 1.0, 0.01)

    def test_la_regle_est_exacte_au_tenor_d_ancrage(self):
        for k in V.KAPPA_GRILLE:
            self.assertAlmostEqual(V.poids_modele(V.TENOR_REF, k), 1.0,
                                   places=12)
            self.assertAlmostEqual(V.poids_regle(V.TENOR_REF), 1.0, places=12)

    def test_aucune_vitesse_ne_sauve_la_regle(self):
        """Le contrôle de la section : le minimum existe et il reste haut."""
        k_opt, e_opt = V.kappa_minimax()
        self.assertGreater(e_opt, 0.25)
        for k in V.KAPPA_GRILLE:
            self.assertGreaterEqual(V.ecart_maximal(k), e_opt - 1e-9)

    def test_le_relief_a_son_maximum_au_fond(self):
        z = V.surface_poids()
        vals = [v for l in z for v in l]
        self.assertEqual(z[0][0], max(vals))


class TestLaBande(unittest.TestCase):
    """La courbure change de signe, et la bande se mesure."""

    def test_la_bande_est_bornee_par_les_deux_racines(self):
        for j in (7.0, 90.0, 365.0):
            t = j / V.JOURS_AN
            lo, hi = V.bande_de_courbure(t)
            self.assertLess(V.volga(V.S_REF, V.S_REF, V.VOL_REF, t), 0.0)
            self.assertGreater(V.volga(lo * 0.98 * V.S_REF, V.S_REF,
                                       V.VOL_REF, t), 0.0)
            self.assertGreater(V.volga(hi * 1.02 * V.S_REF, V.S_REF,
                                       V.VOL_REF, t), 0.0)

    def test_la_largeur_vaut_la_variance_fois_le_temps(self):
        for j in (7.0, 30.0, 90.0):
            t = j / V.JOURS_AN
            self.assertAlmostEqual(V.largeur_de_bande(t),
                                   V.VOL_REF ** 2 * t, delta=0.02 * V.VOL_REF
                                   ** 2 * t)

    def test_aucun_strike_n_y_tombe_aux_echeances_courtes(self):
        """Le fait de la section, et il se vérifie plutôt qu'il s'écrit."""
        self.assertLess(V.strikes_dans_la_bande(14.0 / V.JOURS_AN, 0.01), 1.0)
        self.assertGreater(V.strikes_dans_la_bande(365.0 / V.JOURS_AN, 0.01),
                           1.0)

    def test_le_relief_a_son_maximum_au_fond(self):
        z = V.surface_bande()
        vals = [v for l in z for v in l]
        self.assertEqual(z[0][0], max(vals))


class TestLeSeuil(unittest.TestCase):
    """Le seuil est une propriété de la position, jamais du marché."""

    def test_le_seuil_est_nul_a_la_monnaie(self):
        self.assertLess(abs(V.derive_equilibre(V.Ligne(-1.0, 1.0, 90.0))),
                        0.02)

    def test_le_seuil_est_negatif_dans_les_ailes(self):
        for m in (0.85, 0.90, 1.10, 1.20):
            self.assertLess(V.derive_equilibre(V.Ligne(-1.0, m, 90.0)),
                            -0.05)

    def test_le_seuil_croit_comme_le_carre_de_la_vol_de_vol(self):
        aile = V.Ligne(-1.0, 0.90, 90.0)
        un = V.derive_equilibre(aile, 0.5)
        deux = V.derive_equilibre(aile, 1.0)
        self.assertAlmostEqual(deux / un, 4.0, places=6)

    def test_le_seuil_mesure_annule_l_esperance(self):
        """Le contrôle : à la dérive mesurée, la moyenne est nulle."""
        for m in (0.90, 1.10):
            x = V.derive_equilibre_exacte(m, 90.0)
            moy = V._resume(V.simuler_vendeur(m, 90.0, V.NU_REF, x)).moyenne
            self.assertLess(abs(moy), 0.005, m)

    def test_la_forme_fermee_sous_estime_le_seuil(self):
        """Le troisième ordre pèse, et le dépôt publie les deux nombres."""
        for m in (0.90, 1.10):
            ferme = V.derive_equilibre(V.Ligne(-1.0, m, 90.0))
            mesure = V.derive_equilibre_exacte(m, 90.0)
            self.assertLess(mesure, ferme)
            self.assertLess(abs(mesure / ferme - 1.0), 0.40)

    def test_le_relief_a_son_maximum_au_fond(self):
        z = V.surface_seuil()
        vals = [v for l in z for v in l]
        self.assertEqual(z[0][0], max(vals))


class TestLaLoiDuVendeur(unittest.TestCase):
    """Une fois sur deux, exactement, et une espérance négative."""

    def test_la_frequence_vaut_un_demi_partout(self):
        """Le prix d'une option est monotone en volatilité."""
        for m in (0.85, 1.00, 1.15):
            for nu in (0.5, 1.0):
                r = V._resume(V.simuler_vendeur(m, 90.0, nu))
                self.assertLess(abs(r.taux - 0.5), 0.02, (m, nu))

    def test_l_esperance_est_negative_a_derive_nulle(self):
        for m in (0.85, 0.90, 1.10):
            self.assertLess(V._resume(V.simuler_vendeur(m, 90.0)).moyenne,
                            0.0)

    def test_le_gain_est_plafonne_et_la_perte_ne_l_est_pas(self):
        vals = V.simuler_vendeur(0.90, 90.0)
        plafond = V.Ligne(-1.0, 0.90, 90.0).prix(0.01) - V.Ligne(
            -1.0, 0.90, 90.0).prix(V.VOL_REF)
        self.assertLessEqual(max(vals), plafond + 1e-9)
        self.assertLess(min(vals), -2.0 * max(vals))

    def test_les_pertes_ne_sont_pas_plus_concentrees_qu_une_gaussienne(self):
        """La troisième réfutation de la partie, et elle se mesure."""
        vals = V.simuler_vendeur(0.90, 90.0)
        for part in (0.05, 0.10, 0.25):
            ecart = (V.concentration(vals, part)
                     - V.concentration_temoin(part))
            self.assertLess(abs(ecart), 0.03, part)

    def test_la_simulation_est_reproductible(self):
        V._tirages.cache_clear()
        un = V.simuler_vendeur(0.90, 90.0)
        V._tirages.cache_clear()
        self.assertEqual(un, V.simuler_vendeur(0.90, 90.0))


class TestLaPreuve(unittest.TestCase):
    def test_un_avantage_reel_deplace_l_esperance(self):
        for e in V.EXCES:
            self.assertGreater(V.campagne(e).moyenne, 0.0)

    def test_le_cout_decroit_comme_le_carre_de_l_avantage(self):
        un = V.campagne(1.0).annees
        deux = V.campagne(2.0).annees
        self.assertAlmostEqual(deux, un / 4.0, delta=0.30 * un / 4.0)

    def test_la_frequence_monte_a_peine(self):
        """Un avantage réel ne se voit pas dans le taux de réussite."""
        self.assertLess(V.campagne(1.0).taux, 0.72)
        self.assertGreater(V.campagne(1.0).taux, 0.5)

    def test_le_relief_a_son_maximum_au_fond(self):
        z = V.surface_preuve()
        vals = [v for l in z for v in l]
        self.assertEqual(z[0][0], max(vals))


class TestLeDecompte(unittest.TestCase):
    def test_une_seule_affirmation_touche_a_la_direction(self):
        self.assertEqual(V.compte_par_grandeur().get("la direction", 0), 1)

    def test_le_compte_couvre_toutes_les_affirmations(self):
        self.assertEqual(sum(V.compte_par_grandeur().values()),
                         len(V.affirmations()))

    def test_les_familles_viennent_de_leurs_propres_modules(self):
        fam = dict(V.familles())
        self.assertEqual(fam["Gamma, partie XIX"], len(nv.affirmations()))
        self.assertEqual(fam["Delta, partie XX"], len(G.confusions()))
        self.assertEqual(fam["Thêta, partie XXI"], len(th.affirmations()))
        self.assertEqual(fam["Véga, partie XXII"], len(V.affirmations()))


class TestLesTables(unittest.TestCase):
    def setUp(self):
        self.tables = V.all_tables()

    def test_les_dix_tables_sont_la(self):
        self.assertEqual(len(self.tables), 10)

    def test_chaque_table_a_ses_colonnes(self):
        for cle, t in self.tables.items():
            for ligne in t.rows:
                self.assertEqual(len(ligne), len(t.headers), cle)

    def test_chaque_table_a_une_note_et_une_legende(self):
        for cle, t in self.tables.items():
            self.assertTrue(t.caption, cle)
            self.assertGreater(len(t.note or ""), 120, cle)

    def test_les_valeurs_sont_des_chaines_francaises(self):
        for cle, v in V.values().items():
            self.assertIsInstance(v, str, cle)
            self.assertNotIn(".", v.replace("&nbsp;", ""), cle)


class TestLesPlanches(unittest.TestCase):
    def setUp(self):
        self.rendus = figvg.render_all()

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
        for cle in ("vgreliefp", "vgreliefb", "vgreliefs", "vgreliefpr"):
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
            figvg.render_all()
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
            figvg.render_all()
        finally:
            Panel.path = og
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
