"""Tables du risque réel : la géométrie déclarée par l'opérateur, et le forçage.

Le document retenait un stop de cinq centièmes de pour cent. L'opérateur en
déclare un de cinq à dix **millièmes**, une remontée au point mort, deux pour
cent du capital par tentative, et une pratique de répétition de l'entrée
jusqu'à ce qu'elle passe. Ce module refait sur cette géométrie tout ce que le
document faisait sur l'autre.

Le changement n'est pas de degré. À cette largeur de stop, la friction cesse
d'être un prélèvement sur le risque pour en devenir la moitié, puis la
totalité ; l'exposition s'effondre d'un facteur douze ; et les deux effets
poussent l'exigence de signal dans le même sens. Aucune des conclusions
qualitatives du document ne change — c'est la marque d'un cadre qui tient —
mais toutes les quantités changent d'ordre de grandeur.
"""

from __future__ import annotations

import math

from . import forcing as F
from .costs import (COST_BASE, COST_OPTIMISTIC, COST_REALISTIC, ES, MES, MNQ,
                    NQ, stop_points)
from .horizon import outcome_scaled
from .report import (HURST, INDEX_LEVEL, SESSION_MIN, SIGMA_1MIN, STOP_PCT,
                     STOP_PCT_BOX, Table, num)
from .report3 import year as _plain

#: Contrats examinés, et le niveau auquel chacun cote. Un pourcentage de prix
#: ne dit rien sans le niveau ni sans le pas de cotation.
CONTRACT_LEVELS = ((ES, 6000.0), (NQ, 22000.0), (MES, 6000.0), (MNQ, 22000.0))

#: Largeurs comparées : la boîte de l'opérateur, puis l'ancienne calibration.
STOP_ROWS = (0.005, 0.010, 0.050)

#: Ratios visés examinés.
RR_ROWS = (5.0, 10.0, 20.0, 30.0)

RR_REF = 20.0
SPREAD_POINTS = ES.tick_size * 1.0

#: Nombre de tentatives sur lequel la ruine est évaluée, et niveau de ruine.
RUIN_TRADES = 100
RUIN_LEVEL = 0.5


def _cl(pct: float, cost=COST_BASE) -> float:
    return cost.friction_points(ES) / stop_points(INDEX_LEVEL, pct)


def _exposure(pct: float, rr: float = RR_REF) -> float:
    L = stop_points(INDEX_LEVEL, pct)
    return outcome_scaled(L, rr * L, SESSION_MIN, SIGMA_1MIN, HURST).expected_time


def _sharpe(pct: float) -> float:
    return F.required_sharpe_annual(COST_BASE.friction_points(ES),
                                    _exposure(pct), SIGMA_1MIN)


# --- La géométrie réelle -------------------------------------------------------

def table_geometry() -> Table:
    rows = []
    for c, lvl in CONTRACT_LEVELS:
        for pct in STOP_PCT_BOX:
            r = F.friction_over_stop(c, COST_BASE, lvl, pct)
            rows.append([
                c.symbol, num(lvl, 0), num(pct, 3) + " %",
                num(F.stop_ticks(c, lvl, pct), 2),
                num(F.friction_ticks(c, COST_BASE), 2),
                num(r, 3),
                "non" if r >= 1.0 else "oui",
            ])
    return Table(
        key="frc_geometrie",
        caption="La géométrie déclarée, lue en ticks : quatre contrats, deux "
                "largeurs de stop",
        headers=["Contrat", "Niveau", "Stop", "Stop (ticks)",
                 "Friction (ticks)", "c/L", "Viable"],
        rows=rows,
        rules_after=[2, 4, 6],
        note="Un stop ne se juge pas en pourcentage mais **en ticks**, parce "
             "que c'est au tick que la friction se compte. Sur les deux "
             "contrats micro, la friction dépasse le stop : l'aller-retour "
             "coûte plus que le risque nominal, et aucun signal ne rattrape "
             "cela. Sur le contrat E-mini du Nasdaq, dont le tick est fin "
             "relativement au niveau, la même largeur en pourcentage laisse "
             "c/L à un cinquième. **Le choix du contrat pèse ici plus lourd "
             "que le choix du signal.**",
    )


