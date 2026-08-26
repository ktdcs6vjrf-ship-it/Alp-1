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
from .figterm import Board, Panel, _esc, _num
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

    # L'échine de hauteur, à gauche du coin le plus à gauche.
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

    # Libellés des deux arêtes du sol, posés au-delà du contour.
    for k, lab in enumerate(row_labels):
        if not lab:
            continue
        x, y = proj(k, nj - 1, floor_z)
        board.add(f'<text class="tk halo" x="{x - 9:.1f}" y="{y + 13:.1f}" '
                  f'text-anchor="end">{_esc(lab)}</text>')
    for k, lab in enumerate(col_labels):
        if not lab:
            continue
        x, y = proj(ni - 1, k, floor_z)
        board.add(f'<text class="tk halo" x="{x + 9:.1f}" y="{y + 13:.1f}">'
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
    _surface(b, 330, 214, z, 0.0, 6.0, cx=58.0, cy=19.0, cz=152.0,
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
# Figure 2 — la surface de puissance
# ---------------------------------------------------------------------------


def fig_power() -> str:
    """Probabilité de détecter un avantage, par échantillon et par effet.

    Le relief a la forme d'une marche : sous une certaine combinaison la
    détection est un tirage à pile ou face, au-delà elle est acquise. Situer
    l'opérateur sur cette marche est tout ce qu'un protocole préenregistré a
    besoin de savoir.
    """
    ns = [250, 500, 1000, 2000]
    bits_grid = [0.005, 0.010, 0.020, 0.040]

    def power(n: int, bits: float) -> float:
        besoin = trades_for_information(bits)
        if besoin <= 0.0 or not math.isfinite(besoin):
            return 0.0
        lam = 1.96 * math.sqrt(max(n, 1) / besoin)
        return min(1.0, max(0.0, _norm_cdf(lam - 1.96)))

    z = [[power(n, bt) for bt in bits_grid] for n in ns]

    b = _plate(384, "Puissance", "La puissance de détection",
               "test G informationnel, seuil 5 %")
    _scale_legend(b, 0, 62, "0 %", "100 %", "probabilité de détection")
    _surface(b, 330, 214, z, 0.0, 1.0, cx=58.0, cy=19.0, cz=152.0,
             row_labels=[f"{n}" for n in ns],
             col_labels=[_num(bt, 3) for bt in bits_grid],
             z_ticks=[(0.0, "0 %"), (0.5, "50 %"), (0.80, "80 %"),
                      (1.0, "100 %")],
             tip="puissance {v:.0%}")
    _source(b, "Arête gauche : décisions enregistrées. Arête droite : bits par "
               "décision. Sous le palier de 80 %, l'absence de preuve ne prouve rien.")
    return b.render(
        "Surface de la puissance de détection selon le nombre de décisions "
        "et l information portée par chacune")


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
        _surface(b, ox, 216, z, -span, span, cx=32.0, cy=13.0, cz=112.0,
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
    """L'observé posé sur chacune de ses cinq lois nulles.

    Une ligne par loi : l'étendue de la loi nulle jusqu'à son quantile à
    95 %, et le trait de l'observé. Un avantage n'est déclaré que si les cinq
    traits passent à droite de leur seuil ; la planche rend visible le fait
    qu'un opérateur peut battre trois lois et rester réfuté.
    """
    #: Les intitulés complets des lois débordent la gouttière. On les abrège
    #: ici, et la table du document porte l'énoncé entier — une figure n'a pas
    #: à répéter ce qu'une table dit mieux.
    COURT = {"mecanique": "Règle scellée", "selection": "Sélection au sort",
             "timing": "Issues permutées", "abstention": "Indépendance",
             "bootstrap": "Bootstrap par blocs"}

    cas = (("sans clairvoyance", 0.0), ("clairvoyance franche", 0.55))
    b = _plate(392, "Lois nulles",
               "Statistique observée et loi nulle, par test",
               f"{SESSIONS} séances, seuil 95 %")

    gauche = 138.0
    for idx, (titre, skill) in enumerate(cas):
        j = synthesise(skill=skill, n_sessions=SESSIONS)
        v = evaluate(j, draws=300)
        y0 = 66 + idx * 150
        p = Panel(b, gauche, y0, W - gauche, 112)
        vals = [t.observed for t in v.tests] + [t.q95 for t in v.tests]
        lo, hi = min(vals + [0.0]), max(vals + [0.0])
        marge = 0.14 * (hi - lo) + 1e-6
        p.domain(lo - marge, hi + marge, -0.65, len(v.tests) - 0.35)

        b.add(f'<text class="lg" x="0" y="{y0 - 6:.1f}">{_esc(titre)}</text>')
        b.add(f'<text class="tk" x="{W:.1f}" y="{y0 - 6:.1f}" '
              f'text-anchor="end">{len(v.beaten)} loi(s) sur 5 battue(s)</text>')

        p.grid_x([lo, (lo + hi) / 2.0, hi], lambda x: _num(x, 2))
        p.vline(0.0, "zero")

        for k, t in enumerate(v.tests):
            row = len(v.tests) - 1 - k
            p.hbar(row, t.null_mean, t.q95, 10.0, "wash",
                   f"{t.label} — loi nulle jusqu'à {t.q95:+.4f}")
            p.vbar(t.q95, row - 0.30, row + 0.30, 1.6, "negf",
                   f"seuil 95 % : {t.q95:+.4f}")
            p.vbar(t.observed, row - 0.32, row + 0.32, 3.6,
                   "s1f" if t.beats else "wash",
                   f"{t.label} — observé {t.observed:+.4f} · {t.reading}")
            b.add(f'<text class="tk" x="{gauche - 12:.1f}" '
                  f'y="{p.sy(row) + 3.5:.1f}" text-anchor="end">'
                  f'{_esc(COURT.get(t.key, t.label))}</text>')

    b.legend(gauche, 366, [("wash", "étendue de la loi nulle"),
                           ("negf", "seuil 95 %"),
                           ("s1f", "observé, loi battue")], step=160)
    _source(b, "La statistique est l'espérance par décision, en unités de risque, "
               "sauf pour l'abstention où elle est l'information mutuelle en bits.")
    return b.render(
        "Cinq lois nulles et la statistique observée sur chacune, pour un "
        "opérateur sans clairvoyance puis avec")


# ---------------------------------------------------------------------------
# Figure 5 — la décomposition de Shapley
# ---------------------------------------------------------------------------


def fig_attribution() -> str:
    """Où l'avantage loge, selon l'endroit où on l'a planté.

    La planche est un contrôle avant d'être une illustration : on plante la
    compétence dans un levier connu, et la décomposition doit l'y désigner.
    Une méthode d'attribution qui répartirait l'avantage sur les quatre
    leviers serait fausse, et cette figure le montrerait.
    """
    from .attribution import decompose

    cas = (("plantée dans l'entrée", 0.45, 0.0),
           ("plantée dans la taille", 0.0, 0.45),
           ("plantée dans les deux", 0.45, 0.45))
    b = _plate(292, "Attribution",
               "Part de chaque levier selon l'emplacement de la compétence",
               "valeur de Shapley, 16 coalitions")

    gauche, largeur, ecart = 70.0, 158.0, 30.0
    haut = 1.05 * max(
        s.value for _, sk, sz in cas
        for s in decompose(synthesise(skill=sk, size_skill=sz,
                                      n_sessions=SESSIONS)).shares)

    for idx, (titre, skill, size_skill) in enumerate(cas):
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
            porteur = s.key == d.carrier.key
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
                      f'{_esc(s.key)}</text>')
            # Étiquette directe sur le seul levier porteur : le reste se lit
            # à l'axe, et une valeur sur chaque barre serait du bruit.
            if porteur:
                p.label(s.value, row, f"{s.fraction:.0%}", dx=6)

    b.legend(gauche, 266, [("s1f", "levier désigné porteur"),
                           ("hm2", "autres leviers")], step=182)
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
    ns = ((1000, "hm7"), (3000, "hm5"), (10000, "hm3"))
    b = _plate(316, "Taxe de multiplicité",
               "Seuil déflaté selon le nombre de leviers ouverts",
               "Bailey et López de Prado")
    p = Panel(b, 62, 62, W - 62, 186)
    p.domain(0, 8, 0.0, 0.105)
    p.grid_y([0.0, 0.025, 0.05, 0.075, 0.10], lambda v: _num(v, 3))
    p.grid_x(list(range(9)), lambda v: f"{v:g}",
             label="leviers discrétionnaires ouverts")

    for n, cls in ns:
        pts = [(k, deflated_threshold_sharpe(max(2.0, 2.0 ** k), n))
               for k in range(9)]
        p.path(pts, cls)
        # Étiquette directe au bout de la courbe : pas de boîte de légende à
        # traverser des yeux pour identifier trois traits.
        p.label(8, pts[-1][1], f"{n:,}".replace(",", " ") + " décisions",
                dx=-4, anchor="end", cls="dl halo")

    p.vline(K_LEVERS, "lvl strong")
    p.label(K_LEVERS, 0.099, f"{K_LEVERS} leviers recensés", dx=7)
    for n, cls in ns:
        val = deflated_threshold_sharpe(max(2.0, 2.0 ** K_LEVERS), n)
        p.dot(K_LEVERS, val, cls.replace("hm", "s") if False else "s1",
              f"{K_LEVERS} leviers · {n} décisions · seuil {val:.4f}", r=3.4)

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
    p.tag(5.0, "avantage déclarable", side="left")

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
        b.add(f'<line class="ba" x1="{p.sx(0.104):.1f}" y1="{p.sy(2.30):.1f}" '
              f'x2="{p.sx(haut):.1f}" y2="{p.sy(2.30):.1f}"/>')

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
    "discpower": fig_power,
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

    p05, p25, p50, p75, p95 = (q(v) for v in (0.05, 0.25, 0.50, 0.75, 0.95))
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
    for v, lab in ((p05, "P5"), (p25, "P25"), (p75, "P75"), (p95, "P95")):
        g.vline(v, "lvl")
    g.vline(p50, "lvl strong")
    g.label(p50, pic * 1.0, "médiane", dx=5, cls="tk halo")

    d = Panel(b, 372, 66, W - 372, 186, title="Répartition")
    d.domain(lo, hi, 0.0, 1.0)
    d.grid_y([0.0, 0.25, 0.5, 0.75, 1.0], lambda v: f"{v:.0%}")
    d.grid_x([lo, p50, hi], lambda v: _num(v, 2), label="espérance par décision")
    d.path([(v, (i + 1) / n) for i, v in enumerate(finaux)], "s2")
    for v, part in ((p05, 0.05), (p50, 0.50), (p95, 0.95)):
        d.vline(v, "lvl")
        d.dot(v, part, "s1", f"{_num(v, 3)} R atteint dans {1 - part:.0%} des cas")
    d.label(p95, 0.95, "P95", dx=7, dy=-4, cls="tk halo")

    _source(b, "La bande claire de l'histogramme couvre 90 pour cent des tirages. "
               "La répartition donne la probabilité qu'une espérance soit "
               "atteinte sans compétence.")
    return b.render(
        "Distribution et fonction de répartition de l espérance mesurée sous "
        "absence de compétence")


FIGURES["disccloud"] = fig_cloud
FIGURES["discdist"] = fig_distribution
