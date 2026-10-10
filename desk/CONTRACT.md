# ALP Desk — contrat des desks

ALP Desk est un terminal mobile (une seule page HTML) pour un trader particulier qui
trade le **MNQ** (Micro E-mini Nasdaq-100) et prépare des comptes de prop firm. Il a
cramé deux comptes (150 k et 100 k) ; sa leçon : *tout noter, réguler, backtester,
pratiquer avant le réel*. Le terminal doit l'y aider, desk par desk.

Racine du projet : `/tmp/claude-0/-home-user-Alp-1/d10614f7-6262-5c23-be49-fb171f0a286c/scratchpad/desk`
(ci-dessous `$D`). Le socle est **déjà écrit** : `src/core.js`, `src/core.css`,
`src/shell.html`, `src/desks/home.js` (desk de référence, à lire en premier).

## Ce que tu écris, et rien d'autre

- `src/desks/<id>.js` — ton desk ;
- `test/<id>.test.js` — tes tests unitaires (`node test/<id>.test.js`, sortie non nulle si échec).

Ne modifie **jamais** `core.js`, `core.css`, `shell.html`, ni le fichier d'un autre desk.
S'il te manque quelque chose dans le socle, écris-le localement dans ton fichier et
signale-le dans ton rapport final (« besoin socle : … »).

## Forme d'un desk

Le fichier est exécuté dans une IIFE au montage. Il enregistre le desk :

```js
var h = T.h, U = T.ui, C = T.chart, F = T.fmt;
T.lib = T.lib || {};
T.lib.risk = { /* fonctions PURES testables : aucun DOM, aucun T.store */ };
T.desk({
  id: 'risk', label: 'Risque', glyph: 'R', group: 'Exécution', order: 40,
  tabs: [{ id: 'compte', label: 'Compte' }, { id: 'jour', label: 'Aujourd’hui' }],
  render: function (root, ctx) {
    // ctx.tab (onglet courant), ctx.setTab(id), ctx.settings, ctx.go(deskId), ctx.rerender()
    root.appendChild(U.page({ kicker: 'Risque', title: 'Le risque, *d’abord*.', lede: '…' }));
    root.appendChild(U.tabs({ tabs: this.tabs, value: ctx.tab, onChange: ctx.setTab }));
    // … contenu de l'onglet
    return function cleanup() { /* désabonnements, timers */ };
  }
});
```

Les onglets sont rendus par **toi** (`U.tabs`) juste sous l'en-tête de page.
`ctx.rerender()` redessine le desk en gardant le défilement : utilise-le après un
changement d'état, ou redessine seulement une partie si tu préfères (meilleur pour la
saisie au clavier : ne détruis jamais un champ en cours de frappe).

## API du socle (lis `src/core.js` pour le détail)

DOM : `T.h(tag, attrs, ...enfants)` — attrs : `class`, `style`, `text`, `html`
(seulement pour du texte que tu as écrit toi-même), `on:{click:fn}`, `aria-*`, `data-*`.
Les chaînes enfants sont échappées. `T.esc(s)`, `T.clear(el)`.

Format (français, espace fine, virgule, vrai signe moins) : `F.num(v, nd, unit, signed)`,
`F.int`, `F.usd(v, nd, signed)`, `F.pct(p, nd, signed)` (p entre 0 et 1), `F.pts`,
`F.r` (multiples de R, signés), `F.date`, `F.dateLong`, `F.time`, `F.dur(minutes)`,
`F.parse(texte)` (accepte la virgule, rend NaN sinon).

