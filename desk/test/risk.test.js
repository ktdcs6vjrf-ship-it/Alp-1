// Tests du desk « Risque » : node test/risk.test.js (sortie non nulle si échec).
// La simulation est évaluée hors du contexte vm, à partir de son seul texte source : c’est la preuve qu’elle est
// autonome (le Web Worker l’exécute ainsi) et cela lui rend la vitesse du moteur.
const fs = require('fs'), path = require('path');
const { T, lib: L } = require('./harness')('risk');
const sim = eval('(' + L.simulate.toString() + ')');
let fails = 0, passes = 0;
function ok(cond, msg) { if (cond) passes++; else { fails++; console.error('ÉCHEC', msg); } }
function near(a, b, tol, msg) { ok(typeof a === 'number' && Math.abs(a - b) <= tol, msg + ' : ' + a + ' attendu ' + b + ' ± ' + tol); }
function section(t) { console.log('· ' + t); }

section('Prérèglages et modèle de compte');
['50k', '100k', '150k'].forEach(function (id) {
  const p = L.PRESETS[id];
  ok(p.verify === true, id + ' marqué à vérifier');
  ok(p.lockAt === p.size + p.maxLoss + 100, id + ' : verrou = taille + perte max + 100');
  const a = L.normAccount(L.applyPreset(id));
  ok(a.balance === p.size && a.high === p.size, id + ' : solde et plus haut partent de la taille');
});
{
  const a = L.normAccount(null);
  ok(a.preset === '50k' && a.size === 50000 && a.dd === 'eod', 'compte par défaut = prérèglage 50 k');
  const b = L.normAccount({ preset: 'perso', size: 80000, maxLoss: 2500, dd: 'static', dailyLimit: null, consistency: null });
  ok(b.lockAt === 82600, 'verrou par défaut = taille + perte max + 100 : ' + b.lockAt);
  ok(b.dailyLimit === null && b.consistency === null, 'limite journalière et consistance facultatives');
  ok(L.normAccount({ size: 50000, lockAt: 10 }).lockAt === 50000, 'le verrou ne descend pas sous la taille');
  ok(L.normAccount({ balance: 51000, high: 50500 }).high === 51000, 'le plus haut vaut au moins le solde');
  ok(L.normAccount({ dd: 'nimporte' }).dd === 'eod', 'type de drawdown inconnu → défaut');
  const c = L.patchAccount(L.applyPreset('50k'), { size: 100000 });
  ok(c.balance === 100000 && c.high === 100000 && c.lockAt === 102100, 'changer la taille entraîne solde, plus haut et verrou restés au départ');
  const d = L.patchAccount(Object.assign(L.applyPreset('50k'), { balance: 50800, high: 51200 }), { size: 60000 });
  ok(d.balance === 50800 && d.high === 60000, 'un solde saisi ne bouge pas avec la taille');
}

section('Plancher et distances');
{
  const st = { size: 50000, target: 3000, maxLoss: 2000, dd: 'static', balance: 50600, high: 51500 };
  ok(L.floorOf(st) === 48000, 'statique : taille − perte max');
  const tr = Object.assign({}, st, { dd: 'eod', lockAt: 52100 });
  ok(L.floorOf(tr) === 49500, 'suiveur : plus haut − perte max');
  ok(L.floorOf(Object.assign({}, tr, { high: 53000, balance: 52000 })) === 50100, 'suiveur figé : verrou − perte max');
  const d = L.distances(tr, 2, 150, 5);
  ok(d.distLiq === 1100 && d.distObj === 2400, 'distances en dollars');
  near(d.ptsLiq, 550, 1e-12, 'points MNQ à un contrat = $ ÷ valeur du point (2 $)');
  near(d.ptsLiqMax, 550 / 50, 1e-12, 'points au plafond de contrats');
  near(d.ratio, 2400 / 1100, 1e-12, 'ratio objectif ÷ liquidation');
  ok(d.fullLosses === 7, 'pertes pleines encaissables : 7 × 155 $ = 1 085 < 1 100 : ' + d.fullLosses);
  ok(L.distances(Object.assign({}, tr, { balance: 50740 }), 2, 150, 5).fullLosses === 7, 'à 1 240 $ = 8 × 155, la 8ᵉ perte liquide : 7');
  ok(d.toLock === 600 && !d.locked, 'reste 600 $ avant de figer le suiveur');
  near(d.dayCap, 1500, 1e-12, 'consistance 50 % d’un objectif de 3 000 $');
  near(L.distances(L.applyPreset('50k')).pTheorem, 0.4, 1e-15, '50 k : 2 000 ÷ (2 000 + 3 000) = 40 %');
  near(L.distances(L.applyPreset('100k')).pTheorem, 1 / 3, 1e-15, '100 k : 3 000 ÷ 9 000');
  near(L.distances(L.applyPreset('150k')).pTheorem, 1 / 3, 1e-15, '150 k : 4 500 ÷ 13 500');
  ok(L.distances(Object.assign({}, st, { balance: 47000 })).pTheorem === 0, 'sous le plancher : 0');
  ok(L.distances(Object.assign({}, st, { balance: 53500 })).pTheorem === 1, 'objectif dépassé : 1');
}

