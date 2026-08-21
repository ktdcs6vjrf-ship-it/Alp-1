"""Construction du document ALP-2 à partir de son gabarit.

Même dispositif que `alp1.paper` : la prose vit dans
`docs/alp2-paper.template.html`, les chiffres sont injectés par le noyau, et
la construction échoue si une balise reste non résolue. Un chiffre du texte et
le point correspondant d'une figure ne peuvent donc pas diverger.

Balises reconnues :

    {{nom}}                    valeur scalaire
    {{TABLE:clé}}              table, numérotée dans l'ordre d'apparition
    {{FIGURE:clé|légende}}     figure, numérotée dans l'ordre d'apparition
"""

from __future__ import annotations

import math
import re
from pathlib import Path

from .calib import BOX, CONCLUSIONS, REFERENCE, breaking_points, derive
from .costs import COST_BASE, COST_REALISTIC, ES, MES, deflated_threshold_sharpe
from .figalp2 import render_all as render_alp2_figures
from .figcss import FIGURE_CSS, FIGURE_TOKENS_DARK, FIGURE_TOKENS_LIGHT
from .friction import (
    RETAIL_ES,
    friction_law,
    implied_exit_slippage_ticks,
    max_size_for_margin,
)
from .grading import ALP1 as GRADE_ALP1, ALP2 as GRADE_ALP2
from .momentum import (
    annualised_sharpe,
    contracts_for_risk,
    edge_points_from_bps,
    mean_abs_move,
    required_drift,
    required_ir,
    sharpe_per_trade,
    trades_for_t_stat,
)
from .prereg import PROTOCOL
from .report import num
from .report2 import (
    EDGE_REF,
    FRICTION,
    FRICTION_REAL,
    HORIZON_MIN,
    SIGMA_1MIN,
    STOP_PTS,
    TRADES_PER_YEAR,
    V1_SIGMA_1MIN,
    all_tables,
    v1_outcome,
    v2_outcome,
)

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "docs" / "alp2-paper.template.html"
OUTPUT = ROOT / "docs" / "alp2-paper.html"


