"""Les planches de la revue de deux documents extérieurs.

Dix planches, six en deux dimensions et quatre en relief. L'ordre est celui
des quatre questions que la partie pose à un résumé de performance : ses
chiffres se referment-ils, son Calmar sort-il du bruit, sa corrélation voit-
elle ce qui compte, et ce qu'il ne publie pas décide-t-il de tout.

Aucune planche ne montre une stratégie. Toutes montrent une **limite de
mesure** — ce qu'un échantillon, un maximum ou un test de corrélation peuvent
et ne peuvent pas établir. C'est ce qui les rend réutilisables sur n'importe
quelle note de performance.
"""

from __future__ import annotations

import math

from . import revue as V
from .figdisc import W, _plate, _source, _surface
from .figterm import Board, Panel, _num, _signed


def _pct(v: float, nd: int = 0) -> str:
    return _num(100.0 * v, nd) + " %"


PW = (W - 74.0) / 2.0 - 30.0
PX1 = 74.0
PX2 = 74.0 + (W - 74.0) / 2.0


def _ticks(lo: float, hi: float, pas: float) -> list[float]:
    out, v = [], math.ceil(lo / pas) * pas
    while v <= hi + 1e-12:
        out.append(round(v, 10))
        v += pas
    return out


def _echine(zlo: float, zhi: float, mini: int = 3,
            maxi: int = 4) -> list[float]:
    """Les graduations d'une échine, déduites du relief qu'elle gradue.

    Deux fautes symétriques à éviter, et elles se ressemblent moins qu'il n'y
    paraît. Une graduation posée **hors** du domaine est ramenée au sol par la
    projection, où elle se lit comme une valeur du sol : elle ne manque pas,
    elle ment. Et une échine dont la dernière graduation tombe loin sous le
    sommet ne gradue plus la moitié haute du relief. On prend donc, parmi les
    pas ordinaires, celui qui donne le plus de graduations tenables **dans**
    le domaine, en serrant le sommet d'aussi près que possible.

    Le plafond est bas — quatre — et il l'est pour une raison de rendu : la
    première étiquette d'arête se pose à la hauteur du coin gauche du sol,
    juste à côté de l'échine, et une échine dense va la heurter.
    """
    candidats: list[list[float]] = []
    for k in range(-6, 9):
        for m in (1.0, 2.0, 2.5, 5.0):
            pas = m * 10.0 ** k
            if (zhi - zlo) / pas > maxi + 1:
                continue           # sans ce garde, un pas minuscule fabrique
                                   # des millions de graduations avant d'être
                                   # écarté par le compte.
            ticks = _ticks(zlo, zhi, pas)
            if ticks:
                candidats.append(ticks)
    if not candidats:
        return []
    # Le compte visé d'abord ; à défaut, deux graduations valent mieux que
    # rien, une échine nue se lisant comme un axe inachevé.
    vises = [t for t in candidats if mini <= len(t) <= maxi]
    return min(vises or candidats, key=lambda t: (zhi - t[-1], -len(t)))


def _echine_log(zlo: float, zhi: float) -> list[tuple[float, str]]:
    """Les graduations d'une échine dont la hauteur est un logarithme.

    On garde l'échelle 1-3 plutôt que les seules décades : sur deux ordres et
    demi, les décades seules ne laissent que deux graduations et l'échine
    cesse de graduer. Chaque valeur retenue tombe **dans** le domaine du
    relief — une graduation hors domaine est ramenée au sol par la projection
    et s'y lit comme une valeur du sol, ce qui est pire que pas de graduation
    du tout.
    """
    out: list[tuple[float, str]] = []
    for k in range(-6, 9):
        for m in (1.0, 3.0):
            v = m * 10.0 ** k
            u = math.log10(v)
            if zlo <= u <= zhi:
                out.append((u, _num(v, 0 if v >= 1.0 else 1) + " %"))
    return out


def _densite(serie, lo: float, hi: float, seaux: int = 26):
    """Densité empirique sur une grille, pour un histogramme de planche."""
    larg = (hi - lo) / seaux
    compte = [0] * seaux
    for v in serie:
        i = int((v - lo) / larg)
        if 0 <= i < seaux:
            compte[i] += 1
    return [(lo + (i + 0.5) * larg, c / (len(serie) * larg))
            for i, c in enumerate(compte)]


# ---------------------------------------------------------------------------
# I. La redondance interne
# ---------------------------------------------------------------------------


