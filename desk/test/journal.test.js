// Tests du desk « Journal » : node test/journal.test.js (sortie non nulle si échec).
// Les valeurs de référence des statistiques ont été calculées à part en Python pur
// (stdlib : statistics, math), indépendamment du code JavaScript, sur l’échantillon ci-dessous.
const fs = require('fs'), path = require('path');
const { T, lib: J } = require('./harness')('journal');
let fails = 0, passes = 0;
function ok(cond, msg) { if (cond) passes++; else { fails++; console.error('ÉCHEC', msg); } }
function near(a, b, tol, msg) { const good = typeof a === 'number' && typeof b === 'number' && (a === b || Math.abs(a - b) <= tol * Math.max(1, Math.abs(b))); ok(good, msg + ' : ' + a + ' attendu ' + b); }
function eq(a, b, msg) { ok(JSON.stringify(a) === JSON.stringify(b), msg + ' : ' + JSON.stringify(a) + ' attendu ' + JSON.stringify(b)); }
function section(t) { console.log('· ' + t); }
const E = 1e-12;

section('Enregistrement du desk');
const d = T.desks().find(x => x.id === 'journal');
ok(!!d, 'le desk est enregistré');
eq(d && [d.label, d.glyph, d.group, d.order], ['Journal', 'J', 'Exécution', 60], 'identité du desk');
eq(d && d.tabs.map(t => t.id), ['saisir', 'registre', 'stats'], 'onglets');

section('P&L net et R');
// Long 1 MNQ : (20 020 − 20 000) × 1 × 1 × 2 − 1,24 × 1 = 38,76 $ ; risque 10 × 1 × 2 = 20 $ ; R = 1,938.
const L = { side: 'long', entry: 20000, stop: 19990, exit: 20020, qty: 1 };
near(J.pnl(L, 2, 1.24), 38.76, E, 'P&L long');
near(J.riskUsd(L, 2), 20, E, 'risque engagé');
near(J.rMultiple(L, 38.76, 2), 1.938, E, 'R long');
// Short 2 MNQ, stop touché : (20 110 − 20 100) × −1 × 2 × 2 − 1,24 × 2 = −42,48 $ ; R = −42,48 / 40.
const Sh = { side: 'short', entry: 20100, stop: 20110, exit: 20110, qty: 2 };
near(J.pnl(Sh, 2, 1.24), -42.48, E, 'P&L short avec commission × quantité');
near(J.rMultiple(Sh, -42.48, 2), -1.062, E, 'R short');
// NQ : valeur du point 20.
near(J.pnl({ side: 'long', entry: 20000, exit: 20001.25, qty: 3 }, 20, 4.5), 1.25 * 3 * 20 - 13.5, E, 'P&L NQ');
// La valeur du point et la commission scellées dans l’entrée priment quand on ne les passe pas.
near(J.pnl({ side: 'short', entry: 100, exit: 90, qty: 1, pv: 2, comm: 1 }), 19, E, 'pv et commission lus dans l’entrée');
ok(isNaN(J.pnl({ side: 'flat', entry: 1, exit: 2, qty: 1 }, 2, 1)), 'sens inconnu → NaN');
ok(isNaN(J.rMultiple({ side: 'long', entry: 10, stop: 10, qty: 1 }, 5, 2)), 'stop à l’entrée → R indéfini');
near(J.rr({ side: 'long', entry: 100, stop: 90, target: 125 }), 2.5, E, 'rapport prévu long');
near(J.rr({ side: 'short', entry: 100, stop: 104, target: 92 }), 2, E, 'rapport prévu short');
ok(isNaN(J.rr({ side: 'long', entry: 100, stop: 90, target: 95 })), 'objectif du mauvais côté → NaN');
// Loi nulle : à dérive nulle E[R] = −c/L (ALP nº 3, partie XI).
near(J.nullR({ entry: 20000, stop: 19990, qty: 1 }, 2, 1.24), -0.062, E, 'espérance sans avantage −c/L');
near(J.nullR({ entry: 20000, stop: 19990, qty: 3 }, 2, 1.24), -0.062, E, '−c/L ne dépend pas de la quantité');
eq(J.maxQty(150, { entry: 20000, stop: 19990 }, 2), 7, 'taille maximale à 150 $ et 10 pt');
eq(J.maxQty(150, { entry: 20000, stop: 19962.5 }, 2), 2, 'taille maximale arrondie vers le bas');
eq(J.maxQty(150, { entry: 20000, stop: 19900 }, 2), 0, 'même un contrat dépasse');

