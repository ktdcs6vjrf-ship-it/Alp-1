"""Où loge l'avantage : la décomposition d'un jugement en ses leviers.

Un opérateur qui bat ses lois nulles a démontré quelque chose, mais pas
encore quoi. Quatre leviers ont été actionnés — entrer ou s'abstenir, choisir
le moment, dimensionner, gérer la sortie — et le verdict global ne dit pas
lequel a payé. La question n'est pas académique : c'est elle qui décide quels
leviers fermer, donc de combien la taxe de multiplicité baissera.

**Pourquoi Shapley et non l'ablation simple.** On serait tenté de neutraliser
un levier à la fois et d'attribuer à chacun la chute observée. Le procédé est
faux dès que les leviers interagissent, et il l'est de façon dirigée : la
somme des chutes ne fait pas le total, et l'ordre dans lequel on neutralise
change le résultat. La valeur de Shapley (1953) est l'unique attribution qui
soit à la fois exhaustive (les parts somment au total), symétrique (deux
leviers interchangeables reçoivent autant) et nulle pour un levier sans
effet. Elle exige d'évaluer toutes les coalitions.

**Et il se trouve que ces coalitions sont exactement les configurations
taxées.** Quatre leviers engendrent 2⁴ = 16 sous-ensembles ; c'est le même 16
que `discipline.effective_trials` fait payer au seuil déflaté. La coïncidence
n'en est pas une : la multiplicité qu'on paie en preuve est la multiplicité
qu'on décompose en attribution. Le papier tire ce fil.

**La neutralisation d'un levier est un contrefactuel déclaré**, jamais une
suppression de données :

| levier   | actif                    | neutralisé                          |
|----------|--------------------------|-------------------------------------|
| `entree` | la décision de l'opérateur | tous les setups éligibles sont pris |
| `moment` | l'issue effectivement obtenue | l'issue moyenne de la séance    |
| `taille` | la mise choisie          | une unité de risque partout         |
| `sortie` | le résultat après gestion | le résultat de la règle scellée     |

Le contrefactuel du `moment` mérite un mot. On lui substitue l'espérance de
la séance et non un tirage permuté : c'est la même construction que la loi
nulle B, prise en espérance plutôt qu'en simulation. Cela rend la
décomposition déterministe, ce qu'une attribution doit être — deux exécutions
du même journal ne peuvent pas répartir l'avantage différemment.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations

from .journal import LEVERS, Journal

#: Les leviers décomposés, dans l'ordre du recensement.
KEYS: tuple[str, ...] = tuple(k for k, _ in LEVERS)
LABELS: dict[str, str] = dict(LEVERS)


@dataclass(frozen=True)
class Share:
    """La part d'un levier dans l'avantage total."""

    key: str
    label: str
    value: float            # la part de Shapley, en R par décision
    fraction: float         # la même, en part du total
    solo: float             # ce que le levier rapporte seul, sans les autres
    marginal: float         # ce qu'il ajoute quand tous les autres sont ouverts

    @property
    def interacts(self) -> bool:
        """Le levier vaut-il autre chose seul qu'en compagnie ?

        Un écart franc entre `solo` et `marginal` signale que l'avantage n'est
        pas séparable : fermer le levier ne rendra pas mécaniquement sa part.
        """
        return abs(self.solo - self.marginal) > 0.5 * abs(self.value) + 1e-9


@dataclass(frozen=True)
class Decomposition:
    """Le partage complet, et ce qu'il en reste après vérification."""

    shares: tuple[Share, ...]
    total: float            # v(tous) − v(aucun)
    baseline: float         # v(aucun) : la règle scellée sur tout l'univers
    realised: float         # v(tous)  : l'opérateur tel qu'il a joué

    @property
    def carrier(self) -> Share:
        """Le levier qui porte l'avantage."""
        return max(self.shares, key=lambda s: s.value)

    @property
    def idle(self) -> tuple[Share, ...]:
        """Les leviers dont la part ne justifie pas le doublement qu'ils coûtent.

        Le critère est délibérément grossier — une part inférieure au dixième
        du total — parce qu'un critère fin donnerait l'illusion qu'on sait
        trancher là où l'échantillon ne le permet pas.
        """
        seuil = 0.10 * abs(self.total)
        return tuple(s for s in self.shares if abs(s.value) < seuil)

    @property
    def exhaustive(self) -> bool:
        """Les parts somment-elles au total ? C'est la propriété qui définit
        Shapley, et la vérifier est le contrôle le moins cher d'une erreur
        d'implémentation."""
        return abs(sum(s.value for s in self.shares) - self.total) < 1e-9


