/* Desk « Journal » — chaque décision, refus compris, s’inscrit au pouce au moment où elle
   se prend et se scelle avant l’issue (ALP nº 3, partie IV, table 9 : la frontière
   temporelle). L’issue se complète ensuite et le P&L se calcule. Le registre se filtre et
   s’exporte ; les statistiques se lisent chacune contre sa loi nulle, jusqu’au mur des
   619 décisions (ALP nº 3, partie VIII, table 14). */
var h = T.h, U = T.ui, C = T.chart, F = T.fmt, S = T.stats;
T.lib = T.lib || {};
var J = T.lib.journal = {};
var NS = 'http://www.w3.org/2000/svg';

/* =====================================================================
   1. Vocabulaire et constantes sourcées
   ===================================================================== */
J.LEVELS = ['Bande VWAP', 'Nœud faible volume', 'Zone 61,8–79', 'Pivot', 'Bord de valeur', 'POC', 'Niveau GEX'];
J.CONFS = ['Rejet', 'Absorption', 'Traversée'];
J.OFFPLAN = 'Hors setup';
J.STAGES = [{ v: 'macro', label: 'Macro' }, { v: 'biais', label: 'Biais' }, { v: 'vwap', label: 'VWAP' }, { v: 'declencheur', label: 'Déclencheur' }, { v: 'risque', label: 'Risque' }, { v: 'autre', label: 'Autre' }];
J.EMOTIONS = ['calme', 'FOMO', 'revanche', 'peur', 'ennui', 'euphorie'];
J.FINS = [{ v: 'objectif', label: 'Objectif' }, { v: 'stop', label: 'Stop' }, { v: 'cloche', label: 'Cloche' }, { v: 'invalidation', label: 'Invalidation' }, { v: 'manuel', label: 'Manuel' }];
J.CF = [{ v: 'objectif', label: 'Objectif atteint' }, { v: 'stop', label: 'Stop touché' }, { v: 'aucune', label: 'Ni l’un ni l’autre' }];
/* ALP nº 3, partie VIII, table 14 : 619 décisions pour établir un Sharpe de 0,10 par décision,
   taxe de multiplicité comprise, soit 1,2 an à deux décisions par séance (252 séances par an,
   SESSIONS_PER_YEAR de alp1/report10.py). */
J.WALL = 619;
J.WALL_PER_SESSION = 2;
J.SESSIONS_PER_YEAR = 252;
J.LATE_MIN = 15;                 /* au-delà, une ligne est marquée « inscrite après coup » */
var Z95 = 1.959963984540054;     /* Φ⁻¹(0,975) exact */
J.Z95 = Z95;

/* =====================================================================
   2. Fonctions pures — aucun DOM, aucun T.store
   ===================================================================== */
function fin(v) { return typeof v === 'number' && isFinite(v); }
function sum(a) { var s = 0; for (var i = 0; i < a.length; i++) s += a[i]; return s; }
function mean(a) { return a.length ? sum(a) / a.length : NaN; }
function round(x, nd) { var k = Math.pow(10, nd); return Math.round(x * k) / k; }
function pad2(n) { return String(n).padStart(2, '0'); }
J.fin = fin;
J.round = round;

J.sideSign = function (side) { return side === 'long' ? 1 : side === 'short' ? -1 : NaN; };

/* P&L net = (sortie − entrée) × sens × quantité × valeur du point − commission × quantité.
   La commission est l’aller-retour par contrat (T.settings.commissionRT). */
J.pnl = function (t, pv, comm) {
  pv = fin(pv) ? pv : t.pv; comm = fin(comm) ? comm : (fin(t.comm) ? t.comm : 0);
  var s = J.sideSign(t.side);
  if (!fin(t.entry) || !fin(t.exit) || !fin(t.qty) || !fin(pv) || !fin(s)) return NaN;
  return (t.exit - t.entry) * s * t.qty * pv - comm * t.qty;
};
/* Risque engagé en dollars : |entrée − stop| × quantité × valeur du point. */
J.riskUsd = function (t, pv) {
  pv = fin(pv) ? pv : t.pv;
  if (!fin(t.entry) || !fin(t.stop) || !fin(t.qty) || !fin(pv)) return NaN;
  return Math.abs(t.entry - t.stop) * t.qty * pv;
};
/* R = P&L / (|entrée − stop| × quantité × valeur du point). */
J.rMultiple = function (t, pnl, pv) { var risk = J.riskUsd(t, pv); return fin(pnl) && risk > 0 ? pnl / risk : NaN; };
/* Rapport prévu objectif / risque, en points ; NaN si l’objectif manque ou est du mauvais côté. */
J.rr = function (t) {
  var s = J.sideSign(t.side);
  if (!fin(s) || !fin(t.entry) || !fin(t.stop) || !fin(t.target)) return NaN;
  var risk = (t.entry - t.stop) * s, gain = (t.target - t.entry) * s;
  return risk > 0 && gain > 0 ? gain / risk : NaN;
};
/* Espérance sans avantage : à dérive nulle, E[R] = −c/L pour toute géométrie
   (ALP nº 3, partie XI). c = commission × quantité, L = risque engagé en dollars. */
J.nullR = function (t, pv, comm) {
  comm = fin(comm) ? comm : (fin(t.comm) ? t.comm : NaN);
  var risk = J.riskUsd(t, pv);
  return fin(comm) && risk > 0 ? -comm * t.qty / risk : NaN;
};
/* Taille maximale qui tient dans la limite de risque par trade, au stop donné. */
J.maxQty = function (limit, t, pv) {
  if (!fin(limit) || !fin(t.entry) || !fin(t.stop) || !fin(pv) || t.entry === t.stop) return NaN;
  return Math.floor(limit / (Math.abs(t.entry - t.stop) * pv) + 1e-9);
};

/* Setup : « niveau · confirmation », ou « Hors setup ». */
function norm(s) {
  return String(s == null ? '' : s).replace(/œ/g, 'oe').replace(/Œ/g, 'OE').normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase().replace(/[–—]/g, '-').replace(/(\d)\.(\d)/g, '$1,$2').replace(/\s+/g, ' ').trim();
}
J.norm = norm;
J.parseSetup = function (txt) {
  var n = norm(txt), out = { level: null, conf: null };
  if (!n) return out;
  if (n.indexOf(norm(J.OFFPLAN)) >= 0) return { level: J.OFFPLAN, conf: null };
  J.LEVELS.forEach(function (l) { if (!out.level && n.indexOf(norm(l)) >= 0) out.level = l; });
  J.CONFS.forEach(function (c) { if (!out.conf && n.indexOf(norm(c)) >= 0) out.conf = c; });
  return out;
};
J.setupText = function (f, partial) {
  if (f.level === J.OFFPLAN) return J.OFFPLAN;
  if (f.level && f.conf) return f.level + ' · ' + f.conf;
  if (partial && (f.level || f.conf)) return f.level || f.conf;
  return f.setupRaw ? String(f.setupRaw) : '';
};
J.shortSetup = function (txt) {
  var p = J.parseSetup(txt), A = { 'Bande VWAP': 'VWAP', 'Nœud faible volume': 'NFV', 'Zone 61,8–79': '61,8–79', 'Pivot': 'Pivot', 'Bord de valeur': 'Bord VA', 'POC': 'POC', 'Niveau GEX': 'GEX', 'Hors setup': 'Hors setup' }, B = { 'Rejet': 'rej.', 'Absorption': 'abs.', 'Traversée': 'trav.' };
  if (!p.level && !p.conf) { var t = String(txt || '—'); return t.length > 16 ? t.slice(0, 15) + '…' : t; }
  return (p.level ? A[p.level] : '') + (p.level && p.conf ? ' · ' : '') + (p.conf ? B[p.conf] : '');
};

/* Le formulaire vide, et la fusion d’un brouillon déposé par un autre desk. */
J.blankForm = function () { return { kind: 'pris', side: null, level: null, conf: null, setupRaw: null, entry: null, stop: null, target: null, qty: 1, conviction: null, emotion: null, plan: null, note: '', stage: null, time: '' }; };
J.fromDraft = function (form, d) {
  var f = Object.assign({}, form);
  if (!d || typeof d !== 'object') return f;
  if (d.kind === 'pris' || d.kind === 'refus') f.kind = d.kind;
  if (d.side === 'long' || d.side === 'short') f.side = d.side;
  if (d.setup) { var ps = J.parseSetup(d.setup); f.level = ps.level; f.conf = ps.conf; f.setupRaw = ps.level ? null : String(d.setup); }
  ['entry', 'stop', 'target', 'qty'].forEach(function (k) { var v = typeof d[k] === 'string' ? F.parse(d[k]) : d[k]; if (fin(v)) f[k] = v; });
  if (d.conviction >= 1 && d.conviction <= 5) f.conviction = Math.round(d.conviction);
  if (J.EMOTIONS.indexOf(d.emotion) >= 0) f.emotion = d.emotion;
  if (typeof d.plan === 'boolean') f.plan = d.plan;
  if (d.note) f.note = String(d.note);
  if (J.STAGES.some(function (s) { return s.v === d.stage; })) f.stage = d.stage;
  if (f.kind === 'refus') { f.side = null; f.entry = null; f.stop = null; f.target = null; } /* un refus ne porte ni sens ni mise */
  return f;
};

/* Contrôle d’une décision avant scellement : liste des défauts, vide si tout va. */
J.validate = function (f) {
  var e = [];
  if (f.kind === 'refus') {
    if (!J.STAGES.some(function (s) { return s.v === f.stage; })) e.push('Choisis l’étape où le setup a été arrêté.');
    return e;
  }
  if (f.kind !== 'pris') return ['Type de décision inconnu.'];
  var s = J.sideSign(f.side);
  if (!fin(s)) e.push('Choisis le sens : long ou short.');
  if (!J.setupText(f)) e.push('Choisis le setup : un niveau et une confirmation, ou « Hors setup ».');
  if (!fin(f.entry) || f.entry <= 0) e.push('Entre le prix d’entrée.');
  if (!fin(f.stop) || f.stop <= 0) e.push('Entre le stop : sans stop, il n’y a pas de R.');
  else if (fin(f.entry) && fin(s)) {
    if (f.stop === f.entry) e.push('Le stop ne peut pas être au prix d’entrée.');
    else if ((f.entry - f.stop) * s < 0) e.push(s > 0 ? 'En long, le stop se place sous l’entrée.' : 'En short, le stop se place au-dessus de l’entrée.');
  }
  if (f.target != null && f.target !== '') {
    if (!fin(f.target)) e.push('L’objectif est illisible.');
    else if (fin(f.entry) && fin(s) && (f.target - f.entry) * s <= 0) e.push(s > 0 ? 'En long, l’objectif se place au-dessus de l’entrée.' : 'En short, l’objectif se place sous l’entrée.');
  }
  if (!fin(f.qty) || f.qty < 1 || Math.floor(f.qty) !== f.qty) e.push('La quantité est un nombre entier de contrats, au moins 1.');
  if (!(f.conviction >= 1 && f.conviction <= 5)) e.push('Annonce ta conviction, de 1 à 5, avant l’issue.');
  if (f.plan !== true && f.plan !== false) e.push('Dis si le plan est respecté.');
  return e;
};

