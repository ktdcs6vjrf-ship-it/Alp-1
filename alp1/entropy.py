"""Le plafond d'information : combien de bits un signal doit porter.

Ce module ajoute au document la borne qui manquait de l'autre côté du
théorème d'invariance.

L'invariance dit ce qu'une géométrie **ne peut pas** faire : créer de
l'espérance sur un prix sans dérive. Elle laisse entière la question
symétrique — un signal qui prétend prévoir la dérive, de combien
d'information a-t-il besoin ? La réponse est un nombre, elle ne dépend
d'aucun modèle de prix, et elle se mesure sur n'importe quelle série.

**Le résultat.** Kelly (1956) montre que le taux de croissance logarithmique
maximal d'un pari répété vaut exactement l'information mutuelle entre le
signal et l'issue. Aucune stratégie, aucun dimensionnement, aucune géométrie
ne dépasse ce plafond : c'est une limite d'information, pas d'ingéniosité.
Un signal qui porte `I` bits par trade ne peut pas financer une croissance
supérieure à `I` bits par trade.

**L'usage.** Le document exige déjà que le taux de réussite passe d'une
valeur martingale `q` à une valeur rentable `p`. Déplacer une loi de
Bernoulli de `q` à `p` coûte exactement `D(p‖q)` — la divergence de
Kullback-Leibler. C'est donc l'information minimale que le signal doit
porter, et elle se compare à ce qu'un signal candidat porte réellement.

**Le piège, et il est le même que celui du ratio de variance.** Les
estimateurs d'information mutuelle par comptage sont **biaisés vers le
haut** : un signal sans aucune information en affiche. Le biais vaut
approximativement `(m−1)/(2N ln 2)` bits pour `m` cellules et `N`
observations, et il dépasse de loin l'information réellement cherchée dès
que la table de contingence est fine. Le module rend donc la correction de
Miller-Madow et, comme ailleurs dans le dépôt, la loi nulle simulée — seule
cette dernière décide.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from .mc import Rng

LN2 = math.log(2.0)


def _xlogx(p: float) -> float:
    return 0.0 if p <= 0.0 else p * math.log(p)


def binary_entropy(p: float) -> float:
    """Entropie d'une Bernoulli(p), en bits. Vaut 1 à p = ½, 0 aux bords."""
    if not 0.0 <= p <= 1.0:
        raise ValueError("p doit être dans [0, 1]")
    return -(_xlogx(p) + _xlogx(1.0 - p)) / LN2


def kl_bernoulli(p: float, q: float) -> float:
    """Divergence D(p‖q) entre deux Bernoulli, en bits.

    C'est le coût en information d'un déplacement du taux de réussite de `q`
    à `p` : la quantité qu'un signal doit apporter pour rendre `p` plausible
    quand la loi nulle dit `q`. Infinie si `q` est dégénérée et pas `p`.
    """
    if not 0.0 <= p <= 1.0 or not 0.0 <= q <= 1.0:
        raise ValueError("p et q doivent être dans [0, 1]")
    out = 0.0
    for a, b in ((p, q), (1.0 - p, 1.0 - q)):
        if a > 0.0:
            if b <= 0.0:
                return math.inf
            out += a * math.log(a / b)
    return out / LN2


@dataclass(frozen=True)
class Requirement:
    """Ce qu'un signal doit porter pour rendre une géométrie rentable."""

    hit_null: float
    hit_needed: float
    bits: float
    reward_risk: float
    friction_ratio: float

    @property
    def lift(self) -> float:
        """Points de taux de réussite à gagner sur la loi nulle."""
        return self.hit_needed - self.hit_null

    @property
    def trades_per_bit(self) -> float:
        """Trades nécessaires pour accumuler un bit d'avantage."""
        return math.inf if self.bits <= 0 else 1.0 / self.bits

    @property
    def feasible(self) -> bool:
        return self.hit_needed < 1.0 and math.isfinite(self.bits)


