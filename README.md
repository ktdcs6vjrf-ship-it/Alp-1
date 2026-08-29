# Alp-1

> **Temps de marché et péremption : invariance des règles d'arrêt,
> exposition, et durée de vie d'une dérive empruntée**
> *Série de documents de travail ALP, nº 1.* JEL : C12, C58, G11, G13, G14.

Le document complet :
[`docs/temps-de-marche-et-peremption.html`](docs/temps-de-marche-et-peremption.html) —
50 sections en neuf parties, 109 tables, 50 figures.

### Le second document

> **Le seuil, et non le signal : ce que l'opérateur discrétionnaire décide
> vraiment. Lois nulles, taxe de multiplicité et théorème d'arrêt optionnel**
> *Série ALP, nº 3.* JEL : C12, C44, C52, G11, G14.

[`docs/prouver-un-jugement.html`](docs/prouver-un-jugement.html) —
44 sections en douze parties, 17 tables, 34 figures.

Il part d'une question — combien de décisions faut-il pour établir la valeur
d'un jugement qui n'existe pas sous forme écrite ? — et la retourne. Le
théorème d'arrêt optionnel donne un seuil de rentabilité `µ* = c/E[τ∧T]` qui
ne dépend d'aucun signal : `µ` est une propriété du marché, `µ*` une propriété
de la géométrie, et l'opérateur la fixe entièrement. À la géométrie déclarée
ce seuil vaut 8,19 point par heure quand le domaine de dérive plausible
s'arrête à 3,2 — la rentabilité n'y est pas improbable, elle est
arithmétiquement impossible. Élargir le stop la déplace d'un facteur 53.

Deux parties récentes s'y ajoutent. **Lire le flux** passe le footprint et le
profil de marché au même protocole que le reste : chaque lecture reçoit sa loi
nulle, et le paramètre non observable dont cette loi dépend est nommé plutôt
que caché. **Le budget d'information** répond en bits à la question du bruit :
à la géométrie déclarée une décision doit porter 0,941 % d'un bit, donc le
marché peut être du bruit à 99,06 % — mais l'établir demande 474 décisions, et
la géométrie qui rend l'avantage facile à obtenir est celle qui le rend
difficile à prouver.

## Ce que contient ce dépôt

Une analyse **analytique**, sans donnée de marché. Elle délimite l'espace dans
lequel un edge peut exister pour cette stratégie et chiffre ce qu'il devrait
valoir ; elle n'établit pas qu'il existe. Aucun test empirique n'a été conduit.

Deux stratégies y sont comparées. **ALP-1** est la pile d'origine : sept
couches d'analyse, un stop serré, un objectif lointain, une remontée du stop
déclenchée par le carnet. **ALP-2** est la géométrie que le diagnostic finit
par désigner : aucun objectif, un stop posé sur la bande de bruit, une sortie
au marché à la clôture.

Le document se lit en neuf parties. La première définit les huit notions
nécessaires. La deuxième établit ce qu'une géométrie peut et ne peut pas. La
troisième passe les sept instruments au crible de leur loi nulle — GEX, profil
de volume, VWAP, théorie de Dow, Fibonacci, carnet d'ordres —, puis audite
l'hypothèse d'edge sous laquelle elle a chiffré ses propres résultats. Cette
hypothèse pose la dérive à deux fois le seuil de rentabilité, lequel est déduit
de la friction : l'espérance publiée vaut donc exactement le ratio de friction
et ne dit rien du marché. Le domaine de dérive que le document appelle plausible
tombe, lui, tout entier sous ce seuil. Un audit sépare alors — par un verdict
calculé, jamais écrit à la main — les trois grandeurs que le changement
d'hypothèse laisse intactes des dix qu'il emporte, dont trois jusqu'au
changement de signe. La quatrième
construit ALP-2 et la confronte à une dérive publiée et à une friction déduite
du carnet. La cinquième va chercher hors de la finance les bornes que le
théorème d'invariance laisse ouvertes. La sixième demande ce que le dehors
offre — un signal diffusé en direct, un catalogue de dérives publiées, un
opérateur discrétionnaire — et ce que chacun coûte. La septième refait tout
le travail sur la géométrie que l'opérateur pratique réellement — un stop de
cinq à dix millièmes de pour cent, une remontée au point mort, deux pour cent
du capital par tentative, et une répétition de l'entrée jusqu'à ce qu'elle
passe. La huitième recompose ces couches en une seule règle exécutable, et
chiffre ce que coûte chaque filtre de confluence en ratio de Sharpe avant de
décider lesquels garder. Le verdict note les deux approches sur une grille fixée d'avance, et
énonce ce qui manque.

## Le résultat structurant

Sous un prix sans dérive, l'espérance nette par trade vaut exactement `−c/L` —
la friction rapportée au risque nominal — quels que soient le placement des
barrières et la règle de gestion du stop. C'est le théorème d'arrêt optionnel :
toute règle d'arrêt laisse `−c` par aller-retour. Le taux de réussite affiché
est lui aussi invariant, et le ratio affiché sur le risque résiduel après
remontée du stop est compensé exactement par sa probabilité de réalisation.

## Le critère maître

Par l'identité de Wald, l'espérance nette d'un trade sous dérive `µ` vaut

```
E[résultat net] = µ · E[τ] − c
```

la dérive captée multipliée par la durée d'exposition, moins la friction. Toute
décision de géométrie — largeur du stop, éloignement du target, remontée du
stop, sortie à l'heure — n'agit que par l'exposition qu'elle produit. Il en
découle trois seuils :

| Grandeur | Forme fermée | Valeur au stop 0,010 % et R:R 1:20 |
|---|---|---|
| Dérive minimale rentable | `µ* = c/E[τ]` | 8,189 points d'indice par heure |
| Ratio d'information requis | `IR* = c/√(ab)` | 0,170 (0,298 en friction réaliste) |
| Lift relatif requis | `Δp/p₀ = c/L` | 55,0 %, **quel que soit le ratio visé** |

Un ratio gain/risque élevé n'assouplit pas l'exigence de qualité du signal : il
la déplace vers un événement plus rare. Ce qui baisse réellement, c'est
l'exigence en ratio d'information, parce que la position reste exposée plus
longtemps pour une même friction.

## Ce que la séance change à un 1:20 – 1:30

Un target à 1:20 sur un stop de 0,60 point est un déplacement de 12 points, soit
0,20 % de l'indice. Son atteignabilité dépend d'une propriété mesurable du
prix : la vitesse à laquelle sa dispersion croît avec l'horizon, `σ(T) = σ₁·T^H`.

| Ratio | Target | P(target) | Exposition |
|---|---|---|---|
| 1:20 | 12 pt | 4,76 % | 2,4 min |
| 1:30 | 18 pt | 3,23 % | 3,1 min |
| 1:50 | 30 pt | 1,96 % | 4,2 min |

À cette largeur de stop, la séance ne borne plus rien : le premier passage est
atteint en quelques minutes, la contrainte d'horizon cesse de mordre, et la
probabilité de touche rejoint sa valeur non contrainte `1/(R+1)`. C'est un
changement de nature du problème, et il est développé dans la septième partie :
ce n'est plus la durée de la séance qui limite, c'est la friction.

## La remontée du stop

Elle est neutre en espérance **si et seulement si** la dérive postérieure à la
confirmation est exactement nulle, et coûte dès qu'elle est positive — c'est-à-
dire précisément quand le signal fonctionne. Or le déclencheur retenu (mur de
liquidité protecteur, prise de liquidité favorable en L2) est, par la logique
qui le motive, un signal favorable.

**Reformulation proposée :** déclencher la remontée sur l'*invalidation* de la
confirmation — mur retiré avant d'être touché, absorption qui échoue, liquidité
prise du côté opposé. Même information, même endroit du carnet, signe inversé.

## Les sept couches, et leurs lois nulles

Chaque couche reçoit une définition calculatoire, la fréquence à laquelle son
motif se produit sur un prix **sans dérive**, et un prédicat testable. Cinq de
ces lois nulles ont une forme fermée sans paramètre, et elles sont sévères.