section('Formules : arrêt optionnel et suiveur continu');
{
  near(L.pObjectif(0, 1, 2000, 3000), 0.4, 1e-15, 'dérive nulle : A/(A + B)');
  near(L.pObjectif(1e-12, 1, 2000, 3000), 0.4 + 2e-12 * 2000 * 3000 / (2 * 5000), 1e-12, 'continuité près de zéro : premier ordre kAB/2(A + B)');
  ok(L.pObjectif(5, 22500, 2000, 3000) > 0.4 && L.pObjectif(-5, 22500, 2000, 3000) < 0.4, 'la dérive déplace la probabilité dans son sens');
  const k = 2 * 5 / 22500, ref = (1 - Math.exp(-k * 2000)) / (1 - Math.exp(-k * 5000));
  near(L.pObjectif(5, 22500, 2000, 3000), ref, 1e-12, 'forme fermée, dérive positive');
  const k2 = -k, ref2 = (1 - Math.exp(-k2 * 2000)) / (1 - Math.exp(-k2 * 5000));
  near(L.pObjectif(-5, 22500, 2000, 3000), ref2, 1e-12, 'forme stable, dérive négative');
  ok(isFinite(L.pObjectif(-500, 100, 2000, 3000)) && L.pObjectif(-500, 100, 2000, 3000) >= 0, 'forme stable sans débordement');
  near(L.rallyHazard(0, 1, 2000), 1 / 2000, 1e-15, 'γ = 1/A à dérive nulle');
  const mu = 3, s2 = 20000, kk = 2 * mu / s2;
  near(L.rallyHazard(mu, s2, 2000), kk / (Math.exp(kk * 2000) - 1), 1e-15, 'γ = k/(e^{kA} − 1)');
  near(L.pTrailing(0, 1, 2000, 3000, Infinity, 0, 0), Math.exp(-1.5), 1e-15, 'suiveur sans verrou : e^{−B/A}');
  near(L.pTrailing(0, 1, 2000, 3000, 2100, 0, 0), Math.exp(-1.05) * 2000 / 2900, 1e-15, 'suiveur verrouillé à 2 100 : e^{−L/A} · A/(A + B − L)');
  near(L.pTrailing(0, 1, 2000, 3000, 3000, 0, 0), Math.exp(-1.5), 1e-15, 'verrou à l’objectif : rien ne change');
  near(L.pTrailing(0, 1, 2000, 3000, 2100, 2500, 2500), L.pObjectif(0, 1, 2400, 500), 1e-12, 'suiveur figé : statique depuis le plancher figé (2 500 − 100)');
  near(L.pTrailing(0, 1, 2000, 3000, 2100, 1000, 1400), (1600 / 2000) * Math.exp(-(2100 - 1400) / 2000) * 2000 / 2900, 1e-12, 'depuis un recul : revenir au plus haut, puis la hausse');
  ok(L.pTrailing(-3, 20000, 2000, 3000, 2100, 0, 0) < L.pTrailing(0, 1, 2000, 3000, 2100, 0, 0), 'une dérive négative réduit le suiveur');
  ok(L.pTrailing(0, 1, 2000, 3000, 2100, -2100, 0) === 0, 'sous le plancher : 0');
  const f = L.formulaNull(2000, 3000, 'eod', 2100);
  ok(f.lo < f.hi && Math.abs(f.hi - 0.4) < 1e-15 && Math.abs(f.lo - L.pTrailing(0, 1, 2000, 3000, 2100, 0, 0)) < 1e-15, 'fin de journée encadré par continu et statique');
  ok(L.formulaNull(2000, 3000, 'static', 2100).v === 0.4, 'statique : A/(A + B)');
}

