"""Monte-Carlo du protocole entier : sa taille, sa puissance, sa durée.

Les simulations du module `alp1.mc` portent sur une *stratégie* : une loi de
trade, des trajectoires, des quantiles. Celle-ci porte sur la **procédure de
décision**. Elle ne demande pas « que produit cette stratégie ? » mais « à
quelle fréquence ce protocole se trompe, et combien de temps met-il à ne pas
se tromper ? ». C'est une différence de nature, et c'est ce qui met la
simulation à l'abri du surajustement : rien de ce qui est mesuré ici n'est un
résultat de stratégie qu'on pourrait vouloir flatteur. Une procédure qui
rejette trop souvent sous l'hypothèse nulle est disqualifiée, et c'est la
première chose que la simulation regarde.

**Trois étages, et l'ordre compte.**

*Premier étage — la séance, minute par minute.* On simule le modèle complet
du document : saisonnalité en U de la vitesse d'échange, volatilité de séance
lognormale, sauts de Merton, bande de bruit estimée sur les quatorze séances
précédentes et donc **entachée d'erreur**, stop posé sur la bande à l'entrée,
sortie à la clôture, ré-armement après un stop. Rien n'y est gaussien ni
indépendant : la loi du résultat d'un trade est asymétrique, à queue épaisse,
et corrélée à sa propre durée. C'est cette loi-là, et non une approximation
normale, qui alimente la suite.

*Deuxième étage — la date.* Les cinq contrats du panel sont noués par une
copule gaussienne à structure de blocs : forte à l'intérieur d'un fuseau,
faible entre fuseaux. Seul le couple (numérateur, dénominateur) agrégé par
date survit à cet étage, parce que c'est tout ce dont l'estimateur à variance
groupée a besoin. La corrélation n'est donc pas une hypothèse de l'inférence :
c'est une propriété du monde simulé, que l'estimateur doit retrouver seul.

*Troisième étage — la procédure.* On rejoue le protocole scellé : pondération
GLS, variance groupée par date, jalonnement en information, frontières
d'O'Brien-Fleming, séquence fixée sur les trois configurations, plafond de
cinq années. Ce qui est compté, ce sont des verdicts.

**Ce qui rend la mesure non surajustée**, et il faut l'énoncer précisément :

  - Aucun réglage de la procédure n'est choisi au vu de sa sortie. Les
    frontières viennent d'une fonction de dépense publiée, le seuil et la
    puissance sont ceux du document, le panel et la cadence sont scellés.
  - La **taille empirique** est mesurée en même temps que la puissance. Un
    levier ajusté en cachette pour gagner de la puissance se paierait en
    taille, et la taille est publiée à côté de son erreur-type de simulation.
  - Le contraste de sélection est mesuré sur les **mêmes tirages** : la même
    famille de trois configurations, lue dans l'ordre scellé puis lue par son
    meilleur élément. L'écart entre les deux taux est le coût de la sélection,
    et il ne dépend d'aucune hypothèse.
  - La dérive n'est jamais estimée ici : elle est **imposée**, et la
    simulation ne mesure que la capacité du protocole à la retrouver.
  - Les graines sont explicites et l'erreur-type de Monte-Carlo accompagne
    chaque taux. Une simulation dont la graine n'est pas publiée n'est pas un
    résultat.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from .costs import norm_cdf
from .mc import Rng, quantile
from .microstructure import JUMPS, Seasonality, VolMixture
from .momentum import mean_abs_move, time_exit_outcome
from .power import (
    ALPHA,
    HORIZON_SESSIONS,
    MIN_SESSIONS_BEFORE_LOOK,
    PANEL,
    RHO_CROSS_REGION,
    RHO_SAME_REGION,
    SESSIONS_PER_YEAR,
    VOL_LOG_SD,
    boundaries,
)

# --- Calibration de la simulation ------------------------------------------
#
# Tous ces nombres viennent du chiffrage scellé. Aucun n'est réglé ici.

INDEX_LEVEL = 6000.0
SESSION_DISPERSION = 60.0
SESSION_MIN = 390.0
ENTRY_MIN = 120.0                 # géométrie au pire cas sur la boîte d'exposant
CLOSE_BUFFER = 2.0                # sortie au marché deux minutes avant la clôture
MAX_ENTRIES = 3                   # cadence pré-enregistrée, par séance et marché
EDGE_BPS = 6.0                    # dérive empruntée, en points de base

#: Corrélation entre la volatilité estimée sur les quatorze séances
#: précédentes et celle de la séance à venir. Une estimation parfaite
#: donnerait 1 et surestimerait le gain de la pondération ; 0,70 est l'ordre
#: de grandeur de la persistance d'une volatilité réalisée à cet horizon.
VOL_FORECAST_CORR = 0.70

POOL_SESSIONS = 4000
DATE_POOL = 12000
REPLICATES = 1500

#: Multiples de la dérive dimensionnante auxquels la courbe de puissance est
#: tracée. Le dernier est l'hypothèse empruntée du document, arrondie.
CURVE: tuple[float, ...] = (0.0, 0.5, 0.75, 1.0, 1.4)
SEED = 20260821


@lru_cache(maxsize=None)
def sigma_per_min() -> float:
    return SESSION_DISPERSION / math.sqrt(SESSION_MIN)


@lru_cache(maxsize=None)
def geometry():
    """Géométrie de référence : stop sur la bande, sortie à la clôture."""
    sigma = sigma_per_min()
    stop = mean_abs_move(sigma, ENTRY_MIN)
    return stop, time_exit_outcome(stop, SESSION_MIN - ENTRY_MIN, sigma)


@lru_cache(maxsize=None)
def friction() -> float:
    """Friction déduite du carnet, en points — celle du document, pas une pose."""
    from .friction import RETAIL_ES, friction_law

    _, out = geometry()
    return friction_law(sigma_per_min(), out.p_stop, 1.0, RETAIL_ES).mean


@lru_cache(maxsize=None)
def design_drift() -> float:
    """Dérive nette par minute pour laquelle le protocole est dimensionné.

    Elle n'est pas choisie : elle est **déduite du budget de temps**. Le
    budget d'information scellé détecte à la puissance visée une dérive nette
    et une seule, et c'est celle-là. Toute dérive supérieure est tranchée plus
    tôt, par la séquentialité ; toute dérive inférieure sort de la portée du
    protocole, et le protocole le dit au lieu de conclure.
    """
    from .power import design_drift as _dd

    return _dd()


@lru_cache(maxsize=None)
def forecast_max_information() -> float:
    """Re-dérivation du budget scellé, pour le contrôle qui l'accompagne."""
    from .power import DESIGN, max_information as _mi

    st = pool_statistics(0.0)
    return _mi(DESIGN, st["exposure"], st["sd"])


