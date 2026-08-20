"""ALP-1 — noyau quantitatif de la stratégie futures multi-couches.

Deux ensembles de modules.

Le cadre du trade — il ne dépend d'aucune couche d'analyse :

    costs    : modèle de friction, hit rate d'équilibre, déflation du Sharpe
    barriers : premier passage brownien sans limite de durée
    horizon  : premier passage sous contrainte de séance et loi d'échelle
    stops    : gestion dynamique du stop, coût exact de la remontée
    momentum : géométrie stop-seul, dimensionnement

Les sept couches — chacune reçoit une définition calculatoire, une loi nulle
en forme fermée quand elle existe, et un prédicat testable :

    gex       : exposition gamma, niveaux publiés, boucle de couverture
    vprofile  : profil de volume comme densité d'occupation
    dow       : théorie de Dow, structure de swings et leurs lois nulles
    fib       : ratios de Fibonacci, loi du retracement, zone OTE
    orderflow : liquidité multi-échelles, persistance, impact, CVD
    regime    : classification de régime par gamma dealer
    signals   : formalisation des couches en prédicats

Et la production du document :

    report   : tables chiffrées du cadre
    lexicon  : lexique des sigles et tables des couches
    figures  : figures du cadre
    figterm  : planches des couches, en panneaux de terminal
    figcss   : feuille de style partagée des figures
    paper    : construction du document à partir du gabarit
"""

__version__ = "0.4.0"

__all__ = [
    "costs", "barriers", "horizon", "stops", "momentum",
    "gex", "vprofile", "dow", "fib", "orderflow", "regime", "signals",
    "report", "lexicon", "figures", "figterm", "figcss", "paper",
]
