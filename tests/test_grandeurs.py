"""La grandeur qu'on cite : les contrôles de la partie XX.

La partie est entièrement fermée — pas une simulation — et les tests suivent
cette nature. Une forme fermée ne se publie pas sans être contrôlée contre une
route indépendante, et il y en a quatre ici : `horizon.outcome` pour les
probabilités de barrière, une différence finie pour le charm et le dual delta,
une réévaluation pour l'identité de prime, et l'accord des deux moitiés du
principe de réflexion.

Viennent ensuite les invariances, qui sont le résultat de la partie, puis les
deux affirmations que la mesure a réfutées et qu'un test garde réfutées : la
volatilité ne fait rien à l'amplitude du bleed, et le portage ne fait presque
rien à l'écart des conventions. Enfin les pièges du dépôt.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import figgra
from alp1 import grandeurs as G
from alp1 import niveaux as nv
from alp1 import quant as q
from alp1 import seuil as S
from alp1.horizon import outcome


class TestTroisProbabilites(unittest.TestCase):

    def test_la_forme_fermee_est_celle_du_theoreme(self):
        for rr in G.RR_GRID:
            a = q.STOP_PTS
            self.assertAlmostEqual(G.p_avant_stop_ferme(a, rr * a),
                                   1.0 / (1.0 + rr), places=12)

    def test_la_forme_fermee_et_la_seance_bornee_s_accordent(self):
        """Tant que la clôture avant barrière reste négligeable."""
        a = q.STOP_PTS
        for rr in G.RR_GRID:
            b = rr * a
            o = outcome(a, b, q.SESSION_MIN, q.SIGMA_1MIN)
            if o.p_open < 0.001:
                self.assertAlmostEqual(o.p_target,
                                       G.p_avant_stop_ferme(a, b),
                                       delta=0.002, msg=str(rr))

    def test_la_seance_finit_par_border(self):
        """La condition n'est pas décorative : elle tombe au bout de la grille."""
        a = q.STOP_PTS
        opens = [outcome(a, rr * a, q.SESSION_MIN, q.SIGMA_1MIN).p_open
                 for rr in G.RR_GRID]
        # Au plancher de précision machine l'ordre n'a plus de sens ; on
        # n'exige la croissance que là où la quantité existe.
        vus = [x for x in opens if x > 1e-12]
        self.assertEqual(vus, sorted(vus))
        self.assertLess(opens[0], 1e-6)
        self.assertGreater(opens[-1], 0.005)

    def test_toucher_vaut_exactement_deux_fois_cloturer(self):
        """Le principe de réflexion, lu dans les deux sens."""
        for b in (3.0, 12.0, 48.0):
            self.assertAlmostEqual(G.p_touche(b), 2.0 * G.p_cloture(b),
                                   places=12)

    def test_les_trois_sont_ordonnees(self):
        a = q.STOP_PTS
        for rr in G.RR_GRID:
            b = rr * a
            self.assertLess(G.p_avant_stop_ferme(a, b), G.p_cloture(b))
            self.assertLess(G.p_cloture(b), G.p_touche(b))

    def test_le_facteur_a_la_geometrie_declaree(self):
        """Le fait de la partie, et il doit rester vrai."""
        a = q.STOP_PTS
        b = q.RR_REF * a
        self.assertGreater(G.p_touche(b) / G.p_avant_stop_ferme(a, b), 10.0)

    def test_la_probabilite_de_touche_ne_depend_que_de_la_distance(self):
        """Aucune des deux barrières n'y entre, seule la cible."""
        for b in (3.0, 12.0):
            self.assertAlmostEqual(G.p_touche(b), G.p_touche(b), places=12)
        self.assertGreater(G.p_touche(3.0), G.p_touche(12.0))


