// Tests du desk « Métriques & espaces » : node test/perf.test.js (sortie non nulle si échec).
// Les valeurs de référence ont été calculées à la main en Python pur (stdlib, sans numpy),
// indépendamment du code JavaScript, sur la série PNL ci-dessous.
const fs = require('fs');
const { T, lib: P } = require('./harness')('perf');
let fails = 0, passes = 0;
function ok(cond, msg) { if (cond) passes++; else { fails++; console.error('ÉCHEC', msg); } }
function near(a, b, tol, msg) { const good = typeof a === 'number' && typeof b === 'number' && (a === b || Math.abs(a - b) <= tol * Math.max(1, Math.abs(b))); ok(good, msg + ' : ' + a + ' attendu ' + b); }
function section(t) { console.log('· ' + t); }

const PNL = [300, -150, -150, 450, -150, 225, -150, -150, 600, -75, 300, -150, 150, -150, -150, 0];
const RISK = 150, CAP = 10000;
const T0 = Date.UTC(2026, 8, 7, 8, 0); // lundi 7 septembre 2026, 08:00 UTC
const trades = PNL.map((v, i) => ({ at: T0 + Math.floor(i / 2) * 864e5 + (i % 2) * 3600e3, pnl: v, r: v / RISK }));
const M = P.metrics(trades, { tpd: 2, days: 252, capital: CAP, risk: RISK, trials: 10, tz: 'UTC' });
const REF = {
  mean: 46.875, sd: 253.78386473532947, sharpe: 0.18470441392673176, sharpeAnn: 4.146603808432245,
  downDev: 107.71054962258803, sortino: 0.4351941398892446, sortinoAnn: 9.770084209183944,
  profitFactor: 1.588235294117647, omega100: 0.6263736263736264, payoff: 2.3823529411764706, winRate: 0.375,
  kelly: 0.11265432098765432, halfKelly: 0.05632716049382716, expR: 0.3125, sqn: 0.7388176557069271,
  tailRatio: 3.25, commonSense: 5.161764705882352, skew: 0.8886672194069639, exKurt: -0.5727960946587594,
  var95h: 150, var99h: 150, var95g: 370.5623103716686, var99g: 543.514554192902, var95cf: 305.6231042333695,
  var99cf: 268.2685223503272, cvar95h: 150, cvar95g: 476.60822812829633, maxDD: 300, maxDDpct: 0.02912621359223301,
  longestUnder: 3, net: 750, recovery: 2.5, annRet: 2.3625, cagr: 8.758130546954783, calmar: 81.1125,
  mar: 300.6958154454475, ulcer: 0.01614919297874791, martin: 146.292139991702, sterling: 104.80638727252143,
  burke: 44.36130044790851, wilsonLo: 0.18481232558863642, wilsonHi: 0.6135895945449727, maxWinStreak: 1,
  maxLossStreak: 2, psr: 0.7813656364181669, sr0_10: 0.3936495753364375, dsr10: 0.18976482707911485,
  minTRL: 68.25306556461742, rho1: -0.4666120815138282, runs: 12, runsMu: 8.2, runsZ: 2.128068099268783,
  tstat: 0.738817655706927, mddNull: 1272.2836219814121,
  episodes: [[1, 4, 300], [4, 6, 150], [6, 9, 300], [9, 11, 75], [11, 13, 150], [13, null, 300]],
  esp_055_2_001: 0.64, pstar_2_001: 0.33666666666666667, kg_01_05_2: 0.038480520568064155, kfstar_05_2: 0.25,
  ruin_mu: 73.76, ruin_s2: 50625, pobj_2000_3000: 0.9970563645257464, ruin_2000_3000: 0.002943635474253581,
  ruin_neg: 0.919045180939882, shAnn_055_2_001_504: 9.626898343556544, wall_010: 619
};
// Le Python utilise statistics.NormalDist (Φ exacte) ; le socle utilise une approximation
// d’erf à 1,5·10⁻⁷ et l’algorithme d’Acklam pour Φ⁻¹ : tolérances en conséquence.
const E = 1e-12, EN = 2e-6;

