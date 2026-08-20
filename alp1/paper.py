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

from .barriers import prob_touch_single_barrier
from .costs import COST_BASE, COST_REALISTIC, ES
from .figcss import FIGURE_CSS, FIGURE_TOKENS_DARK, FIGURE_TOKENS_LIGHT
from .figures import render_all
from .horizon import outcome, outcome_scaled
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
    return v


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

    text = re.sub(r"\{\{TABLE:([a-z_]+)\}\}", sub_table, text)

    figures = render_all()
    fig_counter = {"n": 0}

    def sub_figure(m: re.Match) -> str:
        fig_counter["n"] += 1
        key, caption = m.group(1), m.group(2).strip()
        if key not in figures:
            raise KeyError(f"figure inconnue : {key}")
        return (
            '    <figure>\n'
            f'      <figcaption><span class="lab">Figure {fig_counter["n"]}</span> — {caption}</figcaption>\n'
            f'      <div class="scroll">{figures[key]}</div>\n'
            '    </figure>'
        )

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
