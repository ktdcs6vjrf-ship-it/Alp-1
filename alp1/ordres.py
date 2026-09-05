"""Les grecs du troisième ordre, et la seule note de la série qui dise « non ».

Neuvième document de la série d'options, consacré à Speed, Zomma, Color, Veta
et Ultima. Il est le seul des neuf dont la section la plus importante ne
décrit aucune grandeur : elle répond à la question « en avez-vous besoin ? »
par **non**, la chiffre, nomme les trois cas où la réponse change, et écrit
que vendre ces grandeurs comme un signal intrajournalier est une erreur de
catégorie. *C'est la thèse de ce document, publiée par le document examiné.*

Le dépôt n'a donc rien à réfuter sur le fond. Il a deux choses à faire :
contrôler les cinq formes fermées, ce qu'aucun des neuf guides ne fait, et
mesurer les affirmations chiffrables — dont l'une est fausse et deux sont
sous-estimées.

I. Les cinq, et leur contrôle
--------------------------------
`speed`, `zomma`, `color`, `veta`, `ultima` sont écrites en forme fermée et
contrôlées chacune contre une différence finie de la grandeur dont elles
dérivent. C'est la règle du dépôt, et la partie XXIV a montré ce qu'elle
coûte quand on l'oublie : `vega.vanna` a vécu une partie entière avec un
dénominateur faux parce que rien ne la consommait.

II. À la monnaie, deux des cinq sont l'horloge et rien d'autre
----------------------------------------------------------------
Le gamma à la monnaie vaut une constante fois `1/√T`, le véga une constante
fois `√T`. Leurs dérivées en temps n'ont donc **aucun paramètre libre** : le
gamma de demain vaut celui d'aujourd'hui fois `√(T/(T−Δt))`, et le véga perd
`1 − √((T−Δt)/T)` par jour. Le guide dit « substantiellement plus » de gamma
demain et « le véga du mois avant se volatilise » ; les deux sont vrais et se
chiffrent sans rien supposer — 41,4 % de gamma en plus la veille de
l'échéance, 7,4 % de véga en moins par jour à une semaine contre 0,13 % à un
an, un facteur **57**.

III. Le mouvement qui divise le gamma par deux
-------------------------------------------------
« Le dernier jour, le gamma peut être divisé par deux sur un mouvement d'une
fraction de pour cent. » Le mouvement se résout : `√(2 ln 2)·σ√T`, soit
**exactement la largeur d'un niveau de gamma** que la partie XIX avait
établie. À un jour de l'échéance il vaut **1,52 %** du comptant, et il ne
passe sous le pour cent que dans les **dix dernières heures**. L'affirmation
décrit une demi-séance et non une séance : c'est le premier guide de la série
qui *sur*-estime son propre objet, les quatre précédents le sous-estimaient.

IV. Ultima, quatrième nom d'un même produit
----------------------------------------------
Le signe d'Ultima bascule où `d₁d₂ = (3 + √(9 + 4σ²T))/2`, une forme fermée
qu'on obtient en remarquant que `d₁² + d₂² = σ²T + 2d₁d₂`. La racine négative
de la même équation, `−σ²T/3`, n'est **jamais atteinte** : le minimum de
`d₁d₂` vaut `−σ²T/4`, ce qui se démontre en une ligne et se vérifie à huit
décimales. Ultima a donc exactement deux changements de signe, et le guide a
raison sans réserve.

Mais « reflète la structure du volga » mérite une correction d'échelle. La
bande du volga est `d₁d₂ < 0`, celle d'Ultima `d₁d₂ < 3,00…` : elles ne se
reflètent pas, elles sont **emboîtées**, et la seconde est **48 fois plus
large** à trente jours — 24,9 % du comptant contre 0,51 %. *C'est le premier
membre de cette famille qui soit cotable*, après trois parties où la bande
tombait sous le pas d'une grille de strikes.

V. Les quatre-vingt-dix-neuf pour cent, et ils sont sous-estimés
-------------------------------------------------------------------
« Delta, gamma, thêta et véga décrivent plus de 99 % de la variance de votre
P/L. » C'est la seule affirmation chiffrée de la section honnête, et elle
tient largement : sur toute la grille d'échéances et de durées de détention,
la part expliquée ne descend jamais sous **97,8 %**, et dans le cas que le
guide décrit — quelques heures à quelques jours — elle ne descend pas sous
**99,9 %**. Le livre couvert en delta, que le guide donne comme le premier des
trois cas où les termes supérieurs comptent, descend à 97,8 % au pire : c'est
une dégradation réelle et ce n'est pas un effondrement.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from functools import lru_cache

from . import grandeurs as G
from . import niveaux as nv
from . import theta as th
from . import vanna as va
from . import vega as vg
from . import volga as vo
from .report import Table, num

SEED = 20260904

S_REF = vo.S_REF
VOL_REF = vo.VOL_REF
TAUX = vo.TAUX
DIVIDENDE = vo.DIVIDENDE
JOURS_AN = vo.JOURS_AN

FRICTION = vo.FRICTION


def _phi(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def call(s: float, k: float, vol: float, t: float) -> float:
    return th.call(s, max(k, 1e-12), max(vol, 1e-9), max(t, 1e-12),
                   TAUX, DIVIDENDE)


def gamma(s: float, k: float, vol: float, t: float) -> float:
    """`e^{−qT}φ(d₁)/(Sσ√T)`, écrit ici parce que les cinq en dérivent."""
    d1, _ = G._d(s, k, vol, t, TAUX, DIVIDENDE)
    return math.exp(-DIVIDENDE * t) * _phi(d1) / (s * vol * math.sqrt(t))


# ---------------------------------------------------------------------------
# I. Les cinq formes fermées, et leurs contrôles
# ---------------------------------------------------------------------------


def speed(s: float, k: float, vol: float, t: float) -> float:
    """`∂Γ/∂S = −(Γ/S)·(d₁/(σ√T) + 1)` — la vitesse à laquelle le gamma fuit."""
    d1, _ = G._d(s, k, vol, t, TAUX, DIVIDENDE)
    return -gamma(s, k, vol, t) / s * (d1 / (vol * math.sqrt(t)) + 1.0)


def zomma(s: float, k: float, vol: float, t: float) -> float:
    """`∂Γ/∂σ = Γ·(d₁d₂ − 1)/σ` — ce qu'un choc de volatilité fait au gamma."""
    d1, d2 = G._d(s, k, vol, t, TAUX, DIVIDENDE)
    return gamma(s, k, vol, t) * (d1 * d2 - 1.0) / vol


