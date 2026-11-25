"""Famille R — l'accélération, le meilleur signal du nº 3, passée à toute la batterie.

La mesure principale est celle de S07–S09 (`signaux.mesure`), à l'identique :
elle ne dit rien de neuf. Ce qui est neuf :

- **la courbe de spécification** : trois définitions de l'accélération
  (moitiés des écarts, tiers, dernier écart contre les précédents) × trois
  seuils d'achats (3, 4, 5 jours) × deux issues (dépense, jours d'achat) ;
- **le placebo** : les écarts de chaque client mélangés entre eux. Récence,
  fréquence, montant et ancienneté ne bougent pas (le premier et le dernier
  achat restent en place) ; seul l'ordre disparaît, et avec lui l'accélération ;
- **SPA et CSCV** sur les signaux du nº 3 : l'accélération a été retenue parce
  qu'elle était la meilleure de cinq. L'avoir choisie après coup se paie-t-il ?
- **le temps** : les sept coupes glissantes du nº 3 (CDNOW, Online Retail II),
  et le Sharpe dégonflé de la série de leurs effets.
"""

from __future__ import annotations

import math
import zlib
from datetime import date
from functools import lru_cache

from . import registre4 as R4
from . import signaux, stats, stress
from .registre3 import COUPES, SIGNAUX
from .resultat import Resultat, entier

IDS = {"cdnow": "R01", "retail": "R02", "x5": "R03"}


def _ord(s: str) -> int:
    return date.fromisoformat(s).toordinal()


