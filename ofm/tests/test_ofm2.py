"""Le cahier nº 2, contrôlé contre sa source.

Lancer : `python -m unittest ofm.tests.test_ofm2` (≈ 2 min : la construction
refait les calculs de Lenta, 687 029 clients, en bibliothèque standard).
"""

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from functools import lru_cache
from pathlib import Path

from ofm import (cibler, clair2, donnees2, figmobile2, garder, litterature2, mobile2, objectif,
                 registre, registre2, relancer, stats, synthese, synthese2)


@lru_cache(maxsize=1)
def page() -> str:
    return mobile2.build()


class TestDonnees(unittest.TestCase):
    def test_extraits_conformes_a_la_provenance(self):
        self.assertEqual(donnees2.verifier(), [])

    def test_cinq_marches(self):
        self.assertEqual(sorted(donnees2.provenance()),
                         ["hillstrom", "kickstarter", "lenta", "retail", "x5"])

    def test_aucun_identifiant(self):
        # Ni numéro de client d'origine, ni nom de campagne, ni libellé de produit.
        self.assertNotIn("client_id", donnees2.x5()[0])
        self.assertNotIn("name", donnees2.kickstarter()[0])
        self.assertEqual(len(donnees2.retail()[0]), 6)

    def test_les_tirages_au_sort_sont_equilibres(self):
        # Le hasard doit se voir : bras de taille attendue, à quelques écarts-types près.
        hs = donnees2.hillstrom()
        for code in ("0", "h", "f"):
            n = sum(1 for r in hs if r["courriel"] == code)
            self.assertLess(abs(n - len(hs) / 3), 4 * (len(hs) * 2 / 9) ** 0.5, code)
        for lot, part in ((donnees2.lenta(), 0.75), (donnees2.x5(), 0.5)):
            n, t = len(lot), sum(r["t"] for r in lot)
            self.assertLess(abs(t - n * part), 4 * (n * part * (1 - part)) ** 0.5)


class TestRegistre(unittest.TestCase):
    def test_famille_propre(self):
        # Le registre nº 2 a sa propre correction : il ne touche pas aux verdicts du nº 1.
        self.assertEqual(len(registre2.H), 38)
        self.assertEqual(len(synthese.tous()), 59)
        self.assertFalse(set(registre2.par_id()) & set(registre.par_id()))

    def test_identifiants_uniques_et_resultats_complets(self):
        ids = [h.id for h in registre2.H]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(list(synthese2.tous()), ids)

    def test_verdicts_calcules(self):
        q = synthese2.q_valeurs()
        for i, r in synthese2.tous().items():
            v = synthese2.verdict(i)
            if q[i] >= synthese2.SEUIL_Q:
                self.assertEqual(v, "non établi", i)
            else:
                self.assertIn(v, ("tient", "contraire"), i)

    def test_bh_sur_trente_huit(self):
        res = synthese2.tous()
        attendu = stats.bh([max(r.p, 1e-300) for r in res.values()])
        self.assertEqual(list(synthese2.q_valeurs().values()), attendu)

    def test_les_contraires(self):
        self.assertEqual([i for i in synthese2.tous() if synthese2.verdict(i) == "contraire"], ["C08", "G03"])
        self.assertIn("Les données disent l", synthese2.en_agence("C08"))


