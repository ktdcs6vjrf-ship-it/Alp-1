"""Planches du risque réel : friction, spread, forçage, capital.

Même contrat que `alp1.figterm`, dont ce module reprend la planche et les
panneaux : aucune couleur écrite en dur, tout passe par les jetons du
document, et chaque point tracé sort d'une fonction du noyau. La mise en page
est celle d'un terminal — plusieurs cadres sur une planche, un intitulé et une
lecture chiffrée en tête de chacun, les étiquettes posées sur les traits.

Les six planches répondent à six questions, dans l'ordre où un opérateur les
rencontre. Combien la friction prend-elle de mon risque ? Combien le spread en
prend-il avant que le prix ne bouge ? Que coûte une répétition d'entrées ?
Que devient le capital sur une série ? Quel avantage faudrait-il posséder ?
Et que ma propre série d'échecs révèle-t-elle de la géométrie que je pratique
réellement ?
"""

from __future__ import annotations

import math

from . import forcing as F
from .costs import COST_BASE, COST_OPTIMISTIC, COST_REALISTIC, ES, MES, MNQ, NQ, stop_points
from .figterm import Board, Panel, _Noise, _num, _signed
from .horizon import outcome_scaled
from .report import HURST, INDEX_LEVEL, SESSION_MIN, SIGMA_1MIN, STOP_PCT, STOP_PCT_BOX

#: Grille de largeurs de stop, en pourcentage de l'indice. Elle court du stop
#: le plus serré que l'opérateur déclare à celui que le document retenait
#: auparavant, pour que l'écart se voie plutôt que se raconte.
STOP_GRID = (0.0025, 0.005, 0.010, 0.020, 0.050, 0.100, 0.200)

#: Niveau d'indice par contrat. Les deux complexes ne cotent pas au même
#: niveau, et un pourcentage ne veut rien dire sans lui.
LEVELS = {"ES": 6000.0, "MES": 6000.0, "NQ": 22000.0, "MNQ": 22000.0}

#: Spread complet supposé, en ticks. Un tick sur les quatre contrats aux
#: heures liquides ; c'est la valeur du modèle de coût du dépôt.
SPREAD_TICKS = 1.0

RR_REF = 20.0


def _cl(pct: float) -> float:
    """`c/L` au scénario de référence, pour un stop en pourcentage."""
    return COST_BASE.friction_points(ES) / stop_points(INDEX_LEVEL, pct)


def _exposure(pct: float) -> float:
    L = stop_points(INDEX_LEVEL, pct)
    return outcome_scaled(L, RR_REF * L, SESSION_MIN, SIGMA_1MIN, HURST).expected_time


# ---------------------------------------------------------------------------
# 1. Le mur de friction
# ---------------------------------------------------------------------------

