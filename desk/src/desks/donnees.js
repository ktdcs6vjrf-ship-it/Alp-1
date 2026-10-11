/* Desk « Données & imports » : la boîte de réception de ce que Claude écrit, les jeux de barres d’une minute
   (codage des séances, rapport de qualité, aperçu, suppression), la lecture d’un CSV local par tranches dans un
   worker, les niveaux nommés par séance, et ce qu’il faut envoyer à Claude. Contrat : LABO.md, §2.0–2.3, 2.7,
   2.9, 7. Aucune donnée de marché n’est écrite ici : tout vient d’un fichier de l’utilisateur, de Claude, ou
   d’une marche sans dérive annoncée comme telle.
   Lois nulles : le rapport de qualité marque un « saut suspect » au-delà de 8 écarts-types robustes
   (1,4826 × écart absolu médian) ; sous une loi normale, |Z| > 8 arrive avec une probabilité de 1,2 × 10⁻¹⁵,
   et test/donnees.test.js vérifie qu’aucune marche sans saut n’en porte. */
var h = T.h, U = T.ui, C = T.chart, F = T.fmt;
T.lib = T.lib || {};
var DN = T.lib.donnees = {};
function fin(v) { return typeof v === 'number' && isFinite(v); }

/* =====================================================================
   1. Le cœur : une seule fonction autonome (aucune variable extérieure),
      exécutée dans un worker ou appelée telle quelle par la page et les tests.
   ===================================================================== */
