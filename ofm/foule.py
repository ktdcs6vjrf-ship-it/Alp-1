"""Famille K — la foule : sortir en même temps que tout le monde, ou arriver le premier.

Kickstarter est un marché où des créateurs se disputent l'argent et l'attention
d'une même foule de soutiens, comme des créatrices se disputent les fans. Deux
questions :

- **K01, K02.** Une campagne lancée une semaine où sa catégorie est encombrée
  réussit-elle moins ? La foule se compte sur toutes les campagnes lancées à
  trois jours près ; elle se lit **à l'intérieur** de chaque case (catégorie,
  année, mois), une fois retirés le jour de la semaine, la taille de l'objectif
  et la durée : ce qui reste, c'est le hasard des calendriers d'une semaine à
  l'autre. K02 demande si c'est la foule de **sa** catégorie qui pèse, ou
  l'agitation de tout le site.
- **K03.** Quand Kickstarter ouvre un pays, les campagnes des 90 premiers jours
  réussissent-elles autrement que celles des deux années suivantes ? Le témoin
  est la même différence aux États-Unis, sur les mêmes dates (le site change
  pour tout le monde, pas seulement pour le pays qui ouvre).

La loi nulle de K01 est la permutation de la foule dans chaque case. Sa moyenne
et sa variance se calculent exactement (statistique linéaire permutée par
strate) ; sur 330 000 campagnes, sa forme est normale.
"""

from __future__ import annotations

import math
from datetime import date
from functools import lru_cache

from . import donnees2, stats
from . import registre4 as R4
from .resultat import Resultat, entier

DEB, FIN = date.fromisoformat(R4.K_DEBUT).toordinal(), date.fromisoformat(R4.K_FIN).toordinal()


def _jour(s: str) -> int | None:
    try:
        return date(int(s[:4]), int(s[5:7]), int(s[8:10])).toordinal()
    except ValueError:
        return None


@lru_cache(maxsize=1)
def campagnes() -> tuple[dict, ...]:
    """Toutes les campagnes datées, avec leur jour de lancement et de fin."""
    out = []
    for r in donnees2.kickstarter():
        a, b = _jour(r["lance"]), _jour(r["fin"])
        if a is None or b is None or a < date(2009, 1, 1).toordinal():
            continue
        out.append({**r, "j": a, "jf": b})
    return tuple(out)


@lru_cache(maxsize=1)
def lancements() -> dict[str, dict[int, int]]:
    """Par catégorie, le nombre de lancements par jour (tous états confondus)."""
    acc: dict[str, dict[int, int]] = {}
    for r in campagnes():
        d = acc.setdefault(r["categorie"], {})
        d[r["j"]] = d.get(r["j"], 0) + 1
    return acc


def _dans(par_jour: dict[int, int], a: int, b: int) -> int:
    return sum(par_jour.get(j, 0) for j in range(a, b + 1))


@lru_cache(maxsize=1)
def population() -> tuple[dict, ...]:
    """Les campagnes jugées : réussies ou échouées, dates, objectif et durée du registre."""
    out = []
    for r in campagnes():
        duree = r["jf"] - r["j"]
        if r["etat"] not in ("successful", "failed") or not DEB <= r["j"] < FIN:
            continue
        if r["objectif_usd"] <= 0 or not R4.K_DUREE[0] <= duree <= R4.K_DUREE[1]:
            continue
        out.append({**r, "duree": duree})
    return tuple(out)