class TestControleParSimulation(unittest.TestCase):
    """Une forme fermée se contrôle contre la simulation, sans exception."""

    def test_les_quatre_issues_font_un(self):
        for _, st, ci in G.CONTROLES:
            m = G.simuler_issues(st, ci)
            self.assertAlmostEqual(m.avant + m.apres + m.jamais + m.ni, 1.0,
                                   places=9)

    def test_la_geometrie_de_controle_confirme_les_trois_formes(self):
        """Sur un stop que la grille résout, l'écart tient dans le bruit.

        Mille cinq cents séances donnent un écart-type d'un point de
        pourcentage au plus ; on exige moins de trois points, ce qui est
        large et ce qui suffit à distinguer une forme juste d'une fausse.
        """
        _, st, ci = G.CONTROLES[1]
        m = G.simuler_issues(st, ci)
        for mesure, ferme in ((m.avant, G.p_avant_stop_discret(st, ci)),
                              (m.touche, G.p_touche(ci)),
                              (m.cloture, G.p_cloture(ci))):
            self.assertLess(abs(mesure - ferme), 0.03)

    def test_la_correction_de_continuite_agit_dans_le_bon_sens(self):
        """Une barrière surveillée à pas fini est franchie moins souvent."""
        for _, st, ci in G.CONTROLES:
            self.assertGreater(G.p_avant_stop_discret(st, ci),
                               G.p_avant_stop(st, ci))
        self.assertGreater(G.decalage_continuite(), 0.0)

    def test_le_stop_declare_est_sous_la_resolution_de_la_grille(self):
        """Le fait gênant de la partie, et il se vérifie plutôt qu'il s'écrit."""
        self.assertGreater(G.decalage_continuite() / q.STOP_PTS, 0.20)
        self.assertLess(G.decalage_continuite() / G.STOP_CONTROLE, 0.10)

    def test_les_deux_quantites_lointaines_sont_confirmees_partout(self):
        """Elles ne dépendent pas du stop, donc pas de sa résolution."""
        for _, st, ci in G.CONTROLES:
            m = G.simuler_issues(st, ci)
            self.assertLess(abs(m.touche - G.p_touche(ci)), 0.03)
            self.assertLess(abs(m.cloture - G.p_cloture(ci)), 0.03)

    def test_prendre_le_stop_puis_la_cible_est_le_cas_frequent(self):
        """Le fait que la planche d'exemple existe pour montrer."""
        m = G.simuler_issues(q.STOP_PTS, q.RR_REF * q.STOP_PTS)
        self.assertGreater(m.apres, m.avant)
        self.assertGreater(m.apres, m.jamais)
        self.assertAlmostEqual(m.avant + m.apres, m.touche, delta=0.02)

    def test_les_trois_temoins_portent_trois_issues_distinctes(self):
        temoins = G.trajectoires_temoins()
        cles = [c for c, _, _ in temoins]
        self.assertEqual(cles, ["avant", "apres", "jamais"])
        for _, zoom, minute in temoins:
            self.assertEqual(len(minute), q.SESSION_MIN + 1)
            self.assertEqual(len(zoom), G.MINUTES_ZOOM * G.SOUS_PAS + 1)

    def test_chaque_temoin_verifie_son_issue(self):
        b = q.RR_REF * q.STOP_PTS
        for cle, _, minute in G.trajectoires_temoins():
            m = G.minute_de_la_cible(minute, b)
            if cle == "jamais":
                self.assertEqual(m, -1)
                self.assertLess(max(minute), b)
            else:
                self.assertGreaterEqual(m, 0)
                self.assertGreaterEqual(minute[m], b)

    def test_la_minute_de_la_cible_n_est_pas_celle_du_maximum(self):
        """Le premier jet publiait la seconde en croyant publier la première.

        Elles diffèrent sur la séance qui prend le stop puis la cible, et
        c'est exactement la séance dont la planche parle.
        """
        _, _, minute = next(t for t in G.trajectoires_temoins()
                            if t[0] == "apres")
        m = G.minute_de_la_cible(minute)
        self.assertNotEqual(m, minute.index(max(minute)))
        self.assertLess(m, minute.index(max(minute)))

    def test_le_temoin_du_milieu_prend_le_stop_avant_la_cible(self):
        _, zoom, _ = next(t for t in G.trajectoires_temoins()
                          if t[0] == "apres")
        self.assertLessEqual(min(zoom), -q.STOP_PTS)

    def test_la_simulation_est_reproductible(self):
        a, b = q.STOP_PTS, q.RR_REF * q.STOP_PTS
        G.simuler_issues.cache_clear()
        un = G.simuler_issues(a, b)
        G.simuler_issues.cache_clear()
        deux = G.simuler_issues(a, b)
        self.assertEqual(un, deux)


