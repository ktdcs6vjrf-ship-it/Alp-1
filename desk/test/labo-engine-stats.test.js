// Tests des opérations statistiques du moteur du Labo (LABO.md §4.2 à §4.7) : node test/labo-engine-stats.test.js
// (sortie non nulle si échec). Aucune donnée de marché : marches au tick amorcées (T.lib.laboEngine.lattice),
// barres construites à la main, enregistrements de séance tirés avec une graine explicite.
const H = require('./harness');
const { T, lib: E } = H(['quant', 'risk', 'labo-engine']);
const RK = T.lib.risk;
let fails = 0, passes = 0;
function ok(cond, msg) { if (cond) passes++; else { fails++; console.error('ÉCHEC', msg); } }
function near(a, b, tol, msg) { const good = typeof a === 'number' && typeof b === 'number' && (a === b || Math.abs(a - b) <= tol * Math.max(1, Math.abs(b))); ok(good, msg + ' : ' + a + ' attendu ' + b); }
function throws(fn, re, msg) { try { fn(); ok(false, msg + ' (aucune erreur levée)'); } catch (e) { ok(!re || re.test(String(e.message)), msg + ' : ' + e.message); } }
function section(t) { console.log('· ' + t); }
const MIN = 60000;
const SET = { tick: 0.25, pointValue: 2, commissionRT: 0, maxContracts: 0 };
const hhmm = m => String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0');
const at = m => ({ time: [hhmm(m), hhmm(m + 1)] });
function mulberry(seed) { let s = seed >>> 0; return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
function gauss(r) { let u = 0; while (u === 0) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); }
/* Stratégie de test : fenêtre 00:00–05:00 Paris (les marches commencent à 18:00 New York = 00:00 Paris en janvier). */
function mk(o) {
  o = o || {};
  return {
    side: o.side || 'long', anchor: 'globex', mirror: true,
    session: Object.assign({ tz: 'Europe/Paris', from: '00:00', to: '05:00', flat: '05:00', days: [1, 2, 3, 4, 5], warmup: 15 }, o.session),
    long: { setup: o.setup || [], trigger: o.trigger || { bar: 'up' }, entry: o.entry || { type: 'market' }, stop: o.stop || { type: 'pts', value: 2 }, target: o.target || { type: 'pts', value: 2 } },
    manage: Object.assign({ breakeven: null, trail: null, maxBars: 5, exitOnOpposite: false }, o.manage),
    risk: Object.assign({ mode: 'contracts', contracts: 1, riskUsd: 150, maxQty: null, minStopTicks: 1, maxPerSession: 2, maxLossesPerSession: 0, dailyStopUsd: 0, cooldown: 0 }, o.risk),
    costs: Object.assign({ commissionRT: 0, slipTicks: 1 }, o.costs), fill: o.fill || 'vrai', params: o.params || {}
  };
}
/* Dérive plantée : dans chaque séance de `minutes` barres, les barres [from, from + len) prennent chacune un écart
   d’ouverture de +d (toute la barre est décalée), puis le niveau reste décalé de len·d jusqu’à la fin de la séance. */
function plant(lat, d, from, len, minutes) {
  const n = lat.t.length, o = Float64Array.from(lat.o), h = Float64Array.from(lat.h), l = Float64Array.from(lat.l), c = Float64Array.from(lat.c);
  for (let i = 0; i < n; i++) {
    const m = i % minutes, sh = m < from ? 0 : m < from + len ? d * (m - from + 1) : d * len;
    o[i] += sh; h[i] += sh; l[i] += sh; c[i] += sh;
  }
  return Object.assign({}, lat, { o, h, l, c });
}
const mean = xs => xs.reduce((s, x) => s + x, 0) / xs.length;

