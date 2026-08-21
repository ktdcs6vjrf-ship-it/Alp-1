"""Contrôle du surajustement : sélection, tests multiples, validation croisée.

C'est le module qui répond à la question posée au papier — la stratégie
offre-t-elle un edge *sans surajustement* ? — et sa réponse tient dans une
inversion de perspective.

Un backtest ne produit jamais un Sharpe. Il produit le **maximum** d'un
ensemble de Sharpe : ceux de toutes les variantes essayées, y compris celles
qu'on n'a pas notées, y compris celles qu'on a écartées d'un coup d'œil. La
loi d'un maximum n'est pas celle d'un tirage, et l'écart entre les deux est
l'intégralité du surajustement.

Trois familles d'instruments l'encadrent.

**Déflation.** Le Sharpe attendu du meilleur de `N` essais sans aucun edge
croît en `√(2·ln N)`. Le Sharpe dégonflé (Bailey & López de Prado) le
retranche, et la longueur minimale de backtest en découle directement.

**Correction de tests multiples.** Bonferroni, Holm, Benjamini-Hochberg-
Yekutieli : trois niveaux de sévérité, du contrôle du risque de première
espèce familial au contrôle du taux de fausses découvertes. Harvey, Liu et
Zhu en tirent une décote de Sharpe directement lisible.

**Validation croisée honnête.** Purge et embargo suppriment le recouvrement
entre échantillon d'apprentissage et échantillon de test — sans quoi une
stratégie dont les trades durent une demi-heure fuite d'un pli à l'autre. La
CSCV donne la probabilité de surajustement du backtest lui-même : non pas
« ce jeu de paramètres est-il bon ? », mais « le meilleur en apprentissage
est-il meilleur que la médiane en test ? ».
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations

from .costs import _norm_ppf, norm_cdf as _norm_cdf
from .pathstats import EULER_GAMMA, probabilistic_sharpe


# --- Déflation du Sharpe ----------------------------------------------------


def expected_max_sharpe(n_trials: int, sd_trials: float = 1.0) -> float:
    """Sharpe attendu du **meilleur** de `n_trials` essais sans edge.

    Approximation de valeur extrême de Bailey & López de Prado :

        E[max ŜR] ≈ σ_essais·[(1 − γ)·Φ⁻¹(1 − 1/N) + γ·Φ⁻¹(1 − 1/(N·e))],

    où `γ` est la constante d'Euler-Mascheroni. `σ_essais` est l'écart-type
    des Sharpe **entre configurations essayées** ; en l'absence de cette
    mesure, `1/√(n_obs)` en donne l'ordre de grandeur sous indépendance.

    C'est la barre à franchir, et elle monte avec le nombre d'essais sans que
    la stratégie ait changé d'un iota.
    """
    if n_trials < 2:
        return 0.0
    a = _norm_ppf(1.0 - 1.0 / n_trials)
    b = _norm_ppf(1.0 - 1.0 / (n_trials * math.e))
    return sd_trials * ((1.0 - EULER_GAMMA) * a + EULER_GAMMA * b)


def deflated_sharpe(
    sharpe_hat: float,
    n_obs: int,
    n_trials: int,
    skew: float = 0.0,
    excess_kurtosis: float = 0.0,
    sd_trials: float | None = None,
) -> float:
    """Deflated Sharpe Ratio : `PSR` évalué contre le seuil de sélection.

    `DSR = PSR(SR₀)` où `SR₀ = E[max ŜR | N essais, aucun edge]`. C'est une
    probabilité : la probabilité que le Sharpe vrai soit positif *une fois
    retiré ce que la sélection explique à elle seule*. En dessous de 0,95, le
    résultat n'est pas déclarable.

    Tous les Sharpe sont par observation. Convertir en annualisé avant de
    déflater est l'erreur qui rend l'instrument inopérant.
    """
    sd = sd_trials if sd_trials is not None else 1.0 / math.sqrt(max(n_obs, 1))
    sr0 = expected_max_sharpe(n_trials, sd)
    return probabilistic_sharpe(sharpe_hat, n_obs, sr0, skew, excess_kurtosis)


def minimum_backtest_length(sharpe_hat: float, n_trials: int) -> float:
    """Observations minimales pour qu'un Sharpe résiste à `n_trials` essais.

    En égalant le Sharpe observé au seuil de sélection `√(2 ln N)/√n` :

        MinBTL ≈ [(1 − γ)Φ⁻¹(1 − 1/N) + γΦ⁻¹(1 − 1/(N·e))]² / ŜR².

    Lecture opérationnelle : à Sharpe par trade fixé, chaque décuplement du
    nombre de configurations essayées exige un allongement de l'historique
    d'environ 40 % — et l'historique disponible, lui, est fixe.
    """
    if sharpe_hat <= 0:
        return math.inf
    z = expected_max_sharpe(n_trials, 1.0)
    return (z / sharpe_hat) ** 2


# --- Tests multiples --------------------------------------------------------


def bonferroni_threshold(alpha: float, n_tests: int) -> float:
    """Seuil de p-valeur contrôlant le risque familial : `α/N`. Le plus sévère."""
    if n_tests < 1:
        raise ValueError("n_tests doit être >= 1")
    return alpha / n_tests


def holm_thresholds(alpha: float, n_tests: int) -> list[float]:
    """Seuils de Holm, appliqués aux p-valeurs triées : `α/(N − i + 1)`.

    Uniformément plus puissant que Bonferroni, et sans hypothèse
    supplémentaire : il n'y a jamais de raison de préférer Bonferroni à Holm,
    sinon la simplicité de la formule.
    """
    if n_tests < 1:
        raise ValueError("n_tests doit être >= 1")
    return [alpha / (n_tests - i) for i in range(n_tests)]


def bhy_threshold(alpha: float, n_tests: int, rank: int | None = None) -> float:
    """Seuil de Benjamini-Hochberg-Yekutieli au rang `rank`.

        p_(i) ≤ (i/N)·α / Σ_{j=1}^{N} 1/j

    Contrôle le **taux de fausses découvertes** sous dépendance arbitraire —
    l'hypothèse qui convient aux stratégies, dont les variantes sont toujours
    corrélées entre elles. C'est le compromis retenu par Harvey, Liu et Zhu
    pour la littérature de facteurs, et le plus défendable des trois ici.
    """
    if n_tests < 1:
        raise ValueError("n_tests doit être >= 1")
    r = n_tests if rank is None else rank
    c = sum(1.0 / j for j in range(1, n_tests + 1))
    return (r / n_tests) * alpha / c


def adjusted_pvalue(p_value: float, n_tests: int, method: str = "bhy") -> float:
    """p-valeur corrigée pour `n_tests` tests simultanés, au rang 1.

    Trois sévérités : Bonferroni multiplie par `N` ; Holm fait de même au
    rang 1, et se relâche ensuite ; Benjamini-Hochberg-Yekutieli multiplie par
    `N·c(N)` avec `c(N) = Σ_{j≤N} 1/j`, ce qui contrôle le taux de fausses
    découvertes sous dépendance quelconque.
    """
    if not 0.0 <= p_value <= 1.0:
        raise ValueError("p_value doit être dans [0, 1]")
    if n_tests < 1:
        raise ValueError("n_tests doit être >= 1")
    if method in ("bonferroni", "holm"):
        return min(1.0, p_value * n_tests)
    if method == "bhy":
        c = sum(1.0 / j for j in range(1, n_tests + 1))
        return min(1.0, p_value * n_tests * c)
    raise ValueError("méthode inconnue : bonferroni, holm ou bhy")


def haircut_sharpe(sharpe_hat: float, n_obs: int, n_tests: int,
                   method: str = "bhy") -> float:
    """Décote de Sharpe pour tests multiples (Harvey, Liu & Zhu, 2016).

    Le chemin est celui des auteurs, et il ne fait intervenir aucun seuil de
    signification arbitraire : le Sharpe observé donne une t-statistique
    `t = ŜR·√n`, donc une p-valeur ; la p-valeur est corrigée du nombre de
    tests ; la p-valeur corrigée est reconvertie en t-statistique, puis en
    Sharpe. La décote retournée est la **fraction du Sharpe qui disparaît** :

        décote = 1 − ŜR_ajusté/ŜR.

    Elle ne dépend que de trois nombres — le Sharpe, la longueur de
    l'historique, le nombre d'essais — et elle est, de tout le module, la
    correction la plus directement lisible par un allocataire.
    """
    if sharpe_hat <= 0 or n_obs < 2:
        return 1.0
    t = sharpe_hat * math.sqrt(n_obs)
    p = 1.0 - _norm_cdf(t)
    p_adj = adjusted_pvalue(max(p, 1e-300), n_tests, method)
    if p_adj >= 0.5:
        return 1.0
    t_adj = _norm_ppf(1.0 - p_adj)
    sharpe_adj = t_adj / math.sqrt(n_obs)
    return max(0.0, 1.0 - sharpe_adj / sharpe_hat)


# --- Probabilité de surajustement du backtest -------------------------------


@dataclass(frozen=True)
class CSCVResult:
    """Sortie d'une validation croisée combinatoirement symétrique."""

    pbo: float                  # P(le meilleur en apprentissage soit sous la médiane en test)
    n_splits: int
    median_logit: float
    degradation: float          # perte moyenne de performance, apprentissage → test


