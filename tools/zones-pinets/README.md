# Banc d'essai de `pine/alp0-zones.pine`

Aucun compilateur TradingView n'est joignable depuis le dépôt. Ce banc fait la
meilleure chose suivante : il exécute **le vrai fichier Pine**, sans le
retranscrire, sous [PineTS](https://github.com/LuxAlgo/PineTS) — un runtime
libre qui transpile du Pine v6 natif et l'exécute bougie par bougie — sur des
séances synthétiques, puis lit ce que le script a dessiné (lignes, étiquettes,
boîtes, tableau) et le compare à des issues calculées à la main.

```
npm install        # pinets 0.13.1, figé
node scenarios.mjs # ~20 s, 131 contrôles
```

- `banc.mjs` — heure de Paris → UTC sans table d'heure d'été écrite à la main
  (on essaie les deux décalages et on garde celui qui retombe juste), séances
  d'une minute interpolées entre des jalons, bougies imposées, et `lancer()`
  qui renvoie les objets dessinés et les cellules du tableau.
- `scenarios.mjs` — A touches et issues, B confluences, C saisie invalide et
  données absentes, D doublons, E quotas, F changements d'heure, G anticipation
  et repaint, H gel à 22 h, I créneaux NQ / MNQ, J profil 0DTE, K VWAP,
  L l'exemple fictif de `docs/zones-gamma-format.md` lu dans le fichier,
  M la heatmap z-score (référence indépendante, préchauffage, couleurs),
  N un texte collé sans retours à la ligne, O l'exemple regardé le week-end
  (séance close, niveaux gelés, profil à droite, tableau qui dit où regarder),
  P l'exemple de la consigne du bot, Q le mode démo.

Ce que le banc ne prouve pas : PineTS n'est pas le compilateur de TradingView
(qualificatifs *simple* / *series*, avertissements de l'éditeur). Quatre écarts
connus de PineTS, sans effet pour TradingView :

1. une fonction d'une seule expression qui lit un tableau global
   (`rels.get(i).champ`) est refusée — écrite en deux instructions ;
2. `booléen == (comparaison)` rend toujours faux — écrit avec `and` / `or` ;
3. faute de session d'échange sur des bougies fournies, `timeframe.change("D")`
   bascule à minuit UTC ; sur NQ1!, TradingView bascule à l'ouverture CME.
   Le scénario K ancre donc le VWAP (mode AVWAP) pour un calcul exact, et
   vérifie la remise à zéro « Day » là où PineTS la place.

4. PineTS traite une bougie **postérieure à l'horloge du système** comme du
   temps réel non confirmé : `barstate.isconfirmed` y est faux, et toute la
   logique de l'indicateur (qui ne tourne que sur bougie confirmée) s'arrête,
   sans erreur. Les scénarios sont donc datés dans le passé ; un exemple daté
   d'après le jour où l'on lance le banc ne trace rien. Sur TradingView, une
   bougie n'est jamais dans le futur.

`zscore-vwap.mjs` vérifie de la même façon `pine/alp0-zscore-vwap.pine`, le
script autonome z-score + VWAP (17 contrôles : `node zscore-vwap.mjs`).

Il ne participe pas à `python main.py --tests`.
