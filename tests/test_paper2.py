"""Tests du document ALP-2 : figures, valeurs injectées, assemblage.

Le document tire ses chiffres du même noyau que ses tables. Ces tests
vérifient que le lien tient : qu'aucune balise ne survit à l'assemblage, que
les figures sont du SVG valide, et surtout que les valeurs citées dans la
prose sont celles que les tables affichent — la divergence entre les deux
étant le seul défaut qu'un gabarit ne signale pas de lui-même.
"""

from __future__ import annotations

import math
import re
import unittest

from alp1 import figalp2, paper2
from alp1.calib import BOX, CONCLUSIONS, REFERENCE, breaking_points
from alp1.costs import COST_BASE, ES
from alp1.momentum import edge_points_from_bps, required_ir
from alp1.report2 import (
    EDGE_REF,
    FRICTION,
    SIGMA_1MIN,
    STOP_PTS,
    V1_SIGMA_1MIN,
    all_tables,
    v1_outcome,
    v2_outcome,
)


class TestFigures(unittest.TestCase):
    def test_all_figures_render_as_svg(self):
        figs = figalp2.render_all()
        self.assertEqual(len(figs), 5)
        for key, svg in figs.items():
            with self.subTest(figure=key):
                self.assertTrue(svg.startswith("<svg"), key)
                self.assertTrue(svg.rstrip().endswith("</svg>"), key)
                self.assertIn('class="fig"', svg)
                self.assertIn("role=\"img\"", svg)
                self.assertIn("aria-label=", svg)

    def test_figures_carry_no_hardcoded_colour(self):
        """Les couleurs passent par les variables CSS, jamais en dur.

        C'est ce qui rend les figures correctes en thème clair comme en thème
        sombre sans duplication.
        """
        for key, svg in figalp2.render_all().items():
            with self.subTest(figure=key):
                self.assertNotRegex(svg, r"#[0-9a-fA-F]{3,6}\b")

    def test_figure_tags_are_balanced(self):
        for key, svg in figalp2.render_all().items():
            with self.subTest(figure=key):
                for tag in ("text", "circle", "rect", "path", "line"):
                    opens = len(re.findall(rf"<{tag}[ >]", svg))
                    closes = len(re.findall(rf"</{tag}>", svg))
                    selfc = len(re.findall(rf"<{tag}\b[^>]*/>", svg))
                    self.assertEqual(opens, closes + selfc, f"{key}/{tag}")


