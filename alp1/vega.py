"""Le prix de l'incertitude, et le seuil qu'il impose.

Cette partie ferme la série d'options par son quatrième document, consacré au
véga. Il s'ouvre sur une phrase que les trois précédents n'ont pas :

    *Le véga n'est pas une lettre grecque. Ce n'est pas de la pédanterie — il
    mesure la sensibilité à un paramètre que le modèle suppose constant.*

C'est un aveu de circularité, et le dépôt en connaît la valeur : il en porte
une, nommée dans sa propre mémoire de projet, où une dérive de référence était
dérivée de la friction qu'elle devait battre. Un document qui nomme la sienne
mérite qu'on lise le reste avec attention.

I. Deux conventions, et un facteur cent
----------------------------------------
`V = ∂V/∂σ = Se^{−qT}φ(d₁)√T`, identique pour un call et un put. La forme
fermée est **par unité de volatilité**, donc par cent points ; les systèmes
cotent par point. Le guide écrit que mélanger les deux est une erreur d'un
facteur cent et qu'elle arrive plus souvent qu'on ne l'admet. Le dépôt vérifie
au passage les deux nombres que le guide publie : le véga croît en `√T`, mais
pas exactement — le rapport d'un an à deux semaines vaut **5,07** et non 5,5,
parce que `φ(d₁)` bouge aussi.

II. Le véga n'est pas un risque
--------------------------------
Un livre à véga net nul peut perdre lourdement : la surface a au moins trois
modes indépendants — le niveau, le terme, la peau. Le dépôt fait ce que la
partie XX a fait pour le delta : il construit **deux livres de véga net
rigoureusement nul** et les fait marcher sur chacun des trois modes.

III. La pondération, et l'exposant qu'on postule
--------------------------------------------------
Le guide propose le correctif de pupitre habituel : pondérer chaque échéance
par `√(30/T)`. C'est un exposant **postulé**, et la partie XVIII a payé pour
cette faute-là. Le dépôt le confronte à la seule famille de surfaces qui ait
un sens — une volatilité instantanée à retour à la moyenne — et le résultat
n'est pas un ajustement de constante : *la règle est sans échelle et la
surface en a une.* Aucune vitesse de retour ne la fait tenir : la meilleure
manque encore de 39 % aux deux bouts de la plage.

IV. Où la courbure change de signe
------------------------------------
`volga = V·d₁d₂/σ` est négative **entre** les deux racines `d₁ = 0` et
`d₂ = 0`, c'est-à-dire dans une bande de largeur `e^{σ²T/2} − e^{−σ²T/2}`
autour de la monnaie. Le guide dit « quasi linéaire près de la monnaie,
nettement convexe dans les ailes » ; le dépôt mesure la bande, et elle vaut
**un demi pour cent à trente jours** — plus étroite que le pas de la grille
de strikes.

V. Le seuil d'un vendeur de véga
----------------------------------
De là sort le résultat structurant, et c'est l'identité du document rencontrée
sur un quatrième objet. À espérance nulle sur la variation d'implicite, un
vendeur perd `½·volga·s²` par période. Pour revenir à zéro il lui faut une
**baisse d'implicite** de `µ*_σ = −½·(volga/V)·s²`, qui ne dépend d'aucune vue
et que la position fixe entièrement. Elle est nulle à la monnaie et vaut
**trois quarts de point par mois** sur une aile à dix delta.

VI. Ce qu'il faudrait pour établir une prime de volatilité
------------------------------------------------------------
« Vendre du véga est un portage. Cela paie la plupart du temps et les pertes
sont concentrées. » Le dépôt accepte l'énoncé, mesure la fréquence sous
dérive nulle — elle est bien au-dessus d'un demi, et l'espérance est
**négative** — puis pose sa question habituelle : combien d'expirations pour
distinguer un vrai portage de cette forme-là.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from . import grandeurs as G
from . import niveaux as nv
from . import quant as q
from . import theta as th
from .costs import norm_cdf
from .mc import Rng
from .report import Table, num

SEED = 20260912

S_REF = G.S_REF
VOL_REF = G.VOL_REF

#: Taux et dividende, repris de la partie XXI pour que les quatre parties
#: d'options parlent du même sous-jacent.
TAUX = th.TAUX
DIVIDENDE = th.DIVIDENDE

JOURS_AN = nv.JOURS_AN


def _phi(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


# ---------------------------------------------------------------------------
# I. Deux conventions, et un facteur cent
# ---------------------------------------------------------------------------


def vega(s: float, k: float, vol: float, t: float, r: float = 0.0,
         div: float = 0.0) -> float:
    """`V = Se^{−qT}φ(d₁)√T`, **par unité de volatilité**.

    C'est-à-dire par cent points de volatilité. Les systèmes de négociation
    cotent presque toujours par *un* point, ce qui est ce nombre divisé par
    cent, et mélanger les deux est une erreur d'un facteur cent.
    """
    if t <= 0.0:
        return 0.0
    d1, _ = G._d(s, k, vol, t, r, div)
    return s * math.exp(-div * t) * _phi(d1) * math.sqrt(t)


def vega_par_point(s: float, k: float, vol: float, t: float, r: float = 0.0,
                   div: float = 0.0) -> float:
    """La même chose dans l'unité du pupitre : par point de volatilité."""
    return vega(s, k, vol, t, r, div) / 100.0


def vega_numerique(s: float, k: float, vol: float, t: float, r: float = 0.0,
                   div: float = 0.0) -> float:
    """Le contrôle de la forme fermée, par différence finie sur `σ`."""
    h = 1e-6
    return (th.call(s, k, vol + h, t, r, div)
            - th.call(s, k, vol - h, t, r, div)) / (2.0 * h)


def volga(s: float, k: float, vol: float, t: float, r: float = 0.0,
          div: float = 0.0) -> float:
    """`∂²V/∂σ² = V·d₁d₂/σ` — la courbure en volatilité.

    Elle est **négative entre les deux racines** `d₁ = 0` et `d₂ = 0`, donc
    dans une bande étroite autour de la monnaie, et positive partout ailleurs.
    C'est ce qui interdit de compenser le véga d'une aile par celui d'une
    option à la monnaie.
    """
    if t <= 0.0:
        return 0.0
    d1, d2 = G._d(s, k, vol, t, r, div)
    return vega(s, k, vol, t, r, div) * d1 * d2 / vol


def volga_numerique(s: float, k: float, vol: float, t: float, r: float = 0.0,
                    div: float = 0.0) -> float:
    h = 1e-4
    return (vega(s, k, vol + h, t, r, div)
            - vega(s, k, vol - h, t, r, div)) / (2.0 * h)


def vanna(s: float, k: float, vol: float, t: float, r: float = 0.0,
          div: float = 0.0) -> float:
    """`∂²V/∂S∂σ = −V·d₂/(Sσ)` — ce que la peau déplace."""
    if t <= 0.0:
        return 0.0
    _, d2 = G._d(s, k, vol, t, r, div)
    return -vega(s, k, vol, t, r, div) * d2 / (s * vol)


