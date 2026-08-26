"""Les figures du papier sur l'edge discrétionnaire.

Trois surfaces isométriques et quatre planches plates. Les surfaces portent
les résultats qui ne se lisent pas en deux dimensions — un seuil qui dépend
de deux paramètres à la fois, une puissance qui dépend de la taille de
l'effet *et* de l'échantillon. Les planches portent le reste.

Aucune couleur n'est écrite ici : les figures posent des classes, et
`figcss.py` décide. C'est ce qui leur permet de rester lisibles sur les deux
fonds du document, et c'est gardé par `tests/test_figures_all.py`.
"""

from __future__ import annotations

import math
from functools import lru_cache

from .costs import deflated_threshold_sharpe
from .entropy import trades_for_information
from .figquant import surface
from .figterm import Board, Panel, _esc, _num
from .journal import LEVERS, planted_bits, synthesise
from .operator import evaluate

#: Séances simulées pour les figures qui montrent un journal réel. Assez pour
#: que le signe de l'espérance mécanique soit stable, assez peu pour que la
#: planche se construise en quelques secondes.
SESSIONS = 400

#: Séances de bourse par an — la constante qui traduit un nombre de décisions
#: en années de carrière.
SESSIONS_PER_YEAR = 252

#: Le recensement de l'opérateur : quatre leviers, donc seize configurations.
K_LEVERS = len(LEVERS)


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _trades_for_threshold(sharpe: float, budget: float) -> float:
    """Décisions requises pour franchir le seuil déflaté à `budget` essais.

    Inversion fermée de `√(2·ln B / N) < SR`. C'est la route 2 du papier.
    """
    if sharpe <= 0.0:
        return math.inf
    return 2.0 * math.log(max(budget, 2.0)) / (sharpe ** 2)


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
# Figure 1 — la surface du mur (3D)
# ---------------------------------------------------------------------------


def fig_wall() -> str:
    """Décisions requises selon le nombre de leviers et le Sharpe revendiqué.

    La surface répond à la question que pose tout allocataire : combien de
    temps avant de savoir ? Elle montre du même coup pourquoi la taxe de
    multiplicité est supportable — l'axe des leviers est presque plat devant
    l'axe du Sharpe, parce que le seuil croît en `√(k·ln2)` alors que
    l'échantillon requis décroît en `1/SR²`.
    """
    ks = [0, 2, 4, 6]
    srs = [0.05, 0.075, 0.10, 0.15]
    # Hauteur : années à deux décisions par jour, plafonnée pour rester lisible.
    z = [[min(6.0, _trades_for_threshold(sr, 2.0 ** k)
              / (2 * SESSIONS_PER_YEAR)) for sr in srs] for k in ks]

    b = Board(660, 350)
    Panel(b, 40, 44, 580, 1,
          title="Le mur, en années de carrière",
          readout="deux décisions par jour, 252 séances par an")
    surface(b, 330, 250, z, 0.0, 6.0, cx=44.0, cy=20.0, cz=176.0,
            row_labels=[f"k = {k}" for k in ks],
            col_labels=[f"SR {_num(sr, 3)}" for sr in srs],
            row_axis="leviers discrétionnaires ouverts",
            col_axis="Sharpe revendiqué par décision",
            z_ticks=[(0.0, "0"), (1.0, "1 an"), (3.0, "3 ans"), (6.0, "6 ans")],
            tip="{v:.1f} an(s)")
    b.caption(330, 336,
              "La pente selon le Sharpe écrase celle selon les leviers : quatre "
              "leviers coûtent un facteur deux sur le seuil, jamais seize.")
    return b.render(
        "Surface du nombre d années requises selon les leviers ouverts et le "
        "Sharpe revendiqué par décision")


# ---------------------------------------------------------------------------
# Figure 2 — la surface de puissance (3D)
# ---------------------------------------------------------------------------


