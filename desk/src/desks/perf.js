/* Desk « Métriques & espaces » : la feuille de score complète d’une série de trades,
   chaque mesure avec sa définition exacte et, quand elle existe, sa loi nulle ; la
   distribution, le temps, l’espace des paramètres en 2D et en 3D, et la robustesse
   (PSR, DSR, bootstrap stationnaire porté de alp1/mc.py). */
var h = T.h, U = T.ui, C = T.chart, F = T.fmt, S = T.stats;
T.lib = T.lib || {};
var P = T.lib.perf = {};

/* =====================================================================
   1. Primitives statistiques — fonctions pures, aucun DOM, aucun T.store
   ===================================================================== */
function fin(v) { return typeof v === 'number' && isFinite(v); }
function sum(a) { var s = 0; for (var i = 0; i < a.length; i++) s += a[i]; return s; }
function phi(z) { return Math.exp(-0.5 * z * z) / Math.sqrt(2 * Math.PI); }
var EULER = 0.5772156649015329;
P.fin = fin;
P.phi = phi;

/* Moments de population (ceux de Bailey et López de Prado) ; l’écart-type publié est à n − 1. */
P.moments = function (x) {
  var n = x.length;
  if (!n) return { n: 0, mean: NaN, sd: NaN, skew: NaN, exKurt: NaN };
  var m = sum(x) / n, m2 = 0, m3 = 0, m4 = 0;
  for (var i = 0; i < n; i++) { var d = x[i] - m, d2 = d * d; m2 += d2; m3 += d2 * d; m4 += d2 * d2; }
  m2 /= n; m3 /= n; m4 /= n;
  return { n: n, mean: m, sd: S.sd(x), skew: m2 > 0 ? m3 / Math.pow(m2, 1.5) : NaN, exKurt: m2 > 0 ? m4 / (m2 * m2) - 3 : NaN };
};
P.sharpe = function (x) { if (x.length < 2) return NaN; var s = S.sd(x); return s > 0 ? S.mean(x) / s : NaN; };
/* Écart de baisse sous le seuil MAR, divisé par N total (et non par le seul nombre de pertes). */
P.downsideDev = function (x, mar) {
  mar = mar || 0; if (!x.length) return NaN;
  var s = 0; for (var i = 0; i < x.length; i++) { var d = Math.min(0, x[i] - mar); s += d * d; }
  return Math.sqrt(s / x.length);
};
P.sortino = function (x, mar) {
  mar = mar || 0; if (!x.length) return NaN;
  var dd = P.downsideDev(x, mar), ex = S.mean(x) - mar;
  if (!(dd > 0)) return ex > 0 ? Infinity : NaN;
  return ex / dd;
};
P.omega = function (x, L) {
  L = L || 0; var up = 0, dn = 0;
  for (var i = 0; i < x.length; i++) { if (x[i] > L) up += x[i] - L; else dn += L - x[i]; }
  return dn > 0 ? up / dn : (up > 0 ? Infinity : NaN);
};
P.profitFactor = function (x) {
  var g = 0, l = 0;
  for (var i = 0; i < x.length; i++) { if (x[i] > 0) g += x[i]; else if (x[i] < 0) l -= x[i]; }
  return l > 0 ? g / l : (g > 0 ? Infinity : NaN);
};
P.payoff = function (x) {
  var gw = 0, nw = 0, gl = 0, nl = 0;
  for (var i = 0; i < x.length; i++) { if (x[i] > 0) { gw += x[i]; nw++; } else if (x[i] < 0) { gl -= x[i]; nl++; } }
  return nw && nl ? (gw / nw) / (gl / nl) : NaN;
};
P.winRate = function (x) { if (!x.length) return NaN; var k = 0; for (var i = 0; i < x.length; i++) if (x[i] > 0) k++; return k / x.length; };
P.wilson = function (k, n, z) {
  if (!n) return { p: NaN, lo: NaN, hi: NaN };
  z = z == null ? S.normPpf(0.975) : z;
  var p = k / n, z2 = z * z, den = 1 + z2 / n, c = (p + z2 / (2 * n)) / den, hw = z * Math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / den;
  return { p: p, lo: c - hw, hi: c + hw };
};
P.kelly = function (p, b) { return fin(p) && b > 0 ? p - (1 - p) / b : NaN; };
P.streaks = function (x) {
  var w = 0, l = 0, cw = 0, cl = 0;
  for (var i = 0; i < x.length; i++) {
    if (x[i] > 0) { cw++; cl = 0; } else if (x[i] < 0) { cl++; cw = 0; } else { cw = 0; cl = 0; }
    if (cw > w) w = cw; if (cl > l) l = cl;
  }
  return { win: w, loss: l };
};
P.tailRatio = function (sorted) { var a = S.quantile(sorted, 0.95), b = S.quantile(sorted, 0.05); return b !== 0 && fin(b) ? Math.abs(a) / Math.abs(b) : NaN; };
P.cornishFisher = function (z, g1, g2) { return z + (z * z - 1) * g1 / 6 + (z * z * z - 3 * z) * g2 / 24 - (2 * z * z * z - 5 * z) * g1 * g1 / 36; };
P.varHist = function (sorted, a) { return -S.quantile(sorted, a); };
P.varGauss = function (m, s, a) { return -(m + s * S.normPpf(a)); };
P.varCF = function (m, s, g1, g2, a) { return -(m + s * P.cornishFisher(S.normPpf(a), g1, g2)); };
P.cvarHist = function (sorted, a) {
  var q = S.quantile(sorted, a), s = 0, k = 0;
  for (var i = 0; i < sorted.length && sorted[i] <= q; i++) { s += sorted[i]; k++; }
  return k ? -s / k : NaN;
};
P.cvarGauss = function (m, s, a) { var z = S.normPpf(a); return -(m - s * phi(z) / a); };

/* Courbe de capital, drawdowns et épisodes. eq[0] = capital de départ ; un épisode court
   d’un pic au premier retour à ce pic (end = null s’il n’est pas refermé). */
P.drawdowns = function (pnl, capital) {
  var eq = [capital], dd = [], ddPct = [], c = capital, pk = capital, pkI = 0, max = 0, maxPct = 0, eps = [], cur = null;
  for (var i = 0; i < pnl.length; i++) {
    c += pnl[i]; eq.push(c);
    if (c >= pk) { if (cur) { cur.end = i + 1; eps.push(cur); cur = null; } pk = c; pkI = i + 1; }
    else {
      if (!cur) cur = { start: pkI, trough: i + 1, end: null, depth: 0, depthPct: 0 };
      var d0 = pk - c; if (d0 > cur.depth) { cur.depth = d0; cur.trough = i + 1; }
      var p0 = pk > 0 ? d0 / pk : 1; if (p0 > cur.depthPct) cur.depthPct = p0;
    }
    var dN = pk - c, pN = pk > 0 ? dN / pk : (dN > 0 ? 1 : 0);
    dd.push(dN); ddPct.push(pN); if (dN > max) max = dN; if (pN > maxPct) maxPct = pN;
  }
  if (cur) eps.push(cur);
  var longest = 0; eps.forEach(function (e) { var L = (e.end == null ? pnl.length : e.end) - e.start; if (L > longest) longest = L; });
  return { eq: eq, dd: dd, ddPct: ddPct, max: max, maxPct: maxPct, episodes: eps, longest: longest };
};
P.ulcer = function (ddPct) { if (!ddPct.length) return NaN; var s = 0; for (var i = 0; i < ddPct.length; i++) s += ddPct[i] * ddPct[i]; return Math.sqrt(s / ddPct.length); };
P.autocorr1 = function (x) {
  var n = x.length; if (n < 3) return NaN;
  var m = S.mean(x), num = 0, den = 0;
  for (var i = 0; i < n; i++) { var d = x[i] - m; den += d * d; if (i < n - 1) num += d * (x[i + 1] - m); }
  return den > 0 ? num / den : NaN;
};
/* Test des suites de Wald-Wolfowitz : les nuls sont exclus. z < 0 : gains et pertes groupés. */
P.runsTest = function (x) {
  var s = []; for (var i = 0; i < x.length; i++) if (x[i] !== 0) s.push(x[i] > 0 ? 1 : 0);
  var n = s.length, n1 = 0; for (var j = 0; j < n; j++) n1 += s[j];
  var n2 = n - n1, runs = n ? 1 : 0; for (var k = 1; k < n; k++) if (s[k] !== s[k - 1]) runs++;
  if (!n1 || !n2 || n < 3) return { runs: runs, n1: n1, n2: n2, mu: NaN, sd: NaN, z: NaN };
  var mu = 2 * n1 * n2 / n + 1, va = 2 * n1 * n2 * (2 * n1 * n2 - n) / (n * n * (n - 1));
  return { runs: runs, n1: n1, n2: n2, mu: mu, sd: Math.sqrt(va), z: va > 0 ? (runs - mu) / Math.sqrt(va) : NaN };
};
/* Longueur de bloc moyenne du bootstrap stationnaire (alp1.mc.block_length_for_autocorrelation). */
P.blockLength = function (rho) {
  if (!fin(rho) || Math.abs(rho) < 1e-9) return 1;
  if (Math.abs(rho) >= 1) return NaN;
  return Math.max(1, -1 / Math.log(Math.abs(rho)));
};
/* PSR, DSR, MinTRL : alp1/pathstats.py et alp1/overfit.py, Sharpe par observation. */
P.psrVar = function (sr, g1, g2) { return 1 - (g1 || 0) * sr + 0.25 * ((g2 || 0) + 2) * sr * sr; };
P.psr = function (sr, n, sr0, g1, g2) {
  if (n < 2 || !fin(sr)) return NaN; sr0 = sr0 || 0;
  var v = P.psrVar(sr, g1, g2); if (v <= 0) return sr > sr0 ? 1 : 0;
  return S.normCdf((sr - sr0) * Math.sqrt(n - 1) / Math.sqrt(v));
};
P.expectedMaxSharpe = function (N, sdT) {
  if (!(N >= 2)) return 0;
  return sdT * ((1 - EULER) * S.normPpf(1 - 1 / N) + EULER * S.normPpf(1 - 1 / (N * Math.E)));
};
P.dsr = function (sr, n, N, g1, g2) { var sr0 = P.expectedMaxSharpe(N, 1 / Math.sqrt(Math.max(n, 1))); return { sr0: sr0, dsr: P.psr(sr, n, sr0, g1, g2) }; };
P.minTRL = function (sr, sr0, g1, g2, conf) {
  sr0 = sr0 || 0; conf = conf || 0.95; if (!(sr > sr0)) return Infinity;
  var v = Math.max(0, P.psrVar(sr, g1, g2)), z = S.normPpf(conf);
  return 1 + v * Math.pow(z / (sr - sr0), 2);
};
/* Le mur d’échantillon d’ALP nº 3 (alp1/costs.py, trades_for_significance) : N = ⌈((z₁₋α + z_puissance)/SR)²⌉. */
P.decisionsPourSharpe = function (sr, alpha, power) {
  alpha = alpha == null ? 0.05 : alpha; power = power == null ? 0.8 : power;
  if (!(sr > 0)) return Infinity;
  return Math.ceil(Math.pow((S.normPpf(1 - alpha) + S.normPpf(power)) / sr, 2));
};
P.MUR = { sharpe: 0.10, decisions: 619, source: 'ALP nº 3, partie VIII, table 14 : route 1, test t unilatéral à 5 %, puissance 80 %' };
/* Lois nulles simples. */
P.mddNull = function (sd, n) { return Math.sqrt(Math.PI / 2) * sd * Math.sqrt(n); };
P.longestRunNull = function (n, q) { if (!(q > 0 && q < 1) || !(n >= 1)) return NaN; return Math.log(n * (1 - q)) / Math.log(1 / q); };

/* =====================================================================
   2. Temps, agrégations, séries glissantes
   ===================================================================== */
var DTF = {};
P.parts = function (tz, t) {
  var f = DTF[tz];
  if (!f) { try { f = DTF[tz] = new Intl.DateTimeFormat('en-GB', { timeZone: tz, hour12: false, weekday: 'short', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }); } catch (e) { return T.time.parts(tz, new Date(t)); } }
  var o = {}; f.formatToParts(new Date(t)).forEach(function (p) { o[p.type] = p.value; });
  return { y: +o.year, mo: +o.month, d: +o.day, h: +o.hour % 24, m: +o.minute, wd: { Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6, Sun: 0 }[o.weekday] };
};
/* Instant (ms) d’une heure civile donnée dans un fuseau. */
P.zoned = function (y, mo, d, hh, mm, tz) {
  var guess = Date.UTC(y, mo - 1, d, hh, mm), p = P.parts(tz, guess);
  var seen = Date.UTC(p.y, p.mo - 1, p.d, p.h, p.m);
  return guess - (seen - guess);
};
function dayKey(p) { return p.y + '-' + String(p.mo).padStart(2, '0') + '-' + String(p.d).padStart(2, '0'); }
P.daily = function (trades, tz) {
  var by = {}, out = [];
  trades.forEach(function (t) {
    if (!fin(t.at)) return; var p = P.parts(tz, t.at), k = dayKey(p);
    if (!by[k]) { by[k] = { key: k, y: p.y, mo: p.mo, d: p.d, wd: p.wd, pnl: 0, n: 0 }; out.push(by[k]); }
    by[k].pnl += t.pnl; by[k].n++;
  });
  return out.sort(function (a, b) { return a.key < b.key ? -1 : a.key > b.key ? 1 : 0; });
};
P.hourWeek = function (trades, tz) {
  var cells = {}, hours = {}, wds = {};
  trades.forEach(function (t) {
    if (!fin(t.at)) return; var p = P.parts(tz, t.at), k = p.h + ':' + p.wd;
    hours[p.h] = 1; wds[p.wd] = 1; var c = cells[k] || (cells[k] = { s: 0, n: 0 }); c.s += t.pnl; c.n++;
  });
  var H = Object.keys(hours).map(Number).sort(function (a, b) { return a - b; });
  var order = [1, 2, 3, 4, 5, 6, 0], W = order.filter(function (d) { return wds[d] || d <= 5 && d >= 1; });
  return {
    hours: H, wds: W,
    mean: H.map(function (hh) { return W.map(function (d) { var c = cells[hh + ':' + d]; return c ? c.s / c.n : NaN; }); }),
    count: H.map(function (hh) { return W.map(function (d) { var c = cells[hh + ':' + d]; return c ? c.n : NaN; }); })
  };
};
P.rolling = function (x, w) {
  var out = []; w = Math.max(3, Math.round(w));
  for (var i = w; i <= x.length; i++) { var s = x.slice(i - w, i); out.push({ i: i, sharpe: P.sharpe(s), sortino: P.sortino(s, 0) }); }
  return out;
};
/* Diagramme quantile-quantile : positions de Blom. */
P.qq = function (x) {
  var v = S.sorted(x), n = v.length;
  return v.map(function (y, i) { return [S.normPpf((i + 1 - 0.375) / (n + 0.25)), y]; });
};
P.QLEVELS = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99];
P.quantileTable = function (x) {
  var v = S.sorted(x), m = S.mean(x), s = S.sd(x);
  return P.QLEVELS.map(function (q) { var o = S.quantile(v, q), g = m + s * S.normPpf(q); return { q: q, obs: o, norm: g, gap: o - g }; });
};

/* =====================================================================
   3. Sources : journal, dernier backtest, collage, simulation
   ===================================================================== */
P.fromJournal = function (rows, risk) {
  return rows.filter(function (r) { return r.kind === 'pris' && r.status === 'clos' && fin(r.pnl); })
    .map(function (r) { return { at: fin(r.closedAt) ? r.closedAt : r.at, pnl: r.pnl, r: fin(r.r) ? r.r : r.pnl / risk }; })
    .sort(function (a, b) { return (a.at || 0) - (b.at || 0); });
};
P.fromBacktest = function (bt, risk) {
  if (!bt || !Array.isArray(bt.trades)) return [];
  return bt.trades.filter(function (t) { return t && (fin(t.pnl) || fin(t.r)); })
    .map(function (t) { var pnl = fin(t.pnl) ? t.pnl : t.r * risk; return { at: fin(t.at) ? t.at : null, pnl: pnl, r: fin(t.r) ? t.r : pnl / risk }; });
};
/* Nombre : virgule ou point décimal, séparateurs de milliers, signe moins typographique,
   parenthèses comptables, symboles $ € R. */
