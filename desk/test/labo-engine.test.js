// Tests du moteur du Labo de stratégie (LABO.md §3 et §4) : node test/labo-engine.test.js (sortie non nulle si échec).
// Aucune donnée de marché : barres construites à la main (résultats calculés à la main en commentaire) et marches
// synthétiques amorcées (T.lib.laboEngine.lattice, T.lib.quant.synth).
const vm = require('vm');
const H = require('./harness');
const { T, lib: E, ctx: CTX } = H(['quant', 'labo-engine']);
const Q = T.lib.quant;
let fails = 0, passes = 0;
function ok(cond, msg) { if (cond) passes++; else { fails++; console.error('ÉCHEC', msg); } }
function near(a, b, tol, msg) { const good = typeof a === 'number' && typeof b === 'number' && (a === b || Math.abs(a - b) <= tol * Math.max(1, Math.abs(b))); ok(good, msg + ' : ' + a + ' attendu ' + b); }
function throws(fn, re, msg) { try { fn(); ok(false, msg + ' (aucune erreur levée)'); } catch (e) { ok(!re || re.test(String(e.message)), msg + ' : ' + e.message); } }
function section(t) { console.log('· ' + t); }
const MIN = 60000;
const same = (x, y) => (x !== x && y !== y) || x === y;

/* ---------- Barres à la main : une séance de clé 2026-01-06 (mardi), ouverte le lundi 5 janvier à 23:00 UTC
   = 18:00 New York = 00:00 Paris. La minute m de la séance est aussi la minute Paris 00:m. ---------- */
const T0 = Date.UTC(2026, 0, 5, 23, 0);
function bars(over, n, base, dflt) {
  const out = [];
  for (let m = 0; m < (n || 60); m++) {
    const x = over && over[m], d = dflt || [base || 100, base || 100, base || 100, base || 100];
    const b = !x ? { o: d[0], h: d[1], l: d[2], c: d[3] } : Array.isArray(x) ? { o: x[0], h: x[1], l: x[2], c: x[3], lowFirst: x[4] } : Object.assign({}, x);
    if (b.lowFirst === undefined) delete b.lowFirst;
    b.t = T0 + m * MIN; b.v = 10; out.push(b);
  }
  return out;
}
const hhmm = m => String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0');
const at = m => ({ time: [hhmm(m), hhmm(m + 1)] });
function mk(o) {
  o = o || {};
  const sig = [].concat(o.sig == null ? 10 : o.sig);
  return {
    side: o.side || 'long', anchor: 'globex', mirror: true,
    session: Object.assign({ tz: 'Europe/Paris', from: '00:00', to: '09:00', flat: '09:00', days: [1, 2, 3, 4, 5], warmup: 0 }, o.session),
    long: { setup: o.setup || [], trigger: o.trigger || (sig.length === 1 ? at(sig[0]) : { any: sig.map(at) }), entry: o.entry || { type: 'market' }, stop: o.stop || { type: 'pts', value: 2 }, target: o.target || { type: 'pts', value: 4 } },
    manage: Object.assign({ breakeven: null, trail: null, maxBars: null, exitOnOpposite: false }, o.manage),
    risk: Object.assign({ mode: 'contracts', contracts: 1, riskUsd: 150, maxQty: null, minStopTicks: 1, maxPerSession: 10, maxLossesPerSession: 10, dailyStopUsd: 0, cooldown: 0 }, o.risk),
    costs: Object.assign({ commissionRT: 0, slipTicks: 0 }, o.costs), fill: o.fill || 'pessimiste', params: o.params || {}
  };
}
const SET = { tick: 0.25, pointValue: 2, commissionRT: 0, maxContracts: 0 };
function run(b, spec, extra) { const a = Object.assign({ bars: b, spec }, extra || {}); a.settings = Object.assign({}, SET, extra && extra.settings); return E.run(a); }
const one = r => r.trades.length === 1 ? r.trades[0] : null;
/* Réflexion p → K − p : le haut devient le bas, lowFirst s’inverse. */
function reflectBars(b, K) { return b.map(x => { const y = { t: x.t, o: K - x.o, h: K - x.l, l: K - x.h, c: K - x.c, v: x.v }; if (x.lowFirst != null) y.lowFirst = x.lowFirst ? 0 : 1; return y; }); }
function reflectCols(c, K) {
  const n = c.t.length, o = new Float64Array(n), h = new Float64Array(n), l = new Float64Array(n), cl = new Float64Array(n), lf = new Uint8Array(n);
  for (let i = 0; i < n; i++) { o[i] = K - c.o[i]; h[i] = K - c.l[i]; l[i] = K - c.h[i]; cl[i] = K - c.c[i]; lf[i] = c.lowFirst[i] ? 0 : 1; }
  return { t: c.t, o, h, l, c: cl, v: c.v, lowFirst: lf, walk: c.walk };
}

section('Autonomie : le moteur tourne dans un contexte vide');
{
  const fresh = vm.runInNewContext('(' + E.engine.toString() + ')', {});
  const lat = E.lattice({ sessions: 4, sigma: 2, seed: 3 });
  const spec = mk({ trigger: { bar: 'up' }, session: { warmup: 15 }, manage: { maxBars: 20 } });
  const a = fresh({ op: 'run', bars: lat, spec, settings: SET }), b = E.run({ bars: lat, spec, settings: SET });
  ok(a.trades.length > 10 && a.trades.length === b.trades.length, 'run dans un contexte vide : ' + a.trades.length + ' trades');
  near(a.stats.net, b.stats.net, 1e-12, 'même résultat net dans le contexte vide');
  ok(!/\bT\.|quantEngine|new Function/.test(E.engine.toString()), 'aucune référence à T, à quantEngine ni à new Function');
  const src = E.workerSource();
  ok(typeof src === 'string' && src.indexOf('laboEngine') >= 0, 'source du worker construite');
  new vm.Script(src);
  ok(true, 'la source du worker se compile');
}

section('Clé de séance Globex et résolution des paramètres');
{
  ok(E.key(Date.UTC(2026, 0, 5, 22, 59)) === '2026-01-05', '17:59 New York appartient à la séance du lundi');
  ok(E.key(Date.UTC(2026, 0, 5, 23, 0)) === '2026-01-06', '18:00 New York ouvre la séance du mardi');
  ok(E.key(Date.UTC(2026, 2, 9, 22, 0)) === '2026-03-10', 'heure d’été américaine : 18:00 EDT = 22:00 UTC ouvre la séance suivante');
  ok(E.key(Date.UTC(2026, 2, 9, 21, 59)) === '2026-03-09', 'heure d’été américaine : 21:59 UTC reste dans la séance du lundi');
  const ks = E.op('key', { ts: [T0, T0 + 1440 * MIN] });
  ok(ks[0] === '2026-01-06' && ks[1] === '2026-01-07', 'clés en lot');
  const spec = { params: { k: { v: 1.5 }, n: { v: 20 } }, long: { trigger: { cmp: '>', a: { f: 'close' }, b: { f: 'vwap', k: '$k' } }, stop: { type: 'pts', value: '$n' } } };
  const r1 = E.resolve(spec), r2 = E.resolve(spec, { k: 2 });
  ok(r1.long.trigger.b.k === 1.5 && r1.long.stop.value === 20, '$nom remplacé par params.nom.v');
  ok(r2.long.trigger.b.k === 2, 'une valeur imposée (balayage) l’emporte');
  ok(r1.params.k.v === 1.5, 'les params sont conservés');
  throws(() => E.resolve({ long: { stop: { type: 'pts', value: '$x' } } }), /\$x/, '$nom sans paramètre : erreur');
  const st = E.op('stats', { trades: [{ r: 1, pnl: 4, qty: 1, risk: 2, c: 0, fin: 'objectif' }], settings: { pointValue: 2 } });
  ok(st.n === 1 && st.meanR === 1, 'op stats');
}

/* =================================== Heures =================================== */
section('Heures : fenêtre 20:00–02:00 New York, sortie forcée à 03:00');
{
  const lat = E.lattice({ sessions: 8, sigma: 2, seed: 5 });
  const spec = mk({ trigger: { bar: 'up' }, session: { tz: 'America/New_York', from: '20:00', to: '02:00', flat: '03:00', warmup: 0 }, stop: { type: 'pts', value: 400 }, target: { type: 'none' }, risk: { maxPerSession: 0 } });
  const r = run(lat, spec);
  const smOf = i => (lat.t[i] - lat.t[Math.floor(i / 1380) * 1380]) / MIN;
  ok(r.trades.length === 8, 'une position par séance, tenue jusqu’à la sortie forcée : ' + r.trades.length);
  ok(r.trades.every(t => smOf(t.e) >= 120 && smOf(t.e) < 480), 'chaque entrée est dans la fenêtre (20:00 → 02:00 = minutes 120 → 480 depuis l’ancre)');
  ok(r.trades.every(t => t.fin === 'flat' && smOf(t.j) === 540 && t.exit === lat.o[t.j]), 'chaque sortie à l’ouverture de 03:00 (minute 540), raison flat');
  ok(r.sessions.length === 8 && r.sessions.every(s => s.n === 1), 'toutes les séances éligibles publiées');
}
section('Heures : aucun croisement de VWAP sur la première barre ancrée');
{
  const lat = E.lattice({ sessions: 10, sigma: 2, seed: 9 });
  const s = E.op('series', { bars: lat, spec: { anchor: 'globex' }, settings: SET, conds: [{ cross: 'up', a: { f: 'close' }, b: { f: 'vwap' } }, { cross: 'down', a: { f: 'close' }, b: { f: 'vwap' } }, { touch: { f: 'vwap' }, from: 'above' }, { break: { f: 'vwap' }, dir: 'up' }] });
  let firsts = 0, any = 0;
  for (let k = 0; k < 10; k++) { const i = k * 1380; s.conds.forEach(c => { if (c[i] !== 0) firsts++; }); }
  s.conds[0].forEach(x => { if (x === 1) any++; });
  ok(firsts === 0, 'cross, touch, break faux sur la première barre de chaque séance');
  ok(any > 50, 'les croisements existent ailleurs : ' + any);
}
section('Heures : ancrage paris pendant la semaine de décalage des changements d’heure');
{
  // 8 mars 2026 : heure d’été américaine ; l’Europe change le 29 mars. Globex rouvre à 23:00 Paris.
  const lat = E.lattice({ sessions: 3, sigma: 2, seed: 2, start: '2026-03-10' });
  const spec = mk({ trigger: { bar: 'up' }, session: { tz: 'Europe/Paris', from: '00:00', to: '09:00', flat: '09:00', warmup: 0 } });
  spec.anchor = 'paris';
  const s = E.op('series', { bars: lat, spec, settings: SET, operands: [{ f: 'vwap' }, { f: 'sessmin' }, { f: 'sess', of: 'open' }, { f: 'close' }] });
  let pre = 0; for (let i = 0; i < 60; i++) if (s.ops[0][i] === s.ops[0][i] || s.ops[1][i] === s.ops[1][i] || s.ops[2][i] === s.ops[2][i] || s.sig.L[i]) pre++;
  ok(pre === 0, 'les 60 barres avant 00:00 Paris : grandeurs ancrées NaN, aucun signal');
  ok(s.ops[1][60] === 0 && s.ops[2][60] === lat.o[60], 'l’ancre tombe sur la 61e barre (00:00 Paris), ouverture ancrée = son ouverture');
  near(s.ops[0][60], (lat.h[60] + lat.l[60] + lat.c[60]) / 3, 1e-12, 'VWAP repartie à l’ancre');
  ok(s.ops[3][0] === lat.c[0], 'les grandeurs non ancrées restent définies avant l’ancre');
  const lat2 = E.lattice({ sessions: 2, sigma: 2, seed: 2, start: '2026-01-06' });
  const s2 = E.op('series', { bars: lat2, spec, settings: SET, operands: [{ f: 'sessmin' }] });
  ok(s2.ops[0][0] === 0, 'hors semaine de décalage, l’ancre paris est la première barre');
}
section('Heures : ancrage rth');
{
  const lat = E.lattice({ sessions: 3, sigma: 2, seed: 4 });
  const spec = mk({ trigger: { bar: 'up' }, session: { tz: 'America/New_York', from: '09:45', to: '15:00', flat: '15:30' } });
  spec.anchor = 'rth';
  const s = E.op('series', { bars: lat, spec, settings: SET, operands: [{ f: 'vwap' }, { f: 'prev', of: 'close' }, { f: 'sessmin' }] });
  let bad = 0;
  for (let i = 1380; i < 2760; i++) { const m = i - 1380, inside = m >= 930 && m < 1320; if (inside !== (s.ops[0][i] === s.ops[0][i])) bad++; }
  ok(bad === 0, 'VWAP rth définie de 09:30 à 16:00 New York seulement (minutes 930 → 1320 de la séance Globex)');
  ok(s.ops[2][1380 + 930] === 0, 'sessmin rth = 0 à 09:30');
  ok(s.ops[1][1380 + 1000] === lat.c[1319], 'prev close rth = clôture de 15:59 de la séance précédente');
  const r = run(lat, spec);
  ok(r.trades.length > 0 && r.trades.every(t => (t.e % 1380) >= 945 && (t.e % 1380) < 1290), 'une stratégie rth entre dans sa fenêtre');
  const bad1 = mk({ session: { tz: 'America/New_York', from: '08:00', to: '10:00', flat: '10:00' } }); bad1.anchor = 'rth';
  throws(() => run(lat, bad1), /rth/, 'rth dont la fenêtre sort de 09:30–16:00 : refusée');
  const bad2 = mk({ session: { tz: 'America/New_York', from: '10:00', to: '17:00', flat: '17:00' } }); bad2.anchor = 'rth';
  throws(() => run(lat, bad2), /rth/, 'rth dont la sortie forcée dépasse 16:00 : refusée');
}
section('Heures : le signal est pris si i + 1 entre dans la fenêtre');
{
  const b = bars({}, 60);
  const r1 = run(b, mk({ sig: 10, session: { from: '00:11' }, manage: { maxBars: 1 } }));
  ok(r1.trades.length === 1 && r1.trades[0].e === 11, 'signal à 00:10, fenêtre dès 00:11 : exécuté à 00:11');
  const r2 = run(b, mk({ sig: 9, session: { from: '00:11' }, manage: { maxBars: 1 } }));
  ok(r2.trades.length === 0 && r2.counts.signals === 0, 'signal à 00:09 : hors de la fenêtre, pas compté');
  const r3 = run(b, mk({ sig: 10, session: { warmup: 11 }, manage: { maxBars: 1 } }));
  ok(r3.trades.length === 0, 'amorçage de 11 minutes : la barre 10 ne porte pas de signal');
  const r4 = run(b, mk({ sig: 10, session: { days: [1, 3, 4, 5] }, manage: { maxBars: 1 } }));
  ok(r4.trades.length === 0 && r4.sessions.length === 0, 'jour exclu (mardi) : séance non jouée');
}