@lru_cache(maxsize=None)
def foules(fenetre: int) -> dict[str, list[float]]:
    """Pour chaque campagne jugée : foule de sa catégorie, des autres catégories, et le placebo (+100 à +106 jours)."""
    lc = lancements()
    tous: dict[int, int] = {}
    for d in lc.values():
        for j, k in d.items():
            tous[j] = tous.get(j, 0) + k
    meme, autres, placebo = [], [], []
    a0, a1 = R4.K_PLACEBO
    for r in population():
        pj = lc[r["categorie"]]
        m = _dans(pj, r["j"] - fenetre, r["j"] + fenetre) - 1
        t = _dans(tous, r["j"] - fenetre, r["j"] + fenetre) - 1
        meme.append(math.log1p(m))
        autres.append(math.log1p(t - m))
        placebo.append(math.log1p(_dans(pj, r["j"] + a0, r["j"] + a1)))
    return {"meme": meme, "autres": autres, "placebo": placebo}


def _case(r: dict, quoi: str) -> tuple:
    d = date.fromordinal(r["j"])
    if quoi == "mois":
        return (r["categorie"], d.year, d.month)
    iso = d.isocalendar()
    return (r["categorie"], iso[0], iso[1])


def _issue(quoi: str) -> list[float]:
    if quoi == "reussite":
        return [100.0 if r["etat"] == "successful" else 0.0 for r in population()]
    return [math.log1p(r["soutiens"]) for r in population()]


def _demean(v: list[float], cases: list) -> list[float]:
    s: dict = {}
    n: dict = {}
    for x, c in zip(v, cases):
        s[c] = s.get(c, 0.0) + x
        n[c] = n.get(c, 0) + 1
    return [x - s[c] / n[c] for x, c in zip(v, cases)]


@lru_cache(maxsize=None)
def _controles(case_quoi: str) -> tuple[list[list[float]], list]:
    pop = population()
    cases = [_case(r, case_quoi) for r in pop]
    jsem = [date.fromordinal(r["j"]).weekday() for r in pop]
    cols = [[math.log(r["objectif_usd"]) for r in pop], [float(r["duree"]) for r in pop]]
    cols += [[1.0 if w == k else 0.0 for w in jsem] for k in range(1, 7)]
    return [_demean(c, cases) for c in cols], cases


def _resid(v: list[float], ctrl: list[list[float]]) -> list[float]:
    """Le reste de v après les contrôles (déjà centrés dans leur case)."""
    k = len(ctrl)
    xtx = [[sum(map(float.__mul__, ctrl[a], ctrl[b])) for b in range(k)] for a in range(k)]
    xty = [sum(map(float.__mul__, ctrl[a], v)) for a in range(k)]
    inv = stats.inverse(xtx)
    b = [sum(inv[a][c] * xty[c] for c in range(k)) for a in range(k)]
    out = list(v)
    for col, bj in zip(ctrl, b):
        out = [o - bj * x for o, x in zip(out, col)]
    return out


def _pente(ry: list[float], rx: list[float], cases: list) -> dict:
    """Pente de ry sur rx, écart-type robuste (HC0) et écart-type de la loi de permutation dans les cases."""
    sxx = sum(x * x for x in rx)
    beta = sum(map(float.__mul__, ry, rx)) / sxx
    e = [y - beta * x for y, x in zip(ry, rx)]
    se = math.sqrt(sum((x * u) ** 2 for x, u in zip(rx, e))) / sxx
    # Permutation de rx dans chaque case : moyenne nulle si rx est centré dans la case (presque), variance
    # Σ_c S_yy,c S_xx,c / (n_c − 1), le tout divisé par sxx².
    acc: dict = {}
    for y, x, c in zip(ry, rx, cases):
        a = acc.setdefault(c, [0, 0.0, 0.0, 0.0, 0.0])
        a[0] += 1
        a[1] += y
        a[2] += y * y
        a[3] += x
        a[4] += x * x
    var = 0.0
    for n, sy, syy, sx, sxx_c in acc.values():
        if n > 1:
            var += (syy - sy * sy / n) * (sxx_c - sx * sx / n) / (n - 1)
    sd_perm = math.sqrt(var) / sxx
    return {"beta": beta, "se": se, "sd_perm": sd_perm, "p": stats.p_bilateral(beta / sd_perm),
            "p_hc": stats.p_bilateral(beta / se), "n": len(rx)}


