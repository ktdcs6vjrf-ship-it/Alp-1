"""Mesurer chez soi — étalonnages sur séries synthétiques de vérité connue.

Aucun chiffre de ce module ne vient d'une agence. Ce sont des **expériences de
pensée chiffrées** : on fabrique des fans dont on connaît le jour de paie,
l'heure préférée ou l'absence de tout effet, et l'on regarde ce qu'une méthode
en retrouve. C'est la seule façon de savoir, avant de lire ses propres
exports, combien d'achats il faut pour que la lecture ne soit pas du bruit.
"""

from __future__ import annotations

import math
from functools import lru_cache

from . import stats

ALPHA = 0.05
PUISSANCE = 0.80


# ---------------------------------------------------------------------------
# Budget d'un test A/B
# ---------------------------------------------------------------------------

BASES = (0.30, 0.20, 0.10, 0.05, 0.02, 0.01)
HAUSSES = (1.00, 0.50, 0.30, 0.20, 0.10, 0.05)


def surface_budget() -> list[list[float]]:
    """log10 du nombre d'envois par variante, base (lignes) × hausse relative (colonnes)."""
    return [[math.log10(stats.n_par_bras(p, h)) for h in HAUSSES] for p in BASES]


def effet_de_grappe(m: float, rho: float) -> float:
    """Facteur de plan : m messages par fan, corrélation intra-fan rho."""
    return 1 + (m - 1) * rho


# ---------------------------------------------------------------------------
# Regarder trop souvent
# ---------------------------------------------------------------------------

REGARDS = (1, 2, 5, 10, 20, 50, 100)


@lru_cache(maxsize=1)
def regarder(experiences: int = 4000, n_bras: int = 20000, p: float = 0.05,
             tau: float = 0.005) -> dict:
    """Faux positifs d'un test A/A qu'on regarde k fois, et ceux d'un test toujours valide.

    Chaque expérience est un chemin unique, observé à 100 dates régulières ; un
    test à k regards en garde k, équiréparties. Les mêmes chemins servent à
    tous les k, si bien que la courbe ne peut que monter. Le test toujours
    valide est un mSPRT à mélange normal (Johari et al.) de variance de mélange
    `tau²`, paramètre déclaré, jamais réglé sur ce qu'il évalue.
    """
    alea = stats.rng("regarder")
    K = max(REGARDS)
    m = n_bras // K
    naif = {k: 0 for k in REGARDS}
    msprt = {k: 0 for k in REGARDS}
    sd = math.sqrt(m * p * (1 - p))
    for _ in range(experiences):
        a = b = 0.0
        z_path, l_path = [], []
        for t in range(1, K + 1):
            a += m * p + sd * alea.gauss(0, 1)
            b += m * p + sd * alea.gauss(0, 1)
            n = t * m
            pa, pb = a / n, b / n
            pm = (pa + pb) / 2
            v = 2 * max(pm * (1 - pm), 1e-9) / n
            d = pa - pb
            z_path.append(d / math.sqrt(v))
            l_path.append(0.5 * math.log(v / (v + tau * tau)) + tau * tau * d * d / (2 * v * (v + tau * tau)))
        seuil = math.log(1 / ALPHA)
        for k in REGARDS:
            idx = [round((j + 1) * K / k) - 1 for j in range(k)]
            if any(abs(z_path[i]) > 1.959964 for i in idx):
                naif[k] += 1
            if any(l_path[i] >= seuil for i in idx):
                msprt[k] += 1
    return {"naif": {k: v / experiences for k, v in naif.items()},
            "msprt": {k: v / experiences for k, v in msprt.items()},
            "experiences": experiences, "n_bras": n_bras, "p": p, "tau": tau}


# ---------------------------------------------------------------------------
# La malédiction du gagnant
# ---------------------------------------------------------------------------

def esperance_max(k: int, pas: int = 4000) -> float:
    """E[max de k normales centrées réduites], par intégration numérique."""
    if k == 1:
        return 0.0
    lo, hi = -8.0, 8.0
    h = (hi - lo) / pas
    s = 0.0
    for i in range(pas + 1):
        x = lo + i * h
        w = 0.5 if i in (0, pas) else 1.0
        s += w * x * k * stats.phi(x) * stats.Phi(x) ** (k - 1)
    return s * h


VARIANTES = (20, 12, 8, 5, 3, 2)
ENVOIS = (500, 1000, 2000, 5000, 10000, 20000)


def surface_gagnant(p0: float = 0.05) -> list[list[float]]:
    """Hausse relative mesurée du meilleur de k variantes **sans aucun effet**."""
    return [[esperance_max(k) * math.sqrt(2 * p0 * (1 - p0) / n) / p0 for n in ENVOIS]
            for k in VARIANTES]


# ---------------------------------------------------------------------------
# Le jour de paie d'un fan
# ---------------------------------------------------------------------------

