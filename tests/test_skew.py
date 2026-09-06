"""Les tests de la partie XXIX — le skew et le sourire.

Quatre tests portent ici plus que les autres. Le premier exige que la route
exacte du risk reversal — qui résout un point fixe, le delta dépendant de la
volatilité qui dépend du strike qui dépend du delta — se referme sur sa forme
fermée du premier ordre. Le deuxième exige que **le décalage d'un demi entre
l'exposant du risk reversal et celui de la pente locale tienne sur toute la
grille du paramètre libre**, ce qui le sépare d'une coïncidence : c'est le
résultat de la partie. Le troisième exige que la loi nulle de la corrélation
de rang, simulée, redonne le seuil de Fisher. Le quatrième exige que le véga
net d'un risk reversal soit nul et son delta net un demi — l'objet par lequel
on prétend négocier la forme de la surface est une position directionnelle.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import figsk
from alp1 import grandeurs as G
from alp1 import implicite as I
from alp1 import skew as K
from alp1 import vega as vg

S, V = K.S_REF, K.VOL_REF


class TestLaPeau(unittest.TestCase):
    def test_elle_vaut_la_volatilite_a_la_monnaie(self):
        for t in (7.0, 30.0, 365.0):
            self.assertAlmostEqual(K.peau(0.0, t / K.JOURS_AN), V, places=12)

    def test_elle_descend_a_droite_pour_un_indice(self):
        """Le skew d'un indice actions est descendant, et le guide le dit."""
        t = 30.0 / K.JOURS_AN
        for k in (-0.10, -0.05, 0.05, 0.10):
            self.assertGreater(K.peau(-abs(k), t), K.peau(abs(k), t))

    def test_la_pente_locale_porte_l_exposant_declare(self):
        for h in K.H_GRILLE:
            a = K.pente_locale(30.0 / K.JOURS_AN, h)
            b = K.pente_locale(120.0 / K.JOURS_AN, h)
            self.assertAlmostEqual(b / a, 4.0 ** (-h), places=10, msg=str(h))

    def test_la_courbure_porte_le_meme_exposant_que_la_pente(self):
        """Le défaut du premier jet, et il se mesurait sur le résultat.

        Une surface où la pente s'aplatit et où la courbure reste laisse la
        seconde dominer l'aile aux grands exposants, et le décalage d'un
        demi — le résultat de la partie — s'y dégradait de moitié.
        """
        for h in (0.25, 0.75):
            t0, t1 = 30.0 / K.JOURS_AN, 120.0 / K.JOURS_AN
            # La courbure se lit sur la différence seconde à la monnaie.
            def c(t):
                e = 0.01
                return (K.peau(e, t, h) - 2.0 * K.peau(0.0, t, h)
                        + K.peau(-e, t, h)) / (e * e)
            self.assertAlmostEqual(c(t1) / c(t0), 4.0 ** (-h), places=6,
                                   msg=str(h))


class TestLesConventions(unittest.TestCase):
    def test_le_strike_d_un_delta_rend_ce_delta(self):
        """La route exacte résout un point fixe ; il faut qu'il converge."""
        for jours in K.TENORS:
            t = jours / K.JOURS_AN
            for delta in (0.25, 0.50, 0.75):
                k_log = K.moneyness_du_delta(delta, t)
                k = K.strike_de_moneyness(k_log, t)
                vol = K.peau(k_log, t)
                mesure = G.delta_comptant(S, k, vol, t, K.TAUX, K.DIVIDENDE)
                self.assertAlmostEqual(mesure, delta, places=6,
                                       msg=f"{jours} {delta}")

    def test_la_forme_fermee_suit_la_route_exacte(self):
        """Le premier ordre contre le point fixe, sur toute la grille."""
        for jours in K.TENORS:
            t = jours / K.JOURS_AN
            a = K.risk_reversal(t)
            b = K.risk_reversal_ferme(t)
            self.assertLess(abs(a - b) / abs(b), 0.12, str(jours))

    def test_le_risk_reversal_est_positif_sous_un_skew_descendant(self):
        for jours in K.TENORS:
            self.assertGreater(K.risk_reversal(jours / K.JOURS_AN), 0.0,
                               str(jours))

    def test_la_bande_sondee_croit_en_racine_du_temps(self):
        """Le fait dont tout le reste de la partie découle."""
        a = K.largeur_sondee(30.0 / K.JOURS_AN, h=0.0)
        b = K.largeur_sondee(120.0 / K.JOURS_AN, h=0.0)
        self.assertAlmostEqual(b / a, 2.0, delta=0.06)

    def test_la_bande_sondee_croit_avec_la_volatilite(self):
        """L'argument du guide est juste du comptant et muet de la vol."""
        t = 30.0 / K.JOURS_AN
        suite = [K.largeur_sondee(t, vol_atm=v) for v in K.VOLS]
        for a, b in zip(suite, suite[1:]):
            self.assertGreater(b, a)
        self.assertGreater(suite[-1] / suite[0], 2.5)

    def test_la_bande_fixe_ne_bouge_pas(self):
        """Ce qui sépare les deux conventions, et c'est tout ce qui les sépare."""
        self.assertAlmostEqual(K.LARGEUR_FIXE, math.log(1.10 / 0.90),
                               places=12)

    def test_le_rapport_des_conventions_croit_avec_l_echeance(self):
        suite = [K.rapport_des_conventions(j / K.JOURS_AN) for j in K.TENORS]
        for a, b in zip(suite, suite[1:]):
            self.assertGreater(b, a)