/* L’entrée de journal scellée. Un refus ne porte ni sens, ni prix, ni quantité. */
J.buildEntry = function (f, o) {
  var at = fin(f.at) ? f.at : o.now, note = String(f.note || '').trim();
  if (f.kind === 'refus') {
    var r = { kind: 'refus', at: at, writtenAt: o.now, stage: f.stage, instrument: o.instrument };
    var su = J.setupText(f, true); if (su) r.setup = su;
    if (note) r.note = note;
    return r;
  }
  var e = { kind: 'pris', at: at, writtenAt: o.now, side: f.side, setup: J.setupText(f), entry: f.entry, stop: f.stop, qty: f.qty,
    instrument: o.instrument, pv: o.pv, comm: o.comm, status: 'ouvert', conviction: f.conviction, plan: f.plan };
  if (fin(f.target)) e.target = f.target;
  if (f.emotion) e.emotion = f.emotion;
  if (note) e.note = note;
  return e;
};

/* La clôture : seuls les champs d’issue changent. */
J.validateClose = function (row, c) {
  var e = [];
  if (!row || row.kind !== 'pris') return ['Seule une décision prise se clôt.'];
  if (row.status === 'clos') return ['Cette position est déjà close.'];
  if (!fin(row.entry) || !fin(row.stop) || !fin(row.qty) || !fin(J.sideSign(row.side))) return ['Décision incomplète : entrée, stop, quantité ou sens manquant.'];
  if (!fin(c.exit) || c.exit <= 0) e.push('Entre le prix de sortie.');
  if (!J.FINS.some(function (x) { return x.v === c.fin; })) e.push('Choisis comment la position a fini.');
  return e;
};
J.closePatch = function (row, c, now, o) {
  o = o || {};
  var pv = fin(row.pv) ? row.pv : o.pv, comm = fin(row.comm) ? row.comm : o.comm;
  var p = J.pnl(Object.assign({}, row, { exit: c.exit }), pv, comm);
  p = fin(p) ? round(p, 2) : NaN;
  var patch = { exit: c.exit, fin: c.fin, status: 'clos', closedAt: now, pnl: p, r: J.rMultiple(row, p, pv) };
  if (!fin(row.pv) && fin(pv)) patch.pv = pv;
  if (!fin(row.comm) && fin(comm)) patch.comm = comm;
  var a = String(c.apres || '').trim(); if (a) patch.apres = a;
  return patch;
};

/* Temps, dans un fuseau donné. */
J.dateIn = function (at, tz) { var p = T.time.parts(tz, new Date(at)); return pad2(p.d) + '/' + pad2(p.mo); };
J.timeIn = function (at, tz) { var p = T.time.parts(tz, new Date(at)); return pad2(p.h) + ':' + pad2(p.m); };
J.dateLongIn = function (at, tz) { var p = T.time.parts(tz, new Date(at)); return pad2(p.d) + '/' + pad2(p.mo) + '/' + p.y; };
J.isoDay = function (at, tz) { var p = T.time.parts(tz, new Date(at)); return p.y + '-' + pad2(p.mo) + '-' + pad2(p.d); };
/* Période : 'jour' (même date civile), 'semaine' (lundi → dimanche de la semaine courante), 'tout'. */
J.inPeriod = function (at, period, now, tz) {
  if (period === 'tout' || !period) return true;
  if (!fin(at)) return false;
  var a = T.time.parts(tz, new Date(at)), n = T.time.parts(tz, new Date(now));
  var da = Date.UTC(a.y, a.mo - 1, a.d), dn = Date.UTC(n.y, n.mo - 1, n.d);
  if (period === 'jour') return da === dn;
  if (period === 'semaine') { var mon = dn - ((n.wd + 6) % 7) * 864e5; return da >= mon && da < mon + 7 * 864e5; }
  return true;
};
/* « 10:12 » aujourd’hui, dans le fuseau, en horodatage ; NaN si illisible. */
J.atFromTime = function (hhmm, now, tz) {
  var m = /^(\d{1,2}):(\d{2})$/.exec(String(hhmm || '').trim()); if (!m) return NaN;
  var H = +m[1], M = +m[2]; if (H > 23 || M > 59) return NaN;
  var p = T.time.parts(tz, new Date(now)), diff = (p.h * 60 + p.m) - (H * 60 + M);
  return now - diff * 60000 - p.s * 1000 - (now % 1000);
};
J.lateMinutes = function (r) { return fin(r.writtenAt) && fin(r.at) ? Math.max(0, Math.round((r.writtenAt - r.at) / 60000)) : NaN; };

/* Statistiques. Wilson : (p̂ + z²/2n ± z·√(p̂(1 − p̂)/n + z²/4n²)) / (1 + z²/n). */
J.wilson = function (k, n, z) {
  if (!n) return { p: NaN, lo: NaN, hi: NaN };
  z = z == null ? Z95 : z;
  var p = k / n, z2 = z * z, den = 1 + z2 / n, c = (p + z2 / (2 * n)) / den, hw = z * Math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / den;
  return { p: p, lo: Math.max(0, c - hw), hi: Math.min(1, c + hw) };
};
/* Plus longues séries de gains et de pertes ; un résultat nul coupe les deux. */
J.streaks = function (x) {
  var w = 0, l = 0, cw = 0, cl = 0;
  for (var i = 0; i < x.length; i++) {
    if (x[i] > 0) { cw++; cl = 0; } else if (x[i] < 0) { cl++; cw = 0; } else { cw = 0; cl = 0; }
    if (cw > w) w = cw; if (cl > l) l = cl;
  }
  return { win: w, loss: l };
};
/* Résumé d’un groupe de décisions closes : un gagnant a un P&L net > 0. */
J.summarize = function (list, key) {
  var R = [], P = [], wins = 0, losses = 0;
  list.forEach(function (t) { if (fin(t.r)) R.push(t.r); if (fin(t.pnl)) { P.push(t.pnl); if (t.pnl > 0) wins++; else if (t.pnl < 0) losses++; } });
  var n = P.length, sd = R.length > 1 ? S.sd(R) : NaN;
  return { key: key, n: n, wins: wins, losses: losses, winRate: n ? wins / n : NaN, expR: mean(R), sdR: sd, ciR: fin(sd) ? Z95 * sd / Math.sqrt(R.length) : NaN, sum: sum(P), expUsd: mean(P) };
};
/* Lecture d’une espérance contre zéro, par son intervalle à 95 %. */
J.read = function (g) {
  if (!g || g.n < 2 || !fin(g.ciR)) return 'trop peu';
  if (g.expR - g.ciR > 0) return 'au-dessus de 0';
  if (g.expR + g.ciR < 0) return 'sous 0';
  return 'indistinct';
};
J.groupStats = function (list, keyFn, numeric) {
  var by = {}, keys = [];
  list.forEach(function (t) { var k = keyFn(t); if (k == null || k === '') k = '—'; if (!by[k]) { by[k] = []; keys.push(k); } by[k].push(t); });
  var out = keys.map(function (k) { return J.summarize(by[k], k); });
  out.sort(function (a, b) {
    if (a.key === '—') return 1; if (b.key === '—') return -1;
    if (numeric) return a.key - b.key;
    return b.n - a.n || (String(a.key) < String(b.key) ? -1 : 1);
  });
  return out;
};
/* Table de contingence décision × issue (ALP nº 3, partie IV) : l’issue d’un refus est
   contrefactuelle (champ cf), renseignée après coup. */
J.contingency = function (rows) {
  var t = { prisG: 0, prisP: 0, refusG: 0, refusP: 0, refusN: 0, refusX: 0 };
  rows.forEach(function (r) {
    if (r.kind === 'pris' && r.status === 'clos' && fin(r.pnl)) { if (r.pnl > 0) t.prisG++; else t.prisP++; }
    else if (r.kind === 'refus') { if (r.cf === 'objectif') t.refusG++; else if (r.cf === 'stop') t.refusP++; else if (r.cf === 'aucune') t.refusN++; else t.refusX++; }
  });
  return t;
};
/* Calibration de la conviction : forte (4–5) contre faible (1–2). */
J.calibration = function (closed) {
  var hi = J.summarize(closed.filter(function (t) { return t.conviction >= 4; }), 'forte');
  var lo = J.summarize(closed.filter(function (t) { return t.conviction >= 1 && t.conviction <= 2; }), 'faible');
  var vals = {}; closed.forEach(function (t) { if (t.conviction >= 1) vals[t.conviction] = 1; });
  var flat = Object.keys(vals).length === 1 && closed.length > 30;
  var verdict = flat ? 'constante' : (hi.n < 2 || lo.n < 2 || !fin(hi.ciR) || !fin(lo.ciR)) ? 'trop peu'
    : (hi.expR - hi.ciR > lo.expR + lo.ciR) ? 'calibrée' : (hi.expR + hi.ciR < lo.expR - lo.ciR) ? 'inversée' : 'indiscernable';
  return { hi: hi, lo: lo, verdict: verdict };
};
/* Rythme vers le mur : décisions closes par séance active, séances restantes. */
J.pace = function (nClosed, activeDays) {
  if (!(nClosed > 0) || !(activeDays > 0)) return null;
  var rate = nClosed / activeDays, left = Math.max(0, J.WALL - nClosed), sessions = Math.ceil(left / rate - 1e-9);
  return { rate: rate, left: left, sessions: sessions, years: sessions / J.SESSIONS_PER_YEAR };
};

