#!/usr/bin/env node
/* Outil d’import d’ALP Desk : les fichiers de l’utilisateur → les documents et les assets que Claude écrit dans
   l’artefact (LABO.md §2.1–2.3, 2.7, 2.9, 8). Node, sans dépendance. Il charge les fichiers du desk par
   test/harness.js : la lecture des CSV de barres est T.lib.quant.parseCsv, le découpage et le codage des
   séances T.lib.donnees — une seule implémentation, celle de la page.

   node tools/ingest.js bars FICHIER.csv --tz America/New_York --stamp ouverture|cloture --name "MNQ 1 min"
        --instrument MNQ --roll ajuste|non-ajuste|inconnu [--existing DOSSIER] [--force] --out DOSSIER
   node tools/ingest.js trades FICHIER.csv --tz Europe/Paris --instrument MNQ [--commission 1.24]
        [--dates jj/mm|mm/jj] [--existing DOSSIER] --out DOSSIER
   node tools/ingest.js levels FICHIER.txt --date AAAA-MM-JJ --scale contrat|NDX [--base X] [--band 20]
        [--existing DOSSIER] --out DOSSIER
   node tools/ingest.js fill DOSSIER 2024=<id d’asset> 2025=<id d’asset>     (après les envois d’assets)

   --existing : le dossier écrit par ArtifactData list avec out_dir (<dossier>/<chemin de collection>/<id>.json),
   et, si les fichiers ne portent pas la version, un versions.json { doc_id: version } à sa racine. Les trades déjà
   présents ne sont jamais réécrits ; tout document existant est épinglé par if_version.
   Sortie : <out>/assets/*.json (un fichier par année), <out>/docs/<collection>/<id>.json, et <out>/plan.json, la
   liste ordonnée des appels (assets d’abord, puis lots ArtifactData de 50 écritures et 900 Ko au plus, l’élément
   de boîte en dernier). */
'use strict';
const fs = require('fs'), path = require('path');
const HARNESS = path.resolve(__dirname, '..', 'test', 'harness.js');
const DESKS = path.resolve(__dirname, '..', 'src', 'desks');

const COLL = {
  datasets: 'data/users/me/datasets/items', journal: 'data/users/me/journal/trades',
  levels: 'data/users/me/levels/items', inbox: 'data/users/me/inbox/items'
};
const MAX_WRITES = 50, MAX_BYTES = 900 * 1024, MAX_ASSET = 20 * 1048576;
const PV = { MNQ: 2, NQ: 20, MES: 5, ES: 50, M2K: 5, RTY: 50, MYM: 0.5, YM: 5 };

/* ---------- Socle ---------- */
let ENV = null;
function boot() {
  if (ENV) return ENV;
  const load = require(HARNESS), withEngine = fs.existsSync(path.join(DESKS, 'labo-engine.js'));
  let r = null, warn = null;
  if (withEngine) { try { r = load(['quant', 'labo-engine', 'donnees']); } catch (e) { warn = 'moteur du Labo illisible (' + e.message + ') : clé de séance locale.'; } }
  if (!r) r = load(['quant', 'donnees']);
  ENV = { T: r.T, DN: r.T.lib.donnees, Q: r.T.lib.quant, warn };
  return ENV;
}

/* ---------- Petits outils ---------- */
function parseArgs(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) { const k = a.slice(2), nx = argv[i + 1]; if (nx === undefined || nx.startsWith('--')) o[k] = true; else { o[k] = nx; i++; } }
    else o._.push(a);
  }
  return o;
}
function fail(msg) { const e = new Error(msg); e.user = true; throw e; }
function mkdirp(d) { fs.mkdirSync(d, { recursive: true }); }
function writeJson(file, obj) { mkdirp(path.dirname(file)); const s = JSON.stringify(obj); fs.writeFileSync(file, s); return Buffer.byteLength(s); }
function fnv(s, seed) { let x = seed >>> 0; for (let i = 0; i < s.length; i++) { x ^= s.charCodeAt(i); x = Math.imul(x, 0x01000193) >>> 0; } return x; }
function hash36(s, len) { const a = fnv(s, 0x811c9dc5), b = fnv(s, 0x9747b28c); return (a.toString(36).padStart(7, '0') + b.toString(36).padStart(7, '0')).slice(0, len || 12); }
function iso(t) { return new Date(t).toISOString().slice(0, 19).replace('T', ' ') + ' UTC'; }
function fmtKey(k) { return k ? k.slice(8, 10) + '/' + k.slice(5, 7) + '/' + k.slice(0, 4) : '—'; }
function round2(x) { const r = Math.round(x * 100) / 100; return r === 0 ? 0 : r; }
function normH(s) { return String(s == null ? '' : s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]/g, ''); }
function nowU(prev) { const t = Date.now(); return prev != null && prev >= t ? prev + 1 : t; }

