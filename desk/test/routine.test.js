// Tests des fonctions pures du desk Routine & revue.
const fs = require('fs'), path = require('path');
const { T, lib: R } = require('./harness')('routine');
let n = 0, fail = 0;
function ok(c, m) { n++; if (!c) { fail++; console.error('ÉCHEC', m); } }
function eq(a, b, m) { ok(JSON.stringify(a) === JSON.stringify(b), m + ' : ' + JSON.stringify(a) + ' ≠ ' + JSON.stringify(b)); }
function near(a, b, e, m) { ok(Math.abs(a - b) <= e, m + ' : ' + a + ' ≠ ' + b); }

// 619 : contrôlé contre le texte d'ALP nº 3.
const txt = fs.readdirSync(require('./harness').ALP3).map(f => fs.readFileSync(path.join(require('./harness').ALP3, f), 'utf8')).join('\n');
ok(/619/.test(txt), '619 présent dans ALP nº 3');
eq(R.WALL, 619, 'WALL');

// Préparation
const all = {}; R.CHECKS.forEach(c => all[c.id] = true);
eq(R.readiness({ checks: all, sleep: 5, stress: 1 }).score, 100, 'préparation parfaite');
eq(R.readiness({ checks: all, sleep: 5, stress: 1 }).verdict, 'go', 'verdict go');
eq(R.readiness({}).score, 0, 'rien coché');
eq(R.readiness({}).verdict, 'incomplet', 'incomplet sans échelles');
eq(R.readiness({ checks: {}, sleep: 1, stress: 5 }).verdict, 'sim', 'sim');
eq(R.readiness({ checks: all, sleep: 1, stress: 5 }).score, 60, 'liste seule = 60');
eq(R.readiness({ checks: all, sleep: 1, stress: 5 }).verdict, 'demi', '60 → demi');
eq(R.readiness({ checks: all, sleep: 3, stress: 3 }).score, 80, 'moyen = 80');
eq(R.readiness({ checks: all, sleep: 9, stress: -3 }).score, 100, 'bornes des échelles');
ok(R.CHECKS.every(c => c.id && c.t && c.s), 'liste complète');

// Jours
eq(R.dayOf(Date.UTC(2026, 9, 9, 22, 30), 'Europe/Paris'), '2026-10-10', 'minuit Paris en été');
eq(R.dayOf(Date.UTC(2026, 9, 9, 21, 30), 'Europe/Paris'), '2026-10-09', 'veille');
eq(R.dayOf(Date.UTC(2026, 9, 10, 2, 0), 'America/New_York'), '2026-10-09', 'New York');
eq(R.addDays('2026-02-28', 1), '2026-03-01', 'fin février');
eq(R.addDays('2024-02-28', 1), '2024-02-29', 'bissextile');
eq(R.addDays('2026-01-01', -1), '2025-12-31', 'recul année');
eq(R.weekday('2026-10-10'), 6, 'samedi');
eq(R.weekday('2026-10-12'), 1, 'lundi');

// Statistiques du jour
const d0 = Date.UTC(2026, 9, 9, 6, 0); // 08:00 Paris
const tr = [
  { at: d0, kind: 'pris', status: 'clos', pnl: -150, r: -1, plan: true },
  { at: d0 + 60e3, kind: 'refus', stage: 'vwap' },
  { at: d0 + 120e3, kind: 'pris', status: 'clos', pnl: 300, r: 2, plan: false },
  { at: d0 + 180e3, kind: 'pris', status: 'clos', pnl: -150, r: -1, plan: true },
  { at: d0 + 240e3, kind: 'pris', status: 'clos', pnl: -150, r: -1, plan: true },
  { at: d0 + 300e3, kind: 'pris', status: 'ouvert', plan: true },
  { at: d0 - 864e5, kind: 'pris', status: 'clos', pnl: 999, plan: true }
];
const st = R.dayStats(tr, '2026-10-09', 'Europe/Paris');
eq([st.taken, st.refus, st.open, st.closed, st.wins, st.losses], [5, 1, 1, 4, 1, 3], 'comptes du jour');
eq(st.pnl, -150, 'P&L du jour');
eq(st.r, -1, 'R du jour');
eq(st.consec, 2, 'pertes de suite finales');
eq([st.planOk, st.planN], [4, 5], 'adhérence');
eq(st.rows.length, 6, 'lignes du jour (veille exclue)');

