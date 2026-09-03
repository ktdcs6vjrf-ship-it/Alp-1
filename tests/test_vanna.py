"""Les tests de la partie XXIV — là où le delta et la volatilité se rencontrent.

Le premier de ces tests est celui qui manquait : `vanna` a deux lectures, la
sensibilité du delta à la volatilité et celle du véga au comptant, et leur
égalité est la symétrie des dérivées secondes croisées. Elle ne peut donc
échouer que si une implémentation est fausse — et elle l'était.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import figva
from alp1 import grandeurs as G
from alp1 import niveaux as nv
from alp1 import quant as q
from alp1 import rho as R
from alp1 import theta as th
from alp1 import vanna as VA
from alp1 import vega as vg


S, V = VA.S_REF, VA.VOL_REF


class TestLesDeuxRoutes(unittest.TestCase):
    def test_les_deux_derivees_croisees_sont_le_meme_nombre(self):
        for j in (7.0, 30.0, 90.0, 365.0, 730.0):
            t = j / VA.JOURS_AN
            for m in (0.80, 0.90, 1.00, 1.10, 1.25):
                s = S * m
                self.assertAlmostEqual(VA.vanna(s, S, V, t),
                                       VA.vanna_par_delta(s, S, V, t),
                                       places=4, msg=(j, m))
                self.assertAlmostEqual(VA.vanna(s, S, V, t),
                                       VA.vanna_par_vega(s, S, V, t),
                                       places=4, msg=(j, m))

    def test_la_forme_fausse_differait_d_une_racine(self):
        """Le défaut trouvé, formulé comme un test pour qu'il ne revienne pas."""
        for j in (7.0, 30.0, 365.0):
            t = j / VA.JOURS_AN
            faux = (-vg.vega(S * 0.9, S, V, t, VA.TAUX, VA.DIVIDENDE)
                    * G._d(S * 0.9, S, V, t, VA.TAUX, VA.DIVIDENDE)[1]
                    / (S * 0.9 * V))
            vrai = VA.vanna(S * 0.9, S, V, t)
            self.assertAlmostEqual(faux / vrai, math.sqrt(t), places=9)

    def test_le_call_et_le_put_partagent_leur_vanna(self):
        """Par la parité : leur différence ne dépend pas de la volatilité."""
        h = 1e-5
        for j in (30.0, 365.0):
            t = j / VA.JOURS_AN
            for m in (0.9, 1.1):
                s = S * m
                dp = ((G.delta_comptant(s, S, V + h, t, VA.TAUX, VA.DIVIDENDE)
                       - math.exp(-VA.DIVIDENDE * t))
                      - (G.delta_comptant(s, S, V - h, t, VA.TAUX,
                                          VA.DIVIDENDE)
                         - math.exp(-VA.DIVIDENDE * t))) / (2 * h)
                self.assertAlmostEqual(dp, VA.vanna(s, S, V, t), places=4)

    def test_le_vanna_est_nul_a_echeance_nulle(self):
        self.assertEqual(VA.vanna(S, S, V, 0.0), 0.0)


class TestLeZero(unittest.TestCase):
    def test_le_vanna_s_annule_au_lieu_annonce(self):
        for j in (7.0, 90.0, 365.0):
            t = j / VA.JOURS_AN
            m = VA.moneyness_du_zero(t)
            self.assertAlmostEqual(VA.vanna(S * m, S, V, t), 0.0, places=9)

    def test_il_est_positif_au_dessous_et_negatif_au_dessus(self):
        for j in (7.0, 90.0, 365.0):
            t = j / VA.JOURS_AN
            m = VA.moneyness_du_zero(t)
            self.assertGreater(VA.vanna(S * m * 0.98, S, V, t), 0.0)
            self.assertLess(VA.vanna(S * m * 1.02, S, V, t), 0.0)

    def test_le_cote_est_decide_par_le_taux_de_la_partie_XXIII(self):
        """La condition est `r < q + σ²/2`, et ce taux vient de `rho`."""
        rstar = R.taux_du_pic_exact(V, VA.DIVIDENDE)
        for r in (0.0, 0.02, rstar - 0.005):
            self.assertGreater(VA.moneyness_du_zero(1.0, V, r, VA.DIVIDENDE),
                               1.0)
            self.assertTrue(VA.zero_au_dessus(V, r, VA.DIVIDENDE))
        for r in (rstar + 0.005, 0.08):
            self.assertLess(VA.moneyness_du_zero(1.0, V, r, VA.DIVIDENDE),
                            1.0)
            self.assertFalse(VA.zero_au_dessus(V, r, VA.DIVIDENDE))

    def test_au_taux_exact_le_zero_est_a_la_monnaie(self):
        rstar = R.taux_du_pic_exact(V, VA.DIVIDENDE)
        for j in (7.0, 365.0, 1825.0):
            self.assertAlmostEqual(
                VA.moneyness_du_zero(j / VA.JOURS_AN, V, rstar,
                                     VA.DIVIDENDE), 1.0, places=12)


