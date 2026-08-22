"""L'edge discrétionnaire, rendu décidable sans être expliqué.

Un opérateur affirme qu'il possède un avantage qu'il ne sait pas formuler :
une lecture, un tour de main, quelque chose qui se voit à l'écran et se perd à
l'écrit. Le reste du dépôt ne peut rien pour un signal qu'on ne code pas — et
c'est exactement pourquoi ce module ne demande pas qu'on le code.

**Ce qu'un opérateur peut être, dans ce cadre.** Le théorème d'invariance
interdit qu'une règle d'arrêt crée de l'espérance. Il ne dit rien de la
*sélection des moments*. En reprenant le critère maître pour un opérateur dont
la dérive locale au moment de son entrée vaut `µ_t` et l'exposition `τ_t` :

    E[R] = E[µ_t · τ_t] − c = E[µ]·E[τ] + Cov(µ, τ) − c

et le premier terme est ce que la règle scellée obtient déjà. **Tout l'écart
tient dans la covariance entre la dérive locale et l'exposition choisie.**
C'est l'énoncé exact de ce qu'un talent discrétionnaire peut être ici : non pas
une prévision de direction, mais une allocation d'exposition corrélée à la
dérive. L'énoncé a deux conséquences immédiates, et elles sont opposées.

D'un côté, le talent est mesurable **sans être décrit** : on n'a pas besoin de
savoir ce que l'opérateur regarde pour mesurer la covariance qu'il produit.
De l'autre, il est borné par ce que la dérive vaut : sous dérive nulle, la
covariance est nulle aussi, et un opérateur qui prend plus de positions que la
règle perd exactement la friction supplémentaire. Un talent ne fabrique pas de
dérive ; il en répartit une.

**Le dispositif : apparier plutôt que comparer.** Mesurer un opérateur contre
zéro exige l'échantillon que le document chiffre en années. Le mesurer contre
**la règle scellée, sur les mêmes séances**, est un autre problème : la
différence `D = R_opérateur − R_règle` a pour variance `2σ²(1 − ρ)`, et les
deux bras affrontent le même marché aux mêmes heures, donc `ρ` est élevé. Le
gain d'échantillon vaut `1/(1 − ρ)` : à `ρ = 0,80`, **cinq fois moins
d'observations pour la même puissance.**

Le second avantage est plus important que le premier, et il n'est pas de
variance. La dérive commune s'élimine dans la différence : **le dispositif
apparié reste décidable quand la dérive empruntée a fini de se déprécier.** Le
document date sa propre péremption entre 2027 et 2030 ; la question « cet
opérateur fait-il mieux que sa règle ? » n'a pas de date de péremption, parce
qu'elle ne repose sur aucune dérive publiée.

**Le prix, et il est déjà chiffré ailleurs.** `alp1.discipline` montre qu'une
dérogation prise en regardant le marché double la famille de configurations,
et que quatre suffisent à détruire la valeur probante du protocole. Le même
geste, **déclaré à l'avance comme un bras**, coûte une comparaison et une
seule. La différence entre un talent et une indiscipline n'est pas dans le
geste : elle est dans la date à laquelle il a été déclaré.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .costs import _norm_ppf
from .discipline import effective_trials

#: Corrélation entre les deux bras, encadrée. Deux bras qui tradent le même
#: contrat aux mêmes heures partagent l'essentiel de leur variance ; la borne
#: basse suppose un opérateur qui ne prend presque jamais les mêmes trades que
#: la règle, la borne haute un opérateur qui la suit à quelques filtres près.
RHO_BOX = (0.40, 0.70, 0.90)

#: Nombre de bras d'un dispositif apparié déclaré : la règle et l'opérateur.
ARMS = 2


# --- Ce qu'un talent peut être ----------------------------------------------

def expectation(mean_drift: float, mean_exposure: float,
                cov_drift_exposure: float, friction: float) -> float:
    """Espérance nette d'un opérateur, décomposée selon le critère maître.

    ``E[R] = E[µ]·E[τ] + Cov(µ, τ) − c``. Les unités sont libres pourvu
    qu'elles soient cohérentes ; le document les prend en points d'indice.
    """
    return mean_drift * mean_exposure + cov_drift_exposure - friction


def talent_value(cov_drift_exposure: float, extra_friction: float) -> float:
    """Ce que le talent ajoute à la règle, net de ce qu'il coûte en friction.

    Un opérateur qui entre plus souvent que la règle paie la différence de
    friction, que sa lecture soit bonne ou non. Le talent net est donc la
    covariance qu'il produit **moins** les allers-retours qu'il ajoute.
    """
    return cov_drift_exposure - extra_friction


def required_covariance(extra_friction: float, margin: float = 1.0) -> float:
    """Covariance minimale qu'un opérateur doit produire pour valoir sa friction.

    Le seuil est `margin` fois la friction supplémentaire. À `margin = 1`, il
    s'agit du point mort ; au-delà, de la marge qu'on exige avant d'engager.
    """
    if margin <= 0.0:
        raise ValueError("margin doit être > 0")
    return extra_friction * margin


def breakeven_hit_of_discretion(rule_expectancy: float, extra_trades: float,
                                friction: float) -> float:
    """Espérance par trade supplémentaire pour ne pas dégrader la règle.

    Un opérateur qui ajoute `extra_trades` entrées par séance à une règle dont
    l'espérance vaut `rule_expectancy` ne dégrade pas l'ensemble si chacune de
    ses entrées supplémentaires rapporte au moins zéro net — soit la friction
    entière, puisque la dérive n'est acquise à personne. Le nombre rendu est
    ce que chaque entrée discrétionnaire doit produire **brut**.
    """
    if extra_trades <= 0.0:
        return 0.0
    del rule_expectancy
    return friction


# --- Le dispositif apparié ---------------------------------------------------

def variance_factor(rho: float) -> float:
    """Facteur de variance de la différence appariée : ``2(1 − ρ)``."""
    if not -1.0 <= rho <= 1.0:
        raise ValueError("rho doit être dans [−1, 1]")
    return 2.0 * (1.0 - rho)


def variance_reduction(rho: float) -> float:
    """Gain d'échantillon du dispositif apparié sur le dispositif à deux bras.

    Vaut ``1/(1 − ρ)`` : c'est le rapport entre la variance de la différence
    de deux bras indépendants et celle de la différence appariée.
    """
    if rho >= 1.0:
        return math.inf
    return 1.0 / (1.0 - rho)


def pairs_for_talent(delta: float, sd: float, rho: float,
                     alpha: float = 0.05, power: float = 0.80,
                     n_arms: int = ARMS) -> float:
    """Séances appariées pour détecter un écart `delta` entre bras.

    Test unilatéral sur la moyenne d'une différence appariée :

        N = (z_{α/m} + z_β)² · 2σ²(1 − ρ) / δ².

    `n_arms` entre par le seul canal légitime : un dispositif à plusieurs bras
    déclarés corrige son seuil, et le coût est logarithmique. C'est la
    différence exacte avec la dérogation, dont le coût est exponentiel.
    """
    if delta <= 0.0:
        return math.inf
    if sd <= 0.0:
        raise ValueError("sd doit être > 0")
    comparaisons = max(n_arms - 1, 1)
    za = _norm_ppf(1.0 - alpha / comparaisons)
    zb = _norm_ppf(power)
    return ((za + zb) ** 2) * variance_factor(rho) * sd * sd / (delta * delta)


def detectable_talent(n_pairs: float, sd: float, rho: float,
                      alpha: float = 0.05, power: float = 0.80,
                      n_arms: int = ARMS) -> float:
    """Écart minimal détectable pour un budget de séances donné.

    Réciproque de `pairs_for_talent`. C'est le nombre à publier avant de
    commencer : un dispositif qui ne dit pas ce qu'il peut détecter ne peut
    rien conclure de son propre silence.
    """
    if n_pairs <= 0.0:
        return math.inf
    comparaisons = max(n_arms - 1, 1)
    za = _norm_ppf(1.0 - alpha / comparaisons)
    zb = _norm_ppf(power)
    return (za + zb) * sd * math.sqrt(variance_factor(rho) / n_pairs)


@dataclass(frozen=True)
class Design:
    """Un protocole apparié : ce qu'il exige, ce qu'il détecte, ce qu'il dure."""

    rho: float
    sd: float
    delta: float
    n_pairs: float
    sessions_per_year: float
    detectable: float

    @property
    def years(self) -> float:
        return self.n_pairs / self.sessions_per_year

    @property
    def gain(self) -> float:
        """Facteur d'échantillon gagné sur un dispositif non apparié."""
        return variance_reduction(self.rho)

    @property
    def conclusive(self) -> bool:
        """Vrai si l'écart visé dépasse ce que le budget permet de détecter."""
        return self.delta >= self.detectable


