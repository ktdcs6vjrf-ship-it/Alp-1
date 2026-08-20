"""Flux d'ordres et liquidité : échelles, persistance, discrimination, impact.

Le vocabulaire
--------------
``L1`` / ``L2`` / ``L3``
    Trois profondeurs de diffusion du carnet. L1 : meilleure limite achat et
    vente, avec sa taille. L2 : tailles agrégées par niveau de prix. L3 : les
    ordres individuels avec leur rang dans la file. La lecture d'absorption
    revendiquée par la pile ALP-1 exige au minimum du L2 horodaté, et une file
    par ordre — donc du L3 — pour distinguer une annulation d'une exécution.

``Bid`` / ``ask``, *resting liquidity*
    Ordres limites en attente à un niveau. Ils forment une file : servie par
    priorité prix puis temps.

``Absorption``
    Un volume agressif important frappe un niveau sans le déplacer : la file y
    est reconstituée aussi vite qu'elle est consommée.

``Sweep``, *liquidity grab*
    L'inverse : un ordre agressif consomme plusieurs niveaux d'un coup.

``Spoofing``
    Affichage d'une taille qu'on n'a pas l'intention d'exécuter, retirée à
    l'approche du prix. La pratique est illégale et néanmoins présente ; du
    point de vue de l'opérateur, elle rend le carnet affiché non fiable en tant
    que tel.

``CVD`` — *Cumulative Volume Delta*
    Somme courante des volumes exécutés à l'ask moins ceux exécutés au bid.
    Mesure la pression agressive nette.

``LPR`` — *Liquidity Persistence Ratio*
    Introduit par ce papier : taille restante au contact rapportée à la taille
    affichée avant le contact. Sépare l'absorption réelle du leurre par une
    mesure et non par une impression.

Le résultat structurant de ce module
------------------------------------
Un signal de carnet a une **demi-vie**. L'information qu'il porte se dissipe à
mesure que la file se reconstitue ou se retire. Or l'espérance d'un trade vaut
``µ·E[τ] − c`` : ce qui compte n'est pas l'intensité instantanée du signal mais
son intégrale sur la durée d'exposition. Un signal dont l'information
s'évanouit en quelques secondes ne peut pas financer une friction d'aller-
retour sur une exposition d'une demi-heure, quelle que soit sa justesse.

La fonction `required_instant_drift` chiffre cette contrainte. Sa conclusion
est nette : à l'échelle du carnet, la lecture de flux relève de l'**exécution**
— où placer l'ordre, quand ne pas traverser le spread — et non de la
prédiction directionnelle sur trente minutes. C'est un déplacement de rôle,
pas un rejet de la couche.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .costs import Contract, norm_cdf

_LN2 = math.log(2.0)


# --- Échelles de liquidité ----------------------------------------------------


@dataclass(frozen=True)
class LiquidityScale:
    """Une échelle de liquidité : sa demi-vie, ce qu'elle porte, son accès.

    Attributes
    ----------
    name:
        Nom de l'échelle.
    half_life_min:
        Demi-vie de l'information qu'elle porte, en minutes.
    carries:
        Ce que l'échelle permet de prédire, dans le meilleur des cas.
    observable:
        Ce qu'il faut pour l'observer et la rejouer. Un signal non enregistrable
        n'est pas backtestable, donc pas falsifiable, donc hors du protocole.
    """

    name: str
    half_life_min: float
    carries: str
    observable: str

    @property
    def tau_min(self) -> float:
        """Constante de temps ``T_c = demi-vie / ln 2``."""
        return self.half_life_min / _LN2


SCALES: tuple[LiquidityScale, ...] = (
    LiquidityScale(
        "Cotation", 0.05,
        "coût d'exécution immédiat ; sens du prochain tick",
        "L1 horodaté à la milliseconde ; non enregistrable depuis un flux vidéo"),
    LiquidityScale(
        "File d'ordres", 0.5,
        "tenue d'un niveau au contact ; absorption contre leurre",
        "L2 horodaté, idéalement L3 pour distinguer annulation et exécution"),
    LiquidityScale(
        "Inventaire", 30.0,
        "pression de rééquilibrage d'un teneur ; épuisement d'un flux forcé",
        "L2 agrégé plus volume signé ; reconstructible depuis les ticks"),
    LiquidityScale(
        "Structurel", 390.0,
        "où la liquidité se trouvera : POC, aire de valeur, murs d'options",
        "données publiques de fin de séance ; entièrement rejouable"),
    LiquidityScale(
        "Positionnement", 1950.0,
        "inventaire des teneurs d'options, expirations, rééquilibrages indiciels",
        "chaînes d'options et open interest publiés quotidiennement"),
)


def captured_drift(instant_drift: float, half_life_min: float,
                   exposure_min: float) -> float:
    """Dérive moyenne effectivement captée par une exposition donnée.

    Le signal est supposé produire une dérive qui décroît exponentiellement :
    ``µ(t) = µ₀·exp(−t/T_c)``. Le déplacement espéré sur l'exposition vaut
    l'intégrale, et la dérive *moyenne* sur la période s'en déduit :

        µ̄ = µ₀·T_c·(1 − e^{−τ/T_c}) / τ.

    Pour une exposition longue devant la demi-vie, ``µ̄ ≈ µ₀·T_c/τ`` : la dérive
    utile est divisée par le rapport des deux durées. Trente minutes de position
    sur un signal d'une demi-vie de trente secondes en conservent 2,4 %.
    """
    if half_life_min <= 0 or exposure_min <= 0:
        raise ValueError("half_life_min et exposure_min doivent être > 0")
    tau_c = half_life_min / _LN2
    return instant_drift * tau_c * (1.0 - math.exp(-exposure_min / tau_c)) / exposure_min


def required_instant_drift(friction_points: float, half_life_min: float,
                           exposure_min: float) -> float:
    """Dérive instantanée exigée d'un signal pour couvrir la friction.

    Inversion de `captured_drift` sous la condition ``µ̄·τ = c`` :

        µ₀ = c / [T_c·(1 − e^{−τ/T_c})].

    C'est le test de recevabilité de toute couche de flux. Un signal de carnet
    de demi-vie trentaine de secondes devrait produire une dérive instantanée
    de plusieurs points par minute — un ordre de grandeur au-dessus de la
    volatilité elle-même — pour financer un aller-retour tenu une demi-heure.
    Comme cette exigence est irrecevable, l'une des trois branches suivantes
    doit être choisie explicitement : réduire l'exposition à l'échelle du
    signal, réduire la friction en entrant passivement, ou reclasser la couche
    en outil d'exécution. ALP-1 retient la troisième.
    """
    if friction_points < 0:
        raise ValueError("friction_points doit être ≥ 0")
    if half_life_min <= 0 or exposure_min <= 0:
        raise ValueError("half_life_min et exposure_min doivent être > 0")
    tau_c = half_life_min / _LN2
    return friction_points / (tau_c * (1.0 - math.exp(-exposure_min / tau_c)))


def usable_horizon(half_life_min: float, retention: float = 0.5) -> float:
    """Horizon au-delà duquel il reste moins que `retention` du signal.

    Donne la durée de position cohérente avec une échelle donnée. Pour une
    demi-vie de trente secondes et une rétention de moitié, l'horizon cohérent
    est trente secondes — pas trente minutes.
    """
    if not 0.0 < retention < 1.0:
        raise ValueError("retention doit être dans ]0, 1[")
    return -half_life_min * math.log(retention) / _LN2


# --- File d'ordres et LPR -----------------------------------------------------


def lpr_expected(hazard_per_min: float, elapsed_min: float) -> float:
    """LPR moyen d'une file dont chaque ordre s'annule au taux `hazard_per_min`.

    Les annulations étant indépendantes, la fraction survivante est
    ``exp(−h·Δt)``. Deux populations séparent alors nettement : une file tenue
    par un intervenant qui veut être exécuté a un taux d'annulation faible ; un
    affichage de leurre a un taux élevé, puisqu'il doit disparaître avant le
    contact.
    """
    if hazard_per_min < 0 or elapsed_min < 0:
        raise ValueError("taux et durée doivent être ≥ 0")
    return math.exp(-hazard_per_min * elapsed_min)


def half_life_from_hazard(hazard_per_min: float) -> float:
    """Demi-vie d'une file à partir de son taux d'annulation."""
    if hazard_per_min <= 0:
        return math.inf
    return _LN2 / hazard_per_min


def lpr_discriminability(depth_contracts: float, hazard_genuine: float,
                         hazard_spoof: float, elapsed_min: float,
                         log_dispersion: float = 0.8) -> float:
    """Distance de séparation ``d'`` entre absorption réelle et leurre.

    Le LPR observé mélange deux sources de variabilité, et les distinguer est
    ce qui rend la mesure honnête.

    *Variabilité de comportement.* Le taux d'annulation n'est pas une constante
    de classe : il varie d'un intervenant à l'autre. On le modélise log-normal
    de dispersion `log_dispersion`, ce qui rend ``−ln LPR = h·Δt`` log-normal
    de même dispersion.

    *Variabilité d'échantillonnage.* La file compte ``N`` contrats qui
    s'annulent indépendamment ; la fraction survivante a pour variance
    ``p(1 − p)/N``, soit ``(1 − p)/(N·p)`` en échelle logarithmique.

    D'où la séparation, en unités d'écart-type :

        d' = |ln(h_leurre / h_réel)| / √(2σ² + v_réel + v_leurre).

    Le résultat est instructif dans les deux sens. La profondeur du niveau
    n'améliore la lecture que lorsqu'elle est très faible — au-delà d'une
    dizaine de contrats, le terme d'échantillonnage disparaît devant la
    dispersion comportementale. Ce qui plafonne la lecture d'absorption n'est
    donc pas la finesse de l'œil ni la taille de la file : c'est le
    recouvrement entre deux façons de se comporter dans le carnet. Aucune
    amélioration d'interface ne le fera baisser.
    """
    if depth_contracts <= 0:
        raise ValueError("depth_contracts doit être > 0")
    if min(hazard_genuine, hazard_spoof) <= 0:
        raise ValueError("les taux d'annulation doivent être > 0")
    if log_dispersion < 0:
        raise ValueError("log_dispersion doit être ≥ 0")
    pg = lpr_expected(hazard_genuine, elapsed_min)
    ps = lpr_expected(hazard_spoof, elapsed_min)
    vg = (1.0 - pg) / (depth_contracts * pg) if pg > 0 else math.inf
    vs = (1.0 - ps) / (depth_contracts * ps) if ps > 0 else math.inf
    var = 2.0 * log_dispersion ** 2 + vg + vs
    if not math.isfinite(var) or var <= 0:
        return 0.0
    return abs(math.log(hazard_spoof / hazard_genuine)) / math.sqrt(var)


def lpr_auc(depth_contracts: float, hazard_genuine: float, hazard_spoof: float,
            elapsed_min: float, log_dispersion: float = 0.8) -> float:
    """Aire sous la courbe ROC du LPR : ``AUC = Φ(d'/√2)``.

    0,50 signifie qu'aucune information n'est extraite ; 1,00 une séparation
    parfaite. Une AUC de 0,75 — valeur déjà optimiste ici — signifie que la
    lecture se trompe une fois sur quatre en comparant deux niveaux tirés au
    hasard, l'un tenu, l'autre retiré.
    """
    d = lpr_discriminability(depth_contracts, hazard_genuine, hazard_spoof,
                             elapsed_min, log_dispersion)
    return norm_cdf(d / math.sqrt(2.0))


def required_separation_for_auc(target_auc: float) -> float:
    """Séparation ``d'`` qu'exige une AUC visée. ``d' = √2·Φ⁻¹(AUC)``.

    Convertit une ambition de lecture — « distinguer correctement neuf fois sur
    dix » — en une exigence sur la mesure. Une AUC de 0,90 demande ``d' ≈ 1,8``,
    c'est-à-dire un rapport de taux d'annulation de l'ordre de ``e^{2,1} ≈ 8``
    entre les deux populations sous une dispersion de 0,8. Le protocole doit
    donc commencer par estimer ce rapport, avant toute évaluation de la couche.
    """
    if not 0.5 < target_auc < 1.0:
        raise ValueError("target_auc doit être dans ]0,5 ; 1[")
    return math.sqrt(2.0) * _inv_norm(target_auc)


def _inv_norm(p: float) -> float:
    lo, hi = -12.0, 12.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# --- Impact et friction endogène ---------------------------------------------


def impact_ticks(size_contracts: float, depth_contracts: float) -> float:
    """Impact d'un ordre agressif, en ticks, sur un carnet de profondeur donnée.

    Modèle de carnet uniforme : chaque niveau porte `depth_contracts`, et
    l'ordre consomme les niveaux successifs, d'où ``impact = taille /
    profondeur`` ticks. C'est la forme continue du coefficient de Kyle,
    ``λ = tick / profondeur`` — impact linéaire en taille, inverse de la
    profondeur. La version discrète compte les niveaux entiers franchis,
    ``⌈Q/D⌉ − 1`` ; les deux coïncident dès que l'ordre traverse plusieurs
    niveaux, et la forme continue est retenue ici parce qu'elle est dérivable
    et se compose proprement avec le modèle de friction.
    """
    if depth_contracts <= 0:
        raise ValueError("depth_contracts doit être > 0")
    if size_contracts <= 0:
        return 0.0
    return size_contracts / depth_contracts


def kyle_lambda(tick_size: float, depth_contracts: float) -> float:
    """Impact de prix par contrat, en points d'indice."""
    if depth_contracts <= 0:
        raise ValueError("depth_contracts doit être > 0")
    return tick_size / depth_contracts


def effective_friction(contract: Contract, commission_rt: float,
                       size_contracts: float, depth_at_entry: float,
                       depth_at_exit: float) -> float:
    """Friction aller-retour endogène, fonction de la liquidité rencontrée.

    La friction du module `costs` est un paramètre ; elle est en réalité une
    variable d'état du carnet. Sortir au stop pendant le mouvement même qui l'a
    déclenché, c'est traverser un carnet aminci : c'est le cas où
    `depth_at_exit` est une fraction de `depth_at_entry`, et où la friction
    payée excède celle qui avait été budgétée.

    Cette dépendance a une conséquence directe sur le critère maître. Le seuil
    ``µ* = c/E[τ]`` n'est pas un nombre fixe : il monte précisément dans les
    conditions où la stratégie prend ses pertes. Toute estimation de `c` faite
    sur les seules entrées est optimiste par construction.
    """
    slip_entry = 0.5 + impact_ticks(size_contracts, depth_at_entry)
    slip_exit = 0.5 + impact_ticks(size_contracts, depth_at_exit)
    usd = commission_rt + (slip_entry + slip_exit) * contract.tick_value
    return usd / contract.point_value


# --- CVD et divergences -------------------------------------------------------


def p_sign_divergence(correlation: float) -> float:
    """Fréquence nulle d'une divergence de signe entre prix et CVD.

    Pour un couple gaussien de corrélation ``ρ``, le théorème de Sheppard donne
    ``P(X > 0, Y > 0) = ¼ + arcsin(ρ)/(2π)``, d'où

        P(signes opposés) = ½ − arcsin(ρ)/π.

    Prix et CVD sont fortement corrélés à l'échelle intraséance — l'agressivité
    nette *est* une des causes du déplacement. Mais une corrélation de 0,80
    laisse encore une fenêtre sur cinq en désaccord de signe, **sans qu'aucune
    information ne soit présente**. Une divergence CVD n'est donc un signal que
    si sa fréquence observée excède cette valeur, et sa fréquence brute ne dit
    rien tant que la corrélation de référence n'a pas été mesurée.
    """
    if not -1.0 < correlation < 1.0:
        raise ValueError("correlation doit être dans ]−1, 1[")
    return 0.5 - math.asin(correlation) / math.pi


def divergence_excess(observed_frequency: float, correlation: float) -> float:
    """Écart entre fréquence observée de divergence et sa valeur nulle."""
    return observed_frequency - p_sign_divergence(correlation)


def trades_to_detect_excess(excess: float, base_rate: float,
                            z: float = 2.0) -> float:
    """Observations nécessaires pour distinguer un excès de divergence du hasard.

    Test de proportion à un échantillon : ``n = z²·p(1 − p)/Δ²``. Rappelle que
    la détection d'un écart de deux points de pourcentage sur une fréquence de
    20 % demande plusieurs milliers d'observations — la mesure est possible,
    mais elle n'est pas anecdotique.
    """
    if excess <= 0:
        return math.inf
    if not 0.0 < base_rate < 1.0:
        raise ValueError("base_rate doit être dans ]0, 1[")
    return (z ** 2) * base_rate * (1.0 - base_rate) / (excess ** 2)