def fig_friction_wall() -> str:
    """Ce que la friction prend du risque, selon la largeur du stop.

    Le panneau du haut porte `c/L` sur une échelle logarithmique de stops ;
    la ligne d'unité est le mur — au-dessus, l'aller-retour coûte plus que le
    risque nominal, et aucun signal ne rattrape cela. Le panneau du bas
    compare, contrat par contrat, la largeur du stop et celle de la friction,
    toutes deux en ticks : c'est la seule unité dans laquelle un stop se juge.
    """
    b = Board(640, 470)

    p1 = Panel(b, 62, 44, 496, 178,
               title="Friction rapportée au risque nominal",
               readout="c/L, scénario de référence")
    p1.domain(0.0020, 0.25, 0.02, 4.0, xlog=True, ylog=True)
    p1.band_x(STOP_PCT_BOX[0], STOP_PCT_BOX[1])
    p1.frame()
    p1.grid_y([0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0],
              lambda v: _num(v, 2), "c / L")
    p1.grid_x([0.0025, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2],
              lambda v: _num(v, 3), "largeur du stop, en % de l'indice")

    for cost, cls, nom in ((COST_OPTIMISTIC, "s3", "optimiste"),
                           (COST_BASE, "s1", "référence"),
                           (COST_REALISTIC, "s2", "réaliste")):
        pts = [(x, cost.friction_points(ES) / stop_points(INDEX_LEVEL, x))
               for x in [0.0020 * (1.0233 ** i) for i in range(210)]]
        p1.path(pts, cls, tip=f"friction {nom}")

    p1.hline(1.0, "lvl strong")
    # Sous la ligne d'unité, non au-dessus : au-dessus, l'étiquette venait se
    # poser sur celle du premier point, qui annonce précisément un c/L de
    # 1,100 et se place elle aussi juste au-dessus de la ligne.
    p1.label(0.0022, 0.72, "mur : la friction égale le risque", cls="dl halo")
    for x in STOP_PCT_BOX:
        v = _cl(x)
        p1.dot(x, v, "s1", tip=f"stop {_num(x, 3)} % — c/L = {_num(v, 3)}")
        p1.label(x, v, f"{_num(x, 3)} % → {_num(v, 3)}", dx=8, dy=-7)
    v50 = _cl(0.050)
    p1.dot(0.050, v50, "s1", tip="ancienne calibration")
    p1.label(0.050, v50, f"0,050 % → {_num(v50, 3)}", dx=8, dy=13)
    # Seize points plus bas : à 246, la légende partageait sa ligne avec le
    # libellé d'abscisse du cadre, posé à 250.
    b.legend(62, 264, [("s3", "friction optimiste"), ("s1", "référence"),
                       ("s2", "réaliste")], step=150, kind="line")

    p2 = Panel(b, 62, 300, 496, 122, title="Stop et friction, en ticks du contrat",
               readout="stop 0,010 % · barre pleine = friction")
    contrats = (ES, NQ, MES, MNQ)
    p2.domain(-0.5, len(contrats) - 0.5, 0.0, 10.0)
    p2.frame()
    p2.grid_y([0, 2, 4, 6, 8, 10], lambda v: _num(v, 0), "ticks")
    p2.grid_x(list(range(len(contrats))), lambda v: contrats[int(v)].symbol)
    for i, c in enumerate(contrats):
        lvl = LEVELS[c.symbol]
        st = F.stop_ticks(c, lvl, STOP_PCT)
        fr = F.friction_ticks(c, COST_BASE)
        p2.vbar(i - 0.14, 0.0, st, 26, "hm2",
                tip=f"{c.symbol} — stop {_num(st, 2)} ticks")
        p2.vbar(i + 0.14, 0.0, fr, 26, "hm6" if fr < st else "negf",
                tip=f"{c.symbol} — friction {_num(fr, 2)} ticks")
        if fr >= st:
            p2.label(i, max(st, fr), "c/L > 1", dx=0, dy=-8, anchor="middle")
    b.legend(62, 446, [("hm2", "largeur du stop"),
                       ("hm6", "friction aller-retour"),
                       ("negf", "friction supérieure au stop")], step=180)
    b.caption(320, 464, "friction du scénario de référence — commission plus "
                        "un tick de sortie, aucune donnée de marché")
    return b.render("Friction rapportée au risque selon la largeur du stop, "
                    "et comparaison en ticks par contrat")


# ---------------------------------------------------------------------------
# 2. Ce que le spread prend avant que le prix ne bouge
# ---------------------------------------------------------------------------

