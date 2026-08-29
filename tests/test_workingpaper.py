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
        # ALP-1 (report+lexicon+quant), ALP-2, les deux corrections, et le
        # protocole à horizon borné
        # ALP-1, ALP-2, décote/exposant, horizon borné, instruments, les
        # bornes venues d'ailleurs, ce que le dehors offre, puis la géométrie
        # réellement pratiquée
        # … les quatre tables de la stratégie recomposée, et les deux de
        # l'audit de l'hypothèse d'edge
        self.assertEqual(len(t), 32 + 24 + 5 + 8 + 2 + 7 + 15 + 10 + 4 + 2)

    def test_toutes_les_figures_coexistent(self):
        self.assertEqual(len(monograph.figures()), 50)


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

    def test_une_ligne_qui_continue_garde_sa_virgule(self):
        """Une virgule finale annonce une suite : la ponctuer coupe la phrase.

        Le raccord posait un point à chaque ligne dépourvue de ponctuation
        finale, virgule comprise. Le pied de la grille de Fibonacci se lisait
        « … au-delà du seuil. les signaux manqués sont ceux qui partaient. »
        """
        recompose = monograph.joindre_pieds(
            ["première ligne", "deuxième ligne, qui continue,", "et sa suite"])
        self.assertEqual(
            recompose,
            "première ligne. deuxième ligne, qui continue, et sa suite.")

    def test_une_virgule_finale_sur_la_derniere_ligne_devient_un_point(self):
        """Rien ne suit : la virgule n'annonce plus rien."""
        self.assertEqual(monograph.joindre_pieds(["une ligne seule,"]),
                         "une ligne seule.")

    def test_une_ligne_courte_marquee_cap_est_extraite(self):
        """La marque prime sur la longueur.

        Une phrase de pied peut finir sur une ligne courte. Le critère de
        longueur, appliqué ligne à ligne, la laissait dans le SVG et coupait
        la phrase en deux — moitié sous la figure, moitié dedans. La classe
        `cap`, posée par `Board.caption`, déclare l'intention.
        """
        svg = ('<svg class="fig" viewBox="0 0 640 300">'
               '<text class="lg cap" x="320" y="292">et la fin, courte</text>'
               '</svg>')
        propre, pieds = monograph.extraire_pieds(svg)
        self.assertEqual(pieds, ["et la fin, courte"])
        self.assertNotIn("et la fin", propre)

    def test_une_annotation_courte_reste_dans_le_graphique(self):
        """Sans la marque, une ligne courte de la bande basse reste en place.

        C'est ce qui distingue une annotation — posée dans la figure parce
        qu'elle commente un tracé précis — d'une ligne de pied.
        """
        svg = ('<svg class="fig" viewBox="0 0 640 300">'
               '<text class="lg" x="320" y="292">trois courbes</text></svg>')
        propre, pieds = monograph.extraire_pieds(svg)
        self.assertEqual(pieds, [])
        self.assertIn("trois courbes", propre)

    def test_une_annotation_longue_marquee_keep_reste_dans_le_graphique(self):
        """La marque `keep` prime sur le secours de longueur.

        Le défaut a coûté deux annotations : posées dans la bande basse et
        plus longues que le seuil de prose, elles étaient sorties du SVG et
        reparaissaient dans la note du document, où elles ne commentaient
        plus rien. `Board.annotation` pose la marque ; ce test la garde.
        """
        svg = ('<svg class="fig" viewBox="0 0 640 300">'
               '<text class="lg keep" x="10" y="292">'
               'la frontiere recule vers les fortes derives quand le stop se resserre'
               '</text></svg>')
        propre, pieds = monograph.extraire_pieds(svg)
        self.assertEqual(pieds, [])
        self.assertIn("la frontiere recule", propre)

    def test_toute_annotation_du_depot_porte_la_marque_keep(self):
        """Le contrôle de bout en bout : aucune annotation ne se perd.

        Le test précédent garde la règle ; celui-ci garde son application.
        Une figure qui poserait sa prose sans passer par `Board.annotation`
        la verrait disparaître au premier build.
        """
        from alp1.figterm import Board
        b = Board(640, 300)
        b.annotation(10, 292, "une phrase assez longue pour depasser le seuil "
                              "de prose et tomber dans la bande basse")
        propre, pieds = monograph.extraire_pieds(b.render("essai"))
        self.assertEqual(pieds, [])
        self.assertIn("une phrase assez longue", propre)

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

    def test_les_parties_sont_toutes_ouvertes(self):
        self.assertEqual(self.corps.count('<div class="part">'), 9)

    def test_les_sections_sont_numerotees_en_continu(self):
        ids = re.findall(r'<h2 id="([a-z0-9-]+)"', self.corps)
        self.assertEqual(len(ids), 50)
        self.assertEqual(len(set(ids)), 50)

    def test_le_sommaire_couvre_toutes_les_sections(self):
        ids = set(re.findall(r'<h2 id="([a-z0-9-]+)"', self.corps))
        ancres = set(re.findall(r'href="#([a-z0-9-]+)"', self.corps))
        self.assertEqual(ids - ancres, set(), "sections absentes du sommaire")
        self.assertEqual(ancres - ids, set(), "ancres mortes")

    def test_les_renvois_citent_le_bon_numero_de_section(self):
        """Un renvoi « section 9 » doit pointer vers la neuvième section.

        Le numéro affiché dans le corps vient d'un compteur CSS ; celui écrit
        dans le texte est à la main. Rien n'empêche les deux de diverger, sinon
        ce test — et l'insertion d'une section les fait diverger en silence.
        """
        ids = re.findall(r'<h2 id="([a-z0-9-]+)"', self.corps)
        numero = {cle: i for i, cle in enumerate(ids, 1)}
        for cle, cite in re.findall(r'href="#([a-z0-9-]+)">(\d+)<', self.corps):
            with self.subTest(section=cle):
                self.assertEqual(int(cite), numero[cle])

    def test_le_sommaire_numerote_comme_le_corps(self):
        """Les `start` du sommaire suivent la numérotation réelle."""
        ids = re.findall(r'<h2 id="([a-z0-9-]+)"', self.corps)
        numero = {cle: i for i, cle in enumerate(ids, 1)}
        sommaire = self.corps.split('</nav>')[0]
        courant = 1
        for start, ancre in re.findall(
                r'<ol start="(\d+)">|<li><a href="#([a-z0-9-]+)"', sommaire):
            if start:
                courant = int(start)
                continue
            with self.subTest(section=ancre):
                self.assertEqual(numero[ancre], courant)
            courant += 1

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

    def test_aucune_note_ne_publie_sa_marque_de_gras(self):
        """Les astérisques et les apostrophes inverses se rendent, ne s'écrivent pas.

        Vingt-six notes de ce document publiaient leurs `**` et huit leurs
        apostrophes inverses comme des caractères. Le code était juste — la
        chaîne y porte bien la marque — et la page, fausse. C'est la règle du
        dépôt : une note se regarde.
        """
        for note in re.findall(r'<p class="note">(.*?)</p>', self.corps, re.S):
            self.assertNotIn("**", note)
            self.assertNotIn("`", note)

    def test_aucune_cellule_ne_publie_sa_marque_de_gras(self):
        for cellule in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", self.corps, re.S):
            self.assertNotIn("**", cellule)
            self.assertNotIn("`", cellule)

    def test_figures_et_tables_numerotees_a_partir_de_un(self):
        figs = re.findall(r'<span class="lab">Figure (\d+)</span>', self.corps)
        self.assertEqual([int(n) for n in figs], list(range(1, len(figs) + 1)))


