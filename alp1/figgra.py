"""Les planches de « la grandeur qu'on cite n'est pas celle qui décide ».

Douze planches, huit à plat et quatre en relief. Aucune ne montre un signal :
toutes montrent deux nombres qu'un seul mot désigne, et la distance entre eux.

Les fonctions d'échine, de graduation et de décade sont importées de `fignv`
plutôt que recopiées : elles ont été écrites pour la partie précédente, elles
portent chacune une leçon de rendu, et une troisième copie serait une
troisième occasion de les faire diverger.
"""

from __future__ import annotations

import math

from . import grandeurs as V
from . import niveaux as nv
from . import quant as q
from .figdisc import W, _plate, _source, _surface
from .fignv import _dec, _echine, _pct, _ticks
from .figterm import Board, Panel, _num, _signed


PW = (W - 74.0) / 2.0 - 30.0
PX1 = 74.0
PX2 = 74.0 + (W - 74.0) / 2.0


# ---------------------------------------------------------------------------
# I. Une cible a trois probabilités
# ---------------------------------------------------------------------------


def fig_gr_probas() -> str:
    """Les trois probabilités d'une seule cible.

    À gauche les trois courbes, qui se séparent dès que la cible s'éloigne du
    stop. À droite leur rapport, qui montre que l'écart n'est pas un accident
    de réglage.
    """
    a = q.STOP_PTS
    b = q.RR_REF * a
    b_ = _plate(494, "Grandeurs · trois probabilités pour une cible",
                "Le même mot pour trois nombres, et ils diffèrent d'un facteur "
                + _num(V.p_touche(b) / V.p_avant_stop(a, b), 0),
                "prix sans dérive")

    rrs = [1.5 * (1.06 ** i) for i in range(80)]
    rrs = [r for r in rrs if r <= 90.0]

    p1 = Panel(b_, PX1, 92, PW, 214, title="Les trois, contre l'ambition",
               readout="probabilité")
    p1.domain(1.5, 90.0, 0.003, 1.0, xlog=True, ylog=True)
    p1.frame()
    p1.grid_y([0.003, 0.01, 0.03, 0.1, 0.3, 1.0], lambda v: _num(v, 3),
              dx=40.0)
    p1.grid_x([2, 5, 10, 20, 40, 80], lambda v: _num(v, 0),
              label="rapport gain sur risque")
    p1.path([(r, V.p_touche(r * a)) for r in rrs], "hm5",
            tip="touchee a un moment")
    p1.path([(r, V.p_cloture(r * a)) for r in rrs], "hm3", dash="5 3",
            tip="cloture au-dela")
    p1.path([(r, V.p_avant_stop_ferme(a, r * a)) for r in rrs], "hm6",
            tip="touchee avant le stop")
    for cls, val in (("hm5", V.p_touche(b)), ("hm3", V.p_cloture(b)),
                     ("hm6", V.p_avant_stop_ferme(a, b))):
        p1.dot(q.RR_REF, val, cls, _pct(val, 2), r=4.2)

    p2 = Panel(b_, PX2, 92, PW, 214, title="Le rapport des deux premières",
               readout="facteur")
    p2.domain(1.5, 90.0, 1.0, 20.0, xlog=True)
    p2.frame()
    p2.grid_y(_ticks(1.0, 20.0, 5.0), lambda v: _num(v, 0), dx=28.0)
    p2.grid_x([2, 5, 10, 20, 40, 80], lambda v: _num(v, 0),
              label="rapport gain sur risque")
    p2.path([(r, V.p_touche(r * a) / V.p_avant_stop_ferme(a, r * a))
             for r in rrs], "hm6", tip="rapport des deux premieres")
    p2.dot(q.RR_REF, V.p_touche(b) / V.p_avant_stop_ferme(a, b), "hm7",
           "géométrie déclarée", r=4.4)
    p2.label(q.RR_REF, V.p_touche(b) / V.p_avant_stop_ferme(a, b),
             "géométrie déclarée", dx=-9, dy=-8, anchor="end")

    b_.legend(PX1, 352.0,
              [("hm6", "touchée avant le stop", ""),
               ("hm3", "clôture au-delà", "5 3"),
               ("hm5", "touchée à un moment", "")],
              step=190.0, kind="line")
    b_.annotation(0.0, 372.0,
                  "la première décide du trade, la deuxième est celle d'un "
                  "backtest naïf, la troisième celle que l'œil retient")
    b_.annotation(0.0, 388.0,
                  "à la géométrie déclarée elles valent " + _pct(
                      V.p_avant_stop_ferme(a, b), 2) + ", " + _pct(
                      V.p_cloture(b), 1) + " et " + _pct(V.p_touche(b), 1))
    b_.annotation(0.0, 404.0,
                  "et le rapport des deux extrêmes croît avec l'ambition de "
                  "la cible")

    _source(b_, "Les trois courbes sont exactes et portent le même nom dans "
                "la bouche de tout le monde. Celle du bas est le théorème "
                "d'arrêt optionnel, et c'est la seule qui décide d'un "
                "trade : elle ne fait intervenir aucune volatilité, "
                "seulement le rapport des deux distances. Celle du milieu "
                "est ce qu'un backtest rapporte lorsqu'il demande si le prix "
                "était au-delà de la cible à la clôture. Celle du haut est ce "
                "qu'un graphique donne à l'œil — le prix est passé là — et "
                "c'est le principe de réflexion, donc exactement le double de "
                "la précédente. Rien dans cette planche ne dépend d'une "
                "donnée de marché.")
    return b_.render("Trois probabilites d une meme cible contre le rapport "
                     "gain sur risque, et le rapport des deux extremes.")