def fig_rev_coherence() -> str:
    """Ce que les chiffres publiés disent les uns des autres.

    Un résumé de performance est **redondant** : le Calmar est le rapport de
    deux autres métriques, le Treynor en est un troisième, la statistique de
    corrélation publie l'effectif. Six recalculs, six accords — le premier
    contrôle d'une note ne demande aucune donnée et il est presque toujours
    omis.

    Le cadre de droite porte le seul recalcul qui apprenne quelque chose : le
    rapport du Sortino au Sharpe tombe exactement sur la valeur d'une loi
    symétrique, ce qui veut dire que le Sortino publié n'ajoute rien.
    """
    b = _plate(430, "Revue · la redondance interne",
               "Ce qu'un résumé dit de lui-même, sans aucune donnée",
               "sept recalculs")

    lignes = [
        ("Calmar A", V.DOC_A["calmar"], V.DOC_A["cagr"] / V.DOC_A["mdd"]),
        ("Calmar B", V.DOC_B["calmar"], V.DOC_B["cagr"] / V.DOC_B["mdd"]),
        ("Treynor B", V.DOC_B["treynor"],
         (V.DOC_B["cagr"] - V.DOC_B["rf"]) / V.DOC_B["beta"]),
        ("Volatilité B", V.DOC_B["cagr"] / V.DOC_B["sharpe"],
         V.vol_implicite(V.DOC_B["cagr"], V.DOC_B["sharpe"])),
        ("Séances B", V.DOC_B["annees"] * V.SESSIONS_PAR_AN,
         V.n_implicite(V.DOC_B["correlation"], V.DOC_B["t_correlation"])),
        ("Sortino sur Sharpe", V.DOC_B["sortino"] / V.DOC_B["sharpe"],
         V.RAPPORT_SYMETRIQUE),
    ]

    p1 = Panel(b, PX1, 92, PW, 214, title="Écart entre annoncé et recalculé",
               readout="en pour-cent")
    n = len(lignes)
    ecarts = [100.0 * (r - a) / abs(a) for _, a, r in lignes]
    borne = max(2.0, 1.4 * max(abs(e) for e in ecarts))
    p1.domain(-borne, borne, -0.5, n - 0.5)
    p1.frame()
    p1.grid_x(_ticks(-borne, borne, 1.0), lambda v: _signed(v, 0))
    p1.vline(0.0, "lvl")
    for i, ((nom, _, _), e) in enumerate(zip(lignes, ecarts)):
        y = n - 1 - i
        p1.hbar(y, 0.0, e, 13.0, "hm5", tip=nom + " : " + _signed(e, 2) + " %")
        p1.label(e, y, _signed(e, 2), dx=6 if e >= 0 else -6, dy=4,
                 anchor="start" if e >= 0 else "end")
        p1.label(-borne, y + 0.34, nom, dx=4, dy=0)

    p2 = Panel(b, PX2, 92, PW, 214, title="Le Sortino n'ajoute rien",
               readout="rapport au Sharpe")
    p2.domain(0.0, 2.0, 1.20, 1.60)
    p2.frame()
    p2.grid_y(_ticks(1.20, 1.60, 0.10), lambda v: _num(v, 2), dx=34.0)
    p2.grid_x([0.5, 1.5], lambda v: ["loi symétrique", "publié"][int(v)])
    p2.hline(V.RAPPORT_SYMETRIQUE, "lvl")
    p2.vbar(0.5, 1.20, V.RAPPORT_SYMETRIQUE, 44.0, "hm3",
            tip="loi symétrique : √2 = " + _num(V.RAPPORT_SYMETRIQUE, 4))
    p2.vbar(1.5, 1.20, V.DOC_B["sortino"] / V.DOC_B["sharpe"], 44.0, "hm7",
            tip="publié : " + _num(V.DOC_B["sortino"] / V.DOC_B["sharpe"], 4))
    p2.label(0.5, V.RAPPORT_SYMETRIQUE, _num(V.RAPPORT_SYMETRIQUE, 4),
             dx=0, dy=-9, anchor="middle")
    p2.label(1.5, V.DOC_B["sortino"] / V.DOC_B["sharpe"],
             _num(V.DOC_B["sortino"] / V.DOC_B["sharpe"], 4),
             dx=0, dy=-9, anchor="middle")

    b.annotation(0.0, 336.0,
                 "les six recalculs se referment à moins de deux pour cent : "
                 "la note est arithmétiquement cohérente")
    b.annotation(0.0, 352.0,
                 "le rapport Sortino sur Sharpe tombe à "
                 + _num(100 * abs(V.DOC_B["sortino"] / V.DOC_B["sharpe"]
                                  / V.RAPPORT_SYMETRIQUE - 1.0), 1)
                 + " % de la valeur d'une loi symétrique")

    _source(b, "Premier contrôle d'une note de performance, et il ne demande "
               "aucune donnée : ses métriques sont redondantes et la "
               "redondance se vérifie. Le cadre de gauche montre que les six "
               "recalculs se referment, ce qui est une bonne nouvelle pour le "
               "document et le point de départ obligé de toute lecture. Le "
               "cadre de droite montre l'exception utile : la déviation à la "
               "baisse d'une loi symétrique vaut sigma sur racine de deux, "
               "donc le Sortino d'une telle loi vaut exactement racine de "
               "deux fois son Sharpe. Le rapport publié y tombe. Le Sortino "
               "ne contient donc aucune information que le Sharpe ne "
               "contienne déjà — ce qui ne l'invalide pas, mais interdit de "
               "le citer comme une mesure de plus.")
    return b.render("Ecart entre metriques annoncees et recalculees, et "
                    "rapport du Sortino au Sharpe contre la valeur symetrique.")


# ---------------------------------------------------------------------------
# II. Le Calmar
# ---------------------------------------------------------------------------


