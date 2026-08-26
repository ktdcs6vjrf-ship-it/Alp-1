"""Le journal de décision — l'instrument qui rend un jugement mesurable.

Un opérateur discrétionnaire affirme que son avantage n'est pas codable. Pris
au pied de la lettre, l'énoncé interdit toute évaluation : sans règle, pas de
rejeu ; sans rejeu, pas de loi nulle ; sans loi nulle, rien à opposer au
hasard, et la règle 5 du dépôt refuse l'entrée.

La sortie tient dans une distinction que la littérature d'évaluation des
gérants pratique depuis quarante ans sans jamais disposer de la règle qu'elle
juge : **répliquer n'est pas détecter**. Fama et French (2010) ne connaissent
la stratégie d'aucun fonds ; Kacperczyk, Van Nieuwerburgh et Veldkamp (2014)
mesurent une compétence discrétionnaire variable dans le temps sans jamais la
coder. On ne teste pas la règle : on teste la trace qu'elle laisse.

Ce module produit cette trace. La règle reste dans la tête de l'opérateur ;
ce qui sort du dispositif, ce sont des décisions horodatées.

**Les trois champs que la plupart des journaux perdent**, et qui portent
précisément l'information :

1. *Le contexte à l'instant de la décision.* L'état du monde tel qu'il était
   avant que l'issue soit connue. Un journal rempli le soir est un souvenir,
   pas une donnée.
2. *Les abstentions.* Les setups vus et refusés. Chez un discrétionnaire,
   l'avantage loge très souvent dans le refus et non dans la sélection ; sans
   les abstentions cette composante est structurellement invisible, et la
   loi nulle D du module `operator` devient intestable.
3. *La conviction annoncée ex ante.* Elle autorise un test qu'aucun autre
   champ ne permet : la conviction est-elle **calibrée** ? Un opérateur dont
   les décisions à forte conviction battent ses décisions à faible conviction
   démontre une compétence, même si son espérance moyenne est nulle.

**L'univers des setups est produit par la règle scellée** (`strategy.run`)
sur un prix sans dérive. Ce choix n'est pas un détail de commodité : il pose
la vérité de référence. Sous un prix sans dérive, tout sous-ensemble de
setups choisi *sans clairvoyance* a pour espérance exactement `−c/L`, par le
théorème d'arrêt optionnel. La seule façon de battre cette valeur est une
information réelle sur l'issue. Le jugement simulé ici est donc paramétré
par cette information, et par rien d'autre.

**La vérité plantée est une quantité d'information, en bits.** Le paramètre
`skill` fixe la dépendance entre la décision de prendre et l'issue de la
barrière ; l'information mutuelle qui en résulte se lit dans l'unité même où
`alp1.entropy` exprime le plafond informationnel. L'appareil de mesure est
ainsi calibrable contre une vérité connue : sur un opérateur sans compétence
il doit conclure à l'absence, et sur un opérateur dont on a planté `b` bits
il doit les retrouver — ou dire combien de décisions lui manquent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from .mc import Rng
from .measure import Trade

#: Les quatre leviers discrétionnaires recensés. Chacun est un choix pris en
#: regardant le marché, donc chacun **double** la famille des stratégies
#: effectivement explorées : k leviers valent 2^k configurations
#: (voir `alp1.discipline`). L'ordre est celui du recensement, pas une
#: hiérarchie d'importance.
LEVERS: tuple[tuple[str, str], ...] = (
    ("entree", "Entrer ou s'abstenir"),
    ("moment", "Le moment exact dans la fenêtre"),
    ("taille", "La taille de position"),
    ("sortie", "La gestion de sortie"),
)

#: Échelle de conviction annoncée ex ante. Ordinale, jamais cardinale : on ne
#: suppose pas qu'un écart de 1 à 2 vaut un écart de 4 à 5.
CONVICTION_MIN = 1
CONVICTION_MAX = 5

#: Graine par défaut du dépôt.
SEED = 20260821


@dataclass(frozen=True)
class Decision:
    """Une décision discrétionnaire, scellée à l'instant où elle est prise.

    Les champs se lisent en deux blocs séparés par une frontière temporelle
    qu'il ne faut jamais franchir à l'envers : tout ce qui précède `outcome`
    est connu **avant** l'issue, tout ce qui suit ne l'est qu'après. Un
    journal qui laisse fuir la seconde moitié dans la première ne mesure plus
    une compétence mais une reconstruction.
    """

    seq: int                    # rang dans le journal, croissant
    day: str                    # séance, "YYYY-MM-DD"
    minute: int                 # minute de la décision depuis l'ouverture
    taken: bool                 # prise, ou abstention déclarée
    direction: int              # +1 achat, −1 vente, 0 si abstention
    size: float                 # mise, en unités de risque R
    conviction: int             # annoncée ex ante, CONVICTION_MIN..MAX
    offset_min: int             # décalage d'exécution choisi, en minutes
    managed: bool               # la sortie a-t-elle été gérée à la main

    # --- frontière : ce qui suit n'est connu qu'après l'issue ---------------
    net_r: float | None         # résultat net en R, None si abstention
    win: bool | None            # issue favorable, None si abstention

    @property
    def eligible(self) -> bool:
        """Un setup s'est présenté — qu'il ait été pris ou refusé."""
        return True

    @property
    def weighted_r(self) -> float:
        """Le résultat effectivement encaissé, mise comprise.

        Une abstention rapporte exactement zéro : c'est le point qui rend
        l'abstention mesurable au lieu d'être une non-donnée.
        """
        if not self.taken or self.net_r is None:
            return 0.0
        return self.size * self.net_r


@dataclass(frozen=True)
class Journal:
    """Le registre complet : décisions prises **et** abstentions.

    C'est l'objet que l'appareil de mesure consomme. Il porte la vérité
    plantée (`skill_bits`) quand il est synthétique, et `None` quand il vient
    d'un opérateur réel — auquel cas la vérité est justement ce qu'on cherche.
    """

    decisions: tuple[Decision, ...]
    levers: tuple[str, ...]
    skill_bits: float | None = None
    source: str = "synthétique"

    @property
    def n_eligible(self) -> int:
        return len(self.decisions)

    @property
    def taken(self) -> tuple[Decision, ...]:
        return tuple(d for d in self.decisions if d.taken)

    @property
    def skipped(self) -> tuple[Decision, ...]:
        return tuple(d for d in self.decisions if not d.taken)

    @property
    def n_taken(self) -> int:
        return len(self.taken)

    @property
    def take_rate(self) -> float:
        return self.n_taken / self.n_eligible if self.n_eligible else 0.0

    @property
    def budget(self) -> float:
        """Le nombre de configurations effectives : 2^k pour k leviers.

        C'est la taxe de sélection que le jugement doit financer avant de
        payer quoi que ce soit d'autre.
        """
        return 2.0 ** len(self.levers)

    @property
    def returns(self) -> list[float]:
        """Les résultats des décisions prises, mise comprise."""
        return [d.weighted_r for d in self.taken]

    @property
    def mean_r(self) -> float:
        r = self.returns
        return sum(r) / len(r) if r else 0.0

    @property
    def sd_r(self) -> float:
        r = self.returns
        if len(r) < 2:
            return 0.0
        m = sum(r) / len(r)
        return math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1))

    @property
    def sharpe_trade(self) -> float:
        sd = self.sd_r
        return self.mean_r / sd if sd > 0.0 else 0.0

    @property
    def hit_rate(self) -> float:
        w = [d for d in self.taken if d.win]
        return len(w) / self.n_taken if self.n_taken else 0.0

    def contingency(self) -> list[list[int]]:
        """La table 2×2 décision × issue, sur **tous** les setups éligibles.

        Lignes : refusé, pris. Colonnes : perdant, gagnant. C'est la table que
        `alp1.entropy` consomme pour mesurer l'information mutuelle entre la
        décision de l'opérateur et l'issue — donc la compétence d'abstention.

        Une abstention porte une issue contrefactuelle : ce que le setup
        *aurait* donné s'il avait été pris. Sans elle, la moitié de la table
        est vide et l'information n'est pas identifiable. C'est la raison pour
        laquelle un journal sans abstentions ne peut pas être évalué ici.
        """
        table = [[0, 0], [0, 0]]
        for d in self.decisions:
            if d.win is None:
                continue
            table[1 if d.taken else 0][1 if d.win else 0] += 1
        return table

    def by_conviction(self) -> dict[int, list[float]]:
        """Les résultats regroupés par niveau de conviction annoncé."""
        out: dict[int, list[float]] = {}
        for d in self.taken:
            out.setdefault(d.conviction, []).append(d.weighted_r)
        return out


# ---------------------------------------------------------------------------
# L'univers des setups — la règle scellée sur un prix sans dérive
# ---------------------------------------------------------------------------


@lru_cache(maxsize=8)
def _universe_cached(n_sessions: int, seed: int) -> tuple[Trade, ...]:
    """Mémoïsation de l'univers, selon la convention du dépôt.

    L'univers ne dépend que de la *forme* du problème — le nombre de séances
    et la graine — jamais d'un paramètre de l'opérateur. Le rejouer à chaque
    clairvoyance testée coûterait plusieurs secondes pour un résultat
    identique au bit près.
    """
    from .dataset import synthetic_sessions
    from .strategy import run

    return tuple(run(synthetic_sessions(n_sessions, seed=seed)))


def universe(n_sessions: int = 900, seed: int = SEED) -> list[Trade]:
    """Les setups éligibles, produits par la règle scellée.

    Le prix est sans dérive : `synthetic_sessions` laisse ses deux paramètres
    de dérive à zéro. Toute espérance mesurée au-dessus de `−c/L` sur un
    sous-ensemble de ces setups vient donc de la **sélection**, jamais du
    prix. C'est ce qui fait de cet univers une vérité de référence et non un
    simple jeu d'essai.

    L'import est tardif : `dataset` et `mc` forment un cycle que le dépôt
    casse partout de cette façon.
    """
    if n_sessions < 1:
        raise ValueError("n_sessions doit être ≥ 1")
    return list(_universe_cached(n_sessions, seed))


# ---------------------------------------------------------------------------
# L'opérateur synthétique — une clairvoyance de taille connue
# ---------------------------------------------------------------------------


def _take_probabilities(skill: float, base_rate: float) -> tuple[float, float]:
    """P(prendre | gagnant) et P(prendre | perdant) pour une clairvoyance.

    La paramétrisation est symétrique autour de `base_rate` : la compétence
    déplace les deux probabilités en sens opposés d'une même quantité, ce qui
    laisse le **taux de prise global** à peu près constant quel que soit
    `skill`. C'est délibéré : sans cela, un opérateur compétent prendrait
    aussi mécaniquement moins de trades, et l'on ne saurait plus démêler la
    compétence de la sélectivité.
    """
    if not 0.0 <= skill <= 1.0:
        raise ValueError("skill doit être dans [0, 1]")
    if not 0.0 < base_rate < 1.0:
        raise ValueError("base_rate doit être dans ]0, 1[")
    span = min(base_rate, 1.0 - base_rate)
    return base_rate + skill * span, base_rate - skill * span


def planted_bits(skill: float, base_rate: float, win_rate: float) -> float:
    """L'information mutuelle plantée, en bits par décision.

    C'est la **vérité connue** de l'opérateur synthétique : la quantité que
    l'appareil de mesure doit retrouver. Elle se calcule en fermé sur la table
    2×2 de la loi jointe, sans simulation, donc sans bruit d'estimation.

    À `skill = 0` elle vaut exactement zéro : décision et issue sont
    indépendantes, et aucune quantité de décisions ne fera apparaître un
    avantage. C'est le cas qui calibre le niveau du test.
    """
    p_win, p_lose = _take_probabilities(skill, base_rate)
    w = max(0.0, min(1.0, win_rate))
    # Loi jointe P(prise, issue) sur les quatre cases.
    joint = ((w * p_win, (1.0 - w) * p_lose),
             (w * (1.0 - p_win), (1.0 - w) * (1.0 - p_lose)))
    total = sum(sum(row) for row in joint)
    if total <= 0.0:
        return 0.0
    bits = 0.0
    for i, row in enumerate(joint):
        for j, cell in enumerate(row):
            p = cell / total
            if p <= 0.0:
                continue
            px = sum(joint[i]) / total
            py = sum(r[j] for r in joint) / total
            if px <= 0.0 or py <= 0.0:
                continue
            bits += p * math.log2(p / (px * py))
    return max(0.0, bits)


def synthesise(skill: float = 0.0, n_sessions: int = 900,
               base_rate: float = 0.50, seed: int = SEED,
               size_skill: float = 0.0, timing_noise: int = 0,
               levers: tuple[str, ...] | None = None) -> Journal:
    """Un journal d'opérateur dont la compétence est connue d'avance.

    `skill` est une clairvoyance sur l'issue de la barrière, portée par le
    **seul levier d'abstention**. Les autres leviers sont ouverts — ils
    coûtent leur taxe de multiplicité — mais neutres : ils ne portent aucune
    information. C'est ce qui rend le module d'attribution falsifiable. Une
    décomposition correcte doit retrouver l'avantage là où il est planté, et
    ne rien trouver ailleurs. Une décomposition qui répartit l'avantage sur
    les quatre leviers est fausse, et ce dispositif le dit.

    `size_skill` permet, à l'inverse, de planter l'avantage dans le
    dimensionnement : la mise suit alors la clairvoyance au lieu de la
    décision de prendre. Les deux peuvent être combinés.

    `timing_noise` décale l'exécution de quelques minutes, sans information :
    il sert à vérifier que la loi nulle B ne crée pas d'avantage à partir de
    rien.
    """
    if not 0.0 <= size_skill <= 1.0:
        raise ValueError("size_skill doit être dans [0, 1]")
    if timing_noise < 0:
        raise ValueError("timing_noise doit être ≥ 0")

    trades = universe(n_sessions, seed)
    rng = Rng(seed + 7919)
    p_win, p_lose = _take_probabilities(skill, base_rate)
    q_win, q_lose = _take_probabilities(size_skill, 0.5)

    decisions: list[Decision] = []
    n_win = 0
    for seq, t in enumerate(trades):
        win = t.net_r > 0.0
        n_win += 1 if win else 0
        # La clairvoyance ne voit que le signe de l'issue, jamais son ampleur.
        take = rng.uniform() < (p_win if win else p_lose)
        # La conviction annoncée suit la même clairvoyance : c'est ce qui la
        # rend calibrable, et calibrable veut dire réfutable.
        edge = (q_win if win else q_lose) if size_skill > 0.0 else 0.5
        size = 0.5 + edge if size_skill > 0.0 else 1.0
        level = CONVICTION_MIN + int(edge * (CONVICTION_MAX - CONVICTION_MIN))
        offset = rng.randint(timing_noise + 1) if timing_noise else 0
        decisions.append(Decision(
            seq=seq, day=t.day, minute=t.entry_minute, taken=take,
            direction=t.direction if take else 0,
            size=size if take else 0.0,
            conviction=max(CONVICTION_MIN, min(CONVICTION_MAX, level)),
            offset_min=offset, managed=False,
            net_r=t.net_r, win=win,
        ))

    win_rate = n_win / len(trades) if trades else 0.0
    bits = planted_bits(skill, base_rate, win_rate)
    return Journal(
        decisions=tuple(decisions),
        levers=levers if levers is not None else tuple(k for k, _ in LEVERS),
        skill_bits=bits,
        source=f"synthétique, clairvoyance {skill:.2f}",
    )


# ---------------------------------------------------------------------------
# Intégrité du registre — ce qui invalide un journal avant tout calcul
# ---------------------------------------------------------------------------


def audit(journal: Journal) -> list[str]:
    """Les défauts qui interdisent d'exploiter un journal.

    L'ordre est celui de la gravité. Un journal qui déclenche le premier
    défaut n'est pas dégradé : il est inexploitable, parce que la quantité
    qu'on voudrait mesurer n'y est pas identifiable.
    """
    faults: list[str] = []
    d = journal.decisions

    if not d:
        return ["journal vide"]
    if not journal.skipped:
        faults.append(
            "aucune abstention enregistrée : la compétence de refus n'est pas "
            "identifiable, la loi nulle D est intestable")
    if not journal.taken:
        faults.append("aucune décision prise : rien à évaluer")

    seqs = [x.seq for x in d]
    if seqs != sorted(seqs):
        faults.append("les rangs ne sont pas croissants : l'ordre est douteux")
    if len(set(seqs)) != len(seqs):
        faults.append("rangs dupliqués : le registre a été édité")

    leaked = [x for x in d if not x.taken and x.direction != 0]
    if leaked:
        faults.append(
            f"{len(leaked)} abstention(s) portent une direction : "
            "le champ a été rempli après coup")
    sized = [x for x in d if not x.taken and x.size != 0.0]
    if sized:
        faults.append(f"{len(sized)} abstention(s) portent une mise non nulle")

    unknown = [x for x in d if x.win is None]
    if unknown:
        faults.append(
            f"{len(unknown)} setup(s) sans issue contrefactuelle : "
            "la table de contingence sera incomplète")

    flat = {x.conviction for x in journal.taken}
    if len(flat) == 1 and journal.n_taken > 30:
        faults.append(
            "conviction constante : le test de calibration est sans objet")

    return faults
