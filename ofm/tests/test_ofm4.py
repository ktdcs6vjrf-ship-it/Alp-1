"""Le cahier nº 4, contrôlé contre sa source.

Lancer : `python -m unittest ofm.tests.test_ofm4` (≈ 1 min avec `ofm/donnees/CALCUL4.json` à jour ; sinon le
calcul complet, une quinzaine de minutes, est refait).
"""

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from functools import lru_cache
from pathlib import Path

from ofm import (calcul4, clair4, donnees4, etalonnage4, figmobile4, formation4, litterature4, mobile4, stress,
                 synthese4)
from ofm import registre4 as R4


@lru_cache(maxsize=1)
def page() -> str:
    return mobile4.build()


class TestRegistre4(unittest.TestCase):
    def test_vingt_cinq_tests_uniques(self):
        ids = [h.id for h in R4.H]
        self.assertEqual(len(ids), 25)
        self.assertEqual(len(set(ids)), 25)
        self.assertEqual({h.famille for h in R4.H}, set(R4.FAMILLES))

    def test_la_batterie_ne_cite_que_des_tests_declares(self):
        noms = {t for t, _, _ in R4.TESTS}
        for fam, tests in R4.APPLICABLES.items():
            self.assertTrue(set(tests) <= noms, fam)
        for i, tests in R4.SANS_OBJET.items():
            self.assertIn(i, R4.par_id())
            self.assertTrue(set(tests) <= noms, i)

    def test_le_registre_ne_calcule_rien(self):
        texte = Path(R4.__file__).read_text(encoding="utf-8")
        for m in ("avances", "synthese4", "arene", "calcul4"):
            self.assertNotIn(f"import {m}", texte)


class TestStress(unittest.TestCase):
    def test_holm_sur_un_exemple(self):
        self.assertEqual(stress.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])

    def test_dsr_a_un_essai_est_le_sharpe_probabiliste(self):
        serie = [0.02, -0.01, 0.03, 0.01, 0.0, 0.02, -0.02, 0.04]
        d = stress.dsr(serie, 1)
        self.assertEqual(d["sr0"], 0.0)
        self.assertTrue(0.5 < d["dsr"] < 1.0)

    def test_hypercube_visite_chaque_tranche(self):
        pts = stress.hypercube({"a": (0.0, 1.0), "b": (0, 9)}, 10, "test")
        self.assertEqual(sorted(int(p["a"] * 10) for p in pts), list(range(10)))
        self.assertEqual(sorted(p["b"] for p in pts), list(range(10)))

    def test_cscv_sans_avance_proche_de_la_moitie(self):
        e = stress.etalonner_cscv(essais=20, K=6)
        self.assertTrue(0.3 < e["pbo"] < 0.7, e)

    def test_t3(self):
        self.assertTrue(stress.passe_t3(1.0, 1e-4, +1))
        self.assertFalse(stress.passe_t3(1.0, 0.01, +1))
        self.assertFalse(stress.passe_t3(-1.0, 1e-4, +1))


class TestDonnees4(unittest.TestCase):
    def test_extrait_conforme_a_la_provenance(self):
        self.assertEqual(donnees4.verifier(), [])

    def test_soixante_mille_impressions(self):
        rows = donnees4.obp()
        self.assertEqual(len(rows), 60_000)
        for pol in ("r", "b"):
            for c in R4.CAMPAGNES:
                self.assertEqual(sum(1 for r in rows if r["politique"] == pol and r["campagne"] == c), 10_000)


class TestCalcul4(unittest.TestCase):
    def test_le_fichier_suit_le_code(self):
        d = json.loads(calcul4.CIBLE.read_text(encoding="utf-8"))
        self.assertEqual(d["empreinte"], calcul4.empreinte(), "CALCUL4.json est périmé : python -m ofm.calcul4")

    def test_vingt_cinq_resultats(self):
        self.assertEqual(set(calcul4.charger()["resultats"]), {h.id for h in R4.H})


class TestSynthese4(unittest.TestCase):
    def test_verdicts_ecrits(self):
        calcules = {i: synthese4.verdict(i) for i in synthese4.tous()}
        self.assertEqual(calcules, clair4.VERDICTS_ECRITS, "un verdict a changé : réécrire le texte, pas le test")

    def test_survie_ecrite(self):
        calcules = {i: synthese4.bilan(i)["survit"] for i in synthese4.tous()}
        self.assertEqual(calcules, clair4.SURVIE_ECRITE, "la survie a changé : réécrire le texte")

    def test_chaque_bilan_a_ses_treize_tests(self):
        for i in synthese4.tous():
            b = synthese4.bilan(i)
            self.assertEqual(set(b["tests"]), {t for t, _, _ in R4.TESTS})
            self.assertTrue(all(v["etat"] in ("passe", "echoue", "sans objet") for v in b["tests"].values()))
            self.assertEqual(b["applicables"], len(R4.applicables(i)))

    def test_un_survivant_tient(self):
        for i in synthese4.survivants():
            self.assertEqual(synthese4.verdict(i), "tient")

    def test_un_sans_objet_n_est_jamais_compte_reussi(self):
        for i in synthese4.tous():
            b = synthese4.bilan(i)
            self.assertEqual(b["passes"], sum(1 for v in b["tests"].values() if v["etat"] == "passe"))


