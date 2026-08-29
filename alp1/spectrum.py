"""Combien de vos signaux sont réels : la loi de Marchenko-Pastur.

Un opérateur qui suit `k` couches d'analyse en regarde la matrice de
corrélation, y trouve une première valeur propre nettement plus grande que
les autres, et conclut qu'un facteur commun gouverne ses signaux. La
conclusion est presque toujours fausse, et pour une raison qui se calcule
sans rien mesurer.

Le résultat, en une ligne
------------------------
Sur `k` séries **indépendantes** observées `N` fois, les valeurs propres de
la matrice de corrélation empirique ne valent pas toutes un. Elles se
répartissent entre deux bornes, et pour `γ = k/N` :

    λ± = (1 ± √γ)²

C'est la loi de Marchenko-Pastur (1967). **Toute valeur propre inférieure à
`λ₊` est indiscernable du bruit**, quelle que soit la taille de
l'échantillon — c'est une borne, pas une approximation qui s'améliore.

La transition qui décide
-----------------------
La question intéressante est l'inverse : à partir de quelle force un facteur
réel devient-il visible ? Baik, Ben Arous et Péché (2005) donnent la réponse
et elle est brutale. Pour un facteur de force `s` — la population a une
valeur propre `1 + s` —, la valeur propre observée vaut

    λ = (1 + s)(1 + γ/s)   si s > √γ
    λ = λ₊                 sinon

**Sous `s = √γ`, le facteur ne sort pas du bruit. Pas faiblement : pas du
tout.** Il reste collé au bord, et aucune finesse d'estimation ne l'en
décolle. C'est une transition de phase, et c'est l'énoncé le plus net que ce
dépôt connaisse du problème qu'il mesure partout ailleurs.

Ce que cela donne à l'opérateur
-------------------------------
Sept couches sur deux cent cinquante séances donnent `γ = 0,028` et
`√γ = 0,167` : un facteur commun doit porter dix-sept pour cent de variance
en plus pour se voir. Sept couches sur soixante séances donnent `√γ = 0,34`.
Le seuil ne dépend d'aucune propriété du marché — seulement du nombre de
choses regardées rapporté au nombre de fois où on les a regardées.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from .mc import Rng


def mp_edges(gamma: float) -> tuple[float, float]:
    """Les deux bords du spectre de Marchenko-Pastur, `λ₋` et `λ₊`.

    `gamma` est le rapport du nombre de séries au nombre d'observations. À
    `γ → 0` les deux bords se referment sur un : avec assez d'observations,
    toute valeur propre différente de un est réelle. À `γ = 1` le bord bas
    touche zéro et le haut vaut quatre.
    """
    if gamma <= 0.0:
        return (1.0, 1.0)
    r = math.sqrt(gamma)
    return ((1.0 - r) ** 2, (1.0 + r) ** 2)


def mp_density(lam: float, gamma: float) -> float:
    """La densité de Marchenko-Pastur en `λ`, nulle hors des deux bords."""
    lo, hi = mp_edges(gamma)
    if not lo < lam < hi or gamma <= 0.0:
        return 0.0
    return math.sqrt((hi - lam) * (lam - lo)) / (2.0 * math.pi * gamma * lam)


def bbp_threshold(gamma: float) -> float:
    """`√γ` — la force minimale qu'un facteur doit avoir pour se voir.

    En dessous, la valeur propre observée reste **exactement** au bord du
    bruit. Ce n'est pas une perte de puissance : c'est une disparition.
    """
    return math.sqrt(max(gamma, 0.0))


def spiked_eigenvalue(s: float, gamma: float) -> float:
    """La valeur propre observée pour un facteur de force `s`.

    Formule de Baik-Ben Arous-Péché. Au-dessus du seuil elle croît avec `s` ;
    en dessous elle est plate, collée à `λ₊`.
    """
    _, hi = mp_edges(gamma)
    if s <= bbp_threshold(gamma):
        return hi
    return (1.0 + s) * (1.0 + gamma / s)


def observations_for_spike(s: float, k: int) -> float:
    """Observations requises pour qu'un facteur de force `s` sorte du bruit.

    La condition `s > √γ` avec `γ = k/N` donne `N > k/s²`. Elle est
    remarquable par ce qu'elle ne contient pas : ni la loi des rendements, ni
    la friction, ni la géométrie du trade. Regarder deux fois plus de choses
    demande deux fois plus d'observations, et diviser la force du facteur par
    deux en demande quatre fois plus.
    """
    if s <= 0.0:
        return math.inf
    return k / (s * s)


# ---------------------------------------------------------------------------
# La loi nulle, simulée pour valider la forme fermée à `k` fini
# ---------------------------------------------------------------------------


def _jacobi_eigenvalues(a: list[list[float]], sweeps: int = 60) -> list[float]:
    """Valeurs propres d'une matrice symétrique, par rotations de Jacobi.

    Stdlib uniquement, et c'est la raison de sa présence : le dépôt n'importe
    pas d'algèbre linéaire. La méthode est lente mais exacte à la précision
    machine, et les matrices en jeu font moins de trente lignes.
    """
    n = len(a)
    m = [row[:] for row in a]
    for _ in range(sweeps):
        hors = math.sqrt(sum(m[i][j] ** 2
                             for i in range(n) for j in range(i + 1, n)))
        if hors < 1e-12:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if abs(m[p][q]) < 1e-15:
                    continue
                theta = (m[q][q] - m[p][p]) / (2.0 * m[p][q])
                t = (math.copysign(1.0, theta)
                     / (abs(theta) + math.sqrt(theta * theta + 1.0)))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for i in range(n):
                    aip, aiq = m[i][p], m[i][q]
                    m[i][p] = c * aip - s * aiq
                    m[i][q] = s * aip + c * aiq
                for i in range(n):
                    api, aqi = m[p][i], m[q][i]
                    m[p][i] = c * api - s * aqi
                    m[q][i] = s * api + c * aqi
    return sorted(m[i][i] for i in range(n))


def correlation_eigenvalues(series: list[list[float]]) -> list[float]:
    """Valeurs propres de la matrice de corrélation de `k` séries.

    Les séries sont centrées et réduites, puis la matrice est formée à la
    main. Une série constante est traitée comme de corrélation nulle avec
    tout le reste, ce qui est le seul comportement défendable.
    """
    k = len(series)
    n = len(series[0])
    z = []
    for s in series:
        mu = sum(s) / n
        var = sum((v - mu) ** 2 for v in s) / max(n - 1, 1)
        sd = math.sqrt(var)
        z.append([(v - mu) / sd for v in s] if sd > 0 else [0.0] * n)
    corr = [[0.0] * k for _ in range(k)]
    for i in range(k):
        for j in range(i, k):
            c = sum(z[i][t] * z[j][t] for t in range(n)) / max(n - 1, 1)
            corr[i][j] = corr[j][i] = c
    return _jacobi_eigenvalues(corr)


@dataclass(frozen=True)
class NullSpectrum:
    """Le spectre d'une matrice de corrélation de séries indépendantes."""

    eigenvalues: tuple[float, ...]   # toutes les valeurs propres, triées
    lambda_max_mean: float
    lambda_max_q95: float
    edge: float                      # `λ₊` de la forme fermée
    k: int
    n: int
    draws: int