section('Setup');
eq(J.parseSetup('Bande VWAP · Rejet'), { level: 'Bande VWAP', conf: 'Rejet' }, 'setup canonique');
eq(J.parseSetup('Noeud faible volume · Traversee'), { level: 'Nœud faible volume', conf: 'Traversée' }, 'setup sans accents');
eq(J.parseSetup('zone 61.8-79 / absorption'), { level: 'Zone 61,8–79', conf: 'Absorption' }, 'zone écrite au point et au tiret');
eq(J.parseSetup('Hors setup'), { level: 'Hors setup', conf: null }, 'hors setup');
eq(J.parseSetup('Cassure de range'), { level: null, conf: null }, 'setup inconnu');
eq(J.setupText({ level: 'POC', conf: 'Rejet' }), 'POC · Rejet', 'texte du setup');
eq(J.setupText({ level: 'POC', conf: null }), '', 'setup incomplet refusé pour une prise');
eq(J.setupText({ level: 'POC', conf: null }, true), 'POC', 'setup partiel accepté pour un refus');
eq(J.setupText({ level: null, conf: null, setupRaw: 'Cassure de range' }), 'Cassure de range', 'setup brut conservé');
eq(J.shortSetup('Nœud faible volume · Absorption'), 'NFV · abs.', 'abréviation');

section('Brouillon déposé par le desk Stratégie');
const fd = J.fromDraft(J.blankForm(), { kind: 'pris', side: 'short', setup: 'Bande VWAP · Rejet' });
eq([fd.kind, fd.side, fd.level, fd.conf, fd.qty], ['pris', 'short', 'Bande VWAP', 'Rejet', 1], 'brouillon pris');
const fr = J.fromDraft(J.blankForm(), { kind: 'refus', side: 'long', stage: 'vwap', entry: 20000 });
eq([fr.kind, fr.side, fr.entry, fr.stage], ['refus', null, null, 'vwap'], 'un brouillon de refus perd son sens et ses prix');
const fx = J.fromDraft(J.blankForm(), { kind: 'pris', entry: '20 012,25', setup: 'Range' });
eq([fx.entry, fx.setupRaw, fx.level], [20012.25, 'Range', null], 'prix en texte et setup inconnu');
eq(J.fromDraft(J.blankForm(), null).kind, 'pris', 'brouillon absent');

section('Validation avant scellement');
const good = { kind: 'pris', side: 'long', level: 'Pivot', conf: 'Rejet', entry: 20000, stop: 19990, target: 20020, qty: 1, conviction: 3, plan: true };
eq(J.validate(good), [], 'décision complète');
ok(J.validate(Object.assign({}, good, { stop: 20010 })).some(e => /sous l’entrée/.test(e)), 'stop au-dessus en long');
ok(J.validate(Object.assign({}, good, { side: 'short' })).some(e => /au-dessus de l’entrée/.test(e)), 'stop au-dessous en short');
ok(J.validate(Object.assign({}, good, { target: 19995 })).some(e => /objectif/.test(e)), 'objectif du mauvais côté');
eq(J.validate(Object.assign({}, good, { target: null })), [], 'objectif facultatif');
ok(J.validate(Object.assign({}, good, { qty: 1.5 })).length === 1, 'quantité entière');
ok(J.validate(Object.assign({}, good, { conviction: null })).some(e => /conviction/.test(e)), 'conviction obligatoire');
ok(J.validate(Object.assign({}, good, { plan: null })).some(e => /plan/.test(e)), 'plan obligatoire');
ok(J.validate(Object.assign({}, good, { conf: null })).some(e => /setup/.test(e)), 'setup obligatoire');
eq(J.validate(Object.assign({}, good, { level: 'Hors setup', conf: null })), [], 'hors setup accepté');
ok(J.validate({ kind: 'refus' }).length === 1, 'refus sans étape');
eq(J.validate({ kind: 'refus', stage: 'macro' }), [], 'refus complet');

