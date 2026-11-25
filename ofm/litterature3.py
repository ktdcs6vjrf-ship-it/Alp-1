"""Les sources du cahier nº 3, et ce que disent les études qu'il ne pouvait pas rejouer.

Les chiffres de `AILLEURS` ont été recherchés le 23 novembre 2026 ; quand un
chiffre n'a été retrouvé que dans un résumé secondaire, la note le dit, et
quand il n'a pas été retrouvé du tout, il n'est pas repris (Madrian et Shea :
le constat seul). Les nombres de `AILLEURS` sont **cités**, pas calculés : ils
appartiennent aux études, et la page le dit à côté de chacun.
"""

from __future__ import annotations

import html as H

REFS = {
    # --- Les jeux de données --------------------------------------------------
    "fader2005": {"auteurs": "Fader, P. S., Hardie, B. G. S. et Lee, K. L.", "court": "Fader et al.", "annee": "2005",
                  "titre": "RFM and CLV: using iso-value curves for customer base analysis",
                  "revue": "Journal of Marketing Research 42(4), 415–430 ; jeu CDNOW, copie du paquet Lifetimes"},
    "chen2019": {"auteurs": "Chen, D.", "court": "Chen", "annee": "2019",
                 "titre": "Online Retail II", "revue": "UCI Machine Learning Repository (copie GitHub, Git LFS)"},
    "x52019": {"auteurs": "X5 Retail Group", "court": "X5 RetailHero", "annee": "2019",
               "titre": "RetailHero : achats des clients", "revue": "concours ODS (copie de scikit-uplift)"},
    "thornton2008": {"auteurs": "Thornton, R. L.", "court": "Thornton", "annee": "2008",
                     "titre": "The demand for, and impact of, learning HIV status",
                     "revue": "American Economic Review 98(5), 1829–1863"},
    "rondeau2008": {"auteurs": "Rondeau, D. et List, J. A.", "court": "Rondeau et List", "annee": "2008",
                    "titre": "Matching and challenge gifts to charity: evidence from laboratory and natural field experiments",
                    "revue": "Experimental Economics 11(3), 253–267"},
    "cai2015": {"auteurs": "Cai, J., de Janvry, A. et Sadoulet, E.", "court": "Cai et al.", "annee": "2015",
                "titre": "Social networks and the decision to insure",
                "revue": "American Economic Journal: Applied Economics 7(2), 81–108"},
    "gueguen2002": {"auteurs": "Guéguen, N.", "court": "Guéguen", "annee": "2002",
                    "titre": "The effects of a joke on tipping when it is delivered at the same time as the bill",
                    "revue": "Journal of Applied Social Psychology 32(9), 1955–1963"},
    "lynn1993": {"auteurs": "Lynn, M. et Mynier, K.", "court": "Lynn et Mynier", "annee": "1993",
                 "titre": "Effect of server posture on restaurant tipping",
                 "revue": "Journal of Applied Social Psychology 23(8), 678–685"},
    "arelbundock": {"auteurs": "Arel-Bundock, V.", "court": "Rdatasets", "annee": "2026",
                    "titre": "Rdatasets : une collection de jeux de données publiés avec R",
                    "revue": "dépôt GitHub, commit 1dcc2bf (copie des cinq expériences)"},
    # --- Les méthodes ----------------------------------------------------------
    "zhang2015": {"auteurs": "Zhang, Y., Bradlow, E. T. et Small, D. S.", "court": "Zhang et al.", "annee": "2015",
                  "titre": "Predicting customer value using clumpiness: from RFM to RFMC",
                  "revue": "Marketing Science 34(2), 195–208"},
    "grinold1989": {"auteurs": "Grinold, R. C.", "court": "Grinold", "annee": "1989",
                    "titre": "The fundamental law of active management",
                    "revue": "Journal of Portfolio Management 15(3), 30–37"},
    "phipson2010": {"auteurs": "Phipson, B. et Smyth, G. K.", "court": "Phipson et Smyth", "annee": "2010",
                    "titre": "Permutation p-values should never be zero",
                    "revue": "Statistical Applications in Genetics and Molecular Biology 9(1), article 39"},
    "bh1995": {"auteurs": "Benjamini, Y. et Hochberg, Y.", "court": "Benjamini et Hochberg", "annee": "1995",
               "titre": "Controlling the false discovery rate: a practical and powerful approach to multiple testing",
               "revue": "Journal of the Royal Statistical Society B 57(1), 289–300"},
    # --- Ailleurs ---------------------------------------------------------------
    "mclean2016": {"auteurs": "McLean, R. D. et Pontiff, J.", "court": "McLean et Pontiff", "annee": "2016",
                   "titre": "Does academic research destroy stock return predictability?",
                   "revue": "Journal of Finance 71(1), 5–32"},
    "hou2020": {"auteurs": "Hou, K., Xue, C. et Zhang, L.", "court": "Hou et al.", "annee": "2020",
                "titre": "Replicating anomalies", "revue": "Review of Financial Studies 33(5), 2019–2133"},
    "harvey2016": {"auteurs": "Harvey, C. R., Liu, Y. et Zhu, H.", "court": "Harvey et al.", "annee": "2016",
                   "titre": "… and the cross-section of expected returns",
                   "revue": "Review of Financial Studies 29(1), 5–68"},
    "johnson2003": {"auteurs": "Johnson, E. J. et Goldstein, D.", "court": "Johnson et Goldstein", "annee": "2003",
                    "titre": "Do defaults save lives?", "revue": "Science 302(5649), 1338–1339"},
    "madrian2001": {"auteurs": "Madrian, B. C. et Shea, D. F.", "court": "Madrian et Shea", "annee": "2001",
                    "titre": "The power of suggestion: inertia in 401(k) participation and savings behavior",
                    "revue": "Quarterly Journal of Economics 116(4), 1149–1187"},
    "gneezy2000": {"auteurs": "Gneezy, U. et Rustichini, A.", "court": "Gneezy et Rustichini", "annee": "2000",
                   "titre": "Pay enough or don't pay at all", "revue": "Quarterly Journal of Economics 115(3), 791–810"},
    "nunes2006": {"auteurs": "Nunes, J. C. et Drèze, X.", "court": "Nunes et Drèze", "annee": "2006",
                  "titre": "The endowed progress effect: how artificial advancement increases effort",
                  "revue": "Journal of Consumer Research 32(4), 504–512"},
    "ue2011": {"auteurs": "Parlement européen et Conseil", "court": "Directive 2011/83/UE", "annee": "2011",
               "titre": "Directive relative aux droits des consommateurs, article 22 (paiements supplémentaires)",
               "revue": "Journal officiel de l'Union européenne L 304, 64–88"},
}