def fig_rev_calmar() -> str:
    """La bande d'échantillonnage d'un Calmar, et ce qu'elle avale.

    À gauche, la loi du Calmar sous une hypothèse **plus favorable** que la
    réalité : rendements indépendants et gaussiens, sans grappe de pertes. Les
    deux valeurs que le document oppose y sont posées, et elles tiennent dans
    la même bosse.

    À droite, la vitesse à laquelle cette bande se referme. Son exposant est
    ajusté sur les horizons simulés et vaut plus que la racine attendue — mais
    la bande part de si haut que l'écart revendiqué demanderait des décennies.
    """
    _, cals = V.tirages(V.DOC_A["cagr"], V.DOC_A["sharpe"], V.DOC_A["annees"])
    lo, med, hi = V.bande_calmar(V.DOC_A["cagr"], V.DOC_A["sharpe"],
                                 V.DOC_A["annees"])
    gain = V.DOC_A["calmar_couvert"] - V.DOC_A["calmar"]

    b = _plate(446, "Revue · la bande du Calmar",
               "Un rapport dont le dénominateur est un maximum",
               _num(V.N_CHEMINS, 0) + " histoires simulées")

    p1 = Panel(b, PX1, 92, PW, 214, title="Loi du Calmar sous la loi nulle",
               readout="densité")
    haut_x = 2.0
    dens = _densite([c for c in cals if c <= haut_x], 0.0, haut_x, 26)
    p1.domain(0.0, haut_x, 0.0, max(d for _, d in dens) * 1.25)
    p1.frame()
    p1.grid_y([], lambda v: "")
    p1.grid_x(_ticks(0.0, haut_x, 0.5), lambda v: _num(v, 1))
    # Le lavis d'abord : c'est un rectangle plein, et il recouvrirait les
    # barres s'il était peint après elles.
    p1.band_x(lo, hi)
    for x, d in dens:
        p1.vbar(x, 0.0, d, 9.0, "hm3",
                tip="Calmar " + _num(x, 2) + " : densité " + _num(d, 2))
    haut_y = max(d for _, d in dens) * 1.25
    for val, nom, cls in ((V.DOC_A["calmar"], "nu", "hm7"),
                          (V.DOC_A["calmar_couvert"], "couvert", "hm6")):
        p1.vline(val, "lvl")
        p1.dot(val, haut_y * 0.86, cls,
               nom + " : " + _num(val, 2), r=4.4)
        p1.label(val, haut_y * 0.86, nom, dx=7, dy=4)
    p1.label(1.96, haut_y * 0.55, "bande à 90 %", dx=0, dy=0,
             anchor="end")

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce que l'horizon resserre",
               readout="demi-largeur de la bande")
    pts = V.largeur_par_horizon()
    # Le domaine se déduit des horizons simulés : porté à deux cents ans, il
    # laissait deux cinquièmes du cadre vides à droite de la dernière mesure.
    p2.domain(4.0, 1.35 * V.HORIZONS[-1], 0.10, 1.6, xlog=True, ylog=True)
    p2.frame()
    p2.grid_y([0.2, 0.4, 0.8, 1.6], lambda v: _num(v, 1), dx=32.0)
    p2.grid_x([5, 10, 20, 40, 80], lambda v: _num(v, 0),
              label="années observées")
    p2.path([(t, w) for t, w in pts], "hm6", tip="demi-largeur de la bande")
    for t, w in pts:
        p2.dot(t, w, "hm6", _num(t, 0) + " ans : " + _num(w, 3), r=3.4)
    p2.hline(gain, "lvl")
    p2.dot(V.annees_pour_ecart(gain), gain, "hm7",
           "l'écart revendiqué sort du bruit à "
           + _num(V.annees_pour_ecart(gain), 0) + " ans", r=4.4)
    p2.label(4.6, gain, "l'écart revendiqué, " + _num(gain, 2), dx=0, dy=-8)

    b.annotation(0.0, 336.0,
                 "la bande mesure " + _num(100 * (hi - lo) / med, 0)
                 + " % de sa médiane ; l'écart revendiqué en occupe "
                 + _num(100 * gain / (hi - lo), 0) + " %")
    b.annotation(0.0, 352.0,
                 "il faudrait " + _num(V.annees_pour_ecart(gain), 0)
                 + " ans pour qu'il sorte du bruit, et le document en a "
                 + _num(V.DOC_A["annees"], 0))
    b.annotation(0.0, 368.0,
                 "la loi nulle employée ici est plus favorable que la "
                 "réalité : elle ignore les grappes de pertes")

    _source(b, "Rendements quotidiens indépendants et gaussiens, de même "
               "rendement composé et de même Sharpe que la stratégie "
               "annoncée. C'est la loi la plus douce qui soit — une vraie "
               "série de pertes se groupe, ce qui aggrave le maximum — donc "
               "la bande tracée est une borne inférieure de l'incertitude "
               "réelle. Le maximum de perte annoncé par le document, "
            + _pct(V.DOC_A["mdd"], 1) + ", tombe d'ailleurs au-delà du "
              "quatre-vingt-quinzième centile de cette loi nulle, ce qui est "
              "la signature attendue d'une stratégie qui perd en grappes. Le "
              "document conclut de son côté par un bootstrap apparié dont le "
              "premier quartile est nul : les deux routes disent la même "
              "chose.")
    return b.render("Loi du Calmar sous une hypothese independante, et "
                    "vitesse a laquelle sa bande se referme.")