/* ---------- Documents existants (ArtifactData list, out_dir) ---------- */
function walk(dir, out) {
  if (!fs.existsSync(dir)) return out;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) { const p = path.join(dir, e.name); if (e.isDirectory()) walk(p, out); else if (e.name.endsWith('.json')) out.push(p); }
  return out;
}
function unwrap(o) {
  if (!o || typeof o !== 'object' || Array.isArray(o)) return null;
  const isV = v => Number.isInteger(v) && v >= 1;
  if (o.data && typeof o.data === 'object' && !Array.isArray(o.data) && (isV(o.version) || 'doc_id' in o)) return { doc: o.data, version: isV(o.version) ? o.version : null };
  if (o.document && typeof o.document === 'object' && !Array.isArray(o.document)) return { doc: o.document, version: isV(o.version) ? o.version : null };
  const v = [o.__version__, o._version, o.$version, o.meta && o.meta.version].find(isV);
  return { doc: o, version: v || null };
}
/* readExisting(dossier, 'journal/trades') → Map(id → { doc, version, file }) */
function readExisting(dir, suffix) {
  const map = new Map();
  if (!dir) return map;
  if (!fs.existsSync(dir)) fail('Dossier --existing introuvable : ' + dir);
  let versions = {};
  const vf = path.join(dir, 'versions.json');
  if (fs.existsSync(vf)) { try { versions = JSON.parse(fs.readFileSync(vf, 'utf8')) || {}; } catch (e) { fail('versions.json illisible : ' + e.message); } }
  const want = suffix.split('/').join(path.sep);
  for (const f of walk(dir, [])) {
    if (path.basename(f) === 'versions.json') continue;
    if (!path.dirname(f).endsWith(want)) continue;
    let o; try { o = JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { continue; }
    const u = unwrap(o); if (!u) continue;
    const id = u.doc.id || path.basename(f, '.json');
    const v = u.version || (Number.isInteger(versions[id]) ? versions[id] : null);
    map.set(id, { doc: u.doc, version: v, file: f });
  }
  return map;
}

/* ---------- Plan d’appels ---------- */
function batchWrites(writes, maxN, maxB) {
  maxN = maxN || MAX_WRITES; maxB = maxB || MAX_BYTES;
  const out = []; let cur = [], bytes = 0;
  for (const w of writes) {
    const b = (w.bytes || 0) + 256;
    if (b > maxB) fail('Document trop gros pour un lot (' + w.doc_id + ', ' + b + ' octets).');
    if (cur.length && (cur.length >= maxN || bytes + b > maxB)) { out.push({ writes: cur, bytes }); cur = []; bytes = 0; }
    cur.push(w); bytes += b;
  }
  if (cur.length) out.push({ writes: cur, bytes });
  return out;
}
function batchCalls(writes, label) {
  return batchWrites(writes).map((b, k, all) => {
    const ws = b.writes.map(w => { const e = { op: 'set', collection: w.collection, doc_id: w.doc_id, file_path: w.file_path }; if (w.if_version) e.if_version = w.if_version; return e; });
    const call = { tool: 'ArtifactData', what: label + (all.length > 1 ? ' (' + (k + 1) + '/' + all.length + ')' : ''), args: { action: 'batch', url: '$URL', writes: ws }, count: ws.length, bytes: b.bytes };
    const miss = b.writes.filter(w => w.exists && !w.if_version).map(w => w.doc_id);
    if (miss.length) call.lireVersion = miss;
    return call;
  });
}
function writePlan(out, plan) {
  plan.calls = plan.calls.map((c, i) => Object.assign({ n: i + 1 }, c));
  const f = path.join(out, 'plan.json'); mkdirp(out);
  fs.writeFileSync(f, JSON.stringify(plan, null, 1));
  return f;
}
function docWrite(out, sub, collection, doc, existing) {
  const file = path.resolve(out, 'docs', sub, doc.id + '.json'), bytes = writeJson(file, doc);
  const w = { collection, doc_id: doc.id, file_path: file, bytes };
  if (existing) { w.exists = true; if (existing.version) w.if_version = existing.version; }
  return w;
}
function inboxDoc(kind, title, count, detail, go, seed) {
  const at = Date.now();
  return { id: 'ib' + at.toString(36) + hash36(seed + '|' + kind, 6), at, kind, title, count, detail, go, seen: false, u: at };
}

/* =====================================================================
   bars : CSV de barres d’une minute → un asset JSON par année + fiche du jeu + élément de boîte
   ===================================================================== */
function cmdBars(file, o) {
  const { DN, Q } = boot();
  const tz = o.tz || 'America/New_York', stamp = o.stamp || 'ouverture', instrument = String(o.instrument || 'MNQ').toUpperCase(), roll = o.roll || 'inconnu';
  if (['ouverture', 'cloture'].indexOf(stamp) < 0) fail('--stamp : ouverture ou cloture.');
  if (['ajuste', 'non-ajuste', 'inconnu'].indexOf(roll) < 0) fail('--roll : ajuste, non-ajuste ou inconnu.');
  if (['MNQ', 'NQ'].indexOf(instrument) < 0) fail('--instrument : MNQ ou NQ.');
  if (!o.out) fail('--out DOSSIER est obligatoire.');
  const out = path.resolve(o.out), name = o.name && o.name !== true ? String(o.name) : path.basename(file).replace(/\.[a-z0-9]+$/i, '');
  const text = fs.readFileSync(file, 'utf8');
  const r = Q.parseCsv(text, { tz });
  if (r.error) fail(r.error);
  const n = r.bars.length, cols = { t: new Float64Array(n), o: new Float64Array(n), h: new Float64Array(n), l: new Float64Array(n), c: new Float64Array(n), v: new Float64Array(n) };
  r.bars.forEach((b, i) => { cols.t[i] = stamp === 'cloture' ? b.t - 60000 : b.t; cols.o[i] = b.o; cols.h[i] = b.h; cols.l[i] = b.l; cols.c[i] = b.c; cols.v[i] = b.v; });
  let mis = 0, firstMis = -1;
  for (let i = 0; i < n; i++) if (cols.t[i] % 60000 !== 0) { mis++; if (firstMis < 0) firstMis = i; }
  if (mis) fail(mis + ' barre' + (mis > 1 ? 's' : '') + ' hors des minutes entières (première : ' + iso(cols.t[firstMis]) + ') : import refusé.');
  const D = DN.chooseD(cols);
  if (!D) fail('Prix non décimaux au pas 1/4, 1/100 ou 1/10 000 : série ajustée par ratio ? Import refusé.');
  if (!r.hasVolume) cols.v = null;
  const sessions = DN.splitSessions(cols), q = DN.quality(cols, { sessions });
  const rollKeys = {};
  if (roll === 'non-ajuste') q.rolls.filter(x => x.where === 'ouverture').forEach(x => { rollKeys[x.key] = true; });
  const fingerprint = DN.fingerprint({ instrument, D }, cols), id = 'ds' + hash36(fingerprint, 12);
  const ex = readExisting(o.existing, 'datasets/items'), warnings = [];
  for (const [eid, e] of ex) if (eid !== id && e.doc.fingerprint === fingerprint && !e.doc.deleted && !e.doc.deleting && !o.force) {
    const plan = { outil: 'ingest', kind: 'bars', status: 'deja-present', resume: 'Données identiques déjà présentes : jeu ' + eid + ' (« ' + (e.doc.name || '') + ' »). Rien à écrire (--force pour réimporter).', calls: [], warnings: [] };
    mkdirp(out); writePlan(out, plan); return { plan, out, id: eid };
  }
  const prev = ex.get(id) || null;
  const enc = DN.encodeYears(cols, { D, instrument, sessions, rollKeys });
  /* Contrôle bit pour bit avant d’écrire : ce que la page décodera est exactement ce que parseCsv a lu. */
  const back = DN.decodeAssets(enc.years.map(y => y.text));
  for (let i = 0; i < n; i++) if (back.cols.t[i] !== cols.t[i] || back.cols.o[i] !== cols.o[i] || back.cols.h[i] !== cols.h[i] || back.cols.l[i] !== cols.l[i] || back.cols.c[i] !== cols.c[i] || back.cols.v[i] !== (cols.v ? cols.v[i] : 0))
    fail('Contrôle du codage en échec à la barre ' + i + ' (' + iso(cols.t[i]) + ').');
  mkdirp(path.join(out, 'assets'));
  const calls = [], assets = [];
  enc.years.forEach(y => {
    if (y.bytes > MAX_ASSET) fail('L’année ' + y.year + ' dépasse 20 Mio (' + y.bytes + ' octets).');
    const f = path.resolve(out, 'assets', id + '-' + y.year + '.json'); fs.writeFileSync(f, y.text);
    calls.push({ tool: 'Artifact', what: 'barres ' + y.year + ' (' + y.sessions + ' séances, ' + (y.bytes / 1048576).toFixed(1) + ' Mio)', args: { action: 'publish', url: '$URL', file_path: f, asset: true }, gives: '$asset:' + y.year });
    assets.push({ year: y.year, id: '$asset:' + y.year, sessions: y.sessions, from: y.from, to: y.to, bytes: y.bytes });
  });
  calls.push({ command: 'node ' + path.resolve(__dirname, 'ingest.js') + ' fill ' + out + ' ' + enc.years.map(y => y.year + '=<id>').join(' '), what: 'reporter dans la fiche l’identifiant rendu par chaque envoi' });
  const now = Date.now();
  const meta = { id, name, instrument, source: 'claude', srcTz: tz, stamp, from: sessions[0].key, to: sessions[sessions.length - 1].key, sessions: sessions.length, bars: n, hasVolume: !!r.hasVolume, D, roll, fingerprint,
    assets, complete: true, note: 'Importé par Claude depuis « ' + path.basename(file) + ' ».', createdAt: prev && prev.doc.createdAt || now, u: nowU(prev && prev.doc.u) };
  const wMeta = docWrite(out, 'datasets', COLL.datasets, meta, prev);
  calls.push.apply(calls, batchCalls([wMeta], 'fiche du jeu (complete: true)'));
  const detail = fmtKey(meta.from) + ' → ' + fmtKey(meta.to) + ' · ' + n.toLocaleString('fr-FR') + ' barres · pas 1/' + D + ' · contrat continu ' + ({ ajuste: 'ajusté', 'non-ajuste': 'non ajusté', inconnu: 'inconnu' })[roll] + (q.rollCount ? ' · ' + q.rollCount + ' saut(s) suspect(s)' : '');
  const ib = inboxDoc('barres', 'Barres « ' + name + ' »', sessions.length, detail, { desk: 'donnees', tab: 'series', sel: id }, fingerprint);
  calls.push.apply(calls, batchCalls([docWrite(out, 'inbox', COLL.inbox, ib, null)], 'élément de boîte (en dernier)'));
  const cleanup = prev ? (prev.doc.assets || []).filter(a => /^[0-9a-f]{32}$/.test(a.id || '')).map(a => ({ tool: 'Artifact', args: { action: 'delete', url: '$URL', path: a.id }, why: 'ancien fichier ' + a.year + ' de ce jeu, plus désigné par aucune fiche après l’écriture' })) : [];
  if (prev && !prev.version) warnings.push('Le jeu ' + id + ' existe déjà mais sa version est inconnue : lis-le (ArtifactData get) et ajoute if_version au lot.');
  if (r.skipped) warnings.push(r.skipped + ' ligne(s) ignorée(s)' + (r.firstSkip ? ' (ligne ' + r.firstSkip.line + ' : « ' + r.firstSkip.text + ' »)' : '') + '.');
  if (r.fixed) warnings.push(r.fixed + ' barre(s) réparée(s) (plus haut et plus bas).');
  if (r.dup) warnings.push(r.dup + ' horodatage(s) en double : la dernière ligne gardée.');
  (r.warnings || []).forEach(w => warnings.push(w));
  if (q.rollCount) warnings.push(q.rollCount + ' saut(s) suspect(s) au-delà de 8 écarts-types robustes : ' + q.rolls.slice(0, 5).map(x => x.key + ' (' + x.gap.toFixed(2) + ' pt)').join(', ') + '.');
  if (q.short.length) warnings.push(q.short.length + ' séance(s) de moins de 80 % des 1 380 barres.');
  const plan = { outil: 'ingest', kind: 'bars', cree: new Date(now).toISOString(), url: '<lien de l’artefact : remplace $URL>', id, fingerprint,
    resume: 'Jeu « ' + name + ' » : ' + sessions.length + ' séances, ' + n + ' barres, ' + enc.years.length + ' fichier(s) par année, du ' + fmtKey(meta.from) + ' au ' + fmtKey(meta.to) + '.',
    ordre: 'Envoyer chaque asset, lancer fill avec les identifiants rendus, puis les lots ArtifactData dans l’ordre ; l’élément de boîte toujours en dernier.',
    calls, cleanup, warnings, qualite: { sessions: q.sessions, missing: q.missing, holes: q.holes, flat: q.flat, rolls: q.rolls.slice(0, 10), short: q.short.length, noVolume: q.noVolume.length } };
  writePlan(out, plan);
  return { plan, out, id, meta, years: enc.years.map(y => y.year) };
}

/* fill : reporte les identifiants d’assets dans la fiche et le plan. */
function cmdFill(dir, pairs) {
  const out = path.resolve(dir), pf = path.join(out, 'plan.json');
  if (!fs.existsSync(pf)) fail('plan.json introuvable dans ' + out);
  const ids = {};
  pairs.forEach(p => { const m = /^(\d{4})=([0-9a-f]{32})$/.exec(p); if (!m) fail('Attendu ANNEE=<32 caractères hexadécimaux>, reçu « ' + p + ' ».'); ids[m[1]] = m[2]; });
  const files = walk(path.join(out, 'docs'), []);
  let left = 0;
  files.forEach(f => {
    let s = fs.readFileSync(f, 'utf8');
    const s2 = s.replace(/\$asset:(\d{4})/g, (m, y) => ids[y] || m);
    if (s2 !== s) fs.writeFileSync(f, s2);
    left += (s2.match(/\$asset:\d{4}/g) || []).length;
  });
  if (left) fail(left + ' identifiant(s) d’asset manquant(s) : donne ANNEE=<id> pour chaque année envoyée.');
  const plan = JSON.parse(fs.readFileSync(pf, 'utf8'));
  plan.calls.forEach(c => { if (c.gives && /^\$asset:(\d{4})$/.test(c.gives)) { const y = c.gives.slice(7); if (ids[y]) c.rendu = ids[y]; } });
  plan.rempli = true;
  fs.writeFileSync(pf, JSON.stringify(plan, null, 1));
  return { plan, out };
}

/* =====================================================================
   trades : export de plateforme → entrées de journal (FIFO pour des exécutions)
   ===================================================================== */
const TAL = {
  symbol: ['symbol', 'symbole', 'contract', 'contrat', 'instrument', 'product', 'produit', 'ticker', 'market', 'marche', 'sym', 'contractname'],
  side: ['side', 'sens', 'buysell', 'bs', 'action', 'direction', 'longshort', 'achatvente', 'ordside', 'tradeside'],
  qty: ['qty', 'quantity', 'quantite', 'qte', 'size', 'taille', 'contracts', 'contrats', 'filledqty', 'fillqty', 'filled', 'lots', 'nbcontrats', 'filledquantity'],
  price: ['price', 'prix', 'fillprice', 'avgprice', 'avgfillprice', 'averageprice', 'executionprice', 'prixexecution', 'prixmoyen', 'tradeprice'],
  time: ['time', 'timestamp', 'datetime', 'filltime', 'executiontime', 'heure', 'dateheure', 'horodatage', 'tradetime', 'transacttime', 'createdat'],
  date: ['date', 'tradedate', 'jour', 'datedutrade'],
  entryPrice: ['entryprice', 'prixentree', 'prixdentree', 'openprice', 'entry', 'avgentryprice', 'entryavg', 'prixouverture'],
  exitPrice: ['exitprice', 'prixsortie', 'prixdesortie', 'closeprice', 'exit', 'avgexitprice', 'exitavg', 'prixfermeture'],
  entryTime: ['entrytime', 'heureentree', 'heuredentree', 'opentime', 'opened', 'entrydate', 'dateentree', 'datedentree', 'entrytimestamp', 'opendate'],
  exitTime: ['exittime', 'heuresortie', 'heuredesortie', 'closetime', 'closed', 'exitdate', 'datesortie', 'datedesortie', 'exittimestamp', 'closedate'],
  buyPrice: ['buyprice', 'prixachat', 'prixdachat'], sellPrice: ['sellprice', 'prixvente', 'prixdevente'],
  buyTime: ['boughttimestamp', 'buytime', 'buytimestamp', 'heureachat', 'dateachat'], sellTime: ['soldtimestamp', 'selltime', 'selltimestamp', 'heurevente', 'datevente'],
  pnl: ['pnl', 'pl', 'profit', 'profitloss', 'netpnl', 'netpl', 'netprofit', 'realizedpnl', 'realizedpl', 'realized', 'resultat', 'resultatnet', 'gain', 'gainperte', 'plnet', 'pnlnet', 'grosspnl', 'grosspl'],
  comm: ['commission', 'commissions', 'fees', 'fee', 'frais', 'comm', 'commissionsfees', 'totalfees', 'commissionfees'],
  status: ['status', 'statut', 'etat', 'state', 'orderstatus']
};
function splitLine(line, sep) {
  if (line.indexOf('"') < 0) return line.split(sep);
  const out = []; let cur = '', inq = false;
  for (let i = 0; i < line.length; i++) { const ch = line[i]; if (ch === '"') { if (inq && line[i + 1] === '"') { cur += '"'; i++; } else inq = !inq; } else if (ch === sep && !inq) { out.push(cur); cur = ''; } else cur += ch; }
  out.push(cur); return out;
}
function clean(s) { return String(s == null ? '' : s).trim().replace(/^["']+|["']+$/g, '').trim(); }
function readTable(text) {
  const lines = String(text).replace(/^﻿/, '').split(/\r\n|\n|\r/);
  let first = -1; for (let i = 0; i < lines.length; i++) if (lines[i].trim()) { first = i; break; }
  if (first < 0) fail('Le fichier est vide.');
  let sep = null, bc = 0;
  for (const c of ['\t', ';', ',']) { const k = lines[first].split(c).length - 1; if (k > bc) { bc = k; sep = c; } }
  if (!sep) fail('Aucun séparateur reconnu : virgule, point-virgule ou tabulation.');
  const head = splitLine(lines[first], sep).map(clean), rows = [];
  for (let i = first + 1; i < lines.length; i++) if (lines[i].trim()) rows.push({ line: i + 1, cells: splitLine(lines[i], sep).map(clean) });
  return { sep, head, rows };
}
function findCols(head) {
  const nh = head.map(normH), ix = {};
  Object.keys(TAL).forEach(k => { ix[k] = -1; for (const a of TAL[k]) { const j = nh.indexOf(a); if (j >= 0) { ix[k] = j; break; } } });
  ix.netPnl = ix.pnl >= 0 && /net/.test(nh[ix.pnl]);
  return ix;
}
function parseNum(s, decComma) {
  let t = clean(s).replace(/[\s  $€]/g, '').replace(/−/g, '-');
  if (!t) return NaN;
  let neg = false;
  if (/^\(.*\)$/.test(t)) { neg = true; t = t.slice(1, -1); }
  if (t.indexOf(',') >= 0 && t.indexOf('.') >= 0) { if (t.lastIndexOf(',') > t.lastIndexOf('.')) t = t.replace(/\./g, '').replace(',', '.'); else t = t.replace(/,/g, ''); }
  else if (t.indexOf(',') >= 0) { t = decComma || !/^-?\d{1,3}(,\d{3})+$/.test(t) ? t.replace(',', '.') : t.replace(/,/g, ''); }
  if (!/^[-+]?\d*\.?\d+(e[-+]?\d+)?$/i.test(t)) return NaN;
  const x = Number(t); return isFinite(x) ? (neg ? -x : x) : NaN;
}
const RE_YMDT = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[T ]+(\d{1,2}):(\d{2})(?::(\d{2})(?:[.,](\d+))?)?)?\s*(AM|PM)?\s*(Z|UTC|GMT|[+-]\d{2}:?\d{2})?$/i;
const RE_DMYT = /^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})(?:[T ,]+(\d{1,2}):(\d{2})(?::(\d{2})(?:[.,](\d+))?)?)?\s*(AM|PM)?\s*(Z|UTC|GMT|[+-]\d{2}:?\d{2})?$/i;
function parseWhen(s, tz, order, Q) {
  s = clean(s); if (!s) return NaN;
  if (/^\d{13}$/.test(s)) return +s;
  if (/^\d{10}(\.\d+)?$/.test(s)) return Math.round(+s * 1000);
  let m, y, mo, d, hh, mi, ss, frac, ap, z;
  if ((m = RE_YMDT.exec(s))) { y = +m[1]; mo = +m[2]; d = +m[3]; hh = +(m[4] || 0); mi = +(m[5] || 0); ss = +(m[6] || 0); frac = m[7] || ''; ap = m[8]; z = m[9]; }
  else if ((m = RE_DMYT.exec(s))) { if (order === 'mdy') { mo = +m[1]; d = +m[2]; } else { d = +m[1]; mo = +m[2]; } y = +m[3]; if (y < 100) y += 2000; hh = +(m[4] || 0); mi = +(m[5] || 0); ss = +(m[6] || 0); frac = m[7] || ''; ap = m[8]; z = m[9]; }
  else return NaN;
  if (ap) { hh = hh % 12 + (/pm/i.test(ap) ? 12 : 0); }
  if (!(mo >= 1 && mo <= 12 && d >= 1 && d <= 31 && hh <= 23 && mi <= 59 && ss <= 60)) return NaN;
  const ms = frac ? Math.round(+('0.' + frac) * 1000) : 0;
  if (z) { let off = 0; if (/^[+-]/.test(z)) { const zz = z.replace(':', ''); off = (zz[0] === '-' ? -1 : 1) * (+zz.slice(1, 3) * 60 + +(zz.slice(3, 5) || 0)); } return Date.UTC(y, mo - 1, d, hh, mi, ss, ms) - off * 60000; }
  return Q.wallToUtc(y, mo, d, hh, mi, tz) + ss * 1000 + ms;
}
function sideOf(s) {
  const t = normH(s);
  if (!t) return 0;
  if (/^(b|buy|bot|bought|long|achat|acheter|achete|a|l)$/.test(t) || /buy|achat|long/.test(t)) return 1;
  if (/^(s|sell|sld|sold|short|vente|vendre|vendu|v)$/.test(t) || /sell|vente|short/.test(t)) return -1;
  return 0;
}
function rootOf(sym, fallback) {
  const s = String(sym || '').toUpperCase().replace(/^[/@]/, '');
  const m = /^(MNQ|NQ|MES|ES|M2K|RTY|MYM|YM)/.exec(s);
  return m ? m[1] : fallback;
}
/* FIFO : chaque sortie consomme la plus ancienne entrée ouverte du même symbole ; le surplus ouvre en sens
   inverse. Une ligne par paire (exécution d’entrée, exécution de sortie). */
function fifo(fills) {
  const ord = fills.map((f, i) => [f, i]).sort((a, b) => (a[0].t - b[0].t) || (a[1] - b[1])).map(x => x[0]);
  const book = {}, trips = [];
  for (const f of ord) {
    const q = book[f.symbol] || (book[f.symbol] = []);
    let rem = f.qty;
    while (rem > 1e-12 && q.length && q[0].side !== f.side) {
      const lot = q[0], m = Math.min(rem, lot.qty);
      trips.push({ symbol: f.symbol, side: lot.side, qty: m, entry: lot.price, exit: f.price, at: lot.t, closedAt: f.t,
        comm: lot.cpc == null || f.cpc == null ? null : (lot.cpc + f.cpc) * m, lines: [lot.line, f.line] });
      lot.qty -= m; rem -= m; if (lot.qty <= 1e-12) q.shift();
    }
    if (rem > 1e-12) q.push({ side: f.side, qty: rem, price: f.price, t: f.t, line: f.line, cpc: f.cpc });
  }
  const open = []; Object.keys(book).forEach(s => book[s].forEach(l => open.push({ symbol: s, side: l.side, qty: l.qty, price: l.price, t: l.t, line: l.line })));
  return { trips, open };
}
function parseTrades(text, o) {
  const { Q } = boot();
  const tz = o.tz || 'Europe/Paris', tab = readTable(text), ix = findCols(tab.head), dec = tab.sep !== ',';
  const cell = (r, k) => ix[k] >= 0 ? r.cells[ix[k]] : '';
  const isClock = s => /^\d{1,2}:\d{2}(:\d{2}([.,]\d+)?)?\s*(AM|PM)?$/i.test(s);
  const stamp = (r, kTime, kDate) => { const tv = cell(r, kTime), dv = kDate ? cell(r, kDate) : ''; return dv && tv && isClock(tv) ? dv + ' ' + tv : (tv || dv); };
  const tripMode = (ix.entryPrice >= 0 && ix.exitPrice >= 0) || (ix.buyPrice >= 0 && ix.sellPrice >= 0);
  const fillMode = !tripMode && ix.price >= 0 && (ix.time >= 0 || ix.date >= 0) && (ix.side >= 0 || ix.qty >= 0);
  if (!tripMode && !fillMode) fail('Colonnes introuvables : il faut soit prix et heure d’entrée et de sortie, soit prix, heure et sens de chaque exécution. En-têtes lus : ' + tab.head.join(', ') + '.');
  const timeCells = [];
  tab.rows.forEach(r => { if (tripMode) { [stamp(r, 'entryTime', 'date'), stamp(r, 'exitTime', 'date'), cell(r, 'buyTime'), cell(r, 'sellTime')].forEach(s => s && timeCells.push(s)); } else timeCells.push(stamp(r, 'time', ix.time >= 0 && ix.date >= 0 && ix.date !== ix.time ? 'date' : null)); });
  let dmy = 0, mdy = 0; timeCells.forEach(s => { const m = /^(\d{1,2})[-/.](\d{1,2})[-/.]\d{2,4}/.exec(s); if (m) { if (+m[1] > 12) dmy++; else if (+m[2] > 12) mdy++; } });
  const forced = o.dates === 'mm/jj' ? 'mdy' : o.dates === 'jj/mm' ? 'dmy' : null;
  const order = forced || (mdy > 0 && dmy === 0 ? 'mdy' : 'dmy'), warnings = [];
  if (!forced && dmy === 0 && mdy === 0 && timeCells.some(s => /^\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}/.test(s))) warnings.push('Dates ambiguës (jour et mois tous deux ≤ 12) : lues jour/mois. Ajoute --dates mm/jj si la plateforme écrit le mois d’abord.');
  const skipped = []; const skip = (r, why) => skipped.push({ line: r.line, why });
  const fallbackRoot = String(o.instrument || 'MNQ').toUpperCase();
  let trips = [], open = [], fmt;
  const hasComm = ix.comm >= 0;
  if (fillMode) {
    fmt = 'executions';
    const fills = [];
    tab.rows.forEach(r => {
      if (ix.status >= 0 && /cancel|annul|reject|refus|expir|working|pending|attente/i.test(cell(r, 'status'))) { skip(r, 'ordre non exécuté'); return; }
      const t = parseWhen(stamp(r, 'time', ix.time >= 0 && ix.date >= 0 && ix.date !== ix.time ? 'date' : null), tz, order, Q);
      const price = parseNum(cell(r, 'price'), dec); let qty = ix.qty >= 0 ? parseNum(cell(r, 'qty'), dec) : 1;
      let side = ix.side >= 0 ? sideOf(cell(r, 'side')) : 0;
      if (!side && isFinite(qty) && qty !== 0) side = qty > 0 ? 1 : -1;
      qty = Math.abs(qty);
      if (!isFinite(t) || !isFinite(price) || !(qty > 0) || !side) { skip(r, 'exécution illisible'); return; }
      const c = hasComm ? Math.abs(parseNum(cell(r, 'comm'), dec)) : NaN;
      fills.push({ line: r.line, t, price, qty, side, symbol: cell(r, 'symbol') || fallbackRoot, cpc: hasComm ? (isFinite(c) ? c / qty : 0) : null });
    });
    const f = fifo(fills); trips = f.trips; open = f.open;
    trips.forEach(x => { x.pnlFile = NaN; });
  } else {
    fmt = 'allers-retours';
    tab.rows.forEach(r => {
      let side = ix.side >= 0 ? sideOf(cell(r, 'side')) : 0, entry, exit, at, closedAt;
      let qty = ix.qty >= 0 ? Math.abs(parseNum(cell(r, 'qty'), dec)) : 1;
      if (ix.entryPrice >= 0) {
        entry = parseNum(cell(r, 'entryPrice'), dec); exit = parseNum(cell(r, 'exitPrice'), dec);
        at = parseWhen(stamp(r, 'entryTime', ix.entryTime >= 0 && ix.date >= 0 ? 'date' : null), tz, order, Q); closedAt = parseWhen(stamp(r, 'exitTime', ix.exitTime >= 0 && ix.date >= 0 ? 'date' : null), tz, order, Q);
      } else {
        const bp = parseNum(cell(r, 'buyPrice'), dec), sp = parseNum(cell(r, 'sellPrice'), dec), bt = parseWhen(cell(r, 'buyTime'), tz, order, Q), st = parseWhen(cell(r, 'sellTime'), tz, order, Q);
        if (!side && isFinite(bt) && isFinite(st)) side = bt <= st ? 1 : -1;
        if (side > 0) { entry = bp; exit = sp; at = bt; closedAt = st; } else { entry = sp; exit = bp; at = st; closedAt = bt; }
      }
      const pnlFile = ix.pnl >= 0 ? parseNum(cell(r, 'pnl'), dec) : NaN;
      if (!side && isFinite(pnlFile) && pnlFile !== 0 && isFinite(entry) && isFinite(exit) && exit !== entry) side = Math.sign(pnlFile) * Math.sign(exit - entry);
      if (!isFinite(entry) || !isFinite(exit) || !isFinite(at) || !(qty > 0) || !side) { skip(r, 'trade illisible'); return; }
      if (!isFinite(closedAt)) closedAt = at;
      const c = hasComm ? Math.abs(parseNum(cell(r, 'comm'), dec)) : NaN;
      trips.push({ symbol: cell(r, 'symbol') || fallbackRoot, side, qty, entry, exit, at, closedAt, comm: hasComm ? (isFinite(c) ? c : 0) : null, pnlFile, lines: [r.line] });
    });
  }
  return { trips, open, fmt, skipped, warnings, ix, order, tz, hasComm };
}
/* Une entrée de journal (CONTRACT.md) + { id, u, src: 'import', imp } ; jamais de stop inventé, donc jamais de r. */
function toJournal(trips, o, meta) {
  const commOpt = o.commission != null && o.commission !== true ? parseNum(o.commission) : null, fallbackRoot = String(o.instrument || 'MNQ').toUpperCase();
  const occ = {}, out = [], notes = { netFromFile: 0, grossFromFile: 0, fileOther: 0, computed: 0, commInconnue: 0, horsMNQ: 0 };
  trips.forEach(x => {
    const root = rootOf(x.symbol, fallbackRoot), pv = PV[root] || PV[fallbackRoot] || 2;
    if (root !== 'MNQ' && root !== 'NQ') notes.horsMNQ++;
    let comm = x.comm, commSrc = 'fichier';
    if (comm == null) { if (commOpt != null && isFinite(commOpt)) { comm = commOpt * x.qty; commSrc = 'option'; } else { comm = 0; commSrc = 'inconnue'; notes.commInconnue++; } }
    const gross = x.side * (x.exit - x.entry) * pv * x.qty;
    let pnl, pnlSrc;
    if (isFinite(x.pnlFile)) {
      if (Math.abs(x.pnlFile - gross) < 0.011 && comm) { pnl = gross - comm; pnlSrc = 'fichier brut, commission retirée'; notes.grossFromFile++; }
      else { pnl = x.pnlFile; pnlSrc = 'fichier'; if (Math.abs(x.pnlFile - (gross - comm)) < 0.011 || Math.abs(x.pnlFile - gross) < 0.011) notes.netFromFile++; else notes.fileOther++; }
    } else { pnl = gross - comm; pnlSrc = 'calcul'; notes.computed++; }
    const content = [root, x.symbol, x.side, x.qty, x.at, x.closedAt, x.entry, x.exit].join('|');
    occ[content] = (occ[content] || 0) + 1;
    const id = 'i' + hash36(content + '#' + occ[content], 13);
    out.push({ id, at: x.at, kind: 'pris', side: x.side > 0 ? 'long' : 'short', entry: x.entry, exit: x.exit, qty: x.qty, instrument: root, status: 'clos', closedAt: x.closedAt, pnl: round2(pnl),
      src: 'import', imp: { file: meta.file, at: meta.at, fmt: meta.fmt, lines: x.lines, symbol: x.symbol, commission: round2(comm), commissionSource: commSrc, pnlSource: pnlSrc }, u: 0 });
  });
  return { entries: out, notes };
}
function cmdTrades(file, o) {
  if (!o.out) fail('--out DOSSIER est obligatoire.');
  const out = path.resolve(o.out), text = fs.readFileSync(file, 'utf8'), at = Date.now();
  const p = parseTrades(text, o);
  const j = toJournal(p.trips, o, { file: path.basename(file), at, fmt: p.fmt });
  const ex = readExisting(o.existing, 'journal/trades');
  const fresh = j.entries.filter(e => !ex.has(e.id)), kept = j.entries.length - fresh.length;
  const writes = [];
  fresh.forEach(e => { e.u = nowU(); writes.push(docWrite(out, 'journal', COLL.journal, e, null)); });
  const calls = batchCalls(writes, 'trades');
  const warnings = p.warnings.slice();
  if (p.skipped.length) warnings.push(p.skipped.length + ' ligne(s) ignorée(s), première : ligne ' + p.skipped[0].line + ' (' + p.skipped[0].why + ').');
  if (p.open.length) warnings.push(p.open.length + ' position(s) encore ouverte(s) en fin de fichier : non importée(s).');
  if (j.notes.commInconnue) warnings.push('Commission absente du fichier pour ' + j.notes.commInconnue + ' trade(s) : P&L brut. Relance avec --commission X ($ aller-retour par contrat) si tu la connais.');
  if (j.notes.fileOther) warnings.push(j.notes.fileOther + ' P&L du fichier ne se retrouvent pas par le calcul (prix × quantité × valeur du point) : gardés tels quels.');
  if (j.notes.horsMNQ) warnings.push(j.notes.horsMNQ + ' trade(s) hors MNQ et NQ.');
  if (fresh.length) {
    const detail = 'Fichier « ' + path.basename(file) + ' » : ' + fresh.length + ' nouveau(x)' + (kept ? ', ' + kept + ' déjà présent(s), non réécrit(s)' : '') + (p.open.length ? ', ' + p.open.length + ' position(s) ouverte(s) ignorée(s)' : '') + '. Sans stop connu, aucun R : ajoute le stop dans le journal pour le calculer.';
    const ib = inboxDoc('trades', fresh.length + ' trade' + (fresh.length > 1 ? 's' : '') + ' importé' + (fresh.length > 1 ? 's' : ''), fresh.length, detail, { desk: 'journal', tab: 'registre' }, path.basename(file) + at);
    calls.push.apply(calls, batchCalls([docWrite(out, 'inbox', COLL.inbox, ib, null)], 'élément de boîte (en dernier)'));
  }
  const plan = { outil: 'ingest', kind: 'trades', cree: new Date(at).toISOString(), url: '<lien de l’artefact : remplace $URL>', format: p.fmt, ordreDates: p.order,
    resume: j.entries.length + ' aller(s)-retour(s) lu(s) (' + p.fmt + ') : ' + fresh.length + ' à écrire, ' + kept + ' déjà présent(s).', calls, cleanup: [], warnings };
  mkdirp(out); writePlan(out, plan);
  return { plan, out, entries: j.entries, fresh, kept, open: p.open, parsed: p };
}

