"""Le registre du cahier nº 4 — écrit avant le premier calcul de résultat.

La demande : *une avance que la concurrence n'a pas encore prise, en tenant
compte de ceux qui ont pensé comme toi, puis de ceux qui l'ont prévu, vérifiée
par tous les stress tests possibles* (`docs/ofm/demande-cahier-4.md`).

Trois idées guident le registre.

1. **Les niveaux.** Le niveau 0 suit les guides (écrire à tout le monde) ; le
   niveau 1 a vu le niveau 0 et fait mieux selon la mode (écrire d'abord aux
   gros dépensiers, relancer ceux qui décrochent) ; le niveau 2 a prévu le
   niveau 1 (apprendre sur ses propres fans, par tirage au sort, à qui un
   message change quelque chose). Une avance de niveau 2 se mesure **contre les
   règles des niveaux 0 et 1**, pas contre rien.
2. **L'usure.** Une avance qui se copie s'use (McLean et Pontiff, 2016). On
   cherche donc aussi ce qui ne se copie pas, et on mesure ce qui arrive quand
   la foule fait la même chose au même moment (famille K) ou quand elle
   s'adapte (l'arène, famille Z).
3. **La batterie.** Chaque hypothèse passe une batterie déclarée ici (`TESTS`) ;
   un test qui ne s'applique pas est « sans objet », jamais compté comme réussi.
   Une hypothèse **survit** si son verdict (Benjamini-Hochberg sur la famille du
   nº 4 seule) est « tient » et si elle réussit tous les tests qui s'y
   appliquent. Rien de cela n'est écrit à la main : tout est calculé.

Familles :

- **A — Apprendre chez soi.** Sur trois expériences tirées au sort (Hillstrom,
  Lenta, X5), une agence apprend sur une partie de sa base (le pilote) à qui le
  message change quelque chose, puis écrit au tiers de la base restante qu'elle
  a choisi. On compare ce qu'elle gagne à ce que gagnent, au même nombre de
  messages, les règles de la foule : les gros dépensiers (niveau 1), les plus à
  risque (niveau 1, Ascarza 2018), le hasard (niveau 0).
- **B — Le bandit.** ZOZOTOWN a tiré au sort, pendant sept jours, quelle
  politique choisissait les articles montrés : un échantillonnage de Thompson
  qui apprend en continu, ou le hasard uniforme (Open Bandit Dataset, Saito et
  al.). Apprendre en gagnant rapporte-t-il plus de clics ?
- **K — La foule.** Sur 330 000 campagnes Kickstarter : lancer la même semaine
  que beaucoup d'autres dans sa catégorie coûte-t-il des réussites ? Les
  premières campagnes d'un pays qui ouvre réussissent-elles mieux que les
  suivantes ?
- **W — Les baleines changent.** Sur trois marchés d'achats répétés : les
  meilleurs clients de demain sont-ils, pour plus de la moitié, d'autres que
  ceux d'aujourd'hui ?
- **R — L'accélération, revérifiée.** Le meilleur signal du nº 3 (S07–S09),
  mesuré à l'identique, puis passé à toute la batterie. Sa mesure principale
  n'apprend rien de neuf (mêmes données, même mesure) ; ce qui est neuf, ce sont
  les tests.
- **Z — L'arène.** Une simulation de 200 agences en concurrence pendant 36
  mois, de niveaux tirés selon Camerer, Ho et Chong (2004), qui s'imitent, se
  disputent les créatrices et subissent la règle européenne sur les chatbots
  (AI Act, article 50). Ses paramètres sont tirés en hypercube latin sur le
  domaine déclaré ici (`DOMAINE`) ; une affirmation de l'arène « tient » si
  elle est vraie dans la part déclarée des tirages. L'arène ne prouve rien du
  monde : elle vérifie qu'une conclusion ne dépend pas d'un réglage précis.
  Ses affirmations ne sont pas des tests statistiques et n'entrent pas dans la
  correction BH.

Décisions prises avant le calcul, en regardant la forme des fichiers et le plan
des expériences, jamais une issue :

- **Hillstrom** : traité = un courriel (hommes ou femmes) ; issue = la visite ;
  la règle des gros dépensiers lit `historique`. **Lenta** : issue = `y` ; gros
  dépensiers = `depense_12m`. **X5** : issue = `y` ; gros dépensiers =
  `depense`. Le modèle « mco » est celui du nº 2 (deux régressions linéaires,
  une par bras, sur `registre2.VARIABLES`) ; les modèles « cases » estiment
  l'effet par case sur le pilote, rétréci vers l'effet moyen (`RETRECI`).
- **Le placebo** remplace l'issue par une variable connue **avant** l'envoi
  (`PLACEBO`) : le message ne peut pas l'avoir changée, la politique apprise ne
  doit rien y « gagner ».
- **Open Bandit** : l'échantillon public du dépôt `st-tech/zr-obp` (10 000
  impressions par politique et par campagne, du 24 au 30 novembre 2019).
- **Kickstarter** : n'entrent que les campagnes réussies ou échouées, lancées
  du 1er mai 2009 au 31 décembre 2017, d'objectif positif et de durée de 1 à
  92 jours. La foule se compte sur **toutes** les campagnes lancées (annulées et
  suspendues comprises : elles ont pris de l'attention), à trois jours près.
  Elle se lit à l'intérieur de chaque case (catégorie, année, mois), le jour de
  la semaine, la taille de l'objectif et la durée retirés. Les pays qui
  ouvrent : ceux dont la première campagne précède le 1er janvier 2016 (17
  pays) ; les pionniers sont les campagnes des 90 premiers jours, les suivants
  celles des jours 91 à 730 ; le témoin est la même différence aux États-Unis,
  sur les mêmes dates.
- **Les baleines** : 1 % des clients ayant acheté dans la période, classés par
  dépense (`COUPES` du nº 3).

`sens` vaut +1 ou −1 quand une direction est annoncée, 0 pour une question
ouverte. Changer une définition après un résultat imposerait un nouvel
identifiant ; le registre garderait les deux.
"""

