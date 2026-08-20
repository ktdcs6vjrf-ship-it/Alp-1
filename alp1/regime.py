"""GRC — Gamma-Regime Conditioning.

Variable de conditionnement d'ALP-1. Le constat de départ est une
contradiction interne de la pile : deux moteurs incompatibles y tournent en
permanence.

  - Théorie de Dow  -> moteur de *continuation* (le prix persiste)
  - VWAP ±k·SD      -> moteur de *réversion*  (le prix revient)

Utilisés en parallèle sans arbitre, ils s'annulent : chaque signal de l'un est
un contre-signal de l'autre. Le gamma dealer net fournit cet arbitre, et il
n'est pas ad hoc — c'est un flux de couverture mécanique et documenté :

  Γ > 0 (dealers longs gamma)  : ils couvrent à contre-tendance (vendent la
      hausse, achètent la baisse). La volatilité réalisée est comprimée, le
      prix est épinglé autour des gros strikes. -> régime de RÉVERSION.

  Γ < 0 (dealers courts gamma) : ils couvrent dans le sens du mouvement
      (achètent la hausse, vendent la baisse). La volatilité est amplifiée,
      les mouvements s'auto-entretiennent. -> régime de MOMENTUM.

Statut de l'hypothèse. Le signe du gamma prédit une propriété de la variance
et de l'autocorrélation des rendements, non une direction : ce module fournit
une variable de *conditionnement*, jamais un signal directionnel. Sa valeur se
mesure comme un différentiel de lift, et son mécanisme se teste directement par
l'exposant d'échelle des rendements — voir `alp1.horizon`.

Une observation de terrain va dans le sens du mécanisme : les extrêmes de bande
à trois écarts-types donnent lieu à des balayages suivis de clôtures au-delà,
comportement attendu en gamma négatif. Sa force probante reste faible — un
phénomène unique, et une explication concurrente sans contenu gamma, la simple
accumulation d'ordres stop à ces niveaux.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Regime(str, Enum):
    """Régime de marché déduit du gamma dealer net."""

    REVERSION = "reversion"      # Γ > 0 : fader les extrêmes
    MOMENTUM = "momentum"        # Γ < 0 : suivre la cassure
    TRANSITION = "transition"    # |Γ| ≈ 0 : zone d'expansion de vol, no-trade


@dataclass(frozen=True)
class GammaState:
    """État gamma du sous-jacent à un instant donné.

    Parameters
    ----------
    net_gamma:
        Gamma dealer net au spot, en $ par point de variation (convention
        usuelle : $ notionnel à hedger pour 1 % de mouvement).
    spot:
        Niveau spot courant.
    flip_level:
        « Zero gamma level » — strike où le gamma dealer net change de signe.
    call_wall / put_wall:
        Strikes de concentration gamma maximale au-dessus / en dessous du spot.
        Ce sont les aimants et les niveaux de TP naturels.
    """

    net_gamma: float
    spot: float
    flip_level: float | None = None
    call_wall: float | None = None
    put_wall: float | None = None

    def distance_to_flip_pct(self) -> float | None:
        """Distance au flip level, en % du spot. Proxy de fragilité du régime."""
        if self.flip_level is None or self.spot <= 0:
            return None
        return 100.0 * (self.spot - self.flip_level) / self.spot


def classify(
    state: GammaState,
    neutral_band_pct: float = 0.15,
) -> Regime:
    """Classe le régime courant.

    `neutral_band_pct` : demi-largeur, en % du spot, de la zone autour du flip
    level traitée comme transition. C'est là que la volatilité s'étend et que
    les deux playbooks échouent simultanément — donc no-trade par défaut.
    """
    dist = state.distance_to_flip_pct()
    if dist is not None and abs(dist) <= neutral_band_pct:
        return Regime.TRANSITION
    if state.net_gamma > 0:
        return Regime.REVERSION
    if state.net_gamma < 0:
        return Regime.MOMENTUM
    return Regime.TRANSITION


@dataclass(frozen=True)
class Playbook:
    """Ensemble des couches actives sous un régime donné."""

    regime: Regime
    allow_vwap_fade: bool
    allow_dow_continuation: bool
    allow_lvn_reversion: bool
    allow_breakout: bool
    target_anchor: str
    rationale: str


PLAYBOOKS: dict[Regime, Playbook] = {
    Regime.REVERSION: Playbook(
        regime=Regime.REVERSION,
        allow_vwap_fade=True,
        allow_dow_continuation=False,
        allow_lvn_reversion=True,
        allow_breakout=False,
        target_anchor="POC / VWAP",
        rationale=(
            "Gamma dealer positif : la couverture est contra-tendancielle et "
            "comprime la volatilité réalisée. Les bandes VWAP tiennent, le prix "
            "est rappelé vers le POC. Les cassures sont majoritairement fausses."
        ),
    ),
    Regime.MOMENTUM: Playbook(
        regime=Regime.MOMENTUM,
        allow_vwap_fade=False,
        allow_dow_continuation=True,
        allow_lvn_reversion=False,
        allow_breakout=True,
        target_anchor="Call/Put wall opposé",
        rationale=(
            "Gamma dealer négatif : la couverture amplifie le mouvement. Fader "
            "une bande SD revient à se placer contre un flux de hedging forcé — "
            "c'est le mécanisme du 'swipe and close' observé en SD3. Les LVN "
            "sont traversées, pas respectées."
        ),
    ),
    Regime.TRANSITION: Playbook(
        regime=Regime.TRANSITION,
        allow_vwap_fade=False,
        allow_dow_continuation=False,
        allow_lvn_reversion=False,
        allow_breakout=False,
        target_anchor="—",
        rationale=(
            "Spot au voisinage du flip level : le signe du gamma est instable, "
            "la volatilité réalisée s'étend et les deux playbooks échouent "
            "ensemble. Absence de position = position."
        ),
    ),
}


def playbook_for(state: GammaState, neutral_band_pct: float = 0.15) -> Playbook:
    """Retourne le playbook actif pour l'état gamma courant."""
    return PLAYBOOKS[classify(state, neutral_band_pct)]
