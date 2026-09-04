"""La convexité en volatilité, et le sourire qu'on en tire.

Huitième document de la série d'options, consacré au volga. C'est le plus
ambitieux des huit : il ne décrit pas seulement une grandeur, il prétend
**dériver le sourire de volatilité** d'une inégalité de Jensen, sans peau
supposée et sans flux modélisé. La prétention est légitime et le dépôt la
reprend ; ce qu'il corrige est la route.

Sept affirmations sont examinées. Deux tiennent — et l'une se **renforce** —
deux se corrigent sur un nombre, et trois portent sur la même faute : *un
développement du second ordre poussé loin hors du domaine où il vaut, puis
inversé au premier ordre.*

I. La forme fermée, et les deux routes qui la contrôlent
----------------------------------------------------------
`volga = ∂²V/∂σ² = 𝒱·d₁d₂/σ`. Deux routes indépendantes la contrôlent : la
dérivée du véga en volatilité, et la différence seconde du prix. Elles
s'accordent à cinq décimales. La partie XXIV avait trouvé que `vanna` était
fausse d'un facteur `√T` parce que **rien ne la consommait donc rien ne la
contrôlait** ; ce module applique la leçon avant d'en avoir besoin.

II. « Près de la monnaie » est une bande de un demi pour cent
---------------------------------------------------------------
Le guide écrit que près de la monnaie les deux `d` sont petits et de signes
opposés, donc que le volga y est légèrement négatif. C'est exact, et
l'ensemble en question a déjà été mesuré **deux fois** dans ce document : la
partie XXII l'a publié comme la bande de courbure négative, la partie XXIV
comme la bande où le vanna désobéit à sa propre règle. Sa largeur en
logarithme vaut `σ²T` — `0,51 %` du comptant à trente jours — et aucun strike
d'une grille au pas d'un pour cent n'y tombe au-dessous de quinze jours.
*Trois guides décrivent le même intervalle sous trois noms.*

III. La droite et la crosse de hockey
----------------------------------------
« La ligne à la monnaie est proche d'une droite ; celle à trente pour cent
hors de la monnaie est une crosse de hockey. » Les deux moitiés tiennent, et
la première **se renforce** : le prix d'une option à la monnaie s'écarte de sa
corde de `0,1 %` sur toute la plage de volatilité, ce qui n'est pas « proche
d'une droite » mais une droite. La seconde s'en écarte de `34,5 %`.

IV. Le sourire par Jensen, et les trois routes qui n'en donnent pas un
------------------------------------------------------------------------
`E[V(σ)] ≈ V(σ̄) + ½·volga·Var(σ)`. Le mécanisme est juste et la figure du
guide ne le montre pas. Trois routes, trois sourires : l'inversion au premier
ordre rend **+28 points** de volatilité implicite sur un mois à trente pour
cent de la monnaie — plus du double de l'entrée — ; le développement du second
ordre correctement inversé en rend **+4**, et il **se retourne** au strike
79,5 ; l'espérance exacte sous la même loi de volatilité en rend **+9**, et
elle ne se retourne pas. *Le retournement que la planche du guide montre est
un artefact de son approximation, et sa légende dit qu'il correspond à ce
qu'on observe sur les marchés.*

V. Vingt points contre deux fois dix
---------------------------------------
« Une hausse de vingt points de volatilité coûte au vendeur à six mois bien
plus que deux fois ce que coûte une hausse de dix. » Le fait est réel et le
ténor est le mauvais : le rapport vaut **2,08** à six mois — à peine plus que
deux — et **4,18** à deux semaines. Le guide illustre son mécanisme là où il
est le plus faible, exactement comme celui du charm choisissait un strike sans
delta.

VI. Le papillon n'est pas neutre en véga
-------------------------------------------
« Les papillons sont le trade de volga pur : ailes longues, corps court, véga
quasi nul, volga grand. » La seconde moitié tient ; la première est fausse
d'un cinquième. Un papillon un-deux-un symétrique en delta est **court de
20 % du véga du corps** à vingt-cinq deltas et de **56 %** à dix. La
correction est simple, elle se calcule, et elle **améliore** le trade : en
pondérant les ailes par le rapport des végas — 1,25 à vingt-cinq deltas — le
véga net devient exactement nul *et le volga net monte de 33 à 41.*

VII. Le décompte, sur huit parties
-------------------------------------
Sur les cinquante-neuf affirmations des huit parties d'options, aucune ne
donne un sens.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from . import charm as CH
from . import grandeurs as G
from . import niveaux as nv
from . import theta as th
from . import vanna as va
from . import vega as vg
from .costs import COST_BASE, ES
from .report import Table, num

SEED = 20260920

S_REF = vg.S_REF
VOL_REF = vg.VOL_REF
TAUX = vg.TAUX
DIVIDENDE = vg.DIVIDENDE
JOURS_AN = nv.JOURS_AN

FRICTION = COST_BASE.friction_points(ES)


# ---------------------------------------------------------------------------
# I. La forme fermée, et les deux routes qui la contrôlent
# ---------------------------------------------------------------------------


def volga(s: float, k: float, vol: float, t: float, r: float = TAUX,
          div: float = DIVIDENDE) -> float:
    """`𝒱·d₁d₂/σ` — la forme fermée. Elle vit dans `vega`."""
    return vg.volga(s, k, vol, t, r, div)


def volga_par_vega(s: float, k: float, vol: float, t: float, r: float = TAUX,
                   div: float = DIVIDENDE, h: float = 1e-5) -> float:
    """Première route : la dérivée du véga en volatilité."""
    return (vg.vega(s, k, vol + h, t, r, div)
            - vg.vega(s, k, vol - h, t, r, div)) / (2.0 * h)


def volga_par_prix(s: float, k: float, vol: float, t: float, r: float = TAUX,
                   div: float = DIVIDENDE, h: float = 1e-4) -> float:
    """Seconde route : la différence seconde du prix en volatilité.

    Elle ne passe par aucune forme fermée intermédiaire, donc elle contrôle le
    véga en même temps que le volga. C'est la leçon de la partie XXIV, où une
    dérivée croisée était fausse d'un facteur `√T` parce que rien ne la
    consommait et donc rien ne la contrôlait.
    """
    return (th.call(s, k, vol + h, t, r, div)
            - 2.0 * th.call(s, k, vol, t, r, div)
            + th.call(s, k, vol - h, t, r, div)) / (h * h)


#: Échéances balayées, en jours.
ECHEANCES: tuple[float, ...] = (14.0, 30.0, 90.0, 180.0, 365.0)

#: Moneyness balayées.
MONEYNESS: tuple[float, ...] = (0.85, 0.95, 1.00, 1.05, 1.15)


def table_deux_routes() -> Table:
    rows = []
    for j in ECHEANCES:
        t = j / JOURS_AN
        for m in (0.85, 1.00, 1.15):
            s = S_REF * m
            rows.append([
                num(j, 0),
                num(m, 2),
                num(volga(s, S_REF, VOL_REF, t), 4, signed=True),
                num(volga_par_vega(s, S_REF, VOL_REF, t), 4, signed=True),
                num(volga_par_prix(s, S_REF, VOL_REF, t), 4, signed=True),
                num(volga(s, S_REF, VOL_REF, t)
                    / max(vg.vega(s, S_REF, VOL_REF, t), 1e-12), 2),
            ])
    return Table(
        key="vo_deux_routes",
        caption="Le volga par ses deux routes, et le rapport qui gouverne tout",
        headers=["Jours", "S/K", "Forme fermée", "Par la dérivée du véga",
                 "Par la différence seconde du prix", "Volga sur véga"],
        rows=rows,
        note="`volga = 𝒱·d₁d₂/σ`, et le facteur `d₁d₂` décide de tout : près "
             "de la monnaie les deux sont petits et de signes opposés, dans "
             "les deux ailes ils grandissent et partagent leur signe. La "
             "table le vérifie par deux routes indépendantes — la dérivée du "
             "véga en volatilité, et la différence seconde du prix, qui ne "
             "passe par aucune forme fermée intermédiaire et contrôle donc "
             "le véga en même temps. L'accord est à quatre décimales. *Ce "
             "contrôle-là n'est pas une formalité :* la partie XXIV a trouvé "
             "que la dérivée croisée du même module était fausse d'un facteur "
             "racine de l'échéance, parce que rien ne la consommait et donc "
             "rien ne la contrôlait. La dernière colonne est la grandeur que "
             "la suite emploie : le volga rapporté au véga vaut `d₁d₂/σ`, "
             "c'est-à-dire la courbure par unité de pente, et c'est elle qui "
             "se convertit en points de volatilité implicite.",
    )


# ---------------------------------------------------------------------------
# II. « Près de la monnaie » est une bande de un demi pour cent
# ---------------------------------------------------------------------------


def bande_negative(t: float, vol: float = VOL_REF, r: float = TAUX,
                   div: float = DIVIDENDE) -> tuple[float, float]:
    """La bande `d₂ < 0 < d₁`, où le volga est négatif.

    C'est le même ensemble que `vanna.bande_de_desobeissance` et que la bande
    de courbure de la partie XXII ; le module l'importe plutôt que de le
    récrire, et un test exige l'égalité.
    """
    return va.bande_de_desobeissance(t, vol, r, div)


def largeur_de_bande(t: float, vol: float = VOL_REF) -> float:
    """La largeur relative de cette bande — `e^{σ²T} − 1`."""
    return va.largeur_de_desobeissance(t, vol)


def decalage_de_portage(t: float, r: float = TAUX,
                        div: float = DIVIDENDE) -> float:
    """`(r − q)·T` — ce qui sépare cette bande de celle de la partie XXII.

    Les deux bandes ont **exactement** la même largeur en logarithme, `σ²T`,
    et ce n'est pas une coïncidence : elles sont bornées par les mêmes deux
    racines. Mais la partie XXII écrit la sienne en moneyness comptant, celle
    du vanna et celle-ci en moneyness à terme, et le forward dérive. Le même
    ensemble ne tombe donc pas au même endroit du tableau des strikes, et
    l'écart vaut le portage — c'est la question de la partie XXIII posée sur
    un autre objet : *quelle variable tient-on fixe ?*
    """
    return (r - div) * t


#: Pas de grille de strikes balayés, en fraction du comptant.
PAS_GRILLE: tuple[float, ...] = (0.0025, 0.0050, 0.0100, 0.0250)


def strikes_dans_la_bande(t: float, pas: float,
                          vol: float = VOL_REF) -> float:
    """Le nombre de strikes d'une grille au pas donné qui tombent dedans."""
    return vg.strikes_dans_la_bande(t, pas, vol)


