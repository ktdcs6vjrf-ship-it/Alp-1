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
N_SECTIONS = 43
N_PARTIES = 12
N_TABLES = 16
N_FIGURES = 32


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


class TestParametresCentralises(unittest.TestCase):
    """Un paramètre cité par la prose vient du module, jamais du gabarit.

    C'est la règle 4 du dépôt appliquée aux paramètres et non aux seuls
    résultats. Un nombre qui gouverne un calcul et qu'on récrit à la main dans
    une phrase devient faux dès que le calcul change, et le désaccord ne se
    voit pas — ni à la lecture, ni à la construction.
    """

    #: Les constantes que la prose ou une légende cite en toutes lettres.
    CLES = ("SHARPE_CITE", "FENETRE_GLISSANTE", "BITS_ROC", "N_SESSIONS")

    @classmethod
    def setUpClass(cls) -> None:
        cls.gabarit = discpaper.TEMPLATE.read_text(encoding="utf-8")
        cls.corps = cls.gabarit.split("</style>", 1)[1]

    def test_aucun_parametre_ecrit_en_clair(self) -> None:
        """La recherche porte sur la prose entière, non sur le début d'un nœud.

        La première version ne cherchait que `>0,10` — la forme prise par un
        paramètre placé juste après une balise. Deux occurrences de `0,10`
        vivaient au milieu de phrases, hors de portée du contrôle : « pour
        prouver un Sharpe de 0,10 » et « de l'ordre de 0,10 par décision ».
        On balaie maintenant le texte débarrassé de ses balises, en ignorant
        ce qui vient des clés — puisque c'est précisément ce qu'on veut.
        """
        import re

        from alp1 import report10
        from alp1.report import num

        # Le gabarit sans ses balises ni ses clés : il ne reste que ce qu'un
        # rédacteur a tapé lui-même.
        prose = re.sub(r"<[^>]+>", " ", re.sub(r"\{\{[^}]*\}\}", " ", self.corps))
        for cle in self.CLES:
            valeur = getattr(report10, cle)
            # On cherche la forme exacte que `num` produirait : c'est celle
            # qu'un rédacteur recopierait.
            for nd in (0, 2, 3):
                litteral = num(valeur, nd)
                if len(litteral) < 3:
                    continue
                # Les bornes rejettent un chiffre voisin — pour ne pas
                # confondre « 0,10 » avec « 0,105 » — et rien d'autre : une
                # virgule de phrase suit très bien un nombre, et l'exclure
                # rendait le contrôle aveugle au cas même qu'il vise.
                #
                # La recherche est explicite et non `assertNotRegex` : celui-ci
                # déverse la botte de foin entière dans le message, soit
                # cinquante kilo-octets de gabarit pour une aiguille de quatre
                # caractères.
                motif = re.compile(r"(?<![\d.,])" + re.escape(litteral)
                                   + r"(?!\d)")
                trouve = motif.search(prose)
                if trouve is not None:
                    a = max(0, trouve.start() - 60)
                    autour = " ".join(prose[a:trouve.end() + 60].split())
                    self.fail(f"{cle} = {litteral} est écrit en clair dans le "
                              f"gabarit ; il doit venir de report10.values(). "
                              f"Contexte : …{autour}…")

    def test_les_cles_correspondantes_existent(self) -> None:
        """Les clés qui portent ces paramètres sont bien publiées.

        L'assertion porte sur un booléen et non sur l'appartenance à la
        chaîne : `assertIn` échouerait en déversant le gabarit entier dans le
        message, ce qui rend l'échec illisible pour un gabarit de cette
        taille.
        """
        vals = discpaper.values()
        for cle in ("d_sharpe_cite", "d_fenetre", "d_bits_roc", "d_seances"):
            self.assertIn(cle, vals, f"{cle} absente de values()")
            self.assertTrue("{{" + cle + "}}" in self.gabarit,
                            f"{cle} est calculée mais jamais citée "
                            f"par le gabarit")


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


class TestLesDeuxRoutesDuMur(unittest.TestCase):
    """Le bornage retiré, et les deux routes rendues comparables.

    Le budget de configurations était borné par `max(2.0, ...)`, ce qui
    fabriquait une taxe de sélection là où il n'y en a aucune. Le défaut
    portait trois affirmations du document — un levier à « +0,0000 », une
    géométrie à configuration unique créditée de 1 258 décisions de taxe, et
    une surface qui montait dès le premier levier. Ces tests le ferment.
    """

    def test_a_configuration_unique_la_taxe_est_nulle(self) -> None:
        """Rien à sélectionner, donc rien à déflater."""
        from alp1.costs import deflated_threshold_sharpe
        from alp1.report10 import _trades_for_threshold
        self.assertEqual(deflated_threshold_sharpe(1, 3000), 0.0)
        self.assertEqual(_trades_for_threshold(0.10, 1.0), 0.0)

    def test_le_premier_levier_fait_un_saut_depuis_zero(self) -> None:
        """La table des leviers affichait « +0,0000 » pour le premier.

        Le résumé disait déjà l'inverse de sa propre table : il annonce que
        le premier levier porte le seuil de zéro à sa valeur à deux
        configurations. C'est la table qui avait tort.
        """
        from alp1.report10 import table_levers
        premiere = table_levers().rows[0]
        seuil, ajout = premiere[3], premiere[4]
        self.assertEqual(ajout.lstrip("+"), seuil)
        self.assertNotIn("0,0000", ajout)

    def test_les_deux_routes_ont_la_meme_forme(self) -> None:
        """Toutes deux valent K/√N, et c'est la raison de leur accord.

        Le document cite les deux constantes ; la figure de l'échelle les
        trace. Si l'une des deux cessait d'être un simple K/√N, la figure et
        le texte diraient encore qu'elles se ressemblent sans que ce soit
        vrai.
        """
        import math
        from alp1.costs import significance_constant, trades_for_significance
        from alp1.report10 import _trades_for_threshold
        for sr in (0.05, 0.10, 0.15):
            k_test = significance_constant()
            self.assertAlmostEqual((k_test / sr) ** 2,
                                   float(trades_for_significance(sr, 1.0)),
                                   delta=1.0)
            k_taxe = math.sqrt(2.0 * math.log(16.0))
            self.assertAlmostEqual((k_taxe / sr) ** 2,
                                   _trades_for_threshold(sr, 16.0), places=6)

    def test_l_exigence_liante_est_le_maximum_des_deux(self) -> None:
        """Et à seize configurations, c'est le test ordinaire qui lie."""
        from alp1.costs import trades_for_significance
        from alp1.report10 import _trades_binding, _trades_for_threshold
        liant = _trades_binding(0.10, 16.0)
        self.assertEqual(liant, float(trades_for_significance(0.10, 1.0)))
        self.assertGreater(liant, _trades_for_threshold(0.10, 16.0))

    def test_la_taxe_ne_passe_devant_qu_au_dela_de_vingt_deux_essais(self) -> None:
        """Le seuil de bascule que le document cite, vérifié aux deux bords.

        C'est de lui que sort la phrase « les quatre leviers recensés ne
        coûtent rien de plus que ce qu'il faut de toute façon ».
        """
        from alp1.report10 import _trades_binding, _trades_for_threshold
        for budget in (2.0, 4.0, 8.0, 16.0, 22.0):
            self.assertGreater(_trades_binding(0.10, budget),
                               _trades_for_threshold(0.10, budget))
        self.assertEqual(_trades_binding(0.10, 64.0),
                         _trades_for_threshold(0.10, 64.0))


if __name__ == "__main__":
    unittest.main()
