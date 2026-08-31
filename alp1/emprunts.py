"""Cinq disciplines empruntées, et ce que chacune rend au dispositif.

Pourquoi emprunter
------------------
Un fonds qui n'embauche aucun opérateur de marché n'a pas remplacé le jugement
par de la puissance de calcul : il a remplacé une question posée en langue de
salle de marché par une question posée dans une discipline qui savait déjà y
répondre. Cette partie fait le même trajet, dans le sens inverse. Elle prend
cinq disciplines constituées, en extrait ce qui se mesure sur une séance, et
publie pour chacune **la fréquence de son motif sous un prix sans dérive**.

Les cinq, et l'ordre dans lequel elles viennent, ne sont pas un goût. C'est
l'ordre de ce qu'elles touchent dans l'identité qui gouverne tout le
document ::

    E[R] = (µ · E[τ∧T] − c) / a

Le marché ne concède que `µ`. L'opérateur fixe `a` et, par sa géométrie,
`E[τ∧T]` ; la friction fixe `c`. Une discipline qui déplace `E[τ∧T]` déplace
donc le seuil de rentabilité sans rien dire du sens, et c'est le cas de la
plupart. Une seule des cinq touche `µ`.

Ce que chacune apporte, en une ligne
------------------------------------
* **L'unité d'observation** (biostatistique élémentaire) : le nombre d'années
  requis pour établir un Sharpe donné ne dépend pas du pas de temps observé.
  Choisir la minute plutôt que la séance ne prouve rien de plus — sauf par la
  multiplicité que ce choix introduit, et dont le coût est *logarithmique*.
* **L'analyse de survie** : un extrême de séance a un taux de hasard, et ce
  taux n'est pas maximal à l'instant où l'extrême est posé. Sa loi nulle est
  fermée — le principe de réflexion — donc aucune simulation n'est requise
  pour savoir ce qu'un sommet vaut. Le piège de la discipline est la censure
  à droite : ignorer les séances non résolues fausse la médiane.
* **Les processus auto-excitants** (Hawkes, sismologie) : l'activité appelle
  l'activité, avec une décroissance chiffrable. La loi nulle est le Poisson
  homogène. Ce que l'excitation déplace, c'est l'horloge — donc `E[τ∧T]`,
  donc `µ*` — et jamais la direction.
* **Les valeurs extrêmes** : la loi de l'arc sinus dit à quelle heure le haut
  du jour se pose, sans aucune propriété de marché ; la Pareto généralisée
  dit ce qui vit au-delà du stop. Le piège est le même que celui de la taille
  de grappe : le nombre d'observations retenues décide de l'indice de queue.
* **La théorie de la détection** (psychophysique) : elle sépare enfin les deux
  choses que le taux de réussite mélange — la sensibilité `d′`, que
  l'opérateur ne choisit pas, et le critère, qu'il choisit entièrement. C'est
  la seule des cinq qui touche `µ`, et elle explique analytiquement le
  résultat que la grammaire du setup mesurait sur douze setups.
* **Le spectre en grande dimension** : combien de lectures peut-on suivre
  avant que le bruit fabrique une structure ? La transition de Baik-Ben
  Arous-Péché donne le seuil, et il ne dépend d'aucune propriété du marché.

Ce que la partie ne fait pas
---------------------------
Elle ne promet aucune de ces disciplines comme un avantage. Chacune arrive
avec sa loi nulle, et la dernière section publie le verdict **calculé** :
quel terme de l'identité la discipline déplace, de combien, et si ce
déplacement suffit à changer le signe d'un compte. Quatre des cinq déplacent
l'horloge, une seule déplace le sens, et aucune ne dispense du seuil.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from . import seuil, spectrum, stress
from .costs import COST_BASE, ES, _norm_ppf, norm_cdf
from .hmm import bayes_error, observations_to_separate, separability
from .horizon import outcome_scaled
from .mc import Rng
from .report import (HURST, INDEX_LEVEL, SESSION_MIN, SIGMA_1MIN, Table, num)

# ---------------------------------------------------------------------------
# Les constantes déclarées
# ---------------------------------------------------------------------------

#: Graine unique de la partie. Toute simulation en découle, et aucune ne tire
#: sa graine d'un résultat.
SEED = 20260902

SIGMA = SIGMA_1MIN                 # points par racine de minute
SESSION = SESSION_MIN              # 390 minutes

#: La largeur de stop de travail. C'est celle des parties XIII et XIV, et pour
#: la même raison : à 0,010 % une minute de bruit vaut deux fois le stop, et
#: il n'y a alors rien à mesurer qui ne soit du bruit.
STOP_PCT = 0.150
RR = 2.0

#: Géométrie de travail, et les deux grandeurs qu'elle fixe.
GEOM = seuil.geometry(STOP_PCT, reward_risk=RR)
STOP_PTS = GEOM.stop_points
FRICTION_RATIO = GEOM.friction_ratio          # c/a
BASE_RATE = 1.0 / (1.0 + RR)                  # q : la cible tombe d'abord
BREAK_EVEN_P = (1.0 + FRICTION_RATIO) / (1.0 + RR)

#: Risque de première espèce et puissance, déclarés une fois.
ALPHA = 0.05
PUISSANCE = 0.80
Z_ALPHA = _norm_ppf(1.0 - ALPHA / 2.0)
Z_BETA = _norm_ppf(PUISSANCE)
FACTEUR = Z_ALPHA + Z_BETA

SESSIONS_PAR_AN = 252.0

#: L'archive dont on suppose disposer : cinq ans de séances. Ce n'est pas un
#: paramètre ajusté, c'est ce qu'un opérateur a raisonnablement sous la main.
HORIZON_ANS = 5.0

#: Le Sharpe annuel de référence — celui qu'un livre intraday discrétionnaire
#: revendique couramment. Il sert de cible à établir, jamais de résultat.
SHARPE_REF = 1.0

#: Une carrière, en années. Sert au seul verdict de la table de multiplicité.
CARRIERE = 30.0

#: Le relevé réel d'un opérateur qui commence : trente décisions, deux mois.
RELEVE_REEL = 30
RELEVE_PAR_AN = 180.0


# ---------------------------------------------------------------------------
# I. L'unité d'observation — ce que le pas de temps ne change pas
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Unite:
    """Une unité d'observation, et ce qu'elle permet d'établir.

    Le point de la section tient dans le rapport entre deux de ses propriétés.
    `d_min` — la taille d'effet minimale détectable **sur cette unité** —
    parcourt quatre ordres de grandeur d'une ligne à l'autre. `sharpe_min` —
    la même exigence traduite en Sharpe annuel — ne bouge pas, parce que
    l'effet et le bruit se composent tous deux en racine du nombre d'unités.
    """

    cle: str
    nom: str
    par_an: float
    n: float
    quoi: str

    @property
    def annees(self) -> float:
        return self.n / self.par_an

    @property
    def d_min(self) -> float:
        """Effet minimal détectable sur une unité, en écarts-types."""
        return FACTEUR / math.sqrt(self.n)

    @property
    def sharpe_min(self) -> float:
        """Le même seuil, annualisé : `FACTEUR/√années`, et rien d'autre."""
        return self.d_min * math.sqrt(self.par_an)


UNITES: tuple[Unite, ...] = (
    Unite("minute", "la minute", SESSION * SESSIONS_PAR_AN,
          SESSION * SESSIONS_PAR_AN * HORIZON_ANS,
          "le signe du pas de prix suivant"),
    Unite("episode", "l'épisode de volatilité", 10.0 * SESSIONS_PAR_AN,
          10.0 * SESSIONS_PAR_AN * HORIZON_ANS,
          "une bouffée d'activité et son retour au calme"),
    Unite("extreme", "l'extrême de séance", 2.0 * SESSIONS_PAR_AN,
          2.0 * SESSIONS_PAR_AN * HORIZON_ANS,
          "le haut et le bas du jour, et l'heure de chacun"),
    Unite("decision", "la décision de l'opérateur", 2.0 * SESSIONS_PAR_AN,
          2.0 * SESSIONS_PAR_AN * HORIZON_ANS,
          "entrer, ou laisser passer"),
    Unite("seance", "la séance", SESSIONS_PAR_AN,
          SESSIONS_PAR_AN * HORIZON_ANS,
          "le rendement du jour"),
    Unite("releve", "le relevé qui existe", RELEVE_PAR_AN, float(RELEVE_REEL),
          "les trente premières décisions enregistrées"),
)


def annees_pour(sharpe: float) -> float:
    """Années requises pour établir un Sharpe annuel donné.

    `(FACTEUR/S)²`, et c'est tout : ni l'instrument, ni le pas de temps, ni
    la loi des rendements n'y entrent. La formule est celle de tout test de
    moyenne, écrite dans l'unité que la finance utilise.
    """
    if sharpe <= 0.0:
        return math.inf
    return (FACTEUR / sharpe) ** 2


def seuil_deflate(k_config: float) -> float:
    """Quantile déflaté de Bonferroni pour `k` configurations candidates."""
    return _norm_ppf(1.0 - ALPHA / (2.0 * k_config))


def annees_pour_avec(sharpe: float, k_config: float) -> float:
    """Années requises quand la conclusion est cherchée parmi `k` candidats."""
    if sharpe <= 0.0:
        return math.inf
    return ((seuil_deflate(k_config) + Z_BETA) / sharpe) ** 2


#: Le budget de configurations balayé. `2^k` pour `k` leviers, comme dans
#: `discipline` : la table lit donc directement en nombre de leviers.
LEVIERS_GRID: tuple[int, ...] = (0, 2, 4, 6, 8, 10, 12, 14, 16, 18)


def table_unites() -> Table:
    rows = []
    for u in UNITES:
        rows.append([
            u.nom,
            num(u.par_an, 0),
            num(u.n, 0),
            num(u.d_min, 4),
            num(u.sharpe_min, 2),
            u.quoi,
        ])
    return Table(
        key="emp_unites",
        caption="L'unité d'observation change tout sauf la conclusion",
        headers=["Unité", "Par an", "n disponible", "d′ minimal",
                 "Sharpe annuel équivalent", "Ce qu'on y observe"],
        rows=rows,
        note="Effet minimal détectable à " + num(100 * ALPHA, 0) + " % et "
             + num(100 * PUISSANCE, 0) + " % de puissance, soit "
             "`d = " + num(FACTEUR, 3) + "/√n`. La quatrième colonne parcourt "
             "quatre ordres de grandeur ; la cinquième ne bouge pas, et c'est "
             "le résultat de la section : **le nombre d'années décide, le pas "
             "de temps ne décide de rien**. La dernière ligne n'est pas une "
             "archive mais un relevé réel de " + num(RELEVE_REEL, 0)
             + " décisions — il faudrait "
             + num(annees_pour(SHARPE_REF), 1) + " ans pour établir un Sharpe "
             "de " + num(SHARPE_REF, 0) + ", quelle que soit l'unité choisie.",
        wrap_last=True,
    )


def table_multiplicite() -> Table:
    rows = []
    for k in LEVIERS_GRID:
        nb = float(2 ** k)
        z = seuil_deflate(nb)
        ans = annees_pour_avec(SHARPE_REF, nb)
        rows.append([
            num(k, 0),
            num(nb, 0),
            num(z, 2),
            num(FACTEUR / math.sqrt(HORIZON_ANS) * (z + Z_BETA) / FACTEUR, 2),
            num(ans, 1),
            "à portée" if ans <= CARRIERE else "hors de portée",
        ])
    return Table(
        key="emp_multiplicite",
        caption="Ce que coûte le fait de chercher, plutôt que de savoir",
        headers=["Leviers", "Configurations", "Quantile déflaté",
                 "Sharpe détectable en " + num(HORIZON_ANS, 0) + " ans",
                 "Années pour Sharpe " + num(SHARPE_REF, 0), "Verdict"],
        rows=rows,
        note="Déflation de Bonferroni sur `2^k` configurations, `k` leviers "
             "discrétionnaires — la comptabilité du recensement des leviers. "
             "Le fait "
             "utile est la **lenteur** de la colonne : passer d'une "
             "configuration à " + num(2.0 ** 18, 0) + " multiplie le nombre "
             "d'années par " + num(annees_pour_avec(SHARPE_REF, 2.0 ** 18)
                                   / annees_pour(SHARPE_REF), 2)
             + " seulement, parce que le quantile croît comme la racine du "
             "logarithme du nombre de candidats. Chercher coûte cher, mais "
             "beaucoup moins cher que ne le suggère le nombre de candidats. "
             "Verdict calculé contre une carrière de "
             + num(CARRIERE, 0) + " ans.",
    )


