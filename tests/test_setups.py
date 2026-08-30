"""La grammaire du setup : ce qui est déclaré, ce qui est mesuré, et l'écart.

Les contrôles de ce fichier ferment quatre portes, et chacune s'est déjà
ouverte ailleurs dans le dépôt :

* **la divergence figure/table** — une planche qui coche une case que la
  mesure aurait refusée ;
* **la circularité** — un seuil de confirmation dérivé de ce qu'il sert à
  évaluer, ou un verdict écrit plutôt que calculé ;
* **le chevauchement des fenêtres** — mille contacts qui ne portent pas mille
  fois l'information d'un seul, et font apparaître un effet là où il n'y en a
  pas ;
* **le regard en avant** — un niveau calculé avec des barres que l'opérateur
  n'avait pas encore vues.
"""

from __future__ import annotations

import math
import unittest

from alp1 import concepts as C
from alp1 import quant, seuil, setups, vprofile
from alp1.barriers import required_drift


class TestDeclarations(unittest.TestCase):
    """Ce qui est écrit d'avance l'est une fois, et sans redite."""

    def test_les_cles_de_setup_sont_uniques(self):
        cles = [s.cle for s in setups.SETUPS]
        self.assertEqual(len(cles), len(set(cles)))

    def test_chaque_setup_reference_un_niveau_et_une_confirmation_declares(self):
        niveaux = {n.cle for n in setups.NIVEAUX}
        confs = {c.cle for c in setups.CONFIRMATIONS}
        for s in setups.SETUPS:
            with self.subTest(setup=s.cle):
                self.assertIn(s.niveau, niveaux)
                self.assertIn(s.confirmation, confs)

    def test_les_seuils_declares_ne_viennent_pas_de_la_mesure(self):
        """Les cinq seuils sont des littéraux, jamais des grandeurs mesurées.

        Le contrôle est grossier — il vérifie qu'ils valent exactement ce que
        le module déclare — mais il attrape la seule faute qui compte : un
        seuil réglé après coup sur ce qu'il sert à évaluer, ce qui est le
        piège de circularité que la section 18 du document nº 1 documente.
        """
        self.assertEqual(setups.MULT_VOLUME, 1.5)
        self.assertEqual(setups.PART_MECHE, 0.60)
        self.assertEqual(setups.DEPASSEMENT, 1.0)
        self.assertAlmostEqual(setups.PART_DELTA, 1.0 / 3.0)
        self.assertEqual(setups.Z_ABSORPTION, C.Z_ABSORPTION)

    def test_chaque_confirmation_oriente_l_attente(self):
        for c in setups.CONFIRMATIONS:
            with self.subTest(confirmation=c.cle):
                self.assertIn(c.sens_attendu, (-1, +1))


class TestSeance(unittest.TestCase):
    """La séance simulée, et ce qu'on peut en rejouer."""

    @classmethod
    def setUpClass(cls):
        cls.seances = setups.seances()

    def test_la_simulation_est_deterministe(self):
        self.assertIs(self.seances, setups.seances())
        premiere = self.seances[0][17]
        rejouee = setups.footprint(0, 17)[0]
        self.assertEqual(premiere, rejouee)

    def test_le_footprint_rejoue_epuise_le_volume_de_la_barre(self):
        """Les rangées se partagent le volume de la barre, à l'arrondi près."""
        for minute in (12, 200, 380):
            with self.subTest(minute=minute):
                barre, cellules = setups.footprint(0, minute)
                total = sum(c.total for c in cellules)
                self.assertLessEqual(abs(total - barre.volume),
                                     len(cellules) + 1)

    def test_les_rangees_couvrent_l_etendue_de_la_barre(self):
        barre, cellules = setups.footprint(0, 200)
        self.assertLessEqual(cellules[0].prix, barre.bas + 1e-9)
        self.assertGreaterEqual(cellules[-1].prix + 0.25, barre.haut - 1e-9)

    def test_la_correlation_du_delta_est_du_bon_ordre(self):
        """Le delta doit dire le sens sans le dire parfaitement.

        À une corrélation d'un, la confirmation de delta ne serait qu'une
        redite de la clôture ; à zéro, elle ne dirait rien. Le contrôle borne
        largement, parce que c'est `ALIGNEMENT` qui est déclaré et non cette
        corrélation, qui n'en est que la conséquence.
        """
        r = setups.correlation_delta()
        self.assertGreater(r, 0.45)
        self.assertLess(r, 0.85)

    def test_la_seance_sans_derive_ne_derive_pas(self):
        fins = [s[-1].cloture for s in self.seances]
        moyenne = sum(fins) / len(fins)
        ecart = math.sqrt(sum((x - moyenne) ** 2 for x in fins) / len(fins))
        self.assertLess(abs(moyenne), 3.0 * ecart / math.sqrt(len(fins)))


