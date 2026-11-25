"""Répondre à une offre — l'expérience de Karlan et List (2007).

50 083 anciens donateurs d'une association américaine ont reçu une lettre
dont le contenu était **tiré au sort** : sans contrepartie (témoin), ou avec un
donateur qui double, triple ou quadruple chaque don (1:1, 2:1, 3:1), un
plafond annoncé de 25 000 à 100 000 $, et un montant suggéré égal à 1, 1,25 ou
1,5 fois le plus gros don passé. C'est le seul jeu du document où l'effet est
**causal** par construction : le tirage au sort fait la loi nulle.

Le parallèle avec une agence est direct. Une contrepartie est un bonus
attaché à l'achat (« un contenu offert pour un acheté »), son ratio est la
générosité du bonus, le montant suggéré est le prix proposé d'un pourboire.
"""

from __future__ import annotations

import math
from functools import lru_cache

from . import donnees, stats
from .resultat import Resultat, entier


def _pct(v: float, nd: int = 2) -> str:
    return f"{v * 100:.{nd}f}".replace(".", ",") + " %"


def _dol(v: float) -> str:
    return f"{v:.2f}".replace(".", ",") + " $"


def _taux(rows) -> tuple[int, int]:
    rows = list(rows)
    return int(sum(r["gave"] for r in rows)), len(rows)


def _prop(rid: str, a, b, quoi: str) -> Resultat:
    xa, na = _taux(a)
    xb, nb = _taux(b)
    e = stats.deux_proportions(xa, na, xb, nb)
    lo, hi = e.ic()
    return Resultat(
        id=rid, effet=e.diff * 100, ic=(lo * 100, hi * 100), p=e.p, n=na + nb,
        unite="pt", lecture=f"{_pct(e.a)} contre {_pct(e.b)} ({quoi})",
        methode="écart de proportions, tirage au sort", base=e.b,
        relatif=e.relatif, extra={"a": e.a, "b": e.b, "na": na, "nb": nb},
    )


def _moy(rid: str, a, b, quoi: str) -> Resultat:
    a, b = [r["amount"] for r in a], [r["amount"] for r in b]
    e = stats.deux_moyennes(a, b)
    lo, hi = e.ic()
    return Resultat(
        id=rid, effet=e.diff, ic=(lo, hi), p=e.p, n=len(a) + len(b), unite="$",
        lecture=(f"{_dol(e.a)} contre {_dol(e.b)} en moyenne, médianes "
                 f"{_dol(stats.quantile(a, .5))} et {_dol(stats.quantile(b, .5))} ({quoi})"),
        methode="écart de moyennes (Welch), donateurs seulement", base=e.b,
        relatif=e.relatif,
    )


def _interaction(rid: str, rows, cle, quoi: str) -> Resultat:
    rows = [r for r in rows if cle(r) is not None]
    X = [[1.0, r["treatment"], cle(r), r["treatment"] * cle(r)] for r in rows]
    fit = stats.mco(X, [r["gave"] for r in rows], ["c", "t", "g", "tg"])
    lo, hi = fit.ic("tg")
    t0 = [r for r in rows if cle(r) == 0]
    t1 = [r for r in rows if cle(r) == 1]

    def eff(sub):
        xa, na = _taux(r for r in sub if r["treatment"] == 1)
        xb, nb = _taux(r for r in sub if r["treatment"] == 0)
        return xa / na - xb / nb

    return Resultat(
        id=rid, effet=fit.b("tg") * 100, ic=(lo * 100, hi * 100), p=fit.p("tg"),
        n=len(rows), unite="pt",
        lecture=(f"effet du bonus {eff(t1) * 100:+.2f} pt {quoi}, "
                 f"{eff(t0) * 100:+.2f} pt ailleurs").replace(".", ","),
        methode="interaction en probabilité linéaire, robuste",
    )


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    rows = donnees.karlan()
    trt = [r for r in rows if r["treatment"] == 1]
    ctl = [r for r in rows if r["treatment"] == 0]
    out = {}
    out["O01"] = _prop("O01", trt, ctl, "bonus contre témoin")
    out["O02"] = _prop("O02", [r for r in trt if r["ratio"] in ("2", "3")],
                       [r for r in trt if r["ratio"] == "1"], "2:1 ou 3:1 contre 1:1")
    out["O03"] = _prop("O03", [r for r in trt if r["size"] == "$100,000"],
                       [r for r in trt if r["size"] == "$25,000"],
                       "plafond 100 000 $ contre 25 000 $")
    dons = [r for r in trt if r["gave"] == 1]
    out["O04"] = _moy("O04", [r for r in dons if r["ask"] == "1.50x"],
                      [r for r in dons if r["ask"] == "1x"], "suggestion 1,5× contre 1×")
    connus = [r for r in rows if r["mrm2"] is not None]
    out["O05"] = _prop("O05", [r for r in connus if r["mrm2"] <= 3],
                       [r for r in connus if r["mrm2"] > 3],
                       "dernier don à 3 mois ou moins, contre plus")
    out["O06"] = _prop("O06", [r for r in rows if r["freq"] >= 4],
                       [r for r in rows if r["freq"] < 4], "4 dons passés ou plus, contre moins")
    out["O07"] = _interaction("O07", connus, lambda r: 1.0 if r["mrm2"] <= 3 else 0.0,
                              "chez les récents")
    out["O08"] = _interaction("O08", rows, lambda r: r["red0"], "dans les États Bush")
    out["O09"] = _moy("O09", dons, [r for r in ctl if r["gave"] == 1],
                      "donateurs avec bonus contre témoins")
    out["O10"] = ronds()
    return out