def fig_gr_cout() -> str:
    """Ce que la confusion coûte, portée dans l'identité de Wald.

    Une seule droite, parce que l'espérance est linéaire en la probabilité.
    Ce qui compte est où tombent les trois points, et de quel côté du seuil.
    """
    a = q.STOP_PTS
    b = q.RR_REF * a
    p1v = V.p_avant_stop(a, b)
    p2v, p3v = V.p_cloture(b), V.p_touche(b)
    eq = (1.0 + V.FRICTION / a) / (1.0 + q.RR_REF)

    b_ = _plate(478, "Grandeurs · ce que la confusion coûte",
                "L'identité ne sait pas laquelle des trois on lui a passée",
                "écart : " + _num(V.esperance_r(p3v) - V.esperance_r(p1v), 1)
                + " R")

    ps = [0.002 + 0.004 * i for i in range(180)]
    ps = [p for p in ps if p <= 0.70]

    p1 = Panel(b_, PX1, 92, PW, 214, title="E[R] contre la probabilité employée",
               readout="en R")
    p1.domain(0.0, 0.70, -1.5, 13.0)
    p1.frame()
    p1.grid_y(_ticks(0.0, 12.0, 3.0), lambda v: _signed(v, 0), dx=28.0)
    p1.grid_x(_ticks(0.0, 0.70, 0.20), lambda v: _num(v, 2),
              label="probabilité portée dans l'identité")
    p1.hline(0.0, "lvl")
    p1.path([(p, V.esperance_r(p)) for p in ps], "hm6",
            tip="identite de Wald")
    p1.vline(eq, "lvl")
    for p, cls, nom in ((p1v, "hm7", "vraie"), (p3v, "hm5", "backtest"),
                        (p2v, "hm3", "l'œil")):
        p1.dot(p, V.esperance_r(p), cls, nom + " : "
               + _signed(V.esperance_r(p), 2) + " R", r=4.4)
    p1.label(eq, 12.0, "équilibre", dx=6, dy=0)

    p2 = Panel(b_, PX2, 92, PW, 214, title="Les trois espérances",
               readout="en R")
    lignes = (("touchée avant le stop", p1v, "hm7"),
              ("clôture au-delà", p2v, "hm3"),
              ("touchée à un moment", p3v, "hm5"))
    n = len(lignes)
    p2.domain(-1.5, 13.0, -0.6, n - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, 12.0, 3.0), lambda v: _signed(v, 0))
    p2.vline(0.0, "lvl")
    for i, (nom, p, cls) in enumerate(lignes):
        y = n - 1 - i
        e = V.esperance_r(p)
        p2.hbar(y, 0.0, e, 15.0, cls, tip=nom + " : " + _signed(e, 3) + " R")
        p2.label(e, y, _signed(e, 2), dx=8 if e >= 0 else -8, dy=4,
                 anchor="start" if e >= 0 else "end")
        p2.label(-1.5, y + 0.33, nom, dx=4, dy=0)

    b_.annotation(0.0, 352.0,
                  "l'espérance est linéaire en la probabilité : ce qui "
                  "compte est où tombent les trois points")
    b_.annotation(0.0, 368.0,
                  "le trait vertical est le taux d'équilibre, "
                  + _pct(eq, 2) + " : la vraie est dessous, les deux autres "
                  "au-dessus")
    b_.annotation(0.0, 384.0,
                  "c'est pourquoi la confusion ne se voit pas — elle fait "
                  "changer le verdict de signe")

    _source(b_, "L'identité de Wald prend la probabilité qu'on lui donne et "
                "ne vérifie pas laquelle. Avec la bonne, elle rend moins le "
                "rapport de friction, ce qui est le résultat structurant de "
                "tout ce document. Avec celle qu'un backtest naïf rapporte, "
                "elle rend cinq R ; avec celle que l'œil retient, plus de "
                "onze. L'écart ne vient d'aucune erreur de marché ni d'aucune "
                "erreur de calcul : il vient de la question qui a été posée. "
                "Et le trait vertical explique pourquoi l'erreur survit — le "
                "taux d'équilibre tombe entre la vraie valeur et les deux "
                "autres, si bien que la confusion ne déplace pas un chiffre, "
                "elle retourne un verdict.")
    return b_.render("Esperance en R contre la probabilite employee, et les "
                     "trois esperances qui en decoulent.")


