"""Génère les tables chiffrées du paper ALP-1.

Usage :
    python -m alp1.report
"""

from __future__ import annotations

import math

from .barriers import (
    drift_to_information_ratio,
    prob_target_before_stop,
    prob_touch_single_barrier,
    required_drift,
)
from .costs import (
    COST_BASE,
    COST_OPTIMISTIC,
    COST_REALISTIC,
    ES,
    breakeven_hit_rate,
    expectancy_r,
    deflated_threshold_sharpe,
    required_reward_risk,
    stop_points,
    trades_for_significance,
)

# Hypothèses de marché. ES vers 6000, volatilité 1-min typique en RTH.
INDEX_LEVEL = 6000.0
SIGMA_1MIN = 1.25  # points; ~ATR(1m) 2.5 pts => sigma ~1.25
STOP_GRID_PCT = (0.005, 0.010, 0.050, 0.100, 0.250)


def _fmt(x: float, nd: int = 2) -> str:
    if x is math.inf or x == math.inf:
        return "∞"
    return f"{x:,.{nd}f}"


def table_stop_sizes() -> str:
    rows = [
        "| Stop (% indice) | Points | Ticks | Risque nominal $/contrat |",
        "|---|---|---|---|",
    ]
    for pct in STOP_GRID_PCT:
        pts = stop_points(INDEX_LEVEL, pct)
        rows.append(
            f"| {pct:.3f} % | {pts:.2f} | {ES.ticks(pts):.1f} | "
            f"{pts * ES.point_value:,.2f} |"
        )
    return "\n".join(rows)


