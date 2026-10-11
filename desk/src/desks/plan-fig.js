/* Figures du desk Plan : des planches SVG calculées, jamais des données de marché.
   – VWAP « comme sur le graphique » : une séance synthétique (barres de 5 min, volume en U avec le pic de l’ouverture
     américaine), la VWAP ancrée à minuit et ses bandes ±1σ et ±2σ calculées sur cette séance ; les points marqués sont
     trouvés par une règle (premier contact de la bande), jamais posés à la main.
   – Footprint chiffré : cellules bid × ask, delta et volume de chaque barre calculés à partir des cellules.
   – Carte de liquidité : le carnet dans le temps (heatmap), un mur de liquidité et sept issues possibles.
   – Profil de volume : histogramme d’une séance synthétique, HVN et LVN détectés par une règle.
   – Frise du jour : les fenêtres interdites calculées depuis les annonces saisies.
   Tous les prix et volumes sont des illustrations ; chaque planche le dit. */
var F = T.fmt;
T.lib = T.lib || {};
var G = T.lib.planFig = {};
var E = function (t) { return T.esc(t); };
function fin(v) { return typeof v === 'number' && isFinite(v); }
function r1(v) { return Math.round(v * 10) / 10; }
function normal(r) { var u = r() || 1e-12, v = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }
G.DISCLAIMER = 'Illustration : prix et volumes inventés pour montrer la forme, pas une séance réelle.';

/* ===================================================================
   1. VWAP réaliste
   =================================================================== */
/* Une séance de 00:00 à 22:00 (heure de Paris) en barres de 5 minutes. Volume en U, ouverture européenne à 9 h,
   pic à 15 h 30 (ouverture du cash américain) ; la volatilité suit le volume. drift en points par barre, choc à 15 h 30. */
G.session = function (seed, o) {
  o = o || {};
  var r = T.rng(seed), n = 264, bars = [], p = o.p0 || 31000, cv = 0, cpv = 0, cp2v = 0;
  for (var i = 0; i < n; i++) {
    var hr = i / 12, vol = 0.35 + (hr >= 8 ? 0.5 : 0) + (hr >= 9 ? 0.4 : 0) + (hr >= 14.5 ? 0.5 : 0) + (hr >= 15.5 ? 2.6 * Math.exp(-(hr - 15.5) / 0.6) + 0.6 : 0) + (hr >= 21.5 ? 0.5 : 0);
    vol *= 0.8 + 0.4 * r();
    var sd = (o.sd || 2.2) * Math.sqrt(vol), drift = (o.drift || 0) * (hr >= (o.driftFrom || 0) ? 1 : 0);
    var op = p, hi = p, lo = p;
    for (var k = 0; k < 5; k++) { p += drift / 5 + normal(r) * sd / Math.sqrt(5); if (o.shock && i === 186 && k === 0) p += o.shock; hi = Math.max(hi, p); lo = Math.min(lo, p); }
    var tp = (hi + lo + p) / 3, v = vol * 100;
    cv += v; cpv += tp * v; cp2v += tp * tp * v;
    var vw = cpv / cv, sg = Math.sqrt(Math.max(0, cp2v / cv - vw * vw));
    bars.push({ i: i, t: i * 5, o: op, h: hi, l: lo, c: p, v: v, vwap: vw, sd: sg });
  }
  return bars;
};
/* Règles de recherche : la première graine (à partir de base) dont la séance vérifie la condition. Déterministe. */
G.find = function (base, o, cond, max) { for (var s = base; s < base + (max || 600); s++) { var b = G.session(s, o); var m = cond(b); if (m) return { seed: s, bars: b, m: m }; } return null; };
G.FROM = 108; /* 09:00 */
G.touch = function (bars, k, side, from) { for (var i = from || G.FROM + 6; i < bars.length; i++) { var b = bars[i], band = b.vwap + side * k * b.sd; if (side < 0 ? b.l <= band : b.h >= band) return i; } return -1; };
G.backToVwap = function (bars, i0, side) { for (var i = i0 + 1; i < bars.length; i++) { var b = bars[i]; if (side < 0 ? b.h >= b.vwap : b.l <= b.vwap) return i; } return -1; };
/* Un rebond propre : l’extrême de la séance dessinée tombe l’après-midi, au-delà de la bande ; le prix revient ensuite
   à la VWAP (au moins vingt minutes plus tard) sans toucher la bande opposée. */
