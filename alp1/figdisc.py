"""Les figures du papier sur l'edge discrétionnaire.

Trois surfaces isométriques et quatre planches plates, toutes bâties sur le
même gabarit : un bandeau d'en-tête, une zone de tracé, et une bande de pied
réservée que rien ne traverse. Cette discipline de gabarit n'est pas
cosmétique — c'est elle qui empêche une légende de venir mordre sur un
libellé d'axe, faute la plus fréquente des figures produites par programme.

**Une seule couleur porte du sens.** L'accent est le bleu ; les grandeurs
ordonnées — années, probabilités, seuils — passent par la rampe séquentielle
d'une seule teinte, jamais par des teintes catégorielles, qui coderaient de
l'ordre avec un canal qui n'en porte pas. Le rouge est réservé au seul cas où
il signifie quelque chose : le pôle négatif d'une échelle divergente. Tout le
reste est neutre.

Aucune couleur n'est écrite ici : les figures posent des classes et
`figcss.py` décide. C'est ce qui leur permet de rester lisibles sur les deux
fonds du document, et c'est gardé par `tests/test_figures_all.py`.
"""

from __future__ import annotations

import math
from functools import lru_cache

from .costs import deflated_threshold_sharpe
from .entropy import trades_for_information
from .figterm import Board, Panel, _esc, _num, _signed
from .journal import LEVERS, synthesise
from .operator import evaluate

#: Séances simulées pour les figures qui montrent un journal. Assez pour que
#: le signe de l'espérance mécanique soit stable.
SESSIONS = 400

#: Séances de bourse par an — la constante qui traduit un nombre de décisions
#: en années de carrière.
SESSIONS_PER_YEAR = 252

#: Le recensement de l'opérateur : quatre leviers, donc seize configurations.
K_LEVERS = len(LEVERS)

#: Largeur commune. Toutes les planches la partagent, ce qui donne au
#: document un rythme régulier plutôt qu'une suite de cadres dépareillés.
W = 660.0

#: Hauteur du bandeau d'en-tête et de la bande de pied. Réservées : la zone
#: de tracé ne s'y étend jamais.
HEAD = 46.0
FOOT = 30.0


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _trades_for_threshold(sharpe: float, budget: float) -> float:
    """Décisions requises, la plus exigeante des deux routes.

    La route 1 est le test ordinaire sur la moyenne, `(z_α + z_β)²/SR²` ; elle
    vaut même à configuration unique. La route 2 est la taxe de sélection,
    `2·ln B/SR²` ; elle s'annule à configuration unique, parce qu'il n'y a
    alors rien à sélectionner. C'est leur maximum qu'un opérateur doit
    atteindre, et le module `report10` calcule exactement la même chose.

    Le budget était borné par `max(budget, 2.0)`, ce qui fabriquait une taxe
    là où il n'y en a aucune et faisait afficher à la surface plus d'un an à
    zéro levier. La borne est levée ; le plancher est maintenant celui du test
    ordinaire, qui est un vrai plancher.
    """
    if sharpe <= 0.0:
        return math.inf
    from .costs import trades_for_significance
    return max(float(trades_for_significance(sharpe, 1.0)),
               2.0 * math.log(max(budget, 1.0)) / (sharpe ** 2))


def _pourcent(p: float) -> str:
    """Une probabilité de queue, lisible sur cinq ordres de grandeur.

    Le pour-cent cesse de se lire sous le millième : « 0,0004 % » ne dit rien
    à personne, quand « 4 par million » se compare tout de suite à ce qu'on
    croise dans la vie.
    """
    if p >= 0.01:
        return _num(p * 100.0, 1) + " %"
    if p >= 1e-5:
        return _num(p * 100.0, 3) + " %"
    return _num(p * 1e6, 1) + " par million"


def _ramp(u: float) -> str:
    """Classe de la rampe séquentielle pour une valeur normalisée dans [0, 1]."""
    return f"hm{min(7, max(0, int(round(u * 7.0))))}"


# ---------------------------------------------------------------------------
# Le gabarit partagé
# ---------------------------------------------------------------------------


def _plate(height: float, eyebrow: str, title: str, readout: str = "",
           width: float = W) -> Board:
    """Ouvre une planche et dessine son bandeau d'en-tête.

    Le surtitre est en capitales espacées, le titre en romain, la lecture
    chiffrée alignée à droite. Un filet ferme le bandeau. Rien de ce qui suit
    ne remonte au-dessus.
    """
    b = Board(width, height)
    b.add(f'<text class="tk" x="0" y="11" '
          f'style="letter-spacing:.11em">{_esc(eyebrow.upper())}</text>')
    b.add(f'<text class="hdr" x="0" y="31" '
          f'style="letter-spacing:0;text-transform:none;font-size:13px">'
          f'{_esc(title)}</text>')
    if readout:
        b.add(f'<text class="tk" x="{width:.1f}" y="31" text-anchor="end">'
              f'{_esc(readout)}</text>')
    b.add(f'<line class="ba" x1="0" y1="{HEAD - 8:.1f}" '
          f'x2="{width:.1f}" y2="{HEAD - 8:.1f}"/>')
    return b


def _source(board: Board, text: str) -> None:
    """Pose la ligne de lecture dans la bande de pied.

    Elle porte la classe `cap`, qui la déclare comme pied de figure : c'est
    ce qui la fait extraire du SVG et rendre en texte sous la légende quand
    le document est construit. Dans un aperçu isolé, elle reste à sa place et ne heurte
    rien, la bande lui étant réservée.
    """
    board.add(f'<text class="lg cap" x="0" y="{board.height - 8:.1f}">'
              f'{_esc(text)}</text>')


def _scale_legend(board: Board, x: float, y: float, lo: str, hi: str,
                  label: str, width: float = 132.0) -> None:
    """Légende d'échelle pour une rampe séquentielle.

    Une rampe continue exige sa légende : sans elle, la teinte n'est pas
    déchiffrable, et le lecteur ne dispose d'aucun moyen de convertir une
    nuance en grandeur.
    """
    step = width / 8.0
    for k in range(8):
        board.add(f'<rect class="{_ramp(k / 7.0)}" x="{x + k * step:.1f}" '
                  f'y="{y - 6:.1f}" width="{step:.1f}" height="8"/>')
    board.add(f'<text class="tk" x="{x:.1f}" y="{y + 14:.1f}">{_esc(lo)}</text>')
    board.add(f'<text class="tk" x="{x + width:.1f}" y="{y + 14:.1f}" '
              f'text-anchor="end">{_esc(hi)}</text>')
    board.add(f'<text class="lg" x="{x + width + 14:.1f}" y="{y + 1:.1f}">'
              f'{_esc(label)}</text>')