def fig_gr_confusion() -> str:
    """Le relief du rapport des deux probabilités."""
    z = V.surface_confusion()
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Grandeurs · le relief de la confusion",
               "Où les deux probabilités s'écartent le plus",
               "hauteur : rapport des deux")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(a, 1) for a in V.SURF_STOP_PTS],
             col_labels=[_num(r, 0) for r in V.SURF_RR],
             z_ticks=[(t, _num(t, 0)) for t in _echine(zlo, zhi)],
             tip="facteur {v:.1f}", zero=zlo)

    b.annotation(0.0, 408.0,
                 "arête gauche : largeur du stop en points · arête droite : "
                 "rapport gain sur risque")
    b.annotation(0.0, 424.0,
                 "les deux axes éloignent la cible du stop sans l'éloigner de "
                 "la portée du prix, et c'est ce qui creuse l'écart")
    b.annotation(0.0, 440.0,
                 "la géométrie déclarée du document est au coin du fond, là "
                 "où la confusion coûte le plus")

    _source(b, "Le dénominateur est pris en forme fermée et non par "
               "simulation : au coin des cibles les plus lointaines, la "
               "probabilité bornée par la séance s'annule par soupassement, "
               "et le rapport mesuré y serait zéro sur zéro. La forme fermée "
               "est celle du problème non borné, elle ne s'annule jamais, et "
               "c'est elle qui porte la structure. Ce que le relief ajoute "
               "aux tables est que les deux axes agissent par le même "
               "mécanisme : un stop étroit et une cible ambitieuse écartent "
               "tous deux les deux barrières l'une de l'autre, sans pour "
               "autant mettre la cible hors de portée du prix sur une séance. "
               "L'écart est donc maximal exactement là où une géométrie "
               "ambitieuse se place.")
    return b.render("Surface du rapport des deux probabilites sur le plan de "
                    "la largeur du stop et du rapport gain sur risque.")


def fig_gr_relief_cout() -> str:
    """Le relief du coût, en R par décision."""
    z = V.surface_cout()
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Grandeurs · le relief du coût",
               "Ce que la confusion coûte, en R par décision",
               "hauteur : écart en R")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(a, 1) for a in V.SURF_STOP_PTS],
             col_labels=[_num(r, 0) for r in V.SURF_RR],
             z_ticks=[(t, _signed(t, 0)) for t in _echine(zlo, zhi)],
             tip="{v:+.2f} R par décision", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : largeur du stop en points · arête droite : "
                 "rapport gain sur risque")
    b.annotation(0.0, 424.0,
                 "l'écart ne dépend pas de la friction : il coûte la même "
                 "chose à qui paie cher et à qui ne paie rien")
    b.annotation(0.0, 440.0,
                 "le sol est posé à zéro, et presque tout le relief est "
                 "au-dessus")

    _source(b, "L'espérance étant linéaire en la probabilité, l'écart vaut "
               "simplement la différence des deux probabilités multipliée par "
               "ce que chaque décision paie, soit un plus le rapport gain sur "
               "risque. Le produit est ce que le relief montre, et il a la "
               "forme qu'on attend d'un produit : plat là où l'un des deux "
               "facteurs est petit, et abrupt là où les deux sont grands. La "
               "conséquence pratique est que la confusion est la plus chère "
               "exactement pour les géométries qu'un opérateur discrétionnaire "
               "préfère — stop serré, objectif lointain.")
    return b.render("Surface de l ecart d esperance en R sur le plan de la "
                    "largeur du stop et du rapport gain sur risque.")


# ---------------------------------------------------------------------------
# II. Un delta en a trois aussi
# ---------------------------------------------------------------------------


def fig_gr_deltas() -> str:
    """Les trois deltas contre le comptant, et l'écart contre la volatilité."""
    b = _plate(478, "Grandeurs · trois deltas pour un mot",
               "Le delta n'est pas la probabilité de finir dans la monnaie",
               "échéance six mois")

    t = 0.5
    r = V.TAUX_TABLE
    spots = [60.0 + 1.0 * i for i in range(81)]

    p1 = Panel(b, PX1, 92, PW, 214, title="Les trois, contre le comptant",
               readout="valeur")
    p1.domain(60.0, 140.0, 0.0, 1.0)
    p1.frame()
    p1.grid_y(_ticks(0.0, 1.0, 0.25), lambda v: _num(v, 2), dx=32.0)
    p1.grid_x([70, 90, 110, 130], lambda v: _num(v, 0), label="comptant")
    p1.vline(V.S_REF, "lvl")
    p1.path([(s, V.delta_comptant(s, V.S_REF, V.VOL_REF, t, r))
             for s in spots], "hm6", tip="delta comptant")
    p1.path([(s, V.proba_terminale(s, V.S_REF, V.VOL_REF, t, r))
             for s in spots], "hm3", dash="5 3", tip="N(d2)")
    p1.path([(s, V.dual_delta(s, V.S_REF, V.VOL_REF, t, r))
             for s in spots], "hm5", dash="2 3", tip="dual delta")

    p2 = Panel(b, PX2, 92, PW, 214, title="L'écart à la monnaie",
               readout="points de delta")
    vols = [0.05 + 0.01 * i for i in range(90)]
    p2.domain(0.05, 0.95, 0.0, 26.0)
    p2.frame()
    p2.grid_y(_ticks(0.0, 25.0, 5.0), lambda v: _num(v, 0), dx=28.0)
    p2.grid_x([0.1, 0.3, 0.5, 0.7, 0.9], lambda v: _pct(v, 0),
              label="volatilité annuelle")
    for mois, cls, dash in ((1.0, "hm3", "5 3"), (6.0, "hm6", "")):
        p2.path([(v, 100 * V.ecart_delta_proba(V.S_REF, V.S_REF, v,
                                               mois / 12.0, r))
                 for v in vols], cls, dash=dash,
                tip=_num(mois, 0) + " mois")
    gros = 100 * V.ecart_delta_proba(V.S_REF, V.S_REF, 0.80, t, r)
    p2.dot(0.80, gros, "hm7", "80 % et six mois : " + _num(gros, 1)
           + " points", r=4.4)
    p2.label(0.80, gros, _num(gros, 1), dx=-8, dy=-8, anchor="end")

    b.legend(PX1, 352.0,
             [("hm6", "delta comptant", ""), ("hm3", "N(d₂)", "5 3"),
              ("hm5", "dual delta", "2 3")], step=190.0, kind="line")
    b.annotation(0.0, 372.0,
                 "à droite, un mois en tiretés et six mois en trait plein : "
                 "l'écart croît avec les deux")
    b.annotation(0.0, 388.0,
                 "le document extérieur annonçait plus de quinze points ; le "
                 "recalcul en donne " + _num(gros, 1))

    _source(b, "Le delta comptant est la vraie dérivée, et la seule des trois "
               "qui neutralise une position. N(d₂) est la probabilité "
               "risque-neutre de finir dans la monnaie. Le dual delta est la "
               "sensibilité au strike, et c'est de lui, dérivé une seconde "
               "fois, qu'on tire une densité ; à taux nul il coïncide avec le "
               "précédent, ce qui est la raison pour laquelle la planche est "
               "tracée à taux non nul. Le raccourci populaire confond les "
               "deux premiers. Ils sont proches à échéance courte et près de "
               "la monnaie, ce qui explique sa survie, et ils se séparent "
               "exactement là où l'on s'appuie le plus dessus.")
    return b.render("Les trois deltas contre le comptant, et l ecart entre "
                    "delta et probabilite terminale contre la volatilite.")


