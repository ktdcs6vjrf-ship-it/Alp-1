"""La grammaire du setup : le niveau, le contact, la confirmation, l'invalidation.

Le catalogue de `concepts.py` range des **motifs**. Un opérateur ne prend pas un
motif : il prend un motif **à un endroit**, tenu par une **condition qu'il a
écrite d'avance**, et abandonné sur une **autre**. Entre « une absorption »
et « une absorption au point de contrôle, confirmée par une clôture qui ne
franchit pas le niveau, invalidée si elle le franchit d'un écart-type dans le
quart d'heure », il y a toute la distance entre une observation et une règle.

Ce module écrit les quatre termes, pour six familles de niveaux et trois
confirmations, puis les **mesure** sur des séances sans dérive. Rien n'y est
postulé de l'efficacité d'une confirmation ; on mesure ce qu'elle change, et
ce qu'elle coûte.

Le résultat, en une phrase
--------------------------
    la confirmation ne déplace pas l'espérance — elle divise l'échantillon.

Sous prix sans dérive, la probabilité que le prix aille dans le sens attendu
vaut un demi au contact brut, et elle vaut encore un demi une fois la
confirmation exigée : c'est le théorème d'arrêt optionnel, qui ne connaît pas
les conditions d'entrée. Ce que la confirmation change, en revanche, se mesure
sans ambiguïté : elle retire entre deux tiers et quatre-vingt-quinze pour cent
des occasions. Le nombre de décisions nécessaires pour établir la rentabilité
de la géométrie ne bougeant pas, **le délai d'établissement est multiplié par
ce même facteur**. Une confirmation est donc un pari : elle ne se justifie que
si l'on croit qu'elle déplace `µ` d'assez pour compenser le temps qu'elle
coûte — et le tableau du bas de ce module chiffre exactement ce « d'assez ».

Ce qui est déclaré, et ce qui est calculé
-----------------------------------------
Déclarés, et ce sont les seuls : la définition des six niveaux, celle des
trois confirmations, celle des invalidations, et les cinq seuils numériques
qu'elles contiennent. Tout le reste — fréquences, parts confirmées, parts
invalidées, réactions, délais, verdicts — est mesuré sur les mêmes séances
sans dérive que le catalogue.

Le paramètre non observable, encore
-----------------------------------
Deux réglages décident ici de fréquences, et ni l'un ni l'autre ne s'observe :
l'échelle d'impact qui sert au `z` d'absorption, et l'indépendance déclarée
entre le volume d'une minute et son amplitude. La première est calibrée sur la
séance elle-même — le déplacement typique d'une minute rapporté à la racine de
son volume typique — de sorte que le `z` soit centré réduit quand il n'y a rien
à lire. La seconde est fausse dans le vrai marché, où volume et amplitude vont
ensemble : l'indépendance rend l'absorption **plus** fréquente ici qu'elle ne
l'est en séance, ce qui va dans le sens conservateur pour la thèse défendue.
Les deux sont écrits ici plutôt que cachés, comme la taille de grappe du
footprint et le pas de rangée du profil de marché le sont ailleurs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from . import concepts as C
from . import dow, seuil, vprofile
from . import footprint as fp
from . import quant as q
from .barriers import required_drift
from .costs import ES
from .mc import Rng
from .report import Table, num

# ---------------------------------------------------------------------------
# La séance, à la barre : ce que le catalogue n'avait pas
# ---------------------------------------------------------------------------

#: Sous-pas par minute. Douze suffisent à donner à la barre une ouverture, un
#: haut, un bas et une clôture qui ne soient pas dégénérés ; au-delà, la mèche
#: cesse de dépendre du nombre de sous-pas et la loi de la mèche dominante
#: converge vers celle du module `dow`.
SOUS_PAS = 12

#: Volume d'une minute ordinaire, en contrats. Repris du volume de la barre
#: neutre du module de footprint, pour que les deux couches parlent de la même
#: minute.
V_MINUTE = 1800.0

#: Dispersion du volume à la minute, en écart-type de son logarithme. Le
#: volume est tiré **indépendamment** de l'amplitude de la barre : c'est le
#: choix conservateur, et il est discuté dans l'en-tête du module.
DISPERSION_VOLUME = 0.45

#: Probabilité qu'un sous-pas haussier s'exécute à l'ask. À un demi, le delta
#: n'apprendrait rien du sens ; à un, il le rendrait exactement. La valeur
#: déclarée place la corrélation entre delta et rendement au voisinage de celle
#: que `orderflow` retient pour le CVD, et le module la mesure pour le dire.
ALIGNEMENT = 0.90

#: Échelle d'impact de la séance : le déplacement typique d'une minute rapporté
#: à la racine de son volume typique. C'est elle, et non la profondeur affichée
#: du carnet, qui rend le `z` d'absorption centré réduit quand il n'y a rien à
#: lire.
LAMBDA_SEANCE = q.SIGMA_1MIN / math.sqrt(V_MINUTE)

#: Séances simulées. Le catalogue en prend quatre cents pour des détecteurs à
#: une occasion par séance. Il en faut davantage ici : la confirmation la plus
#: exigeante ne retient qu'un contact sur quarante, et une part mesurée sur
#: trente observations ne dit rien qu'on puisse publier.
SEANCES = 900
SEED = 20260830


@dataclass(frozen=True)
class Barre:
    """Une minute : ouverture, haut, bas, clôture, volume, et sa coupe bid/ask."""

    t: int
    ouverture: float
    haut: float
    bas: float
    cloture: float
    volume: int
    ask: int
    bid: int

    @property
    def delta(self) -> int:
        return self.ask - self.bid

    @property
    def etendue(self) -> float:
        return self.haut - self.bas

    @property
    def deplacement(self) -> float:
        return self.cloture - self.ouverture

    @property
    def z(self) -> float:
        """Déplacement rapporté à la racine du volume — le `z` d'impact.

        Un `z` proche de zéro **est** l'absorption : beaucoup de contrats se
        sont échangés et le prix n'a pas bougé. Le volume élevé y est déjà
        contenu, ce qui n'empêche pas la confirmation de l'exiger séparément —
        un `z` nul sur une barre vide ne dit rien.
        """
        return self.deplacement / (LAMBDA_SEANCE * math.sqrt(max(self.volume, 1)))

    def meche(self, sens: int) -> float:
        """Part de l'étendue occupée par la mèche du côté `sens`.

        `sens` vaut +1 pour la mèche haute, −1 pour la basse. Sur une barre
        d'étendue nulle la part est nulle : il n'y a pas de mèche à lire.
        """
        if self.etendue <= 0.0:
            return 0.0
        corps_haut = max(self.ouverture, self.cloture)
        corps_bas = min(self.ouverture, self.cloture)
        haut = self.haut - corps_haut if sens > 0 else corps_bas - self.bas
        return haut / self.etendue


def _graine(seance: int, t: int) -> int:
    """Graine propre à une minute d'une séance.

    Chaque barre tire d'un flux qui n'appartient qu'à elle, au lieu de puiser
    dans un flux de séance. Ce n'est pas un détail de commodité : c'est ce qui
    permet de **rejouer une barre isolée** — donc d'en redessiner le footprint
    dans une figure — sans avoir à rejouer la séance entière, et sans que la
    figure et la mesure puissent diverger.
    """
    return SEED + 1_000_003 * seance + 7919 * t


def _barre(t: int, depart: float, rng: Rng, derive_min: float,
           detail: bool = False):
    """Une minute simulée : douze sous-pas, un volume, une coupe bid/ask.

    Le volume de chaque sous-pas est la même fraction du volume de la minute ;
    seul le **côté** dépend du sens du sous-pas, et il en dépend de façon
    bruitée. C'est la règle du tick, avec son taux d'erreur déclaré.

    Quand `detail` est demandé, le volume de chaque sous-pas est en outre
    réparti sur les **rangées de prix** qu'il traverse, à un tick près : c'est
    le footprint de la barre, celui qu'une plateforme affiche. Le sous-pas
    donne son côté à toutes les rangées qu'il traverse, ce qui est la règle du
    tick appliquée à la trace et non au seul dernier prix.
    """
    sigma = q.SIGMA_1MIN / math.sqrt(SOUS_PAS)
    mu = derive_min / SOUS_PAS
    volume = max(int(V_MINUTE * math.exp(DISPERSION_VOLUME * rng.gauss()
                                         - 0.5 * DISPERSION_VOLUME ** 2)), 1)
    part = volume / SOUS_PAS
    x = depart
    haut = bas = depart
    ask = 0.0
    cellules: dict[float, list[float]] = {}
    for _ in range(SOUS_PAS):
        pas = mu + sigma * rng.gauss()
        depuis = x
        x += pas
        haut = max(haut, x)
        bas = min(bas, x)
        p_ask = ALIGNEMENT if pas >= 0.0 else 1.0 - ALIGNEMENT
        au_ask = rng.uniform() < p_ask
        ask += part * (1.0 if au_ask else 0.0)
        if detail:
            rangees = _rangees(depuis, x)
            morceau = part / len(rangees)
            for prix in rangees:
                case = cellules.setdefault(prix, [0.0, 0.0])
                case[1 if au_ask else 0] += morceau
    n_ask = int(round(ask))
    barre = Barre(t, depart, haut, bas, x, volume, n_ask, volume - n_ask)
    if not detail:
        return barre
    cells = tuple(Cellule(prix, int(round(v[0])), int(round(v[1])))
                  for prix, v in sorted(cellules.items()))
    return barre, cells


@dataclass(frozen=True)
class Cellule:
    """Une rangée de footprint : le volume vendu au bid, acheté à l'ask."""

    prix: float
    bid: int
    ask: int

    @property
    def total(self) -> int:
        return self.bid + self.ask