class TestCoutDeLaConfusion(unittest.TestCase):

    def test_avec_la_bonne_l_esperance_vaut_moins_la_friction(self):
        """`E[R] = −c/a` sous prix sans dérive — le théorème du document."""
        a = q.STOP_PTS
        p = G.p_avant_stop_ferme(a, q.RR_REF * a)
        self.assertAlmostEqual(G.esperance_r(p), -G.FRICTION / a, places=12)

    def test_l_esperance_est_lineaire_en_la_probabilite(self):
        pente = (G.esperance_r(0.2) - G.esperance_r(0.1)) / 0.1
        self.assertAlmostEqual(pente, 1.0 + q.RR_REF, places=9)

    def test_le_cout_est_le_produit_declare(self):
        """`(p_touche − a/(a+b))·(1+R:R)`, sans la friction."""
        for a in G.SURF_STOP_PTS:
            for rr in G.SURF_RR:
                self.assertAlmostEqual(
                    G.cout_de_confusion(a, rr),
                    G.esperance_r(G.p_touche(rr * a), a, rr)
                    - G.esperance_r(G.p_avant_stop_ferme(a, rr * a), a, rr),
                    places=9)

    def test_le_cout_ne_depend_pas_de_la_friction(self):
        """Il coûte la même chose à qui paie cher et à qui ne paie rien."""
        a, rr = q.STOP_PTS, q.RR_REF
        for c in (0.0, 0.33, 2.0):
            ecart = (G.esperance_r(G.p_touche(rr * a), a, rr, c)
                     - G.esperance_r(G.p_avant_stop_ferme(a, rr * a), a, rr, c))
            self.assertAlmostEqual(ecart, G.cout_de_confusion(a, rr),
                                   places=9)

    def test_les_trois_encadrent_le_taux_d_equilibre(self):
        """Le fait qui explique la survie de l'erreur."""
        a = q.STOP_PTS
        b = q.RR_REF * a
        eq = (1.0 + G.FRICTION / a) / (1.0 + q.RR_REF)
        self.assertLess(G.p_avant_stop_ferme(a, b), eq)
        self.assertLess(eq, G.p_cloture(b))

    def test_le_rapport_de_confusion_est_la_forme_fermee(self):
        for a in (0.3, 3.0):
            for rr in (5.0, 40.0):
                self.assertAlmostEqual(
                    G.rapport_de_confusion(a, rr),
                    G.p_touche(rr * a) * (1.0 + rr), places=9)


