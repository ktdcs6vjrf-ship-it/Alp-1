"""Les planches du document — 2D et reliefs 3D, sur la boîte à outils d'ALP.

Même contrat que les `fig*.py` d'ALP : chaque figure est une chaîne SVG, aucune
couleur n'est écrite en dur (tout passe par les classes de `alp1.figcss`), le
domaine se déduit des données, un fond se peint avant ce qu'il souligne, et le
libellé ARIA ne porte aucune apostrophe. Les reliefs sont des nuages de points
(`figdisc._surface`), le maximum au fond.
"""

from __future__ import annotations

import math
from functools import lru_cache

from alp1.figdisc import (HEAD, LEGEND_BAR_X, LEGEND_MARGIN, W, _colorbar, _plate,
                          _ramp, _source, _surface)
from alp1.figterm import Panel, _num

from . import (calendrier, choisir, demander, mesurer, negocier, offrir, persuader,
               registre, revenir, stats, synthese)

FIGURES: dict = {}

#: Noms courts des hypothèses, pour les planches. Ils ne remplacent pas
#: l'énoncé du registre : l'infobulle de chaque point le porte en entier.
COURT = {
    "D01": "merci d'avance", "D02": "promettre de rendre", "D03": "montrer une preuve",
    "D04": "récit d'emploi", "D05": "récit d'argent", "D06": "récit familial",
    "D07": "récit étudiant", "D08": "simple envie", "D09": "demande longue",
    "D10": "karma élevé", "D11": "compte ancien", "D12": "déjà membre",
    "D13": "« please »", "D14": "urgence", "D15": "début de mois", "D16": "week-end",
    "D17": "le soir",
    "O01": "bonus présent", "O02": "bonus plus gros", "O03": "plafond plus haut",
    "O04": "montant suggéré", "O05": "donateur récent", "O06": "donateur fréquent",
    "O07": "bonus × récence", "O08": "bonus × État", "O09": "panier avec bonus",
    "O10": "montants ronds",
    "P01": "questions", "P02": "montant précis", "P03": "« je donne aussi »",
    "P04": "« vous êtes libre »", "P05": "émotion", "P06": "personne agréable",
    "P07": "même style", "P08": "messages longs", "P09": "demander tôt",
    "P10": "engagé d'emblée", "P11": "il questionne", "P12": "« merci »",
    "N01": "annonce précise", "N02": "chiffrer le premier", "N03": "ancre de l'acheteur",
    "N04": "négociation longue", "N05": "contre-offre précise", "N06": "citer l'état",
    "N07": "se dire ferme", "N08": "accords perdus",
    "S01": "contraste", "S02": "fatigue", "S03": "désir non sélectif",
    "S04": "goût rendu", "S05": "niche clivante", "S06": "croire être aimé",
    "S07": "première rencontre",
    "R01": "BG/NBD contre rythme", "R02": "fidèle silencieux", "R03": "décile de tête",
    "R04": "dépense passée", "T01": "le 13 du mois",
}


def _fig(cle: str):
    def deco(f):
        FIGURES[cle] = f
        return f
    return deco


def _pct(v: float, nd: int = 1) -> str:
    return _num(v * 100, nd) + " %"


def _graduations(lo: float, hi: float, n: int = 5) -> list[float]:
    """Graduations rondes **dans** le domaine, jamais au-delà."""
    if hi <= lo:
        return [lo]
    brut = (hi - lo) / max(n - 1, 1)
    e = 10 ** math.floor(math.log10(brut))
    pas = min((m * e for m in (1, 2, 2.5, 5, 10) if m * e >= brut), default=10 * e)
    k0 = math.ceil(lo / pas - 1e-9)
    out = []
    v = k0 * pas
    while v <= hi + 1e-9 * pas:
        out.append(round(v, 10))
        v += pas
    return out


def _echine(lo: float, hi: float, fmt) -> list[tuple[float, str]]:
    ticks = _graduations(lo, hi, 4)
    while len(ticks) > 4:
        ticks = ticks[::2]
    return [(t, fmt(t)) for t in ticks if lo - 1e-12 <= t <= hi + 1e-12]


def _cls_verdict(v: str) -> str:
    return {"tient": "s1", "contraire": "neg", "non établi": "s3"}[v]


def _eclaircir(labels: list[str], pas_px: float) -> list[str]:
    """Garde une étiquette sur k, k étant le plus petit pas qui les sépare.

    Le long d'une arête du sol, deux étiquettes voisines ne sont écartées que
    de `pas_px` en abscisse et de moins d'une hauteur de ligne en ordonnée :
    une étiquette plus large que le pas recouvre sa voisine. On garde donc la
    première, puis une toutes les k, et la dernière si elle ne heurte pas.
    """
    largeur = max((6.0 * len(l) for l in labels), default=0.0) + 6.0
    k = max(1, math.ceil(largeur / max(pas_px, 1e-9)))
    if k == 1:
        return labels
    garde = [l if j % k == 0 else "" for j, l in enumerate(labels)]
    dernier = len(labels) - 1
    if dernier % k and dernier % k >= k / 2 + 0.5:
        garde[dernier] = labels[dernier]
        garde[dernier - dernier % k] = "" if dernier - dernier % k != 0 else garde[0]
    return garde


def _relief(eyebrow, titre, lecture, z, rows, cols, fmt, tip, source, aria, legende_z,
            annotation=None, cz=130.0, tipv=None, plafond=None):
    """Une planche en relief : nuage, échine, légende de couleur, source.

    La hauteur de la planche se **calcule** : le sommet du coin du fond à la
    valeur haute se pose sous le bandeau, le coin avant au sol porte ses
    étiquettes, et la bande de pied vient dessous. Écrite à la main, elle
    faisait monter le relief sur le titre de quatre planches.
    """
    plat = [v for ligne in z for v in ligne]
    marge = (max(plat) - min(plat)) * 0.04 or 0.01
    zlo, zhi = min(plat) - marge, max(plat) + marge
    if min(plat) >= 0.0:
        zlo = max(0.0, zlo)
    if plafond is not None and max(plat) <= plafond:
        zhi = min(plafond, zhi)
    ni, nj = len(z), len(z[0])
    cx = min(30.0, 270.0 / max(ni + nj - 2, 1))
    cy = cx * 0.31
    oy = HEAD + 30 + cz
    bas = oy + (ni + nj - 2) * cy + 44
    hauteur = bas + (34 if annotation else 0) + 26
    b = _plate(hauteur, eyebrow, titre, lecture, width=W + LEGEND_MARGIN)
    _surface(b, 330, oy, z, zlo, zhi, cx=cx, cy=cy, cz=cz,
             row_labels=_eclaircir(rows, cx), col_labels=_eclaircir(cols, cx),
             z_ticks=_echine(zlo, zhi, fmt), tip=tip, tip_value=tipv, zero=zlo)
    _colorbar(b, W + LEGEND_BAR_X, HEAD + 34, HEAD + 34 + cz, zlo, zhi, fmt=fmt)
    b.add(f'<text class="tk" x="{W + LEGEND_BAR_X:.1f}" y="{HEAD + 56 + cz:.1f}">'
          f'{legende_z}</text>')
    if annotation:
        b.annotation(0, bas + 22, annotation)
    _source(b, source)
    return b.render(aria)


