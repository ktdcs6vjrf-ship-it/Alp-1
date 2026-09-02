"""La grandeur qu'on cite n'est pas celle qui décide.

Cette partie part du premier document de la série d'options dont la partie XIX
a examiné le second. Il est consacré au delta, et il tient tout entier dans
une observation que son auteur formule sans en tirer toutes les conséquences :
*les opérateurs emploient un seul mot pour au moins trois grandeurs
différentes, et confondre les trois est la première source d'erreur de
dimensionnement.*

Le dépôt reprend l'observation et découvre d'abord qu'elle le concerne.

I. Une cible a trois probabilités
--------------------------------
Avant de regarder le delta de quiconque, il faut regarder le sien. Une cible
posée à `b` points de l'entrée porte trois nombres, tous exacts, tous
calculables, et tous appelés « la probabilité que ma cible soit touchée » :

* `a/(a+b)` — la toucher **avant le stop**, la seule qui décide du trade ;
* `2Φ(−b/σ√T)` — la toucher **à un moment**, celle qu'un graphique montre ;
* `Φ(−b/σ√T)` — **clôturer au-delà**, celle qu'un backtest naïf rapporte.

À la géométrie déclarée du document elles valent 4,76 %, 62,7 % et 31,3 % :
**un facteur treize entre la première et la deuxième.** Et l'erreur ne coûte
pas un peu. Portée dans l'identité de Wald, la deuxième transforme une
espérance vraie de `−c/a` en une espérance crue de plus de onze R.

II. Un delta en a trois aussi
-----------------------------
`Δ = e^{−qT}N(d₁)` couvre. `N(d₂)` est la probabilité risque-neutre de finir
dans la monnaie. `−∂V/∂K` est le dual delta, dont on tire une densité. Le
raccourci « le delta est la probabilité de finir dans la monnaie » confond les
deux premiers, et l'écart se calcule : il croît avec la volatilité et avec
l'échéance, c'est-à-dire **exactement là où l'on s'appuie le plus dessus**.

La coupure est la même que celle de la partie I, et ce n'est pas une analogie.
`N(d₁)` pondère par le chemin, `N(d₂)` ne regarde que le terme ; `a/(a+b)`
pondère par le chemin, `Φ(−b/σ√T)` ne regarde que le terme. Deux domaines, une
seule confusion.

III. Ce qui bouge pendant qu'on ne fait rien
--------------------------------------------
Le charm est la dérivée du delta par rapport au temps seul. Le document dit
qu'il « domine dans les derniers jours ». La mesure raffine : **à la monnaie
il est quasi nul** — un millième de delta par jour à un jour de l'échéance,
contre cent vingt-trois à son maximum — et ce maximum vit hors de la monnaie,
dans une bande qui se resserre vers le strike à mesure que l'échéance
approche. Le lieu de ce maximum a une forme fermée,
`d₁* = (σ√T ± √(σ²T+4))/2`, contrôlée ici contre un balayage. Son amplitude,
elle, tend vers `φ(1)/2T` : l'échéance la déplace d'un facteur cent cinquante
sur la plage utile, la volatilité d'un facteur un et demi.

IV. Le résumé qui cache
-----------------------
Le delta d'un livre s'additionne, et c'est ce qui le rend commode et
dangereux. Deux livres de delta net identique peuvent être des paris opposés.
Le module en construit deux et les fait marcher sur le même mouvement.

V. La convention qu'on n'attache pas
------------------------------------
Delta comptant, delta forward, delta ajusté de la prime : trois nombres pour
un mot, séparés par `e^{−qT}`, `e^{−rT}` et la prime elle-même. Sur un indice
l'écart est petit ; il ne l'est pas partout, et un pupitre qui mélange les
conventions construit un livre mal couvert.

VI. Le témoin, une seconde fois
-------------------------------
Le même document rapporte, pour les agrégats dérivés du delta, le **même**
résultat nul que la partie XIX a repris pour ceux dérivés du gamma, et avec le
même protocole : le contrôle apparié en distance. C'est une seconde
application indépendante, sur une famille différente, et c'est ce qui fait
d'un contrôle une méthode.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from . import niveaux as nv
from . import quant as q
from . import seuil
from .costs import COST_BASE, ES, norm_cdf
from .emprunts import BETA_CONTINUITE
from .horizon import outcome
from .mc import Rng
from .report import Table, num

SEED = 20260908

#: L'écart-type d'une séance entière, en points.
SIGMA_SEANCE = q.SIGMA_1MIN * math.sqrt(q.SESSION_MIN)

FRICTION = COST_BASE.friction_points(ES)


def _phi(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


# ---------------------------------------------------------------------------
# I. Une cible a trois probabilités
# ---------------------------------------------------------------------------


def p_avant_stop(stop_pts: float, cible_pts: float,
                 minutes: float = q.SESSION_MIN,
                 sigma: float = q.SIGMA_1MIN) -> float:
    """Toucher la cible **avant** le stop. La seule qui décide du trade.

    Calculée par `horizon.outcome`, donc avec la troncature de séance. Sa
    forme fermée non bornée est `a/(a+b)`, et l'accord des deux est contrôlé.
    """
    return outcome(stop_pts, cible_pts, minutes, sigma).p_target


def p_avant_stop_ferme(stop_pts: float, cible_pts: float) -> float:
    """`a/(a+b)` — la forme fermée du problème non borné."""
    return stop_pts / (stop_pts + cible_pts)


def p_touche(cible_pts: float, minutes: float = q.SESSION_MIN,
             sigma: float = q.SIGMA_1MIN) -> float:
    """Toucher la cible **à un moment** de la séance : `2Φ(−b/σ√T)`.

    C'est le principe de réflexion, et c'est le nombre qu'un graphique donne à
    l'œil : le prix est passé là, donc « ça marche ». Il ne dit rien de ce
    qu'on avait déjà perdu avant d'y arriver.
    """
    return 2.0 * norm_cdf(-cible_pts / (sigma * math.sqrt(minutes)))


def p_cloture(cible_pts: float, minutes: float = q.SESSION_MIN,
              sigma: float = q.SIGMA_1MIN) -> float:
    """Clôturer au-delà de la cible : `Φ(−b/σ√T)`.

    C'est le nombre qu'un backtest rend quand il mesure « le prix était-il
    au-dessus à la clôture », et c'est la moitié du précédent — exactement,
    par le principe de réflexion.
    """
    return norm_cdf(-cible_pts / (sigma * math.sqrt(minutes)))


#: Rapports gain/risque balayés, à stop déclaré. Le rapport déclaré du
#: document y figure.
RR_GRID: tuple[float, ...] = (2.0, 5.0, 10.0, 20.0, 40.0, 80.0)


def table_probas() -> Table:
    a = q.STOP_PTS
    rows = []
    for rr in RR_GRID:
        b = rr * a
        o = outcome(a, b, q.SESSION_MIN, q.SIGMA_1MIN)
        p1, p2, p3 = o.p_target, p_touche(b), p_cloture(b)
        rows.append([
            num(rr, 0),
            num(b, 1),
            num(b / SIGMA_SEANCE, 3),
            num(100 * p1, 2),
            num(100 * p2, 1),
            num(100 * p3, 1),
            num(p2 / p1, 1),
            num(100 * o.p_open, 2),
        ])
    b0 = q.RR_REF * a
    return Table(
        key="gr_probas",
        caption="Trois probabilités pour une seule cible, et elles ne se ressemblent pas",
        headers=["Rapport gain/risque", "Cible (points)", "Cible (σ de séance)",
                 "Touchée avant le stop (%)", "Touchée à un moment (%)",
                 "Clôture au-delà (%)", "Rapport des deux premières",
                 "Clôture avant barrière (%)"],
        rows=rows,
        note="Les trois colonnes sont exactes et portent le même nom dans la "
             "bouche de tout le monde. La première est celle qui décide d'un "
             "trade, et c'est le théorème d'arrêt optionnel : `a/(a+b)`, sans "
             "aucune référence à la volatilité. La deuxième est celle qu'un "
             "**graphique** donne à l'œil — le prix est passé là, donc « ça "
             "marche » — et c'est le principe de réflexion. La troisième est "
             "celle qu'un **backtest naïf** rapporte quand il demande si le "
             "prix était au-delà à la clôture ; elle vaut exactement la "
             "moitié de la deuxième, ce qui est le même principe lu à "
             "l'envers. À la géométrie déclarée du document, elles valent "
             + num(100 * p_avant_stop(a, b0), 2) + " %, "
             + num(100 * p_touche(b0), 1) + " % et "
             + num(100 * p_cloture(b0), 1) + " % : **un facteur "
             + num(p_touche(b0) / p_avant_stop(a, b0), 0) + " entre la "
             "première et la deuxième.** La dernière colonne montre que "
             "l'écart n'est pas un accident de réglage : il croît avec "
             "l'ambition de la cible, c'est-à-dire précisément là où la "
             "confusion est la plus tentante. La dernière colonne porte la "
             "condition, comme dans la partie précédente&nbsp;: `a/(a+b)` est "
             "le taux du problème **non borné**, et la séance finit. Elle est "
             "négligeable jusqu'à un rapport de vingt&nbsp;; à quatre-vingts, "
             "la cible est à " + num(RR_GRID[-1] * a / SIGMA_SEANCE, 1)
             + " écarts-types de séance, une décision sur "
             + num(1.0 / outcome(a, RR_GRID[-1] * a, q.SESSION_MIN,
                                 q.SIGMA_1MIN).p_open, 0) + " finit à la "
             "clôture, et la première colonne vaut alors la moitié de sa "
             "forme fermée. **La dernière ligne de cette table est un ordre "
             "de grandeur, pas une mesure.**",
    )


def esperance_r(p: float, stop_pts: float = q.STOP_PTS,
                rr: float = q.RR_REF, friction: float = FRICTION) -> float:
    """`E[R] = p·R − (1−p) − c/a`, l'identité du document.

    Elle prend la probabilité qu'on lui donne. C'est tout l'objet de la
    section : **elle ne sait pas laquelle on lui a donnée.**
    """
    return p * rr - (1.0 - p) - friction / stop_pts


def table_cout() -> Table:
    a = q.STOP_PTS
    b = q.RR_REF * a
    lignes = (
        ("Touchée avant le stop", p_avant_stop(a, b), "celle qui décide"),
        ("Clôture au-delà", p_cloture(b), "celle d'un backtest naïf"),
        ("Touchée à un moment", p_touche(b), "celle que l'œil retient"),
    )
    vraie = esperance_r(p_avant_stop(a, b))
    rows = []
    for nom, p, source in lignes:
        e = esperance_r(p)
        rows.append([
            nom,
            source,
            num(100 * p, 2),
            num(e, 3, signed=True),
            num(e - vraie, 2, signed=True),
            "exacte" if abs(e - vraie) < 1e-9 else "crue",
        ])
    equilibre = (1.0 + FRICTION / a) / (1.0 + q.RR_REF)
    return Table(
        key="gr_cout",
        caption="Ce que la confusion coûte, portée dans l'identité de Wald",
        headers=["Probabilité employée", "D'où elle vient", "Sa valeur (%)",
                 "E[R] qui en découle", "Écart à la vérité (R)", "Statut"],
        rows=rows,
        note="L'identité `E[R] = p·R − (1−p) − c/a` ne vérifie pas laquelle "
             "des trois on lui a passée, et c'est tout le problème. Avec la "
             "bonne, elle rend " + num(vraie, 3, signed=True) + " R, "
             "c'est-à-dire exactement `−c/a` — le résultat structurant du "
             "document, une fois de plus. Avec celle qu'un backtest naïf "
             "rapporte, elle rend "
             + num(esperance_r(p_cloture(b)), 2, signed=True) + " R. Avec "
             "celle que l'œil retient, "
             + num(esperance_r(p_touche(b)), 2, signed=True) + " R. **L'écart "
             "entre la vérité et la croyance vaut "
             + num(esperance_r(p_touche(b)) - vraie, 1) + " R par décision**, "
             "et il ne vient d'aucune erreur de marché : il vient de la "
             "question qu'on a posée. Le taux d'équilibre, lui, vaut "
             + num(100 * equilibre, 2) + " % — il est plus haut que la "
             "première colonne et plus bas que les deux autres, et c'est "
             "pourquoi la confusion ne se voit pas : *les trois nombres sont "
             "de part et d'autre du seuil qui décide.*",
        wrap_cols=[0, 1],
    )


# ---------------------------------------------------------------------------
# I bis. Les trois, sur des trajectoires
# ---------------------------------------------------------------------------
#
# Les trois formes fermées ci-dessus n'avaient, dans le premier jet de ce
# module, aucun contrôle par simulation — et la règle du dépôt est sans
# exception sur ce point. C'est ce contrôle, et c'est aussi l'exemple : on ne
# comprend pas pourquoi les trois nombres diffèrent tant qu'on n'a pas vu une
# trajectoire qui touche la cible **après** avoir pris le stop.

#: Sous-pas par minute de la simulation. Déclaré, parce qu'il décide de tout :
#: une barrière surveillée à pas fini est franchie moins souvent qu'une
#: barrière continue, et l'écart vaut `β₁·σ√Δt`.
SOUS_PAS = 12

N_SESSIONS = 1500

#: La géométrie de contrôle. Son stop est assez large pour qu'une grille au
#: douzième de minute le résolve, ce qui n'est pas le cas de la géométrie
#: déclarée — et c'est le fait de la section.
STOP_CONTROLE = 6.0
CIBLE_CONTROLE = 24.0


@dataclass(frozen=True)
class Issues:
    """Le décompte des quatre issues d'une séance, et les deux fréquences."""

    #: La cible avant le stop : le trade gagne.
    avant: float
    #: Le stop d'abord, **puis** la cible : le trade perd, et le graphique
    #: montre pourtant que « le prix y est allé ».
    apres: float
    #: Le stop, et la cible jamais atteinte.
    jamais: float
    #: Ni l'une ni l'autre barrière avant la clôture.
    ni: float
    #: La cible touchée à un moment quelconque, et la clôture au-delà.
    touche: float
    cloture: float