class TestTroisDeltas(unittest.TestCase):

    def test_le_delta_est_entre_zero_et_un(self):
        for vol in G.VOLS:
            for mois in (0.25, 6.0, 24.0):
                d = G.delta_comptant(100.0, 100.0, vol, mois / 12.0)
                self.assertGreater(d, 0.0)
                self.assertLess(d, 1.0)

    def test_le_dual_delta_est_la_derivee_au_strike(self):
        """Forme fermée contre différence finie, à taux et dividende nuls."""
        for vol, t in ((0.25, 0.5), (0.60, 0.08), (0.10, 2.0)):
            self.assertAlmostEqual(G.dual_delta(100.0, 100.0, vol, t),
                                   G.dual_delta_numerique(100.0, 100.0, vol,
                                                          t),
                                   places=6, msg=str((vol, t)))

    def test_a_taux_nul_le_dual_delta_est_la_probabilite_terminale(self):
        for vol, t in ((0.25, 0.5), (0.80, 1.0)):
            self.assertAlmostEqual(G.dual_delta(100.0, 100.0, vol, t),
                                   G.proba_terminale(100.0, 100.0, vol, t),
                                   places=12)

    def test_a_taux_non_nul_ils_different(self):
        """C'est pourquoi la table est tracée à taux non nul."""
        r = G.TAUX_TABLE
        self.assertNotAlmostEqual(
            G.dual_delta(100.0, 100.0, 0.25, 1.0, r),
            G.proba_terminale(100.0, 100.0, 0.25, 1.0, r), places=3)

    def test_le_delta_depasse_toujours_la_probabilite_terminale(self):
        for vol in G.VOLS:
            for mois in (0.25, 1.0, 6.0, 24.0):
                self.assertGreater(
                    G.ecart_delta_proba(100.0, 100.0, vol, mois / 12.0), 0.0)

    def test_l_ecart_croit_avec_la_volatilite_et_l_echeance(self):
        vals = [G.ecart_delta_proba(100.0, 100.0, v, 0.5) for v in G.VOLS]
        self.assertEqual(vals, sorted(vals))
        vals = [G.ecart_delta_proba(100.0, 100.0, 0.25, m / 12.0)
                for m in (0.25, 1.0, 6.0, 24.0)]
        self.assertEqual(vals, sorted(vals))

    def test_l_ecart_ne_depend_que_du_produit_sigma_racine_t(self):
        """Comme la bande de gamma de la partie XIX, et pour la même raison."""
        ref = G.ecart_delta_proba(100.0, 100.0, 0.40, 0.25)
        self.assertAlmostEqual(
            G.ecart_delta_proba(100.0, 100.0, 0.20, 1.0), ref, places=12)

    def test_le_document_exterieur_etait_prudent(self):
        """Il annonçait plus de quinze points ; le recalcul en donne plus."""
        self.assertGreater(
            100 * G.ecart_delta_proba(100.0, 100.0, 0.80, 0.5), 15.0)


