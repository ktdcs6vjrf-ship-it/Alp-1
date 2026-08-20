"""Tables chiffrées du papier ALP-2.

Mêmes conventions que `alp1.report` : chaque table est décrite une fois sous
forme de données, puis rendue en texte ou en HTML. Les hypothèses tiennent en
trois nombres — le niveau d'indice, la dispersion d'une séance, la durée de la
séance — dont tout le reste se déduit.

Usage :
    python -m alp1.report2
"""

from __future__ import annotations

import math

from .costs import (
    COST_BASE,
    COST_OPTIMISTIC,
    COST_REALISTIC,
    ES,
    MES,
    deflated_threshold_sharpe,
)
from .grading import ALP1 as GRADE_ALP1, ALP2 as GRADE_ALP2, CRITERIA, families
from .horizon import hurst_from_dispersions, outcome_scaled
from .momentum import (
    annualised_sharpe,
    band_pct,
    contracts_for_risk,
    edge_points_from_bps,
    expectancy_r,
    mean_abs_move,
    required_drift,
    required_ir,
    sharpe_per_trade,
    sigma_from_session,
    time_exit_outcome,
    trades_for_t_stat,
)
from .report import Table, num

# --- Hypothèses -------------------------------------------------------------

INDEX_LEVEL = 6000.0
SESSION_MIN = 390.0              # 09:30 – 16:00 ET
SESSION_DISPERSION = 60.0        # 1,00 % de l'indice, soit 16 % annualisé
SIGMA_1MIN = sigma_from_session(SESSION_DISPERSION, SESSION_MIN)

ENTRY_MIN = 90.0                 # entrée de référence : 11:00 ET
HORIZON_MIN = SESSION_MIN - ENTRY_MIN
STOP_PTS = mean_abs_move(SIGMA_1MIN, ENTRY_MIN)   # la bande de bruit elle-même

FRICTION = COST_BASE.friction_points(ES)
FRICTION_REAL = COST_REALISTIC.friction_points(ES)

EDGE_BPS = (3.0, 4.5, 6.0, 8.0)  # dérive captée par trade, en points de base
EDGE_REF = 6.0                   # valeur rapportée par la réplication ES/NQ
TRADES_PER_YEAR = 200.0
RISK_PCT = 0.5

STOP_GRID = (10.0, 15.0, 20.0, STOP_PTS, 30.0, 40.0)

# Paramétrage d'ALP-1, repris tel quel pour la comparaison — y compris sa
# calibration la plus favorable (σ₁ = 1,25 et H = 0,65).
V1_STOP_PTS = 3.0
V1_SIGMA_1MIN = 1.25
V1_HURST = hurst_from_dispersions(V1_SIGMA_1MIN, SESSION_DISPERSION, SESSION_MIN)
V1_RR = 20.0


def v1_outcome():
    """Issues du trade ALP-1 de référence, sous ses propres hypothèses."""
    return outcome_scaled(V1_STOP_PTS, V1_RR * V1_STOP_PTS, SESSION_MIN,
                          V1_SIGMA_1MIN, V1_HURST)


def v2_outcome(stop: float = STOP_PTS, horizon: float = HORIZON_MIN):
    """Issues du trade ALP-2 de référence."""
    return time_exit_outcome(stop, horizon, SIGMA_1MIN)


def _edge_pts(bps: float = EDGE_REF) -> float:
    return edge_points_from_bps(bps, INDEX_LEVEL)


# --- Tables -----------------------------------------------------------------

