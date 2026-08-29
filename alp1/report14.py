"""Les tables et les scalaires de la partie « lire le flux ».

Trois couches y sont mesurées contre leur loi nulle : le footprint, le profil
TPO, et le budget d'information que la géométrie impose. Rien n'est écrit à
la main ; tout se calcule depuis `footprint`, `tpo` et `entropy`.
"""

from __future__ import annotations

import math

from . import footprint as fp
from . import quant as q
from . import spectrum as sp
from . import tpo as tp
from .entropy import required_bits, trades_for_information
from .report import Table, num

#: Pas de rangée du profil affiché, en points d'indice. Il est déclaré ici et
#: dans la figure par la même constante — un pas écrit deux fois finirait par
#: diverger, et c'est lui qui décide de la rareté de ce qu'on lit.
PAS_RANGEE = 3.0

#: Volume de niveau retenu pour les lois nulles du déséquilibre. Deux cents
#: quarante contrats est l'ordre de grandeur d'un niveau de barre à la minute
#: sur un future indiciel liquide.
NIVEAU_CONTRATS = 240


def table_footprint() -> Table:
    """Les trois barres construites, et ce que chacune donne à lire."""
    lam = fp.IMPACT_PER_ROOT_VOLUME
    rows = []
    for cle, nom in (("neutre", "Barre neutre"),
                     ("absorption", "Absorption"),
                     ("desequilibre", "Déséquilibre acheteur")):
        bar = fp.synthesise(cle)
        rows.append([
            nom,
            num(bar.volume, 0),
            num(bar.delta, 0, signed=True),
            num(fp.absorption_z(bar, lam), 2, signed=True),
            num(len(fp.diagonal_imbalances(bar)), 0),
            num(fp.expected_imbalances(bar), 2),
            num(fp.exhaustion_ratio(bar, +1), 3),
        ])
    return Table(
        "footprint",
        "Trois barres en footprint, et ce que chacune donne à lire.",
        ["Barre", "Volume", "Δ", "z d'impact", "Déséquilibres",
         "Attendus sous martingale", "Rapport d'épuisement"],
        rows, wrap_cols=[0], wide=True,
        note="Le z d'impact rapporte le déplacement de la barre à celui "
             "qu'un volume de cette taille produit en moyenne ; une "
             "absorption est un z proche de zéro pour un gros volume, jamais "
             "un petit déplacement seul. La colonne des déséquilibres "
             "attendus est la loi nulle de la barre elle-même, à volumes de "
             "niveau inchangés : la barre neutre en produit environ un sans "
             "qu'aucune intention n'y soit, et en relever un ne dit donc "
             "rien.",
    )


def table_tpo() -> Table:
    """Les cinq lectures du profil, et leur fréquence sous un prix sans dérive."""
    prof = tp.synthesise(tick=PAS_RANGEE)
    loi = tp.null_profile(tick=PAS_RANGEE, draws=500)
    va_bas, va_haut = prof.value_area()
    etendue = prof.prices[-1] - prof.prices[0]
    ext_h, ext_b = prof.range_extension()
    oui = "oui"
    non = "non"
    rows = [
        ["Extension de séance", oui if (ext_h or ext_b) else non,
         num(100 * loi.p_extension, 1, "%"), "l'état par défaut"],
        ["Extrême haut pauvre", oui if prof.poor_high else non,
         num(100 * loi.p_poor_high, 1, "%"), "rare, mais selon la rangée"],
        ["Extrême bas pauvre", oui if prof.poor_low else non,
         num(100 * loi.p_poor_low, 1, "%"), "rare, mais selon la rangée"],
        ["Tirages simples", num(len(prof.single_prints), 0),
         num(loi.singles_mean, 1) + " en moyenne", "à comparer, jamais à compter"],
        ["Aire de valeur / étendue",
         num((va_haut - va_bas) / etendue, 3) if etendue else "—",
         num(loi.value_width_mean, 3), "à comparer, jamais à compter"],
    ]
    return Table(
        "tpo",
        "Les cinq lectures du profil de marché, et leur fréquence sur une "
        "séance sans dérive.",
        ["Lecture", "Sur la séance construite", "Sous un prix sans dérive",
         "Ce qu'elle vaut"],
        rows, wrap_cols=[0, 3], wide=True,
        note=f"La séance construite n'a aucune dérive : tout ce qu'on y "
             f"reconnaît a été produit sans intention. Les rangées font "
             f"{num(PAS_RANGEE, 0)} points, ce qui est la convention des "
             f"plateformes sur un future indiciel — et ce choix décide de la "
             f"rareté de l'extrême pauvre bien plus que le marché ne le fait.",
    )


