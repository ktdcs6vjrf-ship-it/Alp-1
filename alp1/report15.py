"""L'hypothèse d'edge du document nº 1, et ce qu'elle doit à la friction.

La troisième partie du document nº 1 pose une hypothèse d'edge unique,
`µ = 2 µ*`, et la déclare « explicite, sans paramètre libre ». La première
moitié de la phrase est vraie. La seconde ne l'est pas : le multiple **est**
le paramètre libre, il vaut 2 par convention, et comme `µ*` est déduit de la
friction, toute grandeur publiée sous cette hypothèse est une fonction de la
friction avant d'être une fonction du marché.

Le cas `k = 2` le montre en une ligne. L'identité de Wald donne
`E[R] = (µ·E[τ∧T] − c)/a`, donc à `µ = k µ*` :

    E[R] = (k − 1) · c / a

À `k = 2`, l'espérance publiée vaut exactement `c/a`, le ratio de friction.
**Le chiffre ne contient aucune information sur le marché ; il contient la
friction.**

Ce module ne remplace pas l'hypothèse : il la rend lisible comme paramètre.
Deux tables en sortent.

`hypothese` balaie `k` et donne, à chaque valeur, ce que la troisième partie
publierait. Elle porte le fait qui décide de la lecture du document : à la
géométrie déclarée, le seuil de rentabilité vaut 8,19 points d'indice par
heure, quand le domaine de dérive que le même document appelle plausible
plafonne à 3,2. **Le domaine plausible tout entier tombe sous le seuil**, à
`k ≤ 0,39` — c'est-à-dire que l'hypothèse de référence n'est pas seulement
haute, elle est hors du domaine où le document lui-même situe le marché.

`dependance` classe les résultats de la partie selon ce qu'ils font quand on
remplace `k = 2` par la borne haute du plausible. Le verdict de la dernière
colonne n'est pas écrit à la main : il est **calculé** par comparaison des
deux colonnes précédentes, de sorte qu'aucune ligne ne puisse annoncer une
indépendance que le calcul refuse.
"""

from __future__ import annotations

import math

from .drawdown import (adjustment_coefficient, expected_max_drawdown_drift,
                       expected_max_drawdown_null)
from .overfit import minimum_backtest_length
from .pathstats import annualise, min_track_record_length
from .stress import var_from_law, var_gaussian
from . import quant as q
from . import seuil
from .report import Table, num

#: Multiples balayés. Les deux premiers ne sont pas des choix : ce sont les
#: bornes du domaine plausible du document, converties en multiples du seuil.
#: Les suivants encadrent l'hypothèse de référence.
MULTIPLES = (1.20, 1.50, 2.00, 3.00, 5.00)


def mu_star_per_hour() -> float:
    """`µ* = c/E[τ∧T]` à la géométrie déclarée, en points d'indice par heure."""
    return 60.0 * q.FRICTION / q.geometry(q.RR_REF).expected_time


def seuil_le_plus_bas() -> float:
    """Le plus bas seuil de rentabilité de la grille de ratios du document.

    Élargir le target allonge l'exposition, donc abaisse `µ*`. La question
    est de savoir si l'élargissement suffit à faire entrer une géométrie dans
    le domaine plausible. La réponse est non, et ce nombre la porte : même au
    ratio le plus large de la grille, le seuil reste au-dessus du plafond du
    plausible.
    """
    return min(60.0 * q.FRICTION / q.geometry(rr).expected_time
               for rr in q.RR_GRID)


def multiple_of(drift_per_hour: float) -> float:
    """Le multiple `k` correspondant à une dérive déclarée en points par heure."""
    return drift_per_hour / mu_star_per_hour()


def _ans(trades: float) -> str:
    return "∞" if trades == math.inf else num(trades / q.TRADES_PER_YEAR, 2)


def _ligne(k: float, etiquette: str) -> list[str]:
    law = q.law_at_multiple(k)
    sr = law.sharpe_per_trade
    mtrl = min_track_record_length(sr, 0.0, law.skewness, law.excess_kurtosis)
    mbtl = minimum_backtest_length(sr, q.N_TRIALS_REF)
    return [
        etiquette,
        num(k, 2),
        num(k * mu_star_per_hour(), 2),
        num(law.mean, 4, signed=True),
        num(annualise(sr, q.TRADES_PER_YEAR), 2, signed=True),
        _ans(mtrl),
        _ans(mbtl),
        num(100.0 * law.kelly_fraction(), 2) + " %",
    ]


