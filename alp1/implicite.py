"""La volatilité implicite, et les deux nombres qu'on en tire à tort.

Dixième document de la série d'options, et le second — après le guide du
vanna — à **publier le résultat de son propre test négatif** : une relation
monotone entre l'IV rank et les résultats à venir, dit-il, *disparaît
entièrement* dès que la fenêtre de classement est rendue strictement
glissante. Le motif était un artefact du classement, pas une propriété du
marché. Le dépôt reprend ce test, en publie la loi nulle, et découvre que
l'artefact est plus grand que le guide ne l'écrit.

Sa phrase d'ouverture est la meilleure définition de l'objet qu'on puisse
donner : *l'implicite n'est pas une prévision, pas une mesure, pas une
propriété du sous-jacent ; c'est le nombre qu'il faut mettre dans
Black-Scholes pour retrouver un prix qu'on a déjà observé.* Le dépôt
souscrit et va là où le guide s'arrête : si c'est un changement d'unités,
alors **la précision de la traduction se calcule**, et elle n'est pas la
même partout.

I. L'inversion existe, et sa précision s'effondre avant elle
--------------------------------------------------------------
Le guide écrit que le véga est strictement positif, donc que la solution est
unique quand elle existe. C'est vrai. Ce qui manque est le pas suivant : le
véga s'annule **exponentiellement** dans les ailes et en racine du temps
près de l'échéance, et la traduction d'un tick en points de volatilité vaut
`100·tick/𝒱`. Elle diverge donc là où le guide place sa remarque sur les
marchés larges. Le nombre se calcule : un seul tick vaut 0,44 point de
volatilité à la monnaie et à trente jours, et **3,5 points** à cinq deltas
et une semaine. Le lieu où un tick vaut un point entier est une courbe, et
le dépôt la publie.

II. Un IV rank sur un an porte l'information de deux observations
-------------------------------------------------------------------
C'est le résultat structurant de la partie, et il vient d'un fait que le
guide ne mentionne pas : la volatilité est **persistante**. Sous un retour à
la moyenne de vitesse `κ`, l'échantillon effectif d'une fenêtre de durée `T`
vaut `κT/2` observations et non `n` — deux, pour un an et une vitesse de
quatre par an. *La longueur de la fenêtre n'achète presque rien ; c'est la
vitesse de retour à la moyenne qui décide, et elle n'est pas observable.*
La conséquence se chiffre : distinguer un percentile de 80 d'un percentile
de 50 demande huit ans et neuf mois de données, et le guide recommande
d'annoncer la fenêtre — ce qui est juste, et insuffisant.

III. Le rang est hostage d'un point, le percentile d'un sur n
----------------------------------------------------------------
« Un jour de crise peut tenir le rang artificiellement bas pendant un an. »
Exact, et le rapport des deux sensibilités **est** la taille de la fenêtre :
un pic déplace le rang de tout ce qu'il ajoute au dénominateur et le
percentile d'exactement `1/n`. C'est le défaut du Calmar de la partie XVIII
— un dénominateur qui est un maximum, et il n'y a qu'un seul maximum dans
une série — rencontré ici sur un troisième objet.

IV. Le look-ahead se reproduit sous loi nulle, et le premier jet s'y trompe
-----------------------------------------------------------------------------
Le guide dit que la relation disparaît. Le dépôt dit pourquoi elle
apparaissait : classer aujourd'hui contre une fenêtre qui contient l'avenir,
c'est demander à la statistique de regarder ce qu'on lui demande de prédire.

Écrire cette loi nulle proprement a coûté un aller-retour, et il est
instructif. Le premier jet posait le gain du vendeur comme *le niveau de
volatilité du jour moins la réalisée qui suit* : la colonne glissante rendait
alors **0,284** de corrélation là où la loi nulle en exigeait zéro, et le test
ne prouvait rien. Ce n'était pas un bug — sous un retour à la moyenne, le
niveau du jour prédit *vraiment* la variation qui suit, et un vendeur qui
vend haut gagne pour cette seule raison. L'erreur était de confondre le
niveau de volatilité avec **un prix**, ce qui est précisément la confusion
que le guide passe sa première page à dissoudre. L'implicite honnête est
l'espérance conditionnelle de la réalisée à venir, elle a une forme fermée
sous le processus déclaré, et le gain qu'elle définit est d'espérance
conditionnelle nulle **par construction**. Alors seulement la colonne
glissante rend zéro, et la colonne fuitée ne le rend pas.

V. Un prix coté dans les mauvaises unités paie une prime qui n'existe pas
----------------------------------------------------------------------------
Le sous-titre du guide est *« un prix coté dans les mauvaises unités, exprès »*
et il ne va pas jusqu'au bout de sa propre remarque. Un vendeur dont
l'implicite égale exactement la volatilité vraie a une espérance nulle **en
variance** et une espérance **positive en volatilité**, parce que la racine
est concave : le biais vaut 0,23 point à un mois, soit un neuvième du bas
de la fourchette que le guide annonce, et sa forme fermée `σ/(4h)` referme
la mesure à deux pour cent. *Une partie de la prime de risque de volatilité
publiée est une propriété de l'unité de cotation, pas du marché.* Le second
jet de cette section l'a découvert en écrivant « perd en espérance » et en
mesurant l'inverse.

VI. Les cinq pièges, et deux d'entre eux sont le même nombre
--------------------------------------------------------------
Un forward faux et un prix périmé déplacent tous deux l'implicite de
`Δ·ΔS/𝒱` : la même forme fermée, contrôlée contre une réinversion complète.
Le classement des cinq par leur coût n'est pas celui de la liste du guide.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from functools import lru_cache

from . import grandeurs as G
from . import ordres as O
from . import theta as th
from . import vega as vg
from . import volga as vo
from .costs import norm_cdf
from .report import Table, num

SEED = 20260905

S_REF = vo.S_REF
VOL_REF = vo.VOL_REF
TAUX = vo.TAUX
DIVIDENDE = vo.DIVIDENDE
JOURS_AN = vo.JOURS_AN

#: Le pas de cotation d'une option, en points d'indice. Sur un comptant à
#: cent, cinq centièmes valent cinq points de base du notionnel : c'est
#: l'ordre de grandeur d'un marché d'options d'indice liquide. Le nombre
#: n'est pas critique — toute la partie II est **proportionnelle** à lui —
#: mais il doit être écrit, parce qu'un tick qu'on ne déclare pas est un
#: tick qu'on choisit après avoir vu le résultat.
TICK = 0.05

#: Le nombre de séances d'une année de cotation. Le même que celui des
#: parties précédentes, et il sert ici de fenêtre de référence parce que
#: c'est celle que les outils grand public emploient.
SEANCES_AN = 252

#: La vitesse de retour à la moyenne de la volatilité, en par an. **Elle
#: n'est pas observable dans ce dépôt** et c'est le seul paramètre libre de
#: la partie : elle est donc balayée partout où elle décide d'un nombre, et
#: la valeur de référence n'est là que pour donner un exemple. La
#: littérature la place entre deux et huit ; quatre est le milieu
#: géométrique, et un temps de relaxation de trois mois.
KAPPA = 4.0
KAPPA_GRILLE: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0, 16.0)

#: La dispersion instantanée du logarithme de la volatilité, en par racine
#: d'année. Elle fixe l'amplitude de la série simulée et rien d'autre : tous
#: les résultats de rang et de percentile sont **invariants** par changement
#: d'échelle du logarithme, et un test l'exige.
ETA = 0.9

#: Le niveau moyen de la volatilité simulée.
VOL_MOYENNE = 0.20

Z_95 = 1.959963984540054


def _phi(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def call(s: float, k: float, vol: float, t: float) -> float:
    return th.call(s, max(k, 1e-12), max(vol, 1e-12), max(t, 1e-12),
                   TAUX, DIVIDENDE)


def vega(s: float, k: float, vol: float, t: float) -> float:
    """`𝒱 = Se^{−qT}φ(d₁)√T`, par unité de volatilité."""
    return vg.vega(s, k, vol, t, TAUX, DIVIDENDE)


# ---------------------------------------------------------------------------
# I. L'inversion, et les bornes hors desquelles elle n'existe pas
# ---------------------------------------------------------------------------


def bornes_d_arbitrage(s: float, k: float, t: float) -> tuple[float, float]:
    """Le plancher et le plafond entre lesquels un prix de call admet une IV.

    Sous le plancher `max(Se^{−qT} − Ke^{−rT}, 0)` et au-dessus du plafond
    `Se^{−qT}`, aucune volatilité positive ne rend le prix : le guide écrit
    « unique quand elle existe » et ne dit pas où elle cesse d'exister. Les
    deux bornes sont les limites de la fonction quand `σ → 0` et `σ → ∞`,
    et la monotonie fait le reste.
    """
    bas = max(s * math.exp(-DIVIDENDE * t) - k * math.exp(-TAUX * t), 0.0)
    return bas, s * math.exp(-DIVIDENDE * t)


def existe(prix: float, s: float, k: float, t: float) -> bool:
    bas, haut = bornes_d_arbitrage(s, k, t)
    return bas < prix < haut


def implicite(prix: float, s: float, k: float, t: float,
              tol: float = 1e-12, n_max: int = 200) -> float:
    """La volatilité implicite, par bissection sur `[10⁻⁸, 10]`.

    Le guide dit qu'il n'existe pas de forme fermée et que la fonction est
    monotone : les deux sont vrais, et la seconde suffit à la bissection.
    Renvoie `nan` hors des bornes d'arbitrage, ce qui est la seule réponse
    honnête et que les outils rendent rarement.
    """
    if not existe(prix, s, k, t):
        return float("nan")
    lo, hi = 1e-8, 10.0
    for _ in range(n_max):
        mid = 0.5 * (lo + hi)
        if call(s, k, mid, t) < prix:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


def implicite_newton(prix: float, s: float, k: float, t: float,
                     depart: float = 0.30, n_max: int = 60) -> float:
    """La même chose par Newton sur le véga — **la route de contrôle**.

    Deux routes indépendantes vers le même nombre, et leur accord est ce qui
    rend l'inversion publiable. Newton s'appuie sur le véga, donc il échoue
    là où celui-ci s'annule ; la bissection n'échoue jamais. *La comparaison
    des deux est déjà la mesure de la section suivante.*
    """
    if not existe(prix, s, k, t):
        return float("nan")
    x = depart
    for _ in range(n_max):
        v = vega(s, k, x, t)
        if v < 1e-14:
            return float("nan")
        pas = (call(s, k, x, t) - prix) / v
        x -= pas
        if x <= 1e-9:
            x = 1e-9
        if abs(pas) < 1e-13:
            break
    return x


def ecart_a_la_droite(k: float, t: float, s: float = S_REF,
                      vol_max: float = 0.90, n: int = 200) -> float:
    """Ce que la fonction inverse s'écarte de sa corde, en part de sa hauteur.

    À la monnaie, le véga ne dépend presque pas de la volatilité — `φ(d₁)`
    y vaut la constante de la densité normale à un centième près — donc la
    fonction inverse est **presque affine** sur toute la plage négociée.
    C'est ce qui fait qu'un opérateur peut raisonner en volatilité comme il
    raisonnerait en prix, et c'est un fait mesurable plutôt qu'une
    impression : la mesure vaut quelques pour cent à la monnaie et un ordre
    de grandeur de plus dans l'aile.

    Le même geste que `volga.ecart_a_la_corde` de la partie XXVI, sur la
    fonction réciproque.
    """
    bas = bornes_d_arbitrage(s, k, t)[0]
    haut = call(s, k, vol_max, t)
    if haut <= bas:
        return 0.0
    pires = 0.0
    for i in range(1, n):
        prix = bas + (haut - bas) * i / n
        v = implicite(prix, s, k, t)
        if v != v:
            continue
        corde = vol_max * (prix - bas) / (haut - bas)
        pires = max(pires, abs(v - corde))
    return pires / vol_max


#: Les couples (jours, moneyness) de la table d'inversion.
INVERSIONS: tuple[tuple[float, float], ...] = (
    (30.0, 1.00), (30.0, 1.10), (30.0, 1.25),
    (7.0, 1.00), (7.0, 1.10), (7.0, 1.25),
)


# ---------------------------------------------------------------------------
# II. Le tick, et ce qu'il vaut en points de volatilité
# ---------------------------------------------------------------------------


def points_de_vol_par_tick(s: float, k: float, vol: float, t: float,
                           tick: float = TICK) -> float:
    """`100·tick/𝒱` — ce qu'un pas de cotation vaut en points de volatilité.

    C'est la précision de la traduction dont le guide fait sa définition. Le
    véga est au dénominateur, donc la quantité **diverge** dans l'aile et
    près de l'échéance : la remarque « dans les marchés larges la fourchette
    peut valoir plusieurs points de volatilité » est exacte, et elle vaut
    aussi dans les marchés étroits dès qu'on s'éloigne de la monnaie.
    """
    v = vega(s, k, vol, t)
    return math.inf if v <= 0.0 else 100.0 * tick / v


def points_de_vol_par_tick_mesure(s: float, k: float, vol: float, t: float,
                                  tick: float = TICK) -> float:
    """Le même nombre par inversion réelle — **la route de contrôle**.

    On prend le prix, on ajoute un tick, on réinverse, on prend l'écart. La
    forme fermée est le premier ordre de cette différence ; leur accord est
    ce qui autorise à publier la première.
    """
    p = call(s, k, vol, t)
    haut = implicite(p + tick, s, k, t)
    if haut != haut:
        return math.inf
    return 100.0 * (haut - vol)


def moneyness_cotable(t: float, vol: float = VOL_REF, s: float = S_REF,
                      tick: float = TICK, bas: float = 0.40,
                      n: int = 600) -> float:
    """La moneyness au-delà de laquelle l'option ne cote plus rien.

    Le guide écrit que la solution est unique **quand elle existe**, et
    borne son existence par l'arbitrage. Il en manque une, bien plus proche :
    une option dont le prix théorique tombe sous un demi-pas de cotation
    s'affiche à zéro, et zéro est *sous* le plancher d'arbitrage. Il n'y a
    donc aucune volatilité implicite du tout, à aucune précision — et cette
    frontière-là est atteinte à quelques pour cent de la monnaie sur les
    échéances courtes, très loin de celle que le guide décrit.

    Renvoie `S/K`, cherchée du côté hors de la monnaie.
    """
    seuil = 0.5 * tick

    def f(m: float) -> float:
        return call(s, s / m, vol, t) - seuil

    if f(1.0) < 0.0:
        return 1.0
    pas = (1.0 - bas) / n
    lo, hi = 1.0, 1.0
    for i in range(1, n + 1):
        lo = 1.0 - i * pas
        if f(lo) < 0.0:
            break
    else:
        return bas
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if f(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def strike_du_point_de_vol(t: float, vol: float = VOL_REF, s: float = S_REF,
                           tick: float = TICK, bas: float = 0.25,
                           n: int = 400) -> float:
    """La moneyness au-delà de laquelle un seul tick vaut un point de vol.

    Cherchée du côté **hors de la monnaie** — donc `S/K < 1`, un call dont
    le strike est au-dessus du comptant — parce que c'est l'aile qu'un
    pupitre cote et celle dont le guide parle. Le premier jet balayait de
    l'autre côté et rendait des deltas de quatre-vingt-dix, ce qui n'est pas
    faux du véga (il est symétrique en `d₁`) mais ne décrit pas l'objet.

    Balayée puis affinée par bissection, parce qu'inverser `φ(d₁)` à la main
    donne deux racines dont une seule est du bon côté de la monnaie.
    """
    def f(m: float) -> float:
        return points_de_vol_par_tick(s, s / m, vol, t, tick) - 1.0

    hi = 1.0
    if f(hi) > 0.0:
        return 1.0
    pas = (1.0 - bas) / n
    lo = hi
    for i in range(1, n + 1):
        lo = 1.0 - i * pas
        if f(lo) > 0.0:
            break
    else:
        return bas
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def delta_du_strike(s: float, k: float, vol: float, t: float) -> float:
    return G.delta_comptant(s, k, vol, t, TAUX, DIVIDENDE)


def strike_du_delta(delta: float, t: float, vol: float = VOL_REF,
                    s: float = S_REF) -> float:
    """Le strike d'un delta donné, par bissection — la convention du pupitre.

    Le guide recommande une convention à delta fixe pour stabiliser une
    série ; la partie s'en sert pour poser ses ailes au même endroit à
    toutes les échéances, ce qu'une moneyness fixe ne fait pas.
    """
    lo, hi = s * 0.20, s * 5.0
    for _ in range(120):
        mid = 0.5 * (lo + hi)
        if delta_du_strike(s, mid, vol, t) > delta:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


#: Les deltas des ailes balayées, et l'échéance de chaque ligne.
DELTAS: tuple[float, ...] = (0.50, 0.25, 0.10, 0.05)
TENORS: tuple[float, ...] = (7.0, 30.0, 90.0, 365.0)


# ---------------------------------------------------------------------------
# III. La série de volatilité, son rang et son percentile
# ---------------------------------------------------------------------------


def serie(n: int, kappa: float = KAPPA, eta: float = ETA,
          moyenne: float = VOL_MOYENNE, graine: int = SEED) -> list[float]:
    """Une trajectoire de volatilité à retour à la moyenne, en logarithme.

    `d ln σ = κ(ln θ − ln σ)dt + η dW`, discrétisée à la séance et **amorcée
    dans son régime stationnaire** : sans quoi les premières centaines de
    points portent la condition initiale et faussent tout rang calculé
    dessus. La graine est explicite, comme partout dans ce dépôt.
    """
    dt = 1.0 / SEANCES_AN
    rng = random.Random(graine)
    m = math.log(moyenne)
    sd_stat = eta / math.sqrt(2.0 * kappa)
    x = m + sd_stat * rng.gauss(0.0, 1.0)
    rho = math.exp(-kappa * dt)
    sd_pas = sd_stat * math.sqrt(1.0 - rho * rho)
    out = []
    for _ in range(n):
        x = m + rho * (x - m) + sd_pas * rng.gauss(0.0, 1.0)
        out.append(math.exp(x))
    return out


def iv_rank(fenetre: list[float], valeur: float) -> float:
    """`(σ − σ_min)/(σ_max − σ_min)` — deux points décident de tout."""
    lo, hi = min(fenetre), max(fenetre)
    return 0.5 if hi <= lo else (valeur - lo) / (hi - lo)


def iv_percentile(fenetre: list[float], valeur: float) -> float:
    """`#{σᵢ < σ}/n` — toute la distribution décide."""
    return sum(1 for v in fenetre if v < valeur) / len(fenetre)


def effet_d_un_pic(fenetre: list[float], valeur: float,
                   facteur: float) -> tuple[float, float]:
    """Ce qu'un seul jour de crise fait au rang et au percentile.

    Le pic multiplie le maximum de la fenêtre par `facteur`. Le rang tombe
    d'un coup, parce que son dénominateur **est** ce maximum ; le percentile
    ne bouge que d'un point sur `n`, et parfois pas du tout. Renvoie les deux
    valeurs après le pic.
    """
    pique = list(fenetre)
    pique[int(len(pique) * 0.5)] = max(fenetre) * facteur
    return iv_rank(pique, valeur), iv_percentile(pique, valeur)


def sensibilite_du_rang(fenetre: list[float], valeur: float,
                        facteur: float) -> float:
    """De combien le rang bouge quand un seul point de la fenêtre bouge."""
    return abs(effet_d_un_pic(fenetre, valeur, facteur)[0]
               - iv_rank(fenetre, valeur))


def sensibilite_du_percentile(fenetre: list[float], valeur: float,
                              facteur: float) -> float:
    return abs(effet_d_un_pic(fenetre, valeur, facteur)[1]
               - iv_percentile(fenetre, valeur))


def rapport_des_sensibilites(fenetre: list[float], valeur: float,
                             facteur: float) -> float:
    """Le rapport des deux sensibilités, et il vaut la taille de la fenêtre.

    Le dénominateur n'est **pas** le déplacement mesuré du percentile mais
    son maximum possible, `1/n`. Deux raisons, et la seconde est la bonne.
    La première est qu'un déplacement mesuré vaut zéro dans la majorité des
    tirages — le pic remplace un point qui était déjà au-dessus de la valeur
    classée, donc le comptage ne change pas — et un rapport à zéro n'est pas
    un nombre. La seconde est qu'on veut publier une **borne** : le rang est
    au moins ce facteur plus sensible que le percentile ne pourra jamais
    l'être, quel que soit le tirage.

    Le résultat est donc `n · sensibilité du rang`, et il croît avec la
    fenêtre : *allonger la fenêtre, geste par lequel on croit stabiliser une
    statistique, aggrave le rang exactement dans la proportion où il
    améliore le percentile.*
    """
    return len(fenetre) * sensibilite_du_rang(fenetre, valeur, facteur)


@lru_cache(maxsize=64)
def sensibilite_moyenne_du_rang(n: int, facteur: float = 2.0,
                                tirages: int = 200) -> float:
    """Le recul moyen du rang sur `tirages` fenêtres indépendantes.

    Une seule fenêtre ne suffit pas : le recul dépend d'où tombe le maximum
    de ce tirage-là, et la colonne d'une table lue sur un tirage unique
    n'est pas monotone alors que la grandeur qu'elle mesure l'est. Le dépôt
    a déjà payé cette leçon en partie XIV, sur un contrôle de borne lu sur
    un seul point.
    """
    total = 0.0
    for j in range(tirages):
        s = serie(n + 1, graine=SEED + 4093 * j + n)
        total += sensibilite_du_rang(s[:-1], s[-1], facteur)
    return total / tirages


def borne_du_rapport(n: int, facteur: float = 2.0) -> float:
    """`n` fois le recul moyen du rang — la borne, lissée sur les tirages."""
    return n * sensibilite_moyenne_du_rang(n, facteur)


def percentile_immobile(fenetre: list[float], valeur: float,
                        facteur: float) -> bool:
    """Vrai quand le pic ne déplace le percentile de rien du tout.

    C'est le cas ordinaire, et il mérite d'être publié plutôt que caché
    derrière un tiret : un jour de crise ne change pas le comptage des jours
    moins volatils que celui qu'on classe, sauf s'il franchit ce seuil.
    """
    return sensibilite_du_percentile(fenetre, valeur, facteur) <= 0.0


#: Les longueurs de fenêtre balayées, en séances.
FENETRES: tuple[int, ...] = (63, 126, 252, 504, 1260)


# ---------------------------------------------------------------------------
# IV. L'échantillon effectif, et le budget d'un percentile
# ---------------------------------------------------------------------------


def autocorrelation(kappa: float = KAPPA, pas: float = 1.0) -> float:
    """`e^{−κ·Δt}` — la corrélation d'un pas, sous le processus déclaré."""
    return math.exp(-kappa * pas / SEANCES_AN)


