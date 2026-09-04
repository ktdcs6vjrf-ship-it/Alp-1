"""Ce que chaque lecture vaut si l'on prend position, dans les deux sens.

Ce module ne mesure aucun motif nouveau. Il fait une seule chose et la fait
partout : **il convertit ce que les autres modules ont mesuré en probabilités
de spéculation**, pour qu'une figure ne puisse plus être regardée sans qu'on
sache ce qu'il en coûterait d'en tirer une position. C'est le passage de la
description à la décision, et il n'y a rien à inventer pour le faire — la
chaîne de mesure existe, il fallait la brancher sur les deux sens.

Trois quantités par lecture, et jamais moins.

I. Les trois issues, et la portée de la séance
-------------------------------------------------
Sous prix sans dérive, la probabilité d'atteindre l'objectif avant le stop
vaut `a/(a+b)` — le théorème d'arrêt optionnel, et c'est le résultat
structurant de ce document. **Mais cette identité suppose que la séance ne
borne rien**, et à cible lointaine elle borne tout. La probabilité honnête
est celle du problème *borné par la séance*, qui rend trois issues et non
deux : l'objectif, le stop, et la position encore ouverte au coup de cloche.

Le fait qui en sort décide de toute géométrie. À un rapport d'un pour vingt,
un stop de 0,150 % demande à la séance **7,3 écarts-types** de son propre
parcours. Une séance en parcourt un. La probabilité d'objectif n'y vaut donc
pas 4,76 % mais **zéro**, et le R:R qu'un opérateur croit déclarer n'existe
pas. `portee_de_seance` publie ce nombre, `rr_atteignable` publie le rapport
que la séance autorise réellement, et les deux ensemble expliquent pourquoi
le rapport déclaré est le paramètre le moins vérifié du dispositif.

II. Les deux sens, et leur symétrie exacte
---------------------------------------------
À dérive nulle, les deux sens rendent **le même nombre à la précision
machine** — c'est la même identité vue des deux côtés, et un test l'exige.
C'est aussi ce qui rend le reste lisible : tout écart entre les deux sens est,
par construction, la dérive et rien d'autre. Sous la dérive haute du domaine
plausible, cet écart se chiffre — 52,9 % contre 9,4 % à la géométrie de
lecture d'une heure quarante — et **il passe par un maximum**. C'est le seul
réglage que ce document recommande explicitement, et la section V le donne.

III. Le seuil, par deux routes qui ne s'accordent pas
--------------------------------------------------------
La dérive qui annule l'espérance se calcule de deux façons, et **elles
diffèrent d'un facteur deux à dix**. L'identité de Wald bornée par la séance
donne `µ* = c/E[τ∧T]`, le nombre que la partie X publie. Le problème à deux
barrières *non borné* donne une dérive bien plus petite, parce qu'il laisse au
prix un temps que la séance ne lui laisse pas. Le rapport des deux vaut 2,2 au
stop déclaré et 10,4 au stop élargi, et il croît exactement quand la séance se
met à border. `derive_de_wald` et `derive_non_bornee` publient les deux, et
`ecart_des_routes` le rapport : *la route non bornée est celle qu'on emploie
sans y penser, et c'est la plus optimiste des deux.*

IV. L'horizon qui sépare le plus les deux sens
------------------------------------------------
L'écart directionnel n'est ni croissant ni décroissant avec l'horizon : il
passe par un maximum, et le maximum est calculé. Sous cet horizon, la dérive
n'a pas le temps d'agir — l'écart tombe à 12,6 points de taux à cinq minutes.
Au-dessus, la séance tronque l'objectif et il retombe à 18,2 sur la séance
entière. Le maximum vaut **43,4 points de taux à cent deux minutes**, et le
fait qui le rend publiable est ailleurs : à cet horizon **l'objectif vaut
exactement un écart-type de séance**, 1,02 mesuré. Ce n'est pas un artefact de
balayage, c'est la seule échelle où la dérive dispose de toute la séance sans
que la séance lui reprenne l'objectif.

L'affirmation a une frontière et le module la nomme : au-delà de la séance,
la position n'est plus fermée au coup de cloche, la dérive agit plus longtemps
que la volatilité ne s'étale, et l'écart remonte sans limite. L'optimum est
celui d'un opérateur intrajournalier, et il cesse d'en être un dès qu'on lève
cette contrainte.

V. Ce que le module ne fait pas
---------------------------------
Il n'attribue aucune dérive à aucune lecture. L'avantage de chaque lecture
vient de `concepts`, de `setups` ou du module qui l'a mesuré, et **tous
rendent zéro** — c'est le résultat du document et non une hypothèse de
celui-ci. Ce que ce module ajoute est le prix de ce zéro, sens par sens, et
la dérive qu'il faudrait pour le renverser.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from . import barriers
from . import concepts as C
from . import horizon as H
from . import quant as q
from . import seuil
from .report import Table, num

#: Les trois géométries que le document compare, en pour cent du niveau.
#: Elles sont celles de la partie X : le stop déclaré du dispositif, un stop
#: intermédiaire, et le stop élargi que le diagnostic finit par désigner.
GEOMETRIES: tuple[float, ...] = (0.010, 0.050, 0.150)

#: Les dérives auxquelles tout est lu : zéro, puis les deux bornes du domaine
#: plausible de la partie X. Aucune n'est ajustée sur quoi que ce soit.
DERIVES: tuple[float, ...] = (0.0,) + seuil.PLAUSIBLE_DRIFT_PER_HOUR

#: Les deux sens. `+1` achète, `−1` vend.
SENS: tuple[int, ...] = (1, -1)

#: Le rapport objectif sur risque du dispositif déclaré.
RR = q.RR_REF

#: La séance, en minutes, et l'écart-type qu'elle parcourt.
SEANCE_MIN = q.SESSION_MIN
SIGMA_MIN = q.SIGMA_1MIN
ECART_SEANCE = SIGMA_MIN * math.sqrt(SEANCE_MIN)

FRICTION = seuil.COST_BASE.friction_points(seuil.ES)

#: Le plafond du domaine de dérive plausible, en points par heure.
PLAUSIBLE_HAUTE = seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]


def nom_du_sens(sens: int) -> str:
    return "hausse" if sens > 0 else "baisse"


# ---------------------------------------------------------------------------
# I. Les trois issues
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Issue:
    """Les trois issues d'une position, et ce qu'elle vaut."""

    stop: float               # a, en points
    objectif: float           # b, en points
    derive_par_heure: float
    sens: int
    p_objectif: float
    p_stop: float
    p_ouvert: float
    esperance_r: float

    @property
    def portee(self) -> float:
        """L'objectif, en écarts-types de séance."""
        return self.objectif / ECART_SEANCE

    @property
    def hors_de_portee(self) -> bool:
        """La séance interdit-elle en pratique d'atteindre l'objectif ?

        Le critère porte sur la **portée** et non sur la probabilité : un
        objectif au-delà de ce qu'une séance parcourt en écart-type n'est pas
        improbable, il est hors d'atteinte, et le dire en distance plutôt
        qu'en probabilité évite de choisir un seuil.
        """
        return self.portee > 1.0


