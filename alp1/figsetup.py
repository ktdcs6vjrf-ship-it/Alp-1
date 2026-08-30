"""Les figures du setup : le niveau, le contact, la confirmation, sa suite.

Les planches du catalogue montraient des **motifs**. Celles-ci montrent des
**setups** : un niveau calculé, le prix qui vient le toucher, la condition
qu'on avait écrite d'avance, et ce que le prix en fait ensuite. C'est la
différence entre « voici une absorption » et « voici une absorption sur le
point de contrôle, tenue par ces trois critères, démentie par celui-ci ».

Trois règles gouvernent ce module, et elles viennent toutes d'un défaut
constaté :

* **une figure de setup montre l'objet, pas son contexte.** Le footprint se
  dessine en cellules bid × ask, jamais en bougies — une planche de bougies
  posée devant une section qui parle de déséquilibre diagonal ne montre rien
  de ce dont la section parle ;
* **chaque marque porte son nom dans la figure.** Un cadre, un liseré, une
  bande ne disent rien tant qu'une ligne ne dit pas ce qu'ils marquent ;
* **rien n'est choisi.** L'exemple d'une confirmation est le premier que le
  détecteur retient dans l'ordre des graines, et les cases cochées sous chaque
  colonne sont celles que la mesure a cochées — figure et table lisent la même
  liste de critères.

Aucune couleur n'est écrite : les planches posent des classes et `figcss.py`
décide.
"""

from __future__ import annotations

import math

from . import concepts as C
from . import dow, seuil
from . import footprint as fp
from . import setups as S
from . import vprofile
from .figdisc import W, _plate, _ramp, _source, _surface
from .figterm import Board, Panel, _esc, _num

FIGURES: dict[str, object] = {}

#: Marges de la planche. La gauche porte les graduations de prix, qui sont
#: larges : un cadre posé plus à gauche rejette ses étiquettes hors du SVG.
MARGE_G = 62.0
MARGE_D = 12.0


def _utile() -> float:
    return W - MARGE_G - MARGE_D


#: Coche et croix. Elles sont écrites en caractère littéral, jamais en entité
#: HTML : le balayage des figures refuse les entités, qui se rendent en clair
#: dans certains contextes.
OUI, NON = "✓", "✗"


# ---------------------------------------------------------------------------
# Bougies construites sur de vraies barres
# ---------------------------------------------------------------------------


def _bougies(barres, debut: int, fin: int, pas: int = 1):
    """Agrège de vraies barres en bougies de `pas` minutes.

    Le haut d'une bougie est le plus haut des barres qu'elle couvre, et non le
    plus haut de leurs clôtures : c'est ce qui distingue une bougie d'une
    ligne brisée, et c'est précisément la mèche que la confirmation de rejet
    mesure.
    """
    out = []
    for k, i in enumerate(range(debut, fin, pas)):
        tranche = barres[i:i + pas]
        if not tranche:
            break
        out.append((float(k), i, tranche[0].ouverture,
                    max(b.haut for b in tranche),
                    min(b.bas for b in tranche),
                    tranche[-1].cloture))
    return out


def _tracer(p: Panel, bougies, largeur: float = 0.62,
            surligne: int | None = None) -> None:
    """Dessine les bougies ; `surligne` cercle celle de la minute donnée."""
    demi = 0.5 * largeur * p.w / max(len(bougies), 1)
    for t, i, o, h, b_, c in bougies:
        cls = "s1f" if c >= o else "negf"
        ln = "s1" if c >= o else "neg"
        x = p.sx(t)
        p.board.add(f'<line class="ln {ln}" x1="{x:.2f}" y1="{p.sy(h):.2f}" '
                    f'x2="{x:.2f}" y2="{p.sy(b_):.2f}" stroke-width="1"/>')
        yh, yb = p.sy(max(o, c)), p.sy(min(o, c))
        p.board.add(f'<rect class="{cls}" x="{x - demi:.2f}" y="{yh:.2f}" '
                    f'width="{2 * demi:.2f}" '
                    f'height="{max(yb - yh, 1.0):.2f}"/>')
        if surligne is not None and i == surligne:
            p.board.add(f'<rect class="rang" x="{x - demi - 2:.2f}" '
                        f'y="{p.sy(h) - 3:.2f}" width="{2 * demi + 4:.2f}" '
                        f'height="{p.sy(b_) - p.sy(h) + 6:.2f}" rx="2"/>')


def _pas(lo: float, hi: float) -> float:
    brut = (hi - lo) / 4.0
    exposant = math.floor(math.log10(brut)) if brut > 0 else 0
    base = 10.0 ** exposant
    for m in (1.0, 2.0, 2.5, 5.0, 10.0):
        if brut <= m * base:
            return m * base
    return 10.0 * base


def _ticks(lo: float, hi: float) -> list[float]:
    pas = _pas(lo, hi)
    v = math.ceil(lo / pas) * pas
    out = []
    while v <= hi + 1e-9:
        out.append(round(v, 6))
        v += pas
    return out


def _bande_y(p: Panel, lo: float, hi: float, cls: str = "zone") -> None:
    """Une bande horizontale **découpée au domaine du cadre**.

    `Panel.band_y` ne découpe pas : une aire de valeur plus large que la
    fenêtre débordait du cadre et venait se peindre sur les graduations du
    voisin. Le découpage se fait ici plutôt que dans le cadre partagé, qui
    sert trois autres documents.
    """
    ylo, yhi = sorted((p.y0, p.y1))
    a, z = max(min(lo, hi), ylo), min(max(lo, hi), yhi)
    if z <= a:
        return
    p.band_y(a, z, cls)


def _cadre(b: Board, x, y, w, h, titre, readout, bougies, niveaux=(),
           surligne=None, marge: float = 0.12) -> Panel:
    """Un cadre de bougies dont le domaine **contient** les niveaux tracés.

    Le domaine se déduit des données et des niveaux à la fois. C'est le point
    de vigilance de tout ce dépôt : un niveau posé hors du domaine est tout de
    même tracé par `hline`, qui ne découpe pas, et vient alors se coller au
    bord du cadre en prétendant être un niveau lu.
    """
    valeurs = [c[3] for c in bougies] + [c[4] for c in bougies] + list(niveaux)
    lo, hi = min(valeurs), max(valeurs)
    tampon = marge * (hi - lo or 1.0)
    p = Panel(b, x, y, w, h, titre, readout)
    p.domain(-0.6, len(bougies) - 0.4, lo - tampon, hi + tampon)
    p.frame()
    p.grid_y(_ticks(lo - tampon, hi + tampon), fmt=lambda v: _num(v, 2))
    _tracer(p, bougies, surligne=surligne)
    return p