def fig_spread_bite() -> str:
    """Le rebond de cotation, et la part du stop qu'il consomme.

    À gauche, une trajectoire de prix efficient rigoureusement plate, entourée
    de son bid et de son ask : rien ne bouge, et pourtant le prix observé
    oscille d'un spread complet. Les trois niveaux de stop montrent lequel
    survit à cette oscillation. À droite, la probabilité d'être sorti par ce
    seul bruit en une minute.
    """
    b = Board(640, 430)
    tick = ES.tick_size
    demi = SPREAD_TICKS * tick / 2.0

    p1 = Panel(b, 62, 44, 300, 200, title="Prix efficient plat, prix observé",
               readout="modèle de Roll, spread d'un tick")
    n = 46
    noise = _Noise(1987)
    signe = [1 if noise.gauss() > 0 else -1 for _ in range(n)]
    p1.domain(0.0, n - 1.0, -0.75, 0.45)
    p1.band_y(-demi, demi, "wash")
    p1.frame()
    p1.grid_y([-0.6, -0.3, 0.0, 0.3], lambda v: _signed(v, 2),
              "points depuis l'entrée")
    p1.grid_x([0, 15, 30, 45], lambda v: f"{v:g}", "rafraîchissements de cotation")
    p1.path([(i, demi) for i in range(n)], "s3", dash="3 3")
    p1.path([(i, -demi) for i in range(n)], "s3", dash="3 3")
    p1.path([(i, 0.0) for i in range(n)], "s1")
    p1.path([(i, signe[i] * demi) for i in range(n)], "px")
    for pct, cls in ((0.005, "s2"), (0.010, "s2")):
        niveau = -stop_points(INDEX_LEVEL, pct)
        p1.hline(niveau, "lvl")
        p1.tag(niveau, f"stop {_num(pct, 3)} %", side="left")
    p1.label(0.5, 0.30, "ask", dx=0, dy=0)
    p1.label(0.5, -0.20, "bid", dx=0, dy=0)

    p2 = Panel(b, 404, 44, 154, 200, title="Part du stop",
               readout="consommée par le spread")
    p2.domain(-0.5, 2.5, 0.0, 1.0)
    p2.frame()
    p2.grid_y([0, 0.25, 0.5, 0.75, 1.0], lambda v: f"{v * 100:.0f} %")
    labels = ("0,005", "0,010", "0,050")
    p2.grid_x([0, 1, 2], lambda v: labels[int(v)], "stop, en %")
    for i, pct in enumerate((0.005, 0.010, 0.050)):
        part = F.spread_share(stop_points(INDEX_LEVEL, pct), SPREAD_TICKS * tick)
        p2.vbar(i, 0.0, part, 30, "negf" if part > 0.5 else "hm3",
                tip=f"spread = {part * 100:.0f} % du stop")
        p2.label(i, part, f"{part * 100:.0f} %", dx=0, dy=-7, anchor="middle")

    p3 = Panel(b, 62, 300, 496, 96,
               title="Probabilité d'être sorti par le seul bruit, en une minute",
               readout="premier passage sur le stop utile L − s")
    p3.domain(0.0020, 0.25, 0.0, 1.0, xlog=True)
    p3.band_x(STOP_PCT_BOX[0], STOP_PCT_BOX[1])
    p3.frame()
    p3.grid_y([0, 0.5, 1.0], lambda v: f"{v * 100:.0f} %")
    p3.grid_x([0.0025, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2], lambda v: _num(v, 3),
              "largeur du stop, en % de l'indice")
    pts = []
    for i in range(210):
        x = 0.0020 * (1.0233 ** i)
        pts.append((x, F.noise_stop_probability(stop_points(INDEX_LEVEL, x),
                                                SPREAD_TICKS * tick, SIGMA_1MIN)))
    p3.path(pts, "s2")
    for x in STOP_PCT_BOX:
        v = F.noise_stop_probability(stop_points(INDEX_LEVEL, x),
                                     SPREAD_TICKS * tick, SIGMA_1MIN)
        p3.dot(x, v, "s2", tip=f"{v * 100:.1f} %")
        p3.label(x, v, f"{v * 100:.0f} %", dx=8, dy=-6)
    b.caption(320, 420, "trajectoire de cotation simulée de façon déterministe "
                        "— le prix efficient n'y bouge pas d'un point")
    return b.render("Rebond de cotation, part du stop consommée par le spread, "
                    "et probabilité de sortie par le bruit seul")


# ---------------------------------------------------------------------------
# 3. Le forçage
# ---------------------------------------------------------------------------

