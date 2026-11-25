"""Le plan de A à Z et la formation du cahier nº 4 — tirés des verdicts, jamais d'une intuition.

Chaque phase et chaque leçon dit **pourquoi** (les hypothèses du registre qui la
portent, et les études d'ailleurs), **comment**, **ce que font les autres**,
**pourquoi ça tient quand ils copient**, et **comment le vérifier chez soi**.
Les textes sont écrits devant les verdicts de `clair4.VERDICTS_ECRITS` ; les
nombres viennent de la page (`{{clé}}`). Un test vérifie que chaque hypothèse
citée existe et porte le verdict sous lequel le texte a été écrit.

La structure des leçons reprend les blocs des parcours de Lueur
(`lib/formation/*.ts` : lead, kid, steps, do, warn, quiz) pour entrer dans
l'app sans réécriture.
"""

from __future__ import annotations

PLAN = (
    {"id": "regles", "titre": "Les règles du jeu, avant le jeu",
     "phrase": "Une agence qui triche gagne vite et perd tout d'un coup : on commence par ce qui ne se négocie pas.",
     "pourquoi": "Depuis le 2 août 2026, une IA qui parle à un fan doit se présenter (AI Act, article 50) ; une "
                 "action de groupe vise neuf agences dont les chatteurs se faisaient passer pour les créatrices ; les "
                 "règles de paiement imposent âge et consentement vérifiés. Dans l'arène, la « mode » (IA non "
                 "annoncée) gagne tant qu'elle n'est pas contrôlée, puis perd jusqu'à {{divulgation}} de ses ventes "
                 "de chat quand elle doit s'annoncer (Luo et al.).",
     "preuves": (), "refs": ("ue2024ai", "nzfenix2024", "mastercard2021", "luo2019", "senat2026"),
     "etapes": ("Contrat écrit avec chaque créatrice : part, limites, droit de partir avec ses comptes.",
                "Âge et identité vérifiés pour toute personne qui apparaît dans un contenu.",
                "Le chat dit qui écrit : « l'équipe de [prénom] » ; une IA s'annonce si elle converse seule.",
                "Aucun faux compte à rebours, aucune case cochée qui fait payer, aucune cible en détresse."),
     "autres": "Niveau 0 et niveau 1 : chatteurs qui jouent la créatrice, IA non annoncée, urgences inventées.",
     "copie": "La règle ne s'use pas quand les autres la suivent : elle protège de la chute, pas du concurrent.",
     "verifier": "La liste des quatre points est cochée pour chaque créatrice avant le premier message."},
    {"id": "mesurer", "titre": "Mesurer avant de croire",
     "phrase": "Chaque campagne garde un groupe témoin tiré au sort ; on vérifie qu'il ressemble au groupe écrit.",
     "pourquoi": "Sans témoin, on ne sait pas ce que le message rapporte. Et un témoin mal tiré ment : le placebo de ce "
                 "cahier a trouvé que le jeu Lenta, présenté comme tiré au sort, ne l'est pas (z = {{lenta_z_rep}} sur "
                 "la réponse passée aux SMS). Les entreprises qui testent ainsi progressent de 30 à 100 % en un an "
                 "(Koning et al.).",
     "preuves": ("A02", "A08"), "refs": ("koning2022",),
     "etapes": ("Tirer au sort 10 % des fans de chaque campagne : ils ne reçoivent pas le message.",
                "Écrire d'avance ce qu'on mesure (ventes à 7 jours) et ce qui comptera comme réussite.",
                "Vérifier l'équilibre : même dépense passée, même ancienneté dans les deux groupes.",
                "Lire l'écart entre les deux groupes, avec son intervalle, jamais le total vendu."),
     "autres": "Niveau 0 : regarde le total vendu. Niveau 1 : compare au mois d'avant (la saison ment).",
     "copie": "Ce que tes témoins t'apprennent sur tes fans n'est écrit nulle part : personne ne peut le copier.",
     "verifier": "Quatre campagnes de suite avec témoin, équilibre vérifié, écart lu avec son intervalle."},
    {"id": "cibler", "titre": "Écrire à ceux que le message change",
     "phrase": "Pas aux plus gros dépensiers d'office : à ceux que tes propres témoins montrent sensibles au message.",
     "pourquoi": "Sur X5, la politique apprise fait {{x5_appris}} achats pour 100 clients, le hasard {{x5_hasard}}, la "
                 "règle des gros dépensiers {{x5_valeur}} — pire que le hasard (A12). L'avance tient sous presque tous "
                 "les réglages (A03, A09). Les gros dépensiers achètent de toute façon : le message ne change rien "
                 "chez eux.",
     "preuves": ("A03", "A09", "A12", "A04"), "refs": ("ascarza2018",),
     "etapes": ("Après trois campagnes avec témoin, comparer par segment l'écart écrits / témoins.",
                "Classer les fans par effet estimé, pas par dépense.",
                "Écrire au tiers de tête ; garder le témoin pour réapprendre.",
                "Recommencer chaque mois : l'effet change avec les fans."),
     "autres": "Niveau 1 : « les vingt meilleurs fans d'abord », la liste que tous les outils affichent.",
     "copie": "Même si toutes les agences apprennent, chacune apprend sur ses propres fans : l'avance ne s'use pas "
              "dans l'arène ({{copie_10}} des tirages à 10 % d'imitateurs, {{copie_90}} à 90 %).",
     "verifier": "Sur ton témoin, la liste apprise fait mieux que la liste au hasard, intervalle au-dessus de zéro."},
    {"id": "accelerer", "titre": "Repérer ceux qui accélèrent",
     "phrase": "Le fan dont les achats se rapprochent vaut plus que ce que disent ses chiffres : c'est l'avance qui "
               "passe toute la batterie.",
     "pourquoi": "L'accélération annonce la dépense au-delà de ce que récence, fréquence et montant savent déjà, sur "
                 "trois marchés ({{r01_ic}}, {{r02_ic}}, {{r03_ic}}) ; sur X5, elle passe chacun des tests qui "
                 "s'appliquent à elle (R03). Les outils du marché trient par dépense : presque personne ne regarde "
                 "le rythme.",
     "preuves": ("R03", "R01", "R02"), "refs": ("fader2005",),
     "etapes": ("Pour chaque fan d'au moins trois achats : l'écart moyen entre les premiers achats, puis entre les "
                "derniers.", "Si les derniers écarts sont plus courts, le fan accélère : il entre dans la liste.",
                "Chaque lundi, la liste va aux chatteurs, avant les relances générales.",
                "Mesurer sur deux mois si ces fans dépensent plus que leurs chiffres ne l'annonçaient."),
     "autres": "Niveau 1 : trie par dépense totale (les baleines restent des baleines : W01).",
     "copie": "Si d'autres agences l'apprennent, elles regardent leurs fans, pas les tiens. Le signal est petit : il "
              "sert parce qu'il sert souvent.",
     "verifier": "Après deux mois, la dépense des fans de la liste dépasse celle prévue par leur RFM."},
    {"id": "bandit", "titre": "Pousser ce qui marche sans arrêter d'essayer",
     "phrase": "Proposer plus souvent le contenu qui vend, tout en laissant une petite place aux autres.",
     "pourquoi": "Sur le jeu complet de ZOZOTOWN, l'algorithme qui apprend en continu fait {{obp_th}} de clics contre "
                 "{{obp_ha}} au hasard ; une banque y a gagné 8 % de clients (Schwartz et al.). Sur l'échantillon "
                 "public, cent fois plus petit, l'écart n'est pas établi (B04) : il faut beaucoup d'essais pour le voir.",
     "preuves": ("B04",), "refs": ("saito2021", "schwartz2017"),
     "etapes": ("Pour chaque contenu : nombre d'envois et nombre d'achats.",
                "Avant chaque envoi, tirer pour chaque contenu un taux plausible (ses achats et ses échecs) et "
                "proposer le plus haut.", "Les contenus qui vendent reviennent, les autres restent essayés.",
                "Comparer à la rotation habituelle sur assez d'envois avant de conclure."),
     "autres": "Niveau 0 : tourne les contenus au hasard. Niveau 1 : ne propose plus que le best-seller du mois dernier.",
     "copie": "L'algorithme est public ; ce qu'il apprend de tes fans ne l'est pas.",
     "verifier": "Sur plusieurs milliers d'envois, plus d'achats par envoi qu'avec la rotation."},
    {"id": "garder", "titre": "Garder les créatrices",
     "phrase": "La taille fait le premier centile ; les créatrices font la taille.",
     "pourquoi": "Dans l'arène, aucune stratégie ne mène une agence de taille moyenne au premier centile en trois ans : "
                 "la taille de départ pèse plus que la tactique. La prise la plus basse capte le plus de créatrices, "
                 "un coup d'avance gagne le plus (rang médian {{rang_med_2}} contre {{rang_med_1}} pour la mode). "
                 "Mieux payer fait rester (Raff et Summers).",
     "preuves": (), "refs": ("raff1987",),
     "etapes": ("Montrer à chaque créatrice, chaque mois, ce que l'agence a rapporté en plus (le témoin le prouve).",
                "Une part juste, écrite, revue chaque année.",
                "Mesurer les départs de créatrices chaque mois ; chaque départ a sa raison notée."),
     "autres": "Niveau 0 et 1 : 50 % de prise, résultats affirmés sans preuve.",
     "copie": "Une prise plus basse se copie ; une preuve de résultat par témoin, non.",
     "verifier": "Moins d'une créatrice sur trente qui part chaque mois."},
    {"id": "foule", "titre": "Ne pas courir après la foule ni après le premier rang",
     "phrase": "Être premier ou être là où personne n'est ne suffit pas : ce qui gagne, c'est être bon assez tôt.",
     "pourquoi": "Sur Kickstarter, sortir la même semaine que sa catégorie n'est pas établi comme coûteux (K01). Les "
                 "premières campagnes d'un pays qui ouvre réussissent moins ({{k03_d}} points), mais un faux jour "
                 "d'ouverture donne presque le même écart ({{k03_placebo}}) : ce n'est pas l'effet d'être premier "
                 "(K03). Près de la moitié des pionniers échouent (Golder et Tellis), et une astuce publiée perd "
                 "58 % de son effet (McLean et Pontiff).",
     "preuves": ("K01", "K03"), "refs": ("golder1993", "mclean2016"),
     "etapes": ("Se méfier d'une astuce vendue dans une formation : si elle est publiée, elle s'use.",
                "Arriver tôt sur une plateforme ou une niche, mais avec la méthode des phases 1 à 4.",
                "Tester chez soi les créneaux d'envoi au lieu de suivre ou de fuir la foule."),
     "autres": "Niveau 0 : copie la dernière astuce virale. Niveau 1 : fuit les créneaux encombrés sans preuve.",
     "copie": "Ne pas suivre la mode ne s'use pas : c'est la méthode, pas le truc.",
     "verifier": "Chaque nouvelle astuce passe par un groupe témoin avant d'être généralisée."},
    {"id": "grandir", "titre": "Grandir, mois après mois",
     "phrase": "Chaque mois : ce qui a été prouvé, ce qui a été abandonné, ce qui reste à tester.",
     "pourquoi": "Un petit avantage répété souvent fait beaucoup ; un gros pari isolé est une loterie. Dans l'arène, "
                 "un coup d'avance finit devant la mode dans {{arene_21}} des tirages, devant le guide dans "
                 "{{arene_20}} : pas toujours. Ce qu'il coûte (témoin, part plus juste, franchise) doit rester "
                 "petit devant ce qu'il rapporte.",
     "preuves": (), "refs": ("koning2022",),
     "etapes": ("Le registre des tests de l'agence, comme celui de ce cahier : écrit avant, jugé après.",
                "Un bilan mensuel : écarts mesurés, intervalle, décision.",
                "Garder le témoin petit (10 %) et la franchise peu coûteuse ; surveiller les deux."),
     "autres": "Niveau 3 : teste tout, tout le temps, et oublie de vendre (finit derrière un coup d'avance dans "
               "{{arene_23}} des tirages).",
     "copie": "L'avance n'est pas une astuce : c'est la vitesse à laquelle l'agence apprend.",
     "verifier": "Six mois de bilans, au moins trois décisions prises sur un écart prouvé."},
)