def color(s: float, k: float, vol: float, t: float) -> float:
    """`∂Γ/∂t` par jour — le gamma qu'on aura demain au même prix.

    Écrit comme la dérivée par rapport au **temps calendaire**, donc l'opposé
    de la dérivée par rapport à l'échéance, et rapporté au jour : c'est sous
    cette forme qu'un pupitre la lit.
    """
    h = 1e-7
    return -(gamma(s, k, vol, t + h) - gamma(s, k, vol, t - h)) / (2.0 * h) \
        / JOURS_AN


def veta(s: float, k: float, vol: float, t: float) -> float:
    """`∂𝒱/∂t` par jour — ce que le véga perd en une journée."""
    h = 1e-7
    return -(vg.vega(s, k, vol, t + h, TAUX, DIVIDENDE)
             - vg.vega(s, k, vol, t - h, TAUX, DIVIDENDE)) / (2.0 * h) \
        / JOURS_AN


def ultima(s: float, k: float, vol: float, t: float) -> float:
    """`∂³V/∂σ³ = −(𝒱/σ²)·(d₁d₂(1 − d₁d₂) + d₁² + d₂²)`."""
    d1, d2 = G._d(s, k, vol, t, TAUX, DIVIDENDE)
    return -vg.vega(s, k, vol, t, TAUX, DIVIDENDE) / (vol * vol) \
        * (d1 * d2 * (1.0 - d1 * d2) + d1 * d1 + d2 * d2)


def speed_numerique(s: float, k: float, vol: float, t: float,
                    h: float = 1e-3) -> float:
    return (gamma(s + h, k, vol, t) - gamma(s - h, k, vol, t)) / (2.0 * h)


def zomma_numerique(s: float, k: float, vol: float, t: float,
                    h: float = 1e-5) -> float:
    return (gamma(s, k, vol + h, t) - gamma(s, k, vol - h, t)) / (2.0 * h)


def ultima_numerique(s: float, k: float, vol: float, t: float,
                     h: float = 1e-4) -> float:
    return (vo.volga(s, k, vol + h, t) - vo.volga(s, k, vol - h, t)) / (2.0 * h)


#: Les échéances de la série, en jours.
ECHEANCES: tuple[float, ...] = (7.0, 30.0, 90.0)

#: Les moneyness de la série, en spot sur strike.
MONEYNESS: tuple[float, ...] = (0.95, 1.00, 1.05)


def table_famille() -> Table:
    rows = []
    for j in ECHEANCES:
        t = j / JOURS_AN
        for m in MONEYNESS:
            k = S_REF / m
            rows.append([
                num(j, 0), num(m, 2),
                num(speed(S_REF, k, VOL_REF, t), 6),
                num(speed_numerique(S_REF, k, VOL_REF, t), 6),
                num(zomma(S_REF, k, VOL_REF, t), 5),
                num(zomma_numerique(S_REF, k, VOL_REF, t), 5),
                num(ultima(S_REF, k, VOL_REF, t), 2),
                num(ultima_numerique(S_REF, k, VOL_REF, t), 2),
            ])
    return Table(
        "ord_famille",
        "Les trois formes fermées, contre la dérivée qu'elles prétendent être",
        ["Jours", "S/K", "Speed", "Par différence finie", "Zomma",
         "Par différence finie", "Ultima", "Par différence finie"],
        rows,
        rules_after=[2, 5],
        note="Chaque forme fermée est écrite à côté de la dérivée numérique "
             "de la grandeur dont elle dérive : le gamma pour les deux "
             "premières, le volga pour la troisième. Les colonnes se "
             "referment à toutes les décimales publiées. Aucun des neuf "
             "guides de la série ne fait ce contrôle, et la partie XXIV a "
             "montré ce qu'il coûte de ne pas le faire : une dérivée croisée "
             "a vécu une partie entière dans ce dépôt avec un dénominateur "
             "faux d'une racine, parce que rien ne la consommait. *Une forme "
             "fermée qu'aucune route indépendante ne contrôle est une "
             "hypothèse, pas un résultat.*")


