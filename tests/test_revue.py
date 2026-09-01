"""Deux documents venus du dehors : les contrôles de la partie XVIII.

La partie ne dispose d'aucune donnée — seulement de deux jeux de nombres
publiés — et c'est ce qui décide de la forme des tests. Il n'y a rien à
comparer à une série ; il y a des identités qui doivent se refermer, des lois
limites qui doivent tenir exactement, et des verdicts qui doivent rester
calculés.

Quatre familles. Les identités de cohérence, qu'on vérifie en inversant les
formules dans les deux sens. Les lois exactes — la corrélation d'un saut
partagé, la puissance de Fisher, la capacité en `ν⁻²` — contrôlées contre
leurs formes limites et, quand elles décident d'un chiffre publié, contre la
simulation qui les rend. Les invariances, qui sont le résultat de la partie.
Et les pièges du dépôt : le maximum de chaque relief au fond, aucune
apostrophe dans un libellé ARIA, aucune marque dans un pied de figure, aucune
graduation hors domaine.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import figrev
from alp1 import revue as R


class TestCoherenceInterne(unittest.TestCase):

    def test_la_volatilite_implicite_se_referme(self):
        for cagr, sharpe in ((0.246, 1.00), (0.442, 2.14), (0.10, 0.5)):
            v = R.vol_implicite(cagr, sharpe)
            self.assertAlmostEqual(cagr / v, sharpe, places=12)

    def test_un_sharpe_nul_demande_une_volatilite_infinie(self):
        self.assertEqual(R.vol_implicite(0.2, 0.0), math.inf)

    def test_l_alpha_de_jensen_s_inverse(self):
        """Le seul contrôle qui fasse sortir un nombre vérifiable dehors."""
        for beta in (0.2, 0.37, 1.0, 1.6):
            m = R.marche_implicite(R.DOC_B["cagr"], beta,
                                   R.DOC_B["alpha_jensen"], R.DOC_B["rf"])
            alpha = (R.DOC_B["cagr"] - R.DOC_B["rf"]
                     - beta * (m - R.DOC_B["rf"]))
            self.assertAlmostEqual(alpha, R.DOC_B["alpha_jensen"], places=12)

    def test_le_marche_implicite_est_plausible(self):
        """Un rendement de marché hors de [0 %, 30 %] serait un signal."""
        m = R.marche_implicite(R.DOC_B["cagr"], R.DOC_B["beta"],
                               R.DOC_B["alpha_jensen"], R.DOC_B["rf"])
        self.assertGreater(m, 0.0)
        self.assertLess(m, 0.30)

    def test_l_effectif_implicite_s_inverse(self):
        """De `n` on retrouve `t`, et c'est la ligne la plus utile de la table.

        Au signe près : l'effectif est une fonction du carré du rapport, donc
        un `t` négatif et son opposé donnent le même échantillon. C'est
        voulu — le sens de la corrélation ne change pas ce qu'il en a coûté
        de la mesurer.
        """
        for rho in (-0.02, 0.05, 0.31):
            for t in (-1.40, 0.8, 3.2):
                n = R.n_implicite(rho, t)
                self.assertAlmostEqual(
                    abs(rho) * math.sqrt(n - 2.0) / math.sqrt(1.0 - rho * rho),
                    abs(t), places=9)

    def test_une_correlation_nulle_ne_borne_aucun_effectif(self):
        self.assertEqual(R.n_implicite(0.0, 1.4), math.inf)

    def test_l_effectif_implicite_tombe_sur_la_periode_annoncee(self):
        """Le résumé publie sa taille d'échantillon sans le vouloir."""
        n = R.n_implicite(R.DOC_B["correlation"], R.DOC_B["t_correlation"])
        annonce = R.DOC_B["annees"] * R.SESSIONS_PAR_AN
        self.assertLess(abs(n - annonce) / annonce, 0.03)

    def test_le_rapport_sortino_est_celui_d_une_loi_symetrique(self):
        """Le Sortino publié n'ajoute rien au Sharpe publié."""
        rapport = R.DOC_B["sortino"] / R.DOC_B["sharpe"]
        self.assertAlmostEqual(rapport, R.RAPPORT_SYMETRIQUE, delta=0.005)

    def test_toutes_les_lignes_recalculees_sont_coherentes(self):
        """Aucun verdict n'est écrit : la colonne se calcule à 3 %."""
        t = R.table_coherence()
        verdicts = [ligne[4] for ligne in t.rows]
        self.assertEqual(verdicts.count("à expliquer"), 0)
        self.assertEqual(verdicts.count("vérifiable dehors"), 1)


