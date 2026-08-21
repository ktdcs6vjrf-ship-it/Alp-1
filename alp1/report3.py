"""Tables et valeurs des deux corrections apportées au document de travail.

Deux objections restaient sans réponse dans le document. Elles sont traitées
ici, chacune par son module de calcul et ses tables.

**La dérive est empruntée à des travaux publiés.** Un effet publié s'arbitre.
`alp1.decay` chiffre la décote documentée, la traduit en taux annuel, et en
tire la durée de vie résiduelle de la conclusion. C'est la seule section du
document qui porte une date d'expiration.

**L'exposant d'échelle est posé deux fois, à deux valeurs différentes.**
`alp1.scaling` refait la chaîne de calibration sous un exposant quelconque et
montre dans quel sens la conclusion bouge — contre elle, et non pour elle.
"""

from __future__ import annotations

import math

from .calib import BOX, REFERENCE, breaking_points, derive, verdicts
from .decay import (
    DECAY_OUT_OF_SAMPLE,
    DECAY_POST_PUBLICATION,
    DECAY_WINDOW_YEARS,
    breaking_decay,
    breaking_rate,
    decay_rate,
    half_life,
    rate_box,
    runways,
    scenario_grid,
    surviving_edge,
)
from .momentum import edge_points_from_bps
from .report import Table, num


def year(y: float) -> str:
    """Une année s'écrit sans séparateur de milliers."""
    return str(int(round(y))).replace("-", "\u2212")
from .scaling import (
    HURST_ASSUMED,
    HURST_HI,
    HURST_LO,
    HURST_MARTINGALE,
    calibrate,
    coherence_gap,
    robust_entry,
    sensitivity,
    worst_case,
)

#: Année d'observation. Fixée explicitement plutôt que lue sur l'horloge : un
#: document dont les nombres changent avec la date de compilation n'est pas
#: reproductible, et la durée de vie résiduelle est précisément un nombre qu'un
#: lecteur doit pouvoir recalculer à l'identique.
ASOF_YEAR = 2026

EDGE_BPS = REFERENCE.edge_bps
INDEX = REFERENCE.index_level


def _breaking_edge_bps() -> float:
    """Point de rupture de la dérive, en points de base.

    Repris du module de calibration plutôt que recalculé : c'est le même
    nombre que celui de la table des ruptures, et il doit le rester.
    """
    concl = next(v.conclusion for v in verdicts()
                 if v.enclosure.key == "net_points")
    for b in breaking_points(concl):
        if b.axis == "edge_bps" and b.value is not None:
            return b.value
    raise LookupError("pas de point de rupture sur l'axe edge_bps")


# --- Décote post-publication ------------------------------------------------


def table_decay_evidence() -> Table:
    lam = decay_rate()
    lo, _, hi = rate_box()
    rows = [
        ["Décote hors échantillon, avant publication",
         num(DECAY_OUT_OF_SAMPLE * 100, 0, "%"),
         "McLean et Pontiff (2016), 97 anomalies",
         "Surajustement du travail d'origine"],
        ["Décote après publication",
         num(DECAY_POST_PUBLICATION * 100, 0, "%"),
         "McLean et Pontiff (2016)",
         "Arbitrage par les lecteurs"],
        ["Décote hors États-Unis",
         "0 %",
         "Jacobs et Müller (2020), 39 marchés",
         "Aucune décote détectée : la borne basse de la boîte"],
        ["Taux annuel retenu",
         num(lam, 3) + " / an",
         "Déduit : 58 % consommés en "
         + num(DECAY_WINDOW_YEARS, 0) + " ans",
         "Demi-vie de " + num(half_life(lam), 1) + " ans"],
        ["Boîte du taux annuel",
         num(lo, 3) + " – " + num(hi, 3),
         "Bornes des deux lignes précédentes",
         "58 % en 3 ans pour la borne haute"],
    ]
    return Table(
        "decay_evidence",
        "Ce que la littérature documente de la décote post-publication d'un effet, "
        "et le taux annuel qu'on en déduit.",
        ["Grandeur", "Valeur", "Source", "Lecture"],
        rows,
        wrap_cols=[2, 3],
        rules_after=[3],
        note="Les deux premières lignes sont mesurées, la troisième est une absence "
             "de mesure, et les deux dernières sont déduites sous hypothèse de "
             "décroissance exponentielle — la seule forme à un paramètre compatible "
             "avec une décote observée sur une fenêtre. Aucune n'est estimée ici.")


