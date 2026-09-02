"""Le loyer de la convexité, et ce qu'il n'achète pas.

Cette partie ferme la série d'options dont les parties XIX et XX ont examiné
le gamma et le delta. Le troisième document est consacré au thêta, et il
s'ouvre sur la phrase la plus juste des trois :

    *Le thêta est le loyer de la convexité, et les deux ne se séparent pas.*

Le dépôt souscrit, et va là où le guide s'arrête. Car si les deux ne se
séparent pas, alors le vendeur d'option n'encaisse pas un revenu : il
encaisse une **fréquence**. C'est la forme que ce document connaît par cœur —
la confirmation qui ne déplace pas l'espérance mais divise l'échantillon, le
niveau qui « tient » 94 % du temps sur du bruit pur, la cible touchée 62 %
du temps et gagnante 6,6 % — et elle a ici sa forme la plus pure, parce
qu'elle se calcule en une ligne et vaut une constante universelle.

I. Le loyer, et ses trois termes
--------------------------------
Le thêta d'un call porte trois effets empilés, et les confondre est la source
de la plupart des légendes :

* la décroissance de la valeur temps, `−Se^{−qT}φ(d₁)σ/2√T`, toujours
  négative pour une position longue et **proportionnelle au gamma** ;
* l'intérêt sur le strike, `−rKe^{−rT}N(d₂)`, négatif pour un call et
  **positif pour un put** ;
* le portage du dividende, `+qSe^{−qT}N(d₁)`, positif pour un call.

Le rapport du premier terme au gamma est un invariant exact — `½σ²S²` — et
c'est l'identité que la partie XIX a déjà établie par trois routes. Elle n'est
pas répétée ici : ce qui est nouveau est ce que les deux autres termes font au
**signe**, et la partie V le mesure.

II. La loi nulle d'un vendeur de prime
--------------------------------------
Le guide écrit que sur un grand échantillon, si l'implicite égale le réalisé,
le profit espéré est nul. C'est exact et c'est le point de départ, pas la
conclusion : *à espérance nulle, le vendeur gagne quand même la majorité du
temps*, et c'est cette fréquence qui se prend pour un revenu.

Elle se calcule. Sur un intervalle de couverture, le vendeur encaisse
`½ΓS²(σ²Δt − (ΔS/S)²)` : il gagne si le mouvement réalisé est inférieur au
mouvement facturé, c'est-à-dire si `Z² < 1`. La fréquence vaut donc
**2Φ(1) − 1 = 68,3 %**, sans référence au strike, à l'échéance, à la
volatilité ni au niveau. C'est la médiane d'un khi-deux à un degré (0,455)
comparée à sa moyenne (1) : *la loi de la variance réalisée est asymétrique,
et sa médiane est sous sa moyenne de plus de moitié.*

Sur la vie entière d'une option, la fréquence descend vers un demi à mesure
que les intervalles s'accumulent — et c'est pour cela qu'un vendeur qui
couvre souvent a l'impression de gagner moins qu'un vendeur qui ne couvre
pas, à espérance rigoureusement identique. Le vendeur nu, lui, a sa propre
constante : un straddle à la monnaie est gagnant si `|S_T − K|` est inférieur
à la prime, ce qui vaut **57,6 %** et ne dépend, là encore, ni de la
volatilité ni de l'échéance.

III. Ce que coûte la couverture discrète
-----------------------------------------
À couverture continue et volatilité réalisée égale à l'implicite, le résultat
n'est pas seulement d'espérance nulle : il est **identiquement nul**. Toute la
dispersion d'un livre de prime vient donc de la discrétisation, et elle a une
loi. Le module ne la postule pas — la partie XVIII a déjà payé pour cette
erreur-là : il l'ajuste, coefficient et puissance, et publie l'exposant mesuré.

IV. Les deux horloges
----------------------
Black-Scholes a une horloge, les marchés en ont deux : la variance s'accumule
les jours de bourse, l'escompte tous les jours. Le guide en tire une
prédiction vérifiable — « le thêta calendaire annonce trois jours de
décroissance sur un week-end, vous en observerez plutôt un » — et le dépôt la
mesure. Elle est fausse dans le bon sens : la valeur décroît comme la
**racine** du temps, pas comme le temps, et le guide vient lui-même de
consacrer une section à cette racine. Le compte exact est plus près de un et
demi.

V. Le signe
------------
« Un put profondément dans la monnaie peut avoir un thêta positif. Vérifiez
le signe, ne le supposez pas. » L'avertissement est juste ; le dépôt en fait
une carte. La frontière du thêta positif se calcule, la région se mesure, et
elle a une propriété que le guide n'écrit pas : **à taux nul elle est vide.**
Ce n'est donc pas une curiosité d'option, c'est un fait de taux.

VI. Ce qu'il faudrait pour établir une prime de variance
---------------------------------------------------------
Le guide conclut que le profit persistant d'un vendeur vient de l'écart entre
implicite et réalisé, et non du passage du temps. Le dépôt accepte l'énoncé et
pose sa question habituelle : combien de décisions pour l'établir ? La réponse
se calcule sur la dispersion mesurée en partie III, et elle se compare à une
carrière.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from . import grandeurs as G
from . import niveaux as nv
from . import quant as q
from .costs import norm_cdf
from .mc import Rng
from .report import Table, num

SEED = 20260910

#: Niveau et volatilité de référence, repris de la partie XX pour que les
#: trois parties d'options parlent du même sous-jacent.
S_REF = G.S_REF
VOL_REF = G.VOL_REF

#: Jours de bourse par an. La variance s'accumule sur ceux-là ; l'escompte,
#: sur les 365 de `niveaux.JOURS_AN`. Toute la partie IV est dans cet écart.
JOURS_BOURSE = 252.0

#: Taux et dividende d'un indice large. Ils ne servent qu'aux termes deux et
#: trois du thêta, et la partie V montre que le premier ne suffit pas.
TAUX = 0.04
DIVIDENDE = 0.013

#: L'option de référence : trente jours, à la monnaie.
JOURS_OPTION = 30.0


def _phi(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


# ---------------------------------------------------------------------------
# I. Le loyer, et ses trois termes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Termes:
    """Les trois effets empilés dans le thêta, en unités par an."""

    decroissance: float
    interet: float
    portage: float

    @property
    def total(self) -> float:
        return self.decroissance + self.interet + self.portage


def termes_call(s: float, k: float, vol: float, t: float, r: float = TAUX,
                div: float = DIVIDENDE) -> Termes:
    """Les trois termes du thêta d'un call, séparés.

    Le premier est celui que tout le monde appelle « le thêta » ; les deux
    autres sont ceux dont le signe se suppose au lieu de se vérifier.
    """
    d1, d2 = G._d(s, k, vol, t, r, div)
    return Termes(
        decroissance=-s * math.exp(-div * t) * _phi(d1) * vol
        / (2.0 * math.sqrt(t)),
        interet=-r * k * math.exp(-r * t) * norm_cdf(d2),
        portage=div * s * math.exp(-div * t) * norm_cdf(d1),
    )


def termes_put(s: float, k: float, vol: float, t: float, r: float = TAUX,
               div: float = DIVIDENDE) -> Termes:
    """Les trois termes du thêta d'un put.

    Le premier est **le même** — la décroissance de valeur temps ne connaît
    pas le sens de l'option, c'est le gamma qui la fixe et le gamma est
    commun. Les deux autres changent de signe.
    """
    d1, d2 = G._d(s, k, vol, t, r, div)
    return Termes(
        decroissance=-s * math.exp(-div * t) * _phi(d1) * vol
        / (2.0 * math.sqrt(t)),
        interet=r * k * math.exp(-r * t) * norm_cdf(-d2),
        portage=-div * s * math.exp(-div * t) * norm_cdf(-d1),
    )


def call(s: float, k: float, vol: float, t: float, r: float = TAUX,
         div: float = DIVIDENDE) -> float:
    """Prix d'un call, taux et dividende compris."""
    if t <= 0.0:
        return max(s - k, 0.0)
    d1, d2 = G._d(s, k, vol, t, r, div)
    return (s * math.exp(-div * t) * norm_cdf(d1)
            - k * math.exp(-r * t) * norm_cdf(d2))