def table_assumptions() -> Table:
    o = v2_outcome()
    rows = [
        ["Contrat", "ES / MES",
         f"{num(ES.point_value, 0)} $ et {num(MES.point_value, 0)} $ le point, "
         f"tick de {num(ES.tick_size, 2)} pt"],
        ["Niveau d'indice", num(INDEX_LEVEL, 0), "référence de conversion des pourcentages"],
        ["Dispersion de séance", num(SESSION_DISPERSION, 0, "pt"),
         f"{num(100 * SESSION_DISPERSION / INDEX_LEVEL, 2)} % de l'indice, "
         f"soit environ {num(100 * SESSION_DISPERSION / INDEX_LEVEL * math.sqrt(252), 0)} % annualisé"],
        ["Volatilité à 1 min", num(SIGMA_1MIN, 2, "pt"),
         "déduite de la ligne précédente, non posée à côté d'elle"],
        ["Séance", f"{num(SESSION_MIN, 0)} min", "09:30 – 16:00 ET"],
        ["Entrée de référence", "11:00 ET",
         f"{num(ENTRY_MIN, 0)} min après l'ouverture, {num(HORIZON_MIN, 0)} min avant la clôture"],
        ["Bande de bruit à l'entrée", num(STOP_PTS, 1, "pt"),
         f"déplacement absolu moyen depuis l'ouverture à cette heure-là, "
         f"{num(band_pct(INDEX_LEVEL, SIGMA_1MIN, ENTRY_MIN), 2)} % de l'indice"],
        ["Stop", num(STOP_PTS, 1, "pt"),
         f"la bande elle-même ; {num(STOP_PTS * MES.point_value, 0)} $ sur MES, "
         f"{num(STOP_PTS * ES.point_value, 0)} $ sur ES"],
        ["Target", "aucun",
         f"sortie au marché à la clôture ; P(stop touché avant) = {num(100 * o.p_stop, 0)} %"],
        ["Friction de référence", num(FRICTION, 2, "pt"),
         f"{num(COST_BASE.friction_usd(ES), 2)} $ par aller-retour sur ES"],
        ["Friction réaliste", num(FRICTION_REAL, 2, "pt"),
         f"{num(COST_REALISTIC.friction_usd(ES), 2)} $ — un demi-tick à l'entrée, "
         "un tick et demi à la sortie"],
    ]
    return Table(
        "assumptions",
        "Hypothèses de calcul d'ALP-2. Trois nombres sont posés — niveau d'indice, "
        "dispersion de séance, durée de séance — et tout le reste s'en déduit.",
        ["Grandeur", "Valeur", "Détail"], rows, wrap_last=True,
        note="La volatilité à une minute n'est pas un paramètre libre : elle vaut "
             "dispersion/√durée. C'est la différence de méthode avec ALP-1, où les "
             "deux quantités étaient posées séparément et leur incompatibilité "
             "absorbée par un exposant d'échelle.")


def table_grading() -> Table:
    rows = []
    rules = []
    seen_family = None
    for i, c in enumerate(CRITERIA):
        if seen_family is not None and c.family != seen_family:
            rules.append(i)
        seen_family = c.family
        rows.append([
            c.label, num(c.weight, 0),
            num(GRADE_ALP1.scores[c.key], 0), num(GRADE_ALP2.scores[c.key], 0),
            num(GRADE_ALP1.points(c.key), 1), num(GRADE_ALP2.points(c.key), 1),
        ])
    rows.append(["Total", num(100.0, 0), "—", "—",
                 num(GRADE_ALP1.total(), 1), num(GRADE_ALP2.total(), 1)])
    return Table(
        "grading",
        "La grille appliquée aux deux documents. Douze critères, poids fixés "
        "d'avance, même échelle d'ancrage de 0 à 5.",
        ["Critère", "Poids", "ALP-1", "ALP-2", "Points ALP-1", "Points ALP-2"],
        rows, rules_after=rules + [len(rows) - 1],
        note="Les trois familles pèsent 35, 35 et 30 points. Le total d'ALP-1 est "
             "porté presque entièrement par la première : un document analytique "
             "juste, reproductible, et sans contenu empirique.")


def table_family_scores() -> Table:
    rows = []
    for fam in families():
        g1, top = GRADE_ALP1.family_total(fam)
        g2, _ = GRADE_ALP2.family_total(fam)
        rows.append([fam, num(top, 0), num(g1, 1), num(g2, 1),
                     num(g2 - g1, 1, signed=True)])
    rows.append(["Total", num(100.0, 0), num(GRADE_ALP1.total(), 1),
                 num(GRADE_ALP2.total(), 1),
                 num(GRADE_ALP2.total() - GRADE_ALP1.total(), 1, signed=True)])
    return Table(
        "family_scores",
        "Note par famille de critères. L'écart ne porte pas sur la rigueur : il "
        "porte sur le contenu empirique et sur l'exploitabilité.",
        ["Famille", "Maximum", "ALP-1", "ALP-2", "Écart"], rows,
        rules_after=[len(rows) - 1],
        note="ALP-1 obtient 25,8 points sur 35 en validité interne et 9,8 sur 35 en "
             "contenu empirique. C'est le profil exact d'un théorème sans mesure : "
             "rien n'y est faux, rien n'y est établi sur le marché.")


