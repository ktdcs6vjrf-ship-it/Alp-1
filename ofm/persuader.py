"""Persuader par écrit — Persuasion for Good.

1 017 conversations écrites entre deux inconnus : l'un (le persuadeur) doit
convaincre l'autre (le persuadé) de donner une partie de sa rémunération à une
association. Le don réel, versé après la conversation, est connu. C'est le
geste d'un chatteur : une conversation qui finit, ou non, par un paiement.

Les variables sont calculées sur le texte, avec des lexiques déclarés au
registre. Le modèle est une probabilité linéaire de don positif, toutes les
variables ensemble et le nombre de tours en contrôle, écarts-types robustes.
"""

from __future__ import annotations

import re
from functools import lru_cache

from . import donnees, stats
from .resultat import Resultat, entier

MONTANT = re.compile(r"(\$\s?\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:cents?|dollars?)\b|"
                     r"\b(?:one|two|ten|twenty|fifty)\s+(?:cents?|dollars?)\b)")
SOI = re.compile(r"\bi(?:'ll|'m|'ve| will| am| have| already| also| usually| always|"
                 r" just| plan to| going to| gonna| myself)*\s+(?:donate|donated|donating|"
                 r"give|gave|giving)\b")
LIBRE = re.compile(r"(no pressure|up to you|your choice|no obligation|don'?t have to|"
                   r"not obligated|no worries if|totally understand|it'?s okay if|"
                   r"it'?s ok if|completely understand)")
EMOTION = re.compile(r"\b(children|kids|starving|suffering|die|dying|heartbreaking|"
                     r"poverty|hunger|malnourished|orphans?)\b")
MERCI = re.compile(r"\bthank")

#: Mots-outils par catégorie (Ireland et Pennebaker, 2010), en anglais.
OUTILS = {
    "pronoms_perso": "i me my mine myself we us our ours you your yours he him his she "
                     "her hers they them their theirs",
    "pronoms_imperso": "it its it's that this these those something anything nothing "
                       "everything someone anyone everyone",
    "articles": "a an the",
    "prepositions": "to of in for on with at by from about into over after under "
                    "between through during without",
    "auxiliaires": "am is are was were be been being have has had do does did will "
                   "would can could should may might must shall",
    "adverbes": "very really just so too also only even still now then here there "
                "quite pretty",
    "conjonctions": "and but or because if so although though while whereas",
    "negations": "no not never none nor don't can't won't isn't aren't didn't doesn't",
    "quantifieurs": "all some many much few lot lots more most less several each every",
}
_OUTILS = {k: set(v.split()) for k, v in OUTILS.items()}
_MOT = re.compile(r"[a-z']+")


def _lsm(a: list[str], b: list[str]) -> float:
    if not a or not b:
        return 0.0
    out = []
    for mots in _OUTILS.values():
        pa = sum(1 for w in a if w in mots) / len(a)
        pb = sum(1 for w in b if w in mots) / len(b)
        out.append(1 - abs(pa - pb) / (pa + pb + 1e-4))
    return sum(out) / len(out)


@lru_cache(maxsize=1)
def table() -> tuple[dict, ...]:
    info, dial = donnees.p4g()
    phr: dict = {}
    for r in dial:
        phr.setdefault(r["dialogue"], []).append((int(r["tour"]), r["role"], r["phrase"]))
    don = {(r["B2"], r["B4"]): r for r in info}
    lignes = []
    for d, items in phr.items():
        if (d, "1") not in don:
            continue
        p0 = [t.lower() for k, ro, t in items if ro == "0"]
        p1 = [t.lower() for k, ro, t in items if ro == "1"]
        txt0, txt1 = " ".join(p0), " ".join(p1)
        m0, m1 = _MOT.findall(txt0), _MOT.findall(txt1)
        tours0 = {k for k, ro, _ in items if ro == "0"}
        debut1 = sum(len(_MOT.findall(t.lower())) for k, ro, t in items if ro == "1" and k <= 2)
        premiere = min((k for k, ro, t in items if ro == "0" and "donat" in t.lower()),
                       default=99)
        persu = don[(d, "1")]
        agre = persu["agreeable.x"]
        lignes.append({
            "y": 1.0 if float(persu["B6"]) > 0 else 0.0,
            "montant": float(persu["B6"]),
            "q0": txt0.count("?"), "q1": txt1.count("?"),
            "P02": 1.0 if MONTANT.search(txt0) else 0.0,
            "P03": 1.0 if SOI.search(txt0) else 0.0,
            "P04": 1.0 if LIBRE.search(txt0) else 0.0,
            "P05": 1.0 if EMOTION.search(txt0) else 0.0,
            "agre": float(agre) if agre not in ("", "NA") else None,
            "lsm": _lsm(m0, m1),
            "mpt": len(m0) / max(len(tours0), 1),
            "P09": 1.0 if premiere <= 2 else 0.0,
            "debut1": debut1,
            "P12": 1.0 if MERCI.search(txt0) else 0.0,
            "tours": max(k for k, _, _ in items) + 1,
        })
    lignes = [l for l in lignes if l["agre"] is not None]
    med = {k: stats.quantile([l[k] for l in lignes], 0.5)
           for k in ("q0", "q1", "agre", "lsm", "mpt", "debut1")}
    for l in lignes:
        l["P01"] = 1.0 if l["q0"] > med["q0"] else 0.0
        l["P06"] = 1.0 if l["agre"] > med["agre"] else 0.0
        l["P07"] = 1.0 if l["lsm"] > med["lsm"] else 0.0
        l["P08"] = 1.0 if l["mpt"] > med["mpt"] else 0.0
        l["P10"] = 1.0 if l["debut1"] > med["debut1"] else 0.0
        l["P11"] = 1.0 if l["q1"] > med["q1"] else 0.0
    return tuple(lignes)