def rapport_de_tenors(jours_long: float = 365.0, jours_court: float = 14.0,
                      vol: float = VOL_REF, s: float = S_REF,
                      k: float = S_REF) -> float:
    """Le rapport des végas de deux échéances, **au même strike**.

    Le guide l'annonce à « environ 5,5 » pour un an contre deux semaines. Il
    vaut 5,07, et l'écart n'est pas dans la racine : `√T` seul rendrait 5,11,
    et `φ(d₁)` retire le reste. La racine est donc une bonne approximation, et
    le nombre publié une mauvaise.
    """
    return (vega(s, k, vol, jours_long / JOURS_AN)
            / vega(s, k, vol, jours_court / JOURS_AN))


#: Le rapport annoncé par le guide.
RAPPORT_ANNONCE = 5.5

#: Échéances balayées, en jours.
ECHEANCES: tuple[float, ...] = (7.0, 14.0, 30.0, 60.0, 90.0, 180.0, 365.0)

#: Moneyness balayées.
MONEYNESS: tuple[float, ...] = (0.80, 0.90, 0.95, 1.00, 1.05, 1.10, 1.20)


def largeur_du_pic(t: float, vol: float = VOL_REF, part: float = 0.5) -> float:
    """La largeur du pic de véga, à mi-hauteur, en fraction du spot.

    Le guide écrit « là où le gamma est une pointe, le véga est une colline ».
    La colline se mesure : le véga vaut la moitié de son maximum quand
    `|d₁| = √(2 ln 2)`, la même constante que la largeur d'un niveau de la
    partie XIX.
    """
    u = math.sqrt(2.0 * math.log(1.0 / part))
    v = vol * math.sqrt(t)
    return math.exp(u * v + 0.5 * v * v) - math.exp(-u * v + 0.5 * v * v)


def largeur_du_pic_gamma(t: float, vol: float = VOL_REF,
                         part: float = 0.5) -> float:
    """La même largeur pour le gamma, mesurée sur une grille de spot.

    C'est le contrôle de la phrase du guide, et il la réfute : les deux pics
    ont **presque la même largeur**, parce qu'ils partagent `φ(d₁)`. Ce qui
    va en sens inverse n'est pas la largeur, c'est la hauteur.
    """
    ms = [0.30 + 0.0005 * i for i in range(3400)]
    hauteurs = [(m, nv.gamma(m * S_REF, S_REF, vol, t)) for m in ms]
    cible = part * max(h for _, h in hauteurs)
    dedans = [m for m, h in hauteurs if h >= cible]
    return (max(dedans) - min(dedans)) if dedans else 0.0


def rapport_gamma_vega(s: float, vol: float, t: float) -> float:
    """`Γ/V = 1/(S²σT)` — exact, et **indépendant du strike**.

    C'est le pendant de l'identité `|Θ₁|/Γ = ½σ²S²` de la partie XIX, et les
    deux se composent : `|Θ₁|/V = σ/2T`. Trois grandeurs grecques, deux
    rapports fixes, et *aucun des trois ne contient une direction*.
    """
    return 1.0 / (s * s * vol * t)


def rapport_theta_vega(vol: float, t: float) -> float:
    """`|Θ₁|/V = σ/2T`, obtenu en composant les deux identités."""
    return vol / (2.0 * t)


def table_echelle() -> Table:
    rows = []
    for j in ECHEANCES:
        t = j / JOURS_AN
        g = nv.gamma(S_REF, S_REF, VOL_REF, t)
        v = vega(S_REF, S_REF, VOL_REF, t)
        rows.append([
            num(j, 0),
            num(v, 2),
            num(vega_par_point(S_REF, S_REF, VOL_REF, t), 4),
            num(v / vega(S_REF, S_REF, VOL_REF, 30.0 / JOURS_AN), 3),
            num(math.sqrt(j / 30.0), 3),
            num(100 * largeur_du_pic(t), 1),
            num(100 * largeur_du_pic_gamma(t), 1),
            num(g / v, 5),
        ])
    return Table(
        key="vg_echelle",
        caption="Le véga, ses deux unités, et la colline qui n'en est pas une",
        headers=["Jours", "Véga par unité de volatilité",
                 "Véga par point (unité du pupitre)",
                 "Rapport au mois", "√(T/30)",
                 "Largeur du pic de véga (% du spot)",
                 "Largeur du pic de gamma (% du spot)",
                 "Gamma sur véga"],
        rows=rows,
        note="Les deux premières colonnes sont **le même nombre** dans deux "
             "unités qui diffèrent d'un facteur cent : la forme fermée est "
             "par unité de volatilité, les systèmes cotent par point. C'est "
             "la seule erreur de cette série qui coûte deux ordres de "
             "grandeur d'un coup. Les colonnes trois et quatre comparent la "
             "croissance mesurée à la racine du temps : la racine est "
             "excellente, et le rapport d'un an à deux semaines vaut "
             + num(rapport_de_tenors(), 2) + " quand le guide annonce "
             + num(RAPPORT_ANNONCE, 1) + ". Les deux largeurs **réfutent la "
             "formule du guide** — le gamma serait une pointe, le véga une "
             "colline — car les deux pics partagent `φ(d₁)` et mesurent la "
             "même chose à un pour cent près ; ce qui va en sens inverse est "
             "la hauteur. La dernière colonne le dit exactement : "
             "`Γ/V = 1/(S²σT)`, indépendant du strike, et elle chute d'un "
             "facteur " + num(nv.gamma(S_REF, S_REF, VOL_REF, 7.0 / JOURS_AN)
                              / vega(S_REF, S_REF, VOL_REF, 7.0 / JOURS_AN)
                              / (nv.gamma(S_REF, S_REF, VOL_REF, 1.0)
                                 / vega(S_REF, S_REF, VOL_REF, 1.0)), 0)
             + " entre la semaine et l'année. *Une option courte est presque "
             "du gamma pur, une option longue presque du véga pur*, et c'est "
             "une identité et non une observation.",
    )


# ---------------------------------------------------------------------------
# II. Le véga n'est pas un risque
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Ligne:
    """Une ligne d'un livre : une quantité, un strike, une échéance."""

    quantite: float
    moneyness: float
    jours: float

    @property
    def strike(self) -> float:
        return S_REF / self.moneyness

    def vega(self, vol: float = VOL_REF) -> float:
        return self.quantite * vega(S_REF, self.strike, vol,
                                    self.jours / JOURS_AN)

    def prix(self, vol: float) -> float:
        return self.quantite * th.call(S_REF, self.strike, vol,
                                       self.jours / JOURS_AN, 0.0, 0.0)


def _neutraliser(lignes: list[Ligne], couverture: Ligne) -> list[Ligne]:
    """Ajoute à un livre la quantité de couverture qui annule son véga net.

    Le zéro est **calculé**, jamais écrit : la partie XX a publié « +0,00 »
    à la main sur deux livres qui n'étaient pas à delta nul, et la leçon
    vaut pour toutes les grandeurs additives.
    """
    besoin = sum(l.vega() for l in lignes)
    unitaire = Ligne(1.0, couverture.moneyness, couverture.jours).vega()
    return lignes + [Ligne(-besoin / unitaire, couverture.moneyness,
                           couverture.jours)]


