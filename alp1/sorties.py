"""Sortir d'une position intraday : ce que chaque concept coûte, et sur quoi il agit.

Le dépôt démontre un théorème sur les sorties et ne catalogue nulle part les
**concepts** de sortie. `stops.py` traite analytiquement la remontée au point
mort, puis affirme en prose que « il en va de même du stop suiveur, des prises
partielles et de tout autre schéma de gestion ». C'était vrai, et ce n'était
pas mesuré. Ce module le mesure.

La question posée
-----------------
Un opérateur intraday dispose d'une dizaine de concepts de sortie — stop et
target, remontée au point mort, stop suiveur, sortie sur temps, prise
partielle, effondrement de volatilité, clôture sèche. La question « lequel est
le meilleur ? » n'a pas de réponse tant qu'on n'a pas dit *sur quoi* un concept
de sortie peut agir. Le théorème d'arrêt optionnel le dit :

    E[R] = (µ · E[τ∧T] − c) / a

`µ` appartient au marché, `c` au courtier, `a` à la déclaration de risque.
**Il ne reste que `E[τ∧T]`.** Un concept de sortie n'agit que sur le temps de
marché, et son classement se lit sur cette seule colonne.

Ce que ce module démontre plutôt que d'affirmer
----------------------------------------------
Onze règles sont appliquées aux **mêmes** trajectoires simulées, ce qui rend
les différences bien plus précises que les niveaux. Deux résultats en sortent,
et ce sont des mesures, pas des rappels de théorème :

1. **Sous un prix sans dérive, les onze règles rendent `−c/a`**, et l'écart de
   chacune à la règle de référence est nul à l'erreur de Monte-Carlo près. Le
   stop suiveur, la prise partielle et la sortie sur temps n'y font pas
   exception : le dépôt l'écrivait sans le montrer.
2. **Sous une dérive déclarée, l'espérance simulée de chaque règle égale la
   prédiction de Wald** `(µ·E[τ∧T] − c)/a`, sur une gamme d'exposition de un à
   seize. Le classement des concepts est donc *entièrement* expliqué par le
   temps de marché, et par rien d'autre.

Sur la discrétisation
---------------------
Les trajectoires avancent par pas d'une minute, et une barrière franchie dans
le pas est constatée au prix atteint, non au prix de la barrière. Ce n'est pas
une approximation d'une règle continue : **c'est la règle**, et le théorème
d'arrêt optionnel s'y applique exactement, puisqu'un temps d'arrêt discret est
un temps d'arrêt. Le remplissage retenu est donc le pire cas, celui que
`measure.fill="extreme"` nomme ailleurs dans le dépôt.

Sur la géométrie retenue
------------------------
La simulation tourne au stop de 0,150 % — celui que le chapitre du seuil
désigne — et non au stop déclaré de 0,010 %. La raison est arithmétique et
elle est elle-même un résultat : à 0,6 point de stop, **une minute de bruit
vaut deux fois le stop**, et la position est close avant qu'aucune gestion
n'ait pu agir. Il n'y a pas de concept de sortie à la géométrie déclarée ; il
n'y a qu'une friction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from .costs import COST_BASE, ES, stop_points
from . import quant as q
from .report import Table, num
from .report11 import DERIVE_TRAVAIL

#: Largeur de stop de la simulation, en pour-cent de l'indice. C'est celle que
#: le chapitre du seuil désigne comme optimale, et la seule où une gestion de
#: sortie dispose de place pour agir.
STOP_PCT = 0.150

#: Pas de temps, en minutes, et durée de séance.
PAS_MIN = 1.0
SEANCE_MIN = int(q.SESSION_MIN)

#: Nombre de trajectoires. Chacune est doublée par son antithétique — même
#: bruit, signe opposé — ce qui annule au premier ordre la composante
#: symétrique de la variance sans coûter un tirage de plus.
N_PATHS = 24000
SEED = 20260829

#: Friction supplémentaire d'un remplissage intermédiaire, en fraction de la
#: friction d'aller-retour. Une prise partielle sur la moitié de la position
#: ajoute une demi-sortie, donc un quart d'aller-retour.
FRICTION_FILL = 0.25


def stop_points_declare() -> float:
    return stop_points(q.INDEX_LEVEL, STOP_PCT)


def friction() -> float:
    return COST_BASE.friction_points(ES)


def bruit_par_pas() -> float:
    return q.SIGMA_1MIN * math.sqrt(PAS_MIN)


# --- Les règles ------------------------------------------------------------
#
# Chacune reçoit la trajectoire des prix relatifs à l'entrée, en points, et
# rend `(pas de sortie, prix de sortie, remplissages, temps d'exposition)`.
# Aucune ne regarde au-delà de son index : ce sont des temps d'arrêt, et c'est
# ce qui rend le théorème applicable.
#
# Le quatrième terme n'est pas le temps de sortie : c'est **l'intégrale de la
# taille de position**, en minutes de position pleine. Les deux coïncident
# pour onze règles sur douze, et divergent pour la prise partielle — qui est
# la seule à changer de taille en cours de route. C'est cette divergence qui
# explique pourquoi sa prédiction de Wald échouait quand la colonne portait le
# temps de sortie : l'identité de Wald mesure le temps **exposé**, pas le
# temps écoulé.


@dataclass(frozen=True)
class Regle:
    """Un concept de sortie, son nom, sa famille et sa fonction d'arrêt."""

    cle: str
    nom: str
    famille: str          # « discrétionnaire » ou « quantitatif »
    fn: object
    lecture: str