/* =================================== Opérandes =================================== */
section('Opérandes : VWAP identique à sessionVwap de Quant');
{
  const sb = Q.synth({ seed: 3, days: 3, sigma: 4 }), pre = Q.sessionVwap(sb);
  const s = E.op('series', { bars: sb, spec: { anchor: 'globex' }, settings: SET, operands: [{ f: 'vwap' }, { f: 'vwap', k: 1 }, { f: 'dist', a: { f: 'close' }, b: { f: 'vwap' }, unit: 'sd' }] });
  let bad = 0, und = 0;
  for (let i = 0; i < sb.length; i++) {
    if (s.ops[0][i] !== pre.vwap[i]) bad++;
    if (pre.sd[i] >= 0.25) { if (s.ops[1][i] !== pre.vwap[i] + pre.sd[i]) bad++; } else if (s.ops[1][i] === s.ops[1][i]) und++;
  }
  ok(bad === 0, 'VWAP et VWAP + σ égales bit pour bit à sessionVwap (' + sb.length + ' barres)');
  ok(und === 0, 'σ inférieur à un tick : vwap avec k ≠ 0 indéfinie');
  const sb0 = sb.map(x => Object.assign({}, x, { v: 0 }));
  const s0 = E.op('series', { bars: sb0, spec: { anchor: 'globex' }, settings: SET, operands: [{ f: 'vwap' }] });
  let m = 0, ok0 = true; for (let i = 0; i < 30; i++) { m += (sb[i].h + sb[i].l + sb[i].c) / 3; if (Math.abs(s0.ops[0][i] - m / (i + 1)) > 1e-9) ok0 = false; }
  ok(ok0, 'séance de volume nul : poids égaux');
}
section('Opérandes : définitions à la main');
{
  // barres 0..59 : o = 100 + m/4, h = o + 1, l = o − 1, c = o + 0,5
  const over = {}; for (let m = 0; m < 60; m++) { const o = 100 + m / 4; over[m] = [o, o + 1, o - 1, o + 0.5]; }
  const b = bars(over, 60);
  const list = [{ f: 'sess', of: 'high' }, { f: 'sess', of: 'low' }, { f: 'sess', of: 'open' }, { f: 'hh', n: 3 }, { f: 'll', n: 3, of: { f: 'close' } },
    { f: 'or', from: '00:10', to: '00:20', of: 'high' }, { f: 'or', from: '00:10', to: '00:20', of: 'mid' }, { f: 'at', time: '00:30', of: 'close' }, { f: 'tf', m: 5, of: { f: 'close' } },
    { f: 'tf', m: 15, of: { f: 'high' } }, { f: 'body' }, { f: 'range', lag: 2 }, { f: 'sma', n: 4 }, { f: 'dist', a: { f: 'high' }, b: { f: 'low' }, unit: 'ticks' }, { f: 'rsi', n: 5 },
    { f: 'atr', n: 5 }, { f: 'sessmin' }, { f: 'time' }, { f: 'dow' }, { f: 'close', lag: 1 }, { f: 'hl2' }, { f: 'sd', n: 4 }];
  const s = E.op('series', { bars: b, spec: { anchor: 'globex' }, settings: SET, operands: list }), O = s.ops;
  ok(O[0][0] !== O[0][0] && O[0][5] === b[4].h && O[1][5] === b[0].l && O[2][7] === 100, 'sess : haut/bas jusqu’à i − 1 (NaN à la première barre), ouverture ancrée');
  ok(O[3][2] !== O[3][2] && O[3][10] === b[9].h, 'hh(3) : plus haut des barres i−3 … i−1, barre courante exclue');
  ok(O[4][10] === b[7].c, 'll(3) de close : plus bas de i−3 … i−1');
  ok(O[5][19] !== O[5][19] && O[5][20] === b[19].h && O[6][25] === (b[19].h + b[10].l) / 2, 'or 00:10–00:20 : NaN tant que le range n’est pas clos, puis haut et milieu');
  ok(O[7][29] !== O[7][29] && O[7][30] === b[30].c && O[7][59] === b[30].c, 'at 00:30 : NaN avant, puis la clôture de 00:30');
  ok(O[8][13] === b[9].c && O[8][14] === b[14].c && O[8][3] !== O[8][3], 'tf 5 : clôture de la dernière barre de 5 minutes close');
  ok(O[9][29] === b[29].h && O[9][31] === b[29].h && O[9][14] === b[14].h, 'tf 15 de high : plus haut de la dernière tranche close');
  ok(O[10][3] === 0.5 && O[11][5] === 2 && O[11][1] !== O[11][1], 'body = c − o ; range avec lag');
  near(O[12][10], (b[7].c + b[8].c + b[9].c + b[10].c) / 4, 1e-12, 'sma(4)');
  ok(O[13][4] === 8, 'dist en ticks : 2 points = 8 ticks');
  ok(O[14][10] === 100, 'rsi d’une série qui ne fait que monter = 100');
  near(O[15][10], 2, 1e-12, 'atr(5) : vrai range = max(h − l, |h − c₋₁|, |l − c₋₁|) = 2');
  ok(O[16][7] === 7 && O[17][7] === 7 && O[18][7] === 2, 'sessmin, minutes depuis minuit (Paris), jour de la clé (mardi = 2)');
  ok(O[19][0] !== O[19][0] && O[19][5] === b[4].c && O[20][3] === b[3].o, 'lag et hl2');
  near(O[21][10], Math.sqrt(((-0.375) ** 2 + (-0.125) ** 2 + 0.125 ** 2 + 0.375 ** 2) / 4), 1e-12, 'sd(4) de population');
  const flat = E.op('series', { bars: bars({}, 30), spec: { anchor: 'globex' }, settings: SET, operands: [{ f: 'rsi', n: 5 }, { f: 'vwap', k: 1 }, { f: 'dist', a: { f: 'close' }, b: { f: 'vwap' }, unit: 'sd' }, { f: 'hh', n: 50 }] });
  ok(flat.ops[0][20] === 50, 'rsi = 50 quand gains et pertes moyens sont nuls');
  ok(flat.ops[1][20] !== flat.ops[1][20] && flat.ops[2][20] !== flat.ops[2][20], 'σ nul (< 1 tick) : vwap ± kσ et dist en sd indéfinies');
  ok(flat.ops[3][20] !== flat.ops[3][20], 'hh sur un ensemble trop court : NaN');
  throws(() => E.op('series', { bars: b, spec: {}, operands: [{ op: '*', a: { f: 'close' }, b: 2 }] }), /Niveau/, 'niveau × nombre refusé');
  throws(() => E.op('series', { bars: b, spec: {}, operands: [{ op: '+', a: { f: 'close' }, b: { f: 'open' } }] }), /niveau/, 'niveau + niveau refusé');
  throws(() => E.op('series', { bars: b, spec: {}, operands: [{ f: 'zz' }] }), /inconnu/, 'opérande inconnu refusé');
}
section('Opérandes : niveaux nommés, plus proche, rvol, prev, nouvelles');
{
  const lat = E.lattice({ sessions: 6, sigma: 2, seed: 8, base: 20000 });
  const keys = lat.keys, lv = {};
  keys.forEach((k, j) => { lv[k] = { levels: { HVL: 19900 + j, CR: 20100 }, scale: 'NDX', base: 50 }; });
  lv[keys[5]] = { CR: 20100.5 };
  const s = E.op('series', { bars: lat, spec: {}, settings: SET, levels: lv, adj: { [keys[2]]: 3 }, operands: [{ f: 'level', name: 'HVL' }, { f: 'nearest', side: 'above' }, { f: 'nearest', side: 'below', names: ['HVL'] }, { f: 'rvol', n: 3 }, { f: 'prev', of: 'high' }, { f: 'prev', of: 'close', n: 2 }] });
  ok(s.ops[0][10] === 19950 && s.ops[0][1380 * 2 + 5] === 19900 + 2 + 50 + 3, 'niveau NDX + base + ajustement de la séance');
  ok(s.ops[0][1380 * 5] !== s.ops[0][1380 * 5], 'niveau absent ce jour-là : NaN');
  let nb = 0; for (let i = 0; i < 1380; i++) { const c = lat.c[i], up = [19950, 20150].filter(x => x > c).sort((x, y) => x - y)[0]; if (!same(s.ops[1][i], up === undefined ? NaN : up)) nb++; }
  ok(nb === 0, 'nearest above : le plus proche au-dessus de close[i]');
  ok([...Array(1380).keys()].every(i => same(s.ops[2][i], 19950 < lat.c[i] ? 19950 : NaN)), 'nearest below restreint aux noms donnés');
  const i3 = 1380 * 3 + 100, rv = lat.v[i3] / ((lat.v[100] + lat.v[1380 + 100] + lat.v[2760 + 100]) / 3);
  near(s.ops[3][i3], rv, 1e-12, 'rvol(3) : volume ÷ moyenne à la même minute des 3 séances précédentes');
  ok(s.ops[3][50] !== s.ops[3][50], 'rvol sans séance précédente : NaN');
  let hi = -Infinity; for (let i = 0; i < 1380; i++) hi = Math.max(hi, lat.h[i]);
  ok(s.ops[4][1380 + 7] === hi && s.ops[4][7] !== s.ops[4][7], 'prev high = plus haut de la séance précédente');
  ok(s.ops[5][2760 + 7] === lat.c[1379], 'prev close n = 2');
  // séance courte : elle est sautée par prev, et le saut est compté
  const cut = { t: [], o: [], h: [], l: [], c: [], v: [] };
  for (let i = 0; i < lat.t.length; i++) { if (i >= 1380 + 600 && i < 2760) continue; ['t', 'o', 'h', 'l', 'c', 'v'].forEach(k => cut[k].push(lat[k][i])); }
  const sc = E.op('series', { bars: cut, spec: {}, settings: SET, operands: [{ f: 'prev', of: 'close' }] });
  ok(sc.ops[0][600 + 1380 + 5] === lat.c[1379], 'prev saute une séance de moins de 80 % des barres attendues');
  ok(sc.warnings.some(w => /80 %/.test(w)), 'le saut figure dans warnings');
  // nouvelles : aucune publication d’impact ≥ 2 dans [t − 5 min, t + 10 min], t = clôture de la barre
  const tN = lat.t[200] + 30 * 1000;
  const sn = E.op('series', { bars: lat, spec: {}, settings: SET, news: [{ t: tN, impact: 2 }, { t: lat.t[600], impact: 1 }], conds: [{ news: { impact: 2, before: 5, after: 10 } }] });
  const nc = sn.conds[0];
  ok(nc[189] === 1 && nc[190] === 0 && nc[204] === 0 && nc[205] === 1, 'news : fausse de 10 min avant à 5 min après la publication');
  ok(nc[600] === 1, 'news : impact inférieur ignoré');
}
section('Conditions : logique, for, within, touch, reject, break');
{
  const over = { 5: [100, 101, 99.5, 100.5], 6: [100.5, 101.5, 99, 101], 7: [101, 101, 100.5, 100.75], 8: [100.75, 102, 100.5, 101.75] };
  const b = bars(over, 20);
  const conds = [{ bar: 'up' }, { for: 2, cond: { bar: 'up' } }, { within: 3, cond: { bar: 'down' } }, { touch: 100.5, from: 'above' }, { reject: 100.5, from: 'above' },
    { break: 101.5, dir: 'up' }, { not: { bar: 'up' } }, { all: [{ bar: 'up' }, { cmp: '>', a: { f: 'close' }, b: 101 }] }, { any: [{ bar: 'down' }, { cmp: '>', a: { f: 'vwap', k: 2 }, b: 0 }] }, { time: ['00:06', '00:08'] }];
  const s = E.op('series', { bars: b, spec: {}, settings: SET, conds }), C = s.conds;
  ok(C[0][5] === 1 && C[0][7] === 0 && C[0][3] === 0, 'bar up');
  ok(C[1][6] === 1 && C[1][5] === 0 && C[1][8] === 0, 'for 2 : vraie sur les 2 dernières barres');
  ok(C[2][7] === 1 && C[2][9] === 1 && C[2][10] === 0, 'within 3 : vraie si au moins une des 3 dernières');
  ok(C[3][7] === 1 && C[3][6] === 0, 'touch above : low ≤ L et close[i−1] > L');
  ok(C[4][7] === 1, 'reject above : touché et clôture revenue au-dessus');
  ok(C[5][8] === 1 && C[5][6] === 0, 'break up : close > L et close[i−1] ≤ L');
  ok(C[6][5] === 0 && C[6][7] === 1, 'not');
  ok(C[7][6] === 0 && C[7][8] === 1, 'all');
  ok(C[8][7] === 1 && C[8][5] === 2, 'any : un opérande indéfini rend la condition indéfinie (2) quand rien n’est vrai');
  ok(C[9][6] === 1 && C[9][7] === 1 && C[9][8] === 0, 'time : sessmin dans [00:06, 00:08)');
}