J.stats = function (rows, tz) {
  tz = tz || 'Europe/Paris';
  var taken = [], refus = [], open = [], closed = [];
  rows.forEach(function (r) {
    if (r.kind === 'refus') refus.push(r);
    else if (r.kind === 'pris') { taken.push(r); if (r.status === 'clos' && fin(r.pnl)) closed.push(r); else open.push(r); }
  });
  closed.sort(function (a, b) { return ((a.closedAt || a.at || 0) - (b.closedAt || b.at || 0)) || ((a.at || 0) - (b.at || 0)); });
  var base = J.summarize(closed, 'tout'), P = closed.map(function (t) { return t.pnl; }), R = closed.map(function (t) { return t.r; }).filter(fin);
  var gains = 0, loss = 0; P.forEach(function (v) { if (v > 0) gains += v; else loss -= v; });
  var wR = R.filter(function (x) { return x > 0; }), lR = R.filter(function (x) { return x < 0; });
  var avgWinR = mean(wR), avgLossR = lR.length ? -mean(lR) : NaN, payoff = fin(avgWinR) && avgLossR > 0 ? avgWinR / avgLossR : NaN;
  var eq = S.cumsum(P), eqPlan = [], c = 0; closed.forEach(function (t) { if (t.plan === true) c += t.pnl; eqPlan.push(c); });
  var nulls = closed.map(function (t) { return J.nullR(t); }).filter(fin);
  var days = {}; closed.forEach(function (t) { if (fin(t.at)) days[J.isoDay(t.at, tz)] = 1; });
  var ok = closed.filter(function (t) { return t.plan === true; }), no = closed.filter(function (t) { return t.plan === false; });
  var sOk = J.summarize(ok, 'oui'), sNo = J.summarize(no, 'non');
  var stage = {}; refus.forEach(function (r) { var k = r.stage || 'autre'; stage[k] = (stage[k] || 0) + 1; });
  return {
    n: rows.length, nTaken: taken.length, nClosed: closed.length, nOpen: open.length, nRefus: refus.length,
    refusShare: (taken.length + refus.length) ? refus.length / (taken.length + refus.length) : NaN,
    wins: base.wins, losses: base.losses, flats: closed.length - base.wins - base.losses,
    winRate: base.winRate, wilson: J.wilson(base.wins, base.n), expR: base.expR, sdR: base.sdR, ciR: base.ciR, expUsd: base.expUsd,
    net: sum(P), gains: gains, lossUsd: loss, profitFactor: loss > 0 ? gains / loss : (gains > 0 ? Infinity : NaN),
    avgWinR: avgWinR, avgLossR: avgLossR, payoff: payoff, pEq: fin(payoff) ? 1 / (1 + payoff) : NaN, nullR: mean(nulls),
    streaks: J.streaks(P), equity: eq, equityPlan: eqPlan, maxDD: S.maxDrawdown([0].concat(eq)), activeDays: Object.keys(days).length,
    plan: { ok: sOk, no: sNo, nUnknown: closed.length - ok.length - no.length, gapR: sNo.expR - sOk.expR,
      lostR: no.length && fin(sOk.expR) && fin(sNo.expR) ? no.length * (sOk.expR - sNo.expR) : NaN, usd: sNo.sum },
    byEmotion: J.groupStats(closed, function (t) { return t.emotion; }),
    bySetup: J.groupStats(closed, function (t) { return t.setup; }),
    byHour: J.groupStats(closed, function (t) { return fin(t.at) ? T.time.parts(tz, new Date(t.at)).h : null; }, true),
    byConviction: J.groupStats(closed, function (t) { return t.conviction >= 1 && t.conviction <= 5 ? t.conviction : null; }, true),
    byStage: J.STAGES.map(function (s) { return { key: s.v, n: stage[s.v] || 0 }; }).filter(function (s) { return s.n; }),
    calibration: J.calibration(closed),
    contingency: J.contingency(rows),
    closed: closed
  };
};

