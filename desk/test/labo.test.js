// Tests du desk Labo (parties pures de T.lib.labo) : clés de cache, registre des essais, borne du document de
// résultats, format de quant:lastBacktest, règles d’ouverture hors échantillon, transitions d’état.
// node test/labo.test.js
'use strict';
const { T, lib: LB } = require('./harness')(['quant', 'perf', 'risk', 'labo-engine', 'labo-stats', 'donnees', 'labo']);
const LE = T.lib.laboEngine, LS = T.lib.laboStats;
let pass = 0, fail = 0;
function ok(c, m) { if (c) pass++; else { fail++; console.log('ÉCHEC : ' + m); } }
function eq(a, b, m) { ok(JSON.stringify(a) === JSON.stringify(b), m + ' — attendu ' + JSON.stringify(b) + ', obtenu ' + JSON.stringify(a)); }
function near(a, b, tol, m) { ok(Math.abs(a - b) <= tol, m + ' — attendu ' + b + ', obtenu ' + a); }
function throws(f, m) { try { f(); ok(false, m + ' (aucune erreur)'); } catch (e) { ok(true, m); } }
function seq(seed) { return T.rng(seed); }

/* ---------- 0. Desk ---------- */
const desk = T.desks().find(d => d.id === 'labo');
ok(!!desk, 'desk labo enregistré');
eq([desk.label, desk.glyph, desk.group, desk.order], ['Labo de stratégie', 'L', 'Recherche', 45], 'identité du desk');
eq(desk.tabs.map(t => t.id), ['concevoir', 'tester', 'valider', 'verdict', 'suivre'], 'onglets');

/* ---------- 1. Identifiants, octets, compaction ---------- */
const r1 = seq(7);
for (let i = 0; i < 50; i++) { const s = LB.newSid(1767225600000 + i * 999, r1); ok(LB.SID_RE.test(s), 'sid conforme ' + s); }
eq(LB.versionId('sabcdef12', 3), 'sabcdef12_v3', 'id de version');
eq([LB.byteLength('abc'), LB.byteLength('é'), LB.byteLength('€'), LB.byteLength('😀'), LB.byteLength('’')], [3, 2, 3, 4, 3], 'octets UTF-8');
const cp = LB.compact({ t: 1767570540000, x: 0.123456789123, n: NaN, i: Infinity, arr: new Float64Array([1.5, 2.25]), f: function () {}, u: undefined, k: -19986.25 });
eq(cp.t, 1767570540000, 'compact : horodatage exact');
eq([cp.x, cp.n, cp.i, cp.arr, 'f' in cp, 'u' in cp, cp.k], [0.1234568, null, null, [1.5, 2.25], false, false, -19986.25], 'compact : nombres, NaN, tableaux typés, fonctions');