section('Entrée scellée');
const now = Date.UTC(2026, 9, 9, 10, 0, 30, 500); // vendredi 9 octobre 2026, 12:00:30 à Paris
const ent = J.buildEntry(Object.assign({ emotion: 'calme', note: '  rejet net  ' }, good), { now, pv: 2, comm: 1.24, instrument: 'MNQ' });
eq([ent.kind, ent.status, ent.at, ent.writtenAt, ent.setup, ent.pv, ent.comm, ent.note, ent.instrument], ['pris', 'ouvert', now, now, 'Pivot · Rejet', 2, 1.24, 'rejet net', 'MNQ'], 'une prise s’inscrit ouverte, avec sa valeur du point et sa commission');
const ref = J.buildEntry({ kind: 'refus', stage: 'biais', side: 'long', entry: 1, qty: 3, level: 'POC', conf: null, note: '' }, { now, pv: 2, comm: 1.24, instrument: 'MNQ' });
ok(!('side' in ref) && !('entry' in ref) && !('qty' in ref) && !('stop' in ref) && !('pnl' in ref), 'un refus ne porte ni sens ni mise');
eq([ref.kind, ref.stage, ref.setup], ['refus', 'biais', 'POC'], 'champs du refus');

section('Clôture');
const open = Object.assign({ id: 'x' }, ent);
ok(J.validateClose(open, { exit: null, fin: 'stop' }).length === 1, 'sortie manquante');
ok(J.validateClose(open, { exit: 20020, fin: 'nulle part' }).length === 1, 'fin inconnue');
ok(J.validateClose(Object.assign({}, open, { status: 'clos' }), { exit: 1, fin: 'stop' }).length === 1, 'déjà close');
ok(J.validateClose({ kind: 'refus' }, { exit: 1, fin: 'stop' }).length === 1, 'un refus ne se clôt pas');
const patch = J.closePatch(open, { exit: 20020, fin: 'objectif', apres: ' bien géré ' }, now + 3600e3, {});
eq([patch.status, patch.fin, patch.exit, patch.pnl, patch.closedAt, patch.apres], ['clos', 'objectif', 20020, 38.76, now + 3600e3, 'bien géré'], 'patch de clôture');
near(patch.r, 1.938, E, 'R de clôture');
ok(!('side' in patch) && !('entry' in patch) && !('stop' in patch) && !('conviction' in patch) && !('plan' in patch), 'la clôture ne touche aucun champ de décision');
const legacy = J.closePatch({ kind: 'pris', side: 'long', entry: 100, stop: 95, qty: 2 }, { exit: 110, fin: 'manuel' }, now, { pv: 20, comm: 4 });
eq([legacy.pnl, legacy.pv, legacy.comm], [392, 20, 4], 'entrée sans valeur du point : réglages au moment de la clôture');
near(J.closePatch(open, { exit: 20000.25, fin: 'manuel' }, now, {}).pnl, -0.74, E, 'P&L arrondi au cent');