def table_bande() -> Table:
    rows = []
    for j in ECHEANCES:
        t = j / JOURS_AN
        lo, hi = bande_negative(t)
        rows.append([
            num(j, 0),
            num(lo, 5),
            num(hi, 5),
            num(100 * largeur_de_bande(t), 3),
            num(math.log(hi / lo), 6),
            num(VOL_REF * VOL_REF * t, 6),
            num(strikes_dans_la_bande(t, 0.01), 2),
        ])
    return Table(
        key="vo_bande",
        caption="Le troisième nom du même intervalle",
        headers=["Jours", "Borne basse (S/K)", "Borne haute (S/K)",
                 "Largeur (%)", "Largeur en logarithme", "`σ²T`",
                 "Strikes d'une grille au pour cent"],
        rows=rows,
        note="Le guide décrit l'endroit où le volga est négatif comme « près "
             "de la monnaie », et ne le chiffre pas. Ce document l'a déjà "
             "chiffré **deux fois**, pour deux motifs qui n'avaient rien à "
             "voir. La partie XXII l'a publié comme la bande où la courbure "
             "du véga change de signe, pour dire qu'on n'y peut pas "
             "compenser une aile par une option à la monnaie. La partie XXIV "
             "l'a retrouvé comme la bande où le vanna cesse de ramener le "
             "delta vers un demi. C'est **le même ensemble** : la condition "
             "est `d₁d₂ < 0` dans les trois cas, et les deux avant-dernières "
             "colonnes le vérifient — la largeur en logarithme vaut `σ²T` à "
             "toutes les échéances.\n\nLa dernière colonne dit ce que cela "
             "vaut en pratique. Sur une grille de strikes au pas d'un pour "
             "cent, il y tombe " + num(strikes_dans_la_bande(30.0 / JOURS_AN,
                                                             0.01), 2)
             + " strike à trente jours et **aucun au-dessous de quinze**. "
             "*« Près de la monnaie » désigne un intervalle que personne ne "
             "peut négocier*, et les trois guides qui le décrivent le "
             "décrivent tous sans le mesurer.",
    )