P.parseNum = function (s) {
  s = String(s == null ? '' : s).trim(); if (!s) return NaN;
  var neg = /^\(.*\)$/.test(s); if (neg) s = s.slice(1, -1);
  s = s.replace(/[\s  $€]/g, '').replace(/R$/i, '').replace(/[−–]/g, '-');
  if (s.indexOf(',') >= 0 && s.indexOf('.') >= 0) { if (s.lastIndexOf(',') > s.lastIndexOf('.')) s = s.replace(/\./g, '').replace(',', '.'); else s = s.replace(/,/g, ''); }
  else s = s.replace(',', '.');
  if (!/^[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?$/i.test(s)) return NaN;
  var v = parseFloat(s); return isFinite(v) ? (neg ? -v : v) : NaN;
};
/* Date : 2026-09-14[ 15:42], 14/09/2026[ 15:42], 2026/09/14. Rend {t, time} ou null. */
P.parseDate = function (s, tz) {
  s = String(s || '').trim(); var m, y, mo, d, hh = 0, mi = 0, time = false;
  if ((m = /^(\d{4})[-\/.](\d{1,2})[-\/.](\d{1,2})(?:[ T](\d{1,2}):(\d{2})(?::\d{2}(?:\.\d+)?)?)?/.exec(s))) { y = +m[1]; mo = +m[2]; d = +m[3]; if (m[4] != null) { hh = +m[4]; mi = +m[5]; time = true; } }
  else if ((m = /^(\d{1,2})[\/.-](\d{1,2})[\/.-](\d{4})(?:[ T](\d{1,2}):(\d{2})(?::\d{2})?)?/.exec(s))) { d = +m[1]; mo = +m[2]; y = +m[3]; if (m[4] != null) { hh = +m[4]; mi = +m[5]; time = true; } }
  else return null;
  if (mo < 1 || mo > 12 || d < 1 || d > 31 || hh > 23 || mi > 59) return null;
  return { t: tz ? P.zoned(y, mo, d, hh, mi, tz) : Date.UTC(y, mo - 1, d, hh, mi), time: time };
};
P.parseCsv = function (text, unit, risk, tz) {
  var lines = String(text || '').split(/\r?\n/), trades = [], skipped = [], dated = 0, timed = 0, seen = 0;
  lines.forEach(function (raw, i) {
    var line = raw.trim(); if (!line || line[0] === '#') return;
    seen++;
    var parts;
    if (line.indexOf(';') >= 0) parts = line.split(';');
    else if (line.indexOf('\t') >= 0) parts = line.split('\t');
    else { var mm = /^(.+?)\s*,\s*([^,]+)$/.exec(line); parts = mm && P.parseDate(mm[1]) ? [mm[1], mm[2]] : [line]; }
    parts = parts.map(function (q) { return q.trim(); }).filter(function (q) { return q !== ''; });
    /* la valeur : le dernier champ numérique ; une première ligne sans nombre est un en-tête */
    var vi = -1, v = NaN;
    for (var k = parts.length - 1; k >= 0; k--) { var x = P.parseNum(parts[k]); if (fin(x)) { v = x; vi = k; break; } }
    if (vi < 0) { if (!(seen === 1 && /[a-zà-ÿ]/i.test(line))) skipped.push({ line: i + 1, text: line.slice(0, 40) }); return; }
    var dt = null, hm = null;
    for (var j = 0; j < parts.length; j++) {
      if (j === vi) continue;
      var d = P.parseDate(parts[j], tz);
      if (d && !dt) dt = { s: parts[j], d: d };
      else if (!hm) { var tm = /^(\d{1,2}):(\d{2})/.exec(parts[j]); if (tm) hm = tm[1].padStart(2, '0') + ':' + tm[2]; }
    }
    if (dt && !dt.d.time && hm) dt.d = P.parseDate(dt.s.split(/[ T]/)[0] + ' ' + hm, tz) || dt.d;
    if (dt) { dated++; if (dt.d.time) timed++; }
    trades.push({ at: dt ? dt.d.t : null, pnl: unit === 'r' ? v * risk : v, r: unit === 'r' ? v : v / risk });
  });
  var allDated = trades.length > 0 && dated === trades.length;
  if (allDated) trades.sort(function (a, b) { return a.at - b.at; });
  else trades.forEach(function (t) { t.at = null; });
  return { trades: trades, skipped: skipped, hasDates: allDated, hasTimes: allDated && timed === trades.length };
};
/* Tirages simulés : issue binaire (+b R ou −1 R) avec bruit d’exécution gaussien, coût déduit.
   Les dates sont des jours ouvrés finissant à `end`, heures dans la fenêtre [from, to[. */
P.simulate = function (o) {
  o = Object.assign({ p: 0.4, b: 1.5, n: 250, seed: 42, noise: 0.15, cost: 0, risk: 150, tpd: 2, end: Date.UTC(2026, 0, 2), from: 9, to: 17, tz: 'UTC' }, o || {});
  var n = Math.max(0, Math.min(20000, Math.round(o.n))), rnd = T.rng(o.seed), rt = T.rng((o.seed ^ 0x5bd1e995) >>> 0), out = [];
  var spare = null;
  function gauss() { if (spare != null) { var s = spare; spare = null; return s; } var u1 = Math.max(rnd(), 1e-300), u2 = rnd(), r = Math.sqrt(-2 * Math.log(u1)); spare = r * Math.sin(2 * Math.PI * u2); return r * Math.cos(2 * Math.PI * u2); }
  var tpd = Math.max(1, Math.round(o.tpd)), nDays = Math.ceil(n / tpd), days = [];
  var e = P.parts(o.tz, o.end), cur = Date.UTC(e.y, e.mo - 1, e.d);
  while (days.length < nDays) { var wd = new Date(cur).getUTCDay(); if (wd !== 0 && wd !== 6) days.unshift(cur); cur -= 864e5; }
  var from = o.from, to = o.to > o.from ? o.to : o.from + 8;
  for (var i = 0; i < n; i++) {
    var win = rnd() < o.p, rr = (win ? o.b : -1) + (o.noise > 0 ? o.noise * gauss() : 0);
    var pnl = rr * o.risk - o.cost, dd = new Date(days[Math.floor(i / tpd)]);
    var minute = Math.floor(rt() * (to - from) * 60), at = P.zoned(dd.getUTCFullYear(), dd.getUTCMonth() + 1, dd.getUTCDate(), from + Math.floor(minute / 60), minute % 60, o.tz);
    out.push({ at: at, pnl: pnl, r: pnl / o.risk });
  }
  return out.sort(function (a, b) { return a.at - b.at; });
};

/* =====================================================================
   4. La feuille de score
   ===================================================================== */
P.metrics = function (trades, o) {
  o = Object.assign({ tpd: 2, days: 252, capital: 50000, risk: 150, trials: 10, tz: 'Europe/Paris' }, o || {});
  var x = trades.map(function (t) { return t.pnl; }), r = trades.map(function (t) { return t.r; }), n = x.length, M = { n: n, opt: o };
  if (!n) return M;
  var mo = P.moments(x), sorted = S.sorted(x), nYear = o.tpd * o.days;
  M.nYear = nYear; M.mean = mo.mean; M.sd = mo.sd; M.skew = mo.skew; M.exKurt = mo.exKurt; M.net = sum(x);
  M.first = trades[0].at; M.last = trades[n - 1].at;
  M.sharpe = P.sharpe(x); M.sharpeAnn = M.sharpe * Math.sqrt(nYear);
  M.downDev = P.downsideDev(x, 0); M.sortino = P.sortino(x, 0); M.sortinoAnn = M.sortino * Math.sqrt(nYear);
  M.omega0 = P.omega(x, 0); M.omega1R = P.omega(x, o.risk);
  M.pf = P.profitFactor(x); M.payoff = P.payoff(x); M.winRate = P.winRate(x);
  M.wins = x.filter(function (v) { return v > 0; }).length; M.losses = x.filter(function (v) { return v < 0; }).length;
  M.wilson = P.wilson(M.wins, n); M.pEq = fin(M.payoff) ? 1 / (1 + M.payoff) : NaN;
  M.kelly = P.kelly(M.winRate, M.payoff); M.halfKelly = M.kelly / 2;
  M.expR = S.mean(r); M.sdR = S.sd(r); M.sqn = n > 1 && M.sdR > 0 ? Math.sqrt(Math.min(n, 100)) * M.expR / M.sdR : NaN;
  M.tstat = M.sd > 0 ? M.mean / (M.sd / Math.sqrt(n)) : NaN;
  M.tail = P.tailRatio(sorted); M.csr = M.tail * M.pf;
  M.var95h = P.varHist(sorted, 0.05); M.var99h = P.varHist(sorted, 0.01);
  M.var95g = P.varGauss(M.mean, M.sd, 0.05); M.var99g = P.varGauss(M.mean, M.sd, 0.01);
  M.var95cf = P.varCF(M.mean, M.sd, M.skew, M.exKurt, 0.05); M.var99cf = P.varCF(M.mean, M.sd, M.skew, M.exKurt, 0.01);
  M.cfOk = !(M.var99cf < M.var95cf);
  M.cvar95h = P.cvarHist(sorted, 0.05); M.cvar95g = P.cvarGauss(M.mean, M.sd, 0.05);
  var D = P.drawdowns(x, o.capital); M.D = D; M.maxDD = D.max; M.maxDDpct = D.maxPct; M.longest = D.longest; M.nEpisodes = D.episodes.length;
  M.longestDays = NaN;
  if (fin(M.first)) {
    D.episodes.forEach(function (e) {
      var a = trades[Math.max(0, e.start - 1)].at, b = trades[(e.end == null ? n : e.end) - 1].at;
      if (fin(a) && fin(b)) { var dd = (b - a) / 864e5; if (!(dd <= M.longestDays)) M.longestDays = dd; }
    });
  }
  M.recovery = D.max > 0 ? M.net / D.max : (M.net > 0 ? Infinity : NaN);
  M.annRet = M.mean * nYear / o.capital; M.years = n / nYear;
  var endCap = o.capital + M.net; M.cagr = endCap > 0 ? Math.pow(endCap / o.capital, 1 / M.years) - 1 : -1;
  M.calmar = D.maxPct > 0 ? M.annRet / D.maxPct : (M.annRet > 0 ? Infinity : NaN);
  M.mar = D.maxPct > 0 ? M.cagr / D.maxPct : (M.cagr > 0 ? Infinity : NaN);
  M.ulcer = P.ulcer(D.ddPct); M.martin = M.ulcer > 0 ? M.annRet / M.ulcer : (M.annRet > 0 ? Infinity : NaN);
  var deps = D.episodes.map(function (e) { return e.depthPct; }).sort(function (a, b) { return b - a; }), k = Math.min(5, deps.length);
  M.sterlingK = k;
  M.sterling = k ? M.annRet / (sum(deps.slice(0, k)) / k) : (M.annRet > 0 ? Infinity : NaN);
  M.burke = deps.length ? M.annRet / Math.sqrt(sum(deps.map(function (d) { return d * d; }))) : (M.annRet > 0 ? Infinity : NaN);
  var days = P.daily(trades, o.tz); M.daysN = days.length;
  if (days.length) { var dv = days.map(function (d) { return d.pnl; }), neg = -sum(dv.filter(function (v) { return v < 0; })); M.gpr = neg > 0 ? sum(dv) / neg : (sum(dv) > 0 ? Infinity : NaN); M.gprBasis = 'jours'; }
  else { M.gpr = M.pf - 1; M.gprBasis = 'trades'; }
  M.streaks = P.streaks(x); M.runNullLoss = P.longestRunNull(n, 1 - M.winRate); M.runNullWin = P.longestRunNull(n, M.winRate);
  M.rho1 = P.autocorr1(x); M.runs = P.runsTest(x);
  M.psr = P.psr(M.sharpe, n, 0, M.skew, M.exKurt);
  var ds = P.dsr(M.sharpe, n, o.trials, M.skew, M.exKurt); M.sr0 = ds.sr0; M.dsr = ds.dsr;
  M.minTRL = P.minTRL(M.sharpe, 0, M.skew, M.exKurt, 0.95);
  M.mddNull = P.mddNull(M.sd, n);
  M.needed = P.decisionsPourSharpe(M.sharpe);
  return M;
};

function usd(v, signed) { if (!fin(v)) return F.num(v); var a = Math.abs(v); return F.usd(v, a > 0 && a < 10 ? 2 : 0, signed); }
function nb(v, nd) { return F.num(v, nd == null ? 2 : nd); }
function verdictOf(z, thr) { if (!fin(z)) return null; return z > thr ? 'hors' : z < -thr ? 'contre' : 'bruit'; }
/* Pour une mesure de forme, l’écart à la loi nulle n’a pas de sens favorable : seulement « hors du bruit ». */
function verdictAbs(z, thr) { if (!fin(z)) return null; return Math.abs(z) > thr ? 'hors' : 'bruit'; }
P.usd = usd;

/* La feuille, groupée. Chaque ligne : nom, valeur, lecture, définition exacte, loi nulle, verdict. */
P.score = function (M) {
  var o = M.opt, n = M.n, rt = Math.sqrt(n), z1 = S.normPpf(0.95), z2 = S.normPpf(0.975), N = M.nYear;
  function row(k, name, v, read, def, nul, verdict) { return { k: k, name: name, v: v, read: read, def: def, nul: nul || null, verdict: verdict || null }; }
  var tpdTxt = nb(o.tpd, o.tpd % 1 ? 1 : 0);
  var shortSpan = M.years < 0.5 ? ' Sur moins de six mois de trades, la composition gonfle ce nombre : lis-le avec prudence.' : '';
  var A = [
    row('sharpe', 'Sharpe par trade', nb(M.sharpe, 3),
      M.sharpe > 0 ? 'L’espérance d’un trade, en écarts-types. À ce niveau, il faut environ ' + F.int(M.needed) + ' trades pour le distinguer de zéro (tu en as ' + F.int(n) + ').' : 'Nul ou négatif : aucun nombre de trades ne le rendra significativement positif.',
      'SR = moyenne(x) / écart-type(x), x = P&L net de chaque trade, écart-type à n − 1. Aucun taux sans risque : un trade intrajournalier n’immobilise pas de capital.',
      'Sans avantage, ŜR suit à peu près une normale centrée d’écart-type 1/√n = ' + nb(1 / rt, 3) + ' : il ne dépasse 1,645/√n = ' + nb(z1 / rt, 3) + ' qu’une fois sur vingt.',
      verdictOf(M.sharpe * rt, z1)),
    row('sharpeAnn', 'Sharpe annualisé', nb(M.sharpeAnn, 2),
      'Le même nombre, multiplié par √' + F.int(N) + ' (trades par an déclarés). Une convention d’affichage : il n’ajoute aucune information.',
      'SR_an = SR × √(trades par jour × jours par an) = SR × √(' + tpdTxt + ' × ' + F.int(o.days) + ').',
      'Seuil du bruit, annualisé : 1,645 × √(' + F.int(N) + ' / n) = ' + nb(z1 * Math.sqrt(N / n), 2) + '.',
      verdictOf(M.sharpe * rt, z1)),
    row('psr', 'Sharpe probabiliste (PSR)', F.pct(M.psr, 1),
      'Probabilité que le vrai Sharpe soit positif, compte tenu du nombre de trades, de l’asymétrie et du kurtosis.',
      'PSR = Φ( (ŜR − SR*) · √(n − 1) / √(1 − γ₁·ŜR + (γ₂ + 2)/4 · ŜR²) ), SR* = 0, γ₁ asymétrie, γ₂ kurtosis en excès (Bailey et López de Prado, 2012).',
      'Un Sharpe se déclare positif au-delà de 95 %.',
      fin(M.psr) ? (M.psr >= 0.95 ? 'hors' : M.psr <= 0.05 ? 'contre' : 'bruit') : null),
    row('dsr', 'Sharpe déflaté (DSR)', F.pct(M.dsr, 1),
      'Le PSR mesuré contre le meilleur Sharpe que ' + F.int(o.trials) + ' variantes sans avantage auraient produit : ' + nb(M.sr0, 3) + ' par trade.',
      'DSR = PSR(SR₀), SR₀ = (1/√n) · [ (1 − γ)·Φ⁻¹(1 − 1/N) + γ·Φ⁻¹(1 − 1/(N·e)) ], γ = 0,5772 (Euler-Mascheroni), N = nombre de variantes essayées, réglable dans l’onglet Robustesse.',
      'Au-dessous de 95 %, la sélection seule explique le résultat.',
      fin(M.dsr) ? (M.dsr >= 0.95 ? 'hors' : 'bruit') : null),
    row('minTRL', 'Durée minimale de track record', fin(M.minTRL) ? F.int(Math.ceil(M.minTRL)) + ' trades' : '∞',
      fin(M.minTRL) ? 'Trades nécessaires pour déclarer ce Sharpe positif à 95 %, forme de la loi comprise ; tu en as ' + F.int(n) + '.' : 'Infinie : un Sharpe nul ou négatif ne se déclare jamais positif.',
      'MinTRL = 1 + (1 − γ₁·ŜR + (γ₂ + 2)/4 · ŜR²) · (z₀,₉₅ / ŜR)², z₀,₉₅ = 1,645 (Bailey et López de Prado).',
      'Tant que n reste sous le MinTRL, le Sharpe observé ne se distingue pas de zéro.',
      fin(M.minTRL) ? (n >= M.minTRL ? 'hors' : 'bruit') : 'bruit'),
    row('sortino', 'Sortino (MAR = 0)', nb(M.sortino, 3),
      'Comme le Sharpe, mais seul ce qui tombe sous zéro compte comme risque. Annualisé : ' + nb(M.sortinoAnn, 2) + '.',
      'Sortino = (moyenne − MAR) / DD, DD = √( Σ min(0, xᵢ − MAR)² / N ), N = nombre total de trades et non le seul nombre de pertes, MAR = 0. Annualisé : × √(trades par an).',
      'À espérance nulle il vaut 0 en moyenne ; pas de loi fermée, le bootstrap de l’onglet Robustesse en tient lieu.'),
    row('calmar', 'Calmar', nb(M.calmar, 2),
      'Rendement annualisé pour chaque point de pire creux.' + shortSpan,
      'Calmar = rendement annualisé / drawdown maximal (% du pic). Rendement annualisé = moyenne × trades par an / capital de référence = ' + F.pct(M.annRet, 1) + '. Sur tout l’échantillon ; la convention d’origine prend 36 mois.'),
    row('mar', 'MAR', nb(M.mar, 2),
      'Comme le Calmar, avec la croissance composée depuis le premier trade.' + shortSpan,
      'MAR = TCAC / drawdown maximal (%), TCAC = (capital final / capital de référence)^(1/années) − 1 = ' + F.pct(M.cagr, 1) + ', années = n / trades par an = ' + nb(M.years, 2) + '.'),
    row('omega', 'Omega (seuil 0)', nb(M.omega0, 2),
      'Somme des gains sur somme des pertes, au seuil zéro. Au-dessus de 1, les gains l’emportent.',
      'Ω(L) = Σ max(xᵢ − L, 0) / Σ max(L − xᵢ, 0). À L = 0 il coïncide exactement avec le facteur de profit ; il s’en sépare dès que L bouge : Ω(1 R) = ' + nb(M.omega1R, 2) + '.',
      'À espérance nulle, Ω(0) = 1 exactement.'),
    row('ulcer', 'Ulcer Index', F.pct(M.ulcer, 2),
      'Profondeur et durée des creux en un seul nombre : un creux long pèse autant qu’un creux profond.',
      'UI = √( (1/n) · Σ Dᵢ² ), Dᵢ = (pic − capitalᵢ) / pic après chaque trade, capital de départ = capital de référence.'),
    row('martin', 'Ratio de Martin (UPI)', nb(M.martin, 2),
      'Rendement annualisé par point d’Ulcer.',
      'UPI = rendement annualisé / UI (Martin, 1987), sans taux sans risque.'),
    row('sterling', 'Sterling', nb(M.sterling, 2),
      M.sterlingK ? 'Rendement annualisé sur la moyenne des ' + F.int(M.sterlingK) + ' plus profonds creux.' : 'Aucun creux : le ratio est infini.',
      'Sterling = rendement annualisé / moyenne des k plus profonds épisodes de drawdown, k = min(5, épisodes). Variante de Bacon (2008), sans la décote arbitraire de 10 %.'),
    row('burke', 'Burke', nb(M.burke, 2),
      'Comme le Sterling, mais un creux profond pèse plus que plusieurs petits.',
      'Burke = rendement annualisé / √( Σ Dⱼ² ), Dⱼ = profondeur de chaque épisode de drawdown, en % du pic.')
  ];
  var span = fin(M.first) && fin(M.last) ? ' du ' + F.dateLong(M.first) + ' au ' + F.dateLong(M.last) : '';
  var wl = M.wilson, eqTxt = !fin(M.pEq) ? 'Sans gain ou sans perte, le taux d’équilibre n’est pas défini.' : 'Taux d’équilibre à ton payoff : 1/(1 + b) = ' + F.pct(M.pEq, 1) + '. ' + (wl.lo > M.pEq ? 'L’intervalle est entièrement au-dessus : ton taux bat l’équilibre.' : wl.hi < M.pEq ? 'L’intervalle est entièrement au-dessous de l’équilibre.' : 'L’intervalle le contient : ton taux est indiscernable de l’équilibre.');
  var B = [
    row('net', 'Profit net', usd(M.net, true), F.int(n) + ' trade' + (n > 1 ? 's' : '') + span + '.', 'Σ xᵢ, nets de commission.'),
    row('expUsd', 'Espérance par trade', usd(M.mean, true), 'Ce que rapporte un trade moyen, net de commission.',
      'E = Σ xᵢ / n.', 't = E / (s/√n) = ' + nb(M.tstat, 2) + ' ; il faut t > 1,645 pour sortir du bruit à 5 % (unilatéral).', verdictOf(M.tstat, z1)),
    row('expR', 'Espérance en R', F.r(M.expR, 3), 'En multiples du risque initial, 1 R = ' + usd(o.risk) + ' (réglages).',
      'E_R = moyenne des résultats en R : le champ r de chaque trade, ou P&L / risque par trade s’il manque.'),
    row('pf', 'Facteur de profit', nb(M.pf, 2), 'Dollars gagnés pour un dollar perdu.', 'PF = Σ gains / |Σ pertes|.', 'À espérance nulle, PF = 1.'),
    row('payoff', 'Payoff ratio', nb(M.payoff, 2), 'Gain moyen sur perte moyenne. Il ne se lit qu’avec le taux de réussite.',
      'b = moyenne des gains / |moyenne des pertes|.', fin(M.pEq) ? 'Taux de réussite d’équilibre à ce payoff : 1/(1 + b) = ' + F.pct(M.pEq, 1) + '.' : null),
    row('win', 'Taux de réussite', F.pct(M.winRate, 1),
      'Intervalle de Wilson à 95 % : ' + F.pct(wl.lo, 1) + ' à ' + F.pct(wl.hi, 1) + ', la fourchette où se trouve probablement le vrai taux.',
      'p̂ = gagnants / n. Wilson : (p̂ + z²/2n ± z·√(p̂(1 − p̂)/n + z²/4n²)) / (1 + z²/n), z = 1,96. Un trade nul n’est ni gagnant ni perdant.',
      eqTxt, fin(M.pEq) ? (wl.lo > M.pEq ? 'hors' : wl.hi < M.pEq ? 'contre' : 'bruit') : null),
    row('sqn', 'SQN (Van Tharp)', nb(M.sqn, 2), 'Le t de Student de tes R, plafonné à 100 trades.',
      'SQN = √min(n, 100) × moyenne(R) / écart-type(R). Van Tharp plafonne n à 100 pour comparer des systèmes de fréquences différentes.',
      'Sans avantage, il tombe entre −1,96 et 1,96 dans 95 % des cas.', verdictOf(M.sqn, z2)),
    row('kelly', 'Kelly', F.pct(M.kelly, 1),
      (M.kelly > 0 ? 'La fraction du capital à risquer par trade qui maximise la croissance, si tes p et b étaient les vrais.' : 'Négatif : à ces p et b, toute mise réduit la croissance attendue ; la seule fraction optimale est zéro.') + ' Ton risque déclaré vaut ' + F.pct(o.risk / o.capital, 2) + ' du capital de référence.',
      'f* = p − (1 − p)/b, p = taux de réussite, b = payoff ratio.',
      'À l’équilibre, f* = 0. Estimé sur peu de trades, il surestime presque toujours : d’où le demi-Kelly.'),
    row('halfKelly', 'Demi-Kelly', F.pct(M.halfKelly, 1), 'La moitié de f* : environ trois quarts de la croissance optimale pour la moitié de la volatilité.',
      'f*/2. Au second ordre, g(f*/2) = ¾ · g(f*).'),
    row('gpr', 'Gain-to-pain (Schwager)', nb(M.gpr, 2),
      M.gprBasis === 'jours' ? 'Somme des P&L journaliers sur la somme de leurs pertes, sur ' + F.int(M.daysN) + ' jours.' : 'Sans dates, calculé sur les trades : il vaut alors exactement PF − 1.',
      'GPR = Σ P&L des périodes / |Σ P&L des périodes négatives|. Schwager l’écrit sur des mois ; un journal court prend les jours.',
      'À espérance nulle, 0.')
  ];
  var cfWarn = M.cfOk ? '' : ' Ici la VaR 99 % Cornish-Fisher passe sous la VaR 95 % : la correction sort de son domaine de validité (loi trop éloignée de la normale), ne t’y fie pas.';
  var Cq = [
    row('skew', 'Asymétrie', nb(M.skew, 2), 'Positive : des gains rares et grands. Négative : des pertes rares et grandes, le profil d’un vendeur d’options.',
      'γ₁ = m₃ / m₂^(3/2), moments centrés de population.', 'Sous la normale, écart-type ≈ √(6/n) = ' + nb(Math.sqrt(6 / n), 2) + '.', verdictAbs(M.skew / Math.sqrt(6 / n), z2)),
    row('kurt', 'Kurtosis en excès', nb(M.exKurt, 2), 'Au-dessus de 0 : plus de résultats extrêmes que la normale n’en prévoit.',
      'γ₂ = m₄ / m₂² − 3.', 'Sous la normale, écart-type ≈ √(24/n) = ' + nb(Math.sqrt(24 / n), 2) + '.', verdictAbs(M.exKurt / Math.sqrt(24 / n), z2)),
    row('tail', 'Tail ratio', nb(M.tail, 2), 'Le 95ᵉ centile sur le 5ᵉ, en valeur absolue : la queue des gains contre celle des pertes.',
      'TR = |q₉₅| / |q₅|, quantiles empiriques interpolés.', 'Pour une loi symétrique autour de zéro, 1.'),
    row('csr', 'Common sense ratio', nb(M.csr, 2), 'Tail ratio × facteur de profit (Bernut). Au-dessus de 1, les queues travaillent pour toi.', 'CSR = TR × PF.'),
    row('var95h', 'VaR 95 % historique', usd(M.var95h), 'La perte qu’un trade sur vingt dépasse, lue dans tes propres trades.', 'VaR₉₅ = −q₅, quantile empirique interpolé.'),
    row('var95g', 'VaR 95 % gaussienne', usd(M.var95g), 'La même, si tes résultats suivaient une normale de même moyenne et écart-type.', 'VaR = −(µ + σ·z₀,₀₅), z₀,₀₅ = −1,645.'),
    row('var95cf', 'VaR 95 % Cornish-Fisher', usd(M.var95cf), 'La VaR gaussienne corrigée par l’asymétrie et le kurtosis.',
      'z_cf = z + (z² − 1)·γ₁/6 + (z³ − 3z)·γ₂/24 − (2z³ − 5z)·γ₁²/36 ; VaR = −(µ + σ·z_cf).'),
    row('var99h', 'VaR 99 % historique', usd(M.var99h), 'La perte qu’un trade sur cent dépasse. Sous cent trades, c’est presque ta pire perte.', 'VaR₉₉ = −q₁.'),
    row('var99g', 'VaR 99 % gaussienne', usd(M.var99g), 'Sous la normale de même moyenne et écart-type.', 'VaR = −(µ + σ·z₀,₀₁), z₀,₀₁ = −2,326.'),
    row('var99cf', 'VaR 99 % Cornish-Fisher', usd(M.var99cf), 'Corrigée par l’asymétrie et le kurtosis.' + cfWarn, 'Même développement qu’à 95 %, z = −2,326.'),
    row('cvar95', 'CVaR 95 % (expected shortfall)', usd(M.cvar95h), 'La perte moyenne quand on est dans les 5 % pires trades.',
      'ES₉₅ = −moyenne des xᵢ ≤ q₅ (historique). Version gaussienne : −(µ − σ·φ(z₀,₀₅)/0,05) = ' + usd(M.cvar95g) + '.')
  ];
  var nullDD = 'Sans avantage et à même volatilité, on attend ≈ √(π/2)·σ·√n = ' + usd(M.mddNull) + ' (Magdon-Ismail et coll., 2004) : ' + (M.maxDD < M.mddNull ? 'ton creux est moins profond que celui du hasard.' : 'ton creux est au moins aussi profond que celui du hasard.');
  var Dd = [
    row('maxDD', 'Drawdown maximal', usd(M.maxDD), 'Le pire recul depuis un sommet du capital.', 'MDD = maxₜ (picₜ − capitalₜ), pic = plus haut atteint depuis le début, capital de départ compris.', nullDD),
    row('maxDDpct', 'Drawdown maximal (%)', F.pct(M.maxDDpct, 2), 'En % du pic, sur un capital de référence de ' + usd(o.capital) + '.', 'MDD% = maxₜ (picₜ − capitalₜ) / picₜ.'),
    row('longest', 'Plus longue durée sous l’eau', F.int(M.longest) + ' trade' + (M.longest > 1 ? 's' : ''),
      'La plus longue attente entre un sommet et son retour' + (fin(M.longestDays) ? ' ; en temps, le plus long creux a duré ' + F.int(Math.round(M.longestDays)) + ' jour' + (Math.round(M.longestDays) > 1 ? 's' : '') + ' calendaires.' : '.'),
      'Nombre de trades entre un pic et le premier retour à ce pic, ou la fin de l’échantillon si le creux n’est pas refermé.'),
    row('recovery', 'Facteur de récupération', nb(M.recovery, 2), 'Combien de fois le profit net couvre le pire creux.', 'RF = profit net / drawdown maximal ($).')
  ];
  var R = M.runs;
  var E = [
    row('streaks', 'Plus longues séries (gains / pertes)', F.int(M.streaks.win) + ' / ' + F.int(M.streaks.loss),
      fin(M.runNullLoss) ? 'Au hasard, à ton taux de réussite, la plus longue série de pertes attendue sur ' + F.int(n) + ' trades est d’environ ' + nb(M.runNullLoss, 1) + '.' : 'Nombre maximal de trades consécutifs de même signe.',
      'Nombre maximal de trades consécutifs de même signe ; un trade nul interrompt les deux.',
      'Plus longue série attendue : log₁/q (n·(1 − q)), q = probabilité de l’issue (Schilling, 1990). Gains : ' + nb(M.runNullWin, 1) + ', pertes : ' + nb(M.runNullLoss, 1) + '.'),
    row('rho1', 'Autocorrélation d’ordre 1', nb(M.rho1, 3), 'Un gain annonce-t-il un gain ? Positive : les résultats se suivent ; négative : ils alternent.',
      'ρ₁ = Σ (xₜ − x̄)(xₜ₊₁ − x̄) / Σ (xₜ − x̄)².', 'Sans dépendance, |ρ₁| < 1,96/√n = ' + nb(z2 / rt, 3) + ' dans 95 % des cas.',
      fin(M.rho1) ? (Math.abs(M.rho1) > z2 / rt ? 'hors' : 'bruit') : null),
    row('runs', 'Test des suites (Wald-Wolfowitz)', fin(R.z) ? 'z = ' + nb(R.z, 2) : '—',
      fin(R.z) ? F.int(R.runs) + ' suites observées pour ' + nb(R.mu, 1) + ' attendues au hasard : ' + (R.runs < R.mu ? 'un peu moins, donc gains et pertes tendent à se grouper' : R.runs > R.mu ? 'un peu plus, donc gains et pertes tendent à alterner' : 'exactement le hasard') + (Math.abs(R.z) > z2 ? ', au-delà du bruit.' : ', sans sortir du bruit.') : 'Il faut au moins un gain et une perte.',
      'n₁ gains, n₂ pertes (nuls exclus), R suites. µ = 2n₁n₂/n + 1, σ² = 2n₁n₂(2n₁n₂ − n) / (n²(n − 1)), z = (R − µ)/σ.',
      '|z| > 1,96 : l’ordre des gains et des pertes n’est pas aléatoire (z < 0 : groupés, z > 0 : alternés).',
      fin(R.z) ? (Math.abs(R.z) > z2 ? 'hors' : 'bruit') : null)
  ];
  return [
    { id: 'risque', title: 'Rendement ajusté au risque', rows: A },
    { id: 'gains', title: 'Gains et pertes', rows: B },
    { id: 'queues', title: 'Queues', rows: Cq },
    { id: 'dd', title: 'Drawdown', rows: Dd },
    { id: 'reg', title: 'Régularité', rows: E }
  ];
};

/* =====================================================================
   5. Espaces de paramètres — formes fermées, grilles pures
   ===================================================================== */
P.esperanceR = function (p, b, c) { return p * b - (1 - p) - (c || 0); };
P.seuilEquilibre = function (b, c) { return (1 + (c || 0)) / (1 + b); };
P.kellyGrowth = function (f, p, b) { if (f >= 1) return -Infinity; return p * Math.log(1 + f * b) + (1 - p) * Math.log(1 - f); };
P.kellyF = function (p, b) { return p - (1 - p) / b; };
/* Marche à dérive µ et variance σ² par trade : probabilité d’atteindre +B (objectif) avant −A (perte max).
   P = (1 − e^{−2µA/σ²}) / (1 − e^{−2µ(A+B)/σ²}) ; à dérive nulle, A/(A + B). */
P.pObjectif = function (mu, s2, A, B) {
  if (!(s2 > 0)) return mu > 0 ? 1 : mu < 0 ? 0 : A / (A + B);
  var k = 2 * mu / s2;
  if (Math.abs(k * (A + B)) < 1e-10) return A / (A + B);
  if (k > 0) return -Math.expm1(-k * A) / -Math.expm1(-k * (A + B));
  var u = -k; /* e^{−kA} énorme : forme stable */
  return Math.exp(-u * B) * (-Math.expm1(-u * A)) / (-Math.expm1(-u * (A + B)));
};
P.ruinMoments = function (p, b, risk, cost) { return { mu: risk * (p * b - (1 - p)) - (cost || 0), s2: p * (1 - p) * Math.pow((b + 1) * risk, 2) }; };
P.ruine = function (p, b, o) { var m = P.ruinMoments(p, b, o.risk, o.cost); return 1 - P.pObjectif(m.mu, m.s2, o.perteMax, o.objectif); };
P.sharpeAnnuel = function (p, b, c, nYear) { var sd = (b + 1) * Math.sqrt(p * (1 - p)); return sd > 0 ? P.esperanceR(p, b, c) / sd * Math.sqrt(nYear) : NaN; };
P.lin = function (a, b, n, centers) { var o = []; for (var i = 0; i < n; i++) o.push(centers ? a + (i + 0.5) * (b - a) / n : a + i * (b - a) / (n - 1)); return o; };
P.grille = function (fn, xs, ys) { return ys.map(function (y) { return xs.map(function (x) { return fn(x, y); }); }); };
P.SURF_KINDS = ['esperance', 'kelly', 'ruine', 'sharpe'];
/* o : { risk, cost ($), objectif ($), perteMax ($), nYear, bKelly } */
P.surfaceDef = function (kind, o) {
  var c = o.cost / o.risk, pdom = [0.2, 0.8], bdom = [0.5, 4];
  var be = function (n) { return P.lin(bdom[0], bdom[1], n || 60).map(function (b) { return [b, P.seuilEquilibre(b, c)]; }).filter(function (q) { return q[1] >= pdom[0] && q[1] <= pdom[1]; }); };
  var fpct = function (v) { return F.pct(v, 0); };
  if (kind === 'esperance') return {
    kind: kind, title: 'Espérance par trade', x: { name: 'R:R', dom: bdom, fmt: function (v) { return nb(v, 2); } }, y: { name: 'réussite', dom: pdom, fmt: fpct },
    z: { name: 'espérance', fmt: function (v) { return F.r(v, 2); } }, fn: function (b, p) { return P.esperanceR(p, b, c); },
    mid: 0, midLabel: 'équilibre', line: be(), lineLabel: 'p* = (1 + c)/(1 + b)'
  };
  if (kind === 'kelly') {
    var bk = o.bKelly, crest = P.lin(pdom[0], pdom[1], 80).map(function (p) { return [P.kellyF(p, bk), p]; }).filter(function (q) { return q[0] >= 0 && q[0] <= 0.5; });
    return {
      kind: kind, title: 'Croissance de Kelly', x: { name: 'fraction risquée', dom: [0, 0.5], fmt: function (v) { return F.pct(v, v < 0.1 ? 1 : 0); } }, y: { name: 'réussite', dom: pdom, fmt: fpct },
      z: { name: 'croissance par trade', fmt: function (v) { return v === 0 ? '0 %' : F.pct(v, Math.abs(v) < 0.01 ? 3 : 1, true); } }, fn: function (f, p) { return P.kellyGrowth(f, p, bk); },
      mid: 0, midLabel: 'croissance nulle', line: crest, lineLabel: 'crête f* = p − (1 − p)/b', b: bk
    };
  }
  if (kind === 'ruine') {
    var A = o.perteMax, B = o.objectif;
    return {
      kind: kind, title: 'Probabilité de ruine', x: { name: 'R:R', dom: bdom, fmt: function (v) { return nb(v, 2); } }, y: { name: 'réussite', dom: pdom, fmt: fpct },
      z: { name: 'ruine', fmt: function (v) { return F.pct(v, 1); } }, fn: function (b, p) { return P.ruine(p, b, o); },
      mid: B / (A + B), midLabel: 'dérive nulle : ' + F.pct(B / (A + B), 0), line: be(), lineLabel: 'dérive nulle'
    };
  }
  return {
    kind: 'sharpe', title: 'Sharpe annualisé', x: { name: 'R:R', dom: bdom, fmt: function (v) { return nb(v, 2); } }, y: { name: 'réussite', dom: pdom, fmt: fpct },
    z: { name: 'Sharpe annualisé', fmt: function (v) { return nb(v, 1); } }, fn: function (b, p) { return P.sharpeAnnuel(p, b, c, o.nYear); },
    mid: 0, midLabel: 'équilibre', line: be(), lineLabel: 'Sharpe nul'
  };
};
P.surface = function (kind, o, nx, ny, centers) {
  var d = P.surfaceDef(kind, o), xs = P.lin(d.x.dom[0], d.x.dom[1], nx, centers), ys = P.lin(d.y.dom[0], d.y.dom[1], ny, centers);
  var vals = P.grille(d.fn, xs, ys), lo = Infinity, hi = -Infinity, am = [0, 0];
  vals.forEach(function (row, j) { row.forEach(function (v, i) { if (!fin(v)) return; if (v < lo) lo = v; if (v > hi) { hi = v; am = [i, j]; } }); });
  return Object.assign(d, { xs: xs, ys: ys, vals: vals, zmin: lo, zmax: hi, argmax: am });
};

/* =====================================================================
   6. Bootstrap stationnaire (Politis et Romano) — fonction autonome pour T.compute
   Port de alp1/mc.py stationary_bootstrap ; générateur mulberry32 (celui de T.rng).
   Chaque tour tire un rééchantillon brut (Sharpe, drawdown) puis un rééchantillon centré
   (loi nulle du Sharpe : même dépendance, même forme, espérance retirée).
   ===================================================================== */
P.bootstrap = function perfBootstrap(a) {
  var x = a.x, n = x.length, B = a.B, p = 1 / a.block, st = a.seed >>> 0;
  function rnd() { st = (st + 0x6D2B79F5) >>> 0; var t = st; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }
  var m = 0, i0; for (i0 = 0; i0 < n; i0++) m += x[i0]; m /= n;
  function draw(center) {
    var i = Math.floor(rnd() * n), s = 0, s2 = 0, eq = 0, pk = 0, dd = 0, v;
    for (var k = 0; k < n; k++) {
      v = x[i] - center; s += v; s2 += v * v; eq += v; if (eq > pk) pk = eq; if (pk - eq > dd) dd = pk - eq;
      if (rnd() < p) i = Math.floor(rnd() * n); else i = (i + 1) % n;
    }
    var mu = s / n, va = (s2 - n * mu * mu) / (n - 1);
    return [va > 0 ? mu / Math.sqrt(va) : 0, dd];
  }
  var boot = [], nul = [], mdd = [];
  for (var b = 0; b < B; b++) { var d = draw(0); boot.push(d[0]); mdd.push(d[1]); nul.push(draw(m)[0]); }
  if (!a.raw) { var cmp = function (u, w) { return u - w; }; boot.sort(cmp); nul.sort(cmp); mdd.sort(cmp); }
  return { boot: boot, nul: nul, mdd: mdd, block: a.block, B: B };
};

/* =====================================================================
   7. Composants graphiques locaux (besoin socle : nuage de points, histogramme
   avec densité, calendrier, carte de chaleur continue, surface 3D)
   ===================================================================== */
var X = T.esc, charts = P.charts = {};
function cssColor(s) {
  s = String(s || '').trim(); var m;
  if ((m = /^#([0-9a-f]{3})$/i.exec(s))) return [parseInt(m[1][0] + m[1][0], 16), parseInt(m[1][1] + m[1][1], 16), parseInt(m[1][2] + m[1][2], 16)];
  if ((m = /^#([0-9a-f]{6})/i.exec(s))) return [parseInt(m[1].slice(0, 2), 16), parseInt(m[1].slice(2, 4), 16), parseInt(m[1].slice(4, 6), 16)];
  if ((m = /^rgba?\(([^)]+)\)/i.exec(s))) { var q = m[1].split(',').map(parseFloat); return [q[0], q[1], q[2]]; }
  return [128, 128, 128];
}
P.cssColor = cssColor;
function palette() {
  var cs = getComputedStyle(document.documentElement), g = function (k) { return cs.getPropertyValue(k).trim(); };
  return { lo: cssColor(g('--line-2')), mid: cssColor(g('--violet')), hi: cssColor(g('--hi')), line: g('--line'), line2: g('--line-2'), mute: g('--mute'), soft: g('--soft'), fg: g('--fg'), white: g('--hi'), violet: g('--violet'), violet2: g('--violet-2'), panel: g('--panel'), bg: g('--bg'), ink: cssColor(g('--panel')), mono: g('--f-mono') || 'monospace' };
}
function lerp(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]; }
/* Échelle gris → violet → blanc ; t ∈ [0, 1], le violet à mi-course. */
P.ramp = function (pal, t) { t = Math.max(0, Math.min(1, t)); return t < 0.5 ? lerp(pal.lo, pal.mid, t / 0.5) : lerp(pal.mid, pal.hi, (t - 0.5) / 0.5); };
/* Position sur l’échelle : le violet tombe sur la valeur d’équilibre quand elle est dans l’étendue. */
P.tOf = function (z, lo, hi, mid) {
  if (!(hi > lo)) return 0.5;
  if (mid == null || !(mid > lo && mid < hi)) return (z - lo) / (hi - lo);
  return z <= mid ? 0.5 * (z - lo) / (mid - lo) : 0.5 + 0.5 * (z - mid) / (hi - mid);
};
function rgba(c, a) { return 'rgba(' + Math.round(c[0]) + ',' + Math.round(c[1]) + ',' + Math.round(c[2]) + ',' + (a == null ? 1 : a) + ')'; }
function emptySvg(W, t) { return { svg: '<svg viewBox="0 0 ' + W + ' 60" height="60"><text class="ax" x="' + (W / 2) + '" y="34" text-anchor="middle">' + X(t || 'Pas encore de données') + '</text></svg>' }; }

/* Histogramme, avec en option la normale de même moyenne et écart-type (en effectifs attendus).
   Les repères verticaux sont nommés dans la légende, par leur trait : aucun nom n’est posé sur
   la donnée, et deux repères voisins ne se chevauchent jamais. */
charts.histNormal = function (o) {
  var v = (o.values || []).filter(fin), n = v.length, m = S.mean(v), s = S.sd(v), fmt = o.fmt || function (x) { return F.num(x, 0); }, normal = o.normal !== false, unit = o.countLabel || 'trade';
  var leg = normal ? [{ label: o.barLabel || 'trades', box: 'var(--hi)' }, { label: 'normale de même µ et σ', tone: 'violet' }] : [];
  (o.refs || []).forEach(function (r) { if (r.label && fin(r.x)) leg.push({ label: r.label, tone: r.tone === 'violet' ? 'violet' : r.tone === 'mute' ? 'mute' : '', dash: !!r.dash }); });
  return C.mount({ legend: leg }, function (W) {
    if (n < 2 || !(s > 0)) return emptySvg(W, 'Il faut au moins deux résultats différents');
    var refs = (o.refs || []).filter(function (r) { return fin(r.x); });
    var H = o.height || 190, M = { l: 12, r: 12, t: 10, b: 26 };
    var lo = normal ? Math.min(Math.min.apply(null, v), m - 3 * s) : Math.min.apply(null, v), hi = normal ? Math.max(Math.max.apply(null, v), m + 3 * s) : Math.max.apply(null, v);
    refs.forEach(function (r) { if (r.x < lo) lo = r.x; if (r.x > hi) hi = r.x; });
    var pad = (hi - lo) * 0.03; lo -= pad; hi += pad;
    var nbin = o.bins || Math.min(40, Math.max(10, Math.round(Math.sqrt(n) * 1.3))), bw = (hi - lo) / nbin, cnt = [];
    for (var i = 0; i < nbin; i++) cnt.push(0);
    v.forEach(function (x) { var k = Math.floor((x - lo) / bw); if (k >= nbin) k = nbin - 1; if (k < 0) k = 0; cnt[k]++; });
    var dens = function (x) { return n * bw * phi((x - m) / s) / s; }, ymax = Math.max(Math.max.apply(null, cnt), normal ? dens(m) : 0) * 1.04;
    var sx = function (x) { return M.l + (x - lo) / (hi - lo) * (W - M.l - M.r); }, sy = function (c) { return M.t + (1 - c / ymax) * (H - M.t - M.b); }, g = '';
    var split = o.split == null ? 0 : o.split;
    cnt.forEach(function (c, k) { if (!c) return; var a = lo + k * bw, mid = a + bw / 2, low = split !== false && mid < split; g += '<rect x="' + (sx(a) + 0.5).toFixed(1) + '" y="' + sy(c).toFixed(1) + '" width="' + Math.max(1, sx(a + bw) - sx(a) - 1).toFixed(1) + '" height="' + (H - M.b - sy(c)).toFixed(1) + '" fill="' + (low ? 'var(--soft)' : 'var(--hi)') + '" opacity="' + (low ? '.5' : '.85') + '"/>'; });
    g += '<line class="zl" x1="' + M.l + '" x2="' + (W - M.r) + '" y1="' + (H - M.b) + '" y2="' + (H - M.b) + '"/>';
    if (normal) { var d = ''; for (var q = 0; q <= 120; q++) { var xx = lo + (hi - lo) * q / 120; d += (q ? 'L' : 'M') + sx(xx).toFixed(1) + ',' + sy(dens(xx)).toFixed(1); } g += '<path d="' + d + '" fill="none" stroke="var(--violet)" stroke-width="1.8" stroke-linejoin="round"/>'; }
    T.ticks(lo, hi, Math.max(2, Math.floor((W - 24) / 84))).forEach(function (t) { if (t < lo || t > hi) return; g += '<text class="ax" x="' + sx(t).toFixed(1) + '" y="' + (H - 8) + '" text-anchor="middle">' + X(fmt(t)) + '</text>'; });
    refs.forEach(function (r) {
      var x = sx(r.x), col = r.tone === 'mute' ? 'var(--soft)' : r.tone === 'violet' ? 'var(--violet)' : 'var(--hi)';
      g += '<line x1="' + x.toFixed(1) + '" x2="' + x.toFixed(1) + '" y1="' + M.t + '" y2="' + (H - M.b) + '" stroke="' + col + '" stroke-width="1.6"' + (r.dash ? ' stroke-dasharray="4 3"' : '') + '/>';
    });
    g += '<line class="hl" x1="0" x2="0" y1="' + M.t + '" y2="' + (H - M.b) + '" stroke="var(--violet)" style="opacity:0"/>';
    var xs = cnt.map(function (_, k) { return sx(lo + (k + 0.5) * bw); });
    return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '">' + g + '</svg>', hover: { xs: xs, html: function (k) { var a = lo + k * bw; return '<b>' + X(fmt(a)) + ' à ' + X(fmt(a + bw)) + '</b><br>' + cnt[k] + ' ' + unit + (cnt[k] > 1 ? 's' : '') + (normal ? '<br>normale ' + X(F.num(dens(a + bw / 2), 1)) : ''); } } };
  });
};

/* Diagramme quantile-quantile contre la normale : nuage de points, diagonale µ + σ·z. */
charts.qq = function (o) {
  var v = (o.values || []).filter(fin), n = v.length, m = S.mean(v), s = S.sd(v), fmt = o.fmt || function (x) { return F.num(x, 0); };
  var pts = P.qq(v); if (pts.length > 700) { var step = pts.length / 700, keep = []; for (var i = 0; i < 700; i++) keep.push(pts[Math.floor(i * step)]); keep.push(pts[pts.length - 1]); pts = keep; }
  return C.mount({ legend: [{ label: 'trades classés', box: 'var(--hi)' }, { label: 'normale µ + σ·z', tone: 'violet', dash: true }] }, function (W) {
    if (n < 3 || !(s > 0)) return emptySvg(W, 'Il faut au moins trois résultats différents');
    var H = o.height || 240, M = { l: 54, r: 12, t: 12, b: 30 };
    var zx0 = pts[0][0], zx1 = pts[pts.length - 1][0], xp = (zx1 - zx0) * 0.05; zx0 -= xp; zx1 += xp;
    var ys = pts.map(function (q) { return q[1]; }).concat([m + s * zx0, m + s * zx1]), y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys), yp = (y1 - y0) * 0.06 || 1; y0 -= yp; y1 += yp;
    var sx = function (z) { return M.l + (z - zx0) / (zx1 - zx0) * (W - M.l - M.r); }, sy = function (y) { return M.t + (1 - (y - y0) / (y1 - y0)) * (H - M.t - M.b); }, g = '';
    T.ticks(y0, y1, 4).forEach(function (t) { if (t < y0 || t > y1) return; g += '<line class="' + (t === 0 ? 'zl' : 'gl') + '" x1="' + M.l + '" x2="' + (W - M.r) + '" y1="' + sy(t).toFixed(1) + '" y2="' + sy(t).toFixed(1) + '"/><text class="ax" x="' + (M.l - 7) + '" y="' + (sy(t) + 3.5).toFixed(1) + '" text-anchor="end">' + X(fmt(t)) + '</text>'; });
    T.ticks(zx0, zx1, 5).forEach(function (t) { if (t < zx0 || t > zx1) return; g += '<line class="gl" x1="' + sx(t).toFixed(1) + '" x2="' + sx(t).toFixed(1) + '" y1="' + M.t + '" y2="' + (H - M.b) + '" opacity=".5"/><text class="ax" x="' + sx(t).toFixed(1) + '" y="' + (H - 12) + '" text-anchor="middle">' + X(F.num(t, Math.abs(t) % 1 ? 1 : 0)) + '</text>'; });
    g += '<text class="ax" x="' + (W - M.r) + '" y="' + (H - 1) + '" text-anchor="end">quantile normal z</text>';
    g += '<line x1="' + sx(zx0).toFixed(1) + '" x2="' + sx(zx1).toFixed(1) + '" y1="' + sy(m + s * zx0).toFixed(1) + '" y2="' + sy(m + s * zx1).toFixed(1) + '" stroke="var(--violet)" stroke-width="1.5" stroke-dasharray="5 4"/>';
    var r = n > 300 ? 1.8 : 2.6;
    pts.forEach(function (q) { g += '<circle cx="' + sx(q[0]).toFixed(1) + '" cy="' + sy(q[1]).toFixed(1) + '" r="' + r + '" fill="var(--hi)" opacity=".78"/>'; });
    g += '<line class="hl" x1="0" x2="0" y1="' + M.t + '" y2="' + (H - M.b) + '" stroke="var(--violet)" style="opacity:0"/>';
    return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '">' + g + '</svg>', hover: { xs: pts.map(function (q) { return sx(q[0]); }), html: function (k) { var q = pts[k]; return '<b>z ' + X(F.num(q[0], 2)) + '</b><br>observé ' + X(fmt(q[1])) + '<br>normale ' + X(fmt(m + s * q[0])); } } };
  });
};

