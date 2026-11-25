"""Les mots simples du cahier nº 4 — écrits devant des verdicts, et figés.

Pour chaque hypothèse : une explication normale, une version « comme à 5 ans »
et un exemple d'agence. `VERDICTS_ECRITS` et `SURVIE_ECRITE` fixent les verdicts
et la survie à la batterie sous lesquels ces textes ont été écrits : si un
calcul change l'un d'eux, `TestClair4` échoue, et c'est le texte qu'on réécrit,
jamais le test. Les nombres ne sont jamais écrits ici : ils viennent de la page
(`{{clé}}`), calculés.
"""

from __future__ import annotations

VERDICTS_ECRITS = {
    "A01": "non établi", "A02": "tient", "A03": "tient", "A04": "tient", "A05": "tient", "A06": "non établi",
    "A07": "tient", "A08": "tient", "A09": "tient", "A10": "non établi", "A11": "non établi", "A12": "tient",
    "B01": "non établi", "B02": "non établi", "B03": "non établi", "B04": "non établi",
    "K01": "non établi", "K02": "non établi", "K03": "tient",
    "W01": "contraire", "W02": "non établi", "W03": "non établi",
    "R01": "tient", "R02": "tient", "R03": "tient",
}
SURVIE_ECRITE = {i: i == "R03" for i in VERDICTS_ECRITS}