def _rangees(depuis: float, vers: float) -> tuple[float, ...]:
    """Les rangées de prix qu'un sous-pas traverse, au tick près."""
    lo, hi = sorted((depuis, vers))
    pas = ES.tick_size
    debut = math.floor(lo / pas)
    fin = math.floor(hi / pas)
    return tuple(k * pas for k in range(debut, fin + 1))


def footprint(seance_index: int, minute: int,
              derive_par_heure: float = 0.0) -> tuple[Barre, tuple[Cellule, ...]]:
    """Rejoue une minute et rend son footprint.

    La barre rendue est **la même** que celle de `seances` : même graine, même
    flux, même volume. Une figure ne peut donc pas montrer autre chose que ce
    que la table mesure.
    """
    barres = seances(derive_par_heure)[seance_index]
    depart = barres[minute].ouverture
    rng = Rng(_graine(seance_index, minute))
    return _barre(minute, depart, rng, derive_par_heure / 60.0, detail=True)


@lru_cache(maxsize=4)
def seances(derive_par_heure: float = 0.0,
            n: int = SEANCES) -> tuple[tuple[Barre, ...], ...]:
    """`n` séances de barres à la minute, à dérive déclarée.

    À dérive nulle, rien n'est ajouté à la marche : ni saut, ni saisonnalité,
    ni régime. C'est le minimum contre lequel un setup doit se comparer, et il
    suffit à établir qu'aucune des confirmations recensées ici ne déplace la
    suite du prix.
    """
    derive_min = derive_par_heure / 60.0
    out = []
    for index in range(n):
        x = 0.0
        barres = []
        for t in range(int(q.SESSION_MIN)):
            barre = _barre(t, x, Rng(_graine(index, t)), derive_min)
            barres.append(barre)
            x = barre.cloture
        out.append(tuple(barres))
    return tuple(out)


def correlation_delta() -> float:
    """Corrélation mesurée entre le delta d'une barre et son déplacement.

    Elle n'est pas déclarée : `ALIGNEMENT` l'est, et cette corrélation en
    découle. Elle sert de contrôle — la placer au voisinage de celle que
    `orderflow` retient pour le CVD est ce qui autorise à lire les
    confirmations de delta comme on lit celles d'une plateforme.
    """
    xs: list[float] = []
    ys: list[float] = []
    for barres in seances()[:40]:
        for b in barres:
            xs.append(b.delta / b.volume)
            ys.append(b.deplacement)
    n = float(len(xs))
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / n
    vx = sum((a - mx) ** 2 for a in xs) / n
    vy = sum((b - my) ** 2 for b in ys) / n
    return cov / math.sqrt(vx * vy) if vx > 0 and vy > 0 else 0.0


# ---------------------------------------------------------------------------
# Les six niveaux : où le prix se rend, et comment ce « où » se calcule
# ---------------------------------------------------------------------------

#: Minute à partir de laquelle les contacts sont comptés. Les niveaux tirés du
#: profil sont bâtis sur ce qui précède : un niveau lu sur la séance entière
#: serait un niveau connu après coup, ce qui n'est pas la situation de
#: l'opérateur.
DEBUT = int(q.SESSION_MIN) // 2

#: Pas du profil de volume, en points. Il décide de la finesse du point de
#: contrôle et du nœud de faible volume, comme le pas de rangée décide de la
#: rareté de l'extrême pauvre.
PAS_PROFIL = 1.0

#: Seuil du zigzag de Dow, en points. C'est le paramètre libre de la couche de
#: structure, et il est fixé ici avant mesure.
SEUIL_PIVOT = 6.0

#: Un contact est neuf si le prix venait d'au moins cet écart, en points ; il
#: se réarme quand le prix s'en éloigne d'autant. Sans réarmement, une heure
#: passée à osciller sur un niveau compterait soixante contacts.
ECART_REARME = 3.0


@dataclass(frozen=True)
class Niveau:
    """Un niveau de prix, et la façon dont il se calcule."""

    cle: str
    nom: str
    famille: str
    calcul: str
    horizon_min: float