def table_decay_runway() -> Table:
    brk = _breaking_edge_bps()
    rows = []
    for r in runways(EDGE_BPS, brk, ASOF_YEAR):
        rows.append([
            r.source,
            year(r.published),
            num(r.age, 0),
            num(r.edge_today, 2),
            num(r.margin, 2) + "×",
            year(r.expiry),
            num(r.remaining, 1),
        ])
    return Table(
        "decay_runway",
        "Dérive subsistante et durée de vie résiduelle de la conclusion, "
        "vues de " + year(ASOF_YEAR) + ", au taux de décroissance retenu.",
        ["Travail source", "Publié", "Âge", "Dérive restante (pdb)",
         "Marge sur rupture", "Année de rupture", "Années restantes"],
        rows,
        wrap_cols=[0],
        wide=True,
        note="Le point de rupture est de " + num(brk, 2) + " point de base : c'est la "
             "dérive sous laquelle l'espérance nette s'annule. La marge n'est pas le "
             "rapport de la dérive publiée à ce seuil, mais celui de la dérive qu'il "
             "en reste aujourd'hui. Lue depuis le travail de 2018, la fenêtre "
             "d'exploitation se referme avant la fin de la décennie.")


def table_decay_scenarios() -> Table:
    brk = _breaking_edge_bps()
    published = min(runways(EDGE_BPS, brk, ASOF_YEAR),
                    key=lambda r: r.published).published
    scen = scenario_grid(EDGE_BPS, brk, ASOF_YEAR, published)
    brk_rate = breaking_rate(EDGE_BPS, brk, float(ASOF_YEAR - published))
    rows = []
    for rate, edge, margin, holds in scen:
        rows.append([
            num(rate, 3) + " / an",
            "∞" if rate <= 0 else num(half_life(rate), 1),
            num(edge, 2),
            num(edge_points_from_bps(edge, INDEX), 2),
            num(margin, 2) + "×",
            "tient" if holds else "TOMBE",
        ])
    return Table(
        "decay_scenarios",
        "La conclusion sur toute la boîte du taux de décroissance, dérive datée "
        "de la publication de " + year(published) + ".",
        ["Taux annuel", "Demi-vie (ans)", "Dérive restante (pdb)",
         "en points", "Marge sur rupture", "Verdict"],
        rows,
        note="La conclusion ne tient pas sur toute la boîte : elle bascule au-delà "
             "de " + num(brk_rate, 3) + " par an, soit une demi-vie de "
             + num(half_life(brk_rate), 1) + " ans. Ce taux est intérieur à la "
             "boîte de plausibilité, et c'est le fait marquant de cette section — "
             "la survie de la conclusion ne dépend plus seulement de la dérive "
             "publiée, mais de la vitesse à laquelle elle s'arbitre, qui n'est pas "
             "mesurée ici. La marge passe de " + num(EDGE_BPS / brk, 2) + "× sans "
             "décote à " + num(scen[-1][2], 2) + "× au taux le plus sévère.")


# --- Cohérence de l'exposant d'échelle --------------------------------------


def table_scaling_chain() -> Table:
    rows = []
    for s in sensitivity(HURST_LO, HURST_HI, 4):
        rows.append([
            num(s.hurst, 2),
            num(s.sigma_1min, 3),
            num(s.band, 2),
            num(s.p_stop * 100, 1, "%"),
            num(s.exposure, 1),
            num(s.mu_star_per_hour, 4),
            num(s.ir_star, 4),
        ])
    a, b, factor = coherence_gap()
    return Table(
        "scaling_chain",
        "La chaîne de calibration refaite sous chaque exposant d'échelle, "
        "les trois entrées du document restant inchangées.",
        ["H", "σ₁ (pt)", "Bande (pt)", "P(stop)", "E[τ∧T] (min)",
         "µ* (pt/h)", "IR*"],
        rows,
        note="La première ligne est la calibration du document, retrouvée à la "
             "douzième décimale. La dernière est celle qu'imposerait l'exposant que "
             "le document invoque par ailleurs : le seuil de signal y est "
             + num(factor, 3) + " fois plus élevé. Une persistance plus forte "
               "n'aide donc pas — elle éloigne le prix plus vite du point d'entrée, "
               "le stop est touché plus souvent, et le seuil monte.")


