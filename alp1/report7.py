"""Tables de la sixième partie : le témoin, le catalogue, l'opérateur.

Trois questions qu'un opérateur pose avant d'engager du capital, et auxquelles
le document ne répondait pas. Un signal diffusé en direct vaut-il quelque
chose à l'instant `t` ? La littérature offre-t-elle d'autres dérives que celle
qui est empruntée, et combien peut-on en assembler ? Un talent discrétionnaire
qui ne se formule pas peut-il malgré tout se mesurer ?

Les trois réponses sortent du même cadre que le reste du document — critère
maître, loi nulle, plafond d'information, coût de la sélection — et aucune
n'exige de données payantes.
"""

from __future__ import annotations

import math

from .broadcast import (
    FINFLUENCER_PRIOR,
    HALF_LIFE_GRID_S,
    LATENCY_BOX_S,
    Call,
    Ledger,
    best_of_crowd,
    crowd_threshold_calls,
    deletion_explaining,
    deletions_per_loss,
    evaluate,
    hit_rate_of_crowd,
    latency_factor,
    min_half_life,
    posterior_after_screen,
    tolerated_delay,
)
from .discret import (
    RHO_BOX,
    declaration_gain,
    deviation_families,
    detectable_talent,
    pairs_for_talent,
    plan,
    variance_reduction,
)
from .litedge import (
    ASOF,
    CATALOGUE,
    CATALOGUE_BY_KEY,
    FRICTION_BPS,
    GEOM_ALP1,
    GEOM_ALP2,
    compatible,
    effective_pieces,
    entry_threshold,
    implied_second_half_sharpe,
    independent_families,
    optimal_pieces,
    selection_threshold,
)
from .report import Table, num
from .report3 import year as _plain

#: Trades du protocole scellé, et séances de son budget. Les deux nombres sont
#: ceux de la quatrième partie ; ils fixent ici les seuils d'entrée.
SEALED_TRADES = 7012
SEALED_SESSIONS = 1260

#: Rapport de la dérive de l'émetteur au seuil de rentabilité, pour la
#: frontière de latence. Le document retient déjà `µ = 2µ*` comme edge de
#: référence ; la grille encadre.
RATIO_GRID = (1.5, 2.0, 3.0, 10.0)

#: Nombre de diffuseurs regardés, pour la loi nulle du classement.
CROWD_GRID = (1, 10, 50, 200, 1000)

#: Appels par an d'un diffuseur assidu : cinq par direct, deux cents directs.
CALLS_PER_YEAR = 1000.0

#: Ratio de Sharpe publié par le travail de 2024 sur l'échantillon complet.
#: Sert de point d'appui au prédicat de décote, non de mesure du dépôt.
PUBLISHED_SHARPE = 1.33
PUBLISHED_POST_YEARS = 6.0


def _families_best():
    """Une pièce par famille compatible : la meilleure de sa famille."""
    g = GEOM_ALP2
    best = {}
    for c in compatible():
        f = c.family or c.key
        if f not in best or c.information_ratio(g) > best[f].information_ratio(g):
            best[f] = c
    return list(best.values())


# --- Le témoin ---------------------------------------------------------------

def table_latency() -> Table:
    rows = []
    etiquettes = {3.0: "flux de carnet", 60.0: "motif d'une barre",
                  1800.0: "motif de séance", 23400.0: "thèse de journée"}
    for h in HALF_LIFE_GRID_S:
        rows.append([etiquettes[h], num(h, 0, "s")]
                    + [num(latency_factor(d, h) * 100, 2, "%")
                       for d in LATENCY_BOX_S])
    return Table(
        key="tmn_latence",
        caption="Ce qu'un direct laisse arriver : part de l'information "
                "survivant au délai de diffusion",
        headers=["Nature du signal", "Demi-vie"]
                + [f"Δ = {int(d)} s" for d in LATENCY_BOX_S],
        rows=rows,
        note="Le facteur vaut 2^(−Δ/h) et **factorise exactement** la dérive "
             "captée : le délai n'altère pas le profil de décroissance, il le "
             "multiplie. Un signal de flux, celui que la lecture de carnet "
             "prétend fournir, arrive au spectateur amputé de 90 % au délai "
             "médian et de 99,9 % au délai haut.",
        wrap_last=False,
    )