/* Export CSV : séparateur « ; », virgule décimale, champs protégés. */
J.CSV_COLS = ['date', 'heure', 'type', 'statut', 'sens', 'instrument', 'setup', 'etape_refus', 'entree', 'stop', 'objectif', 'quantite', 'sortie', 'fin', 'pnl_usd', 'r', 'conviction', 'emotion', 'plan_respecte', 'issue_contrefactuelle', 'inscrit_apres_min', 'note', 'apres'];
J.csvCell = function (v) {
  if (v == null) return '';
  var s;
  if (typeof v === 'number') s = fin(v) ? String(v).replace('.', ',') : '';
  else { s = String(v); if (/^[=+@]/.test(s)) s = '\'' + s; }
  if (/[;"\n\r]/.test(s) || /^\s|\s$/.test(s)) s = '"' + s.replace(/"/g, '""') + '"';
  return s;
};
J.toCsv = function (rows, tz) {
  var lines = [J.CSV_COLS.join(';')];
  rows.forEach(function (r) {
    var pris = r.kind === 'pris', late = J.lateMinutes(r);
    var v = [J.isoDay(r.at, tz), J.timeIn(r.at, tz), r.kind || '', pris ? (r.status === 'clos' ? 'clos' : 'ouvert') : '', pris ? r.side || '' : '', r.instrument || '',
      r.setup || '', pris ? '' : (r.stage || ''), pris ? r.entry : null, pris ? r.stop : null, pris ? r.target : null, pris ? r.qty : null, pris ? r.exit : null, pris ? r.fin || '' : '',
      fin(r.pnl) ? round(r.pnl, 2) : null, fin(r.r) ? round(r.r, 4) : null, pris && fin(r.conviction) ? r.conviction : null, r.emotion || '',
      r.plan === true ? 'oui' : r.plan === false ? 'non' : '', r.cf || '', fin(late) ? late : null, r.note || '', r.apres || ''];
    lines.push(v.map(J.csvCell).join(';'));
  });
  return lines.join('\n');
};

/* Typographie française : espaces insécables avant « : » et fines avant « ; ! ? ». */
J.fr = function (s) {
  return String(s).replace(/ :/g, ' :').replace(/ ([;!?])/g, ' $1').replace(/« /g, '« ').replace(/ »/g, ' »');
};

/* =====================================================================
   3. Interface
   ===================================================================== */
var fr = J.fr;
var KEY = { wip: 'journal:wip', filter: 'journal:filter', draft: 'journal:draft', dim: 'journal:dim' };
var UI = { sel: null, confirmDel: null, close: {}, errors: [], fresh: false, draftNote: null, justAdded: null, self: false };

function stageLabel(v) { var s = J.STAGES.find(function (x) { return x.v === v; }); return s ? s.label : (v || '—'); }
function finLabel(v) { var s = J.FINS.find(function (x) { return x.v === v; }); return s ? s.label : (v || '—'); }
function emoLabel(v) { if (!v || v === '—') return 'Non dite'; return v === 'FOMO' ? 'FOMO' : v.charAt(0).toUpperCase() + v.slice(1); }
function sideLabel(v) { return v === 'long' ? 'Long' : v === 'short' ? 'Short' : '—'; }
function plural(n, one, many) { return n + ' ' + (n > 1 ? (many || one + 's') : one); }
function tzOf(set) { return set.tz || 'Europe/Paris'; }
function px(v) { return fin(v) ? F.num(v, 2) : '—'; }
function usd2(v) { return fin(v) ? F.usd(v, 2, true) : '—'; }
function note(t, warn) { return U.note(fr(t), warn); }
function lab(text, ctrl, hint) {
  if (ctrl && ctrl.setAttribute && !ctrl.getAttribute('aria-label')) { ctrl.setAttribute('role', 'group'); ctrl.setAttribute('aria-label', text); }
  return h('div', { class: 'fld' }, h('label', null, text), ctrl, hint ? h('span', { class: 'hint' }, fr(hint)) : null); }
function wide(btn) { btn.style.width = '100%'; return btn; }
function errBox(list) { return list && list.length ? h('div', { class: 'note warn', role: 'alert' }, list.map(function (e) { return h('div', null, fr(e)); })) : null; }

function loadForm() { var f = Object.assign(J.blankForm(), T.store.get(KEY.wip, {}) || {}); f.time = ''; return f; }
function saveForm(f) { var c = Object.assign({}, f); delete c.time; T.store.set(KEY.wip, c); }
function busy(root) { var a = document.activeElement; return !!(a && root.contains(a) && /^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)); }
function hasDraft() { var d = T.store.get(KEY.draft, null); return !!(d && typeof d === 'object' && Object.keys(d).length); }
function takeDraft() {
  if (!hasDraft()) return null;
  var d = T.store.get(KEY.draft, null), f = J.fromDraft(J.blankForm(), d);
  saveForm(f); T.store.set(KEY.draft, null); UI.errors = [];
  var su = J.setupText(f, true) || d.setup;
  return (f.kind === 'refus' ? 'Un refus' : 'Une décision') + (f.side ? ' ' + f.side : '') + (su ? ' sur « ' + su + ' »' : '') + ' arrive du desk Stratégie, champs pré-remplis. Vérifie, complète, puis inscris : rien n’est scellé tant que tu n’as pas inscrit.';
}
function markToday(rows) {
  var now = Date.now(), any = rows.some(function (r) { return J.inPeriod(r.at, 'jour', now, 'Europe/Paris'); });
  if (any && !T.day.get().done.journal) T.day.mark('journal');
}
function selfWrite(fn) { UI.self = true; try { return fn(); } finally { UI.self = false; } }

/* Une grille de paires libellé / valeur, en lecture seule. */
function kv(items) {
  return h('div', { class: 'grid2' }, items.filter(Boolean).map(function (it) {
    return h('div', { style: 'display:flex;flex-direction:column;gap:3px;min-width:0;padding:8px 10px;border:1px solid var(--line);border-radius:9px;background:var(--raise)' + (it[2] ? ';grid-column:1/-1' : '') },
      h('span', { class: 'mono', style: 'font-size:10px;letter-spacing:.07em;text-transform:uppercase;color:var(--mute)' }, it[0]),
      h('span', { class: it[2] ? null : 'mono', style: 'font-size:13.5px;color:var(--fg);overflow-wrap:anywhere;white-space:pre-wrap' }, it[1] == null || it[1] === '' ? '—' : String(it[1])));
  }));
}

/* ---------- Champs vivants : l’état suit la frappe, sans redessiner le champ ---------- */
function numField(o, st, key, live) {
  var el = U.field({ id: o.id, full: o.full, label: o.label, unit: o.unit, value: st[key], allowEmpty: true, min: o.min, placeholder: o.placeholder, hint: o.hint ? fr(o.hint) : null,
    onChange: function (v) { st[key] = fin(v) ? v : null; o.save && o.save(); live && live(); } });
  var inp = el.querySelector('input');
  inp.addEventListener('input', function () { var x = F.parse(inp.value); st[key] = fin(x) ? x : null; live && live(); });
  return el;
}
function textField(o, st, key) {
  var el = U.field({ id: o.id, type: o.type || 'text', full: o.full, label: o.label, value: st[key], placeholder: o.placeholder, hint: o.hint ? fr(o.hint) : null,
    onChange: function (v) { st[key] = v; o.save && o.save(); } });
  var inp = el.querySelector('input,textarea');
  inp.addEventListener('input', function () { st[key] = inp.value; });
  return el;
}

/* ---------- Saisir ---------- */
function renderSaisir(root, ctx, rows) {
  var set = ctx.settings, tz = tzOf(set);
  var dn = takeDraft(); if (dn) UI.draftNote = dn;
  if (UI.draftNote) root.appendChild(U.callout([h('b', null, 'Brouillon reçu. '), fr(UI.draftNote)]));

  var open = rows.filter(function (r) { return r.kind === 'pris' && r.status !== 'clos'; }).sort(function (a, b) { return b.at - a.at; });
  if (open.length) {
    var so = U.section('Positions *ouvertes*', plural(open.length, 'à clore', 'à clore'));
    open.forEach(function (r) { so.appendChild(openCard(r, set, ctx)); });
    so.appendChild(note('Toucher « Objectif » ou « Stop » reporte le prix prévu dans la sortie, si elle est vide. Le P&L et le R se calculent seuls, commission déduite.'));
    root.appendChild(so);
  }

  var s = U.section('Nouvelle *décision*', 'scellée à l’inscription');
  s.appendChild(todayLine(rows, set));
  var holder = h('div', { style: 'display:flex;flex-direction:column;gap:12px;min-width:0' });
  s.appendChild(holder);
  var form = loadForm();
  function save() { saveForm(form); }
  function redraw() {
    T.clear(holder);
    holder.appendChild(U.seg({ aria: 'Type de décision', options: [{ v: 'pris', label: 'Décision prise' }, { v: 'refus', label: 'Setup refusé' }], value: form.kind,
      onChange: function (v) { if (v === form.kind) return; form.kind = v; UI.errors = []; save(); redraw(); } }));
    holder.appendChild(form.kind === 'refus' ? cardRefus(form, set, save, redraw, submit) : cardPris(form, set, save, redraw, submit));
  }
  function submit() {
    var now = Date.now(), at = now, errs = [];
    if (form.time) {
      at = J.atFromTime(form.time, now, tz);
      if (!fin(at)) errs.push('L’heure de la décision est illisible.');
      else if (at > now + 60000) errs.push('L’heure de la décision est dans le futur.');
    }
    errs = J.validate(form).concat(errs);
    if (errs.length) { UI.errors = errs; UI.fresh = true; redraw(); UI.fresh = false; var eb = holder.querySelector('[role="alert"]'); if (eb && eb.scrollIntoView) eb.scrollIntoView({ block: 'center', behavior: 'smooth' }); return; }
    var e = J.buildEntry(Object.assign({}, form, { at: fin(at) ? at : now }), { now: now, pv: set.pointValue, comm: set.commissionRT, instrument: set.instrument });
    var id = selfWrite(function () { return T.journal.add(e); });
    T.day.mark('journal');
    var kind = form.kind, qty = form.qty;
    form = J.blankForm(); form.kind = kind; form.qty = fin(qty) ? qty : 1; saveForm(form);
    UI.errors = []; UI.draftNote = null; UI.justAdded = id;
    T.toast(kind === 'refus' ? 'Refus inscrit.' : 'Décision scellée : position ouverte.');
    ctx.rerender();
  }
  redraw();
  root.appendChild(s);
  root.appendChild(note('Les champs de décision — sens, setup, prix, taille, conviction, émotion, plan — se scellent à l’inscription et ne se modifient plus ; seule l’issue se complète ensuite. Un journal rempli le soir est un souvenir, pas une donnée : la mémoire d’une décision est révisée par son issue (ALP nº 3, partie IV, table 9).'));
}

function todayLine(rows, set) {
  var now = Date.now(), tz = tzOf(set), today = rows.filter(function (r) { return J.inPeriod(r.at, 'jour', now, tz); });
  var taken = today.filter(function (r) { return r.kind === 'pris'; }), refus = today.length - taken.length;
  var pnl = sum(taken.map(function (r) { return fin(r.pnl) ? r.pnl : 0; })), losses = taken.filter(function (r) { return r.pnl < 0; }).length;
  var hitT = taken.length >= set.maxTradesDay, hitL = losses >= set.maxLossesDay, hitS = pnl <= -set.dailyStop;
  var wrap = h('div', { style: 'display:flex;flex-direction:column;gap:8px' });
  wrap.appendChild(h('div', { class: 'row' },
    U.pill('Aujourd’hui'), U.pill(taken.length + ' / ' + set.maxTradesDay + ' pris', hitT ? 'no' : null),
    U.pill(losses + ' / ' + set.maxLossesDay + ' pertes', hitL ? 'no' : null), U.pill(F.usd(pnl, 0, true), hitS ? 'no' : null), U.pill(plural(refus, 'refus', 'refus'))));
  if (hitT || hitL || hitS) {
    var why = [hitT ? 'trades du jour' : null, hitL ? 'pertes du jour' : null, hitS ? 'stop du jour' : null].filter(Boolean).join(', ');
    wrap.appendChild(note('Limite atteinte (' + why + ') : ta règle dit d’arrêter. Si tu prends quand même un trade, inscris-le avec « Plan respecté : non » — c’est ce qui permettra d’en chiffrer le coût.', true));
  }
  return wrap;
}

function setupPicker(form, save, redraw, withOff) {
  var lv = J.LEVELS.slice(); if (withOff) lv.push(J.OFFPLAN);
  var out = [lab('Niveau', U.chips({ options: lv.map(function (l) { return { v: l, label: l }; }), value: form.level,
    onChange: function (v) { form.level = form.level === v ? null : v; if (form.level === J.OFFPLAN) form.conf = null; form.setupRaw = null; save(); redraw(); } }))];
  if (form.level !== J.OFFPLAN) out.push(lab('Confirmation', U.chips({ options: J.CONFS.map(function (c) { return { v: c, label: c }; }), value: form.conf,
    onChange: function (v) { form.conf = form.conf === v ? null : v; form.setupRaw = null; save(); redraw(); } })));
  else out.push(note('Un trade hors setup reste une décision : l’inscrire est ce qui permet d’en mesurer le coût.'));
  if (form.setupRaw && !form.level) out.push(note('Setup reçu tel quel : « ' + form.setupRaw + ' ». Choisis niveau et confirmation pour le ranger dans la grammaire, sinon il sera inscrit sous ce nom.'));
  return out;
}

function liveErrors(form, holder) {
  if (!UI.errors.length) return;
  UI.errors = J.validate(form);
  T.clear(holder); var eb = errBox(UI.errors); if (eb) holder.appendChild(eb);
}
function cardPris(form, set, save, redraw, submit) {
  var pv = set.pointValue, prev = h('div', { style: 'display:flex;flex-direction:column;gap:8px' }), errs = h('div');
  if (UI.errors.length && !UI.fresh) UI.errors = J.validate(form);
  function live() { liveErrors(form, errs); paint(); }
  function paint() {
    T.clear(prev);
    var t = { side: form.side, entry: form.entry, stop: form.stop, target: form.target, qty: fin(form.qty) && form.qty >= 1 ? form.qty : 1 };
    var ok = fin(t.entry) && fin(t.stop) && t.entry !== t.stop, pts = ok ? Math.abs(t.entry - t.stop) : NaN;
    var risk = ok ? J.riskUsd(t, pv) : NaN, rr = J.rr(t), nul = ok ? J.nullR(t, pv, set.commissionRT) : NaN, mq = J.maxQty(set.riskPerTrade, t, pv);
    prev.appendChild(U.kpis([
      { label: 'Risque engagé', value: fin(risk) ? F.usd(risk, 0) : '—', tone: risk > set.riskPerTrade ? 'neg' : null, hint: ok ? F.num(pts, 2) + ' pt × ' + t.qty + ' × ' + F.usd(pv, 0) : 'entrée et stop' },
      { label: 'Rapport prévu', value: fin(rr) ? F.num(rr, 2) : '—', unit: fin(rr) ? 'R' : null, hint: fin(rr) ? 'objectif sur risque' : 'objectif facultatif' },
      { label: 'Sans avantage', value: fin(nul) ? F.r(nul, 3) : '—', hint: 'loi nulle −c/L' },
      { label: 'Taille maximale', value: fin(mq) ? F.int(mq) : '—', unit: fin(mq) ? 'ct' : null, hint: 'à ' + F.usd(set.riskPerTrade, 0) + ' de risque' }
    ], 4));
    if (risk > set.riskPerTrade) prev.appendChild(note('Au-dessus de ta limite par trade (' + F.usd(set.riskPerTrade, 0) + '). La taille se calcule depuis le stop : à ce stop, ' + (mq >= 1 ? 'au plus ' + plural(mq, 'contrat') + '.' : 'même un contrat dépasse la limite.'), true));
  }
  var body = [
    lab('Sens', U.seg({ aria: 'Sens', options: [{ v: 'long', label: 'Long ↑' }, { v: 'short', label: 'Short ↓' }], value: form.side, onChange: function (v) { form.side = v; save(); redraw(); } }))
  ].concat(setupPicker(form, save, redraw, true));
  body.push(U.fields([
    numField({ id: 'j-entry', label: 'Entrée', unit: 'pt', save: save }, form, 'entry', live),
    numField({ id: 'j-stop', label: 'Stop', unit: 'pt', save: save }, form, 'stop', live),
    numField({ id: 'j-target', label: 'Objectif · facultatif', unit: 'pt', save: save }, form, 'target', live),
    numField({ id: 'j-qty', label: 'Quantité', unit: 'contrats', min: 1, save: save }, form, 'qty', live)
  ]));
  body.push(prev);
  body.push(lab('Conviction annoncée', U.seg({ aria: 'Conviction', options: [1, 2, 3, 4, 5].map(function (k) { return { v: k, label: String(k) }; }), value: form.conviction, onChange: function (v) { form.conviction = v; save(); redraw(); } }), 'Avant l’issue : c’est elle qui permet le test de calibration.'));
  body.push(lab('Émotion', U.chips({ options: J.EMOTIONS.map(function (e) { return { v: e, label: emoLabel(e) }; }), value: form.emotion, onChange: function (v) { form.emotion = form.emotion === v ? null : v; save(); redraw(); } })));
  body.push(lab('Plan respecté', U.seg({ aria: 'Plan respecté', options: [{ v: true, label: 'Oui' }, { v: false, label: 'Non' }], value: form.plan, onChange: function (v) { form.plan = v; save(); redraw(); } })));
  body.push(textField({ id: 'j-note', type: 'textarea', full: true, label: 'Note : ce que tu vois au moment de décider', placeholder: 'Contexte, raison, doute…', save: save }, form, 'note'));
  body.push(textField({ id: 'j-time', type: 'time', label: 'Heure de la décision', hint: 'Vide : maintenant. Plus de ' + J.LATE_MIN + ' min d’écart et la ligne sera marquée « inscrite après coup ».' }, form, 'time'));
  body.push(errs);
  body.push(wide(U.button({ label: 'Inscrire et sceller', kind: 'pri', onClick: submit })));
  paint(); var eb = errBox(UI.errors); if (eb) errs.appendChild(eb);
  return U.card({ title: 'Décision prise', meta: set.instrument + ' · ' + F.usd(pv, 0) + ' le point', body: body });
}

function cardRefus(form, set, save, redraw, submit) {
  if (UI.errors.length && !UI.fresh) UI.errors = J.validate(form);
  var body = [
    lab('Étape où le setup s’est arrêté', U.chips({ options: J.STAGES, value: form.stage, onChange: function (v) { form.stage = v; save(); redraw(); } })),
    h('div', { class: 'mono', style: 'font-size:10.5px;color:var(--mute);letter-spacing:.02em' }, 'Setup vu (facultatif)')
  ].concat(setupPicker(form, save, redraw, false));
  body.push(textField({ id: 'j-note', type: 'textarea', full: true, label: 'Note : pourquoi pas', placeholder: 'Ce qui manquait…', save: save }, form, 'note'));
  body.push(textField({ id: 'j-time', type: 'time', label: 'Heure du refus', hint: 'Vide : maintenant.' }, form, 'time'));
  var eb = errBox(UI.errors); if (eb) body.push(eb);
  body.push(wide(U.button({ label: 'Inscrire le refus', kind: 'pri', onClick: submit })));
  body.push(note('Un refus ne porte ni sens ni mise : une abstention qui porte une direction a été complétée après coup (ALP nº 3, partie IV). Les refus sont la moitié de l’information : sans eux, la compétence de ne pas trader reste invisible.'));
  return U.card({ title: 'Setup refusé', meta: 'abstention', body: body });
}

/* Clôture : sortie, fin, P&L et R recalculés à la frappe. */
function closeForm(row, set, ctx) {
  var st = UI.close[row.id] || (UI.close[row.id] = { exit: null, fin: null, apres: '' });
  var pv = fin(row.pv) ? row.pv : set.pointValue, comm = fin(row.comm) ? row.comm : set.commissionRT;
  var prev = h('div'), finBox = h('div'), errs = h('div');
  var exitF = numField({ id: 'j-exit-' + row.id, full: true, label: 'Prix de sortie', unit: 'pt' }, st, 'exit', paint), inp = exitF.querySelector('input');
  function drawFin() {
    T.clear(finBox);
    finBox.appendChild(lab('Fin', U.chips({ options: J.FINS, value: st.fin, onChange: function (v) {
      st.fin = v;
      if (st.exit == null) { var p0 = v === 'objectif' ? row.target : v === 'stop' ? row.stop : null; if (fin(p0)) { st.exit = p0; inp.value = String(p0).replace('.', ','); } }
      drawFin(); paint();
    } })));
  }
  function paint() {
    T.clear(prev);
    var p = fin(st.exit) ? J.pnl(Object.assign({}, row, { exit: st.exit }), pv, comm) : NaN, r = J.rMultiple(row, p, pv);
    prev.appendChild(U.kpis([
      { label: 'P&L net', value: fin(p) ? F.usd(p, 2, true) : '—', tone: p < 0 ? 'neg' : null, hint: fin(comm * row.qty) ? 'comm. ' + F.usd(comm * row.qty, 2) + ' déduite' : 'commission inconnue' },
      { label: 'Résultat', value: fin(r) ? F.r(r) : '—', tone: r < 0 ? 'neg' : fin(r) ? 'acc' : null, hint: 'risque ' + F.usd(J.riskUsd(row, pv), 2) }
    ]));
  }
  drawFin(); paint();
  var btn = U.button({ label: 'Clore la position', kind: 'acc', onClick: function () {
    var e = J.validateClose(row, st);
    T.clear(errs); if (e.length) { errs.appendChild(errBox(e)); return; }
    var patch = J.closePatch(row, st, Date.now(), { pv: pv, comm: comm });
    selfWrite(function () { T.journal.update(row.id, patch); });
    delete UI.close[row.id];
    T.toast('Position close : ' + F.usd(patch.pnl, 2, true) + ' · ' + F.r(patch.r));
    ctx.rerender();
  } });
  return h('div', { style: 'display:flex;flex-direction:column;gap:10px;min-width:0' },
    finBox, exitF, prev,
    textField({ id: 'j-apres-' + row.id, type: 'textarea', full: true, label: 'Ce que l’issue enseigne (facultatif)', placeholder: 'Écrit après l’issue, rangé à part de la note de décision.' }, st, 'apres'),
    errs, wide(btn));
}

function openCard(row, set, ctx) {
  var tz = tzOf(set);
  var head = h('div', { class: 'row', style: 'gap:6px' }, U.pill(sideLabel(row.side), 'acc'), U.pill('ouverte'), U.pill('scellée ' + J.timeIn(row.at, tz)));
  var info = h('div', { class: 'mono', style: 'font-size:12px;color:var(--soft);line-height:1.5' },
    'Entrée ' + px(row.entry) + ' · stop ' + px(row.stop) + (fin(row.target) ? ' · objectif ' + px(row.target) : '') + (fin(row.qty) ? ' · ' + plural(row.qty, 'contrat') : ''));
  var c = U.card({ title: row.setup || 'Décision', meta: J.dateIn(row.at, tz), accent: UI.justAdded === row.id, body: [head, info, closeForm(row, set, ctx)] });
  return c;
}

/* ---------- Registre ---------- */
function renderRegistre(root, ctx, rows) {
  var set = ctx.settings, tz = tzOf(set), now = Date.now();
  if (hasDraft()) root.appendChild(U.callout([h('b', null, 'Un brouillon t’attend. '), fr('Le desk Stratégie a préparé une décision. '), U.button({ label: 'Ouvrir la saisie', small: true, kind: 'acc', onClick: function () { ctx.setTab('saisir'); } })]));
  if (UI.sel) { var r = rows.find(function (x) { return x.id === UI.sel; }); if (r) { renderFiche(root, ctx, r); return; } UI.sel = null; }
  var period = T.store.get(KEY.filter, 'semaine');
  var list = rows.filter(function (r) { return J.inPeriod(r.at, period, now, tz); }).sort(function (a, b) { return b.at - a.at; });
  var s = U.section('Le *registre*', plural(list.length, 'ligne'));
  s.appendChild(U.seg({ aria: 'Période', options: [{ v: 'jour', label: 'Jour' }, { v: 'semaine', label: 'Semaine' }, { v: 'tout', label: 'Tout' }], value: period, onChange: function (v) { T.store.set(KEY.filter, v); ctx.rerender(); } }));
  var taken = list.filter(function (r) { return r.kind === 'pris'; }), pnl = sum(taken.map(function (r) { return fin(r.pnl) ? r.pnl : 0; }));
  var openN = taken.filter(function (r) { return r.status !== 'clos'; }).length;
  s.appendChild(U.kpis([
    { label: 'Décisions', value: F.int(list.length), hint: plural(list.length - taken.length, 'refus', 'refus') },
    { label: 'Prises', value: F.int(taken.length), hint: openN ? plural(openN, 'ouverte') : 'toutes closes' },
    { label: 'P&L net', value: F.usd(pnl, 0, true), tone: pnl < 0 ? 'neg' : null, hint: 'commissions déduites' },
    { label: 'R cumulés', value: F.r(sum(taken.map(function (r) { return fin(r.r) ? r.r : 0; })), 1), hint: 'somme des R clos' }
  ], 4));
  var labels = { jour: 'aujourd’hui', semaine: 'cette semaine', tout: 'au journal' };
  s.appendChild(U.table({
    cols: [
      { k: 'at', label: 'Date', fmt: function (v) { return J.dateIn(v, tz); } },
      { k: 'at', label: 'Heure', fmt: function (v) { return J.timeIn(v, tz); } },
      { k: 'kind', label: 'Type', fmt: function (v, r) { return v === 'refus' ? 'Refus' : r.status === 'clos' ? 'Pris' : 'Ouvert'; } },
      { k: 'side', label: 'Sens', fmt: function (v, r) { return r.kind === 'pris' ? sideLabel(v) : '—'; } },
      { k: 'r', label: 'R', align: 'r', fmt: function (v) { return fin(v) ? F.r(v) : '—'; } },
      { k: 'pnl', label: '$', align: 'r', fmt: function (v) { return fin(v) ? F.usd(v, 0, true) : '—'; } },
      { k: 'setup', label: 'Setup', fmt: function (v) { return v || '—'; } },
      { k: 'fin', label: 'Fin', fmt: function (v, r) { return r.kind === 'refus' ? 'arrêté · ' + stageLabel(r.stage) : r.status !== 'clos' ? 'ouverte' : finLabel(v); } }
    ],
    rows: list,
    rowClass: function (r) { return r.pnl < 0 ? 'neg' : null; },
    onRow: function (r) { UI.sel = r.id; UI.confirmDel = null; ctx.rerender(); window.scrollTo(0, 0); },
    empty: { title: 'Aucune décision ' + labels[period], text: fr('Chaque setup vu s’inscrit dans « Saisir » : pris ou refusé. Le registre garde tout, dans l’ordre où les décisions ont été prises.'), action: U.button({ label: 'Saisir une décision', small: true, kind: 'acc', onClick: function () { ctx.setTab('saisir'); } }) }
  }));
  if (list.length) s.appendChild(note('Toucher une ligne ouvre sa fiche : la décision en lecture seule, l’issue à compléter tant que la position est ouverte.'));
  root.appendChild(s);
  if (list.length) root.appendChild(exportBlock(list, tz, labels[period]));
}

function exportBlock(list, tz, label) {
  var s = U.section('Exporter', 'CSV · séparateur « ; »'), box = h('div', { style: 'display:flex;flex-direction:column;gap:8px' });
  function fallback(txt) {
    T.clear(box);
    var ta = h('textarea', { readonly: true, 'aria-label': 'Export CSV', style: 'width:100%;min-height:150px;border:1px solid var(--line-2);border-radius:9px;background:var(--raise);color:var(--fg);font:12px/1.4 var(--f-mono);padding:10px' });
    ta.value = txt; box.appendChild(ta); ta.focus(); ta.select();
    var ok = false; try { ok = document.execCommand && document.execCommand('copy'); } catch (e) { ok = false; }
    box.appendChild(note(ok ? 'Copié. Le texte reste sélectionné ci-dessus.' : 'Le presse-papiers est fermé ici : le texte est sélectionné, copie-le avec le menu du système.'));
    T.toast(ok ? 'CSV copié.' : 'CSV sélectionné.');
  }
  var btn = U.button({ label: 'Copier ' + plural(list.length, 'ligne') + ' en CSV', kind: 'ghost', small: true, onClick: function () {
    var txt = J.toCsv(list.slice().sort(function (a, b) { return a.at - b.at; }), tz);
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(txt).then(function () { T.clear(box); box.appendChild(note('Copié : ' + plural(list.length, 'ligne') + ' ' + label + ', virgule décimale, prêt pour un tableur.')); T.toast('CSV copié.'); }, function () { fallback(txt); });
    else fallback(txt);
  } });
  s.appendChild(h('div', { class: 'row' }, btn));
  s.appendChild(box);
  return s;
}

function renderFiche(root, ctx, r) {
  var set = ctx.settings, tz = tzOf(set), pris = r.kind === 'pris', closed = pris && r.status === 'clos';
  root.appendChild(h('div', { class: 'row' }, U.button({ label: '‹ Retour au registre', small: true, kind: 'ghost', onClick: function () { UI.sel = null; UI.confirmDel = null; ctx.rerender(); } })));
  var s = U.section(pris ? 'Une décision *prise*' : 'Un *refus*', J.dateLongIn(r.at, tz) + ' · ' + J.timeIn(r.at, tz));
  var late = J.lateMinutes(r);
  s.appendChild(U.flow({ nodes: [
    { ix: '1', title: pris ? 'Décision' : 'Refus', sub: 'scellée à ' + J.timeIn(r.at, tz) + (late > J.LATE_MIN ? ' · inscrite ' + F.dur(late) + ' après' : ''), state: 'done' },
    pris ? { ix: '2', title: 'Issue', sub: closed ? 'close à ' + J.timeIn(r.closedAt, tz) + ' · ' + F.r(r.r) + ' · ' + usd2(r.pnl) : 'à compléter : la position est ouverte', state: closed ? 'done' : 'active' }
      : { ix: '2', title: 'Issue contrefactuelle', sub: r.cf ? (J.CF.find(function (x) { return x.v === r.cf; }) || {}).label : 'ce que le setup aurait donné', state: r.cf ? 'done' : 'active' }
  ] }));
  if (late > J.LATE_MIN) s.appendChild(note('Inscrite ' + F.dur(late) + ' après la décision. Ce n’est pas une faute, c’est une donnée : la mémoire d’une décision est révisée par son issue (ALP nº 3, partie IV).', true));
  var pv = fin(r.pv) ? r.pv : set.pointValue;
  var dec = pris ? [
    ['Sens', sideLabel(r.side)], ['Setup', r.setup], ['Entrée', px(r.entry)], ['Stop', px(r.stop)], ['Objectif', px(r.target)], ['Quantité', fin(r.qty) ? plural(r.qty, 'contrat') : '—'],
    ['Risque engagé', fin(J.riskUsd(r, pv)) ? F.usd(J.riskUsd(r, pv), 2) : '—'], ['Rapport prévu', fin(J.rr(r)) ? F.num(J.rr(r), 2) + ' R' : '—'],
    ['Conviction', fin(r.conviction) ? r.conviction + ' / 5' : '—'], ['Émotion', r.emotion ? emoLabel(r.emotion) : '—'],
    ['Plan respecté', r.plan === true ? 'Oui' : r.plan === false ? 'Non' : '—'], ['Instrument', (r.instrument || set.instrument) + ' · ' + F.usd(pv, 0) + '/pt' + (fin(r.comm) ? ' · comm. ' + F.usd(r.comm, 2) : '')],
    r.note ? ['Note de décision', r.note, true] : null
  ] : [['Arrêté à l’étape', stageLabel(r.stage)], ['Setup vu', r.setup || '—'], ['Instrument', r.instrument || set.instrument], ['Heure', J.timeIn(r.at, tz)], r.note ? ['Note', r.note, true] : null];
  s.appendChild(U.card({ title: 'Décision', meta: U.pill('scellée'), body: kv(dec) }));
  if (pris && !closed) s.appendChild(U.card({ title: 'Issue', meta: 'à compléter', accent: true, body: closeForm(r, set, ctx) }));
  else if (closed) {
    s.appendChild(U.card({ title: 'Issue', meta: U.pill('clôturée', 'on'), body: [kv([
      ['Sortie', px(r.exit)], ['Fin', finLabel(r.fin)], ['P&L net', usd2(r.pnl)], ['Résultat', fin(r.r) ? F.r(r.r) : '—'],
      ['Close à', fin(r.closedAt) ? J.timeIn(r.closedAt, tz) : '—'], ['Durée', fin(r.closedAt) ? F.dur((r.closedAt - r.at) / 60000) : '—'],
      r.apres ? ['Après l’issue', r.apres, true] : null
    ]), note('Une issue close ne se modifie plus : un registre qu’on retouche cesse d’être une donnée. Une erreur de saisie se corrige en supprimant la ligne.')] }));
  } else {
    var cfBody = [U.chips({ options: J.CF, value: r.cf || null, onChange: function (v) { selfWrite(function () { T.journal.update(r.id, { cf: r.cf === v ? null : v }); }); ctx.rerender(); } }),
      note('Champ d’issue, renseigné après coup : ce que le setup refusé aurait donné s’il avait été pris. Sans lui, la moitié de la table de contingence reste vide et la compétence de refus n’est pas mesurable (ALP nº 3, partie IV).')];
    s.appendChild(U.card({ title: 'Issue contrefactuelle', meta: r.cf ? 'renseignée' : 'facultative', body: cfBody }));
  }
  root.appendChild(s);
  var del = U.section('Supprimer', null);
  if (UI.confirmDel === r.id) {
    del.appendChild(U.callout([h('b', null, 'Supprimer cette ligne ? '), fr('Elle disparaît du registre et des statistiques, sur cet appareil comme sur ton compte.'),
      h('div', { class: 'row', style: 'margin-top:10px' },
        U.button({ label: 'Confirmer la suppression', kind: 'acc', small: true, onClick: function () { selfWrite(function () { T.journal.remove(r.id); }); UI.sel = null; UI.confirmDel = null; T.toast('Ligne supprimée.'); ctx.rerender(); } }),
        U.button({ label: 'Annuler', kind: 'ghost', small: true, onClick: function () { UI.confirmDel = null; ctx.rerender(); } }))]));
  } else {
    del.appendChild(h('div', { class: 'row' }, U.button({ label: 'Supprimer la ligne', kind: 'ghost', small: true, onClick: function () { UI.confirmDel = r.id; ctx.rerender(); } })));
  }
  root.appendChild(del);
}

/* ---------- Statistiques ---------- */
function hub(center, tiles) {
  var wrap = h('div', { style: 'position:relative' }), svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('style', 'position:absolute;left:0;top:0;pointer-events:none;overflow:visible');
  var grid = U.kpis(tiles, 3); grid.style.marginTop = '34px';
  wrap.appendChild(svg); wrap.appendChild(center); wrap.appendChild(grid);
  T.observe(wrap, function () {
    if (!wrap.isConnected) return;
    var wr = wrap.getBoundingClientRect(), cr = center.getBoundingClientRect(), out = '', cx = cr.left + cr.width / 2 - wr.left, cy = cr.bottom - wr.top;
    svg.setAttribute('width', wr.width); svg.setAttribute('height', wr.height);
    Array.prototype.forEach.call(grid.children, function (el) {
      var r = el.getBoundingClientRect(); if (r.top - wr.top > cy + 60) return;
      var x = r.left + r.width / 2 - wr.left, y = r.top - wr.top;
      out += '<path d="M' + cx + ',' + cy + ' C' + cx + ',' + (cy + 22) + ' ' + x + ',' + (y - 22) + ' ' + x + ',' + y + '" fill="none" stroke="var(--line-2)" stroke-width="1.2"/><circle cx="' + x + '" cy="' + y + '" r="2.5" fill="var(--line-2)"/>';
    });
    out += '<circle cx="' + cx + '" cy="' + cy + '" r="3" fill="var(--violet)"/>';
    svg.innerHTML = out;
  });
  return wrap;
}

/* Jauge de la loi nulle : ton taux (trait blanc), son intervalle de Wilson (bande violette),
   le taux d’équilibre 1/(1 + b) (tirets). */
function nullGauge(p, w, eq) {
  return C.mount({ legend: [{ label: 'ton taux' }, { label: 'Wilson à 95 %', box: 'var(--violet-a)' }, { label: 'équilibre 1/(1 + b)', tone: 'mute', dash: true }] }, function (W) {
    var H = 66, l = 12, r = 12, sx = function (v) { return l + Math.max(0, Math.min(1, v)) * (W - l - r); }, g = '', X = T.esc;
    g += '<line x1="' + l + '" x2="' + (W - r) + '" y1="34" y2="34" stroke="var(--line-2)"/>';
    [0, 0.25, 0.5, 0.75, 1].forEach(function (v, i) { g += '<line x1="' + sx(v) + '" x2="' + sx(v) + '" y1="30" y2="38" stroke="var(--line-2)"/><text class="ax" x="' + sx(v) + '" y="60" text-anchor="' + (i === 0 ? 'start' : i === 4 ? 'end' : 'middle') + '">' + X(F.pct(v, 0)) + '</text>'; });
    if (fin(w.lo) && fin(w.hi)) g += '<rect x="' + sx(w.lo) + '" y="26" width="' + Math.max(2, sx(w.hi) - sx(w.lo)) + '" height="16" rx="3" fill="var(--violet-a)" stroke="var(--violet-b)"/>';
    if (fin(eq)) {
      var x = sx(eq), anc = x < 70 ? 'start' : x > W - 70 ? 'end' : 'middle';
      g += '<line x1="' + x + '" x2="' + x + '" y1="16" y2="48" stroke="var(--soft)" stroke-dasharray="3 3" stroke-width="1.3"/><text class="axl" x="' + x + '" y="11" text-anchor="' + anc + '">équilibre ' + X(F.pct(eq, 1)) + '</text>';
    }
    if (fin(p)) g += '<rect x="' + (sx(p) - 1.5) + '" y="22" width="3" height="24" rx="1.5" fill="var(--hi)"/>';
    return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '">' + g + '</svg>' };
  });
}