def _session_means(journal: Journal) -> dict[str, float]:
    """L'issue moyenne de chaque séance — le contrefactuel du levier `moment`."""
    sums: dict[str, list[float]] = {}
    for d in journal.decisions:
        if d.net_r is not None:
            sums.setdefault(d.day, []).append(d.net_r)
    return {day: sum(v) / len(v) for day, v in sums.items()}


def coalition_value(journal: Journal, active: frozenset[str],
                    session_means: dict[str, float] | None = None) -> float:
    """L'espérance par setup éligible quand seuls les leviers d'`active` jouent.

    Le dénominateur est le nombre de setups **éligibles**, pas le nombre de
    décisions prises. C'est ce qui rend les coalitions comparables : une
    coalition qui referme le levier d'entrée prend tous les setups, et diviser
    par un dénominateur variable mélangerait la sélectivité au résultat.
    """
    if not journal.decisions:
        return 0.0
    means = session_means if session_means is not None else _session_means(journal)

    total = 0.0
    for d in journal.decisions:
        if d.net_r is None:
            continue
        # Levier « entrée » : ouvert, la décision de l'opérateur ; fermé, on
        # prend tout ce qui était éligible.
        if "entree" in active and not d.taken:
            continue
        # Levier « sortie » : le journal ne porte qu'un résultat par décision.
        # Faute d'une gestion distincte à rejouer, les deux branches
        # coïncident ; la part du levier sera nulle et c'est la vérité, non
        # une approximation.
        outcome = d.net_r
        # Levier « moment » : ouvert, l'issue obtenue ; fermé, l'espérance de
        # la séance — la loi nulle B prise en espérance.
        if "moment" not in active:
            outcome = means.get(d.day, 0.0)
        # Levier « taille » : ouvert, la mise choisie ; fermé, une unité.
        size = d.size if ("taille" in active and d.taken) else 1.0
        total += size * outcome
    return total / journal.n_eligible


def decompose(journal: Journal,
              keys: tuple[str, ...] = KEYS) -> Decomposition:
    """La valeur de Shapley de chaque levier, sur les 2^k coalitions.

    Avec quatre leviers cela fait seize évaluations, chacune linéaire en
    nombre de décisions : la décomposition exacte est moins chère qu'une
    seule loi nulle simulée. Il n'y a donc aucune raison de se contenter
    d'une ablation approchée.
    """
    if not journal.decisions:
        raise ValueError("journal vide : rien à décomposer")
    n = len(keys)
    means = _session_means(journal)

    cache: dict[frozenset[str], float] = {}

    def v(s: frozenset[str]) -> float:
        if s not in cache:
            cache[s] = coalition_value(journal, s, means)
        return cache[s]

    vide, plein = frozenset(), frozenset(keys)
    shares: list[Share] = []
    for i, key in enumerate(keys):
        others = [k for k in keys if k != key]
        phi = 0.0
        for taille in range(n):
            poids = (math.factorial(taille) * math.factorial(n - taille - 1)
                     / math.factorial(n))
            for sub in combinations(others, taille):
                s = frozenset(sub)
                phi += poids * (v(s | {key}) - v(s))
        shares.append(Share(
            key=key, label=LABELS.get(key, key), value=phi, fraction=0.0,
            solo=v(frozenset({key})) - v(vide),
            marginal=v(plein) - v(plein - {key}),
        ))

    total = v(plein) - v(vide)
    if abs(total) > 1e-12:
        shares = [Share(s.key, s.label, s.value, s.value / total,
                        s.solo, s.marginal) for s in shares]
    return Decomposition(tuple(shares), total=total,
                         baseline=v(vide), realised=v(plein))
