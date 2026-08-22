"""Le forçage : répéter l'entrée jusqu'à ce qu'elle passe, et ce que cela coûte.

Un opérateur décrit sa pratique ainsi : il prend le même signal, se fait
sortir, le reprend, se fait sortir encore, et recommence jusqu'à ce que le
mouvement parte. Il observe des séries de cinq à six échecs consécutifs, et
il engage deux pour cent du capital à chaque tentative sur un stop de cinq à
dix millièmes de pour cent du prix.

Ce module traite cette pratique comme le reste du document traite les autres :
il lui donne une définition calculatoire, une loi nulle, et un prédicat
testable. Rien de ce qui suit ne suppose que la pratique soit mauvaise ; tout
y est déduit de la géométrie qu'elle emploie.

**Le théorème du forçage.** Chaque tentative est un problème de premier
passage avec stop `L`, target `R·L` et friction `c`. Sous un prix sans dérive,
la probabilité de toucher le target avant le stop vaut `p = 1/(R+1)`, et le
nombre de tentatives jusqu'à la première réussite suit une loi géométrique de
moyenne `1/p = R+1`. Le résultat total attendu vaut alors

    E[forçage] = R·L − (R+1−1)·L − (R+1)·c = −(R+1)·c

soit **exactement `(R+1)` fois la friction, et rien d'autre**. Le forçage ne
crée pas d'espérance ; il en détruit `R+1` fois plus qu'une tentative unique,
parce qu'il paie `R+1` allers-retours pour un seul aboutissement. C'est le
théorème d'arrêt optionnel, appliqué à une règle d'arrêt sur la *séquence* de
trades plutôt que sur le trajet du prix.

**La série d'échecs n'est pas de la malchance.** `P(k échecs consécutifs) =
(1 − p)^k`. À un ratio de 1:20, `p = 4,76 %` et six échecs de suite surviennent
avec probabilité **74,6 %**. L'opérateur qui en observe cinq ou six n'a pas
subi un accident : il a observé la médiane. Une pratique dont la conséquence
prévue est déjà réalisée n'a pas de mystère à expliquer.

**Le point mort n'est pas mort.** La friction reste due dans toutes les
issues, sortie au point mort comprise. Une sortie « à BE » coûte donc `c/L` en
multiples du risque — 11 % à un stop de cinq centièmes de pour cent, **55 % à
un centième, 110 % à un demi-millième**. À la géométrie la plus serrée, une
sortie au point mort coûte plus cher qu'un stop entier n'en coûtait à la
géométrie que le document retenait auparavant. Et comme un journal de trading
retire habituellement les sorties à BE du dénominateur du taux de réussite,
c'est l'issue la plus fréquente qui disparaît des statistiques tenues.

**Le spread mange une part du stop avant que le marché ne bouge.** Dans le
modèle de Roll (1984), le prix observé oscille entre bid et ask autour d'un
prix efficient inchangé. Une entrée à l'ask et un stop `L` sous l'entrée sont
touchés dès que le prix efficient a baissé de `L − s`, où `s` est le spread
complet : **le stop utile n'est pas `L` mais `L − s`**. Un stop inférieur au
spread est touché au premier rafraîchissement de cotation, sans qu'aucun prix
n'ait bougé.

**Quand une règle de stop ajoute-t-elle de la valeur ?** Kaminski et Lo (2014)
tranchent la question sur données et le résultat est net : sous l'hypothèse de
marche aléatoire, une règle de stop simple **diminue toujours** l'espérance ;
en présence de momentum, elle peut en ajouter. Le document a mesuré l'exposant
d'échelle de sa propre série de contrôle et trouvé `Ĥ = 0,5014` une fois
corrigé du biais de l'estimateur. Le forçage n'est donc pas une pratique
neutre dont la valeur dépendrait de l'exécution : c'est une pratique dont la
valeur dépend d'une propriété du prix, et cette propriété est celle que le
document n'a pas trouvée.

Références employées, et leur statut :

- Kaminski, K. et Lo, A. « When Do Stop-Loss Rules Stop Losses ? », *Journal
  of Financial Markets* 18, 2014 — résultat de signe, repris tel quel.
- Osler, C. « Currency Orders and Exchange Rate Dynamics », *Journal of
  Finance* 58(5), 2003, et « Stop-Loss Orders and Price Cascades in Currency
  Markets », *JIMF* 24(2), 2005 — groupement des stops et cascades.
- Roll, R. « A Simple Implicit Measure of the Effective Bid-Ask Spread »,
  *Journal of Finance* 39(4), 1984 — rebond de cotation.
- Barber, Lee, Liu et Odean, « The Cross-Section of Speculator Skill »,
  *Journal of Financial Markets* 18, 2014 — moins de 1 % des opérateurs
  intrajournaliers dégagent un résultat positif net de frais de façon
  prévisible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .barriers import prob_touch_single_barrier
from .costs import Contract, CostModel, stop_points
from .mc import Rng

#: Fraction du capital engagée par tentative. **Déclarée par l'opérateur.**
RISK_PER_TRADE = 0.02

#: Longueurs de série observées par l'opérateur, en échecs consécutifs.
OBSERVED_STREAK = (5, 6)

#: Exposant d'échelle mesuré par `varratio` sur la série de contrôle, corrigé
#: du biais de l'estimateur. Sert de verdict de régime, non de calibration.
MEASURED_HURST = 0.5014


# --- La géométrie, lue en ticks et en levier ---------------------------------

def stop_ticks(contract: Contract, index_level: float, stop_pct: float) -> float:
    """Largeur du stop en ticks du contrat.

    C'est la seule unité dans laquelle un stop se juge : un stop se compare au
    pas de cotation et au spread, non au prix. Sous deux ou trois ticks, la
    question n'est plus de savoir si le signal est bon.
    """
    if contract.tick_size <= 0:
        raise ValueError("tick_size doit être > 0")
    return stop_points(index_level, stop_pct) / contract.tick_size


def friction_ticks(contract: Contract, cost: CostModel) -> float:
    """Friction aller-retour, en ticks du contrat."""
    return cost.friction_points(contract) / contract.tick_size


def friction_over_stop(contract: Contract, cost: CostModel,
                       index_level: float, stop_pct: float) -> float:
    """`c/L` pour un contrat donné. Au-dessus de un, le trade est déjà perdu.

    Le rapport ne dépend pas du signal, ne dépend pas du marché, et se calcule
    avant d'ouvrir quoi que ce soit. C'est le premier nombre à écrire.
    """
    stop = stop_points(index_level, stop_pct)
    if stop <= 0:
        raise ValueError("stop_pct doit être > 0")
    return cost.friction_points(contract) / stop


def leverage(risk_fraction: float, stop_pct: float) -> float:
    """Levier notionnel impliqué par un risque en capital et un stop en prix.

    Risquer une fraction `f` du capital sur un déplacement de `stop_pct` du
    prix impose une exposition notionnelle de `f / (stop_pct/100)` fois le
    capital. Le levier n'est donc **pas un choix indépendant** : il est fixé
    par le couple, et il l'est avant toute considération de signal.
    """
    if stop_pct <= 0:
        raise ValueError("stop_pct doit être > 0")
    return risk_fraction / (stop_pct / 100.0)


def gap_wipeout(risk_fraction: float, stop_pct: float,
                gap_pct: float) -> float:
    """Fraction du capital effacée par un écart de prix de `gap_pct`.

    Un stop ne franchit pas un trou de cotation. Au levier qu'impose la
    géométrie, un écart d'ouverture ordinaire ne coûte pas une position : il
    coûte plusieurs fois le capital.
    """
    return leverage(risk_fraction, stop_pct) * gap_pct / 100.0


# --- Ce que le spread prend avant que le marché ne bouge ---------------------

def effective_stop(stop_points_: float, spread_points: float) -> float:
    """Déplacement du prix efficient requis pour toucher le stop.

    Modèle de Roll : le prix observé vaut le prix efficient plus ou moins un
    demi-spread. Une entrée à l'ask et un stop `L` sous l'entrée sont touchés
    dès que le prix efficient a baissé de `L − s`. Rendu négatif ou nul quand
    le stop est plus étroit que le spread — le stop est alors touché au
    premier rafraîchissement, sans mouvement.
    """
    return stop_points_ - spread_points


def spread_share(stop_points_: float, spread_points: float) -> float:
    """Part du stop consommée par le seul spread, entre zéro et un."""
    if stop_points_ <= 0:
        raise ValueError("stop_points_ doit être > 0")
    return min(spread_points / stop_points_, 1.0)


def noise_stop_probability(stop_points_: float, spread_points: float,
                           sigma_1min: float, minutes: float = 1.0) -> float:
    """Probabilité d'être sorti par le seul bruit, en `minutes` minutes.

    Le stop utile est `L − s` ; la probabilité que le prix efficient l'atteigne
    est celle d'un premier passage brownien sans dérive. Vaut un lorsque le
    stop n'excède pas le spread.
    """
    utile = effective_stop(stop_points_, spread_points)
    if utile <= 0.0:
        return 1.0
    return prob_touch_single_barrier(utile, sigma_1min, minutes)


# --- Le théorème du forçage ---------------------------------------------------

def martingale_hit_rate(reward_risk: float) -> float:
    """`p = 1/(R+1)` — fréquence de touche du target sous prix sans dérive."""
    if reward_risk <= 0:
        raise ValueError("reward_risk doit être > 0")
    return 1.0 / (reward_risk + 1.0)


def expected_attempts(p: float) -> float:
    """Tentatives jusqu'à la première réussite. Loi géométrique, moyenne `1/p`."""
    if not 0.0 < p <= 1.0:
        raise ValueError("p doit être dans ]0, 1]")
    return 1.0 / p