/* Calendrier de chaleur des P&L journaliers, façon GitHub : semaines en colonnes, jours en lignes. */
var MOIS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];
var JOURS = ['dim', 'lun', 'mar', 'mer', 'jeu', 'ven', 'sam'];
charts.calendar = function (o) {
  var days = o.days || [], fmt = o.fmt || usd, outer = h('div', { class: 'chart' }), sc = h('div', { class: 'heat pf-cal' }), tip = h('div', { class: 'tip' });
  outer.appendChild(sc); outer.appendChild(tip);
  if (!days.length) { sc.appendChild(h('p', { class: 'note', style: 'padding:12px' }, 'Aucune date dans cette source.')); return outer; }
  var by = {}; days.forEach(function (d) { by[d.key] = d; });
  var f = days[0], l = days[days.length - 1], t0 = Date.UTC(f.y, f.mo - 1, f.d), t1 = Date.UTC(l.y, l.mo - 1, l.d);
  var off0 = (new Date(t0).getUTCDay() + 6) % 7, start = t0 - off0 * 864e5, off1 = (new Date(t1).getUTCDay() + 6) % 7, end = t1 + (6 - off1) * 864e5;
  var cells = []; for (var t = start; t <= end + 1; t += 864e5) { var dt = new Date(t), k = dt.getUTCFullYear() + '-' + String(dt.getUTCMonth() + 1).padStart(2, '0') + '-' + String(dt.getUTCDate()).padStart(2, '0'); cells.push({ t: t, key: k, mo: dt.getUTCMonth(), y: dt.getUTCFullYear(), d: dt.getUTCDate(), wd: dt.getUTCDay(), v: by[k] || null }); }
  var weeks = Math.ceil(cells.length / 7), mx = 0; days.forEach(function (d) { mx = Math.max(mx, Math.abs(d.pnl)); });
  function draw() {
    if (!outer.isConnected) return;
    var W = Math.max(240, outer.clientWidth - 18), lab = 26, top = 16, gap = 2, avail = W - lab, cell = Math.max(10, Math.min(18, Math.floor(avail / weeks) - gap)), st = cell + gap;
    var SW = lab + weeks * st, SH = top + 7 * st, g = '', lastLab = -99;
    [0, 2, 4].forEach(function (r) { g += '<text class="ax" x="0" y="' + (top + r * st + cell - 2) + '">' + JOURS[(r + 1) % 7] + '</text>'; });
    for (var w = 0; w < weeks; w++) {
      var c0 = cells[w * 7]; if (!c0) break;
      var x = lab + w * st, moLab = null;
      /* le mois s’écrit sur la semaine qui contient son premier jour ; la première colonne prend le mois du premier trade */
      for (var r1 = 0; r1 < 7; r1++) { var cc = cells[w * 7 + r1]; if (cc && cc.d === 1) moLab = cc.mo; }
      if (w === 0) moLab = f.mo - 1;
      if (moLab != null && x - lastLab > 30 && x + 26 <= SW + 4) { g += '<text class="ax" x="' + x + '" y="10">' + X(MOIS[moLab]) + '</text>'; lastLab = x; }
      for (var r2 = 0; r2 < 7; r2++) {
        var ce = cells[w * 7 + r2]; if (!ce) continue; var y = top + r2 * st, v = ce.v, attr;
        if (!v) attr = 'fill="none" stroke="var(--line)"';
        else if (v.pnl === 0) attr = 'fill="var(--line-2)"';
        else { var a = Math.sqrt(Math.abs(v.pnl) / (mx || 1)); attr = v.pnl > 0 ? 'fill="var(--violet)" fill-opacity="' + (0.22 + 0.78 * a).toFixed(3) + '"' : 'fill="var(--soft)" fill-opacity="' + (0.14 + 0.6 * a).toFixed(3) + '"'; }
        g += '<rect data-i="' + (w * 7 + r2) + '" x="' + (x + 0.5) + '" y="' + (y + 0.5) + '" width="' + (cell - 1) + '" height="' + (cell - 1) + '" rx="2" ' + attr + '/>';
      }
    }
    sc.innerHTML = '<svg width="' + SW + '" height="' + SH + '" viewBox="0 0 ' + SW + ' ' + SH + '" style="display:block;width:' + SW + 'px;max-width:none;height:' + SH + 'px;overflow:visible">' + g + '</svg>';
    if (SW > W) sc.scrollLeft = sc.scrollWidth;
  }
  function show(e) {
    var tg = e.target, i = tg && tg.getAttribute && tg.getAttribute('data-i'); if (i == null) { tip.classList.remove('on'); return; }
    var ce = cells[+i], rc = outer.getBoundingClientRect(), rr = tg.getBoundingClientRect();
    tip.innerHTML = '<b>' + JOURS[ce.wd] + ' ' + String(ce.d).padStart(2, '0') + ' ' + X(MOIS[ce.mo]) + ' ' + ce.y + '</b><br>' + (ce.v ? X(fmt(ce.v.pnl, true)) + ' · ' + ce.v.n + ' trade' + (ce.v.n > 1 ? 's' : '') : 'aucun trade');
    tip.classList.add('on'); var tw = tip.offsetWidth, left = rr.left - rc.left + 14; if (left + tw > rc.width) left = rr.left - rc.left - tw - 6; tip.style.left = Math.max(0, left) + 'px'; tip.style.top = Math.max(0, rr.top - rc.top - 44) + 'px';
  }
  sc.addEventListener('pointermove', show); sc.addEventListener('pointerdown', show); sc.addEventListener('pointerleave', function (e) { if (e.pointerType === 'mouse') tip.classList.remove('on'); });
  T.observe(outer, draw);
  return outer;
};

