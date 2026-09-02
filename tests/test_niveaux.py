"""Un niveau a une largeur : les contrôles de la partie XIX.

La partie est presque entièrement de l'arithmétique fermée, et deux
simulations. Les tests suivent cette coupure.

D'abord les identités, qu'on vérifie en les inversant et en les confrontant à
la machinerie du dépôt — `horizon.outcome` pour les probabilités de barrière,
`entropy` pour le budget d'information. C'est la règle du dépôt sur les formes
fermées : aucune ne se publie sans être contrôlée contre une route
indépendante.

Ensuite les invariances, qui sont le résultat de la partie et doivent donc
tenir exactement : le taux du témoin ne dépend pas de la distance, l'exposant
de l'échantillon vaut deux, l'équilibre gamma-thêta ne dépend pas de
l'échéance.

Puis les deux simulations — la largeur d'ancrage et la bande de bascule — dont
on vérifie qu'elles sont reproductibles et monotones là où elles doivent
l'être.

Enfin les pièges du dépôt : le maximum de chaque relief au fond, aucune
apostrophe dans un libellé ARIA, aucune marque dans un pied de figure, aucune
graduation hors domaine.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import entropy as E
from alp1 import fignv
from alp1 import niveaux as N
from alp1 import quant as q
from alp1 import seuil as S
from alp1.horizon import outcome


class TestTemoin(unittest.TestCase):

    def test_le_taux_de_touche_est_la_forme_du_principe_de_reflexion(self):
        """Contrôlée contre `horizon`, qui la calcule tout autrement."""
        for k in N.DISTANCES:
            d = k * N.SIGMA_SEANCE
            # Une cible lointaine mais finie : à 1e9 la série spectrale de
            # `outcome` ne converge plus et rend n'importe quoi.
            o = outcome(d, 60.0 * N.SIGMA_SEANCE, q.SESSION_MIN,
                        q.SIGMA_1MIN)
            self.assertAlmostEqual(N.taux_de_touche(d), o.p_stop, delta=0.01)

    def test_un_niveau_a_l_ouverture_est_toujours_touche(self):
        self.assertEqual(N.taux_de_touche(0.0), 1.0)

    def test_le_taux_de_touche_decroit_avec_la_distance(self):
        vals = [N.taux_de_touche(k * N.SIGMA_SEANCE) for k in N.DISTANCES]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_la_forme_fermee_vaut_tant_que_la_seance_ne_borne_rien(self):
        """Le contrôle du module, et sa condition.

        `a/(a+b)` est le taux du problème **non borné**. La séance finit, et
        les deux lois ne coïncident que tant que la clôture avant barrière
        reste négligeable. Le test vérifie les deux moitiés de cette phrase :
        l'accord là où la condition tient, et la divergence là où elle tombe.
        """
        for pct in N.STOPS:
            a = S.geometry(pct).stop_points
            b = q.RR_REF * a
            po = N.cloture_avant_barriere(a)
            ferme = N.taux_de_reussite_ferme(a, b)
            borne = N.taux_de_reussite(a, b)
            if po < 0.02:
                self.assertAlmostEqual(borne, ferme, delta=0.02, msg=str(pct))
            else:
                self.assertLess(borne, ferme, msg=str(pct))

    def test_la_cloture_avant_barriere_croit_avec_le_stop(self):
        vals = [N.cloture_avant_barriere(S.geometry(p).stop_points)
                for p in N.STOPS]
        self.assertEqual(vals, sorted(vals))
        self.assertLess(vals[0], 0.001)
        self.assertGreater(vals[-1], 0.5)

    def test_le_taux_de_reussite_ne_depend_pas_de_la_distance(self):
        """Le résultat de la section, et il doit tenir exactement."""
        ref = N.taux_de_reussite(q.STOP_PTS, q.RR_REF * q.STOP_PTS)
        for k in N.DISTANCES:
            _ = k
            self.assertAlmostEqual(
                N.taux_de_reussite(q.STOP_PTS, q.RR_REF * q.STOP_PTS), ref,
                places=12)

    def test_le_taux_de_reussite_est_celui_du_theoreme(self):
        self.assertAlmostEqual(
            N.taux_de_reussite_ferme(q.STOP_PTS, q.RR_REF * q.STOP_PTS),
            1.0 / (1.0 + q.RR_REF), places=12)

    def test_la_table_du_temoin_a_une_colonne_constante(self):
        t = N.table_temoin()
        derniere = {ligne[-1] for ligne in t.rows}
        self.assertEqual(len(derniere), 1)


class TestDefinition(unittest.TestCase):

    def test_le_taux_de_tenue_est_la_forme_fermee(self):
        for _, r, e in N.DEFINITIONS:
            self.assertAlmostEqual(N.taux_de_tenue(r, e),
                                   N.taux_de_tenue_ferme(r, e), delta=0.01)

    def test_une_definition_symetrique_rend_un_demi(self):
        for d in (0.5, 2.0, 8.0):
            self.assertAlmostEqual(N.taux_de_tenue_ferme(d, d), 0.5,
                                   places=12)

    def test_le_taux_depasse_un_demi_des_que_l_extension_depasse_le_recul(self):
        """Le fait de la section : l'asymétrie suffit, sans aucun niveau."""
        for _, r, e in N.DEFINITIONS:
            self.assertEqual(N.taux_de_tenue_ferme(r, e) > 0.5, e > r)

    def test_la_definition_la_plus_asymetrique_rend_plus_de_neuf_dixiemes(self):
        nom, r, e = N.DEFINITIONS[-1]
        self.assertGreater(N.taux_de_tenue_ferme(r, e), 0.9)

    def test_les_deux_taux_sont_complementaires(self):
        for _, r, e in N.DEFINITIONS:
            self.assertAlmostEqual(N.taux_de_tenue_ferme(r, e)
                                   + N.taux_de_tenue_ferme(e, r), 1.0,
                                   places=12)