def table_bruit() -> Table:
    """Combien de bruit chaque géométrie supporte, et ce qu'il en coûte."""
    rows = []
    for stop, cl, nom in ((0.010, 0.55, "Géométrie déclarée"),
                          (0.050, 0.11, "Stop à 0,050 %"),
                          (0.150, 0.037, "Optimum du chapitre X")):
        besoin = required_bits(q.RR_REF, cl)
        n = trades_for_information(besoin.bits)
        rows.append([
            nom,
            num(stop, 3, "%"),
            num(100 * cl, 1, "%"),
            num(100 * besoin.bits, 3, "%"),
            num(100 * (1.0 - besoin.bits), 3, "%"),
            num(n, 0),
        ])
    return Table(
        "bruit",
        "Ce qu'une décision doit porter d'information, et ce qu'il en coûte "
        "de l'établir.",
        ["Géométrie", "Stop", "Friction c/L", "Information exigée",
         "Bruit toléré", "Décisions pour le prouver"],
        rows, wrap_cols=[0], wide=True,
        note="L'information est une part d'un bit : une décision binaire en "
             "porte un au plus. La colonne du bruit toléré en est le "
             "complément, et c'est la réponse chiffrée à la question « le "
             "marché est-il du bruit à quatre-vingt-dix-neuf pour cent ». La "
             "dernière colonne en donne le prix : une exigence dix fois plus "
             "petite demande dix fois plus de décisions pour être établie.",
    )


#: Couches suivies et séances observées de la table du spectre. Sept est le
#: nombre de couches que le document nº 3 recense ; deux cent cinquante est
#: l'année de séances qu'un opérateur peut espérer journaliser.
COUCHES = 7
SEANCES = 250


def table_spectre() -> Table:
    """Ce qu'un facteur doit peser pour se voir, selon ce qu'on regarde."""
    rows = []
    for k, n in ((3, SEANCES), (COUCHES, SEANCES), (COUCHES, 60),
                 (12, SEANCES), (20, 60)):
        g = k / n
        _, hi = sp.mp_edges(g)
        seuil = sp.bbp_threshold(g)
        rows.append([
            num(k, 0),
            num(n, 0),
            num(g, 4),
            num(hi, 3),
            num(100 * hi / k, 1, "%"),
            num(seuil, 3),
            num(sp.observations_for_spike(0.30, k), 0),
        ])
    return Table(
        "spectre",
        "Le bord du bruit et la force critique, selon le nombre de couches "
        "suivies et de séances observées.",
        ["Couches k", "Séances N", "γ = k/N", "Bord λ₊",
         "Part de variance", "Force critique √γ",
         "N requis pour s = 0,30"],
        rows, wide=True,
        note="La part de variance est le bord rapporté au nombre de couches : "
             "c'est la fraction qu'un facteur commun doit expliquer pour que "
             "sa valeur propre sorte du bruit. La dernière colonne inverse la "
             "condition √γ < s pour un facteur de force trois dixièmes. Rien "
             "dans ces colonnes ne contient une propriété du marché : le seuil "
             "ne dépend que du nombre de choses regardées, rapporté au nombre "
             "de fois où on les a regardées.",
    )


TABLES = (table_footprint, table_tpo, table_bruit, table_spectre)


def all_tables() -> dict[str, Table]:
    return {fn().key: fn() for fn in TABLES}


