# Labo de stratégie — spécification (version 2)

Ce document est le **contrat** du Labo de stratégie et du desk Données d'ALP Desk. Il complète
`CONTRACT.md` (lis-le d'abord : API `T.*`, style, règle « aucun chiffre de marché inventé »,
vérification). En cas de conflit, ce document l'emporte pour ce qu'il décrit. La version 1 a été
relue par deux critiques indépendants (méthode quantitative, ingénierie) ; leurs 37 constats sont
intégrés ici, et les mesures qui les fondent sont citées là où elles décident d'une règle.

L'utilisateur trade le MNQ. Il veut **créer une stratégie de zéro et la tester** avec les meilleurs
outils quantitatifs, et **ne rien saisir lui-même** : il envoie fichiers, captures et descriptions
à Claude, qui écrit tout dans sa base (`ArtifactData`) et ses fichiers attachés (`assets`). Tout ce
que l'interface sait faire doit donc pouvoir être fait par Claude en écrivant un document JSON, et
tout ce que le Labo calcule doit être relisible par Claude (2.8).

## 0. Principes — ils viennent du dépôt ALP et ne se discutent pas

1. **Toute méthode vient avec sa loi nulle.** Un résultat ne s'affiche jamais seul : il est posé à
   côté d'entrées au hasard (même exécution), de prix permutés, et d'une marche sans dérive où
   `E[R] = −c/L` (coût sur risque, trade par trade : 4.1).
2. **Pré-enregistrement.** Une stratégie se **scelle** (hachage + date) avant le hors échantillon.
   Le hors échantillon appartient à l'**instrument**, pas à la stratégie : sa date de coupure est
   fixée une fois pour toutes (2.6) et chaque ouverture est enregistrée, jamais décomptée.
3. **La multiplicité se compte toute seule**, dans un registre en ajout seul, par instrument et
   par période (2.5) : dupliquer une stratégie, réimporter un fichier ou changer de lien ne
   remettent rien à zéro.
4. **Un paramètre déclaré n'est jamais dérivé de ce qu'il sert à évaluer.** Les seuils du verdict
   (`GATES`) sont des constantes du code, chacune avec sa justification ; les coûts du verdict ont
   des planchers déclarés que la stratégie ne peut pas abaisser.
5. **Aucune donnée de marché inventée.** Sans fichier de l'utilisateur, le Labo tourne sur une
   marche aléatoire sans dérive **annoncée comme telle** (« aucun avantage n'existe ici : une
   stratégie qui y gagne est surajustée »).
6. **Pas de prévision vendue.** « Gagnante », « rentable » ne qualifient jamais une stratégie sans
   l'intervalle et la loi nulle à côté.

## 1. Fichiers et propriétaires

| Fichier | Contenu | `T.lib` |
|---|---|---|
| `src/desks/labo-engine.js` | moteur autonome (worker) : séances, séries, règles, exécution, statistiques, lois nulles, balayages ; exécuteur de worker ; enveloppes | `T.lib.laboEngine` |
| `src/desks/labo-stats.js` | `GRAMMAR`, normalisation, hachage, lecture en français, DSR, PBO, SPRT, verdict, gabarits | `T.lib.laboStats` |
| `src/desks/labo-builder.js` | éditeur de stratégie (onglet Concevoir) | `T.lib.laboBuilder` |
| `src/desks/labo.js` | le desk « Labo de stratégie » | `T.lib.labo` |
| `src/desks/donnees.js` | le desk « Données & imports », codage des séances, jeux, niveaux, boîte | `T.lib.donnees` |
| `tools/ingest.js` | Node sans dépendance : fichiers de l'utilisateur → documents et assets pour Claude | — |
| `tools/labo-check.js` | Node : valide et lit en français une stratégie JSON avant que Claude l'écrive | — |
| `test/labo-*.test.js`, `test/donnees.test.js`, `test/ingest.test.js` | tests | — |

`build.py` assemble `src/desks/*.js` par ordre alphabétique et accepte `--only a,b,c` (liste).
Chaque fichier n'utilise `T.lib.x` d'un autre fichier **qu'au rendu ou à l'appel**, jamais au
chargement. **Une seule implémentation par fonction** : `resolve`, `mirror`, les statistiques
de run (4.1) et la clé de séance vivent dans `laboEngine` ; `T.lib.laboStats.resolve/mirror/stats`
et `T.lib.donnees.sessionKey` en sont des enveloppes synchrones, et un test vérifie
l'égalité enveloppe = op. Les outils Node chargent les fichiers du desk par `test/harness.js`
(`require('./harness')(['quant', 'labo-engine', 'labo-stats', 'donnees'])` rend `{T, lib, ctx}`,
`lib` = `T.lib` du dernier, nom en camelCase) : il n'y a pas de seconde implémentation à garder
en parité.

Socle disponible (ne pas modifier) : tout `CONTRACT.md`, plus `T.ucoll(chemin, {mirror, live})`
(collection privée `data/users/<id>/<doc>/<collection>` : `list`, `get`, `set`, `add`, `update`,
`remove`, `on`, `ready`, `cloud`, `refresh` — voir `src/core.js`), `T.cloudReady()`,
`T.onCloud(fn)`. Réutilisables : `T.lib.quant` (`engine`, `parseCsv`, `cscv`, `psr`, `dsr(sr, n,
N, skew, exkurt, sdTrials)`, `route1`, `wilson`, `wallToUtc`, `backtest` — `wall` est le **mur
d'échantillon**, pas l'heure murale), `T.lib.perf` (`metrics`, `bootstrap`, `charts.heatmap2d`,
`charts.surface3d`, `injectCss`, `surface`), `T.lib.risk` (`normAccount` → `size, target,
maxLoss, dd, lockAt, dailyLimit, dailyMode, maxContracts, consistency`, `simulate`).

## 2. Données

Chemins relatifs à `data/users/<id>/` (privé). Claude écrit avec `ArtifactData`, collection
`data/users/me/<doc>/<collection>`. Tout document porte `id` (= identifiant) et `u` (ms).

### 2.0 Durée de vie, lien, migration

La base et les assets d'un artefact lui appartiennent : ils survivent aux republications du
**même** lien et n'existent pas sur un nouveau lien (base vide, stockage local vide). L'utilisateur
veut un nouveau lien à chaque amélioration : **avant d'annoncer un nouveau lien, Claude migre tout**,
dans cet ordre : (1) `labo/essais`, `labo/oos`, `labo/config` ; (2) `labo/strategies`,
`labo/results` ; (3) les assets de barres (copie côté serveur : `Artifact publish` avec `url` du
nouveau lien, `asset: true`, `from_url` = ancien lien, `asset_ids` ≤ 10 par appel), puis
`datasets/items` réécrit avec les nouveaux identifiants ; (4) `levels/items`, `journal/trades`,
`inbox/items` ; (5) la collection `data/users/me` (clés `T.store`, documents `{t, v}`). Lecture :
`ArtifactData list` (limit 1000, curseur, `out_dir`) ; écriture : lots ≤ 50 entrées et ≤ 900 Ko.
Puis Claude écrit la clé `T.store` `labo:lignee` (`{t, v: {sources: [liens], migreLe, comptes:
{collection: n}}}`) et un élément de boîte `kind: 'migration'`. Le Labo affiche la lignée à côté
de N (« dont M essais hérités ») ; si un compte local est inférieur à `lignee.comptes`, le niveau
« prête » est bloqué (migration incomplète).

### 2.1 Jeux de barres

- Méta : `T.ucoll('datasets/items')`, un document par jeu, `id` = `/^ds[a-z0-9]{6,20}$/` :
  `{ id, name, instrument: 'MNQ'|'NQ', source: 'claude'|'fichier'|'synthetique', srcTz,
  stamp: 'ouverture'|'cloture', from, to (clés), sessions, bars, hasVolume, D,
  roll: 'ajuste'|'non-ajuste'|'inconnu', fingerprint, assets: [{ year, id (asset), sessions,
  from, to, bytes }], complete: true, deleting?: true, note, createdAt, u }`.