| Motif | Loi nulle | Valeur |
|---|---|---|
| Mèche haute ≥ k × corps | `1/(2k + 1)` | **un jour sur trois** à k = 1 |
| Clôture au-delà du corps de la veille | `3/8` de chaque côté | **trois jours sur quatre** |
| Nouveau sommet avant nouveau creux | `δ/(d + δ)` | fixé par la profondeur du repli seule |
| Retracement ≥ f avant continuation | `η/(f + η)` | 13,9 % au 0,618 |
| Séance passée au-delà de k σ du VWAP | `2·Φ(−k)` | 1,1 min par séance à 3 σ |

Un motif qui apparaît trois jours sur quatre sur une marche aléatoire ne devient
pas informatif parce qu'on l'a vu précéder trois hausses. Sans loi nulle, une
observation de marché n'a pas d'unité de mesure.

### Trois résultats nouveaux

**Un stop constant n'est pas un risque constant.** Le profil de volume est, à
vitesse d'échange stable, une estimation de la densité d'occupation du prix. Or
pour une diffusion, cette densité vaut `1/σ(x)²` : un LVN n'est pas un vide que
le prix comble, c'est un intervalle de volatilité locale élevée. Un stop de
0,010 % ne vaut que 0,7 écart-type local sur le POC et 0,5 sur un LVN, et la
probabilité d'être sorti par le bruit seul en trente minutes passe de 90 % à
93 %. La règle d'entrée de la pile privilégie précisément les LVN.

**La grille de Fibonacci paie quand le signal ne vaut rien.** À exposition
inchangée, l'écart d'espérance entre entrée en zone OTE et entrée au marché
vaut `Δ = −(1 − q)·E_marché` : attendre le retracement améliore l'espérance par
signal *si et seulement si* le signal exécuté au marché est perdant. Même forme
que le résultat sur la remontée du stop.

**Un signal de carnet ne peut pas financer un aller-retour.** L'information
d'un signal de flux a une demi-vie. Sur l'exposition de la géométrie retenue, un
signal de demi-vie trois secondes n'en conserve presque rien et exigerait 4,6
points de dérive par minute — 3,7 fois la volatilité — pour couvrir la
friction. La couche relève
de l'exécution, pas de la prédiction.

## Le régime de gamma, et ce que le contrôle de plausibilité révèle

Le signe du gamma net prédit une propriété de la variance et de
l'autocorrélation, non une direction. Le mécanisme se dérive jusqu'au bout :

```
Γ → λΓ → ρ = −λΓ/(1 + λΓ) → H = ½ + ln√((1+ρ)/(1−ρ))/ln T → P(target) → E[τ]
```

C'est le seul canal par lequel le gamma agit sur l'espérance. Inversée, la
relation devient un instrument de critique : reproduire l'exposant `H = 0,649`
retenu par le papier exigerait un gamma net de **−166 milliards de dollars par
1 %**, soit 42 % du volume quotidien du complexe indiciel — un ordre de grandeur
au-dessus de tout gamma observable, et à un cinquième du seuil où
l'autocorrélation atteint l'unité.

Conclusion, et elle va contre l'hypothèse : la persistance calibrée **ne peut
pas** être attribuée au régime de gamma. Le candidat suivant de la littérature
échoue pour une raison inverse et plus profonde. Le fractionnement des ordres
institutionnels engendre bien une mémoire longue du flux signé, mais le noyau
d'impact qui lui répond décroît selon l'exposant qui *restaure* exactement la
diffusivité : le mécanisme le mieux documenté de persistance du flux garantit
l'absence de persistance du prix. **Aucun mécanisme documenté ne soutient
l'exposant retenu**, et la géométrie doit donc être choisie robuste à cet
exposant plutôt qu'optimale en un point que personne n'a mesuré.

## Les instruments de validation, et le verdict qu'ils rendent

La troisième partie construit la loi du résultat d'un trade — quatre atomes qui
reproduisent *exactement* la moyenne et la variance du noyau —, puis lui impose
une dérive par inclinaison d'Esscher. L'edge de référence n'a pas de paramètre
libre : c'est `µ = 2µ*`, le double du seuil de rentabilité, ce qui donne par
construction `E[R] = c/L = 0,110 R`.

Sur cette hypothèse, les seize instruments concordent.

| Instrument | Résultat sur l'edge de référence |
|---|---|
| Sharpe annualisé | 1,96 |
| Sortino / Sharpe | 4,28 — un facteur que la **géométrie** fabrique, pas le signal |
| MinTRL | 278 trades, soit 0,6 an, pour affirmer que le Sharpe est positif |
| MinBTL après 100 essais | 840 trades, soit 1,7 an |
| Sharpe déflaté à 100 essais | 25,9 % |
| E[drawdown max] sur 1 an | 87 R, contre un gain annuel espéré de 277 R |
| Monte-Carlo, 4 000 années | une stratégie sans edge bat, une année sur vingt, le Sharpe **vrai** de celle qui en a un |
| Stress inversé | un choc de 2,78 % efface une année entière d'espérance |

Ces valeurs sont celles de la géométrie que l'opérateur pratique, et elles
**renversent** la conclusion que le document tirait d'un stop cinq fois plus
large. L'avantage de référence y vaut 0,550 R par trade et se démontre en une
demi-année ; le problème d'inférence disparaît presque entièrement. Ce qui le
remplace n'est pas plus doux, et la septième partie le chiffre : l'avantage
devenu facile à mesurer est devenu impossible à posséder.

**Trois résultats structurent la partie.**

*Le ratio de Sortino ne dit rien de plus que le Sharpe.* Leur rapport vaut
identiquement `σ/DD`, et sur une géométrie à stop fixe la dispersion à la baisse
est bornée par le stop. Le facteur vaut 4,54 à 1:20 et 5,9 à 1:50 : il croît
avec le ratio visé et ne contient aucune information sur le signal.

*Un drawdown record ne prouve rien.* Sans dérive, `E[MDD] = σ_R·√(πN/2)` croît
sans borne — c'est le théorème de Lévy, le processus de drawdown ayant la loi du
brownien réfléchi. Avec dérive, la croissance devient logarithmique et le
coefficient de Lundberg `θ*` borne la ruine. L'écart entre les deux lois, non le
niveau de l'une, est ce qui informe.

*Baum-Welch converge toujours.* Sur 120 points de bruit indépendant, un HMM à
deux états produit des régimes séparés de 1,87 écarts-types et un chemin de
Viterbi net. Rien dans la sortie du modèle ne signale l'imposture ; seul le ΔBIC
la démasque. Symétriquement, des régimes **réels** à séparabilité réaliste ne
franchissent le BIC que d'extrême justesse sur 750 observations.

## Le verdict

La question « la stratégie offre-t-elle un edge sans surajustement ? » admet une
réponse en trois propositions.

1. **Aucun instrument ne peut établir qu'un edge existe**, et ce n'est pas une
   limite des instruments : ce dépôt ne contient aucune donnée de marché.
2. **La difficulté change de face avec la largeur du stop, sans jamais
   disparaître.** Sur un stop large, l'avantage requis est minuscule et donc
   indiscernable du bruit avant une dizaine d'années. Sur le stop serré que
   l'opérateur pratique, il se mesure en une demi-année — mais il exige un
   ratio de Sharpe annualisé de 34, que personne ne possède. Le même mur, lu à
   deux abscisses de la même courbe.
3. **Il en découle une conclusion plus forte que la précaution habituelle sur le
   surajustement.** Là où l'avantage requis est petit, un bon backtest d'un an
   n'est pas une preuve faible : c'est une observation dont l'explication par
   défaut est la sélection. Là où il est grand, un bon backtest d'un an est une
   affirmation extraordinaire, et se traite comme telle.

La deuxième proposition porte sur un **instrument de mesure**, et c'est ce que
la partie suivante exploite : la durée d'une vérification n'est pas une
propriété de la stratégie.

| Levier | Effet |
|---|---|
| Fixer la configuration **avant** de regarder les données | gratuit, et le facteur reste le même quelle que soit la géométrie |
| Passer de 2 à 8 trades par séance | divise la durée par quatre, si la dérive survit à la multiplication des signaux |
| Augmenter l'amplitude de l'edge | à la géométrie serrée, `3,2 µ*` suffit à rendre l'edge déclarable en un an après cent essais |
| **Changer de dispositif de mesure** | **4,8 ans → 0,91 an** à niveau, puissance et hypothèse d'edge inchangés (section suivante) |

## Le protocole à horizon borné : décider en cinq ans