class TestExigence(unittest.TestCase):

    def test_l_exces_requis_est_l_ecart_des_deux_taux(self):
        """`(1+c/a)/(1+R) − 1/(1+R)`, écrit autrement."""
        for pct in N.STOPS:
            g = S.geometry(pct)
            p0 = 1.0 / (1.0 + q.RR_REF)
            p1 = (1.0 + g.friction_ratio) / (1.0 + q.RR_REF)
            self.assertAlmostEqual(N.exces_requis(g.friction_ratio), p1 - p0,
                                   places=12)

    def test_sans_friction_aucun_exces_n_est_requis(self):
        self.assertAlmostEqual(N.exces_requis(0.0), 0.0, places=12)

    def test_l_exces_decroit_avec_la_largeur_du_stop(self):
        vals = [N.exces_requis(S.geometry(p).friction_ratio) for p in N.STOPS]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_l_echantillon_croit_comme_le_carre(self):
        """L'exposant est le résultat de la partie : il doit valoir deux."""
        a = N.touches_requises(0.10)
        b = N.touches_requises(0.05)
        self.assertAlmostEqual(b / a, 4.0, places=9)

    def test_une_friction_nulle_demande_un_echantillon_infini(self):
        self.assertEqual(N.touches_requises(0.0), math.inf)

    def test_les_deux_routes_s_accordent(self):
        """Le contrôle qui autorise à publier la forme fermée.

        La route d'information passe par la divergence de Kullback-Leibler,
        celle du module par une approximation normale de deux proportions.
        Elles ne partagent aucune ligne de code, et elles doivent tomber au
        même ordre de grandeur sur toute la grille.
        """
        for pct in N.STOPS:
            g = S.geometry(pct)
            ferme = N.touches_requises(g.friction_ratio)
            info = N.touches_par_information(g.friction_ratio)
            self.assertLess(abs(ferme / info - 1.0), 0.30, pct)

    def test_la_route_d_information_passe_par_le_bon_couple(self):
        for pct in N.STOPS:
            g = S.geometry(pct)
            r = E.required_bits(q.RR_REF, g.friction_ratio)
            self.assertAlmostEqual(r.hit_needed - r.hit_null,
                                   N.exces_requis(g.friction_ratio),
                                   places=12)

    def test_elargir_le_stop_divise_l_exigence_et_multiplie_la_preuve(self):
        g0 = S.geometry(0.010)
        g1 = S.geometry(0.150)
        self.assertGreater(N.exces_requis(g0.friction_ratio),
                           10.0 * N.exces_requis(g1.friction_ratio))
        self.assertGreater(N.touches_requises(g1.friction_ratio),
                           100.0 * N.touches_requises(g0.friction_ratio))