def cscv(performance: list[list[float]], n_blocks: int = 8) -> CSCVResult:
    """CSCV et probabilité de surajustement (Bailey, Borwein, López de Prado).

    `performance[s][t]` est la performance de la configuration `s` sur la
    sous-période `t`. La série est découpée en `n_blocks` blocs ; pour chacune
    des `C(n, n/2)` partitions symétriques, la configuration la meilleure en
    apprentissage est retenue, et l'on regarde son **rang relatif** en test.

    La PBO est la fréquence des cas où ce rang tombe sous la médiane. Sur des
    configurations sans edge, elle vaut ½ par symétrie ; au-delà, la sélection
    fait activement pire que le hasard, ce qui est le signe d'un backtest
    conduit par le bruit.

    Note d'usage : la PBO ne mesure pas si la stratégie gagne. Elle mesure si
    *la procédure de sélection* est informative. Une PBO basse sur une famille
    de configurations toutes perdantes ne sauve rien.
    """
    n_configs = len(performance)
    if n_configs < 2:
        raise ValueError("il faut au moins deux configurations")
    n_periods = len(performance[0])
    if any(len(row) != n_periods for row in performance):
        raise ValueError("toutes les configurations doivent couvrir les mêmes périodes")
    if n_blocks < 2 or n_blocks % 2:
        raise ValueError("n_blocks doit être pair et >= 2")
    if n_periods < n_blocks:
        raise ValueError("pas assez de périodes pour ce découpage")

    edges = [round(i * n_periods / n_blocks) for i in range(n_blocks + 1)]
    blocks = [list(range(edges[i], edges[i + 1])) for i in range(n_blocks)]

    logits: list[float] = []
    degradations: list[float] = []
    half = n_blocks // 2
    for train_ids in combinations(range(n_blocks), half):
        train_set = set(train_ids)
        tr_idx = [i for b in train_ids for i in blocks[b]]
        te_idx = [i for b in range(n_blocks) if b not in train_set for i in blocks[b]]
        tr = [_mean([row[i] for i in tr_idx]) for row in performance]
        te = [_mean([row[i] for i in te_idx]) for row in performance]
        best = max(range(n_configs), key=lambda s: tr[s])
        order = sorted(range(n_configs), key=lambda s: te[s])
        rank = order.index(best) + 1
        omega = rank / (n_configs + 1.0)
        omega = min(max(omega, 1e-9), 1.0 - 1e-9)
        logits.append(math.log(omega / (1.0 - omega)))
        degradations.append(tr[best] - te[best])

    pbo = sum(1 for lg in logits if lg <= 0.0) / len(logits)
    return CSCVResult(
        pbo=pbo,
        n_splits=len(logits),
        median_logit=_median(logits),
        degradation=_mean(degradations),
    )


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


