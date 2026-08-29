"""Contrôles qui portent sur **toutes** les figures du dépôt, sans exception.

Chaque module de figures avait jusqu'ici ses propres contrôles, ou n'en avait
pas. Une règle appliquée à un module sur neuf n'est pas une règle : le défaut
qui a motivé ce fichier — une entité numérique d'espace fine que le contrôle
des couleurs prenait pour un hexadécimal — a vécu deux commits dans un module
que rien ne surveillait.

Ces tests balaient la totalité. Ajouter un module de figures sans l'inscrire
ici fait échouer le premier test, ce qui est le comportement voulu.
"""

from __future__ import annotations

import importlib
import re
import unittest

#: Tous les modules de figures du dépôt. La liste est vérifiée contre le
#: contenu réel du paquet : elle ne peut pas se démoder en silence.
MODULES = (
    "figures", "figterm", "figquant", "figalp2", "figdecay",
    "figpower", "figrisk", "figedge", "figstrat", "figdisc", "figflux",
    "fighyp",
)


def _render(nom: str) -> dict[str, str]:
    return importlib.import_module(f"alp1.{nom}").render_all()


class TestCouverture(unittest.TestCase):
    def test_aucun_module_de_figures_n_echappe_a_la_liste(self):
        """Le test qui empêche cette liste de se démoder."""
        import pathlib
        import alp1
        dossier = pathlib.Path(alp1.__file__).parent
        trouves = {p.stem for p in dossier.glob("fig*.py")
                   if p.stem != "figcss"}
        self.assertEqual(trouves, set(MODULES))

    def test_chaque_module_expose_un_rendu(self):
        for m in MODULES:
            with self.subTest(module=m):
                self.assertTrue(_render(m))


class TestToutesLesFigures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.figs = {f"{m}:{k}": v
                    for m in MODULES for k, v in _render(m).items()}

    def test_aucune_couleur_n_est_ecrite_en_dur(self):
        """Les couleurs passent par les variables CSS, sans exception.

        C'est ce qui rend chaque figure correcte en thème clair comme en
        thème sombre sans duplication. La règle attrape aussi les entités
        numériques dont le corps ressemble à un hexadécimal, et c'est
        délibéré : une espace fine s'écrit en caractère littéral.
        """
        for cle, svg in self.figs.items():
            with self.subTest(figure=cle):
                self.assertNotRegex(svg, r"#[0-9a-fA-F]{3,6}\b")

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
                self.assertEqual(svg.count("<title>"), svg.count("</title>"))

    def test_chaque_figure_porte_une_description(self):
        """Sans elle, la figure est muette pour un lecteur d'écran."""
        for cle, svg in self.figs.items():
            with self.subTest(figure=cle):
                self.assertRegex(svg, r'aria-label="[^"]{20,}"')

    def test_chaque_figure_declare_sa_boite(self):
        for cle, svg in self.figs.items():
            with self.subTest(figure=cle):
                self.assertRegex(svg, r'viewBox="0 0 [\d.]+ [\d.]+"')

    def test_aucun_pied_ne_reste_dans_le_svg(self):
        """Le pied de figure part en entier, ou il ne part pas du tout.

        `extraire_pieds` sortait les lignes de pied une à une, sur un critère
        de longueur. Une phrase dont la dernière ligne tombait sous le seuil
        se retrouvait coupée en deux : le début rendu sous la figure, la fin
        restée dans le SVG. Trois figures ont vécu ainsi, dont une dont la
        note se terminait sur une virgule.

        La marque `cap` a remplacé le critère de longueur. Ce test vérifie
        qu'aucune ligne ainsi marquée ne survit à l'extraction.
        """
        from alp1.workingpaper import extraire_pieds

        for cle, svg in self.figs.items():
            with self.subTest(figure=cle):
                reste, pieds = extraire_pieds(svg)
                self.assertNotIn('class="lg cap"', reste,
                                 "une ligne de pied est restée dans le SVG")
                if pieds:
                    self.assertFalse(
                        pieds[-1].rstrip().endswith(","),
                        f"la note de {cle} se termine sur une virgule : "
                        f"sa dernière ligne manque")

    def test_aucune_cle_de_figure_n_est_dupliquee(self):
        vues: dict[str, str] = {}
        for cle in self.figs:
            module, nom = cle.split(":", 1)
            with self.subTest(figure=nom):
                self.assertNotIn(nom, vues,
                                 f"{nom} produite par {vues.get(nom)} et {module}")
                vues[nom] = module


if __name__ == "__main__":
    unittest.main()