def fig_gr_gap() -> str:
    """Le relief de l'écart delta contre probabilité terminale."""
    z = V.surface_gap()
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Grandeurs · le relief de l'écart",
               "Delta moins probabilité terminale, à la monnaie",
               "hauteur : points de delta")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_pct(v, 0) for v in V.SURF_VOL],
             col_labels=[_num(m, 2) if m < 1 else _num(m, 0)
                         for m in V.SURF_MOIS],
             z_ticks=[(t, _num(t, 0)) for t in _echine(zlo, zhi)],
             tip="{v:.1f} points de delta", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : volatilité annuelle · arête droite : "
                 "échéance en mois")
    b.annotation(0.0, 424.0,
                 "les deux axes n'entrent que par le produit sigma racine de "
                 "T, comme la bande de gamma de la partie précédente")
    b.annotation(0.0, 440.0,
                 "au coin du fond l'écart vaut " + _num(zhi, 0) + " points, "
                 "c'est-à-dire la moitié d'un delta")

    _source(b, "L'écart vaut N(d₁) moins N(d₁ moins sigma racine de T), donc "
               "il ne dépend que de ce seul produit — le même que celui qui "
               "gouverne la largeur de la bande de gamma de la partie "
               "précédente, et le même que celui qui gouverne l'ajustement de "
               "prime de la section cinq. Trois écarts apparemment sans "
               "rapport, une seule quantité derrière. Le raccourci qui "
               "confond le delta avec une probabilité est donc sans "
               "conséquence sur une option courte et à la monnaie, et il "
               "devient une erreur de dimensionnement de premier ordre "
               "partout ailleurs.")
    return b.render("Surface de l ecart entre delta et probabilite terminale "
                    "sur le plan de la volatilite et de l echeance.")


# ---------------------------------------------------------------------------
# III. Ce qui bouge pendant qu'on ne fait rien
# ---------------------------------------------------------------------------