def table_friction_ratio() -> str:
    models = [
        ("Optimiste", COST_OPTIMISTIC),
        ("Base", COST_BASE),
        ("Réaliste", COST_REALISTIC),
    ]
    rows = [
        "| Stop (%) | Risque $ | " + " | ".join(f"c/L {n}" for n, _ in models) + " |",
        "|---|---|" + "---|" * len(models),
    ]
    for pct in STOP_GRID_PCT:
        pts = stop_points(INDEX_LEVEL, pct)
        risk = pts * ES.point_value
        cells = []
        for _, m in models:
            cells.append(f"{m.friction_usd(ES) / risk:.2f}")
        rows.append(f"| {pct:.3f} % | {risk:,.2f} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def table_breakeven() -> str:
    rr_grid = (2.0, 3.0, 5.0, 10.0, 20.0)
    rows = [
        "| Stop (%) | c/L | " + " | ".join(f"p* @ R={r:g}" for r in rr_grid) + " |",
        "|---|---|" + "---|" * len(rr_grid),
    ]
    for pct in STOP_GRID_PCT:
        pts = stop_points(INDEX_LEVEL, pct)
        risk = pts * ES.point_value
        ratio = COST_BASE.friction_usd(ES) / risk
        cells = [f"{100 * breakeven_hit_rate(r, ratio):.1f} %" for r in rr_grid]
        rows.append(f"| {pct:.3f} % | {ratio:.2f} | " + " | ".join(cells) + " |")
    rows.append("")
    rows.append("Référence sans friction : p* = 1/(R+1) = " + ", ".join(
        f"{100 / (r + 1):.1f} % (R={r:g})" for r in rr_grid
    ))
    return "\n".join(rows)


def table_noise_stopout() -> str:
    horizons = (1.0, 5.0, 15.0, 30.0)
    rows = [
        "| Stop (%) | Points | " + " | ".join(f"P(stop) {h:g} min" for h in horizons) + " |",
        "|---|---|" + "---|" * len(horizons),
    ]
    for pct in STOP_GRID_PCT:
        pts = stop_points(INDEX_LEVEL, pct)
        cells = [
            f"{100 * prob_touch_single_barrier(pts, SIGMA_1MIN, h):.1f} %"
            for h in horizons
        ]
        rows.append(f"| {pct:.3f} % | {pts:.2f} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def table_required_drift() -> str:
    """Drift requis pour l'équilibre, à R:R = 3 fixe."""
    rr = 3.0
    fric_pts = COST_BASE.friction_points(ES)
    rows = [
        "| Stop (%) | Stop pts | TP pts | µ requis (pts/min) | Horizon méd. (min) | IR requis |",
        "|---|---|---|---|---|---|",
    ]
    for pct in STOP_GRID_PCT:
        a = stop_points(INDEX_LEVEL, pct)
        b = rr * a
        mu = required_drift(a, b, SIGMA_1MIN, fric_pts)
        if mu is math.inf or mu == math.inf:
            rows.append(f"| {pct:.3f} % | {a:.2f} | {b:.2f} | ∞ | — | ∞ |")
            continue
        # Horizon caractéristique : temps pour parcourir le stop au drift requis,
        # borné par la diffusion.
        horizon = max(0.25, (a / mu) if mu > 0 else 1.0)
        horizon = min(horizon, 60.0)
        ir = drift_to_information_ratio(mu, SIGMA_1MIN, horizon)
        rows.append(
            f"| {pct:.3f} % | {a:.2f} | {b:.2f} | {mu:.4f} | {horizon:.1f} | {ir:.2f} |"
        )
    return "\n".join(rows)


def table_zero_drift_identity() -> str:
    """Montre que sans drift, tout couple (stop, TP) a la même espérance nulle."""
    rr_grid = (2.0, 3.0, 5.0, 10.0, 20.0)
    a = stop_points(INDEX_LEVEL, 0.010)
    rows = [
        "| R:R | P(TP avant SL), µ=0 | p* sans friction | p* avec friction | E[R] à p=P(µ=0) |",
        "|---|---|---|---|---|",
    ]
    risk = a * ES.point_value
    ratio = COST_BASE.friction_usd(ES) / risk
    for r in rr_grid:
        p0 = prob_target_before_stop(a, r * a, 0.0, SIGMA_1MIN)
        rows.append(
            f"| {r:g} | {100 * p0:.2f} % | {100 / (r + 1):.2f} % | "
            f"{100 * breakeven_hit_rate(r, ratio):.2f} % | "
            f"{expectancy_r(p0, r, ratio):+.3f} R |"
        )
    return "\n".join(rows)


def table_sizing_comparison() -> str:
    """Compare stop serré à forte taille et stop normalisé à la volatilité."""
    fric = COST_BASE.friction_usd(ES)
    budget = 300.0  # risque $ par trade, constant

    scenarios = [
        ("Serré 0.010 %", stop_points(INDEX_LEVEL, 0.010)),
        ("Serré 0.050 %", stop_points(INDEX_LEVEL, 0.050)),
        ("Vol-normalisé 1.5σ(1m)", 1.5 * SIGMA_1MIN),
        ("Vol-normalisé 3σ(1m)", 3.0 * SIGMA_1MIN),
    ]
    rows = [
        "| Configuration | Stop pts | Contrats @300$ | Friction totale $ | c/L | p* @ R=3 |",
        "|---|---|---|---|---|---|",
    ]
    for name, pts in scenarios:
        risk_per_ct = pts * ES.point_value
        n = max(1, int(budget / risk_per_ct))
        total_fric = n * fric
        ratio = fric / risk_per_ct
        rows.append(
            f"| {name} | {pts:.2f} | {n} | {total_fric:,.2f} | {ratio:.2f} | "
            f"{100 * breakeven_hit_rate(3.0, ratio):.1f} % |"
        )
    return "\n".join(rows)


def table_sample_size() -> str:
    configs = [
        ("Optimiste", 0.30, 1.50),
        ("Modéré", 0.20, 1.50),
        ("Marginal", 0.10, 1.80),
        ("Convexe (lottery)", 0.15, 4.00),
    ]
    rows = [
        "| Profil | E[R]/trade | σ(R) | N trades (80 % puissance) |",
        "|---|---|---|---|",
    ]
    for name, mu, sd in configs:
        rows.append(f"| {name} | {mu:.2f} | {sd:.2f} | {trades_for_significance(mu, sd):,} |")
    return "\n".join(rows)


def table_multiple_testing() -> str:
    rows = [
        "| Configurations testées | N=200 obs | N=500 obs | N=1000 obs |",
        "|---|---|---|---|",
    ]
    for trials in (10, 100, 1000, 10000):
        cells = [f"{deflated_threshold_sharpe(trials, n):.3f}" for n in (200, 500, 1000)]
        rows.append(f"| {trials:,} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


SECTIONS = [
    ("Taille du stop selon l'interprétation du pourcentage", table_stop_sizes),
    ("Friction rapportée au risque nominal (c/L)", table_friction_ratio),
    ("Hit rate d'équilibre p*", table_breakeven),
    ("Probabilité de stop-out par le seul bruit", table_noise_stopout),
    ("Identité d'espérance nulle sans drift", table_zero_drift_identity),
    ("Drift requis pour l'équilibre (R:R = 3)", table_required_drift),
    ("Stop serré à forte taille vs stop normalisé", table_sizing_comparison),
    ("Taille d'échantillon requise", table_sample_size),
    ("Seuil de Sharpe sous test multiple", table_multiple_testing),
]


def main() -> None:
    print(f"ALP-1 — tables quantitatives")
    print(f"Contrat {ES.symbol} | indice {INDEX_LEVEL:,.0f} | "
          f"σ(1 min) = {SIGMA_1MIN} pts | friction base = "
          f"{COST_BASE.friction_usd(ES):,.2f} $/AR\n")
    for title, fn in SECTIONS:
        print(f"\n### {title}\n")
        print(fn())


if __name__ == "__main__":
    main()