def fig_forcing_ladder() -> str:
    """Le coût d'une séquence forcée, et la loi des séries.

    À gauche, le résultat cumulé d'une séquence répétée jusqu'à la première
    réussite : le brut revient exactement à zéro à la tentative `R+1`, la
    friction ne revient jamais. À droite, la probabilité d'observer au moins
    `k` échecs consécutifs, aux trois ratios, avec la bande de ce que
    l'opérateur observe.
    """
    b = Board(640, 424)
    cl = _cl(STOP_PCT)
    p = F.martingale_hit_rate(RR_REF)
    n_max = int(round(1.0 / p)) + 4

    p1 = Panel(b, 62, 46, 300, 196, title="Résultat cumulé d'une séquence forcée",
               readout=f"1:{RR_REF:.0f}, stop {_num(STOP_PCT, 3)} %")
    p1.domain(0.0, float(n_max), -24.0, 4.0)
    p1.frame()
    p1.grid_y([-24, -18, -12, -6, 0], lambda v: _signed(v, 0),
              "multiples du risque")
    p1.grid_x([0, 7, 14, 21], lambda v: f"{v:g}", "tentatives")
    p1.hline(0.0, "zero")
    brut, net = [(0.0, 0.0)], [(0.0, 0.0)]
    for k in range(1, n_max + 1):
        gagne = k == int(round(1.0 / p))
        db = RR_REF if gagne else -1.0
        brut.append((float(k), brut[-1][1] + db))
        net.append((float(k), net[-1][1] + db - cl))
    p1.path(brut, "s3", dash="4 3", tip="avant friction")
    p1.path(net, "s2", tip="après friction")
    fin = net[int(round(1.0 / p))][1]
    p1.dot(1.0 / p, fin, "s2", tip=f"{_signed(fin, 2)} R")
    p1.label(1.0 / p, fin, f"{_signed(fin, 1)} R", dx=-8, dy=14, anchor="end")
    p1.label(2.0, 1.6, "brut : revient exactement à zéro")
    # Dix points plus haut : à 262, la légende partageait sa ligne avec les
    # libellés d'abscisse des deux cadres, posés à 270.
    b.legend(62, 252, [("s3", "avant friction"), ("s2", "après friction")],
             step=160, kind="line")

    p2 = Panel(b, 404, 46, 154, 196, title="Séries d'échecs",
               readout="P(au moins k)")
    p2.domain(0.0, 12.0, 0.0, 1.0)
    p2.band_x(float(F.OBSERVED_STREAK[0]), float(F.OBSERVED_STREAK[1]))
    p2.frame()
    p2.grid_y([0, 0.25, 0.5, 0.75, 1.0], lambda v: f"{v * 100:.0f} %")
    p2.grid_x([0, 3, 6, 9, 12], lambda v: f"{v:g}", "échecs consécutifs")
    for rr, cls in ((5.0, "s3"), (10.0, "s1"), (20.0, "s2")):
        q = F.martingale_hit_rate(rr)
        p2.path([(float(k), F.streak_probability(q, k)) for k in range(13)], cls,
                tip=f"1:{rr:.0f}")
        p2.label(12.0, F.streak_probability(q, 12), f"1:{rr:.0f}", dx=-4, dy=-5,
                 anchor="end")
    v = F.streak_probability(p, F.OBSERVED_STREAK[1])
    p2.dot(float(F.OBSERVED_STREAK[1]), v, "s2")

    # La lecture longue passait sur deux lignes — c'est ce que fait `Panel`
    # quand titre et lecture ne tiennent pas côte à côte — et la ligne du
    # dessus tombait sur les libellés d'abscisse des cadres du haut. L'unité
    # part sur l'axe, où elle a sa place, et la lecture se réduit à ce que le
    # titre ne dit pas.
    p3 = Panel(b, 62, 300, 496, 68,
               title="Ce que le forçage coûte, par ratio visé",
               readout="par largeur de stop")
    ratios = (5.0, 10.0, 20.0, 30.0)
    p3.domain(-0.5, len(ratios) - 0.5, -36.0, 0.0)
    p3.frame()
    p3.grid_y([-36, -24, -12, 0], lambda v: _signed(v, 0),
              "multiples du risque")
    p3.grid_x(list(range(len(ratios))), lambda v: f"1:{ratios[int(v)]:.0f}")
    for i, rr in enumerate(ratios):
        for j, (pct, cls) in enumerate(((0.010, "hm3"), (0.005, "hm6"))):
            f = F.force_until_success(rr, _cl(pct))
            p3.vbar(i - 0.15 + 0.30 * j, 0.0, f.net_r, 24, cls,
                    tip=f"1:{rr:.0f}, stop {_num(pct, 3)} % — {_signed(f.net_r, 2)} R")
    b.legend(62, 392, [("hm3", "stop 0,010 %"), ("hm6", "stop 0,005 %")], step=170)
    b.caption(320, 414, "sous prix sans dérive — le brut est nul par le "
                        "théorème d'arrêt optionnel, seule la friction reste")
    return b.render("Coût cumulé d'une séquence forcée, loi des séries "
                    "d'échecs, et coût du forçage par ratio visé")


