// Tests de T.lib.laboStats (LABO.md §3.0, §3.8, §5) et de tools/labo-check.js : node test/labo-stats.test.js
// (sortie non nulle si échec). Aucune donnée de marché : séries tirées avec une graine explicite, marches au tick
// du moteur (T.lib.laboEngine.lattice), résultats de verdict construits à la main.
'use strict';
const fs = require('fs'), os = require('os'), path = require('path'), cp = require('child_process');
const H = require('./harness');
const { T, lib: LS } = H(['quant', 'perf', 'risk', 'labo-engine', 'labo-stats']);
const LE = T.lib.laboEngine, Q = T.lib.quant, P = T.lib.perf;
let fails = 0, passes = 0;
function ok(cond, msg) { if (cond) passes++; else { fails++; console.error('ÉCHEC', msg); } }
function near(a, b, tol, msg) { const good = typeof a === 'number' && typeof b === 'number' && (a === b || Math.abs(a - b) <= tol); ok(good, msg + ' : ' + a + ' attendu ' + b + ' ± ' + tol); }
const C = x => LS.canonical(x);
function eq(a, b, msg) { const x = C(a), y = C(b); ok(x === y, msg + (x === y ? '' : ' :\n   ' + x.slice(0, 400) + '\n ≠ ' + y.slice(0, 400))); }
function throws(fn, re, msg) { try { fn(); ok(false, msg + ' (aucune erreur levée)'); } catch (e) { ok(!re || re.test(String(e.message)), msg + ' : ' + e.message); } }
function section(t) { console.log('· ' + t); }
const clone = x => JSON.parse(JSON.stringify(x));
function setPath(o, k, v) { const ps = k.split('.'); let x = o; for (let i = 0; i < ps.length - 1; i++) { if (!x[ps[i]] || typeof x[ps[i]] !== 'object') x[ps[i]] = {}; x = x[ps[i]]; } x[ps[ps.length - 1]] = v; }
function mulberry(seed) { let s = seed >>> 0; return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
function gauss(r) { let u = 0; while (u === 0) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); }
const mean = xs => xs.reduce((s, x) => s + x, 0) / xs.length;
const sdv = xs => { const m = mean(xs); return Math.sqrt(xs.reduce((s, x) => s + (x - m) * (x - m), 0) / (xs.length - 1)); };
const hasErr = (n, re) => n.errors.some(e => re.test(e));
const hasWarn = (n, re) => n.warnings.some(e => re.test(e));
const BAD = /undefined|NaN|\bnull\b|\[object|non reconnu|'/;
function readingOk(rows, msg, o) {
  o = o || {};
  ok(Array.isArray(rows) && rows.length >= 10, msg + ' : au moins dix blocs (' + (rows && rows.length) + ')');
  const ids = {};
  (rows || []).forEach(x => {
    ids[x.id] = 1;
    ok(x && typeof x.title === 'string' && x.title && !BAD.test(x.title) && typeof x.text === 'string' && x.text.trim().length > 8 && !BAD.test(x.text) && /[.!?»]$/.test(x.text),
      msg + ' : bloc ' + (x && x.id) + ' « ' + (x && x.text) + ' »');
    ok(!/\d{1,2} h \d\d/.test(x.text), msg + ' : heure sans espaces insécables dans ' + x.id + ' « ' + x.text + ' »');
  });
  ['seance', 'sens', 'declencheur', 'entree', 'stop', 'objectif', 'gestion', 'risque', 'couts', 'remplissage'].forEach(k => ok(ids[k], msg + ' : bloc ' + k + ' présent'));
  if (o.seller) { const v = rows.filter(x => x.id === 'vendeur')[0]; ok(v && !/Miroir impossible|Aucune règle/.test(v.text), msg + ' : côté vendeur lu' + (v ? ' « ' + v.text + ' »' : '')); }
}
/* Stratégie de base : un achat sur barre haussière, vente en miroir. */
function spec(rule, top) {
  const s = { sid: 'stest0001', name: 'Essai', hypothesis: 'Aucune : test de la grammaire.', side: 'both', mirror: true,
    long: Object.assign({ setup: [], trigger: { bar: 'up' }, entry: { type: 'market' }, stop: { type: 'pts', value: 5 }, target: { type: 'r', value: 2 } }, rule || {}) };
  return Object.assign(s, top || {});
}
const norm = (s, c) => LS.normalize(s, c);
const normCond = c => norm(spec({ trigger: c })).spec.long.trigger;
const G = LS.GRAMMAR;
function initOf(a) {
  if (a.type === 'conds') return [{ bar: 'up' }, { cmp: '>', a: { f: 'close' }, b: { f: 'vwap' } }];
  if (a.type === 'cond') return a.init !== undefined ? clone(a.init) : { bar: 'up' };
  if (a.init !== undefined) return clone(a.init);
  if (a.def !== undefined && a.def !== null) return clone(a.def);
  return undefined;
}
function build(args, head) { const o = Object.assign({}, head); args.forEach(a => { const v = initOf(a); if (v !== undefined) setPath(o, a.k, v); }); return o; }
const NOLVL = { dataset: { name: 'jeu témoin', roll: 'non-ajuste', source: 'fichier' } };

/* ---------------------------------------------------------------------------------------------- */
section('Grammaire : registre complet et lisible');
{
  const TYPES = ['int', 'num', 'time', 'timePair', 'enum', 'operand', 'names', 'bool', 'cond', 'conds', 'barsOrTime', 'days'];
  const CLS = ['niveau', 'ecart', 'oscillateur', 'neutre', 'of', 'calcule', 'constante'];
  const want = ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'volume', 'range', 'body', 'vwap', 'sma', 'ema', 'hh', 'll', 'sd', 'atr', 'rsi', 'rvol', 'prev', 'sess', 'or', 'at', 'tf', 'level', 'nearest', 'time', 'dow', 'sessmin', 'dist'];
  const fs_ = G.operands.filter(o => !o.form).map(o => o.f);
  eq(fs_.slice().sort(), want.slice().sort(), 'opérandes de §3.2, tous présents et rien d’autre');
  ok(G.operands.some(o => o.form === 'op') && G.operands.some(o => o.form === 'const'), 'formes calcul et constante déclarées');
  eq(G.conditions.map(c => c.key), Array.from(LE.COND_KEYS), 'conditions = celles du moteur, même ordre');
  eq(G.entries.map(x => x.type), ['market', 'limit', 'stop'], 'entrées');
  eq(G.stops.map(x => x.type), ['pts', 'atr', 'swing', 'level'], 'stops');
  eq(G.targets.map(x => x.type), ['r', 'pts', 'atr', 'level', 'none'], 'objectifs');
  const walk = (label, args) => {
    ok(typeof label === 'string' && label.trim() && !/'/.test(label), 'libellé lisible : ' + label);
    (args || []).forEach(a => {
      ok(typeof a.k === 'string' && TYPES.indexOf(a.type) >= 0 && typeof a.label === 'string' && a.label.trim() && !/'/.test(a.label), 'argument ' + label + '.' + a.k + ' (' + a.type + ')');
      if (a.type === 'enum') ok(Array.isArray(a.options) && a.options.length && a.options.every(o => typeof o.label === 'string' && o.label && !/'/.test(o.label)), 'options de ' + label + '.' + a.k);
    });
  };
  G.operands.forEach(o => { walk(o.label, o.args); ok(CLS.indexOf(o.cls) >= 0, 'classe déclarée de ' + o.f + ' : ' + o.cls); });
  G.conditions.forEach(o => walk(o.label, o.args));
  G.entries.concat(G.stops, G.targets).forEach(o => walk(o.label, o.args));
  walk(G.manage.breakeven.label, G.manage.breakeven.args); walk(G.manage.trail.label, G.manage.trail.args); walk('gestion', G.manage.args);
  walk('risque', G.risk); walk('coûts', G.costs); walk('séance', G.session);
  ['anchors', 'sides', 'fills', 'instruments', 'classes', 'groups'].forEach(k => ok(Array.isArray(G[k]) && G[k].length && G[k].every(o => typeof o.label === 'string' && o.label && !/'/.test(o.label) && !/\d h \d/.test(o.label)), 'liste ' + k + ' : libellés en texte, heures insécables'));
  eq(G.anchors.map(o => o.v), ['globex', 'paris', 'rth'], 'ancrages');
  eq(G.fills.map(o => o.v), ['pessimiste', 'optimiste', 'chemin'], 'remplissages déclarables (vrai est réservé aux marches synthétiques)');
  /* Formes que lit le moteur (rapport du moteur) : valid par défaut 1, through, buffer, dynamic, breakeven, trail, warmup. */
  const argOf = (list, t, k) => (list.filter(x => x.type === t)[0].args.filter(a => a.k === k)[0] || {});
  ok(argOf(G.entries, 'limit', 'valid').def === 1 && argOf(G.entries, 'stop', 'valid').def === 1, 'entry.valid vaut 1 barre par défaut, comme le moteur');
  ok(argOf(G.entries, 'limit', 'through').type === 'bool', 'entry.through');
  ok(G.stops.every(s => s.type === 'swing' || s.args.length) && argOf(G.stops, 'pts', 'buffer').unit === 'ticks', 'stop.buffer en ticks');
  ok(argOf(G.targets, 'level', 'dynamic').def === false, 'target.dynamic');
  eq(G.manage.breakeven.args.map(a => a.k), ['r', 'offset'], 'breakeven {r, offset}');
  eq(G.manage.trail.args.map(a => a.k), ['type', 'value', 'n', 'start'], 'trail {type, value, n, start}');
  ok(G.session.some(a => a.k === 'warmup' && a.def === 15), 'session.warmup = 15 min par défaut');
}

/* ---------------------------------------------------------------------------------------------- */
section('Défauts (§3.0) : des constantes du code, jamais T.settings');
{
  let reads = 0;
  const g0 = T.settings && T.settings.get;
  if (T.settings) T.settings.get = function () { reads++; return { instrument: 'NQ', pointValue: 20, tick: 1, commissionRT: 9, tz: 'Asia/Tokyo', winFrom: '03:00', winTo: '04:00', riskPerTrade: 999, maxTradesDay: 9, maxLossesDay: 9, dailyStop: 9 }; };
  const n = norm({ long: { trigger: { bar: 'up' }, stop: { type: 'pts', value: 5 } } });
  const D = LS.DEFAULTS;
  ok(n.errors.length === 0, 'document minimal sans erreur : ' + n.errors.join(' | '));
  ['instrument', 'anchor', 'session', 'side', 'mirror', 'short', 'manage', 'risk', 'costs', 'fill', 'params'].forEach(k => eq(n.spec[k], D[k], 'défaut ' + k));
  eq(D.session, { tz: 'Europe/Paris', from: '00:00', to: '09:00', flat: '09:00', days: [1, 2, 3, 4, 5], warmup: 15 }, 'session par défaut de §3.0');
  eq(D.risk, { mode: 'contracts', contracts: 1, riskUsd: 150, maxQty: null, minStopTicks: 4, maxPerSession: 3, maxLossesPerSession: 2, dailyStopUsd: 400, cooldown: 0 }, 'risque par défaut de §3.0');
  eq(D.costs, { commissionRT: null, slipTicks: 1 }, 'coûts par défaut : commission du réglage, 1 tick');
  eq(n.spec.long.entry, { type: 'market' }, 'entrée au marché par défaut');
  eq(n.spec.long.setup, [], 'contexte vide par défaut');
  LS.describe(n.spec); LS.hash(n.spec, 1.24); LS.configHash(n.spec);
  ok(reads === 0, 'normalize, describe et les hachages ne lisent jamais T.settings (' + reads + ' lectures)');
  if (T.settings) T.settings.get = g0;
  const s2 = norm({ long: { trigger: { bar: 'up' }, stop: { type: 'pts', value: 5 } }, session: { to: '08:00' } }).spec;
  ok(s2.session.flat === '08:00', 'flat absent = fin de fenêtre');
}

/* ---------------------------------------------------------------------------------------------- */
section('Chaque opérande : normalise, se lit, se reflète, et sa classe est celle du moteur');
{
  const condFor = (x, cls) => cls === 'niveau' ? { cmp: '>', a: { f: 'close' }, b: x } : cls === 'oscillateur' ? { cmp: '>', a: x, b: 70 } : { cmp: '>', a: x, b: 1 };
  G.operands.filter(o => o.form !== 'const').forEach(g => {
    const x = g.form === 'op' ? build(g.args, {}) : build(g.args, { f: g.f });
    const tag = g.f + ' ' + C(x);
    let cls; try { cls = LS.classOf(x); } catch (e) { cls = 'ERR ' + e.message; }
    const decl = g.cls === 'of' ? LS.classOf(x.of == null ? { f: g.f === 'hh' ? 'high' : g.f === 'll' ? 'low' : 'close' } : x.of) : g.cls === 'calcule' ? 'niveau' : g.cls;
    ok(cls === decl, tag + ' : classe ' + cls + ' = classe déclarée ' + decl);
    /* La classe confrontée au moteur : le miroir d’une comparaison à la constante 5 la révèle. */
    let m = null, me = null; try { m = LS.mirror({ cmp: '>', a: x, b: 5 }, 'cond'); } catch (e) { me = e.message; }
    if (cls === 'niveau') ok(me && /Miroir impossible/.test(me), tag + ' : niveau contre constante refusé par le moteur');
    else if (cls === 'ecart') ok(m && m.cmp === '<' && m.b === -5, tag + ' : écart contre constante → −x');
    else if (cls === 'oscillateur') ok(m && m.cmp === '<' && m.b === 95, tag + ' : oscillateur contre constante → 100 − x');
    else ok(m && C(m) === C({ cmp: '>', a: x, b: 5 }), tag + ' : neutre inchangé');
    const c = condFor(x, cls), s = spec({ trigger: c, setup: [c] });
    const n = norm(s, NOLVL);
    ok(n.errors.length === 0, tag + ' : normalise sans erreur ' + n.errors.join(' | '));
    readingOk(LS.describe(s), tag, { seller: true });
    const m1 = LS.mirror(c, 'cond'), m2 = LE.op('mirror', { cond: c });
    eq(m1, m2, tag + ' : enveloppe mirror = op du moteur');
    eq(normCond(LS.mirror(m1, 'cond')), normCond(c), tag + ' : le miroir du miroir rend la condition');
    eq(norm(n.spec).spec, n.spec, tag + ' : normalize idempotent');
  });
  /* La constante : un nombre ou "$nom". */
  const s = spec({ trigger: { cmp: '>', a: { f: 'rsi', n: 14 }, b: '$seuil' } }, { params: { seuil: { v: 30 } } });
  const n = norm(s); ok(n.errors.length === 0 && LS.classOf('$seuil') === 'constante' && LS.classOf(3) === 'constante', 'constante "$nom" et nombre');
  readingOk(LS.describe(s), 'constante', { seller: true });
}

/* ---------------------------------------------------------------------------------------------- */
section('Chaque condition : normalise, se lit, se reflète');
{
  G.conditions.forEach(g => {
    const c = build(g.args, {});
    const tag = g.key + ' ' + C(c);
    const s = spec({ trigger: c, setup: [c] });
    const n = norm(s);
    ok(n.errors.length === 0, tag + ' : normalise sans erreur ' + n.errors.join(' | '));
    readingOk(LS.describe(s), tag, { seller: true });
    const m1 = LS.mirror(c, 'cond');
    eq(m1, LE.op('mirror', { cond: c }), tag + ' : enveloppe = op');
    eq(normCond(LS.mirror(m1, 'cond')), normCond(c), tag + ' : involution');
  });
  const rd = c => LS.describe(spec({ trigger: c })).filter(x => x.id === 'declencheur')[0].text;
  ok(/une publication d’impact 3 ou plus tombe entre 15\smin avant/.test(rd({ not: { news: { impact: 3, before: 15, after: 5 } } })), 'négation d’une publication : lue sans double négation');
  ok(/la barre n’est pas haussière/.test(rd({ not: { bar: 'up' } })) && /la condition «\s.*\s» est fausse/.test(rd({ not: { cmp: '>', a: { f: 'close' }, b: { f: 'vwap' } } })), 'négations lues');
  ok(/sur 1 barre\b/.test(rd({ cmp: '>', a: { f: 'close' }, b: { f: 'sma', n: 1 } })) && /2 ticks/.test(LS.describe(spec({ stop: { type: 'pts', value: 5, buffer: '$b' } }, { params: { b: { v: 2 } } })).filter(x => x.id === 'stop')[0].text), 'accord des unités sur la valeur, paramètre compris');
  eq(LS.mirror({ cross: 'up', a: { f: 'close' }, b: { f: 'vwap' } }, 'cond'), { cross: 'down', a: { f: 'close' }, b: { f: 'vwap', k: 0 } }, 'cross up ↔ down');
  eq(LS.mirror({ touch: { f: 'prev', of: 'high', n: 1 }, from: 'above' }, 'cond'), { touch: { f: 'prev', of: 'low', n: 1 }, from: 'below' }, 'touch above ↔ below, high ↔ low');
}

/* ---------------------------------------------------------------------------------------------- */
section('Entrées, stops, objectifs, gestion : normalisent, se lisent, se reflètent');
{
  const rules = [];
  G.entries.forEach(g => rules.push(['entrée ' + g.type, { entry: build(g.args, { type: g.type }) }]));
  G.stops.forEach(g => rules.push(['stop ' + g.type, { stop: build(g.args, { type: g.type }) }]));
  G.targets.forEach(g => rules.push(['objectif ' + g.type, { target: build(g.args, { type: g.type }) }]));
  rules.push(['entrée limite jusqu’à une heure', { entry: { type: 'limit', at: { f: 'vwap', k: -1 }, offset: 2, valid: '08:30', through: true, tz: 'Europe/Paris' } }]);
  rules.push(['entrée stop paramétrée', { entry: { type: 'stop', at: { f: 'hh', n: 10 }, offset: '$o', valid: '$v' } }]);
  rules.push(['stop au niveau avec marge', { stop: { type: 'level', at: { f: 'sess', of: 'low' }, buffer: 3 } }]);
  rules.forEach(([tag, r]) => {
    const s = spec(r, { params: { o: { v: 2 }, v: { v: 3 } } });
    const n = norm(s);
    const usedP = C(r).indexOf('$') >= 0;
    ok(n.errors.length === 0, tag + ' : normalise sans erreur ' + n.errors.join(' | '));
    readingOk(LS.describe(s), tag, { seller: true });
    const rule = LS.resolve(n.spec, {}).long;
    eq(LS.mirror(rule, 'rule'), LE.op('mirror', { rule: rule }), tag + ' : enveloppe = op');
    if (!usedP) eq(norm(spec(LS.mirror(LS.mirror(rule, 'rule'), 'rule'))).spec.long, n.spec.long, tag + ' : involution');
  });
  const lim = norm(spec({ entry: { type: 'limit', at: { f: 'vwap' } } })).spec.long.entry;
  eq(lim, { type: 'limit', at: { f: 'vwap' }, valid: 1, through: false }, 'limite : valid 1 et through false écrits, offset 0 omis');
  const mg = [
    ['break-even en nombre', { breakeven: 1 }, { breakeven: { r: 1 }, trail: null, maxBars: null, exitOnOpposite: false }],
    ['break-even {r, offset} paramétré', { breakeven: { r: '$be', offset: 2 } }, null],
    ['suiveur en points', { trail: { type: 'pts', value: 8 } }, { breakeven: null, trail: { type: 'pts', value: 8, start: 0 }, maxBars: null, exitOnOpposite: false }],
    ['suiveur en ATR', { trail: { type: 'atr', value: 2, n: 20, start: 1 } }, null],
    ['suiveur en R (dist)', { trail: { type: 'r', dist: 1.5 } }, null],
    ['sortie au temps et signal opposé', { maxBars: 30, exitOnOpposite: true }, null]
  ];
  mg.forEach(([tag, m, want]) => {
    const s = spec({}, { manage: m, params: { be: { v: 1.5 } } });
    const n = norm(s);
    ok(n.errors.length === 0, tag + ' : normalise ' + n.errors.join(' | '));
    if (want) eq(n.spec.manage, want, tag + ' : forme normalisée');
    readingOk(LS.describe(s), tag, { seller: true });
    eq(LS.mirror(s, 'spec'), LE.op('mirror', { spec: s }), tag + ' : miroir de la spec, enveloppe = op');
  });
  ok(norm(spec({}, { manage: { trail: { type: 'r', dist: 1.5 } } })).spec.manage.trail.value === 1.5, 'trail.dist lu comme value');
  /* Ancrages et séances. */
  [['paris', { anchor: 'paris', session: { from: '01:00', to: '09:00' } }], ['rth', { anchor: 'rth', session: { tz: 'America/New_York', from: '09:45', to: '11:30', flat: '15:50' } }],
    ['jours', { session: { days: [1, 3, 5] } }], ['un jour', { session: { days: [2] } }], ['taille au risque', { risk: { mode: 'risk', riskUsd: 200, maxQty: 3, cooldown: 3 } }],
    ['sans limites', { risk: { maxPerSession: null, maxLossesPerSession: null, dailyStopUsd: null } }], ['commission et glissement', { costs: { commissionRT: 1.24, slipTicks: 2 } }],
    ['remplissage optimiste', { fill: 'optimiste' }], ['remplissage chemin', { fill: 'chemin' }], ['vente seule en miroir', { side: 'short' }], ['achat seul', { side: 'long' }],
    ['vente écrite', { side: 'both', mirror: false, short: { trigger: { bar: 'down' }, stop: { type: 'pts', value: 4 }, target: { type: 'pts', value: 8 } } }]
  ].forEach(([tag, top]) => {
    const s = spec({}, top), n = norm(s);
    ok(n.errors.length === 0, tag + ' : normalise ' + n.errors.join(' | '));
    readingOk(LS.describe(s), tag, { seller: (top.side || 'both') !== 'long' });
    eq(norm(n.spec).spec, n.spec, tag + ' : idempotent');
  });
  const d = LS.describe(spec({}, { costs: { slipTicks: 1 } }), { slipTicksRT: 1.37 });
  ok(/2 ticks/.test(d.filter(x => x.id === 'couts')[0].text) && /1,37\stick/.test(d.filter(x => x.id === 'couts')[0].text), 'coûts : convention par jambe, équivalent aller-retour et coût réalisé moyen');
  const sh = LS.describe(spec({ setup: [{ cmp: '>', a: { f: 'close' }, b: { f: 'vwap', k: 1 } }] }, { side: 'short' }));
  const v = sh.filter(x => x.id === 'vendeur')[0].text;
  ok(/au-dessous de la bande VWAP à −1/.test(v), 'côté vendeur reflété : « ' + v + ' »');
  ok(/\d h \d\d/.test(LS.describe(spec()).filter(x => x.id === 'seance')[0].text), 'heures « 09 h 00 » à espaces insécables');
  [null, {}, 'pas du JSON', { side: 'short', mirror: false }, { long: { trigger: { zzz: 1 } } }].forEach((x, i) => {
    let rows = null; try { rows = LS.describe(x); } catch (e) { rows = null; }
    ok(Array.isArray(rows) && rows.length && rows.every(r => r.text && !/undefined|NaN/.test(r.text)), 'lecture d’un document défectueux n° ' + i + ' sans undefined ni NaN');
  });
}

/* ---------------------------------------------------------------------------------------------- */
section('Validations de normalize');
{
  let n = norm(spec({ trigger: { cmp: '>', a: { f: 'close' }, b: { f: 'sma', n: '$len' } } }));
  ok(hasErr(n, /long\.trigger\.b\.n.*\$len.*non déclaré/), '$nom sans paramètre → erreur nommée');
  n = norm(spec({}, { params: { inutile: { v: 3 } } }));
  ok(n.errors.length === 0 && hasWarn(n, /params\.inutile.*jamais utilisé/), 'paramètre inutilisé → avertissement');
  n = norm(spec({ stop: { type: 'pts', value: '$s' } }, { params: { s: { v: -2 } } }));
  ok(hasErr(n, /paramètre « s » = −2/), 'valeur de paramètre hors de ce qu’accepte l’argument');
  n = norm(spec({}, { side: 'both', mirror: false }));
  ok(hasErr(n, /^short : obligatoire/), 'mirror false et vente jouée sans short → erreur');
  n = norm(spec({}, { side: 'short', mirror: false, long: null, short: { trigger: { bar: 'down' }, stop: { type: 'pts', value: 4 } } }));
  ok(n.errors.length === 0, 'vente seule écrite côté vendeur : valide ' + n.errors.join(' | '));
  const rs = LS.describe(n.spec); readingOk(rs, 'vente seule écrite');
  ok(/^Vente au marché/.test(rs.filter(x => x.id === 'entree')[0].text) && /au-dessus de l’entrée|sous l’entrée/.test(rs.filter(x => x.id === 'stop')[0].text + rs.filter(x => x.id === 'objectif')[0].text) && !rs.some(x => x.id === 'vendeur'), 'vente seule écrite : blocs lus côté vendeur');
  /* Miroir : niveau contre constante. */
  n = norm(spec({ trigger: { cmp: '>', a: { f: 'close' }, b: 20000 } }));
  ok(hasErr(n, /^long\.trigger : Miroir impossible/), 'niveau contre constante, vente jouée → erreur');
  n = norm(spec({ setup: [{ cmp: '>', a: { f: 'close' }, b: '$p' }] }, { params: { p: { v: 20000 } } }));
  ok(hasErr(n, /^long\.setup\[0\] : Miroir impossible/), 'niveau contre "$p" (constante) → erreur');
  n = norm(spec({ trigger: { cmp: '>', a: { f: 'close' }, b: 20000 } }, { side: 'long' }));
  ok(n.errors.length === 0 && hasWarn(n, /Miroir impossible.*sans effet/), 'achat seul : simple avertissement');
  n = norm(spec({ trigger: { cmp: '>', a: { f: 'close' }, b: 20000 } }, { side: 'long', manage: { exitOnOpposite: true } }));
  ok(hasErr(n, /Miroir impossible/), 'achat seul avec sortie sur signal opposé : le miroir est lu → erreur');
  n = norm(spec({ trigger: { cmp: '>', a: { f: 'dist', a: { f: 'close' }, b: { f: 'vwap' }, unit: 'sd' }, b: { f: 'range' } } }));
  ok(hasErr(n, /Miroir impossible/), 'écart contre neutre → erreur');
  n = norm(spec({ trigger: { cmp: '>', a: { f: 'body' }, b: '$p' } }, { params: { p: { v: 2 } } }));
  ok(n.errors.length === 0, 'écart contre "$p" : reflété');
  /* Heures et ancre. */
  n = norm(spec({}, { session: { tz: 'Europe/Paris', from: '23:00', to: '02:00' } }));
  ok(hasErr(n, /^session : .*chevauche l’ancre globex/), 'fenêtre 23:00–02:00 Paris à cheval sur l’ancre Globex → erreur');
  n = norm(spec({}, { session: { tz: 'America/New_York', from: '20:00', to: '02:00', flat: '03:00' } }));
  ok(n.errors.length === 0, 'fenêtre 20:00–02:00 New York, flat 03:00 : valide ' + n.errors.join(' | '));
  n = norm(spec({}, { session: { tz: 'Europe/Paris', from: '08:00', to: '09:00', flat: '07:00' } }));
  ok(hasErr(n, /chevauche l’ancre/), 'flat avant le début → erreur');
  n = norm(spec({}, { anchor: 'paris', session: { tz: 'Europe/Paris', from: '23:00', to: '01:00' } }));
  ok(hasErr(n, /chevauche l’ancre paris/), 'ancre paris : fenêtre 23:00–01:00 → erreur');
  n = norm(spec({}, { session: { from: '05:00', to: '05:00' } }));
  ok(hasErr(n, /fenêtre vide/), 'fenêtre vide → erreur');
  n = norm(spec({}, { anchor: 'rth', session: { tz: 'America/New_York', from: '09:00', to: '11:00' } }));
  ok(hasErr(n, /rth.*09 h 30–16 h 00/), 'rth : fenêtre qui commence avant 09:30 → erreur');
  n = norm(spec({}, { anchor: 'rth', session: { tz: 'America/New_York', from: '10:00', to: '16:30' } }));
  ok(hasErr(n, /rth/), 'rth : fenêtre qui finit après 16:00 → erreur');
  n = norm(spec({}, { anchor: 'rth', session: { tz: 'Europe/Paris', from: '15:45', to: '17:00', flat: '21:30' } }));
  ok(hasErr(n, /toutes les semaines/), 'rth en heure de Paris : sortie forcée hors séance les semaines de décalage → erreur');
  n = norm(spec({}, { anchor: 'rth', session: { tz: 'America/New_York', from: '09:45', to: '11:30', flat: '15:50' } }));
  ok(n.errors.length === 0, 'rth 09:45–11:30 New York : valide');
  n = norm(spec({ trigger: { break: { f: 'or', from: '23:30', to: '00:30' }, dir: 'up' } }));
  ok(n.errors.length + n.warnings.length > 0 && (hasErr(n, /range/) || hasWarn(n, /range/)), 'range d’ouverture à cheval sur l’ancre signalé');
  n = norm(spec({}, { session: { tz: 'Mars/Olympus' } }));
  ok(hasErr(n, /fuseau inconnu/), 'fuseau inconnu → erreur');
  /* Niveaux nommés (§2.2). */
  const lv = spec({ trigger: { reject: { f: 'level', name: 'HVL' }, from: 'above' } });
  n = norm(lv); ok(n.errors.length === 0 && hasWarn(n, /raccord des contrats/), 'niveau sans jeu : avertissement, vérifié au lancement');
  n = norm(lv, { dataset: { name: 'MNQ', roll: 'inconnu' } }); ok(hasErr(n, /^long\.trigger\.reject : .*roll inconnu/), 'jeu roll inconnu → erreur');
  n = norm(lv, { dataset: { name: 'MNQ' } }); ok(hasErr(n, /roll absent/), 'jeu sans roll → erreur');
  n = norm(lv, { dataset: { meta: { roll: 'ajuste' }, adj: {} } }); ok(hasErr(n, /ajusté mais ne porte pas/), 'jeu ajusté sans adj → erreur');
  n = norm(lv, { dataset: { meta: { roll: 'ajuste' }, adj: { '2026-03-16': 12.5 } } }); ok(n.errors.length === 0, 'jeu ajusté avec adj : valide');
  n = norm(lv, { meta: { roll: 'non-ajuste' } }); ok(n.errors.length === 0, 'jeu non ajusté : valide');
  n = norm(lv, { dataset: { meta: { roll: 'non-ajuste' }, levels: { '2026-01-05': { levels: { HVL: 21000 }, scale: 'NDX' } } } }); ok(hasErr(n, /NDX sans base/), 'niveaux NDX sans base → erreur');
  n = norm(lv, { dataset: { meta: { roll: 'non-ajuste' }, levels: { '2026-01-05': { levels: { HVL: 21000 }, scale: 'NDX', base: 180 } } } }); ok(n.errors.length === 0, 'niveaux NDX avec base : valides');
  n = norm(spec({ target: { type: 'level', at: { f: 'nearest', side: 'above', names: ['CR', 'GW'] } } }), { dataset: { roll: 'inconnu' } }); ok(hasErr(n, /^long\.target\.at/), 'nearest dans l’objectif : même contrôle');
  n = norm(lv, { dataset: { roll: 'non-ajuste', source: 'synthetique' } }); ok(hasWarn(n, /marche synthétique/), 'marche synthétique : avertissement');
  /* Formes refusées. */
  const bad = [
    ['opérande inconnu', spec({ trigger: { cmp: '>', a: { f: 'zz' }, b: 1 } }), /opérande inconnu « zz »/],
    ['deux formes dans une condition', spec({ trigger: { bar: 'up', cmp: '>', a: 1, b: 2 } }), /une seule forme/],
    ['condition inconnue', spec({ trigger: { foo: 1 } }), /condition inconnue/],
    ['niveau × nombre', spec({ trigger: { cmp: '>', a: { op: '*', a: { f: 'close' }, b: 2 }, b: { f: 'vwap' } } }), /Niveau × nombre refusé/],
    ['niveau + niveau', spec({ trigger: { cmp: '>', a: { op: '+', a: { f: 'close' }, b: { f: 'open' } }, b: { f: 'vwap' } } }), /Niveau \+ niveau refusé/],
    ['niveau attendu', spec({ trigger: { touch: { f: 'rsi', n: 14 }, from: 'above' } }), /un niveau \(un prix\) est attendu/],
    ['enum', spec({ trigger: { bar: 'side' } }), /valeur « side » inconnue/],
    ['heure', spec({ trigger: { time: ['25:00', '10:00'] } }), /deux heures/],
    ['entier', spec({ trigger: { cmp: '>', a: { f: 'sma', n: 2.5 }, b: { f: 'vwap' } } }), /entier/],
    ['stop non positif', spec({ stop: { type: 'pts', value: 0 } }), /strictement supérieur à 0/],
    ['type de stop', spec({ stop: { type: 'pourcent', value: 1 } }), /type « pourcent » inconnu/],
    ['remplissage vrai', spec({}, { fill: 'vrai' }), /réservé aux marches synthétiques/],
    ['sid', spec({}, { sid: 'S_1' }), /^sid : identifiant invalide/],
    ['id incohérent', spec({}, { id: 'stest0001_v2', version: 1 }), /^id : doit valoir/],
    ['scellée sans hachage', spec({}, { status: 'scellee', sealedAt: 1 }), /^hash/],
    ['news', spec({ trigger: { news: true } }), /news : un objet/],
    ['liste vide', spec({ trigger: { all: [] } }), /liste non vide/],
    ['déclencheur absent', spec({ trigger: undefined }), /déclencheur requis/],
    ['stop absent', spec({ stop: undefined }), /stop requis/],
    ['instrument', spec({}, { instrument: 'ES' }), /MNQ ou NQ/]
  ];
  bad.forEach(([tag, s, re]) => { let r; try { r = norm(s); } catch (e) { r = { errors: ['LEVÉE ' + e.message], warnings: [] }; } ok(hasErr(r, re), tag + ' → ' + r.errors.join(' | ')); });
  ['pas du JSON', null, [], 5].forEach(x => { const r = norm(x); ok(r.spec === null && r.errors.length === 1, 'entrée illisible ' + C(x) + ' → une erreur, aucune exception'); });
  n = norm(spec({}, { zz: 1 })); ok(hasWarn(n, /^zz : clé inconnue/) && n.spec.zz === 1, 'clé inconnue gardée et signalée');
  n = norm(Object.assign(spec(), { sid: undefined }), { strict: true }); ok(hasErr(n, /^sid/), 'mode strict : identité exigée');
  ok(norm(JSON.stringify(spec())).errors.length === 0, 'normalize accepte le texte JSON');
}

/* ---------------------------------------------------------------------------------------------- */
section('Enveloppes : resolve, mirror, stats = op du moteur');
{
  const s = norm(spec({ trigger: { cross: 'up', a: { f: 'rsi', n: '$n' }, b: '$seuil' }, stop: { type: 'atr', value: '$m' } }, { params: { n: { v: 14 }, seuil: { v: 30 }, m: { v: 1.5 } } })).spec;
  eq(LS.resolve(s, { seuil: 25 }), LE.op('resolve', { spec: s, values: { seuil: 25 } }), 'resolve = op');
  ok(LS.resolve(s, { seuil: 25 }).long.trigger.b === 25 && LS.resolve(s, {}).long.trigger.b === 30, 'resolve : valeur imposée puis valeur du paramètre');
  eq(LS.mirror(s, 'spec'), LE.op('mirror', { spec: s }), 'mirror (spec) = op');
  eq(LS.mirror(s, 'spec', { seuil: 20 }), LE.op('mirror', { spec: s, values: { seuil: 20 } }), 'mirror (spec, valeurs) = op');
  eq(LS.mirror({ f: 'vwap', k: 2 }, 'operand'), LE.op('mirror', { operand: { f: 'vwap', k: 2 } }), 'mirror (opérande) = op');
  throws(() => LS.mirror({ cmp: '>', a: { f: 'close' }, b: '$p' }, 'cond'), /Miroir avant résolution/, 'mirror refuse un "$nom" non résolu');
  const lat = LE.lattice({ sessions: 6, seed: 7 });
  const run = LE.run({ bars: lat, spec: norm(spec({ trigger: { bar: 'up' }, stop: { type: 'pts', value: 3 }, target: { type: 'r', value: 1 } }, { risk: { maxPerSession: 20, maxLossesPerSession: null, dailyStopUsd: null } })).spec, values: {}, settings: { tick: 0.25, pointValue: 2, commissionRT: 1.24 } });
  ok(run.trades.length > 20, 'run sur la marche au tick : ' + run.trades.length + ' trades');
  eq(LS.stats(run.trades, 2), LE.op('stats', { trades: run.trades, settings: { pointValue: 2 } }), 'stats = op');
  eq(LS.stats(run.trades, 2), run.stats, 'stats = statistiques du run');
}

/* ---------------------------------------------------------------------------------------------- */
section('Hachage : FNV-1a 64 bits exact sur l’UTF-8 du JSON canonique');
{
  const ref = str => { let h = 0xcbf29ce484222325n; for (const b of Buffer.from(str, 'utf8')) { h ^= BigInt(b); h = (h * 0x100000001b3n) & 0xffffffffffffffffn; } return h.toString(16).padStart(16, '0'); };
  ok(LS.fnv64('') === 'cbf29ce484222325' && LS.fnv64('a') === 'af63dc4c8601ec8c' && LS.fnv64('foobar') === '85944171f73967e8', 'vecteurs de référence FNV-1a 64');
  const strs = ['é', 'Résistance €', '日本語', '😀 émoji', 'a\uD800b', 'z\uDC00', ' h ', '{"a":1}'];
  const r = mulberry(11);
  for (let i = 0; i < 150; i++) { let s = ''; const L = Math.floor(r() * 30); for (let k = 0; k < L; k++) { const z = r(); s += String.fromCharCode(z < 0.5 ? 32 + Math.floor(r() * 95) : z < 0.8 ? 0xa0 + Math.floor(r() * 0x700) : z < 0.95 ? 0x800 + Math.floor(r() * 0xd000) : 0xd800 + Math.floor(r() * 0x800)); } strs.push(s); }
  let okB = 0, okL = 0, okU = 0;
  strs.forEach(s => { const x = ref(s); if (LS.fnv64(s, 'bigint') === x) okB++; if (LS.fnv64(s, 'limbs') === x) okL++; if (C(LS.utf8(s)) === C(Array.from(Buffer.from(s, 'utf8')))) okU++; });
  ok(okB === strs.length, 'BigInt = référence sur ' + okB + '/' + strs.length + ' chaînes (accents, émoji, demi-paires)');
  ok(okL === strs.length, 'quatre membres de 16 bits = référence sur ' + okL + '/' + strs.length);
  ok(okU === strs.length, 'UTF-8 = Buffer de node sur ' + okU + '/' + strs.length);
  ok(C({ b: 1, a: [-0, null, 'é', true, undefined], c: undefined, d: { y: 2, x: 1.5 } }) === '{"a":[0,null,"é",true,null],"b":1,"d":{"x":1.5,"y":2}}', 'JSON canonique : clés triées, −0 → 0, undefined omis, null gardé, sans espace');
  ok(C({ 'é': 1, z: 2, A: 3, a: 4 }) === '{"A":3,"a":4,"z":2,"é":1}', 'clés triées par unité de code');
  ok(C(1e21) === '1e+21' && C(0.1 + 0.2) === '0.30000000000000004', 'nombres par String(x)');
  const base = spec({ setup: [{ cmp: '>', a: { f: 'close' }, b: { f: 'vwap', k: '$k' } }], trigger: { reject: { f: 'level', name: 'Résistance' }, from: 'above' }, stop: { type: 'pts', value: '$s' } }, { params: { k: { v: 1, label: 'bande' }, s: { v: 5 } }, costs: { commissionRT: null, slipTicks: 1 } });
  const h0 = LS.hash(base, 1.24), c0 = LS.configHash(base);
  ok(/^h[0-9a-f]{16}$/.test(h0) && /^h[0-9a-f]{16}$/.test(c0) && h0 !== c0, 'format h + 16 hex : ' + h0 + ' ' + c0);
  const pl = LS.hashPayload(base, { commissionRT: 1.24 });
  ok(h0 === 'h' + ref(pl), 'hash = FNV de l’UTF-8 du JSON canonique (accent du nom de niveau compris)');
  ok(pl.indexOf('$') < 0 && pl.indexOf('params') < 0 && pl.indexOf('"hypothesis"') < 0 && pl.indexOf('"sid"') < 0 && pl.indexOf('Résistance') > 0, 'charge : résolue, sans params ni identité');
  ok(c0 === 'h' + ref(LS.hashPayload(base, { kind: 'config' })), 'configHash = FNV de sa charge');
  /* Ordre des clés, profondément mélangé. */
  const shuffle = (x, rnd) => { if (Array.isArray(x)) return x.map(y => shuffle(y, rnd)); if (!x || typeof x !== 'object') return x; const ks = Object.keys(x); for (let i = ks.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [ks[i], ks[j]] = [ks[j], ks[i]]; } const o = {}; ks.forEach(k => { o[k] = shuffle(x[k], rnd); }); return o; };
  let same = 0; for (let i = 0; i < 20; i++) { const s = shuffle(base, mulberry(100 + i)); if (LS.hash(s, 1.24) === h0 && LS.configHash(s) === c0) same++; }
  ok(same === 20, 'ordre des clés sans effet (20 mélanges)');
  /* −0 */
  const z = clone(base); z.risk = { cooldown: -0 }; z.long.entry = { type: 'limit', at: { f: 'vwap' }, offset: -0 };
  const z2 = clone(base); z2.risk = { cooldown: 0 }; z2.long.entry = { type: 'limit', at: { f: 'vwap' } };
  ok(LS.hash(z, 1.24) === LS.hash(z2, 1.24), '−0 et 0 : même hachage');
  const zp = clone(base); zp.params.k.v = -0; const zq = clone(base); zq.params.k.v = 0;
  ok(LS.hash(zp, 1.24) === LS.hash(zq, 1.24), '−0 dans un paramètre résolu : même hachage');
  /* Normalisée puis résolue : un paramètre vaut sa valeur. */
  const lit = clone(base); lit.long.setup[0].b.k = 1; lit.long.stop.value = 5; lit.params = {};
  ok(LS.hash(lit, 1.24) === h0 && LS.configHash(lit) === c0, 'paramètre résolu = valeur écrite en clair');
  const lab = clone(base); lab.params.k.label = 'autre'; lab.params.k.min = 0; lab.params.k.max = 3; lab.params.k.step = 0.5;
  ok(LS.hash(lab, 1.24) === h0, 'libellé et bornes d’un paramètre sans effet');
  const v2 = clone(base); v2.params.s.v = 6;
  ok(LS.hash(v2, 1.24) !== h0 && LS.configHash(v2) !== c0, 'valeur d’un paramètre : change les deux hachages');
  ok(LS.configHash(base, { s: 6 }) === LS.configHash(v2) && LS.hash(base, 1.24, { s: 6 }) === LS.hash(v2, 1.24), 'valeurs imposées (balayage) = paramètre réécrit');
  const def = clone(base); def.long.trigger.reject.name = 'Resistance';
  ok(LS.hash(def, 1.24) !== h0, 'un accent compte');
  const id = clone(base); id.name = 'Autre nom'; id.hypothesis = 'Autre'; id.sid = 'sautre0001'; id.status = 'brouillon'; id.u = 5; id.createdAt = 9; delete id.id;
  ok(LS.hash(id, 1.24) === h0 && LS.configHash(id) === c0, 'identité, nom et hypothèse hors du hachage');
  const lagd = clone(lit); lagd.long.setup[0].a = { f: 'close', lag: 0 };
  ok(LS.hash(lagd, 1.24) === h0, 'défaut écrit (lag 0) = défaut omis');
  /* Coûts : dans le hachage scellé (commission figée), hors du configHash. */
  const dc = clone(base); dc.costs.commissionRT = 1.24;
  ok(LS.hash(dc) === h0 && LS.hash(dc, 9) === h0, 'commission déclarée = commission du réglage figée au scellement');
  ok(LS.hash(base, 1.5) !== h0 && LS.hash(base) !== h0, 'une autre commission change le hachage scellé');
  const vary = [['glissement', s => { s.costs.slipTicks = 3; }], ['commission', s => { s.costs.commissionRT = 4; }], ['remplissage', s => { s.fill = 'optimiste'; }],
    ['contrats', s => { s.risk = { contracts: 5 }; }], ['risque en $', s => { s.risk = { riskUsd: 900 }; }], ['plafond', s => { s.risk = { maxQty: 7 }; }]];
  vary.forEach(([tag, f]) => { const s = clone(base); f(s); ok(LS.configHash(s) === c0, 'configHash insensible : ' + tag); ok(LS.hash(s, 1.24) !== h0, 'hachage scellé sensible : ' + tag); });
  const sens = [['stop minimal', s => { s.risk = { minStopTicks: 8 }; }], ['mode de taille', s => { s.risk = { mode: 'risk' }; }], ['fenêtre', s => { s.session = { from: '01:00' }; }],
    ['ancre', s => { s.anchor = 'paris'; }], ['sens', s => { s.side = 'long'; }], ['déclencheur', s => { s.long.trigger.from = 'below'; }], ['gestion', s => { s.manage = { maxBars: 10 }; }], ['cooldown', s => { s.risk = { cooldown: 2 }; }]];
  sens.forEach(([tag, f]) => { const s = clone(base); f(s); ok(LS.configHash(s) !== c0 && LS.hash(s, 1.24) !== h0, 'les deux hachages sensibles : ' + tag); });
  throws(() => LS.hash(spec({ trigger: { cmp: '>', a: { f: 'zz' }, b: 1 } })), /Hachage impossible/, 'spec en erreur : pas de hachage');
  /* Scellement. */
  const sealed = LS.seal(base, 1.24, 1767225600000);
  ok(sealed.status === 'scellee' && sealed.sealedAt === 1767225600000 && sealed.costs.commissionRT === 1.24 && sealed.hash === h0, 'seal : commission figée, hachage = hash(spec, commission)');
  ok(LS.verifySeal(sealed).ok === true, 'verifySeal : intacte');
  const alt = clone(sealed); alt.long.stop.value = 6; alt.params = clone(base.params);
  ok(LS.verifySeal(alt).ok === false, 'verifySeal : règle modifiée → altérée');
  const alt2 = clone(sealed); alt2.costs.commissionRT = 0.5;
  ok(LS.verifySeal(alt2).ok === false, 'verifySeal : commission modifiée → altérée');
  throws(() => LS.seal(Object.assign(clone(base), { hypothesis: ' ' }), 1.24), /hypothèse/, 'seal exige l’hypothèse');
  throws(() => LS.seal(base), /commission/, 'seal exige la commission du réglage quand la stratégie n’en déclare pas');
}

/* ---------------------------------------------------------------------------------------------- */
section('Sharpe déflaté : T.lib.quant.dsr, T.lib.perf, et sa loi nulle');
{
  const cases = [{ sr: 0.12, n: 700, N: 25, skew: -0.3, exkurt: 2.5 }, { sr: 0.05, n: 300, N: 1, skew: 0, exkurt: 0 }, { sr: 0.2, n: 120, N: 400, skew: 0.4, exkurt: 6 }];
  cases.forEach(c => {
    const a = LS.dsr(c), q = Q.dsr(c.sr, c.n, c.N, c.skew, c.exkurt), p = P.dsr(c.sr, c.n, c.N, c.skew, c.exkurt);
    ok(a.dsr === q.dsr && a.sr0 === q.sr0, 'dsr = T.lib.quant.dsr ' + C(c));
    near(a.dsr, p.dsr, 1e-12, 'dsr = T.lib.perf.dsr (1/√n par défaut) ' + C(c));
    ok(a.sdSource === 'defaut' && Math.abs(a.sdTrials - 1 / Math.sqrt(c.n)) < 1e-15, 'sdTrials par défaut 1/√n');
    const b = LS.dsr(Object.assign({ sdTrials: 0.03 }, c)), q2 = Q.dsr(c.sr, c.n, c.N, c.skew, c.exkurt, 0.03);
    ok(b.dsr === q2.dsr && b.sdSource === 'registre', 'dsr avec sdTrials du registre = T.lib.quant.dsr');
  });
  ok(LS.dsr({ sr: 0.1, n: 619, N: 50 }).dsr < LS.dsr({ sr: 0.1, n: 619, N: 1 }).dsr, 'plus d’essais, Sharpe plus déflaté');
  /* Loi nulle : sans avantage et N = 1, la probabilité que le DSR dépasse 0,95 vaut 5 %. */
  const r = mulberry(5); let hit = 0; const M = 2000, n = 150;
  for (let k = 0; k < M; k++) { const xs = []; for (let i = 0; i < n; i++) xs.push(gauss(r)); const sr = mean(xs) / sdv(xs); if (LS.dsr({ sr, n, N: 1, skew: 0, exkurt: 0 }).dsr >= 0.95) hit++; }
  near(hit / M, 0.05, 0.015, 'loi nulle : DSR ≥ 0,95 dans 5 % des séries sans avantage');
}

/* ---------------------------------------------------------------------------------------------- */
section('Registre des essais : N, sdTrials, hérités');
{
  const rows = [
    { id: 'e1', sid: 'saaaaaa1', root: 'saaaaaa1', version: 1, instrument: 'MNQ', fingerprint: 'fpA', from: '2025-01-02', to: '2025-06-30', op: 'run', hashes: ['h1', 'h2'], sr: [0.1, 0.2], at: 1000 },
    { id: 'e2', sid: 'sbbbbbb2', root: 'sbbbbbb2', version: 1, instrument: 'MNQ', fingerprint: 'fpA', from: '2025-01-02', to: '2025-06-30', op: 'run', hashes: ['h3'], sr: [0.05], at: 1000 },
    { id: 'e3', sid: 'scccccc3', root: 'saaaaaa1', version: 1, instrument: 'MNQ', fingerprint: 'fpA', from: '2025-02-01', to: '2025-05-30', op: 'sweep', hashes: ['h1', 'h4'], sr: [0.1, -0.1], at: 3000 },
    { id: 'e4', sid: 'saaaaaa1', root: 'saaaaaa1', version: 2, instrument: 'MNQ', fingerprint: 'fpB', from: '2025-03-01', to: '2025-08-30', op: 'run', hashes: ['h5'], sr: [0.3], at: 4000 },
    { id: 'e5', sid: 'saaaaaa1', root: 'saaaaaa1', version: 1, instrument: 'NQ', fingerprint: 'fpC', from: '2025-01-02', to: '2025-06-30', op: 'run', hashes: ['h6'], sr: [0.3], at: 1000 },
    { id: 'e6', sid: 'saaaaaa1', root: 'saaaaaa1', version: 1, instrument: 'MNQ', fingerprint: 'fpA', from: '2024-01-02', to: '2024-06-28', op: 'run', hashes: ['h7'], sr: [0.3], at: 1000 }
  ];
  const t = LS.trials(rows, 'MNQ', '2025-03-01', '2025-04-01');
  ok(t.N === 5, 'N = configHash distincts des essais qui recoupent la période (deux essais concurrents comptés, doublon une fois) : ' + t.N);
  ok(t.sdTrials === null && t.sdSource === 'defaut', 'moins de dix Sharpe : sdTrials par défaut');
  ok(Math.abs(LS.trials(rows, 'MNQ', '2025-03-01', '2025-04-01', { n: 400 }).sdTrials - 0.05) < 1e-15, 'avec n : sdTrials = 1/√n');
  ok(LS.trials(rows.filter(x => x.id !== 'e3'), 'MNQ', '2025-03-01', '2025-04-01').N === 4, 'sans la copie : N = 4 ; la stratégie dupliquée hérite des essais de l’origine (h1 compté pour toutes)');
  ok(LS.trials(rows, 'MNQ', '2025-07-01', '2025-07-31').N === 1, 'jeu réimporté (autre empreinte) : ses essais comptent sur la période qu’ils recoupent');
  ok(LS.trials(rows, 'NQ', '2025-03-01', '2025-04-01').N === 1, 'autre instrument : registre séparé');
  ok(LS.trials(rows, 'MNQ', '2024-03-01', '2025-01-02').N === 4, 'bords inclus : une période qui touche le premier jour recoupe');
  ok(LS.trials(rows, 'MNQ', '2026-01-01', '2026-02-01').N === 0, 'période vierge : N = 0');
  const inh = LS.trials(rows, 'MNQ', '2025-03-01', '2025-04-01', { lignee: { t: 1, v: { sources: ['x'], migreLe: 2000, comptes: {} } } });
  ok(inh.inherited === 3 && inh.N === 5, 'hérités = configHash vus avant la migration : ' + inh.inherited);
  const many = []; const r = mulberry(3); const srs = [];
  for (let i = 0; i < 12; i++) { const s = gauss(r) * 0.05; srs.push(s); many.push({ id: 'm' + i, instrument: 'MNQ', from: '2025-01-02', to: '2025-12-31', hashes: ['g' + i], sr: [s], at: i }); }
  const tm = LS.trials(many, 'MNQ', '2025-03-01', '2025-04-01');
  ok(tm.N === 12 && tm.sdSource === 'registre' && Math.abs(tm.sdTrials - sdv(srs)) < 1e-15, 'dix Sharpe ou plus : sdTrials = leur écart-type');
  eq(LS.newHashes(rows, 'MNQ', '2025-03-01', '2025-04-01', ['h1', 'h9', 'h9', 'h6']), ['h9', 'h6'], 'nouveaux configHash (h6 appartient à NQ)');
  const docs = LS.essaiDocs({ sid: 'saaaaaa1', version: 3, instrument: 'MNQ', fingerprint: 'fpA', from: 'a', to: 'b', op: 'sweep', hashes: Array.from({ length: 1200 }, (_, i) => 'k' + i), sr: Array.from({ length: 1200 }, (_, i) => i % 7 ? i / 1e4 : NaN) }, 1767225600000, mulberry(1));
  ok(docs.length === 3 && docs.every(d => d.hashes.length <= 500 && d.hashes.length === d.sr.length && /^e[0-9a-z]+$/.test(d.id) && d.root === 'saaaaaa1' && d.u === d.at) && new Set(docs.map(d => d.id)).size === 3, 'essais : ≤ 500 configHash par document, identifiants distincts');
  ok(docs[0].sr[0] === null && docs[0].sr[1] === 1e-4, 'Sharpe non fini écrit null');
}

/* ---------------------------------------------------------------------------------------------- */
section('PBO par CSCV : hasard ≈ 0,5, configuration dominante basse');
{
  const mat = (seed, nc, ns, plant) => { const r = mulberry(seed); return Array.from({ length: nc }, (_, c) => Array.from({ length: ns }, () => ({ n: 1, sumR: 0, sumR2: 0, net: 100 * gauss(r) + (c === 0 ? plant : 0) }))); };
  const vals = []; for (let s = 1; s <= 8; s++) vals.push(LS.pbo(mat(s, 16, 160, 0)).value);
  near(mean(vals), 0.5, 0.12, 'configurations au hasard : PBO moyen ' + vals.map(v => v.toFixed(2)).join(' '));
  const lo = LS.pbo(mat(9, 16, 160, 60)).value;
  ok(lo <= 0.05, 'configuration dominante plantée : PBO ' + lo);
  const m = mat(4, 10, 96, 0), perf = m.map(row => row.map(c => c.net));
  ok(LS.pbo(m).value === Q.cscv(perf, 8).pbo, 'enveloppe : T.lib.quant.cscv sur les P&L nets par séance');
  ok(LS.pbo(perf).value === LS.pbo(m).value, 'matrice de nombres acceptée');
  ok(LS.pbo([perf[0]]).value === null && LS.pbo(null).value === null, 'moins de deux configurations : null');
  ok(LS.pbo(m.map(r => r.slice(0, 5))).value === null, 'trop peu de séances : null');
  /* Sur un vrai balayage du moteur (marche au tick sans dérive) : la matrice et la grille se lisent telles quelles. */
  const tpl = norm(LS.TEMPLATES[2].spec).spec;
  const sw = LE.op('sweep', { bars: LE.lattice({ sessions: 16, seed: 4 }), spec: tpl, settings: { tick: 0.25, pointValue: 2, commissionRT: 1.24 }, p1: 'n', p2: 'seuil' });
  const pb = LS.pbo(sw.mat), pl = LS.plateau(sw.cells, sw.best), stb = LS.stability(sw.cells);
  ok(sw.cells.length * sw.cells[0].length === 12 && sw.mat.length === 12, 'balayage 3 × 4 du gabarit RSI');
  ok(pb.value === null || (pb.value >= 0 && pb.value <= 1), 'PBO sur la matrice du balayage : ' + pb.value);
  ok(pl === false || (typeof pl === 'number' && isFinite(pl)), 'plateau sur la grille du balayage : ' + pl);
  ok(stb.cells > 0 && stb.value >= 0 && stb.value <= 1, 'stabilité sur la grille du balayage : ' + C(stb.value));
}

/* ---------------------------------------------------------------------------------------------- */
section('Plateau et stabilité');
{
  ok(LS.plateau([[-0.1, -0.2], [-0.3, -0.05]]) === false, 'meilleur négatif : false');
  ok(LS.plateau([[0, 0], [0, 0]]) === false, 'meilleur nul : false');
  near(LS.plateau([[0.8, 0.8, 0.8], [0.8, 1, 0.8], [0.8, 0.8, 0.8]]), 0.8, 1e-15, '2D : huit voisins');
  near(LS.plateau([0.2, 1, 0.6]), 0.4, 1e-15, '1D : deux voisins');
  near(LS.plateau([[0.2], [1], [0.6]]), 0.4, 1e-15, '1D en colonne : deux voisins');
  near(LS.plateau([[1, 0.5], [0.5, 0.2]]), 0.4, 1e-15, 'coin : trois voisins');
  near(LS.plateau([[{ meanR: 0.1 }, { meanR: 0.3 }, { meanR: 0.2 }]], [1, 0]), (0.1 + 0.2) / 2 / 0.3, 1e-15, 'cellules {meanR} et meilleur donné [ix, iy]');
  near(LS.plateau([[0.5, 0.2, 0.4]], [2, 0]), 0.2 / 0.4, 1e-15, 'meilleur imposé : sa propre valeur sert de dénominateur');
  near(LS.plateau([[0.3, 0.3, 0.1]]), (0.3) / 0.3, 1e-15, 'égalité : la première cellule');
  ok(LS.plateau([[0.4]]) === false && LS.plateau([]) === false, 'aucun voisin : false');
  near(LS.plateau([[0.5, null, 0.5]], [0, 0]), 0, 1e-15, 'voisin sans valeur compté zéro');
  const st = LS.stability([[{ meanR: -0.1, n: 10 }, { meanR: 0.2, n: 10 }], [{ meanR: 0.3, n: 10 }, { meanR: 5, n: 0 }]]);
  ok(st.cells === 3 && st.above === 2 && Math.abs(st.value - 2 / 3) < 1e-15 && st.median === 0.2 && st.min === -0.1 && st.max === 0.3, 'stabilité : cellules sans trade exclues ' + C(st));
  ok(LS.stability([[0.1, -0.2, 0.05]], { floor: 0.06 }).above === 1, 'plancher déclaré');
  ok(LS.stability([]).value === null, 'grille vide : null');
}

/* ---------------------------------------------------------------------------------------------- */
section('SPRT : bornes de Wald, décisions, test binomial exact');
{
  const up = Math.log(0.8 / 0.05), lo = Math.log(0.2 / 0.95);
  let s = LS.sprt([], { mu0: -0.1, mu1: 0.2, sigma: 1 });
  ok(Math.abs(s.upper - up) < 1e-15 && Math.abs(s.lower - lo) < 1e-15 && s.decision === 'continuer' && s.form === 'normal', 'bornes ln((1−β)/α) et ln(β/(1−α)), α = 5 %, β = 20 %');
  s = LS.sprt(Array(30).fill(1), { mu0: -0.1, mu1: 0.2, sigma: 1 });
  ok(s.decision === 'avantage-confirme' && s.at === Math.ceil(up / (0.3 * 0.95)) - 1, 'normal : gains constants, franchissement haut au pas calculé (' + s.at + ')');
  s = LS.sprt(Array(30).fill(-1), { mu0: -0.1, mu1: 0.2, sigma: 1 });
  ok(s.decision === 'aucun-avantage' && s.at === Math.ceil(-lo / (0.3 * 1.05)) - 1, 'normal : pertes constantes, franchissement bas (' + s.at + ')');
  s = LS.sprt([0.05, 0.05], { mu0: -0.1, mu1: 0.2, sigma: 1 }); ok(s.decision === 'continuer' && s.n === 2 && s.llr === 0, 'au milieu : continuer, incrément nul');
  ok(LS.sprt([1, 2], { mu0: 0.1, mu1: 0.1, sigma: 1 }).decision === 'na' && LS.sprt([1], { mu0: 0.1, mu1: 0.05, sigma: 1 }).decision === 'na', 'mu1 ≤ mu0 → na');
  ok(LS.sprt([1], { mu0: 0, mu1: 0.1, sigma: 0 }).decision === 'na', 'σ nul → na');
  /* Binomial exact. */
  const p0 = 0.4, p1 = 0.5, lw = Math.log(p1 / p0), ll = Math.log((1 - p1) / (1 - p0));
  s = LS.sprt(Array(40).fill(1), { form: 'binomial', p0, p1 });
  ok(s.form === 'binomial' && s.decision === 'avantage-confirme' && s.at === Math.ceil(up / lw) - 1, 'binomial : gains seuls, franchissement au pas ' + s.at);
  s = LS.sprt(Array(40).fill(-1), { p0, p1 });
  ok(s.decision === 'aucun-avantage' && s.at === Math.ceil(-lo / -ll) - 1, 'binomial : pertes seules, franchissement au pas ' + s.at);
  const r = mulberry(21), xs = []; for (let i = 0; i < 9; i++) xs.push(r() < 0.5 ? 1.2 : r() < 0.2 ? 0 : -1);
  s = LS.sprt(xs, { p0, p1 });
  const w = xs.filter(x => x > 0).length, l = xs.filter(x => x < 0).length;
  let lik = 0; xs.forEach(x => { if (x > 0) lik += Math.log(p1) - Math.log(p0); else if (x < 0) lik += Math.log(1 - p1) - Math.log(1 - p0); });
  ok(s.wins === w && s.losses === l && s.n === w + l, 'binomial : r = 0 ne compte pas (' + w + ' gains, ' + l + ' pertes)');
  near(s.llr, w * lw + l * ll, 1e-12, 'binomial exact : w·ln(p1/p0) + l·ln((1−p1)/(1−p0))');
  near(s.llr, lik, 1e-12, 'binomial exact : log du rapport de vraisemblance de Bernoulli');
  ok(LS.sprt([1], { p0: 0.5, p1: 0.45 }).decision === 'na' && LS.sprt([1], { p0: 0, p1: 0.5 }).decision === 'na', 'p1 ≤ p0 ou taux hors ]0, 1[ → na');
  /* Loi nulle : sous H0 la fausse confirmation reste près de α ; sous H1 la fausse condamnation près de β. */
  const sim = (mu, form, seed) => { const g = mulberry(seed); let conf = 0, rej = 0; for (let k = 0; k < 1500; k++) { const ys = []; for (let i = 0; i < 1500; i++) ys.push(form === 'binomial' ? (g() < mu ? 1 : -1) : mu + gauss(g)); const d = LS.sprt(ys, form === 'binomial' ? { p0: 0.4, p1: 0.5 } : { mu0: -0.05, mu1: 0.15, sigma: 1 }).decision; if (d === 'avantage-confirme') conf++; if (d === 'aucun-avantage') rej++; } return { conf: conf / 1500, rej: rej / 1500 }; };
  const h0 = sim(-0.05, 'normal', 31), h1 = sim(0.15, 'normal', 32), b0 = sim(0.4, 'binomial', 33), b1 = sim(0.5, 'binomial', 34);
  ok(h0.conf < 0.065, 'normal sous H0 : fausse confirmation ' + h0.conf + ' ≤ α');
  ok(h1.rej < 0.23, 'normal sous H1 : fausse condamnation ' + h1.rej + ' ≤ β');
  ok(b0.conf < 0.065, 'binomial sous H0 : fausse confirmation ' + b0.conf + ' ≤ α');
  ok(b1.rej < 0.23, 'binomial sous H1 : fausse condamnation ' + b1.rej + ' ≤ β');
  /* Plan et trades de suivi. */
  const fx = norm(spec({ target: { type: 'r', value: 2 } })).spec;
  ok(LS.fixedGeometry(fx) === true, 'géométrie fixe : objectif en R, sans gestion');
  ok(LS.fixedGeometry(norm(spec({ target: { type: 'r', value: 2 } }, { manage: { breakeven: 1 } })).spec) === false && LS.fixedGeometry(norm(spec({ target: { type: 'pts', value: 8 } })).spec) === false && LS.fixedGeometry(norm(spec({}, { manage: { maxBars: 5 } })).spec) === false, 'break-even, objectif en points ou maxBars : géométrie variable');
  eq(LS.sprtPlan(fx, { equilibrium: 0.36, winRate: 0.4, costR: 0.08, sdR: 1.3 }, 0.02), { form: 'binomial', p0: 0.36, p1: 0.4 }, 'plan binomial : p0 = equilibrium, p1 = taux en échantillon');
  eq(LS.sprtPlan(norm(spec({ target: { type: 'pts', value: 8 } })).spec, { equilibrium: 0.36, winRate: 0.4, costR: 0.08, sdR: 1.3 }, 0.02), { form: 'normal', mu0: -0.08, mu1: 0.02, sigma: 1.3 }, 'plan normal : mu0 = −costR, mu1 = borne basse du bootstrap');
  const ver = { sid: 'saaaaaa1', version: 2, sealedAt: 5000 };
  const jr = [
    { id: 'a', strat: 'saaaaaa1', stratV: 2, kind: 'pris', status: 'clos', r: 1, at: 7000 },
    { id: 'b', strat: 'saaaaaa1', stratV: 2, kind: 'pris', status: 'clos', r: -1, at: 6000 },
    { id: 'c', strat: 'saaaaaa1', stratV: 1, kind: 'pris', status: 'clos', r: 1, at: 6500 },
    { id: 'd', strat: 'saaaaaa1', stratV: 2, kind: 'pris', status: 'clos', r: 1, at: 4000 },
    { id: 'e', strat: 'sautre001', stratV: 2, kind: 'pris', status: 'clos', r: 1, at: 6500 },
    { id: 'f', strat: 'saaaaaa1', stratV: 2, kind: 'pris', status: 'ouvert', at: 6600 },
    { id: 'g', strat: 'saaaaaa1', stratV: 2, kind: 'refus', at: 6700 },
    { id: 'h', strat: 'saaaaaa1', stratV: 2, kind: 'pris', status: 'clos', at: 6800 },
    { id: 'i', strat: 'saaaaaa1', stratV: 2, kind: 'pris', status: 'clos', r: 2, at: 6900, deleted: true }
  ];
  eq(LS.followTrades(jr, ver).map(x => x.id), ['b', 'a'], 'suivi : version scellée, après sealedAt, pris, clos, avec R, dans l’ordre');
  ok(LS.followTrades(jr, { sid: 'saaaaaa1', version: 2, sealedAt: null }).length === 0, 'version non scellée : aucun trade de suivi');
}

/* ---------------------------------------------------------------------------------------------- */
section('CUSUM et sa loi nulle');
{
  const c = LS.cusum([0, 0, 0, -2, -2, -2, 3], 0, 0.5, 4);
  eq(c.neg, [0, 0, 0, 1.5, 3, 4.5, 1], 'cumul des chutes');
  ok(c.alarm === 5 && c.alarmUp === -1, 'alarme au premier dépassement de h');
  near(LS.cusumArl0(0.5, 4, 1), 336, 4, 'ARL0 de Siegmund pour k = 0,5, h = 4 (≈ 336)');
  const r = mulberry(8), runs = [];
  for (let k = 0; k < 400; k++) { const xs = []; for (let i = 0; i < 4000; i++) xs.push(gauss(r)); const a = LS.cusum(xs, 0, 0.5, 4, 1).alarm; runs.push(a < 0 ? 4000 : a + 1); }
  const arl = mean(runs), ref = LS.cusumArl0(0.5, 4, 1);
  ok(Math.abs(arl - ref) / ref < 0.2, 'loi nulle : durée moyenne avant fausse alarme simulée ' + arl.toFixed(0) + ' contre ' + ref.toFixed(0));
}

/* ---------------------------------------------------------------------------------------------- */
section('Gabarits : six points de départ, valides, neutres');
{
  const ids = LS.TEMPLATES.map(t => t.id);
  eq(ids, ['vwap-rejet', 'or-cassure', 'rsi-retour', 'veille-rejet', 'ema-poursuite', 'gex-proche', 'plan-hvz'], 'les six gabarits de §5, plus celui du desk Plan');
  const lat = LE.lattice({ sessions: 8, seed: 12 });
  LS.TEMPLATES.forEach(t => {
    const n = norm(t.spec);
    ok(n.errors.length === 0, t.id + ' : normalise sans erreur ' + n.errors.join(' | '));
    ok(typeof t.label === 'string' && t.label && typeof t.description === 'string' && /aucun avantage n’est supposé/.test(t.description) && !/rentab|gagnant|profitable|garanti|'/i.test(t.description + t.label), t.id + ' : description neutre');
    readingOk(LS.describe(t.spec), t.id, { seller: true });
    const f = LS.fromTemplate(t.id, 'sgabarit01', 1767225600000);
    const nf = norm(f, { strict: true });
    ok(nf.errors.length === 0 && f.id === 'sgabarit01_v1' && f.status === 'brouillon' && f.template === t.id, t.id + ' : fromTemplate rend un brouillon complet ' + nf.errors.join(' | '));
    eq(norm(n.spec).spec, n.spec, t.id + ' : idempotent');
    ok(/^h[0-9a-f]{16}$/.test(LS.hash(t.spec, 1.24)) && /^h[0-9a-f]{16}$/.test(LS.configHash(t.spec)), t.id + ' : hachages');
    let m = null; try { m = LS.mirror(n.spec, 'spec'); } catch (e) { m = null; }
    ok(m && m.trigger, t.id + ' : côté vendeur calculable');
    const lvl = /"f":"(level|nearest)"/.test(C(t.spec.long));
    if (lvl) {
      ok(hasErr(norm(t.spec, { dataset: { roll: 'inconnu' } }), /roll inconnu/), t.id + ' : refusé sur un jeu au raccord inconnu');
      ok(norm(t.spec, { dataset: { roll: 'non-ajuste' } }).errors.length === 0, t.id + ' : accepté sur un jeu non ajusté');
    } else {
      let res = null, e = null; try { res = LE.run({ bars: lat, spec: n.spec, values: {}, settings: { tick: 0.25, pointValue: 2, commissionRT: 1.24 } }); } catch (x) { e = x.message; }
      ok(res && Array.isArray(res.trades) && res.stats && res.counts.signals >= 0, t.id + ' : le moteur joue le gabarit sur la marche au tick ' + (e || (res.trades.length + ' trades, ' + res.counts.signals + ' signaux')));
    }
  });
  throws(() => LS.fromTemplate('inconnu'), /Gabarit inconnu/, 'gabarit inconnu');
}

/* ---------------------------------------------------------------------------------------------- */
section('Verdict : critères de §5, niveaux, sens de null et de na');
{
  const Gt = LS.GATES;
  ok(LS.sampleMin() === 619 && LS.sampleMin() === Q.MUR.r1 && Q.route1(Gt.sample.sr, Gt.sample.alpha, Gt.sample.power) === 619, 'échantillon : route 1 d’ALP nº 3, 619 trades');
  ok(Gt.randomP === 0.05 && Gt.permuteP === 0.05 && Gt.dsr === 0.95 && Gt.pbo === 0.2 && Gt.plateau === 0.7 && Gt.wfe === 0.5 && Gt.oosP === 0.05 && Gt.rejectP === 0.5 && Gt.floors.slipTicks === 1 && Gt.stressTicks === 1, 'seuils de §5');
  const src = fs.readFileSync(path.join(__dirname, '..', 'src', 'desks', 'labo-stats.js'), 'utf8');
  const block = src.slice(src.indexOf('LS.GATES = {'), src.indexOf('};', src.indexOf('LS.GATES = {')));
  ['sample', 'randomP', 'permuteP', 'dsr', 'pbo', 'plateau', 'stressTicks', 'wfe', 'oosP', 'rejectP', 'floors'].forEach(k => ok(new RegExp('\\*/\\s*' + k + ':').test(block), 'GATES.' + k + ' porte sa justification en commentaire'));
  eq(LS.floorCosts({ commissionRT: 0.5, slipTicks: 0 }, 1.24), { commissionRT: 1.24, slipTicks: 1, raised: true }, 'planchers : commission du réglage, un tick');
  eq(LS.floorCosts({ commissionRT: 2, slipTicks: 2 }, 1.24), { commissionRT: 2, slipTicks: 2, raised: false }, 'coûts déclarés au-dessus des planchers : gardés');
  eq(LS.floorCosts({ commissionRT: null, slipTicks: 1 }, 1.24), { commissionRT: 1.24, slipTicks: 1, raised: true }, 'commission absente : celle du réglage');
  const plan = LS.oosPlan({ nIS: 700, sessionsIS: 350, sessionsOOS: 100, meanR: 0.05, costR: 0.05, sdR: 1.2 });
  ok(plan.expected === 200 && plan.required === Q.route1(0.1 / 1.2, 0.05, 0.8) && plan.enough === false, 'avant l’ouverture : trades attendus ' + plan.expected + ', requis ' + plan.required);
  ok(LS.oosPlan({ nIS: 700, sessionsIS: 350, sessionsOOS: 100, meanR: -0.1, costR: 0.05, sdR: 1.2 }).required === Infinity, 'sans écart à −costR : aucun nombre ne suffit');
  const good = { n: 700, meanR: 0.1, costR: 0.05, random: { p: 0.01 }, permute: { p: 0.02 }, dsr: { dsr: 0.97 }, N: 12, pbo: 0.1, plateau: 0.8, costs: { floor: 0.08, plus1: 0.05 }, wfa: { wfe: 0.7 }, oos: { sealed: true, altered: false, first: true, p: 0.01 } };
  const textOk = (v, tag) => { ok(!/undefined|NaN|'/.test(v.text) && v.items.every(i => !/undefined|NaN|'/.test(String(i.why) + String(i.value) + String(i.label))), tag + ' : textes propres « ' + v.text + ' »'); };
  let v = LS.verdict(good);
  eq(v.items.map(i => i.id), ['echantillon', 'hasard', 'permutation', 'dsr', 'pbo', 'plateau', 'couts', 'wfe', 'oos'], 'neuf critères, dans l’ordre de §5');
  ok(v.level === 'prete-simulateur' && v.items.every(i => i.pass === true), 'tous tenus : prête pour le simulateur');
  ok(/pas une promesse de gain/.test(v.text), 'prête : aucune promesse');
  textOk(v, 'prête');
  v = LS.verdict(Object.assign({}, good, { pbo: 'na', plateau: 'na', wfa: 'na' }));
  ok(v.level === 'prete-simulateur' && v.items.filter(i => i.pass === 'na').length === 3, '’na’ (sans balayage ni analyse en avant) n’empêche pas « prête »');
  textOk(v, 'na');
  v = LS.verdict(Object.assign({}, good, { pbo: null }));
  ok(v.level === 'a-approfondir' && v.items.filter(i => i.id === 'pbo')[0].pass === null && /reste à calculer/.test(v.text), 'null (applicable, non calculé) empêche « prête »');
  textOk(v, 'null');
  v = LS.verdict(Object.assign({}, good, { n: 100 }));
  ok(v.level === 'a-approfondir' && v.items[0].pass === false && /il en manque 519/.test(v.items[0].why), 'échantillon trop court : à approfondir');
  v = LS.verdict(Object.assign({}, good, { meanR: -0.06, costR: 0.05 }));
  ok(v.level === 'rejetee' && /ne dépasse pas/.test(v.text), 'meanR ≤ −costR : rejetée');
  v = LS.verdict(Object.assign({}, good, { meanR: -0.05, costR: 0.05 }));
  ok(v.level === 'rejetee', 'meanR = −costR exactement : rejetée');
  v = LS.verdict(Object.assign({}, good, { random: { p: 0.5 } }));
  ok(v.level === 'rejetee' && /une fois sur deux/.test(v.text), 'p des entrées au hasard ≥ 0,5 : rejetée');
  v = LS.verdict(Object.assign({}, good, { random: { p: 0.2 } }));
  ok(v.level === 'a-approfondir' && v.items[1].pass === false, 'p = 0,2 : à approfondir, pas rejetée');
  v = LS.verdict(Object.assign({}, good, { oos: { sealed: true, first: false, p: 0.01, prior: { version: 1, at: 1767225600000 } } }));
  ok(v.level === 'a-approfondir' && v.items[8].pass === false && /déjà vu.*version 1/.test(v.items[8].why), 'seconde ouverture de la lignée : le critère tombe');
  textOk(v, 'déjà vu');
  v = LS.verdict(Object.assign({}, good, { oos: { sealed: true, altered: true, first: true, p: 0.01 } }));
  ok(v.items[8].pass === false, 'version altérée : le critère tombe');
  v = LS.verdict(Object.assign({}, good, { oos: null }));
  ok(v.items[8].pass === null && v.level === 'a-approfondir', 'hors échantillon pas encore ouvert : null');
  v = LS.verdict(Object.assign({}, good, { costs: { floor: 0.08, na: true, through1: 0.02 } }));
  ok(v.items[6].pass === true && /dépassement/.test(v.items[6].why), 'aucune jambe glissée : critère lu sur le dépassement exigé');
  v = LS.verdict(Object.assign({}, good, { costs: { floor: 0.08, plus1: -0.01 } }));
  ok(v.items[6].pass === false && v.level === 'a-approfondir', 'coûts : négatif à +1 tick → false');
  v = LS.verdict(Object.assign({}, good, { plateau: false }));
  ok(v.items[5].pass === false, 'plateau false (meilleur ≤ 0) : critère faux');
  v = LS.verdict(Object.assign({}, good, { wfa: { wfe: null } }));
  ok(v.items[7].pass === false, 'WFE indéfinie : critère faux');
  v = LS.verdict(Object.assign({}, good, { dsr: 0.9, N: 40 }));
  ok(v.items[3].pass === false && /N = 40/.test(v.items[3].why), 'Sharpe déflaté sous 0,95 avec N du registre');
  v = LS.verdict(Object.assign({}, good, { blocked: 'migration incomplète (essais : 3 sur 5).' }));
  ok(v.level === 'a-approfondir' && /migration incomplète/.test(v.text), 'migration incomplète : « prête » bloquée');
  v = LS.verdict({});
  ok(v.level === 'a-approfondir' && v.items.every(i => i.pass === null), 'rien de calculé : tout à null, à approfondir');
  textOk(v, 'vide');
  v = LS.verdict(Object.assign({}, good, { pbo: 0.5, n: 10 }));
  ok(/surajustement \(PBO\)/.test(v.text), 'libellés en minuscule sans abîmer les sigles : « ' + v.text + ' »');
  ok(LS.LEVELS['a-approfondir'] && LS.LEVELS.rejetee && LS.LEVELS['prete-simulateur'], 'libellés des niveaux');
}

/* ---------------------------------------------------------------------------------------------- */
section('tools/labo-check.js');
{
  const tool = require(path.join(__dirname, '..', 'tools', 'labo-check.js'));
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'labo-check-'));
  const good = path.join(dir, 'bon.json'), bad = path.join(dir, 'faux.json'), list = path.join(dir, 'liste.json'), ds = path.join(dir, 'jeu.json');
  fs.writeFileSync(good, JSON.stringify(LS.TEMPLATES[0].spec));
  fs.writeFileSync(bad, JSON.stringify(spec({ trigger: { cmp: '>', a: { f: 'close' }, b: '$p' } })));
  fs.writeFileSync(list, JSON.stringify([LS.TEMPLATES[2].spec, LS.TEMPLATES[5].spec]));
  fs.writeFileSync(ds, JSON.stringify({ name: 'MNQ témoin', roll: 'inconnu' }));
  let out = []; let code = tool.main([good, '--commission', '1,24'], s => out.push(s));
  const txt = out.join('\n');
  ok(code === 0 && /Erreurs \(0\)/.test(txt) && /Lecture :/.test(txt) && /Côté vendeur/.test(txt), 'stratégie valide : code 0, lecture imprimée');
  ok(txt.indexOf('Hachage scellé : ' + LS.hash(LS.TEMPLATES[0].spec, 1.24)) >= 0 && txt.indexOf('configHash     : ' + LS.configHash(LS.TEMPLATES[0].spec)) >= 0, 'les deux hachages = ceux de T.lib.laboStats');
  out = []; code = tool.main([bad], s => out.push(s));
  ok(code === 1 && /✗ long\.trigger\.b/.test(out.join('\n')) && /Hachage : impossible/.test(out.join('\n')), 'stratégie fautive : code 1, erreur nommée');
  out = []; code = tool.main([list, '--dataset', ds], s => out.push(s));
  ok(code === 1 && /n° 2/.test(out.join('\n')) && /roll inconnu/.test(out.join('\n')), 'liste et jeu : le gabarit GEX est refusé sur un jeu au raccord inconnu');
  out = []; code = tool.main([good, '--json', '--values', '{"bande": -2.5}'], s => out.push(s));
  const js = JSON.parse(out.join('\n'));
  ok(code === 0 && js.ok === true && js.configHash === LS.configHash(LS.TEMPLATES[0].spec, { bande: -2.5 }) && js.reading.length >= 10, 'sortie JSON, valeurs imposées');
  ok(tool.main(['--zz'], () => {}) === 2 && tool.main([path.join(dir, 'absent.json')], () => {}) === 2 && tool.main([], () => {}) === 2, 'appel mal formé : code 2');
  const p = cp.spawnSync(process.execPath, [path.join(__dirname, '..', 'tools', 'labo-check.js'), bad], { encoding: 'utf8' });
  ok(p.status === 1 && /Résultat : 1 erreur/.test(p.stdout), 'en ligne de commande : code de sortie non nul sur erreur');
  const p2 = cp.spawnSync(process.execPath, [path.join(__dirname, '..', 'tools', 'labo-check.js'), good], { encoding: 'utf8' });
  ok(p2.status === 0 && /Résultat : valide/.test(p2.stdout), 'en ligne de commande : code 0 sur une stratégie valide');
  fs.rmSync(dir, { recursive: true, force: true });
}

console.log((fails ? 'ÉCHEC' : 'OK') + ' — labo-stats : ' + passes + ' contrôles réussis, ' + fails + ' échec' + (fails > 1 ? 's' : '') + ' sur ' + (passes + fails) + '.');
process.exit(fails ? 1 : 0);