def required_bits(reward_risk: float, friction_ratio: float) -> Requirement:
    """Information minimale par trade, pour un R:R et une friction donnés.

    Le taux de réussite sous martingale vaut ``1/(R+1)`` — c'est la
    probabilité de premier passage, et c'est aussi le taux d'équilibre sans
    friction. Le taux d'équilibre **avec** friction vaut
    ``(1 + c/L)/(R + 1)``. L'écart entre les deux est ce que le signal doit
    financer, et `D(p‖q)` en donne le prix en bits.

    La quantité rendue est une **borne inférieure** de l'information mutuelle
    entre le signal et l'issue : aucune stratégie ne franchit le seuil avec
    moins, quelle que soit la façon dont elle dimensionne ses positions.
    """
    if reward_risk <= 0:
        raise ValueError("reward_risk doit être > 0")
    if friction_ratio < 0:
        raise ValueError("friction_ratio doit être ≥ 0")
    q = 1.0 / (reward_risk + 1.0)
    p = (1.0 + friction_ratio) / (reward_risk + 1.0)
    bits = kl_bernoulli(min(p, 1.0), q) if p < 1.0 else math.inf
    return Requirement(hit_null=q, hit_needed=p, bits=bits,
                       reward_risk=reward_risk, friction_ratio=friction_ratio)


def growth_from_bits(bits: float) -> float:
    """Croissance logarithmique maximale, en bits par trade.

    Identité de Kelly : le taux de croissance optimal d'un pari répété vaut
    l'information mutuelle entre signal et issue. La fonction est l'identité,
    et elle est écrite pour que le document puisse la citer comme telle — le
    plafond n'est pas approché, il **est** l'information.
    """
    if bits < 0:
        raise ValueError("bits doit être ≥ 0")
    return bits


# --- Mesure sur données, et son biais ---------------------------------------


def mutual_information(table: list[list[int]]) -> float:
    """Information mutuelle empirique d'une table de contingence, en bits.

    Estimateur par comptage — le plus simple, et le plus trompeur : il est
    biaisé vers le haut, et le biais croît avec la finesse de la table.
    `miller_madow` le corrige au premier ordre ; la loi nulle simulée est ce
    qui décide.
    """
    n = sum(sum(row) for row in table)
    if n <= 0:
        raise ValueError("table vide")
    rows = [sum(r) for r in table]
    cols = [sum(col) for col in zip(*table)]
    out = 0.0
    for i, row in enumerate(table):
        for j, cell in enumerate(row):
            if cell > 0 and rows[i] > 0 and cols[j] > 0:
                out += (cell / n) * math.log((cell * n) / (rows[i] * cols[j]))
    return out / LN2


def miller_madow(table: list[list[int]]) -> float:
    """Information mutuelle corrigée du biais au premier ordre.

    Le biais de l'estimateur par comptage vaut approximativement
    ``(m_x − 1)(m_y − 1) / (2N ln 2)`` bits pour une table `m_x × m_y` et `N`
    observations. La correction le retranche. Elle ne suffit pas : sur les
    tailles d'échantillon de ce document, le biais résiduel reste du même
    ordre que l'information cherchée, et seule la loi nulle tranche.
    """
    n = sum(sum(row) for row in table)
    if n <= 0:
        raise ValueError("table vide")
    mx = sum(1 for r in table if sum(r) > 0)
    my = sum(1 for c in zip(*table) if sum(c) > 0)
    biais = (mx - 1) * (my - 1) / (2.0 * n * LN2)
    return mutual_information(table) - biais


@dataclass(frozen=True)
class NullMI:
    """Loi de l'information mutuelle sous indépendance, à table fixée."""

    rows: int
    cols: int
    n_obs: int
    mean: float
    sd: float
    q95: float
    draws: int

    def z(self, observed: float) -> float:
        return (observed - self.mean) / self.sd if self.sd > 0 else math.nan

    def significant(self, observed: float) -> bool:
        """Au-delà du quantile 95 % de la loi nulle simulée."""
        return observed > self.q95


