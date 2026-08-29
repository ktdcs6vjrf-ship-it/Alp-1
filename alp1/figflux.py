"""Les figures du flux d'ordres : footprint, profil TPO, budget d'information.

Trois couches que les deux premiers documents citaient sans les montrer. Le
module suit la règle du dépôt : aucune couleur en dur, tout passe par les
jetons de `figcss`, et chaque lecture est posée à côté de sa loi nulle.
"""

from __future__ import annotations

import math

from . import footprint as fp
from . import tpo as tp
from .figdisc import W, _num, _plate, _ramp, _source, _surface
from .figterm import Board, Panel, _esc

FIGURES: dict[str, object] = {}


# ---------------------------------------------------------------------------
# Le footprint, montré comme une plateforme le montre
# ---------------------------------------------------------------------------


def fig_footprint() -> str:
    """Trois barres en footprint, et ce que chacune donne à lire.

    Le footprint se lit en chiffres, pas en formes : à chaque niveau de prix,
    le volume exécuté au bid à gauche, à l'ask à droite. La figure garde cette
    présentation parce que c'est celle que l'opérateur a sous les yeux, et
    parce qu'une version « propre » en aplats perdrait ce qui fait la lecture
    — la comparaison de deux nombres voisins.

    Les trois barres sont **construites**, et chacune porte nettement une
    lecture. Sous chacune, le chiffre qui décide : le nombre de déséquilibres
    observés, et le nombre que sa propre loi nulle en attend.
    """
    kinds = (("neutre", "Barre neutre"),
             ("absorption", "Absorption"),
             ("desequilibre", "Déséquilibre acheteur"))
    barres = {k: fp.synthesise(k) for k, _ in kinds}
    lam = fp.IMPACT_PER_ROOT_VOLUME
    vmax = max(max(c.bid, c.ask) for b in barres.values() for c in b.cells)

    b = _plate(396, "Footprint",
               "Ce que le carnet laisse comme trace une fois exécuté",
               "bid à gauche · ask à droite")

    n = len(barres["neutre"].cells)
    haut, pas = 92.0, 21.0
    demi = 58.0                     # demi-largeur d'une colonne de barre
    for col, (cle, titre) in enumerate(kinds):
        barre = barres[cle]
        cx = 118.0 + col * 196.0
        b.add(f'<text class="hdr" x="{cx:.1f}" y="{haut - 26:.1f}" '
              f'text-anchor="middle">{_esc(titre)}</text>')
        b.add(f'<line class="hsep" x1="{cx - demi:.1f}" y1="{haut - 18:.1f}" '
              f'x2="{cx + demi:.1f}" y2="{haut - 18:.1f}"/>')
        desq = dict(fp.diagonal_imbalances(barre))
        for i in range(n - 1, -1, -1):
            cell = barre.cells[i]
            y = haut + (n - 1 - i) * pas
            # Les deux barres de volume, du centre vers l'extérieur. La rampe
            # code le volume du côté, jamais le signe : le signe est déjà
            # porté par le côté où la barre pousse.
            for signe, vol in ((-1, cell.bid), (+1, cell.ask)):
                lg = demi * 0.86 * vol / vmax
                x0 = cx if signe > 0 else cx - lg
                b.add(f'<rect class="{_ramp(0.18 + 0.72 * vol / vmax)}" '
                      f'x="{x0:.1f}" y="{y - 8:.1f}" width="{max(lg, 0.6):.1f}" '
                      f'height="14" opacity="0.30"/>')
            # `halo` cerne le chiffre de la couleur du fond : sans lui, les
            # chiffres de la colonne d'absorption se perdent dans leur barre.
            b.add(f'<text class="tk halo" x="{cx - 7:.1f}" y="{y + 3:.1f}" '
                  f'text-anchor="end">{cell.bid}</text>')
            b.add(f'<text class="tk halo" x="{cx + 7:.1f}" y="{y + 3:.1f}">'
                  f'{cell.ask}</text>')
            if cell.price in desq:
                cote = desq[cell.price]
                x0 = cx + 2 if cote == "acheteur" else cx - 34
                b.add(f'<rect class="frame" x="{x0:.1f}" y="{y - 9:.1f}" '
                      f'width="32" height="16" rx="2"/>')
            if col == 0:
                b.add(f'<text class="tk" x="{cx - demi - 8:.1f}" '
                      f'y="{y + 3:.1f}" text-anchor="end">'
                      f'{_num(cell.price, 2)}</text>')
        bas = haut + n * pas
        b.add(f'<line class="hsep" x1="{cx - demi:.1f}" y1="{bas - 6:.1f}" '
              f'x2="{cx + demi:.1f}" y2="{bas - 6:.1f}"/>')
        lignes = [
            f"volume {barre.volume}   Δ {barre.delta:+d}",
            f"z d'impact {_num(fp.absorption_z(barre, lam), 2)}",
            f"déséquilibres {len(desq)}, "
            f"attendus {_num(fp.expected_imbalances(barre), 2)}",
        ]
        for k, texte in enumerate(lignes):
            b.add(f'<text class="lg" x="{cx:.1f}" y="{bas + 10 + 13 * k:.1f}" '
                  f'text-anchor="middle">{_esc(texte)}</text>')

    b.annotation(0, bas + 56, "le déséquilibre compare l'ask d'un niveau au "
                              "bid du niveau du dessous, jamais du même niveau")
    _source(b, "Trois barres construites, à volumes et niveaux déclarés. À "
               "chaque niveau, le volume exécuté au bid à gauche et à l'ask à "
               "droite ; les cadres marquent un déséquilibre diagonal de trois "
               "pour un. La barre neutre en attend environ un de sa seule loi "
               "nulle : en relever un ne dit rien. L'absorption se lit au z "
               "d'impact, qui rapporte le déplacement au volume échangé — "
               "trois fois le volume de la barre neutre pour un déplacement "
               "nul.")
    return b.render("Trois barres en footprint : neutre, absorption et "
                    "déséquilibre acheteur, avec leurs lois nulles")


