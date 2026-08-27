"""Tables et valeurs du papier sur l'edge discrétionnaire.

Aucun nombre du document n'est écrit à la main : tout passe par ici, et tout
se recalcule. C'est la règle 4 du dépôt, et c'est aussi ce qui rend le papier
réfutable — un lecteur qui doute d'un chiffre peut relancer le module qui le
produit.
"""

from __future__ import annotations

import math

from .attribution import decompose
from .costs import deflated_threshold_sharpe, trades_for_significance
from .entropy import trades_for_information
from .journal import LEVERS, audit, planted_bits, synthesise, universe
from .operator import evaluate
from .report import Table, num

#: Séances simulées. Assez pour que le signe de l'espérance mécanique soit
#: stable — en deçà de 400, il bascule, et le papier en fait un résultat.
N_SESSIONS = 400

#: Clairvoyance franche : celle qui doit faire tomber les cinq lois.
SKILL_FORTE = 0.55

#: Séances de bourse par an.
SESSIONS_PER_YEAR = 252

#: Nombre de leviers recensés chez l'opérateur.
K_LEVERS = len(LEVERS)

#: Cadences de décision envisagées, en décisions par séance.
CADENCES = (1, 2, 3, 5)

#: Sharpe par décision revendiqués, pour la traduction en temps calendaire.
SHARPES = (0.05, 0.075, 0.10, 0.15)

#: Le Sharpe de référence du papier phare — l'avantage de géométrie. Il sert
#: de point de comparaison : c'est lui qui bute sur 17 434 trades.
SHARPE_GEOMETRIE = 0.0332

#: Paramètres cités en toutes lettres par la prose ou par une légende. Les
#: tenir ici plutôt qu'au fil du texte est la règle 4 du dépôt : un nombre
#: écrit à la main devient faux au premier changement, et le désaccord ne se
#: voit pas.
SHARPE_CITE = 0.10          # le Sharpe que le corps du texte prend en exemple
FENETRE_GLISSANTE = 150     # largeur de la fenêtre de la figure éponyme
BITS_ROC = 0.005            # compétence retenue par la caractéristique

#: Paramètres du nuage Monte-Carlo, tenus ici pour que la légende de la figure
#: cite le nombre réellement tracé. Ils doivent suivre `figdisc._paths`.
_CHEMINS = 520
_HORIZON = 1400


def _trades_for_threshold(sharpe: float, budget: float) -> float:
    """Décisions requises pour franchir le seuil déflaté à `budget` essais."""
    if sharpe <= 0.0:
        return math.inf
    return 2.0 * math.log(max(budget, 2.0)) / (sharpe ** 2)


_CACHE: dict[str, object] = {}


def _journal(skill: float):
    key = f"j{skill}"
    if key not in _CACHE:
        _CACHE[key] = synthesise(skill=skill, n_sessions=N_SESSIONS)
    return _CACHE[key]


def _verdict(skill: float):
    key = f"v{skill}"
    if key not in _CACHE:
        _CACHE[key] = evaluate(_journal(skill), draws=300)
    return _CACHE[key]


# ---------------------------------------------------------------------------
# Table 1 — les leviers recensés et ce qu'ils coûtent
# ---------------------------------------------------------------------------


def table_levers() -> Table:
    rows = []
    for k, (key, label) in enumerate(LEVERS, start=1):
        budget = 2.0 ** k
        seuil = deflated_threshold_sharpe(max(2.0, budget), 3000)
        avant = deflated_threshold_sharpe(max(2.0, 2.0 ** (k - 1)), 3000)
        rows.append([
            label,
            key,
            num(budget, 0),
            num(seuil, 4),
            num(seuil - avant, 4, signed=True),
        ])
    return Table(
        "levers",
        "Les quatre leviers discrétionnaires recensés, et ce que chacun ajoute "
        "au seuil de preuve.",
        ["Levier", "Clé", "Configurations", "Seuil déflaté",
         "Ce que ce levier ajoute"],
        rows,
        wrap_cols=[0],
        wide=True,
        note="Le seuil est calculé sur 3 000 décisions. Chaque levier double le "
             "nombre de configurations ; le seuil croît en racine du logarithme "
             "de ce nombre, d'où un incrément décroissant.",
    )