NIVEAUX: tuple[Niveau, ...] = (
    Niveau("poc", "Point de contrôle", "Profil de volume",
           "le pas du profil de la première demi-séance où le plus de volume "
           "s'est échangé", 60.0),
    Niveau("valeur", "Bord de l'aire de valeur", "Profil de volume",
           "les deux bornes qui couvrent 70 % du volume de la première "
           "demi-séance, par extension depuis le point de contrôle", 60.0),
    Niveau("lvn", "Nœud de faible volume", "Profil de volume",
           "un creux local du profil de la première demi-séance, de "
           "proéminence 5 %", 60.0),
    Niveau("vwap", "Deuxième bande VWAP", "Prix-volume",
           "le VWAP courant plus ou moins deux écarts-types courants, "
           "recalculés à chaque minute", 30.0),
    Niveau("pivot", "Pivot de structure", "Structure de Dow",
           "les trois derniers sommets ou creux confirmés par un zigzag de "
           + num(SEUIL_PIVOT, 0) + " points, jamais lu à l'œil", 120.0),
    Niveau("ote", "Zone d'entrée optimale", "Fibonacci",
           "le retracement de 61,8 % à 79 % de la dernière jambe du zigzag",
           45.0),
)

_PAR_NIVEAU = {n.cle: n for n in NIVEAUX}


def _niveaux_poc(barres: tuple[Barre, ...], i: int,
                 profil: vprofile.Profile) -> tuple[float, ...]:
    return (profil.poc,)


def _niveaux_valeur(barres, i, profil) -> tuple[float, ...]:
    va = profil.value_area()
    return (va.low, va.high)


def _niveaux_lvn(barres, i, profil) -> tuple[float, ...]:
    return tuple(profil.lvn(prominence=0.05))


def _niveaux_vwap(barres, i, profil) -> tuple[float, ...]:
    """Les deux bandes à deux écarts-types, recalculées à la minute.

    Le volume par minute étant dispersé, le VWAP est ici une **vraie** moyenne
    pondérée par le volume, et non la moyenne courante du prix que le
    catalogue utilise. L'écart entre les deux est faible ; l'écrire l'est
    moins, parce que c'est la seule définition qu'une plateforme affiche.
    """
    somme = poids = carre = 0.0
    for b in barres[:i + 1]:
        typique = (b.haut + b.bas + b.cloture) / 3.0
        somme += typique * b.volume
        carre += typique * typique * b.volume
        poids += b.volume
    if poids <= 0:
        return ()
    moyenne = somme / poids
    var = max(carre / poids - moyenne * moyenne, 0.0)
    sigma = math.sqrt(var)
    if sigma <= 0.0:
        return ()
    return (moyenne - 2.0 * sigma, moyenne + 2.0 * sigma)


def _pivots(barres: tuple[Barre, ...], i: int) -> list[dow.Swing]:
    """Les pivots confirmés à la minute `i`, et rien après elle."""
    chemin = [b.cloture for b in barres[:i + 1]]
    return dow.swings(chemin, SEUIL_PIVOT)


#: Nombre de pivots suivis. Un seul — le dernier confirmé — ne donnerait
#: qu'un contact toutes les sept séances, ce qui ne mesure rien ; trois est
#: aussi ce qu'un opérateur garde à l'écran.
N_PIVOTS = 3


def _niveaux_pivot(barres, i, profil) -> tuple[float, ...]:
    sw = _pivots(barres, i)
    return tuple(s.price for s in sw[-N_PIVOTS:])


def _niveaux_ote(barres, i, profil) -> tuple[float, ...]:
    """Les deux bords de la zone 61,8–79 % de la dernière jambe confirmée."""
    sw = _pivots(barres, i)
    if len(sw) < 2:
        return ()
    fin, depart = sw[-1], sw[-2]
    jambe = fin.price - depart.price
    if abs(jambe) < SEUIL_PIVOT:
        return ()
    return (fin.price - 0.618 * jambe, fin.price - 0.79 * jambe)


_CALCUL = {"poc": _niveaux_poc, "valeur": _niveaux_valeur,
           "lvn": _niveaux_lvn, "vwap": _niveaux_vwap,
           "pivot": _niveaux_pivot, "ote": _niveaux_ote}

#: Les niveaux dont le calcul ne bouge pas d'une minute à l'autre. Les
#: recalculer à chaque minute coûterait trois cents fois le nécessaire.
_STATIQUES = {"poc", "valeur", "lvn"}


# ---------------------------------------------------------------------------
# Les trois confirmations : ce qui tient la lecture, et ce qui la brise
# ---------------------------------------------------------------------------

#: Multiple du volume médian de la séance au-delà duquel une barre est dite
#: chargée. La moitié de plus que la minute médiane : c'est déjà rare, la loi
#: du volume étant log-normale de dispersion déclarée, et l'exiger double
#: n'aurait laissé qu'un contact sur cent vingt — une part que l'échantillon
#: ne saurait pas mesurer.
MULT_VOLUME = 1.5

#: `z` d'impact sous lequel la barre est lue comme absorbante. Repris du
#: catalogue, pour que la figure, la table et la loi nulle ne divergent pas.
Z_ABSORPTION = C.Z_ABSORPTION

#: Part de l'étendue qu'une mèche doit occuper pour valoir rejet.
PART_MECHE = 0.60

#: Dépassement, en écarts-types d'une minute, qu'une clôture doit franchir
#: pour valoir exécution — et au-delà duquel une absorption ou un rejet est
#: déclaré invalidé.
DEPASSEMENT = 1.0

#: Part du volume de la barre que le delta doit porter dans le sens de la
#: traversée. Un tiers : sur douze sous-pas dont le côté se tire à la règle du
#: tick, c'est un écart-type au-dessus de la barre ordinaire. Le deux tiers
#: qu'on lit parfois n'est pas atteignable par une barre que le hasard
#: construit — ni, sans doute, par beaucoup de vraies.
PART_DELTA = 1.0 / 3.0

#: Minutes pendant lesquelles l'invalidation est guettée.
FENETRE = 15


@dataclass(frozen=True)
class Confirmation:
    """Ce qui doit se produire au contact, et ce qui le dément ensuite."""

    cle: str
    nom: str
    condition: str
    invalidation: str
    #: +1 si la lecture attend la poursuite du mouvement d'approche,
    #: −1 si elle en attend le rejet. C'est ce signe qui oriente la mesure de
    #: la suite du prix : sans lui, une réaction favorable et une réaction
    #: défavorable se compenseraient dans la même colonne.
    sens_attendu: int


CONFIRMATIONS: tuple[Confirmation, ...] = (
    Confirmation(
        "absorption", "Absorption",
        "volume au moins " + num(MULT_VOLUME, 1) + " fois le volume médian, "
        "|z| d'impact sous " + num(Z_ABSORPTION, 2) + ", et clôture qui ne "
        "franchit pas le niveau",
        "une clôture au-delà du niveau de plus d'un écart-type dans les "
        + str(FENETRE) + " minutes",
        -1),
    Confirmation(
        "rejet", "Rejet en mèche",
        "une mèche au-delà du niveau valant au moins "
        + num(100.0 * PART_MECHE, 0) + " % de l'étendue de la barre, et une "
        "clôture revenue du côté d'où le prix venait",
        "une clôture au-delà du niveau de plus d'un écart-type dans les "
        + str(FENETRE) + " minutes",
        -1),
    Confirmation(
        "execution", "Exécution",
        "une clôture au-delà du niveau de plus d'un écart-type d'une minute, "
        "et un delta dans le sens de la traversée pour au moins "
        + num(100.0 * PART_DELTA, 0) + " % du volume de la barre",
        "un retour du prix de l'autre côté du niveau dans les "
        + str(FENETRE) + " minutes",
        +1),
)