def livre_calendrier() -> list[Ligne]:
    """Long le mois, court l'année, à véga net nul."""
    return _neutraliser([Ligne(1.0, 1.00, 30.0)], Ligne(1.0, 1.00, 365.0))


def livre_peau() -> list[Ligne]:
    """Long les deux ailes, court la monnaie, à véga net nul."""
    return _neutraliser([Ligne(1.0, 0.90, 90.0), Ligne(1.0, 1.10, 90.0)],
                        Ligne(1.0, 1.00, 90.0))


#: Amplitudes de choc balayées, en points de volatilité. La seconde est celle
#: de l'exemple du guide, et c'est à cette taille que la courbure se voit :
#: elle croît comme le **carré** du choc.
CHOCS: tuple[float, ...] = (1.0, 10.0)


def mode_niveau(ligne: Ligne, choc: float) -> float:
    """Toute la surface monte."""
    return choc / 100.0


#: Le pivot du mode de terme, en jours : l'avant monte, l'arriere baisse, et
#: le ténor pivot ne bouge pas. Une marche au lieu d'une rampe ferait passer
#: un livre entier du mauvais côté selon qu'il est à 89 ou 91 jours.
PIVOT_TERME = 90.0


def mode_terme(ligne: Ligne, choc: float) -> float:
    """L'avant monte, l'arrière baisse, en rampe autour du pivot."""
    pente = 1.0 - ligne.jours / PIVOT_TERME
    return choc * max(-1.0, min(1.0, pente)) / 100.0


def mode_peau(ligne: Ligne, choc: float) -> float:
    """Les ailes montent, le corps baisse."""
    return (choc if abs(math.log(ligne.moneyness)) > 0.05 else -choc) / 100.0


MODES = (("Niveau", mode_niveau), ("Terme", mode_terme), ("Peau", mode_peau))

LIVRES = (("Calendrier", livre_calendrier), ("Peau", livre_peau))


def pl_livre(lignes: list[Ligne], mode, choc: float) -> float:
    """Le résultat d'un livre sous un mode, par **réévaluation exacte**."""
    return sum(l.prix(VOL_REF + mode(l, choc)) - l.prix(VOL_REF)
               for l in lignes)


def pl_au_premier_ordre(lignes: list[Ligne], mode, choc: float) -> float:
    """Le même résultat lu au véga seul — ce que le résumé du livre annonce."""
    return sum(l.vega() * mode(l, choc) for l in lignes)


def vega_net(lignes: list[Ligne]) -> float:
    return sum(l.vega() for l in lignes)


def table_modes() -> Table:
    rows = []
    for nom_l, faire in LIVRES:
        lignes = faire()
        for nom_m, mode in MODES:
            for choc in CHOCS:
                rows.append([
                    nom_l,
                    nom_m,
                    num(choc, 0),
                    num(vega_net(lignes) / 100.0, 8),
                    num(pl_au_premier_ordre(lignes, mode, choc), 4,
                        signed=True),
                    num(pl_livre(lignes, mode, choc), 4, signed=True),
                    num(pl_livre(lignes, mode, choc)
                        - pl_au_premier_ordre(lignes, mode, choc), 4,
                        signed=True),
                ])
    lp = livre_peau()
    return Table(
        key="vg_modes",
        caption="Deux livres à véga net nul, et trois façons de perdre dessus",
        headers=["Livre", "Mode", "Choc (points de vol)",
                 "Véga net (par point)",
                 "Résultat au véga (points d'indice)",
                 "Résultat par réévaluation", "Ce que la courbure ajoute"],
        rows=rows,
        note="Les deux livres ont un véga net **calculé** nul, à la huitième "
             "décimale : la quantité de couverture est résolue, jamais "
             "écrite — la partie XX a publié « +0,00 » à la main sur deux "
             "livres qui n'étaient pas neutres, et la leçon vaut pour toute "
             "grandeur additive. La table sépare deux aveuglements "
             "différents. Le premier est celui du **nombre résumé** : le véga "
             "net est nul et le résultat ne l'est pas, parce qu'une somme de "
             "sensibilités ne dit rien quand les paramètres ne bougent pas "
             "ensemble. Le livre calendrier vit du mode de terme, le livre de "
             "peau vit du mode de peau, et chacun est aveugle à celui de "
             "l'autre. Le second est celui du **premier ordre**, et c'est la "
             "dernière colonne : sous un choc de niveau, où le véga annonce "
             "zéro et le dit correctement, le livre de peau perd tout de "
             "même — " + num(abs(pl_livre(lp, mode_niveau, 10.0)), 3)
             + " point d'indice sur les dix points de l'exemple du guide, "
             "contre " + num(abs(pl_livre(lp, mode_niveau, 1.0)), 4)
             + " sur un seul. *Cette perte-là croît comme le carré du choc*, "
             "elle n'a aucun véga, et c'est exactement ce qui interdit de "
             "compenser le véga d'une aile par celui d'une option à la "
             "monnaie.",
    )


# ---------------------------------------------------------------------------
# III. La pondération, et l'exposant qu'on postule
# ---------------------------------------------------------------------------


#: L'échéance de référence de la règle du guide, en jours.
TENOR_REF = 30.0


def poids_regle(jours: float, ref: float = TENOR_REF) -> float:
    """`√(30/T)` — la règle du guide, et son exposant postulé."""
    return math.sqrt(ref / jours)


def _g(t: float, kappa: float) -> float:
    """La sensibilité de la variance implicite de ténor `t` à la variance
    instantanée, sous retour à la moyenne de vitesse `kappa`.

    `(1 − e^{−κT})/(κT)` : c'est la moyenne de l'espérance de la variance
    future sur l'intervalle, et rien d'autre n'entre.
    """
    x = kappa * t
    return (1.0 - math.exp(-x)) / x if x > 1e-12 else 1.0


def poids_modele(jours: float, kappa: float, ref: float = TENOR_REF) -> float:
    """Le poids qu'une surface à retour à la moyenne impose."""
    return _g(jours / JOURS_AN, kappa) / _g(ref / JOURS_AN, kappa)


def exposant_effectif(jours: float, kappa: float) -> float:
    """L'exposant local `−d ln g / d ln T`, mesuré et non postulé.

    Il vaut zéro aux ténors courts et un aux ténors longs. Il ne vaut un
    demi qu'à **un seul** ténor, et la règle du guide suppose qu'il le vaut
    partout.
    """
    h = 1e-4
    t = jours / JOURS_AN
    a = math.log(_g(t * (1.0 - h), kappa))
    b = math.log(_g(t * (1.0 + h), kappa))
    return -(b - a) / (2.0 * h)


def tenor_de_l_exposant(cible: float, kappa: float) -> float:
    """Le ténor, en jours, où l'exposant effectif vaut `cible`."""
    lo, hi = 1e-4, 60.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if exposant_effectif(mid * JOURS_AN, kappa) < cible:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi) * JOURS_AN


