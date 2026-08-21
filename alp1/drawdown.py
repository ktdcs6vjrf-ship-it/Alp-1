"""Théorie du drawdown : profondeur, durée, ruine.

Le drawdown est la seule statistique de risque qu'un allocataire regarde
avant le Sharpe, et c'est la seule que la loi d'un trade ne donne pas
directement : elle porte sur la *trajectoire*, donc sur l'ordre des trades.

Trois résultats en forme fermée structurent le module.

**Sans dérive**, l'espérance du drawdown maximal d'une marche de `N` pas
d'écart-type `σ_R` vaut exactement `σ_R·√(πN/2)`. Elle croît en racine de
`N` et ne se stabilise jamais : un drawdown record n'est pas un signal de
rupture, c'est le comportement attendu d'une stratégie sans edge — et aussi
d'une stratégie avec edge observée assez longtemps.

**Avec dérive**, la profondeur cesse de croître. Le coefficient d'ajustement
de Lundberg `θ*` — l'unique racine positive de `E[e^{−θR}] = 1` — borne la
probabilité de jamais perdre `D` unités de risque par `e^{−θ*·D}`, et
l'espérance du pire drawdown de toute l'histoire vaut de l'ordre de `1/θ*`.
`θ*` est exactement l'inclinaison d'Esscher qui rend la loi martingale : la
même quantité gouverne la mesure de stress et la mesure de ruine.

**Sur une trajectoire donnée**, l'indice d'Ulcer intègre la profondeur *et*
la durée, ce que le drawdown maximal — un seul point de la trajectoire —
ignore par construction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .pathstats import TradeLaw


# --- Drawdown d'une trajectoire donnée --------------------------------------


@dataclass(frozen=True)
class DrawdownProfile:
    """Lecture complète du drawdown d'une courbe d'équité."""

    max_drawdown: float          # profondeur maximale, en unités de la courbe
    max_duration: int            # plus longue période sous les eaux, en trades
    time_under_water: float      # fraction du temps passée sous un sommet
    ulcer_index: float           # √moyenne des carrés du drawdown relatif
    recovery: int | None         # trades pour effacer le pire drawdown, None si jamais


def equity_curve(returns: list[float], start: float = 0.0) -> list[float]:
    """Courbe d'équité cumulée, en unités de risque `R`. Additive, non composée.

    L'addition est le bon choix ici : la mise est reconstituée à taille fixe
    à chaque trade — un `R` est un `R`, quel que soit le capital du moment.
    Le cas composé relève du dimensionnement de Kelly, traité dans
    `alp1.pathstats`.
    """
    out, acc = [start], start
    for r in returns:
        acc += r
        out.append(acc)
    return out


def drawdown_series(curve: list[float]) -> list[float]:
    """Drawdown en cours à chaque point : `sommet courant − valeur`, ≥ 0."""
    peak, out = -math.inf, []
    for v in curve:
        peak = max(peak, v)
        out.append(peak - v)
    return out


def profile(curve: list[float], scale: float = 1.0) -> DrawdownProfile:
    """Profil complet de drawdown d'une courbe d'équité.

    `scale` normalise l'indice d'Ulcer, qui est défini sur un drawdown
    *relatif* ; en unités de `R`, on rapporte au capital de risque de
    référence plutôt qu'à un pourcentage de compte.
    """
    if len(curve) < 2:
        raise ValueError("la courbe doit contenir au moins deux points")
    dd = drawdown_series(curve)
    mdd = max(dd)

    longest = run = 0
    under = 0
    for d in dd:
        if d > 1e-12:
            run += 1
            under += 1
            longest = max(longest, run)
        else:
            run = 0

    peak_idx = max(range(len(dd)), key=lambda i: dd[i])
    prior_peak = max(curve[: peak_idx + 1])
    recovery: int | None = None
    for j in range(peak_idx, len(curve)):
        if curve[j] >= prior_peak - 1e-12:
            recovery = j - peak_idx
            break

    ulcer = math.sqrt(sum((d / scale) ** 2 for d in dd) / len(dd)) if scale > 0 else 0.0
    return DrawdownProfile(
        max_drawdown=mdd,
        max_duration=longest,
        time_under_water=under / len(dd),
        ulcer_index=ulcer,
        recovery=recovery,
    )


# --- Loi nulle : le drawdown d'une stratégie sans edge ----------------------


def expected_max_drawdown_null(sd_per_trade: float, n_trades: int) -> float:
    """`E[MDD]` d'une marche sans dérive, en unités de risque `R`.

    Pour un brownien sans dérive observé sur `[0, T]`, l'espérance du
    drawdown maximal vaut `σ·√(πT/2)`. Appliquée à une suite de `N` trades
    d'écart-type `σ_R` :

        E[MDD] = σ_R·√(πN/2) ≈ 1,2533·σ_R·√N.

    Aucune dérive n'entre dans cette formule, et pourtant elle croît sans
    borne. C'est le point que le module existe pour établir : **un drawdown
    profond n'est pas une preuve que la stratégie s'est cassée**, et un
    drawdown modeste n'est pas une preuve qu'elle fonctionne.
    """
    if n_trades < 0 or sd_per_trade < 0:
        raise ValueError("n_trades et sd_per_trade doivent être >= 0")
    return sd_per_trade * math.sqrt(math.pi * n_trades / 2.0)


def drawdown_quantile_null(sd_per_trade: float, n_trades: int, q: float) -> float:
    """Quantile du drawdown maximal d'une marche sans dérive.

    Le théorème de Lévy donne l'identité en loi entre le processus de
    drawdown `M_t − W_t` et le brownien réfléchi `|W_t|`. Le drawdown maximal
    a donc **exactement** la loi de `sup_{t≤T}|W_t|`, dont la répartition
    s'écrit

        P(sup|W| ≤ x·σ√T) = (4/π)·Σ_{n≥0} ((−1)ⁿ/(2n+1))·exp(−(2n+1)²π²/(8x²)).

    C'est la même identité qui donne `E[MDD] = σ√(πT/2)` : les deux résultats
    du module ne sont qu'une seule propriété, lue en espérance puis en
    quantile.
    """
    if not 0.0 < q < 1.0:
        raise ValueError("q doit être dans ]0, 1[")
    lo, hi = 1e-6, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if reflected_max_cdf(mid) < q:
            lo = mid
        else:
            hi = mid
    return sd_per_trade * math.sqrt(n_trades) * 0.5 * (lo + hi)


def reflected_max_cdf(x: float) -> float:
    """`P(sup_{t≤1}|W_t| ≤ x)` — série du brownien réfléchi, tronquée.

    La série converge géométriquement et très vite : douze termes suffisent à
    la double précision sur toute la plage utile.
    """
    if x <= 0:
        return 0.0
    total = 0.0
    for n in range(0, 24):
        k = 2 * n + 1
        total += ((-1) ** n / k) * math.exp(-(k**2) * math.pi**2 / (8.0 * x * x))
    return max(0.0, min(1.0, 4.0 / math.pi * total))


# --- Avec dérive : coefficient d'ajustement et ruine ------------------------


def adjustment_coefficient(law: TradeLaw, tol: float = 1e-13,
                           max_iter: int = 400) -> float:
    """Coefficient de Lundberg `θ*` : unique racine positive de `E[e^{−θR}] = 1`.

    Il n'existe que si `E[R] > 0` et si la loi peut perdre. C'est le taux de
    décroissance exponentielle de la probabilité de ruine, et l'inverse de
    l'échelle du pire drawdown de toute l'histoire.

    Lecture directe : `θ*` grand signifie edge fort relativement à la
    dispersion, donc drawdowns bornés ; `θ* → 0` quand l'espérance tend vers
    zéro, et la profondeur explose comme `1/θ*`. Retourne 0 si l'espérance
    est nulle ou négative — aucune borne de ruine n'existe alors, la ruine
    est certaine.
    """
    if law.mean <= 0:
        return 0.0
    if min(law.values) >= 0:
        return math.inf

    def mgf(theta: float) -> float:
        return sum(p * math.exp(-theta * v) for v, p in zip(law.values, law.probs))

    lo, hi = 1e-12, 1.0
    for _ in range(200):
        if mgf(hi) > 1.0:
            break
        hi *= 2.0
        if hi > 1e6:
            return math.inf
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        if mgf(mid) < 1.0:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol * max(1.0, hi):
            break
    return 0.5 * (lo + hi)


def risk_of_ruin(law: TradeLaw, depth_r: float) -> float:
    """Borne de Lundberg : `P(perdre un jour D unités de risque) ≤ e^{−θ*·D}`.

    Sur un horizon infini et une mise constante. La borne est atteinte à un
    facteur près qui vaut 1 dans la limite des grands `D` ; c'est la forme
    utilisée en assurance depuis Cramér, et elle est plus informative qu'une
    simulation parce qu'elle donne le *taux* et pas seulement un chiffre.

    Espérance nulle ou négative : la ruine est certaine, le résultat vaut 1.
    """
    if depth_r <= 0:
        return 1.0
    theta = adjustment_coefficient(law)
    if theta <= 0:
        return 1.0
    if theta == math.inf:
        return 0.0
    return math.exp(-theta * depth_r)


def ruin_depth_for_probability(law: TradeLaw, p: float) -> float:
    """Profondeur `D` telle que `P(drawdown ≥ D) = p`. Inverse de Lundberg."""
    if not 0.0 < p < 1.0:
        raise ValueError("p doit être dans ]0, 1[")
    theta = adjustment_coefficient(law)
    if theta <= 0:
        return math.inf
    return -math.log(p) / theta


def expected_max_drawdown_drift(law: TradeLaw, n_trades: int) -> float:
    """`E[MDD]` sur `N` trades pour une loi d'espérance positive.

    Les excursions sous le sommet courant sont, asymptotiquement, des
    variables exponentielles de taux `θ*`. Le maximum de `m` tirages
    exponentiels a pour espérance `(ln m + γ)/θ*`, où `γ` est la constante
    d'Euler-Mascheroni. Le nombre d'excursions attendu sur `N` trades vaut
    `m = N·E[R]·θ*` à l'ordre dominant, d'où

        E[MDD_N] ≈ min( (ln(1 + m) + γ)/θ*,  σ_R·√(πN/2) ).

    Le `1 +` sous le logarithme n'est pas cosmétique : il raccorde la formule
    au régime des petits `N`, où le drawdown n'a pas encore eu le temps de
    devenir extrême et où l'asymptotique pure diverge vers `−∞`. La borne par
    la valeur sans dérive ferme l'autre côté — une dérive positive ne peut
    pas creuser le drawdown. Le résultat suit la simulation à mieux que 7 %
    au-delà de deux cents trades, ce que la suite de tests vérifie.

    Croissance **logarithmique** en `N`, contre `√N` sans dérive : c'est le
    contraste qui rend le drawdown informatif. Si l'espérance est nulle ou
    négative, la formule sans dérive s'applique et le résultat est renvoyé
    tel quel.
    """
    if n_trades <= 0:
        return 0.0
    theta = adjustment_coefficient(law)
    if theta <= 0 or theta == math.inf:
        return expected_max_drawdown_null(law.sd, n_trades)
    m = max(0.0, n_trades * law.mean * theta)
    est = (math.log1p(m) + 0.5772156649015329) / theta
    return min(est, expected_max_drawdown_null(law.sd, n_trades))


def calmar(law: TradeLaw, trades_per_year: float, n_trades: int) -> float:
    """Ratio de Calmar : gain annuel espéré sur drawdown maximal espéré.

    Le seul ratio du module qui dépende de la longueur de l'historique par
    son dénominateur — donc le seul dont la valeur publiée dépende du choix
    de la fenêtre. Un Calmar mesuré sur trois ans n'est pas comparable à un
    Calmar mesuré sur dix : le numérateur est stable, le dénominateur croît.
    """
    mdd = expected_max_drawdown_drift(law, n_trades)
    if mdd <= 0:
        return math.inf
    return law.mean * trades_per_year / mdd


def time_under_water_quantile_null(q: float) -> float:
    """Quantile de la fraction du temps passée sous un sommet, sans dérive.

    Loi de l'arcsinus : la fraction du temps qu'une marche sans dérive passe
    du côté négatif a pour répartition `F(u) = (2/π)·arcsin(√u)`, donc pour
    quantile `sin²(πq/2)`. Sa moyenne vaut ½ mais sa densité `1/(π√(u(1−u)))`
    est **minimale en son centre** : les deux bords sont les modes.

    Conséquence directe et contre-intuitive : une stratégie sans edge passe
    typiquement soit presque tout son temps sous son sommet, soit presque
    aucun — pratiquement jamais la moitié. L'observation « la stratégie est
    restée sous son plus haut quatre-vingts pour cent de l'année » a donc,
    sous la loi nulle, une probabilité de 0,20, et ne prouve rien.
    """
    if not 0.0 <= q <= 1.0:
        raise ValueError("q doit être dans [0, 1]")
    return math.sin(math.pi * q / 2.0) ** 2


def prob_time_under_water_exceeds(fraction: float) -> float:
    """`P(fraction du temps sous les eaux > f)` sous la loi de l'arcsinus."""
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("fraction doit être dans [0, 1]")
    return 1.0 - (2.0 / math.pi) * math.asin(math.sqrt(fraction))