/* =====================================================================
   levels : collage « NOM : prix » → document du mois (LABO.md 2.2)
   Règles de lecture de pine/alp0-gex.pine : un nombre se nettoie de ce qui le décore, jamais de son signe ;
   le sens de lecture (« nom : prix » ou « prix = nom ») est déduit du côté qui rend un nombre ; un titre ##
   commute la lecture ; une fenêtre de plausibilité écarte ce qui est trop loin des autres.
   ===================================================================== */
function cleanNumber(s) { return String(s).replace(/[,\s  *`$_]/g, '').replace(/−/g, '-').trim(); }
function cleanTag(s) { return String(s).replace(/[*`#]/g, '').replace(/-/g, ' ').replace(/\s+/g, ' ').trim(); }
function toNumber(s) { return /^[-+]?\d+(\.\d+)?$/.test(s) ? Number(s) : NaN; }
function headDigits(s) { const m = /^\d{1,3}/.exec(cleanTag(s)); return m ? m[0] : ''; }
function codeDe(tag, pref) {
  const t = String(tag || '').toLowerCase().trim();
  let c;
  if (t === '') c = '';
  else if (t.indexOf('macro') >= 0 || t === 'rm') c = 'RM';
  else if (t.indexOf('flip') >= 0 || t.indexOf('hvl') >= 0) c = 'HVL';
  else if (t.indexOf('max pain') >= 0 || t.indexOf('maxpain') >= 0 || t === 'mp') c = 'MP';
  else if (t.indexOf('gamma wall') >= 0 || t.indexOf('major wall') >= 0 || t === 'gw') c = 'GW';
  else if (t.indexOf('call') >= 0 || t.indexOf('resist') >= 0 || t === 'cr') c = 'CR';
  else if (t.indexOf('put') >= 0 || t.indexOf('support') >= 0 || t === 'ps') c = 'PS';
  else c = t.toUpperCase();
  const dejaPref = c.length > 0 && /^\d/.test(c);
  return c === '' || !pref || dejaPref || c === 'RM' ? c : pref + c;
}
function parseLevels(text, o) {
  o = o || {};
  const band = o.band != null && o.band !== true ? Number(o.band) : 20, tick = o.tick || 0.25;
  const lines = String(text).replace(/^﻿/, '').split(/\r\n|\n|\r/);
  let section = 'niveaux', pref = '';
  const cands = [], rejected = [];
  /* Première passe : l’échéance (« horizon: 0 dte ») dans la section de contexte. */
  lines.forEach(raw => { const l = raw.trim(); if (/^#/.test(l)) { section = /context|contexte/i.test(l) ? 'contexte' : /level|niveau|zone/i.test(l) ? 'niveaux' : 'autre'; return; } if (section === 'contexte' && /horizon/i.test(l)) { const p = l.split(/[:=|]/); if (p.length > 1) pref = headDigits(p.slice(1).join(':')); } });
  section = 'niveaux';
  lines.forEach((raw, i) => {
    const l = raw.trim(); if (!l) return;
    if (/^#/.test(l)) { section = /context|contexte/i.test(l) ? 'contexte' : /level|niveau|zone/i.test(l) ? 'niveaux' : 'autre'; return; }
    if (section !== 'niveaux') return;
    let parts;
    if (l.indexOf('=') >= 0) parts = l.split('=');
    else if (l.indexOf(':') >= 0) parts = l.split(':');
    else if (l.indexOf('|') >= 0) parts = l.split('|').filter(x => x.trim() !== '');
    else parts = [l];
    const g = (parts[0] || '').trim(), d = parts.length > 1 ? parts.slice(1).join(':').trim() : '';
    const vG = toNumber(cleanNumber(g)), vD = toNumber(cleanNumber(d));
    let v = NaN, tag = '';
    if (isFinite(vG)) { v = vG; tag = cleanTag(d); } else if (isFinite(vD)) { v = vD; tag = cleanTag(g); }
    if (!isFinite(v)) { rejected.push({ line: i + 1, text: l.slice(0, 60), why: 'aucun nombre' }); return; }
    cands.push({ line: i + 1, text: l.slice(0, 60), v, tag });
  });
  const vs = cands.map(c => c.v).sort((a, b) => a - b), n = vs.length;
  const median = n ? (n % 2 ? vs[(n - 1) / 2] : (vs[n / 2 - 1] + vs[n / 2]) / 2) : NaN, win = Math.abs(median) * band / 100;
  const levels = {};
  let unnamed = 0;
  cands.forEach(c => {
    if (!(Math.abs(c.v - median) <= win)) { rejected.push({ line: c.line, text: c.text, why: 'hors de la fenêtre de ' + band + ' % autour de la médiane' }); return; }
    let code = codeDe(c.tag, pref);
    if (!code) code = 'N' + (++unnamed);
    let name = code, k = 2;
    while (Object.prototype.hasOwnProperty.call(levels, name) && Math.abs(levels[name] - c.v) >= tick) name = code + (k++);
    if (Object.prototype.hasOwnProperty.call(levels, name)) return; /* même nom, même prix : un seul niveau */
    levels[name] = c.v;
  });
  return { levels, rejected, median, prefix: pref, band, count: Object.keys(levels).length };
}
function cmdLevels(file, o) {
  if (!o.out) fail('--out DOSSIER est obligatoire.');
  const key = o.date; if (!/^\d{4}-\d{2}-\d{2}$/.test(key || '')) fail('--date AAAA-MM-JJ (la clé de la séance Globex) est obligatoire.');
  const scale = o.scale || 'contrat'; if (['contrat', 'NDX'].indexOf(scale) < 0) fail('--scale : contrat ou NDX.');
  const base = o.base != null && o.base !== true ? parseNum(String(o.base)) : null;
  if (o.base != null && !isFinite(base)) fail('--base : un nombre (NQ − NDX ce jour-là).');
  const out = path.resolve(o.out), text = fs.readFileSync(file, 'utf8');
  const r = parseLevels(text, o);
  if (!r.count) fail('Aucun niveau lu. Lignes refusées : ' + r.rejected.slice(0, 5).map(x => x.line + ' (' + x.why + ')').join(', ') + '.');
  const month = key.slice(0, 7), ex = readExisting(o.existing, 'levels/items'), prev = ex.get(month) || null;
  const days = Object.assign({}, prev && prev.doc.days || {});
  const day = { levels: r.levels, scale, source: o.source && o.source !== true ? String(o.source) : path.basename(file) };
  if (isFinite(base)) day.base = base;
  const replaced = !!days[key];
  days[key] = day;
  const doc = { id: month, days, u: nowU(prev && prev.doc.u) };
  const calls = batchCalls([docWrite(out, 'levels', COLL.levels, doc, prev)], 'niveaux du mois ' + month);
  const ib = inboxDoc('niveaux', 'Niveaux du ' + fmtKey(key), r.count, Object.keys(r.levels).join(', ') + ' · échelle ' + scale + (scale === 'NDX' ? (isFinite(base) ? ', base ' + base : ', base absente') : ''), { desk: 'donnees', tab: 'niveaux', sel: key }, key + '|' + JSON.stringify(r.levels));
  calls.push.apply(calls, batchCalls([docWrite(out, 'inbox', COLL.inbox, ib, null)], 'élément de boîte (en dernier)'));
  const warnings = [];
  if (scale === 'NDX' && !isFinite(base)) warnings.push('Échelle NDX sans --base : le Labo refusera ces niveaux tant que la base NQ − NDX de ce jour n’est pas écrite.');
  if (r.rejected.length) warnings.push(r.rejected.length + ' ligne(s) écartée(s) : ' + r.rejected.slice(0, 6).map(x => 'ligne ' + x.line + ' « ' + x.text + ' » (' + x.why + ')').join(' ; ') + '.');
  if (replaced) warnings.push('La séance ' + key + ' avait déjà des niveaux : ils sont remplacés.');
  if (prev && !prev.version) warnings.push('Le mois ' + month + ' existe déjà mais sa version est inconnue : lis-le (ArtifactData get) et ajoute if_version au lot.');
  const plan = { outil: 'ingest', kind: 'levels', cree: new Date().toISOString(), url: '<lien de l’artefact : remplace $URL>', resume: r.count + ' niveau(x) pour la séance ' + key + ' (' + scale + '), document du mois ' + month + '.', calls, cleanup: [], warnings };
  mkdirp(out); writePlan(out, plan);
  return { plan, out, doc, parsed: r };
}

/* ---------- Ligne de commande ---------- */
function usage() {
  return ['Usage :',
    '  node tools/ingest.js bars FICHIER.csv --tz America/New_York --stamp ouverture|cloture --name "MNQ 1 min" --instrument MNQ --roll ajuste|non-ajuste|inconnu [--existing DOSSIER] --out DOSSIER',
    '  node tools/ingest.js trades FICHIER.csv --tz Europe/Paris --instrument MNQ [--commission X] [--dates jj/mm|mm/jj] [--existing DOSSIER] --out DOSSIER',
    '  node tools/ingest.js levels FICHIER.txt --date AAAA-MM-JJ --scale contrat|NDX [--base X] [--band 20] [--existing DOSSIER] --out DOSSIER',
    '  node tools/ingest.js fill DOSSIER 2024=<id> [2025=<id> …]'].join('\n');
}
function report(res) {
  const p = res.plan, lines = [p.resume];
  if (ENV && ENV.warn) lines.push('Note : ' + ENV.warn);
  (p.warnings || []).forEach(w => lines.push('Attention : ' + w));
  lines.push(p.calls.length + ' appel(s) dans ' + path.join(res.out, 'plan.json') + ' :');
  p.calls.forEach(c => lines.push('  ' + c.n + '. ' + (c.tool ? c.tool + ' ' + c.args.action : 'commande') + ' — ' + (c.what || '') + (c.count ? ' (' + c.count + ' écriture(s), ' + Math.round(c.bytes / 1024) + ' Ko)' : '')));
  (p.cleanup || []).forEach(c => lines.push('  puis : ' + c.tool + ' ' + c.args.action + ' ' + c.args.path + ' — ' + c.why));
  return lines.join('\n');
}
function main(argv) {
  const o = parseArgs(argv), cmd = o._[0];
  try {
    let res;
    if (cmd === 'bars' && o._[1]) res = cmdBars(o._[1], o);
    else if (cmd === 'trades' && o._[1]) res = cmdTrades(o._[1], o);
    else if (cmd === 'levels' && o._[1]) res = cmdLevels(o._[1], o);
    else if (cmd === 'fill' && o._[1]) { res = cmdFill(o._[1], o._.slice(2)); console.log('Identifiants reportés : ' + path.join(res.out, 'docs')); return 0; }
    else { console.log(usage()); return cmd ? 2 : 0; }
    console.log(report(res));
    return 0;
  } catch (e) {
    console.error('Erreur : ' + (e && e.message || e));
    if (!(e && e.user) && e && e.stack) console.error(e.stack.split('\n').slice(1, 4).join('\n'));
    return 1;
  }
}
module.exports = { boot, parseArgs, readExisting, unwrap, batchWrites, batchCalls, cmdBars, cmdTrades, cmdLevels, cmdFill, parseTrades, toJournal, fifo, readTable, findCols, parseNum, parseWhen, sideOf, rootOf,
  parseLevels, codeDe, cleanNumber, cleanTag, COLL, MAX_WRITES, MAX_BYTES, main };
if (require.main === module) process.exitCode = main(process.argv.slice(2));
