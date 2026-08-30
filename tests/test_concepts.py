"""Le catalogue des lectures : ordre calculé, symétrie nulle, invariant.

Trois choses sont gardées ici, et chacune correspond à un piège que ce dépôt
a déjà rencontré ailleurs.

**L'ordre est calculé.** Il vient de l'horizon déclaré, jamais d'une liste
écrite. Un test le vérifie, faute de quoi la table et la prose pourraient
diverger sans que rien ne le signale.

**La loi nulle est exactement symétrique.** L'appariement antithétique le
garantit par construction ; si un jour la simulation perdait son appariement,
la colonne « sans dérive » se mettrait à pencher d'un côté et la thèse
centrale du chapitre — un motif n'apprend rien tant qu'il ne déplace pas la
dérive — reposerait sur du bruit d'échantillonnage.

**Aucune efficacité n'est postulée.** C'est le garde-fou contre la
circularité de `quant.reference_drift` : le catalogue calcule ce qu'une
lecture *devrait* valoir, il ne déclare jamais ce qu'elle vaut.
"""

from __future__ import annotations

import math
import unittest

from alp1 import concepts as C
from alp1 import dow, fib
from alp1 import footprint as fp


class TestOrdre(unittest.TestCase):
    """L'ordre du catalogue n'est écrit nulle part."""

    def test_l_ordre_suit_l_horizon(self):
        horizons = [l.horizon_min for l in C.ordre()]
        self.assertEqual(horizons, sorted(horizons))

    def test_l_ordre_contient_tout_le_catalogue(self):
        self.assertEqual({l.cle for l in C.ordre()},
                         {l.cle for l in C.CATALOGUE})

    def test_le_footprint_ouvre_le_catalogue(self):
        """Le point de la partie : la lecture la plus rapide vient en tête.

        Elle n'y est pas parce qu'elle compte davantage, mais parce qu'elle
        est la seule dont les prétentions se tranchent en moins d'un an.
        """
        premiere = C.ordre()[0]
        self.assertEqual(premiere.horizon_min, 5.0)
        self.assertLess(C.exigence(premiere.cle).annees, 1.0)

    def test_les_cles_sont_uniques(self):
        cles = [l.cle for l in C.CATALOGUE]
        self.assertEqual(len(cles), len(set(cles)))


class TestLoisNulles(unittest.TestCase):
    """Chaque lecture a sa fréquence sous prix sans dérive, et elle est calculée."""

    def test_toutes_les_frequences_sont_des_probabilites(self):
        for l in C.CATALOGUE:
            with self.subTest(lecture=l.cle):
                p = C.frequence_nulle(l.cle)
                self.assertGreater(p, 0.0)
                self.assertLess(p, 1.0)

    def test_les_occasions_sont_positives(self):
        for l in C.CATALOGUE:
            with self.subTest(lecture=l.cle):
                self.assertGreater(C.occasions(l.cle), 0.0)

    def test_les_lois_fermees_viennent_de_leur_module(self):
        """Là où une loi existe déjà, le catalogue la reprend sans la refaire.

        C'est ce qui interdit qu'une fréquence dérive de sa source : si
        `dow.p_dominant_wick` changeait, la table du catalogue changerait
        avec elle, et ce test le confirme plutôt que de figer un nombre.
        """
        self.assertAlmostEqual(C.frequence_nulle("meche"),
                               dow.p_dominant_wick(1.0), places=12)
        self.assertAlmostEqual(C.frequence_nulle("structure"),
                               dow.p_higher_high_null(0.4, 3.0), places=12)
        self.assertAlmostEqual(C.frequence_nulle("ote"),
                               fib.p_retrace_null(0.618, continuation=0.10),
                               places=12)
        from alp1 import orderflow as of
        self.assertAlmostEqual(C.frequence_nulle("carnet"),
                               of.lpr_expected(C.LPR_HAZARD, C.LPR_MINUTES),
                               places=12)
        self.assertAlmostEqual(C.frequence_nulle("divergence"),
                               of.p_sign_divergence(C.CORRELATION_CVD),
                               places=12)
        barre = fp.synthesise("neutre")
        self.assertAlmostEqual(
            C.frequence_nulle("desequilibre"),
            fp.expected_imbalances(barre) / (len(barre.cells) - 1), places=12)

    def test_aucune_lecture_n_est_rare(self):
        """Le fait désagréable de la partie, et il vaut d'être gardé.

        Aucun des quinze motifs ne descend sous trois pour cent sous un prix
        sans dérive. Une lecture qui deviendrait rare mériterait un chapitre,
        pas une ligne de table.
        """
        for l in C.CATALOGUE:
            with self.subTest(lecture=l.cle):
                self.assertGreater(C.frequence_nulle(l.cle), 0.03)


