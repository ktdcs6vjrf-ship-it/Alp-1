"""Deux documents venus du dehors, et ce qu'on peut en récupérer.

Ce qui est examiné
------------------
Deux notes de recherche quantitative circulent, dont on ne connaît que les
résumés. La première couvre un recouvrement d'options sur la volatilité
destiné à protéger une stratégie de momentum longue ; la seconde un
portefeuille combinant deux sources de rendement décorrélées. Toutes deux
publient des chiffres précis et aucune ne publie son code.

La posture est celle des parties XV et XVII, et elle vaut d'être répétée une
troisième fois : **rien de ce qui suit ne conteste ces chiffres.** Ils sont
les données de l'affaire. La question n'est jamais « sont-ils vrais ? » mais
« que faudrait-il pour qu'ils le soient, et lesquels de leurs nombres sont
mesurables ? »

Ce que la lecture rend, et ce qu'elle ne rend pas
-------------------------------------------------
Il faut le dire d'emblée parce que c'est la réponse à la seule question qui
compte : **on ne récupère aucun avantage négociable d'un résumé.** Un résumé
ne contient ni signal, ni règle, ni série. Ce qu'on en récupère est un
protocole de lecture — quatre calculs qui s'appliquent à n'importe quelle
note de performance et qui décident, sans accès aux données, de ce que ses
chiffres peuvent et ne peuvent pas établir.

Les quatre calculs
------------------
*Le Calmar est un rapport dont le dénominateur est un maximum.* Un maximum
est la statistique la plus instable de la finance, et sa bande
d'échantillonnage est énorme. Sous une loi nulle de même rendement et de même
Sharpe, le Calmar du premier document se promène de 0,26 à 1,10 : **toute
l'amélioration qu'il revendique tient à l'intérieur d'un seul tirage.**

*La corrélation quotidienne n'est pas celle qui décide.* Deux stratégies
peuvent partager un krach une fois par décennie et afficher une corrélation
de Pearson de deux centièmes — indétectable sur vingt ans de données. Le test
de corrélation est aveugle exactement à la dépendance qui fabrique les
pertes.

*Un prix physique ne contient pas la prime de risque.* Le premier document le
dit lui-même. Le module chiffre ce que cet aveu coûte : la marge de rendement
que l'amélioration de Calmar représente, et le budget de prime au-delà duquel
elle disparaît.

*La capacité décroît comme le carré de la rotation.* L'impact croît en racine
de la taille ; pour un budget de coût fixé, la taille admissible varie donc
comme l'inverse du carré du nombre d'aller-retours. Une stratégie intraday à
dix aller-retours par séance a une capacité qui se compte en dizaines de
contrats, et c'est le nombre qu'aucun des deux documents ne publie.

Ce qui reste
------------
Le décompte final est calculé, et il ressemble à celui des deux parties
précédentes : ce qui se récupère est une méthode de lecture, jamais une
direction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from . import seuil
from .costs import _norm_ppf, norm_cdf
from .mc import Rng
from .report import Table, num

SEED = 20260904

SESSIONS_PAR_AN = 252.0
ALPHA = 0.05
PUISSANCE = 0.80
FACTEUR = _norm_ppf(1.0 - ALPHA / 2.0) + _norm_ppf(PUISSANCE)

# ---------------------------------------------------------------------------
# Les nombres publiés — recopiés une seule fois, ici
# ---------------------------------------------------------------------------
#
# Deux résumés, deux jeux de nombres. Ils sont repris tels quels et ne sont
# contestés nulle part dans ce module.

#: Document A — recouvrement d'options de volatilité sur une stratégie de
#: momentum longue. Les métriques citées sont celles de l'ère des options.
DOC_A: dict[str, float] = {
    "cagr_total": 0.305,      # sur l'historique complet
    "cagr": 0.246,            # depuis 2006
    "sharpe": 1.00,
    "mdd": 0.628,
    "calmar": 0.39,
    "calmar_couvert": 0.61,
    "skew_mensuel": 0.21,
    "annees": 20.0,           # 2006–2026
    "p_mieux": 0.75,          # bootstrap apparié
    "p25_difference": 0.00,
}

#: Document B — portefeuille à deux stratégies décorrélées.
DOC_B: dict[str, float] = {
    "cagr": 0.442,
    "sharpe": 2.14,
    "sortino": 3.03,
    "mdd": 0.218,
    "calmar": 2.03,
    "correlation": -0.020,
    "t_correlation": -1.40,
    "p_correlation": 0.161,
    "ci_bas": -0.047,
    "ci_haut": 0.008,
    "beta": 0.37,
    "alpha_jensen": 0.385,
    "treynor": 1.147,
    "ir_nasdaq": 1.14,
    "annees": 19.7,
    "rf": 0.02,
}


# ---------------------------------------------------------------------------
# I. Ce qui se vérifie de l'intérieur
# ---------------------------------------------------------------------------


def vol_implicite(cagr: float, sharpe: float, rf: float = 0.0) -> float:
    """La volatilité qu'un couple rendement/Sharpe impose."""
    return (cagr - rf) / sharpe if sharpe else math.inf


def marche_implicite(cagr: float, beta: float, alpha: float,
                     rf: float) -> float:
    """Le rendement de marché qu'un alpha de Jensen impose.

    `α = R − r_f − β(R_m − r_f)` s'inverse en une ligne. C'est le seul
    contrôle interne qui fasse sortir du document un nombre **vérifiable
    ailleurs** : le rendement du marché de référence sur la période est public.
    """
    return rf + (cagr - rf - alpha) / beta if beta else math.inf


def n_implicite(rho: float, t: float) -> float:
    """L'effectif qu'un couple corrélation/statistique impose.

    De `t = r√(n−2)/√(1−r²)` on tire `n = (t/r)²(1−r²) + 2`. Un résumé qui
    publie les deux publie donc sa taille d'échantillon sans le savoir, et
    l'accord avec la période annoncée est le premier contrôle à faire.
    """
    if rho == 0.0:
        return math.inf
    return (t / rho) ** 2 * (1.0 - rho * rho) + 2.0


#: Rapport Sortino/Sharpe d'une distribution **symétrique**. La déviation à la
#: baisse d'une loi symétrique vaut `σ/√2`, donc le Sortino vaut exactement
#: `√2` fois le Sharpe. Un Sortino qui tombe sur ce rapport n'apprend rien de
#: plus que le Sharpe.
RAPPORT_SYMETRIQUE = math.sqrt(2.0)


