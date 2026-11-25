"""Tous les calculs du cahier nº 4, rangés avec leur empreinte dans `ofm/donnees/CALCUL4.json`.

La batterie complète prend une quinzaine de minutes (36 réglages × 3 règles × 3
marchés, dont les 687 029 clients de Lenta, et 4 000 arènes). La page, les
graphiques et la synthèse lisent donc ce fichier. Il porte l'**empreinte**
SHA-256 de chaque module qui calcule et de chaque extrait de données : si un
seul octet change, l'empreinte ne correspond plus et tout se recalcule. Un
fichier ne peut donc pas survivre au code qui l'a produit.

    python -m ofm.calcul4          # recalcule si l'empreinte a changé
    python -m ofm.calcul4 --force  # recalcule tout
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path

from .resultat import Resultat

ICI = Path(__file__).resolve().parent
CIBLE = ICI / "donnees" / "CALCUL4.json"
SOURCES = ("registre", "registre2", "registre3", "registre4", "stats", "stress", "cibler", "donnees", "donnees2",
           "donnees3", "donnees4", "signaux", "avances", "bandit", "foule", "baleines", "revisite", "arene")
DONNEES = ("hillstrom.csv.gz", "lenta.csv.gz", "x5.csv.gz", "x5_achats.csv.gz", "kickstarter.csv.gz",
           "cdnow.csv.gz", "retail.csv.gz", "obp.csv.gz")


def empreinte() -> str:
    h = hashlib.sha256()
    for m in SOURCES:
        h.update((ICI / f"{m}.py").read_bytes())
    for f in DONNEES:
        h.update((ICI / "donnees" / f).read_bytes())
    return h.hexdigest()


def _res(r: Resultat) -> dict:
    return dataclasses.asdict(r)


def calculer() -> dict:
    from . import arene, avances, baleines, bandit, foule, registre4 as R4, revisite

    out: dict = {"empreinte": empreinte(), "resultats": {}, "batteries": {}}
    for m in (avances, bandit, foule, baleines, revisite):
        for k, v in m.resultats().items():
            out["resultats"][k] = _res(v)
        for k, v in m.batteries().items():
            out["batteries"][k] = v
    out["gains"] = {jeu: {"appris": avances.principal(jeu, "hasard")["gain_a"],
                          **{r: avances.principal(jeu, r)["gain_b"] for r in ("valeur", "risque", "hasard")}}
                    for jeu in avances.JEUX}
    out["rapports"] = avances.rapports()
    out["k03"] = foule.k03()
    out["k03_placebo"] = foule.k03(decalage=R4.K_FAUSSE_OUVERTURE)
    out["baleines"] = {j: {str(q): baleines.mesure(j, q) for q in R4.W_PARTS} for j in baleines.IDS}
    out["r_temps"] = {j: revisite.temps(j) for j in ("cdnow", "retail")}
    out["arene"] = {"jouer": arene.jouer(), "affirmations": arene.affirmations(),
                    "severe": arene.affirmations(severe=True),
                    "sensibilite": {p: arene.sensibilite(p) for p in R4.DOMAINE},
                    "calage": arene.calage()}
    return out


def _json(o):
    if isinstance(o, tuple):
        return list(o)
    raise TypeError(type(o))


@lru_cache(maxsize=1)
def charger(force: bool = False) -> dict:
    if not force and CIBLE.exists():
        d = json.loads(CIBLE.read_text(encoding="utf-8"))
        if d.get("empreinte") == empreinte():
            return _relire(d)
    d = calculer()
    CIBLE.write_text(json.dumps(d, ensure_ascii=False, default=_json, separators=(",", ":")) + "\n",
                     encoding="utf-8")
    return _relire(json.loads(CIBLE.read_text(encoding="utf-8")))


def _relire(d: dict) -> dict:
    """Rend aux résultats leur forme (Resultat) et aux clés de l'arène leur type (entiers)."""
    d["resultats"] = {k: Resultat(**{**v, "ic": tuple(v["ic"])}) for k, v in d["resultats"].items()}
    d["arene"]["jouer"] = [{int(s): v for s, v in t.items()} for t in d["arene"]["jouer"]]
    for cle in ("affirmations", "severe"):
        a = d["arene"][cle]
        for k in ("top1", "top10", "rang_median", "pire_rang"):
            a[k] = {int(s): v for s, v in a[k].items()}
        a["copie"]["parts"] = {float(p): v for p, v in a["copie"]["parts"].items()}
    return d


def main() -> None:
    d = charger(force="--force" in sys.argv)
    print("empreinte", d["empreinte"][:16], "résultats", len(d["resultats"]), "→", CIBLE.name)


if __name__ == "__main__":
    main()