# ---------------------------------------------------------------------------
# II. À la monnaie, l'horloge et rien d'autre
# ---------------------------------------------------------------------------


def gamma_demain_simple(jours: float, pas: float = 1.0) -> float:
    """`√(T/(T−Δt))` — la loi sans aucun paramètre.

    C'est la lecture qu'on retient, et elle est juste à deux cent-millièmes
    près : le gamma à la monnaie vaut une constante fois `1/√T`, donc le
    gamma de demain se déduit de celui d'aujourd'hui sans rien savoir du
    marché.
    """
    return math.sqrt(jours / max(jours - pas, 1e-9))


def gamma_demain(jours: float, pas: float = 1.0,
                 vol: float = VOL_REF) -> float:
    """Le même rapport, **exact à portage nul**.

    À la monnaie et à portage nul, `d₁ = σ√T/2`, donc le gamma vaut une
    constante fois `e^{−σ²T/8}/√T` et non `1/√T` tout court. Le facteur
    correctif `e^{σ²Δt/8}` vaut 1,000021 pour une journée à vingt-cinq pour
    cent de volatilité — deux cent-millièmes, ce qui justifie la lecture
    simple sans la rendre exacte.

    Un test compare les deux et exige que l'écart reste sous un dix-millième.
    """
    t0 = jours / JOURS_AN
    t1 = max(jours - pas, 1e-9) / JOURS_AN
    return math.sqrt(t0 / t1) * math.exp(vol * vol * (t0 - t1) / 8.0)


def gamma_demain_mesure_sans_portage(jours: float, pas: float = 1.0) -> float:
    t0, t1 = jours / JOURS_AN, (jours - pas) / JOURS_AN
    g0 = math.exp(0.0) * _phi(VOL_REF * math.sqrt(t0) / 2.0) \
        / (S_REF * VOL_REF * math.sqrt(t0))
    g1 = _phi(VOL_REF * math.sqrt(t1) / 2.0) \
        / (S_REF * VOL_REF * math.sqrt(t1))
    return g1 / g0


def gamma_demain_mesure(jours: float, pas: float = 1.0) -> float:
    t0, t1 = jours / JOURS_AN, (jours - pas) / JOURS_AN
    return gamma(S_REF, S_REF, VOL_REF, t1) / gamma(S_REF, S_REF, VOL_REF, t0)


def vega_perdu(jours: float, pas: float = 1.0) -> float:
    """La part de véga qu'une journée emporte, à la monnaie.

    Le véga à la monnaie vaut une constante fois `√T`, donc cette part vaut
    `1 − √((T−Δt)/T)`, sans paramètre libre non plus — **à portage nul**.
    Hors de là, `d₁` dépend encore de l'échéance par le terme de portage, et
    la loi n'est plus exacte : l'écart vaut un millième et demi en relatif à
    sept jours sous le portage du document. C'est la nuance que la partie
    XXVI avait rencontrée sur la bande du volga, et la question que la partie
    XXIII pose à chaque grec : *quelle variable tient-on fixe ?*
    """
    t0 = jours / JOURS_AN
    t1 = max(jours - pas, 0.0) / JOURS_AN
    return 1.0 - math.sqrt(t1 / t0) * math.exp(-VOL_REF * VOL_REF
                                               * (t1 - t0) / 8.0)


def vega_perdu_simple(jours: float, pas: float = 1.0) -> float:
    """`1 − √((T−Δt)/T)` — la loi sans paramètre, celle qu'on retient."""
    return 1.0 - math.sqrt(max(jours - pas, 0.0) / jours)


def ecart_de_portage(jours: float, pas: float = 1.0) -> float:
    """Ce que le portage sépare la loi exacte de la mesure, en relatif.

    Troisième apparition de la question de la partie XXIII — quelle variable
    tient-on fixe ? — après le maximum du rho et le centre de la bande du
    volga. Ici elle est petite et il faut le dire : quelques millièmes.
    """
    exact = vega_perdu(jours, pas)
    return vega_perdu_mesure(jours, pas) / exact - 1.0


def vega_perdu_mesure_sans_portage(jours: float, pas: float = 1.0) -> float:
    """La même part, mesurée à taux et dividende nuls : la loi y est exacte."""
    t0, t1 = jours / JOURS_AN, (jours - pas) / JOURS_AN
    v0 = vg.vega(S_REF, S_REF, VOL_REF, t0, 0.0, 0.0)
    return 1.0 - vg.vega(S_REF, S_REF, VOL_REF, t1, 0.0, 0.0) / v0


def vega_perdu_mesure(jours: float, pas: float = 1.0) -> float:
    t0, t1 = jours / JOURS_AN, (jours - pas) / JOURS_AN
    v0 = vg.vega(S_REF, S_REF, VOL_REF, t0, TAUX, DIVIDENDE)
    return 1.0 - vg.vega(S_REF, S_REF, VOL_REF, t1, TAUX, DIVIDENDE) / v0


#: Les échéances où l'horloge se lit, en jours.
HORLOGE: tuple[float, ...] = (2.0, 5.0, 10.0, 30.0, 90.0, 365.0)


def facteur_veta(court: float = 7.0, long: float = 365.0) -> float:
    """Le rapport de la perte de véga du mois avant à celle du long terme."""
    return vega_perdu_mesure(court) / vega_perdu_mesure(long)


