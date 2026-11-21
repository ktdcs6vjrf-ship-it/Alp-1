"""Le registre du cahier nº 2 — écrit avant le premier calcul de résultat.

Même règle que le registre du cahier nº 1 : chaque hypothèse est fixée **avant
d'avoir regardé les résultats**, avec son sens, sa mesure et son test, puis la
correction de Benjamini-Hochberg porte sur la famille entière. Le cahier nº 2 a
**sa propre famille** : ajouter ses tests à ceux du nº 1 changerait, après
coup, les valeurs q d'un registre déjà publié. Les deux registres restent donc
séparés, et chacun garde ses verdicts.

Le registre a été commité avant le premier calcul de résultat (l'historique du
dépôt le date). Les seules décisions prises avant ce calcul, en regardant la
forme des fichiers et jamais un résultat :

- **Trois jeux visés n'ont pas pu entrer.** Criteo Uplift (la copie publique a
  été retirée de son hébergeur), KKBox (Kaggle et Mendeley, injoignables d'ici)
  et l'archive des titres d'Upworthy (OSF, injoignable). Lenta et X5, deux
  expériences de SMS tirées au sort, prennent la place de Criteo pour la
  question du ciblage ; aucun jeu d'abonnement réel n'est joignable, si bien que
  le renouvellement d'abonnement reste **non testé** ici.
- **La visite sert aux comparaisons fines sur Hillstrom.** L'achat n'y touche
  que 0,9 % des clients : une différence d'effet entre deux moitiés y serait
  indétectable. Les effets principaux se lisent sur l'achat et la dépense ; les
  écarts d'effet et le ciblage, sur la visite.
- **Kickstarter** : l'échantillon est celui des campagnes terminées, réussies ou
  échouées ; les campagnes annulées, suspendues, en cours ou sans état sont
  écartées, comme celles dont la durée sort de 1 à 92 jours (le fichier porte
  des lancements datés de 1970). L'année est celle du lancement.
- **Online Retail II** : un achat est un jour d'achat (les factures d'un même
  jour s'additionnent, comme dans CDNOW), hors annulations et montants nuls ;
  la calibration couvre du 1ᵉʳ décembre 2009 au 30 novembre 2010, la
  validation les douze mois suivants. Comme dans CDNOW, la cohorte est celle
  des clients dont le premier achat observé tombe dans les treize premières
  semaines (jusqu'au 28 février 2010) : chacun a au moins 39 semaines pour
  montrer son rythme, et le rythme passé d'un client vu une seule semaine
  n'aurait pas de sens. Le silence de G02 et G03 est d'au moins 26 semaines.
- **Le ciblage (famille C)** suit une seule coupe tirée au sort par jeu : le
  modèle s'estime sur une moitié, le tiers choisi se lit sur l'autre. Les
  variables des modèles sont listées ci-dessous (`VARIABLES`), fixées avant le
  calcul ; une valeur manquante prend la médiane de la moitié d'estimation et
  une indicatrice d'absence.
- **X5** : un âge hors de 14 à 100 ans est une erreur de saisie (le fichier
  porte des âges négatifs) et devient une valeur manquante.

`sens` vaut +1 ou −1 quand une direction est annoncée, 0 pour une question
ouverte. Changer une définition après un résultat imposerait un nouvel
identifiant, et le registre garderait les deux.
"""

from __future__ import annotations

from .registre import Hypothese

