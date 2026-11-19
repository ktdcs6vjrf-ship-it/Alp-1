"""Revenir acheter — la cohorte CDNOW et le modèle BG/NBD.

23 570 clients recrutés au premier trimestre 1997, suivis 78 semaines, chaque
achat daté et chiffré. On calibre sur les 39 premières semaines, on prédit les
39 suivantes, et l'on compare à ce qui s'est passé. Aucune étape ne regarde la
seconde moitié avant la prédiction : c'est le backtest au sens strict.

Le modèle BG/NBD (Fader, Hardie et Lee, 2005) suppose qu'un client actif achète
à un rythme propre (loi de Poisson, rythmes dispersés en loi gamma) et qu'après
chaque achat il peut « mourir » avec une probabilité propre (dispersée en loi
bêta). Un client ne dit jamais qu'il est parti : la mort se lit dans le
silence, et **le même silence ne pèse pas pareil selon le rythme passé**.
"""

from __future__ import annotations

import math
from datetime import date
from functools import lru_cache

from . import donnees, stats
from .resultat import Resultat, entier

DEBUT = date(1997, 1, 1)
CALIB_SEM = 39.0
HOLD_SEM = 39.0


def hyp2f1(a: float, b: float, c: float, z: float) -> float:
    """Série hypergéométrique de Gauss, |z| < 1."""
    terme, somme, k = 1.0, 1.0, 0
    while k < 20000:
        terme *= (a + k) * (b + k) / ((c + k) * (k + 1)) * z
        somme += terme
        k += 1
        if abs(terme) < 1e-13 * abs(somme):
            break
    return somme