def ecart_maximal(kappa: float) -> float:
    """L'écart relatif maximal entre la règle et le modèle, sur la plage."""
    return max(abs(poids_modele(j, kappa) / poids_regle(j) - 1.0)
               for j in ECHEANCES)


@lru_cache(maxsize=2)
def kappa_minimax() -> tuple[float, float]:
    """La vitesse de retour qui **minimise** l'écart maximal, et cet écart.

    C'est le meilleur cas possible pour la règle, et il n'est pas bon : la
    règle est sans échelle, la surface en a une, et aucune vitesse ne
    réconcilie une loi de puissance avec une courbe qui a un genou.
    """
    meilleur = (0.0, math.inf)
    for i in range(1, 4001):
        k = i * 0.01
        e = ecart_maximal(k)
        if e < meilleur[1]:
            meilleur = (k, e)
    return meilleur


#: Vitesses de retour balayées, par an. Elle n'est pas observable ici — aucun
#: hébergeur de données de marché n'est joignable — et le dépôt la balaie donc
#: au lieu de la choisir, comme la taille de grappe du footprint.
KAPPA_GRILLE: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0, 16.0)


def table_ponderation() -> Table:
    k_opt, e_opt = kappa_minimax()
    rows = []
    for j in ECHEANCES:
        ligne = [num(j, 0), num(poids_regle(j), 3)]
        for k in (4.0, k_opt):
            ligne.append(num(poids_modele(j, k), 3))
        ligne.append(num(100 * (poids_modele(j, k_opt) / poids_regle(j) - 1.0),
                         1, signed=True))
        ligne.append(num(exposant_effectif(j, k_opt), 3))
        rows.append(ligne)
    return Table(
        key="vg_ponderation",
        caption="La règle en racine, contre la seule surface qui ait une échelle",
        headers=["Jours", "Règle √(30/T)",
                 "Modèle, retour en 4/an", "Modèle, au meilleur retour",
                 "Écart de la règle (%)", "Exposant effectif"],
        rows=rows,
        note="Le guide propose de pondérer chaque seau d'échéance par "
             "`√(30/T)`, et l'appelle le correctif standard. C'est un "
             "exposant **postulé**, et la partie XVIII a payé pour cette "
             "faute : une demi-largeur y était supposée décroître en racine, "
             "la mesure a rendu 0,61. Ici le verdict est plus dur, parce "
             "qu'il ne porte pas sur la valeur de l'exposant mais sur son "
             "existence. Sous la seule famille de surfaces qui ait un sens — "
             "une volatilité instantanée revenant vers sa moyenne — la "
             "sensibilité du ténor `T` vaut `(1 − e^{−κT})/(κT)`, dont "
             "l'exposant local passe de **zéro** aux ténors courts à **un** "
             "aux ténors longs. La dernière colonne le montre : il ne vaut un "
             "demi qu'à un seul ténor. *La règle est sans échelle, la surface "
             "en a une*, et la meilleure vitesse de retour possible — "
             + num(k_opt, 2) + " par an, soit une demi-vie de "
             + num(JOURS_AN * math.log(2.0) / k_opt, 0) + " jours — laisse "
             "encore " + num(100 * e_opt, 0) + " % d'écart aux deux bouts de "
             "la plage.",
    )


def table_kappa() -> Table:
    """Le paramètre non observable, et le ténor qu'il déplace."""
    rows = []
    for k in KAPPA_GRILLE:
        rows.append([
            num(k, 1),
            num(JOURS_AN * math.log(2.0) / k, 0),
            num(exposant_effectif(30.0, k), 3),
            num(exposant_effectif(365.0, k), 3),
            num(tenor_de_l_exposant(0.5, k), 0),
            num(100 * ecart_maximal(k), 0),
        ])
    return Table(
        key="vg_kappa",
        caption="La vitesse de retour, qu'on ne mesure pas ici, et ce qu'elle décide",
        headers=["Retour à la moyenne (par an)", "Demi-vie (jours)",
                 "Exposant à 30 jours", "Exposant à un an",
                 "Ténor où l'exposant vaut ½ (jours)",
                 "Écart maximal de la règle (%)"],
        rows=rows,
        note="La vitesse de retour n'est pas observable dans ce dépôt : "
             "aucun hébergeur de données de marché n'y est joignable, et la "
             "règle du dépôt est alors de balayer plutôt que de choisir — "
             "c'est ce qui est fait pour la taille de grappe du footprint et "
             "pour la hauteur de rangée du profil. Le balayage rend un fait "
             "qui ne dépend d'aucune de ces valeurs : le ténor où l'exposant "
             "vaut un demi est **inversement proportionnel** à la vitesse, "
             "et pour qu'il tombe sur les trente jours de la règle il "
             "faudrait une demi-vie de " + num(
                 JOURS_AN * math.log(2.0) / (458.6 / 30.0), 0) + " jours. "
             "Aucune ligne du balayage n'amène l'écart maximal sous trente "
             "pour cent. La règle n'approxime donc pas mal une surface : "
             "*elle en décrit une autre.*",
    )


# ---------------------------------------------------------------------------
# IV. Où la courbure change de signe
# ---------------------------------------------------------------------------


def bande_de_courbure(t: float, vol: float = VOL_REF) -> tuple[float, float]:
    """La bande de moneyness où `volga` est **négative**.

    Elle est bornée par les deux racines `d₂ = 0` et `d₁ = 0`, donc par
    `e^{−σ²T/2}` et `e^{+σ²T/2}` : une forme fermée sans aucun paramètre
    libre. Le guide dit « quasi linéaire près de la monnaie, nettement
    convexe dans les ailes » ; c'est cette bande-là, et elle est étroite.
    """
    v = 0.5 * vol * vol * t
    return math.exp(-v), math.exp(v)


def largeur_de_bande(t: float, vol: float = VOL_REF) -> float:
    lo, hi = bande_de_courbure(t, vol)
    return hi - lo


#: Pas de grille de strikes balayés, en fraction du spot. Aucun n'est
#: observable ici, et le dépôt les balaie plutôt que d'en choisir un.
PAS_DE_GRILLE: tuple[float, ...] = (0.0025, 0.005, 0.01, 0.025, 0.05)


def strikes_dans_la_bande(t: float, pas: float,
                          vol: float = VOL_REF) -> float:
    """Combien de strikes tombent dans la bande. Souvent moins d'un."""
    return largeur_de_bande(t, vol) / pas