def decalage_continuite(sous_pas: int = SOUS_PAS,
                        sigma: float = q.SIGMA_1MIN) -> float:
    """`β₁·σ√Δt` — de combien une barrière surveillée à pas fini s'éloigne.

    La constante est celle de la partie XVI, et elle n'est pas recopiée : le
    module l'importe. Une barrière discrète se comporte comme une barrière
    continue **plus loin**, et les deux barrières s'éloignent ensemble.
    """
    return BETA_CONTINUITE * sigma * math.sqrt(1.0 / sous_pas)


def p_avant_stop_discret(stop_pts: float, cible_pts: float,
                         sous_pas: int = SOUS_PAS) -> float:
    """La forme fermée corrigée du pas d'observation."""
    d = decalage_continuite(sous_pas)
    return (stop_pts + d) / (stop_pts + cible_pts + 2.0 * d)


@lru_cache(maxsize=8)
def simuler_issues(stop_pts: float, cible_pts: float, n: int = N_SESSIONS,
                   sous_pas: int = SOUS_PAS, seed: int = SEED) -> Issues:
    """Le décompte mesuré sur `n` séances sans dérive.

    Rien n'y est approché : chaque séance est parcourue au sous-pas déclaré,
    et les quatre issues sont exclusives. La quantité intéressante est la
    deuxième — le stop d'abord, la cible ensuite — parce qu'elle est
    exactement ce qui sépare la probabilité qui décide de celle que l'œil
    retient.
    """
    rng = Rng(seed)
    pas = int(q.SESSION_MIN * sous_pas)
    sd = q.SIGMA_1MIN / math.sqrt(sous_pas)
    avant = apres = jamais = ni = touche = clot = 0
    for _ in range(n):
        x = mx = 0.0
        au_stop = a_la_cible = cible_avant = False
        for _ in range(pas):
            x += sd * rng.gauss()
            if x > mx:
                mx = x
            if not au_stop and not a_la_cible:
                if x <= -stop_pts:
                    au_stop = True
                elif x >= cible_pts:
                    a_la_cible = cible_avant = True
            elif au_stop and not a_la_cible and x >= cible_pts:
                a_la_cible = True
        if mx >= cible_pts:
            touche += 1
        if x >= cible_pts:
            clot += 1
        if cible_avant:
            avant += 1
        elif au_stop and a_la_cible:
            apres += 1
        elif au_stop:
            jamais += 1
        else:
            ni += 1
    return Issues(avant / n, apres / n, jamais / n, ni / n, touche / n,
                  clot / n)


