"""Les tests de la partie XXVI — la convexité en volatilité, et le sourire.

Deux tests portent ici plus que les autres. Le premier exige que la bande où
le volga est négatif soit *le même ensemble* que celle de la partie XXII et
que celle de la partie XXIV : trois guides décrivent un intervalle sans savoir
qu'ils décrivent le même, et rien ne le garantit sinon une égalité écrite.

Le second est un plancher numérique. Une volatilité implicite s'obtient en
inversant un prix ; quand la correction de prix tombe au-dessous de la
résolution d'un flottant double, l'inversion ne rend plus un nombre mais du
bruit d'arrondi. `tenor_inversible` mesure où cela commence, et un test exige
que le raccourci du second ordre soit effectivement mort en deçà.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import figvo
from alp1 import grandeurs as G
from alp1 import theta as th
from alp1 import vanna as va
from alp1 import vega as vg
from alp1 import volga as VO


S, V = VO.S_REF, VO.VOL_REF


class TestLaFormeFermee(unittest.TestCase):
    """`𝒱·d₁d₂/σ` contre deux routes indépendantes."""

    def test_le_volga_egale_la_derivee_du_vega(self):
        for j in (7.0, 30.0, 90.0, 365.0):
            t = j / VO.JOURS_AN
            for m in (0.80, 0.95, 1.0, 1.05, 1.25):
                self.assertAlmostEqual(VO.volga(S * m, S, V, t),
                                       VO.volga_par_vega(S * m, S, V, t),
                                       places=4, msg=(j, m))

    def test_il_egale_la_difference_seconde_du_prix(self):
        for j in (30.0, 90.0, 365.0):
            t = j / VO.JOURS_AN
            for m in (0.85, 1.0, 1.15):
                self.assertAlmostEqual(VO.volga(S * m, S, V, t),
                                       VO.volga_par_prix(S * m, S, V, t),
                                       places=2, msg=(j, m))

    def test_il_s_annule_aux_deux_bords_de_la_bande(self):
        """Le volga est nul là où l'un des deux arguments l'est."""
        for j in (7.0, 30.0, 365.0):
            t = j / VO.JOURS_AN
            lo, hi = VO.bande_negative(t)
            for m in (lo, hi):
                self.assertLess(abs(VO.volga(S, S / m, V, t)), 1e-9, (j, m))

    def test_il_est_negatif_strictement_dedans(self):
        for j in (7.0, 30.0, 365.0):
            t = j / VO.JOURS_AN
            lo, hi = VO.bande_negative(t)
            m = math.sqrt(lo * hi)
            self.assertLess(VO.volga(S, S / m, V, t), 0.0, j)

    def test_le_rapport_au_vega_ne_depend_pas_du_niveau(self):
        for j in (30.0, 180.0):
            t = j / VO.JOURS_AN
            a = VO.volga(S * 1.2, S, V, t) / vg.vega(S * 1.2, S, V, t)
            b = VO.volga(2 * S * 1.2, 2 * S, V, t) / vg.vega(2 * S * 1.2,
                                                             2 * S, V, t)
            self.assertAlmostEqual(a, b, places=6, msg=j)


class TestLaBandeEstLaMeme(unittest.TestCase):
    """Le troisième nom d'un seul intervalle."""

    def test_elle_a_la_largeur_de_celle_de_la_partie_XXII(self):
        """Exactement la même largeur — les deux racines sont les mêmes."""
        for j in (7.0, 30.0, 90.0, 365.0):
            t = j / VO.JOURS_AN
            a = VO.bande_negative(t)
            b = vg.bande_de_courbure(t)
            self.assertAlmostEqual(math.log(a[1] / a[0]),
                                   math.log(b[1] / b[0]), places=12, msg=j)

    def test_le_portage_seul_separe_les_deux_centres(self):
        """Et c'est la question de la partie XXIII : quelle variable fixe-t-on ?"""
        for j in (7.0, 30.0, 365.0):
            t = j / VO.JOURS_AN
            a = VO.bande_negative(t)
            b = vg.bande_de_courbure(t)
            ca = 0.5 * (math.log(a[0]) + math.log(a[1]))
            cb = 0.5 * (math.log(b[0]) + math.log(b[1]))
            self.assertAlmostEqual(cb - ca, VO.decalage_de_portage(t),
                                   places=12, msg=j)

    def test_les_deux_centres_coincident_a_portage_nul(self):
        self.assertAlmostEqual(VO.decalage_de_portage(1.0, 0.02, 0.02), 0.0,
                               places=15)

    def test_elle_egale_celle_de_la_partie_XXIV(self):
        for j in (14.0, 30.0, 180.0):
            t = j / VO.JOURS_AN
            self.assertAlmostEqual(VO.largeur_de_bande(t),
                                   va.largeur_de_desobeissance(t),
                                   places=12, msg=j)

    def test_sa_largeur_en_logarithme_vaut_sigma_carre_T(self):
        for j in (7.0, 30.0, 365.0):
            t = j / VO.JOURS_AN
            lo, hi = VO.bande_negative(t)
            self.assertAlmostEqual(math.log(hi / lo), V * V * t, places=9,
                                   msg=j)

    def test_aucun_strike_d_une_grille_au_pour_cent_n_y_tombe(self):
        self.assertLess(VO.strikes_dans_la_bande(30.0 / VO.JOURS_AN, 0.01),
                        1.0)


