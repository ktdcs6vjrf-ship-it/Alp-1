"""Tables et valeurs du protocole à horizon borné.

Une seule question organise cette partie du document : *combien de temps faut-il
pour que le protocole réponde ?* Le document précédent y répondait sur le
dispositif le plus naïf, et la réponse — dix à vingt-cinq années — était exacte
pour ce dispositif et fausse comme propriété de la stratégie.

Le module rassemble les deux moitiés de la réponse corrigée. `alp1.power`
calcule ce qu'un plan bien construit exige, en forme fermée : frontières
séquentielles, information par date, dérive minimale détectable.
`alp1.mcprotocol` mesure ce qu'il obtient réellement, en rejouant la procédure
entière sur un marché simulé qui viole toutes les hypothèses dont la forme
fermée est issue. Les tables ci-dessous mettent systématiquement les deux
colonnes côte à côte : une prévision qui ne serait pas confrontée à sa
simulation ne vaudrait pas mieux qu'un backtest.
"""

from __future__ import annotations

import math

from . import mcprotocol as mcp
from . import power as pw
from .decay import decay_rate, runways
from .report import Table, num
from .report3 import ASOF_YEAR, year

EDGE_BPS = mcp.EDGE_BPS


def pct(value: float, nd: int = 1) -> str:
    return num(100.0 * value, nd, "%")


# --- Le plan séquentiel -----------------------------------------------------


def table_plan() -> Table:
    plan = pw.boundaries()
    rows = []
    for k, t in enumerate(plan.fractions):
        rows.append([
            f"Examen {k + 1}",
            num(t, 2),
            num(plan.efficacy[k], 3),
            num(plan.futility[k], 3) if k < len(plan.fractions) - 1 else "—",
            pct(plan.stop_probs_h0[k], 1),
            pct(plan.stop_probs_h1[k], 1),
        ])
    return Table(
        "power_plan",
        "Le plan séquentiel : quatre examens jalonnés en information",
        ["Examen", "Fraction d'information", "Seuil de rejet",
         "Seuil d'abandon", "P(rejet) sous H₀", "P(rejet) sous H₁"],
        rows,
        note=("Frontières de la fonction de dépense d'O'Brien-Fleming, au "
              "niveau unilatéral " + pct(pw.ALPHA, 0) + " et à la puissance "
              + pct(pw.POWER, 0) + ". Le premier examen exige "
              + num(plan.efficacy[0], 2) + " écarts-types : presque rien n'est "
              "dépensé tôt, ce qui laisse le seuil final à "
              + num(plan.efficacy[-1], 3) + " au lieu de "
              + num(1.645, 3) + " pour une décision unique. Le prix de ce "
              "droit de regard est une information maximale majorée de "
              + pct(plan.inflation - 1.0, 1) + " ; le gain est une durée "
              "espérée de " + pct(plan.expected_fraction_h1, 0) + " de "
              "l'échantillon complet sous H₁ et de "
              + pct(plan.expected_fraction_h0, 0) + " sous H₀. La borne "
              "d'abandon est déclarée non contraignante : la franchir "
              "autorise à arrêter, n'y oblige pas, et le niveau du test reste "
              "valide dans les deux cas."),
        wide=True,
    )


# --- Le décompte des leviers ------------------------------------------------


def table_ledger() -> Table:
    sr = _sharpe_trade()
    rows = []
    for lev in pw.ledger(sr):
        rows.append([
            lev.name,
            "—" if lev.factor == 1.0 else "×" + num(lev.factor, 3),
            num(lev.years_after, 2, "ans"),
            lev.assumption,
        ])
    return Table(
        "power_ledger",
        "Du dispositif naïf au dispositif borné, un levier à la fois",
        ["Levier", "Facteur", "Durée du verdict", "Ce qu'il exige en échange"],
        rows,
        note=("Sous l'hypothèse de dérive du document, inchangée : "
              + num(EDGE_BPS, 2) + " points de base captés par trade. Aucun "
              "levier ne relève l'edge supposé ; tous portent sur la manière "
              "de le mesurer. L'ordre est celui du coût en hypothèses, du "
              "plus gratuit au plus cher : un lecteur qui refuse le dernier "
              "levier lit la durée à l'avant-dernière ligne, et ainsi de "
              "suite."),
        wrap_cols=[0, 3],
        wide=True,
    )


