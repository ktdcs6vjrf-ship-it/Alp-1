// Desk Plan : fonctions pures, schémas, reliefs. node test/plan.test.js
const { T, lib: L } = require('./harness')(['perf', 'plan']);
let pass = 0, fail = 0;
function ok(c, m) { if (c) pass++; else { fail++; console.log('ÉCHEC', m); } }
function near(a, b, tol, m) { ok(Math.abs(a - b) <= tol, m + ' : ' + a + ' ≠ ' + b + ' ± ' + tol); }
function section(t) { console.log('· ' + t); }

section('Étapes : celles de la carte de séance, dans le même ordre');
ok(JSON.stringify(L.STEPS.map(s => s.id)) === JSON.stringify(T.DAY_STEPS.map(s => s.id)), 'mêmes identifiants que T.DAY_STEPS');
L.STEPS.forEach(s => {
  ok(s.items.length > 0 && s.quoi.length > 0 && s.k5, s.id + ' : liste, préparation et version simple');
  s.schemas.forEach(k => ok(!!L.SCHEMAS[k], s.id + ' : schéma ' + k + ' défini'));
});
ok(L.PREP.every(id => L.STEP[id]), 'étapes de préparation connues');

section('État du jour');
{
  const d = L.normDay({ date: '2026-10-12', checks: { macro: [true, true] }, veille: 'hausse' }, '2026-10-11');
  ok(d.checks.macro.every(v => !v) && d.veille === null, 'un état d’un autre jour repart à zéro');
  const e = L.normDay({ date: '2026-10-11', checks: { macro: [true, false, true] }, veille: 'zz', stop: -2 }, '2026-10-11');
  ok(e.checks.macro.length === L.STEP.macro.items.length && e.checks.macro[0] && e.checks.macro[2], 'cases du jour gardées, longueur fixée par l’étape');
  ok(e.veille === null && e.stop === null, 'valeurs hors domaine écartées');
  ok(L.ownPct(e, 'macro') === 40, 'pourcentage : 2 cases sur 5 = 40 %');
  const t = L.toggle(e, 'macro', 1); ok(L.ownPct(t, 'macro') === 60 && L.ownPct(e, 'macro') === 40, 'toggle sans muter l’original');
  ok(L.prepPct(id => (id === 'macro' ? 100 : 0)) === Math.round(100 / 7), 'préparation : moyenne des sept étapes');
}

section('T.day : pourcentage, compatibilité avec mark');
{
  T.day.setPct('zones', 50); ok(T.day.pct('zones') === 50, 'setPct puis pct');
  T.day.mark('zones'); ok(T.day.pct('zones') === 100, 'une étape faite lit 100');
  T.day.mark('zones', false); ok(T.day.pct('zones') === 50, 'défaite : le pourcentage posé revient');
  ok(T.day.pct('revue') === 0, 'étape jamais touchée : 0');
  ok(T.settings.defaults.winFrom === 0 && T.settings.defaults.winTo === 24 && T.time.inWindow(0, 24, 'Europe/Paris'), 'fenêtre par défaut : toute heure');
}

section('Lecture des niveaux et des annonces');
{
  const z = L.parseLevels('21480-21495, 21620,25 ; FVG 21590–21598\nhaut 21700');
  ok(z.length === 4, 'quatre éléments');
  ok(z[0].lo === 21480 && z[0].hi === 21495 && z[0].mid === 21487.5, 'fourchette');
  ok(z[1].lo === 21620.25 && z[1].hi === 21620.25, 'virgule collée décimale');
  ok(z[2].label === 'FVG' && z[2].lo === 21590 && z[2].hi === 21598, 'libellé et tiret long');
  ok(z[3].label === 'haut', 'libellé simple');
  ok(L.parseLevels('').length === 0 && L.parseLevels('abc').length === 0, 'rien à lire');
  const ev = L.parseTimes('20:00 FOMC, 14h30 CPI, 16 h ISM, 25:00 zz');
  ok(ev.length === 3 && ev[0].hhmm === '14:30' && ev[0].label === 'CPI' && ev[1].min === 960 && ev[2].label === 'FOMC', 'annonces triées, heures invalides écartées');
  const f = L.forbidden(14 * 60 + 28, ev, 5, 15);
  ok(f.now && f.now.ev.label === 'CPI' && f.now.until === 14 * 60 + 45, 'dans la fenêtre interdite du CPI');
  const g = L.forbidden(14 * 60 + 45, ev, 5, 15);
  ok(!g.now && g.next && g.next.ev.label === 'ISM' && g.next.from === 955, 'sortie à l’heure dite, prochaine fenêtre');
  ok(L.minText(-5) === '23:55' && L.minText(1445) === '00:05', 'minutes autour de minuit');
}