Composants `U.*` : `page({kicker,title,lede})` (dans `title`, `*mot*` passe en italique
serif), `section(title, meta)` (rends-la puis `appendChild`), `card({title,meta,body,accent,flush})`,
`kpis([{label,value,unit,hint,tone:'neg'|'acc',onClick}], cols)`, `pill(text,'on'|'acc'|'no')`,
`button({label,kind:'pri'|'acc'|'ghost',small,onClick,disabled})`, `note(text, warn)`,
`callout(enfants)`, `empty({title,text,action})`, `prose([html])`,
`field({id,label,value,unit,type:'number'|'text'|'select'|'textarea'|'time'|'date',options,min,max,placeholder,hint,full,onChange})`
(les nombres acceptent la virgule ; `onChange` reçoit un nombre),
`fields([...], cols)`, `seg({options:[{v,label}],value,onChange})`, `chips({options,value,multi,onChange})`,
`tabs({tabs,value,onChange})`, `checklist({items:[{id,t,s}],checked:{id:true},onToggle(id,on)})`,
`table({cols:[{k,label,align:'r',fmt(v,row),cls}],rows,empty,onRow,rowClass})`,
`flow({nodes:[{title,sub,state:'done'|'active'|'todo',ix,go,onClick}]})` (carte de nœuds reliés).

Graphiques `C.*` (SVG à la largeur réelle, info-bulle au toucher) :
`line({series:[{name,points:[[x,y]],tone:'fg'|'violet'|'mute',dash,area}],x:{type:'num'|'time'|'cat',labels,fmt},y:{fmt,zero,min,max},hlines:[{y,label,tone}],bands:[{y0,y1,label}],vlines,height})`,
`bar({cats,series:[{name,values,tone}],stacked,horizontal,fmt,height})`,
`hist({values,bins,refs:[{x,label,tone,dash}],split,fmt,min,max})`,
`fan({q:{p05,p25,p50,p75,p95},paths,hlines,fmt,xLabel(i),legend})`,
`sankey({nodes:[{id,label,col,tone}],links:[{s,t,v,tone}],fmt,height})`,
`ladder({levels:[{price,label,kind:'violet'|'mute',dash}],price,fmt})`,
`gauge({value,min,max,log,band:[a,b],ticks:[[v,'label']]})`,
`quadrant({xLabel,yLabel,quadrants:[hg,hd,bg,bd],points:[{x,y,label}]})` (x,y dans [−1,1]),
`spark(values,{tone})`, `heat({rows,cols,values,fmt,diverging,corner})`.
Tons : `fg` (blanc), `violet` (accent), `mute` (gris). **Aucune couleur écrite en dur** :
seulement les variables CSS du socle (`var(--violet)`, `var(--soft)`, `var(--line)`…) si
tu dois styler un élément à la main.

Calcul lourd (> 50 ms) : `T.compute(fn, arg).then(res => …)` — `fn` est exécutée dans un
Web Worker, elle doit être **autonome** (aucune variable extérieure, aucun `T`), recevoir
`arg` et rendre un objet sérialisable. Définis-la comme fonction nommée et réutilise la
même dans tes tests. Aléa : toujours graine explicite (`T.rng(seed)` dans le fil principal ;
recopie un mulberry32 dans la fonction du worker).

Statistiques : `T.stats.mean, sd, quantile(sorted,q), sorted, normCdf, normPpf, erf,
maxDrawdown(equity), cumsum`. Temps : `T.time.parts(tz)`, `T.time.hhmm(tz)`,
`T.time.globex()` → `{open, cash, ny}`, `T.time.inWindow(from,to,tz)`.

Sauvegarde :
- `T.store.get(clé, défaut)` / `T.store.set(clé, valeur)` / `T.store.on(clé, fn)` —
  états par utilisateur (copie locale + base privée). **Préfixe tes clés par ton id** :
  `risk:account`, `risk:rules`… Clés : lettres, chiffres, `-_.:`.
- `T.settings.get()` → `{instrument, pointValue, tick, commissionRT, tz, winFrom, winTo,
  riskPerTrade, maxTradesDay, maxLossesDay, dailyStop}` ; `T.settings.set(patch)`.
- `T.journal.list()`, `.add(entrée)` → id, `.update(id, patch)`, `.remove(id)`, `.on(fn)`.
- `T.shared.watch(collection, fn)` → reçoit la liste des documents (écrits par Claude) et
  rend une fonction de désabonnement. Collections : `macro`, `calendar`.
