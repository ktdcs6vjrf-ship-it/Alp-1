"""Tables des trois bornes venues d'ailleurs : information, physique, discipline.

Le document démontre qu'une géométrie ne crée pas d'espérance. Il lui manquait
les bornes symétriques — celles qui disent ce qu'un *signal* doit porter, ce
qu'un *instrument* peut voir, et ce qu'une *dérogation* détruit. Les trois
viennent de disciplines étrangères à la finance, se calculent sans aucune
donnée payante, et convergent sur un même constat.
"""

from __future__ import annotations

import math

from .discipline import SEALED_BUDGET, breaking_deviations, deviation_cost, grid
from .entropy import (
    kl_bernoulli,
    null_mutual_information,
    observations_for_bits,
    required_bits,
    trades_for_information,
)
from .nonlinear import EMBED, dfa, null_dfa, null_permutation, permutation_entropy
from .report import Table, num
from .report3 import year as _plain

#: Les deux frictions relatives du document, en rapport c/L.
C_OVER_L_V1 = 0.1100
C_OVER_L_V2 = 0.0143
RR_REF = 20.0

#: Espérance de l'edge de référence, en multiples du risque.
EDGE_R = 0.110

#: Le protocole scellé : cinq marchés, 1 260 séances, 1,113 entrée par séance.
SEALED_TRADES = 7012
SEALED_SR = 0.0332

#: Contrôle synthétique. Mêmes graine et longueur que partout ailleurs.
N_SESSIONS = 250
SEED = 20260821
NULL_DRAWS = 8


def _control():
    from .dataset import synthetic_sessions
    return synthetic_sessions(N_SESSIONS, seed=SEED)


def _edge_bits() -> float:
    """Information portée par l'edge de référence, en bits par trade."""
    q = 1.0 / (RR_REF + 1.0)
    return kl_bernoulli((EDGE_R + 1.0) / (RR_REF + 1.0), q)


# --- 1. Le plafond d'information --------------------------------------------


def table_information() -> Table:
    rows = []
    for nom, cl in (("ALP-1, stop de trois points", C_OVER_L_V1),
                    ("ALP-2, stop sur la bande", C_OVER_L_V2)):
        r = required_bits(RR_REF, cl)
        rows.append([
            nom,
            num(cl * 100, 2, "%"),
            num(r.hit_null * 100, 2, "%"),
            num(r.hit_needed * 100, 2, "%"),
            num(r.bits * 1e6, 1),
            num(trades_for_information(r.bits), 0),
        ])
    return Table(
        "information",
        "Information minimale qu'un signal doit porter pour rendre la "
        "géométrie rentable, et échantillon qu'il faut pour la décider.",
        ["Géométrie", "c/L", "Réussite sous martingale", "Réussite requise",
         "Bits requis (×10⁻⁶)", "Trades pour décider"],
        rows,
        wrap_cols=[0],
        wide=True,
        note="L'information se lit par l'identité de Kelly : le taux de "
             "croissance maximal d'un pari répété vaut l'information mutuelle "
             "entre signal et issue. Déplacer le taux de réussite de sa valeur "
             "martingale à sa valeur rentable coûte la divergence entre les "
             "deux lois de Bernoulli, et aucune géométrie ni aucun "
             "dimensionnement ne contourne ce prix. La géométrie d'ALP-2 "
             "divise l'exigence par "
             + num(required_bits(RR_REF, C_OVER_L_V1).bits
                   / required_bits(RR_REF, C_OVER_L_V2).bits, 1)
             + ", et multiplie par autant l'échantillon qui la décide : ce "
               "qu'elle rend facile à obtenir, elle le rend difficile à "
               "prouver.")


