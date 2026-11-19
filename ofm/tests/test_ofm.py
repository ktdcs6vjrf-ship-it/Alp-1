"""Ce que le document affirme, contrôlé contre sa source.

Lancer : `python -m unittest ofm.tests.test_stats ofm.tests.test_ofm` (≈ 1 min).
Le test de construction refait le document entier : c'est le seul qui
traverse vraiment le rendu (renvois, numérotation, balises, apostrophes).
"""

import math
import re
import unittest
from functools import lru_cache
from pathlib import Path

from ofm import (donnees, figures, offrir, papier, registre, revenir, stats, synthese)


@lru_cache(maxsize=1)
def document() -> str:
    return papier.build()


class TestDonnees(unittest.TestCase):
    def test_extraits_conformes_a_la_provenance(self):
        self.assertEqual(donnees.verifier(), [])

    def test_aucun_nom_utilisateur(self):
        # L'extraction retire les noms : un champ « username » ne doit pas survivre.
        self.assertFalse(any("username" in k for k in donnees.raop()[0]))
        self.assertFalse(any("giver" in k for k in donnees.raop()[0]))


class TestModelesPublies(unittest.TestCase):
    """Une forme fermée se contrôle contre une valeur publiée, sans exception."""

    def test_bgnbd_redonne_l_article(self):
        g = {}
        for x, tx, T in donnees.cdnow_echantillon():
            g[(x, tx, T)] = g.get((x, tx, T), 0) + 1
        f = lambda lp: -sum(n * revenir._ll_bgnbd([math.exp(u) for u in lp], *k)
                            for k, n in g.items())
        lp, _ = stats.nelder_mead(f, [math.log(.25), math.log(4), math.log(.8),
                                      math.log(2.5)], pas=.4, tol=1e-12)
        p = [math.exp(u) for u in lp]
        for v, pub in zip(p, (0.243, 4.414, 0.793, 2.426)):
            self.assertAlmostEqual(v, pub, delta=0.0015)

    def test_bgbb_redonne_l_article(self):
        for v, pub in zip(revenir.ajuster_dons(), (1.204, 0.750, 0.657, 2.783)):
            self.assertAlmostEqual(v, pub, delta=0.0015)

    def test_karlan_list_redonne_les_taux_publies(self):
        r = offrir.resultats()["O01"]
        self.assertAlmostEqual(r.extra["b"], 0.0179, delta=0.0002)
        self.assertAlmostEqual(r.extra["a"], 0.0220, delta=0.0002)

    def test_esperance_bgnbd_contre_simulation(self):
        # E[X(t)] de la cohorte contre un tirage du modèle génératif.
        p = revenir.ajuster()
        r, alpha, a, b = p
        alea = stats.rng("bgnbd-sim")
        t, n, tot = 39.0, 20000, 0
        for _ in range(n):
            lam = alea.gammavariate(r, 1 / alpha)
            pm = alea.betavariate(a, b)
            temps, vivant = 0.0, True
            while vivant:
                temps += alea.expovariate(lam) if lam > 0 else math.inf
                if temps > t:
                    break
                tot += 1
                vivant = alea.random() >= pm
        self.assertAlmostEqual(tot / n, revenir.esperance_naissance(p, t), delta=0.03)


class TestRegistre(unittest.TestCase):
    def test_identifiants_uniques_et_resultats_complets(self):
        ids = [h.id for h in registre.H]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(list(synthese.tous()), ids)
        self.assertEqual(len(ids), 59)

    def test_verdicts_calcules(self):
        q = synthese.q_valeurs()
        for i, r in synthese.tous().items():
            v = synthese.verdict(i)
            if q[i] >= synthese.SEUIL_Q:
                self.assertEqual(v, "non établi", i)
            else:
                self.assertIn(v, ("tient", "contraire"), i)

    def test_bh_est_monotone(self):
        res = synthese.tous()
        q = synthese.q_valeurs()
        ordre = sorted(res, key=lambda i: res[i].p)
        qs = [q[i] for i in ordre]
        self.assertEqual(qs, sorted(qs))

    def test_le_seul_contraire_est_le_silence(self):
        contraires = [i for i in synthese.tous() if synthese.verdict(i) == "contraire"]
        self.assertEqual(contraires, ["R02"])


class TestFigures(unittest.TestCase):
    def test_aucune_couleur_en_dur(self):
        src = Path(figures.__file__).read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"#[0-9a-fA-F]{6}\b", src))
        self.assertNotIn("&#", src)

    def test_libelles_aria_sans_apostrophe(self):
        for k, svg in figures.rendre().items():
            aria = re.search(r'aria-label="([^"]*)"', svg).group(1)
            self.assertNotIn("'", aria, k)
            self.assertNotIn("’", aria, k)

    def test_toutes_les_figures_sont_placees(self):
        gab = papier.TEMPLATE.read_text(encoding="utf-8")
        places = re.findall(r"\{\{FIGURE:([a-z0-9_]+)\|", gab)
        self.assertEqual(sorted(places), sorted(figures.FIGURES))
        self.assertEqual(len(places), len(set(places)))


class TestDocument(unittest.TestCase):
    def test_comptes(self):
        html = document()
        self.assertEqual(len(re.findall(r'<figure class="plate">', html)), len(figures.FIGURES))
        self.assertEqual(len(re.findall(r'<span class="lab">Table \d+</span>', html)),
                         len(papier.tables()))

    def test_aucune_balise_restante(self):
        self.assertIsNone(re.search(r"\{\{|\}\}", document()))

    def test_renvois_de_section(self):
        """Chaque « section N » pointe vers la N-ième section numérotée."""
        html = document()
        ids = re.findall(r'<h2 id="(s-[a-z0-9-]+)"(?! class="unnumbered")>', html)
        rang = {i: k + 1 for k, i in enumerate(ids)}
        for cible, n in re.findall(r'<a href="#(s-[a-z0-9-]+)">(\d+)</a>', html):
            self.assertEqual(rang.get(cible), int(n), cible)

    def test_sommaire_identique_au_corps(self):
        html = document()
        toc = html[html.index('<nav class="toc"'):html.index("</nav>")]
        liens = re.findall(r'<li><a href="#(s-[a-z0-9-]+)">', toc)
        ids = re.findall(r'<h2 id="(s-[a-z0-9-]+)"(?! class="unnumbered")>', html)
        self.assertEqual(liens, [i for i in ids if i != "s-conclusion"])
        for cible in re.findall(r'href="#([a-z0-9-]+)"', html):
            self.assertIn(f'id="{cible}"', html, cible)

    def test_pas_d_apostrophe_droite_dans_le_texte(self):
        html = document()
        corps = html[html.index("</style>"):]
        texte = re.sub(r"<[^>]+>", " ", corps)
        self.assertNotIn("'", texte)


if __name__ == "__main__":
    unittest.main()