class TestBandeDuCalmar(unittest.TestCase):

    def test_la_simulation_rend_le_rendement_qu_on_lui_donne(self):
        """Contrôle de la chaîne : le CAGR médian doit être celui demandé."""
        mdds, cals = R.tirages(0.246, 1.0, 20.0)
        self.assertEqual(len(mdds), R.N_CHEMINS)
        med = R._q(cals, 0.5) * R._q(mdds, 0.5)
        self.assertLess(abs(med - 0.246) / 0.246, 0.25)

    def test_la_bande_encadre_sa_mediane(self):
        for d in (R.DOC_A, R.DOC_B):
            lo, med, hi = R.bande_calmar(d["cagr"], d["sharpe"], d["annees"])
            self.assertLess(lo, med)
            self.assertLess(med, hi)

    def test_le_mdd_annonce_du_document_a_sort_de_la_bande(self):
        """Le fait de la section, et il doit rester vrai."""
        lo, _, hi = R.bande_mdd(R.DOC_A["cagr"], R.DOC_A["sharpe"],
                                R.DOC_A["annees"])
        self.assertGreater(R.DOC_A["mdd"], hi)

    def test_la_bande_est_plus_large_que_l_amelioration_revendiquee(self):
        lo, _, hi = R.bande_calmar(R.DOC_A["cagr"], R.DOC_A["sharpe"],
                                   R.DOC_A["annees"])
        gain = R.DOC_A["calmar_couvert"] - R.DOC_A["calmar"]
        self.assertLess(gain, 0.5 * (hi - lo))

    def test_les_prefixes_rendent_la_meme_chose_qu_une_simulation_separee(self):
        """Le maximum des `T` premières années est une statistique de préfixe.

        C'est l'astuce qui fait tenir le balayage en vingt secondes au lieu de
        dix minutes ; si elle était fausse, tous les chiffres d'horizon le
        seraient. On la contrôle en refaisant à la main le préfixe le plus
        court sur le même flux d'aléa.
        """
        horizons = (5.0, 20.0)
        bandes = R.bandes_par_prefixe(1.0, horizons, n=60, seed=R.SEED + 77)
        sigma = R.vol_implicite(0.246, 1.0)
        sd_j = sigma / math.sqrt(R.SESSIONS_PAR_AN)
        mu_j = math.log(1.246) / R.SESSIONS_PAR_AN
        jours = int(R.SESSIONS_PAR_AN * horizons[0])
        bruit = R._bruit(int(R.SESSIONS_PAR_AN * horizons[-1]), 60,
                         R.SEED + 77)
        cals = []
        for chemin in bruit:
            x = pic = dd = 0.0
            for g in chemin[:jours]:
                x += mu_j + sd_j * g
                if x > pic:
                    pic = x
                elif pic - x > dd:
                    dd = pic - x
            m = 1.0 - math.exp(-dd)
            if m > 1e-9:
                cals.append((math.exp(x / horizons[0]) - 1.0) / m)
        tri = tuple(sorted(cals))
        attendu = (R._q(tri, 0.05), R._q(tri, 0.50), R._q(tri, 0.95))
        for a, b in zip(bandes[0], attendu):
            self.assertAlmostEqual(a, b, places=12)

    def test_le_flux_d_alea_est_partage(self):
        """Règle du dépôt : la graine ne dépend que de l'indice de trajectoire."""
        a = R._bruit(500, 20, R.SEED + 5)
        b = R._bruit(500, 20, R.SEED + 5)
        self.assertIs(a, b)
        long = R._bruit(900, 20, R.SEED + 5)
        self.assertNotEqual(len(long[0]), len(a[0]))

    def test_la_bande_se_resserre_avec_l_horizon(self):
        largeurs = [w for _, w in R.largeur_par_horizon()]
        self.assertEqual(largeurs, sorted(largeurs, reverse=True))

    def test_l_ajustement_repasse_par_les_points_simules(self):
        """L'exposant est ajusté, jamais postulé — et c'est vérifiable."""
        k, p = R.loi_de_bande()
        for t, w in R.largeur_par_horizon():
            self.assertAlmostEqual(k * t ** (-p) / w, 1.0, delta=0.08)

    def test_l_exposant_un_demi_manquerait_les_points(self):
        """La racine attendue est réfutée par la mesure, pas par une opinion."""
        pts = R.largeur_par_horizon()
        k = math.exp(sum(math.log(w) + 0.5 * math.log(t) for t, w in pts)
                     / len(pts))
        racine = max(abs(k * t ** -0.5 / w - 1.0) for t, w in pts)
        ka, pa = R.loi_de_bande()
        ajuste = max(abs(ka * t ** (-pa) / w - 1.0) for t, w in pts)
        self.assertGreater(racine, 0.15)
        self.assertLess(ajuste, 0.5 * racine)
        self.assertGreater(pa, 0.55)

    def test_les_annees_requises_suivent_l_exposant_ajuste(self):
        p = R.loi_de_bande()[1]
        self.assertAlmostEqual(
            R.annees_pour_ecart(0.10) / R.annees_pour_ecart(0.20),
            2.0 ** (1.0 / p), places=6)

    def test_un_ecart_nul_ne_s_etablit_jamais(self):
        self.assertEqual(R.annees_pour_ecart(0.0), math.inf)

    def test_l_amelioration_revendiquee_est_hors_d_une_carriere(self):
        gain = R.DOC_A["calmar_couvert"] - R.DOC_A["calmar"]
        self.assertGreater(R.annees_pour_ecart(gain), 40.0)