_PAR_CONF = {c.cle: c for c in CONFIRMATIONS}


def _pct(v: float, nd: int = 1) -> str:
    return num(100.0 * v, nd) + " %"


@dataclass(frozen=True)
class Critere:
    """Une condition élémentaire d'une confirmation, et ce qu'elle a valu.

    Les figures lisent cette structure, et `_confirme` la lit aussi : une
    planche ne peut donc pas cocher une case que la mesure aurait refusée.
    C'est le même défaut de divergence que celui qui guette une table et sa
    prose, et il se ferme de la même façon — par une source unique.
    """

    libelle: str
    #: Le même critère en un mot, pour les colonnes étroites des figures.
    court: str
    valeur: str
    exige: str
    ok: bool


def criteres(cle: str, barre: Barre, niveau: float, sens: int,
             volume_median: float) -> tuple[Critere, ...]:
    """Les conditions élémentaires de la confirmation `cle`, sur cette barre.

    `sens` est le sens de l'approche : +1 si le prix vient d'en dessous du
    niveau, −1 s'il vient d'au-dessus.
    """
    ecart = sens * (barre.cloture - niveau)
    if cle == "absorption":
        mult = barre.volume / volume_median if volume_median else 0.0
        return (
            Critere("volume de la barre", "volume", num(mult, 2) + "×",
                    "≥ " + num(MULT_VOLUME, 1) + "×", mult >= MULT_VOLUME),
            Critere("|z| d'impact", "|z|", num(abs(barre.z), 2),
                    "≤ " + num(Z_ABSORPTION, 2), abs(barre.z) <= Z_ABSORPTION),
            Critere("clôture face au niveau", "clôture", num(ecart, 2) + " pt",
                    "≤ 0", ecart <= 0.0),
        )
    if cle == "rejet":
        meche = barre.meche(sens)
        return (
            Critere("mèche au-delà du niveau", "mèche", _pct(meche, 0),
                    "≥ " + num(100.0 * PART_MECHE, 0) + " %",
                    meche >= PART_MECHE),
            Critere("clôture face au niveau", "clôture", num(ecart, 2) + " pt",
                    "≤ 0", ecart <= 0.0),
        )
    if cle == "execution":
        part = barre.delta / barre.volume if barre.volume else 0.0
        return (
            Critere("clôture au-delà du niveau", "clôture", num(ecart, 2) + " pt",
                    "≥ " + num(DEPASSEMENT * q.SIGMA_1MIN, 2) + " pt",
                    ecart >= DEPASSEMENT * q.SIGMA_1MIN),
            Critere("delta de la barre", "delta", _pct(sens * part, 0),
                    "≥ " + num(100.0 * PART_DELTA, 0) + " %",
                    sens * part >= PART_DELTA),
        )
    raise KeyError(f"confirmation inconnue : {cle}")


def _confirme(cle: str, barre: Barre, niveau: float, sens: int,
              volume_median: float) -> bool:
    """La confirmation `cle` tient-elle sur cette barre ?

    Elle tient quand **tous** ses critères tiennent, et il n'existe pas
    d'autre définition dans le dépôt : la table, la figure et la mesure lisent
    la même liste.
    """
    return all(c.ok for c in criteres(cle, barre, niveau, sens, volume_median))


def _invalide(cle: str, barres: tuple[Barre, ...], i: int, niveau: float,
              sens: int) -> bool:
    """La confirmation est-elle démentie dans la fenêtre déclarée ?"""
    fin = min(i + 1 + FENETRE, len(barres))
    suite = barres[i + 1:fin]
    if cle in ("absorption", "rejet"):
        return any(sens * (b.cloture - niveau) >= DEPASSEMENT * q.SIGMA_1MIN
                   for b in suite)
    return any(sens * (b.cloture - niveau) <= 0.0 for b in suite)


# ---------------------------------------------------------------------------
# Les setups : un niveau, une confirmation, une attente
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Setup:
    """Les quatre termes réunis, et le nom d'usage de l'ensemble."""

    niveau: str
    confirmation: str
    nom: str
    attente: str

    @property
    def cle(self) -> str:
        return f"{self.niveau}-{self.confirmation}"

    @property
    def horizon_min(self) -> float:
        return _PAR_NIVEAU[self.niveau].horizon_min

    @property
    def famille(self) -> str:
        return _PAR_NIVEAU[self.niveau].famille


SETUPS: tuple[Setup, ...] = (
    Setup("poc", "absorption", "Absorption au point de contrôle",
          "le prix s'arrête sur le prix le plus échangé et repart d'où il "
          "venait"),
    Setup("poc", "execution", "Traversée du point de contrôle",
          "l'aimant cède et la séance change de zone de valeur"),
    Setup("valeur", "rejet", "Rejet du bord de valeur",
          "le bord tient et le prix retourne vers le point de contrôle"),
    Setup("valeur", "execution", "Acceptation hors de la valeur",
          "la valeur se déplace et le prix s'établit au-delà"),
    Setup("lvn", "execution", "Traversée d'un nœud de faible volume",
          "le vide se traverse d'un trait, faute de liquidité pour retenir"),
    Setup("lvn", "rejet", "Rejet d'un nœud de faible volume",
          "le prix refuse d'entrer dans le vide et repart"),
    Setup("vwap", "rejet", "Rejet de la deuxième bande",
          "le prix a trop dévié de son coût moyen et revient vers lui"),
    Setup("vwap", "execution", "Sortie de bande",
          "la déviation s'installe au lieu de se corriger"),
    Setup("pivot", "rejet", "Retest de pivot tenu",
          "l'ancien extrême tient au retour et la structure se poursuit"),
    Setup("pivot", "execution", "Rupture de structure",
          "le pivot cède, ce qui retourne la lecture de tendance"),
    Setup("ote", "absorption", "Absorption en zone d'entrée",
          "le retracement s'épuise sur la zone et la jambe reprend"),
    Setup("ote", "rejet", "Rejet en zone d'entrée",
          "la mèche marque le fond du retracement et la jambe reprend"),
)

_PAR_SETUP = {s.cle: s for s in SETUPS}


# ---------------------------------------------------------------------------
# Mesure
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Contact:
    """Un contact de niveau, avec ce qu'il porte et ce qu'il devient."""

    seance: int
    minute: int
    niveau: float
    sens: int
    confirmations: frozenset[str]
    invalidations: frozenset[str]
    #: Déplacement du prix, en points, du contact jusqu'à l'horizon, **orienté
    #: dans le sens de l'approche**. L'orientation par l'attente du setup se
    #: fait plus tard : un même contact sert à plusieurs confirmations, dont
    #: les attentes sont contraires.
    suite: dict[float, float]
    #: Excursions extrêmes sur l'horizon, mêmes conventions.
    pic: dict[float, float]
    creux: dict[float, float]


#: Les horizons à mesurer sur chaque contact — l'union de ceux des niveaux.
HORIZONS = tuple(sorted({n.horizon_min for n in NIVEAUX}))