IDS = tuple(f"P{k:02d}" for k in range(1, 13))


@lru_cache(maxsize=1)
def modele() -> stats.Ajustement:
    lignes = table()
    X = [[1.0, *[l[i] for i in IDS], l["tours"]] for l in lignes]
    return stats.mco(X, [l["y"] for l in lignes], ["const", *IDS, "tours"])


def _pct(v: float) -> str:
    return f"{v * 100:.1f}".replace(".", ",") + " %"


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    lignes = table()
    fit = modele()
    out = {}
    for i in IDS:
        a = [l["y"] for l in lignes if l[i] == 1.0]
        b = [l["y"] for l in lignes if l[i] == 0.0]
        e = stats.deux_proportions(int(sum(a)), len(a), int(sum(b)), len(b))
        lo, hi = fit.ic(i)
        out[i] = Resultat(
            id=i, effet=fit.b(i) * 100, ic=(lo * 100, hi * 100), p=fit.p(i),
            n=len(lignes), unite="pt",
            lecture=f"{_pct(e.a)} donnent avec, {_pct(e.b)} sans ({entier(len(a))} contre {entier(len(b))})",
            methode="probabilité linéaire ajustée sur les 12 variables et la longueur, robuste",
            base=e.b, relatif=(fit.b(i) / e.b if e.b else None),
            extra={"taux_avec": e.a, "taux_sans": e.b, "n_avec": len(a), "n_sans": len(b)},
        )
    return out


def main() -> None:
    from .registre import par_id
    reg = par_id()
    lignes = table()
    print("dialogues", len(lignes), "taux de don", sum(l["y"] for l in lignes) / len(lignes))
    for i, r in resultats().items():
        print(f"{i} {reg[i].enonce[:60]:60s} {r.effet:+6.2f} pt "
              f"[{r.ic[0]:+.2f}, {r.ic[1]:+.2f}] p={r.p:.4f}  {r.lecture}")


if __name__ == "__main__":
    main()


HESITE = re.compile(r"\b(no|not|can't|cannot|don't|won't|maybe|unsure|hmm+|rather not|"
                    r"pass|skeptical|hesitant|tight|need the money|need it)\b")
ACCORD = re.compile(r"(i'?ll donate|i will donate|i'?d like to donate|i'?ll give|"
                    r"i will give|i can donate|count me in|i'?m in\b|\bsure\b|\byes\b|"
                    r"i'?ll do it|i would like to donate|i'?ll go with)")


@lru_cache(maxsize=1)
def diagnostic_reponse() -> dict[str, tuple[float, float, int]]:
    """Ce qui précède une tactique — diagnostic **a posteriori**, hors registre.

    Une tactique de conversation n'est pas tirée au sort : le persuadeur la
    choisit **en réponse** à ce que l'autre vient d'écrire. On compare donc,
    pour chaque tactique, la part des messages qui suivent une hésitation (ou
    un accord) du persuadé à la même part sur l'ensemble des messages.
    Rend {tactique: (part après la tactique, part de base, effectif)}.
    """
    _, dial = donnees.p4g()
    par: dict = {}
    for r in dial:
        par.setdefault(r["dialogue"], {}).setdefault((int(r["tour"]), r["role"]), []).append(
            r["phrase"].lower())
    compte = {"libre": [0, 0], "merci": [0, 0], "base_h": [0, 0], "base_a": [0, 0]}
    for tours in par.values():
        for (k, ro), phrases in tours.items():
            if ro != "0" or (k - 1, "1") not in tours:
                continue
            avant = " ".join(tours[(k - 1, "1")])
            moi = " ".join(phrases)
            h, a = bool(HESITE.search(avant)), bool(ACCORD.search(avant))
            compte["base_h"][0] += h
            compte["base_h"][1] += 1
            compte["base_a"][0] += a
            compte["base_a"][1] += 1
            if LIBRE.search(moi):
                compte["libre"][0] += h
                compte["libre"][1] += 1
            if MERCI.search(moi):
                compte["merci"][0] += a
                compte["merci"][1] += 1
    return {
        "libre": (compte["libre"][0] / compte["libre"][1],
                  compte["base_h"][0] / compte["base_h"][1], compte["libre"][1]),
        "merci": (compte["merci"][0] / compte["merci"][1],
                  compte["base_a"][0] / compte["base_a"][1], compte["merci"][1]),
    }