# ---------------------------------------------------------------------------
# Table 2 — la table de correspondance des cinq lois nulles
# ---------------------------------------------------------------------------


def table_nulls() -> Table:
    v = _verdict(SKILL_FORTE)
    rows = []
    for t in v.tests:
        rows.append([
            t.label,
            t.refutes,
            num(t.observed, 4, signed=True),
            num(t.q95, 4, signed=True),
            "battue" if t.beats else "non battue",
        ])
    return Table(
        "nulls",
        "Les cinq lois nulles, ce que chacune réfute, et le verdict sur un "
        "opérateur dont la clairvoyance est connue.",
        ["Loi nulle", "Ce qu'elle réfute si elle tient", "Observé",
         "Seuil 95 %", "Verdict"],
        rows,
        wrap_cols=[0, 1],
        wide=True,
        note="Le verdict est positif si et seulement si les cinq lois sont battues. "
             "Une loi inapplicable — un journal sans abstentions, par exemple — "
             "est comptée comme non battue.",
    )


# ---------------------------------------------------------------------------
# Table 3 — la calibration contre la vérité plantée
# ---------------------------------------------------------------------------


def table_calibration() -> Table:
    rows = []
    for skill in (0.0, 0.20, 0.35, SKILL_FORTE):
        j = _journal(skill)
        v = _verdict(skill)
        rows.append([
            num(skill, 2),
            num(j.skill_bits or 0.0, 4),
            num(j.mean_r, 4, signed=True),
            num(v.sharpe_trade, 4, signed=True),
            f"{len(v.beaten)} / 5",
            "déclaré" if v.accepted else "refusé",
        ])
    return Table(
        "calibration",
        "Ce que l'appareil déclare, selon la compétence qu'on lui a plantée.",
        ["Clairvoyance", "Bits par décision", "E[R] par décision",
         "Sharpe par décision", "Lois battues", "Verdict"],
        rows,
        wide=True,
        note="La première ligne mesure le niveau du test : à compétence nulle, le "
             "nombre de lois battues est nul. La dernière mesure la puissance. "
             "Les lignes intermédiaires situent la plage où la compétence est "
             "non nulle et le verdict négatif.",
    )


# ---------------------------------------------------------------------------
# Table 4 — la décomposition de Shapley
# ---------------------------------------------------------------------------


def table_attribution() -> Table:
    cas = (("entrée", 0.45, 0.0), ("taille", 0.0, 0.45),
           ("les deux", 0.45, 0.45))
    rows = []
    for label, skill, size_skill in cas:
        d = decompose(synthesise(skill=skill, size_skill=size_skill,
                                 n_sessions=N_SESSIONS))
        parts = {s.key: s.fraction for s in d.shares}
        rows.append([
            label,
            num(d.total, 4, signed=True),
            num(parts.get("entree", 0.0) * 100, 1, unit="%"),
            num(parts.get("moment", 0.0) * 100, 1, unit="%"),
            num(parts.get("taille", 0.0) * 100, 1, unit="%"),
            num(parts.get("sortie", 0.0) * 100, 1, unit="%"),
            d.carrier.key,
        ])
    return Table(
        "attribution",
        "La décomposition de Shapley retrouve-t-elle la compétence là où elle "
        "a été plantée ?",
        ["Compétence plantée dans", "Avantage total", "entrée", "moment",
         "taille", "sortie", "Levier désigné"],
        rows,
        note="Chaque ligne somme à cent pour cent, propriété qui définit la "
             "valeur de Shapley et qui sert ici de contrôle d'implémentation. "
             "La colonne « sortie » vaut zéro exact et non zéro approché : le "
             "journal synthétique ne gère aucune sortie, et la décomposition "
             "l'énonce au lieu de la bruiter.",
    )


