"""Tests des tables, valeurs et figures des deux corrections.

Une table qui cite un nombre que son module ne produit pas est pire qu'une
table absente. Ces tests vérifient que chaque nombre affiché vient bien du
calcul dont il se réclame, et que le point de rupture cité est celui de la
table des ruptures du document — non un second point de rupture recalculé à
côté, qui pourrait en diverger silencieusement.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import figdecay, report3
from alp1.calib import REFERENCE, breaking_points, verdicts
from alp1.decay import breaking_decay, decay_rate, runways, surviving_edge
from alp1.report import Table
from alp1.report3 import ASOF_YEAR, EDGE_BPS, _breaking_edge_bps, year
from alp1.scaling import coherence_gap, robust_entry


class TestPointDeRupture(unittest.TestCase):
    def test_le_seuil_vient_de_la_table_des_ruptures_du_document(self):
        """Le point de rupture cité est celui de `calib`, non un doublon."""
        concl = next(v.conclusion for v in verdicts()
                     if v.enclosure.key == "net_points")
        attendu = next(b.value for b in breaking_points(concl)
                       if b.axis == "edge_bps")
        self.assertAlmostEqual(_breaking_edge_bps(), attendu, places=12)

    def test_le_seuil_est_sous_la_derive_publiee(self):
        self.assertLess(_breaking_edge_bps(), EDGE_BPS)


class TestTables(unittest.TestCase):
    def setUp(self):
        self.tables = report3.all_tables()

    def test_chaque_table_porte_sa_propre_cle(self):
        for cle, t in self.tables.items():
            with self.subTest(table=cle):
                self.assertIsInstance(t, Table)
                self.assertEqual(t.key, cle)

    def test_chaque_ligne_a_le_nombre_de_colonnes_des_en_tetes(self):
        for cle, t in self.tables.items():
            for i, ligne in enumerate(t.rows):
                with self.subTest(table=cle, ligne=i):
                    self.assertEqual(len(ligne), len(t.headers))

    def test_aucune_table_n_est_vide(self):
        for cle, t in self.tables.items():
            with self.subTest(table=cle):
                self.assertTrue(t.rows)
                self.assertTrue(t.caption)

    def test_les_annees_s_ecrivent_sans_separateur_de_milliers(self):
        """« 2 026 » est une quantité, « 2026 » est une année."""
        for cle in ("decay_runway", "decay_scenarios"):
            with self.subTest(table=cle):
                rendu = self.tables[cle].to_text() + self.tables[cle].caption
                self.assertNotRegex(rendu, r"[12]\s\d{3}")

    def test_le_verdict_de_la_grille_suit_la_marge_affichee(self):
        for ligne in self.tables["decay_scenarios"].rows:
            marge = float(ligne[4].rstrip("×").replace(",", ".")
                          .replace("−", "-"))
            with self.subTest(marge=marge):
                self.assertEqual(ligne[5] == "tient", marge > 1.0)

    def test_la_chaine_d_echelle_commence_a_la_calibration_du_document(self):
        premiere = self.tables["scaling_chain"].rows[0]
        self.assertEqual(premiere[0], "0,50")

    def test_l_heure_du_protocole_est_signalee_dans_la_table(self):
        statuts = [l[4] for l in self.tables["scaling_entry"].rows]
        self.assertEqual(sum("protocole" in s for s in statuts), 1)
        self.assertEqual(sum("optimum" in s for s in statuts), 1)


class TestValeurs(unittest.TestCase):
    def setUp(self):
        self.v = report3.values()

    def test_chaque_valeur_est_une_chaine_rendue(self):
        for cle, val in self.v.items():
            with self.subTest(cle=cle):
                self.assertIsInstance(val, str)
                self.assertTrue(val)

    def test_aucune_valeur_ne_porte_de_point_decimal_anglais(self):
        for cle, val in self.v.items():
            with self.subTest(cle=cle):
                self.assertNotRegex(val, r"\d\.\d")

    def test_la_decote_de_rupture_correspond_au_seuil(self):
        attendu = breaking_decay(EDGE_BPS, _breaking_edge_bps()) * 100
        self.assertAlmostEqual(
            float(self.v["decay_break"].replace(",", ".")), attendu, places=1)

    def test_la_derive_restante_correspond_a_l_age_de_la_publication(self):
        r = runways(EDGE_BPS, _breaking_edge_bps(), ASOF_YEAR)[0]
        self.assertAlmostEqual(
            float(self.v["decay_first_left"].replace(",", ".")),
            surviving_edge(EDGE_BPS, r.age, decay_rate()), places=2)

    def test_le_facteur_de_coherence_est_celui_du_module(self):
        _, _, facteur = coherence_gap()
        self.assertAlmostEqual(
            float(self.v["scal_factor"].replace(",", ".")), facteur, places=3)

    def test_l_heure_retenue_est_celle_du_protocole(self):
        self.assertEqual(self.v["scal_entry_ref"],
                         str(int(REFERENCE.entry_min)))

    def test_l_heure_optimale_est_celle_que_le_module_designe(self):
        meilleure = min(robust_entry(), key=lambda r: r[2])[0]
        self.assertEqual(self.v["scal_entry_best"], str(int(meilleure)))

    def test_les_annees_s_ecrivent_sans_separateur(self):
        for cle in ("asof", "decay_first_year", "decay_last_year",
                    "decay_first_expiry", "decay_last_expiry"):
            with self.subTest(cle=cle):
                self.assertRegex(self.v[cle], r"^\d{4}$")


class TestAnnee(unittest.TestCase):
    def test_une_annee_est_rendue_sans_separateur(self):
        self.assertEqual(year(2026), "2026")
        self.assertEqual(year(2027.5), "2028")

    def test_une_annee_infinie_ne_casse_pas(self):
        with self.assertRaises((OverflowError, ValueError)):
            year(math.inf)


class TestFigures(unittest.TestCase):
    def setUp(self):
        self.figs = figdecay.render_all()

    def test_chaque_figure_est_un_svg_complet(self):
        for cle, svg in self.figs.items():
            with self.subTest(figure=cle):
                self.assertTrue(svg.startswith("<svg"))
                self.assertTrue(svg.rstrip().endswith("</svg>"))

    def test_les_balises_sont_equilibrees(self):
        for cle, svg in self.figs.items():
            with self.subTest(figure=cle):
                self.assertEqual(svg.count("<svg"), svg.count("</svg>"))
                self.assertEqual(svg.count("<text"), svg.count("</text>"))

    def test_aucune_couleur_n_est_ecrite_en_dur(self):
        """Les couleurs passent par les variables CSS, jamais en dur."""
        for cle, svg in self.figs.items():
            with self.subTest(figure=cle):
                self.assertNotRegex(svg, r"#[0-9a-fA-F]{3,6}\b")

    def test_chaque_figure_porte_une_description(self):
        for cle, svg in self.figs.items():
            with self.subTest(figure=cle):
                self.assertRegex(svg, r'aria-label="[^"]{20,}"')

    def test_les_annees_des_figures_s_ecrivent_sans_separateur(self):
        etiquettes = re.findall(r">([^<]*)</text>", self.figs["decayrunway"])
        for e in etiquettes:
            with self.subTest(etiquette=e):
                self.assertNotRegex(e, r"[12]\s\d{3}")


if __name__ == "__main__":
    unittest.main()
