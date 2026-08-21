"""Tests du document de travail : fusion, structure, navigation, figures.

La fusion de deux documents crée des risques qu'aucun des deux n'avait :
des clés qui se recouvrent silencieusement, un sommaire qui ment sur la
numérotation, des ancres mortes. Ces tests portent sur ces risques-là.
"""

from __future__ import annotations

import re
import unittest

from alp1 import paper, paper2, report2, workingpaper as monograph


class TestFusion(unittest.TestCase):
    def test_les_collisions_de_valeur_sont_declarees(self):
        """Toute clé commune aux deux documents porte la même valeur, ou est déclarée."""
        v1, v2 = paper.values(), paper2.values()
        divergentes = {k for k in set(v1) & set(v2) if v1[k] != v2[k]}
        self.assertEqual(divergentes, set(monograph.COLLISIONS_VALEURS))

    def test_les_collisions_de_table_sont_declarees(self):
        from alp1 import lexicon, quant, report
        t1 = {**report.all_tables(), **lexicon.all_tables(), **quant.all_tables()}
        self.assertEqual(set(t1) & set(report2.all_tables()),
                         set(monograph.COLLISIONS_TABLES))

    def test_la_version_alp2_est_exposee_sous_un_nom_prefixe(self):
        v = monograph.values()
        for cle in monograph.COLLISIONS_VALEURS:
            self.assertIn(cle, v)
            self.assertIn(f"{cle}_a2", v)
            self.assertNotEqual(v[cle], v[f"{cle}_a2"])

    def test_aucune_valeur_des_deux_documents_ne_disparait(self):
        v = monograph.values()
        for source in (paper.values(), paper2.values()):
            for cle in source:
                with self.subTest(cle=cle):
                    self.assertTrue(cle in v or f"{cle}_a2" in v)

    def test_les_tables_des_deux_documents_sont_toutes_atteignables(self):
        t = monograph.tables()
        self.assertEqual(len(t), 32 + 24)   # ALP-1 (report+lexicon+quant) et ALP-2

    def test_toutes_les_figures_coexistent(self):
        self.assertEqual(len(monograph.figures()), 31)


class TestPiedsDeFigure(unittest.TestCase):
    """La prose de pied sort du SVG et se rend sous la légende."""

    def test_une_phrase_de_pied_est_extraite(self):
        svg = ('<svg class="fig" viewBox="0 0 640 300">'
               '<text class="lg" x="320" y="292" text-anchor="middle">'
               'une phrase d explication assez longue pour ne pas etre une etiquette'
               '</text></svg>')
        propre, pieds = monograph.extraire_pieds(svg)
        self.assertEqual(len(pieds), 1)
        self.assertNotIn("une phrase", propre)

    def test_une_etiquette_courte_reste_dans_le_graphique(self):
        svg = '<svg class="fig" viewBox="0 0 640 300"><text class="lg" x="10" y="292">POC</text></svg>'
        propre, pieds = monograph.extraire_pieds(svg)
        self.assertEqual(pieds, [])
        self.assertIn("POC", propre)

    def test_une_etiquette_de_panneau_reste_dans_le_graphique(self):
        """La classe `sub` porte la structure de la figure, jamais un commentaire."""
        svg = ('<svg class="fig" viewBox="0 0 640 300"><text class="sub" x="10" y="292">'
               'un libelle de panneau assez long pour depasser le seuil de prose</text></svg>')
        propre, pieds = monograph.extraire_pieds(svg)
        self.assertEqual(pieds, [])
        self.assertIn("libelle de panneau", propre)

    def test_un_texte_haut_dans_le_cadre_reste_dans_le_graphique(self):
        svg = ('<svg class="fig" viewBox="0 0 640 300"><text class="lg" x="10" y="40">'
               'un commentaire pose en haut du cadre, donc pas un pied de figure</text></svg>')
        _, pieds = monograph.extraire_pieds(svg)
        self.assertEqual(pieds, [])

    def test_aucune_figure_du_document_ne_garde_de_prose_longue(self):
        for cle, svg in monograph.figures().items():
            propre, _ = monograph.extraire_pieds(svg)
            for m in re.finditer(r'<text class="([^"]*)"([^>]*)>(.*?)</text>',
                                 propre, re.S):
                classes = m.group(1).split()
                if "sub" in classes or not ({"lg", "ax"} & set(classes)):
                    continue
                texte = re.sub(r"<[^>]+>", "", m.group(3)).strip()
                y = re.search(r'y="(-?[\d.]+)"', m.group(2))
                if not y:
                    continue
                hauteur = monograph._hauteur(propre)
                if float(y.group(1)) >= hauteur - monograph._MARGE_PIED:
                    self.assertLessEqual(len(texte), monograph._LONGUEUR_PROSE,
                                         f"{cle} : {texte!r}")


class TestStructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = monograph.build()
        cls.corps = cls.html.split("</style>", 1)[1]

    def test_aucune_balise_non_resolue(self):
        self.assertEqual(re.findall(r"\{\{[^}]+\}\}", self.html), [])

    def test_cinq_parties(self):
        self.assertEqual(self.corps.count('<div class="part">'), 5)

    def test_trente_deux_sections_numerotees(self):
        ids = re.findall(r'<h2 id="([a-z0-9-]+)"', self.corps)
        self.assertEqual(len(ids), 32)
        self.assertEqual(len(set(ids)), 32)

    def test_le_sommaire_couvre_toutes_les_sections(self):
        ids = set(re.findall(r'<h2 id="([a-z0-9-]+)"', self.corps))
        ancres = set(re.findall(r'href="#([a-z0-9-]+)"', self.corps))
        self.assertEqual(ids - ancres, set(), "sections absentes du sommaire")
        self.assertEqual(ancres - ids, set(), "ancres mortes")

    def test_le_sommaire_est_dans_l_ordre_du_document(self):
        ordre_doc = re.findall(r'<h2 id="([a-z0-9-]+)"', self.corps)
        sommaire = self.corps.split('</nav>')[0]
        ordre_toc = re.findall(r'href="#([a-z0-9-]+)"', sommaire)
        self.assertEqual(ordre_toc, ordre_doc)

    def test_les_deux_documents_sont_presents(self):
        # un marqueur propre a chacun
        self.assertIn("théorème d&#x27;invariance".replace("&#x27;", "'"), self.corps)
        self.assertIn("bande de bruit", self.corps)

    def test_la_composition_est_au_fer_a_gauche(self):
        """La césure française n'étant pas garantie, la justification est écartée."""
        self.assertIn("text-align: left", self.html)
        self.assertIn("text-wrap: pretty", self.html)

    def test_les_trois_etats_de_theme_sont_definis(self):
        self.assertIn("prefers-color-scheme: dark", self.html)
        self.assertIn(':root:not([data-theme="light"])', self.html)
        self.assertIn(':root[data-theme="dark"]', self.html)

    def test_le_document_porte_son_avertissement(self):
        self.assertIn("ne constitue ni un conseil en investissement", self.corps)
        self.assertIn("Aucune mesure sur historique n&#x27;est conduite ici"
                      .replace("&#x27;", "'"), self.corps)

    def test_la_construction_est_deterministe(self):
        self.assertEqual(self.html, monograph.build())

    def test_figures_et_tables_numerotees_a_partir_de_un(self):
        figs = re.findall(r'<span class="lab">Figure (\d+)</span>', self.corps)
        self.assertEqual([int(n) for n in figs], list(range(1, len(figs) + 1)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