section('Rendement ajusté au risque');
near(M.mean, REF.mean, E, 'moyenne');
near(M.sd, REF.sd, E, 'écart-type n − 1');
near(M.sharpe, REF.sharpe, E, 'Sharpe par trade');
near(M.sharpeAnn, REF.sharpeAnn, E, 'Sharpe annualisé √504');
near(M.downDev, REF.downDev, E, 'écart de baisse, divisé par N total');
near(M.sortino, REF.sortino, E, 'Sortino MAR = 0');
near(M.sortinoAnn, REF.sortinoAnn, E, 'Sortino annualisé');
near(M.calmar, REF.calmar, 1e-10, 'Calmar');
near(M.mar, REF.mar, 1e-10, 'MAR');
near(M.annRet, REF.annRet, E, 'rendement annualisé arithmétique');
near(M.cagr, REF.cagr, 1e-10, 'TCAC');
near(M.ulcer, REF.ulcer, 1e-12, 'Ulcer Index');
near(M.martin, REF.martin, 1e-10, 'ratio de Martin');
near(M.sterling, REF.sterling, 1e-10, 'Sterling (Bacon, k plus profonds)');
near(M.burke, REF.burke, 1e-10, 'Burke');
near(M.omega0, REF.profitFactor, E, 'Omega(0) = facteur de profit');
near(P.omega(PNL, 100), REF.omega100, E, 'Omega(100)');
near(M.psr, REF.psr, EN, 'PSR contre SR* = 0');
near(M.sr0, REF.sr0_10, 1e-7, 'SR₀ du DSR, N = 10');
near(M.dsr, REF.dsr10, EN, 'DSR, N = 10');
near(M.minTRL, REF.minTRL, 1e-7, 'MinTRL');
ok(P.dsr(0.2, 100, 1, 0, 0).dsr === P.psr(0.2, 100, 0, 0, 0), 'DSR à un seul essai = PSR (rien à sélectionner)');
ok(P.minTRL(-0.1, 0, 0, 0) === Infinity, 'MinTRL infini pour un Sharpe négatif');
near(P.psr(0, 50, 0, 0, 0), 0.5, 1e-7, 'PSR d’un Sharpe nul = 1/2');

section('Gains et pertes');
near(M.pf, REF.profitFactor, E, 'facteur de profit');
near(M.payoff, REF.payoff, E, 'payoff ratio');
near(M.winRate, REF.winRate, E, 'taux de réussite (un nul ne gagne pas)');
near(M.kelly, REF.kelly, E, 'Kelly p − (1 − p)/b');
near(M.halfKelly, REF.halfKelly, E, 'demi-Kelly');
near(M.expR, REF.expR, E, 'espérance en R');
near(M.sqn, REF.sqn, 1e-12, 'SQN plafonné à 100');
near(M.tstat, REF.tstat, 1e-12, 't de Student');
near(M.wilson.lo, REF.wilsonLo, 1e-8, 'Wilson borne basse');
near(M.wilson.hi, REF.wilsonHi, 1e-8, 'Wilson borne haute');
near(M.net, REF.net, E, 'profit net');
near(M.recovery, REF.recovery, E, 'facteur de récupération');
{
  const days = []; for (let i = 0; i < PNL.length; i += 2) days.push(PNL[i] + PNL[i + 1]);
  const neg = -days.filter(v => v < 0).reduce((a, b) => a + b, 0), tot = days.reduce((a, b) => a + b, 0);
  near(M.gpr, tot / neg, E, 'gain-to-pain = Σ jours / |Σ jours négatifs|');
  ok(M.gprBasis === 'jours' && M.daysN === 8, 'gain-to-pain calculé sur 8 jours');
  const noDates = P.metrics(PNL.map(v => ({ at: null, pnl: v, r: v / RISK })), { capital: CAP, risk: RISK });
  near(noDates.gpr, noDates.pf - 1, E, 'sans dates, gain-to-pain = PF − 1');
}

section('Queues');
near(M.skew, REF.skew, 1e-12, 'asymétrie (moments de population)');
near(M.exKurt, REF.exKurt, 1e-12, 'kurtosis en excès');
near(M.tail, REF.tailRatio, E, 'tail ratio');
near(M.csr, REF.commonSense, E, 'common sense ratio');
near(M.var95h, REF.var95h, E, 'VaR 95 historique');
near(M.var99h, REF.var99h, E, 'VaR 99 historique');
near(M.var95g, REF.var95g, 1e-7, 'VaR 95 gaussienne');
near(M.var99g, REF.var99g, 1e-7, 'VaR 99 gaussienne');
near(M.var95cf, REF.var95cf, 1e-7, 'VaR 95 Cornish-Fisher');
near(M.var99cf, REF.var99cf, 1e-7, 'VaR 99 Cornish-Fisher');
ok(M.cfOk === false, 'Cornish-Fisher non monotone détecté (VaR 99 < VaR 95)');
near(M.cvar95h, REF.cvar95h, E, 'CVaR 95 historique');
near(M.cvar95g, REF.cvar95g, 1e-7, 'CVaR 95 gaussienne');
near(P.cornishFisher(-1.645, 0, 0), -1.645, E, 'Cornish-Fisher sans asymétrie ni kurtosis = z');