def _independants(lot, horizon_min: float):
    """Ne garde, dans chaque séance, que des contacts à fenêtres disjointes.

    **C'est le contrôle qui décide de tout le chapitre.** Un nœud de faible
    volume donne onze contacts par demi-séance ; leurs fenêtres d'une heure se
    recouvrent presque toutes, si bien que mille contacts ne portent pas mille
    fois l'information d'un seul. Mesurée sur le lot brut, l'excursion
    favorable médiane s'écartait de l'excursion défavorable d'un bon point —
    assez pour qu'on croie lire un effet là où il n'y a que trois cents chemins
    comptés mille fois.

    La règle est celle de l'embargo du module `overfit` : dans une séance, on
    garde le premier contact, puis le premier suivant dont la fenêtre ne
    recouvre plus la précédente. Les fréquences, elles, continuent d'être
    comptées sur le lot entier — le débit d'occasions n'a rien à voir avec
    l'indépendance des observations.
    """
    garde = []
    seance = -1
    limite = -1.0
    for c in lot:
        if c.seance != seance:
            seance, limite = c.seance, -1.0
        if c.minute >= limite:
            garde.append(c)
            limite = c.minute + horizon_min
    return garde


def _mediane(v: list[float]) -> float:
    v = sorted(v)
    n = len(v)
    if not n:
        return 0.0
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def _contacts_seance(barres: tuple[Barre, ...], cle_niveau: str,
                     index: int) -> list[Contact]:
    """Tous les contacts d'un niveau sur une séance, avec leur suite.

    Le contact est neuf quand la barre traverse le niveau alors que le prix
    s'en tenait à `ECART_REARME` points au moins ; il se réarme au même écart.
    C'est la même règle pour les six niveaux, ce qui est le point : sans règle
    commune, comparer les familles reviendrait à comparer six façons de
    compter.
    """
    profil = vprofile.from_path([b.cloture for b in barres[:DEBUT]],
                                step=PAS_PROFIL)
    volume_median = _mediane([float(b.volume) for b in barres[:DEBUT]])
    calcul = _CALCUL[cle_niveau]
    fixes = calcul(barres, DEBUT - 1, profil) if cle_niveau in _STATIQUES else ()

    loin: dict[float, bool] = {}
    out: list[Contact] = []
    for i in range(DEBUT, len(barres) - 1):
        niveaux = fixes if cle_niveau in _STATIQUES else calcul(barres, i, profil)
        for niveau in niveaux:
            barre = barres[i]
            arme = loin.get(niveau, True)
            if not (barre.bas <= niveau <= barre.haut):
                if abs(barre.cloture - niveau) >= ECART_REARME:
                    loin[niveau] = True
                continue
            if not arme:
                continue
            loin[niveau] = False
            precedent = barres[i - 1].cloture
            sens = 1 if precedent < niveau else -1
            confirmees = frozenset(
                c.cle for c in CONFIRMATIONS
                if _confirme(c.cle, barre, niveau, sens, volume_median))
            invalidees = frozenset(
                c for c in confirmees if _invalide(c, barres, i, niveau, sens))
            suite, pic, creux = {}, {}, {}
            for h in HORIZONS:
                fin = min(i + int(h), len(barres) - 1)
                fenetre = barres[i + 1:fin + 1]
                if not fenetre:
                    suite[h] = pic[h] = creux[h] = 0.0
                    continue
                base = barre.cloture
                suite[h] = sens * (barres[fin].cloture - base)
                hauts = [sens * (b.haut - base) for b in fenetre]
                bas = [sens * (b.bas - base) for b in fenetre]
                pic[h] = max(hauts + bas)
                creux[h] = min(hauts + bas)
            out.append(Contact(index, i, niveau, sens, confirmees, invalidees,
                               suite, pic, creux))
    return out


@lru_cache(maxsize=16)
def contacts(cle_niveau: str,
             derive_par_heure: float = 0.0) -> tuple[Contact, ...]:
    """Tous les contacts d'un niveau, sur toutes les séances."""
    out: list[Contact] = []
    for index, barres in enumerate(seances(derive_par_heure)):
        out.extend(_contacts_seance(barres, cle_niveau, index))
    return tuple(out)


@dataclass(frozen=True)
class Mesure:
    """Ce qu'un setup vaut quand il n'y a rien à lire."""

    contacts: int             # contacts bruts observés
    par_seance: float         # contacts bruts par séance
    confirmes: int
    part_confirmee: float     # P(confirmation | contact)
    retenus_par_seance: float
    part_invalidee: float     # P(démenti | confirmation)
    independants: int         # confirmations à fenêtres disjointes
    p_brut: float             # P(sens attendu | contact), sans confirmation
    p_confirme: float         # P(sens attendu | contact confirmé)
    mfe: float                # excursion favorable médiane, confirmés
    mae: float                # excursion défavorable médiane, confirmés

    @property
    def facteur_filtre(self) -> float:
        """De combien la confirmation divise les occasions."""
        return 1.0 / self.part_confirmee if self.part_confirmee > 0 else math.inf


@lru_cache(maxsize=64)
def mesurer(cle: str, derive_par_heure: float = 0.0) -> Mesure:
    """Le setup, mesuré de bout en bout sur les séances simulées."""
    setup = _PAR_SETUP[cle]
    conf = _PAR_CONF[setup.confirmation]
    h = setup.horizon_min
    attendu = conf.sens_attendu

    tous = contacts(setup.niveau, derive_par_heure)
    n_seances = float(len(seances(derive_par_heure)))
    retenus = [c for c in tous if setup.confirmation in c.confirmations]
    demenis = sum(1 for c in retenus if setup.confirmation in c.invalidations)

    # Les fréquences se comptent sur le lot entier, les réactions sur les
    # seules fenêtres disjointes : ce sont deux questions différentes.
    libres = _independants(tous, h)
    retenus_libres = _independants(retenus, h)

    def part_favorable(lot) -> float:
        if not lot:
            return 0.0
        return sum(1 for c in lot if attendu * c.suite[h] > 0.0) / len(lot)

    if retenus_libres:
        # L'excursion est mesurée dans le sens **attendu** : un rejet attend
        # que le prix reparte, une exécution qu'il poursuive. Mesurées dans le
        # sens de l'approche, les deux se compenseraient dans la même colonne.
        pics = [attendu * (c.pic[h] if attendu > 0 else c.creux[h])
                for c in retenus_libres]
        creux = [attendu * (c.creux[h] if attendu > 0 else c.pic[h])
                 for c in retenus_libres]
        mfe, mae = _mediane(pics), _mediane(creux)
    else:
        mfe = mae = 0.0

    return Mesure(
        len(tous), len(tous) / n_seances, len(retenus),
        len(retenus) / len(tous) if tous else 0.0,
        len(retenus) / n_seances,
        demenis / len(retenus) if retenus else 0.0,
        len(retenus_libres),
        part_favorable(libres), part_favorable(retenus_libres), mfe, mae)