def _sharpe_trade() -> float:
    """Sharpe par trade sous l'hypothèse empruntée, sur le marché simulé."""
    st = mcp.pool_statistics(0.0)
    edge = EDGE_BPS * 1e-4 * mcp.INDEX_LEVEL
    return (edge - mcp.friction()) / st["sd"]


# --- Ce que l'horizon décide -----------------------------------------------


def _hypotheses() -> list[tuple[str, float]]:
    """Les dérives dont le document a besoin, en points de base captés."""
    mde = mcp.bps_of_net_drift(mcp.design_drift())
    return [
        ("Dérive empruntée, sans décote", EDGE_BPS),
        ("Décote de 25 %", 0.75 * EDGE_BPS),
        ("Dérive dimensionnante du protocole", mde),
        ("Décote documentée, datée de 2021", 2.52),
        ("Décote documentée, datée de 2018", 1.50),
    ]


def table_horizon() -> Table:
    st = mcp.pool_statistics(0.0)
    sd, c = st["sd"], mcp.friction()
    plan = pw.boundaries()
    cap = pw.HORIZON_SESSIONS / pw.SESSIONS_PER_YEAR
    rows = []
    for label, bps in _hypotheses():
        net = bps * 1e-4 * mcp.INDEX_LEVEL - c
        sr = net / sd
        h = pw.horizon(pw.DESIGN, sr, plan=plan, cap_years=cap)
        naive = pw.NAIVE.years_for(pw.fixed_sample(sr, n_tests=3))
        rows.append([
            label,
            num(bps, 2, "pdb"),
            num(net, 2, "pt"),
            num(naive, 1, "ans") if naive < 1e3 else "∞",
            num(h.years_max, 2, "ans") if h.years_max < 1e3 else "∞",
            "oui" if h.decidable else "non",
        ])
    return Table(
        "power_horizon",
        "Ce que cinq années tranchent, et ce qu'elles ne tranchent pas",
        ["Hypothèse de dérive captée", "Dérive", "Net par trade",
         "Dispositif naïf", "Dispositif borné", "Décidable en 5 ans"],
        rows,
        note=("La colonne « dispositif naïf » est celle du document "
              "précédent : un marché, une entrée par séance, seuil corrigé de "
              "Bonferroni sur trois configurations, décision unique. La "
              "colonne « dispositif borné » est l'information maximale du "
              "plan séquentiel, convertie en années à la cadence du panel. La "
              "dernière ligne est le résultat inconfortable, et il est "
              "énoncé plutôt que contourné : à la décote documentée en "
              "moyenne sur les anomalies publiées, la dérive tombe sous ce "
              "que n'importe quel horizon réalisable peut distinguer de zéro."),
        wrap_cols=[0],
        wide=True,
    )


def table_mde() -> Table:
    st = mcp.pool_statistics(0.0)
    sd, c = st["sd"], mcp.friction()
    tau = st["exposure"]
    rows = []
    for years in (1.0, 2.0, 3.0, 4.0, 5.0):
        panel = pw.minimum_detectable_edge(pw.DESIGN, years, sd, tau, c,
                                           mcp.INDEX_LEVEL)
        solo = pw.minimum_detectable_edge(pw.SOLO, years, sd, tau, c,
                                          mcp.INDEX_LEVEL)
        rows.append([
            num(years, 0, "an" if years == 1 else "ans"),
            num(panel["effective_trades"], 0),
            num(panel["existence_bps"], 2, "pdb"),
            num(panel["viability_bps"], 2, "pdb"),
            num(solo["viability_bps"], 2, "pdb"),
        ])
    return Table(
        "power_mde",
        "Dérive minimale détectable, par horizon et par largeur de panel",
        ["Horizon", "Trades effectifs", "Existence (µ ≠ 0)",
         "Viabilité (µ &gt; µ*)", "Viabilité, un seul marché"],
        rows,
        note=("Deux seuils, deux questions. L'<em>existence</em> demande si la "
              "dérive captée est non nulle et ignore la friction, qui est une "
              "constante observée au journal. La <em>viabilité</em> demande si la "
              "dérive nette est positive et supporte la friction en entier : "
              "elle est toujours plus exigeante, et c'est elle qui décide "
              "d'engager du capital. Ce tableau est ce qui rend un échec du "
              "protocole informatif : ne pas rejeter à cinq années exclut, à "
              + pct(pw.POWER, 0) + " de puissance, toute dérive supérieure à "
              "la valeur de la dernière ligne."),
    )


