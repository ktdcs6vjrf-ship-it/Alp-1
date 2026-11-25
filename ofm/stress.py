"""La batterie du cahier nº 4 — les outils des quants, en bibliothèque standard.

Chaque fonction répond à une question qu'un gérant pose avant de croire un
backtest, et chacune est étalonnée sur une vérité connue (`etalonner`) avant
de servir sur des données réelles :

- **Holm** (1979) : la correction qui garde à 5 % la chance d'une seule fausse
  alerte dans toute la famille (plus sévère que Benjamini-Hochberg, qui garde
  la *part* de fausses alertes).
- **Le seuil t ≥ 3** (Harvey, Liu et Zhu, 2016) : quand beaucoup de chercheurs
  ont fouillé les mêmes données, 1,96 ne suffit plus.
- **SPA** (Hansen, 2005) et **Reality Check** (White, 2000) : *parmi tous les
  réglages essayés, le meilleur bat-il vraiment la référence, ou l'a-t-on
  trouvé en cherchant ?* Bootstrap à multiplicateurs sur la fonction
  d'influence de chaque réglage.
- **CSCV et PBO** (Bailey, Borwein, López de Prado et Zhu, 2017) : on coupe
  les données en 16 blocs ; pour chacune des 12 870 façons d'en prendre 8, on
  choisit le meilleur réglage sur ces 8 et on regarde son rang sur les 8
  autres. La PBO est la part des cas où le réglage choisi finit sous la médiane ;
  la « perte » est la part des cas où il ne bat plus la référence.
- **Le Sharpe dégonflé** (Bailey et López de Prado, 2014) : la probabilité que
  le vrai Sharpe dépasse celui qu'on obtiendrait en prenant le meilleur de N
  essais sans avantage, asymétrie et queues épaisses comprises.
- **La courbe de spécification** (Simonsohn, Simmons et Nelson, 2020) : le même
  effet sous tous les réglages raisonnables, résumé en deux parts (même sens,
  significatif).
"""

from __future__ import annotations

import math
from itertools import combinations
from statistics import NormalDist

from . import stats

EULER = 0.5772156649015329
_N = NormalDist()


# ---------------------------------------------------------------------------
# Corrections pour la famille
# ---------------------------------------------------------------------------

def holm(pvals: list[float]) -> list[float]:
    """Valeurs p ajustées de Holm (pas à pas descendant, taux d'erreur de la famille)."""
    m = len(pvals)
    ordre = sorted(range(m), key=lambda i: pvals[i])
    out = [0.0] * m
    courant = 0.0
    for rang, i in enumerate(ordre):
        courant = max(courant, min(1.0, (m - rang) * pvals[i]))
        out[i] = courant
    return out


def passe_t3(effet: float, p: float, sens: int, seuil: float = 3.0) -> bool:
    """|t| ≥ 3 (lu depuis la valeur p bilatérale), dans le sens annoncé."""
    z = abs(stats.Phi_inv(max(min(p, 1 - 1e-16), 1e-300) / 2))
    return z >= seuil and (sens == 0 or (effet > 0) == (sens > 0))


# ---------------------------------------------------------------------------
# SPA et Reality Check
# ---------------------------------------------------------------------------

def spa(d: list[float], influence: list[list[float]], tirages: int, nom: str) -> dict:
    """Test SPA de Hansen (2005), version cohérente, et le Reality Check de White (2000).

    `d[k]` : l'écart moyen du réglage k à la référence (positif = mieux) ;
    `influence[k][g]` : la contribution du groupe g à cet écart (somme sur g = 0,
    variance de d[k] = Σ_g influence²). Les tirages multiplient les
    contributions par des poids normaux (bootstrap à multiplicateurs), ce qui
    reproduit la loi jointe des écarts sans refaire les calculs."""
    K, G = len(d), len(influence[0])
    sig = [math.sqrt(sum(v * v for v in inf)) for inf in influence]
    t_obs = max(0.0, max(dk / s for dk, s in zip(d, sig) if s > 0))
    seuil = math.sqrt(2.0 * math.log(math.log(max(G, 16))))
    # g_c : on ne recentre que les réglages qui ne sont pas nettement mauvais.
    centre_c = [dk if dk / s >= -seuil else 0.0 for dk, s in zip(d, sig)]
    alea = stats.rng(f"spa-{nom}")
    n_spa = n_rc = 0
    for _ in range(tirages):
        w = [alea.gauss(0.0, 1.0) for _ in range(G)]
        best_c = best_u = 0.0
        for k in range(K):
            if sig[k] == 0:
                continue
            fl = sum(map(float.__mul__, w, influence[k]))
            zc = (d[k] + fl - centre_c[k]) / sig[k]
            zu = fl / sig[k]
            if zc > best_c:
                best_c = zc
            if zu > best_u:
                best_u = zu
        n_spa += best_c >= t_obs
        n_rc += best_u >= t_obs
    return {"t": t_obs, "p_spa": (n_spa + 1) / (tirages + 1), "p_rc": (n_rc + 1) / (tirages + 1),
            "meilleur": max(range(K), key=lambda k: d[k] / sig[k] if sig[k] > 0 else -math.inf)}