def plan(delta: float, sd: float, rho: float, budget_sessions: float,
         sessions_per_year: float = 252.0, alpha: float = 0.05,
         power: float = 0.80, n_arms: int = ARMS) -> Design:
    """Le protocole apparié complet, pour un écart visé et un budget."""
    n = pairs_for_talent(delta, sd, rho, alpha, power, n_arms)
    return Design(rho=rho, sd=sd, delta=delta, n_pairs=n,
                  sessions_per_year=sessions_per_year,
                  detectable=detectable_talent(budget_sessions, sd, rho,
                                               alpha, power, n_arms))


# --- Bras déclaré contre dérogation ------------------------------------------

def declared_cost(n_arms: int) -> float:
    """Configurations d'un dispositif à `n_arms` bras déclarés à l'avance.

    Un bras déclaré est une comparaison, pas une exploration : la famille
    compte `n_arms − 1` tests, et le seuil se corrige par ce nombre.
    """
    if n_arms < 1:
        raise ValueError("n_arms doit être ≥ 1")
    return float(max(n_arms - 1, 1))


def deviation_families(n_deviations: float) -> float:
    """Configurations d'une discrétion **non déclarée**, via `discipline`.

    Chaque dérogation est un choix binaire pris en regardant les données : la
    famille double. `discipline.effective_trials` porte déjà ce calcul, et le
    module se contente de l'appeler pour que les deux régimes soient chiffrés
    par la même fonction.
    """
    return effective_trials(n_deviations)