Un protocole de vérification a deux propriétés distinctes, et les confondre est
l'erreur qui rend un papier de stratégie inexploitable. Sa **validité** est la
fréquence à laquelle il conclut à tort. Sa **durée** est le temps de marché
qu'il faut lui donner pour qu'il conclue tout court. Les dix à vingt-cinq
années ci-dessus sont exactes pour le dispositif sur lequel elles sont
calculées — un marché, une entrée par séance, moyenne non pondérée, Bonferroni,
décision unique. Ce n'est pas une propriété de la stratégie.

Le protocole scellé atteint **la même validité en cinq années de données au
plus**, sans relever d'un point la dérive supposée. Cinq leviers, et chacun
nomme l'hypothèse qu'il exige.

| Levier | Facteur | Durée | Ce qu'il exige |
|---|---|---|---|
| Dispositif du document précédent | — | 4,8 ans | un marché, une entrée, Bonferroni, décision unique |
| Séquence fixée au lieu de Bonferroni | ×0,70 | 3,3 ans | un ordre déclaré avant les données ; aucune hypothèse de marché |
| Pondération GLS par la volatilité pré-entrée | ×0,61 | 2,0 ans | dérive constante en points par minute |
| Cadence : jusqu'à trois entrées par séance | ×0,93 | 1,9 an | la dérive survit aux entrées de rang 2 et 3 |
| Panel de cinq contrats, trois fuseaux | ×0,57 | 1,1 an | dérive commune au panel |
| Décision séquentielle, quatre examens | ×0,84 | **0,91 an** | aucune ; le maximum monte de 15,7 % |

**La statistique change de nature.** Ce qui est estimé n'est plus une moyenne
par trade mais la dérive nette **par unité d'exposition** :
`µ̂ = Σw·R / Σw·τ` avec `w = 1/σ̂²`, variance groupée par date. Deux trades de
dix minutes ne valent pas un trade de vingt, et les compter comme deux
observations d'une moyenne jette une part de l'échantillon.

**Les examens sont jalonnés en information, pas en calendrier.** Ils tombent
quand `1/Var(µ̂)` franchit une fraction pré-enregistrée du budget. Conséquence
décisive : la corrélation entre marchés, la cadence et la persistance de la
volatilité déplacent la *date* des examens, jamais leurs seuils. **Aucune
hypothèse de calibration n'entre dans le taux d'erreur du protocole.**

### Ce que cinq années tranchent

Le protocole ne se donne pas une taille d'échantillon puis un calendrier : il
se donne un budget de temps de marché — 1 260 séances — et en déduit ce qu'il
peut trancher. Sous cette contrainte, une dérive et une seule est détectable à
80 % de puissance, et elle est publiée.

| | Valeur |
|---|---|
| Dérive minimale détectable, viabilité | **3,68 points de base captés** |
| Décote absorbée sur la dérive empruntée | 39 % |
| Durée médiane du verdict, hypothèse empruntée | **2,02 ans** |
| Puissance à l'hypothèse empruntée | 0,999 |
| Horizon épuisé sans conclure | 0,000 |

C'est ce chiffre qui rend un *échec* du protocole informatif : ne pas rejeter
au terme des cinq années exclut, à 80 % de puissance, toute dérive supérieure à
3,68 points de base. Un protocole qui ne publie pas sa dérive minimale
détectable ne peut rien conclure de son propre silence.

### Le Monte-Carlo porte sur la procédure, pas sur la stratégie

La simulation ne demande pas ce que la stratégie produit. Elle demande à quelle
fréquence le protocole se trompe. Trois étages : la séance minute par minute
(saisonnalité en U, volatilité lognormale, sauts, bande estimée sur 14 séances
donc entachée d'erreur, stop surveillé en continu par pont brownien,
ré-armement) ; les cinq contrats d'une date noués par une copule à blocs ; puis
le protocole rejoué examen par examen, 1 500 fois par point.

| Contrôle | Mesuré | Attendu |
|---|---|---|
| Taille sous H₀ | **0,046 ± 0,005** | 0,05 |
| Puissance à θ₁ | **0,827** | 0,80 |
| Arrêt optionnel sur le marché simulé | z = −0,67 | 0 |
| Information par date, prévue / mesurée | 47,7 / 50,9 | écart prudent |
| Exposition réalisée / forme fermée | 136,7 / 163,4 min | la forme fermée surestime |
| Taille selon ρ ∈ [0,50 ; 0,95] | 0,043 – 0,046 | plate |
| Durée médiane selon ρ | 2,46 → 3,34 ans | c'est elle qui bouge |

**Ce qui met la mesure à l'abri du surajustement**, et il faut l'énoncer :
aucun réglage n'est choisi au vu de la sortie ; la taille est publiée à côté de
la puissance, de sorte qu'un levier ajusté en cachette se paierait en taille ;
la dérive n'est jamais estimée mais **imposée** ; les frontières viennent d'une
fonction de dépense publiée ; les graines sont explicites.

Le dernier contrôle ne porte pas sur un calcul mais sur une pratique. À données
identiques et procédure identique, lire la famille de trois configurations dans
l'ordre scellé donne un taux d'erreur de **0,046** ; la lire par son meilleur
élément le porte à **0,107**. Seul l'ordre de lecture change.

### Ce que le protocole ne tranche pas

Le panel n'est pas un ornement : à information maximale scellée, un marché
unique n'atteint pas son dernier examen 53 % du temps sous l'hypothèse
empruntée — il ne conclut pas, faute de temps de marché et non faute de dérive.
Trois contrats suffisent pour cette hypothèse-là (0,995 de puissance), les cinq
pour sa version décotée.

Et la limite se dit sans l'adoucir. Le protocole absorbe une décote de 39 % ;
la décote documentée est plus forte. La dérive reste au-dessus du seuil de
**détectabilité** seulement si son taux de décroissance annuel est inférieur à
**6,1 %/an**, contre **17,4 %** documentés. Datée du travail de 2018, elle est
passée sous ce seuil en 2021 ; datée de sa généralisation, en 2024. Ce n'est
pas le protocole qui est trop lent : c'est la question qui a peut-être cessé
d'être décidable — et le protocole est ce qui permet de le dire plutôt que de
le supposer.

## Deux corrections, et une échéance

Le document porte deux résultats que ni ALP-1 ni ALP-2 ne contenaient, et qui
touchent tous deux à la solidité de la conclusion plutôt qu'à sa portée.

**La dérive est empruntée, et elle se déprécie.** Elle n'a pas été mesurée ici :
elle vient de travaux publiés en 2018 et 2021. McLean et Pontiff mesurent sur
97 anomalies une décote post-publication d'environ 58 %. Appliquée à cette
dérive, elle donne deux nombres opposés.

| | Sans décote | Datée de 2018 | Datée de 2021 |
|---|---|---|---|
| Dérive restante en 2026 | 6,00 pdb | **1,50 pdb** | 2,52 pdb |
| Marge sur le point de rupture (1,16 pdb) | 5,17× | **1,29×** | 2,17× |
| Année de bascule | — | **2027** | 2030 |

Le rassurant : la conclusion survit à une décote de **80,7 %**, contre 58 %
documentés. Le reste : le taux qui la fait basculer, 0,205 par an, tombe *à
l'intérieur* de la boîte de plausibilité. L'absence de mesure n'est donc plus
une lacune de complétude qu'on comble quand l'occasion se présente — **c'est une
échéance**, entre dix-huit mois et quatre ans selon la date qu'on retient.

**L'exposant d'échelle était posé deux fois, à deux valeurs.** La calibration le
fixe à ½ par `σ₁ = D/√T` ; la discussion du gamma en retient 0,65. Refaite sous
exposant imposé, la chaîne complète — volatilité, bande, stop, exposition, seuil
— montre que l'incohérence joue **contre** la stratégie : le seuil requis monte
d'un facteur 1,112 et la probabilité d'arrêt passe de 66,2 % à 71,5 %. La
persistance invoquée pour rendre les targets atteignables les rend aussi plus
coûteux à atteindre, et le second effet domine parce que le target n'est presque
jamais touché.

Évaluée au pire cas sur la boîte d'exposant, la géométrie désigne une entrée à
**120 minutes** plutôt qu'à 90 : exposition de 172,2 minutes au lieu de 165,6,
et 3,8 % de moins sur la dérive requise. L'écart est modeste et gratuit. Mais
90 minutes figurent dans l'empreinte scellée : la corriger n'est légitime que
**tant qu'aucune série de prix n'a été ouverte**, ce qui est encore le cas.