def _bilineaire(z: list[list[float]], facteur: int) -> list[list[float]]:
    """Densifie une grille par interpolation bilinéaire.

    Le nuage de points a besoin de bien plus d'échantillons que la grille de
    données n'en porte : c'est la densité qui dessine la forme. L'interpolation
    n'invente rien — entre deux mailles connues, elle ne fait que rendre la
    surface que la projection en mailles pleines aurait peinte.
    """
    ni, nj = len(z), len(z[0])
    mi, mj = (ni - 1) * facteur + 1, (nj - 1) * facteur + 1
    out = []
    for a in range(mi):
        fa, ra = divmod(a, facteur)
        fa = min(fa, ni - 2) if ni > 1 else 0
        ta = (a - fa * facteur) / facteur
        ligne = []
        for b in range(mj):
            fb = min(b // facteur, nj - 2) if nj > 1 else 0
            tb = (b - fb * facteur) / facteur
            v = ((1 - ta) * (1 - tb) * z[fa][fb]
                 + ta * (1 - tb) * z[fa + 1][fb]
                 + (1 - ta) * tb * z[fa][fb + 1]
                 + ta * tb * z[fa + 1][fb + 1])
            ligne.append(v)
        out.append(ligne)
    return out


#: Échantillons visés par axe dans le nuage. Trente-quatre suffisent à ce que
#: la surface se lise comme un relief continu ; au-delà, le poids du document
#: monte sans que la forme gagne.
NUAGE_CIBLE = 34

#: Bandes de profondeur peintes de l'arrière vers l'avant. Le nuage est groupé
#: par bande et par classe de rampe, ce qui remplace des milliers de cercles
#: par quelques dizaines de tracés — sans quoi une seule surface pèserait
#: davantage qu'un chapitre entier.
NUAGE_BANDES = 12


def _surface(board: Board, ox: float, oy: float, z: list[list[float]],
             zlo: float, zhi: float, *, cx: float, cy: float, cz: float,
             row_labels: list[str], col_labels: list[str],
             z_ticks: list[tuple[float, str]], tip: str = "{v:+.3f}",
             classify=None, zero: float = 0.0) -> None:
    """Surface en **nuage de points**, munie d'une échine de hauteur.

    Le relief n'est pas peint en mailles pleines mais échantillonné : quelques
    centaines de points posés sur la surface, dont la taille et la teinte
    suivent la hauteur. Deux raisons, et aucune n'est décorative.

    La première est que le nuage **laisse voir à travers**. Une maille pleine
    cache ce qui est derrière elle ; un versant arrière plus haut que le
    versant avant disparaît. Le nuage, lui, laisse le relief lointain
    transparaître entre les points du relief proche, et c'est exactement ce
    qu'une surface à deux bosses demande.

    La seconde est qu'un point n'a pas de bordure. Les mailles pleines
    devaient être séparées par un filet couleur papier, faute de quoi la
    surface se lisait comme un aplat ; ce filet mangeait la moitié de la
    surface dès que la grille était fine, et interdisait donc de raffiner.

    Trois repères restent, et ils portent toute la lecture chiffrée : le
    **sol** en grille de filets, les **montants** aux quatre coins, et
    l'**échine** verticale graduée à gauche. Sans elle, une projection
    isométrique est ambiguë et aucune élévation ne se convertit en grandeur.

    Les sommets de la grille de données gardent chacun un cercle et son
    infobulle : le nuage donne la forme, les sommets donnent les nombres.
    """
    ni, nj = len(z), len(z[0])
    span = (zhi - zlo) or 1.0

    if classify is None:
        def classify(v: float) -> str:
            return _ramp((min(max(v, zlo), zhi) - zlo) / span)

    def proj(i: float, j: float, val: float) -> tuple[float, float]:
        val = min(max(val, zlo), zhi)
        return (ox + (i - j) * cx,
                oy + (i + j) * cy - (val - zlo) * cz / span)

    floor_z = min(max(zero, zlo), zhi)

    # Le sol : une grille de filets, pas un aplat. On voit où sont les mailles
    # sans que le sol dispute la lecture à la surface.
    for i in range(ni):
        a, bb = proj(i, 0, floor_z), proj(i, nj - 1, floor_z)
        board.add(f'<line class="floor" x1="{a[0]:.1f}" y1="{a[1]:.1f}" '
                  f'x2="{bb[0]:.1f}" y2="{bb[1]:.1f}"/>')
    for j in range(nj):
        a, bb = proj(0, j, floor_z), proj(ni - 1, j, floor_z)
        board.add(f'<line class="floor" x1="{a[0]:.1f}" y1="{a[1]:.1f}" '
                  f'x2="{bb[0]:.1f}" y2="{bb[1]:.1f}"/>')

    # Montants aux quatre coins : la référence au sol lève l'ambiguïté.
    for (i, j) in ((0, 0), (ni - 1, 0), (ni - 1, nj - 1), (0, nj - 1)):
        fx, fy = proj(i, j, floor_z)
        sx, sy = proj(i, j, z[i][j])
        board.add(f'<line class="post" x1="{fx:.1f}" y1="{fy:.1f}" '
                  f'x2="{sx:.1f}" y2="{sy:.1f}"/>')

    # Le nuage. Densification bilinéaire, puis regroupement par bande de
    # profondeur et par classe : l'arrière est peint avant l'avant.
    facteur = max(1, round(NUAGE_CIBLE / max(ni - 1, nj - 1, 1)))
    dense = _bilineaire(z, facteur)
    mi, mj = len(dense), len(dense[0])
    seaux: dict[tuple[int, str], list[tuple[float, float, float]]] = {}
    for a in range(mi):
        for b in range(mj):
            val = dense[a][b]
            u = (min(max(val, zlo), zhi) - zlo) / span
            x, y = proj(a / facteur, b / facteur, val)
            bande = int((a + b) / (mi + mj - 2 or 1) * (NUAGE_BANDES - 1))
            seaux.setdefault((bande, classify(val)), []).append((x, y, u))
    for (bande, cls), pts in sorted(seaux.items()):
        # Un point par « M x,y h.01 » : le bout rond du trait fait le disque,
        # et l'épaisseur porte la hauteur. Quelques dizaines de tracés
        # remplacent ainsi des milliers de cercles.
        r = 0.9 + 1.6 * (sum(p[2] for p in pts) / len(pts))
        d = "".join(f"M{x:.1f},{y:.1f}h.01" for x, y, _ in pts)
        board.add(f'<path class="nuage {cls}" stroke-width="{2 * r:.2f}" '
                  f'd="{d}"/>')

    # Les sommets de la grille de données : le nuage donne la forme, ces
    # points donnent les nombres.
    sommets = []
    for i in range(ni):
        for j in range(nj):
            sommets.append((i + j, i, j))
    for _, i, j in sorted(sommets):
        x, y = proj(i, j, z[i][j])
        board.add(f'<circle class="noeud {classify(z[i][j])}" cx="{x:.1f}" '
                  f'cy="{y:.1f}" r="2.6">'
                  f'<title>{_esc(tip.format(v=z[i][j]))}</title></circle>')

    # L'échine de hauteur, à gauche du coin le plus à gauche. Sans
    # graduation, on ne la trace pas : un axe nu se lit comme inachevé. Le
    # garde porte sur ce bloc seul — les libellés d'arêtes qui suivent sont
    # rendus dans tous les cas.
    if z_ticks:
        edge = ox - (nj - 1) * cx - 34.0
        top = proj(0, nj - 1, zhi)[1]
        bot = proj(0, nj - 1, zlo)[1]
        board.add(f'<line class="ba" x1="{edge:.1f}" y1="{top:.1f}" '
                  f'x2="{edge:.1f}" y2="{bot:.1f}"/>')
    for val, lab in z_ticks:
        yy = proj(0, nj - 1, val)[1]
        board.add(f'<line class="ba" x1="{edge:.1f}" y1="{yy:.1f}" '
                  f'x2="{edge + 5:.1f}" y2="{yy:.1f}"/>')
        board.add(f'<text class="tk" x="{edge - 5:.1f}" y="{yy + 3.5:.1f}" '
                  f'text-anchor="end">{_esc(lab)}</text>')

    # Libellés des deux arêtes du sol. Les deux séries convergent
    # géométriquement au coin avant — le dernier libellé de ligne et le dernier
    # libellé de colonne y occupent le même point. On les sépare en les posant
    # sur deux lignes de base distinctes, ce qu'aucun décalage horizontal ne
    # ferait puisque la convergence est exacte.
    for k, lab in enumerate(row_labels):
        if not lab:
            continue
        x, y = proj(k, nj - 1, floor_z)
        board.add(f'<text class="tk halo" x="{x - 11:.1f}" y="{y + 15:.1f}" '
                  f'text-anchor="end">{_esc(lab)}</text>')
    for k, lab in enumerate(col_labels):
        if not lab:
            continue
        x, y = proj(ni - 1, k, floor_z)
        board.add(f'<text class="tk halo" x="{x + 11:.1f}" y="{y + 26:.1f}">'
                  f'{_esc(lab)}</text>')


@lru_cache(maxsize=1)
def _calibration() -> tuple[tuple[float, float, int, float], ...]:
    """La courbe de calibration : clairvoyance plantée → lois battues.

    C'est le contrôle qui autorise à publier quoi que ce soit d'autre. Un
    appareil qui déclare un avantage sur un opérateur sans compétence ne
    mesure rien, et la seule façon de le savoir est de le lui demander.
    """
    out = []
    for skill in (0.0, 0.10, 0.20, 0.30, 0.45, 0.60):
        j = synthesise(skill=skill, n_sessions=SESSIONS)
        v = evaluate(j, draws=200)
        out.append((skill, j.skill_bits or 0.0, len(v.beaten), v.sharpe_trade))
    return tuple(out)


# ---------------------------------------------------------------------------
# Figure 1 — la surface du mur
# ---------------------------------------------------------------------------


def fig_wall() -> str:
    """Années requises selon les leviers ouverts et le Sharpe revendiqué.

    La surface répond à la question que pose tout allocataire : combien de
    temps avant de savoir ?

    L'arête des leviers y est **exactement plate jusqu'au quatrième**, et
    c'est un fait et non une approximation : tant que la taxe de sélection
    reste sous l'exigence du test ordinaire, ouvrir un levier ne coûte rien
    de plus que ce qu'il faut de toute façon. Il faut dépasser vingt-deux
    configurations pour qu'elle passe devant. L'arête du Sharpe, elle, va du
    simple au sextuple sur la même largeur de cadre.

    La version précédente bornait le budget à deux essais, ce qui donnait à
    zéro levier une taxe inexistante et faisait monter l'arête dès le premier
    pas. La légende parlait alors d'une arête « presque plate » — vraie du
    bornage, pas de la donnée.
    """
    ks = [0, 2, 4, 6]
    srs = [0.05, 0.075, 0.10, 0.15]
    # Le pas de deux leviers est conservé : c'est la lecture du cadre, et le
    # palier se voit d'autant mieux qu'il couvre les deux premiers points.
    z = [[min(6.0, _trades_for_threshold(sr, 2.0 ** k)
              / (2 * SESSIONS_PER_YEAR)) for sr in srs] for k in ks]

    b = _plate(384, "Mur d'échantillon", "Le mur, en années de carrière",
               "deux décisions par jour")
    _scale_legend(b, 0, 62, "immédiat", "6 ans et plus", "années requises")
    _surface(b, 330, 232, z, 0.0, 6.0, cx=58.0, cy=13.0, cz=185.0,
             row_labels=[f"k = {k}" for k in ks],
             col_labels=[f"SR {_num(sr, 3)}" for sr in srs],
             z_ticks=[(0.0, "0"), (1.0, "1 an"), (3.0, "3 ans"), (6.0, "6 ans")],
             tip="{v:.1f} an(s)")
    _source(b, "Arête gauche : leviers discrétionnaires ouverts. Arête droite : "
               "Sharpe revendiqué par décision. La hauteur est la plus "
               "exigeante des deux routes — le test ordinaire sur la moyenne "
               "et la taxe de sélection — plafonnée à six ans, à deux "
               "décisions par séance. L'arête des leviers est plate jusqu'au "
               "quatrième parce que la taxe y reste sous l'exigence du test "
               "ordinaire : ouvrir ces leviers ne coûte rien de plus que ce "
               "qu'il faut de toute façon.")
    return b.render(
        "Surface du nombre d années requises selon les leviers ouverts et le "
        "Sharpe revendiqué par décision")


# ---------------------------------------------------------------------------
# Figure 3 — le plan d'espérance, sans puis avec clairvoyance
# ---------------------------------------------------------------------------


def fig_plane() -> str:
    """L'espérance selon la sélectivité et la mise, sans puis avec information.

    À gauche, l'opérateur sans clairvoyance : la surface n'a aucune forme.
    Elle erre entre −0,124 et +0,044 R, et elle passe au positif sur une
    ligne — ce qui est la démonstration du propos et non son exception : à
    cette taille d'échantillon, le bruit de la mesure dépasse largement ce
    que la sélectivité pourrait produire. Le long de l'axe de la mise elle
    est exactement proportionnelle, la taille multipliant une espérance sans
    jamais en créer. C'est le théorème d'arrêt optionnel, transposé du choix
    des barrières au choix des trades.
    À droite, le même opérateur muni d'une clairvoyance : la surface
    s'incline, et selon l'axe de la sélectivité.

    L'échelle est divergente et non séquentielle, car la grandeur est signée
    et le zéro est la frontière qui décide.
    """
    selectivity = [1.00, 0.75, 0.50, 0.25]
    sizing = [0.5, 1.0, 1.5, 2.0]

    def build(skill: float) -> list[list[float]]:
        j = synthesise(skill=skill, n_sessions=SESSIONS)
        ranked = sorted(j.decisions, key=lambda d: (not d.taken, d.seq))
        rows = []
        for part in selectivity:
            n = max(1, int(round(part * j.n_eligible)))
            m = sum(d.net_r or 0.0 for d in ranked[:n]) / n
            rows.append([m * size for size in sizing])
        return rows

    z_null, z_edge = build(0.0), build(0.55)

    #: Largeur de la bande neutre, en unités de risque. Le seuil est une
    #: grandeur économique — en deçà, l'espérance ne finance rien — et non une
    #: fraction de l'étendue observée.
    NEUTRE = 0.02

    def etendue(z: list[list[float]]) -> tuple[float, float]:
        plat = [v for r in z for v in r]
        return min(plat), max(plat)

    def cadre(z: list[list[float]]) -> tuple[float, float]:
        """Le domaine de hauteur d'un cadre, déduit de ses propres données.

        Une marge de six pour cent, et le zéro toujours inclus parce que
        c'est la frontière que la couleur code.
        """
        lo, hi = etendue(z)
        marge = (hi - lo) * 0.06 or 0.01
        return min(lo - marge, 0.0), max(hi + marge, 0.0)

    def graduations(lo: float, hi: float) -> list[tuple[float, str]]:
        """Trois à cinq valeurs rondes dans le domaine, zéro compris."""
        for pas in (0.02, 0.05, 0.10, 0.25, 0.50, 1.00):
            k0, k1 = math.ceil(lo / pas), math.floor(hi / pas)
            if k1 - k0 <= 4:
                break
        return [(pas * k, _num(pas * k, 2) + " R")
                for k in range(k0, k1 + 1)]

    b = _plate(386, "Invariance",
               "Espérance selon la sélectivité et la mise",
               "chaque cadre porte sa propre échelle")
    for idx, (sub, z) in enumerate((("sans clairvoyance", z_null),
                                    ("avec clairvoyance", z_edge))):
        # Chaque cadre est gradué sur son propre domaine. Une échelle commune
        # écrasait la surface de gauche contre son plancher — son étendue vaut
        # le septième de celle de droite — et le lecteur n'y voyait plus
        # qu'une crêpe, c'est-à-dire rien. La comparaison des grandeurs est
        # rendue par les deux étendues écrites sous les titres et par la
        # barre de rapport, non par un cadre qui rend l'une illisible.
        lo, hi = cadre(z)
        vlo, vhi = etendue(z)
        span = max(abs(vlo), abs(vhi)) or 0.05

        def diverging(v: float, span: float = span) -> str:
            """Deux pôles opposés et un neutre au milieu.

            Le neutre doit se lire comme « rien » : c'est lui qui fait de la
            frontière du zéro une frontière visible plutôt qu'un simple
            changement de nuance.
            """
            if v < -NEUTRE:
                return "dn"
            if v <= NEUTRE:
                return "ze"
            return _ramp(0.45 + 0.55 * min(1.0, v / span))

        ox = 186 + idx * 322
        b.add(f'<text class="lg" x="{ox:.1f}" y="74" text-anchor="middle">'
              f'{_esc(sub)}</text>')
        b.add(f'<text class="tk" x="{ox:.1f}" y="89" text-anchor="middle">'
              f'{_esc("étendue " + _num(vlo, 3) + " à " + _num(vhi, 3) + " R")}'
              f'</text>')
        # Le sol se pose au bas du domaine et non au zéro : la rangée à
        # 50 % descend sous zéro, et un sol posé là laissait la surface le
        # traverser et venir s'écrire par-dessus les libellés d'arête. Le
        # zéro reste lisible — il est gradué sur l'échine, et la couleur en
        # fait une frontière.
        _surface(b, ox, 224, z, lo, hi, cx=28.0, cy=10.0, cz=112.0,
                 row_labels=[f"{p:.0%}" for p in selectivity],
                 col_labels=[f"{s:g} R" for s in sizing],
                 z_ticks=graduations(lo, hi),
                 tip="{v:+.3f} R", classify=diverging, zero=lo)

    # Le rapport des deux étendues, écrit une fois : c'est la seule grandeur
    # que deux échelles indépendantes ne donnent plus à lire directement.
    _, hn = etendue(z_null)
    ln, _x = etendue(z_null)
    le, he = etendue(z_edge)
    rapport = (he - le) / (hn - ln)
    b.annotation(0, 326, "les deux cadres ne partagent pas leur échelle : "
                         "l'étendue de droite vaut " + _num(rapport, 1)
                 + " fois celle de gauche")
    b.legend(0, 348, [("negf", "espérance négative"),
                      ("wash", "neutre, sous 0,02 R"),
                      ("hm6", "espérance positive")], step=178)
    _source(b, "Arête gauche : part des setups retenus. Arête droite : mise en "
               "unités de risque. Sans clairvoyance, la surface n'a aucune "
               "forme selon la sélectivité — elle change de signe d'une "
               "rangée à l'autre sans ordre — et reste exactement "
               "proportionnelle selon la mise, qui multiplie une espérance "
               "sans jamais en créer. Avec clairvoyance, elle monte "
               "régulièrement quand on resserre la sélection. La première "
               "rangée est commune aux deux cadres&nbsp;: à 100 % de setups "
               "retenus, il n'y a plus de sélection, donc plus rien que la "
               "clairvoyance puisse changer.")
    return b.render(
        "Deux surfaces d espérance par décision selon la sélectivité et la "
        "mise, sans puis avec clairvoyance")


# ---------------------------------------------------------------------------
# Figure 4 — les cinq lois nulles
# ---------------------------------------------------------------------------


def fig_nulls() -> str:
    """Les cinq lois nulles, chacune montrée plutôt que résumée.

    Un cadre par loi. La forme grise est la distribution de la statistique
    sous l'hypothèse que la loi décrit — ce que l'adversaire produit quand il
    n'a aucune compétence. Le trait vertical est la valeur observée chez
    l'opérateur, et le trait pointillé le quantile à 95 pour cent. Une loi est
    battue quand l'observé passe à droite du pointillé.

    Trois des cinq lois sont simulées et leur distribution est tracée à partir
    de leurs tirages. Les deux autres ont un adversaire analytique&nbsp;: leur
    densité est celle de la loi normale que le test emploie, et elle est
    tracée comme telle plutôt que simulée pour l'occasion.
    """
    COURT = {"mecanique": "Règle scellée", "selection": "Sélection au sort",
             "timing": "Issues permutées", "abstention": "Indépendance",
             "bootstrap": "Bootstrap par blocs"}

    j = synthesise(skill=0.55, n_sessions=SESSIONS)
    v = evaluate(j, draws=400)

    b = _plate(404, "Lois nulles",
               "Chaque statistique observée, posée sur sa loi",
               f"{len(v.beaten)} loi(s) sur 5 battue(s)")

    cols, larg, ecart = 3, 178.0, 42.0
    for k, t in enumerate(v.tests):
        col, lig = k % cols, k // cols
        x0 = 20 + col * (larg + ecart)
        y0 = 76 + lig * 152

        # Domaine : la loi, l'observé et le seuil doivent tous tenir.
        pts = list(t.sample) or [t.null_mean - 3 * t.null_sd,
                                 t.null_mean + 3 * t.null_sd]
        lo = min(min(pts), t.observed, t.q95)
        hi = max(max(pts), t.observed, t.q95)
        marge = 0.14 * (hi - lo) + 1e-9
        lo, hi = lo - marge, hi + marge

        n_bins = 26
        largeur = (hi - lo) / n_bins
        bins = [0.0] * n_bins
        if t.sample:
            for val in t.sample:
                bins[min(n_bins - 1, max(0, int((val - lo) / largeur)))] += 1.0
        else:
            # Adversaire analytique : on classe sa loi exactement, avec les
            # mêmes bornes de classe que les histogrammes voisins. La hauteur
            # d'une barre est la probabilité que la loi tombe dans la classe,
            # et non un comptage de tirages — mais le langage visuel est le
            # même, ce qui est le point : cinq cadres, une seule lecture.
            sd = t.null_sd or (hi - lo) / 6.0
            for i in range(n_bins):
                a = lo + i * largeur
                bins[i] = (_norm_cdf((a + largeur - t.null_mean) / sd)
                           - _norm_cdf((a - t.null_mean) / sd))
        pic = max(bins) or 1.0

        p = Panel(b, x0, y0, larg, 96, title=COURT.get(t.key, t.key))
        p.domain(lo, hi, 0.0, pic * 1.18)
        p.grid_x([t.null_mean, t.observed], lambda z: _num(z, 2))

        # Un seul tracé pour les cinq cadres. La densité continue réservée
        # aux deux lois analytiques leur donnait une allure à part, alors que
        # la planche existe pour qu'on les compare : cinq lois, cinq cadres,
        # une seule grammaire. Une loi très concentrée devant son domaine —
        # l'indépendance en est une — se réduit à une ou deux classes, et
        # c'est exactement ce que montrerait l'histogramme de ses tirages.
        for i, c in enumerate(bins):
            if c <= 0.0:
                continue
            centre = lo + (i + 0.5) * largeur
            p.vbar(centre, 0.0, c, (larg / n_bins) - 0.8,
                   "barfill" if centre < t.q95 else "barfill inner",
                   f"{_num(centre, 3)} — {int(c)} tirage(s)" if t.sample
                   else f"{_num(centre, 3)} — {c:.1%} de la loi")

        p.vline(t.q95, "lvl")
        p.vbar(t.observed, 0.0, pic * 1.10, 2.4,
               "s1f" if t.beats else "negf",
               f"observé {t.observed:+.4f} · {t.reading}")
        # Une seule étiquette : le motif se répète d'un cadre à l'autre, et
        # la répéter déborderait du dernier.
        if k == 0:
            p.label(t.observed, pic * 1.10, "observé", dx=5, dy=-1,
                    cls="tk halo")
        b.add(f'<text class="tk" x="{x0 + larg:.1f}" y="{y0 - 12:.1f}" '
              f'text-anchor="end">{"battue" if t.beats else "non battue"}</text>')

    b.legend(20, 372, [("barfill", "loi nulle"),
                       ("s1f", "observé, loi battue"),
                       ("negf", "observé, non battue")], step=196, kind="swatch")
    # Le texte de lecture se déduit des tests plutôt que d'être recopié : une
    # loi qui changerait d'adversaire renommerait la note toute seule. La
    # version écrite à la main désignait « les deux dernières », or ce sont
    # la première et la quatrième.
    analytiques = [COURT.get(t.key, t.key).lower()
                   for t in v.tests if not t.sample]
    boot = next((t for t in v.tests if t.key == "bootstrap"), None)
    note = ("Les deux graduations d'un cadre sont la moyenne de la loi et "
            "l'observé. Une loi est battue quand le trait fort passe à droite "
            "du pointillé. ")
    if analytiques:
        note += ("Adversaire analytique pour "
                 + " et ".join(analytiques)
                 + " : la hauteur d'une barre y est la probabilité exacte de "
                   "la classe, là où les trois autres comptent des tirages. ")
    if boot is not None:
        note += ("Le bootstrap se lit autrement : la forme grise y est la "
                 "distribution de l'espérance rééchantillonnée, l'observé sa "
                 "borne basse à 2,5 %, et le seuil est zéro.")
    _source(b, note)
    return b.render(
        "Cinq lois nulles montrées comme distributions, avec la statistique "
        "observée et le seuil à 95 pour cent posés sur chacune")


# ---------------------------------------------------------------------------
# Figure 5 — la décomposition de Shapley
# ---------------------------------------------------------------------------


#: Les clés des leviers sont des identifiants sans accent ; l'axe d'une figure
#: française porte des mots français. Le libellé complet de `LEVERS` est une
#: phrase, trop longue pour une étiquette de ligne ou de colonne.
NOMS_LEVIERS = {"entree": "entrée", "moment": "moment",
                "taille": "taille", "sortie": "sortie"}


def fig_attribution() -> str:
    """Où l'avantage loge, selon l'endroit où on l'a planté.

    La planche est un contrôle avant d'être une illustration : on plante la
    compétence dans un levier connu, et la décomposition doit l'y désigner.
    Une méthode d'attribution qui répartirait l'avantage sur les quatre
    leviers serait fausse, et cette figure le montrerait.
    """
    from .attribution import decompose

    # Chaque cas déclare *où* la compétence a été plantée. Le troisième en
    # plante deux : la figure doit alors désigner les deux, sans quoi elle
    # laisserait croire que la décomposition n'en trouve qu'un.
    cas = (("plantée dans l'entrée", 0.45, 0.0, ("entree",)),
           ("plantée dans la taille", 0.0, 0.45, ("taille",)),
           ("plantée dans les deux", 0.45, 0.45, ("entree", "taille")))

    # Bandeau « Contrôle » et non « Attribution » : la planche précédente
    # décompose un opérateur, celle-ci vérifie que la décomposition retrouve
    # la compétence là où on l'a plantée. Deux bandeaux identiques côte à côte
    # se lisaient comme une redite.
    b = _plate(292, "Contrôle de l'attribution",
               "Part de chaque levier selon l'emplacement de la compétence",
               "valeur de Shapley, 16 coalitions")

    gauche, largeur, ecart = 70.0, 158.0, 30.0
    haut = 1.05 * max(
        s.value for _, sk, sz, _ in cas
        for s in decompose(synthesise(skill=sk, size_skill=sz,
                                      n_sessions=SESSIONS)).shares)

    for idx, (titre, skill, size_skill, plantes) in enumerate(cas):
        d = decompose(synthesise(skill=skill, size_skill=size_skill,
                                 n_sessions=SESSIONS))
        x0 = gauche + idx * (largeur + ecart)
        p = Panel(b, x0, 84, largeur, 132)
        p.domain(0.0, haut, -0.6, len(d.shares) - 0.4)
        b.add(f'<text class="lg" x="{x0:.1f}" y="74">{_esc(titre)}</text>')
        p.grid_x([0.0, 0.1, 0.2], lambda x: _num(x, 1))
        p.vline(0.0, "ba")

        for k, s in enumerate(d.shares):
            row = len(d.shares) - 1 - k
            porteur = s.key in plantes
            if s.value > 1e-9:
                p.hbar(row, 0.0, s.value, 13.0,
                       "s1f" if porteur else "hm2",
                       f"{s.label} — {s.value:+.4f} R ({s.fraction:+.1%})")
            else:
                # Une part nulle doit se voir comme nulle, non comme absente.
                p.dot(0.0, row, "s1", f"{s.label} — part nulle", r=2.0)
            if idx == 0:
                b.add(f'<text class="tk" x="{x0 - 10:.1f}" '
                      f'y="{p.sy(row) + 3.5:.1f}" text-anchor="end">'
                      f'{_esc(NOMS_LEVIERS[s.key])}</text>')
            # Étiquette directe sur les leviers où la compétence a été
            # plantée : le reste se lit à l'axe, et une valeur sur chaque
            # barre serait du bruit.
            if porteur and s.value > 1e-9:
                p.label(s.value, row, f"{s.fraction:.0%}", dx=6)

    b.legend(gauche, 266, [("s1f", "levier où la compétence est plantée"),
                           ("hm2", "autres leviers")], step=250)
    _source(b, "Abscisse : part de Shapley, en unités de risque par setup "
               "éligible. Les quatre parts d'un panneau somment à l'avantage total "
               "de ce panneau. Un point marque une part exactement nulle.")
    return b.render(
        "Décomposition de Shapley de l avantage sur les quatre leviers, pour "
        "trois emplacements de la compétence plantée")


# ---------------------------------------------------------------------------
# Figure 6 — la taxe de multiplicité
# ---------------------------------------------------------------------------


def fig_tax() -> str:
    """Le seuil déflaté selon le nombre de leviers ouverts.

    La courbe est concave, et c'est tout l'argument : la taxe croît en racine
    du nombre de leviers, donc les premiers coûtent cher et les suivants
    presque rien.

    Les trois tailles d'échantillon forment une grandeur **ordonnée** : elles
    passent donc par la rampe séquentielle et non par des teintes
    catégorielles, qui prétendraient à une identité là où il n'y a qu'un
    rang.
    """
    ns = ((1000, "hm7"), (3000, "hm5"), (10000, "hm2"))
    b = _plate(316, "Taxe de multiplicité",
               "Seuil déflaté selon le nombre de leviers ouverts",
               "Bailey et López de Prado")
    p = Panel(b, 62, 62, W - 62, 186)
    # Le domaine va au-delà de la dernière graduation : la marge ainsi
    # réservée à droite accueille les étiquettes de bout de courbe. Sans
    # elle, l'étiquette se posait *sur* le trait qu'elle nomme, et un moignon
    # de ligne dépassait derrière le texte.
    p.domain(0, 9.7, 0.0, 0.105)
    p.grid_y([0.0, 0.025, 0.05, 0.075, 0.10], lambda v: _num(v, 3))
    p.grid_x([0, 1, 2, 3, 4, 5, 6, 7], lambda v: f"{v:g}",
             label="leviers discrétionnaires ouverts")

    for n, cls in ns:
        # Sans bornage : à zéro levier le budget vaut une configuration, et le
        # seuil est nul. Le borner à deux ferait démarrer la courbe au niveau
        # d'un levier et masquerait le saut initial, qui est le fait le plus
        # marquant de la figure.
        pts = [(k, deflated_threshold_sharpe(2 ** k, n)) for k in range(8)]
        p.path(pts, cls)
        # Étiquette directe au bout de la courbe, posée dans la marge : pas de
        # boîte de légende à traverser des yeux pour trois traits.
        p.dot(7, pts[-1][1], cls, r=2.4)
        p.label(7, pts[-1][1], f"{n:,}".replace(",", " ") + " décisions",
                dx=8, cls="dl halo")

    p.vline(K_LEVERS, "lvl strong")
    p.label(K_LEVERS, 0.099, f"{K_LEVERS} leviers recensés", dx=7)
    # L'annotation la plus importante de la figure : à budget d'une
    # configuration, il n'y a rien à sélectionner, donc rien à déflater.
    # Posée au-dessus de l'origine, elle ne heurte plus la graduation.
    p.label(0.25, 0.0115, "aucune taxe à zéro levier", dx=0)
    for n, cls in ns:
        val = deflated_threshold_sharpe(2 ** K_LEVERS, n)
        p.dot(K_LEVERS, val, cls,
              f"{K_LEVERS} leviers · " + f"{n:,}".replace(",", "\u202f")
              + f" décisions · seuil {_num(val, 4)}", r=3.4)

    b.add('<text class="ax" x="14" y="155" transform="rotate(-90 14 155)" '
          'text-anchor="middle">Sharpe par décision requis</text>')
    _source(b, "Seuil donné par l'approximation de Bailey et López de Prado : "
               "racine de deux fois le logarithme du budget, divisé par "
               "l'échantillon. Chaque courbe est étiquetée à son extrémité.")
    return b.render(
        "Seuil de Sharpe déflaté selon le nombre de leviers discrétionnaires "
        "ouverts, pour trois tailles d échantillon")


# ---------------------------------------------------------------------------
# Figure 7 — la calibration de l'appareil
# ---------------------------------------------------------------------------


def fig_calibration() -> str:
    """Ce que l'appareil déclare, selon ce qu'on lui a planté.

    À gauche, l'opérateur sans compétence : aucune loi battue. À droite, la
    compétence franche : les cinq. Entre les deux, la zone où l'avantage
    existe mais n'est pas démontrable — et c'est le sujet du document, pas un
    défaut de l'appareil.
    """
    data = _calibration()
    b = _plate(316, "Calibration",
               "Lois battues selon l'information plantée",
               f"{SESSIONS} séances, seuil 95 %")
    p = Panel(b, 62, 62, W - 92, 186)
    p.domain(0.0, max(d[1] for d in data) * 1.08, -0.25, 5.5)

    # La zone d'indécision, posée avant tout le reste pour rester au fond.
    flous = [bits for _, bits, n, _ in data if 0 < n < 5]
    if flous:
        p.band_x(min(flous), max(flous), "wash")

    p.grid_y([0, 1, 2, 3, 4, 5], lambda v: f"{v:g}")
    p.grid_x([0.0, 0.05, 0.10, 0.15, 0.20], lambda v: _num(v, 2),
             label="information plantée, en bits par décision")
    p.hline(5.0, "lvl strong")
    # Le niveau se nomme à droite, là où la courbe est déjà plate. La version
    # encadrée posée à gauche recouvrait la graduation « 5 » et la bande
    # d'indécision, c'est-à-dire les deux choses que la figure doit montrer.
    p.label(p.x1, 5.0, "avantage déclarable", dx=-4, dy=-7, anchor="end",
            cls="tk halo")

    p.path([(bits, n) for _, bits, n, _ in data], "s1")
    for skill, bits, n, sr in data:
        p.dot(bits, n, "s1",
              f"clairvoyance {skill:.2f} · {bits:.4f} bit · "
              f"{n}/5 lois battues · Sharpe {sr:+.4f}")

    # Les deux points qui portent l'argument, étiquetés directement. Les
    # étiquettes sont posées au-dessus de la courbe, jamais dessus : une
    # annotation qui recouvre la donnée qu'elle commente est un contresens.
    p.label(0.052, 0.62, "aucune compétence : rien n'est déclaré", dx=0)
    b.add(f'<line class="ba" x1="{p.sx(0.050):.1f}" y1="{p.sy(0.62):.1f}" '
          f'x2="{p.sx(0.004):.1f}" y2="{p.sy(0.10):.1f}"/>')
    if flous:
        # Deportee dans le quadrant que la courbe laisse libre une fois son
        # palier atteint, et reliee a la bande qu'elle commente.
        haut = max(flous)
        p.label(0.108, 2.30, "l'avantage existe,", dx=0)
        p.label(0.108, 2.30, "mais ne se démontre pas", dx=0, dy=16)
        # Le trait de rappel entre dans la bande au lieu de s'arrêter à son
        # bord : posé sur la bordure, il se confondait avec une graduation.
        centre = 0.5 * (min(flous) + haut)
        b.add(f'<line class="ba" x1="{p.sx(0.104):.1f}" y1="{p.sy(2.30):.1f}" '
              f'x2="{p.sx(centre):.1f}" y2="{p.sy(2.30):.1f}"/>')

    b.add('<text class="ax" x="14" y="155" transform="rotate(-90 14 155)" '
          'text-anchor="middle">lois nulles battues sur cinq</text>')
    _source(b, "Abscisse : information plantée, en bits par décision. Ordonnée : "
               "lois nulles battues sur cinq. Chaque point est un journal complet, "
               f"évalué par la batterie entière.")
    return b.render(
        "Nombre de lois nulles battues selon l information plantée par "
        "décision, calibration de l appareil de mesure")


FIGURES = {
    "discwall": fig_wall,
    "discplane": fig_plane,
    "discnulls": fig_nulls,
    "discattrib": fig_attribution,
    "disctax": fig_tax,
    "disccalib": fig_calibration,
}


def render_all() -> dict[str, str]:
    return {k: fn() for k, fn in FIGURES.items()}


# ---------------------------------------------------------------------------
# Figure 8 — le nuage Monte-Carlo de l'estimateur
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _paths(n_paths: int = 520, horizon: int = 1400) -> tuple:
    """Trajectoires de l'espérance cumulée, sous absence de compétence.

    Chaque chemin rééchantillonne le journal sans compétence par blocs, puis
    trace la moyenne courante décision après décision. L'ensemble dessine
    l'entonnoir dans lequel un estimateur sans avantage évolue, et sa largeur
    à chaque abscisse est le bruit que l'opérateur doit dépasser.
    """
    from .mc import Rng, block_length_for_autocorrelation, stationary_bootstrap

    j = synthesise(skill=0.0, n_sessions=SESSIONS)
    base = j.returns
    rng = Rng(20260823)
    bloc = block_length_for_autocorrelation(0.0)

    paths, finaux = [], []
    for _ in range(n_paths):
        tirage = stationary_bootstrap(base, rng, bloc, n=horizon)
        cum, total = [], 0.0
        for k, v in enumerate(tirage, start=1):
            total += v
            if k % 40 == 0:
                cum.append((k, total / k))
        paths.append(tuple(cum))
        finaux.append(total / horizon)
    return tuple(paths), tuple(sorted(finaux)), horizon


def fig_cloud() -> str:
    """L'entonnoir de l'estimateur en l'absence de compétence.

    L'abscisse est le nombre de décisions accumulées, l'ordonnée l'espérance
    mesurée depuis le début. Les quantiles marquent l'enveloppe dans laquelle
    un opérateur sans avantage se trouve, et son resserrement en racine du
    nombre de décisions donne la lecture directe du mur d'échantillon.
    """
    paths, finaux, horizon = _paths()

    def quantile(xs, q: float) -> float:
        s = sorted(xs)
        pos = q * (len(s) - 1)
        lo = int(math.floor(pos))
        return s[lo] + (s[min(lo + 1, len(s) - 1)] - s[lo]) * (pos - lo)

    ks = [k for k, _ in paths[0]]
    par_k = {k: [] for k in ks}
    for chemin in paths:
        for k, v in chemin:
            par_k[k].append(v)

    lo = min(quantile(par_k[k], 0.01) for k in ks[3:])
    hi = max(quantile(par_k[k], 0.99) for k in ks[3:])
    marge = 0.12 * (hi - lo)

    b = _plate(330, "Monte-Carlo", "Espérance cumulée sous absence de compétence",
               f"{len(paths)} chemins, bootstrap par blocs")
    p = Panel(b, 66, 62, W - 138, 200)
    # Grille ronde en ordonnée, et le zéro en fait partie : la ligne
    # d'espérance nulle tracée plus bas restait sans graduation, donc sans
    # nom. En abscisse, un pas régulier plutôt que 250-500-1000-1400.
    cran, pas = 0.05, 0.10
    y0 = cran * math.floor((lo - marge) / cran)
    y1 = cran * math.ceil((hi + marge) / cran)
    p.domain(ks[3], horizon, y0, y1)
    p.grid_y([pas * k for k in range(math.ceil(y0 / pas),
                                     math.floor(y1 / pas) + 1)],
             lambda v: _num(v, 2))
    p.grid_x([t for t in range(250, horizon, 250) if horizon - t >= 150]
             + [horizon], lambda v: f"{v:g}", label="décisions accumulées")

    # La bande interquantile, posée avant les chemins pour rester au fond.
    haut = [(k, quantile(par_k[k], 0.95)) for k in ks[3:]]
    bas = [(k, quantile(par_k[k], 0.05)) for k in ks[3:]]
    d = " ".join(("M" if i == 0 else "L") + f"{p.sx(x):.1f},{p.sy(y):.1f}"
                 for i, (x, y) in enumerate(haut))
    d += " " + " ".join(f"L{p.sx(x):.1f},{p.sy(y):.1f}" for x, y in reversed(bas))
    b.add(f'<path class="band-mc" d="{d} Z"/>')

    for chemin in paths:
        pts = [(k, v) for k, v in chemin if k >= ks[3]]
        b.add('<path class="path-mc" d="' + " ".join(
            ("M" if i == 0 else "L") + f"{p.sx(x):.0f},{p.sy(y):.1f}"
            for i, (x, y) in enumerate(pts)) + '"/>')

    for q, cls, lab in ((0.95, "quant dash", "P95"), (0.50, "quant", "médiane"),
                        (0.05, "quant dash", "P5")):
        pts = [(k, quantile(par_k[k], q)) for k in ks[3:]]
        b.add('<path class="' + cls + '" d="' + " ".join(
            ("M" if i == 0 else "L") + f"{p.sx(x):.1f},{p.sy(y):.1f}"
            for i, (x, y) in enumerate(pts)) + '"/>')
        p.label(horizon, pts[-1][1], lab, dx=6, cls="tk halo")

    p.hline(0.0, "lvl strong")
    _source(b, "Abscisse : décisions accumulées. Ordonnée : espérance mesurée depuis "
               "le début, en unités de risque. La bande couvre 90 pour cent des "
               "chemins.")
    return b.render(
        "Nuage de trajectoires de l espérance cumulée sous absence de "
        "compétence, avec ses quantiles")


# ---------------------------------------------------------------------------
# Figure 9 — histogramme et fonction de répartition
# ---------------------------------------------------------------------------


def fig_distribution() -> str:
    """La loi de l'estimateur, en densité puis en répartition.

    À gauche, la distribution des espérances obtenues sans compétence, avec
    ses quantiles. À droite, la même information en cumulé : elle donne
    directement la probabilité qu'un opérateur sans avantage atteigne une
    espérance donnée.
    """
    _, finaux, horizon = _paths()
    n = len(finaux)

    def q(x: float) -> float:
        pos = x * (n - 1)
        lo = int(math.floor(pos))
        return finaux[lo] + (finaux[min(lo + 1, n - 1)] - finaux[lo]) * (pos - lo)

    p05, p50, p95 = (q(v) for v in (0.05, 0.50, 0.95))
    lo, hi = finaux[0], finaux[-1]
    n_bins = 46
    largeur = (hi - lo) / n_bins
    bins = [0] * n_bins
    for v in finaux:
        bins[min(n_bins - 1, int((v - lo) / largeur))] += 1
    pic = max(bins)

    b = _plate(330, "Loi de l'estimateur",
               "Densité et répartition, sans compétence",
               f"{n} tirages, {horizon} décisions")

    g = Panel(b, 60, 66, 250, 186, title="Distribution")
    g.domain(lo, hi, 0, pic * 1.08)
    g.grid_y([0, pic // 2, pic], lambda v: f"{v:g}")
    g.grid_x([lo, p50, hi], lambda v: _num(v, 2), label="espérance par décision")
    for k, c in enumerate(bins):
        centre = lo + (k + 0.5) * largeur
        dedans = p05 <= centre <= p95
        g.vbar(centre, 0, c, (g.w / n_bins) - 1.2,
               "barfill inner" if dedans else "barfill",
               f"{_num(centre, 3)} R — {c} tirage(s)")
    # Trois repères seulement, et chacun nommé. Les quartiers P25 et P75
    # tracés sans étiquette laissaient cinq pointillés dont le lecteur ne
    # pouvait dire lequel était lequel — cinq traits pour une seule légende.
    for v, lab, cls in ((p05, "P5", "lvl"),
                        (p50, "médiane", "lvl strong"),
                        (p95, "P95", "lvl")):
        g.vline(v, cls)
        # Toutes les étiquettes partent à droite de leur trait. Ancrer la
        # dernière à gauche la ramenait sur « médiane », et les deux mots se
        # chevauchaient.
        g.label(v, pic * 1.03, lab, dx=5, cls="tk halo")

    # Dix-huit points de marge à droite : la dernière graduation est
    # centrée sur le bord du cadre et déborderait de la planche sans eux.
    d = Panel(b, 372, 66, W - 390, 186, title="Répartition")
    d.domain(lo, hi, 0.0, 1.0)
    d.grid_y([0.0, 0.25, 0.5, 0.75, 1.0], lambda v: f"{v:.0%}")
    d.grid_x([lo, p50, hi], lambda v: _num(v, 2),
             label="espérance par décision")
    d.path([(v, (i + 1) / n) for i, v in enumerate(finaux)], "s2")
    for v, part in ((p05, 0.05), (p50, 0.50), (p95, 0.95)):
        d.vline(v, "lvl")
        d.dot(v, part, "s1", f"{_num(v, 3)} R atteint dans {1 - part:.0%} des cas")
    # Les trois repères portent le même nom que dans le cadre de gauche, et
    # se posent sous la courbe : au-dessus, « P95 » tombait dessus.
    for v, part, lab in ((p05, 0.05, "P5"), (p50, 0.50, "médiane"),
                         (p95, 0.95, "P95")):
        d.label(v, part, lab, dx=7, dy=13, cls="tk halo")

    _source(b, "La bande claire de l'histogramme couvre 90 pour cent des tirages. "
               "La répartition donne la probabilité qu'une espérance soit "
               "atteinte sans compétence.")
    return b.render(
        "Distribution et fonction de répartition de l espérance mesurée sous "
        "absence de compétence")


FIGURES["disccloud"] = fig_cloud
FIGURES["discdist"] = fig_distribution


# ---------------------------------------------------------------------------
# Figure 10 — l'estimation glissante et sa bande
# ---------------------------------------------------------------------------


def fig_rolling() -> str:
    """L'espérance mesurée sur fenêtre glissante, avec son intervalle.

    L'estimation sur fenêtre fixe ne converge pas : elle oscille, et
    l'amplitude de son oscillation est donnée par l'intervalle. La figure
    compare deux opérateurs sur la même fenêtre, et montre à quelle taille de
    fenêtre leurs intervalles cessent de se recouvrir.
    """
    #: La fenêtre vient de `report10`, qui la publie aussi au document : sans
    #: source unique, la légende et la figure divergeraient en silence. Le
    #: journal doit être nettement plus long que la fenêtre, faute de quoi il
    #: ne reste qu'une poignée de positions à tracer.
    from .report10 import FENETRE_GLISSANTE

    FEN, SEANCES = FENETRE_GLISSANTE, 1400

    def serie(skill: float) -> list[tuple[int, float, float]]:
        j = synthesise(skill=skill, n_sessions=SEANCES)
        r = j.returns
        out = []
        for fin in range(FEN, len(r), 4):
            f = r[fin - FEN:fin]
            m = sum(f) / FEN
            sd = math.sqrt(sum((x - m) ** 2 for x in f) / (FEN - 1))
            out.append((fin, m, 1.96 * sd / math.sqrt(FEN)))
        return out

    sans, avec = serie(0.0), serie(0.55)
    tout = sans + avec
    lo = min(m - e for _, m, e in tout)
    hi = max(m + e for _, m, e in tout)

    b = _plate(320, "Fenêtre glissante",
               f"Espérance mesurée sur {FEN} décisions",
               "intervalle à 95 %")
    p = Panel(b, 66, 62, W - 118, 194)
    # Bornes et graduations sur une grille ronde. Calées au plus juste, elles
    # donnaient « 1,03 » et « −0,35 » en ordonnée et « 279 » en abscisse :
    # des repères qu'aucun lecteur n'interpole de tête.
    pas = 0.25
    lo = pas * math.floor(lo / pas)
    hi = pas * math.ceil(hi / pas)
    p.domain(sans[0][0], max(x for x, _, _ in tout), lo, hi)
    p.grid_y([pas * k for k in range(round(lo / pas), round(hi / pas) + 1)],
             lambda v: _num(v, 2))
    dernier = max(x for x, _, _ in tout)
    ticks = [FEN] + [t for t in range(200, dernier + 1, 200)
                     if t > FEN + 80]
    p.grid_x(ticks, lambda v: f"{v:g}", label="décision courante")

    for pts, cls, lab in ((sans, "s3", "sans"), (avec, "s1", "avec")):
        haut = [(x, m + e) for x, m, e in pts]
        bas = [(x, m - e) for x, m, e in pts]
        d = " ".join(("M" if i == 0 else "L") + f"{p.sx(x):.1f},{p.sy(y):.1f}"
                     for i, (x, y) in enumerate(haut))
        d += " " + " ".join(f"L{p.sx(x):.1f},{p.sy(y):.1f}"
                            for x, y in reversed(bas))
        b.add(f'<path class="band-mc" d="{d} Z"/>')
        p.path([(x, m) for x, m, _ in pts], cls)
        p.label(pts[-1][0], pts[-1][1], lab, dx=7, cls="tk halo")

    p.hline(0.0, "lvl strong")
    p.tag(0.0, "espérance nulle", side="left")
    # Les deux courbes n'ont pas la même longueur, et il faut le dire : sur le
    # même nombre de séances l'opérateur clairvoyant s'abstient davantage, donc
    # enregistre moins de décisions. Sans cette phrase, sa courbe passe pour
    # tronquée.
    _source(b, "Abscisse : rang de la décision courante. Ordonnée : moyenne des "
               f"{FEN} décisions précédentes. La bande est l'intervalle à 95 pour "
               f"cent de cette moyenne. Les deux séries couvrent {SEANCES} séances "
               f"chacune : l'opérateur clairvoyant s'abstient davantage et en tire "
               f"{avec[-1][0]} décisions contre {sans[-1][0]}, d'où une courbe plus "
               "courte.")
    return b.render(
        "Espérance mesurée sur fenêtre glissante et son intervalle de "
        "confiance, pour deux opérateurs")


# ---------------------------------------------------------------------------
# Figure 11 — la carte de puissance
# ---------------------------------------------------------------------------


def _power(n: float, bits: float) -> float:
    """Puissance du test G à seuil 5 %, par approximation normale."""
    besoin = trades_for_information(max(bits, 1e-9))
    if besoin <= 0.0 or not math.isfinite(besoin):
        return 0.0
    lam = 1.96 * math.sqrt(max(n, 1.0) / besoin)
    return min(1.0, max(0.0, _norm_cdf(lam - 1.96)))


def fig_powermap() -> str:
    """La puissance en carte plane plutôt qu'en relief.

    La surface isométrique donne la forme ; elle ne permet pas de lire une
    valeur. La carte plane le permet : chaque case porte sa puissance, et la
    ligne de niveau à 80 pour cent sépare le domaine où la détection est
    acquise de celui où elle ne l'est pas.
    """
    ns = [125, 250, 500, 1000, 2000, 4000]
    bits_grid = [0.0025, 0.005, 0.010, 0.020, 0.040, 0.080]

    b = _plate(340, "Puissance", "Carte de puissance à seuil 5 %",
               "test G informationnel")
    gx, gy = 92.0, 66.0
    cw = (W - gx - 108) / len(ns)
    ch = 172.0 / len(bits_grid)

    for j, bits in enumerate(reversed(bits_grid)):
        y = gy + j * ch
        b.add(f'<text class="tk" x="{gx - 8:.1f}" y="{y + ch / 2 + 3.5:.1f}" '
              f'text-anchor="end">{_esc(_num(bits, 4))}</text>')
        for i, n in enumerate(ns):
            pw = _power(n, bits)
            x = gx + i * cw
            b.add(f'<rect class="{_ramp(pw)}" x="{x + 1:.1f}" y="{y + 1:.1f}" '
                  f'width="{cw - 2:.1f}" height="{ch - 2:.1f}">'
                  f'<title>{n} décisions · {_esc(_num(bits, 4))} bit · '
                  f'puissance {pw:.0%}</title></rect>')
            b.add(f'<text class="cell {"cl-hi" if pw > 0.55 else "cl-lo"}" '
                  f'x="{x + cw / 2:.1f}" y="{y + ch / 2 + 3.5:.1f}" '
                  f'text-anchor="middle">{pw * 100:.0f}</text>')
    for i, n in enumerate(ns):
        b.add(f'<text class="tk" x="{gx + i * cw + cw / 2:.1f}" '
              f'y="{gy + len(bits_grid) * ch + 15:.1f}" text-anchor="middle">'
              f'{n}</text>')
    b.add(f'<text class="ax" x="{gx + (W - gx - 108) / 2:.1f}" '
          f'y="{gy + len(bits_grid) * ch + 32:.1f}" text-anchor="middle">'
          f'décisions enregistrées</text>')
    b.add(f'<text class="ax" x="20" y="{gy + 86:.1f}" '
          f'transform="rotate(-90 20 {gy + 86:.1f})" text-anchor="middle">'
          f'bits par décision</text>')

    _scale_legend(b, gx, 296, "0 %", "100 %", "puissance de détection")
    _source(b, "Chaque case porte sa puissance en pour cent. La détection est "
               "acquise au sens usuel à partir de 80.")
    return b.render(
        "Carte de la puissance de détection par nombre de décisions et "
        "information par décision")


# ---------------------------------------------------------------------------
# Figure 12 — la caractéristique opérationnelle
# ---------------------------------------------------------------------------


def fig_roc() -> str:
    """Ce que coûte un seuil plus permissif, en faux positifs.

    Le seuil de 5 pour cent retenu partout ailleurs n'est qu'un point de
    cette courbe. La caractéristique donne, pour chaque taux de fausse
    déclaration accepté, le taux de détection correspondant, et elle le donne
    à plusieurs tailles d'échantillon.
    """
    from .report10 import BITS_ROC

    def norm_ppf(q: float) -> float:
        from .costs import _norm_ppf
        return _norm_ppf(q)

    b = _plate(322, "Caractéristique",
               "Détection contre fausse déclaration",
               f"compétence de {_num(BITS_ROC, 3)} bit par décision")
    p = Panel(b, 66, 62, 300, 194)
    p.domain(0.0, 1.0, 0.0, 1.0)
    p.grid_y([0, 0.25, 0.5, 0.75, 1.0], lambda v: f"{v:.0%}")
    p.grid_x([0, 0.25, 0.5, 0.75, 1.0], lambda v: f"{v:.0%}",
             label="taux de fausse déclaration")

    # La diagonale : un appareil sans pouvoir de séparation.
    p.path([(0.0, 0.0), (1.0, 1.0)], "s3", dash="3 3")
    p.label(0.60, 0.60, "aucune séparation", dx=4, dy=-5, cls="tk halo")

    besoin = trades_for_information(BITS_ROC)
    for n, cls in ((250, "hm3"), (1000, "hm5"), (4000, "hm7")):
        decalage = 1.96 * math.sqrt(n / besoin)
        pts = []
        for k in range(1, 100):
            alpha = k / 100.0
            t = norm_ppf(1.0 - alpha)
            pts.append((alpha, min(1.0, max(0.0, _norm_cdf(decalage - t)))))
        p.path(pts, cls)
        # Étiquette au coude de la courbe, où les trois se séparent.
        coude = pts[9]
        p.label(coude[0], coude[1], f"{n}", dx=6, dy=4, cls="tk halo")
        # Le point de fonctionnement retenu par le protocole.
        pw = _power(n, BITS_ROC)
        p.dot(0.05, pw, "s1", f"{n} décisions · seuil 5 % · puissance {pw:.0%}")
    p.vline(0.05, "lvl strong")
    p.label(0.05, 0.06, "seuil retenu : 5 %", dx=7)

    # Le second cadre : puissance au seuil retenu, en fonction de N.
    q = Panel(b, 424, 62, W - 460, 194, title="Au seuil de 5 %")
    q.domain(100, 6000, 0.0, 1.0)
    q.grid_y([0, 0.5, 0.8, 1.0], lambda v: f"{v:.0%}", side="right")
    q.grid_x([1000, 3000, 5000], lambda v: f"{v:g}", label="décisions")
    q.path([(n, _power(n, BITS_ROC)) for n in range(120, 6001, 40)], "s1")
    q.hline(0.80, "lvl strong")
    q.tag(0.80, "80 %", side="left")

    _source(b, "Cadre de gauche : chaque courbe est une taille d'échantillon. "
               "Cadre de droite : puissance au seuil retenu, en fonction du "
               "nombre de décisions.")
    return b.render(
        "Caractéristique opérationnelle du test : taux de détection contre "
        "taux de fausse déclaration, à trois tailles d échantillon")


# ---------------------------------------------------------------------------
# Figure 13 — la cascade de Shapley
# ---------------------------------------------------------------------------


def fig_waterfall() -> str:
    """De la règle scellée à l'opérateur, levier par levier.

    Les parts de Shapley somment exactement à l'écart total. La cascade rend
    cette propriété visible : chaque marche est une part, et la dernière
    colonne retombe sur l'espérance réalisée.
    """
    from .attribution import decompose

    d = decompose(synthesise(skill=0.45, size_skill=0.30,
                             n_sessions=SESSIONS))
    b = _plate(342, "Attribution", "De la règle scellée à l'opérateur",
               "valeur de Shapley")
    p = Panel(b, 78, 66, W - 118, 176)

    etapes = [("règle scellée", d.baseline, None)]
    courant = d.baseline
    for s in d.shares:
        etapes.append((NOMS_LEVIERS[s.key], s.value, courant))
        courant += s.value
    etapes.append(("opérateur", courant, None))

    # Les bornes se calent sur une grille ronde, et les graduations sur des
    # multiples de cinq centièmes. Des bornes calculées au plus juste
    # donnaient des graduations arbitraires — 0,27 et 0,14 — qu'aucun lecteur
    # ne peut interpoler de tête.
    pas, cran = 0.05, 0.025
    lo = cran * math.floor((min(0.0, d.baseline) - 0.015) / cran)
    hi = cran * math.ceil((courant * 1.10) / cran)
    p.domain(-0.6, len(etapes) - 0.4, lo, hi)
    p.grid_y([pas * k for k in range(math.ceil(lo / pas),
                                     math.floor(hi / pas) + 1)],
             lambda v: _num(v, 2))
    p.hline(0.0, "ba")

    for i, (nom, val, base) in enumerate(etapes):
        if base is None:                      # colonne pleine : un total
            p.vbar(i, 0.0, val, 36.0, "s2f",
                   f"{nom} — {val:+.4f} R par setup éligible")
            p.label(i, max(val, 0.0), _num(val, 3), dx=0, dy=-8,
                    anchor="middle")
        else:                                  # marche : une contribution
            haut, bas = base + val, base
            cls = "s1f" if val > 1e-9 else "negf"
            p.vbar(i, bas, haut, 36.0, cls,
                   f"{nom} — {val:+.4f} R ({val / d.total:+.0%} du total)")
            # Une marche trop courte pour se voir reste une marche : sans
            # étiquette, elle passe pour un défaut de tracé. On l'annonce
            # comme négligeable plutôt que de l'arrondir à « −0,000 ».
            texte = _signed(val, 3) if abs(val) >= 0.001 else "≈ 0"
            p.label(i, max(haut, bas), texte, dx=0, dy=-8, anchor="middle")
            # Le trait de liaison, qui rend la cascade lisible.
            b.add(f'<line class="gl" x1="{p.sx(i - 0.34):.1f}" '
                  f'y1="{p.sy(bas):.1f}" x2="{p.sx(i - 0.66):.1f}" '
                  f'y2="{p.sy(bas):.1f}"/>')
        b.add(f'<text class="tk" x="{p.sx(i):.1f}" '
              f'y="{p.y + p.h + 16:.1f}" text-anchor="middle">'
              f'{_esc(nom)}</text>')

    b.add(f'<text class="ax" x="20" y="{p.y + 88:.1f}" '
          f'transform="rotate(-90 20 {p.y + 88:.1f})" text-anchor="middle">'
          f'espérance par setup éligible</text>')
    b.legend(78, 318, [("s2f", "niveau atteint"),
                       ("s1f", "part positive"),
                       ("negf", "part négative")], step=152)
    _source(b, "Les deux colonnes pleines sont des niveaux ; les marches "
               "intermédiaires sont des contributions. Leur somme est exacte "
               "par construction.")
    return b.render(
        "Cascade de la valeur de Shapley, de la règle scellée à l espérance "
        "réalisée par l opérateur")


FIGURES["discrolling"] = fig_rolling
FIGURES["discpowermap"] = fig_powermap
FIGURES["discroc"] = fig_roc
FIGURES["discwaterfall"] = fig_waterfall


# ---------------------------------------------------------------------------
# Figure 14 — les sept couches et les quatre leviers
# ---------------------------------------------------------------------------


def fig_layers() -> str:
    """Où chaque couche d'analyse intervient dans la décision.

    La matrice ne dit pas ce qu'une couche vaut : elle dit à quel moment
    l'opérateur la consulte. Un levier alimenté par plusieurs couches
    concentre la charge de preuve ; un levier qu'aucune couche n'alimente est
    exercé sans support déclaré.
    """
    from .report10 import COUCHES

    leviers = [k for k, _ in LEVERS]
    b = _plate(322, "Architecture",
               "Quelle couche alimente quel levier",
               f"{len(COUCHES)} couches, {len(leviers)} leviers")

    gx, gy = 210.0, 74.0
    cw = (W - gx - 20) / len(leviers)
    ch = 152.0 / len(COUCHES)

    for j, (nom, _, levier, _) in enumerate(COUCHES):
        y = gy + j * ch
        b.add(f'<text class="tk" x="{gx - 10:.1f}" y="{y + ch / 2 + 3.5:.1f}" '
              f'text-anchor="end">{_esc(nom)}</text>')
        for i, k in enumerate(leviers):
            x = gx + i * cw
            actif = k == levier
            b.add(f'<rect class="{"s1f" if actif else "wash"}" '
                  f'x="{x + 2:.1f}" y="{y + 2:.1f}" '
                  f'width="{cw - 4:.1f}" height="{ch - 4:.1f}" rx="2">'
                  f'<title>{_esc(nom)} — '
                  f'{"alimente" if actif else "n a pas d effet sur"} '
                  f'le levier « {NOMS_LEVIERS[k]} »</title></rect>')

    for i, k in enumerate(leviers):
        n = sum(1 for c in COUCHES if c[2] == k)
        x = gx + i * cw + cw / 2
        b.add(f'<text class="tk" x="{x:.1f}" y="{gy - 22:.1f}" '
              f'text-anchor="middle">{_esc(NOMS_LEVIERS[k])}</text>')
        b.add(f'<text class="dl" x="{x:.1f}" y="{gy - 9:.1f}" '
              f'text-anchor="middle">{n}</text>')

    b.add(f'<line class="ba" x1="{gx:.1f}" y1="{gy - 5:.1f}" '
          f'x2="{W - 20:.1f}" y2="{gy - 5:.1f}"/>')
    b.add(f'<text class="ax" x="{gx - 10:.1f}" y="{gy - 9:.1f}" '
          f'text-anchor="end">couches alimentant</text>')

    b.legend(gx, 268, [("s1f", "la couche alimente le levier"),
                       ("wash", "sans effet déclaré")], step=228)
    _source(b, "Le chiffre au-dessus de chaque colonne est le nombre de couches "
               "qui alimentent ce levier. La matrice situe les couches dans la "
               "décision ; elle ne mesure pas leur apport.")
    return b.render(
        "Matrice des sept couches d analyse et des quatre leviers "
        "discrétionnaires qu elles alimentent")


FIGURES["disclayers"] = fig_layers

# ---------------------------------------------------------------------------
# Les sept couches — figures reprises des documents antérieurs
# ---------------------------------------------------------------------------

# Ces figures existent déjà : elles ont été construites pour les documents
# nº 1 et nº 2, où chaque couche est passée au crible de sa loi nulle. Les
# refaire ici serait à la fois du travail perdu et une source de divergence —
# deux figures du même objet finiraient par ne plus dire la même chose.
#
# Elles n'écrivent aucune couleur : elles posent des classes, et la feuille
# du document décide. Reprises telles quelles, elles adoptent donc d'elles-
# mêmes le jeu de jetons sombre de ce document.

#: Les clés sont en minuscules et soulignés : c'est ce que le motif du
#: gabarit accepte, et une clé capitalisée passerait simplement inaperçue.
COUCHES_FIGURES = {
    "couche_dow": "fig_dow_null",
    "couche_profil": "fig_volume_profile",
    "couche_vwap": "fig_vwap_bands",
    "couche_gamma": "fig_gex_levels",
    "couche_carnet": "fig_liquidity_map",
    "couche_fib": "fig_fib_retracement",
    "couche_horizon": "fig_signal_horizon",
}


def _couche(nom: str):
    """Rend une figure de couche depuis `figterm`, sans la redéfinir."""
    from . import figterm

    return lambda: getattr(figterm, nom)()


for _cle, _fn in COUCHES_FIGURES.items():
    FIGURES[_cle] = _couche(_fn)

# ---------------------------------------------------------------------------
# Figure 21 — le seuil, et non le signal
# ---------------------------------------------------------------------------


def fig_seuil() -> str:
    """Le seuil que la géométrie impose, et ce qu'elle rend à dérive déclarée.

    Deux cadres qui partagent l'abscisse. En haut le seuil `µ* = c/E[τ∧T]`,
    en échelle logarithmique parce qu'il couvre deux ordres de grandeur, avec
    la bande de dérive plausible posée derrière : on voit d'un coup d'œil que
    la géométrie déclarée tombe au-dessus de la bande — donc hors d'atteinte
    quelle que soit la dérive réelle — et que l'optimum tombe six fois sous sa
    borne basse. En bas l'espérance nette, dont l'optimum est intérieur.
    """
    from . import seuil as S
    from .report11 import DERIVE_TRAVAIL

    gs = S.scan()
    xs = [g.stop_pct for g in gs]
    mus = [g.break_even_per_hour for g in gs]
    ers = [g.expectancy_r(DERIVE_TRAVAIL) for g in gs]
    opt = S.best(DERIVE_TRAVAIL)
    bas, haut = S.PLAUSIBLE_DRIFT_PER_HOUR

    b = _plate(392, "Le seuil, et non le signal",
               "Ce que la géométrie exige du signal",
               f"dérive déclarée {_num(DERIVE_TRAVAIL, 1)} pt/h")

    # --- cadre du haut : le seuil ----------------------------------------
    # Domaines déduits des données, bande plausible comprise : c'est elle qui
    # décide du verdict, elle doit donc tenir dans le cadre.
    ylo = min(min(mus), bas) / 1.6
    yhi = max(max(mus), haut) * 1.6
    # Pas de « µ » dans l'intitulé : la feuille de style le met en capitales
    # et le mu minuscule y devient un M. Le symbole vit dans la ligne de
    # lecture, qui n'est pas capitalisée — même piège que dans `figquant`.
    p1 = Panel(b, 66, 62, W - 116, 132, title="Seuil de rentabilité",
               readout="µ* = c / E[τ∧T]")
    p1.domain(min(xs) / 1.35, max(xs) * 1.35, ylo, yhi, xlog=True, ylog=True)
    p1.band_y(bas, haut, "wash")
    p1.frame()
    # Graduations déduites du domaine, jamais écrites à la main : une
    # puissance de dix posée hors du domaine serait tout de même tracée —
    # `grid_y` ne découpe pas — et tomberait entre les deux cadres.
    dec = [10.0 ** k for k in range(-3, 3)]
    p1.grid_y([v for v in dec if ylo <= v <= yhi], lambda v: _num(v, 2),
              "points par heure")
    p1.grid_x([0.01, 0.025, 0.05, 0.1, 0.2, 0.4], lambda v: _num(v, 3) + " %")
    p1.path(list(zip(xs, mus)), "s1")
    for g in gs:
        p1.dot(g.stop_pct, g.break_even_per_hour,
               "s1" if g.reachable else "negf",
               f"stop {_num(g.stop_pct, 3)} % — µ* = "
               f"{_num(g.break_even_per_hour, 3)} pt/h", r=3.0)
    p1.label(max(xs) * 1.3, (bas * haut) ** 0.5, "dérive plausible",
             dx=-4, anchor="end", cls="tk halo")
    p1.label(xs[0], mus[0], "géométrie déclarée", dx=8, dy=-6, cls="dl halo")

    # --- cadre du bas : l'espérance --------------------------------------
    lo2 = min(ers) - 0.06 * (max(ers) - min(ers))
    hi2 = max(ers) + 0.14 * (max(ers) - min(ers))
    p2 = Panel(b, 66, 250, W - 116, 96,
               title="Espérance nette par trade",
               readout="identité de Wald, temps borné par la séance")
    p2.domain(min(xs) / 1.35, max(xs) * 1.35, lo2, hi2, xlog=True)
    p2.frame()
    pas = 0.2
    p2.grid_y([pas * k for k in range(math.ceil(lo2 / pas),
                                      math.floor(hi2 / pas) + 1)],
              lambda v: _num(v, 1), "multiples du risque")
    p2.grid_x([0.01, 0.025, 0.05, 0.1, 0.2, 0.4], lambda v: _num(v, 3) + " %",
              "largeur du stop, en % de l\'indice")
    p2.hline(0.0, "lvl strong")
    p2.path(list(zip(xs, ers)), "s1")
    p2.dot(opt.stop_pct, opt.expectancy_r(DERIVE_TRAVAIL), "s1f",
           f"optimum — {_num(opt.expectancy_r(DERIVE_TRAVAIL), 4)} R", r=4.0)
    p2.label(opt.stop_pct, opt.expectancy_r(DERIVE_TRAVAIL), "optimum",
             dx=8, dy=-7, cls="dl halo")
    p2.dot(xs[0], ers[0], "negf", r=4.0)

    _source(b, "Le seuil ne dépend que de la géométrie et de la friction, "
               "jamais du signal. La bande est le domaine de dérive que le "
               "document nº 1 déclare plausible : une géométrie dont le seuil "
               "passe au-dessus ne peut pas être rentable, quelle que soit la "
               "dérive réelle. L\'optimum du cadre du bas est intérieur — la "
               "friction domine à gauche, la saturation de séance à droite.")
    return b.render(
        "Seuil de rentabilité et espérance nette selon la largeur du stop, "
        "avec le domaine de dérive plausible")


FIGURES["discseuil"] = fig_seuil

# ---------------------------------------------------------------------------
# Figure 22 — la surface du seuil, et le plafond du plausible
# ---------------------------------------------------------------------------


def fig_seuil_surface() -> str:
    """Le seuil sur le plan (largeur de stop, friction), et ce qui le franchit.

    La figure précédente montre le seuil le long d'un seul axe. Celle-ci le
    montre sur les deux axes que l'opérateur contrôle réellement — la
    géométrie et la friction — et y pose la seule chose qu'il ne contrôle
    pas&nbsp;: le plafond de dérive plausible.

    La hauteur est le logarithme du seuil, parce qu'il couvre deux ordres et
    demi de grandeur et qu'une échelle linéaire écraserait tout sauf le coin
    le plus défavorable. Les graduations portent les valeurs réelles.

    La couleur ne code pas la hauteur mais le **verdict**&nbsp;: une maille
    rouge est une configuration dont le seuil dépasse le plafond du plausible,
    donc dont la rentabilité est impossible quelle que soit la dérive du
    marché. C'est la lecture que la figure existe pour donner, et elle se fait
    sans lire une seule graduation.
    """
    from . import seuil as S

    # Les deux grilles viennent du module et non de la figure : le texte qui
    # commente la surface cite les mêmes bornes, et une friction écrite deux
    # fois finirait par diverger de l'autre.
    stops = S.SURFACE_STOP_PCT
    frictions = S.friction_grid()
    plafond = S.PLAUSIBLE_DRIFT_PER_HOUR[1]

    z = [[math.log10(S.break_even(pct, c)) for c in frictions]
         for pct in stops]

    plat = [v for ligne in z for v in ligne]
    # Le domaine suit les données et non les décennies entières : arrondir à
    # la décennie donnait quatre décades pour des valeurs qui n'en couvrent
    # que 2,3, et la surface n'occupait plus que la moitié de son cadre.
    zlo, zhi = min(plat) - 0.15, max(plat) + 0.15
    limite = math.log10(plafond)

    def verdict(v: float) -> str:
        """Rouge au-dessus du plafond, rampe en dessous.

        La frontière est la seule information que la figure doit livrer au
        premier regard ; la nuance sous le plafond est secondaire.
        """
        if v > limite:
            return "dn"
        return _ramp(0.25 + 0.65 * (limite - v) / max(limite - zlo, 1e-9))

    # Le sol se pose au bas du domaine et non à µ* = 1 pt/h : laissé au zéro
    # par défaut, il coupait la surface en son milieu et la moitié basse
    # passait sous un plancher qui n'est le plancher de rien.
    ticks = [(float(k), _num(10.0 ** k, 2) if k < 1 else _num(10.0 ** k, 0))
             for k in range(math.ceil(zlo), math.floor(zhi) + 1)]
    ticks.append((limite, _num(plafond, 1) + " — plafond"))

    b = _plate(384, "Le seuil sur deux axes",
               "Ce que la géométrie et la friction décident ensemble",
               "hauteur : µ* en points par heure")
    # Libellés d'arête réduits à leur valeur : « stop 0,010 % » heurtait les
    # graduations de l'échine, portées de ce même côté. Le sens des deux axes
    # est donné par la ligne de lecture, où il ne coûte aucune place.
    _surface(b, 330, 197, z, zlo, zhi, cx=44.0, cy=11.0, cz=190.0,
             row_labels=[_num(p, 3) + " %" for p in stops],
             col_labels=[_num(f, 3) for f in frictions[:-1]]
                        + [_num(frictions[-1], 3) + " pt"],
             z_ticks=sorted(ticks),
             tip="µ* = {v:.2f} en log10 des points par heure",
             classify=verdict, zero=zlo)

    # Deux pastilles et non une rampe : le rouge n'appartient pas à la rampe,
    # et une légende d'échelle continue décrirait un encodage que la figure
    # n'emploie pas. C'est la couleur qui porte le verdict, pas la nuance.
    b.legend(0, 344, [("hm5", "seuil sous le plafond — rentabilité possible"),
                      ("dn", "seuil au-dessus — impossible à toute dérive")],
             step=300, kind="swatch")
    _source(b, "Arête gauche : largeur du stop. Arête droite : friction "
               "aller-retour, en points. La hauteur est le seuil de "
               "rentabilité en échelle logarithmique ; les graduations "
               "portent sa valeur réelle en points par heure. Une maille "
               "rouge dépasse le plafond de dérive plausible de "
               + _num(plafond, 1) + " points par heure : sa rentabilité est "
               "impossible, quelle que soit la dérive du marché. Seule la "
               "rangée du stop le plus serré y tombe, et elle y tombe pour "
               "toutes les frictions.")
    return b.render(
        "Surface du seuil de rentabilité sur le plan de la largeur de stop et "
        "de la friction, avec le verdict d atteignabilité en couleur")


FIGURES["discseuil3d"] = fig_seuil_surface


# ---------------------------------------------------------------------------
# Figure 23 — l'identité de Wald, montrée plutôt qu'énoncée
# ---------------------------------------------------------------------------


def fig_wald() -> str:
    """Le théorème d'arrêt optionnel, en deux cadres et sans une ligne d'algèbre.

    C'est le résultat qui fonde les trois documents, et il n'avait jusqu'ici
    aucune figure — il vivait dans une identité posée en prose et dans des
    tables. Le lecteur devait le croire sur parole.

    Le cadre du haut porte quatre droites, une par géométrie, donnant
    l'espérance nette selon la dérive du marché. Trois choses s'y lisent d'un
    coup, et aucune ne demande de calcul.

    D'abord **l'ordonnée à l'origine**. À dérive nulle, les quatre droites
    valent exactement `−c/L` — la friction rapportée au risque nominal — et
    aucune n'atteint zéro. Aucune géométrie ne crée d'espérance : c'est la loi
    nulle du dépôt, et elle est ici un point sur un axe.

    Ensuite **la pente**, qui est `E[τ∧T]/60L` : elle mesure le temps de
    marché que la géométrie achète par unité de risque. C'est la seule chose
    que le choix des barrières décide.

    Enfin **le point de croisement**, qui est `µ*`. La droite du stop déclaré
    ne croise jamais zéro dans la bande de dérive plausible ; les trois autres
    la croisent avant même sa borne basse.

    Le cadre du bas donne la pente à sa source : le temps de marché acheté
    croît comme le carré de la largeur du stop tant que la séance ne borne
    rien, puis sature contre elle. C'est cette saturation qui rend l'optimum
    intérieur — la droite la plus raide n'est pas la plus large.
    """
    from . import quant as Q
    from . import seuil as S

    stops = (0.010, 0.050, 0.100, 0.200)
    classes = ("neg", "s3", "s1", "s2")
    gs = [S.geometry(p) for p in stops]
    bas, haut = S.PLAUSIBLE_DRIFT_PER_HOUR
    mu_max = haut * 1.06

    b = _plate(420, "Arrêt optionnel",
               "Ce que la géométrie achète, et ce qu'elle ne crée pas",
               "E[R] = (µ·E[τ∧T] − c) / L")
    # La légende monte sous le bandeau : posée en pied, elle venait heurter
    # l'intitulé d'abscisse du second cadre, et quatre traits à identifier se
    # lisent mieux avant les courbes qu'après.
    b.legend(66, 56, [(c, _num(g.stop_pct, 3) + " %")
                      for g, c in zip(gs, classes)], step=116, kind="line")

    # --- cadre du haut : quatre droites, une par géométrie ----------------
    # Domaine déduit des quatre droites elles-mêmes, bornes comprises : une
    # fenêtre écrite à la main couperait l'ordonnée à l'origine de la
    # géométrie serrée, qui est justement ce que le cadre existe pour montrer.
    vals = [g.expectancy_r(m) for g in gs for m in (0.0, mu_max)]
    lo = min(vals) - 0.10 * (max(vals) - min(vals))
    hi = max(vals) + 0.09 * (max(vals) - min(vals))
    p1 = Panel(b, 66, 92, W - 116, 158,
               title="Espérance nette selon la dérive du marché",
               readout="quatre géométries, une friction")
    p1.domain(0.0, mu_max, lo, hi)
    p1.band_x(bas, haut, "wash")
    p1.frame()
    pas = 0.2
    p1.grid_y([pas * k for k in range(math.ceil(lo / pas),
                                      math.floor(hi / pas) + 1)],
              lambda v: _num(v, 1), "multiples du risque")
    p1.grid_x([0.0, 0.8, 1.6, 2.4, 3.2], lambda v: _num(v, 1),
              "dérive du marché, en points d'indice par heure")
    p1.hline(0.0, "lvl strong")
    for g, cls in zip(gs, classes):
        p1.path([(0.0, g.expectancy_r(0.0)), (mu_max, g.expectancy_r(mu_max))],
                cls, tip=f"stop {_num(g.stop_pct, 3)} % — pente "
                         f"{g.exposure_min / 60.0 / g.stop_points:.3f} R par pt/h")
        # L'ordonnée à l'origine est la loi nulle : on la marque, elle ne se
        # déduit pas d'une droite qu'on suit du regard jusqu'à l'axe.
        p1.dot(0.0, g.expectancy_r(0.0), cls, r=3.5,
               tip=f"stop {_num(g.stop_pct, 3)} % — à dérive nulle, "
                   f"−c/L = {g.expectancy_r(0.0):+.3f} R")
    # Aucun libellé posé au bout des droites : celles de 0,100 % et 0,200 %
    # se recouvrent presque partout — c'est le fond du propos, l'optimum
    # étant plat — et deux libellés y tomberaient l'un sur l'autre. La
    # légende du haut fait l'identification.
    p1.label(0.0, gs[0].expectancy_r(0.0), "à dérive nulle : −c/L",
             dx=10, dy=-11, cls="dl halo")
    p1.label(0.06, hi * 0.60,
             "0,100 % et 0,200 % se recouvrent : l'optimum est plat",
             dx=0, dy=0, cls="dl halo")
    p1.label(mu_max * 0.5, gs[0].expectancy_r(mu_max * 0.5),
             "la géométrie déclarée ne croise jamais le zéro",
             dx=0, dy=-9, anchor="middle", cls="dl halo")
    p1.label((bas * haut) ** 0.5, hi, "dérive plausible", dx=0, dy=13,
             anchor="middle", cls="tk halo")

    # --- cadre du bas : la pente à sa source ------------------------------
    fins = S.scan()
    xs = [g.stop_pct for g in fins]
    taus = [g.exposure_min for g in fins]
    p2 = Panel(b, 66, 306, W - 116, 66, title="Temps de marché acheté",
               readout="E[τ∧T], borné par la séance")
    # Le domaine monte jusqu'à la séance entière : c'est le plafond contre
    # lequel l'exposition sature, et un cadre calé sur le seul maximum
    # observé aurait rejeté ce plafond hors du cadre — la ligne s'y serait
    # tout de même tracée, `hline` ne découpant pas.
    p2.domain(min(xs) / 1.35, max(xs) * 1.35, 0.0, Q.SESSION_MIN * 1.06,
              xlog=True)
    p2.frame()
    p2.grid_y([0, 130, 260, 390], lambda v: f"{v:g}", "minutes")
    p2.grid_x([0.01, 0.025, 0.05, 0.1, 0.2, 0.4], lambda v: _num(v, 3) + " %",
              "largeur du stop, en % de l'indice")
    p2.hline(Q.SESSION_MIN, "lvl")
    p2.label(max(xs) * 1.3, Q.SESSION_MIN, "séance entière", dx=-4, dy=-5,
             anchor="end", cls="tk halo")
    p2.path(list(zip(xs, taus)), "px")
    for g, cls in zip(gs, classes):
        p2.dot(g.stop_pct, g.exposure_min, cls, r=3.5,
               tip=f"stop {_num(g.stop_pct, 3)} % — {g.exposure_min:.1f} min")

    _source(b, "Chaque droite est une géométrie. Son ordonnée à l'origine est "
               "la friction rapportée au risque nominal, et elle est négative "
               "pour les quatre : à dérive nulle, aucune géométrie ne rend une "
               "espérance positive, quel que soit le placement des barrières. "
               "Sa pente est le temps de marché acheté par unité de risque, et "
               "c'est la seule chose que le choix des barrières décide. Son "
               "croisement avec le zéro est le seuil µ*. La géométrie déclarée "
               "ne croise pas le zéro dans la bande de dérive plausible ; les "
               "trois autres le croisent avant sa borne basse. Le cadre du bas "
               "donne la pente à sa source — et montre pourquoi la plus raide "
               "n'est pas la plus large, l'exposition saturant contre la "
               "séance.")
    return b.render(
        "Espérance nette selon la dérive pour quatre géométries, et temps de "
        "marché acheté selon la largeur du stop")


FIGURES["discwald"] = fig_wald


def fig_wald_surface() -> str:
    """L'espérance sur le plan (géométrie × dérive), et la frontière du zéro.

    La figure précédente coupe ce plan en quatre droites. Celle-ci le montre
    entier, et la couleur y code le signe : la seule chose que le lecteur ait
    à trouver est la ligne où la surface change de couleur, qui est la
    frontière `µ = µ*`.

    Ce que la figure donne à lire est la **forme de la frontière**, et une
    seule chose la décrit : elle recule vers les fortes dérives à mesure que
    le stop se resserre. À la géométrie déclarée, la rangée entière reste
    rouge — son seuil dépasse la dérive la plus forte du cadre, et aucune
    dérive plausible ne la rend rentable.

    Ce que la figure ne donne **pas** à lire, et qu'il faut chercher dans la
    figure précédente : que l'arête de la dérive nulle soit négative sur toute
    sa longueur. La couleur d'une maille suit la moyenne de ses quatre coins,
    et les mailles qui bordent cette arête empruntent la moitié de leur
    moyenne à la colonne voisine, où la dérive n'est plus nulle. L'ordonnée à
    l'origine des quatre droites du cadre plan la porte exactement ; ici elle
    serait affirmée sans être montrée.
    """
    from . import seuil as S

    stops = (0.010, 0.025, 0.050, 0.100, 0.200, 0.400)
    derives = (0.0, 0.8, 1.6, 2.4, 3.2)
    gs = [S.geometry(p) for p in stops]
    z = [[g.expectancy_r(m) for m in derives] for g in gs]

    plat = [v for ligne in z for v in ligne]
    # Le domaine suit les données, marge comprise, et le zéro y tombe où il
    # tombe : c'est la frontière que la couleur code, pas une borne du cadre.
    marge = (max(plat) - min(plat)) * 0.055
    zlo, zhi = min(plat) - marge, max(plat) + marge

    def signe(v: float) -> str:
        """Rouge sous zéro, rampe au-dessus, et rien entre les deux.

        Pas de bande neutre ici, à la différence du plan d'espérance : le
        jeton neutre est un gris très sombre, et sur ce fond une maille qui
        le porte disparaît. Un quart de la surface passe au voisinage de zéro
        — c'est justement la région que la figure existe pour montrer — et
        l'y peindre en noir revenait à l'effacer. La hauteur porte déjà la
        grandeur ; la couleur ne porte que le signe.
        """
        if v < 0.0:
            return "dn"
        return _ramp(0.35 + 0.60 * min(1.0, v / max(zhi, 1e-9)))

    b = _plate(372, "Arrêt optionnel, sur deux axes",
               "Où l'espérance change de signe",
               "hauteur et couleur : E[R] par trade")
    # Hauteur ramenée à 140 : à 170, la graduation la plus haute de l'échine
    # remontait au-dessus du filet de bandeau et venait sur le titre.
    _surface(b, 314, 160, z, zlo, zhi, cx=32.0, cy=10.0, cz=140.0,
             row_labels=[_num(p, 3) + " %" for p in stops],
             col_labels=[_num(d, 1) for d in derives[:-1]]
                        + [_num(derives[-1], 1) + " pt/h"],
             z_ticks=[(0.2 * k, _num(0.2 * k, 1) + " R")
                      for k in range(math.ceil(zlo / 0.2),
                                     math.floor(zhi / 0.2) + 1)],
             tip="E[R] = {v:+.3f} R", classify=signe, zero=zlo)
    b.annotation(0, 292, "la frontière recule vers les fortes dérives à "
                         "mesure que le stop se resserre")
    b.legend(0, 314, [("dn", "espérance négative — µ < µ*"),
                      ("hm6", "espérance positive — µ > µ*")],
             step=300, kind="swatch")
    _source(b, "Arête gauche : largeur du stop. Arête droite : dérive du "
               "marché, en points d'indice par heure. La hauteur et la "
               "couleur portent la même grandeur, l'espérance nette par "
               "trade ; la couleur en isole le signe, qui est ce que la "
               "figure existe pour donner. La frontière rouge-bleu est "
               "l'ensemble des couples où µ = µ*. Elle recule vers les "
               "fortes dérives à mesure que le stop se resserre, et la rangée "
               "du stop déclaré reste entièrement rouge : son seuil dépasse la "
               "dérive la plus forte du cadre. La couleur d'une maille suit la "
               "moyenne de ses quatre coins ; le signe exact à dérive nulle se "
               "lit sur l'ordonnée à l'origine des droites de la figure "
               "précédente, non ici.")
    return b.render(
        "Surface de l espérance nette par trade sur le plan de la largeur de "
        "stop et de la dérive du marché, avec la frontière du signe")


FIGURES["discwald3d"] = fig_wald_surface


# ---------------------------------------------------------------------------
# Figure 25 — le même chiffre, à cinq tailles d'échantillon
# ---------------------------------------------------------------------------


def fig_echelle() -> str:
    """Pourquoi le même Sharpe observé est du bruit ici et un fait là.

    C'est l'intuition centrale des trois documents, et elle n'avait pas
    d'image. Un opérateur qui relève un Sharpe de 0,10 par décision sur cent
    vingt-cinq décisions relève un événement ordinaire ; le même chiffre sur
    deux mille décisions est un événement à quatre pour un million. Rien n'a
    changé du chiffre — seul l'échantillon a changé, et avec lui la loi nulle
    à laquelle on le compare.

    Le cadre du haut montre cette loi nulle à cinq tailles. Chaque densité est
    ramenée à la même hauteur : c'est sa **largeur** qui porte l'information,
    et la comparer à hauteur égale est la seule façon de voir se resserrer
    l'écart-type en `1/√N`. La part de la loi au-delà du chiffre revendiqué
    est teintée, et elle fond d'une rangée à l'autre.

    Le cadre du bas donne les deux routes du mur d'échantillon sous leur
    forme commune. Toutes deux valent `K/√N` — le test ordinaire avec
    `K = z_α + z_β`, la taxe de sélection avec `K = √(2·ln B)` — et c'est
    pourquoi elles s'accordent : à seize configurations les deux constantes
    valent 2,49 et 2,35, soit six pour cent d'écart. **Deux routes qui ne
    partagent aucune hypothèse mais partagent leur forme.** Leurs croisements
    avec le Sharpe revendiqué sont exactement les deux nombres que la table
    du mur publie.
    """
    from .costs import norm_cdf, significance_constant

    sharpe = 0.10
    budget = 2.0 ** 4
    tailles = (125, 250, 500, 1000, 2000)
    k_test = significance_constant()
    k_taxe = math.sqrt(2.0 * math.log(budget))

    b = _plate(440, "Échelle",
               "Le même chiffre, à cinq tailles d'échantillon",
               f"Sharpe revendiqué {_num(sharpe, 2)} par décision")

    # --- cadre du haut : la loi nulle se resserre en 1/√N -----------------
    # Domaine déduit de la plus large des cinq lois : à N = 125 l'écart-type
    # vaut 0,089, et une fenêtre plus étroite couperait ses queues.
    demi = 2.9 / math.sqrt(min(tailles))
    p1 = Panel(b, 92, 78, W - 168, 150,
               title="La loi nulle du Sharpe observé",
               readout="densités ramenées à la même hauteur")
    p1.domain(-demi, demi, 0.0, float(len(tailles)))
    p1.frame()
    p1.grid_x([-0.2, -0.1, 0.0, 0.1, 0.2], lambda v: _num(v, 2),
              "Sharpe observé par décision")
    # Les rangées vont de la plus large en bas à la plus resserrée en haut :
    # la graduation doit donc relire la liste à l'envers.
    p1.grid_y([k + 0.5 for k in range(len(tailles))],
              lambda v: f"N = {tailles[len(tailles) - 1 - int(v)]}")
    for rang, n in enumerate(tailles):
        # Les rangées se lisent de bas en haut par taille croissante : la
        # plus large en bas, la plus resserrée en haut.
        base = float(len(tailles) - 1 - rang)
        sd = 1.0 / math.sqrt(n)
        pts = [(-demi + 2.0 * demi * i / 120.0, 0.0) for i in range(121)]
        courbe = [(x, base + 0.92 * math.exp(-0.5 * (x / sd) ** 2))
                  for x, _ in pts]
        # La queue au-delà du chiffre revendiqué, teintée : c'est elle qui
        # fond d'une rangée à l'autre, et c'est la p-valeur.
        queue = [(x, y) for x, y in courbe if x >= sharpe]
        if queue:
            # La queue est teintée du jeton de série et non du gris : celui-ci
            # se confond avec le fond, et la part que la figure existe pour
            # montrer se lisait comme un rectangle noir.
            p1.area([(sharpe, base + 0.92 * math.exp(-0.5 * (sharpe / sd) ** 2))]
                    + queue, base, "area ar1")
        # Un seul jeton pour les cinq courbes : ce qui les distingue est leur
        # largeur, et deux couleurs y ajouteraient une différence qui n'existe
        # pas.
        p1.path(courbe, "s2",
                tip=f"N = {n} — écart-type de la loi nulle {sd:.4f}")
        p = 1.0 - norm_cdf(sharpe / sd)
        p1.label(demi, base + 0.30, _pourcent(p), dx=-6, anchor="end",
                 cls="dl halo")
    p1.vline(sharpe, "lvl strong")
    p1.label(sharpe, float(len(tailles)), "chiffre revendiqué", dx=6, dy=13,
             cls="tk halo")

    # --- cadre du bas : les deux routes sous leur forme commune -----------
    n_lo, n_hi = 100.0, 4000.0
    p2 = Panel(b, 92, 296, W - 168, 76, title="Les deux routes du mur",
               readout="toutes deux en K / √N")
    p2.domain(n_lo, n_hi, 0.0, k_test / math.sqrt(n_lo) * 1.12, xlog=True)
    p2.frame()
    p2.grid_y([0.0, 0.1, 0.2], lambda v: _num(v, 2), "Sharpe requis")
    p2.grid_x([125, 250, 500, 1000, 2000, 4000], lambda v: f"{v:g}",
              "décisions enregistrées")
    p2.hline(sharpe, "lvl strong")
    # Les deux courbes se recouvrent presque : c'est le propos, et c'est
    # aussi ce qui interdit de poser leurs deux libellés au même endroit. On
    # les écarte de part et d'autre de la ligne du chiffre revendiqué.
    for k, cls, nom, dy, anc in ((k_taxe, "s3", "taxe", -10.0, "end"),
                                 (k_test, "s1", "test t", 16.0, "start")):
        p2.path([(n_lo * (n_hi / n_lo) ** (i / 80.0),
                  k / math.sqrt(n_lo * (n_hi / n_lo) ** (i / 80.0)))
                 for i in range(81)], cls,
                tip=f"{nom} — K = {k:.2f}")
        n_star = (k / sharpe) ** 2
        p2.dot(n_star, sharpe, cls, r=3.5,
               tip=f"{nom} — {n_star:.0f} décisions")
        p2.label(n_star, sharpe, f"{nom} · {_num(n_star, 0)}",
                 dx=6.0 if anc == "start" else -6.0, dy=dy,
                 anchor=anc, cls="dl halo")

    # Deux entrées et non trois : la troisième désignait la teinte de queue
    # par une classe de remplissage, que la légende de trait rendait sans
    # contour — donc invisible, et débordant du cadre.
    b.legend(92, 420, [("s1", f"test t — K = {_num(k_test, 2)}"),
                       ("s3", f"taxe de sélection — K = {_num(k_taxe, 2)}")],
             step=250, kind="line")
    _source(b, "Cadre du haut : la loi nulle du Sharpe observé, à cinq "
               "tailles d'échantillon. Les densités sont ramenées à la même "
               "hauteur ; c'est leur largeur qui porte l'information, et elle "
               "décroît en racine de l'échantillon. La part teintée est la "
               "probabilité d'observer au moins le chiffre revendiqué sans "
               "aucune compétence : elle passe de 13 % à quatre par million "
               "sur la plage. Cadre du bas : les deux routes du mur ont la "
               "même forme, K sur racine de N, et ne diffèrent que par leur "
               "constante — d'où leur accord, qui ne tient à aucune "
               "hypothèse partagée.")
    return b.render(
        "Loi nulle du Sharpe observé à cinq tailles d échantillon, et les "
        "deux routes du mur sous leur forme commune")


FIGURES["discechelle"] = fig_echelle