def gross_drift_of_bps(bps: float, exposure: float) -> float:
    """Dérive brute par minute d'une dérive captée de `bps` sur le trade.

    La littérature chiffre un déplacement **par trade**, non par minute ; le
    convertir demande l'exposition, et l'exposition à retenir est celle que la
    règle produit réellement — saisonnalité, bande estimée et ré-entrées
    comprises — non celle de la forme fermée, qui la surestime.
    """
    return bps * 1e-4 * INDEX_LEVEL / exposure


@lru_cache(maxsize=None)
def weighted_exposure() -> float:
    """Exposition moyenne pondérée ``Σwτ/Σw``, celle que voit l'estimateur."""
    base = date_pool(0.0)
    return sum(base.b) / sum(base.w)


def net_drift_of_bps(bps: float) -> float:
    """Dérive **nette** par minute — la quantité que le test principal borne."""
    st = pool_statistics(0.0)
    return (gross_drift_of_bps(bps, st["exposure"])
            - friction() / weighted_exposure())


def bps_of_net_drift(theta: float) -> float:
    """Réciproque : la dérive captée, en points de base, d'une dérive nette."""
    st = pool_statistics(0.0)
    gross = theta + friction() / weighted_exposure()
    return 1e4 * gross * st["exposure"] / INDEX_LEVEL


@lru_cache(maxsize=None)
def reference_multiple() -> float:
    """L'hypothèse empruntée, en multiples de la dérive dimensionnante."""
    return net_drift_of_bps(EDGE_BPS) / design_drift()


# --- Premier étage : la séance simulée --------------------------------------


@dataclass(frozen=True)
class Trade:
    """Un trade simulé, tel que le journal d'exécution le rapporterait."""

    net: float          # résultat net en points, friction déduite
    tau: float          # exposition en minutes
    sigma_hat: float    # volatilité estimée avant l'entrée, en points/√min
    rank: int           # rang de l'entrée dans la séance
    stopped: bool       # sortie au stop plutôt qu'à la clôture


def _session_trades(steps: list[tuple[float, float, float]], bridge: list[float],
                    sigma_hat: float, drift: float, c: float) -> list[Trade]:
    """Déroule une séance et rend ses trades, sous la dérive imposée.

    Le chemin de prix est celui des chocs fournis : deux hypothèses de dérive
    partagent donc exactement le même marché, et l'écart entre elles ne peut
    pas venir du tirage. La dérive est ajoutée au résultat **de la position**,
    ce qui est l'énoncé de l'hypothèse : le signal annonce un déplacement, il
    ne modifie pas la dynamique non conditionnelle du prix.

    Le stop est surveillé **en continu** sur la part diffusive, par pont
    brownien entre deux minutes observées : sans cette correction, une
    surveillance à la minute ferait sortir systématiquement au-delà du stop et
    la martingale afficherait une espérance inférieure à moins la friction —
    un dépassement qui serait un artefact de pas de temps, non un coût de
    marché. La part de saut, elle, franchit réellement le stop, et le
    dépassement qu'elle produit est conservé : c'est un coût réel, et
    l'identité de Wald l'absorbe.
    """
    band_k = math.sqrt(2.0 / math.pi) * sigma_hat
    price = 0.0
    out: list[Trade] = []
    entry_t = 0.0
    side = 0.0
    stop = 0.0
    pnl = 0.0
    live = False
    armed = True
    last = len(steps)
    for i in range(last):
        t = i + 1.0
        dif, jmp, var = steps[i]
        price += dif + jmp
        band = band_k * math.sqrt(t)
        if not live:
            if not armed:
                # Ré-armement : le prix doit revenir dans la bande avant qu'une
                # nouvelle cassure compte. Sans cette condition, un stop serait
                # immédiatement suivi d'une entrée au même endroit.
                if abs(price) < band:
                    armed = True
                continue
            if t >= ENTRY_MIN and abs(price) > band and len(out) < MAX_ENTRIES:
                entry_t, side, stop, pnl, live = (
                    t, 1.0 if price > 0 else -1.0, band, 0.0, True)
            continue
        # Le résultat de la position se cumule à partir des chocs postérieurs à
        # l'entrée : le prix d'entrée n'a pas à être conservé.
        before = pnl
        pnl += side * dif + drift
        if pnl <= -stop:
            out.append(Trade(-stop - c, t - 0.5 - entry_t, sigma_hat,
                             len(out) + 1, True))
            live, armed, pnl = False, False, 0.0
            continue
        if var > 0.0:
            crossing = math.exp(-2.0 * (before + stop) * (pnl + stop) / var)
            if bridge[i] < crossing:
                out.append(Trade(-stop - c, t - 0.5 - entry_t, sigma_hat,
                                 len(out) + 1, True))
                live, armed, pnl = False, False, 0.0
                continue
        pnl += side * jmp
        if pnl <= -stop:
            out.append(Trade(pnl - c, t - entry_t, sigma_hat, len(out) + 1, True))
            live, armed, pnl = False, False, 0.0
    if live:
        out.append(Trade(pnl - c, last - entry_t, sigma_hat, len(out) + 1, False))
    return out


