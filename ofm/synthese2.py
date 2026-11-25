"""La synthèse du cahier nº 2 : sa famille, sa correction, ses verdicts calculés.

Même mécanique que `synthese.py`, sur le registre nº 2 seul : les valeurs q
de Benjamini-Hochberg portent sur ses trente-huit tests, et le verdict découle
de la valeur q, du sens annoncé et du signe. Les deux paramètres déclarés
(`TRANSPOSITION`, `P_AGENCE`) sont ceux du cahier nº 1 : un effet mesuré
ailleurs se planifie chez soi à la moitié de sa taille, et le budget d'envois
se lit à un taux d'achat de 5 %.
"""

from __future__ import annotations

import math
from functools import lru_cache

from . import cibler, garder, objectif, registre2, relancer, stats
from .resultat import Resultat
from .synthese import P_AGENCE, SEUIL_Q, TRANSPOSITION


@lru_cache(maxsize=1)
def tous() -> dict[str, Resultat]:
    out: dict[str, Resultat] = {}
    for m in (relancer, cibler, garder, objectif):
        for k, v in m.resultats().items():
            if k in out:
                raise KeyError(f"identifiant en double : {k}")
            out[k] = v
    ids = [h.id for h in registre2.H]
    manquants, orphelins = set(ids) - set(out), set(out) - set(ids)
    if manquants or orphelins:
        raise KeyError(f"registre et résultats divergent : {manquants} {orphelins}")
    return {i: out[i] for i in ids}


@lru_cache(maxsize=1)
def q_valeurs() -> dict[str, float]:
    res = tous()
    ids = list(res)
    return dict(zip(ids, stats.bh([max(res[i].p, 1e-300) for i in ids])))


def verdict(i: str) -> str:
    h = registre2.par_id()[i]
    r = tous()[i]
    if q_valeurs()[i] >= SEUIL_Q:
        return "non établi"
    if h.sens == 0 or (r.effet > 0) == (h.sens > 0):
        return "tient"
    return "contraire"


def en_agence(i: str) -> str:
    h = registre2.par_id()[i]
    if verdict(i) == "contraire":
        return f"Le pari disait : « {h.ofm.rstrip('.')} ». Les données disent l'inverse."
    return h.ofm


def z_oriente(i: str) -> float:
    h = registre2.par_id()[i]
    r = tous()[i]
    z = abs(stats.Phi_inv(max(r.p, 1e-300) / 2))
    return z * (1.0 if r.effet >= 0 else -1.0) * (h.sens if h.sens != 0 else 1.0)


def budget(i: str) -> float | None:
    r = tous()[i]
    if r.relatif is None or not math.isfinite(r.relatif) or r.relatif == 0:
        return None
    plan = abs(r.relatif) * TRANSPOSITION
    if plan > 3:
        return None
    return stats.n_par_bras(P_AGENCE, plan)


def comptes() -> dict[str, int]:
    v = [verdict(i) for i in tous()]
    nominal = sum(1 for r in tous().values() if r.p < 0.05)
    return {"total": len(v), "tient": v.count("tient"), "contraire": v.count("contraire"),
            "non": v.count("non établi"), "nominal": nominal, "attendus_bruit": round(0.05 * len(v))}


def main() -> None:
    reg = registre2.par_id()
    q = q_valeurs()
    for i, r in tous().items():
        b = budget(i)
        print(f"{i} {verdict(i):10s} q={q[i]:.4f} z={z_oriente(i):+6.2f} "
              f"{'' if b is None else f'n={b:,.0f}':>12s}  {reg[i].enonce[:60]}")
    print(comptes())


if __name__ == "__main__":
    main()