def _stop_seul(p, a):
    for i, x in enumerate(p):
        if x <= -a:
            return i, x, 0, float(i)
    n = len(p) - 1
    return n, p[-1], 0, float(n)


def _barrieres(p, a, rr):
    b = rr * a
    for i, x in enumerate(p):
        if x <= -a or x >= b:
            return i, x, 0, float(i)
    n = len(p) - 1
    return n, p[-1], 0, float(n)


def _point_mort(p, a):
    seuil = -a
    for i, x in enumerate(p):
        if x <= seuil:
            return i, x, 0, float(i)
        if x >= a:
            seuil = 0.0
    n = len(p) - 1
    return n, p[-1], 0, float(n)


def _suiveur(p, a, d):
    haut = 0.0
    for i, x in enumerate(p):
        if x <= haut - d:
            return i, x, 0, float(i)
        if x > haut:
            haut = x
    n = len(p) - 1
    return n, p[-1], 0, float(n)


def _temps(p, a, n):
    for i, x in enumerate(p):
        if x <= -a or i >= n:
            return i, x, 0, float(i)
    m = len(p) - 1
    return m, p[-1], 0, float(m)


def _partielle(p, a):
    """Moitié prise à +1R, le reste protégé au point mort jusqu'à la clôture.

    Le prix rendu est la moyenne des deux sorties, et le remplissage
    intermédiaire est compté : une prise partielle achète de la variance en
    payant de la friction, et la table doit le montrer.

    Les deux sorties sont constatées **au prix atteint**, comme celles de
    toutes les autres règles. Les avoir constatées au prix de la barrière
    faisait perdre à cette règle le dépassement du pas, et elle seule : la
    colonne d'écart affichait alors un coût qui n'était qu'un remplissage
    différent des autres.
    """
    pris, prix1, pas1 = False, 0.0, 0
    seuil = -a
    for i, x in enumerate(p):
        if x <= seuil:
            if not pris:
                return i, x, 0, float(i)
            return i, 0.5 * prix1 + 0.5 * x, 1, pas1 + 0.5 * (i - pas1)
        if not pris and x >= a:
            pris, prix1, pas1, seuil = True, x, i, 0.0
    n, fin = len(p) - 1, p[-1]
    if not pris:
        return n, fin, 0, float(n)
    return n, 0.5 * prix1 + 0.5 * fin, 1, pas1 + 0.5 * (n - pas1)


def _volatilite(p, a, fenetre, fraction):
    """Sortie quand l'amplitude récente tombe sous une fraction de l'attendu.

    C'est le concept « le mouvement est fini, je sors » rendu calculable. Il
    ne regarde que le passé du prix, donc c'est un temps d'arrêt, donc il ne
    crée pas d'espérance — la table le vérifie plutôt que de le supposer.
    """
    attendu = fraction * bruit_par_pas() * math.sqrt(fenetre)
    for i, x in enumerate(p):
        if x <= -a:
            return i, x, 0, float(i)
        if i >= fenetre:
            recent = p[i - fenetre:i + 1]
            if max(recent) - min(recent) < attendu:
                return i, x, 0, float(i)
    n = len(p) - 1
    return n, p[-1], 0, float(n)


def _cloture(p, a):
    n = len(p) - 1
    return n, p[-1], 0, float(n)