# ---------------------------------------------------------------------------
# CSCV et probabilité de surajustement
# ---------------------------------------------------------------------------

def cscv(perf: list[list[float]], reference: list[float] | None = None) -> dict:
    """PBO et probabilité de perte (Bailey et al., 2017).

    `perf[k][s]` : la performance du réglage k sur le bloc s (une moyenne par
    bloc) ; `reference[s]` : celle de la référence (0 si l'on juge déjà un écart).
    Chacune des C(S, S/2) moitiés sert à choisir, son complément à juger."""
    K, S = len(perf), len(perf[0])
    ref = reference or [0.0] * S
    blocs = range(S)
    lambdas, pertes, degradation = [], 0, []
    total = 0
    for a in combinations(blocs, S // 2):
        b = tuple(x for x in blocs if x not in a)
        is_ = [sum(perf[k][s] for s in a) / len(a) for k in range(K)]
        oos = [sum(perf[k][s] for s in b) / len(b) for k in range(K)]
        r_is = sum(ref[s] for s in a) / len(a)
        r_oos = sum(ref[s] for s in b) / len(b)
        k_star = max(range(K), key=lambda k: (is_[k], -k))
        rang = 1 + sum(1 for k in range(K) if oos[k] < oos[k_star])
        rang += 0.5 * (sum(1 for k in range(K) if oos[k] == oos[k_star]) - 1)
        omega = rang / (K + 1)
        lambdas.append(math.log(omega / (1 - omega)))
        pertes += oos[k_star] - r_oos <= 0
        degradation.append((is_[k_star] - r_is, oos[k_star] - r_oos))
        total += 1
    return {"pbo": sum(1 for x in lambdas if x <= 0) / total, "perte": pertes / total,
            "combinaisons": total, "lambdas": lambdas, "degradation": degradation}


# ---------------------------------------------------------------------------
# Le Sharpe dégonflé
# ---------------------------------------------------------------------------

def moments(x: list[float]) -> tuple[float, float, float, float]:
    """Moyenne, écart-type (n − 1), asymétrie et aplatissement (non excédentaire, 3 pour la loi normale)."""
    n = len(x)
    m = sum(x) / n
    c2 = sum((v - m) ** 2 for v in x) / n
    if c2 == 0:
        return m, 0.0, 0.0, 3.0
    c3 = sum((v - m) ** 3 for v in x) / n
    c4 = sum((v - m) ** 4 for v in x) / n
    return m, math.sqrt(c2 * n / (n - 1)), c3 / c2 ** 1.5, c4 / c2 ** 2


def sr_attendu_max(essais: int, var_sr: float) -> float:
    """Le Sharpe que le meilleur de N essais sans avantage atteindrait (Bailey et López de Prado, 2014)."""
    if essais <= 1:
        return 0.0
    return math.sqrt(var_sr) * ((1 - EULER) * _N.inv_cdf(1 - 1 / essais)
                                + EULER * _N.inv_cdf(1 - 1 / (essais * math.e)))


def dsr(serie: list[float], essais: int = 1, var_sr: float = 0.0) -> dict:
    """Le Sharpe dégonflé d'une série de rendements par période (non annualisé)."""
    m, s, g3, g4 = moments(serie)
    T = len(serie)
    if s == 0 or T < 3:
        return {"sr": 0.0, "sr0": 0.0, "dsr": 0.0, "T": T}
    sr = m / s
    sr0 = sr_attendu_max(essais, var_sr)
    den = 1 - g3 * sr + (g4 - 1) / 4 * sr * sr
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(max(den, 1e-12))
    return {"sr": sr, "sr0": sr0, "dsr": stats.Phi(z), "T": T, "asym": g3, "aplat": g4}


# ---------------------------------------------------------------------------
# La courbe de spécification et les parts dans le même sens
# ---------------------------------------------------------------------------

def resume_spec(effets: list[float], ps: list[float], sens: int) -> dict:
    """Part des réglages dans le sens annoncé, et part significative dans ce sens."""
    signe = sens if sens != 0 else (1 if sorted(effets)[len(effets) // 2] >= 0 else -1)
    meme = [e * signe > 0 for e in effets]
    sig = [m and p < 0.05 for m, p in zip(meme, ps)]
    ordre = sorted(effets)
    return {"n": len(effets), "meme_sens": sum(meme) / len(meme), "signif": sum(sig) / len(sig),
            "mediane": ordre[len(ordre) // 2], "bas": ordre[0], "haut": ordre[-1], "signe": signe}


def part_meme_sens(effets: list[float], sens: int) -> float:
    signe = sens if sens != 0 else (1 if sorted(effets)[len(effets) // 2] >= 0 else -1)
    return sum(1 for e in effets if e * signe > 0) / len(effets)


# ---------------------------------------------------------------------------
# Tirages : Poisson(1) et hypercube latin
# ---------------------------------------------------------------------------

_CDF_POISSON1 = []
_acc = 0.0
for _k in range(12):
    _acc += math.exp(-1.0) / math.factorial(_k)
    _CDF_POISSON1.append(_acc)


def poisson1(alea) -> int:
    u = alea.random()
    for k, c in enumerate(_CDF_POISSON1):
        if u <= c:
            return k
    return len(_CDF_POISSON1)


def hypercube(domaine: dict, n: int, nom: str) -> list[dict]:
    """Hypercube latin (McKay, Beckman et Conover, 1979) : chaque paramètre visite chacune de ses n tranches
    une fois. Un domaine d'entiers (deux entiers) est tiré en entiers."""
    alea = stats.rng(f"lhs-{nom}")
    colonnes = {}
    for cle, (a, b) in domaine.items():
        tranches = list(range(n))
        alea.shuffle(tranches)
        if isinstance(a, int) and isinstance(b, int):
            colonnes[cle] = [min(b, a + int((t + alea.random()) / n * (b - a + 1))) for t in tranches]
        else:
            colonnes[cle] = [a + (t + alea.random()) / n * (b - a) for t in tranches]
    return [{cle: colonnes[cle][i] for cle in domaine} for i in range(n)]


# ---------------------------------------------------------------------------
# L'étalonnage sur vérité connue
# ---------------------------------------------------------------------------

def etalonner_spa(essais: int = 200, K: int = 12, G: int = 200, tirages: int = 199, effet: float = 0.0) -> dict:
    """SPA sous l'hypothèse nulle (aucun réglage ne bat la référence) et sous un vrai avantage.

    Chaque réglage est la moyenne de G contributions normales corrélées entre
    réglages (un même facteur commun, comme des réglages voisins sur les mêmes
    clients) ; le premier réglage reçoit `effet` écarts-types d'avance."""
    alea = stats.rng(f"etal-spa-{effet}")
    rejets_spa = rejets_rc = 0
    for e in range(essais):
        commun = [alea.gauss(0, 1) for _ in range(G)]
        influence, d = [], []
        for k in range(K):
            x = [0.7 * c + 0.71 * alea.gauss(0, 1) for c in commun]
            m = sum(x) / G
            inf = [(v - m) / G for v in x]
            s = math.sqrt(sum(v * v for v in inf))
            d.append(m + (effet * s if k == 0 else 0.0))
            influence.append(inf)
        r = spa(d, influence, tirages, f"etal-{effet}-{e}")
        rejets_spa += r["p_spa"] < 0.05
        rejets_rc += r["p_rc"] < 0.05
    return {"essais": essais, "spa": rejets_spa / essais, "rc": rejets_rc / essais, "effet": effet}


def etalonner_cscv(essais: int = 60, K: int = 12, S: int = 16, avance: float = 0.0) -> dict:
    """PBO quand tous les réglages se valent (attendu : environ 0,5) et quand l'un a une vraie avance."""
    alea = stats.rng(f"etal-cscv-{avance}")
    pbo, perte = [], []
    for _ in range(essais):
        perf = [[alea.gauss(avance if k == 0 else 0.0, 1.0) for _ in range(S)] for k in range(K)]
        r = cscv(perf)
        pbo.append(r["pbo"])
        perte.append(r["perte"])
    return {"essais": essais, "pbo": sum(pbo) / essais, "perte": sum(perte) / essais, "avance": avance}


def etalonner_dsr(essais: int = 2000, T: int = 52, N: int = 10) -> dict:
    """Part des séries sans avantage dont le meilleur de N essais passe DSR ≥ 0,95 (attendu ≤ 5 %)."""
    alea = stats.rng("etal-dsr")
    passe = 0
    passe_naif = 0
    for _ in range(essais):
        series = [[alea.gauss(0, 1) for _ in range(T)] for _ in range(N)]
        srs = [moments(s)[0] / moments(s)[1] for s in series]
        k = max(range(N), key=lambda i: srs[i])
        m = sum(srs) / N
        var = sum((v - m) ** 2 for v in srs) / (N - 1)
        passe += dsr(series[k], N, var)["dsr"] >= 0.95
        passe_naif += dsr(series[k], 1)["dsr"] >= 0.95
    return {"essais": essais, "dsr": passe / essais, "sans_correction": passe_naif / essais, "T": T, "N": N}


def etalonner_holm(essais: int = 2000, m: int = 25) -> dict:
    """Part des familles de m tests nuls qui contiennent au moins une fausse alerte (attendu ≤ 5 %)."""
    alea = stats.rng("etal-holm")
    fausses = brutes = 0
    for _ in range(essais):
        p = [alea.random() for _ in range(m)]
        fausses += min(holm(p)) < 0.05
        brutes += min(p) < 0.05
    return {"essais": essais, "holm": fausses / essais, "sans_correction": brutes / essais, "m": m}


def main() -> None:
    print(etalonner_holm())
    print(etalonner_dsr())
    print(etalonner_cscv())
    print(etalonner_cscv(avance=1.0))
    print(etalonner_spa(essais=100))
    print(etalonner_spa(essais=100, effet=3.0))


if __name__ == "__main__":
    main()