- `T.day.mark(étape)` : marque une étape de la carte de séance comme faite aujourd'hui.
  Étapes : `macro`, `biais`, `fenetre`, `declencheur`, `risque`, `journal`, `revue`.

Navigation : `T.nav.go(deskId, tabId)`, `T.toast(message)`.

## Schéma d'une entrée de journal (partagé par tous les desks)

```
{ at: ms (heure de la décision), kind: 'pris' | 'refus',
  stage: 'macro'|'biais'|'vwap'|'declencheur'|'risque'|'autre'   // pour un refus
  side: 'long'|'short', setup: texte (ex. 'Bande VWAP · Rejet'),
  entry, stop, target, exit: prix ; qty: contrats ; instrument: 'MNQ'|'NQ'
  status: 'ouvert'|'clos', closedAt: ms,
  pnl: dollars nets de commission, r: résultat en R,
  fin: 'objectif'|'stop'|'cloche'|'invalidation'|'manuel',
  conviction: 1..5, plan: true|false (plan respecté), emotion: texte, note: texte }
```
Un refus ne porte **ni sens ni mise** (ALP nº 3 : une abstention qui porte une direction a
été complétée après coup). Les champs de décision se scellent à la saisie ; seuls les
champs d'issue (exit, fin, pnl, r, note) se complètent ensuite.

## Données de marché : la règle

**Aucun chiffre de marché inventé.** Pas de niveau, de prix, de CPI, de taux « d'exemple »
présentés comme réels. Si une vue attend des données (de l'utilisateur ou de Claude), elle
montre un état vide soigné qui dit quoi fournir et comment. Les constantes publiques
(spécifications CME du NQ/MNQ, horaires Globex) et les résultats du document de recherche
ALP nº 3 (textes bruts : `/tmp/claude-0/-home-user-Alp-1/d10614f7-6262-5c23-be49-fb171f0a286c/scratchpad/alp3txt/pNN.txt`,
dépôt : `/home/user/Alp-1`) sont autorisés, **avec leur source** dans une note. Les règles
de prop firm changent : tout préréglage est modifiable et marqué « à vérifier ».

## Style

- Français, ton neutre, phrases courtes et claires, apostrophes typographiques (’),
  pas de jargon non expliqué. L'utilisateur aime une écriture soignée : un titre de page
  porte souvent un mot en italique serif (`'Le risque, *d’abord*.'`).
- Chaque vue tient à **390 px** sans défilement horizontal (les tableaux défilent dans
  leur cadre). Pas de texte coupé, pas de chevauchement.
- Chaque formule a un test unitaire, et chaque nombre tiré d'ALP nº 3 est contrôlé
  contre le texte ou le code du dépôt.
- Toute méthode statistique vient avec sa **loi nulle** (règle du dépôt ALP) : un
  backtest se compare à des entrées au hasard, un taux de réussite à son taux d'équilibre.

## Vérifier avant de rendre

```
cd $D
python3 build.py --only <id> --fonts --out dist/only-<id>.html
node --check dist/only-<id>.html.js
node test/<id>.test.js
node test/e2e.js http://127.0.0.1:8766/desk/dist/only-<id>.html <id> --shots shots/<id> --full
```
Le serveur d'aperçu tourne déjà sur le port 8766 (sinon :
`cd /tmp/claude-0/-home-user-Alp-1/d10614f7-6262-5c23-be49-fb171f0a286c/scratchpad && setsid nohup python3 -m http.server 8766 &`).
Le banc doit rendre `"bad": 0`. **Regarde ensuite tes captures** (outil Read sur les PNG
de `shots/<id>/`) : un défaut visible (texte qui déborde d'une carte, graphique vide,
étiquettes qui se chevauchent) se corrige avant de rendre. Crée `shots/<id>` avant.
