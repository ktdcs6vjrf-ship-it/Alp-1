"""Les jeux de données du cahier nº 3 : provenance, extraction compacte, lecture.

Même règle que `donnees.py` et `donnees2.py` : chaque jeu vient d'une copie
publique figée (commit Git, ou objet S3 désigné par son ETag), l'extraction ne
garde que les colonnes utilisées, renumérote ce qui identifie, et écrit un
fichier compressé **au bit près** dans `ofm/donnees/`. `PROVENANCE3.json` porte
la source, la version, l'empreinte SHA-256 du brut et celle de l'extrait. Le
cahier se reconstruit sans réseau ; l'extraction se rejoue avec
`python -m ofm.donnees3` quand les bruts sont présents (`OFM_BRUT3`, par défaut
`/home/user/donnees-ext/ofm3`, et `OFM_BRUT2` pour les achats de X5).

**Les signaux** se lisent sur trois marchés d'achats répétés : CDNOW et Online
Retail II, déjà extraits pour les cahiers nº 1 et nº 2 (`donnees.cdnow`,
`donnees2.retail`, relus tels quels), et **les achats de X5** (un échantillon
de clients fixé par règle, une ligne par passage en caisse).

**Les leviers** viennent de cinq expériences tirées au sort, publiées avec leur
article et recopiées par le dépôt Rdatasets (V. Arel-Bundock), figé à un commit :
Thornton (2008), Rondeau et List (2008), Cai, de Janvry et Sadoulet (2015),
Guéguen (2002), Lynn et Mynier (1993).
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import os
import zlib
from functools import lru_cache
from pathlib import Path

from .donnees import DOSSIER, _csv, _ecrire_gz, _sha
from .registre3 import X5_MODULO

PROVENANCE3 = DOSSIER / "PROVENANCE3.json"
BRUT3 = Path(os.environ.get("OFM_BRUT3", "/home/user/donnees-ext/ofm3"))
BRUT2 = Path(os.environ.get("OFM_BRUT2", "/home/user/donnees-ext/ofm2"))

RDATASETS = "https://github.com/vincentarelbundock/Rdatasets"
RDATASETS_COMMIT = "1dcc2bf5f955cc1224a3e1307256e1fe86b68dae"

SOURCES3 = {
    "x5_achats": {
        "titre": "Achats de X5 RetailHero (2019), un client sur vingt-cinq environ",
        "depot": "https://sklift.s3.eu-west-2.amazonaws.com/",
        "commit": "ETag b28f96e6fc52c03e223f18ee855e67ed-39 (copie de scikit-uplift 0.5.1)",
        "chemin": "purchases.csv.gz",
        "unite": "passage en caisse d'un client de l'échantillon : date, montant, lignes de produit",
    },
    "thornton": {
        "titre": "Bonus pour aller chercher son résultat (Thornton, 2008 ; Malawi)",
        "depot": RDATASETS, "commit": RDATASETS_COMMIT,
        "chemin": "csv/causaldata/thornton_hiv.csv",
        "unite": "personne testée : bonus tiré au sort, distance au centre, résultat retiré ou non",
    },
    "rondeau": {
        "titre": "Premier don annoncé contre doublement promis (Rondeau et List, 2008)",
        "depot": RDATASETS, "commit": RDATASETS_COMMIT,
        "chemin": "csv/experimentr/rondeau.csv",
        "unite": "lettre de collecte : version tirée au sort, don reçu",
    },
    "cai": {
        "titre": "Choix par défaut et explication détaillée (Cai, de Janvry et Sadoulet, 2015 ; Chine)",
        "depot": RDATASETS, "commit": RDATASETS_COMMIT,
        "chemin": "csv/causaldata/social_insure.csv",
        "unite": "foyer de riziculteurs : format de séance tiré au sort, assurance souscrite ou non",
    },
    "gueguen": {
        "titre": "Une blague avec l'addition (Guéguen, 2002 ; café de station balnéaire)",
        "depot": RDATASETS, "commit": RDATASETS_COMMIT,
        "chemin": "csv/Stat2Data/TipJoke.csv",
        "unite": "client d'un café : carte tirée au sort avec l'addition, pourboire ou non",
    },
    "lynn": {
        "titre": "Le serveur à hauteur des yeux (Lynn et Mynier, 1993 ; restaurant)",
        "depot": RDATASETS, "commit": RDATASETS_COMMIT,
        "chemin": "csv/experimentr/lynn.csv",
        "unite": "table d'un restaurant : posture tirée au sort, addition et pourboire",
    },
}


def _rd(nom: str) -> list[dict]:
    with open(BRUT3 / nom, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _na(v: str) -> bool:
    return v in ("", "NA")


def _x5_achats() -> tuple[list[Path], str]:
    """Une ligne par passage en caisse d'un client de l'échantillon.

    Le montant d'un passage (`purchase_sum`) est répété sur chacune de ses
    lignes de produit : on le prend une fois, et l'on compte les lignes."""
    src = BRUT2 / "x5_purchases.csv.gz"
    passages: dict[tuple[str, str], list] = {}
    with gzip.open(src, "rt", encoding="utf-8", newline="") as f:
        rd = csv.reader(f)
        c = {k: i for i, k in enumerate(next(rd))}
        ic, it, idt, isum = c["client_id"], c["transaction_id"], c["transaction_datetime"], c["purchase_sum"]
        garde: dict[str, bool] = {}
        for r in rd:
            cid = r[ic]
            g = garde.get(cid)
            if g is None:
                g = garde[cid] = zlib.crc32(cid.encode("utf-8")) % X5_MODULO == 0
            if not g:
                continue
            p = passages.setdefault((cid, r[it]), [cid, r[idt][:16], float(r[isum] or 0), 0])
            p[3] += 1
    rang = {cid: i + 1 for i, cid in enumerate(sorted({p[0] for p in passages.values()}))}
    rows = sorted([rang[p[0]], p[1], f"{p[2]:.2f}", p[3]] for p in passages.values())
    return [src], _csv(rows, ["client", "date", "montant", "lignes"])