@lru_cache(maxsize=1)
def ronds() -> Resultat:
    """Les montants ronds, contre une loi lisse **locale**.

    La loi nulle n'est pas « un chiffre final sur dix » : la densité des dons
    décroît avec le montant, et comparer à une moyenne globale mélangerait la
    pente et l'arrondi. On compare chaque multiple de 5 à ses quatre voisins
    entiers : sous une densité lisse à l'échelle du dollar, un don tombé dans
    la fenêtre {5k−2, …, 5k+2} a une chance sur cinq d'être le multiple.
    """
    dons = [r["amount"] for r in donnees.karlan() if r["gave"] == 1]
    entiers = [int(round(a)) for a in dons if abs(a - round(a)) < 1e-9 and a >= 3]
    dans = au_centre = 0
    for a in entiers:
        k = round(a / 5)
        if abs(a - 5 * k) <= 2:
            dans += 1
            au_centre += (a == 5 * k)
    p0 = 0.2
    obs = au_centre / dans
    se0 = math.sqrt(p0 * (1 - p0) / dans)
    z = (obs - p0) / se0
    se = math.sqrt(obs * (1 - obs) / dans)
    return Resultat(
        id="O10", effet=(obs - p0) * 100, ic=((obs - 1.96 * se - p0) * 100,
                                             (obs + 1.96 * se - p0) * 100),
        p=stats.p_bilateral(z), n=dans, unite="pt",
        lecture=(f"{_pct(obs, 1)} des dons tombent sur le multiple de 5 de leur fenêtre, "
                 f"contre 20 % sous une densité lisse ({entier(dans)} dons entiers)"),
        methode="binomiale contre la densité lisse locale (fenêtres de cinq dollars)",
        extra={"part": obs, "n": dans},
    )


def comptes_montants(maxi: int = 120) -> dict[int, int]:
    c: dict[int, int] = {}
    for r in donnees.karlan():
        if r["gave"] == 1 and r["amount"] <= maxi and abs(r["amount"] - round(r["amount"])) < 1e-9:
            c[int(round(r["amount"]))] = c.get(int(round(r["amount"])), 0) + 1
    return c


@lru_cache(maxsize=1)
def grille_ratio_recence() -> tuple[list[list[float]], list[str], list[str]]:
    """Taux de don par ratio du bonus (colonnes) et par récence (lignes)."""
    bornes = [(0, 2, "≤ 2 mois"), (3, 5, "3–5"), (6, 8, "6–8"), (9, 12, "9–12"),
              (13, 1e9, "> 12")]
    ratios = ["Control", "1", "2", "3"]
    z = []
    for lo, hi, _ in bornes:
        ligne = []
        for ra in ratios:
            sub = [r for r in donnees.karlan()
                   if r["mrm2"] is not None and lo <= r["mrm2"] <= hi and r["ratio"] == ra]
            x, n = _taux(sub)
            ligne.append(x / n)
        z.append(ligne)
    return z, [b[2] for b in bornes], ["témoin", "1:1", "2:1", "3:1"]


def taux_bras() -> list[tuple[str, float, float, int]]:
    out = []
    for ra, nom in (("Control", "témoin"), ("1", "1:1"), ("2", "2:1"), ("3", "3:1")):
        x, n = _taux(r for r in donnees.karlan() if r["ratio"] == ra)
        p = x / n
        out.append((nom, p, 1.96 * math.sqrt(p * (1 - p) / n), n))
    return out


def main() -> None:
    from .registre import par_id
    reg = par_id()
    for i, r in resultats().items():
        print(f"{i} {reg[i].enonce[:60]:60s} {r.effet:+7.3f} {r.unite} "
              f"[{r.ic[0]:+.3f}, {r.ic[1]:+.3f}] p={r.p:.4f}  {r.lecture}")
    print(taux_bras())


if __name__ == "__main__":
    main()
