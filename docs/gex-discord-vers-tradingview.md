# Des niveaux gamma Discord au graphique NQ

Note opérationnelle. Elle ne fait partie d'aucun des trois documents de
travail : elle ne mesure rien, elle ne porte aucune loi nulle, et elle n'en
revendique aucune. C'est une note d'outillage, au même titre que
`pine/alp0.pine`.

## La question

Un robot Discord répond à `!gex NDX` par une liste de niveaux gamma exprimés
en points d'**indice**. Le graphique est celui du **future**, NQ. Peut-on les
faire apparaître automatiquement sur TradingView ?

## La réponse courte

**Non, pas directement.** Pine Script n'a aucun accès réseau : aucune
fonction n'ouvre une URL, ne lit un webhook ni n'interroge une API. C'est une
propriété du langage, pas une limite de version, et elle ne se contourne pas.

Trois routes existent, et elles se classent sans ambiguïté.

## Route 1 — coller les niveaux dans l'indicateur *(cinq secondes par jour)*

`pine/alp0-gex.pine`. On colle la réponse du robot telle quelle dans une zone
de texte, une ligne par niveau ; l'indicateur fait le reste.

```
20450 = call wall
20200 = gamma flip
19980 = put wall
20310
```

L'étiquette est facultative, le séparateur peut être `=`, `:` ou `|`, les
lignes vides et celles commençant par `#` sont ignorées — la réponse du robot
se colle donc sans nettoyage.

**La conversion NDX → NQ est faite par l'indicateur, jamais à la main.** Il
lit `NASDAQ:NDX` en direct sur le même pas de temps, calcule la base
`NQ − NDX` et en prend la médiane sur trente barres. C'est la seule méthode
exacte : la base bouge de plusieurs dizaines de points selon le taux sans
risque, les dividendes attendus et l'échéance, elle change à chaque roll
trimestriel, et un niveau reporté sans elle est décalé de bien plus que la
distance qu'on prétend lire.

C'est la route à retenir. Elle demande une action manuelle par jour, elle
n'a aucune dépendance, et elle ne peut pas se désynchroniser.

## Route 2 — Pine Seeds *(automatique, mais lent à mettre en place)*

TradingView sait lire une série de données depuis un dépôt GitHub public, via
`request.seed()`. Le principe :

1. le robot écrit chaque jour un fichier CSV dans un dépôt public, au format
   `symbole, horodatage, valeur` que TradingView impose ;
2. on demande à TradingView d'enregistrer le dépôt comme source *Seeds* ;
3. l'indicateur lit la série avec `request.seed("seed_<dépôt>", "<symbole>", close)`.

Les limites tiennent à ce que Seeds est conçu pour des **séries temporelles**,
pas pour une liste de niveaux : il faut un symbole par niveau — `NDX_CALLWALL`,
`NDX_PUTWALL`, `NDX_FLIP` — chacun tenu à jour indépendamment. La résolution
est quotidienne. Et l'enregistrement du dépôt passe par une validation
manuelle de TradingView, dont le délai n'est pas garanti.

À faire si les niveaux doivent apparaître sans intervention et que le délai
de mise en place est acceptable. Pas pour demain matin.

## Route 3 — alertes webhook *(l'inverse du besoin)*

Les webhooks de TradingView vont **du** graphique **vers** Discord, jamais
l'inverse. Ils servent à faire prévenir le robot par le graphique, pas à
faire alimenter le graphique par le robot. Ils ne répondent pas à la question.

## La conversion, en détail

Le future cote au-dessus ou au-dessous de l'indice selon le coût de portage :

    NQ ≈ NDX · (1 + (r − q)·T/365)

où `r` est le taux sans risque, `q` le rendement de dividende attendu de
l'indice sur la période, et `T` le nombre de jours jusqu'à l'échéance. Les
trois bougent, et `T` tombe à zéro puis saute d'un trimestre à chaque roll.

**Ne calculez pas cette formule.** Mesurez la base :

    base = NQ − NDX, au même instant

C'est exact par construction, cela n'exige aucun paramètre, et cela survit au
roll sans qu'on ait à y penser. La base est stable à quelques points près à
l'intérieur d'une séance ; la médiane sur trente barres absorbe un print
d'indice en retard sans retarder le roll d'une séance.