# --- Validation croisée purgée ----------------------------------------------


@dataclass(frozen=True)
class Fold:
    """Un pli de validation croisée purgée : indices de test et d'apprentissage."""

    test: tuple[int, ...]
    train: tuple[int, ...]


def purged_folds(n_obs: int, n_folds: int = 5, horizon: int = 1,
                 embargo_pct: float = 0.01) -> list[Fold]:
    """Validation croisée purgée avec embargo (López de Prado, 2018).

    Deux corrections, toutes deux indispensables dès que les étiquettes se
    chevauchent dans le temps — ce qui est le cas de tout trade de durée non
    nulle :

    * **purge** : on retire de l'apprentissage toute observation dont
      l'étiquette recouvre la fenêtre de test (`horizon` périodes) ;
    * **embargo** : on retire en plus les `embargo_pct` d'observations qui
      suivent immédiatement le test, pour couper la corrélation sérielle
      résiduelle.

    Sans purge, une stratégie dont les trades durent `h` périodes fuite `h`
    observations par bord de pli, et la validation croisée « valide » un
    modèle qui a vu son propre futur.
    """
    if n_obs < n_folds or n_folds < 2:
        raise ValueError("paramètres de découpage invalides")
    if horizon < 0 or embargo_pct < 0:
        raise ValueError("horizon et embargo doivent être >= 0")
    embargo = int(math.ceil(embargo_pct * n_obs))
    edges = [round(i * n_obs / n_folds) for i in range(n_folds + 1)]
    folds: list[Fold] = []
    for i in range(n_folds):
        lo, hi = edges[i], edges[i + 1]
        test = tuple(range(lo, hi))
        banned_lo = max(0, lo - horizon)
        banned_hi = min(n_obs, hi + horizon + embargo)
        train = tuple(j for j in range(n_obs) if not banned_lo <= j < banned_hi)
        folds.append(Fold(test=test, train=train))
    return folds