(async function main() {

/* =================================== 4.2 et 4.3 : puissance et taille =================================== */
section('Puissance : une dérive plantée dans la fenêtre donne p < 0,05 (hasard et permutation)');
{
  const lat = plant(E.lattice({ sessions: 40, sigma: 1, seed: 21, minutes: 300 }), 0.5, 120, 10, 300);
  const spec = mk({ trigger: at(119), stop: { type: 'pts', value: 20 }, target: { type: 'none' }, manage: { maxBars: 10 } });
  const run = E.run({ bars: lat, spec, settings: SET });
  ok(run.trades.length === 40 && run.trades.every(t => t.i % 300 === 119 && t.fin === 'temps'), 'la stratégie entre à 02:00 et sort après dix barres, une fois par séance');
  const rd = E.op('random', { bars: lat, spec, settings: SET, draws: 200, seed: 1 });
  ok(rd.p < 0.05 && rd.p === 1 / 201, 'entrées au hasard : p = ' + rd.p + ' (observé ' + rd.obs.toFixed(3) + ' R, 95 % du hasard sous ' + rd.hi.toFixed(3) + ')');
  ok(rd.signals === 40 && rd.n === 40, 'un signal tiré par séance, comme la stratégie');
  const pm = E.op('permute', { bars: lat, spec, settings: SET, draws: 99, seed: 1, budgetMs: Infinity });
  ok(pm.p < 0.05, 'permutation par tranches de 30 minutes : p = ' + pm.p + ' (p minimal ' + pm.pmin.toFixed(3) + ')');
  ok(pm.block === 30 && /tranche de 30 minutes/.test(pm.h0) && pm.draws === 99 && pm.pmin === 1 / 100, 'hypothèse nulle et p minimal publiés');
  near(pm.obs, rd.obs, 1e-12, 'même valeur observée pour les deux lois nulles');
  const ps = E.op('permute', { bars: lat, spec, settings: SET, draws: 60, seed: 1, block: 'seance', budgetMs: Infinity });
  ok(ps.p < 0.05 && /séance/.test(ps.h0), 'permutation de toute la séance : p = ' + ps.p);
}

section('Taille : sans dérive, p < 0,05 sur environ 5 % de 40 graines');
{
  const spec = mk({});
  const pr = [], pp = [];
  for (let s = 1; s <= 40; s++) {
    const lat = E.lattice({ sessions: 30, sigma: 1, seed: 100 + s, minutes: 300 });
    pr.push(E.op('random', { bars: lat, spec, settings: SET, draws: 100, seed: s }).p);
    pp.push(E.op('permute', { bars: lat, spec, settings: SET, draws: 50, seed: s, budgetMs: Infinity }).p);
  }
  const kr = pr.filter(p => p < 0.05).length, kp = pp.filter(p => p < 0.05).length;
  ok(kr <= 6, 'entrées au hasard : ' + kr + ' graines sur 40 sous 0,05 (attendu ≈ 2, tolérance ≤ 6)');
  ok(kp <= 6, 'permutation : ' + kp + ' graines sur 40 sous 0,05 (attendu ≈ 2, tolérance ≤ 6)');
  ok(mean(pr) > 0.35 && mean(pr) < 0.65, 'p moyen des entrées au hasard ≈ 0,5 : ' + mean(pr).toFixed(3));
  ok(mean(pp) > 0.35 && mean(pp) < 0.65, 'p moyen de la permutation ≈ 0,5 : ' + mean(pp).toFixed(3));
}

section('Une stratégie qui ne gagne que le glissement d’entrée (limite contre marché) n’a pas p < 0,05');
{
  const lim = mk({ entry: { type: 'limit', at: { f: 'close' }, offset: 1, valid: 1 } }), mkt = mk({});
  let low = 0, sMidL = 0, sMidM = 0, sObsL = 0, sObsM = 0;
  for (let s = 1; s <= 10; s++) {
    const lat = E.lattice({ sessions: 40, sigma: 1, seed: 300 + s, minutes: 300 });
    const rl = E.op('random', { bars: lat, spec: lim, settings: SET, draws: 100, seed: s }), rm = E.op('random', { bars: lat, spec: mkt, settings: SET, draws: 100, seed: s });
    if (rl.p < 0.05) low++;
    sMidL += rl.mid; sMidM += rm.mid; sObsL += rl.obs; sObsM += rm.obs;
  }
  ok(low <= 2, 'limite : p < 0,05 sur ' + low + ' graines sur 10');
  ok(sObsL > sObsM, 'la version limite gagne bien sur la version marché (moyenne observée ' + (sObsL / 10).toFixed(3) + ' R contre ' + (sObsM / 10).toFixed(3) + ' R)');
  ok(sMidL - sMidM > 0.08, 'la loi nulle rejoue l’ordre limite : sa médiane gagne le même glissement (' + ((sMidL - sMidM) / 10).toFixed(3) + ' R ; un tick sur un stop de 2 points = 0,125 R)');
}

/* =================================== 4.2 : le chemin d’exécution =================================== */
section('Entrées au hasard : chaque tirage suit exactement le chemin de la stratégie');
{
  const lat = E.lattice({ sessions: 25, sigma: 1, seed: 7, minutes: 300 });
  /* une seule barre exécutable par séance (01:59) : le tirage ne peut que retomber sur le signal observé */
  const spec = mk({ session: { from: '02:00', to: '02:01', flat: '05:00', warmup: 0 }, trigger: at(119),
    entry: { type: 'limit', at: { f: 'vwap' }, offset: 2, valid: 30 }, stop: { type: 'swing', n: 5, buffer: 1 }, target: { type: 'r', value: 1.5 }, manage: { maxBars: null } });
  const run = E.run({ bars: lat, spec, settings: SET }), rd = E.op('random', { bars: lat, spec, settings: SET, draws: 30, seed: 4 });
  ok(run.trades.length > 5, 'la stratégie de contrôle trade : ' + run.trades.length + ' trades');
  ok(rd.means.every(m => m === rd.obs), 'tirage forcé sur la barre du signal : même meanR à chaque tirage (ordre limite, valid, swing, objectif en R)');
  ok(rd.p === 1 && rd.lo === rd.obs && rd.hi === rd.obs, 'p = 1 quand tous les tirages égalent l’observé');

  /* nombre de signaux, proportion d’achats, statistique, p et étiquette */
  const sp2 = mk({ side: 'both', trigger: { bar: 'up' }, setup: [{ cmp: '>', a: { f: 'close' }, b: { f: 'vwap' } }] });
  const r2 = E.run({ bars: lat, spec: sp2, settings: SET }), x2 = E.op('random', { bars: lat, spec: sp2, settings: SET, draws: 60, seed: 9, N: 37 });
  const want = r2.sessions.reduce((s, x) => s + x.sig - x.amb, 0), nL = r2.trades.filter(t => t.side > 0).length;
  ok(x2.signals === want, 'autant de signaux tirés que de signaux lus : ' + x2.signals + ' / ' + want);
  near(x2.pLong, nL / r2.trades.length, 1e-12, '« both » : proportion d’achats observée');
  near(x2.obs, r2.stats.meanR, 1e-12, 'statistique observée = meanR des trades remplis');
  const k = x2.means.filter(m => m === null || m >= x2.obs).length;
  near(x2.p, (1 + k) / 61, 1e-12, 'p = (1 + #{tirés ≥ observé}) / (tirages + 1)');
  ok(x2.label === 'configuration isolée, non corrigée des N = 37 essais', 'étiquette : ' + x2.label);
  ok(E.op('random', { bars: lat, spec: sp2, settings: SET, draws: 5 }).label === 'configuration isolée, non corrigée des N essais', 'étiquette sans N');

  /* stop « level » indéfini à la barre tirée : distance médiane observée */
  const sp3 = mk({ session: { warmup: 0 }, trigger: { all: [{ bar: 'up' }, { time: ['00:45', '05:00'] }] }, stop: { type: 'level', at: { f: 'or', from: '00:00', to: '00:30', of: 'low' }, buffer: 1 }, target: { type: 'r', value: 1 }, manage: { maxBars: 30 } });
  const r3 = E.run({ bars: lat, spec: sp3, settings: SET }), x3 = E.op('random', { bars: lat, spec: sp3, settings: SET, draws: 40, seed: 2 });
  const ds = r3.trades.map(t => Math.abs(t.entry - t.stop0)).sort((x, y) => x - y), md = ds.length % 2 ? ds[(ds.length - 1) / 2] : (ds[ds.length / 2 - 1] + ds[ds.length / 2]) / 2;
  ok(r3.trades.length > 10 && r3.trades.every(t => !t.fb), 'observé : stop au bas du range d’ouverture, toujours défini');
  near(x3.fallback.stop, md, 1e-12, 'distance de repli = médiane observée de |entrée − stop|');
  ok(x3.fbShare > 0.02, 'des tirages avant 00:30 utilisent la distance de repli : ' + (100 * x3.fbShare).toFixed(1) + ' %');
}

/* =================================== 4.3 : la permutation =================================== */
section('Permutation : mouvement net de chaque tranche, multiensemble des barres, grille du tick');
{
  /* barres à écarts d’ouverture aléatoires, sur la grille du quart de point, trois séances Globex */
  const r = mulberry(5), t = [], o = [], h = [], l = [], c = [], v = [], lf = [];
  const T0 = Date.UTC(2026, 0, 5, 23, 0);
  let p = 20000;
  for (let s = 0; s < 3; s++) for (let m = 0; m < 1380; m++) {
    const g = Math.round(gauss(r) * 2) * 0.25, op = p + g, cl = op + Math.round(gauss(r) * 4) * 0.25;
    t.push(T0 + s * 86400000 + m * MIN); o.push(op); c.push(cl);
    h.push(Math.max(op, cl) + Math.round(r() * 6) * 0.25); l.push(Math.min(op, cl) - Math.round(r() * 6) * 0.25);
    v.push(1 + Math.floor(r() * 50)); lf.push(r() < 0.5 ? 1 : 0); p = cl;
  }
  const bars = { t, o, h, l, c, v, lowFirst: lf };
  const P = E.op('permuted', { bars, seed: 3 }), n = t.length;
  ok(P.keys.length === 3 && P.t.length === n && P.t.every((x, i) => x === t[i]), 'heures inchangées');
  ok(P.o.every((x, i) => Number.isInteger(x * 4) && Number.isInteger(P.h[i] * 4) && Number.isInteger(P.l[i] * 4) && Number.isInteger(P.c[i] * 4)), 'prix reconstruits sur la grille du tick');
  let moved = 0, blocksOk = true, shapeOk = true, permOk = true, firstOk = true, endOk = true;
  const blk = i => Math.floor(t[i] / (30 * MIN)), sess = i => Math.floor(i / 1380);
  const tup = (O, Hh, Ll, C, V, LF, i, prevC) => [O[i] - prevC, Hh[i] - O[i], Ll[i] - O[i], C[i] - O[i], V[i], LF[i]].join('|');
  for (let s = 0; s < 3; s++) {
    const i0 = s * 1380, i1 = i0 + 1379;
    if (P.o[i0] !== o[i0] || P.c[i0] !== c[i0] || P.h[i0] !== h[i0] || P.l[i0] !== l[i0] || P.perm[i0] !== i0) firstOk = false;
    if (P.c[i1] !== c[i1]) endOk = false;
    let b0 = i0 + 1;
    while (b0 <= i1) {
      let b1 = b0; while (b1 < i1 && blk(b1 + 1) === blk(b0)) b1++;
      if (P.c[b1] - P.c[b0 - 1] !== c[b1] - c[b0 - 1]) blocksOk = false;
      const A = [], B = [];
      for (let i = b0; i <= b1; i++) {
        A.push(tup(o, h, l, c, v, lf, i, c[i - 1])); B.push(tup(P.o, P.h, P.l, P.c, P.v, P.lowFirst, i, P.c[i - 1]));
        const k = P.perm[i];
        if (k < b0 || k > b1 || sess(k) !== s) permOk = false;
        if (k !== i) moved++;
        if (P.lowFirst[i] !== lf[k] || P.v[i] !== v[k] || Math.abs((P.c[i] - P.o[i]) - (c[k] - o[k])) > 1e-9) permOk = false;
      }
      if (A.sort().join() !== B.sort().join()) shapeOk = false;
      b0 = b1 + 1;
    }
  }
  ok(firstOk, '1re barre de chaque séance en place (elle porte l’écart de la nuit)');
  ok(endOk, 'clôture de chaque séance inchangée');
  ok(blocksOk, 'mouvement net de chaque tranche de 30 minutes conservé exactement');
  ok(shapeOk, 'multiensemble (écart d’ouverture, forme, volume, ordre intrabarre) de chaque tranche conservé');
  ok(permOk, 'chaque barre reste dans sa tranche et emporte son volume et son ordre intrabarre');
  ok(moved > n * 0.9, 'les minutes bougent : ' + moved + ' barres déplacées sur ' + n);
  const Q = E.op('permuted', { bars, seed: 3, block: 'seance' });
  let qOk = true; for (let i = 0; i < n; i++) if (sess(Q.perm[i]) !== sess(i) || (i % 1380 === 0 && Q.perm[i] !== i)) qOk = false;
  ok(qOk && Q.block === 'seance', '« seance » : permutation dans la séance, 1re barre exclue');
  ok(E.op('permuted', { bars, seed: 3 }).perm.every((x, i) => x === P.perm[i]) && !E.op('permuted', { bars, seed: 4 }).perm.every((x, i) => x === P.perm[i]), 'déterministe à graine égale, différent à graine différente');
  /* prix hors grille : calcul en flottants, mouvement net conservé à l’arrondi près */
  const bars2 = Object.assign({}, bars, { o: o.map(x => x + 0.013), h: h.map(x => x + 0.013), l: l.map(x => x + 0.013), c: c.map(x => x + 0.013) });
  const P2 = E.op('permuted', { bars: bars2, seed: 3 });
  ok(Math.abs(P2.c[1379] - bars2.c[1379]) < 1e-6 && Math.abs(P2.o[700] - P.o[700] - 0.013) < 1e-6, 'prix hors grille : même permutation, reconstruction en flottants');
  const lat = E.lattice({ sessions: 3, sigma: 1, seed: 2, minutes: 120 });
  const PL = E.op('permuted', { bars: lat, seed: 1 });
  ok(PL.walk && PL.walk.every((x, i) => x === lat.walk[PL.perm[i]]), 'la colonne walk suit sa barre (remplissage vrai rejouable)');
  const vr = E.run({ bars: { t: lat.t, o: PL.o, h: PL.h, l: PL.l, c: PL.c, v: PL.v, lowFirst: PL.lowFirst, walk: PL.walk }, spec: mk({ session: { to: '02:00', flat: '02:00' } }), settings: SET });
  ok(vr.trades.length > 0 && !vr.warnings.some(w => /sans ordre intrabarre/.test(w)), 'série permutée jouable en remplissage vrai');
}

section('Permutation : budget de temps et p minimal');
{
  const lat = E.lattice({ sessions: 20, sigma: 1, seed: 8, minutes: 300 }), spec = mk({});
  const full = E.op('permute', { bars: lat, spec, settings: SET, draws: 6, minDraws: 1, seed: 5, budgetMs: Infinity });
  const cut = E.op('permute', { bars: lat, spec, settings: SET, draws: 50, minDraws: 3, seed: 5, budgetMs: 0 });
  ok(cut.draws === 3 && cut.cut === true && cut.pmin === 1 / 4, 'budget dépassé : on s’arrête au minimum de tirages, p minimal publié (' + cut.draws + ')');
  ok(full.draws === 6 && !full.cut && cut.means.every((m, i) => m === full.means[i]), 'les premiers tirages ne dépendent pas du budget');
  const dflt = E.op('permute', { bars: lat, spec, settings: SET, draws: 60, seed: 5, budgetMs: 0 });
  ok(dflt.draws === 50, 'au moins 50 tirages par défaut, même hors budget : ' + dflt.draws);
}

section('permuteGrid : la grille rejouée sur chaque permutation');
{
  const lat = plant(E.lattice({ sessions: 40, sigma: 1, seed: 31, minutes: 300 }), 0.5, 120, 10, 300);
  const spec = mk({ trigger: at(119), stop: { type: 'pts', value: 20 }, target: { type: 'none' }, manage: { maxBars: '$mb' }, params: { mb: { v: 10, min: 5, max: 20, step: 5 } } });
  const g = E.op('permuteGrid', { bars: lat, spec, settings: SET, p1: 'mb', xs: [5, 10], draws: 30, seed: 2, budgetMs: Infinity });
  const sw = E.op('sweep', { bars: lat, spec, settings: SET, p1: 'mb', xs: [5, 10] });
  near(g.obs, sw.best.meanR, 1e-12, 'meilleur observé = meilleure cellule du balayage');
  ok(g.configs === 2 && g.draws === 30 && g.p < 0.05 && /meilleure des 2 configurations/.test(g.label), 'dérive plantée : p = ' + g.p + ' contre le meilleur permuté');
  const g0 = E.op('permuteGrid', { bars: E.lattice({ sessions: 40, sigma: 1, seed: 32, minutes: 300 }), spec, settings: SET, p1: 'mb', draws: 30, seed: 2, budgetMs: Infinity });
  ok(g0.p > 0.05, 'sans dérive, le meilleur de la grille n’est pas significatif : p = ' + g0.p.toFixed(3));
}

/* =================================== Balayage =================================== */
section('Balayage : chaque cellule = le run de sa configuration (miroir recalculé après résolution)');
{
  const lat = E.lattice({ sessions: 30, sigma: 1, seed: 12, minutes: 300 });
  const spec = mk({ side: 'both', setup: [{ cmp: '<', a: { f: 'close' }, b: { f: 'vwap', k: '$k' } }], stop: { type: 'pts', value: '$st' }, target: { type: 'r', value: 1.5 },
    params: { k: { v: 0, min: -1, max: 1, step: 0.5 }, st: { v: 2, min: 2, max: 3, step: 1 } } });
  const sw = E.op('sweep', { bars: lat, spec, settings: SET, p1: 'k', p2: 'st' });
  ok(sw.xs.join() === '-1,-0.5,0,0.5,1' && sw.ys.join() === '2,3' && sw.cells.length === 2 && sw.cells[0].length === 5, 'grille tirée de params (min, max, step) : 5 × 2');
  ok(sw.mat.length === 10 && sw.mat.every(r => r.length === sw.keys.length) && sw.keys.length === 30, 'mat[config][séance] : 10 configurations × 30 séances');
  let same = true, rows = true, shorts = 0, bestK = -1, bestV = -Infinity;
  sw.cells.forEach((row, iy) => row.forEach((cell, ix) => {
    const k = iy * 5 + ix, vals = sw.configs[k], r = E.run({ bars: lat, spec, settings: SET, values: vals }), s = r.stats;
    if (vals.k !== sw.xs[ix] || vals.st !== sw.ys[iy]) same = false;
    ['n', 'meanR', 'sdR', 'net', 'pf', 'maxDD', 'winRate', 'costR'].forEach(f => { if (!(cell[f] === s[f] || (cell[f] !== cell[f] && s[f] !== s[f]))) same = false; });
    if (!(cell.sharpe === s.sharpeTrade || (cell.sharpe !== cell.sharpe && s.sharpeTrade !== s.sharpeTrade))) same = false;
    shorts += r.trades.filter(t => t.side < 0).length;
    const m = sw.mat[k], sum = f => m.reduce((a, e) => a + e[f], 0);
    if (sum('n') !== s.n || Math.abs(sum('sumR') - s.meanR * s.n) > 1e-9 || Math.abs(sum('net') - s.net) > 1e-9 || Math.abs(sum('gw') - sum('gl') - s.net) > 1e-9 || Math.abs(sum('sumC') / s.n - s.costR) > 1e-12) rows = false;
    if (s.meanR > bestV) { bestV = s.meanR; bestK = k; }
  }));
  ok(same, 'n, meanR, sdR, net, pf, sharpe, maxDD, winRate et costR de chaque cellule = run individuel');
  ok(shorts > 0, 'les ventes reflétées sont recalculées pour chaque k : ' + shorts + ' ventes');
  ok(rows, 'mat se referme sur la cellule : Σn, ΣsumR, Σnet, Σgw − Σgl, ΣsumC');
  ok(sw.best && sw.best.k === bestK && sw.best.meanR === bestV && sw.best.values.k === sw.configs[bestK].k, 'meilleure configuration (meanR) : k = ' + sw.best.values.k + ', stop ' + sw.best.values.st);
  const one = E.op('sweep', { bars: lat, spec, settings: SET, p1: 'st', xs: [2, 2.5, 3] });
  ok(one.ys.length === 1 && one.ys[0] === null && one.p2 === null && one.cells[0].length === 3 && one.configs[1].st === 2.5 && one.configs[1].k === undefined, 'un seul paramètre : ys = [null], valeurs données par la liste');
  const nb = E.op('sweep', { bars: lat, spec, settings: SET, p1: 'st', xs: [2, 3], objective: 'net', minTrades: 1e9 });
  ok(nb.best === null, 'minTrades hors d’atteinte : aucune meilleure configuration');
  throws(() => E.op('sweep', { bars: lat, spec, settings: SET, p1: 'zz' }), /pas déclaré/, 'paramètre non déclaré refusé');
  throws(() => E.op('sweep', { bars: lat, spec, settings: SET, p1: 'k', xs: Array.from({ length: 30 }, (_, i) => i / 10), p2: 'st', ys: Array.from({ length: 20 }, (_, i) => 2 + i / 10) }), /au plus 400/, 'grille de plus de 400 cellules refusée');
  throws(() => E.op('sweep', { bars: lat, spec, settings: SET, p1: 'k', objective: 'gain' }), /Objectif inconnu/, 'objectif inconnu refusé');
}

/* =================================== Analyse en avant =================================== */
section('Analyse en avant : matrice construite, réponses calculées à la main');
{
  const cell = (n, sumR, extra) => Object.assign({ n, sumR, sumR2: n ? sumR * sumR / n : 0, net: 10 * sumR, gw: sumR > 0 ? 10 * sumR : 0, gl: sumR < 0 ? -10 * sumR : 0, sumC: 0 }, extra);
  const A = [1, 1, -1, -1, 1, 1], B = [-1, -1, 1, 1, -1, -1];
  const mat = [A.map(x => cell(1, x)), B.map(x => cell(1, x))], keys = ['2026-03-02', '2026-03-03', '2026-03-04', '2026-03-05', '2026-03-06', '2026-03-09'];
  const w = E.op('wfa', { mat, keys, configs: [{ p: 1 }, { p: 2 }], wfa: { is: 2, oos: 1, mode: 'rolling' } });
  ok(w.windows.length === 4 && w.windows.map(x => x.best).join() === '0,0,1,0', 'rolling : meilleures IS 0, 0 (égalité → la première), 1, 0');
  ok(w.windows.map(x => x.oosMeanR).join() === '-1,-1,-1,1' && w.windows[2].values.p === 2, 'OOS appliquée telle quelle : −1, −1, −1, +1');
  ok(w.windows[0].isFrom === keys[0] && w.windows[0].isTo === keys[1] && w.windows[0].oosFrom === keys[2] && w.windows[3].oosTo === keys[5], 'bornes des fenêtres en clés');
  near(w.stitched.meanR, -0.5, 1e-12, 'meanR cousue = −2/4');
  near(w.isMeanR, 0.5, 1e-12, 'meanR des meilleurs IS pondérée par les trades = 4/8');
  near(w.wfe, -1, 1e-12, 'wfe = −0,5 / 0,5');
  ok(w.stitched.n === 4 && w.stitched.net === -20 && w.eq.length === 4 && w.eq[3][1] === -20 && w.stitched.maxDD === 30, 'équité OOS cousue par séance : net −20, perte maximale 30');
  const wa = E.op('wfa', { mat, keys, wfa: { is: 2, oos: 1, mode: 'anchored' } });
  ok(wa.windows.map(x => x.best).join() === '0,0,0,0' && wa.windows.map(x => x.oosMeanR).join() === '-1,-1,1,1', 'anchored : IS depuis la 1re séance, meilleure 0 partout');
  near(wa.isMeanR, 4 / 14, 1e-12, 'anchored : dénominateur (2 + 1 + 0 + 1) / (2 + 3 + 4 + 5)');
  near(wa.wfe, 0, 1e-12, 'anchored : wfe = 0');
  const w2 = E.op('wfa', { mat, keys, wfa: { is: 2, oos: 3 } });
  ok(w2.windows.length === 2 && w2.windows[1].oosFrom === keys[5] && w2.windows[1].oosTo === keys[5], 'dernière fenêtre OOS raccourcie aux séances restantes');
  /* minTrades : une configuration trop maigre est exclue, même meilleure */
  const mat3 = [A.map(x => cell(1, x)), [cell(0, 0), cell(1, 3), cell(0, 0), cell(0, 0), cell(0, 0), cell(0, 0)]];
  const w3 = E.op('wfa', { mat: mat3, keys, wfa: { is: 2, oos: 1, minTrades: 2 } });
  ok(w3.windows[0].best === 0, 'minTrades = 2 : la configuration à un seul trade IS est exclue');
  ok(E.op('wfa', { mat: mat3, keys, wfa: { is: 2, oos: 1, minTrades: 1 } }).windows[0].best === 1, 'minTrades = 1 : elle gagne');
  ok(E.op('wfa', { mat: mat3, keys, wfa: { is: 2, oos: 1, minTrades: 9 } }).windows.every(x => x.best === -1 && x.oosN === 0), 'aucune configuration éligible : fenêtre sans trade');
  /* objectif : net et pf choisissent autrement que meanR ; wfe reste en meanR */
  const mat4 = [[cell(1, 2), cell(1, 2), cell(1, 1), cell(1, 1)], [cell(4, 4), cell(4, 4), cell(4, 2), cell(4, 2)]], k4 = keys.slice(0, 4);
  ok(E.op('wfa', { mat: mat4, keys: k4, wfa: { is: 2, oos: 1 } }).windows[0].best === 0 && E.op('wfa', { mat: mat4, keys: k4, wfa: { is: 2, oos: 1, objective: 'net' } }).windows[0].best === 1, 'objectif meanR → 0 ; objectif net → 1');
  const wn = E.op('wfa', { mat: mat4, keys: k4, wfa: { is: 2, oos: 1, objective: 'net' } });
  near(wn.wfe, 0.5 / (14 / 16), 1e-12, 'wfe en meanR quel que soit l’objectif : (4/8) / (14/16)');
  /* dénominateur ≤ costR → null */
  const mat5 = [A.map(x => cell(1, x, { sumC: 0.6 })), B.map(x => cell(1, x, { sumC: 0.6 }))];
  const w5 = E.op('wfa', { mat: mat5, keys, wfa: { is: 2, oos: 1 } });
  ok(w5.wfe === null && Math.abs(w5.costR - 0.6) < 1e-12, 'meanR IS 0,5 ≤ costR 0,6 : wfe = null');
  throws(() => E.op('wfa', { mat, keys, wfa: { is: 6, oos: 1 } }), /au moins 7/, 'pas assez de séances : refus');
  throws(() => E.op('wfa', { mat, keys, wfa: { is: 2, oos: 1, mode: 'glissant' } }), /mode/, 'mode inconnu refusé');
  /* sel et hors échantillon sur une matrice donnée */
  throws(() => E.op('wfa', { mat, keys, oosFrom: '2026-03-06', wfa: { is: 2, oos: 1 } }), /Hors échantillon/, 'oosFrom sans sel : refus');
  const w6 = E.op('wfa', { mat, keys, oosFrom: '2026-03-06', sel: { to: '2026-03-05' }, wfa: { is: 2, oos: 1 } });
  ok(w6.windows.length === 2 && w6.eq[w6.eq.length - 1][0] === '2026-03-05', 'sel avant la coupure : seules les colonnes de sel sont lues');
  /* sur un jeu : le balayage est fait par l’opération, la fenêtre ne relance rien */
  const lat = E.lattice({ sessions: 24, sigma: 1, seed: 13, minutes: 300 });
  const spec = mk({ stop: { type: 'pts', value: '$st' }, params: { st: { v: 2, min: 1, max: 3, step: 1 } } });
  const sw = E.op('sweep', { bars: lat, spec, settings: SET, p1: 'st' });
  const wa2 = E.op('wfa', { bars: lat, spec, settings: SET, p1: 'st', wfa: { is: 8, oos: 4 } }), wb2 = E.op('wfa', { mat: sw.mat, keys: sw.keys, configs: sw.configs, wfa: { is: 8, oos: 4 } });
  ok(JSON.stringify(wa2.windows) === JSON.stringify(wb2.windows) && wa2.wfe === wb2.wfe, 'wfa sur un jeu = wfa sur la matrice de son balayage');
}

/* =================================== Stress des coûts =================================== */
section('Stress des coûts : monotonie, glissement d’équilibre, cas « na »');
{
  const lat = plant(E.lattice({ sessions: 60, sigma: 1, seed: 41, minutes: 300 }), 0.25, 120, 10, 300);
  const spec = mk({ trigger: at(119), stop: { type: 'pts', value: 4 }, target: { type: 'none' }, manage: { maxBars: 10 }, costs: { commissionRT: null, slipTicks: 1 } });
  const S1 = Object.assign({}, SET, { commissionRT: 1 });
  const st = E.op('stress', { bars: lat, spec, settings: S1 });
  ok(st.slips.join() === '0,1,2,3,4' && st.mults.join() === '1,1.5,2' && st.throughs.join() === '0,1,2' && st.rows.length === 45, 'grille 5 glissements × 3 commissions × 3 dépassements');
  ok(st.comm === 1 && st.slip === 1 && st.legs > 0, 'coûts déclarés : commission des réglages, 1 tick par jambe');
  let monoS = true, monoC = true;
  for (let it = 0; it < 3; it++) for (let im = 0; im < 3; im++) for (let is = 1; is < 5; is++) if (!(st.meanR[it][im][is] < st.meanR[it][im][is - 1])) monoS = false;
  for (let it = 0; it < 3; it++) for (let is = 0; is < 5; is++) for (let im = 1; im < 3; im++) if (!(st.net[it][im][is] < st.net[it][im - 1][is])) monoC = false;
  ok(monoS, 'meanR décroît avec le glissement, à chaque commission et chaque dépassement');
  ok(monoC, 'le net décroît avec la commission');
  const run = E.run({ bars: lat, spec, settings: S1 });
  near(st.base.meanR, run.stats.meanR, 1e-12, 'ligne de base = run aux coûts déclarés');
  const m = st.meanR[0][0];
  ok(m[0] > 0 && m[4] < 0 && typeof st.breakEven === 'number' && st.breakEven > 0 && st.breakEven < 4, 'meanR passe sous zéro dans la grille : équilibre à ' + (typeof st.breakEven === 'number' ? st.breakEven.toFixed(2) : st.breakEven) + ' tick par jambe');
  const s0 = Math.floor(st.breakEven);
  near(st.breakEven, s0 + m[s0] / (m[s0] - m[s0 + 1]), 1e-12, 'interpolation linéaire entre les deux glissements qui encadrent zéro');
  ok(st.criterion.kind === 'slip' && st.criterion.slip === 2 && st.criterion.meanR === m[2] && st.criterion.pass === (m[2] > 0), 'critère : meanR à +1 tick par jambe');
  const big = E.op('stress', { bars: plant(E.lattice({ sessions: 60, sigma: 1, seed: 41, minutes: 300 }), 1, 120, 10, 300), spec, settings: S1 });
  ok(big.breakEven === null && big.beyond === true, 'toujours positif à 4 ticks : équilibre au-delà de la grille');
  const ov = E.op('stress', { bars: lat, spec, settings: S1, override: { slipTicks: 2, commissionRT: 3 } });
  ok(ov.slip === 2 && ov.comm === 3 && ov.criterion.slip === 3 && ov.meanR[0][0].every((x, i) => x < st.meanR[0][0][i]), 'coûts planchers (override) : base à 2 ticks et 3 $, critère à 3 ticks, grille à commission 3 $');
  near(ov.base.meanR, E.run({ bars: lat, spec, settings: S1, override: { slipTicks: 2, commissionRT: 3 } }).stats.meanR, 1e-12, 'base sous override = run sous override');

  /* aucune jambe glissée : entrée limite, sortie à l’objectif → « na », critère sur le dépassement */
  const T0 = Date.UTC(2026, 0, 5, 23, 0), hb = [];
  for (let k = 0; k < 60; k++) hb.push({ t: T0 + k * MIN, o: 100, h: 100, l: 100, c: 100, v: 10 });
  Object.assign(hb[11], { o: 100, h: 100, l: 99.25, c: 99.5 });
  Object.assign(hb[12], { o: 99.5, h: 100.75, l: 99.5, c: 100.5 });
  for (let k = 13; k < 60; k++) Object.assign(hb[k], { o: 100.5, h: 100.5, l: 100.5, c: 100.5 });
  const hs = mk({ session: { to: '09:00', flat: '09:00', warmup: 0 }, trigger: at(10), entry: { type: 'limit', at: { f: 'close' }, offset: 2 }, stop: { type: 'pts', value: 2 }, target: { type: 'pts', value: 1 }, manage: { maxBars: null }, fill: 'pessimiste', costs: { commissionRT: null, slipTicks: 1 } });
  const na = E.op('stress', { bars: hb, spec: hs, settings: S1 });
  ok(na.base.n === 1 && na.legs === 0 && na.breakEven === 'na', 'entrée limite et sortie à l’objectif : aucune jambe glissée, équilibre « na »');
  ok(na.meanR[0][0].every(x => x === 0.25) && na.meanR[0][1].every(x => x === 0.125) && na.meanR[0][2].every(x => x === 0), 'glissement sans effet ; commission ×1, ×1,5, ×2 : 0,25, 0,125, 0 R (calcul à la main)');
  ok(na.meanR[1][0][0] === 0.25 && na.n[2][0][0] === 0 && na.meanR[2][0][0] !== na.meanR[2][0][0], 'dépassement 1 tick : rempli ; 2 ticks : l’ordre expire');
  ok(na.criterion.kind === 'through' && na.criterion.through === 1 && na.criterion.meanR === 0.25 && na.criterion.pass === true, 'critère lu sur le dépassement à 1 tick');
}

/* =================================== Bootstrap et passage prop =================================== */
section('Bootstrap stationnaire : couverture de l’intervalle à 90 % sur une moyenne connue');
{
  const mu = 0.1;
  let cover = 0, coverA = 0;
  const reps = 120;
  for (let rep = 0; rep < reps; rep++) {
    const r = mulberry(1000 + rep), recs = [];
    for (let s = 0; s < 150; s++) {
      const n = Math.floor(r() * 3); let sumR = 0;
      for (let k = 0; k < n; k++) sumR += mu + gauss(r);
      recs.push({ pnl: 20 * sumR, n, lo: Math.min(0, 20 * sumR) - 5, hi: Math.max(0, 20 * sumR) + 5, sumR });
    }
    const b = E.op('boot', { records: recs, draws: 400, seed: rep + 1, perYear: 150 });
    if (b.meanR.lo <= mu && mu <= b.meanR.hi) cover++;
    if (b.annual.lo <= 20 * mu * 150 && 20 * mu * 150 <= b.annual.hi) coverA++;
  }
  ok(cover / reps >= 0.8 && cover / reps <= 0.97, 'meanR : l’intervalle couvre la vraie moyenne dans ' + (100 * cover / reps).toFixed(1) + ' % des cas (attendu ≈ 90 %)');
  ok(coverA / reps >= 0.8 && coverA / reps <= 0.97, 'net annuel : couverture ' + (100 * coverA / reps).toFixed(1) + ' %');
}

section('Bootstrap : séances sans trade comprises, net annuel, éventail');
{
  const recs = [];
  for (let s = 0; s < 50; s++) recs.push(s % 5 === 0 ? { key: null, pnl: 0, n: 0, lo: 0, hi: 0, sumR: 0 } : { pnl: s % 2 ? 30 : -10, n: 1, lo: -12, hi: 35, sumR: s % 2 ? 1.5 : -0.5 });
  const b = E.op('boot', { records: recs, draws: 500, seed: 3, perYear: 250 });
  ok(b.sessions === 50 && b.trades === 40, 'les séances sans trade sont gardées : 50 séances, 40 trades');
  near(b.meanR.obs, recs.reduce((s, x) => s + x.sumR, 0) / 40, 1e-12, 'meanR observée = ΣsumR / Σn');
  near(b.annual.obs, recs.reduce((s, x) => s + x.pnl, 0) * 250 / 50, 1e-12, 'net annuel = Σpnl × séances par an / séances');
  ok(b.meanR.lo < b.meanR.obs && b.meanR.obs < b.meanR.hi && b.annual.lo < b.annual.hi, 'intervalles autour de l’observé');
  const q = b.fan.q;
  ok(b.fan.horizon === 60 && ['p05', 'p25', 'p50', 'p75', 'p95'].every(k => q[k].length === 61 && q[k][0] === 0), 'éventail : 61 points (départ à zéro) pour chaque quantile');
  let ordered = true; for (let t = 0; t <= 60; t++) if (!(q.p05[t] <= q.p25[t] && q.p25[t] <= q.p50[t] && q.p50[t] <= q.p75[t] && q.p75[t] <= q.p95[t])) ordered = false;
  ok(ordered, 'quantiles ordonnés à chaque séance');
  near(q.p50[60], 60 * recs.reduce((s, x) => s + x.pnl, 0) / 50, 0.35, 'médiane à 60 séances ≈ 60 × P&L moyen par séance');
  ok(b.fan.paths.length === 10 && b.fan.paths[0].length === 61, 'dix trajectoires gardées pour le dessin');
  const b2 = E.op('boot', { records: recs, draws: 50 });
  ok(b2.perYear === 252, 'sans clé de séance : 252 séances par an');
}

section('Passage prop : cas déterministes calculés à la main');
{
  const acc = { size: 50000, target: 3000, maxLoss: 2000, dd: 'static', lockAt: 52100, dailyLimit: null, dailyMode: 'pause', consistency: null };
  const P = (recs, a, o) => E.op('boot', Object.assign({ records: recs, draws: 20, seed: 1, account: Object.assign({}, acc, a) }, o)).prop;
  const win = [{ pnl: 500, n: 1, lo: 0, hi: 500, sumR: 1 }];
  let p = P(win);
  ok(p.pPass === 1 && p.medPass === 6, '+500 par séance, objectif 3 000 : réussite à la 6e séance');
  ok(P(win, {}, { minDays: 10 }).medPass === 10, 'minDays = 10 : réussite repoussée à la 10e séance');
  ok(P([{ pnl: 2000, n: 1, lo: 0, hi: 2000, sumR: 1 }], { consistency: 50 }).medPass === 2, 'consistance 50 % : 2 × 2 000, meilleure séance = 50 % du profit, réussite à la 2e');
  p = P([{ pnl: 2500, n: 1, lo: 0, hi: 2500, sumR: 1 }], { consistency: 40 });
  ok(p.pPass === 1 && p.medPass === 3, 'consistance 40 % : +2 500 par séance, la réussite attend que 2 500 ≤ 40 % du profit (3e séance, pas la 2e)');
  const lose = [{ pnl: -500, n: 1, lo: -500, hi: 0, sumR: -1 }];
  p = P(lose);
  ok(p.pFail === 1 && p.medFail === 4 && p.cause.never === 20, '−500 par séance, plancher statique −2 000 : échec à la 4e séance, jamais en gain');
  p = P(lose, { dailyLimit: 300 });
  ok(p.pFail === 1 && p.medFail === 7, 'limite du jour 300 (pause) : la séance s’arrête à −300, échec à la 7e quand le creux passe sous le plancher');
  p = P(lose, { dailyLimit: 300, dailyMode: 'fail' });
  ok(p.pFail === 1 && p.medFail === 1 && p.cause.daily === 20, 'limite du jour en mode « fail » : échec dès la 1re séance');
  const spike = [{ pnl: 100, n: 1, lo: 0, hi: 1000, sumR: 0.2 }];
  p = P(spike, { dd: 'intraday', maxLoss: 500, lockAt: 99999, target: 3000 });
  ok(p.pFail === 1 && p.medFail === 1 && p.cause.gain === 0, 'suiveur intraday : sommet à +1 000 puis clôture à +100, plancher à +500 franchi dès la 1re séance');
  p = P(spike, { dd: 'eod', maxLoss: 500, lockAt: 99999, target: 3000 }, { maxDays: 40 });
  ok(p.pPass === 1 && p.medPass === 30, 'même séance en fin de jour : le plancher suit la clôture, réussite à la 30e séance');
  p = P(win, { target: 1e6 }, { maxDays: 15 });
  ok(p.pNone === 1 && p.maxDays === 15, 'objectif hors d’atteinte en 15 séances : non-conclusion');
  const up = { pnl: 400, n: 1, lo: 0, hi: 400, sumR: 1 }, lk = [up, up, up, { pnl: -900, n: 1, lo: -900, hi: 0, sumR: -1 }];
  ok(P(lk, { dd: 'eod', maxLoss: 1000, lockAt: 50300, target: 1e6 }, { draws: 200, maxDays: 30 }).pFail < P(lk, { dd: 'eod', maxLoss: 1000, lockAt: 1e9, target: 1e6 }, { draws: 200, maxDays: 30 }).pFail, 'verrou du suiveur : le plancher se fige, moins d’échecs qu’un suiveur sans verrou');
  throws(() => E.op('boot', { records: win, account: { size: 50000 } }), /size, target et maxLoss/, 'compte incomplet refusé');
}

section('Passage prop contre T.lib.risk.simulate (cas paramétrique, même direction et même ordre de grandeur)');
{
  const S = 200, G = 300, A = 2000, B = 3000, days = 30;
  function recsFor(p, seed) {
    const r = mulberry(seed), N = 2000, nw = Math.round(p * N), out = [];
    for (let k = 0; k < N; k++) {
      const u = 1e-9 + r() * (1 - 2e-9);
      if (k < nw) out.push({ pnl: G, n: 1, lo: -G * S * (1 - u) / (u * S + G), hi: G, sumR: 1.5 });
      else out.push({ pnl: -S, n: 1, lo: -S, hi: S * G * (1 - u) / (u * G + S), sumR: -1 });
    }
    for (let k = N - 1; k > 0; k--) { const j = Math.floor(r() * (k + 1)); const x = out[k]; out[k] = out[j]; out[j] = x; }
    return out;
  }
  const res = [];
  for (const [p, dd] of [[0.45, 'static'], [0.6, 'static'], [0.45, 'intraday'], [0.6, 'eod']]) {
    const sim = RK.simulate({ p, win: 1.5, loss: 1, risk: S, tpd: 1, cost: 0, target: B, maxLoss: A, dd, lock: Infinity, daily: 0, days, n: 4000, seed: 7 });
    const bt = E.op('boot', { records: recsFor(p, 11), draws: 50, propDraws: 4000, seed: 5, maxDays: days, account: { size: 50000, target: B, maxLoss: A, dd, lockAt: 1e12, dailyLimit: null } }).prop;
    res.push({ p, dd, sim, bt });
    ok(Math.abs(bt.pPass - sim.pPass) < 0.06 && Math.abs(bt.pFail - sim.pFail) < 0.06, 'p = ' + p + ', ' + dd + ' : réussite ' + bt.pPass.toFixed(3) + ' contre ' + sim.pPass.toFixed(3) + ', échec ' + bt.pFail.toFixed(3) + ' contre ' + sim.pFail.toFixed(3));
  }
  ok(res[1].bt.pPass > res[0].bt.pPass && res[1].sim.pPass > res[0].sim.pPass, 'plus d’avantage, plus de réussites, dans les deux modèles');
  ok(res[2].bt.pFail > res[0].bt.pFail && res[2].sim.pFail > res[0].sim.pFail, 'le suiveur intraday fait échouer plus souvent que le plancher statique, dans les deux modèles');
  ok(res[0].bt.medPass > 0 && Math.abs(res[0].bt.medPass - res[0].sim.medPass) <= 3, 'jours médians de réussite : ' + res[0].bt.medPass + ' contre ' + res[0].sim.medPass);
}

/* =================================== Déterminisme, progression, sélection =================================== */
section('Déterminisme, progression, sel et hors échantillon');
{
  const lat = E.lattice({ sessions: 26, sigma: 1, seed: 17, minutes: 300 });
  const spec = mk({ stop: { type: 'pts', value: '$st' }, params: { st: { v: 2, min: 1, max: 3, step: 1 } } });
  const base = { bars: lat, spec, settings: SET, seed: 4 };
  const J = x => JSON.stringify(x);
  const ops = [['random', { draws: 30 }], ['permute', { draws: 8, minDraws: 1, budgetMs: Infinity }], ['permuteGrid', { p1: 'st', draws: 4, minDraws: 1, budgetMs: Infinity }], ['sweep', { p1: 'st' }], ['stress', {}], ['boot', { draws: 200, account: { size: 50000, target: 3000, maxLoss: 2000 } }], ['wfa', { p1: 'st', wfa: { is: 6, oos: 3 } }]];
  ops.forEach(([op, extra]) => {
    const a1 = E.op(op, Object.assign({}, base, extra)), a2 = E.op(op, Object.assign({}, base, extra));
    const strip = x => J(Object.assign({}, x, { ms: 0, cut: false }));
    ok(strip(a1) === strip(a2), op + ' : déterministe à graine égale');
    const calls = [];
    E.op(op, Object.assign({}, base, extra, { onProgress: (k, n) => calls.push([k, n]) }));
    const last = calls[calls.length - 1];
    ok(calls.length > 0 && last[0] === last[1] && calls.every((c, i) => i === 0 || c[0] >= calls[i - 1][0]), op + ' : progression croissante jusqu’à n/n (' + calls.length + ' appels)');
  });
  ok(J(E.op('random', Object.assign({}, base, { draws: 30, seed: 5 })).means) !== J(E.op('random', Object.assign({}, base, { draws: 30 })).means), 'random : autre graine, autres tirages');
  ok(J(E.op('boot', Object.assign({}, base, { draws: 200, seed: 5 })).means) !== J(E.op('boot', Object.assign({}, base, { draws: 200 })).means), 'boot : autre graine, autres tirages');
  /* hors échantillon : refus sans sel, sel respectée */
  const oosFrom = lat.keys[20];
  ['random', 'permute', 'permuteGrid', 'sweep', 'stress', 'boot', 'wfa'].forEach(op => {
    throws(() => E.op(op, Object.assign({}, base, { oosFrom, p1: 'st', draws: 3, minDraws: 1, wfa: { is: 4, oos: 2 } })), /Hors échantillon/, op + ' : oosFrom sans sel refusé');
  });
  const sel = { from: lat.keys[2], to: lat.keys[19] };
  const sw = E.op('sweep', Object.assign({}, base, { oosFrom, sel, p1: 'st' }));
  ok(sw.keys.length === 18 && sw.keys[0] === sel.from && sw.keys[17] === sel.to, 'sweep : seules les séances de sel forment les colonnes de mat');
  const bt = E.op('boot', Object.assign({}, base, { oosFrom, sel, draws: 50 }));
  ok(bt.sessions === 18, 'boot : 18 séances de sel');
  const rd = E.op('random', Object.assign({}, base, { oosFrom, sel, draws: 10 }));
  ok(rd.n === E.run(Object.assign({}, base, { oosFrom, sel })).trades.length, 'random : la valeur observée est celle du run sur sel');
  const ro = E.op('random', Object.assign({}, base, { oosFrom, oos: true, sel: { from: oosFrom }, draws: 10 }));
  ok(ro.n > 0, 'ouverture hors échantillon (oos: true) : entrées au hasard rejouées sur les seules séances hors échantillon');
  const recs = E.run(Object.assign({}, base)).sessions;
  throws(() => E.op('boot', { records: recs, oosFrom }), /Hors échantillon/, 'boot sur enregistrements : oosFrom sans sel refusé');
  ok(E.op('boot', { records: recs, oosFrom, sel: { to: lat.keys[9] }, draws: 20 }).sessions === 10, 'boot sur enregistrements : filtrés par sel');
  ok(E.HEAVY.random && E.HEAVY.permute && E.HEAVY.permuteGrid && E.HEAVY.sweep && E.HEAVY.wfa && E.HEAVY.boot && !E.HEAVY.stress, 'opérations lourdes refusées hors worker : random, permute, permuteGrid, sweep, wfa, boot');
}

section('Exécuteur local : les opérations lourdes sont refusées dans le fil principal');
{
  const ex = E.worker({ local: true });
  const lat = E.lattice({ sessions: 4, sigma: 1, seed: 1, minutes: 120 });
  await ex.load('fp1', lat);
  for (const op of ['random', 'permute', 'sweep', 'wfa', 'boot']) {
    let msg = '';
    try { await ex.call(op, { spec: mk({}), settings: SET }).promise; } catch (e) { msg = e.message; }
    ok(/impossible sur cet appareil/i.test(msg), op + ' en local : ' + msg);
  }
  const st = await ex.call('stress', { spec: mk({ session: { to: '02:00', flat: '02:00' } }), settings: SET }).promise;
  ok(st.rows.length === 45, 'stress tourne en local (rejoue seulement l’exécution)');
  ex.close();
}

/* =================================== Performance =================================== */
section('Performance : une année synthétique (350 000 barres)');
{
  const lat = E.lattice({ sessions: 254, sigma: 1, seed: 11 });
  const spec = mk({ side: 'both', session: { to: '09:00', flat: '09:00' }, setup: [{ cmp: '<', a: { f: 'close' }, b: { f: 'vwap' } }],
    trigger: { all: [{ cmp: '<=', a: { f: 'low' }, b: { f: 'vwap', k: '$k' } }, { cmp: '>', a: { f: 'close' }, b: { f: 'vwap', k: '$k' } }] },
    stop: { type: 'pts', value: '$st' }, target: { type: 'r', value: 2 }, manage: { maxBars: 60 }, fill: 'pessimiste',
    risk: { maxPerSession: 3, maxLossesPerSession: 2, dailyStopUsd: 400, minStopTicks: 4 }, costs: { commissionRT: 1, slipTicks: 1 },
    params: { k: { v: -1, min: -2.25, max: 0, step: 0.25 }, st: { v: 4, min: 2, max: 11, step: 1 } } });
  E.op('random', { bars: lat, spec, settings: SET, draws: 20 });
  let t0 = Date.now(); const rd = E.op('random', { bars: lat, spec, settings: SET, draws: 200, seed: 1 }); const dr = Date.now() - t0;
  ok(rd.n > 300 && dr < 1000, 'random, 200 tirages : ' + dr + ' ms pour ' + rd.n + ' trades observés (borne 1 000 ms)');
  t0 = Date.now(); const sw = E.op('sweep', { bars: lat, spec, settings: SET, p1: 'k', p2: 'st' }); const ds = Date.now() - t0;
  ok(sw.mat.length === 100 && ds < 6000, 'sweep, 100 cellules : ' + ds + ' ms (borne 6 000 ms)');
  t0 = Date.now(); const w = E.op('wfa', { mat: sw.mat, keys: sw.keys, wfa: { is: 60, oos: 20, mode: 'anchored' } }); const dw = Date.now() - t0;
  ok(w.windows.length === 10 && dw < 1000, 'wfa sur la matrice : ' + dw + ' ms');
  t0 = Date.now(); const st = E.op('stress', { bars: lat, spec, settings: SET }); const dst = Date.now() - t0;
  ok(st.rows.length === 45 && dst < 2000, 'stress, 47 exécutions : ' + dst + ' ms (borne 2 000 ms)');
  t0 = Date.now(); const pm = E.op('permute', { bars: lat, spec, settings: SET, draws: 3, minDraws: 1, budgetMs: Infinity }); const dp = Date.now() - t0;
  ok(pm.draws === 3 && dp / 3 < 1200, 'permute : ' + Math.round(dp / 3) + ' ms par tirage (100 tirages ≈ ' + Math.round(dp / 30) / 10 + ' s ; budget ajusté à 60 s)');
}

  console.log((fails ? 'ÉCHECS : ' + fails : 'OK') + ' — ' + passes + ' contrôles réussis, ' + fails + ' échoués');
  process.exit(fails ? 1 : 0);
})().catch(e => { console.error('ÉCHEC (exception)', e && e.stack || e); process.exit(1); });
