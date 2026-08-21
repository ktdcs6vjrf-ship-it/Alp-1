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

from .calib import (
    AXIS_LABEL,
    CONCLUSIONS,
    REFERENCE,
    breaking_points,
    identity_checks,
    plausibility_checks,
    verdicts,
)
from .costs import (
    COST_BASE,
    COST_OPTIMISTIC,
    COST_REALISTIC,
    ES,
    MES,
    deflated_threshold_sharpe,
)
from .friction import (
    RETAIL_ES,
    friction_box,
    friction_law,
    implied_exit_slippage_ticks,
    margins,
    max_size_for_margin,
)
from .grading import ALP1 as GRADE_ALP1, ALP2 as GRADE_ALP2, CRITERIA, families
from .horizon import hurst_from_dispersions, outcome_scaled
from .microstructure import adequacy_rows, gap_comparison, robustness_box
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
from .prereg import BUDGET, PROTOCOL, degrees_of_freedom
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
             "Ce seuil reste le bon repère à opposer à un Sharpe rapporté sans "
             "protocole ; il n'est pas la règle de décision retenue, qui traite la "
             "multiplicité en séquence fixée plutôt qu'en la corrigeant après coup.")


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
         "Moyenne inférieure à la friction déduite au quantile 90 % → arrêt"],
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
         "Écart d'exécution moyen au-delà du quantile 90 % de la loi de friction "
         "→ le chiffrage de la friction est faux, et toutes les marges avec lui"],
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



# --- Cohérence de la calibration --------------------------------------------

def table_identities() -> Table:
    rows = []
    for c in identity_checks(REFERENCE):
        rows.append([
            c.label, num(c.obtained, 6), num(c.expected, 6),
            "ok" if c.ok else "ÉCHEC", c.comment,
        ])
    return Table(
        "identities",
        "Les identités que la calibration doit satisfaire exactement. Ce ne sont "
        "pas des contrôles de plausibilité : un écart au-delà de la tolérance "
        "serait une erreur d'algèbre.",
        ["Identité", "Obtenu", "Attendu", "Verdict", "Ce qu'elle dit"],
        rows, wrap_last=True,
        note="Aucune de ces lignes n'est ajustable. Elles sont vérifiées à chaque "
             "exécution du dépôt, et leur échec arrêterait la construction du "
             "document avant qu'il ne soit écrit.")


def table_plausibility() -> Table:
    rows = []
    for r in plausibility_checks(REFERENCE):
        rows.append([
            r.label, num(r.obtained, 2, r.unit),
            f"[{num(r.lo, 2)} ; {num(r.hi, 2)}]",
            "ok" if r.ok else "ÉCHEC", r.comment,
        ])
    return Table(
        "plausibility",
        "Les contrôles qui peuvent échouer : les entrées confrontées à des "
        "fourchettes posées d'avance, tirées d'observations publiques et non du "
        "document.",
        ["Grandeur", "Valeur", "Fourchette admise", "Verdict", "Motif de la "
         "fourchette"],
        rows, wrap_last=True,
        note="La ligne du taux de réussite est la seule où une sortie du noyau "
             "rencontre une observation de tiers : 33,8 % impliqués par la "
             "géométrie contre 38 à 40 % rapportés par les réplications de la même "
             "règle. Le chiffre n'a pas été calibré dessus — il tombe là.")


def table_box() -> Table:
    rows = []
    for v in verdicts():
        e = v.enclosure
        rows.append([
            e.label, num(e.reference, 4, e.unit), num(e.lo, 4), num(e.hi, 4),
            f"{v.conclusion.side} {num(v.conclusion.bound, 3)}",
            "tient" if v.holds else "TOMBE",
        ])
    return Table(
        "box",
        "Chaque conclusion du document, encadrée par balayage tensoriel sur la "
        "boîte de plausibilité — 3 125 combinaisons des cinq entrées libres.",
        ["Conclusion", "À la référence", "Minimum", "Maximum", "Seuil", "Verdict"],
        rows,
        note="Les trois lignes centrales — dérive rapportée à la friction, "
             "résultat net, Sharpe par trade — sont la même inégalité écrite dans "
             "trois unités ; elles basculent donc ensemble, et c'est ce qu'on "
             "vérifie plutôt que de le supposer.")


