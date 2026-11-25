"""Cibler — par l'effet attendu, pas par le risque (Ascarza, 2018).

L'agence qui relance « les fans qui décrochent » parie que le fan le plus à
risque est celui que le message sauvera. Ascarza (2018) a montré sur deux
expériences de terrain que ce pari est souvent faux : le client le plus à
risque n'est pas le plus sensible au message, et cibler par l'effet attendu
rapporte davantage. On le revérifie ici sur les trois expériences tirées au
sort du cahier, **hors de l'échantillon** :

1. une coupe tirée au sort partage chaque jeu en deux moitiés ;
2. sur la première, deux modèles linéaires (un par bras) prédisent l'issue de
   chaque client avec et sans message — l'**effet estimé** est leur écart, le
   **risque** est la probabilité prédite de ne rien faire sans message ;
3. sur la seconde, jamais vue par les modèles, on choisit le tiers des clients
   de plus fort effet estimé, puis le tiers de plus fort risque, et l'on
   mesure l'effet réel du message dans chacun, grâce au tirage au sort.

La même coupe sert la famille M : une prédiction de l'issue par le seul passé
du client, estimée sur la première moitié, est corrélée à l'issue sur la
seconde. Le carré de cette corrélation est la part de variance qu'un test A/B
ajusté sur ce passé n'a plus à payer (Deng et al., 2013).
"""

from __future__ import annotations

import math
from functools import lru_cache
from itertools import compress
from operator import mul

from . import donnees2, registre2, stats
from .resultat import Resultat, entier

PART = registre2.PART_CIBLEE


def _log(v):
    return None if v is None else math.log1p(max(v, 0.0))


def _hillstrom():
    rows = []
    for r in donnees2.hillstrom():
        rows.append(({"recence": float(r["recence"]), "log_historique": math.log1p(r["historique"]),
                      "hommes": float(r["hommes"]), "femmes": float(r["femmes"]),
                      "nouveau": float(r["nouveau"]), "zone_s": float(r["zone"] == "s"),
                      "zone_r": float(r["zone"] == "r"), "canal_w": float(r["canal"] == "w"),
                      "canal_m": float(r["canal"] == "m")},
                     0 if r["courriel"] == "0" else 1, float(r["visite"]), r["depense"]))
    return rows


def _lenta():
    rows = []
    for r in donnees2.lenta():
        rows.append(({"age": r["age"], "sexe_f": float(r["sexe"] == "f"), "sexe_m": float(r["sexe"] == "m"),
                      "enfants": r["enfants"], "format": r["format"], "anciennete": r["anciennete"],
                      "rep_sms": r["rep_sms"], "rep_viber": r["rep_viber"], "promo": r["promo"],
                      "log_depense_12m": _log(r["depense_12m"]), "log_depense_3m": _log(r["depense_3m"]),
                      "log_recus_12m": _log(r["recus_12m"]), "log_recus_3m": _log(r["recus_3m"]),
                      "log_folies_12m": _log(r["folies_12m"])},
                     r["t"], float(r["y"]), float(r["y"])))
    return rows


def _x5():
    rows = []
    for r in donnees2.x5():
        age = r["age"] if r["age"] is not None and 14 <= r["age"] <= 100 else None
        rows.append(({"age": age, "sexe_f": float(r["sexe"] == "f"), "sexe_m": float(r["sexe"] == "m"),
                      "log_passages": _log(r["passages"]), "log_depense": _log(r["depense"]),
                      "recence_j": r["recence_j"], "premier_j": r["premier_j"],
                      "express_oui": float((r["express"] or 0) >= 1), "carte_j": r["carte_j"],
                      "points_oui": float(r["points_j"] is not None)},
                     r["t"], float(r["y"]), float(r["y"])))
    return rows


JEUX = {"hillstrom": _hillstrom, "lenta": _lenta, "x5": _x5}


def ols(cols: list[list[float]], y: list[float]) -> list[float]:
    """Coefficients des moindres carrés, colonne par colonne (`cols[0]` = constante).

    Les produits croisés passent par `map`, sans boucle Python par ligne : sur
    les 687 029 clients de Lenta, c'est la différence entre trois secondes et
    deux minutes."""
    k = len(cols)
    xtx = [[0.0] * k for _ in range(k)]
    for a in range(k):
        for c in range(a, k):
            xtx[a][c] = xtx[c][a] = sum(map(mul, cols[a], cols[c]))
    xty = [sum(map(mul, cols[a], y)) for a in range(k)]
    inv = stats.inverse(xtx)
    return [sum(inv[a][c] * xty[c] for c in range(k)) for a in range(k)]