function wallSection(st) {
  var n = st.nClosed, pace = J.pace(n, st.activeDays), s = U.section('Le mur des *619*', 'ALP nº 3, partie VIII');
  var big = h('div', { style: 'display:flex;align-items:baseline;gap:8px;flex-wrap:wrap' },
    h('span', { class: 'mono', style: 'font-size:34px;font-weight:600;color:var(--hi);letter-spacing:-.02em' }, F.int(n)),
    h('span', { class: 'mono', style: 'font-size:14px;color:var(--soft)' }, '/ ' + J.WALL + ' décisions closes'),
    h('span', { class: 'mono', style: 'margin-left:auto;font-size:12px;color:var(--violet-2)' }, F.pct(Math.min(1, n / J.WALL), 1)));
  var phrase = h('p', { style: 'margin:0;font-family:var(--f-serif);font-style:italic;font-size:21px;line-height:1.25;color:var(--fg)' }, fr('Avant ' + J.WALL + ' décisions, le journal décrit ; il ne juge pas.'));
  var body = [big, C.gauge({ value: n, min: 0, max: J.WALL, band: [0, Math.min(n, J.WALL)], ticks: [[0, '0'], [J.WALL / 2, '310'], [J.WALL, String(J.WALL)]] }), phrase];
  if (pace && pace.left > 0) body.push(note('À ton rythme (' + F.num(pace.rate, 1) + ' décision close par séance active), il reste environ ' + F.int(pace.sessions) + ' séances, soit ' + F.num(pace.years, 1) + ' an' + (pace.years >= 2 ? 's' : '') + ' à ' + J.SESSIONS_PER_YEAR + ' séances par an.'));
  else if (pace) body.push(note('Le mur est franchi : les statistiques ci-dessous commencent à pouvoir juger, à la taxe de multiplicité près.'));
  body.push(note('Source : ALP nº 3 « Le seuil, et non le signal », partie VIII, table 14 — 619 décisions pour établir un Sharpe de 0,10 par décision, taxe de multiplicité comprise, soit 1,2 an à deux décisions par séance. Les refus n’entrent pas dans ce compte : le Sharpe se mesure sur les décisions prises.'));
  s.appendChild(U.card({ accent: true, body: body }));
  return s;
}