def table_breakeven() -> Table:
    rows = []
    for pct in STOP_ROWS:
        cl = _cl(pct)
        rows.append([
            num(pct, 3) + " %",
            num(stop_points(INDEX_LEVEL, pct), 2),
            num(cl, 3),
            num(F.breakeven_exit_r(cl), 2),
            num(-1.0 - cl, 2),
            num(F.breakeven_exit_r(cl) / (-1.0 - cl) * 100, 0),
        ])
    return Table(
        key="frc_point_mort",
        caption="Ce qu'une sortie « au point mort » coûte réellement",
        headers=["Stop", "Points", "c/L", "Sortie au point mort (R)",
                 "Sortie au stop (R)", "Part du stop"],
        rows=rows,
        note="La friction est due dans **toutes** les issues, sortie au point "
             "mort comprise : le point mort n'est mort que du prix. À la "
             "géométrie la plus serrée, une sortie au point mort coûte plus "
             "cher qu'un stop entier n'en coûtait à l'ancienne calibration. "
             "Et comme un journal de trading retire habituellement les "
             "sorties à BE du dénominateur du taux de réussite, **c'est "
             "l'issue la plus fréquente et la plus coûteuse qui disparaît des "
             "statistiques tenues.**",
    )


def table_spread() -> Table:
    rows = []
    for pct in STOP_ROWS:
        L = stop_points(INDEX_LEVEL, pct)
        utile = F.effective_stop(L, SPREAD_POINTS)
        rows.append([
            num(pct, 3) + " %",
            num(L, 2),
            num(SPREAD_POINTS, 2),
            num(utile, 2),
            num(F.spread_share(L, SPREAD_POINTS) * 100, 0) + " %",
            num(F.noise_stop_probability(L, SPREAD_POINTS, SIGMA_1MIN) * 100, 1)
            + " %",
        ])
    return Table(
        key="frc_spread",
        caption="Ce que le spread prend du stop avant que le prix ne bouge",
        headers=["Stop", "Points", "Spread", "Stop utile",
                 "Part prise par le spread", "Sorti par le bruit en 1 min"],
        rows=rows,
        note="Dans le modèle de Roll (1984), le prix observé oscille entre "
             "bid et ask autour d'un prix efficient **inchangé**. Une entrée "
             "à l'ask et un stop `L` sous l'entrée sont touchés dès que le "
             "prix efficient a baissé de `L − s` : le stop utile n'est pas "
             "`L`. La dernière colonne est la probabilité de premier passage "
             "sur ce stop utile en une minute, sans aucune dérive — et elle "
             "explique, seule, une série de cinq à six échecs consécutifs.",
    )


# --- Le forçage -----------------------------------------------------------------

def table_forcing() -> Table:
    rows = []
    for rr in RR_ROWS:
        f10 = F.force_until_success(rr, _cl(0.010))
        f05 = F.force_until_success(rr, _cl(0.005))
        rows.append([
            f"1:{rr:.0f}",
            num(f10.hit_rate * 100, 2) + " %",
            num(f10.attempts, 1),
            num(f10.gross_r, 3, signed=True),
            num(f10.net_r, 2, signed=True),
            num(f05.net_r, 2, signed=True),
        ])
    return Table(
        key="frc_theoreme",
        caption="Le théorème du forçage : répéter jusqu'à la réussite, et ce "
                "qu'il en coûte",
        headers=["Ratio visé", "p sous prix sans dérive", "Tentatives moyennes",
                 "Brut (R)", "Net, stop 0,010 % (R)", "Net, stop 0,005 % (R)"],
        rows=rows,
        note="La colonne « brut » est le résultat entier de la séquence avant "
             "friction, et elle vaut **exactement zéro à toutes les lignes**. "
             "Ce n'est pas un arrondi : c'est le théorème d'arrêt optionnel, "
             "appliqué à une règle d'arrêt sur la séquence de trades plutôt "
             "que sur le trajet du prix. Il n'y a donc rien à optimiser dans "
             "la façon de forcer. Ce qui reste est la friction, payée "
             "`R+1` fois pour un seul aboutissement.",
    )