def _predire(cols: list[list[float]], b: list[float]) -> list[float]:
    p = [b[0]] * len(cols[0])
    for col, bj in zip(cols[1:], b[1:]):
        p = [u + bj * v for u, v in zip(p, col)]
    return p


@lru_cache(maxsize=None)
def coupe(jeu: str) -> dict:
    """La coupe, les colonnes du modèle et les prédictions, pour un jeu.

    Une valeur manquante prend la médiane de la moitié d'estimation et une
    indicatrice d'absence (si la variable manque au moins une fois)."""
    rows = JEUX[jeu]()
    alea = stats.rng(f"coupe-{jeu}")
    est = [alea.random() < 0.5 for _ in rows]
    noms = registre2.VARIABLES[jeu]
    cols_all: list[list[float]] = [[1.0] * len(rows)]
    absences: list[list[float]] = []
    for v in noms:
        brut = [r[0][v] for r in rows]
        vus = [x for x, e in zip(brut, est) if e and x is not None]
        med = stats.quantile(vus, 0.5)
        cols_all.append([med if x is None else float(x) for x in brut])
        if any(x is None for x in brut):
            ind = [1.0 if x is None else 0.0 for x in brut]
            # Deux variables absentes ensemble (pas d'historique du tout) n'ont
            # qu'une indicatrice : deux colonnes égales rendraient le modèle singulier.
            if ind not in absences:
                absences.append(ind)
                cols_all.append(ind)
    t = [r[1] for r in rows]
    y = [r[2] for r in rows]
    ym = [r[3] for r in rows]

    def sous(masque):
        return [list(compress(c, masque)) for c in cols_all]

    m1 = [e and ti == 1 for e, ti in zip(est, t)]
    m0 = [e and ti == 0 for e, ti in zip(est, t)]
    b1 = ols(sous(m1), [yi for yi, m in zip(y, m1) if m])
    b0 = ols(sous(m0), [yi for yi, m in zip(y, m0) if m])
    bm = ols(sous(est), [yi for yi, m in zip(ym, est) if m])
    val = [not e for e in est]
    cv = sous(val)
    p1, p0, pm = _predire(cv, b1), _predire(cv, b0), _predire(cv, bm)
    return {"t": [ti for ti, m in zip(t, val) if m], "y": [yi for yi, m in zip(y, val) if m],
            "ym": [yi for yi, m in zip(ym, val) if m], "effet": [a - b for a, b in zip(p1, p0)],
            "risque": [1.0 - b for b in p0], "pm": pm, "n_est": sum(est), "n_val": sum(val)}


def _tau(t, y, membre) -> tuple[float, list[float], int, int]:
    """Effet du message dans un groupe, et sa fonction d'influence (zéro hors du groupe)."""
    s1 = s0 = n1 = n0 = 0
    for ti, yi, m in zip(t, y, membre):
        if m:
            if ti:
                s1 += yi
                n1 += 1
            else:
                s0 += yi
                n0 += 1
    m1, m0 = s1 / n1, s0 / n0
    inf = [(((yi - m1) / n1) if ti else (-(yi - m0) / n0)) if m else 0.0
           for ti, yi, m in zip(t, y, membre)]
    return m1 - m0, inf, n1, n0


def _top(score: list[float], part: float) -> list[bool]:
    k = int(round(len(score) * part))
    ordre = sorted(range(len(score)), key=lambda i: (-score[i], i))[:k]
    m = [False] * len(score)
    for i in ordre:
        m[i] = True
    return m


@lru_cache(maxsize=None)
def tiers(jeu: str) -> dict:
    c = coupe(jeu)
    t, y = c["t"], c["y"]
    tous = [True] * len(t)
    mu, mr = _top(c["effet"], PART), _top(c["risque"], PART)
    tu, iu, *nu = _tau(t, y, mu)
    tr, ir, *nr = _tau(t, y, mr)
    ta, ia, *na = _tau(t, y, tous)
    commun = sum(1 for a, b in zip(mu, mr) if a and b)
    return {"effet": (tu, iu, nu), "risque": (tr, ir, nr), "tous": (ta, ia, na),
            "commun": commun, "k": sum(mu), "n": len(t)}


