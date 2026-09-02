"""Un niveau a une largeur, et personne ne la publie.

Ce module part d'un objet extérieur : un guide d'options qui traite le gamma
des teneurs de marché, et qui fait une chose que la vulgarisation ne fait
jamais — il publie le résultat de son propre test. Sur plusieurs années de
séances de futures sur indice, l'issue de retournement mesurée **contre un
niveau témoin placé à la même distance de l'ouverture**, les niveaux dérivés
du gamma ne portent aucune information mesurable. Ni le niveau de bascule, ni
la classification de régime, ni la concentration de gamma par strike ne
battent le témoin.

Le protocole du dépôt reprend cela et en tire quatre choses que le guide ne
calcule pas.

I. Le contrôle apparié en distance
----------------------------------
C'est la loi nulle correcte pour **tout** niveau, et elle manquait au
catalogue de la partie III. Un niveau à distance `d` de l'ouverture est touché
à un taux que le principe de réflexion donne exactement ; et une fois touché,
il « tient » à un taux que le théorème d'arrêt optionnel donne exactement,
`a/(a+b)`. Publier « le prix a retourné sur le niveau 62 % du temps » ne dit
rien tant que le taux du témoin n'est pas publié à côté.

De là sort une identité fermée, et c'est le résultat de la partie :

    l'excès requis      δ  = (c/a)/(1 + R:R)
    les touches requises n  = z²·(R:R)·(a/c)²

**L'avantage exigé décroît comme la friction relative, et l'échantillon croît
comme son carré.** Élargir le stop rend l'exigence petite et la preuve
impossible — c'est le budget d'information de la partie IV, retrouvé par une
route entièrement différente, et les deux routes s'accordent à 25 %.

II. La largeur
--------------
Le guide dit une phrase que personne ne convertit en nombre : *gamma n'est pas
un nombre, c'est un lieu*. La courbure vit à moins d'un écart-type du strike
et s'annule au-delà. Cet écart-type se calcule : la demi-largeur à mi-hauteur
de `φ(d₁)` vaut `√(2 ln 2)·σ√T`, soit 1,177 σ√T en log-moneyness.

Un niveau qui a une largeur ne se trade pas avec un stop plus étroit qu'elle,
et la raison est exacte : depuis le niveau, la probabilité de toucher `−a`
avant de sortir de la bande vaut `w/(a+w)`. **Quand la bande est large devant
le stop, ce n'est plus le marché qui invalide, c'est la bande.**

III. La géométrie que la largeur force
--------------------------------------
Si le stop doit valoir la largeur, la largeur choisit la géométrie, donc `µ*`,
donc l'échantillon. Le module le calcule pour chacune des lectures du
catalogue et rend un verdict contre le domaine de dérive plausible.

IV. L'identité gamma-thêta
--------------------------
`Θ + ½σ²S²Γ + (r−q)SΔ = rV` est l'équation de Black-Scholes, et pour un livre
couvert en delta à taux nul elle se réduit à `Θ = −½σ²S²Γ`. Le mouvement
d'équilibre quotidien vaut alors `σ/√365` **exactement, à toute échéance et à
tout strike**. C'est le théorème d'arrêt optionnel du marché d'options : aucune
échéance ne crée d'espérance, le vendeur facture exactement la courbure au
prix de la volatilité implicite. Le guide trace cette courbe et la voit monter
de 1,32 à 1,39 % ; le module montre que la montée est l'écart entre le thêta
instantané et la réévaluation exacte à un jour, et le chiffre.

V. Le signe que la reconstruction jette
---------------------------------------
`GEX = Σ Γᵢ·OIᵢ·m·S²·(1 %)·signᵢ` suppose le signe. L'intérêt ouvert n'en porte
aucun. Le module simule l'ignorance — une fraction seulement des strikes dont
le signe est connu — et rend la bande dans laquelle le niveau de bascule se
promène. C'est le mécanisme du résultat négatif du guide, calculé au lieu
d'être affirmé.
"""

from __future__ import annotations

import math
import zlib
from dataclasses import dataclass
from functools import lru_cache

from . import quant as q
from . import seuil
from .costs import COST_BASE, ES, _norm_ppf, norm_cdf
from .entropy import required_bits, trades_for_information
from .horizon import outcome
from .mc import Rng
from .report import Table, num

SEED = 20260906

ALPHA = 0.05
PUISSANCE = 0.80
#: `z_{α/2} + z_β` — le même facteur que la partie XVIII.
FACTEUR = _norm_ppf(1.0 - ALPHA / 2.0) + _norm_ppf(PUISSANCE)

SESSIONS_PAR_AN = 252.0

#: La friction déclarée du dépôt, en points d'aller-retour.
FRICTION = COST_BASE.friction_points(ES)

#: L'écart-type d'une séance entière, en points puis en fraction du niveau.
SIGMA_SEANCE = q.SIGMA_1MIN * math.sqrt(q.SESSION_MIN)
SIGMA_SEANCE_PCT = SIGMA_SEANCE / q.INDEX_LEVEL


def _graine(cle: str) -> int:
    """Une graine dérivée d'un nom, par digest explicite.

    Jamais `hash` : il est randomisé par processus, et c'est le piège que la
    partie XIV a payé.
    """
    return SEED ^ (zlib.crc32(cle.encode("utf-8")) & 0xFFFF)


# ---------------------------------------------------------------------------
# I. Le contrôle apparié en distance
# ---------------------------------------------------------------------------


def taux_de_touche(distance_pts: float, minutes: float = q.SESSION_MIN,
                   sigma: float = q.SIGMA_1MIN) -> float:
    """Probabilité qu'un niveau à `distance_pts` soit touché avant la clôture.

    Principe de réflexion, forme fermée exacte : le maximum d'une marche sans
    dérive dépasse `d` avec probabilité `2Φ(−d/σ√T)`. C'est la moitié du
    contrôle — un niveau lointain est rarement touché, et un niveau proche
    l'est presque toujours, quel que soit ce qu'il prétend marquer.
    """
    if distance_pts <= 0.0:
        return 1.0
    return 2.0 * norm_cdf(-distance_pts / (sigma * math.sqrt(minutes)))


def taux_de_reussite(stop_pts: float, cible_pts: float,
                     minutes: float = q.SESSION_MIN,
                     sigma: float = q.SIGMA_1MIN) -> float:
    """Le taux de réussite d'un trade pris sur le niveau, sous prix sans dérive.

    Entrée au niveau, invalidation à `stop_pts` de l'autre côté, objectif à
    `cible_pts`. Le théorème d'arrêt optionnel rend `a/(a+b)` dans le problème
    non borné ; la séance tronque, et `horizon.outcome` donne la valeur
    exacte. Le contrôle du module est que les deux coïncident quand la séance
    est longue devant les barrières.
    """
    return outcome(stop_pts, cible_pts, minutes, sigma).p_target


def taux_de_reussite_ferme(stop_pts: float, cible_pts: float) -> float:
    """`a/(a+b)` — la forme fermée, contrôlée contre la précédente."""
    return stop_pts / (stop_pts + cible_pts)


