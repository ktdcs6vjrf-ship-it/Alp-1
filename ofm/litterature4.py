"""Les sources du cahier nº 4 : le marché, la concurrence, les méthodes, et ce que d'autres ont établi.

Recherchées et recoupées le 25 novembre 2026. Les nombres de `MARCHE` et
d'`AILLEURS` sont **cités**, pas calculés : ils appartiennent à leurs sources,
et la page le dit à côté de chacun. Quand un chiffre n'a été retrouvé que dans
une source secondaire, la note le dit ; quand il n'a pas pu être relu (la part
du premier centile des créatrices, « 33 % », venue d'une seule analyse
indépendante de 2020), il n'est pas repris.
"""

from __future__ import annotations

import html as H

REFS = {
    # --- Le marché ---------------------------------------------------------------
    "fenix2025": {"auteurs": "Fenix International Ltd", "court": "Fenix International", "annee": "2025",
                  "titre": "Comptes annuels de l'exercice clos le 30 novembre 2024 (OnlyFans)",
                  "revue": "Companies House (Royaume-Uni), repris par Fortune, Euronews et Business Insider"},
    "ft2026": {"auteurs": "Financial Times", "court": "Financial Times", "annee": "2026",
               "titre": "Comptes de l'exercice clos en novembre 2025 de Fenix International",
               "revue": "article repris par plusieurs titres (août 2026) ; chiffres non relus dans le dépôt officiel"},
    "nzfenix2024": {"auteurs": "N.Z. et al. c. Fenix International Ltd et al.", "court": "N.Z. c. Fenix", "annee": "2024",
                    "titre": "Action de groupe sur les « chatteurs » qui se font passer pour les créatrices",
                    "revue": "Cour fédérale du district central de Californie, nº 8:24-cv-01655, déposée le 29 juillet 2024"},
    "ue2024ai": {"auteurs": "Parlement européen et Conseil", "court": "AI Act, art. 50", "annee": "2024",
                 "titre": "Règlement (UE) 2024/1689 sur l'intelligence artificielle, article 50 (transparence)",
                 "revue": "Journal officiel de l'UE ; l'article 50(1) s'applique depuis le 2 août 2026"},
    "mastercard2021": {"auteurs": "Mastercard", "court": "Mastercard", "annee": "2021",
                       "titre": "Règles sur les contenus pour adultes (vérification de l'âge et du consentement)",
                       "revue": "annoncées en avril 2021, en vigueur le 15 octobre 2021"},
    "senat2026": {"auteurs": "Sénat", "court": "Sénat", "annee": "2026",
                  "titre": "Proposition de loi visant à lutter contre le proxénétisme et l'exploitation sexuelle en ligne",
                  "revue": "adoptée en première lecture le 10 février 2026, transmise à l'Assemblée nationale"},
    "cunningham2011": {"auteurs": "Cunningham, S. et Kendall, T. D.", "court": "Cunningham et Kendall", "annee": "2011",
                       "titre": "Prostitution 2.0: the changing face of sex work",
                       "revue": "Journal of Urban Economics 69(3), 273–287"},
    "cunningham2024": {"auteurs": "Cunningham, S., DeAngelo, G. et Tripp, J.", "court": "Cunningham et al.", "annee": "2024",
                       "titre": "Did Craigslist's erotic services reduce female homicide and rape?",
                       "revue": "Journal of Human Resources 59(1), 280–315"},
    # --- La concurrence --------------------------------------------------------------
    "nagel1995": {"auteurs": "Nagel, R.", "court": "Nagel", "annee": "1995",
                  "titre": "Unraveling in guessing games: an experimental study",
                  "revue": "American Economic Review 85(5), 1313–1326"},
    "camerer2004": {"auteurs": "Camerer, C. F., Ho, T.-H. et Chong, J.-K.", "court": "Camerer et al.", "annee": "2004",
                    "titre": "A cognitive hierarchy model of games",
                    "revue": "Quarterly Journal of Economics 119(3), 861–898"},
    "mclean2016": {"auteurs": "McLean, R. D. et Pontiff, J.", "court": "McLean et Pontiff", "annee": "2016",
                   "titre": "Does academic research destroy stock return predictability?",
                   "revue": "Journal of Finance 71(1), 5–32"},
    "golder1993": {"auteurs": "Golder, P. N. et Tellis, G. J.", "court": "Golder et Tellis", "annee": "1993",
                   "titre": "Pioneer advantage: marketing logic or marketing legend?",
                   "revue": "Journal of Marketing Research 30(2), 158–170"},
    "salganik2006": {"auteurs": "Salganik, M. J., Dodds, P. S. et Watts, D. J.", "court": "Salganik et al.", "annee": "2006",
                     "titre": "Experimental study of inequality and unpredictability in an artificial cultural market",
                     "revue": "Science 311(5762), 854–856"},
    "raff1987": {"auteurs": "Raff, D. M. G. et Summers, L. H.", "court": "Raff et Summers", "annee": "1987",
                 "titre": "Did Henry Ford pay efficiency wages?", "revue": "Journal of Labor Economics 5(4), S57–S86"},
    # --- Les avances ------------------------------------------------------------------
    "koning2022": {"auteurs": "Koning, R., Hasan, S. et Chatterji, A.", "court": "Koning et al.", "annee": "2022",
                   "titre": "Experimentation and start-up performance: evidence from A/B testing",
                   "revue": "Management Science 68(9), 6434–6453"},
    "schwartz2017": {"auteurs": "Schwartz, E. M., Bradlow, E. T. et Fader, P. S.", "court": "Schwartz et al.", "annee": "2017",
                     "titre": "Customer acquisition via display advertising using multi-armed bandit experiments",
                     "revue": "Marketing Science 36(4), 500–522"},
    "saito2021": {"auteurs": "Saito, Y., Aihara, S., Matsutani, M. et Narita, Y.", "court": "Saito et al.", "annee": "2021",
                  "titre": "Open Bandit Dataset and Pipeline: towards realistic and reproducible off-policy evaluation",
                  "revue": "arXiv 2008.07146 ; jeu public du dépôt st-tech/zr-obp, commit 8cbd5fa"},
    "luo2019": {"auteurs": "Luo, X., Tong, S., Fang, Z. et Qu, Z.", "court": "Luo et al.", "annee": "2019",
                "titre": "Frontiers: machines vs. humans: the impact of artificial intelligence chatbot disclosure on "
                         "customer purchases", "revue": "Marketing Science 38(6), 937–947"},
    "ascarza2018": {"auteurs": "Ascarza, E.", "court": "Ascarza", "annee": "2018",
                    "titre": "Retention futility: targeting high-risk customers might be ineffective",
                    "revue": "Journal of Marketing Research 55(1), 80–98"},
    "wang2022": {"auteurs": "Wang, Y., Lu, M. et Shi, C.", "court": "Wang et al.", "annee": "2022",
                 "titre": "Does customer email engagement improve profitability? Evidence from a field experiment in "
                          "subscription service retailing",
                 "revue": "Manufacturing & Service Operations Management 24(5), 2703–2721"},
    "damgaard2018": {"auteurs": "Damgaard, M. T. et Gravert, C.", "court": "Damgaard et Gravert", "annee": "2018",
                     "titre": "The hidden costs of nudging: experimental evidence from reminders in fundraising",
                     "revue": "Journal of Public Economics 157, 15–26"},
    # --- Les jeux de données (relus des nº 2 et 3) ------------------------------------
    "hillstrom2008": {"auteurs": "Hillstrom, K.", "court": "Hillstrom", "annee": "2008",
                      "titre": "The MineThatData e-mail analytics and data mining challenge",
                      "revue": "jeu de 64 000 clients, courriel tiré au sort"},
    "lenta2020": {"auteurs": "Lenta et scikit-uplift", "court": "Lenta", "annee": "2020",
                  "titre": "Lenta uplift dataset", "revue": "687 029 clients, SMS tiré au sort"},
    "x52019": {"auteurs": "X5 Retail Group", "court": "X5 RetailHero", "annee": "2019",
               "titre": "RetailHero : expérience SMS et achats", "revue": "concours ODS (copie de scikit-uplift)"},
    "kickstarter2018": {"auteurs": "Kickstarter (relevé public)", "court": "Kickstarter", "annee": "2018",
                        "titre": "Campagnes de financement participatif 2009–2018",
                        "revue": "copie GitHub figée (cahier nº 2)"},
    "fader2005": {"auteurs": "Fader, P. S., Hardie, B. G. S. et Lee, K. L.", "court": "Fader et al.", "annee": "2005",
                  "titre": "RFM and CLV: using iso-value curves for customer base analysis",
                  "revue": "Journal of Marketing Research 42(4), 415–430 ; jeu CDNOW"},
    "chen2019": {"auteurs": "Chen, D.", "court": "Chen", "annee": "2019",
                 "titre": "Online Retail II", "revue": "UCI Machine Learning Repository (copie GitHub)"},
    # --- Les méthodes -------------------------------------------------------------------
    "white2000": {"auteurs": "White, H.", "court": "White", "annee": "2000",
                  "titre": "A reality check for data snooping", "revue": "Econometrica 68(5), 1097–1126"},
    "hansen2005": {"auteurs": "Hansen, P. R.", "court": "Hansen", "annee": "2005",
                   "titre": "A test for superior predictive ability",
                   "revue": "Journal of Business & Economic Statistics 23(4), 365–380"},
    "bailey2017": {"auteurs": "Bailey, D. H., Borwein, J. M., López de Prado, M. et Zhu, Q. J.", "court": "Bailey et al.",
                   "annee": "2017", "titre": "The probability of backtest overfitting",
                   "revue": "Journal of Computational Finance 20(4), 39–69"},
    "bailey2014": {"auteurs": "Bailey, D. H. et López de Prado, M.", "court": "Bailey et López de Prado", "annee": "2014",
                   "titre": "The deflated Sharpe ratio: correcting for selection bias, backtest overfitting and "
                            "non-normality", "revue": "Journal of Portfolio Management 40(5), 94–107"},
    "harvey2016": {"auteurs": "Harvey, C. R., Liu, Y. et Zhu, H.", "court": "Harvey et al.", "annee": "2016",
                   "titre": "… and the cross-section of expected returns",
                   "revue": "Review of Financial Studies 29(1), 5–68"},
    "holm1979": {"auteurs": "Holm, S.", "court": "Holm", "annee": "1979",
                 "titre": "A simple sequentially rejective multiple test procedure",
                 "revue": "Scandinavian Journal of Statistics 6(2), 65–70"},
    "simonsohn2020": {"auteurs": "Simonsohn, U., Simmons, J. P. et Nelson, L. D.", "court": "Simonsohn et al.",
                      "annee": "2020", "titre": "Specification curve analysis",
                      "revue": "Nature Human Behaviour 4, 1208–1214"},
    "mckay1979": {"auteurs": "McKay, M. D., Beckman, R. J. et Conover, W. J.", "court": "McKay et al.", "annee": "1979",
                  "titre": "A comparison of three methods for selecting values of input variables in the analysis of "
                           "output from a computer code", "revue": "Technometrics 21(2), 239–245"},
    "bh1995": {"auteurs": "Benjamini, Y. et Hochberg, Y.", "court": "Benjamini et Hochberg", "annee": "1995",
               "titre": "Controlling the false discovery rate: a practical and powerful approach to multiple testing",
               "revue": "Journal of the Royal Statistical Society B 57(1), 289–300"},
    "phipson2010": {"auteurs": "Phipson, B. et Smyth, G. K.", "court": "Phipson et Smyth", "annee": "2010",
                    "titre": "Permutation p-values should never be zero",
                    "revue": "Statistical Applications in Genetics and Molecular Biology 9(1), article 39"},
}

