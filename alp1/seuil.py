"""Le seuil, et non le signal : où l'avantage intraday est réellement décidé.

Les deux premiers documents établissent que la dérive `µ` n'est pas détectable
avec l'échantillon disponible. C'est vrai, c'est mesuré par trois routes
indépendantes, et rien ici ne le remet en cause.

Mais la question posée n'était pas la bonne. Un trade n'a pas besoin que `µ`
soit *démontrable* : il a besoin que `µ` dépasse le seuil que la géométrie
impose. L'identité de Wald, appliquée avec un temps borné par la séance, le dit
en une ligne :

    E[R] = (µ · E[τ∧T] − c) / a          et donc      µ* = c / E[τ∧T]

`µ` est une propriété du marché, hors de portée de l'opérateur. **`µ*` est une
propriété de la géométrie, entièrement sous son contrôle.** C'est là qu'est
l'avantage exploitable, et il est arithmétique là où `µ` est statistique.

Ce que ce module corrige
------------------------
`quant.reference_drift()` vaut `DRIFT_MULTIPLE × c / E[τ]`, c'est-à-dire deux
fois le seuil de rentabilité. La dérive y est **définie** à partir de la
friction : l'avantage n'est pas dérivé, il est supposé. Cette dérive supposée
vaut 16,4 points par heure, soit 5,1 fois la borne haute du domaine que la
figure du mur d'échantillon appelle plausible. Les chapitres de risque du
document nº 1 tournent donc sous une dérive que le document lui-même juge
invraisemblable.

Ici la dérive est un **paramètre déclaré**, jamais dérivé de la friction, et
son domaine plausible est cité explicitement.

La loi nulle
------------
À `µ = 0`, `E[R] = −c/a` pour toute géométrie : négatif partout, et l'optimum
est de ne pas trader. Aucune géométrie ne crée d'espérance — c'est le théorème
d'arrêt optionnel, et il reste vrai. Ce module ne prétend donc pas produire un
avantage à partir de rien. Il établit une chose plus faible et plus utile :
*conditionnellement à une dérive positive*, la géométrie décide si on la garde
ou si la friction la mange.
"""

from __future__ import annotations

from dataclasses import dataclass

from .costs import COST_BASE, ES, Contract, CostModel, stop_points
from .horizon import outcome_scaled
from . import quant as q

#: Domaine de dérive que le document nº 1 traite comme plausible, en points
#: d'indice par heure. C'est l'abscisse de sa figure du mur d'échantillon. Il
#: est déclaré ici pour que tout verdict d'atteignabilité soit rapporté à une
#: borne écrite, et non à une intuition.
PLAUSIBLE_DRIFT_PER_HOUR = (0.6, 3.2)

#: Grille de largeurs de stop balayée, en pourcentage de l'indice. Elle part du
#: stop déclaré par l'opérateur et va jusqu'à ce que l'exposition sature contre
#: la séance.
STOP_GRID_PCT = (0.010, 0.025, 0.050, 0.075, 0.100,
                 0.150, 0.200, 0.300, 0.400, 0.600)


@dataclass(frozen=True)
class Geometry:
    """Une géométrie, et ce qu'elle exige du signal pour être rentable."""

    stop_pct: float
    stop_points: float
    exposure_min: float      # E[τ∧T], borné par la séance
    friction_points: float   # c, aller-retour
    break_even_per_hour: float   # µ* = c/E[τ], en points par heure

    @property
    def friction_ratio(self) -> float:
        """`c/L` — la fraction du risque nominal mangée par la friction."""
        return self.friction_points / self.stop_points

    @property
    def reachable(self) -> bool:
        """Le seuil tombe-t-il dans le domaine de dérive plausible ?"""
        return self.break_even_per_hour <= PLAUSIBLE_DRIFT_PER_HOUR[1]

    def expectancy_r(self, drift_per_hour: float) -> float:
        """`E[R]` en multiples du risque, par l'identité de Wald.

        Le temps est celui borné par la séance : un trade qui n'a touché
        aucune barrière est fermé à la clôture, et c'est cette troncature qui
        empêche l'espérance de croître indéfiniment avec la largeur du stop.
        """
        gagne = drift_per_hour / 60.0 * self.exposure_min
        return (gagne - self.friction_points) / self.stop_points


def geometry(stop_pct: float, cost: CostModel | None = None,
             contract: Contract = ES,
             reward_risk: float = q.RR_REF) -> Geometry:
    """La géométrie complète pour une largeur de stop donnée."""
    cost = cost if cost is not None else COST_BASE
    a = stop_points(q.INDEX_LEVEL, stop_pct)
    o = outcome_scaled(a, reward_risk * a, q.SESSION_MIN, q.SIGMA_1MIN, q.HURST)
    c = cost.friction_points(contract)
    return Geometry(stop_pct, a, o.expected_time, c,
                    c / o.expected_time * 60.0)


def scan(cost: CostModel | None = None, contract: Contract = ES,
         grid: tuple[float, ...] = STOP_GRID_PCT) -> tuple[Geometry, ...]:
    """La grille entière, du stop déclaré à la saturation de séance."""
    return tuple(geometry(p, cost, contract) for p in grid)


def best(drift_per_hour: float, cost: CostModel | None = None,
         contract: Contract = ES,
         grid: tuple[float, ...] = STOP_GRID_PCT) -> Geometry:
    """La géométrie qui maximise `E[R]` sous la dérive déclarée.

    L'optimum est **intérieur** et il l'est pour une raison mécanique : trop
    serré, la friction domine — `c/a` explose et `E[τ]` est trop court pour
    que la dérive agisse ; trop large, `E[τ]` sature contre la séance pendant
    que `a` continue de croître, et `E[R]` retombe en `1/a`.
    """
    return max(scan(cost, contract, grid),
               key=lambda g: g.expectancy_r(drift_per_hour))