def variante(t: list[int], definition: str) -> float | None:
    ecarts = [b - a for a, b in zip(t, t[1:])]
    if len(ecarts) < 2 or min(ecarts) <= 0:
        return None
    if definition == "moities":
        return signaux.acceleration(t)
    if definition == "tiers":
        h = max(1, len(ecarts) // 3)
        return math.log((sum(ecarts[:h]) / h) / (sum(ecarts[-h:]) / h))
    return math.log((sum(ecarts[:-1]) / (len(ecarts) - 1)) / ecarts[-1])


@lru_cache(maxsize=None)
def lignes(jeu: str) -> tuple[dict, ...]:
    """Les clients d'au moins deux jours d'achat d'apprentissage : RFM, jours d'achat et deux issues."""
    d0, d1, d2 = (_ord(x) for x in COUPES[jeu])
    dern = d1 - 1
    out = []
    for c, js in signaux.jours(jeu).items():
        cal = [x for x in js if d0 <= x[0] < d1]
        if len(cal) < 2:
            continue
        prem = cal[0][0]
        F = len(cal)
        out.append({"client": c, "R": dern - cal[-1][0], "F": F, "M": sum(x[1] for x in cal) / F, "T": dern - prem,
                    "t": tuple(x[0] - prem for x in cal),
                    "depense": sum(x[1] for x in js if d1 <= x[0] < d2),
                    "jours": float(sum(1 for x in js if d1 <= x[0] < d2))})
    out.sort(key=lambda r: r["client"])
    return tuple(out)


def _ic(rows: list[dict], tirages: int, nom: str) -> dict:
    return signaux.ic_partiel(rows, "sig", tirages=tirages, nom=nom)


@lru_cache(maxsize=None)
def spec(jeu: str) -> tuple[list, list]:
    out, noms = [], []
    for definition in R4.R_DEFINITIONS:
        for seuil in R4.R_SEUILS:
            for issue in R4.R_ISSUES:
                rows = []
                for r in lignes(jeu):
                    if r["F"] < seuil:
                        continue
                    v = variante(list(r["t"]), definition)
                    if v is None:
                        continue
                    rows.append({**r, "sig": v, "y": r[issue]})
                m = _ic(rows, R4.R_TIRAGES_SPEC, f"r-spec-{jeu}-{definition}-{seuil}-{issue}")
                out.append((m["effet"], m["p"]))
                noms.append((definition, seuil, issue))
    return out, noms


@lru_cache(maxsize=None)
def placebo(jeu: str) -> dict:
    """Les écarts de chaque client mélangés : même RFM, plus d'ordre."""
    alea = stats.rng(f"r-placebo-{jeu}")
    rows = []
    for r in lignes(jeu):
        if r["F"] < 3:
            continue
        e = [b - a for a, b in zip(r["t"], r["t"][1:])]
        alea.shuffle(e)
        t = [0]
        for x in e:
            t.append(t[-1] + x)
        v = signaux.acceleration(t)
        if v is not None:
            rows.append({**r, "sig": v, "y": r["depense"]})
    m = _ic(rows, R4.TIRAGES, f"r-placebo-ic-{jeu}")
    return {"effet": m["effet"], "p": m["p"], "n": m["n"]}


@lru_cache(maxsize=None)
def concurrents(jeu: str) -> dict:
    """Les signaux du nº 3 sur un échantillon commun (au moins trois jours d'achat) : SPA et CSCV."""
    commun = {r["client"] for r in signaux.table(jeu) if r["acceleration"] is not None}
    base_rows = [r for r in signaux.table(jeu) if r["client"] in commun]
    noms = list(SIGNAUX[jeu])
    effets, influences, par_bloc = [], [], []
    clients = [r["client"] for r in base_rows]
    groupe = [zlib.crc32(str(c).encode()) % R4.GROUPES for c in clients]
    bloc = [zlib.crc32(f"b{c}".encode()) % R4.BLOCS for c in clients]
    n = len(base_rows)
    for s in noms:
        rows = [{**r, "sig": r[s]} for r in base_rows]
        m = _ic(rows, R4.R_TIRAGES_SPEC, f"r-spa-{jeu}-{s}")
        fr, yr = m["reste_signal"], m["reste_y"]
        sx = math.sqrt(sum(x * x for x in fr) / n)
        sy = math.sqrt(sum(y * y for y in yr) / n)
        zx, zy = [x / sx for x in fr], [y / sy for y in yr]
        rho = m["rho"]
        inf = [0.0] * R4.GROUPES
        for a, b, g in zip(zx, zy, groupe):
            inf[g] += (a * b - rho * (a * a + b * b) / 2) / n
        effets.append(m["effet"])
        influences.append(inf)
        sb = [[0.0, 0.0, 0.0] for _ in range(R4.BLOCS)]
        for x, y, k in zip(fr, yr, bloc):
            sb[k][0] += x * y
            sb[k][1] += x * x
            sb[k][2] += y * y
        par_bloc.append([v[0] / math.sqrt(v[1] * v[2]) - m["centre"] for v in sb])
    sp = stress.spa(effets, influences, R4.TIRAGES, f"r-{jeu}")
    cs = stress.cscv(par_bloc)
    return {"noms": noms, "effets": effets, "spa": sp, "cscv": {k: cs[k] for k in ("pbo", "perte", "combinaisons")},
            "n": n, "choisi": noms[max(range(len(noms)), key=lambda k: effets[k])]}


@lru_cache(maxsize=None)
def temps(jeu: str) -> dict:
    if jeu not in signaux.GLISSANT:
        return {"serie": [], "noms": [], "dsr": None}
    g = signaux.glissant(jeu)
    serie = [ligne["acceleration"][0] for ligne in g]
    srs = []
    for s in SIGNAUX[jeu]:
        x = [ligne[s][0] for ligne in g]
        m, sd, *_ = stress.moments(x)
        if sd > 0:
            srs.append(m / sd)
    mm = sum(srs) / len(srs)
    var = sum((v - mm) ** 2 for v in srs) / (len(srs) - 1)
    return {"serie": serie, "noms": [ligne["coupe"] for ligne in g],
            "dsr": stress.dsr(serie, 5, var), "var_sr": var}


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    out = {}
    for jeu, rid in IDS.items():
        m = signaux.mesure("acceleration", jeu)
        out[rid] = Resultat(
            id=rid, effet=m["effet"], ic=m["ic"], p=m["p"], n=m["n"], unite="r",
            lecture=(f"{signaux.MARCHE[jeu]} : IC partiel {m['effet']:+.3f} au-delà de RFM "
                     f"({entier(m['n'])} clients ; mesure de S{7 + list(IDS).index(jeu):02d} du nº 3)").replace(".", ","),
            methode="IC partiel des rangs, RFM retiré ; restes mélangés dans les cases RFM")
    return out


@lru_cache(maxsize=1)
def batteries() -> dict[str, dict]:
    out = {}
    for jeu, rid in IDS.items():
        s, noms = spec(jeu)
        c = concurrents(jeu)
        t = temps(jeu)
        out[rid] = {"spec": s, "spec_noms": noms, "placebo": (placebo(jeu)["effet"], placebo(jeu)["p"]),
                    "spa": c["spa"], "cscv": c["cscv"], "concurrents": {k: c[k] for k in ("noms", "effets", "choisi")},
                    "temps": t["serie"], "temps_noms": t["noms"], "dsr": t["dsr"]}
    return out


def main() -> None:
    for i, r in resultats().items():
        b = batteries()[i]
        print(i, f"{r.effet:+.4f} p={r.p:.3f}", r.lecture)
        print("   spec", [round(a, 3) for a, _ in b["spec"]])
        print("   placebo", b["placebo"], "spa", round(b["spa"]["p_spa"], 3), "cscv", b["cscv"])
        print("   temps", [round(x, 3) for x in b["temps"]], "dsr", b["dsr"] and round(b["dsr"]["dsr"], 3))


if __name__ == "__main__":
    main()