function dimSection(st) {
  var dims = [{ v: 'emotion', label: 'Émotion' }, { v: 'setup', label: 'Setup' }, { v: 'heure', label: 'Heure' }, { v: 'conviction', label: 'Conviction' }];
  var cur = T.store.get(KEY.dim, 'emotion'); if (!dims.some(function (d) { return d.v === cur; })) cur = 'emotion';
  var s = U.section('Où vont *les R*', 'par dimension'), holder = h('div', { style: 'display:flex;flex-direction:column;gap:10px;min-width:0' });
  function draw() {
    T.clear(holder);
    holder.appendChild(U.seg({ aria: 'Dimension', options: dims, value: cur, onChange: function (v) { cur = v; T.store.set(KEY.dim, v); draw(); } }));
    var groups = cur === 'emotion' ? st.byEmotion : cur === 'setup' ? st.bySetup : cur === 'heure' ? st.byHour : st.byConviction;
    var name = cur === 'emotion' ? emoLabel : cur === 'setup' ? function (k) { return k === '—' ? 'Non dit' : k; } : cur === 'heure' ? function (k) { return k === '—' ? '—' : pad2(k) + ' h'; } : function (k) { return k === '—' ? 'Non dite' : k + ' / 5'; };
    var short = cur === 'setup' ? function (k) { return k === '—' ? 'Non dit' : J.shortSetup(k); } : name;
    var vals = groups.map(function (g) { return fin(g.expR) ? g.expR : 0; });
    holder.appendChild(C.bar({ cats: groups.map(function (g) { return short(g.key); }), series: [{ name: 'E[R]', values: vals, tone: 'violet' }], horizontal: cur !== 'heure', fmt: function (v) { return F.r(v); }, ml: cur === 'heure' ? 54 : 96, height: 190 }));
    holder.appendChild(U.table({ cols: [
      { k: 'key', label: dims.find(function (d) { return d.v === cur; }).label, fmt: function (v) { return name(v); } },
      { k: 'n', label: 'n', align: 'r' },
      { k: 'expR', label: 'E[R]', align: 'r', fmt: function (v) { return fin(v) ? F.r(v) : '—'; } },
      { k: 'ciR', label: '± IC 95 %', align: 'r', fmt: function (v) { return fin(v) ? '± ' + F.num(v, 2) : '—'; } },
      { k: 'key', label: 'Lecture', fmt: function (v, g) { return J.read(g); } },
      { k: 'winRate', label: 'Réussite', align: 'r', fmt: function (v) { return fin(v) ? F.pct(v, 0) : '—'; } },
      { k: 'sum', label: 'P&L', align: 'r', fmt: function (v) { return F.usd(v, 0, true); } }
    ], rows: groups, rowClass: function (g) { return g.expR < 0 ? 'neg' : null; } }));
    if (cur === 'conviction') {
      var cb = st.calibration, txt = {
        constante: 'Conviction constante sur plus de 30 décisions : le test de calibration est sans objet. Ce n’est pas une faute, mais il faut le savoir plutôt que de croire le test passé.',
        'trop peu': 'Il faut au moins deux décisions closes à forte conviction (4–5) et deux à faible (1–2) pour comparer.',
        calibrée: 'Les intervalles se séparent : tes décisions à forte conviction battent celles à faible conviction. Une conviction calibrée est une compétence, même à espérance moyenne nulle (ALP nº 3, partie IV).',
        inversée: 'Les intervalles se séparent dans le mauvais sens : tes décisions à faible conviction battent celles à forte conviction.',
        indiscernable: 'Forte (4–5) : ' + F.r(cb.hi.expR) + ' sur ' + cb.hi.n + ' ; faible (1–2) : ' + F.r(cb.lo.expR) + ' sur ' + cb.lo.n + '. Les intervalles se recouvrent : la calibration n’est pas encore lisible.'
      }[cb.verdict];
      holder.appendChild(note('Calibration — ' + txt, cb.verdict === 'calibrée' || cb.verdict === 'inversée'));
    } else holder.appendChild(note('« Lecture » compare l’intervalle à 95 % de chaque espérance à zéro : « indistinct » veut dire que l’échantillon ne sépare pas ce groupe du hasard. Un écart entre deux groupes ne se lit qu’avec son incertitude.'));
  }
  draw(); s.appendChild(holder); return s;
}

