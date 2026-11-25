"""Les jeux de données du cahier nº 2 : provenance, extraction compacte, lecture.

Même règle que `donnees.py` : chaque jeu vient d'une copie publique figée
(objet S3 versionné par son ETag, ou objet Git LFS désigné par son empreinte),
l'extraction ne garde que les colonnes utilisées, renumérote les clients, et
écrit un fichier compressé **au bit près** dans `ofm/donnees/`. Le fichier
`PROVENANCE2.json` porte la source, la version, l'empreinte SHA-256 du brut et
celle de l'extrait. Le cahier se reconstruit sans réseau à partir des extraits ;
l'extraction se rejoue avec `python -m ofm.donnees2` quand les bruts sont
présents (`OFM_BRUT2`, par défaut `/home/user/donnees-ext/ofm2`).

Cinq marchés, choisis parce que l'humain y fait un geste d'agence :

- **Hillstrom** — 64 000 clients d'un vendeur en ligne, un courriel **tiré au
  sort** (hommes, femmes, aucun) : la relance groupée ;
- **Lenta** — 687 029 clients d'une enseigne, un SMS **tiré au sort** : la
  relance à grande échelle, avec l'historique de réponse aux messages passés ;
- **X5 RetailHero** — 200 039 clients, un SMS **tiré au sort**, et l'historique
  d'achats d'avant le message (récence, fréquence, dépense) ;
- **Online Retail II** — un grossiste en ligne britannique, 2009–2011 : les
  achats répétés, pour revérifier sur un second marché les fidèles silencieux ;
- **Kickstarter** — 378 661 campagnes : demander de l'argent avec un objectif
  affiché et une date de fin.

Trois jeux visés n'ont pas pu entrer : Criteo Uplift (copie retirée de son
hébergeur), KKBox (seulement sur Kaggle et Mendeley, injoignables d'ici) et
l'archive Upworthy (seulement sur OSF, injoignable). Le cahier le dit.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import os
import zipfile
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from .donnees import DOSSIER, _csv, _ecrire_gz, _sha

PROVENANCE2 = DOSSIER / "PROVENANCE2.json"
BRUT2 = Path(os.environ.get("OFM_BRUT2", "/home/user/donnees-ext/ofm2"))

SOURCES2 = {
    "hillstrom": {
        "titre": "Courriels tirés au sort de Hillstrom (MineThatData, 2008)",
        "depot": "https://hillstorm1.s3.us-east-2.amazonaws.com/hillstorm_no_indices.csv.gz",
        "commit": "ETag a68a81291f53a14f4e29002629803ba3 (copie de scikit-uplift 0.5.1)",
        "chemin": "hillstorm_no_indices.csv.gz",
        "unite": "client d'un vendeur en ligne, courriel tiré au sort, deux semaines suivies",
    },
    "lenta": {
        "titre": "SMS tirés au sort de Lenta (BigTarget Hackathon, 2020)",
        "depot": "https://sklift.s3.eu-west-2.amazonaws.com/lenta_dataset.csv.gz",
        "commit": "ETag 8d1e9ceb092cf1cabd933880ef8a7e99-9 (copie de scikit-uplift 0.5.1)",
        "chemin": "lenta_dataset.csv.gz",
        "unite": "client d'une enseigne, SMS tiré au sort, visite en magasin ensuite",
    },
    "x5": {
        "titre": "SMS tirés au sort de X5 RetailHero (2019)",
        "depot": "https://sklift.s3.eu-west-2.amazonaws.com/",
        "commit": "ETags 2720bbb659daa9e0989b2777b6a42d19, b9cdeb2806b732771de03e819b3354c5, "
                  "b28f96e6fc52c03e223f18ee855e67ed-39 (copie de scikit-uplift 0.5.1)",
        "chemin": "uplift_train.csv.gz + clients.csv.gz + purchases.csv.gz",
        "unite": "client d'une enseigne, SMS tiré au sort, achat ensuite ; historique d'avant",
    },
    "retail": {
        "titre": "Online Retail II (Chen, 2019 ; grossiste en ligne britannique, 2009–2011)",
        "depot": "https://github.com/dsfsi/dsfsi-datasets",
        "commit": "Git LFS oid sha256:cd8933885509825c8e78db04d697c58e62909ded854c4084e094bd31f7e417cc",
        "chemin": "data/cos781/online_retail_II.csv.zip",
        "unite": "facture d'un client identifié",
    },
    "kickstarter": {
        "titre": "Campagnes Kickstarter, 2009–2018 (Mouillé, 2018)",
        "depot": "https://github.com/SohanChatterjee24/startup-sales-predictor",
        "commit": "Git LFS oid sha256:4846177ce8cfacd06a6acf06cba663b9aa5f5f77e7d0debecf5bdc861a87e3cb",
        "chemin": "data/raw/ks-projects-201801.csv",
        "unite": "campagne de financement participatif, objectif et date de fin affichés",
    },
}

HILLSTROM = {"zip_code": {"Urban": "u", "Surburban": "s", "Rural": "r"},
             "channel": {"Phone": "p", "Web": "w", "Multichannel": "m"},
             "segment": {"Mens E-Mail": "h", "Womens E-Mail": "f", "No E-Mail": "0"}}


def _r(v: str, nd: int) -> str:
    """Un nombre arrondi, vide s'il manque — l'extrait garde l'absence."""
    if v in ("", "nan", "NaN", "NA"):
        return ""
    x = round(float(v), nd)
    return str(int(x)) if nd == 0 else f"{x:.{nd}f}".rstrip("0").rstrip(".")