#: Niveau d'indice ajouté aux prix pour l'affichage. Il ne sert qu'aux
#: figures, où un axe gradué autour de zéro se lirait comme un rendement et
#: non comme un prix ; aucune mesure ne le voit.
PRIX_BASE = 6000.0


def exemple(cle_niveau: str, cle_confirmation: str,
            dementi: bool | None = None) -> Contact | None:
    """Le premier contact que la confirmation retient, dans l'ordre des graines.

    Rien n'y est choisi à la main. `dementi` permet de demander un exemple
    tenu ou un exemple démenti — les deux existent en abondance, et une figure
    qui ne montrerait que des exemples tenus mentirait par sélection.
    """
    for c in contacts(cle_niveau):
        if cle_confirmation not in c.confirmations:
            continue
        if dementi is not None:
            if (cle_confirmation in c.invalidations) != dementi:
                continue
        return c
    return None


def profil(seance_index: int) -> vprofile.Profile:
    """Le profil de volume de la première demi-séance, celui des niveaux."""
    barres = seances()[seance_index]
    return vprofile.from_path([b.cloture for b in barres[:DEBUT]],
                              step=PAS_PROFIL)


def contexte(c: Contact) -> tuple[tuple[Barre, ...], float]:
    """La séance d'un contact et son volume médian de première moitié."""
    barres = seances()[c.seance]
    return barres, _mediane([float(b.volume) for b in barres[:DEBUT]])


def barre_fp(c: Contact):
    """La barre du contact, convertie en barre de footprint du module `fp`.

    Le passage par `footprint.Bar` n'est pas cosmétique : il donne accès aux
    déséquilibres diagonaux et à leur loi nulle exacte, qui sont déjà écrits
    et testés ailleurs. Une figure qui les recalculerait pourrait en diverger.
    """
    barre, cellules = footprint(c.seance, c.minute)
    return barre, fp.Bar(tuple(fp.Cell(x.prix, x.bid, x.ask) for x in cellules),
                         barre.ouverture, barre.cloture)


# ---------------------------------------------------------------------------
# Le contrôle : les douze setups mis en commun
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Poule:
    """Les douze setups mis en commun, orientés chacun par son attente.

    Une part mesurée sur vingt confirmations ne se publie pas ; mise en commun
    sur les douze, elle porte plusieurs milliers d'observations et tranche.
    C'est là, et pas dans une cellule isolée de la table, que se lit le
    résultat du chapitre.
    """

    n_brut: int
    p_brut: float
    n_confirme: int
    p_confirme: float
    n_poursuite: int
    p_poursuite: float
    n_rejet: int
    p_rejet: float
    #: Excursions médianes, en écarts-types d'horizon : c'est la seule unité
    #: qui permette de mettre en commun des lectures de trente minutes et de
    #: deux heures.
    mfe: float
    mae: float

    @property
    def rapport(self) -> float:
        """Excursion favorable rapportée à l'excursion défavorable.

        Un rapport de un est la symétrie exacte. Une **ligne** de la table
        s'en écarte de vingt pour cent sans que rien ne se passe — c'est le
        bruit d'échantillonnage d'un lot de quelques centaines de fenêtres
        disjointes. La mise en commun, elle, tranche.
        """
        return self.mfe / abs(self.mae) if self.mae else math.inf

    @property
    def demi_intervalle(self) -> float:
        """Demi-intervalle à 95 % de la part confirmée, en points de %."""
        n = max(self.n_confirme, 1)
        return 100.0 * 1.96 * math.sqrt(0.25 / n)


@lru_cache(maxsize=4)
def poule(derive_par_heure: float = 0.0) -> Poule:
    """Les douze setups mis en commun, à dérive déclarée."""
    brut = conf = pours = rej = 0
    n_brut = n_conf = n_pours = n_rej = 0
    pics: list[float] = []
    creux: list[float] = []
    for s in SETUPS:
        attendu = _PAR_CONF[s.confirmation].sens_attendu
        h = s.horizon_min
        tous = contacts(s.niveau, derive_par_heure)
        for c in _independants(tous, h):
            n_brut += 1
            brut += attendu * c.suite[h] > 0.0
        retenus = [c for c in tous if s.confirmation in c.confirmations]
        sigma_h = q.SIGMA_1MIN * math.sqrt(h)
        for c in _independants(retenus, h):
            favorable = attendu * c.suite[h] > 0.0
            n_conf += 1
            conf += favorable
            pics.append(attendu * (c.pic[h] if attendu > 0 else c.creux[h])
                        / sigma_h)
            creux.append(attendu * (c.creux[h] if attendu > 0 else c.pic[h])
                         / sigma_h)
            if attendu > 0:
                n_pours += 1
                pours += favorable
            else:
                n_rej += 1
                rej += favorable
    return Poule(n_brut, brut / max(n_brut, 1), n_conf, conf / max(n_conf, 1),
                 n_pours, pours / max(n_pours, 1),
                 n_rej, rej / max(n_rej, 1),
                 _mediane(pics), _mediane(creux))


# ---------------------------------------------------------------------------
# Ce que la confirmation coûte
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Cout:
    """Le prix d'une confirmation, en décisions et en années."""

    decisions: float          # décisions requises pour établir la géométrie
    par_an_brut: float
    par_an_retenu: float
    annees_brut: float
    annees_retenu: float

    @property
    def facteur(self) -> float:
        return (self.annees_retenu / self.annees_brut
                if self.annees_brut > 0 else math.inf)


def cout(cle: str) -> Cout:
    """Le délai d'établissement, avec et sans la confirmation.

    Le nombre de décisions ne change pas : il ne dépend que de la géométrie —
    stop à l'écart-type d'horizon, cible à deux fois le stop, friction de
    référence — et la confirmation n'en touche aucun terme. Seul le débit
    d'occasions change, et le délai est leur quotient. **C'est tout le coût
    d'une confirmation, et il est exactement mesurable.**
    """
    setup = _PAR_SETUP[cle]
    m = mesurer(cle)
    n = C.decisions_pour(setup.horizon_min)
    brut = m.par_seance * C.SEANCES_PAR_AN
    retenu = m.retenus_par_seance * C.SEANCES_PAR_AN
    return Cout(n, brut, retenu,
                n / brut if brut > 0 else math.inf,
                n / retenu if retenu > 0 else math.inf)


def derive_compensatrice(cle: str) -> float:
    """La dérive qu'une confirmation devrait apporter pour valoir son prix.

    Le raisonnement tient en une ligne. La confirmation multiplie le délai par
    `F`. Pour que le délai revienne à ce qu'il était, il faudrait que le nombre
    de décisions requis soit divisé par `F` — or ce nombre varie comme
    l'inverse du carré de l'écart de taux à établir. Il faut donc que la
    confirmation multiplie cet écart par `√F`, ce qui se traduit en dérive par
    la même règle que le seuil de rentabilité.

    Rendu en points par heure, à comparer aux deux bornes du domaine plausible
    du document nº 1. Sous la borne basse, la confirmation se rembourse dès
    qu'elle capte une dérive ordinaire ; entre les deux bornes, il lui faut une
    dérive haute ; au-dessus, **elle ne peut pas se rembourser**, quel que soit
    son pouvoir prédictif réel.

    L'approximation est écrite plutôt que cachée : la conversion d'un écart de
    taux en dérive est prise au premier ordre, la probabilité de toucher étant
    à peu près linéaire en `µ` au voisinage de zéro. Elle suffit à ranger les
    douze setups ; elle ne suffirait pas à publier une troisième décimale.
    """
    setup = _PAR_SETUP[cle]
    c = cout(cle)
    if c.facteur == math.inf or c.facteur <= 0:
        return math.inf
    a, b, friction = C.geometrie(setup.horizon_min)
    mu = required_drift(a, b, q.SIGMA_1MIN, friction) * 60.0
    return mu * math.sqrt(c.facteur)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