Si `NASDAQ:NDX` n'est pas accessible sur votre abonnement, l'indicateur
accepte une base fixe : relevez `NQ − NDX` une fois à l'ouverture et
saisissez-la. À refaire chaque jour, et impérativement au roll.

## Coller l'export entier, sans le nettoyer

Un robot ne répond plus par trois lignes de prix : il répond par un document —
un en-tête, une section de niveaux, une liste de colonnes, un bloc CSV. Le
lecteur de l'indicateur avale ce document tel quel. Quatre règles y suffisent,
et chacune existe parce qu'un collage réel la demandait.

**Le sens de lecture est déduit.** `20450 = call wall` et `- **flip:** 29,280.00`
n'écrivent pas le prix du même côté du séparateur. On essaie le nombre à
gauche, puis à droite ; c'est le côté qui rend un nombre qui gagne.

**Le nombre se nettoie de ce qui le décore, jamais de ce qui le signe.** Les
séparateurs de milliers, les astérisques de gras, les accents graves, les
espaces et le dollar sortent ; **le tiret reste**, sans quoi un niveau négatif
deviendrait positif. C'est aussi ce qui fait qu'`0 dte` ne devient pas `0` :
les lettres ne sont pas retirées, donc la conversion échoue et la ligne tombe.

**Un titre `##` commute la lecture.** Hors de la section des niveaux, rien
n'est lu. C'est ce qui fait ignorer le bloc CSV et l'en-tête sans avoir à les
reconnaître — et si le collage ne porte aucun titre, tout se lit, donc la
liste nue continue de marcher.

**Un nombre hors de la fenêtre de plausibilité est refusé.** Un en-tête
transporte des millésimes, des comptes de lignes, des horizons : `22` et `0`
passeraient les trois règles précédentes. La fenêtre — un pour cent du prix
par défaut — les écarte, et elle est mesurée *avec et sans* la base, puisqu'on
ne sait pas encore de quelle échelle le niveau parle.

Enfin, **deux niveaux au même prix ne font qu'un trait**. Le cas est courant :
un mur d'appel et un mur de vente tombent souvent sur le même strike. Sans
fusion, deux intitulés se superposent illisiblement. Et la famille du trait
fusionné redevient neutre : un mur d'appel et un mur de vente sur le même
strike ne font pas un niveau d'appel, ils font un niveau dont la famille n'est
pas décidable.

`tools/gex_lecture_sim.py` est la transcription Python de cette boucle. Elle
n'est pas dans la chaîne des documents et ne prétend rien mesurer : elle sert à
vérifier qu'un collage donné rend les niveaux attendus **sans avoir à ouvrir
TradingView**, puisqu'aucun compilateur Pine n'est joignable depuis le dépôt.

### Le vocabulaire, et le préfixe qu'on n'écrit pas

Un robot écrit « call wall », un opérateur lit **CR**. La table de
correspondance est dans `codeDe`, en un seul endroit :

| code | nom | ce qui s'y range |
|---|---|---|
| `PS` | put support | put wall, put support, support |
| `CR` | call resistance | call wall, call resistance, resistance |
| `MP` | max pain | max pain |
| `GW` | gamma wall | gamma wall, major wall |
| `HVL` | gamma flip | flip, gamma flip, hvl |
| `RM` | résistance macro | tout ce qui porte « macro » |
| `R1` `R2` `S1` `S2` | supports et résistances secondaires | gardés tels quels |

**L'ordre des tests porte le sens.** « major wall » se range en `GW` avant que
« wall » ne le fasse basculer ailleurs ; « resistance macro » en `RM` avant
que « resistance » ne le prenne. Une table de correspondance dont l'ordre est
arbitraire finit par ranger le mauvais mot.

Le **préfixe d'échéance ne s'écrit pas à la main** : il se lit dans l'en-tête
de l'export. `- **horizon:** 0 dte` rend `0PS`, `0CR`, `0HVL`. C'est la seule
raison pour laquelle la section `## Context` est lue — tout le reste de
l'en-tête tombe.

Conséquence pratique : **coller deux exports d'échéances différentes à la
suite** donne `0CR` et `30CR` sur la même planche, chacun avec la sienne, sans
avoir à les distinguer à la main. Le préfixe se remet à zéro à chaque
`## Context` rencontré. Un code déjà préfixé dans le texte collé garde le
sien, et `RM` en est exempt : « macro » *est* son échéance, donc `30RM` dirait
deux fois la même chose et mal.