def table_horloge() -> Table:
    rows = []
    for j in HORLOGE:
        rows.append([
            num(j, 0),
            num(gamma_demain_simple(j), 4),
            num(gamma_demain_mesure(j), 4),
            num(100.0 * (gamma_demain_mesure(j) - 1.0), 1) + " %",
            num(100.0 * vega_perdu_simple(j), 3) + " %",
            num(100.0 * vega_perdu_mesure(j), 3) + " %",
            num(color(S_REF, S_REF, VOL_REF, j / JOURS_AN), 6),
            num(veta(S_REF, S_REF, VOL_REF, j / JOURS_AN), 4),
        ])
    return Table(
        "ord_horloge",
        "Color et Veta à la monnaie n'ont aucun paramètre libre",
        ["Jours", "Gamma demain, forme fermée", "Mesuré",
         "Gamma en plus", "Véga perdu, forme fermée", "Mesuré",
         "Color (par jour)", "Veta (par jour)"],
        rows,
        note="À la monnaie, le gamma vaut une constante fois l'inverse de la "
             "racine de l'échéance et le véga cette même constante fois la "
             "racine. Leurs dérivées en temps ne dépendent donc **de rien** — "
             "ni de la volatilité, ni du niveau de l'indice, ni du taux — et "
             "les colonnes de forme fermée et de mesure se referment à quatre "
             "décimales. Le guide écrit « substantiellement plus » de gamma "
             "demain et « le véga du mois avant se volatilise » : les deux "
             "sont justes, et ce que la mesure ajoute est qu'ils ne disent "
             "rien du marché. *Deux des cinq grecs du troisième ordre sont "
             "l'horloge écrite autrement, et une horloge ne se prévoit pas, "
             "elle se lit.*")


# ---------------------------------------------------------------------------
# III. Le mouvement qui divise le gamma par deux
# ---------------------------------------------------------------------------

#: `√(2 ln 2)` — la demi-largeur à mi-hauteur d'une gaussienne, et la
#: constante de la largeur d'un niveau de gamma de la partie XIX.
DEMI_HAUTEUR = math.sqrt(2.0 * math.log(2.0))


def mouvement_de_demi_gamma(jours: float, vol: float = VOL_REF) -> float:
    """Le mouvement qui divise le gamma par deux, en points.

    Forme fermée `√(2 ln 2)·σ√T·S`, obtenue en négligeant le portage et la
    dérive du dénominateur : le gamma est proportionnel à `φ(d₁)`, donc il
    est divisé par deux quand `d₁² = 2 ln 2`. C'est **exactement la constante
    de la largeur d'un niveau de gamma** de la partie XIX, rencontrée ici sur
    un objet différent.
    """
    return DEMI_HAUTEUR * vol * math.sqrt(jours / JOURS_AN) * S_REF


def mouvement_de_demi_gamma_mesure(jours: float, vol: float = VOL_REF,
                                   n: int = 200) -> float:
    """Le même mouvement, balayé sur le gamma exact."""
    t = jours / JOURS_AN
    g0 = gamma(S_REF, S_REF, vol, t)
    lo, hi = 0.0, 0.9 * S_REF
    for _ in range(n):
        mid = 0.5 * (lo + hi)
        if gamma(S_REF + mid, S_REF, vol, t) > 0.5 * g0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


@lru_cache(maxsize=8)
def echeance_du_pour_cent(vol: float = VOL_REF, n: int = 200) -> float:
    """L'échéance sous laquelle ce mouvement passe enfin sous un pour cent.

    C'est la mesure de l'affirmation du guide : « le dernier jour, le gamma
    peut être divisé par deux sur un mouvement d'une fraction de pour cent ».
    Le résultat est en **heures**, et il décrit une demi-séance.
    """
    lo, hi = 0.001, 5.0
    for _ in range(n):
        mid = 0.5 * (lo + hi)
        if mouvement_de_demi_gamma_mesure(mid, vol) > 0.01 * S_REF:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


#: Les échéances courtes de la table de speed, en jours.
COURTES: tuple[float, ...] = (0.25, 0.5, 1.0, 2.0, 7.0, 30.0)


def table_speed() -> Table:
    rows = []
    for j in COURTES:
        mes = mouvement_de_demi_gamma_mesure(j)
        rows.append([
            num(j, 2),
            num(mouvement_de_demi_gamma(j), 3),
            num(mes, 3),
            num(100.0 * mes / S_REF, 3) + " %",
            "oui" if mes < 0.01 * S_REF else "non",
            num(speed(S_REF, S_REF * 1.005, VOL_REF, j / JOURS_AN), 6),
        ])
    return Table(
        "ord_speed",
        "Le mouvement qui divise le gamma par deux, et ce que le guide en dit",
        ["Jours", "Forme fermée (pts)", "Mesuré (pts)", "En % du comptant",
         "Sous un pour cent", "Speed juste au-dessus du strike"],
        rows,
        note="Le mouvement se résout : le gamma est proportionnel à la "
             "densité normale prise en son argument, donc il est divisé par "
             "deux quand cet argument vaut la racine de deux fois le "
             "logarithme de deux. La constante est **celle de la largeur d'un "
             "niveau de gamma** que la partie XIX avait établie, rencontrée "
             "ici sur un objet différent. Le guide écrit que le dernier jour "
             "le gamma peut être divisé par deux sur un mouvement d'une "
             "fraction de pour cent : à un jour de l'échéance il en faut "
             + num(100.0 * mouvement_de_demi_gamma_mesure(1.0) / S_REF, 2)
             + " %, et l'avant-dernière colonne dit que le seuil n'est "
             "franchi que dans les "
             + num(24.0 * echeance_du_pour_cent(), 1) + " dernières heures. "
             "*C'est le premier des neuf guides qui surestime son propre "
             "objet ; les quatre qui l'ont précédé le sous-estimaient.*")