@lru_cache(maxsize=4096)
def _issues(a: float, b: float, derive_min: float,
            horizon_min: float) -> tuple[float, float, float]:
    return H.absorption_probabilities(a, b, horizon_min, derive_min, SIGMA_MIN)


def lire(stop_pct: float, derive_par_heure: float = 0.0, sens: int = 1,
         reward_risk: float = RR,
         horizon_min: float = SEANCE_MIN) -> Issue:
    """Les trois issues d'une position, et son espérance en R.

    Le signe du sens entre dans la **dérive**, jamais dans la géométrie : une
    vente voit la même distance de stop et le même objectif, et une dérive de
    signe opposé. C'est ce qui rend la symétrie à dérive nulle exacte plutôt
    qu'approchée, et un test l'exige à la précision machine.

    L'espérance passe par l'identité de Wald, `E[R] = (µ·E[τ∧T] − c)/a`, avec
    `E[τ∧T]` pris à dérive nulle — c'est la convention de la partie X, et elle
    est légèrement conservatrice sous dérive favorable, le temps d'exposition
    se raccourcissant quand la dérive aide.
    """
    g = seuil.geometry(stop_pct, reward_risk=reward_risk)
    a, b = g.stop_points, reward_risk * g.stop_points
    mu = sens * derive_par_heure / 60.0
    p_obj, p_stop, p_ouvert = _issues(a, b, mu, horizon_min)
    esp = (sens * derive_par_heure / 60.0 * g.exposure_min
           - g.friction_points) / a
    return Issue(a, b, derive_par_heure, sens, p_obj, p_stop, p_ouvert, esp)


def portee_de_seance(stop_pct: float, reward_risk: float = RR) -> float:
    """L'objectif d'une géométrie, en écarts-types de séance.

    C'est le nombre qui décide si le rapport déclaré existe. Au-delà d'un
    écart-type environ, la séance se ferme avant que l'objectif soit atteint,
    et le rapport n'est plus qu'une intention.
    """
    g = seuil.geometry(stop_pct, reward_risk=reward_risk)
    return reward_risk * g.stop_points / ECART_SEANCE


def stop_de_portee_un(reward_risk: float = RR) -> float:
    """La largeur de stop dont l'objectif vaut exactement une séance.

    Forme fermée, et elle n'a rien de subtile : l'objectif vaut `RR·a` et la
    séance parcourt `σ√T`, donc `a = σ√T/RR` et le stop en pour cent suit du
    niveau de l'indice. C'est la frontière du négociable au rapport déclaré,
    et elle est **plus basse que le stop déclaré du dispositif** — ce qui est
    la seule bonne nouvelle de la partie.
    """
    a = ECART_SEANCE / reward_risk
    return 100.0 * a / q.INDEX_LEVEL


def rr_atteignable(stop_pct: float, seuil_p: float = 0.05,
                   haut: float = 60.0, n: int = 48) -> float:
    """Le plus grand rapport dont l'objectif garde la probabilité demandée.

    Bissection sur le rapport : la probabilité d'objectif est strictement
    décroissante en `b`, donc la racine est unique. Renvoie le rapport, pas
    la distance — c'est sous cette forme qu'un opérateur le déclare.
    """
    g = seuil.geometry(stop_pct)
    a = g.stop_points
    if _issues(a, haut * a, 0.0, SEANCE_MIN)[0] >= seuil_p:
        return haut
    lo, hi = 0.25, haut
    if _issues(a, lo * a, 0.0, SEANCE_MIN)[0] < seuil_p:
        return lo
    for _ in range(n):
        mid = 0.5 * (lo + hi)
        if _issues(a, mid * a, 0.0, SEANCE_MIN)[0] >= seuil_p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def ecart_directionnel(horizon_min: float,
                       derive_par_heure: float | None = None) -> float:
    """Ce que la dérive sépare les deux sens, en points de taux.

    À dérive nulle il vaut zéro exactement, dans les deux sens et à tout
    horizon. Sous une dérive déclarée il mesure la seule chose qu'une
    spéculation directionnelle achète : la différence entre parier dans le
    bon sens et parier dans l'autre.
    """
    d = (seuil.PLAUSIBLE_DRIFT_PER_HOUR[1] if derive_par_heure is None
         else derive_par_heure)
    a = SIGMA_MIN * math.sqrt(horizon_min)
    b = C.RR_LECTURE * a
    t = max(SEANCE_MIN, horizon_min)
    mu = d / 60.0
    return 100.0 * (_issues(a, b, mu, t)[0] - _issues(a, b, -mu, t)[0])


@lru_cache(maxsize=8)
def horizon_optimal(derive_par_heure: float | None = None,
                    haut: float = SEANCE_MIN, n: int = 780) -> float:
    """L'horizon où la dérive sépare le plus les deux sens, en minutes.

    C'est le seul réglage que ce document recommande explicitement, et il
    sort d'un compromis dont les deux côtés sont mesurables. Sous cet
    horizon, la dérive n'a pas le temps d'agir : l'écart entre les deux sens
    tombe à douze points de taux à cinq minutes. Au-dessus, la séance
    tronque : l'objectif sort de sa portée et l'écart retombe à dix-huit.

    Le maximum tombe là où **l'objectif vaut exactement un écart-type de
    séance**, et ce n'est pas une coïncidence de balayage : c'est la seule
    échelle où la dérive dispose de toute la séance sans que la séance lui
    reprenne l'objectif. Un test l'exige à quelques centièmes près.

    Le balayage s'arrête **à la séance**, et cette borne n'est pas
    cosmétique : au-delà, la position est tenue d'une séance sur l'autre, la
    dérive agit plus longtemps que la volatilité ne s'étale, et l'écart
    remonte sans limite. La table le montre sur une ligne exprès. Ce document
    parle d'un opérateur intrajournalier ; l'optimum est celui de sa
    contrainte, et il cesse d'en être un dès qu'on lève la contrainte.
    """
    best = (0.0, -math.inf)
    for i in range(1, n + 1):
        t0 = haut * i / n
        e = ecart_directionnel(t0, derive_par_heure)
        if e > best[1]:
            best = (t0, e)
    return best[0]