def _foret(p: Panel, items, x_lo, x_hi, fmt_x, label_x):
    """Diagramme en forêt : une ligne par item (étiquette, effet, bas, haut, classe, bulle)."""
    n = len(items)
    p.domain(x_lo, x_hi, -0.5, n - 0.5)
    p.frame()
    p.vline(0.0, cls="zero")
    p.grid_x(_graduations(x_lo, x_hi, 6), fmt=fmt_x, label=label_x, rules=True)
    for k, (lab, e, lo, hi, cls, bulle) in enumerate(items):
        y = n - 1 - k
        p.path([(max(lo, x_lo), y), (min(hi, x_hi), y)], cls)
        p.dot(min(max(e, x_lo), x_hi), y, cls, tip=bulle, r=3.2)
        p.board.add(f'<text class="tk" x="{p.x - 6:.1f}" y="{p.sy(y) + 3:.1f}" '
                    f'text-anchor="end">{lab}</text>')


# ---------------------------------------------------------------------------
# La chasse entière
# ---------------------------------------------------------------------------

@_fig("chasse")
def fig_chasse() -> str:
    from . import stats as S
    res, reg, q = synthese.tous(), registre.par_id(), synthese.q_valeurs()
    fams = list(registre.FAMILLES)
    passes = [r.p for i, r in res.items() if q[i] < synthese.SEUIL_Q]
    zbh = abs(S.Phi_inv(max(passes) / 2))
    xlo, xhi = -5.0, 12.0
    b = _plate(352, "Cinquante-neuf hypothèses, une seule correction",
               "La chasse entière, dans le sens de chaque pari",
               "z orienté : positif = sens annoncé")
    p = Panel(b, 92, HEAD + 22, W - 168, 212).domain(xlo, xhi, -0.5, len(fams) - 0.5)
    p.band_x(-1.96, 1.96, "wash")
    p.frame()
    p.vline(0.0, cls="zero")
    p.vline(zbh, cls="lvl strong")
    p.vline(-zbh, cls="lvl strong")
    p.grid_x([-4, -2, 0, 2, 4, 6, 8, 10, 12], fmt=lambda v: _num(v, 0), label="z orienté")
    b.add(f'<text class="tk" x="{p.x + p.w + 8:.1f}" y="{p.y - 2:.1f}">z &gt; 12</text>')
    for k, f in enumerate(fams):
        y = len(fams) - 1 - k
        b.add(f'<text class="tk" x="{p.x - 6:.1f}" y="{p.sy(y) + 3:.1f}" '
              f'text-anchor="end">{registre.FAMILLES[f]}</text>')
        ids = [i for i in res if i.startswith(f)]
        hors = []
        for j, i in enumerate(ids):
            z = synthese.z_oriente(i)
            v = synthese.verdict(i)
            dy = ((j % 5) - 2) * 0.13
            bulle = f"{i} {reg[i].enonce} : z {_num(z, 2)}, q {_num(q[i], 4)}, {v}"
            p.dot(min(max(z, xlo), xhi), y + dy, _cls_verdict(v), tip=bulle, r=3.4)
            if z > xhi:
                hors.append(_num(z, 0))
        if hors:
            b.add(f'<text class="tk" x="{p.x + p.w + 8:.1f}" y="{p.sy(y) + 3:.1f}">'
                  f'{" · ".join(hors[:2])}</text>')
            if len(hors) > 2:
                b.add(f'<text class="tk" x="{p.x + p.w + 8:.1f}" y="{p.sy(y) + 15:.1f}">'
                      f'{" · ".join(hors[2:])}</text>')
    b.legend(0, 312, [("s1f", "tient après correction"), ("negf", "contraire au pari"),
                      ("s3f", "non établi")], step=190)
    _source(b, (f"Chaque point est une hypothèse du registre, placée à son z orienté : "
                f"positif quand l'effet va dans le sens annoncé. La bande claire est la zone "
                f"|z| < 1,96 ; les deux traits pleins sont le seuil de Benjamini-Hochberg sur la "
                f"famille entière (|z| > {_num(zbh, 2)}). Les points au-delà de 12 sont posés au "
                f"bord, et leur valeur est écrite à droite du cadre."))
    return b.render("Nuage des cinquante neuf hypotheses du registre selon leur z oriente "
                    "et leur famille, avec le seuil corrige")


@_fig("pvaleurs")
def fig_pvaleurs() -> str:
    ps = [r.p for r in synthese.tous().values()]
    bins = 10
    c = [0] * bins
    for v in ps:
        c[min(int(v * bins), bins - 1)] += 1
    attendu = len(ps) / bins
    b = _plate(270, "Ce que le bruit seul aurait donné",
               "Les valeurs p de la famille, contre leur loi nulle",
               f"{len(ps)} tests, {_num(attendu, 1)} attendus par case sous le bruit")
    p = Panel(b, 56, HEAD + 18, W - 70, 150).domain(0, 1, 0, max(c) * 1.1)
    p.frame()
    p.grid_y(_graduations(0, max(c) * 1.1, 5), fmt=lambda v: _num(v, 0), label="tests")
    p.grid_x([k / 10 for k in range(11)], fmt=lambda v: _num(v, 1), label="valeur p")
    for k, n in enumerate(c):
        p.vbar((k + 0.5) / bins, 0, n, (p.w / bins) * 0.78, "s2f",
               tip=f"p entre {_num(k / bins, 1)} et {_num((k + 1) / bins, 1)} : {n} tests")
    p.hline(attendu, cls="lvl strong")
    p.label(0.62, attendu, f"loi nulle : {_num(attendu, 1)} par case", dy=-6, cls="tk halo")
    _source(b, ("Sous le seul hasard, les valeurs p sont uniformes : la même hauteur dans "
                "chaque case. L'excès de la première case est ce que les données portent ; "
                "le reste a l'allure du bruit, et la correction de Benjamini-Hochberg décide "
                "lesquels des tests de la première case on garde."))
    return b.render("Histogramme des valeurs p des cinquante neuf tests contre la loi uniforme")


