"""Fixer un objectif — 378 661 campagnes Kickstarter (2009–2018).

Une campagne affiche un objectif et une date de fin, puis des inconnus
promettent de l'argent. C'est la cagnotte d'un live : un palier annoncé
(« à 500, je… »), un compte à rebours, et des fans qui paient pour qu'il soit
atteint. Trois résultats publiés s'y revérifient : les promesses accélèrent à
l'approche de l'objectif (Kuppuswamy et Bayus, 2017), une campagne plus longue
et un objectif plus haut réussissent moins (Mollick, 2014).

Rien n'est tiré au sort ici : l'objectif et la durée sont choisis par le
porteur. Les comparaisons se font donc **à catégorie et année fixées**, et la
densité des fins de campagne se lit contre sa propre pente lisse (B01).
"""

from __future__ import annotations

import math
from datetime import date
from functools import lru_cache

from . import donnees2, stats
from .resultat import Resultat, entier


def _d(s: str) -> date:
    return date(int(s[:4]), int(s[5:7]), int(s[8:10]))


@lru_cache(maxsize=1)
def campagnes() -> tuple[dict, ...]:
    out = []
    for r in donnees2.kickstarter():
        if r["etat"] not in ("successful", "failed") or r["objectif_usd"] <= 0:
            continue
        duree = (_d(r["fin"]) - _d(r["lance"])).days
        if not 1 <= duree <= 92:
            continue
        lance = _d(r["lance"])
        out.append({"ok": 1.0 if r["etat"] == "successful" else 0.0,
                    "ratio": r["promis_usd"] / r["objectif_usd"],
                    "log_obj": math.log10(r["objectif_usd"]), "duree": duree,
                    "rond": 1.0 if r["objectif"] >= 1000 and r["objectif"] % 1000 == 0 else 0.0,
                    "weekend": 1.0 if lance.weekday() >= 5 else 0.0,
                    "strate": (r["categorie"], lance.year), "objectif_usd": r["objectif_usd"],
                    "soutiens": r["soutiens"], "categorie": r["categorie"], "annee": lance.year})
    return tuple(out)


def _compte(lo: float, hi: float) -> int:
    return sum(1 for c in campagnes() if lo <= c["ratio"] < hi)


@lru_cache(maxsize=1)
def entassement() -> dict:
    """B01 : l'excès juste au-dessus de l'objectif, contre la pente lisse voisine.

    Sous une densité lisse localement log-linéaire, le rapport des fenêtres
    intérieures [1 ; 1,05) / [0,95 ; 1) vaut la pente lue sur les fenêtres
    extérieures [1,05 ; 1,15) / [0,85 ; 0,95), à l'échelle de leurs centres
    (0,05 contre 0,20 d'écart). L'excès extérieur éventuel rend le test prudent."""
    ia, ib = _compte(1.00, 1.05), _compte(0.95, 1.00)
    oa, ob = _compte(1.05, 1.15), _compte(0.85, 0.95)
    L = math.log(ia / ib) - 0.25 * math.log(oa / ob)
    se = math.sqrt(1 / ia + 1 / ib + (1 / 16) * (1 / oa + 1 / ob))
    return {"L": L, "se": se, "ia": ia, "ib": ib, "oa": oa, "ob": ob}


def _fe(y: list[float], X: list[list[float]], strates: list) -> stats.Ajustement:
    """Moindres carrés à effets fixes (catégorie × année), par retrait des moyennes de strate."""
    groupes: dict = {}
    for i, s in enumerate(strates):
        groupes.setdefault(s, []).append(i)
    k = len(X[0])
    yd, Xd = list(y), [list(r) for r in X]
    for idx in groupes.values():
        my = sum(y[i] for i in idx) / len(idx)
        mx = [sum(X[i][j] for i in idx) / len(idx) for j in range(k)]
        for i in idx:
            yd[i] = y[i] - my
            Xd[i] = [X[i][j] - mx[j] for j in range(k)]
    return stats.mco(Xd, yd, [f"x{j}" for j in range(k)], grappes=None)