def portee_de_l_optimum(derive_par_heure: float | None = None) -> float:
    """L'objectif de l'horizon optimal, en écarts-types de séance."""
    t = horizon_optimal(derive_par_heure)
    return C.RR_LECTURE * SIGMA_MIN * math.sqrt(t) / ECART_SEANCE


# ---------------------------------------------------------------------------
# II. Le seuil, par deux routes
# ---------------------------------------------------------------------------


def derive_de_wald(stop_pct: float, reward_risk: float = RR) -> float:
    """`µ* = c/E[τ∧T]`, en points par heure — la route bornée par la séance."""
    return seuil.geometry(stop_pct, reward_risk=reward_risk).break_even_per_hour


def derive_non_bornee(stop_pct: float, reward_risk: float = RR) -> float:
    """La même dérive dans le problème à deux barrières **sans horizon**.

    C'est la route qu'on emploie sans y penser, parce qu'elle a une forme
    fermée et qu'elle ne demande pas de choisir un horizon. Elle suppose que
    le prix a tout le temps qu'il lui faut, ce qu'une séance ne donne pas.
    """
    g = seuil.geometry(stop_pct, reward_risk=reward_risk)
    a, b = g.stop_points, reward_risk * g.stop_points
    return barriers.required_drift(a, b, SIGMA_MIN, g.friction_points) * 60.0


def ecart_des_routes(stop_pct: float, reward_risk: float = RR) -> float:
    """Le rapport des deux seuils. Il croît quand la séance se met à border."""
    bas = derive_non_bornee(stop_pct, reward_risk)
    if bas <= 0.0:
        return math.inf
    return derive_de_wald(stop_pct, reward_risk) / bas


def dans_le_domaine(derive: float) -> bool:
    """La dérive requise tombe-t-elle dans le domaine plausible déclaré ?"""
    return derive <= seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]


def verdict(stop_pct: float, reward_risk: float = RR) -> str:
    """Le verdict d'une géométrie, calculé et jamais écrit.

    Deux conditions indépendantes, et le verdict nomme celle qui tranche : la
    dérive requise doit tomber dans le domaine plausible, et l'objectif doit
    rester dans la portée de la séance. Une géométrie peut échouer sur l'une,
    sur l'autre, ou sur les deux — et la géométrie déclarée échoue sur la
    première quand le stop élargi échoue sur la seconde.
    """
    payante = dans_le_domaine(derive_de_wald(stop_pct, reward_risk))
    portee = portee_de_seance(stop_pct, reward_risk) <= 1.0
    if payante and portee:
        return "négociable"
    if payante:
        return "payante, mais l'objectif est hors de portée de la séance"
    if portee:
        return "à portée, mais hors du domaine de dérive"
    return "ni à portée ni dans le domaine"


# ---------------------------------------------------------------------------
# III. Le bandeau d'une figure
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Hypothese:
    """Ce qu'une famille de figures autorise à spéculer, et sur quoi.

    `avantage` est la dérive **mesurée** que la lecture apporte, en points par
    heure. Elle vaut zéro partout, et ce n'est pas une convention : c'est le
    résultat des modules qui l'ont mesurée, et `source` nomme lequel. Le jour
    où une lecture en produirait une, elle se déclarerait ici et le bandeau la
    porterait sans qu'on touche à une seule figure.
    """

    horizon_min: float
    objet: str
    source: str
    avantage: float = 0.0

    @property
    def directionnelle(self) -> bool:
        return self.horizon_min > 0.0


#: L'horizon d'une lecture décide de sa géométrie — `a = σ√t` — donc de tout
#: le bandeau. Une famille sans objet directionnel porte `0.0` et se lit sur
#: la géométrie déclarée du dispositif.
HYPOTHESES: dict[str, Hypothese] = {
    "figcat": Hypothese(30.0, "une lecture du catalogue",
                        "concepts.reaction, appariée et symétrique"),
    "figsetup": Hypothese(60.0, "un setup à un niveau calculé",
                          "setups.poule, 49,4 % contre 50,1 %"),
    "figflux": Hypothese(5.0, "un déséquilibre du flux",
                         "footprint, loi binomiale exacte"),
    "figsortie": Hypothese(390.0, "un concept de sortie",
                           "sorties, douze règles sur chemins appariés"),
    "figdisc": Hypothese(390.0, "le dispositif entier",
                         "report10, la géométrie déclarée"),
    "figrobu": Hypothese(390.0, "le théorème sous six lois",
                         "robustesse, les six rendent −c/a"),
    "figon": Hypothese(930.0, "la session overnight",
                       "overnight, la loi de l'arc sinus"),
    "figemp": Hypothese(390.0, "une discipline empruntée",
                        "emprunts, quatre déplacent l'horloge"),
    "figfds": Hypothese(390.0, "une pratique de fonds",
                        "fonds, aucune ne touche la direction"),
    "figrev": Hypothese(390.0, "un résumé de performance",
                        "revue, aucune direction négociable"),
    "fignv": Hypothese(0.0, "un niveau d'options",
                       "niveaux, deux déplacent l'horloge"),
    "figgra": Hypothese(0.0, "une grandeur de delta",
                        "grandeurs, aucune ne donne un sens"),
    "figth": Hypothese(0.0, "le loyer de la convexité",
                       "theta, une seule dit qu'il n'y a pas de sens"),
    "figvg": Hypothese(0.0, "le prix de l'incertitude",
                       "vega, aucune ne donne un sens"),
    "figrh": Hypothese(0.0, "la sensibilité au taux",
                       "rho, aucune ne donne un sens"),
    "figva": Hypothese(0.0, "la dérivée croisée",
                       "vanna, aucune ne donne un sens"),
    "figch": Hypothese(0.0, "la saignée du delta",
                       "charm, aucune ne donne un sens"),
    "figvo": Hypothese(0.0, "la convexité en volatilité",
                       "volga, aucune ne donne un sens"),
    "figspec": Hypothese(390.0, "la feuille elle-même",
                         "speculation, les deux sens à trois dérives"),
}

#: La famille qui sert quand une figure n'est déclarée nulle part. Elle est
#: la géométrie déclarée du dispositif, et c'est le choix conservateur.
DEFAUT = Hypothese(0.0, "le dispositif déclaré", "seuil, la partie X")


def hypothese(cle_module: str) -> Hypothese:
    return HYPOTHESES.get(cle_module, DEFAUT)