/* =================================== Causalité =================================== */
section('Causalité : modifier les barres après i ne change rien jusqu’à i');
{
  const lat = E.lattice({ sessions: 26, sigma: 2, seed: 21 }), alt = E.lattice({ sessions: 26, sigma: 3, seed: 22, base: 20500 });
  const lv = {}; lat.keys.forEach((k, j) => { lv[k] = { A: 20000 + 7 * j, B: 19990 - 3 * j }; });
  const news = [{ t: lat.t[1380 * 24 + 700], impact: 3 }];
  const ops = [{ f: 'or', from: '15:00', to: '15:30', tz: 'Europe/Paris', of: 'high' }, { f: 'or', from: '09:00', to: '09:30', tz: 'America/New_York', of: 'mid' },
    { f: 'tf', m: 5, of: { f: 'close' } }, { f: 'tf', m: 15, of: { f: 'sma', n: 4 } }, { f: 'tf', m: 60, of: { f: 'high' } }, { f: 'tf', m: 30, of: { f: 'rsi', n: 5 } },
    { f: 'rvol', n: 5 }, { f: 'prev', of: 'high' }, { f: 'prev', of: 'close', n: 2 }, { f: 'at', time: '09:00', tz: 'America/New_York', of: 'close' },
    { f: 'vwap' }, { f: 'vwap', k: -1.5 }, { f: 'sma', n: 30 }, { f: 'ema', n: 20 }, { f: 'hh', n: 15 }, { f: 'll', n: 15 }, { f: 'sd', n: 20 }, { f: 'atr', n: 14 }, { f: 'rsi', n: 14 },
    { f: 'sess', of: 'high' }, { f: 'sess', of: 'low' }, { f: 'dist', a: { f: 'close' }, b: { f: 'vwap' }, unit: 'sd' }, { f: 'nearest', side: 'above' }, { f: 'sessmin' }, { f: 'volume', lag: 3 }];
  const conds = [{ cross: 'up', a: { f: 'close' }, b: { f: 'vwap' } }, { touch: { f: 'vwap', k: -1 }, from: 'above' }, { reject: { f: 'prev', of: 'low' }, from: 'above' },
    { break: { f: 'or', from: '09:00', to: '09:30', tz: 'America/New_York', of: 'high' }, dir: 'up' }, { for: 3, cond: { bar: 'up' } }, { within: 6, cond: { cross: 'down', a: { f: 'ema', n: 5 }, b: { f: 'tf', m: 15, of: { f: 'close' } } } }, { news: { impact: 2, before: 30, after: 30 } }];
  const spec = mk({ trigger: { all: [{ cross: 'up', a: { f: 'close' }, b: { f: 'vwap' } }, { cmp: '>', a: { f: 'rvol', n: 5 }, b: 0.8 }] }, setup: [{ cmp: '>', a: { f: 'close' }, b: { f: 'tf', m: 15, of: { f: 'ema', n: 3 } } }] });
  const base = E.op('series', { bars: lat, spec, settings: SET, levels: lv, news, operands: ops, conds });
  const S = 1380 * 24, cuts = [S + 4, S + 14, S + 59, S + 899, S + 929, S + 935, S + 1379, S + 1380 + 2];
  let bad = 0, where = '';
  cuts.forEach(i => {
    const m = { t: lat.t, o: Float64Array.from(lat.o), h: Float64Array.from(lat.h), l: Float64Array.from(lat.l), c: Float64Array.from(lat.c), v: Float64Array.from(lat.v) };
    for (let j = i + 1; j < lat.t.length; j++) { m.o[j] = alt.o[j]; m.h[j] = alt.h[j]; m.l[j] = alt.l[j]; m.c[j] = alt.c[j]; m.v[j] = alt.v[j] * 3; }
    const r = E.op('series', { bars: m, spec, settings: SET, levels: lv, news, operands: ops, conds });
    for (let q = 0; q < ops.length; q++) for (let j = 0; j <= i; j++) if (!same(r.ops[q][j], base.ops[q][j])) { bad++; where = where || ('opérande ' + JSON.stringify(ops[q]) + ' barre ' + j + ' coupe ' + i); break; }
    for (let q = 0; q < conds.length; q++) for (let j = 0; j <= i; j++) if (r.conds[q][j] !== base.conds[q][j]) { bad++; where = where || ('condition ' + q + ' barre ' + j); break; }
    for (let j = 0; j <= i; j++) if (r.sig.L[j] !== base.sig.L[j]) { bad++; where = where || ('signal barre ' + j); break; }
  });
  ok(bad === 0, 'aucune série ni aucun signal ≤ i ne dépend des barres après i (or à 15 h de l’ancre, tf, rvol, prev, at…) ' + where);
  let orv = 0; for (let j = S; j < S + 1380; j++) if (base.ops[0][j] === base.ops[0][j]) orv++;
  ok(orv === 1380 - 930, 'or 15:00–15:30 Paris (15 h après l’ancre) défini à partir de 15:30 seulement');
}

