// Tests du desk « Stratégie intraday » : node test/micro.test.js (sortie non nulle si échec).
// Le calcul du seuil est évalué hors du contexte vm, à partir de son seul texte source : c’est la preuve qu’il est
// autonome (le Web Worker de T.compute l’exécute ainsi). Chaque nombre tiré d’ALP nº 3 est relu dans le texte brut
// du document (scratchpad/alp3txt) et, pour les seuils déclarés, dans le code du dépôt (alp1/setups.py, alp1/concepts.py).
const fs = require('fs'), path = require('path');
const { T, lib: L } = require('./harness')('micro');
const { lib: J } = require('./harness')('journal');
const seuil = eval('(' + L.seuil.toString() + ')');
const F = T.fmt;
let fails = 0, passes = 0;
function ok(cond, msg) { if (cond) passes++; else { fails++; console.error('ÉCHEC', msg); } }
function eq(a, b, msg) { ok(a === b, msg + ' : « ' + a + ' » attendu « ' + b + ' »'); }
function near(a, b, tol, msg) { ok(typeof a === 'number' && Math.abs(a - b) <= tol, msg + ' : ' + a + ' attendu ' + b + ' ± ' + tol); }
function section(t) { console.log('· ' + t); }
const sp = s => String(s).replace(/[    ]/g, ' ');
const SP = path.join(__dirname, '..', '..');
const txt = n => sp(fs.readFileSync(path.join(require('./harness').ALP3, 'p' + n + '.txt'), 'utf8'));
const P03 = txt('03');
const pc1 = v => sp(F.num(v, 1, '%'));
function block(s, from, to) { const i = s.indexOf(from); const j = to ? s.indexOf(to, i + from.length) : -1; return i < 0 ? '' : s.slice(i, j < 0 ? undefined : j); }
function rowOf(blk, name) { const line = blk.split('\n').find(l => l.startsWith('| ' + name + ' |')); return line ? line.slice(2).split(' | ').map(x => x.trim()) : null; }

