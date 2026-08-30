"""Le catalogue des lectures, dans l'ordre de leur horizon.

Ce module répond à une question que les deux premiers documents laissaient
éparpillée : **quinze lectures de marché sont citées, dans quel ordre faut-il
les prendre, et que vaut chacune ?**

L'ordre n'est pas écrit, il est calculé
--------------------------------------
Chaque lecture porte un **horizon d'observation** déclaré — la durée sur
laquelle son motif se forme et se résout. Le catalogue est trié par cet
horizon, du plus court au plus long, et ce tri n'est pas d'esthétique : il
range les lectures de la plus **prouvable** à la moins prouvable. Une lecture
de cinq minutes offre des dizaines d'occasions par séance ; une structure de
Dow en offre une tous les trois jours. Le nombre de décisions requis pour
établir l'une ou l'autre, lui, ne diminue pas — il augmente.

D'où le résultat structurant de ce catalogue, qui tient en une phrase :

    ce qui se prouve ne paie pas, ce qui paie ne se prouve pas.

À cinq minutes, la géométrie de lecture exige une dérive de près de deux
points par heure — dans le domaine plausible, mais tout en haut. À trois
séances, elle n'en exige plus qu'un centième de point — sauf qu'il faut deux
cent soixante mille décisions pour l'établir, et que le marché n'en offre
qu'une centaine par an.

Ce qui est déclaré, et ce qui est calculé
-----------------------------------------
Trois choses sont **déclarées**, et elles sont les seules :

* l'horizon de chaque lecture et le nombre d'occasions qu'elle offre par
  séance — ce sont des faits de forme, pas des résultats ;
* la géométrie de lecture : un rapport gain-risque de 2 et une barrière de
  réaction posée aux trois quarts de l'écart-type d'horizon ;
* la dérive haute du domaine plausible, reprise de `seuil.py`.

Tout le reste est calculé, y compris les verdicts. En particulier, **aucune
probabilité de continuation n'est postulée**. La question « le motif marche-t-il
sept fois sur dix ? » n'est pas posée ; on calcule ce que la fréquence devrait
valoir pour que la lecture paie sa friction, et ce que coûte l'établissement
de cet écart. C'est la seule façon d'éviter le piège de circularité que la
section 18 du document nº 1 documente.

La loi nulle
------------
Sous un prix sans dérive, la réaction est **exactement symétrique** : autant
de chances de monter que de descendre, excursion favorable médiane égale à
l'excursion défavorable, et probabilité d'être plus haut à l'horizon égale à
un demi à la troisième décimale. C'est l'ancrage pédagogique du catalogue :
un concept ne dit rien tant qu'il ne déplace pas `µ`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from . import dow, entropy, fib, seuil, tpo, varratio, vprofile
from . import footprint as fp
from . import orderflow as of
from . import quant as q
from .barriers import required_drift
from .costs import COST_BASE, ES, norm_cdf
from .mc import Rng
from .report import Table, num

# ---------------------------------------------------------------------------
# Paramètres déclarés
# ---------------------------------------------------------------------------

#: Rapport gain-risque de la **géométrie de lecture**. Il n'a rien à voir avec
#: le 20:1 que l'opérateur déclare : la question posée ici n'est pas « que
#: rapporte son trade » mais « que doit valoir cette lecture pour payer sa
#: friction sur son propre horizon ». Un rapport de 2 est le plus neutre qu'on
#: puisse poser — il ne penche ni vers la fréquence ni vers l'amplitude.
RR_LECTURE = 2.0

#: Barrière de réaction, en écarts-types d'horizon. À trois quarts d'écart-type
#: la barrière est atteinte dans quatre cas sur cinq avant la fin de
#: l'horizon : la lecture reste informative. Posée à un écart-type entier, la
#: majorité des tirages expirerait sans rien toucher et la table ne dirait plus
#: que la troncature.
K_BARRIERE = 0.75

#: Séances de bourse par an, comme dans tout le dépôt.
SEANCES_PAR_AN = 252.0

#: Niveau de test et puissance du contrôle d'établissement.
ALPHA = 0.05
PUISSANCE = 0.80

#: Trajectoires appariées par point de la table de réaction. Le nombre est
#: modulé par l'horizon : une lecture de cinq minutes est cent fois moins
#: coûteuse à simuler qu'une structure de trois séances.
PAIRES_MIN, PAIRES_MAX, PAIRES_BUDGET = 800, 5000, 300_000

#: Séances simulées pour les quatre détecteurs de motif qui n'ont pas de loi
#: fermée : la bande VWAP, le nœud de faible volume, le retour au POC et le
#: retest de niveau.
SEANCES = 400
SEED = 20260830

#: Seuil de z d'impact sous lequel une barre est lue comme absorbante. Le z
#: rapporte déjà le déplacement à la racine du volume : un z proche de zéro
#: **est** l'absorption, et le volume élevé y est contenu.
Z_ABSORPTION = 0.25

#: Rapport du volume au niveau extrême sur le volume médian sous lequel une
#: barre est lue comme épuisée. Déclaré : la lecture d'usage dit « le volume
#: s'effondre au bout », et la moitié de la médiane en est la traduction la
#: plus littérale.
SEUIL_EPUISEMENT = 0.5

#: Corrélation entre signe du volume délta et signe du rendement, utilisée par
#: la loi nulle de la divergence. Elle vient de `orderflow`.
CORRELATION_CVD = 0.62

#: Persistance de liquidité : durée qu'un niveau doit tenir pour être lu comme
#: « vrai », et taux de retrait sous lequel on la calcule.
LPR_MINUTES = 5.0
LPR_HAZARD = 0.18


def friction() -> float:
    """`c` — friction aller-retour en points d'indice."""
    return COST_BASE.friction_points(ES)