# ---------------------------------------------------------------------------
# III. La droite et la crosse de hockey
# ---------------------------------------------------------------------------

#: La plage de volatilité que le guide balaie sur sa planche de droite.
VOL_BASSE = 0.05
VOL_HAUTE = 0.70


def ecart_a_la_corde(moneyness: float, t: float, n: int = 400) -> float:
    """L'écart maximal du prix à la corde qui joint ses deux bouts.

    C'est la mesure de « proche d'une droite » : zéro pour une droite exacte,
    et rapportée au prix du bout haut pour être sans dimension.
    """
    k = S_REF * moneyness
    vols = [VOL_BASSE + (VOL_HAUTE - VOL_BASSE) * i / n for i in range(n + 1)]
    ps = [th.call(S_REF, k, v, t, TAUX, DIVIDENDE) for v in vols]
    a, b = ps[0], ps[-1]
    ecart = max(abs(p - (a + (b - a) * i / n)) for i, p in enumerate(ps))
    return ecart / ps[-1]


#: Moneyness de la planche du guide, en écart hors de la monnaie.
ECARTS: tuple[float, ...] = (0.0, 0.05, 0.15, 0.30)


def table_courbure() -> Table:
    rows = []
    for j in (30.0, 90.0, 365.0):
        t = j / JOURS_AN
        for e in ECARTS:
            m = 1.0 + e
            rows.append([
                num(j, 0),
                num(100 * e, 0),
                num(100 * ecart_a_la_corde(m, t), 2),
                num(volga(S_REF * m, S_REF, VOL_REF, t), 2),
                num(volga(S_REF * m, S_REF, VOL_REF, t)
                    / max(vg.vega(S_REF * m, S_REF, VOL_REF, t), 1e-12), 2),
            ])
    t90 = 90.0 / JOURS_AN
    return Table(
        key="vo_courbure",
        caption="La droite et la crosse, mesurées à la corde",
        headers=["Jours", "Écart hors de la monnaie (%)",
                 "Écart maximal à la corde (% du prix)", "Volga",
                 "Volga sur véga"],
        rows=rows,
        note="Le guide écrit que la ligne à la monnaie est « proche d'une "
             "droite » et que celle à trente pour cent hors de la monnaie est "
             "« une crosse de hockey ». Les deux moitiés tiennent, et la "
             "première **se renforce** : sur toute la plage de volatilité "
             "que sa propre planche balaie, de "
             + num(100 * VOL_BASSE, 0) + " à " + num(100 * VOL_HAUTE, 0)
             + " %, le prix d'une option à la monnaie s'écarte de sa corde de "
             + num(100 * ecart_a_la_corde(1.0, t90), 2) + " % — ce n'est pas "
             "« proche d'une droite », c'est une droite. *Le prix d'une "
             "option à la monnaie est linéaire en volatilité au dixième de "
             "pour cent près, et c'est un fait plus fort que celui que le "
             "guide énonce.* Celle à trente pour cent s'en écarte de "
             + num(100 * ecart_a_la_corde(1.30, t90), 1) + " %. La dernière "
             "colonne donne la grandeur qui gouverne cet écart, et elle "
             "explique le contraste sans qu'on ait à le regarder : le volga "
             "par unité de véga passe de zéro à la monnaie à "
             + num(volga(1.30 * S_REF, S_REF, VOL_REF, t90)
                   / vg.vega(1.30 * S_REF, S_REF, VOL_REF, t90), 1)
             + " à trente pour cent.",
    )


# ---------------------------------------------------------------------------
# IV. Le sourire par Jensen, et les trois routes
# ---------------------------------------------------------------------------

#: La volatilité de la volatilité que le guide déclare, en fraction de la
#: volatilité moyenne. Elle n'est pas observable ici, et la partie XXII la
#: balayait déjà pour la même raison.
NU = 0.30

#: Le nombre de nœuds de la quadrature de Simpson, et sa demi-largeur en
#: écarts-types. La loi de la volatilité est prise normale autour de sa
#: moyenne, comme le développement du guide le suppose implicitement.
N_QUAD = 400
LARGEUR_QUAD = 5.0


def ecart_type_vol(nu: float = NU, vol: float = VOL_REF) -> float:
    """L'écart-type de la volatilité, en fraction."""
    return nu * vol


def implicite(k: float, prix: float, t: float) -> float:
    """La volatilité implicite d'un prix, par bissection."""
    lo, hi = 0.005, 5.0
    for _ in range(200):
        m = 0.5 * (lo + hi)
        if th.call(S_REF, k, m, t, TAUX, DIVIDENDE) < prix:
            lo = m
        else:
            hi = m
    return 0.5 * (lo + hi)


@lru_cache(maxsize=4096)
def prix_exact(k: float, t: float, nu: float = NU,
               vol: float = VOL_REF) -> float:
    """`E[V(σ)]` sous une loi normale de volatilité, par quadrature."""
    s = ecart_type_vol(nu, vol)
    tot = wtot = 0.0
    for i in range(N_QUAD + 1):
        z = -LARGEUR_QUAD + 2.0 * LARGEUR_QUAD * i / N_QUAD
        w = math.exp(-0.5 * z * z)
        c = 1.0 if i in (0, N_QUAD) else (4.0 if i % 2 else 2.0)
        tot += c * w * th.call(S_REF, k, max(1e-4, vol + s * z), t, TAUX,
                               DIVIDENDE)
        wtot += c * w
    return tot / wtot


def sourire_naif(k: float, t: float, nu: float = NU,
                 vol: float = VOL_REF) -> float:
    """`σ̄ + ½·Var(σ)·d₁d₂/σ̄` — l'inversion au premier ordre.

    C'est la route la plus courte : on divise la correction de prix par le
    véga, ce qui revient à supposer que le prix est linéaire en volatilité
    entre les deux points. Sur une aile, il ne l'est pas — c'est même le
    contraire que le guide vient de démontrer dans sa propre section 1.
    """
    d1, d2 = G._d(S_REF, k, vol, t, TAUX, DIVIDENDE)
    s = ecart_type_vol(nu, vol)
    return vol + 0.5 * s * s * d1 * d2 / vol