@lru_cache(maxsize=None)
def k01(fenetre: int = R4.K_FENETRE, issue: str = "reussite", case_quoi: str = "mois",
        variable: str = "meme") -> dict:
    ctrl, cases = _controles(case_quoi)
    f = foules(fenetre)
    ry = _resid(_demean(_issue(issue), cases), ctrl)
    rx = _resid(_demean(f[variable], cases), ctrl)
    return _pente(ry, rx, cases)


@lru_cache(maxsize=None)
def k02(fenetre: int = R4.K_FENETRE, issue: str = "reussite", case_quoi: str = "mois") -> dict:
    """Pentes des deux foules ensemble ; leur différence et un rééchantillonnage des semaines."""
    ctrl, cases = _controles(case_quoi)
    f = foules(fenetre)
    ry = _resid(_demean(_issue(issue), cases), ctrl)
    rm = _resid(_demean(f["meme"], cases), ctrl)
    ra = _resid(_demean(f["autres"], cases), ctrl)
    semaines = [date.fromordinal(r["j"]).isocalendar()[:2] for r in population()]
    acc: dict = {}
    for y, m, a, s in zip(ry, rm, ra, semaines):
        e = acc.setdefault(s, [0.0] * 5)
        e[0] += m * m
        e[1] += m * a
        e[2] += a * a
        e[3] += m * y
        e[4] += a * y
    blocs = list(acc.values())

    def coef(w):
        s = [sum(wi * b[k] for wi, b in zip(w, blocs)) for k in range(5)]
        det = s[0] * s[2] - s[1] * s[1]
        bm = (s[2] * s[3] - s[1] * s[4]) / det
        ba = (s[0] * s[4] - s[1] * s[3]) / det
        return bm, ba

    bm, ba = coef([1.0] * len(blocs))
    alea = stats.rng(f"k02-{fenetre}-{issue}-{case_quoi}")
    tir = []
    for _ in range(R4.TIRAGES):
        w = [0.0] * len(blocs)
        for _ in range(len(blocs)):
            w[int(alea.random() * len(blocs))] += 1.0
        m_, a_ = coef(w)
        tir.append(m_ - a_)
    d = bm - ba
    mt = sum(tir) / len(tir)
    se = math.sqrt(sum((v - mt) ** 2 for v in tir) / (len(tir) - 1))
    return {"beta_meme": bm, "beta_autres": ba, "d": d, "se": se, "p": stats.p_bilateral(d / se),
            "n": len(ry), "semaines": len(blocs)}


def _par_annee(fn) -> list[tuple[int, float]]:
    """La même pente, année de lancement par année (les cases sont déjà dans l'année)."""
    pop = population()
    annees = sorted({date.fromordinal(r["j"]).year for r in pop})
    return [(a, fn(a)) for a in annees]


@lru_cache(maxsize=None)
def k_annee(annee: int, variable: str) -> float:
    ctrl, cases = _controles("mois")
    f = foules(R4.K_FENETRE)
    garde = [date.fromordinal(r["j"]).year == annee for r in population()]
    ry = _resid(_demean(_issue("reussite"), cases), ctrl)
    rx = _resid(_demean(f["meme"], cases), ctrl)
    if variable == "d":
        ra = _resid(_demean(f["autres"], cases), ctrl)
        m = [x for x, g in zip(rx, garde) if g]
        a = [x for x, g in zip(ra, garde) if g]
        y = [x for x, g in zip(ry, garde) if g]
        s = [sum(map(float.__mul__, u, v)) for u, v in ((m, m), (m, a), (a, a), (m, y), (a, y))]
        det = s[0] * s[2] - s[1] * s[1]
        return (s[2] * s[3] - s[1] * s[4]) / det - (s[0] * s[4] - s[1] * s[3]) / det
    x = [v for v, g in zip(rx, garde) if g]
    y = [v for v, g in zip(ry, garde) if g]
    return sum(map(float.__mul__, x, y)) / sum(v * v for v in x)


