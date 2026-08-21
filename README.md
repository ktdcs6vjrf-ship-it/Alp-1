# Alp-1

Formalisation, diagnostic quantitatif, batterie d'instruments de validation et
protocole de falsification d'une stratégie intraday sur futures indiciels à
sept couches.

Le paper complet : [`docs/alp1-paper.html`](docs/alp1-paper.html).

## Ce que contient ce dépôt

Une analyse **analytique**, sans donnée de marché. Elle délimite l'espace dans
lequel un edge peut exister pour cette stratégie et chiffre ce qu'il devrait
valoir ; elle n'établit pas qu'il existe. Aucun test empirique n'a été conduit.

Le document se lit en trois parties. La première traite la stratégie comme une
géométrie — un stop, un target, une règle de sortie — et n'a besoin d'aucune
couche d'analyse. La seconde examine les sept couches une à une : GEX, profil
de volume, VWAP, théorie de Dow, Fibonacci, carnet d'ordres. La troisième
applique seize instruments de mesure, de simulation et de stress — Monte-Carlo,
HMM, Sharpe, Sortino, drawdown maximal, VaR/ES, valeurs extrêmes, Sharpe
déflaté, PBO, validation croisée purgée — pour décider **ce qu'un historique
permettrait de conclure**.

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
pas** être attribuée au régime de gamma. Le papier le signale plutôt que de le
résoudre.

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
2. **L'edge supposé, s'il existe à l'amplitude retenue, n'est pas mesurable dans
   un échantillon que la stratégie possédera un jour** — 9,7 ans sans sélection,
   25,1 ans après cent configurations essayées.
3. **Il en découle une conclusion plus forte que la précaution habituelle sur le
   surajustement.** Puisqu'aucun backtest d'un an ne distingue l'edge du bruit,
   un bon backtest d'un an n'est pas une preuve faible : c'est une observation
   dont l'explication par défaut est la sélection.

Deux leviers déplacent le verdict, et le calcul les chiffre.

| Levier | Effet |
|---|---|
| Fixer la configuration **avant** de regarder les données | 25,1 ans → 9,7 ans. Gratuit. |
| Passer de 2 à 8 trades par séance | 25,1 ans → 6,3 ans, si la dérive survit à la multiplication des signaux |
| Augmenter l'amplitude de l'edge | il faudrait `10,9 µ*` — un Sharpe annualisé de 3,8 — pour qu'une année suffise. Hors de portée. |

## Utilisation

```bash
python main.py                    # tables quantitatives du cadre
python main.py --layers           # lexique des sigles et tables des couches
python main.py --quant            # instruments de validation et de stress
python main.py --alp2             # tables d'ALP-2 et grille de notation
python main.py --prereg           # protocole scellé et son empreinte SHA-256
python main.py --measure f.csv    # exécute le protocole sur un historique
python main.py --paper            # reconstruit docs/alp1-paper.html
python main.py --tests            # 264 tests unitaires du noyau
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
| `alp1/paper.py` | Assemblage du document depuis `docs/alp1-paper.template.html` |

Le document est reconstruit à partir du gabarit : prose d'un côté, chiffres
injectés par le code de l'autre. Un chiffre du texte et le point correspondant
d'une figure ne peuvent pas diverger. Il compte 32 tables et 26 figures, toutes
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
empirique.** Les instruments de la troisième partie sont appliqués à des lois
déduites du modèle et à des séries synthétiques dont la vérité est connue
d'avance — ce qui les contrôle, mais ne mesure rien du marché. Ce dépôt ne
constitue pas un conseil en investissement et ne comporte aucune affirmation de
performance.