# ---------------------------------------------------------------------------
# Figure — le footprint sur le niveau de liquidité
# ---------------------------------------------------------------------------

#: Rangées de footprint affichées de part et d'autre du niveau. Onze couvrent
#: deux points et demi d'indice, soit l'étendue d'une minute ordinaire.
RANGEES = 11


def _echelle_cellules(bar) -> int:
    return max(max(c.bid, c.ask) for c in bar.cells) or 1


def _cellule(b: Board, x: float, y: float, w: float, h: float, valeur: int,
             vmax: int, encadre: bool = False) -> None:
    """Une demi-cellule de footprint : un fond gradué et son nombre.

    Le fond code le volume du côté, jamais son signe : le signe est déjà porté
    par le côté où la cellule se trouve. Le nombre est cerné de la couleur du
    papier, sans quoi il disparaît dans les cellules les plus chargées.
    """
    part = valeur / vmax if vmax else 0.0
    b.add(f'<rect class="{_ramp(0.10 + 0.80 * part)}" x="{x:.1f}" '
          f'y="{y - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" '
          f'opacity="0.42"/>')
    if encadre:
        b.add(f'<rect class="imb" x="{x + 0.8:.1f}" y="{y - h / 2 + 0.8:.1f}" '
              f'width="{w - 1.6:.1f}" height="{h - 1.6:.1f}" rx="2"/>')
    b.add(f'<text class="tk halo" x="{x + w / 2:.1f}" y="{y + 3.5:.1f}" '
          f'text-anchor="middle">{valeur}</text>')