section('Temps et périodes (Europe/Paris)');
const TZ = 'Europe/Paris';
eq(J.dateIn(now, TZ) + ' ' + J.timeIn(now, TZ), '09/10 12:00', 'date et heure à Paris');
eq(J.isoDay(Date.UTC(2026, 9, 8, 22, 10), TZ), '2026-10-09', 'après minuit à Paris, jour suivant');
ok(J.inPeriod(Date.UTC(2026, 9, 8, 22, 10), 'jour', now, TZ), 'jour : 00:10 à Paris');
ok(!J.inPeriod(Date.UTC(2026, 9, 8, 21, 50), 'jour', now, TZ), 'jour : 23:50 la veille');
ok(J.inPeriod(Date.UTC(2026, 9, 4, 22, 30), 'semaine', now, TZ), 'semaine : lundi 00:30');
ok(!J.inPeriod(Date.UTC(2026, 9, 4, 21, 30), 'semaine', now, TZ), 'semaine : dimanche 23:30');
ok(J.inPeriod(Date.UTC(2020, 0, 1), 'tout', now, TZ), 'tout');
eq(J.atFromTime('11:45', now, TZ), Date.UTC(2026, 9, 9, 9, 45, 0, 0), 'heure de décision saisie');
ok(isNaN(J.atFromTime('25:00', now, TZ)) && isNaN(J.atFromTime('midi', now, TZ)), 'heure illisible');
ok(J.atFromTime('12:30', now, TZ) > now, 'heure future détectée');
eq(J.lateMinutes({ at: now - 20 * 60000, writtenAt: now }), 20, 'écart d’inscription');