def verdict(cle: str) -> str:
    """Le verdict d'une confirmation, calculé et jamais écrit.

    Trois cas, décidés par la position de la dérive compensatrice dans le
    domaine plausible. L'ordre des lignes de la table en découle ; changer une
    borne du domaine change les verdicts sans qu'une ligne de prose bouge.
    """
    mu = derive_compensatrice(cle)
    basse, haute = seuil.PLAUSIBLE_DRIFT_PER_HOUR
    if mu <= basse:
        return "une dérive ordinaire suffit"
    if mu <= haute:
        return "il faut une dérive haute"
    return "hors du domaine : irremboursable"


def table_grammaire() -> Table:
    """Les quatre termes, écrits avant toute mesure."""
    rows = []
    for n in NIVEAUX:
        for c in CONFIRMATIONS:
            cle = f"{n.cle}-{c.cle}"
            if cle not in _PAR_SETUP:
                continue
            s = _PAR_SETUP[cle]
            rows.append([s.nom, n.calcul, c.condition, s.attente,
                         c.invalidation])
    return Table(
        "grammaire",
        "Les douze setups, terme à terme : où, quoi, ce qu'on en attend, et "
        "ce qui l'annule.",
        ["Setup", "Le niveau, et comment il se calcule",
         "La confirmation exigée", "Ce qu'on en attend", "L'invalidation"],
        rows,
        wide=True,
        wrap_cols=[1, 2, 3, 4],
        note="Rien de cette table n'est mesuré : elle est **écrite d'avance**, "
             "et c'est sa fonction. Un setup dont la confirmation se choisit "
             "après coup n'est pas un setup, c'est un commentaire. Les cinq "
             "seuils qu'elle contient — deux fois le volume médian, un z sous "
             + num(Z_ABSORPTION, 2) + ", une mèche à "
             + num(100.0 * PART_MECHE, 0) + " % de l'étendue, un dépassement "
             "d'un écart-type, un delta à " + num(100.0 * PART_DELTA, 0)
             + " % du volume — sont déclarés une fois et servent aux six "
               "familles. Les déplacer déplacerait toutes les fréquences de "
               "la table suivante, ce qui est précisément le piège du "
               "paramètre non observable.")


def table_confirmation() -> Table:
    """Ce que la confirmation change, et ce qu'elle ne change pas."""
    rows = []
    for s in SETUPS:
        m = mesurer(s.cle)
        rows.append([
            s.nom,
            s.famille,
            num(m.par_seance, 2),
            _pct(m.part_confirmee),
            C._grand(float(m.independants)),
            _pct(m.part_invalidee),
            _pct(m.p_brut),
            _pct(m.p_confirme),
            num(m.mfe, 2) + " / " + num(m.mae, 2),
        ])
    pool = poule()
    pooled = ["Les douze, mis en commun", "—", "—", "—",
              C._grand(float(pool.n_confirme)), "—",
              _pct(pool.p_brut), _pct(pool.p_confirme),
              "rapport " + num(pool.rapport, 2)]
    return Table(
        "confirmation",
        "Les douze setups mesurés sur "
        + str(SEANCES) + " séances sans dérive, du contact brut à la "
        "confirmation démentie.",
        ["Setup", "Famille", "Contacts par séance", "Part confirmée",
         "Observations indépendantes", "Part démentie",
         "P(sens attendu), contact brut", "P(sens attendu), confirmé",
         "MFE / MAE, confirmés"],
        rows + [pooled],
        wide=True,
        rules_after=[len(rows) - 1],
        note="Les deux colonnes de probabilité sont le cœur de la table, et "
             "la dernière ligne dit ce qu'elles disent : **un demi**. La "
             "confirmation ne déplace pas la suite du prix — ni le contact "
             "brut ni le contact confirmé ne battent le pile ou face, "
             "et l'excursion favorable médiane vaut l'excursion défavorable "
             "à " + num(100.0 * abs(pool.rapport - 1.0), 0) + " % près. Ce "
             "n'est pas un défaut des confirmations retenues : c'est le "
             "théorème d'arrêt optionnel, qui ne connaît pas les conditions "
             "d'entrée. **Les cellules isolées se lisent avec leur effectif**, "
             "que la table publie exprès, et il ne compte que des fenêtres "
             "**disjointes** — deux contacts dont les heures suivantes se "
             "recouvrent ne sont pas deux observations, et les compter pour "
             "telles faisait apparaître des écarts d'un point sur les "
             "excursions. Une part mesurée sur trente fenêtres porte neuf "
             "points de bruit d'échantillonnage, et "
             "seule la ligne de mise en commun — " + C._grand(float(pool.n_confirme))
             + " fenêtres disjointes, soit un demi-intervalle de "
             + num(pool.demi_intervalle, 1) + " point de pourcentage — "
             "tranche. La colonne de la part démentie mérite d'être lue à "
             "côté : la moitié environ des confirmations est démentie dans "
             "les " + str(FENETRE) + " minutes, **alors même qu'elle vient "
             "d'être obtenue**. Ce qui change vraiment est la part confirmée, "
             "que la table suivante convertit en années.")