#: Ce que d'autres ont établi et que ce cahier ne pouvait pas rejouer.
AILLEURS = (
    {"titre": "Un avantage publié s'use", "ref": "mclean2016",
     "constat": "Sur 97 signaux de rendement publiés en finance, le gain baisse de 26 % hors de l'échantillon de l'article et de 58 % après sa publication : une fois connu, un avantage se fait prendre par d'autres.",
     "preuve": "97 signaux, comparés avant et après leur publication.",
     "enfant": "Quand tout le monde connaît le coin à champignons, il n'en reste plus beaucoup."},
    {"titre": "La plupart des signaux ne tiennent pas", "ref": "hou2020",
     "constat": "Refaits avec soin, 65 % de 452 signaux publiés ne passent plus le seuil habituel, et 82 % ne passent pas un seuil corrigé pour le nombre de tests.",
     "preuve": "réplication de 452 signaux, chiffres de l'article publié.",
     "enfant": "Beaucoup de trucs qui avaient l'air de marcher ne marchent plus quand on vérifie bien."},
    {"titre": "Un seuil plus haut quand on cherche beaucoup", "ref": "harvey2016",
     "constat": "Après des centaines de signaux essayés par la recherche, un nouveau signal devrait franchir un t de 3 environ, pas 1,96 : sinon on retient le hasard.",
     "preuve": "revue de plusieurs centaines de facteurs publiés et correction pour tests multiples ; leur nombre exact n'est pas repris, faute de l'avoir retrouvé.",
     "enfant": "Si tu lances la pièce cent fois, tu finiras par avoir une série de « face » : ça ne prouve rien."},
    {"titre": "Un petit avantage, répété, compte", "ref": "grinold1989",
     "constat": "La valeur d'un signal croît comme sa justesse multipliée par la racine du nombre de décisions indépendantes qu'il guide : un signal faible sert s'il sert souvent.",
     "preuve": "résultat théorique, la « loi fondamentale de la gestion active ».",
     "enfant": "Gagner un tout petit peu à chaque partie finit par faire beaucoup, si l'on joue souvent."},
    {"titre": "La case cochée d'avance", "ref": "johnson2003",
     "constat": "Les pays où le don d'organes est présumé, sauf refus, ont des taux de consentement bien plus hauts que ceux où il faut s'inscrire ; dans leur expérience en ligne, 82 % consentent quand il faut se retirer, 42 % quand il faut s'inscrire.",
     "preuve": "comparaison entre pays et expérience en ligne ; les deux taux viennent d'un résumé secondaire de l'expérience.",
     "enfant": "Ce qui est déjà coché, on le garde souvent sans y penser."},
    {"titre": "L'inscription automatique", "ref": "madrian2001",
     "constat": "Dans une grande entreprise américaine, l'inscription automatique à l'épargne retraite a fait nettement monter la participation, et la plupart des salariés ont gardé le taux proposé par défaut.",
     "preuve": "avant et après un changement de règle ; les taux ne sont pas repris, faute de les avoir retrouvés.",
     "enfant": "Quand on est inscrit d'office, on reste inscrit."},
    {"titre": "Payer peu peut faire moins bien que rien", "ref": "gneezy2000",
     "constat": "Des étudiants payés une toute petite somme par bonne réponse ont fait moins bien que ceux qui n'étaient pas payés ; seuls des paiements assez gros ont fait mieux.",
     "preuve": "expérience en laboratoire, quatre niveaux de paiement tirés au sort.",
     "enfant": "Un cadeau trop petit peut vexer au lieu de faire plaisir."},
    {"titre": "Une carte déjà commencée", "ref": "nunes2006",
     "constat": "Une carte de fidélité de dix cases dont deux déjà tamponnées a été complétée presque deux fois plus souvent qu'une carte de huit cases vides, pour le même nombre d'achats à faire.",
     "preuve": "expérience de terrain, 300 cartes tirées au sort dans une station de lavage ; l'ordre de grandeur vient d'un résumé de l'étude.",
     "enfant": "Quand on a déjà un peu avancé, on a envie de finir."},
    {"titre": "Jamais pour un paiement", "ref": "ue2011",
     "constat": "Un paiement supplémentaire exige l'accord exprès du client : une case cochée d'avance ne vaut pas accord, et le client peut se faire rembourser.",
     "preuve": "règle de droit européen, article 22 de la directive.",
     "enfant": "On ne peut pas faire payer quelqu'un juste parce qu'il n'a pas décoché une case."},
)


def html_ref(r: dict) -> str:
    t = H.escape(r["titre"], quote=False)
    return (f'{H.escape(r["auteurs"], quote=False)} ({r["annee"]}). {t}. '
            f'<em>{H.escape(r["revue"], quote=False)}</em>.')
