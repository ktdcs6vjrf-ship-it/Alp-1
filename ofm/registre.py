"""Le registre des hypothèses — écrit avant le premier calcul.

C'est la règle qui sépare une recherche d'une pêche. Tester soixante idées et
ne publier que les sept qui « marchent », c'est publier le bruit : au seuil de
5 %, trois d'entre elles passeraient sans le moindre effet. Le registre fixe
donc, **avant d'avoir regardé les données**, chaque hypothèse, son sens
attendu, sa mesure et son test. Le document les publie toutes, celles qui
tombent comme celles qui tiennent, et la correction de Benjamini-Hochberg
porte sur la famille entière.

`sens` vaut +1 ou −1 quand une direction est annoncée, 0 pour une question
exploratoire (test bilatéral sans pari). Une hypothèse dont l'effet est
significatif **dans le sens contraire** est un résultat, pas un échec, et le
verdict le dit.

Aucune ligne de ce fichier n'a été modifiée après le calcul : un changement de
définition imposerait d'en changer l'identifiant, et le registre garderait les
deux. Une seule retouche a eu lieu **avant** tout calcul de résultat : D15 à
D17 visaient l'heure locale du demandeur, mais le champ « local » du jeu ne
porte que trois décalages (0, +1 et +8 h) — le fuseau de la machine qui a
collecté, pas celui des demandeurs. Ils se lisent donc à l'heure de New York,
approximation d'un public surtout nord-américain. Et les hypothèses de
speed dating ont été restreintes, toujours avant calcul, aux **décisions
d'hommes** : un public d'abonnés est masculin, et la décision qui compte est
la sienne.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Hypothese:
    id: str
    famille: str
    jeu: str
    enonce: str
    sens: int
    mesure: str
    ofm: str


FAMILLES = {
    "D": "Demander",
    "O": "Offrir",
    "P": "Persuader",
    "N": "Négocier",
    "S": "Choisir",
    "R": "Revenir",
    "T": "Le calendrier",
}

H = (
    # --- Demander : Random Acts of Pizza ------------------------------------
    Hypothese("D01", "D", "raop", "Remercier d'avance aide à recevoir", +1,
              "« thank », « appreciate », « grateful » dans la demande",
              "Le merci fait partie de la demande, pas seulement de la suite."),
    Hypothese("D02", "D", "raop", "Promettre de rendre aide à recevoir", +1,
              "« pay it forward », « return the favor », « pay you back », « repay »",
              "Offrir une contrepartie explicite à un pourboire."),
    Hypothese("D03", "D", "raop", "Montrer une preuve aide à recevoir", +1,
              "lien d'image (imgur, .jpg, .png) ou mot « proof »",
              "La vérification et la preuve d'authenticité se monnaient."),
    Hypothese("D04", "D", "raop", "Le récit d'emploi aide à recevoir", +1,
              "lexique de l'emploi : job, unemployed, fired, laid off, interview, paycheck",
              "Un contexte de vie vérifiable crédibilise une demande."),
    Hypothese("D05", "D", "raop", "Le récit d'argent aide à recevoir", +1,
              "lexique de l'argent : rent, bills, broke, bank, overdraft, money",
              "Idem, pour une contrainte matérielle."),
    Hypothese("D06", "D", "raop", "Le récit familial aide à recevoir", +1,
              "lexique de la famille : wife, husband, kids, son, daughter, family, baby",
              "Idem, pour un tiers à charge."),
    Hypothese("D07", "D", "raop", "Le récit étudiant change la réussite", 0,
              "lexique étudiant : college, student, finals, semester, exam, dorm",
              "Question ouverte : un statut sans détresse aide-t-il ?"),
    Hypothese("D08", "D", "raop", "Le récit de simple envie nuit à la demande", -1,
              "lexique du désir : craving, crave, birthday, party, drunk, celebrate",
              "Demander pour l'envie seule est le registre qui convertit le moins."),
    Hypothese("D09", "D", "raop", "Une demande longue reçoit davantage", +1,
              "nombre de mots au-dessus de la médiane",
              "L'effort visible d'une demande se lit comme un signal."),
    Hypothese("D10", "D", "raop", "Le demandeur à karma élevé reçoit davantage", +1,
              "solde de votes Reddit au-dessus de la médiane",
              "Le statut d'un compte ancien et noté précède la demande."),
    Hypothese("D11", "D", "raop", "Un compte ancien reçoit davantage", +1,
              "âge du compte au-dessus de la médiane",
              "Idem, par l'ancienneté seule."),
    Hypothese("D12", "D", "raop", "Un membre déjà actif dans la communauté reçoit davantage", +1,
              "a déjà commenté ou publié dans le forum avant la demande",
              "Donner avant de demander : présence préalable dans le lieu."),
    Hypothese("D13", "D", "raop", "« Please » change la réussite", 0,
              "mot « please » dans la demande",
              "Question ouverte sur la politesse formelle."),
    Hypothese("D14", "D", "raop", "L'urgence change la réussite", 0,
              "tonight, today, asap, right now",
              "Question ouverte : l'urgence presse-t-elle ou repousse-t-elle ?"),
    Hypothese("D15", "D", "raop", "Une demande du début de mois reçoit davantage", +1,
              "jour 1 à 10 du mois, heure de New York",
              "Le donateur a sa paie en début de mois : calendrier des relances."),
    Hypothese("D16", "D", "raop", "Le week-end change la réussite", 0,
              "samedi ou dimanche, heure de New York",
              "Question ouverte sur le jour de la semaine."),
    Hypothese("D17", "D", "raop", "Le soir change la réussite", 0,
              "18 h à minuit, heure de New York",
              "Question ouverte sur l'heure de la demande."),
    # --- Offrir : Karlan et List --------------------------------------------
    Hypothese("O01", "O", "karlan", "Une offre de doublement augmente la réponse", +1,
              "taux de don, lettre avec contrepartie contre lettre témoin",
              "Un bonus attaché à l'achat déclenche l'achat."),
    Hypothese("O02", "O", "karlan", "Un bonus plus généreux augmente encore la réponse", +1,
              "taux de don, contrepartie 2:1 ou 3:1 contre 1:1",
              "Si non : offrir le plus petit bonus, garder la marge."),
    Hypothese("O03", "O", "karlan", "Un plafond de contrepartie annoncé plus haut augmente la réponse", +1,
              "taux de don, plafond 100 000 $ contre 25 000 $",
              "La taille annoncée de l'enveloppe joue-t-elle ?"),
    Hypothese("O04", "O", "karlan", "Un montant suggéré plus haut élève le don", +1,
              "montant donné parmi les donateurs, suggestion 1,5× contre 1×",
              "Le prix suggéré d'un pourboire tire-t-il le montant ?"),
    Hypothese("O05", "O", "karlan", "Le donateur récent répond davantage", +1,
              "taux de don, dernier don il y a 3 mois ou moins contre plus",
              "Viser d'abord le fan récemment actif."),
    Hypothese("O06", "O", "karlan", "Le donateur fréquent répond davantage", +1,
              "taux de don, au moins 4 dons passés contre moins",
              "Viser le fan qui a l'habitude d'acheter."),
    Hypothese("O07", "O", "karlan", "Le bonus agit davantage sur le donateur récent", 0,
              "interaction contrepartie × récence sur le taux de don",
              "Faut-il réserver le bonus aux actifs ou aux endormis ?"),
    Hypothese("O08", "O", "karlan", "Le bonus agit davantage dans les États républicains", +1,
              "interaction contrepartie × État Bush 2004",
              "Hétérogénéité géographique du même levier."),
    Hypothese("O09", "O", "karlan", "Le bonus augmente aussi le montant de qui donne", +1,
              "montant moyen parmi les donateurs, contrepartie contre témoin",
              "Le bonus fait-il monter le panier, ou seulement l'entrée ?"),
    Hypothese("O10", "O", "karlan", "Les montants choisis s'agglutinent sur les nombres ronds", +1,
              "part des dons multiples de 5 $, contre la part d'une loi lisse",
              "Grille de pourboires : proposer des montants ronds."),
    # --- Persuader : Persuasion for Good -------------------------------------
    Hypothese("P01", "P", "p4g", "Le persuadeur qui pose des questions obtient davantage", +1,
              "points d'interrogation du persuadeur au-dessus de la médiane",
              "Questionner le fan plutôt que réciter un argumentaire."),
    Hypothese("P02", "P", "p4g", "Nommer un montant précis obtient davantage", +1,
              "le persuadeur écrit un montant ($, cents, dollar)",
              "Une demande chiffrée plutôt qu'une demande ouverte."),
    Hypothese("P03", "P", "p4g", "Dire qu'on donne soi-même obtient davantage", +1,
              "« I donate », « I will donate », « I've donated »",
              "Montrer l'exemple : preuve sociale à la première personne."),
    Hypothese("P04", "P", "p4g", "Laisser explicitement libre obtient davantage", +1,
              "« no pressure », « up to you », « your choice », « no obligation »",
              "La technique « vous êtes libre » appliquée à une offre."),
    Hypothese("P05", "P", "p4g", "L'appel à l'émotion obtient davantage", +1,
              "children, kids, starving, suffering, die, heartbreaking",
              "Le registre émotionnel contre le registre informatif."),
    Hypothese("P06", "P", "p4g", "La personne agréable donne davantage", +1,
              "score d'agréabilité du persuadé au-dessus de la médiane",
              "Qui viser : un trait de la personne, pas du message."),
    Hypothese("P07", "P", "p4g", "L'accord de style entre les deux obtient davantage", +1,
              "appariement des mots-outils (LSM) au-dessus de la médiane",
              "Écrire comme écrit le fan : longueur, pronoms, ponctuation."),
    Hypothese("P08", "P", "p4g", "Le persuadeur prolixe change le résultat", 0,
              "mots par tour du persuadeur au-dessus de la médiane",
              "Question ouverte : longueur des messages du vendeur."),
    Hypothese("P09", "P", "p4g", "Parler du don dès les trois premiers tours change le résultat", 0,
              "première mention de « donat » par le persuadeur au tour 3 ou avant",
              "Question ouverte : vendre tôt ou tard dans l'échange."),
    Hypothese("P10", "P", "p4g", "Le persuadé engagé d'emblée donne davantage", +1,
              "mots du persuadé aux trois premiers tours au-dessus de la médiane",
              "L'engagement des premiers messages désigne l'acheteur."),
    Hypothese("P11", "P", "p4g", "Le persuadé qui pose des questions donne davantage", +1,
              "points d'interrogation du persuadé au-dessus de la médiane",
              "Une question du fan est un signal d'achat."),
    Hypothese("P12", "P", "p4g", "Remercier change le résultat", 0,
              "le persuadeur écrit « thank »",
              "Question ouverte sur la politesse du vendeur."),
    # --- Négocier : CraigslistBargain ----------------------------------------
    Hypothese("N01", "N", "bargain", "Un prix d'annonce précis se négocie moins", +1,
              "prix final / prix affiché, annonce non ronde contre ronde",
              "Afficher 37 $ plutôt que 40 $ pour un contenu sur mesure."),
    Hypothese("N02", "N", "bargain", "Le vendeur qui chiffre le premier vend plus cher", +1,
              "prix final / affiché quand le premier montant vient du vendeur",
              "Annoncer son prix avant que le fan ne propose le sien."),
    Hypothese("N03", "N", "bargain", "La première offre de l'acheteur ancre le prix final", +1,
              "corrélation entre première offre de l'acheteur et prix final, rapportés à l'annonce",
              "Ne jamais laisser une offre basse sans contre-ancre."),
    Hypothese("N04", "N", "bargain", "Une négociation longue change le prix", 0,
              "prix final / affiché, nombre de tours au-dessus de la médiane",
              "Question ouverte : céder vite ou tenir longtemps."),
    Hypothese("N05", "N", "bargain", "Une contre-offre précise du vendeur tient mieux", +1,
              "prix final / affiché, première contre-offre du vendeur non ronde",
              "Répondre à un marchandage par un montant précis."),
    Hypothese("N06", "N", "bargain", "Justifier par l'état de l'objet tient le prix", +1,
              "le vendeur cite l'état : new, excellent, barely used, great condition",
              "Justifier un prix par une qualité concrète du contenu."),
    Hypothese("N07", "N", "bargain", "Se dire ferme tient le prix", +1,
              "le vendeur écrit firm, final, lowest, best I can do",
              "Un engagement déclaré ferme la négociation."),
    Hypothese("N08", "N", "bargain", "Chiffrer le premier coûte des accords", 0,
              "taux d'accord quand le vendeur chiffre le premier",
              "Le prix d'une ancre haute : combien de ventes perdues ?"),
    # --- Choisir : speed dating ----------------------------------------------
    Hypothese("S01", "S", "speed", "Le partenaire précédent plus beau fait dire non au suivant", -1,
              "oui d'un homme à la partenaire k selon l'attrait de la partenaire k−1 (notes des autres)",
              "Ce que le fan vient de voir abaisse ce qu'il voit ensuite."),
    Hypothese("S02", "S", "speed", "Le taux de oui baisse au fil de la soirée", -1,
              "oui des hommes selon le rang de la rencontre, à décideur fixé",
              "La fatigue de décision : les premières offres de la séance."),
    Hypothese("S03", "S", "speed", "Qui dit oui à tout le monde est moins choisi", -1,
              "oui reçu des hommes selon le taux de oui donné ailleurs par la femme (désir non sélectif)",
              "Un « tu es mon préféré » envoyé à tous se détecte et se paie."),
    Hypothese("S04", "S", "speed", "Le désir sélectif est rendu", +1,
              "goût relatif de A pour B et goût relatif de B pour A",
              "L'attention singulière, et elle seule, appelle la réciprocité."),
    Hypothese("S05", "S", "speed", "La dispersion des goûts paie sous le seuil et coûte au-dessus", -1,
              "interaction moyenne × écart-type des notes d'attrait reçues des hommes sur le taux de oui reçu",
              "Une niche clivante bat un profil consensuel quand l'achat est rare."),
    Hypothese("S06", "S", "speed", "Croire être aimé fait dire oui", +1,
              "probabilité perçue d'un oui en retour, à attrait et plaisir fixés (décideurs hommes)",
              "Le fan achète à qui il croit plaire."),
    Hypothese("S07", "S", "speed", "La première rencontre de la soirée est avantagée", +1,
              "oui des hommes au premier rang contre les rangs du milieu, à décideur fixé",
              "Le premier message de la séance est le mieux reçu."),
    # --- Revenir : CDNOW -----------------------------------------------------
    Hypothese("R01", "R", "cdnow", "Le modèle BG/NBD prédit mieux que le rythme passé", +1,
              "erreur absolue moyenne des achats répétés de la seconde moitié",
              "Classer les fans par probabilité d'être vivants, pas par dépense."),
    Hypothese("R02", "R", "cdnow", "Après un long silence, l'ancien acheteur fréquent revient moins", -1,
              "achats futurs selon la fréquence passée, parmi les silencieux",
              "Le fan fidèle qui se tait est plus perdu que l'occasionnel qui se tait."),
    Hypothese("R03", "R", "cdnow", "Le classement BG/NBD capte davantage les achats futurs", +1,
              "part des achats futurs captée par le décile de tête",
              "Qui relancer en premier, à budget de chatteur fixé."),
    Hypothese("R04", "R", "cdnow", "La dépense passée prédit la dépense future", +1,
              "corrélation des dépenses des deux moitiés",
              "La covariable qui rend un test A/B deux fois moins cher."),
    # --- Le calendrier -------------------------------------------------------
    Hypothese("T01", "T", "naissances", "Moins de naissances un 13 (contrôle positif)", -1,
              "naissances du 13 contre le 6 et le 20 du même mois",
              "La méthode de calendrier doit voir un effet connu avant d'être crue."),
)


def par_id() -> dict[str, Hypothese]:
    return {h.id: h for h in H}