section('Géométrie d’un trade, loi nulle');
{
  near(L.equilibrium(1.5, 1, 5, 150), (1 + 5 / 150) / 2.5, 1e-15, 'équilibre = (1 + coût/risque)/(R + 1)');
  near(L.expectancyR(L.equilibrium(1.5, 1, 5, 150), 1.5, 1, 5, 150), 0, 1e-12, 'espérance nette nulle à l’équilibre');
  near(L.expectancyR(L.zeroEdge(2, 1), 2, 1, 6, 150), -6 / 150, 1e-12, 'sans avantage : −c/L');
  near(L.zeroEdge(1.5, 1), 0.4, 1e-15, 'sans avantage = perte/(gain + perte)');
  const m = L.moments(0.4, 1.5, 1, 150, 5);
  near(m.mu, -5, 1e-12, 'dérive par trade sans avantage = −frais');
  near(m.s2, 0.24 * 375 * 375, 1e-9, 'variance p(1 − p)((gain + perte)·risque)²');
  const s = L.normSim({ p: 2, days: 999, tpd: 0 }, { riskPerTrade: 120, maxTradesDay: 4 });
  ok(s.p === 1 && s.days === 120 && s.tpd === 4 && s.risk === 120, 'paramètres bornés, défauts tirés des réglages');
}

section('Monte-Carlo : le théorème retrouvé (spécification)');
{
  const base = { win: 1, loss: 1, risk: 150, tpd: 10, cost: 0, target: 3000, maxLoss: 2000, days: 2000, n: 20000, seed: 3, fan: false };
  const r = sim(Object.assign({}, base, { p: 0.5, dd: 'static' }));
  near(r.pPass, 2000 / 5000, 0.02, 'avantage nul, sans frais, statique, 20 000 trajectoires : perte max ÷ (perte max + objectif)');
  ok(r.pNone < 0.001, 'pratiquement aucune trajectoire non résolue : ' + r.pNone);
  ok(r.pass + r.fail + r.none === r.n, 'les issues se partagent les trajectoires');
  const r15 = sim(Object.assign({}, base, { p: 0.4, win: 1.5, dd: 'static' }));
  near(r15.pPass, 0.4, 0.02, 'géométrie 1,5 R : même probabilité, la géométrie n’y change rien');
  const eq = sim(Object.assign({}, base, { p: L.equilibrium(1.5, 1, 5, 150), win: 1.5, cost: 5, dd: 'static' }));
  near(eq.pPass, 0.4, 0.02, 'loi nulle (équilibre, frais compris) : retrouve A/(A + B)');
  const ne = sim(Object.assign({}, base, { p: 0.4, win: 1.5, cost: 5, dd: 'static' }));
  const m = L.moments(0.4, 1.5, 1, 150, 5);
  near(ne.pPass, L.pStatic(m.mu, m.s2, 2000, 3000, 0), 0.02, 'sans avantage, frais payés : la diffusion à dérive −c');
  ok(ne.pPass < eq.pPass - 0.1, 'la friction seule retire plus de dix points : ' + ne.pPass);
  const eo = sim(Object.assign({}, base, { p: 0.5, dd: 'eod', lock: 2100 }));
  const it = sim(Object.assign({}, base, { p: 0.5, dd: 'intraday', lock: 2100 }));
  ok(it.pPass <= eo.pPass && eo.pPass <= r.pPass, 'intrajournalier ≤ fin de journée ≤ statique (mêmes tirages) : ' + [it.pPass, eo.pPass, r.pPass].join(' ≤ '));
  near(it.pPass, L.pTrailing(0, 1, 2000, 3000, 2100, 0, 0), 0.02, 'suiveur intrajournalier : la formule continue de Lehoczky');
  const small = sim(Object.assign({}, base, { p: 0.5, dd: 'intraday', lock: null, risk: 50, n: 4000 }));
  near(small.pPass, Math.exp(-1.5), 0.025, 'suiveur sans verrou à petit pas : e^{−B/A}');
  const st2 = sim(Object.assign({}, base, { p: 0.5, dd: 'static', pnl0: 1000, hwm0: 1000, n: 10000 }));
  near(st2.pPass, 3000 / 5000, 0.025, 'depuis un solde de +1 000 $ : (1 000 + 2 000) ÷ 5 000');
}

