# Alp-1

> **Temps de marché et péremption : invariance des règles d'arrêt,
> exposition, et durée de vie d'une dérive empruntée**
> *Série de documents de travail ALP, nº 1.* JEL : C12, C58, G11, G13, G14.

Le document complet :
[`docs/temps-de-marche-et-peremption.html`](docs/temps-de-marche-et-peremption.html) —
35 sections en cinq parties, 69 tables, 36 figures.

## Ce que contient ce dépôt

Une analyse **analytique**, sans donnée de marché. Elle délimite l'espace dans
lequel un edge peut exister pour cette stratégie et chiffre ce qu'il devrait
valoir ; elle n'établit pas qu'il existe. Aucun test empirique n'a été conduit.

Deux stratégies y sont comparées. **ALP-1** est la pile d'origine : sept
couches d'analyse, un stop serré, un objectif lointain, une remontée du stop
déclenchée par le carnet. **ALP-2** est la géométrie que le diagnostic finit
par désigner : aucun objectif, un stop posé sur la bande de bruit, une sortie
au marché à la clôture.

Le document se lit en cinq parties. La première définit les huit notions
nécessaires. La deuxième établit ce qu'une géométrie peut et ne peut pas. La
troisième passe les sept instruments au crible de leur loi nulle — GEX, profil
de volume, VWAP, théorie de Dow, Fibonacci, carnet d'ordres. La quatrième
construit ALP-2 et la confronte à une dérive publiée et à une friction déduite
du carnet. La cinquième note les deux approches sur une grille fixée d'avance,
et énonce ce qui manque.

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

| Grandeur | Forme fermée | Valeur au stop 0,050 % et R:R 1:20 |
|---|---|---|
| Dérive minimale rentable | `µ* = c/E[τ]` | 0,685 point d'indice par heure |
| Ratio d'information requis | `IR* = c/√(ab)` | 0,049 (0,086 en friction réaliste) |
| Lift relatif requis | `Δp/p₀ = c/L` | 11,0 %, **quel que soit le ratio visé** |

Un ratio gain/risque élevé n'assouplit pas l'exigence de qualité du signal : il
la déplace vers un événement plus rare. Ce qui baisse réellement, c'est
l'exigence en ratio d'information, parce que la position reste exposée plus
longtemps pour une même friction.

## Ce que la séance change à un 1:20 – 1:30

Un target à 1:20 sur un stop de 3 points est un déplacement de 60 points, soit
1,00 % de l'indice. Son atteignabilité dépend d'une propriété mesurable du
prix : la vitesse à laquelle sa dispersion croît avec l'horizon, `σ(T) = σ₁·T^H`.

| Ratio | P(target) si `H = 0,50` | P(target) si `H = 0,65` | Exposition |
|---|---|---|---|
| 1:20 | 0,76 % | 4,65 % | 28,9 min |
| 1:30 | 0,02 % | 2,40 % | 35,0 min |
| 1:50 | 0,00 % | 0,31 % | 38,2 min |

Sous la calibration retenue, 1:20 est à l'intérieur de la portée d'une séance,
1:30 à sa limite. **C'est le paramètre le plus fragile du document** : si les
60 points de dispersion de séance sont une amplitude haut-bas et non un
écart-type de clôture, l'exposant tombe à 0,57 et P(1:30) est divisée par
quatre. Le premier test du protocole porte donc sur la loi d'échelle, avant
tout signal.

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
0,050 % vaut donc 3,6 écarts-types locaux sur le POC et 2,3 sur un LVN, et la
probabilité d'être sorti par le bruit seul en trente minutes passe de 51 % à
67 %. La règle d'entrée de la pile privilégie précisément les LVN.

**La grille de Fibonacci paie quand le signal ne vaut rien.** À exposition
inchangée, l'écart d'espérance entre entrée en zone OTE et entrée au marché
vaut `Δ = −(1 − q)·E_marché` : attendre le retracement améliore l'espérance par
signal *si et seulement si* le signal exécuté au marché est perdant. Même forme
que le résultat sur la remontée du stop.