def table_bande() -> Table:
    rows = []
    for j in ECHEANCES:
        t = j / JOURS_AN
        lo, hi = bande_de_courbure(t)
        ligne = [num(j, 0), num(lo, 4), num(hi, 4),
                 num(100 * largeur_de_bande(t), 2)]
        for pas in (0.005, 0.01, 0.025):
            ligne.append(num(strikes_dans_la_bande(t, pas), 2))
        rows.append(ligne)
    return Table(
        key="vg_bande",
        caption="La bande où la courbure est négative, et le pas de la grille de strikes",
        headers=["Jours", "Borne basse (S/K)", "Borne haute (S/K)",
                 "Largeur (% du spot)",
                 "Strikes dedans, pas de 0,5 %", "pas de 1 %",
                 "pas de 2,5 %"],
        rows=rows,
        note="`volga = V·d₁d₂/σ` est négative entre les deux racines, donc "
             "sur la bande `[e^{−σ²T/2}, e^{+σ²T/2}]` — une forme fermée "
             "sans paramètre libre, dont la largeur vaut `σ²T` au premier "
             "ordre. Le guide écrit que le véga est quasi linéaire en `σ` "
             "près de la monnaie et nettement convexe dans les ailes ; c'est "
             "exact, et la mesure dit à quel point « près de la monnaie » est "
             "près. À trente jours la bande fait "
             + num(100 * largeur_de_bande(30.0 / JOURS_AN), 2) + " % du "
             "spot : **sur une grille au pas d'un pour cent, il n'y tombe "
             "pas un seul strike.** La phrase du guide décrit donc une "
             "propriété vraie d'un lieu qui, aux échéances courtes, ne "
             "contient aucun instrument négociable — et c'est pour cela que "
             "la courbure ne se compense jamais entre une aile et une option "
             "à la monnaie : *il n'y a pas d'option à la monnaie au sens de "
             "la courbure.*",
    )


# ---------------------------------------------------------------------------
# V. Le seuil d'un vendeur de véga
# ---------------------------------------------------------------------------


#: Volatilités de la volatilité balayées, par an. Non observable ici.
NU_GRILLE: tuple[float, ...] = (0.40, 0.60, 0.80, 1.00, 1.50)

#: La volatilité de la volatilité déclarée pour les chiffres de la partie.
NU_REF = 0.80

#: La position du vendeur : une aile à quatre-vingt-dix jours, vendue.
VENDEUR = Ligne(-1.0, 0.90, 90.0)

#: La période de détention, en jours.
PERIODE = 30.0


def ecart_type_implicite(nu: float = NU_REF, jours: float = PERIODE,
                         vol: float = VOL_REF) -> float:
    """L'écart-type de la variation d'implicite sur la période, en absolu."""
    return vol * nu * math.sqrt(jours / JOURS_AN)


def derive_equilibre(ligne: Ligne, nu: float = NU_REF,
                     jours: float = PERIODE, vol: float = VOL_REF) -> float:
    """`µ*_σ = −½·(volga/V)·s²` — le seuil d'un vendeur de véga.

    C'est l'identité du document rencontrée sur un quatrième objet. À
    espérance nulle sur la variation d'implicite, un vendeur perd
    `½·volga·s²` par période ; pour revenir à zéro il lui faut une **baisse
    d'implicite** de ce montant, qui ne dépend d'aucune vue et que la
    position fixe entièrement. Le nombre est rendu en points de volatilité.
    """
    v = vega(S_REF, ligne.strike, vol, ligne.jours / JOURS_AN)
    w = volga(S_REF, ligne.strike, vol, ligne.jours / JOURS_AN)
    s = ecart_type_implicite(nu, jours, vol)
    return -100.0 * 0.5 * (w / v) * s * s


@lru_cache(maxsize=4)
def _tirages(n: int = 20000, seed: int = SEED) -> tuple[float, ...]:
    """Les tirages, **fixés une fois**.

    Toutes les dérives voient le même flux d'aléa : c'est ce qui rend
    l'espérance simulée une fonction lisse et monotone de la dérive, donc
    inversible par bissection, et c'est la même raison qui rend lisses les
    reliefs de la partie XIV.
    """
    rng = Rng(seed)
    return tuple(rng.gauss() for _ in range(n))


def simuler_vendeur(moneyness: float = 0.90, jours_option: float = 90.0,
                    nu: float = NU_REF, derive: float = 0.0,
                    n: int = 20000, vol: float = VOL_REF,
                    seed: int = SEED) -> tuple[float, ...]:
    """Vend une option, la garde un mois, et ne bouge que l'implicite.

    Le spot est **épinglé** : la partie mesure le risque de volatilité seul,
    comme la planche du guide qui montre un choc d'implicite sans que le
    marché bouge. La dérive est en points de volatilité sur la période.
    """
    ligne = Ligne(-1.0, moneyness, jours_option)
    s = ecart_type_implicite(nu, PERIODE, vol)
    m = derive / 100.0
    base = ligne.prix(vol)
    return tuple(ligne.prix(max(0.01, vol + m + s * z)) - base
                 for z in _tirages(n, seed))


@dataclass(frozen=True)
class Resume:
    moyenne: float
    mediane: float
    taux: float
    q05: float
    pire: float
    ecart_type: float


