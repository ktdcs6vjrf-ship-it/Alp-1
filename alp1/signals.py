"""Formalisation des 7 couches d'ALP-1 en filtres testables.

Chaque couche devient un prédicat explicite sur un état de marché observable.
L'objectif n'est pas de reproduire le jugement discrétionnaire de l'opérateur
mais de le rendre *falsifiable* : tant qu'une couche reste une appréciation
visuelle, elle ne peut être ni backtestée ni invalidée, et son apport à
l'espérance est indécidable.

Deux couches sont volontairement reformulées :

  - Fibonacci wick n'est pas traité comme un signal directionnel (la
    littérature ne documente pas d'edge autonome pour les niveaux de Fibonacci)
    mais comme un *optimiseur d'exécution* : une grille de placement d'ordres
    limites conditionnelle à un signal déjà validé. Il s'évalue alors sur le
    couple (taux de remplissage, R obtenu), pas sur un taux de réussite.

  - Bookmap devient le Liquidity Persistence Ratio (LPR), une mesure scalaire
    qui sépare l'absorption réelle du spoofing, au lieu d'une lecture visuelle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .regime import GammaState, Playbook, playbook_for


class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True)
class DailyBar:
    """Barre journalière, pour la couche Dow (D1)."""

    open: float
    high: float
    low: float
    close: float

    @property
    def body_high(self) -> float:
        return max(self.open, self.close)

    @property
    def body_low(self) -> float:
        return min(self.open, self.close)

    @property
    def upper_wick(self) -> float:
        return self.high - self.body_high

    @property
    def lower_wick(self) -> float:
        return self.low - self.body_low  # négatif ou nul

    @property
    def body_range(self) -> float:
        return self.body_high - self.body_low

    def wick_ratio(self) -> float:
        """Mèche haute rapportée au corps. Mesure la rejection par le haut."""
        if self.body_range <= 0:
            return 0.0
        return self.upper_wick / self.body_range


# --- Couche 1 : Théorie de Dow (D1) -----------------------------------------


def dow_continuation(today: DailyBar, yesterday: DailyBar) -> Direction | None:
    """Règle D1 : clôture au-delà du *corps* de la veille => continuation.

    Codifie la règle d'origine. À noter : ce filtre est un régime directionnel,
    pas un signal d'entrée — il ne dit rien du timing, seulement du biais.
    """
    if today.close > yesterday.body_high:
        return Direction.LONG
    if today.close < yesterday.body_low:
        return Direction.SHORT
    return None


def dow_rejection(today: DailyBar, wick_threshold: float = 1.0) -> Direction | None:
    """Clôture avec mèche dominante => chercher le setup *opposé*.

    `wick_threshold` = 1.0 signifie « mèche au moins aussi grande que le corps ».
    Dans la stack d'origine cette condition est couplée à la présence d'une zone
    historique majeure ; ici le seuil de mèche est le proxy quantifiable, la
    zone étant fournie séparément par la couche S/R.
    """
    if today.body_range <= 0:
        return None
    if today.upper_wick / today.body_range >= wick_threshold:
        return Direction.SHORT
    if abs(today.lower_wick) / today.body_range >= wick_threshold:
        return Direction.LONG
    return None


# --- Couche 2 : Volume Profile (LVN / HVN / POC) ----------------------------


@dataclass(frozen=True)
class VolumeProfile:
    """Profil de volume sur la structure d'accumulation retenue.

    `nodes` : dict {prix -> volume}. POC, HVN et LVN en sont dérivés, ce qui
    supprime la sélection visuelle des nœuds — principale source de
    surajustement de cette couche.
    """

    nodes: dict[float, float]

    @property
    def poc(self) -> float:
        return max(self.nodes.items(), key=lambda kv: kv[1])[0]

    def _threshold(self, quantile: float) -> float:
        vals = sorted(self.nodes.values())
        if not vals:
            return 0.0
        idx = min(len(vals) - 1, int(quantile * (len(vals) - 1)))
        return vals[idx]

    def lvn_levels(self, quantile: float = 0.25) -> list[float]:
        """Nœuds de bas volume : traversée rapide, mauvaise acceptation."""
        thr = self._threshold(quantile)
        return sorted(p for p, v in self.nodes.items() if v <= thr)

    def hvn_levels(self, quantile: float = 0.75) -> list[float]:
        """Nœuds de haut volume : acceptation, zones de support structurel."""
        thr = self._threshold(quantile)
        return sorted(p for p, v in self.nodes.items() if v >= thr)


def lvn_entry_valid(
    price: float,
    profile: VolumeProfile,
    direction: Direction,
    tolerance: float,
) -> bool:
    """Règle d'origine : acheter dans une LVN adossée à une HVN inférieure.

    Logique microstructurelle : la LVN offre une entrée peu disputée (peu de
    volume à absorber) tandis que la HVN adjacente fournit le socle d'inventaire
    qui doit contenir le prix. Symétrique pour la vente.
    """
    lvns = profile.lvn_levels()
    hvns = profile.hvn_levels()
    if not lvns or not hvns:
        return False

    near_lvn = any(abs(price - lvl) <= tolerance for lvl in lvns)
    if not near_lvn:
        return False

    if direction is Direction.LONG:
        return price < profile.poc and any(h < price for h in hvns)
    return price > profile.poc and any(h > price for h in hvns)


# --- Couche 3 : VWAP ± k·SD -------------------------------------------------


def vwap_band_signal(
    price: float,
    vwap: float,
    sd: float,
    bands: tuple[float, ...] = (1.5, 2.0, 2.5, 3.0),
    max_band: float = 2.5,
) -> tuple[Direction | None, float | None]:
    """Signal de réversion sur bande VWAP.

    Retourne (direction, bande atteinte). `max_band` plafonne les entrées : la
    bande 3.0 est exclue par défaut, conformément à l'observation d'origine —
    et le GRC en donne la raison mécanique (gamma négatif).
    """
    if sd <= 0:
        return None, None
    z = (price - vwap) / sd
    touched = [b for b in bands if abs(z) >= b]
    if not touched:
        return None, None
    band = max(touched)
    if band > max_band:
        return None, band
    return (Direction.SHORT if z > 0 else Direction.LONG), band


# --- Couche 4 : Bookmap -> Liquidity Persistence Ratio ----------------------


@dataclass(frozen=True)
class BookSnapshot:
    """Cliché du carnet à un niveau de prix donné."""

    level: float
    resting_size: float
    timestamp_s: float


def liquidity_persistence_ratio(
    pre_touch: BookSnapshot,
    at_touch: BookSnapshot,
) -> float:
    """LPR = taille restante au contact / taille affichée avant le contact.

    Rend mesurable l'intuition d'origine sur le spoofing :

      LPR ≳ 0.7  -> la liquidité tient au contact : absorption réelle, le
                    niveau a une chance de contenir le prix.
      LPR ≲ 0.3  -> la taille est retirée à l'approche : leurre, le niveau
                    cède probablement. Signal *inverse* de l'apparence.

    Limite d'infrastructure majeure : ce calcul exige un flux L2 horodaté et
    enregistrable. Un stream Bookmap gratuit sur YouTube ne permet ni la
    capture, ni l'horodatage, ni le rejeu — cette couche est donc, en l'état,
    non backtestable et donc non falsifiable.
    """
    if pre_touch.resting_size <= 0:
        return 0.0
    return at_touch.resting_size / pre_touch.resting_size


# --- Couche 5 : GEX 0DTE (via GRC) ------------------------------------------
# Voir alp1.regime — le gamma passe de simple repère de TP à variable d'état
# qui arbitre entre les moteurs de continuation et de réversion.


# --- Couche 6 : Fibonacci wick, traité comme optimiseur d'exécution ---------


OTE_LEVELS: tuple[float, ...] = (0.618, 0.705, 0.79)


def ote_zone(wick_low: float, wick_high: float, direction: Direction) -> tuple[float, float]:
    """Zone OTE (Optimal Trade Entry) tracée sur la mèche de confirmation.

    Pour un long, le retracement se mesure du haut vers le bas de la mèche.
    Retourne (borne basse, borne haute) de la zone de placement des limites.
    """
    rng = wick_high - wick_low
    if rng <= 0:
        raise ValueError("wick_high doit être > wick_low")
    lo_f, hi_f = min(OTE_LEVELS), max(OTE_LEVELS)
    if direction is Direction.LONG:
        return wick_high - hi_f * rng, wick_high - lo_f * rng
    return wick_low + lo_f * rng, wick_low + hi_f * rng


def ote_execution_edge(
    fill_rate: float,
    r_if_filled: float,
    r_market_entry: float,
) -> float:
    """Gain d'espérance de l'entrée OTE face à une entrée au marché.

        Δ = fill_rate · R_OTE − R_marché

    C'est la bonne façon d'évaluer la couche Fibonacci : elle améliore le prix
    d'entrée (donc R) au prix des signaux non remplis. Un Δ > 0 constitue un
    edge d'exécution réel et mesurable — indépendamment de toute propriété
    prédictive prêtée aux ratios de Fibonacci eux-mêmes.
    """
    return fill_rate * r_if_filled - r_market_entry


# --- Agrégation : la pile de confluence -------------------------------------


@dataclass
class Confluence:
    """Score de confluence et traçabilité des couches déclenchées."""

    direction: Direction
    layers: dict[str, bool] = field(default_factory=dict)

    @property
    def score(self) -> int:
        return sum(1 for v in self.layers.values() if v)

    @property
    def total(self) -> int:
        return len(self.layers)

    def passes(self, minimum: int) -> bool:
        return self.score >= minimum


def evaluate(
    direction: Direction,
    gamma: GammaState,
    dow: Direction | None,
    vwap_dir: Direction | None,
    lvn_ok: bool,
    lpr: float | None,
    lpr_threshold: float = 0.7,
) -> tuple[Confluence, Playbook]:
    """Évalue la pile complète sous le régime gamma courant.

    Le GRC agit en amont : une couche désactivée par le playbook ne peut pas
    contribuer au score, même si son signal brut est présent. C'est la
    différence essentielle avec la stack d'origine, où les couches votent
    toutes en permanence et où Dow et VWAP peuvent se contredire sans arbitre.
    """
    pb = playbook_for(gamma)

    layers = {
        "dow": pb.allow_dow_continuation and dow is direction,
        "vwap": pb.allow_vwap_fade and vwap_dir is direction,
        "lvn": pb.allow_lvn_reversion and lvn_ok,
        "book": lpr is not None and lpr >= lpr_threshold,
    }
    return Confluence(direction=direction, layers=layers), pb