def table_breaking() -> Table:
    target = CONCLUSIONS[3]        # résultat net par trade
    rows = []
    for b in breaking_points(target):
        val = "aucun" if b.value is None else num(b.value, 3)
        rows.append([
            AXIS_LABEL[b.axis],
            f"[{num(b.box_lo, 3)} ; {num(b.box_hi, 3)}]", val,
            "\u221e" if b.factor == float("inf") else num(b.factor, 2, "×"),
            "oui" if b.inside_box else "non",
        ])
    return Table(
        "breaking",
        "Points de rupture de la conclusion « l'espérance nette par trade reste "
        "positive » : valeur de chaque entrée qui l'annule, les autres étant "
        "placées au plus défavorable de la boîte.",
        ["Entrée", "Boîte", "Rupture", "Facteur au-delà de la boîte",
         "Dans la boîte ?"],
        rows,
        note="Aucune rupture n'est atteinte à l'intérieur de la boîte. Il faut une "
             "friction de 1,50 point — 2,6 fois le pire scénario d'exécution — ou "
             "une dérive tombée de 6 à 1,2 point de base pour annuler l'espérance. "
             "C'est la forme utile d'un test de sensibilité : elle dit ce qu'il "
             "faudrait croire pour renverser la conclusion.")


# --- Adéquation du modèle ---------------------------------------------------

def table_adequacy() -> Table:
    rows = []
    for r in adequacy_rows(STOP_PTS, ENTRY_MIN, SIGMA_1MIN, FRICTION, SESSION_MIN):
        rows.append([
            r.label, num(r.diffusion, 4, r.unit), num(r.seasonal, 4),
            num(r.jumps, 4), num(r.heteroscedastic, 4),
            num(r.worst_deviation_pct, 2, "%"),
            "invariant" if r.invariant else "—",
        ])
    return Table(
        "adequacy",
        "Les grandeurs du document sous chacun des trois écarts documentés, pris "
        "un à la fois : saisonnalité en U, sauts, volatilité de séance aléatoire.",
        ["Grandeur", "Diffusion", "Saisonnalité", "Sauts", "Hétéroscédasticité",
         "Écart max", "Statut"],
        rows, rules_after=[1],
        note="Les deux premières lignes sont nulles dans toutes les colonnes, et "
             "c'est le résultat central : le critère maître survit aux trois "
             "écarts. Il est plus robuste que la diffusion dont il est tiré, parce "
             "qu'il ne demande au prix que d'être une martingale sous friction, ce "
             "que le changement de temps, les sauts centrés et une volatilité "
             "aléatoire laissent intact.")


def table_gaps() -> Table:
    stops = (3.0, 10.0, STOP_PTS, 40.0)
    exposures = (28.9, 100.0, v2_outcome().expected_time, 200.0)
    rows = []
    for g in gap_comparison(stops, exposures):
        rows.append([
            num(g.stop, 1), num(100 * g.p_jump, 1, "%"),
            num(g.expected_overshoot, 4), num(g.realised_loss, 3),
            num(g.inflation_pct, 3, "%"), num(g.cost_in_r, 5),
        ])
    return Table(
        "gaps",
        "Ce qu'un saut coûte selon la largeur du stop. Deux familles de sauts : "
        "décalages de carnet fréquents et petits, surprises macro rares et "
        "grandes.",
        ["Stop (pt)", "P(saut pendant l'exposition)", "Dépassement espéré (pt)",
         "Perte réalisée (pt)", "Inflation du risque", "Coût (R)"],
        rows, rules_after=[2],
        note="Le saut ne déplace pas l'espérance — la sortie d'ALP-2 étant au "
             "marché, le dépassement entre dans X et Wald l'absorbe. Il déplace le "
             "dénominateur. Sur un stop de trois points, la perte réelle excède la "
             "perte nominale de 9,3 % ; sur la bande de bruit, de 0,3 %. C'est le "
             "rapport de trente entre les deux géométries devant le même marché.")


def table_micro_box() -> Table:
    rows = []
    for r in robustness_box(STOP_PTS, ENTRY_MIN, SIGMA_1MIN, FRICTION, SESSION_MIN):
        rows.append([
            r.label, num(r.base, 4, r.unit), num(r.lo, 4), num(r.hi, 4),
            num(r.worst_deviation_pct, 1, "%"),
        ])
    return Table(
        "micro_box",
        "Les paramètres du modèle enrichi ne sont pas mesurés non plus : ils sont "
        "balayés sur quatre-vingt-une combinaisons, et c'est l'encadrement qui "
        "est rapporté.",
        ["Grandeur", "Référence", "Minimum", "Maximum", "Écart max"], rows,
        note="Le pire déplacement de la boîte, 19 %, reste d'un ordre de grandeur "
             "inférieur à la marge que la dérive documentée laisse sur la "
             "friction. C'est la seule lecture qui compte : non pas que les "
             "grandeurs soient stables, mais que leur variation ne consomme pas la "
             "marge.")