/* ---------- 2. Clés de cache ---------- */
const base = { configHash: 'h0123456789abcdef', fingerprint: 'MNQ|2026-01-05|2026-03-27|82800|2044627750', sel: { from: '2026-01-05', to: '2026-03-02' }, op: 'tester' };
const k0 = LB.cacheKey(base);
eq(k0, LB.cacheKey(JSON.parse(JSON.stringify(base))), 'clé de cache stable');
ok(LB.cacheKey(Object.assign({}, base, { op: 'valider' })) !== k0, 'la clé dépend de l’op');
ok(LB.cacheKey(Object.assign({}, base, { fingerprint: 'MNQ|x' })) !== k0, 'la clé dépend de l’empreinte');
ok(LB.cacheKey(Object.assign({}, base, { sel: { from: '2026-01-05', to: '2026-03-03' } })) !== k0, 'la clé dépend de la sélection');
ok(LB.cacheKey(Object.assign({}, base, { configHash: 'h1' })) !== k0, 'la clé dépend du configHash');
ok(LB.cacheMatch({ key: k0 }, base) && !LB.cacheMatch({ key: k0 }, Object.assign({}, base, { op: 'x' })) && !LB.cacheMatch(null, base), 'cacheMatch');
const rid = LB.resultId('sabcdefg_v2', base.fingerprint, 'tester');
ok(/^sabcdefg_v2__[0-9a-z]{7}__tester$/.test(rid), 'identifiant de résultat ' + rid);
eq(rid.split('__')[1], T.lib.donnees.shortPrint(base.fingerprint), 'empreinte courte = T.lib.donnees.shortPrint');
const v1 = LB.variantKey({ h: 'hx', s: { tick: 0.25, pointValue: 2, commissionRT: 1.24 } }), v2 = LB.variantKey({ s: { commissionRT: 1.24, pointValue: 2, tick: 0.25 }, h: 'hx' });
eq(v1, v2, 'variante insensible à l’ordre des clés');
ok(LB.variantKey({ h: 'hx', s: { tick: 0.25, pointValue: 2, commissionRT: 2.5 } }) !== v1, 'variante sensible aux coûts');
// configHash ignore les coûts : la clé de cache ne bouge pas, la variante si (§2.8 + coûts).
const tpl = LS.fromTemplate('vwap-rejet', 'stestabc1');
const tplCost = JSON.parse(JSON.stringify(tpl)); tplCost.costs.commissionRT = 3;
eq(LS.configHash(tpl), LS.configHash(tplCost), 'configHash insensible à la commission');
ok(LS.hash(tpl, 1.24) !== LS.hash(tplCost, 1.24), 'le hachage complet voit la commission (variante)');

/* ---------- 3. Registre des essais ---------- */
const reg = [];
const o1 = { sid: 'sstratA01', root: 'sstratA01', version: 1, instrument: 'MNQ', fingerprint: 'fp1', from: '2025-01-02', to: '2025-06-30', op: 'run', hashes: ['hA'], sr: [0.05] };
let w = LB.essaisToWrite(reg, o1, 1000, seq(1));
eq(w.length, 1, 'premier lancement : un essai');
eq([w[0].hashes, w[0].sr, w[0].instrument, w[0].op, w[0].from, w[0].to], [['hA'], [0.05], 'MNQ', 'run', '2025-01-02', '2025-06-30'], 'contenu de l’essai');
ok(/^e[0-9a-z]+$/.test(w[0].id), 'id d’essai e + base36');
reg.push.apply(reg, w);
eq(LB.essaisToWrite(reg, o1, 2000, seq(2)).length, 0, 'relance identique : aucun essai');
// stratégie dupliquée (autre sid, même configuration) et jeu réimporté (autre empreinte) : aucun nouvel essai.
eq(LB.essaisToWrite(reg, Object.assign({}, o1, { sid: 'sdupli001', fingerprint: 'fp2' }), 3000, seq(3)).length, 0, 'duplication et réimport n’ajoutent rien');
eq(LS.trials(reg, 'MNQ', '2025-03-01', '2025-04-01').N, 1, 'N hérité par la période recoupée');
// deux essais concurrents sur la même période comptent les deux.
w = LB.essaisToWrite(reg, Object.assign({}, o1, { sid: 'sstratB01', root: 'sstratB01', hashes: ['hB', 'hA', 'hB'], sr: [0.1, 0.05, 0.1] }), 4000, seq(4));
eq(w.length === 1 && w[0].hashes, ['hB'], 'seuls les configHash nouveaux, sans doublon');
eq(w[0].sr, [0.1], 'Sharpe aligné sur le hash');
reg.push.apply(reg, w);
eq(LS.trials(reg, 'MNQ', '2025-01-02', '2025-06-30').N, 2, 'deux essais concurrents comptent les deux');
eq(LS.trials(reg, 'NQ', '2025-01-02', '2025-06-30').N, 0, 'autre instrument : rien');
eq(LS.trials(reg, 'MNQ', '2025-07-01', '2025-12-31').N, 0, 'période disjointe : rien');
// un balayage de 1 200 configurations se range en trois documents de 500 au plus.
const many = []; for (let i = 0; i < 1200; i++) many.push('hS' + i);
w = LB.essaisToWrite(reg, Object.assign({}, o1, { op: 'sweep', hashes: many, sr: many.map((_, i) => i / 1e4) }), 5000, seq(5));
eq(w.map(d => d.hashes.length), [500, 500, 200], 'essais coupés par 500');
eq(w[2].sr[199], 0.1199, 'Sharpe du dernier hash');
reg.push.apply(reg, w);
eq(LS.trials(reg, 'MNQ', '2025-01-02', '2025-06-30').N, 1202, 'N compte toutes les configurations');
// lignée : migration incomplète bloque « prête ».
const lc = LB.lineageCheck({ t: 1, v: { sources: ['a'], migreLe: 10, comptes: { 'labo/essais': 5, 'labo/oos': 1 } } }, { 'labo/essais': 4, 'labo/oos': 1 });
eq([lc.blocked, lc.missing.length, lc.missing[0].coll], [true, 1, 'labo/essais'], 'migration incomplète détectée');
ok(/labo\/essais 4 sur 5/.test(lc.text), 'texte de la migration incomplète');
eq(LB.lineageCheck(null, {}).blocked, false, 'sans lignée : rien de bloqué');
eq(LB.lineageCheck({ v: { comptes: { 'labo/essais': 5 } } }, { 'labo/essais': 7 }).blocked, false, 'compte supérieur : rien de bloqué');