class TestL_exposant(unittest.TestCase):
    """Le résultat de la partie, et ce qui le sépare d'une coïncidence."""

    def test_les_deux_conventions_a_bande_fixe_portent_moins_H(self):
        for h in K.H_GRILLE:
            self.assertAlmostEqual(K.exposant_de_la_pente_locale(h), -h,
                                   places=2, msg=str(h))
            self.assertAlmostEqual(K.exposant_de_la_pente_fixe(h), -h,
                                   places=2, msg=str(h))

    def test_le_risk_reversal_porte_un_demi_moins_H(self):
        for h in K.H_GRILLE:
            self.assertAlmostEqual(K.exposant_du_risk_reversal(h), 0.5 - h,
                                   delta=0.03, msg=str(h))

    def test_le_decalage_vaut_un_demi_sur_toute_la_grille(self):
        """Ce qui en fait un résultat plutôt qu'un réglage de paramètres."""
        vals = [K.decalage_des_exposants(h) for h in K.H_GRILLE]
        for v in vals:
            self.assertAlmostEqual(v, 0.5, delta=0.03)
        self.assertLess(max(vals) - min(vals), 0.02)

    def test_il_se_degrade_avec_la_volatilite_et_le_mecanisme_est_connu(self):
        """Une nuance que la mesure impose, et qui confirme le mécanisme.

        Le premier ordre suppose une bande étroite ; celle du risk reversal
        s'élargit avec `σ√T`. Le décalage vaut donc un demi à trois
        dix-millièmes près à basse volatilité, et en perd un dixième à
        quarante-cinq pour cent. *Un écart qui va dans le sens que le
        mécanisme prédit est un contrôle, pas un défaut.*
        """
        vals = [K.decalage_des_exposants(vol_atm=v) for v in K.VOLS]
        for a, b in zip(vals, vals[1:]):
            self.assertLess(b, a)
        self.assertAlmostEqual(vals[0], 0.5, delta=0.01)
        self.assertGreater(vals[-1], 0.35)

    def test_le_verdict_bascule_au_bon_endroit(self):
        """Le RR ne s'aplatit qu'au-delà d'un demi, les deux autres avant."""
        self.assertFalse(K.s_aplatit(
            lambda t, h, vol_atm=V: K.risk_reversal(t, h, vol_atm=vol_atm),
            0.25))
        self.assertTrue(K.s_aplatit(
            lambda t, h, vol_atm=V: K.risk_reversal(t, h, vol_atm=vol_atm),
            1.0))
        self.assertTrue(K.s_aplatit(
            lambda t, h, vol_atm=V: K.pente_moneyness_fixe(
                t, h, vol_atm=vol_atm), 0.25))

    def test_le_basculement_est_a_un_demi(self):
        self.assertAlmostEqual(K.h_du_basculement(), 0.5, places=12)