def derive_haute() -> float:
    """Borne haute du domaine de dérive plausible, en points par heure."""
    return seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]


# ---------------------------------------------------------------------------
# Les quinze lectures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Lecture:
    """Une lecture de marché, et les trois faits de forme qui la décrivent.

    `occasions` est le nombre de fois qu'une séance **présente la situation**,
    pas le nombre de fois que le motif se complète : c'est la distinction qui
    permet de séparer la rareté d'un motif de la rareté de son contexte.
    """

    cle: str
    nom: str
    famille: str
    horizon_min: float
    occasions: float
    situation: str
    attente: str
    source_nulle: str


CATALOGUE: tuple[Lecture, ...] = (
    Lecture("desequilibre", "Déséquilibre diagonal", "Footprint", 5.0, 624.0,
            "l'ask d'un niveau écrase le bid du niveau du dessous, trois "
            "pour un",
            "la poursuite du mouvement dans le sens du déséquilibre",
            "binomiale exacte, à taille de grappe déclarée"),
    Lecture("absorption", "Absorption", "Footprint", 5.0, 78.0,
            "un volume élevé s'échange et le prix ne bouge pas",
            "le rejet du côté où le volume a été absorbé",
            "loi centrale du z d'impact"),
    Lecture("epuisement", "Épuisement", "Footprint", 5.0, 78.0,
            "le volume s'effondre au niveau extrême de l'excursion",
            "le retournement, faute de participants au bout",
            "loi simulée du rapport d'épuisement"),
    Lecture("carnet", "Persistance de liquidité", "Carnet", 5.0, 48.0,
            "un bloc affiché reste en place au lieu de se retirer",
            "le niveau tient et le prix rebondit dessus",
            "loi exponentielle du retrait"),
    Lecture("divergence", "Divergence du CVD", "Flux", 15.0, 26.0,
            "le prix fait un nouvel extrême, le volume délta cumulé non",
            "l'essoufflement puis le retournement",
            "loi du signe sous corrélation déclarée"),
    Lecture("vwap", "Bande VWAP", "Prix-volume", 30.0, 0.0,
            "le prix touche la deuxième bande d'écart-type autour du VWAP",
            "le retour vers le VWAP",
            "détecteur simulé sur séances sans dérive"),
    Lecture("ote", "Zone d'entrée optimale", "Fibonacci", 45.0, 6.0,
            "le prix retrace une jambe entre 61,8 % et 79 %",
            "la reprise de la jambe depuis la zone",
            "loi de retracement sous martingale"),
    Lecture("lvn", "Nœud de faible volume", "Prix-volume", 60.0, 0.0,
            "le prix aborde une zone où peu de volume s'est échangé",
            "la traversée rapide, faute de liquidité pour retenir",
            "détecteur simulé sur séances sans dérive"),
    Lecture("poc", "Retour au point de contrôle", "Prix-volume", 60.0, 1.0,
            "le prix s'écarte du prix le plus échangé de la séance",
            "le retour au point de contrôle avant la clôture",
            "détecteur simulé sur séances sans dérive"),
    Lecture("singles", "Tirages simples", "Profil de marché", 90.0, 1.0,
            "une rangée du profil n'est visitée que par une seule période",
            "le comblement de la rangée laissée vide",
            "loi simulée du profil TPO"),
    Lecture("retest", "Retest de niveau", "Structure", 120.0, 0.0,
            "le prix revient sur un extrême de séance qu'il avait quitté",
            "le niveau tient et le prix repart",
            "détecteur simulé sur séances sans dérive"),
    Lecture("extreme", "Extrême pauvre", "Profil de marché", 390.0, 1.0,
            "le haut de séance est plat, sans queue de rejet",
            "l'extension au-delà, la séance suivante",
            "loi simulée du profil TPO"),
    Lecture("gamma", "Régime de gamma", "Dérivés", 390.0, 1.0,
            "l'exposition gamma des teneurs de marché passe sous zéro",
            "l'amplification des mouvements au lieu de leur amortissement",
            "détecteur simulé sur séances sans dérive"),
    Lecture("meche", "Rejet en mèche", "Structure", 390.0, 1.0,
            "la bougie de séance ferme loin de son extrême, mèche dominante",
            "le rejet du niveau touché par la mèche",
            "loi de la mèche dominante sous martingale"),
    Lecture("structure", "Plus haut plus haut", "Structure", 1170.0, 0.34,
            "trois séances dessinent un sommet plus haut et un creux plus haut",
            "la poursuite de la tendance ainsi établie",
            "loi du plus haut plus haut sous martingale"),
)


def ordre() -> tuple[Lecture, ...]:
    """Le catalogue trié par horizon croissant, puis par nom.

    Le tri est la seule chose que ce module impose à la lecture du document :
    il n'y a pas d'ordre écrit ailleurs, et changer un horizon déplace la
    lecture dans la table sans qu'aucune prose n'ait à bouger.
    """
    return tuple(sorted(CATALOGUE, key=lambda l: (l.horizon_min, l.nom)))


# ---------------------------------------------------------------------------
# Quatre détecteurs sans loi fermée : on les mesure sur des séances sans dérive
# ---------------------------------------------------------------------------


@lru_cache(maxsize=2)
def _seances(n: int = SEANCES) -> tuple[tuple[float, ...], ...]:
    """`n` séances de prix sans dérive, à la minute.

    Rien n'est ajouté à la marche : ni saut, ni saisonnalité, ni régime. C'est
    le minimum contre lequel un détecteur de motif doit se comparer, et il
    suffit à établir qu'aucun des quatre motifs simulés ici n'est rare.
    """
    rng = Rng(SEED)
    sessions = []
    for _ in range(n):
        x, chemin = 0.0, [0.0]
        for _ in range(int(q.SESSION_MIN)):
            x += q.SIGMA_1MIN * rng.gauss()
            chemin.append(x)
        sessions.append(tuple(chemin))
    return tuple(sessions)


