/* Desks « Routine & revue » et « Réglages ».
   La routine porte la discipline : un état d'esprit relevé avant la séance, des disjoncteurs pendant,
   une revue du processus après, et des paliers qui gardent le réel fermé tant que les règles ne tiennent
   pas en simulation. Les seuils de préparation et de palier sont des RÈGLES DÉCLARÉES, pas des mesures :
   ils disent ce que l'opérateur s'engage à respecter, et rien sur le marché.
   Source du seul nombre de recherche employé : ALP nº 3, partie VIII, table 14 — 619 décisions pour
   établir un Sharpe de 0,10 par décision (constante WALL, contrôlée par test/routine.test.js). */
var h = T.h, U = T.ui, C = T.chart, F = T.fmt;
T.lib = T.lib || {};
var R = T.lib.routine = {};
var K = { days: 'routine:days', pause: 'routine:pause' };
R.KEYS = K;
R.WALL = 619;

/* =====================================================================
   1. Fonctions pures — aucun DOM, aucun T.store
   ===================================================================== */
function fin(v) { return typeof v === 'number' && isFinite(v); }
function pad(n) { return String(n).padStart(2, '0'); }
function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }

R.CHECKS = [
  { id: 'sommeil', t: 'Nuit correcte', s: 'Pas de séance après une nuit blanche : la fatigue coûte plus cher que la séance manquée.' },
  { id: 'regles', t: 'Règles relues', s: 'Risque par trade, perte maximale du jour, nombre de trades : lus, pas récités.' },
  { id: 'macro', t: 'Calendrier vu', s: 'Les heures d’impact fort de la journée sont connues avant d’ouvrir le graphique.' },
  { id: 'plan', t: 'Plan écrit', s: 'Biais, niveaux et déclencheur écrits d’avance ; un seul setup par séance.' },
  { id: 'stop', t: 'Perte maximale acceptée', s: 'Si elle tombe, la séance est finie. C’est décidé maintenant, pas à chaud.' },
  { id: 'revanche', t: 'Aucune revanche à prendre', s: 'La séance d’hier est close ; rien n’est à « récupérer » aujourd’hui.' },
  { id: 'cadre', t: 'Cadre calme', s: 'Notifications coupées, pas d’autre écran, pas de trade en marchant.' }
];
R.MODES = [
  { v: 'replay', label: 'Replay', s: 'Rejouer une séance passée' },
  { v: 'sim', label: 'Simulateur', s: 'Temps réel, argent fictif' },
  { v: 'eval', label: 'Évaluation', s: 'Compte d’évaluation prop' },
  { v: 'reel', label: 'Réel', s: 'Argent engagé' }
];
R.GRADES = [
  { v: 'A', score: 4, s: 'Plan suivi à la lettre, refus compris' },
  { v: 'B', score: 3, s: 'Un écart mineur, sans effet sur le risque' },
  { v: 'C', score: 2, s: 'Un écart qui a changé une décision' },
  { v: 'D', score: 1, s: 'Plusieurs écarts, ou une règle de risque touchée' },
  { v: 'E', score: 0, s: 'Séance hors plan : revanche, taille, stop déplacé' }
];
R.gradeScore = function (g) { var x = R.GRADES.filter(function (r) { return r.v === g; })[0]; return x ? x.score : NaN; };

/* Préparation : 60 % la liste, 20 % le sommeil, 20 % le calme (stress inversé). Échelles de 1 à 5.
   Verdict déclaré : ≥ 80 séance normale ; 60 à 80 taille réduite de moitié ; < 60 simulateur seulement. */
R.READY = { go: 80, half: 60 };
R.readiness = function (o) {
  o = o || {};
  var n = R.CHECKS.length, done = R.CHECKS.filter(function (c) { return o.checks && o.checks[c.id]; }).length;
  var sl = fin(o.sleep) ? clamp(o.sleep, 1, 5) : null, st = fin(o.stress) ? clamp(o.stress, 1, 5) : null;
  var parts = { liste: 60 * done / n, sommeil: sl == null ? 0 : 20 * (sl - 1) / 4, calme: st == null ? 0 : 20 * (5 - st) / 4 };
  var score = Math.round(parts.liste + parts.sommeil + parts.calme);
  var complete = sl != null && st != null;
  var verdict = !complete ? 'incomplet' : score >= R.READY.go ? 'go' : score >= R.READY.half ? 'demi' : 'sim';
  return { score: score, done: done, n: n, parts: parts, complete: complete, verdict: verdict };
};
R.VERDICT = {
  incomplet: { t: 'À compléter', s: 'sommeil et tension à noter' },
  go: { t: 'Normale', s: 'la taille du plan, pas plus' },
  demi: { t: 'Demi-taille', s: 'ou un seul trade' },
  sim: { t: 'Simulateur', s: 'aucun argent engagé' }
};

