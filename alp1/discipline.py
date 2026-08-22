"""La discipline comme multiplicité : ce qu'une dérogation coûte en preuve.

Un opérateur qui demande si son tempérament, son sommeil ou son sport lui
donnent un avantage pose une question mal formée, et la reformuler la rend
décidable.

Dans le cadre de ce document, rien de ce qu'un opérateur *est* ne crée de
dérive. La dérive est une propriété du prix ; le théorème d'invariance
interdit qu'une décision de sortie en fabrique, et aucun état physiologique
ne change cette algèbre. Ce que l'état de l'opérateur décide, c'est autre
chose, et c'est mesurable : **exécute-t-il la règle scellée, ou en
dévie-t-il ?**

**Le résultat.** Une dérogation n'est pas une erreur de plus ou de moins
dans un échantillon : c'est une configuration supplémentaire explorée. Un
opérateur qui, sur `N` signaux, décide `k` fois de passer outre — prendre une
entrée non prévue, sauter une entrée prévue — n'a pas exécuté la stratégie
scellée. Il a exécuté l'une des `2^k` stratégies que ces `k` choix binaires
engendrent, et il a choisi laquelle en regardant le marché. Le seuil de
sélection déflaté ne se calcule alors plus sur les trois configurations du
sceau mais sur ce nombre-là, et il croît en `√(2·ln n_essais)`.

La conséquence est brutale et se chiffre en une ligne : **dix dérogations
suffisent à porter le budget de trois configurations à plus de mille**, ce
qui relève le seuil de sélection d'un facteur qu'aucune amélioration de
signal ne compense. La discipline cesse d'être une vertu molle pour devenir
la condition qui préserve le contenu informationnel de l'échantillon.

**Ce que la littérature apporte, et où elle s'arrête.** Lo et Repin (2002)
mesurent les réponses physiologiques d'opérateurs professionnels et les
relient à la volatilité ; Coates et Herbert (2008) montrent que le cortisol
d'opérateurs de salle suit la variance du marché et que la testostérone suit
les gains. Ces travaux documentent ce qui **fait varier le taux de
dérogation** — l'état physiologique, la série de pertes récente, la privation
de sommeil. Ils ne documentent aucune dérive de prix, et ce module ne leur en
fait pas dire. Ils entrent ici comme des déterminants d'un paramètre, non
comme une source d'avantage.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .costs import deflated_threshold_sharpe

#: Budget de configurations scellé par le protocole.
SEALED_BUDGET = 3


@dataclass(frozen=True)
class Deviation:
    """Ce qu'un taux de dérogation fait au seuil de sélection."""

    rate: float
    n_trades: int
    n_deviations: float
    effective_trials: float
    threshold: float
    sealed_threshold: float

    @property
    def inflation(self) -> float:
        """Facteur par lequel le seuil de sélection est relevé."""
        if self.sealed_threshold <= 0:
            return math.inf
        return self.threshold / self.sealed_threshold

    def clears(self, sharpe_trade: float) -> bool:
        """Le Sharpe attendu franchit-il encore le seuil ainsi relevé ?"""
        return sharpe_trade > self.threshold


def effective_trials(n_deviations: float,
                     budget: int = SEALED_BUDGET) -> float:
    """Configurations effectivement explorées après `k` dérogations.

    Chaque dérogation est un choix binaire pris en regardant le marché : la
    famille de stratégies réalisables double. Le budget scellé les multiplie,
    puisque la dérogation s'ajoute au choix de configuration plutôt qu'il ne
    le remplace.

    Le nombre croît exponentiellement, et c'est le fait qui décide : la borne
    n'est pas atteinte progressivement mais franchie d'un coup, après une
    poignée de dérogations.
    """
    if n_deviations < 0:
        raise ValueError("n_deviations doit être ≥ 0")
    if budget < 1:
        raise ValueError("budget doit être ≥ 1")
    return budget * (2.0 ** n_deviations)


def deviation_cost(rate: float, n_trades: int,
                   budget: int = SEALED_BUDGET) -> Deviation:
    """Seuil de sélection sous un taux de dérogation donné.

    `rate` est la part des signaux sur lesquels l'opérateur passe outre la
    règle. Le nombre attendu de dérogations vaut ``rate · N``, et le seuil se
    calcule sur les configurations que ces dérogations engendrent.
    """
    if not 0.0 <= rate <= 1.0:
        raise ValueError("rate doit être dans [0, 1]")
    if n_trades < 1:
        raise ValueError("n_trades doit être ≥ 1")
    k = rate * n_trades
    n_eff = effective_trials(k, budget)
    return Deviation(
        rate=rate, n_trades=n_trades, n_deviations=k,
        effective_trials=n_eff,
        threshold=deflated_threshold_sharpe(max(2.0, n_eff), n_trades),
        sealed_threshold=deflated_threshold_sharpe(budget, n_trades),
    )


def breaking_deviations(sharpe_trade: float, n_trades: int,
                        budget: int = SEALED_BUDGET) -> float:
    """Nombre de dérogations qui annule la significativité du résultat.

    On cherche `k` tel que le seuil déflaté à ``budget·2^k`` configurations
    rejoigne le Sharpe attendu. De
    ``SR = √(2·ln(budget·2^k)/N)`` on tire

        k = (N·SR²/2 − ln budget) / ln 2.

    C'est le nombre de fois où l'opérateur peut passer outre sa propre règle
    avant que cinq années de données ne vaillent plus rien. Il est petit.
    """
    if sharpe_trade <= 0:
        return 0.0
    if n_trades < 1:
        raise ValueError("n_trades doit être ≥ 1")
    k = (n_trades * sharpe_trade ** 2 / 2.0 - math.log(budget)) / math.log(2.0)
    return max(0.0, k)


def breaking_rate(sharpe_trade: float, n_trades: int,
                  budget: int = SEALED_BUDGET) -> float:
    """Taux de dérogation de rupture, en part des signaux."""
    k = breaking_deviations(sharpe_trade, n_trades, budget)
    return min(1.0, k / n_trades) if n_trades else 0.0


def grid(sharpe_trade: float, n_trades: int,
         rates: tuple[float, ...] = (0.0, 0.001, 0.005, 0.01, 0.02, 0.05),
         budget: int = SEALED_BUDGET) -> list[Deviation]:
    """Le seuil de sélection sur une grille de taux de dérogation."""
    return [deviation_cost(r, n_trades, budget) for r in rates]