/* =================================== Miroir =================================== */
const K = 40000;
const OPERANDS = [
  [{ f: 'close' }, 'n'], [{ f: 'open' }, 'n'], [{ f: 'high' }, 'n'], [{ f: 'low', lag: 2 }, 'n'], [{ f: 'hl2' }, 'n'], [{ f: 'hlc3' }, 'n'],
  [{ f: 'volume' }, 'u'], [{ f: 'range', lag: 1 }, 'u'], [{ f: 'body' }, 'e'], [{ f: 'body', lag: 1 }, 'e'],
  [{ f: 'vwap' }, 'n'], [{ f: 'vwap', k: 1.5 }, 'n'], [{ f: 'vwap', k: -1 }, 'n'],
  [{ f: 'sma', n: 10 }, 'n'], [{ f: 'ema', n: 8, of: { f: 'high' } }, 'n'], [{ f: 'sma', n: 5, of: { f: 'body' } }, 'e'], [{ f: 'ema', n: 5, of: { f: 'rsi', n: 14 } }, 'o'],
  [{ f: 'hh', n: 10 }, 'n'], [{ f: 'll', n: 10 }, 'n'], [{ f: 'hh', n: 5, of: { f: 'close' } }, 'n'], [{ f: 'll', n: 5, of: { f: 'body' } }, 'e'], [{ f: 'hh', n: 5, of: { f: 'rsi', n: 14 } }, 'o'], [{ f: 'hh', n: 5, of: { f: 'volume' } }, 'u'],
  [{ f: 'sd', n: 20 }, 'u'], [{ f: 'sd', n: 10, of: { f: 'high' } }, 'u'], [{ f: 'atr', n: 14 }, 'u'], [{ f: 'atr', n: 14, lag: 1 }, 'u'], [{ f: 'rsi', n: 14 }, 'o'], [{ f: 'rsi', n: 7, lag: 1 }, 'o'],
  [{ f: 'rvol', n: 3 }, 'u'], [{ f: 'prev', of: 'high' }, 'n'], [{ f: 'prev', of: 'low', n: 2 }, 'n'], [{ f: 'prev', of: 'open' }, 'n'], [{ f: 'prev', of: 'close' }, 'n'],
  [{ f: 'sess', of: 'high' }, 'n'], [{ f: 'sess', of: 'low' }, 'n'], [{ f: 'sess', of: 'open' }, 'n'],
  [{ f: 'or', from: '01:00', to: '01:30', of: 'high' }, 'n'], [{ f: 'or', from: '01:00', to: '01:30', of: 'low' }, 'n'], [{ f: 'or', from: '01:00', to: '01:30', of: 'mid' }, 'n'], [{ f: 'or', from: '01:00', to: '01:30', of: 'open' }, 'n'], [{ f: 'or', from: '01:00', to: '01:30', of: 'close' }, 'n'],
  [{ f: 'at', time: '02:00', of: 'open' }, 'n'], [{ f: 'at', time: '02:00', of: 'close' }, 'n'],
  [{ f: 'tf', m: 5, of: { f: 'high' } }, 'n'], [{ f: 'tf', m: 15, of: { f: 'close' } }, 'n'], [{ f: 'tf', m: 60, of: { f: 'rsi', n: 14 } }, 'o'], [{ f: 'tf', m: 30, of: { f: 'body' } }, 'e'], [{ f: 'tf', m: 5, of: { f: 'vwap', k: 1 } }, 'n'],
  [{ f: 'level', name: 'A' }, 'n'], [{ f: 'nearest', side: 'above' }, 'n'], [{ f: 'nearest', side: 'below', names: ['A', 'B'] }, 'n'],
  [{ f: 'time' }, 'u'], [{ f: 'dow' }, 'u'], [{ f: 'sessmin' }, 'u'],
  [{ f: 'dist', a: { f: 'close' }, b: { f: 'vwap' }, unit: 'pts' }, 'e'], [{ f: 'dist', a: { f: 'high' }, b: { f: 'sma', n: 10 }, unit: 'ticks' }, 'e'], [{ f: 'dist', a: { f: 'close' }, b: { f: 'prev', of: 'high' }, unit: 'atr', n: 14 }, 'e'], [{ f: 'dist', a: { f: 'low' }, b: { f: 'vwap' }, unit: 'sd' }, 'e'],
  [{ op: '+', a: { f: 'close' }, b: { f: 'atr', n: 14 } }, 'n'], [{ op: '-', a: { f: 'vwap' }, b: 3 }, 'n'], [{ op: '+', a: 2, b: { f: 'low' } }, 'n'], [{ op: '-', a: { f: 'high' }, b: { f: 'low' } }, 'e'],
  [{ op: '+', a: { f: 'close' }, b: { f: 'body' } }, 'n'], [{ op: '-', a: { f: 'close' }, b: { f: 'body' } }, 'n'], [{ op: '*', a: { f: 'body' }, b: 2 }, 'e'], [{ op: '/', a: { f: 'range' }, b: { f: 'atr', n: 14 } }, 'u'], [{ op: '-', a: { f: 'body' }, b: 0.5 }, 'e'], [{ op: '+', a: { f: 'sma', n: 5, of: { f: 'body' } }, b: { f: 'body' } }, 'e']
];
const CONDS = [
  { cmp: '>', a: { f: 'close' }, b: { f: 'vwap' } }, { cmp: '<=', a: { f: 'low' }, b: { f: 'vwap', k: -1 } }, { cmp: '>=', a: { f: 'close' }, b: { f: 'sma', n: 20 } }, { cmp: '<', a: { f: 'high' }, b: { f: 'prev', of: 'high' } },
  { cmp: '>', a: { f: 'body' }, b: 0.5 }, { cmp: '<', a: { f: 'dist', a: { f: 'close' }, b: { f: 'vwap' }, unit: 'sd' }, b: -1 }, { cmp: '>', a: { f: 'body' }, b: { op: '*', a: { f: 'body', lag: 1 }, b: 2 } }, { cmp: '<', a: 1, b: { f: 'body' } },
  { cmp: '<', a: { f: 'rsi', n: 14 }, b: 30 }, { cmp: '>', a: { f: 'rsi', n: 14 }, b: { f: 'ema', n: 5, of: { f: 'rsi', n: 14 } } }, { cmp: '>', a: 70, b: { f: 'rsi', n: 14 } },
  { cmp: '>', a: { f: 'atr', n: 14 }, b: 1 }, { cmp: '>', a: { f: 'rvol', n: 3 }, b: 1.5 }, { cmp: '>', a: { f: 'range' }, b: { f: 'atr', n: 14 } },
  { cross: 'up', a: { f: 'close' }, b: { f: 'vwap' } }, { cross: 'down', a: { f: 'ema', n: 5 }, b: { f: 'sma', n: 20 } }, { cross: 'up', a: { f: 'rsi', n: 14 }, b: 50 }, { cross: 'up', a: { f: 'body' }, b: 0 },
  { touch: { f: 'vwap', k: -1 }, from: 'above' }, { touch: { f: 'sess', of: 'high' }, from: 'below' }, { reject: { f: 'prev', of: 'low' }, from: 'above' }, { reject: { f: 'level', name: 'A' }, from: 'below' },
  { break: { f: 'or', from: '01:00', to: '01:30', of: 'high' }, dir: 'up' }, { break: { f: 'hh', n: 20 }, dir: 'up' }, { break: { f: 'level', name: 'B' }, dir: 'down' }, { touch: { f: 'nearest', side: 'below' }, from: 'above' }, { break: { op: '+', a: { f: 'vwap' }, b: { f: 'atr', n: 14 } }, dir: 'up' },
  { bar: 'up' }, { bar: 'down' }, { time: ['01:00', '03:00'] }, { news: { impact: 2, before: 5, after: 10 } },
  { all: [{ bar: 'up' }, { cmp: '>', a: { f: 'close' }, b: { f: 'vwap' } }] }, { any: [{ bar: 'down' }, { cross: 'up', a: { f: 'close' }, b: { f: 'tf', m: 5, of: { f: 'close' } } }] },
  { not: { cmp: '<', a: { f: 'rsi', n: 14 }, b: 40 } }, { for: 3, cond: { bar: 'up' } }, { within: 5, cond: { cross: 'up', a: { f: 'close' }, b: { f: 'vwap' } } }
];
section('Miroir : chaque forme reflétée sur la série réelle = la forme sur la série réfléchie');
{
  const lat = E.lattice({ sessions: 12, sigma: 2, seed: 31 }), rl = reflectCols(lat, K);
  const lv = {}, lvR = {};
  lat.keys.forEach((k, j) => { lv[k] = { A: 20000 + 5 * j, B: 19980 - 4 * j, C: 20020.5 }; lvR[k] = { A: K - lv[k].A, B: K - lv[k].B, C: K - lv[k].C }; });
  const news = [{ t: lat.t[3000], impact: 3 }, { t: lat.t[9000], impact: 1 }];
  const mirrored = OPERANDS.map(x => E.op('mirror', { operand: x[0] }));
  const real = E.op('series', { bars: lat, spec: {}, settings: SET, levels: lv, news, operands: mirrored });
  const refl = E.op('series', { bars: rl, spec: {}, settings: SET, levels: lvR, news, operands: OPERANDS.map(x => x[0]) });
  let badOps = [];
  OPERANDS.forEach((x, q) => {
    const A = refl.ops[q], B = real.ops[q], cls = x[1];
    let defined = 0;
    for (let i = 0; i < A.length; i++) {
      const want = cls === 'n' ? K - B[i] : cls === 'e' ? -B[i] : cls === 'o' ? 100 - B[i] : B[i];
      if (A[i] === A[i]) defined++;
      if (!(same(A[i], want) || Math.abs(A[i] - want) <= 1e-7 * Math.max(1, Math.abs(want)))) { badOps.push(JSON.stringify(x[0]) + ' @' + i + ' ' + A[i] + ' ≠ ' + want); return; }
    }
    if (defined < 100) badOps.push(JSON.stringify(x[0]) + ' : trop peu de valeurs définies (' + defined + ')');
  });
  ok(badOps.length === 0, OPERANDS.length + ' formes d’opérande : niveau → K − x, écart → −x, oscillateur → 100 − x, neutre inchangé ' + badOps.slice(0, 3).join(' | '));
  const mc = CONDS.map(c => E.op('mirror', { cond: c }));
  const rc = E.op('series', { bars: lat, spec: {}, settings: SET, levels: lv, news, conds: mc });
  const fc = E.op('series', { bars: rl, spec: {}, settings: SET, levels: lvR, news, conds: CONDS });
  const badC = [];
  CONDS.forEach((c, q) => {
    let diff = 0, t1 = 0; for (let i = 0; i < rc.conds[q].length; i++) { if (rc.conds[q][i] !== fc.conds[q][i]) diff++; if (fc.conds[q][i] === 1) t1++; }
    if (diff) badC.push(JSON.stringify(c) + ' : ' + diff + ' barres');
    if (!t1) badC.push(JSON.stringify(c) + ' : jamais vraie');
  });
  ok(badC.length === 0, CONDS.length + ' formes de condition, barre par barre ' + badC.slice(0, 3).join(' | '));
  const m1 = E.op('mirror', { cond: { cmp: '<', a: { f: 'rsi', n: 14 }, b: 30 } });
  ok(m1.cmp === '>' && m1.b === 70, 'oscillateur contre constante : comparaison inversée, x → 100 − x');
  const m2 = E.op('mirror', { cond: { cmp: '>', a: { f: 'dist', a: { f: 'close' }, b: { f: 'vwap' }, unit: 'pts' }, b: 3 } });
  ok(m2.cmp === '<' && m2.b === -3 && m2.a.a.f === 'close', 'écart contre constante : dist(a, b) > x → dist(a′, b′) < −x');
  const m3 = E.op('mirror', { rule: { setup: [], trigger: { touch: { f: 'vwap', k: -2 }, from: 'above' }, entry: { type: 'limit', at: { f: 'low' }, offset: 2 }, stop: { type: 'swing', n: 5, buffer: 2 }, target: { type: 'level', at: { f: 'prev', of: 'high' } } } });
  ok(m3.trigger.touch.k === 2 && m3.trigger.from === 'below' && m3.entry.at.f === 'high' && m3.entry.offset === 2 && m3.target.at.of === 'low', 'règle entière : déclencheur, entrée et objectif reflétés (le décalage garde son signe, le sens l’applique)');
  throws(() => E.op('mirror', { cond: { cmp: '>', a: { f: 'close' }, b: 20000 } }), /constante/, 'niveau contre constante : miroir refusé');
  ok(E.mirror({ cross: 'up', a: { f: 'close' }, b: { f: 'vwap' } }).cross === 'down' && E.mirror({ f: 'hh', n: 3 }).f === 'll' && E.mirror(m3.trigger ? { trigger: { bar: 'up' }, stop: { type: 'pts', value: 1 } } : null).trigger.bar === 'down', 'enveloppe mirror : condition, opérande, règle devinés');
  ok(E.mirror({ params: { k: { v: 2 } }, long: { trigger: { touch: { f: 'vwap', k: '$k' }, from: 'above' }, stop: { type: 'pts', value: 1 } } }).trigger.touch.k === -2, 'enveloppe mirror : spec résolue puis reflétée');
  throws(() => E.op('mirror', { cond: { cmp: '>', a: { f: 'body' }, b: { f: 'atr', n: 14 } } }), /écart/, 'écart contre neutre : miroir refusé');
  throws(() => E.op('mirror', { cond: { cmp: '>', a: { f: 'body' }, b: '$p' } }), /résolution/, 'miroir avant résolution refusé');
  throws(() => run(lat, mk({ side: 'both', trigger: { cmp: '>', a: { f: 'close' }, b: 20000 } })), /Miroir impossible/, 'une stratégie both qui compare un niveau à une constante est refusée');
}
section('Miroir : une stratégie both sur une série et sur sa réflexion rend les mêmes trades, de sens opposés');
{
  const lat = E.lattice({ sessions: 21, sigma: 2, seed: 41 }), rl = reflectCols(lat, K);
  const specs = [
    mk({ side: 'both', fill: 'chemin', session: { warmup: 15 }, setup: [{ cmp: '<', a: { f: 'close' }, b: { f: 'vwap' } }], trigger: { all: [{ cmp: '<=', a: { f: 'low' }, b: { f: 'vwap', k: -1 } }, { cmp: '>', a: { f: 'close' }, b: { f: 'vwap', k: -1 } }] },
      stop: { type: 'level', at: { f: 'vwap', k: -1 }, buffer: 8 }, target: { type: 'level', at: { f: 'vwap' }, dynamic: true }, risk: { maxPerSession: 0, cooldown: 1 }, costs: { slipTicks: 1, commissionRT: 1 } }),
    mk({ side: 'both', fill: 'vrai', session: { warmup: 30 }, trigger: { cross: 'up', a: { f: 'close' }, b: { f: 'ema', n: 20 } }, entry: { type: 'limit', at: { f: 'close' }, offset: 2, valid: 3 },
      stop: { type: 'swing', n: 10, buffer: 2 }, target: { type: 'r', value: 2 }, manage: { breakeven: 1, trail: { type: 'atr', value: 2, n: 14, start: 1.5 } }, risk: { mode: 'risk', riskUsd: 200, maxPerSession: 0 }, costs: { slipTicks: 1 } }),
    mk({ side: 'both', fill: 'pessimiste', session: { warmup: 30 }, trigger: { break: { f: 'hh', n: 20 }, dir: 'up' }, entry: { type: 'stop', at: { f: 'high' }, offset: 1, valid: 2 },
      stop: { type: 'atr', value: 1.5, n: 14 }, target: { type: 'atr', value: 3, n: 14 }, manage: { maxBars: 30, exitOnOpposite: true }, risk: { maxPerSession: 0 }, costs: { slipTicks: 2 } })
  ];
  specs.forEach((spec, q) => {
    const a = run(lat, spec, { sel: { from: lat.keys[1] } }), b = run(rl, spec, { sel: { from: lat.keys[1] } });
    let bad = 0;
    if (a.trades.length !== b.trades.length) bad++;
    else a.trades.forEach((x, k) => { const y = b.trades[k]; if (x.i !== y.i || x.e !== y.e || x.j !== y.j || x.side !== -y.side || x.fin !== y.fin || x.qty !== y.qty || Math.abs(x.pnl - y.pnl) > 1e-9 || Math.abs(x.entry - (K - y.entry)) > 1e-9) bad++; });
    const sides = new Set(a.trades.map(t => t.side));
    ok(bad === 0 && a.trades.length > 20 && sides.size === 2, 'stratégie ' + (q + 1) + ' (' + spec.fill + ') : ' + a.trades.length + ' trades appariés, sens opposés, même P&L');
    ok(JSON.stringify(a.counts) === JSON.stringify(b.counts), 'stratégie ' + (q + 1) + ' : mêmes compteurs');
  });
}