#: Les modules et leçons de la formation (même découpage que les parcours de Lueur).
MODULES = (
    {"id": "marche", "titre": "Comprendre le marché", "lecons": (
        {"id": "argent", "titre": "Où va l'argent",
         "lead": "Sur 100 $ payés par un fan, la plateforme en garde 20 ; le reste se partage entre la créatrice, "
                 "le chat et l'agence.",
         "kid": "Le gâteau est coupé avant que l'agence ne mange : il faut savoir qui prend quelle part.",
         "faits": ("Les fans ont payé {{brut}} sur l'année 2024 (+{{croiss_brut}}).",
                   "Il y a {{fans_par}} comptes de fans pour une créatrice, et {{par_creatrice}} par créatrice en "
                   "moyenne sur l'année, avant la part de la plateforme.",
                   "Les comptes de créateurs montent plus vite (+{{croiss_crea}}) que l'argent payé : chaque créatrice "
                   "a une plus petite part."),
         "faire": ("Calcule, pour une créatrice, la part de chacun sur 100 $.",),
         "eviter": ("Croire un chiffre de « statistiques » sans source : la plupart se recopient entre elles.",),
         "quiz": ("Sur 100 $ payés par un fan, combien la plateforme garde-t-elle ?", ("20 $", "50 $", "5 $"), 0,
                  "La plateforme prend 20 % ; le partage entre créatrice et agence se fait sur les 80 $ restants.")},
        {"id": "inconnu", "titre": "Ce qu'on ne sait pas",
         "lead": "Personne ne publie les ventes des créatrices : toute étude d'OnlyFans passe par des marchés voisins.",
         "kid": "On ne peut pas regarder dans la tirelire des autres ; on regarde des tirelires qui leur ressemblent.",
         "faits": ("Le chiffre « le premier centile prend un tiers » vient d'une seule analyse de 2020 : il n'est pas repris.",
                   "Ce cahier teste sur des expériences tirées au sort dans le commerce en ligne, et le dit."),
         "faire": ("Garder tes propres chiffres (Lueur Sync) : ce sont les seuls vrais pour toi.",),
         "eviter": ("Transposer un chiffre d'un autre marché sans le vérifier chez toi.",),
         "quiz": ("Pourquoi tester sur des marchés voisins ?", ("Les données d'OnlyFans ne sont pas publiques",
                  "Ils sont plus faciles", "Ils donnent de meilleurs chiffres"), 0,
                  "Aucune donnée de vente d'OnlyFans n'est publique : on teste ailleurs et on revérifie chez soi.")},
    )},
    {"id": "avance", "titre": "Penser à un coup d'avance", "lecons": (
        {"id": "niveaux", "titre": "Les niveaux",
         "lead": "La plupart des gens pensent à un coup d'avance, presque personne à plus de trois : il faut un coup "
                 "d'avance sur les vrais concurrents, pas sur des génies.",
         "kid": "Si tous tes amis font la même chose, fais un pas de côté ; mais pas dix, sinon tu es seul.",
         "faits": ("En moyenne, les gens raisonnent à environ {{tau}} coups d'avance (Camerer, Ho et Chong).",
                   "Dans l'arène, « trop d'avance » finit derrière « un coup d'avance » dans {{arene_23}} des tirages."),
         "faire": ("Écris ce que fait le guide (niveau 0), ce que fait la mode (niveau 1), et fais un pas de plus.",),
         "eviter": ("Viser la stratégie « parfaite » : elle suppose des concurrents qui n'existent pas.",),
         "quiz": ("Combien de coups d'avance faut-il viser ?", ("Un de plus que la foule", "Le plus possible", "Aucun"), 0,
                  "La foule pense à un ou deux coups : en penser un de plus suffit, plus coûte sans rapporter.")},
        {"id": "usure", "titre": "Un truc publié s'use",
         "lead": "Quand une astuce est connue de tous, ses fans y sont habitués : son effet baisse.",
         "kid": "Le coin à champignons que tout le monde connaît est vide le matin.",
         "faits": ("En bourse, un signal publié perd 58 % de son gain après sa publication (McLean et Pontiff).",
                   "Une méthode (apprendre chez soi) ne s'use pas de la même façon : dans l'arène, son avance reste la "
                   "même que 10 % ou 90 % des concurrents la copient ({{copie_10}}, {{copie_90}})."),
         "faire": ("Pour chaque astuce de formation, demande : est-elle publiée ? Alors elle s'use.",),
         "eviter": ("Payer une formation pour une liste d'astuces : la liste est déjà dans le prix.",),
         "quiz": ("Qu'est-ce qui s'use quand tout le monde le fait ?", ("Une astuce", "Apprendre sur ses propres fans",
                  "Les règles de droit"), 0, "Une astuce s'use ; ce que tu apprends de tes fans reste à toi.")},
        {"id": "premier", "titre": "Le premier n'est pas le gagnant",
         "lead": "Arriver premier sur un marché neuf n'est pas une avance prouvée ; arriver tôt et bon, si.",
         "kid": "Le premier qui court n'est pas toujours celui qui gagne la course.",
         "faits": ("Près de la moitié des pionniers échouent (Golder et Tellis).",
                   "Sur Kickstarter, l'écart des pionniers ({{k03_d}} points) se retrouve avec un faux jour d'ouverture "
                   "({{k03_placebo}}) : ce n'est pas l'effet d'être premier (K03)."),
         "faire": ("Avant de te lancer sur une nouvelle plateforme, prépare la méthode (témoins, ciblage) qui y marchera.",),
         "eviter": ("Te ruer sur une niche « parce que personne n'y est encore ».",),
         "quiz": ("Qu'a montré le faux jour d'ouverture ?", ("Que l'écart n'était pas dû au fait d'être premier",
                  "Que les pionniers gagnent", "Rien"), 0,
                  "Le même écart apparaît sans aucune ouverture : il vient d'autre chose.")},
    )},
    {"id": "preuve", "titre": "Prouver avant d'agir", "lecons": (
        {"id": "temoin", "titre": "Le groupe témoin",
         "lead": "Le seul moyen de savoir ce qu'un message rapporte : ne pas l'envoyer à un groupe tiré au sort.",
         "kid": "Pour savoir si l'engrais fait pousser, on laisse une plante sans engrais.",
         "faits": ("Sur des données simulées où la vérité est connue, notre chaîne ne conclut à tort que {{etal_a_nul}} "
                   "fois sur 100, et son intervalle contient le vrai gain {{etal_couv}} fois sur 100.",),
         "faire": ("10 % de témoin tiré au sort sur chaque campagne.",),
         "eviter": ("Choisir le témoin à la main (« ceux qui n'ont pas ouvert ») : il ne ressemble plus aux autres.",),
         "quiz": ("Comment choisir le groupe témoin ?", ("Au hasard", "Les fans inactifs", "Les nouveaux fans"), 0,
                  "Seul le hasard fait deux groupes semblables en tout, sauf le message.")},
        {"id": "placebo", "titre": "Le placebo",
         "lead": "On mesure un effet impossible : s'il apparaît, c'est la mesure qui ment.",
         "kid": "On vérifie que la balance affiche zéro quand il n'y a rien dessus.",
         "faits": ("Sur Lenta, le message « fait changer » le sexe des clients : impossible. Le tirage au sort n'était "
                   "pas équilibré (z = {{lenta_z_sexe}} sur le sexe, {{lenta_z_rep}} sur la réponse passée aux SMS).",),
         "faire": ("Avant de lire un résultat, compare les deux groupes sur ce qu'ils étaient avant.",),
         "eviter": ("Croire un gain sans avoir vérifié que les groupes se ressemblaient au départ.",),
         "quiz": ("À quoi sert un placebo ?", ("Vérifier que la mesure ne ment pas", "Augmenter les ventes",
                  "Remplacer le témoin"), 0, "Un effet sur une chose que le message ne peut pas changer trahit un défaut.")},
        {"id": "famille", "titre": "Beaucoup de tests, un seuil plus haut",
         "lead": "Sur 25 idées testées, une ou deux « marchent » par pure chance : on relève le seuil pour toutes.",
         "kid": "Si tu lances la pièce cent fois, tu auras des séries de faces sans aucun truc.",
         "faits": ("Sans correction, 25 tests nuls donnent au moins une fausse alerte {{etal_holm_brut}} du temps ; avec "
                   "la correction de Holm, {{etal_holm}}.",),
         "faire": ("Compte tes tests ; plus tu en fais, plus il faut un écart net.",),
         "eviter": ("Garder la meilleure de dix idées sans la retester.",),
         "quiz": ("Tu testes 25 idées et une passe tout juste. Que fais-tu ?", ("Je la reteste", "Je la généralise",
                  "Je l'oublie"), 0, "Une idée sur 25 passe par chance : on la reteste sur de nouveaux fans.")},
        {"id": "reglage", "titre": "Le meilleur réglage n'est pas une preuve",
         "lead": "Choisir le meilleur de 36 réglages sur des données, puis le juger sur les mêmes données, c'est se mentir.",
         "kid": "Celui qui gagne à l'entraînement doit aussi gagner au match.",
         "faits": ("Le test SPA (Hansen) et le CSCV (Bailey et al.) disent si le réglage choisi gagne encore sur des "
                   "données qu'il n'a pas vues.", "Nos outils rendent les mêmes chiffres que les bibliothèques de "
                   "référence des quants (statsmodels, arch, scipy)."),
         "faire": ("Choisis tes réglages sur un mois, juge-les sur le suivant.",),
         "eviter": ("Annoncer « +40 % » sur le meilleur des réglages essayés.",),
         "quiz": ("Où juger un réglage choisi ?", ("Sur des données qu'il n'a pas vues", "Sur les mêmes données",
                  "Nulle part"), 0, "Seules des données neuves disent si le réglage était bon ou chanceux.")},
    )},
    {"id": "avances", "titre": "Les avances qui tiennent", "lecons": (
        {"id": "cibler", "titre": "Écrire à qui le message change",
         "lead": "Le message rapporte chez ceux qu'il fait acheter, pas chez ceux qui achèteraient de toute façon.",
         "kid": "Donner un bonbon à celui qui en a plein ne le rend pas plus content.",
         "faits": ("Sur X5 : {{x5_appris}} achats pour 100 clients avec la liste apprise, {{x5_hasard}} au hasard, "
                   "{{x5_valeur}} avec les gros dépensiers (A03, A09, A12).",),
         "faire": ("Classe tes fans par effet du message mesuré sur tes témoins.",),
         "eviter": ("Réserver les relances aux meilleurs fans sans preuve qu'elles changent quelque chose chez eux.",),
         "quiz": ("Sur X5, la règle des gros dépensiers fait…", ("pire que le hasard", "mieux que tout", "comme la liste apprise"),
                  0, "Les gros dépensiers achètent de toute façon : leur écrire en premier gaspille les messages.")},
        {"id": "accelere", "titre": "Les fans qui accélèrent",
         "lead": "Le fan dont les achats se rapprochent est en train de s'attacher : c'est le signal qui passe toute la batterie.",
         "kid": "L'ami qui vient de plus en plus souvent va devenir ton meilleur ami.",
         "faits": ("Effet au-delà de RFM : {{r03_ic}} sur X5, {{r01_ic}} sur CDNOW, {{r02_ic}} sur Online Retail II.",
                   "Sur X5, il passe chacun des tests qui s'appliquent à lui (R03)."),
         "faire": ("Chaque lundi, la liste des fans qui accélèrent, aux chatteurs.",),
         "eviter": ("Croire que le signal est gros : il est petit, il sert parce qu'il sert souvent.",),
         "quiz": ("Que mesure l'accélération ?", ("Des achats qui se rapprochent", "Une grosse dépense", "Un nouveau fan"),
                  0, "Ce n'est pas combien le fan dépense, c'est le rythme de ses retours.")},
        {"id": "bandit", "titre": "Apprendre en gagnant",
         "lead": "Proposer surtout ce qui vend, en continuant d'essayer le reste : on gagne pendant qu'on apprend.",
         "kid": "On joue plus souvent au jeu qui fait gagner, sans arrêter d'essayer les autres.",
         "faits": ("Jeu complet de ZOZOTOWN : {{obp_th}} de clics contre {{obp_ha}} au hasard.",
                   "Échantillon public : écart de {{b04_d}} point, pas établi (trop peu d'impressions)."),
         "faire": ("Compte envois et achats par contenu ; propose le plus souvent ceux qui vendent.",),
         "eviter": ("Ne plus jamais essayer un contenu parce qu'il a raté une fois.",),
         "quiz": ("Pourquoi l'échantillon public ne tranche-t-il pas ?", ("Trop peu d'impressions", "Le bandit ne marche pas",
                  "Les clics sont faux"), 0, "L'article trouve l'avantage sur 26 millions d'impressions ; l'échantillon "
                                             "en a 60 000.")},
    )},
    {"id": "arene", "titre": "Ce que l'arène enseigne", "lecons": (
        {"id": "copient", "titre": "Quand les autres copient",
         "lead": "Une méthode qui apprend sur tes propres fans ne s'use pas quand les autres la copient ; ce qui peut "
                 "la faire perdre, c'est son coût.",
         "kid": "Si tout le monde a un jardin, ton jardin pousse quand même.",
         "faits": ("Un coup d'avance bat la mode dans {{copie_10}} des tirages à 10 % d'imitateurs et {{copie_90}} à 90 % : "
                   "pas d'usure, mais pas 90 %.", "Il perd quand la franchise ou le témoin coûtent cher, ou quand "
                   "apprendre demande beaucoup de fans."),
         "faire": ("Garde le témoin petit et surveille ce que coûte la franchise.",),
         "eviter": ("Croire qu'une bonne méthode gagne toujours : elle gagne souvent.",),
         "quiz": ("Qu'est-ce qui fait perdre un coup d'avance dans l'arène ?", ("Son coût", "Les imitateurs", "La chance seule"),
                  0, "Son avance ne s'use pas avec les imitateurs ; elle se perd quand elle coûte trop.")},
        {"id": "part", "titre": "La part ou le profit",
         "lead": "La prise la plus basse capte le plus de créatrices ; un coup d'avance gagne le plus. Et la taille de "
                 "départ décide du premier centile.",
         "kid": "Le plus gros panier n'est pas toujours le plus lourd en pièces d'or.",
         "faits": ("Rang médian : {{rang_med_2}} pour un coup d'avance, {{rang_med_1}} pour la mode, {{rang_med_3}} pour "
                   "trop d'avance.", "Aucune stratégie ne mène une agence moyenne au premier centile en 36 mois."),
         "faire": ("Grandis en créatrices, avec une preuve de résultat à leur montrer.",),
         "eviter": ("Baisser sa prise sans fin pour attirer : on grandit et on gagne moins.",),
         "quiz": ("Qu'est-ce qui décide du premier centile dans l'arène ?", ("La taille", "La tactique seule", "La chance seule"),
                  0, "La tactique fait monter le rang ; la taille fait le premier centile.")},
    )},
    {"id": "regles", "titre": "Les règles", "lecons": (
        {"id": "ia", "titre": "L'IA doit se présenter",
         "lead": "Depuis le 2 août 2026, une IA qui parle seule à un fan doit dire qu'elle est une IA.",
         "kid": "Un robot doit dire qu'il est un robot.",
         "faits": ("Annoncée avant la conversation, une IA fait baisser les achats de plus de {{divulgation}} "
                   "(Luo et al.).", "Amende possible : 15 millions d'euros ou 3 % du chiffre d'affaires mondial."),
         "faire": ("L'IA aide les chatteurs (brouillons) ; si elle converse seule, elle s'annonce.",),
         "eviter": ("Un robot non annoncé : il vend bien jusqu'au contrôle, puis tout tombe.",),
         "quiz": ("Une IA qui converse seule avec un fan doit…", ("dire qu'elle est une IA", "se taire", "imiter la créatrice"),
                  0, "C'est l'article 50 de l'AI Act, en vigueur depuis le 2 août 2026.")},
        {"id": "franchise", "titre": "Ne jamais se faire passer pour elle",
         "lead": "Le chat dit qui écrit : l'équipe de la créatrice. Faire croire le contraire est visé par la justice.",
         "kid": "On ne ment pas sur qui parle.",
         "faits": ("Une action de groupe vise OnlyFans et neuf agences pour des chatteurs qui jouaient la créatrice.",
                   "C'est aussi la règle de la maison de ce cahier : aucune tactique qui repose sur ce mensonge."),
         "faire": ("Présenter l'équipe ; garder des messages écrits par la créatrice elle-même.",),
         "eviter": ("« Je suis [prénom] » écrit par quelqu'un d'autre.",),
         "quiz": ("Qui écrit dans le chat ?", ("L'équipe, présentée comme telle", "Un chatteur qui joue la créatrice",
                  "Un robot anonyme"), 0, "Le mensonge sur l'identité expose l'agence et la créatrice.")},
    )},
)


def lecons():
    for m in MODULES:
        for l in m["lecons"]:
            yield m, l