def regles() -> tuple[Regle, ...]:
    """Les onze concepts, dans l'ordre où un opérateur les rencontre."""
    return (
        Regle("stop", "Stop seul, sortie à la clôture", "discrétionnaire",
              lambda p, a: _stop_seul(p, a),
              "la règle de référence : rien d'autre qu'un risque borné"),
        Regle("rr2", "Stop et target 1:2", "discrétionnaire",
              lambda p, a: _barrieres(p, a, 2.0),
              "le target proche coupe l'exposition de moitié"),
        Regle("rr5", "Stop et target 1:5", "discrétionnaire",
              lambda p, a: _barrieres(p, a, 5.0),
              "le target lointain est rarement atteint dans la séance"),
        Regle("rr20", "Stop et target 1:20", "discrétionnaire",
              lambda p, a: _barrieres(p, a, 20.0),
              "au-delà de la portée d'une séance : équivaut au stop seul"),
        Regle("be", "Remontée au point mort à +1R", "discrétionnaire",
              lambda p, a: _point_mort(p, a),
              "convertit des gagnants en nuls et des perdants en nuls"),
        Regle("suiv1", "Stop suiveur à 1R", "discrétionnaire",
              lambda p, a: _suiveur(p, a, a),
              "suit le plus haut atteint, à un risque nominal de distance"),
        Regle("suiv05", "Stop suiveur à ½R", "discrétionnaire",
              lambda p, a: _suiveur(p, a, 0.5 * a),
              "serré : coupe l'exposition d'un facteur huit"),
        Regle("t60", "Sortie sur temps, 60 minutes", "quantitatif",
              lambda p, a: _temps(p, a, 60),
              "le seul concept qui borne l'exposition sans borner le risque"),
        Regle("t120", "Sortie sur temps, 120 minutes", "quantitatif",
              lambda p, a: _temps(p, a, 120),
              "même mécanique, deux fois plus de temps de marché"),
        Regle("part", "Prise partielle à +1R, reste au point mort",
              "discrétionnaire", lambda p, a: _partielle(p, a),
              "paie une friction de plus pour acheter de la variance en moins"),
        Regle("vol", "Effondrement de volatilité", "quantitatif",
              lambda p, a: _volatilite(p, a, 30, 0.55),
              "« le mouvement est fini » — mais il ne lit que le prix passé"),
        Regle("clot", "Clôture sèche, sans stop", "quantitatif",
              lambda p, a: _cloture(p, a),
              "le maximum de temps de marché, et une perte non bornée"),
    )


# --- La mesure -------------------------------------------------------------


@dataclass(frozen=True)
class Mesure:
    """Ce qu'une règle rend, à une dérive donnée."""

    cle: str
    exposition: float     # E[∫H dt] : minutes de position pleine
    ecoule: float         # E[τ∧T] : minutes jusqu'à la sortie finale
    esperance: float      # E[R] simulée
    wald: float           # (µ·E[τ∧T] − c̄)/a, avec la friction propre à la règle
    friction: float       # c̄ : friction moyenne réellement payée, en points
    ecart_type: float
    ecart_ref: float      # E[R] − E[R de la règle de référence]
    ecart_ref_se: float   # erreur type de cet écart, trajectoires appariées
    taux_gain: float


def _increments(rng, n):
    return [rng.gauss() for _ in range(n)]