@lru_cache(maxsize=64)
def null_spectrum(k: int = 7, n: int = 250, draws: int = 300,
                  seed: int = 20260829) -> NullSpectrum:
    """Le spectre observé sur des séries **indépendantes**, par simulation.

    Elle ne remplace pas la forme fermée : elle la contrôle. À `k` fini le
    bord n'est pas net — la plus grande valeur propre fluctue autour de `λ₊`
    selon la loi de Tracy-Widom — et c'est cette fluctuation que la
    simulation chiffre, pour que le document ne présente pas `λ₊` comme une
    barrière plus dure qu'elle ne l'est.
    """
    rng = Rng(seed)
    toutes: list[float] = []
    maxima: list[float] = []
    for _ in range(draws):
        series = [[rng.gauss() for _ in range(n)] for _ in range(k)]
        vals = correlation_eigenvalues(series)
        toutes.extend(vals)
        maxima.append(vals[-1])
    maxima.sort()
    return NullSpectrum(
        eigenvalues=tuple(sorted(toutes)),
        lambda_max_mean=sum(maxima) / len(maxima),
        lambda_max_q95=maxima[min(len(maxima) - 1, int(0.95 * len(maxima)))],
        edge=mp_edges(k / n)[1],
        k=k, n=n, draws=draws,
    )


def main() -> None:
    for k, n in ((7, 250), (7, 60), (20, 250), (4, 500)):
        g = k / n
        lo, hi = mp_edges(g)
        print(f"k={k:3d} N={n:4d}  γ={g:.4f}  "
              f"λ₋={lo:.3f}  λ₊={hi:.3f}  "
              f"seuil BBP √γ={bbp_threshold(g):.3f}  "
              f"part de variance requise={hi / k:.1%}")
    print()
    for s in (0.05, 0.10, 0.167, 0.25, 0.40, 0.60):
        g = 7 / 250
        print(f"facteur s={s:.3f}  →  λ observée = "
              f"{spiked_eigenvalue(s, g):.4f}  "
              f"({'visible' if s > bbp_threshold(g) else 'collée au bord'})  "
              f"·  N requis à k=7 : {observations_for_spike(s, 7):.0f}")
    print()
    loi = null_spectrum(7, 250, draws=120)
    print(f"simulation k=7 N=250 : λ_max moyenne {loi.lambda_max_mean:.4f}, "
          f"quantile 95 % {loi.lambda_max_q95:.4f}, forme fermée λ₊ "
          f"{loi.edge:.4f}")