from __future__ import annotations

from .registre import Hypothese
from .registre3 import COUPES  # noqa: F401  (les coupes des baleines et de l'accélération)

# ---------------------------------------------------------------------------
# Famille A : la politique apprise contre les règles de la foule
# ---------------------------------------------------------------------------

#: Réglage principal : la part de la base qui sert de pilote (le reste juge),
#: la part de la base jugée à qui l'agence écrit, et le modèle.
PILOTE = 0.5
BUDGET = 1 / 3
MODELE = "mco"
#: La courbe de spécification : tous les croisements (3 × 4 × 3 = 36 réglages).
PILOTES = (0.2, 0.35, 0.5)
BUDGETS = (0.1, 0.2, 1 / 3, 0.5)
MODELES = ("mco", "cases2", "cases3")
#: Rétrécissement de l'effet d'une case vers l'effet moyen : (n τ_case + K τ̄) / (n + K),
#: n = n₁n₀/(n₁ + n₀) dans la case, sur le pilote.
RETRECI = 100
#: Les variables des cases, par jeu : (variable, découpage). « q5 » = quintiles
#: du pilote, « q3 » = terciles, une liste = bornes fixes, « val » = valeurs.
CASES = {
    "hillstrom": {"cases2": (("log_historique", "q5"), ("recence", (3, 6, 10))),
                  "cases3": (("log_historique", "q5"), ("recence", (3, 6, 10)), ("hf", "val"))},
    "lenta": {"cases2": (("log_depense_12m", "q5"), ("rep_sms", "q3")),
              "cases3": (("log_depense_12m", "q5"), ("rep_sms", "q3"), ("sexe", "val"))},
    "x5": {"cases2": (("log_depense", "q5"), ("recence_j", "q5")),
           "cases3": (("log_depense", "q5"), ("recence_j", "q5"), ("age", "q3"))},
}
#: Tous les réglages sont jugés sur la même moitié de la base : chaque client
#: reçoit un nombre u tiré au hasard ; il est jugé si u ≥ 0,5, il est au pilote
#: si u < π (les pilotes de 20, 35 et 50 % sont emboîtés, le juge est commun).
#: Les règles de la foule. « valeur » : les plus gros dépensiers d'abord ;
#: « risque » : les plus probables de ne rien faire sans message (modèle du bras
#: témoin, sur le pilote) ; « hasard » : un ordre tiré au sort.
VALEUR = {"hillstrom": "historique", "lenta": "depense_12m", "x5": "depense"}
REGLES = ("valeur", "risque", "hasard")
#: L'issue du placebo : connue avant l'envoi, donc insensible au message.
PLACEBO = {"hillstrom": "femmes", "lenta": "sexe_f", "x5": "express_oui"}
#: Le rééchantillonnage : les clients jugés sont répartis au hasard en GROUPES
#: groupes ; les groupes reçoivent des poids de Poisson (bootstrap de Poisson
#: sur des sommes suffisantes, exact pour des issues 0/1). TIRAGES tirages.
GROUPES = 1000
TIRAGES = 999
#: Autres coupes pilote / jugés : 19 graines de plus que la coupe principale.
COUPES_EN_PLUS = 19
#: CSCV : BLOCS blocs de clients jugés ; toutes les moitiés (C(16, 8) = 12 870).
BLOCS = 16