class TestClair4(unittest.TestCase):
    def test_chaque_hypothese_a_ses_trois_textes(self):
        self.assertEqual(set(clair4.CARTES), {h.id for h in R4.H})
        for i, t in clair4.CARTES.items():
            self.assertEqual(len(t), 3, i)
            self.assertTrue(all(len(x) > 20 for x in t), i)

    def test_chaque_test_et_chaque_graphique_sont_expliques(self):
        self.assertEqual(set(clair4.TESTS_CLAIR), {t for t, _, _ in R4.TESTS})
        self.assertEqual(set(clair4.GRAPHIQUES), set(figmobile4.FIGURES))

    def test_chaque_affirmation_de_l_arene(self):
        self.assertEqual(set(clair4.Z_CLAIR), {z for z, *_ in R4.Z})


class TestFormation4(unittest.TestCase):
    def test_les_preuves_existent_et_portent_le_verdict_ecrit(self):
        for p in formation4.PLAN:
            for i in p["preuves"]:
                self.assertIn(i, clair4.VERDICTS_ECRITS, p["id"])
            for r in p["refs"]:
                self.assertIn(r, litterature4.REFS, p["id"])

    def test_les_questions_ont_une_bonne_reponse(self):
        for _, l in formation4.lecons():
            q, choix, bon, pourquoi = l["quiz"]
            self.assertTrue(0 <= bon < len(choix), l["id"])
            self.assertTrue(pourquoi)

    def test_chaque_nombre_vient_de_la_page(self):
        vals = mobile4.valeurs()
        textes = []
        for p in formation4.PLAN:
            textes += [p["phrase"], p["pourquoi"], p["autres"], p["copie"], p["verifier"], *p["etapes"]]
        for _, l in formation4.lecons():
            textes += [l["lead"], l["kid"], *l["faits"], *l["faire"], *l["eviter"], l["quiz"][0], *l["quiz"][1]]
        for t in list(clair4.GRAPHIQUES.values()):
            textes += list(t)
        for t in textes:
            for cle in re.findall(r"\{\{([a-z0-9_]+)\}\}", t):
                self.assertIn(cle, vals, t[:60])


class TestEtalonnage4(unittest.TestCase):
    def test_le_fichier_est_la(self):
        e = etalonnage4.lire()
        self.assertLessEqual(e["holm"]["holm"], 0.06)
        self.assertLessEqual(e["a_nul"]["conclut"], 0.05)
        self.assertGreaterEqual(e["a_heterogene"]["couverture"], 0.9)

    def test_une_version_courte_redonne_l_ordre_de_grandeur(self):
        self.assertLessEqual(stress.etalonner_holm(400)["holm"], 0.08)


class TestPage4(unittest.TestCase):
    def test_aucune_balise_ni_entite(self):
        p = page()
        self.assertNotIn("{{", p)
        self.assertNotIn("&#x27;", p)
        self.assertNotIn("&#39;", p)

    def test_les_sections_suivent_les_groupes(self):
        ordre = re.findall(r'<section id="([a-z]+)">', page())
        self.assertEqual(ordre, [i for _, ids in mobile4.GROUPES for i in ids])

    def test_vingt_graphiques_au_moins_dont_cinq_en_3d(self):
        p = page()
        self.assertGreaterEqual(p.count('<figure class="viz">'), 20)
        self.assertGreaterEqual(p.count("vue 3D"), 5)

    def test_le_script_se_compile(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node absent")
        scripts = re.findall(r"<script>(.*?)</script>", page(), flags=re.S)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write("\n;\n".join(scripts))
        r = subprocess.run([node, "--check", f.name], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_la_sortie_pour_lueur(self):
        s = mobile4.sortie()
        self.assertEqual(s["cahier"], "ofm4")
        self.assertEqual(len(s["verdicts"]), 25)
        self.assertEqual(sum(s["survie"].values()), int(mobile4.valeurs()["n_survivent"]))


if __name__ == "__main__":
    unittest.main()