/* ---------- 4. Hors échantillon ---------- */
const keys = []; for (let i = 0; i < 60; i++) keys.push('2026-' + String(1 + Math.floor(i / 28)).padStart(2, '0') + '-' + String(1 + i % 28).padStart(2, '0'));
eq(LB.oosProposal(keys), keys[42], 'proposition : 30 % des séances après la coupure');
eq(LB.oosProposal(keys.slice().reverse()), keys[42], 'proposition indépendante de l’ordre');
eq(LB.oosProposal(['2026-01-02']), null, 'une séance : pas de proposition');
const sp = LB.splitSel(keys, keys[42]);
eq([sp.is.n, sp.oos.n, sp.is.to, sp.oos.from], [42, 18, keys[41], keys[42]], 'partage échantillon / hors échantillon');
eq(LB.splitSel(keys, null).oos.n, 0, 'sans coupure : tout en échantillon');
const op1 = { id: 'o1', root: 'sroot0001', sid: 'sroot0001', version: 2, instrument: 'MNQ', from: '2026-03-01', to: '2026-03-31', at: 100 };
let oo = LB.oosOpening([], { root: 'sroot0001', instrument: 'MNQ', from: '2026-03-01', to: '2026-03-31' });
eq([oo.first, oo.prior, oo.total], [true, null, 0], 'première ouverture');
oo = LB.oosOpening([op1], { root: 'sroot0001', instrument: 'MNQ', from: '2026-03-15', to: '2026-04-10' });
eq([oo.first, oo.prior && oo.prior.version, oo.lineage, oo.total], [false, 2, 1, 1], 'seconde ouverture de la lignée : déjà vu (version 2)');
oo = LB.oosOpening([op1], { root: 'sautre001', instrument: 'MNQ', from: '2026-03-01', to: '2026-03-31' });
eq([oo.first, oo.total], [true, 1], 'autre lignée : première, mais comptée au total de la période');
eq(LB.oosOpening([op1], { root: 'sroot0001', instrument: 'NQ', from: '2026-03-01', to: '2026-03-31' }).first, true, 'autre instrument : première');
eq(LB.oosOpening([op1], { root: 'sroot0001', instrument: 'MNQ', from: '2026-04-01', to: '2026-04-30' }).first, true, 'période disjointe : première');
eq(LB.oosOpening([op1], { root: 'sroot0001', instrument: 'MNQ', from: '2026-03-01', to: '2026-03-31', self: 'o1' }).first, true, 'une ouverture ne se compte pas contre elle-même');
const op2 = Object.assign({}, op1, { id: 'o2', version: 3, at: 200 });
eq(LB.oosOpening([op2, op1], { root: 'sroot0001', instrument: 'MNQ', from: '2026-03-01', to: '2026-03-31', self: 'o2', before: 200 }).prior.version, 2, 'la plus ancienne ouverture fait foi');
eq(LB.oosOpening([op1, Object.assign({}, op2, { deleted: true })], { root: 'sroot0001', instrument: 'MNQ', from: '2026-03-01', to: '2026-03-31' }).lineage, 1, 'ouverture supprimée ignorée');
// une stratégie dupliquée garde son root : elle hérite des ouvertures.
const dupRoot = LB.planDuplicate(LS.fromTemplate('rsi-retour', 'sroot0001'), { sid: 'sdupli777', now: 5 }).doc;
eq([dupRoot.sid, dupRoot.root], ['sdupli777', 'sroot0001'], 'duplication : nouveau sid, même root');
eq(LB.oosOpening([op1], { root: dupRoot.root, instrument: 'MNQ', from: '2026-03-01', to: '2026-03-31' }).first, false, 'la copie hérite des ouvertures de la lignée');
eq(LB.canSetOos(null, [], 'MNQ', '2026-03-02').ok, true, 'coupure choisie avant tout lancement');
eq(LB.canSetOos({ oosFrom: '2026-02-01' }, [], 'MNQ', '2026-03-02').ok, false, 'coupure posée une fois');
eq(LB.canSetOos(null, [{ instrument: 'MNQ', hashes: ['h'] }], 'MNQ', '2026-03-02').ok, false, 'jamais après un lancement réel');
eq(LB.canSetOos(null, [{ instrument: 'NQ', hashes: ['h'] }], 'MNQ', '2026-03-02').ok, true, 'un lancement sur un autre instrument ne bloque pas');
eq(LB.canSetOos(null, [], 'MNQ', '02/03/2026').ok, false, 'clé invalide refusée');
eq(LB.canOpenOos({ status: 'brouillon', oosN: 10 }).ok, false, 'brouillon : pas d’ouverture');
eq(LB.canOpenOos({ status: 'alteree', oosN: 10 }).ok, false, 'altérée : pas d’ouverture');
eq(LB.canOpenOos({ status: 'scellee', oosN: 0 }).ok, false, 'sans séance hors échantillon : pas d’ouverture');
eq(LB.canOpenOos({ status: 'scellee', oosN: 10, opened: true }).ok, false, 'déjà ouverte par cette version');
eq(LB.canOpenOos({ status: 'scellee', oosN: 10 }).ok, true, 'scellée, non altérée : ouverture possible');