# ---------------------------------------------------------------------------
# Famille B : le bandit
# ---------------------------------------------------------------------------

CAMPAGNES = ("all", "men", "women")
OBP_COMMIT = "8cbd5fa4558b7ad2ba4781546d6604e4cc3e07c4"

# ---------------------------------------------------------------------------
# Famille K : la foule et les pionniers
# ---------------------------------------------------------------------------

K_DEBUT, K_FIN = "2009-05-01", "2018-01-01"
K_FENETRE = 3            # jours de part et d'autre du lancement
K_DUREE = (1, 92)        # jours
PIONNIERS = 90           # jours après la première campagne du pays
SUIVANTS = 730
OUVERTURE_AVANT = "2016-01-01"
#: Courbe de spécification de la foule : fenêtre × issue × case.
K_FENETRES = (1, 3, 7)
K_ISSUES = ("reussite", "log_soutiens")
K_CASES = ("mois", "semaine")
#: Le placebo de la foule : les lancements de la catégorie 100 à 106 jours plus
#: tard. Une campagne dure au plus 92 jours : ils ne peuvent pas l'avoir gênée.
K_PLACEBO = (100, 106)
#: Courbe de spécification des pionniers : fenêtre des pionniers × des suivants.
K_PIONNIERS = (30, 90, 180)
K_SUIVANTS = (365, 730)
#: Le placebo des pionniers : un faux jour d'ouverture, un an après le vrai.
K_FAUSSE_OUVERTURE = 365
#: La stabilité des pionniers : la première vague (pays ouverts avant 2015)
#: contre la seconde.
K_VAGUE = "2015-01-01"

# ---------------------------------------------------------------------------
# Famille W : les baleines
# ---------------------------------------------------------------------------

BALEINE = 0.01
W_PARTS = (0.005, 0.01, 0.02, 0.05)
W_CLASSEMENTS = ("depense", "jours")

# ---------------------------------------------------------------------------
# Famille R : l'accélération revérifiée
# ---------------------------------------------------------------------------

#: Courbe de spécification : définition × seuil d'achats × issue (3 × 3 × 2).
R_DEFINITIONS = ("moities", "tiers", "dernier")
R_SEUILS = (3, 4, 5)
R_ISSUES = ("depense", "jours")
R_TIRAGES_SPEC = 199

# ---------------------------------------------------------------------------
# La batterie
# ---------------------------------------------------------------------------

