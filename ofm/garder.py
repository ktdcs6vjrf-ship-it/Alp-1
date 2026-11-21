"""Garder — les fidèles d'un second marché (Online Retail II).

Le cahier nº 1 a trouvé, sur CDNOW, un résultat contraire au modèle publié :
après six mois de silence, l'ancien acheteur fréquent revient **davantage**
que l'occasionnel, quand BG/NBD le croit perdu. Un résultat contraire sur un
seul marché peut être une particularité de ce marché. On le revérifie donc
sur un autre : un grossiste en ligne britannique (2009–2011), des achats
datés et chiffrés, la même méthode — calibrer sur une année, prédire la
suivante, et comparer à ce qui s'est passé sans avoir regardé la seconde
année avant la prédiction.

Les définitions sont celles du registre (`registre2.py`) : un achat est un
jour d'achat, la cohorte est celle des clients vus pour la première fois les
treize premières semaines, le silence dure au moins 26 semaines.
"""

from __future__ import annotations

import math
from datetime import date
from functools import lru_cache

from . import donnees2, revenir, stats
from .resultat import Resultat, entier

DEBUT = date(2009, 12, 1)
FIN_CALIB = date(2010, 12, 1)       # exclu
FIN_VALID = date(2011, 12, 1)       # exclu
COHORTE = date(2010, 3, 1)          # premier achat avant cette date
SILENCE = 26.0
HOLD_SEM = (FIN_VALID - FIN_CALIB).days / 7.0


def _jour(s: str) -> date:
    return date(int(s[:4]), int(s[5:7]), int(s[8:10]))


@lru_cache(maxsize=1)
def clients() -> tuple[dict, ...]:
    """Par client de la cohorte : x, t_x, T (semaines), achats et dépenses."""
    jours: dict[int, dict[date, float]] = {}
    for client, d, montant, _, annulee, _ in donnees2.retail():
        if annulee or montant <= 0:
            continue
        j = _jour(d)
        if not DEBUT <= j < FIN_VALID:
            continue
        jours.setdefault(client, {}).setdefault(j, 0.0)
        jours[client][j] += montant
    out = []
    for c, achats in jours.items():
        cal = sorted(j for j in achats if j < FIN_CALIB)
        if not cal or cal[0] >= COHORTE:
            continue
        hold = [j for j in achats if FIN_CALIB <= j < FIN_VALID]
        naissance = cal[0]
        out.append({
            "client": c, "x": len(cal) - 1, "tx": (cal[-1] - naissance).days / 7.0,
            "T": (FIN_CALIB - naissance).days / 7.0, "hold": len(hold),
            "dep_cal": sum(achats[j] for j in cal), "dep_hold": sum(achats[j] for j in hold),
            "dep_1": achats[naissance],
        })
    out.sort(key=lambda c: c["client"])
    return tuple(out)


@lru_cache(maxsize=1)
def ajuster() -> tuple[float, float, float, float]:
    groupes: dict = {}
    for c in clients():
        cle = (c["x"], round(c["tx"], 6), round(c["T"], 6))
        groupes[cle] = groupes.get(cle, 0) + 1

    def f(lp):
        p = [math.exp(v) for v in lp]
        return -sum(n * revenir._ll_bgnbd(p, *k) for k, n in groupes.items())

    lp, _ = stats.nelder_mead(f, [math.log(0.5), math.log(5.0), math.log(0.5),
                                  math.log(2.0)], pas=0.4, tol=1e-12)
    return tuple(math.exp(v) for v in lp)


@lru_cache(maxsize=1)
def predictions() -> tuple[tuple[dict, float, float], ...]:
    p = ajuster()
    out = []
    for c in clients():
        b = revenir.esperance(p, c["x"], c["tx"], c["T"], HOLD_SEM)
        naif = c["x"] / c["T"] * HOLD_SEM
        out.append((c, b, naif))
    return tuple(out)