def table_hypothese() -> Table:
    """Ce que le multiple décide, et où tombe le domaine plausible."""
    bas, haut = seuil.PLAUSIBLE_DRIFT_PER_HOUR
    rows = [
        _ligne(multiple_of(bas), "Borne basse du plausible"),
        _ligne(multiple_of(haut), "Borne haute du plausible"),
        _ligne(1.0, "Seuil de rentabilité µ*"),
    ]
    for k in MULTIPLES:
        nom = ("**Hypothèse du document** — µ = 2 µ*" if k == q.DRIFT_MULTIPLE
               else "µ = " + num(k, 2) + " µ*")
        rows.append(_ligne(k, nom))
    return Table(
        "hypothese",
        "Ce que le multiple de dérive décide, et où tombe le domaine que le "
        "document appelle plausible",
        ["Dérive supposée", "k", "µ (pt/h)", "E[R] (R)", "Sharpe an.",
         "ŜR > 0 (ans)", "après " + num(q.N_TRIALS_REF, 0) + " essais (ans)",
         "Kelly f*"],
        rows,
        wrap_cols=[0],
        wide=True,
        rules_after=[2, 3],
        note="L'espérance de la quatrième colonne vaut exactement "
             "`(k − 1)·c/a` : elle est **affine en k et nulle au seuil**, ce "
             "qui se vérifie ligne à ligne. À l'hypothèse du document, "
             "`k = 2`, elle vaut donc `c/a` — le ratio de friction, et rien "
             "d'autre. Les trois premières lignes portent le fait qui "
             "gouverne la lecture de toute la partie : le domaine plausible "
             "plafonne à `k` = " + num(multiple_of(haut), 2) + ", donc **sous "
             "le seuil de rentabilité**. Aucune dérive que ce document juge "
             "plausible ne rend cette géométrie profitable, et les deux "
             "colonnes de délai y valent l'infini — non parce que "
             "l'échantillon manque, mais parce qu'il n'y a rien à établir.")


def _quantites(k: float) -> dict[str, str]:
    """Les grandeurs publiées par la troisième partie, à un multiple donné."""
    law = q.law_at_multiple(k)
    nul = q.null_law()
    n = int(q.TRADES_PER_YEAR)
    sr = law.sharpe_per_trade
    mtrl = min_track_record_length(sr, 0.0, law.skewness, law.excess_kurtosis)
    mbtl = minimum_backtest_length(sr, q.N_TRIALS_REF)
    return {
        "Espérance sans dérive, −c/L": num(nul.mean, 4, signed=True) + " R",
        "Drawdown maximal espéré sans dérive": num(
            expected_max_drawdown_null(nul.sd, n), 0) + " R",
        "Probabilité de surajustement (CSCV)": num(
            100.0 * q.cscv_null().pbo, 1) + " %",
        "Rapport Sortino/Sharpe": num(law.sd / law.downside_deviation(), 2),
        "VaR gaussienne / VaR exacte, à 99 %": num(
            var_gaussian(law.mean, law.sd, 0.99) / var_from_law(law, 0.99), 2),
        "Espérance par trade": num(law.mean, 4, signed=True) + " R",
        "Sharpe annualisé": num(annualise(sr, q.TRADES_PER_YEAR), 2, signed=True),
        "Années pour affirmer ŜR > 0": _ans(mtrl),
        "… après " + num(q.N_TRIALS_REF, 0) + " configurations essayées": _ans(mbtl),
        "Fraction de Kelly": num(100.0 * law.kelly_fraction(), 2) + " %",
        "Coefficient de Lundberg θ*": num(adjustment_coefficient(law), 4),
        "Gain annuel espéré": num(n * law.mean, 0, signed=True) + " R",
        "Drawdown maximal espéré de l'année": num(
            expected_max_drawdown_drift(law, n), 0) + " R",
    }


def _verdict(a: str, b: str) -> str:
    """Le statut d'une ligne, déduit des deux colonnes et jamais écrit à la main."""
    if a == b:
        return "indépendant"
    if "∞" in (a, b):
        return "sans terme fini"
    if a.startswith("−") != b.startswith("−"):
        return "s'inverse"
    return "dégradé"


def _audit() -> list[list[str]]:
    """Les lignes de la table de dépendance, les indépendantes en tête.

    L'ordre n'est pas écrit à la main : il est le résultat du calcul, de
    sorte qu'une grandeur qui cesserait d'être indépendante changerait de
    place au lieu de rester sous un intertitre devenu faux.
    """
    haut = seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]
    ref = _quantites(q.DRIFT_MULTIPLE)
    pla = _quantites(multiple_of(haut))
    rows = [[nom, ref[nom], pla[nom], _verdict(ref[nom], pla[nom])]
            for nom in ref]
    rows.sort(key=lambda r: r[3] != "indépendant")
    return rows


