"""Tables de la stratégie scellée : ses portes, leur prix, et sa batterie.

Le document démontait sept couches sans jamais dire laquelle retenir. Ce
module produit les tables qui tranchent — le catalogue des portes avec la
raison qui ferme chacune, le prix qu'une confluence fait payer au seuil de
sélection, et le verdict de la batterie sur une série dont la vérité est
connue.
"""

from __future__ import annotations

import math

from .costs import deflated_threshold_sharpe
from .dataset import synthetic_sessions
from .report import Table, num
from .strategy import (
    ENTRY_MIN,
    EXIT_MIN,
    GATES,
    MAX_ENTRIES,
    REFERENCE_BITS,
    SEALED,
    run,
    validate,
)

#: Trades du protocole borné — cinq marchés, 1 260 séances.
SEALED_TRADES = 7012

#: Sharpe par trade qu'implique la dérive documentée.
SEALED_SR = 0.0332

#: Contrôle synthétique, mêmes graine et longueur que partout ailleurs.
N_SESSIONS = 300
SEED = 20260822


def _verdict():
    return validate(run(synthetic_sessions(N_SESSIONS, seed=SEED)), draws=300)


def table_gates() -> Table:
    rows = []
    for g in GATES:
        rows.append([
            g.label,
            g.layer,
            "ouverte" if g.enabled else "fermée",
            ", ".join(g.needs),
            g.rationale,
        ])
    return Table(
        "gates",
        "Les portes de la stratégie, l'état de chacune, et la raison qui la "
        "décide.",
        ["Porte", "Couche d'origine", "État", "Données exigées", "Pourquoi"],
        rows,
        wrap_cols=[0, 1, 4],
        wide=True,
        rules_after=[2],
        note="Les deux premières lignes ne sont pas des portes optionnelles : "
             "le déclencheur définit la règle, et la correction de stop ne "
             "décide d'aucune entrée. Aucune des deux n'ajoute de "
             "configuration. Les cinq suivantes sont fermées, et chacune "
             "porte la raison qui la ferme — tirée du diagnostic de la "
             "troisième partie, non d'une préférence.")


def table_gate_price() -> Table:
    rows = []
    for k in range(6):
        b = 2.0 ** k
        s = deflated_threshold_sharpe(b, SEALED_TRADES)
        rows.append([
            num(k, 0),
            num(b, 0),
            num(s, 4),
            num(s / SEALED_SR * 100, 0, "%"),
            "oui" if s < SEALED_SR else "NON",
        ])
    return Table(
        "gate_price",
        "Ce qu'une couche de confluence coûte au seuil de sélection, sur les "
        + num(SEALED_TRADES, 0) + " trades du protocole borné.",
        ["Portes ouvertes", "Configurations", "Seuil de sélection",
         "Part du Sharpe consommée", "Le signal franchit encore"],
        rows,
        wide=True,
        note="C'est la version chiffrée d'une intuition répandue et fausse. "
             "Ajouter une couche paraît toujours améliorer une stratégie, "
             "puisque le taux de réussite affiché monte. Mais chaque porte "
             "est un choix binaire, la famille double, et le seuil croît "
             "comme la racine de son logarithme. Une porte consomme "
             + num(deflated_threshold_sharpe(2.0, SEALED_TRADES)
                   / SEALED_SR * 100, 0)
             + " % du Sharpe de la dérive documentée ; les cinq en consomment "
             + num(deflated_threshold_sharpe(32.0, SEALED_TRADES)
                   / SEALED_SR * 100, 0)
             + " % — avant qu'aucune n'ait prouvé qu'elle apporte quoi que ce "
               "soit. Une configuration unique, elle, ne paie rien.")