/* ---------- 5. Transitions d’état : brouillon → scellée → altérée ---------- */
const draft = LS.fromTemplate('or-cassure', 'sstate001', 1000);
eq(LB.statusOf(draft), 'brouillon', 'gabarit : brouillon');
eq(LB.statusOf(null), null, 'aucune version : null');
let ps = LB.planSave(draft, { stored: null, now: 2000 });
eq([ps.id, ps.created, ps.doc.status, ps.doc.hash, ps.doc.u], ['sstate001_v1', true, 'brouillon', null, 2000], 'premier enregistrement');
const stored1 = ps.doc;
let sl = LB.planSeal(stored1, { stored: stored1, commissionRT: 1.24, oosFrom: '2026-03-02', now: 3000 });
eq([sl.ok, /hypothèse/.test(sl.why)], [false, true], 'sceller exige l’hypothèse');
const withHyp = Object.assign(JSON.parse(JSON.stringify(stored1)), { hypothesis: 'La cassure du range d’ouverture prolonge le mouvement du matin.' });
sl = LB.planSeal(withHyp, { stored: stored1, commissionRT: 1.24, oosFrom: null, now: 3000 });
eq([sl.ok, /coupure/.test(sl.why)], [false, true], 'sceller exige la coupure de l’instrument');
sl = LB.planSeal(withHyp, { stored: stored1, commissionRT: 1.24, oosFrom: '2026-03-02', now: 3000 });
ok(sl.ok && /^h[0-9a-f]{16}$/.test(sl.hash), 'scellement : hachage');
const sealed = sl.doc;
eq([sealed.id, sealed.status, sealed.sealedAt, sealed.costs.commissionRT], ['sstate001_v1', 'scellee', 3000, 1.24], 'version scellée, commission figée');
eq(LB.statusOf(sealed), 'scellee', 'hachage vérifié : scellée');
eq(LS.verifySeal(sealed).ok, true, 'verifySeal concorde');
const tampered = JSON.parse(JSON.stringify(sealed)); tampered.long.stop.buffer = 9;
eq(LB.statusOf(tampered), 'alteree', 'modification d’une version scellée : altérée');
const tampered2 = JSON.parse(JSON.stringify(sealed)); tampered2.costs.commissionRT = 0.5;
eq(LB.statusOf(tampered2), 'alteree', 'commission changée après scellement : altérée');
eq(LB.planSeal(withHyp, { stored: sealed, commissionRT: 1.24, oosFrom: '2026-03-02' }).ok, false, 'une version scellée ne se rescelle pas');
eq(LB.planSeal(sealed, { stored: sealed, commissionRT: 1.24, oosFrom: '2026-03-02' }).already, true, 'resceller à l’identique : déjà scellée');
// enregistrer une version scellée inchangée : rien ; modifiée : version 2 en brouillon.
ps = LB.planSave(sealed, { stored: sealed, now: 4000 });
eq([ps.unchanged, ps.doc, ps.id], [true, null, 'sstate001_v1'], 'version scellée inchangée : aucune écriture');
const edited = JSON.parse(JSON.stringify(sealed)); edited.long.target.value = 3; delete edited.params.rr;
ps = LB.planSave(edited, { stored: sealed, lists: [[sealed]], now: 5000 });
eq([ps.id, ps.doc.version, ps.doc.status, ps.doc.hash, ps.doc.sealedAt, ps.doc.parent, ps.doc.root, ps.doc.sid], ['sstate001_v2', 2, 'brouillon', null, null, 'sstate001_v1', 'sstate001', 'sstate001'], 'modifier une scellée crée la version suivante');
eq(sealed.status, 'scellee', 'la version scellée n’est pas touchée');
// le numéro suivant tient compte des registres (une version supprimée ne se réutilise pas).
eq(LB.nextVersion('sstate001', [sealed], [{ sid: 'sstate001', version: 4 }], [{ sid: 'sautre', version: 9 }]), 5, 'nextVersion lit stratégies, essais et ouvertures');
ps = LB.planSave(edited, { stored: sealed, lists: [[sealed], [{ sid: 'sstate001', version: 4 }]], now: 5000 });
eq(ps.id, 'sstate001_v5', 'modification après une version 4 connue des registres : version 5');
// un brouillon s’écrit à sa place.
const d2 = JSON.parse(JSON.stringify(stored1)); d2.name = 'Renommée';
ps = LB.planSave(d2, { stored: stored1, now: 6000 });
eq([ps.id, ps.created, ps.doc.name, ps.doc.createdAt], ['sstate001_v1', false, 'Renommée', stored1.createdAt], 'brouillon modifié en place');
// sans sid : un nouveau sid est posé.
const raw = { name: 'Sans identité', hypothesis: '', side: 'long', long: { trigger: { cross: 'up', a: { f: 'close' }, b: { f: 'vwap' } }, entry: { type: 'market' }, stop: { type: 'pts', value: 10 }, target: { type: 'r', value: 2 } } };
ps = LB.planSave(raw, { sid: 'snouveau01', now: 7000 });
eq([ps.id, ps.doc.sid, ps.doc.root, ps.doc.version], ['snouveau01_v1', 'snouveau01', 'snouveau01', 1], 'spec sans identité : nouveau sid');
throws(() => LB.planSave('{pas du json', {}), 'spec illisible refusée');
const nv = LB.planNewVersion(sealed, { lists: [[sealed]], now: 8000 }).doc;
eq([nv.id, nv.status, nv.parent], ['sstate001_v2', 'brouillon', 'sstate001_v1'], 'nouvelle version');