# ---------------------------------------------------------------------------
# 4. Le capital, et le levier que la géométrie impose
# ---------------------------------------------------------------------------

def fig_capital_path() -> str:
    """Ce qu'une série fait au capital, et le levier qu'impose le couple.

    Le panneau du haut compose les pertes plutôt que de les additionner. Le
    panneau du bas montre que le levier n'est pas un troisième choix : il est
    fixé par la fraction risquée et la largeur du stop, et il fixe à son tour
    ce qu'un écart d'ouverture emporte.
    """
    b = Board(640, 434)

    p1 = Panel(b, 62, 46, 496, 172, title="Capital après k pertes consécutives",
               readout="fraction risquée par tentative")
    p1.domain(0.0, 34.0, 0.3, 1.0)
    p1.band_x(float(F.OBSERVED_STREAK[0]), float(F.OBSERVED_STREAK[1]))
    p1.frame()
    p1.grid_y([0.3, 0.5, 0.7, 0.9, 1.0], lambda v: f"{v * 100:.0f} %",
              "capital restant")
    p1.grid_x([0, 6, 12, 18, 24, 30], lambda v: f"{v:g}", "pertes consécutives")
    for f, cls in ((0.005, "s3"), (0.01, "s1"), (0.02, "s2")):
        pts = [(float(k), 1.0 - F.drawdown_after(f, k)) for k in range(35)]
        p1.path(pts, cls, tip=f"{f * 100:g} % par tentative")
        p1.label(34.0, pts[-1][1], f"{_num(f * 100, 1)} %", dx=-4, dy=-5,
                 anchor="end")
    for k in F.OBSERVED_STREAK:
        v = 1.0 - F.drawdown_after(0.02, k)
        p1.dot(float(k), v, "s2", tip=f"{k} pertes — {_num((1 - v) * 100, 1)} % effacés")
    n50 = F.losses_to_drawdown(0.02, 0.5)
    p1.vline(n50, "lvl")
    # Ancrée à gauche du trait : le trait tombe sur le bord droit du cadre —
    # la moitié du capital part à la trente-quatrième perte, dernière abscisse
    # du domaine — et l'étiquette posée à sa droite sortait de la planche.
    p1.label(n50, 0.92, f"−50 % à {_num(n50, 0)} pertes", dx=-6, dy=0,
             anchor="end", cls="dl halo")
    # La légende descend dans le tiers bas du cadre, que les trois courbes
    # laissent vide : posée sous le cadre, elle partageait sa ligne avec le
    # libellé d'abscisse.
    b.legend(76, p1.sy(0.40), [("s3", "0,5 % par tentative"), ("s1", "1 %"),
                               ("s2", "2 %")], step=150, kind="line")

    p2 = Panel(b, 62, 296, 496, 96,
               title="Levier notionnel imposé, et ce qu'un écart emporte",
               readout="à 2 % du capital par tentative")
    p2.domain(0.0020, 0.25, 8.0, 900.0, xlog=True, ylog=True)
    p2.band_x(STOP_PCT_BOX[0], STOP_PCT_BOX[1])
    p2.frame()
    p2.grid_y([10, 40, 100, 400, 900], lambda v: f"{v:g}×", "levier")
    p2.grid_x([0.0025, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2], lambda v: _num(v, 3),
              "largeur du stop, en % de l'indice")
    p2.path([(x, F.leverage(F.RISK_PER_TRADE, x))
             for x in [0.0020 * (1.0233 ** i) for i in range(210)]], "s2")
    for x in STOP_PCT_BOX:
        lv = F.leverage(F.RISK_PER_TRADE, x)
        efface = F.gap_wipeout(F.RISK_PER_TRADE, x, 0.5) * 100.0
        p2.dot(x, lv, "s2")
        p2.label(x, lv, f"{_num(lv, 0)}× — un écart de 0,5 % efface "
                        f"{_num(efface, 0)} %", dx=8, dy=-6)
    b.caption(320, 424, "la composition, non la somme — et le levier n'est pas "
                        "un choix séparé, il est fixé par les deux autres")
    return b.render("Capital restant après une série de pertes, et levier "
                    "notionnel imposé par la largeur du stop")


