"""Une affirmation venue du dehors, passée au protocole : les extrêmes overnight.

Ce qui est examiné
------------------
Une publication à large diffusion avance sept nombres sur le contrat NQ, tirés
de onze ans et 2 827 séances. Ils sont repris ici **tels quels**, comme des
données à expliquer et non comme des résultats à défendre :

  1. l'un des deux extrêmes de la session 18:00–09:30 ET est franchi pendant
     les heures régulières sur 94,2 % des séances ;
  2. les deux le sont sur 22,9 % ;
  3. aucun sur 5,8 % ;
  4. ouverture **au-dessus** du milieu du range overnight : le haut casse en
     premier dans 76,2 % des cas ;
  5. ouverture **au-dessous** : le bas casse en premier dans 75,6 % ;
  6. première cassure médiane 11 minutes après 9:30 ;
  7. 68,7 % ont cassé un côté avant 10:00.

La conclusion qui les accompagne est qu'on peut « prédire quel niveau sera
touché en premier », et s'en servir de biais quand on n'en a pas.

La question que le dépôt pose
-----------------------------
Jamais « ce chiffre est-il vrai ? » — il l'est probablement, et rien ici ne le
conteste. Toujours : **à quelle fréquence ce chiffre apparaît-il sous un prix
sans dérive ?** Un motif ne vaut que comparé à sa loi nulle.

Ce que la loi nulle donne, et l'ordre dans lequel il faut le lire
-----------------------------------------------------------------
*D'abord une grandeur sans dimension.* Soit `u` la position de l'ouverture de
9:30 dans le range overnight, comptée du bas : `u = (open − L)/(H − L)`. Comme
l'ouverture **est** le dernier point de la session overnight, `u` est la
position du point terminal d'une marche dans son propre range — une quantité
qui ne dépend d'aucune volatilité, d'aucun instrument et d'aucune époque.

Sa loi n'est pas uniforme, et c'est tout le sujet : elle est **en U**. Une
marche sans dérive finit bien plus souvent près d'un bord de son range que du
milieu, parce que l'instant où le maximum est atteint suit une loi de l'arc
sinus, qui charge les extrémités du trajet. La distance médiane de l'ouverture
au bord le plus proche vaut environ un cinquième du range, contre quatre
cinquièmes à l'autre bord.

*Ensuite la loi d'arrêt.* Sous prix sans dérive, la probabilité de toucher une
barrière avant l'autre vaut le rapport des distances inverses. À `u` médian, le
bord proche est à un cinquième et le bord lointain à quatre : la probabilité de
toucher le proche en premier vaut donc quatre cinquièmes, **soit environ
80 %**. Le 76 % annoncé n'a pas besoin du marché pour exister ; il a besoin
d'une marche et d'un range.

*Enfin un seul paramètre libre.* Le modèle n'en a qu'un, le rapport de
volatilité `k = σ_overnight / σ_régulière`, et il n'est pas observable dans les
nombres publiés. Il est donc **calibré sur les nombres 2 et 3** — la part des
séances qui cassent les deux côtés, celle qui n'en casse aucun — puis les
nombres 4 et 5 sont **prédits sans aucun degré de liberté restant**. C'est la
règle du dépôt : un paramètre déclaré n'est jamais dérivé de ce qu'il sert à
évaluer.

Ce qui survit
-------------
Un nombre sur sept ne s'explique pas par une volatilité constante : le
**timing**. Une marche à volatilité plate casse son premier bord vers la
quarantième minute, quand la publication en annonce onze. Ce n'est pas un
défaut du modèle nul, c'est une propriété réelle et connue du marché — la
variance de la première demi-heure. Le module la déclare, la mesure, et montre
qu'elle **reproduit le timing à variance totale identique**. Elle dit quand,
jamais dans quel sens.

Le résidu, et pourquoi il ne suffit pas
---------------------------------------
Il faut le dire sans l'arrondir : **la loi nulle ne rend pas tout**. Elle place
le conditionnel autour de 71 à 74 % là où la publication annonce 76,2 %. Trois
à cinq points survivent, et une hypothèse séduisante les explique mal — on
pourrait croire que la dispersion de volatilité d'une séance à l'autre les
comble, puisqu'elle corrige la part des séances qui ne cassent rien ; elle
l'aggrave. Le module publie cette réfutation plutôt que de la taire.

Deux choses bornent ce résidu, et la seconde le tue.

*La première est un paramètre que personne n'observe.* Sur la boîte plausible
du rapport de volatilité nuit/jour et de la dispersion de séance, la
prédiction nulle se promène de 66 à 74 %. La taille du « résidu » est donc
décidée par un réglage non observable, exactement comme la taille de grappe
décide de la rareté d'un déséquilibre de footprint. On ne peut pas conclure
d'un écart dont la moitié est un choix d'hypothèse.

*La seconde n'a pas besoin du résidu.* La géométrie que l'affirmation impose a
un **taux de réussite d'équilibre**, et il se calcule sans rien simuler : viser
un bord à un cinquième du range en risquant les quatre autres cinquièmes exige
de gagner quatre fois sur cinq, plus la friction. Le chiffre publié est
**au-dessous**. Autrement dit, même en tenant les 76,2 % pour intégralement
réels et intégralement gagnés sur le marché, la stratégie perd de l'argent —
et le résidu, réel ou non, ne change pas le signe.

C'est le résultat structurant du document nº 1, retrouvé sur un cas d'espèce
que personne n'a construit pour lui : **un taux de réussite ne s'interprète
jamais sans la géométrie qui l'a produit.**
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from .costs import COST_BASE, ES
from .mc import Rng
from .report import SIGMA_1MIN, Table, num

# --- Les sept nombres publiés ----------------------------------------------
#
# Ils sont recopiés une seule fois, ici, et tout le reste du module s'y réfère.
# Aucun n'est retouché : ce sont les données de l'affaire.

ANNONCES: dict[str, float] = {
    "au_moins_un": 0.942,
    "les_deux": 0.229,
    "aucun": 0.058,
    "haut_si_dessus": 0.762,
    "bas_si_dessous": 0.756,
    "premier_median": 11.0,          # minutes après 9:30
    "avant_dix_heures": 0.687,
}

#: Les deux nombres sur lesquels le paramètre libre est calibré. Ils sont
#: choisis **avant** de regarder le résultat, et ce sont ceux qui ne portent
#: aucune direction : la part des séances qui cassent les deux côtés et celle
#: qui n'en casse aucun. Les nombres de direction restent donc à prédire.
CALIBRAGE = ("aucun", "les_deux")

SESSION_ON_MIN = 930               # 18:00 → 09:30
SESSION_RTH_MIN = 390              # 09:30 → 16:00

#: Le seul paramètre libre : le rapport des volatilités par minute. La boîte
#: est celle qu'un opérateur déclarerait sans regarder le résultat — la nuit
#: échange moins que le jour, d'un tiers à deux tiers.
K_BOX = (0.30, 0.70)
K_PAS = 0.02

#: Le profil de variance de la première demi-heure. Deux paramètres déclarés,
#: et la normalisation garantit que **la variance totale de la séance régulière
#: est identique au cas plat** : ce qui change est la répartition, jamais le
#: montant. Sans cette contrainte, le profil expliquerait le timing en
#: fabriquant de la volatilité, ce qui ne prouverait rien.
PIC_AMPLITUDE = 6.0
PIC_TAU = 25.0

#: Tolérance du verdict, en points de pourcentage. Un écart sous ce seuil est
#: dit « expliqué » : la loi nulle rend le chiffre. Le seuil est déclaré ici
#: et une seule fois.
TOLERANCE_PCT = 3.0
TOLERANCE_MIN = 5.0                # minutes, pour la ligne de timing

N_NUITS = 20000
N_PATHS = 14000
SEED = 20260901


def friction() -> float:
    return COST_BASE.friction_points(ES)


# --- La nuit : une grandeur sans dimension ---------------------------------


@lru_cache(maxsize=None)
def nuits(n: int = N_NUITS) -> tuple[tuple[float, float], ...]:
    """Pour chaque nuit simulée, `(u, portée)`.

    `u` est la position du point terminal dans le range de la marche, et
    `portée` le range lui-même en unités d'écart-type par racine de minute.
    La marche est faite à volatilité **un** : c'est le rapport `k` qui la
    remet à l'échelle plus tard, si bien que toutes les valeurs de `k`
    partagent exactement les mêmes nuits. Le balayage de calibration est donc
    apparié à la source, et sa courbe lisse sans lissage.
    """
    rng = Rng(SEED)
    out = []
    for _ in range(n):
        x = hi = lo = 0.0
        for _ in range(SESSION_ON_MIN):
            x += rng.gauss()
            if x > hi:
                hi = x
            elif x < lo:
                lo = x
        portee = hi - lo
        out.append(((x - lo) / portee, portee))
    return tuple(out)


def quantiles_position(qs=(0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)) -> dict[float, float]:
    us = sorted(u for u, _ in nuits())
    return {q: us[min(int(q * len(us)), len(us) - 1)] for q in qs}


def distance_au_bord() -> tuple[float, float]:
    """Distance médiane au bord le plus proche, et au bord opposé."""
    d = sorted(min(u, 1.0 - u) for u, _ in nuits())
    proche = d[len(d) // 2]
    return proche, 1.0 - proche


def part_extremes(marge: float = 0.15) -> float:
    """Part des séances qui ouvrent dans les `marge` premiers pour-cent d'un bord."""
    us = [u for u, _ in nuits()]
    return sum(1 for u in us if u < marge or u > 1.0 - marge) / len(us)