def sourire_second_ordre(k: float, t: float, nu: float = NU,
                         vol: float = VOL_REF) -> float:
    """Le développement du guide, correctement inversé."""
    s = ecart_type_vol(nu, vol)
    p = (th.call(S_REF, k, vol, t, TAUX, DIVIDENDE)
         + 0.5 * volga(S_REF, k, vol, t) * s * s)
    return implicite(k, p, t)


def sourire_exact(k: float, t: float, nu: float = NU,
                  vol: float = VOL_REF) -> float:
    """L'espérance exacte du prix sous la même loi, réinversée."""
    return implicite(k, prix_exact(k, t, nu, vol), t)


def poids_de_la_correction(k: float, t: float, nu: float = NU,
                          vol: float = VOL_REF) -> float:
    """`½·volga·Var(σ)/V` — ce que le terme de convexité pèse dans le prix.

    C'est le critère usuel de validité d'un développement du second ordre :
    il vaut tant que sa correction reste petite devant ce qu'elle corrige.
    Sur cet objet le critère **pointe à l'envers**, et c'est la mesure qui le
    dit : la correction pèse le plus là où les deux routes sont justes, et
    elle s'annule dans l'aile où elles échouent, parce que le véga s'y annule
    plus vite qu'elle. Un raccourci dont l'erreur de prix est invisible peut
    donc avoir une erreur de volatilité implicite énorme, et c'est le fait de
    la section.
    """
    v = th.call(S_REF, k, vol, t, TAUX, DIVIDENDE)
    if v <= 1e-12:
        return 0.0
    return 0.5 * volga(S_REF, k, vol, t) * ecart_type_vol(nu, vol) ** 2 / v


def pic_du_poids(t: float, nu: float = NU, vol: float = VOL_REF,
                 fenetre: tuple[float, float] = (0.72, 1.00),
                 n: int = 800) -> tuple[float, float]:
    """Le strike où la correction pèse le plus lourd, et ce qu'elle y pèse."""
    best = (0.0, -math.inf)
    for i in range(n + 1):
        k = S_REF * (fenetre[0] + (fenetre[1] - fenetre[0]) * i / n)
        v = poids_de_la_correction(k, t, nu, vol)
        if v > best[1]:
            best = (k, v)
    return best


def crete_du_volga(t: float, vol: float = VOL_REF,
                   haut: float = 1.80, n: int = 2000) -> float:
    """La moneyness où le volga culmine, du côté haut, à échéance donnée.

    Le lieu se balaie plutôt qu'il ne se résout : le volga vaut `𝒱·d₁d₂/σ`
    et annuler sa dérivée mêle la densité normale à un polynôme en `d₁`. Un
    test compare ce balayage à un pas dix fois plus fin, et exige que le
    lieu croisse avec l'échéance — c'est le fait que la planche montre.
    """
    best = (1.0, -math.inf)
    for i in range(n + 1):
        m = 1.0 + (haut - 1.0) * i / n
        v = abs(volga(S_REF * m, S_REF, vol, t))
        if v > best[1]:
            best = (m, v)
    return best[0]


#: Le plancher au-dessous duquel une correction de prix ne se distingue plus
#: du bruit d'arrondi d'un flottant double. Il est posé mille fois au-dessus
#: de l'epsilon machine, parce que le prix lui-même passe par une exponentielle
#: et une fonction d'erreur et n'est pas exact au dernier bit.
PLANCHER_INVERSION = 1e-9


def tenor_inversible(k: float, seuil: float = PLANCHER_INVERSION,
                     nu: float = NU, vol: float = VOL_REF,
                     n: int = 60) -> float:
    """Le ténor le plus court où le second ordre corrige encore quelque chose.

    Au-dessous, `½·volga·Var(σ)` rapporté au prix tombe sous le plancher : le
    prix corrigé est **le même flottant** que le prix de départ, et la
    volatilité implicite qu'on en tire est du bruit d'arrondi et non un
    nombre. Ce n'est pas un défaut de la bissection ; c'est le raccourci qui
    n'a plus de contenu à l'aile courte, et la mesure le dit en jours.

    Renvoyé en jours. La bissection se tient entre un jour et deux ans.
    """
    lo, hi = 1.0, 730.0
    if poids_de_la_correction(k, hi / JOURS_AN, nu, vol) < seuil:
        return hi
    for _ in range(n):
        mid = 0.5 * (lo + hi)
        if poids_de_la_correction(k, mid / JOURS_AN, nu, vol) < seuil:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


#: La fenêtre de strikes que la planche du guide dessine.
FENETRE = (0.70, 1.30)


def retournement(t: float, nu: float = NU, vol: float = VOL_REF,
                 n: int = 800) -> tuple[float, float]:
    """Le strike où le sourire du second ordre se retourne, et sa valeur.

    Le sourire d'un développement du second ordre **redescend** dans les
    ailes : la correction de prix reste bornée alors que le véga s'effondre
    plus lentement qu'elle. Le lieu de ce retournement est le domaine au-delà
    duquel le développement ne décrit plus rien, et il se balaie.

    Le balayage se tient dans la fenêtre que la planche du guide dessine, et
    il exige un véga non négligeable : au-delà, l'inversion d'un prix qui ne
    dépend plus de la volatilité rend n'importe quoi, et c'est un artefact de
    bissection et non un fait de marché.
    """
    plancher = 1e-3 * vg.vega(S_REF, S_REF, vol, t, TAUX, DIVIDENDE)
    best = (0.0, -math.inf)
    for i in range(n + 1):
        k = FENETRE[0] * S_REF + (1.0 - FENETRE[0]) * S_REF * i / n
        if vg.vega(S_REF, k, vol, t, TAUX, DIVIDENDE) < plancher:
            continue
        v = sourire_second_ordre(k, t, nu, vol)
        if v > best[1]:
            best = (k, v)
    return best


#: Les strikes de la planche du guide.
STRIKES: tuple[float, ...] = (70.0, 80.0, 90.0, 95.0, 100.0, 105.0, 110.0,
                              120.0, 130.0)

#: Les trois ténors de la planche du guide, en jours.
TENORS: tuple[float, ...] = (30.0, 90.0, 365.0)