def fig_rev_bande() -> str:
    """Le coin où un Calmar devient une mesure.

    Deux axes resserrent la bande, et pas à la même vitesse. L'horizon la
    resserre comme une puissance ajustée sur la mesure. Le Sharpe la resserre
    bien plus vite, parce qu'il rend le maximum de perte lui-même moins
    variable. Le relief dit donc qu'un Calmar n'est une mesure qu'au coin des
    Sharpe élevés et des longues archives, et que la région où on le cite le
    plus est celle où il ne mesure rien.

    Les graduations de l'échine se déduisent du relief, jamais d'une liste
    écrite à la main : une échine plafonnée à deux cents pour cent sous un
    sommet à cinq cent cinquante ne gradue plus rien.
    """
    z = V.surface_bande()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Revue · le relief de la bande",
               "Quand un Calmar cesse d'être une anecdote",
               "hauteur : largeur de bande en % de la médiane")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(s, 1) for s in V.SURF_SHARPE],
             col_labels=[_num(t, 0) for t in V.SURF_ANNEES],
             z_ticks=[(t, _num(t, 0) + " %")
                      for t in _echine(zlo, zhi)],
             tip="{v:.0f} % de la médiane", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : Sharpe · arête droite : années observées · "
                 "hauteur : largeur de la bande à 90 %")
    b.annotation(0.0, 424.0,
                 "le coin du fond est celui des Sharpe faibles et des "
                 "archives courtes, et c'est là que le Calmar se cite le plus")
    b.annotation(0.0, 440.0,
                 "le versant s'effondre sur le Sharpe bien plus vite que sur "
                 "l'horizon")

    _source(b, "Largeur de la bande à quatre-vingt-dix pour cent, rapportée à "
               "sa médiane, sous rendements indépendants. Les deux axes ne "
               "coûtent pas la même chose et c'est le fait de la planche : "
               "quadrupler l'horizon divise la bande par "
               + _num(4.0 ** V.loi_de_bande()[1], 1) + ", quand doubler le "
               "Sharpe la divise bien davantage. La raison tient en une "
               "phrase — un Sharpe élevé rend le maximum de perte lui-même "
               "moins variable, alors qu'un horizon long ne fait que "
               "moyenner davantage un maximum qui reste unique. Il n'y a "
               "qu'un seul maximum dans une série, quelle que soit sa "
               "longueur, et c'est toute la difficulté du Calmar.")
    return b.render("Surface de la largeur de bande du Calmar sur le plan du "
                    "Sharpe et du nombre d annees observees.")


# ---------------------------------------------------------------------------
# III. La corrélation
# ---------------------------------------------------------------------------


def fig_rev_queue() -> str:
    """Ce que la corrélation de Pearson ne peut pas voir.

    À gauche, la corrélation qu'un krach partagé induit, contre sa fréquence.
    La courbe passe sous la limite de détection bien avant que le krach ne
    devienne négligeable : entre les deux, la dépendance existe et le test la
    déclare absente.

    À droite, ce que cette dépendance invisible fait à la pire séance d'un
    mélange. Le maximum de perte n'en souffre que modérément ; la pire séance,
    elle, triple.
    """
    n_dispo = V.DOC_B["annees"] * V.SESSIONS_PAR_AN
    limite = V.rho_detectable(n_dispo)

    b = _plate(462, "Revue · la dépendance que Pearson ne voit pas",
               "Un krach partagé, et ce qu'un test de corrélation en dit",
               _num(n_dispo, 0) + " séances disponibles")

    p1 = Panel(b, PX1, 92, PW, 214, title="Corrélation induite par un krach",
               readout="krach de " + _num(V.TAILLE_SAUT, 0) + " écarts-types")
    p1.domain(0.01, 1.2, 0.001, 0.4, xlog=True, ylog=True)
    p1.frame()
    p1.grid_y([0.002, 0.01, 0.05, 0.2], lambda v: _num(v, 3), dx=44.0)
    p1.grid_x([0.02, 0.05, 0.2, 1.0],
              lambda v: "1 / " + _num(1.0 / v, 0), label="krachs par an")
    limite_bas = 0.001
    p1.band_y(limite_bas, limite)
    pts = [(f, V.rho_du_saut(V.TAILLE_SAUT, f))
           for f in [0.01 * (1.14 ** i) for i in range(40)] if f <= 1.2]
    p1.path(pts, "hm6", tip="corrélation induite")
    p1.hline(limite, "lvl")
    f_lim = (V.SESSIONS_PAR_AN * (limite / (1.0 - limite))
             / (V.TAILLE_SAUT ** 2))
    p1.dot(f_lim, limite, "hm7",
           "limite de visibilité : un krach tous les "
           + _num(1.0 / f_lim, 1) + " ans", r=4.4)
    p1.label(0.011, limite, "limite de détection", dx=0, dy=-8)
    p1.label(f_lim, limite, "un tous les " + _num(1.0 / f_lim, 1) + " ans",
             dx=8, dy=20)

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce que la queue coûte au mélange",
               readout="pire séance, en σ du mélange")
    n = len(V.MODELES)
    pires = [abs(V.melange(f)[1]) for _, f in V.MODELES]
    p2.domain(0.0, max(pires) * 1.25, -0.5, n - 0.5)
    p2.frame()
    p2.grid_x(_ticks(0.0, max(pires) * 1.25, 4.0), lambda v: _num(v, 0))
    for i, ((nom, f), pire) in enumerate(zip(V.MODELES, pires)):
        y = n - 1 - i
        p2.hbar(y, 0.0, pire, 15.0, "hm3" if f == 0.0 else "hm6",
                tip=nom + " : " + _num(pire, 1) + " écarts-types")
        p2.label(pire, y, _num(pire, 1), dx=6, dy=4)
        court = "indépendance" if f == 0.0 else ("un tous les "
                                                 + _num(1.0 / f, 0) + " ans")
        p2.label(0.0, y + 0.30, court, dx=4, dy=0)

    b.annotation(0.0, 352.0,
                 "sous la bande grisée, la dépendance existe et le test la "
                 "déclare absente")
    b.annotation(0.0, 368.0,
                 "l'intervalle publié, de " + _num(V.DOC_B["ci_bas"], 3)
                 + " à " + _num(V.DOC_B["ci_haut"], 3) + ", est compatible "
                 "avec un krach partagé une fois par décennie")
    b.annotation(0.0, 384.0,
                 "et ce krach-là multiplie la pire séance du mélange par "
                 + _num(pires[2] / pires[0], 1))

    _source(b, "La corrélation de Pearson est une moyenne sur toutes les "
               "séances, et les séances ordinaires diluent un événement rare "
               "jusqu'à le rendre invisible. Le cadre de droite mesure ce que "
               "cette invisibilité coûte, sur deux jambes déduites des "
               "chiffres publiés et mélangées aux poids déclarés. Deux "
               "lectures : le maximum de perte ne bouge que de quelques "
               "points, ce qui est honnête à dire ; la pire séance, elle, "
               "est multipliée, parce que ce jour-là les deux jambes perdent "
               "ensemble et que le mélange n'amortit rien. La "
               "diversification protège toutes les séances sauf celle qui "
               "compte.")
    return b.render("Correlation induite par un krach partage contre sa "
                    "frequence, et pire seance du melange par modele.")