def table_frontier() -> Table:
    rows = []
    for r in RATIO_GRID:
        rows.append([f"µ = {num(r, 1)}·µ*"]
                    + [num(min_half_life(d, r), 1, "s") for d in LATENCY_BOX_S]
                    + [num(tolerated_delay(60.0, r), 1, "s")])
    return Table(
        key="tmn_frontiere",
        caption="La frontière de recopiabilité : demi-vie minimale du signal, "
                "et délai toléré",
        headers=["Qualité de l'émetteur"]
                + [f"h* à Δ = {int(d)} s" for d in LATENCY_BOX_S]
                + ["Δ toléré à h = 60 s"],
        rows=rows,
        note="`h* = Δ·ln 2 / ln(µ/µ*)`. À dérive exactement double du seuil, "
             "la demi-vie minimale **égale le délai** — l'égalité est fortuite "
             "et commode. La frontière diverge quand l'émetteur s'approche de "
             "son propre seuil : plus il est juste rentable, plus son signal "
             "doit être lent pour supporter le trajet.",
    )


def table_crowd() -> Table:
    rows = []
    for k in CROWD_GRID:
        n = 200
        rows.append([
            _plain(k),
            num(best_of_crowd(k, n), 4),
            num(hit_rate_of_crowd(k, n) * 100, 2, "%"),
            num(crowd_threshold_calls(k, 0.05), 0),
            num(crowd_threshold_calls(k, 0.05) / CALLS_PER_YEAR, 2, "an"),
        ])
    return Table(
        key="tmn_foule",
        caption="La loi nulle du classement : ce que le meilleur de K "
                "diffuseurs sans aucun talent affiche",
        headers=["Diffuseurs regardés", "Sharpe/appel du meilleur",
                 "Taux affiché", "Appels pour trancher", "Durée de collecte"],
        rows=rows,
        note="Colonnes 2 et 3 : sur 200 appels chacun et **aucun talent**, le "
             "meilleur d'une centaine de diffuseurs affiche six réussites sur "
             "dix. Colonnes 4 et 5 : appels nécessaires pour établir un "
             "avantage de cinq points au rang où le diffuseur est lu, seuil "
             "corrigé par le nombre de candidats, à raison de mille appels "
             "enregistrés par an.",
    )


def table_deletion() -> Table:
    grille = ((0.50, "appel directionnel jugé au signe"),
              (1.0 / 21.0, "géométrie 1:20 d'ALP-1"))
    rows = []
    for p0, quoi in grille:
        for lift in (1.11, 1.20, 1.40):
            pobs = min(p0 * lift, 0.999)
            rows.append([
                quoi, num(p0 * 100, 2, "%"), num(pobs * 100, 2, "%"),
                num(deletion_explaining(p0, pobs) * 100, 1, "%"),
                num(deletions_per_loss(p0, pobs), 1),
            ])
    return Table(
        key="tmn_effacement",
        caption="Ce qu'il suffit d'effacer : fraction des appels perdants qui "
                "reproduit à elle seule le taux affiché",
        headers=["Lecture de l'issue", "Taux sous prix sans dérive",
                 "Taux affiché", "Fraction effacée", "Un perdant sur"],
        rows=rows,
        rules_after=[3],
        note="Aucune intention n'est supposée : un direct interrompu, un "
             "récapitulatif qui ne retient que ce qui mérite un commentaire, "
             "et un effacement délibéré produisent la même arithmétique. La "
             "ligne à retenir est la première du second bloc : **un appel "
             "perdant effacé sur dix suffit à fabriquer l'intégralité de "
             "l'avantage que la géométrie 1:20 exige.** C'est pourquoi seule "
             "une collecte prospective et horodatée à la réception est "
             "recevable.",
    )