// Disjoncteurs
const set = { maxTradesDay: 3, maxLossesDay: 2, dailyStop: 400, tz: 'Europe/Paris' };
const br = R.breakers(st, set), by = {}; br.forEach(b => by[b.id] = b);
eq(by.trades.state, 'stop', 'trades atteints');
eq(by.pertes.state, 'stop', 'pertes atteintes');
eq(by.stop.state, 'ok', '150 $ sur 400 : libre');
eq(by.serie.state, 'pause', 'deux pertes de suite : pause');
eq(R.sessionState(br), 'stop', 'stop domine');
eq(R.breakers({ taken: 2, losses: 1, pnl: -250, consec: 1 }, set).map(b => b.state), ['alerte', 'alerte', 'alerte', 'alerte'], 'alertes');
eq(R.sessionState(R.breakers({ taken: 0, losses: 0, pnl: 0, consec: 0 }, set)), 'ok', 'libre');
eq(R.sessionState(R.breakers({ taken: 1, losses: 0, pnl: 0, consec: 2 }, { maxTradesDay: 10, maxLossesDay: 10, dailyStop: 1000 })), 'pause', 'pause seule');
eq(R.breakers({ taken: 1, losses: 0, pnl: -500, consec: 0 }, set)[2].state, 'stop', 'perte du jour atteinte');

// Matrice
const m = R.matrix(tr);
eq([m.okWin, m.okLoss, m.offWin, m.offLoss, m.n], [1, 3, 1, 0, 5], 'matrice processus/résultat');
eq(R.matrix([{ kind: 'refus' }, { kind: 'pris', status: 'clos', pnl: 10 }]).n, 0, 'sans plan : hors matrice');

// Notes
eq(R.GRADES.map(g => R.gradeScore(g.v)), [4, 3, 2, 1, 0], 'notes');
ok(isNaN(R.gradeScore('Z')), 'note inconnue');

// Séances et paliers
function mk(start, k, mode, grade, pnl, plan) {
  const days = {}, trades = []; let d = start, i = 0;
  while (i < k) { const wd = R.weekday(d); if (wd && wd !== 6) { days[d] = { mode, review: { grade } }; const t = Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10), 7); trades.push({ at: t, kind: 'pris', status: 'clos', pnl, plan }); i++; } d = R.addDays(d, 1); }
  return { days, trades, end: d };
}
const s = { tz: 'Europe/Paris', maxTradesDay: 3, maxLossesDay: 2, dailyStop: 400 };
const a = mk('2026-01-05', 10, 'replay', 'B', -100, true);
let ses = R.sessions(a.days, a.trades, s);
eq(ses.length, 10, 'dix séances');
let lad = R.ladder(ses);
eq(lad.map(x => x.state), ['tenu', 'ouvert', 'ferme', 'ferme'], 'replay tenu');
const b = mk(a.end, 20, 'sim', 'A', 50, true);
const days2 = Object.assign({}, a.days, b.days), tr2 = a.trades.concat(b.trades);
lad = R.ladder(R.sessions(days2, tr2, s));
eq(lad.map(x => x.state), ['tenu', 'tenu', 'ouvert', 'ferme'], 'simulateur tenu');
eq(lad[1].clean, 20, 'vingt séances propres');
// une séance hors limite casse la série propre
const last = Object.keys(b.days).sort().pop();
const tr3 = tr2.concat([{ at: Date.UTC(+last.slice(0, 4), +last.slice(5, 7) - 1, +last.slice(8, 10), 8), kind: 'pris', status: 'clos', pnl: -500, plan: true }]);
lad = R.ladder(R.sessions(days2, tr3, s));
eq(lad[1].clean, 0, 'perte du jour dépassée : série remise à zéro');
eq(lad[1].state, 'ouvert', 'palier simulateur rouvert');
eq(lad[2].state, 'ferme', 'évaluation refermée');
// adhérence insuffisante
const c = mk('2026-01-05', 10, 'replay', 'B', -100, false);
eq(R.ladder(R.sessions(c.days, c.trades, s))[0].state, 'ouvert', 'adhérence nulle : replay non tenu');
// une séance sans revue ne compte pas
const d = mk('2026-01-05', 10, 'replay', null, -100, true);
eq(R.gate(R.sessions(d.days, d.trades, s), R.LADDER[0]).sessions, 0, 'sans note, pas de séance');

