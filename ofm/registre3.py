"""Le registre du cahier nº 3 — écrit avant le premier calcul de résultat.

La question de l'utilisateur : *quelles données portent un avantage que le
marché n'a pas encore pris ?* En finance, un avantage qui tient est un signal
qui prédit **au-delà des facteurs que tout le monde connaît** ; ce que tout le
monde regarde est déjà « dans le prix ». Pour une agence, ce que tout le monde
regarde, c'est RFM : depuis quand le fan n'a pas acheté (récence), combien de
fois (fréquence), combien (montant), et depuis quand il est là. Les outils de
gestion de comptes l'affichent tous. Le cahier nº 3 teste donc deux choses :

- **Les signaux (famille S)** — cinq lectures du rythme d'achat que RFM ne
  contient pas (le groupement des achats, l'élan, l'accélération, le pic, la
  variété), mesurées **après avoir retiré tout ce que RFM explique**, sur trois
  marchés d'achats répétés ; puis le *backtest* d'une règle d'agence (donner la
  priorité au dixième des fans le mieux classé) hors échantillon.
- **Les leviers (famille L)** — cinq gestes peu coûteux, tirés au sort sur le
  terrain par d'autres chercheurs : un tout petit bonus, la distance à
  parcourir, l'annonce d'un premier don, le choix coché d'avance, une blague
  avec l'addition, se mettre à hauteur des yeux.

Même règle que les registres nº 1 et nº 2 : chaque hypothèse est fixée **avant
d'avoir regardé un résultat**, avec son sens, sa mesure et son test ; la
correction de Benjamini-Hochberg porte sur **la famille du cahier nº 3 seule**
(ajouter ces tests aux registres publiés changerait leurs valeurs q après coup).
Le registre est commité avant le premier calcul (l'historique du dépôt le date).
Décisions prises avant ce calcul, en regardant la forme des fichiers et le plan
des expériences, jamais une issue :

- **Un achat est un jour d'achat** (les factures d'un même jour s'additionnent,
  comme dans les cahiers nº 1 et nº 2), hors annulations et montants nuls.
- **Les signaux se lisent chez les clients d'au moins deux jours d'achat** dans
  la période d'apprentissage : un rythme demande au moins deux achats.
  L'accélération en demande trois (deux écarts). Le premier achat ouvre la
  fenêtre du client, la fin de la période d'apprentissage la ferme.
- **Ce que RFM sait** (`BASE`) : récence, fréquence, montant moyen par jour
  d'achat et ancienneté, chacun ramené à son rang (de 0 à 1), avec cinq
  morceaux de droite (nœuds à 0,2 · 0,4 · 0,6 · 0,8), plus les six produits
  deux à deux et une constante : 27 termes. C'est volontairement un adversaire
  fort : un signal qui ne ferait que mieux lire la récence n'est pas un signal.
- **La mesure** : la corrélation partielle des rangs (IC) entre le signal et la
  dépense de la période de validation, une fois retiré, de l'un et de l'autre,
  ce que les 27 termes expliquent. **La loi nulle** : les restes du signal sont
  mélangés à l'intérieur des cases RFM (`CASES`), 999 fois.
- **Le backtest** : une moitié des clients, tirée par empreinte (`crc32`),
  apprend deux classements (RFM seul ; RFM et les signaux) ; l'autre moitié
  juge. On compte la part de la dépense de validation que tient le dixième de
  tête de chaque classement. L'intervalle et la valeur p viennent de 999
  rééchantillonnages appariés des clients jugés (poids de Poisson).
- **X5** : 45,8 millions de lignes d'achat ; le cahier garde les clients dont
  l'empreinte `crc32` de l'identifiant vaut 0 modulo 25 (une règle, pas un
  choix). Le 18 mars 2019, dernier jour du fichier, peut être incomplet : il
  est écarté.
- **Thornton** : seules entrent les personnes dont le retrait du résultat, le
  bonus et la distance sont connus (2 834) ; celles dont le village manque
  forment une strate à part. Les bornes du « petit » et du « grand » bonus
  sont fixées sur le plan des montants (`BONUS_PETIT`, `BONUS_GRAND`), sans
  regarder le retrait.
- **Rondeau et List** : six lettres sur 3 000 n'ont pas de montant (ni don,
  ni zéro) ; elles sont écartées.
- **Cai, de Janvry et Sadoulet** : le choix par défaut est tiré au sort par
  hameau (aucun hameau ne mélange les deux formats) : il se permute par hameau,
  à l'intérieur de chaque village. La séance détaillée l'est par personne.

`sens` vaut +1 ou −1 quand une direction est annoncée, 0 pour une question
ouverte. Changer une définition après un résultat imposerait un nouvel
identifiant, et le registre garderait les deux.
"""