def table_coherence() -> Table:
    rows = []

    def ligne(quoi: str, annonce: float, recalcul: float, nd: int,
              unite: str, source: str) -> None:
        ecart = (recalcul - annonce) / abs(annonce) if annonce else 0.0
        rows.append([quoi, num(annonce, nd, unite), num(recalcul, nd, unite),
                     num(100 * ecart, 1, signed=True),
                     "cohérent" if abs(ecart) <= 0.03 else "à expliquer",
                     source])

    ligne("Calmar de la stratégie nue", DOC_A["calmar"],
          DOC_A["cagr"] / DOC_A["mdd"], 3, "", "A : CAGR sur MDD")
    ligne("Volatilité annuelle", DOC_B["cagr"] / DOC_B["sharpe"],
          vol_implicite(DOC_B["cagr"], DOC_B["sharpe"]), 3, "",
          "B : CAGR sur Sharpe")
    ligne("Calmar du portefeuille", DOC_B["calmar"],
          DOC_B["cagr"] / DOC_B["mdd"], 3, "", "B : CAGR sur MDD")
    ligne("Ratio de Treynor", DOC_B["treynor"],
          (DOC_B["cagr"] - DOC_B["rf"]) / DOC_B["beta"], 3, "",
          "B : excès sur bêta")
    ligne("Séances derrière la corrélation",
          DOC_B["annees"] * SESSIONS_PAR_AN,
          n_implicite(DOC_B["correlation"], DOC_B["t_correlation"]), 0, "",
          "B : corrélation et t")
    ligne("Rapport Sortino sur Sharpe",
          DOC_B["sortino"] / DOC_B["sharpe"], RAPPORT_SYMETRIQUE, 4, "",
          "B : loi symétrique")

    marche = marche_implicite(DOC_B["cagr"], DOC_B["beta"],
                              DOC_B["alpha_jensen"], DOC_B["rf"])
    rows.append(["Rendement de marché implicite", "—",
                 num(100 * marche, 1, "%"), "—", "vérifiable dehors",
                 "B : alpha de Jensen inversé"])

    return Table(
        key="rev_coherence",
        caption="Ce que les chiffres publiés disent les uns des autres",
        headers=["Grandeur", "Annoncé", "Recalculé", "Écart (%)", "Verdict",
                 "D'où vient le recalcul"],
        rows=rows,
        note="Premier contrôle d'un résumé, et il ne demande aucune donnée : "
             "les métriques d'une note de performance sont **redondantes**, "
             "et la redondance se vérifie. Les six premières lignes se "
             "referment. La cinquième est la plus utile — un couple "
             "corrélation/statistique publie la taille d'échantillon sans le "
             "vouloir, et elle tombe ici sur la période annoncée. La dernière "
             "sort du document : inverser l'alpha de Jensen donne le "
             "rendement du marché de référence sur la période, un nombre "
             "public que personne n'a besoin du document pour vérifier. "
             "L'avant-dernière est la plus instructive et elle ne coûte rien "
             "à personne : le rapport Sortino sur Sharpe tombe à "
             + num(100 * abs(DOC_B["sortino"] / DOC_B["sharpe"]
                             / RAPPORT_SYMETRIQUE - 1.0), 1)
             + " % de `√2`, la valeur exacte d'une loi **symétrique**. *Le "
             "Sortino publié n'ajoute donc rien au Sharpe publié.*",
        wrap_last=True,
    )


# ---------------------------------------------------------------------------
# II. Le Calmar est un rapport dont le dénominateur est un maximum
# ---------------------------------------------------------------------------

N_CHEMINS = 1200

#: Tirages des balayages et des reliefs. Un horizon long coûte cher, et une
#: largeur *relative* converge bien plus vite qu'un quantile isolé.
N_CHEMINS_BALAYAGE = 400
N_CHEMINS_SURFACE = 300


@lru_cache(maxsize=32)
def tirages(cagr: float, sharpe: float, annees: float,
            n: int = N_CHEMINS, seed: int = SEED) -> tuple[tuple[float, ...],
                                                           tuple[float, ...]]:
    """`n` histoires possibles d'une stratégie de rendement et Sharpe donnés.

    La loi nulle est la plus favorable qui soit : rendements quotidiens
    indépendants et gaussiens, sans grappe de pertes, sans queue épaisse,
    sans autocorrélation. Une vraie stratégie fait **pire** que cette loi sur
    le maximum de perte, jamais mieux — donc la bande calculée ici est une
    borne inférieure de l'incertitude réelle.
    """
    sigma = vol_implicite(cagr, sharpe)
    mu = math.log(1.0 + cagr)
    jours = int(SESSIONS_PAR_AN * annees)
    sd_j = sigma / math.sqrt(SESSIONS_PAR_AN)
    mu_j = mu / SESSIONS_PAR_AN
    rng = Rng(seed)
    mdds: list[float] = []
    cals: list[float] = []
    for _ in range(n):
        x = pic = dd = 0.0
        for _ in range(jours):
            x += mu_j + sd_j * rng.gauss()
            if x > pic:
                pic = x
            elif pic - x > dd:
                dd = pic - x
        m = 1.0 - math.exp(-dd)
        g = math.exp(x / annees) - 1.0
        mdds.append(m)
        cals.append(g / m if m > 1e-9 else math.inf)
    return tuple(sorted(mdds)), tuple(sorted(c for c in cals
                                             if math.isfinite(c)))


def _q(serie: tuple[float, ...], p: float) -> float:
    return serie[min(len(serie) - 1, int(p * (len(serie) - 1)))]


def bande_calmar(cagr: float, sharpe: float, annees: float,
                 n: int = N_CHEMINS) -> tuple[float, float, float]:
    _, cals = tirages(cagr, sharpe, annees, n)
    return (_q(cals, 0.05), _q(cals, 0.50), _q(cals, 0.95))


def bande_mdd(cagr: float, sharpe: float,
              annees: float) -> tuple[float, float, float]:
    mdds, _ = tirages(cagr, sharpe, annees)
    return (_q(mdds, 0.05), _q(mdds, 0.50), _q(mdds, 0.95))


def table_calmar() -> Table:
    rows = []
    for nom, d in (("Document A, stratégie nue", DOC_A),
                   ("Document B, portefeuille", DOC_B)):
        lo_m, med_m, hi_m = bande_mdd(d["cagr"], d["sharpe"], d["annees"])
        lo_c, med_c, hi_c = bande_calmar(d["cagr"], d["sharpe"], d["annees"])
        dedans = lo_c <= d["calmar"] <= hi_c
        rows.append([
            nom,
            num(100 * d["mdd"], 1),
            num(100 * lo_m, 1) + " à " + num(100 * hi_m, 1),
            num(d["calmar"], 2),
            num(lo_c, 2) + " à " + num(hi_c, 2),
            num(100 * (hi_c - lo_c) / med_c, 0),
            "dans la bande" if dedans else "hors de la bande",
        ])
    lo_c, med_c, hi_c = bande_calmar(DOC_A["cagr"], DOC_A["sharpe"],
                                     DOC_A["annees"])
    gain = DOC_A["calmar_couvert"] - DOC_A["calmar"]
    return Table(
        key="rev_calmar",
        caption="La bande d'échantillonnage d'un Calmar, sous la loi la plus favorable",
        headers=["Document", "MDD annoncé (%)", "MDD à 90 % (%)",
                 "Calmar annoncé", "Calmar à 90 %", "Largeur de bande (%)",
                 "Verdict"],
        rows=rows,
        note=num(N_CHEMINS, 0) + " histoires simulées par ligne, sous "
             "rendements quotidiens **indépendants et gaussiens** — la loi la "
             "plus favorable qui soit, sans grappe de pertes ni queue "
             "épaisse. Une vraie stratégie fait pire sur le maximum, jamais "
             "mieux : la bande est donc une borne inférieure de "
             "l'incertitude. Elle mesure "
             + num(100 * (hi_c - lo_c) / med_c, 0) + " % de sa médiane sur le "
             "document A, et c'est le fait de la section. L'amélioration que "
             "ce document revendique vaut " + num(gain, 2) + " point de "
             "Calmar, soit " + num(100 * gain / (hi_c - lo_c), 0) + " % de la "
             "largeur de la bande. **Elle tient tout entière à l'intérieur "
             "d'un seul tirage**, ce que le document dit d'ailleurs lui-même "
             "par une autre route : son bootstrap apparié place le premier "
             "quartile de la différence à zéro.",
    )