/* ===================================================================== */
section('Seuil µ* : port exact, référence ES (σ 1 min 1,25 ; σ séance 60 ; c 0,33 ; séance 390 min)');
const REF = { c: 0.33, s1: 1.25, sS: 60, T: 390, drift: 0 };
const g010 = seuil(Object.assign({ a: 0.6, rr: 20 }, REF));
const g050 = seuil(Object.assign({ a: 3, rr: 20 }, REF));
const g150 = seuil(Object.assign({ a: 9, rr: 20 }, REF));
eq(sp(F.num(g010.mu, 3)), '8,189', 'stop 0,010 % (0,6 pt) à 1:20 : µ* borné');
eq(sp(F.int(g010.N)), '474', 'stop 0,010 % : décisions requises');
eq(sp(F.int(g050.N)), '10 568', 'stop 0,050 % (3 pt) : décisions requises');
eq(sp(F.num(g150.mu, 3)), '0,196', 'stop 0,150 % (9 pt) : µ* borné');
eq(sp(L.fmtMu(g010.mu)), '8,189', 'affichage de µ* à trois décimales');
eq(sp(F.num(g010.muNB, 2)), '3,75', 'stop déclaré : µ* non borné (partie XXX)');
eq(sp(F.num(g150.portee, 2)), '7,29', 'stop élargi à 1:20 : objectif à 7,29 σ de séance');
eq(sp(F.num(g150.ecartSeance, 1)), '24,7', 'une séance parcourt 24,7 points');
eq(sp(F.num(g150.pOpen * 100, 1)), '28,5', 'stop élargi : 28,5 % des positions finissent à la cloche');
near(g010.pOpen, 0, 5e-4, 'stop déclaré : aucune position à la cloche');
eq(sp(F.num(g150.rrMax, 1)), '5,2', 'stop élargi : rapport autorisé par la séance à 5 %');
eq(sp(F.num(g150.hOpt, 0)), '102', 'horizon d’épreuve, 102 minutes');
eq(sp(F.num(g150.ecartOpt, 1)), '43,4', 'écart directionnel maximal, 43,4 points de taux');
near(g010.er0, -0.33 / 0.6, 1e-12, 'loi nulle : E[R] = −c/a à dérive nulle');
near(g010.nullRate, 1 / 21, 1e-12, 'taux nul à 1:20 = 1/(1+R:R)');
eq(sp(F.pct(g010.nullRate, 2)), '4,76 %', 'taux nul à 1:20, 4,76 %');
const P11 = txt('11'), P13 = txt('13'), P30 = txt('30');
ok(P11.indexOf('8,19') >= 0 && P11.indexOf('0,196') >= 0, 'partie XI : 8,19 et 0,196 publiés');
ok(/Stop à 0,050 % \| 0,050 % \| [^\n]*\| 10 568/.test(P13), 'partie XIII : 10 568 décisions au stop de 0,050 %');
ok(/474 décisions/.test(P13), 'partie XIII : 474 décisions à la géométrie déclarée');
['3,75', '7,29', '28,5 %', '5,2', '102 min', '43,4', '24,7'].forEach(k => ok(P30.indexOf(k) >= 0, 'partie XXX publie ' + k));
eq(L.verdict(g010).code, 'domaine', 'stop déclaré : à portée mais hors domaine');
eq(L.verdict(g150).code, 'portee', 'stop élargi à 1:20 : payant mais hors de portée');
const lect15 = seuil(Object.assign({ a: 1.25 * Math.sqrt(15), rr: 2 }, REF));
eq(L.verdict(lect15).code, 'ok', 'lecture 15 min à 1:2 : les deux conditions passent');
ok(L.verdict(null).code === 'err' && L.verdict({ err: 'x' }).code === 'err', 'verdict sans résultat');
ok(seuil({ a: 0, rr: 2, c: 0.33, s1: 1.25, sS: 60, T: 390 }).err, 'paramètre invalide → erreur, pas de nombre');
{
  const d = seuil(Object.assign({}, REF, { a: 1.25 * Math.sqrt(15), rr: 2, drift: 3.2 }));
  near(d.erD, (3.2 / 60 * d.expo - 0.33) / d.a, 1e-12, 'E[R] à dérive déclarée = (µ·E[τ∧T] − c)/a');
  near(d.mu, lect15.mu, 1e-12, 'µ* ne dépend pas de la dérive déclarée');
  near(d.mu, 0.33 / d.expo * 60, 1e-12, 'µ* = c / E[τ∧T]');
}
eq(sp(F.num(L.caseMin(0.45), 1)), '8,4', 'case du NQ : 60 · 0,45 / 3,2 = 8,4 min (« tenue ≥ 8,4 min »)');
near(L.frictionOf({ commissionRT: 4, pointValue: 20, tick: 0.25 }), 0.45, 1e-12, 'préréglage NQ : 4 $ / 20 $ + 1 tick');
near(L.frictionOf({ commissionRT: 4, pointValue: 2, tick: 0.25 }), 2.25, 1e-12, 'préréglage MNQ : 4 $ / 2 $ + 1 tick');
near(L.frictionOf(T.settings.defaults), 1.24 / 2 + 0.25, 1e-12, 'mes réglages : commission / valeur du point + 1 tick');
ok(isNaN(L.frictionOf({ pointValue: 0 })), 'réglages incomplets → pas de friction');
{
  const s0 = L.normSeuil(null);
  ok(s0.preset === 'ref' && s0.level === 6000 && s0.c === 0.33 && Math.abs(s0.a - 1.25 * Math.sqrt(15)) < 1e-12 && s0.rr === 2, 'état par défaut : référence, lecture 15 min à 1:2');
  ok(L.normSeuil({ c: 'x', preset: 'zz', rr: NaN }).c === 0.33 && L.normSeuil({ preset: 'zz' }).preset === 'ref', 'valeurs illisibles → défauts');
  const q = L.applyPreset(Object.assign({}, s0, { s1: 9 }), 'nq', T.settings.defaults);
  ok(q.c === 0.45 && q.s1 === 9 && q.preset === 'nq', 'NQ ne change que la friction');
  ok(L.applyPreset(q, 'ref').s1 === 1.25, 'Réf. ALP remet la calibration du document');
  ok(Math.abs(L.applyPreset(s0, 'moi', T.settings.defaults).c - 0.87) < 1e-9, 'mes réglages → c = 0,87 pt');
  const g = L.applyGeo(s0, 0.010); ok(Math.abs(g.a - 0.6) < 1e-12 && g.rr === 20, '0,010 % de 6 000 = 0,6 pt à 1:20');
  const hz = L.applyHorizon(s0, 30); ok(Math.abs(hz.a - 1.25 * Math.sqrt(30)) < 1e-12 && hz.rr === 2, 'lecture 30 min : stop σ√h à 1:2');
  const cp = L.calcParams(s0); ok(Object.keys(cp).sort().join() === 'T,a,c,drift,rr,s1,sS', 'paramètres envoyés au calcul');
}