def fig_gr_charm() -> str:
    """Le bleed contre la monnaie, et son lieu.

    La planche répond à la phrase du document extérieur — « le charm domine
    dans les derniers jours » — en montrant où il domine, et où il ne domine
    pas du tout.
    """
    b = _plate(510, "Grandeurs · ce qui bouge pendant qu'on ne fait rien",
               "Le bleed ne domine pas au strike, il domine à côté",
               "volatilité " + _pct(V.VOL_REF, 0))

    ms = [0.86 + 0.001 * i for i in range(281)]

    p1 = Panel(b, PX1, 92, PW, 214, title="Bleed contre moneyness",
               readout="millièmes de delta par jour")
    p1.domain(0.86, 1.14, -140.0, 140.0)
    p1.frame()
    p1.grid_y(_ticks(-100.0, 100.0, 50.0), lambda v: _signed(v, 0), dx=34.0)
    p1.grid_x([0.90, 0.95, 1.00, 1.05, 1.10], lambda v: _num(v, 2),
              label="moneyness S sur K")
    p1.hline(0.0, "lvl")
    p1.vline(1.0, "lvl")
    for j, cls, dash in ((30.0, "hm3", "5 3"), (7.0, "hm5", "2 3"),
                         (1.0, "hm6", "")):
        t = j / nv.JOURS_AN
        p1.path([(m, 1000 * V.bleed_par_jour(V.S_REF * m, V.S_REF,
                                             V.VOL_REF, t)) for m in ms],
                cls, dash=dash, tip=_num(j, 0) + " jours")
    mp = V.moneyness_du_pic(V.VOL_REF, 1.0 / nv.JOURS_AN)
    p1.dot(mp, -1000 * V.bleed_du_pic(V.VOL_REF, 1.0 / nv.JOURS_AN), "hm7",
           "maximum à un jour : S/K = " + _num(mp, 4), r=4.4)

    p2 = Panel(b, PX2, 92, PW, 214, title="Amplitude au pic, et sa limite",
               readout="millièmes par jour")
    js = [0.5 * (1.12 ** i) for i in range(60)]
    js = [x for x in js if x <= 200.0]
    # Le plancher descend a un dixieme : la courbe a la monnaie vit sous un
    # millieme jusqu'a deux jours de l'echeance, et un domaine plancher a un
    # la coupait en deux sans que rien ne le signale.
    p2.domain(0.5, 200.0, 0.1, 300.0, xlog=True, ylog=True)
    p2.frame()
    p2.grid_y([0.1, 1, 10, 100], lambda v: _num(v, 1), dx=32.0)
    p2.grid_x([1, 3, 10, 30, 100], lambda v: _num(v, 0),
              label="jours à l'échéance")
    p2.path([(j, 1000 * V.bleed_du_pic(V.VOL_REF, j / nv.JOURS_AN))
             for j in js], "hm6", tip="amplitude au pic")
    p2.path([(j, 1000 * V.amplitude_asymptotique(j / nv.JOURS_AN))
             for j in js], "hm3", dash="5 3", tip="phi(1) sur 2T")
    p2.path([(j, 1000 * abs(V.bleed_par_jour(V.S_REF, V.S_REF, V.VOL_REF,
                                             j / nv.JOURS_AN)))
             for j in js], "hm5", dash="2 3", tip="a la monnaie")

    b.legend(PX1, 348.0,
             [("hm6", "cadre gauche : un jour", ""),
              ("hm3", "trente jours", "5 3"),
              ("hm5", "sept jours", "2 3")],
             step=180.0, kind="line")
    b.legend(PX1, 368.0,
             [("hm6", "cadre droit : au pic", ""),
              ("hm3", "sa forme limite φ(1)/2T", "5 3"),
              ("hm5", "à la monnaie", "2 3")],
             step=180.0, kind="line")
    b.annotation(0.0, 388.0,
                 "à la monnaie le bleed est " + _num(
                     V.bleed_du_pic(V.VOL_REF, 1.0 / nv.JOURS_AN)
                     / abs(V.bleed_par_jour(V.S_REF, V.S_REF, V.VOL_REF,
                                            1.0 / nv.JOURS_AN)), 0)
                 + " fois plus petit qu'à son pic, à un jour de l'échéance")
    b.annotation(0.0, 420.0,
                 "et le pic se referme sur le strike, de "
                 + _num(100 * (1.0 - V.moneyness_du_pic(
                     V.VOL_REF, 60.0 / nv.JOURS_AN)), 1) + " % à "
                 + _num(100 * (1.0 - mp), 1) + " % en deux mois")

    _source(b, "Le charm est la seule dérivée qui déplace une position sans "
               "qu'il se passe quoi que ce soit sur le marché, et c'est à ce "
               "titre qu'il appartient à ce document : il agit pendant qu'on "
               "ne fait rien, comme le temps de marché de la dixième partie. "
               "Le cadre de gauche montre pourquoi la formule courante — le "
               "bleed domine les derniers jours — est trop grossière : au "
               "strike il est quasi nul, parce que le delta d'une option à la "
               "monnaie reste à un demi quoi qu'il arrive. Le cadre de droite "
               "donne l'amplitude au pic et sa forme limite, qui ne dépend "
               "que de l'échéance ; leur accord est ce qui a montré que la "
               "volatilité pèse cent fois moins que l'échéance sur cette "
               "amplitude.")
    return b.render("Bleed du delta contre la moneyness pour trois echeances, "
                    "et amplitude au pic contre l echeance.")


def fig_gr_lieu() -> str:
    """Le relief du lieu du bleed."""
    z = V.surface_lieu()
    vals = [v for l in z for v in l]
    zlo, zhi = min(vals), max(vals)

    b = _plate(486, "Grandeurs · où le bleed agit",
               "La bande du bleed se referme sur le strike",
               "hauteur : distance au strike en %")

    _surface(b, 0.52 * W, 232.0, z, zlo, zhi, cx=42.0, cy=13.0, cz=158.0,
             row_labels=[_num(j, 0) for j in V.SURF_JOURS],
             col_labels=[_pct(v, 0) for v in V.SURF_VOL_CHARM],
             z_ticks=[(t, _pct(t / 100.0, 0)) for t in _echine(zlo, zhi)],
             tip="{v:.1f} % du strike", zero=0.0)

    b.annotation(0.0, 408.0,
                 "arête gauche : jours à l'échéance · arête droite : "
                 "volatilité annuelle")
    b.annotation(0.0, 424.0,
                 "le premier essai portait l'amplitude : l'échéance la "
                 "déplace d'un facteur 154, la volatilité d'un facteur 1,6")
    b.annotation(0.0, 440.0,
                 "ce qui dépend des deux, c'est le lieu, et il se referme "
                 "comme sigma racine de T")

    _source(b, "L'amplitude du bleed en son maximum se déplace d'un facteur "
               "cent cinquante avec l'échéance et d'un facteur un et demi "
               "seulement avec la volatilité, si bien qu'un relief des deux "
               "n'aurait montré qu'une rampe le long d'un seul axe. La forme "
               "fermée dit pourquoi : au pic, d₁ tend vers moins un quand "
               "sigma racine de T tend vers zéro, si bien que l'amplitude "
               "tend vers phi de un sur deux T, qui ne dépend que de "
               "l'échéance. C'est cette mesure qui a fait remplacer le relief "
               "d'amplitude par celui du lieu. Le lieu, lui, dépend bien des "
               "deux, et il porte le fait pratique : la bande où le temps "
               "seul déplace une position se referme sur le strike à mesure "
               "que l'échéance approche, si bien qu'une position hors de la "
               "monnaie y entre au lieu d'en sortir.")
    return b.render("Surface de la distance au strike du bleed maximal sur le "
                    "plan de l echeance et de la volatilite.")