# ---------------------------------------------------------------------------
# Table 5 — le mur, en décisions puis en années
# ---------------------------------------------------------------------------


def table_wall() -> Table:
    budget = 2.0 ** K_LEVERS
    rows = []
    for sr in SHARPES:
        n = _trades_for_threshold(sr, budget)
        rows.append([
            num(sr, 3),
            num(trades_for_significance(sr, 1.0), 0),
            num(n, 0),
            num(n / (2 * SESSIONS_PER_YEAR), 1, unit="an"),
            num(n / (3 * SESSIONS_PER_YEAR), 1, unit="an"),
        ])
    return Table(
        "wall",
        "Le mur d'échantillon, à quatre leviers ouverts, en décisions puis en "
        "années de carrière.",
        ["Sharpe par décision", "Route 1 — test t",
         "Route 2 — seuil déflaté", "à 2 décisions/jour",
         "à 3 décisions/jour"],
        rows,
        wide=True,
        note="Les deux routes convergent sans partager aucune hypothèse : la "
             "première ne connaît que la moyenne et la variance, la seconde ne "
             "connaît que le nombre de configurations. Deux chemins séparés qui "
             "butent au même endroit disent que le mur est structurel.",
    )


# ---------------------------------------------------------------------------
# Table 6 — la comparaison avec l'avantage de géométrie
# ---------------------------------------------------------------------------


def table_versus() -> Table:
    budget = 2.0 ** K_LEVERS
    rows = []
    for label, sr, k in (
            ("Géométrie de sortie (ALP-1)", SHARPE_GEOMETRIE, 0),
            ("Opérateur discrétionnaire", 0.10, K_LEVERS)):
        b = 2.0 ** k
        n = _trades_for_threshold(sr, b)
        rows.append([
            label,
            num(sr, 4),
            num(b, 0),
            num(deflated_threshold_sharpe(max(2.0, b), 3000), 4),
            num(n, 0),
            num(n / (2 * SESSIONS_PER_YEAR), 1, unit="an"),
        ])
    return Table(
        "versus",
        "Pourquoi le jugement est prouvable là où la géométrie ne l'est pas.",
        ["Objet du test", "Sharpe revendiqué", "Configurations",
         "Seuil déflaté", "Décisions requises", "à 2 par jour"],
        rows,
        wrap_cols=[0],
        wide=True,
        note="L'arithmétique est celle de la proposition 2 : le budget de "
             "configurations entre dans l'exigence par un logarithme, l'effet "
             "revendiqué par un carré. Multiplier le premier par seize coûte "
             "moins que diviser le second par trois.",
    )


# ---------------------------------------------------------------------------
# Table 7 — ce qu'un journal doit porter
# ---------------------------------------------------------------------------


def table_fields() -> Table:
    rows = [
        ["Horodatage de la décision", "avant l'issue",
         "sans lui, un journal est un souvenir et non une donnée"],
        ["Contexte au moment de la décision", "avant l'issue",
         "c'est l'état du monde que l'opérateur a réellement vu"],
        ["Abstentions — les setups refusés", "avant l'issue",
         "sans elles la loi nulle D est intestable et la moitié de la table de "
         "contingence reste vide"],
        ["Conviction annoncée", "avant l'issue",
         "elle autorise le test de calibration, qu'aucun autre champ ne permet"],
        ["Direction, mise, moment retenu", "avant l'issue",
         "les quatre leviers doivent être séparables pour être décomposés"],
        ["Issue effective", "après l'issue",
         "le résultat net, friction comprise"],
        ["Issue contrefactuelle des refus", "après l'issue",
         "ce que le setup refusé aurait donné — c'est ce qui rend l'abstention "
         "mesurable"],
    ]
    return Table(
        "fields",
        "Ce qu'un journal de décision doit porter, et de quel côté de la "
        "frontière temporelle chaque champ se situe.",
        ["Champ", "Connu", "Pourquoi il est indispensable"],
        rows,
        wrap_cols=[0, 2],
        wide=True,
        note="Les cinq premiers champs sont scellés à l'instant de la décision, "
             "les deux derniers ne sont connus qu'après. Un registre qui "
             "n'enregistre que les lignes du bas n'est pas un journal de "
             "décision mais un journal de trades, et aucun des tests de ce "
             "document ne s'y applique.",
    )