# ---------------------------------------------------------------------------
# Demander
# ---------------------------------------------------------------------------

@_fig("raop_leviers")
def fig_raop_leviers() -> str:
    res, reg = synthese.tous(), registre.par_id()
    ids = [f"D{k:02d}" for k in range(1, 18)]
    items = []
    for i in ids:
        r = res[i]
        v = synthese.verdict(i)
        items.append((f"{i} {COURT[i]}", r.effet,
                      r.ic[0], r.ic[1], _cls_verdict(v),
                      f"{i} {reg[i].enonce} : {_num(r.effet, 1)} pt [{_num(r.ic[0], 1)} ; "
                      f"{_num(r.ic[1], 1)}], {v}"))
    b = _plate(410, "Random Acts of Pizza — 4 040 demandes",
               "Ce qui fait recevoir, toutes choses du registre égales",
               f"base {_pct(demander.base_globale())} de demandes servies")
    p = Panel(b, 170, HEAD + 16, W - 184, 17 * 16)
    _foret(p, items, -10.0, 22.0, lambda v: _num(v, 0), "effet ajusté, en points de pourcentage")
    b.legend(0, 374, [("s1f", "tient"), ("s3f", "non établi")], step=110)
    _source(b, ("Coefficients d'un modèle linéaire de probabilité qui contient les dix-sept "
                "variables à la fois et la tendance du forum ; traits : intervalles à 95 % "
                "robustes. Les plus forts ne sont pas des formules mais des faits sur la "
                "personne qui demande : présence préalable dans la communauté, preuve, statut."))
    return b.render("Effets ajustes des dix sept variables de demande sur la probabilite de "
                    "recevoir une pizza")


@_fig("raop_calendrier")
def fig_raop_calendrier() -> str:
    base = demander.base_globale()
    jours = demander.taux_par("jour", range(1, 32))
    heures = demander.taux_par("heure", range(24))
    hors = demander.hors_bande()
    b = _plate(300, "Le moment de la demande", "Le jour du mois ne dit rien, la nuit peut-être",
               "bande : loi nulle binomiale autour de la base")
    w = (W - 90) / 2
    for k, (serie, titre, x0, x1, fmtx, lab) in enumerate((
            (jours, "jour du mois", 0.5, 31.5, lambda v: _num(v, 0), "jour du mois (New York)"),
            (heures, "heure", -0.5, 23.5, lambda v: _num(v, 0) + " h", "heure (New York)"))):
        p = Panel(b, 62 + k * (w + 34), HEAD + 30, w - 6, 160, title=titre.upper())
        p.domain(x0, x1, 0.0, 0.5)
        lo = [(v, base - 1.96 * math.sqrt(base * (1 - base) / n)) for v, _, n, _ in serie]
        hi = [(v, base + 1.96 * math.sqrt(base * (1 - base) / n)) for v, _, n, _ in serie]
        pts = hi + list(reversed(lo))
        d = " ".join(("M" if j == 0 else "L") + f"{p.sx(x):.1f},{p.sy(y):.1f}"
                     for j, (x, y) in enumerate(pts)) + " Z"
        b.add(f'<path class="band" d="{d}"/>')
        p.frame()
        p.grid_y([0.0, 0.1, 0.2, 0.3, 0.4, 0.5], fmt=lambda v: _pct(v, 0),
                 label="servies" if k == 0 else None)
        ticks = [1, 5, 10, 15, 20, 25, 31] if k == 0 else [0, 4, 8, 12, 16, 20]
        p.grid_x(ticks, fmt=fmtx, label=lab)
        p.hline(base, cls="lvl")
        for v, t, n, h in serie:
            p.path([(v, max(t - h, 0)), (v, min(t + h, 0.5))], "s3")
            p.dot(v, t, "s1", tip=f"{titre} {v} : {_pct(t)} sur {n} demandes", r=2.6)
    nuit = demander.nuit()
    _source(b, (f"Points : part des demandes servies, traits : intervalle à 95 %. La bande est "
                f"ce que donnerait le seul hasard autour de la base, à l'effectif de chaque jour "
                f"ou de chaque heure. {hors['dehors']} points sur {hors['total']} en sortent, quand "
                f"le hasard en ferait sortir {_num(hors['attendus'], 1)} : {hors['jours']} jours "
                f"voisins qui alternent au-dessus et au-dessous, et {hors['heures']} heures. Les "
                f"demandes de nuit (0 h à 6 h) sont servies à {_pct(nuit['a'])} contre "
                f"{_pct(nuit['b'])} : un écart que le registre n'avait pas parié."))
    return b.render("Part des demandes servies selon le jour du mois et selon heure, avec la "
                    "bande de la loi nulle")


@_fig("raop_relief")
def fig_raop_relief() -> str:
    z, qk, qm = demander.grille_statut_effort()
    z = [list(reversed(l)) for l in reversed(z)]
    return _relief(
        "Statut et effort", "Le karma et la longueur se cumulent",
        "hauteur : part des demandes servies", z,
        ["karma Q5", "Q4", "Q3", "Q2", "Q1"], ["mots Q5", "Q4", "Q3", "Q2", "Q1"],
        lambda v: _pct(v, 0), "{v:.1f} % de demandes servies",
        (f"Arête gauche : quintile du solde de votes du demandeur (Q5 le plus haut). Arête "
         f"droite : quintile de longueur du texte. Chaque nœud porte la part des demandes "
         f"servies de sa cellule. Le coin du fond — le compte le mieux noté qui écrit le plus "
         f"long — est servi à {_pct(z[0][0])}, le coin avant à {_pct(z[-1][-1])} ; le sommet, "
         f"{_pct(max(max(l) for l in z))}, est sur le versant des comptes les mieux notés."),
        "Relief de la part des demandes servies selon le quintile de karma et le quintile de "
        "longueur", "part servie", tipv=lambda v: v * 100)


# ---------------------------------------------------------------------------
# Offrir
# ---------------------------------------------------------------------------

