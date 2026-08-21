"""Pré-enregistrement scellé : le protocole gelé avant toute donnée.

Le seuil de Sharpe déflaté répond à la question « combien de configurations
ai-je essayées ? ». Il n'a de valeur que si la réponse est vérifiable, et elle
ne l'est pas après coup : un opérateur qui rapporte trois essais après en avoir
conduit trente produit exactement le même document. La discipline
anti-surajustement n'est donc pas un calcul, c'est un **ordre chronologique** —
fixer la configuration, la publier, puis regarder les données.

Ce module rend cet ordre vérifiable sans faire confiance à personne. Il décrit
le protocole comme une donnée immuable, le sérialise de façon canonique, et en
calcule l'empreinte SHA-256. L'empreinte se publie *avant* d'ouvrir le moindre
fichier de prix ; toute modification ultérieure du protocole — une variante
ajoutée, un seuil déplacé, une règle de sortie assouplie — change l'empreinte
et se voit.

Ce que l'empreinte établit, et ce qu'elle n'établit pas :

  - **Elle établit** qu'un protocole donné existait à une date donnée, et que
    ce qui est mesuré ensuite est bien ce qui avait été annoncé.
  - **Elle n'établit pas** que rien d'autre n'a été essayé en parallèle. Aucun
    dispositif ne peut l'établir de l'extérieur ; ce que celui-ci fait, c'est
    rendre la triche coûteuse et repérable, et donner à l'opérateur un moyen de
    se lier lui-même — ce qui est le seul usage honnête d'un pré-enregistrement.

Le budget est de trois configurations, et le module refuse la quatrième. Ce
n'est pas une précaution rhétorique : `spend` lève une exception, et le seuil
déflaté du document est calculé sur ce trois-là.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

from .costs import _norm_ppf, deflated_threshold_sharpe

SEALED_ON = "2026-08-21"
PROTOCOL_VERSION = "ALP-2/1.0"


# --- Les configurations, et rien d'autre ------------------------------------


@dataclass(frozen=True)
class Configuration:
    """Une configuration du budget : toutes ses règles, gelées.

    Une configuration est complète : entrée, stop, sortie, filtre. Il n'y a pas
    de « paramètre à ajuster ensuite » — c'est précisément ce qu'un
    pré-enregistrement interdit.
    """

    key: str
    label: str
    entry: str
    stop: str
    exit: str
    filter: str
    rationale: str

    def canonical(self) -> str:
        return "|".join((self.key, self.label, self.entry, self.stop,
                         self.exit, self.filter))


CONFIGURATIONS: tuple[Configuration, ...] = (
    Configuration(
        key="C1",
        label="Bande de bruit, sans filtre",
        entry="Première cassure de la bande |P − P_ouverture| > √(2/π)·σ̂₁·√t "
              "après 10:00 ET, dans le sens de la cassure ; une entrée par "
              "séance au plus.",
        stop="Distance égale à la largeur de bande √(2/π)·σ̂₁·√t à "
             "l'instant de l'entrée, fixe, jamais déplacée.",
        exit="Au marché à 15:58 ET, ou au stop, selon ce qui vient en premier.",
        filter="Aucun.",
        rationale="La règle publiée, sans aucun ajout. C'est la configuration "
                  "de référence : si elle échoue, les deux autres n'ont pas "
                  "à être examinées.",
    ),
    Configuration(
        key="C2",
        label="Bande de bruit, conditionnée au gamma net",
        entry="Identique à C1.",
        stop="Identique à C1.",
        exit="Identique à C1.",
        filter="Prise seulement si le gamma net publié à l'ouverture est "
               "négatif.",
        rationale="Le seul filtre du document dont le mécanisme est décrit "
                  "dans une littérature séparée. Le signe du gamma est "
                  "publié avant l'ouverture : le filtre n'utilise aucune "
                  "information future.",
    ),
    Configuration(
        key="C3",
        label="Bande de bruit, entrée retardée",
        entry="Identique à C1, mais la fenêtre de cassure n'ouvre qu'à "
              "11:00 ET.",
        stop="Identique à C1.",
        exit="Identique à C1.",
        filter="Aucun.",
        rationale="Contrôle de robustesse à l'heure d'entrée, pas recherche "
                  "d'optimum : une seule heure alternative, choisie parce "
                  "que c'est celle du chiffrage du document.",
    ),
)

BUDGET = len(CONFIGURATIONS)
CONFIG_BY_KEY = {c.key: c for c in CONFIGURATIONS}


class BudgetExceeded(RuntimeError):
    """Levée quand une configuration hors budget est demandée."""


def spend(key: str) -> Configuration:
    """Retourne la configuration pré-enregistrée, ou refuse.

    C'est la garde du budget : une variante non scellée n'est pas une variante
    « supplémentaire à déclarer », c'est une variante que le protocole ne
    permet pas d'exécuter. Ajouter une quatrième configuration exige de
    modifier ce fichier, ce qui change le sceau — et le changement est daté par
    l'historique du dépôt.
    """
    if key not in CONFIG_BY_KEY:
        raise BudgetExceeded(
            f"« {key} » n'est pas dans le budget pré-enregistré "
            f"({', '.join(CONFIG_BY_KEY)}). Le seuil déflaté du document est "
            f"calculé sur {BUDGET} configurations ; en essayer une de plus "
            f"invalide le seuil, pas seulement la configuration.")
    return CONFIG_BY_KEY[key]


# --- Le protocole -----------------------------------------------------------


@dataclass(frozen=True)
class Protocol:
    """Le protocole complet, immuable et sérialisable.

    `frozen_inputs` contient les nombres de calibration exactement tels qu'ils
    entrent dans le chiffrage : ils font partie du sceau, de sorte qu'on ne
    puisse pas recalibrer après avoir vu les données et prétendre que le
    protocole n'a pas bougé.
    """

    version: str
    subject: str
    sealed_on: str
    configurations: tuple[Configuration, ...]
    primary_statistic: str
    decision_rule: str
    alpha: float
    power: float
    min_trades: int
    cv_folds: int
    cv_embargo_days: int
    stopping_rules: tuple[str, ...]
    falsifiers: tuple[str, ...]
    frozen_inputs: tuple[tuple[str, float], ...] = field(default_factory=tuple)

    def canonical(self) -> str:
        """Sérialisation canonique : ordre fixé, séparateurs fixés, ASCII exclu.

        La canonicité est ce qui donne son sens à l'empreinte. Deux
        exécutions, sur deux machines, doivent produire la même chaîne octet
        pour octet — d'où l'absence de dictionnaire non ordonné, de flottant
        formaté par défaut et de date calculée.
        """
        lines = [
            f"version={self.version}",
            f"subject={self.subject}",
            f"sealed_on={self.sealed_on}",
            f"budget={len(self.configurations)}",
        ]
        lines += [f"config={c.canonical()}" for c in self.configurations]
        lines += [
            f"statistic={self.primary_statistic}",
            f"decision={self.decision_rule}",
            f"alpha={self.alpha:.10f}",
            f"power={self.power:.10f}",
            f"min_trades={self.min_trades}",
            f"cv_folds={self.cv_folds}",
            f"cv_embargo_days={self.cv_embargo_days}",
        ]
        lines += [f"stop={r}" for r in self.stopping_rules]
        lines += [f"falsifier={r}" for r in self.falsifiers]
        lines += [f"input={k}={v:.10f}" for k, v in self.frozen_inputs]
        return "\n".join(lines) + "\n"

    def fingerprint(self) -> str:
        """Empreinte SHA-256 de la sérialisation canonique, en hexadécimal."""
        return hashlib.sha256(self.canonical().encode("utf-8")).hexdigest()

    @property
    def seal(self) -> str:
        """Les seize premiers chiffres de l'empreinte — ce qu'on publie."""
        return self.fingerprint()[:16]

    def hurdle(self, n_obs: int) -> float:
        """Seuil de Sharpe par trade attendu du meilleur des essais sous H₀."""
        return deflated_threshold_sharpe(len(self.configurations), n_obs)

    def required_trades(self, sharpe_trade: float) -> int:
        """Trades nécessaires pour détecter ce Sharpe à la puissance visée.

        Test unilatéral, seuil corrigé de Bonferroni sur le budget :
        ``N = ((z_{1−α/k} + z_{puissance})/SR)²``.
        """
        if sharpe_trade <= 0:
            return 0
        z_a = _norm_ppf(1.0 - self.alpha / len(self.configurations))
        z_b = _norm_ppf(self.power)
        return math.ceil(((z_a + z_b) / sharpe_trade) ** 2)


@dataclass(frozen=True)
class Decision:
    """Verdict rendu par le protocole sur un résultat mesuré."""

    n_obs: int
    sharpe_trade: float
    hurdle: float
    t_stat: float
    t_critical: float
    enough_trades: bool

    @property
    def beats_selection(self) -> bool:
        return self.sharpe_trade > self.hurdle

    @property
    def significant(self) -> bool:
        return self.t_stat > self.t_critical

    @property
    def accepted(self) -> bool:
        """Les trois conditions, toutes requises. Aucune ne se rachète."""
        return self.enough_trades and self.beats_selection and self.significant

    @property
    def reason(self) -> str:
        if not self.enough_trades:
            return "échantillon insuffisant : le protocole ne conclut pas"
        if not self.beats_selection:
            return "sous le seuil de sélection : indiscernable du meilleur de trois essais"
        if not self.significant:
            return "au-dessus du seuil de sélection mais non significatif"
        return "accepté : les trois conditions sont remplies"


def decide(protocol: "Protocol", sharpe_trade: float, n_obs: int) -> Decision:
    """Applique la règle de décision gelée à un résultat mesuré.

    Trois conditions, et le protocole exige les trois : un échantillon d'au
    moins `min_trades`, un Sharpe par trade au-dessus du seuil de sélection, et
    un t-statistique au-dessus du seuil corrigé du budget. Un résultat qui
    satisfait deux conditions sur trois n'est pas « presque validé » : il est
    refusé, et c'est l'intérêt d'avoir écrit la règle avant.
    """
    z_a = _norm_ppf(1.0 - protocol.alpha / len(protocol.configurations))
    return Decision(
        n_obs=n_obs,
        sharpe_trade=sharpe_trade,
        hurdle=protocol.hurdle(n_obs),
        t_stat=sharpe_trade * math.sqrt(max(n_obs, 0)),
        t_critical=z_a,
        enough_trades=n_obs >= protocol.min_trades,
    )


PROTOCOL = Protocol(
    version=PROTOCOL_VERSION,
    subject="ALP-2 — cassure de bande de bruit, stop seul, sortie à la clôture",
    sealed_on=SEALED_ON,
    configurations=CONFIGURATIONS,
    primary_statistic="Sharpe par trade du résultat net, en points d'indice, "
                      "friction déduite du modèle de carnet et non posée.",
    decision_rule="Accepter seulement si les trois conditions tiennent : "
                  "N ≥ min_trades, SR/trade > seuil déflaté à 3 essais, "
                  "t = SR·√N > z_{1−α/3}.",
    alpha=0.05,
    power=0.80,
    min_trades=1000,
    cv_folds=5,
    cv_embargo_days=1,
    stopping_rules=(
        "Test 1 — si la bande n'est cassée que sur moins de la moitié des "
        "séances, la règle ne se déclenche pas assez pour être testée : arrêt.",
        "Test 2 — si la dérive moyenne captée est inférieure à la friction "
        "déduite au quantile 90 %, arrêt sans passer aux tests suivants.",
        "Test 3 — le filtre gamma n'est examiné que si C1 a franchi le test 2. "
        "Un filtre ne rattrape pas une règle qui échoue seule.",
        "Aucune configuration n'est rejouée après modification. Une "
        "modification est une quatrième configuration, et le budget est de "
        "trois.",
    ),
    falsifiers=(
        "La dérive captée moyenne est nulle ou négative sur C1.",
        "La dérive captée est concentrée sur une seule tranche horaire : "
        "c'est une signature de sélection, pas de structure.",
        "L'écart d'exécution mesuré en journal dépasse le quantile 90 % de la "
        "loi de friction déduite : le chiffrage de la friction est faux, et "
        "toutes les marges avec lui.",
        "Le Sharpe par trade mesuré tombe sous le seuil de sélection à trois "
        "essais : le résultat est indiscernable de l'artefact.",
    ),
    frozen_inputs=(
        ("index_level", 6000.0),
        ("session_dispersion_points", 60.0),
        ("session_minutes", 390.0),
        ("entry_minutes_after_open", 90.0),
        ("edge_basis_points", 6.0),
        ("trades_per_year", 200.0),
    ),
)

SEAL = PROTOCOL.seal


def degrees_of_freedom() -> list[tuple[str, str]]:
    """Tout ce qui aurait pu être ajusté, et la valeur à laquelle c'est gelé.

    L'intérêt de la liste n'est pas d'être longue mais d'être **close** : un
    degré de liberté qui n'y figure pas et qui est pourtant utilisé dans la
    mesure est une violation du protocole, repérable par lecture.
    """
    return [
        ("Seuil de cassure", "√(2/π)·σ̂₁·√t, aucun multiplicateur libre"),
        ("Fenêtre d'estimation de σ̂₁", "14 séances précédentes, close"),
        ("Heure d'ouverture de la fenêtre", "10:00 ET (C1, C2) ou 11:00 ET (C3)"),
        ("Largeur du stop", "la bande à l'entrée, jamais déplacée"),
        ("Heure de sortie", "15:58 ET, fixe"),
        ("Nombre d'entrées par séance", "une au plus"),
        ("Filtre", "aucun (C1, C3) ou signe du gamma net (C2)"),
        ("Friction", "loi déduite du carnet, quantile 90 % pour les arrêts"),
        ("Taille", "un contrat pour la mesure ; le dimensionnement ne fait "
                   "pas partie du test"),
        ("Sous-période", "aucune : l'échantillon est pris en entier"),
    ]


def main() -> None:
    p = PROTOCOL
    print(f"Protocole {p.version} — scellé le {p.sealed_on}")
    print(f"Sceau SHA-256 : {p.fingerprint()}")
    print(f"À publier     : {p.seal}\n")

    print(f"Budget : {len(p.configurations)} configurations")
    for c in p.configurations:
        print(f"  {c.key} — {c.label}")

    print("\nDegrés de liberté gelés :")
    for name, value in degrees_of_freedom():
        print(f"  {name:36s} {value}")

    print("\nSeuils selon la taille d'échantillon :")
    for n in (200, 400, 1000, 2000, 5000):
        print(f"  N = {n:5d} : seuil de sélection {p.hurdle(n):.4f}, "
              f"t critique {_norm_ppf(1 - p.alpha / BUDGET):.3f}")

    print("\nExemples de décision (SR/trade mesuré) :")
    for sr, n in ((0.090, 400), (0.090, 1000), (0.040, 1000), (0.150, 1000)):
        d = decide(p, sr, n)
        print(f"  SR={sr:.3f} N={n:5d} → {'ACCEPTÉ' if d.accepted else 'refusé'} "
              f"({d.reason})")


if __name__ == "__main__":
    main()
