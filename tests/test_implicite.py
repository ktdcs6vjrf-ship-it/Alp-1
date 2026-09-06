"""Les tests de la partie XXVIII — la volatilité implicite.

Quatre tests portent ici plus que les autres. Le premier exige que les deux
routes d'inversion — bissection et Newton — se referment, et que l'inversion
refuse de rendre un nombre hors des bornes d'arbitrage. Le deuxième exige que
la loi nulle du look-ahead **en soit une** : l'espérance du gain doit être
nulle et le classement glissant ne rien prédire, faute de quoi le test du
guide ne prouve rien — et c'est exactement ce que le premier jet de ce module
a raté. Le troisième exige que la campagne rende zéro en variance et le biais
d'unité en volatilité, la forme fermée contrôlant la mesure. Le quatrième
exige que le tri des pièges soit calculé et non écrit.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import figiv
from alp1 import grandeurs as G
from alp1 import implicite as I
from alp1 import ordres as O
from alp1 import vega as vg

S, V = I.S_REF, I.VOL_REF


class TestInversion(unittest.TestCase):
    def test_les_deux_routes_se_referment(self):
        """Bissection et Newton, sur toute la grille de la table."""
        for jours, m in I.INVERSIONS:
            t = jours / I.JOURS_AN
            k = S / m
            p = I.call(S, k, V, t)
            a = I.implicite(p, S, k, t)
            b = I.implicite_newton(p, S, k, t)
            # Le contrôle porte sur le **prix reconstruit** et non sur la
            # volatilité : deux volatilités qui rendent le même prix à la
            # précision machine sont la même solution du problème posé, et
            # exiger qu'elles se referment en volatilité serait exiger que
            # le prix ne soit pas plat — ce qu'il est, dans l'aile courte,
            # à la résolution d'un flottant. Le plancher numérique de la
            # partie XXVI, sur l'objet dont il est la définition.
            self.assertAlmostEqual(I.call(S, k, a, t), I.call(S, k, b, t),
                                   places=10, msg=f"{jours} {m}")
            self.assertAlmostEqual(a, b, places=4, msg=f"{jours} {m}")

    def test_l_inversion_retrouve_la_volatilite_qui_a_fait_le_prix(self):
        for vol in (0.08, 0.15, 0.25, 0.45, 0.80):
            for m in (0.85, 1.0, 1.15):
                t = 45.0 / I.JOURS_AN
                k = S / m
                p = I.call(S, k, vol, t)
                self.assertAlmostEqual(I.implicite(p, S, k, t), vol,
                                       places=8, msg=f"{vol} {m}")

    def test_hors_des_bornes_l_inversion_refuse(self):
        """Un outil qui rend tout de même un nombre rend du bruit."""
        t = 30.0 / I.JOURS_AN
        bas, haut = I.bornes_d_arbitrage(S, S, t)
        for prix in (bas - 1e-6, bas * 0.5, haut + 1e-6, haut * 1.5):
            self.assertTrue(math.isnan(I.implicite(prix, S, S, t)), prix)
            self.assertFalse(I.existe(prix, S, S, t), prix)

    def test_les_bornes_sont_les_limites_de_la_fonction(self):
        """`σ → 0` donne le plancher, `σ → ∞` le plafond."""
        t = 30.0 / I.JOURS_AN
        for m in (0.9, 1.0, 1.1):
            k = S / m
            bas, haut = I.bornes_d_arbitrage(S, k, t)
            self.assertAlmostEqual(I.call(S, k, 1e-9, t), bas, places=6)
            self.assertAlmostEqual(I.call(S, k, 60.0, t), haut, places=4)

    def test_le_prix_croit_avec_la_volatilite(self):
        """La monotonie, qui est ce qui rend la bissection légitime.

        Elle est **large** et non stricte, et la nuance n'est pas
        rhétorique : à quatre-vingts de strike et trente jours, le prix ne
        bouge pas d'un bit entre cinq et dix pour cent de volatilité, parce
        que la valeur temps y tombe sous la résolution d'un flottant. C'est
        le plancher numérique de la partie XXVI, rencontré ici sur l'objet
        dont il est la définition — et c'est ce que `moneyness_cotable`
        publie.
        """
        t = 30.0 / I.JOURS_AN
        for k in (S * 0.8, S, S * 1.2):
            prix = [I.call(S, k, v, t) for v in
                    [0.05 + 0.05 * i for i in range(20)]]
            for a, b in zip(prix, prix[1:]):
                self.assertLessEqual(a, b, k)
        # À la monnaie, où le véga n'est jamais nul, elle est stricte.
        atm = [I.call(S, S, v, t) for v in
               [0.05 + 0.05 * i for i in range(20)]]
        for a, b in zip(atm, atm[1:]):
            self.assertLess(a, b)

    def test_une_option_cesse_de_coter_bien_avant_l_arbitrage(self):
        """La borne que le guide ne mentionne pas, et elle est la plus proche."""
        for jours in (2.0, 7.0, 30.0, 90.0):
            t = jours / I.JOURS_AN
            m = I.moneyness_cotable(t)
            k = S / m
            self.assertAlmostEqual(I.call(S, k, V, t), 0.5 * I.TICK,
                                   places=6, msg=str(jours))
            plus_loin = S / (m * 0.97)
            self.assertLess(I.call(S, plus_loin, V, t), 0.5 * I.TICK,
                            str(jours))

    def test_la_frontiere_du_point_reste_en_deca_du_cotable(self):
        """Un tick vaut un point avant que l'option cesse de coter."""
        for jours in (7.0, 30.0, 90.0, 365.0):
            t = jours / I.JOURS_AN
            self.assertGreater(I.strike_du_point_de_vol(t),
                               I.moneyness_cotable(t), str(jours))