/* ===================================================================== */
section('Plan VWAP : état du jour, biais, refus et brouillon');
const today = '2026-10-09';
{
  const st = L.stages({ winFrom: 0, winTo: 9 });
  ok(st.map(s => s.items.length).join() === '3,5,4', 'trois étapes : 3, 5 et 4 conditions');
  ok(st.every(s => s.k5 && s.items.every(it => it.k && (it.s || it.dyn))), 'chaque condition a son explication et sa version « 5 ans »');
  eq(st[1].items[0].t, 'Dans la fenêtre 00 h – 09 h', 'fenêtre lue dans les réglages');
  ok(st[1].items[0].s.indexOf('entre minuit et 9 h') === 0 + 'Cherche des trades seulement '.length, 'fenêtre en toutes lettres');
  ok(L.stages({ winFrom: 1, winTo: 7 })[1].sub.indexOf('01 h – 07 h') > 0, 'une autre fenêtre se recompose');
  ok(L.TRADE.rules({ winFrom: 0, winTo: 9 })[1][1].indexOf('ou 9 h (fin de ta fenêtre)') > 0, 'quatre fins : la fin de fenêtre suit les réglages');
  ok(/acheteur/.test(L.vwapSub('long')) && /vendeur/.test(L.vwapSub('short')) && /Choisis le biais/.test(L.vwapSub(null)), 'bon côté de la VWAP selon le biais');
}
{
  const p0 = L.normPlan(null, today);
  ok(p0.date === today && p0.checks.T.length === 3 && p0.checks.B.length === 5 && p0.checks.P.length === 4 && !p0.dir && p0.sig === 'rejet', 'plan vierge');
  const old = { date: '2026-10-08', checks: { T: [true, true, true], B: [true], P: [] }, dir: 'long', dirAt: 5, side: 'long', sig: 'absorption', kid: true };
  const p1 = L.normPlan(old, today);
  ok(p1.checks.T.every(x => !x) && !p1.dir && !p1.side && p1.kid && p1.sig === 'absorption', 'un nouveau jour efface coches et biais, garde la version et le signal');
  const p2 = L.normPlan(Object.assign({}, old, { date: today }), today);
  ok(p2.checks.T.every(Boolean) && p2.checks.B[0] && !p2.checks.B[1] && p2.dir === 'long', 'le même jour garde les coches');
  ok(!L.passed(p2, 'T', null) && L.passed(p2, 'T', 'long'), 'l’étape 1 exige un biais');
  eq(L.activeKey(p2, 'long'), 'B', 'étape active après l’étape 1');
  let p = p2; for (let i = 0; i < 5; i++) if (!p.checks.B[i]) p = L.toggle(p, 'B', i);
  for (let i = 0; i < 4; i++) p = L.toggle(p, 'P', i);
  eq(L.activeKey(p, 'long'), 'X', 'les trois étapes passent : nœud Trade');
  ok(p2.checks.P.every(x => !x), 'toggle ne modifie pas l’état reçu');
  const r = L.afterDecision(p);
  ok(r.checks.B.every(x => !x) && r.checks.P.every(x => !x) && r.checks.T.every(Boolean) && r.dir === 'long', 'après une décision : étapes 2 et 3 à zéro, étape 1 gardée');
  const n = L.newSession(p);
  ok(n.checks.T.every(x => !x) && !n.dir, 'nouvelle séance : tout à refaire');
  eq(L.nDone(p2, 'B'), 1, 'compte des conditions cochées');
}
{
  const rf = L.refus('B', 'rejet', 123);
  ok(rf.kind === 'refus' && rf.stage === 'vwap' && rf.at === 123 && rf.setup === 'Bande VWAP · Rejet' && !('side' in rf) && !('qty' in rf), 'refus : étape, heure, setup, ni sens ni mise');
  ok(L.refus('T', 'rejet', 1).stage === 'biais' && L.refus('P', 'rejet', 1).stage === 'declencheur' && L.refus('X', 'absorption', 1).stage === 'declencheur', 'étapes du journal');
  ok(J.STAGES.some(s => s.v === L.refus('T').stage) && J.STAGES.some(s => s.v === L.refus('B').stage) && J.STAGES.some(s => s.v === L.refus('P').stage), 'étapes reconnues par le journal');
  const ps = J.parseSetup(L.setupText('absorption'));
  ok(ps.level === 'Bande VWAP' && ps.conf === 'Absorption', 'le journal lit le setup « Bande VWAP · Absorption »');
  const d = L.draft('long', null, 'rejet');
  ok(d.kind === 'pris' && d.side === 'long' && d.setup === 'Bande VWAP · Rejet', 'brouillon pris, sens tiré du biais');
  ok(L.draft('both', null, 'rejet') === null && L.draft('both', 'short', 'rejet').side === 'short', 'biais neutre : le sens se choisit au nœud Trade');
  ok(L.draft('short', 'long', 'rejet').side === 'short', 'le biais vendeur interdit le long');
  const f = J.fromDraft(J.blankForm(), d);
  ok(f.kind === 'pris' && f.side === 'long' && f.level === 'Bande VWAP' && f.conf === 'Rejet', 'le formulaire du journal se pré-remplit avec le brouillon');
  eq(L.tradeLabel('both', null), '⇅ selon la bande', 'libellé neutre');
  eq(L.tradeLabel('long', null), '▲ long à −2σ', 'libellé acheteur');
}
{
  ok(L.parseBias({ date: today, bias: 'acheteur' }, today) === 'long', 'biais NQ du jour : acheteur');
  ok(L.parseBias({ date: today, value: 'neutre' }, today) === 'both', 'biais NQ : neutre');
  ok(L.parseBias({ day: today, dir: 'short' }, today) === 'short', 'biais NQ : autre forme');
  ok(L.parseBias({ date: '2026-10-08', bias: 'long' }, today) === null, 'biais NQ d’hier ignoré');
  ok(L.parseBias('long', today) === null, 'chaîne sans date ignorée');
  ok(L.parseBias({ at: Date.now(), v: 'vendeur' }, L.dayKeyOf(Date.now())) === 'short', 'biais horodaté du jour');
  ok(L.normDir('xyz') === null && L.normDir('Buy') === 'long', 'lecture du mot');
  const base = L.normPlan(null, today);
  let e = L.effBias(base, { date: today, bias: 'short', at: 100 }, today);
  ok(e.dir === 'short' && e.src === 'nq', 'sans choix local, le biais du desk NQ');
  e = L.effBias(Object.assign({}, base, { dir: 'long', dirAt: 200 }), { date: today, bias: 'short', at: 100 }, today);
  ok(e.dir === 'long' && e.src === 'local' && e.nq === 'short', 'choix local plus récent');
  e = L.effBias(Object.assign({}, base, { dir: 'long', dirAt: 50 }), { date: today, bias: 'short', at: 100 }, today);
  ok(e.dir === 'short' && e.src === 'nq', 'biais NQ plus récent');
  ok(L.effBias(base, null, today).dir === null, 'aucun biais');
}
{
  const P12 = txt('12'), P17 = txt('17'), P19 = txt('19');
  ok(P03.indexOf('12,68') >= 0, '12,68 contacts par séance (partie III)');
  ok(P03.indexOf('48,7 %') >= 0 && P03.indexOf('49,4 %') >= 0, '48,7 % contre 49,4 % (partie III)');
  ok(P17.indexOf('divise µ* par 2,22') >= 0, 'ordre limite : µ* divisé par 2,22 (partie XVII)');
  ok(P12.indexOf('−0,164 R') >= 0 && P12.indexOf('−1,353 R') >= 0, 'point mort −0,164 R, stop suiveur −1,353 R (partie XII)');
  ok(/1,177/.test(P19), 'largeur d’un niveau gamma ≈ 1,2 σ (1,177, partie XIX)');
}