/* Carte de chaleur continue en canvas : grille centrée sur les cellules, lissage bilinéaire,
   isoligne d’équilibre, point de l’utilisateur, barre d’échelle. */
charts.heatmap2d = function (o) {
  var sf = o.surf, wrap = h('div', { class: 'chart pf-2d' }), cv = h('canvas', { class: 'pf-cv', role: 'img', 'aria-label': sf.title + ' en fonction de ' + sf.x.name + ' et ' + sf.y.name }), tip = h('div', { class: 'tip' });
  wrap.appendChild(cv); wrap.appendChild(tip);
  var img = null, geo = null, pal = null;
  function build() {
    var nx = sf.xs.length, ny = sf.ys.length; img = document.createElement('canvas'); img.width = nx; img.height = ny;
    var g = img.getContext('2d'), id = g.createImageData(nx, ny);
    for (var j = 0; j < ny; j++) for (var i = 0; i < nx; i++) {
      var v = sf.vals[ny - 1 - j][i], c = fin(v) ? P.ramp(pal, P.tOf(v, sf.zmin, sf.zmax, sf.mid)) : pal.ink, q = (j * nx + i) * 4;
      id.data[q] = c[0]; id.data[q + 1] = c[1]; id.data[q + 2] = c[2]; id.data[q + 3] = 255;
    }
    g.putImageData(id, 0, 0);
  }
  function draw() {
    if (!wrap.isConnected) return;
    var W = Math.max(240, Math.round(wrap.clientWidth)), H = o.height || Math.round(Math.min(360, Math.max(270, W * 0.74))), dpr = window.devicePixelRatio || 1;
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); cv.style.height = H + 'px';
    var g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H);
    pal = palette(); if (!img) build();
    var m = { l: 46, r: 10, t: 8, b: 74 }, pw = W - m.l - m.r, ph = H - m.t - m.b, x0 = sf.x.dom[0], x1 = sf.x.dom[1], y0 = sf.y.dom[0], y1 = sf.y.dom[1];
    var sx = function (x) { return m.l + (x - x0) / (x1 - x0) * pw; }, sy = function (y) { return m.t + (1 - (y - y0) / (y1 - y0)) * ph; };
    g.imageSmoothingEnabled = true; g.drawImage(img, m.l, m.t, pw, ph);
    g.strokeStyle = pal.line2; g.lineWidth = 1; g.strokeRect(m.l + 0.5, m.t + 0.5, pw - 1, ph - 1);
    var font = '500 10px ' + pal.mono; g.font = font; g.fillStyle = pal.mute; g.textBaseline = 'middle';
    g.textAlign = 'center'; T.ticks(x0, x1, Math.max(3, Math.floor(pw / 70))).forEach(function (t) { if (t < x0 - 1e-9 || t > x1 + 1e-9) return; var x = sx(t); g.fillRect(Math.round(x), m.t + ph, 1, 4); g.fillText(sf.x.fmt(t), Math.min(Math.max(x, m.l + 12), W - m.r - 12), m.t + ph + 13); });
    g.textAlign = 'right'; T.ticks(y0, y1, 4).forEach(function (t) { if (t < y0 - 1e-9 || t > y1 + 1e-9) return; var y = sy(t); g.fillRect(m.l - 4, Math.round(y), 4, 1); g.fillText(sf.y.fmt(t), m.l - 7, Math.min(Math.max(y, m.t + 6), m.t + ph - 4)); });
    g.fillStyle = pal.soft; g.textAlign = 'center'; g.fillText(sf.x.name + ' →', m.l + pw / 2, m.t + ph + 28);
    g.save(); g.translate(10, m.t + ph / 2); g.rotate(-Math.PI / 2); g.fillText(sf.y.name + ' →', 0, 0); g.restore();
    var ln = sf.line || [];
    if (ln.length > 1) {
      g.save(); g.beginPath(); g.rect(m.l, m.t, pw, ph); g.clip();
      g.setLineDash([6, 4]); g.lineWidth = 2; g.strokeStyle = pal.white; g.beginPath(); ln.forEach(function (q, k) { var x = sx(q[0]), y = sy(q[1]); if (k) g.lineTo(x, y); else g.moveTo(x, y); }); g.stroke(); g.restore();
      var lq = ln[Math.floor(ln.length * 0.62)], lx = sx(lq[0]), ly = sy(lq[1]);
      g.font = '600 10.5px ' + pal.mono; var tw = g.measureText(sf.lineLabel).width, bx = Math.min(Math.max(lx + 8, m.l + 4), m.l + pw - tw - 12), by = Math.min(Math.max(ly - 16, m.t + 4), m.t + ph - 20);
      g.fillStyle = rgba(pal.ink, 0.86); g.fillRect(bx - 4, by, tw + 8, 16); g.fillStyle = pal.white; g.textAlign = 'left'; g.fillText(sf.lineLabel, bx, by + 8.5);
    }
    var u = o.user;
    if (u && fin(u.x) && fin(u.y)) {
      var ux = sx(Math.min(Math.max(u.x, x0), x1)), uy = sy(Math.min(Math.max(u.y, y0), y1)), out = u.x < x0 || u.x > x1 || u.y < y0 || u.y > y1;
      g.setLineDash(out ? [2, 2] : []); g.lineWidth = 2.2; g.strokeStyle = pal.white; g.fillStyle = pal.violet;
      g.beginPath(); g.arc(ux, uy, 6, 0, Math.PI * 2); g.fill(); g.stroke(); g.setLineDash([]);
      g.font = '600 11px ' + pal.mono; var lab = u.label || 'toi', lw = g.measureText(lab).width, lxx = ux + 10 + lw > m.l + pw ? ux - 10 - lw : ux + 10;
      g.fillStyle = rgba(pal.ink, 0.86); g.fillRect(lxx - 3, uy - 9, lw + 6, 17); g.fillStyle = pal.white; g.textAlign = 'left'; g.fillText(lab, lxx, uy);
    }
    var gy = H - 26, gw = pw, gx = m.l, grad = g.createLinearGradient(gx, 0, gx + gw, 0);
    for (var s = 0; s <= 10; s++) grad.addColorStop(s / 10, rgba(P.ramp(pal, s / 10)));
    g.fillStyle = grad; g.fillRect(gx, gy, gw, 7); g.strokeStyle = pal.line2; g.strokeRect(gx + 0.5, gy + 0.5, gw - 1, 6);
    g.font = font; g.fillStyle = pal.mute; g.textBaseline = 'top';
    g.textAlign = 'left'; g.fillText(sf.z.fmt(sf.zmin), gx, gy + 11); g.textAlign = 'right'; g.fillText(sf.z.fmt(sf.zmax), gx + gw, gy + 11);
    var tm = P.tOf(sf.mid, sf.zmin, sf.zmax, sf.mid);
    if (sf.mid != null && sf.mid > sf.zmin && sf.mid < sf.zmax) { var mx = gx + gw * tm; g.fillStyle = pal.white; g.fillRect(Math.round(mx), gy - 3, 1, 13); g.fillStyle = pal.soft; g.textAlign = 'center'; g.fillText(sf.midLabel, Math.min(Math.max(mx, gx + 60), gx + gw - 60), gy + 11); }
    g.textBaseline = 'alphabetic';
    geo = { m: m, pw: pw, ph: ph, x0: x0, x1: x1, y0: y0, y1: y1, W: W };
  }
  function show(e) {
    if (!geo) return; var rc = cv.getBoundingClientRect(), px = e.clientX - rc.left, py = e.clientY - rc.top, G = geo;
    if (px < G.m.l || px > G.m.l + G.pw || py < G.m.t || py > G.m.t + G.ph) { tip.classList.remove('on'); return; }
    var x = G.x0 + (px - G.m.l) / G.pw * (G.x1 - G.x0), y = G.y0 + (1 - (py - G.m.t) / G.ph) * (G.y1 - G.y0), z = sf.fn(x, y);
    tip.innerHTML = X(sf.x.name) + ' ' + X(sf.x.fmt(x)) + '<br>' + X(sf.y.name) + ' ' + X(sf.y.fmt(y)) + '<br><b>' + X(sf.z.name) + ' ' + X(sf.z.fmt(z)) + '</b>';
    tip.classList.add('on'); var tw = tip.offsetWidth, left = px + 14; if (left + tw > rc.width) left = px - tw - 14; tip.style.left = Math.max(0, left) + 'px'; tip.style.top = Math.max(0, py - 60) + 'px';
  }
  cv.addEventListener('pointermove', show); cv.addEventListener('pointerdown', show); cv.addEventListener('pointerleave', function (e) { if (e.pointerType === 'mouse') tip.classList.remove('on'); });
  T.observe(wrap, draw);
  return wrap;
};