CARTES = {
    "A01": ("Sur Hillstrom, la politique apprise écrit à des clients qui répondent un peu mieux que les gros dépensiers, "
            "mais l'écart reste dans le bruit.",
            "Celui qui a appris et celui qui suit la mode finissent presque à égalité ici.",
            "Une boutique de vêtements écrit à un tiers de ses clients : la liste apprise et la liste des meilleurs "
            "acheteurs font presque pareil."),
    "A02": ("Sur Lenta, la politique apprise fait venir davantage que l'envoi aux gros dépensiers. Mais le placebo a "
            "trouvé un défaut dans ce jeu : à lire avec prudence.",
            "Celui qui apprend gagne, mais l'arbitre a vu que les deux équipes n'étaient pas tirées à égalité.",
            "Une agence qui ne vérifie pas que son groupe témoin ressemble aux autres peut croire à un gain qui "
            "vient du tirage, pas du message."),
    "A03": ("Sur X5, apprendre à qui écrire fait plusieurs fois mieux qu'écrire aux gros dépensiers, et cela tient "
            "sous tous les réglages essayés.",
            "Les gros dépensiers achètent de toute façon : le message ne change rien pour eux. Celui qui apprend "
            "écrit à ceux que le message fait vraiment acheter.",
            "Au lieu d'envoyer le PPV d'abord aux vingt meilleurs fans, on l'envoie à ceux que les essais passés "
            "ont montrés sensibles au message."),
    "A04": ("Sur Hillstrom, apprendre fait mieux que relancer les clients les plus à risque, mais pas assez nettement "
            "pour passer les seuils les plus sévères.",
            "Celui qui va partir n'est pas toujours celui qu'un message retient.",
            "Relancer « ceux qui n'ont rien acheté depuis longtemps » rapporte moins que relancer ceux qui ont "
            "réagi aux relances."),
    "A05": ("Sur Lenta, apprendre fait mieux que relancer les plus à risque. Même défaut de tirage que A02 : prudence.",
            "Le résultat va dans le bon sens, mais les équipes n'étaient pas tirées à égalité.",
            "Un résultat qui vient d'un jeu mal tiré se revérifie chez soi avant de servir."),
    "A06": ("Sur X5, la politique apprise et la relance des plus à risque ne se départagent pas.",
            "Ici, les deux façons de choisir finissent ensemble.",
            "Si les clients à risque sont aussi ceux que le message touche, les deux listes se ressemblent."),
    "A07": ("Sur Hillstrom, apprendre bat le hasard, mais d'un écart que les seuils les plus sévères ne retiennent pas.",
            "Choisir aide un peu, mais c'est encore proche d'un tirage au sort.",
            "Sur une petite base, l'avantage d'apprendre existe mais se voit mal."),
    "A08": ("Sur Lenta, apprendre bat le hasard. Le placebo échoue : le jeu n'est pas équilibré, le résultat ne compte "
            "pas comme preuve.",
            "On a gagné, mais l'arbitre dit que le terrain était penché.",
            "Toujours vérifier que le groupe témoin ressemble au groupe écrit avant de lire un résultat."),
    "A09": ("Sur X5, apprendre à qui écrire fait nettement mieux que le hasard, sous presque tous les réglages, et le "
            "réglage choisi d'avance ne doit rien à la chance.",
            "Si tu sais qui aime les bonbons, tu ne les distribues pas au hasard.",
            "Un groupe témoin de 10 % sur chaque campagne suffit à apprendre, mois après mois, quels fans le message "
            "fait acheter."),
    "A10": ("Sur Hillstrom, écrire aux gros dépensiers ne fait ni mieux ni moins bien que le hasard.",
            "La règle à la mode ne gagne pas ici.",
            "Suivre la règle que tout le monde suit ne donne pas d'avance."),
    "A11": ("Sur Lenta, la règle des gros dépensiers et le hasard ne se départagent pas.",
            "Ici non plus, la mode ne gagne rien.",
            "Les outils qui trient par dépense ne disent pas à qui le message sert."),
    "A12": ("Sur X5, écrire d'abord aux gros dépensiers fait pire que le hasard : ils achètent de toute façon, le "
            "message est gaspillé. Ce n'est vrai que sur ce marché.",
            "Donner un bonbon à celui qui en a déjà plein ne le rend pas plus content.",
            "Avant de réserver les relances aux meilleurs fans, vérifier avec un groupe témoin qu'elles changent "
            "quelque chose chez eux."),
    "B01": ("Sur tous les articles, l'algorithme qui apprend et le hasard ne se départagent pas dans l'échantillon public.",
            "Avec trop peu d'essais, on ne voit pas qui gagne.",
            "Pour voir l'avantage d'un bandit, il faut beaucoup d'impressions : l'échantillon public en a cent fois "
            "moins que le jeu complet."),
    "B02": ("Au rayon hommes, Thompson fait plus de clics que le hasard, mais pas assez nettement une fois les 25 tests "
            "corrigés.",
            "Il gagne un peu, mais on ne peut pas encore dire que ce n'est pas la chance.",
            "Un bon résultat sur un seul rayon ne suffit pas : il faut le revoir ailleurs."),
    "B03": ("Au rayon femmes, aucun écart entre Thompson et le hasard dans l'échantillon.",
            "Les deux robots ont fait exactement aussi bien : pas de gagnant ici.",
            "Sur peu de données, le hasard et l'apprentissage se ressemblent."),
    "B04": ("Les trois rayons ensemble : Thompson fait un peu plus de clics, sans que ce soit établi sur cet échantillon. "
            "Sur le jeu complet, l'article le trouve nettement.",
            "Celui qui apprend gagne sur beaucoup de parties, mais nos parties étaient trop peu nombreuses.",
            "Pousser le contenu qui marche en continuant d'essayer les autres : à mesurer chez soi sur assez de fans."),
    "K01": ("Lancer la même semaine que beaucoup de campagnes de sa catégorie ne fait pas nettement moins réussir.",
            "Être nombreux sur le même terrain ne fait pas perdre à coup sûr.",
            "Envoyer le vendredi soir comme toutes les agences n'est pas prouvé plus mauvais ; c'est à tester chez soi."),
    "K02": ("La foule de sa catégorie ne pèse pas nettement plus que celle du reste du site.",
            "On ne sait pas si c'est la concurrence directe ou l'agitation générale qui compte.",
            "Rien ne prouve qu'il faille fuir les créneaux où les concurrents publient."),
    "K03": ("Les premières campagnes d'un pays qui ouvre réussissent moins que les suivantes. Mais un faux jour "
            "d'ouverture, un an plus tard, donne aussi un écart : ce n'est pas l'effet d'être premier.",
            "Le premier arrivé semblait perdre, mais la même chose arrive quand personne n'arrive : ce n'est pas lui.",
            "Se ruer sur un marché neuf « pour être premier » n'est pas une avance prouvée."),
    "W01": ("Sur CDNOW, la plupart des baleines de demain étaient déjà des baleines : le pari disait l'inverse.",
            "Celui qui achète beaucoup continue souvent d'acheter beaucoup.",
            "Les gros fans restent gros : la question n'est pas de les trouver, c'est de savoir si un message change "
            "quelque chose chez eux (A12)."),
    "W02": ("Sur Online Retail II, la part de nouvelles baleines reste sous la moitié, sans être établie.",
            "Ici, on ne peut pas trancher.",
            "Les meilleurs clients changent un peu, pas beaucoup."),
    "W03": ("Sur X5 (quatre mois seulement), un peu plus de la moitié des baleines sont nouvelles, sans que ce soit établi.",
            "Sur peu de temps, on ne voit pas bien qui reste en tête.",
            "Sur une courte période, la tête de liste bouge davantage."),
    "R01": ("Sur CDNOW, l'accélération annonce la dépense au-delà de RFM, sous tous les réglages et à chaque coupe ; "
            "seul le Sharpe dégonflé échoue, faute de périodes.",
            "Le fan qui revient de plus en plus vite dépense plus, et on le voit à chaque fois.",
            "Marquer dans le CRM les fans dont les achats se rapprochent, avant qu'ils ne deviennent des baleines."),
    "R02": ("Sur Online Retail II, l'accélération tient, mais pas sous les seuils les plus sévères ni au Sharpe dégonflé.",
            "Ça marche aussi ici, un peu moins fort.",
            "Le même signal, sur un autre marché : utile, à suivre."),
    "R03": ("Sur X5, l'accélération annonce la dépense au-delà de RFM et passe tous les tests qui s'appliquent à elle : "
            "c'est l'avance qui survit à la batterie.",
            "Celui qui revient de plus en plus vite est en train de s'attacher. Personne ne le regarde, et ça ne "
            "dépend pas du réglage.",
            "Chaque lundi : la liste des fans dont l'écart entre deux achats raccourcit, pour qu'un chatteur leur "
            "écrive avant les autres agences."),
}

