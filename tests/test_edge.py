"""Tests de la sixième partie : le témoin, le catalogue, l'opérateur.

Trois modules qui produisent des bornes plutôt que des indicateurs. Les tests
portent donc sur ce qui rend une borne utilisable : qu'elle soit exacte là où
elle admet une forme fermée, qu'elle s'inverse sans dériver, et qu'elle refuse
ce qu'elle doit refuser. Deux tests méritent d'être signalés — celui qui
vérifie que la latence **factorise** la dérive captée plutôt que de la
déformer, et celui qui vérifie que l'information fournie par une pièce du
catalogue et celle qu'exige la géométrie sont calculées par la même route,
`entropy`, en sens inverse l'une de l'autre.
"""

from __future__ import annotations

import math
import unittest

from alp1 import broadcast, discret, litedge, report7
from alp1.entropy import required_bits
from alp1.orderflow import captured_drift
from alp1.report import Table


class TestLatence(unittest.TestCase):
    def test_le_facteur_vaut_un_a_delai_nul(self):
        self.assertAlmostEqual(broadcast.latency_factor(0.0, 3.0), 1.0)

    def test_le_facteur_vaut_un_demi_a_une_demi_vie(self):
        self.assertAlmostEqual(broadcast.latency_factor(7.0, 7.0), 0.5)

    def test_la_latence_factorise_la_derive_captee(self):
        """Le délai multiplie la dérive captée sans déformer son profil.

        C'est l'énoncé central du module, et il se vérifie contre la fonction
        du dépôt qui calcule la dérive captée **sans** latence : le rapport
        des deux doit être exactement `2^(−Δ/h)`, à toute exposition.
        """
        h_s, mu = 90.0, 1.7
        for exposition in (5.0, 30.0, 165.6, 390.0):
            sans = captured_drift(mu, h_s / 60.0, exposition)
            for delai in (0.0, 3.0, 10.0, 30.0):
                avec = broadcast.usable_drift(mu, h_s, exposition, delai)
                self.assertAlmostEqual(
                    avec, sans * broadcast.latency_factor(delai, h_s),
                    places=12,
                    msg=f"exposition {exposition}, délai {delai}")

    def test_la_frontiere_et_le_delai_tolere_sont_reciproques(self):
        for ratio in (1.2, 2.0, 5.0):
            for delai in (3.0, 10.0, 30.0):
                h = broadcast.min_half_life(delai, ratio)
                self.assertAlmostEqual(broadcast.tolerated_delay(h, ratio),
                                       delai, places=9)

    def test_a_derive_double_la_demi_vie_minimale_egale_le_delai(self):
        for delai in (3.0, 10.0, 30.0):
            self.assertAlmostEqual(broadcast.min_half_life(delai, 2.0), delai,
                                   places=12)

    def test_un_emetteur_au_seuil_n_est_pas_recopiable(self):
        self.assertEqual(broadcast.min_half_life(10.0, 1.0), math.inf)
        self.assertEqual(broadcast.tolerated_delay(60.0, 0.9), 0.0)

    def test_la_derive_exigee_de_l_emetteur_croit_avec_le_delai(self):
        exigee = [broadcast.required_emitter_drift(1.0, d, 30.0)
                  for d in (0.0, 10.0, 30.0)]
        self.assertEqual(exigee, sorted(exigee))
        self.assertAlmostEqual(exigee[0], 1.0)


class TestEffacement(unittest.TestCase):
    def test_l_inversion_est_exacte(self):
        for p0 in (0.05, 0.25, 0.5):
            for d in (0.05, 0.2, 0.5):
                pobs = broadcast.observed_hit_rate(p0, d)
                self.assertAlmostEqual(
                    broadcast.deletion_explaining(p0, pobs), d, places=12)

    def test_aucun_effacement_ne_change_rien(self):
        self.assertAlmostEqual(broadcast.observed_hit_rate(0.4, 0.0), 0.4)

    def test_un_taux_sous_la_loi_nulle_n_exige_aucun_effacement(self):
        self.assertEqual(broadcast.deletion_explaining(0.5, 0.4), 0.0)
        self.assertEqual(broadcast.deletions_per_loss(0.5, 0.4), math.inf)

    def test_le_lift_de_la_geometrie_1_20_tient_dans_un_perdant_sur_dix(self):
        """Le chiffre que le document cite, recalculé ici sans le lire."""
        p0 = 1.0 / 21.0
        exige = p0 * (1.0 + 0.110)          # lift relatif c/L du document
        un_sur = broadcast.deletions_per_loss(p0, exige)
        self.assertGreater(un_sur, 8.0)
        self.assertLess(un_sur, 11.0)