# ---------------------------------------------------------------------------
# 5. Ce qu'il faudrait posséder
# ---------------------------------------------------------------------------

def fig_sharpe_requirement() -> str:
    """Le ratio de Sharpe annualisé qu'exige chaque largeur de stop.

    C'est la traduction la plus lisible du resserrement, parce qu'elle place
    l'exigence sur une échelle que tout le monde lit. Les repères ne sont pas
    décoratifs : ils disent à quelle hauteur la barre est placée par rapport à
    ce que le métier produit.
    """
    b = Board(640, 400)

    p1 = Panel(b, 66, 48, 492, 232,
               title="Ratio de Sharpe annualisé exigé du signal",
               readout="µ* = c/E[τ], ratio 1:20, friction de référence")
    p1.domain(0.0020, 0.25, 0.4, 200.0, xlog=True, ylog=True)
    p1.band_x(STOP_PCT_BOX[0], STOP_PCT_BOX[1])
    p1.frame()
    p1.grid_y([0.5, 1, 2, 5, 10, 30, 100, 200], lambda v: _num(v, 1),
              "Sharpe annualisé requis")
    p1.grid_x([0.0025, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2], lambda v: _num(v, 3),
              "largeur du stop, en % de l'indice")

    pts = []
    for i in range(210):
        x = 0.0020 * (1.0233 ** i)
        pts.append((x, F.required_sharpe_annual(COST_BASE.friction_points(ES),
                                                _exposure(x), SIGMA_1MIN)))
    p1.path(pts, "s2")

    for niveau, texte in ((1.0, "un bon fonds sur longue période"),
                          (3.0, "les meilleurs résultats publiés")):
        p1.hline(niveau, "lvl")
        p1.label(0.0022, niveau, texte, dx=0, dy=-5)

    for x in list(STOP_PCT_BOX) + [0.050]:
        v = F.required_sharpe_annual(COST_BASE.friction_points(ES),
                                     _exposure(x), SIGMA_1MIN)
        p1.dot(x, v, "s2", tip=f"stop {_num(x, 3)} % — Sharpe {_num(v, 1)}")
        p1.label(x, v, f"{_num(x, 3)} % → {_num(v, 1)}", dx=8,
                 dy=13 if x > 0.02 else -7)

    p2 = Panel(b, 66, 328, 492, 34, title="Exposition moyenne d'une tentative",
               readout="minutes, sous contrainte de séance")
    p2.domain(0.0020, 0.25, 0.0, 32.0, xlog=True)
    p2.frame()
    p2.grid_y([0, 15, 30], lambda v: f"{v:g}")
    p2.band_x(STOP_PCT_BOX[0], STOP_PCT_BOX[1])
    p2.path([(x, _exposure(x)) for x in
             [0.0020 * (1.0233 ** i) for i in range(210)]], "s1")
    b.caption(320, 388, "l'exigence monte par deux canaux à la fois — la "
                        "friction relative croît, l'exposition s'effondre")
    return b.render("Ratio de Sharpe annualisé exigé selon la largeur du stop, "
                    "et exposition moyenne correspondante")


# ---------------------------------------------------------------------------
# 6. Le diagnostic inverse
# ---------------------------------------------------------------------------