#: Les treize tests : nom court, explication, version « 5 ans », exemple.
TESTS_CLAIR = {
    "nul": ("La loi nulle", "On compare le résultat à ce que donnerait le hasard seul, sur les mêmes données.",
            "Si on lance une pièce, on peut avoir trois faces de suite sans truc.",
            "Un PPV qui vend 2 % de plus une semaine peut être de la chance."),
    "bh": ("La famille corrigée", "Avec 25 tests, quelques-uns passent par chance : on relève le seuil pour tous "
           "(Benjamini et Hochberg).", "Plus on achète de tickets, plus on gagne un petit lot par hasard.",
           "Tester 25 idées de relance et garder la meilleure, c'est presque toujours en garder une fausse."),
    "holm": ("Aucune fausse alerte", "Plus sévère encore : la chance d'une seule fausse alerte dans toute la famille "
             "reste sous 5 %.", "On ne veut pas un seul faux trésor dans le coffre.",
             "Avant de changer toute l'équipe de chat, une preuve qui ne laisse presque aucune place au hasard."),
    "t3": ("Le seuil des quants", "Après des centaines de signaux essayés par la recherche, un t de 3, pas 1,96 "
           "(Harvey, Liu et Zhu).", "Quand tout le monde cherche au même endroit, il faut crier plus fort pour être sûr.",
           "Une astuce lue partout doit être bien plus nette qu'une astuce que personne n'a essayée."),
    "coupes": ("Autres coupes", "On refait le partage pilote / jugés avec 19 autres tirages : le sens doit rester.",
               "On rebat les cartes vingt fois : on doit gagner presque à chaque fois.",
               "Le résultat ne doit pas dépendre du groupe de fans tiré pour le test."),
    "marches": ("Autres marchés", "La même mesure, sur les autres marchés : le sens doit être le même partout.",
                "Ce qui marche chez toi doit marcher chez ton cousin.",
                "Une astuce qui ne marche que pour une créatrice n'est pas une méthode."),
    "spec": ("Courbe de spécification", "Le même effet sous tous les réglages raisonnables (taille du pilote, part écrite, "
             "modèle) : 90 % dans le sens, la moitié significative.",
             "On change les petites règles du jeu : si on gagne toujours, c'est qu'on est bon.",
             "Le gain ne doit pas disparaître si l'on écrit à 20 % des fans au lieu de 33 %."),
    "cscv": ("Choix du meilleur réglage", "On choisit le meilleur réglage sur une moitié des données, on le juge sur "
             "l'autre, 12 870 fois (Bailey et al.).",
             "Celui qui gagne à l'entraînement doit aussi gagner au match.",
             "Garder « la » meilleure heure d'envoi trouvée sur un mois : vérifier qu'elle reste bonne le mois suivant."),
    "spa": ("Fouille des données", "Parmi tous les réglages essayés, le meilleur bat-il vraiment la règle de la foule, "
            "ou l'a-t-on trouvé en cherchant ? (Hansen)",
            "Si tu essaies cent chapeaux, l'un d'eux t'ira bien par hasard.",
            "Avoir testé 36 façons de cibler et en montrer une ne prouve rien, sauf si elle passe ce test."),
    "placebo": ("Placebo", "On mesure un effet qui ne peut pas exister (une issue fixée avant le message) : on doit "
                "trouver zéro.", "On vérifie que la balance affiche zéro quand il n'y a rien dessus.",
                "Si le « gain » apparaît aussi sur l'âge des fans, ce n'est pas le message, c'est le tirage."),
    "temps": ("Stabilité dans le temps", "Le même sens, période après période.",
              "Ce qui marchait l'an dernier doit marcher cette année.",
              "Une recette qui ne marche qu'un mois sur deux est une loterie."),
    "dsr": ("Sharpe dégonflé", "La régularité du gain, corrigée du nombre d'essais et des mauvaises surprises "
            "(Bailey et López de Prado).", "Gagner souvent un peu vaut mieux que gagner une fois beaucoup.",
            "Un revenu qui monte chaque semaine bat un gros mois suivi de trois vides."),
    "arene": ("Quand les autres copient", "Dans l'arène, l'avance doit rester devant la mode dans 90 % des tirages, "
              "que 10, 50 ou 90 % des concurrents la copient.",
              "Si tout le monde fait comme toi, est-ce que tu gagnes encore ?",
              "Si toutes les agences mettent des groupes témoins, la tienne garde-t-elle une longueur d'avance ?"),
}