class TestLaCorde(unittest.TestCase):
    def test_le_prix_a_la_monnaie_est_une_droite(self):
        t = 90.0 / VO.JOURS_AN
        self.assertLess(VO.ecart_a_la_corde(1.0, t), 0.002)

    def test_l_aile_ne_l_est_pas(self):
        t = 90.0 / VO.JOURS_AN
        self.assertGreater(VO.ecart_a_la_corde(1.30, t), 0.20)

    def test_l_ecart_croit_avec_la_distance(self):
        t = 90.0 / VO.JOURS_AN
        vals = [VO.ecart_a_la_corde(m, t)
                for m in (1.0, 1.05, 1.10, 1.20, 1.30)]
        for a, b in zip(vals, vals[1:]):
            self.assertLess(a, b)


class TestLaCrete(unittest.TestCase):
    """Ce que la planche du relief affirme."""

    def test_elle_s_eloigne_de_la_monnaie_avec_l_echeance(self):
        lieux = [VO.crete_du_volga(j / VO.JOURS_AN)
                 for j in (5.0, 10.0, 21.0, 45.0, 90.0, 180.0)]
        for a, b in zip(lieux, lieux[1:]):
            self.assertLess(a, b)

    def test_le_balayage_est_stable_au_pas_dix_fois_plus_fin(self):
        for j in (10.0, 90.0, 180.0):
            t = j / VO.JOURS_AN
            self.assertAlmostEqual(VO.crete_du_volga(t),
                                   VO.crete_du_volga(t, n=20000),
                                   places=2, msg=j)

    def test_la_grille_de_la_surface_encadre_la_crete(self):
        """Sans quoi la planche montrerait une rampe, pas une crête."""
        haut = max(VO.SURF_MONEYNESS)
        for j in VO.SURF_ECHEANCE:
            self.assertLess(VO.crete_du_volga(j / VO.JOURS_AN), haut, j)


class TestLesTroisRoutes(unittest.TestCase):
    def test_elles_convergent_a_l_echeance_longue(self):
        t = 2.0
        e = VO.sourire_exact(70.0, t)
        self.assertLess(abs(VO.sourire_second_ordre(70.0, t) - e), 0.002)
        self.assertLess(abs(VO.sourire_naif(70.0, t) - e), 0.005)

    def test_elles_divergent_a_l_echeance_courte(self):
        t = 30.0 / VO.JOURS_AN
        e = VO.sourire_exact(70.0, t)
        self.assertGreater(VO.sourire_naif(70.0, t) - e, 0.15)
        self.assertLess(VO.sourire_second_ordre(70.0, t) - e, -0.03)

    def test_le_sourire_exact_est_nul_a_la_monnaie(self):
        for j in (30.0, 90.0, 365.0):
            t = j / VO.JOURS_AN
            self.assertLess(abs(VO.sourire_exact(S, t) - V), 0.001, j)

    def test_le_sourire_exact_monte_des_deux_cotes(self):
        t = 30.0 / VO.JOURS_AN
        for k in (70.0, 80.0, 90.0):
            self.assertGreater(VO.sourire_exact(k, t), V, k)
        for k in (110.0, 120.0, 130.0):
            self.assertGreater(VO.sourire_exact(k, t), V, k)

    def test_le_prix_exact_est_insensible_a_la_finesse_de_la_quadrature(self):
        """La route de référence ne doit rien devoir à sa grille."""
        t = 30.0 / VO.JOURS_AN
        avant = VO.N_QUAD
        vus = []
        try:
            for n in (200, 400, 1200):
                VO.prix_exact.cache_clear()
                VO.N_QUAD = n
                vus.append(VO.prix_exact(70.0, t))
        finally:
            VO.N_QUAD = avant
            VO.prix_exact.cache_clear()
        for v in vus[1:]:
            self.assertAlmostEqual(v, vus[0], places=9)