/* ---------- 6. Borne du document de résultats et trades ---------- */
const fakeTrades = []; const rr = seq(11);
for (let i = 0; i < 5000; i++) fakeTrades.push({ t: 1767570540000 + i * 60000, tx: 1767570600000 + i * 60000, side: rr() < 0.5 ? 1 : -1, r: (rr() - 0.5) * 4, pnl: (rr() - 0.5) * 40, fin: rr() < 0.5 ? 'stop' : 'objectif', key: '2026-01-05', mae: rr() * 3, mfe: rr() * 3, risk: 1 + rr() * 5, hour: Math.floor(rr() * 24), dow: 1 + Math.floor(rr() * 5) });
const tr = LB.tradeRows(fakeTrades);
eq([tr.rows.length, tr.omitted, tr.total], [3000, 2000, 5000], 'trades : les 3 000 derniers');
eq(tr.rows[2999][0], fakeTrades[4999].t, 'le dernier trade est gardé');
eq(tr.rows[0].length, 5, 'ligne [t, sens, r, pnl, fin]');
const bigDoc = { id: 'x', key: 'k', stats: { n: 5000, meanR: 0.01 }, trades: fakeTrades.map(t => [t.t, t.side, t.r, t.pnl, t.fin]), view: { eq: LB.eqOf(fakeTrades), maemfe: LB.maeMfe(fakeTrades, 5000), heat: LB.heat(fakeTrades), months: LB.months(fakeTrades) }, nulls: { random: { means: fakeTrades.slice(0, 200).map(t => t.r), p: 0.4 } } };
ok(LB.byteLength(JSON.stringify(bigDoc)) > 200000, 'document témoin au-delà de 200 Ko');
const fit = LB.fitDoc(bigDoc);
const fitBytes = LB.byteLength(JSON.stringify(fit));
ok(fitBytes <= 200000, 'document borné à 200 Ko (' + fitBytes + ')');
ok(fit.trades.length <= 3000, 'trades ≤ 3 000');
eq(fit.trades.length + fit.tradesOmitted, 5000, 'tradesOmitted complète le compte');
eq(fit.trades[fit.trades.length - 1][0], fakeTrades[4999].t, 'horodatages exacts après compaction');
eq([fit.key, fit.stats.n, fit.nulls.random.p], ['k', 5000, 0.4], 'clé, statistiques et lois nulles conservées');
const small = LB.fitDoc({ id: 'y', trades: [[1, 1, 0.5, 1, 'stop']] });
eq([small.trades.length, small.tradesOmitted], [1, undefined], 'petit document intact');
// document réel : run sur la marche synthétique, puis borne.
const lat = LE.lattice({ sessions: 30, seed: 3 });
const spec = LS.fromTemplate('vwap-rejet', 'sreal0001');
const run = LE.op('run', { bars: lat, spec: spec, values: {}, settings: { tick: 0.25, pointValue: 2, commissionRT: 1.24 }, seed: 1 });
ok(run.trades.length > 10, 'run de référence : des trades (' + run.trades.length + ')');
const rows = LB.tradeRows(run.trades).rows, realDoc = LB.fitDoc({ id: 'z', stats: run.stats, trades: rows, view: { eq: LB.eqOf(run.trades), heat: LB.heat(run.trades), maemfe: LB.maeMfe(run.trades), months: LB.months(run.trades) } });
ok(LB.byteLength(JSON.stringify(realDoc)) <= 200000 && realDoc.trades.length === run.trades.length, 'document réel complet sous la borne');
near(realDoc.stats.meanR, run.stats.meanR, 1e-6, 'meanR compacté fidèle');