from __future__ import annotations

from .registre import Hypothese

#: Les trois marchés d'achats répétés : début, fin d'apprentissage (exclue),
#: fin de validation (exclue).
COUPES = {
    "cdnow": ("1997-01-01", "1997-10-01", "1998-07-01"),
    "retail": ("2009-12-01", "2010-12-01", "2011-12-01"),
    "x5": ("2018-11-21", "2019-02-18", "2019-03-18"),
}
#: Les nœuds des morceaux de droite, sur l'échelle des rangs.
NOEUDS = (0.2, 0.4, 0.6, 0.8)
#: Les cases de la loi nulle : récence en quintiles, fréquence en classes
#: (2, 3, 4–5, 6–9, 10 et plus), montant en quintiles.
CLASSES_F = ((2, 2), (3, 3), (4, 5), (6, 9), (10, 10 ** 9))
TIRAGES = 999
#: La part des fans à qui l'agence donne la priorité, dans le backtest.
PART_CONTACTEE = 0.10
#: L'échantillon de X5 : l'empreinte crc32 de l'identifiant, modulo 25, vaut 0.
X5_MODULO = 25
#: Les signaux de chaque marché (la variété n'existe pas dans CDNOW : un disque
#: de plus y coûte un disque de plus).
SIGNAUX = {
    "cdnow": ("groupement", "elan", "acceleration", "pic"),
    "retail": ("groupement", "elan", "acceleration", "pic", "variete"),
    "x5": ("groupement", "elan", "acceleration", "pic", "variete"),
}
#: Thornton : bornes du petit et du grand bonus, en dollars.
BONUS_PETIT = 0.50
BONUS_GRAND = 1.50

FAMILLES = {
    "S": "Les signaux que RFM ne voit pas",
    "L": "Les leviers tirés au sort",
}

_IC = "IC partiel des rangs avec la dépense de validation, RFM retiré ; loi nulle : restes mélangés dans les cases RFM"
_BT = ("part de la dépense de validation tenue par le dixième de tête, classement RFM et signaux "
       "contre RFM seul, moitié jugée")