ETUDES = {
    "hillstrom": ("64 000 clients d'une boutique en ligne : un courriel tiré au sort (hommes, femmes ou rien).",
                  "On a écrit à certains et pas aux autres, au hasard, pour voir ce que la lettre change.",
                  "C'est le PPV envoyé à une partie des fans seulement, pour mesurer ce qu'il rapporte vraiment."),
    "lenta": ("687 029 clients d'une chaîne russe : un SMS tiré au sort. Le placebo a montré que les deux groupes ne se "
              "ressemblent pas (le groupe écrit avait déjà plus répondu aux SMS).",
              "Les deux équipes n'étaient pas tirées à égalité : il y a plus de bons joueurs dans l'une.",
              "Si ton groupe témoin a moins de fans fidèles que le groupe écrit, ton « gain » est faux."),
    "x5": ("200 039 clients d'une chaîne russe : un SMS tiré au sort, groupes bien équilibrés.",
           "Deux équipes vraiment tirées au sort : ce qui les sépare, c'est le message.",
           "Le meilleur jeu du cahier pour savoir à qui écrire."),
    "obp": ("ZOZOTOWN, une semaine : un algorithme qui apprend en continu contre le hasard, tirés au sort.",
            "Un robot qui apprend quels habits plaisent, contre un robot qui montre n'importe quoi.",
            "Comme choisir quel contenu proposer à quel fan, et changer dès qu'on voit ce qui marche."),
    "kickstarter": ("331 657 campagnes de financement participatif, 2009–2017 : qui réussit, quand, dans quelle catégorie.",
                    "Des milliers de vendeurs qui demandent de l'argent à la même foule.",
                    "Des créatrices qui se disputent les mêmes fans, le même soir."),
    "achats": ("Trois marchés d'achats répétés (CDNOW, Online Retail II, X5) : qui achète, quand, combien.",
               "Le carnet de chaque client : les jours où il est venu et ce qu'il a pris.",
               "L'historique d'achats de chaque fan, comme dans Lueur Sync."),
}