def table_screen() -> Table:
    rows = []
    for side, quoi in (("long", "suivre le talent"),
                       ("short", "prendre le talent négatif à contre-pied")):
        for n in (6.0, 12.0, 36.0):
            s = posterior_after_screen(n_months=n, side=side)
            rows.append([
                quoi, num(n, 0, "mois"),
                num(s.posterior.talent * 100, 1, "%"),
                num(s.posterior.antitalent * 100, 1, "%"),
                num(s.per_thousand, 1),
            ])
    return Table(
        key="tmn_filtre",
        caption="Les deux sens de recherche, jugés sur les taux de base publiés",
        headers=["Sens du filtre", "Observation", "P(talent sachant retenu)",
                 "P(talent négatif sachant retenu)",
                 "Retenus pour mille examinés"],
        rows=rows,
        rules_after=[3],
        wrap_cols=[0],
        note=f"Taux de base : {num(FINFLUENCER_PRIOR['talent'] * 100, 0, '%')} "
             f"de talent, {num(FINFLUENCER_PRIOR['neutre'] * 100, 0, '%')} de "
             f"neutres, {num(FINFLUENCER_PRIOR['antitalent'] * 100, 0, '%')} "
             f"de talent négatif "
             "(Kakhbod et al. 2023). La puissance du filtre sur chaque type "
             "n'est pas posée : elle se déduit de l'alpha publié pour ce type. "
             "Le filtre inverse gagne sur les deux tableaux — loi a posteriori "
             "plus pure **et** rendement plus élevé — parce qu'il vise la "
             "classe majoritaire.",
    )


# --- Le catalogue ------------------------------------------------------------

def table_catalogue() -> Table:
    rows = []
    for c in CATALOGUE:
        rows.append([
            c.name,
            _plain(c.year),
            _plain(c.dating_year()),
            num(c.surviving_bps(), 2),
            num(c.net_for(GEOM_ALP1), 3, signed=True),
            num(c.net_for(GEOM_ALP2), 3, signed=True),
            num(c.information_ratio(GEOM_ALP2), 5, signed=True),
            str(c.data_cost),
            "oui" if c.compatible() else "non",
        ])
    return Table(
        key="lit_catalogue",
        caption=f"Neuf dérives documentées, mesurées au critère maître du "
                f"document, en {_plain(ASOF)}",
        headers=["Effet", "Publié", "Daté de", "Restant (pdb)",
                 "Net ALP-1 (pdb)", "Net ALP-2 (pdb)", "IR/occurrence",
                 "Coût données", "Compatible"],
        rows=rows,
        wrap_cols=[0],
        wide=True,
        note=f"« Daté de » est l'année de **première** parution de l'effet, "
             f"toutes signatures confondues : republier un résultat ne remet "
             f"pas le compteur de la décote à zéro. Le net retranche la "
             f"friction déduite du carnet, {num(FRICTION_BPS, 3)} pdb par "
             f"aller-retour. Le coût de données va de 0 — barres d'une minute "
             f"d'un contrat, gratuites — à 3 — section transversale de "
             f"milliers de titres, emprunt compris.",
    )


def table_gates() -> Table:
    n = len(CATALOGUE)
    mandat = [c for c in CATALOGUE if c.mandate == "intraseance"]
    cout = [c for c in mandat if c.retail()]
    positif = [c for c in cout if c.net_for(GEOM_ALP2) > 0.0]
    familles = len(independent_families(positif))
    rows = [
        ["Documenté, taille d'effet publiée", _plain(n), "—"],
        ["Porte de mandat : sortie à la clôture", _plain(len(mandat)),
         f"−{n - len(mandat)}"],
        ["Porte de coût : accessible au détail", _plain(len(cout)),
         f"−{len(mandat) - len(cout)}"],
        ["Porte du critère maître : net positif", _plain(len(positif)),
         f"−{len(cout) - len(positif)}" if cout != positif else "—"],
        ["Familles distinctes après regroupement", _plain(familles),
         f"−{len(positif) - familles}"],
    ]
    return Table(
        key="lit_portes",
        caption="Les quatre portes, et ce qui reste après chacune",
        headers=["Porte", "Candidats restants", "Éliminés"],
        rows=rows,
        note="La dernière ligne est la seule qui compte : les trois entrées "
             "qui survivent sont **trois énoncés d'un même effet**, et la "
             "corrélation entre publications d'un même résultat vaut un. Le "
             "catalogue de la littérature ouverte offre à cette géométrie une "
             "pièce, et c'est celle que le document emprunte déjà.",
    )