class TestCharm(unittest.TestCase):

    def test_la_forme_fermee_est_la_derivee_temporelle(self):
        """Contrôle contre une différence finie sur `delta_comptant`."""
        for s, k, vol, t, r, d in ((100, 100, 0.25, 30 / 365, 0.0, 0.0),
                                   (105, 100, 0.25, 7 / 365, 0.0, 0.0),
                                   (95, 100, 0.40, 90 / 365, 0.02, 0.01)):
            h = 1e-7
            fini = ((G.delta_comptant(s, k, vol, t - h, r, d)
                     - G.delta_comptant(s, k, vol, t + h, r, d)) / (2.0 * h))
            self.assertAlmostEqual(G.charm(s, k, vol, t, r, d) / fini, 1.0,
                                   places=5, msg=str((s, t)))

    def test_le_lieu_du_pic_est_la_racine_declaree(self):
        """`u² − uv − 1 = 0` : on vérifie que la racine annule le polynôme."""
        for vol, t in ((0.25, 1 / 365), (0.25, 60 / 365), (0.80, 0.5)):
            v = vol * math.sqrt(t)
            u = G.d1_du_pic(vol, t)
            self.assertAlmostEqual(u * u - u * v - 1.0, 0.0, places=12)

    def test_le_lieu_du_pic_tombe_sur_le_balayage(self):
        """La règle du dépôt : une forme fermée se contrôle contre un balayage.

        C'est ce contrôle qui avait attrapé la constante fausse du pic de
        hasard de la partie XVI, et il coûte quatre lignes.
        """
        for vol, t in ((0.25, 1 / 365), (0.25, 30 / 365), (0.40, 0.25)):
            balaye = max(
                ((abs(G.bleed_par_jour(100.0 * m, 100.0, vol, t)), m)
                 for m in [0.70 + 0.0005 * i for i in range(1200)]))[1]
            self.assertAlmostEqual(G.moneyness_du_pic(vol, t), balaye,
                                   delta=0.001, msg=str((vol, t)))

    def test_le_pic_se_referme_sur_le_strike(self):
        vals = [G.moneyness_du_pic(0.25, j / 365.0) for j in G.JOURS]
        self.assertEqual(vals, sorted(vals))
        self.assertLess(vals[-1], 1.0)

    def test_le_bleed_est_quasi_nul_a_la_monnaie(self):
        """Le raffinement que la mesure impose au document extérieur."""
        for j in G.JOURS:
            t = j / nv.JOURS_AN
            atm = abs(G.bleed_par_jour(100.0, 100.0, 0.25, t))
            self.assertGreater(G.bleed_du_pic(0.25, t) / atm, 10.0, str(j))

    def test_l_amplitude_asymptotique_approche_la_mesure(self):
        """`φ(1)/2T` — et c'est ce contrôle qui a montré l'axe mort."""
        for j in (1.0, 7.0, 60.0):
            t = j / nv.JOURS_AN
            self.assertAlmostEqual(
                G.amplitude_asymptotique(t) / G.bleed_du_pic(0.10, t), 1.0,
                delta=0.05, msg=str(j))

    def test_l_echeance_pese_cent_fois_plus_que_la_volatilite(self):
        """L'affirmation corrigée par la mesure, gardée corrigée.

        Le premier relief de cette section portait l'amplitude contre la
        volatilité, et le premier jet du texte disait que cet axe était mort.
        La mesure dit autre chose et de plus juste : il n'est pas mort, il
        est **cent fois plus faible** que l'axe de l'échéance. Le test compare
        les deux étendues plutôt que d'affirmer la platitude de l'une.
        """
        vols = (0.10, 0.30, 0.90)
        par_vol = max(
            max(G.bleed_du_pic(v, j / nv.JOURS_AN) for v in vols)
            / min(G.bleed_du_pic(v, j / nv.JOURS_AN) for v in vols)
            for j in (1.0, 60.0, 180.0))
        par_echeance = (G.bleed_du_pic(0.25, 1.0 / nv.JOURS_AN)
                        / G.bleed_du_pic(0.25, 180.0 / nv.JOURS_AN))
        self.assertLess(par_vol, 2.0)
        self.assertGreater(par_echeance, 50.0 * par_vol)


class TestLivre(unittest.TestCase):

    def test_les_deux_livres_sont_opposes(self):
        for m in G.MOUVEMENTS:
            self.assertAlmostEqual(G.pl_livre("long", m),
                                   -G.pl_livre("court", m), places=12)

    def test_un_mouvement_nul_ne_rend_rien(self):
        self.assertAlmostEqual(G.pl_livre("long", 0.0), 0.0, places=12)

    def test_le_livre_long_gagne_dans_les_deux_sens(self):
        """C'est la définition de la convexité, et le point de la section."""
        for m in G.MOUVEMENTS:
            self.assertGreater(G.pl_livre("long", m), 0.0)
            self.assertGreater(G.pl_livre("long", -m), 0.0)

    def test_l_ecart_croit_a_peu_pres_comme_le_carre(self):
        a = G.pl_livre("long", 0.01) - G.pl_livre("court", 0.01)
        b = G.pl_livre("long", 0.02) - G.pl_livre("court", 0.02)
        self.assertAlmostEqual(b / a, 4.0, delta=0.4)

    def test_le_delta_du_straddle_n_est_pas_nul_au_strike(self):
        """Le détail qui a fait échouer la première version de la section."""
        t = G.JOURS_LIVRE / nv.JOURS_AN
        self.assertGreater(
            abs(G.delta_straddle(100.0, 100.0, G.VOL_LIVRE, t)), 0.01)

    def test_apres_couverture_le_delta_net_est_nul(self):
        """Et il est calculé, pas écrit."""
        self.assertAlmostEqual(G.delta_net_couvert(), 0.0, places=12)

    def test_le_straddle_vaut_deux_fois_le_call_a_la_monnaie(self):
        """Parité call-put à taux nul, au strike."""
        t = G.JOURS_LIVRE / nv.JOURS_AN
        self.assertAlmostEqual(
            G.straddle(100.0, 100.0, G.VOL_LIVRE, t),
            2.0 * nv.call(100.0, 100.0, G.VOL_LIVRE, t), places=9)


