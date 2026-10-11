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
  neutre: function (k) { return G.find(611, { drift: 0, sd: 1.6 }, function (b) { if (G.touch(b, 2.5, -1, G.FROM) >= 0 || G.touch(b, 2.5, 1, G.FROM) >= 0) return null; var x = 0; for (var i = G.FROM + 1; i < b.length; i++) if ((b[i].c - b[i].vwap) * (b[i - 1].c - b[i - 1].vwap) < 0) x++; return x >= 8 ? { x: x } : null; }); },
  ouverture: function (k) { return G.find(811, { drift: 0, shock: -55 }, function (b) { var i = G.touch(b, k, -1, 186); if (i < 0 || i > 200) return null; var j = G.backToVwap(b, i, -1); return { i: i, j: j }; }); }
};
/* Les bandes de l’utilisateur : ±1,5σ et ±2,5σ. Un contact de l’une ou de l’autre compte. */
G.BANDS = [-2.5, -1.5, 1.5, 2.5];
/* Les scénarios coûtent jusqu’à une demi-seconde de recherche : calculés une fois par bande. */
var SC_CACHE = {};
G.scen = function (name, k) { var key = name + ':' + k; if (!(key in SC_CACHE)) SC_CACHE[key] = G.SCEN[name] ? G.SCEN[name](k) : null; return SC_CACHE[key]; };
var VW = 320, VH = 200;
G.vwapSvg = function (sc, o) {
  o = o || {};
  var bars = sc.bars.slice(G.FROM), k = o.k || 2, n = bars.length, x0 = 6, x1 = VW - 40, y0 = 14, y1 = VH - 22;
  var lo = Infinity, hi = -Infinity;
  bars.forEach(function (b) { lo = Math.min(lo, b.l, b.vwap - 2.65 * b.sd); hi = Math.max(hi, b.h, b.vwap + 2.65 * b.sd); });
  var X = function (i) { return +(x0 + (i + 0.5) / n * (x1 - x0)).toFixed(1); }, Y = function (p) { return +(y0 + (hi - p) / (hi - lo) * (y1 - y0)).toFixed(1); };
  var g = '<rect x="0" y="0" width="' + VW + '" height="' + VH + '" fill="var(--ink)" rx="6"/>';
  [12, 15, 18, 21].forEach(function (hh) { var i = hh * 12 - G.FROM; if (i < 0 || i >= n) return; g += '<line x1="' + X(i) + '" x2="' + X(i) + '" y1="' + y0 + '" y2="' + y1 + '" stroke="var(--line)"/><text class="pl-t" x="' + X(i) + '" y="' + (VH - 7) + '" text-anchor="middle">' + hh + ':00</text>'; });
  if (o.zone) { var zi = o.zone.i - G.FROM; g += '<rect x="' + X(Math.max(0, zi - 4)) + '" y="' + y0 + '" width="' + (X(Math.min(n - 1, zi + 4)) - X(Math.max(0, zi - 4))) + '" height="' + (y1 - y0) + '" fill="var(--violet-a)"/>'; }
  var line = function (f, cls) { return '<path d="' + bars.map(function (b, i) { return (i ? 'L' : 'M') + X(i) + ',' + Y(f(b)); }).join(' ') + '" fill="none" ' + cls + '/>'; };
  G.BANDS.forEach(function (m) { var on = Math.abs(m) === k; g += line(function (b) { return b.vwap + m * b.sd; }, 'stroke="' + (on ? 'var(--soft)' : 'var(--line-2)') + '" stroke-width="' + (on ? 1.2 : 1) + '"'); });
  bars.forEach(function (b, i) { g += '<line x1="' + X(i) + '" x2="' + X(i) + '" y1="' + Y(b.h) + '" y2="' + Y(b.l) + '" stroke="var(--soft)" stroke-width="1" opacity=".85"/>'; });
  g += line(function (b) { return b.vwap; }, 'stroke="var(--hi)" stroke-width="2"');
  var last = bars[n - 1], lab = [['VWAP', last.vwap, 'w']].concat(G.BANDS.map(function (m) { return [(m > 0 ? '+' : '−') + String(Math.abs(m)).replace('.', ',') + 'σ', last.vwap + m * last.sd, '']; }));
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
  continuation: { t: 'La zone ne tient pas : continuation', side: -1, w: 12, seed: 977, keys: [[0, 22], [12, 18], [22, 12.6], [28, 12.3], [33, 9], [38, 6], [42, 9.5], [44, 11.2], [47, 6]], wall: function (t) { return t < 22 ? 1 : t < 31 ? 1 - (t - 22) / 9 : 0; }, hits: [[23, 0.8], [26, 0.9], [29, 1]], fp: 'mangee',
    lire: 'Les acheteurs défendent la zone, le mur fond sous les frappes et cède : le prix passe dessous et revient tester l’ancien support par en dessous, sans le reprendre.', faire: 'Si le biais est vendeur, c’est un setup : vente au retour sous l’ancienne zone, stop au-dessus d’elle, cible le niveau gamma suivant. Biais acheteur : pas de trade.' },
  spawn: { t: 'Le mur apparaît au dernier moment', side: -1, w: 9, seed: 1201, keys: [[0, 22], [14, 15], [24, 10.6], [27, 10.4], [31, 7], [38, 4], [47, 3]], wall: function (t) { return t < 20 ? 0 : t < 27 ? 1 : 0; }, hits: [], fp: 'retiree',
    lire: 'Rien au niveau, puis un mur énorme surgit quelques instants avant le contact, et disparaît dès que le prix arrive. C’est la forme exacte des ordres de manipulation sanctionnés sur le CME : posés pour être vus, pas pour être exécutés.', faire: 'Jamais d’entrée sur un mur qui vient d’apparaître. Un mur se joue s’il est là depuis plusieurs minutes et s’il échange au contact.' },
  ignoree: { t: 'Le prix n’y vient pas', side: -1, w: 7, keys: [[0, 22], [16, 18], [26, 15], [36, 19], [47, 17]], wall: function (t) { return 1; }, hits: [], fp: null,
    lire: 'Le mur reste là toute la séance, le prix ne le touche jamais.', faire: 'Rien à faire. Un plan qui force le contact invente des trades.' }
};
G.LIQ_KEYS = ['tient', 'resistance', 'recharge', 'retiree', 'mangee', 'epuisement', 'ignoree'];
G.LIQ_PLUS = ['continuation', 'spawn'];
G.liqGrid = function (key) {
  var c = G.LIQ[key], seed = c.seed || 1 + G.LIQ_KEYS.indexOf(key) * 97, r = T.rng(seed), px = path(c.keys, seed + 5, 0.45), grid = [];
  for (var p = 0; p < NP; p++) {
    var row = [];
    for (var t = 0; t < NT; t++) {
      var d = Math.abs(p - px[t]), base = r() < 0.18 ? r() * 0.22 : 0;
      if (d < 4 && d > 0.6) base += 0.12 * (1 - d / 4);
      var ws = c.wall(t), dw = Math.abs(p - c.w), wall = dw === 0 ? ws : dw === 1 ? 0.55 * ws : 0;
      var traded = c.side < 0 ? px[t] < c.w + 0.5 && t > 22 : px[t] > c.w - 0.5 && t > 22;
      if (key !== 'recharge' && key !== 'tient' && key !== 'resistance' && key !== 'spawn' && traded && dw <= 1) wall *= 0.4;
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

/* ===================================================================
   6. La carte du jour : le setup tracé avec les niveaux de l’utilisateur
   =================================================================== */
/* o : { price, hvn: [{lo, hi, label}], gamma: [{price, label}], best: {side, entry, stop, target, rr} | null }.
   Rien n’est inventé : sans niveaux, la planche dit ce qui manque. */
G.carteSvg = function (o) {
  var W = 320, H = 240, x0 = 8, xl = 206, y0 = 14, y1 = H - 16, ps = [];
  (o.hvn || []).forEach(function (z) { ps.push(z.lo, z.hi); }); (o.gamma || []).forEach(function (g) { ps.push(g.price); });
  if (fin(o.price)) ps.push(o.price); if (o.best) ps.push(o.best.stop, o.best.target);
  var g = '<rect x="0" y="0" width="' + W + '" height="' + H + '" fill="var(--ink)" rx="6"/>';
  if (ps.length < 2) return '<svg class="pl-svg" viewBox="0 0 ' + W + ' 80" role="img" aria-label="Carte du jour vide"><rect x="0" y="0" width="' + W + '" height="80" fill="var(--ink)" rx="6"/><text class="pl-t" x="' + (W / 2) + '" y="44" text-anchor="middle">Note le prix, tes HVN et tes niveaux gamma</text></svg>';
  var lo = Math.min.apply(null, ps), hi = Math.max.apply(null, ps), pad = (hi - lo) * 0.07 || 5; lo -= pad; hi += pad;
  var Y = function (p) { return +(y0 + (hi - p) / (hi - lo) * (y1 - y0)).toFixed(1); }, labs = [];
  (o.hvn || []).forEach(function (z, i) { var a = Y(z.hi), b = Math.max(Y(z.lo), a + 3); g += '<rect x="' + x0 + '" y="' + a + '" width="' + (xl - x0) + '" height="' + (b - a) + '" fill="var(--violet-a)" stroke="var(--violet-b)"/>'; labs.push({ y: (a + b) / 2, t: (z.label || 'HVN ' + (i + 1)) + ' ' + F.num((z.lo + z.hi) / 2, 0), c: 'v' }); });
  (o.gamma || []).forEach(function (q) { var y = Y(q.price); g += '<line x1="' + x0 + '" x2="' + xl + '" y1="' + y + '" y2="' + y + '" stroke="var(--soft)" stroke-dasharray="5 3"/>'; labs.push({ y: y, t: q.label + ' ' + F.num(q.price, 2), c: '' }); });
  if (fin(o.price)) { var yp = Y(o.price); g += '<line x1="' + x0 + '" x2="' + xl + '" y1="' + yp + '" y2="' + yp + '" stroke="var(--hi)" stroke-width="1.6"/>'; labs.push({ y: yp, t: 'prix ' + F.num(o.price, 2), c: 'w' }); }
  var b = o.best;
  if (b) {
    var xe = 116, xt = 190, ye = Y(b.entry), ys = Y(b.stop), yt = Y(b.target), up = b.side > 0;
    g += '<rect x="' + xe + '" y="' + Math.min(ye, yt) + '" width="' + (xt - xe) + '" height="' + Math.abs(yt - ye) + '" fill="var(--violet)" fill-opacity=".14"/>';
    g += '<rect x="' + xe + '" y="' + Math.min(ye, ys) + '" width="' + (xt - xe) + '" height="' + Math.max(1, Math.abs(ys - ye)) + '" fill="var(--soft)" fill-opacity=".22"/>';
    if (fin(o.price)) g += '<path d="M' + (x0 + 30) + ',' + Y(o.price) + ' C' + (x0 + 70) + ',' + Y(o.price) + ' ' + (xe - 30) + ',' + ye + ' ' + xe + ',' + ye + '" fill="none" stroke="var(--hi)" stroke-dasharray="3 3" stroke-width="1.3"/>';
    g += '<path d="M' + xe + ',' + ye + ' L' + (xt - 4) + ',' + (yt + (up ? 6 : -6)) + '" stroke="var(--violet)" stroke-width="2" fill="none"/><path d="M' + (xt - 9) + ',' + (yt + (up ? 6 : -6)) + ' L' + (xt - 3) + ',' + yt + ' L' + (xt + 1) + ',' + (yt + (up ? 8 : -8)) + '" fill="none" stroke="var(--violet)" stroke-width="2"/>';
    g += '<circle cx="' + xe + '" cy="' + ye + '" r="4" fill="var(--violet)"/>';
    g += '<text class="pl-t w" x="' + (xe - 4) + '" y="' + (yt + (up ? 3.5 : 3.5)) + '" text-anchor="end">' + (up ? 'achat' : 'vente') + ' · R:R 1:' + F.num(b.rr, b.rr < 10 ? 1 : 0) + '</text>';
    labs.push({ y: ys, t: 'stop ' + F.num(b.stop, 2), c: '' });
  }
  labs.sort(function (a, c) { return a.y - c.y; }); var prev = -99;
  labs.forEach(function (l) { var y = Math.max(prev + 11, l.y + 3.5); prev = y; g += '<text class="pl-t' + (l.c ? ' ' + l.c : '') + '" x="' + (xl + 6) + '" y="' + Math.min(H - 4, y).toFixed(1) + '">' + E(l.t) + '</text>'; });
  return '<svg class="pl-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Carte du jour et setup">' + g + '</svg>';
};

/* ===================================================================
   7. Scalp « Mur » : exemples à la heatmap, et le trade simulé sur le chemin dessiné
   =================================================================== */
/* Une colonne = 5 secondes (72 colonnes, six minutes). Une rangée = 1 point de NQ. Le risque vaut 4 rangées :
   entrée 1 rangée devant le mur, stop 3 rangées derrière ; objectif 2R. Les règles sont celles de la carte :
   sens, mur ancien (au moins 24 colonnes, deux minutes), espace jusqu’au mur opposé, touche, tenue, sortie à 3 min. */
var SNT = 72, SNP = 36;
G.SCALP_RULES = { front: 1, behind: 3, rr: 2, ageMin: 24, maxCols: 36, gone: 0.35 };
G.SCALP = {
  tient: { t: 'Mur ancien, il tient : achat', side: 1, trend: 1, wall: 10, wf: function () { return 1; }, keys: [[0, 24], [14, 19], [26, 10.7], [31, 10.5], [36, 14], [44, 21], [59, 24]], hits: 1, attendu: 'gain',
    lire: 'Prix au-dessus de la VWAP, donc achats seulement. Le mur de bids est là depuis le début de la fenêtre ; le prix vient dessus, les bulles s’impriment, le mur ne fond pas. Le prix repart et touche 2R.' },
  vente: { t: 'Mur ancien au-dessus : vente', side: -1, trend: -1, wall: 26, wf: function () { return 1; }, keys: [[0, 12], [14, 17], [26, 25.3], [31, 25.5], [36, 22], [44, 15], [59, 12]], hits: 1, attendu: 'gain',
    lire: 'Prix sous la VWAP : ventes seulement. Le mur d’asks au-dessus tient au contact, les acheteurs s’y épuisent, le prix redescend à 2R.' },
  recharge: { t: 'Le mur se recharge : achat', side: 1, trend: 1, wall: 10, wf: function (t) { return t < 26 ? 0.6 : 0.45 + 0.25 * ((t * 7) % 3) / 2; }, keys: [[0, 23], [14, 18], [26, 10.7], [34, 10.5], [40, 16], [48, 21], [59, 23]], hits: 2, attendu: 'gain',
    lire: 'Le mur affiché est moyen et semble fondre, mais il se reforme à chaque frappe : il échange bien plus qu’il n’affiche. C’est un mur qui tient.' },
  spawn: { t: 'Mur apparu au dernier moment : pas de trade', side: 1, trend: 1, wall: 10, wf: function (t) { return t < 22 ? 0 : t < 29 ? 1 : 0; }, keys: [[0, 23], [14, 18], [26, 11.6], [29, 11.2], [33, 8], [40, 5], [59, 4]], hits: 0, attendu: 'refus',
    lire: 'Rien au niveau, puis un mur énorme surgit moins d’une minute avant le contact et disparaît quand le prix arrive. Règle du mur ancien : refus. Le prix traverse : l’achat aurait été stoppé.' },
  retire: { t: 'Le mur est retiré pendant le trade : sortie', side: 1, trend: 1, wall: 10, wf: function (t) { return t < 30 ? 1 : 0; }, keys: [[0, 23], [14, 18], [26, 10.8], [30, 10.6], [32, 10.4], [36, 6], [44, 4], [59, 4]], hits: 1, attendu: 'sortie',
    lire: 'Mur ancien, entrée au contact, puis le mur disparaît d’un coup. Règle de tenue : sortie immédiate, avant le stop. La perte est une fraction de R au lieu d’un R entier.' },
  mange: { t: 'Le mur fond sous les frappes : sortie', side: 1, trend: 1, wall: 10, wf: function (t) { return t < 26 ? 1 : t < 34 ? 1 - (t - 26) / 8 : 0; }, keys: [[0, 23], [14, 18], [26, 10.8], [33, 10.5], [36, 8], [44, 5], [59, 4]], hits: 2, attendu: 'sortie',
    lire: 'Gros volume au contact, mais la taille affichée baisse frappe après frappe : le mur se fait manger. Sortie dès qu’il passe sous un tiers de sa taille, avant le stop.' },
  contre: { t: 'Mur contre le sens : pas de trade', side: 1, trend: -1, wall: 10, wf: function () { return 1; }, keys: [[0, 24], [14, 19], [26, 10.7], [31, 10.5], [36, 13], [44, 12], [59, 9]], hits: 1, attendu: 'refus',
    lire: 'Le mur de bids tient, mais le prix est sous la VWAP : la règle du sens n’autorise que des ventes. Pas d’achat, même si le mur est beau.' },
  espace: { t: 'Pas de place jusqu’au mur opposé : pas de trade', side: 1, trend: 1, wall: 10, wf: function () { return 1; }, wall2: { row: 16, wf: function () { return 1; } }, keys: [[0, 14], [14, 13], [26, 10.7], [31, 10.5], [38, 14.6], [46, 13], [59, 14]], hits: 1, attendu: 'refus',
    lire: 'Mur sous le prix, mais un autre mur au-dessus, à moins de 2R : l’objectif est bloqué d’avance. Règle de l’espace : pas de trade. Le prix tourne entre les deux murs.' },
  temps: { t: 'Il tient mais rien ne part : sortie au temps', side: 1, trend: 1, wall: 10, wf: function () { return 1; }, keys: [[0, 22], [14, 17], [26, 10.7], [32, 10.5], [44, 13], [56, 13.4], [59, 13]], hits: 1, attendu: 'temps',
    lire: 'Le mur tient, le prix ne part pas. Au bout de trois minutes, sortie au marché : un petit gain ou une petite perte, jamais un trade qu’on garde par espoir.' },
  pasTouche: { t: 'Le prix s’arrête avant : pas rempli', side: 1, trend: 1, wall: 10, wf: function () { return 1; }, keys: [[0, 23], [14, 18], [26, 13.4], [31, 13.2], [40, 18], [59, 23]], hits: 0, attendu: 'rien',
    lire: 'Le prix rebondit deux points avant l’ordre limite. Pas rempli, pas de trade : on ne court pas après. C’est une issue normale.' },
  annonce: { t: 'Pendant une annonce : pas de trade', side: 1, trend: 1, wall: 10, annonce: true, wf: function (t) { return t < 25 ? 1 : 0.2; }, keys: [[0, 22], [10, 20], [24, 11.6], [27, 4], [31, 18], [36, 6], [44, 15], [59, 10]], hits: 1, attendu: 'refus',
    lire: 'Le mur est là, mais l’annonce tombe : le prix traverse dans les deux sens en quelques secondes. Fenêtre interdite : pas de trade, quoi que dise la heatmap.' },
  stoppe: { t: 'Il tenait, puis le stop : la perte normale', side: 1, trend: 1, wall: 10, wf: function (t) { return t < 40 ? 1 : 0.5; }, keys: [[0, 23], [14, 18], [26, 10.7], [30, 10.5], [35, 14.5], [40, 10.5], [42, 6.8], [48, 5], [59, 5]], hits: 1, attendu: 'perte',
    lire: 'Tout était juste : sens, mur ancien, espace, touche, tenue. Le prix repart, revient, et le mur cède au deuxième passage : stop, −1R. Une stratégie à 1:2 en a une sur deux ou trois, même quand elle fonctionne.' }
};
G.SCALP_KEYS = ['tient', 'vente', 'recharge', 'spawn', 'retire', 'mange', 'contre', 'espace', 'temps', 'pasTouche', 'annonce', 'stoppe'];
G.scalpGrid = function (key) {
  var c = G.SCALP[key], seed = 3001 + G.SCALP_KEYS.indexOf(key) * 131, r = T.rng(seed), r2 = T.rng(seed + 9);
  var px = [], k = 0;
  for (var t = 0; t < SNT; t++) { while (k < c.keys.length - 2 && c.keys[k + 1][0] <= t) k++; var a = c.keys[k], b = c.keys[k + 1], u = Math.max(0, Math.min(1, (t - a[0]) / Math.max(1, b[0] - a[0]))); px.push(a[1] + (b[1] - a[1]) * u + (r2() - 0.5) * 0.5); }
  var grid = [];
  for (var p = 0; p < SNP; p++) {
    var row = [];
    for (t = 0; t < SNT; t++) {
      var v = r() < 0.16 ? r() * 0.2 : 0, d = Math.abs(p - px[t]); if (d < 4 && d > 0.7) v += 0.1 * (1 - d / 4);
      var dw = Math.abs(p - c.wall); if (dw <= 1) v += (dw === 0 ? 1 : 0.5) * c.wf(t);
      if (c.wall2) { var d2 = Math.abs(p - c.wall2.row); if (d2 <= 1) v += (d2 === 0 ? 1 : 0.5) * c.wall2.wf(t); }
      row.push(Math.min(1, v));
    }
    grid.push(row);
  }
  return { grid: grid, price: px, c: c };
};
/* Les règles appliquées au chemin : le résultat se calcule, il n’est jamais écrit. */
G.scalpTrade = function (key) {
  var S = G.scalpGrid(key), c = S.c, R = G.SCALP_RULES, sd = c.side, px = S.price;
  var E0 = c.wall + sd * R.front, St = c.wall - sd * R.behind, risk = Math.abs(E0 - St), Tg = E0 + sd * R.rr * risk;
  var tc = -1; for (var t = 0; t < SNT; t++) if (sd > 0 ? px[t] <= E0 : px[t] >= E0) { tc = t; break; }
  var out = { entry: E0, stop: St, target: Tg, risk: risk, tc: tc, tx: -1, r: null, issue: 'rien', why: '' };
  if (tc < 0) { out.why = 'le prix n’atteint pas l’ordre limite'; return out; }
  var born = -1; for (t = 0; t <= tc; t++) if (c.wf(t) >= 0.5) { born = t; break; }
  var age = born < 0 ? 0 : tc - born, blocked = false;
  if (c.wall2) { var lo2 = Math.min(E0, Tg), hi2 = Math.max(E0, Tg); blocked = c.wall2.row > lo2 && c.wall2.row < hi2; }
  if (c.annonce) { out.issue = 'refus'; out.why = 'fenêtre interdite (annonce)'; return out; }
  if (c.trend !== sd) { out.issue = 'refus'; out.why = 'contre le sens de la VWAP'; return out; }
  if (age < R.ageMin) { out.issue = 'refus'; out.why = 'mur trop récent (' + Math.round(age * 5) + ' s)'; return out; }
  if (blocked) { out.issue = 'refus'; out.why = 'mur opposé avant l’objectif'; return out; }
  for (t = tc + 1; t < SNT; t++) {
    var p = px[t];
    if (sd > 0 ? p <= St : p >= St) { out.tx = t; out.r = -1; out.issue = 'perte'; out.why = 'stop'; return out; }
    if (sd > 0 ? p >= Tg : p <= Tg) { out.tx = t; out.r = R.rr; out.issue = 'gain'; out.why = 'objectif 2R'; return out; }
    if (c.wf(t) < R.gone) { out.tx = t; out.r = (p - E0) * sd / risk; out.issue = 'sortie'; out.why = 'le mur ne tient plus'; return out; }
    if (t - tc >= R.maxCols) { out.tx = t; out.r = (p - E0) * sd / risk; out.issue = 'temps'; out.why = 'trois minutes'; return out; }
  }
  out.tx = SNT - 1; out.r = (px[SNT - 1] - E0) * sd / risk; out.issue = 'temps'; out.why = 'fin de la fenêtre'; return out;
};
G.scalpSvg = function (key) {
  var S = G.scalpGrid(key), c = S.c, tr = G.scalpTrade(key), W = 320, H = 210, x0 = 4, x1 = W - 4, y0 = 16, y1 = H - 20, cw = (x1 - x0) / SNT, ch = (y1 - y0) / SNP;
  var X = function (t) { return x0 + (t + 0.5) * cw; }, Y = function (p) { return y1 - (p + 0.5) * ch; };
  var g = '<rect x="0" y="0" width="' + W + '" height="' + H + '" fill="var(--ink)" rx="6"/>';
  S.grid.forEach(function (row, p) { row.forEach(function (v, t) { if (v < 0.06) return; g += '<rect x="' + (x0 + t * cw).toFixed(1) + '" y="' + (y1 - (p + 1) * ch).toFixed(1) + '" width="' + (cw + 0.3).toFixed(1) + '" height="' + (ch + 0.3).toFixed(1) + '" fill="' + (v > 0.75 ? 'var(--violet-2)' : 'var(--violet)') + '" fill-opacity="' + Math.min(0.95, 0.15 + 0.8 * v).toFixed(2) + '"/>'; }); });
  if (c.hits) for (var t = 0; t < SNT; t++) { var near = Math.abs(S.price[t] - c.wall) <= 1.7 && c.wf(t) > 0.2; if (near && t % 2 === 0) g += '<circle cx="' + X(t).toFixed(1) + '" cy="' + Y(c.wall + c.side * 0.6).toFixed(1) + '" r="' + (2 + 1.6 * c.hits).toFixed(1) + '" fill="var(--hi)" fill-opacity=".2" stroke="var(--hi)" stroke-width=".9"/>'; }
  g += '<path d="' + S.price.map(function (p, t) { return (t ? 'L' : 'M') + X(t).toFixed(1) + ',' + Y(p).toFixed(1); }).join(' ') + '" fill="none" stroke="var(--hi)" stroke-width="1.8" stroke-linejoin="round"/>';
  if (tr.tc >= 0 && tr.issue !== 'refus') {
    var ta = X(tr.tc), tb = X(tr.tx >= 0 ? tr.tx : SNT - 1);
    g += '<line x1="' + ta + '" x2="' + tb + '" y1="' + Y(tr.target) + '" y2="' + Y(tr.target) + '" stroke="var(--hi)" stroke-dasharray="4 3"/><text class="pl-t w" x="' + (ta - 6) + '" y="' + (Y(tr.target) + 3.5) + '" text-anchor="end">2R</text>';
    g += '<line x1="' + ta + '" x2="' + tb + '" y1="' + Y(tr.entry) + '" y2="' + Y(tr.entry) + '" stroke="var(--violet)" stroke-width="1.6"/>';
    g += '<line x1="' + ta + '" x2="' + tb + '" y1="' + Y(tr.stop) + '" y2="' + Y(tr.stop) + '" stroke="var(--soft)" stroke-dasharray="3 3"/><text class="pl-t" x="' + (ta - 6) + '" y="' + (Y(tr.stop) + 3.5) + '" text-anchor="end">stop</text>';
    g += '<circle cx="' + ta + '" cy="' + Y(tr.entry) + '" r="4.5" fill="var(--violet)"/>';
    if (tr.tx >= 0) g += '<circle cx="' + tb + '" cy="' + Y(S.price[tr.tx]) + '" r="4.5" fill="none" stroke="var(--hi)" stroke-width="1.8"/>';
  } else if (tr.tc >= 0) g += '<circle cx="' + X(tr.tc) + '" cy="' + Y(S.price[tr.tc]) + '" r="5" fill="none" stroke="var(--soft)" stroke-width="1.6" stroke-dasharray="2 2"/>';
  var born = -1; for (t = 0; t < SNT; t++) if (c.wf(t) >= 0.5) { born = t; break; }
  if (born > 0) g += '<line x1="' + X(born) + '" x2="' + X(born) + '" y1="' + y0 + '" y2="' + y1 + '" stroke="var(--soft)" stroke-dasharray="2 3"/><text class="pl-t" x="' + (X(born) - 3) + '" y="' + (y0 - 4) + '" text-anchor="end">le mur apparaît</text>';
  g += '<text class="pl-t" x="' + x0 + '" y="' + (H - 6) + '">' + (c.trend > 0 ? 'prix au-dessus de la VWAP' : 'prix sous la VWAP') + '</text><text class="pl-t" x="' + x1 + '" y="' + (H - 6) + '" text-anchor="end">6 minutes →</text>';
  return '<svg class="pl-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + E(c.t) + '">' + g + '</svg>';
};
G.surfScalp = function (key) {
  var S = G.scalpGrid(key), xs = [], ys = [], vals = [], lo = Infinity, hi = -Infinity, am = [0, 0];
  for (var t = 0; t < SNT; t += 2) xs.push(t); for (var p = 0; p < SNP; p++) ys.push(p);
  ys.forEach(function (p, j) { vals.push(xs.map(function (t, i) { var v = S.grid[p][t]; if (v < lo) lo = v; if (v > hi) { hi = v; am = [i, j]; } return v; })); });
  return { title: 'Carnet en relief : ' + S.c.t.toLowerCase(), x: { name: 'temps', dom: [0, SNT - 2], fmt: function (v) { return Math.round(v * 5) + ' s'; } }, y: { name: 'prix', dom: [0, SNP - 1], fmt: function (v) { var d = Math.round(v) - S.c.wall; return d === 0 ? 'niveau du mur' : (d > 0 ? '+' : '−') + Math.abs(d) + ' pt du mur'; } },
    z: { name: 'taille affichée', fmt: function (v) { return F.pct(v, 0) + ' du mur'; } }, fn: function (t, p) { return S.grid[Math.max(0, Math.min(SNP - 1, Math.round(p)))][Math.max(0, Math.min(SNT - 1, Math.round(t)))]; }, mid: null, xs: xs, ys: ys, vals: vals, zmin: lo, zmax: hi, argmax: am };
};
