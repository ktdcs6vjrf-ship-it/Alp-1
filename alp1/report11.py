"""Les tables du seuil : ce que la géométrie exige du signal.

Trois tables, et elles répondent à trois questions distinctes. La première
montre que le seuil s'effondre quand le stop s'élargit, et pourquoi. La
deuxième chiffre l'écart entre le pire et le meilleur choix, à dérive
identique. La troisième expose la circularité que le module remplace.
"""

from __future__ import annotations

from . import quant as q
from . import seuil
from .costs import COST_BASE, COST_OPTIMISTIC, COST_REALISTIC, ES, MES, NQ
from .report import Table, num

#: La dérive de travail. Elle est **déclarée**, jamais dérivée de la friction,
#: et elle est prise au milieu du domaine que le document nº 1 appelle
#: plausible. C'est tout l'objet de ce chapitre : sortir de la circularité.
DERIVE_TRAVAIL = 2.0


def table_seuil() -> Table:
    """Le seuil à franchir, largeur de stop par largeur de stop."""
    rows = []
    for g in seuil.scan():
        rows.append([
            num(g.stop_pct, 3) + " %",
            num(g.stop_points, 2),
            num(g.exposure_min, 1),
            num(g.friction_ratio, 3),
            num(g.break_even_per_hour, 3),
            "oui" if g.reachable else "non",
            num(g.expectancy_r(DERIVE_TRAVAIL), 4, signed=True),
        ])
    return Table(
        "seuil",
        "Le seuil de dérive que chaque géométrie impose, et ce qu'elle rend "
        "à dérive déclarée.",
        ["Stop", "a (pts)", "E[τ∧T] min", "c/L", "µ* (pt/h)",
         "Dans le plausible", "E[R] à " + num(DERIVE_TRAVAIL, 1) + " pt/h"],
        rows,
        wide=True,
        note="`µ* = c/E[τ∧T]` est le seuil de rentabilité, et il ne dépend "
             "que de la géométrie et de la friction — jamais du signal. Il "
             "décroît quadratiquement parce que l'exposition croît comme le "
             "carré du stop quand le risque nominal ne croît que "
             "linéairement. La dernière colonne est l'identité de Wald à "
             "dérive déclarée ; l'optimum y est intérieur, la saturation de "
             "séance reprenant d'un côté ce que la friction cède de l'autre.")


def table_ecart() -> Table:
    """Du pire au meilleur choix, à dérive identique."""
    cas = (
        ("Stop déclaré, MES, friction réaliste", 0.010, COST_REALISTIC, MES),
        ("Stop déclaré, ES, friction réaliste", 0.010, COST_REALISTIC, ES),
        ("Stop déclaré, ES, friction de référence", 0.010, COST_BASE, ES),
        ("Stop déclaré, ES, friction optimiste", 0.010, COST_OPTIMISTIC, ES),
        ("Stop 0,050 %, ES, friction de référence", 0.050, COST_BASE, ES),
        ("Stop 0,150 %, ES, friction de référence", 0.150, COST_BASE, ES),
        ("Stop 0,150 %, ES, friction optimiste", 0.150, COST_OPTIMISTIC, ES),
    )
    rows = []
    for nom, pct, cost, contrat in cas:
        g = seuil.geometry(pct, cost, contrat)
        rows.append([
            nom,
            num(g.break_even_per_hour, 3),
            "oui" if g.reachable else "non",
            num(g.expectancy_r(DERIVE_TRAVAIL), 4, signed=True),
        ])
    return Table(
        "ecart",
        "Le même signal, sept géométries : ce que le choix de l'opérateur "
        "fait au seuil qu'il doit franchir.",
        ["Configuration", "µ* (pt/h)", "Dans le plausible",
         "E[R] à " + num(DERIVE_TRAVAIL, 1) + " pt/h"],
        rows,
        wrap_cols=[0],
        wide=True,
        rules_after=[3],
        note="Aucune ligne ne suppose une dérive différente d'une autre : "
             "seule la géométrie change. Les quatre premières lignes sont "
             "hors du domaine plausible, et la conclusion qui s'y attache "
             "n'est pas que la stratégie est improbable — c'est qu'elle est "
             "arithmétiquement impossible, quelle que soit la dérive réelle, "
             "tant qu'elle reste dans le domaine que le document nº 1 "
             "déclare.")