class TestLeRetournement(unittest.TestCase):
    def test_il_tombe_dans_la_fenetre_du_guide(self):
        k, _ = VO.retournement(30.0 / VO.JOURS_AN)
        self.assertGreater(k, VO.FENETRE[0] * S)
        self.assertLess(k, S)

    def test_l_exact_ne_se_retourne_pas(self):
        t = 30.0 / VO.JOURS_AN
        k, _ = VO.retournement(t)
        self.assertGreater(VO.sourire_exact(k - 5.0, t),
                           VO.sourire_exact(k, t))

    def test_le_second_ordre_se_retourne_bien(self):
        t = 30.0 / VO.JOURS_AN
        k, v = VO.retournement(t)
        self.assertGreater(v, VO.sourire_second_ordre(k - 5.0, t))
        self.assertGreater(v, VO.sourire_second_ordre(k + 5.0, t))


class TestLePlancherNumerique(unittest.TestCase):
    """Le piège que la planche a trouvé : une inversion sans contenu."""

    def test_le_tenor_inversible_croit_avec_la_distance(self):
        a = VO.tenor_inversible(90.0)
        b = VO.tenor_inversible(80.0)
        c = VO.tenor_inversible(70.0)
        self.assertLess(a, b)
        self.assertLess(b, c)

    def test_le_poids_est_au_seuil_a_ce_tenor(self):
        for k in (70.0, 80.0, 90.0):
            j = VO.tenor_inversible(k)
            self.assertAlmostEqual(
                VO.poids_de_la_correction(k, j / VO.JOURS_AN)
                / VO.PLANCHER_INVERSION, 1.0, places=2, msg=k)

    def test_sous_ce_tenor_la_correction_ne_change_pas_le_flottant(self):
        k = 70.0
        j = 0.5 * VO.tenor_inversible(k)
        t = j / VO.JOURS_AN
        prix = th.call(S, k, V, t, VO.TAUX, VO.DIVIDENDE)
        corrige = prix + 0.5 * VO.volga(S, k, V, t) * VO.ecart_type_vol() ** 2
        self.assertEqual(prix, corrige)

    def test_le_tenor_publie_reste_tres_au_dessus_du_plancher(self):
        """Le mois du document est mille fois au-dessus, et il faut le voir."""
        t = 30.0 / VO.JOURS_AN
        self.assertGreater(VO.poids_de_la_correction(70.0, t),
                           100.0 * VO.PLANCHER_INVERSION)


class TestLePoidsDeLaCorrection(unittest.TestCase):
    """Le critère usuel pointe à l'envers, et c'est le fait de la section."""

    def test_le_maximum_tombe_la_ou_les_routes_sont_justes(self):
        t = 30.0 / VO.JOURS_AN
        k, _ = VO.pic_du_poids(t)
        self.assertLess(abs(VO.sourire_second_ordre(k, t)
                            - VO.sourire_exact(k, t)), 0.005)

    def test_il_s_annule_la_ou_elles_echouent(self):
        t = 30.0 / VO.JOURS_AN
        self.assertLess(VO.poids_de_la_correction(72.0, t), 1e-4)
        self.assertGreater(abs(VO.sourire_second_ordre(72.0, t)
                               - VO.sourire_exact(72.0, t)), 0.03)

    def test_il_ne_depasse_jamais_deux_pour_cent_du_prix(self):
        t = 30.0 / VO.JOURS_AN
        self.assertLess(VO.pic_du_poids(t)[1], 0.02)


class TestLesChocs(unittest.TestCase):
    def test_le_rapport_depasse_deux(self):
        for j in VO.TENORS_CHOC:
            self.assertGreater(VO.rapport_des_chocs(j), 2.0, j)

    def test_il_decroit_avec_l_echeance(self):
        vals = [VO.rapport_des_chocs(j) for j in (14.0, 30.0, 60.0, 180.0)]
        for a, b in zip(vals, vals[1:]):
            self.assertGreater(a, b)

    def test_le_tenor_du_guide_est_le_plus_faible_des_trois(self):
        vals = [VO.rapport_des_chocs(j) for j in VO.TENORS_CHOC]
        self.assertEqual(min(vals), vals[-1])

    def test_le_cout_est_compte_positivement_et_croit_avec_le_choc(self):
        """Le module publie un coût, la planche en trace l'opposé."""
        for j in VO.TENORS_CHOC:
            petit = VO.perte_du_vendeur(j, VO.CHOC_PETIT)
            grand = VO.perte_du_vendeur(j, VO.CHOC_GRAND)
            self.assertGreater(petit, 0.0, j)
            self.assertGreater(grand, petit, j)