class TestValues(unittest.TestCase):
    def setUp(self):
        self.v = paper2.values()

    def test_every_value_is_a_rendered_string(self):
        for key, val in self.v.items():
            with self.subTest(key=key):
                self.assertIsInstance(val, str)
                self.assertTrue(val.strip())
                self.assertNotIn("nan", val.lower())
                self.assertNotIn("inf", val.lower())

    def test_threshold_ratio_matches_its_components(self):
        """Le facteur cité est bien le quotient des deux seuils cités."""
        o1, o2 = v1_outcome(), v2_outcome()
        ir1 = required_ir(FRICTION, V1_SIGMA_1MIN, o1.expected_time)
        ir2 = required_ir(FRICTION, SIGMA_1MIN, o2.expected_time)
        self.assertAlmostEqual(float(self.v["ir_factor"].replace(",", ".")),
                               ir1 / ir2, places=2)

    def test_signal_margin_matches_edge_and_threshold(self):
        o2 = v2_outcome()
        edge = edge_points_from_bps(EDGE_REF, REFERENCE.index_level)
        ir_signal = edge / (SIGMA_1MIN * math.sqrt(o2.expected_time))
        ir2 = required_ir(FRICTION, SIGMA_1MIN, o2.expected_time)
        self.assertAlmostEqual(float(self.v["ir_margin"].replace(",", ".")),
                               ir_signal / ir2, places=1)

    def test_net_points_is_edge_minus_friction(self):
        edge = edge_points_from_bps(EDGE_REF, REFERENCE.index_level)
        self.assertAlmostEqual(float(self.v["net_pts"].replace(",", ".")),
                               edge - FRICTION, places=2)

    def test_stop_matches_noise_band(self):
        """Le stop cité est la bande, non un nombre choisi."""
        self.assertAlmostEqual(float(self.v["band"].replace(",", ".")),
                               STOP_PTS, places=1)

    def test_breaking_values_agree_with_calib(self):
        net = next(c for c in CONCLUSIONS if c.key == "net_points")
        brk = {b.axis: b for b in breaking_points(net, BOX)}
        self.assertAlmostEqual(float(self.v["brk_friction"].replace(",", ".")),
                               brk["friction"].value, places=2)
        self.assertAlmostEqual(float(self.v["brk_edge"].replace(",", ".")),
                               brk["edge_bps"].value, places=2)

    def test_seal_is_a_prefix_of_the_protocol_digest(self):
        from alp1.prereg import PROTOCOL
        self.assertTrue(PROTOCOL.seal.startswith(self.v["seal"]))
        self.assertEqual(len(self.v["seal"]), 16)

    def test_grades_are_consistent_between_scales(self):
        on100 = float(self.v["grade2"].replace(",", "."))
        on20 = float(self.v["grade2_20"].replace(",", "."))
        self.assertAlmostEqual(on100 / 5, on20, places=1)


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.html = paper2.build()

    def test_no_unresolved_placeholder(self):
        self.assertEqual(re.findall(r"\{\{[^}]+\}\}", self.html), [])

    def test_le_quatrieme_build_sort_aussi_sa_prose_de_pied(self):
        """Les quatre documents traitent leurs figures pareil, ou aucun.

        `paper` et `paper2` gardaient tous deux leur prose d'explication
        *dans* leurs SVG, faute de pouvoir importer `workingpaper` sans
        cycle. `alp1.pieds` porte le traitement pour les quatre ; ce test
        garde le dernier arrivé.
        """
        from alp1 import pieds

        for svg in re.findall(r'<svg class="fig".*?</svg>', self.html, re.S):
            hauteur = pieds.hauteur(svg)
            for m in pieds.TEXTE_SVG.finditer(svg):
                classes = set(m.group(1).split())
                if "sub" in classes or "keep" in classes:
                    continue
                if not ({"lg", "ax"} & classes):
                    continue
                y = re.search(r'y="(-?[\d.]+)"', m.group(2))
                if not y or float(y.group(1)) < hauteur - pieds.MARGE_PIED:
                    continue
                texte = re.sub(r"<[^>]+>", "", m.group(3)).strip()
                self.assertLessEqual(len(texte), pieds.LONGUEUR_PROSE, texte)

    def test_aucune_note_de_figure_ne_coupe_une_phrase(self):
        """Une phrase qui reprend en minuscule après un point est coupée."""
        for note in re.findall(r'<p class="note">(.*?)</p>', self.html, re.S):
            if 'class="lab"' in note:
                continue
            texte = re.sub(r"<[^>]+>", "", note)
            for m in re.finditer(r"\.\s+([a-zà-öø-ÿ])", texte):
                self.fail(f"phrase coupée : "
                          f"…{texte[max(0, m.start() - 50):m.start() + 30]}…")

    def test_document_has_title_and_shell(self):
        self.assertIn("<title>", self.html)
        self.assertIn('<div class="sheet"', self.html)
        self.assertIn("Résumé", self.html)

    def test_every_table_of_the_module_is_reachable(self):
        """Le gabarit cite chaque table produite par le module ALP-2.

        Une table calculée mais jamais citée serait du travail perdu ; une
        table citée mais absente ferait échouer l'assemblage.
        """
        template = paper2.TEMPLATE.read_text(encoding="utf-8")
        cited = set(re.findall(r"\{\{TABLE:([a-z0-9_]+)\}\}", template))
        self.assertEqual(cited, set(all_tables()))

    def test_every_figure_is_cited_once(self):
        template = paper2.TEMPLATE.read_text(encoding="utf-8")
        cited = re.findall(r"\{\{FIGURE:([a-z0-9_]+)\|", template)
        self.assertEqual(sorted(cited), sorted(figalp2.FIGURES))
        self.assertEqual(len(cited), len(set(cited)))

    def test_figures_and_tables_are_numbered_from_one(self):
        figs = re.findall(r"<span class=\"lab\">Figure (\d+)</span>", self.html)
        self.assertEqual([int(n) for n in figs], list(range(1, len(figs) + 1)))

    def test_build_is_deterministic(self):
        self.assertEqual(self.html, paper2.build())

    def test_theme_tokens_are_injected(self):
        self.assertIn("prefers-color-scheme: dark", self.html)
        self.assertIn('data-theme="dark"', self.html)
        self.assertIn('data-theme="light"', self.html)

    def test_no_performance_claim_without_disclaimer(self):
        self.assertIn("ne constitue ni un conseil en investissement", self.html)
        self.assertIn("Aucune mesure n'est conduite ici", self.html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