#: Les nombres cités dont les graphiques se servent (un seul endroit ; leurs sources sont dans `MARCHE`).
CHIFFRES = {
    "brut_2024": 7.22e9, "croissance_brut": 0.09, "net_2024": 1.41e9,
    "createurs_2024": 4.634e6, "croissance_createurs": 0.13,
    "fans_2024": 377.5e6, "croissance_fans": 0.24, "part_plateforme": 0.20,
    # Open Bandit Dataset, jeu complet, campagne « tous les articles » (Saito et al., tableau du jeu).
    "obp_thompson": 0.0050, "obp_hasard": 0.0035,
    # Camerer, Ho et Chong (2004) : coups d'avance moyens.
    "tau": 1.5,
    # Luo et al. (2019) : baisse des achats quand l'IA s'annonce avant la conversation.
    "divulgation": 0.797,
}

#: Le marché, en chiffres cités (pas calculés).
MARCHE = (
    {"titre": "Ce que les fans paient", "ref": "fenix2025", "chiffre": "7,22 Md$",
     "constat": "Les fans ont payé 7,22 milliards de dollars aux créateurs d'OnlyFans sur l'exercice clos fin novembre "
                "2024 (+9 %) ; la plateforme en garde 20 %, soit 1,41 milliard de chiffre d'affaires.",
     "preuve": "comptes déposés au registre britannique, repris par la presse économique."},
    {"titre": "Combien de créateurs", "ref": "fenix2025", "chiffre": "4,63 M",
     "constat": "4,63 millions de comptes de créateurs (+13 %) et 377,5 millions de comptes de fans (+24 %) : il y a "
                "de plus en plus de vendeuses pour chaque fan.",
     "preuve": "mêmes comptes ; un compte n'est pas une personne active."},
    {"titre": "L'année suivante", "ref": "ft2026", "chiffre": "1,6 Md$",
     "constat": "Sur l'exercice clos fin novembre 2025, le chiffre d'affaires de la plateforme aurait monté de 10 % "
                "(environ 1,6 milliard de dollars), son bénéfice avant impôt de 5 %.",
     "preuve": "article du Financial Times repris par d'autres titres ; non relu dans le dépôt officiel."},
    {"titre": "Ce qu'on ne sait pas", "ref": None, "chiffre": "—",
     "constat": "Aucune étude publiée ne mesure la part du revenu tenue par les meilleures créatrices. Le chiffre qui "
                "circule (« le premier centile prend un tiers ») vient d'une seule analyse indépendante de 2020 : il "
                "n'est pas repris.",
     "preuve": "recherche du 25 novembre 2026 ; les pages de « statistiques » se recopient entre elles."},
    {"titre": "Internet a déplacé le marché du sexe", "ref": "cunningham2011", "chiffre": "en ligne",
     "constat": "La sollicitation est passée de la rue à l'écran : Internet baisse le coût de recherche des clients, "
                "et l'offre en ligne s'accompagne d'un recul de la prostitution de rue.",
     "preuve": "données américaines 1999–2008, économétrie."},
    {"titre": "Et l'a rendu plus sûr", "ref": "cunningham2024", "chiffre": "−12 à −18 %",
     "constat": "L'ouverture, ville par ville, des annonces érotiques de Craigslist a fait baisser les homicides de "
                "femmes de 12 à 18 %.",
     "preuve": "déploiement échelonné du service, 2002–2010."},
    {"titre": "Le robinet des paiements", "ref": "mastercard2021", "chiffre": "1 semaine",
     "constat": "Après les nouvelles règles de Mastercard (âge et consentement vérifiés pour tout contenu adulte), "
                "OnlyFans a annoncé en août 2021 l'interdiction des contenus explicites, puis l'a retirée une semaine "
                "plus tard.",
     "preuve": "communiqués et presse ; le rôle exact des banques reste discuté."},
    {"titre": "Les chatteurs devant le juge", "ref": "nzfenix2024", "chiffre": "9 agences",
     "constat": "Une action de groupe américaine accuse OnlyFans et neuf agences d'avoir fait croire aux fans qu'ils "
                "parlaient aux créatrices ; une seconde a suivi en 2025. Aucune décision sur le fond à ce jour.",
     "preuve": "plainte déposée le 29 juillet 2024 ; dossier en cours."},
    {"titre": "L'IA doit se présenter", "ref": "ue2024ai", "chiffre": "2 août 2026",
     "constat": "Depuis le 2 août 2026, une personne qui parle à une IA doit le savoir (article 50, paragraphe 1, de "
                "l'AI Act) ; le report décidé fin 2026 ne touche pas ce paragraphe. Amende possible : 15 millions "
                "d'euros ou 3 % du chiffre d'affaires mondial.",
     "preuve": "texte du règlement et analyses de cabinets d'avocats (août 2026)."},
    {"titre": "Et en France", "ref": "senat2026", "chiffre": "en navette",
     "constat": "Le Sénat a adopté le 10 février 2026 une proposition contre le proxénétisme en ligne qui vise les "
                "plateformes comme OnlyFans ; l'Assemblée ne l'a pas encore examinée, et la « loi intégrale » votée "
                "en octobre 2026 a finalement épargné ces plateformes.",
     "preuve": "dossiers législatifs et presse parlementaire ; à revérifier avant toute décision."},
)