class TestLaPuissance(unittest.TestCase):
    def test_le_seuil_decroit_en_racine_de_n(self):
        a = K.seuil_de_correlation(100.0)
        b = K.seuil_de_correlation(400.0)
        self.assertAlmostEqual(a / b, 2.0, delta=0.02)

    def test_la_loi_nulle_redonne_le_seuil_de_fisher(self):
        """La forme fermée contrôlée contre quatre mille tirages."""
        for n in (252, 495, 1000):
            a = K.seuil_de_correlation(n)
            b = K.seuil_mesure(n)
            self.assertLess(abs(a - b) / a, 0.08, str(n))

    def test_la_loi_nulle_est_centree(self):
        """Ce qui se vérifie plutôt qu'il ne se suppose."""
        for n in (252, 495):
            self.assertLess(abs(K.quantile_de_la_loi_nulle(0.50, n)), 0.02,
                            str(n))

    def test_le_nombre_publie_tombe_dans_la_loi_nulle(self):
        """Le guide a raison de ne rien conclure."""
        rho = K.TEST_PUBLIE["correlation"]
        self.assertGreater(rho, K.quantile_de_la_loi_nulle(0.025, 495))
        self.assertLess(rho, K.quantile_de_la_loi_nulle(0.975, 495))
        self.assertLess(abs(K.ecarts_types_du_publie()), 1.0)

    def test_un_effet_plausible_aurait_ete_indetectable(self):
        """Le point de la partie : l'échantillon ne pouvait pas conclure."""
        self.assertGreater(K.seances_pour_correlation(0.05),
                           K.TEST_PUBLIE["seances"])

    def test_la_transformation_de_fisher_est_exacte(self):
        """`atanh` et non son premier ordre, et les deux coïncident en bas."""
        for rho in (0.01, 0.03, 0.05):
            approx = (K.Z_95 / rho) ** 2 + 3.0
            self.assertAlmostEqual(K.seances_pour_correlation(rho) / approx,
                                   1.0, delta=0.01, msg=str(rho))
        self.assertLess(K.seances_pour_correlation(0.70),
                        (K.Z_95 / 0.70) ** 2 + 3.0)

    def test_le_plancher_de_l_approximation_est_signale(self):
        """Un nombre qui a l'air d'une réponse et n'en est pas une."""
        self.assertTrue(K.borne_de_l_approximation(0.70))
        self.assertFalse(K.borne_de_l_approximation(0.05))


class TestLesRegimes(unittest.TestCase):
    def test_sticky_delta_ne_corrige_rien(self):
        """Par définition : le sourire suit le comptant, la vol ne bouge pas."""
        t = 30.0 / K.JOURS_AN
        k = K.strike_de_moneyness(-0.05, t)
        k_log = math.log(k / K.forward(S, t))
        vol = K.peau(k_log, t)
        attendu = G.delta_comptant(S, k, vol, t, K.TAUX, K.DIVIDENDE)
        self.assertAlmostEqual(K.delta_du_regime(K.REGIMES[0], k, t), attendu,
                               places=12)

    def test_les_trois_regimes_sont_ordonnes(self):
        """Le facteur croît, donc la correction aussi, à pente négative."""
        t = 30.0 / K.JOURS_AN
        for km in (-0.10, -0.05, 0.05):
            k = K.strike_de_moneyness(km, t)
            ds = [K.delta_du_regime(r, k, t) for r in K.REGIMES]
            for a, b in zip(ds, ds[1:]):
                self.assertGreater(b, a, str(km))

    def test_la_correction_porte_le_vega_et_non_le_vanna(self):
        """Le résultat de la partie XXIV, importé et non recopié."""
        t = 30.0 / K.JOURS_AN
        k = K.strike_de_moneyness(-0.05, t)
        k_log = math.log(k / K.forward(S, t))
        vol = K.peau(k_log, t)
        attendu = (G.delta_comptant(S, k, vol, t, K.TAUX, K.DIVIDENDE)
                   + vg.vega(S, k, vol, t, K.TAUX, K.DIVIDENDE)
                   * K.pente_par_point(t))
        self.assertAlmostEqual(K.delta_du_regime(K.REGIMES[1], k, t), attendu,
                               places=12)

    def test_l_etendue_a_la_monnaie_ne_depend_pas_de_l_echeance(self):
        """Une affirmation écrite d'avance, réfutée par la mesure.

        On avait écrit que le sommet de la surface était aux échéances
        longues, où le véga est le plus grand. Il ne l'est pas : le véga
        croît en `√T` exactement autant que la pente locale décroît, donc
        leur produit est constant à l'exposant retenu.
        """
        vals = []
        for jours in (7.0, 45.0, 180.0, 365.0):
            t = jours / K.JOURS_AN
            vals.append(K.ecart_des_regimes(K.strike_de_moneyness(0.0, t), t))
        self.assertLess(max(vals) - min(vals), 0.06)

    def test_la_forme_fermee_de_l_etendue_suit_la_mesure(self):
        for jours in (7.0, 45.0, 180.0, 365.0):
            t = jours / K.JOURS_AN
            a = K.etendue_a_la_monnaie_ferme(t)
            b = K.ecart_des_regimes(K.strike_de_moneyness(0.0, t), t)
            self.assertLess(abs(a - b) / b, 0.25, str(jours))

    def test_l_aile_rattrape_avec_l_echeance(self):
        """Ce qui monte vraiment sur la surface."""
        vals = []
        for jours in (7.0, 45.0, 180.0, 365.0):
            t = jours / K.JOURS_AN
            vals.append(K.ecart_des_regimes(
                K.strike_de_moneyness(-0.06, t), t))
        for a, b in zip(vals, vals[1:]):
            self.assertGreater(b, a)

    def test_l_etendue_est_positive_partout(self):
        t = 30.0 / K.JOURS_AN
        for km in (-0.10, -0.05, 0.0, 0.05, 0.10):
            self.assertGreater(
                K.ecart_des_regimes(K.strike_de_moneyness(km, t), t), 0.0,
                str(km))

    def test_une_option_seule_coute_peu(self):
        """L'affirmation écrite d'avance, et ce que la mesure a rendu.

        On avait écrit que l'erreur de régime dépassait la friction ; elle
        vaut quelques centièmes par option. Ce qui rend la remarque du
        guide juste est le mot « simultanément », que le test suivant
        chiffre.
        """
        t = 30.0 / K.JOURS_AN
        k = K.strike_de_moneyness(-0.05, t)
        self.assertLess(K.cout_en_frictions(k, t), 0.10)
        self.assertGreater(K.cout_en_frictions(k, t), 0.0)

    def test_le_livre_qui_coute_une_friction_est_modeste(self):
        """Le nombre que le guide ne donne pas et qui rend sa phrase lisible."""
        t = 30.0 / K.JOURS_AN
        for m in (-0.10, -0.05, 0.0, 0.05):
            n = K.options_pour_une_friction(K.strike_de_moneyness(m, t), t)
            self.assertGreater(n, 10.0, str(m))
            self.assertLess(n, 200.0, str(m))

    def test_les_deux_mesures_sont_reciproques(self):
        t = 30.0 / K.JOURS_AN
        k = K.strike_de_moneyness(-0.05, t)
        self.assertAlmostEqual(
            K.cout_en_frictions(k, t) * K.options_pour_une_friction(k, t),
            1.0, places=10)

    def test_la_pente_par_point_a_le_signe_du_skew(self):
        """Pente en moneyness négative, donc pente par point positive."""
        self.assertGreater(K.pente_par_point(30.0 / K.JOURS_AN), 0.0)