def fig_rev_invisible() -> str:
    """Le krach que l'archive ne peut pas exclure.

    Le relief ne montre pas un phénomène : il montre une **limite de mesure**.
    Pour chaque fréquence et chaque longueur d'archive, il donne la taille du
    choc partagé qu'un test de corrélation ne détecterait pas. C'est le nombre
    qui manque à toute note concluant à l'indépendance — non pas « la
    corrélation est nulle », mais « voici ce que mes données n'auraient pas
    vu ».
    """
    z = V.surface_invisible()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Revue · le krach invisible",
               "Ce qu'une archive ne peut pas exclure",
               "hauteur : taille du choc, en écarts-types")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=["1 / " + _num(1.0 / f, 0) for f in V.SURF_FREQ],
             col_labels=[_num(t, 0) for t in V.SURF_ARCHIVE],
             z_ticks=[(t, _num(t, 0) + " σ")
                      for t in _echine(zlo, zhi)],
             tip="{v:.1f} écarts-types", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : fréquence du krach partagé · arête droite : "
                 "années d'archive")
    b.annotation(0.0, 424.0,
                 "même avec " + _num(V.SURF_ARCHIVE[-1], 0) + " ans de "
                 "données, un choc de " + _num(z[0][-1], 0) + " écarts-types "
                 "tous les " + _num(1.0 / V.SURF_FREQ[0], 0)
                 + " ans reste indétectable")
    b.annotation(0.0, 440.0,
                 "les deux axes vont dans le même sens : un événement rare et "
                 "une archive courte laissent passer les mêmes chocs")

    _source(b, "On inverse le test : la corrélation détectable sur un "
               "échantillon donné fixe une variance de saut, donc une taille. "
               "Le relief est celui d'une limite de mesure et non d'un "
               "marché — il dit ce qu'un échantillon ne peut pas exclure, ce "
               "qui est la seule chose qu'un test d'indépendance non "
               "significatif établisse. Une note qui conclut à "
               "l'indépendance à partir d'une corrélation non significative "
               "devrait publier ce nombre à côté du sien ; aucune ne le fait, "
               "et il ne coûte pourtant qu'une ligne.")
    return b.render("Surface de la taille du krach partage indetectable, sur "
                    "le plan de la frequence et de la longueur d archive.")


# ---------------------------------------------------------------------------
# IV. Le portage
# ---------------------------------------------------------------------------