def fig_power() -> str:
    """Probabilité de détecter un avantage, par échantillon et par effet.

    Le relief a la forme d'une marche : sous une certaine combinaison, la
    détection est un tirage à pile ou face ; au-delà, elle est acquise. Le
    papier situe l'opérateur sur cette marche, et c'est tout ce qu'un
    protocole préenregistré a besoin de savoir.
    """
    ns = [250, 500, 1000, 2000]
    bits_grid = [0.005, 0.010, 0.020, 0.040]

    def power(n: int, bits: float) -> float:
        besoin = trades_for_information(bits)
        if besoin <= 0.0 or not math.isfinite(besoin):
            return 0.0
        # Puissance approchée : la non-centralité croît linéairement en N.
        lam = 1.96 * math.sqrt(max(n, 1) / besoin)
        return min(1.0, max(0.0, _norm_cdf(lam - 1.96)))

    z = [[power(n, bt) for bt in bits_grid] for n in ns]

    b = Board(660, 350)
    Panel(b, 40, 44, 580, 1,
          title="La puissance de détection",
          readout="test G informationnel, seuil 5 %")
    surface(b, 330, 250, z, 0.0, 1.0, cx=44.0, cy=20.0, cz=176.0,
            row_labels=[f"{n}" for n in ns],
            col_labels=[_num(bt, 3) for bt in bits_grid],
            row_axis="décisions enregistrées",
            col_axis="information par décision, en bits",
            z_ticks=[(0.0, "0 %"), (0.5, "50 %"), (0.80, "80 %"), (1.0, "100 %")],
            tip="puissance {v:.0%}",
            classify=lambda v: "up" if v >= 0.80 else ("ze" if v >= 0.5 else "dn"))
    b.caption(330, 336,
              "La teinte franche marque les combinaisons où la détection est "
              "acquise à 80 %. En deçà, l'absence de preuve ne prouve rien.")
    return b.render(
        "Surface de la puissance de détection selon le nombre de décisions "
        "et l information portée par chacune")


# ---------------------------------------------------------------------------
# Figure 3 — le plan d'espérance, sans puis avec clairvoyance (3D)
# ---------------------------------------------------------------------------


def fig_plane() -> str:
    """L'espérance selon la sélectivité et la mise, sans puis avec information.

    À gauche, l'opérateur sans clairvoyance : la surface est **plate**, et
    elle est plate en négatif. Ni la sélectivité ni le dimensionnement ne
    déforment quoi que ce soit, parce qu'aucun des deux ne porte
    d'information — c'est le théorème d'arrêt optionnel, transposé du choix
    des barrières au choix des trades.

    À droite, le même opérateur muni d'une clairvoyance : la surface
    s'incline, et elle s'incline selon **l'axe de la sélectivité**. C'est la
    figure qui dit où loge un avantage discrétionnaire, et où il ne loge pas.
    """
    selectivity = [1.00, 0.75, 0.50, 0.25]   # part des setups retenus
    sizing = [0.5, 1.0, 1.5, 2.0]            # mise, en unités de risque

    def build(skill: float) -> list[list[float]]:
        j = synthesise(skill=skill, n_sessions=SESSIONS)
        ranked = sorted(j.decisions, key=lambda d: (not d.taken, d.seq))
        rows = []
        for part in selectivity:
            n = max(1, int(round(part * j.n_eligible)))
            gardes = ranked[:n]
            m = sum(d.net_r or 0.0 for d in gardes) / n
            rows.append([m * size for size in sizing])
        return rows

    z_null, z_edge = build(0.0), build(0.55)
    lo = min(min(r) for r in z_null + z_edge)
    hi = max(max(r) for r in z_null + z_edge)
    span = max(abs(lo), abs(hi), 0.05)

    b = Board(680, 372)
    for idx, (title, sub, z) in enumerate((
            ("Sans clairvoyance", "aucune information sur l'issue", z_null),
            ("Avec clairvoyance", "0,15 bit par décision", z_edge))):
        ox = 176 + idx * 336
        Panel(b, ox - 148, 44, 296, 1, title=title, readout=sub)
        surface(b, ox, 250, z, -span, span, cx=30.0, cy=14.0, cz=150.0,
                row_labels=[f"{p:.0%}" for p in selectivity],
                col_labels=[f"{s:g} R" for s in sizing],
                z_ticks=[(0.0, "0")] if idx == 0 else None,
                tip="{v:+.3f} R")
    b.caption(340, 358,
              "axe gauche : part des setups retenus · axe droit : mise en unités "
              "de risque. Sans information, la surface est plate en négatif.")
    return b.render(
        "Deux surfaces d espérance par décision selon la sélectivité et la "
        "mise, sans puis avec clairvoyance")