section('Drawdown');
near(M.maxDD, REF.maxDD, E, 'drawdown maximal $');
near(M.maxDDpct, REF.maxDDpct, E, 'drawdown maximal %');
ok(M.longest === REF.longestUnder, 'plus longue durée sous l’eau en trades');
ok(JSON.stringify(M.D.episodes.map(e => [e.start, e.end, e.depth])) === JSON.stringify(REF.episodes), 'épisodes de drawdown');
near(M.longestDays, 2 - 1 / 24, 1e-9, 'plus longue durée sous l’eau en jours : du trade 6 (mardi 9 h) au trade 9 (jeudi 8 h)');
near(M.mddNull, REF.mddNull, 1e-9, 'drawdown nul attendu √(π/2)·σ·√n');

section('Régularité');
ok(M.streaks.win === REF.maxWinStreak && M.streaks.loss === REF.maxLossStreak, 'plus longues séries');
near(M.rho1, REF.rho1, 1e-12, 'autocorrélation d’ordre 1');
ok(M.runs.runs === REF.runs, 'nombre de suites');
near(M.runs.mu, REF.runsMu, E, 'suites attendues');
near(M.runs.z, REF.runsZ, 1e-12, 'z de Wald-Wolfowitz');
{
  const grouped = P.runsTest([1, 1, 1, 1, 1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1]);
  ok(grouped.z < -1.96, 'des gains et pertes groupés donnent z < −1,96 (' + grouped.z.toFixed(2) + ')');
}

section('Lois nulles contrôlées par simulation');
{
  // Drawdown maximal d’une marche sans dérive : √(π/2)·σ·√n, à la correction de pas discret près.
  const rnd = T.rng(11); let acc = 0; const N = 400, PATHS = 3000;
  for (let k = 0; k < PATHS; k++) { let eq = 0, pk = 0, dd = 0; for (let i = 0; i < N; i++) { const u1 = Math.max(rnd(), 1e-300), u2 = rnd(); eq += Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2); if (eq > pk) pk = eq; if (pk - eq > dd) dd = pk - eq; } acc += dd; }
  const mc = acc / PATHS, th = P.mddNull(1, N);
  ok(mc < th && mc > 0.9 * th, 'drawdown nul : simulation ' + mc.toFixed(2) + ' sous la forme continue ' + th.toFixed(2) + ', à moins de 10 %');
  // Plus longue série de pertes au hasard
  const q = 0.6, n = 300; let s = 0;
  for (let k = 0; k < 2000; k++) { let c = 0, b = 0; for (let i = 0; i < n; i++) { if (rnd() < q) { c++; if (c > b) b = c; } else c = 0; } s += b; }
  const mcRun = s / 2000, thRun = P.longestRunNull(n, q);
  ok(Math.abs(mcRun - thRun) < 1.2, 'plus longue série : simulation ' + mcRun.toFixed(2) + ' contre ' + thRun.toFixed(2));
  // Sharpe sans avantage : écart-type ≈ 1/√n
  const sh = []; for (let k = 0; k < 2000; k++) { const x = []; for (let i = 0; i < 100; i++) x.push(rnd() - 0.5); sh.push(P.sharpe(x)); }
  const sd = T.stats.sd(sh);
  ok(Math.abs(sd - 0.1) < 0.012, 'Sharpe nul : écart-type ' + sd.toFixed(4) + ' ≈ 1/√100');
}