def _footprint_colonne(b: Board, x: float, y: float, w: float, contact,
                       hauteur_rangee: float = 15.0) -> float:
    """Le footprint de la barre d'un contact, avec sa rangée de niveau.

    Rendu l'ordonnée du bas du bloc, pour que l'appelant y pose la suite.
    """
    barre, bar = S.barre_fp(contact)
    cells = list(bar.cells)
    # Onze rangées centrées sur le niveau : au-delà, la colonne dépasse le
    # cadre voisin, et les rangées éloignées ne portent presque rien.
    proche = min(range(len(cells)),
                 key=lambda i: abs(cells[i].price - contact.niveau))
    debut = max(0, min(proche - RANGEES // 2, len(cells) - RANGEES))
    cells = cells[debut:debut + RANGEES]
    vmax = _echelle_cellules(bar)
    desq = dict(fp.diagonal_imbalances(bar))

    largeur_prix = 40.0
    largeur_cell = (w - largeur_prix) / 2.0
    x_bid = x + largeur_prix
    x_ask = x_bid + largeur_cell

    b.add(f'<text class="tk" x="{x:.1f}" y="{y - 6:.1f}">prix</text>')
    b.add(f'<text class="tk" x="{x_bid + largeur_cell / 2:.1f}" '
          f'y="{y - 6:.1f}" text-anchor="middle">bid</text>')
    b.add(f'<text class="tk" x="{x_ask + largeur_cell / 2:.1f}" '
          f'y="{y - 6:.1f}" text-anchor="middle">ask</text>')
    b.add(f'<line class="hsep" x1="{x:.1f}" y1="{y - 2:.1f}" '
          f'x2="{x + w:.1f}" y2="{y - 2:.1f}"/>')

    for k, cellule in enumerate(reversed(cells)):
        yy = y + 10.0 + k * hauteur_rangee
        cote = desq.get(cellule.price)
        b.add(f'<text class="tk" x="{x + largeur_prix - 6:.1f}" '
              f'y="{yy + 3.5:.1f}" text-anchor="end">'
              f'{_num(cellule.price + S.PRIX_BASE, 2)}</text>')
        _cellule(b, x_bid, yy, largeur_cell, hauteur_rangee - 1.0,
                 cellule.bid, vmax, encadre=cote == "vendeur")
        _cellule(b, x_ask, yy, largeur_cell, hauteur_rangee - 1.0,
                 cellule.ask, vmax, encadre=cote == "acheteur")

    # La rangée du niveau est cerclée après les cellules : un aplat posé
    # dessous disparaîtrait sous leurs fonds gradués.
    rang = min(range(len(cells)), key=lambda i: abs(cells[i].price
                                                   - contact.niveau))
    y_rang = y + 10.0 + (len(cells) - 1 - rang) * hauteur_rangee
    b.add(f'<rect class="rang" x="{x - 1:.1f}" '
          f'y="{y_rang - hauteur_rangee / 2:.1f}" width="{w + 2:.1f}" '
          f'height="{hauteur_rangee:.1f}" rx="2"/>')
    return y + 10.0 + len(cells) * hauteur_rangee


def _liste_criteres(b: Board, x: float, y: float, w: float, contact,
                    confirmation: str) -> float:
    """La liste des critères de la confirmation, cochés par la mesure."""
    barres, volume_median = S.contexte(contact)
    barre = barres[contact.minute]
    lignes = S.criteres(confirmation, barre, contact.niveau, contact.sens,
                        volume_median)
    for k, c in enumerate(lignes):
        yy = y + k * 13.0
        b.add(f'<text class="dl" x="{x:.1f}" y="{yy:.1f}">'
              f'{OUI if c.ok else NON}</text>')
        b.add(f'<text class="lg" x="{x + 12:.1f}" y="{yy:.1f}">'
              f'{_esc(c.court)}</text>')
        b.add(f'<text class="tk" x="{x + w:.1f}" y="{yy:.1f}" '
              f'text-anchor="end">{_esc(c.valeur)} · {_esc(c.exige)}</text>')
    return y + len(lignes) * 13.0


#: Géométrie d'une bande : bougies à gauche, footprint au milieu, critères à
#: droite. Les trois largeurs somment la largeur utile, et chacune est le
#: minimum de ce que son contenu demande — un cadre de bougies plus étroit
#: cesse de montrer l'approche, une colonne de critères plus étroite coupe
#: ses lignes.
L_BOUGIES, L_FOOT, L_CRIT = 200.0, 170.0, 184.0

#: Écart entre les deux cadres d'une rangée de zooms. Il doit dépasser la
#: largeur d'une graduation de prix : les étiquettes du cadre de droite sont
#: posées à sa gauche, et un écart plus court les fait mordre sur le cadre
#: voisin. Le défaut s'est vu sur les trois planches à la fois.
ECART_ZOOM = 58.0
ECART_BANDE = 16.0
PITCH = 196.0


def fig_footprint() -> str:
    """Le footprint sur un niveau de liquidité, et les trois lectures.

    Le niveau est le **point de contrôle** de la première demi-séance — le
    prix auquel le plus de contrats se sont échangés, c'est-à-dire la zone de
    liquidité au sens le plus littéral. La bande teintée derrière les bougies
    est l'aire de valeur du même profil : elle dit où la liquidité se trouve,
    le trait plein où elle culmine.

    Les trois bandes sont trois vrais contacts de ce niveau, tirés dans
    l'ordre des graines : celui que l'absorption retient, celui que le rejet
    retient, celui que l'exécution retient. Chacune montre la même chose dans
    le même ordre — l'approche en bougies, le **footprint de la barre du
    contact**, les critères cochés par la mesure, et ce que le prix a fait
    ensuite.
    """
    confirmations = (("absorption", "Absorption"),
                     ("rejet", "Rejet en mèche"),
                     ("execution", "Exécution"))
    exemples = {cle: S.exemple("poc", cle) for cle, _ in confirmations}

    b = _plate(116.0 + 3 * PITCH + 24.0, "Setup · le footprint au niveau",
               "Le point de contrôle abordé trois fois, et ce qui le confirme",
               "bid à gauche · ask à droite")

    b.annotation(MARGE_G, 62.0,
                 "bande teintée : l'aire de valeur · trait plein : le point de "
                 "contrôle · tirets : le seuil d'invalidation")
    b.annotation(MARGE_G, 75.0,
                 "footprint : une rangée par tick, bid à gauche, ask à "
                 "droite ; le cadre marque un déséquilibre 3:1")

    x_foot = MARGE_G + L_BOUGIES + ECART_BANDE
    x_crit = x_foot + L_FOOT + ECART_BANDE

    for rang, (cle, titre) in enumerate(confirmations):
        contact = exemples[cle]
        y = 116.0 + rang * PITCH
        barres, volume_median = S.contexte(contact)
        i = contact.minute
        pr = S.profil(contact.seance)
        va = pr.value_area()

        # --- l'approche, en bougies -----------------------------------------
        bougies = [(t, j, o + S.PRIX_BASE, h + S.PRIX_BASE,
                    l + S.PRIX_BASE, c + S.PRIX_BASE)
                   for t, j, o, h, l, c in
                   _bougies(barres, max(i - 16, 0), min(i + 13, len(barres)))]
        inval = contact.niveau + contact.sens * S.DEPASSEMENT * S.q.SIGMA_1MIN
        p = _cadre(b, MARGE_G, y, L_BOUGIES, 126.0, titre,
                   "séance " + str(contact.seance + 1) + " · minute "
                   + str(i), bougies,
                   niveaux=(contact.niveau + S.PRIX_BASE,
                            inval + S.PRIX_BASE),
                   surligne=i)
        _bande_y(p, va.low + S.PRIX_BASE, va.high + S.PRIX_BASE)
        p.hline(contact.niveau + S.PRIX_BASE, "lvl strong")
        p.hline(inval + S.PRIX_BASE, "lvl")
        p.tag(contact.niveau + S.PRIX_BASE, "POC", side="left")
        # Deux graduations seulement : une troisième posée au bord droit
        # déborderait sur la colonne de prix du footprint, que rien ne
        # protège — un libellé d'abscisse est centré sur sa graduation.
        p.grid_x([0.0, 16.0],
                 fmt=lambda v: "−16 min" if v == 0.0 else "contact")

        # --- le footprint de la barre du contact -----------------------------
        bas = _footprint_colonne(b, x_foot, y + 14.0, L_FOOT, contact,
                                 hauteur_rangee=12.0)
        barre = barres[i]
        for k, texte in enumerate((
                f"volume {barre.volume} · delta {barre.delta:+d}",
                f"z {_num(barre.z, 2)} · mèche "
                f"{_num(100.0 * barre.meche(contact.sens), 0)} %")):
            b.add(f'<text class="tk" x="{x_foot:.1f}" '
                  f'y="{bas + 13 + 12 * k:.1f}">{_esc(texte)}</text>')

        # --- les critères, cochés par la mesure ------------------------------
        b.add(f'<text class="lg" x="{x_crit:.1f}" y="{y + 8:.1f}">'
              f'{_esc("ce que la confirmation exige")}</text>')
        fin = _liste_criteres(b, x_crit, y + 26.0, L_CRIT, contact, cle)
        tenue = cle not in contact.invalidations
        lignes = [
            ("confirmation tenue" if tenue else
             "démentie en moins de " + str(S.FENETRE) + " min"),
            "une heure après : " + _num(contact.suite[60.0], 2) + " pt",
            "dans le sens de l'approche",
        ]
        for k, texte in enumerate(lignes):
            cls = "lg" if k == 0 else "tk"
            b.add(f'<text class="{cls}" x="{x_crit:.1f}" '
                  f'y="{fin + 18 + 13 * k:.1f}">{_esc(texte)}</text>')

    m = {cle: S.mesurer("poc-" + cle) for cle in ("absorption", "execution")}
    _source(b, "Le niveau est calculé, jamais choisi : c'est le point de "
               "contrôle du profil de volume de la première demi-séance, et "
               "les contacts sont comptés sur la seconde. Les trois exemples "
               "sont les premiers que chaque confirmation retient dans "
               "l'ordre des graines — aucun n'a été trié sur sa suite, et "
               "deux des trois sont démentis dans le quart d'heure, ce qui "
               "est la proportion ordinaire. Les cases cochées sont celles que "
               "la mesure coche : la figure et la table lisent la même liste "
               "de critères, ce qui leur interdit de diverger. Le point qui "
               "décide n'est pas le motif mais sa rareté — l'absorption "
               "retient " + _num(100.0 * m["absorption"].part_confirmee, 1)
             + " % des contacts du point de contrôle, l'exécution "
             + _num(100.0 * m["execution"].part_confirmee, 1) + " %, et "
               "aucune des deux ne déplace la probabilité que le prix aille "
               "dans le sens attendu.")
    return b.render("Trois contacts du point de contrôle en footprint, avec "
                    "les critères des trois confirmations")


FIGURES["setfoot"] = fig_footprint


# ---------------------------------------------------------------------------
# Le zoom : un contact, sa confirmation, ce qu'elle exigeait
# ---------------------------------------------------------------------------


def _zoom(b: Board, x: float, y: float, w: float, h: float, contact,
          cle_niveau: str, confirmation: str, titre: str, etiquette: str,
          avant: int = 18, apres: int = 24) -> float:
    """Un contact vu de près : l'approche, le niveau, les critères.

    C'est le motif de lecture commun aux planches du profil, de la structure
    et du VWAP. Il montre toujours les mêmes cinq choses dans le même ordre —
    d'où le prix vient, quel niveau il touche, ce que la confirmation exigeait,
    ce qu'elle a valu, et ce que le prix a fait ensuite.
    """
    barres, _ = S.contexte(contact)
    i = contact.minute
    bougies = [(t, j, o + S.PRIX_BASE, hh + S.PRIX_BASE,
                l + S.PRIX_BASE, c + S.PRIX_BASE)
               for t, j, o, hh, l, c in
               _bougies(barres, max(i - avant, 0), min(i + apres, len(barres)))]
    inval = contact.niveau + contact.sens * S.DEPASSEMENT * S.q.SIGMA_1MIN
    p = _cadre(b, x, y, w, h, titre,
               "séance " + str(contact.seance + 1), bougies,
               niveaux=(contact.niveau + S.PRIX_BASE, inval + S.PRIX_BASE),
               surligne=i)
    p.hline(contact.niveau + S.PRIX_BASE, "lvl strong")
    p.hline(inval + S.PRIX_BASE, "lvl")
    p.tag(contact.niveau + S.PRIX_BASE, etiquette, side="left")
    p.grid_x([0.0, float(min(avant, i))],
             fmt=lambda v: "−" + str(min(avant, i)) + " min" if v == 0.0
             else "contact")
    fin = _liste_criteres(b, x, y + h + 34.0, w, contact, confirmation)
    tenue = confirmation not in contact.invalidations
    suite = contact.suite[S._PAR_NIVEAU[cle_niveau].horizon_min]
    b.add(f'<text class="tk" x="{x:.1f}" y="{fin + 15:.1f}">'
          f'{_esc(("tenue" if tenue else "démentie en " + str(S.FENETRE) + " min") + " · ensuite " + _num(suite, 2) + " pt")}</text>')
    return fin + 15.0


def _seance_temoin(cle_niveau: str, confirmations) -> int:
    """La première séance qui porte un exemple de **chaque** confirmation.

    Le choix n'est pas d'esthétique. Une planche dont le cadre du haut montre
    une séance et les zooms deux autres oblige le lecteur à trois lectures ;
    et une séance où le niveau n'est jamais touché — il y en a — ferait
    afficher « 0 contact » au-dessus d'un cadre qui illustre un setup. La
    règle est déclarée et calculée : la première séance, dans l'ordre des
    graines, qui porte les deux.
    """
    lot = S.contacts(cle_niveau)
    par_seance: dict[int, set[str]] = {}
    for c in lot:
        par_seance.setdefault(c.seance, set()).update(c.confirmations)
    for index in sorted(par_seance):
        if all(k in par_seance[index] for k in confirmations):
            return index
    return 0


def _exemple(cle_niveau: str, confirmation: str, rang: int = 0,
             seance: int | None = None):
    """Le n-ième contact que la confirmation retient, dans l'ordre des graines."""
    trouves = [c for c in S.contacts(cle_niveau)
               if confirmation in c.confirmations
               and (seance is None or c.seance == seance)]
    if trouves:
        return trouves[min(rang, len(trouves) - 1)]
    return _exemple(cle_niveau, confirmation, rang)


# ---------------------------------------------------------------------------
# Figure — le profil de volume : où sont les niveaux, et ce qui s'y passe
# ---------------------------------------------------------------------------


def _profil_lateral(p: Panel, profil, part: float = 0.22) -> None:
    """Pose le profil de volume contre le bord droit du cadre.

    Les barres poussent vers la gauche depuis le bord : c'est la présentation
    d'usage, et elle laisse le tracé de prix lisible parce que les deux
    n'occupent pas la même bande verticale.
    """
    vmax = max(profil.volumes) or 1.0
    largeur = part * (p.x1 - p.x0)
    for prix, vol in zip(profil.prices, profil.volumes):
        prix += S.PRIX_BASE
        if vol <= 0 or not (p.y0 <= prix <= p.y1):
            continue
        p.hbar(prix, p.x1, p.x1 - largeur * vol / vmax, 3.0,
               _ramp(0.25 + 0.6 * vol / vmax),
               tip=f"{_num(prix, 2)} : {_num(vol, 0)} contrats")


def _marquer_contacts(p: Panel, lot, confirmation: str, pas: int) -> int:
    """Pose un point à chaque contact d'une séance, plein s'il est confirmé.

    Le point creux dit « le prix a touché le niveau », le point plein « et la
    condition écrite d'avance y était ». L'écart entre les deux nombres est
    tout le propos du chapitre, et il se voit ici d'un coup d'œil.
    """
    n = 0
    for c in lot:
        confirme = confirmation in c.confirmations
        p.dot(c.minute / pas, c.niveau + S.PRIX_BASE,
              "s2" if confirme else "s3", r=3.4 if confirme else 2.4,
              tip=("contact confirmé" if confirme else "contact")
                  + f" · minute {c.minute}")
        n += confirme
    return n


def _seance_de(lot, index: int):
    return [c for c in lot if c.seance == index]


def fig_profil() -> str:
    """Le profil de volume : trois niveaux calculés, et ce que le prix en fait.

    La planche répond à la question d'ordre du chapitre pour la famille du
    prix-volume. Le cadre du haut montre **d'où viennent les niveaux** : le
    profil de la première demi-séance, son point de contrôle, son aire de
    valeur, ses nœuds de faible volume. Le trait vertical marque la minute où
    les niveaux sont arrêtés — après elle, plus rien n'est recalculé, et les
    contacts sont comptés.

    Les deux cadres du bas prennent deux de ces contacts de près, avec les
    critères que la confirmation exigeait.
    """
    lot_lvn = S.contacts("lvn")
    lot_valeur = S.contacts("valeur")
    index = _seance_temoin("lvn", ("execution",))
    pas = 5

    b = _plate(614.0, "Setup · le profil de volume",
               "Les niveaux d'abord, les contacts ensuite",
               "séance " + str(index + 1))

    barres = S.seances()[index]
    profil = S.profil(index)
    va = profil.value_area()
    noeuds = profil.lvn(prominence=0.05)
    bougies = [(t, j, o + S.PRIX_BASE, h + S.PRIX_BASE,
                l + S.PRIX_BASE, c + S.PRIX_BASE)
               for t, j, o, h, l, c in _bougies(barres, 0, len(barres), pas)]
    niveaux = [v + S.PRIX_BASE for v in
               (profil.poc, va.low, va.high, *noeuds)]
    p = _cadre(b, MARGE_G, 116.0, _utile(), 188.0,
               "La séance entière, et d'où viennent les niveaux",
               _num(len(_seance_de(lot_lvn, index))
                    + len(_seance_de(lot_valeur, index)), 0) + " contacts",
               bougies, niveaux=niveaux)
    _bande_y(p, va.low + S.PRIX_BASE, va.high + S.PRIX_BASE)
    _profil_lateral(p, profil)
    p.vline(S.DEBUT / pas, "lvl strong")
    p.label(S.DEBUT / pas, p.y1, "niveaux arrêtés ici", dx=4.0, dy=12.0,
            cls="lg halo")
    for prix, nom in ((profil.poc, "POC"), (va.low, "VAL"), (va.high, "VAH")):
        p.hline(prix + S.PRIX_BASE, "lvl strong")
        p.tag(prix + S.PRIX_BASE, nom, side="left")
    # Seuls les nœuds effectivement abordés dans la séance sont nommés : le
    # profil en produit jusqu'à six, et six étiquettes empilées contre le bord
    # droit se recouvrent et masquent l'histogramme qu'elles bordent.
    compte: dict[float, int] = {}
    for c in _seance_de(lot_lvn, index):
        compte[c.niveau] = compte.get(c.niveau, 0) + 1
    nommes = sorted(compte, key=lambda v: -compte[v])[:2]
    for noeud in noeuds:
        p.hline(noeud + S.PRIX_BASE, "lvl")
    for k, noeud in enumerate(nommes):
        p.label(p.x0 + (0.34 + 0.16 * k) * (p.x1 - p.x0),
                noeud + S.PRIX_BASE, "LVN", dx=0.0, dy=-4.0,
                anchor="middle", cls="tk halo")
    confirmes = (_marquer_contacts(p, _seance_de(lot_lvn, index),
                                   "execution", pas)
                 + _marquer_contacts(p, _seance_de(lot_valeur, index),
                                     "rejet", pas))
    # Pas de graduation au bord droit : son libellé est centré sur elle et
    # déborderait de la planche, où il serait tracé sans être vu.
    p.grid_x([0.0, 26.0, 52.0], fmt=lambda v: _num(v * pas / 60.0, 1) + " h",
             label="heures de séance")

    b.annotation(MARGE_G, 62.0,
                 "point creux : le prix touche le niveau · point plein : la "
                 "confirmation écrite d'avance y était aussi")
    b.annotation(MARGE_G, 75.0,
                 "bande teintée : l'aire de valeur · histogramme de droite : "
                 "le profil de la première demi-séance")

    ecart = ECART_ZOOM
    lw = (_utile() - ecart) / 2.0
    _zoom(b, MARGE_G, 376.0, lw, 116.0,
          _exemple("lvn", "execution", seance=index),
          "lvn", "execution", "Traversée d'un nœud de faible volume", "LVN")
    _zoom(b, MARGE_G + lw + ecart, 376.0, lw, 116.0,
          _exemple("valeur", "rejet"), "valeur", "rejet",
          "Rejet du bord de valeur", "VAL")

    m_lvn = S.mesurer("lvn-execution")
    m_val = S.mesurer("valeur-rejet")
    _source(b, "Le profil de la première demi-séance est posé contre le bord "
               "droit du cadre du haut ; les trois niveaux en sont tirés, "
               "jamais choisis. Rien de ce qui suit la minute "
               + str(S.DEBUT) + " ne les modifie — c'est la condition pour "
               "que les contacts comptés soient ceux qu'un opérateur aurait "
               "vus. Sur l'ensemble des " + C._grand(float(S.SEANCES))
             + " séances, le bord de l'aire de valeur est touché "
             + _num(m_val.par_seance, 1) + " fois par séance et le rejet y "
               "est confirmé " + _num(100.0 * m_val.part_confirmee, 1)
             + " % du temps ; le nœud de faible volume est abordé "
             + _num(m_lvn.par_seance, 1) + " fois et la traversée confirmée "
             + _num(100.0 * m_lvn.part_confirmee, 1) + " %. Les deux "
               "confirmations laissent la probabilité que le prix aille dans "
               "le sens attendu à un demi ; ce qu'elles changent est le "
               "nombre d'occasions, et donc le délai.")
    return b.render("Une séance avec son profil de volume, ses niveaux, ses "
                    "contacts, et deux contacts vus de près")


FIGURES["setprofil"] = fig_profil


# ---------------------------------------------------------------------------
# Figure — la structure de Dow
# ---------------------------------------------------------------------------

def fig_structure() -> str:
    """La structure de Dow, terme à terme : les pivots, le retest, la rupture.

    La théorie de Dow se lit sur une suite de pivots, et le premier travail
    d'une figure honnête est de montrer que ces pivots sont **calculés** : un
    zigzag de seuil déclaré, appliqué au passé du prix et à rien d'autre. Les
    sommets et les creux portent le nom que le module leur donne, jamais celui
    qu'une lecture après coup leur donnerait.

    Les deux cadres du bas montrent les deux setups que la famille propose,
    et ils sont exactement contraires : le retest attend que l'ancien pivot
    tienne, la rupture qu'il cède.
    """
    index = _seance_temoin("pivot", ("rejet", "execution"))
    pas = 5
    barres = S.seances()[index]
    lot = S.contacts("pivot")

    b = _plate(614.0, "Setup · la structure de Dow",
               "Des pivots calculés, puis deux lectures contraires",
               "zigzag de " + _num(S.SEUIL_PIVOT, 0) + " points")

    bougies = [(t, j, o + S.PRIX_BASE, h + S.PRIX_BASE,
                l + S.PRIX_BASE, c + S.PRIX_BASE)
               for t, j, o, h, l, c in _bougies(barres, 0, len(barres), pas)]
    chemin = [x.cloture for x in barres]
    sw = dow.swings(chemin, S.SEUIL_PIVOT)
    noms = dow.classify(sw)
    p = _cadre(b, MARGE_G, 116.0, _utile(), 188.0,
               "Les pivots d'une séance, et les trois derniers suivis",
               str(len(sw)) + " pivots confirmés", bougies)
    # La ligne brisée des pivots : c'est elle que la théorie lit, et sans elle
    # les étiquettes flottent au-dessus des bougies sans rien relier.
    p.path([(s.index / pas, s.price + S.PRIX_BASE) for s in sw], "s2",
           dash="4 3")
    # `classify` ne nomme pas le premier sommet ni le premier creux — il n'y a
    # rien à quoi les comparer. Les noms s'alignent donc sur la fin.
    decalage = len(sw) - len(noms)
    for k, s in enumerate(sw):
        nom = noms[k - decalage].value if k >= decalage else ""
        p.dot(s.index / pas, s.price + S.PRIX_BASE, "s2", r=3.2,
              tip=f"pivot minute {s.index}")
        if nom:
            p.label(s.index / pas, s.price + S.PRIX_BASE, nom,
                    dx=-2.0, dy=-8.0 if s.is_high else 14.0,
                    anchor="middle", cls="tk halo")
    for s in sw[-S.N_PIVOTS:]:
        p.hline(s.price + S.PRIX_BASE, "lvl")
    _marquer_contacts(p, _seance_de(lot, index), "rejet", pas)
    # Pas de graduation au bord droit : son libellé est centré sur elle et
    # déborderait de la planche, où il serait tracé sans être vu.
    p.grid_x([0.0, 26.0, 52.0], fmt=lambda v: _num(v * pas / 60.0, 1) + " h",
             label="heures de séance")

    b.annotation(MARGE_G, 62.0,
                 "HH sommet plus haut · HL creux plus haut · LH sommet plus "
                 "bas · LL creux plus bas")
    b.annotation(MARGE_G, 75.0,
                 "les noms viennent du module de structure, jamais d'une "
                 "lecture après coup")

    ecart = ECART_ZOOM
    lw = (_utile() - ecart) / 2.0
    _zoom(b, MARGE_G, 376.0, lw, 116.0,
          _exemple("pivot", "rejet", seance=index),
          "pivot", "rejet", "Retest de pivot tenu", "pivot")
    _zoom(b, MARGE_G + lw + ecart, 376.0, lw, 116.0,
          _exemple("pivot", "execution", seance=index), "pivot", "execution",
          "Rupture de structure", "pivot")

    m_r = S.mesurer("pivot-rejet")
    m_e = S.mesurer("pivot-execution")
    _source(b, "Les pivots sont ceux d'un zigzag de "
             + _num(S.SEUIL_PIVOT, 0) + " points, seuil déclaré avant mesure : "
               "c'est le paramètre libre de la couche, et le fixer d'avance est "
               "ce qui interdit d'en faire un degré de liberté. Les trois "
               "derniers pivots confirmés sont suivis, comme un opérateur les "
               "garde à l'écran. Les deux lectures qu'ils autorisent sont "
               "contraires — le retest attend que le niveau tienne, la rupture "
               "qu'il cède — et le prix sans dérive leur donne raison aussi "
               "souvent à l'une qu'à l'autre : "
             + _num(100.0 * m_r.p_confirme, 1) + " % dans le sens attendu pour "
               "le retest, " + _num(100.0 * m_e.p_confirme, 1) + " % pour la "
               "rupture. Ce que la théorie de Dow apporte ici n'est donc pas "
               "une direction, c'est un niveau où poser le stop.")
    return b.render("Les pivots calculés sur une séance, puis le retest tenu et "
                    "la rupture de structure vus de près")


FIGURES["setdow"] = fig_structure


# ---------------------------------------------------------------------------
# Figure — la bande VWAP
# ---------------------------------------------------------------------------


def _bandes_vwap(p: Panel, barres, pas: int) -> None:
    """Le VWAP et ses deux premières bandes, à la minute.

    Le VWAP est une **vraie** moyenne pondérée par le volume, comme celui que
    la mesure emploie : la moyenne simple du prix en diffère peu, mais elle
    n'est pas ce qu'une plateforme affiche, et une figure de setup doit
    montrer ce que l'opérateur voit.
    """
    somme = poids = carre = 0.0
    lignes = {1: ([], []), 2: ([], [])}
    milieu = []
    for i, bar in enumerate(barres):
        typique = (bar.haut + bar.bas + bar.cloture) / 3.0
        somme += typique * bar.volume
        carre += typique * typique * bar.volume
        poids += bar.volume
        moyenne = somme / poids
        sigma = math.sqrt(max(carre / poids - moyenne * moyenne, 0.0))
        if i < 30:
            continue
        milieu.append((i / pas, moyenne + S.PRIX_BASE))
        for k in (1, 2):
            lignes[k][0].append((i / pas, moyenne + k * sigma + S.PRIX_BASE))
            lignes[k][1].append((i / pas, moyenne - k * sigma + S.PRIX_BASE))
    p.path(milieu, "s2")
    for k, dash in ((1, "3 3"), (2, "")):
        for serie in lignes[k]:
            p.path(serie, "s3", dash=dash)
    # Les bandes portent leur nom dans le cadre : une légende posée sous
    # l'axe venait sur l'intitulé des abscisses, et rien n'y distinguait
    # deux entrées de même classe que seul le tireté sépare.
    for k in (1, 2):
        for serie, cote in zip(lignes[k], (+1, -1)):
            if not serie:
                continue
            x, y = serie[len(serie) // 3]
            p.label(x, y, ("+" if cote > 0 else "−") + str(k) + " σ",
                    dx=0.0, dy=-4.0 if cote > 0 else 12.0, anchor="middle",
                    cls="tk halo")


def fig_vwap() -> str:
    """La deuxième bande VWAP : un niveau qui bouge, et deux lectures.

    Toutes les autres familles posent un niveau fixe. Celle-ci pose un niveau
    **mobile**, recalculé à chaque minute sur tout le passé de la séance, et
    c'est ce qui la distingue : le prix ne revient pas sur la bande, c'est la
    bande qui vient à lui autant qu'il va vers elle.

    Les deux lectures sont contraires, comme pour la structure : la bande
    rejetée annonce le retour au coût moyen, la bande franchie l'installation
    de la déviation.
    """
    index = _seance_temoin("vwap", ("rejet", "execution"))
    pas = 5
    barres = S.seances()[index]
    lot = S.contacts("vwap")

    b = _plate(614.0, "Setup · la bande VWAP",
               "Un niveau qui se recalcule à chaque minute",
               "bandes à un et deux écarts-types")

    bougies = [(t, j, o + S.PRIX_BASE, h + S.PRIX_BASE,
                l + S.PRIX_BASE, c + S.PRIX_BASE)
               for t, j, o, h, l, c in _bougies(barres, 0, len(barres), pas)]
    p = _cadre(b, MARGE_G, 116.0, _utile(), 188.0,
               "Le VWAP de la séance et ses deux bandes",
               str(len(_seance_de(lot, index))) + " touches de la deuxième "
               "bande", bougies)
    _bandes_vwap(p, barres, pas)
    _marquer_contacts(p, _seance_de(lot, index), "rejet", pas)
    # Pas de graduation au bord droit : son libellé est centré sur elle et
    # déborderait de la planche, où il serait tracé sans être vu.
    p.grid_x([0.0, 26.0, 52.0], fmt=lambda v: _num(v * pas / 60.0, 1) + " h",
             label="heures de séance")

    b.annotation(MARGE_G, 62.0,
                 "trait plein clair : le VWAP · tirets : ±1 σ · trait plein "
                 "sombre : ±2 σ, le niveau lu")
    b.annotation(MARGE_G, 75.0,
                 "la bande se déplace à chaque minute ; le contact est compté "
                 "quand la barre la traverse")

    ecart = ECART_ZOOM
    lw = (_utile() - ecart) / 2.0
    _zoom(b, MARGE_G, 376.0, lw, 116.0,
          _exemple("vwap", "rejet", seance=index),
          "vwap", "rejet", "Rejet de la deuxième bande", "2 σ")
    _zoom(b, MARGE_G + lw + ecart, 376.0, lw, 116.0,
          _exemple("vwap", "execution", seance=index), "vwap", "execution",
          "Sortie de bande", "2 σ")

    m_r = S.mesurer("vwap-rejet")
    m_e = S.mesurer("vwap-execution")
    _source(b, "La deuxième bande est touchée "
             + _num(m_r.par_seance, 1) + " fois par séance sur les "
             + C._grand(float(S.SEANCES)) + " séances simulées — c'est la "
               "famille la plus généreuse en occasions du catalogue, et c'est "
               "ce qui en fait la seule dont le délai d'établissement se "
               "compte en années plutôt qu'en siècles. Le rejet y est confirmé "
             + _num(100.0 * m_r.part_confirmee, 1) + " % du temps, la sortie "
             + _num(100.0 * m_e.part_confirmee, 1) + " %. Ni l'une ni l'autre "
               "ne déplace la suite du prix : "
             + _num(100.0 * m_r.p_confirme, 1) + " % et "
             + _num(100.0 * m_e.p_confirme, 1) + " % dans le sens attendu, "
               "quand le hasard en donne cinquante. Le fait qu'une bande soit "
               "rare ne la rend pas informative — elle est rare parce que "
               "deux écarts-types sont rares, ce qui est une propriété de la "
               "loi normale et non du marché.")
    return b.render("Le VWAP sur une séance et ses bandes, avec le rejet et la "
                    "sortie de la deuxième bande vus de près")


FIGURES["setvwap"] = fig_vwap


# ---------------------------------------------------------------------------
# Figure — ce que la confirmation coûte
# ---------------------------------------------------------------------------


def _ordre_cout():
    """Les douze setups, du moins coûteux au plus coûteux à établir.

    L'ordre est celui du délai avec confirmation, et il n'est écrit nulle
    part : changer un seuil de confirmation réordonne la figure sans qu'une
    ligne de prose ait à bouger.
    """
    return sorted(S.SETUPS, key=lambda x: S.cout(x.cle).annees_retenu)


def _duree(annees: float) -> str:
    """Une durée de graduation, au singulier quand elle vaut un."""
    if annees < 1000.0:
        return _num(annees, 0) + (" an" if annees == 1.0 else " ans")
    milliers = annees / 1000.0
    return _num(milliers, 0) + (" millénaire" if milliers == 1.0
                                else " millénaires")


def fig_cout() -> str:
    """Le prix d'une confirmation, en années puis en dérive.

    Le cadre du haut donne, pour chaque setup, le délai d'établissement sans
    confirmation puis avec. Le segment qui joint les deux **est** le coût : à
    décisions requises inchangées, exiger la confirmation ne fait que diviser
    le débit d'occasions, et le délai est leur quotient.

    Le cadre du bas convertit ce coût en la seule monnaie qui compte — la
    dérive que la confirmation devrait apporter pour se rembourser — et la
    compare au domaine que le document nº 1 tient pour plausible.
    """
    setups = _ordre_cout()
    n = len(setups)
    basse, haute = seuil.PLAUSIBLE_DRIFT_PER_HOUR

    b = _plate(700.0, "Setup · le prix d'une confirmation",
               "Mêmes décisions requises, moins d'occasions pour les obtenir",
               "échelle logarithmique")

    # --- le délai, de brut à confirmé ------------------------------------
    couts = [S.cout(x.cle) for x in setups]
    lo = 10.0 ** math.floor(math.log10(min(c.annees_brut for c in couts)))
    hi = 10.0 ** math.ceil(math.log10(max(c.annees_retenu for c in couts)))
    marge = 202.0
    p = Panel(b, MARGE_G + marge, 116.0, _utile() - marge, 18.0 * n,
              "Le délai, sans puis avec la confirmation",
              "×" + _num(min(c.facteur for c in couts), 1) + " à ×"
              + _num(max(c.facteur for c in couts), 0))
    p.domain(lo, hi, -0.6, n - 0.4, xlog=True)
    p.frame()
    ticks = []
    v = lo
    while v <= hi + 1e-9:
        ticks.append(v)
        v *= 10.0
    # Une graduation dont le libellé déborderait du cadre est retirée : elle
    # serait tracée hors de la planche, où elle existe sans se voir.
    ticks = [v for v in ticks if p.sx(v) <= p.x + p.w - 34.0]
    p.grid_x(ticks, fmt=_duree, rules=True, label="délai d'établissement")
    p.band_x(max(lo, C.CARRIERE_ANS), hi, "band")
    p.vline(C.CARRIERE_ANS, "lvl strong")
    p.label(C.CARRIERE_ANS, n - 0.4, "une carrière", dx=4.0, dy=10.0,
            cls="tk halo")
    for k, (x, c) in enumerate(zip(setups, couts)):
        y = n - 1 - k
        p.path([(c.annees_brut, y), (c.annees_retenu, y)], "s3")
        p.dot(c.annees_brut, y, "s3", r=3.0,
              tip="sans confirmation : " + C._ans(c.annees_brut))
        p.dot(c.annees_retenu, y, "s2", r=4.0,
              tip="avec confirmation : " + C._ans(c.annees_retenu))
        b.add(f'<text class="lg" x="{MARGE_G + marge - 8:.1f}" '
              f'y="{p.sy(y) + 3.5:.1f}" text-anchor="end">'
              f'{_esc(x.nom)}</text>')

    b.annotation(MARGE_G, 62.0,
                 "point creux : le contact seul · point plein : la "
                 "confirmation exigée")
    b.annotation(MARGE_G, 75.0,
                 "la bande de droite couvre ce qu'une carrière ne suffit plus "
                 "à établir")

    # --- la dérive compensatrice ------------------------------------------
    y2 = 116.0 + 18.0 * n + 92.0
    mus = [S.derive_compensatrice(x.cle) for x in setups]
    p2 = Panel(b, MARGE_G + marge, y2, _utile() - marge, 18.0 * n,
               "La dérive qui rembourserait cette attente", "")
    p2.domain(0.0, max(max(mus) * 1.15, haute * 1.05), -0.6, n - 0.4)
    p2.frame()
    p2.grid_x([0.0, basse, 1.0, 2.0, haute], fmt=lambda v: _num(v, 1),
              label="points par heure")
    p2.band_x(basse, haute, "zone")
    for k, (x, mu) in enumerate(zip(setups, mus)):
        y = n - 1 - k
        p2.hbar(y, 0.0, mu, 9.0, "s1f" if mu <= basse else "s3f",
                tip=x.nom + " : " + _num(mu, 2) + " pt/h")
        b.add(f'<text class="lg" x="{MARGE_G + marge - 8:.1f}" '
              f'y="{p2.sy(y) + 3.5:.1f}" text-anchor="end">'
              f'{_esc(x.nom)}</text>')

    b.annotation(MARGE_G, y2 - 40.0,
                 "bande teintée : le domaine de dérive que le document "
                 "n° 1 tient pour plausible")
    b.annotation(MARGE_G, y2 - 27.0,
                 "une barre qui s'arrête avant la bande se rembourse d'une "
                 "dérive ordinaire")

    v = S.values()
    _source(b, "Le nombre de décisions requises ne dépend que de la "
               "géométrie — stop à l'écart-type d'horizon, cible à deux fois "
               "le stop, friction de référence — et la confirmation n'en "
               "touche aucun terme. Le segment du haut est donc entièrement "
               "un effet de débit : la confirmation retire de "
             + v["u_part_max"] + " à " + v["u_part_min"] + " des contacts, et "
               "multiplie l'attente d'autant, de ×" + v["u_facteur_min"]
             + " à ×" + v["u_facteur_max"] + ". Le cadre du bas dit ce qu'il "
               "faudrait pour que ce soit un bon échange : que la "
               "confirmation déplace la dérive de " + v["u_mu_min"] + " à "
             + v["u_mu_max"] + " point par heure selon le setup. Aucune de ces "
               "valeurs ne sort du domaine plausible, ce qui est la seule "
               "bonne nouvelle du chapitre — mais aucune n'est acquise non "
               "plus : rien dans les données mesurées ici ne dit qu'une "
               "confirmation déplace la dérive d'un centième de point. La "
               "confirmation "
               "la plus exigeante, " + v["u_pire"] + ", est aussi celle qui "
               "réclame le plus.")
    return b.render("Le délai de preuve de douze setups, sans puis avec leur "
                    "confirmation, et la dérive qui rembourserait cette "
                    "attente")


FIGURES["setcout"] = fig_cout


# ---------------------------------------------------------------------------
# Figure — le relief du coût
# ---------------------------------------------------------------------------

#: Parts confirmées et débits de contacts explorés par la surface. Les deux
#: suites sont **décroissantes** : en projection isométrique le coin le plus
#: éloigné est celui des premiers indices, et y placer le maximum fait monter
#: le relief vers l'horizon, ce qui se lit. À l'ordre inverse, le sommet
#: tombe au premier plan, où deux points de profondeur différente paraissent
#: à la même hauteur d'écran.
PARTS = (0.005, 0.01, 0.02, 0.05, 0.10, 0.25, 0.60, 1.0)
DEBITS = (0.5, 1.0, 2.0, 4.0, 8.0, 16.0)

#: Horizon auquel la surface est calculée. Une heure : c'est celui de la
#: famille du profil de volume, la plus fournie du catalogue de setups.
HORIZON_SURFACE = 60.0


def fig_relief() -> str:
    """Le relief du délai, selon la sévérité de la confirmation et le débit.

    Deux axes, et ils ne se compensent jamais : durcir la confirmation et
    raréfier les contacts poussent tous deux le délai vers le haut. C'est le
    même relief à une seule pente que celui du catalogue, et il dit la même
    chose d'une autre façon — **il n'existe pas de confirmation gratuite**.
    """
    b = _plate(506.0, "Setup · le relief du coût",
               "Ce qu'une confirmation coûte, sur deux axes",
               "hauteur : délai, en années")

    decisions = C.decisions_pour(HORIZON_SURFACE)
    z = [[math.log10(max(decisions / (part * debit * C.SEANCES_PAR_AN), 0.02))
          for debit in DEBITS] for part in PARTS]
    _surface(b, 0.52 * W, 214.0, z, -1.0, 4.0,
             cx=30.0, cy=15.0, cz=150.0,
             row_labels=[_num(100.0 * part, 1 if part < 0.05 else 0) + " %"
                         for part in PARTS],
             col_labels=[_num(d, 1 if d < 1 else 0) for d in DEBITS],
             z_ticks=[(-1.0, "1 mois"), (0.0, "1 an"),
                      (math.log10(C.CARRIERE_ANS), "carrière"),
                      (2.0, "1 siècle"), (4.0, "100 siècles")],
             tip="{v:.2f} en log d'années")

    b.annotation(0.0, 428.0,
                 "arête gauche : part des contacts que la confirmation "
                 "retient · arête droite : contacts par séance")
    b.annotation(0.0, 444.0,
                 "au premier plan, une confirmation qui ne retient rien sur "
                 "un niveau qu'on ne touche presque jamais")

    v = S.values()
    _source(b, "La hauteur est le délai d'établissement, en échelle "
               "logarithmique : chaque graduation vaut dix fois la "
               "précédente. Le nombre de décisions requises est celui d'une "
               "lecture d'une heure, et il ne varie pas sur la surface — "
               "seule varie la vitesse à laquelle le marché les fournit. Les "
               "douze setups mesurés tombent tous dans la moitié gauche du "
               "relief : leurs confirmations retiennent entre "
             + v["u_part_min"] + " et " + v["u_part_max"] + " des contacts. "
               "Le plan de la carrière coupe la surface vers une part d'un "
               "dixième pour un niveau touché dix fois par séance — "
               "c'est-à-dire tout juste au bord de ce que les familles les "
               "plus fournies atteignent. Durcir la confirmation d'un cran "
               "fait passer le délai de l'autre côté du plan, et il n'existe "
               "aucune façon de le rattraper par le débit : les deux axes "
               "poussent dans le même sens.")
    return b.render("Surface du délai de preuve selon la part de contacts "
                    "retenue et le nombre de contacts par séance")


FIGURES["setrelief"] = fig_relief


def render_all() -> dict[str, str]:
    """Toutes les figures du module, par clé de gabarit."""
    return {cle: fn() for cle, fn in FIGURES.items()}