# --- Ce que la simulation mesure -------------------------------------------


def table_operating() -> Table:
    ref = round(mcp.reference_multiple(), 3)
    rows = []
    for mult in mcp.CURVE + (ref,):
        op = mcp.operating_point(mcp.exact_pool(mult), mult)
        bps = mcp.bps_of_net_drift(mult * mcp.design_drift())
        label = num(mult, 2) + " · θ₁"
        if mult == 0.0:
            label += " (hypothèse nulle)"
        elif mult == ref:
            label += " (hypothèse empruntée)"
        rows.append([
            label,
            num(bps, 2, "pdb"),
            num(op.reject, 3) + " ± " + num(op.standard_error, 3),
            num(op.futile, 3),
            num(op.exhausted, 3),
            num(op.median_years, 2, "ans"),
            num(op.q90_years, 2, "ans"),
        ])
    size = rows[0][2]
    return Table(
        "power_operating",
        "Taille, puissance et durée du protocole, mesurées sur la procédure entière",
        ["Dérive imposée", "Équivalent capté", "Rejet", "Abandon",
         "Horizon épuisé", "Durée médiane", "Durée au décile 9"],
        rows,
        note=("Chaque ligne est une re-simulation complète du marché sous la "
              "dérive indiquée, suivie de "
              + num(mcp.REPLICATES, 0) + " exécutions du protocole. La "
              "première ligne est le contrôle qui compte : sous l'hypothèse "
              "nulle, le protocole rejette " + size + " pour un niveau "
              "nominal de " + num(pw.ALPHA, 2) + ". La puissance à θ₁ vaut "
              + rows[3][2] + " pour une cible de " + num(pw.POWER, 2) + ". "
              "Aucun réglage n'a été choisi au vu de ces deux nombres : "
              "c'est leur coïncidence avec les valeurs nominales qui atteste "
              "que le plan fait ce qu'il annonce."),
        rules_after=[len(rows) - 1],
        wide=True,
    )


def table_rho() -> Table:
    rows = []
    for r in mcp.rho_sensitivity():
        rows.append([
            num(r["rho_within"], 2),
            num(r["design_effect"], 2),
            num(r["effective_trades"], 2),
            num(r["size"], 3) + " ± " + num(r["standard_error"], 3),
            num(r["power"], 3),
            num(r["median_years"], 2, "ans"),
        ])
    return Table(
        "power_rho",
        "Ce que la corrélation du panel change — et ce qu'elle ne change pas",
        ["Corrélation intra-fuseau", "Effet de grappe",
         "Trades effectifs par date", "Taille", "Puissance à θ₁",
         "Durée médiane"],
        rows,
        note=("La corrélation entre marchés est la seule hypothèse de "
              "calibration dont on pourrait craindre qu'elle porte la "
              "validité du protocole. Elle ne la porte pas : la taille reste "
              "au niveau nominal sur toute la plage, du simple au presque "
              "parfait. Ce qui bouge est la <strong>durée</strong>, de "
              + num(mcp.rho_sensitivity()[0]["median_years"], 2) + " à "
              + num(mcp.rho_sensitivity()[-1]["median_years"], 2) + " années. "
              "C'est la conséquence directe du jalonnement en information : "
              "les examens tombent quand l'information est là, pas à une date "
              "convenue, et une corrélation plus forte retarde les examens "
              "sans déplacer leurs seuils."),
        wide=True,
    )