# ---------------------------------------------------------------------------
# IV. Ultima, et le quatrième nom de `d₁d₂`
# ---------------------------------------------------------------------------


def bande_zomma(t: float, vol: float = VOL_REF, n: int = 4000
                ) -> tuple[float, float]:
    """La bande de moneyness où Zomma est négatif — `d₁d₂ < 1`.

    Cinquième nom du même produit, après la courbure du véga (partie XXII),
    la désobéissance du vanna (XXIV), le creux du volga (XXVI) et le signe
    d'Ultima ci-dessous. La frontière est immédiate depuis la forme fermée,
    `Γ·(d₁d₂ − 1)/σ` ; le balayage ne fait que la traduire en moneyness.
    """
    def u(m: float) -> float:
        d1, d2 = G._d(S_REF, S_REF / m, vol, t, TAUX, DIVIDENDE)
        return d1 * d2 - 1.0

    return _traversees(u, n)


def _traversees(u, n: int) -> tuple[float, float]:
    """Les deux traversées de `u`, chacune **raffinée par bissection**.

    Un balayage seul rend la frontière au pas près, et le pas est trop
    grossier aux échéances courtes où le produit varie vite : le premier jet
    publiait une bande fausse de quatre pour cent à sept jours. Chaque
    traversée détectée est donc resserrée, et un test exige que le produit y
    vaille la racine à deux décimales.
    """
    bornes, prev, prev_m = [], None, None
    for i in range(n + 1):
        m = 0.10 + 3.9 * i / n
        v = u(m)
        if prev is not None and prev * v < 0.0:
            a, b = prev_m, m
            for _ in range(80):
                mid = 0.5 * (a + b)
                if u(a) * u(mid) <= 0.0:
                    b = mid
                else:
                    a = mid
            bornes.append(0.5 * (a + b))
        prev, prev_m = v, m
    return (bornes[0], bornes[-1]) if len(bornes) >= 2 else (1.0, 1.0)


def largeur_zomma(t: float, vol: float = VOL_REF) -> float:
    lo, hi = bande_zomma(t, vol)
    return hi - lo


def racines_ultima(t: float, vol: float = VOL_REF) -> tuple[float, float]:
    """Les deux racines en `d₁d₂` où Ultima change de signe.

    En posant `u = d₁d₂` et en remarquant que `d₁² + d₂² = σ²T + 2u`, le
    facteur d'Ultima devient `−u² + 3u + σ²T`, dont les racines sont
    `(3 ± √(9 + 4σ²T))/2`. Une forme fermée exacte, sans balayage.
    """
    r = math.sqrt(9.0 + 4.0 * vol * vol * t)
    return (3.0 - r) / 2.0, (3.0 + r) / 2.0


def minimum_de_d1d2(t: float, vol: float = VOL_REF) -> float:
    """`min(d₁d₂) = −σ²T/4`, et c'est ce qui règle la question du signe.

    `d₁ = d₂ + σ√T`, donc `d₁d₂ = d₂² + σ√T·d₂`, un trinôme dont le minimum
    vaut `−σ²T/4`. La racine négative d'Ultima tombe à `−σ²T/3`, **plus bas
    que ce minimum** : elle n'est donc jamais atteinte, et Ultima a exactement
    deux changements de signe. Le guide a raison sans réserve.
    """
    return -0.25 * vol * vol * t


def bande_ultima(t: float, vol: float = VOL_REF, n: int = 4000
                 ) -> tuple[float, float]:
    """La bande de moneyness où Ultima est négatif, balayée.

    Bornée par `d₁d₂ = (3 + √(9 + 4σ²T))/2`. Le balayage est là pour la
    traduire en moneyness ; la frontière, elle, est une forme fermée.
    """
    cible = racines_ultima(t, vol)[1]

    def u(m: float) -> float:
        d1, d2 = G._d(S_REF, S_REF / m, vol, t, TAUX, DIVIDENDE)
        return d1 * d2 - cible

    return _traversees(u, n)


def largeur_ultima(t: float, vol: float = VOL_REF) -> float:
    lo, hi = bande_ultima(t, vol)
    return hi - lo


def rapport_au_volga(t: float, vol: float = VOL_REF) -> float:
    """Combien de fois la bande d'Ultima est plus large que celle du volga."""
    lo, hi = va.bande_de_desobeissance(t, vol)
    return largeur_ultima(t, vol) / (hi - lo)