def table_three_routes() -> Table:
    bits = _edge_bits()
    rows = [
        ["Test t sur l'espérance par trade",
         "Statistique du résultat, loi supposée",
         num(17434, 0),
         "Puissance 80 % à 5 %, seuil déflaté à trois essais"],
        ["Seuil de sélection déflaté",
         "Maximum de trois essais sous l'hypothèse nulle",
         num(1993, 0),
         "Franchissement du seuil, sans exigence de puissance"],
        ["Test du rapport de vraisemblance sur la direction",
         "Information mutuelle, aucune loi supposée",
         num(trades_for_information(bits), 0),
         "Même niveau, même puissance, table 2 × 2"],
    ]
    return Table(
        "three_routes",
        "Trois routes indépendantes vers le même mur : l'échantillon qu'exige "
        "la dérive de référence, selon ce qu'on accepte de supposer.",
        ["Route", "Ce qu'elle suppose", "Trades requis", "Condition"],
        rows,
        wrap_cols=[0, 1, 3],
        wide=True,
        note="Les trois calculs ne partagent aucune hypothèse. Le premier "
             "suppose la loi du résultat ; le deuxième ne regarde que le "
             "maximum de trois tirages ; le troisième ne suppose rien de la "
             "loi et ne lit que le signe. Ils tombent dans un rapport de deux "
             "à un, ce qui n'est pas une coïncidence mais la marque d'une "
             "limite structurelle. La route informationnelle est la plus "
             "économe — lire la direction coûte "
             + num((1 - trades_for_information(bits) / 17434) * 100, 0)
             + " % de trades en moins que lire l'espérance, à décision égale.")


def table_mi_bias() -> Table:
    bits = _edge_bits()
    rows = []
    for n_obs in (500, 1000, 2000, 5000, 10000):
        nul = null_mutual_information(2, 2, n_obs, draws=200)
        rows.append([
            num(n_obs, 0),
            num(nul.mean * 1e6, 1),
            num(nul.q95 * 1e6, 1),
            num(bits * 1e6, 1),
            "oui" if bits > nul.q95 else "NON",
        ])
    return Table(
        "mi_bias",
        "Information mutuelle mesurée entre deux variables **indépendantes**, "
        "selon la taille d'échantillon, comparée à celle de l'edge de "
        "référence.",
        ["Observations", "Biais moyen (×10⁻⁶)", "Quantile 95 % (×10⁻⁶)",
         "Edge de référence (×10⁻⁶)", "Discernable"],
        rows,
        wide=True,
        note="La vérité de chaque ligne est zéro : les deux variables sont "
             "tirées indépendamment. L'estimateur par comptage rend pourtant "
             "une valeur positive, et elle dépasse l'information de l'edge "
             "tant que l'échantillon reste petit. C'est le même piège que "
             "celui du ratio de variance, sur un instrument entièrement "
             "différent — et c'est la raison pour laquelle aucune de ces "
             "mesures ne se lit sans sa loi nulle.")


# --- 2. Les deux mesures venues d'autres disciplines ------------------------