# ---------------------------------------------------------------------------
# K03 : les pionniers d'un pays qui ouvre
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def ouvertures() -> dict[str, int]:
    premier: dict[str, int] = {}
    for r in campagnes():
        if r["pays"] in ("US", 'N,0"'):
            continue
        premier[r["pays"]] = min(premier.get(r["pays"], 10 ** 9), r["j"])
    limite = date.fromisoformat(R4.OUVERTURE_AVANT).toordinal()
    return {p: j for p, j in sorted(premier.items(), key=lambda x: x[1]) if j < limite}


def _taux(rows) -> tuple[int, int]:
    return len(rows), sum(1 for r in rows if r["etat"] == "successful")


@lru_cache(maxsize=None)
def k03(pionniers: int = R4.PIONNIERS, suivants: int = R4.SUIVANTS, decalage: int = 0,
        vague: str | None = None) -> dict:
    """Différence pionniers − suivants dans chaque pays, moins la même aux États-Unis, pondérée par les pionniers."""
    pop = population()
    par_pays: dict[str, list[dict]] = {}
    for r in pop:
        par_pays.setdefault(r["pays"], []).append(r)
    us = par_pays.get("US", [])
    limite_vague = date.fromisoformat(R4.K_VAGUE).toordinal()
    cellules = []
    for pays, o in ouvertures().items():
        if vague == "1" and o >= limite_vague or vague == "2" and o < limite_vague:
            continue
        o2 = o + decalage
        fen = ((o2, o2 + pionniers), (o2 + pionniers, o2 + suivants))
        rows = par_pays.get(pays, [])
        e = _taux([r for r in rows if fen[0][0] <= r["j"] < fen[0][1]])
        l_ = _taux([r for r in rows if fen[1][0] <= r["j"] < fen[1][1]])
        E = _taux([r for r in us if fen[0][0] <= r["j"] < fen[0][1]])
        L = _taux([r for r in us if fen[1][0] <= r["j"] < fen[1][1]])
        if min(e[0], l_[0], E[0], L[0]) == 0:
            continue
        cellules.append((pays, e, l_, E, L))

    def did(cel):
        num = den = 0.0
        for _, e, l_, E, L in cel:
            w = e[0]
            num += w * ((e[1] / e[0] - l_[1] / l_[0]) - (E[1] / E[0] - L[1] / L[0]))
            den += w
        return 100.0 * num / den

    d = did(cellules)
    alea = stats.rng(f"k03-{pionniers}-{suivants}-{decalage}-{vague}")
    tir = []
    for _ in range(R4.TIRAGES):
        sim = []
        for pays, *cs in cellules:
            sim.append((pays, *[(n, alea.binomialvariate(n, s / n)) for n, s in cs]))
        tir.append(did(sim))
    mt = sum(tir) / len(tir)
    se = math.sqrt(sum((v - mt) ** 2 for v in tir) / (len(tir) - 1))
    return {"d": d, "se": se, "p": stats.p_bilateral(d / se) if se > 0 else 1.0, "pays": len(cellules),
            "pionniers": sum(c[1][0] for c in cellules), "suivants": sum(c[2][0] for c in cellules),
            "cellules": [(p, e, l_, E, L) for p, e, l_, E, L in cellules]}


# ---------------------------------------------------------------------------
# Résultats et batteries
# ---------------------------------------------------------------------------