class TestLePapillon(unittest.TestCase):
    def test_il_vend_du_vega_a_tout_delta(self):
        for d in (0.05, 0.10, 0.25, 0.40):
            self.assertLess(VO.papillon(d, 90.0).part_de_vega, 0.0, d)

    def test_le_defaut_grandit_quand_les_ailes_s_eloignent(self):
        vals = [abs(VO.papillon(d, 90.0).part_de_vega)
                for d in (0.40, 0.25, 0.10, 0.05)]
        for a, b in zip(vals, vals[1:]):
            self.assertLess(a, b)

    def test_la_ponderation_annule_exactement_le_vega(self):
        for d in (0.10, 0.25, 0.40):
            p = VO.papillon(d, 90.0)
            net = p.poids_neutre * p.vega_ailes - p.vega_corps
            self.assertAlmostEqual(net, 0.0, places=9, msg=d)

    def test_elle_augmente_le_volga(self):
        for d in (0.10, 0.25, 0.40):
            p = VO.papillon(d, 90.0)
            self.assertGreater(p.volga_neutre, p.volga_net, d)

    def test_le_defaut_ne_depend_presque_pas_de_l_echeance(self):
        vals = [VO.papillon(0.25, j).part_de_vega
                for j in (10.0, 45.0, 180.0, 365.0)]
        self.assertLess(max(vals) - min(vals), 0.05)


class TestLeDecompte(unittest.TestCase):
    def test_aucune_affirmation_ne_touche_a_la_direction(self):
        self.assertEqual(VO.compte_par_grandeur().get("la direction", 0), 0)

    def test_le_decompte_se_referme(self):
        self.assertEqual(sum(VO.compte_par_grandeur().values()),
                         len(VO.affirmations()))

    def test_le_cumul_des_huit_parties_est_compte(self):
        self.assertEqual(sum(n for _, n in VO.familles()),
                         int(VO.values()["vo_total_options"]))

    def test_les_grandeurs_sont_celles_du_document(self):
        for a in VO.affirmations():
            self.assertIn(a.grandeur,
                          ("la direction", "l'horloge", "le risque", "rien"),
                          a.enonce)


class TestLesSurfaces(unittest.TestCase):
    def test_les_quatre_surfaces_ont_leur_maximum_au_fond(self):
        for nom, z in (("volga", VO.surface_volga()),
                       ("sourire", VO.surface_sourire()),
                       ("artefact", VO.surface_artefact()),
                       ("papillon", VO.surface_papillon())):
            haut = max(max(l) for l in z)
            lignes = len(z)
            cols = len(z[0])
            trouve = [(i, j) for i in range(lignes) for j in range(cols)
                      if z[i][j] == haut]
            i, j = trouve[0]
            self.assertLess(i, lignes / 2, nom)
            self.assertLess(j, cols / 2 + 1, nom)

    def test_chaque_surface_est_rectangulaire(self):
        for z in (VO.surface_volga(), VO.surface_sourire(),
                  VO.surface_artefact(), VO.surface_papillon()):
            self.assertEqual(len({len(l) for l in z}), 1)


class TestLesTables(unittest.TestCase):
    def setUp(self):
        self.tables = VO.all_tables()

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
        for cle, v in VO.values().items():
            self.assertIsInstance(v, str, cle)
            self.assertNotIn(".", v.replace("&nbsp;", ""), cle)


class TestLesPlanches(unittest.TestCase):
    def setUp(self):
        self.rendus = figvo.render_all()

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
        for cle in ("vorelief", "voreliefs", "voreliefa", "voreliefp"):
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
            figvo.render_all()
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
            figvo.render_all()
        finally:
            Panel.path = og
        self.assertEqual(hits, [])

    def test_le_domaine_est_declare_avant_les_traces(self):
        """Le piège de la partie XXII, retrouvé dans la planche de la corde.

        Un tracé posé avant `domain` se dessine dans le domaine par défaut,
        puis le découpage le réduit à presque rien. Aucun balayage ne le voit ;
        seule l'enveloppe de `Panel.path` le trouve, et elle n'y arrive que si
        l'on compte les points hors domaine plutôt que les points tracés.
        """
        from alp1.figterm import Panel

        hits = []
        og_path, og_dom = Panel.path, Panel.domain

        def path(self, pts, *a, **k):
            if not getattr(self, "_domaine_declare", False):
                hits.append(self.title)
            return og_path(self, pts, *a, **k)

        def domain(self, *a, **k):
            self._domaine_declare = True
            return og_dom(self, *a, **k)

        Panel.path, Panel.domain = path, domain
        try:
            figvo.render_all()
        finally:
            Panel.path, Panel.domain = og_path, og_dom
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