@lru_cache(maxsize=1)
def clients() -> tuple[dict, ...]:
    """Par client : naissance, x, t_x, T (semaines), achats et dépenses des deux moitiés."""
    jours: dict = {}
    for c, d, _, m in donnees.cdnow():
        j = (date(d // 10000, d // 100 % 100, d % 100) - DEBUT).days
        jours.setdefault(c, {}).setdefault(j, 0.0)
        jours[c][j] += m
    fin = CALIB_SEM * 7
    out = []
    for c, achats in jours.items():
        js = sorted(achats)
        naissance = js[0]
        cal = [j for j in js if j < fin]
        hold = [j for j in js if fin <= j < fin + HOLD_SEM * 7]
        out.append({
            "client": c, "naissance": naissance / 7.0,
            "x": len(cal) - 1, "tx": (cal[-1] - naissance) / 7.0,
            "T": (fin - naissance) / 7.0,
            "hold": len(hold),
            "dep_cal": sum(achats[j] for j in cal),
            "dep_hold": sum(achats[j] for j in hold),
            "dep_1": achats[naissance],
        })
    return tuple(out)


def _ll_bgnbd(p, x, tx, T) -> float:
    r, alpha, a, b = p
    a1 = math.lgamma(r + x) - math.lgamma(r) + r * math.log(alpha)
    a2 = math.lgamma(a + b) + math.lgamma(b + x) - math.lgamma(b) - math.lgamma(a + b + x)
    a3 = -(r + x) * math.log(alpha + T)
    a4 = (math.log(a) - math.log(b + x - 1) - (r + x) * math.log(alpha + tx)) if x > 0 else -math.inf
    return a1 + a2 + stats.logsumexp([a3, a4])


@lru_cache(maxsize=1)
def ajuster() -> tuple[float, float, float, float]:
    """Maximum de vraisemblance sur la calibration (paramètres en logarithme)."""
    groupes: dict = {}
    for c in clients():
        cle = (c["x"], round(c["tx"], 6), round(c["T"], 6))
        groupes[cle] = groupes.get(cle, 0) + 1

    def f(lp):
        p = [math.exp(v) for v in lp]
        return -sum(n * _ll_bgnbd(p, *k) for k, n in groupes.items())

    lp, _ = stats.nelder_mead(f, [math.log(0.25), math.log(4.0), math.log(0.8),
                                  math.log(2.5)], pas=0.4, tol=1e-12)
    return tuple(math.exp(v) for v in lp)


def esperance(p, x, tx, T, t) -> float:
    """E[achats dans (T, T+t] | x, t_x, T] — Fader, Hardie et Lee (2005), éq. 10."""
    r, alpha, a, b = p
    z = t / (alpha + T + t)
    num = (a + b + x - 1) / (a - 1) * (
        1 - ((alpha + T) / (alpha + T + t)) ** (r + x) * hyp2f1(r + x, b + x, a + b + x - 1, z))
    den = 1 + ((a / (b + x - 1)) * ((alpha + T) / (alpha + tx)) ** (r + x) if x > 0 else 0.0)
    return num / den


def p_vivant(p, x, tx, T) -> float:
    r, alpha, a, b = p
    if x == 0:
        return 1.0
    return 1.0 / (1 + (a / (b + x - 1)) * ((alpha + T) / (alpha + tx)) ** (r + x))


def esperance_naissance(p, t) -> float:
    """E[X(t)] pour un client né en 0 : courbe de suivi de la cohorte."""
    r, alpha, a, b = p
    if t <= 0:
        return 0.0
    return (a + b - 1) / (a - 1) * (
        1 - (alpha / (alpha + t)) ** r * hyp2f1(r, b, a + b - 1, t / (alpha + t)))


@lru_cache(maxsize=1)
def predictions() -> tuple[tuple[dict, float, float], ...]:
    """(client, prédiction BG/NBD, prédiction naïve) pour la seconde moitié."""
    p = ajuster()
    cache: dict = {}
    out = []
    for c in clients():
        cle = (c["x"], c["tx"], c["T"])
        if cle not in cache:
            cache[cle] = esperance(p, c["x"], c["tx"], c["T"], HOLD_SEM)
        naif = c["x"] / c["T"] * HOLD_SEM if c["T"] > 0 else 0.0
        out.append((c, cache[cle], naif))
    return tuple(out)


SILENCE = 26.0


@lru_cache(maxsize=1)
def resultats() -> dict[str, Resultat]:
    pr = predictions()
    out = {}
    # R01 : erreur absolue, appariée client par client.
    d = [abs(n - c["hold"]) - abs(b - c["hold"]) for c, b, n in pr]
    m, se = stats.moyenne(d), math.sqrt(stats.variance(d) / len(d))
    mae_b = stats.moyenne(abs(b - c["hold"]) for c, b, _ in pr)
    mae_n = stats.moyenne(abs(n - c["hold"]) for c, _, n in pr)
    out["R01"] = Resultat(
        id="R01", effet=m, ic=(m - 1.96 * se, m + 1.96 * se), p=stats.p_bilateral(m / se),
        n=len(d), unite="achat",
        lecture=(f"erreur absolue moyenne {mae_b:.3f} achat par client contre {mae_n:.3f} "
                 f"pour le rythme passé").replace(".", ","),
        methode="écart apparié des erreurs absolues, client par client",
        extra={"mae_bgnbd": mae_b, "mae_naif": mae_n},
    )
    # R02 : parmi les silencieux d'au moins six mois, l'effet de la fréquence passée.
    sil = [(c["x"], c["hold"]) for c, _, _ in pr if c["x"] >= 1 and c["T"] - c["tx"] >= SILENCE]
    X = [[1.0, float(x)] for x, _ in sil]
    fit = stats.mco(X, [float(h) for _, h in sil], ["c", "x"])
    lo, hi = fit.ic("x")
    out["R02"] = Resultat(
        id="R02", effet=fit.b("x"), ic=(lo, hi), p=fit.p("x"), n=len(sil), unite="achat par achat",
        lecture=(f"parmi {entier(len(sil))} clients silencieux depuis au moins {SILENCE:.0f} semaines, "
                 f"chaque achat passé de plus change les achats futurs de {fit.b('x'):+.3f}").replace(".", ","),
        methode="moindres carrés, robuste",
    )
    # R03 : part des achats futurs captée par le décile de tête.
    n = len(pr)
    k = n // 10
    rang_b = sorted(range(n), key=lambda i: -pr[i][1])[:k]
    rang_d = sorted(range(n), key=lambda i: -pr[i][0]["dep_cal"])[:k]
    a_set, b_set = set(rang_b), set(rang_d)
    h = [pr[i][0]["hold"] for i in range(n)]
    tot = sum(h)
    sa = sum(h[i] for i in a_set) / tot
    sb = sum(h[i] for i in b_set) / tot
    D = sa - sb
    z = [h[i] * ((i in a_set) - (i in b_set)) - D * h[i] for i in range(n)]
    seD = math.sqrt(sum(v * v for v in z)) / tot
    out["R03"] = Resultat(
        id="R03", effet=D * 100, ic=((D - 1.96 * seD) * 100, (D + 1.96 * seD) * 100),
        p=stats.p_bilateral(D / seD), n=n, unite="pt",
        lecture=(f"le décile de tête BG/NBD capte {sa * 100:.1f} % des achats futurs, le décile "
                 f"des plus gros dépensiers {sb * 100:.1f} %").replace(".", ","),
        methode="écart de parts, linéarisation du ratio",
        extra={"bgnbd": sa, "depense": sb},
    )
    # R04 : corrélation des dépenses des deux moitiés.
    xs = [c["dep_cal"] for c, _, _ in pr]
    ys = [c["dep_hold"] for c, _, _ in pr]
    r = stats.correlation(xs, ys)
    zf, sez = math.atanh(r), 1 / math.sqrt(n - 3)
    out["R04"] = Resultat(
        id="R04", effet=r, ic=(math.tanh(zf - 1.96 * sez), math.tanh(zf + 1.96 * sez)),
        p=stats.p_bilateral(zf / sez), n=n, unite="r",
        lecture=(f"corrélation {r:.3f} : la covariable retire {r * r * 100:.1f} % de la variance "
                 f"d'un test sur la dépense").replace(".", ","),
        methode="corrélation de Pearson, intervalle de Fisher",
        extra={"r": r},
    )
    return out


def suivi() -> list[tuple[int, float, float]]:
    """Achats répétés cumulés, semaine par semaine : réalisés et attendus."""
    p = ajuster()
    par_sem: dict = {}
    nes: dict = {}
    for c in clients():
        nes[c["naissance"]] = nes.get(c["naissance"], 0) + 1
    jours: dict = {}
    for cl, d, _, m in donnees.cdnow():
        j = (date(d // 10000, d // 100 % 100, d % 100) - DEBUT).days
        jours.setdefault(cl, set()).add(j)
    for cl, js in jours.items():
        for j in sorted(js)[1:]:
            par_sem[j // 7] = par_sem.get(j // 7, 0) + 1
    out, cumul = [], 0
    for w in range(1, int(CALIB_SEM + HOLD_SEM) + 1):
        cumul += par_sem.get(w - 1, 0)
        att = sum(n * esperance_naissance(p, w - b) for b, n in nes.items())
        out.append((w, float(cumul), att))
    return out


def par_frequence(maxi: int = 7) -> list[tuple[int, float, float, int]]:
    """Achats futurs moyens par fréquence de calibration : réalisés et prédits."""
    out = []
    for x in range(maxi + 1):
        sub = [(c["hold"], b) for c, b, _ in predictions()
               if (c["x"] == x if x < maxi else c["x"] >= maxi)]
        out.append((x, stats.moyenne(h for h, _ in sub), stats.moyenne(b for _, b in sub), len(sub)))
    return out


def paradoxe(maxi: int = 6) -> list[tuple[int, float, float, int]]:
    """Silencieux depuis 26 semaines : achats futurs réalisés et prédits par fréquence."""
    out = []
    for x in range(1, maxi + 1):
        sub = [(c["hold"], b) for c, b, _ in predictions()
               if c["T"] - c["tx"] >= SILENCE and (c["x"] == x if x < maxi else c["x"] >= maxi)]
        if sub:
            out.append((x, stats.moyenne(h for h, _ in sub), stats.moyenne(b for _, b in sub), len(sub)))
    return out


def surface_vivant(T: float = 39.0, nx: int = 8, nt: int = 8) -> tuple[list[list[float]], list[int], list[float]]:
    """P(vivant) sur une grille fréquence × date du dernier achat (semaines)."""
    p = ajuster()
    xs = list(range(nx - 1, -1, -1))
    txs = [T * (nt - 1 - k) / (nt - 1) for k in range(nt)]
    z = [[p_vivant(p, x, tx, T) if x > 0 else 1.0 for tx in txs] for x in xs]
    return z, xs, txs


# ---------------------------------------------------------------------------
# Dons répétés : BG/BB en temps discret (Fader, Hardie et Shang, 2010)
# ---------------------------------------------------------------------------

def _ll_bgbb(p, x, tx, n) -> float:
    al, be, ga, de = p
    base = lbeta_(al + x, be + n - x) - lbeta_(al, be) + lbeta_(ga, de + n) - lbeta_(ga, de)
    termes = [base]
    for i in range(n - tx):
        termes.append(lbeta_(al + x, be + tx - x + i) - lbeta_(al, be)
                      + lbeta_(ga + 1, de + tx + i) - lbeta_(ga, de))
    return stats.logsumexp(termes)


lbeta_ = stats.lbeta


@lru_cache(maxsize=1)
def ajuster_dons() -> tuple[float, float, float, float]:
    data = donnees.dons()

    def f(lp):
        p = [math.exp(v) for v in lp]
        return -sum(w * _ll_bgbb(p, x, tx, n) for x, tx, n, w in data)

    lp, _ = stats.nelder_mead(f, [0.0, 0.0, 0.0, 0.0], pas=0.5, tol=1e-12)
    return tuple(math.exp(v) for v in lp)


def p_vivant_dons(x: int, tx: int, n: int = 6) -> float:
    al, be, ga, de = ajuster_dons()
    num = lbeta_(al + x, be + n - x) - lbeta_(al, be) + lbeta_(ga, de + n + 1) - lbeta_(ga, de)
    return math.exp(num - _ll_bgbb((al, be, ga, de), x, tx, n))


def main() -> None:
    print("BG/NBD", [round(v, 4) for v in ajuster()])
    for i, r in resultats().items():
        print(i, f"{r.effet:+.4f} [{r.ic[0]:+.4f}, {r.ic[1]:+.4f}] p={r.p:.4g}", r.lecture)
    print("par fréquence", [(x, round(h, 3), round(b, 3), n) for x, h, b, n in par_frequence()])
    print("paradoxe", [(x, round(h, 3), round(b, 3), n) for x, h, b, n in paradoxe()])
    s = suivi()
    print("suivi", s[38], s[-1])
    print("BG/BB", [round(v, 3) for v in ajuster_dons()], round(p_vivant_dons(6, 6), 3),
          round(p_vivant_dons(5, 1), 3), round(p_vivant_dons(1, 1), 3))


if __name__ == "__main__":
    main()