# ---------------------------------------------------------------------------
# Figure 4 — les cinq lois nulles
# ---------------------------------------------------------------------------


def fig_nulls() -> str:
    """L'observé posé sur chacune de ses cinq lois nulles.

    Une barre par loi : l'étendue de la loi nulle, son quantile à 95 %, et le
    trait fort de l'observé. Un avantage n'est déclaré que si les cinq traits
    passent à droite de leur seuil ; la planche rend visible le fait qu'un
    opérateur peut battre trois lois et rester réfuté.
    """
    cas = (("sans clairvoyance", 0.0), ("clairvoyance franche", 0.55))
    b = Board(672, 392)

    for idx, (titre, skill) in enumerate(cas):
        j = synthesise(skill=skill, n_sessions=SESSIONS)
        v = evaluate(j, draws=300)
        y0 = 52 + idx * 190
        p = Panel(b, 150, y0, 460, 140, title=titre,
                  readout=f"{len(v.beaten)} loi(s) sur 5 battue(s)")
        vals = [t.observed for t in v.tests] + [t.q95 for t in v.tests]
        lo, hi = min(vals + [0.0]), max(vals + [0.0])
        marge = 0.16 * (hi - lo) + 1e-6
        p.domain(lo - marge, hi + marge, -0.6, len(v.tests) - 0.4)
        p.frame()
        p.grid_x([lo, (lo + hi) / 2, hi], lambda x: _num(x, 2),
                 label="statistique, en R par décision" if idx else None)
        p.vline(0.0, "zero")

        for k, t in enumerate(v.tests):
            row = len(v.tests) - 1 - k
            cls = "s1f" if t.beats else "negf"
            # L'étendue de la loi nulle, du centre à son quantile.
            p.hbar(row, t.null_mean, t.q95, 9.0, "wash",
                   f"{t.label} — loi nulle jusqu'à {t.q95:+.4f}")
            p.dot(t.q95, row, "s3", f"seuil 95 % : {t.q95:+.4f}", r=3.0)
            p.vbar(t.observed, row - 0.30, row + 0.30, 3.4, cls,
                   f"{t.label} — observé {t.observed:+.4f} · {t.reading}")
            b.add(f'<text class="tk" x="146" y="{p.sy(row) + 3.5:.1f}" '
                  f'text-anchor="end">{_esc(t.label)}</text>')

    b.legend(150, 378, [("wash", "étendue de la loi nulle"),
                        ("s1f", "observé, loi battue"),
                        ("negf", "observé, loi non battue")], step=192)
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
    b = Board(672, 300)

    for idx, (titre, skill, size_skill) in enumerate(cas):
        d = decompose(synthesise(skill=skill, size_skill=size_skill,
                                 n_sessions=SESSIONS))
        x0 = 44 + idx * 212
        p = Panel(b, x0, 58, 168, 150, title=titre,
                  readout=f"{d.carrier.key}")
        p.domain(0.0, max(0.35, max(s.value for s in d.shares) * 1.15),
                 -0.6, len(d.shares) - 0.4)
        p.frame()
        p.grid_x([0.0, 0.1, 0.2, 0.3], lambda x: _num(x, 1),
                 label="part de Shapley, en R" if idx == 1 else None)

        for k, s in enumerate(d.shares):
            row = len(d.shares) - 1 - k
            cls = "s1f" if s.key == d.carrier.key else "s3f"
            p.hbar(row, 0.0, max(s.value, 0.0), 13.0, cls,
                   f"{s.label} — {s.value:+.4f} R ({s.fraction:+.1%})")
            if idx == 0:
                b.add(f'<text class="tk" x="{x0 - 4:.1f}" '
                      f'y="{p.sy(row) + 3.5:.1f}" text-anchor="end">'
                      f'{_esc(s.key)}</text>')
            if s.value > 0.012:
                p.label(max(s.value, 0.0), row, f"{s.fraction:.0%}", dx=5)

    b.caption(336, 288,
              "La barre franche est le levier porteur. Il est chaque fois celui "
              "où la compétence a été plantée : la décomposition est réfutable, "
              "et elle passe.")
    return b.render(
        "Décomposition de Shapley de l avantage sur les quatre leviers, pour "
        "trois emplacements de la compétence plantée")