def table_cout() -> Table:
    """Le prix d'une confirmation, en années."""
    pire = max(SETUPS, key=lambda s: derive_compensatrice(s.cle))
    meilleur = min(SETUPS, key=lambda s: derive_compensatrice(s.cle))
    rows = []
    for s in SETUPS:
        c = cout(s.cle)
        mu = derive_compensatrice(s.cle)
        rows.append([
            s.nom,
            C._horizon(s.horizon_min),
            C._grand(c.decisions),
            C._grand(c.par_an_brut),
            C._grand(c.par_an_retenu),
            C._ans(c.annees_brut),
            C._ans(c.annees_retenu),
            "×" + num(c.facteur, 1),
            num(mu, 2),
            verdict(s.cle),
        ])
    return Table(
        "cout",
        "Ce que la confirmation coûte : mêmes décisions requises, moins "
        "d'occasions pour les obtenir.",
        ["Setup", "Horizon", "Décisions requises", "Contacts par an",
         "Confirmés par an", "Délai sans confirmation", "Délai avec",
         "Facteur", "µ compensatrice (pt/h)", "Verdict"],
        rows,
        wide=True,
        note="La colonne des décisions requises ne dépend que de la "
             "géométrie : stop à l'écart-type d'horizon, cible à deux fois le "
             "stop, friction de référence. **La confirmation n'en touche aucun "
             "terme**, et le nombre ne bouge donc pas d'une ligne à l'autre à "
             "horizon égal. Seul le débit d'occasions change, et le délai est "
             "leur quotient : exiger la confirmation multiplie l'attente par "
             "le facteur affiché. La dérive compensatrice est ce que la "
             "confirmation devrait apporter pour rembourser ce délai — elle "
             "vaut la dérive requise du même horizon multipliée par la racine "
             "du facteur, le nombre de décisions variant comme l'inverse du "
             "carré de l'écart de taux. Le verdict est calculé, jamais écrit : "
             "il compare cette dérive aux deux bornes du domaine plausible du "
             "document n<sup>o</sup> 1, " + num(seuil.PLAUSIBLE_DRIFT_PER_HOUR[0], 1)
             + " et " + num(seuil.PLAUSIBLE_DRIFT_PER_HOUR[1], 1)
             + " point par heure. Le classement qui en sort n'était pas "
               "cherché et il est net : **la confirmation la plus exigeante "
               "est celle qui se rembourse le plus mal**. La ligne la plus "
               "coûteuse est « " + pire.nom.lower() + " » — un contact retenu "
               "sur " + num(1.0 / mesurer(pire.cle).part_confirmee, 0)
             + ", et une dérive de " + num(derive_compensatrice(pire.cle), 2)
             + " point par heure à trouver en retour. La moins coûteuse est "
               "« " + meilleur.nom.lower() + " », qui se contente de "
             + num(derive_compensatrice(meilleur.cle), 2) + ". Filtrer plus "
               "dur ne rend donc pas la lecture meilleure : cela déplace la "
               "charge de la preuve vers un marché qu'il faut supposer plus "
               "favorable.")


TABLES = (table_grammaire, table_confirmation, table_cout)


def all_tables() -> dict[str, Table]:
    return {t.__name__.removeprefix("table_"): t() for t in TABLES}


# ---------------------------------------------------------------------------
# Scalaires cités par la prose
# ---------------------------------------------------------------------------


def _extremes(fn) -> tuple[Setup, Setup]:
    ordonnes = sorted(SETUPS, key=fn)
    return ordonnes[0], ordonnes[-1]


def ecart_maximal() -> float:
    """Le plus grand écart à un demi, en points de pourcentage, sur les douze.

    C'est le contrôle qui autorise la lecture de la table : si un setup
    s'écartait franchement d'un demi sous prix sans dérive, ce serait le
    détecteur qu'il faudrait relire, pas le marché.
    """
    return max(abs(mesurer(s.cle).p_confirme - 0.5) for s in SETUPS) * 100.0


def values() -> dict[str, str]:
    filtrant, permissif = _extremes(lambda s: mesurer(s.cle).part_confirmee)
    m_filtrant = mesurer(filtrant.cle)
    m_permissif = mesurer(permissif.cle)
    facteurs = [cout(s.cle).facteur for s in SETUPS]
    parts = [mesurer(s.cle).part_confirmee for s in SETUPS]
    demenis = [mesurer(s.cle).part_invalidee for s in SETUPS]
    basse, haute = seuil.PLAUSIBLE_DRIFT_PER_HOUR
    mus = {s.cle: derive_compensatrice(s.cle) for s in SETUPS}
    ordinaire = [s for s in SETUPS if mus[s.cle] <= basse]
    irremboursable = [s for s in SETUPS if mus[s.cle] > haute]
    pool = poule()
    sous_derive = poule(haute)
    pire = max(SETUPS, key=lambda s: mus[s.cle])
    delais = {s.cle: cout(s.cle) for s in SETUPS}
    long = max(SETUPS, key=lambda s: delais[s.cle].annees_retenu)

    return {
        "u_setups": str(len(SETUPS)),
        "u_niveaux": str(len(NIVEAUX)),
        "u_confirmations": str(len(CONFIRMATIONS)),
        "u_familles": str(len({n.famille for n in NIVEAUX})),
        "u_seances": C._grand(float(SEANCES)),
        "u_sous_pas": str(SOUS_PAS),
        "u_correlation": num(correlation_delta(), 2),
        "u_correlation_cvd": num(C.CORRELATION_CVD, 2),

        "u_mult_volume": num(MULT_VOLUME, 1),
        "u_z": num(Z_ABSORPTION, 2),
        "u_meche": num(100.0 * PART_MECHE, 0),
        "u_delta": num(100.0 * PART_DELTA, 0),
        "u_fenetre": str(FENETRE),
        "u_pivot": num(SEUIL_PIVOT, 0),

        "u_filtrant": filtrant.nom.lower(),
        "u_filtrant_part": _pct(m_filtrant.part_confirmee),
        "u_filtrant_facteur": num(cout(filtrant.cle).facteur, 0),
        "u_permissif": permissif.nom.lower(),
        "u_permissif_part": _pct(m_permissif.part_confirmee),

        "u_part_min": _pct(min(parts)),
        "u_part_max": _pct(max(parts)),
        "u_facteur_min": num(min(facteurs), 1),
        "u_facteur_max": num(max(facteurs), 0),
        "u_dementi_min": _pct(min(demenis)),
        "u_dementi_max": _pct(max(demenis)),
        "u_ecart": num(ecart_maximal(), 1),
        "u_ordinaire": str(len(ordinaire)),
        "u_irremboursable": str(len(irremboursable)),
        "u_derive_basse": num(basse, 1),
        "u_derive_haute": num(haute, 1),
        "u_mu_min": num(min(mus.values()), 2),
        "u_mu_max": num(max(mus.values()), 2),
        "u_pire": pire.nom.lower(),

        "u_pool_brut_n": C._grand(float(pool.n_brut)),
        "u_pool_brut": _pct(pool.p_brut),
        "u_pool_n": C._grand(float(pool.n_confirme)),
        "u_pool": _pct(pool.p_confirme),
        "u_pool_demi": num(pool.demi_intervalle, 1),
        "u_pool_poursuite": _pct(pool.p_poursuite),
        "u_pool_rejet": _pct(pool.p_rejet),
        "u_pool_rapport": num(pool.rapport, 2),

        "u_derive_pool": _pct(sous_derive.p_confirme),
        "u_derive_poursuite": _pct(sous_derive.p_poursuite),
        "u_derive_rejet": _pct(sous_derive.p_rejet),
        "u_derive_gain": num(100.0 * (sous_derive.p_poursuite
                                      - pool.p_poursuite), 1),
        "u_derive_perte": num(100.0 * (pool.p_rejet
                                       - sous_derive.p_rejet), 1),

        "u_long": long.nom.lower(),
        "u_long_brut": C._ans(delais[long.cle].annees_brut),
        "u_long_retenu": C._ans(delais[long.cle].annees_retenu),
        "u_court_brut": C._ans(min(c.annees_brut for c in delais.values())),
    }


def main() -> None:
    print(f"setups : {len(SETUPS)} sur {len(NIVEAUX)} niveaux, "
          f"{SEANCES} séances sans dérive")
    print(f"corrélation delta/rendement mesurée : {correlation_delta():.3f}\n")
    for table in TABLES:
        print(table().to_text())
        print()


if __name__ == "__main__":
    main()