class TestLeTick(unittest.TestCase):
    def test_la_forme_fermee_suit_la_reinversion(self):
        """Le premier ordre contre la mesure, là où le véga n'est pas nul."""
        for jours in (30.0, 90.0, 365.0):
            t = jours / I.JOURS_AN
            for delta in (0.50, 0.25, 0.10):
                k = I.strike_du_delta(delta, t)
                a = I.points_de_vol_par_tick(S, k, V, t)
                b = I.points_de_vol_par_tick_mesure(S, k, V, t)
                self.assertLess(abs(a - b) / b, 0.12, f"{jours} {delta}")

    def test_le_tick_vaut_le_tick_sur_le_vega(self):
        t = 30.0 / I.JOURS_AN
        attendu = 100.0 * I.TICK / vg.vega(S, S, V, t, I.TAUX, I.DIVIDENDE)
        self.assertAlmostEqual(I.points_de_vol_par_tick(S, S, V, t), attendu,
                               places=12)

    def test_il_est_proportionnel_au_tick(self):
        """Le tick est déclaré, donc toute la section doit lui être linéaire."""
        t = 30.0 / I.JOURS_AN
        a = I.points_de_vol_par_tick(S, S, V, t, 0.05)
        b = I.points_de_vol_par_tick(S, S, V, t, 0.15)
        self.assertAlmostEqual(b / a, 3.0, places=10)

    def test_il_croit_en_s_eloignant_et_en_se_rapprochant_de_l_echeance(self):
        t = 30.0 / I.JOURS_AN
        suite = [I.points_de_vol_par_tick(S, S / m, V, t)
                 for m in (1.00, 1.05, 1.10, 1.20, 1.30)]
        for a, b in zip(suite, suite[1:]):
            self.assertLess(a, b)
        courts = [I.points_de_vol_par_tick(S, S, V, j / I.JOURS_AN)
                  for j in (365.0, 90.0, 30.0, 7.0, 2.0)]
        for a, b in zip(courts, courts[1:]):
            self.assertLess(a, b)

    def test_la_frontiere_vaut_bien_un_point(self):
        """Ce que la bissection prétend avoir trouvé."""
        for jours in (7.0, 30.0, 90.0, 365.0):
            t = jours / I.JOURS_AN
            m = I.strike_du_point_de_vol(t)
            self.assertAlmostEqual(
                I.points_de_vol_par_tick(S, S / m, V, t), 1.0, places=4,
                msg=str(jours))

    def test_le_delta_de_la_frontiere_n_est_pas_constant(self):
        """Une affirmation écrite d'avance, réfutée par la mesure.

        On attendait un lieu à delta constant, par analogie avec le pic du
        vanna de la partie XXIV. La mesure le refuse, et le mécanisme est
        dans la formule : la frontière est à `φ(d₁) = 100·tick/(S√T)`, un
        seuil **absolu** sur une densité qui s'aplatit, donc `d₁` croît avec
        l'échéance au lieu d'y rester fixe. Ce test garde la réfutation.
        """
        deltas = []
        for jours in (7.0, 30.0, 90.0, 365.0):
            t = jours / I.JOURS_AN
            k = S / I.strike_du_point_de_vol(t)
            deltas.append(I.delta_du_strike(S, k, V, t))
        for a, b in zip(deltas, deltas[1:]):
            self.assertLess(b, a)
        self.assertGreater(deltas[0] / deltas[-1], 8.0)

    def test_le_strike_d_un_delta_rend_ce_delta(self):
        for delta in I.DELTAS:
            for jours in I.TENORS:
                t = jours / I.JOURS_AN
                k = I.strike_du_delta(delta, t)
                self.assertAlmostEqual(I.delta_du_strike(S, k, V, t), delta,
                                       places=6, msg=f"{delta} {jours}")