def put(s: float, k: float, vol: float, t: float, r: float = TAUX,
        div: float = DIVIDENDE) -> float:
    """Prix d'un put, par la parité."""
    if t <= 0.0:
        return max(k - s, 0.0)
    return (call(s, k, vol, t, r, div) - s * math.exp(-div * t)
            + k * math.exp(-r * t))


def theta_numerique(prix, s: float, k: float, vol: float, t: float,
                    r: float = TAUX, div: float = DIVIDENDE) -> float:
    """Le thêta par différence finie sur l'échéance.

    C'est le contrôle des deux formes fermées ci-dessus : une forme fermée ne
    se publie pas sans être confrontée à autre chose qu'elle-même.
    """
    h = 1e-6
    return -(prix(s, k, vol, t + h, r, div)
             - prix(s, k, vol, t - h, r, div)) / (2.0 * h)


def rapport_theta_gamma(s: float, vol: float) -> float:
    """`|Θ₁|/Γ = ½σ²S²` — l'invariant, et il ne dépend ni de T ni de K.

    La partie XIX l'établit par trois routes et en tire le mouvement
    d'équilibre. Il est repris ici pour une seule raison : c'est lui qui rend
    le premier terme du thêta **entièrement redondant** avec le gamma, donc
    qui interdit de citer l'un sans l'autre.
    """
    return 0.5 * vol * vol * s * s


#: Moneyness balayées pour la décomposition. Elles vont assez loin dans la
#: monnaie pour que les termes deux et trois cessent d'être négligeables.
MONEYNESS: tuple[float, ...] = (0.70, 0.85, 0.95, 1.00, 1.05, 1.15, 1.30)

#: Échéances balayées, en jours.
ECHEANCES: tuple[float, ...] = (1.0, 7.0, 30.0, 90.0, 180.0, 365.0)


def table_termes() -> Table:
    rows = []
    for jours in (30.0, 180.0, 365.0):
        t = jours / nv.JOURS_AN
        for m in (0.85, 1.00, 1.15):
            s = S_REF * m
            tc = termes_call(s, S_REF, VOL_REF, t)
            tp = termes_put(s, S_REF, VOL_REF, t)
            part = (abs(tc.interet) + abs(tc.portage)) / abs(tc.total)
            rows.append([
                num(jours, 0),
                num(m, 2),
                num(tc.decroissance / nv.JOURS_AN, 4),
                num(tc.interet / nv.JOURS_AN, 4),
                num(tc.portage / nv.JOURS_AN, 4),
                num(tc.total / nv.JOURS_AN, 4, signed=True),
                num(tp.total / nv.JOURS_AN, 4, signed=True),
                num(100 * part, 1),
            ])
    return Table(
        key="th_termes",
        caption="Les trois termes du thêta, et la part que le mot « thêta » oublie",
        headers=["Jours", "Moneyness S/K", "Décroissance (par jour)",
                 "Intérêt (par jour)", "Portage (par jour)",
                 "Thêta du call", "Thêta du put",
                 "Part des deux termes oubliés (%)"],
        rows=rows,
        note="Sur un indice à " + num(100 * TAUX, 1) + " % de taux et "
             + num(100 * DIVIDENDE, 1) + " % de dividende, à "
             + num(100 * VOL_REF, 0) + " % de volatilité. Le premier terme "
             "est celui que tout le monde entend par « thêta », et il est "
             "**proportionnel au gamma** — la partie XIX en donne l'identité "
             "exacte, `|Θ₁|/Γ = ½σ²S²`, indépendante du strike et de "
             "l'échéance. Les deux autres ne sont pas des raffinements de "
             "pupitre : la dernière colonne mesure leur poids, et il passe de "
             "quelques pour cent à la monnaie et à court terme à une part "
             "**majoritaire** dans la monnaie et à un an. La colonne du put "
             "est là pour une raison précise : son terme d'intérêt est de "
             "signe opposé, et c'est ce qui rend possible un thêta positif — "
             "la cinquième section en fait la carte.",
    )


def table_invariant() -> Table:
    """Le contrôle du premier terme contre le gamma, et des formes contre
    la différence finie."""
    rows = []
    for jours in ECHEANCES:
        t = jours / nv.JOURS_AN
        g = nv.gamma(S_REF, S_REF, VOL_REF, t)
        t1 = termes_call(S_REF, S_REF, VOL_REF, t, 0.0, 0.0).decroissance
        rows.append([
            num(jours, 0),
            num(g, 6),
            num(t1 / nv.JOURS_AN, 5),
            num(abs(t1) / g, 2),
            num(rapport_theta_gamma(S_REF, VOL_REF), 2),
            num(100 * abs(abs(t1) / g / rapport_theta_gamma(S_REF, VOL_REF)
                          - 1.0), 6),
        ])
    return Table(
        key="th_invariant",
        caption="Le premier terme du thêta est le gamma, au facteur près, et le facteur ne bouge pas",
        headers=["Jours", "Gamma", "Décroissance (par jour)",
                 "Rapport mesuré", "½σ²S²", "Écart (%)"],
        rows=rows,
        note="À taux et dividende nuls, pour isoler le premier terme. Le "
             "rapport du thêta de décroissance au gamma vaut `½σ²S²` "
             "**exactement**, à toute échéance : la dernière colonne le "
             "vérifie à la sixième décimale, et son intérêt est qu'elle ne "
             "bouge pas. C'est l'identité que la partie XIX établit par trois "
             "routes ; elle est rappelée ici parce qu'elle interdit une "
             "pratique courante — *citer un thêta sans son gamma revient à "
             "citer un nombre deux fois*. Les deux formes fermées de ce "
             "module sont par ailleurs contrôlées contre une différence finie "
             "sur l'échéance, et l'accord tient à la sixième décimale.",
    )


# ---------------------------------------------------------------------------
# II. La loi nulle d'un vendeur de prime
# ---------------------------------------------------------------------------


def taux_par_intervalle() -> float:
    """`2Φ(1) − 1` — la fréquence de gain d'un intervalle de couverture.

    Le vendeur encaisse `½ΓS²(σ²Δt − ΔS²/S²)` : il gagne si le mouvement
    réalisé est inférieur au mouvement facturé, donc si `Z² < 1`. Aucune
    dépendance au strike, à l'échéance, à la volatilité ou au niveau.
    """
    return 2.0 * norm_cdf(1.0) - 1.0


def mediane_khi2() -> float:
    """La médiane d'un khi-deux à un degré, `[Φ⁻¹(0,75)]²`.

    Elle vaut 0,455 quand la moyenne vaut 1 : *la variance réalisée est
    inférieure à la variance facturée dans deux cas sur trois, et l'écart se
    rattrape entièrement dans le tiers restant.* C'est le mécanisme entier de
    la partie, et il n'a besoin d'aucune donnée de marché.
    """
    lo, hi = 0.0, 4.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if 2.0 * norm_cdf(math.sqrt(mid)) - 1.0 < 0.5:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _gamma_p(a: float, x: float) -> float:
    """La fonction gamma incomplète régularisée `P(a, x)`, par série.

    Elle ne sert qu'à un usage : `P(χ²_m < m) = P(m/2, m/2)`, et la série
    converge toujours ici puisque `x = a < a + 1`. Elle est contrôlée contre
    une simulation dans les tests, comme toute forme fermée du dépôt.
    """
    terme = 1.0 / a
    somme = terme
    n = 1
    while n < 1000:
        terme *= x / (a + n)
        somme += terme
        if terme < 1e-15 * somme:
            break
        n += 1
    return somme * math.exp(-x + a * math.log(x) - math.lgamma(a))