function rulesSection(st) {
  var P = st.plan, s = U.section('Le coût des *règles enfreintes*', 'plan tenu ou non');
  if (!P.no.n) {
    s.appendChild(U.callout(fr(P.ok.n ? 'Aucune décision close hors plan : rien à chiffrer ici, et c’est le meilleur résultat possible de cette section.' : 'Le champ « Plan respecté » n’est renseigné sur aucune décision close.')));
    return s;
  }
  var gap = P.gapR, lost = P.lostR;
  s.appendChild(U.kpis([
    { label: 'Plan respecté', value: fin(P.ok.expR) ? F.r(P.ok.expR) : '—', tone: 'acc', hint: plural(P.ok.n, 'décision') + (fin(P.ok.winRate) ? ' · ' + F.pct(P.ok.winRate, 0) : '') },
    { label: 'Plan enfreint', value: fin(P.no.expR) ? F.r(P.no.expR) : '—', tone: 'neg', hint: plural(P.no.n, 'décision') + (fin(P.no.winRate) ? ' · ' + F.pct(P.no.winRate, 0) : '') },
    { label: 'P&L hors plan', value: F.usd(P.usd, 0, true), tone: P.usd < 0 ? 'neg' : null, hint: 'somme des entorses' },
    { label: 'Écart par entorse', value: fin(gap) ? F.r(gap) : '—', tone: gap < 0 ? 'neg' : null, hint: fin(lost) ? 'soit ' + F.num(Math.abs(lost), 1) + ' R ' + (lost > 0 ? 'perdus' : 'gagnés') : 'à comparer' }
  ], 4));
  var sep = fin(P.ok.ciR) && fin(P.no.ciR) ? (P.ok.expR - P.ok.ciR > P.no.expR + P.no.ciR ? 'Les intervalles à 95 % se séparent : sur cet échantillon, enfreindre le plan coûte, et ce n’est plus du bruit.' : 'Les intervalles à 95 % se recouvrent encore : l’écart est réel dans tes comptes, mais pas encore distinct du bruit.') : 'Pas assez de décisions dans l’un des deux groupes pour un intervalle.';
  s.appendChild(U.callout([h('b', null, fr(plural(P.no.n, 'entorse') + ' : ' + F.usd(P.usd, 0, true) + '. ')), fr('Dans le plan, une décision vaut ' + F.r(P.ok.expR) + ' ; hors plan, ' + F.r(P.no.expR) + '. ' + sep)]));
  if (P.nUnknown) s.appendChild(note(plural(P.nUnknown, 'décision close', 'décisions closes') + ' sans le champ « plan » ne ' + (P.nUnknown > 1 ? 'sont' : 'est') + ' dans aucun des deux groupes.'));
  return s;
}

function sankeySection(rows, st) {
  var s = U.section('De la décision *au résultat*', 'tout le journal');
  var closed = st.closed, nodes = [{ id: 'all', label: 'Décisions', col: 0 }], links = [];
  function add(id, label, col, tone, from, v, ltone) { if (!v) return; if (!nodes.some(function (n) { return n.id === id; })) nodes.push({ id: id, label: label, col: col, tone: tone }); links.push({ s: from, t: id, v: v, tone: ltone }); }
  add('ref', 'Refus', 1, 'mute', 'all', st.nRefus);
  var ok = closed.filter(function (t) { return t.plan === true; }), no = closed.filter(function (t) { return t.plan === false; }), un = closed.filter(function (t) { return t.plan !== true && t.plan !== false; });
  add('ok', 'Plan tenu', 1, 'violet', 'all', ok.length, 'violet');
  add('no', 'Plan enfreint', 1, 'mute', 'all', no.length);
  add('un', 'Plan non dit', 1, 'mute', 'all', un.length);
  add('op', 'Ouvertes', 1, 'mute', 'all', st.nOpen);
  [['ok', ok, 'violet'], ['no', no, null], ['un', un, null]].forEach(function (g) {
    var w = g[1].filter(function (t) { return t.pnl > 0; }).length, l = g[1].filter(function (t) { return t.pnl < 0; }).length, z = g[1].length - w - l;
    add('g', 'Gagnantes', 2, null, g[0], w, g[2]); add('p', 'Perdantes', 2, 'mute', g[0], l, g[2]); add('z', 'Nulles', 2, 'mute', g[0], z, g[2]);
  });
  s.appendChild(C.sankey({ nodes: nodes, links: links, height: 250 }));
  s.appendChild(note('Les flux violets suivent les décisions prises dans le plan. Sans dérive, un filtre réduit le nombre d’occasions sans améliorer l’espérance (ALP nº 3, partie III) : le schéma montre ton plan travailler, il ne juge pas une compétence.'));
  return s;
}

function refusSection(st) {
  var s = U.section('Les *refus*', 'la moitié de l’information'), ct = st.contingency;
  s.appendChild(U.kpis([
    { label: 'Part des refus', value: fin(st.refusShare) ? F.pct(st.refusShare, 0) : '—', hint: plural(st.nRefus, 'refus', 'refus') + ' · ' + plural(st.nTaken, 'prise') },
    { label: 'Refus renseignés', value: F.int(ct.refusG + ct.refusP + ct.refusN), unit: '/ ' + st.nRefus, hint: 'issue contrefactuelle' }
  ]));
  if (st.byStage.length) s.appendChild(C.bar({ cats: st.byStage.map(function (x) { return stageLabel(x.key); }), series: [{ name: 'Refus', values: st.byStage.map(function (x) { return x.n; }), tone: 'mute' }], horizontal: true, fmt: function (v) { return F.int(v); }, ml: 96 }));
  s.appendChild(U.table({ cols: [{ k: 'l', label: 'Issue' }, { k: 'a', label: 'Prise', align: 'r' }, { k: 'b', label: 'Refusée', align: 'r' }], rows: [
    { l: 'Gagnante', a: ct.prisG, b: ct.refusG },
    { l: 'Non gagnante', a: ct.prisP, b: ct.refusP },
    { l: 'Ni l’un ni l’autre', a: '—', b: ct.refusN },
    { l: 'Inconnue', a: st.nOpen, b: ct.refusX }
  ] }));
  s.appendChild(note('Table de contingence décision × issue. L’issue d’un refus se renseigne dans sa fiche (registre) : ce que le setup aurait donné. Sans elle, la compétence de refus — souvent la principale — n’est pas identifiable, quelle que soit la taille de l’échantillon (ALP nº 3, partie IV).'));
  return s;
}