- Barres : **un asset JSON par année** (`application/json`, ≤ 20 Mio, ≈ 5,5 Mo par an) :
  `{ v: 2, instrument, year, D, sessions: [séance d1, …] }`. Claude le téléverse en un appel
  (`Artifact publish`, `url`, `file_path`, `asset: true`) ; la page avec `assets.upload(blob,
  {type: 'application/json'})` (capacité `assets`, écrivain seulement). Lecture partout par
  `fetch('/_blob/' + id)` ; l'`ArrayBuffer`/texte est décodé dans le worker.
- **Clé de séance Globex** (définie par le code de `sessionVwap`) : date UTC de
  `t + décalage(New York, t) + 6 h`. La séance du lundi commence le dimanche à 18 h 00 New York.
- **Séance d1 v2** (petits entiers, ≈ 20 Ko pour 1 380 barres) :
  ```
  { key, t0 (ms UTC, heure d'OUVERTURE de la 1re barre), n, D, C0,
    m:  [n] minutes depuis la barre précédente (m[0] = 0),
    dc: [n] Ck − Ck−1 en unités 1/D (dc[0] = 0),
    o, h, l: [n] (O−C), (H−C) ≥ 0, (C−L) ≥ 0 en unités 1/D,
    vol: [n] entiers | null (source sans volume),
    adj?: points ajoutés à cette séance par un ajustement arrière, contract?: 'MNQZ5', roll?: true }
  ```
  Prix entiers `P = Math.floor(p·D + 0.5)` (même formule partout, jamais `round`). `D` = le plus
  petit de (1/tick = 4, 100, 10 000) tel que `|p·D − P| ≤ 1e-6` pour tous les prix ; sinon l'import
  est refusé (« prix non décimaux : série ajustée par ratio ? »). Décodage : `c[k] = (C0 +
  Σ_{j≤k} dc[j]) / D`, `o[k] = (Ck + o[k]) / D`, etc. — la division rend le même double que la
  lecture du texte décimal, et un test exige `decode(encode(x)) === x` bit pour bit. `t[k] = t0 +
  60000·Σ m`. Une barre dont `t` n'est pas multiple de 60 000 ms est refusée. `h`/`l` réparés comme
  `parseCsv` (h = max, l = min) et comptés. Horodatage : `t` est l'**ouverture** de la barre ;
  `stamp: 'cloture'` à l'import → `t − 60 s`.