@dataclass(frozen=True)
class Detection:
    """Ce qu'un détecteur rend : des occasions, et la part qui se complète."""

    occasions: float          # par séance
    frequence: float          # P(le motif se complète | l'occasion se présente)


def _detect_vwap(chemin: tuple[float, ...]) -> tuple[int, int]:
    """Touches de la deuxième bande, et retours au VWAP dans les trente minutes.

    Le volume par minute étant stable dans la simulation, le VWAP est la
    moyenne courante du prix et la bande son écart-type courant — c'est la
    définition, pas une approximation.
    """
    somme = carre = 0.0
    touches = retours = 0
    dehors = False
    attente: list[tuple[int, float]] = []
    for i, x in enumerate(chemin):
        somme += x
        carre += x * x
        n = i + 1
        moyenne = somme / n
        var = max(carre / n - moyenne * moyenne, 0.0)
        sigma = math.sqrt(var)
        if n < 30 or sigma <= 0:
            continue
        ecart = abs(x - moyenne)
        if ecart >= 2.0 * sigma:
            if not dehors:
                touches += 1
                attente.append((i, moyenne))
                dehors = True
        else:
            dehors = False
        for depart, cible in list(attente):
            if i - depart > 30:
                attente.remove((depart, cible))
            elif abs(x - cible) <= 0.25 * q.SIGMA_1MIN:
                retours += 1
                attente.remove((depart, cible))
    return touches, retours


def _detect_lvn(chemin: tuple[float, ...]) -> tuple[int, int]:
    """Abords d'un nœud de faible volume, et traversées franches.

    Le profil est bâti sur la première demi-séance, les abords comptés sur la
    seconde : un nœud lu sur la séance entière serait un nœud connu après
    coup, ce qui n'est pas la situation de l'opérateur.
    """
    demi = len(chemin) // 2
    profil = vprofile.from_path(chemin[:demi], step=1.0)
    noeuds = profil.lvn(prominence=0.05)
    if not noeuds:
        return 0, 0
    abords = traversees = 0
    for noeud in noeuds:
        loin = True
        depart: int | None = None
        for i in range(demi, len(chemin)):
            ecart = chemin[i] - noeud
            if depart is None:
                if loin and abs(ecart) <= 1.0:
                    abords += 1
                    depart = i
                    cote = 1.0 if chemin[i - 1] > noeud else -1.0
                    loin = False
                elif abs(ecart) > 3.0:
                    loin = True
            else:
                if i - depart > 60:
                    depart = None
                elif ecart * cote < -2.0:
                    traversees += 1
                    depart = None
    return abords, traversees


def _detect_poc(chemin: tuple[float, ...]) -> tuple[int, int]:
    """Écart au point de contrôle de mi-séance, et retour avant la clôture."""
    demi = len(chemin) // 2
    poc = vprofile.from_path(chemin[:demi], step=1.0).poc
    if abs(chemin[demi] - poc) <= 1.0:
        return 0, 0
    for x in chemin[demi:]:
        if abs(x - poc) <= 1.0:
            return 1, 1
    return 1, 0


def _detect_retest(chemin: tuple[float, ...]) -> tuple[int, int]:
    """Retests de l'extrême de la première heure, et part qui tient.

    « Tenir » est défini avant de regarder : le prix ne dépasse pas le niveau
    de deux points dans les deux heures qui suivent le retest. Sans définition
    écrite d'avance, un retest tenu est un retest qu'on a décidé de tenir pour
    tel après coup.
    """
    if len(chemin) < 180:
        return 0, 0
    niveau = max(chemin[:60])
    retests = tenus = 0
    parti = False
    i = 60
    while i < len(chemin) - 120:
        x = chemin[i]
        if not parti:
            if x < niveau - 3.0:
                parti = True
        elif x >= niveau - 0.5:
            retests += 1
            fenetre = chemin[i:i + 120]
            if max(fenetre) < niveau + 2.0:
                tenus += 1
            parti = False
            i += 30
            continue
        i += 1
    return retests, tenus


def _detect_singles(chemin: tuple[float, ...]) -> tuple[int, int]:
    """Tirages simples de la première moitié, et part comblée avant la clôture.

    Le profil est bâti sur les six premières périodes de trente minutes ; les
    rangées qu'une seule période a touchées sont les occasions, et le motif se
    complète si le prix revient les visiter avant la clôture.
    """
    demi = len(chemin) // 2
    profil = tpo.from_path(chemin[:demi], n_periods=6, tick=1.0)
    simples = profil.single_prints
    if not simples:
        return 0, 0
    reste = chemin[demi:]
    combles = sum(1 for prix in simples
                  if any(abs(x - prix) <= 0.5 for x in reste))
    return len(simples), combles


def _hurst_seance(chemin: tuple[float, ...], q: int = 5) -> float:
    """Exposant de Hurst estimé sur une séance, par ratio de variance.

    L'estimateur est celui du dépôt, appliqué à une seule séance. Ce qu'il
    rend sur une **vraie** martingale est le fait qui compte ici, et il est
    déjà documenté ailleurs : il ne rend pas un demi.
    """
    r = [chemin[i + 1] - chemin[i] for i in range(len(chemin) - 1)]
    n = len(r) // q * q
    if n < 2 * q:
        return 0.5
    r = r[:n]
    moyenne = sum(r) / n
    v1 = sum((x - moyenne) ** 2 for x in r) / (n - 1)
    blocs = [sum(r[i:i + q]) for i in range(0, n, q)]
    m = len(blocs)
    moy_q = sum(blocs) / m
    vq = sum((x - moy_q) ** 2 for x in blocs) / (m - 1)
    if v1 <= 0:
        return 0.5
    return varratio.hurst_from_vr(vq / (q * v1), q)


