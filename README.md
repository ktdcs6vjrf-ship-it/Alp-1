# Alp-1

Formalisation, diagnostic quantitatif et protocole de falsification d'une
stratégie intraday sur futures indiciels à sept couches.

Le paper complet : [`docs/alp1-paper.html`](docs/alp1-paper.html).

## Ce que contient ce dépôt

Une analyse **analytique**, sans donnée de marché. Elle délimite l'espace dans
lequel un edge peut exister pour cette stratégie et chiffre ce qu'il devrait
valoir ; elle n'établit pas qu'il existe. Aucun test empirique n'a été conduit.

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

L'exposant `H = 0,65` n'est pas choisi : il est impliqué par la volatilité à une
minute et par la dispersion d'une séance. Sous cette calibration, **1:20 est à
l'intérieur de la portée d'une séance, 1:30 à sa limite**, et l'exposition
sature au-delà — éloigner encore le target n'achète plus de temps de marché mais
continue de diviser la probabilité d'y parvenir.

## La remontée du stop

Elle est neutre en espérance **si et seulement si** la dérive postérieure à la
confirmation est exactement nulle, et coûte dès qu'elle est positive — c'est-à-
dire précisément quand le signal fonctionne. Or le déclencheur retenu (mur de
liquidité protecteur, prise de liquidité favorable en L2) est, par la logique
qui le motive, un signal favorable.

**Reformulation proposée :** déclencher la remontée sur l'*invalidation* de la
confirmation — mur retiré avant d'être touché, absorption qui échoue, liquidité
prise du côté opposé. Même information, même endroit du carnet, signe inversé.
Le `Liquidity Persistence Ratio` du module `alp1.signals` fournit la mesure.

Quant au ratio affiché après remontée, il est arithmétiquement exact et sans
effet sur l'espérance : un 1:290 se paie d'une probabilité de réalisation de
0,34 %, vaut 1:138 une fois la friction prise en compte, et laisse un risque
résiduel que le seul bruit balaie dans 91 % des cas en cinq minutes.

## Le régime de gamma

Le signe du gamma net prédit une propriété de la variance et de
l'autocorrélation, non une direction : ce n'est pas un signal directionnel mais
une variable de conditionnement. Son rôle testable est de conditionner la
**géométrie** — l'exposant d'échelle `H`, donc l'atteignabilité des targets
éloignés — et la prédiction se teste sans aucun signal d'entrée : `H(Γ < 0)`
doit excéder `H(Γ > 0)`.

## Utilisation

```bash
python main.py            # tables quantitatives du paper
python main.py --paper    # reconstruit docs/alp1-paper.html depuis le gabarit
python main.py --tests    # 64 tests unitaires du noyau
```

Aucune dépendance : stdlib uniquement, Python 3.11+.

## Structure

| Module | Rôle |
|---|---|
| `alp1/costs.py` | Friction, hit rate d'équilibre, taille d'échantillon, déflation du Sharpe |
| `alp1/barriers.py` | Premier passage brownien sans limite de durée |
| `alp1/horizon.py` | Premier passage sous contrainte de séance, loi d'échelle `σ₁·T^H` |
| `alp1/stops.py` | Remontée du stop : distribution des issues, coût, seuil de neutralité |
| `alp1/regime.py` | Classification par gamma dealer et playbooks par régime |
| `alp1/signals.py` | Les 7 couches formalisées en prédicats testables |
| `alp1/report.py` | Tables chiffrées du paper |
| `alp1/figures.py` | Figures SVG du paper |
| `alp1/paper.py` | Assemblage du document depuis `docs/alp1-paper.template.html` |

Le document est reconstruit à partir du gabarit : prose d'un côté, chiffres
injectés par le code de l'autre. Un chiffre du texte et le point correspondant
d'une figure ne peuvent pas diverger.

## Statut

Analyse théorique et protocole. **Aucune validation empirique.** Ce dépôt ne
constitue pas un conseil en investissement et ne comporte aucune affirmation de
performance.