@_fig("karlan_bras")
def fig_karlan_bras() -> str:
    bras = offrir.taux_bras()
    c = offrir.comptes_montants(110)
    b = _plate(318, "Karlan et List — 50 083 lettres tirées au sort",
               "La présence du bonus compte, pas sa taille",
               "gauche : taux de don ; droite : montants choisis")
    p = Panel(b, 56, HEAD + 30, 196, 170, title="TAUX DE DON PAR BRAS")
    hi = max(t + h for _, t, h, _ in bras) * 1.15
    p.domain(-0.5, 3.5, 0, hi)
    p.frame()
    p.grid_y(_graduations(0, hi, 5), fmt=lambda v: _pct(v, 1), label="ont donné")
    for k, (nom, t, h, n) in enumerate(bras):
        p.vbar(k, 0, t, 30, "s3f" if k == 0 else "s1f",
               tip=f"{nom} : {_pct(t, 2)} sur {n} lettres")
        p.path([(k, t - h), (k, t + h)], "s2")
        b.add(f'<text class="tk" x="{p.sx(k):.1f}" y="{p.y + p.h + 13:.1f}" '
              f'text-anchor="middle">{nom}</text>')
    q = Panel(b, 312, HEAD + 30, W - 324, 170, title="MONTANTS DONNÉS, AU DOLLAR")
    mx = max(c.values())
    q.domain(0, 111, 0, mx * 1.08)
    q.frame()
    q.grid_y(_graduations(0, mx * 1.08, 5), fmt=lambda v: _num(v, 0), label="dons")
    q.grid_x([0, 10, 25, 50, 75, 100], fmt=lambda v: _num(v, 0) + " $", label="montant")
    for a, n in sorted(c.items()):
        q.vbar(a, 0, n, 1.6, "s1f" if a % 5 == 0 else "s2f", tip=f"{a} $ : {n} dons")
    part = offrir.ronds().extra["part"]
    q.label(55, mx * 0.8, f"{_pct(part, 1)} sur un multiple de 5", cls="tk halo")
    _source(b, (f"Gauche : la lettre témoin fait {_pct(bras[0][1], 2)} de dons, les trois bras "
                f"traités {_pct(bras[1][1], 2)}, {_pct(bras[2][1], 2)} et {_pct(bras[3][1], 2)}, "
                f"intervalles à 95 % en blanc. Droite : "
                "chaque barre est un montant entier ; les multiples de 5 $ sont en accent. "
                "Sous une densité lisse, un don sur cinq tomberait sur le multiple de sa fenêtre."))
    return b.render("Taux de don par bras de la lettre et distribution des montants donnes au "
                    "dollar pres")


@_fig("karlan_relief")
def fig_karlan_relief() -> str:
    z, rows, cols = offrir.grille_ratio_recence()
    z = [list(reversed(l)) for l in z]
    return _relief(
        "Qui, plutôt que quoi", "La récence écrase le bonus",
        "hauteur : taux de don", z, rows, list(reversed(cols)),
        lambda v: _pct(v, 1), "{v:.2f} % de dons",
        (f"Arête gauche : mois écoulés depuis le dernier don. Arête droite : bras de la lettre. "
         f"Le long de la récence, la colonne témoin tombe de {_pct(z[0][-1], 2)} à "
         f"{_pct(z[-1][-1], 2)} ; le long du bonus, la ligne des plus récents passe de "
         f"{_pct(z[0][-1], 2)} à {_pct(z[0][0], 2)}. Le même courrier rapporte davantage "
         f"envoyé aux récents qu'enrichi d'un bonus."),
        "Relief du taux de don selon les mois depuis le dernier don et le bras de la lettre",
        "taux de don", tipv=lambda v: v * 100)


# ---------------------------------------------------------------------------
# Persuader
# ---------------------------------------------------------------------------

@_fig("p4g")
def fig_p4g() -> str:
    res, reg = synthese.tous(), registre.par_id()
    items = []
    for i in [f"P{k:02d}" for k in range(1, 13)]:
        r = res[i]
        v = synthese.verdict(i)
        items.append((f"{i} {COURT[i]}", r.effet, r.ic[0], r.ic[1], _cls_verdict(v),
                      f"{i} {reg[i].enonce} : {_num(r.effet, 1)} pt, {v}"))
    d = persuader.diagnostic_reponse()
    b = _plate(352, "Persuasion for Good — 1 012 conversations",
               "Ce qu'une tactique suit, avant ce qu'elle cause", "")
    p = Panel(b, 150, HEAD + 30, 200, 12 * 16, title="EFFET SUR LE DON (PT)")
    _foret(p, items, -40.0, 45.0, lambda v: _num(v, 0), "points de pourcentage")
    q = Panel(b, 424, HEAD + 30, W - 436, 150, title="CE QUI PRÉCÈDE LA PHRASE")
    q.domain(-0.6, 1.6, 0, 0.35)
    q.frame()
    q.grid_y([0, 0.1, 0.2, 0.3], fmt=lambda v: _pct(v, 0), label="messages précédés")
    groupes = (("libre", "hésitation", "« libre »"), ("merci", "accord", "« merci »"))
    for k, (cle, quoi, nom) in enumerate(groupes):
        apres, base, n = d[cle]
        q.vbar(k - 0.17, 0, base, 22, "s3f",
               tip=f"tous les messages : {_pct(base)} précédés d'un {quoi}")
        q.vbar(k + 0.17, 0, apres, 22, "s1f",
               tip=f"messages avec {nom} : {_pct(apres)} précédés d'un {quoi} ({n})")
        b.add(f'<text class="tk" x="{q.sx(k):.1f}" y="{q.y + q.h + 13:.1f}" '
              f'text-anchor="middle">{nom}</text>')
        b.add(f'<text class="tk" x="{q.sx(k):.1f}" y="{q.y + q.h + 25:.1f}" '
              f'text-anchor="middle">après un {quoi}</text>')
    b.legend(424, HEAD + 236, [("s3f", "tous les messages")], step=120)
    b.legend(424, HEAD + 254, [("s1f", "messages de la tactique")], step=120)
    _source(b, ("Gauche : effets ajustés des douze variables sur le don. Droite : part des "
                "messages précédés d'une hésitation du persuadé, sur l'ensemble et pour les "
                "messages qui disent « vous êtes libre » ; puis la même chose pour un accord et "
                "« merci ». Les deux tactiques suivent l'état de l'autre : dans un journal de "
                "conversation, elles mesurent la réponse à cet état, pas leur propre effet."))
    return b.render("Effets des tactiques de persuasion et part des messages precedes dune "
                    "hesitation ou dun accord")


# ---------------------------------------------------------------------------
# Négocier
# ---------------------------------------------------------------------------