def table_dependance() -> Table:
    """Ce qui tombe avec l'hypothèse, et ce qui n'en dépend pas."""
    rows = _audit()
    libre = sum(1 for r in rows if r[3] == "indépendant")
    porte = len(rows) - libre
    inverse = sum(1 for r in rows if r[3] == "s'inverse")
    infini = sum(1 for r in rows if r[3] == "sans terme fini")
    sd_dd = next(r for r in rows if r[0] == "Rapport Sortino/Sharpe")
    ecart = (float(sd_dd[1].replace(",", "."))
             / float(sd_dd[2].replace(",", ".")) - 1.0)
    return Table(
        "dependance",
        "Les résultats de la troisième partie, selon qu'ils portent "
        "l'hypothèse d'edge ou qu'ils s'en passent",
        ["Grandeur publiée", "à µ = 2 µ*",
         "à la borne haute du plausible", "Statut"],
        rows,
        wrap_cols=[0],
        wide=True,
        rules_after=[libre],
        note="La dernière colonne est **calculée** par comparaison des deux "
             "précédentes, et l'ordre des lignes en découle : aucune ne peut "
             "annoncer une indépendance que le calcul refuse, ni rester au "
             "-dessus du trait si elle cesse d'y avoir droit. Les "
             + num(libre, 0) + " premières ne bougent pas — elles viennent "
             "de la loi nulle, d'une matrice de performances synthétique ou "
             "de la géométrie seule, et le théorème d'invariance les tient. "
             "Les " + num(porte, 0) + " suivantes portent l'hypothèse : "
             + num(inverse, 0) + " changent de signe et " + num(infini, 0)
             + " perdent tout terme fini. Le rapport Sortino/Sharpe est le "
             "cas instructif, et c'est lui qui a coûté une phrase au corps "
             "du document : il se déplace de " + num(100.0 * ecart, 0)
             + " % entre les deux colonnes, alors qu'il y était donné pour "
             "insensible au signal. Le placement des barrières fixe bien "
             "l'ordre de grandeur du facteur ; son niveau, lui, se lit sur "
             "le signal."
    )


TABLES = (table_hypothese, table_dependance)


def all_tables() -> dict[str, Table]:
    return {fn().key: fn() for fn in TABLES}


def values() -> dict[str, str]:
    bas, haut = seuil.PLAUSIBLE_DRIFT_PER_HOUR
    k_haut = multiple_of(haut)
    ref = q.law_at_multiple(q.DRIFT_MULTIPLE)
    pla = q.law_at_multiple(k_haut)
    sr_pla = pla.sharpe_per_trade
    return {
        "h_mu_star": num(mu_star_per_hour(), 2),
        "h_mu_ref": num(q.DRIFT_MULTIPLE * mu_star_per_hour(), 2),
        "h_plausible_bas": num(bas, 1),
        "h_plausible_haut": num(haut, 1),
        "h_k_haut": num(k_haut, 2),
        "h_facteur": num(q.DRIFT_MULTIPLE * mu_star_per_hour() / haut, 1),
        "h_friction_ratio": num(q.FRICTION / q.STOP_PTS, 3),
        "h_rr_large": "1:" + num(max(q.RR_GRID), 0),
        "h_mu_star_large": num(seuil_le_plus_bas(), 2),
        "h_er_ref": num(ref.mean, 4, signed=True),
        "h_er_plausible": num(pla.mean, 4, signed=True),
        "h_sharpe_plausible": num(annualise(sr_pla, q.TRADES_PER_YEAR), 2,
                                  signed=True),
        "h_sd_dd_ref": num(ref.sd / ref.downside_deviation(), 2),
        "h_sd_dd_plausible": num(pla.sd / pla.downside_deviation(), 2),
        "h_n_total": num(len(_audit()), 0),
        "h_n_libre": num(sum(1 for r in _audit() if r[3] == "indépendant"), 0),
        "h_n_porte": num(sum(1 for r in _audit() if r[3] != "indépendant"), 0),
        "h_n_inverse": num(sum(1 for r in _audit() if r[3] == "s'inverse"), 0),
    }


def main() -> None:
    for fn in TABLES:
        t = fn()
        print(t.caption)
        print(t.to_text())
        print()
    for k, v in values().items():
        print(f"  {k:20} {v}")