def _hillstrom() -> tuple[list[Path], str]:
    src = BRUT2 / "hillstrom.csv.gz"
    ent = ["recence", "historique", "hommes", "femmes", "zone", "nouveau", "canal",
           "courriel", "visite", "achat", "depense"]
    rows = []
    with gzip.open(src, "rt", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append([r["recency"], _r(r["history"], 2), r["mens"], r["womens"],
                         HILLSTROM["zip_code"][r["zip_code"]], r["newbie"],
                         HILLSTROM["channel"][r["channel"]], HILLSTROM["segment"][r["segment"]],
                         r["visit"], r["conversion"], _r(r["spend"], 2)])
    return [src], _csv(rows, ent)


LENTA_SEXE = {"Ж": "f", "М": "m"}


def _lenta() -> tuple[list[Path], str]:
    """Une ligne par client : le bras, la visite, et un historique résumé.

    Les dépenses et les reçus du jeu sont ventilés par groupe de produits : la
    dépense résumée est la somme des groupes publiés, les reçus le plus grand
    nombre de reçus d'un groupe (une borne basse des passages en caisse)."""
    src = BRUT2 / "lenta_dataset.csv.gz"
    ent = ["t", "y", "age", "sexe", "enfants", "format", "anciennete", "rep_sms", "rep_viber",
           "promo", "depense_12m", "depense_3m", "recus_12m", "recus_3m", "folies_12m"]
    rows = []
    with gzip.open(src, "rt", encoding="utf-8", newline="") as f:
        rd = csv.reader(f)
        tete = next(rd)
        col = {c: i for i, c in enumerate(tete)}
        s12 = [col[c] for c in tete if c.startswith("sale_sum_12m_g")]
        s3 = [col[c] for c in tete if c.startswith("sale_sum_3m_g")]
        c12 = [col[c] for c in tete if c.startswith("cheque_count_12m_g")]
        c3 = [col[c] for c in tete if c.startswith("cheque_count_3m_g")]

        def somme(r, idx):
            v = [float(r[i]) for i in idx if r[i] not in ("", "nan")]
            return str(round(sum(v))) if v else ""

        def maxi(r, idx):
            v = [float(r[i]) for i in idx if r[i] not in ("", "nan")]
            return str(int(max(v))) if v else ""

        for r in rd:
            rows.append([
                "1" if r[col["group"]] == "test" else "0", r[col["response_att"]],
                _r(r[col["age"]], 0), LENTA_SEXE.get(r[col["gender"]], "u"),
                _r(r[col["children"]], 0), _r(r[col["main_format"]], 0),
                _r(r[col["months_from_register"]], 0), _r(r[col["response_sms"]], 3),
                _r(r[col["response_viber"]], 3), _r(r[col["promo_share_15d"]], 3),
                somme(r, s12), somme(r, s3), maxi(r, c12), maxi(r, c3),
                _r(r[col["crazy_purchases_cheque_count_12m"]], 0)])
    return [src], _csv(rows, ent)


def _jours(a: datetime, b: datetime) -> str:
    return str((b - a).days)


def _x5() -> tuple[list[Path], str]:
    """Une ligne par client tiré au sort : bras, achat, et l'historique d'avant.

    L'historique est résumé à la fin des achats publiés (la date la plus
    récente du fichier) : récence et ancienneté en jours, nombre de passages
    en caisse distincts, dépense, passages payés en points « express » (les
    points des promotions). Une carte retirée ou un premier échange de points
    postérieurs à cette date ne sont pas des faits d'avant : ils sont vidés."""
    tr, cl, pu = (BRUT2 / "x5_uplift_train.csv.gz", BRUT2 / "x5_clients.csv.gz",
                  BRUT2 / "x5_purchases.csv.gz")
    with gzip.open(tr, "rt", encoding="utf-8", newline="") as f:
        bras = {r["client_id"]: (r["treatment_flg"], r["target"]) for r in csv.DictReader(f)}
    agg: dict[str, list] = {}
    fin = None
    vu: set[tuple[str, str]] = set()
    with gzip.open(pu, "rt", encoding="utf-8", newline="") as f:
        rd = csv.reader(f)
        tete = next(rd)
        c = {k: i for i, k in enumerate(tete)}
        ic, it, idt, isum, iexp = (c["client_id"], c["transaction_id"], c["transaction_datetime"],
                                   c["purchase_sum"], c["express_points_spent"])
        dernier = None
        for r in rd:
            d = r[idt]
            if fin is None or d > fin:
                fin = d
            cid = r[ic]
            if cid not in bras:
                continue
            cle = (cid, r[it])
            if cle == dernier or cle in vu:
                continue
            dernier = cle
            vu.add(cle)
            a = agg.setdefault(cid, [0, 0.0, d, d, 0])
            a[0] += 1
            a[1] += float(r[isum] or 0)
            if d < a[2]:
                a[2] = d
            if d > a[3]:
                a[3] = d
            if r[iexp] not in ("", "0", "0.0", "-0.0"):
                a[4] += 1
    t_fin = datetime.fromisoformat(fin)
    ent = ["t", "y", "age", "sexe", "carte_j", "points_j", "passages", "depense",
           "recence_j", "premier_j", "express"]
    rows = []
    with gzip.open(cl, "rt", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            cid = r["client_id"]
            if cid not in bras:
                continue
            t, y = bras[cid]
            carte = points = ""
            if r["first_issue_date"]:
                d = datetime.fromisoformat(r["first_issue_date"])
                carte = _jours(d, t_fin) if d <= t_fin else ""
            if r["first_redeem_date"]:
                d = datetime.fromisoformat(r["first_redeem_date"])
                points = _jours(d, t_fin) if d <= t_fin else ""
            a = agg.get(cid)
            if a:
                hist = [str(a[0]), str(round(a[1])), _jours(datetime.fromisoformat(a[3]), t_fin),
                        _jours(datetime.fromisoformat(a[2]), t_fin), str(a[4])]
            else:
                hist = ["0", "0", "", "", "0"]
            rows.append([t, y, r["age"], r["gender"].lower(), carte, points] + hist)
    rows.sort(key=lambda x: x[:])     # l'ordre du fichier brut ne dit rien : on le fixe
    return [tr, cl, pu], _csv(rows, ent) + f"# fin de l'historique : {fin}\n"


def _retail() -> tuple[list[Path], str]:
    """Une ligne par facture d'un client identifié : date, montant, annulation.

    Les numéros de client sont remplacés par leur rang d'apparition ; les
    libellés de produits ne sortent pas du brut."""
    src = BRUT2 / "online_retail_II.csv.zip"
    factures: dict[str, list] = {}
    rang: dict[str, int] = {}
    with zipfile.ZipFile(src) as z, z.open("online_retail_II.csv") as b:
        rd = csv.DictReader(io.TextIOWrapper(b, encoding="utf-8", newline=""))
        for r in rd:
            client = r["Customer ID"]
            if not client:
                continue
            client = str(int(float(client)))
            if client not in rang:
                rang[client] = len(rang) + 1
            f = factures.setdefault(r["Invoice"], [rang[client], r["InvoiceDate"][:16], 0.0, 0,
                                                   r["Invoice"].startswith("C"), r["Country"]])
            f[2] += float(r["Quantity"]) * float(r["Price"])
            f[3] += 1
    rows = [[f[0], f[1], f"{f[2]:.2f}", f[3], int(f[4]), f[5]] for f in factures.values()]
    rows.sort(key=lambda x: (x[0], x[1]))
    return [src], _csv(rows, ["client", "date", "montant", "lignes", "annulee", "pays"])


def _kickstarter() -> tuple[list[Path], str]:
    src = BRUT2 / "ks-projects-201801.csv"
    ent = ["categorie", "devise", "objectif", "objectif_usd", "promis_usd", "soutiens",
           "etat", "lance", "fin", "pays"]
    rows = []
    with open(src, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append([r["main_category"], r["currency"], r["goal"], r["usd_goal_real"],
                         r["usd_pledged_real"], r["backers"], r["state"], r["launched"][:13],
                         r["deadline"], r["country"]])
    rows.sort()
    return [src], _csv(rows, ent)


EXTRAITS = {"hillstrom": ("hillstrom.csv.gz", _hillstrom), "lenta": ("lenta.csv.gz", _lenta),
            "x5": ("x5.csv.gz", _x5), "retail": ("retail.csv.gz", _retail),
            "kickstarter": ("kickstarter.csv.gz", _kickstarter)}


def extraire(cles: list[str] | None = None) -> dict:
    """Relit les bruts et réécrit les extraits demandés et leur provenance."""
    prov = provenance() if PROVENANCE2.exists() else {}
    for cle in cles or list(EXTRAITS):
        nom, f = EXTRAITS[cle]
        brut, texte = f()
        cible = _ecrire_gz(nom, texte)
        info = dict(SOURCES2[cle])
        info["sha256_brut"] = [_sha(p) for p in brut]
        info["extrait"] = cible.name
        info["sha256_extrait"] = _sha(cible)
        prov[cle] = info
    PROVENANCE2.write_text(json.dumps(prov, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                           encoding="utf-8")
    return prov


# ---------------------------------------------------------------------------
# Lecture (sans réseau)
# ---------------------------------------------------------------------------

def _lignes(nom: str) -> list[dict]:
    with gzip.open(DOSSIER / nom, "rt", encoding="utf-8") as f:
        texte = f.read()
    corps = "\n".join(l for l in texte.splitlines() if not l.startswith("#"))
    return list(csv.DictReader(io.StringIO(corps)))


def _num(v: str) -> float | None:
    return float(v) if v != "" else None


@lru_cache(maxsize=1)
def hillstrom() -> tuple[dict, ...]:
    out = []
    for r in _lignes("hillstrom.csv.gz"):
        out.append({"recence": int(r["recence"]), "historique": float(r["historique"]),
                    "hommes": int(r["hommes"]), "femmes": int(r["femmes"]), "zone": r["zone"],
                    "nouveau": int(r["nouveau"]), "canal": r["canal"], "courriel": r["courriel"],
                    "visite": int(r["visite"]), "achat": int(r["achat"]),
                    "depense": float(r["depense"])})
    return tuple(out)


@lru_cache(maxsize=1)
def lenta() -> tuple[dict, ...]:
    out = []
    for r in _lignes("lenta.csv.gz"):
        d = {k: _num(v) for k, v in r.items() if k != "sexe"}
        d["t"], d["y"] = int(d["t"]), int(d["y"])
        d["sexe"] = r["sexe"]
        out.append(d)
    return tuple(out)


@lru_cache(maxsize=1)
def x5() -> tuple[dict, ...]:
    out = []
    for r in _lignes("x5.csv.gz"):
        d = {k: _num(v) for k, v in r.items() if k != "sexe"}
        d["t"], d["y"] = int(d["t"]), int(d["y"])
        d["sexe"] = r["sexe"]
        out.append(d)
    return tuple(out)


@lru_cache(maxsize=1)
def retail() -> tuple[tuple[int, str, float, int, int, str], ...]:
    return tuple((int(r["client"]), r["date"], float(r["montant"]), int(r["lignes"]),
                  int(r["annulee"]), r["pays"]) for r in _lignes("retail.csv.gz"))


@lru_cache(maxsize=1)
def kickstarter() -> tuple[dict, ...]:
    out = []
    for r in _lignes("kickstarter.csv.gz"):
        out.append({"categorie": r["categorie"], "devise": r["devise"],
                    "objectif": float(r["objectif"]), "objectif_usd": float(r["objectif_usd"]),
                    "promis_usd": float(r["promis_usd"]), "soutiens": int(r["soutiens"]),
                    "etat": r["etat"], "lance": r["lance"], "fin": r["fin"], "pays": r["pays"]})
    return tuple(out)


def provenance() -> dict:
    return json.loads(PROVENANCE2.read_text(encoding="utf-8"))


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