def echantillon_effectif(n: int, kappa: float = KAPPA) -> float:
    """`n·(1−ρ)/(1+ρ)` — ce qu'une fenêtre de `n` séances porte vraiment.

    Pour un `κ` petit devant la fréquence d'échantillonnage, cela vaut
    `κT/2` où `T` est la **durée** de la fenêtre : le nombre d'observations
    disparaît de la formule, et ce qui reste est la durée multipliée par la
    vitesse de retour à la moyenne. *Regarder la volatilité plus souvent
    n'apprend rien de plus ; il faut la regarder plus longtemps.*
    """
    rho = autocorrelation(kappa)
    return n * (1.0 - rho) / (1.0 + rho)


def echantillon_effectif_mesure(n: int, kappa: float = KAPPA,
                                tirages: int = 400) -> float:
    """Le même nombre par la variance mesurée d'un percentile — le contrôle.

    On tire `tirages` fenêtres indépendantes, on mesure la dispersion du
    percentile de la dernière observation, et on la compare à celle qu'un
    échantillon indépendant de taille `m` rendrait : `√(p(1−p)/m)`. Le `m`
    qui referme l'égalité est l'échantillon effectif, mesuré et non postulé.
    """
    vals = []
    for j in range(tirages):
        s = serie(n + 1, kappa=kappa, graine=SEED + 7919 * j)
        vals.append(iv_percentile(s[:-1], s[-1]))
    moy = sum(vals) / len(vals)
    var = sum((v - moy) ** 2 for v in vals) / (len(vals) - 1)
    if var <= 0.0:
        return math.inf
    return moy * (1.0 - moy) / var


