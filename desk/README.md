# ALP Desk

Terminal mobile de préparation pour un opérateur MNQ, publié en **une seule page HTML**
(artefact claude.ai, capacités `db` + `user`). Il n'appartient pas à la chaîne des papiers :
aucun module Python, aucun test du dépôt ne le lit. Il en reprend seulement des résultats
d'ALP nº 3, toujours avec leur source.

Dernier artefact : https://claude.ai/artifact/RUirhupXYNSPHSMGp9BTDH (v4, plan en déroulé voir / faire ; précédents : 1772yYTUpYmuAkEJ7DQWm2, DgoivKfGJjD8mrJ4UFzGwD, Vy2Rb9kb1JNUgtbt8cdcCJ). Capacités : db, user, assets.
Règle : **un nouveau lien à chaque amélioration** — on publie sous un nouveau nom de fichier.

## Les desks

| Fichier | Desk | Ordre | Tests |
|---|---|---|---|
| `src/desks/home.js` | Desk (hub, carte de séance en pourcentages, flux des décisions) | 0 | — |
| `src/desks/plan.js` | Plan de trading (carte des neuf étapes, déroulé voir / faire par moment, mode Live, méthode) | 1 | 341 |
| `src/desks/plan-fig.js` | Figures du Plan : VWAP calculée et ses bandes, footprint chiffré, carte de liquidité (sept issues), profil de volume, FVG, frise du jour | — | (dans plan) |
| `src/desks/macro.js` | Macro (rapports transcrits, régime, calendrier, méthode) | 10 | banc `test/macro-fixture.js` |
| `src/desks/nq.js` | NQ futures (séance, niveaux GEX, contrat, taille) | 20 | 136 |
| `src/desks/micro.js` | Stratégie intraday (plan VWAP, setups, seuil µ*, lectures) | 30 | 303 |
| `src/desks/risk.js` | Risque (compte, jour, passage, règles) | 40 | 139 |
| `src/desks/quant.js` | Quant & backtest (Monte-Carlo, backtest, robustesse, échantillon) | 50 | 191 |
| `src/desks/perf.js` | Métriques & espaces (41 métriques, heatmaps 2D, surfaces 3D) | 55 | 240 |
| `src/desks/journal.js` | Journal (saisie scellée, registre, statistiques) | 60 | 149 |
| `src/desks/routine.js` | Routine & revue (avant, pendant, après, progression) + Réglages | 70 / 90 | 71 |

Le desk **Plan** est le point d'entrée du jour. Sa carte reprend `T.DAY_STEPS` (macro,
biais, zones, gex, fenetre, declencheur, risque, journal, revue) ; chaque étape dit quoi
est un **déroulé** de moments : chacun dit quoi VOIR (un carrousel de planches 2D et de
reliefs 3D, la situation choisie en premier) puis quoi FAIRE (le champ ou le réglage du
moment), et se coche ; l'étape se valide d'un bouton qui ramène à la carte. Les planches
sont des illustrations calculées (`plan-fig.js`), jamais des données de marché : la VWAP
est celle d'une séance synthétique et les contacts marqués sont trouvés par une règle ;
delta et volume d'un footprint se calculent depuis ses cellules. En Live, la planche de
ce qu'il faut voir s'ouvre sous la première case qui manque. Le pourcentage d'une étape
suit sa liste (`T.day.setPct`) ; un autre desk qui marque l'étape (`T.day.mark`) la porte à
100 %. Un desk ouvert depuis une étape porte en tête un bouton « Revenir au plan »
(`T.nav.setReturn`). Le mode Live inscrit un trade ou une passe d'un geste, horodaté,
statut `ouvert` : le journal se complète après la séance. Le bouton « Enregistrer ces zones
pour le Labo » écrit les HVZ, LVN et LVN historiques du jour dans `levels/items` (noms
`HVZ1…`, `LVN1…`, `LVH1…`), que lit le gabarit `plan-hvz` du Labo.

Le socle est `src/core.js` + `src/core.css` + `src/shell.html` ; le contrat d'un desk
(API `T.*`, schéma du journal, règle « aucun chiffre de marché inventé ») est dans
`CONTRACT.md`.

## Construire, tester, regarder

```
cd desk
python3 build.py                                  # dist/alp-desk.html (à publier)
python3 build.py --fonts --out dist/integ.html    # aperçu local avec fontes et doctype
for f in test/*.test.js; do node $f | tail -1; done
python3 -m http.server 8766 &                      # depuis le dossier parent de desk/
node test/e2e.js http://127.0.0.1:8766/desk/dist/integ.html --shots shots/integ --full
```

Le banc de rendu doit rendre `"bad": 0` (débordement, élément hors cadre, erreur,
`NaN`) à 390 et 1280 px. **Puis on regarde les captures** : tous les défauts corrigés
pendant la construction ont été vus à l'œil, aucun par le banc.

Les tests de recoupement lisent le texte brut d'ALP nº 3 dans `ref/alp3txt/` (une
partie par fichier) et quelques modules de `alp1/`.

## Les données que Claude écrit

Deux collections partagées, écrites avec `ArtifactData` sur l'URL de l'artefact :

- `macro` — documents `{kind:'report', date, title, source, lede, tags, blocks}` (blocs
  `h`, `p`, `kpis`, `line`, `bar`, `table`, `heat`, `callout`, `source`) et
  `{kind:'regime', date, growth, inflation, label, note, source}` ;
- `calendar` — `{date, time (heure de Paris), event, country, impact 1-3, prev, cons, actual, note}`.

Tout le reste (journal, réglages, routine) vit dans l'espace privé de chaque
utilisateur, `data/users/<id>/…`, avec une copie locale.

## Pièges déjà tombés dedans

- Une capitale CSS transforme `µ` en `Μ` et `σ` en `Σ` : jamais de `text-transform:
  uppercase` sur un libellé qui porte une lettre grecque.
- `order || 99` envoyait le desk d'ordre 0 à la fin du menu.
- `.chart .axl` écrasait l'attribut `fill` d'un texte SVG : la teinte passe par `style`.
- `pkill -f "http.server"` tue aussi le shell qui l'exécute : relancer le serveur avec
  `setsid nohup`.
- Les étiquettes d'un Sankey à trois colonnes se heurtaient à 390 px ; `C.sankey`
  change maintenant de côté puis descend d'une ligne tant qu'une étiquette en heurte une autre.
- Une heure écrite « 10 h 00 » se coupait en fin de ligne : une passe typographique
  (`T.typoTree`) pose les espaces insécables sur tout ce qui entre dans la vue.
