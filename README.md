# Alp-1

Formalisation, diagnostic quantitatif et protocole de falsification d'une
stratégie discrétionnaire intraday sur futures indiciels à sept couches.

Le paper complet : [`docs/alp1-paper.html`](docs/alp1-paper.html).

## Verdict sur l'edge

**Le dossier ne démontre pas d'edge, et ne peut pas en démontrer un : il ne
contient aucune mesure empirique.** Il contient autre chose — un théorème qui
élimine une classe entière de fausses pistes, l'identification du paramètre
réellement décisif, une hypothèse d'edge rendue falsifiable, et un protocole
capable de la tuer en quelques jours de travail sur données publiques.

## Le résultat central, et son extension

Sous un mouvement brownien sans drift, l'espérance par trade vaut exactement
`−c/L` — la friction rapportée au risque nominal — **quel que soit le ratio
gain/risque retenu**. Par le théorème d'arrêt optionnel, cette valeur est
**préservée par toute règle d'arrêt** : mise à breakeven, stop suiveur, prises
partielles. Le taux de réussite affiché est lui aussi invariant.

Aucun schéma de gestion du stop ne crée d'espérance. Seul un drift conditionnel
à l'entrée le peut.

## Ce que change le stop à 0,050 %

| Grandeur | Stop 0,010 % | Stop 0,050 % | Facteur |
|---|---|---|---|
| Friction / risque `c/L` | 0,550 | 0,110 | 5,0× |
| Lift conditionnel requis Δp | 13,75 pt | 2,75 pt | 5,0× |
| P(stop par le bruit, 5 min) | 83,0 % | 28,3 % | — |
| Ratio d'information requis (15 min) | 1,369 | 0,058 | 23,7× |

L'ancien paramétrage exigeait du signal une capacité prédictive hors d'atteinte,
indépendamment de la qualité des couches d'analyse. Le nouveau ramène l'exigence
à un niveau modeste. **C'est la modification la plus productive apportée à la
stratégie, et elle vaut davantage que l'ajout de n'importe quelle couche.**

## La mise à breakeven, et pourquoi elle est spécifiée à l'envers

La règle est neutre en espérance **si et seulement si** le drift postérieur à la
confirmation est exactement nul. Elle coûte dès qu'il est positif — c'est-à-dire
précisément quand le signal fonctionne.

Or le déclencheur retenu (mur de liquidité protecteur, prise de liquidité
favorable en L2) est, par la logique qui le motive, un signal favorable : il
annonce un drift positif. La règle resserre donc le risque au moment où les
probabilités viennent de s'améliorer, et multiplie par 5,5 la taille
d'échantillon nécessaire à la validation.

**Correctif proposé :** déclencher la mise à BE sur l'*invalidation* de la
confirmation — mur retiré avant d'être touché, absorption qui échoue, liquidité
prise du côté opposé — et non sur la confirmation elle-même. Même information,
même endroit du carnet, signe inversé. Le `Liquidity Persistence Ratio` du
module `alp1.signals` fournit déjà la mesure.

## L'hypothèse d'edge — Gamma-Regime Conditioning

Le signe du gamma dealer net arbitre les deux moteurs contradictoires de la pile
(Dow en continuation, VWAP ± k·SD en réversion). Objection principale, ajoutée
en v0.2 : **un régime n'est pas un drift.** Le gamma prédit une propriété de la
variance et de l'autocorrélation, pas une direction. Le GRC doit donc être testé
comme variable de conditionnement — un différentiel de lift — contre un seuil
explicite de 2,75 points (4,83 sous friction réaliste).

## Utilisation

```bash
python main.py            # génère les tables quantitatives du paper
python main.py --tests    # 46 tests unitaires du noyau
```

Aucune dépendance : stdlib uniquement, Python 3.11+.

## Structure

| Module | Rôle |
|---|---|
| `alp1/costs.py` | Friction, hit rate d'équilibre, taille d'échantillon, déflation du Sharpe |
| `alp1/barriers.py` | First-passage brownien : survie du stop, P(TP avant SL), drift requis |
| `alp1/stops.py` | Mise à breakeven : distribution des issues, coût, seuil de neutralité |
| `alp1/regime.py` | Classification GRC et playbooks par régime |
| `alp1/signals.py` | Les 7 couches formalisées en prédicats testables |
| `alp1/report.py` | Génération des tables du paper |

## Statut

Analyse théorique et protocole. **Aucune validation empirique** — le GRC comme
les autres hypothèses restent à tester sur données historiques, dans l'ordre
indiqué au §7.5 du paper. Ce dépôt ne constitue pas un conseil en investissement
et ne comporte aucune affirmation de performance.