/* =================================== Exécution =================================== */
section('Exécution : entrée au marché');
{
  const b = bars({ 11: [100, 100.5, 99.5, 100], 12: [100, 104.5, 99.75, 104] });
  const t = one(run(b, mk()));
  ok(t && t.i === 10 && t.e === 11 && t.j === 12 && t.entry === 100 && t.stop0 === 98 && t.target0 === 104 && t.exit === 104 && t.fin === 'objectif', 'signal à la clôture de 10, entrée à l’ouverture de 11, objectif à 104');
  ok(t && t.pnl === 8 && t.r === 2 && t.qty === 1 && t.bars === 2 && t.c === 0, 'P&L 4 pts × 2 $ = 8 $, r = 2');
  const s = one(run(b, mk({ costs: { slipTicks: 1, commissionRT: 1 } })));
  // entrée 100,25 ; stop 98,25 ; objectif 104,25 (atteint) ; c = 1 + 0,25·2·1 jambe = 1,5
  ok(s && s.entry === 100.25 && s.stop0 === 98.25 && s.exit === 104.25 && s.legs === 1 && s.c === 1.5, 'glissement d’un tick sur l’entrée au marché, aucun sur l’objectif');
  near(s.pnl, 4 * 2 - 1, 1e-12, 'pnl = qty·(pts·pv − commission)');
  near(s.r, 7 / 4, 1e-12, 'r = pnl / (qty·L·pv)');
  ok(s.mae === 0.75 && s.mfe === 4, 'MAE 0,75 (100,25 → 99,5) et MFE 4 (bornée par l’objectif)');
  ok(s.hour === 0 && s.dow === 2 && s.key === '2026-01-06', 'heure (fuseau de la séance), jour et clé');
}
section('Exécution : entrée limite, marketable, through, expiration');
{
  const lim = { type: 'limit', at: { f: 'close' }, offset: 4, valid: 2 };
  const b = bars({ 11: [100, 100.25, 98.75, 99.5], 12: [99.5, 103.25, 99, 103] });
  const t = one(run(b, mk({ entry: lim })));
  ok(t && t.e === 11 && t.entry === 99 && t.stop0 === 97 && t.target0 === 103 && t.exit === 103 && t.j === 12 && t.legs === 0, 'limite à close − 4 ticks = 99, remplie au prix, sans glissement');
  const s1 = one(run(b, mk({ entry: lim, costs: { slipTicks: 1 } })));
  ok(s1 && s1.entry === 99 && s1.c === 0, 'pas de glissement sur une limite ni sur l’objectif');
  const b2 = bars({ 11: [100, 100.25, 99, 99.5], 12: [99.5, 103.25, 99, 103] });
  ok(one(run(b2, mk({ entry: lim }))).entry === 99, 'low = prix limite : remplie (≤)');
  const r2 = run(b2, mk({ entry: Object.assign({ through: true }, lim) }));
  ok(r2.trades.length === 0 && r2.counts.expire === 1, 'through : low = prix ne suffit pas (<), l’ordre expire après 2 barres');
  const mkt = run(b, mk({ entry: { type: 'limit', at: { op: '+', a: { f: 'close' }, b: 1 }, offset: 0, valid: 2 }, costs: { slipTicks: 1 } }));
  const m = one(mkt);
  ok(m && m.entry === 100.25 && m.mk === 1 && mkt.counts.marketable === 1 && m.legs === 2 && m.fin === 'cloche', 'achat limite à 101 ≥ ouverture 100 : marketable, exécuté au marché, glissement compris');
  const b3 = bars({ 11: [100, 100.25, 99.25, 99.5], 12: [98.5, 99, 98, 98.75] });
  const g = one(run(b3, mk({ entry: Object.assign({}, lim, { valid: 3 }) })));
  ok(g && g.e === 12 && g.entry === 98.5 && g.stop0 === 96.5, 'limite active sur plusieurs barres : ouverture déjà sous le prix → remplie à l’ouverture');
  const ex = run(bars({}), mk({ entry: lim }));
  ok(ex.trades.length === 0 && ex.counts.expire === 1 && ex.counts.signals === 1, 'jamais touchée : expire');
  const vt = run(bars({ 12: [100, 100.25, 98.75, 99.5] }), mk({ entry: Object.assign({}, lim, { valid: '00:12' }) }));
  ok(vt.trades.length === 0 && vt.counts.expire === 1, 'validité en heure : active jusqu’à 00:12 exclu');
  const vt2 = run(bars({ 12: [100, 100.25, 98.75, 99.5] }), mk({ entry: Object.assign({}, lim, { valid: '00:13' }) }));
  ok(vt2.trades.length === 1 && vt2.trades[0].e === 12, 'validité en heure : remplie à 00:12 si l’ordre vit jusqu’à 00:13');
}
section('Exécution : entrée stop');
{
  const stp = { type: 'stop', at: { f: 'close' }, offset: 4, valid: 2 };
  const t = one(run(bars({ 11: [100, 101.5, 99.75, 101.25], 12: [101.25, 105.25, 101, 105] }), mk({ entry: stp, costs: { slipTicks: 1 } })));
  ok(t && t.entry === 101.25 && t.stop0 === 99.25 && t.legs === 1, 'achat stop à 101 : rempli à max(ouverture, prix) + glissement');
  const g = one(run(bars({ 11: [101.5, 102, 101.25, 101.75] }), mk({ entry: stp, manage: { maxBars: 1 } })));
  ok(g && g.entry === 101.5, 'ouverture au-dessus du prix : rempli à l’ouverture');
  const ex = run(bars({}), mk({ entry: stp }));
  ok(ex.trades.length === 0 && ex.counts.expire === 1, 'jamais atteint : expire');
}
section('Exécution : stops');
{
  const base = bars({}, 60, 100, [100, 100.5, 99.5, 100]);   // vrai range 1 partout : ATR = 1
  const st = s => one(run(base, mk({ stop: s, target: { type: 'pts', value: 10 }, manage: { maxBars: 1 } })));
  ok(st({ type: 'pts', value: 2 }).stop0 === 98, 'pts');
  ok(st({ type: 'atr', value: 2, n: 5 }).stop0 === 98, 'atr : 2 × ATR(5) de la barre du signal');
  const sw = bars({ 9: [100, 100.5, 97, 100] }, 60, 100, [100, 100.5, 99.5, 100]);
  ok(one(run(sw, mk({ stop: { type: 'swing', n: 3, buffer: 2 }, manage: { maxBars: 1 } }))).stop0 === 96.5, 'swing : plus bas des 3 dernières barres (signal compris) moins 2 ticks');
  ok(one(run(sw, mk({ stop: { type: 'swing', n: 1 }, manage: { maxBars: 1 } }))).stop0 === 99.5, 'swing n = 1 : la barre du signal seule');
  ok(st({ type: 'level', at: { f: 'low' }, buffer: 4 }).stop0 === 98.5, 'level : bas de la barre du signal moins 4 ticks');
  const sc = run(base, mk({ stop: { type: 'pts', value: 0.5 }, risk: { minStopTicks: 4 } }));
  ok(sc.trades.length === 0 && sc.counts.stopcourt === 1, 'distance < minStopTicks : annulé (stopcourt)');
  const ec = run(base, mk({ stop: { type: 'level', at: { f: 'high' } } }));
  ok(ec.trades.length === 0 && ec.counts.ecart === 1, 'exécution déjà au-delà du stop : annulé (ecart)');
  const an = run(base, mk({ stop: { type: 'atr', value: 2, n: 50 } }));
  ok(an.trades.length === 0 && an.counts.annule === 1, 'stop indéfini (ATR sans historique) : annulé');
}
section('Exécution : objectifs');
{
  const base = bars({}, 60, 100, [100, 100.5, 99.5, 100]);
  const tg = x => one(run(base, mk({ stop: { type: 'pts', value: 2 }, target: x, manage: { maxBars: 1 } })));
  ok(tg({ type: 'r', value: 1.5 }).target0 === 103, 'r : 1,5 × risque');
  ok(tg({ type: 'pts', value: 3 }).target0 === 103, 'pts');
  ok(tg({ type: 'atr', value: 3, n: 5 }).target0 === 103, 'atr');
  ok(tg({ type: 'level', at: { op: '+', a: { f: 'close' }, b: 3 } }).target0 === 103, 'level statique');
  const nn = tg({ type: 'none' }); ok(nn.target0 === null && nn.fin === 'temps', 'none : pas d’objectif');
  const an = run(base, mk({ target: { type: 'level', at: { op: '-', a: { f: 'close' }, b: 1 } } }));
  ok(an.trades.length === 0 && an.counts.annule === 1, 'objectif déjà dépassé à l’exécution : annulé');
  const dyn = bars({ 11: [100, 100.5, 99.5, 101], 12: [101, 103.5, 100.5, 100.5], 13: [100.5, 103.75, 100, 103.5] });
  const d1 = one(run(dyn, mk({ target: { type: 'level', at: { op: '+', a: { f: 'close' }, b: 3 }, dynamic: true } })));
  ok(d1 && d1.j === 13 && d1.exit === 103.5, 'level dynamique : close[j−1] + 3, réévalué à chaque barre (104 en 12, 103,5 en 13)');
  const d0 = one(run(dyn, mk({ target: { type: 'level', at: { op: '+', a: { f: 'close' }, b: 3 } } })));
  ok(d0 && d0.j === 12 && d0.exit === 103, 'level statique : 103 atteint en 12');
  const thr = { type: 'limit', at: { f: 'close' }, offset: 4, valid: 1 };
  const bt = bars({ 11: [100, 100.25, 98.75, 99.5], 12: [99.5, 101, 99.25, 100.5], 13: [100.5, 101.25, 100.25, 101] });
  const t1 = one(run(bt, mk({ entry: thr, target: { type: 'pts', value: 2 } })));
  const t2 = one(run(bt, mk({ entry: Object.assign({ through: true }, thr), target: { type: 'pts', value: 2 } })));
  ok(t1 && t1.j === 12 && t1.exit === 101, 'objectif 101, high = 101 : rempli (≥)');
  ok(t2 && t2.j === 13 && t2.exit === 101, 'entrée through : l’objectif exige high > 101, rempli en 13');
}
section('Exécution : remplissage quand stop et objectif tombent dans la même barre (règle 3)');
{
  const cases = [
    ['haussière', [100, 102.5, 97.5, 101], { pessimiste: 'stop', optimiste: 'objectif', chemin: 'stop', v1: 'stop', v0: 'objectif' }],
    ['baissière', [100, 102.5, 97.5, 99], { pessimiste: 'stop', optimiste: 'objectif', chemin: 'objectif', v1: 'stop', v0: 'objectif' }],
    ['doji', [100, 102.5, 97.5, 100], { pessimiste: 'stop', optimiste: 'objectif', chemin: 'stop', v1: 'stop', v0: 'objectif' }]];
  cases.forEach(([nm, bar, want]) => {
    ['pessimiste', 'optimiste', 'chemin', 'v1', 'v0'].forEach(f => {
      const bb = bars({ 12: bar.concat(f === 'v1' ? [1] : f === 'v0' ? [0] : []) });
      const spec = mk({ fill: f[0] === 'v' ? 'vrai' : f, target: { type: 'pts', value: 2 }, costs: { slipTicks: 1 } });
      const t = one(run(bb, spec)), tR = one(run(reflectBars(bb, 200), Object.assign({}, spec, { side: 'short' })));
      ok(t && t.fin === want[f] && t.j === 12 && t.exit === (want[f] === 'stop' ? 98 : 102.25), 'achat, barre ' + nm + ', ' + f + ' → ' + want[f]);
      ok(tR && tR.fin === want[f] && tR.side === -1 && Math.abs(tR.pnl - t.pnl) < 1e-12, 'vente (miroir), barre ' + nm + ', ' + f + ' → ' + want[f]);
    });
  });
}
section('Exécution : barre d’entrée (table 3.6.4), les deux sens');
{
  const F = ['pessimiste', 'optimiste', 'chemin', 'v1', 'v0'];
  // achat limite à 99 (ouverture 100), stop 98, objectif 101 ; maxBars 1 : la barre d’entrée seule
  const L = [
    ['L1 haussière, stop et objectif', [100, 101.5, 97.5, 100.5], ['stop', 'objectif', 'stop', 'stop', 'stop']],
    ['L2 haussière, objectif seul', [100, 101.5, 98.5, 100.5], ['temps', 'objectif', 'objectif', 'objectif', 'temps']],
    ['L3 clôture au-delà de l’objectif', [100, 101.5, 98.5, 101.25], ['objectif', 'objectif', 'objectif', 'objectif', 'objectif']],
    ['L4 baissière, objectif seul', [100, 101.5, 98.5, 99.5], ['temps', 'objectif', 'temps', 'objectif', 'temps']]];
  // achat stop à 101 (ouverture 100), stop 99,5, objectif 103
  const S = [
    ['S1 haussière, stop et objectif', [100, 103.5, 99.25, 100.25], ['stop', 'objectif', 'objectif', 'objectif', 'objectif']],
    ['S2 haussière, stop seul, clôture au-dessus', [100, 102, 99.25, 101.5], ['stop', 'temps', 'temps', 'temps', 'stop']],
    ['S3 baissière, clôture au stop', [100, 102, 99.25, 99.5], ['stop', 'stop', 'stop', 'stop', 'stop']],
    ['S4 baissière, stop seul, clôture au-dessus', [100, 102, 99.25, 99.75], ['stop', 'temps', 'stop', 'temps', 'stop']]];
  const kinds = [[L, { type: 'limit', at: { f: 'close' }, offset: 4, valid: 1 }, { type: 'pts', value: 1 }], [S, { type: 'stop', at: { f: 'close' }, offset: 4, valid: 1 }, { type: 'pts', value: 1.5 }]];
  let n = 0;
  kinds.forEach(([rows, entry, stop]) => rows.forEach(([nm, bar, want]) => F.forEach((f, q) => {
    const bb = bars({ 11: bar.concat(f === 'v1' ? [1] : f === 'v0' ? [0] : []) });
    const spec = mk({ entry, stop, target: { type: 'pts', value: 2 }, fill: f[0] === 'v' ? 'vrai' : f, manage: { maxBars: 1 } });
    const t = one(run(bb, spec)), tR = one(run(reflectBars(bb, 200), Object.assign({}, spec, { side: 'short' })));
    ok(t && t.e === 11 && t.fin === want[q], nm + ', ' + f + ' : ' + (t && t.fin) + ' attendu ' + want[q]);
    ok(tR && tR.side === -1 && tR.fin === want[q] && Math.abs(tR.pnl - t.pnl) < 1e-12 && tR.entry === 200 - t.entry, nm + ', vente en miroir, ' + f);
    n++;
  })));
  ok(n === 40, 'quarante cas de la table');
}
section('Exécution : écarts d’ouverture, break-even, suiveur, maxBars, flat, cloche, signal opposé');
{
  const gs = one(run(bars({ 12: [97, 97.5, 96, 97] }), mk({ costs: { slipTicks: 1 } })));
  ok(gs && gs.j === 12 && gs.exit === 96.75 && gs.fin === 'stop' && gs.legs === 2, 'ouverture sous le stop : sortie à l’ouverture, glissement compris');
  const gt = one(run(bars({ 12: [105, 106, 104.5, 105.5] }), mk({ costs: { slipTicks: 1 } })));
  ok(gt && gt.exit === 105 && gt.fin === 'objectif' && gt.legs === 1, 'ouverture au-delà de l’objectif : sortie à l’ouverture, sans glissement');
  const beB = bars({ 12: [100, 102.25, 99.5, 101.5], 13: [101.5, 101.75, 99.75, 100.5] });
  const be = one(run(beB, mk({ target: { type: 'pts', value: 6 }, manage: { breakeven: 1 } })));
  ok(be && be.j === 13 && be.exit === 100 && be.fin === 'be', 'break-even : 1 R atteint en 12, stop à l’entrée pour 13 (pas pour 12, dont le bas touche 99,5)');
  const nobe = run(beB, mk({ target: { type: 'pts', value: 6 } }));
  ok(nobe.trades[0].fin === 'cloche', 'sans break-even, la position court jusqu’à la dernière barre');
  const beo = one(run(beB, mk({ target: { type: 'pts', value: 6 }, manage: { breakeven: { r: 1, offset: 1 } } })));
  ok(beo && beo.exit === 100.25 && beo.fin === 'be', 'break-even avec décalage d’un tick');
  const tr = one(run(bars({ 12: [100, 103, 99.5, 102.5], 13: [102.5, 103.5, 101.25, 102] }), mk({ target: { type: 'none' }, manage: { trail: { type: 'pts', value: 1.5, start: 1 } } })));
  ok(tr && tr.j === 13 && tr.exit === 101.5 && tr.fin === 'trail', 'suiveur après 1 R : stop = plus haut depuis l’entrée (103) − 1,5');
  const tr0 = one(run(bars({ 12: [100, 101.5, 99.5, 101], 13: [101, 101.25, 99.75, 100] }), mk({ target: { type: 'none' }, manage: { trail: { type: 'pts', value: 1.5, start: 1 } } })));
  ok(tr0 && tr0.fin === 'cloche', 'suiveur non armé avant 1 R');
  const mb = one(run(bars({ 13: [100, 100.5, 99.5, 100.75] }), mk({ manage: { maxBars: 3 }, costs: { slipTicks: 1 } })));
  ok(mb && mb.j === 13 && mb.fin === 'temps' && mb.exit === 100.5 && mb.bars === 3, 'maxBars 3 : sortie à la clôture de la 3e barre, glissement compris');
  const fl = one(run(bars({}), mk({ session: { to: '00:20', flat: '00:20' }, target: { type: 'none' } })));
  ok(fl && fl.j === 20 && fl.fin === 'flat' && fl.exit === 100, 'flat : sortie à l’ouverture de 00:20');
  const fl2 = one(run(bars({}), mk({ session: { to: '00:15', flat: '00:30' }, target: { type: 'none' } })));
  ok(fl2 && fl2.j === 30 && fl2.fin === 'flat', 'flat après la fin de la fenêtre : la position court jusqu’à flat');
  const cl = one(run(bars({ 29: [100, 100.5, 99.5, 100.25] }, 30), mk({ target: { type: 'none' }, costs: { slipTicks: 1 } })));
  ok(cl && cl.j === 29 && cl.fin === 'cloche' && cl.exit === 100, 'dernière barre des données : clôture, glissement compris');
  const opp = { all: [{ time: ['00:05', '00:40'] }, { bar: 'up' }] };
  const ob = bars({ 10: [100, 100.5, 99.75, 100.25], 15: [100.25, 100.5, 99.75, 100] });
  const op = one(run(ob, mk({ trigger: opp, target: { type: 'none' }, manage: { exitOnOpposite: true } })));
  ok(op && op.e === 11 && op.j === 16 && op.fin === 'oppose' && op.exit === 100, 'signal opposé à la clôture de 15 : sortie à l’ouverture de 16');
  const op0 = one(run(ob, mk({ trigger: opp, target: { type: 'none' } })));
  ok(op0 && op0.fin === 'cloche', 'sans exitOnOpposite, le signal opposé est ignoré');
}
section('Exécution : limites de séance, cooldown, taille au risque, compteurs');
{
  const two = bars({ 12: [100, 100, 97.5, 98] });
  const lim1 = run(bars({}), mk({ sig: [10, 20], manage: { maxBars: 1 }, risk: { maxPerSession: 1 } }));
  ok(lim1.trades.length === 1 && lim1.counts.limite === 1, 'maxPerSession 1 : le second signal n’entre pas');
  const ml = run(two, mk({ sig: [10, 20], risk: { maxLossesPerSession: 1 } }));
  ok(ml.trades.length === 1 && ml.trades[0].fin === 'stop', 'maxLossesPerSession 1 : plus d’entrée après une perte');
  ok(run(two, mk({ sig: [10, 20], risk: { dailyStopUsd: 3 } })).trades.length === 1, 'dailyStopUsd 3 $ : la perte de 4 $ arrête la séance');
  ok(run(two, mk({ sig: [10, 20], risk: { dailyStopUsd: 5 } })).trades.length === 2, 'dailyStopUsd 5 $ : la séance continue');
  const c0 = run(bars({}), mk({ sig: [10, 12], manage: { maxBars: 2 }, risk: { cooldown: 0 } }));
  const c1 = run(bars({}), mk({ sig: [10, 12], manage: { maxBars: 2 }, risk: { cooldown: 1 } }));
  ok(c0.trades.length === 2 && c0.trades[1].i === 12 && c1.trades.length === 1, 'cooldown 0 : la barre de sortie (12) peut porter un signal ; cooldown 1 : non');
  const c2 = run(bars({}), mk({ sig: [10, 13], manage: { maxBars: 2 }, risk: { cooldown: 2 } }));
  const c3 = run(bars({}), mk({ sig: [10, 14], manage: { maxBars: 2 }, risk: { cooldown: 2 } }));
  ok(c2.trades.length === 1 && c3.trades.length === 2, 'cooldown 2 : ni la barre de sortie ni la suivante');
  const rk = o => run(bars({ 10: [100, 100.5, 98, 100] }), mk(Object.assign({ risk: Object.assign({ mode: 'risk', riskUsd: 100 }, o.risk), costs: { commissionRT: null } }, o.spec || {})), { settings: Object.assign({ commissionRT: 1 }, o.settings) });
  // marché : référence close[10] = 100, stop 98 → 2 pts × 2 $ + 1 $ = 5 $ par contrat → 20 contrats
  const r20 = rk({});
  ok(one(r20).qty === 20, 'taille au risque : floor(100 / (2·2 + 1)) = 20');
  near(one(r20).pnl, 20 * (0 * 2 - 1), 1e-12, 'commission du réglage (null dans la stratégie)');
  ok(one(rk({ risk: { maxQty: 5 } })).qty === 5, 'bornée par maxQty');
  ok(one(rk({ settings: { maxContracts: 3 } })).qty === 3, 'bornée par maxContracts du compte');
  const tz = rk({ risk: { riskUsd: 4 } });
  ok(tz.trades.length === 0 && tz.counts.taille === 1, 'qty < 1 : annulé (taille)');
  // limite à 99 : la référence est le prix de l’ordre ; stop level = bas du signal (98) → 1 pt × 2 + 1 = 3 $ → 33
  const rl = rk({ spec: { entry: { type: 'limit', at: { f: 'close' }, offset: 4, valid: 2 }, stop: { type: 'level', at: { f: 'low' } } } });
  ok(rl.counts.signals === 1 && rk({ spec: { stop: { type: 'level', at: { f: 'low' } } } }).trades[0].qty === 20, 'marché : référence close[i]');
  const rlb = run(bars({ 10: [100, 100.5, 98, 100], 11: [100, 100.25, 98.75, 99.5] }), mk({ entry: { type: 'limit', at: { f: 'close' }, offset: 4, valid: 2 }, stop: { type: 'level', at: { f: 'low' } }, risk: { mode: 'risk', riskUsd: 100 }, costs: { commissionRT: null } }), { settings: { commissionRT: 1 } });
  ok(one(rlb) && one(rlb).qty === 33, 'limite : référence = prix de l’ordre (99), floor(100 / 3) = 33');
  const amb = run(bars({}), mk({ side: 'both' }));
  ok(amb.trades.length === 0 && amb.counts.ambigu === 1 && amb.counts.signals === 1, 'signal acheteur et vendeur sur la même barre : ambigu');
  const gap = bars({}).filter((x, m) => m !== 11);
  const tro = run(gap, mk());
  ok(tro.trades.length === 0 && tro.counts.trou === 1, 'barre suivante absente : trou');
  const exp = run(bars({}), mk({ session: { to: '00:11', flat: '00:11' } }));
  ok(exp.trades.length === 0 && exp.counts.expire === 1, 'barre suivante hors fenêtre : expire');
  const ann = run(bars({}), mk({ entry: { type: 'limit', at: { f: 'vwap', k: 1 }, offset: 0 } }));
  ok(ann.trades.length === 0 && ann.counts.annule === 1, 'prix d’ordre indéfini (σ < 1 tick) : annulé');
  ['signals', 'ambigu', 'taille', 'stopcourt', 'ecart', 'annule', 'expire', 'trou', 'marketable'].forEach(k => ok(typeof ann.counts[k] === 'number', 'compteur ' + k + ' publié'));
  const se = run(two, mk({ sig: [10, 20], manage: { maxBars: 2 } }));
  const s0 = se.sessions[0];
  ok(se.sessions.length === 1 && s0.n === 2 && s0.key === '2026-01-06' && s0.lo === -4 && s0.hi === 0, 'enregistrement de séance : n, creux et sommet d’équité (MAE comprise)');
  near(s0.pnl, se.trades[0].pnl + se.trades[1].pnl, 1e-12, 'P&L de séance = somme des trades');
}

