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
n'est pas une précaution rhétorique : `spend` lève une exception, et le plan
de puissance du document est calculé sur ce trois-là.

Les trois configurations ne sont pas examinées de front. Elles sont **ordonnées
d'avance**, et la deuxième n'est lue que si la première rejette. Cette
procédure — le test en séquence fixée — contrôle le taux d'erreur par famille
au niveau `α` sans diviser ce niveau par trois, ce qui retire trente pour cent
de l'échantillon requis sans rien concéder sur la validité. Le prix est réel
mais il se paie ailleurs : si la configuration de référence échoue, les deux
autres ne sont jamais lues, quelles qu'aient été leurs valeurs. C'est
exactement ce qu'on veut d'un protocole — un filtre qui rattrape une règle
défaillante n'a rien démontré sur la règle.

La décision est en outre **séquentielle et jalonnée en information** : quatre
examens, aux fractions données par `alp1.power`, déclenchés non par le
calendrier mais par l'information accumulée. La corrélation entre marchés, la
cadence des entrées et la persistance de la volatilité déplacent alors la
*date* des examens, jamais leurs seuils, et aucune de ces trois hypothèses
n'entre dans le taux d'erreur du protocole.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

from .costs import _norm_ppf, deflated_threshold_sharpe
from .power import (
    ALPHA,
    DESIGN_SESSIONS,
    HORIZON_SESSIONS,
    LOOKS,
    MIN_SESSIONS_BEFORE_LOOK,
    PANEL,
    POWER,
    boundaries,
)

