"""Famille W — les baleines changent : les meilleurs fans de demain ne sont pas ceux d'aujourd'hui.

Toute la foule se dispute les gros dépensiers du moment ; les outils de gestion
les affichent en tête de liste. Sur trois marchés d'achats répétés (CDNOW,
Online Retail II, X5), on compte, parmi le 1 % des clients qui dépensent le
plus pendant la période de validation, la part qui n'étaient **pas** dans le
1 % de tête de la période d'apprentissage. Au-dessus de la moitié, la plupart
des baleines de demain viennent d'ailleurs que des baleines d'aujourd'hui.
"""

from __future__ import annotations

import math
from datetime import date
from functools import lru_cache

from . import registre4 as R4
from . import signaux
from .registre3 import COUPES
from .resultat import Resultat, entier

IDS = {"cdnow": "W01", "retail": "W02", "x5": "W03"}
MARCHE = signaux.MARCHE


def _ord(s: str) -> int:
    return date.fromisoformat(s).toordinal()


@lru_cache(maxsize=None)
def periodes(jeu: str, debut: str, coupe: str, fin: str) -> dict[int, tuple[float, int, float, int]]:
    """Par client : (dépense, jours d'achat) avant la coupe, puis après."""
    d0, d1, d2 = _ord(debut), _ord(coupe), _ord(fin)
    out = {}
    for c, js in signaux.jours(jeu).items():
        a = [x for x in js if d0 <= x[0] < d1]
        b = [x for x in js if d1 <= x[0] < d2]
        if a or b:
            out[c] = (sum(x[1] for x in a), len(a), sum(x[1] for x in b), len(b))
    return out


def _tete(p: dict, quand: int, part: float, classement: str) -> set[int]:
    """Le `part` de tête parmi les clients actifs de la période (0 : apprentissage, 1 : validation)."""
    i_dep, i_j = (0, 1) if quand == 0 else (2, 3)
    actifs = [c for c, v in p.items() if v[i_dep] > 0]
    if classement == "depense":
        ordre = sorted(actifs, key=lambda c: (-p[c][i_dep], c))
    else:
        ordre = sorted(actifs, key=lambda c: (-p[c][i_j], -p[c][i_dep], c))
    k = max(1, math.ceil(len(actifs) * part))
    return set(ordre[:k])


def _binomial_p(k: int, n: int) -> float:
    """p bilatérale exacte du test binomial contre 1/2."""
    def logc(j):
        return math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1) - n * math.log(2)
    obs = logc(k)
    return min(1.0, sum(math.exp(logc(j)) for j in range(n + 1) if logc(j) <= obs + 1e-9))


@lru_cache(maxsize=None)
def mesure(jeu: str, part: float = R4.BALEINE, classement: str = "depense", debut: str | None = None,
           coupe: str | None = None, fin: str | None = None) -> dict:
    d0, d1, d2 = debut or COUPES[jeu][0], coupe or COUPES[jeu][1], fin or COUPES[jeu][2]
    p = periodes(jeu, d0, d1, d2)
    avant, apres = _tete(p, 0, part, classement), _tete(p, 1, part, classement)
    nouveaux = len(apres - avant)
    n = len(apres)
    part_new = nouveaux / n
    # La concentration de la validation : part de la dépense tenue par le 1 % et le 10 % de tête,
    # et ce que gardent les baleines d'aujourd'hui.
    dep2 = sorted((v[2] for v in p.values() if v[2] > 0), reverse=True)
    tot2 = sum(dep2)

    def part_tete(q):
        return sum(dep2[:max(1, math.ceil(len(dep2) * q))]) / tot2

    dep1_tete = sum(p[c][0] for c in avant)
    dep1_tot = sum(v[0] for v in p.values())
    return {"part": part_new, "effet": (part_new - 0.5) * 100, "p": _binomial_p(nouveaux, n), "n": n,
            "nouveaux": nouveaux, "actifs_avant": sum(1 for v in p.values() if v[0] > 0),
            "actifs_apres": len(dep2), "tete1": part_tete(0.01), "tete10": part_tete(0.10),
            "garde_avant": dep1_tete / dep1_tot if dep1_tot else 0.0,
            "garde_apres": sum(p[c][2] for c in avant) / tot2}


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    out = {}
    for jeu, rid in IDS.items():
        m = mesure(jeu)
        se = math.sqrt(m["part"] * (1 - m["part"]) / m["n"]) * 100
        out[rid] = Resultat(
            id=rid, effet=m["effet"], ic=(m["effet"] - 1.96 * se, m["effet"] + 1.96 * se), p=m["p"], n=m["n"],
            unite="pt",
            lecture=(f"{MARCHE[jeu]} : {m['nouveaux']} des {m['n']} baleines de la validation n'en étaient pas "
                     f"avant ({m['part'] * 100:.0f} %) ; le 1 % de tête tient {m['tete1'] * 100:.0f} % de la "
                     f"dépense").replace(".", ","),
            methode="test binomial exact contre la moitié", extra=m)
    return out


@lru_cache(maxsize=1)
def batteries() -> dict[str, dict]:
    out = {}
    for jeu, rid in IDS.items():
        spec = [(mesure(jeu, q, c)["effet"], mesure(jeu, q, c)["p"]) for q in R4.W_PARTS for c in R4.W_CLASSEMENTS]
        temps, noms = [], []
        if jeu in signaux.GLISSANT:
            debut, coupes, duree = signaux.GLISSANT[jeu]
            for c in coupes:
                fin = date.fromordinal(_ord(c) + duree).isoformat()
                temps.append(mesure(jeu, R4.BALEINE, "depense", debut, c, fin)["effet"])
                noms.append(c)
        out[rid] = {"spec": spec, "spec_noms": [(q, c) for q in R4.W_PARTS for c in R4.W_CLASSEMENTS],
                    "temps": temps, "temps_noms": noms}
    return out


def main() -> None:
    for i, r in resultats().items():
        print(i, f"{r.effet:+.1f} pt p={r.p:.2e}", r.lecture, f"gardent {r.extra['garde_apres'] * 100:.0f} %")
    for i, b in batteries().items():
        print(i, [round(a, 1) for a, _ in b["spec"]], [round(x, 1) for x in b["temps"]])


if __name__ == "__main__":
    main()
