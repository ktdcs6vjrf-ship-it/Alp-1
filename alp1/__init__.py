"""ALP-1 — noyau quantitatif de la stratégie futures multi-couches.

Modules
-------
costs    : modèle de friction, hit rate d'équilibre, déflation du Sharpe
barriers : premier passage brownien sans limite de durée
horizon  : premier passage sous contrainte de séance et loi d'échelle
stops    : gestion dynamique du stop, coût exact de la remontée
regime   : classification de régime par gamma dealer
signals  : formalisation des 7 couches en prédicats testables
report   : tables chiffrées du paper
figures  : figures SVG du paper
paper    : construction du document à partir du gabarit
"""

__version__ = "0.3.0"

__all__ = [
    "costs", "barriers", "horizon", "stops", "regime", "signals",
    "report", "figures", "figcss", "paper",
]