#: Les tests, dans l'ordre de la page. Chaque règle est fixée ici.
TESTS = (
    ("nul", "Loi nulle", "p < 0,05 dans le sens annoncé, réglage principal"),
    ("bh", "Famille corrigée", "q de Benjamini-Hochberg < 0,05 sur les 25 tests du nº 4"),
    ("holm", "Aucune fausse alerte", "p de Holm < 0,05 sur les 25 tests (taux d'erreur de la famille)"),
    ("t3", "Seuil des quants", "|t| ≥ 3 (Harvey, Liu et Zhu, 2016)"),
    ("coupes", "Autres coupes", "même sens dans au moins 90 % des 20 coupes pilote / jugés"),
    ("marches", "Autres marchés", "même sens sur chaque marché où la mesure existe"),
    ("spec", "Courbe de spécification", "même sens dans au moins 90 % des réglages, "
                                        "significatif dans au moins la moitié"),
    ("cscv", "Choix du meilleur réglage", "le réglage choisi sur une moitié perd sur l'autre moins de 5 % "
                                          "du temps, et PBO ≤ 0,5 (Bailey et al., 2017)"),
    ("spa", "Fouille des données", "p < 0,05 au test SPA de Hansen (2005) contre la règle de la foule"),
    ("placebo", "Placebo", "rien de significatif sur une issue que le message ne peut pas changer"),
    ("temps", "Stabilité dans le temps", "même sens dans au moins 80 % des périodes"),
    ("dsr", "Sharpe dégonflé", "DSR ≥ 0,95 (Bailey et López de Prado, 2014)"),
    ("arene", "Quand les autres copient", "l'avance reste positive dans au moins 90 % des tirages de "
                                          "l'arène, à 10, 50 et 90 % d'imitateurs"),
)
SEUIL_COUPES = 0.90
SEUIL_SPEC_SENS = 0.90
SEUIL_SPEC_SIGNIF = 0.50
SEUIL_PERTE = 0.05
SEUIL_PBO = 0.5
SEUIL_TEMPS = 0.80
SEUIL_DSR = 0.95
SEUIL_T = 3.0
SEUIL_ARENE = 0.90
#: Les tests « temps » : années (K01, K02), vagues de pays (K03), coupes
#: glissantes du nº 3 (W, R : CDNOW et Online Retail II seulement), jours (B).
#: Le Sharpe dégonflé se lit sur la série des IC des coupes glissantes (R) et
#: sur la série des écarts de clic par jour (B) ; le nombre d'essais vaut 5
#: pour R (les cinq signaux du nº 3) et 1 pour B.

# ---------------------------------------------------------------------------
# L'arène
# ---------------------------------------------------------------------------