H = (
    # --- Les signaux : ce que RFM ne voit pas --------------------------------
    Hypothese("S01", "S", "cdnow", "Le fan qui achète par grappes dépense plus ensuite", +1,
              "groupement des achats (Zhang, Bradlow et Small, 2015) ; " + _IC,
              "Le fan qui achète par séances (trois soirs de suite, puis rien) n'est pas un fan qui décroche."),
    Hypothese("S02", "S", "retail", "Le fan qui achète par grappes dépense plus ensuite", +1,
              "groupement des achats ; " + _IC,
              "Le fan qui achète par séances n'est pas un fan qui décroche."),
    Hypothese("S03", "S", "x5", "Le fan qui achète par grappes dépense plus ensuite", +1,
              "groupement des achats ; " + _IC,
              "Le fan qui achète par séances n'est pas un fan qui décroche."),
    Hypothese("S04", "S", "cdnow", "Le fan dont la dépense se concentre sur la fin dépense plus ensuite", +1,
              "élan : part de la dépense d'apprentissage tombée dans le dernier tiers de la fenêtre du client ; " + _IC,
              "Un fan qui monte en puissance continue de monter."),
    Hypothese("S05", "S", "retail", "Le fan dont la dépense se concentre sur la fin dépense plus ensuite", +1,
              "élan, même définition ; " + _IC,
              "Un fan qui monte en puissance continue de monter."),
    Hypothese("S06", "S", "x5", "Le fan dont la dépense se concentre sur la fin dépense plus ensuite", +1,
              "élan, même définition ; " + _IC,
              "Un fan qui monte en puissance continue de monter."),
    Hypothese("S07", "S", "cdnow", "Le fan dont les écarts entre achats raccourcissent dépense plus ensuite", +1,
              "accélération : log du rapport de l'écart moyen de la première moitié des écarts à celui de la "
              "seconde, clients d'au moins trois jours d'achat ; " + _IC,
              "Un fan qui revient de plus en plus vite est un fan qui s'attache."),
    Hypothese("S08", "S", "retail", "Le fan dont les écarts entre achats raccourcissent dépense plus ensuite", +1,
              "accélération, même définition ; " + _IC,
              "Un fan qui revient de plus en plus vite est un fan qui s'attache."),
    Hypothese("S09", "S", "x5", "Le fan dont les écarts entre achats raccourcissent dépense plus ensuite", +1,
              "accélération, même définition ; " + _IC,
              "Un fan qui revient de plus en plus vite est un fan qui s'attache."),
    Hypothese("S10", "S", "cdnow", "Un gros achat isolé change ce que le fan dépensera", 0,
              "pic : log du rapport du plus gros jour d'achat au jour moyen ; " + _IC,
              "Le plus gros achat d'un fan montre-t-il sa capacité, ou un coup sans lendemain ?"),
    Hypothese("S11", "S", "retail", "Un gros achat isolé change ce que le fan dépensera", 0,
              "pic, même définition ; " + _IC,
              "Le plus gros achat d'un fan montre-t-il sa capacité, ou un coup sans lendemain ?"),
    Hypothese("S12", "S", "x5", "Un gros achat isolé change ce que le fan dépensera", 0,
              "pic, même définition ; " + _IC,
              "Le plus gros achat d'un fan montre-t-il sa capacité, ou un coup sans lendemain ?"),
    Hypothese("S13", "S", "retail", "Le fan qui achète des choses variées dépense plus ensuite", +1,
              "variété : log du nombre moyen de lignes de produit par jour d'achat ; " + _IC,
              "Le fan qui prend des contenus de plusieurs sortes vaut plus que son montant ne le dit."),
    Hypothese("S14", "S", "x5", "Le fan qui achète des choses variées dépense plus ensuite", +1,
              "variété, même définition ; " + _IC,
              "Le fan qui prend des contenus de plusieurs sortes vaut plus que son montant ne le dit."),
    Hypothese("S15", "S", "cdnow", "Les signaux font mieux choisir le dixième de tête que RFM seul", +1, _BT,
              "Donner la priorité aux bons fans : les signaux battent-ils la liste que tout le monde a ?"),
    Hypothese("S16", "S", "retail", "Les signaux font mieux choisir le dixième de tête que RFM seul", +1, _BT,
              "Donner la priorité aux bons fans : les signaux battent-ils la liste que tout le monde a ?"),
    Hypothese("S17", "S", "x5", "Les signaux font mieux choisir le dixième de tête que RFM seul", +1, _BT,
              "Donner la priorité aux bons fans : les signaux battent-ils la liste que tout le monde a ?"),
    # --- Les leviers : des gestes tirés au sort sur le terrain ---------------
    Hypothese("L01", "L", "thornton", "Un bonus, même petit, fait agir", +1,
              "part qui va chercher son résultat, un bonus quelconque contre aucun ; permutation dans le village",
              "Un tout petit cadeau déclenche le geste qu'un long discours ne déclenche pas."),
    Hypothese("L02", "L", "thornton", "Un bonus plus gros fait agir davantage", +1,
              "pente du retrait selon le montant, chez qui a reçu un bonus (points par dollar) ; "
              "permutation des montants dans le village",
              "Doubler le cadeau double-t-il l'effet ?"),
    Hypothese("L03", "L", "thornton", "Le premier pas du bonus fait plus que tout le reste", +1,
              "(petit bonus ≤ 0,50 $ − aucun) moins (grand bonus > 1,50 $ − petit), en points ; "
              "rééchantillonnage des villages",
              "C'est le fait d'offrir qui compte, pas la taille du cadeau."),
    Hypothese("L04", "L", "thornton", "Chaque kilomètre de plus fait moins agir", -1,
              "pente du retrait selon la distance au centre (points par km) ; permutation des distances dans "
              "le village",
              "Chaque étape de plus entre le fan et l'achat coûte des acheteurs."),
    Hypothese("L05", "L", "rondeau", "Annoncer un premier don fait donner plus de monde", +1,
              "part des lettres suivies d'un don, premier don annoncé contre témoin à même objectif ; permutation",
              "Dire (si c'est vrai) que d'autres ont déjà participé fait participer."),
    Hypothese("L06", "L", "rondeau", "Annoncer un premier don fait rapporter plus par lettre", +1,
              "don moyen par lettre envoyée, premier don annoncé contre témoin à même objectif ; permutation",
              "La preuve que d'autres ont payé rapporte de l'argent, pas seulement des gestes."),
    Hypothese("L07", "L", "rondeau", "Promettre de doubler chaque don fait donner plus de monde", +1,
              "part des lettres suivies d'un don, doublement promis contre témoin à même objectif ; permutation",
              "« Je double ton pourboire » fait-il payer ?"),
    Hypothese("L08", "L", "rondeau", "Annoncer un premier don fait mieux que promettre de doubler", +1,
              "part des lettres suivies d'un don, premier don annoncé contre doublement promis ; permutation",
              "Mieux vaut montrer que d'autres ont payé que promettre un bonus."),
    Hypothese("L09", "L", "rondeau", "Un objectif affiché plus bas change le nombre de donneurs", 0,
              "part des lettres suivies d'un don, objectif de 2 500 $ contre 5 000 $ ; permutation",
              "Afficher une petite ou une grande cagnotte ?"),
    Hypothese("L10", "L", "cai", "Le choix coché d'avance fait souscrire davantage", +1,
              "part qui souscrit, format « oui par défaut » contre « non par défaut » ; permutation des hameaux "
              "dans le village",
              "La case cochée d'avance : un levier puissant, et interdit pour un paiement."),
    Hypothese("L11", "L", "cai", "Une explication détaillée fait souscrire davantage", +1,
              "part qui souscrit, séance détaillée contre séance simple ; permutation dans le hameau",
              "Expliquer ce que le fan achète le fait acheter."),
    Hypothese("L12", "L", "gueguen", "Une blague avec l'addition fait laisser un pourboire", +1,
              "part des clients qui laissent un pourboire, carte avec une blague contre aucune carte ; permutation",
              "Un mot drôle au moment de demander rend la demande plus légère."),
    Hypothese("L13", "L", "gueguen", "La blague compte, pas seulement la carte", +1,
              "part des clients qui laissent un pourboire, carte avec une blague contre carte publicitaire ; "
              "permutation",
              "Ce n'est pas le papier qui fait payer, c'est le sourire."),
    Hypothese("L14", "L", "lynn", "Se mettre à hauteur des yeux fait laisser plus", +1,
              "pourboire en part de l'addition, serveur accroupi contre debout ; permutation dans le service "
              "(midi, soir)",
              "Parler au fan à sa hauteur, pas d'en haut."),
)


def par_id() -> dict[str, Hypothese]:
    return {h.id: h for h in H}