def _resume(vals) -> Resume:
    tri = sorted(vals)
    n = len(tri)
    moy = sum(tri) / n
    var = sum((x - moy) ** 2 for x in tri) / (n - 1)
    return Resume(moy, tri[n // 2], sum(1 for x in tri if x > 0.0) / n,
                  tri[max(0, int(0.05 * (n - 1)))], tri[0], math.sqrt(var))


@lru_cache(maxsize=64)
def derive_equilibre_exacte(moneyness: float = 0.90,
                            jours_option: float = 90.0,
                            nu: float = NU_REF, n: int = 20000) -> float:
    """Le seuil **mesuré**, par bissection sur l'espérance simulée.

    La forme fermée est du second ordre, et la variation d'implicite sur un
    mois n'est pas petite : à la volatilité de la volatilité déclarée, son
    écart-type vaut près d'un quart de l'implicite elle-même. Le troisième
    ordre pèse donc, et le dépôt publie les deux nombres plutôt que le seul
    qui l'arrange — la règle est celle des parties XX et XXI : *une forme
    fermée ne se publie pas sans être confrontée à autre chose qu'elle-même.*

    L'espérance décroît avec la dérive — un vendeur perd quand l'implicite
    monte — et la bissection en tient compte.
    """
    lo, hi = -8.0, 4.0
    for _ in range(44):
        mid = 0.5 * (lo + hi)
        if _resume(simuler_vendeur(moneyness, jours_option, nu, mid,
                                   n)).moyenne > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def table_seuil() -> Table:
    rows = []
    for m in (0.80, 0.90, 0.95, 1.00, 1.05, 1.10, 1.20):
        ligne = Ligne(-1.0, m, 90.0)
        t = 90.0 / JOURS_AN
        v = vega(S_REF, ligne.strike, VOL_REF, t)
        w = volga(S_REF, ligne.strike, VOL_REF, t)
        mu = derive_equilibre(ligne)
        mes = _resume(simuler_vendeur(m, 90.0))
        rows.append([
            num(m, 2),
            num(v / 100.0, 4),
            num(w / 10000.0, 6, signed=True),
            num(w / v, 3, signed=True),
            num(mu, 3, signed=True),
            num(derive_equilibre_exacte(m, 90.0), 3, signed=True),
            num(mes.moyenne, 4, signed=True),
            num(100 * mes.taux, 1),
        ])
    return Table(
        key="vg_seuil",
        caption="Le seuil d'un vendeur de véga, et il ne dépend d'aucune vue",
        headers=["Moneyness S/K", "Véga (par point)", "Volga (par point²)",
                 "Volga sur véga", "Seuil, forme fermée (points)",
                 "Seuil, mesuré", "Espérance à dérive nulle (points d'indice)",
                 "Fréquence de gain (%)"],
        rows=rows,
        note="À quatre-vingt-dix jours, à "
             + num(100 * NU_REF, 0) + " % de volatilité de la volatilité, sur "
             "une détention d'un mois. La cinquième colonne est le résultat "
             "de la section, et c'est l'identité du document rencontrée sur "
             "un quatrième objet : `µ*_σ = −½·(volga/V)·s²`. **Elle ne "
             "dépend d'aucune vue sur la volatilité** — elle est une "
             "propriété de la position, exactement comme `µ* = c/E[τ∧T]` est "
             "une propriété de la géométrie. Elle est nulle à la monnaie et "
             "vaut " + num(abs(derive_equilibre(Ligne(-1.0, 0.90, 90.0))), 2)
             + " point par mois sur l'aile vendue : *un vendeur d'aile qui "
             "voit son implicite immobile perd*, et le résumé de son livre "
             "ne le lui dit pas. Les deux dernières colonnes sont la mesure "
             "sur " + num(20000, 0) + " tirages, et elles donnent la forme "
             "que ce document rencontre partout — **une espérance négative "
             "sous une fréquence de gain supérieure à un demi.**",
    )


def table_volofvol() -> Table:
    """Le paramètre non observable, et le seuil qu'il déplace."""
    rows = []
    for nu in NU_GRILLE:
        ligne = [num(nu, 2), num(100 * ecart_type_implicite(nu), 2)]
        for m in (0.90, 1.00, 1.10):
            ligne.append(num(derive_equilibre(Ligne(-1.0, m, 90.0), nu), 3,
                             signed=True))
        ligne.append(num(_resume(simuler_vendeur(0.90, 90.0, nu)).taux * 100,
                         1))
        rows.append(ligne)
    return Table(
        key="vg_volofvol",
        caption="La volatilité de la volatilité, qu'on ne mesure pas ici, et le seuil qu'elle fixe",
        headers=["Volatilité de la volatilité (par an)",
                 "Écart-type mensuel de l'implicite (points)",
                 "Seuil sur l'aile basse", "à la monnaie",
                 "sur l'aile haute", "Fréquence de gain de l'aile basse (%)"],
        rows=rows,
        note="Le seuil croît comme le **carré** de la volatilité de la "
             "volatilité, ce qui est la seule façon dont un paramètre de "
             "second ordre peut entrer. Doubler la vol de vol quadruple ce "
             "qu'il faut d'implicite en baisse pour ne rien gagner. La "
             "colonne du milieu reste nulle à toutes les lignes, et c'est le "
             "fait de la table : **à la monnaie il n'y a pas de seuil**, "
             "parce que la courbure y change de signe. Un livre qui compense "
             "une aile par une position à la monnaie compense donc un seuil "
             "par un zéro. La dernière colonne rappelle que la fréquence de "
             "gain, elle, ne bouge pas du tout : elle vaut un demi à toutes "
             "les lignes, parce que le prix d'une option est monotone en "
             "volatilité et qu'un vendeur gagne exactement quand l'implicite "
             "baisse. *Aucune fréquence de gain ne renseigne ici sur quoi que "
             "ce soit*, et c'est la troisième fois que ce document le "
             "rencontre.",
    )


# ---------------------------------------------------------------------------
# VI. Ce qu'il faudrait pour établir une prime de volatilité
# ---------------------------------------------------------------------------


#: Excès de baisse d'implicite balayés, en points par mois **au-delà du
#: seuil**. C'est la seule définition honnête d'un avantage ici : la baisse
#: qui ramène l'espérance à zéro n'est pas un avantage, c'est un péage.
EXCES: tuple[float, ...] = (0.25, 0.50, 1.00, 2.00)

Z_95 = 1.959963984540054
PERIODES_AN = 12.0


@dataclass(frozen=True)
class Campagne:
    exces: float
    moyenne: float
    ecart_type: float
    taux: float
    periodes: float
    annees: float


@lru_cache(maxsize=32)
def campagne(exces: float, moneyness: float = 0.90,
             jours_option: float = 90.0, nu: float = NU_REF) -> Campagne:
    """Un vendeur qui a un vrai avantage, au-delà du seuil de sa position."""
    seuil = derive_equilibre_exacte(moneyness, jours_option, nu)
    r = _resume(simuler_vendeur(moneyness, jours_option, nu, seuil - exces))
    n = (Z_95 * r.ecart_type / r.moyenne) ** 2 if r.moyenne > 0 else math.inf
    return Campagne(exces, r.moyenne, r.ecart_type, r.taux, n,
                    n / PERIODES_AN)


def concentration(vals, part: float) -> float:
    """La part de la perte totale portée par les `part` pires mois.

    Le guide écrit que les pertes d'un vendeur de véga sont concentrées. Cela
    se mesure, et se compare : sous une loi symétrique de même écart-type, la
    même fraction porte une part plus petite, et l'écart entre les deux est
    ce que le mot « concentré » veut dire.
    """
    pertes = sorted(x for x in vals if x < 0.0)
    if not pertes:
        return 0.0
    total = sum(pertes)
    k = max(1, int(round(part * len(vals))))
    return sum(pertes[:k]) / total


@lru_cache(maxsize=4)
def concentration_temoin(part: float, n: int = 20000,
                         seed: int = SEED + 5) -> float:
    """La même part, sous une loi normale de même écart-type — le témoin."""
    r = _resume(simuler_vendeur(0.90, 90.0))
    rng = Rng(seed)
    vals = [r.ecart_type * rng.gauss() for _ in range(n)]
    return concentration(vals, part)


#: Fractions de mois balayées pour la concentration des pertes.
PARTS: tuple[float, ...] = (0.01, 0.02, 0.05, 0.10, 0.25, 0.50)


def table_loi() -> Table:
    """La loi du vendeur, et le mot « concentré » passé à la mesure."""
    vals = simuler_vendeur(0.90, 90.0)
    r = _resume(vals)
    rows = []
    for part in PARTS:
        rows.append([
            num(100 * part, 0),
            num(100 * concentration(vals, part), 1),
            num(100 * concentration_temoin(part), 1),
            num(100 * (concentration(vals, part)
                       - concentration_temoin(part)), 1, signed=True),
        ])
    return Table(
        key="vg_loi",
        caption="Les pertes d'un vendeur de véga, et ce que « concentré » veut dire",
        headers=["Part des mois (%)", "Part des pertes qu'ils portent (%)",
                 "Sous une loi normale de même écart-type (%)",
                 "Écart (points)"],
        rows=rows,
        note="Le vendeur mesuré ici gagne exactement une fois sur deux — le "
             "prix d'une option est monotone en volatilité — et perd en "
             "moyenne " + num(abs(r.moyenne), 3) + " point d'indice par "
             "mois, ce que la courbure lui prend. Le guide ajoute que ses "
             "pertes sont **concentrées**, et la table passe ce mot à la "
             "mesure : les cinq pour cent de pires mois portent "
             + num(100 * concentration(vals, 0.05), 1) + " % des pertes, "
             "contre " + num(100 * concentration_temoin(0.05), 1) + " % sous "
             "une loi normale de même dispersion. *L'écart est d'un point, et "
             "c'est le résultat de la table* : sous une variation "
             "d'implicite gaussienne, la concentration d'un vendeur de véga "
             "est celle d'une gaussienne. Elle ne vient donc pas de la "
             "position — elle vient de la loi de la variation d'implicite, "
             "que ce dépôt ne peut pas observer. La phrase du guide est "
             "vraie, et elle ne parle pas du véga : *elle parle de la queue "
             "de la volatilité implicite, et c'est là qu'il faudrait la "
             "mesurer.*",
    )


def table_preuve() -> Table:
    rows = []
    for e in EXCES:
        c = campagne(e)
        rows.append([
            num(e, 2),
            num(c.moyenne, 4),
            num(c.ecart_type, 3),
            num(c.moyenne / c.ecart_type, 4),
            num(100 * c.taux, 1),
            num(c.periodes, 0),
            num(c.annees, 1),
        ])
    return Table(
        key="vg_preuve",
        caption="Combien de mois pour établir un portage de volatilité",
        headers=["Avantage au-delà du seuil (points par mois)",
                 "Espérance (points d'indice)", "Dispersion",
                 "Rapport signal sur bruit", "Fréquence de gain (%)",
                 "Mois requis", "Années"],
        rows=rows,
        note="L'avantage se compte **au-delà du seuil** de la position, et "
             "c'est la seule définition honnête : la baisse d'implicite qui "
             "ramène l'espérance à zéro n'est pas un avantage, c'est un "
             "péage, et un vendeur qui l'encaisse croit gagner ce qu'il ne "
             "fait que rendre. La colonne des années se lit à côté de celles "
             "des trois parties précédentes — quatre cent soixante-quatorze "
             "décisions pour une géométrie intrajournalière, cinquante-cinq "
             "expirations pour un point de prime de variance — et elle dit "
             "la même chose une quatrième fois. La fréquence de gain, elle, "
             "monte à peine : *un vendeur qui a un avantage réel ne le voit "
             "pas passer dans son taux de réussite*, parce que ce taux est "
             "gouverné par le signe d'une variation d'implicite et non par "
             "son espérance.",
    )


# ---------------------------------------------------------------------------
# VII. Le décompte
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Affirmation:
    enonce: str
    grandeur: str
    mesure: str


def affirmations() -> tuple[Affirmation, ...]:
    k_opt, e_opt = kappa_minimax()
    return (
        Affirmation(
            "Le véga croît en racine du temps : un an vaut 5,5 fois deux "
            "semaines",
            "l'horloge",
            "la racine tient, le nombre non : " + num(rapport_de_tenors(), 2)),
        Affirmation(
            "Le véga culmine à la monnaie, en colline là où le gamma est une "
            "pointe",
            "rien",
            "les deux pics ont la même largeur à un pour cent près ; c'est la "
            "hauteur qui s'inverse"),
        Affirmation(
            "La forme fermée est par unité de volatilité, les systèmes cotent "
            "par point",
            "le risque",
            "un facteur cent, et c'est la seule erreur de la série qui en "
            "coûte deux ordres"),
        Affirmation(
            "Un livre à véga net nul peut perdre lourdement",
            "le risque",
            num(abs(pl_livre(livre_peau(), mode_peau, 10.0)), 2)
            + " points d'indice sur un livre neutre"),
        Affirmation(
            "La surface a trois modes indépendants, et il faut le véga par "
            "seau",
            "le risque",
            "chaque livre est aveugle au mode de l'autre, mesuré"),
        Affirmation(
            "Le véga est quasi linéaire près de la monnaie et convexe dans "
            "les ailes",
            "le risque",
            "la bande vaut " + num(
                100 * largeur_de_bande(30.0 / JOURS_AN), 2)
            + " % du spot à trente jours"),
        Affirmation(
            "Pondérer chaque seau par la racine de trente sur T",
            "rien",
            "aucune vitesse de retour ne la fait tenir : "
            + num(100 * e_opt, 0) + " % d'écart au mieux"),
        Affirmation(
            "Vendre du véga est un portage : cela paie la plupart du temps",
            "la direction",
            "la fréquence vaut exactement un demi ; ce qui paie est la "
            "dérive, et elle se démontre"),
        Affirmation(
            "Le véga mesure la sensibilité à un paramètre supposé constant",
            "rien",
            "l'aveu de circularité, et le dépôt en porte une"),
    )


def compte_par_grandeur() -> dict[str, int]:
    out: dict[str, int] = {}
    for a in affirmations():
        out[a.grandeur] = out.get(a.grandeur, 0) + 1
    return out


def familles() -> tuple[tuple[str, int], ...]:
    """Les quatre parties d'options, comptées dans leurs propres modules."""
    return (("Gamma, partie XIX", len(nv.affirmations())),
            ("Delta, partie XX", len(G.confusions())),
            ("Thêta, partie XXI", len(th.affirmations())),
            ("Véga, partie XXII", len(affirmations())))


def table_reste() -> Table:
    rows = [[a.enonce, a.grandeur, a.mesure] for a in affirmations()]
    c = compte_par_grandeur()
    return Table(
        key="vg_reste",
        caption="Neuf affirmations de plus, et le décompte des quatre parties",
        headers=["L'affirmation", "Ce qu'elle déplace",
                 "Ce que la mesure en dit"],
        rows=rows,
        note="Le décompte se lit dans l'identité `E[R] = (µ·E[τ∧T] − c)/a` : "
             + num(c.get("le risque", 0), 0) + " affirmations déplacent le "
             "**risque**, " + num(c.get("l'horloge", 0), 0) + " l'horloge, "
             + num(c.get("rien", 0), 0) + " ne déplacent rien, et **une "
             "seule touche à la direction** — celle qui dit que vendre du "
             "véga paie la plupart du temps. La mesure la corrige : la "
             "fréquence vaut exactement un demi, parce que le prix d'une "
             "option est monotone en volatilité, et ce qui paie est une "
             "dérive qu'il faut établir. Sur les "
             + num(sum(n for _, n in familles()), 0) + " affirmations des "
             "quatre parties d'options, *aucune ne donne un sens* — et les "
             "trois qui prétendaient en donner un disaient toutes qu'il n'y "
             "en a pas.",
        wrap_cols=[0, 2],
    )


# ---------------------------------------------------------------------------
# Les quatre reliefs
# ---------------------------------------------------------------------------
#
# Les quatre listes d'axes sont écrites de façon que le **maximum tombe au coin
# du fond** : en projection isométrique le coin (0, 0) est le plus éloigné, et
# un relief qui monte vers l'horizon se lit ; l'ordre inverse pose le sommet au
# premier plan, où il paraît à la hauteur d'écran du coin lointain.

SURF_KAPPA: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0, 16.0, 32.0)
SURF_TENOR: tuple[float, ...] = (365.0, 180.0, 90.0, 60.0, 21.0, 7.0)

