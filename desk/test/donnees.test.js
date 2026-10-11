// Tests du desk « Données & imports » : node test/donnees.test.js (sortie non nulle si échec).
// Toutes les séries sont synthétiques, à graine explicite : aucune donnée de marché n’entre ici.
const fs = require('fs'), path = require('path');
const HAS_ENGINE = fs.existsSync(path.join(__dirname, '..', 'src', 'desks', 'labo-engine.js'));
const H = require('./harness')(HAS_ENGINE ? ['quant', 'labo-engine', 'donnees'] : ['quant', 'donnees']);
const { T, ctx } = H, DN = T.lib.donnees, Q = T.lib.quant;
ctx.TextDecoder = TextDecoder; ctx.TextEncoder = TextEncoder; ctx.Blob = Blob;
let fails = 0, passes = 0;
function ok(cond, msg) { if (cond) passes++; else { fails++; console.error('ÉCHEC', msg); } }
function eq(a, b, msg) { ok(a === b, msg + ' : ' + JSON.stringify(a) + ' attendu ' + JSON.stringify(b)); }
function throws(fn, re, msg) { try { fn(); ok(false, msg + ' : aucune erreur'); } catch (e) { ok(re.test(String(e && e.message)), msg + ' : ' + (e && e.message)); } }
function section(t) { console.log('· ' + t); }
const MIN = 60000, HOUR = 3600000, DAY = 86400000;