def table_streaks() -> Table:
    p = F.martingale_hit_rate(RR_REF)
    rows = []
    for k in (3, 5, 6, 10, 21, 34):
        rows.append([
            _plain(k),
            num(F.streak_probability(p, k) * 100, 1) + " %",
            num(F.streak_probability(F.martingale_hit_rate(5.0), k) * 100, 1) + " %",
            num(F.drawdown_after(0.02, k) * 100, 1) + " %",
            num(F.drawdown_after(0.005, k) * 100, 1) + " %",
        ])
    return Table(
        key="frc_series",
        caption="La loi des séries, et ce qu'elle fait au capital",
        headers=["Échecs consécutifs", "P au ratio 1:20", "P au ratio 1:5",
                 "Capital effacé à 2 %", "Capital effacé à 0,5 %"],
        rows=rows,
        note=f"Six échecs de suite à un ratio de 1:20 surviennent avec "
             f"probabilité {num(F.streak_probability(p, 6) * 100, 1)} % — "
             f"l'opérateur qui en observe cinq ou six n'a pas subi un "
             f"accident, **il a observé la médiane**. Sur deux cents "
             f"tentatives, la plus longue série attendue vaut "
             f"{num(F.expected_longest_streak(p, 200), 0)}. Une série longue "
             f"finit toujours par arriver, et n'est donc jamais à elle seule "
             f"une information sur la qualité du signal.",
    )


def table_capital() -> Table:
    p = F.martingale_hit_rate(RR_REF)
    rows = []
    for pct in STOP_ROWS:
        lv = F.leverage(F.RISK_PER_TRADE, pct)
        rows.append([
            num(pct, 3) + " %",
            num(lv, 0) + " ×",
            num(F.gap_wipeout(F.RISK_PER_TRADE, pct, 0.5) * 100, 0) + " %",
            num(F.gap_wipeout(F.RISK_PER_TRADE, pct, 2.0) * 100, 0) + " %",
            num(F.risk_of_ruin(p, RR_REF, _cl(pct), F.RISK_PER_TRADE,
                               RUIN_TRADES) * 100, 1) + " %",
        ])
    return Table(
        key="frc_capital",
        caption="Le levier que la géométrie impose, et ce qu'il expose",
        headers=["Stop", "Levier notionnel", "Écart de 0,5 %", "Écart de 2 %",
                 f"P(perdre la moitié en {_plain(RUIN_TRADES)} tentatives)"],
        rows=rows,
        note=f"Risquer {num(F.RISK_PER_TRADE * 100, 0)} % du capital sur un "
             f"déplacement de prix de {num(STOP_PCT, 3)} % **impose** un "
             f"levier de {num(F.leverage(F.RISK_PER_TRADE, STOP_PCT), 0)} "
             f"fois le capital : le levier n'est pas un troisième choix, il "
             f"est fixé par les deux autres. Or un stop ne franchit pas un "
             f"trou de cotation. À ce levier, un écart d'ouverture ordinaire "
             f"n'emporte pas une position, il emporte le compte. La dernière "
             f"colonne est simulée sous prix sans dérive, graine explicite.",
    )


# --- Ce qu'il faudrait posséder ------------------------------------------------

def table_requirement() -> Table:
    rows = []
    for pct in STOP_ROWS:
        rows.append([
            num(pct, 3) + " %",
            num(_cl(pct), 3),
            num(_exposure(pct), 2),
            num(COST_BASE.friction_points(ES) / _exposure(pct) * 60.0, 3),
            num(_sharpe(pct), 1),
            num(_sharpe(pct) / _sharpe(0.050), 1) + " ×",
        ])
    return Table(
        key="frc_exigence",
        caption="Ce que le resserrement du stop exige du signal",
        headers=["Stop", "c/L", "E[τ] (min)", "µ* (pt/h)",
                 "Sharpe annualisé requis", "Rapport à 0,050 %"],
        rows=rows,
        note="L'exigence monte par **deux canaux à la fois**, et c'est ce qui "
             "rend le resserrement si coûteux : la friction relative croît "
             "comme l'inverse de la largeur, et l'exposition s'effondre parce "
             "qu'un stop proche est touché vite. Les deux effets vont dans le "
             "même sens et se multiplient. Le repère à retenir est celui de "
             "la dernière colonne : passer de 0,050 % à 0,010 % ne rend pas "
             "l'exigence un peu plus dure, il la multiplie par douze.",
    )