G.rebond = function (b, k, side) {
  var i = -1, ext = side < 0 ? Infinity : -Infinity;
  for (var q = G.FROM; q < b.length; q++) { var v = side < 0 ? b[q].l : b[q].h; if (side < 0 ? v < ext : v > ext) { ext = v; i = q; } }
  if (i < 144 || i > 228) return null;
  var band = b[i].vwap + side * k * b[i].sd; if (side < 0 ? ext > band : ext < band) return null;
  var j = G.backToVwap(b, i, side); if (j < 0 || j - i < 4 || G.touch(b, k, -side, i) >= 0) return null;
  return { i: i, j: j };
};
G.SCEN = {
  achat: function (k) { return G.find(11, { drift: 0 }, function (b) { return G.rebond(b, k, -1); }, 3000); },
  vente: function (k) { return G.find(2011, { drift: 0 }, function (b) { return G.rebond(b, k, 1); }, 3000); },
  attendre: function (k) { return G.find(411, { drift: 0.55, driftFrom: 9 }, function (b) { if (G.touch(b, k, -1, G.FROM) >= 0) return null; var up = 0, n = 0; for (var i = 150; i < b.length; i++) { n++; if (b[i].c > b[i].vwap) up++; } return up / n > 0.9 ? { up: up / n } : null; }); },
  neutre: function (k) { return G.find(611, { drift: 0, sd: 1.6 }, function (b) { if (G.touch(b, 2, -1, G.FROM) >= 0 || G.touch(b, 2, 1, G.FROM) >= 0) return null; var x = 0; for (var i = G.FROM + 1; i < b.length; i++) if ((b[i].c - b[i].vwap) * (b[i - 1].c - b[i - 1].vwap) < 0) x++; return x >= 8 ? { x: x } : null; }); },
  ouverture: function (k) { return G.find(811, { drift: 0, shock: -55 }, function (b) { var i = G.touch(b, k, -1, 186); if (i < 0 || i > 200) return null; var j = G.backToVwap(b, i, -1); return { i: i, j: j }; }); }
};
/* Les scénarios coûtent jusqu’à une demi-seconde de recherche : calculés une fois par bande. */
var SC_CACHE = {};
G.scen = function (name, k) { var key = name + ':' + k; if (!(key in SC_CACHE)) SC_CACHE[key] = G.SCEN[name] ? G.SCEN[name](k) : null; return SC_CACHE[key]; };
var VW = 320, VH = 200;
G.vwapSvg = function (sc, o) {
  o = o || {};
  var bars = sc.bars.slice(G.FROM), k = o.k || 2, n = bars.length, x0 = 6, x1 = VW - 40, y0 = 14, y1 = VH - 22;
  var lo = Infinity, hi = -Infinity;
  bars.forEach(function (b) { lo = Math.min(lo, b.l, b.vwap - 2.15 * b.sd); hi = Math.max(hi, b.h, b.vwap + 2.15 * b.sd); });
  var X = function (i) { return +(x0 + (i + 0.5) / n * (x1 - x0)).toFixed(1); }, Y = function (p) { return +(y0 + (hi - p) / (hi - lo) * (y1 - y0)).toFixed(1); };
  var g = '<rect x="0" y="0" width="' + VW + '" height="' + VH + '" fill="var(--ink)" rx="6"/>';
  [12, 15, 18, 21].forEach(function (hh) { var i = hh * 12 - G.FROM; if (i < 0 || i >= n) return; g += '<line x1="' + X(i) + '" x2="' + X(i) + '" y1="' + y0 + '" y2="' + y1 + '" stroke="var(--line)"/><text class="pl-t" x="' + X(i) + '" y="' + (VH - 7) + '" text-anchor="middle">' + hh + ':00</text>'; });
  if (o.zone) { var zi = o.zone.i - G.FROM; g += '<rect x="' + X(Math.max(0, zi - 4)) + '" y="' + y0 + '" width="' + (X(Math.min(n - 1, zi + 4)) - X(Math.max(0, zi - 4))) + '" height="' + (y1 - y0) + '" fill="var(--violet-a)"/>'; }
  var line = function (f, cls) { return '<path d="' + bars.map(function (b, i) { return (i ? 'L' : 'M') + X(i) + ',' + Y(f(b)); }).join(' ') + '" fill="none" ' + cls + '/>'; };
  [-2, -1, 1, 2].forEach(function (m) { var on = Math.abs(m) === k; g += line(function (b) { return b.vwap + m * b.sd; }, 'stroke="' + (on ? 'var(--soft)' : 'var(--line-2)') + '" stroke-width="' + (on ? 1.2 : 0.9) + '"'); });
  bars.forEach(function (b, i) { g += '<line x1="' + X(i) + '" x2="' + X(i) + '" y1="' + Y(b.h) + '" y2="' + Y(b.l) + '" stroke="var(--soft)" stroke-width="1" opacity=".85"/>'; });
  g += line(function (b) { return b.vwap; }, 'stroke="var(--hi)" stroke-width="2"');
  var last = bars[n - 1], lab = [['VWAP', last.vwap, 'w'], ['+1σ', last.vwap + last.sd, ''], ['+2σ', last.vwap + 2 * last.sd, ''], ['−1σ', last.vwap - last.sd, ''], ['−2σ', last.vwap - 2 * last.sd, '']];
  lab.sort(function (a, b) { return b[1] - a[1]; }); var prev = -99;
  lab.forEach(function (l) { var y = Math.max(prev + 11, Y(l[1]) + 3.5); prev = y; g += '<text class="pl-t' + (l[2] ? ' w' : '') + '" x="' + (x1 + 4) + '" y="' + y + '">' + l[0] + '</text>'; });
  (o.marks || []).forEach(function (m) {
    var i = m.i - G.FROM; if (i < 0 || i >= n) return; var b = bars[i], py = m.at === 'h' ? b.h : m.at === 'l' ? b.l : b.c, x = X(i), y = Y(py);
    g += '<circle cx="' + x + '" cy="' + y + '" r="4.5" fill="none" stroke="var(--violet)" stroke-width="1.8"/>';
    var ty = m.pos === 'b' ? y + 16 : y - 9, tx = x, anchor = x > VW * 0.62 ? 'end' : x < VW * 0.25 ? 'start' : 'middle';
    if (ty < 11 || ty > VH - 26) { ty = y + 3.5; anchor = x > 90 ? 'end' : 'start'; tx = x > 90 ? x - 8 : x + 8; }
    g += '<text class="pl-t v" x="' + tx + '" y="' + ty + '" text-anchor="' + anchor + '">' + E(m.label) + '</text>';
  });
  return '<svg class="pl-svg" viewBox="0 0 ' + VW + ' ' + VH + '" role="img" aria-label="' + E(o.aria || 'VWAP et bandes') + '">' + g + '</svg>';
};

/* ===================================================================
   2. Footprint chiffré
   =================================================================== */