# ---------------------------------------------------------------------------
# IV. Le résumé qui cache
# ---------------------------------------------------------------------------


def fig_gr_livre() -> str:
    """Deux livres de delta net identique, et un mouvement."""
    b = _plate(478, "Grandeurs · le résumé qui cache",
               "Deux livres de delta net nul, et des paris opposés",
               _num(V.JOURS_LIVRE, 0) + " jours, "
               + _pct(V.VOL_LIVRE, 0) + " de volatilité")

    ms = [-0.06 + 0.001 * i for i in range(121)]

    p1 = Panel(b, PX1, 92, PW, 214, title="P/L des deux livres",
               readout="% du notionnel")
    p1.domain(-0.06, 0.06, -2.2, 2.2)
    p1.frame()
    p1.grid_y(_ticks(-2.0, 2.0, 1.0), lambda v: _signed(v, 0), dx=28.0)
    p1.grid_x([-0.04, -0.02, 0.0, 0.02, 0.04], lambda v: _signed(100 * v, 0),
              label="mouvement du comptant, en %")
    p1.hline(0.0, "lvl")
    p1.vline(0.0, "lvl")
    p1.path([(m, 100 * V.pl_livre("long", m)) for m in ms], "hm6",
            tip="livre long de convexite")
    p1.path([(m, 100 * V.pl_livre("court", m)) for m in ms], "hm3",
            dash="5 3", tip="livre court de convexite")
    for m in (-0.02, 0.02):
        p1.dot(m, 100 * V.pl_livre("long", m), "hm7", "deux pour cent", r=4.0)
        p1.dot(m, 100 * V.pl_livre("court", m), "hm7", "deux pour cent", r=4.0)

    p2 = Panel(b, PX2, 92, PW, 214, title="L'écart entre les deux",
               readout="% du notionnel")
    n = len(V.MOUVEMENTS)
    p2.domain(0.0, 3.2, -0.6, n - 0.4)
    p2.frame()
    p2.grid_x(_ticks(0.0, 3.0, 1.0), lambda v: _num(v, 0))
    for i, m in enumerate(V.MOUVEMENTS):
        y = n - 1 - i
        e = 100 * (V.pl_livre("long", m) - V.pl_livre("court", m))
        p2.hbar(y, 0.0, e, 13.0, "hm5",
                tip=_pct(m, 1) + " : " + _num(e, 3) + " %")
        p2.label(e, y, _num(e, 2), dx=7, dy=4)
        p2.label(0.0, y + 0.34, "mouvement de " + _pct(m, 1), dx=4, dy=0)

    b.legend(PX1, 352.0,
             [("hm6", "livre long de convexité", ""),
              ("hm3", "livre court de convexité", "5 3")],
             step=250.0, kind="line")
    b.annotation(0.0, 372.0,
                 "les deux livres ont le même delta net, nul, et le gardent "
                 "tant que le prix ne bouge pas")
    b.annotation(0.0, 388.0,
                 "un résumé de risque qui ne publie que le delta net les "
                 "décrit de façon identique")

    _source(b, "L'additivité du delta est ce qui le rend commode et ce qui le "
               "rend dangereux comme statistique de synthèse. Les deux livres "
               "de cette planche sont construits à delta net nul et le "
               "restent tant que rien ne bouge ; ils sont pourtant des paris "
               "exactement opposés, et leur écart croît comme le carré du "
               "mouvement. C'est la même faute que celle des parties "
               "précédentes, sur un autre objet : publier un premier moment "
               "en croyant décrire une distribution. Le Calmar de la "
               "dix-huitième partie cachait sa bande d'échantillonnage ; le "
               "delta net cache sa courbure.")
    return b.render("P/L de deux livres de delta net nul contre le mouvement "
                    "du comptant, et l ecart entre les deux.")


# ---------------------------------------------------------------------------
# V. La convention, et l'identité
# ---------------------------------------------------------------------------