#: Le nom lisible d'un groupe de familles, par la famille qui le mène. Le
#: regroupement lui-même est **calculé** — deux familles tombent ensemble si
#: et seulement si leur géométrie de lecture est la même — et ce dictionnaire
#: ne fait que nommer le groupe obtenu. Une planche qui alignerait dix-neuf
#: barres sans étiquette ne dirait rien à personne ; six lignes nommées, si.
NOMS_DE_GROUPE: dict[str, str] = {
    "fignv": "les huit parties d'options",
    "figflux": "le flux d'ordres",
    "figcat": "le catalogue des lectures",
    "figsetup": "la grammaire du setup",
    "figdisc": "le dispositif et ses épreuves",
    "figon": "la session overnight",
}


def familles_par_geometrie() -> tuple[tuple[str, int, "Bandeau"], ...]:
    """Les familles de figures, regroupées par la géométrie qu'elles lisent.

    Deux familles tombent dans le même groupe quand leur horizon de lecture
    est le même, donc quand leur bandeau porte les mêmes nombres. Le nom du
    groupe vient de `NOMS_DE_GROUPE`, et un test exige que chaque groupe
    obtenu en ait un — sans quoi une planche publierait une ligne anonyme.

    Renvoyé trié par distance de stop croissante.
    """
    groupes: dict[float, list[str]] = {}
    for cle in HYPOTHESES:
        groupes.setdefault(round(bandeau(cle).stop, 6), []).append(cle)
    sortie = []
    for a in sorted(groupes):
        cles = sorted(groupes[a])
        nom = next((NOMS_DE_GROUPE[c] for c in cles if c in NOMS_DE_GROUPE),
                   cles[0])
        sortie.append((nom, len(cles), bandeau(cles[0])))
    return tuple(sortie)


def ecart_d_un_stop(stop_pct: float,
                    derive_par_heure: float | None = None) -> float:
    """L'écart entre les deux sens, à la géométrie déclarée d'un stop.

    C'est la même grandeur que `ecart_directionnel`, prise sur une géométrie
    de dispositif — stop en pour cent et rapport déclaré — plutôt que sur une
    géométrie de lecture. Les deux se comparent, et la comparaison est le
    dernier fait de la partie.
    """
    d = (PLAUSIBLE_HAUTE if derive_par_heure is None else derive_par_heure)
    return 100.0 * (lire(stop_pct, d, 1).p_objectif
                    - lire(stop_pct, d, -1).p_objectif)


@dataclass(frozen=True)
class Bandeau:
    """Ce qu'une figure autorise à spéculer, dans les deux sens."""

    module: str
    objet: str
    source: str
    stop: float
    objectif: float
    p_hausse: tuple[float, ...]
    p_baisse: tuple[float, ...]
    esperance: tuple[float, ...]
    derive_requise: float
    portee: float

    @property
    def symetrique(self) -> bool:
        return abs(self.p_hausse[0] - self.p_baisse[0]) < 1e-12

    @property
    def verdict(self) -> str:
        if not dans_le_domaine(self.derive_requise):
            return "hors du domaine de dérive plausible"
        if self.portee > 1.0:
            return "objectif hors de la portée d'une séance"
        return "dans le domaine, à dérive déclarée"


@lru_cache(maxsize=64)
def bandeau(cle_module: str) -> Bandeau:
    """Le bandeau d'une famille de figures, entièrement calculé.

    Une figure dont la lecture a un horizon prend la géométrie de cet
    horizon — `a = σ√t`, objectif à `RR_LECTURE·a`, la convention du
    catalogue. Une figure sans objet directionnel prend la géométrie déclarée
    du dispositif. Dans les deux cas rien n'est écrit : le bandeau se recalcule
    à chaque construction, et une correction de module s'y propage.
    """
    h = hypothese(cle_module)
    if h.directionnelle:
        a = SIGMA_MIN * math.sqrt(h.horizon_min)
        b = C.RR_LECTURE * a
        t = max(SEANCE_MIN, h.horizon_min)
        exposition = H.expected_exit_time(a, b, t, SIGMA_MIN)
    else:
        g = seuil.geometry(GEOMETRIES[0])
        a, b, t = g.stop_points, RR * g.stop_points, SEANCE_MIN
        exposition = g.exposure_min

    hausse, baisse, esp = [], [], []
    for d in DERIVES:
        mu = (d + h.avantage) / 60.0
        hausse.append(_issues(a, b, mu, t)[0])
        baisse.append(_issues(a, b, -mu, t)[0])
        esp.append(((d + h.avantage) / 60.0 * exposition - FRICTION) / a)
    requise = FRICTION / exposition * 60.0
    return Bandeau(cle_module, h.objet, h.source, a, b, tuple(hausse),
                   tuple(baisse), tuple(esp), requise, b / ECART_SEANCE)


def module_d_une_figure(cle: str) -> str:
    """Le module d'où vient une figure, déduit du préfixe de sa clé.

    Les clés du dépôt commencent toutes par deux à quatre lettres qui nomment
    leur partie. La correspondance est déclarée plutôt que devinée, et un test
    exige qu'elle couvre toutes les figures du document.
    """
    for prefixe, module in _PREFIXES:
        if cle.startswith(prefixe):
            return module
    return ""


#: Le préfixe des clés de chaque module de figures. **L'ordre compte** : le
#: premier préfixe qui accroche gagne, donc les longs se testent avant les
#: courts. La dernière entrée est un `r` seul, qui ramasse les cinq clés de
#: `figrobu` — elles n'ont pas de préfixe commun plus long — et elle ne peut
#: venir qu'après `rev` et `rh`, qui l'auraient sinon perdue.
#:
#: Cette liste a été **relevée sur les clés réelles et non devinée**, et le
#: premier jet ne l'était pas : trente-sept figures sur deux cent quatorze
#: tombaient dans aucune famille, dont les treize du delta et les neuf du
#: flux. Aucune ne l'aurait signalé — le bandeau se serait simplement tu.
#: Un test lit désormais toutes les clés du gabarit et refuse la moindre
#: orpheline.
_PREFIXES: tuple[tuple[str, str], ...] = (
    ("couche_", "figdisc"), ("disc", "figdisc"),
    ("flow", "figflux"), ("gamma", "figflux"),
    ("sortie", "figsortie"), ("set", "figsetup"), ("cat", "figcat"),
    ("emp", "figemp"), ("fds", "figfds"),
    ("rev", "figrev"), ("rh", "figrh"),
    ("nv", "fignv"), ("gr", "figgra"), ("th", "figth"),
    ("vg", "figvg"), ("va", "figva"), ("vo", "figvo"),
    ("ch", "figch"), ("on", "figon"), ("spec", "figspec"),
    ("r", "figrobu"),
)