/* Surface 3D en nuage de points, projection orthographique, rotation au doigt (azimut et
   élévation, inertie légère). Règles du dépôt ALP : le maximum au fond à l’état initial,
   teinte et taille suivent la hauteur, sol en grille, montants aux coins, échine graduée. */
P.azimutInitial = function (u, v) {
  var best = null, cands = [Math.PI / 4, 3 * Math.PI / 4, 5 * Math.PI / 4, 7 * Math.PI / 4];
  cands.forEach(function (a) { var yr = u * Math.sin(a) + v * Math.cos(a); if (!best || yr < best.yr - 1e-12) best = { a: a, yr: yr }; });
  return best.a;
};
/* Projection : u, v ∈ [−½, ½] au sol, w ∈ [0, 1] en hauteur. Profondeur croissante vers l’observateur. */
P.project = function (u, v, w, az, el, hz) {
  var ca = Math.cos(az), sa = Math.sin(az), xr = u * ca - v * sa, yr = u * sa + v * ca;
  return { x: xr, y: yr * Math.sin(el) - w * hz * Math.cos(el), depth: yr * Math.cos(el) + w * hz * Math.sin(el) };
};
charts.surface3d = function (o) {
  var sf = o.surf, nx = sf.xs.length, ny = sf.ys.length, HZ = 0.62;
  var wrap = h('div', { class: 'chart pf-3d' }), cv = h('canvas', { class: 'pf-cv', role: 'img', 'aria-label': sf.title + ' en relief, à faire tourner au doigt' }), tip = h('div', { class: 'tip' });
  var reset = U.button({ label: 'Vue initiale', small: true, kind: 'ghost', onClick: function () { st.az = az0; st.el = EL0; st.vaz = st.vel = 0; st.tip = -1; tip.classList.remove('on'); draw(); } });
  wrap.appendChild(cv); wrap.appendChild(tip);
  wrap.appendChild(h('div', { class: 'pf-tools' }, h('span', null, 'Glisse pour tourner · touche un point pour ses valeurs'), reset));
  var am = sf.argmax, az0 = P.azimutInitial(am[0] / (nx - 1) - 0.5, am[1] / (ny - 1) - 0.5), EL0 = 0.6;
  var st = { az: az0, el: EL0, vaz: 0, vel: 0, drag: null, raf: 0, pend: false, tip: -1, pts: [] };
  var W = 0, H = 0, Sc = 1, cx = 0, cy = 0;
  function wOf(z) { return sf.zmax > sf.zmin ? (z - sf.zmin) / (sf.zmax - sf.zmin) : 0.5; }
  function scr(u, v, w) { var p = P.project(u, v, w, st.az, st.el, HZ); return [cx + Sc * p.x, cy + Sc * p.y, p.depth]; }
  function draw() {
    if (!wrap.isConnected) return;
    var pal = palette(), dpr = window.devicePixelRatio || 1;
    W = Math.max(240, Math.round(wrap.clientWidth)); H = o.height || Math.round(Math.min(520, Math.max(280, W * 0.8)));
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); cv.style.height = H + 'px';
    var g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H);
    var ml = 60, mr = 16, mt = 14, mb = 42, aw = W - ml - mr, ah = H - mt - mb, se = Math.sin(st.el), ce = Math.cos(st.el);
    Sc = Math.min(aw / Math.SQRT2, ah / (Math.SQRT2 * se + HZ * ce));
    cx = ml + aw / 2; cy = mt + ah / 2 + Sc * (HZ * ce) / 2;
    var font = '500 10px ' + pal.mono;
    /* sol en grille */
    g.lineWidth = 1; g.strokeStyle = pal.line;
    for (var k = 0; k <= 6; k++) {
      var t = -0.5 + k / 6, a = scr(t, -0.5, 0), b = scr(t, 0.5, 0), c = scr(-0.5, t, 0), d = scr(0.5, t, 0);
      g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]); g.moveTo(c[0], c[1]); g.lineTo(d[0], d[1]); g.stroke();
    }
    /* isoligne d’équilibre posée au sol */
    var ln = sf.line || [], X0 = sf.x.dom[0], X1 = sf.x.dom[1], Y0 = sf.y.dom[0], Y1 = sf.y.dom[1];
    var uOf = function (x) { return (x - X0) / (X1 - X0) - 0.5; }, vOf = function (y) { return (y - Y0) / (Y1 - Y0) - 0.5; };
    if (ln.length > 1) { g.setLineDash([5, 4]); g.strokeStyle = pal.soft; g.lineWidth = 1.4; g.beginPath(); ln.forEach(function (q, i) { var p = scr(uOf(q[0]), vOf(q[1]), 0); if (i) g.lineTo(p[0], p[1]); else g.moveTo(p[0], p[1]); }); g.stroke(); g.setLineDash([]); }
    /* montants aux coins */
    var corners = [[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]].map(function (q) { var lo = scr(q[0], q[1], 0), hi = scr(q[0], q[1], 1); return { u: q[0], v: q[1], lo: lo, hi: hi }; });
    g.strokeStyle = pal.line2; g.lineWidth = 1;
    corners.forEach(function (c2) { g.beginPath(); g.moveTo(c2.lo[0], c2.lo[1]); g.lineTo(c2.hi[0], c2.hi[1]); g.stroke(); });
    /* points, du plus lointain au plus proche */
    var pts = [];
    for (var j = 0; j < ny; j++) for (var i = 0; i < nx; i++) { var z = sf.vals[j][i]; if (!fin(z)) continue; var w = wOf(z), p = scr(i / (nx - 1) - 0.5, j / (ny - 1) - 0.5, w); pts.push({ x: p[0], y: p[1], d: p[2], w: w, z: z, i: i, j: j }); }
    pts.sort(function (p1, p2) { return p1.d - p2.d; });
    pts.forEach(function (p) { var c3 = P.ramp(pal, P.tOf(p.z, sf.zmin, sf.zmax, sf.mid)); g.fillStyle = rgba(c3, 0.92); g.beginPath(); g.arc(p.x, p.y, 1.1 + 2.7 * p.w, 0, Math.PI * 2); g.fill(); });
    st.pts = pts;
    /* échine graduée au coin le plus à gauche */
    var left = corners.slice().sort(function (c4, c5) { return c4.lo[0] - c5.lo[0]; })[0];
    g.strokeStyle = pal.mute; g.lineWidth = 1.2; g.beginPath(); g.moveTo(left.lo[0], left.lo[1]); g.lineTo(left.hi[0], left.hi[1]); g.stroke();
    g.font = font; g.fillStyle = pal.soft; g.textAlign = 'right'; g.textBaseline = 'middle';
    T.ticks(sf.zmin, sf.zmax, 4).forEach(function (tv) { if (tv < sf.zmin - 1e-12 || tv > sf.zmax + 1e-12) return; var q = scr(left.u, left.v, wOf(tv)); g.fillRect(q[0] - 4, Math.round(q[1]), 4, 1); g.fillText(sf.z.fmt(tv), q[0] - 7, q[1]); });
    /* arêtes du sol nommées : les deux bords les plus proches */
    var center = scr(0, 0, 0), near = corners.slice().sort(function (c6, c7) { return c7.lo[2] - c6.lo[2]; })[0];
    function edge(isX) {
      var cA = isX ? scr(0, -0.5, 0) : scr(-0.5, 0, 0), cB = isX ? scr(0, 0.5, 0) : scr(0.5, 0, 0), side = cA[2] > cB[2] ? -0.5 : 0.5;
      var f2 = function (s) { return isX ? scr(s, side, 0) : scr(side, s, 0); }, mid = f2(0), dx = mid[0] - center[0], dy = mid[1] - center[1], L = Math.sqrt(dx * dx + dy * dy) || 1, ox = dx / L * 16, oy = dy / L * 16;
      g.fillStyle = pal.soft; g.textAlign = 'center'; g.fillText((isX ? sf.x.name : sf.y.name), mid[0] + ox * 1.15, mid[1] + oy * 1.15);
      g.fillStyle = pal.mute;
      [-0.5, 0.5].forEach(function (s) {
        var q = f2(s), val = isX ? X0 + (s + 0.5) * (X1 - X0) : Y0 + (s + 0.5) * (Y1 - Y0), txt = (isX ? sf.x : sf.y).fmt(val), tw = g.measureText(txt).width;
        if (Math.abs(q[0] - near.lo[0]) < 1 && Math.abs(q[1] - near.lo[1]) < 1) {
          /* coin le plus proche : les deux arêtes s’y rejoignent, chaque étiquette se range du côté de son arête */
          var leftSide = mid[0] < q[0]; g.textAlign = leftSide ? 'right' : 'left'; g.fillText(txt, q[0] + (leftSide ? -6 : 6), q[1] + 14); g.textAlign = 'center';
        } else g.fillText(txt, Math.min(Math.max(q[0] + ox, tw / 2 + 2), W - tw / 2 - 2), q[1] + oy);
      });
    }
    edge(true); edge(false);
    /* point de l’utilisateur */
    var u = o.user;
    if (u && fin(u.x) && fin(u.y)) {
      var xu = Math.min(Math.max(u.x, X0), X1), yu = Math.min(Math.max(u.y, Y0), Y1), zu = sf.fn(xu, yu);
      if (fin(zu)) {
        var wu = Math.max(0, Math.min(1, wOf(zu))), base = scr(uOf(xu), vOf(yu), 0), topp = scr(uOf(xu), vOf(yu), wu);
        g.setLineDash([3, 3]); g.strokeStyle = pal.white; g.lineWidth = 1.2; g.beginPath(); g.moveTo(base[0], base[1]); g.lineTo(topp[0], topp[1]); g.stroke(); g.setLineDash([]);
        g.fillStyle = pal.violet; g.strokeStyle = pal.white; g.lineWidth = 2; g.beginPath(); g.arc(topp[0], topp[1], 5.5, 0, Math.PI * 2); g.fill(); g.stroke();
        g.font = '600 11px ' + pal.mono; g.textAlign = 'left'; var lab = u.label || 'toi', lw = g.measureText(lab).width, lx = topp[0] + 9 + lw > W - 4 ? topp[0] - 9 - lw : topp[0] + 9;
        g.fillStyle = rgba(pal.ink, 0.86); g.fillRect(lx - 3, topp[1] - 9, lw + 6, 17); g.fillStyle = pal.white; g.fillText(lab, lx, topp[1]);
      }
    }
    if (st.tip >= 0) { var tp = null; for (var q2 = 0; q2 < pts.length; q2++) if (pts[q2].i + pts[q2].j * nx === st.tip) { tp = pts[q2]; break; } if (tp) { g.strokeStyle = pal.white; g.lineWidth = 1.5; g.beginPath(); g.arc(tp.x, tp.y, 4 + 2.7 * tp.w, 0, Math.PI * 2); g.stroke(); } }
    g.textBaseline = 'alphabetic';
  }
  function sched() { if (st.pend) return; st.pend = true; requestAnimationFrame(function () { st.pend = false; draw(); }); }
  function clampEl(e) { return Math.max(0.18, Math.min(1.45, e)); }
  function spin() {
    st.raf = 0; if (!wrap.isConnected || st.drag) return;
    if (Math.abs(st.vaz) < 2e-4 && Math.abs(st.vel) < 2e-4) return;
    st.az += st.vaz; st.el = clampEl(st.el + st.vel); st.vaz *= 0.86; st.vel *= 0.86; draw(); st.raf = requestAnimationFrame(spin);
  }
  function nearest(e) {
    var rc = cv.getBoundingClientRect(), px = e.clientX - rc.left, py = e.clientY - rc.top, best = null, bd = 28 * 28;
    st.pts.forEach(function (p) { var dx = p.x - px, dy = p.y - py, d2 = dx * dx + dy * dy; if (d2 < bd) { bd = d2; best = p; } });
    if (!best) { st.tip = -1; tip.classList.remove('on'); draw(); return; }
    st.tip = best.i + best.j * nx; draw();
    tip.innerHTML = X(sf.x.name) + ' ' + X(sf.x.fmt(sf.xs[best.i])) + '<br>' + X(sf.y.name) + ' ' + X(sf.y.fmt(sf.ys[best.j])) + '<br><b>' + X(sf.z.name) + ' ' + X(sf.z.fmt(best.z)) + '</b>';
    tip.classList.add('on'); var tw = tip.offsetWidth, left = best.x + 12; if (left + tw > rc.width) left = best.x - tw - 12; tip.style.left = Math.max(0, left) + 'px'; tip.style.top = Math.max(0, best.y - 64) + 'px';
  }
  cv.addEventListener('pointerdown', function (e) {
    try { cv.setPointerCapture(e.pointerId); } catch (er) {}
    if (st.raf) { cancelAnimationFrame(st.raf); st.raf = 0; }
    st.vaz = st.vel = 0; st.drag = { x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY, moved: false, t: e.timeStamp };
  });
  cv.addEventListener('pointermove', function (e) {
    var d = st.drag;
    if (!d) { if (e.pointerType === 'mouse') nearest(e); return; }
    var dx = e.clientX - d.x, dy = e.clientY - d.y, dt = Math.max(8, e.timeStamp - d.t); d.x = e.clientX; d.y = e.clientY; d.t = e.timeStamp;
    if (!d.moved && Math.abs(e.clientX - d.x0) + Math.abs(e.clientY - d.y0) > 6) { d.moved = true; st.tip = -1; tip.classList.remove('on'); }
    if (d.moved) { var daz = -dx * 0.01, del = dy * 0.008, k = 16 / dt; st.az += daz; st.el = clampEl(st.el + del); st.vaz = Math.max(-0.04, Math.min(0.04, daz * k)); st.vel = Math.max(-0.03, Math.min(0.03, del * k)); sched(); }
  });
  function up(e) { var d = st.drag; st.drag = null; if (!d) return; if (!d.moved) { nearest(e); return; } if (e.timeStamp - d.t > 90) { st.vaz = st.vel = 0; return; } if (!st.raf) st.raf = requestAnimationFrame(spin); }
  cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', function () { st.drag = null; });
  cv.addEventListener('pointerleave', function (e) { if (e.pointerType === 'mouse' && !st.drag) { st.tip = -1; tip.classList.remove('on'); draw(); } });
  wrap.__state = st;
  T.observe(wrap, draw);
  return wrap;
};