def table_timeconstant() -> Table:
    rows = []
    for key in ("mim_us", "bande_bruit", "prefomc", "antitalent"):
        c = CATALOGUE_BY_KEY[key]
        rows.append([
            c.name, num(c.horizon_min, 0, "min"),
            num(c.captured_for(GEOM_ALP1), 3),
            num(c.captured_for(GEOM_ALP2), 3),
            num(c.captured_for(GEOM_ALP2) / max(c.captured_for(GEOM_ALP1), 1e-9), 2),
        ])
    return Table(
        key="lit_constantes",
        caption="L'appariement des constantes de temps : ce que chaque "
                "géométrie capte du même effet",
        headers=["Effet", "Horizon de l'effet",
                 f"Capté à {num(GEOM_ALP1.exposure_min, 1)} min (pdb)",
                 f"Capté à {num(GEOM_ALP2.exposure_min, 1)} min (pdb)",
                 "Rapport"],
        rows=rows,
        wrap_cols=[0],
        note="Le résultat n'était pas prévu par le document et corrige l'une "
             "de ses lectures. **Une exposition plus longue n'achète de la "
             "dérive que sur un effet plus long qu'elle.** Sur un effet de "
             "trente minutes, les 165 minutes d'ALP-2 ne captent rien de plus "
             "que les 29 d'ALP-1 ; sur un effet de trois heures, elles "
             "captent près de six fois plus. La géométrie et l'effet doivent "
             "avoir des constantes de temps appariées, et c'est un critère de "
             "compatibilité plus sévère que le mandat.",
    )


def table_assembly() -> Table:
    from .litedge import assembly_scan
    irs = [c.information_ratio(GEOM_ALP2) for c in CATALOGUE if
           c.information_ratio(GEOM_ALP2) > 0.0]
    rows = []
    for a in assembly_scan(irs, SEALED_TRADES):
        rows.append([
            _plain(a.k), num(a.ir_gross, 5), num(a.estimation_cost, 6),
            num(a.search_cost, 5), num(max(a.ir_net, 0.0), 5),
        ])
    return Table(
        key="lit_assemblage",
        caption=f"Le bilan de l'assemblage sur les {num(SEALED_TRADES, 0)} "
                f"trades du protocole scellé",
        headers=["Pièces retenues", "IR brut", "Coût d'estimation (IR²)",
                 "Coût de fouille (IR)", "IR net"],
        rows=rows,
        note=f"Le coût d'estimation vaut `k/N` en IR au carré — une unité par "
             f"poids ajusté. Le coût de fouille est celui de **choisir** le "
             f"sous-ensemble en regardant les données, `√(2 ln C(m,k)/N)` ; il "
             f"s'annule quand on prend tout, parce que prendre tout n'est pas "
             f"un choix. Les deux lectures s'opposent proprement : sur un jeu "
             f"déclaré d'avance, une seule pièce est optimale ; sur un jeu "
             f"choisi, la fouille coûte plus que le catalogue entier ne "
             f"contient.",
    )