section('Le mur d’échantillon d’ALP nº 3');
ok(P.decisionsPourSharpe(0.10) === REF.wall_010 && P.MUR.decisions === 619, '619 décisions pour un Sharpe de 0,10 (z₀,₉₅ + z₀,₈₀)');
ok(P.decisionsPourSharpe(0.05) === 2474 && P.decisionsPourSharpe(0.15) === 275, 'table 14 : 2 474 à 0,05 et 275 à 0,15');
{
  const p08 = require('./harness').ALP3 + '/p08.txt';
  const txt = fs.readFileSync(p08, 'utf8');
  ok(/\| 0,100 \| 619 \|/.test(txt), 'p08.txt, table 14 : « | 0,100 | 619 | »');
  ok(/Un Sharpe observé de 0,10 par décision/.test(txt), 'p08.txt : le Sharpe cité est 0,10 par décision');
  ok(/Huitième partie/.test(txt) && /Table 14/.test(txt), 'la source citée (partie VIII, table 14) existe');
}

section('Sources');
{
  const csv = 'date;pnl\n2026-09-14 15:42;120\n2026-09-15;−80,5\n# commentaire\n14/09/2026 09:30;(40)\nabc;def\n2026-09-16;1 234,50';
  const r = P.parseCsv(csv, 'usd', 150, 'UTC');
  ok(r.trades.length === 4, 'CSV : quatre lignes lues (' + r.trades.length + ')');
  ok(r.skipped.length === 1 && r.skipped[0].line === 6, 'CSV : une ligne ignorée, la sixième ; l’en-tête ne compte pas');
  ok(r.hasDates && !r.hasTimes, 'CSV : dates partout, heures pas partout');
  ok(JSON.stringify(r.trades.map(t => t.pnl)) === JSON.stringify([-40, 120, -80.5, 1234.5]), 'CSV : valeurs, signe, parenthèses, milliers, tri par date');
  ok(r.trades[0].at === Date.UTC(2026, 8, 14, 9, 30), 'CSV : date française avec heure');
  near(r.trades[1].r, 120 / 150, E, 'CSV en $ : r = pnl / risque');
  const col = P.parseCsv('0,5\n-1\n2,25R\n−1', 'r', 150);
  ok(col.trades.length === 4 && !col.hasDates && col.trades.every(t => t.at === null), 'colonne seule : quatre valeurs, sans dates');
  near(col.trades[2].pnl, 2.25 * 150, E, 'colonne en R : pnl = r × risque');
  const tab = P.parseCsv('2026-09-14\t15:42\t75', 'usd', 150, 'UTC');
  ok(tab.hasTimes && tab.trades[0].at === Date.UTC(2026, 8, 14, 15, 42), 'tabulations : date et heure en colonnes séparées');
  const us = P.parseCsv('2026-09-14,1234.5', 'usd', 150, 'UTC');
  ok(us.trades.length === 1 && us.trades[0].pnl === 1234.5, 'virgule séparatrice et point décimal');
  ok(P.parseNum('1.234,50') === 1234.5 && P.parseNum('1,234.50') === 1234.5 && isNaN(P.parseNum('2026-09-14')), 'nombres : deux conventions, une date n’est pas un nombre');
  const paris = P.parseDate('2026-07-01 15:30', 'Europe/Paris');
  ok(paris.t === Date.UTC(2026, 6, 1, 13, 30), 'heure de Paris en été = UTC + 2');
  const j = P.fromJournal([
    { kind: 'pris', status: 'clos', pnl: 100, r: 0.66, at: 5, closedAt: 9 },
    { kind: 'pris', status: 'ouvert', pnl: 50, at: 3 },
    { kind: 'refus', stage: 'macro', at: 1 },
    { kind: 'pris', status: 'clos', pnl: -75, at: 2 }
  ], 150);
  ok(j.length === 2 && j[0].pnl === -75 && j[0].r === -0.5 && j[1].at === 9, 'journal : seuls les pris clos, r déduit s’il manque, heure de clôture');
  const bt = P.fromBacktest({ label: 'x', trades: [{ at: 1, r: 2 }, { at: 2, pnl: -150 }, { at: 3 }] }, 150);
  ok(bt.length === 2 && bt[0].pnl === 300 && bt[1].r === -1, 'backtest : pnl et r complétés l’un par l’autre');
  ok(P.fromBacktest(null, 150).length === 0, 'backtest absent : aucune ligne');
}