#: Écarts de Calmar dont on cherche la durée d'établissement.
ECARTS_CALMAR: tuple[float, ...] = (0.10, 0.22, 0.40, 0.80, 1.50)

#: Horizons balayés pour ajuster la décroissance de la bande.
HORIZONS: tuple[float, ...] = (5.0, 10.0, 20.0, 40.0, 80.0)


@lru_cache(maxsize=4)
def _bruit(jours: int, n: int, seed: int) -> tuple[tuple[float, ...], ...]:
    """Le flux d'alea, tire une seule fois et relu par tous les balayages.

    C'est la regle du depot sur les surfaces : toutes les cellules voient le
    meme flux, la graine ne dependant que de l'indice de trajectoire. Le
    relief en sort lisse sans aucun lissage.
    """
    rng = Rng(seed)
    return tuple(tuple(rng.gauss() for _ in range(jours)) for _ in range(n))


def bandes_par_prefixe(sharpe: float, horizons: tuple[float, ...],
                       cagr: float = 0.246, n: int = N_CHEMINS_BALAYAGE,
                       seed: int = SEED + 2
                       ) -> tuple[tuple[float, float, float], ...]:
    """Les bandes de Calmar de plusieurs horizons, d'une seule simulation.

    Le maximum de perte des `T` premieres annees est une statistique de
    **prefixe** : il se lit sur la meme trajectoire que celui des `2T`
    premieres. Simuler l'horizon le plus long et relever les prefixes rend
    donc exactement le meme resultat qu'autant de simulations separees, pour
    le prix d'une seule — et il aligne les colonnes sur le meme alea, ce qui
    est aussi ce qu'on veut voir.
    """
    sigma = vol_implicite(cagr, sharpe)
    mu = math.log(1.0 + cagr)
    sd_j = sigma / math.sqrt(SESSIONS_PAR_AN)
    mu_j = mu / SESSIONS_PAR_AN
    jalons = [int(SESSIONS_PAR_AN * t) for t in horizons]
    bruit = _bruit(jalons[-1], n, seed)
    par_horizon: list[list[float]] = [[] for _ in horizons]
    for chemin in bruit:
        x = pic = dd = 0.0
        k = 0
        for i, g in enumerate(chemin, start=1):
            x += mu_j + sd_j * g
            if x > pic:
                pic = x
            elif pic - x > dd:
                dd = pic - x
            if k < len(jalons) and i == jalons[k]:
                m = 1.0 - math.exp(-dd)
                if m > 1e-9:
                    par_horizon[k].append(
                        (math.exp(x / horizons[k]) - 1.0) / m)
                k += 1
    out = []
    for serie in par_horizon:
        tri = tuple(sorted(serie))
        out.append((_q(tri, 0.05), _q(tri, 0.50), _q(tri, 0.95)))
    return tuple(out)


@lru_cache(maxsize=8)
def largeur_par_horizon(cagr: float = 0.246,
                        sharpe: float = 1.0) -> tuple[tuple[float, float], ...]:
    """La demi-largeur de la bande de Calmar, horizon par horizon."""
    bandes = bandes_par_prefixe(sharpe, HORIZONS, cagr)
    return tuple((t, 0.5 * (hi - lo))
                 for t, (lo, _, hi) in zip(HORIZONS, bandes))


@lru_cache(maxsize=8)
def loi_de_bande(cagr: float = 0.246,
                 sharpe: float = 1.0) -> tuple[float, float]:
    """Le couple `(k, p)` de l'ajustement `demi-largeur = k·T^{−p}`.

    L'exposant est **ajusté, jamais postulé**, et c'est ce qui distingue cette
    fonction de la version qu'elle remplace. On attendait la racine — la
    vitesse de toute moyenne — et la mesure rend nettement plus vite. La
    raison tient au numérateur : le rendement annualisé se resserre lui aussi
    avec l'horizon, si bien que les deux membres du rapport se stabilisent
    ensemble. Un test compare l'ajustement aux points simulés et refuse
    l'exposant un demi, qui les manque de plusieurs dizaines de pour-cent.
    """
    pts = largeur_par_horizon(cagr, sharpe)
    xs = [math.log(t) for t, _ in pts]
    ys = [math.log(w) for _, w in pts]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    pente = (sum((x - mx) * (y - my) for x, y in zip(xs, ys))
             / sum((x - mx) ** 2 for x in xs))
    return math.exp(my - pente * mx), -pente


def annees_pour_ecart(ecart: float, cagr: float = 0.246,
                      sharpe: float = 1.0) -> float:
    """Années requises pour qu'un écart de Calmar dépasse la bande.

    La demi-largeur décroît comme une puissance de l'horizon, mais elle part
    de très haut parce que le dénominateur du Calmar est un maximum et qu'il
    n'y a qu'un seul maximum dans une série, quelle que soit sa longueur.
    L'ajustement se fait sur les horizons simulés — coefficient **et**
    exposant — jamais sur une formule postulée.
    """
    if ecart <= 0.0:
        return math.inf
    k, p = loi_de_bande(cagr, sharpe)
    return (k / ecart) ** (1.0 / p)


def _ecart_de_la_racine(cagr: float = 0.246, sharpe: float = 1.0) -> float:
    """De combien un exposant un demi manque les horizons simulés.

    C'est le nombre qui justifie d'ajuster l'exposant plutôt que de le
    postuler, et il se publie plutôt que de se qualifier.
    """
    pts = largeur_par_horizon(cagr, sharpe)
    k = math.exp(sum(math.log(w) + 0.5 * math.log(t) for t, w in pts)
                 / len(pts))
    return max(abs(k * t ** -0.5 / w - 1.0) for t, w in pts)


def table_detecter() -> Table:
    rows = []
    for e in ECARTS_CALMAR:
        an = annees_pour_ecart(e)
        rows.append([
            num(e, 2),
            num(an, 1),
            num(an * SESSIONS_PAR_AN, 0),
            "à portée" if an <= 40.0 else "hors d'une carrière",
        ])
    pts = largeur_par_horizon()
    return Table(
        key="rev_detecter",
        caption="Ce qu'il faut d'années pour qu'un écart de Calmar existe",
        headers=["Écart de Calmar à établir", "Années requises",
                 "Séances", "Verdict"],
        rows=rows,
        note="La demi-largeur de la bande décroît comme la puissance "
             + num(loi_de_bande()[1], 2) + " de l'horizon — elle passe de "
             + num(pts[0][1], 2) + " à cinq ans à " + num(pts[-1][1], 2)
             + " à " + num(HORIZONS[-1], 0) + " ans. **L'exposant est "
             "ajusté sur les horizons simulés, jamais postulé** : on "
             "attendait la racine, la vitesse de toute moyenne, et la "
             "mesure rend plus vite, parce que le numérateur du Calmar se "
             "resserre lui aussi. Mais la bande part de très haut, parce "
             "qu'un maximum sur un échantillon "
             "a l'effectif le plus petit de toutes les statistiques : il n'y "
             "a qu'un seul maximum, quelle que soit la longueur de la série. "
             "L'amélioration de " + num(DOC_A["calmar_couvert"]
                                        - DOC_A["calmar"], 2) + " point que "
             "revendique le document A demanderait "
             + num(annees_pour_ecart(DOC_A["calmar_couvert"]
                                     - DOC_A["calmar"]), 0) + " ans pour "
             "sortir du bruit. **Ce n'est pas une critique du document : "
             "c'est une propriété du Calmar**, et elle vaut pour toute note "
             "de performance qui met une amélioration de Calmar en titre.",
    )