# ---------------------------------------------------------------------------
# II. L'analyse de survie — un extrême a un taux de hasard
# ---------------------------------------------------------------------------

#: Minute d'observation. L'extrême de la première partie de séance est posé,
#: et l'on demande combien de temps il tient.
T0 = 120.0
RESTE = SESSION - T0          # 270 minutes jusqu'à la clôture

N_SEANCES_SURVIE = 12000

#: Correction de continuité de Broadie-Glasserman-Kou : `β₁ = −ζ(½)/√(2π)`.
#: Une barrière surveillée toutes les `Δt` se comporte comme une barrière
#: continue déplacée de `β₁·σ√Δt` vers l'extérieur. Le nombre est une
#: constante universelle, pas un ajustement.
BETA_CONTINUITE = 0.5825971579390106


def survie_nulle(distance: float, minutes: float) -> float:
    """`P(le sommet tient m minutes)` en temps continu — forme fermée.

        S(m) = 2·Φ(d/(σ√m)) − 1

    C'est le principe de réflexion : la probabilité que le maximum d'une
    marche sans dérive sur `m` minutes reste sous `d` vaut la probabilité que
    la valeur terminale y reste, moins celle du chemin réfléchi. Elle ne
    contient ni instrument, ni heure, ni régime — seulement une distance
    rapportée à une racine de temps.
    """
    if minutes <= 0.0:
        return 1.0
    if distance <= 0.0:
        return 0.0
    return max(0.0,
               2.0 * norm_cdf(distance / (SIGMA * math.sqrt(minutes))) - 1.0)


def survie_minute(distance: float, minutes: float, pas: float = 1.0) -> float:
    """La même survie, mais pour un sommet **surveillé à la minute**.

    Un opérateur ne regarde pas le prix en temps continu : il regarde une
    bougie d'une minute, et déclare le sommet cassé quand une clôture le
    dépasse. Une barrière ainsi surveillée est franchie moins souvent qu'une
    barrière continue, et l'écart n'est pas un détail de simulation — il vaut
    `β₁·σ√Δt`, soit ici {shift} point, c'est-à-dire une fraction sensible
    d'une distance typique.

    C'est le même piège que la taille de grappe du footprint et la hauteur de
    rangée du profil de marché, sous une troisième forme : **le pas
    d'observation décide de la loi nulle**. La différence est qu'ici la
    correction est connue en forme fermée, donc le piège se referme.
    """
    return survie_nulle(distance + BETA_CONTINUITE * SIGMA * math.sqrt(pas),
                        minutes)


def hasard_nul(distance: float, minutes: float) -> float:
    """Le taux de hasard instantané, par minute.

        h(m) = φ(u)·u / (m·(2Φ(u) − 1)),   u = d/(σ√m)

    Dérivée logarithmique de la survie, changée de signe. C'est la quantité
    que l'analyse de survie appelle *risque instantané* : la probabilité que
    l'extrême tombe dans la minute qui vient, sachant qu'il a tenu jusque-là.
    """
    if minutes <= 0.0 or distance <= 0.0:
        return 0.0
    u = distance / (SIGMA * math.sqrt(minutes))
    s = 2.0 * norm_cdf(u) - 1.0
    if s <= 1e-12:
        return 0.0
    phi = math.exp(-0.5 * u * u) / math.sqrt(2.0 * math.pi)
    return phi * u / (minutes * s)


@lru_cache(maxsize=1)
def _u_pic() -> float:
    """La racine de `3/u − u = 2φ(u)/(2Φ(u)−1)`, par bissection.

    Elle n'a pas de forme fermée, et c'est le genre de détail qui se paie.
    Une première version de ce module posait `u = √3`, ce qu'on obtient en
    dérivant `u³φ(u)` et en oubliant que le dénominateur `2Φ(u)−1` dépend
    lui aussi de `u`. L'erreur était petite — la constante passe de 3 à
    {const} — et un test l'a trouvée en comparant la formule au maximum
    balayé numériquement. C'est la règle du dépôt : une forme fermée se
    contrôle contre la simulation, sans exception.
    """
    lo, hi = 0.5, 3.0
    for _ in range(120):
        mid = 0.5 * (lo + hi)
        s_mid = 2.0 * norm_cdf(mid) - 1.0
        phi = math.exp(-0.5 * mid * mid) / math.sqrt(2.0 * math.pi)
        if 3.0 / mid - mid - 2.0 * phi / s_mid > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def pic_hasard(distance: float) -> float:
    """La minute où le risque est maximal : `d²/(u*²σ²)`.

    En posant `u = d/(σ√m)`, le hasard s'écrit `(σ²/d²)·u³φ(u)/(2Φ(u)−1)`.
    Son maximum en `u` est la racine de `3/u − u = 2φ(u)/(2Φ(u)−1)`, soit
    `u* ≈ {u}` — donc `m* ≈ d²/({c}·σ²)`.

    Le fait est contre-intuitif et il est exact : **un sommet n'est pas le
    plus menacé à l'instant où il est posé.** Juste après, la distance est
    trop grande pour le bruit accumulé ; longtemps après, la survie a déjà
    éliminé les trajectoires qui montaient. Entre les deux se trouve un
    maximum, et il se calcule sans rien simuler.
    """
    u = _u_pic()
    return distance * distance / (u * u * SIGMA * SIGMA)


#: La constante du pic, `u*²`. Elle vaut 2,61 et non 3 : voir `_u_pic`.
def coef_pic() -> float:
    return _u_pic() ** 2


@dataclass(frozen=True)
class Obs:
    """Une observation de survie, et les deux censures qui la bornent.

    `duree_vraie` n'est jamais connue de l'opérateur : elle sert de référence
    et n'entre dans aucun estimateur. Ce que l'on observe est `duree`, bornée
    par la clôture **et** par la sortie de l'opérateur, avec le drapeau qui
    dit laquelle des deux a coupé.
    """

    distance: float
    duree_vraie: float
    duree: float
    censure: bool
    sortie: float


@lru_cache(maxsize=4)
def observations(n: int = N_SEANCES_SURVIE, seed: int = SEED) -> tuple[Obs, ...]:
    """Le sommet de la première partie de séance, et ce qu'il devient.

    Aucune dérive, aucune structure : un pas gaussien par minute. Tout ce que
    la table mesurera vient donc du seul mouvement brownien, ce qui est le
    but — la loi nulle d'un « le haut du jour tient » doit être connue avant
    qu'un opérateur ne revendique quoi que ce soit à ce sujet.

    Deux horloges bornent l'observation, et c'est la seconde qui rend la
    discipline nécessaire. La clôture censure tout le monde au même instant,
    ce qu'un simple comptage à la borne traite correctement. La **sortie de
    l'opérateur** censure chacun à un instant différent, tiré du même prix :
    la position est fermée dès que le prix s'écarte du stop déclaré, et le
    sort du sommet devient alors inobservable. C'est la situation réelle, et
    aucune méthode naïve n'y survit.
    """
    rng = Rng(seed)
    out: list[Obs] = []
    for _ in range(n):
        prix = 0.0
        haut = 0.0
        for _ in range(int(T0)):
            prix += SIGMA * rng.gauss()
            haut = max(haut, prix)
        distance = haut - prix
        depart = prix
        duree_vraie = RESTE
        vue = False
        sortie = RESTE
        dehors = False
        for m in range(1, int(RESTE) + 1):
            prix += SIGMA * rng.gauss()
            if not vue and prix >= haut:
                duree_vraie = float(m)
                vue = True
            if not dehors and abs(prix - depart) >= STOP_PTS:
                sortie = float(m)
                dehors = True
        borne = min(sortie, RESTE)
        duree = min(duree_vraie, borne)
        out.append(Obs(distance, duree_vraie if vue else math.inf,
                       duree, duree_vraie > borne if vue else True, sortie))
    return tuple(out)


#: Bornes des strates de distance, en points. Déclarées avant toute mesure.
STRATES: tuple[float, ...] = (0.0, 3.0, 6.0, 9.0, 14.0, 22.0, 1e9)

#: Horizon auquel la survie est comparée dans la table. Trente minutes : assez
#: long pour que la censure ne morde pas encore, assez court pour que la
#: strate reste peuplée.
M_TABLE = 30.0


def _strate(obs: tuple[Obs, ...], i: int) -> list[Obs]:
    lo, hi = STRATES[i], STRATES[i + 1]
    return [o for o in obs if lo <= o.distance < hi]


def kaplan_meier(obs: list[Obs]) -> list[tuple[float, float]]:
    """Estimateur de Kaplan-Meier, avec censure à droite.

        Ŝ(t) = Π_{tᵢ ≤ t} (1 − dᵢ/nᵢ)

    L'estimateur ne suppose aucune loi. Sa seule hypothèse est que la censure
    est non informative — ici elle l'est, la sortie étant décidée par une
    règle écrite d'avance et non par ce que le sommet allait faire.
    """
    evts = sorted({o.duree for o in obs if not o.censure})
    courbe = [(0.0, 1.0)]
    s = 1.0
    for t in evts:
        a_risque = sum(1 for o in obs if o.duree >= t)
        morts = sum(1 for o in obs if not o.censure and o.duree == t)
        if a_risque <= 0:
            break
        s *= 1.0 - morts / a_risque
        courbe.append((t, s))
    if courbe[-1][0] < RESTE:
        courbe.append((RESTE, s))
    return courbe


def _mediane(courbe: list[tuple[float, float]]) -> float:
    for t, s in courbe:
        if s <= 0.5:
            return t
    return math.inf


def _rmst(courbe: list[tuple[float, float]], borne: float = None) -> float:
    """Durée moyenne restreinte : l'aire sous la courbe de survie."""
    fin = RESTE if borne is None else borne
    aire = 0.0
    for (t0, s0), (t1, _) in zip(courbe, courbe[1:]):
        aire += s0 * (min(t1, fin) - t0)
        if t1 >= fin:
            return aire
    return aire + courbe[-1][1] * (fin - courbe[-1][0])


def survie_moyenne(minutes: float, obs: tuple[Obs, ...] | None = None,
                   pas: float = 1.0) -> float:
    """La survie exacte à la minute, moyennée sur la loi des distances.

    C'est la référence de la table de censure : elle n'estime rien, elle
    applique la forme fermée corrigée à chaque distance et prend la moyenne.
    Aucun estimateur ne peut faire mieux, et c'est ce qui permet de mesurer le
    biais des mauvaises méthodes plutôt que de le postuler.
    """
    o = obs if obs is not None else observations()
    return sum(survie_minute(x.distance, minutes, pas) for x in o) / len(o)


@lru_cache(maxsize=2)
def mediane_exacte() -> float:
    """La minute où la survie moyenne exacte franchit un demi, par bissection."""
    lo, hi = 0.5, RESTE
    if survie_moyenne(hi) > 0.5:
        return math.inf
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if survie_moyenne(mid) > 0.5:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


@lru_cache(maxsize=2)
def rmst_exact() -> float:
    """L'aire exacte sous la survie moyenne, par la règle de Simpson."""
    n = 540
    h = RESTE / n
    acc = 0.0
    for i in range(n + 1):
        w = 1.0 if i in (0, n) else (4.0 if i % 2 else 2.0)
        acc += w * survie_moyenne(i * h)
    return acc * h / 3.0