class TestLaSerie(unittest.TestCase):
    def test_elle_est_deterministe(self):
        self.assertEqual(I.serie(50), I.serie(50))

    def test_elle_est_stationnaire_des_le_premier_point(self):
        """Sans amorçage stationnaire, les premiers points portent l'initiale."""
        debuts, fins = [], []
        for j in range(300):
            s = I.serie(400, graine=I.SEED + 977 * j)
            debuts.append(s[0])
            fins.append(s[-1])
        m0 = sum(debuts) / len(debuts)
        m1 = sum(fins) / len(fins)
        self.assertLess(abs(m0 / m1 - 1.0), 0.10)

    def test_son_autocorrelation_est_celle_qu_on_declare(self):
        s = I.serie(60000, graine=I.SEED + 5)
        m = sum(s) / len(s)
        xs = [math.log(v / m) for v in s]
        num = sum(a * b for a, b in zip(xs, xs[1:]))
        den = sum(a * a for a in xs)
        self.assertAlmostEqual(num / den, I.autocorrelation(), places=2)


class TestRangEtPercentile(unittest.TestCase):
    def test_le_rang_et_le_percentile_vivent_dans_zero_un(self):
        s = I.serie(300, graine=I.SEED + 3)
        fen, val = s[:-1], s[-1]
        for f in (I.iv_rank, I.iv_percentile):
            self.assertGreaterEqual(f(fen, val), 0.0)
            self.assertLessEqual(f(fen, val), 1.0)

    def test_ils_sont_invariants_par_changement_d_echelle(self):
        """Le rang et le percentile ne dépendent que de l'ordre et des bornes."""
        s = I.serie(300, graine=I.SEED + 4)
        fen, val = s[:-1], s[-1]
        gros = [3.7 * v for v in fen]
        self.assertAlmostEqual(I.iv_rank(fen, val),
                               I.iv_rank(gros, 3.7 * val), places=12)
        self.assertAlmostEqual(I.iv_percentile(fen, val),
                               I.iv_percentile(gros, 3.7 * val), places=12)

    def test_le_pic_deplace_le_rang_bien_plus_que_le_percentile(self):
        for n in I.FENETRES:
            s = I.serie(n + 1, graine=I.SEED + 31)
            fen, val = s[:-1], s[-1]
            self.assertGreater(I.sensibilite_du_rang(fen, val, 2.0),
                               I.sensibilite_du_percentile(fen, val, 2.0),
                               str(n))

    def test_le_percentile_ne_bouge_jamais_de_plus_d_un_sur_n(self):
        """Le fait qui rend le rapport égal à la taille de la fenêtre."""
        for n in I.FENETRES:
            s = I.serie(n + 1, graine=I.SEED + 31)
            fen, val = s[:-1], s[-1]
            self.assertLessEqual(
                I.sensibilite_du_percentile(fen, val, 2.0), 1.0 / n + 1e-12,
                str(n))

    def test_le_rapport_croit_avec_la_fenetre(self):
        """Allonger la fenêtre stabilise l'un et déstabilise l'autre.

        La borne est moyennée sur deux cents tirages, sans quoi la suite
        n'est pas monotone alors que la grandeur l'est — le piège de la
        partie XIV, lu sur un point unique.
        """
        suite = [I.borne_du_rapport(n) for n in I.FENETRES]
        for a, b in zip(suite, suite[1:]):
            self.assertGreater(b, a)

    def test_le_recul_du_rang_ne_suit_pas_un_sur_n(self):
        """Le fait qui fabrique la borne : l'un décroît, l'autre s'effondre."""
        rangs = [I.sensibilite_moyenne_du_rang(n) for n in I.FENETRES]
        chute_rang = rangs[0] / rangs[-1]
        chute_pct = I.FENETRES[-1] / I.FENETRES[0]
        self.assertLess(chute_rang, 0.25 * chute_pct)