section('Monte-Carlo : cas déterministes, limite journalière, graine');
{
  const b = { win: 1, loss: 1, risk: 100, cost: 0, target: 1000, maxLoss: 1000, dd: 'static', n: 50, seed: 9, fan: true, keep: 3 };
  const w = sim(Object.assign({}, b, { p: 1, tpd: 2, days: 10 }));
  ok(w.pPass === 1 && w.medPass === 5, 'que des gains, 2 par jour, objectif 10 R : jour 5');
  const l = sim(Object.assign({}, b, { p: 0, tpd: 3, days: 10 }));
  ok(l.pFail === 1 && l.medFail === 4 && l.cause.never === 50, 'que des pertes, 3 par jour, plancher à 10 R : jour 4, jamais en gain');
  const df = sim(Object.assign({}, b, { p: 0, tpd: 5, days: 10, daily: 250, dailyMode: 'fail' }));
  ok(df.pFail === 1 && df.medFail === 1 && df.cause.daily === 50, 'limite journalière éliminatoire : échec au premier jour');
  const dp = sim(Object.assign({}, b, { p: 0, tpd: 5, days: 10, daily: 250, dailyMode: 'pause' }));
  ok(dp.pFail === 1 && dp.medFail === 4 && dp.cause.daily === 0, 'limite journalière qui suspend : −250 $ par jour, plancher au jour 4');
  near(dp.q.p50[1], -250, 1e-9, 'le premier jour s’arrête à la limite');
  ok(l.q.p50.length === 11 && l.paths.length === 3 && l.paths[0].length === 11, 'éventail : un point par jour, départ compris');
  ok(l.q.p50[10] === -1000 && l.q.p50[4] === -1000, 'une trajectoire terminée garde son solde final');
  const c = sim(Object.assign({}, b, { p: 0, tpd: 1, days: 3, cost: 10, n: 5 }));
  near(c.q.p50[3], -330, 1e-9, 'les frais se déduisent à chaque trade');
  const eodPeak = sim(Object.assign({}, b, { p: 1, tpd: 1, days: 3, dd: 'eod', lock: 5000, maxLoss: 150, target: 10000 }));
  ok(eodPeak.pNone === 1, 'fin de journée : le plancher suit, les gains survivent');
  const intraTrap = sim({ p: 0, win: 2, loss: 1, risk: 100, tpd: 1, days: 1, cost: 0, target: 10000, maxLoss: 105, dd: 'intraday', lock: 5000, n: 4000, seed: 5 });
  const staticSame = sim({ p: 0, win: 2, loss: 1, risk: 100, tpd: 1, days: 1, cost: 0, target: 10000, maxLoss: 105, dd: 'static', n: 4000, seed: 5 });
  ok(staticSame.pFail === 0 && intraTrap.pFail > 0.02, 'intrajournalier : l’excursion favorable d’un perdant remonte le plancher (' + intraTrap.pFail + ')');
  const m = 5, S = 100, G = 200, pExc = S * (G - m) / ((S + m) * G);
  near(intraTrap.pFail, pExc, 0.02, 'P(excursion ≥ 5 $ | perte) = S(G − m)/((S + m)G)');
  const s1 = sim(Object.assign({}, b, { p: 0.5, tpd: 3, days: 20, n: 300 })), s2 = sim(Object.assign({}, b, { p: 0.5, tpd: 3, days: 20, n: 300 }));
  ok(JSON.stringify(s1) === JSON.stringify(s2), 'même graine, même résultat au bit près');
  const s3 = sim(Object.assign({}, b, { p: 0.5, tpd: 3, days: 20, n: 300, seed: 10 }));
  ok(JSON.stringify(s1.passDays) !== JSON.stringify(s3.passDays), 'autre graine, autres tirages');
  const fanr = sim({ p: 0.45, win: 1.5, loss: 1, risk: 150, tpd: 3, cost: 5, target: 3000, maxLoss: 2000, dd: 'eod', lock: 2100, daily: 1000, days: 30, n: 2000, seed: 7, fan: true, keep: 4 });
  let mono = true; for (let d = 0; d <= 30; d++) { const q = fanr.q; if (!(q.p05[d] <= q.p25[d] && q.p25[d] <= q.p50[d] && q.p50[d] <= q.p75[d] && q.p75[d] <= q.p95[d])) mono = false; }
  ok(mono, 'quantiles ordonnés à chaque jour');
  ok(fanr.passBy.reduce((a, x) => a + x, 0) === fanr.pass && fanr.failBy.reduce((a, x) => a + x, 0) === fanr.fail, 'comptes par jour cohérents');
  ok(fanr.cause.gain + fanr.cause.never + fanr.cause.daily === fanr.fail, 'causes d’échec exhaustives');
  ok(JSON.parse(JSON.stringify(fanr)).q.p50.length === 31, 'résultat sérialisable');
}