@lru_cache(maxsize=None)
def _minute_profile() -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Variance et écart-type d'une minute, à volatilité de séance unitaire.

    La saisonnalité en U ne dépend pas de la séance tirée : la calculer une
    fois pour toutes retire un appel de fonction par minute simulée, soit
    l'essentiel du coût du vivier.
    """
    seas = Seasonality()
    var = tuple(seas.elapsed(float(i), i + 1.0)
                for i in range(int(SESSION_MIN - CLOSE_BUFFER)))
    return var, tuple(math.sqrt(v) for v in var)


def _jump_minutes(rng: Rng, lam: float, n_minutes: int) -> list[int]:
    """Minutes où un saut survient, par sauts géométriques.

    Tirer une Bernoulli par minute coûte `n` uniformes pour deux sauts par
    séance en moyenne. La loi du nombre de minutes jusqu'au prochain succès
    est géométrique, et l'échantillonner directement donne exactement le même
    processus pour quelques tirages par séance.
    """
    if lam <= 0.0:
        return []
    log1m = math.log1p(-lam)
    out: list[int] = []
    i = -1
    while True:
        u = max(rng.uniform(), 1e-300)
        i += 1 + int(math.log(u) / log1m)
        if i >= n_minutes:
            return out
        out.append(i)


@lru_cache(maxsize=None)
def session_pool(drift_multiple: float = 0.0) -> tuple[tuple[Trade, ...], ...]:
    """Un vivier de séances simulées, sous `drift_multiple × θ₁`.

    Les chocs sont régénérés à graine fixe pour chaque appel, et produits
    **avant** que la règle ne les lise : deux multiples de dérive voient donc
    rigoureusement le même marché, minute par minute et saut par saut. La
    comparaison entre hypothèses est ainsi à variables aléatoires communes, et
    l'écart qu'elle montre ne peut pas venir du tirage.
    """
    mix = VolMixture(sigma_per_min(), nu=VOL_LOG_SD)
    c = friction()
    # `design_drift` se calcule sur le vivier sans dérive : ne pas l'appeler
    # quand il n'y a rien à ajouter, sous peine de récursion.
    drift = drift_multiple * design_drift() if drift_multiple else 0.0
    rho = VOL_FORECAST_CORR
    rates = [(m.intensity_per_min(SESSION_MIN), m.mean_jump, m.sd_jump)
             for m in JUMPS]
    unit_var, unit_sd = _minute_profile()
    last = len(unit_var)

    rng = Rng(SEED + 101)
    pool: list[tuple[Trade, ...]] = []
    for _ in range(POOL_SESSIONS):
        z = rng.gauss()
        sigma = mix.sigma(z)
        z_hat = rho * z + math.sqrt(1.0 - rho * rho) * rng.gauss()
        sigma_hat = mix.sigma(z_hat)
        var2 = sigma * sigma
        jumps = [0.0] * last
        for lam, m_j, s_j in rates:
            # Saut d'espérance nulle : aucun compensateur à retrancher.
            for i in _jump_minutes(rng, lam, last):
                jumps[i] += m_j + s_j * rng.gauss()
        steps = [(sigma * unit_sd[i] * rng.gauss(), jumps[i], var2 * unit_var[i])
                 for i in range(last)]
        bridge = [rng.uniform() for _ in range(last)]
        pool.append(tuple(_session_trades(steps, bridge, sigma_hat, drift, c)))
    return tuple(pool)


@lru_cache(maxsize=None)
def pool_statistics(drift_multiple: float = 0.0) -> dict[str, float]:
    """Ce que le vivier apprend sur la loi d'un trade, avant toute inférence."""
    pool = session_pool(drift_multiple)
    trades = [t for s in pool for t in s]
    n = len(trades)
    mean = sum(t.net for t in trades) / n
    var = sum((t.net - mean) ** 2 for t in trades) / (n - 1)
    sd = math.sqrt(var)
    m3 = sum((t.net - mean) ** 3 for t in trades) / n
    m4 = sum((t.net - mean) ** 4 for t in trades) / n
    tau = sum(t.tau for t in trades) / n
    stops = sum(1 for t in trades if t.stopped)
    return {
        "trades": float(n),
        "entries_per_session": n / len(pool),
        "sessions_with_trade": sum(1 for s in pool if s) / len(pool),
        "mean": mean,
        "sd": sd,
        "skew": m3 / sd**3,
        "excess_kurtosis": m4 / sd**4 - 3.0,
        "exposure": tau,
        "sharpe_trade": mean / sd,
        "p_stop": stops / n,
    }