def fig_gr_convention() -> str:
    """Les trois conventions, et les deux mécanismes qui les écartent."""
    b = _plate(478, "Grandeurs · trois conventions pour un mot",
               "Deux mécanismes, et un seul est du bon ordre de grandeur",
               "à la monnaie")

    mois = [0.25 * (1.12 ** i) for i in range(60)]
    mois = [m for m in mois if m <= 26.0]

    p1 = Panel(b, PX1, 92, PW, 214, title="Les trois conventions",
               readout="valeur")
    p1.domain(0.25, 26.0, 0.35, 0.65, xlog=True)
    p1.frame()
    p1.grid_y(_ticks(0.35, 0.65, 0.05), lambda v: _num(v, 2), dx=32.0)
    p1.grid_x([0.5, 1, 3, 6, 12, 24], lambda v: _num(v, 2),
              label="échéance, en mois")
    for nom, cls, dash, fn in (
            ("comptant", "hm6", "", V.delta_comptant),
            ("forward", "hm3", "5 3", V.delta_forward),
            ("ajusté de la prime", "hm5", "2 3", V.delta_ajuste_prime)):
        p1.path([(m, fn(V.S_REF, V.S_REF, V.VOL_REF, m / 12.0, 0.02, 0.015))
                 for m in mois], cls, dash=dash, tip=nom)

    p2 = Panel(b, PX2, 92, PW, 214, title="Les deux mécanismes",
               readout="points de delta")
    p2.domain(0.25, 26.0, 0.0, 16.0, xlog=True)
    p2.frame()
    p2.grid_y(_ticks(0.0, 16.0, 4.0), lambda v: _num(v, 0), dx=28.0)
    p2.grid_x([0.5, 1, 3, 6, 12, 24], lambda v: _num(v, 2),
              label="échéance, en mois")
    p2.path([(m, V.ajustement_de_prime(V.VOL_REF, m)) for m in mois], "hm6",
            tip="ajustement de prime")
    p2.path([(m, 100 * abs(
        V.delta_comptant(V.S_REF, V.S_REF, V.VOL_REF, m / 12.0, 0.02, 0.015)
        - V.delta_forward(V.S_REF, V.S_REF, V.VOL_REF, m / 12.0, 0.02, 0.015)))
        for m in mois], "hm3", dash="5 3", tip="ecart comptant forward")

    b.legend(PX1, 352.0,
             [("hm6", "comptant · ajustement de prime", ""),
              ("hm3", "forward · écart de portage", "5 3"),
              ("hm5", "ajusté de la prime", "2 3")],
             step=200.0, kind="line")
    b.annotation(0.0, 372.0,
                 "l'écart entre comptant et forward ne vient que du "
                 "dividende, et reste sous deux points de delta")
    b.annotation(0.0, 388.0,
                 "l'ajustement de prime ne dépend ni du taux ni du dividende, "
                 "et atteint " + _num(V.ajustement_de_prime(V.VOL_REF, 24.0), 0)
                 + " points à deux ans")

    _source(b, "Les trois conventions sont correctes et répondent à trois "
               "questions différentes. Ce que le cadre de droite sépare, et "
               "qu'on ne sépare jamais, ce sont les deux mécanismes qui les "
               "écartent, parce qu'ils n'ont pas le même ordre de grandeur. "
               "L'écart entre comptant et forward ne vient que du dividende "
               "et s'annule avec lui. L'ajustement de prime, lui, ne dépend "
               "que de sigma racine de T. La première version de cette "
               "planche balayait le portage et rendait une courbe constante ; "
               "c'est la mesure qui a imposé la décomposition.")
    return b.render("Les trois conventions de delta contre l echeance, et les "
                    "deux mecanismes qui les ecartent.")


def fig_gr_identite() -> str:
    """L'identité, et la condition qui la porte.

    Deux quantités qui n'ont l'air de rien avoir en commun coïncident à la
    monnaie, exactement, et se séparent dès qu'on s'en écarte. La planche
    montre les deux moitiés de cette phrase.
    """
    b = _plate(478, "Grandeurs · une seule quantité, deux noms",
               "L'ajustement de prime est l'écart delta contre probabilité",
               "et seulement à la monnaie")

    p1 = Panel(b, PX1, 92, PW, 214, title="À la monnaie : elles coïncident",
               readout="points de delta")
    mois = [0.25 * (1.12 ** i) for i in range(60)]
    mois = [m for m in mois if m <= 26.0]
    p1.domain(0.25, 26.0, 0.0, 16.0, xlog=True)
    p1.frame()
    p1.grid_y(_ticks(0.0, 16.0, 4.0), lambda v: _num(v, 0), dx=28.0)
    p1.grid_x([0.5, 1, 3, 6, 12, 24], lambda v: _num(v, 2),
              label="échéance, en mois")
    p1.path([(m, V.identite_prime_gap(V.VOL_REF, m)[0]) for m in mois], "hm6",
            tip="ajustement de prime")
    p1.path([(m, V.identite_prime_gap(V.VOL_REF, m)[1]) for m in mois], "hm3",
            dash="6 4", tip="delta moins N(d2)")

    p2 = Panel(b, PX2, 92, PW, 214, title="Hors de la monnaie : elles divergent",
               readout="points de delta")
    ms = [0.80 + 0.005 * i for i in range(81)]
    t = 0.5
    p2.domain(0.80, 1.20, 0.0, 22.0)
    p2.frame()
    p2.grid_y(_ticks(1.0, 20.0, 5.0), lambda v: _num(v, 0), dx=28.0)
    p2.grid_x([0.85, 0.95, 1.05, 1.15], lambda v: _num(v, 2),
              label="moneyness S sur K")
    p2.vline(1.0, "lvl")
    p2.path([(m, 100 * nv.call(V.S_REF * m, V.S_REF, V.VOL_REF, t)
              / (V.S_REF * m)) for m in ms], "hm6", tip="prime sur comptant")
    p2.path([(m, 100 * V.ecart_delta_proba(V.S_REF * m, V.S_REF, V.VOL_REF,
                                           t)) for m in ms], "hm3",
            dash="6 4", tip="delta moins N(d2)")
    p2.dot(1.0, 100 * V.ecart_delta_proba(V.S_REF, V.S_REF, V.VOL_REF, t),
           "hm7", "le seul point où elles se touchent", r=4.4)

    b.legend(PX1, 352.0,
             [("hm6", "ajustement de prime, V sur S", ""),
              ("hm3", "delta moins N(d₂)", "6 4")], step=250.0, kind="line")
    b.annotation(0.0, 372.0,
                 "à la monnaie et à portage nul, la prime vaut S fois "
                 "N(d₁) moins N(d₂), donc les deux sont le même nombre")
    b.annotation(0.0, 388.0,
                 "l'identité tombe dès qu'on quitte la monnaie, et le point "
                 "marqué est le seul où elles se touchent")

    _source(b, "Deux confusions que rien ne rapproche — le raccourci qui "
               "prend le delta pour une probabilité, et la convention qui "
               "retranche la prime — reposent sur une seule quantité. La "
               "démonstration tient en une ligne : à la monnaie et à portage "
               "nul, le prix d'un call vaut S fois la différence des deux "
               "fonctions de répartition, donc la prime rapportée au comptant "
               "est exactement l'écart entre le delta et la probabilité "
               "terminale. Le cadre de droite porte la condition, parce "
               "qu'une identité sans sa condition est une erreur en "
               "attente : hors de la monnaie les deux quantités n'ont plus "
               "rien à voir, et la planche le montre plutôt que de le dire.")
    return b.render("Ajustement de prime et ecart delta contre probabilite "
                    "terminale, a la monnaie puis hors de la monnaie.")