FIGURES["flowfootprint"] = fig_footprint


def _pourcent_court(v: float) -> str:
    """Une fréquence en pour-cent, sans zéro inutile ni notation savante.

    `%g` rendait « 1e-06 % », qui n'apprend rien et déborde sur l'intitulé
    d'axe. Les cinq décennies utiles s'écrivent à la main, en virgule
    française.
    """
    pct = 100.0 * v
    if pct >= 1.0:
        return _num(pct, 0) + " %"
    nd = max(1, int(round(-math.log10(pct))))
    return _num(pct, nd) + " %"


# ---------------------------------------------------------------------------
# Les deux lois nulles du footprint : le déséquilibre et l'épuisement
# ---------------------------------------------------------------------------


def fig_footprint_null() -> str:
    """Ce que les deux lectures valent contre leur bruit, et ce qui les limite.

    À gauche, la fréquence nulle d'un déséquilibre diagonal selon la taille de
    grappe. C'est la figure inconfortable de cette couche : la même barre est
    un événement à une chance sur mille ou une banalité à une sur dix, selon
    un paramètre — le nombre de contrats qu'un même participant fait passer
    d'un coup — que le flux agrégé ne donne pas.

    À droite, la loi nulle du rapport d'épuisement. Le volume au niveau
    extrême d'une excursion **s'effondre déjà** sous martingale, parce que le
    prix y passe peu de temps ; la médiane nulle vaut un et le quantile à cinq
    pour cent tombe à la moitié. « Le volume s'effondre au sommet » n'est donc
    pas une observation tant qu'on n'a pas dit à quel quantile.
    """
    clumps = (2, 4, 6, 8, 12, 16, 20, 28, 36, 48)
    series = ((3.0, "s1", "3 pour 1"), (4.0, "s3", "4 pour 1"))
    courbes = {r: [(c, fp.null_imbalance_probability(240, 240, r, 10, c))
                   for c in clumps] for r, _, _ in series}
    plat = [v for c in courbes.values() for _, v in c if v > 0]

    b = _plate(414, "Lois nulles du footprint",
               "Ce que les deux lectures valent contre leur bruit",
               "deux niveaux à 240 contrats")

    p1 = Panel(b, 92, 84, 232, 178, title="Déséquilibre diagonal",
               readout="fréquence sous martingale")
    # Plancher à un pour cent mille : sous ce niveau la lecture est de toute
    # façon impossible, et laisser le domaine descendre jusqu'au minimum
    # calculé donnait huit décennies dont six vides.
    ylo, yhi = 1e-5, max(plat) * 2.5
    p1.domain(clumps[0], clumps[-1], ylo, yhi, xlog=True, ylog=True)
    p1.frame()
    # Les décennies sont déduites du domaine et non écrites : posées à la
    # main, elles se tassaient toutes dans le quart haut du cadre.
    p1.grid_y([10.0 ** k for k in range(-5, 1) if ylo <= 10.0 ** k <= yhi],
              _pourcent_court, "fréquence nulle")
    p1.grid_x([2, 4, 8, 16, 32, 48], lambda v: f"{v:g}",
              "taille de grappe, en contrats")
    for r, cls, nom in series:
        pts = [(c, v) for c, v in courbes[r] if v > 0]
        p1.path(pts, cls, tip=f"{nom}")
        # Pas de libellé au bout des courbes : à droite elles se rejoignent et
        # deux libellés y tombaient l'un sur l'autre, à gauche elles sortent
        # par le plancher du domaine. La légende de pied fait l'identification.
    p1.vline(fp.CLUMP_DEFAULT, "lvl")
    p1.label(fp.CLUMP_DEFAULT, yhi / 2.6, "grappe déclarée", dx=-5, dy=0,
             anchor="end", cls="lg halo")

    loi = fp.null_exhaustion()
    ech = _echantillon_epuisement()
    p2 = Panel(b, 388, 84, 210, 178, title="Rapport d'épuisement",
               readout="loi nulle simulée")
    lo, hi = 0.0, max(2.4, max(ech) * 1.02)
    p2.domain(lo, hi, 0.0, 1.0)
    p2.frame()
    p2.grid_x([0, 0.5, 1.0, 1.5, 2.0], lambda v: _num(v, 1),
              "volume du niveau extrême / médiane")
    p2.grid_y([0.0, 0.5, 1.0], lambda v: _num(v, 1), "fréquence relative",
              side="right")
    _histogramme(p2, ech, 26, lo, hi)
    p2.vline(loi.q05, "lvl")
    p2.label(loi.q05, 0.92, "5 %", dx=-4, dy=0, anchor="end", cls="tk halo")
    observe = fp.exhaustion_ratio(fp.synthesise("epuisement"), +1)
    p2.vline(observe, "lvl strong")
    p2.label(observe, 0.34, "barre construite, " + _num(observe, 2), dx=7, dy=0,
             cls="dl halo")

    # Deux lignes et non une : la phrase entière fait plus de huit cents
    # pixels et débordait de la planche par la droite.
    b.annotation(0, 308, "la même barre est un événement à une chance sur "
                         "mille ou une banalité à une sur dix,")
    b.annotation(0, 322, "selon un paramètre que le flux agrégé ne donne pas")
    b.legend(0, 344, [("s1", "déséquilibre 3 pour 1"),
                      ("s3", "déséquilibre 4 pour 1")], step=250, kind="line")
    _source(b, "À gauche, la fréquence d'un déséquilibre diagonal sous "
               "martingale, en fonction du nombre de contrats qu'un même "
               "participant fait passer d'un coup. Si les contrats arrivaient "
               "un à un, un rapport de trois pour un sur deux niveaux à 240 "
               "exigerait plus de quinze écarts-types : jamais. Ce qui rend la "
               "lecture possible — et ce qui la limite — est que les contrats "
               "n'arrivent pas un à un. À droite, la loi nulle du rapport "
               "d'épuisement, simulée sur des excursions sans dérive : le "
               "volume s'effondre déjà au niveau extrême sans qu'aucune "
               "intention n'y soit.")
    return b.render("Fréquence nulle du déséquilibre diagonal selon la taille "
                    "de grappe, et loi nulle du rapport d épuisement")


