"""Les figures du catalogue : la situation, puis la suite.

Chaque lecture du catalogue reçoit ici deux choses qu'aucune des deux premiers
documents ne lui donnait : **un exemple**, dessiné comme une plateforme le
dessinerait, et **la suite du prix**, mesurée sur l'horizon de la lecture.

Le point qui décide de tout, et qu'il faut lire avant les figures : *tous les
exemples sont tirés de séances sans dérive*. Le motif y est reconnu par le
détecteur du module `concepts`, sur un prix dont on sait qu'il ne contient
rien. Une figure de ce module ne montre donc jamais « une absorption qui a
marché » — elle montre à quoi ressemble une absorption quand il n'y a rien à
lire, ce qui est la seule illustration honnête qu'on puisse produire sans
données de marché.

Aucune couleur n'est écrite : les planches posent des classes et `figcss.py`
décide.
"""

from __future__ import annotations

import math

from . import concepts as C
from . import footprint as fp
from . import tpo as tp
from . import vprofile
from .figdisc import W, _plate, _ramp, _source, _surface
from .figterm import Board, Panel, _esc, _num

FIGURES: dict[str, object] = {}

#: Hauteur d'une planche à deux rangées de cadres. Les planches de situation la
#: partagent, ce qui donne au chapitre un rythme régulier.
H_SITUATION = 430.0


# ---------------------------------------------------------------------------
# Bougies
# ---------------------------------------------------------------------------


def _bougies(chemin: tuple[float, ...], debut: int, fin: int,
             pas: int) -> list[tuple[float, float, float, float, float]]:
    """Agrège un chemin à la minute en bougies de `pas` minutes.

    Rendu `(t, ouverture, haut, bas, clôture)`, `t` étant l'indice de la bougie
    et non la minute : c'est ce qui permet de poser les bougies à intervalle
    régulier quel que soit le pas.
    """
    out = []
    for k, i in enumerate(range(debut, fin - pas + 1, pas)):
        tranche = chemin[i:i + pas + 1]
        if len(tranche) < 2:
            break
        out.append((float(k), tranche[0], max(tranche), min(tranche),
                    tranche[-1]))
    return out


def _tracer_bougies(p: Panel, bougies, largeur: float = 0.62) -> None:
    """Dessine les bougies dans un cadre déjà mis à l'échelle.

    Le corps est un rectangle, la mèche un trait. La classe suit le sens de
    la bougie — c'est la seule information que la couleur porte ici, et elle
    est binaire, donc légitimement catégorielle.
    """
    for t, o, h, b, c in bougies:
        cls = "s1f" if c >= o else "negf"
        ln = "s1" if c >= o else "neg"
        x = p.sx(t)
        y0, y1 = p.sy(h), p.sy(b)
        p.board.add(f'<line class="ln {ln}" x1="{x:.2f}" y1="{y0:.2f}" '
                    f'x2="{x:.2f}" y2="{y1:.2f}" stroke-width="1"/>')
        haut, bas = max(o, c), min(o, c)
        yh, yb = p.sy(haut), p.sy(bas)
        demi = 0.5 * largeur * p.w / max(len(bougies), 1)
        p.board.add(f'<rect class="{cls}" x="{x - demi:.2f}" y="{yh:.2f}" '
                    f'width="{2 * demi:.2f}" '
                    f'height="{max(yb - yh, 1.0):.2f}"/>')


def _cadre_bougies(b: Board, x, y, w, h, titre, readout, bougies,
                   marge: float = 0.10, surligne=None,
                   etendue=None) -> Panel:
    """Ouvre un cadre, y met les bougies, et rend le cadre pour les surcharges.

    `surligne` est peint **avant** les bougies : une bande posée après les
    recouvrirait, et le cadre montrerait alors une zone vide là où se trouve
    précisément ce qu'il faut regarder.
    """
    hauts = [c[2] for c in bougies]
    bas = [c[3] for c in bougies]
    lo, hi = (min(bas), max(hauts)) if etendue is None else etendue
    tampon = marge * (hi - lo or 1.0)
    p = Panel(b, x, y, w, h, titre, readout)
    p.domain(-0.6, len(bougies) - 0.4, lo - tampon, hi + tampon)
    p.frame()
    pas_y = _pas(lo - tampon, hi + tampon)
    p.grid_y([v for v in _ticks(lo - tampon, hi + tampon, pas_y)],
             fmt=lambda v: _num(v, 1))
    if surligne is not None:
        p.band_x(*surligne)
    _tracer_bougies(p, bougies)
    return p


def _pas(lo: float, hi: float) -> float:
    """Un pas de graduation rond, quatre à six graduations sur l'étendue."""
    brut = (hi - lo) / 5.0
    exposant = math.floor(math.log10(brut)) if brut > 0 else 0
    base = 10.0 ** exposant
    for m in (1.0, 2.0, 2.5, 5.0, 10.0):
        if brut <= m * base:
            return m * base
    return 10.0 * base


def _ticks(lo: float, hi: float, pas: float) -> list[float]:
    depart = math.ceil(lo / pas) * pas
    out, v = [], depart
    while v <= hi + 1e-9:
        out.append(round(v, 6))
        v += pas
    return out


# ---------------------------------------------------------------------------
# Trouver un exemple : une séance sans dérive où le motif se produit
# ---------------------------------------------------------------------------


def _exemple(cle: str) -> tuple[tuple[float, ...], int]:
    """La première séance sans dérive où le détecteur de `cle` se déclenche.

    Rendu la séance et la minute de l'événement. Rien n'est choisi à la main :
    le détecteur est celui du catalogue, la séance est la première qui
    convient dans l'ordre de la graine.
    """
    for chemin in C._seances():
        i = _instant(cle, chemin)
        if i is not None:
            return chemin, i
    raise RuntimeError(f"aucun exemple pour {cle}")