def _spec_k(fn) -> tuple[list, list]:
    out, noms = [], []
    for f in R4.K_FENETRES:
        for i in R4.K_ISSUES:
            for c in R4.K_CASES:
                r = fn(f, i, c)
                out.append((r["beta"] if "beta" in r else r["d"], r["p"]))
                noms.append((f, i, c))
    return out, noms


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    a = k01()
    b = k02()
    c = k03()
    pop = population()
    out = {
        "K01": Resultat(id="K01", effet=a["beta"], ic=(a["beta"] - 1.96 * a["sd_perm"], a["beta"] + 1.96 * a["sd_perm"]),
                        p=a["p"], n=a["n"], unite="pt",
                        lecture=(f"{a['beta']:+.2f} point de réussite par unité de log de la foule de la catégorie, "
                                 f"soit {a['beta'] * math.log(2):+.2f} point quand elle double "
                                 f"({entier(len(pop))} campagnes)").replace(".", ","),
                        methode="pente dans la case catégorie × mois, contrôles retirés ; permutation dans la case",
                        extra={"se_hc": a["se"], "p_hc": a["p_hc"]}),
        "K02": Resultat(id="K02", effet=b["d"], ic=(b["d"] - 1.96 * b["se"], b["d"] + 1.96 * b["se"]), p=b["p"],
                        n=b["n"], unite="pt",
                        lecture=(f"foule de la catégorie {b['beta_meme']:+.2f}, foule des autres {b['beta_autres']:+.2f} "
                                 f"point par unité de log ({b['semaines']} semaines rééchantillonnées)").replace(".", ","),
                        methode="deux foules dans le même modèle ; rééchantillonnage des semaines de lancement",
                        extra={"beta_meme": b["beta_meme"], "beta_autres": b["beta_autres"]}),
        "K03": Resultat(id="K03", effet=c["d"], ic=(c["d"] - 1.96 * c["se"], c["d"] + 1.96 * c["se"]), p=c["p"],
                        n=c["pionniers"] + c["suivants"], unite="pt",
                        lecture=(f"pionniers moins suivants, témoin américain retiré : {c['d']:+.1f} points de réussite "
                                 f"({c['pays']} pays, {entier(c['pionniers'])} campagnes pionnières)").replace(".", ","),
                        methode="différence de différences ; rééchantillonnage des campagnes",
                        extra={"pays": c["pays"], "pionniers": c["pionniers"]}),
    }
    return out


@lru_cache(maxsize=1)
def batteries() -> dict[str, dict]:
    s1, n1 = _spec_k(k01)
    s2, n2 = _spec_k(k02)
    pl = k01(variable="placebo")
    ann1 = _par_annee(lambda a: k_annee(a, "meme"))
    ann2 = _par_annee(lambda a: k_annee(a, "d"))
    s3 = [(lambda r: (r["d"], r["p"]))(k03(p, s)) for p in R4.K_PIONNIERS for s in R4.K_SUIVANTS]
    pl3 = k03(decalage=R4.K_FAUSSE_OUVERTURE)
    v1, v2 = k03(vague="1"), k03(vague="2")
    return {
        "K01": {"spec": s1, "spec_noms": n1, "placebo": (pl["beta"], pl["p"]), "temps": [v for _, v in ann1],
                "temps_noms": [a for a, _ in ann1]},
        "K02": {"spec": s2, "spec_noms": n2, "temps": [v for _, v in ann2], "temps_noms": [a for a, _ in ann2]},
        "K03": {"spec": s3, "spec_noms": [(p, s) for p in R4.K_PIONNIERS for s in R4.K_SUIVANTS],
                "placebo": (pl3["d"], pl3["p"]), "temps": [v1["d"], v2["d"]], "temps_noms": ["vague 1", "vague 2"],
                "pays": k03()["cellules"]},
    }


def main() -> None:
    for i, r in resultats().items():
        print(i, f"{r.effet:+.3f} [{r.ic[0]:+.3f}, {r.ic[1]:+.3f}] p={r.p:.2e}", r.lecture)
    b = batteries()
    for i, v in b.items():
        print(i, "spec", [(round(a, 2), round(p, 3)) for a, p in v["spec"]])
        print("   temps", [round(x, 2) for x in v["temps"]], "placebo", v.get("placebo"))


if __name__ == "__main__":
    main()