def values() -> dict[str, str]:
    """Les scalaires que la partie cite."""
    loi_fp = fp.null_exhaustion()
    loi_tpo = tp.null_profile(tick=PAS_RANGEE, draws=500)
    fin = tp.null_profile(tick=0.25, draws=300)
    neutre = fp.synthesise("neutre")
    desq = fp.synthesise("desequilibre")
    absor = fp.synthesise("absorption")
    lam = fp.IMPACT_PER_ROOT_VOLUME
    table_grappe = dict(fp.null_imbalance_by_clump(
        NIVEAU_CONTRATS, NIVEAU_CONTRATS, (5, 20, 50)))
    declare = required_bits(q.RR_REF, 0.55)
    ouvert = required_bits(q.RR_REF, 0.11)
    return {
        # --- footprint ---
        "f_clump": num(fp.CLUMP_DEFAULT, 0),
        "f_niveau": num(NIVEAU_CONTRATS, 0),
        "f_grappe5": num(100 * table_grappe[5], 3, "%"),
        "f_grappe20": num(100 * table_grappe[20], 1, "%"),
        "f_grappe50": num(100 * table_grappe[50], 1, "%"),
        "f_attendu_neutre": num(fp.expected_imbalances(neutre), 2),
        "f_observe_desq": num(len(fp.diagonal_imbalances(desq)), 0),
        "f_z_absorption": num(fp.absorption_z(absor, lam), 2),
        "f_volume_absorption": num(absor.volume / neutre.volume, 1),
        "f_epuisement_q05": num(loi_fp.q05, 2),
        "f_epuisement_median": num(loi_fp.q50, 2),
        "f_epuisement_vu": num(fp.exhaustion_ratio(fp.synthesise("epuisement"), +1), 2),
        "f_ratio": num(fp.IMBALANCE_RATIO, 0),
        # --- profil TPO ---
        "t_rangee": num(PAS_RANGEE, 0),
        "t_extension": num(100 * loi_tpo.p_extension, 1, "%"),
        "t_pauvre_gros": num(100 * loi_tpo.p_poor_high, 0, "%"),
        "t_pauvre_fin": num(100 * fin.p_poor_high, 0, "%"),
        "t_facteur_pauvre": num(loi_tpo.p_poor_high / max(fin.p_poor_high, 1e-9), 0),
        "t_simples": num(loi_tpo.singles_mean, 1),
        "t_largeur": num(loi_tpo.value_width_mean, 2),
        "t_periodes": num(390.0 / tp.PERIOD_MIN, 0),
        # --- budget d'information ---
        "i_bits_declare": num(100 * declare.bits, 3, "%"),
        "i_bruit_declare": num(100 * (1.0 - declare.bits), 2, "%"),
        "i_bits_ouvert": num(100 * ouvert.bits, 3, "%"),
        "i_bruit_ouvert": num(100 * (1.0 - ouvert.bits), 3, "%"),
        "i_n_declare": num(trades_for_information(declare.bits), 0),
        "i_n_ouvert": num(trades_for_information(ouvert.bits), 0),
        "i_taux_nul": num(100 * declare.hit_null, 2, "%"),
        "i_taux_requis": num(100 * declare.hit_needed, 2, "%"),
        "i_hausse": num(100 * (declare.hit_needed / declare.hit_null - 1), 0, "%"),
        "i_facteur_n": num(trades_for_information(ouvert.bits)
                           / trades_for_information(declare.bits), 0),
        # --- spectre ---
        "x_couches": num(COUCHES, 0),
        "x_seances": num(SEANCES, 0),
        "x_gamma": num(COUCHES / SEANCES, 4),
        "x_edge": num(sp.mp_edges(COUCHES / SEANCES)[1], 3),
        "x_part": num(100 * sp.mp_edges(COUCHES / SEANCES)[1] / COUCHES, 1, "%"),
        "x_seuil": num(sp.bbp_threshold(COUCHES / SEANCES), 3),
        "x_lmax95": num(sp.null_spectrum(COUCHES, SEANCES, draws=260)
                        .lambda_max_q95, 3),
        "x_n_court": num(sp.observations_for_spike(0.30, COUCHES), 0),
    }


def main() -> None:
    for t in all_tables().values():
        print(t.caption)
        print(t.to_text())
        print(t.note)
        print()
    for k, v in values().items():
        print(f"  {k:22} {v}")