/* =================================== Encadrement et loi nulle =================================== */
section('Encadrement : pessimiste ≤ vrai ≤ optimiste sur la marche au tick');
{
  const lat = E.lattice({ sessions: 31, sigma: 2, seed: 3 });
  const entries = { marché: { type: 'market' }, limite: { type: 'limit', at: { f: 'close' }, offset: 4, valid: 3 }, stop: { type: 'stop', at: { f: 'close' }, offset: 4, valid: 3 } };
  ['long', 'short'].forEach(side => Object.keys(entries).forEach(ek => [1, null].forEach(mb => {
    const out = {};
    ['pessimiste', 'vrai', 'optimiste'].forEach(fill => {
      out[fill] = run(lat, mk({ side, trigger: { bar: 'up' }, session: { warmup: 15 }, entry: entries[ek], stop: { type: 'pts', value: 1.5 }, target: { type: 'r', value: 1.5 }, manage: { maxBars: mb }, costs: { slipTicks: 1 }, fill, risk: { maxPerSession: 0, maxLossesPerSession: 0 } }), { sel: { from: lat.keys[1] } });
    });
    const p = out.pessimiste, v = out.vrai, o = out.optimiste;
    if (mb === 1) {
      let viol = 0;
      for (let x = 0; x < p.trades.length; x++) if (p.trades[x].e !== v.trades[x].e || v.trades[x].e !== o.trades[x].e || p.trades[x].r > v.trades[x].r + 1e-12 || v.trades[x].r > o.trades[x].r + 1e-12) viol++;
      ok(p.trades.length > 1000 && viol === 0 && p.trades.length === v.trades.length, side + ', ' + ek + ', barre d’entrée seule : encadrement trade par trade (' + p.trades.length + ')');
    } else ok(p.stats.meanR <= v.stats.meanR + 1e-12 && v.stats.meanR <= o.stats.meanR + 1e-12, side + ', ' + ek + ', trade entier : ' + p.stats.meanR.toFixed(3) + ' ≤ ' + v.stats.meanR.toFixed(3) + ' ≤ ' + o.stats.meanR.toFixed(3));
  })));
}
section('Loi nulle d’ALP : sur la marche au tick, E[R] = −c/L, trade par trade');
{
  const lat = E.lattice({ sessions: 61, sigma: 2, seed: 1 });
  const stops = { pts: { type: 'pts', value: 6 }, atr: { type: 'atr', value: 3, n: 14 }, swing: { type: 'swing', n: 10, buffer: 2 } };
  [0, 1].forEach(slip => Object.keys(stops).forEach(sk => {
    const r = run(lat, mk({ side: 'both', session: { warmup: 15 }, trigger: { cross: 'up', a: { f: 'close' }, b: { f: 'ema', n: 20 } }, stop: stops[sk], target: { type: 'r', value: 2 }, costs: { commissionRT: 1, slipTicks: slip }, fill: 'vrai', risk: { maxPerSession: 0, maxLossesPerSession: 0 } }), { sel: { from: lat.keys[1] } });
    const s = r.stats, se = s.sdR / Math.sqrt(s.n), z = (s.meanR + s.costR) / se;
    ok(s.n > 400 && Math.abs(z) < 2, 'stop ' + sk + ', glissement ' + slip + ' : meanR ' + s.meanR.toFixed(4) + ' contre −costR ' + (-s.costR).toFixed(4) + ' (z = ' + z.toFixed(2) + ', n = ' + s.n + ')');
  }));
  // le remplissage vrai suit le chemin exact : même une entrée stop à stop serré reste sans biais
  const r = run(lat, mk({ side: 'both', session: { warmup: 15 }, trigger: { bar: 'up' }, entry: { type: 'stop', at: { f: 'close' }, offset: 4, valid: 3 }, stop: { type: 'pts', value: 1.5 }, target: { type: 'r', value: 1.5 }, costs: { slipTicks: 1 }, fill: 'vrai', risk: { maxPerSession: 0, maxLossesPerSession: 0 } }), { sel: { from: lat.keys[1] } });
  const z = (r.stats.meanR + r.stats.costR) / (r.stats.sdR / Math.sqrt(r.stats.n));
  ok(Math.abs(z) < 2.5, 'entrée stop, stop de 6 ticks (la barre d’entrée décide souvent) : z = ' + z.toFixed(2));
  const sy = E.op('synth', { bars: lat, spec: mk({ side: 'both', session: { warmup: 15 }, trigger: { cross: 'up', a: { f: 'close' }, b: { f: 'ema', n: 20 } }, stop: { type: 'pts', value: 6 }, target: { type: 'r', value: 2 }, costs: { commissionRT: 1, slipTicks: 1 }, risk: { maxPerSession: 0, maxLossesPerSession: 0 } }), settings: SET, sel: { from: lat.keys[1] }, seed: 5 });
  ok(sy.applicable && Math.abs(sy.sigma - 2) < 0.1 && sy.sessions === 60, 'synth : σ mesuré sur la fenêtre ≈ 2 points, 60 séances');
  ok(Math.abs(sy.vrai - sy.theory) < 2.5 * sy.se && sy.theory < 0, 'synth : vrai ≈ théorie (−costR) : ' + sy.vrai.toFixed(4) + ' / ' + sy.theory.toFixed(4));
  near(sy.biais, sy.declare - sy.vrai, 1e-12, 'synth : biais = declare − vrai');
  const na = E.op('synth', { bars: lat, spec: mk({ trigger: { cmp: '>', a: { f: 'close' }, b: { f: 'level', name: 'HVL' } } }), settings: SET });
  ok(na.applicable === false && /niveau/.test(na.reason), 'synth : stratégie qui lit un niveau → non applicable');
}