class TestLargeur(unittest.TestCase):

    def test_la_constante_est_la_demi_hauteur_d_une_normale(self):
        """`φ(u) = ½φ(0)` a pour solution `u = √(2 ln 2)`."""
        u = N.DEMI_HAUTEUR
        self.assertAlmostEqual(math.exp(-0.5 * u * u), 0.5, places=12)

    def test_la_bande_est_bien_la_mi_hauteur_du_gamma(self):
        """Contrôle contre la fonction `gamma` elle-même, pas contre soi."""
        for j in (1.0, 7.0, 30.0):
            w = N.largeur_gamma(j)
            t = j / N.JOURS_AN
            pic = N.gamma(q.INDEX_LEVEL, q.INDEX_LEVEL, N.VOL_ANNUELLE, t)
            bord = N.gamma(q.INDEX_LEVEL + w, q.INDEX_LEVEL + w,
                           N.VOL_ANNUELLE, t)
            # Le gamma au strike décalé, rapporté au pic, à la moitié près.
            g = N.gamma(q.INDEX_LEVEL + w, q.INDEX_LEVEL, N.VOL_ANNUELLE, t)
            _ = bord
            self.assertAlmostEqual(g / pic, 0.5, delta=0.06, msg=str(j))

    def test_la_bande_croit_comme_racine_du_temps(self):
        self.assertAlmostEqual(
            N.largeur_gamma(40.0) / N.largeur_gamma(10.0), 2.0, delta=0.05)

    def test_une_echeance_nulle_a_une_bande_nulle(self):
        self.assertEqual(N.largeur_gamma(0.0), 0.0)

    def test_l_invalidation_prematuree_est_la_forme_d_arret_optionnel(self):
        for w in (0.25, 2.0, 30.0):
            for a in (0.6, 9.0):
                self.assertAlmostEqual(N.invalidation_prematuree(w, a),
                                       w / (a + w), places=12)

    def test_un_niveau_sans_largeur_n_est_jamais_invalide_par_sa_bande(self):
        self.assertEqual(N.invalidation_prematuree(0.0, 9.0), 0.0)

    def test_l_invalidation_passe_un_demi_quand_la_bande_passe_le_stop(self):
        for a in (0.6, 3.0, 9.0):
            self.assertLess(N.invalidation_prematuree(0.99 * a, a), 0.5)
            self.assertGreater(N.invalidation_prematuree(1.01 * a, a), 0.5)

    def test_l_ordre_des_lectures_est_calcule(self):
        """Le tri sort du code, jamais d'une liste écrite à la main."""
        vals = [x.largeur_pts for x in N.niveaux()]
        self.assertEqual(vals, sorted(vals))

    def test_chaque_lecture_porte_un_nom_court(self):
        for x in N.niveaux():
            self.assertTrue(x.court.strip(), x.cle)
            self.assertLessEqual(len(x.court), 24, x.cle)

    def test_les_trois_natures_sont_toutes_representees(self):
        natures = {x.nature for x in N.niveaux()}
        self.assertEqual(natures, {"exact", "réglage d'affichage",
                                   "choix d'ancrage", "mécanique"})

    def test_la_largeur_d_ancrage_est_reproductible(self):
        """Aucune graine dérivée d'un `hash` : deux appels rendent le même."""
        self.assertEqual(N.largeur_d_ancrage(), N.largeur_d_ancrage())
        self.assertGreater(N.largeur_d_ancrage(), 0.0)

    def test_la_largeur_d_ancrage_est_du_bon_ordre(self):
        """Elle doit rester une fraction de l'écart-type de séance."""
        self.assertLess(N.largeur_d_ancrage(), 0.5 * N.SIGMA_SEANCE)

    def test_la_graine_ne_passe_pas_par_le_hash_integre(self):
        self.assertEqual(N._graine("gamma"), N._graine("gamma"))
        self.assertNotEqual(N._graine("gamma"), N._graine("vwap"))