#: Ce que d'autres ont établi, que ce cahier ne pouvait pas rejouer.
AILLEURS = (
    {"titre": "Combien de coups d'avance", "ref": "camerer2004",
     "constat": "Sur une centaine de jeux, les gens raisonnent en moyenne à environ 1,5 coup d'avance : beaucoup "
                "ne pensent pas plus loin qu'un coup, très peu au-delà de trois.",
     "preuve": "modèle à une seule valeur (loi de Poisson) ajusté sur des expériences de laboratoire.",
     "enfant": "Presque tout le monde regarde ce que font les autres ; presque personne ne regarde ce que les autres "
               "vont faire de ce qu'il fait."},
    {"titre": "Le concours de beauté", "ref": "nagel1995",
     "constat": "Quand il faut deviner les deux tiers de la moyenne des autres, personne ne joue zéro (la réponse "
                "« parfaite ») : la moyenne tourne autour de 36, soit environ deux coups d'avance.",
     "preuve": "expérience de laboratoire ; ordre de grandeur repris d'une revue de la littérature.",
     "enfant": "Être trop malin, c'est aussi se tromper : il faut avoir un coup d'avance sur les vrais gens, pas "
               "sur des génies."},
    {"titre": "Un avantage publié s'use", "ref": "mclean2016",
     "constat": "Sur 97 signaux de bourse publiés, le gain baisse de 26 % hors de l'échantillon de l'article et de "
                "58 % après sa publication.",
     "preuve": "97 signaux comparés avant et après leur publication.",
     "enfant": "Quand tout le monde connaît le coin à champignons, il n'en reste plus beaucoup."},
    {"titre": "Arriver le premier ne suffit pas", "ref": "golder1993",
     "constat": "Sur environ 500 marques de 50 marchés, près de la moitié des pionniers ont échoué ; les leaders "
                "durables sont plus souvent arrivés tôt que premiers, en moyenne treize ans après le pionnier.",
     "preuve": "histoire de 50 catégories de produits, survivants et disparus compris.",
     "enfant": "Le premier qui court n'est pas toujours celui qui gagne la course."},
    {"titre": "Le succès s'emballe", "ref": "salganik2006",
     "constat": "Dans un marché de musique en ligne (14 341 participants), montrer ce que les autres écoutent a rendu "
                "le succès plus inégal et moins prévisible ; la qualité compte, mais seulement en partie.",
     "preuve": "expérience en ligne, huit « mondes » parallèles tirés au sort.",
     "enfant": "Quand tout le monde regarde ce que les autres aiment, un petit coup de chance devient une grosse "
               "différence."},
    {"titre": "Apprendre en testant", "ref": "koning2022",
     "constat": "Les jeunes entreprises qui adoptent les tests A/B voient leur performance monter de 30 à 100 % après "
                "un an : elles lancent plus, gardent ce qui marche et abandonnent plus vite ce qui ne marche pas.",
     "preuve": "des dizaines de milliers d'entreprises, choc d'outil (Google) comme expérience naturelle.",
     "enfant": "Celui qui essaie et regarde le résultat apprend plus vite que celui qui devine."},
    {"titre": "Gagner en apprenant", "ref": "schwartz2017",
     "constat": "Une banque qui répartit ses publicités par un bandit (on pousse ce qui marche en continuant d'essayer "
                "le reste) a gagné 8 % de clients de plus, sans dépenser plus, sur 750 millions d'affichages.",
     "preuve": "expérience de terrain de deux mois.",
     "enfant": "On joue plus souvent au jeu qui fait gagner, sans arrêter d'essayer les autres."},
    {"titre": "Le bandit de ZOZOTOWN, en entier", "ref": "saito2021",
     "constat": "Sur le jeu complet (26 millions d'impressions), l'échantillonnage de Thompson fait 0,50 % de clics "
                "contre 0,35 % au hasard sur tous les articles.",
     "preuve": "test A/B de sept jours ; chiffres de l'article (l'échantillon public est cent fois plus petit).",
     "enfant": "Sur beaucoup de visites, celui qui apprend gagne nettement."},
    {"titre": "L'IA qui se cache vend autant qu'un bon vendeur", "ref": "luo2019",
     "constat": "Au téléphone, un robot non annoncé vend autant qu'un vendeur expérimenté et quatre fois plus qu'un "
                "débutant ; annoncé avant la conversation, il fait baisser les achats de plus de 79,7 %.",
     "preuve": "6 200 clients tirés au sort ; l'annonce tardive atténue la perte.",
     "enfant": "Les gens achètent moins quand ils savent qu'ils parlent à une machine."},
    {"titre": "Relancer a un coût caché", "ref": "damgaard2018",
     "constat": "Un rappel fait donner davantage, mais fait aussi se désinscrire davantage ; oublier ce coût gonfle "
                "dix fois le bénéfice apparent.",
     "preuve": "expérience de terrain avec une association.",
     "enfant": "Si tu sonnes trop souvent chez quelqu'un, il finit par ne plus ouvrir."},
    {"titre": "Le deuxième courriel fatigue", "ref": "wang2022",
     "constat": "Deux courriels par mois font revenir des abonnés, mais l'effet s'use dès le deuxième et ne rapporte "
                "que chez certains : ailleurs, il coûte plus qu'il ne gagne.",
     "preuve": "expérience de terrain dans une chaîne de lavage auto par abonnement.",
     "enfant": "Un rappel aide ; trois rappels agacent."},
    {"titre": "Bien payer garde les gens", "ref": "raff1987",
     "constat": "Le salaire de cinq dollars par jour de Ford (1914), bien au-dessus du marché, a fait baisser les "
                "départs et monter la productivité et les profits.",
     "preuve": "archives de l'entreprise ; les taux de départ ne sont pas repris, faute de les avoir relus dans "
               "l'article.",
     "enfant": "Quand on est bien traité, on ne part pas chez le voisin."},
    {"titre": "Le plus à risque n'est pas le plus sensible", "ref": "ascarza2018",
     "constat": "Relancer les clients les plus susceptibles de partir rapporte moins que relancer ceux que le "
                "message fait vraiment rester.",
     "preuve": "deux expériences de terrain ; revérifié dans le cahier nº 2 et ici (famille A).",
     "enfant": "Celui qui va partir n'est pas toujours celui qu'on peut retenir."},
)


def html_ref(r: dict) -> str:
    t = H.escape(r["titre"], quote=False)
    return (f'{H.escape(r["auteurs"], quote=False)} ({r["annee"]}). {t}. '
            f'<em>{H.escape(r["revue"], quote=False)}</em>.')