# ---------------------------------------------------------------------------
# IV. Les lectures et les setups, passés aux deux sens
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Ligne:
    """Une lecture du catalogue, lue comme une position."""

    cle: str
    nom: str
    horizon_min: float
    stop: float
    objectif: float
    p_nulle: float
    p_haute: float
    p_basse: float
    derive_requise: float
    portee: float

    @property
    def ecart(self) -> float:
        """Ce que la dérive haute sépare les deux sens, en points de taux."""
        return 100.0 * (self.p_haute - self.p_basse)


def ligne(cle: str) -> Ligne:
    """Une lecture du catalogue, convertie en position dans les deux sens."""
    lec = C._PAR_CLE[cle]
    a, b, c = C.geometrie(lec.horizon_min)
    t = max(SEANCE_MIN, lec.horizon_min)
    mu = seuil.PLAUSIBLE_DRIFT_PER_HOUR[1] / 60.0
    p0 = _issues(a, b, 0.0, t)[0]
    ph = _issues(a, b, mu, t)[0]
    pb = _issues(a, b, -mu, t)[0]
    return Ligne(cle, lec.nom, lec.horizon_min, a, b, p0, ph, pb,
                 C.exigence(cle).derive_requise, b / ECART_SEANCE)


def lignes() -> tuple[Ligne, ...]:
    """Les quinze lectures, dans l'ordre calculé du catalogue."""
    return tuple(ligne(l.cle) for l in C.ordre())


# ---------------------------------------------------------------------------
# V. Les tables
# ---------------------------------------------------------------------------


def _pc(v: float, nd: int = 2) -> str:
    return num(100.0 * v, nd) + " %"


def table_geometries() -> Table:
    rows = []
    for pct in GEOMETRIES:
        i = lire(pct)
        rows.append([
            num(pct, 3) + " %",
            num(i.stop, 2),
            num(i.objectif, 1),
            num(i.portee, 2),
            _pc(i.p_objectif),
            _pc(i.p_stop),
            _pc(i.p_ouvert),
            num(derive_de_wald(pct), 3),
        ])
    return Table(
        "spec_geometries",
        "Les trois issues d'une position, et la portée que la séance autorise",
        ["Stop", "a (pts)", "Objectif (pts)", "Objectif en écarts-types de "
         "séance", "P(objectif)", "P(stop)", "P(ouvert à la clôture)",
         "µ* (pts/h)"],
        rows,
        note="Tout y est à dérive nulle et vaut pour les deux sens à la "
             "précision machine. La colonne qui décide est la quatrième. "
             "L'identité `a/(a+b)` de la partie X — 4,76 % à un rapport d'un "
             "pour vingt — ne tient que tant que l'objectif reste dans la "
             "portée d'une séance : elle est exacte au stop déclaré, dont "
             "l'objectif vaut un demi écart-type, et elle tombe à zéro au "
             "stop élargi, dont l'objectif en demande sept. La probabilité "
             "d'objectif n'y est pas petite, elle est nulle, et la position "
             "se termine "
             + _pc(lire(GEOMETRIES[2]).p_ouvert, 1)
             + " du temps ouverte au coup de cloche. "
             "*Un rapport déclaré n'est réel que si la séance peut le "
             "parcourir.*")


def table_sens() -> Table:
    rows = []
    for pct in GEOMETRIES:
        for d in DERIVES:
            h = lire(pct, d, 1)
            b = lire(pct, d, -1)
            rows.append([
                num(pct, 3) + " %",
                num(d, 1),
                _pc(h.p_objectif),
                _pc(b.p_objectif),
                num(100.0 * (h.p_objectif - b.p_objectif), 2),
                num(h.esperance_r, 3),
                num(b.esperance_r, 3),
            ])
    return Table(
        "spec_sens",
        "Les deux sens, aux trois dérives et aux trois géométries",
        ["Stop", "Dérive (pts/h)", "P(objectif) à la hausse",
         "P(objectif) à la baisse", "Écart (points de taux)",
         "E[R] à la hausse", "E[R] à la baisse"],
        rows,
        rules_after=[2, 5],
        note="Les lignes à dérive nulle rendent le même nombre dans les deux "
             "colonnes, et c'est exact et non approché : la symétrie est "
             "celle de la loi, et un test l'exige à la précision machine. "
             "Tout écart entre les deux sens est donc, par construction, la "
             "dérive et rien d'autre. Ce que la table montre ensuite est que "
             "cet écart se paie en espérance et non en probabilité : sous la "
             "dérive haute il vaut "
             + num(100.0 * (lire(GEOMETRIES[0], DERIVES[-1], 1).p_objectif
                            - lire(GEOMETRIES[0], DERIVES[-1], -1).p_objectif),
                   1)
             + " point de taux au stop déclaré et "
             + num(100.0 * (lire(GEOMETRIES[1], DERIVES[-1], 1).p_objectif
                            - lire(GEOMETRIES[1], DERIVES[-1], -1).p_objectif),
                   1)
             + " au stop intermédiaire — deux nombres voisins — quand "
             "l'espérance, elle, passe de "
             + num(lire(GEOMETRIES[0], DERIVES[-1], 1).esperance_r, 2)
             + " à "
             + num(lire(GEOMETRIES[1], DERIVES[-1], 1).esperance_r, 2)
             + " R. *Une dérive ne change pas beaucoup la fréquence des "
             "gains ; elle change ce qu'ils rapportent, et c'est l'identité "
             "de Wald vue du côté de l'opérateur.*")


def table_portee() -> Table:
    rows = []
    for pct in seuil.SURFACE_STOP_PCT:
        g = seuil.geometry(pct)
        rows.append([
            num(pct, 3) + " %",
            num(g.stop_points, 2),
            num(portee_de_seance(pct), 2),
            num(rr_atteignable(pct, 0.10), 1),
            num(rr_atteignable(pct, 0.05), 1),
            num(rr_atteignable(pct, 0.01), 1),
            _pc(lire(pct).p_objectif),
        ])
    return Table(
        "spec_portee",
        "Le rapport que la séance autorise, et celui que le dispositif déclare",
        ["Stop", "a (pts)", "Objectif déclaré, en écarts-types de séance",
         "R:R à P ≥ 10 %", "R:R à P ≥ 5 %", "R:R à P ≥ 1 %",
         "P(objectif) au rapport déclaré"],
        rows,
        note="Les trois colonnes centrales donnent le plus grand rapport dont "
             "l'objectif garde la probabilité annoncée, séance comprise. "
             "Elles s'effondrent bien plus vite que le stop ne s'élargit, "
             "parce que l'objectif croît comme le stop quand la portée de la "
             "séance, elle, ne croît pas du tout. La dernière colonne dit ce "
             "que le rapport déclaré de un pour vingt devient sous cette "
             "contrainte. *Élargir le stop divise le seuil de rentabilité par "
             "cinquante-trois, et c'est le résultat de la partie X ; ce que "
             "cette table ajoute est que le même geste rend l'objectif "
             "inatteignable si on garde le rapport, donc que les deux leviers "
             "ne se règlent pas séparément.*")