@dataclass(frozen=True)
class Forcing:
    """Le bilan d'une séquence forcée jusqu'à la première réussite."""

    reward_risk: float
    friction_ratio: float
    hit_rate: float
    attempts: float
    gross_r: float
    friction_r: float

    @property
    def net_r(self) -> float:
        return self.gross_r - self.friction_r

    @property
    def cost_multiple(self) -> float:
        """Combien de fois la friction d'une tentative unique le forçage coûte."""
        if self.friction_ratio <= 0.0:
            return 0.0
        return self.friction_r / self.friction_ratio


def force_until_success(reward_risk: float, friction_ratio: float,
                        hit_rate: float | None = None) -> Forcing:
    """Espérance d'une séquence répétée jusqu'à la première réussite.

    En multiples du risque nominal, et sous la loi nulle par défaut :

        brut     = R − (1/p − 1) = 0   quand p = 1/(R+1)
        friction = (1/p) · c/L
        net      = −(R+1)·c/L

    Le résultat porte tout l'argument : le brut est **exactement** nul sous la
    loi nulle, quel que soit le ratio, et il n'y a donc rien à optimiser dans
    la façon de forcer. Ce qui reste est la friction, multipliée par le nombre
    d'allers-retours que le forçage impose.
    """
    p = martingale_hit_rate(reward_risk) if hit_rate is None else hit_rate
    n = expected_attempts(p)
    brut = reward_risk - (n - 1.0)
    return Forcing(reward_risk=reward_risk, friction_ratio=friction_ratio,
                   hit_rate=p, attempts=n, gross_r=brut,
                   friction_r=n * friction_ratio)