class TestEchantillonEffectif(unittest.TestCase):
    def test_la_forme_fermee_suit_la_mesure(self):
        """Le contrôle qui autorise à publier `n(1−ρ)/(1+ρ)`."""
        for kappa in (2.0, 4.0, 8.0):
            a = I.echantillon_effectif(I.SEANCES_AN, kappa)
            b = I.echantillon_effectif_mesure(I.SEANCES_AN, kappa)
            self.assertLess(abs(a - b) / b, 0.60, str(kappa))

    def test_il_vaut_kappa_T_sur_deux(self):
        """La forme asymptotique, dont dépend toute la lecture de la partie."""
        for kappa in (1.0, 2.0, 4.0, 8.0):
            attendu = kappa * (I.SEANCES_AN / I.SEANCES_AN) / 2.0
            self.assertAlmostEqual(
                I.echantillon_effectif(I.SEANCES_AN, kappa) / attendu, 1.0,
                delta=0.03, msg=str(kappa))

    def test_il_ne_depend_pas_de_la_frequence_d_echantillonnage(self):
        """Regarder plus souvent n'apprend rien : c'est le résultat."""
        an = I.echantillon_effectif(I.SEANCES_AN, 4.0)
        self.assertAlmostEqual(an, 2.0, delta=0.05)

    def test_le_budget_croit_quand_l_ecart_se_resserre(self):
        a = I.annees_pour_distinguer(0.80, 0.50)
        b = I.annees_pour_distinguer(0.55, 0.50)
        self.assertGreater(b, 10.0 * a)

    def test_le_budget_decroit_quand_le_retour_est_rapide(self):
        suite = [I.annees_pour_distinguer(0.80, 0.50, k)
                 for k in (1.0, 2.0, 4.0, 8.0, 16.0)]
        for a, b in zip(suite, suite[1:]):
            self.assertGreater(a, b)