/* ===================================================================== */
section('Setups : tables 6, 7 et 8 relues dans le texte');
{
  ok(L.NIVEAUX.length === 6 && L.CONFS.length === 3 && L.SETUPS.length === 12, '6 niveaux, 3 confirmations, 12 setups');
  const pairs = new Set(L.SETUPS.map(s => s.niv + '-' + s.conf));
  ok(pairs.size === 12 && L.SETUPS.every(s => L.NIVEAUX.some(n => n.k === s.niv) && L.CONFS.some(c => c.k === s.conf)), 'chaque setup croise un niveau et une confirmation');
  ok(new Set(L.NIVEAUX.map(n => n.fam)).size === 4, 'quatre familles de niveaux');
  L.SETUPS.forEach(s => { const n = L.NIVEAUX.find(x => x.k === s.niv); ok(n.contacts === s.contacts, s.n + ' : contacts du niveau'); });
  const T6 = block(P03, 'Table 6 —', 'Table 7 —');
  L.NIVEAUX.forEach(n => ok(T6.indexOf(n.calc) >= 0, 'table 6 : calcul du niveau ' + n.n));
  const T7 = block(P03, 'Table 7 —', 'Lecture.');
  L.SETUPS.forEach(s => {
    const f = rowOf(T7, s.n);
    if (!f) { ok(false, 'table 7 : ligne ' + s.n); return; }
    const mine = [s.n, s.fam, sp(F.num(s.contacts, 2)), pc1(s.part), sp(F.int(s.obs)), pc1(s.dementie), pc1(s.pBrut), pc1(s.pConf), sp(F.num(s.mfe, 2) + ' / ' + F.num(s.mae, 2))];
    eq(mine.join(' | '), f.join(' | '), 'table 7 : ' + s.n);
  });
  const pool = rowOf(T7, 'Les douze, mis en commun');
  eq(pool.join(' | '), 'Les douze, mis en commun | — | — | — | ' + sp(F.int(L.POOL.obs)) + ' | — | ' + pc1(L.POOL.pBrut) + ' | ' + pc1(L.POOL.pConf) + ' | rapport ' + sp(F.num(L.POOL.rapport, 2)), 'table 7 : mise en commun');
  ok(P03.indexOf('Sur ' + sp(F.int(L.POOL.contacts)) + ' contacts à fenêtres disjointes') >= 0, '20 874 contacts bruts');
  ok(P03.indexOf('demi-intervalle de ' + sp(F.num(L.POOL.demi, 1)) + ' point') >= 0, 'demi-intervalle 1,4 point');
  ok(P03.indexOf(sp(F.int(L.POOL.seances)) + ' séances sans dérive') >= 0, '900 séances');
  const T8 = block(P03, 'Table 8 —', 'Lecture.');
  L.SETUPS.forEach(s => {
    const f = rowOf(T8, s.n);
    if (!f) { ok(false, 'table 8 : ligne ' + s.n); return; }
    const mine = [s.n, s.hz, sp(F.int(s.N)), sp(F.int(s.cAn)), sp(F.int(s.confAn)), sp(L.fmtAns(s.sans)), sp(L.fmtAns(s.avec)), '×' + sp(F.num(s.facteur, 1)), sp(F.num(s.muComp, 2)), s.verdictPub];
    eq(mine.join(' | '), f.join(' | '), 'table 8 : ' + s.n);
    eq(L.verdictSetup(s.muComp), s.verdictPub, 'verdict calculé = verdict publié : ' + s.n);
    const lec = L.LECTURES.find(x => x.hz === s.hz && x.N === s.N);
    ok(!!lec, s.n + ' : décisions requises = celles de la lecture du même horizon');
    if (lec) near(s.muComp, lec.mu * Math.sqrt(s.facteur), 0.02, s.n + ' : µ compensatrice = µ* · √facteur');
    near(s.avec / s.sans, s.facteur, s.facteur * 0.05, s.n + ' : délai avec / sans ≈ facteur');
  });
  ok(L.verdictSetup(0.6) === 'une dérive ordinaire suffit' && L.verdictSetup(0.61) === 'il faut une dérive haute' && L.verdictSetup(3.2) === 'il faut une dérive haute' && L.verdictSetup(3.21) === 'hors du domaine : irremboursable', 'bornes du verdict');
}
{
  const S = L.SEUILS;
  ok(L.CONFS[0].crit[0][1].indexOf(sp(F.num(S.volume, 1))) >= 0 || sp(L.CONFS[0].crit[0][1]).indexOf(sp(F.num(S.volume, 1))) >= 0, 'absorption : volume 1,5 × médiane');
  ok(sp(L.CONFS[0].crit[1][1]).indexOf(sp(F.num(S.z, 2))) >= 0, 'absorption : |z| < 0,25');
  ok(sp(L.CONFS[1].crit[0][1]).indexOf(sp(F.num(S.meche * 100, 0))) >= 0, 'rejet : mèche 60 %');
  ok(sp(L.CONFS[2].crit[1][1]).indexOf(sp(F.num(S.delta * 100, 0))) >= 0, 'traversée : delta 33 %');
  ok(L.CONFS.every(c => c.inv.indexOf(S.fenetre + ' minutes') >= 0), 'invalidation à 15 minutes');
  const repo = '/home/user/Alp-1/alp1';
  if (fs.existsSync(path.join(repo, 'setups.py'))) {
    const py = fs.readFileSync(path.join(repo, 'setups.py'), 'utf8'), cpt = fs.readFileSync(path.join(repo, 'concepts.py'), 'utf8');
    ok(/^MULT_VOLUME = 1\.5$/m.test(py) && S.volume === 1.5, 'code : MULT_VOLUME = 1,5');
    ok(/^PART_MECHE = 0\.60$/m.test(py) && S.meche === 0.6, 'code : PART_MECHE = 0,60');
    ok(/^DEPASSEMENT = 1\.0$/m.test(py) && S.depassement === 1, 'code : DEPASSEMENT = 1 σ');
    ok(/^PART_DELTA = 1\.0 \/ 3\.0$/m.test(py) && Math.abs(S.delta - 1 / 3) < 1e-15, 'code : PART_DELTA = 1/3');
    ok(/^FENETRE = 15$/m.test(py) && S.fenetre === 15, 'code : FENETRE = 15');
    ok(/^SEUIL_PIVOT = 6\.0$/m.test(py), 'code : zigzag de 6 points');
    ok(/^Z_ABSORPTION = 0\.25$/m.test(cpt) && S.z === 0.25, 'code : Z_ABSORPTION = 0,25');
  } else console.log('  (dépôt absent : contrôle du code sauté)');
}

