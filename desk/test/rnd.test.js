// Desk R&D : Scalp Mur. node test/rnd.test.js
const { T, lib: R } = require('./harness')(['perf', 'plan-fig', 'plan', 'rnd']);
let pass = 0, fail = 0;
function ok(c, m) { if (c) pass++; else { fail++; console.log('ÉCHEC', m); } }
function near(a, b, tol, m) { ok(Math.abs(a - b) <= tol, m + ' : ' + a + ' ≠ ' + b + ' ± ' + tol); }
function section(t) { console.log('· ' + t); }
const set = { commissionRT: 1.24, tick: 0.25, pointValue: 2, instrument: 'MNQ' };

section('La carte : six mots, quatre interdits');
ok(R.MOTS.length === 6 && R.MOTS.every(x => x.m && x.t && x.s), 'six mots, chacun avec sa phrase et son détail');
ok(R.INTERDITS.length === 4, 'quatre interdits');

section('Coûts, point mort, loi nulle');
near(R.cout(set), 1.24 + 1, 1e-12, 'coût : commission et un tick par jambe');
near(R.pointMort(4, 2, set), (8 + 2.24) / 24, 1e-12, 'point mort à 1:2, stop 4 points');
ok(R.pointMort(1, 2, set) > R.pointMort(4, 2, set) && R.pointMort(4, 2, set) > 1 / 3, 'stop minuscule : point mort plus haut ; toujours au-dessus de la loi nulle');
const tc = R.tableCouts(set, 2); ok(tc.every((r, i) => !i || r.pm < tc[i - 1].pm), 'point mort décroissant avec le stop');
near(R.stopMinimal(set) * set.pointValue * 0.2, R.cout(set), 1e-12, 'stop minimal : coûts = 20 % du risque');
{
  // Loi nulle contrôlée par simulation : marche symétrique au tick, +2R avant −1R.
  const r = T.rng(5); let up = 0, n = 6000;
  for (let k = 0; k < n; k++) { let x = 0; while (x > -8 && x < 16) x += r() < 0.5 ? -1 : 1; if (x >= 16) up++; }
  near(up / n, R.LOI_NULLE, 0.02, 'loi nulle : 2R avant 1R une fois sur trois (simulée)');
}
{
  const n = R.tradesPourPreuve(0.4); ok(n > 400 && n < 1000, 'trades pour séparer +5 points de 40 % : ' + n);
  ok(R.tradesPourPreuve(0.4, 0.10) < n, 'un effet plus grand demande moins de trades');
}

section('Le testeur');
{
  const e = R.entree('gain', 'long', 1000, 'MNQ'); ok(e.kind === 'pris' && e.setup === R.SETUP && e.r === 2 && e.status === 'clos' && e.side === 'long' && e.fin === 'objectif', 'gain inscrit');
  ok(R.entree('perte', 'short', 1, 'MNQ').r === -1 && R.entree('temps', 'short', 1, 'MNQ').fin === 'cloche', 'perte et sortie au temps');
  const rf = R.refus(5); ok(rf.kind === 'refus' && !('side' in rf) && rf.setup === R.SETUP, 'une passe ne porte ni sens ni mise');
  const rows = [R.entree('gain', 'long', 1, 'MNQ'), R.entree('perte', 'long', 2, 'MNQ'), R.entree('perte', 'long', 3, 'MNQ'), { kind: 'pris', setup: 'autre', r: 5, at: 4 }, R.refus(6)];
  const st = R.stats(rows);
  ok(st.n === 3 && st.gains === 1 && Math.abs(st.wr - 1 / 3) < 1e-12 && st.totalR === 0 && st.passes === 1 && st.eq.length === 3 && st.eq[2][1] === 0, 'statistiques du setup seul');
}

section('Études : chaque affirmation a son verdict et ses sources');
R.ETUDES.forEach((e, i) => {
  ok(e.q && R.VERDICTS[e.v] && e.p.length && e.implication, 'étude ' + i + ' complète');
  ok(e.src.length && e.src.every(s => /^https:\/\//.test(s[1])), 'étude ' + i + ' : sources en lien');
});
ok(R.ETUDES.some(e => e.v === 'non') && R.ETUDES.some(e => e.v === 'établi'), 'des verdicts dans les deux sens');

section('Textes');
{
  const src = require('fs').readFileSync(require('path').join(__dirname, '..', 'src', 'desks', 'rnd.js'), 'utf8');
  ok(!/#[0-9a-fA-F]{6}\b/.test(src), 'aucune couleur écrite en dur');
}
console.log(fail ? 'ÉCHEC — rnd : ' + pass + ' réussis, ' + fail + ' échoués' : 'OK — rnd : ' + pass + ' réussis, 0 échoués');
process.exitCode = fail ? 1 : 0;