/* mulberry32 (graine explicite) et gaussienne de Box-Muller */
function rng(seed) { let a = seed >>> 0; return function () { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
function gauss(r) { let u = 0; while (u === 0) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); }
/* Colonnes à partir de barres { t, o, h, l, c, v } */
function colsOf(bars, noVol) {
  const n = bars.length, c = { t: new Float64Array(n), o: new Float64Array(n), h: new Float64Array(n), l: new Float64Array(n), c: new Float64Array(n), v: noVol ? null : new Float64Array(n) };
  bars.forEach((b, i) => { c.t[i] = b.t; c.o[i] = b.o; c.h[i] = b.h; c.l[i] = b.l; c.c[i] = b.c; if (c.v) c.v[i] = b.v; });
  return c;
}
/* Une marche en ticks entiers, prix écrits en texte décimal puis relus (comme un CSV) : D = 1/pas. */
function walkBars(t0, n, o) {
  const r = rng(o.seed || 1), D = o.D, digits = Math.round(Math.log10(D === 4 ? 100 : D)), out = [];
  let P = o.P0 || 21000 * D;
  const txt = x => Number((x / D).toFixed(D === 4 ? 2 : digits));
  for (let i = 0; i < n; i++) {
    const Po = P + (o.gap ? Math.round(gauss(r) * o.gap) : 0), Pc = Po + Math.round(gauss(r) * (o.step || 6));
    const Ph = Math.max(Po, Pc) + 1 + Math.floor(r() * 4), Pl = Math.min(Po, Pc) - 1 - Math.floor(r() * 4);
    out.push({ t: t0 + (o.times ? o.times[i] : i) * MIN, o: txt(Po), h: txt(Ph), l: txt(Pl), c: txt(Pc), v: o.noVol ? 0 : 1 + Math.floor(r() * 50) });
    P = Pc;
  }
  return out;
}
function sameCols(a, b, fields) { const n = a.t.length; if (n !== b.t.length) return 'longueurs ' + n + ' / ' + b.t.length; for (const f of fields) for (let i = 0; i < n; i++) if (!Object.is(a[f][i], b[f][i])) return f + '[' + i + '] ' + a[f][i] + ' ≠ ' + b[f][i]; return null; }

/* Lundi 5 janvier 2026 : la séance Globex s’ouvre le dimanche 4 à 18:00 New York = 23:00 UTC. */
const MON = Date.UTC(2026, 0, 4, 23, 0);

(async function main() {
  section('Le desk et sa bibliothèque');
  {
    const d = T.desks().find(x => x.id === 'donnees');
    ok(d && d.label === 'Données & imports' && d.glyph === '⇣' && d.group === 'Système' && d.order === 85, 'id, libellé, glyphe, groupe, rang');
    eq(d && d.tabs.map(t => t.id).join(','), 'boite,series,niveaux,envoyer', 'quatre onglets');
    ['sessionKey', 'encodeSession', 'decodeSession', 'chooseD', 'splitSessions', 'fingerprint', 'quality', 'datasets', 'loadDataset', 'saveDataset', 'deleteDataset', 'levelsMap', 'inbox', 'synthetic']
      .forEach(k => ok(typeof DN[k] === 'function', 'T.lib.donnees.' + k));
    const src = fs.readFileSync(path.join(__dirname, '..', 'src', 'desks', 'donnees.js'), 'utf8');
    ok(!/#[0-9a-fA-F]{3,8}\b/.test(src.replace(/&#\d+;/g, '')), 'aucune couleur écrite en dur');
    ok(!/'[^']*\b(µ|σ)[^']*'\s*,\s*{?\s*class:\s*'dn-cap'/.test(src), 'aucune lettre grecque dans une étiquette en capitales');
  }

  section('Clé de séance Globex : changements d’heure américain et européen, ouverture du dimanche');
  {
    const k = t => DN.sessionKey(t);
    // Semaine d’hiver : dimanche 2 mars 2025, 18:00 EST = 23:00 UTC.
    eq(k(Date.UTC(2025, 2, 2, 22, 59)), '2025-03-02', '17:59 New York (hiver) : encore la clé du dimanche');
    eq(k(Date.UTC(2025, 2, 2, 23, 0)), '2025-03-03', '18:00 New York (hiver) : séance du lundi 3 mars');
    // Changement d’heure américain le dimanche 9 mars 2025 : 18:00 EDT = 22:00 UTC.
    eq(k(Date.UTC(2025, 2, 9, 21, 59)), '2025-03-09', '17:59 EDT : clé du dimanche');
    eq(k(Date.UTC(2025, 2, 9, 22, 0)), '2025-03-10', '18:00 EDT le jour du changement : séance du lundi 10 mars');
    // Semaine décalée (New York à l’heure d’été, Paris pas encore) : Globex rouvre à 23:00 Paris.
    eq(k(Date.UTC(2025, 2, 16, 22, 0)), '2025-03-17', '23:00 Paris le dimanche 16 mars : déjà la séance du lundi');
    eq(k(Date.UTC(2025, 2, 16, 23, 0)), '2025-03-17', '00:00 Paris le lundi 17 mars : même séance');
    // Changement européen le 30 mars 2025 : la clé ne dépend que de New York.
    eq(k(Date.UTC(2025, 2, 30, 22, 0)), '2025-03-31', 'changement européen : 18:00 EDT reste l’ouverture');
    eq(k(Date.UTC(2025, 9, 26, 22, 0)), '2025-10-27', 'fin de l’heure d’été européenne (26 octobre) : 18:00 EDT');
    // Fin de l’heure d’été américaine le dimanche 2 novembre 2025 : 18:00 EST = 23:00 UTC.
    eq(k(Date.UTC(2025, 10, 2, 22, 30)), '2025-11-02', '17:30 EST le 2 novembre : clé du dimanche');
    eq(k(Date.UTC(2025, 10, 2, 23, 0)), '2025-11-03', '18:00 EST le 2 novembre : séance du lundi 3');
    // Vendredi : la séance du vendredi finit à 17:00 New York.
    eq(k(Date.UTC(2025, 9, 31, 20, 59)), '2025-10-31', 'vendredi 16:59 EDT : séance du vendredi');
    eq(DN.localKey(Date.UTC(2025, 2, 9, 22, 0)), '2025-03-10', 'définition locale identique');
    if (HAS_ENGINE) {
      eq(DN.keySource(), 'moteur', 'la clé est déléguée au moteur du Labo');
      let diff = 0, n = 0;
      for (let t = Date.UTC(2024, 0, 1); t < Date.UTC(2027, 0, 1); t += HOUR - 7 * MIN) { n++; const a = T.lib.laboEngine.op('key', { t }), b = DN.localKey(t), c = DN.sessionKey(t); if (a !== b || a !== c) diff++; }
      eq(diff, 0, 'enveloppe = op key du moteur = définition locale, sur ' + n + ' instants (2024–2026)');
    }
    // Sans moteur : la définition locale prend le relais, identique.
    const H2 = require('./harness')(['quant', 'donnees']), DN2 = H2.T.lib.donnees;
    eq(DN2.keySource(), 'local', 'sans moteur : clé locale');
    let d2 = 0; for (let t = Date.UTC(2025, 0, 1); t < Date.UTC(2026, 0, 1); t += 5 * HOUR + 13 * MIN) if (DN2.sessionKey(t) !== DN.sessionKey(t)) d2++;
    eq(d2, 0, 'clé locale = clé du moteur sur 2025');
  }

  section('Découpage en séances = sessionVwap de Quant, autour des changements d’heure');
  {
    for (const [label, start] of [['mars (américain)', Date.UTC(2025, 2, 6, 20, 0)], ['mars (européen)', Date.UTC(2025, 2, 27, 20, 0)], ['novembre', Date.UTC(2025, 9, 30, 20, 0)], ['octobre (européen)', Date.UTC(2025, 9, 23, 20, 0)]]) {
      const bars = [];
      for (let t = start; t < start + 6 * DAY; t += MIN) {
        const g = T.time.globex(new Date(t)); if (!g.open) continue;
        bars.push({ t, o: 100, h: 100.25, l: 99.75, c: 100, v: 1 });
      }
      const ss = DN.splitSessions(colsOf(bars)), ref = Q.sessionVwap(bars).sessions;
      eq(JSON.stringify(ss.map(s => [s.key, s.i0, s.i1])), JSON.stringify(ref.map(s => [s.key, s.i0, s.i1])), 'séances identiques à sessionVwap, ' + label);
      ok(ss.every(s => { const p = T.time.parts('America/New_York', new Date(bars[s.i0].t)); return s.i0 === 0 || (p.h === 18 && p.m === 0); }), 'chaque séance commence à 18:00 New York, ' + label);
      ok(ss.every(s => new Date(s.key + 'T12:00:00Z').getUTCDay() !== 0 && new Date(s.key + 'T12:00:00Z').getUTCDay() !== 6), 'aucune clé un samedi ou un dimanche, ' + label);
    }
  }

  section('Séance d1 v2 : aller-retour bit pour bit (pas 0,25 · 0,01 · 0,0001)');
  {
    for (const [D, label] of [[4, '0,25'], [100, '0,01'], [10000, '0,0001']]) {
      const P0 = D === 10000 ? 10834 : 21000 * D;
      const bars = walkBars(MON, 1380, { D, seed: D, P0, step: D === 4 ? 6 : 40 });
      const cols = colsOf(bars);
      eq(DN.chooseD(cols), D, 'pas choisi pour ' + label);
      const doc = DN.encodeSession(cols, 0, cols.t.length - 1, D);
      eq(doc.key, '2026-01-05', 'clé de la séance');
      eq(doc.t0, MON, 't0 = ouverture de la première barre');
      ok(doc.m[0] === 0 && doc.dc[0] === 0 && doc.n === 1380 && doc.D === D, 'm[0] = 0, dc[0] = 0, n, D');
      ok([doc.m, doc.dc, doc.o, doc.h, doc.l, doc.vol].every(a => a.every(Number.isInteger)), 'tous les champs sont des entiers');
      ok(doc.h.every(x => x >= 0) && doc.l.every(x => x >= 0), 'h ≥ 0 et l ≥ 0 (en unités 1/D, depuis la clôture)');
      eq(doc.C0, Math.floor(cols.c[0] * D + 0.5), 'C0 = floor(c·D + 0,5)');
      const back = DN.decodeSession(JSON.parse(JSON.stringify(doc)));
      eq(sameCols(back, cols, ['t', 'o', 'h', 'l', 'c', 'v']), null, 'decode(encode(x)) === x bit pour bit, pas ' + label);
    }
    // Pas de 0,25 avec un D plus fin imposé : toujours exact.
    const cq = colsOf(walkBars(MON, 50, { D: 4, seed: 9 }));
    eq(sameCols(DN.decodeSession(DN.encodeSession(cq, 0, 49, 100)), cq, ['o', 'h', 'l', 'c']), null, 'pas 0,25 codé en 1/100 : exact aussi');
    // Refus au-delà : cinq décimales, prix ajustés par ratio.
    const c5 = colsOf(walkBars(MON, 30, { D: 4, seed: 3 })); c5.c[7] = 21000.12345;
    eq(DN.chooseD(c5), null, 'cinq décimales : aucun pas ne convient');
    throws(() => DN.encodeSession(c5, 0, 29, 10000), /non décimaux/, 'codage refusé à 1/10 000');
    const cr = colsOf(walkBars(MON, 30, { D: 4, seed: 4 })); for (let i = 0; i < 30; i++) cr.c[i] = cr.c[i] * 1.0003127;
    eq(DN.chooseD(cr), null, 'série ajustée par ratio : refusée');
    // Tolérance 1e-6 : un prix lu avec un bruit d’arrondi binaire reste accepté.
    const ct = colsOf(walkBars(MON, 10, { D: 100, seed: 5, P0: 2100000 })); ct.c[3] = 0.1 + 0.2 + 21000;
    eq(DN.chooseD(ct), 100, 'bruit d’arrondi binaire sous 1e-6 : accepté');
    // Trous de données : m porte les minutes écoulées.
    const times = [0, 1, 2, 5, 6, 30];
    const cg = colsOf(walkBars(MON, 6, { D: 4, seed: 6, times }));
    const dg = DN.encodeSession(cg, 0, 5, 4);
    eq(dg.m.join(','), '0,1,1,3,1,24', 'minutes depuis la barre précédente');
    eq(sameCols(DN.decodeSession(dg), cg, ['t']), null, 'les horodatages se reconstruisent');
  }

  section('Barres non alignées, volume absent, plus haut et plus bas réparés');
  {
    const cols = colsOf(walkBars(MON, 20, { D: 4, seed: 7 }));
    cols.t[5] += 30000; for (let i = 6; i < 20; i++) cols.t[i] += 30000;
    throws(() => DN.encodeSession(cols, 0, 19, 4), /minute/, 'une barre qui ne commence pas sur une minute entière est refusée');
    eq(DN.quality(cols).misaligned, 15, 'le rapport de qualité compte les barres non alignées');
    const nv = colsOf(walkBars(MON, 20, { D: 4, seed: 8 }), true);
    const dn = DN.encodeSession(nv, 0, 19, 4);
    eq(dn.vol, null, 'source sans volume : vol = null');
    eq(DN.decodeSession(dn).v, null, 'décodé sans volume');
    ok(JSON.stringify(dn).indexOf('"vol":null') >= 0, 'vol: null écrit dans le JSON');
    const rp = colsOf(walkBars(MON, 10, { D: 4, seed: 10 }));
    rp.h[2] = rp.c[2] - 1; rp.l[4] = rp.o[4] + 0.5;  // h < c, l > o
    const dr = DN.encodeSession(rp, 0, 9, 4);
    eq(dr.fixed, 2, 'deux barres réparées, comptées');
    ok(!('fixed' in JSON.parse(JSON.stringify(dr))), 'le compte n’est pas écrit dans la séance');
    const br = DN.decodeSession(dr);
    eq(br.h[2], Math.max(rp.o[2], rp.c[2], rp.l[2], rp.h[2]), 'h réparé = maximum des quatre prix');
    eq(br.l[4], Math.min(rp.o[4], rp.c[4], rp.h[4], rp.l[4]), 'l réparé = minimum des quatre prix');
    const bad = colsOf(walkBars(MON, 5, { D: 4, seed: 11 })); bad.t[3] = bad.t[2];
    throws(() => DN.encodeSession(bad, 0, 4, 4), /croissants/, 'horodatages non croissants refusés');
  }

  section('Empreinte : instrument|première clé|dernière clé|barres|Σ C entiers mod 2³²');
  {
    let bars = [];
    for (let d = 0; d < 300; d++) { const day = new Date(MON + d * DAY + 12 * HOUR).getUTCDay(); if (day === 6 || day === 0) continue; bars = bars.concat(walkBars(MON + d * DAY, 1380, { D: 4, seed: 100 + d, P0: 84000 + bars.length % 7 })); if (bars.length > 280000) break; }
    const cols = colsOf(bars), fp = DN.fingerprint({ instrument: 'MNQ', D: 4 }, cols);
    let s = 0n; for (let i = 0; i < cols.c.length; i++) s += BigInt(Math.floor(cols.c[i] * 4 + 0.5));
    const ss = DN.splitSessions(cols);
    eq(fp, 'MNQ|' + ss[0].key + '|' + ss[ss.length - 1].key + '|' + cols.t.length + '|' + String(s % 4294967296n), 'forme exacte, somme réduite modulo 2³² (Σ = ' + s + ')');
    ok(s > 4294967296n, 'la somme dépasse 2³² : la réduction est exercée');
    eq(DN.fingerprint({ instrument: 'MNQ', D: 4 }, colsOf(bars)), fp, 'stable : mêmes données, même empreinte');
    const docs = ss.map(x => DN.encodeSession(cols, x.i0, x.i1, 4));
    eq(DN.fingerprintDocs('MNQ', docs.slice().reverse()), fp, 'la même empreinte depuis les séances codées, dans n’importe quel ordre');
    const c2 = colsOf(bars); c2.c[1234] += 0.25; c2.h[1234] = Math.max(c2.h[1234], c2.c[1234]);
    ok(DN.fingerprint({ instrument: 'MNQ', D: 4 }, c2) !== fp, 'un tick de différence change l’empreinte');
    ok(DN.fingerprint({ instrument: 'NQ', D: 4 }, cols) !== fp, 'l’instrument entre dans l’empreinte');
    eq(DN.shortPrint(fp), DN.shortPrint(fp), 'empreinte courte stable');
    ok(/^[0-9a-z]{7}$/.test(DN.shortPrint(fp)), 'empreinte courte : sept caractères');
  }

  section('Rapport de qualité sur des défauts construits');
  {
    const r = rng(42), days = [0, 1, 2, 3], bars = [];
    let P = 84000;
    days.forEach(d => {
      const t0 = MON + d * DAY, n = d === 3 ? 300 : 1380;
      for (let i = 0; i < n; i++) {
        if (d === 1 && i >= 100 && i < 110) continue;                 // 10 minutes manquantes
        const Po = P + (d === 2 && i === 0 ? 800 : 0) + (d === 0 && i === 700 ? 400 : 0); // bascule de +200 pt à l’ouverture, saut de +100 pt en séance
        const Pc = Po + Math.round(gauss(r) * 4);
        let Ph = Math.max(Po, Pc) + 1 + Math.floor(r() * 3), Pl = Math.min(Po, Pc) - 1 - Math.floor(r() * 3);
        let o = Po / 4, c = Pc / 4, h = Ph / 4, l = Pl / 4;
        if (d === 0 && i >= 10 && i < 15) { o = h = l = c = Po / 4; }  // cinq barres plates
        bars.push({ t: t0 + i * MIN, o, h, l, c: d === 0 && i >= 10 && i < 15 ? o : c, v: d === 1 ? 0 : 1 + Math.floor(r() * 9) });
        P = d === 0 && i >= 10 && i < 15 ? Po : Pc;
      }
    });
    const q = DN.quality(colsOf(bars));
    eq(q.sessions, 4, 'quatre séances');
    eq(q.bars, bars.length, 'barres');
    eq(q.missing, 10, 'dix minutes manquantes');
    eq(q.holes, 1, 'un trou');
    ok(q.big.length === 1 && q.big[0].min === 10 && q.big[0].key === '2026-01-06', 'le trou est listé avec sa séance et sa durée');
    eq(q.flat, 5, 'cinq barres plates');
    eq(q.rollCount, 2, 'deux sauts suspects, et seulement eux');
    ok(q.rolls.some(x => x.key === '2026-01-07' && x.where === 'ouverture' && Math.abs(x.gap - 200) < 1e-9), 'la bascule de +200 points à l’ouverture du 7 janvier');
    ok(q.rolls.some(x => x.key === '2026-01-05' && x.where === 'séance' && Math.abs(x.gap - 100) < 1e-9), 'le saut de +100 points en séance');
    ok(q.short.length === 1 && q.short[0].key === '2026-01-08' && q.short[0].n === 300, 'la séance courte (300 barres < 80 % de 1 380)');
    ok(q.hasVolume && q.noVolume.length === 1 && q.noVolume[0] === '2026-01-06', 'la séance sans volume');
    eq(q.days.length, 4, 'une ligne par séance pour l’aperçu');
    ok(q.days.every(d => d.range > 0 && isFinite(d.hi) && isFinite(d.lo)), 'amplitude de chaque séance');
    // Loi nulle : une marche sans saut, avec des écarts d’ouverture gaussiens, ne porte aucun saut suspect.
    let flagged = 0, total = 0;
    for (let seed = 1; seed <= 6; seed++) {
      const rr = rng(seed * 7919), b2 = []; let p = 84000;
      for (let d = 0; d < 10; d++) for (let i = 0; i < 1380; i++) {
        const Po = p + Math.round(gauss(rr) * 1.5), Pc = Po + Math.round(gauss(rr) * 5);
        b2.push({ t: MON + d * DAY + i * MIN, o: Po / 4, h: (Math.max(Po, Pc) + 1) / 4, l: (Math.min(Po, Pc) - 1) / 4, c: Pc / 4, v: 1 }); p = Pc;
      }
      const q2 = DN.quality(colsOf(b2)); flagged += q2.rollCount; total += b2.length;
    }
    eq(flagged, 0, 'loi nulle : aucun saut suspect sur ' + total + ' barres d’une marche sans saut');
  }

  section('Un fichier JSON par année, relu bit pour bit');
  {
    // Du lundi 29 décembre 2025 au vendredi 9 janvier 2026 : deux années, dix séances.
    let bars = [], dc = Date.UTC(2025, 11, 28, 23, 0);
    for (let d = 0; d < 12; d++) { const t0 = dc + d * DAY, key = DN.sessionKey(t0), wd = new Date(key + 'T12:00:00Z').getUTCDay(); if (wd === 0 || wd === 6) continue; bars = bars.concat(walkBars(t0, 1380, { D: 4, seed: 300 + d, P0: 84000 })); }
    const cols = colsOf(bars), ss = DN.splitSessions(cols);
    eq(ss.length, 10, 'dix séances');
    const enc = DN.encodeYears(cols, { D: 4, instrument: 'MNQ', rollKeys: { '2026-01-05': true }, adj: { '2025-12-30': -12.5 } });
    eq(enc.years.map(y => y.year).join(','), '2025,2026', 'deux fichiers, un par année de clé');
    eq(enc.years[0].to, '2025-12-31', 'le premier s’arrête à la dernière séance de 2025');
    ok(enc.years.every(y => y.bytes === y.text.length && y.bytes < 20 * 1048576), 'taille connue, sous 20 Mio');
    const j0 = JSON.parse(enc.years[1].text);
    ok(j0.v === 2 && j0.instrument === 'MNQ' && j0.year === 2026 && j0.D === 4 && Array.isArray(j0.sessions), 'forme { v: 2, instrument, year, D, sessions }');
    ok(j0.sessions.find(s => s.key === '2026-01-05').roll === true, 'séance de bascule marquée roll: true');
    eq(JSON.parse(enc.years[0].text).sessions.find(s => s.key === '2025-12-30').adj, -12.5, 'ajustement arrière porté par sa séance');
    const per = 1380 * 1, size = enc.years[1].bytes / j0.sessions.length;
    ok(size < 40000, 'environ 20 Ko par séance de 1 380 barres (' + Math.round(size) + ' octets)');
    const back = DN.decodeAssets(enc.years.map(y => y.text).reverse());
    eq(sameCols(back.cols, cols, ['t', 'o', 'h', 'l', 'c', 'v']), null, 'relu bit pour bit, années dans le désordre');
    eq(back.sessions.length, 10, 'séances relues');
    ok(back.sessions.find(s => s.key === '2026-01-05').roll === true && back.sessions.find(s => s.key === '2025-12-30').adj === -12.5, 'roll et adj relus');
    const buf = new TextEncoder().encode(enc.years[0].text).buffer;
    eq(DN.decodeAssets([buf]).sessions.length, enc.years[0].sessions, 'lecture depuis un ArrayBuffer');
    throws(() => DN.decodeAssets([enc.years[0].text, enc.years[0].text]), /double/, 'séance en double refusée');
    const other = JSON.parse(enc.years[1].text); other.D = 100; other.sessions.forEach(s => { s.D = 100; });
    throws(() => DN.decodeAssets([enc.years[0].text, JSON.stringify(other)]), /pas de prix/, 'deux pas de prix différents refusés');
    throws(() => DN.decodeAssets(['{"v":1,"sessions":[]}']), /version 2/, 'version 1 refusée');
    void per;
  }

  section('Lecteur de CSV par tranches = parseCsv');
  {
    const bars = walkBars(MON, 3000, { D: 4, seed: 77 });
    const pad = n => String(n).padStart(2, '0');
    const ny = t => { const p = T.time.parts('America/New_York', new Date(t)); return p.y + '-' + pad(p.mo) + '-' + pad(p.d) + ' ' + pad(p.h) + ':' + pad(p.m); };
    const variants = {
      virgule: 'time,open,high,low,close,volume\n' + bars.map(b => [ny(b.t), b.o, b.h, b.l, b.c, b.v].join(',')).join('\n'),
      jjmm: 'Date;Time;Open;High;Low;Close;Volume\r\n' + bars.map(b => { const s = ny(b.t); return [s.slice(8, 10) + '/' + s.slice(5, 7) + '/' + s.slice(0, 4), s.slice(11), String(b.o).replace('.', ','), String(b.h).replace('.', ','), String(b.l).replace('.', ','), String(b.c).replace('.', ','), b.v].join(';'); }).join('\r\n'),
      epoch: bars.map(b => [b.t / 1000, b.o, b.h, b.l, b.c].join('\t')).join('\n')
    };
    for (const k of Object.keys(variants)) {
      const ref = Q.parseCsv(variants[k], { tz: 'America/New_York' });
      const r = DN.parseChunked(variants[k], { tz: 'America/New_York', chunk: 7919, sample: 300 });
      ok(r.chunks > 3, k + ' : lu en ' + r.chunks + ' tranches');
      eq(sameCols(r.cols, colsOf(ref.bars), ['t', 'o', 'h', 'l', 'c', 'v']), null, k + ' : mêmes colonnes que parseCsv');
      ok(r.n === ref.n && r.skipped === ref.skipped && r.sep === ref.sep && r.hasVolume === ref.hasVolume, k + ' : mêmes comptes');
    }
    const rt = DN.readText(variants.virgule, { tz: 'America/New_York', stamp: 'cloture', chunk: 10000 });
    eq(rt.cols.t[0], bars[0].t - MIN, 'horodatage de clôture : t − 60 s');
    eq(rt.D, 4, 'pas de prix déduit');
    eq(rt.sessions.length, 4, 'séances découpées (la première barre, recalée à 17:59, tombe dans la clé du dimanche)');
    eq(rt.sessions[0].i1, 0, 'une seule barre avant 18:00 New York');
  }

  section('Niveaux nommés : un document par mois');
  {
    const docs = [
      { id: '2026-01', u: 5, days: { '2026-01-05': { levels: { HVL: 21500, CR: 21650.5, PS: -3 }, scale: 'contrat', source: 'robot' }, '2026-01-06': { levels: { HVL: 21400 }, scale: 'NDX', base: 112.25 }, '2026-01-07': { levels: { CR: 21000 }, scale: 'NDX' } } },
      { id: '2026-02', u: 6, days: { '2026-02-02': { levels: { GW: 22000 }, scale: 'contrat' } } },
      { id: '2025-12', deleted: true, u: 7, days: { '2025-12-30': { levels: { X: 1 }, scale: 'contrat' } } },
      { id: 'pas-un-mois', u: 8, days: { '2026-01-05': { levels: { Y: 2 } } } }
    ];
    const r = DN.levelsFrom(docs, '2026-01-01', '2026-01-31');
    eq(JSON.stringify(r.map['2026-01-05']), JSON.stringify({ HVL: 21500, CR: 21650.5, PS: -3 }), 'échelle contrat : prix tels quels, signe moins conservé');
    eq(r.map['2026-01-06'].HVL, 21512.25, 'échelle NDX : niveau + base');
    ok(!r.map['2026-01-07'] && r.noBase.join() === '2026-01-07', 'NDX sans base : écarté et listé, jamais un NaN');
    ok(!r.map['2026-02-02'] && !r.map['2025-12-30'], 'période et documents supprimés respectés');
    eq(r.days, 2, 'deux séances lisibles');
    const col = T.ucoll('levels/items'); docs.forEach(d => col.set(d.id, d)); col.remove('2025-12');
    eq(Object.keys(DN.levelsMap('2026-01-01', '2026-12-31').map).sort().join(','), '2026-01-05,2026-01-06,2026-02-02', 'levelsMap lit la collection levels/items');
    eq(DN.levelDays().length, 4, 'une ligne par séance pour l’onglet Niveaux');
  }

  section('Boîte de réception : liens par défaut, tri, lu');
  {
    const col = T.ucoll('inbox/items');
    col.set('ib1', { at: 1000, kind: 'trades', title: 'Trades', count: 3, seen: false });
    col.set('ib2', { at: 3000, kind: 'barres', title: 'Barres', go: { sel: 'dsabc123' }, seen: false });
    col.set('ib3', { at: 2000, kind: 'strategie', title: 'S', go: { desk: 'labo', tab: 'concevoir', sel: 'sabc123_v2' }, seen: true });
    col.set('ib4', { at: 4000, kind: 'niveaux', title: 'N' });
    col.set('ib5', { at: 5000, kind: 'migration', title: 'M' });
    col.set('ib6', { at: 6000, kind: 'note', title: 'Note' });
    const it = DN.inbox();
    eq(it.map(x => x.id).join(','), 'ib6,ib5,ib4,ib2,ib3,ib1', 'du plus récent au plus ancien');
    eq(JSON.stringify(it.find(x => x.id === 'ib1').go), JSON.stringify({ desk: 'journal', tab: 'registre', sel: null }), 'trades → journal/registre');
    eq(JSON.stringify(it.find(x => x.id === 'ib2').go), JSON.stringify({ desk: 'donnees', tab: 'series', sel: 'dsabc123' }), 'barres → donnees/series, sel = jeu');
    eq(JSON.stringify(it.find(x => x.id === 'ib3').go), JSON.stringify({ desk: 'labo', tab: 'concevoir', sel: 'sabc123_v2' }), 'stratégie → labo/concevoir');
    eq(it.find(x => x.id === 'ib4').go.tab, 'niveaux', 'niveaux → donnees/niveaux');
    eq(it.find(x => x.id === 'ib5').go.tab, 'boite', 'migration → donnees/boite');
    eq(it.find(x => x.id === 'ib6').go, null, 'une note sans lien n’en invente pas');
    ok(it.every(x => typeof x.seen === 'boolean'), 'seen toujours booléen');
    await DN.markSeen('ib1');
    ok(DN.inbox().find(x => x.id === 'ib1').seen === true, 'marquer comme lu');
    col.set('ib7', { at: 7000, kind: 'note', title: 'x' }); col.remove('ib7');
    ok(!DN.inbox().some(x => x.id === 'ib7'), 'élément supprimé masqué');
  }

  section('Marche synthétique : par le moteur du Labo, jamais par une imitation');
  {
    if (HAS_ENGINE) {
      const s = DN.synthetic({ seed: 3, sessions: 4, sigma: 2 });
      ok(s.meta.source === 'synthetique' && s.meta.essais === false && s.meta.complete === true, 'source synthétique, jamais comptée dans les essais');
      eq(s.bars.t.length, 4 * 1380, 'barres');
      ok(s.bars.lowFirst && s.bars.lowFirst.length === s.bars.t.length, 'ordre intrabarre vrai (lowFirst) conservé');
      eq(s.meta.sessions, 4, 'séances');
      eq(s.meta.D, 4, 'prix au tick');
      ok(/Aucun avantage/.test(s.meta.note), 'annoncée comme telle');
      const s2 = DN.synthetic({ seed: 3, sessions: 4, sigma: 2 });
      eq(s2.meta.fingerprint, s.meta.fingerprint, 'déterministe à graine égale');
    }
    const DN2 = require('./harness')(['quant', 'donnees']).T.lib.donnees;
    throws(() => DN2.synthetic({ seed: 1 }), /[Mm]oteur indisponible/, 'sans moteur : erreur claire, aucune série de repli');
  }

  section('Écritures : reprises, quota, enregistrement et lecture d’un jeu');
  {
    DN.retryDelay = () => 1; DN.CLOUD_WAIT = 30;
    // withRetry
    let n = 0;
    const r1 = await DN.withRetry(() => { n++; if (n < 3) { const e = new Error('x'); e.code = 'unavailable'; throw e; } return 'ok'; });
    ok(r1 === 'ok' && n === 3, 'unavailable : reprises jusqu’au succès');
    n = 0; let e1 = null;
    try { await DN.withRetry(() => { n++; const e = new Error('x'); e.code = 'store_unavailable'; throw e; }); } catch (e) { e1 = e; }
    ok(e1 && n === 4, 'trois reprises au plus (' + n + ' tentatives)');
    n = 0; e1 = null;
    try { await DN.withRetry(() => { n++; const e = new Error('x'); e.code = 'quota_exceeded'; throw e; }); } catch (e) { e1 = e; }
    ok(e1 && n === 1 && /pleine/.test(DN.errorText(e1)), 'quota_exceeded : arrêt immédiat, message');

    // Sans capacité (hors de claude.ai, ou lecteur non écrivain) : refus clair.
    const cols = colsOf([].concat(walkBars(Date.UTC(2025, 11, 30, 23, 0), 1380, { D: 4, seed: 501 }), walkBars(Date.UTC(2026, 0, 4, 23, 0), 1380, { D: 4, seed: 502 })));
    let err = null; try { await DN.saveDataset({ name: 'x' }, cols); } catch (e) { err = e; }
    ok(err && err.code === 'not_writer', 'pas de capacité assets : not_writer');
    ctx.claude = { use: () => Promise.resolve(null) };
    err = null; try { await DN.saveDataset({ name: 'x' }, cols); } catch (e) { err = e; }
    ok(err && err.code === 'not_writer', 'claude.use rend null : not_writer');

    // Faux service : assets, base, utilisateur.
    const blobs = {}, writes = [], log = [];
    let uploadFail = [], seq = 0;
    const assets = {
      upload: async (blob, opt) => { log.push('upload'); const f = uploadFail.shift(); if (f) { const e = new Error(f); e.code = f; throw e; } const id = (++seq).toString(16).padStart(32, '0'); blobs[id] = await blob.text(); ok(opt && opt.type === 'application/json', 'envoi en application/json'); return { id, sizeBytes: blobs[id].length }; },
      delete: async id => { log.push('delete ' + id); delete blobs[id]; return true; },
      list: async () => ({ usage: { bytes: Object.values(blobs).reduce((a, b) => a + b.length, 0), maxBytes: 1e9, files: Object.keys(blobs).length, maxFiles: 500 } })
    };
    const db = { doc: p => ({ collection: c => ({ doc: id => ({ set: async d => { log.push('set ' + c + '/' + id + (d.deleting ? ' deleting' : '') + (d.complete ? ' complete' : '')); writes.push({ path: p + '/' + c + '/' + id, d: JSON.parse(JSON.stringify(d)) }); return true; } }) }) }) };
    ctx.claude = { use: name => Promise.resolve(name === 'assets' ? assets : name === 'db' ? db : name === 'user' ? { id: () => Promise.resolve('u_test') } : null) };
    let fetches = 0;
    ctx.fetch = async url => { fetches++; const id = String(url).replace('/_blob/', ''); if (!(id in blobs)) return { ok: false, status: 404 }; const s = blobs[id]; return { ok: true, status: 200, arrayBuffer: async () => new TextEncoder().encode(s).buffer, text: async () => s }; };

    uploadFail = ['unavailable', 'resource_exhausted'];
    const prog = [];
    const doc = await DN.saveDataset({ name: 'Essai', instrument: 'MNQ', roll: 'ajuste', stamp: 'ouverture', srcTz: 'America/New_York' }, cols, p => prog.push(p.phase));
    ok(DN.DS_ID.test(doc.id), 'identifiant de jeu ds… (' + doc.id + ')');
    ok(doc.complete === true && doc.assets.length === 2 && doc.sessions === 2 && doc.bars === 2760, 'fiche complète, deux années, deux séances');
    eq(doc.assets.map(a => a.year).join(','), '2025,2026', 'un asset par année');
    ok(doc.assets.every(a => /^[0-9a-f]{32}$/.test(a.id) && a.sessions === 1 && a.bytes > 0), 'identifiants rendus par le service');
    eq(log.filter(x => x === 'upload').length, 4, 'deux reprises sur unavailable et resource_exhausted, puis deux envois');
    const iSet = log.findIndex(x => /^set items/.test(x)), iUp = log.lastIndexOf('upload');
    ok(iSet > iUp && /complete/.test(log[iSet]), 'la fiche (complete: true) est écrite après les assets');
    ok(writes[0].path === 'data/users/u_test/datasets/items/' + doc.id, 'chemin de la fiche : data/users/<id>/datasets/items');
    eq(doc.fingerprint, DN.fingerprint({ instrument: 'MNQ', D: 4 }, cols), 'empreinte dans la fiche');
    ok(prog[0] === 'codage' && prog.indexOf('envoi') > 0 && prog[prog.length - 1] === 'fini', 'progression : codage, envoi, fiche, fini');
    eq(DN.datasets().length, 1, 'le jeu figure dans la liste');

    const ds = await DN.loadDataset(doc.id);
    eq(sameCols(ds.bars, cols, ['t', 'o', 'h', 'l', 'c', 'v']), null, 'loadDataset relit les barres bit pour bit');
    ok(ds.meta.id === doc.id && ds.sessions.length === 2 && ds.levels && typeof ds.adj === 'object', '{ meta, bars, sessions, levels, adj }');
    const f0 = fetches; await DN.loadDataset(doc.id);
    eq(fetches, f0, 'cache mémoire par u : aucune relecture');

    // Jeu incomplet : moins de séances que la fiche.
    const col = T.ucoll('datasets/items');
    col.set('dsincomplet1', Object.assign({}, col.get(doc.id), { id: 'dsincomplet1', sessions: 3 }));
    err = null; try { await DN.loadDataset('dsincomplet1'); } catch (e) { err = e; }
    ok(err && /incomplet \(2\/3\)/.test(err.message), 'séances lues ≠ fiche : « jeu incomplet (2/3) », aucun calcul');
    col.set('dssanscomplet', Object.assign({}, col.get(doc.id), { id: 'dssanscomplet', complete: false }));
    err = null; try { await DN.loadDataset('dssanscomplet'); } catch (e) { err = e; }
    ok(err && err.code === 'incomplete', 'sans complete: true, jamais lu');

    // Quota : arrêt, message, et les assets déjà envoyés sont effacés.
    const before = Object.keys(blobs).length; log.length = 0;
    uploadFail = [null, 'quota_or_state'];
    err = null; try { await DN.saveDataset({ name: 'Deux' }, cols); } catch (e) { err = e; }
    await new Promise(r => setTimeout(r, 5));
    ok(err && err.code === 'quota_or_state' && /plein/.test(DN.errorText(err)), 'stockage plein : arrêt avec message');
    eq(Object.keys(blobs).length, before, 'l’asset déjà envoyé est effacé');
    ok(!log.some(x => /^set/.test(x)), 'aucune fiche écrite');
    uploadFail = [];

    // Suppression : deleting d’abord, puis les assets, puis la fiche.
    log.length = 0;
    await DN.deleteDataset(doc.id);
    ok(/deleting/.test(log[0]), 'deleting: true posé avant tout');
    ok(log.slice(1).every(x => /^delete/.test(x)) && log.length === 3, 'puis les deux assets');
    eq(DN.datasets().filter(d => d.id === doc.id).length, 0, 'le jeu disparaît de la liste (suppression douce)');
    err = null; try { await DN.loadDataset(doc.id); } catch (e) { err = e; }
    ok(!!err, 'un jeu supprimé n’est plus lu');
    col.set('dsdeleting1', Object.assign({}, writes[0].d, { id: 'dsdeleting1', deleting: true }));
    err = null; try { await DN.loadDataset('dsdeleting1'); } catch (e) { err = e; }
    ok(err && err.code === 'deleting', 'un jeu « deleting » n’est jamais lu');

    // Compteurs
    const us = await DN.assetUsage();
    ok(us.source === 'compte' && us.files === Object.keys(blobs).length, 'taille des fichiers attachés lue sur le service');
    const du = DN.docUsage();
    ok(du.limit === 25000 && du.docs >= 0, 'documents utilisés / 25 000');
  }

  console.log((fails ? 'ÉCHEC' : 'OK') + ' — ' + passes + ' réussis, ' + fails + ' échoués');
  process.exit(fails ? 1 : 0);
})().catch(e => { console.error('ÉCHEC (exception)', e && e.stack || e); process.exit(1); });