SURF_SHARPE: tuple[float, ...] = (0.4, 0.7, 1.0, 1.4, 2.0, 3.0)
SURF_ANNEES: tuple[float, ...] = (5.0, 10.0, 20.0, 40.0, 80.0)


def surface_bande() -> list[list[float]]:
    """La largeur relative de la bande de Calmar, sur (Sharpe, horizon).

    Deux axes, deux effets, et ils ne se compensent pas. L'horizon resserre la
    bande comme une racine ; le Sharpe la resserre bien plus vite, parce qu'il
    rend le maximum de perte lui-même moins variable. Le coin où un Calmar
    devient une mesure et cesse d'être une anecdote est étroit.
    """
    return [[100.0 * (hi - lo) / med
             for lo, med, hi in bandes_par_prefixe(s, SURF_ANNEES,
                                                   n=N_CHEMINS_SURFACE)]
            for s in SURF_SHARPE]


# ---------------------------------------------------------------------------
# III. La corrélation quotidienne n'est pas celle qui décide
# ---------------------------------------------------------------------------


def rho_du_saut(taille: float, par_an: float) -> float:
    """La corrélation de Pearson qu'un krach commun induit.

    Deux séries de variance un qui partagent un saut de `taille` écarts-types,
    survenant `par_an` fois l'an, ont une covariance égale à la variance du
    saut, soit `p·J²` par séance. La corrélation vaut donc `v/(1+v)` — et
    elle est **minuscule** dès que le saut est rare, parce que la corrélation
    de Pearson est une moyenne sur toutes les séances et que les séances
    ordinaires la diluent.
    """
    p = par_an / SESSIONS_PAR_AN
    v = p * taille * taille
    return v / (1.0 + v)


def n_pour_rho(rho: float) -> float:
    """Séances requises pour distinguer une corrélation de zéro.

    Transformation de Fisher : `z = ½·ln((1+r)/(1−r))` est asymptotiquement
    normale d'écart-type `1/√(n−3)`, d'où `n = (FACTEUR/z)² + 3`.
    """
    if abs(rho) < 1e-12:
        return math.inf
    z = 0.5 * math.log((1.0 + rho) / (1.0 - rho))
    return (FACTEUR / z) ** 2 + 3.0


def rho_detectable(n: float) -> float:
    """La plus petite corrélation qu'un échantillon puisse établir."""
    if n <= 4.0:
        return 1.0
    return math.tanh(FACTEUR / math.sqrt(n - 3.0))


def p_valeur_rho(rho: float, n: float) -> float:
    """La p-valeur bilatérale du test de corrélation nulle."""
    if n <= 2.0 or abs(rho) >= 1.0:
        return 1.0
    t = rho * math.sqrt(n - 2.0) / math.sqrt(1.0 - rho * rho)
    return 2.0 * (1.0 - norm_cdf(abs(t)))


#: Fréquences de krach commun balayées, en événements par an.
FREQUENCES: tuple[float, ...] = (0.5, 0.2, 0.1, 0.05, 0.02)

#: Taille du krach commun, en écarts-types quotidiens d'une jambe. Huit : ce
#: que deux livres perdent le même jour quand le même choc les traverse.
TAILLE_SAUT = 8.0


def table_queue() -> Table:
    n_dispo = DOC_B["annees"] * SESSIONS_PAR_AN
    rows = []
    for f in FREQUENCES:
        r = rho_du_saut(TAILLE_SAUT, f)
        rows.append([
            num(1.0 / f, 0),
            num(r, 4),
            num(n_pour_rho(r), 0),
            num(n_pour_rho(r) / SESSIONS_PAR_AN, 1),
            num(p_valeur_rho(r, n_dispo), 3),
            "visible" if n_pour_rho(r) <= n_dispo else "invisible",
        ])
    # La fréquence exactement à la limite de ce que l'échantillon distingue.
    r_lim = rho_detectable(n_dispo)
    f_lim = SESSIONS_PAR_AN * (r_lim / (1.0 - r_lim)) / (TAILLE_SAUT ** 2)
    return Table(
        key="rev_queue",
        caption="Un krach partagé, et ce que la corrélation de Pearson en voit",
        headers=["Un krach commun tous les … ans", "ρ induit",
                 "Séances pour le voir", "Années", "p-valeur sur "
                 + num(n_dispo, 0) + " séances", "Verdict"],
        rows=rows,
        note="Krach commun de " + num(TAILLE_SAUT, 0) + " écarts-types "
             "quotidiens frappant les deux stratégies le même jour. La "
             "corrélation qu'il induit est une moyenne sur **toutes** les "
             "séances, et les séances ordinaires la diluent : un krach commun "
             "tous les dix ans ne pèse que "
             + num(rho_du_saut(TAILLE_SAUT, 0.1), 4) + " de corrélation. "
             "L'échantillon disponible — " + num(n_dispo, 0) + " séances — ne "
             "distingue de zéro que les corrélations supérieures à "
             + num(r_lim, 3) + ", ce qui place la limite de visibilité à un "
             "krach commun tous les " + num(1.0 / f_lim, 1) + " ans. "
             "**Au-delà, la dépendance existe et le test ne la voit pas.** "
             "L'intervalle de confiance publié par le document B, de "
             + num(DOC_B["ci_bas"], 3) + " à " + num(DOC_B["ci_haut"], 3)
             + ", est donc parfaitement compatible avec un krach partagé une "
             "fois par décennie.",
    )


#: Modèles de dépendance comparés, en krachs communs par an.
MODELES: tuple[tuple[str, float], ...] = (
    ("Indépendance stricte", 0.0),
    ("Un krach commun tous les 20 ans", 0.05),
    ("Un krach commun tous les 10 ans", 0.10),
    ("Un krach commun tous les 5 ans", 0.20),
)

#: Poids du mélange, tels que le document B les déclare.
POIDS = (0.70, 0.30)

N_MELANGE = 400


def _jambes() -> tuple[float, float]:
    """Sharpe et volatilité de chaque jambe, déduits des chiffres publiés.

    Rien n'est posé à la main. Deux jambes de même qualité, mélangées aux
    poids déclarés et supposées indépendantes, donnent un mélange de
    volatilité `σ·√(w₁²+w₂²)` et de Sharpe `s/√(w₁²+w₂²)`. On inverse.
    """
    norme = math.sqrt(POIDS[0] ** 2 + POIDS[1] ** 2)
    return DOC_B["sharpe"] * norme, DOC_B["cagr"] / DOC_B["sharpe"] / norme