/* bars : [{ label, rows: [[prix, bid, ask, marque?]...] du haut vers le bas, open, close }]. Le delta (ask − bid) et le
   volume se calculent ; rien n’est écrit à la main sous la barre. marque : 1 cellule entourée, 2 déséquilibre. */
G.fpStats = function (rows) { var b = 0, a = 0; rows.forEach(function (r) { b += r[1]; a += r[2]; }); return { bid: b, ask: a, delta: a - b, vol: a + b }; };
G.fpSvg = function (o) {
  var bars = o.bars, nb = bars.length, rowH = 16, top = -Infinity, bot = Infinity;
  bars.forEach(function (b) { b.rows.forEach(function (r) { top = Math.max(top, r[0]); bot = Math.min(bot, r[0]); }); });
  var step = o.step || 1, nr = Math.round((top - bot) / step) + 1, axisW = 40, y0 = 22, W = 256, colW = (W - axisW - 4) / nb, H = y0 + nr * rowH + (o.zone ? 46 : 34);
  var Y = function (p) { return y0 + Math.round((top - p) / step) * rowH; }, maxV = 1;
  bars.forEach(function (b) { b.rows.forEach(function (r) { maxV = Math.max(maxV, r[1], r[2]); }); });
  var g = '<rect x="0" y="0" width="' + W + '" height="' + H + '" fill="var(--ink)" rx="6"/>';
  if (o.zone) { var zy0 = Y(o.zone[1]), zy1 = Y(o.zone[0]) + rowH; g += '<rect x="0" y="' + zy0 + '" width="' + W + '" height="' + (zy1 - zy0) + '" fill="var(--violet-a)"/><rect x="6" y="' + (H - 15) + '" width="10" height="8" fill="var(--violet-a)" stroke="var(--violet-b)"/><text class="pl-t v" x="20" y="' + (H - 7) + '">' + E((o.zoneLabel || 'zone') + ' : ' + o.zone[0] + '–' + o.zone[1]) + '</text>'; }
  for (var q = 0; q < nr; q++) { var pp = top - q * step; g += '<text class="pl-t" x="' + (axisW - 5) + '" y="' + (y0 + q * rowH + 11.5) + '" text-anchor="end">' + E(String(pp)) + '</text>'; }
  bars.forEach(function (b, j) {
    var cx = axisW + colW * j + colW / 2, half = colW / 2 - 6, st = G.fpStats(b.rows);
    var po = b.open, pc = b.close, up = pc >= po;
    var hiP = Math.max.apply(null, b.rows.map(function (r) { return r[0]; })), loP = Math.min.apply(null, b.rows.map(function (r) { return r[0]; }));
    g += '<line x1="' + (cx - half - 3) + '" x2="' + (cx - half - 3) + '" y1="' + Y(hiP) + '" y2="' + (Y(loP) + rowH) + '" stroke="var(--soft)"/>';
    g += '<rect x="' + (cx - half - 5) + '" y="' + Y(Math.max(po, pc)) + '" width="4" height="' + (Math.abs(Y(po) - Y(pc)) + rowH) + '" fill="' + (up ? 'var(--violet)' : 'var(--soft)') + '"/>';
    b.rows.forEach(function (r) {
      var y = Y(r[0]), ob = 0.08 + 0.55 * r[1] / maxV, oa = 0.08 + 0.55 * r[2] / maxV;
      g += '<rect x="' + (cx - half) + '" y="' + (y + 1) + '" width="' + half + '" height="' + (rowH - 2) + '" fill="var(--soft)" fill-opacity="' + ob.toFixed(2) + '"/>';
      g += '<rect x="' + cx + '" y="' + (y + 1) + '" width="' + half + '" height="' + (rowH - 2) + '" fill="var(--violet)" fill-opacity="' + oa.toFixed(2) + '"/>';
      g += '<text class="pl-n" x="' + (cx - 4) + '" y="' + (y + 11.5) + '" text-anchor="end">' + r[1] + '</text><text class="pl-n" x="' + (cx + 4) + '" y="' + (y + 11.5) + '">' + r[2] + '</text>';
      if (r[3]) g += '<rect x="' + (r[3] === 2 ? cx : cx - half) + '" y="' + (y + 0.5) + '" width="' + (r[3] === 2 ? half : 2 * half) + '" height="' + (rowH - 1) + '" fill="none" stroke="var(--hi)" stroke-width="1.3" rx="2"/>';
    });
    g += '<text class="pl-t w" x="' + cx + '" y="14" text-anchor="middle">' + E(b.label) + '</text>';
    var yb = y0 + nr * rowH + 13;
    g += '<text class="pl-t' + (st.delta < 0 ? '' : ' v') + '" x="' + cx + '" y="' + yb + '" text-anchor="middle">Δ ' + (st.delta > 0 ? '+' : st.delta < 0 ? '−' : '') + Math.abs(st.delta) + '</text>';
    g += '<text class="pl-t" x="' + cx + '" y="' + (yb + 12) + '" text-anchor="middle">vol ' + st.vol + '</text>';
  });
  return '<svg class="pl-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + E(o.aria || 'footprint') + '">' + g + '</svg>';
};
/* Les footprints types. Prix au point, de haut en bas. Colonne gauche : vendu au bid ; droite : acheté à l’ask. */
G.FP = {
  absorptionAcheteuse: { zone: [31000, 31002], zoneLabel: 'zone de liquidité', bars: [
    { label: 'arrivée', open: 31007, close: 31002, rows: [[31007, 42, 38], [31006, 75, 51], [31005, 96, 60], [31004, 120, 74], [31003, 188, 92], [31002, 410, 118, 1], [31001, 655, 140, 1], [31000, 702, 96, 1]] },
    { label: 'réaction', open: 31002, close: 31007, rows: [[31008, 30, 84], [31007, 62, 150], [31006, 70, 188], [31005, 81, 205], [31004, 66, 176], [31003, 52, 140], [31002, 40, 96], [31001, 12, 35]] }] },
  absorptionVendeuse: { zone: [31018, 31020], zoneLabel: 'zone de liquidité', bars: [
    { label: 'arrivée', open: 31013, close: 31018, rows: [[31020, 101, 688, 1], [31019, 133, 640, 1], [31018, 120, 402, 1], [31017, 95, 180], [31016, 70, 118], [31015, 61, 99], [31014, 47, 72], [31013, 40, 45]] },
    { label: 'réaction', open: 31018, close: 31013, rows: [[31019, 36, 14], [31018, 98, 41], [31017, 141, 52], [31016, 180, 66], [31015, 203, 80], [31014, 170, 63], [31013, 149, 58], [31012, 82, 30]] }] },
  epuisement: { zone: [31000, 31002], zoneLabel: 'zone de liquidité', bars: [
    { label: 'arrivée', open: 31007, close: 31002, rows: [[31007, 160, 140], [31006, 210, 150], [31005, 188, 120], [31004, 120, 80], [31003, 60, 41], [31002, 22, 12], [31001, 9, 3, 1], [31000, 4, 0, 1]] },
    { label: 'réaction', open: 31002, close: 31006, rows: [[31007, 20, 58], [31006, 48, 132], [31005, 61, 150], [31004, 55, 128], [31003, 40, 96], [31002, 22, 51], [31001, 6, 14]] }] },
  recharge: { zone: [31000, 31001], zoneLabel: 'mur affiché : environ 300', bars: [
    { label: 'arrivée', open: 31006, close: 31001, rows: [[31006, 40, 35], [31005, 66, 48], [31004, 90, 52], [31003, 115, 70], [31002, 160, 88], [31001, 520, 110, 1], [31000, 1450, 130, 1]] },
    { label: 'réaction', open: 31001, close: 31006, rows: [[31007, 25, 70], [31006, 50, 160], [31005, 66, 190], [31004, 58, 172], [31003, 45, 120], [31002, 30, 80], [31001, 10, 28]] }] },
  mangee: { zone: [31000, 31002], zoneLabel: 'zone de liquidité', bars: [
    { label: 'arrivée', open: 31006, close: 31001, rows: [[31006, 60, 50], [31005, 90, 58], [31004, 130, 71], [31003, 170, 80], [31002, 450, 120, 1], [31001, 610, 150, 1], [31000, 590, 140, 1]] },
    { label: 'cassure', open: 31001, close: 30995, rows: [[31001, 120, 60], [31000, 380, 75], [30999, 420, 66, 1], [30998, 460, 70, 1], [30997, 390, 62, 1], [30996, 280, 51], [30995, 170, 40]] }] },
  retiree: { zone: [31000, 31002], zoneLabel: 'mur retiré', bars: [
    { label: 'arrivée', open: 31006, close: 31002, rows: [[31006, 60, 52], [31005, 80, 60], [31004, 95, 70], [31003, 110, 75], [31002, 120, 70]] },
    { label: 'traversée', open: 31002, close: 30996, rows: [[31002, 70, 40], [31001, 85, 35, 1], [31000, 90, 38, 1], [30999, 100, 41], [30998, 120, 50], [30997, 130, 46], [30996, 90, 30]] }] },
  initiative: { zone: [31008, 31010], zoneLabel: 'résistance', bars: [
    { label: 'pression', open: 31004, close: 31009, rows: [[31010, 60, 75], [31009, 70, 96], [31008, 88, 120], [31007, 60, 110], [31006, 52, 90], [31005, 40, 70], [31004, 35, 44]] },
    { label: 'cassure', open: 31009, close: 31015, rows: [[31015, 20, 70], [31014, 22, 140, 2], [31013, 30, 198, 2], [31012, 41, 260, 2], [31011, 66, 150], [31010, 80, 120], [31009, 50, 70]] }] },
  invalidation: { zone: [31000, 31002], zoneLabel: 'zone', bars: [
    { label: 'absorption', open: 31006, close: 31002, rows: [[31006, 45, 40], [31005, 80, 60], [31004, 110, 70], [31003, 160, 90], [31002, 420, 110, 1], [31001, 600, 130, 1], [31000, 640, 120, 1]] },
    { label: 'puis traversée', open: 31002, close: 30996, rows: [[31002, 90, 60], [31001, 210, 70], [31000, 340, 80], [30999, 360, 70], [30998, 310, 60], [30997, 240, 50], [30996, 150, 30]] }] }
};