@_fig("bargain")
def fig_bargain() -> str:
    an = negocier.ancrage()
    res, reg = synthese.tous(), registre.par_id()
    b = _plate(330, "CraigslistBargain — 5 351 accords",
               "La première offre fait le prix, et la précision le tient",
               f"pente {_num(res['N03'].effet, 2)}")
    p = Panel(b, 56, HEAD + 30, 250, 180, title="PRIX FINAL SELON LA 1RE OFFRE")
    p.domain(0.35, 1.05, 0.6, 0.95)
    p.frame()
    p.grid_y([0.6, 0.7, 0.8, 0.9], fmt=lambda v: _pct(v, 0), label="prix final / annonce")
    p.grid_x([0.4, 0.6, 0.8, 1.0], fmt=lambda v: _pct(v, 0), label="1re offre de l'acheteur / annonce")
    p.path([(x, y) for x, y, _ in an], "s1")
    for x, y, n in an:
        p.dot(x, y, "s1", tip=f"1re offre {_pct(x)} : prix final {_pct(y)} ({n} accords)", r=3)
    items = []
    for i in ("N01", "N02", "N04", "N05", "N06", "N07"):
        r = res[i]
        v = synthese.verdict(i)
        items.append((f"{i} {COURT[i]}", r.effet, r.ic[0], r.ic[1], _cls_verdict(v),
                      f"{i} {reg[i].enonce} : {_num(r.effet, 2)} pt de prix, {v}"))
    q = Panel(b, 396, HEAD + 30, W - 408, 6 * 22, title="EFFET SUR LE PRIX (PT)")
    _foret(q, items, -4.0, 8.0, lambda v: _num(v, 0), "points de prix")
    _source(b, (f"Gauche : prix final moyen par décile de première offre de l'acheteur, "
                f"rapportés au prix affiché. Droite : effets ajustés (catégorie, lot, log du prix) "
                f"de six gestes du vendeur. La contre-offre précise tient {_num(res['N05'].effet, 1)} "
                f"points de prix ; se dire « ferme » coïncide avec un prix plus bas "
                f"({_num(res['N07'].effet, 1)}), parce qu'on le dit quand on recule."))
    return b.render("Prix final selon la premiere offre de lacheteur et effets des gestes du "
                    "vendeur")


@_fig("bargain_relief")
def fig_bargain_relief() -> str:
    t = [l for l in negocier.table() if l["valide"] and l["prem_ach"] is not None
         and 0.05 <= l["prem_ach"] <= 1.5]
    from . import stats as S
    k = 5
    qa = [S.quantile([l["prem_ach"] for l in t], (i + 1) / k) for i in range(k - 1)]
    qp = [S.quantile([l["annonce"] for l in t], (i + 1) / k) for i in range(k - 1)]
    s = [[0.0] * k for _ in range(k)]
    n = [[0] * k for _ in range(k)]
    for l in t:
        a = sum(1 for x in qa if l["prem_ach"] > x)
        c = sum(1 for x in qp if l["annonce"] > x)
        s[a][c] += l["ratio"]
        n[a][c] += 1
    z = [[s[a][c] / n[a][c] for c in range(k)] for a in range(k)]
    ecarts = [z[k - 1][c] - z[0][c] for c in range(k)]
    z = list(reversed(z))
    return _relief(
        "L'ancre, à tous les prix", "Une offre basse tire le prix vers le bas partout",
        "hauteur : prix final / annonce", z,
        ["offre Q5", "Q4", "Q3", "Q2", "Q1"], ["prix Q1", "Q2", "Q3", "Q4", "Q5"],
        lambda v: _pct(v, 0), "{v:.1f} % de l'annonce",
        (f"Arête gauche : quintile de la première offre de l'acheteur rapportée à l'annonce "
         f"(Q5 la plus haute). Arête droite : quintile du prix affiché, du meuble bon marché "
         f"au logement. Dans chaque quintile de prix, passer de l'offre la plus basse à la plus "
         f"haute relève le prix final de {_num(min(ecarts) * 100, 1)} à "
         f"{_num(max(ecarts) * 100, 1)} points."),
        "Relief du prix final rapporte a lannonce selon le quintile de premiere offre et le "
        "quintile de prix", "prix final", tipv=lambda v: v * 100)


# ---------------------------------------------------------------------------
# Choisir
# ---------------------------------------------------------------------------

@_fig("speed_contraste")
def fig_speed_contraste() -> str:
    z, _, _ = choisir.contraste_grille()
    z = [list(l) for l in reversed(z)]
    r = synthese.tous()["S01"]
    return _relief(
        "Ce qu'il vient de voir", "La précédente pèse, un peu, sur la suivante",
        f"modèle : {_num(r.effet, 2)} pt par point d'attrait", z,
        ["courante Q4", "Q3", "Q2", "Q1"], ["précédente Q1", "Q2", "Q3", "Q4"],
        lambda v: _pct(v, 0), "{v:.1f} % de oui",
        (f"Arête gauche : quartile d'attrait de la partenaire courante (notes des autres "
         f"hommes). Arête droite : quartile d'attrait de la précédente. Pour une courante du "
         f"quartile haut, {_pct(z[0][0])} de oui après une précédente du quartile bas, "
         f"{_pct(z[0][-1])} après une du quartile haut ; les quartiles bas sont bruités. Le "
         f"modèle à effets fixes isole l'effet de la précédente, que la correction ne garde pas."),
        "Relief du taux de oui des hommes selon lattrait de la partenaire courante et de la "
        "precedente", "taux de oui", cz=130.0, tipv=lambda v: v * 100)