# ---------------------------------------------------------------------------
# VI. Ce qui reste
# ---------------------------------------------------------------------------


def fig_gr_reste() -> str:
    """Le décompte : cinq fois un mot pour deux grandeurs.

    La première version de cette planche donnait à toutes les barres la même
    longueur, et ne portait donc qu'un bit par ligne — la couleur. C'était une
    table déguisée en figure. Les cinq lignes sont dans cinq unités qui ne se
    comparent pas ; ce qui se compare est l'**erreur relative**, sans
    dimension, et c'est elle que la barre porte maintenant.
    """
    lst = V.confusions()
    b = _plate(518, "Grandeurs · le décompte",
               "Cinq fois un mot pour deux grandeurs",
               _num(sum(1 for x in lst if x.opposable), 0) + " sur "
               + _num(len(lst), 0) + " opposables")

    p1 = Panel(b, 214.0, 92, W - 214.0 - 22.0, 232,
               title="De combien la grandeur citée s'écarte",
               readout="erreur relative")
    n = len(lst)
    hi = max(x.erreur_relative for x in lst)
    p1.domain(0.10, 40.0, -0.6, n - 0.4, xlog=True)
    p1.frame()
    p1.grid_x([0.1, 0.3, 1.0, 3.0, 10.0, 30.0],
              lambda v: _pct(v, 0), label="écart, en fraction de ce qui décide")
    p1.vline(1.0, "lvl")
    for i, x in enumerate(lst):
        y = n - 1 - i
        p1.hbar(y, 0.10, x.erreur_relative, 15.0, "hm3" if i == 0 else "hm6",
                tip=x.quoi + " : " + _pct(x.erreur_relative, 0) + " — "
                    + x.cout)
        p1.label(x.erreur_relative, y, _pct(x.erreur_relative, 0), dx=7, dy=4)
        p1.label(0.10, y, x.quoi, dx=-9, dy=4, anchor="end")
    _ = hi

    b.legend(214.0, 368.0,
             [("hm3", "du dépôt"), ("hm6", "du document extérieur")],
             step=250.0)
    b.annotation(0.0, 392.0,
                 "l'axe est sans dimension : de quelle fraction de la "
                 "grandeur qui décide la grandeur citée s'écarte")
    b.annotation(0.0, 408.0,
                 "le trait vertical est cent pour cent, c'est-à-dire une "
                 "erreur du même ordre que la grandeur elle-même")
    b.annotation(0.0, 424.0,
                 "la première ligne est du dépôt, n'a rien à voir avec les "
                 "options, et coûte plus que les quatre autres réunies")

    _source(b, "L'axe est sans dimension, et il fallait qu'il le soit : les "
               "cinq lignes sont en R, en points de delta, en millièmes par "
               "jour et en pour-cent de notionnel, et aucune ne se compare "
               "aux autres dans son unité. Ce qui se compare est la fraction "
               "de la grandeur décisive dont la grandeur citée s'écarte. "
               "Les cinq lignes ont la même forme et c'est le résultat de la "
               "partie. La première est du dépôt : elle concerne une cible et "
               "un stop, elle ne fait intervenir aucune option, et elle coûte "
               "plus que les quatre autres réunies. Les quatre suivantes sont "
               "celles du document extérieur, recalculées et parfois "
               "corrigées. Aucune ne demande une série de prix, et c'est ce "
               "qui les rend utiles : elles se vérifient avant la première "
               "décision, au moment où une erreur de dimensionnement ne coûte "
               "encore rien. La phrase du document extérieur vaut pour les "
               "cinq — la grandeur citée décrit le présent avec exactitude et "
               "ne prévoit rien.")
    return b.render("Rangement des cinq confusions, ce qu on cite contre ce "
                    "qui decide, avec l ecart mesure.")


FIGURES = {
    "grprobas": fig_gr_probas,
    "grcout": fig_gr_cout,
    "grconfusion": fig_gr_confusion,
    "grrelief": fig_gr_relief_cout,
    "grdeltas": fig_gr_deltas,
    "grgap": fig_gr_gap,
    "grcharm": fig_gr_charm,
    "grlieu": fig_gr_lieu,
    "grlivre": fig_gr_livre,
    "grconvention": fig_gr_convention,
    "gridentite": fig_gr_identite,
    "grreste": fig_gr_reste,
}


def render_all() -> dict[str, str]:
    return {k: f() for k, f in FIGURES.items()}
