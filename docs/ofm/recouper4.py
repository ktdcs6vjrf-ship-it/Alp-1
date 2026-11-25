"""Recoupe les outils du cahier nº 4 (bibliothèque standard) avec les bibliothèques de référence.

Ce script ne fait pas partie de la chaîne : il tourne dans un environnement à
part, où numpy, scipy, statsmodels et arch sont installés, et écrit
`ofm/donnees/RECOUPEMENT4.json`. Le cahier lit ce fichier pour dire, chiffres à
l'appui, que ses outils rendent ce que rendent ceux du marché.

    python -m venv ref && ref/bin/pip install numpy scipy statsmodels arch
    ref/bin/python docs/ofm/recouper4.py

Le CSCV n'a pas de version publiée sur PyPI : il est recoupé par une seconde
écriture, vectorisée et indépendante, de la méthode de Bailey et al. (2017).
"""

from __future__ import annotations

import json
import math
import sys
from itertools import combinations
from pathlib import Path

import arch
import numpy as np
import scipy
import statsmodels
from arch.bootstrap import SPA
from scipy import stats as sst
from statsmodels.stats.multitest import multipletests

ICI = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ICI))

from ofm import bandit, baleines, cibler, stats, stress  # noqa: E402

rng = np.random.default_rng(20261125)
out = {"versions": {"numpy": np.__version__, "scipy": scipy.__version__, "statsmodels": statsmodels.__version__,
                    "arch": arch.__version__, "python": sys.version.split()[0]}}

# 1. Benjamini-Hochberg et Holm (statsmodels)
d_bh = d_holm = 0.0
for _ in range(2000):
    p = rng.uniform(0, 1, 25) ** rng.uniform(0.3, 3)
    d_bh = max(d_bh, float(np.max(np.abs(np.array(stats.bh(list(p))) - multipletests(p, method="fdr_bh")[1]))))
    d_holm = max(d_holm, float(np.max(np.abs(np.array(stress.holm(list(p))) - multipletests(p, method="holm")[1]))))
out["bh"] = {"cas": 2000, "ecart_max": d_bh, "reference": "statsmodels.multipletests(fdr_bh)"}
out["holm"] = {"cas": 2000, "ecart_max": d_holm, "reference": "statsmodels.multipletests(holm)"}

# 2. Loi normale (scipy)
xs = np.linspace(-8, 8, 4001)
ps = np.concatenate([np.logspace(-12, -1, 200), np.linspace(0.1, 0.9, 200), 1 - np.logspace(-12, -1, 200)])
out["normale"] = {"Phi_ecart_max": float(max(abs(stats.Phi(x) - sst.norm.cdf(x)) for x in xs)),
                  "Phi_inv_ecart_max": float(max(abs(stats.Phi_inv(p) - sst.norm.ppf(p)) for p in ps)),
                  "reference": "scipy.stats.norm"}

# 3. Test binomial exact (scipy) : les cas des baleines et une grille
cas = [(baleines.mesure(j)["nouveaux"], baleines.mesure(j)["n"]) for j in ("cdnow", "retail", "x5")]
cas += [(int(k), int(n)) for n in (5, 17, 43, 100, 251) for k in np.linspace(0, n, 7)]
out["binomial"] = {"cas": len(cas), "reference": "scipy.stats.binomtest(two-sided)",
                   "ecart_max": float(max(abs(baleines._binomial_p(k, n) - sst.binomtest(k, n, 0.5).pvalue)
                                          for k, n in cas))}

# 4. Khi-deux (Wilson-Hilferty contre scipy), là où le cahier s'en sert (k ≥ 3)
grille = [(x, k) for k in (3, 10, 50, 200, 900) for x in np.linspace(0.2 * k, 2.5 * k, 25)]
out["khi2"] = {"cas": len(grille), "reference": "scipy.stats.chi2.sf",
               "ecart_max": float(max(abs(bandit._khi2_sup(x, k) - sst.chi2.sf(x, k)) for x, k in grille))}

# 5. Sharpe dégonflé : seconde écriture (scipy pour les moments et la loi normale)
def dsr_ref(r, n, var):
    sr = r.mean() / r.std(ddof=1)
    g3, g4 = sst.skew(r), sst.kurtosis(r, fisher=False)
    e = 0.5772156649015329
    sr0 = 0.0 if n <= 1 else math.sqrt(var) * ((1 - e) * sst.norm.ppf(1 - 1 / n) + e * sst.norm.ppf(1 - 1 / (n * math.e)))
    return sst.norm.cdf((sr - sr0) * math.sqrt(len(r) - 1) / math.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2))