section('Simulation');
{
  const o = { p: 0.4, b: 1.5, n: 4000, seed: 3, noise: 0, cost: 0, risk: 150, tpd: 2, end: Date.UTC(2026, 9, 9), from: 9, to: 17, tz: 'Europe/Paris' };
  const a = P.simulate(o), b = P.simulate(o);
  ok(JSON.stringify(a) === JSON.stringify(b), 'simulation déterministe à graine égale');
  ok(JSON.stringify(P.simulate(Object.assign({}, o, { seed: 4 }))) !== JSON.stringify(a), 'une autre graine, un autre tirage');
  const wr = P.winRate(a.map(t => t.pnl));
  ok(Math.abs(wr - 0.4) < 0.025, 'taux de réussite simulé ≈ p (' + wr.toFixed(3) + ')');
  const er = T.stats.mean(a.map(t => t.r));
  ok(Math.abs(er) < 0.06, 'à p = 1/(1 + b), espérance ≈ 0 (' + er.toFixed(4) + ' R)');
  ok(a.every(t => { const p = P.parts('Europe/Paris', t.at); return p.wd >= 1 && p.wd <= 5 && p.h >= 9 && p.h < 17; }), 'jours ouvrés, heures dans la fenêtre, fuseau respecté');
  const c = P.simulate(Object.assign({}, o, { n: 10, cost: 1.24 }));
  ok(c.every(t => Math.abs(t.pnl - (t.r * 150)) < 1e-9 && (Math.abs(t.pnl - (1.5 * 150 - 1.24)) < 1e-9 || Math.abs(t.pnl - (-150 - 1.24)) < 1e-9)), 'sans bruit, deux issues nettes de commission');
}

section('Agrégations');
{
  const d = P.daily(trades, 'UTC');
  ok(d.length === 8 && d[0].key === '2026-09-07' && d[0].pnl === 150 && d[0].n === 2 && d[0].wd === 1, 'P&L journaliers');
  const hw = P.hourWeek(trades, 'UTC');
  ok(hw.hours.join() === '8,9' && hw.wds.slice(0, 5).join() === '1,2,3,4,5', 'carte heure × jour : heures et jours');
  ok(hw.count[0][0] === 2 && hw.mean[0][0] === (300 - 150) / 2 && hw.wds.join() === '1,2,3,4,5,6,0', 'carte : lundi 8 h (trades 1 et 15), moyenne ; samedi et dimanche présents');
  const roll = P.rolling(PNL, 5);
  ok(roll.length === PNL.length - 4 && Math.abs(roll[0].sharpe - P.sharpe(PNL.slice(0, 5))) < E, 'Sharpe glissant');
  const qq = P.qq(PNL);
  ok(qq.length === PNL.length && qq[0][0] < 0 && Math.abs(qq[7][0] + qq[8][0]) < 1e-9, 'quantile-quantile : positions de Blom symétriques');
  const qt = P.quantileTable(PNL);
  ok(qt.length === 9 && qt[4].q === 0.5 && Math.abs(qt[4].obs - (-150 + -75) / 2 * 0 - T.stats.quantile(T.stats.sorted(PNL), 0.5)) < E, 'table des quantiles');
}

