"""Calibration de référence des instruments de validation, et leurs tables.

Un seul point d'entrée pour toute la troisième partie du papier : la loi du
trade sous la loi nulle, la même loi inclinée vers l'edge de référence, et
toutes les simulations, mises en cache pour que le texte, les tables et les
figures lisent rigoureusement les mêmes tirages.

L'edge de référence n'est pas un paramètre libre. Il est fixé par le critère
maître du papier : à la dérive `µ = 2µ*`, l'espérance nette d'un trade vaut
exactement la friction, donc `E[R] = c/L`. Choisir « le double du seuil de
rentabilité » est la seule hypothèse d'edge du document, elle est explicite,
et tous les chiffres de la partie s'y rapportent.

Usage :
    python -m alp1.quant
"""

from __future__ import annotations

import math
from functools import lru_cache

from .costs import COST_REALISTIC, ES
from .drawdown import (
    adjustment_coefficient,
    calmar,
    drawdown_quantile_null,
    expected_max_drawdown_drift,
    expected_max_drawdown_null,
    prob_time_under_water_exceeds,
    ruin_depth_for_probability,
    time_under_water_quantile_null,
)
from .horizon import outcome_scaled
from .hmm import (
    GaussianHMM,
    aic,
    baum_welch,
    bayes_error,
    bic,
    effective_separability,
    log_likelihood,
    observations_to_separate,
    separability,
    two_state_from_persistence,
    viterbi,
)
from .mc import (
    Rng,
    block_length_for_autocorrelation,
    iid_bootstrap,
    quantile,
    sample,
    sign_permutation_pvalue,
    simulate,
    stationary_bootstrap,
)
from .overfit import (
    bhy_threshold,
    bonferroni_threshold,
    cscv,
    deflated_sharpe,
    effective_trials,
    expected_max_sharpe,
    haircut_sharpe,
    holm_thresholds,
    leakage_fraction,
    minimum_backtest_length,
    purged_folds,
    walk_forward_windows,
)
from .pathstats import (
    TradeLaw,
    annualise,
    law_from_outcome,
    lo_adjustment,
    min_track_record_length,
    probabilistic_sharpe,
)
from .report import (
    FRICTION,
    HURST,
    INDEX_LEVEL,
    SESSION_MIN,
    SIGMA_1MIN,
    STOP_PTS,
    TRADES_PER_DAY,
    Table,
    num,
)
from .stress import (
    JumpModel,
    SCENARIOS,
    cornish_fisher_is_valid,
    es_from_law,
    es_gaussian,
    expected_slippage_beyond_stop,
    fit_gpd,
    hill_estimator,
    jump_adjusted_expectancy,
    prob_jump_during_trade,
    reverse_stress_move_pct,
    scenario_loss_r,
    var_cornish_fisher,
    var_evt,
    var_from_law,
    var_gaussian,
)

# --- Calibration de référence ----------------------------------------------

RR_REF = 20.0
RR_GRID = (3.0, 5.0, 10.0, 20.0, 30.0, 50.0)
SESSIONS_PER_YEAR = 252.0
TRADES_PER_YEAR = TRADES_PER_DAY * SESSIONS_PER_YEAR      # 504
DRIFT_MULTIPLE = 2.0                                       # µ = 2µ*, seule hypothèse d'edge
TRIALS_GRID = (1, 10, 100, 1000)
N_TRIALS_REF = 100
SEED = 20260821

# Sauts : ordre de grandeur d'un contrat indiciel liquide — un saut de queue
# par vingt séances, d'amplitude type douze points. Ce sont des paramètres
# d'échelle explicites, pas une mesure.
JUMP = JumpModel(intensity_per_day=0.05, mean_jump=0.0, sd_jump=12.0)

MC_PATHS = 4000
MC_TRADES = int(TRADES_PER_YEAR)


@lru_cache(maxsize=None)
def geometry(rr: float):
    """Distribution d'issues de la géométrie `1:rr`, sous la loi d'échelle."""
    return outcome_scaled(STOP_PTS, rr * STOP_PTS, SESSION_MIN, SIGMA_1MIN, HURST)


@lru_cache(maxsize=None)
def null_law(rr: float = RR_REF) -> TradeLaw:
    """Loi du trade sans dérive : moyenne `−c/L`, exactement."""
    return law_from_outcome(geometry(rr), STOP_PTS, rr * STOP_PTS, FRICTION)


@lru_cache(maxsize=None)
def reference_drift() -> float:
    """`µ = 2µ*` en points par minute, où `µ* = c/E[τ]` à la géométrie 1:20."""
    return DRIFT_MULTIPLE * FRICTION / geometry(RR_REF).expected_time


@lru_cache(maxsize=None)
def edge_law(rr: float = RR_REF) -> TradeLaw:
    """Loi du trade sous la dérive de référence, par inclinaison d'Esscher.

    La dérive est une propriété du **signal**, pas de la géométrie : elle est
    donc tenue fixe à travers la grille de ratios, et c'est l'exposition
    `E[τ]` qui varie. C'est la lecture imposée par l'équation (6).
    """
    o = geometry(rr)
    target = (reference_drift() * o.expected_time - FRICTION) / STOP_PTS
    return null_law(rr).tilted_to_mean(target)


@lru_cache(maxsize=None)
def _paths(kind: str):
    rng = Rng(SEED if kind == "null" else SEED + 1)
    law = null_law() if kind == "null" else edge_law()
    return tuple(simulate(law, MC_TRADES, MC_PATHS, rng))


def mc_paths(kind: str = "null"):
    """Trajectoires simulées, mises en cache : mêmes tirages partout."""
    return _paths(kind)


@lru_cache(maxsize=None)
def _cscv_matrices():
    """Deux matrices de performance : sans edge, puis avec un edge unique.

    Chaque configuration reçoit une série de performances par sous-période.
    Sous H0 aucune ne possède d'edge ; dans la seconde, une seule en possède
    un, d'une amplitude délibérément modeste — la moitié d'un écart-type de
    sous-période. C'est le contraste qui montre ce que la PBO mesure.
    """
    rng = Rng(SEED + 7)
    n_cfg, n_per = 24, 96
    flat = [[rng.gauss() for _ in range(n_per)] for _ in range(n_cfg)]
    rng2 = Rng(SEED + 8)
    real = [[rng2.gauss() + (0.5 if s == 0 else 0.0) for _ in range(n_per)]
            for s in range(n_cfg)]
    return flat, real


@lru_cache(maxsize=None)
def cscv_null():
    return cscv(_cscv_matrices()[0], n_blocks=8)


@lru_cache(maxsize=None)
def cscv_edge():
    return cscv(_cscv_matrices()[1], n_blocks=8)


CSCV_REPS = 120
CSCV_CONFIGS = 24
CSCV_PERIODS = 96