section('Théorème appliqué au compte : arguments');
{
  const a = Object.assign(L.applyPreset('50k'), { balance: 50500, high: 50800 });
  const sp = L.normSim({}, { riskPerTrade: 150, maxTradesDay: 3 });
  const t = L.theoremArgs(a, sp);
  ok(t.rules.cost === 0 && t.friction.cost === sp.cost, 'sans frais puis avec frais');
  near(t.rules.p, 0.4, 1e-15, 'à avantage nul : perte/(gain + perte)');
  ok(t.rules.pnl0 === 500 && t.rules.hwm0 === 800 && t.rules.lock === 2100, 'part du solde courant, relatif au départ');
  ok(t.rules.n >= 400 && t.rules.n <= 5000 && t.rules.n * t.estN <= 1.6e7 + 5000 * 1, 'budget de calcul tenu');
  const r = sim(Object.assign({}, L.theoremArgs(L.applyPreset('50k'), Object.assign({}, sp, { win: 1 })).rules, { dd: 'static', daily: null }));
  near(r.pPass, 0.4, 0.025, 'compte neuf, statique, sans frais : 40 sur 100');
}

section('La journée');
{
  const now = Date.UTC(2026, 9, 9, 10, 0); // vendredi 9 octobre 2026, 12:00 à Paris
  const H = 3600e3, M = 60e3;
  ok(L.dayKeyOf(now) === '2026-10-09', 'clé du jour à Paris');
  ok(L.dayKeyOf(Date.UTC(2026, 9, 8, 22, 30)) === '2026-10-09', '22:30 UTC le 8 = 00:30 à Paris le 9');
  const rows = [
    { id: 'a', at: now - 3 * H, kind: 'pris', status: 'clos', pnl: -150, closedAt: now - 2.8 * H },
    { id: 'b', at: now - 2 * H, kind: 'pris', status: 'clos', pnl: 225, closedAt: now - 1.5 * H },
    { id: 'c', at: now - 20 * M, kind: 'pris', status: 'clos', pnl: -150, closedAt: now - 5 * M },
    { id: 'd', at: now - 2 * M, kind: 'pris', status: 'ouvert' },
    { id: 'e', at: now - 30 * M, kind: 'refus', stage: 'vwap' },
    { id: 'f', at: now - 26 * H, kind: 'pris', status: 'clos', pnl: -500 },
    { id: 'g', at: now - 1 * H, kind: 'pris', status: 'clos', pnl: -900, deleted: true }
  ];
  const set = { riskPerTrade: 150, maxTradesDay: 3, maxLossesDay: 2, dailyStop: 400, pointValue: 2 };
  const s = L.dayState(rows, set, null, now, { inWindow: true, confirmed: true });
  ok(s.taken === 4 && s.closed === 3 && s.open === 1, 'trades pris, clos, ouverts (refus et veille exclus)');
  near(s.pnl, -75, 1e-12, 'P&L du jour');
  ok(s.losses === 2 && s.wins === 1, 'pertes et gains');
  near(s.riskLeft, 325, 1e-12, 'risque restant = stop − perte du jour');
  near(s.cooldownMs, 10 * M, 1e-6, 'refroidissement : 15 min après la perte de 11:55 → 10 min');
  ok(L.fmtClock(s.cooldownMs) === '10:00' && L.fmtClock(61001) === '1:02' && L.fmtClock(0) === '0:00', 'compte à rebours mm:ss');
  const byId = {}; s.breakers.forEach(b => { byId[b.id] = b; });
  ok(byId.trades.open && byId.pertes.open && byId.refroid.open && !byId.stop.open && !byId.prochain.open && !byId.confirm.open && !byId.fenetre.open, 'disjoncteurs : trades, pertes, refroidissement coupent');
  ok(!s.canTrade, 'un disjoncteur suffit : arrête-toi');
  const acc = Object.assign(L.applyPreset('50k'), { dailyLimit: 300, balance: 48100, high: 50000, dd: 'static' });
  const s2 = L.dayState(rows.slice(0, 2), set, acc, now, { inWindow: true, confirmed: true });
  ok(s2.stopEff === 300 && s2.stopSrc === 'compte', 'stop retenu : le plus strict des deux');
  ok(s2.breakers.filter(b => b.id === 'compte')[0].open, 'compte : une perte pleine toucherait le plancher (100 $ de marge)');
  const free = L.dayState([], set, L.applyPreset('50k'), now, { inWindow: true, confirmed: true });
  ok(free.canTrade && free.riskLeft === 400, 'journée vierge, limites confirmées, fenêtre ouverte : tu peux trader');
  ok(!L.dayState([], set, null, now, { inWindow: true, confirmed: false }).canTrade, 'limites non confirmées : arrête-toi');
  ok(!L.dayState([], set, null, now, { inWindow: false, confirmed: true }).canTrade, 'hors fenêtre : arrête-toi');
  const tight = L.dayState([{ at: now - H, kind: 'pris', pnl: -300, closedAt: now - 40 * M }], set, null, now, { inWindow: true, confirmed: true });
  ok(tight.breakers.filter(b => b.id === 'prochain')[0].open && tight.riskLeft === 100, 'un stop plein de 150 $ ne tient plus dans 100 $');
  const E = L.effectiveLimits(set, { riskPerTrade: 150, maxTradesDay: 2, maxLossesDay: 2, dailyStop: 500 });
  ok(E.lim.maxTradesDay === 2 && E.lim.dailyStop === 400 && E.loosened.length === 1 && E.loosened[0] === 'maxTradesDay', 'confirmées : on resserre, on ne relâche pas');
  const s3 = L.dayState(rows, set, null, now, { snap: { riskPerTrade: 150, maxTradesDay: 5, maxLossesDay: 3, dailyStop: 400 } });
  ok(s3.limits.maxTradesDay === 3 && s3.loosened.length === 0, 'resserrer après confirmation ne signale rien');
}