@_fig("speed_reciprocite")
def fig_speed_reciprocite() -> str:
    seq = choisir.sequences()
    par_prob = {}
    for s in seq:
        if s["prob"] is not None:
            k = int(round(s["prob"]))
            par_prob.setdefault(k, []).append(s["y"])
    rangs = choisir.oui_par_rang()
    b = _plate(300, "Speed dating — décisions de 270 hommes",
               "Il dit oui à qui il croit plaire", "")
    w = (W - 110) / 2
    p = Panel(b, 62, HEAD + 30, w - 12, 160, title="OUI SELON LA PROBABILITÉ PERÇUE")
    p.domain(0.5, 10.5, 0, 1)
    p.frame()
    p.grid_y([0, 0.25, 0.5, 0.75, 1], fmt=lambda v: _pct(v, 0), label="oui")
    p.grid_x(list(range(1, 11)), fmt=lambda v: _num(v, 0), label="« elle dira oui » (1 à 10)")
    pts = []
    for k in range(1, 11):
        ys = par_prob.get(k, [])
        if len(ys) >= 20:
            m = sum(ys) / len(ys)
            pts.append((k, m))
            p.dot(k, m, "s1", tip=f"probabilité perçue {k} : {_pct(m)} de oui ({len(ys)})", r=3)
    p.path(pts, "s1")
    q = Panel(b, 50 + w + 60, HEAD + 30, w, 160, title="OUI SELON LE RANG DANS LA SOIRÉE")
    ylo = math.floor((min(m for _, m, _ in rangs) - 0.03) * 50) / 50
    yhi = math.ceil((max(m for _, m, _ in rangs) + 0.03) * 50) / 50
    q.domain(0.5, max(k for k, _, _ in rangs) + 0.5, ylo, yhi)
    q.frame()
    q.grid_y(_graduations(ylo, yhi, 5), fmt=lambda v: _pct(v, 0))
    q.grid_x([1, 5, 10, 15, 20], fmt=lambda v: _num(v, 0), label="rang de la rencontre")
    q.path([(k, m) for k, m, _ in rangs], "s2")
    for k, m, n in rangs:
        q.dot(k, m, "s2", tip=f"rang {k} : {_pct(m)} de oui ({n})", r=2.6)
    r6, r7 = synthese.tous()["S06"], synthese.tous()["S07"]
    _source(b, (f"Gauche : part de oui des hommes selon la probabilité qu'ils prêtaient à un oui "
                f"en retour ; à attrait et plaisir fixés, chaque point vaut {_num(r6.effet, 1)} pt "
                f"de oui. Droite : part de oui par rang de la rencontre ; la première rencontre "
                f"vaut {_num(r7.effet, 1)} pt de plus que le milieu à décideur fixé, ce que la "
                f"correction ne garde pas."))
    return b.render("Taux de oui des hommes selon la probabilite percue dun oui en retour et "
                    "selon le rang de la rencontre")


@_fig("speed_polarisation")
def fig_speed_polarisation() -> str:
    z, ms, ss = choisir.surface_polarisation()
    z = [list(reversed(l)) for l in z]
    ss = list(reversed(ss))
    return _relief(
        "Une niche clivante ?", "La dispersion des goûts coûte, et plus encore en haut",
        "hauteur : oui prédit par le modèle", z,
        [_num(m, 1) for m in ms[:-1]] + [_num(ms[-1], 1) + " /10"],
        [_num(s, 1) for s in ss[:-1]] + [_num(ss[-1], 1) + " ét."],
        lambda v: _pct(v, 0), "{v:.1f} % de oui prédit",
        ("Arête gauche : moyenne des notes d'attrait reçues des autres hommes. Arête droite : "
         "leur écart-type. La théorie du seuil voudrait qu'à moyenne basse la dispersion paie ; "
         "le relief descend le long de l'écart-type partout, à peine en bas, fortement en haut."),
        "Relief du taux de oui predit selon la moyenne et la dispersion des notes recues",
        "oui prédit", cz=130.0, tipv=lambda v: v * 100)


# ---------------------------------------------------------------------------
# Revenir
# ---------------------------------------------------------------------------

@_fig("cdnow_suivi")
def fig_cdnow_suivi() -> str:
    s = revenir.suivi()
    hi = max(max(a, e) for _, a, e in s) * 1.05
    b = _plate(322, "CDNOW — 23 570 clients, 78 semaines",
               "Calibrer sur une moitié, prédire l'autre",
               "achats répétés cumulés")
    p = Panel(b, 70, HEAD + 18, W - 84, 170).domain(0, 78, 0, hi)
    p.band_x(39, 78, "wash")
    p.frame()
    p.grid_y(_graduations(0, hi, 5), fmt=lambda v: _num(v / 1000, 0) + " k", label="achats")
    p.grid_x([0, 13, 26, 39, 52, 65, 78], fmt=lambda v: _num(v, 0), label="semaine")
    p.path([(w, e) for w, _, e in s], "s2", dash="4 3",
           tip="attendu par le modèle BG/NBD")
    p.path([(w, a) for w, a, _ in s], "s1", tip="réalisé")
    p.label(41, hi * 0.08, "seconde moitié : prédiction", cls="tk halo")
    b.legend(0, 284, [("s1", "réalisé"), ("s2", "BG/NBD, calibré sur les 39 premières semaines", "4 3")],
             step=110, kind="line")
    _source(b, (f"La zone claire est la seconde moitié, jamais vue par le modèle. À la 39e "
                f"semaine, {_num(s[38][2], 0)} achats attendus pour {_num(s[38][1], 0)} réalisés ; "
                f"à la 78e, {_num(s[-1][2], 0)} pour {_num(s[-1][1], 0)}. L'écart de la seconde "
                f"moitié vient des clients que le modèle croit partis (figure suivante)."))
    return b.render("Achats repetes cumules reels et attendus par le modele BG NBD sur soixante "
                    "dix huit semaines")


@_fig("cdnow_paradoxe")
def fig_cdnow_paradoxe() -> str:
    tout = revenir.par_frequence()
    par = revenir.paradoxe()
    b = _plate(320, "Le silence n'est pas un départ",
               "Le fidèle qui se tait revient, le modèle le croit mort",
               "achats de la seconde moitié par client")
    w = (W - 110) / 2
    for k, (serie, titre, xs) in enumerate(((tout, "TOUS LES CLIENTS", "achats répétés, 1re moitié"),
                                             (par, "SILENCIEUX DEPUIS 26 SEMAINES", "achats répétés, 1re moitié"))):
        hi = max(max(h, p_) for _, h, p_, _ in serie) * 1.15
        p = Panel(b, 62 + k * (w + 54), HEAD + 30, w - 6, 170, title=titre)
        x0 = serie[0][0] - 0.6
        x1 = serie[-1][0] + 0.6
        p.domain(x0, x1, 0, hi)
        p.frame()
        p.grid_y(_graduations(0, hi, 5), fmt=lambda v: _num(v, 1), label="achats futurs" if k == 0 else None)
        p.grid_x([x for x, *_ in serie], fmt=lambda v: _num(v, 0) + ("+" if v == serie[-1][0] else ""),
                 label=xs)
        for x, h, pr, n in serie:
            p.vbar(x, 0, h, 14, "s1f", tip=f"{x} achats passés : {_num(h, 2)} réalisés ({n} clients)")
        p.path([(x, pr) for x, _, pr, _ in serie], "s2")
        for x, _, pr, n in serie:
            p.dot(x, pr, "s2", tip=f"{x} achats passés : {_num(pr, 2)} prévus", r=2.8)
    b.legend(0, 284, [("s1f", "réalisé"), ("s2f", "prévu par BG/NBD")], step=110)
    r = synthese.tous()["R02"]
    _source(b, (f"Gauche : sur l'ensemble, le modèle suit la fréquence passée. Droite : parmi "
                f"les clients sans achat depuis au moins 26 semaines, il prédit que les plus "
                f"fréquents sont les plus perdus ; ils reviennent au contraire davantage "
                f"({_num(r.effet, 2)} achat futur par achat passé, verdict contraire au pari)."))
    return b.render("Achats futurs reels et predits selon la frequence passee, pour tous les "
                    "clients et pour les silencieux")