def table_calibration() -> Table:
    rows = []
    for sigma in (1.25, 2.0, 2.5, SIGMA_1MIN):
        implied_sess = sigma * math.sqrt(SESSION_MIN)
        h = hurst_from_dispersions(sigma, SESSION_DISPERSION, SESSION_MIN)
        o = outcome_scaled(V1_STOP_PTS, V1_RR * V1_STOP_PTS, SESSION_MIN, sigma, h)
        ann = 100 * sigma * math.sqrt(SESSION_MIN * 252) / INDEX_LEVEL
        rows.append([
            num(sigma, 2), num(ann, 1, "%"), num(implied_sess, 1),
            num(h, 3), num(100 * o.p_target, 2, "%"), num(o.expected_time, 1),
        ])
    return Table(
        "calibration",
        "L'exposant d'échelle d'ALP-1 en fonction de la seule volatilité à une "
        "minute, la dispersion de séance étant maintenue à "
        f"{num(SESSION_DISPERSION, 0)} points.",
        ["σ₁ (pt)", "Vol. annualisée impliquée", "Dispersion en √t (pt)",
         "H impliqué", "P(target 1:20)", "E[τ∧T] (min)"],
        rows,
        note="La probabilité d'atteindre le target est identique sur toutes les "
             "lignes : elle ne dépend que de la dispersion totale à la clôture, que "
             "la calibration maintient constante par construction. L'exposant H ne "
             "mesure donc pas une propriété du prix, il mesure l'écart entre les "
             "deux volatilités posées. Ce qui varie réellement, c'est l'exposition — "
             "et avec elle la dérive requise, dans un rapport de un à un et demi.")


def table_geometry_compare() -> Table:
    o1 = v1_outcome()
    o2 = v2_outcome()
    edge = _edge_pts()

    def line(name, stop, exposure, sd, p_bad, cost):
        ir = required_ir(cost, SIGMA_1MIN if name.startswith("ALP-2") else V1_SIGMA_1MIN,
                         exposure)
        sr = sharpe_per_trade(
            edge, cost, SIGMA_1MIN if name.startswith("ALP-2") else V1_SIGMA_1MIN,
            exposure)
        return [
            name, num(stop, 1), num(100 * cost / stop, 2, "%"), num(exposure, 0),
            num(60 * required_drift(cost, exposure), 3), num(ir, 4),
            num(100 * p_bad, 0, "%"), num(sr, 3),
            num(annualised_sharpe(sr, TRADES_PER_YEAR), 2),
            num(trades_for_t_stat(sr), 0),
        ]

    rows = [
        line("ALP-1 · 1:20", V1_STOP_PTS, o1.expected_time, o1.sd_gross,
             o1.p_stop, FRICTION),
        line("ALP-1 · 1:20 (friction réaliste)", V1_STOP_PTS, o1.expected_time,
             o1.sd_gross, o1.p_stop, FRICTION_REAL),
        line("ALP-2 · bande, sortie à la clôture", STOP_PTS, o2.expected_time,
             o2.sd_gross, o2.p_stop, FRICTION),
        line("ALP-2 · bande (friction réaliste)", STOP_PTS, o2.expected_time,
             o2.sd_gross, o2.p_stop, FRICTION_REAL),
    ]
    return Table(
        "geometry_compare",
        "Les deux géométries devant le même critère. La colonne Sharpe suppose la "
        f"même dérive captée de {num(EDGE_REF, 1)} points de base par trade, soit "
        f"{num(_edge_pts(), 2)} points d'indice.",
        ["Géométrie", "L (pt)", "c/L", "E[τ∧T] (min)", "µ* (pt/h)", "IR*",
         "P(stop)", "SR/trade", "SR annualisé", "N pour t = 2"],
        rows, rules_after=[2],
        note="Rien dans cette table ne dépend d'une hypothèse sur la qualité du "
             "signal, sauf les trois dernières colonnes, qui supposent la même dérive "
             "dans les deux cas. Le stop large ne rend pas le signal meilleur : il "
             "abaisse le seuil que le signal doit franchir, d'un facteur cinq à neuf "
             "selon le scénario d'exécution.")