def fig_rev_locus() -> str:
    """Ce que l'amélioration revendiquée exige, et ce qu'elle vaut.

    Deux Calmar publiés et rien d'autre suffisent à contraindre le couple
    (réduction du maximum, coût net) à une droite. Le cadre de gauche la
    trace : au-dessous d'un seuil calculable, le recouvrement doit *ajouter*
    du rendement, pas seulement en coûter peu.

    Le cadre de droite donne la seule quantité opposable : ce que
    l'amélioration vaut en points de rendement annuel, et donc l'erreur de
    prime qui l'efface.
    """
    b = _plate(494, "Revue · ce que l'amélioration exige",
               "Deux Calmar publiés contraignent tout le reste",
               "de " + _num(V.DOC_A["calmar"], 2) + " à "
               + _num(V.DOC_A["calmar_couvert"], 2))

    ds = [0.05 + 0.005 * i for i in range(76)]

    p1 = Panel(b, PX1, 92, PW, 214, title="Coût net admissible",
               readout="points de CAGR")
    ys = [100.0 * V.cout_admissible(d) for d in ds]
    p1.domain(5.0, 42.0, min(ys) * 1.15, max(ys) * 1.15)
    p1.frame()
    p1.grid_y(_ticks(min(ys) * 1.15, max(ys) * 1.15, 5.0),
              lambda v: _signed(v, 0), dx=34.0)
    p1.grid_x([10, 20, 30, 40], lambda v: _num(v, 0),
              label="réduction du MDD, en points")
    p1.hline(0.0, "lvl")
    p1.path([(100 * d, 100 * V.cout_admissible(d)) for d in ds], "hm6",
            tip="coût net admissible")
    d_min = V.reduction_minimale()
    p1.dot(100 * d_min, 0.0, "hm7",
           "au-dessous de " + _num(100 * d_min, 1) + " points, le "
           "recouvrement doit ajouter du rendement", r=4.4)
    p1.label(100 * d_min, 0.0, _num(100 * d_min, 1) + " points", dx=8, dy=-8)
    # La phrase qui nommait la région au-dessous de zéro se posait au milieu
    # du tracé, qui la barrait — un défaut qu'aucun balayage ne voit, puisque
    # `rect.mjs` ne croise jamais un texte avec un `path`. Elle est descendue
    # dans la légende, sous la planche, où la donnée n'est pas.

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce que l'amélioration vaut",
               readout="points de CAGR")
    p2.domain(5.0, 42.0, 0.0, 14.0)
    p2.frame()
    p2.grid_y(_ticks(0.0, 14.0, 4.0), lambda v: _num(v, 0), dx=26.0)
    p2.grid_x([10, 20, 30, 40], lambda v: _num(v, 0),
              label="réduction du MDD, en points")
    p2.path([(100 * d, 100 * V.marge_de_cagr(d)) for d in ds], "hm7",
            tip="marge de l'amélioration")
    p2.dot(100 * V.REDUCTION_RETENUE, 100 * V.erreur_fatale(), "hm7",
           "à la réduction retenue : " + _num(100 * V.erreur_fatale(), 1)
           + " points", r=4.4)
    p2.label(100 * V.REDUCTION_RETENUE, 100 * V.erreur_fatale(),
             _num(100 * V.erreur_fatale(), 1) + " points", dx=8, dy=-6)

    b.annotation(0.0, 352.0,
                 "le document publie deux Calmar, et ni la réduction du "
                 "maximum ni le budget de prime")
    b.annotation(0.0, 368.0,
                 "les deux premiers contraignent pourtant les deux seconds")
    b.annotation(0.0, 384.0,
                 "au-dessous de " + _num(100 * d_min, 1) + " points de "
                 "réduction, le coût admissible devient négatif")
    b.annotation(0.0, 400.0,
                 "toute sous-estimation de prime supérieure à la courbe de "
                 "droite efface l'amélioration entière")

    _source(b, "Le Calmar couvert vaut le rendement moins le coût, divisé par "
               "le maximum moins sa réduction. Deux Calmar publiés laissent "
               "donc un lieu d'une dimension, que les deux cadres parcourent "
               "sous deux angles. Celui de gauche donne la contrainte "
               "qualitative : au-dessous de " + _num(100 * d_min, 1)
            + " points de réduction, il ne suffit pas que le recouvrement "
              "coûte peu, il doit rapporter — ce que le document revendique "
              "d'ailleurs par un effet de taxe de volatilité. Celui de droite "
              "donne la contrainte quantitative, et c'est la seule opposable "
              "sans données.")
    return b.render("Cout net admissible et marge de l amelioration, selon la "
                    "reduction du maximum de perte.")


def fig_rev_portage() -> str:
    """Le Calmar couvert, quand la prime vraie dépasse la prime modélisée.

    Le sol est posé au Calmar nu : ce qui dépasse est une amélioration, ce qui
    s'enfonce est une dégradation. La ligne de niveau traverse la boîte en
    diagonale, et c'est le fait de la planche — **c'est le produit du budget
    par le facteur qui décide**, jamais l'un des deux seul.
    """
    z = V.surface_portage()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Revue · ce qu'une prime sous-estimée coûte",
               "Le Calmar couvert, budget contre facteur de prime",
               "sol posé au Calmar nu")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_pct(x, 1) for x in V.SURF_BUDGET],
             col_labels=[_num(f, 1) for f in V.SURF_FACTEUR],
             # Trois graduations et pas six : la première étiquette d'arête
             # se pose à la même hauteur que le coin gauche du sol, et une
             # échine dense va la heurter.
             z_ticks=[(t, _num(t, 1)) for t in _echine(zlo, zhi, 3, 3)],
             tip="{v:+.3f} de Calmar", zero=V.DOC_A["calmar"])

    b.annotation(0.0, 408.0,
                 "arête gauche : budget de prime annuel · arête droite : "
                 "rapport entre prime réelle et prime modélisée")
    b.annotation(0.0, 424.0,
                 "le sol est posé au Calmar nu, " + _num(V.DOC_A["calmar"], 2)
                 + " : sous le sol, le recouvrement dégrade")
    b.annotation(0.0, 440.0,
                 "à un budget de " + _pct(0.05, 0) + ", le facteur fatal vaut "
                 + _num(V.facteur_fatal(0.05), 1))

    _source(b, "Le document valorise ses options sur le comptant, sous une "
               "calibration physique, sans structure par terme — il le dit "
               "lui-même — et omet donc la prime de risque de variance. Le "
               "relief ne prétend pas savoir de combien : il donne la forme "
               "de la dépendance. Un gros budget de prime laisse moins de "
               "place à l'erreur, pas plus, ce qui est l'inverse de "
               "l'intuition courante, et la ligne de niveau zéro traverse la "
               "boîte en diagonale parce que seul le produit compte. Aucune "
               "de ces deux quantités n'est publiée.")
    return b.render("Surface du Calmar couvert sur le plan du budget de prime "
                    "et du facteur de sous-estimation.")


# ---------------------------------------------------------------------------
# V. La rotation
# ---------------------------------------------------------------------------