@_fig("cdnow_vivant")
def fig_cdnow_vivant() -> str:
    z, xs, txs = revenir.surface_vivant(nx=8)
    z = [l for l in reversed(z[:-1])]
    xs = list(reversed(xs[:-1]))
    return _relief(
        "Ce que dit le modèle", "La probabilité d'être encore client",
        "hauteur : P(vivant) selon BG/NBD", z,
        [f"{x} achat" + ("s" if x > 1 else "") for x in xs],
        [f"sem. {_num(t, 0)}" for t in txs],
        lambda v: _pct(v, 0), "P(vivant) {v:.1f} %",
        ("Arête gauche : achats répétés pendant la calibration. Arête droite : semaine du "
         "dernier achat (39 : à la fin). Le modèle fait chuter P(vivant) quand un client "
         "fréquent se tait ; la planche précédente montre que les données ne le suivent pas."),
        "Relief de la probabilite detre encore client selon le modele BG NBD", "P(vivant)",
        tipv=lambda v: v * 100, plafond=1.0)


# ---------------------------------------------------------------------------
# Le calendrier
# ---------------------------------------------------------------------------

@_fig("naissances")
def fig_naissances() -> str:
    pr = calendrier.profil()
    lo = min(m - h for _, m, h, _ in pr) * 1.1
    hi = max(m + h for _, m, h, _ in pr) * 1.1
    b = _plate(280, "Contrôle positif — 5 479 jours de naissances",
               "La méthode voit le 13", "écart au même jour de la semaine ±7 jours")
    p = Panel(b, 60, HEAD + 18, W - 74, 160).domain(0.5, 31.5, lo, hi)
    p.frame()
    p.vline(13, cls="lvl")
    p.grid_y(_graduations(lo, hi, 5), fmt=lambda v: _num(v * 100, 0) + " %", label="écart")
    p.grid_x([1, 5, 10, 13, 15, 20, 25, 31], fmt=lambda v: _num(v, 0), label="date du mois")
    p.hline(0.0, cls="zero")
    for k, m, h, n in pr:
        cls = "neg" if k == 13 else "s1"
        p.path([(k, m - h), (k, m + h)], cls)
        p.dot(k, m, cls, tip=f"le {k} : {_num(m * 100, 2)} % ({n} jours)", r=2.8)
    r = synthese.tous()["T01"]
    _source(b, (f"Chaque date est comparée au même jour de la semaine une semaine avant et une "
                f"semaine après. Le 13 tombe seul sous zéro ({_num(r.effet, 2)} % au test apparié, "
                f"{_num(r.extra['vendredi'] * 100, 1)} % un vendredi 13). Les autres écarts sont "
                f"des fériés que la fenêtre de sept jours attrape."))
    return b.render("Ecart des naissances par date du mois au meme jour de la semaine, le "
                    "treize mis en evidence")


# ---------------------------------------------------------------------------
# Mesurer chez soi
# ---------------------------------------------------------------------------

@_fig("budget")
def fig_budget() -> str:
    z = mesurer.surface_budget()
    z = [list(reversed(l)) for l in reversed(z)]
    bases = list(reversed(mesurer.BASES))
    hausses = list(reversed(mesurer.HAUSSES))
    return _relief(
        "Le budget d'un test", "Combien d'envois pour prouver une hausse",
        "hauteur : envois par variante (log)", z,
        [_pct(v, 0) for v in bases], ["+" + _pct(h, 0) for h in hausses],
        lambda v: _num(10 ** v, 0) if v < 3 else _num(10 ** v / 1000, 0 if v >= 4 else 1) + " k",
        "{v} envois par variante",
        (f"Arête gauche : taux d'achat de base du message. Arête droite : hausse relative à "
         f"détecter. Hauteur : envois par variante, à 5 % de risque et 80 % de puissance, en "
         f"échelle logarithmique. Un message qui vend à 5 % et une hausse de 10 % demandent "
         f"{_num(stats.n_par_bras(0.05, 0.10), 0)} envois par variante."),
        "Relief du nombre denvois par variante selon le taux de base et la hausse relative",
        "envois", tipv=lambda v: _num(10 ** v, 0))


@_fig("regarder")
def fig_regarder() -> str:
    r = mesurer.regarder()
    ks = list(mesurer.REGARDS)
    hi = max(r["naif"].values()) * 1.12
    b = _plate(310, "Regarder trop souvent",
               "Un test qu'on consulte chaque jour finit par « gagner »",
               f"{r['experiences']} tests A/A, {_num(r['n_bras'], 0)} envois par bras")
    p = Panel(b, 64, HEAD + 18, W - 78, 160).domain(1, 100, 0, hi, xlog=True)
    p.frame()
    p.grid_y(_graduations(0, hi, 5), fmt=lambda v: _pct(v, 0), label="faux positifs")
    p.grid_x(ks, fmt=lambda v: _num(v, 0), label="nombre de regards sur le test")
    p.hline(0.05, cls="lvl")
    p.path([(k, r["naif"][k]) for k in ks], "s2")
    p.path([(k, r["msprt"][k]) for k in ks], "s1")
    for k in ks:
        p.dot(k, r["naif"][k], "s2", tip=f"{k} regards, test classique : {_pct(r['naif'][k])}", r=3)
        p.dot(k, r["msprt"][k], "s1", tip=f"{k} regards, test toujours valide : {_pct(r['msprt'][k], 2)}", r=3)
    p.label(100, r["naif"][100], f"{_pct(r['naif'][100], 0)}", dx=-30, dy=-8, cls="tk halo")
    p.label(30, 0.05, "5 % promis", dy=-5, cls="tk halo")
    b.legend(0, 274, [("s2", "test classique, arrêt au premier p < 0,05"),
                      ("s1", "test toujours valide (mSPRT)")], step=330, kind="line")
    _source(b, (f"Deux variantes identiques, aucun effet. Le test classique arrêté dès que "
                f"p < 0,05 promet 5 % de fausses victoires ; regardé cent fois, il en donne "
                f"{_pct(r['naif'][100])}. Le test toujours valide reste à {_pct(max(r['msprt'].values()), 2)} "
                f"au plus, quel que soit le nombre de regards, au prix d'une puissance moindre."))
    return b.render("Taux de faux positifs selon le nombre de regards sur un test A A, test "
                    "classique et test toujours valide")