#: Les deux géométries de la table de contrôle. La première est déclarée par
#: le document, la seconde est celle qu'une grille résout.
CONTROLES: tuple[tuple[str, float, float], ...] = (
    ("Géométrie déclarée", q.STOP_PTS, q.RR_REF * q.STOP_PTS),
    ("Géométrie de contrôle", STOP_CONTROLE, CIBLE_CONTROLE),
)


def table_verification() -> Table:
    d = decalage_continuite()
    rows = []
    for nom, st, ci in CONTROLES:
        m = simuler_issues(st, ci)
        for quoi, mesure, ferme in (
                ("Touchée avant le stop", m.avant,
                 p_avant_stop_discret(st, ci)),
                ("Touchée à un moment", m.touche, p_touche(ci)),
                ("Clôture au-delà", m.cloture, p_cloture(ci))):
            rows.append([
                nom,
                quoi,
                num(100 * mesure, 2),
                num(100 * ferme, 2),
                num(100 * (mesure - ferme), 2, signed=True),
                num(100 * d / st, 0),
            ])
    return Table(
        key="gr_verification",
        caption="Les trois formes fermées, mesurées sur des séances simulées",
        headers=["Géométrie", "Quantité", "Mesurée (%)",
                 "Forme fermée corrigée (%)", "Écart (points)",
                 "Décalage de continuité, en % du stop"],
        rows=rows,
        note=num(N_SESSIONS, 0) + " séances sans dérive par géométrie, "
             "parcourues au " + num(SOUS_PAS, 0) + "ᵉ de minute. La forme "
             "fermée est corrigée du **pas d'observation** : une barrière "
             "surveillée à pas fini se comporte comme une barrière continue "
             "plus lointaine de `β₁·σ√Δt`, et la constante est celle de la "
             "partie XVI, importée et non recopiée. La dernière colonne est "
             "le fait de la table, et il est gênant pour la géométrie du "
             "document : **le stop déclaré est si étroit que la correction "
             "vaut " + num(100 * d / q.STOP_PTS, 0) + " % de sa largeur.** "
             "Aucune grille raisonnable ne résout une barrière à six dixièmes "
             "de point ; les deux quantités lointaines, elles, sont "
             "confirmées sans correction sensible. La seconde géométrie "
             "existe pour cela : son stop est assez large pour être résolu, "
             "et les trois formes fermées y tombent sur la mesure. *Une forme "
             "fermée ne se publie pas sans ce contrôle, et le premier jet de "
             "cette partie l'avait omis.*",
    )


def table_issues() -> Table:
    a = q.STOP_PTS
    b = q.RR_REF * a
    m = simuler_issues(a, b)
    lignes = (
        ("La cible avant le stop", m.avant,
         "le trade gagne, et le graphique est d'accord"),
        ("Le stop, puis la cible", m.apres,
         "le trade perd, et le graphique montre que le prix y est allé"),
        ("Le stop, la cible jamais", m.jamais,
         "le trade perd, et le graphique est d'accord"),
        ("Ni l'une ni l'autre", m.ni,
         "sortie à la clôture, sans barrière touchée"),
    )
    rows = []
    for nom, f, lecture in lignes:
        rows.append([nom, num(100 * f, 1), lecture])
    return Table(
        key="gr_issues",
        caption="Les quatre issues d'une séance, et celle qui explique tout",
        headers=["Issue", "Fréquence (%)", "Ce qu'un graphique en montre"],
        rows=rows,
        note="Les quatre issues sont exclusives et couvrent tout. La deuxième "
             "est celle qui explique la partie, et elle vaut "
             + num(100 * m.apres, 1) + " % des séances&nbsp;: **le prix "
             "atteint la cible après avoir pris le stop.** Un graphique "
             "relu après coup montre alors une belle course jusqu'à la "
             "cible ; le compte en banque montre une perte. La somme des deux "
             "premières lignes est la probabilité que l'œil retient, "
             + num(100 * (m.avant + m.apres), 1) + " %, et la première seule "
             "est celle qui décide, " + num(100 * m.avant, 2) + " %. *Tout "
             "l'écart de la section est dans la deuxième ligne*, et c'est "
             "elle que la planche montre sur des trajectoires.",
        wrap_cols=[2],
    )


N_TEMOINS = 400

#: Minutes du zoom. Le stop déclaré se résout en quelques minutes, la cible en
#: quelques heures : les deux événements ne vivent pas à la même échelle, et
#: c'est pour cela que la planche en porte deux.
MINUTES_ZOOM = 8


@lru_cache(maxsize=4)
def trajectoires_temoins(stop_pts: float = q.STOP_PTS,
                         cible_pts: float = q.RR_REF * q.STOP_PTS,
                         n: int = N_TEMOINS, sous_pas: int = SOUS_PAS,
                         seed: int = SEED + 5
                         ) -> tuple[tuple[str, tuple[float, ...],
                                          tuple[float, ...]], ...]:
    """Une trajectoire par issue, choisie par une **règle calculée**.

    On garde la première séance qui réalise chaque issue, dans l'ordre où
    elles se présentent, et rien n'est choisi à la main — c'est la règle de
    `setups._seance_temoin`, et elle existe pour que la planche ne puisse pas
    montrer autre chose que ce que la table mesure.

    Chaque trajectoire est rendue deux fois : au sous-pas sur les premières
    minutes, et à la minute sur la séance entière. Ce n'est pas un confort de
    tracé — le stop déclaré se résout en quelques minutes, et une trajectoire
    à la minute ne le montrerait pas être franchi.
    """
    rng = Rng(seed)
    pas = int(q.SESSION_MIN * sous_pas)
    pas_zoom = int(MINUTES_ZOOM * sous_pas)
    sd = q.SIGMA_1MIN / math.sqrt(sous_pas)
    trouve: dict[str, tuple[tuple[float, ...], tuple[float, ...]]] = {}
    for _ in range(n):
        x = 0.0
        zoom = [0.0]
        minute = [0.0]
        au_stop = a_la_cible = cible_avant = False
        for i in range(pas):
            x += sd * rng.gauss()
            if not au_stop and not a_la_cible:
                if x <= -stop_pts:
                    au_stop = True
                elif x >= cible_pts:
                    a_la_cible = cible_avant = True
            elif au_stop and not a_la_cible and x >= cible_pts:
                a_la_cible = True
            if i < pas_zoom:
                zoom.append(x)
            if (i + 1) % sous_pas == 0:
                minute.append(x)
        if cible_avant:
            cle = "avant"
        elif au_stop and a_la_cible:
            cle = "apres"
        elif au_stop:
            cle = "jamais"
        else:
            cle = "ni"
        trouve.setdefault(cle, (tuple(zoom), tuple(minute)))
        if len(trouve) == 4:
            break
    ordre = ("avant", "apres", "jamais", "ni")
    return tuple((c, trouve[c][0], trouve[c][1]) for c in ordre
                 if c in trouve)