def table_regime() -> Table:
    d = F.persistence_cannot_help(RR_REF, _cl(STOP_PCT), SIGMA_1MIN / stop_points(
        INDEX_LEVEL, STOP_PCT))
    rows = []
    for h, v in sorted(d["atteint"].items()):
        rows.append([
            num(h, 2),
            num(v * 100, 4) + " %",
            num(d["cible"] * 100, 4) + " %",
            "non",
        ])
    return Table(
        key="frc_regime",
        caption="Aucun exposant d'échelle ne rend une géométrie sans dérive "
                "rentable",
        headers=["Exposant H", "p(target) atteint", "p(target) requis",
                 "Seuil franchi"],
        rows=rows,
        note="La colonne du milieu ne bouge pas d'un chiffre significatif, et "
             "ce n'est pas un défaut de la simulation : un changement "
             "d'exposant est un **changement de temps déterministe**, qui ne "
             "modifie pas le rapport des probabilités de premier passage. La "
             "conséquence porte sur la lecture de Kaminski et Lo (2014) : le "
             "momentum qui rend une règle de stop utile chez eux n'est pas "
             "une propriété d'échelle mais une dérive conditionnelle. "
             "**Espérer que la persistance sauve le forçage revient à espérer "
             "la mauvaise grandeur.**",
    )


def table_diagnostic() -> Table:
    tailles = (50, 100, 200, 400)
    rows = []
    for k in (3, 5, 6, 8, 12, 20):
        ligne = [_plain(k)]
        for n in tailles:
            hit = F.implied_hit_rate(k, n)
            ligne.append("—" if hit <= 0.0
                         else f"1:{num(F.implied_reward_risk(hit), 2)}")
        rows.append(ligne)
    return Table(
        key="frc_diagnostic",
        caption="Le diagnostic inverse : ce que votre plus longue série "
                "révèle du ratio que vous pratiquez",
        headers=["Plus longue série d'échecs"]
                + [f"{n} tentatives" for n in tailles],
        rows=rows,
        note="Un tiret marque une case hors domaine : sur cet échantillon, "
             "aucun taux de réussite ne produit en espérance une série aussi "
             "longue. L'instrument ne demande que deux chiffres que l'opérateur "
             "connaît déjà, et n'exige aucune donnée de marché. Il rend le "
             "ratio gain/risque que ce couple implique sous prix sans dérive. "
             "**Une série maximale courte n'est pas une bonne nouvelle** : "
             "elle implique un taux de réussite élevé, donc un ratio bas, "
             "donc une géométrie très éloignée du 1:20 qu'on croit tenir. "
             "Si vos séries plafonnent à cinq ou six sur deux cents "
             "tentatives, vous ne pratiquez pas un 1:20 — vous pratiquez "
             "quelque chose de proche du 1:1, et toutes les tables qui "
             "précèdent doivent être relues à cette ligne.",
    )


# --- Le glossaire ----------------------------------------------------------------