## Deux mesures que le document annonçait sans savoir les faire

Un audit du dépôt a relevé que `docs/donnees-requises.md` annonce un Test 1 qui
« mesure l'exposant d'échelle par ratio de variance », et qu'aucun ratio de
variance n'existait dans le code : `scaling.calibrate` recevait l'exposant en
argument, et le Test 1 de la chaîne comptait des cassures de bande. Le même
audit a relevé que `scan_session` documente lui-même son optimisme — « un stop
touché à l'intérieur d'une barre est exécuté au niveau du stop ». Les deux
manques sont comblés, et chacun produit un résultat.

### `alp1/varratio.py` — la loi d'échelle, mesurée

Ratio de variance de Lo et MacKinlay à fenêtres chevauchantes, statistique
robuste à l'hétéroscédasticité, exposant par `Ĥ = ½ + ln VR(q)/(2 ln q)` et par
régression de `ln Var(q)` sur `ln q`. Aucun rendement n'enjambe un gap de nuit
ni un trou : les séances sont traitées séparément et les sommes agrégées.

**Le résultat n'était pas prévu.** Sur des séances de 390 minutes, l'estimateur
est biaisé vers le haut à échantillon fini, et la statistique asymptotique de
Lo-MacKinlay **rejette la marche aléatoire sur une marche aléatoire** — à tous
les horizons de la grille.

| q | VR(q) | VR sous marche aléatoire | Ĥ brut | Ĥ corrigé | z asympt. | z nul |
|---|---|---|---|---|---|---|
| 2 | 1,0078 | 1,0054 | 0,5056 | **0,5018** | 2,46 | 1,28 |
| 10 | 1,0298 | 1,0295 | 0,5064 | **0,5001** | 2,76 | 0,03 |
| 30 | 1,0982 | 1,0939 | 0,5138 | **0,5006** | 5,00 | 0,22 |
| 60 | 1,2225 | 1,2010 | 0,5245 | **0,5022** | 8,00 | 0,57 |

La régression brute rend `Ĥ = 0,5208` sur une série qui est une martingale par
construction ; corrigée de la loi nulle simulée de l'estimateur, `Ĥ = 0,5014`.
Un Test 1 conduit avec la statistique du manuel aurait donc conclu à la
persistance — c'est-à-dire précisément à ce dont la calibration a besoin.
Le module applique à son propre estimateur la règle que le document impose
partout ailleurs : rapporter un motif à sa fréquence sous un prix sans dérive.

```bash
python main.py --hurst [f.csv]
```

### `alp1/measure.py` — l'encadrement par remplissage du stop