class TestDependanceDeQueue(unittest.TestCase):

    def test_la_correlation_du_saut_est_la_formule_fermee(self):
        for f in R.FREQUENCES:
            p = f / R.SESSIONS_PAR_AN
            v = p * R.TAILLE_SAUT ** 2
            self.assertAlmostEqual(R.rho_du_saut(R.TAILLE_SAUT, f),
                                   v / (1.0 + v), places=12)

    def test_un_krach_jamais_partage_ne_correle_rien(self):
        self.assertEqual(R.rho_du_saut(R.TAILLE_SAUT, 0.0), 0.0)

    def test_la_correlation_croit_avec_la_frequence_et_la_taille(self):
        vals = [R.rho_du_saut(R.TAILLE_SAUT, f)
                for f in sorted(R.FREQUENCES)]
        self.assertEqual(vals, sorted(vals))
        vals = [R.rho_du_saut(j, 0.1) for j in (2.0, 4.0, 8.0, 16.0)]
        self.assertEqual(vals, sorted(vals))

    def test_la_puissance_de_fisher_s_inverse(self):
        for rho in (0.01, 0.04, 0.2, 0.6):
            self.assertAlmostEqual(R.rho_detectable(R.n_pour_rho(rho)), rho,
                                   places=9)

    def test_une_correlation_nulle_demande_un_echantillon_infini(self):
        self.assertEqual(R.n_pour_rho(0.0), math.inf)

    def test_la_correlation_detectable_decroit_avec_l_echantillon(self):
        vals = [R.rho_detectable(n) for n in (50.0, 500.0, 5000.0, 50000.0)]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_la_p_valeur_est_coherente_avec_le_seuil_de_puissance(self):
        """À l'effectif juste requis, la p-valeur doit passer sous alpha."""
        for rho in (0.02, 0.05, 0.15):
            n = R.n_pour_rho(rho)
            self.assertLess(R.p_valeur_rho(rho, n), R.ALPHA)

    def test_un_krach_decennal_reste_invisible(self):
        """Le fait de la section : la dépendance existe et le test la rate."""
        rho = R.rho_du_saut(R.TAILLE_SAUT, 0.10)
        n_dispo = R.DOC_B["annees"] * R.SESSIONS_PAR_AN
        self.assertGreater(R.n_pour_rho(rho), n_dispo)
        self.assertGreater(R.p_valeur_rho(rho, n_dispo), R.ALPHA)
        self.assertGreater(rho, R.DOC_B["ci_bas"])
        self.assertLess(rho, 0.05)

    def test_la_correlation_mesuree_suit_la_formule_fermee(self):
        """La simulation contrôle la forme fermée, sans exception."""
        for f in (0.0, 0.10, 0.20):
            _, _, r = R.melange(f)
            self.assertAlmostEqual(r, R.rho_du_saut(R.TAILLE_SAUT, f),
                                   delta=0.012)

    def test_le_saut_est_compense(self):
        """Sinon la dépendance changerait aussi le rendement."""
        base, _, _ = R.melange(0.0)
        for f in (0.05, 0.10, 0.20):
            mdd, _, _ = R.melange(f)
            self.assertLess(abs(mdd - base) / base, 0.25)

    def test_la_pire_seance_se_degrade_bien_plus_que_le_maximum(self):
        """La diversification protège toutes les séances sauf celle qui compte."""
        mdd0, pire0, _ = R.melange(0.0)
        mdd1, pire1, _ = R.melange(0.10)
        gain_mdd = abs(mdd1 - mdd0) / mdd0
        gain_pire = abs(pire1) / abs(pire0) - 1.0
        self.assertGreater(gain_pire, 1.5 * gain_mdd)
        self.assertGreater(abs(pire1) / abs(pire0), 1.5)

    def test_la_limite_de_visibilite_partage_les_modeles(self):
        """Le verdict n'est pas une opinion : la limite se calcule.

        Les modèles au-dessous de la limite ne se distinguent pas de
        l'indépendance ; celui qui est au-dessus s'en distingue. Un test qui
        exigerait l'invisibilité des quatre serait faux, et c'est exactement
        ce que la table publie.
        """
        n_dispo = R.DOC_B["annees"] * R.SESSIONS_PAR_AN
        r_lim = R.rho_detectable(n_dispo)
        f_lim = (R.SESSIONS_PAR_AN * (r_lim / (1.0 - r_lim))
                 / R.TAILLE_SAUT ** 2)
        vus = 0
        for _, f in R.MODELES:
            _, _, r = R.melange(f)
            visible = R.p_valeur_rho(abs(r), n_dispo) <= R.ALPHA
            self.assertEqual(visible, f > f_lim, f)
            vus += visible
        self.assertEqual(vus, 1)
        self.assertGreater(1.0 / f_lim, 5.0)

    def test_les_jambes_se_deduisent_des_chiffres_publies(self):
        """Rien n'est posé à la main : le mélange doit rendre le Sharpe publié."""
        s, sigma = R._jambes()
        norme = math.sqrt(R.POIDS[0] ** 2 + R.POIDS[1] ** 2)
        self.assertAlmostEqual(s / norme, R.DOC_B["sharpe"], places=12)
        self.assertAlmostEqual(sigma * norme,
                               R.vol_implicite(R.DOC_B["cagr"],
                                               R.DOC_B["sharpe"]), places=12)

    def test_le_krach_invisible_s_inverse(self):
        """Sa corrélation induite doit tomber exactement sur le seuil."""
        for f in (0.02, 0.1, 0.5):
            for t in (10.0, 40.0, 160.0):
                j = R.taille_invisible(f, t)
                self.assertAlmostEqual(
                    R.rho_du_saut(j, f),
                    R.rho_detectable(t * R.SESSIONS_PAR_AN), places=9)

    def test_un_krach_jamais_partage_n_est_jamais_visible(self):
        self.assertEqual(R.taille_invisible(0.0, 20.0), math.inf)


