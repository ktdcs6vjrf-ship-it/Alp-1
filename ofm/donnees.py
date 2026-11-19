"""Les jeux de données : provenance, extraction compacte, lecture.

Aucun hébergeur de données d'OnlyFans n'est joignable, et il ne faut pas qu'il
le soit : la plateforme interdit l'aspiration de ses pages. Les hypothèses se
testent donc sur des **marchés voisins** où l'humain fait le même geste —
demander de l'argent à un inconnu, répondre à une offre, se laisser persuader,
marchander, dire oui à quelqu'un, revenir acheter.

Chaque jeu est un dépôt public cloné à un commit précis. L'extraction n'en
garde que les colonnes utilisées, retire les identifiants (noms d'utilisateur,
donateurs, descriptions d'annonces) et écrit un fichier compressé dans
`ofm/donnees/`. Le fichier `PROVENANCE.json` porte, pour chaque jeu, le dépôt,
le commit, le chemin, l'empreinte SHA-256 du fichier brut et celle de l'extrait.
Le document se reconstruit sans réseau à partir des extraits ; l'extraction se
rejoue avec `python -m ofm.donnees` quand les clones sont présents.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import os
from functools import lru_cache
from pathlib import Path

ICI = Path(__file__).resolve().parent
DOSSIER = ICI / "donnees"
PROVENANCE = DOSSIER / "PROVENANCE.json"

#: Racine des clones bruts. Ils vivent hors du dépôt : ce sont des données
#: téléchargées, donc non fiables, et elles n'y entrent qu'extraites.
BRUT = Path(os.environ.get("OFM_BRUT", "/home/user/donnees-ext"))
BRUT_RAOP = Path(os.environ.get("OFM_BRUT_RAOP",
                                "/home/user/aseastman/random_acts_of_pizza"))

SOURCES = {
    "raop": {
        "titre": "Random Acts of Pizza (Althoff, Danescu-Niculescu-Mizil et Jurafsky, 2014)",
        "depot": "https://github.com/aseastman/random_acts_of_pizza",
        "commit": "e84a8762788a20c23336383d13a92593c403ed02",
        "chemin": "train.json",
        "unite": "demande d'une pizza offerte par un inconnu, Reddit 2011–2013",
    },
    "speed": {
        "titre": "Speed dating de Columbia (Fisman, Iyengar, Kamenica et Simonson, 2006)",
        "depot": "https://github.com/syedm101/speeddating",
        "commit": "ca87bb1a31710e74865c01adb9a88d60b667db3d",
        "chemin": "Speed Dating Data.csv",
        "unite": "rencontre de quatre minutes, décision oui ou non de chaque côté",
    },
    "karlan": {
        "titre": "Expérience de dons de Karlan et List (2007)",
        "depot": "https://github.com/rsm-kvootla/ABTest-DonationStrategy-KarlanList",
        "commit": "c0e2e8211a57d18239c7017dd57f7f57ef73becd",
        "chemin": "statadata.csv",
        "unite": "lettre de sollicitation tirée au sort, donateur antérieur",
    },
    "p4g": {
        "titre": "Persuasion for Good (Wang et al., 2019)",
        "depot": "https://github.com/ohyj1002/persuasionforgood",
        "commit": "3fbc0df7bd2a081413cad6e6092e7c712efc26c4",
        "chemin": "data/FullData/full_info.csv + full_dialog.csv",
        "unite": "conversation écrite où l'un persuade l'autre de donner",
    },
    "bargain": {
        "titre": "CraigslistBargain (He, Chen, Balakrishnan et Liang, 2018)",
        "depot": "https://github.com/tranthai189765/AAAI_env",
        "commit": "ddcdec1a4694af7d5f855a342a583f7c23958bb2",
        "chemin": "data/train.jsonl + data/test.jsonl",
        "unite": "négociation écrite d'un objet d'annonce entre acheteur et vendeur",
    },
    "cdnow": {
        "titre": "Cohorte CDNOW (Fader, Hardie et Lee, 2005)",
        "depot": "https://pypi.org/project/Lifetimes/0.11.3/",
        "commit": "Lifetimes-0.11.3-py3-none-any.whl",
        "chemin": "lifetimes/datasets/CDNOW_master.txt",
        "unite": "achat d'un client recruté au premier trimestre 1997",
    },
    "cdnow_echantillon": {
        "titre": "Échantillon CDNOW publié avec le modèle BG/NBD (2 357 clients)",
        "depot": "https://pypi.org/project/Lifetimes/0.11.3/",
        "commit": "Lifetimes-0.11.3-py3-none-any.whl",
        "chemin": "lifetimes/datasets/cdnow_customers_summary.csv",
        "unite": "résumé fréquence, récence, ancienneté d'un client",
    },
    "dons": {
        "titre": "Donateurs répétés d'une association (Fader, Hardie et Shang, 2010)",
        "depot": "https://pypi.org/project/Lifetimes/0.11.3/",
        "commit": "Lifetimes-0.11.3-py3-none-any.whl",
        "chemin": "lifetimes/datasets/donations.csv",
        "unite": "historique de dons sur six occasions annuelles",
    },
    "naissances": {
        "titre": "Naissances américaines par jour, 2000–2014 (SSA, via FiveThirtyEight)",
        "depot": "https://github.com/fivethirtyeight/data",
        "commit": "4c1ff5e3aef1816ae04af63218015066e186c147",
        "chemin": "births/US_births_2000-2014_SSA.csv",
        "unite": "naissances d'un jour civil",
    },
}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def _ecrire_gz(nom: str, texte: str) -> Path:
    """Écrit un extrait compressé **au bit près** : mtime nul, sans nom."""
    cible = DOSSIER / nom
    tampon = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=tampon, mtime=0,
                       compresslevel=9) as g:
        g.write(texte.encode("utf-8"))
    cible.write_bytes(tampon.getvalue())
    return cible


def _csv(lignes: list[list], entete: list[str]) -> str:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(entete)
    w.writerows(lignes)
    return out.getvalue()


# ---------------------------------------------------------------------------
# Extraction (réseau ou clones requis)
# ---------------------------------------------------------------------------

RAOP_CHAMPS = [
    "unix_timestamp_of_request", "unix_timestamp_of_request_utc",
    "requester_received_pizza", "request_title", "request_text_edit_aware",
    "requester_account_age_in_days_at_request",
    "requester_days_since_first_post_on_raop_at_request",
    "requester_number_of_comments_at_request",
    "requester_number_of_comments_in_raop_at_request",
    "requester_number_of_posts_at_request",
    "requester_number_of_posts_on_raop_at_request",
    "requester_number_of_subreddits_at_request",
    "requester_upvotes_minus_downvotes_at_request",
    "requester_upvotes_plus_downvotes_at_request",
]

SPEED_CHAMPS = [
    "iid", "gender", "wave", "round", "position", "order", "partner", "pid",
    "condtn", "dec", "attr", "sinc", "intel", "fun", "amb", "shar", "like",
    "prob", "met", "dec_o", "attr_o", "sinc_o", "intel_o", "fun_o", "amb_o",
    "shar_o", "like_o", "prob_o", "match", "samerace", "int_corr", "age",
    "age_o", "goal", "date", "go_out", "exphappy",
]

KARLAN_CHAMPS = [
    "treatment", "ratio", "size", "ask", "amount", "gave", "hpa", "freq",
    "years", "mrm2", "dormant", "female", "couple", "red0", "blue0",
    "median_hhincome", "pwhite",
]


def extraire() -> dict:
    """Relit les clones bruts et réécrit les extraits et la provenance."""
    DOSSIER.mkdir(exist_ok=True)
    prov = {}

    def noter(cle: str, brut: list[Path], extrait: Path) -> None:
        info = dict(SOURCES[cle])
        info["sha256_brut"] = [_sha(p) for p in brut]
        info["extrait"] = extrait.name
        info["sha256_extrait"] = _sha(extrait)
        prov[cle] = info

    # RAOP : un enregistrement JSON par ligne, sans nom d'utilisateur.
    src = BRUT_RAOP / "train.json"
    data = json.loads(src.read_text(encoding="utf-8"))
    lignes = []
    for r in data:
        lignes.append(json.dumps({k: r[k] for k in RAOP_CHAMPS},
                                 ensure_ascii=False, sort_keys=True))
    noter("raop", [src], _ecrire_gz("raop.jsonl.gz", "\n".join(lignes) + "\n"))

    # Speed dating : colonnes utiles seulement (ni code postal, ni métier).
    src = BRUT / "syedm101_speeddating" / "Speed Dating Data.csv"
    with open(src, encoding="latin-1", newline="") as f:
        rd = csv.DictReader(f)
        rows = [[r[k] for k in SPEED_CHAMPS] for r in rd]
    noter("speed", [src], _ecrire_gz("speed.csv.gz", _csv(rows, SPEED_CHAMPS)))

    src = BRUT / "rsm-kvootla_ABTest-DonationStrategy-KarlanList" / "statadata.csv"
    with open(src, encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        rows = [[r[k] for k in KARLAN_CHAMPS] for r in rd]
    noter("karlan", [src], _ecrire_gz("karlan.csv.gz", _csv(rows, KARLAN_CHAMPS)))

    base = BRUT / "ohyj1002_persuasionforgood" / "data" / "FullData"
    info, dial = base / "full_info.csv", base / "full_dialog.csv"
    with open(info, encoding="utf-8", newline="") as f:
        rd = csv.reader(f)
        ent = next(rd)
        rows = list(rd)
    e1 = _ecrire_gz("p4g_info.csv.gz", _csv(rows, ent))
    with open(dial, encoding="utf-8", newline="") as f:
        rd = csv.reader(f)
        next(rd)
        rows = [[r[4], r[3], r[2], r[1]] for r in rd]   # dialogue, rôle, tour, phrase
    e2 = _ecrire_gz("p4g_dialog.csv.gz",
                    _csv(rows, ["dialogue", "role", "tour", "phrase"]))
    noter("p4g", [info, dial], e1)
    prov["p4g"]["extrait"] = f"{e1.name} + {e2.name}"
    prov["p4g"]["sha256_extrait"] = [_sha(e1), _sha(e2)]

    lignes, brut = [], []
    for part in ("train", "test"):
        src = BRUT / "tranthai189765_AAAI_env" / "data" / f"{part}.jsonl"
        brut.append(src)
        for k, l in enumerate(open(src, encoding="utf-8")):
            r = json.loads(l)
            lignes.append(json.dumps({
                "lot": part, "objet": r["item_name"],
                "cible_acheteur": r["buyer_price"], "annonce": r["seller_price"],
                "accord": r.get("deal_price"),
                "dialogue": [[t["speaker"], t["text"]] for t in r["dialog"]],
            }, ensure_ascii=False, sort_keys=True))
    noter("bargain", brut,
          _ecrire_gz("bargain.jsonl.gz", "\n".join(lignes) + "\n"))

    src = BRUT / "pypi" / "CDNOW_master.txt"
    rows = [l.split() for l in open(src, encoding="utf-8")
            if l.strip() and l.split()[0].isdigit()]
    noter("cdnow", [src], _ecrire_gz(
        "cdnow.csv.gz", _csv(rows, ["client", "date", "cd", "montant"])))

    src = BRUT / "pypi" / "cdnow_customers_summary.csv"
    noter("cdnow_echantillon", [src],
          _ecrire_gz("cdnow_echantillon.csv.gz", src.read_text(encoding="utf-8")))

    src = BRUT / "pypi" / "donations.csv"
    noter("dons", [src], _ecrire_gz("dons.csv.gz", src.read_text(encoding="utf-8")))

    src = BRUT / "fte" / "births" / "US_births_2000-2014_SSA.csv"
    noter("naissances", [src],
          _ecrire_gz("naissances.csv.gz", src.read_text(encoding="utf-8")))

    PROVENANCE.write_text(json.dumps(prov, ensure_ascii=False, indent=1,
                                     sort_keys=True) + "\n", encoding="utf-8")
    return prov


# ---------------------------------------------------------------------------
# Lecture (sans réseau)
# ---------------------------------------------------------------------------

def _lire(nom: str) -> str:
    with gzip.open(DOSSIER / nom, "rt", encoding="utf-8") as f:
        return f.read()


def _lignes_csv(nom: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(_lire(nom))))


def _f(v: str) -> float | None:
    return float(v) if v not in ("", "NA", "nan") else None


@lru_cache(maxsize=1)
def raop() -> tuple[dict, ...]:
    return tuple(json.loads(l) for l in _lire("raop.jsonl.gz").splitlines() if l)


@lru_cache(maxsize=1)
def speed() -> tuple[dict, ...]:
    out = []
    for r in _lignes_csv("speed.csv.gz"):
        out.append({k: (_f(v) if v.replace(".", "", 1).replace("-", "", 1).isdigit()
                        or v == "" else v) for k, v in r.items()})
    return tuple(out)


@lru_cache(maxsize=1)
def karlan() -> tuple[dict, ...]:
    out = []
    for r in _lignes_csv("karlan.csv.gz"):
        d = {k: _f(r[k]) for k in ("amount", "gave", "hpa", "freq", "years",
                                    "mrm2", "dormant", "female", "couple",
                                    "red0", "blue0", "median_hhincome", "pwhite",
                                    "treatment")}
        d["ratio"], d["size"], d["ask"] = r["ratio"], r["size"], r["ask"]
        out.append(d)
    return tuple(out)


@lru_cache(maxsize=1)
def p4g() -> tuple[tuple[dict, ...], tuple[dict, ...]]:
    return tuple(_lignes_csv("p4g_info.csv.gz")), tuple(_lignes_csv("p4g_dialog.csv.gz"))


@lru_cache(maxsize=1)
def bargain() -> tuple[dict, ...]:
    return tuple(json.loads(l) for l in _lire("bargain.jsonl.gz").splitlines() if l)


@lru_cache(maxsize=1)
def cdnow() -> tuple[tuple[int, int, int, float], ...]:
    out = []
    for r in _lignes_csv("cdnow.csv.gz"):
        out.append((int(r["client"]), int(r["date"]), int(r["cd"]), float(r["montant"])))
    return tuple(out)


@lru_cache(maxsize=1)
def cdnow_echantillon() -> tuple[tuple[int, float, float], ...]:
    return tuple((int(float(r["frequency"])), float(r["recency"]), float(r["T"]))
                 for r in _lignes_csv("cdnow_echantillon.csv.gz"))


@lru_cache(maxsize=1)
def dons() -> tuple[tuple[int, int, int, int], ...]:
    return tuple((int(r["frequency"]), int(r["recency"]), int(r["periods"]),
                  int(r["weights"])) for r in _lignes_csv("dons.csv.gz"))


@lru_cache(maxsize=1)
def naissances() -> tuple[tuple[int, int, int, int, int], ...]:
    return tuple((int(r["year"]), int(r["month"]), int(r["date_of_month"]),
                  int(r["day_of_week"]), int(r["births"]))
                 for r in _lignes_csv("naissances.csv.gz"))


def provenance() -> dict:
    return json.loads(PROVENANCE.read_text(encoding="utf-8"))


def verifier() -> list[str]:
    """Les extraits présents ont-ils l'empreinte que la provenance annonce ?"""
    fautes = []
    for cle, info in provenance().items():
        noms = [n.strip() for n in info["extrait"].split("+")]
        sha = info["sha256_extrait"]
        sha = sha if isinstance(sha, list) else [sha]
        for nom, h in zip(noms, sha):
            if _sha(DOSSIER / nom) != h:
                fautes.append(f"{cle}: {nom}")
    return fautes


if __name__ == "__main__":
    p = extraire()
    for cle, info in p.items():
        print(f"{cle:11s} {info['extrait']}")
    print("fautes :", verifier() or "aucune")