# ---------------------------------------------------------------------------
# Table 8 — les sept couches de la stratégie évaluée
# ---------------------------------------------------------------------------

#: Les sept couches de la pile d'origine, avec ce que chacune observe, le
#: levier discrétionnaire qu'elle alimente, et sa loi nulle telle que le
#: document nº 1 l'établit. La colonne « levier » est la lecture propre à ce
#: document : elle dit où la couche intervient dans la décision, non ce
#: qu'elle vaut.
COUCHES: tuple[tuple[str, str, str, str], ...] = (
    ("Théorie de Dow", "la succession des sommets et des creux journaliers",
     "entree", "trois jours sur quatre déclenchent par hasard"),
    ("Supports et résistances", "les niveaux touchés puis quittés",
     "entree", "tout niveau touché deux fois se qualifie a posteriori"),
    ("Profil de volume", "la densité d'échanges par niveau de prix",
     "sortie", "densité d'occupation : le POC est le mode de la distribution"),
    ("Bandes VWAP", "l'écart au prix moyen pondéré, en écarts-types",
     "entree", "1,1 minute de séance au-delà de trois écarts-types"),
    ("Exposition gamma", "la position des teneurs de marché en options",
     "taille", "le signe du gamma contraint la variance, non la direction"),
    ("Carnet d'ordres", "les tailles affichées et les exécutions agressives",
     "moment", "recouvrement des comportements : aire sous la courbe plafonnée"),
    ("Fibonacci et OTE", "les retracements d'une impulsion",
     "moment", "taux de remplissage de 14 % à la borne 0,618"),
)


def table_layers() -> Table:
    labels = dict(LEVERS)
    rows = [[nom, observe, labels.get(levier, levier), loi]
            for nom, observe, levier, loi in COUCHES]
    return Table(
        "layers",
        "Les sept couches de la stratégie évaluée, ce que chacune observe, et "
        "le levier discrétionnaire qu'elle alimente.",
        ["Couche", "Ce qu'elle observe", "Levier alimenté",
         "Loi nulle établie au document nº 1"],
        rows,
        wrap_cols=[0, 1, 3],
        wide=True,
        note="La colonne du levier situe la couche dans la décision : elle dit "
             "à quel moment l'opérateur la consulte, non ce que la couche "
             "apporte. Les lois nulles de la dernière colonne sont établies au "
             "document nº 1 de cette série et reprises ici sans modification.",
    )


TABLES = (table_layers, table_levers, table_nulls, table_calibration, table_attribution,
          table_wall, table_versus, table_fields)


def all_tables() -> dict[str, Table]:
    return {fn().key: fn() for fn in TABLES}