# --- Deuxième étage : la date, et la corrélation du panel -------------------


def _block_loadings(rho_within: float, rho_cross: float) -> tuple[float, float, float]:
    """Décomposition à trois facteurs d'une corrélation en blocs.

    ``u = √ρ_c·G + √(ρ_w − ρ_c)·R + √(1 − ρ_w)·ε`` : deux contrats du même
    fuseau corrèlent à `ρ_w`, deux fuseaux différents à `ρ_c`, et la variance
    totale vaut un. La décomposition n'existe que si `ρ_w ≥ ρ_c ≥ 0`, ce que
    la structure du panel garantit.
    """
    if not 0.0 <= rho_cross <= rho_within < 1.0:
        raise ValueError("il faut 0 ≤ ρ_cross ≤ ρ_within < 1")
    return (math.sqrt(rho_cross), math.sqrt(rho_within - rho_cross),
            math.sqrt(1.0 - rho_within))


@lru_cache(maxsize=None)
def _mean_cross_region() -> float:
    return sum(RHO_CROSS_REGION.values()) / len(RHO_CROSS_REGION)


@dataclass(frozen=True)
class DatePool:
    """Le seul résumé d'une date dont l'estimateur ait besoin.

    `a` est le numérateur pondéré ``Σ w·X`` de la date — sur le résultat
    **brut**, friction non déduite —, `b` son dénominateur ``Σ w·τ``, `w` la
    somme des poids et `n` le nombre de trades. Tout le reste — quel marché,
    quel rang, quelle heure — a déjà joué son rôle et n'entre plus dans la
    décision.
    """

    a: tuple[float, ...]
    b: tuple[float, ...]
    w: tuple[float, ...]
    n: tuple[int, ...]
    design_effect: float
    effective_trades: float
    realised_correlation: float
    trades_per_date: float


@lru_cache(maxsize=None)
def date_pool(drift_multiple: float = 0.0, n_markets: int = len(PANEL),
              rho_within: float = RHO_SAME_REGION,
              rho_cross: float | None = None,
              seed_offset: int = 0) -> DatePool:
    """Assemble des dates du panel par copule gaussienne sur le vivier.

    Chaque marché tire une séance du vivier, et le tirage est noué aux autres
    par la copule. L'ordonnancement du vivier se fait sur la **somme de
    séance**, qui est la quantité que la variance groupée par date voit
    réellement ; la corrélation demandée porte donc là où elle compte.
    """
    rho_cross = _mean_cross_region() if rho_cross is None else rho_cross
    pool = session_pool(drift_multiple)
    c = friction()
    order = sorted(range(len(pool)),
                   key=lambda i: sum(t.net for t in pool[i]))
    markets = PANEL[:n_markets]
    regions = sorted({m.region for m in markets})
    lg, lr, le = _block_loadings(rho_within, rho_cross)

    rng = Rng(SEED + 211 + seed_offset)
    a_list, b_list, w_list, n_list = [], [], [], []
    contributions = 0.0
    contributions_sq = 0.0
    trades_total = 0
    for _ in range(DATE_POOL):
        g = rng.gauss()
        rfac = {r: rng.gauss() for r in regions}
        a = b = w_sum = 0.0
        n = 0
        for m in markets:
            u = lg * g + lr * rfac[m.region] + le * rng.gauss()
            idx = order[min(len(order) - 1, max(0, int(norm_cdf(u) * len(order))))]
            for t in pool[idx]:
                w = 1.0 / (t.sigma_hat * t.sigma_hat)
                gross = w * (t.net + c)
                a += gross
                b += w * t.tau
                w_sum += w
                contributions += gross
                contributions_sq += gross * gross
                n += 1
        a_list.append(a)
        b_list.append(b)
        w_list.append(w_sum)
        n_list.append(n)
        trades_total += n

    n_dates = len(a_list)
    per_date = trades_total / n_dates
    mean_trade = contributions / trades_total
    var_trade = contributions_sq / trades_total - mean_trade * mean_trade
    mean_a = sum(a_list) / n_dates
    var_cluster = sum(x * x for x in a_list) / n_dates - mean_a * mean_a
    # Effet de grappe : ce que la corrélation de date coûte en information.
    # Sans corrélation il vaut 1, et la date compte pour ses trades entiers.
    deff = var_cluster / (per_date * var_trade) if var_trade > 0 else 1.0
    rho_hat = (deff - 1.0) / max(per_date - 1.0, 1e-9)
    return DatePool(tuple(a_list), tuple(b_list), tuple(w_list), tuple(n_list),
                    design_effect=deff, effective_trades=per_date / deff,
                    realised_correlation=rho_hat, trades_per_date=per_date)


def shifted_pool(base: DatePool, drift: float) -> DatePool:
    """Ajoute une dérive au vivier de dates, sans re-simuler les séances.

    ``A_d → A_d + µ·B_d`` : c'est exactement l'effet d'une dérive de `µ` points
    par minute sur le numérateur pondéré, à temps d'arrêt inchangé. La seule
    chose que la transformation néglige est l'effet de la dérive sur la date
    du stop, qui est du second ordre — une dérive de référence déplace le P&L
    de trois points contre un stop de vingt-trois. `check_shift_accuracy`
    confronte la transformation à une simulation complète sous la même dérive,
    et c'est ce contrôle, non l'argument, qui autorise l'usage.
    """
    return DatePool(
        a=tuple(a + drift * b for a, b in zip(base.a, base.b)),
        b=base.b, w=base.w, n=base.n,
        design_effect=base.design_effect,
        effective_trades=base.effective_trades,
        realised_correlation=base.realised_correlation,
        trades_per_date=base.trades_per_date,
    )