section('Biais, sens, taille');
{
  ok(L.biasOf('hausse', 'aligne') === 'long' && L.biasOf('hausse', 'flou') === 'long' && L.biasOf('baisse', null) === 'short', 'la veille donne le sens');
  ok(L.biasOf('hausse', 'casse') === 'both' && L.biasOf('range', 'aligne') === 'both' && L.biasOf(null, 'aligne') === null, 'cassure et range : pas de sens');
  ok(L.allowed('long', 'long') && !L.allowed('long', 'short') && L.allowed('both', 'short') && !L.allowed(null, 'long'), 'sens autorisé');
  ok(/−2 σ/.test(L.sideRule('long', 2).short) && /\+1 σ/.test(L.sideRule('short', 1).short), 'règle de bande');
  ok(L.contracts(150, 6, 2, 1.24) === 11 && L.contracts(150, 0, 2, 1.24) === 0 && L.contracts(10, 6, 2, 1.24) === 0, 'contrats : arrondi en dessous, commission comprise');
  ok(11 * (6 * 2 + 1.24) <= 150 && 12 * (6 * 2 + 1.24) > 150, 'contrats : la perte au stop tient dans le risque');
}

section('Live et journal');
{
  const d = L.normDay({ date: 'x', live: { zone: true, vwap: true, signal: true, risque: true } }, 'x');
  ok(L.liveState(d, true).ok && !L.liveState(d, false).ok && L.liveState(d, false).miss.id === 'fenetre', 'la fenêtre interdite bloque');
  const d2 = L.normDay({ date: 'x', live: { zone: true, vwap: false } }, 'x');
  ok(L.liveState(d2, true).miss.stage === 'vwap' && L.liveState(d2, true).n === 2, 'première case manquante et compte');
  ok(Object.values(L.resetLive(d).live).every(v => !v), 'remise à zéro après une décision');
  const p = L.normPrefs({ trig: 'absorption' });
  const pr = L.prisEntry('long', p, true, 1000, 'MNQ');
  ok(pr.kind === 'pris' && pr.side === 'long' && pr.status === 'ouvert' && pr.plan === true && pr.setup === 'Plan HVZ · Absorption' && pr.at === 1000, 'un trade pris en un geste');
  const rf = L.refusEntry({ stage: 'vwap' }, p, 2000);
  ok(rf.kind === 'refus' && rf.stage === 'vwap' && !('side' in rf) && !('qty' in rf), 'un refus ne porte ni sens ni mise');
  ok(L.normPrefs({ trig: 'les deux', bande: 3, avant: -1 }).trig === null && L.normPrefs({ bande: 3 }).bande === 2 && L.normPrefs({ avant: -1 }).avant === 5, 'préférences normalisées');
  const lv = L.labLevels({ hvz: '100-110, 200', lvn: '150', hist: '' });
  ok(JSON.stringify(lv) === JSON.stringify({ HVZ1: 105, HVZ2: 200, LVN1: 150 }), 'zones pour le Labo : noms et milieux');
  const st = L.todayStats([{ at: Date.now(), kind: 'pris', pnl: -50 }, { at: Date.now(), kind: 'pris', status: 'ouvert' }, { at: Date.now(), kind: 'refus' }], L.dayKeyOf(Date.now()));
  ok(st.taken === 2 && st.losses === 1 && st.open === 1 && st.pnl === -50 && st.n === 3, 'statistiques du jour');
}