def values() -> dict[str, str]:
    """Les scalaires que le document cite dans son texte."""
    j0, jf = _journal(0.0), _journal(SKILL_FORTE)
    v0, vf = _verdict(0.0), _verdict(SKILL_FORTE)
    budget = 2.0 ** K_LEVERS
    u = universe(N_SESSIONS)
    mec = sum(t.net_r for t in u) / len(u)

    n10 = _trades_for_threshold(0.10, budget)
    n_geo = _trades_for_threshold(SHARPE_GEOMETRIE, 1.0)

    return {
        # Le recensement.
        #
        # Le seuil à zéro levier vaut exactement zéro : une configuration
        # unique n'offre aucune sélection, donc rien à déflater. Le borner par
        # `max(2.0, ·)` fabriquerait la valeur d'un levier et la ferait passer
        # pour celle de zéro — c'est le piège que la mémoire de projet
        # signale, et il faussait ici le facteur annoncé.
        "d_leviers": num(K_LEVERS, 0),
        "d_configs": num(budget, 0),
        "d_seuil_k0": num(deflated_threshold_sharpe(1, 3000), 4),
        "d_seuil_k1": num(deflated_threshold_sharpe(2, 3000), 4),
        "d_seuil_k4": num(deflated_threshold_sharpe(budget, 3000), 4),
        # Rapport du quatrième levier au premier : le seul rapport définissable,
        # puisque le dénominateur à zéro levier est nul.
        "d_facteur_1_4": num(
            deflated_threshold_sharpe(budget, 3000)
            / deflated_threshold_sharpe(2, 3000), 1),

        # L'univers et sa vérité de référence
        "d_seances": num(N_SESSIONS, 0),
        "d_setups": num(len(u), 0),
        "d_esperance_mecanique": num(mec, 4, signed=True),

        # La calibration
        "d_bits_forte": num(jf.skill_bits or 0.0, 4),
        "d_lois_nulle": num(len(v0.beaten), 0),
        "d_lois_forte": num(len(vf.beaten), 0),
        "d_sharpe_forte": num(vf.sharpe_trade, 4, signed=True),
        "d_sharpe_nulle": num(v0.sharpe_trade, 4, signed=True),
        "d_prises_forte": num(jf.n_taken, 0),
        "d_eligibles": num(jf.n_eligible, 0),
        "d_taux_prise": num(jf.take_rate * 100, 0, unit="%"),

        # Le mur
        "d_mur_sr10": num(n10, 0),
        "d_mur_ans10": num(n10 / (2 * SESSIONS_PER_YEAR), 1),
        "d_mur_sr05": num(_trades_for_threshold(0.05, budget), 0),
        "d_mur_sr15": num(_trades_for_threshold(0.15, budget), 0),
        "d_mur_geometrie": num(n_geo, 0),
        "d_sharpe_geometrie": num(SHARPE_GEOMETRIE, 4),

        # Les bornes de la plage d'indécision, relevées sur la calibration
        # elle-même : la prose les citait de mémoire, à « environ 0,05 bit »,
        # ce qui cesserait d'être vrai au premier changement d'échantillon.
        "d_bits_refuse": num(max(
            (_journal(k).skill_bits or 0.0)
            for k in (0.0, 0.20, 0.35, SKILL_FORTE)
            if not _verdict(k).accepted), 4),
        "d_bits_declare": num(min(
            (_journal(k).skill_bits or 0.0)
            for k in (0.0, 0.20, 0.35, SKILL_FORTE)
            if _verdict(k).accepted), 4),

        # Les paramètres que la prose cite
        "d_sharpe_cite": num(SHARPE_CITE, 2),
        "d_fenetre": num(FENETRE_GLISSANTE, 0),
        "d_bits_roc": num(BITS_ROC, 3),

        # La stratégie évaluée
        "d_couches": num(len(COUCHES), 0),
        "d_couches_entree": num(
            sum(1 for c in COUCHES if c[2] == "entree"), 0),

        # Le nuage Monte-Carlo — cités par la légende de la figure, donc
        # produits ici plutôt qu'écrits à la main dans le gabarit.
        "d_chemins": num(_CHEMINS, 0),
        "d_horizon": num(_HORIZON, 0),

        # L'attribution
        "d_part_entree": num(
            next(s.fraction for s in decompose(
                synthesise(skill=0.45, n_sessions=N_SESSIONS)).shares
                if s.key == "entree") * 100, 1, unit="%"),
    }


def main() -> None:
    print("Le journal de décision et les lois nulles de l'opérateur\n")
    for fn in TABLES:
        print(fn().to_text())
        print()
    print("Valeurs cyclées dans le document :")
    for k, v in sorted(values().items()):
        print(f"  {k:26s} {v}")
    print("\nAudit du journal synthétique :",
          audit(_journal(SKILL_FORTE)) or "aucun défaut")
