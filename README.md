# Alp-1

Formalisation, diagnostic quantitatif et protocole de falsification d'une
stratégie intraday sur futures indiciels à sept couches.

Le paper complet : [`docs/alp1-paper.html`](docs/alp1-paper.html).

## Ce que contient ce dépôt

Une analyse **analytique**, sans donnée de marché. Elle délimite l'espace dans
lequel un edge peut exister pour cette stratégie et chiffre ce qu'il devrait
valoir ; elle n'établit pas qu'il existe. Aucun test empirique n'a été conduit.

Le document se lit en deux parties. La première traite la stratégie comme une
géométrie — un stop, un target, une règle de sortie — et n'a besoin d'aucune
couche d'analyse. La seconde examine les sept couches une à une : GEX, profil
de volume, VWAP, théorie de Dow, Fibonacci, carnet d'ordres.

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

## Utilisation

```bash
python main.py            # tables quantitatives du cadre
python main.py --layers   # lexique des sigles et tables des sept couches
python main.py --paper    # reconstruit docs/alp1-paper.html depuis le gabarit
python main.py --tests    # 114 tests unitaires du noyau
```

Aucune dépendance : stdlib uniquement, Python 3.11+.

## Structure

Le cadre du trade, indépendant de toute couche d'analyse :

| Module | Rôle |
|---|---|
| `alp1/costs.py` | Friction, hit rate d'équilibre, taille d'échantillon, déflation du Sharpe |
| `alp1/barriers.py` | Premier passage brownien sans limite de durée |
| `alp1/horizon.py` | Premier passage sous contrainte de séance, loi d'échelle `σ₁·T^H` |
| `alp1/stops.py` | Remontée du stop : distribution des issues, coût, seuil de neutralité |
| `alp1/momentum.py` | Géométrie stop-seul, dimensionnement |

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

La production du document :

| Module | Rôle |
|---|---|
| `alp1/report.py` | Tables chiffrées du cadre |
| `alp1/lexicon.py` | Lexique des sigles et tables des couches |
| `alp1/figures.py` | Figures SVG du cadre |
| `alp1/figterm.py` | Planches des couches, en panneaux de terminal |
| `alp1/figcss.py` | Feuille de style partagée des figures |
| `alp1/paper.py` | Assemblage du document depuis `docs/alp1-paper.template.html` |

Le document est reconstruit à partir du gabarit : prose d'un côté, chiffres
injectés par le code de l'autre. Un chiffre du texte et le point correspondant
d'une figure ne peuvent pas diverger. Il compte 18 tables et 16 figures, toutes
produites par le noyau.

## Statut

Analyse théorique et protocole. **Aucune validation empirique.** Ce dépôt ne
constitue pas un conseil en investissement et ne comporte aucune affirmation de
performance.
