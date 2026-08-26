"""La structure du document sur l'edge discrétionnaire.

Les comptes annoncés sont gardés ici. Changer le gabarit impose de changer
ces nombres, et c'est voulu : un document dont on modifie la structure sans
s'en apercevoir est un document dont on ne sait plus ce qu'il contient.
"""

from __future__ import annotations

import re
import unittest

from alp1 import discpaper

#: Ce que le gabarit déclare. Toute modification de structure passe par ici.
N_SECTIONS = 34
N_PARTIES = 10
N_TABLES = 8
N_FIGURES = 14


class TestConstruction(unittest.TestCase):
    """Le document se construit, et il se construit à l'identique."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.html = discpaper.build()
        cls.corps = cls.html.split("</style>", 1)[1]

    def test_aucune_balise_non_resolue(self) -> None:
        """Une clé mal orthographiée afficherait sa balise en clair au milieu
        d'une phrase. Le garde-fou du module lève ; ce test le confirme."""
        self.assertEqual(re.findall(r"\{\{[^}]+\}\}", self.html), [])

    def test_build_deterministe(self) -> None:
        self.assertEqual(discpaper.build(), self.html)

    def test_aucune_couleur_en_dur(self) -> None:
        """Les figures passent par les jetons CSS, jamais par une couleur
        littérale — c'est ce qui les rend lisibles sur les deux fonds."""
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{6}", self.corps), [])


class TestComptes(unittest.TestCase):
    """Les comptes du gabarit sont ceux que le document rend."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.corps = discpaper.build().split("</style>", 1)[1]

    def test_nombre_de_sections(self) -> None:
        ids = re.findall(r'<h2 id="[a-z0-9-]+"', self.corps)
        self.assertEqual(len(ids), N_SECTIONS)

    def test_nombre_de_parties(self) -> None:
        self.assertEqual(self.corps.count('<div class="part">'), N_PARTIES)

    def test_nombre_de_tables(self) -> None:
        self.assertEqual(len(discpaper.tables()), N_TABLES)
        self.assertEqual(len(re.findall(r"Table \d+", self.corps)), N_TABLES)

    def test_nombre_de_figures(self) -> None:
        self.assertEqual(len(discpaper.figures()), N_FIGURES)
        self.assertEqual(len(re.findall(r"Figure \d+", self.corps)), N_FIGURES)

    def test_tables_numerotees_sans_trou(self) -> None:
        nums = [int(n) for n in re.findall(r"Table (\d+)", self.corps)]
        self.assertEqual(nums, list(range(1, N_TABLES + 1)))

    def test_figures_numerotees_sans_trou(self) -> None:
        nums = [int(n) for n in re.findall(r"Figure (\d+)", self.corps)]
        self.assertEqual(nums, list(range(1, N_FIGURES + 1)))


class TestSommaire(unittest.TestCase):
    """Le sommaire dit exactement ce que le document contient."""

    @classmethod
    def setUpClass(cls) -> None:
        html = discpaper.build()
        cls.corps = html.split("</style>", 1)[1]
        cls.bloc = html.split('nav class="toc"', 1)[1].split("</nav>", 1)[0]
        cls.ids = re.findall(r'<h2 id="([a-z0-9-]+)"', cls.corps)
        cls.ancres = re.findall(r'<a href="#(s-[a-z0-9-]+)"', cls.bloc)

    def test_aucune_section_hors_sommaire(self) -> None:
        self.assertEqual(sorted(set(self.ids) - set(self.ancres)), [])

    def test_aucune_ancre_morte(self) -> None:
        self.assertEqual(sorted(set(self.ancres) - set(self.ids)), [])

    def test_ordre_identique(self) -> None:
        """Le sommaire suit l'ordre du document. Sans ce contrôle, une section
        déplacée laisserait un sommaire qui ment sans que rien ne l'indique."""
        self.assertEqual(self.ids, self.ancres)

    def test_les_start_suivent_la_numerotation(self) -> None:
        """Les `start=` des sous-listes doivent correspondre au rang réel de
        la première section de chaque partie, sinon le sommaire affiche des
        numéros faux."""
        starts = [int(s) for s in re.findall(r'<ol start="(\d+)"', self.bloc)]
        rangs, vu = [], 0
        for bloc in self.bloc.split("<li><span class=\"pt\">")[2:]:
            premiere = re.search(r'<a href="#(s-[a-z0-9-]+)"', bloc)
            self.assertIsNotNone(premiere)
            rangs.append(self.ids.index(premiere.group(1)) + 1)
            vu += 1
        self.assertEqual(starts, rangs)


