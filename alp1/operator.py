"""Les lois nulles de l'opérateur discrétionnaire.

Une seule loi nulle ne suffit pas, et c'est la contribution méthodologique de
ce chapitre. Un opérateur qui bat « le hasard » n'a rien démontré tant qu'on
n'a pas dit **quel** hasard : celui qui choisit les setups au sort, celui qui
décale les instants, celui qui exécute la règle scellée sans état d'âme, ou
celui qui prend tout. Chacun de ces adversaires réfute une prétention
différente, et un avantage réel doit les battre tous.

Le tableau de correspondance est le suivant.

| loi | l'adversaire | ce qu'elle réfute si elle n'est pas battue |
|-----|--------------|--------------------------------------------|
| A   | sélection au sort, même cadence | que le **choix** des setups porte de l'information |
| B   | issues permutées dans la séance | que le **moment** porte de l'information |
| C   | la règle scellée sur tout l'univers | que la discrétion ajoute quoi que ce soit à une règle bête |
| D   | indépendance décision/issue | que l'**abstention** soit informative |
| E   | rééchantillonnage par blocs | que le résultat tienne à autre chose qu'à quelques décisions |

La loi C est celle qui fait mal, et c'est celle qui donne sa force au
dispositif : elle ne demande pas si l'opérateur gagne, elle demande s'il fait
mieux qu'une règle qu'on peut écrire en dix lignes. Un opérateur qui bat A, B
et D mais pas C a démontré une compétence — et démontré du même coup qu'elle
ne vaut pas son coût.

**Sur le niveau et la puissance.** Toutes les lois simulées ici sont
calibrées par construction : appliquées à un journal sans compétence
(`journal.synthesise(skill=0.0)`), elles doivent conclure à l'absence dans
environ 95 % des cas. C'est le contrôle que `tests/test_operator.py` exerce,
et c'est ce qui distingue un appareil de mesure d'une machine à confirmer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .costs import deflated_threshold_sharpe
from .entropy import miller_madow, mutual_information, null_mutual_information
from .journal import Journal
from .mc import Rng, block_length_for_autocorrelation, stationary_bootstrap

#: Nombre de tirages par défaut des lois simulées. 600 suffit pour un
#: quantile à 95 % ; au-delà on gagne de la décimale, pas de la décision.
DRAWS = 600

#: Graine des lois nulles. Décalée d'un jour de la graine du dépôt, comme
#: `strategy.validate`, pour désolidariser le test des données qu'il juge.
SEED = 20260822


@dataclass(frozen=True)
class NullTest:
    """Le verdict d'une loi nulle sur un journal."""

    key: str
    label: str
    refutes: str            # la prétention tombée si la loi n'est pas battue
    observed: float
    null_mean: float
    null_sd: float
    q95: float
    p_value: float
    draws: int
    applicable: bool = True
    note: str = ""

    @property
    def z(self) -> float:
        """L'écart à la loi nulle, en écarts-types simulés."""
        if self.null_sd <= 0.0:
            return 0.0
        return (self.observed - self.null_mean) / self.null_sd

    @property
    def beats(self) -> bool:
        """L'observé dépasse-t-il le quantile 95 % de la loi nulle ?

        Une loi sans objet est comptée comme non battue : l'absence de test
        n'est pas une réussite au test. C'est l'inverse de la convention de
        `strategy.validate` pour la PBO, et le choix est délibéré — ici
        l'inapplicabilité signale un journal incomplet, pas une question sans
        objet.
        """
        return self.applicable and self.observed > self.q95

    @property
    def reading(self) -> str:
        if not self.applicable:
            return f"sans objet — {self.note}"
        verdict = "battue" if self.beats else "non battue"
        return (f"{verdict} · z = {self.z:+.2f} · p = {self.p_value:.3f}")


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _sd(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def _quantile(xs: list[float], q: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    pos = q * (len(s) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def _summarise(key: str, label: str, refutes: str, observed: float,
               draw: list[float], draws: int) -> NullTest:
    """Résume une loi simulée. La p-valeur suit la convention (hits+1)/(n+1).

    Le +1 n'est pas cosmétique : sans lui une loi qui n'est jamais dépassée
    rendrait p = 0, ce qui affirmerait une certitude que le nombre de tirages
    ne permet pas. Avec 600 tirages, la plus petite p-valeur énonçable est
    1/601, et c'est la vérité.
    """
    hits = sum(1 for x in draw if x >= observed)
    return NullTest(
        key=key, label=label, refutes=refutes, observed=observed,
        null_mean=_mean(draw), null_sd=_sd(draw), q95=_quantile(draw, 0.95),
        p_value=(hits + 1) / (len(draw) + 1), draws=draws,
    )


# ---------------------------------------------------------------------------
# Loi A — la sélection au sort
# ---------------------------------------------------------------------------


def null_selection(journal: Journal, draws: int = DRAWS,
                   seed: int = SEED) -> NullTest:
    """L'adversaire prend le même **nombre** de setups, choisis au sort.

    C'est la loi centrale. Elle isole exactement ce que l'opérateur
    revendique : que son choix, parmi des setups tous éligibles, porte de
    l'information. La cadence, la période, la mise moyenne et la loi des
    résultats sont tenues identiques ; seule la sélection change.

    Tenir la cadence constante n'est pas un raffinement. Un adversaire qui
    prendrait un nombre différent de setups changerait aussi la variance de
    la moyenne, et l'écart mesuré mêlerait sélectivité et compétence.
    """
    outcomes = [d.net_r for d in journal.decisions if d.net_r is not None]
    n_take = journal.n_taken
    if n_take < 2 or len(outcomes) <= n_take:
        return NullTest("selection", "Sélection au sort",
                        "que le choix des setups porte de l'information",
                        0.0, 0.0, 0.0, 0.0, 1.0, 0,
                        applicable=False,
                        note="trop peu de setups refusés pour tirer au sort")

    rng = Rng(seed)
    n = len(outcomes)
    draw: list[float] = []
    for _ in range(draws):
        # Tirage sans remise : on choisit n_take rangs distincts, ce qui
        # reproduit exactement la contrainte de l'opérateur.
        pool = list(outcomes)
        total = 0.0
        for k in range(n_take):
            j = k + rng.randint(n - k)
            pool[k], pool[j] = pool[j], pool[k]
            total += pool[k]
        draw.append(total / n_take)

    return _summarise("selection", "Sélection au sort",
                      "que le choix des setups porte de l'information",
                      journal.mean_r, draw, draws)


# ---------------------------------------------------------------------------
# Loi B — les issues permutées dans la séance
# ---------------------------------------------------------------------------


def null_timing(journal: Journal, draws: int = DRAWS,
                seed: int = SEED) -> NullTest:
    """L'adversaire garde les décisions, mais permute les issues **dans la séance**.

    La permutation est intra-séance et non globale, et ce point décide de la
    validité du test. Une permutation globale détruirait aussi la structure
    de volatilité entre séances — la saisonnalité en U, les jours calmes et
    les jours agités — et l'écart mesuré confondrait alors compétence de
    timing et simple exposition aux séances favorables. En permutant à
    l'intérieur du jour, on ne conteste que le choix de la minute.
    """
    by_day: dict[str, list[int]] = {}
    for i, d in enumerate(journal.decisions):
        if d.net_r is not None:
            by_day.setdefault(d.day, []).append(i)
    usable = [idx for idx in by_day.values() if len(idx) >= 2]
    if journal.n_taken < 2 or not usable:
        return NullTest("timing", "Issues permutées dans la séance",
                        "que le moment choisi porte de l'information",
                        0.0, 0.0, 0.0, 0.0, 1.0, 0,
                        applicable=False,
                        note="aucune séance ne porte deux setups ou plus")

    outcomes = [d.net_r for d in journal.decisions]
    sizes = [d.size if d.taken else 0.0 for d in journal.decisions]
    rng = Rng(seed + 1)
    draw: list[float] = []
    for _ in range(draws):
        shuffled = list(outcomes)
        for idx in usable:
            vals = [outcomes[i] for i in idx]
            for k in range(len(vals) - 1, 0, -1):
                j = rng.randint(k + 1)
                vals[k], vals[j] = vals[j], vals[k]
            for i, v in zip(idx, vals):
                shuffled[i] = v
        num = sum(s * (v or 0.0) for s, v in zip(sizes, shuffled))
        draw.append(num / journal.n_taken)

    return _summarise("timing", "Issues permutées dans la séance",
                      "que le moment choisi porte de l'information",
                      journal.mean_r, draw, draws)


# ---------------------------------------------------------------------------
# Loi C — la règle scellée
# ---------------------------------------------------------------------------


def null_mechanical(journal: Journal) -> NullTest:
    """L'adversaire est la règle scellée, qui prend tout sans réfléchir.

    Cette loi n'est pas simulée : l'adversaire est déterministe, c'est
    l'univers entier des setups. La comparaison porte sur l'espérance par
    décision, et le test est un simple t apparié — les deux échantillons
    partagent le même prix, seule la sélection diffère.

    C'est la loi la plus dure, et la seule qui pose la question économique :
    non pas « l'opérateur gagne-t-il ? » mais « fait-il mieux que ce qu'on
    obtient sans lui ? ». Un avantage qui ne la bat pas n'a pas à être payé.
    """
    outcomes = [d.net_r for d in journal.decisions if d.net_r is not None]
    if journal.n_taken < 2 or len(outcomes) < 2:
        return NullTest("mecanique", "La règle scellée",
                        "que la discrétion ajoute à la règle",
                        0.0, 0.0, 0.0, 0.0, 1.0, 0,
                        applicable=False, note="échantillon insuffisant")

    base = _mean(outcomes)
    sd = _sd(journal.returns)
    n = journal.n_taken
    se = sd / math.sqrt(n) if sd > 0.0 and n > 0 else 0.0
    observed = journal.mean_r
    # Le quantile à 95 % de la loi de la moyenne sous « pas mieux que la
    # règle » : centrée sur l'espérance mécanique, dispersée par l'erreur
    # type de l'opérateur.
    q95 = base + 1.645 * se
    z = (observed - base) / se if se > 0.0 else 0.0
    p = 1.0 - _norm_cdf(z)
    return NullTest("mecanique", "La règle scellée",
                    "que la discrétion ajoute à la règle",
                    observed, base, se, q95, p, 0)


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


# ---------------------------------------------------------------------------
# Loi D — l'abstention comme information
# ---------------------------------------------------------------------------


def null_abstention(journal: Journal, draws: int = 400,
                    seed: int = 20260821) -> NullTest:
    """L'adversaire décide indépendamment de l'issue.

    La statistique est l'information mutuelle entre la décision (prendre ou
    refuser) et l'issue contrefactuelle, corrigée du biais de Miller-Madow.
    La correction n'est pas un ornement : sur une table 2×2 estimée à partir
    de quelques centaines d'observations, l'information mutuelle empirique
    est **positive en espérance même sous indépendance**, et un test qui
    l'ignorerait déclarerait une compétence à tout coup.

    C'est la loi qui mesure la compétence d'abstention, et elle est la
    première à devenir intestable : un journal sans abstentions ne remplit
    que la moitié de la table.
    """
    table = journal.contingency()
    total = sum(sum(row) for row in table)
    if total < 30 or not journal.skipped or not journal.taken:
        return NullTest("abstention", "Décision indépendante de l'issue",
                        "que l'abstention soit informative",
                        0.0, 0.0, 0.0, 0.0, 1.0, 0,
                        applicable=False,
                        note="table de contingence incomplète ou trop petite")

    observed = max(0.0, miller_madow(table))
    null = null_mutual_information(2, 2, total, draws=draws, seed=seed)
    z = null.z(observed)
    p = 1.0 - _norm_cdf(z) if null.sd > 0.0 else 1.0
    return NullTest("abstention", "Décision indépendante de l'issue",
                    "que l'abstention soit informative",
                    observed, null.mean, null.sd, null.q95, p, null.draws)


# ---------------------------------------------------------------------------
# Loi E — le rééchantillonnage par blocs
# ---------------------------------------------------------------------------


def null_bootstrap(journal: Journal, draws: int = DRAWS,
                   seed: int = SEED) -> NullTest:
    """L'adversaire est le journal lui-même, rééchantillonné par blocs.

    Le bootstrap stationnaire de Politis et Romano tire des blocs de longueur
    géométrique, calée sur le temps de décorrélation des résultats. Il répond
    à une question que les quatre autres lois ne posent pas : le résultat
    tient-il, ou repose-t-il sur une poignée de décisions ?

    La statistique retenue est la **borne basse à 2,5 %** de l'espérance
    rééchantillonnée. Un opérateur dont la borne basse passe sous zéro n'a pas
    un résultat fragile : il a un résultat que l'échantillon ne soutient pas.
    """
    r = journal.returns
    if len(r) < 30:
        return NullTest("bootstrap", "Rééchantillonnage par blocs",
                        "que le résultat tienne à plus que quelques décisions",
                        0.0, 0.0, 0.0, 0.0, 1.0, 0,
                        applicable=False, note="moins de 30 décisions prises")

    rho = _lag1(r)
    block = block_length_for_autocorrelation(rho)
    rng = Rng(seed + 2)
    means = [_mean(stationary_bootstrap(r, rng, block)) for _ in range(draws)]
    lo = _quantile(means, 0.025)
    # Ici l'observé est la borne basse, et le seuil est zéro : la loi nulle
    # n'est pas une distribution simulée mais la frontière économique.
    return NullTest("bootstrap", "Rééchantillonnage par blocs",
                    "que le résultat tienne à plus que quelques décisions",
                    lo, 0.0, _sd(means), 0.0,
                    sum(1 for m in means if m <= 0.0) / len(means),
                    draws)


def _lag1(xs: list[float]) -> float:
    if len(xs) < 3:
        return 0.0
    m = _mean(xs)
    num = sum((xs[i] - m) * (xs[i + 1] - m) for i in range(len(xs) - 1))
    den = sum((x - m) ** 2 for x in xs)
    return num / den if den > 0.0 else 0.0


# ---------------------------------------------------------------------------
# La batterie
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Verdict:
    """Ce que les cinq lois disent d'un journal, et ce qu'il en reste."""

    tests: tuple[NullTest, ...]
    n_eligible: int
    n_taken: int
    sharpe_trade: float
    budget: float
    threshold: float

    @property
    def beaten(self) -> tuple[NullTest, ...]:
        return tuple(t for t in self.tests if t.beats)

    @property
    def survived(self) -> tuple[NullTest, ...]:
        """Les lois que l'opérateur n'a pas battues. Ce sont elles qui parlent."""
        return tuple(t for t in self.tests if not t.beats)

    @property
    def clears_deflation(self) -> bool:
        """Le Sharpe dépasse-t-il le seuil déflaté par 2^k configurations ?"""
        return self.sharpe_trade > self.threshold

    @property
    def accepted(self) -> bool:
        """Un avantage n'est déclaré que si **toutes** les lois sont battues
        et que la taxe de multiplicité est payée. Aucune pondération, aucune
        moyenne : la convention est celle de `strategy.validate`."""
        return not self.survived and self.clears_deflation

    @property
    def summary(self) -> str:
        if self.accepted:
            return (f"avantage déclarable : {len(self.beaten)} lois battues, "
                    f"seuil déflaté franchi")
        manquantes = ", ".join(t.key for t in self.survived) or "aucune"
        if not self.clears_deflation:
            return (f"refusé — lois non battues : {manquantes} ; "
                    f"seuil déflaté {self.threshold:.4f} non franchi "
                    f"(Sharpe {self.sharpe_trade:+.4f})")
        return f"refusé — lois non battues : {manquantes}"


def evaluate(journal: Journal, draws: int = DRAWS,
             seed: int = SEED) -> Verdict:
    """Fait passer les cinq lois, et chiffre la taxe de multiplicité.

    L'ordre est celui du coût de calcul croissant, comme dans la batterie de
    `strategy.validate` : une loi bon marché qui refuse épargne les autres,
    mais on les calcule toutes parce que le papier a besoin du tableau
    complet, pas seulement du verdict.
    """
    tests = (
        null_mechanical(journal),
        null_selection(journal, draws, seed),
        null_timing(journal, draws, seed),
        null_abstention(journal),
        null_bootstrap(journal, draws, seed),
    )
    budget = journal.budget
    threshold = deflated_threshold_sharpe(max(2.0, budget),
                                          max(journal.n_taken, 1))
    return Verdict(tests=tests, n_eligible=journal.n_eligible,
                   n_taken=journal.n_taken,
                   sharpe_trade=journal.sharpe_trade,
                   budget=budget, threshold=threshold)