/* ---------- 7. quant:lastBacktest ---------- */
const bt = LB.lastBacktest(tr.rows, { label: 'Rejet VWAP · v1 · synthétique', source: 'synth', total: 5000, at: 42 });
eq(Object.keys(bt).sort(), ['at', 'label', 'source', 'trades', 'truncated'], 'clés de quant:lastBacktest');
eq([bt.label, bt.at, bt.source, bt.trades.length, bt.truncated], ['Rejet VWAP · v1 · synthétique', 42, 'synth', 3000, 5000], 'format et troncature');
eq(Object.keys(bt.trades[0]).sort(), ['at', 'pnl', 'r', 'side'], 'champs d’un trade (format de quant.js)');
const lt = fakeTrades[4999];
eq(bt.trades[2999], { at: lt.t, pnl: Math.round(lt.pnl * 100) / 100, r: Math.round(lt.r * 10000) / 10000, side: lt.side > 0 ? 'long' : 'short' }, 'arrondis de quant.js');
const bt2 = LB.lastBacktest(run.trades, { label: 'x', source: 'csv' });
eq([bt2.trades.length, bt2.truncated], [run.trades.length, 0], 'liste complète : truncated = 0');
eq(bt2.trades[0].at, run.trades[0].t, 'trades du moteur acceptés');
const fromBt = T.lib.perf.fromBacktest(bt, 150);
eq(fromBt.length, 3000, 'le desk Métriques lit le format');
near(fromBt[10].pnl, bt.trades[10].pnl, 1e-12, 'Métriques relit le P&L');