def taux_de_m_intervalles(m: int) -> float:
    """La fréquence de gain de `m` intervalles accumulés, à poids égaux.

    Le vendeur gagne si `Σ Z² < m`, donc si un khi-deux à `m` degrés tombe
    sous sa moyenne. À `m = 1` cela vaut 68,3 % ; la suite descend vers un
    demi, et **c'est toute la différence entre le relevé du soir et la
    position**.
    """
    return _gamma_p(m / 2.0, m / 2.0)


#: Nombres d'intervalles balayés pour la décroissance de la fréquence.
INTERVALLES: tuple[int, ...] = (1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233)


def histogramme(par_jour: int = 1, classes: int = 41, nu: bool = False,
                borne: float = 1.0) -> tuple[tuple[float, float], ...]:
    """La loi empirique du résultat, en classes de fraction de prime.

    La figure et la table lisent la **même** fonction : une planche qui
    dessine autre chose que ce que la mesure rend est indétectable à la
    relecture, et le dépôt a déjà payé pour ce défaut.
    """
    vals = _echantillon(par_jour, nu)
    pas = 2.0 * borne / classes
    comptes = [0] * classes
    for x in vals:
        i = int((x + borne) / pas)
        if 0 <= i < classes:
            comptes[i] += 1
    n = len(vals)
    return tuple((-borne + (i + 0.5) * pas, comptes[i] / n / pas)
                 for i in range(classes))


@lru_cache(maxsize=8)
def _echantillon(par_jour: int = 1, nu: bool = False) -> tuple[float, ...]:
    """L'échantillon brut des résultats, pour l'histogramme et ses tests."""
    t_tot = JOURS_OPTION / nv.JOURS_AN
    n_pas = max(1, int(round(JOURS_OPTION * par_jour)))
    dt = t_tot / n_pas
    prime = straddle(S_REF, S_REF, VOL_REF, t_tot)
    out = []
    for i in range(N_CHEMINS):
        chemin = _chemin(Rng(SEED + 7919 * i), n_pas, dt, VOL_REF)
        if nu:
            out.append((prime - abs(chemin[-1] - S_REF)) / prime)
            continue
        vals = [straddle(x, S_REF, VOL_REF, max(0.0, t_tot - k * dt))
                for k, x in enumerate(chemin)]
        pnl = 0.0
        for k in range(n_pas):
            h = G.delta_straddle(chemin[k], S_REF, VOL_REF, t_tot - k * dt)
            pnl += (vals[k] - vals[k + 1]
                    + h * (chemin[k + 1] - chemin[k]))
        out.append(pnl / prime)
    return tuple(out)


def straddle(s: float, k: float, vol: float, t: float) -> float:
    """Prix d'un straddle à taux nul."""
    return nv.call(s, k, vol, t) + nv.call(s, k, vol, t) - s + k


def taux_du_vendeur_nu(vol: float = VOL_REF,
                       jours: float = JOURS_OPTION) -> float:
    """La fréquence de gain d'un straddle vendu et **non couvert**.

    Le vendeur gagne si `|S_T − K|` est inférieur à la prime encaissée. Sous
    prix sans dérive le calcul est fermé, et le nombre est presque constant :
    la prime et l'écart-type terminal sont tous deux proportionnels à `σ√T`,
    si bien que le rapport des deux ne dépend que de `σ√T` lui-même, et très
    peu.
    """
    t = jours / nv.JOURS_AN
    prime = straddle(S_REF, S_REF, vol, t)
    v = vol * math.sqrt(t)
    haut = (math.log((S_REF + prime) / S_REF) + 0.5 * v * v) / v
    bas_prix = S_REF - prime
    if bas_prix <= 0.0:
        return norm_cdf(haut)
    bas = (math.log(bas_prix / S_REF) + 0.5 * v * v) / v
    return norm_cdf(haut) - norm_cdf(bas)


#: Nombre de chemins simulés.
#:
#: Ils ne sont **pas** appariés antithétiquement, et c'est mesuré plutôt que
#: supposé : la corrélation entre un chemin et son symétrique vaut 0,98 sur ce
#: résultat, parce que le bilan d'une couverture delta est une fonctionnelle
#: presque **paire** du chemin — nier le tirage rend deux fois le même nombre.
#: L'appariement ne réduirait donc aucune variance et diviserait par deux
#: l'échantillon effectif. La partie XIV interdit d'apparier une loi
#: asymétrique ; le cas d'ici est l'autre piège du même geste.
N_CHEMINS = 12000


@dataclass(frozen=True)
class Vendeur:
    """Le résultat d'un vendeur, en fractions de la prime encaissée."""

    moyenne: float
    mediane: float
    taux: float
    q05: float
    q95: float
    pire: float
    ecart_type: float


def _quantile(tri: list[float], p: float) -> float:
    if not tri:
        return 0.0
    i = min(len(tri) - 1, max(0, int(round(p * (len(tri) - 1)))))
    return tri[i]


def _resume(vals: list[float]) -> Vendeur:
    tri = sorted(vals)
    n = len(tri)
    moy = sum(tri) / n
    var = sum((x - moy) ** 2 for x in tri) / (n - 1)
    return Vendeur(
        moyenne=moy,
        mediane=_quantile(tri, 0.5),
        taux=sum(1 for x in tri if x > 0.0) / n,
        q05=_quantile(tri, 0.05),
        q95=_quantile(tri, 0.95),
        pire=tri[0],
        ecart_type=math.sqrt(var),
    )


def _chemin(rng: Rng, n_pas: int, dt: float, vol: float) -> list[float]:
    """Un chemin de prix sans dérive, tiré au pas `dt`."""
    s = S_REF
    out = [s]
    rac = vol * math.sqrt(dt)
    for _ in range(n_pas):
        s *= math.exp(-0.5 * vol * vol * dt + rac * rng.gauss())
        out.append(s)
    return out


@dataclass(frozen=True)
class Campagne:
    """Une campagne de vente : le couvert, le nu, et le relevé quotidien."""

    couvert: Vendeur
    nu: Vendeur
    taux_intervalle: float
    taux_premier: float


@lru_cache(maxsize=64)
def simuler_vendeur(jours: float = JOURS_OPTION, par_jour: int = 1,
                    n: int = N_CHEMINS, vol_implicite: float = VOL_REF,
                    vol_reelle: float | None = None,
                    seed: int = SEED) -> Campagne:
    """Vend un straddle à la monnaie, le couvre en delta, et compte.

    Trois comptes sortent de la même simulation : le vendeur **couvert** au
    pas demandé, le vendeur **nu** sur les mêmes chemins, et la fréquence
    d'intervalles gagnants — le relevé quotidien du premier. Les deux
    premiers ont la même espérance, nulle sous volatilité réalisée égale à
    l'implicite ; le troisième n'est pas un résultat, c'est ce que le vendeur
    regarde.
    """
    vr = vol_implicite if vol_reelle is None else vol_reelle
    t_tot = jours / nv.JOURS_AN
    n_pas = max(1, int(round(jours * par_jour)))
    dt = t_tot / n_pas
    prime = straddle(S_REF, S_REF, vol_implicite, t_tot)
    couverts: list[float] = []
    nus: list[float] = []
    gagnants = 0
    intervalles = 0
    premiers = 0
    for i in range(n):
        chemin = _chemin(Rng(seed + 7919 * i), n_pas, dt, vr)
        nus.append((prime - abs(chemin[-1] - S_REF)) / prime)
        # La valeur du straddle le long du chemin, calculée une fois. Le
        # bilan d'un intervalle est alors `V_k − V_{k+1} + h·ΔS`, et la somme
        # de ces bilans **est** le résultat de la position — elle télescope.
        # C'est ce qui rend le relevé quotidien et le résultat final
        # rigoureusement le même objet, lu à deux échelles.
        vals = [straddle(x, S_REF, vol_implicite, max(0.0, t_tot - k * dt))
                for k, x in enumerate(chemin)]
        pnl = 0.0
        for k in range(n_pas):
            h = G.delta_straddle(chemin[k], S_REF, vol_implicite,
                                 t_tot - k * dt)
            bilan = vals[k] - vals[k + 1] + h * (chemin[k + 1] - chemin[k])
            if bilan > 0.0:
                gagnants += 1
                if k == 0:
                    premiers += 1
            intervalles += 1
            pnl += bilan
        couverts.append(pnl / prime)
    return Campagne(_resume(couverts), _resume(nus), gagnants / intervalles,
                    premiers / n)