#: Les termes que le document emploie sans les définir, rendus dans une langue
#: qui ne suppose aucune familiarité avec les marchés. L'ordre est celui dans
#: lequel un lecteur les rencontre, non l'ordre alphabétique.
GLOSSARY = (
    ("Point d'indice",
     "l'unité dans laquelle le prix se compte. Un indice à 6 000 points qui "
     "monte de 1 % gagne 60 points."),
    ("Tick",
     "le plus petit écart de prix possible. On ne peut pas coter entre deux "
     "ticks, comme on ne peut pas payer un demi-centime."),
    ("Spread",
     "l'écart entre le prix auquel on peut vendre tout de suite et celui "
     "auquel on peut acheter tout de suite. On le paie à chaque aller-retour, "
     "même si le prix ne bouge pas."),
    ("Friction (c)",
     "tout ce qu'un aller-retour coûte : commission, spread, et l'écart entre "
     "le prix voulu et le prix obtenu. C'est le seul poste certain."),
    ("Stop (L)",
     "l'ordre de sortie automatique posé sous l'entrée, qui borne la perte. "
     "Sa distance à l'entrée est le risque nominal du trade."),
    ("Point mort, ou BE",
     "déplacer le stop jusqu'au prix d'entrée, une fois le trade en gain. On "
     "croit alors ne plus rien risquer ; la friction reste due."),
    ("Ratio gain/risque (R)",
     "combien de fois le risque on cherche à gagner. Un 1:20 vise vingt fois "
     "ce qu'on accepte de perdre."),
    ("Taux de réussite (p)",
     "la part des trades qui atteignent l'objectif. Sous un prix sans "
     "direction, il vaut mécaniquement 1/(R+1) — un 1:20 réussit une fois "
     "sur vingt-et-une, et cela ne dit rien du trader."),
    ("Dérive (µ)",
     "la tendance moyenne du prix par unité de temps. C'est la seule chose "
     "qui puisse produire un gain ; tout le reste ne fait que la répartir."),
    ("Exposition (E[τ])",
     "le temps moyen pendant lequel la position reste ouverte. C'est la durée "
     "pendant laquelle la dérive peut agir."),
    ("Levier",
     "le rapport entre la taille de la position et le capital. Un levier de "
     "200 signifie qu'un mouvement de 1 % du prix vaut 200 % du capital."),
    ("Loi nulle",
     "ce qu'un motif produit sur un prix sans aucune direction. Sans elle, "
     "observer un motif ne prouve rien : il faut savoir à quelle fréquence il "
     "apparaît quand il n'y a rien à voir."),
    ("Martingale",
     "un prix dont la meilleure prévision de demain est sa valeur "
     "d'aujourd'hui. C'est l'hypothèse de référence, celle qu'il faut "
     "réfuter avant d'affirmer un avantage."),
    ("Ratio de Sharpe",
     "le gain moyen rapporté à son irrégularité, sur un an. Un bon fonds "
     "tient 1 sur longue période ; les meilleurs résultats publiés "
     "approchent 3."),
    ("Forçage",
     "reprendre la même entrée après avoir été sorti, jusqu'à ce qu'elle "
     "passe. Une règle d'arrêt posée sur la suite des trades plutôt que sur "
     "le trajet du prix."),
)


def table_glossary() -> Table:
    return Table(
        key="frc_glossaire",
        caption="Les quinze termes nécessaires, dans une langue qui ne "
                "suppose aucune familiarité avec les marchés",
        headers=["Terme", "Ce que c'est"],
        rows=[[t, d] for t, d in GLOSSARY],
        wrap_last=True,
        note="L'ordre est celui dans lequel le document les rencontre, non "
             "l'ordre alphabétique : chaque entrée n'emploie que les "
             "précédentes. La table se lit donc de haut en bas comme une "
             "construction, et non comme un dictionnaire à consulter.",
    )


TABLES = [table_glossary, table_geometry, table_spread, table_breakeven,
          table_forcing, table_streaks, table_capital, table_requirement,
          table_regime, table_diagnostic]


def all_tables() -> dict[str, Table]:
    return {fn().key: fn() for fn in TABLES}