// Série
const sd = {}; ['2026-10-05', '2026-10-06', '2026-10-07', '2026-10-08', '2026-10-09'].forEach(k => sd[k] = { review: { grade: 'A' } });
eq(R.streak(sd, '2026-10-10'), 5, 'samedi : la semaine compte');
eq(R.streak(sd, '2026-10-12'), 5, 'lundi sans revue ne casse pas');
delete sd['2026-10-07'];
eq(R.streak(sd, '2026-10-09'), 2, 'trou mercredi');
eq(R.streak({}, '2026-10-09'), 0, 'vide');

// Grille
const g = R.grid(sd, '2026-10-09', 12);
eq([g.rows.length, g.cols.length, g.values[0].length], [5, 12, 12], 'grille 5 × 12');
eq(g.values[0][11], 4, 'lundi courant noté A');
ok(isNaN(g.values[2][11]), 'mercredi vide');
eq(g.cols[11], '05/10', 'semaine du 5 octobre');
const g2 = R.grid({}, '2026-10-07', 1);
ok(isNaN(g2.values[4][0]), 'futur vide');

// Élagage
const big = {}; for (let i = 0; i < 450; i++) big[R.addDays('2025-01-01', i)] = { mode: 'sim' };
const pr = R.prune(big);
eq(Object.keys(pr).length, 400, '400 jours gardés');
ok(!('2025-01-01' in pr) && (R.addDays('2025-01-01', 449) in pr), 'les plus récents');

// Export / import
const doc = R.exportDoc({ settings: { riskPerTrade: 100 }, 'routine:days': {} }, tr, '2026-10-10T00:00:00Z');
eq(doc.app, 'ALP Desk', 'marque');
const v = R.validateImport(JSON.parse(JSON.stringify(doc)));
ok(v.ok && v.keys.length === 2 && v.rows.length === 7, 'import valide');
eq(R.validateImport({ app: 'x' }).ok, false, 'fichier étranger');
eq(R.validateImport({ app: 'ALP Desk', journal: 3 }).ok, false, 'journal illisible');
eq(R.validateImport({ app: 'ALP Desk', store: { 'bad key!': 1, ok: 2 } }).keys, ['ok'], 'clés filtrées');
eq(R.newRows(tr, tr).length, 0, 'aucun doublon');
eq(R.newRows(tr.slice(0, 2), tr).length, 5, 'lignes nouvelles seulement');
eq(R.newRows([], [tr[0], tr[0]]).length, 1, 'doublon interne');

// Spécifications CME
eq([R.SPEC.MNQ.pointValue, R.SPEC.NQ.pointValue, R.SPEC.MNQ.tick], [2, 20, 0.25], 'spécifications');

// Les deux desks sont enregistrés
const ids = T.desks().map(x => x.id);
ok(ids.includes('routine') && ids.includes('reglages'), 'desks enregistrés');
const rt = T.desks().find(x => x.id === 'routine');
eq(rt.tabs.map(t => t.id), ['avant', 'pendant', 'apres', 'progression'], 'onglets');
ok(T.DAY_STEPS.find(x => x.id === 'revue').desk === 'routine', 'étape revue pointe ici');

console.log((fail ? 'ÉCHEC ' : 'OK ') + (n - fail) + '/' + n);
process.exit(fail ? 1 : 0);
