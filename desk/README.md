# ALP Desk

Terminal mobile de préparation pour un opérateur MNQ, publié en **une seule page HTML**
(artefact claude.ai, capacités `db` + `user`). Il n'appartient pas à la chaîne des papiers :
aucun module Python, aucun test du dépôt ne le lit. Il en reprend seulement des résultats
d'ALP nº 3, toujours avec leur source.

Dernier artefact : https://claude.ai/artifact/Vy2Rb9kb1JNUgtbt8cdcCJ (version 1).
Règle : **un nouveau lien à chaque amélioration** — on publie sous un nouveau nom de fichier.

## Les desks

| Fichier | Desk | Ordre | Tests |
|---|---|---|---|
| `src/desks/home.js` | Desk (hub, carte de séance, flux des décisions) | 0 | — |
| `src/desks/macro.js` | Macro (rapports transcrits, régime, calendrier, méthode) | 10 | banc `test/macro-fixture.js` |
| `src/desks/nq.js` | NQ futures (séance, niveaux GEX, contrat, taille) | 20 | 136 |
| `src/desks/micro.js` | Stratégie intraday (plan VWAP, setups, seuil µ*, lectures) | 30 | 303 |
| `src/desks/risk.js` | Risque (compte, jour, passage, règles) | 40 | 139 |
| `src/desks/quant.js` | Quant & backtest (Monte-Carlo, backtest, robustesse, échantillon) | 50 | 191 |
| `src/desks/perf.js` | Métriques & espaces (41 métriques, heatmaps 2D, surfaces 3D) | 55 | 240 |
| `src/desks/journal.js` | Journal (saisie scellée, registre, statistiques) | 60 | 149 |
| `src/desks/routine.js` | Routine & revue (avant, pendant, après, progression) + Réglages | 70 / 90 | 71 |

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