section('Trois fins : forme fermée contre simulation');
{
  const inf = L.issues(0.05, 0.1); near(inf.objectif, 0.05 / 0.15, 1e-6, 'barrières proches : a/(a+b)');
  [[0.3, 0.6], [0.5, 1.5], [0.8, 0.8]].forEach(([a, b]) => {
    const q = L.issues(a, b); near(q.objectif + q.stop + q.cloche, 1, 1e-9, 'somme des trois fins');
    const r = T.rng(17), n = 3000, m = 1000, dt = 1 / m; let up = 0, dn = 0;
    for (let k = 0; k < n; k++) { let x = 0, j = 0; for (; j < m; j++) { const u1 = r() || 1e-12, u2 = r(); x += Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2) * Math.sqrt(dt); if (x >= b) { up++; break; } if (x <= -a) { dn++; break; } } }
    // Surveillance discrète : les barrières sont franchies moins souvent (correction β₁·σ√Δt, partie XVI) ; tolérance large.
    near(up / n, q.objectif, 0.035, 'objectif a=' + a + ' b=' + b);
    near(dn / n, q.stop, 0.035, 'stop a=' + a + ' b=' + b);
  });
  const big = L.issues(1, 4); ok(big.cloche > 0.2, 'stop large, grand rapport : la cloche décide souvent (' + big.cloche.toFixed(3) + ')');
}

section('Reliefs : grilles finies, maximum repéré');
['surfFins', 'surfDelai', 'surfProfil'].forEach(k => {
  const s = L[k](8);
  ok(s.vals.length === 8 && s.vals.every(r => r.length === 8 && r.every(v => isFinite(v))), k + ' : grille 8 × 8 finie');
  ok(s.vals[s.argmax[1]][s.argmax[0]] === s.zmax && s.zmin < s.zmax, k + ' : maximum repéré');
  ok(typeof s.z.fmt(s.zmax) === 'string' && typeof s.x.fmt(s.xs[0]) === 'string', k + ' : formats');
});
{
  const d = L.surfDelai(8); near(Math.pow(10, d.fn(1, 10)), 619 / 10 / 52, 1e-9, 'délai : 619 décisions à 10 contacts par semaine, tous gardés');
}

section('Schémas : SVG sans couleur écrite, sans NaN');
Object.keys(L.SCHEMAS).forEach(k => {
  const svg = L.schemaSvg(L.SCHEMAS[k].d);
  ok(/^<svg /.test(svg) && !/NaN|undefined/.test(svg), k + ' : SVG propre');
  ok(!/#[0-9a-fA-F]{3,6}\b/.test(svg), k + ' : aucune couleur écrite en dur');
  ok(L.SCHEMAS[k].t && L.SCHEMAS[k].lire && L.SCHEMAS[k].k5, k + ' : titre, lecture et version simple');
});
{
  const pts = L.noisy([[0, 10], [50, 60], [100, 20]], 3, 5);
  ok(pts[0][1] === 10 && pts.some(p => p[0] === 50 && p[1] === 60) && pts[pts.length - 1][1] === 20, 'le bruit garde les pivots');
  ok(JSON.stringify(pts) === JSON.stringify(L.noisy([[0, 10], [50, 60], [100, 20]], 3, 5)), 'bruit déterministe');
}

section('Textes : apostrophes typographiques, pas de chiffre de marché');
{
  const fs = require('fs'), src = fs.readFileSync(require('path').join(__dirname, '..', 'src', 'desks', 'plan.js'), 'utf8');
  const strs = src.match(/'(?:[^'\\\n]|\\.)*'/g) || [];
  ok(!strs.some(s => /[a-zé]’?'[a-zé]/i.test(s.slice(1, -1))), 'aucune apostrophe droite dans un texte');
  ok(!/#[0-9a-fA-F]{6}\b/.test(src), 'aucune couleur écrite en dur');
}

console.log(fail ? 'ÉCHEC — plan : ' + pass + ' réussis, ' + fail + ' échoués' : 'OK — plan : ' + pass + ' réussis, 0 échoués');
process.exitCode = fail ? 1 : 0;