/* =================================== Croisé avec Quant =================================== */
section('Croisé avec Quant : le gabarit de rejet de bande rend les trades de T.lib.quant.backtest');
{
  // Quant (mode rejet) entre à close[i] ; le Labo à open[i+1]. Sur Q.synth, open[i+1] = close[i] exactement.
  // Écarts de convention, documentés : (1) une sortie de fin de fenêtre est à la clôture de 08:59 chez Quant
  // (« cloche », indice j), à l’ouverture de 09:00 au Labo (« flat », indice j + 1) — même prix sur Q.synth ;
  // (2) Quant accepte 0 < σ < 1 tick, le Labo déclare la bande indéfinie (3.2) : avec 30 minutes d’amorçage,
  // σ dépasse toujours un tick et les deux coïncident ; à amorçage nul, les premières minutes divergent.
  let tot = 0, bad = 0, flats = 0, msg = '';
  [1, 2, 3].forEach(seed => [1, 2].forEach(k => [2, 3.5].forEach(stop => {
    const sb = Q.synth({ seed, days: 20, sigma: 4 });
    const q = Q.backtest(sb, { k, stop, mode: 'rejet', from: 0, to: 9, warm: 30, maxPer: 0, comm: 1.24, slip: 0, tick: 0.25, pv: 2 }, 0, 1);
    const spec = mk({ side: 'both', session: { from: '00:00', to: '09:00', flat: '09:00', warmup: 30 }, fill: 'pessimiste',
      setup: [{ cmp: '<', a: { f: 'close' }, b: { f: 'vwap' } }], trigger: { all: [{ cmp: '<=', a: { f: 'low' }, b: { f: 'vwap', k: -k } }, { cmp: '>', a: { f: 'close' }, b: { f: 'vwap', k: -k } }] },
      stop: { type: 'level', at: { f: 'vwap', k: -k }, buffer: stop / 0.25 }, target: { type: 'level', at: { f: 'vwap' }, dynamic: true },
      risk: { maxPerSession: 0, maxLossesPerSession: 0, dailyStopUsd: 0, cooldown: 1, minStopTicks: 0 }, costs: { commissionRT: 1.24, slipTicks: 0 } });
    const r = run(sb, spec, { settings: { commissionRT: 1.24 } });
    if (q.trades.length !== r.trades.length) { bad++; msg = msg || ('graine ' + seed + ' : ' + q.trades.length + ' contre ' + r.trades.length); return; }
    q.trades.forEach((a, x) => {
      const b = r.trades[x]; tot++;
      const jOk = b.fin === 'flat' ? (a.fin === 'cloche' && b.j === a.j + 1) : (b.j === a.j && b.fin === a.fin);
      if (b.fin === 'flat') flats++;
      if (a.i !== b.i || a.side !== b.side || a.entry !== b.entry || a.exit !== b.exit || a.pnl !== b.pnl || !jOk) { bad++; msg = msg || JSON.stringify({ seed, k, stop, x, q: [a.i, a.j, a.exit, a.fin], l: [b.i, b.j, b.exit, b.fin] }); }
    });
  })));
  ok(bad === 0 && tot > 3000, tot + ' trades identiques (indice du signal, sens, entrée, sortie, P&L au bit près) ' + msg);
  ok(flats > 0, 'des sorties de fin de fenêtre figurent dans la comparaison : ' + flats);
}

/* =================================== Statistiques =================================== */
section('Statistiques (4.1)');
{
  // géométrie fixe : objectif 2 R, coût c/L = 0,1 → gain 1,9 R, perte −1,1 R ; équilibre (1 + 0,1)/(1 + 2)
  const mkT = (r, L, c) => ({ r, pnl: r * L * 2, qty: 1, risk: L, c, fin: r > 0 ? 'objectif' : 'stop' });
  const fixed = [mkT(1.9, 5, 1), mkT(1.9, 5, 1), mkT(-1.1, 5, 1), mkT(-1.1, 5, 1), mkT(-1.1, 5, 1), mkT(0, 5, 1)];
  const s = E.stats(fixed, 2);
  near(s.equilibrium, 1.1 / 3, 1e-12, 'equilibrium = (1 + c/L)/(1 + R:R) sur une géométrie fixe');
  ok(s.n === 6 && s.nz === 5 && s.wins === 2 && s.losses === 3, 'n, nz (r ≠ 0), gains, pertes');
  near(s.winRate, 0.4, 1e-12, 'taux de réussite parmi r ≠ 0');
  near(s.costR, 0.1, 1e-12, 'costR = moyenne de c/(L·pv)');
  near(s.meanR, (3.8 - 3.3) / 6, 1e-12, 'meanR');
  near(s.pf, (2 * 1.9 * 10) / (3 * 1.1 * 10), 1e-12, 'pf');
  ok(s.byFin.objectif.n === 2 && s.byFin.stop.n === 4, 'byFin');
  // identité de signe sur des jeux aléatoires
  let r = 7, bad = 0; const rnd = () => (r = (r * 16807) % 2147483647) / 2147483647;
  for (let k = 0; k < 300; k++) {
    const set = []; const n = 3 + Math.floor(rnd() * 40);
    for (let q = 0; q < n; q++) { const x = rnd() < 0.1 ? 0 : (rnd() - 0.45) * 6; set.push(mkT(x, 2 + rnd() * 10, rnd())); }
    const st = E.stats(set, 2);
    if (!(st.wins && st.losses)) continue;
    if (Math.sign(st.winRate - st.equilibrium) !== Math.sign(st.meanR)) bad++;
  }
  ok(bad === 0, 'signe(winRate − equilibrium) = signe(meanR) sur 300 jeux de trades');
  // coût en R : moyenne de rapports contre rapport de moyennes, risque uniforme entre 4 et 20 points
  const set = []; for (let q = 0; q < 4001; q++) { const L = 4 + 16 * q / 4000; set.push({ r: -1, pnl: -L * 2, qty: 1, risk: L, c: 2, fin: 'stop' }); }
  const sc = E.stats(set, 2);
  near(sc.costR, Math.log(5) / 16, 2e-4, 'costR = c·E[1/L]/pv = ln 5 / 16');
  near(sc.rW0, -2 / (12 * 2), 1e-9, 'prédiction de rW : −Σc / Σ L·pv = −1/12');
  ok(Math.abs(sc.rW0 / -sc.costR - 0.828) < 0.003, 'un rapport de moyennes serait faux de 17 % : ' + (sc.rW0 / -sc.costR).toFixed(3));
  const set2 = [{ r: 0.5, pnl: 3, qty: 3, risk: 1, c: 0, fin: 'objectif' }, { r: -1, pnl: -2, qty: 1, risk: 1, c: 0, fin: 'stop' }];
  near(E.stats(set2, 2).rW, 1 / 8, 1e-12, 'rW = Σ pnl / Σ qty·L·pv');
  const st2 = E.stats([mkT(1, 1, 0), mkT(-1, 1, 0), mkT(2, 1, 0), mkT(-1, 1, 0), mkT(3, 1, 0)], 2);
  const xs = [1, -1, 2, -1, 3], m = 0.8, m2 = xs.reduce((a, x) => a + (x - m) ** 2, 0) / 5, m3 = xs.reduce((a, x) => a + (x - m) ** 3, 0) / 5, m4 = xs.reduce((a, x) => a + (x - m) ** 4, 0) / 5;
  near(st2.skew, m3 / Math.pow(m2, 1.5), 1e-12, 'asymétrie');
  near(st2.exkurt, m4 / (m2 * m2) - 3, 1e-12, 'aplatissement en excès');
  near(st2.sharpeTrade, m / Math.sqrt(m2 * 5 / 4), 1e-12, 'Sharpe par trade = meanR / sdR (écart-type d’échantillon)');
  near(st2.maxDD, 2, 1e-12, 'perte maximale en $ (équité 2, 0, 4, 2, 8)');
}