def table_circularite() -> Table:
    """L'hypothèse que ce chapitre remplace."""
    ref = q.reference_drift() * 60.0
    haut = seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]
    mu_star = q.FRICTION / q.geometry(q.RR_REF).expected_time * 60.0
    rows = [
        ["Dérive de référence du document nº 1",
         num(ref, 2), "définie comme " + num(q.DRIFT_MULTIPLE, 0) + "·µ*"],
        ["Seuil µ* à la géométrie déclarée", num(mu_star, 2), "mesuré"],
        ["Borne haute du domaine plausible", num(haut, 2), "déclarée"],
        ["Dérive de travail de ce chapitre",
         num(DERIVE_TRAVAIL, 2), "déclarée, dans le domaine"],
    ]
    return Table(
        "circularite",
        "La dérive de référence du document nº 1, et ce à quoi elle se "
        "compare.",
        ["Grandeur", "Points par heure", "Statut"],
        rows,
        wrap_cols=[0, 2],
        wide=True,
        note="La dérive de référence vaut `DRIFT_MULTIPLE × c/E[τ]`, soit "
             "deux fois le seuil de rentabilité : elle est **dérivée de la "
             "friction**, donc l'avantage y est supposé et non mesuré. Elle "
             "vaut " + num(ref / haut, 1) + " fois la borne haute du domaine "
             "que le même document appelle plausible. Les chapitres de risque "
             "qui tournent sous cette dérive doivent se lire ainsi. Ce "
             "chapitre-ci déclare la sienne et ne la dérive de rien.")


TABLES = (table_seuil, table_ecart, table_circularite)


def all_tables() -> dict[str, Table]:
    """Indexées par clé, comme `report10` : le gabarit les cite par nom."""
    return {fn().key: fn() for fn in TABLES}


def values() -> dict[str, str]:
    """Les scalaires que le document cite."""
    declare = seuil.geometry(0.010)
    optimum = seuil.best(DERIVE_TRAVAIL)
    pire = seuil.geometry(0.010, COST_REALISTIC, MES)
    meilleur = seuil.geometry(0.150, COST_OPTIMISTIC)
    return {
        "s_mu_declare": num(declare.break_even_per_hour, 2),
        "s_er_declare": num(declare.expectancy_r(DERIVE_TRAVAIL), 3, signed=True),
        "s_stop_optimum": num(optimum.stop_pct, 3),
        "s_mu_optimum": num(optimum.break_even_per_hour, 3),
        "s_er_optimum": num(optimum.expectancy_r(DERIVE_TRAVAIL), 3, signed=True),
        "s_expo_optimum": num(optimum.exposure_min, 0),
        "s_facteur": num(pire.break_even_per_hour
                         / meilleur.break_even_per_hour, 0),
        "s_derive_travail": num(DERIVE_TRAVAIL, 1),
        "s_plausible_bas": num(seuil.PLAUSIBLE_DRIFT_PER_HOUR[0], 1),
        "s_plausible_haut": num(seuil.PLAUSIBLE_DRIFT_PER_HOUR[1], 1),
        "s_ref_circulaire": num(q.reference_drift() * 60.0, 1),
        "s_ref_facteur": num(q.reference_drift() * 60.0
                             / seuil.PLAUSIBLE_DRIFT_PER_HOUR[1], 1),
        "s_stop_declare": num(declare.stop_pct, 3),
        "s_cl_declare": num(declare.friction_ratio * 100.0, 0) + " %",
    }


def main() -> None:
    for t in all_tables():
        print(t.caption)
        print(t.to_text())
        print()
    for k, v in values().items():
        print(f"  {k:20} {v}")
