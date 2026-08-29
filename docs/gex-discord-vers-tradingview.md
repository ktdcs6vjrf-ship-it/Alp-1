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