class TestFoule(unittest.TestCase):
    def test_le_meilleur_croit_avec_la_taille_de_la_foule(self):
        v = [broadcast.best_of_crowd(k, 200) for k in (2, 10, 100, 1000)]
        self.assertEqual(v, sorted(v))

    def test_le_meilleur_decroit_avec_la_longueur_de_l_echantillon(self):
        v = [broadcast.best_of_crowd(100, n) for n in (50, 200, 2000)]
        self.assertEqual(v, sorted(v, reverse=True))

    def test_le_taux_affiche_par_une_foule_sans_talent_depasse_la_loi_nulle(self):
        self.assertGreater(broadcast.hit_rate_of_crowd(100, 200), 0.5)

    def test_le_seuil_d_echantillon_croit_avec_le_nombre_de_candidats(self):
        v = [broadcast.crowd_threshold_calls(k, 0.05) for k in (1, 10, 200)]
        self.assertEqual(v, sorted(v))

    def test_un_avantage_nul_n_est_pas_decidable(self):
        self.assertEqual(broadcast.calls_to_decide(0.5, 0.5), math.inf)


class TestFiltre(unittest.TestCase):
    def test_la_loi_a_posteriori_somme_a_un(self):
        for side in ("long", "short"):
            p = broadcast.posterior_after_screen(side=side).posterior
            self.assertAlmostEqual(p.talent + p.neutre + p.antitalent, 1.0,
                                   places=12)

    def test_le_filtre_inverse_gagne_sur_les_deux_tableaux(self):
        """Loi a posteriori plus pure **et** rendement plus élevé."""
        lg = broadcast.posterior_after_screen(side="long")
        st = broadcast.posterior_after_screen(side="short")
        self.assertGreater(st.posterior.antitalent, lg.posterior.talent)
        self.assertGreater(st.retained, lg.retained)

    def test_la_purete_croit_avec_la_duree_d_observation(self):
        v = [broadcast.posterior_after_screen(n_months=n).posterior.talent
             for n in (3.0, 12.0, 60.0)]
        self.assertEqual(v, sorted(v))

    def test_un_prior_qui_ne_somme_pas_a_un_est_refuse(self):
        with self.assertRaises(ValueError):
            broadcast.posterior_after_screen(
                prior={"talent": 0.5, "neutre": 0.2, "antitalent": 0.2})


