// Tests de l’outil d’import tools/ingest.js : node test/ingest.test.js (sortie non nulle si échec).
// Dix fichiers témoins de barres, générés ici à graine explicite (aucune donnée de marché), lus par l’outil puis
// relus depuis les fichiers d’asset : les colonnes doivent être exactement celles de T.lib.quant.parseCsv.
const fs = require('fs'), path = require('path'), os = require('os');
const ingest = require('../tools/ingest.js');
const { T, DN, Q } = ingest.boot();
let fails = 0, passes = 0;
function ok(cond, msg) { if (cond) passes++; else { fails++; console.error('ÉCHEC', msg); } }
function eq(a, b, msg) { ok(a === b, msg + ' : ' + JSON.stringify(a) + ' attendu ' + JSON.stringify(b)); }
function near(a, b, tol, msg) { ok(typeof a === 'number' && Math.abs(a - b) <= tol, msg + ' : ' + a + ' attendu ' + b); }
function throws(fn, re, msg) { try { fn(); ok(false, msg + ' : aucune erreur'); } catch (e) { ok(re.test(String(e && e.message)), msg + ' : ' + (e && e.message)); } }
function section(t) { console.log('· ' + t); }
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'alp-ingest-'));
const MIN = 60000, NY = 'America/New_York';
function rng(seed) { let a = seed >>> 0; return function () { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const pad = n => String(n).padStart(2, '0');
function nyParts(t) { const p = T.time.parts(NY, new Date(t)); return { Y: String(p.y), M: pad(p.mo), D: pad(p.d), h: pad(p.h), m: pad(p.m), s: pad(p.s) }; }
const quiet = f => { const l = console.log; console.log = () => {}; try { return f(); } finally { console.log = l; } };

/* Barres : deux séances autour du changement d’année (clés 2025-12-31 et 2026-01-02), 400 minutes chacune,
   prix au quart de point. */
function baseBars(seed) {
  const r = rng(seed), out = [];
  let P = 84000;
  [Date.UTC(2025, 11, 30, 23, 0), Date.UTC(2026, 0, 1, 23, 0)].forEach(t0 => {
    for (let i = 0; i < 400; i++) {
      const Po = P + (r() < 0.2 ? (r() < 0.5 ? 1 : -1) : 0), Pc = Po + Math.round((r() - 0.5) * 16);
      const Ph = Math.max(Po, Pc) + Math.floor(r() * 4), Pl = Math.min(Po, Pc) - Math.floor(r() * 4);
      out.push({ t: t0 + i * MIN, o: Po / 4, h: Ph / 4, l: Pl / 4, c: Pc / 4, v: 1 + Math.floor(r() * 80) });
      P = Pc;
    }
  });
  return out;
}
const dec = x => String(x).replace('.', ',');
const FIX = {
  'virgule-iso': () => 'time,open,high,low,close,volume\n' + baseBars(1).map(b => { const p = nyParts(b.t); return [p.Y + '-' + p.M + '-' + p.D + ' ' + p.h + ':' + p.m + ':' + p.s, b.o, b.h, b.l, b.c, b.v].join(','); }).join('\n'),
  'pointvirgule-decimale-jjmm': () => 'Date;Time;Ouverture;Haut;Bas;Clôture;Volume\n' + baseBars(2).map(b => { const p = nyParts(b.t); return [p.D + '/' + p.M + '/' + p.Y, p.h + ':' + p.m, dec(b.o), dec(b.h), dec(b.l), dec(b.c), b.v].join(';'); }).join('\n'),
  'tabulation-mmjj': () => 'Date\tTime\tOpen\tHigh\tLow\tClose\tVolume\n' + baseBars(3).map(b => { const p = nyParts(b.t); return [p.M + '/' + p.D + '/' + p.Y, p.h + ':' + p.m, b.o, b.h, b.l, b.c, b.v].join('\t'); }).join('\n'),
  'epoque-secondes-sans-entete': () => baseBars(4).map(b => [b.t / 1000, b.o, b.h, b.l, b.c, b.v].join(',')).join('\n'),
  'epoque-ms-pointvirgule': () => 'timestamp;open;high;low;close;volume\n' + baseBars(5).map(b => [b.t, b.o, b.h, b.l, b.c, b.v].join(';')).join('\n'),
  'doublons': () => { const B = baseBars(6), L = B.map(b => [new Date(b.t).toISOString(), b.o, b.h, b.l, b.c, b.v].join(',')); for (let k = 0; k < 20; k++) { const b = B[37 * k + 5]; L.splice(37 * k + 6 + k, 0, [new Date(b.t).toISOString(), b.o + 0.25, b.h + 0.5, b.l, b.c + 0.25, b.v + 1].join(',')); } return 'datetime,open,high,low,close,volume\n' + L.join('\n'); },
  'h-inferieur-c': () => 'time,open,high,low,close,volume\n' + baseBars(7).map((b, i) => { const p = nyParts(b.t); const h = i % 50 === 3 ? Math.min(b.o, b.c) - 0.25 : b.h, l = i % 50 === 9 ? Math.max(b.o, b.c) + 0.25 : b.l; return [p.Y + '-' + p.M + '-' + p.D + 'T' + p.h + ':' + p.m, b.o, h, l, b.c, b.v].join(','); }).join('\n'),
  'sans-volume': () => 'time,open,high,low,close\n' + baseBars(8).map(b => { const p = nyParts(b.t); return [p.Y + '-' + p.M + '-' + p.D + ' ' + p.h + ':' + p.m, b.o, b.h, b.l, b.c].join(','); }).join('\n'),
  'iso-utc-desordre': () => { const r = rng(99), L = baseBars(9).map(b => [new Date(b.t).toISOString().replace('.000', ''), b.o, b.h, b.l, b.c, b.v].join(',')); for (let i = L.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); const x = L[i]; L[i] = L[j]; L[j] = x; } return 'Date/Time,Open,High,Low,Close,Volume\n' + L.join('\n'); },
  'points-crlf-sans-entete': () => baseBars(10).map(b => { const p = nyParts(b.t); return [p.D + '.' + p.M + '.' + p.Y, p.h + ':' + p.m, b.o, b.h, b.l, b.c, b.v].join('\t'); }).join('\r\n') + '\r\n'
};
function colsOfBars(bars, vol) { const n = bars.length, c = { t: [], o: [], h: [], l: [], c: [], v: [] }; for (let i = 0; i < n; i++) { const b = bars[i]; c.t.push(b.t); c.o.push(b.o); c.h.push(b.h); c.l.push(b.l); c.c.push(b.c); c.v.push(vol ? b.v : 0); } return c; }
function sameCols(a, b, fields) { const n = a.t.length; if (n !== b.t.length) return 'longueurs ' + n + ' / ' + b.t.length; for (const f of fields) for (let i = 0; i < n; i++) if (!Object.is(a[f][i], b[f][i])) return f + '[' + i + '] ' + a[f][i] + ' ≠ ' + b[f][i]; return null; }
function readPlan(out) { return JSON.parse(fs.readFileSync(path.join(out, 'plan.json'), 'utf8')); }
function batchFiles(call) { return call.args.writes.reduce((s, w) => s + fs.statSync(w.file_path).size, 0); }

section('Barres : dix fichiers témoins, mêmes colonnes que parseCsv');
const firstBars = {};
Object.keys(FIX).forEach((name, k) => {
  const text = FIX[name](), file = path.join(TMP, name + '.csv'); fs.writeFileSync(file, text);
  const ref = Q.parseCsv(text, { tz: NY });
  ok(!ref.error && ref.n === 800, name + ' : parseCsv lit 800 barres (' + (ref.error || ref.n) + ')');
  const out = path.join(TMP, 'out-' + name);
  const res = ingest.cmdBars(file, { tz: NY, stamp: 'ouverture', instrument: 'MNQ', roll: 'inconnu', name: 'Témoin ' + name, out });
  const texts = fs.readdirSync(path.join(out, 'assets')).sort().map(f => fs.readFileSync(path.join(out, 'assets', f), 'utf8'));
  eq(texts.length, 2, name + ' : un fichier d’asset par année');
  const back = DN.decodeAssets(texts);
  eq(sameCols(back.cols, colsOfBars(ref.bars, ref.hasVolume), ['t', 'o', 'h', 'l', 'c', 'v']), null, name + ' : assets relus = colonnes de parseCsv, bit pour bit');
  const chunked = DN.parseChunked(text, { tz: NY, chunk: 2999 + k, sample: 120 });
  eq(sameCols(chunked.cols, colsOfBars(ref.bars, true), ['t', 'o', 'h', 'l', 'c', 'v']), null, name + ' : lecteur par tranches de la page = parseCsv');
  ok(chunked.dup === ref.dup && chunked.fixed === ref.fixed && chunked.skipped === ref.skipped, name + ' : mêmes doublons, réparations, lignes ignorées');
  const meta = JSON.parse(fs.readFileSync(path.join(out, 'docs', 'datasets', res.id + '.json'), 'utf8'));
  ok(/^ds[a-z0-9]{6,20}$/.test(meta.id) && meta.complete === true && meta.source === 'claude' && meta.D === 4 && meta.sessions === 2 && meta.bars === 800, name + ' : fiche du jeu');
  eq(meta.hasVolume, ref.hasVolume, name + ' : volume');
  eq(meta.fingerprint, DN.fingerprint({ instrument: 'MNQ', D: 4 }, back.cols), name + ' : empreinte = celle de la page');
  ok(meta.from === '2025-12-31' && meta.to === '2026-01-02', name + ' : clés de séance');
  firstBars[name] = { file, out, res, ref };
});
{
  const d = firstBars['doublons'].ref, h = firstBars['h-inferieur-c'].ref, nv = firstBars['sans-volume'].ref;
  eq(d.dup, 20, 'doublons : vingt horodatages en double, le dernier gardé');
  eq(h.fixed, 32, 'h < c et l > o : trente-deux barres réparées');
  ok(!nv.hasVolume, 'sans volume : aucun volume');
  const asset = JSON.parse(fs.readFileSync(path.join(firstBars['sans-volume'].out, 'assets', fs.readdirSync(path.join(firstBars['sans-volume'].out, 'assets'))[0]), 'utf8'));
  ok(asset.sessions.every(s => s.vol === null), 'sans volume : vol: null dans chaque séance');
  const jm = firstBars['tabulation-mmjj'].ref, dm = firstBars['pointvirgule-decimale-jjmm'].ref, v0 = firstBars['virgule-iso'].ref;
  eq(sameCols(colsOfBars(jm.bars, true), colsOfBars(v0.bars, true), ['t']), null, 'mm/jj et ISO lisent les mêmes instants');
  eq(sameCols(colsOfBars(dm.bars, true), colsOfBars(v0.bars, true), ['t']), null, 'jj/mm et ISO lisent les mêmes instants');
}

section('Barres : plan d’appels');
{
  const { out, res } = firstBars['virgule-iso'], plan = readPlan(out);
  const kinds = plan.calls.map(c => c.tool ? c.tool + ':' + (c.args.asset ? 'asset' : c.args.action) : 'commande');
  eq(kinds.join(','), 'Artifact:asset,Artifact:asset,commande,ArtifactData:batch,ArtifactData:batch', 'assets d’abord, puis fill, puis la fiche, puis la boîte');
  ok(plan.calls.slice(0, 2).every(c => c.args.action === 'publish' && c.args.asset === true && fs.existsSync(c.args.file_path) && c.args.url === '$URL'), 'chaque asset : Artifact publish, asset: true, fichier présent');
  const wMeta = plan.calls[3].args.writes, wIb = plan.calls[4].args.writes;
  ok(wMeta.length === 1 && wMeta[0].collection === 'data/users/me/datasets/items' && wMeta[0].doc_id === res.id && wMeta[0].op === 'set', 'fiche : data/users/me/datasets/items/<id>');
  ok(wIb.length === 1 && wIb[0].collection === 'data/users/me/inbox/items', 'élément de boîte en dernier');
  const ib = JSON.parse(fs.readFileSync(wIb[0].file_path, 'utf8'));
  ok(ib.kind === 'barres' && ib.go.desk === 'donnees' && ib.go.tab === 'series' && ib.go.sel === res.id && ib.seen === false && ib.count === 2 && ib.u > 0, 'élément de boîte : barres → donnees/series, sel = jeu');
  const meta = JSON.parse(fs.readFileSync(wMeta[0].file_path, 'utf8'));
  ok(meta.assets.every(a => /^\$asset:\d{4}$/.test(a.id)), 'avant fill : identifiants d’asset à reporter');
  throws(() => ingest.cmdFill(out, ['2025=' + 'a'.repeat(32)]), /manquant/, 'fill refuse une année sans identifiant');
  ingest.cmdFill(out, ['2025=' + 'a'.repeat(32), '2026=' + 'b'.repeat(32)]);
  const m2 = JSON.parse(fs.readFileSync(wMeta[0].file_path, 'utf8'));
  eq(m2.assets.map(a => a.id).join(','), 'a'.repeat(32) + ',' + 'b'.repeat(32), 'fill reporte les identifiants rendus');
  ok(readPlan(out).rempli === true, 'plan marqué rempli');
  throws(() => ingest.cmdFill(out, ['2025=xyz']), /hexadécimaux/, 'fill refuse un identifiant mal formé');
}

section('Barres : --existing, if_version, données déjà présentes');
{
  const { file, res } = firstBars['virgule-iso'];
  const ex = path.join(TMP, 'existant-bars'), dir = path.join(ex, 'data', 'users', 'me', 'datasets', 'items');
  fs.mkdirSync(dir, { recursive: true });
  const meta = JSON.parse(fs.readFileSync(path.join(firstBars['virgule-iso'].out, 'docs', 'datasets', res.id + '.json'), 'utf8'));
  fs.writeFileSync(path.join(dir, res.id + '.json'), JSON.stringify(meta, null, 2));
  fs.writeFileSync(path.join(ex, 'versions.json'), JSON.stringify({ [res.id]: 4 }));
  const r2 = ingest.cmdBars(file, { tz: NY, instrument: 'MNQ', out: path.join(TMP, 'out-re1'), existing: ex });
  eq(r2.plan.status, 'deja-present', 'données identiques déjà complètes : rien à écrire');
  eq(r2.plan.calls.length, 0, 'aucun appel');
  // Import interrompu : même identifiant, fiche incomplète → réécrite, épinglée par if_version.
  fs.writeFileSync(path.join(dir, res.id + '.json'), JSON.stringify({ doc_id: res.id, version: 7, data: Object.assign({}, meta, { complete: false, assets: [{ year: 2025, id: 'c'.repeat(32) }] }) }));
  const r3 = ingest.cmdBars(file, { tz: NY, instrument: 'MNQ', out: path.join(TMP, 'out-re2'), existing: ex });
  const call = r3.plan.calls.find(c => c.tool === 'ArtifactData' && c.args.writes[0].collection.endsWith('datasets/items'));
  eq(call && call.args.writes[0].if_version, 7, 'document existant épinglé par if_version (version lue dans l’enveloppe)');
  ok(r3.plan.cleanup.length === 1 && r3.plan.cleanup[0].args.path === 'c'.repeat(32), 'l’ancien asset est listé pour effacement après écriture');
  const r4 = ingest.cmdBars(file, { tz: NY, instrument: 'MNQ', out: path.join(TMP, 'out-re3'), existing: ex, force: true });
  ok(r4.plan.calls.length === 5, '--force réimporte');
  // Refus : barres non alignées, prix non décimaux.
  const bad = path.join(TMP, 'non-alignees.csv');
  fs.writeFileSync(bad, 'time,open,high,low,close\n2026-01-05 10:00:30,1,1,1,1\n2026-01-05 10:01:30,1,1,1,1\n');
  throws(() => ingest.cmdBars(bad, { tz: NY, out: path.join(TMP, 'out-bad') }), /minutes entières/, 'barres non alignées : import refusé');
  const rat = path.join(TMP, 'ratio.csv');
  fs.writeFileSync(rat, 'time,open,high,low,close\n2026-01-05 10:00,21000.123456,21001.5,20999.5,21000.25\n');
  throws(() => ingest.cmdBars(rat, { tz: NY, out: path.join(TMP, 'out-rat') }), /non décimaux/, 'prix non décimaux : import refusé');
  // Horodatage de clôture : t − 60 s.
  const rc = ingest.cmdBars(file, { tz: NY, stamp: 'cloture', instrument: 'MNQ', out: path.join(TMP, 'out-cl') });
  const tx = fs.readdirSync(path.join(TMP, 'out-cl', 'assets')).sort().map(f => fs.readFileSync(path.join(TMP, 'out-cl', 'assets', f), 'utf8'));
  eq(DN.decodeAssets(tx).cols.t[0], firstBars['virgule-iso'].ref.bars[0].t - MIN, 'stamp cloture : la barre est datée de son ouverture');
  void rc;
}

section('Lots ArtifactData : ≤ 50 écritures et ≤ 900 Ko');
{
  const w = []; for (let i = 0; i < 137; i++) w.push({ collection: 'c', doc_id: 'd' + i, bytes: 1000 });
  const b1 = ingest.batchWrites(w);
  ok(b1.length === 3 && b1.every(b => b.writes.length <= 50), '137 petites écritures : trois lots de 50 au plus');
  const w2 = []; for (let i = 0; i < 30; i++) w2.push({ collection: 'c', doc_id: 'g' + i, bytes: 100 * 1024 });
  const b2 = ingest.batchWrites(w2);
  ok(b2.every(b => b.bytes <= ingest.MAX_BYTES && b.writes.length <= 50), 'lots de 100 Ko : 900 Ko au plus par lot');
  eq(b2.reduce((s, b) => s + b.writes.length, 0), 30, 'aucune écriture perdue');
  eq(b2[0].writes.length, 8, 'huit documents de 100 Ko par lot (marge comprise)');
  throws(() => ingest.batchWrites([{ doc_id: 'x', bytes: 950 * 1024 }]), /trop gros/, 'un document de plus de 900 Ko est refusé');
}

section('Trades : exécutions appariées FIFO, sans stop inventé');
const FILLS = ['Symbol,B/S,Qty,Avg Fill Price,Fill Time,Status,Commission',
  'MNQZ5,Buy,2,21000.00,11/03/2025 10:00:00,Filled,1.24',
  'MNQZ5,Buy,1,21002.00,11/03/2025 10:01:00,Filled,0.62',
  'MNQZ5,Sell,2,21005.00,11/03/2025 10:05:00,Filled,1.24',
  'MNQZ5,Sell,2,21001.00,11/03/2025 10:07:00,Filled,1.24',
  'MNQZ5,Buy,1,20999.00,11/03/2025 10:09:00,Filled,0.62',
  'MNQZ5,Buy,3,21010.00,11/03/2025 10:10:00,Cancelled,0',
  'MNQZ5,Sell,1,21020.00,11/13/2025 10:11:00,Filled,0.62'];
{
  const f = path.join(TMP, 'fills.csv'); fs.writeFileSync(f, FILLS.join('\n'));
  const out = path.join(TMP, 'out-trades');
  const r = ingest.cmdTrades(f, { tz: NY, instrument: 'MNQ', out });
  eq(r.parsed.order, 'mdy', 'ordre des dates : mois/jour (le 13 le décide)');
  eq(r.entries.length, 3, 'trois allers-retours');
  const e = r.entries;
  ok(e[0].side === 'long' && e[0].qty === 2 && e[0].entry === 21000 && e[0].exit === 21005, 'premier : 2 achetés à 21 000, vendus à 21 005');
  near(e[0].pnl, 17.52, 1e-9, 'P&L net : 5 pt × 2 $ × 2 − 2,48 $');
  ok(e[1].side === 'long' && e[1].qty === 1 && e[1].entry === 21002 && e[1].exit === 21001, 'deuxième : le lot restant (FIFO), vendu à 21 001');
  near(e[1].pnl, -3.24, 1e-9, 'P&L net du deuxième');
  ok(e[2].side === 'short' && e[2].qty === 1 && e[2].entry === 21001 && e[2].exit === 20999, 'troisième : le surplus vendu ouvre une vente, rachetée à 20 999');
  near(e[2].pnl, 2.76, 1e-9, 'P&L net du troisième');
  eq(e[0].at, Date.UTC(2025, 10, 3, 15, 0), 'heure d’entrée : 10:00 New York = 15:00 UTC');
  eq(e[0].closedAt, Date.UTC(2025, 10, 3, 15, 5), 'heure de sortie');
  ok(e.every(x => x.kind === 'pris' && x.status === 'clos' && x.src === 'import' && x.instrument === 'MNQ' && x.imp && x.imp.file === 'fills.csv'), 'schéma du journal + src: import, imp');
  ok(e.every(x => !('stop' in x) && !('r' in x)), 'aucun stop inventé, donc aucun R');
  ok(e.every(x => /^i[0-9a-z]{13}$/.test(x.id)), 'identifiants dérivés du contenu');
  eq(r.open.length, 1, 'la vente encore ouverte en fin de fichier n’est pas importée');
  ok(r.parsed.skipped.length === 1 && /non exécuté/.test(r.parsed.skipped[0].why), 'l’ordre annulé est écarté');
  const plan = readPlan(out);
  eq(plan.calls.length, 2, 'un lot de trades puis l’élément de boîte');
  ok(plan.calls[0].args.writes.every(w => w.collection === 'data/users/me/journal/trades' && !w.if_version), 'trades : data/users/me/journal/trades, créations');
  const ib = JSON.parse(fs.readFileSync(plan.calls[1].args.writes[0].file_path, 'utf8'));
  ok(ib.kind === 'trades' && ib.count === 3 && ib.go.desk === 'journal' && ib.go.tab === 'registre', 'boîte : trades → journal/registre');
  // Identifiants stables, second import sans doublon.
  const again = ingest.cmdTrades(f, { tz: NY, instrument: 'MNQ', out: path.join(TMP, 'out-trades-2') });
  eq(again.entries.map(x => x.id).join(), e.map(x => x.id).join(), 'mêmes identifiants à la seconde lecture');
  const ex = path.join(TMP, 'existant-trades'), dir = path.join(ex, 'data', 'users', 'me', 'journal', 'trades');
  fs.mkdirSync(dir, { recursive: true });
  e.forEach(x => fs.writeFileSync(path.join(dir, x.id + '.json'), JSON.stringify(Object.assign({}, x, { note: 'annoté par l’utilisateur' }), null, 2)));
  const r2 = ingest.cmdTrades(f, { tz: NY, instrument: 'MNQ', out: path.join(TMP, 'out-trades-3'), existing: ex });
  ok(r2.fresh.length === 0 && r2.kept === 3 && r2.plan.calls.length === 0, 'second import : rien n’est réécrit, aucune boîte');
  const f2 = path.join(TMP, 'fills-plus.csv'); fs.writeFileSync(f2, FILLS.concat(['MNQZ5,Buy,1,21015.00,11/13/2025 10:20:00,Filled,0.62']).join('\n'));
  const r3 = ingest.cmdTrades(f2, { tz: NY, instrument: 'MNQ', out: path.join(TMP, 'out-trades-4'), existing: ex });
  ok(r3.fresh.length === 1 && r3.kept === 3, 'fichier prolongé : seul le nouveau trade est écrit');
  ok(r3.fresh[0].side === 'short' && r3.fresh[0].entry === 21020 && r3.fresh[0].exit === 21015, 'la vente ouverte se referme au second fichier');
}

section('Trades : allers-retours, alias d’en-têtes, P&L du fichier');
{
  const RT = ['Entry Time;Exit Time;Side;Qty;Entry Price;Exit Price;P&L;Commission',
    '03/11/2025 10:00;03/11/2025 10:05;Long;2;21000,00;21005,00;20,00;2,48',
    '25/11/2025 15:30;25/11/2025 15:42;Short;1;21100,50;21102,50;-5,24;1,24',
    '26/11/2025 09:00;26/11/2025 09:10;;1;21000;21004;8,00;1,24'];
  const f = path.join(TMP, 'trades-rt.csv'); fs.writeFileSync(f, RT.join('\n'));
  const r = ingest.cmdTrades(f, { tz: 'Europe/Paris', instrument: 'MNQ', out: path.join(TMP, 'out-rt') });
  eq(r.parsed.fmt, 'allers-retours', 'format reconnu : une ligne par trade');
  eq(r.parsed.order, 'dmy', 'jour/mois (le 25 le décide)');
  eq(r.entries.length, 3, 'trois trades');
  near(r.entries[0].pnl, 17.52, 1e-9, 'P&L brut du fichier : commission retirée');
  near(r.entries[1].pnl, -5.24, 1e-9, 'P&L net du fichier : gardé');
  ok(r.entries[1].side === 'short', 'vente');
  ok(r.entries[2].side === 'long', 'sens déduit du P&L et des prix quand la colonne est vide');
  eq(r.entries[0].at, Date.UTC(2025, 10, 3, 9, 0), '10:00 Paris = 09:00 UTC');
  const sg = path.join(TMP, 'signed.csv');
  fs.writeFileSync(sg, 'Contract,Quantity,Price,Timestamp\nNQH6,1,21000.25,2026-01-05T15:00:00Z\nNQH6,-1,21010.25,2026-01-05T15:30:00Z\n');
  const r2 = ingest.cmdTrades(sg, { tz: NY, instrument: 'MNQ', out: path.join(TMP, 'out-sg'), commission: '4.5' });
  ok(r2.entries.length === 1 && r2.entries[0].instrument === 'NQ' && r2.entries[0].side === 'long', 'quantité signée → sens ; symbole NQH6 → NQ');
  near(r2.entries[0].pnl, 10 * 20 - 4.5, 1e-9, 'valeur du point du NQ (20 $) et --commission');
  throws(() => ingest.parseTrades('a,b,c\n1,2,3\n', { tz: NY }), /Colonnes introuvables/, 'en-têtes inconnus : refus avec la liste lue');
  eq(ingest.sideOf('Achat'), 1, 'Achat → +1'); eq(ingest.sideOf('SLD'), -1, 'SLD → −1'); eq(ingest.sideOf('?'), 0, 'inconnu → 0');
  eq(ingest.parseNum('(1 234,50)', true), -1234.5, 'nombre entre parenthèses : négatif, virgule décimale');
  eq(ingest.parseNum('1,234.50'), 1234.5, 'séparateur de milliers américain');
  eq(ingest.parseNum('−12,5', true), -12.5, 'vrai signe moins');
}

section('Niveaux : collage « NOM : prix »');
{
  const paste = ['## Levels', 'HVL : 21450.25', 'Call Resistance: 21,600.00', 'Put Support : 21 300,50', '21500 = Max Pain', 'Gamma Wall | 21700', 'Mise à jour : 2025', 'Zéro : 0', '**Major Wall**: 21800', '## Context', 'horizon: 0 dte', 'updated: 10:30'].join('\n');
  const p = ingest.parseLevels(paste, {});
  eq(p.prefix, '0', 'échéance lue dans ## Context');
  eq(JSON.stringify(p.levels), JSON.stringify({ '0HVL': 21450.25, '0CR': 21600, '0PS': 21300.5, '0MP': 21500, '0GW': 21700, '0GW2': 21800 }), 'codes courts, préfixe d’échéance, virgule décimale et séparateur de milliers');
  ok(p.rejected.some(x => /2025/.test(x.text)) && p.rejected.some(x => /Zéro/.test(x.text)), 'un millésime et un zéro écartés par la fenêtre de plausibilité');
  ok(!p.rejected.some(x => /10:30/.test(x.text)) && !Object.values(p.levels).includes(10), 'la section de contexte n’est pas lue comme des niveaux');
  const neg = ingest.parseLevels('Delta : -120.5\nX : −118\nY = -121.25', {});
  eq(JSON.stringify(neg.levels), JSON.stringify({ DELTA: -120.5, X: -118, Y: -121.25 }), 'le signe moins est conservé');
  const f = path.join(TMP, 'niveaux.txt'); fs.writeFileSync(f, paste);
  const ex = path.join(TMP, 'existant-niveaux'), dir = path.join(ex, 'data', 'users', 'me', 'levels', 'items');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, '2026-01.json'), JSON.stringify({ id: '2026-01', u: 5, days: { '2026-01-05': { levels: { HVL: 1 }, scale: 'contrat' }, '2026-01-02': { levels: { CR: 21000 }, scale: 'contrat' } } }));
  fs.writeFileSync(path.join(ex, 'versions.json'), JSON.stringify({ '2026-01': 12 }));
  const r = ingest.cmdLevels(f, { date: '2026-01-05', scale: 'NDX', base: '112,5', out: path.join(TMP, 'out-niv'), existing: ex });
  ok(r.doc.id === '2026-01' && r.doc.u > 5, 'document du mois, u supérieur au u lu');
  ok(r.doc.days['2026-01-02'].levels.CR === 21000, 'les autres séances du mois sont gardées');
  ok(r.doc.days['2026-01-05'].scale === 'NDX' && r.doc.days['2026-01-05'].base === 112.5 && r.doc.days['2026-01-05'].levels['0HVL'] === 21450.25, 'séance remplacée : échelle, base, niveaux');
  ok(r.plan.warnings.some(w => /remplacés/.test(w)), 'le remplacement est signalé');
  eq(r.plan.calls[0].args.writes[0].if_version, 12, 'mois existant épinglé par if_version');
  ok(r.plan.calls[r.plan.calls.length - 1].args.writes[0].collection === 'data/users/me/inbox/items', 'élément de boîte en dernier');
  const lv = DN.levelsFrom([r.doc], '2026-01-01', '2026-01-31');
  eq(lv.map['2026-01-05']['0HVL'], 21450.25 + 112.5, 'la page lit niveau + base');
  const r2 = ingest.cmdLevels(f, { date: '2026-01-06', scale: 'NDX', out: path.join(TMP, 'out-niv2') });
  ok(r2.plan.warnings.some(w => /sans --base/.test(w)), 'NDX sans base : avertissement');
  throws(() => ingest.cmdLevels(f, { date: '06/01/2026', out: path.join(TMP, 'x') }), /AAAA-MM-JJ/, 'date au mauvais format refusée');
}

