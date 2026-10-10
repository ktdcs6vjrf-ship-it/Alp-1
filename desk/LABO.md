# Labo de stratégie — spécification

Ce document est le **contrat** du Labo de stratégie et du desk Données d'ALP Desk. Il complète
`CONTRACT.md` (lis-le d'abord : API `T.*`, style, règle « aucun chiffre de marché inventé »,
vérification). En cas de conflit, ce document l'emporte pour ce qu'il décrit.

L'utilisateur trade le MNQ. Il veut **créer une stratégie de zéro et la tester** avec les meilleurs
outils quantitatifs, et **ne rien saisir lui-même** : il envoie ses fichiers, captures et
descriptions à Claude, et Claude écrit tout dans sa base (outil `ArtifactData`). Le Labo doit donc
lire tout ce que Claude peut écrire, et tout ce que l'interface sait faire doit pouvoir être fait
par Claude en écrivant un document JSON.

## 0. Principes — ils viennent du dépôt ALP et ne se discutent pas

1. **Toute méthode vient avec sa loi nulle.** Un résultat de backtest ne s'affiche jamais seul : il
   est posé à côté de ce que donnent des entrées au hasard, des prix permutés et une marche sans
   dérive. Sans dérive, toute géométrie rend `E[R] = −c/L` (coût sur risque) : c'est le plancher
   théorique, et le Labo l'affiche.
2. **Pré-enregistrement.** Une stratégie se **scelle** (hachage + date) avant de voir le hors
   échantillon. Le hors échantillon (OOS) n'est calculé que pour une version scellée ; chaque
   ouverture est comptée, et au-delà d'une, le Labo écrit qu'il n'est plus hors échantillon.
3. **La multiplicité se compte toute seule.** Chaque configuration testée sur des données réelles
   est enregistrée (hachage). Le Sharpe déflaté et le verdict utilisent ce compte, jamais un
   chiffre saisi.
4. **Un paramètre déclaré n'est jamais dérivé de ce qu'il sert à évaluer.** Les seuils du verdict
   sont des règles déclarées, écrites dans le code avec leur justification, pas ajustées aux
   résultats.
5. **Aucune donnée de marché inventée.** Sans fichier de l'utilisateur, le Labo tourne sur une
   marche aléatoire sans dérive **annoncée comme telle** (« aucun avantage n'existe ici : une
   stratégie qui y gagne est surajustée »).
6. **Pas de prévision vendue.** Le Labo mesure ; il ne promet rien. Les mots « gagnante »,
   « rentable » ne qualifient jamais une stratégie sans l'intervalle et la loi nulle à côté.

## 1. Fichiers et propriétaires

| Fichier | Contenu | `T.lib` |
|---|---|---|
| `src/desks/labo-engine.js` | moteur de backtest autonome (worker) + enveloppes | `T.lib.laboEngine` |
| `src/desks/labo-stats.js` | normalisation, miroir, hachage, lecture en français, statistiques, verdict | `T.lib.laboStats` |
| `src/desks/labo-builder.js` | éditeur de stratégie (onglet Concevoir) | `T.lib.laboBuilder` |
| `src/desks/labo.js` | le desk « Labo de stratégie » (onglets) | `T.lib.labo` |
| `src/desks/donnees.js` | le desk « Données & imports » + codage des séances | `T.lib.donnees` |
| `tools/ingest.py` | conversion des fichiers de l'utilisateur en documents ArtifactData | — |
| `test/labo-*.test.js`, `test/donnees.test.js`, `tools/test_ingest.py` | tests | — |