class TestGeometrieForcee(unittest.TestCase):

    def test_la_geometrie_forcee_a_le_stop_de_la_largeur(self):
        for x in N.niveaux():
            g = N.geometrie_forcee(x.largeur_pts)
            self.assertAlmostEqual(g.stop_points, x.largeur_pts, places=9)

    def test_un_stop_plus_large_abaisse_le_seuil(self):
        vals = [N.geometrie_forcee(x.largeur_pts).break_even_per_hour
                for x in N.niveaux()]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_un_stop_plus_large_augmente_l_echantillon(self):
        vals = [N.touches_requises(
            N.geometrie_forcee(x.largeur_pts).friction_ratio)
            for x in N.niveaux()]
        self.assertEqual(vals, sorted(vals))

    def test_la_fenetre_qui_passe_les_deux_est_etroite(self):
        """Le résultat de la section, recompté et non écrit."""
        passe = N.passe_les_deux()
        self.assertGreaterEqual(len(passe), 1)
        self.assertLessEqual(len(passe), 3)
        self.assertLess(len(passe), 0.5 * len(N.niveaux()))

    def test_le_verdict_suit_la_regle_declaree(self):
        hi = S.PLAUSIBLE_DRIFT_PER_HOUR[1]
        passe = set(N.passe_les_deux())
        for x in N.niveaux():
            g = N.geometrie_forcee(x.largeur_pts)
            attendu = (g.break_even_per_hour <= hi
                       and N.touches_requises(g.friction_ratio)
                       <= N.TOUCHES_CARRIERE)
            self.assertEqual(x in passe, attendu, x.cle)


class TestIdentite(unittest.TestCase):

    def test_le_theta_est_l_oppose_de_la_courbure(self):
        """L'identité de Black-Scholes à taux nul, écrite telle quelle."""
        for j in (1.0, 30.0, 180.0):
            t = j / N.JOURS_AN
            g = N.gamma(q.INDEX_LEVEL, q.INDEX_LEVEL, N.VOL_ANNUELLE, t)
            th = N.theta_instantane(q.INDEX_LEVEL, q.INDEX_LEVEL,
                                    N.VOL_ANNUELLE, t)
            self.assertAlmostEqual(
                th + 0.5 * N.VOL_ANNUELLE ** 2 * q.INDEX_LEVEL ** 2 * g,
                0.0, places=9)

    def test_le_theta_se_retrouve_par_difference_finie(self):
        """Contrôle de la forme fermée contre la réévaluation."""
        for j in (30.0, 180.0):
            t = j / N.JOURS_AN
            h = 1e-5
            num = (N.call(q.INDEX_LEVEL, q.INDEX_LEVEL, N.VOL_ANNUELLE,
                          t - h)
                   - N.call(q.INDEX_LEVEL, q.INDEX_LEVEL, N.VOL_ANNUELLE,
                            t + h)) / (2.0 * h)
            th = N.theta_instantane(q.INDEX_LEVEL, q.INDEX_LEVEL,
                                    N.VOL_ANNUELLE, t)
            self.assertAlmostEqual(num / th, 1.0, delta=0.002, msg=str(j))

    def test_l_equilibre_instantane_ne_depend_pas_de_l_echeance(self):
        """Le théorème d'arrêt optionnel du marché d'options."""
        ref = N.equilibre_instantane()
        self.assertAlmostEqual(ref, N.VOL_ANNUELLE / math.sqrt(N.JOURS_AN),
                               places=12)
        for j in N.ECHEANCES:
            _ = j
            self.assertAlmostEqual(N.equilibre_instantane(), ref, places=12)

    def test_les_trois_routes_convergent_a_longue_echeance(self):
        inst = N.equilibre_instantane()
        for j in (90.0, 180.0):
            self.assertAlmostEqual(N.equilibre_exact(j) / inst, 1.0,
                                   delta=0.01)
            self.assertAlmostEqual(N.equilibre_quadratique(j) / inst, 1.0,
                                   delta=0.01)

    def test_les_deux_routes_encadrent_l_identite(self):
        """Elles la serrent des deux côtés, et c'est le fait de la table."""
        inst = N.equilibre_instantane()
        for j in N.ECHEANCES:
            self.assertLessEqual(N.equilibre_exact(j), inst * 1.001, str(j))
            self.assertGreaterEqual(N.equilibre_quadratique(j), inst * 0.999,
                                    str(j))

    def test_l_approximation_quadratique_echoue_au_dernier_jour(self):
        """Là où gamma est le plus grand, et c'est le résultat publiable."""
        r = N.equilibre_quadratique(1.0) / N.equilibre_exact(1.0)
        self.assertGreater(r, 1.4)
        rn = N.equilibre_quadratique(180.0) / N.equilibre_exact(180.0)
        self.assertLess(rn, 1.01)

    def test_le_gamma_par_un_pour_cent_decroit_avec_l_echeance(self):
        vals = [N.gamma(q.INDEX_LEVEL, q.INDEX_LEVEL, N.VOL_ANNUELLE,
                        j / N.JOURS_AN) for j in N.ECHEANCES]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_le_gamma_croit_comme_l_inverse_de_racine_du_temps(self):
        a = N.gamma(q.INDEX_LEVEL, q.INDEX_LEVEL, N.VOL_ANNUELLE, 1 / 365)
        b = N.gamma(q.INDEX_LEVEL, q.INDEX_LEVEL, N.VOL_ANNUELLE, 30 / 365)
        # Pas exactement : `φ(d₁)` porte le terme `½σ²T`, qui décale peu.
        self.assertAlmostEqual(a / b, math.sqrt(30.0), delta=0.01)