class TestRegistre(unittest.TestCase):
    def registre(self, issues, source="direct"):
        reg = broadcast.Ledger("x")
        for i, r in enumerate(issues):
            reg.add(broadcast.Call(ts=1000.0 + i, pseudo="x", instrument="ES",
                                   side=1 if i % 2 == 0 else -1, outcome=r,
                                   source=source))
        return reg

    def test_le_taux_et_la_moyenne_sont_ceux_des_issues_resolues(self):
        reg = self.registre([1.0, -1.0, 1.0, None])
        self.assertEqual(len(reg.resolved), 3)
        self.assertAlmostEqual(reg.hit_rate, 2.0 / 3.0)
        self.assertAlmostEqual(reg.mean_outcome, 1.0 / 3.0)

    def test_un_horodatage_non_monotone_est_releve(self):
        reg = self.registre([1.0, -1.0])
        reg.calls[1] = broadcast.Call(ts=1.0, pseudo="x", instrument="ES",
                                      side=-1, outcome=-1.0)
        self.assertTrue(any("monotone" in d for d in reg.audit()))

    def test_une_source_retrospective_est_relevee(self):
        reg = self.registre([1.0, -1.0], source="recapitulatif")
        self.assertAlmostEqual(reg.retrospective_share, 1.0)
        self.assertTrue(any("récapitulatif" in d for d in reg.audit()))

    def test_une_source_inconnue_est_refusee(self):
        with self.assertRaises(ValueError):
            broadcast.Call(ts=0.0, pseudo="x", instrument="ES", side=1,
                           source="rumeur")

    def test_un_sens_inconnu_est_refuse(self):
        with self.assertRaises(ValueError):
            broadcast.Call(ts=0.0, pseudo="x", instrument="ES", side=2)

    def test_le_csv_fait_l_aller_retour(self):
        reg = self.registre([1.0, -1.0, None])
        relu = broadcast.from_csv(broadcast.to_csv(reg))["x"]
        self.assertEqual(len(relu.calls), len(reg.calls))
        for a, b in zip(reg.calls, relu.calls):
            self.assertAlmostEqual(a.ts, b.ts, places=3)
            self.assertEqual(a.side, b.side)
            self.assertEqual(a.outcome, b.outcome)

    def test_une_ligne_mal_formee_arrete_la_lecture(self):
        with self.assertRaises(ValueError):
            broadcast.from_csv(broadcast.TAPE_HEADER + "\n1,2,3\n")

    def test_une_en_tete_absente_est_refusee(self):
        with self.assertRaises(ValueError):
            broadcast.from_csv("ts,pseudo\n1,x\n")

    def test_l_enregistrement_horodate_a_la_reception(self):
        horloge = iter([10.0, 20.0, 30.0])
        reg = broadcast.record("x", "ES", ["l montée", "s repli", "q", "l tard"],
                               clock=lambda: next(horloge))
        self.assertEqual([c.ts for c in reg.calls], [10.0, 20.0])
        self.assertEqual([c.side for c in reg.calls], [1, -1])
        self.assertEqual(reg.calls[0].note, "montée")

    def test_l_issue_se_rattache_au_dernier_appel(self):
        reg = broadcast.record("x", "ES", ["l a", "r 1,5"], clock=lambda: 1.0)
        self.assertEqual(len(reg.calls), 1)
        self.assertAlmostEqual(reg.calls[0].outcome, 1.5)


class TestVerdict(unittest.TestCase):
    def test_un_registre_sans_avantage_n_a_rien_a_decider(self):
        reg = broadcast.Ledger("x")
        for i in range(10):
            reg.add(broadcast.Call(ts=float(i), pseudo="x", instrument="ES",
                                   side=1, outcome=1.0 if i % 2 else -1.0))
        v = broadcast.evaluate(reg)
        self.assertEqual(v.calls_in_crowd, math.inf)
        self.assertFalse(v.decidable)
        self.assertIn("rien", v.reading())

    def test_le_seuil_monte_avec_le_nombre_de_diffuseurs_regardes(self):
        reg = broadcast.Ledger("x")
        for i in range(40):
            reg.add(broadcast.Call(ts=float(i), pseudo="x", instrument="ES",
                                   side=1, outcome=1.0 if i % 3 else -1.0))
        seul = broadcast.evaluate(reg, n_broadcasters=1)
        foule = broadcast.evaluate(reg, n_broadcasters=200)
        self.assertGreater(foule.calls_in_crowd, seul.calls_in_crowd)
        self.assertGreater(foule.crowd_hit_rate, seul.crowd_hit_rate)


class TestConsensus(unittest.TestCase):
    def appels(self, sens, ts):
        return [broadcast.Call(ts=t, pseudo=f"p{i}", instrument="ES", side=s)
                for i, (s, t) in enumerate(zip(sens, ts))]

    def test_un_accord_parfait_vaut_un(self):
        a = self.appels([1, 1, 1], [0.0, 1.0, 2.0])
        self.assertAlmostEqual(broadcast.consensus(a, 2.0), 1.0)

    def test_un_desaccord_parfait_vaut_zero(self):
        a = self.appels([1, -1], [0.0, 1.0])
        self.assertAlmostEqual(broadcast.consensus(a, 1.0), 0.0)

    def test_un_diffuseur_ne_compte_qu_une_fois(self):
        a = [broadcast.Call(ts=float(i), pseudo="bavard", instrument="ES",
                            side=1) for i in range(9)]
        a.append(broadcast.Call(ts=9.0, pseudo="autre", instrument="ES",
                                side=-1))
        self.assertAlmostEqual(broadcast.consensus(a, 9.0), 0.0)

    def test_la_fenetre_exclut_ce_qui_est_trop_ancien(self):
        a = self.appels([1, 1], [0.0, 1000.0])
        self.assertAlmostEqual(broadcast.consensus(a, 1000.0, window_s=10.0),
                               1.0)