SEALED_ON = "2026-08-21"
PROTOCOL_VERSION = "ALP-2/2.0"


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
              "après 30,8 % de la séance écoulée — 120 minutes sur une séance "
              "de 390 —, dans le sens de la cassure. Jusqu'à trois entrées par "
              "séance et par marché : une nouvelle entrée n'est ouverte "
              "qu'après la sortie de la précédente et après un retour du prix "
              "à l'intérieur de la bande.",
        stop="Distance égale à la largeur de bande √(2/π)·σ̂₁·√t à "
             "l'instant de l'entrée, fixe, jamais déplacée. σ̂₁ est estimée "
             "sur les quatorze séances précédentes, close.",
        exit="Au marché deux minutes avant la clôture de la séance du "
             "contrat, ou au stop, selon ce qui vient en premier.",
        filter="Aucun.",
        rationale="La règle publiée, sans aucun ajout. C'est la première de "
                  "la séquence fixée : si elle ne rejette pas, les deux "
                  "autres ne sont pas lues, et le protocole s'arrête là.",
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
              "23,1 % de la séance écoulée — 90 minutes sur une séance de "
              "390.",
        stop="Identique à C1.",
        exit="Identique à C1.",
        filter="Aucun.",
        rationale="Contrôle de robustesse à l'heure d'entrée, pas recherche "
                  "d'optimum : une seule heure alternative, et elle n'est pas "
                  "libre — c'est celle que le chiffrage retenait avant la "
                  "correction au pire cas sur la boîte d'exposant d'échelle.",
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
    markets: tuple[str, ...]
    primary_statistic: str
    multiplicity: str
    decision_rule: str
    alpha: float
    power: float
    looks: tuple[float, ...]
    design_sessions: int
    horizon_sessions: int
    min_sessions: int
    max_entries_per_session: int
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
        lines += [f"market={m}" for m in self.markets]
        lines += [
            f"statistic={self.primary_statistic}",
            f"multiplicity={self.multiplicity}",
            f"decision={self.decision_rule}",
            f"alpha={self.alpha:.10f}",
            f"power={self.power:.10f}",
        ]
        lines += [f"look={t:.10f}" for t in self.looks]
        lines += [
            f"design_sessions={self.design_sessions}",
            f"horizon_sessions={self.horizon_sessions}",
            f"min_sessions={self.min_sessions}",
            f"max_entries={self.max_entries_per_session}",
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
        """Seuil de Sharpe par trade attendu du meilleur des essais sous H₀.

        Conservé du protocole précédent comme repère de lecture : c'est la
        barre qu'un backtest sélectionné doit franchir pour n'être pas un
        artefact. Elle ne sert plus de règle de décision — la séquence fixée
        rend la correction de sélection inutile sur la configuration de
        référence — mais elle reste le bon ordre de grandeur à opposer à un
        Sharpe rapporté sans protocole.
        """
        return deflated_threshold_sharpe(len(self.configurations), n_obs)

    def required_trades(self, sharpe_trade: float) -> int:
        """Trades nécessaires pour détecter ce Sharpe à la puissance visée.

        Test unilatéral au niveau plein : ``N = ((z_{1−α} + z_puissance)/SR)²``.
        Le niveau n'est plus divisé par le budget, et c'est la séquence fixée
        qui l'autorise.
        """
        if sharpe_trade <= 0:
            return 0
        z_a = _norm_ppf(1.0 - self.alpha)
        z_b = _norm_ppf(self.power)
        return math.ceil(((z_a + z_b) / sharpe_trade) ** 2)

    def bounds(self):
        """Frontières séquentielles du plan, résolues par `alp1.power`."""
        return boundaries(self.looks, self.alpha, self.power)


@dataclass(frozen=True)
class Decision:
    """Verdict rendu par le protocole sur une information accumulée."""

    look: int
    sessions: int
    information_fraction: float
    z: float
    efficacy: float
    futility: float
    exhausted: bool

    @property
    def rejected(self) -> bool:
        return not self.exhausted and self.z >= self.efficacy

    @property
    def abandoned(self) -> bool:
        return not self.exhausted and self.z <= self.futility

    @property
    def conclusive(self) -> bool:
        return self.rejected or self.abandoned

    @property
    def reason(self) -> str:
        if self.exhausted:
            return ("horizon épuisé : le protocole ne conclut pas, et la "
                    "dérive minimale détectable publiée dit ce que ce silence "
                    "exclut")
        if self.rejected:
            return "rejet de l'hypothèse nulle à l'examen " + str(self.look)
        if self.abandoned:
            return "abandon pour futilité à l'examen " + str(self.look)
        return "poursuite : aucune frontière franchie"


def decide(protocol: "Protocol", z: float, information_fraction: float,
           sessions: int) -> Decision:
    """Applique la règle de décision gelée à une information accumulée.

    Deux conditions préalables, et elles ne se rachètent pas : au moins
    `min_sessions` séances, et une information au moins égale à la première
    fraction prévue. Un opérateur pressé qui regarde plus tôt ne lit pas un
    résultat « presque significatif » : il lit un résultat que le protocole
    n'a pas défini.
    """
    plan = protocol.bounds()
    if sessions >= protocol.horizon_sessions and information_fraction < plan.fractions[-1]:
        return Decision(0, sessions, information_fraction, z,
                        math.inf, -math.inf, True)
    look = 0
    for k, t in enumerate(plan.fractions):
        if information_fraction >= t:
            look = k + 1
    if look == 0:
        return Decision(0, sessions, information_fraction, z,
                        math.inf, -math.inf, False)
    return Decision(look, sessions, information_fraction, z,
                    plan.efficacy[look - 1], plan.futility[look - 1], False)


PROTOCOL = Protocol(
    version=PROTOCOL_VERSION,
    subject="ALP-2 — cassure de bande de bruit, stop seul, sortie à la clôture, "
            "sur un panel de cinq contrats indiciels",
    sealed_on=SEALED_ON,
    configurations=CONFIGURATIONS,
    markets=tuple(m.symbol for m in PANEL),
    primary_statistic="Dérive nette par minute d'exposition, estimée par "
                      "µ̂ = Σw·R / Σw·τ avec w = 1/σ̂² — moindres carrés "
                      "généralisés sur la volatilité de séance estimée avant "
                      "l'entrée —, variance groupée par date, friction "
                      "relevée au journal d'exécution et non posée.",
    multiplicity="Séquence fixée : C1, puis C2 seulement si C1 rejette, puis "
                 "C3 seulement si C2 rejette. Chaque test au niveau plein α ; "
                 "le taux d'erreur par famille reste α.",
    decision_rule="Jalonnement en information : examen à chaque franchissement "
                  "d'une fraction pré-enregistrée de I_max. Rejet si "
                  "Z ≥ frontière d'efficacité d'O'Brien-Fleming, abandon si "
                  "Z ≤ frontière de futilité (non contraignante). Au-delà de "
                  "l'horizon sans avoir atteint le dernier examen, le "
                  "protocole ne conclut pas.",
    alpha=ALPHA,
    power=POWER,
    looks=LOOKS,
    design_sessions=DESIGN_SESSIONS,
    horizon_sessions=HORIZON_SESSIONS,
    min_sessions=MIN_SESSIONS_BEFORE_LOOK,
    max_entries_per_session=3,
    cv_folds=5,
    cv_embargo_days=1,
    stopping_rules=(
        "Test 1 — si la bande n'est cassée que sur moins de la moitié des "
        "séances, la règle ne se déclenche pas assez pour être testée : arrêt.",
        "Test 2 — si la dérive moyenne captée est inférieure à la friction "
        "déduite au quantile 90 %, arrêt sans passer aux tests suivants.",
        "Test 3 — le filtre gamma n'est examiné que si C1 a rejeté. Un filtre "
        "ne rattrape pas une règle qui échoue seule.",
        "Aucune configuration n'est rejouée après modification. Une "
        "modification est une quatrième configuration, et le budget est de "
        "trois.",
        "Aucun examen avant 252 séances, quelle que soit l'information "
        "accumulée : une décision prise sur une seule saison n'est pas une "
        "décision sur un marché.",
        "Au-delà de 1 260 séances sans dernier examen atteint, le protocole "
        "s'arrête sans conclure. Il ne prolonge pas l'horizon : prolonger "
        "après avoir vu l'échantillon est une décision informée par les "
        "données, et elle invaliderait le niveau du test.",
    ),
    falsifiers=(
        "La dérive captée moyenne est nulle ou négative sur C1.",
        "La dérive captée est concentrée sur une seule tranche horaire : "
        "c'est une signature de sélection, pas de structure.",
        "La dérive captée décroît de façon monotone avec le rang de l'entrée "
        "dans la séance : la cadence achèterait alors du bruit, et le gain de "
        "durée qu'elle procure serait fictif.",
        "L'hétérogénéité entre marchés du panel excède ce que l'erreur "
        "d'échantillonnage explique (test de Cochran au niveau 5 %) : la "
        "dérive n'est pas commune, et le panel n'est plus une répétition de "
        "la même expérience.",
        "L'écart d'exécution mesuré en journal dépasse le quantile 90 % de la "
        "loi de friction déduite : le chiffrage de la friction est faux, et "
        "toutes les marges avec lui.",
        "L'information accumulée à 252 séances est inférieure au tiers de "
        "celle que le plan prévoit : la cadence ou la corrélation supposées "
        "sont fausses, et l'horizon ne suffira pas.",
    ),
    frozen_inputs=(
        ("index_level", 6000.0),
        ("session_dispersion_points", 60.0),
        ("session_minutes", 390.0),
        ("entry_fraction_of_session", 120.0 / 390.0),
        ("edge_basis_points", 6.0),
        ("markets", float(len(PANEL))),
        ("max_entries_per_session", 3.0),
        ("vol_estimation_sessions", 14.0),
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
        ("Ouverture de la fenêtre", "30,8 % de la séance (C1, C2) ou 23,1 % (C3)"),
        ("Largeur du stop", "la bande à l'entrée, jamais déplacée"),
        ("Heure de sortie", "clôture de la séance moins deux minutes, fixe"),
        ("Nombre d'entrées par séance", "trois au plus, ré-armement imposé"),
        ("Filtre", "aucun (C1, C3) ou signe du gamma net (C2)"),
        ("Panel", "cinq contrats nommés, aucun ajout ni retrait"),
        ("Pondération", "1/σ̂², σ̂ estimée avant l'entrée ; aucune autre"),
        ("Variance", "groupée par date, sans modèle de corrélation"),
        ("Ordre des configurations", "C1, C2, C3 ; fixé, non révisable"),
        ("Examens", "quatre, aux fractions 0,25 / 0,50 / 0,75 / 1,00 de I_max"),
        ("Horizon", "1 260 séances ; aucune prolongation"),
        ("Friction", "loi déduite du carnet, quantile 90 % pour les arrêts"),
        ("Taille", "un contrat pour la mesure ; le dimensionnement ne fait "
                   "pas partie du test"),
        ("Sous-période", "aucune : l'échantillon est pris en entier"),
    ]


def main() -> None:
    p = PROTOCOL
    plan = p.bounds()
    print(f"Protocole {p.version} — scellé le {p.sealed_on}")
    print(f"Sceau SHA-256 : {p.fingerprint()}")
    print(f"À publier     : {p.seal}\n")

    print(f"Budget : {len(p.configurations)} configurations, en séquence fixée")
    for c in p.configurations:
        print(f"  {c.key} — {c.label}")
    print(f"Panel  : {', '.join(p.markets)}")
    print(f"Horizon: {p.horizon_sessions} séances ({p.horizon_sessions / 252:.0f} ans), "
          f"budget d'information {p.design_sessions} séances")

    print("\nFrontières séquentielles :")
    for k, t in enumerate(plan.fractions):
        fut = f"{plan.futility[k]:+.3f}" if k < len(plan.fractions) - 1 else "  —   "
        print(f"  examen {k + 1} — information {t:.2f} : "
              f"rejet si Z ≥ {plan.efficacy[k]:.3f}, abandon si Z ≤ {fut}")
    print(f"  inflation de l'information maximale : {plan.inflation:.3f}")

    print("\nDegrés de liberté gelés :")
    for name, value in degrees_of_freedom():
        print(f"  {name:32s} {value}")

    print("\nExemples de décision :")
    for z, t, n in ((2.9, 0.52, 700), (1.2, 0.52, 700), (0.1, 0.27, 300),
                    (1.9, 1.00, 1100), (1.9, 0.80, 1260)):
        d = decide(p, z, t, n)
        print(f"  Z={z:4.1f} t={t:.2f} N={n:5d} → {d.reason}")


if __name__ == "__main__":
    main()