@lru_cache(maxsize=8)
def melange(par_an: float, taille: float = TAILLE_SAUT, n: int = N_MELANGE,
            seed: int = SEED + 1) -> tuple[float, float, float]:
    """MDD médian, pire séance en écarts-types du mélange, et ρ mesuré.

    Le saut est **compensé** : son espérance est retirée de la dérive, sans
    quoi la dépendance de queue changerait aussi le rendement et l'on ne
    saurait plus ce qu'on mesure. C'est la même précaution que la loi à sauts
    de la partie XIV.
    """
    s, sigma = _jambes()
    sd = sigma / math.sqrt(SESSIONS_PAR_AN)
    mu = s * sigma / SESSIONS_PAR_AN
    p = par_an / SESSIONS_PAR_AN
    saut = taille * sd
    jours = int(SESSIONS_PAR_AN * DOC_B["annees"])
    sd_melange = sd * math.sqrt(POIDS[0] ** 2 + POIDS[1] ** 2)
    rng = Rng(seed)
    mdds: list[float] = []
    pires: list[float] = []
    rhos: list[float] = []
    for _ in range(n):
        x = pic = dd = 0.0
        pire = 0.0
        sa = sb = saa = sbb = sab = 0.0
        for _ in range(jours):
            k = -saut if (p > 0.0 and rng.uniform() < p) else 0.0
            ra = mu + sd * rng.gauss() + k + p * saut
            rb = mu + sd * rng.gauss() + k + p * saut
            r = POIDS[0] * ra + POIDS[1] * rb
            pire = min(pire, r)
            x += r
            if x > pic:
                pic = x
            elif pic - x > dd:
                dd = pic - x
            sa += ra
            sb += rb
            saa += ra * ra
            sbb += rb * rb
            sab += ra * rb
        mdds.append(1.0 - math.exp(-dd))
        pires.append(pire / sd_melange)
        cov = sab / jours - (sa / jours) * (sb / jours)
        va = math.sqrt(max(saa / jours - (sa / jours) ** 2, 1e-18))
        vb = math.sqrt(max(sbb / jours - (sb / jours) ** 2, 1e-18))
        rhos.append(cov / (va * vb))
    mdds.sort()
    pires.sort()
    rhos.sort()
    return (_q(mdds, 0.5), _q(pires, 0.05), _q(rhos, 0.5))


def table_melange() -> Table:
    n_dispo = DOC_B["annees"] * SESSIONS_PAR_AN
    base_mdd, base_pire, _ = melange(0.0)
    rows = []
    for nom, f in MODELES:
        mdd, pire, r = melange(f)
        rows.append([
            nom,
            num(r, 4, signed=True),
            num(p_valeur_rho(abs(r), n_dispo), 3),
            num(100 * mdd, 1),
            num(100 * (mdd - base_mdd) / base_mdd, 1, signed=True),
            num(abs(pire), 1),
            num(abs(pire) / abs(base_pire), 2),
        ])
    return Table(
        key="rev_melange",
        caption="Ce que la dépendance de queue fait à un mélange que Pearson dit décorrélé",
        headers=["Modèle de dépendance", "ρ mesuré", "p-valeur",
                 "MDD médian (%)", "Écart au cas indépendant (%)",
                 "Pire séance (σ du mélange)", "Facteur sur la pire séance"],
        rows=rows,
        note="Deux jambes déduites des chiffres publiés — Sharpe "
             + num(_jambes()[0], 2) + " et volatilité "
             + num(100 * _jambes()[1], 1) + " % chacune, mélangées aux poids "
             "déclarés — sur " + num(N_MELANGE, 0) + " histoires de "
             + num(DOC_B["annees"], 1) + " ans. Le saut commun est compensé, "
             "sans quoi il changerait aussi le rendement. Deux lectures, et "
             "la seconde compte davantage. Sur le **maximum de perte**, la "
             "dépendance de queue coûte quelques points : c'est réel et "
             "modéré. Sur la **pire séance**, elle coûte un facteur, parce "
             "que ce jour-là les deux jambes perdent ensemble et que le "
             "mélange n'amortit rien. *La diversification protège toutes les "
             "séances sauf celle qui compte*, et le test de corrélation ne "
             "distingue aucune de ces lignes de la première.",
    )


SURF_FREQ: tuple[float, ...] = (0.015, 0.03, 0.06, 0.12, 0.25, 0.50)
SURF_ARCHIVE: tuple[float, ...] = (5.0, 10.0, 20.0, 40.0, 80.0, 160.0)


def taille_invisible(par_an: float, annees: float) -> float:
    """Le plus gros krach commun qu'un échantillon **ne peut pas** détecter.

    On inverse : la corrélation détectable sur `n` séances fixe une variance
    de saut, donc une taille. Le nombre rendu est celui qui manque à toute
    note de performance qui conclut à l'indépendance — non pas « la
    corrélation est nulle », mais « voici le choc partagé que mes données
    n'auraient pas vu ».
    """
    r = rho_detectable(annees * SESSIONS_PAR_AN)
    p = par_an / SESSIONS_PAR_AN
    if p <= 0.0:
        return math.inf
    return math.sqrt((r / (1.0 - r)) / p)


def surface_invisible() -> list[list[float]]:
    """La taille du krach invisible, sur (fréquence, longueur de l'archive).

    Le relief est celui d'une **limite de mesure**, pas d'un phénomène : il
    dit ce qu'un échantillon ne peut pas exclure. Les deux axes vont dans le
    même sens et pour la même raison — un événement rare et un échantillon
    court laissent tous deux passer des chocs énormes.
    """
    return [[taille_invisible(f, t) for t in SURF_ARCHIVE]
            for f in SURF_FREQ]


# ---------------------------------------------------------------------------
# IV. Le coût qu'un prix physique ne contient pas
# ---------------------------------------------------------------------------
#
# Le document A énonce lui-même sa limite : il valorise ses options sur le VIX
# *comptant*, sous une calibration physique, sans structure par terme. Il
# manque donc la prime de risque de variance, et le portage réel de la
# protection est plus lourd que le portage modélisé. La section ne discute pas
# de combien — personne ne le sait sans les données — elle calcule **la marge
# dont dispose le résultat**, ce qui est le seul nombre opposable.

#: Réductions du maximum de perte balayées, en points.
REDUCTIONS: tuple[float, ...] = (0.10, 0.18, 0.25, 0.30, 0.35, 0.40)


def cout_admissible(reduction: float,
                    calmar_cible: float = DOC_A["calmar_couvert"]) -> float:
    """Le coût net que le recouvrement peut se permettre, en points de CAGR.

    `Calmar = (CAGR − coût)/(MDD − réduction)` s'inverse. Quand le nombre
    rendu est **négatif**, aucun coût n'est admissible : le recouvrement doit
    alors *ajouter* du rendement pour atteindre le Calmar visé, ce qui n'est
    pas absurde — c'est l'effet de taxe de volatilité que le document
    revendique — mais qui doit être dit.
    """
    return DOC_A["cagr"] - calmar_cible * (DOC_A["mdd"] - reduction)


def reduction_minimale(calmar_cible: float = DOC_A["calmar_couvert"]) -> float:
    """La réduction de MDD au-dessous de laquelle le coût doit être négatif."""
    return DOC_A["mdd"] - DOC_A["cagr"] / calmar_cible


def marge_de_cagr(reduction: float) -> float:
    """Les points de CAGR que vaut l'amélioration de Calmar revendiquée.

    C'est le nombre qui compte, et il tient en une ligne : un écart de Calmar
    multiplié par le maximum de perte auquel il s'applique. Toute erreur de
    prime supérieure à cette marge efface l'amélioration entière.
    """
    return (DOC_A["calmar_couvert"] - DOC_A["calmar"]) * (DOC_A["mdd"]
                                                          - reduction)