def pool_drift(pool: DatePool) -> float:
    """Dérive par minute que le vivier porte réellement, ``ΣA/ΣB``."""
    b = sum(pool.b)
    return sum(pool.a) / b if b else 0.0


def net_pool(base: DatePool) -> DatePool:
    """Passe du résultat brut au résultat net : ``A → A − c·Σw``."""
    c = friction()
    return DatePool(
        a=tuple(a - c * w for a, w in zip(base.a, base.w)),
        b=base.b, w=base.w, n=base.n,
        design_effect=base.design_effect,
        effective_trades=base.effective_trades,
        realised_correlation=base.realised_correlation,
        trades_per_date=base.trades_per_date,
    )


@lru_cache(maxsize=None)
def martingale_check() -> dict[str, float]:
    """L'identité d'arrêt optionnel, confrontée au marché simulé.

    Sous martingale, la dérive **brute** par minute est nulle exactement,
    quelle que soit la géométrie et quel que soit le nombre d'entrées par
    séance. Le vivier ne la réalise qu'à son erreur d'échantillonnage près,
    et c'est cet écart-là — non un défaut du modèle — que le recentrage de la
    nulle retire. Un écart de plus de trois erreurs-types serait au contraire
    la marque d'une faute de simulation, et le test le vérifie.

    L'erreur-type est calculée sur les **séances**, qui sont les unités
    indépendantes du vivier : les trades d'une même séance partagent sa
    volatilité et sa suite de chocs, et les compter comme indépendants
    diviserait l'erreur-type par un facteur qui n'existe pas.
    """
    pool = session_pool(0.0)
    c = friction()
    num = den = 0.0
    per_session: list[tuple[float, float]] = []
    for sess in pool:
        a = b = 0.0
        for t in sess:
            w = 1.0 / (t.sigma_hat * t.sigma_hat)
            a += w * (t.net + c)
            b += w * t.tau
        per_session.append((a, b))
        num += a
        den += b
    n = len(per_session)
    residual = num / den if den else 0.0
    mean_b = den / n
    var = sum((a - residual * b) ** 2 for a, b in per_session) / (n - 1)
    se = math.sqrt(var / n) / mean_b if mean_b else 0.0
    return {
        "sessions": float(n),
        "residual_per_min": residual,
        "standard_error": se,
        "z": residual / se if se > 0 else 0.0,
        "share_of_reference": residual / design_drift(),
    }


@lru_cache(maxsize=None)
def null_pool(n_markets: int = len(PANEL),
              rho_within: float = RHO_SAME_REGION,
              rho_cross: float | None = None,
              seed_offset: int = 0) -> tuple[DatePool, float]:
    """Le vivier à la frontière de l'hypothèse nulle, recentré exactement.

    La nulle du test principal est ``µ_net = 0`` : la dérive captée couvre la
    friction, sans plus. Le vivier y est amené en deux gestes, et les deux
    sont définitionnels plutôt que discrétionnaires. On retranche d'abord la
    friction, qui est une constante observée au journal d'exécution. On
    retranche ensuite la dérive résiduelle du vivier, dont le théorème d'arrêt
    optionnel garantit qu'elle vaut zéro en espérance — la laisser
    reviendrait à mesurer le taux d'erreur du protocole sous une hypothèse
    nulle *fausse*, décalée de l'erreur d'échantillonnage d'un vivier fini.

    Le montant retranché est publié. Il ne touche ni à la forme de la loi, ni
    à sa variance, ni à la structure de corrélation entre marchés : le
    recentrage déplace une moyenne, et rien d'autre.
    """
    base = net_pool(date_pool(0.0, n_markets, rho_within, rho_cross, seed_offset))
    delta = pool_drift(base)
    return shifted_pool(base, -delta), delta


@lru_cache(maxsize=None)
def drifted_pool(multiple: float) -> DatePool:
    """Le vivier nul recentré, auquel on **ajoute** ``multiple × θ₁``.

    Transformation linéaire : elle laisse les temps d'arrêt inchangés. Elle
    sert de contrôle, pas de base aux chiffres publiés — `exact_pool` re-simule
    le marché sous dérive et c'est lui qui alimente la courbe de puissance.
    """
    base, _ = null_pool()
    return shifted_pool(base, multiple * design_drift())


@lru_cache(maxsize=None)
def exact_pool(multiple: float) -> DatePool:
    """Le vivier re-simulé **sous** ``multiple × θ₁``, recentré comme la nulle.

    Le recentrage appliqué est celui mesuré sur le vivier sans dérive, et non
    celui du vivier considéré : retrancher sa propre moyenne à un vivier sous
    dérive retirerait précisément la dérive qu'on cherche à détecter. C'est
    aussi ce qui rend les points de la courbe comparables entre eux — tous ont
    subi la même correction, d'un montant fixé une fois.
    """
    if multiple == 0.0:
        return null_pool()[0]
    _, delta = null_pool()
    return shifted_pool(net_pool(date_pool(multiple)), -delta)