function donneesWorker(a) {
  var NY = 'America/New_York', MIN = 60000, HOUR = 3600000, EPS = 1e-6, M32 = 4294967296;
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function isNum(v) { return typeof v === 'number' && isFinite(v); }
  function noop() {}

  /* ---- Fuseaux (même calcul que quantEngine.off) : un cache par heure UTC est exact pour New York. ---- */
  var OFF = {}, FMT = {};
  function off(tz, t) {
    if (!tz || tz === 'UTC') return 0;
    var hr = Math.floor(t / HOUR), k = tz + '|' + hr, v = OFF[k];
    if (v !== undefined) return v;
    var f = FMT[tz]; if (!f) f = FMT[tz] = new Intl.DateTimeFormat('en-US', { timeZone: tz, hourCycle: 'h23', year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric', second: 'numeric' });
    var o = {}, ps = f.formatToParts(new Date(hr * HOUR)); for (var i = 0; i < ps.length; i++) o[ps[i].type] = ps[i].value;
    v = Date.UTC(+o.year, +o.month - 1, +o.day, (+o.hour) % 24, +o.minute, +o.second) - hr * HOUR;
    OFF[k] = v; return v;
  }
  /* Clé de séance Globex (LABO.md 2.1, code de sessionVwap) : date UTC de t + décalage(New York, t) + 6 h.
     La séance du lundi commence le dimanche à 18 h 00 New York. */
  function keyAt(t) { var s = new Date(t + off(NY, t) + 6 * HOUR); return s.getUTCFullYear() + '-' + pad(s.getUTCMonth() + 1) + '-' + pad(s.getUTCDate()); }
  /* La clé ne change qu’à 18 h 00 New York, une heure pleine UTC : elle est constante dans chaque heure UTC. */
  function hourly(fn) { var c = {}; return function (t) { var hr = Math.floor(t / HOUR), k = c[hr]; if (k === undefined) { k = fn(hr * HOUR); c[hr] = k; } return k; }; }
  var localKey = hourly(keyAt);
  function K(kf) { return typeof kf === 'function' ? hourly(kf) : localKey; }

  function split(t, kf) {
    var key = K(kf), out = [], cur = null, n = t.length;
    for (var i = 0; i < n; i++) { var k = key(t[i]); if (k !== cur) { out.push({ key: k, i0: i, i1: i }); cur = k; } else out[out.length - 1].i1 = i; }
    return out;
  }

  /* ---- Prix entiers : P = floor(p·D + 0,5), D = le plus petit de (1/tick, 100, 10 000) qui rend tous les prix entiers à 1e-6. ---- */
  function dCands(tick) {
    var inv = tick > 0 ? 1 / tick : 4, r = Math.round(inv), c = [];
    if (Math.abs(inv - r) < 1e-9 && r >= 1) c.push(r);
    [100, 10000].forEach(function (d) { if (c.indexOf(d) < 0) c.push(d); });
    return c.sort(function (x, y) { return x - y; });
  }
  function fits(x, D) { var y = x * D, p = Math.floor(y + 0.5); return Math.abs(y - p) <= EPS; }
  function chooseD(cols, tick) {
    var ds = dCands(tick || 0.25), n = cols.t.length, P4 = [cols.o, cols.h, cols.l, cols.c];
    for (var k = 0; k < ds.length; k++) {
      var D = ds[k], ok = true;
      for (var f = 0; f < 4 && ok; f++) { var x = P4[f]; for (var i = 0; i < n; i++) if (!fits(x[i], D)) { ok = false; break; } }
      if (ok) return D;
    }
    return null;
  }
  function intP(x, D) {
    var y = x * D, p = Math.floor(y + 0.5);
    if (!(Math.abs(y - p) <= EPS)) throw new Error('Prix non décimaux au pas 1/' + D + ' (' + x + ') : série ajustée par ratio ?');
    return p;
  }
  function iso(t) { try { return new Date(t).toISOString().slice(0, 19).replace('T', ' ') + ' UTC'; } catch (e) { return String(t); } }

  /* ---- Séance d1 v2 (LABO.md 2.1) ---- */
  function encode(cols, i0, i1, D, k0, kf) {
    if (!(D >= 1) || Math.floor(D) !== D) throw new Error('Pas de prix invalide : ' + D + '.');
    if (!(i1 >= i0) || i0 < 0 || i1 >= cols.t.length) throw new Error('Séance vide ou hors des barres.');
    var n = i1 - i0 + 1, t = cols.t, V = cols.v || null;
    var m = new Array(n), dc = new Array(n), oo = new Array(n), hh = new Array(n), ll = new Array(n), vol = V ? new Array(n) : null;
    var fixed = 0, C0 = 0, prevC = 0, prevT = 0;
    for (var k = 0; k < n; k++) {
      var i = i0 + k, ti = t[i];
      if (!(ti % MIN === 0)) throw new Error('Barre non alignée sur la minute : ' + iso(ti) + '. Chaque barre doit commencer sur une minute entière.');
      if (k) { var dm = (ti - prevT) / MIN; if (!(dm >= 1)) throw new Error('Horodatages non croissants à ' + iso(ti) + '.'); m[k] = dm; } else m[k] = 0;
      prevT = ti;
      var Po = intP(cols.o[i], D), Ph = intP(cols.h[i], D), Pl = intP(cols.l[i], D), Pc = intP(cols.c[i], D);
      var H = Math.max(Ph, Po, Pc, Pl), L = Math.min(Pl, Po, Pc, Ph);
      if (H !== Ph || L !== Pl) fixed++;
      if (k) dc[k] = Pc - prevC; else { C0 = Pc; dc[0] = 0; }
      prevC = Pc; oo[k] = Po - Pc; hh[k] = H - Pc; ll[k] = Pc - L;
      if (vol) { var v = V[i]; vol[k] = v > 0 && isFinite(v) ? Math.round(v) : 0; }
    }
    var doc = { key: k0 || K(kf)(t[i0]), t0: t[i0], n: n, D: D, C0: C0, m: m, dc: dc, o: oo, h: hh, l: ll, vol: vol };
    Object.defineProperty(doc, 'fixed', { value: fixed, enumerable: false, writable: true });
    return doc;
  }
  function checkDoc(d) {
    if (!d || !(d.n >= 1) || !(d.D >= 1) || !isNum(d.t0) || !isNum(d.C0)) throw new Error('Séance illisible' + (d && d.key ? ' (' + d.key + ')' : '') + '.');
    ['m', 'dc', 'o', 'h', 'l'].forEach(function (f) { if (!d[f] || d[f].length !== d.n) throw new Error('Séance ' + d.key + ' : champ ' + f + ' incomplet.'); });
    if (d.vol && d.vol.length !== d.n) throw new Error('Séance ' + d.key + ' : volume incomplet.');
  }
  /* Décodage : la division d’un entier par D rend le même double que la lecture du texte décimal. */
  function decodeInto(d, c, at) {
    var D = d.D, Cc = d.C0, tt = d.t0;
    for (var k = 0; k < d.n; k++) {
      if (k) tt += MIN * d.m[k];
      Cc += d.dc[k];
      var j = at + k;
      c.t[j] = tt; c.c[j] = Cc / D; c.o[j] = (Cc + d.o[k]) / D; c.h[j] = (Cc + d.h[k]) / D; c.l[j] = (Cc - d.l[k]) / D;
      if (c.v) c.v[j] = d.vol ? d.vol[k] : 0;
    }
  }
  function decode(d) {
    checkDoc(d);
    var n = d.n, c = { t: new Float64Array(n), o: new Float64Array(n), h: new Float64Array(n), l: new Float64Array(n), c: new Float64Array(n), v: d.vol ? new Float64Array(n) : null };
    decodeInto(d, c, 0);
    c.key = d.key; c.n = n; c.D = d.D;
    if (d.roll) c.roll = true; if (isNum(d.adj)) c.adj = d.adj; if (d.contract) c.contract = d.contract;
    return c;
  }
  function decodeAssets(list) {
    var docs = [], D = null, inst = null, years = [], seen = {};
    (list || []).forEach(function (x) {
      var s = typeof x === 'string' ? x : (typeof TextDecoder !== 'undefined' ? new TextDecoder('utf-8').decode(x instanceof ArrayBuffer ? new Uint8Array(x) : x) : String(x));
      var j; try { j = JSON.parse(s); } catch (e) { throw new Error('Fichier de barres illisible (JSON invalide).'); }
      if (!j || j.v !== 2 || !Array.isArray(j.sessions)) throw new Error('Fichier de barres illisible : version 2 attendue.');
      if (D === null) D = j.D; else if (j.D !== D) throw new Error('Deux années n’ont pas le même pas de prix (1/' + D + ' et 1/' + j.D + ').');
      inst = inst || j.instrument || null; years.push(j.year);
      j.sessions.forEach(function (d) {
        checkDoc(d);
        if (d.D !== j.D) throw new Error('Séance ' + d.key + ' : pas de prix différent de son fichier.');
        if (seen[d.key]) throw new Error('Séance en double : ' + d.key + '.');
        seen[d.key] = 1; docs.push(d);
      });
    });
    docs.sort(function (x, y) { return x.t0 - y.t0; });
    var N = 0, anyV = false; docs.forEach(function (d) { N += d.n; if (d.vol) anyV = true; });
    var c = { t: new Float64Array(N), o: new Float64Array(N), h: new Float64Array(N), l: new Float64Array(N), c: new Float64Array(N), v: new Float64Array(N) }, at = 0, sessions = [];
    docs.forEach(function (d) {
      decodeInto(d, c, at);
      if (at && c.t[at] <= c.t[at - 1]) throw new Error('Séances qui se chevauchent autour de ' + d.key + '.');
      var s = { key: d.key, i0: at, i1: at + d.n - 1 };
      if (d.roll) s.roll = true; if (isNum(d.adj)) s.adj = d.adj; if (d.contract) s.contract = d.contract;
      sessions.push(s); at += d.n;
    });
    return { cols: c, sessions: sessions, D: D, instrument: inst, n: N, hasVolume: anyV, years: years };
  }

  /* ---- Empreinte : instrument|première clé|dernière clé|barres|somme des C entiers mod 2³² ---- */
  function fpOf(instrument, cols, D, kf) {
    var n = cols.t.length, key = K(kf), s = 0;
    for (var i = 0; i < n; i++) { s = (s + Math.floor(cols.c[i] * D + 0.5)) % M32; if (s < 0) s += M32; }
    return String(instrument || '') + '|' + (n ? key(cols.t[0]) : '') + '|' + (n ? key(cols.t[n - 1]) : '') + '|' + n + '|' + s;
  }
  function fpDocs(instrument, docs) {
    var ds = docs.slice().sort(function (x, y) { return x.t0 - y.t0; }), s = 0, n = 0;
    ds.forEach(function (d) { var Cc = d.C0; for (var k = 0; k < d.n; k++) { Cc += d.dc[k]; s = (s + Cc) % M32; if (s < 0) s += M32; } n += d.n; });
    return String(instrument || '') + '|' + (ds.length ? ds[0].key : '') + '|' + (ds.length ? ds[ds.length - 1].key : '') + '|' + n + '|' + s;
  }

  /* ---- Rapport de qualité ---- */
  function med(s, n) { return n % 2 ? s[(n - 1) / 2] : 0.5 * (s[n / 2 - 1] + s[n / 2]); }
  function mad(x, n) {
    if (!n) return NaN;
    var s = x.slice(0, n); s.sort(); var m0 = med(s, n);
    for (var i = 0; i < n; i++) s[i] = Math.abs(s[i] - m0);
    s.sort(); return med(s, n);
  }
  function quality(cols, o, kf) {
    o = o || {};
    var t = cols.t, n = t.length, O = cols.o, Hh = cols.h, Ll = cols.l, Cc = cols.c, V = cols.v || null, tick = o.tick || 0.25, EXP = o.expected || 1380;
    var ss = o.sessions || split(t, kf), i, s;
    var hasV = false; if (V) for (i = 0; i < n; i++) if (V[i] > 0) { hasV = true; break; }
    var q = { sessions: ss.length, bars: n, from: ss.length ? ss[0].key : null, to: ss.length ? ss[ss.length - 1].key : null, expected: EXP, hasVolume: hasV,
      misaligned: 0, unordered: 0, flat: 0, flatShare: 0, missing: 0, holes: 0, big: [], bigCount: 0, short: [], noVolume: [], rolls: [], rollCount: 0, days: [] };
    var dcs = new Float64Array(Math.max(1, n)), nd = 0, gb = new Float64Array(Math.max(1, ss.length)), nb = 0;
    for (s = 0; s < ss.length; s++) {
      var S0 = ss[s], hi = -Infinity, lo = Infinity, vs = 0, miss = 0;
      for (i = S0.i0; i <= S0.i1; i++) {
        if (t[i] % MIN !== 0) q.misaligned++;
        if (i > S0.i0) {
          var dt = t[i] - t[i - 1];
          if (dt <= 0) q.unordered++;
          else if (dt > MIN) { var mm = Math.round(dt / MIN) - 1; if (mm > 0) { miss += mm; q.holes++; if (mm >= 5) q.big.push({ key: S0.key, t: t[i - 1] + MIN, min: mm }); } }
          dcs[nd++] = Cc[i] - Cc[i - 1];
        }
        if (O[i] === Hh[i] && Hh[i] === Ll[i] && Ll[i] === Cc[i]) q.flat++;
        if (Hh[i] > hi) hi = Hh[i]; if (Ll[i] < lo) lo = Ll[i];
        if (V && V[i] > 0) vs += V[i];
      }
      var cnt = S0.i1 - S0.i0 + 1;
      q.missing += miss;
      if (cnt < 0.8 * EXP) q.short.push({ key: S0.key, n: cnt });
      if (hasV && !(vs > 0)) q.noVolume.push(S0.key);
      if (s > 0) gb[nb++] = O[S0.i0] - Cc[ss[s - 1].i1];
      q.days.push({ key: S0.key, t0: t[S0.i0], n: cnt, hi: hi, lo: lo, range: hi - lo, open: O[S0.i0], close: Cc[S0.i1], vol: vs, missing: miss });
    }
    /* Échelles robustes : variation d’une minute dans la séance, écart d’ouverture entre deux séances. Moins de
       dix écarts d’ouverture ne donnent pas d’échelle : on prend alors celle d’une heure de marche (σ·√60). */
    var sig = 1.4826 * mad(dcs, nd), sb = 1.4826 * mad(gb, nb);
    q.sigma = isNum(sig) ? sig : 0; q.gapScale = isNum(sb) ? sb : 0;
    var sbEff = nb >= 10 ? q.gapScale : Math.max(q.gapScale, q.sigma * Math.sqrt(60));
    q.thrIntra = Math.max(8 * q.sigma, 20 * tick); q.thrOpen = Math.max(8 * sbEff, 20 * tick);
    for (s = 0; s < ss.length; s++) {
      var S1 = ss[s];
      if (s > 0) { var g0 = O[S1.i0] - Cc[ss[s - 1].i1]; if (Math.abs(g0) > q.thrOpen) q.rolls.push({ key: S1.key, t: t[S1.i0], gap: g0, z: sbEff > 0 ? Math.abs(g0) / sbEff : null, where: 'ouverture' }); }
      for (i = S1.i0 + 1; i <= S1.i1; i++) { var g = O[i] - Cc[i - 1]; if (Math.abs(g) > q.thrIntra) q.rolls.push({ key: S1.key, t: t[i], gap: g, z: q.sigma > 0 ? Math.abs(g) / q.sigma : null, where: 'séance' }); }
    }
    q.rollCount = q.rolls.length; q.rolls = q.rolls.slice(0, 50);
    q.big.sort(function (x, y) { return y.min - x.min; }); q.bigCount = q.big.length; q.big = q.big.slice(0, 12);
    q.flatShare = n ? q.flat / n : 0; q.full = ss.length - q.short.length;
    return q;
  }

  /* ---- Un asset JSON par année ---- */
  function encodeYears(b, kf) {
    var cols = b.cols, ss = b.sessions || split(cols.t, kf), by = {}, ys = [], fixed = 0, rk = b.rollKeys || {};
    ss.forEach(function (s) { var y = s.key.slice(0, 4); if (!by[y]) { by[y] = []; ys.push(y); } by[y].push(s); });
    var years = ys.map(function (y) {
      var bars = 0, docs = by[y].map(function (s) {
        var d = encode(cols, s.i0, s.i1, b.D, s.key, kf); fixed += d.fixed; bars += d.n;
        if (rk[s.key]) d.roll = true;
        if (b.adj && isNum(b.adj[s.key])) d.adj = b.adj[s.key];
        return d;
      });
      var text = JSON.stringify({ v: 2, instrument: b.instrument, year: +y, D: b.D, sessions: docs });
      return { year: +y, text: text, sessions: docs.length, bars: bars, from: docs[0].key, to: docs[docs.length - 1].key, bytes: text.length };
    });
    return { years: years, fixed: fixed, sessions: ss.length };
  }

  /* ---- Lecture d’un CSV par tranches, avec le lecteur de quantEngine (parse) sur chaque tranche ----
     Séparateur et colonnes sont fixés sur les 2 000 premières lignes (l’en-tête, ou un en-tête équivalent pour
     un fichier sans en-tête, est recopié devant chaque tranche). L’ordre jour/mois est voté comme le fait
     parseCsv, sur le fichier entier, puis chaque date jj/mm/aaaa est réécrite aaaa-mm-jj dans l’ordre voté :
     une tranche ne peut donc pas lire mois/jour ce que le fichier lit jour/mois. */
  var RE_VOTE = /(^|[^0-9.,])(\d{1,2})[-\/.](\d{1,2})[-\/.](\d{4})/;
  var RE_RW = /(^|[^0-9.,])(\d{1,2})[-\/.](\d{1,2})[-\/.](\d{4})(?![0-9])/;
  function splitQ(line, sep) {
    if (line.indexOf('"') < 0) return line.split(sep);
    var out = [], cur = '', inq = false;
    for (var i = 0; i < line.length; i++) { var ch = line[i]; if (ch === '"') { if (inq && line[i + 1] === '"') { cur += '"'; i++; } else inq = !inq; } else if (ch === sep && !inq) { out.push(cur); cur = ''; } else cur += ch; }
    out.push(cur); return out;
  }
  function cleanS(s) { return String(s == null ? '' : s).trim().replace(/^["']+|["']+$/g, '').trim(); }
  function isClockS(s) { return /^\d{1,2}:\d{2}(:\d{2}([.,]\d+)?)?$/.test(s) || /^\d{4}(\d{2})?$/.test(s); }
  function synthHeader(line, sep) {
    var f0 = splitQ(line, sep).map(cleanS), clk = f0.length >= 6 && isClockS(f0[1]);
    var names = clk ? ['date', 'time', 'open', 'high', 'low', 'close'] : ['time', 'open', 'high', 'low', 'close'];
    if (f0.length > names.length) names.push('volume');
    while (names.length < f0.length) names.push('x' + names.length);
    return names.join(sep);
  }
  function votes() {
    var v = { dmy: 0, mdy: 0, any: 0, carry: '' };
    v.push = function (text, final) {
      var L = (v.carry + String(text == null ? '' : text)).split(/\r\n|\n|\r/); v.carry = final ? '' : L.pop();
      for (var i = 0; i < L.length; i++) { var m = RE_VOTE.exec(L[i]); if (m) { v.any++; if (+m[2] > 12) v.dmy++; else if (+m[3] > 12) v.mdy++; } }
    };
    return v;
  }
  function orderOf(v) { return v.any ? (v.dmy ? 'dmy' : v.mdy ? 'mdy' : 'dmy') : null; }
  function grow(cap) { return { n: 0, cap: cap, t: new Float64Array(cap), o: new Float64Array(cap), h: new Float64Array(cap), l: new Float64Array(cap), c: new Float64Array(cap), v: new Float64Array(cap) }; }
  function gpush(g, b) {
    if (g.n === g.cap) { var cap = g.cap * 2; ['t', 'o', 'h', 'l', 'c', 'v'].forEach(function (k) { var x = new Float64Array(cap); x.set(g[k]); g[k] = x; }); g.cap = cap; }
    var i = g.n++; g.t[i] = b.t; g.o[i] = b.o; g.h[i] = b.h; g.l[i] = b.l; g.c[i] = b.c; g.v[i] = b.v;
  }
  function csvReader(o, parse) {
    var tz = o.tz || NY, SAMPLE = o.sample || 2000, order = o.order || null;
    var st = { carry: '', pre: [], ready: false, head: null, err: null, header: true, sep: null, sepName: '', next: 1, first: true, done: false };
    var g = grow(4096), tot = { skipped: 0, fixed: 0, dup: 0, kinds: {}, firstSkip: null, chunks: 0 };
    function rw(line) { return order ? line.replace(RE_RW, function (m, p, x, y, yr) { return p + yr + '-' + (order === 'mdy' ? x : y) + '-' + (order === 'mdy' ? y : x); }) : line; }
    function feed(lines, start) {
      var any = false, i; for (i = 0; i < lines.length; i++) if (lines[i].trim()) { any = true; break; }
      if (!any) return;
      var r = parse(st.head + '\n' + lines.map(rw).join('\n'), { tz: tz }); tot.chunks++;
      tot.skipped += r.skipped || 0; tot.fixed += r.fixed || 0; tot.dup += r.dup || 0;
      if (r.firstSkip && !tot.firstSkip) { var j = r.firstSkip.line - 2; tot.firstSkip = { line: start + j, text: String(lines[j] == null ? r.firstSkip.text : lines[j]).slice(0, 60) }; }
      if (r.timeKind) tot.kinds[r.timeKind] = (tot.kinds[r.timeKind] || 0) + (r.n || 0);
      var B = r.bars || []; for (i = 0; i < B.length; i++) gpush(g, B[i]);
    }
    function setup(final) {
      var L = st.pre, f = -1, i;
      for (i = 0; i < L.length; i++) if (L[i].trim()) { f = i; break; }
      if (f < 0) { if (final) { st.err = 'Le fichier est vide.'; st.ready = true; } return final; }
      var ne = 0, end = L.length;
      for (i = f + 1; i < L.length; i++) if (L[i].trim() && ++ne >= SAMPLE) { end = i + 1; break; }
      if (ne < SAMPLE && !final) return false;
      var r0 = parse(L.slice(f, end).map(rw).join('\n'), { tz: tz });
      st.sep = r0.sep; st.sepName = r0.sepName || ''; st.header = !!r0.header; st.ready = true;
      if (r0.error && r0.error !== 'Aucune barre lisible.') { st.err = r0.error; return true; }
      st.head = r0.header ? L[f] : synthHeader(L[f], r0.sep);
      var from = r0.header ? f + 1 : f;
      feed(L.slice(from), from + 1);
      st.next = L.length + 1; st.pre = null;
      return true;
    }
    function push(text, final) {
      if (st.done) return;
      text = String(text == null ? '' : text);
      if (st.first && text.length) { text = text.replace(/^﻿/, ''); st.first = false; }
      if (st.err) { if (final) st.done = true; return; }
      var s = st.carry + text, hold = '';
      if (!final && s.length && s.charCodeAt(s.length - 1) === 13) { hold = '\r'; s = s.slice(0, -1); }
      var L = s.split(/\r\n|\n|\r/);
      st.carry = final ? '' : L.pop() + hold;
      if (!st.ready) { for (var i = 0; i < L.length; i++) st.pre.push(L[i]); setup(!!final); }
      else if (!st.err) { feed(L, st.next); st.next += L.length; }
      if (final) st.done = true;
    }
    function end() {
      if (!st.done) push('', true);
      var res = { n: 0, sep: st.sep, sepName: st.sepName, header: st.header, timeKind: '', hasVolume: false, stepMin: NaN, skipped: tot.skipped, firstSkip: tot.firstSkip,
        fixed: tot.fixed, dup: tot.dup, warnings: [], error: st.err, order: order, chunks: tot.chunks, cols: null };
      if (st.err) return res;
      var n = g.n, t = g.t, sorted = true, i, k;
      for (i = 1; i < n; i++) if (t[i] < t[i - 1]) { sorted = false; break; }
      var idx = null;
      if (!sorted) { idx = new Array(n); for (i = 0; i < n; i++) idx[i] = i; idx.sort(function (x, y) { return (t[x] - t[y]) || (x - y); }); }
      var c = { t: new Float64Array(n), o: new Float64Array(n), h: new Float64Array(n), l: new Float64Array(n), c: new Float64Array(n), v: new Float64Array(n) }, m = 0, dup = 0;
      for (k = 0; k < n; k++) {
        i = idx ? idx[k] : k;
        if (m && c.t[m - 1] === t[i]) { m--; dup++; }
        c.t[m] = t[i]; c.o[m] = g.o[i]; c.h[m] = g.h[i]; c.l[m] = g.l[i]; c.c[m] = g.c[i]; c.v[m] = g.v[i]; m++;
      }
      if (m < n) ['t', 'o', 'h', 'l', 'c', 'v'].forEach(function (f) { c[f] = c[f].slice(0, m); });
      res.dup += dup; res.n = m; res.cols = c;
      for (i = 0; i < m; i++) if (c.v[i] > 0) { res.hasVolume = true; break; }
      res.timeKind = Object.keys(tot.kinds).sort(function (x, y) { return tot.kinds[y] - tot.kinds[x]; })[0] || '';
      if (m > 1) { var dd = []; for (i = 1; i < Math.min(m, 4000); i++) dd.push(c.t[i] - c.t[i - 1]); dd.sort(function (x, y) { return x - y; }); res.stepMin = dd[Math.floor(dd.length / 2)] / 60000; }
      if (o.ambiguous) res.warnings.push('Dates ambiguës (jour et mois tous deux ≤ 12) : lues jour/mois.');
      if (!m) res.error = 'Aucune barre lisible.';
      if (isFinite(res.stepMin) && res.stepMin !== 1) res.warnings.push('Pas médian de ' + res.stepMin + ' min entre deux barres : la stratégie suppose des barres d’une minute.');
      if (m && !res.hasVolume) res.warnings.push('Aucun volume lu : la VWAP est calculée à poids égaux.');
      if (m) { res.firstT = c.t[0]; res.lastT = c.t[m - 1]; }
      return res;
    }
    return { push: push, end: end };
  }
  /* Le même lecteur sur une chaîne déjà en mémoire (tests, outil Node), découpée en tranches de o.chunk caractères. */
  function chunked(text, o, parse) {
    text = String(text == null ? '' : text);
    var size = o.chunk || 4194304, N = text.length, p, v = votes();
    if (!N) v.push('', true);
    for (p = 0; p < N; p += size) { var last = p + size >= N; v.push(text.slice(p, p + size), last); if (v.dmy || (p === 0 && !v.any && !last)) break; }
    var rd = csvReader({ tz: o.tz, sample: o.sample, order: orderOf(v), ambiguous: v.any > 0 && !v.dmy && !v.mdy }, parse);
    if (!N) rd.push('', true);
    for (p = 0; p < N; p += size) rd.push(text.slice(p, p + size), p + size >= N);
    return rd.end();
  }
  /* Le fichier local, lu par tranches de 4 Mo (Blob.slice), décodé en UTF-8 en flux. */
  function readFile(file, o, parse, prog) {
    var size = file.size || 0, CH = o.chunk || 4194304, v = votes(), dec = new TextDecoder('utf-8');
    function piece(p) {
      var b = file.slice(p, Math.min(size, p + CH));
      if (b.arrayBuffer) return b.arrayBuffer();
      return new Promise(function (res, rej) { var fr = new FileReader(); fr.onload = function () { res(fr.result); }; fr.onerror = function () { rej(new Error('Fichier illisible.')); }; fr.readAsArrayBuffer(b); });
    }
    function scan(p) {
      if (p >= size) return Promise.resolve();
      return piece(p).then(function (buf) {
        var last = p + CH >= size; v.push(dec.decode(buf, { stream: !last }), last);
        prog({ phase: 'scan', p: Math.min(1, (p + CH) / size) });
        if (v.dmy || (p === 0 && !v.any) || last) return null;
        return scan(p + CH);
      });
    }
    if (!size) v.push('', true);
    return scan(0).then(function () {
      var rd = csvReader({ tz: o.tz, sample: o.sample, order: orderOf(v), ambiguous: v.any > 0 && !v.dmy && !v.mdy }, parse), d2 = new TextDecoder('utf-8');
      function step(p) {
        if (p >= size) { if (!size) rd.push('', true); return rd.end(); }
        return piece(p).then(function (buf) { var last = p + CH >= size; rd.push(d2.decode(buf, { stream: !last }), last); prog({ phase: 'lecture', p: Math.min(1, (p + CH) / size) }); return step(p + CH); });
      }
      return step(0);
    });
  }
  /* Après lecture : horodatage de clôture recalé à l’ouverture (t − 60 s), séances, qualité, pas de prix. */
  function finish(r, o, kf) {
    var c = r.cols, out = { parse: r, cols: null, sessions: [], quality: null, D: null, misaligned: 0 };
    r.cols = null;
    if (!c || r.error) return out;
    if (o.stamp === 'cloture') { for (var i = 0; i < c.t.length; i++) c.t[i] -= MIN; if (c.t.length) { r.firstT = c.t[0]; r.lastT = c.t[c.t.length - 1]; } }
    out.cols = c; out.sessions = split(c.t, kf);
    out.quality = quality(c, { tick: o.tick, sessions: out.sessions }, kf);
    out.misaligned = out.quality.misaligned;
    out.D = chooseD(c, o.tick);
    return out;
  }

  var kf = a.keyFn;
  switch (a.op) {
    case 'kit': return { key: localKey, keyAt: keyAt, hourly: hourly, split: split, chooseD: chooseD, encode: encode, decode: decode, decodeAssets: decodeAssets, fpOf: fpOf, fpDocs: fpDocs,
      quality: quality, encodeYears: encodeYears, csvReader: csvReader, chunked: chunked, votes: votes, finish: finish, synthHeader: synthHeader };
    case 'key': return K(kf)(a.t);
    case 'split': return split(a.t, kf);
    case 'chooseD': return chooseD(a.cols, a.tick);
    case 'encode': return encode(a.cols, a.i0, a.i1, a.D, a.key, kf);
    case 'decode': return decode(a.doc);
    case 'decodeAssets': return decodeAssets(a.buffers || a.texts || []);
    case 'fingerprint': return fpOf(a.instrument, a.cols, a.D, kf);
    case 'quality': return quality(a.cols, a.o || {}, kf);
    case 'encodeYears': return encodeYears(a, kf);
    case 'parseText': return finish(chunked(a.text, a.o || {}, a.parse), a.o || {}, kf);
    case 'readFile': return readFile(a.file, a.o || {}, a.parse, a.onProgress || noop).then(function (r) { return finish(r, a.o || {}, kf); });
  }
  throw new Error('opération inconnue : ' + a.op);
}

/* =====================================================================
   2. Exécuteur : un worker par tâche (source = quantEngine + donneesWorker),
      colonnes Float64Array transférées ; sans worker, le fil principal.
   ===================================================================== */
var WURL = null;
function workerUrl() {
  if (WURL) return WURL;
  var Q = T.lib.quant; if (!Q || !Q.engine) throw new Error('Le lecteur de CSV (desk Quant) n’est pas chargé.');
  var src = 'var quantEngine=(' + Q.engine.toString() + ');var donneesWorker=(' + donneesWorker.toString() + ');' +
    'function tl(r){var L=[];(function w(x,d){if(!x||d>4||typeof x!=="object")return;if(x instanceof Float64Array){if(L.indexOf(x.buffer)<0)L.push(x.buffer);return;}if(Array.isArray(x))return;for(var k in x)w(x[k],d+1);})(r,0);return L;}' +
    'onmessage=function(e){var m=e.data,a=m.a;a.parse=function(t,o){return quantEngine({op:"parse",text:t,o:o});};a.onProgress=function(p){postMessage({progress:p});};' +
    'Promise.resolve().then(function(){return donneesWorker(a);}).then(function(r){var L=tl(r);try{postMessage({ok:true,r:r},L);}catch(x){postMessage({ok:true,r:r});}},function(err){postMessage({ok:false,e:String(err&&err.message||err)});});};';
  WURL = URL.createObjectURL(new Blob([src], { type: 'text/javascript' }));
  return WURL;
}
function mainArgs(a, onProgress) { return Object.assign({}, a, { parse: function (t, o) { return T.lib.quant.parseCsv(t, o); }, onProgress: onProgress || function () {}, keyFn: keyFn() }); }
/* runJob(a, transfer, onProgress) → { promise, cancel } */
function runJob(a, transfer, onProgress) {
  var w = null, done = false, rejectFn = null, started = false;
  function local(resolve, reject) {
    setTimeout(function () { Promise.resolve().then(function () { return donneesWorker(mainArgs(a, onProgress)); }).then(resolve, reject); }, 0);
  }
  var promise = new Promise(function (resolve, reject) {
    rejectFn = reject;
    try { if (typeof Worker === 'function' && typeof Blob === 'function' && typeof URL !== 'undefined' && URL.createObjectURL) w = new Worker(workerUrl()); } catch (e) { w = null; }
    if (!w) { local(resolve, reject); return; }
    w.onmessage = function (m) {
      var d = m.data; started = true;
      if (d && d.progress != null) { if (onProgress) onProgress(d.progress); return; }
      if (done) return; done = true; w.terminate();
      if (d && d.ok) resolve(d.r); else reject(new Error(d && d.e || 'Le calcul a échoué.'));
    };
    w.onerror = function (e) {
      if (done) return; done = true; try { w.terminate(); } catch (x) {}
      if (!started && !(transfer && transfer.length)) local(resolve, reject);
      else reject(new Error(e && e.message || 'Le calcul a échoué.'));
    };
    try { w.postMessage({ a: a }, transfer || []); } catch (e) { done = true; w.terminate(); local(resolve, reject); }
  });
  return { promise: promise, cancel: function () { if (!done) { done = true; if (w) try { w.terminate(); } catch (e) {} if (rejectFn) { var er = new Error('Lecture annulée.'); er.code = 'cancelled'; rejectFn(er); } } } };
}
DN.runJob = runJob;

/* =====================================================================
   3. Bibliothèque T.lib.donnees — fonctions pures et accès aux collections
   ===================================================================== */
var KIT = null;
function kit() { return KIT || (KIT = donneesWorker({ op: 'kit' })); }
DN.worker = donneesWorker;
function engineKey() {
  var L = T.lib.laboEngine;
  if (!L || typeof L.op !== 'function') return null;
  return function (t) { var r = L.op('key', { t: t }); if (typeof r === 'string') return r; if (r && typeof r.key === 'string') return r.key; throw new Error('clé de séance illisible'); };
}
/* La clé de séance vit dans le moteur du Labo (LABO.md 1) ; la définition locale, identique, ne sert que s’il est absent. */
function keyFn() {
  var e = engineKey(); if (!e) return kit().key;
  return function (t) { try { return e(t); } catch (err) { return kit().key(t); } };
}
DN.keySource = function () { var e = engineKey(); if (!e) return 'local'; try { e(Date.UTC(2025, 0, 6, 15)); return 'moteur'; } catch (err) { return 'local'; } };
DN.sessionKey = function (t) { return keyFn()(t); };
DN.localKey = function (t) { return kit().key(t); };
DN.splitSessions = function (cols) { return kit().split(cols && cols.t ? cols.t : cols, keyFn()); };
DN.chooseD = function (cols, tick) { return kit().chooseD(cols, tick || 0.25); };
DN.encodeSession = function (cols, i0, i1, D) { return kit().encode(cols, i0, i1, D, null, keyFn()); };
DN.decodeSession = function (doc) { return kit().decode(doc); };
DN.decodeAssets = function (texts) { return kit().decodeAssets(texts); };
DN.encodeYears = function (cols, o) { return kit().encodeYears(Object.assign({ cols: cols }, o || {}), keyFn()); };
DN.fingerprint = function (meta, cols) { var D = (meta && meta.D) || DN.chooseD(cols); return kit().fpOf((meta && meta.instrument) || 'MNQ', cols, D, keyFn()); };
DN.fingerprintDocs = function (instrument, docs) { return kit().fpDocs(instrument, docs); };
DN.quality = function (cols, o) { return kit().quality(cols, o || {}, keyFn()); };
DN.parseChunked = function (text, o) { return kit().chunked(text, o || {}, function (t, p) { return T.lib.quant.parseCsv(t, p); }); };
DN.readText = function (text, o) { o = o || {}; return kit().finish(DN.parseChunked(text, o), o, keyFn()); };
/* Empreinte courte, pour l’affichage et les identifiants : FNV-1a 32 bits en base 36. */
DN.shortPrint = function (fp) {
  var s = String(fp == null ? '' : fp), x = 0x811c9dc5;
  for (var i = 0; i < s.length; i++) { x ^= s.charCodeAt(i); x = Math.imul(x, 0x01000193) >>> 0; }
  return ('0000000' + x.toString(36)).slice(-7);
};

/* ---- Collections ---- */
function coll(p) { return T.ucoll(p); }
var DS_ID = /^ds[a-z0-9]{6,20}$/;
DN.DS_ID = DS_ID;
DN.usable = function (meta) { return !!meta && meta.complete === true && !meta.deleting && !meta.deleted; };
DN.datasets = function () {
  return coll('datasets/items').list().filter(function (d) { return DS_ID.test(d.id); })
    .sort(function (a, b) { return (b.createdAt || b.u || 0) - (a.createdAt || a.u || 0); });
};
DN.newId = function () { var s = Date.now().toString(36); for (var i = 0; i < 6; i++) s += Math.floor(Math.random() * 36).toString(36); return 'ds' + s.slice(0, 20); };

/* ---- Niveaux nommés : un document par mois (LABO.md 2.2). Rend la forme du moteur, { clé: { nom: prix } },
   prix ramenés à l’échelle du contrat (+ base pour un niveau NDX). Un niveau NDX sans base n’entre pas : il est
   listé dans noBase, pour que la validation le refuse au lieu de rendre un NaN silencieux. ---- */
DN.levelsFrom = function (docs, from, to) {
  var map = {}, noBase = [], scales = { contrat: 0, NDX: 0 }, days = 0;
  (docs || []).forEach(function (doc) {
    if (!doc || doc.deleted || !/^\d{4}-\d{2}$/.test(doc.id || '')) return;
    if (from && doc.id < String(from).slice(0, 7)) return;
    if (to && doc.id > String(to).slice(0, 7)) return;
    var dd = doc.days || {};
    Object.keys(dd).forEach(function (k) {
      if (from && k < from) return; if (to && k > to) return;
      var d = dd[k] || {}, ndx = d.scale === 'NDX';
      scales[ndx ? 'NDX' : 'contrat']++;
      if (ndx && !fin(d.base)) { noBase.push(k); return; }
      var add = ndx ? d.base : 0, m = {}, any = false;
      Object.keys(d.levels || {}).forEach(function (n) { var v = Number(d.levels[n]); if (isFinite(v)) { m[n] = v + add; any = true; } });
      if (any) { map[k] = m; days++; }
    });
  });
  noBase.sort();
  return { map: map, days: days, noBase: noBase, scales: scales };
};
DN.levelsMap = function (from, to) { return DN.levelsFrom(coll('levels/items').list(), from, to); };
DN.levelDays = function (docs) {
  var out = [];
  (docs || coll('levels/items').list()).forEach(function (doc) {
    if (!doc || doc.deleted || !/^\d{4}-\d{2}$/.test(doc.id || '')) return;
    Object.keys(doc.days || {}).forEach(function (k) {
      var d = doc.days[k] || {}, lv = d.levels || {}, names = Object.keys(lv).filter(function (n) { return isFinite(Number(lv[n])); });
      out.push({ key: k, month: doc.id, scale: d.scale === 'NDX' ? 'NDX' : 'contrat', base: fin(d.base) ? d.base : null, source: d.source || '', levels: lv, n: names.length, names: names });
    });
  });
  return out.sort(function (a, b) { return a.key < b.key ? 1 : a.key > b.key ? -1 : 0; });
};

/* ---- Boîte de réception (LABO.md 2.3) ---- */
var GO_DEF = { trades: { desk: 'journal', tab: 'registre' }, barres: { desk: 'donnees', tab: 'series' }, strategie: { desk: 'labo', tab: 'concevoir' },
  niveaux: { desk: 'donnees', tab: 'niveaux' }, migration: { desk: 'donnees', tab: 'boite' }, macro: { desk: 'macro', tab: 'rapports' } };
DN.GO_DEF = GO_DEF;
DN.inboxNorm = function (items) {
  return (items || []).filter(function (x) { return x && !x.deleted; }).map(function (x) {
    var d = GO_DEF[x.kind] || null, g = x.go && typeof x.go === 'object' ? x.go : null, go = null;
    if (g && g.desk) go = { desk: g.desk, tab: g.tab || (d && d.desk === g.desk ? d.tab : null), sel: g.sel == null ? null : g.sel };
    else if (d) go = { desk: d.desk, tab: d.tab, sel: g && g.sel != null ? g.sel : null };
    return Object.assign({}, x, { go: go, seen: !!x.seen });
  }).sort(function (a, b) { return (b.at || b.u || 0) - (a.at || a.u || 0); });
};
DN.inbox = function () { return DN.inboxNorm(coll('inbox/items').list()); };
DN.markSeen = function (id) { return coll('inbox/items').update(id, { seen: true }); };

/* ---- Jeu de la visite : un fichier local, ou une marche synthétique, gardé en mémoire le temps de la page ---- */
var VISIT = null, VSUBS = [];
DN.visit = function () { return VISIT; };
DN.setVisit = function (ds) { VISIT = ds || null; VSUBS.slice().forEach(function (f) { try { f(VISIT); } catch (e) {} }); };
DN.onVisit = function (f) { VSUBS.push(f); return function () { VSUBS = VSUBS.filter(function (x) { return x !== f; }); }; };
function f64(x, n) { if (x instanceof Float64Array) return x; var o = new Float64Array(n); for (var i = 0; i < n; i++) o[i] = x && isFinite(x[i]) ? +x[i] : 0; return o; }
/* Un jeu au format du Labo à partir de colonnes : { meta, bars, sessions, levels, levelsInfo, adj, quality }. */
DN.visitFromCols = function (cols, m) {
  m = m || {};
  var n = cols.t.length, b = { t: f64(cols.t, n), o: f64(cols.o, n), h: f64(cols.h, n), l: f64(cols.l, n), c: f64(cols.c, n), v: f64(cols.v || null, n) };
  if (cols.lowFirst) b.lowFirst = cols.lowFirst;
  var hasV = false; for (var i = 0; i < n; i++) if (b.v[i] > 0) { hasV = true; break; }
  var ss = m.sessions || DN.splitSessions(b), D = m.D || DN.chooseD(b), inst = m.instrument || 'MNQ';
  var q = m.quality || DN.quality(b, { sessions: ss });
  var meta = { id: m.id || 'visite', name: m.name || 'Fichier de la visite', instrument: inst, source: m.source || 'fichier', srcTz: m.srcTz || null, stamp: m.stamp || 'ouverture',
    from: ss.length ? ss[0].key : null, to: ss.length ? ss[ss.length - 1].key : null, sessions: ss.length, bars: n, hasVolume: hasV, D: D, roll: m.roll || 'inconnu',
    fingerprint: D ? DN.fingerprint({ instrument: inst, D: D }, b) : null, complete: true, local: true, note: m.note || '', createdAt: m.createdAt || Date.now() };
  var lv = DN.levelsMap(meta.from, meta.to);
  return { meta: meta, bars: b, sessions: ss, levels: lv.map, levelsInfo: lv, adj: {}, quality: q, origin: m.origin || null };
};
/* Marche sans dérive exacte, par le moteur du Labo (op lattice) ; jamais comptée dans les essais. */
DN.synthetic = function (o) {
  var L = T.lib.laboEngine;
  if (!L || typeof L.op !== 'function') throw new Error('Moteur indisponible : la marche synthétique demande le moteur du Labo.');
  o = Object.assign({ seed: 1, sigma: 2, sessions: 60, tick: 0.25 }, o || {});
  var r = L.op('lattice', o), b = r && (r.bars || r.cols || r);
  if (!b || !b.t || !b.t.length) throw new Error('Moteur indisponible : la marche synthétique n’a rendu aucune barre.');
  var ds = DN.visitFromCols(b, { id: 'synthetique', name: 'Marche sans dérive · graine ' + o.seed, source: 'synthetique', roll: 'ajuste', instrument: o.instrument || 'MNQ',
    note: 'Aucun avantage n’existe ici : une stratégie qui y gagne est surajustée.' });
  ds.meta.seed = o.seed; ds.meta.sigma = o.sigma; ds.meta.essais = false;
  return ds;
};

/* ---- Écritures : séquentielles, trois reprises à délai aléatoire sur unavailable / store_unavailable /
   resource_exhausted, arrêt avec message sur toute autre erreur (quota compris). LABO.md 2.1. ---- */
var RETRY = { unavailable: 1, store_unavailable: 1, resource_exhausted: 1 };
DN.RETRY_CODES = RETRY;
function cerr(code, msg) { var e = new Error(msg); e.code = code; return e; }
function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
DN.retryDelay = function (k) { return 250 + Math.random() * 750 * k; };
DN.withRetry = function (fn, o) {
  o = o || {}; var left = o.tries == null ? 3 : o.tries, delay = o.delay || DN.retryDelay, k = 0;
  function go() { return Promise.resolve().then(fn).catch(function (e) { var code = e && e.code; if (left > 0 && RETRY[code]) { left--; k++; return sleep(delay(k)).then(go); } throw e; }); }
  return go();
};
DN.errorText = function (e) {
  var c = e && e.code, M = {
    not_writer: 'Enregistrer demande l’artefact ouvert dans claude.ai, avec le droit de le modifier.', not_granted: 'Les fichiers attachés ne sont pas accordés à cette vue.',
    local: 'Ton compte n’est pas joignable : ouvre l’artefact dans claude.ai, connecté.', quota_exceeded: 'La base du compte est pleine : supprime des documents ou un jeu, puis recommence.',
    quota_or_state: 'Le stockage des fichiers est plein (ou l’artefact n’accepte plus d’envoi) : supprime un jeu, puis recommence.', too_large: 'Une année dépasse 20 Mio : coupe le fichier en périodes plus courtes.',
    rate_limited: 'Trop d’envois rapprochés : attends une minute, puis recommence.', upstream_auth: 'Session expirée : recharge la page ou reconnecte-toi.',
    capability_disabled: 'Les fichiers attachés ne sont pas disponibles dans cette vue.', capability_removed: 'Les fichiers attachés ne sont pas disponibles dans cette vue.',
    unsupported_type: 'Envoi refusé : format non accepté.', invalid_request: 'Envoi refusé : requête invalide.', revoked: 'L’accès de cette vue a été retiré : recharge la page.',
    unavailable: 'Le service est momentanément indisponible : réessaie dans un instant.', store_unavailable: 'Le stockage est momentanément indisponible : réessaie dans un instant.',
    resource_exhausted: 'Trop d’opérations d’un coup : réessaie dans une minute.'
  };
  return M[c] || (e && e.message) || String(e);
};
function useCap(name) {
  try {
    var w = typeof window !== 'undefined' ? window : null;
    if (!w || !w.claude || typeof w.claude.use !== 'function') return Promise.resolve(null);
    return Promise.resolve(w.claude.use(name)).then(function (x) { return x || null; }, function () { return null; });
  } catch (e) { return Promise.resolve(null); }
}
DN.assetsApi = function () { return useCap('assets'); };
function docRef(path, id) {
  return Promise.all([useCap('db'), useCap('user')]).then(function (r) {
    var db = r[0], user = r[1];
    if (!db || !user || typeof user.id !== 'function') throw cerr('local', DN.errorText({ code: 'local' }));
    return Promise.resolve(user.id()).then(function (uid) {
      if (!uid) throw cerr('local', DN.errorText({ code: 'local' }));
      var p = path.split('/'); return db.doc('data/users/' + uid + '/' + p[0]).collection(p[1]).doc(id);
    });
  });
}
/* Écriture directe d’un document d’une collection privée, avec le code d’erreur (T.ucoll.set ne le rend pas).
   Le miroir de T.ucoll reçoit le document par son abonnement ; u dépasse toujours le u connu. */
function strictSet(path, id, doc) {
  var cur = coll(path).get(id), u = Date.now(); if (cur && cur.u >= u) u = cur.u + 1;
  var d = Object.assign({}, doc, { id: id, u: u });
  return docRef(path, id).then(function (ref) { return DN.withRetry(function () { return ref.set(d); }); }).then(function () {
    /* Sans abonnement du socle (compte pas encore relié), la copie locale est mise à jour ici. */
    if (!T.cloudReady()) coll(path).set(id, d);
    return d;
  });
}
DN.strictSet = strictSet;

/* ---- Lecture d’un jeu du compte ---- */
DN.CLOUD_WAIT = 10000;
function waitCloud(ms) {
  return new Promise(function (res) {
    if (T.cloudReady()) { res(true); return; }
    var done = false, un = null, tm = setTimeout(function () { if (done) return; done = true; if (un) un(); res(false); }, ms);
    un = T.onCloud(function () { if (done) return; done = true; clearTimeout(tm); res(true); });
  });
}
var LCACHE = {};
DN.loadDataset = function (id) {
  if (id === 'visite' || id === 'synthetique') return VISIT && VISIT.meta.id === id ? Promise.resolve(VISIT) : Promise.reject(new Error('Aucun jeu de visite en mémoire.'));
  return waitCloud(DN.CLOUD_WAIT).then(function (online) {
    var col = coll('datasets/items');
    return col.ready().then(function () {
      var meta = col.get(id);
      if (!meta) throw cerr('absent', 'Jeu introuvable' + (online ? '' : ' (compte injoignable)') + '.');
      if (meta.deleting) throw cerr('deleting', 'Ce jeu est en cours de suppression : il n’est plus lu.');
      if (meta.complete !== true) throw cerr('incomplete', 'Jeu incomplet : son import n’est pas terminé, aucun calcul.');
      var c = LCACHE[id]; if (c && c.u === meta.u) return c.p;
      var assets = (meta.assets || []).slice().sort(function (x, y) { return x.year - y.year; });
      if (!assets.length) throw cerr('incomplete', 'Jeu incomplet (0/' + (meta.sessions || 0) + ') : aucun fichier de barres, aucun calcul.');
      var p = assets.reduce(function (acc, as) {
        return acc.then(function (bufs) {
          return fetch('/_blob/' + as.id).then(function (r) {
            if (!r || !r.ok) throw cerr('blob', 'Fichier de barres introuvable (' + as.year + (r ? ', HTTP ' + r.status : '') + ').');
            return r.arrayBuffer ? r.arrayBuffer() : r.text();
          }).then(function (b) { bufs.push(b); return bufs; });
        });
      }, Promise.resolve([])).then(function (bufs) {
        var tr = bufs.filter(function (b) { return typeof ArrayBuffer !== 'undefined' && b instanceof ArrayBuffer; });
        return runJob({ op: 'decodeAssets', buffers: bufs }, tr).promise;
      }).then(function (r) {
        if (r.sessions.length !== meta.sessions) throw cerr('incomplete', 'Jeu incomplet (' + r.sessions.length + '/' + meta.sessions + ') : aucun calcul.');
        if (meta.D && r.D !== meta.D) throw cerr('incomplete', 'Pas de prix différent de la fiche du jeu : aucun calcul.');
        var lv = DN.levelsMap(meta.from, meta.to), adj = {};
        r.sessions.forEach(function (s) { if (fin(s.adj)) adj[s.key] = s.adj; });
        return { meta: meta, bars: r.cols, sessions: r.sessions, levels: lv.map, levelsInfo: lv, adj: adj };
      });
      LCACHE = {}; LCACHE[id] = { u: meta.u, p: p };
      p.catch(function () { if (LCACHE[id] && LCACHE[id].p === p) delete LCACHE[id]; });
      return p;
    });
  });
};

/* ---- Enregistrement : un asset JSON par année, puis la fiche (complete: true). Un échec efface les assets
   déjà envoyés, qu’aucune fiche ne désigne. ---- */
DN.saveDataset = function (meta, cols, onProgress) {
  onProgress = onProgress || function () {};
  meta = Object.assign({}, meta || {});
  var A = null, uploaded = [], id = meta.id && DS_ID.test(meta.id) ? meta.id : DN.newId(), doc = null;
  var n = cols.t.length, hasV = false, i;
  if (cols.v) for (i = 0; i < n; i++) if (cols.v[i] > 0) { hasV = true; break; }
  var src = { t: cols.t, o: cols.o, h: cols.h, l: cols.l, c: cols.c, v: hasV ? cols.v : null };
  return DN.assetsApi().then(function (api) {
    if (!api) throw cerr('not_writer', DN.errorText({ code: 'not_writer' }));
    A = api;
    var D = meta.D || DN.chooseD(src);
    if (!D) throw cerr('decimal', 'Prix non décimaux : série ajustée par ratio ? Rien n’a été envoyé.');
    meta.D = D;
    onProgress({ phase: 'codage', k: 0, n: 1 });
    var ss = DN.splitSessions(src), rollKeys = {};
    if (meta.roll === 'non-ajuste') DN.quality(src, { sessions: ss }).rolls.forEach(function (r) { if (r.where === 'ouverture') rollKeys[r.key] = true; });
    meta.from = ss.length ? ss[0].key : null; meta.to = ss.length ? ss[ss.length - 1].key : null; meta.sessions = ss.length; meta.bars = n; meta.hasVolume = hasV;
    meta.fingerprint = DN.fingerprint({ instrument: meta.instrument || 'MNQ', D: D }, src);
    return runJob({ op: 'encodeYears', cols: src, D: D, instrument: meta.instrument || 'MNQ', rollKeys: rollKeys }).promise;
  }).then(function (enc) {
    var years = enc.years;
    years.forEach(function (y) { if (y.bytes > 20 * 1048576) throw cerr('too_large', DN.errorText({ code: 'too_large' })); });
    return years.reduce(function (acc, y, k) {
      return acc.then(function () {
        onProgress({ phase: 'envoi', k: k, n: years.length, year: y.year });
        return DN.withRetry(function () { return A.upload(new Blob([y.text], { type: 'application/json' }), { type: 'application/json' }); }).then(function (res) {
          uploaded.push({ year: y.year, id: res.id, sessions: y.sessions, from: y.from, to: y.to, bytes: res.sizeBytes || y.bytes });
        });
      });
    }, Promise.resolve());
  }).then(function () {
    onProgress({ phase: 'fiche', k: 0, n: 1 });
    var now = Date.now();
    doc = Object.assign({ name: 'Barres d’une minute', instrument: 'MNQ', source: 'fichier', srcTz: null, stamp: 'ouverture', roll: 'inconnu', note: '' }, meta,
      { id: id, assets: uploaded, complete: true, createdAt: meta.createdAt || now });
    delete doc.deleting; delete doc.deleted; delete doc.local;
    return strictSet('datasets/items', id, doc);
  }).then(function (d) { onProgress({ phase: 'fini', k: 1, n: 1 }); return d; }, function (e) {
    if (A && uploaded.length) uploaded.forEach(function (x) { Promise.resolve().then(function () { return A.delete(x.id); }).catch(function () {}); });
    throw e;
  });
};
/* Suppression : deleting: true d’abord (le jeu n’est plus jamais lu), puis les assets, puis la fiche (douce). */
DN.deleteDataset = function (id) {
  var col = coll('datasets/items'), meta = col.get(id), A = null;
  if (!meta) return Promise.reject(cerr('absent', 'Jeu introuvable.'));
  return strictSet('datasets/items', id, Object.assign({}, meta, { deleting: true })).then(function () { return DN.assetsApi(); }).then(function (api) {
    if (!api) throw cerr('not_writer', DN.errorText({ code: 'not_writer' }));
    A = api;
    return (meta.assets || []).reduce(function (acc, as) { return acc.then(function () { return DN.withRetry(function () { return A.delete(as.id); }); }); }, Promise.resolve());
  }).then(function () { delete LCACHE[id]; return col.remove(id); }).then(function () { return true; });
};

/* ---- Compteurs : documents connus de cet appareil (copies locales) / 25 000, taille des fichiers attachés ---- */
DN.DOC_LIMIT = 25000;
DN.docUsage = function () {
  var parts = [], tot = 0;
  function rows(k) { try { var r = localStorage.getItem('alpdesk:' + k), v = r ? JSON.parse(r) : null; return Array.isArray(v) ? v.length : 0; } catch (e) { return 0; } }
  var st = 0; try { for (var i = 0; i < localStorage.length; i++) { var k = localStorage.key(i); if (k && k.indexOf('alpdesk:s:') === 0) st++; } } catch (e) {}
  parts.push({ label: 'réglages et états', n: st });
  parts.push({ label: 'journal', n: rows('journal') });
  [['datasets/items', 'jeux de barres'], ['levels/items', 'niveaux (mois)'], ['inbox/items', 'boîte'], ['labo/strategies', 'stratégies'], ['labo/essais', 'essais'], ['labo/oos', 'hors échantillon'], ['labo/config', 'réglages du Labo']]
    .forEach(function (p) { parts.push({ label: p[1], n: rows('uc:' + p[0]) }); });
  parts.push({ label: 'macro et calendrier', n: rows('sh:macro') + rows('sh:calendar') });
  parts.forEach(function (p) { tot += p.n; });
  return { docs: tot, limit: DN.DOC_LIMIT, parts: parts };
};
DN.assetUsage = function () {
  var metaBytes = 0, files = 0;
  DN.datasets().forEach(function (m) { (m.assets || []).forEach(function (a) { files++; metaBytes += a.bytes || 0; }); });
  return DN.assetsApi().then(function (A) {
    if (!A || typeof A.list !== 'function') return { source: 'jeux', bytes: metaBytes, files: files };
    return A.list().then(function (r) { var u = r && r.usage || {}; return { source: 'compte', bytes: u.bytes, maxBytes: u.maxBytes, files: u.files, maxFiles: u.maxFiles }; },
      function () { return { source: 'jeux', bytes: metaBytes, files: files }; });
  });
};

/* =====================================================================
   4. Rendu
   ===================================================================== */
var CSS = '.dn-stack{display:flex;flex-direction:column;gap:12px;min-width:0}' +
  '.dn-list{border:1px solid var(--line);border-radius:var(--r);background:var(--panel);overflow:hidden}' +
  '.dn-item{display:flex;flex-direction:column;gap:7px;padding:12px 13px;border-top:1px solid var(--line);min-width:0}.dn-item:first-child{border-top:0}' +
  '.dn-item.unseen{background:linear-gradient(90deg,var(--violet-a),transparent 70%)}' +
  '.dn-top{display:flex;align-items:center;gap:8px;min-width:0}.dn-top b{flex:1;min-width:0;font-size:13.5px;font-weight:600;color:var(--fg);overflow-wrap:anywhere;line-height:1.35}' +
  '.dn-dot{width:8px;height:8px;border-radius:50%;background:var(--violet);flex:none}' +
  '.dn-meta{font:500 11px/1.4 var(--f-mono);color:var(--mute)}' +
  '.dn-detail{font-size:12.5px;color:var(--soft);line-height:1.5;overflow-wrap:anywhere}' +
  '.dn-acts{display:flex;flex-wrap:wrap;gap:6px;align-items:center}' +
  '.dn-kv{max-width:560px;display:grid;grid-template-columns:minmax(0,max-content) minmax(0,1fr);gap:5px 14px;margin:0;font:500 12px/1.45 var(--f-mono)}' +
  '.dn-kv dt{color:var(--mute);white-space:nowrap}.dn-kv dd{margin:0;color:var(--fg);text-align:right;overflow-wrap:anywhere;min-width:0}' +
  '.dn-line{display:flex;flex-wrap:wrap;gap:4px 12px;align-items:baseline;font:500 11.5px/1.5 var(--f-mono);color:var(--mute);min-width:0}.dn-line b{color:var(--fg);font-weight:600;overflow-wrap:anywhere}' +
  '.dn-cap{font:600 10px/1.3 var(--f-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--mute)}' +
  '.dn-prog{display:flex;flex-direction:column;gap:7px}.dn-bar{position:relative;height:10px;border-radius:5px;background:var(--raise-2);overflow:hidden;border:1px solid var(--line)}.dn-bar i{position:absolute;left:0;top:0;bottom:0;background:var(--violet);transition:width .2s}' +
  '.dn-file{position:relative}.dn-file input{display:none}' +
  '.dn-wait{display:flex;align-items:center;gap:10px;padding:14px;border:1px dashed var(--line-2);border-radius:var(--r);font:500 12px/1.4 var(--f-mono);color:var(--mute);background:var(--panel)}' +
  '.dn-wait i{width:8px;height:8px;border-radius:50%;background:var(--violet);flex:none;animation:dnp 1s ease-in-out infinite}@keyframes dnp{50%{opacity:.25}}' +
  '.dn-code{display:block;font:500 11.5px/1.55 var(--f-mono);background:var(--raise);border:1px solid var(--line);border-radius:8px;padding:9px 10px;color:var(--fg);overflow-x:auto;white-space:pre;max-width:100%;margin:0}' +
  '.dn-steps{margin:0;padding-left:18px;color:var(--soft);font-size:13.5px;line-height:1.55}.dn-steps li{margin:0 0 7px}.dn-steps b{color:var(--fg);font-weight:600}' +
  'details.dn-det{border-top:1px solid var(--line);padding-top:10px}details.dn-det>summary{cursor:pointer;list-style:none;font:600 10.5px/1.3 var(--f-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--soft)}details.dn-det>summary::-webkit-details-marker{display:none}details.dn-det>summary::after{content:" +";color:var(--violet-2)}details.dn-det[open]>summary::after{content:" −"}details.dn-det[open]>summary{margin-bottom:10px}' +
  '.dn-chips{display:flex;flex-wrap:wrap;gap:6px}.dn-chip{display:inline-flex;align-items:baseline;gap:6px;padding:5px 9px;border:1px solid var(--line-2);border-radius:8px;background:var(--raise);font:500 11.5px/1.2 var(--f-mono);color:var(--soft)}.dn-chip b{color:var(--fg);font-weight:600}';
function injectCss() { if (document.getElementById('donnees-css')) return; var s = document.createElement('style'); s.id = 'donnees-css'; s.textContent = CSS; document.head.appendChild(s); }

var KIND = { trades: 'Trades', barres: 'Barres', strategie: 'Stratégie', niveaux: 'Niveaux', macro: 'Macro', note: 'Note', migration: 'Migration' };
var DESK_NAME = { journal: 'le journal', donnees: 'Données', labo: 'le Labo', macro: 'Macro', nq: 'NQ', quant: 'Quant' };
function goLabel(g) {
  if (g.desk === 'donnees') return g.tab === 'series' ? (g.sel ? 'Voir le jeu' : 'Voir les séries') : g.tab === 'niveaux' ? 'Voir les niveaux' : 'Ouvrir';
  if (g.desk === 'labo') return g.sel ? 'Ouvrir dans le Labo' : 'Ouvrir le Labo';
  return 'Ouvrir ' + (DESK_NAME[g.desk] || g.desk);
}
var ROLL = { ajuste: 'ajusté', 'non-ajuste': 'non ajusté', inconnu: 'inconnu' };
var TZ_OPTS = [{ v: 'America/New_York', label: 'New York' }, { v: 'America/Chicago', label: 'Chicago (CME)' }, { v: 'Europe/Paris', label: 'Paris' }, { v: 'UTC', label: 'UTC' }];
var TIME_KIND = { s: 'secondes Unix', ms: 'millisecondes Unix', iso: 'ISO avec fuseau', local: 'heure locale du fichier' };
var UI = { sel: null, day: null, confirmDel: null, delBusy: null, delErr: null, report: null, assets: null, probing: false };
var FILE = { file: null, name: '', size: 0, phase: 'idle', progress: 0, step: '', err: null, res: null, cancel: null, saving: null, saveErr: null, savedId: null, label: '', progEl: null, progTx: null };

function prefs() { return Object.assign({ tz: 'America/New_York', stamp: 'ouverture', instrument: 'MNQ', roll: 'inconnu' }, T.store.get('donnees:import', {})); }
function setPrefs(p) { T.store.set('donnees:import', Object.assign(prefs(), p)); }
function pad2(n) { return (n < 10 ? '0' : '') + n; }
function fmtKey(k) { return k && /^\d{4}-\d{2}-\d{2}$/.test(k) ? k.slice(8, 10) + '/' + k.slice(5, 7) + '/' + k.slice(0, 4) : '—'; }
function fmtKeyShort(k) { return k && /^\d{4}-\d{2}-\d{2}$/.test(k) ? k.slice(8, 10) + '/' + k.slice(5, 7) : '—'; }
function fmtWhen(t) { return fin(t) ? F.dateLong(t) + ' · ' + F.time(t) : '—'; }
function fmtBytes(b) { if (!fin(b)) return '—'; if (b < 1024) return F.int(b) + ' o'; if (b < 1048576) return F.num(b / 1024, 0, 'Ko'); return F.num(b / 1048576, 1, 'Mio'); }
function plural(n, s, p) { return F.int(n) + ' ' + (n > 1 ? (p || s + 's') : s); }
function kv(rows) { return h('dl', { class: 'dn-kv' }, rows.filter(Boolean).map(function (r) { return [h('dt', null, r[0]), h('dd', null, r[1] == null || r[1] === '' ? '—' : r[1])]; })); }
function wait(text) { return h('div', { class: 'dn-wait', role: 'status' }, h('i'), text); }
function deskExists(id) { return T.desks().some(function (d) { return d.id === id; }); }

/* ---------------- Rapport de qualité ---------------- */
function qualityView(q) {
  var wrap = h('div', { class: 'dn-stack' });
  wrap.appendChild(U.kpis([
    { label: 'Séances', value: F.int(q.sessions), hint: q.short.length ? plural(q.short.length, 'courte') + ' (< 80 %)' : 'toutes ≥ 80 %' },
    { label: 'Barres', value: F.int(q.bars), hint: fmtKey(q.from) + ' → ' + fmtKey(q.to) },
    { label: 'Minutes manquantes', value: F.int(q.missing), hint: q.holes ? plural(q.holes, 'trou') + ' en séance' : 'aucun trou' },
    { label: 'Barres plates', value: F.int(q.flat), hint: F.pct(q.flatShare, 2) + ' des barres' },
    { label: 'Sauts suspects', value: F.int(q.rollCount), tone: q.rollCount ? 'acc' : null, hint: 'seuil : 8 σ robustes' },
    { label: 'Sans volume', value: q.hasVolume ? F.int(q.noVolume.length) : 'toutes', hint: q.hasVolume ? (q.noVolume.length ? 'séances à zéro' : 'volume partout') : 'source sans volume' }
  ], 3));
  var days = q.days || [];
  if (days.length) {
    /* Abscisse : la clé de chaque séance (jamais l’heure d’ouverture, qui tombe la veille), sans trou de week-end. */
    var lab = days.map(function (d) { return days.length > 260 ? d.key.slice(5, 7) + '/' + d.key.slice(2, 4) : fmtKeyShort(d.key); });
    wrap.appendChild(h('div', { class: 'dn-cap' }, 'Amplitude de chaque séance, en points'));
    if (days.length <= 40) wrap.appendChild(C.bar({ cats: lab, series: [{ name: 'Amplitude', values: days.map(function (d) { return d.range; }), tone: 'violet' }], fmt: function (v) { return F.num(v, 0); }, height: 170 }));
    else wrap.appendChild(C.line({ series: [{ name: 'Amplitude', points: days.map(function (d, i) { return [i, d.range]; }), tone: 'violet', area: true }], x: { type: 'cat', labels: lab }, y: { zero: true, fmt: function (v) { return F.num(v, 0); } }, height: 170 }));
    wrap.appendChild(h('div', { class: 'dn-cap' }, 'Clôture de chaque séance'));
    wrap.appendChild(C.line({ series: [{ name: 'Clôture', points: days.map(function (d, i) { return [i, d.close]; }), tone: 'fg' }], x: { type: 'cat', labels: lab }, y: { fmt: function (v) { return F.num(v, 0); } }, height: 150, ml: 52 }));
  }
  var notes = [];
  if (q.misaligned) notes.push(U.note(plural(q.misaligned, 'barre') + ' ne tombe' + (q.misaligned > 1 ? 'nt' : '') + ' pas sur une minute entière : l’enregistrement les refuse.', true));
  if (q.unordered) notes.push(U.note(plural(q.unordered, 'horodatage') + ' non croissant' + (q.unordered > 1 ? 's' : '') + '.', true));
  if (q.rolls.length) notes.push(U.note('Sauts suspects : ' + q.rolls.slice(0, 6).map(function (r) { return fmtKey(r.key) + ' (' + F.num(r.gap, 2, 'pt', true) + (r.where === 'ouverture' ? ', à l’ouverture' : '') + ')'; }).join(', ') + (q.rollCount > 6 ? ', …' : '') + '. Une bascule de contrat se règle par le champ « roll » du jeu.', true));
  if (q.big.length) notes.push(U.note('Plus grands trous : ' + q.big.slice(0, 5).map(function (b) { return fmtKey(b.key) + ' (' + F.dur(b.min) + ')'; }).join(', ') + '.'));
  if (q.short.length) notes.push(U.note('Séances courtes : ' + q.short.slice(0, 6).map(function (s) { return fmtKey(s.key) + ' (' + F.int(s.n) + ')'; }).join(', ') + (q.short.length > 6 ? ', …' : '') + '. Le Labo ne lit pas « la séance précédente » dans une séance de moins de 80 % des barres attendues.'));
  if (q.hasVolume && q.noVolume.length) notes.push(U.note('Séances sans volume : ' + q.noVolume.slice(0, 6).map(fmtKey).join(', ') + (q.noVolume.length > 6 ? ', …' : '') + '. La VWAP y est calculée à poids égaux.'));
  notes.forEach(function (n) { wrap.appendChild(n); });
  wrap.appendChild(U.note('Loi nulle des sauts : un écart entre une clôture et l’ouverture suivante est suspect au-delà de 8 écarts-types robustes (1,4826 × écart absolu médian, ici ' + F.num(q.sigma, 2, 'pt') + ' par minute). Sous une loi normale, cela arrive moins d’une fois sur 10¹⁴ : ce qui le dépasse se vérifie (bascule de contrat, donnée fausse, nouvelle majeure).'));
  return wrap;
}

/* ---------------- Onglet Boîte ---------------- */
function renderInbox(root, ctx, subs) {
  var col = coll('inbox/items'); subs.push(col.on(function () { if (ctx.tab === 'boite') ctx.rerender(); }));
  var items = DN.inbox(), unseen = items.filter(function (x) { return !x.seen; });
  var week = items.filter(function (x) { return (x.at || x.u || 0) >= Date.now() - 7 * 86400000; }).length;
  root.appendChild(U.kpis([
    { label: 'Non lus', value: F.int(unseen.length), tone: unseen.length ? 'acc' : null, hint: unseen.length ? 'à ouvrir' : 'tout est lu' },
    { label: 'Sept jours', value: F.int(week), hint: 'arrivés récemment' },
    { label: 'Éléments', value: F.int(items.length), hint: 'déposés par Claude' },
    { label: 'Dernier', value: items.length ? F.date(items[0].at || items[0].u) : '—', hint: items.length ? (KIND[items[0].kind] || 'élément') : 'rien encore' }
  ]));
  var sec = U.section('Ce que Claude a *déposé*', unseen.length ? plural(unseen.length, 'non lu') : null);
  if (!items.length) {
    sec.appendChild(U.empty({ title: 'Rien pour l’instant', text: 'Quand Claude importe tes trades, tes barres, des niveaux ou une stratégie, un élément arrive ici avec un lien direct vers l’endroit où le retrouver.', action: U.button({ label: 'Que lui envoyer ?', small: true, onClick: function () { ctx.setTab('envoyer'); } }) }));
  } else {
    sec.appendChild(h('div', { class: 'dn-list' }, items.map(function (it) { return inboxRow(it, ctx); })));
    if (unseen.length > 1) sec.appendChild(h('div', { class: 'dn-acts' }, U.button({ label: 'Tout marquer comme lu', small: true, kind: 'ghost', onClick: function () { unseen.forEach(function (x) { DN.markSeen(x.id); }); } })));
  }
  root.appendChild(sec);
  root.appendChild(U.note('Chaque élément pointe vers l’endroit où la donnée vit désormais. Le lire ne change rien aux données : il sert à suivre ce qui est arrivé depuis ta dernière visite.'));
}
function inboxRow(it, ctx) {
  var g = it.go, ok = g && g.desk && deskExists(g.desk), here = g && g.desk === 'donnees' && (g.tab || 'boite') === 'boite';
  var meta = [fmtWhen(it.at || it.u)];
  if (fin(it.count)) meta.push(F.int(it.count) + (it.kind === 'trades' ? ' trade' + (it.count > 1 ? 's' : '') : it.kind === 'barres' ? ' séance' + (it.count > 1 ? 's' : '') : it.kind === 'niveaux' ? ' niveau' + (it.count > 1 ? 'x' : '') : ''));
  function open() {
    if (!it.seen) DN.markSeen(it.id);
    T.store.set('donnees:go', { desk: g.desk, tab: g.tab || null, sel: g.sel == null ? null : g.sel, from: it.id, at: Date.now() });
    if (g.desk === 'donnees' && g.tab === 'series' && g.sel) { UI.sel = g.sel; T.store.set('donnees:sel', g.sel); }
    if (g.desk === 'donnees' && g.tab === 'niveaux' && g.sel) UI.day = String(g.sel);
    if (g.desk === 'donnees' && g.tab) { ctx.setTab(g.tab); return; }
    T.nav.go(g.desk, g.tab || undefined);
  }
  return h('div', { class: 'dn-item' + (it.seen ? '' : ' unseen') },
    h('div', { class: 'dn-top' }, it.seen ? null : h('i', { class: 'dn-dot', title: 'non lu' }), U.pill(KIND[it.kind] || 'Élément', it.seen ? null : 'acc'), h('b', null, it.title || 'Sans titre')),
    h('div', { class: 'dn-meta' }, meta.join(' · ')),
    it.detail ? h('div', { class: 'dn-detail' }, String(it.detail)) : null,
    h('div', { class: 'dn-acts' },
      g && !here ? U.button({ label: ok ? goLabel(g) : 'Desk absent de cette version', small: true, kind: ok ? 'pri' : null, disabled: !ok, onClick: open }) : null,
      !it.seen ? U.button({ label: 'Marquer comme lu', small: true, kind: 'ghost', onClick: function () { DN.markSeen(it.id); } }) : null));
}

/* ---------------- Onglet Séries ---------------- */
function probeAssets(ctx) {
  if (UI.assets !== null || UI.probing) return;
  UI.probing = true;
  DN.assetsApi().then(function (A) { UI.assets = !!A; UI.probing = false; if (ctx.tab === 'series') ctx.rerender(); });
}
function paintProgress() {
  if (FILE.progEl) FILE.progEl.style.width = Math.round(Math.max(0, Math.min(1, FILE.progress)) * 100) + '%';
  if (FILE.progTx) FILE.progTx.textContent = FILE.step + ' · ' + F.int(Math.round(FILE.progress * 100)) + ' %';
}
function startRead(file, ctx) {
  if (FILE.cancel) { try { FILE.cancel(); } catch (e) {} }
  var P = prefs();
  FILE = Object.assign({}, FILE, { file: file, name: file.name || 'fichier.csv', size: file.size || 0, phase: 'reading', progress: 0, step: 'lecture', err: null, res: null, saving: null, saveErr: null, savedId: null, label: (file.name || '').replace(/\.[a-z0-9]+$/i, '') });
  var job = runJob({ op: 'readFile', file: file, o: { tz: P.tz, stamp: P.stamp, tick: 0.25 } }, null, function (p) {
    if (FILE.file !== file) return; FILE.progress = p.p || 0; FILE.step = p.phase === 'scan' ? 'ordre des dates' : 'lecture'; paintProgress();
  });
  FILE.cancel = job.cancel;
  job.promise.then(function (r) {
    if (FILE.file !== file) return;
    FILE.cancel = null; FILE.res = r; FILE.phase = r.parse && r.parse.error ? 'error' : 'ready'; FILE.err = r.parse && r.parse.error ? r.parse.error : null;
    if (ctx.tab === 'series') ctx.rerender();
  }, function (e) {
    if (FILE.file !== file) return;
    FILE.cancel = null; FILE.phase = e && e.code === 'cancelled' ? 'idle' : 'error'; FILE.err = e && e.code === 'cancelled' ? null : String(e && e.message || e);
    if (ctx.tab === 'series') ctx.rerender();
  });
  ctx.rerender();
}
function fileButton(label, kind, ctx) {
  var input = h('input', { type: 'file', accept: '.csv,.txt,.tsv,text/csv,text/plain', on: { change: function () { var f = input.files && input.files[0]; if (f) startRead(f, ctx); } } });
  return h('label', { class: 'btn sm dn-file' + (kind ? ' ' + kind : ''), role: 'button', tabindex: '0', on: { keydown: function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } } } }, label, input);
}
function fileMeta(P) {
  var r = FILE.res;
  return { name: (FILE.label || '').trim() || 'Barres d’une minute', instrument: P.instrument, source: 'fichier', srcTz: P.tz, stamp: P.stamp, roll: P.roll, D: r.D, note: 'Fichier « ' + FILE.name + ' », lu sur l’appareil.' };
}
function canUse(r) {
  if (!r || !r.cols || !r.cols.t.length) return 'Aucune barre lisible.';
  if (r.misaligned) return plural(r.misaligned, 'barre') + ' hors des minutes entières : le Labo suppose des barres d’une minute alignées.';
  if (!r.D) return 'Prix non décimaux au pas 1/4, 1/100 ou 1/10 000 : série ajustée par ratio ?';
  return null;
}
function useForVisit(ctx) {
  var r = FILE.res, why = canUse(r); if (why) { T.toast(why); return; }
  var P = prefs(), m = fileMeta(P);
  DN.setVisit(DN.visitFromCols(r.cols, Object.assign({}, m, { id: 'visite', sessions: r.sessions, quality: r.quality, origin: r })));
  T.toast('Ce fichier sert au Labo pendant cette visite.');
  ctx.rerender();
}
function saveToAccount(ctx) {
  var r = FILE.res, why = canUse(r); if (why) { T.toast(why); return; }
  var P = prefs(), file = FILE.file;
  FILE.saving = { phase: 'codage', k: 0, n: 1 }; FILE.saveErr = null; ctx.rerender();
  DN.saveDataset(fileMeta(P), r.cols, function (p) { if (FILE.file !== file) return; FILE.saving = p; if (ctx.tab === 'series') ctx.rerender(); }).then(function (doc) {
    if (FILE.file !== file) return;
    FILE.saving = null; FILE.savedId = doc.id; UI.sel = doc.id; T.store.set('donnees:sel', doc.id);
    T.toast('Jeu enregistré dans ton compte.'); if (ctx.tab === 'series') ctx.rerender();
  }, function (e) {
    if (FILE.file !== file) return;
    FILE.saving = null; FILE.saveErr = DN.errorText(e); if (ctx.tab === 'series') ctx.rerender();
  });
}
function fileCard(ctx) {
  var P = prefs(), body = [], r = FILE.res;
  var reread = function () { if (FILE.file && (FILE.phase === 'ready' || FILE.phase === 'error')) startRead(FILE.file, ctx); else ctx.rerender(); };
  if (FILE.phase === 'idle') {
    body.push(U.note('Barres d’une minute en CSV : une colonne time (ou date et heure), open, high, low, close, et volume si la source en a. Séparateur, virgule décimale et ordre des dates sont reconnus. Le fichier est lu sur cet appareil, par tranches de 4 Mo, sans bloquer l’écran.'));
  } else if (FILE.phase === 'reading') {
    var bar = h('i', { style: 'width:0%' }), tx = h('span', null, '');
    FILE.progEl = bar; FILE.progTx = tx;
    body.push(h('div', { class: 'dn-prog' }, h('div', { class: 'dn-line' }, h('b', null, '« ' + FILE.name + ' »'), h('span', null, fmtBytes(FILE.size)), tx), h('div', { class: 'dn-bar' }, bar)));
    body.push(h('div', { class: 'dn-acts' }, U.button({ label: 'Annuler', small: true, kind: 'ghost', onClick: function () { if (FILE.cancel) FILE.cancel(); } })));
    paintProgress();
  } else if (FILE.phase === 'error') {
    body.push(U.note('« ' + FILE.name + ' » : ' + (FILE.err || 'lecture impossible.') + (r && r.parse && r.parse.firstSkip ? ' Première ligne refusée : ' + r.parse.firstSkip.line + '.' : ''), true));
  } else if (FILE.phase === 'ready' && r) {
    var p = r.parse;
    body.push(h('div', { class: 'dn-line' }, h('b', null, '« ' + FILE.name + ' »'), h('span', null, F.int(p.n) + ' barres'), h('span', null, plural(r.sessions.length, 'séance')),
      h('span', null, 'du ' + fmtKey(r.quality.from) + ' au ' + fmtKey(r.quality.to)), h('span', null, 'séparateur : ' + p.sepName), h('span', null, 'temps : ' + (TIME_KIND[p.timeKind] || p.timeKind || '—')), h('span', null, fmtBytes(FILE.size))));
    if (p.skipped) body.push(U.note(plural(p.skipped, 'ligne ignorée', 'lignes ignorées') + (p.firstSkip ? ' (ligne ' + p.firstSkip.line + ' : « ' + p.firstSkip.text + ' »)' : '') + '.', true));
    if (p.dup) body.push(U.note(plural(p.dup, 'horodatage en double', 'horodatages en double') + ' : la dernière ligne lue est gardée.'));
    if (p.fixed) body.push(U.note(plural(p.fixed, 'barre réparée', 'barres réparées') + ' : plus haut et plus bas ramenés au maximum et au minimum des quatre prix.'));
    (p.warnings || []).forEach(function (w) { body.push(U.note(w, true)); });
    var why = canUse(r); if (why) body.push(U.note(why, true));
  }
  body.push(U.fields([
    { type: 'select', label: 'Fuseau du fichier', value: P.tz, options: TZ_OPTS, full: true, hint: 'utilisé seulement si l’heure n’indique pas son fuseau', onChange: function (v) { setPrefs({ tz: v }); reread(); } },
    h('div', { class: 'fld full' }, h('label', null, 'L’heure d’une barre marque'), U.seg({ aria: 'Horodatage', options: [{ v: 'ouverture', label: 'son ouverture' }, { v: 'cloture', label: 'sa clôture' }], value: P.stamp, onChange: function (v) { setPrefs({ stamp: v }); reread(); } }))
  ]));
  if (FILE.phase === 'ready' && r && !canUse(r)) {
    body.push(U.fields([
      { type: 'text', label: 'Nom du jeu', value: FILE.label, full: true, onChange: function (v) { FILE.label = v; } },
      h('div', { class: 'fld' }, h('label', null, 'Instrument'), U.seg({ aria: 'Instrument', options: [{ v: 'MNQ', label: 'MNQ' }, { v: 'NQ', label: 'NQ' }], value: P.instrument, onChange: function (v) { setPrefs({ instrument: v }); ctx.rerender(); } })),
      { type: 'select', label: 'Contrat continu', value: P.roll, options: [{ v: 'inconnu', label: 'je ne sais pas' }, { v: 'ajuste', label: 'ajusté' }, { v: 'non-ajuste', label: 'non ajusté' }], hint: 'bascule d’échéance', onChange: function (v) { setPrefs({ roll: v }); } }
    ]));
    if (FILE.saving) body.push(wait(({ codage: 'Codage des séances…', envoi: 'Envoi de l’année ' + (FILE.saving.year || '') + ' (' + ((FILE.saving.k || 0) + 1) + ' sur ' + (FILE.saving.n || 1) + ')…', fiche: 'Écriture de la fiche du jeu…', fini: 'Terminé.' })[FILE.saving.phase] || 'Enregistrement…'));
    if (FILE.saveErr) body.push(U.note(FILE.saveErr, true));
    if (FILE.savedId) body.push(U.note('Enregistré dans ton compte : le jeu figure plus bas, avec ses fichiers par année.'));
    var isVisit = VISIT && VISIT.origin === r;
    body.push(h('div', { class: 'dn-acts' },
      U.button({ label: isVisit ? 'Utilisé pour cette visite' : 'Utiliser pour cette visite', kind: isVisit ? 'acc' : 'pri', small: true, disabled: !!isVisit, onClick: function () { useForVisit(ctx); } }),
      U.button({ label: 'Enregistrer dans mon compte', small: true, disabled: !!FILE.saving || UI.assets !== true || !!FILE.savedId, onClick: function () { saveToAccount(ctx); } })));
    if (UI.assets === false) body.push(U.note('Enregistrer demande l’artefact ouvert dans claude.ai, avec le droit de le modifier. Sinon, envoie le fichier à Claude : il l’écrit pour toi.'));
    if (UI.assets === null) body.push(U.note('Vérification du droit d’enregistrer…'));
  }
  body.push(h('div', { class: 'dn-acts' }, FILE.phase === 'reading' ? null : fileButton(FILE.file ? 'Changer de fichier' : 'Choisir un fichier CSV', FILE.file ? null : 'pri', ctx),
    FILE.file && FILE.phase !== 'reading' ? U.button({ label: 'Effacer', small: true, kind: 'ghost', onClick: function () { if (VISIT && FILE.res && VISIT.origin === FILE.res) DN.setVisit(null); FILE = { file: null, name: '', size: 0, phase: 'idle', progress: 0, step: '', err: null, res: null, cancel: null, saving: null, saveErr: null, savedId: null, label: '', progEl: null, progTx: null }; ctx.rerender(); } }) : null));
  var card = U.card({ title: 'Fichier de cet appareil', meta: FILE.phase === 'ready' ? 'lu' : FILE.phase === 'reading' ? 'lecture' : FILE.phase === 'error' ? 'refusé' : 'à choisir', body: body });
  var out = [card];
  if (FILE.phase === 'ready' && r && r.quality && !FILE.savedId && !(VISIT && VISIT.origin === r)) { var s = U.section('Qualité du *fichier*', plural(r.sessions.length, 'séance')); s.appendChild(qualityView(r.quality)); out.push(s); }
  return out;
}
function visitSection(ctx) {
  var V = VISIT, sec = U.section('Jeu de cette *visite*', V ? (V.meta.source === 'synthetique' ? 'synthétique' : 'fichier local') : 'aucun');
  if (!V) {
    sec.appendChild(U.note('Aucun jeu en mémoire. Sans fichier ni jeu du compte, le Labo tourne sur une marche aléatoire sans dérive, annoncée comme telle : aucun avantage n’y existe.'));
    if (T.lib.laboEngine && typeof T.lib.laboEngine.op === 'function') sec.appendChild(h('div', { class: 'dn-acts' }, U.button({ label: 'Charger une marche sans dérive', small: true, kind: 'ghost', onClick: function () {
      try { DN.setVisit(DN.synthetic({ seed: 1, sessions: 60, sigma: 2 })); } catch (e) { T.toast(String(e && e.message || e)); }
      ctx.rerender();
    } })));
    return sec;
  }
  var m = V.meta, synth = m.source === 'synthetique';
  var body = [h('div', { class: 'dn-acts' }, U.pill(synth ? 'synthétique, pas le marché' : 'fichier local', synth ? 'acc' : 'on'), U.pill(m.instrument || 'MNQ'))];
  body.push(kv([['Période', fmtKey(m.from) + ' → ' + fmtKey(m.to)], ['Séances', F.int(m.sessions)], ['Barres', F.int(m.bars)], ['Volume', m.hasVolume ? 'oui' : 'non'], ['Pas de prix', m.D ? '1/' + F.int(m.D) : '—'], ['Empreinte', m.fingerprint ? DN.shortPrint(m.fingerprint) : '—']]));
  if (synth || m.note) body.push(U.note(synth ? 'Aucun avantage n’existe ici : une stratégie qui y gagne est surajustée.' : m.note));
  body.push(U.note('Gardé en mémoire le temps de la page, sur cet appareil : rien n’est envoyé. Les essais du Labo sur ce jeu comptent pour la visite seulement.'));
  body.push(h('div', { class: 'dn-acts' }, U.button({ label: 'Ne plus l’utiliser', small: true, kind: 'ghost', onClick: function () { DN.setVisit(null); ctx.rerender(); } })));
  sec.appendChild(U.card({ title: m.name || 'Jeu de la visite', meta: plural(m.sessions || 0, 'séance'), accent: true, body: body }));
  if (V.quality && !(FILE.res && V.origin === FILE.res && FILE.phase !== 'ready')) sec.appendChild(qualityView(V.quality));
  return sec;
}
function ensureReport(meta, ctx) {
  var R = UI.report;
  if (R && R.id === meta.id && R.u === meta.u) return;
  R = UI.report = { id: meta.id, u: meta.u, phase: 'loading', q: null, err: null };
  DN.loadDataset(meta.id).then(function (ds) {
    var b = ds.bars; return runJob({ op: 'quality', cols: { t: b.t, o: b.o, h: b.h, l: b.l, c: b.c, v: ds.meta.hasVolume ? b.v : null }, o: { tick: 0.25 } }).promise;
  }).then(function (q) { if (UI.report !== R) return; R.phase = 'ready'; R.q = q; if (ctx.tab === 'series') ctx.rerender(); },
    function (e) { if (UI.report !== R) return; R.phase = 'error'; R.err = DN.errorText(e); if (ctx.tab === 'series') ctx.rerender(); });
}
function datasetCard(meta, ctx) {
  var usable = DN.usable(meta), sel = UI.sel === meta.id, assets = meta.assets || [], bytes = 0;
  assets.forEach(function (x) { bytes += x.bytes || 0; });
  var state = meta.deleting ? U.pill('suppression', 'no') : meta.complete !== true ? U.pill('incomplet', 'no') : U.pill('complet', 'on');
  var body = [kv([
    ['Instrument', meta.instrument || '—'], ['Période', fmtKey(meta.from) + ' → ' + fmtKey(meta.to)], ['Séances', fin(meta.sessions) ? F.int(meta.sessions) : '—'], ['Barres', fin(meta.bars) ? F.int(meta.bars) : '—'],
    ['Volume', meta.hasVolume ? 'oui' : 'non'], ['Pas de prix', fin(meta.D) ? '1/' + F.int(meta.D) : '—'], ['Contrat continu', ROLL[meta.roll] || 'inconnu'],
    ['Horodatage', meta.stamp === 'cloture' ? 'clôture, recalé à l’ouverture' : 'ouverture'], ['Fichiers', assets.length ? plural(assets.length, 'année') + ' · ' + fmtBytes(bytes) : 'aucun'],
    ['Source', meta.source === 'claude' ? 'écrit par Claude' : meta.source === 'synthetique' ? 'synthétique' : 'fichier'], ['Empreinte', meta.fingerprint ? DN.shortPrint(meta.fingerprint) : '—'], ['Ajouté le', fmtWhen(meta.createdAt || meta.u)]
  ])];
  if (meta.note) body.push(U.note(String(meta.note)));
  if (meta.deleting) body.push(U.note('Suppression commencée : ce jeu n’est plus jamais lu. Elle se termine quand ses fichiers sont effacés.', true));
  else if (meta.complete !== true) body.push(U.note('Import inachevé : tant que la fiche ne porte pas « complet », aucun calcul ne lit ce jeu.', true));
  var acts = [];
  if (usable) acts.push(U.button({ label: sel ? 'Masquer le rapport' : 'Rapport de qualité', small: true, kind: sel ? null : 'pri', onClick: function () { UI.sel = sel ? null : meta.id; T.store.set('donnees:sel', UI.sel); ctx.rerender(); } }));
  if (UI.confirmDel === meta.id) {
    acts.push(U.button({ label: UI.delBusy === meta.id ? 'Suppression…' : 'Confirmer la suppression', small: true, kind: 'acc', disabled: UI.delBusy === meta.id, onClick: function () {
      UI.delBusy = meta.id; UI.delErr = null; ctx.rerender();
      DN.deleteDataset(meta.id).then(function () { UI.delBusy = null; UI.confirmDel = null; if (UI.sel === meta.id) { UI.sel = null; T.store.set('donnees:sel', null); } T.toast('Jeu supprimé.'); ctx.rerender(); },
        function (e) { UI.delBusy = null; UI.delErr = { id: meta.id, text: DN.errorText(e) }; ctx.rerender(); });
    } }));
    acts.push(U.button({ label: 'Annuler', small: true, kind: 'ghost', onClick: function () { UI.confirmDel = null; ctx.rerender(); } }));
  } else acts.push(U.button({ label: 'Supprimer', small: true, kind: 'ghost', onClick: function () { UI.confirmDel = meta.id; UI.delErr = null; ctx.rerender(); } }));
  body.push(h('div', { class: 'dn-acts' }, acts));
  if (UI.delErr && UI.delErr.id === meta.id) body.push(U.note(UI.delErr.text, true));
  if (sel && usable) {
    ensureReport(meta, ctx);
    var R = UI.report;
    body.push(R.phase === 'loading' ? wait('Lecture des fichiers et contrôle…') : R.phase === 'error' ? U.note(R.err, true) : qualityView(R.q));
  }
  return U.card({ title: meta.name || meta.id, meta: state, body: body });
}
function storageCard() {
  var u = DN.docUsage(), slot = h('div', { class: 'dn-line' }, h('span', null, 'Fichiers attachés : lecture…'));
  DN.assetUsage().then(function (a) {
    if (!slot.isConnected) return; T.clear(slot);
    if (a.source === 'compte') slot.appendChild(h('span', null, h('b', null, fmtBytes(a.bytes)), ' de fichiers attachés' + (fin(a.maxBytes) ? ' sur ' + fmtBytes(a.maxBytes) : '') + ' · ' + plural(a.files || 0, 'fichier') + (fin(a.maxFiles) ? ' sur ' + F.int(a.maxFiles) : '')));
    else if (!(a.files > 0)) slot.appendChild(h('span', null, 'Aucun fichier de barres enregistré.'));
    else slot.appendChild(h('span', null, h('b', null, fmtBytes(a.bytes)), ' de fichiers de barres selon les fiches des jeux · ' + plural(a.files || 0, 'fichier')));
  });
  var parts = u.parts.filter(function (p) { return p.n > 0; });
  return U.card({ title: 'Stockage du compte', meta: F.int(u.docs) + ' / 25 000', body: [
    C.gauge({ value: u.docs, min: 0, max: u.limit, ticks: [[0, '0'], [u.limit / 2, F.int(u.limit / 2)], [u.limit, F.int(u.limit)]] }),
    h('div', { class: 'dn-line' }, h('span', null, h('b', null, F.int(u.docs)), ' documents connus de cet appareil, sur 25 000 permis')),
    parts.length ? h('div', { class: 'dn-chips' }, parts.map(function (p) { return h('span', { class: 'dn-chip' }, p.label, h('b', null, F.int(p.n))); })) : null,
    slot,
    U.note('Compte établi sur les copies locales : les résultats mis en cache par le Labo n’y figurent pas.')
  ] });
}
function renderSeries(root, ctx, subs) {
  probeAssets(ctx);
  var col = coll('datasets/items'); subs.push(col.on(function () { if (ctx.tab === 'series') ctx.rerender(); }));
  subs.push(DN.onVisit(function () { if (ctx.tab === 'series') ctx.rerender(); }));
  if (UI.sel == null) UI.sel = T.store.get('donnees:sel', null);
  root.appendChild(visitSection(ctx));
  var s1 = U.section('Lire un *fichier*', 'CSV de barres d’une minute'), fc = fileCard(ctx);
  s1.appendChild(fc[0]); root.appendChild(s1);
  fc.slice(1).forEach(function (el) { root.appendChild(el); });
  var list = DN.datasets(), s2 = U.section('Jeux de ton *compte*', list.length ? plural(list.length, 'jeu', 'jeux') : 'aucun');
  if (!list.length) s2.appendChild(U.empty({ title: 'Aucun jeu enregistré', text: 'Envoie à Claude l’export CSV de ta plateforme : il découpe les barres par année, les écrit dans ton compte et dépose un élément dans la boîte. Tu peux aussi enregistrer un fichier lu ici.', action: U.button({ label: 'Que lui envoyer ?', small: true, onClick: function () { ctx.setTab('envoyer'); } }) }));
  else list.forEach(function (m) { s2.appendChild(datasetCard(m, ctx)); });
  root.appendChild(s2);
  var s3 = U.section('Ce que ton compte *contient*'); s3.appendChild(storageCard()); root.appendChild(s3);
}

/* ---------------- Onglet Niveaux ---------------- */
function renderLevels(root, ctx, subs) {
  var col = coll('levels/items'); subs.push(col.on(function () { if (ctx.tab === 'niveaux') ctx.rerender(); }));
  var days = DN.levelDays(), months = {}, noBase = days.filter(function (d) { return d.scale === 'NDX' && d.base == null; });
  days.forEach(function (d) { months[d.month] = 1; });
  var nLv = 0; days.forEach(function (d) { nLv += d.n; });
  root.appendChild(U.kpis([
    { label: 'Séances', value: F.int(days.length), hint: plural(Object.keys(months).length, 'mois') },
    { label: 'Niveaux', value: F.int(nLv), hint: days.length ? F.num(nLv / days.length, 1) + ' par séance' : 'rien encore' },
    { label: 'Dernière', value: days.length ? fmtKeyShort(days[0].key) : '—', hint: days.length ? plural(days[0].n, 'niveau', 'niveaux') : 'rien encore' },
    { label: 'NDX sans base', value: F.int(noBase.length), tone: noBase.length ? 'neg' : null, hint: noBase.length ? 'refusés par le Labo' : 'aucun' }
  ]));
  if (!days.length) {
    root.appendChild(U.empty({ title: 'Aucun niveau pour l’instant', text: 'Envoie à Claude un collage « NOM : prix » (export d’un robot GEX ou ta propre liste), la date de la séance et l’échelle : prix du contrat, ou de l’indice NDX avec la base NQ − NDX du jour. Il les range ici, séance par séance.', action: U.button({ label: 'Que lui envoyer ?', small: true, onClick: function () { ctx.setTab('envoyer'); } }) }));
    return;
  }
  var cur = days.find(function (d) { return d.key === UI.day; }) || days[0]; UI.day = cur.key;
  var add = cur.scale === 'NDX' && cur.base != null ? cur.base : 0, conv = cur.scale !== 'NDX' || cur.base != null;
  var rows = cur.names.map(function (n) { var v = Number(cur.levels[n]); return { name: n, v: v, c: conv ? v + add : NaN }; }).sort(function (a, b) { return b.v - a.v; });
  var s1 = U.section('Séance du *' + fmtKey(cur.key) + '*', conv && cur.scale === 'NDX' ? 'prix ramenés au contrat' : null);
  var body = [h('div', { class: 'dn-acts' }, U.pill(cur.scale === 'NDX' ? 'échelle NDX' : 'échelle contrat', 'on'), cur.scale === 'NDX' ? U.pill(cur.base != null ? 'base ' + F.num(cur.base, 2) : 'base absente', cur.base != null ? null : 'no') : null)];
  var lad = rows.filter(function (r) { return isFinite(conv ? r.c : r.v); });
  if (lad.length >= 2) body.push(C.ladder({ levels: lad.map(function (r) { return { price: conv ? r.c : r.v, label: r.name, kind: /HVL|FLIP/i.test(r.name) ? 'violet' : null }; }), fmt: function (v) { return F.num(v, 2); } }));
  body.push(U.table({ cols: [{ k: 'name', label: 'Nom' }, { k: 'v', label: cur.scale === 'NDX' ? 'NDX' : 'Prix', align: 'r', fmt: function (v) { return F.num(v, 2); } }].concat(cur.scale === 'NDX' ? [{ k: 'c', label: 'Contrat', align: 'r', fmt: function (v) { return isFinite(v) ? F.num(v, 2) : '—'; } }] : []), rows: rows }));
  if (cur.scale === 'NDX' && cur.base == null) body.push(U.note('Échelle NDX sans base : le Labo refuse ces niveaux tant que la base NQ − NDX de ce jour n’est pas écrite.', true));
  else if (cur.scale === 'NDX') body.push(U.note('Le Labo lit niveau + base (' + F.num(cur.base, 2) + ' points), puis l’ajustement de roll de la séance s’il y en a un.'));
  s1.appendChild(U.card({ title: plural(rows.length, 'niveau', 'niveaux'), meta: cur.source ? 'source : ' + cur.source : null, body: body }));
  root.appendChild(s1);
  var s2 = U.section('Toutes les *séances*', 'touche une ligne');
  s2.appendChild(U.table({ cols: [{ k: 'key', label: 'Séance', fmt: function (v) { return fmtKey(v); } }, { k: 'scale', label: 'Échelle' }, { k: 'base', label: 'Base', align: 'r', fmt: function (v, r) { return r.scale === 'NDX' ? (v == null ? 'absente' : F.num(v, 2)) : '—'; } }, { k: 'n', label: 'Niveaux', align: 'r' }, { k: 'source', label: 'Source', fmt: function (v) { return v || '—'; } }],
    rows: days.slice(0, 120), rowClass: function (r) { return r.key === cur.key ? 'sel' : null; }, onRow: function (r) { UI.day = r.key; ctx.rerender(); } }));
  if (days.length > 120) s2.appendChild(U.note('Les 120 séances les plus récentes sont listées.'));
  root.appendChild(s2);
  root.appendChild(U.note('Un niveau se lit par la clé de la séance Globex : la séance du lundi commence le dimanche à 18 h New York. Sur un contrat continu ajusté, le Labo ajoute l’ajustement de la séance ; sans lui, un niveau est refusé plutôt que décalé.'));
}

/* ---------------- Onglet Envoyer ---------------- */
function renderSend(root) {
  root.appendChild(U.callout([h('b', null, 'Tu n’as rien à saisir. '), 'Envoie tes fichiers et tes captures à Claude dans la conversation : il les vérifie, les écrit dans ton compte, et dépose un élément dans la boîte avec un lien vers l’endroit où les retrouver.']));
  var s = U.section('Ce qu’il faut *envoyer*');
  s.appendChild(U.card({ title: 'Barres d’une minute', meta: 'CSV', body: [
    h('ol', { class: 'dn-steps' },
      h('li', null, h('b', null, 'L’export CSV de ta plateforme'), ', en barres d’une minute du MNQ ou du NQ : colonnes time (ou date et heure), open, high, low, close, volume.'),
      h('li', null, h('b', null, 'La convention d’horodatage'), ' : l’heure d’une barre marque-t-elle son ouverture ou sa clôture ? Et son fuseau, si l’heure n’en porte pas.'),
      h('li', null, h('b', null, 'Le contrat continu'), ' : ajusté à la bascule d’échéance, non ajusté, ou tu ne sais pas. Le rapport de qualité signale les sauts.')),
    U.note('Claude découpe par année (un fichier par an, plusieurs années possibles), vérifie que les prix tombent sur le pas de cotation et que chaque barre commence sur une minute entière.')] }));
  s.appendChild(U.card({ title: 'Tes trades', meta: 'CSV', body: [
    h('ol', { class: 'dn-steps' },
      h('li', null, h('b', null, 'L’export CSV de ta plateforme'), ' : la liste des exécutions ou celle des trades, avec symbole, sens, quantité, prix et heures, P&L et commission si elle y figure.'),
      h('li', null, h('b', null, 'Le fuseau'), ' des heures du fichier.')),
    U.note('Les exécutions sont appariées en allers-retours, la première entrée sortie la première. Un trade déjà présent n’est jamais réécrit : tes annotations restent. Un trade sans stop connu n’a pas de R : ajoute le stop dans le journal si tu veux le calculer.')] }));
  s.appendChild(U.card({ title: 'Niveaux', meta: 'collage', body: [
    h('ol', { class: 'dn-steps' },
      h('li', null, h('b', null, 'Un collage « NOM : prix »'), ', tel quel : l’export d’un robot GEX ou ta propre liste.'),
      h('li', null, h('b', null, 'La date de la séance'), ' et l’échelle : prix du contrat, ou de l’indice NDX avec la base NQ − NDX du jour.')),
    U.note('Le signe moins est conservé, et un nombre trop loin des autres (un en-tête, une année) est écarté.')] }));
  s.appendChild(U.card({ title: 'Captures et descriptions', meta: 'images, texte', body: [
    U.prose(['<b>Rapports macro et calendrier</b> : Claude les transcrit en français dans le desk Macro.', '<b>Une idée de stratégie</b>, en quelques phrases : Claude l’écrit en règles, la vérifie et te montre sa lecture en français avant de l’enregistrer dans le Labo.'])] }));
  root.appendChild(s);
  var s2 = U.section('Ce que Claude *fait*');
  s2.appendChild(U.card({ title: 'De ton fichier à ton compte', body: [
    h('ol', { class: 'dn-steps' },
      h('li', null, 'Il lit le fichier avec le même lecteur que cette page, et produit les fichiers par année et les documents.'),
      h('li', null, 'Il liste d’abord ce que ton compte contient, pour ne rien écraser.'),
      h('li', null, 'Il écrit dans l’ordre : fichiers, puis fiche du jeu marquée complète, puis l’élément de la boîte, toujours en dernier.')),
    h('details', { class: 'dn-det' }, h('summary', null, 'Les commandes'),
      h('pre', { class: 'dn-code' }, 'node tools/ingest.js bars FICHIER.csv \\\n  --tz America/New_York --stamp ouverture \\\n  --instrument MNQ --roll inconnu \\\n  --existing LISTE --out SORTIE\n\nnode tools/ingest.js trades FICHIER.csv \\\n  --tz Europe/Paris --instrument MNQ \\\n  --existing LISTE --out SORTIE\n\nnode tools/ingest.js levels COLLAGE.txt \\\n  --date AAAA-MM-JJ --scale contrat --out SORTIE'))] }));
  s2.appendChild(U.card({ title: 'Un nouveau lien', body: [U.note('La base et les fichiers d’un artefact appartiennent à son lien. Avant d’annoncer un nouveau lien, Claude recopie tout : essais et hors échantillon, stratégies et résultats, fichiers de barres et jeux, niveaux, journal, boîte, puis tes réglages. Un élément « migration » arrive ensuite dans la boîte.')] }));
  root.appendChild(s2);
  var s3 = U.section('Ce que ton compte *contient*'); s3.appendChild(storageCard()); root.appendChild(s3);
}

T.desk({
  id: 'donnees', label: 'Données & imports', glyph: '⇣', group: 'Système', order: 85,
  tabs: [{ id: 'boite', label: 'Boîte' }, { id: 'series', label: 'Séries' }, { id: 'niveaux', label: 'Niveaux' }, { id: 'envoyer', label: 'Envoyer' }],
  render: function (root, ctx) {
    injectCss();
    var tab = this.tabs.some(function (t) { return t.id === ctx.tab; }) ? ctx.tab : 'boite', subs = [];
    ctx.tab = tab;
    root.appendChild(U.page({ kicker: 'Données & imports', title: 'Tes données, *vérifiées*.', lede: 'Ce que Claude a écrit pour toi, tes jeux de barres et tes niveaux. Rien n’est inventé : sans fichier, le Labo tourne sur une marche sans dérive, annoncée comme telle.' }));
    root.appendChild(U.tabs({ tabs: this.tabs, value: tab, onChange: function (t) { UI.confirmDel = null; ctx.setTab(t); } }));
    if (tab === 'boite') renderInbox(root, ctx, subs);
    else if (tab === 'series') renderSeries(root, ctx, subs);
    else if (tab === 'niveaux') renderLevels(root, ctx, subs);
    else renderSend(root);
    return function () { subs.forEach(function (f) { try { f(); } catch (e) {} }); FILE.progEl = null; FILE.progTx = null; };
  }
});