`build.py` assemble `src/desks/*.js` par ordre alphabétique : `donnees`, …, `labo-builder`,
`labo-engine`, `labo-stats`, `labo`, … Chaque fichier n'utilise `T.lib.x` d'un autre fichier
**qu'au moment du rendu ou d'un appel**, jamais au chargement (l'ordre ne doit pas compter).

Le harnais de test charge plusieurs fichiers : `require('./harness')(['quant', 'labo-engine'])`
rend `{ T, lib }` où `lib` est `T.lib` du dernier (`labo-engine` → `T.lib.laboEngine`).

Socle disponible (déjà écrit, ne pas modifier) : tout `CONTRACT.md`, plus
`T.ucoll(chemin, {mirror, live})` — collection privée `data/users/<id>/<doc>/<collection>` :
`list()`, `get(id)`, `set(id, doc)`, `add(doc) → id`, `update(id, patch)`, `remove(id)`,
`on(fn) → désabonnement`, `ready() → Promise`, `cloud()`, `refresh()`. `mirror: false` pour les
grosses collections (pas de copie locale, suppression dure), `live: false` pour lire une fois au
lieu de s'abonner. `T.cloudReady()`, `T.onCloud(fn)`. Réutilisables d'autres desks :
`T.lib.quant` (`engine`, `parseCsv`, `synth`, `cscv`, `psr`, `dsr`, `wall`, `wilson`),
`T.lib.perf` (`metrics`, `bootstrap`, `dsr`, `psr`, `minTRL`, `charts.heatmap2d`,
`charts.surface3d`, `injectCss`, `surface` — voir la forme d'une surface plus bas),
`T.lib.risk` (`normAccount`, `simulate`).

## 2. Modèle de données

Tous les chemins ci-dessous sont relatifs à `data/users/<id>/` (espace privé de l'utilisateur).
Claude les écrit avec `ArtifactData`, collection `data/users/me/<doc>/<collection>`. Chaque
document porte `id` (= identifiant du document) et `u` (millisecondes de dernière écriture).

### 2.1 Jeux de barres

- Méta : `T.ucoll('datasets/items')` — un document par jeu :
  `{ id, name, instrument: 'MNQ'|'NQ', source: 'claude'|'fichier'|'synthetique', srcTz,
  step: 60000, from: 'AAAA-MM-JJ', to: 'AAAA-MM-JJ', sessions, bars, hasVolume, quantum,
  roll: 'ajuste'|'non-ajuste'|'inconnu', note, createdAt, u }`.
- Séances : `T.ucoll('ds-' + id + '/sessions', { mirror: false, live: false })` — **un document
  par séance Globex**, identifiant = clé de séance `AAAA-MM-JJ`.
- **Clé de séance Globex** : date new-yorkaise de l'instant décalé de six heures
  (`t + 6 h` lu à New York). La séance du lundi commence le dimanche à 18 h 00 (New York).
  C'est la partition de stockage ; le moteur re-découpe selon l'ancrage de la stratégie.
- **Codage `d1`** d'une séance (petits entiers, ≈ 20 Ko pour 1 380 barres) :
  ```
  { id: key, key, v: 1, t0: ms UTC de la 1re barre, step: 60000, n, q: quantum (0,25 en général),
    c0: prix de clôture de la 1re barre,
    m:  [n entiers] minutes depuis la barre précédente (m[0] = 0 ; 1 en général),
    dc: [n entiers] (c[k] − c[k−1]) / q, dc[0] = 0,
    o:  [n entiers] (o[k] − c[k]) / q,
    h:  [n entiers ≥ 0] (h[k] − c[k]) / q,
    l:  [n entiers ≥ 0] (c[k] − l[k]) / q,
    vol:[n entiers ≥ 0] }
  ```
  `t[k] = t0 + 60000·Σ_{j≤k} m[j]`, `c[k] = c0 + q·Σ_{j≤k} dc[j]`. Le quantum vaut le pas de
  cotation si tous les prix en sont des multiples (à 1e-6 près), sinon 0,01, sinon 0,0001 ;
  `decode(encode(x)) == x` au quantum près, et un test l'exige.
- Format en mémoire du moteur : **colonnes** `{ t, o, h, l, c, v }` (tableaux ou `Float64Array`
  de même longueur, `t` croissant strictement), plus `levels` optionnel (voir 2.2).

### 2.2 Niveaux nommés (GEX ou autres)

`T.ucoll('levels/items')` — un document par séance : `{ id: key, key, levels: { HVL: 21234.5,
CR: …, PS: … }, source, u }`. Le moteur les reçoit en `levels: { key: { nom: prix } }` ; un
niveau absent vaut `NaN` (la condition qui le lit est fausse).

### 2.3 Boîte de réception

`T.ucoll('inbox/items')` — ce que Claude a déposé :
`{ id, at, kind: 'trades'|'barres'|'strategie'|'niveaux'|'macro'|'note', title, count, detail,
ref (id du jeu, de la stratégie…), seen: false, u }`.

### 2.4 Stratégies

`T.ucoll('labo/strategies')` — **un document par version** : `id = sid + '_v' + version`.
Voir la grammaire en 3. Une version `scellee` ne se modifie plus ; modifier crée la version
suivante en `brouillon`.

### 2.5 Essais (multiplicité) et vues hors échantillon

`T.ucoll('labo/trials')` — un document par couple stratégie × jeu : `id = sid + '__' + dsId`,
`{ id, sid, ds, hashes: [hachages de configuration distincts testés en échantillon, ≤ 2000],
oos: { [hash de version scellée]: nombre d'ouvertures }, runs, last: {at, kind, n, meanR}, u }`.
Les jeux synthétiques n'y entrent pas (la multiplicité ne compte que sur données réelles).

### 2.6 Journal

Les trades de suivi portent `strat: sid` (et `stratV: version`) en plus du schéma du journal.
Claude écrit les trades importés dans `data/users/me/journal/trades/<id>` avec le schéma du
journal plus `{ id, u, src: 'import', imp: idImport }`. Un trade importé sans stop connu n'a
pas de `r` (le journal le gère déjà).

## 3. Grammaire d'une stratégie (JSON)

```js
{
  id, sid, version: 1, status: 'brouillon' | 'scellee', hash: null, sealedAt: null,
  createdAt, u, name: 'Rejet de bande VWAP, nuit',
  hypothesis: 'Pourquoi cela marcherait — écrit avant tout test (obligatoire pour sceller)',
  note: '',
  instrument: 'MNQ',                      // 'MNQ' (2 $/pt) | 'NQ' (20 $/pt), pas 0,25
  anchor: 'globex',                       // 'globex' (18:00 NY) | 'paris' (00:00 Paris) | 'rth' (09:30–16:00 NY)
  session: { tz: 'Europe/Paris', from: '00:00', to: '09:00', flat: '09:00', days: [1,2,3,4,5], warmup: 15 },
  split: { oosFrom: 'AAAA-MM-JJ' | null }, // séances ≥ oosFrom = hors échantillon (choisi avant de sceller)
  side: 'long' | 'short' | 'both',
  mirror: true,                           // le côté vendeur est le miroir exact du côté acheteur
  long:  { setup: [Cond…], trigger: Cond, entry: Entry, stop: Stop, target: Target },
  short: null,                            // obligatoire si side ≠ 'long' et mirror = false
  manage: { breakeven: null | { at: R }, trail: null | { by: 'pts'|'atr'|'r', value, start: R },
            maxBars: null | n, exitOnOpposite: false },
  risk: { mode: 'contracts' | 'risk', contracts: 1, riskUsd: 150,
          maxPerSession: 3, maxLossesPerSession: 2, dailyStopUsd: 400, cooldown: 0 },
  costs: { commissionRT: null, slipTicks: 1 }, // null = réglage de l'utilisateur ; glissement par côté
  fill: 'pessimiste' | 'optimiste' | 'chemin',
  params: { nom: { v: 2, min: 1, max: 3, step: 0.25, label: 'k (σ)' } }
}
```

Toute valeur numérique d'une règle peut s'écrire `"$nom"` : elle vaut alors `params.nom.v`
(ou la valeur imposée par un balayage). Un `$nom` sans paramètre est une erreur de validation.

### 3.1 Opérandes (évalués à la clôture de la barre `i`, causalement)

| Forme | Valeur à la barre i |
|---|---|
| nombre, `"$p"` | constante |
| `{f:'close'\|'open'\|'high'\|'low'\|'hl2'\|'hlc3'\|'volume'\|'range'\|'body', lag?}` | champ de la barre `i − lag` (`range` = h − l, `body` = c − o) |
| `{f:'vwap', k?}` | VWAP de séance (selon `anchor`) + k·σ (k = 0 par défaut) |
| `{f:'ema'\|'sma'\|'atr'\|'rsi', n, lag?}` | moyennes sur la clôture (EMA amorcée par la SMA des n premières), ATR et RSI de Wilder, continues d'une séance à l'autre |
| `{f:'hh'\|'ll', n}` | plus haut / plus bas des barres `i−n … i−1` (barre courante exclue) |
| `{f:'prev', of:'high'\|'low'\|'close'}` | haut, bas, dernière clôture de la séance précédente |
| `{f:'sess', of:'high'\|'low'\|'open'}` | haut / bas de la séance jusqu'à `i−1` ; ouverture = 1re barre |
| `{f:'or', from:'HH:MM', to:'HH:MM', tz?, of:'high'\|'low'\|'mid'}` | range des barres d'horloge ∈ [from, to) de la séance ; `NaN` tant que l'horloge < to |
| `{f:'level', name}` | niveau nommé de la séance (2.2) |
| `{f:'time'}`, `{f:'dow'}`, `{f:'sessmin'}` | minutes depuis minuit (tz de `session`), jour 1–7 (lundi = 1), minutes depuis le début de séance |
| `{f:'dist', a, b, unit:'pts'\|'ticks'\|'atr'\|'sd', n?}` | `(a − b)` en points, ticks, ATR(n = 14) ou σ de VWAP |

VWAP et σ : prix typique `hlc3` pondéré par le volume (poids égaux sans volume), cumulés depuis
le début de séance — identique à `quantEngine` (`sessionVwap`). Un opérande indéfini (`NaN`,
pas assez d'historique) rend **toute** condition qui le lit fausse.

### 3.2 Conditions

| Forme | Vraie à la barre i si |
|---|---|
| `{cmp:'>'\|'<'\|'>='\|'<=', a, b}` | `a[i] cmp b[i]` |
| `{cross:'up'\|'down', a, b}` | up : `a[i−1] ≤ b[i−1]` et `a[i] > b[i]` |
| `{touch: L, from:'above'\|'below'}` | above : `low[i] ≤ L[i]` et `close[i−1] > L[i−1]` |
| `{reject: L, from:'above'\|'below'}` | above : touche par le haut **et** `close[i] > L[i]` |
| `{break: L, dir:'up'\|'down'}` | up : `close[i] > L[i]` et `close[i−1] ≤ L[i−1]` |
| `{bar:'up'\|'down'}` | `close > open` / `close < open` |
| `{time:['HH:MM','HH:MM']}` | horloge (tz de `session`) dans l'intervalle (passage de minuit permis) |
| `{all:[…]}`, `{any:[…]}`, `{not: Cond}` | logique |
| `{for: n, cond}` | `cond` vraie sur les n dernières barres (i−n+1 … i) |
| `{within: n, cond}` | `cond` vraie sur au moins une des n dernières barres |

Un signal = `setup` (toutes vraies) **et** `trigger` vrais à la clôture de `i`.

### 3.3 Miroir

Le côté vendeur d'une stratégie `mirror: true` est **la réflexion des prix** : on remplace chaque
prix `p` par `K − p`. La transformation syntaxique est donc, et seulement : `k → −k` (VWAP) ;
`high ↔ low` (champs, `hh ↔ ll`, `prev`, `sess`, `or`) ; `body → −body`, `dist(a,b) → dist(b',a')` ;
`rsi` comparé à `x` → comparaison inversée à `100 − x` ; comparaisons `<`↔`>` et `<=`↔`>=`
quand elles portent sur des prix ; `cross up ↔ down`, `touch/reject above ↔ below`,
`break up ↔ down`, `bar up ↔ down`. Ce qui n'est pas un prix (`time`, `dow`, `sessmin`,
`volume`, `range`, `atr`, σ) ne change pas. **Une constante comparée à un prix ne se reflète
pas** : `mirror` est refusé (erreur de validation) si une règle compare un prix à un nombre.
Test obligatoire : évaluer la règle reflétée sur la série réelle = évaluer la règle d'origine
sur la série réfléchie, barre par barre, sur des données aléatoires.

### 3.4 Entrée, stop, objectif

Le signal est connu à la **clôture** de i ; rien ne s'exécute avant `i + 1`.

- `Entry` : `{type:'market'}` → ouverture de i+1, glissement défavorable.
  `{type:'limit', at: Opérande, offset: ticks, valid: barres (1), through: true}` → ordre posé
  après la clôture de i au prix `at[i] − offset·tick` (achat), actif de i+1 à i+valid ; rempli si
  `low[j] < prix` (`through`) ou `≤` ; prix = `min(open[j], prix)` ; pas de glissement.
  `{type:'stop', at, offset, valid}` → rempli si `high[j] ≥ prix` ; prix = `max(open[j], prix)`
  + glissement. Un ordre en attente expire en fin de validité, hors fenêtre ou en fin de séance.
- `Stop` (fixé à l'exécution, distance ≥ 1 tick, sinon le trade est annulé) :
  `{type:'pts', value}` · `{type:'atr', value, n:14}` (ATR à la barre du signal) ·
  `{type:'swing', n}` (plus bas des n dernières barres, barre du signal comprise) ·
  `{type:'level', at}` (opérande à la barre du signal) ; `buffer: ticks` éloigne le stop.
  Si l'exécution se fait déjà au-delà du stop (écart d'ouverture), le trade est **annulé** et
  compté.
- `Target` : `{type:'r', value}` (multiple du risque initial) · `{type:'pts', value}` ·
  `{type:'atr', value, n}` · `{type:'level', at, dynamic:false}` (dynamique : réévalué à chaque
  barre sur la valeur de la barre précédente, comme l'objectif VWAP de `quantEngine`) ·
  `{type:'none'}`. Un objectif déjà dépassé à l'exécution annule le trade.

### 3.5 Gestion barre par barre (position ouverte, barre j)

1. Si l'horloge de j ≥ `flat` : sortie à `open[j]` (glissement) — `flat`.
2. Écart d'ouverture : `open[j]` au-delà du stop → sortie à `open[j]` (glissement) ; au-delà de
   l'objectif → sortie à `open[j]` (sans glissement).
3. Dans la barre : stop touché si `low ≤ stop` (achat), objectif si `high ≥ objectif`. Les deux :
   `pessimiste` → stop ; `optimiste` → objectif ; `chemin` → barre haussière (c ≥ o) lue
   O→L→H→C (stop d'abord), baissière O→H→L→C (objectif d'abord). Stop exécuté au stop moins le
   glissement ; objectif exécuté exactement.
4. Barre d'entrée : après une exécution au marché (à l'ouverture), on applique 3. Après une
   exécution limite (achat pendant la baisse), `chemin` : barre haussière → stop puis objectif ;
   baissière → stop seulement. Après une exécution stop (achat pendant la hausse), `chemin` :
   haussière → objectif seulement ; baissière → objectif puis stop. `pessimiste` et `optimiste`
   gardent leur règle.
5. Sinon : `maxBars` atteint → sortie à `close[j]` (glissement) — `temps` ; signal opposé à la
   clôture (`exitOnOpposite`) → sortie à l'ouverture suivante — `oppose` ; dernière barre de la
   séance ou des données → sortie à `close[j]` (glissement) — `cloche`.
6. Mise à jour pour la barre suivante (jamais pour la barre courante) : seuil de break-even
   atteint par le plus haut de j → stop à l'entrée ; stop suiveur après `start`·R :
   `stop = max(stop, plus haut depuis l'entrée − distance)`.

Raisons de sortie : `stop`, `be`, `trail`, `objectif`, `temps`, `flat`, `cloche`, `oppose`.

### 3.6 Taille, coûts, limites

- `contracts` : quantité fixe. `risk` : `qty = floor(riskUsd / (|entrée − stop|·pv + commission))`,
  calculée à l'exécution ; `qty < 1` → trade annulé et compté (`taille`).
- `pnl = qty·(sens·(sortie − entrée)·pv − commission)` ; le glissement est déjà dans les prix.
  `r = pnl / (qty·|entrée − stop initial|·pv)`.
- Une seule position à la fois. Après une sortie, `cooldown` barres sans signal. Par séance :
  `maxPerSession` entrées, `maxLossesPerSession` pertes, `dailyStopUsd` de perte nette → plus
  d'entrée dans la séance. Signal acheteur et vendeur sur la même barre → aucun trade (`ambigu`).
- Fenêtre d'entrée : horloge ∈ [`from`, `to`) dans `session.tz`, jour ∈ `days`, au moins
  `warmup` minutes après le début de la séance, pas sur la dernière barre de la séance.

## 4. Moteur — `labo-engine.js`

Une **fonction autonome** `function laboEngine(a, Q)` (aucune variable extérieure, aucun `T`),
exécutée dans un worker : `labo.js` fabrique la fonction du worker avec
`new Function('a', 'var Q=(' + T.lib.quant.engine + ');var E=(' + laboEngine + ');return E(a, Q);')`
et l'appelle par `T.compute`. `Q` (le moteur de `quant.js`) sert à `synth` ; il peut être absent
pour les autres opérations. `T.lib.laboEngine = { engine: laboEngine, run, …enveloppes }` expose
des enveloppes synchrones pour les tests et les petits calculs.

Entrée commune : `a = { op, bars: {t,o,h,l,c,v}, levels?, spec (normalisée, paramètres résolus),
settings: { commissionRT, pointValue, tick }, sel?: { from, to } (clés de séance des entrées),
seed?, draws?, … }`. Toute opération est **déterministe** à graine égale (mulberry32 recopié).

| `op` | Sortie |
|---|---|
| `run` | `{ trades, counts: {signals, ambigu, taille, ecart, annule, expire}, sessions: [{key, pnl, n}], fill, costs, warnings }` ; trade = `{ i, j, t, tx, key, side, qty, entry, stop0, target0, exit, fin, pts, pnl, r, risk, mae, mfe, bars, hour, dow }` (mae/mfe en points, heure de Paris) |
| `envelope` | `run` en `pessimiste` et en `optimiste` : `{ pess: {…stats, eq}, opt: {…} }` |
| `random` | loi nulle des entrées au hasard (4.2) : `{ means, nets, obs, p, lo, hi }` |
| `permute` | test de permutation (4.3) : `{ means, nets, ns, obs, p, pNet }` |
| `synth` | même stratégie sur marche sans dérive calibrée (4.4) : `{ stats, predicted: −c/L, sigma }` |
| `sweep` | grille sur 1 ou 2 paramètres : `{ p1, p2, xs, ys, cells: [[{n, meanR, net, pf, sharpe, maxDD, winRate}]], perSession: [[pnl par séance]], best }` |
| `wfa` | analyse en avant (4.5) |
| `stress` | coûts : glissement 0–4 ticks × commission ×1, ×1,5, ×2 → `meanR`, `net` ; glissement d'équilibre interpolé |
| `boot` | bootstrap stationnaire des séances : intervalles, éventail d'équité, passage prop (4.6) |
| `features` | les séries calculées pour une liste d'opérandes (pour les graphiques et les tests) |

Performance : une année de barres d'une minute (≈ 350 000) se parcourt en moins d'une seconde
par configuration ; les séries sont calculées une fois par configuration et mises en cache par
clé d'opérande pendant l'appel.

### 4.1 Statistiques d'un run

`{ n, wins, losses, winRate, meanR, sdR, sharpeTrade (= meanR/sdR), net, avgWin, avgLoss, pf,
maxDD ($, sur l'équité des trades), expectancy ($/trade), equilibrium (= taux de réussite qui
annule l'espérance compte tenu de R:R moyen et des coûts), byFin, costR (coût moyen / risque
moyen) }`. `−costR` est la prédiction sans avantage d'ALP (`−c/L`).

### 4.2 Entrées au hasard

`draws` tirages (200 par défaut). Pour chaque séance, autant d'entrées que la stratégie en a
pris, à des barres tirées uniformément parmi les barres éligibles (fenêtre, jours, warmup) ;
sens = celui de la stratégie (`both` : tiré avec la proportion observée d'achats). Chaque entrée
est exécutée **au marché** à la barre suivante avec le stop et l'objectif **de la stratégie**
évalués à cette barre ; un stop ou un objectif de type `level` impossible à cette barre est
remplacé par la distance médiane observée. Trades simulés indépendamment. `p = (1 + #{moyenne
tirée ≥ moyenne observée}) / (draws + 1)`.

### 4.3 Permutation (Masters)

`draws` (100 par défaut). Dans chaque séance, on permute les barres 2 … m (chacune garde son
écart d'ouverture `o − c_prec`, sa forme `h − o`, `l − o`, `c − o` et son volume) et on
reconstruit les prix depuis la première barre ; les heures restent. On recalcule toutes les
séries et on rejoue la stratégie entière. `p` comme en 4.2, sur la moyenne en R et sur le net.

### 4.4 Marche sans dérive calibrée

σ = écart-type médian des variations de clôture d'une minute du jeu ; `Q({op:'synth', o:{seed,
sigma, days: min(120, séances), tick}})` ; même stratégie. Affiche la moyenne mesurée et `−c/L`.

### 4.5 Analyse en avant (walk-forward)

`{ is: n séances, oos: m séances, mode: 'rolling'|'anchored', grid: {p1:[…], p2?:[…]},
objective: 'meanR'|'net'|'sharpe'|'pf', minTrades }`. Fenêtres successives ; sur chaque fenêtre
IS, la meilleure configuration (égalité → la première, moins de `minTrades` → exclue) est
appliquée telle quelle à la fenêtre OOS suivante. Sortie : `{ windows: [{isFrom, isTo, oosFrom,
oosTo, best, isMetric, oosMetric, oosN}], oosTrades, stitched: stats, wfe }`,
`wfe = moyenne OOS / moyenne IS` (indéfini si la moyenne IS ≤ 0).

### 4.6 Bootstrap et passage d'un compte prop

Bootstrap stationnaire (Politis–Romano, bloc moyen 5 séances) des **séances** (P&L par séance) :
intervalle à 90 % de la moyenne par trade et du net annuel, éventail d'équité (quantiles 5, 25,
50, 75, 95 sur 60 séances). Passage : `{ size, target, maxLoss, dd: 'eod'|'intraday'|'static',
dailyLoss, minDays, maxDays }` (pris de `T.lib.risk.normAccount(T.store.get('risk:account'))`
si présent, sinon saisis) → probabilités de réussite, d'échec, de non-conclusion, jours médians.

## 5. Statistiques et verdict — `labo-stats.js`

`T.lib.laboStats` (fonctions pures, fil principal) :

- `normalize(raw) → { spec, errors: [], warnings: [] }` : valeurs par défaut, types, `$param`
  résolubles, `mirror` refusé si une constante est comparée à un prix, `short` exigé si besoin.
- `resolve(spec, overrides) → spec` sans `$` ; `mirrorRules(long) → short` (3.3).
- `hash(spec) → 'h…'` : FNV-1a 64 bits (deux moitiés de 32) du JSON canonique (clés triées) des
  champs de règle (tout sauf `id`, `name`, `note`, `hypothesis`, `status`, dates, `u`) **avec les
  valeurs de paramètres**. `configHash(spec, overrides)` pour les essais.
- `describe(spec) → [{ title, text }]` : lecture en français, phrase par bloc (séance, sens,
  contexte, déclencheur, entrée, stop, objectif, gestion, risque, coûts, remplissage), y compris
  le côté vendeur reflété. Aucune phrase vide, aucun `undefined`, apostrophes typographiques.
- `stats(trades, o)` (4.1), `equity(trades)`, `bySession`, `byHourDow`, `byMonth`.
- `dsr({ sr, n, N, skew, kurt, sdTrials })`, `minTRL`, `tradesForSharpe` (route d'ALP, 619 pour
  0,10), `pbo(perSession)` via `T.lib.quant.cscv`, `plateau(cells, best)` (moyenne des voisins /
  meilleur), `stability(cells)` (part des cellules d'espérance positive).
- `sprt(xs, mu1, sigma, alpha = 0.05, beta = 0.2)` : rapport de vraisemblance cumulé sous loi
  normale, bornes de Wald `ln((1−β)/α)` et `ln(β/(1−α))`, décision `accepter|rejeter|continuer` ;
  `cusum(xs, target, k, h)`.
- `TEMPLATES` : gabarits de départ (rejet de bande VWAP, cassure du range d'ouverture, retour à
  la moyenne RSI, rejet du haut/bas de la veille, poursuite au-dessus de l'EMA) — **des points de
  départ, aucun ne prétend à un avantage**.
- `verdict(r) → { items: [{ id, label, value, pass: true|false|null, why }], level:
  'rejetee'|'a-approfondir'|'prete-simulateur', text }`. Règles déclarées (constante `GATES`,
  chacune avec sa justification en commentaire) : au moins 30 trades en échantillon ; p des
  entrées au hasard < 0,05 ; p de permutation < 0,05 ; Sharpe déflaté ≥ 0,95 avec N = essais
  comptés ; PBO ≤ 0,2 (si balayage) ; plateau ≥ 0,7 (si balayage) ; glissement d'équilibre ≥
  glissement déclaré + 1 tick ; OOS scellé, ouvert une fois, espérance > 0 ; WFE ≥ 0,5 (si
  analyse en avant) ; échantillon ≥ longueur minimale de suivi. Un critère non mesuré vaut
  `null` et empêche « prête ».

## 6. Desk « Labo de stratégie » — `labo.js` + `labo-builder.js`

`id: 'labo'`, `label: 'Labo de stratégie'`, `glyph: 'L'`, `group: 'Recherche'`, `order: 45`.
Onglets : `concevoir`, `tester`, `valider`, `verdict`, `suivre`. Titres avec un mot en italique
serif, phrases courtes. Chaque calcul lourd passe par `T.compute` avec un état « calcul en
cours » et un cache par clé (spécification + jeu + paramètres).

En-tête commun : stratégie courante (sélecteur de versions), jeu de données courant
(synthétique / jeux du compte / fichier local de cette visite, via `T.lib.donnees`), état
(brouillon / scellée, hachage court).

- **Concevoir** (`T.lib.laboBuilder.render(root, ctx, api)`) : liste des stratégies, « Nouvelle »
  (vierge ou depuis un gabarit), éditeur par blocs (séance, sens et miroir, contexte, déclencheur,
  entrée, stop, objectif, gestion, risque et coûts, paramètres), lecture en français en direct,
  hypothèse, date de coupure OOS, boutons Enregistrer, Sceller, Nouvelle version, Dupliquer,
  Supprimer, et « Décrire à Claude » (rappel : l'utilisateur peut écrire sa stratégie en mots à
  Claude, qui l'écrit ici). Un sélecteur d'opérande uniforme (type puis arguments). Chaque nombre
  d'une règle est un paramètre nommé automatiquement. La saisie ne détruit jamais un champ en cours
  de frappe.
- **Tester** (échantillon) : indicateurs (n, réussite contre taux d'équilibre, espérance en R et
  en $, net, PF, Sharpe par trade, perte maximale) ; courbe d'équité avec l'**enveloppe**
  pessimiste/optimiste ; sous-l'eau ; histogramme des R ; nuage MAE/MFE ; carte heure × jour ;
  sankey des issues (signaux → pris / annulés → objectif / stop / temps / clôture…) ; **les trois
  lois nulles** (histogrammes avec la valeur observée et p) ; liste des trades ; bouton
  « Ouvrir dans Métriques » (écrit `quant:lastBacktest` au format de `quant.js`).
- **Valider** : balayage de deux paramètres → carte de chaleur 2D et surface 3D
  (`T.lib.perf.charts`), plateau, stabilité ; PBO ; analyse en avant (barres IS/OOS par fenêtre
  + équité OOS cousue + WFE) ; stress des coûts (courbe + glissement d'équilibre) ; bootstrap
  (éventail, intervalles) ; Sharpe déflaté avec N compté ; sous-périodes (mois).
- **Verdict** : la liste des critères calculés, le niveau, le passage d'un compte prop ; le hors
  échantillon (scellé seulement), avec le compteur d'ouvertures.
- **Suivre** : trades du journal portant `strat`, saisie rapide (sens, entrée, stop, objectif,
  sortie, quantité → P&L et R calculés, écrits dans le journal avec `strat`), SPRT contre
  l'espérance du backtest, CUSUM, écart à l'enveloppe.

Une surface pour `T.lib.perf.charts.heatmap2d/surface3d` a la forme de `T.lib.perf.surface()` :
`{ title, x: {name, dom, fmt}, y: {…}, z: {name, fmt}, xs, ys, vals[ny][nx], zmin, zmax, mid,
midLabel, line: [], lineLabel, fn(x, y) (valeur de la cellule la plus proche), argmax: [i, j] }`.
Appeler `T.lib.perf.injectCss()` avant de les rendre.

## 7. Desk « Données & imports » — `donnees.js`

`id: 'donnees'`, `label: 'Données & imports'`, `glyph: 'D'`… (le hub est déjà « D » : prendre
`'⇣'`), `group: 'Système'`, `order: 85`. Onglets : `boite` (boîte de réception, marquer lu),
`series` (jeux de barres : liste, rapport de qualité — séances, minutes manquantes, écarts, barres
plates, sauts de roll —, aperçu, suppression, **chargement d'un CSV local** via
`T.lib.quant.parseCsv` dans un worker puis « Enregistrer dans mon compte » avec progression),
`niveaux` (niveaux nommés par séance), `envoyer` (ce qu'il faut envoyer à Claude et comment :
barres d'une minute en CSV, export des trades de la plateforme, captures ; aucune instruction de
menu de plateforme non vérifiée — écrire « l'export CSV de ta plateforme »).

`T.lib.donnees` : `sessionKey(t)`, `encodeSession(cols, i0, i1)`, `decodeSession(doc)`,
`splitSessions(cols)`, `quality(cols)`, `datasets()`, `loadDataset(id) → Promise<{ meta, bars,
levels }>` (cache mémoire), `saveDataset(meta, cols, onProgress)`, `deleteDataset(id)`,
`levelsMap()`, `inbox()`, `synthetic(o)` (via `T.lib.quant.synth`, méta `source: 'synthetique'`).

## 8. Outil d'ingestion — `tools/ingest.py`

Python 3.11, **bibliothèque standard seulement** (`zoneinfo` compris). Il prépare ce que Claude
envoie avec `ArtifactData` (`batch`, ≤ 50 écritures et ≤ 900 Ko par lot) :

```
python3 tools/ingest.py bars FICHIER.csv --tz America/New_York --name "MNQ 1 min" --instrument MNQ --out DOSSIER
python3 tools/ingest.py trades FICHIER.csv --tz Europe/Paris --instrument MNQ --out DOSSIER
python3 tools/ingest.py levels FICHIER.txt|.md --date AAAA-MM-JJ --out DOSSIER
```

Chaque commande écrit un fichier JSON par document et `batches.json` : une liste de lots
`[{ writes: [{ op: 'set', collection, doc_id, file_path }] }]`, plus le document de boîte de
réception. `bars` lit les mêmes formats que `quantEngine.parseCsv` (alias de colonnes, date et
heure séparées ou jointes, séparateurs), découpe en séances Globex et code en `d1` (identique au
JavaScript : un test croisé décode en JS ce que Python a codé). `trades` reconnaît les en-têtes
courants (symbole, sens, quantité, prix et heures d'entrée et de sortie, P&L, commission) par
alias, apparie des exécutions en allers-retours FIFO si le fichier liste des exécutions, et
produit des entrées de journal (`kind: 'pris'`, `status: 'clos'`, `src: 'import'`, identifiant
stable dérivé du contenu pour qu'un second import ne duplique rien). `levels` lit un collage de
niveaux nommés (`NOM : prix`). Tests : `python3 -m unittest tools/test_ingest.py`.

## 9. Tests et vérification

Chaque fichier a ses tests (`node test/<nom>.test.js`, sortie non nulle si échec). Obligatoires :

- **Causalité** : modifier les barres après i ne change aucun signal ≤ i ni aucune série ≤ i.
- **Exécution** : cas construits à la main pour chaque type d'entrée, de stop, d'objectif, chaque
  politique de remplissage, l'écart d'ouverture, le break-even, le suiveur, `maxBars`, `flat`,
  `cloche`, les limites de séance, la taille au risque, l'annulation.
- **Miroir** : 3.3 (égalité barre par barre) ; une stratégie `both` sur une série et sur sa
  réflexion rend les mêmes trades de sens opposés.
- **Loi nulle d'ALP** : sur 60 séances synthétiques sans dérive, la moyenne en R de plusieurs
  géométries tombe dans l'intervalle à 95 % de `−c/L`.
- **Puissance** : une série où l'on plante un avantage connu (dérive dans la fenêtre) donne
  p < 0,05 aux entrées au hasard et à la permutation ; sans avantage, p ne l'est pas plus souvent
  que prévu (≈ 5 % sur 40 graines, tolérance large).
- **Déterminisme**, **codage d1** (aller-retour exact, taille), **hachage** stable, **lecture en
  français** sans `undefined`/`NaN`, **SPRT** (bornes, décisions), **DSR/PBO** contre
  `T.lib.quant`/`T.lib.perf`.

Puis : `python3 build.py --fonts --out <scratchpad>/desk/dist/integ.html` (le serveur d'aperçu sert
le scratchpad), `node test/e2e.js …` → `"bad": 0` à 390 et 1280 px, et **regarder les captures**.