def fig_rev_rotation() -> str:
    """La capacité d'une stratégie intraday, et la loi qui la gouverne.

    L'impact croît en racine de la taille ; pour un budget de coût fixé, la
    taille admissible varie donc comme l'inverse du **carré** de la rotation.
    La droite de pente moins deux est cette loi, tracée sans ajustement.

    La friction fixe l'aggrave, et d'une façon que la loi ne dit pas : elle
    ne dépend pas de la taille. Au-delà d'une rotation calculable, aucune
    taille ne convient.
    """
    b = _plate(446, "Revue · la capacité par la rotation",
               "L'impact croît en racine, la capacité tombe en carré",
               "budget " + _pct(V.BUDGET_FRICTION, 0) + " du notionnel")

    rots = [0.5 * (1.14 ** i) for i in range(40)]
    rots = [r for r in rots if r <= 60.0]

    p1 = Panel(b, PX1, 92, PW, 214, title="Capacité contre rotation",
               readout="contrats")
    p1.domain(0.5, 60.0, 0.02, 2e4, xlog=True, ylog=True)
    p1.frame()
    # Les décades se déduisent du domaine : une liste écrite à la main y
    # perdait la graduation de cent, et un axe logarithmique auquel il manque
    # une décade se lit comme un axe dont l'échelle change en cours de route.
    p1.grid_y([10.0 ** k for k in range(-1, 5)],
              lambda v: _num(v, 1 if v < 1.0 else 0), dx=44.0)
    p1.grid_x([1, 2, 5, 10, 20, 40], lambda v: _num(v, 0),
              label="aller-retours par séance")
    p1.path([(r, V.capacite_pure(r)) for r in rots], "hm3", dash="5 3",
            tip="capacité sans friction fixe, pente moins deux")
    p1.path([(r, V.capacite(r)) for r in rots if V.capacite(r) > 0.02],
            "hm7", tip="capacité réelle")
    rf = V.rotation_fatale()
    p1.vline(rf, "lvl")
    p1.label(rf, 3e3, "aucune taille au-delà", dx=-7, dy=0, anchor="end")
    p1.dot(10.0, V.capacite(10.0), "hm7",
           "dix aller-retours : " + _num(V.capacite(10.0), 0) + " contrats",
           r=4.4)

    p2 = Panel(b, PX2, 92, PW, 214, title="Ce que la friction fixe consomme",
               readout="% du notionnel par an")
    p2.domain(0.5, 60.0, 0.0, 30.0, xlog=True)
    p2.frame()
    p2.grid_y(_ticks(0.0, 30.0, 10.0), lambda v: _num(v, 0), dx=30.0)
    p2.grid_x([1, 2, 5, 10, 20, 40], lambda v: _num(v, 0),
              label="aller-retours par séance")
    p2.path([(r, 100 * V.SESSIONS_PAR_AN * r * V.FRICTION_FIXE / V.NIVEAU_NQ)
             for r in rots], "hm6", tip="friction fixe seule")
    p2.hline(100 * V.BUDGET_FRICTION, "lvl")
    p2.label(0.55, 100 * V.BUDGET_FRICTION, "budget de friction", dx=0, dy=-8)
    p2.dot(rf, 100 * V.BUDGET_FRICTION, "hm7",
           "la friction fixe seule épuise le budget à " + _num(rf, 0)
           + " aller-retours", r=4.4)

    b.legend(PX1, 352.0,
             [("hm7", "capacité réelle"),
              ("hm3", "sans friction fixe, pente −2", "5 3")],
             step=170.0, kind="line")
    b.annotation(0.0, 374.0,
                 "doubler le nombre d'aller-retours divise la capacité par "
                 "quatre : c'est la racine de l'impact, lue à l'envers")
    b.annotation(0.0, 390.0,
                 "à dix aller-retours par séance, la capacité vaut "
                 + _num(V.capacite(10.0), 0) + " contrats, soit "
                 + _num(V.capacite(10.0) * V.NIVEAU_NQ * V.POINT_NQ / 1e6, 1)
                 + " millions de dollars de notionnel")

    _source(b, "Loi en racine de la taille, coefficient déclaré, sur un "
               "contrat d'indice dont le niveau, le volume et la volatilité "
               "sont posés. La droite tiretée est la loi pure et sa pente "
               "vaut exactement moins deux ; la courbe pleine y ajoute la "
               "fourchette et la commission, qui ne dépendent pas de la "
               "taille et finissent par tout décider. Le point où elle "
               "s'effondre est celui où le coût ne vient plus de ce qu'on "
               "trade mais du nombre de fois qu'on le trade. Aucun des deux "
               "documents ne publie sa rotation, et c'est pourtant le seul "
               "nombre dont dépend la capacité de ce qu'ils décrivent.")
    return b.render("Capacite d une strategie intraday contre sa rotation, et "
                    "part de la friction fixe dans le budget.")