class TestCatalogue(unittest.TestCase):
    def test_les_cles_sont_uniques(self):
        cles = [c.key for c in litedge.CATALOGUE]
        self.assertEqual(len(cles), len(set(cles)))

    def test_la_datation_par_famille_prend_la_premiere_parution(self):
        for c in litedge.CATALOGUE:
            if not c.family:
                continue
            memes = [x.year for x in litedge.CATALOGUE if x.family == c.family]
            self.assertEqual(c.dating_year(), min(memes))

    def test_la_datation_par_publication_reste_disponible(self):
        bb = litedge.CATALOGUE_BY_KEY["bande_bruit"]
        self.assertEqual(bb.dating_year(dating="publication"), bb.year)
        self.assertGreater(bb.surviving_bps(dating="publication"),
                           bb.surviving_bps())

    def test_une_convention_inconnue_est_refusee(self):
        with self.assertRaises(ValueError):
            litedge.CATALOGUE[0].dating_year(dating="au hasard")

    def test_une_exposition_plus_longue_que_l_horizon_ne_capte_pas_plus(self):
        mim = litedge.CATALOGUE_BY_KEY["mim_us"]
        plafond = mim.surviving_bps()
        for exposition in (mim.horizon_min, 400.0, 10_000.0):
            self.assertLessEqual(mim.captured_bps(exposition), plafond + 1e-12)
        self.assertAlmostEqual(mim.captured_bps(10_000.0), plafond, places=12)

    def test_les_constantes_de_temps_doivent_s_apparier(self):
        """Une géométrie patiente ne gagne que sur un effet plus long qu'elle."""
        mim = litedge.CATALOGUE_BY_KEY["mim_us"]       # 30 minutes
        bb = litedge.CATALOGUE_BY_KEY["bande_bruit"]   # 195 minutes
        gain_court = (mim.captured_for(litedge.GEOM_ALP2)
                      / mim.captured_for(litedge.GEOM_ALP1))
        gain_long = (bb.captured_for(litedge.GEOM_ALP2)
                     / bb.captured_for(litedge.GEOM_ALP1))
        self.assertLess(gain_court, 1.1)
        self.assertGreater(gain_long, 5.0)

    def test_l_information_fournie_et_exigee_suivent_la_meme_route(self):
        """La pièce finance la géométrie si et seulement si son net est positif.

        `bits` remonte la route de `entropy.required_bits`. Le rapport des deux
        doit donc franchir l'unité exactement quand l'espérance nette franchit
        zéro — c'est la seule cohérence qui rend le rapport lisible.
        """
        for g in litedge.GEOMETRIES:
            exige = required_bits(g.reward_risk, g.friction_ratio).bits
            self.assertGreater(exige, 0.0)
            for c in litedge.CATALOGUE:
                net = c.net_for(g)
                ratio = c.bits_ratio(g)
                with self.subTest(effet=c.key, geometrie=g.name):
                    if net > 1e-9:
                        self.assertGreater(ratio, 1.0)
                    elif net < -1e-9:
                        self.assertLess(ratio, 1.0)

    def test_le_ratio_d_information_a_le_signe_de_l_esperance_nette(self):
        for g in litedge.GEOMETRIES:
            for c in litedge.CATALOGUE:
                with self.subTest(effet=c.key, geometrie=g.name):
                    self.assertEqual(c.net_for(g) > 0.0,
                                     c.information_ratio(g) > 0.0)

    def test_la_dispersion_est_deduite_du_couple_publie(self):
        for g in litedge.GEOMETRIES:
            self.assertAlmostEqual(g.sd_r * g.sharpe_trade, g.edge_r, places=12)

    def test_le_mandat_et_le_cout_filtrent_le_catalogue(self):
        compat = litedge.compatible()
        self.assertTrue(compat)
        for c in compat:
            self.assertEqual(c.mandate, litedge.MANDATE_ALP2)
            self.assertLessEqual(c.data_cost, litedge.RETAIL_COST_MAX)

    def test_un_effet_publie_trois_fois_ne_vaut_qu_une_piece(self):
        self.assertAlmostEqual(litedge.effective_pieces(litedge.compatible()),
                               1.0, places=12)

    def test_un_mandat_ou_un_cout_inconnu_est_refuse(self):
        for champ, valeur in (("mandate", "hebdomadaire"), ("data_cost", 9)):
            with self.subTest(champ=champ):
                kw = dict(key="k", name="n", reference="r", year=2020,
                          effect_bps=1.0, horizon_min=10.0, cadence=10.0,
                          mandate="intraseance", data_cost=0, conversion="c")
                kw[champ] = valeur
                with self.assertRaises(ValueError):
                    litedge.Candidate(**kw)