/* =====================================================================
   8. Le desk
   ===================================================================== */
var KEY = { src: 'perf:src', par: 'perf:params', paste: 'perf:paste', sim: 'perf:sim', surf: 'perf:surf', view: 'perf:view' };
var DEF_PAR = { tpd: 2, days: 252, capital: 50000, trials: 10, window: 20, seed: 7, cost: null, objectif: 3000, perteMax: 2000 };
var DEF_SIM = { p: 0.40, b: 1.5, n: 250, seed: 42, noise: 0.15 };
var CSS = '.pf-srcline{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;font:500 11.5px/1.45 var(--f-mono);color:var(--mute)}.pf-srcline b{color:var(--fg);font-weight:600}' +
  '.seg button:disabled{opacity:.36;cursor:default}' +
  'details.pf-hyp{border-top:1px solid var(--line);padding-top:10px}details.pf-hyp>summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;gap:8px;align-items:baseline;font:600 10.5px/1.3 var(--f-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--soft)}details.pf-hyp>summary::-webkit-details-marker{display:none}details.pf-hyp>summary span{color:var(--mute);text-transform:none;letter-spacing:0;font-weight:500;text-align:right}details.pf-hyp[open]>summary{margin-bottom:12px}details.pf-hyp>summary::after{content:"+";color:var(--violet-2);margin-left:6px}details.pf-hyp[open]>summary::after{content:"−"}' +
  '.pf-grp{border:1px solid var(--line);border-radius:var(--r);background:var(--panel);overflow:hidden}.pf-gh{display:flex;justify-content:space-between;gap:8px;padding:10px 13px 9px;font:600 10px/1.2 var(--f-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--violet-2);border-bottom:1px solid var(--line)}.pf-gh span{color:var(--mute);letter-spacing:.04em}' +
  '.pf-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:3px 12px;width:100%;text-align:left;padding:10px 13px;border-top:1px solid var(--line);align-items:baseline}.pf-gh+.pf-row{border-top:0}' +
  '.pf-row .n{font-size:13.5px;font-weight:600;color:var(--fg);display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px;min-width:0}.pf-row .n .pill{height:18px;font-size:9px;padding:0 6px}' +
  '.pf-row .v{font:600 14px/1.2 var(--f-mono);color:var(--hi);text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}' +
  '.pf-row .r{grid-column:1/-1;font-size:12.5px;color:var(--mute);line-height:1.45}.pf-row[aria-expanded="true"]{background:var(--raise)}.pf-row[aria-expanded="true"] .r{color:var(--soft)}' +
  '.pf-def{padding:2px 13px 13px;background:var(--raise);display:flex;flex-direction:column;gap:8px}.pf-def .lb{font:600 9.5px/1 var(--f-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--mute)}' +
  '.pf-f{font:500 12px/1.6 var(--f-mono);color:var(--fg);background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:9px 11px;overflow-wrap:anywhere}.pf-def .nl{font-size:12.5px;color:var(--soft);line-height:1.5;border-left:2px solid var(--violet);padding-left:10px}' +
  '.pf-cv{display:block;width:100%;touch-action:none;-webkit-user-select:none;user-select:none}.pf-tools{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:8px;font:500 10.5px/1.3 var(--f-mono);color:var(--mute)}.pf-tools span{min-width:0}' +
  '.pf-cal{padding:10px 8px 6px}.pf-leg{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:8px;font:500 11px/1.3 var(--f-mono);color:var(--soft)}.pf-leg span{display:inline-flex;align-items:center;gap:5px}.pf-leg i{width:10px;height:10px;border-radius:2px;display:inline-block}' +
  '.pf-sim{display:flex;flex-direction:column;gap:6px}.pf-gauge{display:flex;flex-direction:column;gap:6px}.pf-big{font:600 30px/1 var(--f-mono);color:var(--hi);letter-spacing:-.02em}.pf-big small{font-size:12px;color:var(--soft);font-weight:500;margin-left:4px}';
/* Typographie française sur les textes écrits ici : espace insécable avant : ; ? ! et devant % $, après « et nº. */
function typo(el) {
  if (!el || typeof document === 'undefined') return;
  var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, { acceptNode: function (n) { var p = n.parentNode; return p && /^(TEXTAREA|SCRIPT|STYLE|INPUT)$/.test(p.nodeName) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; } }), n;
  while ((n = w.nextNode())) { var t = n.nodeValue, u = P.typo(t); if (u !== t) n.nodeValue = u; }
}
P.typo = function (t) { return String(t).replace(/ ([:;?!»])/g, '\u202F$1').replace(/« /g, '«\u202F').replace(/(\d) (%|\$)/g, '$1\u00A0$2').replace(/nº /g, 'nº\u00A0').replace(/ — /g, '\u00A0— '); };
function injectCss() { if (document.getElementById('perf-css')) return; var s = document.createElement('style'); s.id = 'perf-css'; s.textContent = CSS; document.head.appendChild(s); }
P.injectCss = injectCss;
var UI = { hypOpen: false, open: {}, boot: { key: null, res: null }, sim: { key: null, trades: [] } };

function params(set) { var p = Object.assign({}, DEF_PAR, T.store.get(KEY.par, {})); if (!fin(p.cost)) p.cost = set.commissionRT; return p; }
function setParam(k, v) { var p = T.store.get(KEY.par, {}); p[k] = v; T.store.set(KEY.par, p); }

/* La source choisie, résolue en trades. */
function resolve(set, par) {
  var src = T.store.get(KEY.src, 'journal'), risk = set.riskPerTrade, bt = T.store.get('quant:lastBacktest', null), hasBt = !!(bt && Array.isArray(bt.trades) && bt.trades.length);
  var o = { src: src, trades: [], hasBt: hasBt, bt: bt, sim: false, dates: false, times: false, label: '' };
  if (src === 'backtest') { o.trades = hasBt ? P.fromBacktest(bt, risk) : []; o.label = hasBt ? 'Backtest « ' + (bt.label || 'sans nom') + ' »' : 'Backtest'; }
  else if (src === 'collage') { var ps = T.store.get(KEY.paste, { text: '', unit: 'usd' }), r = P.parseCsv(ps.text, ps.unit, risk, set.tz); o.trades = r.trades; o.parse = r; o.paste = ps; o.label = 'Collage'; o.dates = r.hasDates; o.times = r.hasTimes; }
  else if (src === 'sim') { var sm = Object.assign({}, DEF_SIM, T.store.get(KEY.sim, {})); o.simPar = sm; o.sim = true; o.label = 'Données simulées'; var so = { p: sm.p, b: sm.b, n: sm.n, seed: sm.seed, noise: sm.noise, cost: set.commissionRT, risk: risk, tpd: par.tpd, end: Date.now(), from: set.winFrom, to: set.winTo, tz: set.tz }, sk = JSON.stringify(Object.assign({}, so, { end: T.day.key() })); if (UI.sim.key !== sk) UI.sim = { key: sk, trades: P.simulate(so) }; o.trades = UI.sim.trades.map(function (t) { return Object.assign({}, t); }); }
  else { o.src = 'journal'; o.trades = P.fromJournal(T.journal.list(), risk); o.label = 'Journal'; }
  if (o.src !== 'collage') { o.dates = o.trades.length > 0 && o.trades.every(function (t) { return fin(t.at); }); o.times = o.dates; }
  return o;
}