**Un signal de carnet ne peut pas financer un aller-retour.** L'information
d'un signal de flux a une demi-vie. Sur une exposition de 29 minutes, un signal
de demi-vie trois secondes en conserve 0,2 % et exigerait 4,6 points de dérive
par minute — 3,7 fois la volatilité — pour couvrir la friction. La couche relève
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
| Sharpe annualisé | 0,50 |
| Sortino / Sharpe | 4,54 — un facteur que la **géométrie** fabrique, pas le signal |
| MinTRL | 4 905 trades, soit 9,7 ans, pour affirmer que le Sharpe est positif |
| MinBTL après 100 essais | 12 659 trades, soit 25,1 ans |
| Sharpe déflaté à 100 essais | 1,7 % |
| E[drawdown max] sur 1 an | 103 R — **supérieur** au gain annuel espéré, 55 R |
| Monte-Carlo, 4 000 années | une stratégie sans edge bat, une année sur vingt, le Sharpe **vrai** de celle qui en a un |
| Stress inversé | un choc de 2,82 % efface une année entière d'espérance |

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
2. **L'edge supposé n'est pas mesurable par le dispositif ordinaire** — une
   moyenne non pondérée de trades comptés un par un, sur un marché, seuil
   corrigé de Bonferroni, décision unique : 9,7 ans sans sélection, 25,1 ans
   après cent configurations essayées.
3. **Il en découle une conclusion plus forte que la précaution habituelle sur le
   surajustement.** Puisqu'aucun backtest d'un an ne distingue l'edge du bruit,
   un bon backtest d'un an n'est pas une preuve faible : c'est une observation
   dont l'explication par défaut est la sélection.

La deuxième proposition porte sur un **instrument de mesure**, et c'est ce que
la partie suivante exploite : la durée d'une vérification n'est pas une
propriété de la stratégie.

| Levier | Effet |
|---|---|
| Fixer la configuration **avant** de regarder les données | 25,1 ans → 9,7 ans. Gratuit. |
| Passer de 2 à 8 trades par séance | 25,1 ans → 6,3 ans, si la dérive survit à la multiplication des signaux |
| Augmenter l'amplitude de l'edge | il faudrait `10,9 µ*` — un Sharpe annualisé de 3,8 — pour qu'une année suffise. Hors de portée. |
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
python main.py --wp               # reconstruit le document de travail
python main.py --paper            # reconstruit docs/alp1-paper.html
python main.py --paper2           # reconstruit docs/alp2-paper.html
python main.py --tests            # 461 tests unitaires du noyau
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
| `alp1/figcss.py` | Feuille de style partagée des figures |
| `alp1/report3.py` | Tables et valeurs de la décote et de l'exposant d'échelle |
| `alp1/report4.py` | Tables et valeurs du protocole à horizon borné |
| `alp1/figdecay.py` | Figures de la décote et de l'exposant d'échelle |
| `alp1/figpower.py` | Planches de puissance, de durée et de trajectoires séquentielles |
| `alp1/paper.py` | Assemblage du document depuis `docs/alp1-paper.template.html` |
| `alp1/workingpaper.py` | Assemblage du document de travail complet |

Le document est reconstruit à partir du gabarit : prose d'un côté, chiffres
injectés par le code de l'autre. Un chiffre du texte et le point correspondant
d'une figure ne peuvent pas diverger. Il compte 40 tables et 28 figures, toutes
produites par le noyau ; les tables d'ALP-2 en ajoutent 24. Les simulations sont ensemencées explicitement : deux
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
empirique.** Le protocole de vérification est en revanche complet, scellé,
exécutable, et son Monte-Carlo établit qu'il rend un verdict sur cinq années de
barres d'une minute au plus. Les instruments de la troisième partie sont appliqués à des lois
déduites du modèle et à des séries synthétiques dont la vérité est connue
d'avance — ce qui les contrôle, mais ne mesure rien du marché. Ce dépôt ne
constitue pas un conseil en investissement et ne comporte aucune affirmation de
performance.