/* Jour (AAAA-MM-JJ) d'un instant, dans un fuseau. */
var DTF = {};
R.dayOf = function (ms, tz) {
  tz = tz || 'Europe/Paris';
  try {
    var f = DTF[tz] || (DTF[tz] = new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' }));
    var o = {}; f.formatToParts(new Date(ms)).forEach(function (p) { o[p.type] = p.value; });
    return o.year + '-' + o.month + '-' + o.day;
  } catch (e) { var d = new Date(ms); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
};
R.isDay = function (s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s); };
R.addDays = function (day, n) { var t = Date.UTC(+day.slice(0, 4), +day.slice(5, 7) - 1, +day.slice(8, 10)) + n * 864e5, d = new Date(t); return d.getUTCFullYear() + '-' + pad(d.getUTCMonth() + 1) + '-' + pad(d.getUTCDate()); };
R.weekday = function (day) { return new Date(Date.UTC(+day.slice(0, 4), +day.slice(5, 7) - 1, +day.slice(8, 10))).getUTCDay(); };

/* Statistiques d'une journée depuis le journal. Pertes consécutives : celles qui terminent la journée. */
R.dayStats = function (trades, day, tz) {
  var out = { taken: 0, refus: 0, open: 0, closed: 0, wins: 0, losses: 0, pnl: 0, r: 0, consec: 0, planOk: 0, planN: 0, rows: [] };
  (trades || []).filter(function (t) { return t && fin(t.at) && R.dayOf(t.at, tz) === day; }).sort(function (a, b) { return a.at - b.at; }).forEach(function (t) {
    out.rows.push(t);
    if (t.kind === 'refus') { out.refus++; return; }
    out.taken++;
    if (t.plan === true || t.plan === false) { out.planN++; if (t.plan) out.planOk++; }
    if (t.status !== 'clos') { out.open++; return; }
    out.closed++;
    var p = fin(t.pnl) ? t.pnl : 0; out.pnl += p; if (fin(t.r)) out.r += t.r;
    if (p > 0) { out.wins++; out.consec = 0; } else if (p < 0) { out.losses++; out.consec++; }
  });
  return out;
};

/* Disjoncteurs : chaque limite du réglage, son état ('ok' | 'alerte' | 'stop'). Pause après deux pertes de suite. */
R.PAUSE_MIN = 15;
R.breakers = function (st, set) {
  var lim = function (v, m) { return !fin(m) || m <= 0 ? 'ok' : v >= m ? 'stop' : v >= m - 1 ? 'alerte' : 'ok'; };
  var loss = Math.max(0, -st.pnl), ds = set.dailyStop;
  var lossState = !fin(ds) || ds <= 0 ? 'ok' : loss >= ds ? 'stop' : loss >= 0.6 * ds ? 'alerte' : 'ok';
  return [
    { id: 'trades', t: 'Trades', v: st.taken, max: set.maxTradesDay, state: lim(st.taken, set.maxTradesDay), unit: '' },
    { id: 'pertes', t: 'Pertes', v: st.losses, max: set.maxLossesDay, state: lim(st.losses, set.maxLossesDay), unit: '' },
    { id: 'stop', t: 'Perte du jour', v: loss, max: ds, state: lossState, unit: '$' },
    { id: 'serie', t: 'De suite', v: st.consec, max: 2, state: st.consec >= 2 ? 'pause' : st.consec === 1 ? 'alerte' : 'ok', unit: '' }
  ];
};
R.sessionState = function (br) {
  if (br.some(function (b) { return b.state === 'stop'; })) return 'stop';
  if (br.some(function (b) { return b.state === 'pause'; })) return 'pause';
  if (br.some(function (b) { return b.state === 'alerte'; })) return 'alerte';
  return 'ok';
};

/* Processus contre résultat : les quatre cases. La case dangereuse est « hors plan, gagné » : elle récompense l'écart. */
R.matrix = function (trades) {
  var m = { okWin: 0, okLoss: 0, offWin: 0, offLoss: 0, n: 0 };
  (trades || []).forEach(function (t) {
    if (!t || t.kind === 'refus' || t.status !== 'clos' || (t.plan !== true && t.plan !== false) || !fin(t.pnl) || t.pnl === 0) return;
    m.n++;
    if (t.plan) { if (t.pnl > 0) m.okWin++; else m.okLoss++; } else { if (t.pnl > 0) m.offWin++; else m.offLoss++; }
  });
  return m;
};

/* Progression : chaque séance classée par mode, et ses chiffres de discipline.
   days : { 'AAAA-MM-JJ': { mode, review:{grade} } }. Une séance compte si elle a une revue. */
R.sessions = function (days, trades, set) {
  set = set || {}; var tz = set.tz || 'Europe/Paris';
  var byDay = {};
  (trades || []).forEach(function (t) { if (!t || !fin(t.at)) return; var d = R.dayOf(t.at, tz); (byDay[d] = byDay[d] || []).push(t); });
  return Object.keys(days || {}).filter(R.isDay).sort().map(function (d) {
    var x = days[d] || {}, st = R.dayStats(byDay[d] || [], d, tz);
    var breach = fin(set.dailyStop) && set.dailyStop > 0 && -st.pnl > set.dailyStop;
    var over = (fin(set.maxTradesDay) && set.maxTradesDay > 0 && st.taken > set.maxTradesDay) || (fin(set.maxLossesDay) && set.maxLossesDay > 0 && st.losses > set.maxLossesDay);
    return { day: d, mode: x.mode || null, reviewed: !!(x.review && x.review.grade), grade: x.review && x.review.grade || null, score: x.review ? R.gradeScore(x.review.grade) : NaN, taken: st.taken, planOk: st.planOk, planN: st.planN, pnl: st.pnl, breach: breach, over: over };
  });
};

/* Paliers déclarés : replay → simulateur → évaluation → réel. Chaque palier s'ouvre quand le précédent est tenu. */
R.LADDER = [
  { mode: 'replay', t: 'Replay', s: 'Apprendre le geste', need: 10, adh: 0.8, clean: 0 },
  { mode: 'sim', t: 'Simulateur', s: 'Tenir les règles en temps réel', need: 20, adh: 0.9, clean: 20 },
  { mode: 'eval', t: 'Évaluation', s: 'Les mêmes règles, avec un objectif', need: 20, adh: 0.9, clean: 20 },
  { mode: 'reel', t: 'Réel', s: 'Taille minimale d’abord', need: 0, adh: 0.9, clean: 0 }
];
/* Pour un palier : séances revues, adhérence au plan (décisions prises), séances propres consécutives
   (revue faite, aucune limite dépassée, note A ou B) — comptées depuis la plus récente. */
R.gate = function (sess, step) {
  var s = sess.filter(function (x) { return x.mode === step.mode && x.reviewed; });
  var ok = 0, n = 0; s.forEach(function (x) { ok += x.planOk; n += x.planN; });
  var clean = 0; for (var i = s.length - 1; i >= 0; i--) { var x = s[i]; if (!x.breach && !x.over && x.score >= 3) clean++; else break; }
  var adh = n ? ok / n : NaN;
  var pass = s.length >= step.need && (step.need === 0 || (fin(adh) && adh >= step.adh)) && clean >= step.clean;
  return { sessions: s.length, adh: adh, decisions: n, clean: clean, pass: pass };
};
R.ladder = function (sess) {
  var open = true;
  return R.LADDER.map(function (step) {
    var g = R.gate(sess, step), st = !open ? 'ferme' : g.pass && step.need > 0 ? 'tenu' : 'ouvert';
    if (!(g.pass && step.need > 0)) open = false;
    return Object.assign({}, step, g, { state: st });
  });
};

/* Série : jours ouvrés consécutifs avec une revue, jusqu'à aujourd'hui (aujourd'hui sans revue ne casse pas la série). */
R.streak = function (days, today) {
  var n = 0, d = today, first = true;
  for (var k = 0; k < 400; k++) {
    var wd = R.weekday(d);
    if (wd !== 0 && wd !== 6) {
      var x = days && days[d], ok = !!(x && x.review && x.review.grade);
      if (ok) n++; else if (!first) break;
      first = false;
    }
    d = R.addDays(d, -1);
  }
  return n;
};

/* Grille des dernières semaines : lignes lun → ven, colonnes semaines ; valeur = note (0 à 4), NaN sans revue. */
R.grid = function (days, today, weeks) {
  weeks = weeks || 12;
  var wd = R.weekday(today), monday = R.addDays(today, -((wd + 6) % 7));
  var start = R.addDays(monday, -7 * (weeks - 1)), cols = [], values = [[], [], [], [], []];
  for (var w = 0; w < weeks; w++) {
    var m = R.addDays(start, 7 * w); cols.push(m.slice(8, 10) + '/' + m.slice(5, 7));
    for (var i = 0; i < 5; i++) {
      var d = R.addDays(m, i), x = days && days[d];
      values[i].push(d > today ? NaN : x && x.review && x.review.grade ? R.gradeScore(x.review.grade) : NaN);
    }
  }
  return { rows: ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven'], cols: cols, values: values };
};

/* Garde les 400 jours les plus récents. */
R.prune = function (days) {
  var keys = Object.keys(days || {}).filter(R.isDay).sort(), out = {};
  keys.slice(-400).forEach(function (k) { out[k] = days[k]; });
  return out;
};

/* ---------- Réglages : instruments, export, import ---------- */
R.SPEC = { MNQ: { pointValue: 2, tick: 0.25, name: 'Micro E-mini Nasdaq-100' }, NQ: { pointValue: 20, tick: 0.25, name: 'E-mini Nasdaq-100' } };
R.TZS = [{ v: 'Europe/Paris', label: 'Paris' }, { v: 'Europe/London', label: 'Londres' }, { v: 'America/New_York', label: 'New York' }, { v: 'America/Chicago', label: 'Chicago' }];
R.exportDoc = function (store, journal, at) {
  return { app: 'ALP Desk', version: 1, exportedAt: at, store: store || {}, journal: journal || [] };
};
/* Signature d'une ligne de journal : deux lignes identiques ne s'importent pas deux fois. */
R.sig = function (t) { return [t.at, t.kind, t.side || '', t.entry == null ? '' : t.entry, t.setup || ''].join('|'); };
R.validateImport = function (doc) {
  if (!doc || typeof doc !== 'object' || doc.app !== 'ALP Desk') return { ok: false, why: 'Ce fichier ne vient pas d’ALP Desk.' };
  if (doc.store != null && (typeof doc.store !== 'object' || Array.isArray(doc.store))) return { ok: false, why: 'La section des réglages est illisible.' };
  if (doc.journal != null && !Array.isArray(doc.journal)) return { ok: false, why: 'La section du journal est illisible.' };
  var keys = Object.keys(doc.store || {}).filter(function (k) { return /^[A-Za-z0-9_.~:@+-]{1,120}$/.test(k); });
  var rows = (doc.journal || []).filter(function (t) { return t && typeof t === 'object' && fin(t.at) && (t.kind === 'pris' || t.kind === 'refus'); });
  return { ok: true, keys: keys, rows: rows };
};
R.newRows = function (existing, rows) {
  var seen = {}; (existing || []).forEach(function (t) { seen[R.sig(t)] = true; });
  return rows.filter(function (t) { var s = R.sig(t); if (seen[s]) return false; seen[s] = true; return true; });
};

/* =====================================================================
   2. Rendu
   ===================================================================== */
function today() { return T.day.key(); }
function getDays() { var d = T.store.get(K.days, {}); return d && typeof d === 'object' ? d : {}; }
function getDay(day) { return getDays()[day] || {}; }
function setDay(day, patch) { var all = getDays(); all[day] = Object.assign({}, all[day] || {}, patch); T.store.set(K.days, R.prune(all)); }
function modeLabel(v) { var m = R.MODES.filter(function (x) { return x.v === v; })[0]; return m ? m.label : '—'; }
function stTone(s) { return s === 'stop' ? 'acc' : s === 'pause' ? 'acc' : s === 'alerte' ? 'on' : null; }
function stLabel(s) { return { ok: 'libre', alerte: 'dernier', stop: 'atteint', pause: 'pause' }[s] || s; }

/* ---------- Avant ---------- */
function tabAvant(root, ctx) {
  var day = today(), x = getDay(day), rd = R.readiness(x), v = R.VERDICT[rd.verdict];
  var s0 = U.section('L’état *avant* le marché', F.dateLong ? F.dateLong(Date.now()) : day);
  s0.appendChild(U.kpis([
    { label: 'Préparation', value: String(rd.score), unit: '/ 100', hint: rd.done + ' / ' + rd.n + ' points cochés', tone: rd.verdict === 'go' ? 'acc' : null },
    { label: 'Verdict', value: v.t, hint: v.s, tone: rd.verdict === 'sim' ? 'neg' : null },
    { label: 'Mode du jour', value: modeLabel(x.mode), hint: 'à choisir plus bas' }
  ], 3));
  s0.appendChild(h('div', { class: 'rt-gauge' }, C.gauge({ value: rd.score, min: 0, max: 100, band: [R.READY.go, 100], ticks: [[0, '0'], [R.READY.half, String(R.READY.half)], [R.READY.go, String(R.READY.go)], [100, '100']] })));
  s0.appendChild(U.note('Sous ' + R.READY.half + ' : simulateur seulement. De ' + R.READY.half + ' à ' + R.READY.go + ' : la moitié de la taille. Ces seuils sont une règle que tu te donnes, pas une mesure : ils servent à décider avant d’avoir envie de trader.'));
  root.appendChild(s0);

  var s1 = U.section('Comment tu *arrives*', 'de 1 à 5');
  var scale = function (key, label, lo, hi) {
    return h('div', { class: 'rt-scale' }, h('div', { class: 'rt-sl' }, h('b', null, label), h('span', null, lo + ' → ' + hi)),
      U.seg({ options: [1, 2, 3, 4, 5].map(function (n) { return { v: n, label: String(n) }; }), value: x[key], onChange: function (n) { var p = {}; p[key] = n; setDay(day, p); ctx.rerender(); } }));
  };
  s1.appendChild(scale('sleep', 'Sommeil', 'très mauvais', 'très bon'));
  s1.appendChild(scale('stress', 'Tension', 'calme', 'à cran'));
  root.appendChild(s1);

  var s2 = U.section('La liste *du matin*', 'cochée chaque jour');
  s2.appendChild(U.checklist({ items: R.CHECKS, checked: x.checks || {}, onToggle: function (id, on) { var c = Object.assign({}, getDay(day).checks || {}); if (on) c[id] = true; else delete c[id]; setDay(day, { checks: c }); ctx.rerender(); } }));
  root.appendChild(s2);

  var s3 = U.section('Où tu *trades* aujourd’hui', 'mode de séance');
  s3.appendChild(U.seg({ options: R.MODES.map(function (m) { return { v: m.v, label: m.label, disabled: rd.verdict === 'sim' && m.v !== 'replay' && m.v !== 'sim', title: m.s }; }), value: x.mode, onChange: function (m) { setDay(day, { mode: m }); ctx.rerender(); } }));
  if (rd.verdict === 'sim') s3.appendChild(U.note('Le verdict du jour ferme l’évaluation et le réel : le choix reste entre replay et simulateur.', true));
  var lad = R.ladder(R.sessions(getDays(), T.journal.list(), ctx.settings));
  var reelOpen = lad[3].state !== 'ferme', evalOpen = lad[2].state !== 'ferme';
  if ((x.mode === 'reel' && !reelOpen) || (x.mode === 'eval' && !evalOpen)) s3.appendChild(U.callout([h('b', null, 'Palier non atteint. '), 'Les paliers de l’onglet Progression ne sont pas encore tenus pour ce mode. Rien ne t’empêche de trader, mais la séance sera comptée hors protocole.']));
  s3.appendChild(U.fields([{ label: 'Intention du jour', type: 'text', full: true, value: x.intention || '', placeholder: 'Ce que je fais, ce que je refuse', onChange: function (t) { setDay(day, { intention: String(t).slice(0, 240) }); T.toast('Intention enregistrée'); } }]));
  root.appendChild(s3);

  var all = rd.complete && rd.done === rd.n;
  root.appendChild(U.callout([h('b', null, all ? 'Prêt. ' : 'Pas encore. '), all ? 'La suite est sur la carte de séance : macro, biais, fenêtre, déclencheur, risque.' : 'Chaque point non coché est une raison de plus de rester en simulateur aujourd’hui.']));
  root.appendChild(h('div', { class: 'rt-acts' }, U.button({ label: 'Ouvrir le desk Macro', kind: 'ghost', small: true, onClick: function () { T.nav.go('macro'); } }), U.button({ label: 'Voir la carte de séance', kind: 'ghost', small: true, onClick: function () { T.nav.go('home'); } })));
}

/* ---------- Pendant ---------- */
function tabPendant(root, ctx) {
  var set = ctx.settings, day = today(), st = R.dayStats(T.journal.list(), day, set.tz), br = R.breakers(st, set), ss = R.sessionState(br);
  var pause = T.store.get(K.pause, null), now = Date.now(), paused = pause && fin(pause.until) && pause.until > now;
  var head = { ok: ['Séance ouverte', 'Aucune limite atteinte.'], alerte: ['Dernière marge', 'Une limite est à un pas : la prochaine décision se prend plus lentement.'], pause: ['Pause obligatoire', 'Deux pertes de suite : ' + R.PAUSE_MIN + ' minutes loin de l’écran avant la décision suivante.'], stop: ['Séance terminée', 'Une limite est atteinte. Ferme la plateforme ; la revue t’attend.'] }[ss];
  var s0 = U.section('Les *disjoncteurs*', 'depuis le journal du jour');
  s0.appendChild(h('div', { class: 'rt-state', 'data-s': ss }, h('b', null, head[0]), h('span', null, head[1])));
  s0.appendChild(h('div', { class: 'rt-brk' }, br.map(function (b) {
    var used = fin(b.max) && b.max > 0 ? clamp(b.v / b.max, 0, 1) : 0;
    var val = b.unit === '$' ? F.usd(b.v, 0) : F.int(b.v), mx = b.unit === '$' ? F.usd(b.max, 0) : F.int(b.max);
    return h('div', { class: 'rt-b', 'data-s': b.state }, h('div', { class: 'rt-bh' }, h('b', null, b.t), U.pill(stLabel(b.state), stTone(b.state))),
      h('div', { class: 'rt-bv' }, val, h('small', null, ' / ' + mx)), h('div', { class: 'rt-bar' }, h('i', { style: 'width:' + (used * 100).toFixed(1) + '%' })));
  })));
  s0.appendChild(U.note('Les limites viennent des Réglages (' + F.int(set.maxTradesDay) + ' trades, ' + F.int(set.maxLossesDay) + ' pertes, ' + F.usd(set.dailyStop, 0) + ' de perte du jour). La pause après deux pertes de suite est une règle du desk.'));
  root.appendChild(s0);

  var s1 = U.section('La *pause*', R.PAUSE_MIN + ' minutes');
  var clock = h('div', { class: 'rt-big' }, '—'), timer = null;
  function tick() {
    var p = T.store.get(K.pause, null), left = p && fin(p.until) ? p.until - Date.now() : 0;
    if (left <= 0) { clock.textContent = 'libre'; clock.removeAttribute('data-on'); if (timer && p) { clearInterval(timer); timer = null; T.store.set(K.pause, null); ctx.rerender(); } return; }
    var m = Math.floor(left / 60000), s = Math.floor(left % 60000 / 1000); clock.textContent = pad(m) + ':' + pad(s); clock.setAttribute('data-on', '1');
  }
  tick(); if (paused) timer = setInterval(tick, 1000);
  s1.appendChild(U.card({ body: [clock, h('p', { class: 'rt-cap' }, paused ? 'Lève-toi, bois de l’eau, relis ton plan. La prochaine décision attend la fin du compte.' : 'Une pause se prend avant d’en avoir besoin : après deux pertes, après un gain qui donne envie de doubler, après une colère.'),
    h('div', { class: 'rt-acts' }, paused ? U.button({ label: 'Arrêter la pause', kind: 'ghost', small: true, onClick: function () { T.store.set(K.pause, null); ctx.rerender(); } }) : U.button({ label: 'Lancer ' + R.PAUSE_MIN + ' minutes', kind: ss === 'pause' ? 'acc' : 'pri', small: true, onClick: function () { T.store.set(K.pause, { until: Date.now() + R.PAUSE_MIN * 60000, at: Date.now() }); ctx.rerender(); } }))] }));
  root.appendChild(s1);

  var s2 = U.section('La *journée* en chiffres', st.taken + ' pris · ' + st.refus + ' refus');
  s2.appendChild(U.kpis([
    { label: 'P&L du jour', value: F.usd(st.pnl, 0, true), hint: st.closed + ' clos, ' + st.open + ' ouvert' + (st.open > 1 ? 's' : ''), tone: st.pnl < 0 ? 'neg' : null },
    { label: 'Résultat en R', value: F.r ? F.r(st.r) : F.num(st.r, 2), hint: 'somme des trades clos' },
    { label: 'Plan respecté', value: st.planN ? F.pct(st.planOk / st.planN, 0) : '—', hint: st.planOk + ' / ' + st.planN + ' décisions' },
    { label: 'Refus', value: F.int(st.refus), hint: 'comptés à part' }
  ], 4));
  if (st.taken) {
    var eq = [[0, 0]], cum = 0; st.rows.filter(function (t) { return t.kind !== 'refus' && t.status === 'clos'; }).forEach(function (t, i) { cum += fin(t.pnl) ? t.pnl : 0; eq.push([i + 1, cum]); });
    if (eq.length > 1) s2.appendChild(U.card({ title: 'Courbe du jour', meta: 'en dollars', flush: true, body: C.line({ series: [{ name: 'P&L', points: eq, tone: 'violet', area: true }], x: { type: 'num', fmt: function (v) { return v ? '#' + v : ''; } }, y: { fmt: function (v) { return F.usd(v, 0); }, zero: true }, hlines: fin(set.dailyStop) && set.dailyStop > 0 ? [{ y: -set.dailyStop, label: 'perte max', tone: 'mute' }] : [], height: 170 }) }));
  } else s2.appendChild(U.empty({ title: 'Aucune décision aujourd’hui', text: 'Les compteurs se remplissent depuis le journal : chaque trade et chaque refus saisis dans le desk Journal.', action: U.button({ label: 'Saisir une décision', kind: 'pri', small: true, onClick: function () { T.nav.go('journal', 'saisir'); } }) }));
  root.appendChild(s2);

  var s3 = U.section('Les signaux de *tilt*', 'à reconnaître');
  s3.appendChild(U.prose([
    '<b>Le stop déplacé.</b> Un stop qu’on éloigne transforme une perte prévue en perte imprévue. La règle : il ne bouge que vers le gain.',
    '<b>La taille qui grossit après une perte.</b> Elle cherche à récupérer, pas à exécuter le plan.',
    '<b>Le trade hors fenêtre.</b> Hors des heures du plan, le setup n’a pas été préparé.',
    '<b>L’ennui.</b> Une séance sans setup est une séance réussie ; l’envie d’agir n’est pas un signal.'
  ]));
  root.appendChild(s3);
  return function () { if (timer) clearInterval(timer); };
}

/* ---------- Après ---------- */
function tabApres(root, ctx) {
  var set = ctx.settings, day = today(), all = T.journal.list(), st = R.dayStats(all, day, set.tz), x = getDay(day), rv = x.review || {};
  var s0 = U.section('La *revue* du soir', T.day.get().done.revue ? 'faite aujourd’hui' : 'à faire');
  s0.appendChild(U.kpis([
    { label: 'Décisions', value: F.int(st.taken + st.refus), hint: st.taken + ' prises, ' + st.refus + ' refus' },
    { label: 'P&L du jour', value: F.usd(st.pnl, 0, true), tone: st.pnl < 0 ? 'neg' : null, hint: 'pas la note' },
    { label: 'Plan respecté', value: st.planN ? F.pct(st.planOk / st.planN, 0) : '—', hint: st.planOk + ' / ' + st.planN },
    { label: 'Série', value: F.int(R.streak(getDays(), day)), unit: 'j', hint: 'jours ouvrés revus' }
  ], 4));
  s0.appendChild(U.note('La note porte sur le processus, jamais sur le résultat : une perte dans le plan vaut A, un gain hors plan vaut au mieux C.'));
  root.appendChild(s0);

  var s1 = U.section('La note du *processus*', 'A à E');
  var draft = { grade: rv.grade || null, good: rv.good || '', mistake: rv.mistake || '', lesson: rv.lesson || '', rule: rv.rule || '' };
  var gradeBox = h('div', { class: 'rt-grades' });
  function paintGrades() {
    T.clear(gradeBox);
    R.GRADES.forEach(function (g) {
      gradeBox.appendChild(h('button', { type: 'button', class: 'rt-g', 'aria-pressed': String(draft.grade === g.v), on: { click: function () { draft.grade = g.v; paintGrades(); } } }, h('b', null, g.v), h('span', null, g.s)));
    });
  }
  paintGrades();
  s1.appendChild(gradeBox);
  s1.appendChild(U.fields([
    { label: 'Ce qui a été bien fait', type: 'textarea', full: true, value: draft.good, placeholder: 'Un geste précis, pas une impression', onChange: function (t) { draft.good = t; } },
    { label: 'L’erreur principale', type: 'textarea', full: true, value: draft.mistake, placeholder: 'Une seule : celle qui a coûté le plus', onChange: function (t) { draft.mistake = t; } },
    { label: 'La leçon, en une phrase', type: 'text', full: true, value: draft.lesson, onChange: function (t) { draft.lesson = t; } },
    { label: 'Règle à tester (pas à adopter)', type: 'text', full: true, value: draft.rule, placeholder: 'À éprouver en simulateur d’abord', onChange: function (t) { draft.rule = t; } }
  ]));
  s1.appendChild(h('div', { class: 'rt-acts' }, U.button({ label: rv.grade ? 'Mettre à jour la revue' : 'Enregistrer la revue', kind: 'pri', onClick: function () {
    var a = document.activeElement; if (a && a.blur) a.blur();
    if (!draft.grade) { T.toast('Choisis une note de A à E'); return; }
    var clip = function (s, n) { return String(s || '').slice(0, n); };
    setDay(day, { review: { grade: draft.grade, good: clip(draft.good, 600), mistake: clip(draft.mistake, 600), lesson: clip(draft.lesson, 240), rule: clip(draft.rule, 240), savedAt: Date.now() } });
    T.day.mark('revue'); T.toast('Revue enregistrée'); ctx.rerender();
  } })));
  root.appendChild(s1);

  var m = R.matrix(all);
  var s2 = U.section('Processus contre *résultat*', m.n + ' trades clos et qualifiés');
  var cell = function (k, t, s, tone) { return h('div', { class: 'rt-c', 'data-t': tone || '' }, h('div', { class: 'rt-cn' }, F.int(m[k])), h('b', null, t), h('span', null, s)); };
  s2.appendChild(h('div', { class: 'rt-mx' },
    h('div', { class: 'rt-ax' }), h('div', { class: 'rt-ax' }, 'Plan respecté'), h('div', { class: 'rt-ax' }, 'Plan enfreint'),
    h('div', { class: 'rt-ax rt-ay' }, 'Gagné'), cell('okWin', 'Mérité', 'Le plan a travaillé.'), cell('offWin', 'Chanceux', 'La case dangereuse : elle récompense l’écart.', 'acc'),
    h('div', { class: 'rt-ax rt-ay' }, 'Perdu'), cell('okLoss', 'Le coût du métier', 'Une perte prévue, dans le plan.'), cell('offLoss', 'Mérité aussi', 'L’écart a été puni ; tant mieux qu’il l’ait été.')));
  s2.appendChild(U.note(m.n ? 'Sur tout le journal. Sans avantage, un trade dans le plan touche son objectif au taux d’équilibre de sa géométrie, 1 / (1 + R:R) (ALP nº 3) : une perte isolée ne dit rien du plan.' : 'Les cases se remplissent avec les trades clos dont le champ « plan respecté » est renseigné dans le Journal.'));
  root.appendChild(s2);

  var s3 = U.section('Les décisions *du jour*', st.rows.length + ' ligne' + (st.rows.length > 1 ? 's' : ''));
  s3.appendChild(U.table({ cols: [
    { k: 'at', label: 'Heure', fmt: function (v) { return T.time.hhmm(set.tz, new Date(v)); } },
    { k: 'kind', label: 'Décision', fmt: function (v, r) { return v === 'refus' ? 'refus' : (r.side === 'short' ? 'vente' : 'achat'); } },
    { k: 'pnl', label: 'P&L', align: 'r', fmt: function (v, r) { return r.kind === 'refus' ? '' : r.status !== 'clos' ? 'ouvert' : F.usd(v, 0, true); } },
    { k: 'plan', label: 'Plan', fmt: function (v, r) { return r.kind === 'refus' ? '' : v === true ? 'oui' : v === false ? 'non' : ''; } }
  ], rows: st.rows, empty: { title: 'Aucune décision aujourd’hui', text: 'Une journée sans trade se revoit aussi : la note dit si le plan a été tenu.' } }));
  root.appendChild(s3);
}

/* ---------- Progression ---------- */
function tabProgression(root, ctx) {
  var set = ctx.settings, days = getDays(), all = T.journal.list(), sess = R.sessions(days, all, set), lad = R.ladder(sess), day = today();
  var taken = all.filter(function (t) { return t.kind === 'pris'; }).length;
  var reviewed = sess.filter(function (s) { return s.reviewed; });
  var s0 = U.section('Du replay *au réel*', 'quatre paliers');
  s0.appendChild(U.flow({ nodes: lad.map(function (st, i) {
    var sub = st.need ? F.int(Math.min(st.sessions, st.need)) + ' / ' + st.need + ' séances · plan ' + (fin(st.adh) ? F.pct(st.adh, 0) : '—') + (st.clean ? ' · ' + st.clean + ' propre' + (st.clean > 1 ? 's' : '') : '') : 'Ouvert quand l’évaluation est tenue';
    return { title: st.t + ' — ' + st.s, sub: sub, state: st.state === 'tenu' ? 'done' : st.state === 'ouvert' ? 'active' : 'todo', go: st.state === 'tenu' ? 'tenu' : st.state === 'ouvert' ? 'en cours' : 'fermé' };
  }) }));
  root.appendChild(s0);
  var s0b = U.section('Ce que chaque palier *exige*', 'règles déclarées');
  s0b.appendChild(U.table({ cols: [
    { k: 't', label: 'Palier' },
    { k: 'need', label: 'Séances', align: 'r', fmt: function (v) { return v ? F.int(v) : '—'; } },
    { k: 'adh', label: 'Plan', align: 'r', fmt: function (v, r) { return r.need ? '≥ ' + F.pct(r.adhReq, 0) : '—'; } },
    { k: 'clean', label: 'Propres', align: 'r', fmt: function (v, r) { return r.cleanReq ? F.int(r.cleanReq) : '—'; } }
  ], rows: R.LADDER.map(function (s) { return { t: s.t, need: s.need, adhReq: s.adh, cleanReq: s.clean }; }) }));
  s0b.appendChild(U.note('Une séance propre : revue faite, aucune limite dépassée, note A ou B. Le compte repart de zéro à la première séance qui ne l’est pas. Ces paliers prouvent une discipline, pas un avantage : la preuve d’un avantage demande ' + R.WALL + ' décisions (ALP nº 3, partie VIII, table 14).'));
  root.appendChild(s0b);

  var s1 = U.section('La *régularité*', 'dernières semaines');
  s1.appendChild(U.kpis([
    { label: 'Séances revues', value: F.int(reviewed.length), hint: 'depuis le début' },
    { label: 'Série', value: F.int(R.streak(days, day)), unit: 'j', hint: 'jours ouvrés de suite' },
    { label: 'Preuve', value: F.int(taken), unit: '/ ' + R.WALL, hint: 'décisions prises', onClick: function () { T.nav.go('journal', 'stats'); } },
    { label: 'Note moyenne', value: reviewed.length ? R.GRADES[4 - Math.round(T.stats.mean(reviewed.slice(-20).map(function (s) { return s.score; })))].v : '—', hint: 'sur 20 dernières revues' }
  ], 4));
  var wk = (typeof window !== 'undefined' && window.innerWidth < 600) ? 8 : 12, g = R.grid(days, day, wk);
  s1.appendChild(U.card({ title: 'Notes de processus', meta: '4 = A · 0 = E', flush: true, body: C.heat({ rows: g.rows, cols: g.cols, values: g.values, corner: 'sem.', fmt: function (v) { return R.GRADES[4 - v] ? R.GRADES[4 - v].v : ''; } }) }));
  s1.appendChild(U.note('Une case vide est un jour ouvré sans revue. La couleur suit la note : plus elle est soutenue, mieux le plan a été tenu.'));
  root.appendChild(s1);

  var last = reviewed.slice(-60);
  var s2 = U.section('La note *dans le temps*', last.length + ' revue' + (last.length > 1 ? 's' : ''));
  if (last.length >= 2) {
    var pts = last.map(function (s, i) { return [i + 1, s.score]; }), mv = [], adh = [];
    last.forEach(function (s, i) { var w = last.slice(Math.max(0, i - 4), i + 1); mv.push([i + 1, T.stats.mean(w.map(function (y) { return y.score; }))]); });
    var ok = 0, n = 0; last.forEach(function (s, i) { ok += s.planOk; n += s.planN; adh.push([i + 1, n ? 100 * ok / n : null]); });
    s2.appendChild(U.card({ title: 'Note de processus', meta: 'et sa moyenne sur cinq séances', flush: true, body: C.line({ series: [{ name: 'Note', points: pts, tone: 'mute' }, { name: 'Moyenne 5 séances', points: mv, tone: 'violet' }], x: { type: 'num', fmt: function (v) { return '#' + v; } }, y: { min: 0, max: 4, fmt: function (v) { return R.GRADES[4 - Math.round(v)] ? R.GRADES[4 - Math.round(v)].v : ''; } }, height: 180 }) }));
    if (adh.some(function (p) { return p[1] != null; })) s2.appendChild(U.card({ title: 'Plan respecté, cumulé', meta: 'pointillé : palier 90 %', flush: true, body: C.line({ series: [{ name: 'Plan respecté', points: adh, tone: 'fg' }], x: { type: 'num', fmt: function (v) { return '#' + v; } }, y: { min: 0, max: 100, fmt: function (v) { return F.num(v, 0) + ' %'; } }, hlines: [{ y: 90, label: '', tone: 'violet' }], height: 170 }) }));
    var modes = R.MODES.map(function (m) { return sess.filter(function (s) { return s.reviewed && s.mode === m.v; }).length; });
    s2.appendChild(U.card({ title: 'Séances revues par mode', flush: true, body: C.bar({ cats: R.MODES.map(function (m) { return m.label; }), series: [{ name: 'Séances', values: modes, tone: 'violet' }], fmt: function (v) { return F.int(v); }, height: 160 }) }));
  } else s2.appendChild(U.empty({ title: 'Deux revues suffisent pour une courbe', text: 'Chaque soir, l’onglet Après enregistre la note du processus. La courbe apparaît à la deuxième.', action: U.button({ label: 'Faire la revue du jour', kind: 'pri', small: true, onClick: function () { ctx.setTab('apres'); } }) }));
  root.appendChild(s2);
}

T.desk({
  id: 'routine', label: 'Routine & revue', glyph: 'P', group: 'Discipline', order: 70,
  tabs: [{ id: 'avant', label: 'Avant' }, { id: 'pendant', label: 'Pendant' }, { id: 'apres', label: 'Après' }, { id: 'progression', label: 'Progression' }],
  render: function (root, ctx) {
    var tab = ctx.tab, titles = {
      avant: ['Routine · avant', 'Arriver *préparé*.', 'Une note de sommeil et de tension, sept points cochés, un mode de séance. Le verdict se prend avant d’avoir envie de trader.'],
      pendant: ['Routine · pendant', 'Les *disjoncteurs*.', 'Les limites du jour se lisent dans le journal, en direct. Quand l’une tombe, la séance s’arrête : la décision a été prise ce matin.'],
      apres: ['Routine · après', 'Noter le *processus*.', 'Le résultat d’un trade dépend du marché ; la note, seulement de toi. La revue juge la seconde.'],
      progression: ['Routine · progression', 'Mériter *le réel*.', 'Replay, simulateur, évaluation, réel : chaque palier s’ouvre quand le précédent est tenu, séance après séance.']
    }[tab] || [];
    root.appendChild(U.page({ kicker: titles[0], title: titles[1], lede: titles[2] }));
    root.appendChild(U.tabs({ tabs: this.tabs, value: tab, onChange: ctx.setTab }));
    var un = [T.journal.on(function () { if (tab === 'pendant' || tab === 'apres') ctx.rerender(); })], cl = null;
    if (tab === 'avant') tabAvant(root, ctx);
    else if (tab === 'pendant') cl = tabPendant(root, ctx);
    else if (tab === 'apres') tabApres(root, ctx);
    else tabProgression(root, ctx);
    return function () { un.forEach(function (f) { f(); }); if (cl) cl(); };
  }
});

/* =====================================================================
   3. Réglages
   ===================================================================== */
function collectStore() {
  var out = {};
  try { for (var i = 0; i < localStorage.length; i++) { var k = localStorage.key(i); if (k && k.indexOf('alpdesk:s:') === 0) { var key = k.slice(10); try { out[key] = T.store.get(key); } catch (e) {} } } } catch (e) {}
  return out;
}
function download(name, text) {
  var b = new Blob([text], { type: 'application/json' }), u = URL.createObjectURL(b), a = h('a', { href: u, download: name });
  document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(u); a.remove(); }, 500);
}

