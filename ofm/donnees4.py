"""Les jeux de données du cahier nº 4 : un seul nouveau, l'Open Bandit Dataset.

ZOZOTOWN (mode en ligne, Japon) a mené pendant sept jours, du 24 au 30
novembre 2019, un test A/B entre deux politiques qui choisissent les articles
montrés : un **échantillonnage de Thompson** (qui apprend en continu quels
articles font cliquer) et le **hasard uniforme** (Saito, Aihara, Matsutani et
Narita). Le jeu complet compte 26 millions d'impressions ; son dépôt public
`st-tech/zr-obp` en porte un échantillon de 10 000 impressions par politique et
par campagne (tous les articles, hommes, femmes). C'est cet échantillon, figé
à un commit, qui entre ici. Le reste du cahier relit les extraits des nº 1 à 3
(Hillstrom, Lenta, X5, Kickstarter, CDNOW, Online Retail II).

Même règle que les autres modules `donnees*` : colonnes utiles seulement,
fichier compressé au bit près, empreintes SHA-256 du brut et de l'extrait dans
`PROVENANCE4.json`. L'empreinte de l'utilisateur (`user_feature_0`, déjà
hachée par ZOZO) est renumérotée : elle ne sert qu'à vérifier que le tirage au
sort a bien mélangé les mêmes clients dans les deux bras (le placebo de B).
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import os
from functools import lru_cache
from pathlib import Path

from .donnees import DOSSIER, _csv, _ecrire_gz, _sha
from .registre4 import CAMPAGNES, OBP_COMMIT

PROVENANCE4 = DOSSIER / "PROVENANCE4.json"
BRUT4 = Path(os.environ.get("OFM_BRUT4", "/home/user/donnees-ext4/zr-obp"))


def _obp() -> tuple[list[Path], str]:
    sources, lignes = [], []
    codes: dict[str, int] = {}
    for pol, lettre in (("random", "r"), ("bts", "b")):
        for camp in CAMPAGNES:
            src = BRUT4 / "obd" / pol / camp / f"{camp}.csv"
            sources.append(src)
            with open(src, encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    u = codes.setdefault(r["user_feature_0"], len(codes))
                    lignes.append([lettre, camp, r["timestamp"][:19], r["position"], r["item_id"], r["click"],
                                   f"{float(r['propensity_score']):.6g}", u])
    return sources, _csv(lignes, ["politique", "campagne", "horodatage", "position", "article", "clic",
                                  "propension", "u0"])


EXTRAITS = {"obp": ("obp.csv.gz", _obp)}
INFOS = {"obp": {"titre": "Open Bandit Dataset, échantillon public (Saito et al. ; ZOZOTOWN, 24–30 nov. 2019)",
                 "depot": "https://github.com/st-tech/zr-obp", "commit": OBP_COMMIT, "chemin": "obd/",
                 "unite": "impression : politique tirée au sort (Thompson ou hasard), article montré, clic"}}


def extraire(cles: list[str] | None = None) -> dict:
    prov = provenance() if PROVENANCE4.exists() else {}
    for cle in cles or list(EXTRAITS):
        nom, f = EXTRAITS[cle]
        brut, texte = f()
        cible = _ecrire_gz(nom, texte)
        info = dict(INFOS[cle])
        info["sha256_brut"] = [_sha(p) for p in brut]
        info["extrait"] = cible.name
        info["sha256_extrait"] = _sha(cible)
        prov[cle] = info
    PROVENANCE4.write_text(json.dumps(prov, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                           encoding="utf-8")
    return prov


@lru_cache(maxsize=1)
def obp() -> tuple[dict, ...]:
    with gzip.open(DOSSIER / "obp.csv.gz", "rt", encoding="utf-8") as f:
        rows = list(csv.DictReader(io.StringIO(f.read())))
    return tuple({"politique": r["politique"], "campagne": r["campagne"], "horodatage": r["horodatage"],
                  "position": int(r["position"]), "article": int(r["article"]), "clic": int(r["clic"]),
                  "propension": float(r["propension"]), "u0": int(r["u0"])} for r in rows)


def provenance() -> dict:
    return json.loads(PROVENANCE4.read_text(encoding="utf-8"))


def verifier() -> list[str]:
    return [cle for cle, info in provenance().items() if _sha(DOSSIER / info["extrait"]) != info["sha256_extrait"]]


if __name__ == "__main__":
    print(json.dumps(extraire(), ensure_ascii=False, indent=1))