class TestPortage(unittest.TestCase):

    def test_le_cout_admissible_rend_le_calmar_vise(self):
        for d in R.REDUCTIONS:
            mdd2 = R.DOC_A["mdd"] - d
            net = R.DOC_A["cagr"] - R.cout_admissible(d)
            self.assertAlmostEqual(net / mdd2, R.DOC_A["calmar_couvert"],
                                   places=12)

    def test_la_reduction_minimale_est_le_zero_du_cout(self):
        self.assertAlmostEqual(R.cout_admissible(R.reduction_minimale()), 0.0,
                               places=12)

    def test_au_dessous_le_recouvrement_doit_ajouter_du_rendement(self):
        d = R.reduction_minimale()
        self.assertLess(R.cout_admissible(d - 0.05), 0.0)
        self.assertGreater(R.cout_admissible(d + 0.05), 0.0)

    def test_la_marge_est_l_ecart_de_calmar_fois_le_maximum(self):
        for d in R.REDUCTIONS:
            self.assertAlmostEqual(
                R.marge_de_cagr(d),
                (R.DOC_A["calmar_couvert"] - R.DOC_A["calmar"])
                * (R.DOC_A["mdd"] - d), places=12)

    def test_la_marge_est_la_meme_grandeur_que_l_erreur_fatale(self):
        self.assertAlmostEqual(R.erreur_fatale(),
                               R.marge_de_cagr(R.REDUCTION_RETENUE),
                               places=12)

    def test_au_facteur_un_le_calmar_est_celui_qui_est_vise(self):
        for b in R.BUDGETS:
            self.assertAlmostEqual(R.calmar_sous_prime(b, 1.0),
                                   R.DOC_A["calmar_couvert"], places=12)

    def test_au_facteur_fatal_le_calmar_retombe_sur_le_calmar_nu(self):
        """La définition du facteur fatal, et elle doit se refermer exactement."""
        for b in R.BUDGETS:
            self.assertAlmostEqual(R.calmar_sous_prime(b, R.facteur_fatal(b)),
                                   R.DOC_A["calmar"], places=9)

    def test_le_facteur_fatal_decroit_avec_le_budget(self):
        """Un gros budget laisse moins de place à l'erreur, pas plus."""
        vals = [R.facteur_fatal(b) for b in R.BUDGETS]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_un_budget_nul_n_a_aucun_facteur_fatal(self):
        self.assertEqual(R.facteur_fatal(0.0), math.inf)

    def test_le_facteur_fatal_vaut_un_plus_la_marge_sur_le_budget(self):
        for b in R.BUDGETS:
            self.assertAlmostEqual(R.facteur_fatal(b),
                                   1.0 + R.erreur_fatale() / b, places=12)

    def test_la_reduction_retenue_est_au_milieu_du_lieu(self):
        """Elle est déclarée, jamais choisie pour un résultat."""
        self.assertGreater(R.REDUCTION_RETENUE, R.reduction_minimale())
        self.assertGreater(R.REDUCTION_RETENUE, R.REDUCTIONS[0])
        self.assertLess(R.REDUCTION_RETENUE, R.REDUCTIONS[-1])