function renderStats(root, ctx, rows) {
  var set = ctx.settings, tz = tzOf(set), st = J.stats(rows, tz);
  if (hasDraft()) root.appendChild(U.callout([h('b', null, 'Un brouillon t’attend. '), U.button({ label: 'Ouvrir la saisie', small: true, kind: 'acc', onClick: function () { ctx.setTab('saisir'); } })]));
  root.appendChild(wallSection(st));
  if (!st.nClosed) {
    root.appendChild(U.empty({ title: st.nOpen ? 'Aucune décision close pour l’instant' : 'Les statistiques apparaîtront à la première décision close',
      text: fr('Courbe de capital, distribution des R, taux de réussite contre son équilibre, coût des règles enfreintes : tout se calcule depuis le journal, rien n’est simulé ici.'),
      action: U.button({ label: st.nOpen ? 'Clore une position' : 'Saisir une décision', small: true, kind: 'acc', onClick: function () { ctx.setTab('saisir'); } }) }));
    if (st.nRefus) root.appendChild(refusSection(st));
    return;
  }
  var w = st.wilson, ciTxt = fin(st.ciR) ? 'IC 95 % ± ' + F.num(st.ciR, 2) + ' R' : 'IC : il faut deux décisions';
  var center = h('div', { class: 'card accent', style: 'max-width:300px;margin:0 auto;text-align:center' },
    h('div', { class: 'cb', style: 'align-items:center;gap:4px;padding:14px' },
      h('div', { class: 'mono', style: 'font-size:10px;letter-spacing:.16em;color:var(--violet-2)' }, 'ESPÉRANCE PAR DÉCISION'),
      h('div', { class: 'mono', style: 'font-size:30px;font-weight:600;color:var(--hi);letter-spacing:-.02em' }, F.r(st.expR)),
      h('div', { class: 'mono', style: 'font-size:11px;color:var(--mute)' }, ciTxt + ' · n = ' + st.nClosed)));
  var s1 = U.section('Le *hub* des résultats', plural(st.nClosed, 'décision close', 'décisions closes'));
  s1.appendChild(hub(center, [
    { label: 'Réussite', value: fin(st.winRate) ? F.pct(st.winRate, 0) : '—', hint: 'Wilson ' + F.num(w.lo * 100, 0) + ' à ' + F.pct(w.hi, 0) },
    { label: 'Facteur de profit', value: F.num(st.profitFactor, 2), hint: 'gains / pertes en $' },
    { label: 'P&L net', value: F.usd(st.net, 0, true), tone: st.net < 0 ? 'neg' : null, hint: 'creux max ' + F.usd(st.maxDD, 0) },
    { label: 'Espérance', value: F.usd(st.expUsd, 2, true), tone: st.expUsd < 0 ? 'neg' : null, hint: 'par décision close' },
    { label: 'Séries max', value: st.streaks.win + ' G · ' + st.streaks.loss + ' P', hint: 'gains, pertes de suite' },
    { label: 'Part des refus', value: fin(st.refusShare) ? F.pct(st.refusShare, 0) : '—', hint: plural(st.nRefus, 'refus', 'refus') }
  ]));
  root.appendChild(s1);

  var s2 = U.section('Courbe *de capital*', 'P&L net cumulé, en dollars');
  var pts = [[0, 0]].concat(st.equity.map(function (v, i) { return [i + 1, v]; }));
  var differs = st.plan.no.n || st.plan.nUnknown;
  var series = [{ name: 'Toutes', points: pts, tone: 'fg', area: true }];
  if (differs) series.push({ name: 'Plan respecté seul', points: [[0, 0]].concat(st.equityPlan.map(function (v, i) { return [i + 1, v]; })), tone: 'violet', dash: true });
  s2.appendChild(C.line({ series: series, x: { type: 'num', fmt: function (v) { return Math.abs(v - Math.round(v)) < 1e-9 ? '#' + Math.round(v) : ''; } }, y: { fmt: function (v) { return F.usd(v, 0); }, zero: true }, ml: 58, height: 220 }));
  s2.appendChild(note('Abscisse : rang de la décision close. ' + (differs ? 'La courbe violette ne garde que les décisions où le plan est respecté : l’écart entre les deux est ce que les entorses ont coûté, ou rapporté, sur cet échantillon. ' : '') + 'Creux maximal : ' + F.usd(st.maxDD, 0) + '.'));
  root.appendChild(s2);

  var R = st.closed.map(function (t) { return t.r; }).filter(fin);
  var lo = Math.min(-1, Math.floor(Math.min.apply(null, R) * 4) / 4), hi = Math.max(1, Math.ceil(Math.max.apply(null, R) * 4) / 4), bw = (hi - lo) / 0.25 > 40 ? (hi - lo) / 40 : 0.25;
  var s3 = U.section('Distribution *des R*', bw === 0.25 ? 'une barre par quart de R' : 'une barre par ' + F.num(bw, 2) + ' R');
  s3.appendChild(C.hist({ values: R, min: lo, max: hi, bins: Math.max(4, Math.round((hi - lo) / bw)), fmt: function (v) { return F.num(v, 1); },
    refs: [{ x: 0, tone: 'dim' }, { x: st.expR, tone: 'violet' }].concat(fin(st.nullR) ? [{ x: st.nullR, tone: 'mute', dash: true }] : []) }));
  s3.appendChild(h('div', { class: 'legend' },
    h('span', null, h('i', { class: 'violet' }), 'E[R] ' + F.r(st.expR)),
    fin(st.nullR) ? h('span', null, h('i', { class: 'mute dash' }), 'sans avantage ' + F.r(st.nullR)) : null,
    h('span', null, h('i', { style: 'border-color:var(--line-2)' }), 'zéro')));
  s3.appendChild(note('Repère violet : ton espérance. Tirets : l’espérance sans avantage, −c/L, la commission rapportée au risque (ALP nº 3, partie XI : à dérive nulle, aucune géométrie ne crée d’espérance). Le glissement n’y est pas compté : la vraie loi nulle est un peu plus basse.'));
  root.appendChild(s3);

  var s4 = U.section('Réussite et *loi nulle*', 'contre son équilibre');
  s4.appendChild(nullGauge(st.winRate, w, st.pEq));
  var vw = !fin(st.pEq) ? 'Sans gain ou sans perte, le taux d’équilibre n’est pas défini.' : w.lo > st.pEq ? 'L’intervalle de Wilson est entièrement au-dessus de l’équilibre : à ton payoff, ton taux de réussite bat le hasard sur cet échantillon.' : w.hi < st.pEq ? 'L’intervalle est entièrement au-dessous de l’équilibre : à ce payoff, ce taux perd.' : 'L’intervalle contient l’équilibre : ton taux de réussite ne se distingue pas encore du hasard.';
  s4.appendChild(U.kpis([
    { label: 'Taux de réussite', value: fin(st.winRate) ? F.pct(st.winRate, 1) : '—', hint: st.wins + ' sur ' + st.nClosed },
    { label: 'Équilibre', value: fin(st.pEq) ? F.pct(st.pEq, 1) : '—', hint: fin(st.payoff) ? 'payoff b = ' + F.num(st.payoff, 2) : 'payoff indéfini' },
    { label: 'Gain moyen', value: fin(st.avgWinR) ? F.r(st.avgWinR) : '—', hint: 'sur les gagnantes' },
    { label: 'Perte moyenne', value: fin(st.avgLossR) ? F.r(-st.avgLossR) : '—', tone: 'neg', hint: 'sur les perdantes' }
  ], 4));
  s4.appendChild(note(vw + ' Wilson : (p̂ + z²/2n ± z·√(p̂(1 − p̂)/n + z²/4n²)) / (1 + z²/n), z = 1,96. Équilibre : 1/(1 + b), le taux auquel l’espérance s’annule.'));
  var ve = !fin(st.ciR) ? '' : (st.expR - st.ciR > 0 ? ' L’intervalle de l’espérance est au-dessus de zéro.' : st.expR + st.ciR < 0 ? ' L’intervalle de l’espérance est sous zéro.' : ' L’intervalle de l’espérance contient zéro.');
  s4.appendChild(note('Espérance : ' + F.r(st.expR) + (fin(st.ciR) ? ' ± ' + F.num(st.ciR, 2) : '') + ' par décision, contre ' + (fin(st.nullR) ? F.r(st.nullR, 3) : '—') + ' sans avantage.' + ve));
  root.appendChild(s4);

  root.appendChild(rulesSection(st));
  root.appendChild(sankeySection(rows, st));
  root.appendChild(dimSection(st));
  root.appendChild(refusSection(st));
  root.appendChild(note('Sources : ALP nº 3 « Le seuil, et non le signal » — partie IV (table 9 : les sept champs et la frontière temporelle), partie VIII (table 14 : le mur de 619 décisions), partie XI (à dérive nulle, E[R] = −c/L). Toutes les autres valeurs de cette page viennent de ton journal.'));
}

/* =====================================================================
   4. Le desk
   ===================================================================== */
T.desk({
  id: 'journal', label: 'Journal', glyph: 'J', group: 'Exécution', order: 60,
  tabs: [{ id: 'saisir', label: 'Saisir' }, { id: 'registre', label: 'Registre' }, { id: 'stats', label: 'Statistiques' }],
  render: function (root, ctx) {
    var set = ctx.settings;
    if (ctx.tab !== 'registre') { UI.sel = null; UI.confirmDel = null; }
    root.appendChild(U.page({ kicker: 'Journal · ' + set.instrument, title: 'Noter *avant* de savoir.', lede: fr('Chaque décision s’inscrit au moment où elle se prend, refus compris, et se scelle avant l’issue. Le registre garde tout ; les statistiques se lisent chacune contre leur loi nulle.') }));
    root.appendChild(U.tabs({ tabs: this.tabs, value: ctx.tab, onChange: function (t) { UI.sel = null; UI.confirmDel = null; ctx.setTab(t); } }));
    var rows = T.journal.list();
    markToday(rows);
    if (ctx.tab === 'registre') renderRegistre(root, ctx, rows);
    else if (ctx.tab === 'stats') renderStats(root, ctx, rows);
    else renderSaisir(root, ctx, rows);
    UI.justAdded = null;
    var pending = false, timer = null;
    var un = T.journal.on(function () { if (UI.self) return; if (busy(root)) { pending = true; return; } ctx.rerender(); });
    function onOut() { if (!pending) return; clearTimeout(timer); timer = setTimeout(function () { if (pending && !busy(root)) { pending = false; ctx.rerender(); } }, 700); }
    root.addEventListener('focusout', onOut);
    return function () { un(); clearTimeout(timer); root.removeEventListener('focusout', onOut); };
  }
});