- **Empreinte** d'un jeu : `instrument|première clé|dernière clé|barres|somme des C entiers mod
  2³²` — c'est elle, jamais `id`, qui identifie des données identiques (essais, cache).
- Écritures de la page : séquentielles, trois reprises à délai aléatoire sur `unavailable` /
  `store_unavailable` / `resource_exhausted`, arrêt avec message sur `quota_exceeded`.
  `deleteDataset` pose `deleting: true` avant tout ; un jeu `deleting` ou sans `complete` n'est
  jamais lu. `loadDataset` vérifie que les séances lues = `meta.sessions` ; sinon « jeu incomplet
  (k/n) », jamais de calcul.

### 2.2 Niveaux nommés (GEX ou autres)

`T.ucoll('levels/items')`, **un document par mois** (`id 'AAAA-MM'`) : `{ id, days: { clé: {
levels: { HVL: …, CR: … }, scale: 'contrat'|'NDX', base?: NQ − NDX ce jour-là, source } }, u }`.
Le moteur lit `niveau + (scale === 'NDX' ? base : 0) + adj(séance)`. Un opérande `level` sur un
jeu `roll: 'inconnu'`, ou `'ajuste'` sans `adj`, ou un niveau `NDX` sans `base`, est une erreur de
validation, jamais un `NaN` silencieux. Jeu `non-ajuste` : la séance de bascule porte `roll: true`
et les séries continues et `prev` y repartent de zéro ; le rapport de qualité la liste.

### 2.3 Boîte de réception

`T.ucoll('inbox/items')` : `{ id, at, kind: 'trades'|'barres'|'strategie'|'niveaux'|'macro'|
'note'|'migration', title, count, detail, go: { desk, tab, sel }, seen: false, u }`. Défauts de
`go` : trades → journal/registre ; barres → donnees/series (sel = id du jeu) ; strategie →
labo/concevoir (sel = id de version) ; niveaux → donnees/niveaux ; migration → donnees/boite.

### 2.4 Stratégies

`T.ucoll('labo/strategies')`, **un document par version** : `id = sid + '_v' + version`,
`sid` = `/^s[a-z0-9]{6,20}$/` (sans `_`). `root` = `sid` d'origine (une duplication garde le
`root`). Une version `scellee` ne se modifie plus : modifier crée `version + 1` en `brouillon`.
**Seule la page scelle.** Au chargement, une version `scellee` dont `hash` ≠ hachage recalculé est
affichée « altérée » et ne peut ni ouvrir le hors échantillon ni prétendre à un verdict.

### 2.5 Essais (multiplicité) — registre en ajout seul

`T.ucoll('labo/essais')` : un document par lancement sur **données réelles** qui introduit au
moins un `configHash` jamais vu ; **jamais modifié**. `id = 'e' + base36(ms) + aléa`,
`{ id, sid, root, version, instrument, fingerprint, from, to (clés des séances d'entrée), op,
hashes: [configHash nouveaux] (≤ 500, sinon plusieurs documents), sr: [Sharpe par trade de chaque
configuration, même ordre], at, u }`. **N** d'un test = nombre de `configHash` distincts parmi les
essais de même instrument dont [from, to] recoupe la période évaluée — toutes stratégies,
versions et jeux confondus, sans plafond. `sdTrials` = écart-type des `sr` de ces essais s'il y en
a au moins dix, sinon `1/√n`. `run`, `sweep` et `wfa` créent des essais ; `envelope`, `stress`,
`random`, `permute`, `synth`, `boot` n'en créent pas. Surcompter ne coûte que `√(2 ln N)` au
seuil (ALP nº 3, seizième partie) ; sous-compter rend le DSR faux. Un fichier local sans compte
compte en mémoire pour la visite et l'écran le dit.

### 2.6 Hors échantillon

- `T.ucoll('labo/config')` : document `'oos-' + instrument` = `{ oosFrom: clé, at, u }`, **posé
  une fois**, au plus tard au premier lancement réel sur l'instrument (proposition : la clé qui
  laisse 30 % des séances disponibles après elle ; l'utilisateur peut la choisir avant ce premier
  lancement, jamais après). Toutes les séances ≥ `oosFrom` sont hors échantillon, celles
  ajoutées plus tard aussi.
- Toute opération autre que l'ouverture hors échantillon reçoit obligatoirement `sel.to <
  oosFrom` ; le moteur refuse une opération sans `sel` quand `oosFrom` existe. La calibration de σ
  (4.4) aussi.
- `T.ucoll('labo/oos')` : un document par ouverture, jamais modifié, `{ id, hash (version
  scellée), sid, root, version, instrument, from, to, at, u }`. Une ouverture est « première » si
  aucun document de même `root` et même instrument ne recoupe la période. Sinon le Labo écrit
  « hors échantillon déjà vu par la version v… le … », et le critère du verdict tombe. L'écran
  publie aussi le nombre total d'ouvertures de la période, toutes lignées.

### 2.7 Journal

Les trades de suivi portent `strat: sid`, `stratV: version`. Claude écrit les trades importés dans
`data/users/me/journal/trades/<id>` avec le schéma du journal plus `{ id, u, src: 'import', imp }`
(`id` stable dérivé du contenu). Un trade sans stop connu n'a pas de `r`.

### 2.8 Résultats lisibles par Claude

`T.ucoll('labo/results', { mirror: false, live: false })` : un document par (version × empreinte ×
op), `id = idVersion + '__' + empreinteCourte + '__' + op`, ≤ 200 Ko :
`{ id, sid, version, hash, configHash, fingerprint, ds, sel, op, at, costs, stats (4.1), nulls:
{ random, permute, synth }, sweep?, wfa?, boot?, verdict?, oos?, trades: [[t, side, r, pnl, fin]]
(≤ 3 000 lignes, sinon `tradesOmitted: n`), u }`. Écrit à la fin de chaque calcul ; sert de cache à
la visite suivante (clé `configHash + fingerprint + sel + op`). Claude le lit par `ArtifactData get`
pour commenter et proposer la version suivante sans rien relancer.

### 2.9 Règles d'écriture de Claude

1. Tout document porte `id` et `u` = ms de l'écriture, **supérieur** au `u` lu (sinon `T.ucoll`
   ignore la mise à jour pour toujours).
2. Aucune suppression dure dans une collection en miroir (tout sauf `labo/results`) : écrire
   `{ deleted: true, u }`.
3. Avant un import, lister les identifiants existants (`list`, `out_dir`) et les passer à l'outil
   (`--existing DOSSIER`) : les trades déjà présents ne sont jamais réécrits (l'utilisateur a pu
   les annoter) ; tout document existant est épinglé par `if_version`.
4. Ordre : assets, puis méta (`complete: true`), puis élément de boîte — toujours en dernier.
5. Jamais de modification d'une version de stratégie : écrire `version + 1`. Avant d'écrire une
   stratégie, `node tools/labo-check.js strategie.json` (normalisation, erreurs, lecture en
   français), et montrer la lecture à l'utilisateur.

## 3. Grammaire d'une stratégie (JSON)

### 3.0 Document minimal et valeurs par défaut

Minimal : `{ id: sid + '_v1', sid, root: sid, version: 1, status: 'brouillon', hash: null,
sealedAt: null, createdAt, u, name, hypothesis, side, long: { trigger, entry, stop, target } }`.
`normalize` complète avec des **constantes du code**, jamais lues dans `T.settings` :
`instrument 'MNQ'`, `anchor 'globex'`, `session { tz: 'Europe/Paris', from: '00:00', to: '09:00',
flat: '09:00', days: [1,2,3,4,5], warmup: 15 }`, `mirror true`, `short null`, `setup []`,
`entry { type: 'market' }`, `manage { breakeven: null, trail: null, maxBars: null, exitOnOpposite:
false }`, `risk { mode: 'contracts', contracts: 1, riskUsd: 150, maxQty: null, minStopTicks: 4,
maxPerSession: 3, maxLossesPerSession: 2, dailyStopUsd: 400, cooldown: 0 }`, `costs {
commissionRT: null, slipTicks: 1 }` (`null` = réglage de l'utilisateur, **figé dans le hachage au
scellement**), `fill 'pessimiste'`, `params {}`. La page réécrit le document normalisé au premier
enregistrement.

```js
{ …, instrument, anchor, session, side: 'long'|'short'|'both', mirror,
  long:  { setup: [Cond…], trigger: Cond, entry, stop, target },
  short: null,                           // obligatoire si side ≠ 'long' et mirror = false
  manage, risk, costs, fill: 'pessimiste'|'optimiste'|'chemin',
  params: { nom: { v, min, max, step, label } } }
```

Toute valeur numérique d'une règle peut s'écrire `"$nom"` (= `params.nom.v`, ou la valeur imposée
par un balayage). `$nom` sans paramètre → erreur.

### 3.1 Séances, ancrage, heures

La séance est **toujours la séance Globex** (clé 2.1). `anchor` ne fixe que l'instant où se
remettent à zéro les grandeurs **ancrées** (`vwap` et σ, `sess`, `or`, `at`, `sessmin`) à
l'intérieur de la séance Globex :
- `globex` → première barre de la séance (18:00 New York) ;
- `paris` → première barre ≥ 00:00 Paris de la date de clé (pendant les semaines où les
  changements d'heure américain et européen sont décalés, Globex rouvre à 23:00 Paris : les barres
  antérieures à l'ancre ont des grandeurs ancrées `NaN` et ne portent pas de signal) ;
- `rth` → première barre ≥ 09:30 New York ; grandeurs ancrées `NaN` hors 09:30–16:00 ; une
  stratégie `rth` dont la fenêtre sort de 09:30–16:00 est refusée.

Toutes les heures d'une stratégie (`from`, `to`, `flat`, `or`, `at`, `time`, `valid` en heure) se
convertissent, **séance par séance**, en minutes écoulées depuis l'ancre (`sessmin`) en tenant
compte du fuseau donné (`session.tz` par défaut) ; toutes les comparaisons se font en `sessmin`,
jamais en heure murale. Une fenêtre ou un `flat` qui chevauche l'ancre est refusé à la validation.
`days` et `dow` se lisent sur la **date de la clé** (lundi = 1). Les fenêtres glissantes (lag,
moyennes, ATR, RSI, `hh`/`ll`, `for`, `within`, `tf`) sont continues d'une séance à l'autre (sauf
séance `roll: true` d'un jeu non ajusté) ; `cross`, `touch`, `reject`, `break` sont fausses sur la
première barre de chaque fenêtre ancrée. `prev` lit la séance précédente **au sens de l'ancrage**
(RTH précédente pour `rth`) en sautant toute séance de moins de 80 % des barres attendues (1 380
globex, 390 rth), chaque saut compté dans `warnings`. Les niveaux se lisent par la clé Globex.

### 3.2 Opérandes et leurs classes

Chaque opérande a une **classe** : `niveau` (un prix), `écart` (une différence de prix, en
points), `oscillateur` (borné 0–100), `neutre` (pas un prix). Tout opérande non fini (`NaN`,
`±Infinity`) est **indéfini** et rend fausse toute condition qui le lit ; un σ de VWAP inférieur à
1 tick est indéfini (donc `vwap` avec k ≠ 0 et `dist` en `sd`) ; `hh`, `ll`, `sess`, `or` sur un
ensemble vide valent `NaN`.

| Forme | Classe | Valeur à la clôture de la barre i |
|---|---|---|
| nombre, `"$p"` | constante | |
| `{f:'close'\|'open'\|'high'\|'low'\|'hl2'\|'hlc3', lag?}` | niveau | champ de la barre `i − lag` |
| `{f:'volume', lag?}`, `{f:'range', lag?}` | neutre | volume ; `h − l` |
| `{f:'body', lag?}` | écart | `c − o` |
| `{f:'vwap', k?}` | niveau | VWAP ancrée + k·σ (σ = écart-type pondéré du prix typique) |
| `{f:'sma'\|'ema'\|'hh'\|'ll', n, of?}` | classe de `of` (défaut `close`) | moyenne ; plus haut/bas de `of` sur i−n … i−1 (barre courante exclue ; défaut `of` = `high` pour `hh`, `low` pour `ll`) |
| `{f:'sd', n, of?}` | neutre | écart-type de `of` sur n barres (Bollinger : `sma ± k·sd` par `op`) |
| `{f:'atr'\|'rsi', n, lag?}` | neutre / oscillateur | Wilder ; RSI = 50 quand gains et pertes moyens sont nuls |
| `{f:'rvol', n}` | neutre | volume ÷ moyenne du volume à la même `sessmin` des n séances précédentes |
| `{f:'prev', of:'open'\|'high'\|'low'\|'close', n?: 1}` | niveau | séance ancrée n fois précédente (3.1) |
| `{f:'sess', of:'high'\|'low'\|'open'}` | niveau | haut/bas de la séance ancrée jusqu'à i−1 ; ouverture = 1re barre ancrée |
| `{f:'or', from, to, tz?, of:'high'\|'low'\|'mid'\|'open'\|'close'}` | niveau | barres de la séance dont l'horodatage ∈ [from, to) ; `NaN` tant que `sessmin(i) < sessmin(to)`, `NaN` toute la séance si l'intervalle est vide ou commence avant l'ancre ; range incomplet → `warnings` |
| `{f:'at', time, tz?, of:'open'\|'close'}` | niveau | prix de la barre de `time` ; `NaN` avant |
| `{f:'tf', m: 5\|15\|30\|60, of}` | classe de `of` | valeur de `of` calculée sur barres de m minutes (alignées sur l'ancre), lue sur la **dernière barre de m minutes close** |
| `{f:'level', name}` | niveau | niveau nommé de la séance (2.2) |
| `{f:'nearest', side:'above'\|'below', names?}` | niveau | niveau nommé le plus proche au-dessus / au-dessous de `close[i]` |
| `{f:'time'}`, `{f:'dow'}`, `{f:'sessmin'}` | neutre | minutes depuis minuit (tz de `session`), jour de la clé (1–7), minutes depuis l'ancre |
| `{f:'dist', a, b, unit:'pts'\|'ticks'\|'atr'\|'sd', n?}` | écart | `(a − b)` en points, ticks, ATR(n = 14) ou σ de VWAP |
| `{op:'+'\|'-'\|'*'\|'/', a, b}` | typé | niveau ± écart = niveau ; niveau − niveau = écart ; écart × nombre = écart ; neutre ⊕ neutre = neutre ; niveau × nombre **refusé** |

VWAP et σ : prix typique `hlc3` pondéré par le volume (poids égaux pour une séance de volume
nul ou `vol: null`), cumulés depuis l'ancre — identique à `sessionVwap` pour `anchor: 'globex'`
(sauf la règle de poids, qui y est globale).

### 3.3 Conditions

| Forme | Vraie à la barre i si (achat ; la vente en 3.4) |
|---|---|
| `{cmp:'>'\|'<'\|'>='\|'<=', a, b}` | `a[i] cmp b[i]` |
| `{cross:'up'\|'down', a, b}` | up : `a[i−1] ≤ b[i−1]` et `a[i] > b[i]` ; down : `a[i−1] ≥ b[i−1]` et `a[i] < b[i]` |
| `{touch: L, from:'above'\|'below'}` | above : `low[i] ≤ L[i]` et `close[i−1] > L[i−1]` ; below : `high[i] ≥ L[i]` et `close[i−1] < L[i−1]` |
| `{reject: L, from}` | touche **et** clôture revenue : above → `close[i] > L[i]` ; below → `close[i] < L[i]` |
| `{break: L, dir:'up'\|'down'}` | up : `close[i] > L[i]` et `close[i−1] ≤ L[i−1]` ; down : `<` et `≥` |
| `{bar:'up'\|'down'}` | `close > open` / `close < open` |
| `{time:['HH:MM','HH:MM'], tz?}` | `sessmin` dans l'intervalle |
| `{news:{impact: 1–3, before: min, after: min}}` | **aucune** publication d'impact ≥ `impact` dans [t − before, t + after] (collection `calendar`, heure de Paris) |
| `{all:[…]}`, `{any:[…]}`, `{not: Cond}` | logique |
| `{for: n, cond}` / `{within: n, cond}` | vraie sur les n dernières barres / sur au moins une |

Un signal = `setup` (toutes vraies) **et** `trigger` vrais à la clôture de i.

### 3.4 Miroir

Le côté vendeur d'une stratégie `mirror: true` est la **réflexion des prix** `p → K − p`. Il se
calcule **après résolution des paramètres** (`mirror(resolve(long))`) : dans le document,
`short` reste `null`, et le moteur le calcule pour chaque configuration. Règles, par classe :
- niveau → reflété (`k → −k` pour `vwap` ; `high ↔ low` pour les champs, `hh ↔ ll`, `prev`,
  `sess`, `or`, `at` ; `nearest above ↔ below`) ; écart → `x → −x` ; oscillateur → `100 − x` ;
  neutre → inchangé ;
- niveau contre niveau : opérandes reflétés, comparaison inversée (`<` ↔ `>`, `<=` ↔ `>=`) ;
- niveau contre constante : **refusé** (`mirror` impossible) — une constante `$p` compte comme
  constante ;
- écart contre constante x : opérandes internes reflétés dans le même ordre, comparaison
  inversée, constante → −x (`dist(a,b) > x` → `dist(a′,b′) < −x` ; `body > x` → `body < −x`) ;
- écart contre écart : reflétés, comparaison inversée ; écart contre neutre ou niveau : refusé ;
- oscillateur contre constante x : comparaison inversée, x → 100 − x ; contre oscillateur :
  comparaison inversée ;
- neutre : inchangé ; `op` : niveau ± d → niveau′ ∓ d ;
- `cross up ↔ down`, `touch/reject above ↔ below`, `break up ↔ down`, `bar up ↔ down` ;
- entrée, stop, objectif : `at − offset·tick` → `at′ + offset·tick`, `swing` plus bas → plus haut,
  `buffer` vers l'extérieur ; gestion : suiveur depuis le plus bas, break-even par le plus bas.

En `chemin`, une barre `c = o` prend le **stop d'abord**, quel que soit le sens. Test : pour
chaque forme de 3.2 et 3.3, évaluer la règle reflétée sur la série réelle = évaluer la règle sur
la série réfléchie (niveaux nommés reflétés aussi), barre par barre, sur données aléatoires ; une
stratégie `both` sur une série et sur sa réflexion rend les mêmes trades de sens opposés.

### 3.5 Entrée, stop, objectif

Le signal est connu à la **clôture** de i ; rien ne s'exécute avant `i + 1`. Un signal n'est
exécutable que si i+1 est dans la même séance, `t[i+1] − t[i] = 60 000` ms, et
`sessmin(from) ≤ sessmin(i+1) < min(sessmin(to), sessmin(flat))` ; sinon il expire (`expire`, ou
`trou` pour un trou de données). Un ordre en attente vérifie la même condition à chaque barre.

- `Entry` : `{type:'market'}` → `open[i+1]`, glissement défavorable.
  `{type:'limit', at, offset: ticks, valid: barres | 'HH:MM', through: true}` → prix
  `at[i] − offset·tick` (achat), actif de i+1 à i+valid ; un achat limite dont le prix est ≥
  `open` de sa première barre active est **marketable** : exécuté comme au marché (glissement
  compris), compté `marketable`. Sinon rempli si `low[j] < prix` (`through`) ou `≤`, au prix ;
  pas de glissement. `{type:'stop', at, offset, valid}` → rempli si `high[j] ≥ prix`, à
  `max(open[j], prix)` + glissement.
- `Stop` (fixé à l'exécution) : `{type:'pts', value}` · `{type:'atr', value, n: 14}` (ATR à la
  barre du signal) · `{type:'swing', n}` (plus bas des n dernières barres, signal compris) ·
  `{type:'level', at}` ; `buffer: ticks` vers l'extérieur. Distance < `risk.minStopTicks` →
  annulé (`stopcourt`). Exécution déjà au-delà du stop → annulé (`ecart`).
- `Target` : `{type:'r', value}` · `{type:'pts', value}` · `{type:'atr', value, n}` ·
  `{type:'level', at, dynamic: false}` (dynamique : réévalué à chaque barre sur la valeur de la
  barre précédente) · `{type:'none'}`. Rempli si `high > objectif` quand `entry.through` (même
  règle de file que l'entrée), sinon `≥`. Objectif déjà dépassé à l'exécution → annulé.

### 3.6 Gestion barre par barre (position ouverte, barre j)

1. `sessmin(j) ≥ sessmin(flat)` → sortie à `open[j]` (glissement) — `flat`.
2. Écart d'ouverture : `open[j]` au-delà du stop → sortie à `open[j]` (glissement) ; au-delà de
   l'objectif → sortie à `open[j]` (sans glissement).
3. Dans la barre (achat ; vente en miroir) : stop si `low ≤ stop`, objectif si `high ≥ objectif`
   (ou `>`, 3.5). Les deux : `pessimiste` → stop ; `optimiste` → objectif ; `chemin` → barre
   haussière (c > o) lue O→L→H→C (stop d'abord), baissière O→H→L→C (objectif d'abord), doji →
   stop. `vrai` (séries synthétiques portant `lowFirst`, 4.4) → selon l'ordre vrai. Stop exécuté
   au stop moins le glissement ; objectif au prix.
4. **Barre d'entrée.** Rempli à `open[j]` (marché, marketable, ou limite/stop déjà dépassé à
   l'ouverture) → règle 3. Sinon seule la partie postérieure au remplissage compte :
   - achat limite rempli à `p < open[j]` : `chemin` haussière → stop si `low ≤ stop`, sinon
     objectif si `high ≥ obj` ; `chemin` baissière → stop si `low ≤ stop`, sinon objectif si
     `close ≥ obj` ; `pessimiste` → stop si `low ≤ stop`, sinon objectif seulement si
     `close ≥ obj` ; `optimiste` → objectif si `high ≥ obj`, sinon stop si `low ≤ stop` ;
   - achat stop rempli à `p > open[j]` : `chemin` haussière → objectif si `high ≥ obj`, sinon stop
     si `close ≤ stop` ; `chemin` baissière → objectif si `high ≥ obj`, sinon stop si
     `low ≤ stop` ; `pessimiste` → stop si `low ≤ stop`, sinon objectif si `high ≥ obj` ;
     `optimiste` → objectif si `high ≥ obj`, sinon stop seulement si `close ≤ stop` ;
   - vente : miroir exact. Ces règles ont été mesurées sur des marches à ordre intrabarre connu
     (relecture de la version 1) : l'ancienne règle faisait sortir la « borne » pessimiste
     au-dessus de la vérité (+0,11 R contre −0,06 R).
5. Sinon : `maxBars` atteint → sortie à `close[j]` (glissement) — `temps` ; signal opposé à la
   clôture (`exitOnOpposite`) → sortie à l'ouverture suivante — `oppose` ; dernière barre de la
   séance ou des données → `close[j]` (glissement) — `cloche`.
6. Mise à jour pour la barre suivante, jamais la courante : break-even atteint par le plus haut
   de j → stop à l'entrée ; suiveur après `start`·R : `stop = max(stop, plus haut depuis l'entrée
   − distance)`.

Raisons : `stop`, `be`, `trail`, `objectif`, `temps`, `flat`, `cloche`, `oppose`.

### 3.7 Taille, coûts, limites

- `contracts` : quantité fixe. `risk` : `qty = floor(riskUsd / (|prix de référence − stop|·pv +
  commission))` calculée **au départ de l'ordre** (prix de référence = `close[i]` pour un ordre au
  marché, prix de l'ordre sinon ; stop de la barre du signal), bornée par `risk.maxQty` et par
  `maxContracts` du compte (`T.lib.risk.normAccount`) ; `qty < 1` → annulé (`taille`).
- Glissement = **ticks par jambe exécutée au marché ou au stop** : entrée `market`/`stop`/
  `marketable` ; sorties `stop`, `be`, `trail`, `temps`, `flat`, `cloche`, `oppose`. Jamais la
  limite ni l'objectif. (Le desk Quant libelle son glissement « aller-retour, sur chaque trade » :
  `describe` publie aussi le coût réalisé moyen en ticks aller-retour, pour comparer.)
- `pnl = qty·(sens·(sortie − entrée)·pv − commissionRT)` ; `r = pnl / (qty·L·pv)`, `L` =
  |entrée − stop initial| ; `c = commissionRT + tick·pv·slipTicks × (jambes glissées)`.
- Une position à la fois. `cooldown: c` : aucun signal sur la barre de sortie ni sur les c − 1
  suivantes (c = 0 : la barre de sortie peut porter un signal). Par séance : `maxPerSession`
  entrées, `maxLossesPerSession` pertes, `dailyStopUsd` de perte nette → plus d'entrée. Signal
  acheteur et vendeur sur la même barre → aucun trade (`ambigu`).

### 3.8 Registre unique de la grammaire

`T.lib.laboStats.GRAMMAR = { operands: [{ f, label, cls, args: [{ k, type: 'int'|'num'|'time'|
'enum'|'operand'|'names', options, def, min, max, label }] }], conditions: [{ key, label, args }],
entries, stops, targets }` alimente l'éditeur, `normalize`, `describe`, le miroir et la
documentation de Claude. Un ajout de forme se fait là, et ses tests de miroir et de lecture avec.

## 4. Moteur — `labo-engine.js`

`function laboEngine(a)` est **autonome** : aucune variable extérieure, aucun `T`, aucun appel à
`quantEngine`, aucune `new Function`. Test : `vm.runInNewContext('(' + laboEngine + ')', {Intl,
Math, Date, …})` exécute `run` sur une petite série. Les fuseaux se calculent avec `Intl` comme
`quantEngine.off` (cache par heure).

**Exécuteur** : `T.lib.laboEngine.worker()` → `{ load(fingerprint, cols) → Promise, call(op, a,
onProgress) → { promise, cancel }, close() }`. Le worker est créé une fois depuis la source de
`laboEngine` (Blob, comme `T.compute`), reçoit les colonnes `Float64Array` **transférées une seule
fois par jeu** (plus `lowFirst` si présent), et poste `{ progress: k/n }` au plus toutes les
250 ms. Un nouveau calcul d'un même onglet annule le précédent ; le desk ferme le worker dans son
`cleanup`. `permute`, `random`, `sweep`, `wfa`, `boot` ne s'exécutent jamais dans le fil
principal : sans worker, « calcul impossible sur cet appareil ». Des enveloppes synchrones
(`T.lib.laboEngine.run(a)`, `.op(name, a)`) servent aux tests et aux petits calculs.

Entrée commune : `a = { op, bars: {t,o,h,l,c,v, lowFirst?} (ou chargées), levels: {clé:
{nom: prix}}, adj?: {clé: pts}, news?: [{t, impact}], spec (normalisée), values (paramètres),
settings: { commissionRT, pointValue, tick, maxContracts }, sel: { from, to }, seed, draws, … }`.
Déterministe à graine égale (mulberry32 recopié). On n'envoie que les séances de `sel` plus 20
séances d'amorçage.

| `op` | Sortie |
|---|---|
| `resolve`, `mirror`, `key`, `stats` | les fonctions uniques (1) |
| `run` | `{ trades, counts: {signals, ambigu, taille, stopcourt, ecart, annule, expire, trou, marketable}, sessions: [{key, pnl, n, lo, hi}] (**toutes** les séances éligibles, sans trade comprises ; lo/hi = creux et sommet de l'équité de la séance, MAE/MFE comprises, en $), stats, fill, costs, warnings }` ; trade = `{ i, j, t, tx, key, side, qty, entry, stop0, target0, exit, fin, pts, pnl, r, risk, c, mae, mfe, bars, hour, dow }` |
| `envelope` | même configuration en `pessimiste` et `optimiste` : `{ pess, opt }` (stats + équité) |
| `random` | 4.2 : `{ means, obs, p, lo, hi, label }` |
| `permute` | 4.3 : `{ means, obs, p, draws, pmin, block, label }` |
| `synth` | 4.4 |
| `lattice` | marche sur le réseau des ticks (4.4) → colonnes + `lowFirst` |
| `sweep` | grille de 1 ou 2 paramètres : `{ p1, p2, xs, ys, cells[ny][nx]: {n, meanR, sdR, net, pf, sharpe, maxDD, winRate}, mat[config][séance]: {n, sumR, sumR2, net}, best }` |
| `wfa` | 4.5, calculée sur la matrice `mat` d'un balayage (jamais de relance par fenêtre) |
| `stress` | 4.7 |
| `boot` | 4.6 |
| `features` | séries d'une liste d'opérandes, `sel` ≤ 5 séances (aperçu d'une règle) |

**Performance.** Les signaux bruts (setup ∧ trigger, par barre et par côté) sont calculés une fois
par configuration ; `envelope`, `stress`, `random` ne rejouent que l'exécution. Séries mises en
cache par clé d'opérande pendant l'appel. Budgets (une année, téléphone de milieu de gamme) :
`run` ≤ 1,5 s, `envelope` ≤ 2 s, `random` (200) ≤ 3 s, `sweep` (≤ 100 cellules) ≤ 60 s ;
`permute` ajuste ses tirages pour tenir 60 s (au moins 50) et l'écran publie le p minimal
atteignable `1/(draws+1)`. Un test chronométré tourne sur 350 000 barres (bornes du test ×3 pour
la machine de test).

### 4.1 Statistiques d'un run (`stats`)

`{ n, nz (trades à r ≠ 0), wins, losses, winRate (part des r > 0 parmi r ≠ 0), meanR, sdR,
skew, exkurt (aplatissement en excès), sharpeTrade = meanR/sdR, net, avgWin, avgLoss, pf, maxDD
($), expectancy ($/trade), equilibrium, costR, rW, byFin }`.
- `equilibrium = L̄ / (W̄ + L̄)`, `W̄` = moyenne des `r > 0`, `L̄` = moyenne des `|r|` des `r < 0`
  (nets ; les coûts n'y entrent pas une seconde fois). Tests : `signe(winRate − equilibrium) =
  signe(meanR)` sur tout jeu de trades ; égalité avec `(1 + c/L)/(1 + R:R)` sur une géométrie fixe.
- `costR = moyenne(c_i / (L_i·pv))` : prédiction sans avantage de `meanR` (−costR) — moyenne de
  rapports contre moyenne de rapports (un rapport de moyennes serait faux de 17 % pour un risque
  uniforme entre 4 et 20 points).
- `rW = Σ pnl / Σ qty·L·pv`, prédiction sans avantage `−Σ qty·c / Σ qty·L·pv`.

### 4.2 Entrées au hasard (ne change que l'instant)

`draws` (200). Pour chaque séance, autant de **signaux** que la stratégie en a émis, tirés
uniformément parmi les barres où un signal aurait été exécutable (3.5) ; chaque signal tiré suit
**exactement** le chemin d'exécution de la stratégie : même type d'ordre (`at` évalué à la barre
tirée), même `offset`, `valid`, `through`, mêmes stop, objectif, gestion, taille, coûts,
limites ; sens = celui de la stratégie (`both` : tiré avec la proportion observée d'achats). Un
stop ou objectif `level` impossible à la barre tirée → distance médiane observée. Statistique :
`meanR` des trades remplis ; `p = (1 + #{tirée ≥ observée}) / (draws + 1)`. Étiquette :
« configuration isolée, non corrigée des N = … essais ».

### 4.3 Permutation

`draws` (100, ajusté au budget). Dans chaque séance, on permute les barres **à l'intérieur de chaque
tranche de 30 minutes d'horloge** (`block: 30` ; `'seance'` = toute la séance sauf la 1re barre).
Chaque barre garde son écart d'ouverture `o − c_prec`, sa forme (`h−o`, `l−o`, `c−o`) et son
volume ; prix reconstruits, heures inchangées. On garde le profil de volatilité de la journée et le
mouvement net de chaque tranche ; on détruit l'ordre des minutes dans une tranche. Hypothèse nulle
affichée : « dans chaque tranche, l'ordre des minutes ne porte aucune information ». Toutes les
séries recalculées, stratégie rejouée ; `p` sur `meanR`. Si la version vient d'un balayage,
`permuteGrid` rejoue la grille déclarée sur chaque permutation et compare le meilleur observé au
meilleur permuté (tirages réduits au budget) ; sinon l'étiquette dit « configuration isolée ».

### 4.4 Marche sans dérive exacte

`lattice` : ±1 tick par pas, `k = round((σ/tick)²)` pas par minute, graine explicite ; chaque barre
porte `lowFirst` (le plus bas atteint avant le plus haut). `fill: 'vrai'` utilise cet ordre. Le
stop d'une marche au tick n'est jamais dépassé : c'est une loi nulle **exacte** (`Q.synth`, à
12 sous-pas gaussiens, dépasse le stop de 0,67 point et rend +0,023 R au lieu de 0 à stop 10 /
objectif 20). `synth` : σ = médiane, sur les séances de `sel`, de l'écart-type des variations de
clôture d'une minute **des barres de la fenêtre** ; séances = min(120, séances de `sel`). Sortie :
`{ sigma, theory: −costR, vrai: meanR en ordre vrai, declare: meanR sous le remplissage déclaré,
biais: declare − vrai }`. C'est `declare`, pas `−c/L`, qui sert de plancher au résultat réel.
Stratégie qui lit `level`, `nearest` ou `news` → « non applicable ».

### 4.5 Analyse en avant

`{ is: séances, oos: séances, mode: 'rolling'|'anchored', objective: 'meanR'|'net'|'sharpe'|'pf',
minTrades }` sur `mat` : sur chaque fenêtre IS, la meilleure configuration (égalité → la première ;
moins de `minTrades` → exclue) est appliquée telle quelle à la fenêtre OOS suivante. Sortie :
`{ windows: [{isFrom, isTo, oosFrom, oosTo, best, isMeanR, oosMeanR, oosN}], stitched: stats,
wfe }`, `wfe = meanR` des fenêtres OOS cousues / `meanR` des meilleurs IS (moyenne pondérée par les
trades), quel que soit l'objectif ; `null` si ce dénominateur est ≤ `costR`.

### 4.6 Bootstrap et passage d'un compte prop

Bootstrap stationnaire (Politis–Romano, bloc moyen 5 séances) des **enregistrements de séance**
`{pnl, n, lo, hi}` (séances sans trade comprises) : intervalle à 90 % de `meanR` et du net annuel,
éventail d'équité (quantiles 5, 25, 50, 75, 95 sur 60 séances). Passage : compte lu par
`T.lib.risk.normAccount` sous **ses** noms (`size, target, maxLoss, dd, lockAt, dailyLimit,
dailyMode, consistency`), plus `minDays`, `maxDays` saisis dans le Labo ; plancher `intraday` suit
`hi` ; échec si `lo` passe sous le plancher ou la limite du jour (règles de `T.lib.risk.simulate`
appliquées aux séances) → probabilités de réussite, d'échec, de non-conclusion, jours médians.

### 4.7 Stress des coûts

Glissement 0–4 ticks par jambe × commission ×1, ×1,5, ×2 × dépassement exigé des ordres limites
(entrée et objectif) de 0, 1, 2 ticks → `meanR`, `net`. Glissement d'équilibre interpolé ; s'il n'y
a aucune jambe glissée, il vaut `'na'` et le critère se lit sur le dépassement (`meanR > 0` à 1 tick
exigé).

## 5. Statistiques et verdict — `labo-stats.js`

`T.lib.laboStats` (fil principal, fonctions pures) :

- `GRAMMAR` (3.8) ; `normalize(raw) → { spec, errors, warnings }` (3.0, validations de 3.1–3.5 et
  2.2) ; `resolve`, `mirror`, `stats` (enveloppes de l'engine).
- `hash(spec)` : FNV-1a 64 bits exact (`BigInt`, base `0xcbf29ce484222325`, premier
  `0x100000001b3`, modulo 2⁶⁴) sur les octets **UTF-8** du JSON canonique → `'h' + 16 hex`.
  JSON canonique : spec normalisée **puis résolue** (aucun `$nom`), sans `params` ; clés triées par
  unité de code ; `null` conservé, `undefined` omis ; nombres par `String(x)` (−0 → `0`) ; sans
  espace. Le hachage scellé couvre règles, `session`, `anchor`, `side`, `mirror`, `manage`, `risk`,
  `costs` (avec `commissionRT` remplacé par sa valeur au scellement) et `fill`. `configHash`
  (essais) couvre la même chose **sauf** `costs`, `fill`, `risk.contracts`, `risk.riskUsd`,
  `risk.maxQty`.
- `describe(spec) → [{ title, text }]` : une phrase par bloc (séance et ancrage, sens et miroir,
  contexte, déclencheur, entrée, stop, objectif, gestion, risque, coûts et convention de
  glissement, remplissage), **côté vendeur reflété compris**. Jamais `undefined`, `NaN`, phrase
  vide ; apostrophes typographiques ; heures avec espaces insécables.
- `dsr({ sr, n, N, skew, exkurt, sdTrials })` (via `T.lib.quant.dsr`), `trials(essais, instrument,
  from, to) → { N, sdTrials, inherited }`, `pbo(mat)` via `T.lib.quant.cscv`, `plateau(cells,
  best)` (sur `meanR` ; `false` si le meilleur ≤ 0 ; sinon moyenne des 8 voisins — 2 en une
  dimension — divisée par le meilleur), `stability(cells)`.
- `sprt(xs, { mu0, mu1, sigma, alpha: 0.05, beta: 0.20 })` : H0 `mu0 = −costR` (aucun avantage),
  H1 `mu1` = borne basse à 90 % du bootstrap en échantillon (jamais la moyenne brute) ; `mu1 ≤ mu0`
  → `'na'`. Bornes de Wald `ln((1−β)/α)` et `ln(β/(1−α))`. Décisions `avantage-confirme`,
  `aucun-avantage`, `continuer`. Géométrie fixe (objectif `r`, sans break-even, suiveur ni
  `maxBars`) → test **binomial exact** : p0 = `equilibrium`, p1 = taux en échantillon, incréments
  `ln(p1/p0)` et `ln((1−p1)/(1−p0))`. N'entrent que les trades de suivi postérieurs à `sealedAt`,
  portant `stratV` = version scellée, dans l'ordre. `cusum(xs, target, k, h)`.
- `TEMPLATES` : gabarits (rejet de bande VWAP, cassure du range d'ouverture, retour à la moyenne
  RSI, rejet du haut/bas de la veille, poursuite au-dessus de l'EMA, rejet du niveau GEX le plus
  proche) — **points de départ, aucun ne prétend à un avantage** ; tous passent `normalize`.
- `verdict(r)` → `{ items: [{ id, label, value, pass: true|false|null|'na', why }], level:
  'rejetee'|'a-approfondir'|'prete-simulateur', text }`. `'na'` (pas de balayage, pas d'analyse en
  avant) n'empêche pas « prête » ; `null` (applicable, non calculé) l'empêche ; un `false` →
  « à approfondir » ou « rejetée » (rejetée si `meanR ≤ −costR` ou p des entrées au hasard ≥ 0,5).
  Le verdict se calcule à des coûts `max(déclarés, planchers)` : commission ≥ réglage de
  l'utilisateur, glissement ≥ 1 tick par jambe glissée (planchers dans `GATES`, justifiés) ; p, DSR
  et OOS y sont rejoués. `GATES` (constantes, une justification chacune) :
  1. échantillon : `n_IS ≥ T.lib.quant.route1(0.10, 0.05, 0.80)` (619 trades ; SR de référence
     **déclaré**, ALP nº 3, huitième partie, table 14 — jamais calculé depuis le Sharpe observé) ;
  2. entrées au hasard : p < 0,05 ; 3. permutation : p < 0,05 ;
  4. Sharpe déflaté ≥ 0,95 avec N et `sdTrials` du registre ;
  5. PBO ≤ 0,2 (`'na'` sans balayage) ; 6. plateau ≥ 0,7 (`'na'` sans balayage) ;
  7. coûts : `meanR > 0` aux planchers et encore à +1 tick par jambe (ou à 1 tick de dépassement
     exigé si aucune jambe ne glisse) ;
  8. WFE ≥ 0,5 (`'na'` sans analyse en avant) ;
  9. hors échantillon : version scellée non altérée, **première ouverture de la lignée**, entrées au
     hasard rejouées sur les seules séances hors échantillon avec p < 0,05. Avant l'ouverture, le
     Labo calcule les trades attendus (taux en échantillon × séances OOS) et le nombre requis pour
     séparer `meanR_IS` de `−costR` (5 % unilatéral, 80 %) ; s'il en manque, il l'écrit avant.

## 6. Desk « Labo de stratégie » — `labo.js` + `labo-builder.js`

`id: 'labo'`, `label: 'Labo de stratégie'`, `glyph: 'L'`, `group: 'Recherche'`, `order: 45`.
Onglets : `concevoir`, `tester`, `valider`, `verdict`, `suivre`. Titres avec un mot en italique
serif, phrases courtes, aucun défilement horizontal à 390 px.

En-tête commun : stratégie et version, jeu courant (synthétique / jeux du compte / fichier local
de la visite, via `T.lib.donnees`), état (brouillon, scellée, altérée ; hachage court), lignée et
N (« dont M hérités »), coupure hors échantillon de l'instrument. Tout calcul passe par l'exécuteur
(4) avec progression, annulation, et le cache `labo/results`.

- **Concevoir** (`T.lib.laboBuilder.render(root, ctx, api)`) : liste des stratégies (versions,
  état), « Nouvelle » (vierge ou gabarit), puis une **pile de cartes** dans l'ordre des blocs
  (séance et ancrage, sens et miroir, contexte, déclencheur, entrée, stop, objectif, gestion,
  risque et coûts, paramètres, hypothèse). Chaque carte montre la phrase de `describe` et
  « Modifier », qui ouvre un **panneau plein écran** : type choisi par puces, champs générés
  depuis `GRAMMAR`. `setup` est une liste (« et ») avec au plus un niveau `any`/`not` dans
  l'interface ; toute forme plus profonde s'affiche « bloc avancé — modifiable par Claude ou en
  JSON », en lecture seule. Réordonner par ↑ ↓, cibles ≥ 44 px. Chaque nombre d'une règle devient
  un paramètre nommé. Onglet « JSON » : zone de texte, coller, « Valider » → erreurs de
  `normalize`. **Aperçu** : la dernière séance de l'échantillon portant un signal, avec les séries
  de la règle (`features`) et les signaux marqués. Boutons : Enregistrer, Sceller (exige
  l'hypothèse et la coupure de l'instrument), Nouvelle version, Dupliquer, Supprimer,
  « Décrire à Claude » (copie l'id de version et le JSON, rappelle que Claude peut l'écrire). La
  saisie ne détruit jamais un champ en cours de frappe.
- **Tester** (échantillon) : indicateurs (n, réussite contre `equilibrium`, `meanR` et `rW` avec
  leurs prédictions sans avantage, net, PF, Sharpe par trade, perte maximale) ; équité avec
  l'**enveloppe** pessimiste/optimiste ; sous-l'eau ; histogramme des R ; nuage MAE/MFE ; carte
  heure × jour ; sankey des issues (signaux → exécutés / expirés / annulés → objectif / stop /
  temps / clôture…) ; **les trois lois nulles** (histogrammes, valeur observée, p, p minimal,
  étiquettes) ; liste des trades ; « Ouvrir dans Métriques » (écrit `quant:lastBacktest` au format
  de `quant.js`, 3 000 derniers trades, `truncated: n`).
- **Valider** : balayage de deux paramètres → carte de chaleur 2D et surface 3D
  (`T.lib.perf.charts`, `injectCss()` avant), plateau, stabilité ; PBO ; analyse en avant (barres
  IS/OOS, équité OOS cousue, WFE) ; stress des coûts ; bootstrap (éventail, intervalles) ; Sharpe
  déflaté avec N compté ; sous-périodes (mois).
- **Verdict** : critères calculés, niveau, passage d'un compte prop ; hors échantillon (scellée
  seulement) avec ouvertures de la lignée et de la période.
- **Suivre** : trades du journal portant `strat`, saisie rapide (sens, entrée, stop, objectif,
  sortie, quantité → P&L et R, écrits avec `strat`, `stratV`), SPRT (5), CUSUM, écart à
  l'enveloppe.

Surface de `T.lib.perf.charts` : la forme de `T.lib.perf.surface()` — `{ title, x: {name, dom,
fmt}, y, z: {name, fmt}, xs, ys, vals[ny][nx], zmin, zmax, mid, midLabel, line: [], lineLabel,
fn(x, y) (valeur de la cellule la plus proche), argmax: [i, j] }`.

## 7. Desk « Données & imports » — `donnees.js`

`id: 'donnees'`, `label: 'Données & imports'`, `glyph: '⇣'`, `group: 'Système'`, `order: 85`.
Onglets : `boite` (boîte de réception : liens `go`, marquer lu), `series` (jeux : liste, rapport de
qualité — séances, minutes manquantes, écarts, barres plates, sauts de roll, séances sans volume —,
aperçu, suppression ; **CSV local** lu par tranches de 4 Mo dans un worker, séparateur, colonnes et
ordre des dates fixés sur les 2 000 premières lignes, colonnes `Float64Array` transférées ; « Utiliser
pour cette visite » ou « Enregistrer dans mon compte » → assets par année ; au-delà de deux ans,
découpage par année), `niveaux` (par séance, échelle, base), `envoyer` (ce qu'il faut envoyer à
Claude : barres d'une minute en CSV avec la convention d'horodatage, export des trades de la
plateforme, captures, niveaux ; « l'export CSV de ta plateforme », aucun chemin de menu non
vérifié). L'écran publie les documents utilisés / 25 000 et la taille des assets.

`T.lib.donnees` : `sessionKey(t)` (enveloppe de l'engine), `encodeSession(cols, i0, i1, D)`,
`decodeSession(doc)`, `chooseD(cols)`, `splitSessions(cols)`, `fingerprint(meta, cols)`,
`quality(cols)`, `datasets()`, `loadDataset(id) → Promise<{ meta, bars, levels, adj }>` (attend
`T.onCloud` 10 s au plus ; cache mémoire par `u`), `saveDataset(meta, cols, onProgress)`,
`deleteDataset(id)`, `levelsMap(from, to)`, `inbox()`, `synthetic(o)` (op `lattice`, méta `source:
'synthetique'`, jamais compté dans les essais).

## 8. Outils — `tools/ingest.js`, `tools/labo-check.js`

Node, sans dépendance ; chargent `quant`, `labo-engine`, `labo-stats`, `donnees` par le harnais.

```
node tools/ingest.js bars FICHIER.csv --tz America/New_York --stamp ouverture|cloture --name "MNQ 1 min" --instrument MNQ --roll ajuste|non-ajuste|inconnu [--existing DOSSIER] --out DOSSIER
node tools/ingest.js trades FICHIER.csv --tz Europe/Paris --instrument MNQ [--existing DOSSIER] --out DOSSIER
node tools/ingest.js levels FICHIER.txt --date AAAA-MM-JJ --scale contrat|NDX [--base X] --out DOSSIER
node tools/labo-check.js strategie.json
```

`bars` lit avec `T.lib.quant.parseCsv`, découpe avec `T.lib.donnees.splitSessions`, code avec
`encodeSession` : un fichier d'asset JSON par année, le document méta, l'élément de boîte, et
`plan.json` = la liste ordonnée des appels à faire (assets d'abord, puis lots `ArtifactData` de
≤ 50 écritures et ≤ 900 Ko avec `if_version` pour les documents existants). `trades` reconnaît les
en-têtes courants par alias (symbole, sens, quantité, prix et heures d'entrée et de sortie, P&L,
commission), apparie des exécutions en allers-retours FIFO, produit des entrées de journal
(`kind: 'pris'`, `status: 'clos'`, `src: 'import'`, `id` stable dérivé du contenu) et omet celles
déjà présentes. `levels` lit un collage « NOM : prix » (mêmes règles de lecture que
`pine/alp0-gex.pine` : signe moins conservé, fenêtre de plausibilité) et écrit dans le document du
mois. `labo-check` normalise, liste erreurs et avertissements, imprime `describe` et le hachage.

## 9. Tests et vérification

Chaque fichier a ses tests (`node test/<nom>.test.js`, sortie non nulle si échec). Obligatoires :

- **Autonomie** : `laboEngine` exécuté dans un contexte vide (4).
- **Causalité** : modifier les barres après i ne change aucun signal ni aucune série ≤ i — dont
  `or` avec un range 15 heures après l'ancre, `tf`, `rvol`, `prev`, `at`.
- **Heures** : fenêtre 20:00–02:00 New York avec `flat` 03:00 ; pas de croisement VWAP à la première
  barre ancrée ; semaine de décalage d'heure en `paris` ; `rth` hors séance.
- **Exécution** : cas construits à la main pour chaque entrée (dont marketable), stop, objectif
  (`through`), politique de remplissage, barre d'entrée (table 3.6.4, les deux sens), écart
  d'ouverture, break-even, suiveur, `maxBars`, `flat`, `cloche`, limites de séance, `cooldown`,
  taille au risque bornée, annulations.
- **Encadrement** : sur la marche au tick (ordre vrai connu), pour chaque type d'ordre et chaque
  sens, `pessimiste ≤ vrai ≤ optimiste` en moyenne de la barre d'entrée et du trade.
- **Loi nulle d'ALP** (`fill: 'vrai'`, marche au tick, 60 séances) : `|meanR + costR| < 2` erreurs-types
  pour un stop `pts`, un stop `atr` et un stop `swing` (risque variable), avec et sans glissement.
- **Puissance et taille** : une dérive plantée dans la fenêtre donne p < 0,05 (hasard et
  permutation) ; sans dérive, p < 0,05 sur environ 5 % de 40 graines (tolérance large) ; une
  stratégie qui ne gagne que le glissement d'entrée (limite contre marché) n'a **pas** p < 0,05.
- **Miroir** : 3.4, chaque forme ; `both` sur série et réflexion.
- **Croisé avec Quant** : sur `T.lib.quant.synth` (où `open[i+1] = close[i]` exactement), le gabarit
  de rejet de bande réglé comme le mode `rejet` (setup `close > vwap`, déclencheur `high ≥ vwap+kσ`
  et `close < vwap+kσ` pour la vente, stop `level` vwap+kσ, `buffer` = stop/tick, objectif `level`
  vwap dynamique, `pessimiste`, `flat` = `to`, `globex`, `cooldown: 1`, glissement nul, même
  commission) rend les mêmes trades (`i`, sortie, `pnl`) que `T.lib.quant.backtest`.
- **Statistiques** : `equilibrium` (signe et forme fermée), `costR` contre `rW`, DSR/PBO contre
  `T.lib.quant`, SPRT (bornes, décisions, binomial exact), hachage stable (ordre des clés, −0,
  UTF-8), `configHash` insensible aux coûts.
- **Registres** : deux essais concurrents sur la même période comptent les deux ; une stratégie
  dupliquée et un jeu réimporté héritent de N et des ouvertures ; une seconde ouverture de la
  lignée fait tomber le critère.
- **Données** : d1 aller-retour bit pour bit (pas 0,25, 0,01, 0,0001, refus au-delà), barres non
  alignées refusées, volume `null`, h/l réparés ; `ingest.js` sur dix fichiers témoins (séparateurs,
  virgule décimale, jj/mm et mm/jj, époques, doublons, h < c) rend les mêmes colonnes que
  `parseCsv` ; trades FIFO ; second import sans doublon.
- **Lecture en français** de chaque gabarit et de chaque forme : sans `undefined`, `NaN`, phrase vide.
- **Performance** : test chronométré (4).

Puis : `python3 build.py --fonts --out <scratchpad>/desk/dist/integ.html` (construction **complète** ;
le serveur d'aperçu sert le scratchpad), `node test/e2e.js …` → `"bad": 0` à 390 et 1280 px, et
**regarder les captures**, y compris avec un jeu synthétique chargé et une stratégie de gabarit
lancée dans chaque onglet.