@lru_cache(maxsize=None)
def cscv_distribution():
    """Loi d'échantillonnage de la PBO, sur des backtests synthétiques répétés.

    Une PBO se lit sur *un* backtest, et sa dispersion d'échantillonnage est
    rarement rapportée. On la mesure ici en répétant l'expérience sur des
    familles indépendantes : sans edge d'un côté, avec un edge unique de
    l'autre. Le résultat décide de ce qu'une lecture isolée autorise à
    conclure.
    """
    rng = Rng(SEED + 21)
    flat, real = [], []
    for _ in range(CSCV_REPS):
        m0 = [[rng.gauss() for _ in range(CSCV_PERIODS)] for _ in range(CSCV_CONFIGS)]
        flat.append(cscv(m0, n_blocks=8).pbo)
        m1 = [[rng.gauss() + (0.5 if s == 0 else 0.0) for _ in range(CSCV_PERIODS)]
              for s in range(CSCV_CONFIGS)]
        real.append(cscv(m1, n_blocks=8).pbo)
    return tuple(flat), tuple(real)


# --- HMM de référence ------------------------------------------------------

HMM_TRUE = two_state_from_persistence(0.94, 0.88, 0.30, -0.30, 1.0, 1.55)
HMM_OBS = 750
HMM_SHORT = 120


@lru_cache(maxsize=None)
def hmm_series(kind: str = "regime"):
    """Série d'observations et états vrais — deux régimes, ou aucun.

    `regime` tire du HMM de référence. `flat` tire d'une gaussienne unique de
    même variance globale : **aucun régime n'existe**, et c'est sur cette
    série que l'on mesure ce que Baum-Welch invente.
    """
    rng = Rng(SEED + {"regime": 11, "flat": 12, "short": 13}[kind])

    def pick(row: tuple[float, ...], u: float) -> int:
        acc = 0.0
        for j, p in enumerate(row):
            acc += p
            if u <= acc:
                return j
        return len(row) - 1

    if kind == "regime":
        state = pick(HMM_TRUE.start, rng.uniform())
        obs, truth = [], []
        for _ in range(HMM_OBS):
            obs.append(HMM_TRUE.means[state] + HMM_TRUE.sds[state] * rng.gauss())
            truth.append(state)
            state = pick(HMM_TRUE.trans[state], rng.uniform())
        return tuple(obs), tuple(truth)

    var = sum(p * (m**2 + s**2) for p, m, s
              in zip(HMM_TRUE.stationary(), HMM_TRUE.means, HMM_TRUE.sds))
    sd = math.sqrt(var)
    n = HMM_SHORT if kind == "short" else HMM_OBS
    return tuple(sd * rng.gauss() for _ in range(n)), tuple([0] * n)


HMM_INIT = GaussianHMM((0.5, 0.5), ((0.80, 0.20), (0.20, 0.80)),
                       (0.5, -0.5), (1.2, 1.2))
HMM_ONE_STATE_INIT = GaussianHMM((1.0,), ((1.0,),), (0.0,), (1.0,))


@lru_cache(maxsize=None)
def hmm_fit(kind: str = "regime"):
    obs, _ = hmm_series(kind)
    fitted, loglik, iters = baum_welch(list(obs), HMM_INIT)
    one, ll1, _ = baum_welch(list(obs), HMM_ONE_STATE_INIT)
    return fitted, loglik, iters, one, ll1


# --- Tables ----------------------------------------------------------------


def table_instruments() -> Table:
    rows = [
        ["Sharpe", "E[R]/σ[R]", "dispersion totale",
         "aveugle à l'asymétrie ; gonflé par l'autocorrélation"],
        ["Sortino", "E[R]/√E[min(R,0)²]", "dispersion à la baisse",
         "flatté d'un facteur σ/DD par un ratio gain/risque élevé"],
        ["Omega", "E[(R−θ)⁺]/E[(θ−R)⁻]", "loi entière",
         "sans hypothèse de moment ; Ω > 1 ⟺ E[R] > θ"],
        ["Calmar", "gain annuel / E[MDD]", "pire perte cumulée",
         "dénominateur croissant avec la fenêtre : non comparable"],
        ["Ulcer", "√moyenne(DD²)", "profondeur et durée",
         "seule mesure qui pénalise la durée sous les eaux"],
        ["Kelly", "argmax E[ln(1+fR)]", "croissance logarithmique",
         "suppose la loi connue ; ruineux si l'edge est surestimé"],
        ["VaR / ES", "quantile et sa moyenne", "queue de perte",
         "la VaR n'est pas sous-additive ; l'ES l'est"],
        ["EVT (GPD)", "loi des dépassements", "au-delà de l'échantillon",
         "seule extrapolation légitime hors des données"],
        ["Monte-Carlo", "loi empirique par tirage", "toute la trajectoire",
         "ne crée aucune information : il propage les hypothèses"],
        ["Bootstrap", "ré-échantillonnage", "incertitude d'estimation",
         "le bootstrap i.i.d. détruit la dépendance ; blocs obligatoires"],
        ["Permutation", "randomisation du signe", "hypothèse de non-prédiction",
         "sans hypothèse de loi ; ne teste que la direction"],
        ["HMM", "Baum-Welch, Viterbi", "régimes latents",
         "converge toujours, y compris sur du bruit"],
        ["DSR / MinTRL", "PSR déflaté du maximum", "sélection",
         "corrige ce que le nombre d'essais explique à lui seul"],
        ["PBO (CSCV)", "rang hors échantillon du meilleur", "procédure entière",
         "mesure la sélection, non la rentabilité"],
        ["CV purgée", "purge et embargo", "fuite temporelle",
         "indispensable dès que les étiquettes se chevauchent"],
        ["Stress inversé", "choc qui efface l'année", "scénario critique",
         "ne dépend d'aucun choix de scénario"],
    ]
    return Table(
        "instruments",
        "Les seize instruments, ce qu'ils mesurent et ce qu'ils ne voient pas",
        ["Instrument", "Définition", "Porte sur", "Angle mort"],
        rows,
        note=("Aucun instrument de cette liste ne crée d'information. Chacun "
              "transforme une hypothèse en conséquence chiffrée ; la colonne "
              "de droite indique laquelle des hypothèses il laisse intacte."),
        wrap_cols=[1, 2, 3],
        wide=True,
    )