`scan_session` accepte désormais `fill="stop"` (le protocole, optimiste) ou
`fill="extreme"` (remplissage au plus bas de la barre à l'achat, au plus haut à
la vente — le pire compatible avec ce qu'on observe). `bounds()` rejoue la
mesure sous les deux.

**L'écart n'est pas de second ordre.** Sur 250 séances sans dérive :

| | Espérance nette | SR/trade |
|---|---|---|
| Remplissage au stop | **+0,4500 pt** | +0,0132 |
| Remplissage à l'extrême | **−0,6925 pt** | −0,0200 |

Écart de 1,14 point, soit 254 % de la borne optimiste. Deux lectures, et il
faut les séparer.

Ce qui **se généralise** : la largeur de la bande. Sur six tirages, l'écart va
de 0,96 à 1,34 point — toujours davantage que la friction (0,53 pt) que la
mesure cherche à franchir. L'hypothèse d'exécution pèse donc plus lourd que la
grandeur mesurée, à chaque tirage.

Ce qui **dépend de l'échantillon** : le renversement de signe. Sur le tirage
ci-dessus l'espérance passe de positive à négative selon le remplissage ; sur
six tirages cela arrive deux fois. Mais dès que la vraie espérance tombe dans
la bande — et la bande est plus large que la friction — c'est l'hypothèse
d'exécution qui décide du signe, non le marché. Publier la borne optimiste
seule reviendrait à présenter une hypothèse comme une mesure.

La lecture est binaire : deux bornes du même côté de zéro, la conclusion tient ;
un zéro entre les deux, **la mesure sur barres ne conclut pas** et il faut du
tick.

```bash
python main.py --bounds [f.csv]
```

## Trois bornes venues d'ailleurs

Le théorème d'invariance dit ce qu'une géométrie ne peut pas faire. Trois
disciplines étrangères à la finance donnent les bornes symétriques. Le critère
de sélection est strict : **un domaine n'entre que s'il produit une borne** —
un énoncé de la forme « aucune stratégie ne dépasse ceci » — et non un
indicateur de plus. Un indicateur s'ajoute au budget de configurations et
relève le seuil de sélection ; une borne le contraint sans rien coûter.

### `alp1/entropy.py` — le plafond d'information

Kelly établit en 1956 que le taux de croissance logarithmique maximal d'un
pari répété **vaut** l'information mutuelle entre signal et issue. Pas une
approximation : une égalité. Déplacer le taux de réussite de sa valeur
martingale à sa valeur rentable coûte la divergence de Kullback-Leibler entre
les deux lois, et rien ne contourne ce prix.

| Géométrie | Bits requis par trade | Trades pour décider |
|---|---|---|
| ALP-1, `c/L` = 55,0 % | 9 407 × 10⁻⁶ | 474 |
| ALP-2, `c/L` = 1,43 % | **7 × 10⁻⁶** | 607 412 |

La géométrie divise l'exigence par **1 281**. Mais le même facteur multiplie
l'échantillon qui la décide : ce qu'elle rend facile à obtenir, elle le rend
difficile à prouver — et réciproquement, ce que le stop serré rend
démontrable, il le rend inatteignable. C'est la même identité, lue dans les
deux sens.

**Trois routes, un seul mur.** Le test t sur l'espérance demande 812 trades,
le seuil de sélection déflaté 288, le test de vraisemblance sur la direction
474. Aucune prémisse commune, un rapport de trois à un : la marque d'une
limite structurelle plutôt que d'un artefact de méthode.

**Le seul gain exploitable de tout ce travail** : lire la direction plutôt que
l'espérance économise **42 % des trades** à décision égale. Le Test 2 moyenne
des déplacements, donc paie le bruit d'amplitude ; un test sur le seul signe
ne le paie pas.

```bash
python main.py --hurst f.csv   # loi d'échelle
```

### `alp1/nonlinear.py` — entropie de permutation et DFA

Le ratio de variance ne détecte que l'autocorrélation linéaire. Deux
instruments construits hors de la finance comblent l'angle mort, sur les
**mêmes barres d'une minute** — coût de données nul.

- **Entropie de permutation** (Bandt et Pompe, 2002 — dynamique non linéaire,
  électroencéphalographie). N'examine pas les valeurs mais leur *ordre*.
  Aucune loi, aucune stationnarité, invariante par transformation monotone.
  Répond à « reste-t-il une structure exploitable ? » avant qu'aucun signal ne
  soit construit.
- **Fluctuations redressées** (Peng et al., 1994 — physiologie, rythme
  cardiaque et séquences d'ADN). Retranche la tendance locale de chaque
  fenêtre avant de mesurer.

**La méthode issue de la physiologie bat celle issue de la finance sur le
problème financier.** Sur une martingale, le ratio de variance affiche 0,5208
quand la vérité est un demi ; les fluctuations redressées affichent 0,5052.
Biais divisé par 3,5.

### `alp1/discipline.py` — le facteur humain, rendu décidable

Rien de ce qu'un opérateur *est* ne crée de dérive : le théorème d'invariance
l'interdit. Ce que son état décide est s'il **exécute la règle scellée**.

Or une dérogation n'est pas une erreur de plus dans l'échantillon : c'est un
choix binaire pris en regardant le marché, donc une configuration explorée de
plus. La famille double à chaque fois, et le seuil de sélection suit.

> **Quatre dérogations suffisent à détruire la valeur probante des 7 012 trades
> du protocole.** Une tous les 1 757 trades, soit environ une par an et demi.

C'est le seul paramètre du document entièrement sous le contrôle de
l'opérateur. Lo et Repin, Coates et Herbert documentent ce qui *fait varier ce
taux* — cortisol, série de pertes, privation de sommeil. Ils ne documentent
aucune dérive de prix, et le document ne leur en fait pas dire.

### Le résultat qui unifie les trois

| Instrument | Plancher de bruit | Rapport à l'exigence d'ALP-2 |
|---|---|---|
| Entropie de permutation, d = 3 | 17,5 × 10⁻⁶ | **2×** |
| Entropie de permutation, d = 4 | 137 × 10⁻⁶ | **19×** |
| Information mutuelle, 1 000 obs. | 864 × 10⁻⁶ | **118×** |

Chaque plancher est ce que l'instrument affiche sur une série où il n'y a
**rien**. Tous dépassent l'information qu'ALP-2 réclame. Ce n'est pas que
l'avantage recherché y soit petit : **il est plus petit que le bruit propre
des appareils censés le voir.** Sur la géométrie serrée, le rapport s'inverse
et les instruments voient largement l'avantage requis — mais c'est parce que
cet avantage est devenu si grand qu'il n'existe pas. C'est l'explication du mur, et elle dit
pourquoi il est structurel.

## Ce que le dehors offre, et ce qu'il coûte

Trois questions qu'un opérateur pose avant d'engager du capital, et auxquelles
rien de ce qui précède ne répondait. Un signal diffusé en direct vaut-il
quelque chose à l'instant où on le reçoit ? La littérature offre-t-elle
d'autres dérives que celle qui est empruntée, et combien peut-on en assembler ?
Un talent discrétionnaire qui ne se formule pas peut-il malgré tout se mesurer ?

### `alp1/broadcast.py` — le signal diffusé, et ce que le trajet lui prend

Un signal a une demi-vie ; un direct a un délai — encodage, mémoire tampon,
distribution, réaction humaine. La dérive captée par un receveur en retard de
`Δ` vaut la dérive captée sans latence **multipliée par `2^(−Δ/h)`** : le
retard ne déforme pas le profil de décroissance, il l'atténue d'un facteur qui
ne dépend que du rapport de deux durées. D'où une frontière en forme fermée,
`h* = Δ·ln 2 / ln(µ/µ*)`, et une égalité commode : à dérive double du seuil,
la demi-vie minimale du signal **égale le délai**.

| Nature du signal | Demi-vie | Δ = 3 s | Δ = 10 s | Δ = 30 s |
|---|---|---|---|---|
| flux de carnet | 3 s | 50,0 % | **9,9 %** | 0,1 % |
| motif d'une barre | 60 s | 96,6 % | 89,1 % | 70,7 % |
| motif de séance | 1 800 s | 99,9 % | 99,6 % | 98,8 % |

**La lecture de flux ne se recopie pas**, et le résultat rejoint par une autre
route celui de la couche de carnet : ce qui n'était pas transportable dans le
temps ne l'est pas davantage dans l'espace. **Ce qui se recopie est ce qui
n'avait pas besoin d'être diffusé** : un motif dont la demi-vie se compte en
dizaines de minutes est, par construction, un motif que le spectateur pouvait
voir sur ses propres barres.

Deux bornes achèvent la couche, et elles portent sur la collecte plutôt que
sur le signal.

**Le classement fabrique le talent qu'on y cherche.** Chercher « le bon
diffuseur » parmi K candidats est une sélection sur K configurations. Sur deux
cents appels chacun et *aucun* talent, le meilleur d'une centaine de diffuseurs
affiche **58,9 %** de réussite. Établir un avantage réel de cinq points au rang
où un diffuseur est lu parmi cinquante demande **1 543 appels enregistrés**,
soit une année et demie de collecte à cinq appels par direct.

**Un historique reconstitué n'est pas un échantillon.** Si une fraction `d` des
appels perdants ne survit pas au récapitulatif, le taux affiché vaut
`p₀ / [p₀ + (1 − p₀)(1 − d)]`. La relation s'inverse, et le nombre qu'elle rend
est petit : **un appel perdant effacé sur dix suffit à fabriquer l'intégralité
de l'avantage que la géométrie 1:20 exige.** Aucune intention n'est supposée —
un direct interrompu et un effacement délibéré ont la même arithmétique. Seule
une collecte prospective, horodatée à la réception, est donc recevable, et
c'est la seule que le dépôt implémente.

Il reste une lecture recevable, et ce n'est pas celle qu'on cherchait. Ce qu'un
direct mesure de façon fiable n'est pas une prévision de prix mais une
**attention datée**. Le cadre range cette grandeur du côté de la capacité et de
la friction, non de la dérive — et Barber, Huang, Odean et Schwarz (2022)
documentent que les épisodes d'attention retail extrême sont suivis de
rendements *négatifs*. Le témoin, s'il informe, informe à contre-pied. Les taux
de base publiés par Kakhbod, Kazempour, Livdan et Schürhoff (2023) vont dans le
même sens : **28 %** de talent contre **56 %** de talent négatif, de sorte
qu'un filtre de contre-pied retient 58 % de sujets en plus avec une loi a
posteriori plus pure — 92,1 % contre 84,1 %.

```bash
python main.py --tape <pseudo>    # enregistre un direct, une frappe par appel
python main.py --diffuseur f.csv  # évalue le registre collecté
```

### `alp1/litedge.py` — neuf dérives publiées, passées au critère maître

Un effet n'entre pas parce qu'il est célèbre : il entre si `cadence · [µ ·
min(exposition, horizon) − c]` est positif après décote, et si son mandat, son
instrument et son coût de données sont compatibles avec la géométrie. Quatre
portes, et le résultat est négatif.

| Porte | Restants |
|---|---|
| Documenté, taille d'effet publiée | 9 |
| Mandat : sortie au marché à la clôture | 4 |
| Coût : accessible à un opérateur de détail | 3 |
| Familles distinctes après regroupement | **1** |

Les trois entrées qui survivent sont **trois énoncés d'un même effet**, et la
corrélation entre deux publications d'un même résultat vaut un. Le catalogue
ouvert met à disposition de cette géométrie une pièce, et c'est celle que le
document emprunte déjà.

**Deux résultats corrigent le document au passage.**

*Les constantes de temps doivent s'apparier.* Une exposition plus longue
n'achète de la dérive que sur un effet plus long qu'elle. Sur le momentum
intraséance, d'horizon trente minutes, les 165 minutes d'ALP-2 ne captent que
**1,04** fois ce que captent les vingt-neuf d'ALP-1 ; sur un effet de trois
heures, **5,7** fois plus. L'avantage d'exposition d'ALP-2 n'est donc pas
acquis contre n'importe quelle dérive.

*La convention de datation de la décote était un paramètre libre non déclaré.*
Un effet se déprécie depuis sa **première** parution, non depuis chacune de ses
republications : l'arbitrage répond à la première. Retenir l'autre convention
multiplierait la dérive restante par **2,83** sur le même effet — davantage que
la marge que le document conserve sur son point de rupture. La convention
retenue ici est la plus sévère, et c'est elle qui avance l'échéance.

### L'assemblage, et son nombre optimal de pièces

Combiner k signaux indépendants de ratio d'information i donne `i·√k` ; mais
estimer un poids coûte `1/N` en ratio d'information au carré. D'où un critère
d'entrée d'une simplicité inattendue :

> **Une pièce mérite sa place si et seulement si son ratio d'information
> dépasse `1/√N`.** Ni le nombre de pièces déjà retenues, ni leur qualité, ni
> leur corrélation n'entrent dans le critère.

| | Valeur |
|---|---|
| IR par occurrence de l'unique pièce compatible | 0,01269 |
| Seuil sur les 7 012 trades du protocole scellé | 0,01194 — franchi d'un cheveu |
| Seuil sur le budget de 1 260 séances | 0,02817 — non franchi |
| Information conservée après ajustement d'un poids | **33,8 %** |
| Seuil imposé par la fouille du catalogue | 0,0199, soit **1,6 fois** ce que la pièce porte |

Deux lectures s'opposent proprement. Sur un jeu déclaré d'avance, une seule
pièce est optimale et elle conserve un tiers de son information. Sur un jeu
choisi au vu des données, **la fouille coûte plus cher que le catalogue entier
ne contient** — prendre tout, en revanche, ne coûte rien, parce que prendre
tout n'est pas un choix. C'est le résultat de la discipline anti-surajustement,
retrouvé sur un autre objet.

### `alp1/discret.py` — l'edge discrétionnaire, rendu décidable sans être expliqué

Le théorème d'invariance interdit qu'une règle d'arrêt crée de l'espérance. Il
ne dit rien de la *sélection des moments*. Le critère maître se décompose :

```
E[R] = E[µ_t · τ_t] − c = E[µ]·E[τ] + Cov(µ, τ) − c
```

et le premier terme est ce que la règle scellée obtient déjà. **Tout l'écart
tient dans la covariance entre la dérive locale et l'exposition choisie.**
C'est l'énoncé exact de ce qu'un talent discrétionnaire peut être ici, et il a
deux conséquences opposées : le talent est mesurable **sans être décrit**, et
il est borné par ce que la dérive vaut. Un talent ne fabrique pas de dérive ;
il en répartit une.

**Le dispositif : apparier plutôt que comparer.** La différence entre le bras
opérateur et le bras règle, sur les mêmes séances, a pour variance
`2σ²(1 − ρ)` ; le gain d'échantillon vaut `1/(1 − ρ)`, soit cinq à
`ρ = 0,80`. À corrélation moyenne, **276 séances — une année — suffisent** à
trancher un écart de cinq centièmes de risque par trade.

Le second avantage pèse davantage que le premier. **La dérive commune
s'élimine dans la différence** : le dispositif ne repose sur aucune dérive
publiée, donc sur aucune décote. Le document date sa propre péremption entre
2027 et 2030 ; la question « cet opérateur fait-il mieux que sa règle ? » n'en
a pas. C'est la seule question du dépôt qui reste décidable après l'échéance.

**Et le même geste change de prix selon la date à laquelle il est déclaré.**
Une dérogation prise en regardant le marché double la famille de
configurations — quatre suffisent à détruire la valeur probante du protocole.
Le même écart, déclaré d'avance comme un second bras, coûte une comparaison :
un facteur **48** à quatre écarts. La différence entre un talent et une
indiscipline n'est pas dans le geste, elle est dans la date à laquelle il a été
déclaré.

```bash
python main.py --edge             # les trois bornes, en quinze tables
```

## La géométrie réellement pratiquée

Les parties qui précèdent raisonnaient sur un stop de cinq centièmes de pour
cent. L'opérateur en déclare un de **cinq à dix millièmes**, une remontée au
point mort, deux pour cent du capital par tentative, et une pratique de
répétition de l'entrée jusqu'à ce qu'elle passe. Le dépôt refait sur cette
géométrie tout ce qu'il faisait sur l'autre. Aucune conclusion qualitative ne
change — c'est la marque d'un cadre qui tient — mais chaque quantité change
d'ordre de grandeur, et trois résultats apparaissent qui n'existaient pas à
l'ancienne largeur.

### `alp1/forcing.py` — un stop se juge en ticks, jamais en pourcentage

Sur un indice à 6 000 points, un stop de 0,010 % vaut 0,60 point, soit **2,4
ticks** d'un contrat E-mini ; la friction d'un aller-retour en vaut 1,3. Le
premier verdict ne porte donc sur aucun signal.

| Contrat | Stop (ticks) | Friction (ticks) | `c/L` | Viable |
|---|---|---|---|---|
| ES | 2,40 | 1,32 | 0,550 | oui |
| NQ | 8,80 | 1,80 | **0,205** | oui |
| MES | 2,40 | 4,20 | 1,750 | **non** |
| MNQ | 8,80 | 9,00 | 1,023 | **non** |

Sur les deux contrats micro, l'aller-retour coûte plus cher que le risque
nominal : la position est perdue à l'ouverture, avant que le marché n'ait
bougé. Sur le contrat du Nasdaq, dont le tick est fin relativement au niveau
auquel il cote, la même largeur laisse `c/L` à un cinquième. **À cette largeur
de stop, le choix du contrat pèse plus lourd que le choix du signal**, et c'est
une décision qui se prend une fois, gratuitement.

**Le point mort n'est pas mort.** La friction est due dans toutes les issues,
sortie au point mort comprise : une sortie à BE coûte exactement `c/L`, soit
**−0,55 R** à 0,010 % et **−1,10 R** à 0,005 %. À la largeur la plus serrée,
sortir au point mort coûte plus cher qu'un stop entier n'en coûtait à
l'ancienne calibration. Et comme un journal de trading retire les sorties à BE
du dénominateur du taux de réussite, c'est l'issue la plus fréquente et la plus
coûteuse qui disparaît des statistiques tenues.

**Le spread prend sa part avant que le prix ne bouge.** Dans le modèle de Roll
(1984), le prix observé oscille entre bid et ask autour d'un prix efficient
inchangé : on entre à l'ask, on est stoppé quand le bid touche le niveau, et le
stop utile n'est donc pas `L` mais `L − s`.

| Stop | Points | Stop utile | Part prise par le spread | Sorti par le bruit en 1 min |
|---|---|---|---|---|
| 0,005 % | 0,30 | 0,05 | 83 % | **96,8 %** |
| 0,010 % | 0,60 | 0,35 | 42 % | **77,9 %** |
| 0,050 % | 3,00 | 2,75 | 8 % | 2,8 % |

Une série de cinq à six échecs consécutifs ne demande, à cette géométrie,
aucune explication de marché : **elle est produite par le bruit de cotation
seul.** Osler (2003, 2005) ajoute la conséquence pratique : les ordres stop se
groupent juste au-delà des niveaux ronds et le prix y passe par cascades. Un
stop de deux ticks posé sur un niveau visible est dans le bruit *à l'endroit
précis où le marché va chercher de la liquidité*.

### Le théorème du forçage

Chaque tentative est un premier passage : stop `L`, target `R·L`, friction `c`.
Sous un prix sans dérive, la probabilité de toucher le target vaut `1/(R+1)`,
le nombre de tentatives jusqu'à la première réussite suit une loi géométrique
de moyenne `R+1`, et le résultat total attendu vaut

```
E[forçage] = R·L − R·L − (R+1)·c = −(R+1)·c
```

Le gain de l'unique réussite et les `R` échecs qui l'ont précédée s'annulent
**exactement**. Ce n'est pas un arrondi : c'est le théorème d'arrêt optionnel,
appliqué à une règle d'arrêt posée sur la *suite des trades* plutôt que sur le
trajet du prix. **Il n'y a donc rien à optimiser dans la façon de forcer** —
attendre un retracement de plus, resserrer la troisième tentative, doubler sur
la quatrième sont toutes des règles d'arrêt, et le théorème les couvre toutes.
Ce qui reste est la friction, payée 21 fois pour un seul aboutissement : **−11,55 R**
à 0,010 %, **−23,10 R** à 0,005 %.

**La série d'échecs n'est pas de la malchance.** À un ratio de 1:20, six échecs
consécutifs surviennent avec probabilité **74,6 %**. L'opérateur qui en observe
cinq ou six n'a pas subi un accident : il a observé la médiane de sa propre
géométrie. Sur deux cents tentatives, la plus longue série *attendue* vaut 46.

**Et la persistance ne sauve pas le forçage — c'est une proposition, non une
mesure.** Kaminski et Lo (2014) établissent que sous marche aléatoire une règle
de stop simple *diminue toujours* l'espérance, et qu'en présence de momentum
elle peut en ajouter. Il serait tentant d'en conclure qu'un exposant d'échelle
supérieur à un demi suffirait. C'est faux : un changement d'exposant est un
changement de temps déterministe, qui ne modifie pas le rapport des
probabilités de premier passage. Celle-ci reste bornée par `1/(R+1)` à tout
exposant, là où la rentabilité en exige davantage. Le momentum qui rend une
règle de stop utile n'est pas une propriété d'échelle mais une dérive
conditionnelle : **espérer que la persistance sauve le forçage revient à
espérer la mauvaise grandeur.**

### Le levier n'est pas un choix séparé

Risquer 2 % du capital sur un déplacement de prix de 0,010 % **impose** une
exposition notionnelle de 200 fois le capital ; à 0,005 %, de 400 fois. Le
levier n'est pas une troisième décision : il est l'exacte conséquence
arithmétique des deux autres, et il est fixé avant toute considération de
signal. Or un stop ne franchit pas un trou de cotation — à ce levier, un écart
d'ouverture de un demi pour cent emporte **100 % du capital**.

La fraction de Kelly ferme la question. Elle vaut `(p(R+1) − 1)/R`, c'est-à-dire
**exactement zéro** sous un prix sans dérive, quel que soit le ratio visé.
Toute fraction positive engagée sur une géométrie sans dérive n'est pas un
sur-engagement modéré : c'est un sur-engagement d'ampleur infinie en
proportion, et la probabilité de perdre la moitié du capital en cent tentatives
vaut 90,9 %.

### Ce qu'il faudrait posséder, et le renversement que cela révèle

Toutes les exigences se ramènent à une seule, lisible sur une échelle que tout
le monde connaît.

| Stop | `c/L` | `E[τ]` | `µ*` | Sharpe annualisé requis |
|---|---|---|---|---|
| 0,050 % | 0,110 | 28,91 min | 0,685 pt/h | 2,9 |
| 0,010 % | 0,550 | 2,42 min | 8,189 pt/h | **34,2** |
| 0,005 % | 1,100 | 0,89 min | 22,206 pt/h | **92,8** |

L'exigence monte par **deux canaux à la fois** : la friction relative croît
comme l'inverse de la largeur, et l'exposition s'effondre d'un facteur 12 parce
qu'un stop proche est touché vite. Les deux effets se multiplient au lieu de se
compenser. Le resserrement ne rend pas l'exigence un peu plus dure, il la
**multiplie par 12** et la porte à un Sharpe annualisé de 34 — contre 3 pour
les meilleurs résultats publiés de la gestion.

C'est le résultat le plus important de cette partie, et il retourne la
conclusion du reste du document sans la contredire. Sur un stop large,
l'avantage requis est minuscule et donc indiscernable du bruit avant une
dizaine d'années. Sur le stop serré, il se démontre en une demi-année — mais il
exige un Sharpe que personne ne possède. **Les deux géométries butent sur le
même mur par ses deux faces : l'une demande un avantage si petit qu'on ne peut
pas le prouver, l'autre un avantage si grand qu'on ne peut pas l'avoir.** Le
passage de l'une à l'autre est continu, et le point où les deux difficultés
sont simultanément minimales n'est à aucune des deux extrémités.

### Le diagnostic inverse, et il est gratuit

Tout ce qui précède suppose un ratio visé. Deux chiffres que l'opérateur
connaît déjà suffisent à savoir lequel il pratique réellement : le nombre de
tentatives, et sa plus longue série d'échecs.

| Plus longue série | 50 tentatives | 100 | 200 | 400 |
|---|---|---|---|---|
| 3 | 1:0,44 | 1:0,31 | 1:0,22 | 1:0,17 |
| 5 | 1:1,14 | 1:0,81 | 1:0,62 | 1:0,48 |
| 6 | 1:1,56 | 1:1,11 | **1:0,84** | 1:0,67 |
| 12 | 1:5,31 | 1:3,35 | 1:2,49 | 1:1,98 |
| 20 | — | 1:7,70 | 1:5,30 | 1:4,10 |

La lecture est contre-intuitive et il faut la dire entière : **une série
maximale courte n'est pas une bonne nouvelle.** Elle implique un taux de
réussite élevé, donc — sous prix sans dérive, où taux de réussite et ratio sont
le même paramètre écrit deux fois — un ratio bas. Cinq à six échecs au maximum
sur deux cents tentatives implique un taux de réussite de 54,2 % et un ratio de
**1:0,84**. Ce n'est pas un 1:20.

Deux lectures s'offrent, et elles se distinguent par une observation faisable
ce soir. Soit le ratio réellement pratiqué est proche de 1:1, et toutes les
tables ci-dessus doivent être relues à cette ligne. Soit le ratio est bien de
1:20 et les séries observées sont bien plus courtes que la loi nulle ne le
prévoit — ce qui serait la **première indication positive** de tout le dépôt,
puisqu'un taux de réussite significativement au-dessus de `1/(R+1)` est
exactement ce que le protocole cherche à établir. La distinction ne demande
qu'un registre honnête des tentatives.

```bash
python main.py --risque           # les six planches et les dix tables
```

## Utilisation

```bash
python main.py                    # tables quantitatives du cadre
python main.py --layers           # lexique des sigles et tables des couches
python main.py --quant            # instruments de validation et de stress
python main.py --alp2             # tables d'ALP-2 et grille de notation
python main.py --prereg           # protocole scellé et son empreinte SHA-256
python main.py --power            # protocole à horizon borné et son Monte-Carlo
python main.py --measure f.csv    # exécute le protocole sur un historique
python main.py --hurst f.csv      # loi d'échelle mesurée, ratio de variance
python main.py --bounds f.csv     # la mesure encadrée par les deux remplissages
python main.py --edge             # témoin, catalogue de dérives, opérateur
python main.py --risque           # géométrie serrée, spread, forçage, capital
python main.py --tape <pseudo>    # enregistre un direct, une frappe par appel
python main.py --diffuseur f.csv  # évalue un registre de diffuseur collecté
python main.py --wp               # reconstruit le document de travail
python main.py --paper            # reconstruit docs/alp1-paper.html
python main.py --paper2           # reconstruit docs/alp2-paper.html
python main.py --disc             # journal de décision, lois nulles, attribution
python main.py --discpaper        # reconstruit docs/prouver-un-jugement.html
python main.py --tests            # 863 tests unitaires du noyau
```

Aucune dépendance : stdlib uniquement, Python 3.11+.

Sans fichier, `--measure` fait tourner la chaîne de mesure sur une série
synthétique de vérité connue — c'est un test de la chaîne, pas une mesure du
marché. Le format attendu est décrit dans
[`docs/donnees-requises.md`](docs/donnees-requises.md).

## Structure

Le cadre du trade, indépendant de toute couche d'analyse :

| Module | Rôle |
|---|---|
| `alp1/costs.py` | Friction, hit rate d'équilibre, taille d'échantillon, déflation du Sharpe |
| `alp1/barriers.py` | Premier passage brownien sans limite de durée |
| `alp1/horizon.py` | Premier passage sous contrainte de séance, loi d'échelle `σ₁·T^H` |
| `alp1/stops.py` | Remontée du stop : distribution des issues, coût, seuil de neutralité |

Les sept couches :

| Module | Rôle |
|---|---|
| `alp1/gex.py` | Gamma Black-Scholes, niveaux 0GW / CR / PS / HVL, boucle de couverture → `H` |
| `alp1/vprofile.py` | POC, aire de valeur, HVN/LVN, inversion densité → volatilité locale |
| `alp1/dow.py` | Six principes, structure de swings, lois nulles en forme fermée |
| `alp1/fib.py` | Provenance des ratios, loi du retracement, arbitrage d'exécution OTE |
| `alp1/orderflow.py` | Échelles de liquidité, LPR et son plafond, impact de Kyle, CVD |
| `alp1/regime.py` | Classification par gamma dealer et playbooks par régime |
| `alp1/signals.py` | Les 7 couches formalisées en prédicats testables |

Le noyau ALP-2 — la géométrie à barrière unique, et ce qu'il faut pour qu'un
chiffre soit défendable plutôt que seulement juste :

| Module | Rôle |
|---|---|
| `alp1/momentum.py` | Géométrie stop-seul, exposition, seuils, dimensionnement |
| `alp1/calib.py` | Identités du modèle, boîte de plausibilité, points de rupture |
| `alp1/microstructure.py` | Saisonnalité en U, sauts, hétéroscédasticité, et ce qui y survit |
| `alp1/friction.py` | La friction comme loi déduite du carnet, marge, capacité |
| `alp1/prereg.py` | Protocole scellé et son empreinte SHA-256 |
| `alp1/grading.py` | Grille de notation, appliquée aux deux documents |
| `alp1/dataset.py` | Lecture et audit d'un CSV de barres d'une minute |
| `alp1/measure.py` | Exécution du protocole sur l'historique fourni |
| `alp1/decay.py` | Décote post-publication de la dérive empruntée, durée de vie résiduelle |
| `alp1/scaling.py` | Calibration sous exposant d'échelle imposé, géométrie au pire cas |
| `alp1/varratio.py` | Loi d'échelle mesurée : ratio de variance, loi nulle de l'estimateur |
| `alp1/entropy.py` | Plafond de Kelly, information requise, biais des estimateurs |
| `alp1/nonlinear.py` | Entropie de permutation, fluctuations redressées, lois nulles |
| `alp1/discipline.py` | Dérogation comme multiplicité, point de rupture |
| `alp1/broadcast.py` | Latence d'un signal diffusé, loi nulle du classement, effacement, registre |
| `alp1/litedge.py` | Catalogue des dérives publiées, portes de compatibilité, assemblage |
| `alp1/discret.py` | Talent comme covariance, dispositif apparié, bras déclaré |
| `alp1/forcing.py` | Géométrie en ticks, spread de Roll, théorème du forçage, séries, levier, ruine |
| `alp1/report5.py` | Tables de la loi d'échelle mesurée et de l'encadrement du remplissage |
| `alp1/report7.py` | Tables du témoin, du catalogue et de l'opérateur |
| `alp1/report8.py` | Tables du risque réel, et glossaire en langue courante |
| `alp1/figrisk.py` | Planches du mur de friction, du spread, du forçage et du capital |
| `alp1/power.py` | Frontières séquentielles, information du panel, dérive minimale détectable |
| `alp1/mcprotocol.py` | Monte-Carlo du protocole entier : taille, puissance, durée du verdict |

Les instruments de validation :

| Module | Rôle |
|---|---|
| `alp1/pathstats.py` | Loi du trade, inclinaison d'Esscher, Sharpe, Sortino, Omega, Kelly, PSR, MinTRL |
| `alp1/drawdown.py` | `E[MDD]` sans dérive et sous dérive, quantiles de Lévy, Lundberg, ruine, Ulcer |
| `alp1/mc.py` | Générateur reproductible, simulation de trajectoires, bootstrap stationnaire, permutation |
| `alp1/hmm.py` | HMM gaussien, Baum-Welch, Viterbi, séparabilité, erreur de Bayes, AIC/BIC |
| `alp1/overfit.py` | Sharpe déflaté, MinBTL, décote de Harvey-Liu-Zhu, PBO par CSCV, plis purgés, marche avant |
| `alp1/stress.py` | VaR / ES, Cornish-Fisher et sa validité, GPD et Hill, sauts de Merton, scénarios, stress inversé |

La production du document :

| Module | Rôle |
|---|---|
| `alp1/report.py` | Tables chiffrées du cadre |
| `alp1/quant.py` | Calibration de référence et tables des instruments |
| `alp1/lexicon.py` | Lexique des sigles et tables des couches |
| `alp1/figures.py` | Figures SVG du cadre |
| `alp1/figterm.py` | Planches des couches, en panneaux de terminal |
| `alp1/figquant.py` | Planches des instruments, surfaces isométriques comprises |
| `alp1/report15.py` | Audit de l'hypothèse d'edge : le multiple comme paramètre, verdict calculé |
| `alp1/fighyp.py` | Planches de l'audit : délai, décomposition de l'espérance, surface du mur |
| `alp1/figcss.py` | Feuille de style partagée des figures |
| `alp1/report3.py` | Tables et valeurs de la décote et de l'exposant d'échelle |
| `alp1/report4.py` | Tables et valeurs du protocole à horizon borné |
| `alp1/figdecay.py` | Figures de la décote et de l'exposant d'échelle |
| `alp1/figpower.py` | Planches de puissance, de durée et de trajectoires séquentielles |
| `alp1/paper.py` | Assemblage du document depuis `docs/alp1-paper.template.html` |
| `alp1/workingpaper.py` | Assemblage du document de travail complet |

Le document est reconstruit à partir du gabarit : prose d'un côté, chiffres
injectés par le code de l'autre. Un chiffre du texte et le point correspondant
d'une figure ne peuvent pas diverger. Il compte 103 tables et 46 figures, toutes
produites par le noyau. Les simulations sont ensemencées explicitement : deux
exécutions du dépôt produisent le même document, au bit près.

## ALP-2, et ce qui lui manque

La grille de notation du dépôt — douze critères, trois familles, poids fixés
d'avance — est appliquée aux deux documents avec la même échelle. ALP-1 obtient
49,4 points sur 100, ALP-2 en obtient 90,2.

| Famille | Maximum | ALP-1 | ALP-2 |
|---|---|---|---|
| Validité interne | 35 | 25,8 | **35,0** |
| Contenu empirique | 35 | 9,8 | 25,2 |
| Exploitabilité | 30 | 13,8 | **30,0** |

**Les 9,8 points manquants sont tous au même endroit.** Deux critères — une
mesure conduite sur historique, et un candidat de dérive ré-estimé sur données
propres — portent sur une mesure, et le dépôt n'a jamais ouvert une série de
prix. Aucun raisonnement ne les débloque ; un fichier CSV les débloque tous les
deux. La chaîne qui le consomme est écrite, auditée et testée sur série
synthétique de vérité connue : elle retrouve `−c` sous martingale et la dérive
injectée sous momentum conditionnel.

Ce qu'il faut fournir, où le trouver et dans quel ordre :
[`docs/donnees-requises.md`](docs/donnees-requises.md).

### Quatre résultats de la partie ALP-2

**Le critère maître est plus robuste que le modèle dont il est tiré.**
Saisonnalité intra-séance, sauts, volatilité de séance aléatoire : `E[R] =
µ·E[τ∧T] − c` y survit exactement, et la vérification est une simulation du
modèle complet plutôt qu'une algèbre — la moyenne simulée rejoint la prédiction
à moins d'une erreur-type, l'exposition étant mesurée dans la simulation
elle-même. Ce qui bouge est borné à 19 % sur une boîte de quatre-vingt-une
combinaisons de paramètres.

**Un saut ne coûte pas ce qu'on croit, et pas où on croit.** Sur une géométrie
sans target, le dépassement du stop entre dans `X_{τ∧T}` et Wald l'absorbe :
l'espérance ne bouge pas. C'est le **dénominateur** qui bouge — la perte réelle
excède la perte nominale de 9,3 % sur un stop de trois points, de 0,3 % sur la
bande de bruit. Un rapport de trente entre les deux géométries devant le même
marché.

**La friction posée était optimiste d'un facteur deux.** Déduite du barème, de
la profondeur du carnet, de la latence et de la volatilité conditionnelle au
déclenchement, elle vaut 0,65 point en moyenne contre 0,33 posé. Le glissement
de sortie déduit, 1,8 tick, retombe par une route indépendante sur le tick et
demi que le scénario réaliste posait. La marge tient quand même : la dérive
publiée dépasse la friction d'un facteur 2,8 au pire coin de la boîte de
carnet. Mais la contrainte de capacité mord tôt — quelques dizaines de contrats,
pas quelques centaines.

**Aucune conclusion ne bascule dans la boîte de plausibilité.** Les six
conclusions du document sont encadrées sur 3 125 combinaisons des entrées, et
le point de rupture de chacune est calculé par bissection : il faut une
friction 2,6 fois supérieure au pire scénario d'exécution, ou une dérive tombée
de 6 à 1,2 point de base, pour annuler l'espérance. Contrôle externe : le taux
de réussite impliqué par la géométrie, 33,8 %, retombe sur les 38–40 % publiés
sans avoir été calibré dessus.

## Statut

Analyse théorique, batterie d'instruments et protocole. **Aucune validation
empirique.** La sixième partie ajoute trois bornes sur ce que des sources
extérieures peuvent apporter — un diffuseur en direct, un catalogue de dérives
publiées, un opérateur discrétionnaire —, et le dépôt fournit la chaîne de
collecte prospective qu'elles supposent ; aucun registre de diffuseur n'a été
collecté à ce jour, et aucun des neuf effets du catalogue n'a été ré-estimé
ici. La septième partie recalibre l'ensemble sur la géométrie que l'opérateur
déclare — stop de cinq à dix millièmes de pour cent, point mort, deux pour cent
du capital par tentative, forçage — et y ajoute le théorème du forçage, le
rebond de cotation de Roll et le diagnostic inverse par la longueur des séries.
Aucune de ces grandeurs n'est mesurée sur un historique : toutes se déduisent
de la géométrie déclarée, ce qui les rend vérifiables sans donnée mais ne les
substitue à aucune mesure. Le protocole de vérification est en revanche complet, scellé,
exécutable, et son Monte-Carlo établit qu'il rend un verdict sur cinq années de
barres d'une minute au plus. Les instruments de la troisième partie sont appliqués à des lois
déduites du modèle et à des séries synthétiques dont la vérité est connue
d'avance — ce qui les contrôle, mais ne mesure rien du marché. Ce dépôt ne
constitue pas un conseil en investissement et ne comporte aucune affirmation de
performance.