def table_entry() -> Table:
    pieces = _families_best()
    ir = pieces[0].information_ratio(GEOM_ALP2) if pieces else 0.0
    rows = []
    for n, quoi in ((SEALED_SESSIONS, "budget en séances du protocole"),
                    (SEALED_TRADES, "trades du protocole scellé"),
                    (20000, "vingt mille trades")):
        a = optimal_pieces([ir], n)
        garde = a.ir_net / ir * 100 if ir > 0 else 0.0
        rows.append([
            quoi, num(n, 0), num(entry_threshold(n), 5), num(ir, 5),
            "oui" if ir > entry_threshold(n) else "non",
            num(max(garde, 0.0), 1, "%"),
        ])
    return Table(
        key="lit_entree",
        caption="Le seuil d'entrée d'une pièce, et ce que l'ajustement de son "
                "poids en consomme",
        headers=["Échantillon", "N", "Seuil 1/√N", "IR de la pièce",
                 "Admise", "Information conservée"],
        rows=rows,
        wrap_cols=[0],
        note="Le critère d'entrée est frappant par ce qu'il ne contient pas : "
             "ni le nombre de pièces déjà retenues, ni leur qualité, ni leur "
             "corrélation. **Une pièce mérite sa place si et seulement si son "
             "ratio d'information dépasse `1/√N`.** L'unique pièce compatible "
             "du catalogue franchit ce seuil d'un cheveu sur l'échantillon du "
             "protocole, et pas du tout sur le budget en séances.",
    )


def table_dating() -> Table:
    rows = []
    for key in ("mim_us", "mim_intl", "bande_bruit"):
        c = CATALOGUE_BY_KEY[key]
        pub = c.surviving_bps(dating="publication")
        fam = c.surviving_bps(dating="famille")
        rows.append([
            c.reference.split(",")[0] + " et al.", _plain(c.year),
            num(pub, 3), num(fam, 3), num(pub / fam, 2),
        ])
    return Table(
        key="lit_datation",
        caption="Ce que la convention de datation change à la dérive restante",
        headers=["Travail", "Année", "Daté de sa parution (pdb)",
                 "Daté de la famille (pdb)", "Rapport"],
        rows=rows,
        wrap_cols=[0],
        note="La convention n'est pas un détail de présentation : elle fait "
             "varier la dérive restante d'un facteur 2,8 sur le même effet, "
             "davantage que la marge que le document conserve sur son point "
             "de rupture. La convention retenue ici est la plus sévère — "
             "l'arbitrage répond à la première parution — et c'est celle qui "
             "avance la date d'échéance.",
    )


def table_oos() -> Table:
    rows = []
    for taux, quoi in ((0.0, "aucune décote (Jacobs et Müller)"),
                       (0.061, "seuil de détectabilité du protocole"),
                       (0.174, "décote documentée, McLean et Pontiff"),
                       (0.290, "borne haute de la boîte")):
        rows.append([
            quoi, num(taux * 100, 1, "%/an"),
            num(implied_second_half_sharpe(PUBLISHED_SHARPE,
                                           PUBLISHED_POST_YEARS, taux), 2),
        ])
    return Table(
        key="lit_hors_echantillon",
        caption="Le prédicat de décote, publié avant d'être lu",
        headers=["Hypothèse de décote", "Taux annuel",
                 "Sharpe impliqué sur la fenêtre postérieure"],
        rows=rows,
        wrap_cols=[0],
        note=f"Un travail publié en 2024 sur un échantillon qui court jusqu'en "
             f"2024 constitue, pour un effet paru en 2018, un test hors "
             f"échantillon de l'hypothèse de décote. Le dépôt ne dispose pas "
             f"du Sharpe scindé qui trancherait ; il publie donc ce que chaque "
             f"taux impliquerait sur les {num(PUBLISHED_POST_YEARS, 0)} années "
             f"postérieures, à partir du Sharpe d'ensemble publié "
             f"({num(PUBLISHED_SHARPE, 2)}). Le nombre, le jour où il est lu, "
             f"tranchera sans qu'on puisse ajuster la théorie après coup.",
    )


# --- L'opérateur --------------------------------------------------------------

