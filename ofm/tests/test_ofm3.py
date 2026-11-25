"""Le cahier nº 3, contrôlé contre sa source.

Lancer : `python -m unittest ofm.tests.test_ofm3` (≈ 3 min : la construction
refait les 31 tests, leurs lois nulles, sept coupes par marché et les essais
de vérité connue, en bibliothèque standard).
"""

import json
import re
import shutil
import subprocess
import tempfile
import unittest
import zlib
from functools import lru_cache
from pathlib import Path

from ofm import (clair3, donnees, donnees3, figmobile3, leviers, litterature3, mobile3,
                 registre2, registre3, signaux, stats, synthese3)


@lru_cache(maxsize=1)
def page() -> str:
    return mobile3.build()


class TestDonnees(unittest.TestCase):
    def test_extraits_conformes_a_la_provenance(self):
        self.assertEqual(donnees3.verifier(), [])

    def test_l_echantillon_de_x5_suit_sa_regle(self):
        # 16 113 clients sur un peu plus de 400 000 : environ un sur vingt-cinq, par empreinte.
        n = len({r[0] for r in donnees3.x5_achats()})
        self.assertTrue(14_000 < n < 18_000, n)

    def test_aucun_identifiant(self):
        for nom in ("x5_achats.csv.gz", "thornton.csv.gz", "rondeau.csv.gz", "cai.csv.gz"):
            with open(donnees.DOSSIER / nom, "rb") as f:
                brut = f.read()
            self.assertIsNone(re.search(rb"[0-9a-f]{10}", zlib.decompress(brut, 16 + zlib.MAX_WBITS)), nom)

    def test_les_tirages_au_sort_sont_complets(self):
        bras = {}
        for b, _ in donnees3.rondeau():
            bras[b] = bras.get(b, 0) + 1
        self.assertEqual(sorted(bras), ["doublement", "premier_don", "temoin_bas", "temoin_haut"])
        self.assertTrue(all(740 <= n <= 750 for n in bras.values()), bras)
        # Le format de Cai et al. est tiré par hameau : aucun hameau ne mélange les deux.
        par_hameau = {}
        for r in donnees3.cai():
            par_hameau.setdefault(r["hameau"], set()).add(r["defaut_oui"])
        self.assertTrue(all(len(v) == 1 for v in par_hameau.values()))


class TestRegistre(unittest.TestCase):
    def test_famille_propre(self):
        # Un identifiant se lit avec son cahier : S01 du nº 1 (speed dating) n'est pas S01 du nº 3
        # (signaux). Ceux du nº 3 ont été commités avant le calcul ; on ne les renomme pas, on le dit.
        self.assertEqual({h.famille for h in registre3.H}, {"S", "L"})
        self.assertFalse({h.id for h in registre3.H} & {h.id for h in registre2.H})
        self.assertEqual(mobile3.sortie()["cahier"], "ofm3")
        self.assertEqual(len(registre3.H), 31)

    def test_identifiants_uniques_et_resultats_complets(self):
        ids = [h.id for h in registre3.H]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(list(synthese3.tous()), ids)

    def test_verdicts_calcules(self):
        c = synthese3.comptes()
        self.assertEqual(c["total"], 31)
        self.assertEqual(c["tient"] + c["contraire"] + c["non"], 31)
        for i in synthese3.tous():
            self.assertIn(synthese3.verdict(i), ("tient", "contraire", "non établi"))

    def test_bh_sur_trente_et_un(self):
        q = synthese3.q_valeurs()
        self.assertEqual(len(q), 31)
        self.assertTrue(all(0 <= v <= 1 for v in q.values()))

    def test_les_contraires(self):
        contraires = [i for i in synthese3.tous() if synthese3.verdict(i) == "contraire"]
        self.assertEqual(contraires, ["S01", "S02"])