d_dsr = 0.0
for _ in range(300):
    r = rng.standard_t(5, size=int(rng.integers(7, 300))) * 0.01 + rng.uniform(-0.002, 0.004)
    n, var = int(rng.integers(1, 20)), float(rng.uniform(0.01, 2))
    d_dsr = max(d_dsr, abs(stress.dsr(list(r), n, var)["dsr"] - dsr_ref(r, n, var)))
out["dsr"] = {"cas": 300, "ecart_max": float(d_dsr), "reference": "seconde écriture avec scipy (skew, kurtosis, norm)"}

# 6. SPA : notre bootstrap à multiplicateurs contre la SPA d'arch (bootstrap stationnaire, blocs de 1)
pa, pb = [], []
for e in range(60):
    T, K = 1000, 12
    commun = rng.normal(size=(T, 1))
    x = 0.7 * commun + 0.71 * rng.normal(size=(T, K))
    x[:, 0] += 0.12 if e % 2 else 0.0          # un essai sur deux : le premier réglage a une vraie avance
    bench = np.zeros(T)
    spa = SPA(bench, -x, reps=999, block_size=1, bootstrap="stationary", studentize=True, nested=False, seed=e)
    spa.compute()
    pa.append(float(spa.pvalues["consistent"]))
    d = list(x.mean(axis=0))
    inf = [list((x[:, k] - x[:, k].mean()) / T) for k in range(K)]
    pb.append(stress.spa(d, inf, 999, f"recoupe-{e}")["p_spa"])
pa, pb = np.array(pa), np.array(pb)
out["spa"] = {"cas": 60, "reference": "arch.bootstrap.SPA (consistent, stationnaire, blocs de 1)",
              "ecart_moyen": float(np.mean(np.abs(pa - pb))), "ecart_max": float(np.max(np.abs(pa - pb))),
              "accord_5pct": float(np.mean((pa < 0.05) == (pb < 0.05))),
              "correlation": float(np.corrcoef(pa, pb)[0, 1])}

# 7. CSCV : seconde écriture, vectorisée
def cscv_ref(perf):
    perf = np.asarray(perf)
    K, S = perf.shape
    lam, perte = [], []
    for a in combinations(range(S), S // 2):
        m = np.zeros(S, bool)
        m[list(a)] = True
        is_, oos = perf[:, m].mean(axis=1), perf[:, ~m].mean(axis=1)
        k = int(np.argmax(is_))
        rang = 1 + np.sum(oos < oos[k]) + 0.5 * (np.sum(oos == oos[k]) - 1)
        w = rang / (K + 1)
        lam.append(math.log(w / (1 - w)))
        perte.append(oos[k] <= 0)
    lam = np.array(lam)
    return float(np.mean(lam <= 0)), float(np.mean(perte))

d_pbo = d_perte = 0.0
for e in range(12):
    perf = rng.normal(size=(9, 16)) + (np.arange(9)[:, None] == 0) * rng.uniform(0, 1.2)
    a = stress.cscv(perf.tolist())
    b = cscv_ref(perf)
    d_pbo = max(d_pbo, abs(a["pbo"] - b[0]))
    d_perte = max(d_perte, abs(a["perte"] - b[1]))
out["cscv"] = {"cas": 12, "ecart_pbo_max": d_pbo, "ecart_perte_max": d_perte,
               "reference": "seconde écriture vectorisée (numpy) de Bailey et al. (2017)"}

# 8. Moindres carrés : cibler.ols contre numpy.linalg.lstsq (Hillstrom, une variable par colonne)
rows = cibler.JEUX["hillstrom"]()[:20000]
noms = ("recence", "log_historique", "hommes", "femmes", "nouveau", "zone_s", "zone_r", "canal_w", "canal_m")
cols = [[1.0] * len(rows)] + [[float(r[0][v]) for r in rows] for v in noms]
y = [r[2] for r in rows]
b_nous = cibler.ols(cols, y)
b_ref = np.linalg.lstsq(np.array(cols).T, np.array(y), rcond=None)[0]
out["mco"] = {"coefficients": len(b_nous), "ecart_max": float(np.max(np.abs(np.array(b_nous) - b_ref))),
              "reference": "numpy.linalg.lstsq"}

# 9. Permutation du bandit contre le test exact de Fisher (une campagne)
fisher = []
for c in ("all", "men", "women"):
    nb, cb, nr, cr = bandit._compte(bandit.lignes(c))
    fisher.append({"campagne": c, "nous": bandit.mesure((c,))["p"],
                   "fisher": float(sst.fisher_exact([[cb, nb - cb], [cr, nr - cr]])[1])})
out["bandit"] = {"reference": "scipy.stats.fisher_exact (bilatéral)", "cas": fisher,
                 "ecart_max": max(abs(f["nous"] - f["fisher"]) for f in fisher)}

cible = ICI / "ofm" / "donnees" / "RECOUPEMENT4.json"
cible.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))