section('Règles');
{
  const r = L.normRules(null);
  ok(r.length >= 8 && r.length <= 10, 'entre huit et dix règles de départ : ' + r.length);
  ok(new Set(r.map(x => x.id)).size === r.length, 'identifiants uniques');
  const txt = r.map(x => x.t + ' ' + x.s).join(' ').toLowerCase();
  ['stop est placé avant l’entrée', 'taille se calcule depuis le stop', 'moyenne à la baisse', 'revanche', 'nombre de pertes', 'hors de ma fenêtre', 'ligne de journal'].forEach(function (k) { ok(txt.indexOf(k) >= 0, 'règle présente : ' + k); });
  ok(r.every(x => L.MOMENTS.some(m => m.v === x.m)), 'chaque règle a un moment connu');
  ok(L.normRules([]).length === 0, 'une liste vidée reste vide');
  ok(L.normRules([{ id: 'x', t: 'T', m: '???' }])[0].m === 'journee', 'moment inconnu → toute la séance');
  const ad = L.adherence({ 'r-stop': true, 'r-taille': true, inconnu: true }, r);
  ok(ad.kept === 2 && ad.total === r.length, 'adhérence : les identifiants supprimés ne comptent pas');
  ok(JSON.stringify(L.pastKeys('2026-03-02', 3)) === JSON.stringify(['2026-02-28', '2026-03-01', '2026-03-02']), 'jours passés à travers février');
  ok(JSON.stringify(L.pastKeys('2026-10-26', 2)) === JSON.stringify(['2026-10-25', '2026-10-26']), 'jours passés à travers le changement d’heure');
  ok(L.pastKeys('2026-10-09', 14).length === 14 && L.pastKeys('n’importe', 3).length === 0, '14 jours, clé invalide refusée');
  ok(/^risk:rulecheck:2026-10-09$/.test(L.KEYS.check + '2026-10-09'), 'clé de coche du jour');
}