section('Statistiques sur un échantillon de référence');
// MNQ, pv 2, commission 1,24. Ordre de clôture : t1, t3, t2, t4, t5.
const base = Date.UTC(2026, 9, 5, 7, 0); // lundi 5 octobre 2026, 09:00 à Paris
const mk = (i, o) => Object.assign({ id: 't' + i, kind: 'pris', status: 'clos', pv: 2, comm: 1.24, instrument: 'MNQ' }, o);
const rows = [
  mk(1, { side: 'long', entry: 20000, stop: 19990, qty: 1, exit: 20020, at: base, closedAt: base + 1, plan: true, emotion: 'calme', conviction: 4, setup: 'Bande VWAP · Rejet' }),
  mk(2, { side: 'short', entry: 20100, stop: 20110, qty: 2, exit: 20110, at: base + 2 * 3600e3, closedAt: base + 3, plan: false, emotion: 'revanche', conviction: 2, setup: 'Pivot · Absorption' }),
  mk(3, { side: 'long', entry: 20050, stop: 20040, qty: 1, exit: 20045, at: base + 864e5, closedAt: base + 2, plan: true, emotion: 'calme', conviction: 3, setup: 'Bande VWAP · Rejet' }),
  mk(4, { side: 'long', entry: 20000, stop: 19980, qty: 1, exit: 19980, at: base + 2 * 864e5, closedAt: base + 4, plan: true, emotion: 'FOMO', conviction: 5, setup: 'POC · Traversée' }),
  mk(5, { side: 'short', entry: 20200, stop: 20212, qty: 1, exit: 20176, at: base + 2 * 864e5 + 3600e3, closedAt: base + 5, plan: false, emotion: 'calme', conviction: 4, setup: 'Pivot · Absorption' }),
  { id: 'o1', kind: 'pris', status: 'ouvert', side: 'long', entry: 1, stop: 0.5, qty: 1, at: base + 3 * 864e5 },
  { id: 'r1', kind: 'refus', stage: 'vwap', cf: 'objectif', at: base + 600e3 },
  { id: 'r2', kind: 'refus', stage: 'biais', at: base + 700e3 },
  { id: 'r3', kind: 'refus', stage: 'vwap', cf: 'stop', at: base + 800e3 }
];
rows.forEach(r => { if (r.status === 'clos') { r.pnl = J.round(J.pnl(r), 2); r.r = J.rMultiple(r, r.pnl); } });
eq(rows.slice(0, 5).map(r => r.pnl), [38.76, -42.48, -11.24, -41.24, 46.76], 'P&L de l’échantillon (Python)');
const st = J.stats(rows, TZ);
eq([st.n, st.nTaken, st.nClosed, st.nOpen, st.nRefus], [9, 6, 5, 1, 3], 'comptes');
near(st.refusShare, 3 / 9, E, 'part des refus');
eq([st.wins, st.losses, st.flats], [2, 3, 0], 'gagnantes, perdantes, nulles');
near(st.winRate, 0.4, E, 'taux de réussite');
near(st.wilson.lo, 0.11762077423264783, 1e-12, 'Wilson bas (2/5)');
near(st.wilson.hi, 0.769275718723987, 1e-12, 'Wilson haut (2/5)');
const w38 = J.wilson(3, 8);
near(w38.lo, 0.13684428582359742, 1e-12, 'Wilson bas (3/8)');
near(w38.hi, 0.6942576053973727, 1e-12, 'Wilson haut (3/8)');
near(st.expR, 0.24626666666666663, 1e-12, 'espérance en R');
near(st.sdR, 1.561670533613142, 1e-12, 'écart-type des R');
near(st.ciR, 1.368839423666177, 1e-12, 'demi-largeur de l’IC à 95 %');
near(st.net, -9.44, 1e-12, 'P&L net');
near(st.expUsd, -1.888, 1e-12, 'espérance en dollars');
near(st.profitFactor, 0.9005897219882054, 1e-12, 'facteur de profit');
near(st.avgWinR, 1.9431666666666665, 1e-12, 'gain moyen en R');
near(st.avgLossR, 0.885, 1e-12, 'perte moyenne en R');
near(st.payoff, 2.1956685499058377, 1e-12, 'payoff');
near(st.pEq, 0.3129235665036243, 1e-12, 'taux d’équilibre 1/(1 + b)');
near(st.nullR, -0.053733333333333334, 1e-12, 'loi nulle −c/L moyenne');
eq(st.equity.map(v => J.round(v, 2)), [38.76, 27.52, -14.96, -56.2, -9.44], 'courbe de capital, ordre de clôture');
eq(st.equityPlan.map(v => J.round(v, 2)), [38.76, 27.52, 27.52, -13.72, -13.72], 'courbe du plan respecté seul');
near(st.maxDD, 94.96, 1e-12, 'creux maximal');
eq(st.streaks, { win: 1, loss: 3 }, 'plus longues séries');
eq(st.activeDays, 3, 'séances actives');
near(st.plan.ok.expR, 0.11499999999999992, 1e-12, 'espérance plan respecté');
near(st.plan.no.expR, 0.4431666666666667, 1e-12, 'espérance plan enfreint');
near(st.plan.gapR, 0.3281666666666668, 1e-12, 'écart par entorse');
near(st.plan.lostR, -0.6563333333333335, 1e-12, 'R perdus (négatif : gagnés ici)');
near(st.plan.usd, 4.28, 1e-12, 'P&L hors plan');
eq(st.plan.nUnknown, 0, 'aucun plan non dit');
const calme = st.byEmotion.find(g => g.key === 'calme');
eq([st.byEmotion[0].key, calme.n, calme.wins], ['calme', 3, 2], 'groupe calme en tête');
near(calme.expR, 1.108111111111111, 1e-12, 'espérance du groupe calme');
near(calme.ciR, 1.6366892563945412, 1e-12, 'IC du groupe calme');
near(calme.sum, 74.28, 1e-12, 'P&L du groupe calme');
eq(J.read(calme), 'indistinct', 'lecture du groupe calme');
eq(J.read({ n: 1, ciR: NaN }), 'trop peu', 'lecture à n = 1');
eq(J.read({ n: 10, expR: 0.5, ciR: 0.2 }), 'au-dessus de 0', 'lecture positive');
eq(J.read({ n: 10, expR: -0.5, ciR: 0.2 }), 'sous 0', 'lecture négative');
eq(st.byHour.map(g => [g.key, g.n]), [[9, 3], [10, 1], [11, 1]], 'par heure de Paris');
eq(st.byConviction.map(g => g.key), [2, 3, 4, 5], 'conviction triée');
eq(st.bySetup.map(g => [g.key, g.n]), [['Bande VWAP · Rejet', 2], ['Pivot · Absorption', 2], ['POC · Traversée', 1]], 'par setup');
eq(st.byStage, [{ key: 'biais', n: 1 }, { key: 'vwap', n: 2 }], 'refus par étape, dans l’ordre des étapes');
eq(st.contingency, { prisG: 2, prisP: 3, refusG: 1, refusP: 1, refusN: 0, refusX: 1 }, 'table de contingence');
eq(st.calibration.verdict, 'trop peu', 'calibration : une seule décision à faible conviction');
const flat = Array.from({ length: 31 }, (_, i) => ({ kind: 'pris', status: 'clos', pnl: i % 2 ? 1 : -1, r: i % 2 ? 1 : -1, conviction: 3, at: base + i }));
eq(J.calibration(flat).verdict, 'constante', 'conviction constante sur plus de 30 décisions');
const cal = Array.from({ length: 40 }, (_, i) => ({ conviction: i < 20 ? 5 : 1, r: i < 20 ? 1 + (i % 2) * 0.1 : -1 - (i % 2) * 0.1, pnl: i < 20 ? 10 : -10 }));
eq(J.calibration(cal).verdict, 'calibrée', 'conviction calibrée');
eq(J.streaks([1, 1, 0, -1, -1, -1, 2]), { win: 2, loss: 3 }, 'un résultat nul coupe les séries');
const empty = J.stats([], TZ);
ok(empty.nClosed === 0 && isNaN(empty.winRate) && isNaN(empty.expR) && isNaN(empty.refusShare), 'journal vide : rien d’inventé');
const pf = J.stats([mk(9, { side: 'long', entry: 10, stop: 9, qty: 1, exit: 12, pnl: 2.76, r: 1.38, at: base })], TZ);
eq(pf.profitFactor, Infinity, 'facteur de profit sans perte : infini');
ok(isNaN(pf.payoff) && isNaN(pf.pEq), 'équilibre indéfini sans perte');