def _thornton() -> tuple[list[Path], str]:
    rows = []
    for r in _rd("thornton_hiv.csv"):
        if _na(r["got"]) or _na(r["any"]) or _na(r["tinc"]) or _na(r["distvct"]):
            continue
        village = 0 if _na(r["villnum"]) else int(r["villnum"])     # sans village : une strate à part
        rows.append([village, int(float(r["got"])), int(float(r["any"])),
                     f"{float(r['tinc']):.4f}", f"{float(r['distvct']):.4f}"])
    rows.sort()
    return [BRUT3 / "thornton_hiv.csv"], _csv(rows, ["village", "retire", "bonus", "montant", "distance"])


def _rondeau() -> tuple[list[Path], str]:
    bras = {"0": "temoin_haut", "1": "premier_don", "2": "doublement", "3": "temoin_bas"}
    rows = sorted([bras[r["treattype"]], f"{float(r['donation']):.2f}"] for r in _rd("rondeau.csv")
                  if not _na(r["donation"]))      # six lettres sans montant connu
    return [BRUT3 / "rondeau.csv"], _csv(rows, ["bras", "don"])


def _cai() -> tuple[list[Path], str]:
    hameaux = {a: i + 1 for i, a in enumerate(sorted({r["address"] for r in _rd("social_insure.csv")}))}
    villages = {v: i + 1 for i, v in enumerate(sorted({r["village"] for r in _rd("social_insure.csv")}))}
    rows = sorted([villages[r["village"]], hameaux[r["address"]], int(r["default"]), int(r["intensive"]),
                   int(r["takeup_survey"])] for r in _rd("social_insure.csv"))
    return [BRUT3 / "social_insure.csv"], _csv(rows, ["village", "hameau", "defaut_oui", "detaillee", "souscrit"])


def _gueguen() -> tuple[list[Path], str]:
    carte = {"Joke": "blague", "Ad": "publicite", "None": "aucune"}
    rows = sorted([carte[r["Card"]], int(r["Tip"])] for r in _rd("TipJoke.csv"))
    return [BRUT3 / "TipJoke.csv"], _csv(rows, ["carte", "pourboire"])