QUOI = {"hillstrom": "visites", "lenta": "visites", "x5": "achats"}


def _ecart(rid: str, jeu: str, a: str, b: str, phrase: str) -> Resultat:
    T = tiers(jeu)
    ta, ia, _ = T[a]
    tb, ib, _ = T[b]
    d = ta - tb
    se = math.sqrt(sum((u - v) ** 2 for u, v in zip(ia, ib)))
    nom = {"effet": "le tiers choisi par effet", "risque": "le tiers le plus à risque", "tous": "tous les clients"}
    return Resultat(
        id=rid, effet=d * 100, ic=((d - 1.96 * se) * 100, (d + 1.96 * se) * 100),
        p=stats.p_bilateral(d / se), n=T["n"], unite="pt",
        lecture=(f"{nom[a]} gagne {ta * 100:+.2f} pt de {QUOI[jeu]} avec le message, "
                 f"{nom[b]} {tb * 100:+.2f} pt ({phrase}, {entier(T['n'])} clients jamais vus par le modèle)"
                 ).replace(".", ","),
        methode="effets mesurés par tirage au sort dans chaque tiers, hors échantillon ; fonction d'influence",
        # Pas de budget : la formule de `synthese2.budget` compare deux taux, et un
        # écart entre deux effets en demande bien davantage.
        base=None, relatif=None,
        extra={"ta": ta, "tb": tb, "commun": T["commun"], "k": T["k"]},
    )


def _covariable(rid: str, jeu: str) -> Resultat:
    c = coupe(jeu)
    r = stats.correlation(c["pm"], c["ym"])
    n = len(c["ym"])
    zf, sez = math.atanh(r), 1 / math.sqrt(n - 3)
    return Resultat(
        id=rid, effet=r, ic=(math.tanh(zf - 1.96 * sez), math.tanh(zf + 1.96 * sez)),
        p=stats.p_bilateral(zf / sez), n=n, unite="r",
        lecture=(f"corrélation {r:.3f} hors échantillon : ajuster sur le passé retire "
                 f"{r * r * 100:.1f} % de la variance, soit autant d'envois en moins").replace(".", ","),
        methode="prédiction par le passé estimée sur une moitié, corrélation de Pearson sur l'autre",
        extra={"r2": r * r},
    )


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    out = {}
    for k, jeu in enumerate(("hillstrom", "lenta", "x5")):
        a, b, c = (f"C{3 * k + j:02d}" for j in (1, 2, 3))
        out[a] = _ecart(a, jeu, "effet", "risque", "effet réel, tiers contre tiers")
        out[b] = _ecart(b, jeu, "risque", "tous", "effet réel, tiers contre moyenne")
        out[c] = _ecart(c, jeu, "effet", "tous", "effet réel, tiers contre moyenne")
    for rid, jeu in (("M01", "hillstrom"), ("M02", "lenta"), ("M03", "x5")):
        out[rid] = _covariable(rid, jeu)
    return out


def courbe(jeu: str, score: str, pas: int = 10) -> list[tuple[float, float]]:
    """Gain cumulé du message selon la part des clients écrits, rangés par un score.

    Chaque point : (part écrite, messages gagnants pour 100 clients de la base),
    l'effet réel du groupe écrit multiplié par sa part. Rangés au hasard, les
    points sont sur la droite qui joint 0 à l'effet moyen."""
    c = coupe(jeu)
    t, y = c["t"], c["y"]
    out = [(0.0, 0.0)]
    for k in range(1, pas + 1):
        m = _top(c[score], k / pas)
        tau, *_ = _tau(t, y, m)
        out.append((k / pas, tau * k / pas * 100))
    return out


def main() -> None:
    from .registre2 import par_id
    reg = par_id()
    for i, r in resultats().items():
        print(f"{i} {reg[i].enonce[:62]:62s} {r.effet:+8.3f} {r.unite:3s} "
              f"[{r.ic[0]:+.3f}, {r.ic[1]:+.3f}] p={r.p:.2e}  {r.lecture}")


if __name__ == "__main__":
    main()