# --- La friction comme loi --------------------------------------------------

def table_friction_law() -> Table:
    o = v2_outcome()
    law = friction_law(SIGMA_1MIN, o.p_stop, 1.0, RETAIL_ES)
    rows = []
    for name, pts, origin in law.components():
        rows.append([name, num(pts, 4, "pt"),
                     num(100 * pts / law.mean, 1, "%"), origin])
    rows.append(["Total — E[c]", num(law.mean, 4, "pt"), num(100.0, 1, "%"),
                 f"contre {num(FRICTION, 3)} pt posés en scénario de référence et "
                 f"{num(FRICTION_REAL, 3)} pt en scénario réaliste"])
    return Table(
        "friction_law",
        "La friction déduite au lieu d'être posée : barème publié, profondeur du "
        "carnet, latence, volatilité conditionnelle au déclenchement.",
        ["Composante", "Points", "Part", "Origine du chiffre"],
        rows, wrap_last=True, rules_after=[len(rows) - 1],
        note=f"Le glissement de sortie déduit vaut "
             f"{num(implied_exit_slippage_ticks(law), 2)} tick, contre un tick posé "
             "en scénario de référence et un tick et demi en scénario réaliste. Les "
             "deux routes ne partagent aucun paramètre : leur rencontre est une "
             "vérification. La friction posée en référence était optimiste d'un "
             "facteur deux.")


def table_friction_quantiles() -> Table:
    o = v2_outcome()
    law = friction_law(SIGMA_1MIN, o.p_stop, 1.0, RETAIL_ES)
    edge = _edge_pts()
    rows = []
    for m in margins(law, edge, STOP_PTS):
        rows.append([
            num(100 * m.quantile, 1, "%"), num(m.friction, 3, "pt"),
            num(m.c_over_l_pct, 2, "%"), num(m.net_points, 3, "pt"),
            num(m.factor, 1, "×"),
        ])
    return Table(
        "friction_quantiles",
        "La marge de la dérive documentée sur la friction, non pas en moyenne "
        "mais au quantile où l'on perd.",
        ["Quantile", "Friction", "c/L", "Net par trade", "Facteur"], rows,
        note="La friction n'efface la dérive qu'à une fréquence de l'ordre de trois "
             "pour un milliard de trades, au lieu de référence. Ce n'est pas la "
             "friction qui menace cette géométrie — c'est l'absence de mesure de la "
             "dérive.")


def table_capacity() -> Table:
    o = v2_outcome()
    edge = _edge_pts()
    rows = []
    for q in (0.50, 0.90, 0.99):
        row = [num(100 * q, 0, "%")]
        for f in (1.0, 2.0, 3.0):
            n = max_size_for_margin(SIGMA_1MIN, o.p_stop, edge, f, q)
            row.append(num(n, 1) if n > 0 else "aucune")
        row.append(num(max_size_for_margin(SIGMA_1MIN, o.p_stop, edge, 2.0, q)
                       * INDEX_LEVEL * ES.point_value / 1e6, 1, "M$"))
        rows.append(row)
    return Table(
        "capacity",
        "Taille maximale en contrats ES préservant une marge donnée, la friction "
        "croissant linéairement avec la taille par l'impact de carnet.",
        ["Quantile de friction", "Marge 1×", "Marge 2×", "Marge 3×",
         "Notionnel à marge 2×"],
        rows,
        note="La contrainte de capacité ne dépend pas du capital mais de ce que le "
             "carnet porte, et elle mord bien avant : quelques dizaines de "
             "contrats, soit quelques millions de dollars de notionnel. Au quantile "
             "99 %, une marge de trois n'est atteinte par aucune taille — la "
             "friction incompressible suffit à la refuser.")