section('Mur des 619 et rythme');
const pc = J.pace(10, 4);
eq([pc.rate, pc.left, pc.sessions], [2.5, 609, 244], 'rythme : 2,5 décisions par séance active');
near(pc.years, 244 / 252, E, 'années restantes à 252 séances');
eq(J.pace(0, 0), null, 'pas de rythme sans décision close');
eq(J.pace(700, 100).left, 0, 'mur franchi');

section('Export CSV');
const csvRows = [
  Object.assign({}, rows[0], { note: 'rejet; puis "retour"', apres: '=SOMME(A1)', writtenAt: base + 20 * 60000 }),
  rows[6]
];
const csv = J.toCsv(csvRows, TZ).split('\n');
eq(csv[0], J.CSV_COLS.join(';'), 'en-tête');
const c1 = csv[1].split(';');
eq(c1.slice(0, 16), ['2026-10-05', '09:00', 'pris', 'clos', 'long', 'MNQ', 'Bande VWAP · Rejet', '', '20000', '19990', '', '1', '20020', '', '38,76', '1,938'], 'ligne prise, virgule décimale');
ok(csv[1].indexOf('"rejet; puis ""retour"""') >= 0, 'champ protégé : point-virgule et guillemets');
ok(csv[1].endsWith(';\'=SOMME(A1)'), 'formule neutralisée');
ok(csv[1].indexOf(';20;') >= 0, 'écart d’inscription en minutes');
const c2 = csv[2].split(';');
eq([c2[2], c2[3], c2[4], c2[7], c2[8], c2[11], c2[19]], ['refus', '', '', 'vwap', '', '', 'objectif'], 'ligne de refus sans sens ni mise');
eq(J.csvCell(-1.5), '-1,5', 'nombre négatif');
eq(J.csvCell(NaN), '', 'NaN exporté vide');