class TestAssemblage(unittest.TestCase):
    def test_le_seuil_d_entree_vaut_l_inverse_de_la_racine(self):
        for n in (100, 1260, 7012):
            self.assertAlmostEqual(litedge.entry_threshold(n),
                                   1.0 / math.sqrt(n), places=12)

    def test_l_ir_combine_croit_en_racine_sans_correlation(self):
        self.assertAlmostEqual(litedge.combined_ir(0.02, 4, 0.0), 0.04,
                               places=12)

    def test_une_correlation_parfaite_annule_le_gain_de_l_empilement(self):
        for k in (2, 5, 20):
            self.assertAlmostEqual(litedge.combined_ir(0.02, k, 1.0), 0.02,
                                   places=12)

    def test_prendre_tout_n_est_pas_un_choix(self):
        self.assertEqual(litedge.selection_threshold(5, 5, 1000), 0.0)
        self.assertGreater(litedge.selection_threshold(5, 2, 1000), 0.0)

    def test_l_ir_brut_croit_avec_le_nombre_de_pieces(self):
        irs = [0.03, 0.02, 0.015, 0.01]
        brut = [a.ir_gross for a in litedge.assembly_scan(irs, 5000)]
        self.assertEqual(brut, sorted(brut))

    def test_une_piece_d_ir_negatif_est_ecartee(self):
        avec = litedge.assembly_scan([0.03, -0.05], 5000)
        self.assertEqual(len(avec), 1)

    def test_le_cout_d_estimation_croit_d_une_unite_par_piece(self):
        scan = litedge.assembly_scan([0.03, 0.02, 0.01], 1000)
        self.assertEqual([a.estimation_cost for a in scan],
                         [1 / 1000, 2 / 1000, 3 / 1000])

    def test_une_piece_sous_le_seuil_n_ameliore_pas_l_ensemble(self):
        n = 5000
        seuil = litedge.entry_threshold(n)
        base = litedge.assembly_scan([0.05], n)[0]
        avec = litedge.assembly_scan([0.05, seuil / 2.0], n)[1]
        self.assertLessEqual(avec.ir_gross ** 2 - avec.estimation_cost,
                             base.ir_gross ** 2 - base.estimation_cost)

    def test_le_compte_des_pieces_qualifiantes_suit_le_seuil(self):
        irs = [0.05, 0.02, 0.005]
        self.assertEqual(litedge.qualifying(irs, 10_000), 2)
        self.assertEqual(litedge.qualifying(irs, 900), 1)
        self.assertEqual(litedge.qualifying(irs, 100), 0)

    def test_l_optimum_existe_et_est_atteint(self):
        irs = [0.05, 0.03, 0.02, 0.01, 0.005]
        meilleur = litedge.optimal_pieces(irs, 20_000)
        for a in litedge.assembly_scan(irs, 20_000):
            self.assertLessEqual(a.ir_net, meilleur.ir_net + 1e-12)


class TestDecote(unittest.TestCase):
    def test_un_taux_nul_ne_reduit_rien(self):
        self.assertAlmostEqual(
            litedge.implied_second_half_sharpe(1.33, 6.0, 0.0), 1.33)

    def test_le_sharpe_implique_decroit_avec_le_taux(self):
        v = [litedge.implied_second_half_sharpe(1.33, 6.0, r)
             for r in (0.0, 0.06, 0.17, 0.29)]
        self.assertEqual(v, sorted(v, reverse=True))

    def test_le_plafond_de_decote_inverse_le_predicat(self):
        for taux in (0.05, 0.17, 0.4):
            observe = litedge.implied_second_half_sharpe(1.33, 6.0, taux)
            self.assertAlmostEqual(litedge.decay_ceiling(1.33, observe, 6.0),
                                   taux, places=6)

    def test_une_seconde_moitie_plus_forte_refute_la_decote(self):
        self.assertEqual(litedge.decay_ceiling(1.0, 1.2, 5.0), 0.0)


