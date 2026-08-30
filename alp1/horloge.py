"""Le régime de gamma déplace l'horloge, et il ne déplace que l'horloge.

La mécanique de couverture des teneurs est correctement décrite partout, y
compris dans la vulgarisation qui circule : gamma long, ils vendent les
hausses et achètent les creux, le mouvement est étouffé ; gamma court,
l'inverse, le mouvement est amplifié. Le document nº 3 l'écrit déjà, et il
ajoute la seule chose qui compte — **le mécanisme contraint la dispersion et
laisse la direction indéterminée.**

Ce module chiffre la suite, que personne n'écrit : si le régime ne déplace
que la dispersion, alors *que déplace-t-il dans la décision ?*

La réponse tient en une colonne constante — sous une condition
-------------------------------------------------------------
La dispersion entre par l'exposant d'échelle, qui n'agit que sur le temps
d'atteinte. Les probabilités de barrière du problème **non borné** n'en
dépendent pas : c'est le théorème d'arrêt optionnel, et il vaut exactement.
Donc, tant que la séance ne borne rien :

* la probabilité d'atteindre le target vaut `1/(1 + R:R)` à tout régime ;
* le temps d'exposition, lui, varie d'un facteur trois entre le chop maximal
  et la tendance maximale ;
* donc `µ* = c/E[τ∧T]` varie du même facteur trois.

**La condition n'est pas décorative, et elle a failli passer.** Une séance
finit ; un trade qui n'a touché aucune barrière avant la clôture sort à la
clôture, et cette troisième issue — `p_open` — dépend, elle, du régime. À la
géométrie déclarée elle est négligeable : le stop fait six dixièmes de point
et les barrières se résolvent en quelques minutes, si bien que `p_open` reste
sous un dix-millième sur toute la plage de régimes et que l'invariance tient à
quatre décimales. C'est le cadre de la table.

Élargissez le stop et la condition tombe. À cinq centièmes de pour cent, un
huitième des trades atteint la clôture en chop contre un pour dix mille en
tendance, et la probabilité de target passe d'un facteur trente-cinq entre
les deux. **Le régime déplace alors bien la probabilité de touche** — non pas parce qu'il aurait cessé de n'agir que sur
l'horloge, mais parce que l'horloge décide désormais si la séance est assez
longue pour atteindre le target. La première version de ce module affirmait
l'invariance sans sa condition ; quatre tests l'ont refusée.

**Le régime de gamma ne dit pas si vous toucherez votre target. Il dit
combien de temps vous resterez en position** — et la partie « Sortir » a
établi que c'est la seule grandeur sur laquelle un opérateur agit.

L'inversion
-----------
La lecture populaire veut que le jour de tendance soit le jour à trader. À
géométrie fixe, c'est le contraire : la tendance résout les barrières plus
vite, achète donc moins de temps de marché pour la même friction, et laisse
une espérance *plus mauvaise* que le chop. « Tendance » au sens du gamma
signifie mouvements amplifiés, c'est-à-dire variance — pas direction.

La fenêtre
----------
Reste la question utile : à quelle condition la lecture du régime
change-t-elle une décision ? Le module la résout. Il existe une bande de
largeurs de stop, et une seule, où le régime décide du **signe** de
l'espérance : en deçà tout est perdu quel que soit le régime, au-delà tout
est gagné quel que soit le régime. La bande est étroite, et la géométrie
déclarée par l'opérateur tombe **sous** elle.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from .costs import COST_BASE, ES, stop_points
from .figterm import ADV_USD, SESSION_MIN, SIGMA_1MIN
from .horizon import outcome_scaled
from . import gex
from . import quant as q
from . import seuil
from .report import Table, num
from .report11 import DERIVE_TRAVAIL

#: Exposants balayés. Les bornes sont celles du domaine que le document nº 1
#: tient pour plausible sur un indice — au-delà, le GEX impliqué sort des
#: ordres de grandeur observés.
EXPOSANTS = (0.46, 0.50, 0.55, 0.60, 0.70)

#: Largeur de stop, en pourcentage de l'indice, à laquelle la séance cesse de
#: ne rien borner. C'est le contre-exemple qui donne sa condition à
#: l'invariance : à cette largeur le régime déplace bien la probabilité de
#: touche, parce que l'horloge décide si la séance est assez longue.
STOP_LARGE = 0.050

#: Largeurs de stop de la grille, en pour-cent de l'indice.
STOPS_PCT = (0.010, 0.013, 0.020, 0.025, 0.030, 0.050, 0.150)

#: Ratio gain/risque tenu fixe : le régime ne le concerne pas.
RR = 20.0


def friction() -> float:
    return COST_BASE.friction_points(ES)


@dataclass(frozen=True)
class Regime:
    """Un régime de gamma, et ce qu'il fait à la géométrie déclarée."""

    hurst: float
    gex_implique: float       # $ par 1 % de variation, signé
    exposition: float         # E[τ∧T] en minutes
    seuil: float              # µ* en points d'indice par heure
    p_target: float           # probabilité d'atteindre le target
    p_open: float             # sortie à la clôture, sans barrière touchée
    esperance: float          # E[R] à la dérive de travail