def table_sourire() -> Table:
    t = 30.0 / JOURS_AN
    rows = []
    for k in STRIKES:
        rows.append([
            num(k, 0),
            num(100 * sourire_naif(k, t), 1),
            num(100 * sourire_second_ordre(k, t), 1),
            num(100 * sourire_exact(k, t), 1),
            num(100 * (sourire_exact(k, t) - VOL_REF), 1, signed=True),
        ])
    return Table(
        key="vo_sourire",
        caption="Trois routes vers le sourire, et trois sourires différents",
        headers=["Strike", "Inversion au premier ordre (%)",
                 "Second ordre correctement inversé (%)",
                 "Espérance exacte (%)", "Ce que le sourire vaut (points)"],
        rows=rows,
        note="Le guide fait ici ce qu'aucun des sept autres n'a tenté : il "
             "**dérive le sourire** d'une inégalité de Jensen, sans peau "
             "supposée et sans flux modélisé. Le mécanisme est juste — le "
             "volga est positif dans les ailes et nul à la monnaie, donc "
             "l'incertitude sur la volatilité monte le prix des ailes et pas "
             "celui du corps — et c'est l'un des rares raisonnements de la "
             "série qui explique une observation au lieu de la décrire. Ce "
             "que le dépôt corrige est la route.\n\nÀ un mois et trente pour "
             "cent de la monnaie, les trois colonnes rendent "
             + num(100 * sourire_naif(70.0, t), 0) + " %, "
             + num(100 * sourire_second_ordre(70.0, t), 0) + " % et "
             + num(100 * sourire_exact(70.0, t), 0) + " %. La première "
             "divise la correction de prix par le véga, ce qui suppose le "
             "prix linéaire en volatilité — *exactement ce que la section 1 "
             "du même guide vient de réfuter* — et rend plus du double de la "
             "volatilité d'entrée. La deuxième inverse correctement le "
             "développement, et rend un sourire trop plat. La troisième est "
             "l'espérance exacte du prix sous la même loi de volatilité, et "
             "c'est la seule qui n'approxime rien. La dernière colonne donne "
             "le résultat honnête : **le sourire que ce mécanisme produit "
             "vaut neuf points de volatilité implicite à trente pour cent de "
             "la monnaie sur un mois**, et il est réel.",
    )


def table_retournement() -> Table:
    rows = []
    for j in TENORS:
        t = j / JOURS_AN
        k, v = retournement(t)
        rows.append([
            num(j, 0),
            num(k, 1),
            num(100 * (1.0 - k / S_REF), 1),
            num(100 * v, 1),
            num(100 * sourire_exact(k, t), 1),
            num(100 * sourire_exact(0.70 * S_REF, t), 1),
        ])
    k30, _ = retournement(30.0 / JOURS_AN)
    return Table(
        key="vo_retournement",
        caption="Le retournement que la planche du guide montre est celui de son approximation",
        headers=["Jours", "Strike du sommet", "Écart à la monnaie (%)",
                 "Sommet du second ordre (%)",
                 "L'exact au même strike (%)", "L'exact à trente pour cent (%)"],
        rows=rows,
        note="La planche du guide montre trois sourires qui montent, "
             "atteignent un sommet et **redescendent** dans les ailes, et sa "
             "légende dit que cette forme « correspond qualitativement à ce "
             "qu'on observe sur les marchés réels ». Un sourire réel ne "
             "redescend pas dans les ailes, et celui-là non plus : le "
             "retournement est un artefact du développement du second "
             "ordre.\n\nLe mécanisme est simple. La correction de prix "
             "`½·volga·Var(σ)` est bornée, parce que le volga finit par "
             "décroître quand on s'éloigne ; le véga par lequel on la "
             "reconvertit décroît plus vite encore. Le rapport passe donc par "
             "un maximum, et il tombe à "
             + num(100 * (1.0 - k30 / S_REF), 0) + " % de la monnaie sur un "
             "mois — *à l'intérieur de la fenêtre que la planche dessine*. "
             "Aux deux ténors plus longs il en sort par le bord, et les deux "
             "lignes correspondantes n'affichent que la borne du balayage. "
             "**L'artefact n'entre dans le domaine dessiné qu'au ténor le "
             "plus court**, et c'est précisément la courbe que la planche du "
             "guide montre en train de se retourner. Les deux dernières "
             "colonnes donnent l'espérance exacte au même endroit et plus "
             "loin : elle continue de monter là où le développement "
             "redescend.",
    )


# ---------------------------------------------------------------------------
# V. Vingt points contre deux fois dix
# ---------------------------------------------------------------------------

#: La position que le guide décrit : un call vendu, hors de la monnaie.
ECART_VENDU = 0.15

#: Les deux chocs de volatilité qu'il compare, en points.
CHOC_PETIT = 0.10
CHOC_GRAND = 0.20

#: Les trois ténors de sa planche, en jours.
TENORS_CHOC: tuple[float, ...] = (14.0, 60.0, 180.0)


def perte_du_vendeur(jours: float, choc: float,
                     ecart: float = ECART_VENDU,
                     vol: float = VOL_REF) -> float:
    """Ce qu'un choc de volatilité coûte au vendeur d'une aile, en points."""
    t = jours / JOURS_AN
    k = S_REF * (1.0 + ecart)
    return (th.call(S_REF, k, vol + choc, t, TAUX, DIVIDENDE)
            - th.call(S_REF, k, vol, t, TAUX, DIVIDENDE))


def rapport_des_chocs(jours: float, ecart: float = ECART_VENDU,
                      vol: float = VOL_REF) -> float:
    """Le rapport de la perte à vingt points sur celle à dix."""
    return (perte_du_vendeur(jours, CHOC_GRAND, ecart, vol)
            / perte_du_vendeur(jours, CHOC_PETIT, ecart, vol))


def part_du_second_ordre(jours: float, choc: float,
                         ecart: float = ECART_VENDU,
                         vol: float = VOL_REF) -> float:
    """La part de la perte que le terme de volga explique."""
    t = jours / JOURS_AN
    k = S_REF * (1.0 + ecart)
    lineaire = vg.vega(S_REF, k, vol, t, TAUX, DIVIDENDE) * choc
    quadratique = 0.5 * volga(S_REF, k, vol, t) * choc * choc
    return quadratique / (lineaire + quadratique)