class TestOperateur(unittest.TestCase):
    def test_le_critere_maitre_se_decompose(self):
        self.assertAlmostEqual(
            discret.expectation(0.01, 100.0, 0.3, 0.65), 1.0 - 0.65 + 0.3 - 0.0,
            places=12)

    def test_un_talent_sans_covariance_ne_vaut_que_sa_friction(self):
        self.assertLess(discret.talent_value(0.0, 0.65), 0.0)
        self.assertAlmostEqual(discret.talent_value(0.65, 0.65), 0.0)

    def test_le_facteur_de_variance_et_le_gain_sont_reciproques(self):
        for rho in (0.0, 0.5, 0.9):
            self.assertAlmostEqual(
                discret.variance_factor(rho) * discret.variance_reduction(rho),
                2.0, places=12)

    def test_le_gain_diverge_a_correlation_parfaite(self):
        self.assertEqual(discret.variance_reduction(1.0), math.inf)

    def test_une_correlation_hors_bornes_est_refusee(self):
        with self.assertRaises(ValueError):
            discret.variance_factor(1.5)

    def test_seances_requises_et_ecart_detectable_sont_reciproques(self):
        for rho in discret.RHO_BOX:
            n = discret.pairs_for_talent(0.05, 0.431, rho)
            self.assertAlmostEqual(discret.detectable_talent(n, 0.431, rho),
                                   0.05, places=9)

    def test_l_appariement_reduit_l_echantillon(self):
        seul = discret.pairs_for_talent(0.05, 0.431, 0.0)
        apparie = discret.pairs_for_talent(0.05, 0.431, 0.8)
        self.assertAlmostEqual(seul / apparie, 5.0, places=9)

    def test_un_ecart_nul_n_est_pas_detectable(self):
        self.assertEqual(discret.pairs_for_talent(0.0, 1.0, 0.5), math.inf)

    def test_declarer_a_l_avance_est_exponentiellement_moins_cher(self):
        gains = [discret.declaration_gain(float(k)) for k in (1, 2, 4, 8)]
        self.assertEqual(gains, sorted(gains))
        self.assertGreater(gains[-1] / gains[0], 100.0)

    def test_le_plan_publie_ce_qu_il_peut_detecter(self):
        d = discret.plan(0.05, 0.431, 0.7, budget_sessions=1260)
        self.assertGreater(d.detectable, 0.0)
        self.assertAlmostEqual(d.years, d.n_pairs / d.sessions_per_year,
                               places=12)
        self.assertEqual(d.conclusive, d.delta >= d.detectable)

    def test_l_audit_releve_les_bras_desequilibres(self):
        self.assertTrue(any("déséquilibrés" in x
                            for x in discret.audit(100, 100, 120)))
        self.assertTrue(any("versions" in x
                            for x in discret.audit(100, 100, 100, 3)))
        self.assertEqual(discret.audit(100, 100, 100), [])


class TestTables(unittest.TestCase):
    def setUp(self):
        self.tables = report7.all_tables()

    def test_chaque_table_a_des_lignes_de_meme_largeur(self):
        for cle, t in self.tables.items():
            with self.subTest(table=cle):
                self.assertIsInstance(t, Table)
                self.assertTrue(t.rows)
                for r in t.rows:
                    self.assertEqual(len(r), len(t.headers))

    def test_chaque_table_porte_une_lecture(self):
        for cle, t in self.tables.items():
            with self.subTest(table=cle):
                self.assertTrue(t.note.strip(),
                                "une table sans lecture est une table muette")

    def test_les_cles_sont_celles_des_fonctions(self):
        self.assertEqual(len(self.tables), len(report7.TABLES))

    def test_les_valeurs_sont_toutes_des_chaines_francaises(self):
        for cle, v in report7.values().items():
            with self.subTest(valeur=cle):
                self.assertIsInstance(v, str)
                self.assertNotIn(".", v.replace(" ", ""))

    def test_les_valeurs_ne_heurtent_pas_celles_du_document(self):
        from alp1 import workingpaper
        deja = set(workingpaper.values())
        for cle in report7.values():
            with self.subTest(valeur=cle):
                self.assertNotIn(cle, deja - set(report7.values()))

    def test_le_registre_de_demonstration_est_exploitable(self):
        reg = report7._demo_ledger()
        self.assertEqual(len(reg.resolved), 12)
        self.assertEqual(reg.audit(), [])


if __name__ == "__main__":
    unittest.main()