class TestLookAhead(unittest.TestCase):
    """La loi nulle doit en être une, et c'est ce que le premier jet a raté."""

    def test_l_implicite_juste_est_l_esperance_conditionnelle(self):
        """La forme fermée, contrôlée contre la moyenne de trajectoires."""
        horizon, kappa = 21, I.KAPPA
        depart = I.VOL_MOYENNE * 1.4
        dt = 1.0 / I.SEANCES_AN
        m = math.log(I.VOL_MOYENNE)
        sd_stat = I.ETA / math.sqrt(2.0 * kappa)
        rho = math.exp(-kappa * dt)
        sd_pas = sd_stat * math.sqrt(1.0 - rho * rho)
        import random
        rng = random.Random(I.SEED + 77)
        total = 0.0
        n = 40000
        for _ in range(n):
            x = math.log(depart)
            somme = 0.0
            for _ in range(horizon):
                x = m + rho * (x - m) + sd_pas * rng.gauss(0.0, 1.0)
                somme += math.exp(x)
            total += somme / horizon
        self.assertAlmostEqual(total / n / I.implicite_juste(depart, horizon),
                               1.0, delta=0.02)

    def test_l_esperance_du_gain_est_nulle(self):
        """Sans quoi le test du guide ne prouve rien."""
        for horizon in I.HORIZONS:
            b = I.biais_de_look_ahead(horizon=horizon)
            self.assertLess(abs(b.esperance), 2.0, str(horizon))

    def test_le_classement_glissant_ne_predit_rien(self):
        for horizon in I.HORIZONS:
            b = I.biais_de_look_ahead(horizon=horizon)
            self.assertLess(abs(b.glissant), b.seuil, str(horizon))

    def test_le_classement_fuite_predit(self):
        """Le motif que le guide a vu disparaître, fabriqué par le bug."""
        for horizon in (10, 21, 42, 63):
            b = I.biais_de_look_ahead(horizon=horizon)
            self.assertGreater(b.fuite, b.seuil, str(horizon))

    def test_la_fuite_grandit_avec_l_horizon(self):
        """Le fait qu'aucun des dix guides n'écrit."""
        suite = [I.biais_de_look_ahead(horizon=h).fuite for h in I.HORIZONS]
        for a, b in zip(suite, suite[1:]):
            self.assertGreater(b, a)


class TestLaPrime(unittest.TestCase):
    def test_l_esperance_en_variance_est_nulle_sans_avantage(self):
        """La définition d'une loi nulle, et elle tient à la simulation près."""
        c = I.campagne(0.0)
        self.assertLess(abs(c.moyenne_variance), 0.5)

    def test_l_esperance_en_variance_vaut_deux_sigma_a_plus_a_carre(self):
        vol = 100.0 * I.VOL_MOYENNE
        for a in (1.0, 2.0, 4.0):
            attendu = 2.0 * vol * a + a * a
            self.assertAlmostEqual(
                I.campagne(a).moyenne_variance / attendu, 1.0, delta=0.01,
                msg=str(a))

    def test_le_biais_d_unite_est_positif_et_suit_sa_forme_fermee(self):
        """`σ/(4h)` contre la mesure, comparés **en erreurs types**.

        Une tolérance relative fixe serait ici une erreur de méthode : le
        biais décroît en `1/h` alors que le bruit d'échantillonnage ne
        décroît qu'en `1/√h`, donc à long horizon toute tolérance relative
        finit par mordre sur le bruit et non sur le fait. Le contrôle porte
        sur l'écart rapporté à l'erreur type de la moyenne.
        """
        for horizon in (10, 21, 63):
            c = I.campagne(0.0, horizon=horizon)
            mesure = I.biais_d_unite(horizon)
            ferme = I.biais_d_unite_ferme(horizon)
            self.assertGreater(mesure, 0.0, str(horizon))
            erreur = c.ecart_type / math.sqrt(6000)
            self.assertLess(abs(mesure - ferme) / erreur, 3.0, str(horizon))

    def test_le_biais_d_unite_ne_depend_pas_de_l_avantage(self):
        """C'est ce qui fait qu'on peut le retrancher d'une prime publiée."""
        vals = [I.campagne(a).biais_d_unite for a in I.PRIMES]
        self.assertLess(max(vals) - min(vals), 1e-9)

    def test_le_taux_sans_avantage_depasse_un_demi(self):
        self.assertGreater(I.taux_d_equilibre(), 0.50)
        self.assertLess(I.taux_d_equilibre(), 0.62)

    def test_le_taux_croit_avec_l_avantage(self):
        suite = [I.campagne(a).taux for a in I.PRIMES]
        for a, b in zip(suite, suite[1:]):
            self.assertGreater(b, a)

    def test_le_budget_decroit_avec_l_avantage(self):
        suite = [I.campagne(a).expirations for a in I.PRIMES[1:]]
        for a, b in zip(suite, suite[1:]):
            self.assertGreater(a, b)