SURF_VOL: tuple[float, ...] = (0.60, 0.45, 0.35, 0.25, 0.18, 0.12)
SURF_ECHEANCE: tuple[float, ...] = (365.0, 180.0, 90.0, 45.0, 21.0, 7.0)

SURF_NU: tuple[float, ...] = (1.60, 1.20, 0.90, 0.70, 0.50, 0.35)
SURF_ECART: tuple[float, ...] = (0.30, 0.22, 0.16, 0.11, 0.06, 0.02)

SURF_EXCES: tuple[float, ...] = (0.20, 0.35, 0.60, 1.00, 1.60, 2.50)
SURF_NU_PREUVE: tuple[float, ...] = (1.60, 1.20, 0.90, 0.70, 0.50, 0.35)


@lru_cache(maxsize=2)
def surface_poids() -> tuple[tuple[float, ...], ...]:
    """L'écart relatif de la règle en racine, en vitesse de retour et en ténor."""
    return tuple(tuple(abs(poids_modele(j, k) / poids_regle(j) - 1.0)
                       for j in SURF_TENOR)
                 for k in SURF_KAPPA)


@lru_cache(maxsize=2)
def surface_bande() -> tuple[tuple[float, ...], ...]:
    """La largeur de la bande de courbure négative, en volatilité et échéance."""
    return tuple(tuple(largeur_de_bande(j / JOURS_AN, v) for j in SURF_ECHEANCE)
                 for v in SURF_VOL)