function sourceCard(ctx, D, par) {
  var set = ctx.settings, body = [];
  var seg = U.seg({ aria: 'Source des trades', options: [{ v: 'journal', label: 'Journal' }, { v: 'backtest', label: 'Backtest' }, { v: 'collage', label: 'Collage' }, { v: 'sim', label: 'Simulées' }], value: D.src, onChange: function (v) { if (v === 'backtest' && !D.hasBt) return; T.store.set(KEY.src, v); ctx.rerender(); } });
  if (!D.hasBt) { var bb = seg.children[1]; bb.disabled = true; bb.setAttribute('aria-disabled', 'true'); bb.title = 'Aucun backtest enregistré'; }
  body.push(seg);
  var n = D.trades.length, line = h('div', { class: 'pf-srcline' });
  if (D.src === 'journal') line.appendChild(h('span', null, n ? [h('b', null, F.int(n) + ' trade' + (n > 1 ? 's' : '') + ' clos'), ' au journal' + (n ? ' · du ' + F.dateLong(D.trades[0].at) + ' au ' + F.dateLong(D.trades[n - 1].at) : '')] : 'Aucun trade clos au journal pour l’instant.'));
  else if (D.src === 'backtest') line.appendChild(h('span', null, D.hasBt ? [h('b', null, D.label), ' · ' + F.int(n) + ' trades'] : 'Aucun backtest enregistré.'));
  else if (D.src === 'collage') line.appendChild(h('span', null, n ? [h('b', null, F.int(n) + ' ligne' + (n > 1 ? 's' : '') + ' lue' + (n > 1 ? 's' : '')), D.parse.skipped.length ? ' · ' + D.parse.skipped.length + ' ignorée' + (D.parse.skipped.length > 1 ? 's' : '') + ' (ligne ' + D.parse.skipped[0].line + ' : « ' + D.parse.skipped[0].text + ' »)' : '', D.dates ? '' : ' · sans dates'] : 'Rien de lu pour l’instant.'));
  else line.appendChild(U.pill('données simulées, pas ton historique', 'acc'));
  line.appendChild(h('span', null, '1 R = ' + usd(set.riskPerTrade) + ' (réglages)'));
  body.push(line);
  if (!D.hasBt && D.src === 'backtest') body.push(U.note('Le desk Quant dépose ici son dernier backtest. Lance-en un, puis reviens.'));
  if (!D.hasBt && D.src !== 'backtest') body.push(U.note('Backtest grisé : aucun backtest enregistré. Le desk Quant y déposera son dernier résultat.'));
  if (D.src === 'collage') {
    var ps = D.paste, taId = 'pf-paste';
    body.push(U.field({ id: taId, type: 'textarea', full: true, label: 'Un CSV « date;pnl », ou une seule colonne de résultats', value: ps.text, placeholder: '2026-09-14 15:42;120\n2026-09-15;−80,5\n…', onChange: function (v) { var cur = T.store.get(KEY.paste, { text: '', unit: 'usd' }); cur.text = v; T.store.set(KEY.paste, cur); } }));
    body.push(h('div', { class: 'row' },
      h('div', { class: 'grow' }, U.seg({ aria: 'Unité des valeurs collées', options: [{ v: 'usd', label: 'En dollars' }, { v: 'r', label: 'En R' }], value: ps.unit || 'usd', onChange: function (v) { var cur = T.store.get(KEY.paste, { text: '', unit: 'usd' }); var ta = document.getElementById(taId); if (ta) cur.text = ta.value; cur.unit = v; T.store.set(KEY.paste, cur); ctx.rerender(); } })),
      U.button({ label: 'Lire le collage', kind: 'pri', small: true, onClick: function () { var ta = document.getElementById(taId), cur = T.store.get(KEY.paste, { text: '', unit: 'usd' }); cur.text = ta ? ta.value : cur.text; T.store.set(KEY.paste, cur); ctx.rerender(); } })));
    body.push(U.note('Séparateur point-virgule ou tabulation ; virgule décimale acceptée. Dates : 2026-09-14 15:42 ou 14/09/2026. Une seule colonne : pas de calendrier ni de carte horaire.'));
  }
  if (D.src === 'sim') {
    var sm = D.simPar, setSim = function (k, v) { var c = Object.assign({}, DEF_SIM, T.store.get(KEY.sim, {})); c[k] = v; T.store.set(KEY.sim, c); ctx.rerender(); };
    body.push(U.fields([
      { label: 'Taux de réussite', unit: '%', value: Math.round(sm.p * 1000) / 10, min: 1, max: 99, onChange: function (v) { setSim('p', v / 100); } },
      { label: 'R:R (gain / perte)', value: sm.b, min: 0.1, max: 20, onChange: function (v) { setSim('b', v); } },
      { label: 'Trades', value: sm.n, min: 10, max: 20000, onChange: function (v) { setSim('n', Math.round(v)); } },
      { label: 'Graine', value: sm.seed, min: 0, max: 4294967295, onChange: function (v) { setSim('seed', Math.round(v)); } },
      { label: 'Bruit d’exécution', unit: 'R', value: sm.noise, min: 0, max: 2, onChange: function (v) { setSim('noise', v); } }
    ], 3));
    var pe = 1 / (1 + sm.b);
    body.push(U.note('Issue +b R ou −1 R, plus un bruit gaussien, moins la commission. Équilibre à ce R:R : p = 1/(1 + b) = ' + F.pct(pe, 1) + (Math.abs(sm.p - pe) < 0.0005 ? ' — le tirage est sans avantage : tout ce que montrent les onglets est du bruit.' : '. Mets p à cette valeur pour voir ce que le bruit seul produit.'), true));
  }
  var det = h('details', { class: 'pf-hyp' });
  if (UI.hypOpen) det.setAttribute('open', '');
  det.addEventListener('toggle', function () { UI.hypOpen = det.open; });
  det.appendChild(h('summary', null, 'Hypothèses', h('span', null, nb(par.tpd, par.tpd % 1 ? 1 : 0) + ' trades/j × ' + F.int(par.days) + ' j · capital ' + usd(par.capital))));
  det.appendChild(U.fields([
    { label: 'Trades par jour', value: par.tpd, min: 0.1, max: 200, hint: 'pour annualiser', onChange: function (v) { setParam('tpd', v); ctx.rerender(); } },
    { label: 'Jours par an', value: par.days, min: 1, max: 366, hint: '252 jours de bourse', onChange: function (v) { setParam('days', Math.round(v)); ctx.rerender(); } },
    { label: 'Capital de référence', unit: '$', value: par.capital, min: 100, max: 1e9, full: true, hint: 'base des pourcentages, du drawdown en % et du TCAC', onChange: function (v) { setParam('capital', v); ctx.rerender(); } }
  ]));
  body.push(det);
  return U.card({ title: 'Source des trades', meta: { journal: 'journal', backtest: 'backtest', collage: 'collage', sim: 'simulation' }[D.src] || '', body: body });
}

function emptyFor(tab, D, ctx) {
  var what = { tableau: 'La feuille de score', distribution: 'La distribution', temps: 'Le temps', robustesse: 'La robustesse' }[tab] || 'Cet onglet';
  var why = D.src === 'journal' ? 'Aucun trade clos au journal. Inscris tes trades au journal (pris, puis clos avec leur P&L), ou choisis une autre source.'
    : D.src === 'backtest' ? 'Aucun backtest enregistré. Lance un backtest dans le desk Quant, colle un CSV, ou choisis les données simulées.'
    : D.src === 'collage' ? 'Rien n’a pu être lu. Colle un CSV « date;pnl » ou une colonne de résultats, puis touche « Lire le collage ».'
    : 'La simulation n’a produit aucun trade : augmente le nombre de trades.';
  if (D.trades.length === 1) why = 'Un seul trade : il en faut au moins deux pour mesurer une dispersion.';
  var acts = h('div', { class: 'row' },
    U.button({ label: 'Ouvrir le journal', small: true, onClick: function () { T.nav.go('journal'); } }),
    U.button({ label: 'Lancer un backtest', small: true, kind: 'ghost', onClick: function () { T.nav.go('quant'); } }),
    D.src !== 'collage' ? U.button({ label: 'Coller un CSV', small: true, kind: 'ghost', onClick: function () { T.store.set(KEY.src, 'collage'); ctx.rerender(); } }) : null,
    D.src !== 'sim' ? U.button({ label: 'Données simulées', small: true, kind: 'acc', onClick: function () { T.store.set(KEY.src, 'sim'); ctx.rerender(); } }) : null);
  return U.empty({ title: what + ' attend des trades', text: why, action: acts });
}

function simBanner(D) { return D.sim ? U.note('Données simulées, pas ton historique : ces chiffres décrivent le générateur réglé plus haut, jamais ta pratique.', true) : null; }

/* ---------- Onglet « tableau » ---------- */
function tabTableau(root, D, M) {
  root.appendChild(U.kpis([
    { label: 'Trades', value: F.int(M.n), hint: { journal: 'au journal', backtest: 'du backtest', collage: 'collés', sim: 'simulés' }[D.src] || '' },
    { label: 'Espérance', value: F.r(M.expR, 3), hint: usd(M.mean, true) + ' par trade', tone: M.expR < 0 ? 'neg' : null },
    { label: 'Sharpe an.', value: nb(M.sharpeAnn, 2), hint: 'par trade ' + nb(M.sharpe, 3) },
    { label: 'PSR', value: F.pct(M.psr, 1), hint: M.psr >= 0.95 ? 'au-delà de 95 %' : 'sous 95 % : bruit', tone: M.psr >= 0.95 ? 'acc' : null },
    { label: 'Drawdown max', value: usd(M.maxDD), hint: F.pct(M.maxDDpct, 2) + ' du pic', tone: 'neg' },
    { label: 'Facteur de profit', value: nb(M.pf, 2), hint: 'taux ' + F.pct(M.winRate, 1) }
  ], 3));
  var s = U.section('La feuille de *score*', 'touche une ligne');
  P.score(M).forEach(function (G) {
    var grp = h('div', { class: 'pf-grp' }, h('div', { class: 'pf-gh' }, G.title, h('span', null, G.rows.length + ' mesures')));
    G.rows.forEach(function (r) {
      var open = !!UI.open[r.k], def = h('div', { class: 'pf-def', hidden: !open || null },
        h('div', { class: 'lb' }, 'Définition exacte'), h('div', { class: 'pf-f' }, r.def),
        r.nul ? h('div', { class: 'lb' }, 'Loi nulle') : null, r.nul ? h('div', { class: 'nl' }, r.nul) : null);
      var pill = r.verdict === 'hors' ? U.pill('hors du bruit', 'acc') : r.verdict === 'contre' ? U.pill('contre toi', 'no') : r.verdict === 'bruit' ? U.pill('bruit') : null;
      var btn = h('button', { class: 'pf-row', type: 'button', 'aria-expanded': String(open), 'data-k': r.k },
        h('span', { class: 'n' }, r.name, pill), h('span', { class: 'v' }, r.v), h('span', { class: 'r' }, r.read));
      btn.addEventListener('click', function () { var o2 = btn.getAttribute('aria-expanded') !== 'true'; btn.setAttribute('aria-expanded', String(o2)); def.hidden = !o2; UI.open[r.k] = o2; });
      grp.appendChild(btn); grp.appendChild(def);
    });
    s.appendChild(grp);
  });
  s.appendChild(U.note('Les pastilles comparent chaque mesure à sa loi nulle, au seuil de 5 % : « bruit » veut dire qu’un opérateur sans avantage obtiendrait aussi souvent ce chiffre. Avant ' + F.int(P.MUR.decisions) + ' décisions, le journal décrit, il ne juge pas (ALP nº 3, partie VIII).'));
  root.appendChild(s);
}

/* ---------- Onglet « distribution » ---------- */
function tabDistribution(root, D, M) {
  var x = D.trades.map(function (t) { return t.pnl; }), fm = function (v) { return F.num(v, Math.abs(v) < 10 && v !== 0 ? 1 : 0); };
  var s1 = U.section('Les résultats, *et la normale*', 'P&L net par trade, en $');
  s1.appendChild(U.card({ body: [
    charts.histNormal({ values: x, fmt: fm, refs: [{ x: -M.var95h, label: 'VaR 95 % ' + usd(M.var95h), tone: 'violet', dash: true }, { x: -M.cvar95h, label: 'CVaR 95 % ' + usd(M.cvar95h), tone: 'mute' }] }),
    U.note('Barres grises : pertes ; blanches : gains. La courbe violette est la loi normale de même moyenne (' + usd(M.mean, true) + ') et même écart-type (' + usd(M.sd) + '), en effectifs attendus. Un stop et un objectif fixes donnent deux bosses qu’aucune normale ne décrit : c’est pourquoi la VaR gaussienne (' + usd(M.var95g) + ') et l’historique (' + usd(M.var95h) + ') divergent.')
  ] }));
  root.appendChild(s1);
  var s2 = U.section('Quantile-*quantile*', 'contre la normale');
  s2.appendChild(U.card({ body: [charts.qq({ values: x, fmt: fm }), U.note('Sous la normale, les points suivent la diagonale. Une queue gauche qui plonge sous la diagonale : des pertes plus lourdes que la normale ; une queue droite au-dessus : des gains plus grands. Asymétrie ' + nb(M.skew, 2) + ', kurtosis en excès ' + nb(M.exKurt, 2) + '.')] }));
  root.appendChild(s2);
  var s3 = U.section('Les quantiles', 'observés contre normale');
  s3.appendChild(U.table({ cols: [
    { k: 'q', label: 'Niveau', fmt: function (v) { return F.pct(v, 0); } },
    { k: 'obs', label: 'Observé', align: 'r', fmt: function (v) { return usd(v, true); } },
    { k: 'norm', label: 'Normale', align: 'r', fmt: function (v) { return usd(v, true); } },
    { k: 'gap', label: 'Écart', align: 'r', fmt: function (v) { return usd(v, true); } }
  ], rows: P.quantileTable(x) }));
  s3.appendChild(U.note('Quantiles empiriques interpolés linéairement ; normale : µ + σ·Φ⁻¹(niveau). Un écart négatif aux bas niveaux veut dire des pertes extrêmes plus grandes que la normale ne le prévoit.'));
  root.appendChild(s3);
}

/* ---------- Onglet « temps » ---------- */
function tabTemps(root, D, M, par, ctx) {
  var x = D.trades.map(function (t) { return t.pnl; }), Dd = M.D, cum = S.cumsum(x);
  var s1 = U.section('Capital *et creux*', 'cumul en $, trade après trade');
  var eq = [[0, 0]].concat(cum.map(function (v, i) { return [i + 1, v]; }));
  s1.appendChild(U.card({ body: [
    C.line({ series: [{ name: 'cumul', points: eq, tone: 'fg', area: true }], x: { fmt: function (v) { return F.int(v); } }, y: { fmt: function (v) { return usd(v); }, zero: true }, height: 200 }),
    C.line({ series: [{ name: 'sous le pic', points: [[0, 0]].concat(Dd.dd.map(function (d, i) { return [i + 1, -d]; })), tone: 'mute', area: true }], x: { fmt: function (v) { return F.int(v); } }, y: { fmt: function (v) { return usd(v); }, zero: true }, hlines: [{ y: -M.mddNull, tone: 'violet' }], height: 150 }),
    U.note('En haut, le cumul ; en bas, la courbe sous l’eau, distance au plus haut atteint. La ligne violette pointillée est le drawdown maximal qu’un opérateur sans avantage, à même volatilité, atteindrait en moyenne sur ' + F.int(M.n) + ' trades : √(π/2)·σ·√n = ' + usd(M.mddNull) + '. Le tien : ' + usd(M.maxDD) + '.')
  ] }));
  root.appendChild(s1);
  var w = Math.max(5, Math.min(Math.round(par.window), Math.max(5, M.n - 1)));
  var s2 = U.section('Sharpe et Sortino *glissants*', 'fenêtre de ' + w + ' trades');
  var roll = P.rolling(x, w), band = S.normPpf(0.975) / Math.sqrt(w);
  var c2 = [U.fields([{ label: 'Fenêtre glissante', unit: 'trades', value: par.window, min: 5, max: 1000, onChange: function (v) { setParam('window', Math.round(v)); ctx.rerender(); } }])];
  if (roll.length > 1) {
    c2.push(C.line({ series: [{ name: 'Sharpe', points: roll.map(function (r) { return [r.i, fin(r.sharpe) ? r.sharpe : null]; }), tone: 'fg' }, { name: 'Sortino', points: roll.map(function (r) { return [r.i, fin(r.sortino) ? Math.max(-3, Math.min(3, r.sortino)) : null]; }), tone: 'violet' }],
      x: { fmt: function (v) { return F.int(v); } }, y: { fmt: function (v) { return nb(v, 2); } }, bands: [{ y0: -band, y1: band }], hlines: [{ y: 0, tone: 'mute' }], height: 200 }));
    c2.push(U.note('Par trade, non annualisés ; le Sortino est borné à ±3 pour l’affichage. La bande violette est ±1,96/√' + w + ' = ±' + nb(band, 2) + ' : un opérateur sans avantage y laisse son Sharpe glissant 95 % du temps. Une sortie de bande isolée ne prouve rien, il y en a une sur vingt par construction.'));
  } else c2.push(U.note('Pas assez de trades pour une fenêtre de ' + w + '.'));
  s2.appendChild(U.card({ body: c2 }));
  root.appendChild(s2);
  var s3 = U.section('Le *calendrier*', 'P&L par jour, fuseau ' + ctx.settings.tz);
  if (D.dates) {
    var days = P.daily(D.trades, ctx.settings.tz), pos = days.filter(function (d) { return d.pnl > 0; }).length;
    s3.appendChild(U.card({ body: [charts.calendar({ days: days, fmt: usd }),
      h('div', { class: 'pf-leg' }, h('span', null, h('i', { style: 'background:var(--soft);opacity:.7' }), 'perte'), h('span', null, h('i', { style: 'background:var(--violet)' }), 'gain'), h('span', null, h('i', { style: 'border:1px solid var(--line)' }), 'sans trade'), h('span', null, 'intensité : racine du montant')),
      U.note(F.int(days.length) + ' jours tradés, ' + F.int(pos) + ' positifs (' + F.pct(pos / days.length, 0) + '). Semaines en colonnes, du lundi au dimanche.')] }));
  } else s3.appendChild(U.empty({ title: 'Pas de dates dans cette source', text: 'Le calendrier demande une date par trade : colle un CSV « date;pnl » plutôt qu’une seule colonne.' }));
  root.appendChild(s3);
  var s4 = U.section('Heure *et jour*', 'P&L moyen par case');
  if (D.dates && D.times) {
    var hw = P.hourWeek(D.trades, ctx.settings.tz), hl = hw.hours.map(function (hh) { return String(hh).padStart(2, '0') + ' h'; }), wl = hw.wds.map(function (d) { return JOURS[d]; });
    s4.appendChild(C.heat({ rows: hl, cols: wl, values: hw.mean, diverging: true, corner: 'heure', fmt: function (v) { return F.num(v, 0); } }));
    s4.appendChild(C.heat({ rows: hl, cols: wl, values: hw.count, corner: 'trades', fmt: function (v) { return F.int(v); } }));
    s4.appendChild(U.note('En haut, le P&L moyen en $ (violet : positif, gris : négatif) ; en bas, le nombre de trades par case. Une case de deux trades ne dit rien : lis toujours les deux cartes ensemble.' + (D.sim ? ' Sur données simulées, toute structure de cette carte est du bruit : c’est exactement ce que la loi nulle produit.' : '')));
  } else s4.appendChild(U.empty({ title: 'Pas d’heures dans cette source', text: D.dates ? 'Les dates collées ne portent pas d’heure : ajoute-la (2026-09-14 15:42) pour obtenir la carte.' : 'Il faut une date et une heure par trade.' }));
  root.appendChild(s4);
}