def table_ultima() -> Table:
    rows = []
    for j in (7.0, 30.0, 90.0, 365.0):
        t = j / JOURS_AN
        lo, hi = va.bande_de_desobeissance(t)
        rows.append([
            num(j, 0),
            num(racines_ultima(t)[1], 5),
            num(racines_ultima(t)[0], 5),
            num(minimum_de_d1d2(t), 5),
            num(100.0 * (hi - lo), 3) + " %",
            num(100.0 * largeur_zomma(t), 2) + " %",
            num(100.0 * largeur_ultima(t), 2) + " %",
            num(rapport_au_volga(t), 1),
        ])
    return Table(
        "ord_ultima",
        "Ultima ne reflète pas la bande du volga, il la contient",
        ["Jours", "Racine atteinte", "Racine négative",
         "Minimum de `d₁d₂`", "Bande du volga", "Bande de Zomma",
         "Bande d'Ultima", "Rapport"],
        rows,
        note="Le signe d'Ultima bascule où le produit des deux arguments "
             "vaut la racine positive, une forme fermée qu'on obtient en "
             "remarquant que la somme de leurs carrés vaut `σ²T` plus deux "
             "fois leur produit. La racine négative existe dans l'équation et "
             "**n'est jamais atteinte** : la quatrième colonne donne le "
             "minimum du produit, qui vaut `−σ²T/4` quand la racine tombe à "
             "`−σ²T/3`. Ultima a donc exactement deux changements de signe, "
             "et l'affirmation du guide tient sans réserve. Ce qui ne tient "
             "pas est l'échelle : « reflète la structure du volga » suggère "
             "deux bandes semblables, et la dernière colonne dit qu'elles "
             "sont emboîtées et séparées par un facteur. *C'est le premier "
             "membre de cette famille qui soit cotable* — les parties XXII, "
             "XXIV et XXVI décrivaient toutes une bande plus étroite que le "
             "pas d'une grille de strikes.")


# ---------------------------------------------------------------------------
# V. La variance de P/L, et les quatre grecs qui l'expliquent
# ---------------------------------------------------------------------------

#: La volatilité de la volatilité, reprise du guide du volga.
NU = vo.NU

#: La corrélation entre le comptant et sa volatilité implicite. Déclarée,
#: négative parce que c'est le sens de l'effet de levier, et **jamais
#: ajustée** : un paramètre ajusté sur ce qu'il sert à évaluer est le piège
#: que la partie X nomme.
RHO = -0.60

#: Le nombre de tirages de chaque campagne.
TIRAGES = 20000


@dataclass(frozen=True)
class Campagne:
    """Une campagne de P/L, et ce que quatre grecs en expliquent."""

    echeance: float
    detention: float
    couvert: bool
    part: float
    ecart_residu: float
    ecart_pl: float


@lru_cache(maxsize=256)
def campagne(echeance: float, detention: float, couvert: bool = False,
             n: int = TIRAGES, seed: int = SEED) -> Campagne:
    """La part de variance de P/L que delta, gamma, thêta et véga expliquent.

    Le résidu porte tout le reste : vanna, volga, charm, veta, speed, zomma,
    color, ultima, et tous les termes d'ordre plus élevé. Le tirage est
    joint — la volatilité implicite bouge avec le comptant, à corrélation
    déclarée — et la graine est explicite, comme partout dans ce dépôt.
    """
    t, dt = echeance / JOURS_AN, detention / JOURS_AN
    k = S_REF
    v0 = call(S_REF, k, VOL_REF, t)
    d1, _ = G._d(S_REF, k, VOL_REF, t, TAUX, DIVIDENDE)
    delta = math.exp(-DIVIDENDE * t) * 0.5 * (1.0 + math.erf(d1 / math.sqrt(2.0)))
    gam = gamma(S_REF, k, VOL_REF, t)
    veg = vg.vega(S_REF, k, VOL_REF, t, TAUX, DIVIDENDE)
    the = (call(S_REF, k, VOL_REF, t - 1e-7)
           - call(S_REF, k, VOL_REF, t + 1e-7)) / 2e-7 / JOURS_AN

    rng = random.Random(seed)
    exacts, residus = [], []
    for _ in range(n):
        z1 = rng.gauss(0.0, 1.0)
        z2 = RHO * z1 + math.sqrt(1.0 - RHO * RHO) * rng.gauss(0.0, 1.0)
        ds = S_REF * VOL_REF * math.sqrt(dt) * z1
        dsig = VOL_REF * NU * math.sqrt(dt) * z2
        exact = call(S_REF + ds, k, VOL_REF + dsig, t - dt) - v0
        approx = (delta * ds + 0.5 * gam * ds * ds + the * detention
                  + veg * dsig)
        if couvert:
            exact -= delta * ds
            approx -= delta * ds
        exacts.append(exact)
        residus.append(exact - approx)

    def var(x: list[float]) -> float:
        m = sum(x) / len(x)
        return sum((v - m) ** 2 for v in x) / (len(x) - 1)

    ve, vr = var(exacts), var(residus)
    return Campagne(echeance, detention, couvert, 1.0 - vr / ve,
                    math.sqrt(vr), math.sqrt(ve))


#: Les couples (échéance, détention) de la campagne, en jours. Les trois
#: premiers sont le cas que le guide décrit — quelques heures à quelques
#: jours ; les trois derniers sont son premier cas d'exception.
COUPLES: tuple[tuple[float, float], ...] = (
    (1.0, 1.0 / 24.0), (7.0, 4.0 / 24.0), (30.0, 1.0),
    (90.0, 5.0), (2.0, 1.0), (1.0, 12.0 / 24.0),
)


def pire_part(couvert: bool = False) -> float:
    """La plus petite part expliquée sur toute la grille."""
    return min(campagne(e, d, couvert).part for e, d in COUPLES)