def leakage_fraction(n_obs: int, n_folds: int, horizon: int) -> float:
    """Fraction de l'apprentissage contaminée si l'on omet la purge.

    Chaque pli de test a deux bords, chacun contaminant `horizon`
    observations d'apprentissage :

        fuite ≈ 2·n_folds·horizon / n_obs.

    À cinq plis, un horizon de trente minutes et une observation par minute
    sur une séance, la fuite atteint 77 % : la validation croisée naïve ne
    valide plus rien du tout.
    """
    if n_obs < 1:
        raise ValueError("n_obs doit être >= 1")
    return min(1.0, 2.0 * n_folds * horizon / n_obs)


def walk_forward_windows(n_obs: int, n_splits: int, anchored: bool = True
                         ) -> list[Fold]:
    """Découpage en avant : apprentissage passé, test futur, jamais l'inverse.

    `anchored` conserve tout le passé disponible à chaque pas ; sinon la
    fenêtre d'apprentissage glisse à longueur constante. C'est le seul
    protocole qui reproduise la contrainte réelle d'exploitation — on ne
    dispose jamais du futur — et le seul dont le résultat soit directement
    interprétable comme une performance atteignable.
    """
    if n_splits < 1 or n_obs < n_splits + 1:
        raise ValueError("paramètres de découpage invalides")
    edges = [round(i * n_obs / (n_splits + 1)) for i in range(n_splits + 2)]
    out: list[Fold] = []
    for i in range(1, n_splits + 1):
        test = tuple(range(edges[i], edges[i + 1]))
        start = 0 if anchored else edges[i - 1]
        out.append(Fold(test=test, train=tuple(range(start, edges[i]))))
    return out


def effective_trials(n_trials: int, mean_correlation: float) -> float:
    """Nombre d'essais **indépendants** équivalent à `n_trials` essais corrélés.

        N_eff = N / (1 + (N − 1)·ρ̄)

    Essayer cent variantes d'un même signal ne coûte pas cent essais : les
    Sharpe obtenus sont corrélés, et le maximum se comporte comme celui d'un
    ensemble plus petit. Inversement, une corrélation moyenne de 0,5 ramène
    cent essais à moins de deux, ce qui est *aussi* une mauvaise nouvelle :
    l'espace de recherche réellement exploré est bien plus étroit qu'il n'y
    paraît.
    """
    if n_trials < 1:
        raise ValueError("n_trials doit être >= 1")
    if not 0.0 <= mean_correlation < 1.0:
        raise ValueError("la corrélation moyenne doit être dans [0, 1[")
    return n_trials / (1.0 + (n_trials - 1) * mean_correlation)