class TestMethodes(unittest.TestCase):
    def test_ecart_de_tiers_contre_bootstrap(self):
        # La fonction d'influence du ciblage doit redonner l'écart-type d'un rééchantillonnage.
        c = cibler.coupe("hillstrom")
        t, y = c["t"], c["y"]
        mu, mr = cibler._top(c["effet"], 1 / 3), cibler._top(c["risque"], 1 / 3)
        d, iu, _, _ = cibler._tau(t, y, mu)
        d2, ir, _, _ = cibler._tau(t, y, mr)
        se = sum((a - b) ** 2 for a, b in zip(iu, ir)) ** 0.5
        alea = stats.rng("bootstrap-tiers")
        n, tirs = len(t), []
        for _ in range(150):
            idx = [alea.randrange(n) for _ in range(n)]
            tt, yy = [t[i] for i in idx], [y[i] for i in idx]
            a = cibler._tau(tt, yy, [mu[i] for i in idx])[0] - cibler._tau(tt, yy, [mr[i] for i in idx])[0]
            tirs.append(a)
        sd = stats.variance(tirs) ** 0.5
        self.assertLess(abs(se / sd - 1), 0.25)

    def test_entassement_lu_sur_des_comptes_exacts(self):
        # Une campagne à 100 % pile n'appartient pas à la tranche d'en dessous.
        h = dict((round(a, 2), n) for a, n in objectif.histogramme(0.9, 1.1, 0.02))
        e = objectif.entassement()
        self.assertEqual(h[0.98] + h[0.96], objectif._compte(0.96, 1.00))
        self.assertGreater(h[1.0], 100 * h[0.98])
        self.assertLess(e["ib"], e["ia"] / 100)

    def test_bgnbd_reutilise_la_vraisemblance_du_nº1(self):
        p = garder.ajuster()
        self.assertTrue(all(v > 0 for v in p))
        # La prévision du modèle et le rythme passé prédisent des ordres de grandeur voisins.
        pr = garder.predictions()
        self.assertLess(abs(sum(b for _, b, _ in pr) / sum(n for _, _, n in pr) - 1), 0.2)

    def test_budget_de_la_depense(self):
        a, d = relancer.budgets_hillstrom()
        self.assertGreater(d, a)