def silencieux() -> list[tuple[dict, float]]:
    return [(c, b) for c, b, _ in predictions() if c["x"] >= 1 and c["T"] - c["tx"] >= SILENCE]


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    pr = predictions()
    out = {}
    d = [abs(n - c["hold"]) - abs(b - c["hold"]) for c, b, n in pr]
    m, se = stats.moyenne(d), math.sqrt(stats.variance(d) / len(d))
    mae_b = stats.moyenne(abs(b - c["hold"]) for c, b, _ in pr)
    mae_n = stats.moyenne(abs(n - c["hold"]) for c, _, n in pr)
    out["G01"] = Resultat(
        id="G01", effet=m, ic=(m - 1.96 * se, m + 1.96 * se), p=stats.p_bilateral(m / se),
        n=len(d), unite="achat",
        lecture=(f"erreur absolue moyenne {mae_b:.3f} jour d'achat par client contre {mae_n:.3f} "
                 f"pour le rythme passé").replace(".", ","),
        methode="écart apparié des erreurs absolues, client par client",
        extra={"mae_bgnbd": mae_b, "mae_naif": mae_n},
    )
    sil = silencieux()
    X = [[1.0, float(c["x"])] for c, _ in sil]
    fit = stats.mco(X, [float(c["hold"]) for c, _ in sil], ["c", "x"])
    lo, hi = fit.ic("x")
    out["G02"] = Resultat(
        id="G02", effet=fit.b("x"), ic=(lo, hi), p=fit.p("x"), n=len(sil), unite="achat par achat",
        lecture=(f"parmi {entier(len(sil))} clients silencieux depuis au moins {SILENCE:.0f} semaines, "
                 f"chaque achat passé de plus change les achats de l'année suivante de "
                 f"{fit.b('x'):+.3f}").replace(".", ","),
        methode="moindres carrés, robuste",
    )
    fit = stats.mco(X, [float(c["hold"]) - b for c, b in sil], ["c", "x"])
    lo, hi = fit.ic("x")
    out["G03"] = Resultat(
        id="G03", effet=fit.b("x"), ic=(lo, hi), p=fit.p("x"), n=len(sil), unite="achat par achat",
        lecture=(f"chez les mêmes silencieux, l'écart entre achats réalisés et prédits grandit de "
                 f"{fit.b('x'):+.3f} par achat passé").replace(".", ","),
        methode="moindres carrés sur le résidu du modèle, robuste",
    )
    n = len(pr)
    k = n // 10
    a_set = set(sorted(range(n), key=lambda i: (-pr[i][1], i))[:k])
    b_set = set(sorted(range(n), key=lambda i: (-pr[i][0]["dep_cal"], i))[:k])
    h = [pr[i][0]["hold"] for i in range(n)]
    tot = sum(h)
    sa = sum(h[i] for i in a_set) / tot
    sb = sum(h[i] for i in b_set) / tot
    D = sa - sb
    z = [h[i] * ((i in a_set) - (i in b_set)) - D * h[i] for i in range(n)]
    seD = math.sqrt(sum(v * v for v in z)) / tot
    out["G04"] = Resultat(
        id="G04", effet=D * 100, ic=((D - 1.96 * seD) * 100, (D + 1.96 * seD) * 100),
        p=stats.p_bilateral(D / seD) if seD > 0 else 1.0, n=n, unite="pt",
        lecture=(f"le décile de tête BG/NBD capte {sa * 100:.1f} % des achats de l'année suivante, "
                 f"le décile des plus gros dépensiers {sb * 100:.1f} %").replace(".", ","),
        methode="écart de parts, linéarisation du ratio",
        extra={"bgnbd": sa, "depense": sb},
    )
    med = stats.quantile([c["dep_1"] for c, _, _ in pr], 0.5)
    hauts = [c["hold"] for c, _, _ in pr if c["dep_1"] > med]
    bas = [c["hold"] for c, _, _ in pr if c["dep_1"] <= med]
    e = stats.deux_moyennes(hauts, bas)
    lo, hi = e.ic()
    out["G05"] = Resultat(
        id="G05", effet=e.diff, ic=(lo, hi), p=e.p, n=len(hauts) + len(bas), unite="achat",
        lecture=(f"{e.a:.2f} jours d'achat l'année suivante après une première commande de plus de "
                 f"{med:.0f} £, contre {e.b:.2f} en dessous").replace(".", ","),
        methode="écart de moyennes (Welch)", base=e.b, relatif=e.relatif,
        extra={"mediane": med},
    )
    return out


def par_frequence(seuil_max: int = 6) -> list[tuple[str, float, float, int]]:
    """Silencieux : achats prédits et réalisés l'année suivante, par fréquence passée."""
    sil = silencieux()
    out = []
    for x in range(1, seuil_max + 1):
        sub = [(c, b) for c, b in sil if (c["x"] == x if x < seuil_max else c["x"] >= x)]
        if not sub:
            continue
        nom = str(x) if x < seuil_max else f"{x}+"
        out.append((nom, stats.moyenne(b for _, b in sub), stats.moyenne(c["hold"] for c, _ in sub), len(sub)))
    return out


def main() -> None:
    from .registre2 import par_id
    reg = par_id()
    print("paramètres BG/NBD", [round(v, 4) for v in ajuster()], "cohorte", len(clients()))
    for i, r in resultats().items():
        print(f"{i} {reg[i].enonce[:60]:60s} {r.effet:+8.3f} {r.unite:3s} "
              f"[{r.ic[0]:+.3f}, {r.ic[1]:+.3f}] p={r.p:.2e}  {r.lecture}")
    print(par_frequence())


if __name__ == "__main__":
    main()