def table_stop_grid() -> Table:
    rows = []
    edge = _edge_pts()
    for stop in STOP_GRID:
        o = time_exit_outcome(stop, HORIZON_MIN, SIGMA_1MIN)
        sr = sharpe_per_trade(edge, FRICTION, SIGMA_1MIN, o.expected_time)
        rows.append([
            num(stop, 1), num(100 * stop / INDEX_LEVEL, 2, "%"),
            num(100 * o.p_stop, 0, "%"), num(o.expected_time, 0),
            num(100 * FRICTION / stop, 2, "%"),
            num(60 * required_drift(FRICTION, o.expected_time), 3),
            num(required_ir(FRICTION, SIGMA_1MIN, o.expected_time), 4),
            num(sr, 3), num(annualised_sharpe(sr, TRADES_PER_YEAR), 2),
        ])
    return Table(
        "stop_grid",
        f"Largeur de stop et seuils, entrée à 11:00 ET, {num(HORIZON_MIN, 0)} minutes "
        "avant la clôture.",
        ["Stop (pt)", "% indice", "P(stop)", "E[τ∧T] (min)", "c/L", "µ* (pt/h)",
         "IR*", "SR/trade", "SR annualisé"],
        rows, rules_after=[3],
        note="L'exposition croît avec le stop mais sature en approchant la durée "
             "restante de la séance : au-delà de la bande, on achète de moins en "
             "moins de temps de marché pour un risque qui, lui, croît "
             "proportionnellement. La ligne surlignée est la bande de bruit "
             "elle-même, seule valeur du tableau qui ne soit pas choisie.")


def table_literature() -> Table:
    rows = [
        ["Momentum intraday de marché", "Gao, Han, Li &amp; Zhou (JFE, 2018)",
         "SPY, 1993–2013",
         "Le rendement de la première demi-heure prédit celui de la dernière ; "
         "R² de 2,6 % avec la douzième demi-heure, 3,3 % les jours de forte "
         "volatilité d'ouverture", "Socle"],
        ["Généralisation et mécanisme",
         "Baltussen, Da, Lammers &amp; Martens (JFE, 2021)",
         "60+ futures, 1974–2020",
         "Le rendement du reste de la séance prédit les 30 dernières minutes, "
         "partout ; réversion les jours suivants ; mécanisme rattaché à la demande "
         "de couverture gamma", "Socle"],
        ["Mise en œuvre par bande de bruit",
         "Zarattini, Aziz &amp; Barbon (2024)", "SPY, 2007–2024",
         "19,6 % par an net de frais, Sharpe 1,33, taux de réussite d'environ 40 %, "
         "sorties à la clôture et stop suiveur sur VWAP", "Règle opératoire"],
        ["Réplication sur futures indiciels", "Réplication publique (2024)",
         "ES et NQ",
         "22,4 % par an, Sharpe 1,57, perte maximale 15 % ; environ 6 points de base "
         "par trade, 38 % de réussite, payoff 2,25", "Ordre de grandeur"],
        ["Gamma des teneurs de marché", "Dim, Eraker &amp; Vilkov (0DTE)",
         "SPX, options du jour",
         "Le gamma net des teneurs est en moyenne positif et négativement lié à la "
         "volatilité intraday future ; positif il renforce la réversion, négatif il "
         "renforce le momentum", "Conditionnement"],
        ["Dérive overnight", "Boyarchenko, Larsen &amp; Whelan (Fed NY)",
         "Futures actions, 24 h",
         "Près de la totalité de la prime de risque sur la fenêtre 2h–3h ET, environ "
         "3,7 % par an — puis proche de zéro depuis 2021", "Écarté : éteint"],
        ["Signaux OHLCV à barre unique", "Mesfin (2026)",
         "MNQ, 5 min, 2021–2025",
         "Quatorze familles de signaux, edge brut de 0,07 à 1,50 point par trade "
         "contre 2 points de friction ; aucune ne franchit le seuil",
         "Écarté : sous la friction"],
        ["Variantes à sorties optimisées", "Maróy (2025)", "SPY / futures",
         "Sharpe supérieur à 3 et plus de 50 % par an après optimisation de tous les "
         "paramètres de sortie", "Écarté : non déflaté"],
    ]
    return Table(
        "literature",
        "Les effets publics considérés, et le motif de leur retenue ou de leur rejet.",
        ["Effet", "Source", "Échantillon", "Magnitude rapportée", "Statut"],
        rows, wrap_last=False, rules_after=[5],
        note="Les trois dernières lignes sont écartées, et chacune pour une raison "
             "différente : un effet qui s'est éteint après publication, une famille "
             "de signaux que la friction annule, une performance obtenue par "
             "optimisation et donc non comparable à un seuil déflaté. Elles "
             "appartiennent au document au même titre que les autres : ce sont elles "
             "qui fixent les garde-fous de la section 9.")