def breakeven_exit_r(friction_ratio: float) -> float:
    """Coût d'une sortie « au point mort », en multiples du risque.

    Vaut `−c/L`. Le point mort n'est mort que du prix ; la friction, elle, est
    due. C'est l'issue que les journaux de trading retirent le plus souvent du
    dénominateur du taux de réussite, et c'est celle qui coûte le plus souvent.
    """
    return -friction_ratio


# --- La loi des séries ---------------------------------------------------------

def streak_probability(p: float, k: int) -> float:
    """`P(k échecs consécutifs) = (1 − p)^k`, sous prix sans dérive."""
    if not 0.0 <= p <= 1.0:
        raise ValueError("p doit être dans [0, 1]")
    if k < 0:
        raise ValueError("k doit être ≥ 0")
    return (1.0 - p) ** k


def streak_for_probability(p: float, q: float) -> float:
    """Longueur de série qu'on atteint avec probabilité `q`.

    Réciproque de la précédente : `k = ln q / ln(1 − p)`. Rendue infinie si la
    réussite est certaine.
    """
    if not 0.0 < q < 1.0:
        raise ValueError("q doit être dans ]0, 1[")
    if p >= 1.0:
        return 0.0
    if p <= 0.0:
        return math.inf
    return math.log(q) / math.log(1.0 - p)