def table_panel() -> Table:
    rows = []
    for r in mcp.panel_width():
        rows.append([
            num(r["markets"], 0),
            num(r["effective_trades"], 2),
            num(r["size"], 3),
            num(r["power"], 3),
            num(r["exhausted"], 3),
            num(r["power_borrowed"], 3),
            num(r["median_years_borrowed"], 2, "ans"),
        ])
    return Table(
        "power_panel",
        "Ce que la largeur du panel achète, hypothèse par hypothèse",
        ["Marchés", "Trades effectifs par date", "Taille", "Puissance à θ₁",
         "Horizon épuisé", "Puissance à l'hypothèse empruntée",
         "Durée médiane"],
        rows,
        note=("Le panel n'est pas un ornement. À information maximale scellée, "
              "un marché unique n'atteint pas son dernier examen dans "
              "l'horizon "
              + pct(mcp.panel_width()[0]["exhausted"], 0) + " du temps sous θ₁ "
              "— il ne conclut pas, faute de temps de marché, et non faute de "
              "dérive. Trois contrats suffisent à trancher l'hypothèse "
              "empruntée ; les cinq sont ce qui rend décidable sa version "
              "décotée."),
        wrap_cols=[1, 5],
        wide=True,
    )


def table_controls() -> Table:
    mart = mcp.martingale_check()
    shift = mcp.check_shift_accuracy()
    sel = mcp.selection_contrast()
    st = mcp.pool_statistics(0.0)
    _, delta = mcp.null_pool()
    base = mcp.date_pool(0.0)
    forecast = pw.information_per_date(pw.DESIGN, st["exposure"], st["sd"])
    realised = mcp.realised_information_per_date()
    rows = [
        ["Arrêt optionnel sur le marché simulé",
         "dérive brute nulle sous martingale",
         num(mart["residual_per_min"], 5) + " ± " + num(mart["standard_error"], 5)
         + " pt/min",
         "z = " + num(mart["z"], 2, signed=True)],
        ["Recentrage de l'hypothèse nulle",
         "friction rapportée à l'exposition / résidu du vivier",
         num(-mcp.friction() / mcp.weighted_exposure(), 5) + " / "
         + num(delta + mcp.friction() / mcp.weighted_exposure(), 5) + " pt/min",
         "le premier terme est définitionnel, le second est du bruit"],
        ["Information par date", "prévue en forme fermée / mesurée",
         num(forecast, 2) + " / " + num(realised, 2),
         "écart " + pct(realised / forecast - 1.0, 1, )],
        ["Exposition réalisée", "simulée / forme fermée",
         num(st["exposure"], 1) + " / " + num(mcp.geometry()[1].expected_time, 1)
         + " min",
         "écart " + pct(st["exposure"] / mcp.geometry()[1].expected_time - 1.0, 1)],
        ["Corrélation de date réalisée", "structure de blocs du panel",
         num(base.realised_correlation, 3),
         "effet de grappe " + num(base.design_effect, 2)],
        ["Dérive ajoutée contre dérive simulée", "puissance, deux routes",
         num(shift["exact"], 3) + " / " + num(shift["approx"], 3),
         "z = " + num(shift["z"], 2, signed=True)],
        ["Coût de la sélection", "ordre scellé / meilleur de trois",
         num(sel["sealed"], 3) + " / " + num(sel["best_of_three"], 3),
         "×" + num(sel["inflation"], 1)],
    ]
    return Table(
        "power_controls",
        "Les contrôles de la simulation, et ce qu'ils autorisent à conclure",
        ["Contrôle", "Ce qui est confronté", "Valeurs", "Lecture"],
        rows,
        note=("Aucun de ces contrôles ne mesure une performance : tous "
              "mesurent si l'appareil de mesure dit la vérité. Le premier est "
              "le plus important — si le marché simulé ne retrouvait pas "
              "l'identité d'arrêt optionnel, tout ce qui suit serait sans "
              "objet. Le dernier est le seul qui porte sur une pratique "
              "plutôt que sur un calcul : à données identiques et procédure "
              "identique, lire la famille par son meilleur élément multiplie "
              "le taux d'erreur par " + num(sel["inflation"], 1) + "."),
        wrap_cols=[0, 1, 3],
        wide=True,
    )


# --- Valeurs citées dans le texte ------------------------------------------


