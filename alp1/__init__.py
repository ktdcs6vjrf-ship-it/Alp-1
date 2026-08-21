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

Les instruments de validation — ils opèrent sur la loi d'un trade, déduite
du cadre ci-dessus, et décident de ce qu'un historique permettrait de
conclure :

    pathstats : loi du trade, Sharpe, Sortino, Omega, Kelly, PSR, MinTRL
    drawdown  : profondeur, durée, coefficient de Lundberg, ruine
    mc        : Monte-Carlo, bootstrap par blocs, tests de permutation
    hmm       : Markov caché gaussien, Baum-Welch, Viterbi, et sa loi nulle
    overfit   : Sharpe déflaté, tests multiples, PBO, validation croisée purgée
    stress    : VaR et ES, valeurs extrêmes, sauts, scénarios, stress inversé

Le noyau ALP-2 — géométrie à barrière unique, et ce qu'il faut pour qu'un
chiffre soit défendable plutôt que seulement juste :

    momentum       : géométrie stop-seul, dimensionnement
    calib          : identités du modèle, boîte de plausibilité, points de rupture
    microstructure : saisonnalité, sauts, hétéroscédasticité, et ce qui y survit
    friction       : la friction comme loi déduite du carnet, marge et capacité
    prereg         : protocole scellé et son empreinte SHA-256
    grading        : grille de notation et son application aux deux documents

La mesure, qui attend un historique :

    dataset  : lecture et audit d'un CSV de barres d'une minute
    measure  : exécution du protocole pré-enregistré sur l'historique fourni

Et la production du document :

    report   : tables chiffrées du cadre
    quant    : calibration de référence et tables des instruments
    lexicon  : lexique des sigles et tables des couches
    figures  : figures du cadre
    figterm  : planches des couches, en panneaux de terminal
    figquant : planches des instruments, surfaces isométriques comprises
    figcss   : feuille de style partagée des figures
    paper    : construction du document à partir du gabarit
"""

__version__ = "0.6.0"

__all__ = [
    "costs", "barriers", "horizon", "stops", "momentum",
    "calib", "microstructure", "friction", "prereg", "grading",
    "dataset", "measure", "report2",
    "gex", "vprofile", "dow", "fib", "orderflow", "regime", "signals",
    "pathstats", "drawdown", "mc", "hmm", "overfit", "stress",
    "report", "quant", "lexicon", "figures", "figterm", "figquant",
    "figcss", "paper",
]
