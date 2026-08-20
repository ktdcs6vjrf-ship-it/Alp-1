"""ALP-1 — noyau quantitatif de la stratégie futures multi-couches.

Modules
-------
costs    : modèle de friction, hit rate d'équilibre, drift requis
barriers : first-passage brownien (survie du stop, P(TP avant SL))
regime   : classification de régime par gamma dealer (GRC)
signals  : formalisation des 7 couches en filtres booléens/scores
report   : génération des tables chiffrées du paper
"""

__version__ = "0.1.0"

__all__ = ["costs", "barriers", "regime", "signals", "report"]