#: Les variables des modèles de ciblage (famille C) et de la covariable d'avant
#: (famille M). Le modèle est linéaire, estimé par moindres carrés dans chaque
#: bras (effet estimé = écart des deux prédictions, risque = 1 − prédiction du
#: témoin) ; `log_` désigne log(1 + x).
VARIABLES = {
    "hillstrom": ("recence", "log_historique", "hommes", "femmes", "nouveau",
                  "zone_s", "zone_r", "canal_w", "canal_m"),
    "lenta": ("age", "sexe_f", "sexe_m", "enfants", "format", "anciennete", "rep_sms",
              "rep_viber", "promo", "log_depense_12m", "log_depense_3m",
              "log_recus_12m", "log_recus_3m", "log_folies_12m"),
    "x5": ("age", "sexe_f", "sexe_m", "log_passages", "log_depense", "recence_j",
           "premier_j", "express_oui", "carte_j", "points_oui"),
}
#: La part des clients que l'agence choisit d'écrire (famille C).
PART_CIBLEE = 1 / 3

FAMILLES = {
    "E": "Relancer",
    "C": "Cibler",
    "G": "Garder",
    "B": "Fixer un objectif",
    "M": "Mesurer",
}

H = (
    # --- Relancer : un message tiré au sort fait-il acheter, et chez qui ? ----
    Hypothese("E01", "E", "hillstrom", "Un courriel de relance fait acheter", +1,
              "taux d'achat sur deux semaines, courriel (hommes ou femmes) contre aucun",
              "Un message groupé déclenche des achats, pas seulement des ouvertures."),
    Hypothese("E02", "E", "hillstrom", "Un courriel de relance fait dépenser", +1,
              "dépense moyenne par client sur deux semaines, zéros compris, courriel contre aucun",
              "Le message rapporte de l'argent, pas seulement des clics."),
    Hypothese("E03", "E", "hillstrom", "Un courriel de relance fait venir", +1,
              "taux de visite du site sur deux semaines, courriel contre aucun",
              "Le message ramène le fan sur la page."),
    Hypothese("E04", "E", "hillstrom", "Le courriel assorti aux achats passés fait davantage venir", +1,
              "visite, courriel de la catégorie déjà achetée contre l'autre catégorie, "
              "chez les clients d'une seule catégorie, écart moyen pondéré par catégorie",
              "Parler au fan de ce qu'il a déjà acheté, pas d'autre chose."),
    Hypothese("E05", "E", "hillstrom", "L'effet du courriel change avec la récence du client", 0,
              "interaction courriel × dernier achat à la médiane ou plus récent, sur la visite",
              "Relancer d'abord le récent ou d'abord l'endormi ?"),
    Hypothese("E06", "E", "hillstrom", "L'effet du courriel change avec la valeur du client", 0,
              "interaction courriel × dépense de l'année au-dessus de la médiane, sur la visite",
              "Le gros acheteur réagit-il plus au message groupé ?"),
    Hypothese("E07", "E", "hillstrom", "L'effet du courriel change chez le nouveau client", 0,
              "interaction courriel × client arrivé dans l'année, sur la visite",
              "Le nouvel abonné réagit-il plus ou moins à une relance ?"),
    Hypothese("E08", "E", "lenta", "Un SMS de relance fait venir", +1,
              "taux de visite en magasin après la campagne, SMS contre témoin",
              "Le message groupé, à l'échelle de centaines de milliers de clients."),
    Hypothese("E09", "E", "lenta", "Le SMS agit davantage sur qui a déjà répondu à un SMS", +1,
              "interaction SMS × part de réponses aux SMS passés supérieure à zéro, sur la visite",
              "Le fan qui a déjà réagi à vos messages est celui que le message fait bouger."),
    Hypothese("E10", "E", "lenta", "L'effet du SMS change chez le client fréquent", 0,
              "interaction SMS × reçus des trois derniers mois à la médiane ou plus, sur la visite",
              "Relancer l'habitué ou le client rare ?"),
    Hypothese("E11", "E", "lenta", "L'effet du SMS change chez le chasseur de promotions", 0,
              "interaction SMS × part de produits en promotion sur quinze jours au-dessus de la médiane",
              "Le fan qui n'achète qu'en promo réagit-il autrement ?"),
    Hypothese("E12", "E", "lenta", "Le SMS fait aussi venir les hommes", +1,
              "taux de visite, SMS contre témoin, clients hommes seulement",
              "Un public d'abonnés est masculin : l'effet doit tenir chez les hommes."),
    Hypothese("E13", "E", "x5", "Un SMS de relance fait acheter", +1,
              "taux d'achat après la campagne, SMS contre témoin",
              "Un message groupé déclenche des achats chez des clients connus."),
    Hypothese("E14", "E", "x5", "L'effet du SMS change avec la récence du client", 0,
              "interaction SMS × dernier passage à la médiane ou plus récent, sur l'achat",
              "Relancer d'abord le récent ou d'abord l'endormi ?"),
    Hypothese("E15", "E", "x5", "L'effet du SMS change chez le client fréquent", 0,
              "interaction SMS × passages en caisse à la médiane ou plus, sur l'achat",
              "Relancer l'habitué ou le client rare ?"),
    Hypothese("E16", "E", "x5", "L'effet du SMS change chez le client des promotions", 0,
              "interaction SMS × au moins un passage payé en points de promotion, sur l'achat",
              "Le fan des offres spéciales réagit-il autrement ?"),
    # --- Cibler : par l'effet attendu, pas par le risque (Ascarza, 2018) ------
    Hypothese("C01", "C", "hillstrom", "Le tiers choisi par effet estimé répond plus que le tiers choisi par risque", +1,
              "effet du courriel sur la visite dans chaque tiers, moitié de validation",
              "Relancer ceux que le message fait bouger, pas ceux qui partent."),
    Hypothese("C02", "C", "hillstrom", "Le tiers le plus à risque répond moins que la moyenne", -1,
              "effet du courriel sur la visite, tiers au plus faible taux de base prédit contre tous",
              "Relancer d'abord les fans qui décrochent est un gaspillage."),
    Hypothese("C03", "C", "hillstrom", "Le tiers choisi par effet estimé répond plus que la moyenne", +1,
              "effet du courriel sur la visite, tiers choisi contre tous, moitié de validation",
              "Choisir à qui écrire vaut mieux qu'écrire à tous."),
    Hypothese("C04", "C", "lenta", "Le tiers choisi par effet estimé répond plus que le tiers choisi par risque", +1,
              "effet du SMS sur la visite dans chaque tiers, moitié de validation",
              "Relancer ceux que le message fait bouger, pas ceux qui partent."),
    Hypothese("C05", "C", "lenta", "Le tiers le plus à risque répond moins que la moyenne", -1,
              "effet du SMS sur la visite, tiers au plus faible taux de base prédit contre tous",
              "Relancer d'abord les fans qui décrochent est un gaspillage."),
    Hypothese("C06", "C", "lenta", "Le tiers choisi par effet estimé répond plus que la moyenne", +1,
              "effet du SMS sur la visite, tiers choisi contre tous, moitié de validation",
              "Choisir à qui écrire vaut mieux qu'écrire à tous."),
    Hypothese("C07", "C", "x5", "Le tiers choisi par effet estimé répond plus que le tiers choisi par risque", +1,
              "effet du SMS sur l'achat dans chaque tiers, moitié de validation",
              "Relancer ceux que le message fait bouger, pas ceux qui partent."),
    Hypothese("C08", "C", "x5", "Le tiers le plus à risque répond moins que la moyenne", -1,
              "effet du SMS sur l'achat, tiers au plus faible taux de base prédit contre tous",
              "Relancer d'abord les fans qui décrochent est un gaspillage."),
    Hypothese("C09", "C", "x5", "Le tiers choisi par effet estimé répond plus que la moyenne", +1,
              "effet du SMS sur l'achat, tiers choisi contre tous, moitié de validation",
              "Choisir à qui écrire vaut mieux qu'écrire à tous."),
    # --- Garder : les fidèles d'un second marché (Online Retail II) -----------
    Hypothese("G01", "G", "retail", "Le modèle BG/NBD prédit mieux que le rythme passé", +1,
              "erreur absolue moyenne des jours d'achat de l'année de validation",
              "Classer les fans par probabilité d'être encore là, sur un second marché."),
    Hypothese("G02", "G", "retail", "Après un long silence, l'ancien acheteur fréquent revient davantage", +1,
              "jours d'achat de l'année suivante selon la fréquence passée, silencieux depuis six mois",
              "Le fidèle qui se tait n'est pas perdu : le résultat du cahier nº 1 se revérifie-t-il ?"),
    Hypothese("G03", "G", "retail", "Le modèle sous-estime d'autant plus le silencieux qu'il était fréquent", +1,
              "écart entre achats réalisés et prédits par BG/NBD selon la fréquence passée, silencieux",
              "La faille du modèle publié se retrouve-t-elle ailleurs ?"),
    Hypothese("G04", "G", "retail", "Le classement BG/NBD capte davantage les achats futurs", +1,
              "part des jours d'achat futurs captée par le décile de tête, contre la dépense passée",
              "Qui relancer en premier, à budget de chatteur fixé."),
    Hypothese("G05", "G", "retail", "Une grosse première commande annonce un client qui revient", +1,
              "jours d'achat de l'année de validation, première commande au-dessus de la médiane contre en dessous",
              "Le premier achat d'un fan dit déjà ce qu'il vaudra."),
    # --- Fixer un objectif : Kickstarter ---------------------------------------
    Hypothese("B01", "B", "kickstarter", "Les promesses s'entassent juste au-dessus de l'objectif", +1,
              "rapport des campagnes entre 100 et 105 % de l'objectif à celles entre 95 et 100 %, "
              "contre la pente lisse lue de 85 à 95 % et de 105 à 115 %",
              "Un objectif affiché attire les derniers dons vers lui : la cagnotte d'un live."),
    Hypothese("B02", "B", "kickstarter", "Une campagne plus longue réussit moins", -1,
              "réussite selon la durée (par dix jours), objectif, catégorie et année fixés",
              "Une offre limitée dans le temps vaut mieux qu'une offre qui traîne."),
    Hypothese("B03", "B", "kickstarter", "Un objectif plus haut réussit moins", -1,
              "réussite selon le logarithme de l'objectif, catégorie et année fixées",
              "Un palier modeste est atteint ; un palier ambitieux reste vide."),
    Hypothese("B04", "B", "kickstarter", "Un objectif rond change la réussite", 0,
              "objectif multiple de 1 000 dans sa monnaie contre non rond, objectif, catégorie et année fixés",
              "Afficher 1 000 ou 970 comme objectif de cagnotte ?"),
    Hypothese("B05", "B", "kickstarter", "Un lancement le week-end change la réussite", 0,
              "lancement le samedi ou le dimanche contre en semaine, objectif, catégorie et année fixés",
              "Lancer une offre le week-end ou en semaine ?"),
    # --- Mesurer : la covariable d'avant (Deng et al., 2013) ------------------
    Hypothese("M01", "M", "hillstrom", "L'historique d'avant prédit la dépense après le courriel", +1,
              "corrélation entre la dépense prédite par l'historique (estimée sur une moitié) et la dépense, autre moitié",
              "Ajuster un test sur le passé du fan pour le rendre moins cher."),
    Hypothese("M02", "M", "lenta", "L'historique d'avant prédit la visite après le SMS", +1,
              "corrélation entre la visite prédite par l'historique (estimée sur une moitié) et la visite, autre moitié",
              "Ajuster un test sur le passé du fan pour le rendre moins cher."),
    Hypothese("M03", "M", "x5", "L'historique d'avant prédit l'achat après le SMS", +1,
              "corrélation entre l'achat prédit par l'historique (estimé sur une moitié) et l'achat, autre moitié",
              "Ajuster un test sur le passé du fan pour le rendre moins cher."),
)


def par_id() -> dict[str, Hypothese]:
    return {h.id: h for h in H}