def taux_de_tenue(retrait_pts: float, extension_pts: float,
                  minutes: float = q.SESSION_MIN,
                  sigma: float = q.SIGMA_1MIN) -> float:
    """Le taux auquel un niveau « tient », **selon la définition qu'on en donne**.

    C'est le piège de toute statistique de niveau, et il n'a rien de subtil :
    « le prix a retourné sur le niveau » n'est pas une observation tant que
    les deux distances ne sont pas déclarées. Tenir, c'est reculer de
    `retrait_pts` avant d'étendre de `extension_pts`, et l'arrêt optionnel
    rend `extension/(retrait + extension)`.

    **Le taux dépasse un demi dès que l'extension exigée dépasse le retrait**,
    sous prix sans dérive et sans qu'aucun niveau n'existe. Une méthode qui
    demande un recul de quelques ticks avant une extension d'un point
    rapportera quatre-vingts pour cent de réussite sur du bruit pur.
    """
    return outcome(extension_pts, retrait_pts, minutes, sigma).p_target


def taux_de_tenue_ferme(retrait_pts: float, extension_pts: float) -> float:
    """`e/(r+e)` — la forme fermée du taux de tenue."""
    return extension_pts / (retrait_pts + extension_pts)


def exces_requis(friction_ratio: float, rr: float = q.RR_REF) -> float:
    """`δ = (c/a)/(1 + R:R)` — l'excès qu'un niveau doit montrer sur son témoin.

    Le taux nul vaut `1/(1+R:R)` et le taux d'équilibre `(1+c/a)/(1+R:R)` :
    la différence est immédiate, et elle ne dépend **que** de la friction
    relative. Un niveau qui ne bat pas son témoin de cet écart-là ne paie pas
    sa friction, quelle que soit la qualité de sa lecture.
    """
    return friction_ratio / (1.0 + rr)


def touches_requises(friction_ratio: float, rr: float = q.RR_REF) -> float:
    """`n = z²·(R:R)·(a/c)²` — les touches nécessaires pour l'établir.

    Deux proportions, dont une gratuite : le témoin se simule autant qu'on
    veut, donc seule la branche du niveau est rare. La simplification est
    exacte parce que `p₀(1−p₀)(1+R:R)² = R:R`.

    Le résultat structurant tient dans l'exposant : **l'échantillon croît
    comme le carré de l'inverse de la friction relative.** Élargir le stop
    divise l'exigence et multiplie la preuve par son carré.
    """
    if friction_ratio <= 0.0:
        return math.inf
    return FACTEUR ** 2 * rr / friction_ratio ** 2


def touches_par_information(friction_ratio: float,
                            rr: float = q.RR_REF) -> float:
    """La même quantité par la route d'information, pour la contrôler."""
    r = required_bits(rr, friction_ratio)
    return trades_for_information(r.bits)


#: Distances balayées, en fractions de l'écart-type de séance.
DISTANCES: tuple[float, ...] = (0.15, 0.30, 0.50, 0.75, 1.00, 1.50)


def table_temoin() -> Table:
    rows = []
    reussite = taux_de_reussite(q.STOP_PTS, q.RR_REF * q.STOP_PTS)
    for k in DISTANCES:
        d = k * SIGMA_SEANCE
        rows.append([
            num(k, 2),
            num(d, 1),
            num(100 * d / q.INDEX_LEVEL, 3),
            num(100 * taux_de_touche(d), 1),
            num(100 * reussite, 2),
        ])
    ferme = taux_de_reussite_ferme(q.STOP_PTS, q.RR_REF * q.STOP_PTS)
    return Table(
        key="niv_temoin",
        caption="Ce qu'un niveau témoin rend, à la seule distance",
        headers=["Distance (σ de séance)", "Distance (points)",
                 "Distance (%)", "Touché avant la clôture (%)",
                 "Réussite du trade pris dessus (%)"],
        rows=rows,
        note="Aucun niveau n'entre dans cette table : elle ne contient que la "
             "**distance**. Le taux de touche est celui du principe de "
             "réflexion, exact, et il ne dit rien d'autre que la distance. La "
             "dernière colonne est celle qui compte, et elle est "
             "**constante** : le taux de réussite d'un trade pris sur le "
             "niveau vaut " + num(100 * ferme, 2) + " % en forme fermée non "
             "bornée contre " + num(100 * reussite, 2) + " % avec la "
             "troncature de séance, et il ne dépend ni de la distance, ni de "
             "ce que le niveau prétend marquer, ni de la façon dont il a été "
             "construit. L'accord des deux routes est le contrôle du module. "
             "*Un niveau ne se juge que contre un témoin placé à la même "
             "distance* — et c'est exactement le protocole que le guide "
             "d'options extérieur applique, pour ne rien trouver.",
    )


#: Définitions de « le niveau a tenu », en couples (retrait, extension) mesurés
#: en points. Aucune n'est plus légitime qu'une autre ; c'est le propos.
DEFINITIONS: tuple[tuple[str, float, float], ...] = (
    ("Recul et extension symétriques", 2.0, 2.0),
    ("Recul de deux points, extension d'un", 2.0, 1.0),
    ("Recul d'un point, extension de deux", 1.0, 2.0),
    ("Recul d'un tick, extension d'un point", 0.25, 1.0),
    ("Recul d'un tick, extension de quatre points", 0.25, 4.0),
)


def table_definition() -> Table:
    rows = []
    for nom, r, e in DEFINITIONS:
        borne = taux_de_tenue(r, e)
        rows.append([
            nom,
            num(r, 2),
            num(e, 2),
            num(100 * taux_de_tenue_ferme(r, e), 1),
            num(100 * borne, 1),
            num(100 * (borne - 0.5), 1, signed=True),
        ])
    return Table(
        key="niv_definition",
        caption="Le taux de tenue d'un niveau qui n'existe pas",
        headers=["Définition retenue", "Recul exigé (points)",
                 "Extension exigée (points)", "Taux nul, forme fermée (%)",
                 "Taux nul, séance bornée (%)", "Écart à un demi"],
        rows=rows,
        note="Toutes ces lignes sont mesurées sur un **prix sans dérive**, et "
             "aucun niveau n'y figure. Le taux de tenue vaut "
             "`e/(r+e)` : il dépasse un demi dès que l'extension exigée "
             "dépasse le recul, et il atteint "
             + num(100 * taux_de_tenue_ferme(DEFINITIONS[-1][1],
                                             DEFINITIONS[-1][2]), 0)
             + " % à la dernière ligne. **C'est la raison pour laquelle tout "
             "niveau publié « fonctionne »** : la définition du retournement "
             "est asymétrique, et l'asymétrie suffit. Une statistique de "
             "niveau qui ne publie pas ses deux distances ne publie rien du "
             "tout, et un taux de soixante-quinze pour cent y est le "
             "résultat *attendu sous l'hypothèse nulle*, pas une découverte.",
        wrap_cols=[0],
    )


#: Les deux géométries que le document oppose depuis la partie X.
GEOMETRIES: tuple[tuple[str, float], ...] = (
    ("Géométrie déclarée", 0.010),
    ("Stop élargi", 0.150),
)

#: Largeurs de stop balayées pour l'exigence et l'échantillon.
STOPS: tuple[float, ...] = (0.010, 0.025, 0.050, 0.100, 0.150, 0.300)


def cloture_avant_barriere(stop_pts: float, rr: float = q.RR_REF) -> float:
    """`p_open` — la part des trades qui atteignent la clôture sans barrière.

    C'est la **condition** sous laquelle tout ce qui précède vaut. Le taux nul
    `1/(1+R:R)` et l'identité qui en découle supposent le problème non borné ;
    la séance finit, et un trade qui n'a touché aucune barrière sort à la
    clôture. Tant que cette part est négligeable, les deux lois coïncident.
    Quand elle ne l'est plus, `a/(a+b)` cesse d'être le taux du témoin — et
    c'est exactement la condition que la partie sur le régime de gamma avait
    déjà dû ajouter après que quatre tests eurent refusé sa première version.
    """
    return outcome(stop_pts, rr * stop_pts, q.SESSION_MIN, q.SIGMA_1MIN).p_open