def table_battery() -> Table:
    v = _verdict()
    rows = []
    for c in v.checks:
        rows.append([
            c.label,
            "franchi" if c.passed else "MANQUÉ",
            c.reading,
        ])
    return Table(
        "battery",
        "La batterie appliquée à une série sans dérive, où la seule réponse "
        "juste est le refus.",
        ["Contrôle", "Verdict", "Lecture"],
        rows,
        wrap_cols=[0, 2],
        wide=True,
        note="Aucun contrôle n'est facultatif et aucun n'est pondéré : un seul "
             "manqué suffit à refuser. C'est la seule règle de décision qui "
             "résiste à la tentation de chercher l'angle sous lequel un "
             "résultat paraît bon. La série de cette table est une marche "
             "aléatoire par construction, et la batterie manque "
             + num(len(v.failed), 0) + " contrôles sur "
             + num(len(v.checks), 0) + " — une batterie qui accepterait tout "
               "ne contrôlerait rien.")


def table_spec() -> Table:
    rows = [
        ["Déclencheur", "Cassure de la bande de bruit",
         "Seule couche dont la loi nulle est exactement connue"],
        ["Heure d'entrée", num(ENTRY_MIN, 0) + " minutes",
         "Optimum au pire cas sur la boîte d'exposant, non l'heure qui "
         "maximise le rendement mesuré"],
        ["Largeur du stop", "La bande, indexée sur la volatilité du nœud",
         "Un stop en pourcentage fixe n'est pas un risque fixe"],
        ["Objectif", "Aucun",
         "Le théorème d'invariance interdit qu'il crée de l'espérance ; il "
         "ne ferait que raccourcir l'exposition"],
        ["Sortie", "Au marché, minute " + num(EXIT_MIN, 0),
         "Maximise le temps de marché, seul canal par lequel une géométrie "
         "agit"],
        ["Entrées par séance", num(MAX_ENTRIES, 0) + " au plus, ré-armement imposé",
         "Sans plafond, une séance agitée achèterait des trades sans acheter "
         "d'information"],
        ["Friction", "Loi déduite du carnet, quantile médian",
         "Déduite du barème, de la profondeur et de la latence, jamais posée"],
        ["Configurations", num(SEALED.budget, 0),
         "Aucune porte optionnelle ouverte, donc aucune taxe de sélection"],
    ]
    return Table(
        "spec",
        "La stratégie scellée, paramètre par paramètre, et la raison de "
        "chacun.",
        ["Élément", "Valeur", "Pourquoi celle-là"],
        rows,
        wrap_cols=[0, 1, 2],
        wide=True,
        note="Rien n'y est ajustable après avoir vu les données. Aucune "
             "sous-période n'est écartée, aucun seuil de confluence n'est "
             "optimisé, et la règle refuse de conclure quand l'échantillon ne "
             "suffit pas — ce qui est le cas le plus fréquent.")


TABLES = [table_spec, table_gates, table_gate_price, table_battery]


def all_tables() -> dict[str, Table]:
    return {fn().key: fn() for fn in TABLES}


def values() -> dict[str, str]:
    v = _verdict()
    un = deflated_threshold_sharpe(2.0, SEALED_TRADES)
    cinq = deflated_threshold_sharpe(32.0, SEALED_TRADES)
    return {
        "st_entry": num(ENTRY_MIN, 0),
        "st_exit": num(EXIT_MIN, 0),
        "st_max": num(MAX_ENTRIES, 0),
        "st_budget": num(SEALED.budget, 0),
        "st_gates_open": num(len(SEALED.open_gates), 0),
        "st_gates_closed": num(len(GATES) - len(SEALED.open_gates), 0),
        "st_price_one": num(un, 4),
        "st_price_one_pct": num(un / SEALED_SR * 100, 0),
        "st_price_all": num(cinq, 4),
        "st_price_all_pct": num(cinq / SEALED_SR * 100, 0),
        "st_checks": num(len(v.checks), 0),
        "st_failed": num(len(v.failed), 0),
        "st_ref_bits": num(REFERENCE_BITS * 1e6, 1),
        "st_trades": num(SEALED_TRADES, 0),
    }


def main() -> None:
    for i, fn in enumerate(TABLES, start=1):
        t = fn()
        print(f"\n### Table {i} — {t.caption}\n")
        print(t.to_text())
    print("\n\nValeurs\n")
    for k, x in sorted(values().items()):
        print(f"  {k:18} {x}")


if __name__ == "__main__":
    main()