def values() -> dict[str, str]:
    p = F.martingale_hit_rate(RR_REF)
    cl10, cl05 = _cl(0.010), _cl(0.005)
    f10 = F.force_until_success(RR_REF, cl10)
    L10 = stop_points(INDEX_LEVEL, 0.010)
    L05 = stop_points(INDEX_LEVEL, 0.005)
    return {
        "frc_stop_lo": num(STOP_PCT_BOX[0], 3),
        "frc_stop_hi": num(STOP_PCT_BOX[1], 3),
        "frc_pts_lo": num(L05, 2),
        "frc_pts_hi": num(L10, 2),
        "frc_ticks_lo": num(F.stop_ticks(ES, INDEX_LEVEL, 0.005), 2),
        "frc_ticks_hi": num(F.stop_ticks(ES, INDEX_LEVEL, 0.010), 2),
        "frc_cl_lo": num(cl05, 3),
        "frc_cl_hi": num(cl10, 3),
        "frc_cl_ancien": num(_cl(0.050), 3),
        "frc_cl_reel": num(_cl(0.010, COST_REALISTIC), 3),
        "frc_cl_optimiste": num(_cl(0.010, COST_OPTIMISTIC), 3),

        "frc_be_hi": num(F.breakeven_exit_r(cl10), 2),
        "frc_be_lo": num(F.breakeven_exit_r(cl05), 2),
        "frc_be_ancien": num(F.breakeven_exit_r(_cl(0.050)), 2),

        "frc_spread_pts": num(SPREAD_POINTS, 2),
        "frc_utile_hi": num(F.effective_stop(L10, SPREAD_POINTS), 2),
        "frc_utile_lo": num(F.effective_stop(L05, SPREAD_POINTS), 2),
        "frc_part_spread_hi": num(F.spread_share(L10, SPREAD_POINTS) * 100, 0),
        "frc_part_spread_lo": num(F.spread_share(L05, SPREAD_POINTS) * 100, 0),
        "frc_bruit_hi": num(F.noise_stop_probability(
            L10, SPREAD_POINTS, SIGMA_1MIN) * 100, 1),
        "frc_bruit_lo": num(F.noise_stop_probability(
            L05, SPREAD_POINTS, SIGMA_1MIN) * 100, 1),
        "frc_bruit_ancien": num(F.noise_stop_probability(
            stop_points(INDEX_LEVEL, 0.050), SPREAD_POINTS, SIGMA_1MIN) * 100, 1),

        "frc_tentatives": num(f10.attempts, 0),
        "frc_brut": num(abs(f10.gross_r), 3),
        "frc_net_hi": num(f10.net_r, 2),
        "frc_net_lo": num(F.force_until_success(RR_REF, cl05).net_r, 2),
        "frc_multiple": num(f10.cost_multiple, 0),

        "frc_p20": num(p * 100, 2),
        "frc_serie6": num(F.streak_probability(p, 6) * 100, 1),
        "frc_serie5": num(F.streak_probability(p, 5) * 100, 1),
        "frc_serie_max": num(F.expected_longest_streak(p, 200), 0),
        "frc_dd6": num(F.drawdown_after(0.02, 6) * 100, 1),
        "frc_pertes50": num(F.losses_to_drawdown(0.02, 0.5), 0),

        "frc_levier": num(F.leverage(F.RISK_PER_TRADE, STOP_PCT), 0),
        "frc_levier_lo": num(F.leverage(F.RISK_PER_TRADE, 0.005), 0),
        "frc_gap": num(F.gap_wipeout(F.RISK_PER_TRADE, STOP_PCT, 0.5) * 100, 0),
        "frc_risque": num(F.RISK_PER_TRADE * 100, 0),
        "frc_ruine": num(F.risk_of_ruin(p, RR_REF, cl10, F.RISK_PER_TRADE,
                                        RUIN_TRADES) * 100, 1),
        "frc_kelly": num(F.kelly_fraction(p, RR_REF), 3),

        "frc_expo_hi": num(_exposure(0.010), 2),
        "frc_expo_ancien": num(_exposure(0.050), 2),
        "frc_expo_facteur": num(_exposure(0.050) / _exposure(0.010), 1),
        "frc_sharpe_hi": num(_sharpe(0.010), 1),
        "frc_sharpe_lo": num(_sharpe(0.005), 1),
        "frc_sharpe_ancien": num(_sharpe(0.050), 1),
        "frc_sharpe_facteur": num(_sharpe(0.010) / _sharpe(0.050), 1),

        "frc_hurst": num(F.MEASURED_HURST, 4),
        "frc_plafond": num(1.0 / (RR_REF + 1.0) * 100, 4),
        "frc_diag_rr": num(F.implied_reward_risk(F.implied_hit_rate(6, 200)), 2),
        "frc_diag_p": num(F.implied_hit_rate(6, 200) * 100, 1),
        "frc_glossaire_n": num(len(GLOSSARY), 0),

        "frc_nq_cl": num(F.friction_over_stop(NQ, COST_BASE, 22000.0, 0.010), 3),
        "frc_mes_cl": num(F.friction_over_stop(MES, COST_BASE, 6000.0, 0.010), 3),
        "frc_mnq_cl": num(F.friction_over_stop(MNQ, COST_BASE, 22000.0, 0.010), 3),
    }


def main() -> None:
    for i, fn in enumerate(TABLES, start=1):
        t = fn()
        print(f"\n### Table {i} — {t.caption}\n")
        print(t.to_text())
    print("\n\nValeurs\n")
    for k, v in sorted(values().items()):
        print(f"  {k:22} {v}")


if __name__ == "__main__":
    main()