/* ===================================================================
   3. Carte de liquidité (heatmap du carnet) et ses issues
   =================================================================== */
var NT = 48, NP = 30;
/* Chemin de prix : images-clés [colonne, rangée] interpolées, bruit déterministe. Mur : rangée w, taille S(t). */
function path(keys, seed, amp) {
  var r = T.rng(seed), out = [];
  for (var t = 0; t < NT; t++) {
    var k = 0; while (k < keys.length - 2 && keys[k + 1][0] <= t) k++;
    var a = keys[k], b = keys[k + 1], u = Math.max(0, Math.min(1, (t - a[0]) / Math.max(1, b[0] - a[0])));
    out.push(a[1] + (b[1] - a[1]) * u + (r() - 0.5) * 2 * (amp == null ? 0.5 : amp));
  }
  return out;
}
G.LIQ = {
  tient: { t: 'La zone tient : absorption acheteuse', side: -1, w: 9, keys: [[0, 22], [12, 17], [24, 10.4], [30, 10.2], [36, 15], [47, 21]], wall: function (t) { return 1; }, hits: [[24, 0.7], [27, 1], [30, 0.6]], fp: 'absorptionAcheteuse',
    lire: 'Le mur de bids reste affiché pendant que les vendeurs frappent dedans : gros volume vendu au bid, et le prix ne casse pas. Delta très négatif, prix qui tient : quelqu’un achète tout.', faire: 'Achat possible si le biais est acheteur et que le prix est sous la bande VWAP : stop sous toute la zone, objectif sur la VWAP, la HVZ opposée ou la cible GEX.' },
  resistance: { t: 'La zone tient : absorption vendeuse', side: 1, w: 21, keys: [[0, 8], [12, 13], [24, 19.6], [30, 19.8], [36, 15], [47, 9]], wall: function (t) { return 1; }, hits: [[24, 0.7], [27, 1], [30, 0.6]], fp: 'absorptionVendeuse',
    lire: 'Le miroir : les acheteurs lèvent l’offre, le mur d’asks reste là, le prix ne monte plus. Delta très positif, prix bloqué : quelqu’un vend tout.', faire: 'Vente possible si le biais est vendeur et que le prix est au-dessus de la bande VWAP : stop au-dessus de toute la zone.' },
  recharge: { t: 'Le mur se recharge (iceberg)', side: -1, w: 9, keys: [[0, 21], [14, 15], [24, 10.4], [33, 10.3], [40, 15], [47, 19]], wall: function (t) { return t < 24 ? 0.55 : 0.25 + 0.3 * ((t * 7) % 3) / 2; }, hits: [[24, 0.8], [26, 1], [28, 1], [30, 0.9], [32, 0.7]], fp: 'recharge',
    lire: 'Le mur affiché est moyen, mais il se reforme à chaque fois qu’on le mange : le volume échangé au niveau dépasse de loin la taille affichée. C’est une absorption plus forte encore, cachée.', faire: 'Même lecture qu’une absorption : achat dans le sens du biais, stop sous la zone. Le chiffre clé est au footprint : 1 450 échangés pour environ 300 affichés.' },
  retiree: { t: 'Le mur est retiré avant le contact', side: -1, w: 9, keys: [[0, 22], [14, 17], [24, 11], [28, 8], [36, 5], [47, 3]], wall: function (t) { return t < 21 ? 1 : 0; }, hits: [], fp: 'retiree',
    lire: 'Le mur était énorme, puis il disparaît juste avant que le prix arrive : il n’était là que pour être vu. Au footprint, rien de gros ne s’échange au niveau.', faire: 'Pas d’achat : il n’y a plus personne. On ne joue jamais un niveau parce qu’un mur y était affiché ; on le joue parce qu’il a échangé et tenu.' },
  mangee: { t: 'La zone est mangée : cassure', side: -1, w: 9, keys: [[0, 21], [14, 15], [24, 10.4], [32, 10], [36, 7], [42, 5], [44, 8.6], [47, 6]], wall: function (t) { return t < 24 ? 1 : t < 34 ? 1 - (t - 24) / 10 : 0; }, hits: [[25, 0.8], [28, 0.9], [31, 1], [34, 0.8]], fp: 'mangee',
    lire: 'Le mur échange beaucoup et fond : sa taille baisse au fil des frappes, puis il disparaît et le prix passe. L’ancien support devient une résistance au retour.', faire: 'Pas d’achat. Si le biais est vendeur, le retour sous la zone est un contact de vente ; sinon on attend.' },
  epuisement: { t: 'Épuisement avant la zone', side: -1, w: 9, keys: [[0, 23], [14, 16], [22, 12.2], [28, 11.4], [34, 13], [47, 20]], wall: function (t) { return 0.9; }, hits: [[27, 0.25]], fp: 'epuisement',
    lire: 'Le prix ralentit en approchant de la zone : les derniers prix de la barre n’échangent presque plus rien. Il ne reste plus de vendeurs, sans même avoir besoin du mur.', faire: 'Achat possible si ton signal choisi est l’épuisement et que le biais est acheteur. Stop sous la zone, même si elle n’a pas été touchée.' },
  ignoree: { t: 'Le prix n’y vient pas', side: -1, w: 7, keys: [[0, 22], [16, 18], [26, 15], [36, 19], [47, 17]], wall: function (t) { return 1; }, hits: [], fp: null,
    lire: 'Le mur reste là toute la séance, le prix ne le touche jamais.', faire: 'Rien à faire. Un plan qui force le contact invente des trades.' }
};
G.LIQ_KEYS = ['tient', 'resistance', 'recharge', 'retiree', 'mangee', 'epuisement', 'ignoree'];
G.liqGrid = function (key) {
  var c = G.LIQ[key], seed = 1 + G.LIQ_KEYS.indexOf(key) * 97, r = T.rng(seed), px = path(c.keys, seed + 5, 0.45), grid = [];
  for (var p = 0; p < NP; p++) {
    var row = [];
    for (var t = 0; t < NT; t++) {
      var d = Math.abs(p - px[t]), base = r() < 0.18 ? r() * 0.22 : 0;
      if (d < 4 && d > 0.6) base += 0.12 * (1 - d / 4);
      var ws = c.wall(t), dw = Math.abs(p - c.w), wall = dw === 0 ? ws : dw === 1 ? 0.55 * ws : 0;
      var traded = c.side < 0 ? px[t] < c.w + 0.5 && t > 22 : px[t] > c.w - 0.5 && t > 22;
      if (key !== 'recharge' && key !== 'tient' && key !== 'resistance' && traded && dw <= 1) wall *= 0.4;
      row.push(Math.min(1, base + wall));
    }
    grid.push(row);
  }
  return { grid: grid, price: px, c: c };
};
G.heatSvg = function (key, o) {
  o = o || {};
  var L = G.liqGrid(key), W = 320, H = 190, x0 = 4, x1 = W - 4, y0 = 6, y1 = H - 18, cw = (x1 - x0) / NT, ch = (y1 - y0) / NP;
  var X = function (t) { return x0 + (t + 0.5) * cw; }, Y = function (p) { return y1 - (p + 0.5) * ch; };
  var g = '<rect x="0" y="0" width="' + W + '" height="' + H + '" fill="var(--ink)" rx="6"/>';
  L.grid.forEach(function (row, p) { row.forEach(function (v, t) { if (v < 0.06) return; g += '<rect x="' + (x0 + t * cw).toFixed(1) + '" y="' + (y1 - (p + 1) * ch).toFixed(1) + '" width="' + (cw + 0.3).toFixed(1) + '" height="' + (ch + 0.3).toFixed(1) + '" fill="' + (v > 0.75 ? 'var(--violet-2)' : 'var(--violet)') + '" fill-opacity="' + Math.min(0.95, 0.15 + 0.8 * v).toFixed(2) + '"/>'; }); });
  L.c.hits.forEach(function (hh) { var t = hh[0], v = hh[1]; g += '<circle cx="' + X(t).toFixed(1) + '" cy="' + Y(L.price[t]).toFixed(1) + '" r="' + (2.5 + 6 * v).toFixed(1) + '" fill="var(--hi)" fill-opacity=".18" stroke="var(--hi)" stroke-width="1"/>'; });
  g += '<path d="' + L.price.map(function (p, t) { return (t ? 'L' : 'M') + X(t).toFixed(1) + ',' + Y(p).toFixed(1); }).join(' ') + '" fill="none" stroke="var(--hi)" stroke-width="1.8" stroke-linejoin="round"/>';
  g += '<text class="pl-t" x="' + x0 + '" y="' + (H - 5) + '">temps →</text><text class="pl-t v" x="' + x1 + '" y="' + (H - 5) + '" text-anchor="end">mur de liquidité</text>';
  return '<svg class="pl-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + E(L.c.t) + '">' + g + '</svg>';
};
/* Relief 3D de la carte de liquidité : temps × prix × taille affichée. */
G.surfLiq = function (key) {
  var L = G.liqGrid(key), xs = [], ys = [], vals = [], lo = Infinity, hi = -Infinity, am = [0, 0];
  for (var t = 0; t < NT; t += 2) xs.push(t); for (var p = 0; p < NP; p++) ys.push(p);
  ys.forEach(function (p, j) { vals.push(xs.map(function (t, i) { var v = L.grid[p][t]; if (v < lo) lo = v; if (v > hi) { hi = v; am = [i, j]; } return v; })); });
  return { title: 'Carnet dans le temps : ' + L.c.t.toLowerCase(), x: { name: 'temps', dom: [xs[0], xs[xs.length - 1]], fmt: function (v) { return 'instant ' + Math.round(v); } }, y: { name: 'prix', dom: [0, NP - 1], fmt: function (v) { var d = Math.round(v) - L.c.w; return d === 0 ? 'niveau du mur' : (d > 0 ? '+' : '−') + Math.abs(d) + ' tick' + (Math.abs(d) > 1 ? 's' : '') + ' du mur'; } },
    z: { name: 'taille affichée', fmt: function (v) { return F.pct(v, 0) + ' du mur'; } }, fn: function (t, p) { return L.grid[Math.max(0, Math.min(NP - 1, Math.round(p)))][Math.max(0, Math.min(NT - 1, Math.round(t)))]; }, mid: null, xs: xs, ys: ys, vals: vals, zmin: lo, zmax: hi, argmax: am };
};