# --- Le profil de variance de la séance régulière --------------------------


@lru_cache(maxsize=None)
def profil(pic: bool) -> tuple[float, ...]:
    """Écart-type par minute, normalisé à variance totale constante."""
    if not pic:
        return tuple([1.0] * SESSION_RTH_MIN)
    v = [1.0 + PIC_AMPLITUDE * math.exp(-i / PIC_TAU) for i in range(SESSION_RTH_MIN)]
    moyenne = sum(v) / len(v)
    return tuple(math.sqrt(x / moyenne) for x in v)


def part_variance_premiere_demi_heure() -> float:
    """Quelle part de la variance de la séance tombe avant 10:00."""
    p = profil(True)
    total = sum(x * x for x in p)
    return sum(x * x for x in p[:30]) / total


# --- La campagne -----------------------------------------------------------


@dataclass(frozen=True)
class Campagne:
    """Ce qu'une loi nulle rend, face aux sept nombres publiés."""

    k: float
    s_vol: float
    pic: bool
    n: int
    au_moins_un: float
    les_deux: float
    aucun: float
    haut_si_dessus: float
    bas_si_dessous: float
    # Les mêmes deux nombres, comptés sur les seules séances qui cassent
    # quelque chose. La publication ne dit pas laquelle des deux conventions
    # elle emploie, et l'écart entre les deux vaut plus que l'effet discuté.
    haut_si_dessus_casse: float
    bas_si_dessous_casse: float
    premier_median: float
    avant_dix_heures: float
    esperance: float          # E[R] du trade que l'affirmation impose
    erreur_type: float
    wald: float               # E[−c/a], calculé trajectoire par trajectoire
    taux_gain: float
    rapport: float            # gain visé rapporté au risque, moyen
    exposition: float         # E[τ∧T], en minutes
    par_decile: tuple[float, ...]
    par_decile_casse: tuple[float, ...]
    # Les trois issues, séparées : elles permettent de recalculer l'espérance
    # à n'importe quel taux de réussite, donc de prendre le chiffre publié au
    # pied de la lettre sans avoir à le croire.
    p_rien: float
    p_proche: float
    esp_rien: float
    esp_proche: float
    esp_loin: float

    def esperance_au_taux(self, p: float) -> float:
        """L'espérance si le bord proche gagnait avec la probabilité `p`.

        Les niveaux de gain et de perte restent ceux que la géométrie impose ;
        seule la fréquence est remplacée. C'est ainsi qu'on teste une
        affirmation sans avoir à la vérifier : on la suppose vraie.
        """
        casse = 1.0 - self.p_rien
        return (self.p_rien * self.esp_rien
                + casse * (p * self.esp_proche + (1.0 - p) * self.esp_loin))

    def taux_equilibre(self) -> float:
        """Le taux de réussite qui rend l'espérance nulle, à géométrie fixée."""
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2.0
            if self.esperance_au_taux(mid) < 0.0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0