class TestMethodes(unittest.TestCase):
    def test_la_mesure_se_trompe_aussi_peu_qu_elle_l_annonce(self):
        # Vérité connue : un signal qui ne dit rien de plus que RFM, même s'il en partage beaucoup.
        k, n = signaux.etalonnage(40, 1500, 0.0, tirages=99)
        self.assertLessEqual(k, 6, f"{k} faux positifs sur {n}")

    def test_la_mesure_voit_un_vrai_signal(self):
        k, n = signaux.etalonnage(20, 1500, 0.4, tirages=99)
        self.assertGreaterEqual(k, 14, f"{k} sur {n}")

    def test_la_loi_nulle_est_centree_sur_son_propre_centre(self):
        # Le centre de la loi nulle n'est pas zéro : l'effet publié s'en écarte, la bande y est centrée.
        r = synthese3.tous()["S02"]
        self.assertAlmostEqual(r.effet, r.extra["rho"] - r.extra["centre"], places=12)
        self.assertLess(r.extra["nul_bas"], 0)
        self.assertGreater(r.extra["nul_haut"], 0)

    def test_le_groupement_et_l_acceleration_par_construction(self):
        self.assertAlmostEqual(signaux.groupement([0, 10, 20], 29), 0.0, places=9)   # écarts égaux
        self.assertGreater(signaux.groupement([0, 1, 2], 29), 0.5)                   # en grappe
        self.assertGreater(signaux.acceleration([0, 20, 30, 35]), 0)                  # ça accélère
        self.assertLess(signaux.acceleration([0, 5, 15, 35]), 0)                      # ça ralentit
        self.assertIsNone(signaux.acceleration([0, 5]))

    def test_la_capture_sur_des_comptes_exacts(self):
        y = [10.0, 0.0, 5.0, 0.0, 85.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        ordre = sorted(range(10), key=lambda i: -y[i])
        self.assertAlmostEqual(signaux.capture(ordre, y, 0.1), 0.85)
        self.assertAlmostEqual(signaux.capture(ordre, y, 0.1, poids=[1] * 10), 0.85)

    def test_le_backtest_juge_des_clients_jamais_vus(self):
        b = signaux.backtest("cdnow")
        t = signaux.table("cdnow")
        self.assertEqual(b["n_a"] + b["n_b"], len(t))
        self.assertTrue(0 < b["rfm"] < b["devin"] <= 1)

    def test_le_premier_pas_sur_des_comptes_exacts(self):
        x = synthese3.tous()["L03"].extra
        self.assertAlmostEqual(synthese3.tous()["L03"].effet / 100,
                               (x["p1"] - x["p0"]) - (x["p2"] - x["p1"]), places=12)

    def test_un_budget_seulement_pour_un_taux(self):
        for i in ("L02", "L04", "L06", "L14", "S07", "S15"):
            self.assertIsNone(synthese3.budget(i), i)


class TestMobile(unittest.TestCase):
    def test_aucune_couleur_en_dur(self):
        for mod in (figmobile3, mobile3, clair3):
            src = Path(mod.__file__).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"#[0-9a-fA-F]{6}\b", src), mod.__name__)

    def test_libelles_aria_sans_apostrophe(self):
        for k, svg in figmobile3.rendre().items():
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
        self.assertEqual([i for _, ids in mobile3.GROUPES for i in ids], sections)
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
            ids = sorted(set(re.findall(r'<span class="(?:res|nul)-id">([A-Z]\d\d)</span>', corps)))
            v = [synthese3.verdict(i) for i in ids]
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
        self.assertIn("localStorage.getItem('ofm-cahier-theme')", scripts[0])
        self.assertIn("'ofm-cahier3-lus'", scripts[1])
        self.assertNotIn("'ofm-cahier-lus'", scripts[1])
        self.assertNotIn("'ofm-cahier2-lus'", scripts[1])
        node = shutil.which("node")
        if node is None:
            self.skipTest("node absent")
        for script in scripts:
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
                f.write(script)
            r = subprocess.run([node, "--check", f.name], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_chaque_figure_est_placee_et_expliquee(self):
        gabarit = mobile3.TEMPLATE.read_text(encoding="utf-8")
        places = re.findall(r"\{\{FIG:([a-z0-9_]+)\|", gabarit)
        self.assertEqual(sorted(places), sorted(figmobile3.FIGURES))
        self.assertEqual(sorted(clair3.GRAPHIQUES), sorted(figmobile3.FIGURES))
        self.assertEqual(page().count('<div class="lire">'), len(figmobile3.FIGURES))

    def test_la_sortie_pour_lueur(self):
        s = mobile3.sortie()
        self.assertEqual(s["cahier"], "ofm3")
        self.assertEqual(set(s["verdicts"]), set(registre3.par_id()))
        self.assertTrue(all(v in ("tient", "contraire", "non établi") for v in s["verdicts"].values()))
        json.dumps(s, ensure_ascii=False)


class TestClair(unittest.TestCase):
    def test_les_verdicts_sont_ceux_sous_lesquels_on_a_ecrit(self):
        for i in synthese3.tous():
            self.assertEqual(synthese3.verdict(i), clair3.VERDICTS_ECRITS[i],
                             f"{i} : le verdict a changé, réécrire son texte (clair3.CARTES)")

    def test_chaque_hypothese_a_ses_trois_explications(self):
        self.assertEqual(sorted(clair3.CARTES), sorted(registre3.par_id()))
        for i, t in clair3.CARTES.items():
            self.assertEqual(len(t), 3, i)
            self.assertTrue(all(len(x) > 20 for x in t), i)
            texte = re.sub(r"X5|nº\s?\d", "", t[0] + t[1])
            self.assertIsNone(re.search(r"\d", texte), f"{i} : une carte ne porte aucun nombre")

    def test_toutes_les_sections_ont_leur_etude(self):
        gabarit = mobile3.TEMPLATE.read_text(encoding="utf-8")
        self.assertEqual(sorted(re.findall(r"\{\{ETUDE:([a-z]+)\}\}", gabarit)), sorted(clair3.ETUDES))

    def test_ailleurs_cite_des_references_connues(self):
        for e in litterature3.AILLEURS:
            self.assertIn(e["ref"], litterature3.REFS)

    def test_les_reliefs_disent_ce_qu_ils_montrent(self):
        # « la colonne accélère est la plus haute de sa rangée », « en grappes plus basse que réguliers ».
        za, _ = signaux.grille("acceleration", "x5")
        self.assertTrue(all(l[-1] == max(l) for l in za))
        zg, _ = signaux.grille("groupement", "cdnow")
        self.assertTrue(all(l[-1] < l[0] for l in zg))
        z, _, _, _ = leviers.grille_bonus_distance()
        self.assertGreater(min(min(l) for l in z[1:]), max(z[0]))


if __name__ == "__main__":
    unittest.main()