def seances_pour_distinguer(p: float, q: float, kappa: float = KAPPA,
                            z: float = Z_95) -> float:
    """Les séances qu'il faut pour séparer deux percentiles.

    L'échantillon indépendant requis vaut `z²(p(1−p)+q(1−q))/(p−q)²` ; la
    persistance le multiplie par `(1+ρ)/(1−ρ)`. C'est le budget
    d'information de la partie IV, rencontré sur un dixième objet — et le
    plus lourd des dix.
    """
    if p == q:
        return math.inf
    m = z * z * (p * (1 - p) + q * (1 - q)) / (p - q) ** 2
    rho = autocorrelation(kappa)
    return m * (1.0 + rho) / (1.0 - rho)


def annees_pour_distinguer(p: float, q: float, kappa: float = KAPPA) -> float:
    return seances_pour_distinguer(p, q, kappa) / SEANCES_AN


#: Les couples de percentiles que la table sépare.
COUPLES_P: tuple[tuple[float, float], ...] = (
    (0.80, 0.50), (0.90, 0.50), (0.95, 0.50), (0.90, 0.75), (0.99, 0.90),
)


# ---------------------------------------------------------------------------
# V. Le look-ahead, reproduit sous une loi nulle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Biais:
    """Ce qu'un classement rend, glissant puis fuité."""
    glissant: float
    fuite: float
    ecart: float
    seuil: float
    esperance: float