/* ---------- 8. Vues pures ---------- */
eq(LB.gridValues(-3, -1, 0.5), [-3, -2.5, -2, -1.5, -1], 'grille de valeurs');
eq(LB.gridValues(0, 0.3, 0.1), [0, 0.1, 0.2, 0.3], 'grille sans dérive flottante');
eq(LB.gridValues(5, 1, 1), [5], 'grille inversée : une valeur');
const sw = LE.op('sweep', { bars: lat, spec: spec, settings: { tick: 0.25, pointValue: 2, commissionRT: 1.24 }, p1: 'bande', p2: 'marge', seed: 1 });
eq(sw.xs, LB.gridValues(spec.params.bande.min, spec.params.bande.max, spec.params.bande.step), 'grille identique à celle du moteur (p1)');
eq(sw.ys, LB.gridValues(spec.params.marge.min, spec.params.marge.max, spec.params.marge.step), 'grille identique à celle du moteur (p2)');
const opsV = LB.operandsOf(LS.resolve(spec, {}).long);
ok(opsV.some(o => o.f === 'vwap' && o.k === -2) && opsV.some(o => o.f === 'close') && opsV.every(o => typeof o === 'object'), 'opérandes de la règle VWAP');
eq(LB.operandsOf(LS.resolve(LS.fromTemplate('rsi-retour', 'sops00001'), {}).long).map(o => o.f), ['rsi'], 'opérandes de la règle RSI (constante exclue)');
const sk = LB.sankeyOf(run.counts, run.stats.byFin, run.stats.n);
const outSig = sk.links.filter(l => l.s === 'sig').reduce((a, l) => a + l.v, 0), outExe = sk.links.filter(l => l.s === 'exe').reduce((a, l) => a + l.v, 0);
eq(outSig, Math.max(run.counts.signals, run.stats.n), 'sankey : les signaux se conservent');
eq(outExe, run.stats.n, 'sankey : chaque exécuté a une sortie');
const eqc = LB.eqOf(run.trades);
near(eqc[eqc.length - 1][1], run.stats.net, 1e-6, 'équité : net final');
const uw = LB.underwater([[1, 10], [2, 5], [3, 12], [4, 2]]);
eq(uw.map(p => p[1]), [0, -5, 0, -10], 'sous l’eau');
eq(LB.downsample([1, 2, 3, 4, 5], 3), [1, 3, 5], 'sous-échantillonnage garde les bouts');
const mo = LB.months([{ key: '2026-01-05', r: 1, pnl: 10 }, { key: '2026-01-20', r: -1, pnl: -5 }, { key: '2026-02-02', r: 2, pnl: 20 }]);
eq(mo.map(m => [m.m, m.n, m.meanR, m.net]), [['2026-01', 2, 0, 5], ['2026-02', 1, 2, 20]], 'sous-périodes mensuelles');
const hm = LB.heat([{ hour: 9, dow: 1, r: 1 }, { hour: 9, dow: 1, r: 3 }, { hour: 14, dow: 3, r: -1 }]);
eq([hm.days, hm.hours, hm.mean, hm.n], [[1, 3], [9, 14], [[2, null], [null, -1]], [[2, 0], [0, 1]]], 'carte heure × jour');
const eg = LB.envelopeGap([1, -1, 2], { pess: -0.2, opt: 0.3, costR: 0.1 });
eq([eg.n, eg.cum, eg.where, eg.pess[3][1], eg.opt[3][1], eg.nul[3][1]], [3, 2, 'dessus', -0.6000000000000001, 0.8999999999999999, -0.30000000000000004], 'écart à l’enveloppe');