def table_exigence() -> Table:
    rows = []
    p0 = 1.0 / (1.0 + q.RR_REF)
    for pct in STOPS:
        g = seuil.geometry(pct)
        d = exces_requis(g.friction_ratio)
        n = touches_requises(g.friction_ratio)
        ni = touches_par_information(g.friction_ratio)
        po = cloture_avant_barriere(g.stop_points)
        rows.append([
            num(pct, 3),
            num(g.stop_points, 2),
            num(g.friction_ratio, 4),
            num(100 * p0, 2),
            num(100 * po, 1),
            num(100 * d, 3, signed=True),
            num(n, 0),
            num(ni, 0),
        ])
    g0 = seuil.geometry(0.010)
    g1 = seuil.geometry(0.150)
    return Table(
        key="niv_exigence",
        caption="Ce qu'un niveau doit battre, et ce que la preuve coûte",
        headers=["Stop (%)", "Stop (points)", "Friction relative c/a",
                 "Taux du témoin (%)", "Clôture avant barrière (%)",
                 "Excès requis (points de taux)", "Touches requises",
                 "Par la route d'information"],
        rows=rows,
        note="Le taux du témoin est **constant** — `1/(1+R:R)` ne dépend que "
             "du rapport gain/risque déclaré. L'excès requis, lui, ne dépend "
             "que de la friction relative, et l'échantillon comme son carré. "
             "Les deux colonnes de droite sont deux routes indépendantes vers "
             "la même quantité : la forme fermée de ce module, et le budget "
             "d'information de la partie IV. Elles s'accordent à "
             + num(100 * abs(touches_requises(g0.friction_ratio)
                             / touches_par_information(g0.friction_ratio)
                             - 1.0), 0) + " % à la géométrie déclarée et à "
             + num(100 * abs(touches_requises(g1.friction_ratio)
                             / touches_par_information(g1.friction_ratio)
                             - 1.0), 0) + " % au stop élargi, ce qui est le "
             "contrôle qui autorise à publier la forme fermée. **Le fait à "
             "retenir est le renversement** : élargir le stop divise "
             "l'exigence par "
             + num(exces_requis(g0.friction_ratio)
                   / exces_requis(g1.friction_ratio), 0) + " et multiplie "
             "l'échantillon par "
             + num(touches_requises(g1.friction_ratio)
                   / touches_requises(g0.friction_ratio), 0) + ". *Rendre "
             "l'exigence petite la rend indémontrable*, et c'est le résultat "
             "de la partie IV retrouvé sans jamais parler d'information. La "
             "cinquième colonne porte la **condition** sous laquelle tout "
             "cela vaut, et elle n'est pas décorative : le taux du témoin est "
             "celui du problème non borné, et la séance finit. Tant que la "
             "clôture avant barrière reste négligeable — "
             + num(100 * cloture_avant_barriere(g0.stop_points), 2)
             + " % à la géométrie déclarée — les deux lois coïncident. À "
             + num(STOPS[-1], 3) + " % elle vaut "
             + num(100 * cloture_avant_barriere(
                 seuil.geometry(STOPS[-1]).stop_points), 0) + " % et le taux "
             "du témoin n'est plus " + num(100 * p0, 2) + " % du tout&nbsp;: "
             "**les deux dernières lignes de cette table sont un ordre de "
             "grandeur, pas une mesure.**",
    )


def surface_exigence() -> list[list[float]]:
    """Le logarithme des touches requises, sur (stop, rapport gain/risque).

    Les deux axes agissent dans le même sens et pour la même raison : un stop
    large et un rapport ambitieux rendent tous deux l'exigence petite, donc la
    preuve longue. Le sommet est au fond, au coin du stop le plus large et du
    rapport le plus grand.
    """
    return [[math.log10(touches_requises(seuil.geometry(p).friction_ratio, r))
             for r in SURF_RR]
            for p in SURF_STOP]


SURF_STOP: tuple[float, ...] = (0.300, 0.200, 0.100, 0.050, 0.025, 0.010)
SURF_RR: tuple[float, ...] = (30.0, 20.0, 12.0, 6.0, 3.0, 1.0)


# ---------------------------------------------------------------------------
# II. La largeur d'un niveau
# ---------------------------------------------------------------------------

#: `√(2 ln 2)` — la demi-largeur à mi-hauteur d'une densité normale, en
#: écarts-types. C'est la constante qui convertit « gamma vit à un écart-type
#: du strike » en un nombre de points.
DEMI_HAUTEUR = math.sqrt(2.0 * math.log(2.0))

#: Volatilité annuelle de référence pour les échéances d'options.
VOL_ANNUELLE = 0.25

JOURS_AN = 365.0


def largeur_gamma(jours: float, vol: float = VOL_ANNUELLE,
                  niveau: float = q.INDEX_LEVEL) -> float:
    """La demi-largeur de la bande de gamma, en points.

    `Γ ∝ φ(d₁)/Sσ√T` : la courbure tombe à la moitié de son sommet quand
    `|d₁| = √(2 ln 2)`, soit à `1,177·σ√T` en log-moneyness. Le nombre rendu
    est cette demi-largeur convertie en points du contrat.

    C'est la phrase du guide — *gamma n'est pas un nombre, c'est un lieu* —
    rendue opposable. Un livre dont le gamma est à trois pour cent et un livre
    de même gamma à la monnaie ne portent pas le même risque, et la distance
    qui les sépare se compare à la largeur du stop qui prétend les trader.
    """
    if jours <= 0.0:
        return 0.0
    t = jours / JOURS_AN
    return niveau * (math.exp(DEMI_HAUTEUR * vol * math.sqrt(t)) - 1.0)


def invalidation_prematuree(largeur_pts: float, stop_pts: float) -> float:
    """`w/(a+w)` — la probabilité que le stop parle avant le niveau.

    Depuis le niveau, sous prix sans dérive, la probabilité de toucher `−a`
    avant de sortir de la bande de demi-largeur `w` vaut `w/(a+w)` par arrêt
    optionnel. Quand la bande est large devant le stop, ce nombre tend vers un
    et **l'invalidation cesse de mesurer le niveau** : elle mesure le bruit
    à l'intérieur de la bande.
    """
    if largeur_pts <= 0.0:
        return 0.0
    return largeur_pts / (stop_pts + largeur_pts)


@dataclass(frozen=True)
class Niveau:
    """Une lecture du catalogue, et la largeur de ce qu'elle marque."""

    cle: str
    nom: str
    origine: str
    largeur_pts: float
    #: D'où vient la largeur — une mécanique, ou le choix d'un ancrage.
    nature: str
    #: Le nom court, pour la gouttière d'une planche. Un nom de vingt
    #: caractères tient dans la marge ; un nom de trente la déborde et vient
    #: se faire barrer par les traits verticaux du cadre.
    court: str = ""

    def rapport(self, stop_pts: float) -> float:
        return self.largeur_pts / stop_pts

    def tradable(self, stop_pts: float, seuil_p: float = 0.5) -> bool:
        """Verdict **calculé** : le stop parle-t-il avant le niveau ?"""
        return invalidation_prematuree(self.largeur_pts, stop_pts) < seuil_p


#: La rangée d'un profil, en points. C'est le paramètre non observable dont
#: la partie III a déjà montré qu'il décide de tout : entre un quart de point
#: et trois points, la fréquence nulle d'un extrême pauvre passe de 5 à 37 %.
RANGEE_PROFIL = 1.0

#: Le tick du contrat.
TICK = 0.25