def _detect_gamma(chemin: tuple[float, ...]) -> tuple[int, int]:
    """La séance paraît-elle amplifiante à l'estimateur usuel ?

    Une occasion par séance, et le motif se complète quand l'exposant estimé
    dépasse un demi — c'est-à-dire quand la lecture conclut au régime
    amplifiant. Sous martingale exacte, la bonne réponse est « jamais ».
    """
    return 1, 1 if _hurst_seance(chemin) > 0.5 else 0


_DETECTEURS = {"vwap": _detect_vwap, "lvn": _detect_lvn,
               "poc": _detect_poc, "retest": _detect_retest,
               "singles": _detect_singles, "gamma": _detect_gamma}


@lru_cache(maxsize=8)
def detecter(cle: str) -> Detection:
    """Occasions par séance et fréquence du motif, sur prix sans dérive."""
    fn = _DETECTEURS[cle]
    total_occ = total_mot = 0
    for chemin in _seances():
        occ, mot = fn(chemin)
        total_occ += occ
        total_mot += mot
    n = float(len(_seances()))
    return Detection(total_occ / n, total_mot / total_occ if total_occ else 0.0)


# ---------------------------------------------------------------------------
# La fréquence nulle de chaque motif
# ---------------------------------------------------------------------------


@lru_cache(maxsize=32)
def frequence_nulle(cle: str) -> float:
    """`P(le motif se complète)` sous prix sans dérive, par lecture.

    Onze des quinze lectures ont une loi nulle déjà écrite dans le dépôt —
    binomiale exacte pour le déséquilibre, loi centrale pour l'absorption,
    lois simulées pour l'épuisement et le profil TPO. Les quatre autres sont
    mesurées ici sur des séances sans dérive. Aucune n'est déclarée.
    """
    if cle in _DETECTEURS:
        return detecter(cle).frequence
    if cle == "desequilibre":
        barre = fp.synthesise("neutre")
        return fp.expected_imbalances(barre) / (len(barre.cells) - 1)
    if cle == "absorption":
        # Le z d'impact est centré réduit sous martingale : la probabilité
        # qu'une barre paraisse absorbante est celle d'un z petit.
        return 2.0 * norm_cdf(Z_ABSORPTION) - 1.0
    if cle == "epuisement":
        nul = fp.null_exhaustion()
        return norm_cdf((SEUIL_EPUISEMENT - nul.mean) / nul.sd)
    if cle == "carnet":
        return of.lpr_expected(LPR_HAZARD, LPR_MINUTES)
    if cle == "divergence":
        return of.p_sign_divergence(CORRELATION_CVD)
    if cle == "ote":
        return fib.p_retrace_null(0.618, continuation=0.10)
    if cle == "extreme":
        nul = tpo.null_profile()
        return nul.p_poor_high
    if cle == "meche":
        return dow.p_dominant_wick(1.0)
    if cle == "structure":
        return dow.p_higher_high_null(0.4, 3.0)
    raise KeyError(f"lecture inconnue : {cle}")




def occasions(cle: str) -> float:
    """Occasions par séance : mesurées quand un détecteur existe, sinon déclarées."""
    if cle in _DETECTEURS:
        return detecter(cle).occasions
    return _PAR_CLE[cle].occasions


_PAR_CLE = {l.cle: l for l in CATALOGUE}


# ---------------------------------------------------------------------------
# Ce que chaque lecture doit valoir, et ce qu'il en coûte de l'établir
# ---------------------------------------------------------------------------


def _inv_norm(p: float) -> float:
    """Quantile normal par bissection sur `norm_cdf` — stdlib, sans table."""
    lo, hi = -12.0, 12.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


@dataclass(frozen=True)
class Exigence:
    """Ce que la géométrie de lecture exige, à un horizon donné."""

    horizon_min: float
    stop: float               # a, en points : l'écart-type d'horizon
    cible: float              # b = RR_LECTURE · a
    friction_ratio: float     # c/a
    taux_nul: float           # 1/(1+RR) — le taux d'équilibre sans friction
    taux_requis: float        # (1 + c/a)/(1+RR)
    bits: float               # information minimale par décision
    derive_requise: float     # µ*, en points par heure
    decisions: float          # décisions pour établir l'écart
    par_an: float             # décisions offertes par an
    annees: float             # decisions / par_an

    @property
    def atteignable(self) -> bool:
        """La dérive requise tombe-t-elle dans le domaine plausible ?"""
        return self.derive_requise <= derive_haute()

    @property
    def verdict(self) -> str:
        """Le verdict, calculé et jamais écrit.

        Deux questions indépendantes, et le verdict nomme celle qui tranche :
        la dérive requise est-elle dans le domaine plausible, et le nombre
        d'années requis tient-il dans une carrière ? Une lecture peut échouer
        sur l'une, sur l'autre, ou sur les deux.
        """
        court = self.annees <= CARRIERE_ANS
        if self.atteignable and court:
            return "payante et prouvable"
        if self.atteignable:
            return "payante, hors de portée de preuve"
        if court:
            return "prouvable, mais hors du domaine de dérive"
        return "ni payante ni prouvable"


#: Durée au-delà de laquelle une exigence de preuve sort d'une carrière
#: d'opérateur. Déclarée, et volontairement généreuse.
CARRIERE_ANS = 30.0