def values() -> dict[str, str]:
    """Toutes les valeurs scalaires citées dans la prose."""
    d = derive(REFERENCE)
    o1, o2 = v1_outcome(), v2_outcome()
    edge = edge_points_from_bps(EDGE_REF, REFERENCE.index_level)
    law = friction_law(SIGMA_1MIN, o2.p_stop, 1.0, RETAIL_ES)

    ir1 = required_ir(FRICTION, V1_SIGMA_1MIN, o1.expected_time)
    ir1r = required_ir(FRICTION_REAL, V1_SIGMA_1MIN, o1.expected_time)
    ir2 = required_ir(FRICTION, SIGMA_1MIN, o2.expected_time)
    ir2r = required_ir(FRICTION_REAL, SIGMA_1MIN, o2.expected_time)
    ir_signal = edge / (SIGMA_1MIN * math.sqrt(o2.expected_time))

    sr = sharpe_per_trade(edge, FRICTION, SIGMA_1MIN, o2.expected_time)
    sr_real = sharpe_per_trade(edge, FRICTION_REAL, SIGMA_1MIN, o2.expected_time)

    net = next(c for c in CONCLUSIONS if c.key == "net_points")
    brk = {b.axis: b for b in breaking_points(net, BOX)}

    # Échantillon à partir duquel le Sharpe attendu dépasse le seuil du meilleur
    # de trois essais sous l'hypothèse nulle.
    lo, hi = 50.0, 20000.0
    for _ in range(90):
        mid = math.sqrt(lo * hi)
        if deflated_threshold_sharpe(3, int(mid)) > sr:
            lo = mid
        else:
            hi = mid
    n_star = math.sqrt(lo * hi)

    cap50 = max_size_for_margin(SIGMA_1MIN, o2.p_stop, edge, 2.0, 0.50)
    cap99 = max_size_for_margin(SIGMA_1MIN, o2.p_stop, edge, 2.0, 0.99)

    return {
        # --- calibration ---
        "index": num(REFERENCE.index_level, 0),
        "dispersion": num(REFERENCE.session_dispersion, 0),
        "dispersion_pct": num(100 * REFERENCE.session_dispersion / REFERENCE.index_level, 2, "%"),
        "vol_annual": num(d.annual_vol_pct, 2, "%"),
        "sigma1": num(SIGMA_1MIN, 2),
        "sigma1_v1": num(V1_SIGMA_1MIN, 2),
        "session": num(REFERENCE.session_min, 0),
        "entry": num(REFERENCE.entry_min, 0),
        "horizon": num(HORIZON_MIN, 0),

        # --- géométrie ---
        "band": num(STOP_PTS, 1),
        "band_pct": num(100 * STOP_PTS / REFERENCE.index_level, 2, "%"),
        "band_mes": num(STOP_PTS * MES.point_value, 0),
        "band_es": num(STOP_PTS * ES.point_value, 0),
        "p_stop": num(100 * o2.p_stop, 0, "%"),
        "p_open": num(100 * o2.p_open, 1, "%"),
        "mean_open": num(o2.mean_open, 1),
        "expo": num(o2.expected_time, 0),
        "expo_pct": num(100 * o2.expected_time / HORIZON_MIN, 1, "%"),
        "sd_gross": num(o2.sd_gross, 1),
        "expo_v1": num(o1.expected_time, 0),
        "p_stop_v1": num(100 * o1.p_stop, 0, "%"),

        # --- friction ---
        "c_over_l": num(100 * FRICTION / STOP_PTS, 2, "%"),
        "c_over_l_real": num(100 * FRICTION_REAL / STOP_PTS, 2, "%"),
        "c_over_l_v1": num(100 * FRICTION / 3.0, 2, "%"),
        "friction_ref": num(FRICTION, 2),
        "friction_real": num(FRICTION_REAL, 2),
        "friction_mean": num(law.mean, 3),
        "friction_q90": num(law.quantile(0.90), 2),
        "friction_q99": num(law.quantile(0.99), 2),
        "slip_ticks": num(implied_exit_slippage_ticks(law), 2),
        "cap50": num(cap50, 0),
        "cap99": num(cap99, 0),

        # --- seuils et signal ---
        "ir1": num(ir1, 4),
        "ir1_real": num(ir1r, 4),
        "ir2": num(ir2, 4),
        "ir2_real": num(ir2r, 4),
        "ir_factor": num(ir1 / ir2, 2),
        "ir_signal": num(ir_signal, 3),
        "ir_margin": num(ir_signal / ir2, 1),
        "mu_star": num(60 * required_drift(FRICTION, o2.expected_time), 3),
        "edge_bps": num(EDGE_REF, 1),
        "edge_pts": num(edge, 2),
        "net_pts": num(edge - FRICTION, 2),

        # --- puissance ---
        "sr_trade": num(sr, 3),
        "sr_trade_real": num(sr_real, 3),
        "sr_annual": num(annualised_sharpe(sr, TRADES_PER_YEAR), 2),
        "n_t2": num(trades_for_t_stat(sr), 0),
        "n_star": num(n_star, 0),
        "n_min": num(PROTOCOL.min_trades, 0),
        "trades_year": num(TRADES_PER_YEAR, 0),
        "years_min": num(PROTOCOL.min_trades / TRADES_PER_YEAR, 1),

        # --- ruptures ---
        "brk_friction": num(brk["friction"].value, 2),
        "brk_friction_factor": num(brk["friction"].factor, 2),
        "brk_edge": num(brk["edge_bps"].value, 2),

        # --- protocole ---
        "seal": PROTOCOL.seal[:16],
        "budget": num(len(PROTOCOL.configurations), 0),

        # --- notation ---
        "grade1": num(GRADE_ALP1.total(), 1),
        "grade2": num(GRADE_ALP2.total(), 1),
        "grade1_20": num(GRADE_ALP1.total() / 5, 1),
        "grade2_20": num(GRADE_ALP2.total() / 5, 1),
    }


def build() -> str:
    text = TEMPLATE.read_text(encoding="utf-8")

    text = text.replace("{{TOKENS_LIGHT}}", FIGURE_TOKENS_LIGHT.rstrip("\n") + "\n")
    text = text.replace("{{TOKENS_DARK}}", FIGURE_TOKENS_DARK.rstrip("\n") + "\n")
    text = text.replace("{{FIGURE_CSS}}", FIGURE_CSS.strip("\n"))

    for key, val in values().items():
        text = text.replace("{{" + key + "}}", val)

    tables = all_tables()
    counter = {"n": 0}

    def sub_table(m: re.Match) -> str:
        counter["n"] += 1
        key = m.group(1)
        if key not in tables:
            raise KeyError(f"table inconnue : {key}")
        return tables[key].to_html(counter["n"])

    text = re.sub(r"\{\{TABLE:([a-z0-9_]+)\}\}", sub_table, text)

    figures = render_alp2_figures()
    fig_counter = {"n": 0}

    def sub_figure(m: re.Match) -> str:
        fig_counter["n"] += 1
        key, caption = m.group(1), m.group(2).strip()
        if key not in figures:
            raise KeyError(f"figure inconnue : {key}")
        return (
            '    <figure class="plate">\n'
            f'      <figcaption><span class="lab">Figure {fig_counter["n"]}</span>'
            f' — {caption}</figcaption>\n'
            f'      <div class="scroll">{figures[key]}</div>\n'
            '    </figure>'
        )

    text = re.sub(r"\{\{FIGURE:([a-z0-9_]+)\|(.+?)\}\}", sub_figure, text, flags=re.S)

    leftovers = re.findall(r"\{\{[^}]+\}\}", text)
    if leftovers:
        raise KeyError(f"balises non résolues : {sorted(set(leftovers))}")
    return text


def main() -> None:
    OUTPUT.write_text(build(), encoding="utf-8")
    print(f"écrit : {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size:,} octets)")


if __name__ == "__main__":
    main()