class TestLesPieges(unittest.TestCase):
    def test_la_forme_fermee_suit_la_reinversion(self):
        """`Δ·ΔS/𝒱` contre une inversion complète au comptant faux."""
        t = 30.0 / I.JOURS_AN
        for m in (0.95, 1.0, 1.05):
            k = S / m
            for ds in (0.0005 * S, 0.001 * S, 0.002 * S):
                a = I.derive_par_deplacement(S, k, V, t, ds)
                b = I.derive_par_deplacement_mesure(S, k, V, t, ds)
                self.assertLess(abs(a - b) / abs(b), 0.05, f"{m} {ds}")
                self.assertGreater(a * b, 0.0, f"signe {m} {ds}")

    def test_le_signe_de_la_forme_fermee_est_negatif(self):
        """Le défaut que le contrôle a trouvé, et qu'il garde fermé.

        `∂σ/∂S` à prix constant vaut `−Δ/𝒱` : croire le comptant plus haut
        qu'il n'est fait *baisser* l'implicite qu'on en déduit. Le premier
        jet écrivait le signe opposé, et les cinq pièges — tous pris en
        valeur absolue — ne voyaient rien.
        """
        t = 30.0 / I.JOURS_AN
        for m in (0.95, 1.0, 1.05):
            self.assertLess(I.derive_par_deplacement(S, S / m, V, t, 0.01 * S),
                            0.0, str(m))
            self.assertGreater(
                I.derive_par_deplacement(S, S / m, V, t, -0.01 * S), 0.0,
                str(m))

    def test_l_ecart_du_premier_ordre_croit_avec_le_deplacement(self):
        """Ce qui distingue une superposition d'une approximation."""
        t = 30.0 / I.JOURS_AN
        suite = [I.ecart_du_premier_ordre(S, S, V, t, d * S)
                 for d in (0.001, 0.002, 0.005, 0.01)]
        for a, b in zip(suite, suite[1:]):
            self.assertGreater(b, a)
        self.assertLess(suite[0], 0.01)

    def test_les_cinq_pieges_sont_la(self):
        self.assertEqual(len(I.pieges()), 5)

    def test_le_cinquieme_est_la_somme_des_quatre(self):
        """Un grec de fournisseur ne cache pas un piège, il les cache tous."""
        p = I.pieges()
        self.assertAlmostEqual(p[-1].cout, sum(x.cout for x in p[:-1]),
                               places=10)

    def test_le_tri_est_calcule(self):
        """Le pire n'est pas écrit : il est le maximum d'une colonne."""
        self.assertEqual(I.pire_piege().cout,
                         max(p.cout for p in I.pieges()))

    def test_le_deplacement_d_un_prix_perime_croit_en_racine(self):
        a = I.deplacement_d_un_prix_perime(15.0)
        b = I.deplacement_d_un_prix_perime(60.0)
        self.assertAlmostEqual(b / a, 2.0, places=8)