# --- Troisième étage : la procédure ----------------------------------------


@dataclass(frozen=True)
class Verdict:
    """Issue d'une exécution du protocole."""

    rejected: bool
    futile: bool
    exhausted: bool
    look: int
    sessions: int

    @property
    def years(self) -> float:
        return self.sessions / SESSIONS_PER_YEAR


def max_information(plan=None) -> float:
    """Information maximale scellée, en unités de ``(point par minute)⁻²``.

    ``I_max = ((z_{1−α} + z_puissance)/θ₁)² × inflation`` — c'est la même
    identité que celle qui définit `design_drift`, lue dans l'autre sens. Le
    nombre est figé dans `alp1.power` plutôt que recalculé : le protocole
    s'arrête quand l'information mesurée l'atteint, et une borne d'arrêt qui
    se recalculerait à chaque exécution ne serait pas une borne. C'est aussi
    ce qui rend la corrélation du panel indifférente à la validité du test.
    """
    from .power import SEALED_MAX_INFORMATION

    return SEALED_MAX_INFORMATION


def run_protocol(pool: DatePool, rng: Rng, plan=None,
                 i_max: float | None = None,
                 horizon: int = HORIZON_SESSIONS) -> Verdict:
    """Rejoue le protocole sur une histoire tirée du vivier de dates.

    Les sommes courantes suffisent : le numérateur `A`, le dénominateur `B`,
    et les trois moments qui composent la variance groupée
    ``V = ΣA² − 2µ̂·ΣAB + µ̂²·ΣB²``. L'estimateur, sa variance et l'information
    se recalculent donc en temps constant à chaque date, ce qui est ce qui rend
    la simulation de la procédure possible à cette échelle.
    """
    plan = plan or boundaries()
    i_max = max_information(plan) if i_max is None else i_max
    a = b = saa = sab = sbb = 0.0
    n_pool = len(pool.a)
    look = 0
    for d in range(1, horizon + 1):
        j = rng.randint(n_pool)
        ad, bd = pool.a[j], pool.b[j]
        a += ad
        b += bd
        saa += ad * ad
        sab += ad * bd
        sbb += bd * bd
        if d < MIN_SESSIONS_BEFORE_LOOK or b <= 0.0:
            continue
        mu = a / b
        v = saa - 2.0 * mu * sab + mu * mu * sbb
        if v <= 0.0:
            continue
        info = (b * b) / v
        while look < len(plan.fractions) and info >= plan.fractions[look] * i_max:
            z = mu * math.sqrt(info)
            if z >= plan.efficacy[look]:
                return Verdict(True, False, False, look + 1, d)
            if z <= plan.futility[look]:
                return Verdict(False, True, False, look + 1, d)
            look += 1
    return Verdict(False, False, True, look, horizon)


@dataclass(frozen=True)
class Operating:
    """Point de fonctionnement du protocole sous une dérive donnée."""

    drift_multiple: float
    reject: float
    futile: float
    exhausted: float
    standard_error: float
    median_years: float
    mean_years: float
    q90_years: float
    look_counts: tuple[float, ...]


def operating_point(pool: DatePool, drift_multiple: float,
                    replicates: int = REPLICATES, plan=None,
                    seed_offset: int = 0,
                    horizon: int = HORIZON_SESSIONS) -> Operating:
    """Taille, puissance et durée du protocole, sur `replicates` histoires."""
    plan = plan or boundaries()
    i_max = max_information(plan)
    rng = Rng(SEED + 401 + seed_offset)
    rejects = futile = exhausted = 0
    years: list[float] = []
    looks = [0] * (len(plan.fractions) + 1)
    for _ in range(replicates):
        v = run_protocol(pool, rng, plan, i_max, horizon)
        rejects += v.rejected
        futile += v.futile
        exhausted += v.exhausted
        years.append(v.years)
        looks[v.look] += 1
    n = float(replicates)
    p = rejects / n
    years.sort()
    return Operating(
        drift_multiple=drift_multiple,
        reject=p,
        futile=futile / n,
        exhausted=exhausted / n,
        standard_error=math.sqrt(max(p * (1.0 - p), 1e-12) / n),
        median_years=quantile(years, 0.50),
        mean_years=sum(years) / n,
        q90_years=quantile(years, 0.90),
        look_counts=tuple(x / n for x in looks),
    )


@lru_cache(maxsize=None)
def trace_paths(multiple: float, n_paths: int = 14,
                step: int = 21) -> tuple[tuple[tuple[float, float], ...], ...]:
    """Trajectoires du `Z` de décision, relevées un mois de bourse sur l'autre.

    C'est la figure que la statistique séquentielle mérite et qu'on ne montre
    presque jamais : non pas la frontière seule, mais les chemins qui la
    rencontrent. Chaque trajectoire s'arrête où le protocole s'arrête — au
    rejet, à l'abandon, ou au plafond d'horizon.
    """
    plan = boundaries()
    i_max = max_information(plan)
    pool = exact_pool(multiple)
    rng = Rng(SEED + 857 + int(round(1000 * multiple)))
    n_pool = len(pool.a)
    out = []
    for _ in range(n_paths):
        a = b = saa = sab = sbb = 0.0
        look = 0
        path: list[tuple[float, float]] = []
        for d in range(1, HORIZON_SESSIONS + 1):
            j = rng.randint(n_pool)
            ad, bd = pool.a[j], pool.b[j]
            a += ad
            b += bd
            saa += ad * ad
            sab += ad * bd
            sbb += bd * bd
            if d < MIN_SESSIONS_BEFORE_LOOK or b <= 0.0:
                continue
            mu = a / b
            v = saa - 2.0 * mu * sab + mu * mu * sbb
            if v <= 0.0:
                continue
            info = (b * b) / v
            t = info / i_max
            if d % step == 0 or t >= 1.0:
                path.append((min(t, 1.0), mu * math.sqrt(info)))
            stop = False
            while look < len(plan.fractions) and info >= plan.fractions[look] * i_max:
                z = mu * math.sqrt(info)
                if z >= plan.efficacy[look] or z <= plan.futility[look]:
                    stop = True
                    break
                look += 1
            if stop:
                break
        out.append(tuple(path))
    return tuple(out)