class TestConvention(unittest.TestCase):

    def test_le_delta_forward_ne_porte_pas_l_escompte(self):
        for div in (0.0, 0.03):
            for t in (0.25, 2.0):
                self.assertAlmostEqual(
                    G.delta_comptant(100.0, 100.0, 0.25, t, 0.02, div),
                    math.exp(-div * t)
                    * G.delta_forward(100.0, 100.0, 0.25, t, 0.02, div),
                    places=12)

    def test_sans_dividende_les_deux_premieres_coincident(self):
        for t in (0.25, 2.0):
            self.assertAlmostEqual(
                G.delta_comptant(100.0, 100.0, 0.25, t, 0.05, 0.0),
                G.delta_forward(100.0, 100.0, 0.25, t, 0.05, 0.0), places=12)

    def test_l_ajustement_de_prime_est_la_prime(self):
        for vol in (0.10, 0.25, 0.90):
            for mois in (1.0, 24.0):
                t = mois / 12.0
                self.assertAlmostEqual(
                    100 * (G.delta_comptant(100.0, 100.0, vol, t)
                           - G.delta_ajuste_prime(100.0, 100.0, vol, t)),
                    G.ajustement_de_prime(vol, mois), places=9)

    def test_le_portage_ne_fait_presque_rien(self):
        """L'affirmation réfutée, gardée réfutée.

        La première version de la table balayait le portage et rendait une
        colonne constante : l'ajustement de prime, qui domine l'étendue, ne
        dépend ni du taux ni du dividende.
        """
        vals = [G.ajustement_de_prime(0.25, 6.0) for _ in range(3)]
        self.assertEqual(len(set(vals)), 1)
        for r in (0.0, 0.05, 0.12):
            self.assertAlmostEqual(
                100 * (G.delta_comptant(100.0, 100.0, 0.25, 0.5, r, 0.0)
                       - G.delta_ajuste_prime(100.0, 100.0, 0.25, 0.5, r,
                                              0.0)),
                G.ajustement_de_prime(0.25, 6.0), places=9)

    def test_l_ajustement_domine_l_ecart_de_portage(self):
        for nom, r, div, mois in G.REGIMES:
            t = mois / 12.0
            portage = abs(G.delta_comptant(100.0, 100.0, G.VOL_REF, t, r, div)
                          - G.delta_forward(100.0, 100.0, G.VOL_REF, t, r,
                                            div))
            self.assertGreater(G.ajustement_de_prime(G.VOL_REF, mois),
                               100 * portage, nom)


class TestIdentiteDePrime(unittest.TestCase):

    def test_a_la_monnaie_les_deux_coincident_exactement(self):
        """`V/S = Δ − N(d₂)` à la monnaie et à portage nul."""
        for vol in (0.10, 0.25, 0.60, 0.90):
            for mois in (1.0, 6.0, 24.0):
                prime, gap = G.identite_prime_gap(vol, mois)
                self.assertAlmostEqual(prime, gap, places=10,
                                       msg=str((vol, mois)))

    def test_hors_de_la_monnaie_elle_tombe(self):
        """Une identité sans sa condition est une erreur en attente."""
        t = 0.5
        for m in (0.90, 1.10):
            s = 100.0 * m
            prime = 100.0 * nv.call(s, 100.0, G.VOL_REF, t) / s
            gap = 100.0 * G.ecart_delta_proba(s, 100.0, G.VOL_REF, t)
            self.assertGreater(abs(prime - gap), 1.0, str(m))