class TestNiveaux(unittest.TestCase):
    """Un niveau se calcule sur le passé, et sur rien d'autre."""

    def test_aucun_niveau_ne_regarde_en_avant(self):
        barres = setups.seances()[0]
        profil = vprofile.from_path(
            [b.cloture for b in barres[:setups.DEBUT]],
            step=setups.PAS_PROFIL)
        for cle, calcul in setups._CALCUL.items():
            for i in (setups.DEBUT + 20, setups.DEBUT + 90):
                with self.subTest(niveau=cle, minute=i):
                    entier = calcul(barres, i, profil)
                    tronque = calcul(barres[:i + 1], i, profil)
                    self.assertEqual(entier, tronque)

    def test_les_contacts_sont_comptes_sur_la_seconde_moitie(self):
        for n in setups.NIVEAUX:
            lot = setups.contacts(n.cle)
            with self.subTest(niveau=n.cle):
                self.assertTrue(lot)
                self.assertTrue(all(c.minute >= setups.DEBUT for c in lot))

    def test_le_contact_se_rearme_avant_de_recompter(self):
        """Deux contacts d'un même niveau ne se suivent pas d'une minute.

        Sans réarmement, une heure passée à osciller sur un niveau compterait
        soixante contacts, et le débit d'occasions — d'où sort tout le chapitre
        du coût — n'aurait plus de sens.
        """
        for n in setups.NIVEAUX:
            precedent: dict[tuple[int, float], int] = {}
            for c in setups.contacts(n.cle):
                cle = (c.seance, c.niveau)
                if cle in precedent:
                    with self.subTest(niveau=n.cle):
                        self.assertGreater(c.minute - precedent[cle], 1)
                precedent[cle] = c.minute


class TestConfirmation(unittest.TestCase):
    """La confirmation tient quand tous ses critères tiennent, et pas avant."""

    def test_la_figure_ne_peut_pas_cocher_ce_que_la_mesure_refuse(self):
        """`_confirme` et `criteres` lisent la même liste, par construction.

        C'est le contrôle qui interdit à une planche d'afficher trois coches
        sous une confirmation que la table compte comme absente.
        """
        for n in setups.NIVEAUX:
            barres_par_seance: dict[int, tuple] = {}
            for c in setups.contacts(n.cle)[:200]:
                if c.seance not in barres_par_seance:
                    barres_par_seance[c.seance] = setups.contexte(c)
                barres, median = barres_par_seance[c.seance]
                barre = barres[c.minute]
                for k in ("absorption", "rejet", "execution"):
                    attendu = all(x.ok for x in setups.criteres(
                        k, barre, c.niveau, c.sens, median))
                    with self.subTest(niveau=n.cle, minute=c.minute, conf=k):
                        self.assertEqual(k in c.confirmations, attendu)

    def test_chaque_critere_publie_sa_valeur_et_son_exigence(self):
        c = setups.contacts("poc")[0]
        barres, median = setups.contexte(c)
        for k in ("absorption", "rejet", "execution"):
            for critere in setups.criteres(k, barres[c.minute], c.niveau,
                                           c.sens, median):
                with self.subTest(confirmation=k, critere=critere.court):
                    self.assertTrue(critere.valeur)
                    self.assertTrue(critere.exige)
                    self.assertTrue(critere.court)

    def test_aucune_confirmation_n_est_ni_toujours_ni_jamais_vraie(self):
        for s in setups.SETUPS:
            m = setups.mesurer(s.cle)
            with self.subTest(setup=s.cle):
                self.assertGreater(m.part_confirmee, 0.0)
                self.assertLess(m.part_confirmee, 0.5)