def table_frequence() -> Table:
    """Les trois fréquences de gain, et la seule espérance qu'elles partagent."""
    c = simuler_vendeur()
    couvert, nu = c.couvert, c.nu
    rows = [
        ["Un intervalle de couverture", num(100 * taux_par_intervalle(), 1),
         "0,00", "exacte", "2Φ(1) − 1"],
        ["Le straddle vendu nu, sur sa vie",
         num(100 * taux_du_vendeur_nu(), 1),
         num(100 * nu.moyenne, 2, signed=True), "simulée",
         "Φ(z₊) − Φ(z₋)"],
        ["Le straddle vendu et couvert chaque jour",
         num(100 * couvert.taux, 1),
         num(100 * couvert.moyenne, 2, signed=True), "simulée", "—"],
    ]
    return Table(
        key="th_frequence",
        caption="Trois fréquences de gain, une seule espérance, et elle est nulle",
        headers=["Ce qu'on compte", "Fréquence de gain (%)",
                 "Espérance (% de la prime)", "Route", "Forme fermée"],
        rows=rows,
        note="Sur " + num(N_CHEMINS, 0) + " chemins sans dérive, à "
             "volatilité réalisée **égale** à l'implicite — l'hypothèse que "
             "le guide pose lui-même pour conclure à l'espérance nulle. La "
             "première ligne est exacte et ne dépend de rien : sur un "
             "intervalle, le vendeur gagne si `Z² < 1`, donc "
             + num(100 * taux_par_intervalle(), 1) + " % du temps. Le "
             "mécanisme est la médiane d'un khi-deux à un degré, "
             + num(mediane_khi2(), 3) + ", comparée à sa moyenne, 1 : *la "
             "variance réalisée est sous la variance facturée dans deux cas "
             "sur trois, et se rattrape entièrement dans le tiers restant.* "
             "Les trois lignes ont la même espérance et trois fréquences "
             "différentes&nbsp;: **ce que le vendeur choisit en couvrant, ce "
             "n'est pas son espérance, c'est la forme de sa loi.**",
        wrap_cols=[0],
    )


def table_distribution() -> Table:
    """La loi du résultat, et le fait qu'elle n'est pas symétrique."""
    rows = []
    for etiquette, par_jour in (("Non couvert", 0), ("Une fois par jour", 1),
                                ("Quatre fois par jour", 4),
                                ("Seize fois par jour", 16)):
        c = simuler_vendeur(par_jour=max(1, par_jour))
        v = c.nu if par_jour == 0 else c.couvert
        rows.append([
            etiquette,
            num(100 * v.taux, 1),
            num(100 * v.moyenne, 2, signed=True),
            num(100 * v.mediane, 1, signed=True),
            num(100 * v.q05, 1, signed=True),
            num(100 * v.pire, 0, signed=True),
            num(100 * v.ecart_type, 1),
        ])
    return Table(
        key="th_distribution",
        caption="La loi du vendeur, en fractions de la prime encaissée",
        headers=["Couverture", "Fréquence de gain (%)", "Moyenne (%)",
                 "Médiane (%)", "5ᵉ centile (%)", "Pire chemin (%)",
                 "Écart-type (%)"],
        rows=rows,
        note="Toutes les lignes portent la même espérance, et elle est nulle "
             "à la précision de l'échantillon : c'est l'hypothèse du guide, "
             "reprise telle quelle. Ce qui change d'une ligne à l'autre est "
             "la **forme** : la médiane est positive partout, la moyenne est "
             "nulle partout, et l'écart entre les deux est payé par la queue "
             "gauche. Couvrir plus souvent resserre la loi sans déplacer son "
             "centre — la colonne d'écart-type décroît, la colonne de moyenne "
             "ne bouge pas — et *c'est la seule chose que la couverture "
             "achète*. La troisième section en donne la loi et l'exposant "
             "mesuré.",
        wrap_cols=[0],
    )


# ---------------------------------------------------------------------------
# III. Ce que coûte la couverture discrète
# ---------------------------------------------------------------------------


#: Fréquences de couverture balayées, en rééquilibrages par jour.
PAS_GRILLE: tuple[int, ...] = (1, 2, 4, 8, 16, 32)

#: Chemins de la campagne d'exposant. Moins que la campagne principale, parce
#: que la grille la plus fine coûte trente-deux fois la plus grossière.
N_GRILLE = 2500


def dispersion(par_jour: int, jours: float = JOURS_OPTION) -> float:
    """L'écart-type du résultat couvert, en fractions de la prime."""
    return simuler_vendeur(jours=jours, par_jour=par_jour,
                           n=N_GRILLE).couvert.ecart_type


@lru_cache(maxsize=8)
def loi_de_dispersion(jours: float = JOURS_OPTION) -> tuple[float, float]:
    """Le couple `(k, p)` de l'ajustement `dispersion = k·n^{−p}`.

    L'exposant est **ajusté**, pas postulé. La partie XVIII a payé pour cette
    règle : une demi-largeur y était supposée décroître en racine de
    l'horizon, la mesure a rendu 0,61, et la racine manquait les points de
    19 %. Ici la racine est la bonne réponse — mais elle est mesurée.
    """
    pts = [(float(n), dispersion(n, jours)) for n in PAS_GRILLE]
    xs = [math.log(x) for x, _ in pts]
    ys = [math.log(y) for _, y in pts]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    pente = (sum((x - mx) * (y - my) for x, y in zip(xs, ys))
             / sum((x - mx) ** 2 for x in xs))
    return math.exp(my - pente * mx), -pente


def dispersion_ajustee(par_jour: float, jours: float = JOURS_OPTION) -> float:
    k, p = loi_de_dispersion(jours)
    return k * par_jour ** (-p)


def couvertures_pour_bruit(cible: float,
                           jours: float = JOURS_OPTION) -> float:
    """Le nombre de couvertures par jour pour ramener la dispersion à `cible`.

    C'est la question du pupitre, et elle a une réponse fermée une fois
    l'exposant mesuré : `n = (k/cible)^{1/p}`.
    """
    k, p = loi_de_dispersion(jours)
    return (k / cible) ** (1.0 / p)


def table_couverture() -> Table:
    k, p = loi_de_dispersion()
    rows = []
    for n_pas in PAS_GRILLE:
        c = simuler_vendeur(par_jour=n_pas, n=N_GRILLE)
        mesure = c.couvert.ecart_type
        rows.append([
            num(n_pas, 0),
            num(100 * mesure, 2),
            num(100 * dispersion_ajustee(n_pas), 2),
            num(100 * c.couvert.moyenne, 2, signed=True),
            num(100 * c.couvert.taux, 1),
            num(100 * c.taux_intervalle, 1),
        ])
    return Table(
        key="th_couverture",
        caption="Ce que la couverture achète, et ce qu'elle n'achète pas",
        headers=["Couvertures par jour", "Dispersion mesurée (%)",
                 "Ajustement k·n^(−p) (%)", "Moyenne (%)",
                 "Fréquence de gain de la position (%)",
                 "Fréquence de gain d'un intervalle (%)"],
        rows=rows,
        note="Sur " + num(N_GRILLE, 0) + " chemins par ligne, à volatilité "
             "réalisée égale à l'implicite. L'exposant est **ajusté** et non "
             "postulé — la partie XVIII a payé pour cette règle — et il vaut "
             + num(p, 3) + " : *la dispersion décroît comme la racine du "
             "nombre de couvertures*, donc **la diviser par deux coûte quatre "
             "fois plus de rééquilibrages**. Les trois dernières colonnes "
             "sont le sujet de la partie. La moyenne ne bouge pas : couvrir "
             "plus souvent n'achète aucune espérance. La fréquence de gain de "
             "la position ne bouge pas non plus, et reste au voisinage d'un "
             "demi. Seule la fréquence d'un **intervalle** reste haute, à "
             + num(100 * taux_par_intervalle(), 1) + " % en forme fermée : "
             "c'est le relevé du soir, et c'est lui qu'on prend pour un "
             "revenu.",
    )