# ---------------------------------------------------------------------------
# Figure 6 — la taxe de multiplicité
# ---------------------------------------------------------------------------


def fig_tax() -> str:
    """Le seuil déflaté selon le nombre de leviers ouverts.

    La courbe est concave, et c'est tout l'argument : la taxe croît en
    `√(k·ln2)`, donc les premiers leviers coûtent cher et les suivants presque
    rien. Un opérateur qui en a déjà quatre n'a pas grand-chose à gagner à en
    fermer un ; il a beaucoup à gagner à passer de quatre à zéro.
    """
    ns = ((1000, "s1"), (3000, "s2"), (10000, "s3"))
    b = Board(660, 320)
    p = Panel(b, 74, 56, 500, 196, title="Le seuil déflaté à franchir",
              readout="Bailey et López de Prado")
    p.domain(0, 8, 0.0, 0.10)
    p.frame()
    p.grid_y([0.0, 0.025, 0.05, 0.075, 0.10], lambda v: _num(v, 3),
             label="Sharpe par décision requis")
    p.grid_x(list(range(9)), lambda v: f"{v:g}",
             label="leviers discrétionnaires ouverts")

    for n, cls in ns:
        pts = [(k, deflated_threshold_sharpe(max(2.0, 2.0 ** k), n))
               for k in range(9)]
        p.path(pts, cls)
        for k, val in pts:
            if k in (0, 4, 8):
                p.dot(k, val, cls,
                      f"{k} levier(s) · {n} décisions · seuil {val:.4f}", r=3.2)

    # Le point de l'opérateur recensé : quatre leviers.
    p.vline(K_LEVERS, "lvl strong")
    p.label(K_LEVERS, 0.093, f"{K_LEVERS} leviers recensés", dx=7)

    b.legend(74, 296, [(cls, f"{n} décisions") for n, cls in ns],
             step=150, kind="line")
    b.caption(330, 274,
              "La concavité est le résultat : passer de zéro à un levier coûte "
              "davantage que passer de quatre à huit.")
    return b.render(
        "Seuil de Sharpe déflaté selon le nombre de leviers discrétionnaires "
        "ouverts, pour trois tailles d échantillon")


# ---------------------------------------------------------------------------
# Figure 7 — la calibration de l'appareil
# ---------------------------------------------------------------------------


def fig_calibration() -> str:
    """Ce que l'appareil déclare, selon ce qu'on lui a planté.

    À gauche de la figure, l'opérateur sans compétence : aucune loi battue.
    À droite, la compétence franche : les cinq. Entre les deux, la zone où
    l'avantage existe mais n'est pas démontrable — et c'est le sujet du
    papier, pas un défaut de l'appareil.
    """
    data = _calibration()
    b = Board(660, 320)
    p = Panel(b, 74, 56, 500, 196, title="Calibration contre la vérité plantée",
              readout=f"{SESSIONS} séances, seuil 95 %")
    p.domain(0.0, max(d[1] for d in data) * 1.08, 0, 5.4)
    p.frame()
    p.grid_y([0, 1, 2, 3, 4, 5], lambda v: f"{v:g}",
             label="lois nulles battues sur cinq")
    p.grid_x([0.0, 0.05, 0.10, 0.15, 0.20], lambda v: _num(v, 2),
             label="information plantée, en bits par décision")

    p.path([(bits, n) for _, bits, n, _ in data], "s1")
    for skill, bits, n, sr in data:
        p.dot(bits, n, "s1",
              f"clairvoyance {skill:.2f} · {bits:.4f} bit · "
              f"{n}/5 lois battues · Sharpe {sr:+.4f}")

    # La frontière de déclaration : les cinq lois.
    p.hline(5.0, "lvl strong")
    p.tag(5.0, "avantage déclarable", side="right")

    # La zone d'indécision, entre première et dernière loi battue.
    battues = [bits for _, bits, n, _ in data if 0 < n < 5]
    if battues:
        p.band_x(min(battues), max(battues), "wash")
        p.label(min(battues), 1.4, "l'avantage existe mais ne se démontre pas",
                dx=6, cls="dl halo")

    b.caption(330, 288,
              "Le point à zéro bit est le contrôle qui autorise tous les autres : "
              "sans compétence, l'appareil ne déclare rien.")
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