class TestCapacite(unittest.TestCase):

    def test_l_impact_croit_en_racine_de_la_taille(self):
        self.assertAlmostEqual(R.impact_nq(400.0) / R.impact_nq(100.0), 2.0,
                               places=9)

    def test_un_ordre_nul_n_a_aucun_impact(self):
        self.assertEqual(R.impact_nq(0.0), 0.0)

    def test_la_capacite_pure_suit_l_inverse_du_carre(self):
        """La loi exacte de la section : doubler la rotation divise par quatre."""
        for r in R.ROTATIONS[:-1]:
            self.assertAlmostEqual(
                R.capacite_pure(r) / R.capacite_pure(2.0 * r), 4.0, places=6)

    def test_la_capacite_pure_epuise_exactement_le_budget(self):
        for r in R.ROTATIONS:
            q = R.capacite_pure(r)
            cout = (R.SESSIONS_PAR_AN * r * 2.0 * R.impact_nq(q)
                    / R.NIVEAU_NQ)
            self.assertAlmostEqual(cout, R.BUDGET_FRICTION, places=9)

    def test_la_capacite_reelle_epuise_exactement_le_budget(self):
        for r in R.ROTATIONS:
            q = R.capacite(r)
            if q <= 0.0:
                continue
            self.assertAlmostEqual(R.drag(q, r), R.BUDGET_FRICTION, places=9)

    def test_la_friction_fixe_rend_la_capacite_toujours_plus_petite(self):
        for r in R.ROTATIONS:
            self.assertLess(R.capacite(r), R.capacite_pure(r))

    def test_la_rotation_fatale_est_le_zero_de_la_capacite(self):
        rf = R.rotation_fatale()
        self.assertGreater(R.capacite(rf * 0.9), 0.0)
        self.assertEqual(R.capacite(rf * 1.1), 0.0)
        self.assertAlmostEqual(
            R.SESSIONS_PAR_AN * rf * R.FRICTION_FIXE / R.NIVEAU_NQ,
            R.BUDGET_FRICTION, places=12)

    def test_la_friction_fixe_est_la_somme_declaree(self):
        self.assertAlmostEqual(
            R.FRICTION_FIXE,
            R.SPREAD_PTS + R.COMMISSION_USD / R.POINT_NQ, places=12)

    def test_la_capacite_decroit_avec_la_rotation(self):
        vals = [R.capacite(r) for r in R.ROTATIONS]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_la_capacite_croit_avec_le_budget(self):
        vals = [R.capacite(10.0, b) for b in (0.05, 0.10, 0.20, 0.40)]
        self.assertEqual(vals, sorted(vals))