section('Espaces de paramètres');
{
  near(P.esperanceR(0.55, 2, 0.01), REF.esp_055_2_001, E, 'espérance p·b − (1 − p) − c');
  near(P.seuilEquilibre(2, 0.01), REF.pstar_2_001, E, 'équilibre p* = (1 + c)/(1 + b)');
  for (const bb of [0.5, 1, 2.5, 4]) near(P.esperanceR(P.seuilEquilibre(bb, 0.03), bb, 0.03), 0, 1e-12, 'espérance nulle sur la ligne d’équilibre, b = ' + bb);
  near(P.kellyGrowth(0.1, 0.5, 2), REF.kg_01_05_2, E, 'croissance de Kelly g(f)');
  near(P.kellyF(0.5, 2), REF.kfstar_05_2, E, 'crête f*');
  // la crête est bien le maximum de g, par balayage
  for (const [p, b] of [[0.5, 2], [0.6, 1], [0.45, 3]]) {
    let best = 0, bg = -Infinity; for (let f = 0; f < 0.99; f += 1e-4) { const g = P.kellyGrowth(f, p, b); if (g > bg) { bg = g; best = f; } }
    near(best, P.kellyF(p, b), 2e-4, 'f* = argmax g, p = ' + p + ', b = ' + b);
  }
  const m = P.ruinMoments(0.5, 2, 150, 1.24);
  near(m.mu, REF.ruin_mu, E, 'dérive par trade'); near(m.s2, REF.ruin_s2, E, 'variance par trade');
  near(P.pObjectif(m.mu, m.s2, 2000, 3000), REF.pobj_2000_3000, 1e-12, 'probabilité d’objectif, dérive positive');
  near(P.ruine(0.5, 2, { risk: 150, cost: 1.24, perteMax: 2000, objectif: 3000 }), REF.ruin_2000_3000, 1e-9, 'ruine, dérive positive');
  near(P.ruine(0.3, 2, { risk: 150, cost: 1.24, perteMax: 2000, objectif: 3000 }), REF.ruin_neg, 1e-12, 'ruine, dérive négative');
  near(P.pObjectif(0, 1, 2000, 3000), 2000 / 5000, E, 'à dérive nulle, P(objectif) = a/(a + b)');
  near(1 - P.pObjectif(0, 1, 2000, 3000), 3000 / 5000, E, 'à dérive nulle, ruine = b/(a + b)');
  near(P.pObjectif(1e-9, 1, 2000, 3000), 0.4, 1e-5, 'continuité au voisinage de la dérive nulle (+)');
  near(P.pObjectif(-1e-9, 1, 2000, 3000), 0.4, 1e-5, 'continuité au voisinage de la dérive nulle (−)');
  ok(P.pObjectif(-50, 100, 1e5, 1e5) === 0 || P.pObjectif(-50, 100, 1e5, 1e5) < 1e-300, 'forte dérive négative : aucun NaN, probabilité nulle');
  ok(Math.abs(P.pObjectif(50, 100, 1e5, 1e5) - 1) < 1e-12, 'forte dérive positive : probabilité 1');
  // sur la ligne d’équilibre, la ruine vaut b/(a + b) quelle que soit la géométrie
  for (const bb of [0.8, 2, 3.5]) { const pe = P.seuilEquilibre(bb, 1.24 / 150); near(P.ruine(pe, bb, { risk: 150, cost: 1.24, perteMax: 2000, objectif: 3000 }), 0.6, 1e-6, 'ruine = 60 % sur la ligne de dérive nulle, R:R ' + bb); }
  // contrôle par simulation : marche gaussienne à petits pas
  {
    const rnd = T.rng(5), mu = 0.02, sd = 1, A = 12, B = 18, PATHS = 4000; let hit = 0;
    for (let k = 0; k < PATHS; k++) { let x = 0; while (x > -A && x < B) { const u1 = Math.max(rnd(), 1e-300), u2 = rnd(); x += mu + sd * Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2); } if (x >= B) hit++; }
    const mc = hit / PATHS, th = P.pObjectif(mu, sd * sd, A, B);
    ok(Math.abs(mc - th) < 0.035, 'forme fermée contre simulation : ' + mc.toFixed(3) + ' contre ' + th.toFixed(3));
  }
  near(P.sharpeAnnuel(0.55, 2, 0.01, 504), REF.shAnn_055_2_001_504, 1e-12, 'Sharpe annualisé de la surface');
  near(P.sharpeAnnuel(P.seuilEquilibre(2, 0.01), 2, 0.01, 504), 0, 1e-12, 'Sharpe nul sur la ligne d’équilibre');
  const o = { risk: 150, cost: 1.24, objectif: 3000, perteMax: 2000, nYear: 504, bKelly: 2 };
  for (const k of P.SURF_KINDS) {
    const s = P.surface(k, o, 21, 17, false), s2 = P.surface(k, o, 30, 30, true);
    ok(s.vals.length === 17 && s.vals[0].length === 21 && s.xs.length === 21 && s.ys.length === 17, k + ' : forme de la grille');
    ok(s.vals.every(r => r.every(v => isFinite(v))) && s2.vals.every(r => r.every(v => isFinite(v))), k + ' : aucune valeur non finie');
    ok(s.zmin < s.zmax && s.vals[s.argmax[1]][s.argmax[0]] === s.zmax, k + ' : étendue et argmax');
    ok(s.xs[0] === s.x.dom[0] && s.xs[20] === s.x.dom[1] && s2.xs[0] > s2.x.dom[0], k + ' : nœuds aux bords, ou centres de cellules');
    ok(s.line.length > 5, k + ' : ligne d’équilibre ou crête tracée');
    near(s.vals[3][5], s.fn(s.xs[5], s.ys[3]), E, k + ' : la grille est la fonction');
    ok(typeof s.z.fmt === 'function' && typeof s.z.name === 'string' && typeof s.x.fmt(1) === 'string' && !/NaN|undefined/.test(s.z.fmt(s.zmin) + s.midLabel + s.lineLabel), k + ' : libellés propres');
  }
  const kel = P.surface('kelly', o, 21, 21, false);
  ok(kel.line.every(q => Math.abs(q[0] - P.kellyF(q[1], 2)) < 1e-12), 'Kelly : la crête tracée est f*(p)');
  const ru = P.surface('ruine', o, 21, 21, false);
  near(ru.mid, 0.6, E, 'ruine : le violet de l’échelle tombe sur b/(a + b)');
}