@lru_cache(maxsize=None)
def regime(hurst: float, stop_pct: float = 0.010,
           drift_per_hour: float = DERIVE_TRAVAIL) -> Regime:
    a = stop_points(q.INDEX_LEVEL, stop_pct)
    o = outcome_scaled(a, RR * a, SESSION_MIN, SIGMA_1MIN, hurst)
    c = friction()
    return Regime(
        hurst=hurst,
        gex_implique=gex.required_gex_for_hurst(hurst, ADV_USD,
                                                horizon_min=SESSION_MIN),
        exposition=o.expected_time,
        seuil=60.0 * c / o.expected_time,
        p_target=o.p_target,
        p_open=o.p_open,
        esperance=(drift_per_hour / 60.0 * o.expected_time - c) / a,
    )


@lru_cache(maxsize=None)
def seuil_par_stop(stop_pct: float, hurst: float) -> float:
    """`µ*` en points par heure, à une largeur de stop et un exposant."""
    a = stop_points(q.INDEX_LEVEL, stop_pct)
    o = outcome_scaled(a, RR * a, SESSION_MIN, SIGMA_1MIN, hurst)
    return 60.0 * friction() / o.expected_time


def verdict(stop_pct: float, drift_per_hour: float = DERIVE_TRAVAIL) -> str:
    """Ce que la lecture du régime décide, à cette largeur de stop.

    Trois états seulement, et c'est le résultat : le régime ne décide du
    signe de l'espérance que dans une bande étroite. En deçà tout est perdu
    quel que soit le régime, au-delà tout est gagné quel que soit le régime,
    et la lecture ne change alors aucune décision.
    """
    bas = seuil_par_stop(stop_pct, min(EXPOSANTS))
    haut = seuil_par_stop(stop_pct, max(EXPOSANTS))
    if bas > drift_per_hour:
        return "perdue à tout régime"
    if haut <= drift_per_hour:
        return "gagnée à tout régime"
    return "**décidée par le régime**"


@lru_cache(maxsize=None)
def fenetre(drift_per_hour: float = DERIVE_TRAVAIL,
            pas: float = 0.00005) -> tuple[float, float]:
    """Les deux largeurs de stop qui bornent la bande où le régime décide.

    Balayage à pas fin plutôt que résolution analytique : `E[τ∧T]` passe par
    la série d'absorption, et une bissection y coûterait le même prix pour
    une précision que la publication n'utilise pas.
    """
    bas = haut = None
    k = 1
    while k * pas <= 0.20:
        pct = k * pas
        etat = verdict(pct, drift_per_hour)
        if bas is None and etat.startswith("**"):
            bas = pct
        if bas is not None and etat == "gagnée à tout régime":
            haut = pct
            break
        k += 1
    if bas is None or haut is None:
        raise ValueError("aucune bande trouvée sur la grille balayée")
    return bas, haut


# --- Tables ----------------------------------------------------------------


def table_horloge() -> Table:
    """Ce que le régime déplace, et la colonne qui ne bouge pas."""
    rows = []
    for h in EXPOSANTS:
        r = regime(h)
        nom = ("gamma long, chop" if h < 0.5 else
               "neutre" if h == 0.5 else
               "gamma court, tendance" if h >= 0.70 else "gamma court")
        rows.append([
            nom, num(h, 2),
            num(r.gex_implique / 1e11 + 0.0, 2) if abs(r.gex_implique) > 5e8
            else num(0.0, 2),
            num(r.exposition, 2),
            num(r.seuil, 2),
            num(100.0 * r.p_target, 3) + " %",
            num(100.0 * r.p_open, 4) + " %",
            num(r.esperance, 4, signed=True),
        ])
    facteur = (regime(min(EXPOSANTS)).exposition
               / regime(max(EXPOSANTS)).exposition)
    return Table(
        "horloge",
        "Ce que le régime de gamma déplace à la géométrie déclarée, et ce "
        "qu'il ne déplace pas",
        ["Régime", "H", "GEX impliqué (10¹¹ $)", "E[τ∧T] (min)", "µ* (pt/h)",
         "p(target)", "p(clôture)",
         "E[R] à " + num(DERIVE_TRAVAIL, 1) + " pt/h"],
        rows,
        wrap_cols=[0],
        wide=True,
        note="**La colonne p(target) ne bouge pas d'un millième** — elle vaut "
             + num(100.0 / (1.0 + RR), 3) + " %, soit exactement "
             "`1/(1 + R:R)`. C'est le théorème d'arrêt optionnel : les "
             "probabilités de barrière du problème non borné ne dépendent que "
             "de la géométrie, jamais de l'exposant d'échelle. La colonne "
             "voisine dit à quelle condition : `p(clôture)` est la part des "
             "trades qui sortent sans avoir touché de barrière, et elle reste "
             "ici sous un dix-millième. **À cette géométrie, la séance ne "
             "borne rien, et le régime ne dit pas si le target sera touché.** "
             "Élargir le stop retire cette condition — à 0,050 % de stop, "
             + num(100.0 * regime(min(EXPOSANTS), 0.050).p_open, 0)
             + " % des trades atteignent la clôture en chop contre "
             "presque aucun en tendance, et la probabilité de target passe "
             "d'un facteur "
             + num(regime(max(EXPOSANTS), 0.050).p_target
                   / regime(min(EXPOSANTS), 0.050).p_target, 0)
             + " entre les deux régimes, parce que l'horloge décide alors si "
             "la séance est assez longue. "
             "Ce qu'il déplace est le temps, d'un facteur " + num(facteur, 1)
             + " entre le chop et la tendance, donc le seuil du même facteur. "
             "La dernière colonne porte l'inversion que la lecture courante "
             "manque : à géométrie fixe, le jour de tendance est celui dont "
             "l'espérance est la **pire**, parce qu'il résout les barrières "
             "plus vite et achète donc moins de temps de marché pour la même "
             "friction. « Tendance » au sens du gamma signifie mouvements "
             "amplifiés, c'est-à-dire variance — pas direction.")