class TestEmbargo(unittest.TestCase):
    """Deux fenêtres qui se recouvrent ne sont pas deux observations."""

    def test_les_observations_retenues_ont_des_fenetres_disjointes(self):
        for s in setups.SETUPS:
            lot = [c for c in setups.contacts(s.niveau)
                   if s.confirmation in c.confirmations]
            garde = setups._independants(lot, s.horizon_min)
            derniere: dict[int, float] = {}
            for c in garde:
                with self.subTest(setup=s.cle):
                    if c.seance in derniere:
                        self.assertGreaterEqual(
                            c.minute - derniere[c.seance], s.horizon_min)
                derniere[c.seance] = c.minute

    def test_l_embargo_retire_des_observations_sans_les_retirer_toutes(self):
        s = setups._PAR_SETUP["lvn-rejet"]
        lot = [c for c in setups.contacts(s.niveau)
               if s.confirmation in c.confirmations]
        garde = setups._independants(lot, s.horizon_min)
        self.assertLess(len(garde), len(lot))
        self.assertGreater(len(garde), 0.2 * len(lot))

    def test_les_frequences_se_comptent_sur_le_lot_entier(self):
        """Le débit d'occasions n'a rien à voir avec l'indépendance.

        Compter les fréquences sur les seules fenêtres disjointes diviserait
        le débit par trois et gonflerait tous les délais du chapitre du coût.
        """
        m = setups.mesurer("lvn-rejet")
        self.assertGreater(m.confirmes, m.independants)
        self.assertAlmostEqual(m.par_seance,
                               m.contacts / float(setups.SEANCES), places=6)


class TestLoiNulle(unittest.TestCase):
    """Le résultat du chapitre : la confirmation ne déplace pas la suite."""

    @classmethod
    def setUpClass(cls):
        cls.pool = setups.poule()

    def test_le_contact_brut_ne_bat_pas_le_pile_ou_face(self):
        demi = 1.96 * math.sqrt(0.25 / self.pool.n_brut)
        self.assertLess(abs(self.pool.p_brut - 0.5), 2.0 * demi)

    def test_le_contact_confirme_ne_bat_pas_le_pile_ou_face(self):
        """**Le contrôle central du chapitre.**

        Si une confirmation déplaçait la probabilité d'aller dans le sens
        attendu sur un prix sans dérive, ce serait le détecteur qu'il faudrait
        relire, pas le marché : aucune règle d'entrée ne peut créer
        d'espérance là où la dérive est nulle.
        """
        demi = 0.01 * self.pool.demi_intervalle
        self.assertLess(abs(self.pool.p_confirme - 0.5), 2.0 * demi)

    def test_les_excursions_mises_en_commun_sont_symetriques(self):
        self.assertGreater(self.pool.rapport, 0.88)
        self.assertLess(self.pool.rapport, 1.12)

    def test_les_deux_orientations_valent_un_demi_chacune(self):
        for n, p in ((self.pool.n_poursuite, self.pool.p_poursuite),
                     (self.pool.n_rejet, self.pool.p_rejet)):
            demi = 1.96 * math.sqrt(0.25 / n)
            with self.subTest(n=n):
                self.assertLess(abs(p - 0.5), 2.5 * demi)