@lru_cache(maxsize=None)
def realised_information_per_date(replicates: int = 120,
                                  sessions: int = HORIZON_SESSIONS) -> float:
    """Information réellement accumulée par date, mesurée sur l'estimateur.

    C'est le pendant simulé de `power.information_per_date`, et le seul
    contrôle qui autorise à jalonner le protocole sur une prévision en forme
    fermée : si les deux divergeaient, les fractions d'information ne
    tomberaient pas où le plan les attend, et les frontières ne tiendraient
    plus le niveau annoncé.
    """
    pool, _ = null_pool()
    rng = Rng(SEED + 613)
    total = 0.0
    n_pool = len(pool.a)
    for _ in range(replicates):
        a = b = saa = sab = sbb = 0.0
        for _ in range(sessions):
            j = rng.randint(n_pool)
            ad, bd = pool.a[j], pool.b[j]
            a += ad
            b += bd
            saa += ad * ad
            sab += ad * bd
            sbb += bd * bd
        mu = a / b
        total += (b * b) / (saa - 2.0 * mu * sab + mu * mu * sbb)
    return total / replicates / sessions


@lru_cache(maxsize=None)
def rho_sensitivity(replicates: int = 1000) -> tuple[dict[str, float], ...]:
    """Ce que la corrélation du panel change, et ce qu'elle ne change pas.

    C'est le contrôle décisif du dispositif. La corrélation entre marchés est
    la seule hypothèse de calibration dont on pourrait craindre qu'elle porte
    la validité du protocole ; le jalonnement en information est précisément ce
    qui l'en dispense. On la fait donc varier du simple au presque parfait :
    la taille doit rester au niveau nominal, et seule la **durée** doit bouger.
    Si la taille dérivait avec `ρ`, le protocole serait faux et le tableau le
    montrerait.
    """
    out = []
    for rho_w in (0.50, 0.65, 0.80, 0.95):
        rho_c = rho_w * _mean_cross_region() / RHO_SAME_REGION
        null, delta = null_pool(rho_within=rho_w, rho_cross=rho_c)
        alt = shifted_pool(net_pool(date_pool(1.0, rho_within=rho_w,
                                             rho_cross=rho_c)), -delta)
        a = operating_point(null, 0.0, replicates, seed_offset=31)
        b = operating_point(alt, 1.0, replicates, seed_offset=31)
        out.append({
            "rho_within": rho_w, "rho_cross": rho_c,
            "design_effect": null.design_effect,
            "effective_trades": null.effective_trades,
            "size": a.reject, "power": b.reject,
            "standard_error": a.standard_error,
            "median_years": b.median_years, "exhausted": b.exhausted,
        })
    return tuple(out)


@lru_cache(maxsize=None)
def panel_width(replicates: int = 1000) -> tuple[dict[str, float], ...]:
    """Le protocole selon le nombre de contrats, d'un seul au panel entier.

    Le repli à un marché n'est pas une dégradation du protocole : c'est le
    protocole qu'un opérateur qui ne dispose que d'un historique ES peut
    exécuter. Ce qu'il perd est de la durée, et le tableau chiffre combien.
    """
    out = []
    ref = round(reference_multiple(), 3)
    for k in (1, 3, 5):
        null, delta = null_pool(n_markets=k)
        alt = shifted_pool(net_pool(date_pool(1.0, n_markets=k)), -delta)
        borrowed = shifted_pool(net_pool(date_pool(ref, n_markets=k)), -delta)
        a = operating_point(null, 0.0, replicates, seed_offset=47)
        b = operating_point(alt, 1.0, replicates, seed_offset=47)
        c = operating_point(borrowed, ref, replicates, seed_offset=47)
        out.append({
            "markets": float(k),
            "trades_per_date": null.trades_per_date,
            "effective_trades": null.effective_trades,
            "size": a.reject, "power": b.reject,
            "median_years": b.median_years, "exhausted": b.exhausted,
            "power_borrowed": c.reject, "median_years_borrowed": c.median_years,
            "exhausted_borrowed": c.exhausted,
        })
    return tuple(out)


# --- Contrôles --------------------------------------------------------------