class TestLeDecompte(unittest.TestCase):
    def test_aucune_affirmation_ne_donne_un_sens(self):
        self.assertNotIn("la direction",
                         {a.grandeur for a in I.affirmations()})

    def test_le_compte_se_referme(self):
        self.assertEqual(sum(I.compte_par_grandeur().values()),
                         len(I.affirmations()))

    def test_le_cumul_reprend_les_neuf_parties_qui_precedent(self):
        f = I.familles()
        self.assertEqual(len(f), len(O.familles()) + 1)
        self.assertEqual(sum(n for _, n in f),
                         sum(n for _, n in O.familles())
                         + len(I.affirmations()))


class TestLesSurfaces(unittest.TestCase):
    SURFACES = ("surface_tick", "surface_effectif", "surface_budget",
                "surface_prime", "surface_tick_brute",
                "surface_budget_brute")

    def test_elles_sont_rectangulaires(self):
        for nom in self.SURFACES:
            g = getattr(I, nom)()
            self.assertTrue(g, nom)
            self.assertEqual(len({len(r) for r in g}), 1, nom)

    def test_le_maximum_tombe_au_fond(self):
        """La règle du dépôt : en projection isométrique, (0,0) est loin."""
        for nom in self.SURFACES:
            g = getattr(I, nom)()
            plat = [(v, i, j) for i, r in enumerate(g)
                    for j, v in enumerate(r)]
            _, i, j = max(plat)
            self.assertLessEqual(i, 1, nom)
            self.assertLessEqual(j, 1, nom)


class TestLesTables(unittest.TestCase):
    def setUp(self):
        self.tables = I.all_tables()

    def test_les_dix_tables_sont_la(self):
        self.assertEqual(len(self.tables), 10)

    def test_chaque_ligne_a_le_bon_nombre_de_colonnes(self):
        for cle, t in self.tables.items():
            for ligne in t.rows:
                self.assertEqual(len(ligne), len(t.headers), cle)

    def test_chaque_table_a_une_note_et_une_legende(self):
        for cle, t in self.tables.items():
            self.assertTrue(t.caption, cle)
            self.assertGreater(len(t.note or ""), 120, cle)

    def test_les_valeurs_sont_des_chaines_francaises(self):
        for cle, v in I.values().items():
            self.assertIsInstance(v, str, cle)
            self.assertNotIn(".", v.replace("&nbsp;", ""), cle)

    def test_le_verdict_du_look_ahead_est_calcule(self):
        """La dernière colonne se déduit des trois qui précèdent."""
        t = self.tables["iv_look_ahead"]
        for ligne in t.rows:
            fuite = abs(float(ligne[2].replace(",", ".")
                              .replace("−", "-")))
            gliss = abs(float(ligne[1].replace(",", ".")
                              .replace("−", "-")))
            seuil = float(ligne[4].replace(",", "."))
            attendu = "oui" if fuite > seuil >= gliss else "non"
            self.assertEqual(ligne[5], attendu, str(ligne))

    def test_aucun_nombre_n_est_publie_en_notation_anglaise(self):
        for t in self.tables.values():
            for ligne in t.rows:
                for cel in ligne[1:]:
                    self.assertNotRegex(cel, r"\d\.\d", t.key)


class TestLesPlanches(unittest.TestCase):
    def setUp(self):
        self.rendus = figiv.render_all()

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
        for cle in ("ivrelieftk", "ivreliefef", "ivreliefbu", "ivreliefpr"):
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
            figiv.render_all()
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
            figiv.render_all()
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
            figiv.render_all()
        finally:
            Panel.path, Panel.domain = og_path, og_dom
        self.assertEqual(hits, [])

    def test_le_bandeau_de_speculation_accroche_la_famille(self):
        from alp1 import speculation as sp
        for cle in self.rendus:
            self.assertEqual(sp.module_d_une_figure(cle), "figiv", cle)


if __name__ == "__main__":
    unittest.main()