def table_edge_scenarios() -> Table:
    o = v2_outcome()
    rows = []
    for bps in EDGE_BPS:
        edge = edge_points_from_bps(bps, INDEX_LEVEL)
        for cost, label in ((FRICTION, "référence"), (FRICTION_REAL, "réaliste")):
            sr = sharpe_per_trade(edge, cost, SIGMA_1MIN, o.expected_time)
            rows.append([
                num(bps, 1), label, num(edge, 2), num(edge - cost, 2),
                num(edge / cost, 1), num(sr, 3),
                num(annualised_sharpe(sr, TRADES_PER_YEAR), 2),
                num(trades_for_t_stat(sr), 0),
            ])
    return Table(
        "edge_scenarios",
        "Dérive captée par trade et conséquences, géométrie ALP-2 de référence. "
        "La ligne à 6 points de base est celle que rapporte la réplication sur "
        "futures.",
        ["Dérive (pb)", "Friction", "Points captés", "Net (pt)", "Dérive / friction",
         "SR/trade", "SR annualisé", "N pour t = 2"],
        rows, rules_after=[4],
        note="Le Sharpe annualisé calculé ici à partir de la dérive publiée tombe "
             "dans la fourchette des Sharpe publiés par les mêmes travaux, entre 1,3 "
             "et 1,6. Ce n'est pas une validation — les deux chiffres viennent de la "
             "même source — mais une vérification de cohérence : le cadre reproduit, "
             "à partir d'une seule grandeur, un résultat obtenu autrement.")


def table_sizing() -> Table:
    rows = []
    for equity in (5_000.0, 10_000.0, 25_000.0, 50_000.0, 100_000.0):
        n_mes = contracts_for_risk(equity, RISK_PCT, STOP_PTS, MES)
        n_es = contracts_for_risk(equity, RISK_PCT, STOP_PTS, ES)
        rows.append([
            num(equity, 0, "$"), num(equity * RISK_PCT / 100, 0, "$"),
            num(n_mes, 1), num(math.floor(n_mes), 0),
            num(n_es, 2),
            num(math.floor(n_mes) * STOP_PTS * MES.point_value, 0, "$"),
            num(math.floor(n_mes) * INDEX_LEVEL * MES.point_value, 0, "$"),
        ])
    return Table(
        "sizing",
        f"Dimensionnement à {num(RISK_PCT, 1)} % de risque par trade, stop de "
        f"{num(STOP_PTS, 1)} points.",
        ["Capital", "Risque visé", "MES (exact)", "MES (retenu)", "ES (exact)",
         "Risque réel", "Notionnel"],
        rows,
        note="Le stop large impose le micro-contrat en dessous d'une centaine de "
             "milliers de dollars : un ES exigerait un capital de 230 000 $ pour "
             "tenir le même pourcentage de risque. C'est une contrainte "
             "d'instrument, pas une préférence — et c'est la contrepartie directe "
             "de la friction relative divisée par sept.")