/* ===================================================================== */
section('Lectures : tables 2, 3 et 5 relues dans le texte');
{
  ok(L.LECTURES.length === 15 && L.familles().length === 8, '15 lectures, 8 familles');
  ok(L.minutes('1,5 h') === 90 && L.minutes('1 séance') === 390 && L.minutes('3 séances') === 1170 && L.minutes('5 min') === 5 && isNaN(L.minutes('demain')), 'horizon converti en minutes');
  const o = L.ordre();
  ok(o.every((x, i) => i === 0 || x.minutes >= o[i - 1].minutes), 'ordre calculé : horizon croissant');
  ok(o.every((x, i) => x.rang === i + 1 && x.n === i + 1), 'l’ordre calculé retrouve celui de la table 2');
  { const keep = L.LECTURES; L.LECTURES = keep.slice().reverse(); const r = L.ordre().map(x => x.minutes); L.LECTURES = keep;
    ok(r.every((m, i) => i === 0 || m >= r[i - 1]), 'écrit à l’envers, le catalogue se range encore par horizon'); }
  const T2 = block(P03, 'Table 2 —', 'Lecture.'), T3 = block(P03, 'Table 3 —', 'Lecture.'), T5 = block(P03, 'Table 5 —', 'Lecture.');
  L.LECTURES.forEach(x => {
    const line2 = T2.split('\n').find(l => l.startsWith('| ' + x.n + ' | '));
    eq(line2, '| ' + x.n + ' | ' + x.nom + ' | ' + x.fam + ' | ' + x.hz + ' | ' + sp(F.num(x.occ, 2)) + ' | ' + pc1(x.freq) + ' | ' + x.loi, 'table 2 : ' + x.nom);
    const f5 = rowOf(T5, x.nom);
    eq(f5 && f5.join(' | '), [x.nom, x.hz, sp(F.num(x.a, 2)), sp(F.num(L.TAUX_NUL, 2, '%')), sp(F.num(x.req, 2, '%')), sp(F.num(x.mu, 3)), sp(F.int(x.N)), sp(F.int(x.an)), sp(L.fmtDelai(x.delai)), sp(F.int(x.muN))].join(' | '), 'table 5 : ' + x.nom);
    const f3 = rowOf(T3, x.nom);
    ok(!!f3 && f3[1].replace('délta', 'delta') === x.sit && f3[2] === x.att, 'table 3 : situation et attente de ' + x.nom);
    eq(f3 && f3.slice(3).join(' | '), ['0,00', sp(F.num(x.depH, 2)), sp(F.num(x.gain, 1))].join(' | '), 'table 3 : déplacements de ' + x.nom);
    near(L.annees(x.delai), x.N / x.an, Math.max(0.02 * x.N / x.an, 0.006), x.nom + ' : délai ≈ décisions / décisions par an');
    ok(Math.abs(x.mu * x.N - x.muN) <= 0.0005 * x.N + 1, x.nom + ' : µ*·N cohérent avec l’arrondi de µ*');
  });
  eq(L.etablissables(), 8, 'lectures établissables en moins de 30 ans');
  ok(P03.indexOf('8 s’établissent en moins de 30 ans et 7 n’y parviennent pas') >= 0, 'le texte publie 8 et 7');
  eq(sp(L.fmtDelai([11.0, 'millénaires'])), '11,0 millénaires', 'délai en millénaires');
  eq(sp(L.fmtDelai([1048, 'ans'])), '1 048 ans', 'délai en ans au-delà de cent');
  eq(sp(L.fmtDelai(null)), '—', 'délai absent → tiret');
  near(L.annees([3.5, 'mois']), 3.5 / 12, 1e-12, 'mois → années');
}

/* ===================================================================== */
section('Pureté et calcul en tâche de fond');
ok(T.store.get('micro:plan', null) === null && T.store.get('micro:seuil', null) === null, 'les fonctions pures n’écrivent rien');
T.compute(L.seuil, Object.assign({ a: 0.6, rr: 20 }, REF)).then(r => {
  eq(sp(F.num(r.mu, 3)), '8,189', 'T.compute rend le même µ*');
  console.log(passes + ' contrôles passés, ' + fails + ' échec(s)');
  process.exit(fails ? 1 : 0);
}, e => { ok(false, 'T.compute : ' + e); console.log(passes + ' passés, ' + fails + ' échec(s)'); process.exit(1); });