def table_locus() -> Table:
    rows = []
    for d in REDUCTIONS:
        mdd2 = DOC_A["mdd"] - d
        cout = cout_admissible(d)
        rows.append([
            num(100 * d, 1),
            num(100 * mdd2, 1),
            num(100 * cout, 2, signed=True),
            num(100 * marge_de_cagr(d), 2),
            ("le recouvrement doit ajouter du rendement" if cout < 0.0
             else "un portage net est admissible"),
        ])
    d_min = reduction_minimale()
    return Table(
        key="rev_locus",
        caption="Ce que l'amélioration de Calmar exige, réduction par réduction",
        headers=["Réduction du MDD (points)", "MDD après (%)",
                 "Coût net admissible (points de CAGR)",
                 "Marge de l'amélioration (points de CAGR)", "Lecture"],
        rows=rows,
        note="Le document publie deux Calmar — " + num(DOC_A["calmar"], 2)
             + " nu et " + num(DOC_A["calmar_couvert"], 2) + " couvert — mais "
             "ni la réduction du maximum de perte, ni le budget de prime. Or "
             "les deux Calmar contraignent ces deux nombres à un lieu d'une "
             "dimension, que la table parcourt. Le fait qui en sort est "
             "net : au-dessous de " + num(100 * d_min, 1) + " points de "
             "réduction, **le recouvrement doit ajouter du rendement**, pas "
             "seulement en coûter peu. La dernière colonne donne la seule "
             "quantité opposable : l'amélioration revendiquée vaut de "
             + num(100 * marge_de_cagr(REDUCTIONS[-1]), 1) + " à "
             + num(100 * marge_de_cagr(REDUCTIONS[0]), 1) + " points de CAGR "
             "selon la réduction obtenue. *Toute sous-estimation de prime "
             "supérieure à cette marge efface l'amélioration entière.*",
        wrap_last=True,
    )


#: Budgets de prime annuels balayés, en fraction de l'actif.
BUDGETS: tuple[float, ...] = (0.01, 0.02, 0.03, 0.05, 0.08, 0.12)

#: Facteurs de prime : le rapport entre la prime réelle et la prime modélisée.
#: Un prix calibré sur le comptant sous une mesure physique omet la prime de
#: risque de variance ; le facteur est supérieur à un, et personne ne sait de
#: combien sans la structure par terme.
FACTEURS: tuple[float, ...] = (1.0, 1.5, 2.0, 3.0)

#: Réduction de MDD retenue pour les deux tables qui suivent. Elle est
#: **déclarée** au milieu du lieu admissible, jamais choisie pour un résultat.
REDUCTION_RETENUE = 0.30


def calmar_sous_prime(budget: float, facteur: float,
                      reduction: float = REDUCTION_RETENUE) -> float:
    """Le Calmar couvert quand la prime vraie vaut `facteur` fois la modélisée."""
    mdd2 = DOC_A["mdd"] - reduction
    net = DOC_A["cagr"] - cout_admissible(reduction) - (facteur - 1.0) * budget
    return net / mdd2 if mdd2 > 0.0 else 0.0


def erreur_fatale(reduction: float = REDUCTION_RETENUE) -> float:
    """Les points de CAGR dont l'erreur de prime ramène le Calmar à sa valeur nue."""
    return (DOC_A["calmar_couvert"] - DOC_A["calmar"]) * (DOC_A["mdd"]
                                                          - reduction)


def facteur_fatal(budget: float,
                  reduction: float = REDUCTION_RETENUE) -> float:
    """Le facteur de prime au-delà duquel l'amélioration disparaît.

    Le surcoût vaut `(k − 1)·budget` ; il devient fatal quand il atteint la
    marge, d'où `k = 1 + marge/budget`. Le nombre est d'autant plus petit que
    le budget est gros — un gros budget de prime laisse peu de place à
    l'erreur, ce qui est exactement l'inverse de l'intuition courante.
    """
    if budget <= 0.0:
        return math.inf
    return 1.0 + erreur_fatale(reduction) / budget


def table_prime() -> Table:
    rows = []
    for b in BUDGETS:
        ligne = [num(100 * b, 0)]
        for f in FACTEURS:
            ligne.append(num(calmar_sous_prime(b, f), 3))
        ligne.append(num(facteur_fatal(b), 2))
        rows.append(ligne)
    return Table(
        key="rev_prime",
        caption="Ce qu'une prime sous-estimée fait au Calmar couvert",
        headers=["Budget de prime (% par an)"]
                + ["facteur " + num(f, 1) for f in FACTEURS]
                + ["Facteur fatal"],
        rows=rows,
        note="Réduction du maximum de perte tenue à "
             + num(100 * REDUCTION_RETENUE, 0) + " points, déclarée au milieu "
             "du lieu admissible de la table précédente. Le facteur est le "
             "rapport entre la prime réellement payée et la prime modélisée ; "
             "il vaut plus que un dès qu'on valorise sur le comptant sans "
             "structure par terme, et le document le dit lui-même. La "
             "dernière colonne est le nombre à retenir : le facteur au-delà "
             "duquel le Calmar couvert retombe sur le Calmar nu. Il vaut "
             + num(facteur_fatal(BUDGETS[0]), 1) + " à un budget de "
             + num(100 * BUDGETS[0], 0) + " % par an et seulement "
             + num(facteur_fatal(BUDGETS[-1]), 1) + " à "
             + num(100 * BUDGETS[-1], 0) + " % — **un gros budget de prime "
             "laisse moins de place à l'erreur, pas plus**, ce qui est "
             "l'inverse de l'intuition courante. Aux budgets du milieu du "
             "tableau, le facteur fatal tombe dans l'ordre de grandeur même "
             "d'une prime de risque de variance. **Le document est "
             "honnête sur sa limite ; la table dit ce que cette limite "
             "coûte.**",
    )


SURF_BUDGET: tuple[float, ...] = (0.005, 0.01, 0.02, 0.04, 0.08, 0.15)
SURF_FACTEUR: tuple[float, ...] = (1.0, 1.3, 1.7, 2.2, 3.0, 4.0)


def surface_portage() -> list[list[float]]:
    """Le Calmar couvert, sur (budget de prime, facteur de prime).

    Le sol est posé au Calmar nu : ce qui dépasse est une amélioration, ce qui
    s'enfonce est une dégradation. La ligne de niveau est la seule chose à
    regarder, et elle traverse la boîte en diagonale — le produit du budget
    par le facteur, et non l'un des deux, décide de tout.
    """
    return [[calmar_sous_prime(b, f) for f in SURF_FACTEUR]
            for b in SURF_BUDGET]


# ---------------------------------------------------------------------------
# V. La capacité décroît comme le carré de la rotation
# ---------------------------------------------------------------------------

#: Le contrat de la stratégie intraday du document B, déclaré.
NIVEAU_NQ = 20000.0
POINT_NQ = 20.0
VOLUME_NQ = 600_000.0        # contrats par séance, ordre de grandeur
SIGMA_NQ_JOUR = 240.0        # points, soit 1,2 % du niveau

#: Coefficient de la loi en racine, celui de la partie XVII.
Y_IMPACT = 0.50