section('Typographie');
eq(J.fr('Wilson : x ; y ? « z »'), 'Wilson : x ; y ? « z »', 'espaces insécables');

section('Sources ALP nº 3, contrôlées contre le texte et le code du dépôt');
const SP = path.join(__dirname, '..', '..');
const p08 = fs.readFileSync(path.join(require('./harness').ALP3, 'p08.txt'), 'utf8');
ok(/Huitième partie/.test(p08) && /Table 14/.test(p08), 'p08 est la partie VIII, table 14');
ok(p08.indexOf('619 décisions, soit 1,2 an à deux décisions par jour') >= 0, '619 décisions, 1,2 an à deux par jour (partie VIII)');
ok(/\| 0,100 \| 619 \|/.test(p08), 'table 14 : Sharpe 0,100 → 619');
eq(J.WALL, 619, 'mur du desk');
eq(Math.round(J.WALL / J.WALL_PER_SESSION / J.SESSIONS_PER_YEAR * 10) / 10, 1.2, '619 / 2 / 252 = 1,2 an');
const rep10 = fs.readFileSync('/home/user/Alp-1/alp1/report10.py', 'utf8');
ok(/SESSIONS_PER_YEAR = 252/.test(rep10), '252 séances par an dans alp1/report10.py');
const p04 = fs.readFileSync(path.join(require('./harness').ALP3, 'p04.txt'), 'utf8');
ok(/Quatrième partie/.test(p04) && /Table 9 — Ce qu’un journal de décision doit porter, et de quel côté de la frontière temporelle/.test(p04), 'frontière temporelle : partie IV, table 9');
ok(/Une abstention qui porte une direction ou une mise non nulle a été complétée après coup/.test(p04), 'un refus sans sens ni mise (partie IV)');
ok(/Issue contrefactuelle des refus \| après l’issue/.test(p04), 'issue contrefactuelle : champ d’après l’issue');
const p11 = fs.readFileSync(path.join(require('./harness').ALP3, 'p11.txt'), 'utf8');
ok(/Onzième partie/.test(p11) && /À dérive nulle, les quatre droites valent exactement −c\/L/.test(p11), 'loi nulle −c/L (partie XI)');
const p03 = fs.readFileSync(path.join(require('./harness').ALP3, 'p03.txt'), 'utf8');
ok(/Troisième partie/.test(p03), 'partie III citée pour le filtre');
const jpy = fs.readFileSync('/home/user/Alp-1/alp1/journal.py', 'utf8');
ok(/conviction constante : le test de calibration est sans objet/.test(jpy) && /journal\.n_taken > 30/.test(jpy), 'audit de la conviction constante au-delà de 30 (alp1/journal.py)');

section('Le desk n’écrit aucune couleur et aucun chiffre de marché');
const src = fs.readFileSync(path.join(__dirname, '..', 'src', 'desks', 'journal.js'), 'utf8');
ok(!/#[0-9a-fA-F]{3,8}\b/.test(src.replace(/&#\d+;/g, '')), 'aucune couleur en dur');
ok(!/rgba?\(/.test(src), 'aucune couleur rgba en dur');
ok(!/localStorage|sessionStorage/.test(src), 'sauvegarde par T.store et T.journal seulement');
const keys = (src.match(/'journal:[a-z]+'/g) || []);
ok(keys.length >= 4 && keys.every(k => /^'journal:/.test(k)), 'clés préfixées par l’id du desk');

console.log(passes + ' réussis, ' + fails + ' échecs');
process.exit(fails ? 1 : 0);