def minute_de_la_cible(chemin: tuple[float, ...],
                       cible_pts: float = q.RR_REF * q.STOP_PTS) -> int:
    """La **première** minute où la trajectoire atteint la cible.

    Elle n'est pas la minute du maximum, et le premier jet de la planche
    avait publié la seconde en croyant publier la première — un nombre faux
    dans une annotation, c'est-à-dire exactement le défaut que ce document
    reproche aux autres.
    """
    for i, x in enumerate(chemin):
        if x >= cible_pts:
            return i
    return -1


#: Le libellé de chaque issue, pour les légendes.
LIBELLES: dict[str, str] = {
    "avant": "la cible avant le stop",
    "apres": "le stop, puis la cible",
    "jamais": "le stop, la cible jamais",
    "ni": "ni l'une ni l'autre",
}


SURF_STOP_PTS: tuple[float, ...] = (0.3, 0.6, 1.2, 2.5, 5.0, 10.0)
SURF_RR: tuple[float, ...] = (80.0, 40.0, 20.0, 10.0, 5.0, 2.0)


def rapport_de_confusion(stop_pts: float, rr: float) -> float:
    """`2Φ(−b/σ√T)·(a+b)/a` — le rapport des deux premières probabilités.

    Le dénominateur est pris en **forme fermée**, et pas par simulation : au
    coin des cibles lointaines la probabilité bornée s'annule par
    soupassement, si bien que le rapport mesuré y serait zéro sur zéro. La
    forme fermée est celle du problème non borné, elle ne s'annule jamais, et
    c'est elle qui porte la structure que la surface montre.
    """
    b = rr * stop_pts
    return p_touche(b) / p_avant_stop_ferme(stop_pts, b)


def cout_de_confusion(stop_pts: float, rr: float) -> float:
    """L'écart d'espérance, en R, entre la croyance et la vérité.

    `E[R]` est linéaire en `p`, donc l'écart vaut simplement
    `(p_touche − a/(a+b))·(1 + R:R)`. Il ne dépend pas de la friction, ce qui
    est le point : **la confusion coûte la même chose à un opérateur qui paie
    cher et à un qui ne paie rien.**
    """
    b_pts = rr * stop_pts
    return (p_touche(b_pts) - p_avant_stop_ferme(stop_pts, b_pts)) * (1.0 + rr)


def surface_cout() -> list[list[float]]:
    """L'écart d'espérance en R, sur (stop, R:R).

    C'est la grandeur de la partie, et elle a la forme d'un produit : l'écart
    de probabilité multiplié par ce que chaque décision paie. Le sommet est au
    fond, au coin du stop le plus étroit et de la cible la plus ambitieuse.
    """
    return [[cout_de_confusion(a, rr) for rr in SURF_RR]
            for a in SURF_STOP_PTS]


def surface_confusion() -> list[list[float]]:
    """Le rapport de la deuxième probabilité à la première, sur (stop, R:R).

    Les deux axes vont dans le même sens : un stop étroit et une cible
    ambitieuse creusent tous deux l'écart, parce qu'ils éloignent la cible du
    stop sans l'éloigner de la portée du prix. Le sommet est au fond.
    """
    return [[rapport_de_confusion(a, rr) for rr in SURF_RR]
            for a in SURF_STOP_PTS]


# ---------------------------------------------------------------------------
# II. Un delta en a trois aussi
# ---------------------------------------------------------------------------

#: Le niveau, le strike et la volatilité de référence des exemples d'options.
S_REF = 100.0
VOL_REF = 0.25


def _d(s: float, k: float, vol: float, t: float, r: float,
       div: float) -> tuple[float, float]:
    a = ((math.log(s / k) + (r - div + 0.5 * vol * vol) * t)
         / (vol * math.sqrt(t)))
    return a, a - vol * math.sqrt(t)


def delta_comptant(s: float, k: float, vol: float, t: float, r: float = 0.0,
                   div: float = 0.0) -> float:
    """`Δ = e^{−qT}N(d₁)` — le delta qui couvre, et le seul qui couvre."""
    return math.exp(-div * t) * norm_cdf(_d(s, k, vol, t, r, div)[0])


def proba_terminale(s: float, k: float, vol: float, t: float, r: float = 0.0,
                    div: float = 0.0) -> float:
    """`N(d₂)` — la probabilité risque-neutre de finir dans la monnaie."""
    return norm_cdf(_d(s, k, vol, t, r, div)[1])


def dual_delta(s: float, k: float, vol: float, t: float, r: float = 0.0,
               div: float = 0.0) -> float:
    """`−∂V/∂K = e^{−rT}N(d₂)` — la sensibilité au strike.

    C'est de cette grandeur, dérivée une seconde fois, qu'on tire la densité
    risque-neutre. Elle ne couvre rien et ne prétend rien couvrir.
    """
    return math.exp(-r * t) * norm_cdf(_d(s, k, vol, t, r, div)[1])


def dual_delta_numerique(s: float, k: float, vol: float, t: float,
                         r: float = 0.0, div: float = 0.0) -> float:
    """La même chose par différence finie sur le strike, pour la contrôler."""
    h = 1e-5 * k
    return -(nv.call(s, k + h, vol, t) - nv.call(s, k - h, vol, t)) / (2.0 * h)


def ecart_delta_proba(s: float, k: float, vol: float, t: float, r: float = 0.0,
                      div: float = 0.0) -> float:
    """`Δ − N(d₂)` — l'écart que le raccourci populaire efface."""
    return (delta_comptant(s, k, vol, t, r, div)
            - proba_terminale(s, k, vol, t, r, div))


#: Volatilités et échéances balayées pour l'écart.
VOLS: tuple[float, ...] = (0.10, 0.25, 0.40, 0.60, 0.80)
ECHEANCES_MOIS: tuple[float, ...] = (0.25, 1.0, 3.0, 6.0, 12.0)

#: Taux de la table des trois deltas. Il est **non nul** exprès : à taux nul
#: le dual delta et `N(d₂)` coïncident, et la colonne ne dirait rien.
TAUX_TABLE = 0.02