/* ===================================================================
   4. Profil de volume de la veille, HVN et LVN détectés par une règle
   =================================================================== */
/* Une séance en deux équilibres reliés par un mouvement rapide : le creux du profil entre eux est la LVN. */
G.vpSession = function (seed) {
  var r = T.rng(seed || 3), pts = [], p = 30;
  for (var t = 0; t < 240; t++) {
    var target = t < 110 ? 30 : t < 125 ? 30 + (t - 110) * 2.6 : 69;
    p += (target - p) * (t >= 110 && t < 125 ? 0.6 : 0.08) + normal(r) * 2.1;
    pts.push(Math.max(4, Math.min(96, p)));
  }
  return pts;
};
G.profile = function (pts, bins) {
  bins = bins || 25; var h = []; for (var i = 0; i < bins; i++) h.push(0);
  pts.forEach(function (p) { h[Math.max(0, Math.min(bins - 1, Math.floor(p / 100 * bins)))]++; });
  var sm = h.map(function (v, i) { return (h[i - 1] || v) * 0.25 + v * 0.5 + (h[i + 1] || v) * 0.25; }), mx = Math.max.apply(null, sm);
  var peaks = [];
  sm.forEach(function (v, i) { if (v >= 0.45 * mx && v >= (sm[i - 1] || 0) && v >= (sm[i + 1] || 0)) peaks.push(i); });
  peaks = peaks.filter(function (i, k) { return !k || i - peaks[k - 1] > 2; });
  var hvz = peaks.map(function (i) { var a = i, b = i; while (a > 0 && sm[a - 1] >= 0.6 * sm[i]) a--; while (b < bins - 1 && sm[b + 1] >= 0.6 * sm[i]) b++; return { lo: a, hi: b, peak: i }; });
  var lvn = []; for (var k = 1; k < hvz.length; k++) { var best = hvz[k - 1].hi + 1; for (var j = hvz[k - 1].hi + 1; j < hvz[k].lo; j++) if (sm[j] < sm[best]) best = j; lvn.push(best); }
  var poc = sm.indexOf(mx);
  return { h: sm, max: mx, bins: bins, hvz: hvz, lvn: lvn, poc: poc };
};
G.vpSvg = function (o) {
  o = o || {};
  var pts = G.vpSession(o.seed || 3), pr = G.profile(pts), W = 320, H = 190, x0 = 6, xs = W - 96, y0 = 10, y1 = H - 18, bh = (y1 - y0) / pr.bins;
  var X = function (i) { return x0 + i / (pts.length - 1) * (xs - x0 - 8); }, Y = function (p) { return y1 - p / 100 * (y1 - y0); }, Yb = function (b) { return y1 - (b + 1) * bh; };
  var g = '<rect x="0" y="0" width="' + W + '" height="' + H + '" fill="var(--ink)" rx="6"/>';
  pr.hvz.forEach(function (z, k) { g += '<rect x="' + x0 + '" y="' + Yb(z.hi).toFixed(1) + '" width="' + (W - x0 - 4) + '" height="' + ((z.hi - z.lo + 1) * bh).toFixed(1) + '" fill="var(--violet-a)"/><text class="pl-t v" x="' + (x0 + 3) + '" y="' + (Yb(z.hi) + 10).toFixed(1) + '">HVZ ' + (k ? 'haute' : 'basse') + '</text>'; });
  pr.lvn.forEach(function (b) { var y = (Yb(b) + bh / 2).toFixed(1); g += '<line x1="' + x0 + '" x2="' + (W - 4) + '" y1="' + y + '" y2="' + y + '" stroke="var(--hi)" stroke-dasharray="4 3"/><text class="pl-t w" x="' + (x0 + 3) + '" y="' + (+y - 4) + '">LVN</text>'; });
  pr.h.forEach(function (v, b) { var w = v / pr.max * 84, y = Yb(b); g += '<rect x="' + (W - 6 - w).toFixed(1) + '" y="' + (y + 0.6).toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + (bh - 1.2).toFixed(1) + '" fill="' + (b === pr.poc ? 'var(--hi)' : pr.hvz.some(function (z) { return b >= z.lo && b <= z.hi; }) ? 'var(--violet)' : 'var(--line-2)') + '"/>'; });
  g += '<text class="pl-t w" x="' + (W - 8) + '" y="' + (Yb(pr.poc) - 2).toFixed(1) + '" text-anchor="end">POC</text>';
  g += '<path d="' + pts.map(function (p, i) { return (i ? 'L' : 'M') + X(i).toFixed(1) + ',' + Y(p).toFixed(1); }).join(' ') + '" fill="none" stroke="var(--soft)" stroke-width="1.1"/>';
  g += '<text class="pl-t" x="' + x0 + '" y="' + (H - 5) + '">la séance d’hier →</text><text class="pl-t" x="' + (W - 6) + '" y="' + (H - 5) + '" text-anchor="end">profil de volume</text>';
  return '<svg class="pl-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Profil de volume de la veille, HVZ et LVN">' + g + '</svg>';
};
/* Trois profils de jours passés : une LVN du premier jour, jamais traversée, prolongée jusqu’à aujourd’hui. */
G.lvnHistSvg = function () {
  var W = 320, H = 180, y0 = 10, y1 = H - 20, g = '<rect x="0" y="0" width="' + W + '" height="' + H + '" fill="var(--ink)" rx="6"/>', cols = 4, cw = (W - 8) / cols;
  var lvnY = null;
  [5, 9, 13].forEach(function (seed, d) {
    var pr = G.profile(G.vpSession(seed).map(function (p) { return p * 0.55 + 30 + d * 4; }), 25), bh = (y1 - y0) / pr.bins, x = 4 + d * cw;
    pr.h.forEach(function (v, b) { var w = v / pr.max * (cw - 14), y = y1 - (b + 1) * bh; g += '<rect x="' + (x + 4).toFixed(1) + '" y="' + (y + 0.6).toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + (bh - 1.2).toFixed(1) + '" fill="' + (pr.lvn.indexOf(b) >= 0 && d === 0 ? 'var(--hi)' : 'var(--line-2)') + '"/>'; });
    if (d === 0 && pr.lvn.length) lvnY = y1 - (pr.lvn[0] + 0.5) * bh;
    g += '<text class="pl-t" x="' + (x + cw / 2) + '" y="' + (H - 6) + '" text-anchor="middle">J−' + (3 - d) + '</text>';
  });
  if (lvnY != null) {
    g += '<line x1="' + (4 + cw * 0.4).toFixed(1) + '" x2="' + (W - 6) + '" y1="' + lvnY.toFixed(1) + '" y2="' + lvnY.toFixed(1) + '" stroke="var(--hi)" stroke-dasharray="4 3"/><text class="pl-t w" x="' + (W - 8) + '" y="' + (lvnY - 5).toFixed(1) + '" text-anchor="end">LVN de J−3, jamais traversée</text>';
    var xt = 4 + 3 * cw, pts = [[xt + 4, y1 - 20], [xt + 20, y1 - 40], [xt + 34, lvnY + 18], [xt + 48, lvnY + 2], [xt + 60, lvnY + 30], [xt + cw - 8, lvnY + 46]];
    g += '<path d="' + pts.map(function (q, i) { return (i ? 'L' : 'M') + q[0].toFixed(1) + ',' + q[1].toFixed(1); }).join(' ') + '" fill="none" stroke="var(--soft)" stroke-width="1.4"/><circle cx="' + (xt + 48).toFixed(1) + '" cy="' + (lvnY + 2).toFixed(1) + '" r="4.5" fill="none" stroke="var(--violet)" stroke-width="1.8"/><text class="pl-t" x="' + (xt + cw / 2) + '" y="' + (H - 6) + '" text-anchor="middle">aujourd’hui</text>';
  }
  return '<svg class="pl-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="LVN historique prolongée">' + g + '</svg>';
};
/* FVG : trois bougies, l’écart entre le haut de la première et le bas de la troisième reste ouvert, puis le prix y revient. */
G.fvgSvg = function () {
  var W = 320, H = 180, y1 = H - 18, Y = function (p) { return y1 - p / 100 * (H - 30); }, g = '<rect x="0" y="0" width="' + W + '" height="' + H + '" fill="var(--ink)" rx="6"/>';
  var c = [[18, 22, 34, 14, 36], [30, 34, 72, 32, 75], [42, 70, 84, 58, 86], [54, 84, 78, 74, 88], [66, 78, 70, 66, 80], [78, 70, 52, 50, 72], [90, 52, 44, 40, 56], [102, 44, 49, 40, 51], [114, 49, 62, 47, 64]];
  var gapLo = 36, gapHi = 58;
  g += '<rect x="' + 70 + '" y="' + Y(gapHi) + '" width="' + (W - 76) + '" height="' + (Y(gapLo) - Y(gapHi)) + '" fill="var(--violet-a)" stroke="var(--violet-b)" stroke-dasharray="3 3"/><text class="pl-t v" x="' + (W - 8) + '" y="' + (Y(gapHi) + 11) + '" text-anchor="end">FVG : écart laissé ouvert</text>';
  c.forEach(function (k) { var x = k[0] * 2.4, up = k[2] >= k[1]; g += '<line x1="' + x + '" x2="' + x + '" y1="' + Y(k[4]) + '" y2="' + Y(k[3]) + '" stroke="var(--soft)"/><rect x="' + (x - 6) + '" y="' + Y(Math.max(k[1], k[2])) + '" width="12" height="' + Math.max(1, Math.abs(Y(k[1]) - Y(k[2]))) + '" fill="' + (up ? 'var(--violet)' : 'var(--soft)') + '"/>'; });
  g += '<text class="pl-t" x="' + (18 * 2.4) + '" y="' + (Y(14) + 14) + '" text-anchor="middle">1</text><text class="pl-t" x="' + (42 * 2.4) + '" y="' + (Y(58) + 14) + '" text-anchor="middle">3</text>';
  g += '<circle cx="' + (102 * 2.4) + '" cy="' + Y(40) + '" r="5" fill="none" stroke="var(--violet)" stroke-width="1.8"/><text class="pl-t v" x="' + (102 * 2.4) + '" y="' + (Y(40) + 16) + '" text-anchor="middle">retour dans l’écart</text>';
  g += '<text class="pl-t" x="8" y="' + (H - 5) + '">haut de 1 sous le bas de 3 : le FVG</text>';
  return '<svg class="pl-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Fair value gap">' + g + '</svg>';
};