def fig_streak_diagnostic() -> str:
    """Ce que la plus longue série d'échecs révèle du ratio réellement pratiqué.

    L'opérateur connaît deux chiffres sans avoir rien à mesurer : le nombre de
    tentatives qu'il a faites, et sa plus longue série d'échecs. La carte les
    croise et rend le ratio gain/risque que ce couple implique sous prix sans
    dérive. C'est le seul instrument du document qui ne demande aucune donnée
    de marché et rende pourtant une propriété de la pratique.
    """
    b = Board(640, 400)
    series = list(range(2, 25))
    tailles = [50, 100, 200, 400, 800]

    p1 = Panel(b, 74, 48, 380, 244, title="Ratio impliqué par la série observée",
               readout="sous prix sans dérive")
    p1.domain(-0.5, len(tailles) - 0.5, series[0] - 0.5, series[-1] + 0.5)
    cw = p1.w / len(tailles)
    ch = p1.h / len(series)
    for j, n in enumerate(tailles):
        for i, k in enumerate(series):
            x = p1.x + cw * j
            y = p1.sy(k) - ch / 2
            hit = F.implied_hit_rate(k, n)
            if hit <= 0.0:
                # Hors domaine : sur cet échantillon, aucun taux de réussite
                # ne produit en espérance une série aussi longue. La case
                # reste vide plutôt que de recevoir une couleur qui la ferait
                # lire comme une valeur.
                b.add(f'<rect class="mesh" x="{x:.2f}" y="{y:.2f}" '
                      f'width="{cw + 0.4:.2f}" height="{ch + 0.4:.2f}">'
                      f'<title>{n} tentatives, série de {k} — hors domaine'
                      f'</title></rect>')
                continue
            rr = F.implied_reward_risk(hit)
            u = min(math.log10(max(rr, 0.1)) + 1.0, 3.0) / 3.0
            step = min(7, max(0, int(round(u * 7))))
            b.add(f'<rect class="hm{step}" x="{x:.2f}" y="{y:.2f}" '
                  f'width="{cw + 0.4:.2f}" height="{ch + 0.4:.2f}">'
                  f'<title>{n} tentatives, série de {k} → 1:{_num(rr, 2)}</title>'
                  f'</rect>')
    p1.grid_y([5, 10, 15, 20], lambda v: f"{v:g}", "plus longue série d'échecs")
    p1.grid_x(list(range(len(tailles))), lambda v: f"{tailles[int(v)]:g}",
              "tentatives au total")
    p1.frame()

    p2 = Panel(b, 490, 48, 68, 244, title="1:R", readout="")
    p2.domain(0.0, 1.0, -1.0, 2.0)
    for step in range(8):
        y0 = -1.0 + 3.0 * step / 8.0
        y1 = -1.0 + 3.0 * (step + 1) / 8.0
        b.add(f'<rect class="hm{step}" x="{p2.x:.1f}" y="{p2.sy(y1):.1f}" '
              f'width="{p2.w:.1f}" height="{abs(p2.sy(y1) - p2.sy(y0)):.1f}"/>')
    p2.grid_y([-1, 0, 1, 2], lambda v: f"1:{10 ** v:g}", side="right")
    p2.frame()

    ligne = []
    for k in series:
        hit = F.implied_hit_rate(k, 200)
        if hit > 0.0:
            ligne.append((float(k), F.implied_reward_risk(hit)))
    p3 = Panel(b, 74, 336, 380, 30, title="", readout="")
    p3.domain(float(series[0]), float(series[-1]), 0.1, 12.0, ylog=True)
    p3.frame()
    p3.grid_y([0.5, 3, 12], lambda v: f"1:{_num(v, 1)}")
    p3.grid_x([5, 10, 15, 20], lambda v: f"{v:g}",
              "coupe à 200 tentatives — série d'échecs")
    p3.path(ligne, "s2")
    for k in F.OBSERVED_STREAK:
        rr = F.implied_reward_risk(F.implied_hit_rate(k, 200))
        p3.dot(float(k), rr, "s2", tip=f"série de {k} → 1:{_num(rr, 2)}")
    b.caption(320, 392, "une série maximale courte n'est pas une bonne "
                        "nouvelle : elle implique un ratio bas — les cases "
                        "hachurées sont hors domaine")
    return b.render("Ratio gain/risque impliqué par la plus longue série "
                    "d'échecs et le nombre de tentatives")


def render_all() -> dict[str, str]:
    return {
        "riskwall": fig_friction_wall(),
        "riskspread": fig_spread_bite(),
        "riskforcing": fig_forcing_ladder(),
        "riskcapital": fig_capital_path(),
        "risksharpe": fig_sharpe_requirement(),
        "riskstreak": fig_streak_diagnostic(),
    }


if __name__ == "__main__":
    for key, svg in render_all().items():
        print(f"{key}: {len(svg):,} octets")