@lru_cache(maxsize=None)
def check_shift_accuracy() -> dict[str, float]:
    """Confronte la dérive ajoutée à une re-simulation complète sous dérive.

    Deux viviers de dates : l'un obtenu en simulant les séances **sous** la
    dérive de référence, l'autre en ajoutant la dérive au vivier sans dérive.
    Si les deux donnent la même puissance à l'erreur de simulation près, la
    transformation linéaire est légitime pour tracer une courbe de puissance ;
    sinon elle ne l'est pas, et le contrôle est là pour le dire.
    """
    _, delta = null_pool()
    exact = shifted_pool(net_pool(date_pool(1.0)), -delta)
    approx = drifted_pool(1.0)
    a = operating_point(exact, 1.0, replicates=800, seed_offset=17)
    b = operating_point(approx, 1.0, replicates=800, seed_offset=17)
    se = math.sqrt(a.standard_error**2 + b.standard_error**2)
    return {
        "exact": a.reject, "approx": b.reject,
        "gap": b.reject - a.reject, "standard_error": se,
        "z": (b.reject - a.reject) / se if se > 0 else 0.0,
        "exact_years": a.mean_years, "approx_years": b.mean_years,
    }


@lru_cache(maxsize=None)
def selection_contrast(replicates: int = 1200) -> dict[str, float]:
    """Le coût de la sélection, sur les mêmes tirages.

    Trois configurations, toutes sans edge. Lue dans l'ordre scellé, la
    famille rejette à `α` : la séquence fixée s'arrête à la première
    configuration qui ne rejette pas. Lue par son meilleur élément — la
    pratique ordinaire — elle rejette bien plus souvent, et l'écart ne tient
    à rien d'autre qu'à l'ordre de lecture.
    """
    plan = boundaries()
    i_max = max_information(plan)
    pools = tuple(null_pool(seed_offset=k)[0] for k in (0, 5, 9))
    rng = Rng(SEED + 733)
    sealed = best = 0
    for _ in range(replicates):
        verdicts = [run_protocol(p, rng, plan, i_max) for p in pools]
        if verdicts[0].rejected:
            sealed += 1
        if any(v.rejected for v in verdicts):
            best += 1
    n = float(replicates)
    return {
        "sealed": sealed / n,
        "best_of_three": best / n,
        "inflation": (best / max(sealed, 1)),
        "standard_error": math.sqrt(ALPHA * (1 - ALPHA) / n),
        "replicates": n,
    }


# --- Sortie texte -----------------------------------------------------------


def main() -> None:
    plan = boundaries()
    print("Plan séquentiel — fractions d'information", plan.fractions)
    print("  efficacité :", [f"{z:.3f}" for z in plan.efficacy])
    print("  futilité   :", [f"{z:.3f}" for z in plan.futility])
    print(f"  inflation {plan.inflation:.3f} — durée espérée sous H1 "
          f"{plan.expected_fraction_h1:.3f}, sous H0 {plan.expected_fraction_h0:.3f}")

    st = pool_statistics(0.0)
    print(f"\nVivier : {st['trades']:.0f} trades, {st['entries_per_session']:.2f} "
          f"par séance, exposition {st['exposure']:.1f} min, "
          f"asymétrie {st['skew']:+.2f}, kurtosis {st['excess_kurtosis']:+.2f}")

    base, delta = null_pool()
    print(f"Recentrage de la nulle : {delta:+.5f} pt/min, soit "
          f"{100 * delta / design_drift():+.1f} % de θ₁")
    print(f"Dérive dimensionnante θ₁ = {design_drift():.5f} pt/min, soit "
          f"{bps_of_net_drift(design_drift()):.2f} pdb captés ; "
          f"hypothèse empruntée = {reference_multiple():.2f}·θ₁")
    print(f"Dates  : {base.trades_per_date:.2f} trades, corrélation réalisée "
          f"{base.realised_correlation:.3f}, "
          f"{base.effective_trades:.2f} trades effectifs par date")

    print("\nPoints de fonctionnement :")
    for mult in CURVE + (round(reference_multiple(), 3),):
        op = operating_point(exact_pool(mult), mult)
        print(f"  θ = {mult:4.2f}·θ₁ : rejet {op.reject:.3f} "
              f"(± {op.standard_error:.3f}) · futilité {op.futile:.3f} · "
              f"horizon épuisé {op.exhausted:.3f} · durée médiane "
              f"{op.median_years:.2f} ans")

    print("\nSensibilité à la corrélation du panel :")
    for r in rho_sensitivity():
        print(f"  ρ = {r['rho_within']:.2f} : effet de grappe {r['design_effect']:.2f}, "
              f"taille {r['size']:.3f}, puissance {r['power']:.3f}, "
              f"durée médiane {r['median_years']:.2f} ans, "
              f"horizon épuisé {r['exhausted']:.3f}")

    print("\nLargeur du panel :")
    for r in panel_width():
        print(f"  {r['markets']:.0f} marché(s) : {r['effective_trades']:.2f} trades "
              f"effectifs par date, taille {r['size']:.3f}, puissance "
              f"{r['power']:.3f}, durée médiane {r['median_years']:.2f} ans, "
              f"horizon épuisé {r['exhausted']:.3f} — sous l'hypothèse "
              f"empruntée : puissance {r['power_borrowed']:.3f}, "
              f"{r['median_years_borrowed']:.2f} ans, épuisé "
              f"{r['exhausted_borrowed']:.3f}")

    sc = selection_contrast()
    print(f"\nSélection : ordre scellé {sc['sealed']:.3f}, "
          f"meilleur de trois {sc['best_of_three']:.3f}")
    ck = check_shift_accuracy()
    print(f"Contrôle de la dérive ajoutée : exacte {ck['exact']:.3f}, "
          f"ajoutée {ck['approx']:.3f}, z = {ck['z']:+.2f}")


if __name__ == "__main__":
    main()