@lru_cache(maxsize=64)
def null_mutual_information(rows: int, cols: int, n_obs: int,
                            draws: int = 400,
                            seed: int = 20260821) -> NullMI:
    """Information mutuelle attendue entre deux variables indépendantes.

    Le tirage respecte les marges uniformes ; c'est le cas le plus favorable
    à l'estimateur, et il suffit à montrer l'ampleur du biais. Une table
    3 × 2 sur mille observations rend déjà quelques millièmes de bit là où la
    vérité est zéro — soit l'ordre de grandeur exact de ce que la dérive
    documentée de ce document exige.

    Mémorisée par ses arguments : elle ne dépend que de la forme de la table
    et du nombre d'observations, jamais des données mesurées.
    """
    if rows < 2 or cols < 2:
        raise ValueError("la table doit avoir au moins deux lignes et colonnes")
    if n_obs < rows * cols:
        raise ValueError("échantillon trop petit pour la table demandée")
    if draws < 2:
        raise ValueError("draws doit être ≥ 2")
    rng = Rng(seed)
    vals = []
    for _ in range(draws):
        t = [[0] * cols for _ in range(rows)]
        for _ in range(n_obs):
            t[rng.randint(rows)][rng.randint(cols)] += 1
        vals.append(mutual_information(t))
    m = sum(vals) / len(vals)
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
    vals.sort()
    q95 = vals[min(len(vals) - 1, int(0.95 * len(vals)))]
    return NullMI(rows=rows, cols=cols, n_obs=n_obs, mean=m, sd=sd,
                  q95=q95, draws=len(vals))


def trades_for_information(bits: float, rows: int = 2, cols: int = 2,
                           alpha: float = 0.05, power: float = 0.80) -> float:
    """Trades nécessaires pour **décider** qu'un signal porte `bits` bits.

    Le test naturel est celui du rapport de vraisemblance sur la table de
    contingence : ``G = 2N·I·ln 2`` suit une loi du khi-deux à
    ``(r−1)(c−1)`` degrés de liberté sous indépendance, et une loi
    non centrale de paramètre ``2N·I·ln 2`` sous l'alternative. Atteindre la
    puissance demandée exige donc

        N ≥ λ(α, puissance, ddl) / (2 · bits · ln 2).

    C'est le pendant informationnel de la taille d'échantillon du document, et
    il tombe au même ordre de grandeur par une route entièrement
    indépendante — ni la loi du résultat, ni la géométrie, ni le Sharpe
    n'entrent dans ce calcul. Deux chemins séparés qui butent sur le même mur
    disent que le mur est structurel.
    """
    if bits <= 0:
        return math.inf
    ddl = (rows - 1) * (cols - 1)
    lam = _noncentrality(alpha, power, ddl)
    return lam / (2.0 * bits * LN2)


def _noncentrality(alpha: float, power: float, ddl: int) -> float:
    """Paramètre de non-centralité d'un khi-deux, par approximation normale.

    Pour un degré de liberté, ``λ = (z_{1−α} + z_{puissance})²`` est exact ;
    au-delà, l'approximation de Patnaik est employée. Elle suffit ici, où
    l'on cherche un ordre de grandeur et non une troisième décimale.
    """
    from .costs import _norm_ppf
    if not 0.0 < alpha < 1.0 or not 0.0 < power < 1.0:
        raise ValueError("alpha et power doivent être dans ]0, 1[")
    z_a = _norm_ppf(1.0 - alpha)
    z_b = _norm_ppf(power)
    base = (z_a + z_b) ** 2
    return base if ddl <= 1 else base + (ddl - 1) * (1.0 + 2.0 / (z_a + z_b))


def observations_for_bits(bits: float, rows: int = 2, cols: int = 2,
                          margin: float = 2.0) -> float:
    """Observations nécessaires pour distinguer `bits` du biais d'estimation.

    On demande que l'information cherchée dépasse le biais d'un facteur
    `margin`. Avec un biais de ``(r−1)(c−1)/(2N ln 2)``, cela donne

        N ≥ margin · (r−1)(c−1) / (2 · bits · ln 2).

    C'est un plancher d'**estimation**, non de décision : en deçà,
    l'information cherchée se confond avec le biais de l'estimateur. Le
    plancher de décision est donné par `trades_for_information`, et il est
    plus exigeant.
    """
    if bits <= 0:
        return math.inf
    return margin * (rows - 1) * (cols - 1) / (2.0 * bits * LN2)