def table_chocs() -> Table:
    rows = []
    for j in TENORS_CHOC:
        rows.append([
            num(j, 0),
            num(perte_du_vendeur(j, CHOC_PETIT), 4),
            num(perte_du_vendeur(j, CHOC_GRAND), 4),
            num(rapport_des_chocs(j), 2),
            num(100 * part_du_second_ordre(j, CHOC_PETIT), 1),
            num(100 * part_du_second_ordre(j, CHOC_GRAND), 1),
        ])
    return Table(
        key="vo_chocs",
        caption="Vingt points contre deux fois dix, et le ténor que le guide choisit",
        headers=["Jours", "Perte à dix points", "Perte à vingt points",
                 "Rapport", "Part du volga à dix points (%)",
                 "Part du volga à vingt points (%)"],
        rows=rows,
        note="« Une hausse de vingt points de volatilité coûte au vendeur à "
             "six mois bien plus que deux fois ce que coûte une hausse de "
             "dix. » Le fait est réel — le rapport dépasse deux à tous les "
             "ténors, et il ne le pourrait pas si le volga était nul — mais "
             "**le ténor choisi est le plus faible des trois** : le rapport "
             "vaut " + num(rapport_des_chocs(180.0), 2) + " à six mois, "
             + num(rapport_des_chocs(60.0), 2) + " à deux mois et "
             + num(rapport_des_chocs(14.0), 2) + " à deux semaines. *« Bien "
             "plus que deux fois » décrit la ligne courte de sa propre "
             "planche, pas la longue.*\n\nC'est la seconde fois de suite "
             "qu'un guide illustre son mécanisme là où il est le plus "
             "faible : celui du charm choisissait un strike qui ne portait "
             "plus de delta, celui-ci choisit le ténor où la convexité est la "
             "moins marquée. Les deux dernières colonnes disent pourquoi le "
             "ténor court gagne : la part de la perte que le terme de volga "
             "explique passe de "
             + num(100 * part_du_second_ordre(180.0, CHOC_GRAND), 0)
             + " % à six mois à "
             + num(100 * part_du_second_ordre(14.0, CHOC_GRAND), 0)
             + " % à deux semaines. Un modèle de risque linéaire en véga "
             "sous-estime donc d'autant plus qu'il regarde court, ce qui est "
             "l'inverse de l'intuition qu'un pupitre s'en fait.",
    )


# ---------------------------------------------------------------------------
# VI. Le papillon n'est pas neutre en véga
# ---------------------------------------------------------------------------


def strike_du_delta(cible: float, t: float, vol: float = VOL_REF,
                    put: bool = False) -> float:
    """Le strike d'un call ou d'un put de delta donné, par bissection."""
    lo, hi = 1.0, 20.0 * S_REF
    ecart = math.exp(-DIVIDENDE * t) if put else 0.0
    for _ in range(200):
        k = 0.5 * (lo + hi)
        d = G.delta_comptant(S_REF, k, vol, t, TAUX, DIVIDENDE) - ecart
        if d > cible:
            lo = k
        else:
            hi = k
    return 0.5 * (lo + hi)


@dataclass(frozen=True)
class Papillon:
    strike_bas: float
    strike_haut: float
    vega_ailes: float
    vega_corps: float
    volga_ailes: float
    volga_corps: float

    @property
    def vega_net(self) -> float:
        return self.vega_ailes - self.vega_corps

    @property
    def volga_net(self) -> float:
        return self.volga_ailes - self.volga_corps

    @property
    def part_de_vega(self) -> float:
        """Le véga net, en fraction du véga du corps."""
        return self.vega_net / self.vega_corps

    @property
    def poids_neutre(self) -> float:
        """La quantité d'ailes qui annule le véga net."""
        return self.vega_corps / self.vega_ailes

    @property
    def volga_neutre(self) -> float:
        """Le volga net du papillon pondéré en véga."""
        return self.poids_neutre * self.volga_ailes - self.volga_corps


def papillon(delta: float, jours: float, vol: float = VOL_REF) -> Papillon:
    """Le papillon un-deux-un symétrique en delta que le guide décrit."""
    t = jours / JOURS_AN
    kl = strike_du_delta(-delta, t, vol, put=True)
    kh = strike_du_delta(delta, t, vol)
    return Papillon(
        kl, kh,
        vg.vega(S_REF, kl, vol, t, TAUX, DIVIDENDE)
        + vg.vega(S_REF, kh, vol, t, TAUX, DIVIDENDE),
        2.0 * vg.vega(S_REF, S_REF, vol, t, TAUX, DIVIDENDE),
        volga(S_REF, kl, vol, t) + volga(S_REF, kh, vol, t),
        2.0 * volga(S_REF, S_REF, vol, t))


#: Deltas d'aile balayés.
DELTAS: tuple[float, ...] = (0.10, 0.25, 0.40)

#: Échéances balayées pour le papillon, en jours.
JOURS_PAP: tuple[float, ...] = (30.0, 90.0, 180.0)


def table_papillon() -> Table:
    rows = []
    for j in JOURS_PAP:
        for d in DELTAS:
            p = papillon(d, j)
            rows.append([
                num(j, 0),
                num(100 * d, 0),
                num(p.strike_bas, 2),
                num(p.strike_haut, 2),
                num(100 * p.part_de_vega, 1, signed=True),
                num(p.volga_net, 2),
                num(p.poids_neutre, 3),
                num(p.volga_neutre, 2),
            ])
    p25 = papillon(0.25, 90.0)
    p10 = papillon(0.10, 90.0)
    return Table(
        key="vo_papillon",
        caption="Le papillon n'est pas neutre en véga, et le corriger l'améliore",
        headers=["Jours", "Delta des ailes (%)", "Strike bas", "Strike haut",
                 "Véga net, en % du corps", "Volga net",
                 "Poids d'ailes qui neutralise", "Volga net une fois neutre"],
        rows=rows,
        note="« Les papillons sont le trade de volga pur : ailes longues, "
             "corps court, véga quasi nul, volga grand. » La seconde moitié "
             "tient et la première est fausse d'un cinquième. Le véga vaut "
             "`Se^{−qT}φ(d₁)√T`, il est **maximal à la monnaie**, et deux "
             "ailes ne valent donc jamais deux corps : un papillon "
             "un-deux-un symétrique en delta est court de "
             + num(100 * abs(p25.part_de_vega), 0) + " % du véga de son "
             "corps à vingt-cinq deltas, et de "
             + num(100 * abs(p10.part_de_vega), 0) + " % à dix. *Plus les "
             "ailes sont lointaines, plus le prétendu trade de volga pur est "
             "en réalité une vente de véga.*\n\nLa correction est immédiate, "
             "elle se calcule, et — c'est le point de la table — **elle "
             "améliore le trade**. En achetant les ailes dans le rapport des "
             "végas, "
             + num(p25.poids_neutre, 2) + " à vingt-cinq deltas, le véga net "
             "devient exactement nul *et le volga net monte de "
             + num(p25.volga_net, 0) + " à " + num(p25.volga_neutre, 0)
             + "*. Le papillon pondéré en véga est donc à la fois plus propre "
             "et plus exposé à ce qu'il prétend acheter. La seule structure "
             "que les sept autres guides aient présentée comme neutre et qui "
             "le soit **exactement** reste le risk reversal de la partie "
             "XXIV, dont le véga net est nul par la parité de `φ`.",
    )