def table_nonlinear() -> Table:
    sessions = _control()
    rows = []
    for d in EMBED:
        pe = permutation_entropy(sessions, d)
        nul = null_permutation(d, n_sessions=N_SESSIONS, draws=NULL_DRAWS)
        deficit_nul = (1.0 - nul.mean) * math.log2(math.factorial(d))
        rows.append([
            f"Entropie de permutation, d = {d}",
            "Dynamique non linéaire, électroencéphalographie",
            num(pe.entropy, 6),
            num(nul.mean, 6),
            num(nul.z(pe.entropy), 2),
            num(deficit_nul * 1e6, 1),
        ])
    a = dfa(sessions)
    m, sd = null_dfa(n_sessions=N_SESSIONS, draws=max(4, NULL_DRAWS // 2))
    rows.append([
        "Fluctuations redressées (α)",
        "Physiologie, rythme cardiaque et séquences d'ADN",
        num(a.alpha, 4),
        num(m, 4),
        num((a.alpha - m) / sd if sd else 0.0, 2),
        "—",
    ])
    rows.append([
        "Ratio de variance (Ĥ), pour mémoire",
        "Économétrie financière",
        "0,5208",
        "0,5060",
        "—",
        "—",
    ])
    return Table(
        "nonlinear",
        "Deux instruments venus d'autres disciplines, appliqués à une série "
        "sans structure, et ce que chacun y voit.",
        ["Instrument", "Discipline d'origine", "Mesuré", "Sous marche aléatoire",
         "z", "Plancher (bits ×10⁻⁶)"],
        rows,
        wrap_cols=[0, 1],
        wide=True,
        rules_after=[2],
        note="La série est une marche aléatoire par construction : la réponse "
             "juste est « aucune structure », et les trois instruments la "
             "donnent une fois rapportés à leur loi nulle. L'écart entre les "
             "colonnes « mesuré » et « sous marche aléatoire » est le biais "
             "d'échantillon fini de chacun — et il est trois fois plus petit "
             "pour la méthode issue de la physiologie que pour celle issue de "
             "l'économétrie financière.")


def table_floor() -> Table:
    """Le tableau qui réunit les trois modules."""
    sessions = _control()
    bits_needed = required_bits(RR_REF, C_OVER_L_V2).bits
    rows = []
    for d in EMBED:
        nul = null_permutation(d, n_sessions=N_SESSIONS, draws=NULL_DRAWS)
        plancher = (1.0 - nul.mean) * math.log2(math.factorial(d))
        rows.append([
            f"Entropie de permutation, d = {d}",
            num(plancher * 1e6, 1),
            num(bits_needed * 1e6, 1),
            num(plancher / bits_needed, 1) + "×",
        ])
    nul_mi = null_mutual_information(2, 2, 1000, draws=200)
    rows.append([
        "Information mutuelle, 1 000 observations",
        num(nul_mi.mean * 1e6, 1),
        num(bits_needed * 1e6, 1),
        num(nul_mi.mean / bits_needed, 1) + "×",
    ])
    return Table(
        "floor",
        "Le plancher de bruit de chaque instrument, comparé à l'information "
        "que la géométrie d'ALP-2 exige d'un signal.",
        ["Instrument", "Plancher (bits ×10⁻⁶)", "Requis (bits ×10⁻⁶)",
         "Rapport"],
        rows,
        wrap_cols=[0],
        wide=True,
        note="Chaque plancher est ce que l'instrument affiche sur une série "
             "où il n'y a rien. Tous dépassent l'information que la stratégie "
             "réclame, d'un facteur de plusieurs dizaines. Ce n'est pas que "
             "l'avantage recherché soit petit : c'est qu'il est plus petit que "
             "le bruit propre des appareils qui devraient le voir. La "
             "conséquence est unique et elle vaut pour les trois — seul un "
             "échantillon très grand, ou une mesure agrégée sur beaucoup de "
             "trades, peut faire émerger le signal du plancher.")


# --- 3. La discipline, chiffrée en preuve -----------------------------------


def table_discipline() -> Table:
    rows = []
    for d in grid(SEALED_SR, SEALED_TRADES,
                  rates=(0.0, 0.0005, 0.001, 0.002, 0.005)):
        rows.append([
            num(d.rate * 100, 3, "%"),
            num(d.n_deviations, 1),
            f"{d.effective_trials:.3g}".replace(".", ",").replace("e+", "×10^"),
            num(d.threshold, 4),
            num(d.inflation, 2) + "×",
            "oui" if d.clears(SEALED_SR) else "NON",
        ])
    k = breaking_deviations(SEALED_SR, SEALED_TRADES)
    return Table(
        "discipline",
        "Ce qu'une dérogation à la règle scellée coûte au seuil de sélection, "
        "sur les " + num(SEALED_TRADES, 0) + " trades du protocole borné.",
        ["Taux de dérogation", "Dérogations", "Configurations explorées",
         "Seuil de sélection", "Inflation", "Le résultat tient"],
        rows,
        wrap_cols=[0],
        wide=True,
        note="Une dérogation n'est pas une erreur de plus dans l'échantillon : "
             "c'est un choix binaire pris en regardant le marché, donc une "
             "configuration supplémentaire explorée. La famille double à "
             "chaque fois, et le seuil de sélection croît comme la racine de "
             "son logarithme. Le point de rupture tombe à "
             + num(k, 1) + " dérogations, soit une tous les "
             + num(SEALED_TRADES / k if k else math.inf, 0)
             + " trades. C'est le seul paramètre de tout le document qui soit "
               "entièrement sous le contrôle de l'opérateur.")


def table_domains() -> Table:
    rows = [
        ["Théorie de l'information", "Kelly, Shannon",
         "Plafond de croissance = information mutuelle",
         "Nulle", "Immédiat",
         "Borne dure ; convertit le seuil en bits et donne un test de "
         "direction plus économe que le test d'espérance"],
        ["Dynamique non linéaire", "Bandt et Pompe",
         "Entropie de permutation des motifs ordinaux",
         "Nulle", "Minutes",
         "Sans modèle ni hypothèse de loi ; dit s'il reste une structure "
         "avant qu'un signal ne soit construit"],
        ["Physiologie et biophysique", "Peng et al.",
         "Fluctuations redressées, exposant α",
         "Nulle", "Minutes",
         "Trois fois moins biaisé que le ratio de variance sur des séances "
         "courtes ; remplace l'estimateur d'exposant du protocole"],
        ["Économie du comportement", "Lo et Repin ; Coates et Herbert",
         "Déterminants du taux de dérogation",
         "Nulle", "Continu",
         "Ne crée aucune dérive ; agit sur le seul paramètre que l'opérateur "
         "contrôle, et le point de rupture est bas"],
        ["Microstructure statistique", "Bouchaud et al.",
         "Noyau d'impact et mémoire du flux",
         "Élevée (carnet)", "Semaines",
         "Déjà exploitée par le document ; ferme la persistance du prix "
         "plutôt qu'elle ne l'ouvre"],
    ]
    return Table(
        "domains",
        "Les domaines extérieurs à la finance évalués pour ce document, et ce "
        "que chacun apporte au critère maître.",
        ["Domaine", "Travaux", "Ce qu'il fournit", "Coût des données",
         "Délai", "Ce qu'il change ici"],
        rows,
        wrap_cols=[0, 1, 2, 5],
        wide=True,
        note="Le classement est par rapport entre ce qu'un domaine décide et "
             "ce qu'il coûte. Les quatre premiers ne demandent aucune donnée "
             "que le protocole n'ait déjà, et les trois premiers tournent sur "
             "les mêmes barres d'une minute. Le cinquième est le seul à "
             "exiger une dépense, et il est aussi le seul dont la conclusion "
             "va contre la stratégie.")


TABLES = [table_information, table_three_routes, table_mi_bias,
          table_nonlinear, table_floor, table_discipline, table_domains]


def all_tables() -> dict[str, Table]:
    return {fn().key: fn() for fn in TABLES}


def values() -> dict[str, str]:
    sessions = _control()
    r1 = required_bits(RR_REF, C_OVER_L_V1)
    r2 = required_bits(RR_REF, C_OVER_L_V2)
    bits = _edge_bits()
    nul3 = null_permutation(3, n_sessions=N_SESSIONS, draws=NULL_DRAWS)
    plancher3 = (1.0 - nul3.mean) * math.log2(6)
    a = dfa(sessions)
    m_dfa, sd_dfa = null_dfa(n_sessions=N_SESSIONS,
                             draws=max(4, NULL_DRAWS // 2))
    k = breaking_deviations(SEALED_SR, SEALED_TRADES)
    nul_mi = null_mutual_information(2, 2, 1000, draws=200)

    return {
        # information
        "inf_bits_v1": num(r1.bits * 1e6, 1),
        "inf_bits_v2": num(r2.bits * 1e6, 1),
        "inf_factor": num(r1.bits / r2.bits, 1),
        "inf_edge_bits": num(bits * 1e6, 1),
        "inf_n_route": num(trades_for_information(bits), 0),
        "inf_n_sharpe": num(17434, 0),
        "inf_gain": num((1 - trades_for_information(bits) / 17434) * 100, 0),
        "inf_mi_bias": num(nul_mi.mean * 1e6, 1),
        "inf_hit_v2": num(r2.hit_needed * 100, 2),
        "inf_hit_null": num(r2.hit_null * 100, 2),

        # non linéaire
        "nl_pe3": num(permutation_entropy(sessions, 3).entropy, 6),
        "nl_pe3_null": num(nul3.mean, 6),
        "nl_pe3_floor": num(plancher3 * 1e6, 1),
        "nl_pe3_ratio": num(plancher3 / r2.bits, 1),
        "nl_dfa": num(a.alpha, 4),
        "nl_dfa_null": num(m_dfa, 4),
        "nl_dfa_bias": num(abs(m_dfa - 0.5), 4),
        "nl_vr_bias": num(0.5208 - 0.5, 4),
        "nl_bias_factor": num((0.5208 - 0.5) / abs(m_dfa - 0.5), 1),

        # discipline
        "disc_trades": num(SEALED_TRADES, 0),
        "disc_break": num(k, 1),
        "disc_break_every": num(SEALED_TRADES / k if k else math.inf, 0),
        "disc_rate": num(k / SEALED_TRADES * 100, 3),
        "disc_budget": num(SEALED_BUDGET, 0),
        "disc_infl_10": num(deviation_cost(10.0 / SEALED_TRADES,
                                           SEALED_TRADES).inflation, 2),
    }


def main() -> None:
    for i, fn in enumerate(TABLES, start=1):
        t = fn()
        print(f"\n### Table {i} — {t.caption}\n")
        print(t.to_text())
    print("\n\nValeurs\n")
    for k, v in sorted(values().items()):
        print(f"  {k:18} {v}")


if __name__ == "__main__":
    main()