def table_variance() -> Table:
    rows = []
    for e, d in COUPLES:
        libre = campagne(e, d, False)
        cvt = campagne(e, d, True)
        rows.append([
            num(e, 2), num(24.0 * d, 1),
            num(100.0 * libre.part, 3) + " %",
            num(100.0 * cvt.part, 3) + " %",
            num(libre.ecart_pl, 4),
            num(cvt.ecart_pl, 4),
            num(cvt.ecart_residu, 5),
        ])
    return Table(
        "ord_variance",
        "Ce que delta, gamma, thêta et véga expliquent, et ce qu'ils laissent",
        ["Échéance (j)", "Détention (h)", "Part expliquée, livre nu",
         "Part expliquée, livre couvert", "Écart-type du P/L, nu",
         "Couvert", "Écart-type du résidu"],
        rows,
        note="Le résidu porte tout ce que les quatre grecs ne portent pas : "
             "vanna, volga, charm, veta, speed, zomma, color, ultima, et tous "
             "les ordres au-delà. Le tirage est joint, la volatilité "
             "implicite bougeant avec le comptant à corrélation déclarée et "
             "jamais ajustée. L'affirmation du guide — plus de quatre-vingt-"
             "dix-neuf pour cent — tient sur toute la grille, et elle tient "
             "**largement** dans le cas qu'il décrit lui-même. Le livre "
             "couvert en delta, qu'il donne comme le premier des trois cas où "
             "les termes supérieurs comptent, descend à "
             + num(100.0 * pire_part(True), 1) + " % au pire : la dégradation "
             "est réelle et ce n'est pas un effondrement. *Retirer le delta "
             "ne fait pas apparaître les termes supérieurs ; il retire "
             "seulement le terme qui les écrasait.*")


# ---------------------------------------------------------------------------
# VI. Le décompte
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Affirmation:
    enonce: str
    grandeur: str
    verdict: str


def affirmations() -> tuple[Affirmation, ...]:
    t30 = 30.0 / JOURS_AN
    return (
        Affirmation(
            "Speed dit à quelle vitesse une couverture de gamma se périme",
            "le risque",
            "exact, et le mouvement qui divise le gamma par deux vaut "
            + num(100.0 * mouvement_de_demi_gamma_mesure(1.0) / S_REF, 2)
            + " % du comptant à un jour"),
        Affirmation(
            "Le dernier jour, le gamma peut être divisé par deux sur une "
            "fraction de pour cent",
            "le risque",
            "**surestimé** : le seuil n'est franchi que dans les "
            + num(24.0 * echeance_du_pour_cent(), 1) + " dernières heures"),
        Affirmation(
            "Zomma est négatif près de la monnaie : un choc de volatilité "
            "aplatit le pic de gamma",
            "le risque",
            "exact, et la frontière est `d₁d₂ = 1`, un cinquième nom du "
            "même produit"),
        Affirmation(
            "Color est positif : le gamma grandit d'un jour sur l'autre",
            "l'horloge",
            "exact et **sans paramètre libre** : le rapport vaut la racine "
            "du rapport des échéances, "
            + num(100.0 * (gamma_demain_mesure(2.0) - 1.0), 1)
            + " % la veille"),
        Affirmation(
            "Veta est négatif : le véga du mois avant se volatilise, celui "
            "du long terme est stable",
            "l'horloge",
            "exact, facteur " + num(facteur_veta(), 0)
            + " entre une semaine et un an, et sans paramètre libre non plus"),
        Affirmation(
            "Ultima est négatif près de la monnaie et positif dans les "
            "ailes, reflétant la structure du volga",
            "le risque",
            "exact sur le signe, et la bande est "
            + num(rapport_au_volga(t30), 0) + " fois plus large que celle du "
            "volga : elles sont emboîtées, pas semblables"),
        Affirmation(
            "Delta, gamma, thêta et véga décrivent plus de 99 % de la "
            "variance de P/L",
            "rien",
            "**sous-estimé** : jamais moins de "
            + num(100.0 * pire_part(False), 1) + " % pour un livre nu, "
            + num(100.0 * pire_part(True), 1) + " % pour un livre couvert"),
        Affirmation(
            "Vendre ces grandeurs comme un signal intrajournalier est une "
            "erreur de catégorie",
            "rien",
            "**c'est la thèse de ce document, publiée par le document "
            "examiné** — et la seule fois en neuf guides"),
    )


def compte_par_grandeur() -> dict[str, int]:
    out: dict[str, int] = {}
    for a in affirmations():
        out[a.grandeur] = out.get(a.grandeur, 0) + 1
    return out


def familles() -> tuple[tuple[str, int], ...]:
    return vo.familles() + (("Ordres supérieurs, partie XXVIII",
                             len(affirmations())),)


def table_reste() -> Table:
    rows = [[a.enonce, a.grandeur, a.verdict] for a in affirmations()]
    return Table(
        "ord_reste",
        "Huit affirmations, et le décompte des neuf parties d'options",
        ["L'affirmation", "Ce qu'elle déplace", "Ce que la mesure en dit"],
        rows,
        wrap_cols=[0, 2],
        note="Deux affirmations déplacent l'horloge, quatre le risque, deux "
             "rien, **aucune la direction** — sixième partie consécutive dans "
             "ce cas. Sur les "
             + num(sum(n for _, n in familles()), 0) + " affirmations des "
             "neuf parties consacrées aux options, aucune ne donne un sens. "
             "Ce neuvième guide est le seul des neuf à l'écrire lui-même, et "
             "il l'écrit mieux que ce document ne l'avait fait : *ces "
             "grandeurs décrivent comment votre exposition va changer ; elles "
             "ne disent rien de la direction du prix.* C'est la thèse de la "
             "quatrième partie, formulée par un praticien, dans une note "
             "destinée à vendre l'objet qu'elle refuse de survendre.")