def table_fenetre() -> Table:
    """Où la lecture du régime change une décision, et où elle n'en change aucune."""
    lo, hi = min(EXPOSANTS), max(EXPOSANTS)
    rows = []
    for pct in STOPS_PCT:
        rows.append([
            num(pct, 3) + " %",
            num(seuil_par_stop(pct, lo), 2),
            num(seuil_par_stop(pct, hi), 2),
            verdict(pct),
        ])
    bas, haut = fenetre()
    return Table(
        "fenetre_gamma",
        "À quelle largeur de stop la lecture du régime change une décision",
        ["Largeur de stop", "µ* en chop (pt/h)", "µ* en tendance (pt/h)",
         "Ce que le régime décide"],
        rows,
        wrap_cols=[3],
        wide=True,
        rules_after=[0],
        note="Le verdict de la dernière colonne compare les deux seuils "
             "extrêmes à la dérive de travail déclarée, "
             + num(DERIVE_TRAVAIL, 1) + " point par heure. Trois états "
             "seulement, et c'est le résultat : **le régime ne décide du "
             "signe de l'espérance que dans une bande étroite**, entre "
             + num(bas, 4) + " % et " + num(haut, 4) + " % de largeur de "
             "stop. En deçà, tout est perdu quel que soit le régime ; "
             "au-delà, tout est gagné quel que soit le régime, et la lecture "
             "ne change alors aucune décision. **La géométrie déclarée par "
             "l'opérateur, " + num(0.010, 3) + " %, tombe sous cette "
             "bande** : le régime n'y décide rien, parce que rien n'y est à "
             "décider. C'est la réponse chiffrée à la question « faut-il "
             "lire le gamma avant l'ouverture ? » — seulement si le stop "
             "tombe dans la bande, et il faut d'abord l'y mettre.")


TABLES = (table_horloge, table_fenetre)


def all_tables() -> dict[str, Table]:
    return {fn().key: fn() for fn in TABLES}


def values() -> dict[str, str]:
    bas_h, haut_h = min(EXPOSANTS), max(EXPOSANTS)
    chop, trend = regime(bas_h), regime(haut_h)
    bas, haut = fenetre()
    return {
        "g_p_target": num(100.0 / (1.0 + RR), 3),
        "g_h_bas": num(bas_h, 2),
        "g_h_haut": num(haut_h, 2),
        "g_tau_chop": num(chop.exposition, 2),
        "g_tau_trend": num(trend.exposition, 2),
        "g_facteur": num(chop.exposition / trend.exposition, 1),
        "g_mu_chop": num(chop.seuil, 2),
        "g_mu_trend": num(trend.seuil, 2),
        "g_er_chop": num(chop.esperance, 3, signed=True),
        "g_er_trend": num(trend.esperance, 3, signed=True),
        "g_gex_trend": num(trend.gex_implique / 1e11, 2),
        "g_plafond": num(seuil.PLAUSIBLE_DRIFT_PER_HOUR[1], 1),
        "g_fenetre_bas": num(bas, 4),
        "g_fenetre_haut": num(haut, 4),
        "g_stop_large": num(STOP_LARGE, 3),
        "g_open_chop": num(100.0 * regime(min(EXPOSANTS), STOP_LARGE).p_open, 0),
        "g_facteur_target": num(regime(max(EXPOSANTS), STOP_LARGE).p_target
                                / regime(min(EXPOSANTS), STOP_LARGE).p_target, 0),
        "g_stop_declare": num(0.010, 3),
    }


def main() -> None:
    for fn in TABLES:
        t = fn()
        print(t.caption)
        print(t.to_text())
        print()
    for k, v in values().items():
        print(f"  {k:16} {v}")