class TestRenvois(unittest.TestCase):
    """Un renvoi qui cite un rang doit citer le bon.

    C'est la garde qui manque le plus souvent : insérer une section décale
    toute la numérotation, les `start=` du sommaire sont corrigés parce qu'ils
    sautent aux yeux, et les renvois en toutes lettres au fil du texte restent
    faux sans que rien ne le signale.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.corps = discpaper.build().split("</style>", 1)[1]
        cls.rangs = {i: n for n, i in enumerate(
            re.findall(r'<h2 id="([a-z0-9-]+)"', cls.corps), start=1)}

    def test_les_renvois_citent_le_bon_rang(self) -> None:
        renvois = re.findall(r'<a href="#(s-[a-z0-9-]+)">(\d+)</a>', self.corps)
        self.assertTrue(renvois, "aucun renvoi numéroté à vérifier")
        for ancre, cite in renvois:
            self.assertIn(ancre, self.rangs, f"ancre morte : {ancre}")
            self.assertEqual(int(cite), self.rangs[ancre],
                             f"le renvoi vers {ancre} annonce {cite}, "
                             f"or la section est la {self.rangs[ancre]}e")


class TestTypographie(unittest.TestCase):
    """La passe typographique française, et ce qu'elle doit épargner."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.html = discpaper.build()
        cls.corps = cls.html.split("</style>", 1)[1]
        cls.style = cls.html.split("<style>", 1)[1].split("</style>", 1)[0]

    def test_aucune_apostrophe_droite(self) -> None:
        """L'apostrophe française est courbe. La droite est une servitude de
        clavier, pas une convention typographique."""
        self.assertEqual(self.corps.count("'"), 0)
        self.assertGreater(self.corps.count("\u2019"), 100)

    def test_le_bloc_de_style_est_epargne(self) -> None:
        """Le style porte des noms de police entre apostrophes ; les courber
        casserait la déclaration."""
        self.assertIn('"Source Serif 4"', self.style)
        self.assertEqual(self.style.count("\u2019"), 0)

    def test_les_attributs_sont_epargnes(self) -> None:
        """Une apostrophe courbe dans un href ou une classe casserait le lien
        ou la règle. La passe ne visite jamais l'intérieur d'une balise."""
        import re
        for balise in re.findall(r"<[^>]+>", self.corps):
            self.assertNotIn("\u2019", balise, balise[:80])

    def test_ponctuation_double_insecable(self) -> None:
        """Aucun deux-points ne doit rester collé à un mot."""
        import re
        colles = re.findall(r"\w:(?:\s|<)", self.corps)
        self.assertEqual(colles, [])

    def test_les_entites_html_survivent(self) -> None:
        """Le point-virgule d'une entité ne prend pas l'espace insécable.

        `&nbsp;` coupée par une espace cesse d'être une entité : le navigateur
        affiche la suite telle quelle, et le document porte des « ; »
        parasites au milieu du texte.
        """
        import re
        cassees = re.findall(r"&[a-zA-Z#0-9]{2,8}[\u202f\u00a0];", self.html)
        self.assertEqual(cassees, [])
        self.assertIn("&nbsp;", self.html)

    def test_les_url_survivent(self) -> None:
        self.assertIn("https://", self.html)


class TestValeurs(unittest.TestCase):
    """Les scalaires cités existent et sont formatés à la française."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.vals = discpaper.values()

    def test_toutes_les_valeurs_sont_des_chaines(self) -> None:
        for k, v in self.vals.items():
            self.assertIsInstance(v, str, k)
            self.assertTrue(v, f"valeur vide : {k}")

    def test_virgule_decimale(self) -> None:
        """Le formatage passe par `report.num` : virgule décimale, espace fine
        insécable, vrai signe moins. Un point décimal signalerait un nombre
        écrit à la main."""
        suspects = [k for k, v in self.vals.items() if re.search(r"\d\.\d", v)]
        self.assertEqual(suspects, [])

    def test_le_mur_est_coherent_entre_les_sharpes(self) -> None:
        """Un Sharpe plus élevé exige moins de décisions. Le contrôle est
        trivial, et c'est pour cela qu'il attrape une inversion de signe."""
        def n(cle: str) -> float:
            return float(self.vals[cle].replace(" ", "").replace(",", "."))
        self.assertGreater(n("d_mur_sr05"), n("d_mur_sr10"))
        self.assertGreater(n("d_mur_sr10"), n("d_mur_sr15"))


if __name__ == "__main__":
    unittest.main()