class TestLaDesobeissance(unittest.TestCase):
    def test_la_bande_est_celle_de_la_volga_negative(self):
        """La largeur en logarithme vaut `σ²T`, comme la partie XXII."""
        for j in (7.0, 30.0, 90.0, 365.0, 730.0):
            t = j / VA.JOURS_AN
            lo, hi = VA.bande_de_desobeissance(t)
            self.assertAlmostEqual(math.log(hi / lo), V * V * t, places=12)
            self.assertAlmostEqual(
                math.log(vg.bande_de_courbure(t)[1]
                         / vg.bande_de_courbure(t)[0]), V * V * t, places=12)

    def test_dans_la_bande_les_deux_d_sont_de_signes_opposes(self):
        for j in (30.0, 365.0):
            t = j / VA.JOURS_AN
            lo, hi = VA.bande_de_desobeissance(t)
            m = math.sqrt(lo * hi)
            d1, d2 = G._d(S * m, S, V, t, VA.TAUX, VA.DIVIDENDE)
            self.assertLess(d1 * d2, 0.0)

    def test_hors_de_la_bande_la_regle_du_guide_tient(self):
        """Le vanna ramène le delta vers un demi partout ailleurs."""
        h = 1e-4
        for j in (30.0, 365.0):
            t = j / VA.JOURS_AN
            lo, hi = VA.bande_de_desobeissance(t)
            for m in (lo * 0.90, hi * 1.10):
                d = G.delta_comptant(S * m, S, V, t, VA.TAUX, VA.DIVIDENDE)
                dh = G.delta_comptant(S * m, S, V + h, t, VA.TAUX,
                                      VA.DIVIDENDE)
                self.assertLess(abs(dh - 0.5), abs(d - 0.5) + 1e-12)

    def test_dans_la_bande_elle_ne_tient_pas(self):
        h = 1e-4
        t = 365.0 / VA.JOURS_AN
        lo, hi = VA.bande_de_desobeissance(t)
        m = math.sqrt(lo * hi)
        d = G.delta_comptant(S * m, S, V, t, VA.TAUX, VA.DIVIDENDE)
        dh = G.delta_comptant(S * m, S, V + h, t, VA.TAUX, VA.DIVIDENDE)
        self.assertGreater(abs(dh - 0.5), abs(d - 0.5))


class TestLeRetournement(unittest.TestCase):
    def test_le_plancher_ferme_egale_le_plancher_balaye(self):
        for m in VA.MONEYNESS_ITM:
            for j in (90.0, 365.0):
                t = j / VA.JOURS_AN
                self.assertAlmostEqual(VA.plancher_du_delta(m, t),
                                       VA.plancher_balaye(m, t), places=4)

    def test_aucune_option_dans_la_monnaie_n_atteint_un_demi(self):
        for m in VA.MONEYNESS_ITM:
            for j in (30.0, 365.0, 1095.0):
                self.assertGreater(VA.plancher_du_delta(m, j / VA.JOURS_AN),
                                   0.5)

    def test_le_delta_remonte_apres_le_retournement(self):
        t = 1.0
        for m in (1.05, 1.20):
            sig = VA.vol_du_retournement(m, t)
            bas = G.delta_comptant(S * m, S, sig, t, VA.TAUX, VA.DIVIDENDE)
            for suite in (1.5, 2.0, 3.0):
                self.assertGreater(
                    G.delta_comptant(S * m, S, sig * suite, t, VA.TAUX,
                                     VA.DIVIDENDE), bas)

    def test_le_retournement_est_atteignable_sur_une_option_longue(self):
        self.assertLess(VA.vol_du_retournement(1.05, 1.0), 0.45)

    def test_hors_de_la_monnaie_il_n_y_a_pas_de_retournement(self):
        self.assertFalse(math.isfinite(VA.vol_du_retournement(0.90, 1.0)))