def table_paired() -> Table:
    rows = []
    for rho in RHO_BOX:
        d = plan(delta=0.05, sd=0.431, rho=rho, budget_sessions=SEALED_SESSIONS)
        rows.append([
            num(rho, 2),
            num(variance_reduction(rho), 2),
            num(d.n_pairs, 0),
            num(d.years, 2, "an"),
            num(d.detectable, 4, "R"),
        ])
    return Table(
        key="ope_apparie",
        caption="Le dispositif apparié : ce que la variance commune fait "
                "gagner",
        headers=["Corrélation des bras", "Gain d'échantillon",
                 "Séances pour détecter 0,05 R", "Durée",
                 "Écart détectable en 1 260 séances"],
        rows=rows,
        note="La dispersion par trade est celle de la géométrie ALP-2, "
             "déduite du couple publié par le document. Le gain vaut "
             "`1/(1 − ρ)`, et les deux bras affrontent la même séance aux "
             "mêmes heures : `ρ` est élevé par construction. Le second "
             "avantage ne se lit pas dans cette table et pèse davantage — "
             "**la dérive commune s'élimine dans la différence**, donc la "
             "question reste décidable après la péremption de la dérive "
             "empruntée.",
    )


def table_declaration() -> Table:
    rows = []
    for k in (1, 2, 4, 8, 16):
        rows.append([
            _plain(k),
            num(deviation_families(float(k)), 0),
            _plain(1),
            num(declaration_gain(float(k)), 0),
        ])
    return Table(
        key="ope_declaration",
        caption="Le même geste, selon la date à laquelle il est déclaré",
        headers=["Écarts à la règle", "Famille si dérogation",
                 "Famille si bras déclaré", "Rapport"],
        rows=rows,
        note="Une dérogation est un choix binaire pris en regardant le "
             "marché : la famille de configurations double à chaque fois. Le "
             "même écart, **déclaré d'avance comme un second bras**, coûte une "
             "comparaison et une seule. La différence entre un talent et une "
             "indiscipline n'est pas dans le geste : elle est dans la date à "
             "laquelle il a été déclaré.",
    )


def table_operator_bound() -> Table:
    rows = []
    for extra, quoi in ((0.5, "une entrée sur deux séances"),
                        (1.0, "une entrée par séance"),
                        (3.0, "trois entrées par séance")):
        cov = extra * FRICTION_BPS
        rows.append([
            quoi, num(extra, 1), num(cov, 3),
            num(cov / GEOM_ALP2.stop_bps(), 5, "R"),
            num(cov * 252.0 / 100.0, 2, "%"),
        ])
    return Table(
        key="ope_borne",
        caption="Ce qu'un talent doit produire pour valoir ses allers-retours",
        headers=["Cadence ajoutée à la règle", "Entrées/séance",
                 "Covariance requise (pdb)", "En multiples du risque",
                 "Par an"],
        rows=rows,
        wrap_cols=[0],
        note="Dans ce cadre, un talent discrétionnaire est **exactement** la "
             "covariance entre la dérive locale et l'exposition choisie : "
             "`E[R] = E[µ]·E[τ] + Cov(µ, τ) − c`. Le premier terme est ce que "
             "la règle obtient déjà ; tout l'écart tient dans le second. La "
             "conséquence est double et il faut la dire entière : le talent "
             "se mesure **sans être décrit**, et il ne fabrique pas de dérive, "
             "il en répartit une.",
    )


TABLES = [table_latency, table_frontier, table_crowd, table_deletion,
          table_screen, table_catalogue, table_gates, table_timeconstant,
          table_entry, table_assembly, table_dating, table_oos,
          table_paired, table_declaration, table_operator_bound]


def all_tables() -> dict[str, Table]:
    return {fn().key: fn() for fn in TABLES}