def table_ratios() -> Table:
    n0, e0 = null_law(), edge_law()
    ny = TRADES_PER_YEAR

    def col(law: TradeLaw) -> list[str]:
        return [
            num(law.mean, 4), num(law.sd, 2), num(law.skewness, 2),
            num(law.excess_kurtosis, 1), num(100 * law.prob_win, 2),
            num(law.sharpe_per_trade, 4), num(annualise(law.sharpe_per_trade, ny), 3),
            num(law.downside_deviation(), 3), num(law.sortino(), 4),
            num(law.sd / law.downside_deviation(), 2), num(law.omega(), 3),
            num(law.kelly_fraction(), 4),
        ]

    labels = [
        "Espérance E[R] (R)", "Écart-type σ[R] (R)", "Asymétrie γ₃",
        "Excès de kurtosis γ₄ − 3", "Taux de gain (%)",
        "Sharpe par trade", f"Sharpe annualisé ({num(ny, 0)} trades)",
        "Déviation à la baisse (R)", "Sortino par trade",
        "Facteur σ/DD", "Omega (seuil 0)", "Fraction de Kelly",
    ]
    a, b = col(n0), col(e0)
    rows = [[lab, x, y] for lab, x, y in zip(labels, a, b)]
    return Table(
        "ratios",
        "Tableau de bord des ratios, sans dérive puis sous la dérive de référence",
        ["Grandeur", "µ = 0", f"µ = {num(DRIFT_MULTIPLE, 0)} µ*"],
        rows,
        note=("Le facteur σ/DD est le rapport exact entre Sortino et Sharpe : à "
              "1:20 il vaut " + num(e0.sd / e0.downside_deviation(), 2) + ". Publier "
              "un Sortino pour une géométrie à ratio élevé, c'est publier un Sharpe "
              "multiplié par une constante que la géométrie fixe et que l'edge "
              "ignore. Le Sharpe annualisé d'un edge égal au double du seuil de "
              "rentabilité vaut " + num(annualise(e0.sharpe_per_trade, ny), 2) + "."),
        rules_after=[4],
    )


def table_detectability() -> Table:
    rows = []
    for rr in RR_GRID:
        o = geometry(rr)
        law = edge_law(rr)
        sr = law.sharpe_per_trade
        mtrl = min_track_record_length(sr, 0.0, law.skewness, law.excess_kurtosis)
        mbtl = minimum_backtest_length(sr, N_TRIALS_REF)
        rows.append([
            f"1:{num(rr, 0)}", num(o.expected_time, 1), num(law.mean, 4),
            num(sr, 4), num(annualise(sr, TRADES_PER_YEAR), 3),
            num(law.sortino() / sr, 2) if sr > 0 else "—",
            num(mtrl, 0) if mtrl < math.inf else "∞",
            num(mtrl / TRADES_PER_YEAR, 1) if mtrl < math.inf else "∞",
            num(mbtl / TRADES_PER_YEAR, 1) if mbtl < math.inf else "∞",
        ])
    return Table(
        "detectability",
        "Détectabilité de l'edge selon la géométrie, à dérive de signal constante",
        ["R:R", "E[τ] (min)", "E[R] (R)", "Sharpe/trade", "Sharpe an.",
         "Sortino/Sharpe", "MinTRL (trades)", "MinTRL (ans)", "après 100 essais (ans)"],
        rows,
        note=("La dérive est tenue fixe : elle appartient au signal, pas à la "
              "géométrie. Élargir le target allonge l'exposition, donc l'espérance, "
              "donc la détectabilité — mais aucune colonne ne descend sous une "
              "décennie une fois la sélection prise en compte. C'est le résultat "
              "central de cette partie."),
        rules_after=[1],
        wide=True,
    )


def table_drawdown() -> Table:
    n0, e0 = null_law(), edge_law()
    n = int(TRADES_PER_YEAR)
    theta = adjustment_coefficient(e0)
    rows = [
        ["E[MDD] sans dérive, 1 an", "σ_R·√(πN/2)",
         num(expected_max_drawdown_null(n0.sd, n), 1) + " R"],
        ["E[MDD] sans dérive, 4 ans", "croissance en √N",
         num(expected_max_drawdown_null(n0.sd, 4 * n), 1) + " R"],
        ["Quantile 95 % du MDD, 1 an", "loi de sup|W| (Lévy)",
         num(drawdown_quantile_null(n0.sd, n, 0.95), 1) + " R"],
        ["E[MDD] sous dérive, 1 an", "(ln m + γ)/θ*",
         num(expected_max_drawdown_drift(e0, n), 1) + " R"],
        ["Gain annuel espéré", "N·E[R]",
         num(n * e0.mean, 1) + " R"],
        ["Coefficient de Lundberg θ*", "E[e^{−θR}] = 1", num(theta, 5)],
        ["Échelle du pire drawdown", "1/θ*", num(1.0 / theta, 0) + " R"],
        ["Profondeur atteinte 1 fois sur 20", "−ln(0,05)/θ*",
         num(ruin_depth_for_probability(e0, 0.05), 0) + " R"],
        ["Ratio de Calmar, 1 an", "N·E[R] / E[MDD]",
         num(calmar(e0, TRADES_PER_YEAR, n), 2)],
        ["P(80 % du temps sous les eaux)", "loi de l'arcsinus",
         num(100 * prob_time_under_water_exceeds(0.80), 0) + " %"],
        ["Médiane du temps sous les eaux", "sin²(π/4)",
         num(100 * time_under_water_quantile_null(0.5), 0) + " %"],
    ]
    return Table(
        "drawdown",
        "Drawdown : loi nulle en √N, loi sous dérive en ln N, et ruine",
        ["Grandeur", "Forme", "Valeur"],
        rows,
        note=("Le drawdown maximal espéré sur un an sous la dérive de référence — "
              + num(expected_max_drawdown_drift(e0, n), 0) + " R — dépasse le gain "
              "annuel espéré, " + num(n * e0.mean, 0) + " R. C'est la traduction en "
              "trajectoire de ce que le Sharpe annualisé disait déjà en niveau : "
              "l'edge existe peut-être, il ne se voit pas."),
        rules_after=[2, 4, 7],
    )