/* ===================================================================
   5. Frise du jour : fenêtres interdites (calculées) et maintenant
   =================================================================== */
G.daySvg = function (events, avant, apres, nowMin) {
  var W = 320, H = 96, x0 = 8, x1 = W - 8, X = function (m) { return x0 + Math.max(0, Math.min(1440, m)) / 1440 * (x1 - x0); }, g = '<rect x="0" y="0" width="' + W + '" height="' + H + '" fill="var(--ink)" rx="6"/>';
  g += '<rect x="' + X(15.5 * 60) + '" y="30" width="' + (X(22 * 60) - X(15.5 * 60)) + '" height="20" fill="rgba(255,255,255,.06)"/><text class="pl-t" x="' + (X(15.5 * 60) + 2) + '" y="26">cash US</text>';
  g += '<line x1="' + x0 + '" x2="' + x1 + '" y1="40" y2="40" stroke="var(--line-2)"/>';
  [0, 6, 9, 12, 15, 18, 21, 24].forEach(function (hh) { var x = X(hh * 60); g += '<line x1="' + x + '" x2="' + x + '" y1="36" y2="44" stroke="var(--line-2)"/><text class="pl-t" x="' + x + '" y="62" text-anchor="' + (hh === 0 ? 'start' : hh === 24 ? 'end' : 'middle') + '">' + hh + 'h</text>'; });
  (events || []).forEach(function (e, k) {
    var a = X(e.min - avant), b = X(e.min + apres);
    g += '<rect x="' + a.toFixed(1) + '" y="30" width="' + Math.max(2, b - a).toFixed(1) + '" height="20" fill="var(--violet)" fill-opacity=".55"/>';
    g += '<text class="pl-t v" x="' + X(e.min).toFixed(1) + '" y="' + (78 + (k % 2) * 11) + '" text-anchor="middle">' + E(e.hhmm + ' ' + e.label) + '</text>';
  });
  if (fin(nowMin)) { var xn = X(nowMin); g += '<line x1="' + xn + '" x2="' + xn + '" y1="14" y2="54" stroke="var(--hi)" stroke-width="2"/><text class="pl-t w" x="' + xn + '" y="11" text-anchor="' + (xn > W * 0.8 ? 'end' : xn < W * 0.2 ? 'start' : 'middle') + '">maintenant</text>'; }
  return '<svg class="pl-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Frise du jour et fenêtres interdites">' + g + '</svg>';
};