def _decidability() -> dict[str, float]:
    """Ce que la décote fait au seuil de détectabilité, et à quel taux.

    Le seuil de rupture du document est celui de la rentabilité — la dérive
    en dessous de laquelle l'espérance nette s'annule. Il en existe un second,
    plus haut, et c'est celui-ci qui décide de la conduite de l'expérience :
    la dérive en dessous de laquelle le protocole ne peut plus **trancher**.
    Le protocole ne devient pas faux en dessous ; il devient muet, et son
    silence n'exclut alors plus rien.
    """
    mde = mcp.bps_of_net_drift(mcp.design_drift())
    rws = runways(EDGE_BPS, mde, ASOF_YEAR)
    first, last = rws[0], rws[-1]
    age = float(ASOF_YEAR - first.published)
    return {
        "mde": mde,
        "first_year": first.published,
        "last_year": last.published,
        "first_expiry": first.expiry,
        "last_expiry": last.expiry,
        "max_rate_today": math.log(EDGE_BPS / mde) / age if age > 0 else math.inf,
        "max_rate_horizon": (math.log(EDGE_BPS / mde)
                             / (age + pw.HORIZON_SESSIONS / pw.SESSIONS_PER_YEAR)),
    }


def values() -> dict[str, str]:
    plan = pw.boundaries()
    st = mcp.pool_statistics(0.0)
    base = mcp.date_pool(0.0)
    _, delta = mcp.null_pool()
    ref = round(mcp.reference_multiple(), 3)
    op0 = mcp.operating_point(mcp.exact_pool(0.0), 0.0)
    op1 = mcp.operating_point(mcp.exact_pool(1.0), 1.0)
    opr = mcp.operating_point(mcp.exact_pool(ref), ref)
    sel = mcp.selection_contrast()
    mart = mcp.martingale_check()
    shift = mcp.check_shift_accuracy()
    mde = mcp.bps_of_net_drift(mcp.design_drift())
    rho = mcp.rho_sensitivity()
    panel = mcp.panel_width()
    sr = _sharpe_trade()
    led = pw.ledger(sr)
    dec = _decidability()
    forecast = pw.information_per_date(pw.DESIGN, st["exposure"], st["sd"])

    return {
        # --- le plan ---
        "pw_alpha": num(pw.ALPHA, 2),
        "pw_alpha_pct": pct(pw.ALPHA, 0),
        "pw_power_pct": pct(pw.POWER, 0),
        "pw_looks": num(len(plan.fractions), 0),
        "pw_eff_first": num(plan.efficacy[0], 2),
        "pw_eff_last": num(plan.efficacy[-1], 3),
        "pw_fixed_z": num(1.645, 3),
        "pw_bonf_z": num(2.128, 3),
        "pw_inflation_pct": pct(plan.inflation - 1.0, 1),
        "pw_expected_h1": pct(plan.expected_fraction_h1, 0),
        "pw_expected_h0": pct(plan.expected_fraction_h0, 0),
        # --- le dispositif ---
        "pw_markets": num(len(pw.PANEL), 0),
        "pw_market_list": ", ".join(m.symbol for m in pw.PANEL),
        "pw_entries": num(st["entries_per_session"], 2),
        "pw_max_entries": num(mcp.MAX_ENTRIES, 0),
        "pw_trades_date": num(base.trades_per_date, 2),
        "pw_deff": num(base.design_effect, 2),
        "pw_eff_date": num(base.effective_trades, 2),
        "pw_rho_realised": num(base.realised_correlation, 3),
        "pw_gls": num(pw.gls_gain(), 2),
        "pw_nu": num(pw.VOL_LOG_SD, 2),
        "pw_vol_corr": num(mcp.VOL_FORECAST_CORR, 2),
        "pw_entry_min": num(mcp.ENTRY_MIN, 0),
        # --- l'horizon ---
        "pw_horizon_years": num(pw.HORIZON_SESSIONS / pw.SESSIONS_PER_YEAR, 0),
        "pw_horizon_sessions": num(pw.HORIZON_SESSIONS, 0),
        "pw_design_years": num(pw.DESIGN_SESSIONS / pw.SESSIONS_PER_YEAR, 1),
        "pw_design_sessions": num(pw.DESIGN_SESSIONS, 0),
        "pw_min_sessions": num(pw.MIN_SESSIONS_BEFORE_LOOK, 0),
        "pw_info_forecast": num(forecast, 1),
        "pw_info_realised": num(mcp.realised_information_per_date(), 1),
        "pw_info_gap": pct(mcp.realised_information_per_date() / forecast - 1.0, 1),
        # --- la dérive dimensionnante ---
        "pw_theta1": num(mcp.design_drift(), 5),
        "pw_mde_bps": num(mde, 2),
        "pw_mde_share": pct(mde / EDGE_BPS, 0),
        "pw_decay_absorbed": pct(1.0 - mde / EDGE_BPS, 0),
        "pw_ref_bps": num(EDGE_BPS, 2),
        "pw_ref_mult": num(ref, 2),
        "pw_deadline_first": year(dec["first_expiry"]),
        "pw_deadline_last": year(dec["last_expiry"]),
        "pw_decay_max_rate": num(dec["max_rate_today"], 3),
        "pw_decay_max_rate_pct": pct(dec["max_rate_today"], 1),
        "pw_decay_horizon_rate_pct": pct(dec["max_rate_horizon"], 1),
        "pw_decay_documented_pct": pct(decay_rate(), 1),
        # --- ce que la simulation mesure ---
        "pw_size": num(op0.reject, 3),
        "pw_size_se": num(op0.standard_error, 3),
        "pw_power_theta1": num(op1.reject, 3),
        "pw_power_ref": num(opr.reject, 3),
        "pw_median_h0": num(op0.median_years, 2),
        "pw_median_theta1": num(op1.median_years, 2),
        "pw_median_ref": num(opr.median_years, 2),
        "pw_q90_ref": num(opr.q90_years, 2),
        "pw_exhausted_theta1": num(op1.exhausted, 3),
        "pw_replicates": num(mcp.REPLICATES, 0),
        "pw_pool_sessions": num(mcp.POOL_SESSIONS, 0),
        "pw_pool_trades": num(st["trades"], 0),
        "pw_skew": num(st["skew"], 2, signed=True),
        "pw_kurtosis": num(st["excess_kurtosis"], 2, signed=True),
        "pw_exposure": num(st["exposure"], 1),
        "pw_exposure_closed": num(mcp.geometry()[1].expected_time, 1),
        "pw_exposure_gap": pct(1.0 - st["exposure"] / mcp.geometry()[1].expected_time, 0),
        "pw_sd_trade": num(st["sd"], 1),
        # --- contrôles ---
        "pw_martingale_z": num(mart["z"], 2, signed=True),
        "pw_recentering": num(delta, 5),
        "pw_recentering_pct": pct(abs(delta) / mcp.design_drift(), 0),
        "pw_shift_z": num(shift["z"], 2, signed=True),
        "pw_sel_sealed": num(sel["sealed"], 3),
        "pw_sel_best": num(sel["best_of_three"], 3),
        "pw_sel_ratio": num(sel["inflation"], 1),
        # --- robustesse ---
        "pw_rho_size_lo": num(min(r["size"] for r in rho), 3),
        "pw_rho_size_hi": num(max(r["size"] for r in rho), 3),
        "pw_rho_years_lo": num(rho[0]["median_years"], 2),
        "pw_rho_years_hi": num(rho[-1]["median_years"], 2),
        "pw_solo_exhausted": pct(panel[0]["exhausted_borrowed"], 0),
        "pw_solo_power_ref": num(panel[0]["power_borrowed"], 3),
        "pw_three_power_ref": num(panel[1]["power_borrowed"], 3),
        # --- le décompte ---
        "pw_naive_years": num(led[0].years_after, 1),
        "pw_bounded_years": num(led[-1].years_after, 2),
        "pw_gate_factor": num(led[1].factor, 3),
        "pw_gls_factor": num(led[2].factor, 3),
        "pw_cadence_factor": num(led[3].factor, 3),
        "pw_panel_factor": num(led[4].factor, 3),
        "pw_seq_factor": num(led[5].factor, 3),
    }


TABLES = [
    table_plan,
    table_ledger,
    table_horizon,
    table_mde,
    table_operating,
    table_rho,
    table_panel,
    table_controls,
]


def all_tables() -> dict[str, Table]:
    return {fn().key: fn() for fn in TABLES}


def main() -> None:
    for fn in TABLES:
        t = fn()
        print(f"\n### {t.caption}\n")
        print(t.to_text())
    print("\n### Valeurs\n")
    for key, val in sorted(values().items()):
        print(f"  {key:24s} {val}")


if __name__ == "__main__":
    main()