def table_montecarlo() -> Table:
    n0, e0 = null_law(), edge_law()
    n = MC_TRADES
    pn, pe = mc_paths("null"), mc_paths("edge")

    def q(paths, attr, lv):
        return quantile([getattr(p, attr) for p in paths], lv)

    rows = [
        ["P(P&L annuel > 0)",
         num(100 * sum(1 for p in pn if p.terminal > 0) / len(pn), 1) + " %",
         num(100 * sum(1 for p in pe if p.terminal > 0) / len(pe), 1) + " %"],
        ["P&L annuel, quantile 5 %", num(q(pn, "terminal", 0.05), 0) + " R",
         num(q(pe, "terminal", 0.05), 0) + " R"],
        ["P&L annuel, médiane", num(q(pn, "terminal", 0.50), 0) + " R",
         num(q(pe, "terminal", 0.50), 0) + " R"],
        ["P&L annuel, quantile 95 %", num(q(pn, "terminal", 0.95), 0) + " R",
         num(q(pe, "terminal", 0.95), 0) + " R"],
        ["MDD moyen simulé", num(sum(p.max_drawdown for p in pn) / len(pn), 1) + " R",
         num(sum(p.max_drawdown for p in pe) / len(pe), 1) + " R"],
        ["MDD, forme fermée",
         num(expected_max_drawdown_null(n0.sd, n), 1) + " R",
         num(expected_max_drawdown_drift(e0, n), 1) + " R"],
        ["MDD, quantile 95 %", num(q(pn, "max_drawdown", 0.95), 0) + " R",
         num(q(pe, "max_drawdown", 0.95), 0) + " R"],
        ["Sharpe mesuré, quantile 95 %", num(q(pn, "sharpe", 0.95), 4),
         num(q(pe, "sharpe", 0.95), 4)],
        ["Sharpe vrai", num(n0.sharpe_per_trade, 4), num(e0.sharpe_per_trade, 4)],
        ["Temps sous les eaux, médiane",
         num(100 * q(pn, "time_under_water", 0.5), 0) + " %",
         num(100 * q(pe, "time_under_water", 0.5), 0) + " %"],
    ]
    return Table(
        "montecarlo",
        f"Monte-Carlo : {num(MC_PATHS, 0)} années simulées de {num(n, 0)} trades",
        ["Statistique", "µ = 0", f"µ = {num(DRIFT_MULTIPLE, 0)} µ*"],
        rows,
        note=("La ligne décisive est l'avant-dernière paire. Une stratégie <strong>sans "
              "aucun edge</strong> produit, une année sur vingt, un Sharpe par trade de "
              + num(q(pn, "sharpe", 0.95), 3) + " — supérieur au Sharpe <strong>vrai</strong> de "
              "la stratégie avec edge, " + num(e0.sharpe_per_trade, 3) + ". Un an de "
              "résultats ne sépare donc pas les deux hypothèses, quel que soit "
              "l'instrument qu'on lui applique."),
        rules_after=[3, 6],
    )


HORIZON_YEARS = (1.0, 5.0, 10.0, 25.0)


def table_selection() -> Table:
    e0 = edge_law()
    n = int(TRADES_PER_YEAR)
    sr = e0.sharpe_per_trade
    sd_trials = 1.0 / math.sqrt(n)
    rows = []
    for k in TRIALS_GRID:
        sr0 = expected_max_sharpe(k, sd_trials)
        dsr = deflated_sharpe(sr, n, k, e0.skewness, e0.excess_kurtosis)
        mbtl = minimum_backtest_length(sr, k)
        rows.append([
            num(k, 0), num(sr0, 4), num(annualise(sr0, TRADES_PER_YEAR), 3),
            num(100 * dsr, 1) + " %",
            num(mbtl, 0) if mbtl < math.inf else "∞",
            num(mbtl / TRADES_PER_YEAR, 1) if mbtl < math.inf else "∞",
            num(effective_trials(k, 0.50), 1),
        ])
    return Table(
        "selection",
        "Ce que le nombre de configurations essayées coûte au résultat",
        ["Essais", "Sharpe/trade attendu du meilleur", "en annualisé",
         "DSR de l'edge de référence", "MinBTL (trades)", "MinBTL (ans)",
         "Essais indépendants équivalents (ρ̄ = 0,5)"],
        rows,
        note=("Toutes les colonnes se lisent à stratégie <strong>inchangée</strong> : seule "
              "varie la taille de l'espace de recherche. À cent essais — chiffre "
              "modeste pour une pile à sept couches réglables — le Sharpe attendu "
              "du meilleur essai <strong>sans aucun edge</strong>, "
              + num(annualise(expected_max_sharpe(100, sd_trials), TRADES_PER_YEAR), 2)
              + " annualisé, dépasse de cinq fois celui de l'edge de référence, "
              + num(annualise(sr, TRADES_PER_YEAR), 2) + ". La dernière colonne "
              "atténue le constat sans le renverser : des variantes corrélées "
              "comptent pour moins d'essais, mais elles explorent aussi un espace "
              "d'autant plus étroit."),
        wrap_cols=[1, 6],
        wide=True,
    )


def table_haircut() -> Table:
    e0 = edge_law()
    sr = e0.sharpe_per_trade
    rows = []
    for years in HORIZON_YEARS:
        n = int(round(years * TRADES_PER_YEAR))
        t_stat = sr * math.sqrt(n)
        cells = [num(years, 0), num(n, 0), num(t_stat, 2)]
        for k in (1, 10, 100):
            cells.append(num(100 * haircut_sharpe(sr, n, k, method="bhy"), 0) + " %")
        rows.append(cells)
    return Table(
        "haircut",
        "Décote de Harvey-Liu-Zhu : ce qui reste du Sharpe après correction",
        ["Historique (ans)", "Trades", "t-statistique",
         "1 essai", "10 essais", "100 essais"],
        rows,
        note=("Décote appliquée au Sharpe de l'edge de référence, "
              + num(sr, 4) + " par trade. Les trois colonnes de droite donnent la "
              "<strong>part du Sharpe effacée</strong> par la correction de tests multiples au "
              "sens de Benjamini-Hochberg-Yekutieli. La colonne « 1 essai » vaut "
              "zéro par construction — sans essais multiples il n'y a rien à "
              "corriger, ce qui ne rend pas pour autant le résultat significatif : "
              "la t-statistique reste sous 2 en deçà de vingt-cinq ans. Dès dix "
              "essais, la décote est totale jusqu'à ce même horizon, et à cent "
              "essais elle l'est partout."),
    )


def table_pbo() -> Table:
    flat, real = cscv_distribution()

    def stat(xs, f):
        return f(list(xs))

    rows = [
        ["Réplications indépendantes", num(CSCV_REPS, 0), num(CSCV_REPS, 0)],
        ["PBO moyenne", num(100 * sum(flat) / len(flat), 1) + " %",
         num(100 * sum(real) / len(real), 1) + " %"],
        ["PBO médiane", num(100 * quantile(list(flat), 0.50), 1) + " %",
         num(100 * quantile(list(real), 0.50), 1) + " %"],
        ["Quantile 5 %", num(100 * quantile(list(flat), 0.05), 1) + " %",
         num(100 * quantile(list(real), 0.05), 1) + " %"],
        ["Quantile 95 %", num(100 * quantile(list(flat), 0.95), 1) + " %",
         num(100 * quantile(list(real), 0.95), 1) + " %"],
        ["Dégradation apprentissage → test", num(cscv_null().degradation, 3),
         num(cscv_edge().degradation, 3)],
    ]
    return Table(
        "pbo",
        "Probabilité de surajustement (CSCV) et sa propre dispersion d'échantillonnage",
        ["Grandeur", f"{num(CSCV_CONFIGS, 0)} configurations sans edge",
         "une seule en possède un"],
        rows,
        note=("Contrôle de l'instrument sur deux cas dont la réponse est connue "
              "d'avance. Sans edge la PBO vaut "
              + num(100 * sum(flat) / len(flat), 0) + " % en moyenne — exactement la "
              "moitié, comme la symétrie de la construction l'exige — mais son "
              "intervalle à 90 % s'étend de "
              + num(100 * quantile(list(flat), 0.05), 0) + " % à "
              + num(100 * quantile(list(flat), 0.95), 0) + " %. <strong>Une PBO lue sur un "
              "seul backtest est donc elle-même une statistique bruitée</strong>, et seule "
              "une valeur extrême conclut : sous "
              + num(100 * quantile(list(flat), 0.05), 0) + " % elle est peu "
              "compatible avec l'absence d'edge, au-delà de "
              + num(100 * quantile(list(real), 0.95), 0) + " % elle l'est peu avec "
              "sa présence, et entre les deux elle ne tranche rien."),
        rules_after=[0, 4],
    )