#: Les deux axes du relief de la couverture. Ils sont écrits de façon que le
#: **maximum tombe au coin du fond** : peu de couvertures, échéance courte. En
#: projection isométrique le coin (0, 0) est le plus éloigné, et un relief qui
#: monte vers l'horizon se lit ; l'ordre inverse pose le sommet au premier
#: plan, où il paraît à la hauteur d'écran du coin lointain.
SURF_PAS: tuple[int, ...] = (1, 2, 4, 8, 16, 32)
SURF_JOURS: tuple[float, ...] = (7.0, 14.0, 30.0, 60.0, 90.0, 120.0)


@lru_cache(maxsize=2)
def surface_dispersion() -> tuple[tuple[float, ...], ...]:
    """La dispersion du vendeur, en couvertures par jour et en échéance.

    Le maximum est au fond : peu de couvertures et échéance courte. C'est la
    règle de lecture des reliefs du dépôt, et elle décide de l'ordre des deux
    listes ci-dessus.
    """
    return tuple(
        tuple(simuler_vendeur(jours=j, par_jour=n, n=800).couvert.ecart_type
              for j in SURF_JOURS)
        for n in SURF_PAS
    )


# ---------------------------------------------------------------------------
# IV. Les deux horloges
# ---------------------------------------------------------------------------


#: Jours non ouvrés d'une année : 365 − 252.
JOURS_FERIES = nv.JOURS_AN - JOURS_BOURSE

#: Le poids d'un jour non ouvré, en jours de bourse. Il n'est **pas
#: observable** : à 1 on retrouve l'horloge calendaire, à 0 l'horloge de
#: bourse, et les deux conventions vivent aux deux bouts du même paramètre.
#: Le dépôt le balaie plutôt que de le choisir — c'est la règle appliquée à
#: la taille de grappe du footprint et à la hauteur de rangée du TPO.
POIDS_GRILLE: tuple[float, ...] = (0.0, 0.10, 0.2566, 0.50, 1.0)


def jours_apparents(poids: float) -> float:
    """Les jours calendaires de décroissance qu'un week-end fait **observer**.

    Le compte est exact et ne dépend pas de l'échéance : trois créneaux non
    ouvrés sont consommés, chacun de poids `ω`, sur un budget annuel de
    `252 + 113ω` jours de bourse répartis sur 365 jours calendaires.
    """
    return 3.0 * poids * nv.JOURS_AN / (JOURS_BOURSE + JOURS_FERIES * poids)


def poids_pour_apparents(cible: float) -> float:
    """Le poids d'un jour non ouvré qui rend `cible` jours apparents.

    C'est la calibration de la partie : le guide publie son observation — on
    voit passer « plutôt un jour » — et cette observation **fixe** le seul
    paramètre non observable du modèle, comme les deux nombres sans direction
    fixaient le modèle nul de la partie XV.
    """
    return cible * JOURS_BOURSE / (3.0 * nv.JOURS_AN - cible * JOURS_FERIES)


def derive_implicite(jours: float, poids: float) -> float:
    """La hausse de volatilité implicite qu'un week-end impose sur l'horloge
    calendaire, pour que la variance totale ne bouge pas.

    À poids calibré sur « un jour apparent », le résultat se simplifie en
    `√((D−1)/(D−3)) − 1`, et il **explose** sous la semaine.
    """
    if jours <= 3.0:
        return math.inf
    tau = jours * (JOURS_BOURSE + JOURS_FERIES * poids) / nv.JOURS_AN
    if tau <= 3.0 * poids:
        return math.inf
    return math.sqrt((1.0 - 3.0 * poids / tau) * jours / (jours - 3.0)) - 1.0


def decote_calendaire(jours: float) -> float:
    """La part de prime qu'un thêta calendaire annonce sur un week-end."""
    return 1.0 - math.sqrt(max(0.0, jours - 3.0) / jours)


def decote_observee(jours: float, poids: float) -> float:
    """La part de prime qu'on observe, à poids donné."""
    tau = jours * (JOURS_BOURSE + JOURS_FERIES * poids) / nv.JOURS_AN
    return 1.0 - math.sqrt(max(0.0, tau - 3.0 * poids) / tau)


def echeance_critique(spread: float, poids: float) -> float:
    """L'échéance au-dessous de laquelle l'effet dépasse une fourchette.

    `spread` est la fourchette de volatilité implicite, en fraction de la
    volatilité cotée. Au-dessus de cette échéance l'effet de week-end est
    dans le bruit de cotation ; au-dessous il est visible et se néglige quand
    même.
    """
    lo, hi = 3.05, 4000.0
    if derive_implicite(hi, poids) > spread:
        return hi
    for _ in range(120):
        mid = 0.5 * (lo + hi)
        if derive_implicite(mid, poids) > spread:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


#: Échéances balayées pour les horloges, en jours calendaires.
ECHEANCES_HORLOGE: tuple[float, ...] = (4.0, 7.0, 14.0, 30.0, 60.0, 90.0,
                                        180.0, 365.0)

#: La fourchette de volatilité implicite déclarée, en fraction de la cotation.
#: Un point de volatilité sur vingt-cinq.
SPREAD_VOL = 0.04


def table_horloges() -> Table:
    poids = poids_pour_apparents(1.0)
    rows = []
    for j in ECHEANCES_HORLOGE:
        d = derive_implicite(j, poids)
        rows.append([
            num(j, 0),
            num(100 * decote_calendaire(j), 2),
            num(100 * decote_observee(j, poids), 2),
            num(decote_observee(j, poids) / decote_calendaire(j) * 3.0, 2),
            num(100 * d, 1) if math.isfinite(d) else "—",
            "oui" if d > SPREAD_VOL else "non",
        ])
    return Table(
        key="th_horloges",
        caption="Le week-end, sur les deux horloges, et la hausse d'implicite qu'il impose",
        headers=["Jours calendaires", "Décote annoncée (%)",
                 "Décote observée (%)", "Jours apparents",
                 "Hausse d'implicite (%)",
                 "Au-dessus de la fourchette"],
        rows=rows,
        note="Le poids d'un jour non ouvré est **calibré**, pas choisi : le "
             "guide publie son propre test — un thêta calendaire annonce "
             "trois jours de décroissance sur un week-end, on en observe "
             "« plutôt un » — et cette observation fixe le seul paramètre non "
             "observable du modèle, `ω` = " + num(poids, 4) + ". La colonne "
             "des jours apparents est alors une **prédiction**, et elle est "
             "presque constante : *le nombre de jours qu'on croit voir passer "
             "ne dépend pas de l'échéance*, parce que la valeur décroît "
             "comme la racine du temps et que la racine se simplifie dans le "
             "rapport. La dernière colonne est le fait utile : à poids "
             "calibré la hausse d'implicite vaut exactement "
             "`√((D−1)/(D−3)) − 1`, elle dépasse une fourchette d'un point "
             "de volatilité au-dessous de "
             + num(echeance_critique(SPREAD_VOL, poids), 0) + " jours, et "
             "elle **explose** sous la semaine — ce qui est la raison pour "
             "laquelle une implicite courte cotée un vendredi ne se compare "
             "pas à la même cotée un lundi.",
    )