def _echantillon_epuisement(draws: int = 1600) -> list[float]:
    """L'échantillon brut de la loi nulle d'épuisement, pour l'histogramme.

    `footprint.null_exhaustion` n'en rend que les résumés ; la figure a besoin
    de la forme. On refait le tirage à la même graine, ce qui garantit que
    l'histogramme et les quantiles tracés décrivent la même simulation.
    """
    from .mc import Rng
    rng = Rng(20260829)
    n_levels, volume = 9, 900
    out = []
    for _ in range(draws):
        compte = [0] * n_levels
        pos = n_levels // 2
        for _ in range(volume):
            compte[pos] += 1
            pos = min(max(pos + (1 if rng.uniform() < 0.5 else -1), 0),
                      n_levels - 1)
        tries = sorted(compte)
        med = tries[n_levels // 2]
        out.append(compte[-1] / med if med else 0.0)
    return out


def _histogramme(panel: Panel, echantillon: list[float], bins: int,
                 lo: float, hi: float, cls: str = "area ar1") -> None:
    """Un histogramme normalisé à hauteur un, posé sur le cadre.

    La hauteur est normalisée parce que le cadre porte une fréquence relative
    et rien d'autre : deux histogrammes de tailles différentes s'y comparent.
    """
    largeur = (hi - lo) / bins
    compte = [0] * bins
    for v in echantillon:
        k = int((v - lo) / largeur)
        if 0 <= k < bins:
            compte[k] += 1
    pic = max(compte) or 1
    for k, c in enumerate(compte):
        if not c:
            continue
        x0, x1 = lo + k * largeur, lo + (k + 1) * largeur
        panel.vbar(0.5 * (x0 + x1), 0.0, c / pic,
                   max(panel.sx(x1) - panel.sx(x0) - 1.0, 1.0), cls,
                   f"{100 * c / len(echantillon):.1f} % entre "
                   f"{x0:.2f} et {x1:.2f}")


FIGURES["flowfootnull"] = fig_footprint_null


def fig_footprint_surface() -> str:
    """La fréquence nulle du déséquilibre sur le plan (grappe × rapport).

    Les deux axes sont ceux que l'opérateur croit contrôler : le seuil de
    lecture qu'il se donne, et la taille de grappe qu'il suppose. Le premier
    est un choix, le second une hypothèse — et la surface montre que le second
    pèse plus lourd que le premier.

    Passer de trois pour un à cinq pour un divise la fréquence nulle par cinq.
    Passer d'une grappe de quatre à une grappe de quarante-huit la multiplie
    par plus de mille. **Le seuil que l'opérateur choisit ne décide presque
    rien devant l'hypothèse qu'il ne fait pas.**
    """
    clumps = (4, 8, 12, 20, 32, 48)
    ratios = (2.0, 2.5, 3.0, 4.0, 5.0)
    plancher = 1e-4
    z = [[math.log10(max(fp.null_imbalance_probability(240, 240, r, 10, c),
                         plancher))
          for r in ratios] for c in clumps]
    plat = [v for ligne in z for v in ligne]
    marge = (max(plat) - min(plat)) * 0.06
    zlo, zhi = min(plat) - marge, max(plat) + marge

    b = _plate(344, "Le seuil ne décide presque rien",
               "Fréquence nulle du déséquilibre sur ses deux axes",
               "hauteur : fréquence en échelle logarithmique")
    _surface(b, 314, 154, z, zlo, zhi, cx=32.0, cy=10.0, cz=142.0,
             row_labels=[f"{c}" for c in clumps],
             col_labels=[_num(r, 1) for r in ratios[:-1]]
                        + [_num(ratios[-1], 1) + " pour 1"],
             z_ticks=[(float(k), _pourcent_court(10.0 ** k))
                      for k in range(math.ceil(zlo), math.floor(zhi) + 1)],
             tip="fréquence nulle = 10^{v:.2f}", zero=zlo)
    b.annotation(0, 306, "arête gauche : la taille de grappe, une hypothèse. "
                         "arête droite : le seuil de lecture, un choix")
    _source(b, "Arête gauche : taille de grappe, en contrats. Arête droite : "
               "seuil de déséquilibre. La hauteur est la fréquence de la "
               "lecture sous martingale, en échelle logarithmique, plancher à "
               "un pour dix mille. Le long de l'arête du seuil la surface "
               "descend d'un facteur cinq ; le long de l'arête de la grappe "
               "elle monte d'un facteur mille. L'opérateur choisit le premier "
               "axe et suppose le second.")
    return b.render("Surface de la fréquence nulle du déséquilibre diagonal "
                    "selon la taille de grappe et le seuil de lecture")


FIGURES["flowfoot3d"] = fig_footprint_surface


# ---------------------------------------------------------------------------
# Le profil TPO, et les cinq lectures qu'il porte
# ---------------------------------------------------------------------------


def fig_tpo() -> str:
    """Un profil de marché, et ce que chacune de ses cinq lectures vaut.

    Le profil est construit sur une séance **sans dérive** : c'est délibéré. Un
    lecteur qui y reconnaît un POC, une aire de valeur, des tirages simples et
    une extension de séance y reconnaît des formes qu'aucune intention n'a
    produites. C'est la démonstration la plus courte du propos.

    Le pas de rangée est de trois points et non d'un tick. C'est la convention
    des plateformes sur un future indiciel, et elle n'est pas cosmétique : à
    un tick de vingt-cinq centièmes, une séance parcourt quatre cents rangées
    et le profil cesse d'être lisible. Le pas de rangée est donc un **choix de
    l'opérateur**, et la figure suivante montre qu'il décide de la rareté de
    ce qu'on y lit.

    Les deux cadres de droite mettent cinq lectures en regard de leur
    fréquence nulle. Trois sont l'état par défaut d'une marche découpée en
    tranches ; l'extrême pauvre est réellement rare — et le document le dit,
    parce que le dépôt n'a pas pour objet de tout démolir.
    """
    #: Pas de rangée du profil affiché, en points d'indice. Déclaré ici parce
    #: qu'il décide de tout ce que la figure montre.
    PAS_RANGEE = 3.0
    prof = tp.synthesise(tick=PAS_RANGEE)
    loi = tp.null_profile(tick=PAS_RANGEE, draws=500)
    va_bas, va_haut = prof.value_area()
    simples = set(prof.single_prints)
    etendue = prof.prices[-1] - prof.prices[0]
    largeur = (va_haut - va_bas) / etendue if etendue else 0.0

    b = _plate(430, "Profil TPO",
               "Le temps passé à chaque prix, et ce qu'on croit y lire",
               f"{prof.n_periods} périodes · rangée {_num(PAS_RANGEE, 0)} pt")

    # --- le profil lui-même, une lettre par période et par prix -----------
    n_max = max(prof.counts)
    p1 = Panel(b, 92, 90, 148, 244, title="La séance",
               readout="sans dérive")
    # Le domaine déborde d'une demi-rangée : calé sur les prix extrêmes, la
    # lettre du dernier niveau sortait par le haut du cadre.
    p1.domain(0, n_max, prof.prices[0] - PAS_RANGEE / 2,
              prof.prices[-1] + PAS_RANGEE / 2)
    p1.band_y(va_bas, va_haut, "wash")
    p1.frame()
    pas_prix = max(1, len(prof.prices) // 6)
    p1.grid_y([prof.prices[i] for i in range(0, len(prof.prices), pas_prix)],
              lambda v: _num(v, 0))
    # Deux graduations et non trois : la troisième venait toucher celle du
    # cadre voisin, et « 10 » suivi de « 0 % » se lisait « 100 % ».
    p1.grid_x([0, 5], lambda v: f"{v:g}", "périodes")
    for prix, periodes in zip(prof.prices, prof.periods):
        cls = "dl" if prix in simples else "tk"
        for k, periode in enumerate(sorted(periodes)):
            b.add(f'<text class="{cls}" x="{p1.sx(k + 0.12):.1f}" '
                  f'y="{p1.sy(prix) + 2.4:.1f}">'
                  f'{tp.LETTERS[periode]}</text>')
    p1.hline(prof.poc, "lvl strong")
    p1.label(float(n_max), prof.poc, "POC", dx=-3, dy=-9, anchor="end",
             cls="dl halo")

    # --- trois fréquences, contre leur loi nulle --------------------------
    ext_h, ext_b = prof.range_extension()
    freqs = (("extension de séance", ext_h or ext_b, loi.p_extension),
             ("extrême haut pauvre", prof.poor_high, loi.p_poor_high),
             ("extrême bas pauvre", prof.poor_low, loi.p_poor_low))
    p2 = Panel(b, 320, 90, 268, 104, title="Trois lectures, trois fréquences",
               readout="part des séances sans dérive")
    p2.domain(0.0, 1.06, -0.5, len(freqs) - 0.5)
    p2.frame()
    p2.grid_x([0.0, 0.25, 0.5, 0.75, 1.0], lambda v: f"{100 * v:.0f} %")
    for k, (nom, observe, nulle) in enumerate(freqs):
        y = len(freqs) - 1 - k
        p2.hbar(y, 0.0, nulle, 11.0, "s1f",
                f"{100 * nulle:.1f} % des séances sans dérive")
        p2.label(nulle, y, f"{100 * nulle:.0f} %", dx=5, dy=3, cls="dl halo")
        b.add(f'<text class="tk" x="{p2.x + 3:.1f}" '
              f'y="{p2.sy(y) - 9:.1f}">'
              f'{_esc(nom + (" — vue ici" if observe else ""))}</text>')

    # --- ce qui décide la rareté : la taille de rangée --------------------
    # Et non les deux grandeurs qu'un premier jet y mettait. À trois points de
    # rangée, une séance sans dérive ne produit presque aucun tirage simple et
    # son aire de valeur couvre exactement la largeur nulle : les deux
    # comparaisons ne montraient rien. Celle-ci montre le fait de la couche.
    rangees = (0.25, 1.0, 2.0, 3.0, 4.0)
    freq_rangee = [(t, tp.null_profile(390, 1.25, t, 220).p_poor_high)
                   for t in rangees]
    p3 = Panel(b, 320, 244, 268, 90,
               title="L'extrême pauvre selon la rangée",
               readout="part des séances sans dérive")
    p3.domain(0.0, max(v for _, v in freq_rangee) * 1.28,
              -0.5, len(rangees) - 0.5)
    p3.frame()
    p3.grid_x([0.0, 0.2, 0.4], lambda v: f"{100 * v:.0f} %",
              "fréquence nulle")
    for k, (t, freq) in enumerate(freq_rangee):
        y = len(rangees) - 1 - k
        cls = "s3f" if abs(t - PAS_RANGEE) < 1e-9 else "s1f"
        p3.hbar(y, 0.0, freq, 9.0, cls,
                f"rangée {t:g} pt — {100 * freq:.1f} % des séances")
        p3.label(freq, y, f"{_num(t, 2)} pt  {100 * freq:.0f} %", dx=5, dy=3,
                 cls="dl halo")

    b.annotation(0, 376, "cette séance n'a aucune dérive : tout ce qu'on y "
                         "reconnaît a été produit sans intention")
    _source(b, "Le profil d'une séance sans dérive, découpée en périodes de "
               "trente minutes, sur des rangées de trois points. Chaque lettre "
               "est une période ayant visité le prix ; les prix en clair sont "
               "des tirages simples. La bande est l'aire de valeur à "
               "soixante-dix pour cent, le trait plein le POC. L'extension de "
               "séance arrive dans la quasi-totalité des séances sans dérive : "
               "ce n'est pas un événement, c'est ce qui arrive quand rien "
               "n'arrive. L'extrême pauvre est rare — mais seulement à rangée "
               "fine : le cadre du bas montre que sa fréquence nulle passe "
               "d'une séance sur vingt à plus d'une sur trois entre un quart "
               "de point et trois points de rangée. La rareté de ce qu'on lit "
               "est donc décidée par un réglage d'affichage.")
    return b.render("Profil TPO d une séance sans dérive, avec la fréquence "
                    "nulle de cinq de ses lectures")


FIGURES["flowtpo"] = fig_tpo


def fig_tpo_surface() -> str:
    """La rareté de l'extrême pauvre sur le plan (pas de cotation × volatilité).

    C'est au profil ce que la taille de grappe est au footprint. Un extrême
    pauvre est rare quand la séance compte cent trente niveaux, banal quand
    elle en compte dix — et le nombre de niveaux ne dit rien du marché,
    seulement du pas de cotation rapporté à la volatilité de séance.

    La surface porte les deux ensemble parce qu'ils ne se lisent pas
    séparément : c'est leur **rapport** qui décide, et deux marchés très
    différents peuvent tomber au même endroit.
    """
    ticks = (0.25, 0.5, 1.0, 2.0, 4.0)
    sigmas = (0.6, 0.9, 1.25, 1.8, 2.5)
    z = [[tp.null_profile(390, s, t, 220).p_poor_high for s in sigmas]
         for t in ticks]
    plat = [v for ligne in z for v in ligne]
    marge = (max(plat) - min(plat)) * 0.06
    zlo, zhi = max(min(plat) - marge, 0.0), max(plat) + marge

    b = _plate(352, "Ce qui décide la rareté",
               "Fréquence nulle d'un extrême pauvre",
               "hauteur : part des séances sans dérive")
    _surface(b, 314, 152, z, zlo, zhi, cx=34.0, cy=11.0, cz=136.0,
             row_labels=[_num(t, 2) for t in ticks[:-1]]
                        + [_num(ticks[-1], 2) + " pt"],
             col_labels=[_num(s, 2) for s in sigmas[:-1]]
                        + [_num(sigmas[-1], 2) + " pt/min"],
             z_ticks=[(0.1 * k, f"{10 * k} %")
                      for k in range(0, int(zhi / 0.1) + 1)
                      if zlo <= 0.1 * k <= zhi],
             tip="{v:.1%} des séances", zero=zlo)
    b.annotation(0, 306, "arête gauche : le pas de cotation. arête droite : "
                         "la volatilité de séance. seul leur rapport décide")
    _source(b, "Arête gauche : pas de cotation, en points d'indice. Arête "
               "droite : volatilité par minute. La hauteur est la part des "
               "séances sans dérive qui produisent un extrême haut pauvre. "
               "Elle va d'une séance sur vingt à près d'une sur deux sur le "
               "cadre, sans qu'aucune propriété du marché ne change : seul le "
               "nombre de niveaux que la séance parcourt a changé. Une "
               "lecture d'extrême ne se transporte donc pas d'un instrument "
               "à l'autre sans que sa loi nulle soit refaite.")
    return b.render("Surface de la fréquence nulle d un extrême pauvre selon "
                    "le pas de cotation et la volatilité de séance")


FIGURES["flowtpo3d"] = fig_tpo_surface


# ---------------------------------------------------------------------------
# Le budget d'information : combien de bruit un trade supporte-t-il ?
# ---------------------------------------------------------------------------


def fig_information() -> str:
    """Ce qu'un trade exige d'information, et ce qu'il en coûte de le prouver.

    La question « le marché est-il du bruit à quatre-vingt-dix-neuf pour
    cent ? » n'a de réponse que rapportée à une géométrie. L'identité de Wald
    donne le taux de réussite qu'il faut atteindre ; la divergence de
    Kullback-Leibler en donne le prix en bits.

    Le résultat renverse la question. À la géométrie déclarée du document —
    une cible à vingt fois le risque, une friction qui mange cinquante-cinq
    pour cent du risque nominal — un trade exige **0,94 % d'un bit** par
    décision. Le marché peut donc être du bruit à 99,06 % et la stratégie
    tenir. En élargissant le stop, la friction tombe à onze pour cent du
    risque et l'exigence à 0,042 % d'un bit : le marché peut être du bruit à
    99,958 %.

    Le second cadre porte le prix de cette bonne nouvelle. Moins un trade
    exige d'information, plus il faut de décisions pour établir qu'il l'a :
    l'échantillon requis va de quelques centaines à plusieurs dizaines de
    milliers sur la même plage. **Rendre l'exigence petite la rend
    indémontrable.** C'est la tension que les trois documents mesurent, et
    elle se lit ici en une figure.
    """
    from .entropy import required_bits, trades_for_information

    fractions = tuple(0.03 + 0.02 * k for k in range(0, 27))   # c/L de 3 à 55 %
    series = ((5.0, "s3", "1:5"), (20.0, "s1", "1:20"), (50.0, "s2", "1:50"))
    bits = {rr: [(f, required_bits(rr, f).bits) for f in fractions]
            for rr, _, _ in series}
    plat = [v for c in bits.values() for _, v in c]

    b = _plate(420, "Budget d'information",
               "Combien de bruit un trade supporte-t-il ?",
               "friction rapportée au risque nominal")

    p1 = Panel(b, 108, 88, W - 172, 150, title="Information exigée par décision",
               readout="divergence de Kullback-Leibler")
    ylo, yhi = min(plat) / 2.4, max(plat) * 2.4
    p1.domain(fractions[0], fractions[-1], ylo, yhi, ylog=True)
    p1.frame()
    # `dx` écarté : une échelle en pour-cent à trois décimales déborde des
    # quarante-deux pixels par défaut et vient sur l'intitulé pivoté.
    p1.grid_y([10.0 ** k for k in range(-6, 0) if ylo <= 10.0 ** k <= yhi],
              _pourcent_court, "part d'un bit", dx=58.0)
    p1.grid_x([0.05, 0.11, 0.2, 0.3, 0.4, 0.55],
              lambda v: _num(100.0 * v, 0) + " %")
    for rr, cls, nom in series:
        p1.path(bits[rr], cls, tip=f"cible {nom}")
        # Au bord gauche : à droite les trois courbes se resserrent à moins
        # d'une demi-décennie, et « 1:20 » tombait sur « 1:50 ».
        p1.label(fractions[0], bits[rr][0][1], nom, dx=7, dy=-6, cls="dl halo")
    for f, nom in ((0.55, "géométrie déclarée"), (0.11, "stop à 0,050 %")):
        val = required_bits(20.0, f).bits
        p1.vline(f, "lvl")
        p1.dot(f, val, "s1", f"{nom} — {100 * val:.3f} % d'un bit", r=4.0)
        # Le repère de droite passe sous son point : au-dessus, il venait
        # sur le libellé de série, qui vit au même bord.
        p1.label(f, val, f"{nom} : {_num(100 * val, 3)} % d'un bit",
                 dx=-7 if f > 0.3 else 7, dy=23 if f > 0.3 else -9,
                 anchor="end" if f > 0.3 else "start", cls="dl halo")

    p2 = Panel(b, 108, 292, W - 172, 78,
               title="Ce qu'il en coûte de le prouver",
               readout="décisions requises")
    n = {rr: [(f, trades_for_information(required_bits(rr, f).bits))
              for f in fractions] for rr, _, _ in series}
    tous = [v for c in n.values() for _, v in c]
    p2.domain(fractions[0], fractions[-1], min(tous) / 2.4, max(tous) * 2.4,
              ylog=True)
    p2.frame()
    p2.grid_y([10.0 ** k for k in range(2, 7)
               if min(tous) / 2.4 <= 10.0 ** k <= max(tous) * 2.4],
              lambda v: _num(v, 0), "décisions", dx=58.0)
    p2.grid_x([0.05, 0.11, 0.2, 0.3, 0.4, 0.55],
              lambda v: _num(100.0 * v, 0) + " %",
              "friction rapportée au risque nominal, c/L")
    for k, (rr, cls, nom) in enumerate(series):
        p2.path(n[rr], cls, tip=f"cible {nom}")
        # Décalées le long de l'abscisse : au bord gauche les trois courbes
        # tiennent dans une demi-décennie et les libellés s'empilent.
        i = 1 + 5 * k
        p2.label(n[rr][i][0], n[rr][i][1], nom, dx=6, dy=-6, cls="dl halo")
    # Pas de légende de pied : les trois courbes sont nommées à leur bout dans
    # les deux cadres, et une légende de plus poussait la ligne de lecture
    # hors de la planche.
    _source(b, "Le taux de réussite d'équilibre sans friction vaut 1/(R+1) ; "
               "avec friction il vaut (1 + c/L)/(R+1). L'écart entre les deux "
               "est ce que le signal doit financer, et la divergence de "
               "Kullback-Leibler en donne le prix en bits — une borne "
               "inférieure, qu'aucune façon de dimensionner ne contourne. À la "
               "géométrie déclarée l'exigence vaut moins d'un centième de bit "
               "par décision : le marché peut être du bruit à plus de "
               "quatre-vingt-dix-neuf pour cent sans que cela empêche quoi que "
               "ce soit. Le cadre du bas donne le prix de cette bonne "
               "nouvelle.")
    return b.render("Information exigée par décision selon la friction "
                    "rapportée au risque, et échantillon requis pour la "
                    "détecter")


FIGURES["flowinfo"] = fig_information


def fig_information_surface() -> str:
    """Le budget d'information sur ses deux axes, la cible et la friction.

    Les deux grandeurs que l'opérateur fixe entièrement, et la seule chose
    qu'elles décident ensemble : la part d'un bit que sa décision doit porter.

    La surface descend dans les deux directions et elle descend vite. D'une
    cible à 1:5 et d'une friction à 55 % — le coin le plus exigeant — à une
    cible à 1:50 et une friction à 5 %, l'exigence est divisée par près de
    mille. Aucun signal n'est en jeu : seules la géométrie et l'exécution.
    """
    from .entropy import required_bits

    cibles = (5.0, 10.0, 20.0, 30.0, 50.0)
    frictions = (0.05, 0.11, 0.20, 0.35, 0.55)
    z = [[math.log10(required_bits(rr, f).bits) for f in frictions]
         for rr in cibles]
    plat = [v for ligne in z for v in ligne]
    marge = (max(plat) - min(plat)) * 0.06
    zlo, zhi = min(plat) - marge, max(plat) + marge

    b = _plate(352, "Budget d'information, sur deux axes",
               "Ce que la géométrie exige du signal, en bits",
               "hauteur : part d'un bit, échelle logarithmique")
    _surface(b, 314, 152, z, zlo, zhi, cx=34.0, cy=11.0, cz=138.0,
             row_labels=[f"1:{rr:g}" for rr in cibles],
             col_labels=[_num(100 * f, 0) for f in frictions[:-1]]
                        + [_num(100 * frictions[-1], 0) + " % de c/L"],
             z_ticks=[(float(k), _num(100.0 * 10.0 ** k,
                                      max(0, -int(k) - 1)) + " %")
                      for k in range(math.ceil(zlo), math.floor(zhi) + 1)],
             tip="10^{v:.2f} bit par décision", zero=zlo)
    b.annotation(0, 306, "arête gauche : la cible, en multiples du risque. "
                         "arête droite : la friction rapportée au risque")
    _source(b, "Arête gauche : ratio gain/risque visé. Arête droite : friction "
               "rapportée au risque nominal. La hauteur est l'information "
               "minimale qu'une décision doit porter pour que la géométrie "
               "soit rentable, en part d'un bit et en échelle logarithmique. "
               "Elle couvre trois ordres de grandeur sur le cadre, sans "
               "qu'aucun signal n'entre dans le calcul : la géométrie et "
               "l'exécution décident seules de ce que le marché doit fournir.")
    return b.render("Surface de l information exigée par décision selon la "
                    "cible et la friction rapportée au risque")


FIGURES["flowinfo3d"] = fig_information_surface


def render_all() -> dict[str, str]:
    """Toutes les figures du module, indexées par clé de gabarit."""
    return {nom: fabrique() for nom, fabrique in FIGURES.items()}


def main() -> None:
    for nom, svg in render_all().items():
        print(f"{nom:16} {len(svg):7d} octets")
