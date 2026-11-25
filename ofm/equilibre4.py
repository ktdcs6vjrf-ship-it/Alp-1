"""L'équilibre des trois expériences de la famille A : les groupes se ressemblent-ils avant le message ?

C'est le contrôle que le placebo de A02 et A08 a fait apparaître : sur Lenta,
le message semblait « changer » le sexe des clients, ce qui est impossible. On
compare donc les deux bras sur tout ce qui est connu **avant** l'envoi : l'écart
standardisé (en écarts-types) et son z. Un tirage au sort bien fait donne des
écarts standardisés de l'ordre du centième ; sur Lenta, la réponse passée aux
SMS diffère de deux dixièmes d'écart-type. Ce contrôle n'était pas déclaré dans
le registre : il est rapporté comme un constat, sans verdict.
"""

from __future__ import annotations

import math
from functools import lru_cache

from . import avances


@lru_cache(maxsize=None)
def equilibre(jeu: str) -> dict[str, tuple[float, float]]:
    d = avances.donnees(jeu)
    t = d["t"]
    out = {}
    for var in d["noms"]:
        x = d["X"][var]
        g1 = [v for v, ti in zip(x, t) if ti and v is not None]
        g0 = [v for v, ti in zip(x, t) if not ti and v is not None]
        m1, m0 = sum(g1) / len(g1), sum(g0) / len(g0)
        s1 = math.sqrt(sum((v - m1) ** 2 for v in g1) / len(g1))
        s0 = math.sqrt(sum((v - m0) ** 2 for v in g0) / len(g0))
        if s1 == 0 and s0 == 0:
            continue
        std = (m1 - m0) / math.sqrt((s1 ** 2 + s0 ** 2) / 2)
        z = (m1 - m0) / math.sqrt(s1 ** 2 / len(g1) + s0 ** 2 / len(g0))
        out[var] = (std, z)
    return out


def pire(jeu: str) -> tuple[str, float, float]:
    e = equilibre(jeu)
    v = max(e, key=lambda k: abs(e[k][0]))
    return v, e[v][0], e[v][1]


if __name__ == "__main__":
    for j in avances.JEUX:
        print(j, pire(j), {k: (round(a, 4), round(b, 2)) for k, (a, b) in equilibre(j).items()})
