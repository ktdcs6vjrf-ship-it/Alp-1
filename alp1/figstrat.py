"""Figures de la stratégie scellée.

    gateprice  — ce qu'une couche de confluence coûte au seuil de sélection
    battery    — la batterie contrôle par contrôle, sur série sans dérive
"""

from __future__ import annotations

import math

from .costs import deflated_threshold_sharpe
from .figures import Canvas, _esc, _legend, _num
from .report9 import SEALED_SR, SEALED_TRADES, _verdict


def fig_gate_price() -> str:
    """Seuil de sélection selon le nombre de couches de confluence ouvertes.

    La question tranchée : ajouter un filtre améliore-t-il une stratégie ? La
    courbe monte, le Sharpe disponible ne bouge pas, et leur croisement dit
    combien de couches la dérive documentée peut financer.
    """
    c = Canvas(640, 262, left=62, right=128, top=22, bottom=46)
    ks = [i * 0.1 for i in range(61)]

    def seuil(k: float) -> float:
        return deflated_threshold_sharpe(2.0 ** k, SEALED_TRADES)

    c.domain(0.0, 6.0, 0.0, max(SEALED_SR, seuil(6.0)) * 1.28)
    c.grid_y([0.0, 0.01, 0.02, 0.03], fmt=lambda v: _num(v, 2),
             label="Sharpe par trade")
    c.ticks_x([0, 1, 2, 3, 4, 5, 6], fmt=lambda v: _num(v, 0),
              label="couches de confluence ouvertes")

    # ce que la dérive documentée offre
    y = c.sy(SEALED_SR)
    c.add(f'<line class="hl" x1="{c.left:.1f}" y1="{y:.1f}" '
          f'x2="{c.left + c.pw:.1f}" y2="{y:.1f}"/>')
    c.add(f'<text class="dl halo" x="{c.left + 8:.1f}" y="{y - 8:.1f}">'
          f'Sharpe offert par la dérive documentée</text>')

    # ce que la sélection prélève
    c.path([(k, seuil(k)) for k in ks], "s2")
    for k in (1, 5):
        s = seuil(k)
        c.dot(k, s, "s2",
              f"{k} couche(s) · seuil {s:.4f} · "
              f"{s / SEALED_SR * 100:.0f} % du Sharpe consommé")
        c.add(f'<text class="dl halo" x="{c.sx(k) + 9:.1f}" '
              f'y="{c.sy(s) + 4:.1f}">{_esc(_num(s / SEALED_SR * 100, 0))} %</text>')

    c.add(f'<text class="lg" x="{c.left + c.pw + 10:.1f}" y="{c.top + 22:.1f}">'
          f'ce que la</text>')
    c.add(f'<text class="lg" x="{c.left + c.pw + 10:.1f}" y="{c.top + 36:.1f}">'
          f'sélection prélève</text>')
    c.add(f'<text class="lg" x="{c.left + c.pw + 10:.1f}" y="{c.top + 62:.1f}">'
          f'zéro porte :</text>')
    c.add(f'<text class="lg" x="{c.left + c.pw + 10:.1f}" y="{c.top + 76:.1f}">'
          f'aucune taxe</text>')
    return c.render(
        "Seuil de sélection déflaté selon le nombre de couches de confluence "
        "ouvertes, comparé au Sharpe qu'offre la dérive documentée")


def fig_battery() -> str:
    """La batterie contrôle par contrôle sur une série sans structure."""
    v = _verdict()
    c = Canvas(640, 40 + 30 * len(v.checks), left=232, right=54,
               top=26, bottom=34)
    c.domain(0.0, 1.0, 0.0, float(len(v.checks)))

    h = c.ph / len(v.checks)
    for i, chk in enumerate(v.checks):
        y = c.top + i * h + h * 0.5
        # Les classes de série portent déjà leur remplissage ; aucune couleur
        # n'est écrite en dur, ce qui garde la figure correcte dans les deux
        # thèmes du document.
        cls = "s3" if chk.passed else "s2"
        c.add(f'<text class="lg" x="{c.left - 12:.1f}" y="{y + 3.5:.1f}" '
              f'text-anchor="end">{_esc(chk.label)}</text>')
        c.add(f'<circle class="pt {cls}" cx="{c.left + 12:.1f}" '
              f'cy="{y:.1f}" r="6">'
              f'<title>{_esc(chk.reading)}</title></circle>')
        c.add(f'<text class="dl" x="{c.left + 28:.1f}" y="{y + 3.5:.1f}">'
              f'{_esc("franchi" if chk.passed else "manqué")}</text>')

    c.add(f'<text class="hdr" x="{c.left - 12:.1f}" y="{c.top - 10:.1f}" '
          f'text-anchor="end">série sans dérive</text>')
    c.add(f'<text class="lg" x="{c.left + 12:.1f}" '
          f'y="{c.top + c.ph + 22:.1f}">'
          f'{_esc(str(len(v.failed)))} contrôles manqués sur '
          f'{_esc(str(len(v.checks)))}  — la seule réponse juste</text>')
    return c.render(
        "Verdict de la batterie, contrôle par contrôle, sur une série dont la "
        "vérité est l'absence d'avantage")


FIGURES = {"gateprice": fig_gate_price, "battery": fig_battery}


def render_all() -> dict[str, str]:
    return {k: fn() for k, fn in FIGURES.items()}
