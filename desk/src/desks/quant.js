/* Desk « Quant & backtest » : Monte-Carlo au niveau des trades, backtest de la bande VWAP sur les barres
   d’une minute que l’utilisateur fournit, balayage de robustesse (CSCV, Sharpe déflaté) et mur d’échantillon.
   Sources, contrôlées par test/quant.test.js :
   – ALP nº 3, onzième partie : « À dérive nulle, les quatre droites valent exactement −c/L » (arrêt optionnel) ;
     quatorzième partie : « E[R] = −c/a, quelle que soit la loi des incréments ».
   – ALP nº 3, huitième partie, table 14 : 619 décisions (route 1, test t unilatéral à 5 %, puissance 80 %)
     contre 555 (route 2, seuil déflaté √(2 ln B), B = 16 configurations) pour un Sharpe de 0,10 par décision.
   – CSCV et probabilité de surapprentissage : portage ligne à ligne de alp1/overfit.py (cscv), arrondi
     bancaire des bornes de blocs compris ; Sharpe déflaté : alp1/overfit.py (expected_max_sharpe,
     deflated_sharpe) et alp1/pathstats.py (probabilistic_sharpe).
   Aucun prix de marché n’est écrit ici : le backtest ne tourne que sur le fichier de l’utilisateur ou sur
   une marche aléatoire synthétique, déclarée comme telle. */
var h = T.h, U = T.ui, C = T.chart, F = T.fmt, S = T.stats;
T.lib = T.lib || {};
var Q = T.lib.quant = {};
var KEY = { mc: 'quant:mc', bt: 'quant:bt', ech: 'quant:ech', last: 'quant:lastBacktest' };
Q.KEYS = KEY;
function fin(v) { return typeof v === 'number' && isFinite(v); }
Q.fin = fin;

/* =====================================================================
   1. Le moteur : une seule fonction autonome, exécutée dans un Web Worker
      par T.compute, et appelée telle quelle par les tests. Aucune variable
      extérieure : ni T, ni F, ni S.
   ===================================================================== */