def table_routes() -> Table:
    rows = []
    for pct in seuil.SURFACE_STOP_PCT:
        wald = derive_de_wald(pct)
        libre = derive_non_bornee(pct)
        rows.append([
            num(pct, 3) + " %",
            num(seuil.geometry(pct).exposure_min, 1),
            num(wald, 3),
            num(libre, 3),
            num(ecart_des_routes(pct), 2),
            "oui" if dans_le_domaine(wald) else "non",
            "oui" if dans_le_domaine(libre) else "non",
        ])
    return Table(
        "spec_routes",
        "La dérive d'équilibre par deux routes, et le facteur qui les sépare",
        ["Stop", "E[τ∧T] (min)", "µ* borné par la séance (pts/h)",
         "µ* non borné (pts/h)", "Rapport",
         "Dans le domaine, borné", "Dans le domaine, non borné"],
        rows,
        note="La route non bornée est celle qu'on emploie sans y penser : "
             "elle a une forme fermée et elle ne demande pas de choisir un "
             "horizon. Elle suppose que le prix a tout le temps qu'il lui "
             "faut. La route bornée est celle de la partie X, et c'est la "
             "seule qui décrive une séance. Les deux dernières colonnes "
             "disent que le verdict, lui, ne bascule sur aucune ligne de la "
             "grille : les deux routes excluent la géométrie déclarée et "
             "admettent les autres. Ce que le raccourci change est l'ampleur, "
             "et elle décide de ce qu'on est prêt à discuter. Au stop "
             "déclaré il place l'exigence à "
             + num(derive_non_bornee(GEOMETRIES[0]), 2) + " points par heure, "
             + num(100.0 * (derive_non_bornee(GEOMETRIES[0])
                            / seuil.PLAUSIBLE_DRIFT_PER_HOUR[1] - 1.0), 0)
             + " % au-dessus du plafond plausible — un dépassement dont on "
             "argumente. La route bornée la place à "
             + num(derive_de_wald(GEOMETRIES[0]), 2) + ", soit un facteur "
             + num(derive_de_wald(GEOMETRIES[0])
                   / seuil.PLAUSIBLE_DRIFT_PER_HOUR[1], 1)
             + " au-dessus, dont on n'argumente pas. *Le raccourci ne "
             "retourne pas le verdict ; il le rend discutable, ce qui suffit "
             "à faire vivre une géométrie que la mesure condamne.*")


def table_lectures() -> Table:
    rows = []
    for lg in lignes():
        rows.append([
            lg.nom,
            num(lg.horizon_min, 0),
            num(lg.stop, 2),
            num(lg.objectif, 2),
            num(lg.portee, 3),
            _pc(lg.p_nulle),
            _pc(lg.p_haute),
            _pc(lg.p_basse),
            num(lg.derive_requise, 2),
        ])
    return Table(
        "spec_lectures",
        "Les quinze lectures du catalogue, prises comme des positions",
        ["Lecture", "Horizon (min)", "a (pts)", "Objectif (pts)",
         "Portée (σ de séance)", "P à dérive nulle", "P à la dérive haute",
         "P à la dérive haute, sens inverse", "µ requis (pts/h)"],
        rows,
        wrap_cols=[0],
        note="La sixième colonne vaut "
             + _pc(1.0 / (1.0 + C.RR_LECTURE))
             + " — exactement `a/(a+b)` — sur les cinq premières lignes, et "
             "c'est le théorème : à rapport fixé, la probabilité d'objectif "
             "ne dépend ni du motif ni de son horizon. Puis elle décroche, et "
             "la colonne qui explique le décrochage est la cinquième. Tant "
             "que l'objectif tient dans la portée d'une séance, le théorème "
             "s'applique ; au-delà, la séance se ferme avant l'objectif et la "
             "probabilité tombe à "
             + _pc(lignes()[-1].p_nulle)
             + ", soit un facteur "
             + num((1.0 / (1.0 + C.RR_LECTURE)) / lignes()[-1].p_nulle, 1)
             + ". *Les lectures longues du catalogue ne sont pas moins "
             "fiables que les courtes : elles sont, à rapport égal, "
             "innégociables dans une séance.* Les deux colonnes suivantes "
             "donnent les deux sens sous la dérive haute, et la dernière est "
             "celle de la partie III, importée et non recopiée.")


def table_esperance() -> Table:
    rows = []
    for pct in GEOMETRIES:
        cible = FRICTION / seuil.geometry(pct).exposure_min * 60.0
        rows.append([
            num(pct, 3) + " %",
            num(lire(pct, 0.0, 1).esperance_r, 3),
            num(lire(pct, seuil.PLAUSIBLE_DRIFT_PER_HOUR[0], 1).esperance_r, 3),
            num(lire(pct, seuil.PLAUSIBLE_DRIFT_PER_HOUR[1], 1).esperance_r, 3),
            num(lire(pct, seuil.PLAUSIBLE_DRIFT_PER_HOUR[1], -1).esperance_r,
                3),
            num(cible, 3),
            verdict(pct),
        ])
    return Table(
        "spec_esperance",
        "Ce que chaque géométrie rend, par dérive et par sens",
        ["Stop", "E[R] à µ = 0", "E[R] à µ = 0,6", "E[R] à µ = 3,2",
         "E[R] à µ = 3,2, sens inverse", "µ d'équilibre (pts/h)", "Verdict"],
        rows,
        wrap_cols=[6],
        note="La première colonne vaut `−c/a` et ne dépend d'aucune "
             "géométrie de sortie : c'est le résultat structurant du "
             "document, et il se lit ici comme le prix d'entrée de toute "
             "spéculation. Les trois suivantes disent ce qu'une dérive "
             "déclarée en fait. La dernière colonne est un verdict calculé "
             "sur deux conditions indépendantes — la dérive requise dans le "
             "domaine plausible, et l'objectif dans la portée de la séance — "
             "et aucune des trois géométries ne les remplit toutes les deux. "
             "*Ce n'est pas que la stratégie soit mauvaise : c'est que les "
             "deux réglages qu'on croit indépendants sont liés par la "
             "séance.*")