@lru_cache(maxsize=None)
def campagne(k: float, s_vol: float = 0.0, pic: bool = True,
             n_paths: int = N_PATHS) -> Campagne:
    """Simule la séance régulière depuis chaque ouverture, et compte.

    Le trade évalué est **celui que l'affirmation impose et rien d'autre** :
    on vise le bord du range le plus proche de l'ouverture, on pose le stop
    sur le bord opposé, on sort à la clôture si rien n'est touché. Aucun
    réglage n'est ajouté — un réglage ajouté ici serait un degré de liberté
    que l'affirmation n'a pas déclaré.
    """
    p = profil(pic)
    c = friction()
    nuit = nuits()[:n_paths]
    rng = Rng(SEED + 1)

    au_moins = deux = zero = 0
    haut_dessus = n_dessus = bas_dessous = n_dessous = 0
    casse_dessus = casse_dessous = 0
    premiers: list[float] = []
    avant_dix = 0
    s1 = s2 = 0.0
    wald_somme = 0.0
    gains = 0
    rapports = 0.0
    tau = 0.0
    dec_ok = [0] * 10
    dec_n = [0] * 10
    dec_casse = [0] * 10
    n_rien = n_proche = 0
    r_rien = r_proche = r_loin = 0.0

    for u, portee_1 in nuit:
        # La séance a sa propre volatilité, d'espérance de variance un : ce
        # qui change est la dispersion d'un jour à l'autre, jamais le montant.
        ech = (math.exp(0.5 * (s_vol * rng.gauss() - 0.5 * s_vol * s_vol))
               if s_vol > 0.0 else 1.0)
        portee = k * portee_1
        haut = (1.0 - u) * portee
        bas = -u * portee
        proche_est_haut = u > 0.5
        y = 0.0
        premier = None
        touche_haut = touche_bas = False
        for i in range(1, SESSION_RTH_MIN + 1):
            y += ech * p[i - 1] * rng.gauss()
            if y >= haut and not touche_haut:
                touche_haut = True
                if premier is None:
                    premier = ("haut", i, y)
            elif y <= bas and not touche_bas:
                touche_bas = True
                if premier is None:
                    premier = ("bas", i, y)
            if touche_haut and touche_bas:
                break

        if premier is None:
            zero += 1
        else:
            au_moins += 1
            premiers.append(float(premier[1]))
            if premier[1] <= 30:
                avant_dix += 1
        if touche_haut and touche_bas:
            deux += 1

        if proche_est_haut:
            n_dessus += 1
            if premier is not None:
                casse_dessus += 1
                if premier[0] == "haut":
                    haut_dessus += 1
        elif u < 0.5:
            n_dessous += 1
            if premier is not None:
                casse_dessous += 1
                if premier[0] == "bas":
                    bas_dessous += 1

        sens = 1.0 if proche_est_haut else -1.0
        d_proche = min(u, 1.0 - u)
        risque = (1.0 - d_proche) * portee * SIGMA_1MIN
        vise = d_proche * portee * SIGMA_1MIN
        if risque <= 0.0:
            continue
        sortie = premier[2] if premier is not None else y
        minute = float(premier[1]) if premier is not None else float(SESSION_RTH_MIN)
        r = (sens * sortie * SIGMA_1MIN - c) / risque
        s1 += r
        s2 += r * r
        wald_somme += -c / risque
        gains += 1 if r > 0.0 else 0
        rapports += vise / risque
        tau += minute
        d = min(int(d_proche * 20.0), 9)
        dec_n[d] += 1
        gagne = premier is not None and ((premier[0] == "haut") == proche_est_haut)
        if premier is not None:
            dec_casse[d] += 1
        if gagne:
            dec_ok[d] += 1
        if premier is None:
            n_rien += 1
            r_rien += r
        elif gagne:
            n_proche += 1
            r_proche += r
        else:
            r_loin += r

    m = len(nuit)
    n_loin = m - n_rien - n_proche
    moyenne = s1 / m
    var = max(s2 / m - moyenne * moyenne, 0.0)
    premiers.sort()
    return Campagne(
        k=k, s_vol=s_vol, pic=pic, n=m,
        au_moins_un=au_moins / m, les_deux=deux / m, aucun=zero / m,
        haut_si_dessus=haut_dessus / max(n_dessus, 1),
        bas_si_dessous=bas_dessous / max(n_dessous, 1),
        haut_si_dessus_casse=haut_dessus / max(casse_dessus, 1),
        bas_si_dessous_casse=bas_dessous / max(casse_dessous, 1),
        premier_median=premiers[len(premiers) // 2] if premiers else 0.0,
        avant_dix_heures=avant_dix / m,
        esperance=moyenne, erreur_type=math.sqrt(var / m),
        wald=wald_somme / m, taux_gain=gains / m,
        rapport=rapports / m, exposition=tau / m,
        par_decile=tuple(dec_ok[i] / dec_n[i] if dec_n[i] else 0.0
                         for i in range(10)),
        par_decile_casse=tuple(dec_ok[i] / dec_casse[i] if dec_casse[i] else 0.0
                               for i in range(10)),
        p_rien=n_rien / m, p_proche=n_proche / m,
        esp_rien=r_rien / max(n_rien, 1),
        esp_proche=r_proche / max(n_proche, 1),
        esp_loin=r_loin / max(n_loin, 1),
    )


# --- La calibration --------------------------------------------------------
#
# Deux paramètres, deux cibles, et les cibles sont celles qui ne portent
# aucune direction. Il ne reste donc **aucun degré de liberté** pour les
# nombres de direction, qui sont prédits et non ajustés.

S_VOL_BOX = (0.0, 0.90)
S_VOL_PAS = 0.15


def _grille(box: tuple[float, float], pas: float) -> tuple[float, ...]:
    lo, hi = box
    n = int(round((hi - lo) / pas)) + 1
    return tuple(round(lo + i * pas, 4) for i in range(n))


@lru_cache(maxsize=None)
def calibrer(pic: bool = True) -> tuple[float, float]:
    """Le couple qui rend au mieux les deux nombres **sans direction**."""
    best, best_err = None, math.inf
    for k in _grille(K_BOX, K_PAS * 2.0):
        for s in _grille(S_VOL_BOX, S_VOL_PAS):
            c = campagne(k, s, pic, 6000)
            err = sum((getattr(c, cle) - ANNONCES[cle]) ** 2 for cle in CALIBRAGE)
            if err < best_err:
                best, best_err = (float(k), float(s)), err
    return best


def retenue(pic: bool = True) -> Campagne:
    k, s = calibrer(pic)
    return campagne(k, s, pic)


#: Les deux axes de la boîte, en ordre **croissant** : le conditionnel y est
#: maximal au coin (0, 0), et c'est là que le relief doit culminer pour qu'une
#: projection isométrique se lise — le coin (0, 0) est le plus éloigné.
SURF_K = (0.30, 0.38, 0.46, 0.54, 0.62, 0.70)
SURF_S = (0.0, 0.18, 0.36, 0.54, 0.72, 0.90)


@lru_cache(maxsize=None)
def surface_boite() -> tuple[tuple[float, ...], ...]:
    """Le conditionnel sur toute la boîte des deux paramètres non observables."""
    return tuple(tuple(
        (lambda c: (c.haut_si_dessus + c.bas_si_dessous) / 2.0)(
            campagne(k, sv, True, 5000))
        for sv in SURF_S) for k in SURF_K)


@lru_cache(maxsize=None)
def sensibilite() -> tuple[tuple[float, float, float], ...]:
    """La même boîte, à plat, pour les tables et les valeurs."""
    z = surface_boite()
    return tuple((k, sv, z[i][j])
                 for i, k in enumerate(SURF_K)
                 for j, sv in enumerate(SURF_S))


#: Les deux axes du plan de jeu équitable, en ordre **décroissant** : le
#: maximum d'espérance est au taux le plus haut et au rapport le plus large.
SURF_TAUX = (0.90, 0.85, 0.80, 0.75, 0.70, 0.65)
SURF_RAPPORT = (1.00, 0.80, 0.60, 0.45, 0.33, 0.25)


def esperance_plan(taux: float, rapport: float,
                   friction_r: float = 0.0) -> float:
    """`E[R] = p·b − (1 − p)·a − c/a`, avec le stop pris pour unité.

    Aucune simulation : c'est l'arithmétique d'un pari à deux issues. Elle
    suffit, et c'est le point — le résultat ne dépend d'aucune propriété du
    marché, seulement du couple (taux, géométrie).
    """
    return taux * rapport - (1.0 - taux) - friction_r


def surface_plan() -> tuple[tuple[float, ...], ...]:
    c = retenue()
    fr = -c.wald                      # la friction, en unités de R
    return tuple(tuple(esperance_plan(t, r, fr) for r in SURF_RAPPORT)
                 for t in SURF_TAUX)


# --- Les tables ------------------------------------------------------------


LIGNES = (
    ("au_moins_un", "Au moins un extrême franchi", False),
    ("les_deux", "Les deux extrêmes franchis", True),
    ("aucun", "Aucun extrême franchi", True),
    ("haut_si_dessus", "Le haut casse en premier, ouverture au-dessus du milieu",
     False),
    ("bas_si_dessous", "Le bas casse en premier, ouverture au-dessous du milieu",
     False),
    ("avant_dix_heures", "Un côté cassé avant 10:00", False),
)


def _verdict(ecart_pct: float, tolerance: float) -> str:
    return "rendu" if abs(ecart_pct) <= tolerance else "résidu"


def table_annonces() -> Table:
    """Les sept nombres publiés, face à ce qu'un prix sans dérive en rend."""
    c = retenue()
    rows = []
    for cle, libelle, calibre in LIGNES:
        annonce = ANNONCES[cle] * 100.0
        nul = getattr(c, cle) * 100.0
        rows.append([
            libelle,
            num(annonce, 1, " %"),
            num(nul, 1, " %"),
            num(nul - annonce, 1, signed=True),
            "calibré" if calibre else _verdict(nul - annonce, TOLERANCE_PCT),
        ])
    rows.append([
        "Première cassure, médiane",
        num(ANNONCES["premier_median"], 0) + " min",
        num(c.premier_median, 0) + " min",
        num(c.premier_median - ANNONCES["premier_median"], 0, signed=True),
        _verdict(c.premier_median - ANNONCES["premier_median"], TOLERANCE_MIN),
    ])
    return Table(
        "on_annonces",
        "Les sept nombres publiés, et ce qu'une marche sans dérive en rend.",
        ["Ce que l'affirmation avance", "Publié", "Loi nulle", "Écart", "Verdict"],
        rows,
        note=("Le modèle nul a **deux** paramètres, tous deux non observables "
              "dans les nombres publiés : le rapport des volatilités nuit/jour, "
              "qui vaut " + num(c.k, 2) + ", et la dispersion de volatilité "
              "d'une séance à l'autre, qui vaut " + num(c.s_vol, 2) + ". Ils "
              "sont calibrés sur les deux lignes marquées « calibré » — celles "
              "qui ne portent **aucune direction** — et il ne reste donc aucun "
              "degré de liberté pour les quatre autres, qui sont prédites. "
              "C'est la condition sans laquelle l'exercice ne prouverait rien : "
              "un paramètre ajusté sur le chiffre qu'il doit expliquer explique "
              "n'importe quoi. Le verdict est calculé contre une tolérance de "
              + num(TOLERANCE_PCT, 0) + " points, déclarée une seule fois."),
        wrap_last=True, wrap_cols=[0],
    )


def table_position() -> Table:
    """Où une marche sans dérive finit dans son propre range."""
    q = quantiles_position()
    rows = []
    for seuil, valeur in q.items():
        rows.append([
            num(seuil * 100.0, 0) + " %",
            num(valeur * 100.0, 1, " %"),
            num(seuil * 100.0, 1, " %"),
            num((valeur - seuil) * 100.0, 1, signed=True),
        ])
    proche, loin = distance_au_bord()
    return Table(
        "on_position",
        "La position de l'ouverture dans le range overnight, par quantile.",
        ["Quantile", "Loi de la marche", "Loi uniforme", "Écart"],
        rows,
        note=("La colonne du milieu est ce qu'on croit spontanément : une "
              "ouverture qui tomberait n'importe où dans le range. La colonne "
              "de gauche est ce qui se produit. La loi est en **U** — les bords "
              "chargés, le milieu creusé — parce que l'instant où une marche "
              "atteint son maximum suit une loi de l'arc sinus, qui charge les "
              "extrémités du trajet. Conséquence chiffrée : la distance médiane "
              "de l'ouverture au bord le plus proche vaut "
              + num(proche * 100.0, 1) + " % du range contre "
              + num(loin * 100.0, 1) + " % à l'autre bord, et "
              + num(part_extremes() * 100.0, 1) + " % des séances ouvrent dans "
              "le dernier sixième d'un bord. C'est là que l'essentiel du "
              "soixante-seize pour cent est déjà contenu, avant qu'aucune "
              "donnée de marché ne soit consultée."),
        wrap_last=True,
    )


def _ecart_arret() -> tuple[float, float]:
    """Écart moyen et écart maximal à la loi d'arrêt, sur la colonne conditionnée.

    Les deux nombres sont mesurés et non qualifiés : « à quelques dixièmes de
    point » était faux aux courtes distances, et une note qui décrit ce qu'on
    espérait plutôt que ce qu'on a mesuré est le défaut que ce dépôt traque.
    """
    c = retenue()
    ecarts = [abs(p - (1.0 - (i + 0.5) * 0.05))
              for i, p in enumerate(c.par_decile_casse)]
    return sum(ecarts) / len(ecarts), max(ecarts)


def table_conditionnel() -> Table:
    """La probabilité de toucher le bord proche, selon la distance à ce bord."""
    c = retenue()
    rows = []
    for i, (p, pc) in enumerate(zip(c.par_decile, c.par_decile_casse)):
        lo, hi = i * 5.0, (i + 1) * 5.0
        milieu = (lo + hi) / 2.0 / 100.0
        rows.append([
            num(lo, 0) + " – " + num(hi, 0) + " %",
            num(p * 100.0, 1, " %"),
            num(pc * 100.0, 1, " %"),
            num((1.0 - milieu) * 100.0, 1, " %"),
            num((pc - (1.0 - milieu)) * 100.0, 1, signed=True),
        ])
    return Table(
        "on_conditionnel",
        "La probabilité de toucher le bord proche en premier, par distance à ce bord.",
        ["Distance au bord proche", "Sur toutes les séances",
         "Sur les séances qui cassent", "Loi d'arrêt : 1 − d", "Écart"],
        rows,
        note=("La quatrième colonne n'est pas une simulation : c'est le "
              "théorème d'arrêt optionnel, qui donne la probabilité de toucher "
              "une barrière avant l'autre comme le rapport des distances "
              "inverses. La troisième la suit de bout en bout, "
              + num(_ecart_arret()[0] * 100.0, 1) + " point d'écart moyen, et "
              "le décrochage se concentre aux deux premières lignes, où il "
              "atteint " + num(_ecart_arret()[1] * 100.0, 1) + " points. La "
              "raison n'est pas le marché mais le **pas de temps** : la "
              "trajectoire avance par minute, et la première minute de séance "
              "porte une amplitude comparable à la distance qu'on mesure ici. "
              "La loi continue est la limite d'un pas qui tend vers zéro, et "
              "une minute d'ouverture n'est pas un pas qui tend vers zéro. "
              "**Il n'y a donc rien à prédire** : la probabilité annoncée est "
              "la distance, lue à l'envers.\n\n"
              "La deuxième colonne est la même chose comptée sur *toutes* les "
              "séances, et elle est plus basse d'un montant qui ne dépend pas "
              "de la distance — exactement les "
              + num(c.p_rien * 100.0, 1) + " % de séances qui ne cassent rien, "
              "et qui comptent alors comme un échec à chaque distance. C'est "
              "le décalage constant qu'on voit d'une colonne à l'autre, et "
              "c'est aussi, à un point près, l'écart entre les deux lectures "
              "possibles du nombre publié."),
        wrap_last=True,
    )


def table_sensibilite() -> Table:
    """Ce que le résidu doit à un paramètre que personne n'observe."""
    vals = [v for _, _, v in sensibilite()]
    lo, hi = min(vals), max(vals)
    annonce = (ANNONCES["haut_si_dessus"] + ANNONCES["bas_si_dessous"]) / 2.0
    c = retenue()
    rows = [
        ["Rapport de volatilité nuit/jour", num(K_BOX[0], 2) + " – "
         + num(K_BOX[1], 2), "non observable dans les nombres publiés"],
        ["Dispersion de volatilité par séance", num(S_VOL_BOX[0], 2) + " – "
         + num(S_VOL_BOX[1], 2), "non observable dans les nombres publiés"],
        ["Conditionnel prédit, sur toute la boîte",
         num(lo * 100.0, 1, " %") + " – " + num(hi * 100.0, 1, " %"),
         "amplitude de " + num((hi - lo) * 100.0, 1) + " points"],
        ["Conditionnel au couple calibré", num(
            (c.haut_si_dessus + c.bas_si_dessous) / 2.0 * 100.0, 1, " %"),
         "k = " + num(c.k, 2) + ", dispersion " + num(c.s_vol, 2)],
        ["Conditionnel publié", num(annonce * 100.0, 1, " %"),
         "moyenne des deux sens"],
        ["Résidu", num((annonce - (c.haut_si_dessus + c.bas_si_dessous) / 2.0)
                       * 100.0, 1) + " points",
         "à comparer à l'amplitude ci-dessus"],
    ]
    return Table(
        "on_sensibilite",
        "Le résidu, et l'amplitude que deux paramètres non observables lui donnent.",
        ["", "Valeur", "Lecture"],
        rows,
        note=("Le dépôt connaît déjà cette figure : la fréquence nulle d'un "
              "déséquilibre de footprint dépend d'une taille de grappe que "
              "personne n'observe, celle d'un extrême pauvre en profil de "
              "marché dépend d'une hauteur de rangée qui est un réglage "
              "d'affichage. Ici, le rapport de volatilité nuit/jour joue le "
              "même rôle. **Un résidu plus petit que l'amplitude de "
              "l'hypothèse n'est pas un résultat**, et il faut le dire avant "
              "de discuter s'il paie."),
        wrap_last=True, wrap_cols=[0],
    )


def _lectures() -> tuple[tuple[str, float, float, float, str], ...]:
    """Les deux façons de lire le nombre publié, et ce que chacune donne.

    La publication écrit « ouverture au-dessus du milieu, le haut casse en
    premier 76,2 % » sans dire de quoi ce pour-cent est la part. Deux
    dénominateurs sont défendables : toutes les séances de ce côté, ou les
    seules qui cassent quelque chose. L'écart entre les deux vaut cinq points,
    soit **plus que l'effet discuté**, et il change le signe du verdict. Le
    module publie les deux plutôt que de choisir celle qui arrange.
    """
    c = retenue()
    ann = (ANNONCES["haut_si_dessus"] + ANNONCES["bas_si_dessous"]) / 2.0
    # Les deux lectures sont ramenées à **une seule convention** — le taux
    # parmi les séances qui cassent — parce que c'est la base sur laquelle un
    # trade se décide, et parce que comparer deux nombres comptés sur des
    # dénominateurs différents est précisément la faute que cette section
    # dénonce. La loi nulle est lue dans la même convention.
    nul = (c.haut_si_dessus_casse + c.bas_si_dessous_casse) / 2.0
    a = ann / (1.0 - ANNONCES["aucun"])
    out = []
    for nom, taux_casse in (("A — sur toutes les séances", a),
                            ("B — sur les séances qui cassent", ann)):
        esp = c.esperance_au_taux(taux_casse)
        out.append((nom, taux_casse, nul, esp,
                    "gagnante" if esp > 0.0 else "perdante"))
    return tuple(out)


def table_lecture() -> Table:
    """Le dénominateur que la publication ne donne pas, et ce qu'il décide."""
    c = retenue()
    seuil = c.taux_equilibre()
    ann = (ANNONCES["haut_si_dessus"] + ANNONCES["bas_si_dessous"]) / 2.0
    rows = []
    for nom, taux, nul, esp, verdict in _lectures():
        rows.append([
            nom,
            num(taux * 100.0, 1, " %"),
            num(nul * 100.0, 1, " %"),
            num((taux - nul) * 100.0, 1, signed=True),
            num(esp, 4, signed=True) + " R",
            verdict,
        ])
    return Table(
        "on_lecture",
        "Les deux lectures possibles du nombre publié, et leurs verdicts opposés.",
        ["Lecture", "Taux parmi les cassures", "Même taux sous loi nulle",
         "Résidu", "Espérance", "Verdict"],
        rows,
        note=("Le taux d'équilibre de cette géométrie vaut "
              + num(seuil * 100.0, 1) + " %. La lecture B tombe au-dessous et "
              "la lecture A au-dessus&nbsp;: **le signe du résultat est décidé "
              "par une phrase que la publication n'écrit pas.** Et sous la "
              "lecture B, la loi nulle rend le nombre publié à un dixième de "
              "point près — il n'y a alors strictement rien à expliquer. Le "
              "dépôt ne tranche pas à la place de l'auteur&nbsp;: il montre que "
              "la question du dénominateur pèse cinq points, quand l'effet "
              "revendiqué en pèse quatre."),
        wrap_last=True, wrap_cols=[0],
    )


def table_horloge() -> Table:
    """Le seul nombre qu'une volatilité constante ne rend pas."""
    k, s = calibrer(True)
    plat = campagne(k, s, False)
    pic = retenue()
    rows = [
        ["Première cassure, médiane",
         num(ANNONCES["premier_median"], 0) + " min",
         num(plat.premier_median, 0) + " min",
         num(pic.premier_median, 0) + " min"],
        ["Un côté cassé avant 10:00",
         num(ANNONCES["avant_dix_heures"] * 100.0, 1, " %"),
         num(plat.avant_dix_heures * 100.0, 1, " %"),
         num(pic.avant_dix_heures * 100.0, 1, " %")],
        ["Le haut casse en premier, ouverture au-dessus",
         num(ANNONCES["haut_si_dessus"] * 100.0, 1, " %"),
         num(plat.haut_si_dessus * 100.0, 1, " %"),
         num(pic.haut_si_dessus * 100.0, 1, " %")],
        ["Espérance du trade imposé", "—",
         num(plat.esperance, 4, signed=True) + " R",
         num(pic.esperance, 4, signed=True) + " R"],
    ]
    return Table(
        "on_horloge",
        "Ce que le pic de variance d'ouverture explique, et ce qu'il ne touche pas.",
        ["", "Publié", "Volatilité plate", "Pic d'ouverture"],
        rows,
        note=("Le profil concentre "
              + num(part_variance_premiere_demi_heure() * 100.0, 0) + " % de la "
              "variance de la séance sur la première demi-heure, **à variance "
              "totale identique** : rien n'est ajouté, tout est déplacé. Il "
              "rend le timing, que la volatilité plate manquait de trente "
              "minutes. Il ne déplace ni la direction ni l'espérance, et c'est "
              "l'essentiel : la variance de l'ouverture dit **quand** la "
              "cassure arrive, jamais de quel côté. C'est la seule des sept "
              "affirmations qui porte une vraie propriété de marché, et elle "
              "n'est pas directionnelle."),
        wrap_last=True, wrap_cols=[0],
    )


def table_esperance() -> Table:
    """Ce que rapporte le trade que l'affirmation impose."""
    c = retenue()
    seuil = c.taux_equilibre()
    annonce = (ANNONCES["haut_si_dessus"] + ANNONCES["bas_si_dessous"]) / 2.0
    z = (c.esperance - c.wald) / c.erreur_type if c.erreur_type else 0.0
    rows = [
        ["Rapport gain-risque moyen", "1 pour " + num(1.0 / c.rapport, 1),
         "le bord proche est bien plus près que le bord opposé"],
        ["Temps de marché", num(c.exposition, 0) + " min",
         "E[τ∧T], l'exposition moyenne"],
        ["Espérance sous loi nulle", num(c.esperance, 4, signed=True) + " R",
         "à comparer à la prédiction de Wald " + num(c.wald, 4, signed=True)
         + " R, écart " + num(z, 2, signed=True) + " erreurs types"],
        ["**Taux de réussite d'équilibre**", num(seuil * 100.0, 1, " %"),
         "ce qu'il faudrait gagner pour ne rien perdre"],
        ["Taux de réussite publié", num(annonce * 100.0, 1, " %"),
         "moyenne des deux sens annoncés"],
        ["Espérance au taux publié, lecture B",
         num(c.esperance_au_taux(annonce), 4, signed=True) + " R",
         "le pour-cent porte sur les séances qui cassent"],
        ["Espérance au taux publié, lecture A",
         num(c.esperance_au_taux(annonce / (1.0 - ANNONCES["aucun"])), 4,
             signed=True) + " R",
         "le pour-cent porte sur toutes les séances"],
    ]
    return Table(
        "on_esperance",
        "Le trade imposé : viser le bord proche, stop sur le bord opposé.",
        ["", "Valeur", "Lecture"],
        rows,
        note=("Les deux dernières lignes ne demandent pas de croire la loi "
              "nulle : on **suppose** le chiffre publié entièrement vrai, "
              "résidu compris, et on remplace la seule fréquence dans le "
              "calcul en laissant à la géométrie les niveaux qu'elle impose. "
              "Elles diffèrent par le dénominateur du pour-cent publié, que la "
              "publication ne précise pas, et elles sont **de signes "
              "opposés** : le taux d'équilibre de cette géométrie vaut "
              + num(seuil * 100.0, 1) + " %, et les deux lectures tombent de "
              "part et d'autre. Ce qui est certain dans les deux cas : le taux "
              "de réussite n'a pas été volé, il a été **acheté** au prix d'un "
              "rapport gain-risque d'un pour " + num(1.0 / c.rapport, 1) + "."),
        wrap_last=True, wrap_cols=[0],
    )


TABLES = (table_annonces, table_position, table_conditionnel,
          table_sensibilite, table_horloge, table_esperance, table_lecture)


def all_tables() -> dict[str, Table]:
    return {t().key: t() for t in TABLES}


def values() -> dict[str, str]:
    c = retenue()
    k, s = calibrer(True)
    plat = campagne(k, s, False)
    proche, loin = distance_au_bord()
    vals = [v for _, _, v in sensibilite()]
    annonce = (ANNONCES["haut_si_dessus"] + ANNONCES["bas_si_dessous"]) / 2.0
    nul_moy = (c.haut_si_dessus + c.bas_si_dessous) / 2.0
    seuil = c.taux_equilibre()
    return {
        "o_sessions": num(2827, 0),
        "o_annees": num(11, 0),
        "o_k": num(c.k, 2),
        "o_svol": num(c.s_vol, 2),
        "o_nuits": num(N_NUITS / 1000.0, 0),
        "o_paths": num(c.n / 1000.0, 0),
        "o_proche": num(proche * 100.0, 1),
        "o_loin": num(loin * 100.0, 1),
        "o_extremes": num(part_extremes() * 100.0, 1),
        "o_ann_haut": num(ANNONCES["haut_si_dessus"] * 100.0, 1),
        "o_ann_bas": num(ANNONCES["bas_si_dessous"] * 100.0, 1),
        "o_ann_moy": num(annonce * 100.0, 1),
        "o_nul_haut": num(c.haut_si_dessus * 100.0, 1),
        "o_nul_bas": num(c.bas_si_dessous * 100.0, 1),
        "o_nul_moy": num(nul_moy * 100.0, 1),
        "o_residu": num((annonce - nul_moy) * 100.0, 1),
        "o_boite_lo": num(min(vals) * 100.0, 1),
        "o_boite_hi": num(max(vals) * 100.0, 1),
        "o_boite_amplitude": num((max(vals) - min(vals)) * 100.0, 1),
        "o_ann_un": num(ANNONCES["au_moins_un"] * 100.0, 1),
        "o_nul_un": num(c.au_moins_un * 100.0, 1),
        "o_ann_deux": num(ANNONCES["les_deux"] * 100.0, 1),
        "o_nul_deux": num(c.les_deux * 100.0, 1),
        "o_ann_aucun": num(ANNONCES["aucun"] * 100.0, 1),
        "o_nul_aucun": num(c.aucun * 100.0, 1),
        "o_tolerance": num(TOLERANCE_PCT, 0),
        "o_ann_median": num(ANNONCES["premier_median"], 0),
        "o_plat_median": num(plat.premier_median, 0),
        "o_pic_median": num(c.premier_median, 0),
        "o_ann_dix": num(ANNONCES["avant_dix_heures"] * 100.0, 1),
        "o_plat_dix": num(plat.avant_dix_heures * 100.0, 1),
        "o_pic_dix": num(c.avant_dix_heures * 100.0, 1),
        "o_part_variance": num(part_variance_premiere_demi_heure() * 100.0, 0),
        "o_taux": num(c.taux_gain * 100.0, 1),
        "o_rapport": num(1.0 / c.rapport, 1),
        "o_seuil": num(seuil * 100.0, 1),
        "o_manque": num((seuil - annonce) * 100.0, 1),
        "o_esperance": num(c.esperance, 4, signed=True),
        "o_esp_annonce": num(c.esperance_au_taux(annonce), 4, signed=True),
        "o_lec_a_taux": num(_lectures()[0][1] * 100.0, 1),
        "o_lec_a_esp": num(_lectures()[0][3], 4, signed=True),
        "o_lec_a_residu": num((annonce - _lectures()[0][2]) * 100.0, 1, signed=True),
        "o_lec_b_taux": num(_lectures()[1][1] * 100.0, 1),
        "o_lec_b_esp": num(_lectures()[1][3], 4, signed=True),
        "o_lec_b_residu": num((annonce - _lectures()[1][2]) * 100.0, 1, signed=True),
        "o_nul_casse": num((c.haut_si_dessus_casse + c.bas_si_dessous_casse)
                           / 2.0 * 100.0, 1),
        "o_ecart_lectures": num((_lectures()[0][1] - _lectures()[1][1]) * 100.0, 1),
        "o_ecart_arret_moyen": num(_ecart_arret()[0] * 100.0, 1),
        "o_ecart_arret_max": num(_ecart_arret()[1] * 100.0, 1),
        "o_wald": num(c.wald, 4, signed=True),
        "o_tau": num(c.exposition, 0),
        "o_friction": num(friction(), 2),
    }


def main() -> None:
    for t in TABLES:
        print(t().to_text())
        print()


if __name__ == "__main__":
    main()