section('Documents existants : enveloppes lues');
{
  eq(ingest.unwrap({ doc_id: 'a', version: 3, data: { id: 'a', x: 1 } }).version, 3, '{ doc_id, version, data }');
  eq(ingest.unwrap({ id: 'a', __version__: 2 }).version, 2, '__version__');
  eq(ingest.unwrap({ id: 'a', x: 1 }).version, null, 'document nu : version inconnue');
}

section('Ligne de commande');
{
  const code = quiet(() => ingest.main(['levels', path.join(TMP, 'niveaux.txt'), '--date', '2026-01-07', '--scale', 'contrat', '--out', path.join(TMP, 'out-cli')]));
  eq(code, 0, 'levels en ligne de commande');
  ok(fs.existsSync(path.join(TMP, 'out-cli', 'plan.json')), 'plan.json écrit');
  const el = console.error; console.error = () => {};
  const bad = ingest.main(['bars', path.join(TMP, 'absent.csv'), '--out', path.join(TMP, 'o')]); console.error = el;
  eq(bad, 1, 'fichier absent : code 1');
  eq(quiet(() => ingest.main(['inconnu'])), 2, 'commande inconnue : usage, code 2');
}

fs.rmSync(TMP, { recursive: true, force: true });
console.log((fails ? 'ÉCHEC' : 'OK') + ' — ' + passes + ' réussis, ' + fails + ' échoués');
process.exit(fails ? 1 : 0);
