"""Marchander par écrit — CraigslistBargain.

6 439 négociations écrites entre un acheteur et un vendeur autour d'une vraie
annonce Craigslist (meuble, logement, vélo, voiture, électronique, téléphone).
Le prix affiché, le prix final et chaque message sont connus. C'est le geste
du fan qui demande « tu me la fais à combien ? » pour un contenu sur mesure.

Dans ce jeu, le locuteur `usr` est le vendeur : son premier montant vaut le prix
affiché (médiane 1,00), celui de `sys` les trois quarts (médiane 0,73).

Mesure : le **ratio** prix final / prix affiché, du point de vue du vendeur,
sur les accords conclus et plausibles (ratio entre 0,2 et 1,5). Régression
linéaire avec contrôles de catégorie, de lot et de logarithme du prix affiché,
écarts-types robustes.
"""

from __future__ import annotations

import math
import re
from functools import lru_cache

from . import donnees, stats
from .resultat import Resultat, entier

_DOLLAR = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*(k\b)?", re.I)
_NOMBRE = re.compile(r"(?<![\w.$])(\d[\d,]*(?:\.\d+)?)\s*(k\b)?", re.I)
ETAT = re.compile(r"(brand new|\bnew\b|excellent|barely used|great condition|"
                  r"perfect condition|like new|mint|good condition|never used)")
FERME = re.compile(r"(\bfirm\b|\bfinal\b|\blowest\b|best i can do|can'?t go lower|"
                   r"cannot go lower|bottom line)")
CATEGORIES = ("furniture", "housing", "bike", "car", "electronics", "phone")


def rond(v: float) -> bool:
    """Un prix rond finit par 0 ou 5 (au dollar) ; en dessous de 10 $, tout entier."""
    if v < 10:
        return abs(v - round(v)) < 1e-9
    return abs(v - round(v)) < 1e-9 and int(round(v)) % 5 == 0


def montants(texte: str, annonce: float) -> list[float]:
    out = []
    for m in _DOLLAR.finditer(texte):
        v = float(m.group(1).replace(",", "") or 0) * (1000 if m.group(2) else 1)
        out.append(v)
    if out:
        return out
    for m in _NOMBRE.finditer(texte):
        try:
            v = float(m.group(1).replace(",", "")) * (1000 if m.group(2) else 1)
        except ValueError:
            continue
        if 1950 <= v <= 2030 and not 1950 <= annonce <= 2030:
            continue
        if 0.2 * annonce <= v <= 1.5 * annonce:
            out.append(v)
    return out


@lru_cache(maxsize=1)
def table() -> tuple[dict, ...]:
    lignes = []
    for x in donnees.bargain():
        a = x["annonce"]
        if not a or a <= 0:
            continue
        premier = None          # (locuteur, montant)
        premier_acheteur = None
        contre_vendeur = None   # première contre-offre du vendeur après l'acheteur
        tours = len(x["dialogue"])
        etat = ferme = False
        for sp, t in x["dialogue"]:
            tl = t.lower()
            ms = [m for m in montants(tl, a) if m > 0]
            if sp == "usr":
                etat = etat or bool(ETAT.search(tl))
                ferme = ferme or bool(FERME.search(tl))
            if not ms:
                continue
            if premier is None:
                premier = (sp, ms[0])
            if sp == "sys" and premier_acheteur is None:
                premier_acheteur = ms[0]
            if (sp == "usr" and premier_acheteur is not None and contre_vendeur is None
                    and abs(ms[0] - a) > 1e-9):
                contre_vendeur = ms[0]
        accord = x["accord"]
        ratio = accord / a if accord else None
        lignes.append({
            "annonce": a, "accord": accord, "ratio": ratio,
            "valide": ratio is not None and 0.2 <= ratio <= 1.5,
            "objet": x["objet"], "lot": 1.0 if x["lot"] == "test" else 0.0,
            "N01": 0.0 if rond(a) else 1.0,
            "N02": 1.0 if premier and premier[0] == "usr" else 0.0,
            "chiffre": premier is not None,
            "prem_ach": (premier_acheteur / a) if premier_acheteur else None,
            "N05": (0.0 if rond(contre_vendeur) else 1.0) if contre_vendeur else None,
            "tours": tours,
            "N06": 1.0 if etat else 0.0, "N07": 1.0 if ferme else 0.0,
        })
    med = stats.quantile([l["tours"] for l in lignes], 0.5)
    for l in lignes:
        l["N04"] = 1.0 if l["tours"] > med else 0.0
    return tuple(lignes)


def _controles(l: dict) -> list[float]:
    return [1.0, math.log(l["annonce"]), l["lot"],
            *[1.0 if l["objet"] == c else 0.0 for c in CATEGORIES[1:]]]


NOMS_C = ["const", "log_annonce", "lot", *CATEGORIES[1:]]