def table_deltas() -> Table:
    rows = []
    r = TAUX_TABLE
    for vol in VOLS:
        for mois in (1.0, 6.0):
            t = mois / 12.0
            d = delta_comptant(S_REF, S_REF, vol, t, r)
            n2 = proba_terminale(S_REF, S_REF, vol, t, r)
            rows.append([
                num(100 * vol, 0),
                num(mois, 0),
                num(d, 4),
                num(n2, 4),
                num(dual_delta(S_REF, S_REF, vol, t, r), 4),
                num(100 * (d - n2), 2),
            ])
    gros = ecart_delta_proba(S_REF, S_REF, 0.80, 0.5, TAUX_TABLE)
    return Table(
        key="gr_deltas",
        caption="Trois grandeurs qu'un seul mot désigne, à la monnaie et à "
                + num(100 * TAUX_TABLE, 0) + " % de taux",
        headers=["Volatilité (%)", "Échéance (mois)", "Delta comptant",
                 "N(d₂)", "Dual delta", "Écart en points de delta"],
        rows=rows,
        note="Le delta comptant couvre&nbsp;: c'est la vraie dérivée, et la "
             "seule des trois qui neutralise une position. `N(d₂)` est la "
             "probabilité risque-neutre de finir dans la monnaie. Le dual "
             "delta est la sensibilité au strike, et c'est de lui qu'on tire "
             "une densité. Le raccourci « le delta est la probabilité de "
             "finir dans la monnaie » confond les deux premiers. Ils sont "
             "proches à échéance courte et près de la monnaie, ce qui "
             "explique la survie du raccourci&nbsp;; **ils se séparent "
             "exactement là où l'on s'appuie le plus dessus**, aux longues "
             "échéances et aux fortes volatilités. Le document extérieur "
             "annonce « plus de quinze points » à quatre-vingts pour cent de "
             "volatilité et six mois&nbsp;; le recalcul en donne "
             + num(100 * gros, 1) + ", et son annonce était donc prudente. "
             "La coupure est celle de la partie précédente, à l'identique&nbsp;: "
             "`N(d₁)` pondère par le chemin, `N(d₂)` ne regarde que le "
             "terme. Le taux de la table est non nul à dessein&nbsp;: à taux "
             "nul le dual delta et `N(d₂)` coïncident exactement, et la "
             "cinquième colonne ne dirait rien.",
    )


SURF_VOL: tuple[float, ...] = (0.90, 0.65, 0.45, 0.30, 0.18, 0.10)
SURF_MOIS: tuple[float, ...] = (24.0, 12.0, 6.0, 3.0, 1.0, 0.25)


def surface_gap() -> list[list[float]]:
    """`Δ − N(d₂)` à la monnaie, sur (volatilité, échéance).

    Les deux axes n'entrent que par le produit `σ√T`, comme la bande de gamma
    de la partie précédente — et pour la même raison, puisque l'écart vaut
    `N(d₁) − N(d₁ − σ√T)`. Le sommet est au fond.
    """
    return [[100.0 * ecart_delta_proba(S_REF, S_REF, v, m / 12.0)
             for m in SURF_MOIS]
            for v in SURF_VOL]


# ---------------------------------------------------------------------------
# III. Ce qui bouge pendant qu'on ne fait rien
# ---------------------------------------------------------------------------


def charm(s: float, k: float, vol: float, t: float, r: float = 0.0,
          div: float = 0.0) -> float:
    """`∂Δ/∂t` — la dérive du delta à prix immobile, par an.

    Le temps calendaire s'écoule dans le sens inverse de l'échéance, d'où le
    signe. La forme fermée est contrôlée contre une différence finie sur
    `delta_comptant`, et l'accord est à six décimales.
    """
    a, b = _d(s, k, vol, t, r, div)
    return (div * math.exp(-div * t) * norm_cdf(a)
            - math.exp(-div * t) * _phi(a)
            * (2.0 * (r - div) * t - b * vol * math.sqrt(t))
            / (2.0 * t * vol * math.sqrt(t)))


def bleed_par_jour(s: float, k: float, vol: float, t: float) -> float:
    """Le charm rapporté à la journée, la seule unité qu'un opérateur lise."""
    return charm(s, k, vol, t) / nv.JOURS_AN


def d1_du_pic(vol: float, t: float) -> float:
    """Le `d₁` où le bleed est maximal : racine de `u² − uv − 1 = 0`.

    À taux et dividende nuls, `∂Δ/∂t = φ(d₁)·d₂/2T` avec `d₂ = d₁ − σ√T`.
    Annuler la dérivée en `d₁` donne `−u(u−v) + 1 = 0`, soit

        `u* = (σ√T ± √(σ²T + 4))/2`.

    C'est une forme fermée, donc elle est contrôlée contre un balayage
    numérique — la règle du dépôt, et celle qui avait attrapé la constante
    fausse du pic de hasard de la partie XVI.
    """
    v = vol * math.sqrt(t)
    return 0.5 * (v - math.sqrt(v * v + 4.0))


def moneyness_du_pic(vol: float, t: float) -> float:
    """Le rapport `S/K` où le bleed est maximal, déduit de `d₁*`."""
    v = vol * math.sqrt(t)
    return math.exp(d1_du_pic(vol, t) * v - 0.5 * v * v)


def bleed_du_pic(vol: float, t: float) -> float:
    """L'amplitude du bleed en son maximum, en delta par jour."""
    return abs(bleed_par_jour(S_REF * moneyness_du_pic(vol, t), S_REF, vol, t))


#: Échéances balayées pour le charm, en jours.
JOURS: tuple[float, ...] = (60.0, 30.0, 14.0, 7.0, 3.0, 1.0)


def table_charm() -> Table:
    rows = []
    for j in JOURS:
        t = j / nv.JOURS_AN
        m = moneyness_du_pic(VOL_REF, t)
        rows.append([
            num(j, 0),
            num(1000 * abs(bleed_par_jour(S_REF, S_REF, VOL_REF, t)), 2),
            num(m, 4),
            num(100 * (1.0 - m), 2),
            num(1000 * bleed_du_pic(VOL_REF, t), 1),
            num(bleed_du_pic(VOL_REF, t)
                / max(abs(bleed_par_jour(S_REF, S_REF, VOL_REF, t)), 1e-12), 0),
        ])
    return Table(
        key="gr_charm",
        caption="Ce que le temps seul fait au delta, et où il le fait",
        headers=["Jours à l'échéance", "Bleed à la monnaie (millièmes/jour)",
                 "Moneyness du maximum", "Distance au strike (%)",
                 "Bleed au maximum (millièmes/jour)", "Rapport des deux"],
        rows=rows,
        note="Le charm est la seule dérivée qui déplace une position **sans "
             "qu'il se passe quoi que ce soit sur le marché**, et c'est à ce "
             "titre qu'il appartient à ce document&nbsp;: comme le temps de "
             "marché de la partie X, il agit pendant qu'on ne fait rien. Le "
             "document extérieur écrit qu'il « domine dans les derniers "
             "jours ». La mesure raffine, et l'écart vaut d'être publié&nbsp;: "
             "**à la monnaie il est quasi nul** — la deuxième colonne — parce "
             "que le delta d'une option à la monnaie reste à un demi quoi "
             "qu'il arrive. Le maximum vit hors de la monnaie, et il se "
             "rapproche du strike à mesure que l'échéance approche&nbsp;: de "
             + num(100 * (1.0 - moneyness_du_pic(VOL_REF, JOURS[0]
                                                 / nv.JOURS_AN)), 1)
             + " % du strike à " + num(JOURS[0], 0) + " jours à "
             + num(100 * (1.0 - moneyness_du_pic(VOL_REF, JOURS[-1]
                                                 / nv.JOURS_AN)), 1)
             + " % à un jour. Le lieu de ce maximum a une forme fermée, "
             "`d₁* = (σ√T ± √(σ²T+4))/2`, contrôlée ici contre un balayage. "
             "*Le bleed ne domine pas les derniers jours&nbsp;: il domine une "
             "bande qui se referme sur le strike, et il est exactement nul "
             "au strike.*",
    )