class TestCeQueLExposantDecide(unittest.TestCase):
    """Trois affirmations que le document faisait et que le calcul refusait.

    Une figure titrée « ce que l'exposant décide » traçait la probabilité
    d'atteindre le target selon l'exposant d'échelle. Cette probabilité ne
    dépend pas de l'exposant : elle vaut la géométrie et rien d'autre. Deux
    tables publiaient la même colonne constante, et l'une d'elles concluait
    « la probabilité passe de 3,23 % à 3,23 %, soit une division par 1,0 ».
    """

    def test_la_probabilite_de_barriere_ne_depend_pas_de_l_exposant(self) -> None:
        """C'est le théorème d'arrêt optionnel, et il vaut exactement.

        Si ce test tombait, c'est que `outcome_scaled` aurait cessé de traiter
        l'exposant comme un changement de temps — et alors les figures qui
        s'appuient sur l'invariance devraient être relues.
        """
        from alp1.figterm import SESSION_MIN, SIGMA_1MIN, STOP_PTS
        from alp1.horizon import outcome_scaled
        ref = outcome_scaled(STOP_PTS, 20 * STOP_PTS, SESSION_MIN, SIGMA_1MIN, 0.5)
        for h in (0.52, 0.57, 0.60, 0.6489, 0.70):
            o = outcome_scaled(STOP_PTS, 20 * STOP_PTS, SESSION_MIN, SIGMA_1MIN, h)
            self.assertAlmostEqual(o.p_target, ref.p_target, places=4)
            self.assertAlmostEqual(o.p_target, 1.0 / 21.0, places=4)

    def test_l_exposant_decide_le_temps_donc_le_seuil(self) -> None:
        """Ce que la figure porte maintenant, et qui varie bien.

        Le temps d'exposition tombe de moitié entre H = ½ et H = 0,70, donc le
        seuil de rentabilité double. C'est la seule chaîne causale que le gamma
        ouvre, et la seule que la figure a le droit d'afficher.
        """
        from alp1.figterm import SESSION_MIN, SIGMA_1MIN, STOP_PTS
        from alp1.horizon import outcome_scaled
        bas = outcome_scaled(STOP_PTS, 20 * STOP_PTS, SESSION_MIN, SIGMA_1MIN, 0.50)
        haut = outcome_scaled(STOP_PTS, 20 * STOP_PTS, SESSION_MIN, SIGMA_1MIN, 0.70)
        self.assertLess(haut.expected_time, bas.expected_time)
        self.assertGreater(bas.expected_time / haut.expected_time, 2.0)

    def test_les_deux_faisceaux_de_monte_carlo_se_separent(self) -> None:
        """La légende annonçait un recouvrement « pendant toute l'année ».

        Ils se séparent bien avant la fin, et c'est mécanique : la dérive de
        référence est supposée à deux fois le seuil de rentabilité. Le test
        garde le fait, pas le chiffre — celui-ci est cité par une valeur.
        """
        from alp1.quant import MC_TRADES, _mc_separation
        self.assertLess(_mc_separation(), MC_TRADES)
        self.assertGreater(_mc_separation(), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