class TestLaPosition(unittest.TestCase):
    def test_le_vega_net_est_nul(self):
        """La parité de la partie XXIV : le véga ne voit que `φ(d₁)`, paire."""
        for jours in K.TENORS:
            p = K.risk_reversal_position(jours / K.JOURS_AN)
            self.assertLess(abs(p.vega_net), 0.02, str(jours))

    def test_le_delta_net_vaut_un_demi(self):
        """Ce que la position porte réellement, et ce n'est pas du skew."""
        for jours in K.TENORS:
            p = K.risk_reversal_position(jours / K.JOURS_AN)
            self.assertAlmostEqual(p.delta_net, 0.50, places=6,
                                   msg=str(jours))

    def test_son_seuil_tombe_sous_le_plancher_plausible(self):
        """L'avertissement de la section : elle est directionnelle."""
        from alp1 import seuil as S_
        p = K.risk_reversal_position(30.0 / K.JOURS_AN)
        self.assertLess(p.seuil_derive, S_.PLAUSIBLE_DRIFT_PER_HOUR[0])
        self.assertLess(p.part_du_plancher, 1.0)

    def test_le_delta_net_ne_depend_pas_de_l_echeance(self):
        vals = [K.risk_reversal_position(j / K.JOURS_AN).delta_net
                for j in K.TENORS]
        self.assertLess(max(vals) - min(vals), 1e-6)


class TestLesForces(unittest.TestCase):
    def test_les_trois_forces_sont_la(self):
        self.assertEqual(len(K.forces()), 3)

    def test_leurs_budgets_different_de_deux_ordres(self):
        self.assertGreater(K.rapport_des_budgets(), 100.0)

    def test_la_plus_chere_est_la_prime_de_crash(self):
        """Le renversement : l'argument économique est le moins établissable."""
        self.assertIn("crash", K.force_la_plus_chere().nom.lower())

    def test_le_tri_est_calcule(self):
        self.assertEqual(K.force_la_plus_chere().seances,
                         max(f.seances for f in K.forces()))

    def test_le_sharpe_donne_des_annees_independantes_du_pas(self):
        """L'identité de la partie XVI, rencontrée ici."""
        a = K.seances_pour_sharpe(0.35) / K.SEANCES_AN
        self.assertAlmostEqual(a, (K.Z_95 / 0.35) ** 2, places=8)


