// Tests de l’éditeur de stratégie (parties pures de T.lib.laboBuilder) : génération des champs depuis GRAMMAR
// pour chaque forme, valeurs de départ valides, aller-retour retouche → spec → normalize → describe, noms de
// paramètres automatiques et uniques, détection des formes trop profondes, messages en clair, versions, aperçu.
// node test/labo-builder.test.js
'use strict';
const { T, lib: LB } = require('./harness')(['quant', 'labo-engine', 'labo-stats', 'labo-builder']);
const LE = T.lib.laboEngine, LS = T.lib.laboStats, G = LS.GRAMMAR;
let pass = 0, fail = 0;
function ok(c, m) { if (c) pass++; else { fail++; console.log('ÉCHEC : ' + m); } }
function eq(a, b, m) { ok(JSON.stringify(a) === JSON.stringify(b), m + ' — attendu ' + JSON.stringify(b) + ', obtenu ' + JSON.stringify(a)); }
function throws(f, m) { try { f(); ok(false, m + ' (aucune erreur)'); } catch (e) { ok(true, m); } }
function clean(t, m) { ok(typeof t === 'string' && t.trim().length > 0 && !/undefined|NaN|\[object|null\b/.test(t), m + ' — « ' + t + ' »'); }
function clone(x) { return JSON.parse(JSON.stringify(x)); }
const PNAME = /^[A-Za-z_][A-Za-z0-9_]*$/;
/* Une stratégie minimale valide (achat seul, sans miroir à calculer), dont on remplace des morceaux. */
function base(patch) {
  const s = { name: 'Essai', hypothesis: 'Hypothèse de test.', side: 'long', mirror: true,
    long: { setup: [], trigger: { bar: 'up' }, entry: { type: 'market' }, stop: { type: 'pts', value: 10 }, target: { type: 'r', value: 2 } } };
  return Object.assign(s, patch || {});
}
function errs(spec) { return LS.normalize(spec).errors; }
function describeClean(spec, m) {
  const d = LS.describe(spec);
  ok(Array.isArray(d) && d.length > 0, m + ' : describe rend des blocs');
  d.forEach(b => clean(b.text, m + ' : phrase ' + b.id));
}

/* ---------- 0. Publication ---------- */
['render', 'fieldsFor', 'initOperand', 'initCond', 'initOrder', 'initManage', 'blank', 'switchCond', 'walkBlock', 'autoName', 'setNumber', 'parametrize',
  'renameParam', 'pruneDropped', 'editable', 'isDeep', 'deepItems', 'humanize', 'cardOf', 'cards', 'shortName', 'operandsOf', 'canonOp', 'previewFromFeatures',
  'versionInfo', 'versionGroups', 'parseJson', 'claudeText', 'specForSave'].forEach(k => ok(typeof LB[k] === 'function', 'LB.' + k + ' publié'));
eq(LB.CARDS.map(c => c.id), ['seance', 'sens', 'contexte', 'declencheur', 'entree', 'stop', 'objectif', 'gestion', 'risque', 'parametres', 'hypothese', 'oos'], 'cartes dans l’ordre des blocs (LABO.md §6)');
ok(T.desks().every(d => d.id !== 'laboBuilder' && d.id !== 'labo-builder'), 'aucun desk enregistré par le fichier');

/* ---------- 1. Champs générés depuis GRAMMAR : chaque argument de chaque forme a un widget connu ---------- */
let nArgs = 0;
function checkFields(args, obj, owner) {
  const fs = LB.fieldsFor(args, obj, owner);
  eq(fs.length, args.length, owner + ' : un champ par argument');
  fs.forEach((f, i) => {
    nArgs++;
    ok(LB.WIDGETS.indexOf(f.widget) >= 0, owner + '.' + f.k + ' : widget connu (' + f.widget + ')');
    clean(f.label, owner + '.' + f.k + ' : libellé');
    eq(f.path, String(args[i].k).split('.'), owner + '.' + f.k + ' : chemin');
    ok(f.numeric === (f.widget === 'number' || f.widget === 'barsOrTime'), owner + '.' + f.k + ' : drapeau numérique');
    if (f.widget === 'chips' || f.widget === 'select') ok(Array.isArray(f.options) && f.options.length > 0 && f.options.every(o => o.label), owner + '.' + f.k + ' : options libellées');
  });
  return fs;
}
const CLS_CMP = { niveau: x => ({ cmp: '>', a: { f: 'close' }, b: x }), ecart: x => ({ cmp: '>', a: x, b: 0 }), oscillateur: x => ({ cmp: '>', a: x, b: 50 }), neutre: x => ({ cmp: '>', a: x, b: 0 }), constante: x => ({ cmp: '>', a: { f: 'body' }, b: x }) };
G.operands.forEach(d => {
  const x = LB.initOperand(d.f), owner = d.form ? null : 'operand:' + d.f;
  if (d.f === 'const') { ok(typeof x === 'number', 'const : valeur de départ numérique'); eq(LB.opKind(x), 'const', 'const : genre'); eq(LB.opKind('$p'), 'const', '"$nom" : genre const'); return; }
  eq(LB.opKind(x), d.f === 'op' ? 'op' : d.f, d.f + ' : genre de la valeur de départ');
  checkFields(d.args, x, owner || 'operand:op');
  let cls = null;
  try { cls = LS.classOf(x); } catch (e) { ok(false, d.f + ' : classe calculable (' + e.message + ')'); return; }
  ok(['niveau', 'ecart', 'oscillateur', 'neutre', 'constante'].indexOf(cls) >= 0, d.f + ' : classe ' + cls);
  const spec = base(); spec.long.setup = [CLS_CMP[cls](x)];
  eq(errs(spec), [], d.f + ' : la valeur de départ passe normalize dans une comparaison');
  describeClean(spec, d.f);
  clean(LB.shortName(x), d.f + ' : nom court');
  const n = LS.normalize(spec).spec;
  clean(LB.shortName(n.long.setup[0].a, n.params) + LB.shortName(n.long.setup[0].b, n.params), d.f + ' : nom court après normalize');
});
G.conditions.forEach(d => {
  const c = LB.initCond(d.key);
  eq(LB.condKey(c), d.key, d.key + ' : clé de la valeur de départ');
  checkFields(d.args, c, 'cond:' + d.key);
  const spec = base(); spec.long.trigger = c;
  eq(errs(spec), [], d.key + ' : la valeur de départ passe normalize comme déclencheur');
  describeClean(spec, 'cond ' + d.key);
  const sp2 = base(); sp2.long.setup = [clone(c)];
  eq(errs(sp2), [], d.key + ' : la valeur de départ passe normalize comme contexte');
  ok(LB.editable(c, true), d.key + ' : éditable au premier niveau');
});
[['entry', G.entries], ['stop', G.stops], ['target', G.targets]].forEach(([kind, list]) => list.forEach(d => {
  const x = LB.initOrder(kind, d.type);
  eq(x.type, d.type, kind + ':' + d.type + ' : type');
  checkFields(d.args, x, kind + ':' + d.type);
  const spec = base(); spec.long[kind] = x;
  eq(errs(spec), [], kind + ':' + d.type + ' : la valeur de départ passe normalize');
  describeClean(spec, kind + ':' + d.type);
}));
['breakeven', 'trail'].forEach(w => {
  const m = LB.initManage(w);
  checkFields(G.manage[w].args, m, w);
  const spec = base({ manage: {} }); spec.manage[w] = m;
  eq(errs(spec), [], w + ' : la valeur de départ passe normalize');
  describeClean(spec, w);
});
ok(LB.initManage('trail').n === undefined, 'suiveur en points : pas de longueur d’ATR écrite');
checkFields(G.manage.args, {}, 'manage');
checkFields(G.risk, {}, 'risk');
checkFields(G.costs, {}, 'costs');
checkFields(G.session, {}, 'session');
ok(nArgs > 80, 'tous les arguments de la grammaire visités (' + nArgs + ')');
throws(() => LB.initOperand('nimporte'), 'opérande inconnu refusé');
throws(() => LB.initCond('nimporte'), 'condition inconnue refusée');
throws(() => LB.initOrder('stop', 'nimporte'), 'type d’ordre inconnu refusé');
/* Arguments masqués quand ils sont sans effet. */
const fd = LB.fieldsFor(G.operands.find(o => o.f === 'dist').args, { f: 'dist', unit: 'pts' }, 'operand:dist');
ok(fd.find(f => f.k === 'n').hidden && !LB.fieldsFor(G.operands.find(o => o.f === 'dist').args, { unit: 'atr' }, 'operand:dist').find(f => f.k === 'n').hidden, 'dist : longueur d’ATR masquée hors unité ATR');
const fl = LB.fieldsFor(G.entries.find(o => o.type === 'limit').args, { valid: 3 }, 'entry:limit');
ok(fl.find(f => f.k === 'tz').hidden && !LB.fieldsFor(G.entries.find(o => o.type === 'limit').args, { valid: '10:00' }, 'entry:limit').find(f => f.k === 'tz').hidden, 'limite : fuseau masqué tant que la validité est en barres');
eq(LB.fieldsFor(G.conditions.find(c => c.key === 'news').args, { news: { impact: 3 } }, 'cond:news').map(f => f.value), [3, undefined, undefined], 'clé pointée : valeur lue dans le sous-objet');
eq(LB.widgetOf({ type: 'enum', free: true, options: [] }), 'tz', 'fuseau libre');
eq(LB.widgetOf({ type: 'enum', options: [1, 2, 3, 4, 5, 6, 7].map(v => ({ v, label: String(v) })) }), 'select', 'plus de six options : liste');
eq(LB.widgetOf({ type: 'nimporte' }), 'advanced', 'type inconnu : bloc avancé');

/* ---------- 2. Changer le genre d’une condition ---------- */
const sw1 = LB.switchCond({ bar: 'up' }, 'not');
eq(sw1, { not: { bar: 'up' } }, 'simple → non : enveloppée');
eq(LB.switchCond(sw1, 'any'), { any: [{ bar: 'up' }] }, 'non → au moins une : l’enfant suit');
eq(LB.switchCond({ for: 4, cond: { bar: 'down' } }, 'within'), { within: 4, cond: { bar: 'down' } }, 'pour n → dans n : n et l’enfant gardés');
eq(LB.condKey(LB.switchCond({ any: [{ bar: 'up' }] }, 'cmp')), 'cmp', 'regroupement → simple : condition neuve');
eq(LB.switchCond({ bar: 'up' }, 'bar'), { bar: 'up' }, 'même genre : copie');
eq(errs(base({ long: Object.assign(base().long, { setup: [LB.switchCond({ cmp: '>', a: { f: 'close' }, b: { f: 'vwap' } }, 'for')] }) })), [], 'condition enveloppée valide');

/* ---------- 3. Noms de paramètres automatiques, uniques ---------- */
eq(LB.autoName('stop', {}), 'stop', 'nom libre gardé');
eq(LB.autoName('stop', { stop: {} }), 'stop_2', 'collision : suffixe _2');
eq(LB.autoName('stop', { stop: {}, stop_2: {} }), 'stop_3', 'collision : suffixe _3');
eq(LB.autoName('Écart à la séance', {}), 'ecart_a_la_seance', 'accents retirés, espaces en _');
eq(LB.autoName('20 barres', {}), 'p_20_barres', 'commence par une lettre');
eq(LB.autoName('', {}), 'p', 'vide : p');
ok(LB.autoName('x'.repeat(60), {}).length <= 24, 'nom borné à 24 caractères');
ok(['stop', 'Écart', '2', '$x', 'news.impact', '', null].every(hn => PNAME.test(LB.autoName(hn, {}))), 'tout nom produit est un identifiant valide');
/* Une règle où chaque nombre doit devenir un paramètre, et plusieurs se disputent le même nom. */
function busy() {
  return base({ side: 'long', manage: { breakeven: { r: 1.5 }, trail: { type: 'atr', value: 2, n: 10, start: 1 }, maxBars: 30 },
    long: { setup: [{ cmp: '>', a: { f: 'close' }, b: { f: 'ema', n: 50 } }, { cmp: '>', a: { f: 'rsi', n: 14 }, b: 55 }, { within: 5, cond: { cross: 'up', a: { f: 'close' }, b: { f: 'vwap', k: 1 } } }, { any: [{ cmp: '>', a: { f: 'dist', a: { f: 'close' }, b: { f: 'vwap' }, unit: 'pts' }, b: 3 }, { bar: 'up' }] }],
      trigger: { cross: 'up', a: { f: 'ema', n: 9 }, b: { f: 'ema', n: 21 } }, entry: { type: 'limit', at: { f: 'vwap', k: -1 }, offset: 2, valid: 3 },
      stop: { type: 'atr', value: 1.5, n: 14, buffer: 2 }, target: { type: 'pts', value: 25 } } });
}
const sb = busy();
eq(errs(sb), [], 'règle chargée valide avant paramétrage');
const created = [];
Object.keys(LB.PARAM_BLOCKS).forEach(b => LB.parametrize(sb, b, 'long').forEach(n => created.push(n)));
ok(created.length >= 18, 'chaque nombre devient un paramètre (' + created.length + ')');
eq(new Set(created).size, created.length, 'noms tous distincts');
ok(created.every(n => PNAME.test(n)), 'noms valides : ' + created.join(', '));
eq(Object.keys(sb.params).sort(), created.slice().sort(), 'params = noms créés');
const leftover = [];
Object.keys(LB.PARAM_BLOCKS).forEach(b => LB.walkBlock(sb, b, 'long', (p, a, o, v) => { if (typeof v === 'number' && ['int', 'num', 'barsOrTime'].indexOf(a.type) >= 0) leftover.push(p.join('.')); }));
eq(leftover, [], 'plus aucun nombre littéral dans les blocs de règle');
ok(created.filter(n => /^ema/.test(n)).length === 3 && created.indexOf('ema_2') >= 0 && created.indexOf('ema_3') >= 0, 'trois longueurs d’EMA : ema, ema_2, ema_3');
eq(errs(sb), [], 'règle paramétrée valide');
eq(LS.resolve(LS.normalize(sb).spec, {}).long, LS.resolve(LS.normalize(busy()).spec, {}).long, 'résolue, la règle paramétrée est la règle d’origine');
ok(Object.keys(sb.params).every(n => typeof sb.params[n].label === 'string' && sb.params[n].label.length > 2 && !/undefined/.test(sb.params[n].label)), 'chaque paramètre a un libellé');
eq(sb.params.stop_atr.label, 'Multiple (stop, ATR)', 'libellé : argument, porteur, unité');
eq(LB.parametrize(sb, 'stop', 'long'), [], 'second passage : rien de neuf');
eq(LB.parametrize(sb, 'risque', 'long'), [], 'risque et coûts ne sont pas paramétrés');
/* setNumber : écrit dans le paramètre existant, élargit sa plage. */
const sn = base(); sn.params = { stop: { v: 10, min: 8, max: 12, step: 1 } }; sn.long.stop.value = '$stop';
eq(LB.setNumber(sn, ['long', 'stop', 'value'], 20, 'stop:pts', G.stops[0].args[0]), 'stop', 'nombre écrit dans le paramètre lié');
eq([sn.params.stop.v, sn.params.stop.max, sn.long.stop.value], [20, 20, '$stop'], 'valeur posée, plage élargie, référence gardée');
eq(LB.setNumber(sn, ['long', 'target', 'value'], 3, 'target:r', G.targets[0].args[0]), 'objectif', 'nombre neuf : paramètre créé');
eq([sn.long.target.value, sn.params.objectif.v], ['$objectif', 3], 'référence écrite');
eq(errs(sn), [], 'spec valide après setNumber');
/* Renommer partout. */
const rn = clone(sb);
eq(LB.renameParam(rn, 'stop_atr', 'k_stop'), null, 'renommage accepté');
ok(!rn.params.stop_atr && rn.params.k_stop && rn.long.stop.value === '$k_stop', 'référence renommée');
eq(errs(rn), [], 'spec valide après renommage');
ok(/pris/.test(LB.renameParam(rn, 'k_stop', 'ema')), 'nom pris refusé');
ok(/invalide/.test(LB.renameParam(rn, 'k_stop', 'é t é')), 'nom invalide refusé');
ok(/introuvable/.test(LB.renameParam(rn, 'zzz', 'yyy')), 'paramètre absent signalé');
eq(Object.keys(rn.params).indexOf('k_stop'), Object.keys(sb.params).indexOf('stop_atr'), 'l’ordre des paramètres est gardé');
/* Comptes d’usage, paramètres abandonnés. */
const us = base({ params: { a: { v: 1 }, b: { v: 2 }, old: { v: 3 } } }); us.long.stop.value = '$a'; us.long.target.value = '$a';
eq([LB.useCount(us, 'a'), LB.useCount(us, 'b')], [2, 0], 'comptes d’usage');
const before = clone(us); before.long.stop.value = '$b';
const after = clone(us); after.params.fresh = { v: 9 };
eq(LB.pruneDropped(before, after).sort(), ['b', 'fresh'], 'retiré : le paramètre que la retouche a lâché et celui qu’elle a créé sans s’en servir');
ok(after.params.old && after.params.a, 'gardé : le paramètre déjà inutilisé avant (normalize le signale)');

/* ---------- 4. Formes trop profondes ---------- */
const simple = { bar: 'up' }, one = { any: [{ bar: 'up' }, { cmp: '>', a: { f: 'close' }, b: { f: 'vwap' } }] };
const deep1 = { any: [{ all: [{ bar: 'up' }, { bar: 'down' }] }, { bar: 'up' }] }, deep2 = { not: { any: [{ bar: 'up' }] } }, deep3 = { for: 3, cond: { not: { bar: 'up' } } };
ok(LB.editable(simple, false) && LB.editable(simple, true), 'condition simple éditable partout');
ok(LB.editable(one, true) && !LB.editable(one, false), 'un niveau de regroupement : éditable au premier niveau seulement');
ok(LB.editable({ not: { bar: 'up' } }, true) && LB.editable({ within: 2, cond: { bar: 'up' } }, true), 'non et dans n barres : un niveau');
[deep1, deep2, deep3].forEach((c, i) => ok(LB.isDeep(c) && !LB.editable(c, true), 'forme profonde ' + (i + 1) + ' détectée'));
ok(LB.isDeep({ foo: 1 }) && LB.isDeep(null) && LB.isDeep({ bar: 'up', cmp: '>' }), 'forme illisible : avancée');
const dp = base(); dp.long.setup = [simple, deep1, one, deep2]; dp.long.trigger = deep3;
const di = LB.deepItems(dp, 'long');
eq(di.map(x => x.path.join('.')), ['long.setup.1', 'long.setup.3', 'long.trigger'], 'formes profondes localisées');
eq(di.map(x => x.card), ['contexte', 'contexte', 'declencheur'], 'rangées dans leur carte');
ok(di.every(x => /Claude ou en JSON/.test(x.text)), 'message « bloc avancé — modifiable par Claude ou en JSON »');
eq(errs(dp), [], 'une forme profonde reste une stratégie valide');
const dc = LB.cards(dp);
eq([dc.list.find(c => c.id === 'contexte').advanced.length, dc.list.find(c => c.id === 'declencheur').advanced.length], [2, 1], 'cartes : blocs avancés affichés');
eq(LB.deepItems(base(), 'long'), [], 'règle simple : aucun bloc avancé');
eq(LB.ADVANCED, 'Bloc avancé — modifiable par Claude ou en JSON.', 'libellé du bloc avancé');

/* ---------- 5. Erreurs en clair, rangées par carte ---------- */
eq(LB.cardOf('long.stop.value'), 'stop', 'chemin → carte stop');
eq(LB.cardOf('long.setup[1].a.n'), 'contexte', 'chemin → carte contexte');
eq(LB.cardOf('short.target.at'), 'objectif', 'côté vendeur → carte objectif');
eq(LB.cardOf('session.flat'), 'seance', 'séance');
eq(LB.cardOf('costs.slipTicks'), 'risque', 'coûts → risque et coûts');
eq(LB.cardOf('params.x'), 'parametres', 'paramètres');
eq(LB.cardOf('short'), 'sens', 'règle de vente absente → sens');
eq(LB.cardOf('nimporte'), 'general', 'chemin inconnu → général');
eq(LB.pathText('long.setup[1].a.n'), 'achat › condition 2 › premier terme › longueur', 'chemin en mots');
eq(LB.pathText('params.ema_2.min'), 'paramètre « ema_2 » › minimum', 'paramètre nommé');
const hz = LB.humanize('long.stop.value : doit être > 0.');
eq([hz.path, hz.card], ['long.stop.value', 'stop'], 'humanize : chemin et carte');
ok(/^Achat › stop › valeur : Doit être/.test(hz.text), 'humanize : texte « ' + hz.text + ' »');
eq(LB.humanize('Phrase sans chemin').card, 'general', 'message sans chemin : général');
const bad = base(); bad.long.stop = { type: 'pts', value: -3 }; bad.session = { from: '25:00' }; bad.long.target = { type: 'r', value: '$absent' };
const bc = LB.cards(bad);
ok(bc.errors >= 3, 'erreurs comptées (' + bc.errors + ')');
ok(bc.list.find(c => c.id === 'stop').errors.length >= 1, 'erreur de stop sur la carte stop');
ok(bc.list.find(c => c.id === 'seance').errors.length >= 1, 'erreur d’heure sur la carte séance');
ok(bc.list.find(c => c.id === 'objectif').errors.length >= 1, '$nom absent sur la carte objectif');
ok(bc.list.find(c => c.id === 'objectif').partial === LB.PARTIAL && !bc.list.find(c => c.id === 'entree').partial, 'carte en erreur : la phrase est dite partielle, les autres non');
bc.list.forEach(c => { c.errors.concat(c.warnings).forEach(t => clean(t, 'message de la carte ' + c.id)); c.texts.forEach(t => clean(t, 'phrase de la carte ' + c.id)); });

/* ---------- 6. Cartes : une phrase par bloc, gabarits, côté vendeur ---------- */
LS.TEMPLATES.forEach(tp => {
  const d = LS.fromTemplate(tp.id), c = LB.cards(d);
  eq(c.errors, 0, 'gabarit ' + tp.id + ' : aucune erreur');
  c.list.filter(x => x.id !== 'oos').forEach(x => { ok(x.texts.length > 0, tp.id + ' : carte ' + x.id + ' non vide'); x.texts.forEach(t => clean(t, tp.id + ' : ' + x.id)); });
  ok(c.list.find(x => x.id === 'sens').texts.length === (d.side === 'long' ? 1 : 2), tp.id + ' : le côté vendeur reflété est lu dans la carte sens');
  ok(LB.operandsOf(d).length >= 1, tp.id + ' : au moins une série à montrer');
});
const ws = base({ side: 'both', mirror: false, short: { setup: [], trigger: { bar: 'down' }, entry: { type: 'market' }, stop: { type: 'pts', value: 12 }, target: { type: 'r', value: 3 } } });
eq(errs(ws), [], 'règle de vente écrite à part : valide');
const wc = LB.cards(ws, { side: 'short' });
ok(/vente/i.test(wc.list.find(c => c.id === 'entree').texts[0]) && /12/.test(wc.list.find(c => c.id === 'stop').texts[0]) && /3/.test(wc.list.find(c => c.id === 'objectif').texts[0]), 'vue vendeur : les cartes lisent la règle de vente');
ws.long.stop.value = '$s'; ws.params = { s: { v: 10 } };
const wsp = LB.parametrize(ws, 'stop', 'short');
eq([wsp, ws.short.stop.value, ws.params.stop.v], [['stop'], '$stop', 12], 'paramétrer la règle de vente');
const noShort = base({ side: 'both', mirror: false });
ok(LB.cards(noShort).list.find(c => c.id === 'sens').errors.length > 0, 'sans miroir et sans règle de vente : erreur sur la carte sens');

/* ---------- 7. Aller-retour : retouche → spec → normalize → describe ---------- */
let rt = LB.blank();
eq(errs(rt), [], 'page vierge valide');
ok(Object.keys(rt.params).every(n => LB.useCount(rt, n) === 1), 'page vierge : chaque paramètre est lu');
rt.long.setup.push(LB.initCond('cmp'));                                  // close > vwap
rt.long.setup[0].b = LB.initOperand('ema');                              // close > ema(20)
LB.setNumber(rt, ['long', 'setup', 0, 'b', 'n'], 34, 'operand:ema', G.operands.find(o => o.f === 'ema').args[0]);
rt.long.trigger = LB.switchCond(rt.long.trigger, 'not');                 // non (barre haussière)
rt.long.entry = LB.initOrder('entry', 'limit');
rt.long.entry.at = LB.initOperand('prev'); rt.long.entry.at.of = 'low';
rt.manage = { breakeven: LB.initManage('breakeven') };
['contexte', 'declencheur', 'entree', 'gestion'].forEach(b => LB.parametrize(rt, b, 'long'));
LB.pruneDropped(LB.blank(), rt);
const rn1 = LS.normalize(rt);
eq(rn1.errors, [], 'retouches : aucune erreur');
eq(rt.long.setup[0].b.n, '$ema', 'longueur d’EMA nommée');
eq(rt.params.ema.v, 34, 'valeur du paramètre');
ok(rt.manage.breakeven.r === '$be', 'break-even nommé');
const rd = LS.describe(rn1.spec);
const rdText = rd.map(b => b.text).join(' ');
ok(/34/.test(rdText) && /ema/i.test(rdText), 'describe lit la longueur 34 de l’EMA');
ok(/veille|précédente/i.test(rd.find(b => b.id === 'entree').text), 'describe lit l’entrée limite sur la séance précédente');
rd.forEach(b => clean(b.text, 'aller-retour : ' + b.id));
const json = JSON.stringify(rn1.spec);
const pj = LB.parseJson(json, Object.assign({}, rn1.spec, { id: 'sabcdefg_v2', sid: 'sabcdefg', version: 2, status: 'brouillon' }));
ok(pj.ok, 'JSON relu sans erreur');
eq([pj.spec.id, pj.spec.sid, pj.spec.version], ['sabcdefg_v2', 'sabcdefg', 2], 'l’identité de la version courante est gardée');
eq(LS.canonical(LS.resolve(pj.spec, {}).long), LS.canonical(LS.resolve(rn1.spec, {}).long), 'JSON → spec : même règle');
eq(LB.specForSave(rt).long, rn1.spec.long, 'à enregistrer : la spec normalisée');
const broken = clone(rt); broken.long.stop.value = '$nulle';
eq(LB.specForSave(broken).long.stop.value, '$nulle', 'spec en erreur : écrite telle quelle (rien n’est retiré en silence)');
const pjBad = LB.parseJson('{ "long": ', null);
ok(!pjBad.ok && /JSON illisible/.test(pjBad.errors[0]), 'JSON illisible signalé');
ok(!LB.parseJson('[1,2]', null).ok, 'un tableau n’est pas une stratégie');
const pjErr = LB.parseJson(JSON.stringify(broken), null);
ok(!pjErr.ok && pjErr.errors.some(m => /nulle/.test(m)), 'erreur de normalize remontée');
pjErr.errors.forEach(m => clean(LB.humanize(m).text, 'erreur JSON en clair'));

/* ---------- 8. Aperçu : opérandes, noms, séance témoin ---------- */
const vr = LS.fromTemplate('vwap-rejet');
const ops = LB.operandsOf(vr);
eq(ops.map(o => o.name), ['VWAP', 'VWAP −2 σ', 'VWAP +2 σ'], 'vwap-rejet : VWAP, bande d’achat, bande de vente reflétée, sans doublon');
ok(ops.every(o => o.cls === 'niveau' && typeof o.text === 'string'), 'classes et lectures des séries');
eq(LB.canonOp({ f: 'vwap', k: 0 }), { f: 'vwap' }, 'forme canonique : défaut retiré');
eq(LB.canonOp({ f: 'ema', n: 9, of: { f: 'close' } }), { f: 'ema', n: 9 }, 'forme canonique : opérande par défaut retiré');
eq(LB.canonOp({ op: '-', a: { f: 'close', lag: 0 }, b: 2 }), { op: '-', a: { f: 'close' }, b: 2 }, 'forme canonique : récursive');
eq(LB.operandsOf(base()).length, 0, 'règle sans opérande : aucune série');
eq(LB.shortName({ f: 'vwap', k: '$b' }, { b: { v: -1.5 } }), 'VWAP −1,5 σ', 'nom court : paramètre résolu');
eq(LB.shortName({ op: '-', a: { f: 'high' }, b: { f: 'atr' } }), '(Plus haut − ATR 14)', 'nom court : calcul');
const lat = LE.lattice({ sessions: 8, sigma: 3, seed: 5 });
const pspec = LS.normalize(base({ long: Object.assign(base().long, { trigger: { cross: 'up', a: { f: 'close' }, b: { f: 'ema', n: 9 } } }) })).spec;
const pops = LB.operandsOf(pspec);
const feat = LE.op('features', { bars: lat, spec: pspec, values: {}, operands: pops.map(o => o.operand), settings: { tick: 0.25, pointValue: 2 }, sel: { from: lat.keys[2], to: lat.keys[7] } });
const pv = LB.previewFromFeatures(feat, pops);
ok(!pv.error && pv.series.length === 1 && pv.series[0].name === 'EMA 9', 'aperçu : une série nommée');
ok(pv.sessions >= 2 && pv.sessions <= 5, 'aperçu : séances découpées (' + pv.sessions + ')');
ok(pv.signals.length > 0 && !pv.none, 'aperçu : la séance témoin porte des signaux');
const lastSig = (function () { let k = -1; const L = feat.sig.L; for (let i = 0; i < L.length; i++) if (L[i] === 1) k = i; return k; })();
ok(pv.bars.t.indexOf(feat.t[lastSig]) >= 0, 'aperçu : c’est la dernière séance qui porte un signal');
eq(pv.series[0].points.length, pv.bars.t.length, 'aperçu : une valeur par barre');
ok(pv.signals.every(s => pv.bars.t.indexOf(s.t) >= 0 && s.side === 'long'), 'aperçu : signaux dans la séance témoin');
ok(pv.series[0].points.every(p => p[1] === null || Number.isFinite(p[1])), 'aperçu : aucune valeur non finie');
ok(/^\d{4}-\d{2}-\d{2}$/.test(pv.key), 'aperçu : clé AAAA-MM-JJ');
const silent = LB.previewFromFeatures(Object.assign({}, feat, { sig: { L: new Array(feat.t.length).fill(0), S: null } }), pops);
ok(silent.none && silent.signals.length === 0 && silent.bars.t.length > 0, 'aperçu sans signal : dernière séance, signalée « none »');
ok(LB.previewFromFeatures({ t: [] }, []).error, 'aperçu vide : erreur');

/* ---------- 9. Versions, scellement, texte pour Claude ---------- */
const doc = Object.assign(LS.fromTemplate('rsi-retour', 'sabcdefg', 1767225600000), { hypothesis: 'Un excès de RSI se résorbe ; réfutée si p ≥ 0,05.' });
eq(LB.versionInfo(doc).status, 'brouillon', 'brouillon');
const sealed = LS.seal(doc, 1.24, 1767312000000);
const vi = LB.versionInfo(sealed);
eq([vi.status, vi.short, vi.version], ['scellee', sealed.hash.slice(0, 9), 1], 'scellée : état et hachage court');
const tampered = clone(sealed); tampered.long.stop = { type: 'pts', value: 99 };
eq(LB.versionInfo(tampered).status, 'alteree', 'scellée puis modifiée : altérée');
const g = LB.versionGroups([
  Object.assign(clone(doc), { id: 'sabcdefg_v1', u: 10 }), Object.assign(clone(sealed), { id: 'sabcdefg_v2', version: 2, u: 30 }),
  { id: 'szzzzzzz_v1', sid: 'szzzzzzz', version: 1, name: 'Autre', u: 20 }, { id: 'sdeleted_v1', sid: 'sdeleted', version: 1, deleted: true, u: 99 }]);
eq(g.map(x => x.sid), ['sabcdefg', 'szzzzzzz'], 'groupes par sid, plus récent d’abord, supprimés exclus');
eq(g[0].versions.map(v => v.version), [2, 1], 'versions, la plus récente d’abord');
eq(LB.versionInfo({}).name, 'Sans nom', 'sans nom');
const ct = LB.claudeText(sealed, vi);
ok(ct.indexOf(sealed.id) >= 0 && ct.indexOf('"long"') >= 0 && /scellée/.test(ct) && /en mots/.test(ct), 'texte pour Claude : id, état, JSON, invitation à décrire en mots');
eq(JSON.parse(ct.slice(ct.indexOf('{'))).id, sealed.id, 'texte pour Claude : JSON relisible');

/* ---------- 10. Libellés et phrases sans défaut ---------- */
G.operands.filter(o => !o.form).forEach(o => o.args.forEach(a => clean(LB.labelOf('operand:' + o.f, a), 'libellé de paramètre ' + o.f + '.' + a.k)));
eq(LB.labelOf('stop:pts', G.stops[0].args[0]), 'Distance (stop, points)', 'libellé : distance du stop');
eq(LB.labelOf('breakeven', G.manage.breakeven.args[0]), 'Gain qui déclenche le break-even (R)', 'libellé : porteur non répété');
eq(LB.labelOf('const:cond', { k: 'v' }), 'Seuil', 'libellé : seuil d’une condition');
eq(LB.hintOf('operand:ema', 'n'), 'ema', 'indice de nom : opérande');
eq(LB.hintOf('cond:news', 'news.impact'), 'impact', 'indice de nom : clé pointée');
eq(LB.hintOf('const:cond', 'v'), 'seuil', 'indice de nom : constante d’une condition');

/* ---------- 11. JSON lisible, messages sans redite, noms des séries du desk ---------- */
[LB.blank(), busy(), LS.fromTemplate('gex-proche'), sealed, { a: [], b: {}, c: [1, 'x, y', null], d: [{ e: [1, 2] }], f: -0, g: 'é’"\\' }].forEach((x, i) => {
  const txt = LB.pretty(x);
  eq(JSON.parse(txt), JSON.parse(JSON.stringify(x)), 'pretty ' + i + ' : JSON valide, même contenu');
});
ok(/"days": \[1, 2, 3, 4, 5\]/.test(LB.pretty(LS.normalize(base()).spec)), 'pretty : liste de nombres sur une ligne');
ok(/"a": \{ "f": "close" \}/.test(LB.pretty(LS.normalize(base({ long: Object.assign(base().long, { setup: [{ cmp: '>', a: { f: 'close' }, b: { f: 'vwap' } }] }) })).spec)), 'pretty : petit objet sur une ligne');
ok(LB.pretty(busy()).split('\n').every(l => l.length <= 100), 'pretty : lignes courtes');
const hh = LB.humanize('hypothesis : hypothèse vide : elle est exigée pour sceller.');
ok(/^Hypothèse vide/.test(hh.text) && hh.card === 'hypothese', 'humanize : pas de « Hypothèse : Hypothèse vide » (' + hh.text + ')');
ok(/^Achat\u00A0: Objectif absent/.test(LB.humanize('long.target : objectif absent : aucun objectif retenu.').text), 'humanize : chemin gardé, mot répété retiré');
const hc = LB.cards(base({ hypothesis: '' })).list.find(c => c.id === 'hypothese');
eq(hc.warnings, [], 'hypothèse vide : pas d’avertissement en double de la phrase de la carte');
ok(/exigée pour sceller/.test(hc.texts.join(' ')), 'hypothèse vide : la carte le dit');
const nm = LB.seriesNames(vr), R0 = LS.reader({});
eq(nm[R0.op({ f: 'vwap', k: -2 })].name, 'VWAP −2 σ', 'noms des séries : lecture longue → nom court');
eq(nm[R0.op({ f: 'vwap', k: 2 })].name, 'VWAP +2 σ', 'noms des séries : côté vendeur reflété');
ok(nm[R0.op({ f: 'close' })].close === true, 'noms des séries : la clôture est repérée (déjà tracée)');
eq(nm[R0.op({ f: 'vwap' })].cls, 'niveau', 'noms des séries : classe');

const tsx = Array.from({ length: 1380 }, (_, i) => i * 60000);
const cw1 = LB.cropWindow(tsx, [{ t: 900 * 60000 }, { t: 960 * 60000 }], 120);
eq([cw1.i0, cw1.i1, cw1.cropped], [780, 1081, true], 'recadrage : deux heures de part et d’autre des signaux groupés');
eq(cw1.slice(tsx).length, 301, 'recadrage : tranche des séries');
const cw2 = LB.cropWindow(tsx, [{ t: 60 * 60000 }, { t: 1300 * 60000 }], 120);
eq([cw2.i0, cw2.i1, cw2.cropped], [0, 1380, false], 'signaux étalés : toute la séance');
eq(LB.cropWindow(tsx, [], 120).cropped, false, 'sans signal : toute la séance');

console.log((fail ? 'ÉCHEC' : 'OK') + ' — labo-builder : ' + pass + ' réussis, ' + fail + ' échoués');
process.exit(fail ? 1 : 0);