Deux zones au même prix ne font qu'un trait, et leurs codes se joignent :
`0CR/0PS`. C'est le cas courant — un mur d'appel et un mur de vente tombent
souvent sur le même strike.

### Les quatre zones que l'indicateur calcule

`PS CR MP GW HVL RM` viennent du robot : l'indicateur les reporte. **`R1 R2 S1
S2`, non — il les calcule**, à partir du bloc CSV du même collage, et c'est la
seule chose de ce fichier qui ne soit pas du report. Le panneau les compte
donc à part, et l'interrupteur qui les produit est nommé pour ce qu'il fait.

La règle tient en une phrase : *les plus fortes concentrations de gamma de
part et d'autre du prix, hors de celles qui portent déjà un nom.* Trois
décisions la précisent, et chacune se justifie.

**Le poids d'un strike est la somme des valeurs absolues de ses jambes.** Un
call et un put au même strike y concentrent tous les deux du gamma, et leurs
signes opposés ne doivent pas s'annuler — sans quoi un strike massivement
chargé des deux côtés passerait pour vide.

**Les colonnes se lisent dans l'en-tête du CSV**, jamais à une position
supposée : `strike` par son nom, la valeur par la première colonne dont le nom
porte `net`. L'ordre des colonnes est une donnée du fichier, pas une
convention.

**Le classement vient après tout le reste** — après la lecture entière, pour
que toutes les zones nommées soient déjà posées donc exclues quel que soit
l'ordre des sections ; et après que la base soit tranchée, parce que
« au-dessus du prix » n'a de sens qu'une fois les deux échelles ramenées à la
même.

Sur l'export du 14 septembre, un seul collage rend huit zones :

| | | |
|---|---|---|
| `0GW` | 29 290 | nommée |
| `0HVL` | 29 280 | nommée |
| `0CR/0PS` | 29 250 | nommées, fusionnées |
| `0R2` | 29 230 | calculée |
| `0R1` | 29 225 | calculée |
| `0S1` | 29 220 | calculée |
| `0S2` | 29 210 | calculée |
| `0MP` | 29 175 | nommée |

`0R1` tombe à 29 225 et non sur le plus gros call : le strike y porte 165 M de
gamma dont 160 côté put. *La concentration ne dit pas le sens, elle dit où le
prix a de la matière à traverser.*

### Un seul trait, gris foncé, continu

Les zones ne sont pas le sujet du graphique : ce sont des repères. Elles
partagent donc **un trait, une teinte, un style** — gris foncé, continu, une
épaisseur — et ce qui les distingue est leur **nom**, pas leur apparence. Le
trait part soixante barres à gauche du prix, pour qu'on voie ce que la zone a
déjà fait et pas seulement où elle est.

Vingt emplacements, contre douze auparavant : deux échéances collées à la
suite en occupent une quinzaine. Vingt est une limite dure, le nombre de
`plot` d'un script étant fixé à la compilation.

### L'échelle, mesurée et non supposée

Un robot qui publie « NDX » peut publier des strikes d'indice, ou des niveaux
déjà portés sur le future. Les deux se ressemblent : rien dans le texte ne les
distingue. Appliquer une base de cent points à des niveaux déjà convertis les
décale de cent points, et **rien dans la page ne le signalerait**.

L'indicateur ne devine donc pas. Il mesure la médiane des niveaux collés, la
compare au prix avec et sans la base, et publie les deux écarts :

    echelle  colles 29280.00  ·  ecart sans base 59.0  ·  avec 169.5

En mode automatique il retient le plus proche et écrit lequel dans l'en-tête
du panneau (`base 110.47 NON appliquée`). Les deux autres modes forcent la
décision, et le panneau continue de publier les deux écarts — de sorte qu'un
réglage forcé qui se trompe se lit sur la même ligne que le nombre qui le
contredit.

## Deux flux, deux retards — les trois mots qui portent tout

La ligne ci-dessus dit `base = NQ − NDX, **au même instant**`, et ces trois
mots sont la seule façon de se tromper sans le voir.

Un abonnement peut livrer le future en différé de quinze minutes et l'indice
autrement — en direct, ou en différé d'une autre durée. La soustraction compare
alors deux instants différents, et la base mesurée absorbe la dérive de l'indice
sur l'intervalle. Sur une matinée qui bouge, cela vaut des dizaines de points :
**exactement l'ordre de grandeur de la base elle-même**, et bien plus que la
distance que le niveau prétend marquer. Rien ne le signale. L'indicateur trace,
les niveaux ont l'air normaux, et ils sont tous décalés du même faux montant.

L'indicateur ne suppose donc aucun retard : **il le mesure**. À chaque barre il
demande à l'indice, en plus de son cours, l'horodatage de la barre dont ce cours
provient. Quand cet horodatage ne tombe pas sur celui de la barre du graphique,
les deux côtés de la soustraction ne parlent pas du même instant : la barre est
écartée et n'entre pas dans la base. La fenêtre compte donc des barres
**retenues**, pas des barres écoulées.

Le panneau publie de quoi vérifier, plutôt que de rassurer :

| ligne | ce qu'elle dit |
|---|---|
| `désalignement  0.0 barre` | l'écart d'horodatage mesuré. Positif : l'indice est en retard sur le future. Négatif : en avance. |
| `28/30 barres retenues` | combien de barres de la fenêtre ont passé le filtre. Une fenêtre qui se vide est un flux qui se désynchronise. |
| `base brute 246.10  écart +0.35 pt` | la base qu'on aurait obtenue **sans** le filtre, et son écart à la base alignée. Cet écart *est* le coût du décalage, en points. |
| `graphique retardé de 15.2 min` | le retard du flux lui-même, mesuré contre l'horloge murale. C'est la réponse chiffrée à « mon NQ est-il vraiment en retard ». |

Si aucune barre n'est alignée, la base n'est pas mesurable : le panneau le dit en
toutes lettres, passe en teinte d'alerte, et les niveaux se tracent **en
pointillé** pour qu'on ne les lise pas comme des niveaux mesurés. Publier un
nombre faux serait pire que ne rien publier.

### Ce que le retard ne casse pas, et ce qu'il casse

**Les niveaux restent justes.** La base est du portage, et elle se chiffre. À
NDX = 24 000, `r − q` = 2,8 % et soixante jours d'échéance, elle vaut 110 points
et dérive par deux canaux sur un quart d'heure : l'échéance qui raccourcit lui
prend **0,019 point**, et le niveau de l'indice lui en donne **0,18** si l'indice
bouge de quarante points. Deux dixièmes de point au total, contre un stop de
cinq. Une base mesurée sur des barres alignées d'il y a quinze minutes *est* la
base de maintenant, à la précision où on l'emploie.

**La colonne « distance au prix », non.** Elle compare un niveau au dernier prix
du graphique, et ce prix a quinze minutes. Sur NQ, quinze minutes valent
couramment vingt à quarante points : la distance affichée peut se tromper de
plus que la largeur du niveau. C'est pour cela que le panneau affiche le retard
au lieu de le taire — aucun indicateur ne peut rattraper une donnée qui n'est
pas encore arrivée.

Le réglage *Recaler l'indice de N barres* existe pour le seul cas où le panneau
annonce un désalignement **négatif** persistant, c'est-à-dire un indice en avance
sur le future. On y entre alors le nombre de barres que le panneau affiche. Dans
tous les autres cas il reste à zéro : décaler une série pour faire tomber un
chiffre à zéro, ce n'est pas aligner deux flux, c'est fabriquer l'alignement
qu'on cherchait à vérifier.

## Ce que ces niveaux valent

Rien dans cette note ne dit qu'un niveau gamma prédit quoi que ce soit. Le
document nº 1 mesure ce que l'exposition gamma peut produire, et sa
conclusion est négative : reproduire l'exposant d'échelle que la calibration
retient exigerait un gamma net d'un ordre de grandeur supérieur à tout gamma
observable sur un indice. Le gamma n'agit d'ailleurs que par un seul canal —
le temps de marché acheté, donc le seuil de rentabilité — et jamais sur
l'atteignabilité du target, qui ne dépend que de la géométrie.

Reporter un niveau proprement et croire qu'il prédit sont deux choses
différentes. Cet outil fait la première.