class TestMobile(unittest.TestCase):
    def test_aucune_couleur_en_dur(self):
        for mod in (figmobile2, mobile2, clair2):
            src = Path(mod.__file__).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"#[0-9a-fA-F]{6}\b", src), mod.__name__)

    def test_libelles_aria_sans_apostrophe(self):
        for k, svg in figmobile2.rendre().items():
            aria = re.search(r'aria-label="([^"]*)"', svg).group(1)
            self.assertNotIn("'", aria, k)
            self.assertNotIn("’", aria, k)

    def test_aucune_balise_restante(self):
        self.assertIsNone(re.search(r"\{\{|\}\}", page()))

    def test_valeurs_au_toucher_typographiees(self):
        for tip in re.findall(r'data-tip="([^"]*)"', page()):
            self.assertNotIn("'", tip)

    def test_l_espace_mene_a_chaque_section(self):
        html = page()
        nav = html[html.index('<nav class="sujets"'):]
        nav = nav[:nav.index("</nav>")]
        tuiles = re.findall(r'<a class="tuile" href="#([a-z]+)"', nav)
        sections = re.findall(r'<section id="([a-z]+)">', html)
        self.assertEqual(tuiles, sections)
        self.assertEqual([i for _, ids in mobile2.GROUPES for i in ids], sections)
        for s in sections:
            corps = html[html.index(f'<section id="{s}">'):]
            corps = corps[:corps.index("</section>")]
            self.assertEqual(corps.count('<nav class="fin"'), 1, s)
        for cible in re.findall(r'href="#([a-z0-9-]+)"', html):
            self.assertIn(f'id="{cible}"', html, cible)

    def test_les_tuiles_comptent_comme_le_registre(self):
        html = page()
        vus = 0
        for tuile in re.findall(r'<a class="tuile".*?</a>', html, flags=re.S):
            m = re.search(r'<span class="t-v" data-ok="(\d+)" data-ko="(\d+)" data-nul="(\d+)"', tuile)
            if not m:
                continue
            s = re.search(r'href="#([a-z]+)"', tuile).group(1)
            corps = html[html.index(f'<section id="{s}">'):]
            corps = corps[:corps.index("</section>")]
            # Une carte pleine porte `res-id`, une ligne « non établi » `nul-id`.
            ids = sorted(set(re.findall(r'<span class="(?:res|nul)-id">([A-Z]\d\d)</span>', corps)))
            v = [synthese2.verdict(i) for i in ids]
            self.assertEqual(tuple(int(x) for x in m.groups()),
                             (v.count("tient"), v.count("contraire"), v.count("non établi")), s)
            vus += 1
        self.assertEqual(vus, 6)

    def test_texte_sans_apostrophe_droite_hors_script(self):
        html = re.sub(r"<script>.*?</script>|<style>.*?</style>", " ", page(), flags=re.S)
        texte = re.sub(r"<[^>]+>", " ", html)
        self.assertNotIn("'", texte)
        self.assertNotIn("&#x27;", texte)
        self.assertNotIn("&#39;", texte)

    def test_le_script_reste_du_javascript_et_range_a_part(self):
        scripts = re.findall(r"<script>(.*?)</script>", page(), flags=re.S)
        self.assertEqual(len(scripts), 2)
        # Le thème est partagé avec le nº 1 ; la lecture et la reprise ne le sont pas.
        self.assertIn("localStorage.getItem('ofm-cahier-theme')", scripts[0])
        self.assertIn("'ofm-cahier2-lus'", scripts[1])
        self.assertNotIn("'ofm-cahier-lus'", scripts[1])
        node = shutil.which("node")
        if node is None:
            self.skipTest("node absent")
        for script in scripts:
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
                f.write(script)
            r = subprocess.run([node, "--check", f.name], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_chaque_figure_est_placee_et_expliquee(self):
        gabarit = mobile2.TEMPLATE.read_text(encoding="utf-8")
        places = re.findall(r"\{\{FIG:([a-z0-9_]+)\|", gabarit)
        self.assertEqual(sorted(places), sorted(figmobile2.FIGURES))
        self.assertEqual(sorted(clair2.GRAPHIQUES), sorted(figmobile2.FIGURES))
        self.assertEqual(page().count('<div class="lire">'), len(figmobile2.FIGURES))

    def test_la_sortie_pour_lueur(self):
        s = mobile2.sortie()
        self.assertEqual(s["cahier"], "ofm2")
        self.assertEqual(set(s["verdicts"]), set(registre2.par_id()))
        self.assertTrue(all(v in ("tient", "contraire", "non établi") for v in s["verdicts"].values()))
        json.dumps(s, ensure_ascii=False)


class TestClair(unittest.TestCase):
    def test_les_verdicts_sont_ceux_sous_lesquels_on_a_ecrit(self):
        for i in synthese2.tous():
            self.assertEqual(synthese2.verdict(i), clair2.VERDICTS_ECRITS[i],
                             f"{i} : le verdict a changé, réécrire son texte (clair2.CARTES)")

    def test_chaque_hypothese_a_ses_trois_explications(self):
        self.assertEqual(sorted(clair2.CARTES), sorted(registre2.par_id()))
        for i, t in clair2.CARTES.items():
            self.assertEqual(len(t), 3, i)
            self.assertTrue(all(len(x) > 20 for x in t), i)
            # Aucun nombre calculé dans une carte ; les noms propres (X5, cahier nº 1) restent.
            texte = re.sub(r"X5|nº\s?\d", "", t[0] + t[1])
            self.assertIsNone(re.search(r"\d", texte), f"{i} : une carte ne porte aucun nombre")

    def test_toutes_les_sections_ont_leur_etude(self):
        gabarit = mobile2.TEMPLATE.read_text(encoding="utf-8")
        self.assertEqual(sorted(re.findall(r"\{\{ETUDE:([a-z]+)\}\}", gabarit)), sorted(clair2.ETUDES))

    def test_ailleurs_cite_des_references_connues(self):
        for e in litterature2.AILLEURS:
            self.assertIn(e["ref"], litterature2.REFS)


if __name__ == "__main__":
    unittest.main()