/* =================================== Divers =================================== */
section('Enveloppe, aperçu, hors échantillon, déterminisme');
{
  const lat = E.lattice({ sessions: 12, sigma: 2, seed: 13 });
  const spec = mk({ side: 'both', session: { warmup: 15 }, trigger: { cross: 'up', a: { f: 'close' }, b: { f: 'vwap' } }, entry: { type: 'limit', at: { f: 'close' }, offset: 2, valid: 2 }, stop: { type: 'pts', value: 3 }, target: { type: 'r', value: 1.5 }, risk: { maxPerSession: 0 }, costs: { slipTicks: 1 } });
  const env = E.op('envelope', { bars: lat, spec, settings: SET });
  ok(env.pess.stats.meanR <= env.opt.stats.meanR && env.pess.eq.length === env.pess.stats.n, 'enveloppe : pessimiste ≤ optimiste, équité publiée');
  const f = E.op('features', { bars: lat, spec, settings: SET, operands: [{ f: 'vwap' }, { f: 'ema', n: 20 }] });
  ok(f.keys.length === 5 && f.t.length === 5 * 1380 && f.series.length === 2 && f.series[0].length === f.t.length && f.sig.L.length === f.t.length, 'features : cinq dernières séances au plus, séries et signaux');
  ok(f.series[0].every(x => x === null || typeof x === 'number'), 'features : NaN publié comme null');
  throws(() => E.run({ bars: lat, spec, settings: SET, oosFrom: lat.keys[8] }), /Hors échantillon/, 'coupure hors échantillon posée : une opération sans sel est refusée');
  throws(() => E.run({ bars: lat, spec, settings: SET, oosFrom: lat.keys[8], sel: { to: lat.keys[8] } }), /Hors échantillon/, 'sel.to = oosFrom refusé');
  ok(E.run({ bars: lat, spec, settings: SET, oosFrom: lat.keys[8], sel: { to: lat.keys[7] } }).sessions.length === 8, 'sel.to < oosFrom accepté');
  ok(E.run({ bars: lat, spec, settings: SET, oosFrom: lat.keys[8], oos: true }).sessions.length === 12, 'ouverture hors échantillon (oos: true) acceptée');
  const sel = E.run({ bars: lat, spec, settings: SET, sel: { from: lat.keys[3], to: lat.keys[5] } });
  ok(sel.sessions.length === 3 && sel.sessions[0].key === lat.keys[3], 'sel : seules les séances choisies sont jouées (les précédentes amorcent)');
  const a = E.run({ bars: lat, spec, settings: SET }), b = E.run({ bars: lat, spec, settings: SET });
  ok(JSON.stringify(a) === JSON.stringify(b), 'deux runs identiques au bit près');
  const l1 = E.lattice({ sessions: 2, seed: 4 }), l2 = E.lattice({ sessions: 2, seed: 4 }), l3 = E.lattice({ sessions: 2, seed: 5 });
  ok(l1.c.every((x, i) => x === l2.c[i]) && l1.walk.every((x, i) => x === l2.walk[i]) && l1.c.some((x, i) => x !== l3.c[i]), 'lattice déterministe à graine égale');
  let lfBad = 0, stepBad = 0;
  for (let i = 0; i < l1.t.length; i++) { if (i && l1.o[i] !== l1.c[i - 1]) stepBad++; if (((l1.h[i] - l1.o[i]) / 0.25) % 1 || ((l1.c[i] - l1.o[i]) / 0.25 + l1.k) % 2) stepBad++; }
  ok(stepBad === 0 && l1.k === 64, 'lattice : prix sur le réseau des ticks, ouverture = clôture précédente, k = (σ/tick)² pas par minute');
  ok(lfBad === 0 && l1.lowFirst.length === l1.t.length, 'lattice : lowFirst publié');
}
section('Bascule de contrat, fenêtre à cheval sur l’ancre, cache du worker, surcharge des coûts');
{
  const lat = E.lattice({ sessions: 4, sigma: 2, seed: 6 }), R = 2760;
  const opsR = [{ f: 'sma', n: 10 }, { f: 'prev', of: 'close' }, { f: 'atr', n: 14 }, { f: 'hh', n: 5 }, { f: 'close', lag: 1 }, { f: 'tf', m: 5, of: { f: 'close' } }];
  const a = E.op('series', { bars: lat, spec: {}, settings: SET, operands: opsR, rolls: [lat.keys[2]] });
  const b = E.op('series', { bars: lat, spec: {}, settings: SET, operands: opsR });
  ok(a.ops[0][R + 8] !== a.ops[0][R + 8] && a.ops[0][R + 9] === a.ops[0][R + 9] && b.ops[0][R + 8] === b.ops[0][R + 8], 'séance de bascule : sma repart de zéro');
  ok(a.ops[1][R + 5] !== a.ops[1][R + 5] && b.ops[1][R + 5] === lat.c[R - 1] && a.ops[1][R + 1385] === lat.c[R + 1379], 'prev repart de zéro à la bascule, puis lit la séance de bascule');
  ok(a.ops[2][R] !== a.ops[2][R] && a.ops[3][R + 4] !== a.ops[3][R + 4] && a.ops[4][R] !== a.ops[4][R] && a.ops[5][R + 2] !== a.ops[5][R + 2], 'atr, hh, lag, tf : aucune lecture à travers la bascule');
  const st = run(lat, mk({ session: { from: '23:00', to: '01:00', flat: '01:00' }, trigger: { bar: 'up' } }));
  ok(st.trades.length === 0 && st.sessions.length === 0 && st.warnings.some(w => /ancre/.test(w)), 'fenêtre à cheval sur l’ancre : séances ignorées, avertissement');
  const C = {}, spec = mk({ side: 'both', session: { warmup: 15 }, trigger: { cross: 'up', a: { f: 'close' }, b: { f: 'vwap' } }, risk: { maxPerSession: 0 } });
  const c1 = E.run({ bars: lat, spec, settings: SET, fp: 'x', cache: C }), ctx1 = C.ctx;
  const c2 = E.run({ bars: lat, spec, settings: SET, fp: 'x', cache: C });
  ok(ctx1 && C.ctx === ctx1 && JSON.stringify(c1) === JSON.stringify(c2), 'cache du worker : même jeu, même contexte, même résultat');
  const s2 = JSON.parse(JSON.stringify(spec)); s2.anchor = 'paris';
  E.run({ bars: lat, spec: s2, settings: SET, fp: 'x', cache: C });
  ok(C.ctx !== ctx1, 'autre ancrage : contexte reconstruit');
  const ov = E.run({ bars: lat, spec, settings: SET, override: { slipTicks: 2, commissionRT: 3, fill: 'optimiste' } });
  ok(ov.costs.slipTicks === 2 && ov.costs.commissionRT === 3 && ov.fill === 'optimiste' && ov.trades.every(t => t.c === 3 + 0.25 * 2 * 2 * t.legs), 'surcharge des coûts et du remplissage (stress, verdict)');
}
section('Exécuteur : enveloppes synchrones, mode local, worker simulé');
(async () => {
  const lat = E.lattice({ sessions: 6, sigma: 2, seed: 17 });
  const spec = mk({ side: 'both', session: { warmup: 15 }, trigger: { cross: 'up', a: { f: 'close' }, b: { f: 'vwap' } }, risk: { maxPerSession: 0 } });
  const ref = E.run({ bars: lat, spec, settings: SET });
  const ex = E.worker({ local: true });
  ok(ex.mode === 'local', 'sans Worker : mode local');
  await ex.load('fp1', lat);
  const r1 = await ex.call('run', { spec, settings: SET }).promise;
  ok(r1.trades.length === ref.trades.length && r1.stats.net === ref.stats.net, 'mode local : run sur les colonnes chargées');
  let refused = null; try { await ex.call('sweep', { spec }).promise; } catch (e) { refused = e.message; }
  ok(/impossible sur cet appareil/.test(refused || ''), 'mode local : une opération lourde est refusée');
  const j1 = ex.call('run', { spec, settings: SET }), j2 = ex.call('run', { spec, settings: SET });
  j2.cancel(); let c2 = null; try { await j2.promise; } catch (e) { c2 = e; }
  ok(c2 && c2.cancelled, 'un calcul en file annulé est rejeté (cancelled)');
  await j1.promise;
  ex.close(); let cl = null; try { await ex.call('run', {}).promise; } catch (e) { cl = e.message; }
  ok(/fermé/.test(cl || ''), 'exécuteur fermé');

  // worker simulé : la source du Blob tourne dans son propre contexte ; messages asynchrones
  const BLOBS = {}, live = []; let nBlob = 0, loads = 0, spawned = 0;
  class FakeWorker {
    constructor(url) {
      spawned++; this.dead = false; const me = this;
      const self = { postMessage(m) { if (!me.dead) setTimeout(() => { if (!me.dead && me.onmessage) me.onmessage({ data: m }); }, 0); } };
      this.inner = self; vm.runInNewContext(BLOBS[url], { self, Date }); live.push(this);
    }
    postMessage(m, tr) { if (m.type === 'load') { loads++; ok(Array.isArray(tr) && tr.length >= 6, 'colonnes transférées (' + tr.length + ' tampons)'); } const me = this; setTimeout(() => { if (!me.dead) me.inner.onmessage({ data: m }); }, 0); }
    terminate() { this.dead = true; }
  }
  CTX.Worker = FakeWorker; CTX.Blob = class { constructor(p) { this.text = p.join(''); } };
  CTX.URL = { createObjectURL(b) { const id = 'blob:' + (++nBlob); BLOBS[id] = b.text; return id; }, revokeObjectURL() {} };
  const wx = E.worker();
  await wx.load('fpA', lat);
  ok(wx.mode === 'worker' && spawned === 1 && loads === 1, 'worker créé une fois, jeu chargé une fois');
  const w1 = await wx.call('run', { spec, settings: SET }).promise;
  const w2 = await wx.call('envelope', { spec, settings: SET }).promise;
  ok(w1.trades.length === ref.trades.length && w1.stats.net === ref.stats.net && w2.pess && loads === 1, 'deux calculs sur le même jeu : aucun rechargement');
  let progress = [];
  const big = E.lattice({ sessions: 120, sigma: 2, seed: 2 });
  await wx.load('fpB', big);
  const job = wx.call('run', { spec, settings: SET }, p => progress.push(p));
  const wr = await job.promise;
  ok(loads === 2 && wr.sessions.length === 120, 'nouveau jeu : chargé une fois');
  ok(progress.every((p, k) => p >= 0 && p <= 1 && (!k || p >= progress[k - 1])), 'progression croissante dans [0, 1] (' + progress.length + ' messages, au plus un par 250 ms)');
  const jc = wx.call('run', { spec, settings: SET });
  jc.cancel(); let cc = null; try { await jc.promise; } catch (e) { cc = e; }
  ok(cc && cc.cancelled && live[0].dead, 'annuler le calcul en cours termine le worker');
  const after = await wx.call('run', { spec, settings: SET }).promise;
  ok(spawned === 2 && loads === 3 && after.sessions.length === 120, 'le calcul suivant recrée le worker et recharge le jeu');
  wx.close();
  ok(live.every(w => w.dead), 'close termine le worker');
  delete CTX.Worker; delete CTX.Blob; delete CTX.URL;

  section('Worker réel : la source du Blob dans un fil worker_threads, colonnes transférées');
  {
    const { Worker } = require('worker_threads');
    const shim = 'const { parentPort } = require("worker_threads"); var self = { postMessage: (m, t) => parentPort.postMessage(m, t) }; parentPort.on("message", d => self.onmessage({ data: d }));\n';
    const w = new Worker(shim + E.workerSource(), { eval: true });
    const msgs = [];
    const next = () => new Promise(res => w.once('message', m => { msgs.push(m.type); res(m); }));
    const cols = { t: Float64Array.from(lat.t), o: Float64Array.from(lat.o), h: Float64Array.from(lat.h), l: Float64Array.from(lat.l), c: Float64Array.from(lat.c), v: Float64Array.from(lat.v), lowFirst: Uint8Array.from(lat.lowFirst), walk: Float64Array.from(lat.walk) };
    w.postMessage({ type: 'load', id: 1, fp: 'fpR', cols }, Object.values(cols).map(x => x.buffer));
    const m1 = await next();
    ok(m1.type === 'loaded' && cols.t.byteLength === 0, 'chargé, tampons transférés (détachés côté appelant)');
    w.postMessage({ type: 'call', id: 2, op: 'run', a: { spec, settings: SET, fp: 'fpR' } });
    const m2 = await next();
    ok(m2.type === 'done' && m2.r.trades.length === ref.trades.length && m2.r.stats.net === ref.stats.net, 'run dans le fil worker = run synchrone');
    w.postMessage({ type: 'call', id: 3, op: 'series', a: { spec, settings: SET, operands: [{ f: 'close' }] } });
    const m3 = await next();
    w.postMessage({ type: 'call', id: 4, op: 'run', a: { spec, settings: SET } });
    const m4 = await next();
    ok(m3.type === 'done' && m4.type === 'done' && m4.r.stats.net === ref.stats.net, 'un résultat qui partage le tampon du jeu ne le détache pas');
    w.postMessage({ type: 'call', id: 5, op: 'run', a: { spec, settings: SET, fp: 'autre' } });
    const m5 = await next();
    ok(m5.type === 'error' && /non chargées/.test(m5.e), 'empreinte différente : erreur, jamais un calcul sur le mauvais jeu');
    await w.terminate();
  }

  section('Performance : 350 000 barres');
  const lat3 = E.lattice({ sessions: 254, sigma: 1, seed: 11 });
  const pspec = mk({ side: 'both', session: { warmup: 15 }, setup: [{ cmp: '<', a: { f: 'close' }, b: { f: 'vwap' } }], trigger: { all: [{ cmp: '<=', a: { f: 'low' }, b: { f: 'vwap', k: -1 } }, { cmp: '>', a: { f: 'close' }, b: { f: 'vwap', k: -1 } }] },
    stop: { type: 'level', at: { f: 'vwap', k: -1 }, buffer: 8 }, target: { type: 'level', at: { f: 'vwap' }, dynamic: true }, risk: { maxPerSession: 0, maxLossesPerSession: 0 }, costs: { slipTicks: 1, commissionRT: 1 } });
  E.run({ bars: lat3, spec: pspec, settings: SET });
  const t0 = Date.now(), pr = E.run({ bars: lat3, spec: pspec, settings: SET }), dt = Date.now() - t0;
  ok(lat3.t.length >= 350000 && pr.trades.length > 1000 && dt < 500, 'run sur ' + lat3.t.length + ' barres en ' + dt + ' ms (borne 500 ms)');

  console.log((fails ? 'ÉCHECS : ' + fails : 'OK') + ' — ' + passes + ' contrôles réussis, ' + fails + ' échoués');
  process.exit(fails ? 1 : 0);
})().catch(e => { console.error('ÉCHEC (exception)', e && e.stack || e); process.exit(1); });