# ---------------------------------------------------------------------------
# VII. Le décompte, sur huit parties
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Affirmation:
    enonce: str
    grandeur: str
    mesure: str


def affirmations() -> tuple[Affirmation, ...]:
    t30 = 30.0 / JOURS_AN
    t90 = 90.0 / JOURS_AN
    p25 = papillon(0.25, 90.0)
    k30, _ = retournement(t30)
    return (
        Affirmation(
            "Le volga vaut le véga fois `d₁d₂` sur sigma, et ce facteur "
            "décide de tout",
            "le risque",
            "exact, contrôlé par la dérivée du véga et par la différence "
            "seconde du prix"),
        Affirmation(
            "Près de la monnaie le volga est légèrement négatif ou nul",
            "rien",
            "exact, et c'est le troisième nom du même intervalle : "
            + num(100 * largeur_de_bande(t30), 2) + " % du comptant à trente "
            "jours"),
        Affirmation(
            "L'option à la monnaie est presque linéaire en volatilité, "
            "l'aile fortement convexe",
            "le risque",
            "se **renforce** : l'écart à la corde vaut "
            + num(100 * ecart_a_la_corde(1.0, t90), 2) + " % à la monnaie, "
            "c'est une droite"),
        Affirmation(
            "L'incertitude sur la volatilité produit le sourire, par Jensen",
            "le risque",
            "le mécanisme tient et vaut "
            + num(100 * (sourire_exact(70.0, t30) - VOL_REF), 0) + " points "
            "à trente pour cent de la monnaie ; trois routes en rendent "
            "trois"),
        Affirmation(
            "Le sourire ainsi produit correspond à ce qu'on observe sur les "
            "marchés",
            "rien",
            "sa planche se retourne à "
            + num(100 * (1.0 - k30 / S_REF), 0) + " % de la monnaie ; un "
            "sourire réel ne se retourne pas"),
        Affirmation(
            "Vingt points de volatilité coûtent bien plus que deux fois dix, "
            "à six mois",
            "le risque",
            "vrai, et six mois est le ténor le plus faible : "
            + num(rapport_des_chocs(180.0), 2) + " contre "
            + num(rapport_des_chocs(14.0), 2) + " à deux semaines"),
        Affirmation(
            "Le papillon a un véga quasi nul et un grand volga",
            "le risque",
            "court de " + num(100 * abs(p25.part_de_vega), 0) + " % du véga "
            "du corps ; le papillon pondéré est exactement neutre et porte "
            "plus de volga"),
        Affirmation(
            "Neutre en véga n'est pas neutre en volatilité",
            "le risque",
            "exact, et la partie XXII l'avait mesuré sur deux livres à véga "
            "net calculé nul"),
    )


def compte_par_grandeur() -> dict[str, int]:
    out: dict[str, int] = {}
    for a in affirmations():
        out[a.grandeur] = out.get(a.grandeur, 0) + 1
    return out


def familles() -> tuple[tuple[str, int], ...]:
    """Les huit parties d'options, comptées dans leurs propres modules."""
    return CH.familles() + (("Volga, partie XXVI", len(affirmations())),)


def table_reste() -> Table:
    rows = [[a.enonce, a.grandeur, a.mesure] for a in affirmations()]
    c = compte_par_grandeur()
    return Table(
        key="vo_reste",
        caption="Huit affirmations, et le décompte des huit parties d'options",
        headers=["L'affirmation", "Ce qu'elle déplace",
                 "Ce que la mesure en dit"],
        rows=rows,
        note="Le décompte se lit dans l'identité `E[R] = (µ·E[τ∧T] − c)/a` : "
             + num(c.get("le risque", 0), 0) + " affirmations déplacent le "
             "**risque**, " + num(c.get("rien", 0), 0) + " ne déplacent "
             "rien, aucune ne touche à l'horloge, et **aucune ne touche à la "
             "direction**. C'est la quatrième partie d'options consécutive "
             "dont cette colonne est vide. Sur les "
             + num(sum(n for _, n in familles()), 0) + " affirmations des "
             "huit parties, *aucune ne donne un sens*.\n\nCe huitième "
             "document est pourtant le plus ambitieux des huit, et il faut "
             "le dire : il ne se contente pas de décrire une grandeur, il "
             "**dérive une observation de marché** — le sourire — d'une "
             "inégalité de Jensen appliquée à une fonction convexe, sans "
             "peau supposée et sans flux modélisé. Aucun des sept autres "
             "n'a tenté cela. Le mécanisme tient, et la mesure lui donne "
             "neuf points de volatilité implicite à trente pour cent de la "
             "monnaie sur un mois. Ce que ce dépôt corrige n'est pas le "
             "raisonnement mais la route : *un développement du second ordre "
             "poussé hors de son domaine, puis inversé au premier ordre*, et "
             "l'artefact que cela produit est exactement le retournement que "
             "sa propre planche affiche.",
        wrap_cols=[0, 2],
    )


# ---------------------------------------------------------------------------
# Les quatre reliefs
# ---------------------------------------------------------------------------
#
# Les axes sont écrits de façon que le **maximum tombe au coin du fond** : en
# projection isométrique le coin (0, 0) est le plus éloigné.

SURF_ECHEANCE: tuple[float, ...] = (180.0, 90.0, 45.0, 21.0, 10.0, 5.0)
SURF_MONEYNESS: tuple[float, ...] = (1.45, 1.34, 1.24, 1.15, 1.07, 1.00)

SURF_ECHEANCE_SOURIRE: tuple[float, ...] = (7.0, 14.0, 30.0, 90.0, 180.0,
                                            365.0)