SURF_JOURS: tuple[float, ...] = (180.0, 60.0, 21.0, 7.0, 3.0, 1.0)
SURF_VOL_CHARM: tuple[float, ...] = (0.90, 0.65, 0.45, 0.30, 0.18, 0.10)


def surface_lieu() -> list[list[float]]:
    """La distance au strike du bleed maximal, en pour-cent, sur (échéance, volatilité).

    Le premier essai de cette surface portait l'**amplitude** du bleed, et la
    mesure l'a écarté : sur cette boîte, l'échéance déplace l'amplitude d'un
    facteur cent cinquante quand la volatilité ne la déplace que d'un facteur
    un et demi. Un relief des deux n'aurait donc montré qu'une rampe le long
    d'un seul axe. La raison se lit dans la forme fermée — au pic, `d₁*` tend
    vers `−1` quand `σ√T` tend vers zéro, donc l'amplitude tend vers
    `φ(1)/(2T)`, qui **ne dépend que de l'échéance**.

    Ce qui dépend des deux, c'est le *lieu* : la bande où le bleed agit se
    referme sur le strike comme `σ√T`. Le sommet est au fond.
    """
    return [[100.0 * (1.0 - moneyness_du_pic(v, j / nv.JOURS_AN))
             for v in SURF_VOL_CHARM]
            for j in SURF_JOURS]


def amplitude_asymptotique(t: float) -> float:
    """`φ(1)/(2T)` par jour — la limite de l'amplitude au pic à faible `σ√T`.

    Contrôlée contre `bleed_du_pic`, dont elle doit s'approcher quand la
    volatilité tend vers zéro. C'est ce contrôle qui a montré que l'axe de
    volatilité du premier relief était mort.
    """
    return _phi(1.0) / (2.0 * t) / nv.JOURS_AN


# ---------------------------------------------------------------------------
# IV. Le résumé qui cache
# ---------------------------------------------------------------------------

#: Les deux livres opposés, à delta net nul l'un comme l'autre.
JOURS_LIVRE = 30.0
VOL_LIVRE = 0.25


def straddle(s: float, k: float, vol: float, t: float) -> float:
    """Valeur d'un straddle, par parité call-put à taux nul : `2C − S + K`."""
    return 2.0 * nv.call(s, k, vol, t) - s + k


def delta_straddle(s: float, k: float, vol: float, t: float) -> float:
    """`2N(d₁) − 1` — le delta d'un straddle, qui n'est **pas** nul au strike.

    C'est le détail qui a fait échouer la première version de cette section.
    Le delta d'un straddle s'annule en `d₁ = 0`, c'est-à-dire un peu
    *au-dessous* du strike, si bien qu'au strike il vaut encore quelques
    centièmes. Une planche qui aurait annoncé « delta net nul » en posant le
    prix au strike aurait donc écrit un zéro faux — et le premier jet l'avait
    écrit à la main plutôt que de le calculer.
    """
    return 2.0 * delta_comptant(s, k, vol, t) - 1.0


def pl_livre(sens: str, mouvement: float) -> float:
    """Le P/L d'un des deux livres après un mouvement, en fraction du comptant.

    Les deux livres sont **couverts en delta à l'ouverture** : on retranche le
    delta initial multiplié par le mouvement. Après cette couverture le delta
    net est nul par construction, et ce qui reste est de la pure convexité —
    ce qui est tout l'objet de la section.
    """
    t = JOURS_LIVRE / nv.JOURS_AN
    s1 = S_REF * (1.0 + mouvement)
    v0 = straddle(S_REF, S_REF, VOL_LIVRE, t)
    v1 = straddle(s1, S_REF, VOL_LIVRE, t)
    couverture = delta_straddle(S_REF, S_REF, VOL_LIVRE, t) * (s1 - S_REF)
    brut = (v1 - v0 - couverture) / S_REF
    return brut if sens == "long" else -brut


def delta_net_couvert() -> float:
    """Le delta net des deux livres après couverture. Il est nul, et calculé."""
    t = JOURS_LIVRE / nv.JOURS_AN
    return (delta_straddle(S_REF, S_REF, VOL_LIVRE, t)
            - delta_straddle(S_REF, S_REF, VOL_LIVRE, t))


#: Mouvements balayés, en fraction du comptant.
MOUVEMENTS: tuple[float, ...] = (0.005, 0.010, 0.020, 0.035, 0.050)


def table_livre() -> Table:
    rows = []
    for m in MOUVEMENTS:
        lo = pl_livre("long", m)
        ct = pl_livre("court", m)
        rows.append([
            num(100 * m, 1),
            num(delta_net_couvert(), 2, signed=True),
            num(100 * lo, 3, signed=True),
            num(100 * ct, 3, signed=True),
            num(100 * (lo - ct), 3),
        ])
    m2 = 0.020
    return Table(
        key="gr_livre",
        caption="Deux livres de delta net identique, et un mouvement de deux pour cent",
        headers=["Mouvement (%)", "Delta net des deux livres",
                 "P/L du livre long (%)", "P/L du livre court (%)",
                 "Écart entre les deux (%)"],
        rows=rows,
        note="Les deux livres sont **couverts en delta à l'ouverture**, si "
             "bien que leur delta net est nul par construction — et la "
             "deuxième colonne le recalcule au lieu de l'écrire, parce que "
             "le delta d'un straddle ne s'annule pas au strike mais un peu "
             "au-dessous, et que le premier jet de cette table avait posé un "
             "zéro faux. Ils restent à delta nul tant que le prix ne bouge "
             "pas. Un résumé de risque qui "
             "ne publie que le delta net les décrit donc de façon "
             "identique&nbsp;: c'est l'additivité qui rend le delta commode, "
             "et c'est elle qui le rend dangereux comme statistique de "
             "synthèse. Sur un mouvement de " + num(100 * m2, 0) + " %, "
             "l'écart entre les deux vaut " + num(100 * (pl_livre("long", m2)
                                                         - pl_livre("court", m2)), 2)
             + " % du notionnel, et il croît comme le carré du mouvement. "
             "**Le delta ne dit rien de la façon dont il va lui-même "
             "changer**, et c'est exactement la même faute que celle des "
             "parties précédentes&nbsp;: publier un premier moment en croyant "
             "décrire une distribution. Le Calmar de la partie XVIII cachait "
             "sa bande&nbsp;; le delta net cache sa courbure.",
    )


# ---------------------------------------------------------------------------
# V. La convention qu'on n'attache pas
# ---------------------------------------------------------------------------

#: Régimes balayés : un taux, un dividende, une échéance. Les trois ne
#: pèsent pas sur les mêmes écarts, et c'est ce que la table montre.
REGIMES: tuple[tuple[str, float, float, float], ...] = (
    ("Indice, un mois", 0.02, 0.015, 1.0),
    ("Indice, six mois", 0.02, 0.015, 6.0),
    ("Indice, deux ans", 0.02, 0.015, 24.0),
    ("Portage fort, six mois", 0.12, 0.000, 6.0),
    ("Dividende fort, six mois", 0.02, 0.060, 6.0),
)


def delta_forward(s: float, k: float, vol: float, t: float, r: float = 0.0,
                  div: float = 0.0) -> float:
    """`N(d₁)` — le delta forward, sans l'escompte de dividende."""
    return norm_cdf(_d(s, k, vol, t, r, div)[0])