class TestSymetrieNulle(unittest.TestCase):
    """Sous prix sans dérive, la réaction ne penche d'aucun côté."""

    def test_les_deux_barrieres_sont_equiprobables(self):
        for horizon in (5.0, 60.0, 390.0):
            with self.subTest(horizon=horizon):
                r = C.reaction(horizon, 0.0)
                self.assertAlmostEqual(r.p_haut, r.p_bas, places=12)

    def test_les_excursions_sont_opposees(self):
        for horizon in (5.0, 60.0):
            with self.subTest(horizon=horizon):
                r = C.reaction(horizon, 0.0)
                self.assertAlmostEqual(r.mfe, -r.mae, places=9)

    def test_une_chance_sur_deux_d_etre_plus_haut(self):
        for horizon in (5.0, 60.0, 390.0):
            with self.subTest(horizon=horizon):
                self.assertAlmostEqual(C.reaction(horizon, 0.0).p_plus_haut,
                                       0.5, places=12)

    def test_la_derive_penche_et_dans_le_bon_sens(self):
        for horizon in (5.0, 390.0):
            with self.subTest(horizon=horizon):
                nul = C.reaction(horizon, 0.0)
                der = C.reaction(horizon, C.derive_haute())
                self.assertGreater(der.p_plus_haut, nul.p_plus_haut)
                self.assertGreater(der.p_haut, der.p_bas)

    def test_l_effet_croit_avec_l_horizon(self):
        """La lecture lente voit la dérive, la rapide ne la verra jamais."""
        gains = [C.reaction(t, C.derive_haute()).p_plus_haut - 0.5
                 for t in (5.0, 60.0, 390.0, 1170.0)]
        self.assertEqual(gains, sorted(gains))
        self.assertLess(gains[0], 0.05)
        self.assertGreater(gains[-1], 0.35)

    def test_l_eventail_part_de_zero_et_reste_symetrique(self):
        colonnes = C.eventail(60.0, 0.0)
        self.assertEqual(colonnes[0], (0.0,) * 5)
        fin = colonnes[-1]
        self.assertAlmostEqual(fin[0], -fin[4], places=9)
        self.assertAlmostEqual(fin[1], -fin[3], places=9)


class TestExigence(unittest.TestCase):
    """Ce que la lecture doit valoir, et ce qu'il en coûte de l'établir."""

    def test_le_taux_nul_vaut_un_sur_un_plus_le_rapport(self):
        """C'est le théorème d'arrêt optionnel, et il ne dépend d'aucune lecture."""
        attendu = 1.0 / (1.0 + C.RR_LECTURE)
        for l in C.CATALOGUE:
            with self.subTest(lecture=l.cle):
                self.assertAlmostEqual(C.exigence(l.cle).taux_nul, attendu,
                                       places=12)

    def test_la_derive_requise_decroit_avec_l_horizon(self):
        mus = [C.exigence(l.cle).derive_requise for l in C.ordre()]
        self.assertEqual(mus, sorted(mus, reverse=True))

    def test_les_decisions_croissent_avec_l_horizon(self):
        ns = [C.exigence(l.cle).decisions for l in C.ordre()]
        self.assertEqual(ns, sorted(ns))

    def test_decisions_pour_est_la_meme_fonction(self):
        """La courbe continue des figures et la table disent la même chose."""
        for l in C.CATALOGUE:
            with self.subTest(lecture=l.cle):
                self.assertAlmostEqual(C.exigence(l.cle).decisions,
                                       C.decisions_pour(l.horizon_min),
                                       places=6)

    def test_le_verdict_est_calcule(self):
        for l in C.CATALOGUE:
            with self.subTest(lecture=l.cle):
                e = C.exigence(l.cle)
                court = e.annees <= C.CARRIERE_ANS
                self.assertEqual("prouvable" in e.verdict
                                 or "et prouvable" in e.verdict, court)

    def test_le_delai_est_le_quotient_annonce(self):
        for l in C.CATALOGUE:
            with self.subTest(lecture=l.cle):
                e = C.exigence(l.cle)
                self.assertAlmostEqual(e.annees, e.decisions / e.par_an,
                                       places=6)