section('Rendu 3D : règles de projection');
{
  // le maximum au fond : à l’azimut initial, le point du maximum est le plus éloigné (yr minimal)
  for (const [u, v] of [[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5], [0.3, -0.1]]) {
    const az = P.azimutInitial(u, v), far = u * Math.sin(az) + v * Math.cos(az);
    const corners = [[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]].map(c => c[0] * Math.sin(az) + c[1] * Math.cos(az));
    ok(far <= Math.min(...corners) + 0.81, 'azimut initial : le maximum (' + u + ', ' + v + ') au fond');
  }
  const az = P.azimutInitial(-0.5, -0.5), back = P.project(-0.5, -0.5, 0, az, 0.6, 0.6), front = P.project(0.5, 0.5, 0, az, 0.6, 0.6);
  ok(back.y < front.y && back.depth < front.depth, 'le coin du maximum est en haut de l’écran et derrière');
  const hi = P.project(0, 0, 1, 0.3, 0.6, 0.6), lo = P.project(0, 0, 0, 0.3, 0.6, 0.6);
  ok(hi.y < lo.y, 'la hauteur monte à l’écran');
  const pal = { lo: [0, 0, 0], mid: [100, 50, 200], hi: [255, 255, 255] };
  ok(JSON.stringify(P.ramp(pal, 0.5)) === JSON.stringify([100, 50, 200]) && JSON.stringify(P.ramp(pal, 0)) === '[0,0,0]' && JSON.stringify(P.ramp(pal, 1)) === '[255,255,255]', 'échelle gris → violet → blanc');
  near(P.tOf(0, -2, 6, 0), 0.5, E, 'l’équilibre tombe au violet'); near(P.tOf(6, -2, 6, 0), 1, E, 'sommet au blanc'); near(P.tOf(-2, -2, 6, 0), 0, E, 'creux au gris');
  ok(JSON.stringify(P.cssColor('#9B8CFF')) === '[155,140,255]' && JSON.stringify(P.cssColor('rgba(1, 2, 3, .5)')) === '[1,2,3]', 'lecture des couleurs CSS');
}

section('Bootstrap stationnaire (port de alp1/mc.py)');
{
  // Référence : même algorithme et même générateur (mulberry32) en Python, tirages bruts / centrés entrelacés.
  const res = P.bootstrap({ x: PNL, B: 3, block: 2.5, seed: 7, raw: true });
  const ref = { boot: [0.42074355570205046, 0.38795894061802827, 0.506032944278365], nul: [-0.18787612876317242, 0.01859605745867308, -0.037350894041699806], mdd: [300, 300, 300] };
  res.boot.forEach((v, i) => near(v, ref.boot[i], 1e-12, 'bootstrap brut, tirage ' + i));
  res.nul.forEach((v, i) => near(v, ref.nul[i], 1e-12, 'bootstrap centré, tirage ' + i));
  res.mdd.forEach((v, i) => near(v, ref.mdd[i], 1e-12, 'drawdown rééchantillonné, tirage ' + i));
  const big = P.bootstrap({ x: PNL, B: 500, block: 1, seed: 1 }), big2 = P.bootstrap({ x: PNL, B: 500, block: 1, seed: 1 });
  ok(JSON.stringify(big) === JSON.stringify(big2), 'bootstrap déterministe à graine égale');
  ok(big.boot.every((v, i) => i === 0 || v >= big.boot[i - 1]), 'quantiles triés');
  const med = T.stats.quantile(big.nul, 0.5);
  ok(Math.abs(med) < 0.08, 'loi nulle centrée sur zéro (médiane ' + med.toFixed(3) + ')');
  const mb = T.stats.quantile(big.boot, 0.5);
  ok(Math.abs(mb - M.sharpe) < 0.08, 'bootstrap brut centré sur le Sharpe observé (' + mb.toFixed(3) + ')');
  ok(/^function perfBootstrap/.test(P.bootstrap.toString()) && !/\bT\.|\bP\./.test(P.bootstrap.toString()), 'fonction autonome pour le worker');
  near(P.blockLength(0.3), 1, E, 'bloc pour ρ = 0,3 (règle −1/ln|ρ|, plancher 1)');
  near(P.blockLength(0.8), -1 / Math.log(0.8), E, 'bloc pour ρ = 0,8');
  ok(P.blockLength(0) === 1 && P.blockLength(NaN) === 1, 'bloc 1 sans dépendance');
}