def table_hasard() -> Table:
    obs = observations()
    rows = []
    ec_c: list[float] = []
    ec_m: list[float] = []
    for i in range(len(STRATES) - 1):
        strate = _strate(obs, i)
        if len(strate) < 40:
            continue
        vus = sum(1 for o in strate if o.duree_vraie <= M_TABLE)
        mesure = 1.0 - vus / len(strate)
        continu = (sum(survie_nulle(o.distance, M_TABLE) for o in strate)
                   / len(strate))
        minute = (sum(survie_minute(o.distance, M_TABLE) for o in strate)
                  / len(strate))
        ec_c.append(mesure - continu)
        ec_m.append(mesure - minute)
        d_med = sorted(o.distance for o in strate)[len(strate) // 2]
        pic = pic_hasard(d_med)
        rows.append([
            (num(STRATES[i], 0) + " à " + num(STRATES[i + 1], 0) + " pt")
            if STRATES[i + 1] < 1e8
            else ("plus de " + num(STRATES[i], 0) + " pt"),
            num(len(strate), 0),
            num(100 * mesure, 1),
            num(100 * continu, 1),
            num(100 * minute, 1),
            num(pic, 1),
            num(60.0 * hasard_nul(d_med, max(pic, 0.5)), 1),
        ])
    mad_c = sum(abs(x) for x in ec_c) / len(ec_c)
    mad_m = sum(abs(x) for x in ec_m) / len(ec_m)
    pire_m = max(abs(x) for x in ec_m)
    return Table(
        key="emp_hasard",
        caption="La survie d'un sommet de séance, mesurée et fermée",
        headers=["Distance au sommet", "Occasions",
                 "Survie à " + num(M_TABLE, 0) + " min mesurée",
                 "Forme fermée continue", "Forme fermée à la minute",
                 "Pic de risque (min)", "Risque au pic (par heure)"],
        rows=rows,
        note="Sommet relevé à la " + num(T0, 0) + "e minute sur "
             + num(N_SEANCES_SURVIE, 0) + " séances sans dérive, sans aucune "
             "censure ici — c'est la durée vraie qui est mesurée. Les deux "
             "colonnes de forme fermée sont `2Φ(d/σ√m) − 1` moyennée sur les "
             "distances effectivement observées dans la strate : la première "
             "en temps continu, la seconde pour une barrière surveillée à la "
             "minute. **C'est la seconde qui décrit ce qu'un opérateur "
             "voit** — écart absolu moyen de " + num(100 * mad_m, 1)
             + " point contre " + num(100 * mad_c, 1) + " pour la forme "
             "continue, et il n'est pas réparti : une seule strate le porte "
             "presque entier. Ce qui reste est le second ordre de la "
             "correction, "
             "sensible seulement à trente minutes : sur l'horizon de séance "
             "de la table de calibration, il retombe sous le point. Les deux "
             "dernières "
             "colonnes portent le fait de la section : le risque n'est pas "
             "maximal quand le sommet vient d'être posé, mais `d²/"
             + num(coef_pic(), 2) + "σ²` minutes plus tard — la constante "
             "est la racine d'une équation sans forme fermée, et elle ne "
             "vaut pas trois.",
    )


def table_censure() -> Table:
    obs = observations()
    part_censuree = sum(1 for o in obs if o.censure) / len(obs)
    part_sortie = sum(1 for o in obs
                      if o.censure and o.sortie < RESTE) / len(obs)

    med_vraie = mediane_exacte()
    rmst_vrai = rmst_exact()

    gardes = [o for o in obs if not o.censure]
    med_ignore = sorted(o.duree for o in gardes)[len(gardes) // 2]
    rmst_ignore = sum(min(o.duree, RESTE) for o in gardes) / len(gardes)

    toutes = sorted(o.duree for o in obs)
    med_borne = toutes[len(toutes) // 2]
    rmst_borne = sum(o.duree for o in obs) / len(obs)

    courbe = kaplan_meier(list(obs))
    med_km = _mediane(courbe)
    rmst_km = _rmst(courbe)

    def ligne(nom: str, med: float, rmst: float, part: float,
              quoi: str) -> list[str]:
        return [nom,
                "\u221e" if med == math.inf else num(med, 1),
                num(rmst, 1),
                num(100 * part, 1),
                num(100 * (rmst - rmst_vrai) / rmst_vrai, 1, signed=True),
                quoi]

    rows = [
        ligne("En écartant les observations non résolues", med_ignore,
              rmst_ignore, 1.0 - part_censuree,
              "la méthode que tout le monde emploie sans le dire"),
        ligne("En les arrêtant à la borne", med_borne, rmst_borne, 1.0,
              "l'autre facilité, de biais opposé"),
        ligne("Kaplan-Meier", med_km, rmst_km, 1.0,
              "l'estimateur de la discipline, sans hypothèse de loi"),
        ligne("Forme fermée moyennée", med_vraie, rmst_vrai, 1.0,
              "la référence, calculée et non estimée"),
    ]
    return Table(
        key="emp_censure",
        caption="Ce que coûte le fait d'écarter ce qui n'a pas fini",
        headers=["Méthode", "Médiane (min)", "Durée moyenne restreinte (min)",
                 "Part de l'échantillon utilisée", "Écart à la référence",
                 "Ce que c'est"],
        rows=rows,
        note=num(100 * part_censuree, 1) + " % des observations sont "
             "**censurées à droite**, dont " + num(100 * part_sortie, 1)
             + " % par la sortie de l'opérateur et le reste par la clôture. "
             "Écarter les non résolues revient à ne garder que les sommets "
             "qui sont tombés, donc à répondre à une autre question — la "
             "durée moyenne y perd "
             + num(abs(100 * (rmst_ignore - rmst_vrai) / rmst_vrai), 0)
             + " %. Les arrêter à la borne fait l'erreur opposée, et le "
             "hasard veut qu'elle soit ici du même signe : les deux "
             "facilités se trompent, jamais l'une contre l'autre. "
             "Kaplan-Meier ne suppose aucune loi et retrouve la référence, "
             "qui est ici calculable parce que la loi nulle est fermée — "
             "**la discipline se vérifie sur un cas où l'on connaît la "
             "réponse, puis s'emploie là où on ne la connaît pas.**",
        wrap_last=True,
    )


#: Nombre de tranches de la courbe de calibration. Dix : assez pour voir une
#: courbure, assez peu pour que chaque tranche porte plus de mille
#: observations.
N_TRANCHES = 10


def calibration(pas: float = 1.0) -> list[tuple[float, float, float, int]]:
    """Prédiction continue, prédiction à la minute, fréquence, effectif.

    C'est l'épreuve que la discipline impose à toute probabilité annoncée :
    parmi les cas où l'on a dit « soixante-dix pour cent », soixante-dix pour
    cent doivent se réaliser. Une prédiction peut être parfaitement calibrée
    et sans aucune valeur — c'est exactement le cas ici, et c'est le point.
    """
    obs = observations()
    triple = [(survie_nulle(o.distance, RESTE),
               survie_minute(o.distance, RESTE, pas),
               o.duree_vraie > RESTE) for o in obs]
    triple.sort(key=lambda t: t[1])
    n = len(triple)
    out = []
    for i in range(N_TRANCHES):
        lo = i * n // N_TRANCHES
        hi = (i + 1) * n // N_TRANCHES
        bloc = triple[lo:hi]
        if not bloc:
            continue
        out.append((sum(a for a, _, _ in bloc) / len(bloc),
                    sum(b for _, b, _ in bloc) / len(bloc),
                    sum(1 for _, _, c in bloc if c) / len(bloc),
                    len(bloc)))
    return out


def table_calibration() -> Table:
    rows = []
    biais_c: list[float] = []
    biais_m: list[float] = []
    for i, (pc, pm, freq, n) in enumerate(calibration(), start=1):
        sd = math.sqrt(max(pm * (1.0 - pm), 1e-9) / n)
        z = (freq - pm) / sd
        biais_c.append(freq - pc)
        biais_m.append(freq - pm)
        rows.append([
            num(i, 0),
            num(100 * pc, 1),
            num(100 * pm, 1),
            num(100 * freq, 1),
            num(100 * (freq - pm), 1, signed=True),
            num(n, 0),
            num(z, 2, signed=True),
        ])
    moy_c = sum(biais_c) / len(biais_c)
    moy_m = sum(biais_m) / len(biais_m)
    abs_c = sum(abs(x) for x in biais_c) / len(biais_c)
    abs_m = sum(abs(x) for x in biais_m) / len(biais_m)
    return Table(
        key="emp_calibration",
        caption="La forme fermée, mise à l'épreuve de la calibration",
        headers=["Tranche", "Annoncé, temps continu", "Annoncé, à la minute",
                 "Fréquence observée", "Écart", "Occasions", "z"],
        rows=rows,
        note="Chaque séance reçoit sa probabilité annoncée que son sommet "
             "tienne jusqu'à la clôture, `2\u03a6(d/\u03c3\u221a" + num(RESTE, 0)
             + ") \u2212 1` ; les séances sont rangées par cette probabilité et la "
             "fréquence réelle est relevée par tranche. Le biais moyen vaut "
             + num(100 * moy_c, 2, signed=True) + " point en temps continu et "
             + num(100 * moy_m, 2, signed=True) + " point une fois la "
             "barrière corrigée du pas d'observation ; l'écart absolu moyen "
             "passe de " + num(100 * abs_c, 2) + " à " + num(100 * abs_m, 2)
             + " point. La conclusion est double, et la seconde moitié "
             "compte plus que la première : la formule est **exacte**, donc "
             "utilisable telle quelle comme loi nulle — et elle est exacte "
             "*sans rien savoir du marché*, donc une lecture qui se contente "
             "de la retrouver n'a rien démontré.",
    )


# ---------------------------------------------------------------------------
# III. L'auto-excitation — l'activité appelle l'activité
# ---------------------------------------------------------------------------

#: Les trois paramètres du processus de Hawkes exponentiel, déclarés. `µ` est
#: le fond exogène, `β` la vitesse d'oubli, et le ratio de branchement
#: `n = α/β` la part de l'activité qui est fille d'une autre.
HAWKES_MU = 0.10           # événements par minute, arrivés du dehors
HAWKES_BETA = 0.60         # par minute — le noyau oublie en 1,7 minute
HAWKES_N = 0.75            # ratio de branchement déclaré
HAWKES_ALPHA = HAWKES_N * HAWKES_BETA

#: Le ratio de branchement retenu est celui que la littérature de
#: microstructure mesure sur le flux d'ordres d'un indice liquide — trois
#: événements sur quatre y sont fils d'un autre. Il est **déclaré**, jamais
#: ajusté sur une quantité que la partie évalue ensuite.

T_HAWKES = 40000.0         # minutes simulées
N_TIRAGES_NULS = 240       # tirages de la loi nulle de Poisson
_BUDGET_NUL = 200000       # comptes de Poisson tirés, au plus, par fenêtre

FENETRES: tuple[float, ...] = (5.0, 10.0, 25.0, 50.0, 100.0, 200.0, 400.0)


def intensite_moyenne(mu: float = HAWKES_MU, n: float = HAWKES_N) -> float:
    """`λ̄ = µ/(1 − n)` — le fond, plus toute sa descendance."""
    return mu / (1.0 - n)


@lru_cache(maxsize=8)
def hawkes(mu: float = HAWKES_MU, alpha: float = HAWKES_ALPHA,
           beta: float = HAWKES_BETA, horizon: float = T_HAWKES,
           seed: int = SEED + 1) -> tuple[float, ...]:
    """Simulation exacte par amincissement d'Ogata.

    L'intensité conditionnelle vaut `λ(t) = µ + Σ_{tᵢ<t} α·e^{−β(t−tᵢ)}`. Le
    noyau exponentiel permet de la tenir à jour en une opération par
    événement, et l'amincissement en fait une simulation **exacte** : on
    propose un instant sous une majorante, on l'accepte avec la probabilité du
    rapport des deux intensités.
    """
    rng = Rng(seed)
    t = 0.0
    excitation = 0.0
    out: list[float] = []
    while True:
        borne = mu + excitation
        w = -math.log(max(rng.uniform(), 1e-300)) / borne
        t += w
        if t >= horizon:
            break
        excitation *= math.exp(-beta * w)
        if rng.uniform() * borne <= mu + excitation:
            out.append(t)
            excitation += alpha
    return tuple(out)


def fano(instants: tuple[float, ...], fenetre: float,
         horizon: float = T_HAWKES) -> float:
    """Rapport de Fano : variance sur moyenne des comptes par fenêtre.

    Il vaut **un** pour un Poisson homogène, quelle que soit la fenêtre, et
    tend vers `1/(1 − n)²` pour un Hawkes exponentiel quand la fenêtre est
    longue devant la mémoire. C'est l'estimateur le plus économe de
    l'auto-excitation : il ne demande ni ajustement ni vraisemblance.
    """
    k = int(horizon / fenetre)
    if k < 8:
        raise ValueError("fenêtre trop longue pour l'horizon")
    comptes = [0] * k
    for t in instants:
        i = int(t / fenetre)
        if 0 <= i < k:
            comptes[i] += 1
    moy = sum(comptes) / k
    if moy <= 0.0:
        return 0.0
    var = sum((c - moy) ** 2 for c in comptes) / (k - 1)
    return var / moy


def branchement_implicite(f: float) -> float:
    """`n̂ = 1 − 1/√F` — l'inversion du rapport de Fano asymptotique."""
    if f <= 0.0:
        return 0.0
    return 1.0 - 1.0 / math.sqrt(f)


@lru_cache(maxsize=8)
def bande_poisson(fenetre: float, taux: float,
                  tirages: int = N_TIRAGES_NULS,
                  horizon: float = T_HAWKES,
                  seed: int = SEED + 2) -> tuple[float, float, float]:
    """La loi nulle du rapport de Fano : Poisson homogène, même taux.

    Elle est indispensable et souvent oubliée. Sur un nombre fini de fenêtres,
    `F̂` fluctue autour de un ; sans sa bande, un `F̂` de 1,2 se lit comme de
    l'excitation alors qu'il peut n'être que du comptage.
    """
    rng = Rng(seed + int(fenetre))
    k = int(horizon / fenetre)
    tirages = max(60, min(tirages, _BUDGET_NUL // max(k, 1)))
    vals = []
    for _ in range(tirages):
        comptes = []
        for _ in range(k):
            # Poisson par la méthode de Knuth : le taux par fenêtre est
            # modéré, donc le produit d'uniformes reste stable.
            lam = taux * fenetre
            seuil_p = math.exp(-lam)
            p, c = rng.uniform(), 0
            while p > seuil_p:
                c += 1
                p *= rng.uniform()
            comptes.append(c)
        moy = sum(comptes) / k
        var = sum((c - moy) ** 2 for c in comptes) / (k - 1)
        vals.append(var / moy if moy > 0 else 0.0)
    vals.sort()
    return (vals[int(0.025 * len(vals))],
            vals[len(vals) // 2],
            vals[int(0.975 * len(vals))])


def table_hawkes() -> Table:
    inst = hawkes()
    taux = len(inst) / T_HAWKES
    rows = []
    for w in FENETRES:
        f = fano(inst, w)
        lo, med, hi = bande_poisson(w, taux)
        rows.append([
            num(w, 0),
            num(f, 2),
            num(med, 2),
            num(lo, 2) + " à " + num(hi, 2),
            num(branchement_implicite(f), 3),
            "excitation" if f > hi else "indistinguable du Poisson",
        ])
    return Table(
        key="emp_hawkes",
        caption="L'auto-excitation, vue par le seul rapport de Fano",
        headers=["Fenêtre (min)", "F mesuré", "F médian sous Poisson",
                 "Bande à 95 % sous Poisson", "Ratio de branchement implicite",
                 "Verdict"],
        rows=rows,
        note="Processus de Hawkes exponentiel simulé par amincissement "
             "d'Ogata sur " + num(T_HAWKES, 0) + " minutes, fond "
             + num(HAWKES_MU, 2) + " événement par minute, mémoire "
             + num(1.0 / HAWKES_BETA, 1) + " minute, ratio de branchement "
             "déclaré " + num(HAWKES_N, 2) + ". Le ratio implicite de la "
             "cinquième colonne vient de `n̂ = 1 − 1/√F`, valable quand la "
             "fenêtre est longue devant la mémoire — ce qui explique que les "
             "fenêtres courtes le sous-estiment, et non l'inverse. La bande "
             "de Poisson est la loi nulle : sans elle, un F de 1,2 se lirait "
             "comme de l'excitation.",
    )


#: Fenêtres après un événement, pour lire la décroissance.
APRES: tuple[tuple[float, float], ...] = (
    (0.0, 1.0), (1.0, 2.0), (2.0, 4.0), (4.0, 8.0), (8.0, 16.0), (16.0, 40.0),
)


def reponse_mesuree(instants: tuple[float, ...],
                    borne: tuple[float, float]) -> float:
    """Taux d'événements dans une fenêtre après chaque événement."""
    lo, hi = borne
    n = len(instants)
    total = 0
    fenetres = 0
    j0 = 0
    for i, t in enumerate(instants):
        if t + hi > instants[-1]:
            break
        fenetres += 1
        j = max(j0, i + 1)
        while j < n and instants[j] < t + lo:
            j += 1
        while j < n and instants[j] < t + hi:
            total += 1
            j += 1
    if fenetres == 0:
        return 0.0
    return total / (fenetres * (hi - lo))


def amplitude_palm(alpha: float = HAWKES_ALPHA,
                   beta: float = HAWKES_BETA) -> float:
    """`α(2β − α)/(2(β − α))` — l'amplitude du relèvement, à l'événement.

    Ce n'est **pas** `α`, et la différence n'est pas cosmétique. Conditionner
    sur un événement fait deux choses : cela ajoute la descendance de cet
    événement, ce que `α` décrit ; mais cela sélectionne aussi un instant où
    l'intensité était déjà élevée, puisqu'un événement y est plus probable.
    Le second terme est du même ordre que le premier et l'oublier sous-estime
    la réponse d'un facteur deux et demi à ratio de branchement élevé.

    Le contrôle est immédiat : intégrée sur le temps, cette amplitude doit
    rendre le rapport de Fano `1/(1−n)²`, ce qu'un test vérifie.
    """
    return alpha * (2.0 * beta - alpha) / (2.0 * (beta - alpha))


def reponse_fermee(t: float, mu: float = HAWKES_MU,
                   alpha: float = HAWKES_ALPHA,
                   beta: float = HAWKES_BETA,
                   lam_bar: float | None = None) -> float:
    """L'intensité attendue `t` après un événement — intensité de Palm.

        E[λ(t) | événement en 0] = λ̄ + A·e^{−(β−α)t}

    La forme est celle d'Omori en sismologie : une secousse relève le taux, et
    le relèvement décroît. L'exposant n'est pas `β` mais `β − α`, parce que
    la descendance de la descendance prolonge la mémoire — c'est exactement
    ce que le ratio de branchement mesure.
    """
    n = alpha / beta
    fond = mu / (1.0 - n) if lam_bar is None else lam_bar
    return fond + amplitude_palm(alpha, beta) * math.exp(-(beta - alpha) * t)


def reponse_moyenne(lo: float, hi: float, mu: float = HAWKES_MU,
                    alpha: float = HAWKES_ALPHA,
                    beta: float = HAWKES_BETA,
                    lam_bar: float | None = None) -> float:
    """La même réponse, moyennée sur une fenêtre — car c'est ce qui se mesure.

    Sur les fenêtres larges, évaluer la forme fermée au milieu de la fenêtre
    la sous-estime : l'exponentielle est convexe. L'intégrale est immédiate et
    évite un désaccord qui n'aurait rien appris.
    """
    n = alpha / beta
    fond = mu / (1.0 - n) if lam_bar is None else lam_bar
    g = beta - alpha
    a = amplitude_palm(alpha, beta)
    if hi <= lo:
        return fond + a * math.exp(-g * lo)
    return fond + a * (math.exp(-g * lo) - math.exp(-g * hi)) / (g * (hi - lo))


def table_omori() -> Table:
    inst = hawkes()
    fond = len(inst) / T_HAWKES
    rows = []
    for lo, hi in APRES:
        mesure = reponse_mesuree(inst, (lo, hi))
        ferme = reponse_moyenne(lo, hi, lam_bar=fond)
        rows.append([
            num(lo, 0) + " à " + num(hi, 0),
            num(mesure, 3),
            num(ferme, 3),
            num(fond, 3),
            num(mesure / fond, 2),
            num(1.0, 2),
        ])
    return Table(
        key="emp_omori",
        caption="La décroissance d'Omori, mesurée contre son Poisson",
        headers=["Minutes après un événement", "Taux mesuré (par min)",
                 "Forme fermée", "Taux de fond", "Rapport au fond",
                 "Rapport sous Poisson"],
        rows=rows,
        note="La forme fermée est l'intensité de Palm `λ̄ + A·e^{−(β−α)t}`, "
             "moyennée sur la fenêtre. Le relèvement décroît avec une "
             "constante de temps de "
             + num(1.0 / (HAWKES_BETA - HAWKES_ALPHA), 1)
             + " minutes, plus longue que la mémoire du noyau parce que la "
             "descendance prolonge la secousse. Son amplitude vaut "
             "`α(2β−α)/2(β−α)` et non `α` : conditionner sur un événement "
             "sélectionne aussi un instant où l'intensité était déjà haute, "
             "et ce second terme vaut ici "
             + num(amplitude_palm() / HAWKES_ALPHA, 1) + " fois le premier. La dernière colonne est la "
             "loi nulle et elle vaut **un partout** : sous Poisson homogène, "
             "un événement ne dit rien du suivant. C'est le seul point de "
             "comparaison qui vaille.",
    )


#: Intensités relatives balayées pour la table d'horloge, et les instants
#: correspondants après un événement.
INSTANTS_APRES: tuple[float, ...] = (0.0, 2.0, 5.0, 10.0, 20.0, 40.0)


def horloge_excitee(t_apres: float, n: float = HAWKES_N) -> tuple[float, float, float, float]:
    """Ce qu'une bouffée d'activité fait au temps de marché, et au seuil.

    L'hypothèse est déclarée et minimale : chaque événement déplace le prix
    d'un pas de taille fixe, donc la variance par minute est proportionnelle à
    l'intensité et `σ ∝ √λ`. Rien d'autre n'est supposé — surtout aucune
    direction.

    La conséquence est la seule qui intéresse le document. `E[τ∧T]` diminue
    comme l'inverse de la variance, donc `µ* = c/E[τ∧T]` **monte** : une
    bouffée d'activité ne rend pas le marché plus payant, elle rend le seuil
    plus haut. La lecture courante — « ça bouge, c'est le moment » — a le
    signe exact du contraire.
    """
    alpha = n * HAWKES_BETA
    lam_bar = intensite_moyenne(HAWKES_MU, n)
    lam = reponse_fermee(t_apres, HAWKES_MU, alpha, HAWKES_BETA)

    ratio = lam / lam_bar
    sigma = SIGMA * math.sqrt(ratio)
    o = outcome_scaled(STOP_PTS, RR * STOP_PTS, SESSION, sigma, HURST)
    tau = o.expected_time
    mu_star = GEOM.friction_points / tau * 60.0
    return ratio, math.sqrt(ratio), tau, mu_star


def table_excitation() -> Table:
    rows = []
    lo, hi = seuil.PLAUSIBLE_DRIFT_PER_HOUR
    for t in INSTANTS_APRES:
        ratio, s_rel, tau, mu_star = horloge_excitee(t)
        if mu_star <= lo:
            verdict = "payant sous toute dérive plausible"
        elif mu_star <= hi:
            verdict = "payant seulement au-delà de µ*"
        else:
            verdict = "hors du domaine plausible"
        rows.append([
            num(t, 0),
            num(ratio, 3),
            num(s_rel, 3),
            num(tau, 1),
            num(mu_star, 3),
            verdict,
        ])
    facteur = horloge_excitee(0.0)[3] / horloge_excitee(40.0)[3]
    return Table(
        key="emp_excitation",
        caption="Ce qu'une bouffée d'activité fait au seuil, et à rien d'autre",
        headers=["Minutes après un événement", "Intensité relative",
                 "Volatilité relative", "E[τ∧T] (min)", "µ* (pt/h)",
                 "Verdict"],
        rows=rows,
        note="Hypothèse déclarée, et la seule : chaque événement déplace le "
             "prix d'un pas de taille fixe, donc `σ ∝ √λ`. Le stop vaut "
             + num(STOP_PCT, 3) + " % et le rapport gain-risque "
             + num(RR, 0) + ". Le seuil est multiplié par "
             + num(facteur, 2) + " entre le calme et l'instant qui suit un "
             "événement, et le verdict change avec lui : ce qui était payant "
             "sous n'importe quelle dérive plausible ne l'est plus qu'au "
             "prix d'une dérive presque doublée. La direction, elle, ne bouge "
             "pas d'un millième — le processus est symétrique par "
             "construction. **L'excitation déplace l'horloge, jamais la "
             "boussole**, et elle la déplace dans le sens défavorable. "
             "Domaine de dérive plausible : "
             + num(lo, 1) + " à " + num(hi, 1) + " point par heure.",
    )


#: Fenêtre sur laquelle la direction est relevée après un événement. Dix
#: minutes : plus long que la mémoire du noyau, plus court que la séance.
FENETRE_DIRECTION = 10.0


@lru_cache(maxsize=2)
def direction_apres(seed: int = SEED + 3) -> tuple[float, float, int]:
    """La part de hausses dans les dix minutes qui suivent un événement.

    Chaque événement porte une marque `±1` tirée à pile ou face, indépendante
    de tout le reste — c'est l'hypothèse nulle de direction, et elle est
    déclarée, pas ajustée. On relève ensuite le signe du déplacement cumulé
    sur la fenêtre qui suit chaque événement.

    Le résultat est un demi, à l'erreur d'échantillonnage près, et il le
    restera quel que soit le ratio de branchement : **l'auto-excitation est une
    propriété du temps, pas du signe**. Le mesurer plutôt que l'affirmer est ce
    qui distingue une loi nulle d'une opinion.
    """
    inst = hawkes()
    rng = Rng(seed)
    marques = [1.0 if rng.uniform() < 0.5 else -1.0 for _ in inst]
    n = len(inst)
    hausses = 0
    total = 0
    j0 = 0
    for i, t in enumerate(inst):
        if t + FENETRE_DIRECTION > inst[-1]:
            break
        cumul = 0.0
        j = max(j0, i + 1)
        while j < n and inst[j] < t + FENETRE_DIRECTION:
            cumul += marques[j]
            j += 1
        if cumul == 0.0:
            continue
        total += 1
        if cumul > 0.0:
            hausses += 1
    part = hausses / total if total else 0.5
    sd = math.sqrt(0.25 / total) if total else 0.0
    return part, sd, total


def evenements_entre(t0: float, t1: float) -> list[float]:
    """Les instants du processus dans une fenêtre, pour la planche."""
    return [t for t in hawkes() if t0 <= t < t1]


def chemin_intensite(t0: float, t1: float, pas: float = 0.25,
                     instants: tuple[float, ...] | None = None,
                     mu: float = HAWKES_MU, alpha: float = HAWKES_ALPHA,
                     beta: float = HAWKES_BETA) -> list[tuple[float, float]]:
    """L'intensité conditionnelle `λ(t) = µ + Σ α·e^{−β(t−tᵢ)}`, échantillonnée.

    C'est la quantité que le processus *est* : elle n'est pas estimée, elle
    est connue, puisque c'est elle qui a produit les instants. La tracer à
    côté d'un Poisson de même taux montre en une seconde ce qu'aucune
    statistique de comptage ne dit aussi vite.
    """
    src = hawkes() if instants is None else instants
    passe = [t for t in src if t < t1]
    out = []
    t = t0
    while t <= t1:
        acc = mu
        for s in reversed(passe):
            if s >= t:
                continue
            d = t - s
            if d > 40.0:
                break
            acc += alpha * math.exp(-beta * d)
        out.append((t, acc))
        t += pas
    return out


def fenetre_temoin(largeur: float = 60.0,
                   instants: tuple[float, ...] | None = None) -> float:
    """L'instant d'ouverture de la fenêtre la plus chargée du processus.

    Choisie par une règle **calculée** et non à la main : c'est la fenêtre de
    `largeur` minutes qui porte le plus d'événements. Une planche qui montre
    un amas doit montrer l'amas que la mesure désigne, sinon elle illustre le
    goût de son auteur.
    """
    inst = hawkes() if instants is None else instants
    meilleur = (0.0, 0)
    debut = 0.0
    while debut + largeur < T_HAWKES:
        n = sum(1 for t in inst if debut <= t < debut + largeur)
        if n > meilleur[1]:
            meilleur = (debut, n)
        debut += largeur / 2.0
    return meilleur[0]


@lru_cache(maxsize=4)
def poisson_temoin(taux: float, horizon: float,
                   seed: int = SEED + 8) -> tuple[float, ...]:
    """Un Poisson homogène de même taux — le témoin de la planche.

    Sans lui, l'œil accepte n'importe quelle irrégularité comme un amas : le
    hasard fait des grappes, et c'est précisément ce que la loi nulle doit
    montrer avant qu'on ne parle d'auto-excitation.
    """
    rng = Rng(seed)
    t = 0.0
    out: list[float] = []
    while True:
        t -= math.log(max(rng.uniform(), 1e-300)) / taux
        if t >= horizon:
            return tuple(out)
        out.append(t)


# ---------------------------------------------------------------------------
# IV. Les valeurs extrêmes — l'heure du haut, et ce qui vit au-delà du stop
# ---------------------------------------------------------------------------

N_SEANCES_ARC = 20000
N_DECILES = 10


@lru_cache(maxsize=4)
def argmax_seances(n: int = N_SEANCES_ARC,
                   seed: int = SEED + 4) -> tuple[float, ...]:
    """L'instant du plus haut de la séance, en fraction de séance.

    Aucune dérive, aucune heure privilégiée, aucun profil de volume : un pas
    gaussien par minute et rien d'autre. Ce qui sort n'est donc **pas** une
    propriété du marché.
    """
    rng = Rng(seed)
    out = []
    m = int(SESSION)
    for _ in range(n):
        prix = 0.0
        haut = -math.inf
        arg = 1
        for i in range(1, m + 1):
            prix += SIGMA * rng.gauss()
            if prix > haut:
                haut = prix
                arg = i
        # Le maximum se cherche sur les minutes cotées, jamais sur l'instant
        # d'ouverture : l'y inclure chargerait le premier dixième d'une masse
        # qui n'appartient à aucun des deux bords, et briserait une symétrie
        # que la loi possède exactement.
        out.append((arg - 0.5) / m)
    return tuple(out)


def arc_sinus(t: float) -> float:
    """`F(t) = (2/π)·arcsin(√t)` — la loi de l'arc sinus, forme fermée.

    C'est la loi de l'instant où une marche sans dérive atteint son maximum
    sur un intervalle. Sa densité est en U : elle diverge aux deux bords et
    creuse au milieu. Le fait est de 1939 et il n'a jamais eu besoin d'un
    marché pour être vrai.
    """
    t = min(max(t, 0.0), 1.0)
    return 2.0 / math.pi * math.asin(math.sqrt(t))


#: Une heure sur une séance de 390 minutes.
PART_HEURE = 60.0 / SESSION


def table_arcsin() -> Table:
    args = argmax_seances()
    n = len(args)
    rows = []
    for i in range(N_DECILES):
        a, b = i / N_DECILES, (i + 1) / N_DECILES
        compte = sum(1 for t in args if a <= t < b)
        mesure = compte / n
        loi = arc_sinus(b) - arc_sinus(a)
        rows.append([
            num(100 * a, 0) + " à " + num(100 * b, 0) + " %",
            num(100 * mesure, 2),
            num(100 * loi, 2),
            num(100 / N_DECILES, 2),
            num(loi * N_DECILES, 2),
        ])
    return Table(
        key="emp_arcsin",
        caption="À quelle heure le haut du jour se pose, sans aucun marché",
        headers=["Moment de la séance", "Fréquence mesurée",
                 "Loi de l'arc sinus", "Loi uniforme",
                 "Rapport à l'uniforme"],
        rows=rows,
        note=num(N_SEANCES_ARC, 0) + " séances de " + num(SESSION, 0)
             + " minutes, sans dérive, sans profil de volume, sans heure "
             "privilégiée. La densité est en **U** : le premier et le dernier "
             "dixième portent chacun "
             + num(100 * (arc_sinus(0.1)), 1) + " % des sommets là où "
             "l'uniforme en prévoit dix. Le premier ou le dernier quart "
             "d'heure de séance en portent "
             + num(100 * 2.0 * arc_sinus(15.0 / SESSION), 1)
             + " % à eux deux. Une affirmation du type « le haut du jour se "
             "fait à l'ouverture ou en clôture » est donc **vraie et sans "
             "contenu** : elle décrit la loi de l'arc sinus, pas le marché.",
    )


#: Taille de l'échantillon d'incréments pour les queues.
N_EVT = 60000

#: Fraction de l'échantillon retenue comme dépassements pour la Pareto.
PART_SEUIL = 0.02

#: Grille de `k/n` du tracé de Hill. Toutes ces valeurs sont défendables, et
#: c'est le problème.
GRILLE_HILL: tuple[float, ...] = (0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20)

#: Les lois retenues pour les queues, prises telles quelles à la partie XIV.
CLES_QUEUES: tuple[str, ...] = ("gauss", "student5", "student3", "merton")

#: Indice de queue vrai, quand il est connu. `None` quand la loi n'a pas de
#: queue de Pareto — et c'est justement le cas que l'estimateur trahit.
XI_VRAI: dict[str, float | None] = {
    "gauss": 0.0, "student5": 0.2, "student3": 1.0 / 3.0, "merton": 0.0,
}


@lru_cache(maxsize=8)
def incrementales(cle: str, n: int = N_EVT,
                  seed: int = SEED + 5) -> tuple[float, ...]:
    """`n` incréments d'une minute sous la loi demandée, variance un."""
    from . import robustesse

    loi = next(x for x in robustesse.lois() if x.cle == cle)
    rng = Rng(seed + sum(ord(c) for c in cle))
    out: list[float] = []
    etat: dict = {}
    for i in range(n):
        if i % int(SESSION) == 0:
            etat = {}
        out.append(loi.fn(rng, etat))
    return tuple(out)


def table_evt() -> Table:
    from . import robustesse

    noms = {x.cle: x.nom for x in robustesse.lois()}
    stop_sigma = STOP_PTS / SIGMA
    rows = []
    ref = None
    ecarts: list[float] = []
    p_stop_ref = {}
    for cle in CLES_QUEUES:
        ech = [abs(x) for x in incrementales(cle)]
        ech_tri = sorted(ech)
        n = len(ech_tri)
        u = ech_tri[int((1.0 - PART_SEUIL) * n)]
        fit = stress.fit_gpd(ech, u)
        pareto = stress.var_evt(fit, 0.999)
        empirique = ech_tri[int(0.999 * n)]
        if ref is None:
            ref = empirique
        ecarts.append(abs(pareto - empirique) / empirique)
        if abs(fit.shape) > 1e-9:
            reste = 1.0 + fit.shape * (stop_sigma - u) / fit.scale
            p_stop_ref[cle] = fit.exceedance_rate * reste ** (-1.0 / fit.shape)
        else:
            p_stop_ref[cle] = fit.exceedance_rate * math.exp(
                -(stop_sigma - u) / fit.scale)
        vrai = XI_VRAI[cle]
        rows.append([
            noms[cle],
            num(fit.shape, 3),
            "—" if vrai is None else num(vrai, 3),
            num(pareto, 2),
            num(empirique, 2),
            num(100 * (pareto - empirique) / empirique, 1, signed=True),
            num(empirique / ref, 2),
        ])
    pire = max(ecarts)
    une_sur = {c: 1.0 / max(v, 1e-300) for c, v in p_stop_ref.items()}
    return Table(
        key="emp_evt",
        caption="Ce qui vit au-delà du stop, loi par loi",
        headers=["Loi d'incrément", "ξ estimé", "ξ vrai",
                 "VaR 99,9 % par la Pareto (σ)", "VaR 99,9 % empirique (σ)",
                 "Écart", "Rapport à la gaussienne"],
        rows=rows,
        note="Pareto généralisée ajustée par la méthode des moments sur les "
             + num(100 * PART_SEUIL, 0) + " % de dépassements les plus grands "
             "de " + num(N_EVT, 0) + " incréments d'une minute à variance un — "
             "les lois sont celles de la partie XIV, reprises sans retouche. "
             "La cinquième colonne est le quantile empirique, encore bien "
             "estimé à ce niveau ; la sixième dit donc ce que l'extrapolation "
             "coûte **là où elle est encore vérifiable**, et elle atteint "
             "déjà " + num(100 * pire, 0) + " %. Plus loin, elle ne se "
             "vérifie plus du tout : prolongée jusqu'au stop de travail, à "
             + num(stop_sigma, 1) + " écarts-types d'une minute, elle annonce "
             "une minute sur " + num(une_sur["gauss"], 0) + " pour la "
             "gaussienne et une sur " + num(une_sur["student3"], 0)
             + " pour la Student à trois degrés — un rapport qui se compte en "
             "millions, et qui ne doit se lire que comme un ordre de "
             "grandeur, la sixième colonne disant pourquoi. **La forme de la "
             "queue ne change pas l'espérance** — la partie XIV l'a montré — "
             "elle change ce que le stop ne protège pas.",
    )


def table_hill() -> Table:
    from . import robustesse

    noms = {x.cle: x.court or x.nom for x in robustesse.lois()}
    rows = []
    plages: dict[str, list[float]] = {c: [] for c in CLES_QUEUES}
    for frac in GRILLE_HILL:
        ligne = [num(100 * frac, 1)]
        for cle in CLES_QUEUES:
            ech = [abs(x) for x in incrementales(cle)]
            k = max(2, int(frac * len(ech)))
            xi = stress.hill_estimator(ech, k)
            plages[cle].append(xi)
            ligne.append(num(xi, 3))
        rows.append(ligne)
    ligne_vrai = ["vrai"] + ["—" if XI_VRAI[c] is None else num(XI_VRAI[c], 3)
                             for c in CLES_QUEUES]
    rows.append(ligne_vrai)
    ecarts = {c: max(plages[c]) - min(plages[c]) for c in CLES_QUEUES}
    return Table(
        key="emp_hill",
        caption="Le tracé de Hill, ou le réglage qui décide de la queue",
        headers=["k/n (%)"] + [noms[c] for c in CLES_QUEUES],
        rows=rows,
        note="Estimateur de Hill sur les `k` plus grandes valeurs absolues de "
             + num(N_EVT, 0) + " incréments. Toutes les fractions du tableau "
             "sont défendables et aucune n'est canonique. L'estimation "
             "parcourt " + num(ecarts["student3"], 2) + " d'amplitude sur la "
             "Student à trois degrés, dont le vrai indice vaut "
             + num(1.0 / 3.0, 3) + ", et " + num(ecarts["gauss"], 2)
             + " sur la gaussienne, dont le vrai indice est **nul** — "
             "l'estimateur y rend pourtant une queue lourde à toute fraction "
             "retenue. C'est le piège de la taille de grappe du footprint et "
             "de la hauteur de rangée du profil de marché, sous une troisième "
             "forme : *un réglage non observable décide de ce que la mesure "
             "déclare rare.*",
        rules_after=[len(GRILLE_HILL) - 1],
    )


# ---------------------------------------------------------------------------
# V. La théorie de la détection — la sensibilité et le critère
# ---------------------------------------------------------------------------

#: Occasions examinées dans l'année. Quatre par séance : l'opérateur regarde
#: quatre configurations, il n'en prend pas quatre.
OCCASIONS_AN = 4.0 * SESSIONS_PAR_AN

#: La sensibilité de référence. Elle est **déclarée**, et généreuse : `d′`
#: vaut ici trois dixièmes d'écart-type, soit une aire sous la courbe ROC de
#: cinquante-huit pour cent. Rien dans le document ne prétend qu'un opérateur
#: l'atteint ; la table suivante balaie tout le domaine, zéro compris.
D_REF = 0.30

#: Les critères balayés, en écarts-types. Un critère négatif est un opérateur
#: qui prend tout, un critère élevé un opérateur qui attend.
CRITERES: tuple[float, ...] = (-0.5, 0.0, 0.4, 0.8, 1.6)

#: Grille de sensibilité de la seconde table, zéro compris.
D_GRID: tuple[float, ...] = (0.0, 0.05, 0.10, 0.20, 0.30, 0.50, 0.80)


def taux_touche(d: float, critere: float) -> float:
    """`H = Φ(d′/2 − c)` — dire oui quand la cible tombe d'abord."""
    return norm_cdf(d / 2.0 - critere)


def taux_fausse(d: float, critere: float) -> float:
    """`F = Φ(−d′/2 − c)` — dire oui quand c'est le stop qui tombe d'abord."""
    return norm_cdf(-d / 2.0 - critere)


def precision(d: float, critere: float, q: float = BASE_RATE) -> float:
    """`P(la cible tombe d'abord | l'opérateur a pris)` — le taux affiché.

    C'est la seule quantité qu'un relevé de trades donne, et c'est un
    mélange. Elle dépend de la sensibilité `d′`, qui vient du marché, du
    critère, qui vient de l'opérateur, et de la fréquence de base `q`, qui
    vient de la géométrie — trois choses que le taux de réussite confond.
    """
    h, f = taux_touche(d, critere), taux_fausse(d, critere)
    den = q * h + (1.0 - q) * f
    return q * h / den if den > 0 else q


def frequence(d: float, critere: float, q: float = BASE_RATE) -> float:
    """La part des occasions sur lesquelles l'opérateur agit."""
    return q * taux_touche(d, critere) + (1.0 - q) * taux_fausse(d, critere)


def esperance_r(p: float) -> float:
    """`E[R] = p·RR − (1 − p) − c/a`, au rapport et à la friction déclarés."""
    return p * RR - (1.0 - p) - FRICTION_RATIO


def esperance_an(d: float, critere: float,
                 occasions: float = OCCASIONS_AN) -> float:
    """Le produit qui décide : combien de fois, multiplié par combien."""
    return occasions * frequence(d, critere) * esperance_r(precision(d, critere))


def aire_roc(d: float) -> float:
    """`Φ(d′/√2)` — l'aire sous la courbe ROC, invariante au critère."""
    return norm_cdf(d / math.sqrt(2.0))


def critere_optimal(d: float) -> tuple[float, float]:
    """Le critère qui maximise le gain annuel, et ce gain.

    Il est **calculé**, jamais choisi, et son existence est le seul argument
    solide en faveur de la sélectivité : au-delà d'un certain point, resserrer
    coûte plus d'occasions qu'il n'apporte de qualité. À sensibilité nulle
    l'optimum part à l'infini, ce qui est la bonne réponse — ne rien faire.
    """
    meilleur, arg = -math.inf, 0.0
    x = -1.5
    while x <= 4.0001:
        v = esperance_an(d, x)
        if v > meilleur:
            meilleur, arg = v, x
        x += 0.01
    return arg, meilleur


def table_critere() -> Table:
    rows = []
    for c in CRITERES:
        p = precision(D_REF, c)
        rows.append([
            num(c, 2, signed=True),
            num(100 * p, 1),
            num(100 * frequence(D_REF, c), 1),
            num(OCCASIONS_AN * frequence(D_REF, c), 0),
            num(esperance_r(p), 3, signed=True),
            num(esperance_an(D_REF, c), 1, signed=True),
        ])
    arg, gain = critere_optimal(D_REF)
    ecart = (100 * precision(D_REF, CRITERES[-1])
             - 100 * precision(D_REF, CRITERES[0]))
    return Table(
        key="emp_critere",
        caption="Cinq opérateurs, une seule sensibilité",
        headers=["Critère (σ)", "Taux de réussite affiché",
                 "Fréquence d'action", "Décisions par an",
                 "E[R] par décision", "E[R] par an"],
        rows=rows,
        note="Les cinq lignes ont **exactement la même sensibilité** `d′ = "
             + num(D_REF, 2) + "`, donc la même aire sous la courbe ROC ("
             + num(100 * aire_roc(D_REF), 1) + " %) et la même erreur de "
             "Bayes (" + num(100 * bayes_error(D_REF), 1) + " %). Seul le "
             "critère change. Le taux de réussite affiché parcourt pourtant "
             + num(ecart, 1) + " points, et il n'apprend donc **rien** sur "
             "l'opérateur qu'on ne sache déjà de sa géométrie : le taux "
             "d'équilibre est " + num(100 * BREAK_EVEN_P, 1) + " % au rapport "
             + num(RR, 0) + " pour un. Le gain annuel, lui, a un maximum "
             "intérieur — " + num(gain, 1) + " R au critère "
             + num(arg, 2, signed=True) + " — et c'est la seule justification "
             "chiffrable de la sélectivité. La grammaire du setup mesurait ce fait "
             "sur douze setups ; il se lit ici en une ligne d'arithmétique.",
    )


def decisions_pour_dprime(d: float, q: float = BASE_RATE) -> float:
    """Décisions requises pour établir `d′` **au taux de base de la géométrie**.

    La formule de manuel suppose deux groupes de même taille. Ici ils ne le
    sont pas : la cible tombe d'abord une fois sur `1 + RR`, donc le groupe
    qui porte l'information est le plus petit. La variance de l'estimateur
    devient `(1/φ(0)²)·¼·(1/n₁ + 1/n₂)`, et l'effectif requis suit ::

        n = ((z_{α/2} + z_β)/d′)² · (¼/φ(0)²) · (1/q + 1/(1−q))

    Le facteur `(1/q + 1/(1−q))` vaut son minimum, quatre, à `q = ½`, et
    croît de part et d'autre. **Un rapport gain-risque déséquilibré coûte donc
    des décisions avant même de coûter de l'espérance**, et c'est un coût que
    la formule équilibrée ne voit pas.
    """
    if d <= 0.0:
        return math.inf
    phi0 = 1.0 / math.sqrt(2.0 * math.pi)
    facteur = 0.25 / (phi0 * phi0) * (1.0 / q + 1.0 / (1.0 - q))
    return ((Z_ALPHA + Z_BETA) / d) ** 2 * facteur


def table_sensibilite() -> Table:
    rows = []
    for d in D_GRID:
        arg, gain = critere_optimal(d)
        equil = observations_to_separate(d, ALPHA, PUISSANCE) if d > 0 else math.inf
        reel = decisions_pour_dprime(d)
        rows.append([
            num(d, 2),
            num(100 * aire_roc(d), 1),
            num(100 * bayes_error(d), 1),
            num(arg, 2, signed=True),
            num(100 * precision(d, arg), 1),
            num(gain, 1, signed=True),
            "∞" if equil == math.inf else num(equil, 0),
            "∞" if reel == math.inf else num(reel, 0),
            "∞" if reel == math.inf else num(reel / (2.0 * SESSIONS_PAR_AN), 2),
        ])
    return Table(
        key="emp_sensibilite",
        caption="Ce qu'il faut de sensibilité, et ce qu'il faut pour l'établir",
        headers=["d′", "Aire sous ROC", "Erreur de Bayes",
                 "Critère optimal", "Taux affiché à l'optimum", "E[R] par an",
                 "Décisions, protocole équilibré",
                 "Décisions, au taux de base réel",
                 "Années à deux par séance"],
        rows=rows,
        note="La première ligne est la loi nulle et elle se lit seule : à "
             "sensibilité nulle, le critère optimal part vers l'infini et le "
             "meilleur gain possible est **de ne rien faire**, la friction "
             "étant le seul terme qui reste. Les trois dernières colonnes "
             "donnent le prix de la démonstration. La septième est la formule "
             "de manuel, qui suppose deux groupes égaux ; la huitième tient "
             "compte du taux de base que la géométrie impose — une fois sur "
             + num(1.0 + RR, 0) + " — et elle est "
             + num(decisions_pour_dprime(D_REF)
                   / observations_to_separate(D_REF, ALPHA, PUISSANCE), 2)
             + " fois plus grande. Un rapport gain-risque déséquilibré coûte "
             "des décisions avant de coûter de l'espérance. Un opérateur à "
             "`d′ = " + num(D_REF, 2) + "` a donc besoin de "
             + num(decisions_pour_dprime(D_REF), 0) + " décisions, soit "
             + num(decisions_pour_dprime(D_REF) / (2.0 * SESSIONS_PAR_AN), 1)
             + " ans, et son relevé en compte "
             + num(RELEVE_REEL, 0) + ".",
    )


#: Effectifs de relevé balayés pour la loi nulle de la sensibilité.
TAILLES_RELEVE: tuple[int, ...] = (30, 100, 252, 504, 1008, 5040)
N_TIRAGES_DPRIME = 4000


@lru_cache(maxsize=16)
def dprime_nul(n: int, tirages: int = N_TIRAGES_DPRIME,
               seed: int = SEED + 6) -> tuple[float, float, float]:
    """La loi de la sensibilité **apparente** quand il n'y en a aucune.

    L'opérateur n'a aucune information, mais il agit tout de même sur la
    moitié des occasions. On estime `d̂′ = Φ⁻¹(Ĥ) − Φ⁻¹(F̂)` sur son relevé,
    avec la correction usuelle `(x+½)/(n+1)` qui évite les infinis.

    Ce que la simulation chiffre est le seul chiffre qui manque à tous les
    relevés publiés : **la sensibilité que le hasard fabrique**.
    """
    rng = Rng(seed + n)
    q = BASE_RATE
    vals = []
    for _ in range(tirages):
        n_cible = sum(1 for _ in range(n) if rng.uniform() < q)
        n_stop = n - n_cible
        if n_cible < 1 or n_stop < 1:
            continue
        h = sum(1 for _ in range(n_cible) if rng.uniform() < 0.5)
        f = sum(1 for _ in range(n_stop) if rng.uniform() < 0.5)
        d = (_norm_ppf((h + 0.5) / (n_cible + 1.0))
             - _norm_ppf((f + 0.5) / (n_stop + 1.0)))
        vals.append(d)
    vals.sort()
    return (vals[len(vals) // 2],
            vals[int(0.95 * len(vals))],
            vals[int(0.99 * len(vals))])


def table_dprime_nul() -> Table:
    rows = []
    for n in TAILLES_RELEVE:
        med, q95, q99 = dprime_nul(n)
        rows.append([
            num(n, 0),
            num(n / (2.0 * SESSIONS_PAR_AN), 2),
            num(med, 3, signed=True),
            num(q95, 3),
            num(q99, 3),
            "le bruit suffit" if q95 >= D_REF else "le bruit ne suffit plus",
        ])
    return Table(
        key="emp_dprime_nul",
        caption="La sensibilité que le hasard fabrique",
        headers=["Décisions au relevé", "Années", "d̂′ médian",
                 "95e centile", "99e centile",
                 "Face à d′ = " + num(D_REF, 2)],
        rows=rows,
        note="Un opérateur sans aucune information, agissant sur la moitié "
             "des occasions, relevé sur `n` décisions. La sensibilité "
             "apparente est estimée comme en psychophysique, `d̂′ = Φ⁻¹(Ĥ) − "
             "Φ⁻¹(F̂)`, avec la correction `(x+½)/(n+1)`. Sur "
             + num(RELEVE_REEL, 0) + " décisions, le bruit seul produit une "
             "sensibilité apparente qui dépasse " + num(dprime_nul(30)[1], 2)
             + " une fois sur vingt — **au-dessus de la sensibilité qu'on "
             "espère d'un opérateur expérimenté**. Il ne faut pas y voir un "
             "défaut d'estimateur : c'est la même arithmétique que la "
             "colonne « décisions pour l'établir » de la table précédente, "
             "vue de l'autre bout.",
    )


# ---------------------------------------------------------------------------
# VI. Le spectre en grande dimension — combien de lectures peut-on suivre
# ---------------------------------------------------------------------------

#: Nombres de lectures suivies simultanément. Quinze est le compte du
#: catalogue de la partie III : ce n'est pas un chiffre rond, c'est le
#: dispositif réel.
LECTURES_GRID: tuple[int, ...] = (3, 6, 9, 12, 15)

#: Force de facteur de référence, déclarée. Un quart : un facteur qui explique
#: un vingtième de la variance commune, ce qui est déjà beaucoup.
S_REF = 0.25

N_TIRAGES_SPECTRE = 200


def table_spectre() -> Table:
    n = int(SESSIONS_PAR_AN)
    rows = []
    for k in LECTURES_GRID:
        gamma = k / n
        _, haut = spectrum.mp_edges(gamma)
        nul = spectrum.null_spectrum(k, n, N_TIRAGES_SPECTRE, SEED + 7)
        seuil_bbp = spectrum.bbp_threshold(gamma)
        besoin = spectrum.observations_for_spike(S_REF, k)
        rows.append([
            num(k, 0),
            num(gamma, 3),
            num(haut, 3),
            num(nul.lambda_max_q95, 3),
            num(seuil_bbp, 3),
            num(besoin, 0),
            num(besoin / SESSIONS_PAR_AN, 2),
            "vu en un an" if besoin <= n else "invisible en un an",
        ])
    return Table(
        key="emp_spectre",
        caption="Combien de lectures peut-on suivre avant que le bruit ne parle",
        headers=["Lectures suivies", "γ = k/n", "Bord λ₊",
                 "95e centile de λ_max simulé", "Seuil BBP √γ",
                 "Séances requises pour s = " + num(S_REF, 2), "Années",
                 "Verdict"],
        rows=rows,
        note="Une année de séances, `n = " + num(n, 0) + "`. Le bord de "
             "Marchenko-Pastur est la forme fermée ; la quatrième colonne est "
             "la même quantité simulée à `k` fini. Elle reste **au-dessous** "
             "du bord fermé et s'en approche à mesure que `k` grandit : à "
             "trois lectures le bord asymptotique surestime de "
             + num(100 * (spectrum.mp_edges(3 / n)[1]
                          / spectrum.null_spectrum(3, n, N_TIRAGES_SPECTRE,
                                                   SEED + 7).lambda_max_q95
                          - 1.0), 1) + " %, à quinze de "
             + num(100 * (spectrum.mp_edges(15 / n)[1]
                          / spectrum.null_spectrum(15, n, N_TIRAGES_SPECTRE,
                                                   SEED + 7).lambda_max_q95
                          - 1.0), 1) + " % seulement — la forme fermée est "
             "donc conservatrice, et elle l'est d'autant moins qu'on suit "
             "plus de lectures. Le "
             "seuil de Baik-Ben Arous-Péché dit qu'un facteur de force "
             "inférieure à `√γ` ne se voit **pas du tout** : sa valeur propre "
             "reste collée au bord, ce n'est pas une perte de puissance mais "
             "une disparition. La bonne nouvelle est la sixième colonne : "
             "suivre les quinze lectures du catalogue ne demande que "
             + num(spectrum.observations_for_spike(S_REF, 15)
                   / SESSIONS_PAR_AN, 2) + " an pour distinguer un facteur de "
             "force " + num(S_REF, 2) + ". Le spectre n'est pas ce qui limite "
             "l'opérateur.",
    )


# ---------------------------------------------------------------------------
# VII. Les surfaces — ce que deux axes montrent et qu'une colonne cache
# ---------------------------------------------------------------------------
#
# Les six reliefs de la partie suivent la règle du dépôt : le maximum est posé
# au **fond** de la projection isométrique, coin `(0, 0)`, faute de quoi le
# sommet tombe au premier plan et deux points de profondeur différente se
# comparent par leur ordonnée d'écran. Les grilles sont donc écrites dans
# l'ordre que cette règle impose, décroissant ou croissant selon l'axe.

SURF_SHARPE: tuple[float, ...] = (2.0, 1.6, 1.2, 0.8, 0.5, 0.3)
SURF_ANNEES: tuple[float, ...] = (20.0, 12.0, 7.0, 4.0, 2.0, 1.0)


def puissance(sharpe: float, annees: float) -> float:
    """`Φ(S·√T − z_{α/2})` — la puissance d'un test de Sharpe sur `T` ans.

    Rien d'autre n'y entre : ni l'instrument, ni le pas de temps, ni la loi
    des rendements. C'est la traduction en langue de finance du test de
    moyenne le plus banal, et c'est ce qui la rend utilisable comme borne.
    """
    return norm_cdf(sharpe * math.sqrt(max(annees, 0.0)) - Z_ALPHA)


def surface_puissance() -> list[list[float]]:
    return [[puissance(s, t) for t in SURF_ANNEES] for s in SURF_SHARPE]


SURF_DISTANCE: tuple[float, ...] = (1.0, 2.0, 4.0, 7.0, 11.0, 17.0)
SURF_MINUTES: tuple[float, ...] = (1.0, 3.0, 8.0, 20.0, 50.0, 120.0)


def surface_hasard() -> list[list[float]]:
    """Le risque instantané **rapporté à son propre maximum**, distance × durée.

    Le choix de la normalisation n'est pas cosmétique, et il a été fait après
    avoir regardé la planche. Le hasard absolu parcourt deux ordres de
    grandeur sur cette boîte : tracé tel quel, le relief se réduisait à une
    aiguille au coin des sommets proches, tout le reste écrasé au sol. La
    crête que la section annonce — le lieu `m = d²/u*²σ²` — n'y était pas
    visible, et la légende décrivait donc un fait que la figure ne montrait
    pas. C'est le défaut que le dépôt appelle « la légende écrite devant un
    cadre borné ».

    Rapporté à son maximum par distance, le relief montre exactement ce dont
    la section parle : une arête qui traverse le plan en diagonale, chaque
    distance ayant son instant de danger maximal, et cet instant reculant
    comme le carré de la distance. Les niveaux absolus, eux, sont dans la
    table.
    """
    return [[hasard_nul(d, m) / hasard_nul(d, pic_hasard(d))
             for m in SURF_MINUTES] for d in SURF_DISTANCE]


SURF_BRANCHEMENT: tuple[float, ...] = (0.85, 0.75, 0.65, 0.50, 0.35, 0.20)
SURF_APRES: tuple[float, ...] = (0.0, 2.0, 5.0, 10.0, 20.0, 40.0)


def surface_seuil() -> list[list[float]]:
    """`µ*` après un événement, sur ratio de branchement × temps écoulé."""
    return [[horloge_excitee(t, n)[3] for t in SURF_APRES]
            for n in SURF_BRANCHEMENT]


SURF_XI: tuple[float, ...] = (0.40, 0.30, 0.20, 0.10, 0.00)
SURF_CONFIANCE: tuple[float, ...] = (0.99999, 0.9999, 0.999, 0.99)

#: Le seuil de la Pareto de référence et son échelle, tenus fixes pour que le
#: relief ne montre que l'effet de l'indice de queue.
U_REF = 2.326
BETA_REF = 0.50
ZETA_REF = 0.01


def var_pareto(xi: float, confiance: float) -> float:
    """VaR d'une queue de Pareto généralisée, en écarts-types d'une minute."""
    ratio = (1.0 - confiance) / ZETA_REF
    if abs(xi) < 1e-9:
        return U_REF - BETA_REF * math.log(ratio)
    return U_REF + BETA_REF / xi * (ratio ** (-xi) - 1.0)


def surface_queue() -> list[list[float]]:
    """Le rapport de la VaR à celle d'une queue exponentielle, `ξ = 0`."""
    return [[var_pareto(x, c) / var_pareto(0.0, c) for c in SURF_CONFIANCE]
            for x in SURF_XI]


SURF_DPRIME: tuple[float, ...] = (0.80, 0.60, 0.45, 0.30, 0.15, 0.00)
SURF_CRITERE: tuple[float, ...] = (-0.4, 0.0, 0.3, 0.6, 1.0, 1.6)


def surface_detection() -> list[list[float]]:
    """L'espérance annuelle sur le plan de la sensibilité et du critère.

    La crête de ce relief est le critère optimal, et elle **se déplace** :
    plus la sensibilité est grande, plus le critère optimal est lâche. C'est
    l'inverse de ce que l'intuition dicte, et c'est mécanique — une bonne
    sensibilité rend rentables des occasions médiocres, qu'un critère serré
    jetterait.
    """
    return [[esperance_an(d, c) for c in SURF_CRITERE] for d in SURF_DPRIME]


SURF_FORCE: tuple[float, ...] = (1.60, 1.20, 0.85, 0.55, 0.30, 0.12)
SURF_GAMMA: tuple[float, ...] = (0.02, 0.05, 0.10, 0.18, 0.30, 0.50)


def surface_bbp() -> list[list[float]]:
    """Ce qu'un facteur **ajoute** au bord du bruit, force × dimension.

    La hauteur est `λ_observée − λ₊`, et non `λ_observée`. La différence
    décide de ce que la planche montre. Tracée en valeur propre brute, la
    surface est un versant lisse où la transition de Baik-Ben Arous-Péché ne
    se distingue pas : le bord du bruit lui-même varie avec `γ`, et sa
    variation masque exactement le plat qu'on cherche à voir.

    Rapportée au bord, la région sous le seuil devient **exactement le sol** —
    un plan à zéro, large et net — et la frontière `s = √γ` se lit comme
    l'arête qu'elle est. Ce n'est pas une atténuation sous le seuil, c'est une
    disparition, et il fallait que la figure le dise aussi clairement que la
    formule.
    """
    return [[spectrum.spiked_eigenvalue(s, g) - spectrum.mp_edges(g)[1]
             for g in SURF_GAMMA] for s in SURF_FORCE]


# ---------------------------------------------------------------------------
# VIII. Le transfert — quel terme chaque discipline déplace, et de combien
# ---------------------------------------------------------------------------

#: Un déplacement relatif d'au moins dix pour cent sur le terme touché : c'est
#: la règle, déclarée avant les mesures, qui décide du verdict de transfert.
SEUIL_TRANSFERT = 0.10


@dataclass(frozen=True)
class Transfert:
    """Une discipline, le terme qu'elle déplace, et de combien."""

    nom: str
    terme: str
    grandeur: str
    effet: float          # déplacement relatif du terme touché
    lecture: str
    sur_le_sens: bool

    @property
    def transfere(self) -> bool:
        return abs(self.effet) >= SEUIL_TRANSFERT


def transferts() -> tuple[Transfert, ...]:
    """Les cinq disciplines, chacune avec son effet **mesuré** plus haut.

    Aucun de ces nombres n'est écrit ici : ils sont relus des mesures des
    sections précédentes, de sorte qu'une correction en amont se propage
    jusqu'au verdict sans qu'on ait à y penser.
    """
    obs = observations()
    gardes = [o for o in obs if not o.censure]
    rmst_ignore = sum(min(o.duree, RESTE) for o in gardes) / len(gardes)
    biais_survie = (rmst_ignore - rmst_exact()) / rmst_exact()

    facteur_seuil = horloge_excitee(0.0)[3] / horloge_excitee(40.0)[3]

    from . import robustesse
    _ = robustesse
    ech_g = sorted(abs(x) for x in incrementales("gauss"))
    ech_s = sorted(abs(x) for x in incrementales("student3"))
    i999 = int(0.999 * len(ech_g))
    rapport_queue = ech_s[i999] / ech_g[i999]

    taux = [precision(D_REF, c) for c in CRITERES]
    amplitude = (max(taux) - min(taux)) / precision(D_REF, 0.0)

    besoin = spectrum.observations_for_spike(S_REF, max(LECTURES_GRID))
    marge_spectre = besoin / SESSIONS_PAR_AN - 1.0

    return (
        Transfert(
            "Analyse de survie", "E[τ∧T]",
            "durée moyenne d'un sommet, en écartant les censurés",
            biais_survie,
            "elle chiffre le temps, et corrige une erreur qui ne se voit pas",
            False),
        Transfert(
            "Processus auto-excitants", "E[τ∧T], donc µ*",
            "seuil de rentabilité juste après un événement",
            facteur_seuil - 1.0,
            "l'activité raccourcit le temps de marché, et lève le seuil",
            False),
        Transfert(
            "Valeurs extrêmes", "a",
            "VaR à 99,9 % d'une queue lourde, rapportée à la gaussienne",
            rapport_queue - 1.0,
            "elle dimensionne ce que le stop ne protège pas",
            False),
        Transfert(
            "Théorie de la détection", "µ",
            "amplitude du taux affiché à sensibilité constante",
            amplitude,
            "elle sépare la compétence du réglage, et c'est la seule",
            True),
        Transfert(
            "Spectre en grande dimension", "le nombre de lectures",
            "séances requises pour voir un facteur de force "
            + num(S_REF, 2) + " sur " + num(max(LECTURES_GRID), 0)
            + " lectures",
            marge_spectre,
            "elle ne contraint pas : une année suffit",
            False),
    )


def table_transfert() -> Table:
    rows = []
    for t in transferts():
        rows.append([
            t.nom,
            t.terme,
            t.grandeur,
            num(100 * t.effet, 1, signed=True),
            "oui" if t.transfere else "non",
            "oui" if t.sur_le_sens else "non",
        ])
    combien = sum(1 for t in transferts() if t.transfere)
    sens = sum(1 for t in transferts() if t.sur_le_sens)
    return Table(
        key="emp_transfert",
        caption="Ce que chaque discipline déplace dans E[R] = (µ·E[τ∧T] − c)/a",
        headers=["Discipline", "Terme touché", "Grandeur mesurée",
                 "Déplacement (%)", "Transfère", "Agit sur le sens"],
        rows=rows,
        note="Le verdict de l'avant-dernière colonne est **calculé**, jamais "
             "écrit : une discipline transfère si elle déplace son terme d'au "
             "moins " + num(100 * SEUIL_TRANSFERT, 0) + " %, règle posée "
             "avant les mesures. " + num(combien, 0) + " des cinq y "
             "parviennent. La dernière colonne est celle qui compte, et elle "
             "ne porte qu'un seul oui : **quatre disciplines déplacent "
             "l'horloge, le risque ou le budget de preuve, une seule touche "
             "au sens.** Les quatre premières sont pourtant les plus faciles "
             "à mesurer, et la cinquième la plus difficile — ce qui suffit à "
             "expliquer pourquoi tant de méthodes publiées portent sur le "
             "quand et si peu sur le quoi.",
        wrap_last=False,
        wrap_cols=[2],
    )


# ---------------------------------------------------------------------------
# Ce que le document consomme
# ---------------------------------------------------------------------------


def values() -> dict[str, str]:
    """Les scalaires de la partie, préfixés `e_`."""
    u_min = UNITES[0]
    u_releve = UNITES[-1]
    obs = observations()
    part_censuree = sum(1 for o in obs if o.censure) / len(obs)
    part, sd, n_dir = direction_apres()
    args = argmax_seances()
    bords = sum(1 for t in args if t < 0.1 or t >= 0.9) / len(args)
    opt_c, opt_v = critere_optimal(D_REF)
    taux = [precision(D_REF, c) for c in CRITERES]
    med30, q95_30 = dprime_nul(30)[:2]
    facteur = horloge_excitee(0.0)[3] / horloge_excitee(40.0)[3]

    return {
        "e_facteur": num(FACTEUR, 3),
        "e_horizon": num(HORIZON_ANS, 0),
        "e_sharpe_ref": num(SHARPE_REF, 0),
        "e_annees_sharpe": num(annees_pour(SHARPE_REF), 1),
        "e_dmin_minute": num(u_min.d_min, 4),
        "e_dmin_releve": num(u_releve.d_min, 3),
        "e_sharpe_invariant": num(u_min.sharpe_min, 2),
        "e_sharpe_releve": num(u_releve.sharpe_min, 2),
        "e_leviers_carriere": num(
            max(k for k in LEVIERS_GRID
                if annees_pour_avec(SHARPE_REF, 2.0 ** k) <= CARRIERE), 0),
        "e_cout_multiplicite": num(
            annees_pour_avec(SHARPE_REF, 2.0 ** 18) / annees_pour(SHARPE_REF),
            2),
        "e_carriere": num(CARRIERE, 0),
        "e_t0": num(T0, 0),
        "e_reste": num(RESTE, 0),
        "e_seances_survie": num(N_SEANCES_SURVIE, 0),
        "e_censure": num(100 * part_censuree, 1),
        "e_beta_continuite": num(BETA_CONTINUITE, 3),
        "e_decalage": num(BETA_CONTINUITE * SIGMA, 2),
        "e_mediane_exacte": num(mediane_exacte(), 0),
        "e_rmst_exact": num(rmst_exact(), 0),
        "e_pic_neuf": num(pic_hasard(9.0), 0),
        "e_coef_pic": num(coef_pic(), 2),
        "e_u_pic": num(_u_pic(), 3),
        "e_hawkes_n": num(HAWKES_N, 2),
        "e_hawkes_memoire": num(1.0 / HAWKES_BETA, 1),
        "e_hawkes_relaxation": num(1.0 / (HAWKES_BETA - HAWKES_ALPHA), 1),
        "e_fano_asymptote": num(1.0 / (1.0 - HAWKES_N) ** 2, 1),
        "e_saut_intensite": num(horloge_excitee(0.0)[0], 2),
        "e_facteur_seuil": num(facteur, 2),
        "e_direction": num(100 * part, 1),
        "e_direction_sd": num(100 * sd, 2),
        "e_direction_n": num(n_dir, 0),
        "e_arc_bord": num(100 * (arc_sinus(0.1)), 1),
        "e_arc_bords": num(100 * bords, 1),
        "e_arc_quart": num(100 * 2.0 * arc_sinus(15.0 / SESSION), 1),
        "e_evt_n": num(N_EVT, 0),
        "e_stop_sigma": num(STOP_PTS / SIGMA, 1),
        "e_d_ref": num(D_REF, 2),
        "e_auc_ref": num(100 * aire_roc(D_REF), 1),
        "e_bayes_ref": num(100 * bayes_error(D_REF), 1),
        "e_taux_bas": num(100 * min(taux), 1),
        "e_taux_haut": num(100 * max(taux), 1),
        "e_taux_amplitude": num(100 * (max(taux) - min(taux)), 1),
        "e_break_even_p": num(100 * BREAK_EVEN_P, 1),
        "e_critere_opt": num(opt_c, 2, signed=True),
        "e_gain_opt": num(opt_v, 1),
        "e_occasions_an": num(OCCASIONS_AN, 0),
        "e_decisions_ref": num(decisions_pour_dprime(D_REF), 0),
        "e_annees_ref": num(decisions_pour_dprime(D_REF)
                            / (2.0 * SESSIONS_PAR_AN), 1),
        "e_releve_reel": num(RELEVE_REEL, 0),
        "e_dprime_med30": num(med30, 3, signed=True),
        "e_dprime_q95_30": num(q95_30, 2),
        "e_dprime_rapport": num(q95_30 / D_REF, 1),
        "e_lectures": num(max(LECTURES_GRID), 0),
        "e_bbp_quinze": num(spectrum.bbp_threshold(15.0 / SESSIONS_PAR_AN), 3),
        "e_seances_spectre": num(
            spectrum.observations_for_spike(S_REF, max(LECTURES_GRID)), 0),
        "e_s_ref": num(S_REF, 2),
        "e_transferts": num(sum(1 for t in transferts() if t.transfere), 0),
        "e_seuil_transfert": num(100 * SEUIL_TRANSFERT, 0),
        "e_stop_pct": num(STOP_PCT, 3),
        "e_rr": num(RR, 0),
        "e_base_rate": num(100 * BASE_RATE, 1),
    }


def all_tables() -> dict[str, Table]:
    tables = [
        table_unites(), table_multiplicite(),
        table_hasard(), table_censure(), table_calibration(),
        table_hawkes(), table_omori(), table_excitation(),
        table_arcsin(), table_evt(), table_hill(),
        table_critere(), table_sensibilite(), table_dprime_nul(),
        table_spectre(), table_transfert(),
    ]
    return {t.key: t for t in tables}


def main() -> None:
    for t in all_tables().values():
        print(t.to_text())
        print()
    for k, v in values().items():
        print(f"{k:24s} {v}")


if __name__ == "__main__":
    main()