def _instant(cle: str, chemin: tuple[float, ...]) -> int | None:
    """La minute du premier événement de `cle` dans une séance, ou rien."""
    demi = len(chemin) // 2
    if cle == "vwap":
        somme = carre = 0.0
        for i, x in enumerate(chemin):
            somme += x
            carre += x * x
            n = i + 1
            moy = somme / n
            sig = math.sqrt(max(carre / n - moy * moy, 0.0))
            if n >= 60 and sig > 0 and abs(x - moy) >= 2.0 * sig and i > 90:
                return i
        return None
    if cle in ("lvn", "poc"):
        profil = vprofile.from_path(chemin[:demi], step=1.0)
        cible = profil.poc if cle == "poc" else None
        if cible is None:
            noeuds = profil.lvn(prominence=0.05)
            if not noeuds:
                return None
            cible = noeuds[len(noeuds) // 2]
        for i in range(demi, len(chemin) - 60):
            if abs(chemin[i] - cible) <= 1.0:
                return i
        return None
    if cle == "retest":
        niveau = max(chemin[:60])
        parti = False
        for i in range(60, len(chemin) - 120):
            if not parti and chemin[i] < niveau - 3.0:
                parti = True
            elif parti and chemin[i] >= niveau - 0.5:
                return i
        return None
    if cle == "meche":
        return len(chemin) - 1
    return demi


def _niveau_exemple(cle: str, chemin: tuple[float, ...]) -> float:
    """Le niveau que la lecture regarde, sur la séance d'exemple."""
    demi = len(chemin) // 2
    if cle == "poc":
        return vprofile.from_path(chemin[:demi], step=1.0).poc
    if cle == "lvn":
        noeuds = vprofile.from_path(chemin[:demi], step=1.0).lvn(prominence=0.05)
        return noeuds[len(noeuds) // 2] if noeuds else 0.0
    if cle == "retest":
        return max(chemin[:60])
    return 0.0


# ---------------------------------------------------------------------------
# L'éventail : ce que le prix fait après le signal
# ---------------------------------------------------------------------------


#: Retrait à droite des cadres d'éventail. Leur dernière graduation d'abscisse
#: est centrée sur le bord du cadre&nbsp;; sans ce retrait, « 60 min » débordait
#: du SVG de sa demi-largeur.
RETRAIT_EVENTAIL = 22.0


def _eventail(b: Board, x, y, w, h, horizon: float, titre: str,
              legendes: bool = True) -> Panel:
    """Le cône des issues, sans dérive puis à la dérive haute du plausible.

    Deux enveloppes superposées, chacune du dixième au neuvième décile, et
    leurs médianes. La superposition est le propos : à cinq minutes les deux
    cônes se confondent, à trois séances ils se séparent — et c'est la même
    dérive dans les deux cas.
    """
    haute = C.derive_haute()
    nul = C.eventail(horizon, 0.0)
    der = C.eventail(horizon, haute)
    n = len(nul) - 1
    ts = [k * horizon / n for k in range(n + 1)]

    lo = min(min(c[0] for c in nul), min(c[0] for c in der))
    hi = max(max(c[4] for c in nul), max(c[4] for c in der))
    marge = 0.12 * (hi - lo)

    p = Panel(b, x, y, w - RETRAIT_EVENTAIL, h, titre,
              "cône du 1er au 9e décile")
    p.domain(0.0, horizon, lo - marge, hi + marge)
    p.frame()
    p.grid_y(_ticks(lo - marge, hi + marge, _pas(lo - marge, hi + marge)),
             fmt=lambda v: _num(v, 0))
    if horizon < 120:
        unite, div, nd, mot = " min", 1.0, 0, "minutes"
    elif horizon < 390:
        unite, div, nd, mot = " h", 60.0, 1, "heures"
    else:
        unite, div, nd, mot = "", 390.0, 1, "séances"
    p.grid_x([0.0, horizon / 2.0, horizon],
             fmt=lambda v: _num(v / div, nd) + unite,
             label=mot + " après le signal")

    # Le cône sous dérive est peint, celui sans dérive est tracé : superposés,
    # deux aplats ne laisseraient voir que celui du dessus, et c'est justement
    # leur recouvrement qui est le propos.
    haut = [(t, c[4]) for t, c in zip(ts, der)]
    bas = [(t, c[0]) for t, c in zip(ts, der)]
    p.board.add(_polygone(p, haut + bas[::-1], "area ar1"))
    p.path([(t, c[4]) for t, c in zip(ts, nul)], "s3", dash="4 3")
    p.path([(t, c[0]) for t, c in zip(ts, nul)], "s3", dash="4 3")
    p.path([(t, c[2]) for t, c in zip(ts, der)], "s1")
    p.hline(0.0)
    if legendes:
        b.legend(x, y + h + 38.0,
                 [("s3", "déciles sans dérive"),
                  ("s1", "médiane à " + _num(haute, 1) + " pt/h")],
                 step=0.5 * w, kind="line")
    return p


def _polygone(p: Panel, pts, cls: str) -> str:
    """Un polygone fermé en coordonnées de données, découpé au cadre."""
    xlo, xhi = sorted((p.x0, p.x1))
    ylo, yhi = sorted((p.y0, p.y1))
    d = []
    for i, (x, y) in enumerate(pts):
        x = min(max(x, xlo), xhi)
        y = min(max(y, ylo), yhi)
        d.append(("M" if i == 0 else "L") + f"{p.sx(x):.2f},{p.sy(y):.2f}")
    return f'<path class="{cls}" opacity="0.30" d="{" ".join(d)} Z"/>'


# ---------------------------------------------------------------------------
# Figure — le flux : absorption, épuisement, déséquilibre
# ---------------------------------------------------------------------------

#: Marges de planche. La gauche loge les graduations d'ordonnée et l'intitulé
#: pivoté ; sans elle, un cadre posé à l'abscisse zéro rejette ses graduations
#: hors du SVG, où elles sont tracées mais invisibles.
MARGE_G = 62.0
MARGE_D = 12.0


def _utile() -> float:
    return W - MARGE_G - MARGE_D


def fig_flux() -> str:
    """Les trois lectures de la barre, et ce qu'elles annoncent.

    Rangée du haut : la situation, en bougies d'une minute, la barre lue
    encadrée. Sous chaque cadre, le détail chiffré de la barre. Rangée du
    bas : le cône des issues sur les cinq minutes qui suivent, commun aux
    trois puisque leur horizon l'est.
    """
    lam = fp.IMPACT_PER_ROOT_VOLUME
    kinds = (("absorption", "Absorption", "absorption"),
             ("epuisement", "Épuisement", "epuisement"),
             ("desequilibre", "Déséquilibre", "desequilibre"))

    b = _plate(520.0, "Catalogue · le flux",
               "Trois lectures de la barre, sur un prix sans dérive",
               "bougies d'une minute")

    chemin, i0 = _exemple("absorption")
    ecart = 30.0
    lw = (_utile() - 2 * ecart) / 3.0
    for col, (cle, titre, sy) in enumerate(kinds):
        x = MARGE_G + col * (lw + ecart)
        deb = max(0, i0 + col * 27 - 14)
        bougies = _bougies(chemin, deb, deb + 25, 1)
        e = C.exigence(cle)
        p = _cadre_bougies(b, x, 86.0, lw, 118.0, titre,
                           _num(100.0 * C.frequence_nulle(cle), 1) + " %",
                           bougies, surligne=(11.5, 16.5))
        p.grid_x([1.0, 12.0, len(bougies) - 2.0],
                 fmt=lambda v: _num(v - 12.0, 0), label="minutes")
        barre = fp.synthesise(sy)
        desq = fp.diagonal_imbalances(barre)
        lignes = [
            f"z d'impact {_num(fp.absorption_z(barre, lam), 2)}",
            f"déséquilibres {len(desq)}, attendus "
            f"{_num(fp.expected_imbalances(barre), 2)}",
            f"une fois sur {_num(1.0 / C.frequence_nulle(cle), 0)} sans dérive",
            f"établie en {C._ans(e.annees)}",
        ]
        for k, texte in enumerate(lignes):
            cls = "tk" if k == 3 else "lg"
            b.add(f'<text class="{cls}" x="{x:.1f}" y="{250.0 + 13 * k:.1f}">'
                  f'{_esc(texte)}</text>')

    _eventail(b, MARGE_G, 342.0, _utile(), 116.0, 5.0,
              "Les cinq minutes qui suivent")

    _source(b, "Les trois situations sont extraites d'une même séance "
               "simulée sans la moindre dérive : le motif s'y produit parce que le "
               "bruit le produit, et non parce qu'une information l'a causé. "
               "La bande grise marque la barre lue ; le chiffre en tête de "
               "cadre est la fréquence du motif sous cette absence de dérive, "
               "et le détail chiffré vient des barres construites du module de "
               "footprint. Le cône du bas est commun aux trois, leur horizon "
               "étant le même : sur cinq minutes, la dérive la plus forte que "
               "le domaine plausible autorise déplace la médiane d'un quart "
               "de point, quand l'enveloppe des déciles en fait sept.")
    return b.render("Trois lectures de footprint sur une séance sans dérive, "
                    "et le cône des issues à cinq minutes")


FIGURES["catflux"] = fig_flux


# ---------------------------------------------------------------------------
# Figure — le prix-volume : nœud de faible volume et retour au point de contrôle
# ---------------------------------------------------------------------------


def _profil_lateral(p: Panel, chemin, jusqu_a: int, part: float = 0.26,
                    pas: float = 1.0) -> vprofile.Profile:
    """Pose le profil de volume contre le bord droit du cadre.

    Les barres poussent vers la gauche depuis le bord : c'est la présentation
    d'usage, et elle laisse le tracé de prix lisible parce que les deux
    n'occupent pas la même bande verticale.
    """
    profil = vprofile.from_path(chemin[:jusqu_a], step=pas)
    vmax = max(profil.volumes) or 1.0
    largeur = part * (p.x1 - p.x0)
    for prix, vol in zip(profil.prices, profil.volumes):
        if vol <= 0 or not (p.y0 <= prix <= p.y1):
            continue
        lg = largeur * vol / vmax
        p.board.add(f'<g opacity="0.55">')
        p.hbar(prix, p.x1, p.x1 - lg, 4.0, _ramp(0.25 + 0.6 * vol / vmax))
        p.board.add('</g>')
    return profil


def fig_profil() -> str:
    """Le nœud de faible volume et le retour au point de contrôle.

    Deux lectures de la même construction — l'histogramme du temps passé par
    prix — et deux attentes opposées : traverser vite là où personne n'a
    traité, revenir là où tout le monde a traité.
    """
    b = _plate(524.0, "Catalogue · le prix-volume",
               "Ce que l'histogramme du temps passé permet d'espérer",
               "bougies de cinq minutes")

    ecart = 40.0
    lw = (_utile() - ecart) / 2.0
    for col, (cle, titre) in enumerate((("lvn", "Nœud de faible volume"),
                                        ("poc", "Retour au point de contrôle"))):
        chemin, i0 = _exemple(cle)
        niveau = _niveau_exemple(cle, chemin)
        x = MARGE_G + col * (lw + ecart)
        bougies = _bougies(chemin, 0, 390, 5)
        p = _cadre_bougies(b, x, 86.0, lw, 150.0, titre,
                           _num(100.0 * C.frequence_nulle(cle), 1) + " %",
                           bougies,
                           surligne=(i0 / 5.0 - 1.0, i0 / 5.0 + 1.0))
        _profil_lateral(p, chemin, len(chemin) // 2)
        p.hline(niveau, "lvl strong")
        p.tag(niveau, "POC" if cle == "poc" else "LVN", side="left")
        p.grid_x([0.0, 39.0, 77.0], fmt=lambda v: _num(v * 5.0 / 60.0, 1) + " h",
                 label="heures de séance")
        e = C.exigence(cle)
        lignes = [
            f"occasions par séance {_num(C.occasions(cle), 1)}",
            f"une fois sur {_num(1.0 / C.frequence_nulle(cle), 1)} sans dérive",
            f"µ* {_num(e.derive_requise, 3)} pt/h · établie en "
            f"{C._ans(e.annees)}",
        ]
        for k, texte in enumerate(lignes):
            b.add(f'<text class="lg" x="{x:.1f}" y="{280.0 + 13 * k:.1f}">'
                  f'{_esc(texte)}</text>')

    _eventail(b, MARGE_G, 350.0, _utile(), 116.0, 60.0,
              "L'heure qui suit, pour les deux lectures")

    _source(b, "Le profil de la demi-séance est posé contre le bord droit de "
               "chaque cadre ; le niveau lu en est tiré, jamais choisi. À "
               "gauche, le nœud de faible volume est traversé sept fois sur dix "
               "par le seul bruit — la lecture annonce donc ce qui se "
               "produit presque toujours. À droite, le prix revient au point "
               "de contrôle avant la clôture dans près de deux séances sur "
               "trois, également sans qu'aucune dérive n'y soit pour rien. Le "
               "cône du bas vaut pour les deux : sur une heure, la dérive "
               "haute du domaine plausible déplace la médiane de trois points "
               "pour une enveloppe de vingt-quatre.")
    return b.render("Nœud de faible volume et retour au point de contrôle sur "
                    "séances sans dérive, avec le cône des issues à une heure")


FIGURES["catprofil"] = fig_profil


# ---------------------------------------------------------------------------
# Figure — la bande VWAP et la zone d'entrée optimale
# ---------------------------------------------------------------------------


def _bandes_vwap(p: Panel, chemin, pas: int) -> None:
    """Trace le VWAP courant et ses deux premières bandes d'écart-type."""
    somme = carre = 0.0
    vwap, hi1, lo1, hi2, lo2 = [], [], [], [], []
    for i, x in enumerate(chemin):
        somme += x
        carre += x * x
        n = i + 1
        moy = somme / n
        sig = math.sqrt(max(carre / n - moy * moy, 0.0))
        if i % pas or n < 30:
            continue
        t = i / pas
        vwap.append((t, moy))
        hi1.append((t, moy + sig))
        lo1.append((t, moy - sig))
        hi2.append((t, moy + 2 * sig))
        lo2.append((t, moy - 2 * sig))
    p.path(vwap, "s2")
    for serie in (hi1, lo1):
        p.path(serie, "s3", dash="3 3")
    for serie in (hi2, lo2):
        p.path(serie, "s3")


def fig_vwap() -> str:
    """La bande VWAP et la zone d'entrée optimale, côte à côte.

    Les deux lectures ont la même forme logique : un niveau construit sur le
    passé, et une attente de retour vers lui. Elles diffèrent par l'horizon,
    donc par le nombre d'occasions, donc par leur prouvabilité.
    """
    b = _plate(524.0, "Catalogue · les niveaux construits",
               "Un repère bâti sur le passé, et l'attente d'un retour",
               "bougies de cinq minutes")

    ecart = 40.0
    lw = (_utile() - ecart) / 2.0

    chemin, i0 = _exemple("vwap")
    bougies = _bougies(chemin, 0, 390, 5)
    p = _cadre_bougies(b, MARGE_G, 86.0, lw, 150.0, "Bande VWAP",
                       _num(100.0 * C.frequence_nulle("vwap"), 1) + " %",
                       bougies, surligne=(i0 / 5.0 - 1.0, i0 / 5.0 + 1.0))
    _bandes_vwap(p, chemin, 5)
    p.grid_x([0.0, 39.0, 77.0], fmt=lambda v: _num(v * 5.0 / 60.0, 1) + " h",
             label="heures de séance")

    # La zone d'entrée optimale, sur la jambe la plus ample de la séance.
    debut, fin = _jambe(chemin)
    x2 = MARGE_G + lw + ecart
    bougies2 = _bougies(chemin, max(0, debut - 20), min(390, fin + 60), 5)
    p2 = _cadre_bougies(b, x2, 86.0, lw, 150.0, "Zone d'entrée optimale",
                        _num(100.0 * C.frequence_nulle("ote"), 1) + " %",
                        bougies2)
    bas, haut = min(chemin[debut:fin]), max(chemin[debut:fin])
    p2.band_y(haut - 0.79 * (haut - bas), haut - 0.618 * (haut - bas))
    for r, lab in ((0.618, "0,618"), (0.79, "0,79")):
        niveau = haut - r * (haut - bas)
        p2.hline(niveau)
        p2.tag(niveau, lab, side="left")
    p2.grid_x([0.0, 12.0, 24.0, 36.0],
              fmt=lambda v: _num(v * 5.0, 0), label="minutes")

    for col, cle in enumerate(("vwap", "ote")):
        e = C.exigence(cle)
        x = MARGE_G + col * (lw + ecart)
        lignes = [
            f"occasions par séance {_num(C.occasions(cle), 1)}",
            f"une fois sur {_num(1.0 / C.frequence_nulle(cle), 1)} sans dérive",
            f"µ* {_num(e.derive_requise, 3)} pt/h · établie en "
            f"{C._ans(e.annees)}",
        ]
        for k, texte in enumerate(lignes):
            b.add(f'<text class="lg" x="{x:.1f}" y="{280.0 + 13 * k:.1f}">'
                  f'{_esc(texte)}</text>')

    _eventail(b, MARGE_G, 350.0, _utile(), 116.0, 45.0,
              "Les trois quarts d'heure qui suivent")

    _source(b, "À gauche, le VWAP de séance et ses deux premières bandes "
               "d'écart-type, recalculés à chaque bougie ; la bande grise "
               "marque la touche de la deuxième bande. À droite, la jambe la "
               "plus ample de la même séance et la zone comprise entre ses "
               "retracements de 61,8 % et 79 %. Les deux repères sont "
               "construits sur le passé du prix et rien d'autre — c'est ce "
               "qui les rend calculables, et c'est aussi ce qui interdit "
               "qu'ils portent une information que le passé du prix ne "
               "contient pas.")
    return b.render("Bande VWAP et zone dite optimale sur une séance sans "
                    "dérive, avec le cône des issues à quarante-cinq minutes")


FIGURES["catvwap"] = fig_vwap


def _jambe(chemin) -> tuple[int, int]:
    """La jambe la plus ample de la séance, par balayage des extrêmes."""
    i_bas = min(range(len(chemin)), key=lambda i: chemin[i])
    i_haut = max(range(len(chemin)), key=lambda i: chemin[i])
    return (i_bas, i_haut) if i_bas < i_haut else (i_haut, i_bas)


# ---------------------------------------------------------------------------
# Figure — la structure : retest, mèche, plus haut plus haut
# ---------------------------------------------------------------------------


def _multi(n: int) -> tuple[float, ...]:
    """`n` séances sans dérive mises bout à bout, sans rupture de niveau.

    Chaque séance reprend au niveau où la précédente s'est arrêtée. Le chemin
    obtenu reste une marche sans dérive — recoller des marches indépendantes
    n'en fabrique pas une.
    """
    out: list[float] = [0.0]
    for chemin in C._seances()[:n]:
        base = out[-1]
        out.extend(base + x for x in chemin[1:])
    return tuple(out)


def fig_structure() -> str:
    """Les trois lectures de forme, du retest à la structure de Dow.

    Elles partagent une famille et rien d'autre : leurs horizons vont de deux
    heures à trois séances, et leur prouvabilité s'échelonne de sept siècles à
    trois millénaires et demi.
    """
    b = _plate(540.0, "Catalogue · la structure",
               "Ce que la forme du prix laisse croire, sur un prix sans dérive",
               "du quart d'heure à la séance")

    ecart = 46.0
    lw = (_utile() - 2 * ecart) / 3.0

    # Retest d'un extrême de séance, en bougies de cinq minutes.
    chemin, i0 = _exemple("retest")
    niveau = _niveau_exemple("retest", chemin)
    bougies = _bougies(chemin, 0, 390, 5)
    p = _cadre_bougies(b, MARGE_G, 86.0, lw, 146.0, "Retest de niveau",
                       _num(100.0 * C.frequence_nulle("retest"), 1) + " %",
                       bougies, surligne=(i0 / 5.0 - 1.5, i0 / 5.0 + 1.5))
    p.hline(niveau, "lvl strong")
    p.grid_x([0.0, 39.0, 77.0], fmt=lambda v: _num(v * 5.0 / 60.0, 0) + " h",
             label="séance")

    # Rejet en mèche, en bougies de séance sur quinze séances.
    multi = _multi(15)
    jour = [(_bougies(multi[k * 390:(k + 1) * 390 + 1], 0, 390, 390) or
             [(0.0, 0.0, 0.0, 0.0, 0.0)])[0] for k in range(15)]
    jour = [(float(k), o, h, l, c) for k, (_, o, h, l, c) in enumerate(jour)]
    p2 = _cadre_bougies(b, MARGE_G + lw + ecart, 86.0, lw, 146.0,
                        "Rejet en mèche",
                        _num(100.0 * C.frequence_nulle("meche"), 1) + " %",
                        jour)
    k_meche = max(range(len(jour)),
                  key=lambda k: (jour[k][2] - max(jour[k][1], jour[k][4]))
                  / (abs(jour[k][4] - jour[k][1]) + 0.5))
    p2.band_x(k_meche - 0.5, k_meche + 0.5)
    p2.grid_x([0.0, 7.0, 14.0], fmt=lambda v: _num(v, 0), label="séances")

    # Plus haut plus haut : les pivots de la même série.
    p3 = _cadre_bougies(b, MARGE_G + 2 * (lw + ecart), 86.0, lw, 146.0,
                        "Plus haut plus haut",
                        _num(100.0 * C.frequence_nulle("structure"), 1) + " %",
                        jour)
    pivots = _pivots([c[4] for c in jour])
    for k, (idx, sens) in enumerate(pivots):
        p3.dot(float(idx), jour[idx][2] if sens > 0 else jour[idx][3],
               "s2" if sens > 0 else "s3", r=3.0)
    if len(pivots) >= 2:
        p3.path([(float(i), jour[i][2] if s > 0 else jour[i][3])
                 for i, s in pivots], "s2", dash="4 3")
    p3.grid_x([0.0, 7.0, 14.0], fmt=lambda v: _num(v, 0), label="séances")

    for col, cle in enumerate(("retest", "meche", "structure")):
        e = C.exigence(cle)
        x = MARGE_G + col * (lw + ecart)
        lignes = [
            f"une fois sur {_num(1.0 / C.frequence_nulle(cle), 1)} sans dérive",
            f"{C._grand(e.par_an)} décisions par an",
            f"établie en {C._ans(e.annees)}",
        ]
        for k, texte in enumerate(lignes):
            cls = "tk" if k == 2 else "lg"
            b.add(f'<text class="{cls}" x="{x:.1f}" y="{276.0 + 13 * k:.1f}">'
                  f'{_esc(texte)}</text>')

    _eventail(b, MARGE_G, 366.0, _utile(), 116.0, 1170.0,
              "Les trois séances qui suivent")

    _source(b, "Les trois cadres sont tirés des mêmes séances simulées sans "
               "dérive, et les deux de droite montrent la même série de "
               "quinze séances, lue deux fois : une fois pour la mèche d'une "
               "bougie, une fois pour les pivots qu'elle dessine. La structure "
               "de droite — un sommet plus haut, un creux "
               "plus haut — s'y forme comme elle se formerait sur un marché : "
               "neuf fois sur dix le hasard suffit à la produire. Le cône "
               "du bas est le seul du chapitre où l'écart se voit à l'œil : "
               "sur trois séances, la dérive haute du domaine plausible "
               "déplace la médiane de soixante-deux points. C'est aussi la "
               "lecture qui demande trois millénaires et demi pour être "
               "établie, faute d'occasions.")
    return b.render("Retest, rejet en mèche et structure de Dow sur des "
                    "séances sans dérive, et le cône des issues à trois séances")


FIGURES["catstructure"] = fig_structure


def _pivots(closes: list[float], seuil: float = 8.0) -> list[tuple[int, int]]:
    """Pivots alternés d'une série, par filtre de renversement.

    Un sommet est confirmé quand la série a reculé d'au moins `seuil` points
    depuis son plus haut ; un creux, symétriquement. C'est la mécanique de la
    théorie de Dow réduite à ce qu'elle a de vérifiable, et l'alternance
    sommet-creux en découle par construction plutôt que par convention.

    Deux extrêmes courants sont suivis en parallèle, et non un seul : avec un
    seul, la première version du filtre suivait la dernière valeur vue et ne
    confirmait jamais rien.
    """
    if not closes:
        return []
    out: list[tuple[int, int]] = []
    sens, i_max, i_min = 0, 0, 0
    for i, x in enumerate(closes):
        if x > closes[i_max]:
            i_max = i
        if x < closes[i_min]:
            i_min = i
        if sens >= 0 and closes[i_max] - x >= seuil:
            out.append((i_max, 1))
            sens, i_min = -1, i
        elif sens <= 0 and x - closes[i_min] >= seuil:
            out.append((i_min, -1))
            sens, i_max = 1, i
    return out


# ---------------------------------------------------------------------------
# Figure — le profil de marché : tirages simples et extrême pauvre
# ---------------------------------------------------------------------------


def _tpo_blocs(p: Panel, profil, marquer=None) -> None:
    """Dessine un profil TPO en blocs : une case par période et par rangée."""
    for prix, periodes in zip(profil.prices, profil.periods):
        if not (p.y0 <= prix <= p.y1):
            continue
        cls = "s2f" if (marquer and marquer(prix, periodes)) else "s1f"
        for k, _ in enumerate(sorted(periodes)):
            p.board.add(f'<rect class="{cls}" x="{p.sx(k) - 2.4:.2f}" '
                        f'y="{p.sy(prix) - 2.2:.2f}" width="4.8" height="4.4" '
                        f'opacity="0.85"/>')


def fig_tpo() -> str:
    """Les deux lectures du profil de marché, sur une séance sans dérive."""
    b = _plate(520.0, "Catalogue · le profil de marché",
               "Deux lectures du profil, et ce qu'elles annoncent",
               "périodes de trente minutes")

    ecart = 40.0
    lw = (_utile() - ecart) / 2.0
    chemin = C._seances()[0]
    profil = tp.from_path(chemin, n_periods=13, tick=1.0)
    simples = set(profil.single_prints)
    largeur = max(profil.counts)

    lo, hi = min(chemin), max(chemin)
    for col, (cle, titre, marquer) in enumerate((
            ("singles", "Tirages simples",
             lambda prix, per: prix in simples),
            ("extreme", "Extrême pauvre",
             lambda prix, per: prix >= profil.prices[-1] - 1e-9))):
        x = MARGE_G + col * (lw + ecart)
        pan = Panel(b, x, 86.0, lw, 150.0, titre,
                    _num(100.0 * C.frequence_nulle(cle), 1) + " %")
        pan.domain(-0.8, largeur + 0.8, lo - 2.0, hi + 2.0)
        pan.frame()
        pan.grid_y(_ticks(lo - 2.0, hi + 2.0, _pas(lo - 2.0, hi + 2.0)),
                   fmt=lambda v: _num(v, 0))
        pan.grid_x([float(k) for k in range(0, largeur + 1,
                                            max(1, largeur // 4))],
                   fmt=lambda v: _num(v + 1, 0),
                   label="périodes ayant visité la rangée")
        _tpo_blocs(pan, profil, marquer)
        pan.hline(profil.poc, "lvl strong")
        pan.tag(profil.poc, "POC", side="right")

        e = C.exigence(cle)
        lignes = [
            f"une fois sur {_num(1.0 / C.frequence_nulle(cle), 1)} sans dérive",
            f"{C._grand(e.par_an)} décisions par an",
            f"établie en {C._ans(e.annees)}",
        ]
        for k, texte in enumerate(lignes):
            cls = "tk" if k == 2 else "lg"
            b.add(f'<text class="{cls}" x="{x:.1f}" y="{282.0 + 13 * k:.1f}">'
                  f'{_esc(texte)}</text>')

    _eventail(b, MARGE_G, 348.0, _utile(), 116.0, 390.0,
              "La séance qui suit")

    _source(b, "Une même séance simulée sans dérive, lue deux fois. À gauche, "
               "les rangées qu'une seule période a visitées sont marquées ; à "
               "droite, c'est le haut de séance qui l'est, plat parce que deux "
               "périodes y ont imprimé. Les deux lectures se donnent pour "
               "rares et ne le sont pas au même degré : une rangée en tirage "
               "simple est comblée avant la clôture une fois sur deux, un haut "
               "plat se produit trois fois sur cent. Ce qui les sépare "
               "vraiment n'est pas leur rareté mais le nombre d'occasions "
               "qu'elles offrent — onze cents par an contre huit.")
    return b.render("Profil de marché sur une séance sans dérive : tirages "
                    "simples et extrême pauvre, avec le cône à une séance")


FIGURES["cattpo"] = fig_tpo


# ---------------------------------------------------------------------------
# Figure — l'ordre calculé, et le mur de prouvabilité
# ---------------------------------------------------------------------------

#: Décalages d'étiquettes, écrits une fois pour toutes. Un placement
#: automatique donnerait des chevauchements sur un nuage aussi serré, et un
#: nuage de quinze points ne justifie pas un solveur.
_ETIQ = {
    "desequilibre": (8.0, -8.0, "start"), "carnet": (8.0, 4.0, "start"),
    "absorption": (8.0, 15.0, "start"), "epuisement": (8.0, 15.0, "start"),
    "divergence": (8.0, -8.0, "start"), "lvn": (8.0, -8.0, "start"),
    "singles": (8.0, 15.0, "start"), "vwap": (-9.0, -8.0, "end"),
    "ote": (-9.0, 15.0, "end"), "poc": (8.0, 4.0, "start"),
    "gamma": (8.0, -8.0, "start"), "meche": (8.0, 4.0, "start"),
    "structure": (-9.0, 15.0, "end"), "retest": (-9.0, 4.0, "end"),
    "extreme": (8.0, 15.0, "start"),
}


def fig_ordre() -> str:
    """Pourquoi le catalogue est dans cet ordre, et où il se coupe.

    Un seul plan suffit : l'horizon en abscisse, les décisions offertes par an
    en ordonnée. La courbe de la carrière y sépare les lectures qu'on peut
    établir de celles qu'on ne pourra pas.
    """
    b = _plate(490.0, "Catalogue · l'ordre",
               "Ce qu'on peut établir, et ce qu'on ne pourra pas",
               "les deux axes sont logarithmiques")

    p = Panel(b, MARGE_G, 88.0, _utile(), 244.0,
              "Horizon de la lecture contre décisions offertes par an",
              "au-dessus de la courbe : établi en moins de "
              + C.num(C.CARRIERE_ANS, 0) + " ans")
    p.domain(3.0, 1600.0, 4.0, 40000.0, xlog=True, ylog=True)
    p.frame()
    p.grid_y([10.0, 100.0, 1000.0, 10000.0],
             fmt=lambda v: C._grand(v), label="décisions par an", dx=52.0)
    p.grid_x([5.0, 15.0, 60.0, 390.0, 1170.0],
             fmt=lambda v: _num(v, 0),
             label="horizon de la lecture, en minutes", rules=True)

    courbe = []
    t = 3.0
    while t <= 1600.0:
        courbe.append((t, C.decisions_pour(t) / C.CARRIERE_ANS))
        t *= 1.08
    p.path(courbe, "s2", dash="5 3")

    for l in C.ordre():
        e = C.exigence(l.cle)
        ok = e.annees <= C.CARRIERE_ANS
        p.dot(l.horizon_min, max(e.par_an, 4.1), "s1" if ok else "neg",
              tip=f"{l.nom} — {C._ans(e.annees)}", r=4.5)
    for l in C.ordre():
        dx, dy, anc = _ETIQ[l.cle]
        p.label(l.horizon_min, max(C.exigence(l.cle).par_an, 4.1), l.nom,
                dx=dx, dy=dy, anchor=anc)

    b.legend(MARGE_G, 386.0,
             [("s1f", "établie en moins de " + C.num(C.CARRIERE_ANS, 0)
               + " ans"),
              ("negf", "hors de portée d'une carrière")],
             step=0.34 * _utile())
    b.legend(MARGE_G + 0.68 * _utile(), 386.0,
             [("s2", "la courbe de la carrière")], kind="line")

    _source(b, "Chaque point est une lecture du catalogue. L'abscisse est son "
               "horizon, l'ordonnée le nombre de décisions qu'elle offre par "
               "an — le produit de ses occasions par séance, de la fréquence "
               "de son motif et des deux cent cinquante-deux séances de "
               "l'année. La courbe en tirets est le lieu des lectures qu'une "
               "carrière suffit tout juste à établir. Elle monte, parce que le "
               "nombre de décisions requises croît avec l'horizon ; les "
               "lectures lentes sont donc doublement pénalisées, exigeant plus "
               "de décisions au moment même où elles en offrent moins.")
    return b.render("Horizon contre décisions annuelles, et la courbe qui "
                    "sépare les lectures établissables des autres")


FIGURES["catordre"] = fig_ordre


# ---------------------------------------------------------------------------
# Figure — l'invariant : le produit qui ne bouge pas
# ---------------------------------------------------------------------------


def fig_invariant() -> str:
    """Ce que la lecture exige du marché, contre ce qu'elle exige de l'échantillon.

    Les quinze lectures tombent sur une droite de pente −1 en échelles
    logarithmiques, c'est-à-dire sur une hyperbole : leur produit est
    constant. Il n'y a donc pas de bonne et de mauvaise lecture, il y a deux
    devises pour la même facture.
    """
    inv = C.invariant("derive")
    b = _plate(474.0, "Catalogue · l'invariant",
               "Le marché d'un côté, l'échantillon de l'autre",
               "µ*·N = " + C._grand(inv.moyenne))

    p = Panel(b, MARGE_G, 88.0, _utile(), 250.0,
              "Dérive requise contre décisions requises",
              "écart d'un bout à l'autre : "
              + C.num(100.0 * inv.etendue, 2) + " %")
    p.domain(0.005, 4.0, 700.0, 400_000.0, xlog=True, ylog=True)
    p.frame()
    p.grid_y([1000.0, 10000.0, 100000.0], fmt=lambda v: C._grand(v),
             label="décisions requises", dx=52.0)
    p.grid_x([0.01, 0.03, 0.1, 0.3, 1.0, 3.0],
             fmt=lambda v: _num(v, 3 if v < 0.1 else 2),
             label="dérive requise, en points d'indice par heure", rules=True)

    p.band_x(*C.seuil.PLAUSIBLE_DRIFT_PER_HOUR)

    hyper = []
    mu = 0.005
    while mu <= 4.0:
        hyper.append((mu, inv.moyenne / mu))
        mu *= 1.06
    p.path(hyper, "s2", dash="5 3")

    for l in C.ordre():
        e = C.exigence(l.cle)
        p.dot(e.derive_requise, e.decisions, "s1",
              tip=f"{l.nom} — µ* {C.num(e.derive_requise, 3)} pt/h, "
                  f"{C._grand(e.decisions)} décisions", r=4.5)
    for cle, texte, dx, dy, anc in (
            ("desequilibre", "5 min", 8.0, 14.0, "start"),
            ("divergence", "15 min", 8.0, -8.0, "start"),
            ("vwap", "30 min", 8.0, 14.0, "start"),
            ("lvn", "1 h", -9.0, -10.0, "end"),
            ("singles", "1,5 h", 8.0, 17.0, "start"),
            ("retest", "2 h", -9.0, -8.0, "end"),
            ("meche", "1 séance", 8.0, 14.0, "start"),
            ("structure", "3 séances", 8.0, -8.0, "start")):
        e = C.exigence(cle)
        p.label(e.derive_requise, e.decisions, texte, dx=dx, dy=dy, anchor=anc)

    b.legend(MARGE_G, 392.0,
             [("s1f", "les quinze lectures"),
              ("swatch-wash", "domaine de dérive plausible")],
             step=0.34 * _utile())
    b.legend(MARGE_G + 0.68 * _utile(), 392.0,
             [("s2", "l'hyperbole du produit constant")], kind="line")

    _source(b, "Chaque point est une lecture, placée par ce que sa géométrie "
               "exige du marché et par le nombre de décisions qu'il faut pour "
               "l'établir. Les quinze tombent sur l'hyperbole, à un pour "
               "mille et demi près. Une lecture rapide exige du marché deux "
               "cent trente fois plus de dérive qu'une lecture lente et deux "
               "cent trente fois moins de décisions : le produit ne bouge "
               "pas. Aucun horizon n'est donc avantageux en soi, et le choix "
               "d'un horizon n'est pas un choix de qualité mais un choix de "
               "monnaie — payer en exigence sur le marché, ou payer en "
               "patience.")
    return b.render("Dérive requise contre décisions requises : les quinze "
                    "lectures sur une hyperbole de produit constant")


FIGURES["catinvariant"] = fig_invariant


# ---------------------------------------------------------------------------
# Figures en nuage de points — le mur, puis le gain
# ---------------------------------------------------------------------------

#: Horizons balayés par les deux surfaces, en minutes, du plus long au plus
#: court. L'ordre décroissant n'est pas indifférent : en projection isométrique
#: le coin `(0, 0)` est le plus **éloigné**, et y placer le maximum fait monter
#: le relief vers le fond. À l'ordre inverse, le sommet tombait au premier plan,
#: où l'œil ne peut pas le comparer au coin lointain — deux points de
#: profondeur différente ne se comparent pas par leur hauteur à l'écran.
HORIZONS = (1170.0, 390.0, 120.0, 60.0, 30.0, 15.0, 5.0)

#: Occasions par séance balayées. Trois décades : de la lecture qui ne se
#: présente qu'une fois tous les trois jours à celle qui se présente trois
#: cents fois par séance.
OCCASIONS = (0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0)

#: Dérives balayées, en points d'indice par heure. La dernière est la borne
#: haute du domaine que le document nº 1 tient pour plausible.
DERIVES = (3.2, 2.7, 2.2, 1.6, 1.0, 0.5, 0.0)

#: Fréquence de motif retenue pour la surface du mur. C'est la médiane des
#: quinze fréquences du catalogue, arrondie : la surface balaie les occasions
#: et l'horizon, il faut bien que la troisième grandeur soit tenue fixe.
FREQUENCE_TYPE = 0.30


def _horizon_court(t: float) -> str:
    if t < 60:
        return _num(t, 0) + " min"
    if t < 390:
        return _num(t / 60.0, 0) + " h"
    return _num(t / 390.0, 0) + " sé."


def fig_mur() -> str:
    """Le mur de prouvabilité, en années, sur deux axes.

    Un relief à une seule pente, et c'est ce qui le rend lisible : le délai
    monte quand l'horizon s'allonge et quand les occasions se raréfient, et
    les deux effets se composent sans jamais se compenser.
    """
    b = _plate(524.0, "Catalogue · le mur",
               "Combien d'années pour établir une lecture",
               "hauteur : délai, en années")

    z = [[math.log10(max(C.decisions_pour(t)
                         / (occ * FREQUENCE_TYPE * C.SEANCES_PAR_AN), 0.02))
          for occ in OCCASIONS] for t in HORIZONS]
    _surface(b, 0.52 * W, 212.0, z, -1.0, 4.0,
             cx=27.0, cy=14.0, cz=150.0,
             row_labels=[_horizon_court(t) for t in HORIZONS],
             col_labels=[_num(o, 1 if o < 1 else 0) for o in OCCASIONS],
             z_ticks=[(-1.0, "1 mois"), (0.0, "1 an"),
                      (math.log10(C.CARRIERE_ANS), "carrière"),
                      (2.0, "1 siècle"), (4.0, "100 siècles")],
             tip="{v:.2f} en log d'années")

    b.annotation(0.0, 462.0,
                 "arête gauche : horizon de la lecture · arête droite : "
                 "occasions par séance")
    _source(b, "La hauteur est le délai d'établissement, en échelle "
               "logarithmique : chaque graduation vaut dix fois la "
               "précédente. Le relief n'a qu'une pente, et c'est le fait à "
               "retenir — allonger l'horizon et raréfier les occasions "
               "poussent dans le même sens, si bien qu'aucune lecture lente ne "
               "peut se rattraper en se présentant plus souvent. Le coin du "
               "fond est la lecture de trois séances qui ne se présente qu'une "
               "fois tous les trois jours ; le coin le plus proche, la lecture "
               "de cinq minutes qui se présente trois cents fois par séance. "
               "Le plan de la carrière coupe la surface vers une heure et "
               "quarante minutes d'horizon pour une lecture qui se présente "
               "dix fois par séance, et vers dix minutes seulement pour une "
               "lecture qui ne se présente qu'une fois. Tout ce qui est "
               "au-delà appartient à la littérature, pas à la mesure.")
    return b.render("Surface du délai de preuve selon horizon et occasions "
                    "par séance")


FIGURES["catmur"] = fig_mur


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def fig_gain() -> str:
    """Ce que la dérive ajoute à la probabilité d'avoir raison.

    La hauteur est le gain en points de pourcentage sur la probabilité que le
    prix soit plus haut à l'horizon. Elle se calcule en forme fermée — la loi
    du déplacement est normale — et ne doit donc rien à une simulation.
    """
    b = _plate(524.0, "Catalogue · le gain",
               "Ce que la dérive ajoute à la chance d'avoir raison",
               "hauteur : points au-dessus de 50 %")

    z = [[100.0 * (_phi(d / 60.0 * math.sqrt(t) / C.q.SIGMA_1MIN) - 0.5)
          for d in DERIVES] for t in HORIZONS]
    _surface(b, 0.52 * W, 212.0, z, 0.0, 45.0,
             cx=27.0, cy=14.0, cz=150.0,
             row_labels=[_horizon_court(t) for t in HORIZONS],
             col_labels=[_num(d, 1) for d in DERIVES],
             z_ticks=[(0.0, "0"), (10.0, "+10"), (20.0, "+20"),
                      (30.0, "+30"), (45.0, "+45")],
             tip="{v:+.1f} points")

    b.annotation(0.0, 462.0,
                 "arête gauche : horizon de la lecture · arête droite : "
                 "dérive du marché, en points par heure")
    _source(b, "Le coin le plus proche est la lecture de cinq minutes sans "
               "dérive : le gain y est nul, et c'est la situation de "
               "l'opérateur intraday. Le coin du fond est la lecture de trois "
               "séances sous la dérive la plus forte que le domaine plausible "
               "autorise : quarante-trois points de pourcentage, c'est-à-dire "
               "une quasi-certitude. Les deux coins décrivent le même "
               "marché. Ce qui les sépare n'est pas "
               "la qualité de la lecture mais la durée pendant laquelle on la "
               "laisse agir — et cette durée est exactement ce que la figure "
               "précédente déclare hors de portée de preuve.")
    return b.render("Surface du gain de probabilité selon horizon et dérive")


FIGURES["catgain"] = fig_gain


def render_all() -> dict[str, str]:
    return {k: v() for k, v in FIGURES.items()}