def table_crossval() -> Table:
    n_obs = int(SESSION_MIN)
    horizon = int(round(geometry(RR_REF).expected_time))
    rows = []
    for folds in (3, 5, 10):
        leak = leakage_fraction(n_obs, folds, horizon)
        purged = purged_folds(n_obs, folds, horizon=horizon, embargo_pct=0.01)
        kept = sum(len(f.train) for f in purged) / (folds * n_obs)
        naive = (folds - 1) / folds
        wf = walk_forward_windows(n_obs, folds)
        wf_train = sum(len(f.train) for f in wf) / (folds * n_obs)
        rows.append([
            num(folds, 0),
            num(100 * naive, 0) + " %",
            num(100 * leak, 0) + " %",
            num(100 * kept, 0) + " %",
            num(100 * (naive - kept), 0) + " pts",
            num(100 * wf_train, 0) + " %",
        ])
    return Table(
        "crossval",
        "Fuite temporelle d'une validation croisée naïve, coût de la purge, et l'alternative",
        ["Plis", "Apprentissage naïf", "Fuite sans purge",
         "Apprentissage après purge", "Coût de la purge", "Apprentissage en marche avant"],
        rows,
        note=("Une observation par minute sur une séance de "
              + num(SESSION_MIN, 0) + " minutes, un trade dont l'exposition dure "
              + num(horizon, 0) + " minutes — les valeurs du papier, pas des "
              "hypothèses nouvelles. La colonne « fuite » est la part de "
              "l'apprentissage qui recouvre la fenêtre de test&nbsp;: à dix plis, "
              "elle atteint la totalité, et la validation croisée ne valide plus "
              "rien. La marche avant apprend sur moins de données mais ne fuit "
              "jamais&nbsp;; c'est le seul protocole dont le résultat s'interprète "
              "comme une performance atteignable."),
        wide=True,
    )


def table_hmm() -> Table:
    cases = ("regime", "flat", "short")
    cols: list[list[str]] = []
    for kind in cases:
        fitted, loglik, _, _, ll1 = hmm_fit(kind)
        obs, truth = hmm_series(kind)
        n = len(obs)
        d = separability(fitted.means[0], fitted.means[1],
                         0.5 * (fitted.sds[0] + fitted.sds[1]))
        path = viterbi(fitted, list(obs))
        switches = sum(1 for i in range(1, n) if path[i] != path[i - 1])
        k2, k1 = fitted.n_free_parameters, 2
        acc = sum(1 for a, b in zip(path, truth) if a == b) / n
        cols.append([
            num(n, 0),
            num(d, 2),
            num(100 * bayes_error(d), 0) + " %",
            num(fitted.trans[0][0], 2) + " / " + num(fitted.trans[1][1], 2),
            num(fitted.expected_sojourn(0), 1),
            num(switches, 0),
            num(loglik - ll1, 2),
            num(aic(loglik, k2) - aic(ll1, k1), 1),
            num(bic(loglik, k2, n) - bic(ll1, k1, n), 1),
            num(observations_to_separate(d), 0) if d > 0 else "∞",
            num(100 * max(acc, 1 - acc), 0) + " %" if kind == "regime" else "sans objet",
        ])

    labels = [
        "Observations", "Séparabilité d′ estimée", "Erreur de Bayes par point",
        "Persistances estimées", "Séjour moyen, état 1",
        "Basculements de Viterbi", "Gain de log-vraisemblance sur 1 état",
        "ΔAIC (2 états − 1 état)", "ΔBIC (2 états − 1 état)",
        "Observations requises pour d′", "Exactitude du décodage",
    ]
    rows = [[lab, a, b, c] for lab, a, b, c in zip(labels, *cols)]
    _, _, _, _, _ = hmm_fit("short")
    f_short = hmm_fit("short")[0]
    d_short = separability(f_short.means[0], f_short.means[1],
                           0.5 * (f_short.sds[0] + f_short.sds[1]))
    return Table(
        "hmm",
        "Un même HMM à deux états, ajusté sur trois séries dont on connaît la vérité",
        ["Grandeur", "deux régimes réels", "aucun régime, série longue",
         "aucun régime, série courte"],
        rows,
        note=("Les deux colonnes de droite sont ajustées sur du bruit indépendant : "
              "il n'y a <strong>rien</strong> à trouver. Sur série longue, Baum-Welch le "
              "reconnaît et les deux états se confondent. Sur série courte il "
              "produit deux régimes séparés de " + num(d_short, 2) + " écarts-types, "
              "avec un chemin de Viterbi net — et rien dans la sortie du modèle ne "
              "signale l'imposture. Seul le ΔBIC la démasque, et seulement si on le "
              "calcule. Symétriquement, la colonne de gauche montre le prix à payer "
              "de l'autre côté : des régimes <strong>réels</strong> à séparabilité réaliste ne "
              "franchissent le BIC que d'extrême justesse sur sept cent cinquante "
              "observations."),
        rules_after=[2, 5, 8],
        wide=True,
    )


def table_stress() -> Table:
    e0 = edge_law()
    n = int(TRADES_PER_YEAR)
    annual = n * e0.mean
    rows = []
    for s in SCENARIOS:
        loss = scenario_loss_r(s, INDEX_LEVEL, STOP_PTS, fill_fraction=1.0)
        rows.append([
            s.label, s.window,
            num(abs(s.move_pct), 1) + " %",
            num(abs(s.move_pct) / 100 * INDEX_LEVEL, 0),
            num(loss, 0) + " R",
            num(loss / annual, 1),
        ])
    return Table(
        "stress",
        "Scénarios de choc, ramenés au risque nominal et à l'année d'espérance",
        ["Scénario", "Fenêtre", "Amplitude", "Points d'indice",
         "Perte si le stop ne sert pas", "en années d'espérance"],
        rows,
        note=("Le stop vaut " + num(STOP_PTS, 0) + " points. Toute amplitude qui le "
              "franchit sans exécution intermédiaire se paie intégralement : la "
              "colonne de droite exprime cette perte en années de gain espéré, à "
              "l'edge de référence. Un seul écart d'ouverture de 2 % efface "
              + num(scenario_loss_r(SCENARIOS[-1], INDEX_LEVEL, STOP_PTS) / annual, 1)
              + " années."),
        wrap_cols=[0],
        wide=True,
    )