class TestLeDecompte(unittest.TestCase):
    def test_aucune_affirmation_ne_donne_un_sens(self):
        self.assertNotIn("la direction",
                         {a.grandeur for a in K.affirmations()})

    def test_le_compte_se_referme(self):
        self.assertEqual(sum(K.compte_par_grandeur().values()),
                         len(K.affirmations()))

    def test_le_cumul_reprend_les_dix_parties_qui_precedent(self):
        f = K.familles()
        self.assertEqual(len(f), len(I.familles()) + 1)
        self.assertEqual(sum(n for _, n in f),
                         sum(n for _, n in I.familles())
                         + len(K.affirmations()))


class TestLesSurfaces(unittest.TestCase):
    SURFACES = ("surface_rapport", "surface_exposant", "surface_regimes",
                "surface_puissance")

    def test_elles_sont_rectangulaires(self):
        for nom in self.SURFACES:
            g = getattr(K, nom)()
            self.assertTrue(g, nom)
            self.assertEqual(len({len(r) for r in g}), 1, nom)

    def test_le_maximum_tombe_au_fond(self):
        """La règle du dépôt : en projection isométrique, (0,0) est loin."""
        for nom in self.SURFACES:
            g = getattr(K, nom)()
            plat = [(v, i, j) for i, r in enumerate(g)
                    for j, v in enumerate(r)]
            _, i, j = max(plat)
            self.assertLessEqual(i, 1, nom)
            self.assertLessEqual(j, 1, nom)


class TestLesTables(unittest.TestCase):
    def setUp(self):
        self.tables = K.all_tables()

    def test_les_neuf_tables_sont_la(self):
        self.assertEqual(len(self.tables), 9)

    def test_chaque_ligne_a_le_bon_nombre_de_colonnes(self):
        for cle, t in self.tables.items():
            for ligne in t.rows:
                self.assertEqual(len(ligne), len(t.headers), cle)

    def test_chaque_table_a_une_note_et_une_legende(self):
        for cle, t in self.tables.items():
            self.assertTrue(t.caption, cle)
            self.assertGreater(len(t.note or ""), 120, cle)

    def test_les_valeurs_sont_des_chaines_francaises(self):
        for cle, v in K.values().items():
            self.assertIsInstance(v, str, cle)
            self.assertNotIn(".", v.replace("&nbsp;", ""), cle)

    def test_le_verdict_de_l_exposant_est_calcule(self):
        """Les deux dernières colonnes se déduisent des trois qui précèdent."""
        t = self.tables["sk_exposant"]
        for ligne in t.rows:
            rr = float(ligne[1].replace(",", ".").replace("−", "-"))
            fixe = float(ligne[2].replace(",", ".").replace("−", "-"))
            self.assertEqual(
                ligne[5], "oui" if rr < -K.SEUIL_APLATISSEMENT else "non",
                str(ligne))
            self.assertEqual(
                ligne[6], "oui" if fixe < -K.SEUIL_APLATISSEMENT else "non",
                str(ligne))

    def test_aucun_nombre_n_est_publie_en_notation_anglaise(self):
        for t in self.tables.values():
            for ligne in t.rows:
                for cel in ligne[1:]:
                    self.assertNotRegex(cel, r"\d\.\d", t.key)


class TestLesPlanches(unittest.TestCase):
    def setUp(self):
        self.rendus = figsk.render_all()

    def test_les_seize_planches_sont_la(self):
        self.assertEqual(len(self.rendus), 16)

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
        for cle in ("skreliefra", "skreliefex", "skreliefre", "skreliefpu"):
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
            figsk.render_all()
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
            figsk.render_all()
        finally:
            Panel.path = og
        self.assertEqual(hits, [])

    def test_le_domaine_est_declare_avant_les_traces(self):
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
            figsk.render_all()
        finally:
            Panel.path, Panel.domain = og_path, og_dom
        self.assertEqual(hits, [])

    def test_le_bandeau_de_speculation_accroche_la_famille(self):
        from alp1 import speculation as sp
        for cle in self.rendus:
            self.assertEqual(sp.module_d_une_figure(cle), "figsk", cle)


if __name__ == "__main__":
    unittest.main()