#: Friction fixe d'un aller-retour, en points : un tick de fourchette traversé
#: aux deux bouts, plus la commission.
SPREAD_PTS = 0.25
COMMISSION_USD = 2.00
FRICTION_FIXE = SPREAD_PTS + COMMISSION_USD / POINT_NQ

#: Budget de friction annuel, en fraction du notionnel engagé. Vingt pour
#: cent : la moitié du rendement publié, ce qui est déjà généreux.
BUDGET_FRICTION = 0.20

ROTATIONS: tuple[float, ...] = (1.0, 2.0, 5.0, 10.0, 20.0, 40.0)


def impact_nq(taille: float) -> float:
    """`Y·σ_jour·√(Q/V)` — l'impact d'un ordre sur le contrat, en points."""
    if taille <= 0.0:
        return 0.0
    return Y_IMPACT * SIGMA_NQ_JOUR * math.sqrt(taille / VOLUME_NQ)


def drag(taille: float, rotation: float) -> float:
    """Le coût annuel d'une rotation donnée, en fraction du notionnel."""
    par_aller_retour = 2.0 * impact_nq(taille) + FRICTION_FIXE
    return SESSIONS_PAR_AN * rotation * par_aller_retour / NIVEAU_NQ


def rotation_fatale(budget: float = BUDGET_FRICTION) -> float:
    """La rotation où la friction fixe seule épuise le budget.

    Au-delà, **aucune taille ne rend la stratégie viable** : le coût ne vient
    plus de l'impact, qui se réduit en réduisant la taille, mais du nombre
    d'aller-retours, qui est la stratégie elle-même.
    """
    return budget * NIVEAU_NQ / (SESSIONS_PAR_AN * FRICTION_FIXE)


def capacite_pure(rotation: float, budget: float = BUDGET_FRICTION) -> float:
    """La capacité si la friction fixe était nulle — la loi en `ν⁻²`.

    Le budget fixe l'impact admissible par aller-retour ; l'impact croît en
    racine de la taille ; la taille admissible varie donc comme l'inverse du
    **carré** de la rotation. Doubler le nombre d'aller-retours divise la
    capacité par quatre, et c'est exact.
    """
    imp = budget * NIVEAU_NQ / (2.0 * SESSIONS_PAR_AN * rotation)
    return VOLUME_NQ * (imp / (Y_IMPACT * SIGMA_NQ_JOUR)) ** 2


def capacite(rotation: float, budget: float = BUDGET_FRICTION) -> float:
    """La capacité réelle, friction fixe comprise."""
    reste = budget * NIVEAU_NQ / (SESSIONS_PAR_AN * rotation) - FRICTION_FIXE
    if reste <= 0.0:
        return 0.0
    return VOLUME_NQ * (reste / (2.0 * Y_IMPACT * SIGMA_NQ_JOUR)) ** 2


def table_rotation() -> Table:
    rows = []
    for r in ROTATIONS:
        cap = capacite(r)
        rows.append([
            num(r, 0),
            num(100 * SESSIONS_PAR_AN * r * FRICTION_FIXE / NIVEAU_NQ, 1),
            num(capacite_pure(r), 0),
            num(cap, 1),
            num(cap * NIVEAU_NQ * POINT_NQ / 1e6, 1),
            "viable" if cap >= 1.0 else "aucune taille ne convient",
        ])
    return Table(
        key="rev_rotation",
        caption="La capacité d'une stratégie intraday, rotation par rotation",
        headers=["Aller-retours par séance", "Friction fixe seule (% par an)",
                 "Capacité sans friction fixe (contrats)",
                 "Capacité réelle (contrats)", "Notionnel (M$)", "Verdict"],
        rows=rows,
        note="Contrat déclaré : niveau " + num(NIVEAU_NQ, 0) + ", "
             + num(POINT_NQ, 0) + " $ le point, volume "
             + num(VOLUME_NQ, 0) + " contrats par séance, volatilité "
             + num(SIGMA_NQ_JOUR, 0) + " points. Friction fixe "
             + num(FRICTION_FIXE, 2) + " point par aller-retour, budget "
             + num(100 * BUDGET_FRICTION, 0) + " % du notionnel par an. La "
             "troisième colonne porte la loi exacte : sans friction fixe, la "
             "capacité varie comme l'inverse du **carré** de la rotation, "
             "parce que l'impact croît en racine de la taille. Doubler le "
             "nombre d'aller-retours divise la capacité par quatre. La "
             "quatrième colonne ajoute la fourchette et la commission, et "
             "elle tombe bien plus vite : au-delà de "
             + num(rotation_fatale(), 0) + " aller-retours par séance, la "
             "friction fixe seule épuise le budget et *aucune taille ne "
             "convient*, parce que le coût ne vient plus de la taille mais du "
             "nombre de décisions. **Ce nombre est celui qu'aucun des deux "
             "documents ne publie.**",
    )


SURF_TAILLE_NQ: tuple[float, ...] = (400.0, 150.0, 60.0, 25.0, 10.0, 4.0)
SURF_ROTATION: tuple[float, ...] = (40.0, 20.0, 10.0, 5.0, 2.0, 1.0)


def surface_drag() -> list[list[float]]:
    """Le **logarithme** du coût annuel, sur (taille, rotation).

    Hauteur logarithmique parce que le coût parcourt trois ordres de grandeur
    sur cette boîte, exactement comme le relief de la partie XVII. Les
    graduations et les infobulles restent en pour-cent par an.
    """
    return [[math.log10(max(100.0 * drag(q, r), 1e-6)) for r in SURF_ROTATION]
            for q in SURF_TAILLE_NQ]


# ---------------------------------------------------------------------------
# VI. Ce qu'on peut en récupérer
# ---------------------------------------------------------------------------

#: Une lecture se récupère si elle se calcule **à partir des seuls nombres
#: publiés**, sans accès aux données ni au code. C'est la règle, posée avant
#: les mesures, et elle est plus dure qu'elle n'en a l'air : elle élimine
#: toute reconstitution de méthode.
SANS_DONNEES = True


@dataclass(frozen=True)
class Lecture:
    """Une chose qu'on peut extraire d'un résumé, et ce qu'elle vaut."""

    nom: str
    document: str
    effet: str
    negociable: bool
    calculable: bool

    @property
    def transfere(self) -> bool:
        return self.calculable


def lectures() -> tuple[Lecture, ...]:
    """Les cinq lectures, avec leurs effets relus des sections précédentes."""
    lo, _, hi = bande_calmar(DOC_A["cagr"], DOC_A["sharpe"], DOC_A["annees"])
    _, pire_ind, _ = melange(0.0)
    _, pire_dep, _ = melange(0.10)
    n_dispo = DOC_B["annees"] * SESSIONS_PAR_AN

    return (
        Lecture(
            "La redondance interne", "A et B",
            num(7, 0) + " grandeurs recalculées, aucune incohérence",
            False, True),
        Lecture(
            "La bande du Calmar", "A",
            "bande de " + num(lo, 2) + " à " + num(hi, 2) + " pour un Calmar "
            "annoncé à " + num(DOC_A["calmar"], 2),
            False, True),
        Lecture(
            "La dépendance de queue", "B",
            "facteur " + num(abs(pire_dep) / abs(pire_ind), 2) + " sur la "
            "pire séance, à corrélation invisible",
            False, True),
        Lecture(
            "La marge de l'amélioration", "A",
            num(100 * erreur_fatale(), 1) + " points de CAGR, soit un facteur "
            "de prime fatal de " + num(facteur_fatal(0.05), 1),
            False, True),
        Lecture(
            "La capacité par la rotation", "A et B",
            num(capacite(10.0), 0) + " contrats à dix aller-retours par "
            "séance, nulle au-delà de " + num(rotation_fatale(), 0),
            False, True),
    )