@lru_cache(maxsize=2)
def surface_seuil() -> tuple[tuple[float, ...], ...]:
    """Le seuil d'un vendeur, en vol de vol et en écart à la monnaie."""
    return tuple(tuple(abs(derive_equilibre(Ligne(-1.0, math.exp(-e), 90.0),
                                            nu))
                       for e in SURF_ECART)
                 for nu in SURF_NU)


@lru_cache(maxsize=2)
def surface_preuve() -> tuple[tuple[float, ...], ...]:
    """Les années requises, en avantage et en volatilité de la volatilité."""
    return tuple(tuple(min(2000.0, campagne(e, 0.90, 90.0, nu).annees)
                       for e in SURF_EXCES)
                 for nu in SURF_NU_PREUVE)


# ---------------------------------------------------------------------------
# Valeurs, tables, et exécution directe
# ---------------------------------------------------------------------------


def values() -> dict[str, str]:
    k_opt, e_opt = kappa_minimax()
    aile = Ligne(-1.0, 0.90, 90.0)
    lp = livre_peau()
    lc = livre_calendrier()
    r0 = _resume(simuler_vendeur(0.90, 90.0))
    return {
        "vg_rapport": num(rapport_de_tenors(), 2),
        "vg_rapport_annonce": num(RAPPORT_ANNONCE, 1),
        "vg_rapport_racine": num(math.sqrt(365.0 / 14.0), 2),
        "vg_pic_vega": num(100 * largeur_du_pic(30.0 / JOURS_AN), 1),
        "vg_pic_gamma": num(100 * largeur_du_pic_gamma(30.0 / JOURS_AN), 1),
        "vg_gv_semaine": num(nv.gamma(S_REF, S_REF, VOL_REF, 7.0 / JOURS_AN)
                             / vega(S_REF, S_REF, VOL_REF, 7.0 / JOURS_AN), 4),
        "vg_gv_an": num(nv.gamma(S_REF, S_REF, VOL_REF, 1.0)
                        / vega(S_REF, S_REF, VOL_REF, 1.0), 5),
        "vg_gv_facteur": num(nv.gamma(S_REF, S_REF, VOL_REF, 7.0 / JOURS_AN)
                             / vega(S_REF, S_REF, VOL_REF, 7.0 / JOURS_AN)
                             / (nv.gamma(S_REF, S_REF, VOL_REF, 1.0)
                                / vega(S_REF, S_REF, VOL_REF, 1.0)), 0),
        "vg_peau_niveau": num(abs(pl_livre(lp, mode_niveau, 10.0)), 3),
        "vg_peau_peau": num(abs(pl_livre(lp, mode_peau, 10.0)), 2),
        "vg_cal_terme": num(abs(pl_livre(lc, mode_terme, 10.0)), 2),
        "vg_kappa": num(k_opt, 2),
        "vg_demivie": num(JOURS_AN * math.log(2.0) / k_opt, 0),
        "vg_ecart_regle": num(100 * e_opt, 0),
        "vg_exposant_30": num(exposant_effectif(30.0, k_opt), 2),
        "vg_exposant_365": num(exposant_effectif(365.0, k_opt), 2),
        "vg_tenor_demi": num(tenor_de_l_exposant(0.5, k_opt), 0),
        "vg_bande_30": num(100 * largeur_de_bande(30.0 / JOURS_AN), 2),
        "vg_bande_365": num(100 * largeur_de_bande(1.0), 1),
        "vg_strikes_30": num(strikes_dans_la_bande(30.0 / JOURS_AN, 0.01), 2),
        "vg_seuil_aile": num(abs(derive_equilibre(aile)), 2),
        "vg_seuil_mesure": num(abs(derive_equilibre_exacte(0.90, 90.0)), 2),
        "vg_seuil_ecart": num(
            100 * (derive_equilibre_exacte(0.90, 90.0)
                   / derive_equilibre(aile) - 1.0), 0),
        "vg_taux": num(100 * r0.taux, 1),
        "vg_moyenne": num(r0.moyenne, 3, signed=True),
        "vg_nu": num(100 * NU_REF, 0),
        "vg_ecart_mensuel": num(100 * ecart_type_implicite(), 1),
        "vg_annees_1": num(campagne(1.0).annees, 1),
        "vg_annees_demi": num(campagne(0.5).annees, 1),
        "vg_taux_1": num(100 * campagne(1.0).taux, 1),
        "vg_affirmations": num(len(affirmations()), 0),
        "vg_total_options": num(sum(n for _, n in familles()), 0),
        "vg_tirages": num(20000, 0),
        "vg_periode": num(PERIODE, 0),
        "vg_conc5": num(100 * concentration(simuler_vendeur(0.90, 90.0),
                                            0.05), 0),
        "vg_conc5_temoin": num(100 * concentration_temoin(0.05), 0),
    }


def all_tables() -> dict[str, Table]:
    tables = [table_echelle(), table_modes(), table_ponderation(),
              table_kappa(), table_bande(), table_seuil(), table_volofvol(),
              table_loi(), table_preuve(), table_reste()]
    return {t.key: t for t in tables}


def main() -> None:
    for t in all_tables().values():
        print(t.to_text())
        print()
    for k, v in values().items():
        print(f"{k:22s} {v}")


if __name__ == "__main__":
    main()