class TestLeDeplacement(unittest.TestCase):
    def test_le_strike_du_vingt_deltas_est_bien_a_vingt_deltas(self):
        for j in (30.0, 365.0):
            t = j / VA.JOURS_AN
            k = VA.strike_du_delta(0.20, t)
            self.assertAlmostEqual(
                G.delta_comptant(S, k, VA.VOL_BASSE, t, VA.TAUX,
                                 VA.DIVIDENDE), 0.20, places=6)

    def test_la_mesure_depasse_le_nombre_annonce(self):
        for j in (7.0, 30.0, 365.0):
            _, exact, _, _ = VA.deplacement(j / VA.JOURS_AN)
            self.assertGreater(exact, VA.DELTA_ANNONCE + 0.05)

    def test_le_premier_ordre_depasse_la_mesure(self):
        for j in (7.0, 30.0, 365.0):
            _, exact, lin, _ = VA.deplacement(j / VA.JOURS_AN)
            self.assertGreater(lin, exact)

    def test_le_choc_qui_rend_trente_deltas_est_bien_plus_petit(self):
        for j in (30.0, 365.0):
            k, _, _, v30 = VA.deplacement(j / VA.JOURS_AN)
            self.assertLess(v30, VA.VOL_HAUTE)
            self.assertAlmostEqual(
                G.delta_comptant(S, k, v30, j / VA.JOURS_AN, VA.TAUX,
                                 VA.DIVIDENDE), VA.DELTA_ANNONCE, places=6)


class TestLePic(unittest.TestCase):
    def test_le_lieu_du_pic_est_celui_du_balaye(self):
        for j in (7.0, 90.0, 365.0, 1825.0):
            t = j / VA.JOURS_AN
            m, v = VA.pic_balaye(t)
            self.assertLess(abs(VA.moneyness_du_pic(t) / m - 1.0), 0.002)
            self.assertAlmostEqual(VA.vanna_du_pic(t), v, places=3)

    def test_le_pic_partage_la_racine_du_charm(self):
        """`d₁² − σ√T·d₁ − 1 = 0` : la même équation dans les deux modules."""
        for j in (7.0, 90.0, 365.0):
            t = j / VA.JOURS_AN
            d1 = G.d1_du_pic(V, t)
            v = V * math.sqrt(t)
            self.assertAlmostEqual(d1 * d1 - v * d1 - 1.0, 0.0, places=12)

    def test_le_pic_se_tient_a_un_delta_presque_constant(self):
        deltas = [VA.delta_du_pic(j / VA.JOURS_AN)
                  for j in (1.0, 30.0, 365.0, 1825.0)]
        self.assertGreater(min(deltas), 0.15)
        self.assertLess(max(deltas), 0.22)

    def test_le_maximum_croit_de_bout_en_bout(self):
        vals = [VA.vanna_du_pic(j / VA.JOURS_AN)
                for j in (1.0, 7.0, 30.0, 90.0, 365.0, 730.0, 1825.0)]
        for a, b in zip(vals, vals[1:]):
            self.assertGreater(b, a)

    def test_ce_que_la_fenetre_laisse_voir_finit_par_decroitre(self):
        """Le résultat de la section : la bosse est celle du cadre."""
        vus = [VA.vanna_max_fenetre(j / VA.JOURS_AN)
               for j in (365.0, 730.0, 1825.0)]
        for a, b in zip(vus, vus[1:]):
            self.assertLess(b, a)

    def test_le_pic_sort_de_la_fenetre_du_guide(self):
        self.assertTrue(VA.dans_la_fenetre(90.0 / VA.JOURS_AN))
        self.assertFalse(VA.dans_la_fenetre(730.0 / VA.JOURS_AN))