def delta_ajuste_prime(s: float, k: float, vol: float, t: float,
                       r: float = 0.0, div: float = 0.0) -> float:
    """Le delta ajusté de la prime : `Δ − V/S`.

    Quand la prime se règle dans la devise du sous-jacent, la détenir *est*
    une position dans le sous-jacent, et il faut la retrancher.
    """
    v = nv.call(s, k, vol, t)
    return delta_comptant(s, k, vol, t, r, div) - v / s


def ajustement_de_prime(vol: float, mois: float) -> float:
    """`V/S` — l'ajustement, en points de delta. Il ne dépend que de `σ√T`."""
    t = mois / 12.0
    return 100.0 * nv.call(S_REF, S_REF, vol, t) / S_REF


def table_convention() -> Table:
    rows = []
    for nom, r, div, mois in REGIMES:
        t = mois / 12.0
        dc = delta_comptant(S_REF, S_REF, VOL_REF, t, r, div)
        df = delta_forward(S_REF, S_REF, VOL_REF, t, r, div)
        da = delta_ajuste_prime(S_REF, S_REF, VOL_REF, t, r, div)
        rows.append([
            nom,
            num(dc, 4),
            num(df, 4),
            num(da, 4),
            num(100 * abs(dc - df), 2),
            num(100 * (dc - da), 2),
            num(100 * (max(dc, df, da) - min(dc, df, da)), 2),
        ])
    return Table(
        key="gr_convention",
        caption="Trois conventions pour un mot, et deux mécanismes de tailles très différentes",
        headers=["Régime", "Delta comptant", "Delta forward",
                 "Ajusté de la prime", "Écart comptant/forward",
                 "Ajustement de prime", "Étendue totale"],
        rows=rows,
        note="Les trois conventions sont correctes&nbsp;; elles répondent à "
             "trois questions différentes. Ce que la table sépare, et qu'on "
             "ne sépare jamais, ce sont les **deux mécanismes** qui les "
             "écartent, parce qu'ils n'ont pas le même ordre de grandeur. "
             "L'écart entre comptant et forward ne vient que du dividende, il "
             "s'annule quand celui-ci s'annule, et il reste sous "
             + num(100 * max(abs(delta_comptant(S_REF, S_REF, VOL_REF,
                                                m / 12.0, r, d)
                                 - delta_forward(S_REF, S_REF, VOL_REF,
                                                 m / 12.0, r, d))
                             for _, r, d, m in REGIMES), 1)
             + " point de delta sur toute la table. L'ajustement de prime, "
             "lui, ne dépend ni du taux ni du dividende&nbsp;: **il ne dépend "
             "que de `σ√T`**, exactement comme l'écart `Δ − N(d₂)` de la "
             "section précédente et comme la largeur de la bande de gamma de "
             "la partie XIX. Il vaut ici jusqu'à "
             + num(max(ajustement_de_prime(VOL_REF, m)
                       for _, _, _, m in REGIMES), 1)
             + " points, soit un ordre de grandeur de plus. **Et il vaut "
             "exactement l'écart `Δ − N(d₂)` de la section précédente** : à "
             "la monnaie et à portage nul, `C = S·(N(d₁) − N(d₂))`, donc "
             "`V/S = Δ − N(d₂)`. Les deux confusions de cette partie sont un "
             "seul nombre portant deux noms, et l'identité tombe dès qu'on "
             "s'écarte de la monnaie. *La première "
             "version de cette table balayait le portage et rendait une "
             "colonne constante&nbsp;; c'est la mesure qui a imposé la "
             "décomposition.* La règle d'hygiène est celle du document "
             "extérieur&nbsp;: citer un delta avec sa convention attachée.",
        wrap_cols=[0],
    )


def identite_prime_gap(vol: float, mois: float) -> tuple[float, float]:
    """L'ajustement de prime et l'écart `Δ − N(d₂)`, qui sont le même nombre.

    À la monnaie et à portage nul, `C = S·N(d₁) − K·N(d₂)` avec `K = S`, donc

        `V/S = N(d₁) − N(d₂) = Δ − N(d₂)`.

    **La quantité qu'on retranche pour changer de convention est exactement
    celle dont le delta dépasse la probabilité terminale.** Les deux
    confusions de cette partie, qui n'ont l'air de rien avoir en commun, sont
    un seul nombre portant deux noms. L'identité est *conditionnelle à la
    monnaie* — elle tombe dès qu'on s'en écarte — et un test l'exige dans les
    deux sens.
    """
    t = mois / 12.0
    return (ajustement_de_prime(vol, mois),
            100.0 * ecart_delta_proba(S_REF, S_REF, vol, t))


# ---------------------------------------------------------------------------
# VI. Ce qui reste
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Confusion:
    """Une grandeur qu'un seul mot désigne, et ce que la confondre coûte."""

    quoi: str
    citee: str
    decide: str
    cout: str
    #: Les deux valeurs, dans l'unité de la ligne. Elles servent à calculer
    #: l'erreur relative, seule grandeur commune aux cinq lignes.
    valeur_citee: float
    valeur_decide: float
    #: L'écart se mesure-t-il, ou faut-il des données pour le voir ?
    calculable: bool

    @property
    def opposable(self) -> bool:
        return self.calculable

    @property
    def erreur_relative(self) -> float:
        """`|citée − décide| / |décide|` — la seule échelle que les cinq partagent.

        Les cinq lignes sont dans cinq unités différentes : des R, des points
        de delta, des millièmes par jour, des pour-cent de notionnel. Aucune
        ne se compare aux autres, et une planche qui les mettrait sur un même
        axe mentirait. Ce rapport-là, lui, est sans dimension : il dit de
        quelle fraction de la grandeur qui décide la grandeur citée s'écarte.
        """
        if self.valeur_decide == 0.0:
            return math.inf
        return abs(self.valeur_citee - self.valeur_decide) / abs(
            self.valeur_decide)


def confusions() -> tuple[Confusion, ...]:
    """Les cinq confusions, avec leurs écarts relus des sections."""
    a = q.STOP_PTS
    b = q.RR_REF * a
    vraie = esperance_r(p_avant_stop(a, b))
    crue = esperance_r(p_touche(b))
    t6 = 0.5
    t1 = 1.0 / nv.JOURS_AN
    return (
        Confusion(
            "La probabilité d'une cible",
            "touchée à un moment, " + num(100 * p_touche(b), 0) + " %",
            "touchée avant le stop, " + num(100 * p_avant_stop(a, b), 2) + " %",
            num(crue - vraie, 1) + " R par décision",
            crue, vraie, True),
        Confusion(
            "Le delta d'une option",
            "N(d₂), la probabilité terminale",
            "e^{−qT}N(d₁), le seul qui couvre",
            num(100 * ecart_delta_proba(S_REF, S_REF, 0.80, t6), 1)
            + " points de delta à 80 % et six mois",
            proba_terminale(S_REF, S_REF, 0.80, t6),
            delta_comptant(S_REF, S_REF, 0.80, t6), True),
        Confusion(
            "Le delta qui bouge seul",
            "sa valeur à la monnaie, quasi nulle",
            "sa valeur au pic, hors de la monnaie",
            num(1000 * bleed_du_pic(VOL_REF, t1), 0)
            + " millièmes de delta par jour au maximum",
            abs(bleed_par_jour(S_REF, S_REF, VOL_REF, t1)),
            bleed_du_pic(VOL_REF, t1), True),
        Confusion(
            "Le delta d'un livre",
            "le delta net, nul pour les deux",
            "l'écart de leurs P/L sur deux pour cent",
            num(100 * (pl_livre("long", 0.02) - pl_livre("court", 0.02)), 2)
            + " % de notionnel sur deux pour cent",
            0.0, pl_livre("long", 0.02) - pl_livre("court", 0.02), True),
        Confusion(
            "La convention d'un delta",
            "le delta comptant, sans mention",
            "celui de la convention du pupitre",
            num(ajustement_de_prime(VOL_REF, 6.0), 1) + " points de delta "
            "d'ajustement de prime à six mois",
            delta_comptant(S_REF, S_REF, VOL_REF, 0.5),
            delta_ajuste_prime(S_REF, S_REF, VOL_REF, 0.5), True),
    )