AGENCES = 200
MOIS = 36
TIRAGES_ARENE = 400
#: Le domaine des paramètres, tiré en hypercube latin. Les bornes viennent
#: d'études quand il y en a (dites entre parenthèses), sont larges sinon.
DOMAINE = {
    "tau": (1.0, 2.0),            # niveaux de raisonnement, Poisson (Camerer, Ho et Chong, 2004)
    "imitation": (0.0, 0.10),     # part des agences qui comparent et copient chaque mois
    "capacite": (0.2, 1.0),       # chance qu'une agence qui copie le niveau 2 sache le faire
    "encombrement": (0.0, 1.0),   # perte d'effet d'une tactique quand toute la foule la fait
    "divulgation": (0.3, 0.8),    # baisse des achats quand l'IA est annoncée (Luo et al., 2019 : 0,797)
    "part_chat": (0.3, 0.7),      # part du revenu qui passe par la conversation
    "economie_ia": (0.05, 0.25),  # coût du chat épargné par l'IA, en part du revenu
    "controle": (0.0, 0.05),      # chance mensuelle que l'obligation d'annoncer soit appliquée
    "bascule": (1, 6),            # mois pour repasser à un chat humain une fois contrôlé
    "temoin": (0.10, 0.20),       # part des fans gardée en groupe témoin au niveau 2
    "apprentissage": (2_000, 50_000),  # fans pour obtenir la moitié du gain d'apprentissage
    "depart": (0.01, 0.04),       # départ mensuel d'une créatrice à part égale
    "sensibilite": (0.0, 3.0),    # hausse des départs quand l'agence prend plus
    "attrait": (0.0, 3.0),        # poids de ce que gagne une créatrice dans son choix d'agence
    "visibilite": (0.0, 1.0),     # avantage cumulatif de la taille (Salganik et al., 2006)
    "bruit": (0.05, 0.30),        # bruit mensuel du revenu d'une agence
    "heterogeneite": (0.5, 1.5),  # dispersion (log) de la taille initiale des agences
    "transparence": (0.0, 0.3),   # part du revenu du chat perdue à dire que l'équipe écrit (aucune étude)
}
#: Le modèle de l'arène, fixé ici :
#: - revenu d'une créatrice par mois = qualité × [(1 − part_chat) + part_chat × ciblage × franchise] × bruit ;
#: - ciblage : hasard au niveau 0 (1) ; gros dépensiers au niveau 1 (ρ_valeur, encombré par la part des
#:   agences de niveau ≥ 1 : × (1 − encombrement × part)) ; appris aux niveaux 2 et 3
#:   (1 + (ρ_appris − 1) × fans / (fans + apprentissage)), sur la part des fans hors témoin ;
#: - ρ_appris et ρ_valeur ne sont pas tirés : ils viennent des mesures A07–A09 (appris / hasard) et
#:   A10–A12 (gros dépensiers / hasard), réglage principal, moyenne des trois marchés (`CALAGE`) ;
#: - franchise : niveau 0 (chat humain qui se fait passer pour la créatrice) et niveau 1 (IA non annoncée)
#:   valent 1 jusqu'au contrôle, puis 1 − transparence (niveau 0 dès le contrôle ; niveau 1 après
#:   `bascule` mois à 1 − divulgation) ; niveaux 2 et 3 : 1 − transparence dès le départ ;
#: - coût du chat en part du revenu : humain `COUT_HUMAIN`, IA `COUT_HUMAIN − economie_ia` (niveau 1 avant
#:   bascule), IA en appui des humains `COUT_HUMAIN − economie_ia / 2` (niveaux 2 et 3) ;
#: - l'agence garde `PRISE × (1 − PLATEFORME)` du revenu, moins le chat ; la créatrice garde le reste ;
#: - départs : `depart × exp(sensibilite × (PRISE − 0,5))` par mois ; les créatrices qui partent et les
#:   nouvelles (`CROISSANCE` du total par mois) choisissent une agence avec un poids
#:   taille^visibilite × exp(attrait × (paie par créatrice / paie moyenne − 1)) ;
#: - imitation : chaque mois, une agence sur `imitation` regarde une autre agence au hasard et copie son
#:   niveau si elle gagne plus par créatrice (niveau ≥ 2 : seulement avec la chance `capacite`) ;
#: - contrôle : chaque mois, chance `controle` que l'obligation d'annoncer s'applique (pour de bon) ;
#: - niveau 3 : témoin double, prise de 30 %.
CALAGE = "A07–A09 pour ρ_appris, A10–A12 pour ρ_valeur (rapport des gains au hasard, réglage principal)"
FANS_PAR_CREATRICE = 2_000
CROISSANCE = 0.01
COUT_HUMAIN = 0.15
PLATEFORME = 0.20
TAILLE_FOCALE = 3
#: Les parts d'imitateurs du test « quand les autres copient » (part des concurrents au niveau 2 au départ).
IMITATEURS = (0.1, 0.5, 0.9)
#: La part prise par l'agence, selon le niveau (déclarée, pas tirée).
PRISE = {0: 0.50, 1: 0.50, 2: 0.40, 3: 0.30}
#: Les quatre stratégies évaluées pour l'agence de l'utilisateur.
STRATEGIES = {0: "Le guide", 1: "La mode", 2: "Un coup d'avance", 3: "Trop d'avance"}
#: Les affirmations de l'arène et leur seuil (part des tirages).
Z = (
    ("Z01", "Un coup d'avance finit devant la mode", 0.90,
     "rang final de la stratégie 2 meilleur que celui de la stratégie 1, même graine"),
    ("Z02", "Un coup d'avance finit devant le guide", 0.90,
     "rang final de la stratégie 2 meilleur que celui de la stratégie 0, même graine"),
    ("Z03", "Un coup d'avance finit devant trop d'avance", 0.50,
     "rang final de la stratégie 2 meilleur que celui de la stratégie 3, même graine"),
    ("Z04", "L'avance tient quand la moitié des concurrents la copie", 0.90,
     "stratégie 2 devant la médiane des agences quand 50 % des concurrents jouent le niveau 2 dès le départ"),
)

# ---------------------------------------------------------------------------
# Les hypothèses statistiques (famille BH du nº 4 : 25 tests)
# ---------------------------------------------------------------------------

FAMILLES = {
    "A": "Apprendre chez soi",
    "B": "Le bandit",
    "K": "La foule",
    "W": "Les baleines changent",
    "R": "L'accélération, revérifiée",
}

_A = ("gain du message (points d'issue pour 100 clients jugés), politique apprise sur le pilote contre {r}, "
      "au même nombre de messages ; réglage principal (pilote 50 %, tiers de la base, mco) ; "
      "bootstrap de Poisson sur 1 000 groupes")
_B = "taux de clic de l'échantillonnage de Thompson moins celui du hasard, en points ; permutation des politiques"
_W = ("part des baleines de la période de validation (1 % de tête par dépense) qui n'étaient pas des baleines "
      "de la période d'apprentissage, moins 50 % ; test binomial")