def _lynn() -> tuple[list[Path], str]:
    rows = sorted([int(r["crouch"]), int(r["daytime"]), int(r["groupsize"]), f"{float(r['bill']):.2f}",
                   f"{float(r['tip']):.2f}"] for r in _rd("lynn.csv"))
    return [BRUT3 / "lynn.csv"], _csv(rows, ["accroupi", "midi", "convives", "addition", "pourboire"])


EXTRAITS = {"x5_achats": ("x5_achats.csv.gz", _x5_achats), "thornton": ("thornton.csv.gz", _thornton),
            "rondeau": ("rondeau.csv.gz", _rondeau), "cai": ("cai.csv.gz", _cai),
            "gueguen": ("gueguen.csv.gz", _gueguen), "lynn": ("lynn.csv.gz", _lynn)}


def extraire(cles: list[str] | None = None) -> dict:
    """Relit les bruts et réécrit les extraits demandés et leur provenance."""
    prov = provenance() if PROVENANCE3.exists() else {}
    for cle in cles or list(EXTRAITS):
        nom, f = EXTRAITS[cle]
        brut, texte = f()
        cible = _ecrire_gz(nom, texte)
        info = dict(SOURCES3[cle])
        info["sha256_brut"] = [_sha(p) for p in brut]
        info["extrait"] = cible.name
        info["sha256_extrait"] = _sha(cible)
        prov[cle] = info
    PROVENANCE3.write_text(json.dumps(prov, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                           encoding="utf-8")
    return prov


# ---------------------------------------------------------------------------
# Lecture (sans réseau)
# ---------------------------------------------------------------------------

def _lignes(nom: str) -> list[dict]:
    with gzip.open(DOSSIER / nom, "rt", encoding="utf-8") as f:
        return list(csv.DictReader(io.StringIO(f.read())))


@lru_cache(maxsize=1)
def x5_achats() -> tuple[tuple[int, str, float, int], ...]:
    return tuple((int(r["client"]), r["date"], float(r["montant"]), int(r["lignes"]))
                 for r in _lignes("x5_achats.csv.gz"))


@lru_cache(maxsize=1)
def thornton() -> tuple[dict, ...]:
    return tuple({"village": int(r["village"]), "retire": int(r["retire"]), "bonus": int(r["bonus"]),
                  "montant": float(r["montant"]), "distance": float(r["distance"])}
                 for r in _lignes("thornton.csv.gz"))


@lru_cache(maxsize=1)
def rondeau() -> tuple[tuple[str, float], ...]:
    return tuple((r["bras"], float(r["don"])) for r in _lignes("rondeau.csv.gz"))


@lru_cache(maxsize=1)
def cai() -> tuple[dict, ...]:
    return tuple({k: int(v) for k, v in r.items()} for r in _lignes("cai.csv.gz"))


@lru_cache(maxsize=1)
def gueguen() -> tuple[tuple[str, int], ...]:
    return tuple((r["carte"], int(r["pourboire"])) for r in _lignes("gueguen.csv.gz"))


@lru_cache(maxsize=1)
def lynn() -> tuple[dict, ...]:
    return tuple({"accroupi": int(r["accroupi"]), "midi": int(r["midi"]), "convives": int(r["convives"]),
                  "addition": float(r["addition"]), "pourboire": float(r["pourboire"])}
                 for r in _lignes("lynn.csv.gz"))


def provenance() -> dict:
    return json.loads(PROVENANCE3.read_text(encoding="utf-8"))


def verifier() -> list[str]:
    """Les extraits présents ont-ils l'empreinte que la provenance annonce ?"""
    return [cle for cle, info in provenance().items()
            if _sha(DOSSIER / info["extrait"]) != info["sha256_extrait"]]


if __name__ == "__main__":
    import sys
    p = extraire(sys.argv[1:] or None)
    for cle, info in p.items():
        print(f"{cle:12s} {info['extrait']:22s} {(DOSSIER / info['extrait']).stat().st_size:>10,} octets")
    print("fautes :", verifier() or "aucune")