/* ---------- Onglet « espaces » ---------- */
function tabEspaces(root, D, M, par, ctx) {
  var set = ctx.settings, kind = T.store.get(KEY.surf, 'esperance'), view = T.store.get(KEY.view, '3d');
  if (P.SURF_KINDS.indexOf(kind) < 0) kind = 'esperance';
  var hasPt = M && M.n >= 2 && fin(M.payoff) && fin(M.winRate);
  var bK = hasPt ? Math.max(0.2, Math.min(10, M.payoff)) : 2;
  var o = { risk: set.riskPerTrade, cost: par.cost, objectif: par.objectif, perteMax: par.perteMax, nYear: par.tpd * par.days, bKelly: bK };
  var user = null;
  if (hasPt) user = kind === 'kelly' ? { x: set.riskPerTrade / par.capital, y: M.winRate, label: 'toi' } : { x: M.payoff, y: M.winRate, label: 'toi' };
  var names = { esperance: 'Espérance', kelly: 'Kelly', ruine: 'Ruine', sharpe: 'Sharpe' };
  var s = U.section('L’espace *des paramètres*', 'formes fermées');
  s.appendChild(U.chips({ options: P.SURF_KINDS.map(function (k) { return { v: k, label: names[k] }; }), value: kind, onChange: function (v) { T.store.set(KEY.surf, v); ctx.rerender(); } }));
  s.appendChild(U.seg({ aria: 'Rendu', options: [{ v: '2d', label: 'Carte 2D' }, { v: '3d', label: 'Relief 3D' }], value: view, onChange: function (v) { T.store.set(KEY.view, v); ctx.rerender(); } }));
  var sf = view === '2d' ? P.surface(kind, o, 96, 96, true) : P.surface(kind, o, 29, 29, false);
  var c = o.cost / o.risk, A = o.perteMax, B = o.objectif;
  var formula = {
    esperance: 'E[R] = p·b − (1 − p) − c, c = coût / risque = ' + usd(o.cost) + ' / ' + usd(o.risk) + ' = ' + nb(c, 4) + ' R. Équilibre : p* = (1 + c)/(1 + b).',
    kelly: 'g(f) = p·ln(1 + f·b) + (1 − p)·ln(1 − f), b = ' + nb(bK, 2) + (hasPt ? ' (ton payoff)' : ' (sans source, b = 2)') + '. Crête : f* = p − (1 − p)/b ; au-delà de 2f*, la croissance devient négative.',
    ruine: 'P(objectif avant perte max) = (1 − e^(−2µa/σ²)) / (1 − e^(−2µ(a+b)/σ²)), a = perte max ' + usd(A) + ', b = objectif ' + usd(B) + ', µ = risque·(p·R:R − (1 − p)) − coût, σ² = p(1 − p)·((R:R + 1)·risque)². Ruine = 1 − P. À dérive nulle : P = a/(a + b) = ' + F.pct(A / (A + B), 0) + ', donc ruine = ' + F.pct(B / (A + B), 0) + ', quelle que soit la géométrie.',
    sharpe: 'SR_an = (p·b − (1 − p) − c) / ((b + 1)·√(p(1 − p))) × √(trades par an), trades par an = ' + F.int(o.nYear) + '. Nul sur la ligne d’équilibre.'
  }[kind];
  var lede = {
    esperance: 'Ce que rapporte un trade, en R, pour chaque couple taux de réussite × R:R. Tout ce qui est sous la ligne pointillée perd de l’argent, quel que soit le talent qu’on croit y mettre.',
    kelly: 'Le taux de croissance du capital par trade selon la fraction risquée. Il monte jusqu’à la crête f*, puis redescend : risquer trop détruit un avantage réel.',
    ruine: 'La probabilité de toucher la perte maximale du compte avant l’objectif, pour une marche à dérive tirée de p, du R:R et du risque par trade (approximation de diffusion). Ici, le blanc est la ruine presque certaine.',
    sharpe: 'Le Sharpe annualisé qu’un système stationnaire produirait à chaque couple : il montre combien la même espérance pèse différemment selon la géométrie.'
  }[kind];
  var vis = view === '2d' ? charts.heatmap2d({ surf: sf, user: user }) : charts.surface3d({ surf: sf, user: user });
  var read = [];
  if (hasPt) {
    var zu = sf.fn(user.x, user.y), pe = P.seuilEquilibre(M.payoff, c);
    read.push(h('div', { class: 'pf-srcline' }, h('span', null, 'Ton point : '), h('b', null, kind === 'kelly' ? 'f = ' + F.pct(user.x, 2) + ' · p = ' + F.pct(user.y, 1) : 'R:R ' + nb(user.x, 2) + ' · p = ' + F.pct(user.y, 1)), h('span', null, '→ ' + sf.z.name + ' ' + sf.z.fmt(zu))));
    if (kind !== 'kelly') read.push(U.note('À ton R:R, le taux d’équilibre vaut ' + F.pct(pe, 1) + ' ; ton taux mesuré ' + (M.winRate > pe ? 'le dépasse de ' : 'lui manque de ') + nb(Math.abs(M.winRate - pe) * 100, 1) + ' points. Intervalle de Wilson : ' + F.pct(M.wilson.lo, 1) + ' à ' + F.pct(M.wilson.hi, 1) + '.' + (user.x > sf.x.dom[1] || user.x < sf.x.dom[0] ? ' Ton R:R sort du cadre : le point est posé au bord.' : '')));
    else read.push(U.note('Crête à ton taux : f* = ' + F.pct(Math.max(0, P.kellyF(M.winRate, bK)), 1) + ' du capital. Ton risque déclaré : ' + F.pct(user.x, 2) + '.'));
  } else read.push(U.note('Ton point apparaîtra sur la surface quand la source contiendra au moins deux trades, dont un gain et une perte.'));
  s.appendChild(U.card({ title: sf.title, meta: view === '2d' ? 'carte 2D' : 'relief 3D', body: [h('p', { class: 'note', style: 'margin:0' }, lede), vis].concat(read).concat([h('div', { class: 'pf-f' }, formula)]) }));
  var flds = [{ label: 'Coût par trade', unit: '$', value: par.cost, min: 0, max: 1000, hint: 'commission aller-retour + glissement', onChange: function (v) { setParam('cost', v); ctx.rerender(); } }];
  if (kind === 'ruine') flds.push({ label: 'Perte max du compte', unit: '$', value: par.perteMax, min: 10, max: 1e7, onChange: function (v) { setParam('perteMax', v); ctx.rerender(); } }, { label: 'Objectif', unit: '$', value: par.objectif, min: 10, max: 1e7, onChange: function (v) { setParam('objectif', v); ctx.rerender(); } });
  s.appendChild(U.fields(flds));
  if (kind === 'ruine') s.appendChild(U.note('Perte max et objectif sont des valeurs de départ arbitraires, à remplacer par celles de ton compte (règles de prop firm : à vérifier auprès de la firme). Risque par trade : ' + usd(o.risk) + ', dans les réglages.', true));
  s.appendChild(U.note(view === '3d' ? 'Le relief s’ouvre avec son maximum au fond (règle des surfaces d’ALP) ; teinte et taille des points suivent la hauteur ; la ligne pointillée au sol est l’équilibre. Échelle : gris sous l’équilibre, violet à l’équilibre, blanc au sommet.' : 'Échelle : gris sous l’équilibre, violet à l’équilibre, blanc au sommet. Touche la carte pour lire la valeur exacte, calculée et non interpolée.'));
  root.appendChild(s);
}

/* ---------- Onglet « robustesse » ---------- */
function tabRobustesse(root, D, M, par, ctx) {
  var n = M.n, wall = P.MUR.decisions, prog = Math.min(1, n / wall);
  var call = U.callout([h('div', { class: 'pf-gauge' },
    h('div', { class: 'pf-big' }, F.int(n), h('small', null, '/ ' + F.int(wall) + ' décisions')),
    C.gauge({ value: n, min: 0, max: wall, ticks: [[0, '0'], [Math.round(wall / 2), F.int(Math.round(wall / 2))], [wall, F.int(wall)]] }),
    h('div', null, h('b', null, 'Avant ' + F.int(wall) + ' décisions, le journal décrit, il ne juge pas. '), 'C’est ce qu’il faut pour distinguer de zéro un Sharpe de 0,10 par décision, au seuil de 5 % avec 80 % de puissance' + (prog >= 1 ? ' : tu as franchi le mur, les verdicts deviennent lisibles.' : ' : il t’en manque ' + F.int(wall - n) + '.')))]);
  root.appendChild(call);
  root.appendChild(U.note('Source : ' + P.MUR.source + '. Contrôle : ⌈((z₀,₉₅ + z₀,₈₀)/0,10)²⌉ = ' + F.int(P.decisionsPourSharpe(0.10)) + '.'));
  var s1 = U.section('PSR et DSR, *simplement*', 'Bailey et López de Prado');
  s1.appendChild(U.kpis([
    { label: 'PSR', value: F.pct(M.psr, 1), hint: 'P(vrai Sharpe > 0)', tone: M.psr >= 0.95 ? 'acc' : null },
    { label: 'DSR', value: F.pct(M.dsr, 1), hint: F.int(par.trials) + ' essais', tone: M.dsr >= 0.95 ? 'acc' : null },
    { label: 'MinTRL', value: fin(M.minTRL) ? F.int(Math.ceil(M.minTRL)) : '∞', unit: 'trades', hint: 'tu en as ' + F.int(n) }
  ], 3));
  s1.appendChild(U.prose([
    '<b>Le PSR</b> répond à une seule question : avec ' + T.esc(F.int(n)) + ' trades de cette forme, quelle est la probabilité que ton vrai Sharpe soit au-dessus de zéro ? Il pénalise l’asymétrie négative et les queues épaisses, qui rendent un Sharpe moins fiable à valeur égale.',
    '<b>Le DSR</b> retire en plus ce que la sélection explique seule. Si tu as essayé ' + T.esc(F.int(par.trials)) + ' réglages et gardé le meilleur, le hasard t’aurait déjà donné un Sharpe de ' + T.esc(nb(M.sr0, 3)) + ' par trade : c’est cette barre, et non zéro, que ton résultat doit franchir.',
    '<b>La règle :</b> un résultat se déclare au-delà de 95 %. Au-dessous, il n’est pas faux : il n’est pas encore prouvé.'
  ]));
  s1.appendChild(U.fields([
    { label: 'Variantes essayées (N)', value: par.trials, min: 1, max: 1e6, hint: 'chaque réglage testé compte', onChange: function (v) { setParam('trials', Math.max(1, Math.round(v))); ctx.rerender(); } },
    { label: 'Graine du bootstrap', value: par.seed, min: 0, max: 4294967295, hint: 'même graine, mêmes tirages', onChange: function (v) { setParam('seed', Math.round(v)); ctx.rerender(); } }
  ]));
  root.appendChild(s1);
  var s2 = U.section('Le Sharpe *rééchantillonné*', '2 000 tirages');
  var box = h('div', { style: 'display:flex;flex-direction:column;gap:12px' });
  s2.appendChild(box); root.appendChild(s2);
  var x = D.trades.map(function (t) { return t.pnl; }), block = P.blockLength(M.rho1);
  if (!fin(block)) block = 1;
  var hs = 0; for (var i = 0; i < x.length; i++) hs = (hs * 31 + Math.round(x[i] * 100)) % 1000000007;
  var key = x.length + ':' + hs + ':' + par.seed + ':' + block.toFixed(4);
  function fill(res) {
    if (!box.isConnected) return; T.clear(box); setTimeout(function () { typo(box); }, 0);
    var q = function (a, p) { return S.quantile(a, p); }, lo = q(res.boot, 0.025), hi = q(res.boot, 0.975), le0 = 0;
    for (var k = 0; k < res.boot.length; k++) if (res.boot[k] <= 0) le0++;
    var ge = 0; for (var k2 = 0; k2 < res.nul.length; k2++) if (res.nul[k2] >= M.sharpe) ge++;
    var pv = (ge + 1) / (res.nul.length + 1);
    box.appendChild(U.kpis([
      { label: 'IC 95 % du Sharpe', value: nb(lo, 2), unit: 'à ' + nb(hi, 2), hint: 'observé ' + nb(M.sharpe, 3) },
      { label: 'P(Sharpe ≤ 0)', value: F.pct(le0 / res.boot.length, 1), hint: 'part des rééchantillons', tone: le0 / res.boot.length > 0.05 ? 'neg' : 'acc' },
      { label: 'p-valeur nulle', value: F.num(pv, 3), hint: 'Sharpe centré ≥ observé', tone: pv < 0.05 ? 'acc' : null },
      { label: 'Bloc moyen', value: nb(res.block, 1), unit: 'trades', hint: 'ρ₁ = ' + nb(M.rho1, 2) }
    ], 4));
    box.appendChild(U.card({ title: 'Ce que tes trades rééchantillonnés donnent', meta: 'Sharpe par trade', body: [charts.histNormal({ values: res.boot, normal: false, split: false, countLabel: 'tirage', fmt: function (v) { return nb(v, 2); }, refs: [{ x: M.sharpe, label: 'observé ' + nb(M.sharpe, 3), tone: 'violet' }, { x: lo, label: 'IC 95 % : ' + nb(lo, 2) + ' à ' + nb(hi, 2), tone: 'mute', dash: true }, { x: hi, tone: 'mute', dash: true }, { x: 0, label: 'zéro', tone: 'fg' }] }),
      U.note('Chaque tirage recolle des blocs de trades consécutifs de longueur géométrique (moyenne ' + nb(res.block, 1) + ', tirée de l’autocorrélation d’ordre 1), ce qui garde la dépendance que le bootstrap simple détruirait. Si l’intervalle contient zéro, ton Sharpe n’en est pas séparé.')] }));
    box.appendChild(U.card({ title: 'La loi nulle : les mêmes trades, sans avantage', meta: 'espérance retirée', body: [charts.histNormal({ values: res.nul, normal: false, split: false, countLabel: 'tirage', fmt: function (v) { return nb(v, 2); }, refs: [{ x: M.sharpe, label: 'ton Sharpe ' + nb(M.sharpe, 3), tone: 'violet' }, { x: 0, label: 'zéro', tone: 'fg' }] }),
      U.note('Mêmes trades, même dépendance, même forme, mais centrés sur zéro : voilà ce qu’un opérateur sans avantage obtient avec ta distribution. La p-valeur est la part de ces tirages qui font au moins aussi bien que toi : ' + F.num(pv, 3) + '.')] }));
    var md = res.mdd;
    box.appendChild(U.kpis([
      { label: 'Drawdown observé', value: usd(M.maxDD), hint: 'un seul chemin' },
      { label: 'Médiane bootstrap', value: usd(q(md, 0.5)), hint: 'chemin typique' },
      { label: 'Bootstrap 95 %', value: usd(q(md, 0.95)), hint: 'à prévoir', tone: 'neg' }
    ], 3));
    box.appendChild(U.note('Le drawdown que tu as vécu n’est qu’un ordre parmi d’autres de tes propres trades. Le 95ᵉ centile du bootstrap est le creux que le même jeu de trades produit une fois sur vingt : c’est lui qu’un compte doit pouvoir encaisser.'));
  }
  if (UI.boot.key === key && UI.boot.res) fill(UI.boot.res);
  else {
    box.appendChild(U.note('Calcul du bootstrap en cours…'));
    T.compute(P.bootstrap, { x: x, B: 2000, block: block, seed: par.seed }).then(function (res) { UI.boot = { key: key, res: res }; fill(res); }, function (e) { if (box.isConnected) { T.clear(box); box.appendChild(U.note('Le calcul a échoué : ' + (e && e.message || e), true)); } });
  }
}

T.desk({
  id: 'perf', label: 'Métriques & espaces', glyph: 'Σ', group: 'Recherche', order: 55,
  tabs: [{ id: 'tableau', label: 'Tableau' }, { id: 'distribution', label: 'Distribution' }, { id: 'temps', label: 'Temps' }, { id: 'espaces', label: 'Espaces' }, { id: 'robustesse', label: 'Robustesse' }],
  render: function (root, ctx) {
    injectCss();
    var set = ctx.settings, par = params(set), tab = ctx.tab || 'tableau', D = resolve(set, par);
    root.appendChild(U.page({ kicker: 'Recherche · métriques & espaces', title: 'Chaque chiffre, *et son bruit*.', lede: 'Les mesures de performance usuelles, chacune avec sa définition exacte et, quand elle existe, sa loi nulle : ce qu’un opérateur sans avantage aurait obtenu sur le même nombre de trades.' }));
    root.appendChild(U.tabs({ tabs: this.tabs, value: tab, onChange: ctx.setTab }));
    root.appendChild(sourceCard(ctx, D, par));
    var M = P.metrics(D.trades, { tpd: par.tpd, days: par.days, capital: par.capital, risk: set.riskPerTrade, trials: par.trials, tz: set.tz });
    var ban = simBanner(D); if (ban && tab !== 'espaces') root.appendChild(ban);
    if (tab === 'espaces') tabEspaces(root, D, M, par, ctx);
    else if (D.trades.length < 2) root.appendChild(emptyFor(tab, D, ctx));
    else if (tab === 'distribution') tabDistribution(root, D, M);
    else if (tab === 'temps') tabTemps(root, D, M, par, ctx);
    else if (tab === 'robustesse') tabRobustesse(root, D, M, par, ctx);
    else tabTableau(root, D, M);
    typo(root);
    var un1 = T.journal.on(function () { if (T.store.get(KEY.src, 'journal') === 'journal') ctx.rerender(); });
    var un2 = T.store.on('quant:lastBacktest', function () { ctx.rerender(); });
    return function () { un1(); un2(); };
  }
});