function quantEngine(a) {
  var NY = 'America/New_York', PAR = 'Europe/Paris';
  function rng(seed) { var s = seed >>> 0; return function () { s = (s + 0x6D2B79F5) >>> 0; var t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  function gauss(r) { var u = r(); while (u <= 1e-300) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function q(sorted, p) { var n = sorted.length; if (!n) return NaN; var x = (n - 1) * p, lo = Math.floor(x), hi = Math.ceil(x); return sorted[lo] + (sorted[hi] - sorted[lo]) * (x - lo); }
  function sortedCopy(arr) { var f = new Float64Array(arr.length); for (var i = 0; i < arr.length; i++) f[i] = arr[i]; f.sort(); return f; }
  function mean(x) { var s = 0; for (var i = 0; i < x.length; i++) s += x[i]; return x.length ? s / x.length : NaN; }

  /* ---- Fuseaux : décalage (ms) à ajouter à l’instant UTC pour lire l’heure murale. Les changements
     d’heure de New York, Chicago et Paris tombent sur des heures pleines UTC : un cache par heure est exact. */
  var OFF = {}, FMT = {};
  function off(tz, t) {
    if (!tz || tz === 'UTC') return 0;
    var hr = Math.floor(t / 3600000), key = tz + '|' + hr, v = OFF[key];
    if (v !== undefined) return v;
    var f = FMT[tz]; if (!f) f = FMT[tz] = new Intl.DateTimeFormat('en-US', { timeZone: tz, hourCycle: 'h23', year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric', second: 'numeric' });
    var o = {}, ps = f.formatToParts(new Date(hr * 3600000)); for (var i = 0; i < ps.length; i++) o[ps[i].type] = ps[i].value;
    v = Date.UTC(+o.year, +o.month - 1, +o.day, (+o.hour) % 24, +o.minute, +o.second) - hr * 3600000;
    OFF[key] = v; return v;
  }
  function wall(y, mo, d, hh, mi, ss, tz) { var g = Date.UTC(y, mo - 1, d, hh, mi, ss || 0); var t = g - off(tz, g); return g - off(tz, t); }

  /* ---- Lecture d’un CSV de barres ---- */
  function splitLine(line, sep) {
    if (line.indexOf('"') < 0) return line.split(sep);
    var out = [], cur = '', inq = false;
    for (var i = 0; i < line.length; i++) { var ch = line[i]; if (ch === '"') { if (inq && line[i + 1] === '"') { cur += '"'; i++; } else inq = !inq; } else if (ch === sep && !inq) { out.push(cur); cur = ''; } else cur += ch; }
    out.push(cur); return out;
  }
  function clean(s) { return String(s == null ? '' : s).trim().replace(/^["']+|["']+$/g, '').trim(); }
  function normH(s) { return clean(s).replace(/^<|>$/g, '').toLowerCase(); }
  function num(s, dec) {
    s = clean(s).replace(/[\s  ]/g, '');
    if (!s) return NaN;
    if (dec) { if (s.indexOf(',') >= 0 && s.indexOf('.') >= 0) s = s.replace(/\./g, ''); s = s.replace(',', '.'); }
    var x = Number(s); return isFinite(x) ? x : NaN;
  }
  var ALIAS = {
    time: ['time', 'datetime', 'date/time', 'date time', 'date_time', 'timestamp', 'time (utc)', 'gmt time', 'local time', 'horodatage'],
    date: ['date', 'day', 'jour'], open: ['open', 'o', 'ouverture', 'first'], high: ['high', 'h', 'haut', 'plus haut', 'max'],
    low: ['low', 'l', 'bas', 'plus bas', 'min'], close: ['close', 'c', 'last', 'dernier', 'clôture', 'cloture', 'price'],
    vol: ['volume', 'vol', 'v', 'tickvol', 'tick volume', 'volume total', 'totalvolume']
  };
  function isClock(s) { return /^\d{1,2}:\d{2}(:\d{2}([.,]\d+)?)?$/.test(s) || /^\d{4}(\d{2})?$/.test(s); }
  function clockOf(s) { if (/^\d{4}(\d{2})?$/.test(s)) return s.slice(0, 2) + ':' + s.slice(2, 4) + (s.length === 6 ? ':' + s.slice(4) : ''); return s; }
  var ZRE = '\\s*(Z|UTC|GMT|[+-]\\d{2}(?::?\\d{2})?)?$';
  var RE_YMD = new RegExp('^(\\d{4})[-/.](\\d{1,2})[-/.](\\d{1,2})(?:[T ]+(\\d{1,2}):(\\d{2})(?::(\\d{2})(?:[.,]\\d+)?)?)?' + ZRE, 'i');
  var RE_DMY = new RegExp('^(\\d{1,2})[-/.](\\d{1,2})[-/.](\\d{4})(?:[T ]+(\\d{1,2}):(\\d{2})(?::(\\d{2})(?:[.,]\\d+)?)?)?' + ZRE, 'i');
  var RE_PACK = /^(\d{4})(\d{2})(\d{2})[ T]?(\d{2})(\d{2})(\d{2})?$/;
  function parseTime(s, tz, order) {
    if (!s) return null;
    var m, y, mo, d, hh, mi, ss, z;
    var pk = /^(19|20)\d{6}(\d{4}|\d{6})$/.test(s) ? RE_PACK.exec(s) : null;
    if (pk && !(+pk[2] >= 1 && +pk[2] <= 12 && +pk[3] >= 1 && +pk[3] <= 31 && +pk[4] <= 23 && +pk[5] <= 59)) pk = null;
    if (!pk && /^-?\d+(\.\d+)?$/.test(s)) { var x = +s; if (x > 1e11) return { t: Math.round(x), k: 'ms' }; if (x > 1e8) return { t: Math.round(x * 1000), k: 's' }; return null; }
    if ((m = RE_YMD.exec(s))) { y = +m[1]; mo = +m[2]; d = +m[3]; hh = +(m[4] || 0); mi = +(m[5] || 0); ss = +(m[6] || 0); z = m[7]; }
    else if ((m = RE_DMY.exec(s))) { if (order === 'mdy') { mo = +m[1]; d = +m[2]; } else { d = +m[1]; mo = +m[2]; } y = +m[3]; hh = +(m[4] || 0); mi = +(m[5] || 0); ss = +(m[6] || 0); z = m[7]; }
    else if ((m = RE_PACK.exec(s))) { y = +m[1]; mo = +m[2]; d = +m[3]; hh = +m[4]; mi = +m[5]; ss = +(m[6] || 0); }
    else return null;
    if (!(mo >= 1 && mo <= 12 && d >= 1 && d <= 31 && hh >= 0 && hh <= 23 && mi >= 0 && mi <= 59 && ss >= 0 && ss <= 60)) return null;
    if (z) {
      var offm = 0;
      if (/^[+-]/.test(z)) { var zz = z.replace(':', ''); offm = (zz[0] === '-' ? -1 : 1) * (+zz.slice(1, 3) * 60 + +(zz.slice(3, 5) || 0)); }
      return { t: Date.UTC(y, mo - 1, d, hh, mi, ss) - offm * 60000, k: 'iso' };
    }
    return { t: wall(y, mo, d, hh, mi, ss, tz), k: 'local' };
  }
  function parseCsv(text, o) {
    var tz = o.tz || NY;
    var res = { bars: [], n: 0, skipped: 0, firstSkip: null, sep: null, sepName: '', timeKind: '', hasVolume: false, stepMin: NaN, warnings: [], error: null, header: true, fixed: 0, dup: 0 };
    text = String(text == null ? '' : text).replace(/^﻿/, '');
    var lines = text.split(/\r\n|\n|\r/), first = -1, i;
    for (i = 0; i < lines.length; i++) if (lines[i].trim()) { first = i; break; }
    if (first < 0) { res.error = 'Le fichier est vide.'; return res; }
    var hl = lines[first], cands = [['\t', 'tabulation'], [';', 'point-virgule'], [',', 'virgule']], best = null, bc = 0;
    cands.forEach(function (c) { var k = hl.split(c[0]).length - 1; if (k > bc) { bc = k; best = c; } });
    if (!best) { res.error = 'Aucun séparateur reconnu : virgule, point-virgule ou tabulation.'; return res; }
    var sep = best[0], dec = sep !== ','; res.sep = sep; res.sepName = best[1];
    var head = splitLine(hl, sep).map(normH);
    function find(names) { for (var j = 0; j < head.length; j++) if (names.indexOf(head[j]) >= 0) return j; return -1; }
    var ix = { time: find(ALIAS.time), date: find(ALIAS.date), open: find(ALIAS.open), high: find(ALIAS.high), low: find(ALIAS.low), close: find(ALIAS.close), vol: find(ALIAS.vol) };
    var start = first + 1;
    if (ix.open < 0 || ix.high < 0 || ix.low < 0 || ix.close < 0) {
      var f0 = splitLine(hl, sep).map(clean), clk = f0.length >= 6 && isClock(f0[1]);
      var b = clk ? 2 : 1;
      if (f0.length >= b + 4 && [0, 1, 2, 3].every(function (k) { return isFinite(num(f0[b + k], dec)); })) {
        ix = clk ? { date: 0, time: 1, open: 2, high: 3, low: 4, close: 5, vol: f0.length > 6 ? 6 : -1 } : { time: 0, date: -1, open: 1, high: 2, low: 3, close: 4, vol: f0.length > 5 ? 5 : -1 };
        start = first; res.header = false;
      } else { res.error = 'Colonnes introuvables : il faut open, high, low, close, et time ou date.'; return res; }
    }
    if (ix.time < 0 && ix.date < 0) { res.error = 'Colonne de temps introuvable : time, date ou datetime.'; return res; }
    var raw = [], dmy = 0, mdy = 0;
    for (i = start; i < lines.length; i++) {
      var L = lines[i]; if (!L.trim()) continue;
      var f = splitLine(L, sep), ts;
      if (ix.date >= 0 && ix.time >= 0 && ix.date !== ix.time) { var tv = clean(f[ix.time]); ts = isClock(tv) ? clean(f[ix.date]) + ' ' + clockOf(tv) : tv; }
      else ts = clean(f[ix.time >= 0 ? ix.time : ix.date]);
      var md = /^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})/.exec(ts);
      if (md) { if (+md[1] > 12) dmy++; else if (+md[2] > 12) mdy++; }
      raw.push([i + 1, ts, f, L]);
    }
    var order = mdy > 0 && dmy === 0 ? 'mdy' : 'dmy';
    if (dmy === 0 && mdy === 0 && raw.some(function (r) { return /^\d{1,2}[-/.]\d{1,2}[-/.]\d{4}/.test(r[1]); })) res.warnings.push('Dates ambiguës (jour et mois tous deux ≤ 12) : lues jour/mois.');
    var kinds = {}, bars = [];
    raw.forEach(function (r) {
      var tt = parseTime(r[1], tz, order), f = r[2];
      var o_ = num(f[ix.open], dec), h_ = num(f[ix.high], dec), l_ = num(f[ix.low], dec), c_ = num(f[ix.close], dec), v_ = ix.vol >= 0 ? num(f[ix.vol], dec) : 0;
      if (!tt || !isFinite(o_) || !isFinite(h_) || !isFinite(l_) || !isFinite(c_)) { res.skipped++; if (!res.firstSkip) res.firstSkip = { line: r[0], text: String(r[3]).slice(0, 60) }; return; }
      var hh = Math.max(h_, o_, c_, l_), ll = Math.min(l_, o_, c_, h_); if (hh !== h_ || ll !== l_) res.fixed++;
      kinds[tt.k] = (kinds[tt.k] || 0) + 1;
      bars.push({ t: tt.t, o: o_, h: hh, l: ll, c: c_, v: isFinite(v_) && v_ > 0 ? v_ : 0 });
    });
    bars.sort(function (x, y) { return x.t - y.t; });
    var out = [];
    for (i = 0; i < bars.length; i++) { if (out.length && out[out.length - 1].t === bars[i].t) { out[out.length - 1] = bars[i]; res.dup++; } else out.push(bars[i]); }
    res.bars = out; res.n = out.length;
    res.hasVolume = out.some(function (x) { return x.v > 0; });
    res.timeKind = Object.keys(kinds).sort(function (x, y) { return kinds[y] - kinds[x]; })[0] || '';
    if (out.length > 1) { var dd = []; for (i = 1; i < Math.min(out.length, 4000); i++) dd.push(out[i].t - out[i - 1].t); dd.sort(function (x, y) { return x - y; }); res.stepMin = dd[Math.floor(dd.length / 2)] / 60000; }
    if (!out.length && !res.error) res.error = 'Aucune barre lisible.';
    if (isFinite(res.stepMin) && res.stepMin !== 1) res.warnings.push('Pas médian de ' + res.stepMin + ' min entre deux barres : la stratégie suppose des barres d’une minute.');
    if (out.length && !res.hasVolume) res.warnings.push('Aucun volume lu : la VWAP est calculée à poids égaux.');
    if (out.length) { res.firstT = out[0].t; res.lastT = out[out.length - 1].t; }
    return res;
  }

  /* ---- VWAP de séance, ancrée à l’ouverture Globex (18 h, New York) ----
     Prix typique (h + l + c)/3 pondéré par le volume ; σ = écart-type pondéré du prix typique autour de la VWAP.
     Une séance va de 18:00 à 17:00 (New York) : sa clé est la date new-yorkaise de l’instant décalé de six heures. */
  function sessionVwap(bars, o) {
    o = o || {};
    var n = bars.length, vw = new Array(n), sd = new Array(n), sess = new Array(n), parMin = new Array(n), nyMin = new Array(n), sessions = [];
    var any = false, i; for (i = 0; i < n; i++) if (bars[i].v > 0) { any = true; break; }
    var sw = 0, sp = 0, sp2 = 0, p0 = 0, cur = null, wtz = o.winTz || PAR;
    for (i = 0; i < n; i++) {
      var b = bars[i], ny = b.t + off(NY, b.t), dn = new Date(ny), sk = new Date(ny + 6 * 3600000);
      var key = sk.getUTCFullYear() + '-' + pad(sk.getUTCMonth() + 1) + '-' + pad(sk.getUTCDate());
      if (key !== cur) { cur = key; sessions.push({ key: key, i0: i, i1: i }); sw = 0; sp = 0; sp2 = 0; p0 = (b.h + b.l + b.c) / 3; }
      sessions[sessions.length - 1].i1 = i;
      var w = any ? (b.v > 0 ? b.v : 0) : 1, tp = (b.h + b.l + b.c) / 3 - p0;
      sw += w; sp += w * tp; sp2 += w * tp * tp;
      if (sw > 0) { var m1 = sp / sw, va = sp2 / sw - m1 * m1; vw[i] = p0 + m1; sd[i] = va > 1e-12 ? Math.sqrt(va) : 0; } else { vw[i] = NaN; sd[i] = NaN; }
      sess[i] = sessions.length - 1; nyMin[i] = dn.getUTCHours() * 60 + dn.getUTCMinutes();
      var dp = new Date(b.t + off(wtz, b.t)); parMin[i] = dp.getUTCHours() * 60 + dp.getUTCMinutes();
    }
    return { vwap: vw, sd: sd, sess: sess, parMin: parMin, nyMin: nyMin, sessions: sessions, uniform: !any };
  }

  /* ---- Le backtest ----
     p : k (écarts-types), stop (points au-delà de la bande), mode ('rejet' | 'contact'), from, to (heures de Paris),
     warm (minutes de séance avant le premier signal), maxPer (trades par séance, 0 = illimité),
     comm ($ aller-retour), slip (ticks aller-retour), tick, pv ($ par point). Un contrat. */
  function context(bars, pre, p) {
    var n = bars.length, fm = Math.round(p.from * 60), tm = Math.round(p.to * 60), inw = new Array(n), last = new Array(n), i;
    for (i = 0; i < n; i++) { var m = pre.parMin[i]; inw[i] = fm === tm ? true : fm < tm ? (m >= fm && m < tm) : (m >= fm || m < tm); }
    for (i = 0; i < n; i++) last[i] = i === n - 1 || pre.sess[i + 1] !== pre.sess[i] || !inw[i + 1];
    var cost = (p.comm || 0) + (p.slip || 0) * (p.tick || 0.25) * (p.pv || 2);
    /* Gestion d’une position ouverte à la barre i : stop d’abord si les deux sont touchés dans la même barre
       (pire cas), remplissage à l’ouverture si elle a déjà franchi le niveau ; tgt = null pour la VWAP mobile
       (celle de la barre précédente, connue avant la barre). */
    function manage(i0, side, entry, stopPx, tgt) {
      for (var j = i0 + 1; j < n; j++) {
        var b = bars[j], tg = tgt == null ? pre.vwap[j - 1] : tgt;
        if (side < 0) { if (b.h >= stopPx) return { j: j, x: Math.max(b.o, stopPx), fin: 'stop' }; if (b.l <= tg) return { j: j, x: Math.min(b.o, tg), fin: 'objectif' }; }
        else { if (b.l <= stopPx) return { j: j, x: Math.min(b.o, stopPx), fin: 'stop' }; if (b.h >= tg) return { j: j, x: Math.max(b.o, tg), fin: 'objectif' }; }
        if (last[j]) return { j: j, x: b.c, fin: 'cloche' };
      }
      return { j: n - 1, x: bars[n - 1].c, fin: 'cloche' };
    }
    function eligible(i) {
      if (!inw[i] || last[i]) return false;
      var s0 = pre.sessions[pre.sess[i]].i0;
      return (bars[i].t - bars[s0].t) / 60000 >= (p.warm || 0);
    }
    function signal(i) {
      if (!eligible(i)) return null;
      var b = bars[i];
      if (p.mode === 'contact') {
        var s0 = pre.sessions[pre.sess[i]].i0;
        if (i - 1 < s0 || !(pre.sd[i - 1] > 0)) return null;
        var v = pre.vwap[i - 1], Up = v + p.k * pre.sd[i - 1], Lo = v - p.k * pre.sd[i - 1], up = b.h >= Up, dn = b.l <= Lo;
        if (up && dn) return null;
        if (up) { var st = Up + p.stop; if (b.o >= st) return null; return { side: -1, entry: Math.max(b.o, Up), stop: st, ref: v, same: b.h >= st }; }
        if (dn) { var st2 = Lo - p.stop; if (b.o <= st2) return null; return { side: 1, entry: Math.min(b.o, Lo), stop: st2, ref: v, same: b.l <= st2 }; }
        return null;
      }
      if (!(pre.sd[i] > 0)) return null;
      var vw = pre.vwap[i], U = vw + p.k * pre.sd[i], L = vw - p.k * pre.sd[i];
      if (b.h >= U && b.c < U && b.c > vw) return { side: -1, entry: b.c, stop: U + p.stop, ref: vw };
      if (b.l <= L && b.c > L && b.c < vw) return { side: 1, entry: b.c, stop: L - p.stop, ref: vw };
      return null;
    }
    function record(i, side, entry, stopPx, ex, ref) {
      var pts = side * (ex.x - entry), risk = Math.abs(entry - stopPx), pnl = pts * (p.pv || 2) - cost;
      return { i: i, j: ex.j, t: bars[i].t, tx: bars[ex.j].t, side: side, entry: entry, stop: stopPx, exit: ex.x, fin: ex.fin, pts: pts, pnl: pnl, r: risk > 0 ? pnl / (risk * (p.pv || 2)) : NaN, risk: risk, ref: ref, sess: pre.sess[i], hour: Math.floor(pre.parMin[i] / 60) };
    }
    return { n: n, inw: inw, last: last, cost: cost, manage: manage, eligible: eligible, signal: signal, record: record };
  }
  function runBt(bars, pre, p) {
    var cx = context(bars, pre, p), trades = [], cnt = {}, i = 0;
    while (i < cx.n) {
      var sg = cx.signal(i);
      if (!sg || (p.maxPer > 0 && (cnt[pre.sess[i]] || 0) >= p.maxPer)) { i++; continue; }
      var ex = sg.same ? { j: i, x: sg.stop, fin: 'stop' } : cx.manage(i, sg.side, sg.entry, sg.stop, null);
      trades.push(cx.record(i, sg.side, sg.entry, sg.stop, ex, sg.ref));
      cnt[pre.sess[i]] = (cnt[pre.sess[i]] || 0) + 1;
      i = ex.j + 1;
    }
    return { trades: trades, cx: cx };
  }
  function stats(tr) {
    var n = tr.length, w = 0, l = 0, sp = 0, sn = 0, sum = 0, sumR = 0, nR = 0, eq = 0, pk = 0, dd = 0, run = 0, ls = 0, i;
    for (i = 0; i < n; i++) {
      var x = tr[i].pnl; sum += x;
      if (x > 0) { w++; sp += x; run = 0; } else if (x < 0) { l++; sn -= x; run++; if (run > ls) ls = run; } else run = 0;
      if (isFinite(tr[i].r)) { sumR += tr[i].r; nR++; }
      eq += x; if (eq > pk) pk = eq; if (pk - eq > dd) dd = pk - eq;
    }
    var m = n ? sum / n : NaN, v = 0; for (i = 0; i < n; i++) v += (tr[i].pnl - m) * (tr[i].pnl - m);
    var sd = n > 1 ? Math.sqrt(v / (n - 1)) : NaN;
    return { n: n, wins: w, losses: l, winRate: n ? w / n : NaN, exp: m, expR: nR ? sumR / nR : NaN, pf: sn > 0 ? sp / sn : (sp > 0 ? Infinity : NaN), maxDD: dd, sd: sd, sharpe: sd > 0 ? m / sd : NaN, net: sum, avgWin: w ? sp / w : NaN, avgLoss: l ? -sn / l : NaN, lossStreak: ls };
  }
  function moments(x) {
    var n = x.length; if (n < 2) return { n: n, mean: n ? x[0] : NaN, sd: NaN, sharpe: NaN, skew: 0, exkurt: 0 };
    var m = mean(x), m2 = 0, m3 = 0, m4 = 0;
    for (var i = 0; i < n; i++) { var d = x[i] - m; m2 += d * d; m3 += d * d * d; m4 += d * d * d * d; }
    m2 /= n; m3 /= n; m4 /= n;
    var sd = Math.sqrt(m2 * n / (n - 1));
    return { n: n, mean: m, sd: sd, sharpe: sd > 0 ? m / sd : NaN, skew: m2 > 0 ? m3 / Math.pow(m2, 1.5) : 0, exkurt: m2 > 0 ? m4 / (m2 * m2) - 3 : 0 };
  }
  function hours(tr) {
    var out = []; for (var hh = 0; hh < 24; hh++) out.push({ h: hh, n: 0, sum: 0, wins: 0 });
    tr.forEach(function (t) { var o = out[t.hour]; o.n++; o.sum += t.pnl; if (t.pnl > 0) o.wins++; });
    return out.filter(function (o) { return o.n > 0; });
  }
  /* ---- Les deux lois nulles ----
     1. Mêmes minutes d’entrée, sens tiré au hasard : stop et objectif fixes aux distances que le trade avait
        à l’entrée (stop = son risque, objectif = sa distance à la VWAP), dans le sens tiré.
     2. Minutes tirées au hasard dans la fenêtre de la même séance : le sens suit la règle (vers la VWAP),
        le stop garde la distance du trade apparié, l’objectif reste la VWAP mobile. Seul l’instant change.
     Chaque tirage rejoue tous les trades ; on garde l’espérance par trade de chaque tirage. */
  function nulls(bars, pre, p, trades, cx, draws, seed) {
    var r = rng(seed), elig = {}, D = draws, m1 = [], m2 = [], first1 = [], first2 = [];
    function pool(s) {
      if (elig[s]) return elig[s];
      var se = pre.sessions[s], out = [];
      for (var i = se.i0; i <= se.i1; i++) if (cx.eligible(i) && pre.sd[i] > 0) out.push(i);
      elig[s] = out; return out;
    }
    for (var d = 0; d < D; d++) {
      var s1 = 0, s2 = 0;
      for (var k = 0; k < trades.length; k++) {
        var t = trades[k], side = r() < 0.5 ? 1 : -1, g = Math.max(Math.abs(t.entry - t.ref), p.tick || 0.25);
        var e1 = cx.manage(t.i, side, t.entry, t.entry - side * t.risk, t.entry + side * g);
        var x1 = cx.record(t.i, side, t.entry, t.entry - side * t.risk, e1, t.ref).pnl; s1 += x1;
        var pl = pool(t.sess), u = pl.length ? pl[Math.floor(r() * pl.length)] : t.i, c = bars[u].c, v = pre.vwap[u];
        var sd2 = c > v ? -1 : c < v ? 1 : (r() < 0.5 ? 1 : -1);
        var e2 = cx.manage(u, sd2, c, c - sd2 * t.risk, null);
        var x2 = cx.record(u, sd2, c, c - sd2 * t.risk, e2, v).pnl; s2 += x2;
        if (d === 0) { first1.push(x1); first2.push(x2); }
      }
      m1.push(trades.length ? s1 / trades.length : NaN); m2.push(trades.length ? s2 / trades.length : NaN);
    }
    var ref = trades.length ? mean(trades.map(function (t) { return t.pnl; })) : NaN;
    function sum(ms, fr) { var so = sortedCopy(ms), ge = 0; ms.forEach(function (x) { if (x >= ref) ge++; }); return { means: ms, mean: mean(ms), lo: q(so, 0.05), hi: q(so, 0.95), p: (ge + 1) / (ms.length + 1), first: fr }; }
    return { draws: D, seed: seed, rand1: sum(m1, first1), rand2: sum(m2, first2), cost: cx.cost };
  }
  function runAll(a) {
    var pre = sessionVwap(a.bars, a.p), bt = runBt(a.bars, pre, a.p), tr = bt.trades;
    var fins = { objectif: 0, stop: 0, cloche: 0 }, fw = { objectif: [0, 0], stop: [0, 0], cloche: [0, 0] };
    tr.forEach(function (t) { fins[t.fin]++; fw[t.fin][t.pnl > 0 ? 0 : 1]++; });
    var out = { trades: tr, stats: stats(tr), hours: hours(tr), fins: fins, finsWin: fw, sessions: pre.sessions.length, uniform: pre.uniform, cost: bt.cx.cost, bars: a.bars.length };
    if (a.draws > 0 && tr.length) out.nulls = nulls(a.bars, pre, a.p, tr, bt.cx, a.draws, a.seed >>> 0);
    return out;
  }

  /* ---- Données synthétiques : marche aléatoire sans dérive, une minute = douze sous-pas ---- */
  function synth(o) {
    var r = rng(o.seed >>> 0), bars = [], px = o.base || 10000, sub = 12, sds = (o.sigma || 4) / Math.sqrt(sub), tick = o.tick || 0.25;
    function R(x) { return Math.round(x / tick) * tick; }
    var d = Date.UTC(2026, 0, 4), made = 0, days = Math.max(1, Math.min(120, Math.round(o.days || 20)));
    while (made < days) {
      var dt = new Date(d), wd = dt.getUTCDay();
      if (wd <= 4) {
        var t0 = wall(dt.getUTCFullYear(), dt.getUTCMonth() + 1, dt.getUTCDate(), 18, 0, 0, NY);
        for (var k = 0; k < 1380; k++) {
          var op = px, hi = px, lo = px;
          for (var s = 0; s < sub; s++) { px += sds * gauss(r); if (px > hi) hi = px; if (px < lo) lo = px; }
          bars.push({ t: t0 + k * 60000, o: R(op), h: R(hi), l: R(lo), c: R(px), v: 20 + Math.floor(r() * 100) });
        }
        made++;
      }
      d += 86400000;
    }
    return bars;
  }

  /* ---- CSCV : portage de alp1/overfit.py, ligne à ligne ---- */
  function roundHalfEven(x) { var f = Math.floor(x); return x - f === 0.5 ? (f % 2 === 0 ? f : f + 1) : Math.round(x); }
  function cscv(perf, nb) {
    nb = nb || 8; var N = perf.length;
    if (N < 2) return { error: 'il faut au moins deux configurations' };
    var Tn = perf[0].length;
    if (perf.some(function (row) { return row.length !== Tn; })) return { error: 'toutes les configurations doivent couvrir les mêmes périodes' };
    if (nb < 2 || nb % 2) return { error: 'le nombre de blocs doit être pair' };
    if (Tn < nb) return { error: 'pas assez de périodes pour ce découpage' };
    var edges = [], blocks = [], i;
    for (i = 0; i <= nb; i++) edges.push(roundHalfEven(i * Tn / nb));
    for (i = 0; i < nb; i++) { var bl = []; for (var t = edges[i]; t < edges[i + 1]; t++) bl.push(t); blocks.push(bl); }
    var combos = [], half = nb / 2;
    (function rec(start, acc) { if (acc.length === half) { combos.push(acc.slice()); return; } for (var j = start; j < nb; j++) { acc.push(j); rec(j + 1, acc); acc.pop(); } })(0, []);
    var logits = [], degr = [], omegas = [];
    combos.forEach(function (tc) {
      var inTr = {}; tc.forEach(function (b) { inTr[b] = true; });
      var trI = [], teI = []; tc.forEach(function (b) { blocks[b].forEach(function (x) { trI.push(x); }); });
      for (var b = 0; b < nb; b++) if (!inTr[b]) blocks[b].forEach(function (x) { teI.push(x); });
      var tr = perf.map(function (row) { var s = 0; for (var k = 0; k < trI.length; k++) s += row[trI[k]]; return s / trI.length; });
      var te = perf.map(function (row) { var s = 0; for (var k = 0; k < teI.length; k++) s += row[teI[k]]; return s / teI.length; });
      var best = 0; for (var s = 1; s < N; s++) if (tr[s] > tr[best]) best = s;
      var order = []; for (s = 0; s < N; s++) order.push(s); order.sort(function (x, y) { return te[x] - te[y]; });
      var rank = order.indexOf(best) + 1, om = Math.min(Math.max(rank / (N + 1), 1e-9), 1 - 1e-9);
      logits.push(Math.log(om / (1 - om))); degr.push(tr[best] - te[best]); omegas.push(rank / (N + 1));
    });
    var sl = logits.slice().sort(function (x, y) { return x - y; }), L = sl.length;
    return { pbo: logits.filter(function (x) { return x <= 0; }).length / L, splits: L, medianLogit: L % 2 ? sl[(L - 1) / 2] : 0.5 * (sl[L / 2 - 1] + sl[L / 2]), degradation: mean(degr), logits: logits, omegas: omegas, edges: edges };
  }
  function sweep(bars, p, ks, stops) {
    var pre = sessionVwap(bars, p), ns = pre.sessions.length, grid = [], perf = [];
    ks.forEach(function (k) {
      stops.forEach(function (st) {
        var pp = {}; for (var key in p) pp[key] = p[key]; pp.k = k; pp.stop = st;
        var tr = runBt(bars, pre, pp).trades, v = new Array(ns); for (var i = 0; i < ns; i++) v[i] = 0;
        tr.forEach(function (t) { v[t.sess] += t.pnl; });
        perf.push(v);
        var m = moments(tr.map(function (t) { return t.pnl; }));
        grid.push({ k: k, stop: st, n: tr.length, exp: m.mean, sd: m.sd, sharpe: m.sharpe, skew: m.skew, exkurt: m.exkurt, net: tr.reduce(function (s, t) { return s + t.pnl; }, 0), win: tr.length ? tr.filter(function (t) { return t.pnl > 0; }).length / tr.length : NaN });
      });
    });
    return { grid: grid, sessions: ns, cscv: ns >= 8 ? cscv(perf, 8) : { error: 'il faut au moins huit séances' } };
  }

  /* ---- Monte-Carlo au niveau des trades ----
     o : mode 'param' (p, rr, disp, risk, cost) ou 'boot' (sample en $) ; n trades, P trajectoires, capital, ruin ($ de perte
     qui crame le compte, absorbant), seed. La loi nulle garde la forme et retire l’avantage : taux d’équilibre
     (1 + c/L)/(1 + R:R) en paramétrique, échantillon recentré (x − x̄) en bootstrap. Mêmes tirages uniformes. */
  function monteCarlo(o) {
    var n = Math.max(1, Math.round(o.n)), P = Math.max(1, Math.round(o.paths || 10000)), cap = o.capital, lvl = cap - o.ruin, K = Math.min(n, 60), cps = [], c;
    for (c = 0; c <= K; c++) cps.push(Math.round(c * n / K));
    var risk = o.risk, cost = o.cost || 0, rr = o.rr, sdisp = o.disp || 0;
    var pEq = Math.min(1, (1 + cost / risk) / (1 + rr));
    function param(p) { return function (r) { var R; if (r() < p) R = sdisp > 0 ? rr * Math.exp(sdisp * gauss(r) - sdisp * sdisp / 2) : rr; else R = -1; return R * risk - cost; }; }
    var smp = o.sample || [], mu = smp.length ? mean(smp) : 0;
    function boot(shift) { var m = smp.length; return function (r) { return smp[Math.floor(r() * m)] - shift; }; }
    function sim(draw) {
      var r = rng(o.seed >>> 0), finals = new Array(P), dds = new Array(P), str = new Array(P), grid = [], paths = [], ruined = 0, NP = Math.min(14, P), k, t;
      for (c = 0; c <= K; c++) grid.push(new Float64Array(P));
      for (k = 0; k < P; k++) {
        var eq = cap, pk = cap, dd = 0, run = 0, best = 0, dead = false, ci = 1, path = k < NP ? [cap] : null;
        grid[0][k] = cap;
        for (t = 1; t <= n; t++) {
          if (!dead) { var x = draw(r); eq += x; if (eq > pk) pk = eq; if (pk - eq > dd) dd = pk - eq; if (x < 0) { run++; if (run > best) best = run; } else run = 0; if (o.ruin > 0 && eq <= lvl) { dead = true; ruined++; } }
          if (t === cps[ci]) { grid[ci][k] = eq; if (path) path.push(eq); ci++; }
        }
        finals[k] = eq; dds[k] = dd; str[k] = best; if (path) paths.push(path);
      }
      var qq = { p05: [], p25: [], p50: [], p75: [], p95: [] };
      grid.forEach(function (g) { g.sort(); qq.p05.push(q(g, 0.05)); qq.p25.push(q(g, 0.25)); qq.p50.push(q(g, 0.5)); qq.p75.push(q(g, 0.75)); qq.p95.push(q(g, 0.95)); });
      var fs = sortedCopy(finals), ds = sortedCopy(dds), ss = sortedCopy(str), loss = 0; for (k = 0; k < P; k++) if (finals[k] < cap) loss++;
      return { q: qq, paths: paths, finals: finals, dds: dds, ruin: ruined / P, pLoss: loss / P, meanFinal: mean(finals), final05: q(fs, 0.05), final50: q(fs, 0.5), final95: q(fs, 0.95), dd50: q(ds, 0.5), dd95: q(ds, 0.95), streak50: q(ss, 0.5), streak95: q(ss, 0.95) };
    }
    var alt, nul;
    if (o.mode === 'boot') { alt = sim(boot(0)); nul = sim(boot(mu)); }
    else { alt = sim(param(o.p)); nul = sim(param(pEq)); }
    return { alt: alt, nul: nul, cps: cps, pEq: pEq, mu: mu, n: n, paths: P };
  }

  switch (a.op) {
    case 'parse': return parseCsv(a.text, a.o || {});
    case 'vwap': return sessionVwap(a.bars, a.o || {});
    case 'bt': return runAll(a);
    case 'stats': return stats(a.trades);
    case 'moments': return moments(a.x);
    case 'synth': return { bars: synth(a.o || {}) };
    case 'cscv': return cscv(a.perf, a.nb);
    case 'sweep': return sweep(a.bars, a.p, a.ks, a.stops);
    case 'mc': return monteCarlo(a.o);
    case 'wall': return { t: wall(a.y, a.mo, a.d, a.hh, a.mi, a.ss || 0, a.tz) };
  }
  throw new Error('opération inconnue : ' + a.op);
}

/* =====================================================================
   2. Fonctions pures exportées (tests) — aucun DOM, aucun T.store
   ===================================================================== */
Q.engine = quantEngine;
Q.parseCsv = function (text, o) { return quantEngine({ op: 'parse', text: text, o: o || {} }); };
Q.sessionVwap = function (bars, o) { return quantEngine({ op: 'vwap', bars: bars, o: o || {} }); };
Q.backtest = function (bars, p, draws, seed) { return quantEngine({ op: 'bt', bars: bars, p: p, draws: draws || 0, seed: seed || 1 }); };
Q.stats = function (trades) { return quantEngine({ op: 'stats', trades: trades }); };
Q.moments = function (x) { return quantEngine({ op: 'moments', x: x }); };
Q.synth = function (o) { return quantEngine({ op: 'synth', o: o }).bars; };
Q.cscv = function (perf, nb) { return quantEngine({ op: 'cscv', perf: perf, nb: nb }); };
Q.sweep = function (bars, p, ks, stops) { return quantEngine({ op: 'sweep', bars: bars, p: p, ks: ks, stops: stops }); };
Q.monteCarlo = function (o) { return quantEngine({ op: 'mc', o: o }); };
Q.wallToUtc = function (y, mo, d, hh, mi, tz) { return quantEngine({ op: 'wall', y: y, mo: mo, d: d, hh: hh, mi: mi, tz: tz }).t; };

/* Mur d’échantillon (ALP nº 3, huitième partie). Route 1 : test t unilatéral, N = ⌈((z₁₋α + z_puissance)/SR)²⌉
   (alp1/costs.py, trades_for_significance). Route 2 : taxe de sélection, N = 2 ln B / SR² (report10._trades_for_threshold),
   nulle à une seule configuration. La plus exigeante lie. */
Q.zSum = function (alpha, power) { return S.normPpf(1 - alpha) + S.normPpf(power); };
Q.route1 = function (sr, alpha, power) { if (!(sr > 0)) return Infinity; return Math.ceil(Math.pow(Q.zSum(alpha, power) / sr, 2) - 1e-9); };
Q.route2 = function (sr, B) { if (!(sr > 0)) return Infinity; return 2 * Math.log(Math.max(B, 1)) / (sr * sr); };
Q.wall = function (sr, B, alpha, power) { var a = Q.route1(sr, alpha, power), b = Q.route2(sr, B); return { r1: a, r2: b, n: Math.max(a, Math.ceil(b - 1e-9)), taxe: b > a }; };
Q.configsCrossing = function (alpha, power) { return Math.exp(Math.pow(Q.zSum(alpha, power), 2) / 2); };
Q.threshold = function (N, K) { return N > 0 ? K / Math.sqrt(N) : Infinity; };
Q.SESSIONS = 252;
Q.MUR = { sharpe: 0.10, configs: 16, r1: 619, r2: 555, source: 'ALP nº 3, huitième partie, table 14' };
Q.wilson = function (k, n, z) {
  if (!n) return { p: NaN, lo: NaN, hi: NaN };
  z = z == null ? S.normPpf(0.975) : z;
  var p = k / n, z2 = z * z, den = 1 + z2 / n, c = (p + z2 / (2 * n)) / den, hw = z * Math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / den;
  return { p: p, lo: c - hw, hi: c + hw };
};
/* Taux d’équilibre : le taux de réussite qui annule l’espérance à gain et perte moyens donnés. */
Q.breakEven = function (avgWin, avgLoss) { var L = Math.abs(avgLoss); return avgWin > 0 && L > 0 ? L / (avgWin + L) : NaN; };
/* Taux d’équilibre d’une géométrie fixe, frais compris : (1 + c/L)/(1 + R:R). */
Q.equilibrium = function (rr, costR) { return (1 + (costR || 0)) / (1 + rr); };
Q.expectancyR = function (p, rr, costR) { return p * rr - (1 - p) - (costR || 0); };
/* Sharpe probabiliste, seuil de sélection, Sharpe déflaté (Bailey et López de Prado ; alp1/pathstats.py, alp1/overfit.py). */
var EULER = 0.5772156649015329;
Q.psr = function (sr, n, sr0, skew, exkurt) {
  if (!(n >= 2) || !fin(sr)) return 0;
  var v = 1 - (skew || 0) * sr + 0.25 * ((exkurt || 0) + 2) * sr * sr;
  if (v <= 0) return sr > (sr0 || 0) ? 1 : 0;
  return S.normCdf((sr - (sr0 || 0)) * Math.sqrt(n - 1) / Math.sqrt(v));
};
Q.expectedMaxSharpe = function (N, sdTrials) { if (!(N >= 2)) return 0; return sdTrials * ((1 - EULER) * S.normPpf(1 - 1 / N) + EULER * S.normPpf(1 - 1 / (N * Math.E))); };
Q.dsr = function (sr, n, N, skew, exkurt, sdTrials) { var sd = fin(sdTrials) ? sdTrials : 1 / Math.sqrt(Math.max(n, 1)), sr0 = Q.expectedMaxSharpe(N, sd); return { sr0: sr0, dsr: Q.psr(sr, n, sr0, skew, exkurt) }; };
/* Les trades pris et clos du journal, en dollars et en R. */
Q.fromJournal = function (rows, risk) {
  return (rows || []).filter(function (r) { return r && r.kind === 'pris' && r.status === 'clos' && (fin(r.pnl) || fin(r.r)); })
    .map(function (r) { var pnl = fin(r.pnl) ? r.pnl : r.r * risk; return { at: fin(r.closedAt) ? r.closedAt : r.at, pnl: pnl, r: fin(r.r) ? r.r : pnl / risk }; })
    .sort(function (a, b) { return (a.at || 0) - (b.at || 0); });
};
/* Grille de stops du balayage, autour du stop choisi, arrondie au tick. */
Q.stopGrid = function (s, tick) { tick = tick || 0.25; return [0.5, 1, 1.5, 2].map(function (m) { return Math.max(tick, Math.round(s * m / tick) * tick); }); };
Q.K_GRID = [1.5, 2, 2.5, 3];

/* =====================================================================
   3. Rendu
   ===================================================================== */
var SVGNS = 'http://www.w3.org/2000/svg';
var CSS = '.qt-hub{position:relative}.qt-hub>svg{position:absolute;left:0;top:0;pointer-events:none;overflow:visible}' +
  '.qt-core{max-width:320px;width:100%;margin:0 auto;text-align:center}.qt-core>.cb{align-items:center;gap:4px;padding:14px}' +
  '.qt-kick{font:600 10px/1.2 var(--f-mono);letter-spacing:.16em;text-transform:uppercase;color:var(--violet-2)}' +
  '.qt-big{font:600 30px/1.05 var(--f-mono);color:var(--hi);letter-spacing:-.02em;white-space:nowrap}.qt-big small{font-size:13px;color:var(--soft);font-weight:500;margin-left:4px;letter-spacing:0}' +
  '.qt-sub{font:500 11px/1.45 var(--f-mono);color:var(--mute)}' +
  '.qt-stack{display:flex;flex-direction:column;gap:22px;min-width:0}' +
  '.qt-wait{display:flex;align-items:center;gap:10px;padding:18px 14px;border:1px dashed var(--line-2);border-radius:var(--r);font:500 12px/1.4 var(--f-mono);color:var(--mute);background:var(--panel)}' +
  '.qt-wait i{width:8px;height:8px;border-radius:50%;background:var(--violet);flex:none;animation:qtp 1s ease-in-out infinite}@keyframes qtp{50%{opacity:.25}}' +
  '.qt-line{display:flex;flex-wrap:wrap;gap:4px 12px;align-items:baseline;font:500 11.5px/1.5 var(--f-mono);color:var(--mute)}.qt-line b{color:var(--fg);font-weight:600}' +
  '.qt-vs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}@media (max-width:560px){.qt-vs{grid-template-columns:minmax(0,1fr)}}' +
  '.qt-vs>div{border:1px solid var(--line);border-radius:10px;padding:10px 11px;background:var(--panel);display:flex;flex-direction:column;gap:4px;min-width:0}' +
  '.qt-vs>div.on{border-color:var(--violet-b);background:linear-gradient(180deg,var(--violet-a),transparent 80%),var(--panel)}' +
  '.qt-vs .l{font:600 10px/1.3 var(--f-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--mute)}.qt-vs .v{font:600 19px/1.1 var(--f-mono);color:var(--hi);white-space:nowrap}.qt-vs .h{font:500 11px/1.4 var(--f-mono);color:var(--mute)}' +
  '.qt-prog{display:flex;flex-direction:column;gap:8px}.qt-bar{position:relative;height:10px;border-radius:5px;background:var(--raise-2);overflow:hidden;border:1px solid var(--line)}.qt-bar i{position:absolute;left:0;top:0;bottom:0;background:var(--violet)}' +
  '.qt-ticks{display:flex;justify-content:space-between;font:500 10.5px/1 var(--f-mono);color:var(--mute)}' +
  '.qt-file{position:relative}.qt-file input{display:none}' +
  'details.qt-det{border-top:1px solid var(--line);padding-top:10px}details.qt-det>summary{cursor:pointer;list-style:none;font:600 10.5px/1.3 var(--f-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--soft)}details.qt-det>summary::-webkit-details-marker{display:none}details.qt-det>summary::after{content:" +";color:var(--violet-2)}details.qt-det[open]>summary::after{content:" −"}details.qt-det[open]>summary{margin-bottom:12px}' +
  '.qt-src{display:flex;flex-direction:column;gap:10px}.qt-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}' +
  '.qt-verdict{display:flex;flex-direction:column;align-items:flex-start;gap:6px;font-size:13px;color:var(--soft);line-height:1.5}.qt-verdict+.qt-verdict{border-top:1px solid var(--line);padding-top:12px}';
function injectCss() { if (document.getElementById('quant-css')) return; var s = document.createElement('style'); s.id = 'quant-css'; s.textContent = CSS; document.head.appendChild(s); }
function typo(el) {
  if (!el || typeof document === 'undefined') return;
  var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, { acceptNode: function (n) { var p = n.parentNode; return p && /^(TEXTAREA|SCRIPT|STYLE|INPUT|OPTION)$/.test(p.nodeName) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; } }), n;
  while ((n = w.nextNode())) { var t = n.nodeValue, u = T.typo(t).replace(/nº /g, 'nº '); if (u !== t) n.nodeValue = u; }
}
function lru(max) { var m = new Map(); return { get: function (k) { return m.get(k); }, put: function (k, v) { m.delete(k); m.set(k, v); while (m.size > max) m.delete(m.keys().next().value); }, drop: function (k) { m.delete(k); } }; }
var CACHE = { mc: lru(4), bt: lru(4), sw: lru(3) };
var DATA = { key: null, kind: null, bars: null, name: '', info: null, text: null, pending: null, pkey: null, err: null };

function wait(text) { return h('div', { class: 'qt-wait', role: 'status' }, h('i'), text); }
/* Calcul en tâche de fond, mis en cache par clé ; peint dans slot si la vue est toujours là. */
function runInto(cache, key, arg, slot, paint, waitText) {
  var hit = cache.get(key);
  if (hit && hit.res) { paint(hit.res); return; }
  slot.appendChild(wait(waitText || 'Calcul en cours…'));
  if (!hit) {
    hit = { p: T.compute(quantEngine, arg) }; cache.put(key, hit);
    hit.p.then(function (r) { hit.res = r; }, function () { cache.drop(key); });
  }
  hit.p.then(function (r) { if (!slot.isConnected) return; T.clear(slot); paint(r); typo(slot); },
    function (e) { if (!slot.isConnected) return; T.clear(slot); slot.appendChild(U.empty({ title: 'Le calcul a échoué', text: String(e && e.message || e) })); });
}
/* Hub : un nœud central relié par des courbes aux tuiles du premier rang (même dessin que l’accueil). */
function hub(center, tiles, cols) {
  var wrap = h('div', { class: 'qt-hub' }), svg = document.createElementNS(SVGNS, 'svg'), grid = U.kpis(tiles, cols || 3);
  grid.style.marginTop = '30px';
  wrap.appendChild(svg); wrap.appendChild(center); wrap.appendChild(grid);
  T.observe(wrap, function () {
    if (!wrap.isConnected) return; var wr = wrap.getBoundingClientRect(), cr = center.getBoundingClientRect(), out = '';
    svg.setAttribute('width', wr.width); svg.setAttribute('height', wr.height);
    var cx = cr.left + cr.width / 2 - wr.left, cy = cr.bottom - wr.top;
    Array.prototype.forEach.call(grid.children, function (el) { var r = el.getBoundingClientRect(); if (r.top - wr.top > cy + 60) return; var x = r.left + r.width / 2 - wr.left, y = r.top - wr.top; out += '<path d="M' + cx + ',' + cy + ' C' + cx + ',' + (cy + 20) + ' ' + x + ',' + (y - 20) + ' ' + x + ',' + y + '" fill="none" stroke="var(--line-2)" stroke-width="1.2"/>'; });
    out += '<circle cx="' + cx + '" cy="' + cy + '" r="3" fill="var(--violet)"/>';
    svg.innerHTML = out;
  });
  return wrap;
}
/* Histogramme local : bande d’étiquettes au-dessus du tracé (aucun texte sur les barres), classes alignées
   sur le réseau quand les valeurs sont discrètes (sinon une classe sur deux est vide), seconde loi en contour. */
Q.binning = function (vals, maxBins) {
  maxBins = maxBins || 36;
  var a = vals.filter(fin).sort(function (x, y) { return x - y; }), n = a.length;
  if (!n) return null;
  var lo = a[0], hi = a[n - 1];
  if (hi === lo) return { lo: lo - 0.5, hi: hi + 0.5, nb: 1, lattice: true };
  var u = [a[0]]; for (var i = 1; i < n && u.length <= 400; i++) if (a[i] - u[u.length - 1] > 1e-9 * Math.max(1, Math.abs(a[i]))) u.push(a[i]);
  if (u.length <= 400) {
    var d = Infinity; for (i = 1; i < u.length; i++) d = Math.min(d, u[i] - u[i - 1]);
    var lat = u.every(function (x) { var k = (x - lo) / d; return Math.abs(k - Math.round(k)) < 1e-6 * Math.max(1, k); });
    if (lat) { var L = Math.round((hi - lo) / d) + 1, g = Math.ceil(L / maxBins), nb = Math.ceil(L / g); return { lo: lo - d / 2, hi: lo - d / 2 + nb * g * d, nb: nb, lattice: true }; }
  }
  /* Valeurs presque discrètes (un réseau rompu par quelques trajectoires ruinées) : le plus grand nombre de classes
     qui ne laisse aucune classe vide entre le 5e et le 95e centile. */
  var q05 = a[Math.floor(0.05 * (n - 1))], q95 = a[Math.ceil(0.95 * (n - 1))];
  for (var nb2 = maxBins; nb2 >= 8; nb2--) {
    var w = (hi - lo) / nb2, c = new Array(nb2).fill(0);
    for (i = 0; i < n; i++) c[Math.min(nb2 - 1, Math.floor((a[i] - lo) / w))]++;
    var i0 = Math.min(nb2 - 1, Math.floor((q05 - lo) / w)), i1 = Math.min(nb2 - 1, Math.floor((q95 - lo) / w)), hole = false;
    for (var j = i0; j <= i1; j++) if (!c[j]) { hole = true; break; }
    if (!hole) return { lo: lo, hi: hi, nb: nb2, lattice: false };
  }
  return { lo: lo, hi: hi, nb: 8, lattice: false };
};
/* Graduations : le plus grand nombre dont les étiquettes ne se touchent pas (largeur estimée à 6,2 px par signe). */
Q.axisTicks = function (lo, hi, span, f) {
  for (var n = Math.max(2, Math.floor(span / 40)); n >= 2; n--) {
    var tk = T.ticks(lo, hi, n).filter(function (t) { return t >= lo && t <= hi; });
    if (tk.length < 2) return tk;
    var gap = (tk[1] - tk[0]) / (hi - lo) * span, wmax = 0; tk.forEach(function (t) { wmax = Math.max(wmax, String(f(t)).length * 6.2); });
    if (gap >= wmax + 12) return tk;
  }
  return T.ticks(lo, hi, 2).filter(function (t) { return t >= lo && t <= hi; });
};
function histo(o) {
  var v1 = (o.values || []).filter(fin), v2 = (o.values2 || []).filter(fin), TN = { violet: 'var(--violet)', mute: 'var(--soft)', fg: 'var(--hi)', dim: 'var(--line-2)' };
  return C.mount({ legend: o.legend }, function (W) {
    if (!v1.length) return { svg: '<svg viewBox="0 0 ' + W + ' 60" height="60"><text class="ax" x="' + (W / 2) + '" y="34" text-anchor="middle">Pas encore de données</text></svg>' };
    var B = Q.binning(v1.concat(v2), o.bins || 36), nb = B.nb, lo = B.lo, hi = B.hi, bw = (hi - lo) / nb, f = o.fmt || function (x) { return F.num(x, 1); };
    function count(v) { var c = new Array(nb).fill(0); v.forEach(function (x) { var i = Math.floor((x - lo) / bw); if (i >= nb) i = nb - 1; if (i < 0) i = 0; c[i]++; }); return c; }
    var c1 = count(v1), c2 = v2.length ? count(v2) : null, s1 = v1.length, s2 = v2.length || 1;
    var mx = 0; c1.forEach(function (c) { mx = Math.max(mx, c / s1); }); if (c2) c2.forEach(function (c) { mx = Math.max(mx, c / s2); });
    var m = { l: 12, r: 12, b: 24 }, sx = function (x) { return m.l + (x - lo) / (hi - lo) * (W - m.l - m.r); };
    /* étiquettes : rangées gloutonnes, aucune ne chevauche sa voisine */
    var refs = (o.refs || []).filter(function (r) { return fin(r.x) && r.x >= lo && r.x <= hi; }).map(function (r) { return Object.assign({}, r); }), rows = [];
    refs.sort(function (a, b) { return a.x - b.x; }).forEach(function (r) {
      var x = sx(r.x), w = String(r.label || '').length * 6.2 + 4, end = x > W * 0.62; r.px = x; r.end = end;
      var a = end ? x - w - 4 : x + 4, b = end ? x - 4 : x + w + 4, k = 0;
      while (rows[k] && rows[k].some(function (s) { return a < s[1] + 6 && b > s[0] - 6; })) k++;
      (rows[k] = rows[k] || []).push([a, b]); r.row = k;
    });
    var band = rows.length * 13 + (rows.length ? 6 : 0), top = band + 8, H = (o.height || 160) + band, base = H - m.b;
    var sy = function (p) { return top + (1 - p / mx) * (base - top); }, g = '';
    c1.forEach(function (c, i) { if (!c) return; var x1 = sx(lo + i * bw), x2 = sx(lo + (i + 1) * bw); g += '<rect x="' + (x1 + 0.5).toFixed(1) + '" y="' + sy(c / s1).toFixed(1) + '" width="' + Math.max(1, x2 - x1 - 1).toFixed(1) + '" height="' + (base - sy(c / s1)).toFixed(1) + '" fill="' + (TN[o.tone || 'violet']) + '" opacity="' + (o.tone === 'mute' ? '.42' : '.62') + '"/>'; });
    if (c2) { var d = 'M' + sx(lo).toFixed(1) + ',' + base; c2.forEach(function (c, i) { var y = sy(c / s2).toFixed(1); d += 'L' + sx(lo + i * bw).toFixed(1) + ',' + y + 'L' + sx(lo + (i + 1) * bw).toFixed(1) + ',' + y; }); d += 'L' + sx(hi).toFixed(1) + ',' + base; g += '<path d="' + d + '" fill="none" stroke="' + TN[o.tone2 || 'fg'] + '" stroke-width="1.3" stroke-linejoin="round" opacity=".9"/>'; }
    g += '<line class="zl" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + base + '" y2="' + base + '"/>';
    var lastB = -Infinity;
    Q.axisTicks(lo, hi, W - m.l - m.r, f).forEach(function (t) {
      var x = sx(t), w = String(f(t)).length * 6.2, an = x - w / 2 < 2 ? 'start' : x + w / 2 > W - 2 ? 'end' : 'middle', a0 = an === 'start' ? x : an === 'end' ? x - w : x - w / 2;
      if (a0 < lastB + 10) return; lastB = a0 + w;
      g += '<text class="ax" x="' + x.toFixed(1) + '" y="' + (H - 7) + '" text-anchor="' + an + '">' + T.esc(f(t)) + '</text>';
    });
    refs.forEach(function (r) {
      var col = TN[r.tone || 'violet'], y = 4 + r.row * 13 + 9;
      g += '<line x1="' + r.px.toFixed(1) + '" x2="' + r.px.toFixed(1) + '" y1="' + (y - 9) + '" y2="' + base + '" stroke="' + col + '" stroke-width="1.5"' + (r.dash ? ' stroke-dasharray="4 3"' : '') + '/>';
      g += '<text class="axl" x="' + (r.end ? r.px - 5 : r.px + 5).toFixed(1) + '" y="' + y + '" text-anchor="' + (r.end ? 'end' : 'start') + '" fill="' + col + '">' + T.esc(r.label || '') + '</text>';
    });
    g += '<line class="hl" x1="0" x2="0" y1="' + top + '" y2="' + base + '" stroke="var(--violet)" style="opacity:0"/>';
    var xs = []; for (var i = 0; i < nb; i++) xs.push(sx(lo + (i + 0.5) * bw));
    return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '">' + g + '</svg>', hover: { xs: xs, html: function (i) {
      var a = lo + i * bw, b = a + bw, sh = function (c, n) { return F.pct(c / n, 1); };
      return '<b>' + T.esc(f(a)) + ' à ' + T.esc(f(b)) + '</b><br>' + T.esc(o.name1 || 'série') + ' ' + sh(c1[i], s1) + (c2 ? '<br>' + T.esc(o.name2 || 'loi nulle') + ' ' + sh(c2[i], s2) : '');
    } } };
  });
}
function core(kick, big, unit, sub) { return h('div', { class: 'card accent qt-core' }, h('div', { class: 'cb' }, h('div', { class: 'qt-kick' }, kick), h('div', { class: 'qt-big' }, big, unit ? h('small', null, unit) : null), sub ? h('div', { class: 'qt-sub' }, sub) : null)); }
function kUsd(v) { if (!fin(v)) return '—'; return Math.abs(v) >= 10000 ? F.num(v / 1000, 1, 'k$') : F.usd(v, 0); }
function usd2(v, signed) { return F.usd(v, 2, signed); }
function pct(p, nd) { return fin(p) ? F.pct(p, nd == null ? 1 : nd) : '—'; }
function parisParts(t) { return T.time.parts('Europe/Paris', new Date(t)); }
function pad2(n) { return String(n).padStart(2, '0'); }
function hourLabel(x) { var hh = Math.floor(x), mm = Math.round((x - hh) * 60); if (mm === 60) { hh++; mm = 0; } return pad2(hh % 24) + ':' + pad2(mm); }

/* ---------------- Onglet Monte-Carlo ---------------- */
var DEF_MC = { src: 'param', p: 0.45, rr: 1.5, disp: 0, cost: null, n: 100, capital: 50000, risk: null, ruin: 2000, seed: 1, unit: 'r' };
function mcParams(set) { var o = Object.assign({}, DEF_MC, T.store.get(KEY.mc, {})); if (!fin(o.risk)) o.risk = set.riskPerTrade; if (!fin(o.cost)) o.cost = set.commissionRT; return o; }
function setMc(k, v, ctx) { var c = T.store.get(KEY.mc, {}); c[k] = v; T.store.set(KEY.mc, c); if (ctx) ctx.rerender(); }

function renderMC(root, ctx) {
  var set = ctx.settings, o = mcParams(set), rows = Q.fromJournal(T.journal.list(), set.riskPerTrade);
  var s0 = U.section('Les *hypothèses*', 'graine ' + o.seed + ' · 10 000 trajectoires'), body = [];
  body.push(U.seg({ aria: 'Source des résultats', options: [{ v: 'param', label: 'Paramétrique' }, { v: 'journal', label: 'Journal (' + rows.length + ')' }], value: o.src, onChange: function (v) { setMc('src', v, ctx); } }));
  if (o.src === 'param') {
    body.push(U.fields([
      { label: 'Taux de réussite', unit: '%', value: +(o.p * 100).toFixed(2), min: 0, max: 100, onChange: function (v) { setMc('p', v / 100, ctx); } },
      { label: 'Gain / risque (R:R)', unit: 'R', value: o.rr, min: 0.05, max: 50, onChange: function (v) { setMc('rr', v, ctx); } },
      { label: 'Variabilité du gain', unit: '%', value: +(o.disp * 100).toFixed(1), min: 0, max: 150, hint: '0 = gain fixe ; la moyenne reste R:R', onChange: function (v) { setMc('disp', v / 100, ctx); } },
      { label: 'Frais par trade', unit: '$', value: o.cost, min: 0, max: 500, hint: 'commission et glissement', onChange: function (v) { setMc('cost', v, ctx); } }
    ]));
  } else {
    body.push(h('div', { class: 'qt-row' }, h('span', { class: 'qt-line' }, h('b', null, F.int(rows.length) + ' trade' + (rows.length > 1 ? 's' : '') + ' clos'), ' rééchantillonnés avec remise'), U.seg({ aria: 'Unité du rééchantillonnage', options: [{ v: 'r', label: 'En R' }, { v: 'usd', label: 'En $' }], value: o.unit, onChange: function (v) { setMc('unit', v, ctx); } })));
    body.push(U.note(o.unit === 'r' ? 'Chaque résultat en R est remis à l’échelle du risque par trade ci-dessous : la carrière est rejouée à ta mise actuelle.' : 'Les résultats en dollars sont tirés tels quels, frais déjà déduits : le risque par trade ne sert pas.'));
  }
  body.push(U.fields([
    { label: 'Nombre de trades', value: o.n, min: 10, max: 2000, onChange: function (v) { setMc('n', Math.round(v), ctx); } },
    { label: 'Capital de départ', unit: '$', value: o.capital, min: 100, onChange: function (v) { setMc('capital', v, ctx); } },
    { label: 'Risque par trade (1 R)', unit: '$', value: o.risk, min: 1, onChange: function (v) { setMc('risk', v, ctx); } },
    { label: 'Seuil de ruine (perte)', unit: '$', value: o.ruin, min: 0, hint: '0 = pas de seuil', onChange: function (v) { setMc('ruin', v, ctx); } },
    { label: 'Graine', value: o.seed, min: 1, max: 999999, hint: 'même graine, mêmes tirages', onChange: function (v) { setMc('seed', Math.round(v), ctx); } }
  ]));
  s0.appendChild(U.card({ body: body })); root.appendChild(s0);

  var slot = h('div', { class: 'qt-stack' }); root.appendChild(slot);
  if (o.src === 'journal' && rows.length < 20) {
    slot.appendChild(U.empty({ title: rows.length ? 'Seulement ' + rows.length + ' trade' + (rows.length > 1 ? 's' : '') + ' clos au journal' : 'Aucun trade clos au journal', text: 'Il en faut au moins 20 : rééchantillonner moins de vingt résultats ne fait que recopier ton échantillon, avec ses hasards, dix mille fois. Passe en paramétrique, ou reviens quand le journal aura grandi.', action: U.button({ label: 'Passer en paramétrique', small: true, onClick: function () { setMc('src', 'param', ctx); } }) }));
    return;
  }
  var sample = o.src === 'journal' ? rows.map(function (r) { return o.unit === 'r' ? r.r * o.risk : r.pnl; }) : null;
  var arg = { op: 'mc', o: { mode: o.src === 'journal' ? 'boot' : 'param', p: o.p, rr: o.rr, disp: o.disp, risk: o.risk, cost: o.src === 'journal' ? 0 : o.cost, n: o.n, paths: 10000, capital: o.capital, ruin: o.ruin, seed: o.seed, sample: sample } };
  runInto(CACHE.mc, JSON.stringify(arg), arg, slot, function (res) { paintMC(slot, res, o, sample); }, 'Dix mille trajectoires de ' + o.n + ' trades…');
}

function paintMC(slot, res, o, sample) {
  var A = res.alt, N = res.nul, boot = !!sample, lvl = o.capital - o.ruin;
  var eTrade = boot ? res.mu : Q.expectancyR(o.p, o.rr, o.cost / o.risk) * o.risk;
  var s1 = U.section('Le *risque* de cramer', boot ? 'ton journal, rejoué' : 'ton hypothèse, rejouée');
  s1.appendChild(hub(core('Probabilité de ruine', o.ruin > 0 ? pct(A.ruin) : '—', null, o.ruin > 0 ? 'loi nulle ' + pct(N.ruin) + ' · seuil ' + F.usd(lvl, 0) : 'aucun seuil de ruine saisi'), [
    { label: 'Espérance / trade', value: F.usd(eTrade, 2, true), hint: (boot ? 'moyenne' : F.r(eTrade / o.risk, 3)) + ' · nulle 0' },
    { label: 'Résultat médian', value: F.usd(A.final50 - o.capital, 0, true), hint: 'nulle ' + F.usd(N.final50 - o.capital, 0, true) },
    { label: 'Finir en perte', value: pct(A.pLoss), hint: 'nulle ' + pct(N.pLoss) },
    { label: 'Creux max médian', value: F.usd(A.dd50, 0), hint: '95e centile ' + F.usd(A.dd95, 0) },
    { label: 'Série de pertes', value: F.int(A.streak50), unit: 'médiane', hint: '95e centile ' + F.int(A.streak95) },
    boot ? { label: 'Échantillon', value: F.int(sample.length), unit: 'trades', hint: 'tirés avec remise' } : { label: 'Taux d’équilibre', value: pct(res.pEq), hint: 'frais compris' }
  ], 3));
  slot.appendChild(s1);

  var s2 = U.section('L’*éventail*', o.n + ' trades · 5–95 % et 25–75 %');
  var hl = [{ y: o.capital, label: 'départ' }]; if (o.ruin > 0) hl.push({ y: lvl, label: 'ruine', tone: 'violet' });
  s2.appendChild(C.fan({ q: A.q, paths: A.paths, hlines: hl, fmt: kUsd, height: 230, xLabel: function (i) { return 'trade ' + res.cps[i]; }, legend: [{ label: 'médiane', tone: 'fg' }, { label: '90 % et 50 % des trajectoires', box: 'var(--violet-b)' }, { label: 'quatorze trajectoires', tone: 'mute' }] }));
  s2.appendChild(U.note('Chaque trajectoire est la même hypothèse, jouée dans un autre ordre. L’écart entre les deux bords n’est pas du talent qui varie : c’est l’ordre des tirages.' + (o.ruin > 0 ? ' La ruine est absorbante : un compte cramé ne trade plus, d’où le plancher.' : '')));
  slot.appendChild(s2);

  var s3 = U.section('Le résultat *final*', 'après ' + o.n + ' trades');
  s3.appendChild(histo({ values: A.finals, values2: N.finals, name1: boot ? 'journal' : 'hypothèse', name2: 'loi nulle', fmt: kUsd, refs: [{ x: o.capital, label: 'départ', tone: 'dim', dash: true }, { x: N.final50, label: 'médiane nulle', tone: 'fg', dash: true }, { x: A.final50, label: 'médiane', tone: 'violet' }], legend: [{ label: boot ? 'ton journal' : 'ton hypothèse', box: 'var(--violet)' }, { label: 'loi nulle, même tirage', tone: 'fg' }] }));
  s3.appendChild(h('div', { class: 'qt-line' }, h('span', null, '5e centile ', h('b', null, kUsd(A.final05))), h('span', null, 'médiane ', h('b', null, kUsd(A.final50))), h('span', null, '95e centile ', h('b', null, kUsd(A.final95)))));
  slot.appendChild(s3);

  var s4 = U.section('Le creux *maximal*', 'de sommet à creux, par trajectoire');
  var refs = [{ x: A.dd50, label: 'médiane', tone: 'violet' }, { x: N.dd50, label: 'médiane nulle', tone: 'fg', dash: true }]; if (o.ruin > 0) refs.push({ x: o.ruin, label: 'ruine', tone: 'mute', dash: true });
  s4.appendChild(histo({ values: A.dds, values2: N.dds, name1: boot ? 'journal' : 'hypothèse', name2: 'loi nulle', fmt: kUsd, refs: refs, legend: [{ label: boot ? 'ton journal' : 'ton hypothèse', box: 'var(--violet)' }, { label: 'loi nulle', tone: 'fg' }] }));
  s4.appendChild(U.note('Un creux est mesuré du plus haut atteint jusque-là. Une règle de perte suiveuse de prop firm se lit ici : ' + (o.ruin > 0 ? 'la ligne marque ton seuil saisi, mesuré depuis le départ.' : 'saisis un seuil de ruine pour la tracer.')));
  slot.appendChild(s4);

  var s5 = U.section('Avec et *sans* avantage', 'mêmes tirages uniformes');
  var row = function (l, a, b) { return { m: l, a: a, b: b }; };
  s5.appendChild(U.table({ cols: [{ k: 'm', label: 'Mesure', cls: 'wrap' }, { k: 'a', label: boot ? 'Journal' : 'Hypothèse', align: 'r' }, { k: 'b', label: 'Loi nulle', align: 'r' }], rows: [
    row('Espérance par trade', F.usd(eTrade, 2, true), F.usd(0, 2)),
    row('Probabilité de ruine', o.ruin > 0 ? pct(A.ruin, 2) : '—', o.ruin > 0 ? pct(N.ruin, 2) : '—'),
    row('Résultat final médian', F.usd(A.final50 - o.capital, 0, true), F.usd(N.final50 - o.capital, 0, true)),
    row('5e centile du résultat', F.usd(A.final05 - o.capital, 0, true), F.usd(N.final05 - o.capital, 0, true)),
    row('Probabilité de finir en perte', pct(A.pLoss), pct(N.pLoss)),
    row('Creux maximal médian', F.usd(A.dd50, 0), F.usd(N.dd50, 0)),
    row('Creux maximal, 95e centile', F.usd(A.dd95, 0), F.usd(N.dd95, 0)),
    row('Plus longue série de pertes, médiane', F.int(A.streak50), F.int(N.streak50)),
    row('Plus longue série de pertes, 95e centile', F.int(A.streak95), F.int(N.streak95))
  ] }));
  s5.appendChild(U.note(boot ? 'Loi nulle : tes propres résultats recentrés à espérance nulle (on retranche la moyenne, ' + F.usd(res.mu, 2, true) + ') : même dispersion, mêmes queues, aucun avantage. Ce qui reste de risque y est celui du hasard seul.'
    : 'Loi nulle : même R:R, même variabilité, taux de réussite ramené au taux d’équilibre (1 + c/L)/(1 + R:R) = ' + pct(res.pEq, 2) + ', où l’espérance nette est nulle. Sous un prix sans dérive elle est même négative, −c/L (ALP nº 3, onzième partie : « À dérive nulle, les quatre droites valent exactement −c/L ») : cette loi nulle est donc généreuse.'));
  slot.appendChild(s5);
}

/* ---------------- Onglet Backtest ---------------- */
var TZ_OPTS = [{ v: 'America/New_York', label: 'New York' }, { v: 'America/Chicago', label: 'Chicago (CME)' }, { v: 'Europe/Paris', label: 'Paris' }, { v: 'UTC', label: 'UTC' }];
var DEF_BT = { src: null, name: '', tz: 'America/New_York', k: 2, stop: 5, mode: 'rejet', from: null, to: null, warm: 30, maxPer: null, comm: null, slip: 2, seed: 7, synth: { seed: 11, sigma: 4, days: 20 } };
function btParams(set) {
  var o = Object.assign({}, DEF_BT, T.store.get(KEY.bt, {}));
  o.synth = Object.assign({}, DEF_BT.synth, o.synth || {});
  if (!fin(o.from)) o.from = set.winFrom; if (!fin(o.to)) o.to = set.winTo;
  if (!fin(o.maxPer)) o.maxPer = set.maxTradesDay; if (!fin(o.comm)) o.comm = set.commissionRT;
  return o;
}
function setBt(patch, ctx) { var c = Object.assign({}, T.store.get(KEY.bt, {}), patch); T.store.set(KEY.bt, c); if (ctx) ctx.rerender(); }
function engineParams(o, set) { return { k: o.k, stop: o.stop, mode: o.mode, from: o.from, to: o.to, warm: o.warm, maxPer: o.maxPer, comm: o.comm, slip: o.slip, tick: set.tick || 0.25, pv: set.pointValue || 2 }; }
function synthKey(sy) { return 'synth:' + sy.seed + ':' + sy.sigma + ':' + sy.days; }
/* Les barres courantes : synthétiques (régénérées depuis leur graine) ou le fichier chargé dans cette page. */
function ensureData(o) {
  if (o.src === 'synth') {
    var k = synthKey(o.synth);
    if (DATA.key === k && DATA.bars) return Promise.resolve(DATA);
    if (DATA.pending && DATA.pkey === k) return DATA.pending;
    DATA.pkey = k;
    DATA.pending = T.compute(quantEngine, { op: 'synth', o: { seed: o.synth.seed, sigma: o.synth.sigma, days: o.synth.days, base: 10000, tick: 0.25 } }).then(function (r) {
      DATA = { key: k, kind: 'synth', bars: r.bars, name: 'Marche aléatoire synthétique', info: { n: r.bars.length, firstT: r.bars[0].t, lastT: r.bars[r.bars.length - 1].t, hasVolume: true, warnings: [] }, text: null, pending: null, pkey: null };
      return DATA;
    });
    return DATA.pending;
  }
  if (o.src === 'csv' && DATA.kind === 'csv' && DATA.bars) return Promise.resolve(DATA);
  return null;
}
function loadText(text, name, ctx) {
  var o = btParams(ctx.settings);
  T.toast('Lecture de « ' + name + ' »…');
  T.compute(quantEngine, { op: 'parse', text: text, o: { tz: o.tz } }).then(function (r) {
    if (r.error || !r.bars.length) { DATA.err = { name: name, error: r.error || 'Aucune barre lisible.', firstSkip: r.firstSkip }; ctx.rerender(); return; }
    DATA = { key: 'csv:' + name + ':' + r.n + ':' + r.bars[0].t + ':' + r.bars[r.n - 1].t + ':' + o.tz, kind: 'csv', bars: r.bars, name: name, info: r, text: text, pending: null, pkey: null, err: null };
    setBt({ src: 'csv', name: name }, ctx);
  }, function (e) { DATA.err = { name: name, error: String(e && e.message || e) }; ctx.rerender(); });
}
function fileButton(label, kind, ctx) {
  var input = h('input', { type: 'file', accept: '.csv,.txt,.tsv,text/csv,text/plain', on: { change: function () { var f = input.files && input.files[0]; if (!f) return; var rd = new FileReader(); rd.onload = function () { loadText(String(rd.result || ''), f.name, ctx); }; rd.onerror = function () { T.toast('Fichier illisible'); }; rd.readAsText(f); } } });
  return h('label', { class: 'btn sm qt-file' + (kind ? ' ' + kind : ''), role: 'button', tabindex: '0', on: { keydown: function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } } } }, label, input);
}
function dataCard(ctx, o) {
  var set = ctx.settings, body = [], has = (o.src === 'synth') || (o.src === 'csv' && DATA.kind === 'csv' && DATA.bars);
  if (o.src === 'csv' && DATA.kind === 'csv' && DATA.bars) {
    var I = DATA.info, a = parisParts(I.firstT), b = parisParts(I.lastT);
    body.push(h('div', { class: 'qt-line' }, h('b', null, '« ' + DATA.name + ' »'), h('span', null, F.int(I.n) + ' barres'), h('span', null, 'du ' + pad2(a.d) + '/' + pad2(a.mo) + '/' + a.y + ' au ' + pad2(b.d) + '/' + pad2(b.mo) + '/' + b.y), h('span', null, 'séparateur : ' + I.sepName), h('span', null, 'temps : ' + ({ s: 'secondes Unix', ms: 'millisecondes', iso: 'ISO avec fuseau', local: 'heure locale du fichier' }[I.timeKind] || I.timeKind))));
    if (I.skipped) body.push(U.note(I.skipped + ' ligne' + (I.skipped > 1 ? 's' : '') + ' ignorée' + (I.skipped > 1 ? 's' : '') + (I.firstSkip ? ' (ligne ' + I.firstSkip.line + ' : « ' + I.firstSkip.text + ' »)' : '') + '.', true));
    (I.warnings || []).forEach(function (w) { body.push(U.note(w, true)); });
  } else if (o.src === 'synth') {
    body.push(h('div', { class: 'qt-row' }, U.pill('synthétique, pas le marché', 'acc'), h('span', { class: 'qt-line' }, 'marche aléatoire sans dérive · base arbitraire 10 000 · ' + o.synth.days + ' séances')));
  } else if (o.src === 'csv' && o.name) {
    body.push(U.note('Le fichier « ' + o.name + ' » n’est plus en mémoire : les barres restent sur cet appareil, le temps de la page, et ne sont jamais envoyées. Recharge-le pour relancer le backtest.', true));
  } else {
    body.push(h('p', { class: 'note' }, 'Exporte des barres d’une minute du MNQ (TradingView : menu du graphique, « Exporter les données du graphique », ou tout CSV) avec les colonnes time ou date, open, high, low, close, volume. Séparateur virgule, point-virgule ou tabulation ; temps en secondes Unix, en millisecondes ou en ISO. Le fichier est lu sur l’appareil et n’est envoyé nulle part.'));
  }
  if (DATA.err) body.push(U.note('« ' + DATA.err.name + ' » : ' + DATA.err.error + (DATA.err.firstSkip ? ' Première ligne refusée : ' + DATA.err.firstSkip.line + '.' : ''), true));
  body.push(U.fields([{ type: 'select', label: 'Fuseau du fichier', value: o.tz, options: TZ_OPTS, hint: 'seulement si l’heure du fichier n’a pas de fuseau', onChange: function (v) {
    setBt({ tz: v });
    if (DATA.kind === 'csv' && DATA.text) loadText(DATA.text, DATA.name, ctx); else ctx.rerender();
  } }]));
  var sy = o.synth, setSy = function (k, v) { var c = Object.assign({}, sy); c[k] = v; setBt({ synth: c }, ctx); };
  var syn = h('details', { class: 'qt-det' }, h('summary', null, 'Réglages de la marche synthétique'),
    U.fields([
      { label: 'σ par minute', unit: 'pt', value: sy.sigma, min: 0.25, max: 100, hint: 'à régler sur ta propre mesure', onChange: function (v) { setSy('sigma', v); } },
      { label: 'Séances', value: sy.days, min: 1, max: 120, onChange: function (v) { setSy('days', Math.round(v)); } },
      { label: 'Graine', value: sy.seed, min: 1, max: 999999, onChange: function (v) { setSy('seed', Math.round(v)); } }
    ], 3));
  if (o.src === 'synth') syn.open = true;
  body.push(syn);
  body.push(h('div', { class: 'qt-row' },
    fileButton(o.src === 'csv' && DATA.bars ? 'Changer de fichier' : 'Importer un CSV', 'pri', ctx),
    U.button({ label: o.src === 'synth' ? 'Synthétique : actif' : 'Données synthétiques', small: true, kind: o.src === 'synth' ? 'acc' : null, onClick: function () { DATA.err = null; setBt({ src: 'synth' }, ctx); } }),
    has || o.src ? U.button({ label: 'Effacer', small: true, kind: 'ghost', onClick: function () { DATA = { key: null, kind: null, bars: null, name: '', info: null, text: null, pending: null, pkey: null, err: null }; setBt({ src: null, name: '' }, ctx); } }) : null));
  void set;
  return U.card({ title: 'Barres d’une minute', meta: o.src === 'synth' ? 'synthétiques' : o.src === 'csv' && DATA.bars ? 'ton fichier' : 'à fournir', body: body });
}
function stratCard(ctx, o) {
  var set = ctx.settings;
  var body = [
    U.seg({ aria: 'Entrée', options: [{ v: 'rejet', label: 'Au rejet' }, { v: 'contact', label: 'Au contact' }], value: o.mode, onChange: function (v) { setBt({ mode: v }, ctx); } }),
    U.fields([
      { label: 'Bande à k écarts-types', unit: 'σ', value: o.k, min: 0.25, max: 6, onChange: function (v) { setBt({ k: v }, ctx); } },
      { label: 'Stop après la bande', unit: 'pt', value: o.stop, min: 0.25, max: 200, onChange: function (v) { setBt({ stop: v }, ctx); } },
      { label: 'Fenêtre, début (Paris)', unit: 'h', value: o.from, min: 0, max: 24, hint: hourLabel(o.from) + ' ; 15,5 = 15:30', onChange: function (v) { setBt({ from: v }, ctx); } },
      { label: 'Fenêtre, fin (Paris)', unit: 'h', value: o.to, min: 0, max: 24, hint: hourLabel(o.to) + ', sortie forcée', onChange: function (v) { setBt({ to: v }, ctx); } },
      { label: 'Échauffement VWAP', unit: 'min', value: o.warm, min: 0, max: 600, hint: 'pas de signal avant', onChange: function (v) { setBt({ warm: Math.round(v) }, ctx); } },
      { label: 'Trades max par séance', value: o.maxPer, min: 0, max: 50, hint: '0 = sans limite', onChange: function (v) { setBt({ maxPer: Math.round(v) }, ctx); } },
      { label: 'Commission', unit: '$', value: o.comm, min: 0, max: 50, hint: 'aller-retour, par contrat', onChange: function (v) { setBt({ comm: v }, ctx); } },
      { label: 'Glissement', unit: 'ticks', value: o.slip, min: 0, max: 40, hint: 'aller-retour ; 1 tick = ' + F.num(set.tick || 0.25, 2) + ' pt = ' + F.usd((set.tick || 0.25) * (set.pointValue || 2), 2), onChange: function (v) { setBt({ slip: v }, ctx); } }
    ]),
    U.note('Short seulement au-dessus de la VWAP, long seulement en dessous ; un contrat, un trade à la fois ; objectif : la VWAP de la barre précédente ; si stop et objectif tombent dans la même barre, le stop est compté (pire cas). Valeur du point ' + set.instrument + ' : ' + F.usd(set.pointValue || 2, 0) + ' (spécification CME du MNQ).')
  ];
  return U.card({ title: 'Règles', meta: 'VWAP ± ' + F.num(o.k, 2) + ' σ · stop ' + F.num(o.stop, 2) + ' pt', body: body });
}
function renderBT(root, ctx) {
  var set = ctx.settings, o = btParams(set);
  var s0 = U.section('Les *données*', 'ton fichier, ou le hasard pur'); s0.appendChild(dataCard(ctx, o)); root.appendChild(s0);
  var s1 = U.section('La *stratégie*', 'bande VWAP de séance'); s1.appendChild(stratCard(ctx, o)); root.appendChild(s1);
  var slot = h('div', { class: 'qt-stack' }); root.appendChild(slot);
  var pr = ensureData(o);
  if (!pr) {
    slot.appendChild(U.empty({ title: 'Pas encore de barres', text: 'Les résultats apparaîtront ici. Importe ton fichier de barres d’une minute avec le bouton de la carte « Barres d’une minute », ou lance la marche synthétique : elle montre ce que la stratégie rend quand il n’y a rien à trouver.' }));
    return;
  }
  slot.appendChild(wait('Préparation des barres…'));
  pr.then(function (D) {
    if (!slot.isConnected) return; T.clear(slot);
    var p = engineParams(o, set), arg = { op: 'bt', bars: D.bars, p: p, draws: 250, seed: o.seed };
    runInto(CACHE.bt, D.key + '|' + JSON.stringify(p) + '|' + o.seed, arg, slot, function (res) { paintBT(slot, res, o, set, D, ctx); }, 'Backtest et 2 × 250 tirages des lois nulles…');
  }, function (e) { if (!slot.isConnected) return; T.clear(slot); slot.appendChild(U.empty({ title: 'Les données n’ont pas pu être préparées', text: String(e && e.message || e) })); });
}
function paintBT(slot, res, o, set, D, ctx) {
  var st = res.stats, nl = res.nulls, synth = D.kind === 'synth';
  if (!st.n) {
    slot.appendChild(U.empty({ title: 'Aucun trade sur ' + F.int(res.bars) + ' barres', text: 'Aucune barre de la fenêtre ' + hourLabel(o.from) + '–' + hourLabel(o.to) + ' (heure de Paris) n’a rempli la règle. Vérifie la fenêtre et le fuseau du fichier, ou rapproche la bande (k plus petit).' }));
    return;
  }
  var s1 = U.section('Le résultat *net*', F.int(res.sessions) + ' séances · ' + F.int(res.bars) + ' barres');
  s1.appendChild(hub(core('Espérance nette par trade', F.usd(st.exp, 2, true), null, F.r(st.expR, 3) + ' · frais ' + F.usd(res.cost, 2) + ' par trade'), [
    { label: 'Trades', value: F.int(st.n), hint: F.num(st.n / res.sessions, 2) + ' par séance' },
    { label: 'Réussite', value: pct(st.winRate), hint: st.wins + ' / ' + st.n + ' gagnants' },
    { label: 'Facteur de profit', value: fin(st.pf) ? F.num(st.pf, 2) : st.pf === Infinity ? '∞' : '—', hint: 'gains / pertes' },
    { label: 'Creux maximal', value: F.usd(st.maxDD, 0), hint: 'net ' + F.usd(st.net, 0, true) },
    { label: 'Sharpe par trade', value: fin(st.sharpe) ? F.num(st.sharpe, 3) : '—', hint: 'moyenne / écart-type' },
    { label: 'Contre le hasard', value: nl ? 'p = ' + F.num(nl.rand2.p, 3) : '—', tone: nl && nl.rand2.p < 0.05 ? 'acc' : null, hint: 'minutes au hasard' }
  ], 3));
  slot.appendChild(s1);

  if (nl) {
    var s2 = U.section('Contre le *hasard*', nl.draws + ' tirages · graine ' + nl.seed);
    var box = function (on, l, v, hh) { return h('div', { class: on ? 'on' : null }, h('div', { class: 'l' }, l), h('div', { class: 'v' }, v), h('div', { class: 'h' }, hh)); };
    s2.appendChild(h('div', { class: 'qt-vs' },
      box(true, 'Ta stratégie', F.usd(st.exp, 2, true), F.int(st.n) + ' trades · par trade'),
      box(false, 'Mêmes minutes, sens au hasard', F.usd(nl.rand1.mean, 2, true), '90 % : ' + F.usd(nl.rand1.lo, 2) + ' à ' + F.usd(nl.rand1.hi, 2) + ' · p = ' + F.num(nl.rand1.p, 3)),
      box(false, 'Minutes au hasard', F.usd(nl.rand2.mean, 2, true), '90 % : ' + F.usd(nl.rand2.lo, 2) + ' à ' + F.usd(nl.rand2.hi, 2) + ' · p = ' + F.num(nl.rand2.p, 3))));
    s2.appendChild(histo({ values: nl.rand2.means, values2: nl.rand1.means, tone: 'mute', tone2: 'fg', name1: 'minutes au hasard', name2: 'sens au hasard', fmt: function (v) { return F.num(v, 1, '$'); }, refs: [{ x: st.exp, label: 'stratégie', tone: 'violet' }, { x: -res.cost, label: '−frais', tone: 'dim', dash: true }], legend: [{ label: 'minutes au hasard', box: 'var(--soft)' }, { label: 'sens au hasard', tone: 'fg' }, { label: 'ta stratégie', tone: 'violet' }] }));
    s2.appendChild(U.note('Histogramme : l’espérance par trade ($) de chacun des ' + nl.draws + ' tirages, pour les deux lois nulles. La p-valeur est la part des tirages qui font au moins aussi bien que la stratégie. Le sens au hasard garde les minutes et la géométrie de chaque trade ; les minutes au hasard gardent la règle de sens et la sortie, et ne changent que l’instant.'));
    if (synth) s2.appendChild(U.callout([h('b', null, 'Données synthétiques : il n’y a rien à trouver. '), 'Sur une marche sans dérive, l’espérance d’une sortie quelconque vaut −c/a : les frais, et rien d’autre (ALP nº 3, quatorzième partie : « E[R] = −c/a, quelle que soit la loi des incréments »). Attendu ici : ' + F.usd(-res.cost, 2) + ' par trade ; mesuré : ' + F.usd(st.exp, 2, true) + '. Ce qui s’en écarte est le bruit d’un échantillon de ' + st.n + ' trades.']));
    slot.appendChild(s2);
  }

  var s3 = U.section('La courbe de *capital*', 'un contrat, frais déduits');
  var eq = function (arr) { var s = 0, out = [[0, 0]]; arr.forEach(function (x, i) { s += x; out.push([i + 1, s]); }); return out; };
  var series = [{ name: 'Stratégie', points: eq(res.trades.map(function (t) { return t.pnl; })), tone: 'violet', width: 2 }];
  if (nl) { series.push({ name: 'Sens au hasard (1 tirage)', points: eq(nl.rand1.first), tone: 'mute', dash: true }); series.push({ name: 'Minutes au hasard (1 tirage)', points: eq(nl.rand2.first), tone: 'mute' }); }
  s3.appendChild(C.line({ series: series, x: { type: 'num', fmt: function (v) { return F.int(v); } }, y: { fmt: function (v) { return F.usd(v, 0); }, zero: true }, height: 220, ml: 58 }));
  slot.appendChild(s3);

  var s4 = U.section('Où finissent les *trades*', F.int(st.n) + ' trades : sortie, puis issue');
  var labels = { objectif: 'Objectif VWAP', stop: 'Stop', cloche: 'Fin de fenêtre' }, nodes = [], links = [];
  ['objectif', 'stop', 'cloche'].forEach(function (k) { if (res.fins[k]) nodes.push({ id: k, label: labels[k], col: 0, tone: k === 'objectif' ? 'violet' : 'mute' }); });
  nodes.push({ id: 'g', label: 'Gagnants', col: 1 }); nodes.push({ id: 'p', label: 'Perdants ou nuls', col: 1, tone: 'mute' });
  ['objectif', 'stop', 'cloche'].forEach(function (k) { if (res.finsWin[k][0]) links.push({ s: k, t: 'g', v: res.finsWin[k][0], tone: 'violet' }); if (res.finsWin[k][1]) links.push({ s: k, t: 'p', v: res.finsWin[k][1] }); });
  if (!st.wins) nodes = nodes.filter(function (n) { return n.id !== 'g'; });
  if (!(st.n - st.wins)) nodes = nodes.filter(function (n) { return n.id !== 'p'; });
  s4.appendChild(C.sankey({ nodes: nodes, links: links, height: 220 }));
  s4.appendChild(U.note('Un objectif VWAP peut perdre : la moyenne bouge pendant le trade, et les frais s’ajoutent. La fin de fenêtre est la sortie forcée à ' + hourLabel(o.to) + ' (heure de Paris).'));
  slot.appendChild(s4);

  var s5 = U.section('Par *heure* d’entrée', 'heure de Paris');
  s5.appendChild(C.bar({ cats: res.hours.map(function (x) { return pad2(x.h) + ' h'; }), series: [{ name: 'P&L net', values: res.hours.map(function (x) { return x.sum; }), tone: 'violet' }], fmt: function (v) { return F.usd(v, 0); }, height: 190, ml: 54 }));
  s5.appendChild(U.table({ cols: [{ k: 'h', label: 'Heure', fmt: function (v) { return pad2(v) + ':00'; } }, { k: 'n', label: 'Trades', align: 'r' }, { k: 'w', label: 'Réussite', align: 'r' }, { k: 'e', label: 'Espérance', align: 'r' }, { k: 'sum', label: 'Net', align: 'r', fmt: function (v) { return F.usd(v, 0, true); } }],
    rows: res.hours.map(function (x) { return { h: x.h, n: x.n, w: pct(x.wins / x.n, 0), e: F.usd(x.sum / x.n, 2, true), sum: x.sum }; }) }));
  s5.appendChild(U.note('Découper par heure multiplie les comparaisons : au seuil de 5 %, une heure sur vingt paraît « gagnante » par hasard, et il y en a ici ' + res.hours.length + '. Une heure ne se retient que si elle tient sur des données qui n’ont pas servi à la choisir.'));
  slot.appendChild(s5);

  var s6 = U.section('Les *trades*', res.trades.length > 150 ? '150 derniers sur ' + F.int(res.trades.length) : F.int(res.trades.length) + ' trades');
  var shown = res.trades.slice(-150).reverse();
  s6.appendChild(U.table({ cols: [
    { k: 't', label: 'Date', fmt: function (v) { var p = parisParts(v); return pad2(p.d) + '/' + pad2(p.mo); } },
    { k: 't', label: 'Heure', fmt: function (v) { var p = parisParts(v); return pad2(p.h) + ':' + pad2(p.m); } },
    { k: 'side', label: 'Sens', fmt: function (v) { return v > 0 ? 'long' : 'short'; } },
    { k: 'entry', label: 'Entrée', align: 'r', fmt: function (v) { return F.num(v, 2); } },
    { k: 'stop', label: 'Stop', align: 'r', fmt: function (v) { return F.num(v, 2); } },
    { k: 'exit', label: 'Sortie', align: 'r', fmt: function (v) { return F.num(v, 2); } },
    { k: 'fin', label: 'Fin', fmt: function (v) { return labels[v] || v; } },
    { k: 'pts', label: 'Points', align: 'r', fmt: function (v) { return F.num(v, 2, '', true); } },
    { k: 'pnl', label: 'Net', align: 'r', fmt: function (v) { return F.usd(v, 2, true); } },
    { k: 'r', label: 'R', align: 'r', fmt: function (v) { return F.r(v, 2); } }
  ], rows: shown, rowClass: function (r) { return r.pnl < 0 ? 'neg' : null; } }));
  s6.appendChild(h('div', { class: 'qt-row' }, U.button({ label: 'Envoyer au desk Métriques', small: true, kind: 'pri', onClick: function () {
    T.store.set(KEY.last, { label: 'VWAP ± ' + F.num(o.k, 2) + ' σ · stop ' + F.num(o.stop, 2) + ' pt · ' + (o.mode === 'rejet' ? 'rejet' : 'contact') + ' · ' + (synth ? 'synthétique' : D.name), at: Date.now(), source: synth ? 'synth' : 'csv',
      trades: res.trades.map(function (t) { return { at: t.t, pnl: Math.round(t.pnl * 100) / 100, r: Math.round(t.r * 10000) / 10000, side: t.side > 0 ? 'long' : 'short' }; }) });
    T.toast('Backtest enregistré : le desk Métriques peut le lire'); T.nav.go('perf');
  } }), h('span', { class: 'qt-line' }, 'Le desk Métriques reprend ces trades comme source « Backtest ».')));
  slot.appendChild(s6);
  void ctx;
}

/* ---------------- Onglet Robustesse ---------------- */
function renderRB(root, ctx) {
  var set = ctx.settings, o = btParams(set), pr = ensureData(o);
  var stops = Q.stopGrid(o.stop, set.tick || 0.25);
  var s0 = U.section('Le *balayage*', '4 × 4 réglages, mêmes séances');
  s0.appendChild(h('div', { class: 'qt-line' }, h('span', null, 'k ∈ {' + Q.K_GRID.map(function (k) { return F.num(k, 1); }).join(' ; ') + '}'), h('span', null, 'stop ∈ {' + stops.map(function (s) { return F.num(s, 2); }).join(' ; ') + '} pt'), h('span', null, 'le reste : réglages du backtest')));
  root.appendChild(s0);
  var slot = h('div', { class: 'qt-stack' }); root.appendChild(slot);
  if (!pr) {
    slot.appendChild(U.empty({ title: 'Rien à balayer pour l’instant', text: 'Le balayage rejoue la stratégie sur les barres de l’onglet Backtest : importe ton fichier, ou lance la marche synthétique. Il faut au moins huit séances pour la validation croisée.', action: U.button({ label: 'Ouvrir le backtest', small: true, kind: 'pri', onClick: function () { ctx.setTab('backtest'); } }) }));
    return;
  }
  slot.appendChild(wait('Préparation des barres…'));
  pr.then(function (D) {
    if (!slot.isConnected) return; T.clear(slot);
    var p = engineParams(o, set), arg = { op: 'sweep', bars: D.bars, p: p, ks: Q.K_GRID, stops: stops };
    runInto(CACHE.sw, D.key + '|' + JSON.stringify(p) + '|' + stops.join(','), arg, slot, function (res) { paintRB(slot, res, o, stops, D); }, 'Seize backtests et 70 partitions…');
  }, function (e) { if (!slot.isConnected) return; T.clear(slot); slot.appendChild(U.empty({ title: 'Les données n’ont pas pu être préparées', text: String(e && e.message || e) })); });
}
function paintRB(slot, res, o, stops, D) {
  var G = res.grid, cell = function (k, s) { return G.find(function (g) { return g.k === k && g.stop === s; }); };
  var s1 = U.section('L’espérance, *case par case*', '$ net par trade');
  s1.appendChild(C.heat({ rows: Q.K_GRID.map(function (k) { return 'k = ' + F.num(k, 1); }), cols: stops.map(function (s) { return F.num(s, 2) + ' pt'; }), values: Q.K_GRID.map(function (k) { return stops.map(function (s) { var c = cell(k, s); return c && c.n ? c.exp : NaN; }); }), fmt: function (v) { return F.num(v, 2, '', true); }, diverging: true, corner: 'k \\ stop' }));
  s1.appendChild(C.heat({ rows: Q.K_GRID.map(function (k) { return 'k = ' + F.num(k, 1); }), cols: stops.map(function (s) { return F.num(s, 2) + ' pt'; }), values: Q.K_GRID.map(function (k) { return stops.map(function (s) { var c = cell(k, s); return c ? c.n : NaN; }); }), fmt: function (v) { return F.int(v); }, corner: 'trades' }));
  var inGrid = Q.K_GRID.indexOf(o.k) >= 0;
  s1.appendChild(U.note('Le stop de ton réglage (' + F.num(o.stop, 2) + ' pt) est la deuxième colonne' + (inGrid ? ', ton k une des lignes.' : ' ; ton k (' + F.num(o.k, 2) + ') n’est pas sur la grille.') + ' Une case isolée qui brille au milieu de voisines ternes est le motif d’un réglage chanceux, pas d’un avantage.'));
  slot.appendChild(s1);

  var valid = G.filter(function (g) { return g.n >= 2 && fin(g.sharpe); }), N = valid.length;
  var best = valid.slice().sort(function (a, b) { return b.sharpe - a.sharpe; })[0];
  var sds = valid.map(function (g) { return g.sharpe; }), sdT = sds.length > 1 ? S.sd(sds) : NaN;
  var D2 = best ? Q.dsr(best.sharpe, best.n, N, best.skew, best.exkurt, sdT) : null, cs = res.cscv;
  var s2 = U.section('Le *surapprentissage*, chiffré', 'CSCV · Sharpe déflaté');
  s2.appendChild(hub(core('Probabilité de surapprentissage', cs.error ? '—' : pct(cs.pbo, 0), null, cs.error ? cs.error : cs.splits + ' partitions de ' + res.sessions + ' séances en 8 blocs'), [
    { label: 'Meilleur réglage', value: best ? 'k = ' + F.num(best.k, 1) : '—', hint: best ? 'stop ' + F.num(best.stop, 2) + ' pt' : 'aucun à 2 trades' },
    { label: 'Sharpe du meilleur', value: best ? F.num(best.sharpe, 3) : '—', hint: best ? F.int(best.n) + ' trades' : 'par trade' },
    { label: 'Seuil SR₀', value: D2 ? F.num(D2.sr0, 3) : '—', hint: N + ' essais · σ ' + (fin(sdT) ? F.num(sdT, 3) : '—') },
    { label: 'Sharpe déflaté', value: D2 ? pct(D2.dsr, 0) : '—', tone: D2 && D2.dsr >= 0.95 ? 'acc' : null, hint: D2 && D2.dsr >= 0.95 ? 'déclarable' : 'non déclarable' },
    { label: 'Logit médian', value: cs.error ? '—' : F.num(cs.medianLogit, 2), hint: 'rang en test' },
    { label: 'Dégradation', value: cs.error ? '—' : F.usd(cs.degradation, 0, true), hint: 'par séance, en test' }
  ], 3));
  if (!cs.error) {
    s2.appendChild(histo({ values: cs.omegas, tone: 'mute', name1: 'partitions', fmt: function (v) { return F.pct(v, 0); }, refs: [{ x: 0.5, label: 'médiane en test', tone: 'violet', dash: true }] }));
    s2.appendChild(U.note('Chaque partition coupe les séances en deux moitiés : on choisit le meilleur réglage sur la première, on lit son rang relatif sur la seconde (barres : les ' + cs.splits + ' partitions). Sous 50 % (logit négatif), le réglage choisi finit sous la médiane. Sur des réglages sans avantage, la probabilité vaut ½ par symétrie ; au-delà, la sélection fait pire que le hasard.'));
  }
  slot.appendChild(s2);
  var verdict = U.card({ body: [
    h('div', { class: 'qt-verdict' }, U.pill(cs.error ? 'incomplet' : cs.pbo > 0.5 ? 'sélection pas meilleure que le hasard' : cs.pbo > 0.25 ? 'sélection peu informative' : 'sélection informative', cs.error ? null : cs.pbo <= 0.25 ? 'acc' : 'no'), h('span', null, cs.error ? 'La validation croisée demande au moins huit séances.' : 'La PBO ne dit pas si la stratégie gagne : elle dit si choisir le meilleur réglage sur le passé est informatif. Une PBO basse sur des réglages tous perdants ne sauve rien.')),
    h('div', { class: 'qt-verdict' }, U.pill(D2 && D2.dsr >= 0.95 ? 'déclarable' : 'non déclarable', D2 && D2.dsr >= 0.95 ? 'acc' : 'no'), h('span', null, 'Le Sharpe déflaté retranche du meilleur Sharpe ce que le choix parmi ' + N + ' réglages explique à lui seul (seuil SR₀). Sous 95 %, le résultat n’est pas publiable.'))
  ] });
  slot.appendChild(verdict);
  slot.appendChild(U.note('Sources : CSCV portée ligne à ligne depuis alp1/overfit.py (Bailey, Borwein et López de Prado) ; SR₀ = σ·[(1 − γ)·Φ⁻¹(1 − 1/N) + γ·Φ⁻¹(1 − 1/(N·e))], σ étant l’écart-type mesuré des Sharpe entre réglages ; DSR = PSR(SR₀) avec asymétrie et kurtosis du meilleur réglage (alp1/pathstats.py).' + (D.kind === 'synth' ? ' Données synthétiques : la grille entière est du bruit, et la PBO doit tourner autour de ½.' : '')));
}

/* ---------------- Onglet Échantillon ---------------- */
var DEF_ECH = { sr: 0.10, B: 16, alpha: 0.05, power: 0.80, dpd: 2 };
function echParams() { return Object.assign({}, DEF_ECH, T.store.get(KEY.ech, {})); }
function setEch(k, v, ctx) { var c = T.store.get(KEY.ech, {}); c[k] = v; T.store.set(KEY.ech, c); ctx.rerender(); }
function renderECH(root, ctx) {
  var set = ctx.settings, o = echParams(), W = Q.wall(o.sr, o.B, o.alpha, o.power), K1 = Q.zSum(o.alpha, o.power), K2 = Math.sqrt(2 * Math.log(Math.max(o.B, 1)));
  var all = T.journal.list(), rows = Q.fromJournal(all, set.riskPerTrade), n = rows.length, years = W.n / (o.dpd * Q.SESSIONS);
  var s0 = U.section('Ce qu’il faut *établir*', 'l’effet visé, pas l’effet observé');
  s0.appendChild(U.card({ body: [U.fields([
    { label: 'Sharpe visé', value: o.sr, min: 0.01, max: 2, hint: 'par décision : espérance / écart-type', onChange: function (v) { setEch('sr', v, ctx); } },
    { label: 'Configurations (B)', value: o.B, min: 1, max: 100000, hint: 'B = 2ᵏ pour k leviers ; ALP nº 3 : 16', onChange: function (v) { setEch('B', Math.round(v), ctx); } },
    { label: 'Seuil α (unilatéral)', unit: '%', value: +(o.alpha * 100).toFixed(2), min: 0.1, max: 25, onChange: function (v) { setEch('alpha', v / 100, ctx); } },
    { label: 'Puissance', unit: '%', value: +(o.power * 100).toFixed(1), min: 50, max: 99.9, onChange: function (v) { setEch('power', v / 100, ctx); } },
    { label: 'Décisions par jour', value: o.dpd, min: 0.1, max: 50, onChange: function (v) { setEch('dpd', v, ctx); } }
  ], 3), U.note('Le nombre requis part de l’effet à détecter, déclaré ici, et jamais du Sharpe observé : sinon un très mauvais résultat exigerait un petit échantillon et passerait.')] }));
  root.appendChild(s0);

  var s1 = U.section('Le *mur*', 'la plus exigeante des deux routes lie');
  s1.appendChild(hub(core('Décisions requises', F.int(W.n), null, 'Sharpe ' + F.num(o.sr, 2) + ' · ' + F.int(o.B) + ' configuration' + (o.B > 1 ? 's' : '') + ' · ' + F.num(years, 1) + ' an à ' + F.num(o.dpd, 1) + '/jour'), [
    { label: 'Route 1 · test t', value: F.int(W.r1), tone: W.taxe ? null : 'acc', hint: 'K = z_α + z_β = ' + F.num(K1, 3) },
    { label: 'Route 2 · taxe', value: F.int(Math.round(W.r2)), tone: W.taxe ? 'acc' : null, hint: 'K = √(2 ln B) = ' + F.num(K2, 3) },
    { label: 'Bascule des routes', value: F.num(Q.configsCrossing(o.alpha, o.power), 1), unit: 'config.', hint: 'au-delà, la taxe lie' },
    { label: 'Trades clos', value: F.int(n), hint: 'refus compris : ' + F.int(all.length) },
    { label: 'Encore', value: F.int(Math.max(0, W.n - n)), unit: 'décisions', hint: W.n > n ? '≈ ' + F.num((W.n - n) / o.dpd / 21, 1) + ' mois' : 'mur franchi' },
    { label: 'Années de carrière', value: F.num(years, 2), hint: Q.SESSIONS + ' séances par an' }
  ], 3));
  slot1(s1, W, n, o, K1, K2);
  root.appendChild(s1);

  var s2 = U.section('La table 14, *recalculée*', F.int(o.B) + ' configurations');
  s2.appendChild(U.table({ cols: [{ k: 'sr', label: 'Sharpe', fmt: function (v) { return F.num(v, 3); } }, { k: 'a', label: 'Route 1', align: 'r', fmt: F.int }, { k: 'b', label: 'Route 2', align: 'r', fmt: function (v) { return F.int(Math.round(v)); } }, { k: 'y2', label: 'à 2/jour', align: 'r', fmt: function (v) { return F.num(v, 1, 'an'); } }, { k: 'y3', label: 'à 3/jour', align: 'r', fmt: function (v) { return F.num(v, 1, 'an'); } }],
    rows: [0.05, 0.075, 0.10, 0.15].map(function (sr) { var w = Q.wall(sr, o.B, o.alpha, o.power); return { sr: sr, a: w.r1, b: w.r2, y2: w.n / (2 * Q.SESSIONS), y3: w.n / (3 * Q.SESSIONS) }; }), rowClass: function (r) { return Math.abs(r.sr - o.sr) < 1e-9 ? 'sel' : null; } }));
  s2.appendChild(U.note('Source : ALP nº 3, huitième partie, table 14 — à seize configurations, 619 décisions par la route 1 contre 555 par la route 2 pour un Sharpe de 0,10 ; « c’est la plus exigeante qui lie : 619 décisions, soit 1,2 an à deux décisions par jour ». Les années, ici, suivent l’exigence liante ; la table publiée les calcule sur la route 2.'));
  root.appendChild(s2);

  var s3 = U.section('Le *journal*, vers N', n ? F.int(n) + ' / ' + F.int(W.n) : 'vide');
  var share = Math.min(1, n / W.n);
  s3.appendChild(U.card({ body: [h('div', { class: 'qt-prog' },
    h('div', { class: 'qt-line' }, h('b', null, pct(share, 1)), h('span', null, 'du mur · ' + F.int(n) + ' trade' + (n > 1 ? 's' : '') + ' clos sur ' + F.int(W.n))),
    h('div', { class: 'qt-bar', role: 'progressbar', 'aria-valuemin': '0', 'aria-valuemax': String(W.n), 'aria-valuenow': String(n) }, h('i', { style: 'width:' + (share * 100).toFixed(2) + '%' })),
    h('div', { class: 'qt-ticks' }, h('span', null, '0'), h('span', null, F.int(Math.round(W.n / 2))), h('span', null, F.int(W.n)))),
    U.note('Seuls les trades pris et clos portent un résultat mesurable ; les refus comptent dans la discipline, pas dans la preuve.')] }));
  if (n) {
    var wins = rows.filter(function (r) { return r.pnl > 0; }), losses = rows.filter(function (r) { return r.pnl < 0; });
    var wl = Q.wilson(wins.length, n), be = Q.breakEven(wins.length ? S.mean(wins.map(function (r) { return r.pnl; })) : NaN, losses.length ? S.mean(losses.map(function (r) { return r.pnl; })) : NaN);
    var rs = rows.map(function (r) { return r.r; }), srObs = rs.length > 1 && S.sd(rs) > 0 ? S.mean(rs) / S.sd(rs) : NaN;
    s3.appendChild(U.kpis([
      { label: 'Taux de réussite', value: pct(wl.p), hint: wins.length + ' / ' + n },
      { label: 'Wilson à 95 %', value: pct(wl.lo, 0) + '–' + pct(wl.hi, 0), hint: 'largeur ' + pct(wl.hi - wl.lo, 0) },
      { label: 'Taux d’équilibre', value: pct(be), hint: fin(be) ? 'à gain/perte moyens' : 'gain et perte requis' },
      { label: 'Sharpe observé', value: fin(srObs) ? F.num(srObs, 3) : '—', hint: 'descriptif' }
    ], 4));
    var inside = fin(be) && be >= wl.lo && be <= wl.hi;
    s3.appendChild(C.gauge({ value: wl.p, min: 0, max: 1, band: [wl.lo, wl.hi], ticks: [[0, '0 %'], [0.25, '25 %'], [0.5, '50 %'], [0.75, '75 %'], [1, '100 %']] }));
    s3.appendChild(U.note(fin(be) ? (inside ? 'Le taux d’équilibre (' + pct(be) + ') tombe dans l’intervalle de Wilson : le journal ne distingue pas encore ton taux de réussite de celui qui annule l’espérance.' : 'Le taux d’équilibre (' + pct(be) + ') tombe hors de l’intervalle de Wilson. C’est un écart sur ' + n + ' trades, pas encore une preuve : le mur demande ' + F.int(W.n) + ' décisions.') : 'Le taux d’équilibre demande au moins un gain et une perte au journal.'));
  } else {
    s3.appendChild(U.empty({ title: 'Aucun trade clos au journal', text: 'Chaque trade pris puis clos au journal avance cette barre. L’intervalle de Wilson du taux de réussite apparaîtra au premier.', action: U.button({ label: 'Ouvrir le journal', small: true, onClick: function () { T.nav.go('journal'); } }) }));
  }
  root.appendChild(s3);
  root.appendChild(U.callout([h('b', null, 'Avant N, le journal décrit, il ne juge pas. '), 'Un Sharpe de ' + F.num(o.sr, 2) + ' par décision ne se sépare du hasard qu’après ' + F.int(W.n) + ' décisions ; tout ce qui précède est une description honnête, pas un verdict sur ta compétence — ni dans un sens, ni dans l’autre.']));
  void set;
}
function slot1(sec, W, n, o, K1, K2) {
  var lo = Math.max(10, Math.round(W.n / 9)), top = Math.max(W.n * 3, n * 1.1, lo * 4), pts1 = [], pts2 = [], pts3 = [];
  for (var i = 0; i <= 60; i++) { var N = Math.round(lo * Math.pow(top / lo, i / 60)); pts1.push([N, Q.threshold(N, K1)]); pts2.push([N, Q.threshold(N, K2)]); pts3.push([N, o.sr]); }
  var vl = [{ x: W.n, label: 'mur ' + F.int(W.n) }]; if (n >= lo && n <= top) vl.push({ x: n, label: 'journal' });
  sec.appendChild(C.line({ series: [{ name: 'Route 1 · test t', points: pts1, tone: 'fg' }, { name: 'Route 2 · taxe', points: pts2, tone: 'mute', dash: true }, { name: 'Sharpe visé ' + F.num(o.sr, 2), points: pts3, tone: 'violet' }], x: { type: 'num', fmt: function (v) { return F.int(v); } }, y: { fmt: function (v) { return F.num(v, 2); }, min: 0 }, vlines: vl, height: 210, endDots: false }));
  sec.appendChild(U.note('Les deux routes ont la même forme, K/√N : le Sharpe minimal qu’un échantillon de N décisions sépare du hasard. Le mur est l’abscisse où la plus haute des deux courbes passe sous le Sharpe visé.'));
}

/* =====================================================================
   4. Le desk
   ===================================================================== */
var HEAD = {
  montecarlo: { k: 'Quant · Monte-Carlo', t: 'Dix mille *carrières*, avant la vraie.', l: 'Le même avantage, rejoué dix mille fois dans un autre ordre : la dispersion des issues, le creux le plus profond, le risque de cramer le compte. Puis la même chose sans avantage, pour voir ce que le hasard fait déjà seul.' },
  backtest: { k: 'Quant · Backtest', t: 'La bande VWAP, *sur tes données*.', l: 'Tu fournis des barres d’une minute du MNQ ; la stratégie est rejouée règle par règle, frais compris, puis comparée à deux lois nulles : les mêmes minutes avec un sens tiré au hasard, et des minutes tirées au hasard.' },
  robustesse: { k: 'Quant · Robustesse', t: 'Un réglage, ou *seize* ?', l: 'Seize réglages voisins rejoués sur les mêmes séances. Un bon résultat entouré de mauvais voisins est un accident : la validation croisée combinatoire et le Sharpe déflaté le chiffrent.' },
  echantillon: { k: 'Quant · Échantillon', t: 'Combien de *décisions* ?', l: 'Un Sharpe de 0,10 par décision ne se distingue du hasard qu’après plusieurs centaines de décisions. Avant ce nombre, le journal décrit ; il ne juge pas.' }
};
var RENDER = { montecarlo: renderMC, backtest: renderBT, robustesse: renderRB, echantillon: renderECH };
T.desk({
  id: 'quant', label: 'Quant & backtest', glyph: 'Q', group: 'Recherche', order: 50,
  tabs: [{ id: 'montecarlo', label: 'Monte-Carlo' }, { id: 'backtest', label: 'Backtest' }, { id: 'robustesse', label: 'Robustesse' }, { id: 'echantillon', label: 'Échantillon' }],
  render: function (root, ctx) {
    injectCss();
    var tab = HEAD[ctx.tab] ? ctx.tab : 'montecarlo', hd = HEAD[tab];
    root.appendChild(U.page({ kicker: hd.k, title: hd.t, lede: hd.l }));
    root.appendChild(U.tabs({ tabs: this.tabs, value: tab, onChange: ctx.setTab }));
    RENDER[tab](root, ctx);
    typo(root);
    var un = (tab === 'echantillon' || tab === 'montecarlo') ? T.journal.on(function () { ctx.rerender(); }) : null;
    return function () { if (un) un(); };
  }
});