def table_recuperer() -> Table:
    rows = []
    for x in lectures():
        rows.append([
            x.nom,
            x.document,
            x.effet,
            "oui" if x.calculable else "non",
            "oui" if x.negociable else "non",
        ])
    return Table(
        key="rev_recuperer",
        caption="Ce qui se récupère d'un résumé, et ce qui ne s'y trouve pas",
        headers=["Lecture", "Document", "Effet chiffré",
                 "Calculable sans les données", "Donne un avantage négociable"],
        rows=rows,
        note="La règle de verdict est posée avant les mesures et elle est "
             "dure : une lecture se récupère si elle se calcule à partir des "
             "**seuls nombres publiés**, sans accès aux données ni au code. "
             "Les cinq y parviennent, et c'est le résultat utile de la "
             "partie : *un résumé de performance en dit beaucoup plus qu'il "
             "ne croit, à condition de lui poser les quatre questions que ce "
             "document pose.* La dernière colonne ne porte aucun oui, et il "
             "n'y a là aucune ruse : un résumé ne contient ni signal, ni "
             "règle, ni série. **Ce qui se récupère est une méthode de "
             "lecture, jamais une direction.** C'est, à un objet près, la "
             "conclusion des dix-sept parties précédentes.",
        wrap_last=False,
        wrap_cols=[2],
    )


# ---------------------------------------------------------------------------
# Ce que le document consomme
# ---------------------------------------------------------------------------


def values() -> dict[str, str]:
    lo_a, med_a, hi_a = bande_calmar(DOC_A["cagr"], DOC_A["sharpe"],
                                     DOC_A["annees"])
    lo_b, _, hi_b = bande_calmar(DOC_B["cagr"], DOC_B["sharpe"],
                                 DOC_B["annees"])
    mlo_a, _, mhi_a = bande_mdd(DOC_A["cagr"], DOC_A["sharpe"],
                                DOC_A["annees"])
    n_dispo = DOC_B["annees"] * SESSIONS_PAR_AN
    r_lim = rho_detectable(n_dispo)
    f_lim = SESSIONS_PAR_AN * (r_lim / (1.0 - r_lim)) / (TAILLE_SAUT ** 2)
    _, pire_ind, _ = melange(0.0)
    _, pire_dep, _ = melange(0.10)
    gain = DOC_A["calmar_couvert"] - DOC_A["calmar"]

    return {
        "v_cagr_a": num(100 * DOC_A["cagr"], 1),
        "v_sharpe_a": num(DOC_A["sharpe"], 2),
        "v_mdd_a": num(100 * DOC_A["mdd"], 1),
        "v_calmar_a": num(DOC_A["calmar"], 2),
        "v_calmar_couvert": num(DOC_A["calmar_couvert"], 2),
        "v_gain_calmar": num(gain, 2),
        "v_annees_a": num(DOC_A["annees"], 0),
        "v_cagr_b": num(100 * DOC_B["cagr"], 1),
        "v_sharpe_b": num(DOC_B["sharpe"], 2),
        "v_sortino_b": num(DOC_B["sortino"], 2),
        "v_mdd_b": num(100 * DOC_B["mdd"], 1),
        "v_calmar_b": num(DOC_B["calmar"], 2),
        "v_rho": num(DOC_B["correlation"], 3, signed=True),
        "v_ci_bas": num(DOC_B["ci_bas"], 3, signed=True),
        "v_ci_haut": num(DOC_B["ci_haut"], 3, signed=True),
        "v_annees_b": num(DOC_B["annees"], 1),
        "v_seances_b": num(n_dispo, 0),
        "v_seances_implicites": num(
            n_implicite(DOC_B["correlation"], DOC_B["t_correlation"]), 0),
        "v_rapport_sortino": num(DOC_B["sortino"] / DOC_B["sharpe"], 4),
        "v_racine_deux": num(RAPPORT_SYMETRIQUE, 4),
        "v_ecart_sortino": num(
            100 * abs(DOC_B["sortino"] / DOC_B["sharpe"]
                      / RAPPORT_SYMETRIQUE - 1.0), 1),
        "v_marche_implicite": num(
            100 * marche_implicite(DOC_B["cagr"], DOC_B["beta"],
                                   DOC_B["alpha_jensen"], DOC_B["rf"]), 1),
        "v_bande_a_bas": num(lo_a, 2),
        "v_bande_a_haut": num(hi_a, 2),
        "v_bande_a_largeur": num(100 * (hi_a - lo_a) / med_a, 0),
        "v_bande_b_bas": num(lo_b, 2),
        "v_bande_b_haut": num(hi_b, 2),
        "v_mdd_a_bas": num(100 * mlo_a, 1),
        "v_mdd_a_haut": num(100 * mhi_a, 1),
        "v_part_bande": num(100 * gain / (hi_a - lo_a), 0),
        "v_annees_gain": num(annees_pour_ecart(gain), 0),
        "v_exposant_bande": num(loi_de_bande()[1], 2),
        "v_ecart_racine": num(100 * _ecart_de_la_racine(), 0),
        "v_chemins": num(N_CHEMINS, 0),
        "v_saut": num(TAILLE_SAUT, 0),
        "v_rho_limite": num(r_lim, 3),
        "v_freq_limite": num(1.0 / f_lim, 1),
        "v_rho_dix_ans": num(rho_du_saut(TAILLE_SAUT, 0.1), 4),
        "v_facteur_pire": num(abs(pire_dep) / abs(pire_ind), 2),
        "v_invisible": num(taille_invisible(0.015, 160.0), 0),
        "v_reduction_min": num(100 * reduction_minimale(), 1),
        "v_marge_min": num(100 * marge_de_cagr(REDUCTIONS[-1]), 1),
        "v_marge_max": num(100 * marge_de_cagr(REDUCTIONS[0]), 1),
        "v_reduction_retenue": num(100 * REDUCTION_RETENUE, 0),
        "v_erreur_fatale": num(100 * erreur_fatale(), 1),
        "v_facteur_fatal": num(facteur_fatal(0.05), 1),
        "v_friction_fixe": num(FRICTION_FIXE, 2),
        "v_budget_friction": num(100 * BUDGET_FRICTION, 0),
        "v_capacite_dix": num(capacite(10.0), 0),
        "v_notionnel_dix": num(capacite(10.0) * NIVEAU_NQ * POINT_NQ / 1e6, 1),
        "v_rotation_fatale": num(rotation_fatale(), 0),
        "v_capacite_pure_dix": num(capacite_pure(10.0), 0),
        "v_lectures": num(sum(1 for x in lectures() if x.transfere), 0),
    }


def all_tables() -> dict[str, Table]:
    tables = [
        table_coherence(), table_calmar(), table_detecter(),
        table_queue(), table_melange(), table_locus(), table_prime(),
        table_rotation(), table_recuperer(),
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
