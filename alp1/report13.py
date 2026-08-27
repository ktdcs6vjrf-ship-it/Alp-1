"""Ce que les chapitres de risque deviennent sous une dérive déclarée.

Les chapitres de risque du document nº 1 — Sharpe, Kelly, ruine de Lundberg —
tournent sous `reference_drift()`, qui vaut deux fois le seuil de rentabilité.
Cette table refait les mêmes calculs sous une dérive **déclarée**, à la
géométrie de l'opérateur puis à la géométrie optimale.

Le résultat n'est pas celui qu'on attendrait. Corriger la circularité ne
dégrade pas les chiffres : elle les déplace. À dérive plausible et géométrie
corrigée, chaque grandeur de risque est **meilleure** que dans le cas de
référence circulaire du document nº 1.
"""

from __future__ import annotations

from .costs import COST_BASE, ES, stop_points
from .drawdown import adjustment_coefficient
from .horizon import outcome_scaled
from .pathstats import law_from_outcome
from . import quant as q
from . import seuil
from .report import Table, num
from .report11 import DERIVE_TRAVAIL


def _loi(stop_pct: float, drift_per_hour: float):
    """La loi du trade sous une dérive **déclarée**, jamais dérivée de `c`."""
    a = stop_points(q.INDEX_LEVEL, stop_pct)
    o = outcome_scaled(a, q.RR_REF * a, q.SESSION_MIN, q.SIGMA_1MIN, q.HURST)
    c = COST_BASE.friction_points(ES)
    base = law_from_outcome(o, a, q.RR_REF * a, c)
    cible = (drift_per_hour / 60.0 * o.expected_time - c) / a
    return base.tilted_to_mean(cible)


def _grandeurs(stop_pct: float, drift_per_hour: float) -> list[str]:
    law = _loi(stop_pct, drift_per_hour)
    sharpe = law.mean / law.sd if law.sd else 0.0
    kelly = law.kelly_fraction()
    theta = adjustment_coefficient(law)
    return [
        num(law.mean, 4, signed=True),
        num(sharpe, 4, signed=True),
        num(100.0 * kelly, 2) + " %",
        num(theta, 4),
    ]


def table_risque() -> Table:
    """Les grandeurs de risque, avant et après la correction."""
    ref_h = q.reference_drift() * 60.0
    opt = seuil.best(DERIVE_TRAVAIL)
    rows = [
        ["Document nº 1 — µ = " + num(q.DRIFT_MULTIPLE, 0) + "µ*, stop "
         + num(0.010, 3) + " %", num(ref_h, 2)] + _grandeurs(0.010, ref_h),
        ["Dérive déclarée, stop " + num(0.010, 3) + " %",
         num(DERIVE_TRAVAIL, 2)] + _grandeurs(0.010, DERIVE_TRAVAIL),
        ["Dérive déclarée, stop " + num(opt.stop_pct, 3) + " % optimal",
         num(DERIVE_TRAVAIL, 2)] + _grandeurs(opt.stop_pct, DERIVE_TRAVAIL),
    ]
    return Table(
        "risque",
        "Les grandeurs de risque du document nº 1, refaites sous une dérive "
        "déclarée plutôt que dérivée de la friction.",
        ["Cas", "µ (pt/h)", "E[R]", "Sharpe/trade", "Kelly f*", "θ* Lundberg"],
        rows,
        wrap_cols=[0],
        wide=True,
        rules_after=[1],
        note="La première ligne est le cas de référence du document nº 1, et "
             "son espérance vaut exactement le ratio de friction — c'est "
             "mécanique : si µ = 2µ*, alors µ·E[τ] = 2c et E[R] = c/a. **Le "
             "chiffre annoncé ne contient aucune information sur le marché ; "
             "il ne contient que la friction.** La deuxième ligne montre ce "
             "que devient la même géométrie sous une dérive plausible : "
             "l'espérance est négative, Kelly vaut zéro, et il n'y a rien à "
             "dimensionner. La troisième corrige la géométrie et non "
             "l'hypothèse : chaque grandeur y dépasse celle de la première "
             "ligne, à une dérive cinq fois plus faible.")


TABLES = (table_risque,)


def all_tables() -> dict[str, Table]:
    return {fn().key: fn() for fn in TABLES}


def values() -> dict[str, str]:
    ref_h = q.reference_drift() * 60.0
    opt = seuil.best(DERIVE_TRAVAIL)
    a = stop_points(q.INDEX_LEVEL, 0.010)
    ref = _loi(0.010, ref_h)
    bon = _loi(opt.stop_pct, DERIVE_TRAVAIL)
    return {
        "r_cl": num(COST_BASE.friction_points(ES) / a, 3),
        "r_er_ref": num(ref.mean, 3, signed=True),
        "r_sharpe_ref": num(ref.mean / ref.sd, 4, signed=True),
        "r_kelly_ref": num(100.0 * ref.kelly_fraction(), 2),
        "r_sharpe_opt": num(bon.mean / bon.sd, 4, signed=True),
        "r_kelly_opt": num(100.0 * bon.kelly_fraction(), 2),
        "r_theta_ref": num(adjustment_coefficient(ref), 4),
        "r_theta_opt": num(adjustment_coefficient(bon), 4),
    }


def main() -> None:
    t = table_risque()
    print(t.caption)
    print(t.to_text())
    print()
    for k, v in values().items():
        print(f"  {k:16} {v}")