@_fig("gagnant")
def fig_gagnant() -> str:
    z = mesurer.surface_gagnant()
    return _relief(
        "La malédiction du gagnant", "Le meilleur de vingt variantes nulles",
        "hauteur : hausse mesurée sans aucun effet", z,
        [f"{k} var." for k in mesurer.VARIANTES],
        [_num(n, 0) if n < 1000 else _num(n / 1000, 0) + " k" for n in mesurer.ENVOIS],
        lambda v: "+" + _pct(v, 0), "+{v:.1f} % affichés",
        ("Arête gauche : nombre de variantes comparées. Arête droite : envois par variante, à "
         "5 % d'achat de base. Aucune variante n'a d'effet ; la hauteur est la hausse relative "
         "qu'affiche, en moyenne, celle qui arrive en tête. Elle se lit comme une découverte."),
        "Relief de la hausse mesuree de la meilleure variante sans effet selon le nombre de "
        "variantes et les envois", "hausse affichée", tipv=lambda v: v * 100)


@_fig("paie")
def fig_paie() -> str:
    d = mesurer.paie()
    z = [list(reversed(l)) for l in d["puissance"]]
    return _relief(
        "Le jour de paie d'un fan", "Il se lit, mais tard et seulement s'il est fort",
        "hauteur : part des paies détectées", z,
        [f"×{_num(1 + a, 1)}" for a in mesurer.AMPLITUDES],
        [f"{n} achats" for n in reversed(mesurer.ACHATS)],
        lambda v: _pct(v, 0), "{v:.0f} % détectées",
        (f"Arête gauche : intensité d'achat dans les trois jours qui suivent la paie, rapportée "
         f"au reste du cycle de quatorze jours. Arête droite : achats observés en six mois. "
         f"Hauteur : part des fans dont la paie est détectée à moins de 5 % de faux positifs. "
         f"À dépense doublée, elle n'est détectée que dans {_pct(d['puissance'][mesurer.AMPLITUDES.index(1.0)][-1], 0)} "
         f"des cas même à 32 achats."),
        "Relief de la part des jours de paie detectes selon lintensite et le nombre dachats",
        "détectés", tipv=lambda v: v * 100, plafond=1.0)


@_fig("horloge")
def fig_horloge() -> str:
    d = mesurer.horloge()
    z = [list(reversed(l)) for l in reversed(d["erreur"])]
    return _relief(
        "L'heure d'un fan", "Vingt messages suffisent si son heure est nette",
        "hauteur : erreur médiane sur son heure", z,
        [f"κ {_num(k, 2)}" for k in reversed(mesurer.CONCENTRATIONS)],
        [f"{n} msg" for n in reversed(mesurer.MESSAGES)],
        lambda v: _num(v, 1) + " h", "{v:.2f} h d'erreur médiane",
        (f"Arête gauche : concentration de ses messages autour de son heure (κ de von Mises : "
         f"0,25 diffus, 4 très net). Arête droite : messages observés. Hauteur : erreur médiane "
         f"sur l'heure estimée, en heures. Pour un fan diffus, même {mesurer.MESSAGES[0]} messages "
         f"laissent {_num(d['erreur'][-1][0], 1)} h d'erreur."),
        "Relief de lerreur mediane sur lheure dun fan selon la concentration et le nombre de "
        "messages", "erreur")


@_fig("classement")
def fig_classement() -> str:
    reg = registre.par_id()
    items = [(i, z, n) for i, z, n in synthese.classement() if n is not None]
    sem = [(i, n / synthese.ENVOIS_SEMAINE) for i, _, n in items]
    lo, hi = 0.05, max(s for _, s in sem) * 1.6
    h = 22 * len(sem)
    b = _plate(h + 120, "Ce qu'une agence peut revérifier",
               "Le classement par semaines de test",
               f"base déclarée {_pct(synthese.P_AGENCE, 0)}, effet transposé à moitié")
    p = Panel(b, 190, HEAD + 16, W - 204, h).domain(lo, hi, -0.5, len(sem) - 0.5, xlog=True)
    p.frame()
    ticks = [t for t in (0.1, 0.5, 1, 5, 10, 50, 100, 500) if lo <= t <= hi]
    p.grid_x(ticks, fmt=lambda v: _num(v, 1 if v < 1 else 0), label="semaines à "
             f"{_num(synthese.ENVOIS_SEMAINE, 0)} envois par variante", rules=True)
    for k, (i, s) in enumerate(sem):
        y = len(sem) - 1 - k
        cls = _cls_verdict(synthese.verdict(i))
        p.hbar(y, lo, s, 11, cls + "f",
               tip=f"{i} {reg[i].enonce} : {_num(s, 1)} semaines")
        b.add(f'<text class="tk" x="{p.x - 6:.1f}" y="{p.sy(y) + 3:.1f}" '
              f'text-anchor="end">{i} {COURT[i]}</text>')
    _source(b, ("Pour chaque effet qui tient et s'exprime en taux : les semaines d'envois qu'il "
                "faudrait à une agence pour le revérifier sur ses propres fans, au risque de 5 % "
                "et à 80 % de puissance, si l'effet relatif mesuré ailleurs ne survit qu'à moitié "
                "et si un message groupé vend à 5 %. Les deux paramètres sont déclarés ; la "
                "surface du budget donne toutes les autres bases."))
    return b.render("Classement des effets etablis par semaines de test necessaires dans une "
                    "agence")


@lru_cache(maxsize=1)
def rendre() -> dict[str, str]:
    return {k: f() for k, f in FIGURES.items()}


if __name__ == "__main__":
    import sys
    from pathlib import Path
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/ofm-figures")
    out.mkdir(parents=True, exist_ok=True)
    for k, svg in rendre().items():
        (out / f"{k}.svg").write_text(svg, encoding="utf-8")
        print(k, len(svg))