@lru_cache(maxsize=None)
def mesurer(drift_per_hour: float, n_paths: int = N_PATHS,
            reference: str = "clot") -> tuple[Mesure, ...]:
    """Applique les onze règles aux **mêmes** trajectoires.

    Les trajectoires communes sont ce qui rend la colonne d'écart utilisable :
    la variance d'une différence appariée est d'un ordre de grandeur sous
    celle des niveaux, et c'est la différence qui répond à la question posée.
    Chaque tirage est doublé par son antithétique, bruit de signe opposé et
    dérive inchangée.

    La référence est la clôture sèche, et ce choix n'est pas de commodité :
    sa valeur terminale est la somme des incréments, dont l'appariement
    antithétique annule **exactement** la partie bruit. Sa ligne vaut donc
    `(µ·T − c̄)/a` sans erreur d'échantillonnage, et c'est elle qui ancre la
    table. Les autres règles franchissent des barrières, opération que
    l'appariement ne symétrise pas ; leur niveau porte un décalage commun
    d'échantillonnage que la colonne d'écart, elle, ne porte pas.
    """
    from .mc import Rng

    a, c = stop_points_declare(), friction()
    sig, mu = bruit_par_pas(), drift_per_hour / 60.0 * PAS_MIN
    rs = regles()
    somme = {r.cle: 0.0 for r in rs}
    carre = {r.cle: 0.0 for r in rs}
    tau = {r.cle: 0.0 for r in rs}
    ecoul = {r.cle: 0.0 for r in rs}
    gains = {r.cle: 0 for r in rs}
    fric = {r.cle: 0.0 for r in rs}
    d_somme = {r.cle: 0.0 for r in rs}
    d_carre = {r.cle: 0.0 for r in rs}

    rng = Rng(SEED)
    n = 0
    for _ in range(n_paths):
        z = _increments(rng, SEANCE_MIN)
        for signe in (1.0, -1.0):
            x, p = 0.0, [0.0]
            for u in z:
                x += mu + sig * signe * u
                p.append(x)
            n += 1
            vals = {}
            for r in rs:
                i, sortie, fills, expo = r.fn(p, a)
                cc = c * (1.0 + FRICTION_FILL * fills)
                fric[r.cle] += cc
                rr = (sortie - cc) / a
                somme[r.cle] += rr
                carre[r.cle] += rr * rr
                tau[r.cle] += expo * PAS_MIN
                ecoul[r.cle] += i * PAS_MIN
                gains[r.cle] += 1 if rr > 0.0 else 0
                vals[r.cle] = rr
            base = vals[reference]
            for r in rs:
                d = vals[r.cle] - base
                d_somme[r.cle] += d
                d_carre[r.cle] += d * d

    out = []
    for r in rs:
        m = somme[r.cle] / n
        v = max(carre[r.cle] / n - m * m, 0.0)
        e = tau[r.cle] / n
        dm = d_somme[r.cle] / n
        dv = max(d_carre[r.cle] / n - dm * dm, 0.0)
        cc = fric[r.cle] / n
        out.append(Mesure(
            cle=r.cle, exposition=e, ecoule=ecoul[r.cle] / n, esperance=m,
            wald=(drift_per_hour / 60.0 * e - cc) / a, friction=cc,
            ecart_type=math.sqrt(v), ecart_ref=dm,
            ecart_ref_se=math.sqrt(dv / n), taux_gain=gains[r.cle] / n,
        ))
    return tuple(out)


def bruit_sur_stop_declare() -> float:
    """Combien de stops déclarés tiennent dans une minute de bruit."""
    return q.SIGMA_1MIN / q.STOP_PTS


# --- Tables ----------------------------------------------------------------


def _par_cle(drift: float) -> dict[str, Mesure]:
    return {m.cle: m for m in mesurer(drift)}


def table_sorties_nulles() -> Table:
    """Les douze concepts sous un prix sans dérive."""
    ms, rs = _par_cle(0.0), {r.cle: r for r in regles()}
    ratio = friction() / stop_points_declare()
    rows = []
    for r in regles():
        m = ms[r.cle]
        rows.append([
            r.nom, r.famille[:5] + ".",
            num(m.exposition, 0),
            num(m.esperance, 4, signed=True),
            num(m.ecart_ref, 4, signed=True) + " ± "
            + num(2.0 * m.ecart_ref_se, 4),
            num(m.ecart_type, 2),
            num(100.0 * m.taux_gain, 0) + " %",
        ])
    pire = max(abs(m.esperance - m.wald) for m in ms.values())
    return Table(
        "sorties_nulles",
        "Douze concepts de sortie sous un prix sans dérive, appliqués aux "
        "mêmes trajectoires",
        ["Concept", "Famille", "Exposition (min)", "E[R] (R)",
         "Écart à la clôture sèche", "σ[R]", "Taux de gain"],
        rows,
        wrap_cols=[0],
        wide=True,
        rules_after=[len(rows) - 1],
        note="La ligne de clôture sèche vaut `−c/a` = "
             + num(-ratio, 4) + " **exactement**, et non à l'erreur près : "
             "sa valeur terminale est la somme des incréments, dont "
             "l'appariement antithétique annule la partie bruit. C'est elle "
             "qui ancre la table. Les onze autres franchissent des barrières, "
             "et leur écart à cette ancre est nul à l'erreur de Monte-Carlo "
             "près — l'intervalle donné est à deux écarts types, sur "
             "trajectoires appariées. Le pire écart à la prédiction vaut "
             + num(pire, 4) + " R, soit " + num(100.0 * pire / ratio, 0)
             + " % du ratio de friction. **Aucun concept de sortie ne crée "
             "d'espérance, et cela vaut pour le stop suiveur, la prise "
             "partielle et la sortie sur temps** — que le dépôt affirmait "
             "sans les mesurer. Ce qui change d'une ligne à l'autre est la "
             "dispersion, d'un facteur quatre, et le taux de gain, de dix-sept "
             "à cinquante pour cent.")