def table_bandeaux() -> Table:
    rows = []
    for cle in sorted(HYPOTHESES):
        b = bandeau(cle)
        rows.append([
            cle,
            b.objet,
            num(b.stop, 2),
            _pc(b.p_hausse[0]),
            _pc(b.p_hausse[-1]),
            _pc(b.p_baisse[-1]),
            num(b.derive_requise, 2),
        ])
    return Table(
        "spec_bandeaux",
        "Le bandeau que chaque famille de figures porte, et d'où il vient",
        ["Famille", "Objet", "a (pts)", "P à dérive nulle",
         "P à la dérive haute", "P à la dérive haute, sens inverse",
         "µ requis (pts/h)"],
        rows,
        wrap_cols=[1],
        note="Chaque famille de figures du document porte désormais ce "
             "bandeau sous sa planche, recalculé à chaque construction. La "
             "quatrième colonne est la même partout, ce qui est le théorème ; "
             "les deux suivantes varient parce que l'horizon d'une lecture "
             "décide de sa géométrie. Ce que la table ne contient pas est une "
             "colonne d'avantage mesuré : elle vaudrait zéro sur toutes les "
             "lignes, et ce zéro n'est pas une convention de ce module mais "
             "le résultat de ceux qui l'ont mesuré, nommés en regard de "
             "chaque famille dans le code. *Le jour où une lecture en "
             "produirait un, il se déclarerait à un seul endroit et tous les "
             "bandeaux du document le porteraient.*")


def table_reste() -> Table:
    rows = []
    for pct in GEOMETRIES:
        i0 = lire(pct, 0.0, 1)
        rows.append([
            num(pct, 3) + " %",
            "hors de portée" if i0.hors_de_portee else "à portée",
            "hors du domaine" if not dans_le_domaine(derive_de_wald(pct))
            else "dans le domaine",
            num(rr_atteignable(pct, 0.05), 1),
            num(portee_de_seance(pct), 2),
        ])
    return Table(
        "spec_reste",
        "Ce qu'il reste à déclarer avant la première position",
        ["Stop", "L'objectif", "La dérive requise",
         "Le rapport que la séance autorise à 5 %", "Portée déclarée (σ)"],
        rows,
        note="Trois géométries, et aucune ne passe les deux conditions. Le "
             "stop déclaré échoue sur la dérive, qu'il faudrait porter à "
             "8,19 points par heure quand le domaine plausible s'arrête à "
             "3,2. Les deux stops élargis passent la dérive et échouent sur "
             "la portée : leur objectif demande à la séance deux et sept "
             "fois ce qu'elle parcourt. L'avant-dernière colonne dit ce qu'il "
             "faudrait déclarer à la place, et c'est le seul réglage que ce "
             "document recommande explicitement. *Un opérateur qui veut une "
             "position négociable n'a pas trois paramètres à choisir mais "
             "deux, et la séance fixe le troisième.*")


def table_optimum() -> Table:
    opt = horizon_optimal()
    rows = []
    for t0 in (5.0, 15.0, 30.0, 60.0, opt, 120.0, 240.0, 390.0, 780.0):
        a = SIGMA_MIN * math.sqrt(t0)
        b = C.RR_LECTURE * a
        t = max(SEANCE_MIN, t0)
        mu = DERIVES[-1] / 60.0
        rows.append([
            num(t0, 0) + (" ←" if abs(t0 - opt) < 1e-9 else ""),
            num(a, 2),
            num(b / ECART_SEANCE, 3),
            _pc(_issues(a, b, 0.0, t)[0]),
            _pc(_issues(a, b, mu, t)[0]),
            _pc(_issues(a, b, -mu, t)[0]),
            num(ecart_directionnel(t0), 2),
        ])
    return Table(
        "spec_optimum",
        "L'horizon où la dérive sépare le plus les deux sens",
        ["Horizon (min)", "a (pts)", "Objectif en écarts-types de séance",
         "P à dérive nulle", "P à la dérive haute", "P au sens inverse",
         "Écart (points de taux)"],
        rows,
        note="La dernière colonne est la seule chose qu'une spéculation "
             "directionnelle achète : la différence entre parier dans le bon "
             "sens et parier dans l'autre. Elle est nulle à dérive nulle, à "
             "tout horizon et exactement. Sous la dérive haute du domaine "
             "plausible elle passe par un maximum, et le maximum tombe à "
             + num(opt, 0) + " minutes, où l'écart vaut "
             + num(ecart_directionnel(opt), 1) + " points de taux contre "
             + num(ecart_directionnel(5.0), 1) + " à cinq minutes et "
             + num(ecart_directionnel(390.0), 1) + " à la séance entière. "
             "Le compromis a deux côtés mesurables : sous cet horizon la "
             "dérive n'a pas le temps d'agir, au-dessus la séance tronque "
             "l'objectif. La troisième colonne dit où le maximum tombe, et "
             "elle vaut " + num(portee_de_l_optimum(), 3) + " — *l'horizon "
             "optimal est celui dont l'objectif vaut exactement un "
             "écart-type de séance*, et ce n'est pas un artefact de "
             "balayage : c'est la seule échelle où la dérive dispose de "
             "toute la séance sans que la séance lui reprenne l'objectif. "
             "La dernière ligne marque la frontière de l'affirmation : à deux "
             "séances, l'écart remonte à "
             + num(ecart_directionnel(780.0), 1) + " points, parce que la "
             "position n'est plus fermée au coup de cloche et que la dérive "
             "agit plus longtemps que la volatilité ne s'étale. *L'optimum "
             "est celui d'un opérateur intrajournalier, et il cesse d'en être "
             "un dès qu'on lève cette contrainte.*")


def all_tables() -> dict[str, Table]:
    return {t.key: t for t in (
        table_geometries(), table_sens(), table_portee(), table_routes(),
        table_lectures(), table_optimum(), table_esperance(),
        table_bandeaux(), table_reste(),
    )}


# ---------------------------------------------------------------------------
# VI. Les surfaces
# ---------------------------------------------------------------------------