def table_deflation() -> Table:
    o = v2_outcome()
    sr = sharpe_per_trade(_edge_pts(), FRICTION, SIGMA_1MIN, o.expected_time)
    rows = []
    for n_obs in (200, 400, 1000, 2000):
        row = [num(n_obs, 0)]
        for k in (1, 3, 10, 100):
            thr = deflated_threshold_sharpe(k, n_obs) if k > 1 else 0.0
            row.append(num(thr, 3))
        row.append(num(sr, 3))
        rows.append(row)
    return Table(
        "deflation",
        "Seuil de Sharpe par trade attendu du meilleur essai sous l'hypothèse nulle, "
        "selon le nombre de configurations essayées et la taille d'échantillon.",
        ["Trades", "1 essai", "3 essais", "10 essais", "100 essais",
         "SR/trade attendu"],
        rows,
        note="La dernière colonne est le Sharpe par trade qu'implique la dérive "
             "publiée. À 400 trades et trois configurations, le seuil de sélection "
             "vaut déjà 0,074 pour un Sharpe attendu de 0,090 : la marge est mince. "
             "Deux conséquences opérationnelles — ne pas dépasser trois variantes, et "
             "ne rien conclure avant un millier de trades.")


def table_protocol() -> Table:
    rows = [
        ["1", "Bande de bruit",
         "Mesurer la bande à chaque demi-heure sur les 14 séances précédentes, et la "
         "fréquence des cassures.",
         "Prix à la minute", "Aucune cassure sur plus de la moitié des séances → la "
         "règle ne se déclenche pas assez pour être testée"],
        ["2", "Dérive captée",
         "Pour chaque cassure, relever le déplacement du prix entre l'entrée et la "
         "sortie effective, et en moyenner la valeur.",
         "Prix à la minute",
         f"Moyenne inférieure à {num(FRICTION_REAL, 2)} point (friction réaliste) → "
         "arrêt"],
        ["3", "Conditionnement gamma",
         "Partitionner les cassures par signe du gamma net publié à l'ouverture, et "
         "comparer les deux dérives.",
         "Un niveau de gamma net quotidien",
         "Écart nul entre les deux groupes → conserver la règle sans le filtre"],
        ["4", "Heure d'entrée",
         "Comparer la dérive captée selon l'heure de la cassure, par tranche d'une "
         "demi-heure.",
         "Les mêmes données qu'au test 2",
         "Dérive concentrée sur une seule tranche → suspecter la sélection, pas la "
         "structure"],
        ["5", "Exécution",
         "Journal en temps réel : heure de cassure, prix d'entrée, écart au prix "
         "théorique, sortie, motif.",
         "Le journal lui-même",
         "Écart d'exécution moyen supérieur à un tick → la friction réaliste est "
         "optimiste, refaire le test 2 avec la valeur mesurée"],
    ]
    return Table(
        "protocol",
        "Protocole de validation, du moins coûteux au plus coûteux. Chaque ligne peut "
        "interrompre la séquence.",
        ["#", "Test", "Mesure", "Données requises", "Critère d'arrêt"],
        rows,
        note="Aucun de ces tests ne demande de flux de carnet ni d'abonnement "
             "payant, et les quatre premiers se conduisent sur historique avant "
             "d'engager le moindre dollar. C'est la différence pratique la plus nette "
             "avec le protocole d'ALP-1, dont le test décisif exigeait un flux L2 "
             "enregistré.")


TABLES = [
    table_assumptions,
    table_grading,
    table_family_scores,
    table_calibration,
    table_geometry_compare,
    table_stop_grid,
    table_literature,
    table_edge_scenarios,
    table_sizing,
    table_deflation,
    table_protocol,
]


def all_tables() -> dict[str, Table]:
    tables = [fn() for fn in TABLES]
    return {t.key: t for t in tables}


def main() -> None:
    for i, fn in enumerate(TABLES, start=1):
        t = fn()
        print(f"\n### Table {i} — {t.caption}\n")
        print(t.to_text())


if __name__ == "__main__":
    main()