def _effet_binaire(rid: str, lignes, cle: str, quoi: str) -> Resultat:
    sub = [l for l in lignes if l[cle] is not None]
    X = [[*_controles(l), l[cle]] for l in sub]
    fit = stats.mco(X, [l["ratio"] for l in sub], [*NOMS_C, cle])
    lo, hi = fit.ic(cle)
    a = [l["ratio"] for l in sub if l[cle] == 1.0]
    b = [l["ratio"] for l in sub if l[cle] == 0.0]
    ma, mb = stats.moyenne(a), stats.moyenne(b)
    return Resultat(
        id=rid, effet=fit.b(cle) * 100, ic=(lo * 100, hi * 100), p=fit.p(cle),
        n=len(sub), unite="pt de prix",
        lecture=(f"prix final à {ma * 100:.1f} % de l'annonce {quoi}, {mb * 100:.1f} % sinon "
                 f"({entier(len(a))} contre {entier(len(b))})").replace(".", ","),
        methode="moindres carrés, catégorie, lot et log du prix en contrôle, robuste",
        base=mb, extra={"moy_avec": ma, "moy_sans": mb},
    )


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    tout = table()
    lignes = [l for l in tout if l["valide"]]
    out = {
        "N01": _effet_binaire("N01", lignes, "N01", "pour une annonce précise"),
        "N02": _effet_binaire("N02", [l for l in lignes if l["chiffre"]], "N02",
                              "quand le vendeur chiffre le premier"),
        "N04": _effet_binaire("N04", lignes, "N04", "pour une négociation longue"),
        "N05": _effet_binaire("N05", lignes, "N05", "après une contre-offre précise"),
        "N06": _effet_binaire("N06", lignes, "N06", "quand le vendeur cite l'état"),
        "N07": _effet_binaire("N07", lignes, "N07", "quand le vendeur se dit ferme"),
    }
    # N03 : pente du prix final sur la première offre de l'acheteur.
    sub = [l for l in lignes if l["prem_ach"] is not None and 0.05 <= l["prem_ach"] <= 1.5]
    X = [[*_controles(l), l["prem_ach"]] for l in sub]
    fit = stats.mco(X, [l["ratio"] for l in sub], [*NOMS_C, "prem"])
    lo, hi = fit.ic("prem")
    out["N03"] = Resultat(
        id="N03", effet=fit.b("prem"), ic=(lo, hi), p=fit.p("prem"), n=len(sub),
        unite="pente",
        lecture=(f"chaque point de première offre de l'acheteur déplace le prix final de "
                 f"{fit.b('prem'):.2f} point").replace(".", ","),
        methode="moindres carrés, mêmes contrôles, robuste",
    )
    # N08 : taux d'accord selon qui chiffre le premier.
    ch = [l for l in tout if l["chiffre"]]
    a = [l for l in ch if l["N02"] == 1.0]
    b = [l for l in ch if l["N02"] == 0.0]
    xa = sum(1 for l in a if l["accord"])
    xb = sum(1 for l in b if l["accord"])
    e = stats.deux_proportions(xa, len(a), xb, len(b))
    lo, hi = e.ic()
    out["N08"] = Resultat(
        id="N08", effet=e.diff * 100, ic=(lo * 100, hi * 100), p=e.p, n=len(ch), unite="pt",
        lecture=(f"accord dans {e.a * 100:.1f} % des cas quand le vendeur chiffre le premier, "
                 f"{e.b * 100:.1f} % sinon").replace(".", ","),
        methode="écart de proportions", base=e.b, relatif=e.relatif,
    )
    return {k: out[k] for k in sorted(out)}


@lru_cache(maxsize=1)
def ancrage(bins: int = 10) -> list[tuple[float, float, int]]:
    """Prix final moyen par décile de première offre de l'acheteur."""
    sub = sorted((l["prem_ach"], l["ratio"]) for l in table()
                 if l["valide"] and l["prem_ach"] is not None and 0.05 <= l["prem_ach"] <= 1.5)
    out = []
    for k in range(bins):
        part = sub[k * len(sub) // bins:(k + 1) * len(sub) // bins]
        out.append((stats.moyenne(p for p, _ in part), stats.moyenne(r for _, r in part),
                    len(part)))
    return out


def main() -> None:
    from .registre import par_id
    reg = par_id()
    t = table()
    print("dialogues", len(t), "accords valides", sum(1 for l in t if l["valide"]))
    for i, r in resultats().items():
        print(f"{i} {reg[i].enonce[:58]:58s} {r.effet:+7.3f} {r.unite} "
              f"[{r.ic[0]:+.3f}, {r.ic[1]:+.3f}] p={r.p:.4f}  {r.lecture}")
    print(ancrage())


if __name__ == "__main__":
    main()