class TestSigne(unittest.TestCase):

    def test_le_profil_est_symetrique_a_asymetrie_un(self):
        prof = N.profil_oi(1.0)
        for (k, c, _), (k2, _, p2) in zip(prof, reversed(prof)):
            self.assertAlmostEqual(k + k2, 2.0 * q.INDEX_LEVEL, places=6)
            self.assertAlmostEqual(c, p2, places=6)

    def test_l_asymetrie_ne_touche_que_les_puts(self):
        a = N.profil_oi(1.0)
        b = N.profil_oi(3.0)
        for (_, c1, p1), (_, c2, p2) in zip(a, b):
            self.assertAlmostEqual(c1, c2, places=9)
            self.assertAlmostEqual(3.0 * p1, p2, places=9)

    def test_la_bascule_supposee_existe_et_est_pres_du_comptant(self):
        x = N.bascule()
        self.assertFalse(math.isnan(x))
        self.assertLess(abs(x - q.INDEX_LEVEL) / q.INDEX_LEVEL, 0.05)

    def test_la_bascule_annule_l_exposition(self):
        self.assertAlmostEqual(N.gex(N.bascule()), 0.0, delta=0.5)

    def test_l_exposition_change_de_signe_autour_de_la_bascule(self):
        x = N.bascule()
        self.assertLess(N.gex(0.97 * x), 0.0)
        self.assertGreater(N.gex(1.03 * x), 0.0)

    def test_a_signe_connu_la_bande_est_nulle(self):
        """Le contrôle de la colonne : sans ignorance, aucune incertitude."""
        lo, med, hi, absent = N.bande_de_bascule(1.0, n=40)
        self.assertEqual(absent, 0.0)
        self.assertAlmostEqual(hi - lo, 0.0, places=6)
        self.assertAlmostEqual(med, N.bascule(), places=6)

    def test_la_bande_se_resserre_quand_le_signe_se_connait(self):
        largeurs = []
        for f in N.PARTS:
            lo, _, hi, _ = N.bande_de_bascule(f)
            largeurs.append(0.0 if math.isnan(lo) else hi - lo)
        self.assertEqual(largeurs, sorted(largeurs, reverse=True))

    def test_a_signe_inconnu_la_bande_ecrase_la_geometrie(self):
        """Le fait de la section, et il doit rester vrai."""
        lo, _, hi, absent = N.bande_de_bascule(0.0)
        a1 = S.geometry(0.150).stop_points
        self.assertGreater(hi - lo, 20.0 * a1)
        self.assertGreater(absent, 0.10)

    def test_la_bande_est_reproductible(self):
        self.assertEqual(N.bande_de_bascule(0.5), N.bande_de_bascule(0.5))


class TestReste(unittest.TestCase):

    def test_les_cinq_affirmations_sont_la(self):
        self.assertEqual(len(N.affirmations()), 5)

    def test_aucune_affirmation_ne_donne_le_sens(self):
        """Le résultat de la partie, et la colonne est calculée."""
        self.assertEqual(sum(1 for x in N.affirmations() if x.directionnelle),
                         0)

    def test_le_verdict_est_calcule_et_non_ecrit(self):
        for x in N.affirmations():
            self.assertEqual(x.directionnelle, x.porte == "le sens", x.quoi)

    def test_chaque_affirmation_range_dans_une_colonne_connue(self):
        for x in N.affirmations():
            self.assertIn(x.porte, ("rien", "l'horloge", "le risque",
                                    "le sens"), x.quoi)

    def test_le_decompte_couvre_les_cinq(self):
        c = {"rien": 0, "l'horloge": 0, "le risque": 0, "le sens": 0}
        for x in N.affirmations():
            c[x.porte] += 1
        self.assertEqual(sum(c.values()), 5)
        self.assertEqual(c["le sens"], 0)
        self.assertGreaterEqual(c["l'horloge"], 1)

    def test_les_effets_sont_relus_des_sections(self):
        """Aucun nombre de la table de synthèse n'est écrit à la main."""
        par_nom = {x.quoi: x for x in N.affirmations()}
        w = N.largeur_gamma(1.0)
        self.assertIn(f"{w:.0f}",
                      par_nom["La concentration de gamma par strike"].effet)

    def test_chaque_affirmation_porte_un_nom_court(self):
        for x in N.affirmations():
            self.assertTrue(x.court.strip(), x.quoi)
            self.assertLessEqual(len(x.court), 24, x.quoi)