def declaration_gain(n_deviations: float, n_arms: int = ARMS) -> float:
    """Rapport des deux familles : ce que déclarer à l'avance fait économiser.

    Le rapport croît exponentiellement en nombre de dérogations, et c'est le
    seul argument dont le module a besoin : la déclaration préalable est
    gratuite, son absence ne l'est pas.
    """
    return deviation_families(n_deviations) / declared_cost(n_arms)


# --- Ce qui invalide un dispositif apparié ----------------------------------

#: Les quatre défauts qui rendent un appariement non concluant. Aucun n'est
#: réparable après la collecte, et chacun se prévient à coût nul.
CONTAMINATIONS = (
    ("execution_conditionnelle",
     "le bras règle n'est joué que lorsque l'opérateur ne prend pas la main : "
     "les deux bras cessent d'affronter la même séance"),
    ("information_asymetrique",
     "l'opérateur voit l'entrée de la règle avant de décider : la différence "
     "mesure une réaction à la règle, pas une lecture du marché"),
    ("regle_ajustee",
     "la règle est modifiée pendant la collecte : le comparateur bouge, et "
     "l'écart cesse d'avoir un référent"),
    ("selection_des_seances",
     "les séances où l'opérateur ne se sent pas prêt sont retirées : la "
     "sélection porte sur l'issue par le canal de l'état de l'opérateur"),
)


def audit(paired_sessions: int, rule_sessions: int, operator_sessions: int,
          rule_versions: int = 1) -> list[str]:
    """Ce qui, dans un appariement déjà collecté, empêche de conclure."""
    defauts: list[str] = []
    if rule_sessions != operator_sessions:
        defauts.append(
            f"bras déséquilibrés : {rule_sessions} séances pour la règle, "
            f"{operator_sessions} pour l'opérateur — l'appariement est partiel")
    if paired_sessions < min(rule_sessions, operator_sessions):
        manque = min(rule_sessions, operator_sessions) - paired_sessions
        defauts.append(f"{manque} séance(s) non appariée(s) : la variance "
                       "commune n'y est pas éliminée")
    if rule_versions > 1:
        defauts.append(f"{rule_versions} versions de la règle sur la période : "
                       "le comparateur a bougé pendant la mesure")
    return defauts


def main() -> None:
    from .report7 import main as report7_main
    report7_main()


if __name__ == "__main__":
    main()