_R = "IC partiel de l'accélération avec la dépense de validation, RFM retiré (mesure de S07–S09 du nº 3)"

H = (
    Hypothese("A01", "A", "hillstrom", "Apprendre chez soi bat l'envoi aux gros dépensiers", +1,
              _A.format(r="les plus gros dépensiers"),
              "Écrire d'abord aux gros dépensiers, comme tout le monde, rapporte moins qu'apprendre à qui écrire."),
    Hypothese("A02", "A", "lenta", "Apprendre chez soi bat l'envoi aux gros dépensiers", +1,
              _A.format(r="les plus gros dépensiers"),
              "Écrire d'abord aux gros dépensiers, comme tout le monde, rapporte moins qu'apprendre à qui écrire."),
    Hypothese("A03", "A", "x5", "Apprendre chez soi bat l'envoi aux gros dépensiers", +1,
              _A.format(r="les plus gros dépensiers"),
              "Écrire d'abord aux gros dépensiers, comme tout le monde, rapporte moins qu'apprendre à qui écrire."),
    Hypothese("A04", "A", "hillstrom", "Apprendre chez soi bat la relance des plus à risque", +1,
              _A.format(r="les plus à risque"),
              "Relancer ceux qui décrochent rapporte moins qu'apprendre qui le message fait revenir."),
    Hypothese("A05", "A", "lenta", "Apprendre chez soi bat la relance des plus à risque", +1,
              _A.format(r="les plus à risque"),
              "Relancer ceux qui décrochent rapporte moins qu'apprendre qui le message fait revenir."),
    Hypothese("A06", "A", "x5", "Apprendre chez soi bat la relance des plus à risque", +1,
              _A.format(r="les plus à risque"),
              "Relancer ceux qui décrochent rapporte moins qu'apprendre qui le message fait revenir."),
    Hypothese("A07", "A", "hillstrom", "Apprendre chez soi bat l'envoi au hasard", +1,
              _A.format(r="un tirage au hasard"),
              "Choisir à qui écrire, appris sur ses fans, rapporte plus qu'écrire au hasard."),
    Hypothese("A08", "A", "lenta", "Apprendre chez soi bat l'envoi au hasard", +1,
              _A.format(r="un tirage au hasard"),
              "Choisir à qui écrire, appris sur ses fans, rapporte plus qu'écrire au hasard."),
    Hypothese("A09", "A", "x5", "Apprendre chez soi bat l'envoi au hasard", +1,
              _A.format(r="un tirage au hasard"),
              "Choisir à qui écrire, appris sur ses fans, rapporte plus qu'écrire au hasard."),
    Hypothese("A10", "A", "hillstrom", "La règle des gros dépensiers fait autrement que le hasard", 0,
              "gain du message, gros dépensiers contre hasard, au même nombre de messages ; réglage principal",
              "La règle de la mode fait-elle mieux, ou pire, que d'écrire au hasard ?"),
    Hypothese("A11", "A", "lenta", "La règle des gros dépensiers fait autrement que le hasard", 0,
              "gain du message, gros dépensiers contre hasard, au même nombre de messages ; réglage principal",
              "La règle de la mode fait-elle mieux, ou pire, que d'écrire au hasard ?"),
    Hypothese("A12", "A", "x5", "La règle des gros dépensiers fait autrement que le hasard", 0,
              "gain du message, gros dépensiers contre hasard, au même nombre de messages ; réglage principal",
              "La règle de la mode fait-elle mieux, ou pire, que d'écrire au hasard ?"),
    Hypothese("B01", "B", "obp_all", "Apprendre en continu rapporte plus de clics que le hasard", +1, _B,
              "Pousser le contenu qui marche, en continuant d'essayer les autres, rapporte plus que tourner au hasard."),
    Hypothese("B02", "B", "obp_men", "Apprendre en continu rapporte plus de clics que le hasard", +1, _B,
              "Pousser le contenu qui marche, en continuant d'essayer les autres, rapporte plus que tourner au hasard."),
    Hypothese("B03", "B", "obp_women", "Apprendre en continu rapporte plus de clics que le hasard", +1, _B,
              "Pousser le contenu qui marche, en continuant d'essayer les autres, rapporte plus que tourner au hasard."),
    Hypothese("B04", "B", "obp", "Apprendre en continu rapporte plus de clics que le hasard, les trois campagnes ensemble",
              +1, "écart de Mantel-Haenszel sur les trois campagnes ; permutation dans chaque campagne",
              "Le gain du bandit tient quand on met les trois rayons ensemble."),
    Hypothese("K01", "K", "kickstarter", "Lancer quand la catégorie est encombrée fait moins réussir", -1,
              "pente de la réussite (points) selon le log du nombre de lancements de la catégorie à trois jours près, "
              "dans la case catégorie × mois, jour de la semaine, objectif et durée retirés ; permutation dans la case",
              "Sortir le même jour que tout le monde dans la même niche coûte des ventes."),
    Hypothese("K02", "K", "kickstarter", "La foule de sa propre catégorie pèse plus que celle des autres", -1,
              "pente de la foule de la catégorie moins pente de la foule des autres catégories, même modèle ; "
              "rééchantillonnage des semaines",
              "Ce qui coûte, c'est la concurrence directe, pas l'agitation générale du site."),
    Hypothese("K03", "K", "kickstarter", "Les premières campagnes d'un pays qui ouvre réussissent autrement que les suivantes", 0,
              "(réussite des 90 premiers jours − jours 91 à 730) dans le pays, moins la même différence aux "
              "États-Unis sur les mêmes dates ; 17 pays ; rééchantillonnage des campagnes",
              "Arriver le premier sur un marché neuf : avantage, ou simple pari ?"),
    Hypothese("W01", "W", "cdnow", "Plus de la moitié des baleines de demain ne sont pas celles d'aujourd'hui", +1, _W,
              "Les meilleurs fans de demain sont surtout d'autres que ceux d'aujourd'hui."),
    Hypothese("W02", "W", "retail", "Plus de la moitié des baleines de demain ne sont pas celles d'aujourd'hui", +1, _W,
              "Les meilleurs fans de demain sont surtout d'autres que ceux d'aujourd'hui."),
    Hypothese("W03", "W", "x5", "Plus de la moitié des baleines de demain ne sont pas celles d'aujourd'hui", +1, _W,
              "Les meilleurs fans de demain sont surtout d'autres que ceux d'aujourd'hui."),
    Hypothese("R01", "R", "cdnow", "L'accélération annonce la dépense, au-delà de RFM", +1, _R,
              "Un fan qui revient de plus en plus vite vaut plus que ce que disent ses chiffres."),
    Hypothese("R02", "R", "retail", "L'accélération annonce la dépense, au-delà de RFM", +1, _R,
              "Un fan qui revient de plus en plus vite vaut plus que ce que disent ses chiffres."),
    Hypothese("R03", "R", "x5", "L'accélération annonce la dépense, au-delà de RFM", +1, _R,
              "Un fan qui revient de plus en plus vite vaut plus que ce que disent ses chiffres."),
)