section('Journal comme hypothèse');
{
  const rows = [];
  for (let i = 0; i < 20; i++) rows.push({ kind: 'pris', r: i % 5 < 2 ? 1.5 : -1 });
  rows.push({ kind: 'refus' }, { kind: 'pris', pnl: 300 }, { kind: 'pris', r: 2, deleted: true });
  const j = L.fromJournal(rows, 150);
  ok(j.n === 21, 'trades pris comptés, R tiré du P&L si besoin');
  near(j.p, 9 / 21, 1e-12, 'taux de réussite');
  near(j.win, (8 * 1.5 + 2) / 9, 1e-12, 'gain moyen en R');
  near(j.loss, 1, 1e-12, 'perte moyenne en R');
  near(j.hw, 1.96 * Math.sqrt((9 / 21) * (12 / 21) / 21), 1e-12, 'demi-largeur à 95 %');
  ok(L.fromJournal(rows.slice(0, 5), 150) === null, 'moins de dix trades : rien');
}

section('Typographie');
ok(L.typo('Source : 40 %') === 'Source : 40 %', 'espace fine avant deux-points, insécable avant %');

section('Sources : ALP nº 3, contrôlées contre le texte');
{
  const dir = require('./harness').ALP3;
  const p20 = fs.readFileSync(path.join(dir, 'p20.txt'), 'utf8'), p11 = fs.readFileSync(path.join(dir, 'p11.txt'), 'utf8'), p00 = fs.readFileSync(path.join(dir, 'p00.txt'), 'utf8');
  ok(/^Vingtième partie/.test(p20) && /^Onzième partie/.test(p11), 'les parties citées portent bien ces numéros');
  ok(p20.indexOf('a/(a+b) — la toucher avant le stop. C’est le théorème d’arrêt optionnel') >= 0, 'vingtième partie : a/(a+b) est le théorème d’arrêt optionnel');
  ok(p20.indexOf('Elle vaut 4,76 %') >= 0 && T.fmt.pct(1 / (1 + 20), 2) === '4,76 %', 'vingtième partie : 4,76 % = 1/(1 + 20), retrouvé par la formule');
  ok(p11.indexOf('À dérive nulle, les quatre droites valent exactement −c/L') >= 0, 'onzième partie : −c/L à dérive nulle');
  ok(p00.indexOf('619 décisions') >= 0, 'résumé : 619 décisions');
  const src = fs.readFileSync(path.join(__dirname, '..', 'src', 'desks', 'risk.js'), 'utf8');
  ok(src.indexOf('vingtième partie') >= 0 && src.indexOf('onzième partie') >= 0, 'le desk cite ses sources');
  ok(!/#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|rgba?\(/.test(src), 'aucune couleur écrite en dur');
}

console.log(passes + ' réussis, ' + fails + ' échecs');
process.exit(fails ? 1 : 0);