def table_poids() -> Table:
    """Le paramètre non observable, et ce qu'il décide."""
    rows = []
    for w in POIDS_GRILLE:
        d30 = derive_implicite(30.0, w)
        d7 = derive_implicite(7.0, w)
        rows.append([
            num(w, 4),
            num(jours_apparents(w), 2),
            num(100 * d7, 1) if math.isfinite(d7) else "—",
            num(100 * d30, 1) if math.isfinite(d30) else "—",
            num(echeance_critique(SPREAD_VOL, w), 0) if w > 0 else "0",
        ])
    return Table(
        key="th_poids",
        caption="Le paramètre que personne n'observe, et l'écart qu'il ouvre",
        headers=["Poids d'un jour non ouvré", "Jours apparents",
                 "Hausse d'implicite à 7 jours (%)",
                 "Hausse à 30 jours (%)",
                 "Échéance où l'effet dépasse la fourchette (jours)"],
        rows=rows,
        note="Les deux conventions que le guide oppose ne sont pas deux "
             "théories : ce sont **les deux bouts d'un même paramètre**. À "
             "`ω = 1` l'horloge est calendaire et le week-end coûte trois "
             "jours ; à `ω = 0` elle est de bourse et il ne coûte rien. Entre "
             "les deux, tout est admissible et rien n'est observable "
             "directement — c'est la situation de la taille de grappe du "
             "footprint et de la hauteur de rangée du TPO, où un réglage "
             "décide de la rareté de ce qu'on lit. La ligne calibrée sur "
             "l'observation du guide est " + num(poids_pour_apparents(1.0), 4)
             + ", et la dernière colonne dit à partir de quand le choix cesse "
             "d'être académique.",
    )


SURF_HORLOGE_POIDS: tuple[float, ...] = (0.10, 0.20, 0.35, 0.50, 0.75, 1.0)
SURF_HORLOGE_JOURS: tuple[float, ...] = (5.0, 10.0, 21.0, 45.0, 90.0, 180.0)


@lru_cache(maxsize=2)
def surface_horloges() -> tuple[tuple[float, ...], ...]:
    """La hausse d'implicite de week-end, en poids et en échéance."""
    return tuple(
        tuple(min(1.5, max(0.0, derive_implicite(j, w)))
              for j in SURF_HORLOGE_JOURS)
        for w in SURF_HORLOGE_POIDS
    )



# ---------------------------------------------------------------------------
# V. Le signe
# ---------------------------------------------------------------------------


def frontiere_signe(t: float, vol: float = VOL_REF, r: float = TAUX,
                    div: float = DIVIDENDE) -> float:
    """La moneyness `S/K` au-dessous de laquelle le thêta d'un put est positif.

    Rend 0 quand la région n'existe pas — ce qui est le cas à taux nul, et
    c'est le fait de la section : le thêta positif n'est pas une curiosité
    d'option, **c'est un fait de taux**.
    """
    if termes_put(1e-4, 1.0, vol, t, r, div).total <= 0.0:
        return 0.0
    lo, hi = 1e-4, 1.0
    for _ in range(120):
        mid = 0.5 * (lo + hi)
        if termes_put(mid, 1.0, vol, t, r, div).total > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


#: Grille de moneyness et d'échéances sur laquelle se mesure la part du plan.
PLAN_MONEYNESS: tuple[float, ...] = tuple(
    0.40 + 0.01 * i for i in range(101))
PLAN_JOURS: tuple[float, ...] = tuple(7.0 + 7.0 * i for i in range(52))


def part_positive(r: float, vol: float = VOL_REF,
                  div: float = DIVIDENDE) -> float:
    """La part du plan (moneyness × échéance) où le thêta d'un put est positif."""
    n = 0
    for j in PLAN_JOURS:
        t = j / nv.JOURS_AN
        for m in PLAN_MONEYNESS:
            if termes_put(m, 1.0, vol, t, r, div).total > 0.0:
                n += 1
    return n / (len(PLAN_JOURS) * len(PLAN_MONEYNESS))


#: Taux balayés pour la part du plan. Le zéro y est, et c'est lui le résultat.
TAUX_GRILLE: tuple[float, ...] = (0.0, 0.01, 0.02, 0.04, 0.06)


def table_signe() -> Table:
    rows = []
    for r in TAUX_GRILLE:
        f30 = frontiere_signe(30.0 / nv.JOURS_AN, r=r)
        f365 = frontiere_signe(365.0 / nv.JOURS_AN, r=r)
        rows.append([
            num(100 * r, 1),
            num(f30, 3) if f30 > 0 else "aucune",
            num(f365, 3) if f365 > 0 else "aucune",
            num(100 * part_positive(r), 2),
        ])
    return Table(
        key="th_signe",
        caption="Où le thêta change de signe, et pourquoi la région est vide à taux nul",
        headers=["Taux (%)", "Frontière à 30 jours (S/K)",
                 "Frontière à 1 an (S/K)", "Part du plan à thêta positif (%)"],
        rows=rows,
        note="Le thêta d'un put est positif quand le terme d'intérêt "
             "`+rKe^{−rT}N(−d₂)` l'emporte sur la décroissance de valeur "
             "temps, ce qui demande un put **profondément dans la monnaie**, "
             "où la seconde s'annule. La première ligne est le fait de la "
             "section : *à taux nul la région n'existe pas*, exactement, et "
             "pas approximativement — le terme qui la crée est proportionnel "
             "à `r`. L'avertissement du guide — « vérifiez le signe, ne le "
             "supposez pas » — est donc juste et daté : il n'a rien coûté à "
             "personne pendant la décennie où les taux étaient nuls, et il "
             "redevient une règle de pupitre dès qu'ils ne le sont plus. La "
             "dernière colonne est mesurée sur une grille de "
             + num(len(PLAN_MONEYNESS) * len(PLAN_JOURS), 0) + " points.",
    )


SURF_SIGNE_TAUX: tuple[float, ...] = (0.06, 0.04, 0.03, 0.02, 0.01, 0.0)
SURF_SIGNE_JOURS: tuple[float, ...] = (21.0, 45.0, 90.0, 180.0, 270.0, 365.0)


@lru_cache(maxsize=2)
def surface_signe() -> tuple[tuple[float, ...], ...]:
    """La frontière du thêta positif, en taux et en échéance."""
    return tuple(
        tuple(frontiere_signe(j / nv.JOURS_AN, r=r) for j in SURF_SIGNE_JOURS)
        for r in SURF_SIGNE_TAUX
    )


# ---------------------------------------------------------------------------
# VI. Ce qu'il faudrait pour établir une prime de variance
# ---------------------------------------------------------------------------


#: Écarts implicite-réalisé balayés, en points de volatilité.
PRIMES: tuple[float, ...] = (0.5, 1.0, 2.0, 4.0)

#: Le quantile normal bilatéral à 95 %.
Z_95 = 1.959963984540054

#: Expirations par an pour un vendeur mensuel.
EXPIRATIONS_AN = 12.0


@dataclass(frozen=True)
class Prime:
    """Ce qu'un écart implicite-réalisé rapporte, et ce qu'il coûte à établir."""

    points: float
    moyenne: float
    ecart_type: float
    taux: float
    expirations: float
    annees: float


@lru_cache(maxsize=16)
def campagne_prime(points: float, par_jour: int = 1) -> Prime:
    """Simule un vendeur qui a réellement un avantage de `points` de volatilité.

    L'implicite reste à la référence, le réalisé descend. L'espérance cesse
    d'être nulle ; la dispersion, elle, ne bouge presque pas — et c'est le
    rapport des deux qui décide du nombre d'expirations.
    """
    c = simuler_vendeur(par_jour=par_jour, n=N_CHEMINS,
                        vol_reelle=VOL_REF - points / 100.0)
    v = c.couvert
    n = (Z_95 * v.ecart_type / v.moyenne) ** 2 if v.moyenne > 0 else math.inf
    return Prime(points, v.moyenne, v.ecart_type, v.taux, n,
                 n / EXPIRATIONS_AN)


#: Avantages balayés pour situer le point où un mois vaut une soirée.
PRIMES_FINES: tuple[float, ...] = (1.0, 1.25, 1.5, 1.75, 2.0)