CYCLE = 14          # paie toutes les deux semaines, la cadence la plus répandue
FENETRE = 3         # jours de dépense accrue après la paie
JOURS = 182         # six mois d'historique : treize cycles exacts
ACHATS = (4, 6, 8, 12, 16, 24, 32)
AMPLITUDES = (5.0, 3.0, 2.0, 1.0, 0.5)


def _stat_paie(jours: list[int]) -> tuple[int, int]:
    """Plus grand nombre d'achats tombant dans une fenêtre de trois jours du cycle."""
    c = [0] * CYCLE
    for d in jours:
        c[d % CYCLE] += 1
    best, phase = -1, 0
    for f in range(CYCLE):
        s = sum(c[(f + k) % CYCLE] for k in range(FENETRE))
        if s > best:
            best, phase = s, f
    return best, phase


def _tirer(alea, n: int, phase: int, amp: float) -> list[int]:
    poids = [1.0 + (amp if (d - phase) % CYCLE < FENETRE else 0.0) for d in range(JOURS)]
    tot = sum(poids)
    cumul, acc = [], 0.0
    for w in poids:
        acc += w / tot
        cumul.append(acc)
    out = []
    for _ in range(n):
        u = alea.random()
        lo, hi = 0, JOURS - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cumul[mid] < u:
                lo = mid + 1
            else:
                hi = mid
        out.append(lo)
    return out


@lru_cache(maxsize=1)
def paie(tirages: int = 1500) -> dict:
    """Puissance de détection et justesse de la phase, par achats × amplitude.

    La loi nulle se tire pour chaque nombre d'achats : des jours uniformes sur
    six mois, la même statistique, son quantile à 95 %. Une phase est « juste »
    si elle tombe à un jour près de la vraie.
    """
    alea = stats.rng("paie")
    seuils = {}
    for n in ACHATS:
        nul = sorted(_stat_paie(_tirer(alea, n, 0, 0.0))[0] for _ in range(4000))
        s = nul[int(0.95 * len(nul))]
        frac_eg = (0.95 * len(nul) - sum(1 for v in nul if v < s)) / max(1, sum(1 for v in nul if v == s))
        seuils[n] = (s, sum(1 for v in nul if v > s) / len(nul), frac_eg)
    puissance, justesse = [], []
    for amp in AMPLITUDES:
        lp, lj = [], []
        for n in ACHATS:
            s, _, _ = seuils[n]
            ok = juste = 0
            for _ in range(tirages):
                ph = alea.randrange(CYCLE)
                st, f = _stat_paie(_tirer(alea, n, ph, amp))
                ok += st > s
                d = min((f - ph) % CYCLE, (ph - f) % CYCLE)
                juste += d <= 1
            lp.append(ok / tirages)
            lj.append(juste / tirages)
        puissance.append(lp)
        justesse.append(lj)
    taux_nul = {n: seuils[n][1] for n in ACHATS}
    return {"puissance": puissance, "justesse": justesse, "faux_positifs": taux_nul,
            "seuils": {n: seuils[n][0] for n in ACHATS}}


# ---------------------------------------------------------------------------
# L'heure d'un fan
# ---------------------------------------------------------------------------

MESSAGES = (160, 80, 40, 20, 10, 5)
CONCENTRATIONS = (4.0, 2.0, 1.0, 0.5, 0.25)


@lru_cache(maxsize=1)
def horloge(tirages: int = 1200) -> dict:
    """Erreur médiane (heures) sur l'heure de pointe, et puissance du test de Rayleigh."""
    alea = stats.rng("horloge")
    erreur, puiss = [], []
    for kappa in CONCENTRATIONS:
        le, lp = [], []
        for n in MESSAGES:
            errs, ok = [], 0
            for _ in range(tirages):
                mu = alea.uniform(0, 2 * math.pi)
                a = [alea.vonmisesvariate(mu, kappa) for _ in range(n)]
                _, mh, p = stats.rayleigh(a)
                d = abs((mh - mu + math.pi) % (2 * math.pi) - math.pi)
                errs.append(d * 24 / (2 * math.pi))
                ok += p < ALPHA
            le.append(stats.quantile(errs, 0.5))
            lp.append(ok / tirages)
        erreur.append(le)
        puiss.append(lp)
    return {"erreur": erreur, "puissance": puiss}


def main() -> None:
    r = regarder()
    print("regards naïfs", r["naif"])
    print("regards mSPRT", r["msprt"])
    print("gagnant", [[round(v, 3) for v in l] for l in surface_gagnant()])
    pa = paie()
    print("paie fp", pa["faux_positifs"])
    for amp, l in zip(AMPLITUDES, pa["puissance"]):
        print("paie A", amp, [round(v, 2) for v in l])
    h = horloge()
    for k, l in zip(CONCENTRATIONS, h["erreur"]):
        print("horloge κ", k, [round(v, 2) for v in l])


if __name__ == "__main__":
    main()