#: Les axes des reliefs. Chaque surface a le sien, et l'ordre n'est pas un
#: détail : en projection isométrique le coin `(0, 0)` est le plus éloigné, et
#: y placer le maximum fait monter le relief vers l'horizon. À l'ordre inverse
#: le sommet tombe au premier plan, où il paraît à la même hauteur d'écran que
#: le coin lointain. Une surface croissante et une surface décroissante dans
#: la même grandeur demandent donc des axes opposés.
SURF_STOP: tuple[float, ...] = (0.200, 0.150, 0.100, 0.050, 0.025, 0.010)
SURF_STOP_CROISSANT: tuple[float, ...] = (0.010, 0.025, 0.050, 0.100, 0.150,
                                          0.200)

SURF_RR: tuple[float, ...] = (20.0, 12.0, 7.0, 4.0, 2.0, 1.0)
SURF_RR_CROISSANT: tuple[float, ...] = (1.0, 2.0, 4.0, 7.0, 12.0, 20.0)

#: Les dérives des reliefs, en points par heure.
SURF_DERIVE: tuple[float, ...] = (3.2, 2.6, 2.0, 1.4, 0.8, 0.2)


@lru_cache(maxsize=2)
def surface_survie() -> tuple[tuple[float, ...], ...]:
    """La part du théorème qui survit à la séance, en stop et en rapport.

    `P(objectif)` rapportée à `1/(1+RR)`. Elle vaut **un** partout où
    l'objectif tient dans la portée d'une séance — le théorème s'y applique
    exactement — et elle s'effondre au coin où il n'y tient plus. Publier le
    rapport plutôt que la probabilité est ce qui rend le relief lisible : la
    probabilité brute varie de cinquante pour cent à zéro et son plateau
    écrase tout le reste, quand le rapport a un plafond à un.
    """
    return tuple(tuple(lire(s, 0.0, 1, rr).p_objectif * (1.0 + rr)
                       for rr in SURF_RR_CROISSANT)
                 for s in SURF_STOP_CROISSANT)


@lru_cache(maxsize=2)
def surface_portee() -> tuple[tuple[float, ...], ...]:
    """L'objectif en écarts-types de séance, en stop et en rapport."""
    return tuple(tuple(portee_de_seance(s, rr) for rr in SURF_RR)
                 for s in SURF_STOP)


@lru_cache(maxsize=2)
def surface_ecart() -> tuple[tuple[float, ...], ...]:
    """L'écart entre les deux sens, en points de taux, en stop et en dérive."""
    return tuple(tuple(100.0 * (lire(s, d, 1).p_objectif
                                - lire(s, d, -1).p_objectif)
                       for d in SURF_DERIVE)
                 for s in SURF_STOP_CROISSANT)


@lru_cache(maxsize=2)
def surface_esperance() -> tuple[tuple[float, ...], ...]:
    """E[R] à la hausse, en largeur de stop et en dérive."""
    return tuple(tuple(lire(s, d, 1).esperance_r for d in SURF_DERIVE)
                 for s in SURF_STOP)


# ---------------------------------------------------------------------------
# VII. Les valeurs citées dans le texte
# ---------------------------------------------------------------------------


def values() -> dict[str, str]:
    d0 = lire(GEOMETRIES[0])
    d2 = lire(GEOMETRIES[2])
    haute = seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]
    basse = seuil.PLAUSIBLE_DRIFT_PER_HOUR[0]
    return {
        "spec_p_nulle": _pc(d0.p_objectif),
        "spec_portee_declaree": num(portee_de_seance(GEOMETRIES[0]), 2),
        "spec_portee_elargie": num(portee_de_seance(GEOMETRIES[2]), 2),
        "spec_p_elargie": _pc(d2.p_objectif),
        "spec_ouvert_elargie": _pc(d2.p_ouvert),
        "spec_rr_declare": num(RR, 0),
        "spec_rr_atteignable": num(rr_atteignable(GEOMETRIES[2], 0.05), 1),
        "spec_rr_atteignable_moyen": num(rr_atteignable(GEOMETRIES[1], 0.05),
                                         1),
        "spec_ecart_haut": num(100.0 * (lire(GEOMETRIES[1], haute, 1)
                                        .p_objectif
                                        - lire(GEOMETRIES[1], haute, -1)
                                        .p_objectif), 1),
        "spec_ecart_declare": num(100.0 * (lire(GEOMETRIES[0], haute, 1)
                                           .p_objectif
                                           - lire(GEOMETRIES[0], haute, -1)
                                           .p_objectif), 1),
        "spec_p_basse_elargie": _pc(lire(GEOMETRIES[2], basse, 1).p_objectif),
        "spec_wald_declare": num(derive_de_wald(GEOMETRIES[0]), 2),
        "spec_libre_declare": num(derive_non_bornee(GEOMETRIES[0]), 2),
        "spec_ecart_routes_declare": num(ecart_des_routes(GEOMETRIES[0]), 2),
        "spec_ecart_routes_elargi": num(ecart_des_routes(GEOMETRIES[2]), 1),
        "spec_er_nul": num(d0.esperance_r, 3),
        "spec_er_haut": num(lire(GEOMETRIES[2], haute, 1).esperance_r, 3),
        "spec_er_bas": num(lire(GEOMETRIES[2], haute, -1).esperance_r, 3),
        "spec_derive_haute": num(haute, 1),
        "spec_derive_basse": num(basse, 1),
        "spec_ecart_seance": num(ECART_SEANCE, 1),
        "spec_familles": num(len(HYPOTHESES), 0),
        "spec_lectures": num(len(lignes()), 0),
        "spec_horizon_optimal": num(horizon_optimal(), 0),
        "spec_portee_optimale": num(portee_de_l_optimum(), 3),
        "spec_ecart_optimal": num(ecart_directionnel(horizon_optimal()), 1),
        "spec_ecart_court": num(ecart_directionnel(5.0), 1),
        "spec_ecart_seance_entiere": num(ecart_directionnel(390.0), 1),
        "spec_p_courte": _pc(lignes()[0].p_nulle),
        "spec_p_longue": _pc(lignes()[-1].p_nulle),
        "spec_facteur_horloge": num(lignes()[0].p_nulle
                                    / lignes()[-1].p_nulle, 1),
        "spec_stop_optimal": num(SIGMA_MIN * math.sqrt(horizon_optimal()), 2),
        "spec_objectif_optimal": num(C.RR_LECTURE * SIGMA_MIN
                                     * math.sqrt(horizon_optimal()), 1),
    }


def main() -> None:
    for t in all_tables().values():
        print(t.to_text())
        print()
    for k, v in values().items():
        print(f"{k:28s} {v}")


if __name__ == "__main__":
    main()