@lru_cache(maxsize=2)
def avantage_pour_egaler_la_soiree() -> float:
    """L'avantage qu'il faut pour qu'un mois affiche ce qu'une soirée affiche.

    Un vendeur **sans le moindre avantage** gagne 68,3 % de ses soirées. Un
    vendeur qui a un avantage réel gagne une fraction de ses **mois** qui
    monte avec cet avantage. La question de la partie est où les deux se
    croisent, et la réponse tient à ce que les deux nombres ne comptent pas
    le même objet : *il faut un avantage considérable pour qu'un mois affiche
    ce qu'une soirée sans avantage affiche déjà.*
    """
    pts = [(p, campagne_prime(p).taux) for p in PRIMES_FINES]
    cible = taux_par_intervalle()
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if y0 <= cible <= y1:
            return x0 + (x1 - x0) * (cible - y0) / (y1 - y0)
    return pts[-1][0]


def table_preuve() -> Table:
    rows = []
    for pts in PRIMES:
        p = campagne_prime(pts)
        rows.append([
            num(pts, 1),
            num(100 * p.moyenne, 2),
            num(100 * p.ecart_type, 1),
            num(p.moyenne / p.ecart_type, 3),
            num(100 * p.taux, 1),
            num(p.expirations, 0),
            num(p.annees, 1),
        ])
    return Table(
        key="th_preuve",
        caption="Combien d'expirations pour établir une prime de variance",
        headers=["Écart implicite-réalisé (points de vol)",
                 "Espérance (% de la prime)", "Dispersion (%)",
                 "Rapport signal sur bruit", "Fréquence de gain (%)",
                 "Expirations requises", "Années, à une par mois"],
        rows=rows,
        note="Le guide conclut que le profit persistant d'un vendeur vient de "
             "l'écart entre implicite et réalisé, et non du passage du temps. "
             "Le dépôt accepte l'énoncé et pose sa question : combien de "
             "décisions pour l'établir ? La dispersion est celle de la "
             "troisième section, mesurée et non postulée, et elle **ne bouge "
             "pas** avec l'avantage — c'est ce qui rend la colonne des "
             "expirations si sensible. Deux lectures s'imposent. La première "
             "est que la fréquence de gain reste au voisinage d'un demi même "
             "quand l'avantage est réel : *un vendeur qui gagne une fois sur "
             "deux peut avoir un avantage considérable, et un vendeur qui "
             "gagne deux fois sur trois peut n'en avoir aucun.* La seconde "
             "est le prix : un point de volatilité demande "
             + num(campagne_prime(1.0).annees, 1) + " ans à une expiration "
             "par mois, ce qui est le budget d'information de la quatrième "
             "partie, rencontré sur un objet entièrement différent.",
    )


SURF_PRIME_POINTS: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)
SURF_PRIME_PAS: tuple[int, ...] = (1, 2, 4, 8, 16, 32)


@lru_cache(maxsize=2)
def surface_preuve() -> tuple[tuple[float, ...], ...]:
    """Les années requises, en avantage et en fréquence de couverture.

    Les deux axes agissent, et pas de la même façon : l'avantage entre au
    carré au dénominateur, la couverture ne réduit que le numérateur.
    """
    out = []
    for n_pas in SURF_PRIME_PAS:
        ligne = []
        for pts in SURF_PRIME_POINTS:
            c = simuler_vendeur(par_jour=n_pas, n=1200,
                                vol_reelle=VOL_REF - pts / 100.0).couvert
            if c.moyenne <= 0.0:
                ligne.append(200.0)
            else:
                n = (Z_95 * c.ecart_type / c.moyenne) ** 2
                ligne.append(min(200.0, n / EXPIRATIONS_AN))
        out.append(tuple(ligne))
    return tuple(out)


# ---------------------------------------------------------------------------
# VII. Le décompte
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Affirmation:
    """Une affirmation du guide, et ce qu'elle déplace dans l'identité."""

    enonce: str
    grandeur: str
    mesure: str
    negociable: bool


def affirmations() -> tuple[Affirmation, ...]:
    poids = poids_pour_apparents(1.0)
    c = simuler_vendeur()
    return (
        Affirmation(
            "Le thêta est le loyer du gamma, et le mouvement d'équilibre "
            "vaut σ/√365",
            "l'horloge",
            "identité exacte, trois routes, partie XIX",
            False),
        Affirmation(
            "La valeur temps décroît en racine : la moitié d'une prime de "
            "90 jours part en 68 jours",
            "l'horloge",
            num(100 * (1.0 - math.sqrt(22.5 / 90.0)), 1) + " % perdus quand "
            "il reste 22,5 jours",
            False),
        Affirmation(
            "Le thêta est un loyer, pas un rendement : à implicite égale au "
            "réalisé, l'espérance est nulle",
            "la direction",
            num(100 * c.couvert.moyenne, 2, signed=True) + " % de la prime, "
            "mesuré",
            True),
        Affirmation(
            "La décroissance se concentre à la monnaie et s'inverse loin "
            "d'elle",
            "l'horloge",
            "le premier terme suit le gamma, exactement",
            False),
        Affirmation(
            "Deux horloges : la variance s'accumule les jours de bourse, "
            "l'escompte tous les jours",
            "l'horloge",
            num(jours_apparents(poids), 2) + " jours apparents sur trois "
            "annoncés",
            False),
        Affirmation(
            "Ne jamais citer un thêta sans le gamma de la position",
            "rien",
            "le rapport des deux vaut ½σ²S², donc le second est le premier",
            False),
        Affirmation(
            "Le thêta en pourcentage de la prime est l'unité comparable",
            "le risque",
            "toute la partie est chiffrée dans cette unité",
            False),
        Affirmation(
            "Le thêta court terme n'est pas de l'argent gratuit : le gamma "
            "grandit d'autant",
            "le risque",
            "le rapport ne bouge pas d'une échéance à l'autre",
            False),
        Affirmation(
            "Une option profondément dans la monnaie peut avoir un thêta "
            "positif",
            "le risque",
            num(100 * part_positive(TAUX), 2) + " % du plan à "
            + num(100 * TAUX, 0) + " % de taux, **zéro** à taux nul",
            False),
    )


def familles() -> tuple[tuple[str, int], ...]:
    """Les trois parties d'options, comptées dans leurs propres modules.

    Les totaux ne sont pas recopiés : ils viennent de `niveaux.affirmations`,
    de `grandeurs.confusions` et de la fonction ci-dessus. Un compte écrit à
    la main dans une planche est un compte qui finit par mentir — celui-ci
    l'a fait une fois, dans le premier jet de cette partie.
    """
    return (("Gamma, partie XIX", len(nv.affirmations())),
            ("Delta, partie XX", len(G.confusions())),
            ("Thêta, partie XXI", len(affirmations())))


def compte_par_grandeur() -> dict[str, int]:
    """Combien d'affirmations déplacent quoi. Compté, jamais écrit."""
    out: dict[str, int] = {}
    for a in affirmations():
        out[a.grandeur] = out.get(a.grandeur, 0) + 1
    return out


def table_reste() -> Table:
    rows = []
    for a in affirmations():
        rows.append([a.enonce, a.grandeur, a.mesure,
                     "oui" if a.negociable else "non"])
    return Table(
        key="th_reste",
        caption="Neuf affirmations, ce qu'elles déplacent, et celle qui parle de direction",
        headers=["L'affirmation", "Ce qu'elle déplace", "Ce que la mesure en dit",
                 "Négociable"],
        rows=rows,
        note="Le décompte se lit dans l'identité `E[R] = (µ·E[τ∧T] − c)/a` : "
             + num(compte_par_grandeur().get("l'horloge", 0), 0)
             + " affirmations déplacent **l'horloge**, "
             + num(compte_par_grandeur().get("le risque", 0), 0)
             + " le **risque**, une ne déplace rien, et **une seule touche à "
             "la direction**. "
             "C'est celle qui dit qu'il n'y en a pas. Le guide écrit, sans y "
             "insister, que l'espérance d'un vendeur est nulle lorsque "
             "l'implicite égale le réalisé ; c'est le théorème d'arrêt "
             "optionnel du marché d'options, et c'est la conclusion des trois "
             "parties de cette série. *Les "
             + num(sum(n for _, n in familles()), 0) + " affirmations "
             "examinées sur le gamma, le delta et le thêta déplacent "
             "l'horloge ou le risque ; aucune ne donne un sens.*",
        wrap_cols=[0, 2],
    )


