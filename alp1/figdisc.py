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
    """Décisions requises pour franchir le seuil déflaté à `budget` essais."""
    if sharpe <= 0.0:
        return math.inf
    return 2.0 * math.log(max(budget, 2.0)) / (sharpe ** 2)


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

    Elle porte la classe `lg` et dépasse cinquante-cinq caractères, ce qui la
    fait extraire du SVG et rendre en texte sous la légende quand le document
    est construit. Dans un aperçu isolé, elle reste à sa place et ne heurte
    rien, la bande lui étant réservée.
    """
    board.add(f'<text class="lg" x="0" y="{board.height - 8:.1f}">'
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


def _surface(board: Board, ox: float, oy: float, z: list[list[float]],
             zlo: float, zhi: float, *, cx: float, cy: float, cz: float,
             row_labels: list[str], col_labels: list[str],
             z_ticks: list[tuple[float, str]], tip: str = "{v:+.3f}",
             classify=None, zero: float = 0.0) -> None:
    """Surface isométrique munie d'une échine de hauteur.

    Trois choses distinguent ce rendu d'une simple projection. Le **sol** est
    une grille de filets et non un aplat, ce qui laisse voir la position des
    mailles sans peser. L'**échine** verticale à gauche porte les graduations
    de hauteur&nbsp;: sans elle une projection isométrique est ambiguë, et le
    lecteur ne peut convertir une élévation en grandeur. Les **mailles** sont
    séparées par un filet couleur papier, jamais par une bordure sombre.

    Le remplissage suit par défaut la rampe séquentielle, la hauteur étant une
    grandeur ordonnée. Les surfaces signées passent un `classify` divergent.
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

    # Mailles peintes de l'arrière vers l'avant : occultation correcte sans
    # moteur de rendu.
    quads = []
    for i in range(ni - 1):
        for j in range(nj - 1):
            corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            pts = [proj(a, bb, z[a][bb]) for a, bb in corners]
            mean = sum(z[a][bb] for a, bb in corners) / 4.0
            quads.append((i + j, pts, mean))
    for _, pts, val in sorted(quads, key=lambda q: -q[0]):
        pt = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        board.add(f'<polygon class="mesh {classify(val)}" points="{pt}">'
                  f'<title>{_esc(tip.format(v=val))}</title></polygon>')

    # L'échine de hauteur, à gauche du coin le plus à gauche. Sans
    # graduation, on ne la trace pas : un axe nu se lit comme inachevé. Le
    # garde porte sur ce bloc seul — les libellés d'arêtes qui suivent sont
    # rendus dans tous les cas.
    if z_ticks:
        edge = ox - (nj - 1) * cx - 26.0
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
        board.add(f'<text class="tk halo" x="{x - 11:.1f}" y="{y + 12:.1f}" '
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
    temps avant de savoir ? Elle montre du même coup pourquoi la taxe de
    multiplicité est supportable — l'arête des leviers est presque plate
    devant celle du Sharpe, parce que le seuil croît en racine du logarithme
    du budget alors que l'échantillon décroît comme le carré du Sharpe.
    """
    ks = [0, 2, 4, 6]
    srs = [0.05, 0.075, 0.10, 0.15]
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
               "Sharpe revendiqué par décision. Hauteur plafonnée à six ans, à "
               "deux décisions par séance.")
    return b.render(
        "Surface du nombre d années requises selon les leviers ouverts et le "
        "Sharpe revendiqué par décision")


# ---------------------------------------------------------------------------
# Figure 3 — le plan d'espérance, sans puis avec clairvoyance
# ---------------------------------------------------------------------------


def fig_plane() -> str:
    """L'espérance selon la sélectivité et la mise, sans puis avec information.

    À gauche, l'opérateur sans clairvoyance : la surface est plate, et plate
    en négatif. Ni la sélectivité ni le dimensionnement ne la déforment,
    parce qu'aucun des deux ne porte d'information — c'est le théorème
    d'arrêt optionnel, transposé du choix des barrières au choix des trades.
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
    span = max(abs(v) for r in z_null + z_edge for v in r) or 0.05

    #: Largeur de la bande neutre, en unités de risque. Le seuil est une
    #: grandeur économique — en deçà, l'espérance ne finance rien — et non une
    #: fraction de l'étendue observée. Le calculer en fraction ferait
    #: disparaître dans le neutre toute la surface sans clairvoyance, dont les
    #: valeurs sont vingt fois plus petites que celles de sa voisine.
    NEUTRE = 0.02

    def diverging(v: float) -> str:
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

    b = _plate(368, "Invariance",
               "Espérance selon la sélectivité et la mise",
               "sélectivité × mise")
    for idx, (sub, z) in enumerate((("sans clairvoyance", z_null),
                                    ("avec clairvoyance", z_edge))):
        ox = 208 + idx * 300
        b.add(f'<text class="lg" x="{ox:.1f}" y="72" text-anchor="middle">'
              f'{_esc(sub)}</text>')
        _surface(b, ox, 224, z, -span, span, cx=32.0, cy=10.0, cz=134.0,
                 row_labels=[f"{p:.0%}" for p in selectivity],
                 col_labels=[f"{s:g} R" for s in sizing],
                 z_ticks=([(-span, _num(-span, 2)), (0.0, "0"),
                           (span, _num(span, 2))] if idx == 0 else []),
                 tip="{v:+.3f} R", classify=diverging)
    b.legend(0, 322, [("negf", "espérance négative"),
                      ("wash", "neutre, sous 0,02 R"),
                      ("hm6", "espérance positive")], step=178)
    _source(b, "Arête gauche : part des setups retenus. Arête droite : mise en "
               "unités de risque. Sans information, aucun réglage ne déforme "
               "la surface.")
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
            # Adversaire analytique : on trace sa densité normale, mise à
            # l'échelle du même cadre que les histogrammes voisins.
            sd = t.null_sd or (hi - lo) / 6.0
            for i in range(n_bins):
                c = lo + (i + 0.5) * largeur
                bins[i] = math.exp(-0.5 * ((c - t.null_mean) / sd) ** 2)
        pic = max(bins) or 1.0

        p = Panel(b, x0, y0, larg, 96, title=COURT.get(t.key, t.key))
        p.domain(lo, hi, 0.0, pic * 1.18)
        p.grid_x([t.null_mean, t.observed], lambda z: _num(z, 2))

        if t.sample:
            for i, c in enumerate(bins):
                if c <= 0.0:
                    continue
                centre = lo + (i + 0.5) * largeur
                p.vbar(centre, 0.0, c, (larg / n_bins) - 0.8,
                       "barfill" if centre < t.q95 else "barfill inner",
                       f"{_num(centre, 3)} — {int(c)} tirage(s)")
        else:
            # Aire sous la densité, échantillonnée finement : une loi étroite
            # devant un domaine large reste visible en courbe là où des barres
            # la réduiraient à un trait unique.
            sd = t.null_sd or (hi - lo) / 6.0
            fins = [(lo + k * (hi - lo) / 240.0,
                     pic * math.exp(-0.5 * ((lo + k * (hi - lo) / 240.0
                                             - t.null_mean) / sd) ** 2))
                    for k in range(241)]
            p.area(fins, 0.0, "barfill",
                   f"densité analytique, écart-type {sd:.4f}")

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
                 + " : leur densité est tracée, non simulée. ")
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

    b = _plate(292, "Attribution",
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
    p.domain(ks[3], horizon, lo - marge, hi + marge)
    p.grid_y([lo, (lo + hi) / 2.0, hi], lambda v: _num(v, 2))
    p.grid_x([250, 500, 1000, horizon], lambda v: f"{v:g}",
             label="décisions accumulées")

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

    d = Panel(b, 372, 66, W - 372, 186, title="Répartition")
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
    p.domain(sans[0][0], max(x for x, _, _ in tout), lo, hi)
    p.grid_y([lo, (lo + hi) / 2.0, hi], lambda v: _num(v, 2))
    dernier = max(x for x, _, _ in tout)
    p.grid_x([FEN, dernier // 3, 2 * dernier // 3, dernier],
             lambda v: f"{v:g}", label="décision courante")

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
    _source(b, "Abscisse : rang de la décision courante. Ordonnée : moyenne des "
               f"{FEN} décisions précédentes. La bande est l'intervalle à 95 pour "
               "cent de cette moyenne.")
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
                  f'le levier « {k} »</title></rect>')

    for i, k in enumerate(leviers):
        n = sum(1 for c in COUCHES if c[2] == k)
        x = gx + i * cw + cw / 2
        b.add(f'<text class="tk" x="{x:.1f}" y="{gy - 22:.1f}" '
              f'text-anchor="middle">{_esc(k)}</text>')
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