def values() -> dict[str, str]:
    from .litedge import assembly_scan

    pieces = _families_best()
    ir = pieces[0].information_ratio(GEOM_ALP2) if pieces else 0.0
    seule = optimal_pieces([ir], SEALED_TRADES)
    irs_pos = [c.information_ratio(GEOM_ALP2) for c in CATALOGUE
               if c.information_ratio(GEOM_ALP2) > 0.0]
    fouille = selection_threshold(len(irs_pos), 1, SEALED_TRADES)
    mim = CATALOGUE_BY_KEY["mim_us"]
    bb = CATALOGUE_BY_KEY["bande_bruit"]
    ecran_l = posterior_after_screen(n_months=12.0, side="long")
    ecran_s = posterior_after_screen(n_months=12.0, side="short")
    intraseance = [c for c in CATALOGUE if c.mandate == "intraseance"]

    return {
        # témoin
        "tmn_delai_med": num(LATENCY_BOX_S[1], 0),
        "tmn_delai_haut": num(LATENCY_BOX_S[2], 0),
        "tmn_reste_flux": num(latency_factor(LATENCY_BOX_S[1], 3.0) * 100, 1),
        "tmn_perte_flux": num((1 - latency_factor(LATENCY_BOX_S[1], 3.0)) * 100, 1),
        "tmn_reste_seance": num(latency_factor(LATENCY_BOX_S[1], 1800.0) * 100, 1),
        "tmn_hstar_med": num(min_half_life(LATENCY_BOX_S[1], 2.0), 1),
        "tmn_foule_taux": num(hit_rate_of_crowd(100, 200) * 100, 1),
        "tmn_foule_sr": num(best_of_crowd(100, 200), 4),
        "tmn_appels_seul": num(crowd_threshold_calls(1, 0.05), 0),
        "tmn_appels_50": num(crowd_threshold_calls(50, 0.05), 0),
        "tmn_annees_50": num(crowd_threshold_calls(50, 0.05) / CALLS_PER_YEAR, 1),
        "tmn_effacement": num(deletion_explaining(0.5, 0.55) * 100, 1),
        "tmn_effacement_un": num(deletions_per_loss(0.5, 0.55), 1),
        "tmn_effacement_a1": num(deletion_explaining(1 / 21, 1.11 / 21) * 100, 1),
        "tmn_effacement_a1_un": num(deletions_per_loss(1 / 21, 1.11 / 21), 1),
        "tmn_post_long": num(ecran_l.posterior.talent * 100, 1),
        "tmn_post_short": num(ecran_s.posterior.antitalent * 100, 1),
        "tmn_rendement_long": num(ecran_l.per_thousand, 1),
        "tmn_rendement_short": num(ecran_s.per_thousand, 1),
        "tmn_rendement_gain": num(
            (ecran_s.retained / ecran_l.retained - 1.0) * 100, 0),
        "tmn_prior_anti": num(FINFLUENCER_PRIOR["antitalent"] * 100, 0),
        "tmn_prior_talent": num(FINFLUENCER_PRIOR["talent"] * 100, 0),

        # catalogue
        "lit_n": num(len(CATALOGUE), 0),
        "lit_intraseance": num(len(intraseance), 0),
        "lit_compatibles": num(len(compatible()), 0),
        "lit_familles": num(effective_pieces(compatible()), 0),
        "lit_friction_bps": num(FRICTION_BPS, 3),
        "lit_mim_restant": num(mim.surviving_bps(), 2),
        "lit_mim_net2": num(mim.net_for(GEOM_ALP2), 3),
        "lit_mim_net1": num(mim.net_for(GEOM_ALP1), 3),
        "lit_mim_ir": num(ir, 5),
        "lit_mim_an": num(mim.net_for(GEOM_ALP2) * 252 / 100, 2),
        "lit_seuil_7012": num(entry_threshold(SEALED_TRADES), 5),
        "lit_seuil_1260": num(entry_threshold(SEALED_SESSIONS), 5),
        "lit_conserve": num(max(seule.ir_net, 0.0) / ir * 100 if ir else 0.0, 1),
        "lit_consomme": num(100 - (max(seule.ir_net, 0.0) / ir * 100 if ir else 0.0), 1),
        "lit_fouille": num(fouille, 4),
        "lit_fouille_rapport": num(fouille / ir if ir else math.inf, 1),
        "lit_datation_rapport": num(
            bb.surviving_bps(dating="publication") / bb.surviving_bps(), 2),
        "lit_bb_capt1": num(bb.captured_for(GEOM_ALP1), 3),
        "lit_bb_capt2": num(bb.captured_for(GEOM_ALP2), 3),
        "lit_bb_rapport": num(
            bb.captured_for(GEOM_ALP2) / bb.captured_for(GEOM_ALP1), 1),
        "lit_mim_rapport": num(
            mim.captured_for(GEOM_ALP2) / mim.captured_for(GEOM_ALP1), 2),
        "lit_sharpe_pub": num(PUBLISHED_SHARPE, 2),
        "lit_sharpe_174": num(implied_second_half_sharpe(
            PUBLISHED_SHARPE, PUBLISHED_POST_YEARS, 0.174), 2),

        # opérateur
        "ope_gain_08": num(variance_reduction(0.80), 1),
        "ope_gain_09": num(variance_reduction(RHO_BOX[2]), 0),
        "ope_seances_07": num(
            pairs_for_talent(0.05, 0.431, RHO_BOX[1]), 0),
        "ope_annees_07": num(
            pairs_for_talent(0.05, 0.431, RHO_BOX[1]) / 252.0, 2),
        "ope_detectable": num(
            detectable_talent(SEALED_SESSIONS, 0.431, RHO_BOX[1]), 4),
        "ope_declaration_4": num(declaration_gain(4.0), 0),
        "ope_cov_requise": num(FRICTION_BPS, 3),
        "ope_cov_an": num(FRICTION_BPS * 252 / 100, 2),
    }