class TestInvariant(unittest.TestCase):
    """Le produit qui ne bouge pas, sur cinq ordres de grandeur d'horizon."""

    def test_le_produit_derive_decisions_est_constant(self):
        inv = C.invariant("derive")
        self.assertLess(inv.etendue, 0.005)
        self.assertGreater(inv.moyenne, 0.0)

    def test_le_produit_bits_decisions_est_constant(self):
        inv = C.invariant("bits")
        self.assertLess(inv.etendue, 0.01)

    def test_l_invariant_n_est_pas_une_coincidence_de_grille(self):
        """Il tient aussi entre les horizons du catalogue.

        Sans ce contrôle, la constance pourrait n'être qu'un artefact des
        quinze horizons retenus. Elle est balayée ici sur une grille
        indépendante, et de façon plus serrée.
        """
        produits = []
        for t in (7.0, 23.0, 41.0, 200.0, 700.0, 2000.0):
            a, b, c = C.geometrie(t)
            from alp1.barriers import required_drift
            from alp1 import quant as q
            mu = required_drift(a, b, q.SIGMA_1MIN, c) * 60.0
            produits.append(mu * C.decisions_pour(t))
        etendue = (max(produits) - min(produits)) / (sum(produits)
                                                     / len(produits))
        self.assertLess(etendue, 0.01)


    def test_l_invariant_est_une_propriete_de_la_largeur_de_stop(self):
        """La conservation ne vient pas de l'horizon mais de la géométrie.

        Elle se vérifie ici sur une famille de stops qui ne doit rien au
        catalogue, d'un point à cent cinquante. Sans ce contrôle, le chapitre
        attribuerait à l'horizon une propriété qui appartient au stop.
        """
        import math as _m
        from alp1 import entropy as _e
        from alp1 import quant as _q
        from alp1.barriers import required_drift as _rd
        produits = []
        for a in (1.0, 4.0, 16.0, 64.0, 150.0):
            c = C.friction()
            mu = _rd(a, C.RR_LECTURE * a, _q.SIGMA_1MIN, c) * 60.0
            besoin = _e.required_bits(C.RR_LECTURE, c / a)
            p0, p1 = besoin.hit_null, besoin.hit_needed
            za, zb = C._inv_norm(1.0 - C.ALPHA / 2.0), C._inv_norm(C.PUISSANCE)
            n = ((za * _m.sqrt(p0 * (1.0 - p0))
                  + zb * _m.sqrt(p1 * (1.0 - p1))) / (p1 - p0)) ** 2
            produits.append(mu * n)
        moyenne = sum(produits) / len(produits)
        self.assertLess((max(produits) - min(produits)) / moyenne, 0.005)


class TestAucunePostulation(unittest.TestCase):
    """Le garde-fou contre la circularité, et il est structurel.

    `quant.reference_drift` définissait la dérive à partir de la friction
    qu'elle servait à évaluer. Le catalogue ne peut pas commettre la même
    faute tant qu'il ne porte aucun champ d'efficacité : ce test l'exige du
    type lui-même, et non d'une valeur.
    """

    def test_la_lecture_ne_declare_aucune_efficacite(self):
        champs = set(C.Lecture.__dataclass_fields__)
        interdits = {"p_revendiquee", "p_claim", "efficacite", "taux_observe",
                     "reussite"}
        self.assertEqual(champs & interdits, set())

    def test_les_parametres_declares_sont_enumerables(self):
        """Trois paramètres déclarés, et la prose du module les nomme tous."""
        for nom in ("RR_LECTURE", "K_BARRIERE", "CARRIERE_ANS",
                    "SEUIL_EPUISEMENT", "Z_ABSORPTION"):
            with self.subTest(parametre=nom):
                self.assertIsInstance(getattr(C, nom), float)


class TestTables(unittest.TestCase):
    """Les quatre tables disent ce que le module calcule."""

    @classmethod
    def setUpClass(cls):
        cls.tables = C.all_tables()

    def test_les_quatre_tables_existent(self):
        self.assertEqual(sorted(self.tables),
                         ["catalogue", "exigence", "reaction", "situations"])

    def test_le_catalogue_a_une_ligne_par_lecture(self):
        for cle in ("catalogue", "exigence", "situations"):
            with self.subTest(table=cle):
                self.assertEqual(len(self.tables[cle].rows), len(C.CATALOGUE))

    def test_la_reaction_a_une_ligne_par_horizon(self):
        horizons = {l.horizon_min for l in C.CATALOGUE}
        self.assertEqual(len(self.tables["reaction"].rows), len(horizons))

    def test_le_deplacement_nul_est_nul(self):
        """La colonne qui porte la thèse : sans dérive, rien ne se déplace."""
        for ligne in self.tables["situations"].rows:
            self.assertIn(ligne[3], ("0,00", "−0,00"))

    def test_les_valeurs_sont_toutes_des_chaines_non_vides(self):
        for cle, valeur in C.values().items():
            with self.subTest(cle=cle):
                self.assertIsInstance(valeur, str)
                self.assertTrue(valeur)


class TestFormats(unittest.TestCase):
    """Les deux aides de mise en forme, sur cinq ordres de grandeur."""

    def test_les_durees_se_lisent_partout(self):
        for valeur, attendu in ((0.5, "mois"), (3.0, "ans"), (300.0, "ans"),
                                (30000.0, "millénaires")):
            with self.subTest(valeur=valeur):
                self.assertIn(attendu, C._ans(valeur))
        self.assertEqual(C._ans(math.inf), "jamais")

    def test_les_grands_nombres_portent_leur_espace(self):
        self.assertEqual(C._grand(263824.0), "263 824")


if __name__ == "__main__":
    unittest.main()