def table_reste() -> Table:
    rows = []
    for x in confusions():
        rows.append([
            x.quoi,
            x.citee,
            x.decide,
            x.cout,
            num(100 * x.erreur_relative, 0),
            "oui" if x.opposable else "non",
        ])
    return Table(
        key="gr_reste",
        caption="Cinq fois un mot pour deux grandeurs, et ce que l'écart coûte",
        headers=["La grandeur", "Ce qu'on cite", "Ce qui décide",
                 "L'écart mesuré", "Erreur relative (%)",
                 "Opposable sans données"],
        rows=rows,
        note="Les cinq lignes ont la même forme, et c'est le résultat de la "
             "partie&nbsp;: **la grandeur qu'on cite décrit le présent, celle "
             "qui décide est une autre.** La première est du dépôt et non du "
             "document extérieur — c'est la plus coûteuse des cinq, et elle "
             "n'a rien à voir avec les options. Les quatre suivantes sont "
             "celles du document, recalculées. La dernière colonne ne porte "
             "que des oui, et c'est ce qui rend la partie utile&nbsp;: aucun "
             "de ces écarts ne demande une série de prix. L'avant-dernière "
             "colonne est la seule échelle que les cinq lignes partagent, "
             "parce qu'elle est sans dimension&nbsp;: de quelle fraction de "
             "la grandeur qui décide la grandeur citée s'écarte. Elle va de "
             + num(100 * min(x.erreur_relative for x in confusions()), 0)
             + " % à " + num(100 * max(x.erreur_relative
                                       for x in confusions()), 0) + " %, et "
             "la plus petite reste plus grande que toutes les tolérances "
             "qu'un opérateur s'accorde d'ordinaire. Ils se calculent "
             "sur une feuille, avant la première décision, et c'est "
             "exactement le moment où ils servent. *Le delta décrit le "
             "présent avec exactitude et ne prévoit rien* — la phrase est du "
             "document extérieur, et elle vaut pour les cinq lignes.",
        wrap_cols=[1, 2, 3],
    )


# ---------------------------------------------------------------------------
# Ce que le document consomme
# ---------------------------------------------------------------------------


def values() -> dict[str, str]:
    a = q.STOP_PTS
    b = q.RR_REF * a
    p1, p2, p3 = p_avant_stop(a, b), p_touche(b), p_cloture(b)
    vraie = esperance_r(p1)
    t6, t1 = 0.5, 1.0 / nv.JOURS_AN
    return {
        "g_p_avant": num(100 * p1, 2),
        "g_p_touche": num(100 * p2, 1),
        "g_p_cloture": num(100 * p3, 1),
        "g_facteur_touche": num(p2 / p1, 0),
        "g_facteur_cloture": num(p3 / p1, 1),
        "g_apres_stop": num(100 * simuler_issues(a, b).apres, 1),
        "g_jamais_stop": num(100 * simuler_issues(a, b).jamais, 1),
        "g_minute_cible": num(minute_de_la_cible(
            next(mm for c, _, mm in trajectoires_temoins() if c == "apres")),
            0),
        "g_avant_mesure": num(100 * simuler_issues(a, b).avant, 2),
        "g_touche_mesure": num(100 * simuler_issues(a, b).touche, 1),
        "g_sessions": num(N_SESSIONS, 0),
        "g_sous_pas": num(SOUS_PAS, 0),
        "g_decalage_pct": num(100 * decalage_continuite() / q.STOP_PTS, 0),
        "g_stop_pts": num(a, 1),
        "g_stop_controle": num(STOP_CONTROLE, 0),
        "g_decalage_controle": num(
            100 * decalage_continuite() / STOP_CONTROLE, 0),
        "g_cible_pts": num(b, 0),
        "g_cible_sigma": num(b / SIGMA_SEANCE, 2),
        "g_sigma_seance": num(SIGMA_SEANCE, 1),
        "g_er_vraie": num(vraie, 3, signed=True),
        "g_er_touche": num(esperance_r(p2), 2, signed=True),
        "g_er_cloture": num(esperance_r(p3), 2, signed=True),
        "g_ecart_r": num(esperance_r(p2) - vraie, 1),
        "g_equilibre": num(100 * (1.0 + FRICTION / a) / (1.0 + q.RR_REF), 2),
        "g_delta_atm": num(delta_comptant(S_REF, S_REF, VOL_REF, t6), 4),
        "g_nd2_atm": num(proba_terminale(S_REF, S_REF, VOL_REF, t6), 4),
        "g_gap_ref": num(100 * ecart_delta_proba(S_REF, S_REF, VOL_REF, t6), 1),
        "g_gap_gros": num(100 * ecart_delta_proba(S_REF, S_REF, 0.80, t6), 1),
        "g_gap_annonce": num(15.0, 0),
        "g_bleed_atm": num(1000 * abs(bleed_par_jour(S_REF, S_REF, VOL_REF,
                                                     t1)), 1),
        "g_bleed_pic": num(1000 * bleed_du_pic(VOL_REF, t1), 0),
        "g_rapport_bleed": num(bleed_du_pic(VOL_REF, t1)
                               / abs(bleed_par_jour(S_REF, S_REF, VOL_REF,
                                                    t1)), 0),
        "g_pic_60j": num(100 * (1.0 - moneyness_du_pic(VOL_REF,
                                                       60.0 / nv.JOURS_AN)), 1),
        "g_pic_1j": num(100 * (1.0 - moneyness_du_pic(VOL_REF, t1)), 1),
        "g_livre_ecart": num(100 * (pl_livre("long", 0.02)
                                    - pl_livre("court", 0.02)), 2),
        "g_livre_jours": num(JOURS_LIVRE, 0),
        "g_conv_cptfwd": num(
            100 * abs(delta_comptant(S_REF, S_REF, VOL_REF, 0.5, 0.02, 0.015)
                      - delta_forward(S_REF, S_REF, VOL_REF, 0.5, 0.02,
                                      0.015)), 2),
        "g_conv_prime": num(ajustement_de_prime(VOL_REF, 6.0), 1),
        "g_conv_prime_max": num(ajustement_de_prime(0.90, 24.0), 1),
        "g_confusions": num(len(confusions()), 0),
        "g_opposables": num(sum(1 for x in confusions() if x.opposable), 0),
        "g_vol_ref": num(100 * VOL_REF, 0),
        "g_rr": num(q.RR_REF, 0),
    }


def all_tables() -> dict[str, Table]:
    tables = [
        table_probas(), table_verification(), table_issues(), table_cout(),
        table_deltas(), table_charm(), table_livre(), table_convention(),
        table_reste(),
    ]
    return {t.key: t for t in tables}


def main() -> None:
    for t in all_tables().values():
        print(t.to_text())
        print()
    for k, v in values().items():
        print(f"{k:22s} {v}")


if __name__ == "__main__":
    main()