#: Quels tests s'appliquent à quelle famille (les autres sont « sans objet »).
APPLICABLES = {
    "A": ("nul", "bh", "holm", "t3", "coupes", "marches", "spec", "cscv", "spa", "placebo", "arene"),
    "B": ("nul", "bh", "holm", "t3", "marches", "spec", "placebo", "temps", "dsr", "arene"),
    "K": ("nul", "bh", "holm", "t3", "spec", "placebo", "temps"),
    "W": ("nul", "bh", "holm", "t3", "marches", "spec", "temps"),
    "R": ("nul", "bh", "holm", "t3", "marches", "spec", "cscv", "spa", "placebo", "temps", "dsr"),
}
#: A10–A12 comparent deux règles de la foule : aucun réglage n'est choisi, rien
#: n'est copié. K02 est lui-même la comparaison de K01 à la foule des autres.
#: X5 n'a pas de coupes glissantes (quatre mois d'achats).
SANS_OBJET = {
    "A10": ("cscv", "spa", "arene"), "A11": ("cscv", "spa", "arene"), "A12": ("cscv", "spa", "arene"),
    "K02": ("placebo",),
    "W03": ("temps",),
    "R03": ("temps", "dsr"),
}


def par_id() -> dict[str, Hypothese]:
    return {h.id: h for h in H}


def applicables(i: str) -> tuple[str, ...]:
    fam = par_id()[i].famille
    return tuple(t for t in APPLICABLES[fam] if t not in SANS_OBJET.get(i, ()))