def table_scaling_entry() -> Table:
    rows = []
    best = min(robust_entry(), key=lambda r: r[2])
    for t, expo, mu, ir in robust_entry():
        rows.append([
            num(t, 0),
            num(expo, 1),
            num(mu, 4),
            num(ir, 4),
            "retenu par le protocole" if t == REFERENCE.entry_min
            else ("optimum au pire cas" if t == best[0] else ""),
        ])
    return Table(
        "scaling_entry",
        "Heure d'entrée évaluée au pire cas sur la boîte d'exposant, "
        "toutes les autres entrées inchangées.",
        ["Entrée (min)", "E[τ∧T] (min)", "µ* (pt/h)", "IR*", "Statut"],
        rows,
        wrap_cols=[4],
        note="Retarder l'entrée élargit la bande de bruit, donc éloigne le stop et "
             "allonge l'exposition ; mais la séance restante raccourcit. L'optimum "
             "est intérieur et tombe à " + num(best[0], 0) + " minutes, contre "
             + num(REFERENCE.entry_min, 0) + " retenues par le protocole scellé. "
             "L'écart est de " + num((1 - best[2] / robust_entry()[2][2]) * 100, 1)
             + " % sur la dérive requise — réel, modeste, et gratuit.")


TABLES = [
    table_decay_evidence,
    table_decay_runway,
    table_decay_scenarios,
    table_scaling_chain,
    table_scaling_entry,
]


def all_tables() -> dict[str, Table]:
    return {fn().key: fn() for fn in TABLES}


def values() -> dict[str, str]:
    brk = _breaking_edge_bps()
    lam = decay_rate()
    lo_r, _, hi_r = rate_box()
    rws = runways(EDGE_BPS, brk, ASOF_YEAR)
    first, last = rws[0], rws[-1]
    a, b, factor = coherence_gap()
    best = min(robust_entry(), key=lambda r: r[2])
    ref_entry = [r for r in robust_entry() if r[0] == REFERENCE.entry_min][0]
    w = worst_case()

    return {
        # --- décote ---
        "decay_pub": num(DECAY_POST_PUBLICATION * 100, 0),
        "decay_oos": num(DECAY_OUT_OF_SAMPLE * 100, 0),
        "decay_rate": num(lam, 3),
        "decay_halflife": num(half_life(lam), 1),
        "decay_rate_hi": num(hi_r, 3),
        "decay_break": num(breaking_decay(EDGE_BPS, brk) * 100, 1),
        "decay_brk_bps": num(brk, 2),
        "decay_first_year": year(first.published),
        "decay_first_left": num(first.edge_today, 2),
        "decay_first_margin": num(first.margin, 2),
        "decay_first_expiry": year(first.expiry),
        "decay_first_remaining": num(first.remaining, 1),
        "decay_last_year": year(last.published),
        "decay_last_left": num(last.edge_today, 2),
        "decay_last_margin": num(last.margin, 2),
        "decay_last_expiry": year(last.expiry),
        "decay_margin_nominal": num(EDGE_BPS / brk, 2),
        "decay_brk_rate": num(breaking_rate(EDGE_BPS, brk, float(ASOF_YEAR - first.published)), 3),
        "decay_brk_halflife": num(half_life(breaking_rate(EDGE_BPS, brk, float(ASOF_YEAR - first.published))), 1),
        "asof": year(ASOF_YEAR),

        # --- exposant d'échelle ---
        "scal_ir_half": num(a, 4),
        "scal_ir_high": num(b, 4),
        "scal_factor": num(factor, 3),
        "scal_sigma_high": num(calibrate(HURST_HI).sigma_1min, 3),
        "scal_band_high": num(calibrate(HURST_HI).band, 2),
        "scal_pstop_half": num(calibrate(HURST_LO).p_stop * 100, 1),
        "scal_pstop_high": num(calibrate(HURST_HI).p_stop * 100, 1),
        "scal_worst_h": num(w.hurst, 2),
        "scal_entry_best": num(best[0], 0),
        "scal_entry_ref": num(REFERENCE.entry_min, 0),
        "scal_entry_gain": num((1 - best[2] / ref_entry[2]) * 100, 1),
        "scal_expo_best": num(best[1], 1),
        "scal_expo_ref": num(ref_entry[1], 1),
    }


def main() -> None:
    for i, fn in enumerate(TABLES, start=1):
        t = fn()
        print(f"\n### Table {i} — {t.caption}\n")
        print(t.to_text())
    print("\n\nValeurs\n")
    for k, v in sorted(values().items()):
        print(f"  {k:24} {v}")


if __name__ == "__main__":
    main()