class TestLeMauvaisGrec(unittest.TestCase):
    def test_la_correction_au_vega_reproduit_la_reevaluation(self):
        t = VA.JOURS_PEAU / VA.JOURS_AN
        for s in VA.SPOTS:
            self.assertAlmostEqual(VA.delta_par_vega(s, S, t),
                                   VA.delta_reevalue(s, S, t), places=4)

    def test_la_formule_du_guide_ne_capte_presque_rien(self):
        t = VA.JOURS_PEAU / VA.JOURS_AN
        vrai = VA.delta_reevalue(S, S, t)
        bs = G.delta_comptant(S, S, VA.peau(S), t, VA.TAUX, VA.DIVIDENDE)
        pa = VA.delta_par_vanna(S, S, t)
        self.assertLess(abs((pa - bs) / (vrai - bs)), 0.01)

    def test_la_correction_du_gamma_est_celle_qui_porte_le_vanna(self):
        t = VA.JOURS_PEAU / VA.JOURS_AN
        for s in VA.SPOTS:
            self.assertAlmostEqual(VA.gamma_par_vanna(s, S, t),
                                   VA.gamma_reevalue(s, S, t), places=5)

    def test_le_facteur_deux_est_necessaire(self):
        t = VA.JOURS_PEAU / VA.JOURS_AN
        p = VA.pente_de_peau()
        s = 94.0
        v = VA.peau(s)
        avec = abs(VA.gamma_par_vanna(s, S, t) - VA.gamma_reevalue(s, S, t))
        sans = abs(VA.gamma_bs(s, S, v, t) + VA.vanna(s, S, v, t) * p
                   - VA.gamma_reevalue(s, S, t))
        self.assertLess(avec, sans)

    def test_la_pente_de_peau_est_negative(self):
        self.assertLess(VA.pente_de_peau(), 0.0)


class TestLeTemoinEtLAgregation(unittest.TestCase):
    def test_le_taux_de_reussite_ne_depend_pas_de_la_distance(self):
        taux = [nv.taux_de_reussite_ferme(d * q.INDEX_LEVEL,
                                          q.RR_REF * d * q.INDEX_LEVEL)
                for d in VA.DISTANCES]
        for x in taux[1:]:
            self.assertAlmostEqual(x, taux[0], places=12)

    def test_le_profil_agrege_de_vanna_traverse_zero_deux_fois(self):
        """Le résultat qui vient avant tout tirage, et le piège du premier jet."""
        self.assertEqual(len(VA.lignes_de_vex()), 2)

    def test_le_profil_agrege_de_gamma_n_en_traverse_qu_une(self):
        self.assertTrue(math.isfinite(nv.bascule()))

    def test_chaque_ligne_annule_bien_le_profil(self):
        for x in VA.lignes_de_vex():
            self.assertLess(abs(VA.vex(x)), 1.0)

    def test_signe_inconnu_les_lignes_se_multiplient(self):
        hist, lo, med, hi = VA.compte_de_lignes(0.0, 0.0)
        self.assertEqual(sum(hist), VA.N_TIRAGES)
        self.assertGreater(hist[3] / VA.N_TIRAGES, 0.4)
        self.assertGreater(hi - lo, 500.0)

    def test_la_dispersion_de_volatilite_multiplie_les_lignes(self):
        """L'hypothèse écrite d'avance disait la bande ; c'est le compte."""
        bas = VA.compte_de_lignes(0.0, 0.0)
        haut = VA.compte_de_lignes(0.0, VA.DISPERSIONS_VOL[-1])
        self.assertGreater(haut[0][3], bas[0][3])
        largeur_bas = bas[3] - bas[1]
        largeur_haut = haut[3] - haut[1]
        self.assertLess(abs(largeur_haut / largeur_bas - 1.0), 0.20)