SURF_MONEYNESS_SOURIRE: tuple[float, ...] = (0.72, 0.78, 0.85, 0.91, 0.96,
                                             1.00)

SURF_ECHEANCE_ART: tuple[float, ...] = (7.0, 14.0, 30.0, 90.0, 180.0, 365.0)
SURF_MONEYNESS_ART: tuple[float, ...] = (0.72, 0.78, 0.85, 0.91, 0.96, 1.00)

SURF_DELTA: tuple[float, ...] = (0.05, 0.10, 0.18, 0.26, 0.34, 0.45)
SURF_ECHEANCE_PAP: tuple[float, ...] = (10.0, 21.0, 45.0, 90.0, 180.0,
                                        365.0)


@lru_cache(maxsize=2)
def surface_volga() -> tuple[tuple[float, ...], ...]:
    """`|volga|` en échéance et en moneyness."""
    return tuple(tuple(abs(volga(S_REF * m, S_REF, VOL_REF, j / JOURS_AN))
                       for m in SURF_MONEYNESS)
                 for j in SURF_ECHEANCE)


@lru_cache(maxsize=2)
def surface_sourire() -> tuple[tuple[float, ...], ...]:
    """Le sourire exact, en points de volatilité implicite."""
    return tuple(tuple(100.0 * (sourire_exact(S_REF * m, j / JOURS_AN)
                                - VOL_REF)
                       for m in SURF_MONEYNESS_SOURIRE)
                 for j in SURF_ECHEANCE_SOURIRE)


@lru_cache(maxsize=2)
def surface_artefact() -> tuple[tuple[float, ...], ...]:
    """Ce que l'inversion au premier ordre ajoute à l'espérance exacte."""
    return tuple(tuple(100.0 * (sourire_naif(S_REF * m, j / JOURS_AN)
                                - sourire_exact(S_REF * m, j / JOURS_AN))
                       for m in SURF_MONEYNESS_ART)
                 for j in SURF_ECHEANCE_ART)


@lru_cache(maxsize=2)
def surface_papillon() -> tuple[tuple[float, ...], ...]:
    """Le défaut de véga d'un papillon, en fraction du corps."""
    return tuple(tuple(100.0 * abs(papillon(d, j).part_de_vega)
                       for j in SURF_ECHEANCE_PAP)
                 for d in SURF_DELTA)


# ---------------------------------------------------------------------------
# Valeurs, tables, et exécution directe
# ---------------------------------------------------------------------------


def values() -> dict[str, str]:
    t30 = 30.0 / JOURS_AN
    t90 = 90.0 / JOURS_AN
    p25 = papillon(0.25, 90.0)
    p10 = papillon(0.10, 90.0)
    k30, v30 = retournement(t30)
    return {
        "vo_nu": num(100 * NU, 0),
        "vo_ecart_vol": num(100 * ecart_type_vol(), 2),
        "vo_bande_30": num(100 * largeur_de_bande(t30), 2),
        "vo_bande_365": num(100 * largeur_de_bande(1.0), 1),
        "vo_strikes_30": num(strikes_dans_la_bande(t30, 0.01), 2),
        "vo_corde_atm": num(100 * ecart_a_la_corde(1.0, t90), 2),
        "vo_corde_aile": num(100 * ecart_a_la_corde(1.30, t90), 1),
        "vo_rapport_aile": num(volga(1.30 * S_REF, S_REF, VOL_REF, t90)
                               / vg.vega(1.30 * S_REF, S_REF, VOL_REF, t90),
                               1),
        "vo_naif_70": num(100 * sourire_naif(70.0, t30), 0),
        "vo_ordre2_70": num(100 * sourire_second_ordre(70.0, t30), 0),
        "vo_exact_70": num(100 * sourire_exact(70.0, t30), 0),
        "vo_lift_70": num(100 * (sourire_exact(70.0, t30) - VOL_REF), 0),
        "vo_lift_130": num(100 * (sourire_exact(130.0, t30) - VOL_REF), 1),
        "vo_lift_an": num(100 * (sourire_exact(70.0, 1.0) - VOL_REF), 1),
        "vo_retour_strike": num(k30, 1),
        "vo_retour_ecart": num(100 * (1.0 - k30 / S_REF), 0),
        "vo_retour_valeur": num(100 * v30, 1),
        "vo_choc_court": num(rapport_des_chocs(14.0), 2),
        "vo_choc_moyen": num(rapport_des_chocs(60.0), 2),
        "vo_choc_long": num(rapport_des_chocs(180.0), 2),
        "vo_part_court": num(100 * part_du_second_ordre(14.0, CHOC_GRAND), 0),
        "vo_part_long": num(100 * part_du_second_ordre(180.0, CHOC_GRAND), 0),
        "vo_pap_defaut_25": num(100 * abs(p25.part_de_vega), 0),
        "vo_pap_defaut_10": num(100 * abs(p10.part_de_vega), 0),
        "vo_pap_poids": num(p25.poids_neutre, 2),
        "vo_pap_volga": num(p25.volga_net, 0),
        "vo_pap_volga_neutre": num(p25.volga_neutre, 0),
        "vo_portage_30": num(100 * decalage_de_portage(t30), 2),
        "vo_portage_365": num(100 * decalage_de_portage(1.0), 1),
        "vo_crete_10": num(crete_du_volga(10.0 / JOURS_AN), 2),
        "vo_crete_180": num(crete_du_volga(180.0 / JOURS_AN), 2),
        "vo_poids_pic": num(100 * pic_du_poids(t30)[1], 2),
        "vo_poids_strike": num(pic_du_poids(t30)[0], 1),
        "vo_poids_aile": num(100 * poids_de_la_correction(72.0, t30), 4),
        "vo_tenor_inversible": num(tenor_inversible(70.0), 0),
        "vo_affirmations": num(len(affirmations()), 0),
        "vo_total_options": num(sum(n for _, n in familles()), 0),
        "vo_vol": num(100 * VOL_REF, 0),
    }


def all_tables() -> dict[str, Table]:
    tables = [table_deux_routes(), table_bande(), table_courbure(),
              table_sourire(), table_retournement(), table_chocs(),
              table_papillon(), table_reste()]
    return {t.key: t for t in tables}


def main() -> None:
    for t in all_tables().values():
        print(t.to_text())
        print()
    for k, v in values().items():
        print(f"{k:24s} {v}")


if __name__ == "__main__":
    main()