def _correlation(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    if sxx <= 0.0 or syy <= 0.0:
        return 0.0
    return sxy / math.sqrt(sxx * syy)


def implicite_juste(vol_du_jour: float, horizon: int,
                    kappa: float = KAPPA, eta: float = ETA,
                    moyenne: float = VOL_MOYENNE) -> float:
    """L'implicite d'un teneur qui connaît le processus et ne prend aucune marge.

    C'est l'espérance conditionnelle de la volatilité moyenne des `horizon`
    séances à venir, sachant celle d'aujourd'hui. Sous le processus déclaré
    elle a une **forme fermée** : le logarithme est gaussien de moyenne
    `m + ρⱼ(x − m)` et de variance `s²(1 − ρⱼ²)`, donc son exponentielle a
    l'espérance qu'on sait, et la moyenne des espérances est la somme.

    C'est la définition que le guide donne lui-même — un prix, pas un
    niveau — et elle est ce qui rend la section testable. Le premier jet
    prenait la volatilité du jour à la place, et la loi nulle rendait alors
    une corrélation franche là où elle devait rendre zéro : *sous un retour
    à la moyenne, le niveau prédit la variation, et un vendeur qui vend haut
    gagne sans avoir le moindre avantage.*
    """
    dt = 1.0 / SEANCES_AN
    m = math.log(moyenne)
    s2 = eta * eta / (2.0 * kappa)
    x = math.log(vol_du_jour)
    total = 0.0
    for j in range(1, horizon + 1):
        rho = math.exp(-kappa * j * dt)
        total += math.exp(m + rho * (x - m) + 0.5 * s2 * (1.0 - rho * rho))
    return total / horizon


@lru_cache(maxsize=32)
def biais_de_look_ahead(n: int = 4000, fenetre: int = 252,
                        horizon: int = 21, kappa: float = KAPPA) -> Biais:
    """Le résultat négatif du guide, et le positif que le bug fabrique.

    Le gain d'une expiration est l'implicite juste moins la réalisée
    observée. Il est d'espérance conditionnelle **nulle par construction**,
    donc rien de ce qui est connu le jour de la vente ne peut le prédire :
    c'est une loi nulle, et non une hypothèse. La colonne `esperance` le
    contrôle — elle doit tomber sur zéro à la précision de l'échantillon, et
    un test l'exige.

    On classe ensuite le jour de deux façons : sur la fenêtre strictement
    antérieure, puis sur une fenêtre **centrée** qui contient l'avenir. La
    première ne peut rien prédire et ne prédit rien ; la seconde prédit, et
    *c'est exactement le motif que le guide a vu disparaître.*
    """
    s = serie(n, kappa=kappa, graine=SEED + 13)
    rangs_g, rangs_f, gains = [], [], []
    demi = fenetre // 2
    for i in range(fenetre, n - horizon):
        futur = s[i:i + horizon]
        realisee = sum(futur) / len(futur)
        gains.append(implicite_juste(s[i], horizon, kappa) - realisee)
        rangs_g.append(iv_rank(s[i - fenetre:i], s[i]))
        rangs_f.append(iv_rank(s[i - demi:i + demi], s[i]))
    g = _correlation(rangs_g, gains)
    f = _correlation(rangs_f, gains)
    # Les gains se chevauchent sur `horizon` séances et pas davantage : ce
    # sont des innovations, pas des niveaux, et leur échantillon
    # indépendant est le nombre de fenêtres disjointes. Prendre ici
    # l'échantillon effectif de la **volatilité** serait le bon nombre pour
    # un test sur son niveau et un nombre dix fois trop conservateur pour
    # un test sur ses innovations.
    m = len(gains) / horizon
    seuil = Z_95 / math.sqrt(max(m, 2.0))
    moy = sum(gains) / len(gains)
    sd = math.sqrt(sum((x - moy) ** 2 for x in gains) / (len(gains) - 1))
    return Biais(g, f, f - g, seuil,
                 moy / (sd / math.sqrt(max(m, 2.0))))


#: Les horizons de détention balayés, en séances.
HORIZONS: tuple[int, ...] = (5, 10, 21, 42, 63)


# ---------------------------------------------------------------------------
# VI. La prime, et ce qu'il faut pour l'établir
# ---------------------------------------------------------------------------


#: Ce que le guide annonce pour les indices actions, en points de
#: volatilité. Cité une seule fois, comme les annonces des parties XV, XVII
#: et XVIII.
PRIME_ANNONCEE: tuple[float, float] = (2.0, 4.0)


@dataclass(frozen=True)
class Campagne:
    """Un vendeur de prime, dans les deux unités de cotation."""
    points: float
    moyenne: float
    moyenne_variance: float
    biais_d_unite: float
    ecart_type: float
    taux: float
    expirations: float
    annees: float
    part_pires: float


@lru_cache(maxsize=64)
def campagne(points: float, n: int = 6000, horizon: int = 21) -> Campagne:
    """Un vendeur dont l'implicite dépasse la volatilité vraie de `points`.

    Deux comptabilités du même livre, et elles ne disent pas la même chose.
    En **variance**, le vendeur encaisse `σ_i² − σ_r²` et son espérance vaut
    exactement `2σa + a²` : elle est nulle quand l'avantage l'est, ce qui est
    la définition d'une loi nulle. En **volatilité** — l'unité dans laquelle
    tout le monde cote — il encaisse `σ_i − σ_r`, et l'espérance porte en
    plus `σ(1 − E[√(χ²ₕ/h)])`, un terme strictement positif que la concavité
    de la racine produit *sans qu'aucun avantage existe*.

    Les chemins sont **appariés** : le même flux d'aléa sert à tous les
    avantages balayés, ce qui rend la colonne du taux de gain monotone sans
    l'avoir lissée.
    """
    rng = random.Random(SEED + 101)
    chemins = [[rng.gauss(0.0, 1.0) for _ in range(horizon)]
               for _ in range(n)]
    vol, res, res_var = 100.0 * VOL_MOYENNE, [], []
    for chemin in chemins:
        u = math.sqrt(sum(z * z for z in chemin) / horizon)
        realisee = vol * u
        res.append((vol + points) - realisee)
        res_var.append((vol + points) ** 2 - realisee * realisee)
    moy = sum(res) / len(res)
    moy_var = sum(res_var) / len(res_var)
    var = sum((x - moy) ** 2 for x in res) / (len(res) - 1)
    sd = math.sqrt(var)
    taux = sum(1 for x in res if x > 0.0) / len(res)
    pertes = sorted(x for x in res if x < 0.0)
    k = max(1, int(round(0.05 * len(res))))
    total = sum(pertes)
    part = sum(pertes[:k]) / total if total < 0.0 else 0.0
    exp_ = (Z_95 * sd / moy) ** 2 if moy > 0.0 else math.inf
    return Campagne(points, moy, moy_var, moy - points, sd, taux, exp_,
                    exp_ * horizon / SEANCES_AN, part)


def biais_d_unite(horizon: int = 21) -> float:
    """`σ(1 − E[√(χ²ₕ/h)])` — la prime qu'un changement d'unités fabrique.

    Le sujet du guide est qu'une option est cotée dans les mauvaises unités,
    exprès. Voici ce que l'unité coûte : un vendeur dont l'implicite égale
    exactement la volatilité vraie encaisse ce nombre par expiration, en
    points de volatilité, **sans avoir le moindre avantage**. C'est mesuré
    sur les mêmes chemins que la campagne et contrôlé contre le
    développement `σ/(4h)`, qui en est le premier terme.
    """
    return campagne(0.0, horizon=horizon).moyenne


def biais_d_unite_ferme(horizon: int = 21) -> float:
    """Le premier terme du développement : `σ/(4h)`.

    `E[√(χ²ₕ/h)] = 1 − 1/(4h) + O(1/h²)`. Le contrôle de la forme fermée
    contre la mesure est ce qui autorise à publier la seconde, et l'écart
    des deux dit à partir de quel horizon le développement suffit.
    """
    return 100.0 * VOL_MOYENNE / (4.0 * horizon)


#: Les avantages balayés, en points de volatilité.
PRIMES: tuple[float, ...] = (0.0, 1.0, 2.0, 3.0, 4.0, 6.0)


def taux_d_equilibre(horizon: int = 21) -> float:
    """La fréquence de gain d'un vendeur **sans le moindre avantage**.

    C'est la loi nulle de la section, et elle n'est pas un demi : la médiane
    d'un khi-deux tombe sous sa moyenne, donc la réalisée d'un échantillon
    tombe sous sa valeur vraie plus d'une fois sur deux. C'est exactement le
    mécanisme de la partie XXI — `P(χ²ₘ < m)` — rencontré sur un autre
    estimateur, et il **cesse** de valoir 68 % parce que l'objet n'est plus
    un intervalle de couverture mais une expiration entière.
    """
    return campagne(0.0, horizon=horizon).taux


# ---------------------------------------------------------------------------
# VII. Les cinq pièges, et deux qui sont le même nombre
# ---------------------------------------------------------------------------


def derive_par_deplacement(s: float, k: float, vol: float, t: float,
                           ds: float) -> float:
    """`−Δ·ΔS/𝒱` — l'implicite apparente que déplace un comptant qui bouge.

    C'est la forme fermée du piège des prix périmés **et** de celui du
    forward faux : dans les deux cas le prix de l'option est juste pour un
    comptant qui n'est plus celui qu'on utilise pour inverser. Deux des cinq
    pièges du guide sont donc le même nombre, et il porte deux noms.

    **Le signe est négatif** et le premier jet l'avait oublié : à prix
    constant, `∂σ/∂S = −(∂C/∂S)/(∂C/∂σ)`, donc croire le comptant plus haut
    qu'il n'est fait *baisser* l'implicite qu'on en déduit. L'amplitude
    était juste et les cinq pièges, tous pris en valeur absolue, ne
    voyaient rien ; c'est le contrôle contre la réinversion qui a rendu
    deux cents pour cent d'écart et montré le signe. *Une forme fermée dont
    on ne consomme que la valeur absolue est une forme fermée à moitié
    contrôlée.*
    """
    d = G.delta_comptant(s, k, vol, t, TAUX, DIVIDENDE)
    v = vega(s, k, vol, t)
    return -math.inf if v <= 0.0 else -100.0 * d * ds / v


def derive_par_deplacement_mesure(s: float, k: float, vol: float, t: float,
                                  ds: float) -> float:
    """Le même nombre par réinversion complète — la route de contrôle.

    On prend le prix au comptant vrai, puis on l'inverse au comptant faux.
    La forme fermée en est le premier ordre ; le second est le gamma, et
    l'écart des deux dit à partir de quel déplacement il faut le compter.
    """
    p = call(s, k, vol, t)
    faux = implicite(p, s + ds, k, t)
    return math.inf if faux != faux else 100.0 * (faux - vol)


def ecart_du_premier_ordre(s: float, k: float, vol: float, t: float,
                           ds: float) -> float:
    """Ce que la forme fermée manque, en part de la mesure.

    `Δ·ΔS/𝒱` est le **premier ordre** du décalage d'implicite : le second
    porte le gamma, et il n'est pas négligeable dès que le déplacement
    dépasse quelques dixièmes de pour cent. Publier ce nombre est ce qui
    distingue une superposition d'une approximation — la partie XXIII a
    payé pour cette distinction sur le rho, et la partie XXVI sur le
    sourire.
    """
    a = derive_par_deplacement(s, k, vol, t, ds)
    b = derive_par_deplacement_mesure(s, k, vol, t, ds)
    return 0.0 if b == 0.0 or b != b else abs(a - b) / abs(b)


def deplacement_d_un_prix_perime(minutes: float, vol: float = VOL_REF,
                                 s: float = S_REF) -> float:
    """Ce que le comptant parcourt pendant qu'un prix vieillit.

    L'espérance de la valeur absolue d'un déplacement gaussien vaut
    `√(2/π)·σ√Δt` : c'est la même constante que la partie XXV emploie pour
    le coût de couvrir au delta du soir, importée et non recopiée.
    """
    dt = minutes / (60.0 * 24.0 * 365.0)
    return math.sqrt(2.0 / math.pi) * s * vol * math.sqrt(dt)


#: Les âges de cotation balayés, en minutes.
AGES: tuple[float, ...] = (1.0, 5.0, 15.0, 60.0, 240.0)


@dataclass(frozen=True)
class Piege:
    """Un des cinq pièges pratiques, et ce qu'il coûte en points de vol."""
    nom: str
    cout: float
    unite: str
    remede: str


def pieges() -> tuple[Piege, ...]:
    """Les cinq pièges du guide, chiffrés dans une seule unité.

    Le guide les nomme et n'en chiffre aucun. Les mettre tous en points de
    volatilité est ce qui les rend comparables, et le classement qui en sort
    n'est pas celui de la liste. Le cinquième est un cas à part et la mesure
    le dit : un grec calculé ailleurs ne cache pas *un* des quatre autres,
    il les cache **tous**, puisqu'on ignore à la fois le forward employé, le
    taux, la convention de prix et l'âge de la cotation. Son coût est donc
    leur somme, et c'est pour cela qu'il arrive en tête d'une liste où le
    guide le place en dernier.
    """
    t = 30.0 / JOURS_AN
    k_aile = strike_du_delta(0.10, t)
    quatre = (
        Piege("Quelle cotation : bid, ask, mid ou dernier",
              points_de_vol_par_tick(S_REF, k_aile, VOL_REF, t) * 4.0,
              "une fourchette de quatre ticks à dix deltas",
              "coter en milieu et publier la largeur"),
        Piege("Quel strike : la monnaie se déplace",
              abs(derive_par_deplacement(S_REF, S_REF, VOL_REF, t,
                                         0.01 * S_REF)),
              "un déplacement d'un pour cent du comptant",
              "une convention à delta fixe"),
        Piege("Dividendes et taux : un forward faux",
              abs(derive_par_deplacement(S_REF, S_REF, VOL_REF, t,
                                         0.002 * S_REF)),
              "un forward faux de vingt points de base",
              "recalculer le forward, jamais l'emprunter"),
        Piege("Cotations périmées",
              abs(derive_par_deplacement(
                  S_REF, k_aile, VOL_REF, t,
                  deplacement_d_un_prix_perime(60.0))),
              "un prix de dix deltas vieux d'une heure",
              "filtrer sur l'âge et la largeur"),
    )
    return quatre + (
        Piege("Grecs de fournisseur",
              sum(x.cout for x in quatre),
              "les quatre autres à la fois, faute de connaître la convention",
              "réinverser depuis la prime brute"),
    )


def pire_piege() -> Piege:
    return max(pieges(), key=lambda p: p.cout)


# ---------------------------------------------------------------------------
# VIII. Le décompte
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Affirmation:
    enonce: str
    grandeur: str
    verdict: str


def affirmations() -> tuple[Affirmation, ...]:
    b = biais_de_look_ahead()
    t30 = 30.0 / JOURS_AN
    k5 = strike_du_delta(0.05, 7.0 / JOURS_AN)
    return (
        Affirmation(
            "L'implicite n'est pas une prévision : c'est le nombre qu'il "
            "faut mettre dans le modèle pour retrouver un prix observé",
            "rien",
            "**c'est la meilleure définition des dix guides**, et elle "
            "dissout la moitié des confusions qui suivent"),
        Affirmation(
            "Le véga est strictement positif, donc la solution est unique "
            "quand elle existe",
            "le risque",
            "exact, et **incomplet** : la précision de l'inversion vaut "
            + num(points_de_vol_par_tick(S_REF, k5, VOL_REF,
                                         7.0 / JOURS_AN), 1)
            + " points de volatilité par tick à cinq deltas et une semaine"),
        Affirmation(
            "Dans les marchés larges, la fourchette peut valoir plusieurs "
            "points de volatilité",
            "le risque",
            "**sous-estimé** : elle les vaut aussi dans un marché étroit, "
            "dès que le strike passe "
            + num(strike_du_point_de_vol(t30), 3) + " de moneyness"),
        Affirmation(
            "L'implicite dépasse la réalisée de deux à quatre points en "
            "indice actions",
            "le risque",
            "plausible, et il faut " + _ans(campagne(2.0).annees)
            + " pour établir le bas de la fourchette contre zéro — "
            + _ans(campagne(1.0).annees) + " pour un point, contre les "
            "quatre et demi que la partie XXI demande à un vendeur couvert"),
        Affirmation(
            "Préférez le percentile au rang : le rang est hostage d'un seul "
            "pic",
            "le risque",
            "exact, et le rapport des deux sensibilités **est** la taille de "
            "la fenêtre — allonger la fenêtre aggrave le rang"),
        Affirmation(
            "Un jour de crise peut tenir le rang bas pendant un an",
            "l'horloge",
            "exact par construction : l'ombre d'un pic dure exactement la "
            "fenêtre, et c'est le défaut du Calmar de la partie XVIII"),
        Affirmation(
            "Calculez le rang sur une fenêtre strictement glissante",
            "rien",
            "**c'est le second guide des dix à publier son propre test "
            "négatif** — et la loi nulle rend "
            + num(b.fuite, 3) + " de corrélation fuitée contre "
            + num(b.glissant, 3) + " glissante"),
        Affirmation(
            "Annoncez la fenêtre de classement",
            "rien",
            "juste et **insuffisant** : la fenêtre ne dit pas l'échantillon, "
            "qui vaut " + num(echantillon_effectif(SEANCES_AN), 1)
            + " observations pour une année de séances"),
        Affirmation(
            "Un forward faux donne une implicite fausse",
            "le risque",
            "exact, et c'est **le même nombre** que celui des cotations "
            "périmées : `Δ·ΔS/𝒱` dans les deux cas"),
    )


def compte_par_grandeur() -> dict[str, int]:
    out: dict[str, int] = {}
    for a in affirmations():
        out[a.grandeur] = out.get(a.grandeur, 0) + 1
    return out


def familles() -> tuple[tuple[str, int], ...]:
    return O.familles() + (("Implicite, partie XXVIII",
                            len(affirmations())),)


# ---------------------------------------------------------------------------
# IX. Les tables
# ---------------------------------------------------------------------------


def _pc(x: float, n: int = 1) -> str:
    return num(100.0 * x, n)


def _ans(x: float, n: int = 1) -> str:
    """Le nombre et son unité, accordés. « 0,6 ans » se lit comme une faute."""
    return num(x, n) + ("\u00a0an" if abs(x) < 2.0 else "\u00a0ans")


def table_inversion() -> Table:
    rows = []
    for jours, m in INVERSIONS:
        t = jours / JOURS_AN
        k = S_REF / m
        p = call(S_REF, k, VOL_REF, t)
        bas, haut = bornes_d_arbitrage(S_REF, k, t)
        rows.append([
            num(jours, 0), num(m, 2), num(p, 4),
            num(bas, 4), num(haut, 2),
            num(implicite(p, S_REF, k, t), 6),
            num(implicite_newton(p, S_REF, k, t), 6),
        ])
    return Table(
        "iv_inversion",
        "Deux routes vers le même nombre, et les bornes hors desquelles il "
        "n'existe pas",
        ["Jours", "S/K", "Prix", "Plancher", "Plafond",
         "Par bissection", "Par Newton"],
        rows,
        rules_after=[2],
        note="Le guide écrit qu'il n'existe pas de forme fermée, que la "
             "fonction est monotone en volatilité, et que la solution est "
             "donc unique **quand elle existe**. Les trois sont exacts, et "
             "la dernière incise mérite ses deux colonnes : sous le "
             "plancher `max(Se^{−qT} − Ke^{−rT}, 0)` et au-dessus du "
             "plafond `Se^{−qT}`, aucune volatilité positive ne rend le "
             "prix, et un outil qui rend tout de même un nombre rend du "
             "bruit. Les deux routes se referment à six décimales. Newton "
             "s'appuie sur le véga et échoue là où celui-ci s'annule ; la "
             "bissection n'échoue jamais, et **c'est déjà la mesure de la "
             "section suivante**.")


def table_tick() -> Table:
    rows = []
    for jours in TENORS:
        t = jours / JOURS_AN
        for delta in DELTAS:
            k = strike_du_delta(delta, t)
            rows.append([
                num(jours, 0), num(delta, 2), num(k / S_REF, 3),
                num(vega(S_REF, k, VOL_REF, t) / 100.0, 4),
                num(points_de_vol_par_tick(S_REF, k, VOL_REF, t), 2),
                num(points_de_vol_par_tick_mesure(S_REF, k, VOL_REF, t), 2),
            ])
    return Table(
        "iv_tick",
        "Ce qu'un seul pas de cotation vaut en points de volatilité",
        ["Jours", "Delta", "K/S", "Véga par point", "Forme fermée",
         "Par réinversion"],
        rows,
        rules_after=[3, 7, 11],
        wide=True,
        note="Si l'implicite est un changement d'unités, alors la précision "
             "de la traduction se calcule, et elle vaut `100·tick/𝒱`. Les "
             "deux dernières colonnes sont la forme fermée et la "
             "réinversion complète d'un prix augmenté d'un tick ; elles se "
             "referment partout où le véga n'est pas minuscule, et là où il "
             "l'est c'est la réinversion qui a raison. Le guide place sa "
             "remarque sur les fourchettes larges dans les marchés larges ; "
             "la mesure dit qu'elle vaut d'abord **loin de la monnaie et "
             "près de l'échéance**, y compris dans un marché parfaitement "
             "étroit. À cinq deltas et une semaine, un tick vaut "
             + num(points_de_vol_par_tick(
                 S_REF, strike_du_delta(0.05, 7.0 / JOURS_AN), VOL_REF,
                 7.0 / JOURS_AN), 1) + " points de volatilité — *l'objet "
             "coté n'a plus deux chiffres significatifs.*")


def table_frontiere() -> Table:
    rows = []
    for jours in (2.0, 7.0, 30.0, 90.0, 365.0):
        t = jours / JOURS_AN
        m = strike_du_point_de_vol(t)
        k = S_REF / m
        rows.append([
            num(jours, 0), num(m, 3), num(k / S_REF, 3),
            num(delta_du_strike(S_REF, k, VOL_REF, t), 3),
            num(points_de_vol_par_tick(S_REF, S_REF, VOL_REF, t), 2),
            num(points_de_vol_par_tick(S_REF, S_REF / 0.90, VOL_REF, t), 2),
        ])
    return Table(
        "iv_frontiere",
        "Le lieu où un tick vaut un point de volatilité entier",
        ["Jours", "S/K de la frontière", "K/S", "Delta correspondant",
         "Un tick à la monnaie", "Un tick à K/S = 1,11"],
        rows,
        note="La frontière est le lieu où un seul pas de cotation vaut un "
             "point entier de volatilité, c'est-à-dire où l'objet coté "
             "cesse d'avoir deux chiffres significatifs. Elle est cherchée "
             "du côté hors de la monnaie, celui qu'un pupitre cote ; le "
             "premier jet balayait l'autre côté et rendait des deltas de "
             "quatre-vingt-dix, ce qui n'est pas faux du véga — il est "
             "symétrique en `d₁` — mais ne décrit pas l'objet. Une "
             "affirmation écrite d'avance est ici **réfutée par la "
             "mesure** : on attendait un delta constant, par analogie avec "
             "le pic du vanna de la partie XXIV, et la colonne le contredit "
             "franchement. Le mécanisme est visible dans la formule : la "
             "frontière est à `φ(d₁) = 100·tick/(S√T)`, donc `d₁` **croît** "
             "avec l'échéance au lieu d'y rester fixe. *La partie XXIV avait "
             "un lieu à delta constant parce que son pic était celui de "
             "`φ(d₁)` fois une fonction de `d₁` ; ici le seuil est absolu, "
             "et un seuil absolu sur une densité qui s'aplatit ne peut pas "
             "rendre un argument constant.*")


def table_effectif() -> Table:
    rows = []
    for n in FENETRES:
        for kappa in (2.0, 4.0, 8.0):
            rows.append([
                num(n, 0), num(n / SEANCES_AN, 2), num(kappa, 0),
                num(autocorrelation(kappa), 4),
                num(echantillon_effectif(n, kappa), 1),
                num(echantillon_effectif_mesure(n, kappa), 1),
            ])
    return Table(
        "iv_effectif",
        "Ce qu'une fenêtre de classement porte vraiment",
        ["Séances", "Années", "κ (par an)", "Corrélation d'un pas",
         "Échantillon effectif", "Mesuré"],
        rows,
        rules_after=[2, 5, 8, 11],
        wide=True,
        note="C'est le résultat de la partie, et il vient d'un fait que le "
             "guide ne mentionne pas : la volatilité est **persistante**. "
             "L'échantillon effectif d'une fenêtre vaut `n(1−ρ)/(1+ρ)`, "
             "c'est-à-dire `κT/2` pour un retour à la moyenne lent devant "
             "la séance — *le nombre d'observations disparaît de la formule*, "
             "et ce qui reste est la durée multipliée par une vitesse qu'on "
             "n'observe pas. Une année de séances porte deux observations "
             "indépendantes à la vitesse de référence. La dernière colonne "
             "mesure la même chose par la dispersion d'un percentile sur "
             "quatre cents fenêtres tirées ; les deux se referment, ce qui "
             "autorise la première. **Regarder la volatilité plus souvent "
             "n'apprend rien ; il faut la regarder plus longtemps.**")


def table_budget() -> Table:
    rows = []
    for p, q in COUPLES_P:
        for kappa in (2.0, 4.0, 8.0):
            rows.append([
                _pc(p, 0), _pc(q, 0), num(kappa, 0),
                num(seances_pour_distinguer(p, q, kappa), 0),
                num(annees_pour_distinguer(p, q, kappa), 1),
            ])
    return Table(
        "iv_budget",
        "Les années qu'il faut pour séparer deux percentiles",
        ["Percentile observé", "Contre", "κ (par an)", "Séances requises",
         "Années"],
        rows,
        rules_after=[2, 5, 8, 11],
        note="L'échantillon indépendant requis vaut "
             "`z²(p(1−p)+q(1−q))/(p−q)²` ; la persistance le multiplie par "
             "`(1+ρ)/(1−ρ)`. C'est le budget d'information de la partie IV "
             "rencontré sur un dixième objet, et le plus lourd des dix : "
             "séparer un percentile de quatre-vingts d'un percentile de "
             "cinquante demande " + num(annees_pour_distinguer(0.80, 0.50), 1)
             + " ans de données à la vitesse de référence. Le guide "
             "recommande d'annoncer la fenêtre de classement, ce qui est "
             "juste et **insuffisant** : une fenêtre annoncée ne dit pas "
             "l'échantillon qu'elle porte, et deux outils qui annoncent la "
             "même fenêtre sur deux actifs de vitesses différentes publient "
             "deux nombres qui n'ont pas la même précision.")


def table_pic() -> Table:
    rows = []
    for n in FENETRES:
        s = serie(n + 1, graine=SEED + 31)
        fen, val = s[:-1], s[-1]
        bouge = sensibilite_du_percentile(fen, val, 2.0)
        rows.append([
            num(n, 0),
            num(iv_rank(fen, val), 3),
            num(iv_percentile(fen, val), 3),
            num(sensibilite_moyenne_du_rang(n), 4),
            num(bouge, 4) if bouge > 0.0 else "immobile",
            num(1.0 / n, 5),
            num(borne_du_rapport(n), 0),
        ])
    return Table(
        "iv_pic",
        "Ce qu'un seul jour de crise fait aux deux statistiques",
        ["Fenêtre (séances)", "Rang", "Percentile",
         "Le rang recule de", "Le percentile bouge de",
         "Au plus", "Rapport des sensibilités"],
        rows,
        wide=True,
        note="Le pic double le maximum de la fenêtre, ce qui est un "
             "événement banal en volatilité. Le rang tombe d'un coup parce "
             "que son dénominateur **est** ce maximum ; le percentile ne "
             "peut pas bouger de plus d'un point sur `n`, et dans la "
             "majorité des tirages il ne bouge pas du tout — un jour de "
             "crise ne change pas le comptage des jours moins volatils que "
             "celui qu'on classe, sauf s'il franchit ce seuil. La colonne "
             "du recul est **moyennée sur deux cents fenêtres** : lue sur "
             "un tirage unique elle n'est pas monotone, alors que la "
             "grandeur qu'elle mesure l'est, et le dépôt a déjà payé cette "
             "leçon en partie XIV. La dernière colonne rapporte ce recul au "
             "maximum possible du percentile, ce qui en fait une **borne** "
             "valable quel que soit le tirage : *allonger la fenêtre, geste "
             "par lequel on croit stabiliser une statistique, aggrave le "
             "rang exactement dans la proportion où il améliore le "
             "percentile.* C'est le défaut du Calmar de la partie XVIII — un "
             "dénominateur qui est un maximum, et il n'y a qu'un seul "
             "maximum dans une série quelle que soit sa longueur — "
             "rencontré ici sur un troisième objet.")


def table_look_ahead() -> Table:
    rows = []
    for horizon in HORIZONS:
        b = biais_de_look_ahead(horizon=horizon)
        rows.append([
            num(horizon, 0),
            num(b.glissant, 4),
            num(b.fuite, 4),
            num(b.ecart, 4),
            num(b.seuil, 4),
            "oui" if abs(b.fuite) > b.seuil >= abs(b.glissant) else "non",
        ])
    return Table(
        "iv_look_ahead",
        "Le motif que le guide a vu disparaître, reproduit sous loi nulle",
        ["Horizon (séances)", "Fenêtre glissante", "Fenêtre fuitée",
         "Écart", "Seuil à 95 %", "Le bug fabrique le motif"],
        rows,
        wide=True,
        note="La volatilité simulée ici n'a **aucune prévisibilité** : son "
             "niveau du jour ne dit rien de la réalisée qui suit, et la "
             "colonne de la fenêtre glissante le confirme en restant sous "
             "son seuil. La colonne suivante classe le même jour contre une "
             "fenêtre **centrée**, qui contient l'avenir — le bug que le "
             "guide décrit — et la corrélation apparaît. Elle n'est pas "
             "petite. *Le guide a publié un résultat négatif ; ce que le "
             "dépôt publie est le résultat positif que le bug fabrique*, ce "
             "qui explique pourquoi il est si commun dans la recherche "
             "publiée et les outils grand public. La dernière colonne est "
             "un verdict calculé, jamais écrit.")


def table_prime() -> Table:
    rows = []
    for pts in PRIMES:
        c = campagne(pts)
        rows.append([
            num(pts, 1),
            num(c.moyenne, 3),
            num(c.ecart_type, 2),
            _pc(c.taux),
            num(c.expirations, 0) if c.expirations < 1e6 else "—",
            num(c.annees, 1) if c.annees < 1e5 else "—",
            _pc(c.part_pires),
        ])
    return Table(
        "iv_prime",
        "La prime annoncée, et ce qu'il faut pour la distinguer de zéro",
        ["Avantage (pts de vol)", "Espérance", "Écart-type",
         "Fréquence de gain", "Expirations requises", "Années",
         "Part des pertes dans les 5 % pires"],
        rows,
        wide=True,
        note="Le guide annonce deux à quatre points en indice actions et "
             "décrit l'asymétrie exactement : une petite prime positive la "
             "plupart du temps, ponctuée d'épisodes où la réalisée déborde "
             "franchement. Les deux moitiés se mesurent. La première ligne "
             "est la loi nulle — **un vendeur sans le moindre avantage gagne "
             + _pc(taux_d_equilibre()) + " % de ses expirations** et perd en "
             "espérance, parce que la racine est concave et que la réalisée "
             "d'un échantillon tombe en moyenne sous sa valeur vraie. C'est "
             "la structure de la partie XXI sur un autre estimateur, et "
             "c'est ce qui fait vivre les stratégies de prime courte bien "
             "au-delà de ce que leur espérance justifie. La colonne des "
             "années dit le reste : établir le bas de la fourchette annoncée "
             "demande " + num(campagne(2.0).annees, 1) + " ans.")


def table_pieges() -> Table:
    rows = []
    for p in sorted(pieges(), key=lambda x: -x.cout):
        rows.append([p.nom, num(p.cout, 2), p.unite, p.remede])
    return Table(
        "iv_pieges",
        "Les cinq pièges pratiques, tous dans la même unité",
        ["Le piège", "Coût (pts de vol)", "Sur quoi", "Le remède"],
        rows,
        wrap_cols=[0, 2, 3],
        wide=True,
        note="Le guide nomme les cinq et n'en chiffre aucun. Les mettre "
             "tous en points de volatilité est ce qui les rend comparables, "
             "et le classement qui en sort n'est pas celui de la liste : le "
             "plus cher est « " + pire_piege().nom.lower() + " », que le "
             "guide place en dernier. Deux d'entre eux sont **le même "
             "nombre** — un forward faux et un prix périmé décalent tous "
             "deux l'implicite de `Δ·ΔS/𝒱`, la seule différence étant "
             "l'origine du décalage. La forme fermée n'est que le "
             "**premier ordre** de ce décalage, et la partie publie ce "
             "qu'elle manque : "
             + _pc(ecart_du_premier_ordre(S_REF, S_REF, VOL_REF,
                                          30.0 / JOURS_AN,
                                          0.01 * S_REF), 1)
             + " % à un pour cent de déplacement, "
             + _pc(ecart_du_premier_ordre(S_REF, S_REF, VOL_REF,
                                          30.0 / JOURS_AN,
                                          0.002 * S_REF), 1)
             + " % à vingt points de base — le second ordre porte le gamma, "
             "et il cesse d'être négligeable exactement là où le piège "
             "devient cher. Le tri est calculé, jamais écrit, et un test "
             "l'exige.")


def table_reste() -> Table:
    rows = [[a.enonce, a.grandeur, a.verdict] for a in affirmations()]
    c = compte_par_grandeur()
    return Table(
        "iv_reste",
        "Neuf affirmations, et le décompte des dix parties d'options",
        ["L'affirmation", "Ce qu'elle déplace", "Ce que la mesure en dit"],
        rows,
        wrap_cols=[0, 2],
        note=num(c.get("le risque", 0), 0) + " affirmations déplacent le "
             "risque, " + num(c.get("l'horloge", 0), 0) + " l'horloge, "
             + num(c.get("rien", 0), 0) + " rien, **aucune la direction** — "
             "septième partie consécutive dans ce cas. Sur les "
             + num(sum(n for _, n in familles()), 0) + " affirmations des "
             "dix parties consacrées aux options, aucune ne donne un sens. "
             "Ce dixième guide est le second des dix à publier le résultat "
             "de son propre test négatif, après celui du vanna, et c'est le "
             "seul des deux dont le résultat négatif porte sur un outil que "
             "le document examiné recommande par ailleurs. *Un guide qui "
             "écrit que sa propre statistique préférée ne prédit rien une "
             "fois calculée proprement est un guide qu'on peut lire.*")


def all_tables() -> dict[str, Table]:
    return {t.key: t for t in (
        table_inversion(), table_tick(), table_frontiere(),
        table_effectif(), table_budget(), table_pic(),
        table_look_ahead(), table_prime(), table_pieges(), table_reste(),
    )}


# ---------------------------------------------------------------------------
# X. Les surfaces
# ---------------------------------------------------------------------------

#: Les axes des reliefs. **Le maximum va au fond**, donc les listes sont
#: écrites dans l'ordre qui l'y met — la règle du dépôt, et la seule façon
#: qu'un relief se lise en projection isométrique.
SURF_JOURS: tuple[float, ...] = (2.0, 5.0, 12.0, 30.0, 90.0, 250.0)
SURF_JOURS_CROISSANT: tuple[float, ...] = (250.0, 90.0, 30.0, 12.0, 5.0, 2.0)
#: La surface du pas de cotation se lit en **delta** et non en moneyness.
#: Une moneyness fixe ne décrit pas le même objet à deux échéances — à
#: deux jours, `S/K = 0,90` est au-delà de la frontière où l'option cesse
#: de coter, et la cellule y rendait dix millions de points de volatilité
#: par tick. Le delta, lui, existe à toute échéance : c'est la convention
#: que le guide recommande, employée ici pour la raison qu'il donne.
SURF_DELTAS: tuple[float, ...] = (0.05, 0.10, 0.20, 0.30, 0.40, 0.50)
#: Deux listes de vitesses, et l'ordre n'est pas le même parce que les deux
#: surfaces ont leur maximum aux deux bouts : l'échantillon effectif croît
#: avec la vitesse, le budget décroît avec elle. La règle du dépôt — le
#: maximum au fond — se lit donc à l'envers d'une surface à l'autre.
SURF_KAPPA: tuple[float, ...] = (16.0, 8.0, 4.0, 2.0, 1.0, 0.5)
SURF_KAPPA_BUDGET: tuple[float, ...] = (0.5, 1.0, 2.0, 4.0, 8.0, 16.0)
SURF_FENETRE: tuple[float, ...] = (1260.0, 756.0, 504.0, 252.0, 126.0, 63.0)
SURF_PRIMES: tuple[float, ...] = (0.5, 1.0, 2.0, 3.0, 4.5, 6.0)
SURF_HORIZONS: tuple[float, ...] = (63.0, 42.0, 21.0, 10.0, 5.0)


def surface_tick() -> list[list[float]]:
    """Points de volatilité par tick, en échéance et en moneyness.

    La grandeur parcourt plus de trois ordres, donc la **hauteur porte son
    logarithme** — le geste de la partie XVII, et `figdisc._surface` prend
    un `tip_value` pour que l'infobulle publie l'unité d'origine. Sans lui
    la surface se réduit à une aiguille au coin et l'arête que la section
    décrit n'est pas visible.
    """
    out = []
    for jours in SURF_JOURS:
        t = jours / JOURS_AN
        out.append([math.log10(points_de_vol_par_tick(
            S_REF, strike_du_delta(d, t), VOL_REF, t))
            for d in SURF_DELTAS])
    return out


def surface_tick_brute() -> list[list[float]]:
    """La même surface dans son unité, pour les infobulles."""
    out = []
    for jours in SURF_JOURS:
        t = jours / JOURS_AN
        out.append([points_de_vol_par_tick(
            S_REF, strike_du_delta(d, t), VOL_REF, t)
            for d in SURF_DELTAS])
    return out


def surface_effectif() -> list[list[float]]:
    """Échantillon effectif, en vitesse de retour et en fenêtre."""
    return [[echantillon_effectif(int(n), kappa) for n in SURF_FENETRE]
            for kappa in SURF_KAPPA]


#: Les percentiles balayés par la surface du budget, du plus proche de la
#: médiane — donc du plus cher — au plus extrême.
SURF_PERCENTILES: tuple[float, ...] = (0.60, 0.70, 0.80, 0.90, 0.95, 0.99)


def surface_budget() -> list[list[float]]:
    """Années pour séparer un percentile de cinquante, en écart et vitesse.

    La hauteur porte le **logarithme** : la grandeur parcourt trois ordres,
    et un plafond fabriquerait un plateau d'ex æquo au lieu d'un sommet.
    """
    return [[math.log10(annees_pour_distinguer(p, 0.50, kappa))
             for p in SURF_PERCENTILES] for kappa in SURF_KAPPA_BUDGET]


def surface_budget_brute() -> list[list[float]]:
    """La même surface en années, pour les infobulles."""
    return [[annees_pour_distinguer(p, 0.50, kappa)
             for p in SURF_PERCENTILES] for kappa in SURF_KAPPA_BUDGET]


def surface_prime() -> list[list[float]]:
    """Années pour établir la prime, en avantage et en horizon."""
    return [[campagne(p, horizon=int(h)).annees
             for p in SURF_PRIMES] for h in SURF_HORIZONS]


# ---------------------------------------------------------------------------
# XI. Les valeurs du gabarit
# ---------------------------------------------------------------------------


def values() -> dict[str, str]:
    t30 = 30.0 / JOURS_AN
    t7 = 7.0 / JOURS_AN
    k5 = strike_du_delta(0.05, t7)
    k10 = strike_du_delta(0.10, t30)
    b = biais_de_look_ahead()
    s = serie(SEANCES_AN + 1, graine=SEED + 31)
    fen, val = s[:-1], s[-1]
    return {
        "iv_tick": num(TICK, 2),
        "iv_droite_atm": _pc(ecart_a_la_droite(S_REF, t30), 1),
        "iv_droite_aile": _pc(ecart_a_la_droite(S_REF / 1.25, t30), 0),
        "iv_biais_unite": num(biais_d_unite(), 2),
        "iv_biais_ferme": num(biais_d_unite_ferme(), 2),
        "iv_cotable_30": num(moneyness_cotable(t30), 3),
        "iv_cotable_7": num(moneyness_cotable(t7), 3),
        "iv_delta_frontiere_7": num(
            delta_du_strike(S_REF, S_REF / strike_du_point_de_vol(t7),
                            VOL_REF, t7), 3),
        "iv_delta_frontiere_an": num(
            delta_du_strike(S_REF,
                            S_REF / strike_du_point_de_vol(1.0),
                            VOL_REF, 1.0), 3),
        "iv_tick_atm": num(points_de_vol_par_tick(S_REF, S_REF, VOL_REF,
                                                  t30), 2),
        "iv_tick_aile": num(points_de_vol_par_tick(S_REF, k10, VOL_REF,
                                                   t30), 2),
        "iv_tick_extreme": num(points_de_vol_par_tick(S_REF, k5, VOL_REF,
                                                      t7), 1),
        "iv_frontiere_30": num(strike_du_point_de_vol(t30), 3),
        "iv_frontiere_7": num(strike_du_point_de_vol(t7), 3),
        "iv_kappa": num(KAPPA, 0),
        "iv_rho": num(autocorrelation(), 4),
        "iv_neff_an": num(echantillon_effectif(SEANCES_AN), 1),
        "iv_neff_cinq": num(echantillon_effectif(5 * SEANCES_AN), 1),
        "iv_neff_mesure": num(echantillon_effectif_mesure(SEANCES_AN), 1),
        "iv_annees_80": num(annees_pour_distinguer(0.80, 0.50), 1),
        "iv_annees_90": num(annees_pour_distinguer(0.90, 0.50), 1),
        "iv_annees_99": num(annees_pour_distinguer(0.99, 0.90), 1),
        "iv_rang": num(iv_rank(fen, val), 3),
        "iv_percentile": num(iv_percentile(fen, val), 3),
        "iv_sens_rang": num(sensibilite_du_rang(fen, val, 2.0), 3),
        "iv_sens_pct": num(sensibilite_du_percentile(fen, val, 2.0), 4),
        "iv_rapport_sens": num(borne_du_rapport(SEANCES_AN), 0),
        "iv_sens_rang_moy": num(sensibilite_moyenne_du_rang(SEANCES_AN), 3),
        "iv_fuite": num(b.fuite, 3),
        "iv_glissant": num(b.glissant, 3),
        "iv_seuil": num(b.seuil, 3),
        "iv_prime_bas": num(PRIME_ANNONCEE[0], 0),
        "iv_prime_haut": num(PRIME_ANNONCEE[1], 0),
        "iv_taux_nul": _pc(taux_d_equilibre()),
        "iv_annees_prime": num(campagne(2.0).annees, 1),
        "iv_part_pires": _pc(campagne(2.0).part_pires),
        "iv_pire_piege": pire_piege().nom.lower(),
        "iv_pire_cout": num(pire_piege().cout, 1),
        "iv_affirmations": num(len(affirmations()), 0),
        "iv_total_options": num(sum(n for _, n in familles()), 0),
        "iv_seances_an": num(SEANCES_AN, 0),
    }


def main() -> None:
    for t in all_tables().values():
        print(t.key, "—", t.caption)
    for k, v in values().items():
        print(f"  {k} = {v}")


if __name__ == "__main__":
    main()