def fig_rev_drag() -> str:
    """Le coût annuel sur tout le plan de la taille et de la rotation.

    Deux versants pour deux causes, et c'est ce qui rend le relief utile.
    Vers les grandes tailles, le coût monte parce que l'impact croît. Vers les
    rotations rapides, il monte parce qu'on paie la fourchette plus souvent —
    et ce second versant ne se corrige pas en réduisant la taille.
    """
    z = V.surface_drag()
    vals = [v for ligne in z for v in ligne]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Revue · le relief du coût",
               "Ce qu'une stratégie paie, taille contre rotation",
               "hauteur : % du notionnel par an")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(q, 0) for q in V.SURF_TAILLE_NQ],
             col_labels=[_num(r, 0) for r in V.SURF_ROTATION],
             z_ticks=_echine_log(zlo, zhi),
             tip="{v:.1f} % par an", zero=zlo,
             tip_value=lambda v: 10.0 ** v)

    b.annotation(0.0, 408.0,
                 "arête gauche : taille en contrats · arête droite : "
                 "aller-retours par séance · hauteur logarithmique")
    # « Presque tout le relief est au-dessus » qualifiait au lieu de mesurer,
    # et la mesure dit la moitié. Un écart se publie chiffré.
    seuil = 100.0 * V.BUDGET_FRICTION
    au_dessus = sum(1 for ligne in z for v in ligne if 10.0 ** v > seuil)
    b.annotation(0.0, 424.0,
                 "le budget déclaré est " + _pct(V.BUDGET_FRICTION, 0)
                 + " par an, et "
                 + _num(100.0 * au_dessus / (len(z) * len(z[0])), 0)
                 + " % des mailles du relief passent au-dessus")
    b.annotation(0.0, 440.0,
                 "le versant de la rotation ne se corrige pas en réduisant la "
                 "taille — c'est la stratégie elle-même")

    _source(b, "Hauteur logarithmique, parce que le coût parcourt trois "
               "ordres de grandeur sur cette boîte ; les graduations et les "
               "infobulles restent en pour-cent du notionnel par an. Ce que "
               "le relief ajoute aux tables est la nature des deux versants. "
               "Celui de la taille se corrige en tradant moins gros, et un "
               "opérateur seul y est structurellement à l'abri. Celui de la "
               "rotation ne se corrige pas : réduire la taille n'y change "
               "rien, puisque la fourchette se paie au même prix sur un "
               "contrat que sur mille. Une stratégie intraday paie donc un "
               "coût qu'elle ne peut pas fuir, et il croît avec ce qui la "
               "définit.")
    return b.render("Surface du cout annuel sur le plan de la taille de "
                    "position et de la rotation.")


# ---------------------------------------------------------------------------
# VI. Le décompte
# ---------------------------------------------------------------------------


def fig_rev_recuperer() -> str:
    """Ce qui se récupère d'un résumé, et ce qui ne s'y trouve pas.

    Cinq lectures, toutes calculables à partir des seuls nombres publiés,
    aucune ne donnant un avantage négociable. La planche n'a pas d'axe
    quantitatif parce qu'il n'y a rien à comparer : elle range des questions,
    et la dernière colonne est la réponse à celle que tout le monde pose.
    """
    xs = V.lectures()
    b = _plate(416, "Revue · le décompte",
               "Cinq lectures, et ce qu'aucune ne donne",
               "règle : calculable sans les données")

    p = Panel(b, 214.0, 92, W - 254.0, 176,
              title="Ce que chaque lecture rend", readout="")
    n = len(xs)
    p.domain(0.0, 1.0, -0.5, n - 0.5)
    p.frame()
    for i, x in enumerate(xs):
        y = n - 1 - i
        p.hbar(y, 0.0, 1.0, 20.0, "hm5" if x.transfere else "hm1",
               tip=x.nom + " : " + x.effet)
        p.label(0.012, y, x.effet, dx=0, dy=4)
        b.add('<text class="lg" x="206" y="%.1f" text-anchor="end">%s</text>'
              % (p.sy(y) - 2.0, x.nom))
        b.add('<text class="tk" x="206" y="%.1f" text-anchor="end">%s</text>'
              % (p.sy(y) + 11.0, "document " + x.document))

    b.legend(74.0, 300.0,
             [("hm5", "calculable sans les données"),
              ("hm1", "exige les données")],
             step=280.0)
    b.annotation(0.0, 324.0,
                 "les cinq lectures se calculent sur les seuls nombres "
                 "publiés ; aucune ne donne un avantage négociable")
    b.annotation(0.0, 340.0,
                 "un résumé ne contient ni signal, ni règle, ni série")

    _source(b, "La règle de verdict est posée avant les mesures et elle est "
               "dure : une lecture se récupère si elle se calcule à partir "
               "des seuls nombres publiés, sans accès aux données ni au code. "
               "Les cinq y parviennent, et c'est le résultat utile de la "
               "partie — un résumé de performance en dit beaucoup plus qu'il "
               "ne croit. Mais aucune ne donne un avantage négociable, et il "
               "n'y a là aucune ruse : ce qui se récupère est une méthode de "
               "lecture, jamais une direction. C'est, à un objet près, la "
               "conclusion des dix-sept parties précédentes.")
    return b.render("Les cinq lectures recuperables d un resume et ce "
                    "qu aucune ne donne.")


FIGURES = {
    "revcoherence": fig_rev_coherence,
    "revcalmar": fig_rev_calmar,
    "revbande": fig_rev_bande,
    "revqueue": fig_rev_queue,
    "revinvisible": fig_rev_invisible,
    "revlocus": fig_rev_locus,
    "revportage": fig_rev_portage,
    "revrotation": fig_rev_rotation,
    "revdrag": fig_rev_drag,
    "revrecuperer": fig_rev_recuperer,
}


def render_all() -> dict[str, str]:
    return {k: f() for k, f in FIGURES.items()}