eq([LB.decOf([-3, -2.5, -1]), LB.decOf([0, 4, 8]), LB.decOf([0.25, 0.125]), LB.decOf([1 / 3])], [1, 0, 3, 3], 'décimales utiles d’une grille');
// carte 2D en blocs : chaque échantillon prend la cellule calculée la plus proche, la meilleure cellule reste repérée.
const nearestIdx = (a, v) => { let b = 0; for (let i = 1; i < a.length; i++) if (Math.abs(a[i] - v) < Math.abs(a[b] - v)) b = i; return b; };
const surf0 = { x: { dom: [-3, -1] }, y: { dom: [0, 20] }, xs: [-3, -2, -1], ys: [0, 10, 20], vals: [[1, 2, 3], [4, 5, 6], [7, 8, 9]], argmax: [2, 2] };
const bl = LB.blocks(surf0, nearestIdx);
eq([bl.xs.length, bl.ys.length, bl.vals.length, bl.vals[0].length], [60, 60, 60, 60], 'blocs : au moins 60 échantillons par axe');
eq([bl.vals[0][0], bl.vals[0][59], bl.vals[59][0], bl.vals[59][59], bl.vals[30][30]], [1, 3, 7, 9, 5], 'blocs : valeurs des cellules les plus proches');
const distinct = new Set(); bl.vals.forEach(r => r.forEach(v => distinct.add(v)));
eq(distinct.size, 9, 'blocs : aucune valeur interpolée');
eq(bl.vals[bl.argmax[1]][bl.argmax[0]], 9, 'blocs : la meilleure cellule reste repérée');
eq(surf0.xs.length, 3, 'blocs : la surface d’origine est intacte');

/* ---------- 9. Saisie rapide ---------- */
let q = LB.quickTrade({ side: 'long', entry: 20000, stop: 19990, target: 20020, exit: 20020, qty: 2, pointValue: 2, commissionRT: 1.24 });
eq([q.ok, q.pnl, q.r, q.fin], [true, 77.52, 1.938, 'objectif'], 'achat à l’objectif : pnl et R nets de commission');
q = LB.quickTrade({ side: 'short', entry: 20000, stop: 20010, exit: 20010, qty: 1, pointValue: 2, commissionRT: 1.24 });
eq([q.pnl, q.r, q.fin], [-21.24, -1.062, 'stop'], 'vente au stop');
q = LB.quickTrade({ side: 'long', entry: 20000, exit: 20005, qty: 1, pointValue: 2, commissionRT: 0 });
eq([q.ok, q.r, q.fin], [true, null, 'manuel'], 'sans stop : pas de R');
eq(LB.quickTrade({ side: 'long', entry: 20000, stop: 20010, exit: 20005, qty: 1, pointValue: 2 }).ok, false, 'stop du mauvais côté refusé');
eq(LB.quickTrade({ side: 'long', entry: 20000, exit: 20005, qty: 1.5, pointValue: 2 }).ok, false, 'quantité non entière refusée');

/* ---------- 10. Calendrier ---------- */
const nw = LB.newsFrom([{ date: '2026-01-07', time: '14:30', impact: 3 }, { date: '2026-07-07', time: '14h30', impact: '2' }, { date: 'x', time: '10:00' }, { date: '2026-01-08' }]);
eq(nw, [{ t: Date.UTC(2026, 0, 7, 13, 30), impact: 3 }, { t: Date.UTC(2026, 6, 7, 12, 30), impact: 2 }], 'publications en heure de Paris → UTC (hiver, été)');

console.log((fail ? 'ÉCHEC' : 'OK') + ' — labo : ' + pass + ' réussis, ' + fail + ' échoués');
process.exit(fail ? 1 : 0);