def _effet_fe(rid: str, cles: list[str], echelle: float, unite: str, lecture) -> Resultat:
    cs = campagnes()
    X = [[c[k] if k != "duree" else c["duree"] / 10.0 for k in cles] for c in cs]
    fit = _fe([c["ok"] for c in cs], X, [c["strate"] for c in cs])
    b, (lo, hi) = fit.b("x0"), fit.ic("x0")
    base = stats.moyenne(c["ok"] for c in cs)
    return Resultat(
        id=rid, effet=b * echelle, ic=(lo * echelle, hi * echelle), p=fit.p("x0"), n=len(cs),
        unite=unite, lecture=lecture(b, base),
        methode="probabilité linéaire à effets fixes catégorie × année, robuste",
        base=base, relatif=b / base,
    )


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    out = {}
    e = entassement()
    L, se = e["L"], e["se"]
    out["B01"] = Resultat(
        id="B01", effet=(math.exp(L) - 1) * 100,
        ic=((math.exp(L - 1.96 * se) - 1) * 100, (math.exp(L + 1.96 * se) - 1) * 100),
        p=stats.p_bilateral(L / se), n=e["ia"] + e["ib"] + e["oa"] + e["ob"], unite="%",
        lecture=(f"{entier(e['ia'])} campagnes finissent entre 100 et 105 % de leur objectif contre "
                 f"{entier(e['ib'])} entre 95 et 100 % ; la pente voisine en attendait un rapport de "
                 f"{math.exp(0.25 * math.log(e['oa'] / e['ob'])):.2f}").replace(".", ","),
        methode="rapport de comptes contre la pente log-linéaire des fenêtres voisines, loi de Poisson",
    )
    out["B02"] = _effet_fe("B02", ["duree", "log_obj"], 100, "pt",
                           lambda b, base: (f"chaque dizaine de jours de campagne en plus change la réussite de "
                                            f"{b * 100:+.2f} pt (base {base * 100:.1f} %)").replace(".", ","))
    out["B03"] = _effet_fe("B03", ["log_obj"], 100, "pt",
                           lambda b, base: (f"un objectif dix fois plus haut change la réussite de "
                                            f"{b * 100:+.2f} pt").replace(".", ","))
    out["B04"] = _effet_fe("B04", ["rond", "log_obj"], 100, "pt",
                           lambda b, base: (f"un objectif rond (multiple de 1 000) change la réussite de "
                                            f"{b * 100:+.2f} pt à objectif égal").replace(".", ","))
    out["B05"] = _effet_fe("B05", ["weekend", "log_obj"], 100, "pt",
                           lambda b, base: (f"un lancement le week-end change la réussite de "
                                            f"{b * 100:+.2f} pt à objectif égal").replace(".", ","))
    return out


def histogramme(lo: float = 0.5, hi: float = 1.5, pas: float = 0.02) -> list[tuple[float, int]]:
    """Comptes des fins de campagne par tranche de l'objectif atteint."""
    n = int(round((hi - lo) / pas))
    c = [0] * n
    for x in campagnes():
        k = int((x["ratio"] - lo) / pas)
        if 0 <= k < n and lo <= x["ratio"] < hi:
            c[k] += 1
    return [(lo + i * pas, v) for i, v in enumerate(c)]


def reussite_duree_objectif() -> tuple[list[list[float]], list[str], list[str]]:
    """Taux de réussite (%) par durée (lignes) et objectif (colonnes)."""
    durees = [(1, 20, "≤ 20 j"), (21, 29, "21–29 j"), (30, 30, "30 j"), (31, 45, "31–45 j"), (46, 92, "> 45 j")]
    objs = [(0, 3, "< 1 000 $"), (3, 4, "1 000–10 000"), (4, 5, "10 000–100 000"), (5, 99, "> 100 000")]
    z = []
    for a, b, _ in durees:
        ligne = []
        for lo, hi, _ in objs:
            sub = [c["ok"] for c in campagnes() if a <= c["duree"] <= b and lo <= c["log_obj"] < hi]
            ligne.append(100 * sum(sub) / len(sub) if sub else 0.0)
        z.append(ligne)
    return z, [d[2] for d in durees], [o[2] for o in objs]


def main() -> None:
    from .registre2 import par_id
    reg = par_id()
    print("campagnes", len(campagnes()), entassement())
    for i, r in resultats().items():
        print(f"{i} {reg[i].enonce[:55]:55s} {r.effet:+8.3f} {r.unite:3s} "
              f"[{r.ic[0]:+.3f}, {r.ic[1]:+.3f}] p={r.p:.2e}  {r.lecture}")


if __name__ == "__main__":
    main()