def table_tails() -> Table:
    e0 = edge_law()
    # L'EVT porte sur les drawdowns annuels simulés : c'est la grandeur dont la
    # queue décide de la survie, et la seule du dispositif qui soit lourde.
    dd = [p.max_drawdown for p in mc_paths("edge")]
    thr = quantile(dd, 0.90)
    fit = fit_gpd(dd, thr)
    k = max(2, len(dd) // 20)
    v_exact = var_from_law(e0, 0.99)
    v_gauss = var_gaussian(e0.mean, e0.sd, 0.99)
    rows = [
        ["VaR 99 % d'un trade — loi exacte", num(v_exact, 2) + " R"],
        ["VaR 99 % d'un trade — gaussienne", num(v_gauss, 2) + " R"],
        ["Rapport gaussien / exact", num(v_gauss / max(v_exact, 1e-9), 1)],
        ["ES 99 % d'un trade — loi exacte", num(es_from_law(e0, 0.99), 2) + " R"],
        ["ES 99 % d'un trade — gaussienne", num(es_gaussian(e0.mean, e0.sd, 0.99), 2) + " R"],
        ["Cornish-Fisher applicable ?",
         "oui" if cornish_fisher_is_valid(e0.skewness, e0.excess_kurtosis) else "non"],
        ["Seuil EVT — quantile 90 % du drawdown annuel", num(thr, 0) + " R"],
        ["Dépassements exploités", num(fit.n_exceed, 0)],
        ["Indice de queue ξ — méthode des moments", num(fit.shape, 3)],
        ["Indice de queue ξ — estimateur de Hill", num(hill_estimator(dd, k), 3)],
        ["Variance de queue finie (ξ < ½) ?", "oui" if fit.has_finite_variance else "non"],
        ["Drawdown annuel, quantile 99 % simulé", num(quantile(dd, 0.99), 0) + " R"],
        ["Drawdown annuel, quantile 99,9 % extrapolé", num(var_evt(fit, 0.999), 0) + " R"],
    ]
    return Table(
        "tails",
        "Queues : approximation gaussienne, loi exacte du trade, extrapolation EVT du drawdown",
        ["Grandeur", "Valeur"],
        rows,
        note=("Deux résultats, et ils vont en sens contraire. D'abord la VaR "
              "gaussienne d'un trade <strong>surestime</strong> la perte d'un facteur "
              + num(v_gauss / max(v_exact, 1e-9), 0) + ", parce qu'elle lit un "
              "écart-type dont la quasi-totalité vient de la queue de <strong>gain</strong> ; le "
              "correctif de Cornish-Fisher censé y remédier n'est pas monotone à "
              "cette asymétrie, et aucun de ses quantiles n'est interprétable. "
              "Ensuite la VaR et l'ES exacts d'un trade coïncident, à "
              + num(v_exact, 2) + " R : sous le pour-cent extrême, toute la masse "
              "est dans l'atome du stop. <strong>Le stop est l'ES — jusqu'au premier "
              "saut</strong>, et c'est exactement ce que la table suivante chiffre."),
        rules_after=[2, 5, 10],
    )


def table_jump() -> Table:
    e0 = edge_law()
    o = geometry(RR_REF)
    p = prob_jump_during_trade(JUMP, o.expected_time, SESSION_MIN)
    excess = expected_slippage_beyond_stop(JUMP, STOP_PTS)
    adj = jump_adjusted_expectancy(e0, JUMP, STOP_PTS, o.expected_time, SESSION_MIN)
    rev = reverse_stress_move_pct(e0, TRADES_PER_YEAR, INDEX_LEVEL, STOP_PTS)
    rows = [
        ["Intensité de saut retenue", num(JUMP.intensity_per_day, 3) + " / séance"],
        ["Amplitude type d'un saut", num(JUMP.sd_jump, 0) + " points"],
        ["Exposition d'un trade", num(o.expected_time, 1) + " min"],
        ["P(un saut pendant l'exposition)", num(100 * p, 2) + " %"],
        ["Surcoût espéré d'un saut, E[(|J| − a)⁺]", num(excess, 2) + " points"],
        ["en unités de risque", num(excess / STOP_PTS, 2) + " R"],
        ["Espérance avant correction", num(e0.mean, 4) + " R"],
        ["Espérance après correction de saut", num(adj, 4) + " R"],
        ["Part de l'edge consommée", num(100 * (1 - adj / e0.mean), 0) + " %"],
        ["Choc qui efface une année d'espérance", num(rev, 2) + " %"],
        ["en points d'indice", num(rev / 100 * INDEX_LEVEL, 0)],
    ]
    return Table(
        "jump",
        "Risque de saut et stress inversé : ce que le stop ne protège pas",
        ["Grandeur", "Valeur"],
        rows,
        note=("Le saut est d'espérance nulle — il ne biaise pas le prix. Il biaise "
              "le <strong>trade</strong>, parce que le stop tronque le gain et laisse la perte "
              "courir : l'asymétrie est dans la géométrie, pas dans le marché, et "
              "elle survit à toute hypothèse de saut centré. Elle consomme "
              + num(100 * (1 - adj / e0.mean), 0) + " % de l'edge de référence à "
              "l'intensité retenue."),
        rules_after=[5, 8],
    )



TRADES_PER_DAY_GRID = (2.0, 4.0, 8.0, 16.0)


@lru_cache(maxsize=None)
def law_at_multiple(k: float) -> TradeLaw:
    """Loi du trade à la géométrie de référence, sous une dérive `k·µ*`."""
    o = geometry(RR_REF)
    mu_star = FRICTION / o.expected_time
    return null_law().tilted_to_mean((k * mu_star * o.expected_time - FRICTION) / STOP_PTS)


@lru_cache(maxsize=None)
def required_multiple(years: float = 1.0, n_trials: int = 1,
                      confidence: float = 0.95) -> float:
    """Multiple de dérive `k` rendant l'edge déclarable sur `years` années.

    On résout en `k` l'équation `DSR(k) = confidence`, où le Sharpe déflaté
    intègre à la fois la longueur d'historique et le nombre de configurations
    essayées. Le résultat répond à la question posée au papier dans le seul
    sens où elle est décidable : non pas « y a-t-il un edge ? », mais *quel
    edge faudrait-il pour qu'un an de résultats permette de l'affirmer ?*
    """
    def dsr(k: float) -> float:
        law = law_at_multiple(k)
        n = int(round(years * TRADES_PER_YEAR))
        return deflated_sharpe(law.sharpe_per_trade, n, n_trials,
                               law.skewness, law.excess_kurtosis)

    # La borne haute n'est pas un réglage : elle est imposée par le support
    # de la loi du trade. L'inclinaison d'Esscher ne déplace la moyenne qu'à
    # l'intérieur des valeurs extrêmes du support, et la moyenne visée vaut
    # `(k − 1)·c/L`. Poser une borne fixe supposerait la géométrie ; la
    # déduire du support la rend valide à toute largeur de stop.
    c_sur_l = FRICTION / STOP_PTS
    plafond = max(null_law().values)
    # Neuf dixièmes du plafond, et non le plafond : tout près du support la
    # loi inclinée dégénère vers une masse ponctuelle, son aplatissement
    # diverge, et le Sharpe déflaté cesse d'être calculable de façon fiable.
    # La marge n'est pas cosmétique — sans elle la bissection lirait un faux
    # échec dans un artefact numérique.
    k_max = 1.0 + 0.90 * plafond / c_sur_l if c_sur_l > 0 else 64.0
    lo, hi = 1.0, min(64.0, k_max)
    if hi <= lo or dsr(hi) < confidence:
        return math.inf
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if dsr(mid) < confidence:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def table_verdict() -> Table:
    e0 = edge_law()
    sr = e0.sharpe_per_trade
    mtrl = min_track_record_length(sr, 0.0, e0.skewness, e0.excess_kurtosis)
    mbtl = minimum_backtest_length(sr, N_TRIALS_REF)
    k1, k100 = required_multiple(1.0, 1), required_multiple(1.0, N_TRIALS_REF)
    l1, l100 = law_at_multiple(k1), law_at_multiple(k100)
    n = int(TRADES_PER_YEAR)
    rows = [
        ["Edge de référence (µ = 2 µ*)", num(e0.mean, 3) + " R/trade",
         num(annualise(sr, TRADES_PER_YEAR), 2)],
        ["Déclarable en 1 an, 1 essai", num(k1, 1) + " µ*",
         num(annualise(l1.sharpe_per_trade, TRADES_PER_YEAR), 2)],
        [f"Déclarable en 1 an, {num(N_TRIALS_REF, 0)} essais", num(k100, 1) + " µ*",
         num(annualise(l100.sharpe_per_trade, TRADES_PER_YEAR), 2)],
        ["Écart au réel", "facteur " + num(k100 / DRIFT_MULTIPLE, 1), "—"],
    ]
    for tpd in TRADES_PER_DAY_GRID:
        per_year = tpd * SESSIONS_PER_YEAR
        rows.append([
            f"À {num(tpd, 0)} trades par séance",
            num(mtrl / per_year, 1) + " ans pour ŜR > 0",
            num(mbtl / per_year, 1) + " ans après 100 essais",
        ])
    return Table(
        "verdict",
        "Le verdict, dans les deux sens où la question est décidable",
        ["Situation", "Dérive requise ou délai", "Sharpe annualisé ou délai après sélection"],
        rows,
        note=("Deux lectures d'un même calcul. Par le haut : pour qu'une année de "
              "résultats <strong>suffise</strong> à déclarer l'edge après "
              + num(N_TRIALS_REF, 0) + " configurations essayées, il faudrait une "
              "dérive de " + num(k100, 1) + " µ* — un Sharpe annualisé de "
              + num(annualise(l100.sharpe_per_trade, TRADES_PER_YEAR), 1) + ", soit "
              + num(k100 / DRIFT_MULTIPLE, 0) + " fois l'hypothèse de référence. Par "
              "le bas : à edge de référence inchangé, le seul levier qui raccourcisse "
              "réellement le délai est la <strong>fréquence</strong> — le délai est un nombre de "
              "trades, et le convertir en années est le seul endroit où la cadence "
              "intervienne. Passer de deux à huit trades par séance ramène "
              + num(mbtl / (2 * SESSIONS_PER_YEAR), 0) + " ans à "
              + num(mbtl / (8 * SESSIONS_PER_YEAR), 0) + "."),
        rules_after=[3],
        wide=True,
    )


def _mc_separation() -> float:
    """Trade à partir duquel les deux faisceaux ne se touchent plus.

    Les faisceaux de la figure sont ceux des quantiles 5 % et 95 % ; ils se
    séparent quand le décile bas de la loi avec dérive passe au-dessus du
    décile haut de la loi nulle. La figure les trace sur `MC_TRADES` trades ;
    cette fonction rend l'abscisse de la séparation, ou `MC_TRADES` si elle
    n'a pas lieu.
    """
    from .mc import Rng, fan, fan_index

    niveaux = (0.05, 0.25, 0.50, 0.75, 0.95)
    pas = 12
    idx = fan_index(MC_TRADES, pas)
    fn = fan(null_law(), MC_TRADES, 900, niveaux, Rng(SEED + 31), pas)
    fe = fan(edge_law(), MC_TRADES, 900, niveaux, Rng(SEED + 32), pas)
    for k, x in enumerate(idx):
        if fe[0.05][k] > fn[0.95][k]:
            return float(x)
    return float(MC_TRADES)


def values() -> dict[str, str]:
    """Valeurs scalaires citées dans le texte de la troisième partie."""
    n0, e0 = null_law(), edge_law()
    n = int(TRADES_PER_YEAR)
    sr = e0.sharpe_per_trade
    pn, pe = mc_paths("null"), mc_paths("edge")
    flat, real = cscv_distribution()
    o20 = geometry(RR_REF)
    theta = adjustment_coefficient(e0)
    k1, k100 = required_multiple(1.0, 1), required_multiple(1.0, N_TRIALS_REF)
    l100 = law_at_multiple(k100)
    mtrl = min_track_record_length(sr, 0.0, e0.skewness, e0.excess_kurtosis)
    mbtl = minimum_backtest_length(sr, N_TRIALS_REF)
    sd_tr = 1.0 / math.sqrt(n)
    f_short = hmm_fit("short")[0]
    d_short = separability(f_short.means[0], f_short.means[1],
                           0.5 * (f_short.sds[0] + f_short.sds[1]))
    f_reg = hmm_fit("regime")[0]
    d_reg = separability(f_reg.means[0], f_reg.means[1],
                         0.5 * (f_reg.sds[0] + f_reg.sds[1]))
    horizon = int(round(o20.expected_time))
    jump_p = prob_jump_during_trade(JUMP, o20.expected_time, SESSION_MIN)
    jump_adj = jump_adjusted_expectancy(e0, JUMP, STOP_PTS, o20.expected_time,
                                        SESSION_MIN)
    v_exact = var_from_law(e0, 0.99)
    v_gauss = var_gaussian(e0.mean, e0.sd, 0.99)

    return {
        "q_trades_year": num(TRADES_PER_YEAR, 0),
        "q_mult": num(DRIFT_MULTIPLE, 0),
        "q_edge_r": num(e0.mean, 3),
        "q_null_r": num(n0.mean, 3),
        "q_sd_r": num(e0.sd, 2),
        "q_skew": num(e0.skewness, 2),
        "q_kurt": num(e0.excess_kurtosis, 1),
        "q_sharpe": num(sr, 4),
        "q_sharpe_an": num(annualise(sr, TRADES_PER_YEAR), 2),
        "q_sortino": num(e0.sortino(), 4),
        "q_sd_dd": num(e0.sd / e0.downside_deviation(), 2),
        "q_sd_dd_50": num(edge_law(50.0).sd / edge_law(50.0).downside_deviation(), 1),
        # Ce que chacune des deux dispersions fait d'un bout à l'autre de la
        # grille de ratios. Le document affirmait que la dispersion à la
        # baisse « ne bouge pas quand on éloigne le target » ; elle bouge de
        # dix-huit pour cent, quand la dispersion totale est multipliée par
        # six. C'est le rapport des deux mouvements qui porte le résultat,
        # non l'immobilité de l'un d'eux.
        "q_sd_dd_nul": num(n0.sd / n0.downside_deviation(), 2),
        "q_dd_grid": num(100.0 * (edge_law(max(RR_GRID)).downside_deviation()
                                  / edge_law(min(RR_GRID)).downside_deviation()
                                  - 1.0), 0),
        "q_sd_grid": num(edge_law(max(RR_GRID)).sd / edge_law(min(RR_GRID)).sd, 1),
        "q_dd": num(e0.downside_deviation(), 2),
        "q_omega": num(e0.omega(), 3),
        "q_kelly": num(100 * e0.kelly_fraction(), 2),
        "q_pwin": num(100 * e0.prob_win, 1),
        "q_mtrl": num(mtrl, 0),
        "q_mtrl_years": num(mtrl / TRADES_PER_YEAR, 1),
        "q_mbtl": num(mbtl, 0),
        "q_mbtl_years": num(mbtl / TRADES_PER_YEAR, 1),
        "q_trials": num(N_TRIALS_REF, 0),
        "q_maxsr": num(expected_max_sharpe(N_TRIALS_REF, sd_tr), 3),
        "q_maxsr_an": num(annualise(expected_max_sharpe(N_TRIALS_REF, sd_tr),
                                    TRADES_PER_YEAR), 2),
        "q_dsr": num(100 * deflated_sharpe(sr, n, N_TRIALS_REF, e0.skewness,
                                           e0.excess_kurtosis), 1),
        "q_dsr1": num(100 * deflated_sharpe(sr, n, 1, e0.skewness,
                                            e0.excess_kurtosis), 0),
        "q_k1": num(k1, 1),
        "q_k100": num(k100, 1),
        "q_k100_sharpe": num(annualise(l100.sharpe_per_trade, TRADES_PER_YEAR), 1),
        "q_k100_ratio": num(k100 / DRIFT_MULTIPLE, 0),
        "q_mdd_null": num(expected_max_drawdown_null(n0.sd, n), 0),
        "q_mdd_edge": num(expected_max_drawdown_drift(e0, n), 0),
        "q_mdd_q95": num(drawdown_quantile_null(n0.sd, n, 0.95), 0),
        "q_annual_gain": num(n * e0.mean, 0),
        "q_theta": num(theta, 4),
        "q_ruin_depth": num(ruin_depth_for_probability(e0, 0.05), 0),
        "q_ruin_years": num(ruin_depth_for_probability(e0, 0.05) / (n * e0.mean), 1),
        "q_calmar": num(calmar(e0, TRADES_PER_YEAR, n), 2),
        "q_tuw80": num(100 * prob_time_under_water_exceeds(0.80), 0),
        "q_mc_paths": num(MC_PATHS, 0),
        # Le trade où les deux intervalles à 90 % cessent de se toucher. La
        # légende de la figure annonçait un recouvrement « pendant toute
        # l'année » ; les faisceaux se séparent bien avant, et cela n'a rien
        # d'un résultat sur le marché — la dérive de référence est supposée à
        # deux fois le seuil de rentabilité, donc au niveau exact qui rend la
        # stratégie rentable.
        "q_mc_separation": num(_mc_separation(), 0),
        "q_p_profit_null": num(100 * sum(1 for x in pn if x.terminal > 0) / len(pn), 0),
        "q_p_loss_edge": num(100 * sum(1 for x in pe if x.terminal <= 0) / len(pe), 0),
        "q_sr_null_q95": num(quantile([x.sharpe for x in pn], 0.95), 3),
        "q_pbo_null": num(100 * sum(flat) / len(flat), 0),
        "q_pbo_lo": num(100 * quantile(list(flat), 0.05), 0),
        "q_pbo_hi": num(100 * quantile(list(flat), 0.95), 0),
        "q_pbo_edge": num(100 * sum(real) / len(real), 0),
        "q_pbo_edge_hi": num(100 * quantile(list(real), 0.95), 0),
        "q_leak5": num(100 * leakage_fraction(int(SESSION_MIN), 5, horizon), 0),
        "q_horizon": num(horizon, 0),
        "q_dprime_short": num(d_short, 2),
        "q_dprime_reg": num(d_reg, 2),
        "q_bayes_short": num(100 * bayes_error(d_short), 0),
        "q_hmm_short_n": num(HMM_SHORT, 0),
        "q_hmm_n": num(HMM_OBS, 0),
        "q_obs_sep": num(observations_to_separate(0.30), 0),
        "q_var_exact": num(v_exact, 2),
        "q_var_gauss": num(v_gauss, 2),
        "q_var_ratio": num(v_gauss / max(v_exact, 1e-9), 0),
        "q_jump_p": num(100 * jump_p, 2),
        "q_jump_excess": num(expected_slippage_beyond_stop(JUMP, STOP_PTS), 2),
        "q_jump_cost": num(100 * (1 - jump_adj / e0.mean), 0),
        "q_reverse": num(reverse_stress_move_pct(e0, TRADES_PER_YEAR, INDEX_LEVEL,
                                                 STOP_PTS), 2),
        "q_reverse_pts": num(reverse_stress_move_pct(
            e0, TRADES_PER_YEAR, INDEX_LEVEL, STOP_PTS) / 100 * INDEX_LEVEL, 0),
        "q_gap2_years": num(scenario_loss_r(SCENARIOS[-1], INDEX_LEVEL, STOP_PTS)
                            / (n * e0.mean), 1),
        "q_1987_years": num(scenario_loss_r(SCENARIOS[0], INDEX_LEVEL, STOP_PTS)
                            / (n * e0.mean), 1),
        "q_freq8": num(mbtl / (8 * SESSIONS_PER_YEAR), 1),
        "q_n_instruments": num(len(table_instruments().rows), 0),
    }


TABLES = (
    table_instruments,
    table_ratios,
    table_detectability,
    table_drawdown,
    table_montecarlo,
    table_selection,
    table_haircut,
    table_pbo,
    table_crossval,
    table_hmm,
    table_stress,
    table_tails,
    table_jump,
    table_verdict,
)


def all_tables() -> dict[str, Table]:
    return {t.key: t for t in (fn() for fn in TABLES)}


def main() -> None:
    print("ALP-1 — instruments de validation et de stress\n")
    for fn in TABLES:
        t = fn()
        print(f"\n### {t.caption}\n")
        print(t.to_text())


if __name__ == "__main__":
    main()