def expected_longest_streak(p: float, n_trades: int) -> float:
    """Plus longue série d'échecs attendue sur `n` tentatives.

    Approximation classique de la plus longue suite : `ln(n·p) / ln(1/(1−p))`.
    Elle croît **logarithmiquement** avec le nombre de tentatives, ce qui est
    la raison pour laquelle une série longue finit toujours par arriver et
    n'est jamais, à elle seule, une information sur le signal.
    """
    if n_trades < 1:
        raise ValueError("n_trades doit être ≥ 1")
    if not 0.0 < p < 1.0:
        raise ValueError("p doit être dans ]0, 1[")
    lam = n_trades * p
    if lam <= 1.0:
        return 0.0
    return math.log(lam) / math.log(1.0 / (1.0 - p))


# --- Le dimensionnement, et la ruine ------------------------------------------

def drawdown_after(risk_fraction: float, k: int) -> float:
    """Fraction du capital effacée par `k` pertes pleines consécutives.

    `1 − (1 − f)^k` : la composition, non la somme. La différence est faible
    à faible `k` et décide à grand `k`.
    """
    if not 0.0 <= risk_fraction < 1.0:
        raise ValueError("risk_fraction doit être dans [0, 1[")
    if k < 0:
        raise ValueError("k doit être ≥ 0")
    return 1.0 - (1.0 - risk_fraction) ** k


def losses_to_drawdown(risk_fraction: float, level: float) -> float:
    """Pertes consécutives nécessaires pour effacer `level` du capital."""
    if not 0.0 < level < 1.0:
        raise ValueError("level doit être dans ]0, 1[")
    if not 0.0 < risk_fraction < 1.0:
        raise ValueError("risk_fraction doit être dans ]0, 1[")
    return math.log(1.0 - level) / math.log(1.0 - risk_fraction)


def kelly_fraction(p: float, reward_risk: float) -> float:
    """Fraction de Kelly : `(p(R+1) − 1)/R`. Nulle sous la loi nulle.

    Le résultat est exact et il est frappant : sous un prix sans dérive, la
    fraction optimale n'est pas petite, elle est **exactement zéro**, quel que
    soit le ratio visé. Toute fraction positive engagée sur une géométrie sans
    dérive est un sur-engagement d'ampleur infinie en proportion.
    """
    if reward_risk <= 0:
        raise ValueError("reward_risk doit être > 0")
    return (p * (reward_risk + 1.0) - 1.0) / reward_risk


def overbet(risk_fraction: float, p: float, reward_risk: float) -> float:
    """Rapport de la fraction engagée à la fraction de Kelly.

    Infini quand Kelly est nul ou négatif — et c'est le cas sous la loi nulle.
    Au-delà de deux fois Kelly, la croissance espérée redevient négative même
    lorsque l'espérance par trade est positive : le dimensionnement suffit à
    annuler un avantage réel.
    """
    k = kelly_fraction(p, reward_risk)
    if k <= 0.0:
        return math.inf
    return risk_fraction / k


