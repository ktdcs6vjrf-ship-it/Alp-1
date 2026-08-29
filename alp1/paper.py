"""Construction du document à partir du gabarit.

    python -m alp1.paper

Le gabarit `docs/alp1-paper.template.html` contient la prose et des balises de
substitution&nbsp;; tout ce qui est chiffré — valeurs isolées, tables, figures —
est injecté par ce module à partir du noyau. Un chiffre du texte et le point
correspondant d'une figure ne peuvent donc pas diverger.

Balises reconnues :
    {{nom}}                    valeur scalaire
    {{TABLE:clé}}              table, numérotée dans l'ordre d'apparition
    {{FIGURE:clé|légende}}     figure, numérotée dans l'ordre d'apparition
"""

from __future__ import annotations

import math
import pathlib
import re

from . import dow, fib, gex, lexicon, orderflow, quant, vprofile
from .barriers import prob_touch_single_barrier
from .costs import COST_BASE, COST_REALISTIC, ES, norm_cdf
from .figcss import FIGURE_CSS, FIGURE_TOKENS_DARK, FIGURE_TOKENS_LIGHT
from .figquant import render_all as render_quant_figures
from .figterm import render_all as render_terminal_figures
from .figures import render_all
from .horizon import outcome, outcome_scaled
from .pieds import figure_html
from .report import (
    FRICTION,
    HURST,
    INDEX_LEVEL,
    RESIDUAL_PCT,
    RESIDUAL_PTS,
    SESSION_DISPERSION,
    SESSION_MIN,
    SIGMA_1MIN,
    STOP_PCT,
    STOP_PTS,
    all_tables,
    num,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "docs" / "alp1-paper.template.html"
OUTPUT = ROOT / "docs" / "alp1-paper.html"


def _geom(rr: float):
    return outcome_scaled(STOP_PTS, rr * STOP_PTS, SESSION_MIN, SIGMA_1MIN, HURST)


def _n_trades(rr: float, mu: float) -> float:
    o = _geom(rr)
    e = (mu * o.expected_time - FRICTION) / STOP_PTS
    sr = e / (o.sd_gross / STOP_PTS)
    return (2.0 / sr) ** 2 if sr > 0 else math.inf


def values() -> dict[str, str]:
    """Toutes les valeurs scalaires citées dans le texte."""
    o5, o10, o20, o30, o50 = (_geom(r) for r in (5.0, 10.0, 20.0, 30.0, 50.0))
    d20 = outcome(STOP_PTS, 20.0 * STOP_PTS, SESSION_MIN, SIGMA_1MIN)
    d30 = outcome(STOP_PTS, 30.0 * STOP_PTS, SESSION_MIN, SIGMA_1MIN)
    c_ratio = FRICTION / STOP_PTS
    c_real = COST_REALISTIC.friction_points(ES)
    sigma_sqrt = SIGMA_1MIN * math.sqrt(SESSION_MIN)
    b30 = 30.0 * STOP_PTS
    advance = STOP_PTS
    d_remain = b30 - advance
    mu_ref = FRICTION / o20.expected_time

    def ir(o) -> float:
        return FRICTION / (SIGMA_1MIN * math.sqrt(o.expected_time))

    v: dict[str, str] = {
        "index": num(INDEX_LEVEL, 0),
        "stop_pct": num(STOP_PCT, 3),
        "stop_pts": num(STOP_PTS, 2),
        "stop_ticks": num(ES.ticks(STOP_PTS), 0),
        "tgt20": num(20 * STOP_PTS, 0),
        "tgt30": num(30 * STOP_PTS, 0),
        "tgt20_pct": num(100 * 20 * STOP_PTS / INDEX_LEVEL, 2),
        "tgt30_pct": num(100 * 30 * STOP_PTS / INDEX_LEVEL, 2),
        "residual_pct": num(RESIDUAL_PCT, 3),
        "residual_pts": num(RESIDUAL_PTS, 2),
        "friction_pts": num(FRICTION, 2),
        "residual_plus_c": num(RESIDUAL_PTS + FRICTION, 2),
        "comm": num(COST_REALISTIC.commission_rt, 2),
        "cl_real": num(c_real / STOP_PTS, 3),
        "c_real": num(c_real, 2),
        "lift_rel": num(100 * c_ratio, 1),
        "sigma1": num(SIGMA_1MIN, 2),
        "sigma_sess": num(SESSION_DISPERSION, 0),
        "sigma_sess_pct": num(100 * SESSION_DISPERSION / INDEX_LEVEL, 2),
        "sigma_sqrt": num(sigma_sqrt, 1),
        "sigma_gap": num(SESSION_DISPERSION / sigma_sqrt, 1),
        "hurst": num(HURST, 2),
        "session": num(SESSION_MIN, 0),
        "p0_5": num(100 / 6.0, 2),
        "p0_20": num(100 / 21.0, 2),
        "p0_30": num(100 / 31.0, 2),
        "pstar_5": num(100 * (1 + c_ratio) / 6.0, 2),
        "pstar_20": num(100 * (1 + c_ratio) / 21.0, 2),
        "dp5": num(100 * c_ratio / 6.0, 2),
        "dp20": num(100 * c_ratio / 21.0, 2),
        "ir5": num(ir(o5), 3),
        "ir20": num(ir(o20), 3),
        "ir20_real": num(c_real / (SIGMA_1MIN * math.sqrt(o20.expected_time)), 3),
        "ptp30": num(100 * o30.p_target, 2),
        "ptp30_diff": num(100 * d30.p_target, 3),
        "z30_diff": num(b30 / sigma_sqrt, 1),
        "z20": num(20 * STOP_PTS / SESSION_DISPERSION, 1),
        "z30": num(b30 / SESSION_DISPERSION, 1),
        "tau20": num(o20.expected_time, 1),
        "tau30": num(o30.expected_time, 1),
        "tau50": num(o50.expected_time, 1),
        "tau_gain_2030": num(100 * (o30.expected_time / o20.expected_time - 1), 0),
        "tau_gain_3050": num(100 * (o50.expected_time / o30.expected_time - 1), 0),
        "ptp_ratio_2030": num(o20.p_target / o30.p_target, 1),
        "ptp_ratio_3050": num(o30.p_target / o50.p_target, 1),
        "d_remain": num(d_remain, 0),
        "displayed_ratio": num(d_remain / RESIDUAL_PTS, 0),
        "effective_ratio": num((d_remain - FRICTION) / (RESIDUAL_PTS + FRICTION), 0),
        "noise5": num(100 * prob_touch_single_barrier(RESIDUAL_PTS, SIGMA_1MIN, 5.0), 1),
        "mu_k2": num(2 * mu_ref * 60, 2),
        "n20_k2": num(_n_trades(20.0, 2 * mu_ref), 0),
        "n10_k2": num(_n_trades(10.0, 2 * mu_ref), 0),
        "n20_k3": num(_n_trades(20.0, 3 * mu_ref), 0),
        "sr_typ": "0,02 à 0,05",
    }
    v.update(_layer_values())
    v.update(quant.values())
    return v


def _layer_values() -> dict[str, str]:
    """Valeurs scalaires de la seconde partie — les sept couches.

    Elles proviennent des mêmes fonctions que les tables et les figures de
    `alp1.lexicon` et `alp1.figterm` : un chiffre du texte et le point
    correspondant d'une figure ne peuvent pas diverger.
    """
    adv = lexicon.ADV_USD
    gex_req = gex.required_gex_for_hurst(HURST, adv, horizon_min=SESSION_MIN)
    o20 = _geom(20.0)
    mu_star = FRICTION / o20.expected_time

    prof = vprofile.reference_profile()
    lvn = prof.lvn()
    lvn_worst = min(lvn, key=lambda lv: prof.volumes[prof.prices.index(lv)])
    sig_poc = prof.sigma_at(prof.poc, SIGMA_1MIN)
    sig_lvn = prof.sigma_at(lvn_worst, SIGMA_1MIN)

    leg_len = 40.0
    target = 20.0 * STOP_PTS
    o_ote = outcome_scaled(STOP_PTS, target + fib.OTE_LOW * leg_len, SESSION_MIN,
                           SIGMA_1MIN, HURST)
    cmp_ote = fib.compare(leg_len, STOP_PTS, target, FRICTION, mu_star, SIGMA_1MIN,
                          o20.expected_time, o_ote.expected_time)

    thin = orderflow.effective_friction(ES, COST_BASE.commission_rt, 5.0, 120.0, 8.0)
    p30_alt = outcome_scaled(STOP_PTS, 30 * STOP_PTS, SESSION_MIN,
                             SIGMA_1MIN, 0.570).p_target
    quote, queue = orderflow.SCALES[0], orderflow.SCALES[1]
    mu0_quote = orderflow.required_instant_drift(FRICTION, quote.half_life_min,
                                                 o20.expected_time)
    mu0_queue = orderflow.required_instant_drift(FRICTION, queue.half_life_min,
                                                 o20.expected_time)
    cvd_null = orderflow.p_sign_divergence(0.80)

    return {
        "adv_bn": num(adv / 1e9, 0),
        "gex_req_bn": num(gex_req / 1e9, 0),
        "gex_req_adv": num(100 * abs(gex_req) / adv, 0),
        "hurst_alt": num(0.570, 3),
        "ptp30_alt": num(100 * p30_alt, 2),
        "stop_sigma_poc": num(prof.effective_stop_sigma(prof.poc, STOP_PTS, SIGMA_1MIN), 1),
        "stop_sigma_lvn": num(prof.effective_stop_sigma(lvn_worst, STOP_PTS, SIGMA_1MIN), 1),
        "pstop_poc": num(100 * prob_touch_single_barrier(STOP_PTS, sig_poc, 30.0), 0),
        "pstop_lvn": num(100 * prob_touch_single_barrier(STOP_PTS, sig_lvn, 30.0), 0),
        "vwap1_min": num(2 * norm_cdf(-1.0) * SESSION_MIN, 0),
        "vwap3_min": num(2 * norm_cdf(-3.0) * SESSION_MIN, 1),
        "daily_bias": num(dow.required_daily_bias(FRICTION, o20.expected_time,
                                                  SESSION_MIN), 2),
        "daily_bias_pct": num(100 * dow.required_daily_bias(
            FRICTION, o20.expected_time, SESSION_MIN) / INDEX_LEVEL, 3),
        "fill_618": num(100 * fib.p_retrace_null(fib.OTE_LOW), 1),
        "fill_786": num(100 * fib.p_retrace_null(0.786), 1),
        "mu_crit_ote": num(cmp_ote.critical_drift * 60.0, 2),
        "mu_star_h": num(mu_star * 60.0, 3),
        "half_tick_pts": num(fib.slippage_saving(0.5, ES.tick_value, ES.point_value), 3),
        "mu0_quote": num(mu0_quote, 2),
        "mu0_quote_sigma": num(mu0_quote / SIGMA_1MIN, 1),
        "mu0_queue": num(mu0_queue, 2),
        "auc_max": num(orderflow.lpr_auc(200.0, 1.0, 4.0, 0.5), 2),
        "dprime_req": num(orderflow.required_separation_for_auc(0.90), 2),
        "friction_thin": num(thin, 2),
        "cvd_div": num(100 * cvd_null, 0),
        "cvd_n": num(orderflow.trades_to_detect_excess(0.02, cvd_null), 0),
    }


def build() -> str:
    text = TEMPLATE.read_text(encoding="utf-8")

    text = text.replace("{{TOKENS_LIGHT}}", FIGURE_TOKENS_LIGHT.rstrip("\n") + "\n")
    text = text.replace("{{TOKENS_DARK}}", FIGURE_TOKENS_DARK.rstrip("\n") + "\n")
    text = text.replace("{{FIGURE_CSS}}", FIGURE_CSS.strip("\n"))

    for key, val in values().items():
        text = text.replace("{{" + key + "}}", val)

    tables = {**all_tables(), **lexicon.all_tables(), **quant.all_tables()}
    counter = {"n": 0}

    def sub_table(m: re.Match) -> str:
        counter["n"] += 1
        key = m.group(1)
        if key not in tables:
            raise KeyError(f"table inconnue : {key}")
        return tables[key].to_html(counter["n"])

    text = re.sub(r"\{\{TABLE:([a-z_]+)\}\}", sub_table, text)

    figures = {**render_all(), **render_terminal_figures(),
               **render_quant_figures()}
    fig_counter = {"n": 0}

    def sub_figure(m: re.Match) -> str:
        fig_counter["n"] += 1
        key, caption = m.group(1), m.group(2).strip()
        if key not in figures:
            raise KeyError(f"figure inconnue : {key}")
        return figure_html(figures[key], fig_counter["n"], caption)

    text = re.sub(r"\{\{FIGURE:([a-z_]+)\|(.+?)\}\}", sub_figure, text, flags=re.S)

    leftovers = re.findall(r"\{\{[^}]+\}\}", text)
    if leftovers:
        raise KeyError(f"balises non résolues : {sorted(set(leftovers))}")
    return text


def main() -> None:
    OUTPUT.write_text(build(), encoding="utf-8")
    print(f"écrit : {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size:,} octets)")


if __name__ == "__main__":
    main()