T.desk({
  id: 'reglages', label: 'Réglages', glyph: 'S', group: 'Système', order: 90,
  render: function (root, ctx) {
    var set = ctx.settings, sp = R.SPEC[set.instrument] || R.SPEC.MNQ;
    root.appendChild(U.page({ kicker: 'Système · réglages', title: 'Les *constantes* du desk.', lede: 'Instrument, frais, fenêtre et limites : chaque desk lit ces valeurs. Elles se changent ici, une fois, et s’appliquent partout.' }));
    var save = function (patch, msg) { T.settings.set(patch); T.toast(msg || 'Réglage enregistré'); };

    var s0 = U.section('L’*instrument*', 'CME · Nasdaq-100');
    s0.appendChild(U.seg({ options: [{ v: 'MNQ', label: 'MNQ · micro' }, { v: 'NQ', label: 'NQ · E-mini' }], value: set.instrument, onChange: function (v) { var s = R.SPEC[v]; T.settings.set({ instrument: v, pointValue: s.pointValue, tick: s.tick }); T.toast(v + ' sélectionné'); ctx.rerender(); } }));
    s0.appendChild(U.kpis([
      { label: 'Valeur du point', value: F.usd(sp.pointValue, 0), hint: sp.name },
      { label: 'Pas de cotation', value: F.num(sp.tick, 2), unit: 'pt', hint: F.usd(sp.tick * sp.pointValue, 2) + ' par tick' },
      { label: 'Risque par trade', value: F.num(set.riskPerTrade / sp.pointValue, 1), unit: 'pt', hint: F.usd(set.riskPerTrade, 0) + ' pour un contrat' }
    ], 3));
    s0.appendChild(U.note('Spécifications publiques CME : NQ 20 $ le point, MNQ 2 $, pas de 0,25 point. La commission ne change pas avec l’instrument : vérifie-la chez ton courtier.'));
    root.appendChild(s0);

    var s1 = U.section('Frais et *fenêtre*', 'heure locale');
    s1.appendChild(U.fields([
      { label: 'Commission aller-retour', value: set.commissionRT, unit: '$', min: 0, max: 50, hint: 'par contrat, frais CME compris · à vérifier', onChange: function (v) { save({ commissionRT: v }); } },
      { label: 'Fuseau', type: 'select', value: set.tz, options: R.TZS, onChange: function (v) { save({ tz: v }, 'Fuseau enregistré'); } },
      { label: 'Fenêtre : début', value: set.winFrom, unit: 'h', min: 0, max: 23, onChange: function (v) { save({ winFrom: Math.round(v) }); } },
      { label: 'Fenêtre : fin', value: set.winTo, unit: 'h', min: 0, max: 24, onChange: function (v) { save({ winTo: Math.round(v) }); } }
    ]));
    s1.appendChild(U.note('La fenêtre est la plage horaire où ton plan s’applique (par défaut 00 h – 09 h, heure de Paris). Une fenêtre qui passe minuit se règle avec un début plus grand que la fin.'));
    root.appendChild(s1);

    var s2 = U.section('Les *limites*', 'lues par Risque et Routine');
    s2.appendChild(U.fields([
      { label: 'Risque par trade', value: set.riskPerTrade, unit: '$', min: 1, max: 100000, onChange: function (v) { save({ riskPerTrade: v }); } },
      { label: 'Perte maximale du jour', value: set.dailyStop, unit: '$', min: 0, max: 1000000, onChange: function (v) { save({ dailyStop: v }); } },
      { label: 'Trades par jour', value: set.maxTradesDay, min: 1, max: 50, onChange: function (v) { save({ maxTradesDay: Math.round(v) }); } },
      { label: 'Pertes par jour', value: set.maxLossesDay, min: 1, max: 50, onChange: function (v) { save({ maxLossesDay: Math.round(v) }); } }
    ]));
    var ratio = set.riskPerTrade > 0 ? set.dailyStop / set.riskPerTrade : NaN;
    s2.appendChild(U.note(!fin(ratio) ? 'Renseigne le risque par trade.' : 'La perte maximale du jour vaut ' + F.num(ratio, 1) + ' fois le risque par trade. ' + (ratio > set.maxLossesDay ? 'Avec ' + F.int(set.maxLossesDay) + ' pertes autorisées, c’est leur nombre qui arrête la séance avant la perte maximale.' : 'Elle tombe avant que les ' + F.int(set.maxLossesDay) + ' pertes autorisées ne soient atteintes : c’est elle qui arrête la séance.')));
    s2.appendChild(h('div', { class: 'rt-acts' }, U.button({ label: 'Rétablir les valeurs par défaut', kind: 'ghost', small: true, onClick: function () { T.store.set('settings', {}); T.toast('Valeurs par défaut rétablies'); ctx.rerender(); } })));
    root.appendChild(s2);

    var s3 = U.section('La *sauvegarde*', 'appareil et compte');
    var stt = T.saveStatus.get();
    s3.appendChild(U.kpis([
      { label: 'État', value: stt === 'cloud' ? 'compte' : stt === 'saving' ? 'envoi…' : 'appareil', hint: stt === 'cloud' ? 'synchronisé avec ton compte' : 'copie locale seulement' },
      { label: 'Journal', value: F.int(T.journal.list().length), unit: 'lignes', hint: 'trades et refus' }
    ]));
    s3.appendChild(U.note('Chaque changement est écrit sur l’appareil puis, quand la page est ouverte depuis ton compte, dans ta base privée : un autre lecteur du lien ne voit pas tes données. Un export garde une copie que tu possèdes.'));
    var fileIn = h('input', { type: 'file', accept: 'application/json,.json', style: 'display:none', on: { change: function () {
      var f = fileIn.files && fileIn.files[0]; if (!f) return;
      var rd = new FileReader();
      rd.onload = function () {
        var doc; try { doc = JSON.parse(rd.result); } catch (e) { T.toast('Fichier illisible'); return; }
        var v = R.validateImport(doc); if (!v.ok) { T.toast(v.why); return; }
        v.keys.forEach(function (k) { if (k.indexOf('tab:') === 0) return; T.store.set(k, doc.store[k]); });
        var fresh = R.newRows(T.journal.list(), v.rows);
        fresh.forEach(function (t) { var c = Object.assign({}, t); delete c.id; delete c.u; delete c.deleted; T.journal.add(c); });
        T.toast(v.keys.length + ' réglages, ' + fresh.length + ' lignes de journal importés'); ctx.rerender();
      };
      rd.readAsText(f);
    } } });
    s3.appendChild(h('div', { class: 'rt-acts' },
      U.button({ label: 'Exporter mes données', kind: 'pri', small: true, onClick: function () { var d = R.exportDoc(collectStore(), T.journal.list(), new Date().toISOString()); download('alp-desk-' + today() + '.json', JSON.stringify(d, null, 1)); T.toast('Export prêt'); } }),
      U.button({ label: 'Importer un export', kind: 'ghost', small: true, onClick: function () { fileIn.click(); } }), fileIn));
    s3.appendChild(U.note('L’import ajoute sans effacer : une ligne de journal déjà présente n’est pas dupliquée.'));
    root.appendChild(s3);

    var s4 = U.section('*À propos*', 'ALP Desk');
    s4.appendChild(U.table({ cols: [{ k: 'g', label: 'Groupe' }, { k: 'l', label: 'Desk' }, { k: 't', label: 'Onglets', align: 'r' }], rows: T.desks().map(function (d) { return { g: d.group || '', l: d.label, t: (d.tabs || []).length || '—' }; }), onRow: function (r) { var d = T.desks().filter(function (x) { return x.label === r.l; })[0]; if (d) T.nav.go(d.id); } }));
    s4.appendChild(U.prose([
      '<b>Aucun chiffre de marché n’est inventé.</b> Les rapports macro et le calendrier sont transcrits par Claude depuis tes captures ; les niveaux et les prix viennent de toi ; les seuls nombres écrits dans le code sont les spécifications CME et les résultats d’ALP nº 3, avec leur source.',
      '<b>Le desk évolue en passant par Claude.</b> Un desk à ajouter, une règle à changer, un graphique à refaire : on le demande, il est reconstruit et republié sous un nouveau lien.'
    ]));
    root.appendChild(s4);
  }
});