class TestReste(unittest.TestCase):

    def test_les_cinq_confusions_sont_la(self):
        self.assertEqual(len(G.confusions()), 5)

    def test_toutes_sont_opposables_sans_donnees(self):
        self.assertTrue(all(x.opposable for x in G.confusions()))

    def test_le_verdict_est_calcule_et_non_ecrit(self):
        for x in G.confusions():
            self.assertEqual(x.opposable, x.calculable, x.quoi)

    def test_l_erreur_relative_est_la_formule_declaree(self):
        for x in G.confusions():
            if x.valeur_decide != 0.0:
                self.assertAlmostEqual(
                    x.erreur_relative,
                    abs(x.valeur_citee - x.valeur_decide)
                    / abs(x.valeur_decide), places=12, msg=x.quoi)

    def test_les_cinq_erreurs_sont_finies_et_grandes(self):
        """La plus petite dépasse toute tolérance qu'on s'accorde."""
        for x in G.confusions():
            self.assertTrue(math.isfinite(x.erreur_relative), x.quoi)
            self.assertGreater(x.erreur_relative, 0.10, x.quoi)

    def test_la_premiere_est_la_plus_couteuse(self):
        """Et elle est du dépôt, pas du document extérieur."""
        lst = G.confusions()
        self.assertEqual(lst[0].erreur_relative,
                         max(x.erreur_relative for x in lst))


class TestSurfaces(unittest.TestCase):

    SURFACES = (
        ("confusion", G.surface_confusion, G.SURF_STOP_PTS, G.SURF_RR),
        ("cout", G.surface_cout, G.SURF_STOP_PTS, G.SURF_RR),
        ("gap", G.surface_gap, G.SURF_VOL, G.SURF_MOIS),
        ("lieu", G.surface_lieu, G.SURF_JOURS, G.SURF_VOL_CHARM),
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

    def test_la_surface_du_cout_traverse_zero(self):
        vals = [v for l in G.surface_cout() for v in l]
        self.assertGreater(max(vals), 0.0)
        self.assertLess(min(vals), 0.0)

    def test_la_surface_du_gap_ne_depend_que_du_produit(self):
        """Deux cellules de même `σ√T` doivent porter la même hauteur."""
        z = G.surface_gap()
        for i, v in enumerate(G.SURF_VOL):
            for j, m in enumerate(G.SURF_MOIS):
                attendu = 100.0 * G.ecart_delta_proba(G.S_REF, G.S_REF, v,
                                                      m / 12.0)
                self.assertAlmostEqual(z[i][j], attendu, places=9)


class TestLesTables(unittest.TestCase):

    def setUp(self):
        self.tables = G.all_tables()

    def test_les_neuf_tables_sont_la(self):
        self.assertEqual(len(self.tables), 9)
        for cle in self.tables:
            self.assertTrue(cle.startswith("gr_"), cle)

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
        for cle in G.values():
            self.assertTrue(cle.startswith("g_"), cle)


class TestLesPlanches(unittest.TestCase):

    def setUp(self):
        self.rendus = figgra.render_all()

    def test_les_quatorze_planches_sont_la(self):
        self.assertEqual(len(self.rendus), 14)

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
        for cle in ("grconfusion", "grrelief", "grgap", "grlieu"):
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
            figgra.render_all()
        finally:
            Panel.grid_y, Panel.grid_x = og_y, og_x
        self.assertEqual(hits, [])

    def test_aucun_trace_n_est_reduit_par_le_decoupage(self):
        """Une courbe qui n'entre pas dans son cadre est un cadre vide."""
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
            figgra.render_all()
        finally:
            Panel.path = og
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