def risk_of_ruin(p: float, reward_risk: float, friction_ratio: float,
                 risk_fraction: float, n_trades: int, ruin_level: float = 0.5,
                 paths: int = 4000, seed: int = 20260822) -> float:
    """Probabilité d'effacer `ruin_level` du capital en `n_trades` tentatives.

    Simulation multiplicative reproductible : chaque tentative multiplie le
    capital par `1 + f·(R − c/L)` en cas de réussite et par
    `1 − f·(1 + c/L)` en cas d'échec. La forme multiplicative est celle d'un
    opérateur qui redimensionne sur le capital courant, ce qui est le cas
    d'une règle en pourcentage.
    """
    if not 0.0 < ruin_level < 1.0:
        raise ValueError("ruin_level doit être dans ]0, 1[")
    gagne = 1.0 + risk_fraction * (reward_risk - friction_ratio)
    perd = 1.0 - risk_fraction * (1.0 + friction_ratio)
    if perd <= 0.0:
        return 1.0
    seuil = 1.0 - ruin_level
    rng = Rng(seed)
    ruines = 0
    for _ in range(paths):
        capital = 1.0
        for _ in range(n_trades):
            capital *= gagne if rng.uniform() < p else perd
            if capital <= seuil:
                ruines += 1
                break
    return ruines / paths


# --- Le régime, et la seule condition qui rende le forçage rationnel ---------

@dataclass(frozen=True)
class RegimeVerdict:
    """Ce que l'exposant d'échelle décide d'une règle de stop."""

    hurst: float
    persistent: bool
    reading: str


def regime_verdict(hurst: float = MEASURED_HURST,
                   tolerance: float = 0.01) -> RegimeVerdict:
    """Verdict de régime sur une règle de stop, d'après Kaminski et Lo (2014).

    Leur résultat est de signe et il suffit : sous marche aléatoire une règle
    de stop simple **diminue toujours** l'espérance ; en présence de momentum
    elle peut en ajouter. La grandeur qui tranche est donc la persistance, et
    le document en possède déjà une mesure.

    La tolérance n'est pas cosmétique : l'estimateur du document affiche
    `0,5208` sur une série qui est une martingale par construction, et ne
    revient à `0,5014` qu'une fois corrigé de sa propre loi nulle. Exiger un
    écart d'au moins un centième est la conséquence de ce biais, pas une
    précaution ajoutée.
    """
    persistant = hurst > 0.5 + tolerance
    if persistant:
        lecture = ("persistance mesurée au-delà du biais de l'estimateur : "
                   "une règle de stop peut ajouter de la valeur")
    elif hurst < 0.5 - tolerance:
        lecture = ("retour à la moyenne mesuré : une règle de stop retranche, "
                   "et le forçage retranche à chaque répétition")
    else:
        lecture = ("indiscernable d'une marche aléatoire : sous cette "
                   "hypothèse une règle de stop diminue toujours l'espérance")
    return RegimeVerdict(hurst=hurst, persistent=persistant, reading=lecture)


def persistence_cannot_help(reward_risk: float, friction_ratio: float,
                            sigma_per_stop: float, horizon_min: float = 390.0,
                            hurst_grid=(0.50, 0.65, 0.80, 0.95)) -> dict:
    """Aucun exposant d'échelle ne rend une géométrie sans dérive rentable.

    Ce n'est pas un résultat numérique mais une **proposition**, et la
    fonction se contente de l'exhiber. Un changement d'exposant est un
    changement de temps déterministe ; il ne modifie pas le rapport des
    probabilités de premier passage, seulement la fréquence à laquelle la
    séance suffit à les réaliser. La probabilité de toucher le target avant le
    stop reste donc bornée par `1/(R+1)`, quelle que soit la persistance, là
    où la rentabilité exige `(1 + c/L)/(R+1)`, strictement au-dessus.

    La conséquence porte sur la lecture de Kaminski et Lo. Le momentum qui
    rend une règle de stop utile chez eux n'est **pas** une propriété
    d'échelle : c'est une dérive conditionnelle. Espérer que la persistance
    sauve le forçage revient à espérer la mauvaise grandeur.

    Rend, pour chaque exposant de la grille, la probabilité atteinte et le
    seuil manqué.
    """
    from .horizon import outcome_scaled

    cible = (1.0 + friction_ratio) / (reward_risk + 1.0)
    plafond = 1.0 / (reward_risk + 1.0)
    return {
        "cible": cible,
        "plafond": plafond,
        "atteint": {h: outcome_scaled(1.0, reward_risk, horizon_min,
                                      sigma_per_stop, h).p_target
                    for h in hurst_grid},
    }