def table_friction_box() -> Table:
    o = v2_outcome()
    edge = _edge_pts()
    b = friction_box(SIGMA_1MIN, o.p_stop, edge)
    rows = [
        ["Friction moyenne E[c]", num(b.mean_lo, 3, "pt"), num(b.mean_hi, 3, "pt"),
         num(b.mean_margin, 2, "×"), "oui" if b.survives else "NON"],
        ["Friction au quantile 99 %", num(b.q99_lo, 3, "pt"),
         num(b.q99_hi, 3, "pt"), num(b.worst_margin, 2, "×"),
         "oui" if b.tail_survives else "NON"],
    ]
    return Table(
        "friction_box",
        f"La friction encadrée sur {num(b.n_eval, 0)} combinaisons des paramètres "
        "de carnet — profondeur, dispersion, amincissement au stop, latence, "
        "volatilité de déclenchement.",
        ["Grandeur", "Minimum", "Maximum", "Marge au pire coin", "La marge tient ?"],
        rows,
        note="La distinction entre les deux lignes est celle qu'il faut garder. "
             "L'espérance du trade survit partout dans la boîte, avec au minimum un "
             "facteur 2,8. Le centième trade le plus coûteux, dans le carnet le "
             "plus dégradé de la boîte — profondeur de quinze contrats, "
             "amincissement à 15 %, latence d'une seconde et demie —, ne survit "
             "pas. Ce résultat est conservé plutôt que fait disparaître en "
             "resserrant la boîte : il désigne le régime où la taille doit être "
             "réduite.")


# --- Pré-enregistrement -----------------------------------------------------

def table_prereg() -> Table:
    p = PROTOCOL
    rows = [
        ["Sceau SHA-256", p.seal + "…", "empreinte de la sérialisation canonique "
         "du protocole, publiable avant d'ouvrir le moindre fichier de prix"],
        ["Version", p.version, f"scellée le {p.sealed_on}"],
        ["Budget", num(BUDGET, 0) + " configurations, en séquence fixée",
         ", ".join(f"{c.key} — {c.label}" for c in p.configurations)],
        ["Panel", num(len(p.markets), 0) + " contrats", ", ".join(p.markets)
         + " — même règle, trois fuseaux, aucun ajout ni retrait"],
        ["Statistique primaire", "dérive nette par minute", p.primary_statistic],
        ["Multiplicité", "séquence fixée", p.multiplicity],
        ["Règle de décision", num(len(p.looks), 0) + " examens séquentiels",
         p.decision_rule],
        ["Horizon", num(p.horizon_sessions, 0) + " séances",
         "soit " + num(p.horizon_sessions / 252, 0) + " années ; budget "
         "d'information calé sur " + num(p.design_sessions, 0) + " séances, et "
         "aucun examen avant " + num(p.min_sessions, 0)],
        ["Cadence", num(p.max_entries_per_session, 0) + " entrées par séance "
         "au plus", "ré-armement imposé : le prix doit revenir dans la bande "
         "avant qu'une nouvelle cassure compte"],
        ["Validation croisée", f"{p.cv_folds} plis purgés",
         f"embargo de {p.cv_embargo_days} séance de part et d'autre de chaque pli"],
    ]
    return Table(
        "prereg",
        "Le protocole scellé. L'empreinte se publie avant la mesure ; toute "
        "modification ultérieure la change et se voit.",
        ["Élément", "Valeur", "Détail"], rows, wrap_last=True,
        note="Ce que le sceau établit : qu'un protocole donné existait à une date "
             "donnée, et que ce qui est mesuré ensuite est ce qui avait été "
             "annoncé. Ce qu'il n'établit pas : que rien d'autre n'a été essayé en "
             "parallèle. Aucun dispositif extérieur ne peut l'établir ; celui-ci "
             "rend l'écart repérable, ce qui est le seul usage honnête d'un "
             "pré-enregistrement.")


def table_dof() -> Table:
    rows = [[name, value] for name, value in degrees_of_freedom()]
    return Table(
        "dof",
        "Tout ce qui aurait pu être ajusté, et la valeur à laquelle c'est gelé.",
        ["Degré de liberté", "Valeur gelée"], rows, wrap_last=True,
        note="L'intérêt de la liste n'est pas d'être longue mais d'être close : un "
             "degré de liberté qui n'y figure pas et qui est pourtant utilisé dans "
             "la mesure est une violation du protocole, repérable par simple "
             "lecture du code de mesure.")


TABLES = [
    table_assumptions,
    table_grading,
    table_family_scores,
    table_identities,
    table_plausibility,
    table_box,
    table_breaking,
    table_calibration,
    table_geometry_compare,
    table_stop_grid,
    table_literature,
    table_edge_scenarios,
    table_sizing,
    table_deflation,
    table_adequacy,
    table_gaps,
    table_micro_box,
    table_friction_law,
    table_friction_quantiles,
    table_capacity,
    table_friction_box,
    table_prereg,
    table_dof,
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