#: Les affirmations de l'arène : explication et version « 5 ans ».
Z_CLAIR = {
    "Z01": ("Un coup d'avance finit-il devant la mode dans au moins 9 tirages sur 10 ?",
            "Celui qui a prévu ce que font les autres gagne-t-il presque toujours ?"),
    "Z02": ("Un coup d'avance finit-il devant le guide dans au moins 9 tirages sur 10 ?",
            "Gagne-t-il presque toujours contre celui qui suit la recette ?"),
    "Z03": ("Un coup d'avance finit-il devant « trop d'avance » plus d'une fois sur deux ?",
            "Être trop malin, est-ce aussi perdre ?"),
    "Z04": ("Quand la moitié des concurrents copient, un coup d'avance reste-t-il au-dessus de la médiane 9 fois sur 10 ?",
            "Si la moitié de la classe copie ta recette, restes-tu dans la meilleure moitié ?"),
}

#: Sous chaque graphique : ce que tu vois, ce que ça montre, et ce que ton agence en fait.
GRAPHIQUES = {
    "etalonnage": ("Pour chaque outil, une barre bleue (avec l'outil) et, quand elle existe, une barre grise (sans correction), "
                   "sur des données où il n'y a aucun avantage à trouver.",
                   "Avec les outils, les fausses alertes restent sous la ligne de 5 % ; sans correction, 25 tests nuls en "
                   "donnent au moins une {{etal_holm_brut}} du temps.",
                   "Plus tu testes d'idées, plus il faut corriger avant de croire celle qui « marche »."),
    "recoupement": ("Une barre par outil : sa longueur dit combien de chiffres il partage avec la bibliothèque de référence.",
                    "Nos outils rendent les mêmes chiffres que statsmodels, scipy et numpy, à la précision de la machine ; le "
                    "test SPA prend les mêmes décisions que celui de la bibliothèque arch.",
                    "Les calculs de ce cahier peuvent être refaits avec les outils des quants : ils ne dépendent pas d'un "
                    "programme maison mal écrit."),
    "batterie": ("Une ligne par idée, une colonne par test : bleu passe, rouge échoue, gris sans objet ; le point de droite "
                 "est bleu si l'idée passe tout.",
                 "Une seule ligne est bleue partout où un test s'applique : l'accélération sur X5 (R03). Trois autres ne "
                 "ratent qu'une case.",
                 "Avant de bâtir une méthode sur une idée, regarde combien de tests elle passe, pas seulement si elle « marche »."),
    "batterie3d": ("Une colonne par famille : les tests passés en bleu, les échecs en rouge, les tests sans objet en fantôme gris.",
                   "Apprendre chez soi et l'accélération passent la plupart de leurs tests ; le bandit, la foule et les "
                   "baleines en ratent beaucoup.",
                   "Les idées de méthode (mesurer, cibler, repérer) résistent mieux que les idées d'astuce (le bon créneau, "
                   "être premier)."),
    "marche": ("Trois barres : la croissance sur un an des paiements des fans, des comptes de créateurs et des comptes de fans.",
               "Les comptes de créateurs (+{{croiss_crea}}) montent plus vite que l'argent payé (+{{croiss_brut}}) : il y a "
               "plus de vendeuses pour chaque dollar.",
               "Le gâteau grandit, mais il y a plus de parts : celle de chaque créatrice rétrécit si l'agence ne fait pas "
               "mieux que la moyenne."),
    "argent3d": ("Une colonne par stratégie : la plateforme, la créatrice, le chat et l'agence se partagent 100 $ payés par les fans.",
                 "Prendre moins aux créatrices laisse moins à l'agence sur chaque dollar : elle doit le rattraper par le "
                 "nombre de créatrices et par ce que la méthode rapporte.",
                 "Avant de baisser ta part, calcule combien de créatrices en plus il te faut pour gagner autant."),
    "niveaux": ("Une barre par niveau de raisonnement : la part des gens qui pensent à 0, 1, 2, ou 3 coups d'avance et plus.",
                "Avec {{tau}} coups d'avance en moyenne, la plupart des gens sont aux niveaux 0 et 1 ; une petite partie "
                "au niveau 2, encore moins au-delà.",
                "La plupart de tes concurrents suivent le guide ou la mode : un coup d'avance sur eux suffit."),
    "a_gains": ("Pour chaque marché, ce que le message rapporte pour 100 clients selon la façon de choisir à qui écrire.",
                "La barre bleue (appris chez soi) est la plus haute sur les trois marchés ; sur X5, la règle des gros "
                "dépensiers fait moins que le hasard.",
                "Écrire d'abord aux gros dépensiers n'est pas une stratégie : c'est l'habitude de la foule."),
    "a_spec": ("Pour chaque marché, les 36 réglages de la politique apprise contre le hasard, rangés du moins bon au meilleur.",
               "Sur X5, presque tous les réglages sont au-dessus de zéro ; sur Hillstrom et Lenta, une partie reste dans le bruit.",
               "Une méthode qui ne marche que sous un réglage précis est fragile : la tienne doit gagner sous presque tous."),
    "a_spec3d": ("Des blocs, un par taille de pilote (lignes) et part de la base écrite (colonnes) ; plus le bloc est haut, "
                 "plus la politique apprise bat le hasard.",
                 "Sur X5, chaque bloc dépasse zéro : l'avance ne dépend ni de la taille du pilote ni de la part écrite.",
                 "Même un petit pilote suffit pour commencer à apprendre : 20 % de la base donnent déjà l'avance."),
    "b_jours": ("Une barre par jour de la semaine du test : l'écart de clics entre l'algorithme qui apprend et le hasard ; "
                "la ligne pointillée est l'écart publié sur le jeu complet.",
                "L'écart change de signe d'un jour à l'autre : sur 60 000 impressions, le bruit domine ; le jeu complet, "
                "cent fois plus grand, montre l'avance.",
                "Pour juger un bandit, il faut beaucoup d'envois : sur une petite base, une semaine ne prouve rien."),
    "k_annees": ("Une barre par année : ce que la foule de sa catégorie fait à la réussite d'une campagne.",
                 "Le signe change d'une année à l'autre : aucun effet stable de la foule.",
                 "Rien ne prouve qu'il faille fuir, ni suivre, les créneaux de la foule : teste les tiens."),
    "k_pionniers": ("Un point par pays : les pionniers moins les suivants, témoin américain retiré ; la ligne bleue est la "
                    "vraie ouverture, la rouge un faux jour un an plus tard.",
                    "Les deux lignes sont sous zéro : l'écart des pionniers se retrouve sans ouverture, il ne vient donc pas "
                    "du fait d'être premier.",
                    "Ne paie pas pour être le premier sur une nouvelle plateforme : sois prêt à y être bon."),
    "w_baleines": ("Pour chaque marché, la part des meilleurs clients de la validation qui étaient déjà parmi les meilleurs.",
                   "Sur CDNOW et Online Retail II, environ deux baleines sur trois l'étaient déjà ; sur X5, en quatre mois, "
                   "la tête bouge davantage.",
                   "Tes gros fans restent gros : inutile de les chercher, mesure plutôt si tes messages changent quelque "
                   "chose chez eux."),
    "w3d": ("Des blocs par marché (lignes) et par taille de la tête de liste (colonnes) ; la hauteur est la part déjà baleine.",
            "Sur CDNOW et Online Retail II, plus de la moitié quelle que soit la taille de la tête ; sur X5, un peu moins.",
            "La liste des meilleurs fans change lentement : elle se suit au mois, pas au jour."),
    "r_glissant": ("Deux courbes, une par marché : l'effet de l'accélération à sept coupes successives.",
                   "Les deux courbes restent au-dessus de zéro à chaque coupe : le signal ne dépend pas de la date.",
                   "Un signal qui tient à chaque date peut servir chaque semaine."),
    "r3d": ("Des blocs par marché (lignes) et par définition de l'accélération (colonnes) ; la hauteur est l'effet au-delà de RFM.",
            "Tous les blocs sont positifs : quelle que soit la façon de mesurer le rythme, le fan qui accélère dépense plus.",
            "Choisis la définition la plus simple à calculer : elles disent toutes la même chose."),
    "arene_rangs": ("Une ligne par stratégie : la barre couvre la moitié des tirages, le point est le rang médian, le trait va "
                    "du pire au meilleur.",
                    "Un coup d'avance a le meilleur rang médian ({{rang_med_2}}) et le meilleur pire cas ; trop d'avance "
                    "finit le plus bas ({{rang_med_3}}).",
                    "Un coup d'avance est la stratégie la plus sûre, pas une garantie."),
    "arene_tornade": ("Pour les huit paramètres qui comptent le plus, deux points : la part des tirages où un coup d'avance "
                      "bat la mode quand le paramètre est bas (gris) ou haut (bleu).",
                      "L'avance gagne presque toujours quand la règle à la mode s'use (beaucoup d'agences sur les mêmes gros "
                      "fans) et quand les créatrices regardent ce qu'elles gagnent ; elle recule quand dire la vérité coûte "
                      "cher aux fans ou quand apprendre demande beaucoup de fans.",
                      "Ce sont les quatre choses à surveiller chez toi : la saturation des gros fans, ce que tu paies aux "
                      "créatrices, ce que coûte la franchise, et la taille de ta base."),
    "arene3d": ("Des blocs selon les deux paramètres les plus influents ; la hauteur est la part des tirages où un coup "
                "d'avance bat la mode.",
                "Quand la mode s'use et que les créatrices regardent leur paie, l'avance est presque sûre ; quand ni l'un ni "
                "l'autre, elle se joue à pile ou face.",
                "Plus tes concurrents se battent pour les mêmes gros fans, plus ta méthode vaut."),
    "arene_part": ("Un point par stratégie : la part des créatrices captée à 36 mois (en largeur) et le rang de profit médian "
                   "(en hauteur).",
                   "Trop d'avance capte le plus de créatrices mais gagne le moins ; un coup d'avance gagne le plus.",
                   "Capter la plus grosse part ne veut pas dire gagner le plus : choisis ce que tu vises."),
}