class TestCout(unittest.TestCase):
    """Le prix d'une confirmation, et d'où il vient exactement."""

    def test_la_confirmation_ne_touche_pas_le_nombre_de_decisions(self):
        """Il ne dépend que de la géométrie, et la confirmation n'en est pas.

        C'est ce qui rend le coût entièrement imputable au débit d'occasions,
        et donc calculable sans hypothèse.
        """
        for s in setups.SETUPS:
            with self.subTest(setup=s.cle):
                self.assertAlmostEqual(setups.cout(s.cle).decisions,
                                       C.decisions_pour(s.horizon_min),
                                       places=6)

    def test_le_facteur_de_delai_est_l_inverse_de_la_part_confirmee(self):
        for s in setups.SETUPS:
            m = setups.mesurer(s.cle)
            with self.subTest(setup=s.cle):
                self.assertAlmostEqual(setups.cout(s.cle).facteur,
                                       1.0 / m.part_confirmee, places=6)

    def test_la_derive_compensatrice_suit_la_racine_du_facteur(self):
        """Elle vaut la dérive de rentabilité de l'horizon, fois √F.

        Le nombre de décisions varie comme l'inverse du carré de l'écart de
        taux à établir ; diviser ce nombre par `F` demande donc de multiplier
        l'écart par `√F`. Le test refait le calcul depuis le module de
        barrières, sans repasser par la fonction qu'il contrôle.
        """
        for s in setups.SETUPS:
            a, b, friction = C.geometrie(s.horizon_min)
            mu = required_drift(a, b, quant.SIGMA_1MIN, friction) * 60.0
            attendu = mu * math.sqrt(setups.cout(s.cle).facteur)
            with self.subTest(setup=s.cle):
                self.assertAlmostEqual(setups.derive_compensatrice(s.cle),
                                       attendu, places=9)
                self.assertGreater(attendu, 0.0)

    def test_le_verdict_est_calcule_et_non_ecrit(self):
        basse, haute = seuil.PLAUSIBLE_DRIFT_PER_HOUR
        for s in setups.SETUPS:
            mu = setups.derive_compensatrice(s.cle)
            v = setups.verdict(s.cle)
            with self.subTest(setup=s.cle):
                if mu <= basse:
                    self.assertIn("ordinaire", v)
                elif mu <= haute:
                    self.assertIn("haute", v)
                else:
                    self.assertIn("irremboursable", v)

    def test_exiger_la_confirmation_allonge_toujours_le_delai(self):
        for s in setups.SETUPS:
            c = setups.cout(s.cle)
            with self.subTest(setup=s.cle):
                self.assertGreater(c.annees_retenu, c.annees_brut)


class TestSorties(unittest.TestCase):
    """Ce que le module publie au document."""

    def test_les_trois_tables_ont_des_lignes_et_une_lecture(self):
        tables = setups.all_tables()
        self.assertEqual(set(tables), {"grammaire", "confirmation", "cout"})
        for cle, t in tables.items():
            with self.subTest(table=cle):
                self.assertTrue(t.rows)
                self.assertTrue(t.note)
                for ligne in t.rows:
                    self.assertEqual(len(ligne), len(t.headers))

    def test_la_table_de_grammaire_couvre_les_douze_setups(self):
        self.assertEqual(len(setups.table_grammaire().rows), len(setups.SETUPS))

    def test_la_table_de_confirmation_porte_sa_ligne_de_mise_en_commun(self):
        rows = setups.table_confirmation().rows
        self.assertEqual(len(rows), len(setups.SETUPS) + 1)
        self.assertIn("commun", rows[-1][0])

    def test_toutes_les_valeurs_sont_des_chaines_non_vides(self):
        for cle, valeur in setups.values().items():
            with self.subTest(cle=cle):
                self.assertIsInstance(valeur, str)
                self.assertTrue(valeur.strip())

    def test_les_valeurs_ne_heurtent_pas_celles_du_catalogue(self):
        self.assertFalse(set(setups.values()) & set(C.values()))


if __name__ == "__main__":
    unittest.main()