N_ANCRAGE = 400


@lru_cache(maxsize=4)
def largeur_d_ancrage(n: int = N_ANCRAGE, seed: int = SEED + 3) -> float:
    """L'écart entre les retracements de Fibonacci des balancements plausibles.

    Un retracement n'a pas de largeur mécanique : c'est un prix exact. Sa
    largeur vient d'ailleurs, et de plus loin — du **choix du balancement**.
    Sur une séance sans dérive, plusieurs balancements dépassent le seuil
    d'amplitude au-dessus duquel un opérateur les retiendrait, et chacun donne
    son 61,8 %. Le nombre rendu est l'écart-type de ces niveaux, c'est-à-dire
    la largeur que le choix fabrique.

    Le point n'est pas que la méthode soit mauvaise : c'est qu'une largeur
    d'ancrage est une largeur comme une autre, et qu'elle se compare au stop
    de la même façon.
    """
    rng = Rng(seed)
    pas = int(q.SESSION_MIN)
    seuil_amp = 0.35 * SIGMA_SEANCE
    ecarts: list[float] = []
    for _ in range(n):
        x = 0.0
        chemin = [0.0]
        for _ in range(pas):
            x += q.SIGMA_1MIN * rng.gauss()
            chemin.append(x)
        # Les balancements retenus : chaque couple (creux, sommet) séparé d'au
        # moins le seuil d'amplitude, pris sur des fenêtres emboîtées.
        niveaux = []
        for fin in range(60, pas + 1, 30):
            seg = chemin[:fin + 1]
            bas, haut = min(seg), max(seg)
            if haut - bas >= seuil_amp:
                niveaux.append(haut - 0.618 * (haut - bas))
        if len(niveaux) >= 2:
            m = sum(niveaux) / len(niveaux)
            v = sum((z - m) ** 2 for z in niveaux) / (len(niveaux) - 1)
            ecarts.append(math.sqrt(v))
    ecarts.sort()
    return ecarts[len(ecarts) // 2] if ecarts else 0.0


@lru_cache(maxsize=1)
def niveaux() -> tuple[Niveau, ...]:
    """Les lectures du catalogue, rangées par largeur **calculée**.

    L'ordre n'est écrit nulle part : il sort du tri, et un test l'exige.
    """
    bruts = [
        Niveau("gamma0", "Gamma, deux heures d'échéance", "Dérivés",
               largeur_gamma(2.0 / 24.0), "mécanique", "gamma, 2 h"),
        Niveau("gamma1", "Gamma, un jour d'échéance", "Dérivés",
               largeur_gamma(1.0), "mécanique", "gamma, 1 j"),
        Niveau("gamma30", "Gamma, trente jours d'échéance", "Dérivés",
               largeur_gamma(30.0), "mécanique", "gamma, 30 j"),
        Niveau("vwap", "VWAP et sa bande à un sigma", "Exécution",
               SIGMA_SEANCE / math.sqrt(3.0), "mécanique", "VWAP, bande"),
        Niveau("poc", "Point de contrôle du profil", "Profil de volume",
               RANGEE_PROFIL, "réglage d'affichage", "point de contrôle"),
        Niveau("lvn", "Nœud de faible volume", "Profil de volume",
               2.0 * RANGEE_PROFIL, "réglage d'affichage", "nœud de volume"),
        Niveau("fibo", "Retracement de Fibonacci", "Structure",
               largeur_d_ancrage(), "choix d'ancrage", "Fibonacci"),
        Niveau("overnight", "Extrême de la session overnight", "Structure",
               TICK, "exact", "extrême overnight"),
        Niveau("footprint", "Déséquilibre de footprint", "Flux d'ordres",
               TICK, "exact", "footprint"),
    ]
    return tuple(sorted(bruts, key=lambda x: (x.largeur_pts, x.cle)))


def table_largeur() -> Table:
    a0 = q.STOP_PTS
    a1 = seuil.geometry(0.150).stop_points
    rows = []
    for x in niveaux():
        rows.append([
            x.nom,
            x.nature,
            num(x.largeur_pts, 2),
            num(100 * x.largeur_pts / q.INDEX_LEVEL, 3),
            num(x.rapport(a0), 1),
            num(100 * invalidation_prematuree(x.largeur_pts, a0), 1),
            num(100 * invalidation_prematuree(x.largeur_pts, a1), 1),
        ])
    return Table(
        key="niv_largeur",
        caption="La largeur de ce que chaque lecture marque, et ce qu'elle coûte au stop",
        headers=["Lecture", "D'où vient la largeur", "Demi-largeur (points)",
                 "En % du niveau", "Rapport à la géométrie déclarée",
                 "Le stop parle avant le niveau, stop déclaré (%)",
                 "au stop élargi (%)"],
        rows=rows,
        note="L'ordre des lignes est **calculé** — les lectures sont triées "
             "par largeur croissante, et rien n'est écrit à la main. Trois "
             "natures se distinguent, et c'est la lecture utile de la table. "
             "Une largeur **mécanique** est une propriété du phénomène : "
             "gamma vit à `√(2 ln 2)·σ√T` du strike, et cela ne se négocie "
             "pas. Un **réglage d'affichage** est une largeur qu'on choisit "
             "sans le savoir, et la partie III a déjà montré qu'il décide de "
             "la rareté de ce qu'on lit. Un **choix d'ancrage** est une "
             "largeur que la méthode fabrique : le retracement est un prix "
             "exact, mais le balancement retenu ne l'est pas. La dernière "
             "colonne est le nombre qu'aucune méthode de niveaux ne publie : "
             "*la probabilité que le stop parle avant le niveau*. Au-dessus "
             "de cinquante pour cent, l'invalidation ne mesure plus le "
             "niveau, elle mesure le bruit dans sa bande.",
        wrap_last=False,
        wrap_cols=[0, 1],
    )


SURF_LARGEUR: tuple[float, ...] = (30.0, 12.0, 5.0, 2.0, 0.8, 0.3)
SURF_STOP_PTS: tuple[float, ...] = (0.3, 0.6, 1.5, 3.0, 6.0, 12.0)


def surface_invalidation() -> list[list[float]]:
    """`w/(a+w)`, sur (largeur du niveau, largeur du stop).

    Le sommet est au fond : niveau le plus large, stop le plus étroit. La
    ligne de niveau à cinquante pour cent est la diagonale `w = a`, et c'est
    la seule chose à regarder — au-dessus d'elle, l'invalidation appartient à
    la bande et non au marché.
    """
    return [[invalidation_prematuree(w, a) for a in SURF_STOP_PTS]
            for w in SURF_LARGEUR]


# ---------------------------------------------------------------------------
# III. La géométrie que la largeur force
# ---------------------------------------------------------------------------


#: Le nombre d'occasions d'une carrière, borne optimiste : une par séance
#: pendant quarante ans. C'est la borne contre laquelle le verdict de preuve
#: est calculé, et elle est généreuse par construction.
TOUCHES_CARRIERE = 40.0 * SESSIONS_PAR_AN


def geometrie_forcee(largeur_pts: float) -> seuil.Geometry:
    """La géométrie qu'un niveau de largeur `w` impose : `a = w`."""
    return seuil.geometry(100.0 * largeur_pts / q.INDEX_LEVEL)


def passe_les_deux() -> tuple[Niveau, ...]:
    """Les lectures dont la géométrie forcée passe les **deux** verdicts.

    Rien n'est écrit : on recompte. C'est le résultat de la section, et il est
    d'autant plus utile qu'il est court.
    """
    hi = seuil.PLAUSIBLE_DRIFT_PER_HOUR[1]
    out = []
    for x in niveaux():
        g = geometrie_forcee(x.largeur_pts)
        if (g.break_even_per_hour <= hi
                and touches_requises(g.friction_ratio) <= TOUCHES_CARRIERE):
            out.append(x)
    return tuple(out)


def table_forcee() -> Table:
    lo, hi = seuil.PLAUSIBLE_DRIFT_PER_HOUR
    rows = []
    for x in niveaux():
        g = geometrie_forcee(x.largeur_pts)
        n = touches_requises(g.friction_ratio)
        rows.append([
            x.nom,
            num(g.stop_points, 2),
            num(g.exposure_min, 1),
            num(g.break_even_per_hour, 3),
            "dans le domaine" if g.break_even_per_hour <= hi
            else "hors du domaine",
            num(n, 0),
            "à portée" if n <= TOUCHES_CARRIERE else "hors d'une carrière",
        ])
    return Table(
        key="niv_forcee",
        caption="Ce que la largeur d'un niveau impose à la géométrie",
        headers=["Lecture", "Stop forcé (points)", "Temps de marché (min)",
                 "µ* requis (pt/h)", "Verdict sur µ*", "Touches requises",
                 "Verdict sur la preuve"],
        rows=rows,
        note="Si l'invalidation doit appartenir au marché et non à la bande, "
             "alors le stop vaut la largeur, et la largeur choisit tout le "
             "reste. Le verdict de la quatrième colonne est **calculé** "
             "contre le domaine de dérive plausible [" + num(lo, 1) + " ; "
             + num(hi, 1) + "] pt/h, jamais écrit. La lecture est en deux "
             "temps et le second contredit le premier. Un niveau large "
             "*abaisse* `µ*`, parce qu'un stop large achète du temps de "
             "marché — c'est le levier de la partie X, et il joue ici aussi. "
             "Mais il fait exploser l'échantillon, parce que l'exigence "
             "devient minuscule et que la preuve croît comme son carré. "
             "**La largeur d'un niveau ne rend pas le trade impossible : elle "
             "rend impossible de savoir s'il marche.** Les deux verdicts sont "
             "calculés et ils se contredisent ligne après ligne : les "
             "lectures étroites échouent sur `µ*`, les lectures larges "
             "échouent sur la preuve, et la fenêtre où les deux passent tient "
             "en " + num(len(passe_les_deux()), 0) + " ligne sur "
             + num(len(niveaux()), 0) + " — "
             + ", ".join(x.nom.lower() for x in passe_les_deux())
             + ". Le compte est recalculé, jamais écrit. Le second "
             "verdict compare à " + num(TOUCHES_CARRIERE, 0) + " occasions, "
             "soit une par séance pendant quarante ans — une borne "
             "**optimiste**, puisqu'un niveau donné n'est pas touché à chaque "
             "séance.",
        wrap_cols=[0],
    )


# ---------------------------------------------------------------------------
# IV. L'identité gamma-thêta
# ---------------------------------------------------------------------------


def _phi(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _d1(s: float, k: float, vol: float, t: float) -> float:
    return (math.log(s / k) + 0.5 * vol * vol * t) / (vol * math.sqrt(t))


def call(s: float, k: float, vol: float, t: float) -> float:
    """Prix d'un call à taux nul — tout ce dont le module a besoin."""
    if t <= 0.0:
        return max(s - k, 0.0)
    d1 = _d1(s, k, vol, t)
    d2 = d1 - vol * math.sqrt(t)
    return s * norm_cdf(d1) - k * norm_cdf(d2)


def gamma(s: float, k: float, vol: float, t: float) -> float:
    """`Γ = φ(d₁)/(Sσ√T)`."""
    if t <= 0.0:
        return 0.0
    return _phi(_d1(s, k, vol, t)) / (s * vol * math.sqrt(t))


def theta_instantane(s: float, k: float, vol: float, t: float) -> float:
    """`Θ = −½σ²S²Γ` à taux nul — l'identité, pas une approximation."""
    return -0.5 * vol * vol * s * s * gamma(s, k, vol, t)


def equilibre_instantane(vol: float = VOL_ANNUELLE) -> float:
    """Le mouvement quotidien d'équilibre, par l'identité : `σ/√365`.

    Il ne dépend ni de l'échéance, ni du strike, ni du niveau. C'est le
    théorème d'arrêt optionnel du marché d'options : **aucune échéance ne crée
    d'espérance**, et le vendeur facture exactement la courbure au prix de la
    volatilité implicite.
    """
    return vol / math.sqrt(JOURS_AN)


def equilibre_exact(jours: float, vol: float = VOL_ANNUELLE,
                    s: float = q.INDEX_LEVEL) -> float:
    """Le mouvement d'équilibre par réévaluation exacte sur une nuit.

    L'identité est instantanée ; un opérateur, lui, détient un jour. Sur ce
    jour, `T` diminue et la courbure change, si bien que le décaissement réel
    n'est pas `Θ·1/365`. On résout donc en `x` le bilan d'une couverture delta
    sur un mouvement symétrique d'amplitude `x` :

        ½·[V(S(1+x), T−dt) + V(S(1−x), T−dt)] − V(S, T) = 0

    Le terme de delta disparaît de la moyenne, ce qui est toute la raison de
    prendre le mouvement symétrique. La bissection est sur `x`.
    """
    t = jours / JOURS_AN
    dt = 1.0 / JOURS_AN
    k = s

    def bilan(x: float) -> float:
        haut = call(s * (1.0 + x), k, vol, t - dt)
        bas = call(s * (1.0 - x), k, vol, t - dt)
        return 0.5 * (haut + bas) - call(s, k, vol, t)

    lo, hi = 1e-7, 0.60
    for _ in range(90):
        mid = 0.5 * (lo + hi)
        if bilan(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def equilibre_quadratique(jours: float, vol: float = VOL_ANNUELLE,
                          s: float = q.INDEX_LEVEL) -> float:
    """Le mouvement d'équilibre par l'approximation que tout le monde écrit.

    On garde la forme quadratique `½ΓS²x²` du gain de couverture, mais on la
    règle sur le thêta **fini** d'un jour au lieu du thêta instantané :

        ½·Γ(T)·S²·x² = V(S, T) − V(S, T − dt)

    C'est la route de la vulgarisation, et elle est bonne partout sauf là où
    gamma compte le plus.
    """
    t = jours / JOURS_AN
    dt = 1.0 / JOURS_AN
    k = s
    decote = call(s, k, vol, t) - call(s, k, vol, t - dt)
    g = gamma(s, k, vol, t)
    if g <= 0.0:
        return math.inf
    return math.sqrt(2.0 * decote / (g * s * s))


#: Échéances balayées, en jours.
ECHEANCES: tuple[float, ...] = (1.0, 3.0, 7.0, 14.0, 30.0, 60.0, 90.0, 180.0)


def table_identite() -> Table:
    inst = equilibre_instantane()
    rows = []
    for j in ECHEANCES:
        ex = equilibre_exact(j)
        qd = equilibre_quadratique(j)
        rows.append([
            num(j, 0),
            num(100 * inst, 3),
            num(100 * qd, 3),
            num(100 * ex, 3),
            num(qd / ex, 2),
            num(gamma(q.INDEX_LEVEL, q.INDEX_LEVEL, VOL_ANNUELLE,
                      j / JOURS_AN) * q.INDEX_LEVEL ** 2 * 0.01, 2),
        ])
    r1 = equilibre_quadratique(ECHEANCES[0]) / equilibre_exact(ECHEANCES[0])
    rn = equilibre_quadratique(ECHEANCES[-1]) / equilibre_exact(ECHEANCES[-1])
    return Table(
        key="niv_identite",
        caption="Le mouvement d'équilibre d'un livre couvert, échéance par échéance",
        headers=["Jours à l'échéance", "Par l'identité (%)",
                 "Par l'approximation quadratique (%)",
                 "Par réévaluation exacte (%)", "Rapport des deux routes",
                 "Gamma par 1 % (points)"],
        rows=rows,
        note="La deuxième colonne est **constante**, et c'est le résultat "
             "structurant. L'équation de Black-Scholes se réduit, pour un "
             "livre couvert en delta à taux nul, à `Θ = −½σ²S²Γ` : le thêta "
             "payé est exactement la courbure reçue, facturée au prix de la "
             "volatilité implicite. Le mouvement d'équilibre vaut donc "
             "`σ/√365` **à toute échéance et à tout strike** — c'est le "
             "théorème d'arrêt optionnel du marché d'options, et il dit la "
             "même chose que `E[R] = −c/a` : aucune géométrie ne crée "
             "d'espérance, elle achète du temps. "
             "Les deux colonnes suivantes sont les deux façons de tenir "
             "compte du fait qu'un opérateur détient un jour et non un "
             "instant, et **elles encadrent la vérité par les deux côtés**. "
             "L'approximation quadratique surestime, parce que la parabole "
             "monte plus vite que le vrai gain d'une couverture sur un grand "
             "mouvement ; la réévaluation exacte est la mesure. Leur rapport "
             "vaut " + num(r1, 2) + " à un jour et " + num(rn, 2) + " à "
             + num(ECHEANCES[-1], 0) + ". *L'approximation qui fonde tout le "
             "discours sur le gamma échoue exactement là où le gamma est le "
             "plus grand* — le dernier jour, celui dont le guide extérieur "
             "dit lui-même qu'il est un pari sur la loi terminale. La "
             "dernière colonne est l'unité utilisable, `Γ·S²·0,01`, la seule "
             "qui se compare d'un sous-jacent à l'autre.",
    )


SURF_JOURS: tuple[float, ...] = (180.0, 90.0, 30.0, 7.0, 2.0, 0.5)
SURF_VOL: tuple[float, ...] = (0.60, 0.45, 0.32, 0.22, 0.15, 0.10)


def surface_bande() -> list[list[float]]:
    """La demi-largeur de la bande de gamma, sur (échéance, volatilité).

    Les deux axes entrent par le même produit `σ√T`, et c'est le fait de la
    surface : une échéance courte et une volatilité basse font exactement la
    même chose au lieu qu'occupe la courbure. Le sommet est au fond.
    """
    return [[largeur_gamma(j, v) for v in SURF_VOL] for j in SURF_JOURS]


# ---------------------------------------------------------------------------
# V. Le signe que la reconstruction jette
# ---------------------------------------------------------------------------

#: Le profil d'intérêt ouvert synthétique : les puts sous le comptant, les
#: calls au-dessus, en cloches décalées. C'est la forme que le guide dessine,
#: et elle est reconstruite ici pour être mesurée, pas pour être crue.
STRIKES: tuple[float, ...] = tuple(
    q.INDEX_LEVEL * (0.85 + 0.005 * i) for i in range(61))

#: Écart des deux cloches au comptant, en fraction du niveau.
DECALAGE = 0.030
LARGEUR_CLOCHE = 0.045
OI_MAX = 10000.0

#: Multiplicateur du contrat, et la constante du pour-cent de la formule.
MULTIPLICATEUR = 50.0

JOURS_GEX = 7.0

#: Les signes que la reconstruction courante suppose : teneur long les calls,
#: court les puts. C'est ce couple, et lui seul, qui fait exister une bascule.
SIGNE_CALL = 1.0
SIGNE_PUT = -1.0


def profil_oi(asymetrie: float = 1.0) -> tuple[tuple[float, float, float], ...]:
    """L'intérêt ouvert par strike : (strike, OI call, OI put).

    L'asymétrie est déclarée et balayée : à un, les deux cloches ont la même
    masse ; au-dessous, les puts dominent, ce qui est la forme habituelle d'un
    indice. Elle est **le seul réglage** de cette section.
    """
    out = []
    for k in STRIKES:
        m = k / q.INDEX_LEVEL
        c = OI_MAX * math.exp(-0.5 * ((m - 1.0 - DECALAGE)
                                      / LARGEUR_CLOCHE) ** 2)
        p = OI_MAX * asymetrie * math.exp(
            -0.5 * ((m - 1.0 + DECALAGE) / LARGEUR_CLOCHE) ** 2)
        out.append((k, c, p))
    return tuple(out)


def gex(spot: float, signes: tuple[float, ...] | None = None,
        asymetrie: float = 1.0, jours: float = JOURS_GEX) -> float:
    """`GEX = Σ Γᵢ·OIᵢ·m·S²·(1 %)·signᵢ`, en millions par pour-cent.

    `signes` porte le signe **par strike**. Quand il est absent, on applique
    l'hypothèse de la reconstruction courante, celle qui fait exister une
    bascule : le teneur est **long les calls** que les vendeurs couverts lui
    cèdent et **court les puts** que les acheteurs de protection lui achètent.
    C'est cette hypothèse-là que la section met à l'épreuve — et il faut voir
    qu'elle est double, puisqu'elle suppose à la fois un sens et le fait qu'il
    soit le même à tous les strikes.
    """
    t = jours / JOURS_AN
    total = 0.0
    for i, (k, oi_c, oi_p) in enumerate(profil_oi(asymetrie)):
        g = gamma(spot, k, VOL_ANNUELLE, t)
        s_c = SIGNE_CALL if signes is None else signes[2 * i]
        s_p = SIGNE_PUT if signes is None else signes[2 * i + 1]
        total += g * spot * spot * 0.01 * MULTIPLICATEUR * (
            s_c * oi_c + s_p * oi_p)
    return total / 1e6


def bascule(signes: tuple[float, ...] | None = None, asymetrie: float = 1.0,
            lo: float = 0.90, hi: float = 1.12,
            jours: float = JOURS_GEX) -> float:
    """Le niveau de bascule : le comptant où `GEX` traverse zéro.

    Bissection sur le comptant. Quand la fonction ne change pas de signe sur
    la boîte, il n'y a **pas** de bascule et la fonction rend `nan` — ce qui
    est une issue en soi, et la table la compte.
    """
    a, b = lo * q.INDEX_LEVEL, hi * q.INDEX_LEVEL
    fa = gex(a, signes, asymetrie, jours)
    fb = gex(b, signes, asymetrie, jours)
    if fa * fb > 0.0:
        return math.nan
    for _ in range(60):
        m = 0.5 * (a + b)
        fm = gex(m, signes, asymetrie, jours)
        if fa * fm <= 0.0:
            b, fb = m, fm
        else:
            a, fa = m, fm
    return 0.5 * (a + b)


N_SIGNES = 240


@lru_cache(maxsize=128)
def bande_de_bascule(part_connue: float, asymetrie: float = 1.0,
                     n: int = N_SIGNES, seed: int = SEED + 7,
                     jours: float = JOURS_GEX
                     ) -> tuple[float, float, float, float]:
    """La bande où la bascule se promène quand le signe n'est pas observé.

    `part_connue` est la fraction des strikes dont le signe est réellement
    connu ; sur le reste, le teneur est court avec probabilité un demi. On
    rend le cinquième centile, la médiane, le quatre-vingt-quinzième, et la
    part des tirages où **aucune** bascule n'existe dans la boîte.

    C'est le mécanisme du résultat négatif du guide, calculé : si la bande est
    large devant la géométrie qui prétend trader le niveau, le niveau publié
    ne porte rien à cette résolution — sans qu'il faille invoquer quoi que ce
    soit sur l'efficience du marché.
    """
    rng = Rng(seed)
    vals: list[float] = []
    absent = 0
    for _ in range(n):
        signes = []
        for _ in range(len(STRIKES)):
            for suppose in (SIGNE_CALL, SIGNE_PUT):
                if rng.uniform() < part_connue:
                    signes.append(suppose)
                else:
                    signes.append(1.0 if rng.uniform() < 0.5 else -1.0)
        x = bascule(tuple(signes), asymetrie, jours=jours)
        if math.isnan(x):
            absent += 1
        else:
            vals.append(x)
    vals.sort()
    if not vals:
        return (math.nan, math.nan, math.nan, 1.0)

    def qt(p: float) -> float:
        return vals[min(len(vals) - 1, int(p * (len(vals) - 1)))]

    return (qt(0.05), qt(0.50), qt(0.95), absent / n)


#: Parts de strikes dont le signe serait connu.
PARTS: tuple[float, ...] = (0.00, 0.25, 0.50, 0.75, 0.90, 1.00)


def table_signe() -> Table:
    ref = bascule()
    a1 = seuil.geometry(0.150).stop_points
    rows = []
    for f in PARTS:
        lo, med, hi, absent = bande_de_bascule(f)
        largeur = hi - lo
        rows.append([
            num(100 * f, 0),
            num(med, 0),
            num(lo, 0) + " à " + num(hi, 0),
            num(largeur, 0),
            num(100 * largeur / q.INDEX_LEVEL, 2),
            num(largeur / a1, 1),
            num(100 * absent, 1),
        ])
    lo0, _, hi0, _ = bande_de_bascule(0.0)
    return Table(
        key="niv_signe",
        caption="Où se promène le niveau de bascule quand le signe n'est pas observé",
        headers=["Signes connus (%)", "Bascule médiane", "Bande à 90 %",
                 "Largeur (points)", "En % du niveau",
                 "Rapport au stop élargi", "Aucune bascule (%)"],
        rows=rows,
        note="La reconstruction courante suppose le teneur long les calls "
             "et court les puts, à **tous** les strikes. L'intérêt ouvert ne "
             "porte aucun signe : c'est une supposition habillée en donnée, "
             "et le guide extérieur le dit lui-même. La table mesure ce que "
             "la supposition vaut, en n'en retenant qu'une fraction et en "
             "tirant le reste à pile ou face. À signe entièrement connu la "
             "bascule est un point — " + num(ref, 0) + " — et la bande est "
             "nulle par construction, ce qui est le contrôle de la colonne. "
             "À signe entièrement inconnu, elle occupe "
             + num(hi0 - lo0, 0) + " points, soit "
             + num((hi0 - lo0) / a1, 0) + " fois le stop élargi du document. "
             "**Un niveau dont l'incertitude propre vaut des dizaines de fois "
             "la géométrie qui prétend le trader ne porte rien à cette "
             "résolution**, et il n'y a là aucune affirmation sur "
             "l'efficience du marché : c'est de l'arithmétique sur ce que la "
             "reconstruction jette. La dernière colonne compte les tirages où "
             "la bascule n'existe pas du tout dans la boîte — une issue que "
             "la publication d'un nombre unique ne peut pas représenter, et "
             "qui **censure la colonne précédente** : une configuration sans "
             "bascule ne peut entrer dans aucun quantile, si bien que la "
             "largeur publiée est une borne **inférieure** de l'incertitude, "
             "et qu'elle l'est le plus là où l'incertitude est la plus "
             "grande. C'est pour cette raison que le relief de la section "
             "porte la part d'absence et non la largeur.",
    )


#: Parts de signes connus balayées par le relief.
SURF_PART: tuple[float, ...] = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)

#: Échéances balayées, en jours, **décroissantes** : le sommet du relief doit
#: tomber au coin le plus éloigné de la projection.
SURF_JOURS_GEX: tuple[float, ...] = (180.0, 60.0, 21.0, 7.0, 3.0, 1.0)

N_SURFACE_SIGNES = 90


def surface_absence() -> list[list[float]]:
    """La part des configurations **sans aucune bascule**, sur (signes, échéance).

    La grandeur portée n'est pas la largeur de la bande, et le choix vient
    d'une mesure qui a réfuté la première version. On attendait qu'un profil
    très asymétrique resserre l'incertitude, la masse d'un côté devant finir
    par dominer ; **le balayage rend une surface plate sur cet axe** — de 975
    à 1 072 points sur toute la plage d'asymétrie, soit rien. L'axe a donc été
    remplacé par l'échéance, qui agit, et pour une raison qu'on peut dire :
    près de l'échéance la courbure se concentre sur quelques strikes et le
    passage à zéro y est tenu par le déséquilibre local ; loin de l'échéance
    elle s'étale, tous les strikes pèsent à peu près pareil, et la somme
    devient une quasi-égalité que n'importe quel signe retourné fait basculer.

    La largeur de bande, elle, souffre d'une **censure** : les configurations
    dont le passage à zéro sort de la boîte n'ont pas de bascule et ne peuvent
    pas entrer dans un quantile. La bande mesurée est donc une borne
    inférieure de l'incertitude, et elle l'est le plus là où l'incertitude est
    la plus grande. La part d'absence n'a pas ce défaut : c'est exactement la
    quantité que la censure produit, et elle se lit sans correction.
    """
    out = []
    for f in SURF_PART:
        ligne = []
        for j in SURF_JOURS_GEX:
            _, _, _, absent = bande_de_bascule(f, 1.0, N_SURFACE_SIGNES,
                                               SEED + 13, j)
            ligne.append(100.0 * absent)
        out.append(ligne)
    return out


# ---------------------------------------------------------------------------
# VI. Ce qui reste
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Affirmation:
    """Une affirmation du guide extérieur, et ce que le protocole en fait."""

    quoi: str
    ce_qu_elle_dit: str
    effet: str
    #: Déplace-t-elle l'horloge, le risque, ou le sens ?
    porte: str
    #: Le nom court, pour la gouttière d'une planche.
    court: str = ""

    @property
    def directionnelle(self) -> bool:
        return self.porte == "le sens"


def affirmations() -> tuple[Affirmation, ...]:
    """Les cinq affirmations, avec leurs effets relus des sections."""
    a1 = seuil.geometry(0.150).stop_points
    lo0, _, hi0, _ = bande_de_bascule(0.0)
    w = largeur_gamma(1.0)
    return (
        Affirmation(
            "Le niveau de bascule",
            "le prix change de comportement au passage de zéro",
            "bande de " + num(hi0 - lo0, 0) + " points sur le seul signe "
            "inconnu, soit " + num((hi0 - lo0) / a1, 0) + " fois le stop "
            "élargi",
            "rien", "la bascule"),
        Affirmation(
            "La concentration de gamma par strike",
            "les gros strikes aimantent le prix",
            "demi-largeur de " + num(w, 0) + " points à un jour, soit "
            + num(w / q.STOP_PTS, 0) + " fois la géométrie déclarée",
            "rien", "gamma par strike"),
        Affirmation(
            "Le régime de gamma",
            "gamma court amplifie, gamma long amortit",
            "facteur trois sur le temps de marché, donc sur µ*, à "
            "probabilité de touche inchangée",
            "l'horloge", "le régime"),
        Affirmation(
            "Gamma court et sa queue",
            "beaucoup de petits gains, puis un qui les défait",
            "le dimensionnement sur la séance médiane sous-estime la perte "
            "d'un facteur que la partie XVIII mesure à 2,98 sur la pire "
            "séance",
            "le risque", "gamma court"),
        Affirmation(
            "L'identité gamma-thêta",
            "la courbure reçue est exactement le thêta payé",
            "mouvement d'équilibre " + num(100 * equilibre_instantane(), 2)
            + " % par jour, constant à toute échéance",
            "l'horloge", "gamma et thêta"),
    )


def table_reste() -> Table:
    rows = []
    for x in affirmations():
        rows.append([
            x.quoi,
            x.ce_qu_elle_dit,
            x.effet,
            x.porte,
            "oui" if x.directionnelle else "non",
        ])
    return Table(
        key="niv_reste",
        caption="Cinq affirmations sur le gamma, et ce que chacune déplace",
        headers=["Affirmation", "Ce qu'elle dit", "Ce que le protocole mesure",
                 "Ce qu'elle déplace", "Donne un sens"],
        rows=rows,
        note="La colonne de verdict est **calculée** — elle vaut « oui » si "
             "et seulement si ce que l'affirmation déplace est le sens — et "
             "elle ne porte aucun oui. Deux affirmations déplacent l'horloge, "
             "une déplace le risque, deux ne déplacent rien à la résolution "
             "où on les trade. Ce n'est pas un verdict sur la mécanique : la "
             "couverture des teneurs est réelle et son effet sur la "
             "volatilité réalisée est documenté. C'est un verdict sur la "
             "**reconstruction de détail** — intérêt ouvert non signé, une "
             "seule volatilité, positionnement supposé — qui jette exactement "
             "l'information qui la rendrait utilisable. *Si vous n'observez "
             "pas le signe de l'inventaire du teneur, vous ne mesurez pas son "
             "gamma. Vous mesurez où l'intérêt ouvert se trouve.*",
        wrap_cols=[1, 2],
    )


# ---------------------------------------------------------------------------
# Ce que le document consomme
# ---------------------------------------------------------------------------


def values() -> dict[str, str]:
    g0 = seuil.geometry(0.010)
    g1 = seuil.geometry(0.150)
    a1 = g1.stop_points
    lo0, med0, hi0, absent0 = bande_de_bascule(0.0)
    w1 = largeur_gamma(1.0)
    w0 = largeur_gamma(2.0 / 24.0)
    w30 = largeur_gamma(30.0)
    par_cle = {x.cle: x for x in niveaux()}
    return {
        "n_sigma_seance": num(SIGMA_SEANCE, 1),
        "n_sigma_seance_pct": num(100 * SIGMA_SEANCE_PCT, 3),
        "n_taux_temoin": num(100.0 / (1.0 + q.RR_REF), 2),
        "n_pouvert_declare": num(
            100 * cloture_avant_barriere(g0.stop_points), 2),
        "n_pouvert_elargi": num(100 * cloture_avant_barriere(a1), 1),
        "n_touche_demi": num(100 * taux_de_touche(0.5 * SIGMA_SEANCE), 1),
        "n_touche_un": num(100 * taux_de_touche(SIGMA_SEANCE), 1),
        "n_exces_declare": num(100 * exces_requis(g0.friction_ratio), 2),
        "n_exces_elargi": num(100 * exces_requis(g1.friction_ratio), 3),
        "n_touches_declare": num(touches_requises(g0.friction_ratio), 0),
        "n_touches_elargi": num(touches_requises(g1.friction_ratio), 0),
        "n_info_declare": num(touches_par_information(g0.friction_ratio), 0),
        "n_info_elargi": num(touches_par_information(g1.friction_ratio), 0),
        "n_accord_declare": num(
            100 * abs(touches_requises(g0.friction_ratio)
                      / touches_par_information(g0.friction_ratio) - 1.0), 0),
        "n_facteur_exces": num(exces_requis(g0.friction_ratio)
                               / exces_requis(g1.friction_ratio), 0),
        "n_facteur_touches": num(touches_requises(g1.friction_ratio)
                                 / touches_requises(g0.friction_ratio), 0),
        "n_demi_hauteur": num(DEMI_HAUTEUR, 3),
        "n_largeur_0dte": num(w0, 1),
        "n_largeur_1j": num(w1, 0),
        "n_largeur_30j": num(w30, 0),
        "n_largeur_0dte_pct": num(100 * w0 / q.INDEX_LEVEL, 2),
        "n_largeur_1j_pct": num(100 * w1 / q.INDEX_LEVEL, 2),
        "n_rapport_0dte": num(w0 / q.STOP_PTS, 0),
        "n_rapport_1j": num(w1 / q.STOP_PTS, 0),
        "n_rapport_0dte_elargi": num(w0 / a1, 1),
        "n_inval_0dte": num(100 * invalidation_prematuree(w0, a1), 1),
        "n_inval_1j": num(100 * invalidation_prematuree(w1, a1), 1),
        "n_largeur_ancrage": num(largeur_d_ancrage(), 2),
        "n_largeur_vwap": num(par_cle["vwap"].largeur_pts, 1),
        "n_stop_declare": num(q.STOP_PTS, 2),
        "n_stop_elargi": num(a1, 1),
        "n_equilibre": num(100 * equilibre_instantane(), 3),
        "n_equilibre_1j": num(100 * equilibre_exact(1.0), 3),
        "n_equilibre_180j": num(100 * equilibre_exact(180.0), 3),
        "n_equilibre_quad_1j": num(100 * equilibre_quadratique(1.0), 3),
        "n_rapport_routes_1j": num(
            equilibre_quadratique(1.0) / equilibre_exact(1.0), 2),
        "n_rapport_routes_long": num(
            equilibre_quadratique(180.0) / equilibre_exact(180.0), 2),
        "n_vol_annuelle": num(100 * VOL_ANNUELLE, 0),
        "n_bascule_ref": num(bascule(), 0),
        "n_bascule_bas": num(lo0, 0),
        "n_bascule_haut": num(hi0, 0),
        "n_bascule_largeur": num(hi0 - lo0, 0),
        "n_bascule_pct": num(100 * (hi0 - lo0) / q.INDEX_LEVEL, 2),
        "n_bascule_rapport": num((hi0 - lo0) / a1, 0),
        "n_bascule_absent": num(100 * absent0, 1),
        "n_rr": num(q.RR_REF, 0),
        "n_friction": num(FRICTION, 2),
        "n_lectures": num(len(niveaux()), 0),
        "n_passent": num(len(passe_les_deux()), 0),
        "n_qui_passe": passe_les_deux()[0].nom.lower() if passe_les_deux()
        else "aucune",
        "n_touches_carriere": num(TOUCHES_CARRIERE, 0),
        "n_directionnelles": num(
            sum(1 for x in affirmations() if x.directionnelle), 0),
        "n_horloge": num(
            sum(1 for x in affirmations() if x.porte == "l'horloge"), 0),
        "n_rien": num(sum(1 for x in affirmations() if x.porte == "rien"), 0),
    }


def all_tables() -> dict[str, Table]:
    tables = [
        table_temoin(), table_definition(), table_exigence(),
        table_largeur(), table_forcee(), table_identite(), table_signe(),
        table_reste(),
    ]
    return {t.key: t for t in tables}


def main() -> None:
    for t in all_tables().values():
        print(t.to_text())
        print()
    for k, v in values().items():
        print(f"{k:26s} {v}")


if __name__ == "__main__":
    main()
