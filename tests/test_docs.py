"""Les nombres cités dans la documentation viennent du code.

Le document de travail se construit par gabarit : aucun de ses nombres ne peut
diverger du calcul, puisqu'il n'y est pas écrit. `README.md` et
`docs/donnees-requises.md` sont en prose libre, et leurs nombres y sont donc
écrits à la main — ce sont les deux seuls endroits du dépôt où une divergence
silencieuse est possible. Ces tests la ferment.

Le test de fin est le plus utile des deux : il refuse tout nombre à point
décimal dans la prose française, ce qui attrape le copier-coller depuis une
sortie de calcul avant qu'il n'atteigne le lecteur.
"""

from __future__ import annotations

import pathlib
import re
import unittest

from alp1.calib import REFERENCE
from alp1.decay import breaking_decay, breaking_rate, decay_rate, runways, surviving_edge
from alp1.report3 import ASOF_YEAR, EDGE_BPS, _breaking_edge_bps
from alp1.scaling import HURST_HI, HURST_LO, calibrate, coherence_gap, robust_entry

RACINE = pathlib.Path(__file__).resolve().parent.parent
DOC = RACINE / "docs" / "donnees-requises.md"
LISEZMOI = RACINE / "README.md"


def fr(x: float, nd: int) -> str:
    """Le nombre tel qu'il doit apparaître dans la prose française."""
    return f"{x:.{nd}f}".replace(".", ",")


class TestNombresCites(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texte = (DOC.read_text(encoding="utf-8")
                     + LISEZMOI.read_text(encoding="utf-8"))
        cls.brk = _breaking_edge_bps()
        cls.rws = runways(EDGE_BPS, cls.brk, ASOF_YEAR)

    def citer(self, valeur: str, quoi: str):
        self.assertIn(valeur, self.texte,
                      f"{quoi} : « {valeur} » absent de la documentation")

    def test_la_decote_de_rupture_est_citee_juste(self):
        self.citer(fr(breaking_decay(EDGE_BPS, self.brk) * 100, 1) + " %",
                   "décote de rupture")

    def test_le_point_de_rupture_est_cite_juste(self):
        self.citer(fr(self.brk, 2), "point de rupture en points de base")

    def test_la_derive_restante_de_chaque_source_est_citee_juste(self):
        for r in self.rws:
            with self.subTest(source=r.source):
                self.citer(fr(r.edge_today, 2), f"dérive restante ({r.published})")

    def test_les_marges_sont_citees_juste(self):
        for r in self.rws:
            with self.subTest(source=r.source):
                self.citer(fr(r.margin, 2) + "×", f"marge ({r.published})")
        self.citer(fr(EDGE_BPS / self.brk, 2) + "×", "marge sans décote")

    def test_les_annees_de_rupture_sont_citees_juste(self):
        for r in self.rws:
            with self.subTest(source=r.source):
                self.citer(str(int(round(r.expiry))), f"expiration ({r.published})")

    def test_le_taux_de_bascule_est_cite_juste(self):
        taux = breaking_rate(EDGE_BPS, self.brk,
                             float(ASOF_YEAR - self.rws[0].published))
        self.citer(fr(taux, 3), "taux de bascule")

    def test_le_facteur_de_coherence_est_cite_juste(self):
        _, _, facteur = coherence_gap()
        self.citer(fr(facteur, 3), "facteur de cohérence de l'exposant")

    def test_les_probabilites_d_arret_sont_citees_juste(self):
        for h in (HURST_LO, HURST_HI):
            with self.subTest(H=h):
                self.citer(fr(calibrate(h).p_stop * 100, 1) + " %",
                           f"probabilité d'arrêt (H = {h})")

    def test_l_heure_d_entree_optimale_est_citee_juste(self):
        r = robust_entry()
        best = min(r, key=lambda x: x[2])
        ref = [x for x in r if x[0] == REFERENCE.entry_min][0]
        self.citer(str(int(best[0])), "heure d'entrée optimale")
        self.citer(str(int(ref[0])), "heure d'entrée du protocole")
        self.citer(fr((1 - best[2] / ref[2]) * 100, 1) + " %", "gain d'entrée")
        self.citer(fr(ref[1], 1), "exposition à l'heure du protocole")
        self.citer(fr(best[1], 1), "exposition à l'heure optimale")

    def test_aucun_nombre_anglais_ne_traine(self):
        """Un point décimal dans la prose est le signe d'un copier-coller."""
        prose = re.sub(r"```.*?```", "", self.texte, flags=re.S)
        prose = re.sub(r"`[^`]*`", "", prose)
        prose = re.sub(r"\d\.\d+e[+-]?\d+", "", prose)          # notation scientifique
        prose = re.sub(r"(?i)\b(?:python|v)\s?\d+\.\d+(?:\.\d+)?\+?", "", prose)  # versions
        prose = re.sub(r"[\w-]+\.(md|csv|py|html)\b", "", prose)  # noms de fichiers
        for m in re.finditer(r"\d+\.\d+", prose):
            with self.subTest(nombre=m.group(0)):
                self.fail(f"nombre à point décimal dans la prose : {m.group(0)}")


if __name__ == "__main__":
    unittest.main()


class TestComptes(unittest.TestCase):
    """Les comptes annoncés par le README sont ceux du dépôt."""

    @classmethod
    def setUpClass(cls):
        cls.texte = LISEZMOI.read_text(encoding="utf-8")

    def citer(self, valeur: str, quoi: str):
        self.assertIn(valeur, self.texte,
                      f"{quoi} : « {valeur} » absent du README")

    def test_le_nombre_de_tables_annonce_est_le_bon(self):
        from alp1.workingpaper import tables
        self.citer(f"{len(tables())} tables", "nombre de tables")

    def test_le_nombre_de_figures_annonce_est_le_bon(self):
        from alp1.workingpaper import figures
        self.citer(f"{len(figures())} figures", "nombre de figures")

    def test_le_nombre_de_sections_annonce_est_le_bon(self):
        from alp1.workingpaper import build
        corps = build().split("</style>", 1)[1]
        n = len(re.findall(r'<h2 id="[a-z0-9-]+"', corps))
        self.citer(f"{n} sections", "nombre de sections")

    def test_le_nombre_de_tests_annonce_est_le_bon(self):
        loader = unittest.TestLoader()
        suite = loader.discover(str(RACINE / "tests"), top_level_dir=str(RACINE))

        def compter(s):
            return sum(compter(x) if isinstance(x, unittest.TestSuite) else 1
                       for x in s)

        self.citer(f"{compter(suite)} tests unitaires", "nombre de tests")