class TestRecuperer(unittest.TestCase):

    def test_les_cinq_lectures_se_calculent_sans_les_donnees(self):
        lec = R.lectures()
        self.assertEqual(len(lec), 5)
        self.assertTrue(all(x.calculable for x in lec))

    def test_aucune_lecture_ne_donne_un_avantage_negociable(self):
        """Le résultat de la partie : une méthode de lecture, jamais un sens."""
        self.assertTrue(all(not x.negociable for x in R.lectures()))

    def test_le_verdict_est_calcule_et_non_ecrit(self):
        for x in R.lectures():
            self.assertEqual(x.transfere, x.calculable, x.nom)

    def test_les_effets_sont_relus_des_sections(self):
        """Aucun nombre de la table de synthèse n'est écrit à la main."""
        par_nom = {x.nom: x for x in R.lectures()}
        _, pire_ind, _ = R.melange(0.0)
        _, pire_dep, _ = R.melange(0.10)
        facteur = abs(pire_dep) / abs(pire_ind)
        self.assertIn(f"{facteur:.2f}".replace(".", ","),
                      par_nom["La dépendance de queue"].effet)
        self.assertIn(f"{R.capacite(10.0):.0f}",
                      par_nom["La capacité par la rotation"].effet)


class TestSurfaces(unittest.TestCase):

    SURFACES = (
        ("bande", R.surface_bande, R.SURF_SHARPE, R.SURF_ANNEES),
        ("invisible", R.surface_invisible, R.SURF_FREQ, R.SURF_ARCHIVE),
        ("portage", R.surface_portage, R.SURF_BUDGET, R.SURF_FACTEUR),
        ("drag", R.surface_drag, R.SURF_TAILLE_NQ, R.SURF_ROTATION),
    )

    def test_les_dimensions_suivent_les_grilles(self):
        for nom, fn, lignes, colonnes in self.SURFACES:
            z = fn()
            self.assertEqual(len(z), len(lignes), nom)
            for ligne in z:
                self.assertEqual(len(ligne), len(colonnes), nom)

    def test_le_maximum_est_au_fond_de_la_projection(self):
        """Le coin (0, 0) est le plus éloigné : le relief doit monter vers lui."""
        for nom, fn, _, _ in self.SURFACES:
            z = fn()
            i, j, _ = max(((i, j, z[i][j])
                           for i in range(len(z)) for j in range(len(z[0]))),
                          key=lambda t: t[2])
            self.assertLessEqual(i, 1, nom)
            self.assertLessEqual(j, 1, nom)

    def test_la_surface_de_portage_traverse_le_calmar_nu(self):
        """La ligne de niveau du Calmar nu doit traverser la boîte."""
        vals = [v for ligne in R.surface_portage() for v in ligne]
        self.assertGreater(max(vals), R.DOC_A["calmar"])
        self.assertLess(min(vals), R.DOC_A["calmar"])

    def test_la_surface_du_cout_est_logarithmique(self):
        """La hauteur est un logarithme : l'infobulle doit le défaire."""
        z = R.surface_drag()
        self.assertAlmostEqual(
            10.0 ** z[0][0],
            100.0 * R.drag(R.SURF_TAILLE_NQ[0], R.SURF_ROTATION[0]), places=9)

    def test_la_surface_du_cout_parcourt_plusieurs_ordres(self):
        vals = [v for ligne in R.surface_drag() for v in ligne]
        self.assertGreater(max(vals) - min(vals), 1.5)


class TestLesTables(unittest.TestCase):

    def setUp(self):
        self.tables = R.all_tables()

    def test_les_neuf_tables_sont_la(self):
        self.assertEqual(len(self.tables), 9)
        for cle in self.tables:
            self.assertTrue(cle.startswith("rev_"), cle)

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
        for cle in R.values():
            self.assertTrue(cle.startswith("v_"), cle)

    def test_les_nombres_publies_ne_sont_recopies_qu_une_fois(self):
        """`DOC_A` et `DOC_B` sont les seules sources des deux résumés."""
        self.assertEqual(len(R.DOC_A), 10)
        self.assertEqual(len(R.DOC_B), 16)


class TestLesPlanches(unittest.TestCase):

    def setUp(self):
        self.rendus = figrev.render_all()

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
        for cle in ("revbande", "revinvisible", "revportage", "revdrag"):
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
            figrev.render_all()
        finally:
            Panel.grid_y, Panel.grid_x = og_y, og_x
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