class TestLesNotesDePupitre(unittest.TestCase):
    def test_le_vega_net_d_un_risk_reversal_est_identiquement_nul(self):
        for j in (7.0, 30.0, 90.0, 365.0, 730.0):
            for vol in (0.12, 0.25, 0.45):
                for d in (0.10, 0.25, 0.40):
                    _, _, v, _ = VA.risk_reversal(d, j, vol)
                    self.assertAlmostEqual(v, 0.0, places=8, msg=(j, vol, d))

    def test_son_vanna_net_ne_l_est_pas(self):
        _, _, _, a = VA.risk_reversal()
        self.assertGreater(abs(a), 1.0)

    def test_une_aile_de_put_vendue_est_longue_de_vanna(self):
        """Le signe est l'inverse de ce que le guide écrit."""
        t = 90.0 / VA.JOURS_AN
        k = VA.strike_du_delta_put(-0.10, t)
        self.assertLess(VA.vanna(S, k, V, t), 0.0)

    def test_la_couverture_derive_avec_la_volatilite(self):
        for d in VA.DELTAS:
            if d < 0.5:
                self.assertGreater(VA.derive_de_couverture(d, 90.0), 0.0)


class TestLeDecompte(unittest.TestCase):
    def test_aucune_affirmation_ne_touche_a_la_direction(self):
        self.assertEqual(VA.compte_par_grandeur().get("la direction", 0), 0)

    def test_le_compte_se_referme(self):
        self.assertEqual(sum(VA.compte_par_grandeur().values()),
                         len(VA.affirmations()))

    def test_les_six_familles_sont_comptees_dans_leurs_modules(self):
        fam = dict(VA.familles())
        self.assertEqual(fam["Gamma, partie XIX"], len(nv.affirmations()))
        self.assertEqual(fam["Delta, partie XX"], len(G.confusions()))
        self.assertEqual(fam["Thêta, partie XXI"], len(th.affirmations()))
        self.assertEqual(fam["Véga, partie XXII"], len(vg.affirmations()))
        self.assertEqual(fam["Rho, partie XXIII"], len(R.affirmations()))
        self.assertEqual(fam["Vanna, partie XXIV"], len(VA.affirmations()))

    def test_chaque_affirmation_porte_sa_mesure(self):
        for a in VA.affirmations():
            self.assertGreater(len(a.enonce), 20)
            self.assertGreater(len(a.mesure), 20)
            self.assertIn(a.grandeur,
                          ("l'horloge", "le risque", "rien", "la direction"))


class TestLesSurfaces(unittest.TestCase):
    def test_les_quatre_reliefs_ont_leur_maximum_au_fond(self):
        for nom in ("surface_vanna", "surface_desobeissance", "surface_peau",
                    "surface_retournement"):
            z = getattr(VA, nom)()
            haut = max(max(l) for l in z)
            self.assertAlmostEqual(z[0][0], haut, places=9, msg=nom)

    def test_les_reliefs_sont_carres_et_pleins(self):
        for nom in ("surface_vanna", "surface_desobeissance", "surface_peau",
                    "surface_retournement"):
            z = getattr(VA, nom)()
            self.assertEqual(len(z), 6, nom)
            for l in z:
                self.assertEqual(len(l), 6, nom)
                for v in l:
                    self.assertTrue(math.isfinite(v), nom)


class TestLesTables(unittest.TestCase):
    def setUp(self):
        self.tables = VA.all_tables()

    def test_les_douze_tables_sont_la(self):
        self.assertEqual(len(self.tables), 12)

    def test_chaque_table_a_ses_colonnes(self):
        for cle, t in self.tables.items():
            for ligne in t.rows:
                self.assertEqual(len(ligne), len(t.headers), cle)

    def test_chaque_table_a_une_note_et_une_legende(self):
        for cle, t in self.tables.items():
            self.assertTrue(t.caption, cle)
            self.assertGreater(len(t.note or ""), 120, cle)

    def test_les_valeurs_sont_des_chaines_francaises(self):
        for cle, v in VA.values().items():
            self.assertIsInstance(v, str, cle)
            self.assertNotIn(".", v.replace("&nbsp;", ""), cle)


class TestLesPlanches(unittest.TestCase):
    def setUp(self):
        self.rendus = figva.render_all()

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
        for cle in ("vareliefv", "vareliefb", "vareliefp", "vareliefr"):
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
            figva.render_all()
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
            figva.render_all()
        finally:
            Panel.path = og
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
