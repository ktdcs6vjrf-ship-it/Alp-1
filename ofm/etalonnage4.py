"""L'étalonnage du cahier nº 4 sur vérité connue, rangé dans `ofm/donnees/ETALONNAGE4.json`.

Avant de croire la batterie sur des données réelles, on la fait tourner sur des
données dont on connaît la réponse : des tests tous nuls (aucun ne devrait
conclure plus de 5 fois sur 100), et de vrais avantages (ils devraient être
vus). Le calcul prend une dizaine de minutes ; la page relit le fichier, et un
test vérifie qu'une version courte redonne les mêmes ordres de grandeur.

    python -m ofm.etalonnage4
"""

from __future__ import annotations

import json
from pathlib import Path

from . import avances, stress

CIBLE = Path(__file__).resolve().parent / "donnees" / "ETALONNAGE4.json"


def calculer() -> dict:
    return {
        "holm": stress.etalonner_holm(),
        "dsr": stress.etalonner_dsr(),
        "cscv_nul": stress.etalonner_cscv(),
        "cscv_avance": stress.etalonner_cscv(avance=1.0),
        "spa_nul": stress.etalonner_spa(essais=400, G=500),
        "spa_avance": stress.etalonner_spa(essais=100, effet=3.0),
        "a_nul": avances.etalonner(300, False),
        "a_heterogene": avances.etalonner(300, True),
    }


def lire() -> dict:
    return json.loads(CIBLE.read_text(encoding="utf-8"))


def main() -> None:
    out = calculer()
    CIBLE.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
