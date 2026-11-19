"""La synthèse : toutes les hypothèses, une seule correction, des verdicts calculés.

Les modules de famille rendent chacun leurs résultats. Celui-ci les rassemble
dans l'ordre du registre, applique Benjamini-Hochberg à la **famille entière**
— cinquante-neuf tests, pas sept — et calcule le verdict. Aucun verdict n'est
écrit à la main : il découle de la valeur q, du sens annoncé et du signe.

Deux paramètres sont **déclarés**, et jamais dérivés de ce qu'ils servent à
évaluer :

- `TRANSPOSITION = 1/2` — un effet mesuré ailleurs se planifie chez soi à la
  moitié de sa taille. C'est l'ordre de grandeur des réplications (Open
  Science Collaboration, 2015 : effets répliqués moitié moindres) et il reste
  optimiste face aux unités de « nudge » (DellaVigna et Linos, 2022 : 1,4 point
  à l'échelle contre 8,7 dans les revues).
- `P_AGENCE = 5 %` — le taux d'achat d'un message groupé, pour convertir un
  effet relatif en budget d'envois. Il est illustratif : chaque agence doit y
  mettre le sien, et la surface du budget se lit à toutes les bases.
"""

from __future__ import annotations

import math
from functools import lru_cache

from . import (calendrier, choisir, demander, negocier, offrir, persuader, registre,
               revenir, stats)
from .resultat import Resultat

TRANSPOSITION = 0.5
P_AGENCE = 0.05
ENVOIS_SEMAINE = 3000      # par variante : 2 000 fans × 3 messages, coupés en deux
SEUIL_Q = 0.05


@lru_cache(maxsize=1)
def tous() -> dict[str, Resultat]:
    out: dict[str, Resultat] = {}
    for m in (demander, offrir, persuader, negocier, choisir, revenir, calendrier):
        for k, v in m.resultats().items():
            if k in out:
                raise KeyError(f"identifiant en double : {k}")
            out[k] = v
    ids = [h.id for h in registre.H]
    manquants = set(ids) - set(out)
    orphelins = set(out) - set(ids)
    if manquants or orphelins:
        raise KeyError(f"registre et résultats divergent : {manquants} {orphelins}")
    return {i: out[i] for i in ids}


@lru_cache(maxsize=1)
def q_valeurs() -> dict[str, float]:
    res = tous()
    ids = list(res)
    q = stats.bh([max(res[i].p, 1e-300) for i in ids])
    return dict(zip(ids, q))


def verdict(i: str) -> str:
    h = registre.par_id()[i]
    r = tous()[i]
    if q_valeurs()[i] >= SEUIL_Q:
        return "non établi"
    if h.sens == 0 or (r.effet > 0) == (h.sens > 0):
        return "tient"
    return "contraire"


def z_oriente(i: str) -> float:
    """z signé dans le sens annoncé (positif = va dans le sens du pari)."""
    h = registre.par_id()[i]
    r = tous()[i]
    z = abs(stats.Phi_inv(max(r.p, 1e-300) / 2))
    signe = 1.0 if r.effet >= 0 else -1.0
    return z * signe * (h.sens if h.sens != 0 else 1.0)


def budget(i: str) -> float | None:
    """Envois par variante pour revérifier l'effet chez soi, à base et taille déclarées."""
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
            "non": v.count("non établi"), "nominal": nominal,
            "attendus_bruit": round(0.05 * len(v))}


def classement() -> list[tuple[str, float, float | None]]:
    """Les effets qui tiennent, du plus vite vérifiable au plus lent."""
    out = []
    for i in tous():
        if verdict(i) in ("tient", "contraire"):
            out.append((i, z_oriente(i), budget(i)))
    return sorted(out, key=lambda t: (t[2] is None, t[2] or 0.0, -abs(t[1])))


def main() -> None:
    reg = registre.par_id()
    q = q_valeurs()
    for i, r in tous().items():
        b = budget(i)
        print(f"{i} {verdict(i):10s} q={q[i]:.4f} z={z_oriente(i):+6.2f} "
              f"{'' if b is None else f'n={b:,.0f}':>12s}  {reg[i].enonce[:55]}")
    print(comptes())


if __name__ == "__main__":
    main()