section('Feuille de score : textes');
{
  const groups = P.score(M);
  ok(groups.map(g => g.title).join('|') === 'Rendement ajusté au risque|Gains et pertes|Queues|Drawdown|Régularité', 'cinq groupes, dans l’ordre');
  const keys = groups.flatMap(g => g.rows.map(r => r.k));
  const need = ['sharpe', 'sharpeAnn', 'psr', 'dsr', 'minTRL', 'sortino', 'calmar', 'mar', 'omega', 'ulcer', 'martin', 'sterling', 'burke', 'net', 'expUsd', 'expR', 'pf', 'payoff', 'win', 'sqn', 'kelly', 'halfKelly', 'gpr', 'skew', 'kurt', 'tail', 'csr', 'var95h', 'var95g', 'var95cf', 'var99h', 'var99g', 'var99cf', 'cvar95', 'maxDD', 'maxDDpct', 'longest', 'recovery', 'streaks', 'rho1', 'runs'];
  need.forEach(k => ok(keys.indexOf(k) >= 0, 'mesure présente : ' + k));
  const all = groups.flatMap(g => g.rows);
  ok(all.every(r => r.name && r.v && r.read && r.def), 'chaque ligne a nom, valeur, lecture et définition');
  const txt = JSON.stringify(all);
  ok(!/NaN|undefined|\[object/.test(txt), 'aucun NaN ni undefined dans les textes');
  ok(!/'/.test(all.map(r => r.read + r.def + (r.nul || '')).join('')), 'apostrophes typographiques seulement');
  ok(all.find(r => r.k === 'sharpe').verdict === 'bruit' && all.find(r => r.k === 'runs').verdict === 'hors', 'verdicts : Sharpe dans le bruit, suites hors du bruit');
  ok(/n’est pas défini|indiscernable|au-dessus|au-dessous/.test(all.find(r => r.k === 'win').nul), 'taux de réussite comparé à son taux d’équilibre');
  // une série dégénérée ne produit ni NaN ni undefined dans le texte
  const deg = P.metrics([{ at: null, pnl: 10, r: 0.1 }, { at: null, pnl: 10, r: 0.1 }], { capital: 1000, risk: 100 });
  ok(!/NaN|undefined|\[object/.test(JSON.stringify(P.score(deg))), 'série sans perte : textes propres');
  const one = P.metrics([{ at: 1, pnl: -10, r: -0.1 }, { at: 2, pnl: -20, r: -0.2 }, { at: 3, pnl: 5, r: 0.05 }], { capital: 1000, risk: 100, tz: 'UTC' });
  ok(!/NaN|undefined|\[object/.test(JSON.stringify(P.score(one))), 'petite série perdante : textes propres');
}

section('Typographie');
{
  const out = P.typo('Lecture : 80 % de puissance ; « bruit » ? ALP nº 3 — fin');
  ok(out === 'Lecture\u202F: 80\u00A0% de puissance\u202F; «\u202Fbruit\u202F»\u202F? ALP nº\u00A03\u00A0— fin', 'espaces insécables avant : ; ? » et %, après « et nº');
  ok(P.typo('R:R 2,5') === 'R:R 2,5', 'R:R n’est pas touché');
}

section('Registre du desk');
{
  const d = T.desks().find(x => x.id === 'perf');
  ok(d && d.label === 'Métriques & espaces' && d.glyph === 'Σ' && d.group === 'Recherche' && d.order === 55, 'identité du desk');
  ok(d && d.tabs.map(t => t.id).join() === 'tableau,distribution,temps,espaces,robustesse', 'cinq onglets');
}

console.log(fails ? '\n' + fails + ' échec(s), ' + passes + ' réussite(s)' : '\nTous les tests passent (' + passes + ').');
process.exit(fails ? 1 : 0);