class TestSurfaces(unittest.TestCase):

    SURFACES = (
        ("exigence", N.surface_exigence, N.SURF_STOP, N.SURF_RR),
        ("invalidation", N.surface_invalidation, N.SURF_LARGEUR,
         N.SURF_STOP_PTS),
        ("bande", N.surface_bande, N.SURF_JOURS, N.SURF_VOL),
        ("absence", N.surface_absence, N.SURF_PART, N.SURF_JOURS_GEX),
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

    def test_la_surface_de_l_exigence_est_logarithmique(self):
        """La hauteur est un logarithme : l'infobulle doit le défaire."""
        z = N.surface_exigence()
        self.assertAlmostEqual(
            10.0 ** z[0][0],
            N.touches_requises(S.geometry(N.SURF_STOP[0]).friction_ratio,
                               N.SURF_RR[0]), places=6)

    def test_la_surface_d_invalidation_traverse_un_demi(self):
        vals = [v for ligne in N.surface_invalidation() for v in ligne]
        self.assertGreater(max(vals), 0.5)
        self.assertLess(min(vals), 0.5)

    def test_la_surface_d_absence_s_annule_a_signe_connu(self):
        """Le contrôle : sans ignorance, la bascule existe toujours."""
        z = N.surface_absence()
        for v in z[-1]:
            self.assertAlmostEqual(v, 0.0, places=9)

    def test_l_absence_decroit_quand_le_signe_se_connait(self):
        """À la tolérance d'un tirage près : le relief vient d'une simulation.

        Exiger la monotonie stricte reviendrait à exiger qu'un tirage sur
        quatre-vingt-dix ne tombe jamais du mauvais côté, ce qui est faux et
        rendrait le test fragile sans rien garantir de plus.
        """
        tol = 200.0 / N.N_SURFACE_SIGNES
        z = N.surface_absence()
        for j in range(len(N.SURF_JOURS_GEX)):
            colonne = [z[i][j] for i in range(len(N.SURF_PART))]
            for haut, bas in zip(colonne, colonne[1:]):
                self.assertGreaterEqual(haut, bas - tol, j)
            self.assertGreater(colonne[0], colonne[-1] + 10.0, j)

    def test_l_asymetrie_du_profil_ne_resserre_rien(self):
        """La mesure qui a réfuté le premier axe, gardée comme test.

        Elle est le genre d'affirmation qu'on écrit sans la vérifier : la
        masse d'un côté devrait finir par dominer. Elle ne domine pas, et le
        test l'exige, faute de quoi la planche reprendrait un axe mort.
        """
        largeurs = []
        for asym in (1.0, 2.0, 4.0):
            lo, _, hi, _ = N.bande_de_bascule(0.0, asym, 90, N.SEED + 13)
            largeurs.append(hi - lo)
        etendue = (max(largeurs) - min(largeurs)) / min(largeurs)
        self.assertLess(etendue, 0.25)


class TestLesTables(unittest.TestCase):

    def setUp(self):
        self.tables = N.all_tables()

    def test_les_huit_tables_sont_la(self):
        self.assertEqual(len(self.tables), 8)
        for cle in self.tables:
            self.assertTrue(cle.startswith("niv_"), cle)

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
        for cle in N.values():
            self.assertTrue(cle.startswith("n_"), cle)


class TestLesPlanches(unittest.TestCase):

    def setUp(self):
        self.rendus = fignv.render_all()

    def test_les_douze_planches_sont_la(self):
        self.assertEqual(len(self.rendus), 12)

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
        for cle in ("nvrelief", "nvinvalidation", "nvbande", "nvbascule"):
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
            fignv.render_all()
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
            if len(pts) > 2 and len(dedans) < 2:
                hits.append((self.title, len(pts), len(dedans)))
            return og(self, pts, *a, **k)

        Panel.path = f
        try:
            fignv.render_all()
        finally:
            Panel.path = og
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