def _demo_ledger() -> Ledger:
    """Un registre de démonstration : douze appels, issues de vérité connue.

    Il ne mesure aucun diffuseur. Il sert à ce que la chaîne d'évaluation soit
    exécutable et vérifiable sans qu'aucune donnée réelle n'existe, comme
    partout ailleurs dans le dépôt.
    """
    issues = [1.0, -1.0, 1.0, -1.0, -1.0, 1.0, -1.0, 1.0, -1.0, -1.0, 1.0, -1.0]
    reg = Ledger("demonstration")
    for i, r in enumerate(issues):
        reg.add(Call(ts=1.0e9 + 600.0 * i, pseudo="demonstration",
                     instrument="ES", side=1 if i % 2 == 0 else -1,
                     outcome=r, source="direct"))
    return reg


def main(pseudo: str | None = None) -> None:
    if pseudo:
        from pathlib import Path

        from .broadcast import from_csv
        chemin = Path(pseudo)
        if chemin.exists():
            registres = from_csv(chemin.read_text(encoding="utf-8"))
        else:
            registres = {"demonstration": _demo_ledger()}
            print("Aucun fichier de ce nom : registre de démonstration.\n")
        for nom, reg in sorted(registres.items()):
            v = evaluate(reg, n_broadcasters=max(len(registres), 1))
            print(f"### {nom} — {v.n_calls} appels résolus\n")
            print(f"  taux affiché              {v.hit_rate:.1%}")
            print(f"  loi nulle                 {v.p_null:.1%}")
            print(f"  seuil du classement       {v.crowd_hit_rate:.1%}")
            for etiquette, valeur in (("appels requis, seul", v.calls_alone),
                                      ("appels requis, au rang",
                                       v.calls_in_crowd)):
                rendu = "—" if valeur == math.inf else f"{valeur:,.0f}"
                print(f"  {etiquette:25} {rendu}")
            print(f"  effacement suffisant      {v.deletion_explaining:.1%}")
            print(f"  demi-vie minimale         {v.min_half_life_s:.1f} s")
            for d in v.defauts:
                print(f"  défaut : {d}")
            print(f"\n  {v.reading()}\n")
        return

    for i, fn in enumerate(TABLES, start=1):
        t = fn()
        print(f"\n### Table {i} — {t.caption}\n")
        print(t.to_text())
    print("\n\nValeurs\n")
    for k, v in sorted(values().items()):
        print(f"  {k:22} {v}")


if __name__ == "__main__":
    main()