def geometrie(horizon_min: float) -> tuple[float, float, float]:
    """La géométrie de lecture à un horizon : `(a, b, c)` en points."""
    a = q.SIGMA_1MIN * math.sqrt(horizon_min)
    return a, RR_LECTURE * a, friction()


def decisions_pour(horizon_min: float) -> float:
    """Décisions requises pour établir la rentabilité d'un horizon donné.

    Écrit pour un horizon quelconque et non pour les seuls horizons du
    catalogue : la courbe de la carrière, dans les figures, est continue et
    doit se calculer partout.
    """
    a, _, c = geometrie(horizon_min)
    besoin = entropy.required_bits(RR_LECTURE, c / a)
    p0, p1 = besoin.hit_null, besoin.hit_needed
    za, zb = _inv_norm(1.0 - ALPHA / 2.0), _inv_norm(PUISSANCE)
    return ((za * math.sqrt(p0 * (1.0 - p0))
             + zb * math.sqrt(p1 * (1.0 - p1))) / (p1 - p0)) ** 2


@lru_cache(maxsize=64)
def exigence(cle: str) -> Exigence:
    """L'exigence complète d'une lecture, à son propre horizon.

    Rien n'y est postulé sur l'efficacité du motif. On y calcule ce que la
    fréquence devrait valoir pour couvrir la friction — c'est la borne
    inférieure de Kullback-Leibler du module `entropy` — puis le nombre de
    décisions qui sépare cette fréquence de celle du hasard, puis le temps que
    le marché met à en offrir autant.
    """
    t = _PAR_CLE[cle].horizon_min
    a, b, c = geometrie(t)
    besoin = entropy.required_bits(RR_LECTURE, c / a)
    mu = required_drift(a, b, q.SIGMA_1MIN, c) * 60.0
    p0, p1 = besoin.hit_null, besoin.hit_needed
    n = decisions_pour(t)

    par_an = occasions(cle) * frequence_nulle(cle) * SEANCES_PAR_AN
    return Exigence(t, a, b, c / a, p0, p1, besoin.bits, mu, n, par_an,
                    n / par_an if par_an > 0 else math.inf)


# ---------------------------------------------------------------------------
# Où va le prix, une fois le motif reconnu
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Reaction:
    """La suite du prix sur l'horizon de la lecture, barrières comprises.

    Toutes les grandeurs sont en points d'indice et rapportées au prix au
    moment du signal. `p_haut` et `p_bas` sont les probabilités de toucher la
    barrière favorable ou défavorable avant la fin de l'horizon ; `p_ouvert`
    celle de n'en toucher aucune.
    """

    barriere: float
    p_haut: float
    p_bas: float
    p_ouvert: float
    mfe: float                # excursion favorable médiane
    mae: float                # excursion défavorable médiane
    fin: float                # déplacement médian à l'horizon
    p_plus_haut: float        # P(le prix est plus haut à l'horizon)
    paires: int


def _paires(horizon_min: float) -> int:
    n = int(PAIRES_BUDGET / max(horizon_min, 1.0))
    return max(PAIRES_MIN, min(PAIRES_MAX, n))