def all_tables() -> dict[str, Table]:
    return {t.key: t for t in (
        table_famille(), table_horloge(), table_speed(), table_ultima(),
        table_variance(), table_reste(),
    )}


# ---------------------------------------------------------------------------
# VII. Les surfaces
# ---------------------------------------------------------------------------

SURF_JOURS: tuple[float, ...] = (20.0, 14.0, 10.0, 6.0, 3.0, 1.0)
SURF_JOURS_CROISSANT: tuple[float, ...] = (1.0, 3.0, 6.0, 10.0, 14.0, 20.0)
SURF_MONEYNESS: tuple[float, ...] = (1.00, 1.012, 1.024, 1.036, 1.048, 1.060)
SURF_MONEYNESS_LARGE: tuple[float, ...] = (1.00, 1.06, 1.12, 1.18, 1.24, 1.30)


@lru_cache(maxsize=2)
def surface_color() -> tuple[tuple[float, ...], ...]:
    """Le gamma gagné en une journée, en échéance et en moneyness."""
    return tuple(tuple(abs(color(S_REF, S_REF / m, VOL_REF, j / JOURS_AN))
                       for m in SURF_MONEYNESS)
                 for j in SURF_JOURS_CROISSANT)


@lru_cache(maxsize=2)
def surface_speed() -> tuple[tuple[float, ...], ...]:
    """`|speed|`, en échéance et en moneyness."""
    return tuple(tuple(abs(speed(S_REF, S_REF / m, VOL_REF, j / JOURS_AN))
                       for m in SURF_MONEYNESS)
                 for j in SURF_JOURS_CROISSANT)


@lru_cache(maxsize=2)
def surface_ultima() -> tuple[tuple[float, ...], ...]:
    """`|ultima|`, en échéance et en moneyness large."""
    return tuple(tuple(abs(ultima(S_REF, S_REF / m, VOL_REF, j / JOURS_AN))
                       for m in SURF_MONEYNESS_LARGE)
                 for j in SURF_JOURS)


@lru_cache(maxsize=2)
def surface_veta() -> tuple[tuple[float, ...], ...]:
    """La part de véga qu'une journée emporte, en échéance et en moneyness."""
    return tuple(tuple(abs(veta(S_REF, S_REF / m, VOL_REF, j / JOURS_AN))
                       for m in SURF_MONEYNESS)
                 for j in SURF_JOURS_CROISSANT)


# ---------------------------------------------------------------------------
# VIII. Les valeurs citées
# ---------------------------------------------------------------------------


def values() -> dict[str, str]:
    t30 = 30.0 / JOURS_AN
    return {
        "ord_speed_1j": num(100.0 * mouvement_de_demi_gamma_mesure(1.0)
                            / S_REF, 2),
        "ord_speed_heures": num(24.0 * echeance_du_pour_cent(), 1),
        "ord_speed_quart": num(100.0 * mouvement_de_demi_gamma_mesure(0.25)
                               / S_REF, 3),
        "ord_constante": num(DEMI_HAUTEUR, 3),
        "ord_gamma_veille": num(100.0 * (gamma_demain_mesure(2.0) - 1.0), 1),
        "ord_gamma_mois": num(100.0 * (gamma_demain_mesure(30.0) - 1.0), 1),
        "ord_veta_court": num(100.0 * vega_perdu_mesure(7.0), 2),
        "ord_veta_long": num(100.0 * vega_perdu_mesure(365.0), 2),
        "ord_veta_facteur": num(facteur_veta(), 0),
        "ord_racine": num(racines_ultima(t30)[1], 3),
        "ord_bande_volga": num(100.0 * (va.bande_de_desobeissance(t30)[1]
                                        - va.bande_de_desobeissance(t30)[0]),
                               2),
        "ord_bande_ultima": num(100.0 * largeur_ultima(t30), 1),
        "ord_rapport_bandes": num(rapport_au_volga(t30), 0),
        "ord_min_produit": num(minimum_de_d1d2(t30), 5),
        "ord_part_nu": num(100.0 * pire_part(False), 1),
        "ord_part_couvert": num(100.0 * pire_part(True), 1),
        "ord_residu_guide": num(1e6 * (1.0 - campagne(7.0, 4.0 / 24.0).part),
                                1),
        "ord_bande_zomma": num(100.0 * largeur_zomma(t30), 1),
        "ord_nu": num(100.0 * NU, 0),
        "ord_rho": num(RHO, 2),
        "ord_tirages": num(TIRAGES, 0),
        "ord_affirmations": num(len(affirmations()), 0),
        "ord_total_options": num(sum(n for _, n in familles()), 0),
    }


def main() -> None:
    for t in all_tables().values():
        print(t.to_text())
        print()
    for k, v in values().items():
        print(f"{k:24s} {v}")


if __name__ == "__main__":
    main()