# ---------------------------------------------------------------------------
# Les chemins témoins
# ---------------------------------------------------------------------------


N_TEMOINS = 600


@lru_cache(maxsize=4)
def chemins_temoins(jours: float = JOURS_OPTION, par_jour: int = 1,
                    n: int = N_TEMOINS, vol: float = VOL_REF,
                    seed: int = SEED + 11
                    ) -> tuple[tuple[str, tuple[float, ...],
                                     tuple[float, ...]], ...]:
    """Trois chemins, choisis par une **règle calculée**.

    Le loyer se perçoit tous les jours et se rend en un après-midi : la
    planche existe pour montrer cela, et elle ne le montrerait pas si le
    chemin était choisi à la main. La règle retient le premier chemin dont le
    résultat dépasse la moitié de la prime, le premier qui en perd plus de la
    moitié, et celui dont le résultat est le plus proche de la médiane.
    """
    t_tot = jours / nv.JOURS_AN
    n_pas = max(1, int(round(jours * par_jour)))
    dt = t_tot / n_pas
    prime = straddle(S_REF, S_REF, vol, t_tot)
    lots = []
    for i in range(n):
        chemin = _chemin(Rng(seed + 7919 * i), n_pas, dt, vol)
        vals = [straddle(x, S_REF, vol, max(0.0, t_tot - k * dt))
                for k, x in enumerate(chemin)]
        cumul = [0.0]
        for k in range(n_pas):
            h = G.delta_straddle(chemin[k], S_REF, vol, t_tot - k * dt)
            cumul.append(cumul[-1] + (vals[k] - vals[k + 1]
                                      + h * (chemin[k + 1] - chemin[k])))
        lots.append((cumul[-1] / prime, tuple(x / prime for x in cumul),
                     tuple(chemin)))
    tri = sorted(lots, key=lambda x: x[0])
    median = tri[len(tri) // 2]
    gagnant = next((x for x in lots if x[0] > 0.5), tri[-1])
    perdant = next((x for x in lots if x[0] < -0.5), tri[0])
    return (("gagnant", gagnant[1], gagnant[2]),
            ("median", median[1], median[2]),
            ("perdant", perdant[1], perdant[2]))


LIBELLES = {
    "gagnant": "le loyer encaissé jusqu'au bout",
    "median": "le chemin médian",
    "perdant": "le loyer rendu en une séance",
}


def jour_de_la_perte(cumul: tuple[float, ...]) -> int:
    """Le jour où le chemin perd le plus, en une seule journée.

    C'est le nombre que la planche annonce, et il se calcule : la plus grande
    baisse d'un jour à l'autre, jamais le jour du minimum.
    """
    pires = [(cumul[k] - cumul[k - 1], k) for k in range(1, len(cumul))]
    return min(pires)[1]


# ---------------------------------------------------------------------------
# Valeurs, tables, et exécution directe
# ---------------------------------------------------------------------------


def values() -> dict[str, str]:
    c = simuler_vendeur()
    k, p = loi_de_dispersion()
    poids = poids_pour_apparents(1.0)
    un = campagne_prime(1.0)
    t30 = 30.0 / nv.JOURS_AN
    ti = termes_call(S_REF, S_REF, VOL_REF, 1.0)
    part = (abs(ti.interet) + abs(ti.portage)) / abs(ti.total)
    _, cumul, _ = chemins_temoins()[2]
    jp = jour_de_la_perte(cumul)
    return {
        "th_taux_intervalle": num(100 * taux_par_intervalle(), 1),
        "th_mediane_khi2": num(mediane_khi2(), 3),
        "th_taux_nu": num(100 * taux_du_vendeur_nu(), 1),
        "th_taux_nu_mesure": num(100 * c.nu.taux, 1),
        "th_taux_couvert": num(100 * c.couvert.taux, 1),
        "th_moyenne_couverte": num(100 * c.couvert.moyenne, 2, signed=True),
        "th_moyenne_nue": num(100 * c.nu.moyenne, 2, signed=True),
        "th_mediane_nue": num(100 * c.nu.mediane, 1, signed=True),
        "th_ecart_couvert": num(100 * c.couvert.ecart_type, 1),
        "th_ecart_nu": num(100 * c.nu.ecart_type, 1),
        "th_pire_nu": num(100 * c.nu.pire, 0, signed=True),
        "th_premier": num(100 * c.taux_premier, 1),
        "th_vie": num(100 * c.taux_intervalle, 1),
        "th_exposant": num(p, 3),
        "th_dispersion_1": num(100 * dispersion(1), 1),
        "th_dispersion_16": num(100 * dispersion(16), 2),
        "th_couvertures_pour_5": num(couvertures_pour_bruit(0.05), 0),
        "th_poids": num(poids, 4),
        "th_apparents": num(jours_apparents(poids), 2),
        "th_derive7": num(100 * derive_implicite(7.0, poids), 1),
        "th_derive30": num(100 * derive_implicite(30.0, poids), 1),
        "th_derive4": num(100 * derive_implicite(4.0, poids), 0),
        "th_critique": num(echeance_critique(SPREAD_VOL, poids), 0),
        "th_spread_vol": num(100 * SPREAD_VOL, 0),
        "th_frontiere30": num(frontiere_signe(t30), 3),
        "th_part0": num(100 * part_positive(0.0), 2),
        "th_part4": num(100 * part_positive(TAUX), 1),
        "th_annees_1pt": num(un.annees, 1),
        "th_expirations_1pt": num(un.expirations, 0),
        "th_taux_1pt": num(100 * un.taux, 1),
        "th_moyenne_1pt": num(100 * un.moyenne, 2),
        "th_annees_4pt": num(campagne_prime(4.0).annees, 1),
        "th_avantage_soiree": num(avantage_pour_egaler_la_soiree(), 1),
        "th_taux_2pt": num(100 * campagne_prime(2.0).taux, 1),
        "th_prime": num(100 * straddle(S_REF, S_REF, VOL_REF, JOURS_OPTION
                                       / nv.JOURS_AN) / S_REF, 2),
        "th_jours": num(JOURS_OPTION, 0),
        "th_vol": num(100 * VOL_REF, 0),
        "th_taux_pct": num(100 * TAUX, 1),
        "th_div_pct": num(100 * DIVIDENDE, 1),
        "th_chemins": num(N_CHEMINS, 0),
        "th_part_oubliee": num(100 * part, 0),
        "th_jour_perte": num(jp, 0),
        "th_perte_jour": num(100 * (cumul[jp - 1] - cumul[jp]), 0),
        "th_moitie_prime": num(100 * (1.0 - math.sqrt(22.5 / 90.0)), 0),
        "th_bourse": num(JOURS_BOURSE, 0),
        "th_rapport_horloges": num(nv.JOURS_AN / JOURS_BOURSE, 3),
        "th_affirmations": num(len(affirmations()), 0),
        "th_total_options": num(sum(n for _, n in familles()), 0),
        "th_horloge_n": num(compte_par_grandeur().get("l'horloge", 0), 0),
        "th_risque_n": num(compte_par_grandeur().get("le risque", 0), 0),
    }


def all_tables() -> dict[str, Table]:
    tables = [
        table_termes(), table_invariant(), table_frequence(),
        table_distribution(), table_couverture(), table_horloges(),
        table_poids(), table_signe(), table_preuve(), table_reste(),
    ]
    return {t.key: t for t in tables}


def main() -> None:
    for t in all_tables().values():
        print(t.to_text())
        print()
    for k, v in values().items():
        print(f"{k:24s} {v}")


if __name__ == "__main__":
    main()