@lru_cache(maxsize=128)
def reaction(horizon_min: float, derive_par_heure: float) -> Reaction:
    """Simulation appariée de la suite du prix, à horizon et dérive donnés.

    Chaque tirage est doublé par son antithétique — même bruit, signe opposé,
    dérive inchangée. Sous dérive nulle l'appariement rend la table
    **exactement** symétrique, et c'est le contrôle qui autorise à lire la
    colonne sous dérive : tout écart y est l'effet de la dérive, jamais celui
    du tirage.
    """
    t = int(round(horizon_min))
    d = K_BARRIERE * q.SIGMA_1MIN * math.sqrt(t)
    mu = derive_par_heure / 60.0
    n_paires = _paires(horizon_min)

    rng = Rng(SEED)
    haut = bas = ouvert = plus_haut = 0
    mfe: list[float] = []
    mae: list[float] = []
    fin: list[float] = []
    for _ in range(n_paires):
        z = [rng.gauss() for _ in range(t)]
        for signe in (1.0, -1.0):
            x = pic = creux = 0.0
            issue = 0
            for u in z:
                x += mu + q.SIGMA_1MIN * signe * u
                pic = max(pic, x)
                creux = min(creux, x)
                if issue == 0:
                    if x >= d:
                        issue = 1
                    elif x <= -d:
                        issue = -1
            haut += issue == 1
            bas += issue == -1
            ouvert += issue == 0
            plus_haut += x > 0.0
            mfe.append(pic)
            mae.append(creux)
            fin.append(x)

    n = float(len(fin))

    def med(v: list[float]) -> float:
        v = sorted(v)
        m = len(v)
        return v[m // 2] if m % 2 else 0.5 * (v[m // 2 - 1] + v[m // 2])

    return Reaction(d, haut / n, bas / n, ouvert / n, med(mfe), med(mae),
                    med(fin), plus_haut / n, n_paires)


@lru_cache(maxsize=32)
def eventail(horizon_min: float, derive_par_heure: float,
             pas: int = 24) -> tuple[tuple[float, ...], ...]:
    """Quantiles du prix minute par minute après le signal.

    Rendu `pas + 1` colonnes, chacune portant les quantiles à 10, 25, 50, 75
    et 90 % du déplacement depuis le signal. C'est la matière de l'éventail
    dessiné dans les figures : sous prix sans dérive il est symétrique autour
    de zéro, et sous dérive il penche sans jamais cesser de contenir zéro.
    """
    t = int(round(horizon_min))
    mu = derive_par_heure / 60.0
    n_paires = _paires(horizon_min)
    jalons = [round(k * t / pas) for k in range(pas + 1)]
    colonnes: list[list[float]] = [[] for _ in jalons]

    rng = Rng(SEED + 1)
    for _ in range(n_paires):
        z = [rng.gauss() for _ in range(t)]
        for signe in (1.0, -1.0):
            x = 0.0
            chemin = [0.0]
            for u in z:
                x += mu + q.SIGMA_1MIN * signe * u
                chemin.append(x)
            for k, j in enumerate(jalons):
                colonnes[k].append(chemin[j])

    out = []
    for col in colonnes:
        col.sort()
        out.append(tuple(_quantile(col, f)
                         for f in (0.10, 0.25, 0.50, 0.75, 0.90)))
    return tuple(out)


def _quantile(tries: list[float], f: float) -> float:
    """Quantile par interpolation linéaire entre les deux rangs encadrants.

    L'interpolation n'est pas un raffinement : c'est ce qui rend la paire de
    quantiles `f` et `1 − f` **exactement** opposée sur un échantillon
    symétrique. La sélection par troncature d'indice ne l'était pas, et
    l'éventail sans dérive penchait alors d'un centième de point — assez pour
    contredire à l'écran la symétrie que le chapitre affirme.
    """
    n = len(tries)
    if n == 1:
        return tries[0]
    k = f * (n - 1)
    i = int(math.floor(k))
    j = min(i + 1, n - 1)
    t = k - i
    return tries[i] * (1.0 - t) + tries[j] * t


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


def _ans(v: float) -> str:
    """Une durée en années, lisible sur cinq ordres de grandeur."""
    if v is None or v == math.inf:
        return "jamais"
    if v < 1.0:
        return num(v * 12.0, 1) + " mois"
    if v < 100.0:
        return num(v, 1) + " ans"
    if v < 10_000.0:
        return num(v, 0) + " ans"
    return num(v / 1000.0, 1) + " millénaires"


def _grand(v: float) -> str:
    """Un compte, avec espace fine insécable de millier."""
    return f"{round(v):,}".replace(",", " ")


def table_catalogue() -> Table:
    """Les quinze lectures, dans l'ordre calculé de leur horizon."""
    rows = []
    for rang, l in enumerate(ordre(), start=1):
        rows.append([
            str(rang),
            l.nom,
            l.famille,
            _horizon(l.horizon_min),
            num(occasions(l.cle), 2),
            num(100.0 * frequence_nulle(l.cle), 1) + " %",
            l.source_nulle,
        ])
    return Table(
        "catalogue",
        "Les quinze lectures du dispositif, rangées par horizon croissant.",
        ["#", "Lecture", "Famille", "Horizon", "Occasions par séance",
         "Fréquence sous prix sans dérive", "Loi nulle"],
        rows,
        wide=True,
        wrap_cols=[6],
        note="L'ordre n'est pas écrit : il est celui de l'horizon, et il range "
             "les lectures de la plus rapide à la plus lente. La colonne des "
             "occasions dit combien de fois par séance la **situation** se "
             "présente ; celle de la fréquence, quelle part de ces situations "
             "voit le motif se compléter **alors qu'il n'y a rien à lire**. "
             "Aucune de ces fréquences n'est petite. Le déséquilibre diagonal "
             "se produit une fois sur neuf par pur hasard, la traversée d'un "
             "nœud de faible volume sept fois sur dix, la structure de Dow "
             "presque neuf fois sur dix.")


def _horizon(minutes: float) -> str:
    if minutes < 60.0:
        return num(minutes, 0) + " min"
    if minutes < q.SESSION_MIN:
        heures = minutes / 60.0
        return num(heures, 0 if heures == int(heures) else 1) + " h"
    if minutes <= q.SESSION_MIN:
        return "1 séance"
    return num(minutes / q.SESSION_MIN, 0) + " séances"


def table_exigence() -> Table:
    """Ce que chaque lecture doit valoir, et le temps qu'il faut pour le savoir."""
    rows = []
    for l in ordre():
        e = exigence(l.cle)
        rows.append([
            l.nom,
            _horizon(l.horizon_min),
            num(e.stop, 2),
            num(100.0 * e.taux_nul, 2) + " %",
            num(100.0 * e.taux_requis, 2) + " %",
            num(e.derive_requise, 3),
            _grand(e.decisions),
            _grand(e.par_an),
            _ans(e.annees),
            _grand(e.derive_requise * e.decisions),
        ])
    return Table(
        "exigence",
        "Le seuil de rentabilité de chaque lecture sur son propre horizon, et "
        "le temps que le marché met à l'établir.",
        ["Lecture", "Horizon", "a (pts)", "Taux nul", "Taux requis",
         "µ* (pt/h)", "Décisions", "Décisions par an", "Délai", "µ*·N"],
        rows,
        wide=True,
        note="La géométrie de lecture est la même partout — un stop à "
             "l'écart-type d'horizon, une cible à deux fois le stop — de sorte "
             "que seule la durée change d'une ligne à l'autre. Le taux nul "
             "vaut alors un tiers pour toutes, ce qui est le théorème d'arrêt "
             "optionnel et non une coïncidence. Deux colonnes vont en sens "
             "contraire : la dérive requise s'effondre avec l'horizon, le "
             "nombre de décisions explose. La lecture qu'on peut établir est "
             "celle qui exige le plus du marché ; celle qui n'en exige presque "
             "rien demande des millénaires. La dernière colonne est le produit "
             "des deux, et il ne bouge pas : il vaut le même nombre à cinq "
             "minutes et à trois séances, à " + num(1000.0
             * invariant("derive").etendue, 1) + " pour mille près. "
             "Il n'existe donc **aucun horizon avantageux** — seulement des "
             "façons différentes de payer la même facture.")


def table_reaction() -> Table:
    """Où va le prix après le signal, sous les deux hypothèses de dérive."""
    haute = derive_haute()
    rows = []
    vus: set[float] = set()
    for l in ordre():
        if l.horizon_min in vus:
            continue
        vus.add(l.horizon_min)
        nul = reaction(l.horizon_min, 0.0)
        der = reaction(l.horizon_min, haute)
        rows.append([
            _horizon(l.horizon_min),
            num(nul.barriere, 2),
            num(100.0 * nul.p_haut, 1) + " / " + num(100.0 * nul.p_bas, 1),
            num(100.0 * nul.p_plus_haut, 1) + " %",
            num(nul.mfe, 2) + " / " + num(nul.mae, 2),
            num(100.0 * der.p_haut, 1) + " / " + num(100.0 * der.p_bas, 1),
            num(100.0 * der.p_plus_haut, 1) + " %",
            num(der.mfe, 2) + " / " + num(der.mae, 2),
        ])
    return Table(
        "reaction",
        "Ce que le prix fait après le signal, sur l'horizon de la lecture.",
        ["Horizon", "Barrière (pts)", "Haut / bas, sans dérive (%)",
         "P(plus haut), sans dérive", "MFE / MAE, sans dérive",
         "Haut / bas à " + num(haute, 1) + " pt/h (%)",
         "P(plus haut) à " + num(haute, 1) + " pt/h",
         "MFE / MAE à " + num(haute, 1) + " pt/h"],
        rows,
        wide=True,
        note="Colonnes de gauche : le prix sans dérive. La symétrie y est "
             "exacte à la décimale publiée — les deux probabilités de barrière "
             "sont égales, l'excursion favorable vaut l'excursion défavorable, "
             "et il y a une chance sur deux d'être plus haut à l'horizon. "
             "**C'est ce que vaut n'importe quel concept qui ne déplace pas la "
             "dérive**, et c'est vrai de l'absorption comme du plus haut plus "
             "haut. Colonnes de droite : la même chose sous la dérive la plus "
             "forte que le domaine plausible autorise. L'effet est invisible à "
             "cinq minutes et massif à trois séances — l'exact inverse de ce "
             "que la table précédente déclare prouvable.")


def table_situations() -> Table:
    """Un exemple par lecture, et ce que le prix en fait."""
    haute = derive_haute()
    rows = []
    for l in ordre():
        nul = reaction(l.horizon_min, 0.0)
        der = reaction(l.horizon_min, haute)
        rows.append([
            l.nom,
            l.situation,
            l.attente,
            num(nul.fin, 2),
            num(der.fin, 2),
            num(100.0 * (der.p_plus_haut - nul.p_plus_haut), 1),
        ])
    return Table(
        "situations",
        "La situation type de chaque lecture, ce que l'opérateur en attend, "
        "et le déplacement que le prix produit ensuite.",
        ["Lecture", "La situation", "Ce qu'on en attend",
         "Déplacement médian, sans dérive", "Déplacement médian, à dérive haute",
         "Gain de probabilité (points de %)"],
        rows,
        wide=True,
        wrap_cols=[1, 2],
        note="Les deux colonnes de déplacement sont en points d'indice, "
             "mesurées du signal jusqu'à la fin de l'horizon de la lecture. "
             "Sans dérive, elles valent zéro pour les quinze lectures : c'est "
             "la même chose que dire que la reconnaissance du motif n'a rien "
             "appris. La dernière colonne est ce que la dérive haute du domaine "
             "plausible ajoute à la probabilité d'être plus haut : quatre "
             "points de pourcentage sur une lecture de cinq minutes, quarante-"
             "quatre sur une lecture de trois séances. La lecture lente voit "
             "la dérive ; la lecture rapide ne la verra jamais.")


TABLES = (table_catalogue, table_exigence, table_reaction, table_situations)


def all_tables() -> dict[str, Table]:
    return {t.__name__.removeprefix("table_"): t() for t in TABLES}


# ---------------------------------------------------------------------------
# Scalaires cités par la prose
# ---------------------------------------------------------------------------


def prouvables() -> tuple[Lecture, ...]:
    """Les lectures qu'une carrière suffit à établir."""
    return tuple(l for l in ordre() if exigence(l.cle).annees <= CARRIERE_ANS)


def frontiere() -> float:
    """Le premier horizon dont le délai dépasse la carrière, en minutes.

    Elle n'est pas nette — deux lectures d'une heure tombent de part et
    d'autre, parce que le nombre d'occasions qu'elles offrent diffère d'un
    facteur dix. C'est précisément ce que la frontière apprend : à horizon
    égal, c'est la fréquence des occasions qui décide de la prouvabilité.
    """
    for l in ordre():
        if exigence(l.cle).annees > CARRIERE_ANS:
            return l.horizon_min
    return math.inf


@dataclass(frozen=True)
class Invariant:
    """Un produit qui ne dépend pas de l'horizon, et sa dispersion."""

    moyenne: float
    etendue: float            # (max − min) / moyenne


def invariant(quoi: str = "derive") -> Invariant:
    """Le produit conservé du catalogue.

    Deux produits ne bougent pas d'un bout à l'autre des quinze lectures, et
    ils disent la même chose de deux façons :

    * `µ*·N` — ce que la lecture exige du **marché**, multiplié par ce qu'elle
      exige de l'**échantillon**. Une lecture rapide réclame une dérive deux
      cent trente fois plus forte qu'une lecture lente, et deux cent trente
      fois moins de décisions pour l'établir. Le produit ne bouge pas.
    * `bits·N` — l'information totale qu'une preuve consomme, à niveau et
      puissance déclarés. Elle vaut le même nombre de bits partout ; l'horizon
      décide seulement sur combien de décisions il faut l'étaler.

    Il n'y a donc **aucun horizon avantageux**. Choisir une lecture rapide,
    c'est acheter de la prouvabilité en payant en exigence de dérive ; choisir
    une lecture lente, l'inverse. Le catalogue n'offre pas un menu de qualités
    inégales : il offre un menu de devises.

    **D'où vient la conservation, et jusqu'où elle porte.** Ce n'est pas une
    propriété de l'horizon mais de la **largeur de stop**, à rapport gain-risque
    et friction fixés : le nombre de décisions croît comme `a²` — il vaut
    `1/(p₁ − p₀)²` et l'écart de taux est proportionnel à `c/a` — tandis que la
    dérive requise décroît comme `1/a²`. Le produit est donc constant sur toute
    la famille des géométries, et il l'est encore mieux que sur le catalogue :
    d'un stop d'un point à un stop de cent cinquante, il ne bouge que d'un
    quart de pour cent. L'horizon n'y entre que parce que la géométrie de
    lecture pose `a = σ√T` ; c'est la déclaration qui relie les deux, et elle
    est écrite, pas découverte.
    """
    vals = []
    for l in ordre():
        e = exigence(l.cle)
        vals.append(e.derive_requise * e.decisions if quoi == "derive"
                    else e.bits * e.decisions)
    moy = sum(vals) / len(vals)
    return Invariant(moy, (max(vals) - min(vals)) / moy)


def values() -> dict[str, str]:
    rang = ordre()
    rapide, lent = rang[0], rang[-1]
    e_rapide, e_lent = exigence(rapide.cle), exigence(lent.cle)
    haute = derive_haute()
    r_rapide_nul = reaction(rapide.horizon_min, 0.0)
    r_rapide = reaction(rapide.horizon_min, haute)
    r_lent_nul = reaction(lent.horizon_min, 0.0)
    r_lent = reaction(lent.horizon_min, haute)
    seance_nul = reaction(q.SESSION_MIN, 0.0)
    seance = reaction(q.SESSION_MIN, haute)
    ok = prouvables()

    out = {
        "c_lectures": str(len(CATALOGUE)),
        "c_familles": str(len({l.famille for l in CATALOGUE})),
        "c_rr_lecture": num(RR_LECTURE, 0),
        "c_k_barriere": num(K_BARRIERE, 2),
        "c_carriere": num(CARRIERE_ANS, 0),
        "c_derive_haute": num(haute, 1),
        "c_seances_sim": _grand(float(SEANCES)),
        "c_friction": num(friction(), 2),
        "c_taux_nul": num(100.0 / (1.0 + RR_LECTURE), 2) + "&nbsp;%",

        "c_rapide": rapide.nom.lower(),
        "c_rapide_horizon": _horizon(rapide.horizon_min),
        "c_rapide_mu": num(e_rapide.derive_requise, 2),
        "c_rapide_decisions": _grand(e_rapide.decisions),
        "c_rapide_par_an": _grand(e_rapide.par_an),
        "c_rapide_delai": _ans(e_rapide.annees),
        "c_rapide_gain": num(100.0 * (r_rapide.p_plus_haut
                                      - r_rapide_nul.p_plus_haut), 1),

        "c_lent": lent.nom.lower(),
        "c_lent_horizon": _horizon(lent.horizon_min),
        "c_lent_mu": num(e_lent.derive_requise, 3),
        "c_lent_decisions": _grand(e_lent.decisions),
        "c_lent_par_an": _grand(e_lent.par_an),
        "c_lent_delai": _ans(e_lent.annees),
        "c_lent_gain": num(100.0 * (r_lent.p_plus_haut
                                    - r_lent_nul.p_plus_haut), 1),

        "c_ratio_mu": num(e_rapide.derive_requise / e_lent.derive_requise, 0),
        "c_ratio_decisions": num(e_lent.decisions / e_rapide.decisions, 0),
        "c_prouvables": str(len(ok)),
        "c_hors_portee": str(len(CATALOGUE) - len(ok)),
        "c_frontiere": _horizon(frontiere()),

        "c_p_desequilibre": num(100.0 * frequence_nulle("desequilibre"), 1),
        "c_occ_desequilibre": _grand(occasions("desequilibre")),
        "c_p_lvn": num(100.0 * frequence_nulle("lvn"), 1),
        "c_p_structure": num(100.0 * frequence_nulle("structure"), 1),
        "c_p_extreme": num(100.0 * frequence_nulle("extreme"), 1),
        "c_p_gamma": num(100.0 * frequence_nulle("gamma"), 1),
        "c_p_absorption": num(100.0 * frequence_nulle("absorption"), 1),
        "c_p_epuisement": num(100.0 * frequence_nulle("epuisement"), 1),

        "c_seance_mfe": num(seance.mfe, 1),
        "c_seance_mae": num(abs(seance.mae), 1),
        "c_seance_mfe_nul": num(seance_nul.mfe, 1),
        "c_seance_p": num(100.0 * seance.p_plus_haut, 1),

        "c_invariant_mu": _grand(invariant("derive").moyenne),
        "c_invariant_mu_etendue": num(100.0 * invariant("derive").etendue, 2),
        "c_invariant_bits": num(invariant("bits").moyenne, 2),
        "c_invariant_bits_etendue": num(100.0 * invariant("bits").etendue, 2),
    }
    return out


def main() -> None:
    print(f"catalogue : {len(CATALOGUE)} lectures, "
          f"{len(prouvables())} prouvables en {CARRIERE_ANS:.0f} ans\n")
    for table in TABLES:
        t = table()
        print(t.to_text())
        print()


if __name__ == "__main__":
    main()