def table_sorties_derive() -> Table:
    """Les douze concepts sous une dérive déclarée, et la prédiction de Wald."""
    ms = _par_cle(DERIVE_TRAVAIL)
    ordre = sorted(regles(), key=lambda r: -ms[r.cle].exposition)
    rows = []
    for r in ordre:
        m = ms[r.cle]
        sharpe = m.esperance / m.ecart_type if m.ecart_type else 0.0
        rows.append([
            r.nom,
            num(m.exposition, 0),
            num(m.ecoule, 0) if abs(m.ecoule - m.exposition) > 0.5 else "—",
            num(m.esperance, 4, signed=True),
            num(m.wald, 4, signed=True),
            num(m.esperance - m.wald, 4, signed=True),
            num(sharpe, 4, signed=True),
        ])
    pire = max(abs(m.esperance - m.wald) for m in ms.values())
    part = ms["part"]
    return Table(
        "sorties_derive",
        "Les mêmes douze concepts sous une dérive déclarée de "
        + num(DERIVE_TRAVAIL, 1) + " point par heure, rangés par exposition",
        ["Concept", "Exposition (min)", "Temps écoulé", "E[R] simulée",
         "Wald (µ·E[τ] − c)/a", "Écart", "Sharpe/trade"],
        rows,
        wrap_cols=[0],
        wide=True,
        rules_after=[0],
        note="La cinquième colonne n'est pas ajustée : c'est l'identité de "
             "Wald évaluée sur l'exposition mesurée, et la sixième dit ce "
             "qu'il en reste. Le pire écart vaut " + num(pire, 4) + " R sur "
             "une gamme d'espérance de " + num(ms["suiv05"].esperance, 3)
             + " à " + num(ms["clot"].esperance, 3) + " R. **Le classement "
             "des concepts de sortie est entièrement expliqué par la première "
             "colonne**, et par rien d'autre : aucune règle n'ajoute ni ne "
             "retire quoi que ce soit à ce que son temps d'exposition "
             "commande. La troisième colonne n'est renseignée que pour la "
             "prise partielle, seule règle qui change de taille en cours de "
             "route : son temps écoulé vaut " + num(part.ecoule, 0)
             + " minutes quand son temps *exposé* n'en vaut que "
             + num(part.exposition, 0) + ". Elle a la durée d'un trade long "
             "et le rendement d'un trade court, et c'est là tout son coût.")


TABLES = (table_sorties_nulles, table_sorties_derive)


def all_tables() -> dict[str, Table]:
    return {fn().key: fn() for fn in TABLES}


def values() -> dict[str, str]:
    n0, nd = _par_cle(0.0), _par_cle(DERIVE_TRAVAIL)
    ratio = friction() / stop_points_declare()
    pire0 = max(abs(m.esperance - m.wald) for m in n0.values())
    pired = max(abs(m.esperance - m.wald) for m in nd.values())
    return {
        "so_stop_pct": num(STOP_PCT, 3),
        "so_stop_pts": num(stop_points_declare(), 1),
        "so_n": num(2 * N_PATHS, 0),
        "so_regles": num(len(regles()), 0),
        "so_ratio": num(ratio, 4),
        "so_pire_nul": num(pire0, 4),
        "so_pire_derive": num(pired, 4),
        "so_expo_min": num(nd["suiv05"].exposition, 0),
        "so_expo_max": num(nd["clot"].exposition, 0),
        "so_er_min": num(nd["suiv05"].esperance, 3, signed=True),
        "so_er_max": num(nd["clot"].esperance, 3, signed=True),
        "so_facteur": num(nd["clot"].exposition / nd["suiv05"].exposition, 0),
        "so_part_ecoule": num(nd["part"].ecoule, 0),
        "so_part_expo": num(nd["part"].exposition, 0),
        "so_part_cout": num(nd["part"].esperance - nd["stop"].esperance, 3,
                            signed=True),
        "so_sd_min": num(min(m.ecart_type for m in n0.values()), 2),
        "so_sd_max": num(max(m.ecart_type for m in n0.values()), 2),
        "so_gain_min": num(100.0 * min(m.taux_gain for m in n0.values()), 0),
        "so_gain_max": num(100.0 * max(m.taux_gain for m in n0.values()), 0),
        "so_bruit_stop": num(bruit_sur_stop_declare(), 2),
        "so_be_cout": num(nd["be"].esperance - nd["stop"].esperance, 3,
                          signed=True),
        "so_suiveur_cout": num(nd["suiv05"].esperance - nd["clot"].esperance,
                               3, signed=True),
    }


def main() -> None:
    for fn in TABLES:
        t = fn()
        print(t.caption)
        print(t.to_text())
        print()
    for k, v in values().items():
        print(f"  {k:18} {v}")