#: Heures de séance par an : six heures et demie, deux cent cinquante-deux
#: séances. Sert à annualiser une exigence horaire, et à rien d'autre.
HOURS_PER_YEAR = 6.5 * 252.0


def required_sharpe_annual(friction_points: float, exposure_min: float,
                           sigma_1min: float) -> float:
    """Ratio de Sharpe annualisé qu'exige une géométrie, sur son exposition.

    La dérive minimale rentable vaut `µ* = c/E[τ]` par minute. Rapportée à la
    volatilité de la même minute, elle donne un Sharpe par minute, qu'on
    annualise par la racine du nombre de minutes de marché dans l'année.

    C'est la traduction la plus lisible de ce qu'un resserrement de stop
    coûte, parce qu'elle place l'exigence sur une échelle que tout le monde
    lit. Le resserrement ne divise pas seulement l'exposition : il divise
    l'exposition **et** multiplie la friction relative, et les deux effets
    vont dans le même sens.
    """
    if exposure_min <= 0.0 or sigma_1min <= 0.0:
        raise ValueError("exposure_min et sigma_1min doivent être > 0")
    mu_par_min = friction_points / exposure_min
    sharpe_min = mu_par_min / sigma_1min
    return sharpe_min * math.sqrt(HOURS_PER_YEAR * 60.0)


# --- Le diagnostic inverse : ce que la série observée révèle -----------------

def implied_hit_rate(longest_streak: float, n_trades: int) -> float:
    """Taux de réussite impliqué par la plus longue série observée.

    Inversion numérique de `expected_longest_streak`. C'est le diagnostic le
    plus utile du module, parce qu'il ne demande à l'opérateur qu'un chiffre
    qu'il connaît déjà — sa plus longue série d'échecs — et qu'il lui rend une
    grandeur qu'il croit connaître : la géométrie qu'il pratique réellement.

    Une série maximale **courte** n'est pas une bonne nouvelle : elle implique
    un taux de réussite élevé, donc un ratio gain/risque bas, donc une
    géométrie très éloignée du 1:20 qu'on croit tenir. Une série maximale
    **longue** est cohérente avec un ratio élevé et ne dit rien de plus.
    """
    if longest_streak <= 0.0:
        return 1.0
    if n_trades < 2:
        raise ValueError("n_trades doit être ≥ 2")
    # Une série donnée n'est pas atteignable sur tout échantillon : à `n`
    # petit, aucun taux de réussite ne produit une série aussi longue en
    # espérance. Le diagnostic rend alors zéro, qui se lit « hors domaine »
    # plutôt qu'un taux de réussite arbitrairement petit.
    plafond = max(expected_longest_streak(q / 1000.0, n_trades)
                  for q in range(1, 1000))
    if longest_streak > plafond:
        return 0.0
    lo, hi = 1e-6, 1.0 - 1e-9
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        attendu = expected_longest_streak(mid, n_trades)
        if attendu > longest_streak:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def implied_reward_risk(p: float) -> float:
    """Ratio gain/risque cohérent avec un taux de réussite, sous loi nulle.

    `R = 1/p − 1`. Sous un prix sans dérive, taux de réussite et ratio visé ne
    sont pas deux paramètres : c'est le même, écrit deux fois.
    """
    if not 0.0 < p <= 1.0:
        raise ValueError("p doit être dans ]0, 1]")
    return 1.0 / p - 1.0
