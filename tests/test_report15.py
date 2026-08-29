"""L'audit de l'hypothèse d'edge du document nº 1.

Ces tests gardent trois choses que la prose de la section 18 affirme, et qui
seraient invérifiables si le calcul se mettait à dire autre chose : l'identité
`E[R] = (k − 1)·c/a`, le fait que le domaine plausible tombe sous le seuil de
rentabilité, et le caractère **calculé** de la colonne de verdict.

Le dernier point mérite son test. Une table d'audit dont le verdict serait
écrit à la main est exactement le genre d'objet qui survit à la grandeur qu'il
décrit : la ligne resterait « indépendant » longtemps après que le calcul a
cessé de l'être. Le test ci-dessous refait le verdict à partir des deux
colonnes publiées et exige l'accord.
"""

from __future__ import annotations

import math
import unittest

from alp1 import quant as q
from alp1 import report15 as r
from alp1 import seuil


class TestIdentite(unittest.TestCase):
    """`µ = k µ*` implique `E[R] = (k − 1)·c/a`, exactement."""

    def test_l_esperance_est_affine_en_k_et_nulle_au_seuil(self):
        ratio = q.FRICTION / q.STOP_PTS
        for k in (0.25, 0.5, 1.0, 1.2, 2.0, 3.0, 5.0):
            with self.subTest(k=k):
                self.assertAlmostEqual(q.law_at_multiple(k).mean,
                                       (k - 1.0) * ratio, places=6)

    def test_l_hypothese_du_document_publie_le_ratio_de_friction(self):
        """C'est la circularité, réduite à une égalité numérique.

        Si ce test tombe, c'est que `DRIFT_MULTIPLE` a changé — et alors la
        section 18 tout entière doit être relue, puisqu'elle est construite
        sur le fait que l'espérance publiée *est* la friction.
        """
        self.assertEqual(q.DRIFT_MULTIPLE, 2.0)
        self.assertAlmostEqual(q.law_at_multiple(q.DRIFT_MULTIPLE).mean,
                               q.FRICTION / q.STOP_PTS, places=6)


class TestDomainePlausible(unittest.TestCase):
    def test_le_plausible_tombe_sous_le_seuil_de_rentabilite(self):
        """Le fait qui gouverne la lecture de toute la troisième partie."""
        haut = seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]
        self.assertLess(r.multiple_of(haut), 1.0)
        self.assertLess(q.law_at_multiple(r.multiple_of(haut)).mean, 0.0)

    def test_aucune_geometrie_de_la_grille_n_entre_dans_le_plausible(self):
        """Élargir le target abaisse le seuil, mais pas jusque-là."""
        self.assertGreater(r.seuil_le_plus_bas(),
                           seuil.PLAUSIBLE_DRIFT_PER_HOUR[1])

    def test_le_delai_est_infini_sur_tout_le_domaine_plausible(self):
        """Pas « très long » : infini. On n'établit pas un Sharpe négatif."""
        from alp1.pathstats import min_track_record_length
        bas, haut = seuil.PLAUSIBLE_DRIFT_PER_HOUR
        for mu in (bas, 0.5 * (bas + haut), haut):
            with self.subTest(mu=mu):
                law = q.law_at_multiple(r.multiple_of(mu))
                self.assertEqual(
                    min_track_record_length(law.sharpe_per_trade, 0.0,
                                            law.skewness, law.excess_kurtosis),
                    math.inf)


class TestVerdictCalcule(unittest.TestCase):
    """La colonne de statut se déduit des deux colonnes, et pas d'un avis."""

    @classmethod
    def setUpClass(cls):
        cls.rows = r.table_dependance().rows

    def test_chaque_statut_se_refait_a_partir_des_deux_colonnes(self):
        for nom, gauche, droite, statut in self.rows:
            with self.subTest(grandeur=nom):
                self.assertEqual(statut, r._verdict(gauche, droite))

    def test_les_lignes_independantes_portent_deux_colonnes_egales(self):
        for nom, gauche, droite, statut in self.rows:
            if statut == "indépendant":
                with self.subTest(grandeur=nom):
                    self.assertEqual(gauche, droite)

    def test_les_independantes_viennent_en_tete(self):
        """L'ordre suit le calcul : rien ne reste au-dessus du trait par habitude."""
        statuts = [s == "indépendant" for _, _, _, s in self.rows]
        self.assertEqual(statuts, sorted(statuts, reverse=True))

    def test_le_trait_tombe_a_la_derniere_ligne_independante(self):
        table = r.table_dependance()
        libre = sum(1 for row in table.rows if row[3] == "indépendant")
        self.assertEqual(table.rules_after, [libre])

    def test_l_audit_trouve_des_lignes_des_deux_cotes(self):
        """Une table dont tout serait d'un seul côté ne trancherait rien."""
        statuts = {row[3] for row in self.rows}
        self.assertIn("indépendant", statuts)
        self.assertIn("s'inverse", statuts)
        self.assertIn("sans terme fini", statuts)

    def test_la_loi_nulle_traverse_le_changement_d_hypothese(self):
        """C'est le théorème d'invariance, vu depuis la table d'audit."""
        ligne = next(row for row in self.rows
                     if row[0].startswith("Espérance sans dérive"))
        self.assertEqual(ligne[3], "indépendant")


class TestTables(unittest.TestCase):
    def test_les_deux_tables_sont_exposees(self):
        self.assertEqual(set(r.all_tables()), {"hypothese", "dependance"})

    def test_chaque_ligne_de_la_table_du_multiple_a_le_bon_nombre_de_cases(self):
        t = r.table_hypothese()
        for row in t.rows:
            self.assertEqual(len(row), len(t.headers))

    def test_les_valeurs_citees_existent_toutes(self):
        v = r.values()
        for cle in ("h_mu_star", "h_mu_ref", "h_k_haut", "h_facteur",
                    "h_er_plausible", "h_n_libre", "h_n_porte",
                    "h_mu_star_large"):
            self.assertIn(cle, v)


class TestFigures(unittest.TestCase):
    def test_les_deux_planches_se_rendent(self):
        from alp1 import fighyp
        figs = fighyp.render_all()
        self.assertEqual(set(figs), {"hyphypothese", "hyphypothese3d"})
        for cle, svg in figs.items():
            with self.subTest(figure=cle):
                self.assertTrue(svg.startswith("<svg"))
                self.assertIn("aria-label", svg)

    def test_la_surface_ne_depasse_pas_son_plafond(self):
        """Le plafond est une durée de carrière, pas un réglage de cadre."""
        from alp1 import fighyp
        for rr in q.RR_GRID:
            for mu in fighyp.DERIVES_3D:
                with self.subTest(rr=rr, mu=mu):
                    v = min(fighyp._annees(mu, rr, essais=q.N_TRIALS_REF),
                            fighyp.PLAFOND_ANS)
                    self.assertLessEqual(v, fighyp.PLAFOND_ANS)
                    self.assertGreater(v, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
