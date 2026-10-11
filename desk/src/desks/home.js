/* Desk d'accueil : le hub du jour, la carte de séance, le flux des décisions. Sert de référence d'usage du socle. */
var h = T.h, U = T.ui, C = T.chart, F = T.fmt;

function todayRows() {
  var k = T.day.key();
  return T.journal.list().filter(function (r) { var p = T.time.parts('Europe/Paris', new Date(r.at)); return p.y + '-' + String(p.mo).padStart(2, '0') + '-' + String(p.d).padStart(2, '0') === k; });
}

function hub(set) {
  var rows = todayRows(), taken = rows.filter(function (r) { return r.kind === 'pris'; });
  var pnl = taken.reduce(function (a, r) { return a + (isFinite(r.pnl) ? r.pnl : 0); }, 0);
  var losses = taken.filter(function (r) { return r.pnl < 0; }).length;
  var left = Math.max(0, set.dailyStop + Math.min(0, pnl));
  var g = T.time.globex(), win = T.time.inWindow(set.winFrom, set.winTo, set.tz), allDay = set.winFrom === 0 && set.winTo >= 24, all = T.journal.list().length;
  var tiles = [
    { label: 'P&L du jour', value: F.usd(pnl, 0, true), tone: pnl < 0 ? 'neg' : null, hint: taken.length + ' trade' + (taken.length > 1 ? 's' : '') + ' pris', go: 'journal' },
    { label: 'Risque restant', value: F.usd(left, 0), tone: left <= 0 ? 'neg' : null, hint: 'stop du jour ' + F.usd(set.dailyStop, 0), go: 'risk' },
    { label: 'Pertes du jour', value: losses + ' / ' + set.maxLossesDay, tone: losses >= set.maxLossesDay ? 'neg' : null, hint: losses >= set.maxLossesDay ? 'arrêt : journée finie' : 'avant l’arrêt', go: 'risk' },
    allDay ? { label: 'Fenêtre', value: 'toute heure', tone: 'acc', hint: 'heure de Paris ' + T.time.hhmm('Europe/Paris'), go: 'plan' }
      : { label: 'Fenêtre ' + String(set.winFrom).padStart(2, '0') + '–' + String(set.winTo).padStart(2, '0') + ' h', value: win ? 'ouverte' : 'fermée', tone: win ? 'acc' : null, hint: 'heure de Paris ' + T.time.hhmm('Europe/Paris'), go: 'micro' },
    { label: 'Globex', value: g.open ? 'ouvert' : 'fermé', hint: 'New York ' + g.ny + (g.cash ? ' · cash ouvert' : ''), go: 'nq' },
    { label: 'Preuve', value: F.int(all), unit: '/ 619', hint: 'décisions au journal', go: 'quant' }
  ];
  var wrap = h('div', { style: 'position:relative' });
  var center = h('div', { class: 'card accent', style: 'max-width:300px;margin:0 auto;text-align:center' },
    h('div', { class: 'cb', style: 'align-items:center;gap:4px;padding:14px' },
      h('div', { class: 'mono', style: 'font-size:10px;letter-spacing:.16em;color:var(--violet-2)' }, 'DESK · ' + set.instrument),
      h('div', { class: 'mono', style: 'font-size:30px;font-weight:600;color:var(--hi);letter-spacing:-.02em' }, F.usd(pnl, 0, true)),
      h('div', { class: 'mono', style: 'font-size:11px;color:var(--mute)' }, 'P&L net du jour · ' + rows.length + ' décision' + (rows.length > 1 ? 's' : ''))));
  var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('style', 'position:absolute;left:0;top:0;pointer-events:none;overflow:visible');
  var grid = U.kpis(tiles.map(function (t) { return Object.assign({}, t, { onClick: function () { T.nav.go(t.go); } }); }), 3);
  grid.style.marginTop = '34px';
  wrap.appendChild(svg); wrap.appendChild(center); wrap.appendChild(grid);
  T.observe(wrap, function () {
    if (!wrap.isConnected) return; var wr = wrap.getBoundingClientRect(), cr = center.getBoundingClientRect(), out = '';
    svg.setAttribute('width', wr.width); svg.setAttribute('height', wr.height);
    var cx = cr.left + cr.width / 2 - wr.left, cy = cr.bottom - wr.top;
    Array.prototype.forEach.call(grid.children, function (el, i) { var r = el.getBoundingClientRect(); if (r.top - wr.top > cy + 60) return; var x = r.left + r.width / 2 - wr.left, y = r.top - wr.top; out += '<path d="M' + cx + ',' + cy + ' C' + cx + ',' + (cy + 22) + ' ' + x + ',' + (y - 22) + ' ' + x + ',' + y + '" fill="none" stroke="var(--line-2)" stroke-width="1.2"/>'; });
    out += '<circle cx="' + cx + '" cy="' + cy + '" r="3" fill="var(--violet)"/>';
    svg.innerHTML = out;
  });
  return wrap;
}

/* La carte de séance : chaque étape ouvre son étape du desk Plan, avec son pourcentage. */
function flowMap() {
  var d = T.day.get(), firstOpen = T.DAY_STEPS.findIndex(function (s) { return T.day.pct(s.id, d) < 100; });
  return U.flow({ nodes: T.DAY_STEPS.map(function (s, i) {
    var p = T.day.pct(s.id, d);
    return { title: s.t, sub: s.s, pct: p, state: p >= 100 ? 'done' : i === firstOpen ? 'active' : 'todo', go: p + ' % ›', onClick: function () { T.store.set('plan:open', s.id); T.nav.go('plan', 'carte'); } };
  }) });
}

function decisionsSankey() {
  var rows = T.journal.list();
  if (!rows.length) return U.empty({ title: 'Le flux des décisions apparaîtra ici', text: 'Chaque setup vu, filtré ou pris, s’inscrit au journal. Le schéma montre alors où ton plan arrête les trades, et ce que deviennent ceux qui passent.', action: U.button({ label: 'Ouvrir le journal', kind: 'sm', small: true, onClick: function () { T.nav.go('journal'); } }) });
  var stages = [['macro', 'Filtré macro'], ['biais', 'Filtré biais'], ['vwap', 'Filtré VWAP'], ['declencheur', 'Filtré déclencheur'], ['risque', 'Filtré risque']];
  var nodes = [{ id: 'vus', label: 'Setups vus', col: 0 }], links = [];
  stages.forEach(function (s) { var n = rows.filter(function (r) { return r.kind === 'refus' && r.stage === s[0]; }).length; if (n) { nodes.push({ id: s[0], label: s[1], col: 1, tone: 'mute' }); links.push({ s: 'vus', t: s[0], v: n }); } });
  var other = rows.filter(function (r) { return r.kind === 'refus' && !stages.some(function (s) { return s[0] === r.stage; }); }).length;
  if (other) { nodes.push({ id: 'autre', label: 'Refus, autre', col: 1, tone: 'mute' }); links.push({ s: 'vus', t: 'autre', v: other }); }
  var taken = rows.filter(function (r) { return r.kind === 'pris'; });
  if (taken.length) {
    nodes.push({ id: 'pris', label: 'Pris', col: 1, tone: 'violet' }); links.push({ s: 'vus', t: 'pris', v: taken.length, tone: 'violet' });
    var w = taken.filter(function (r) { return r.pnl > 0; }).length, l = taken.filter(function (r) { return r.pnl < 0; }).length, z = taken.length - w - l;
    if (w) { nodes.push({ id: 'g', label: 'Gagnants', col: 2 }); links.push({ s: 'pris', t: 'g', v: w, tone: 'violet' }); }
    if (l) { nodes.push({ id: 'p', label: 'Perdants', col: 2, tone: 'mute' }); links.push({ s: 'pris', t: 'p', v: l }); }
    if (z) { nodes.push({ id: 'z', label: 'Nuls', col: 2, tone: 'mute' }); links.push({ s: 'pris', t: 'z', v: z }); }
  }
  return C.sankey({ nodes: nodes, links: links, height: 240 });
}

T.desk({
  id: 'home', label: 'Desk', glyph: 'D', group: 'Desk', order: 0,
  render: function (root, ctx) {
    var set = ctx.settings, p = T.time.parts('Europe/Paris');
    var jours = ['dimanche', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi'];
    root.appendChild(U.page({ kicker: 'Desk · ' + jours[p.wd] + ' ' + F.dateLong(Date.now()), title: 'Préparer, *puis* trader.', lede: 'Chaque étape du jour a son desk. Le terminal ne promet aucun avantage : il t’aide à décider toujours de la même façon, à tenir ton risque et à tout inscrire.' }));
    var s1 = U.section('Le *hub* du jour', 'touche une tuile pour ouvrir son desk'); s1.appendChild(hub(set)); root.appendChild(s1);
    var s2 = U.section('Carte de séance', 'dans l’ordre, chaque jour'); s2.appendChild(flowMap()); s2.appendChild(h('div', { style: 'display:flex;gap:8px;flex-wrap:wrap;margin-top:12px' }, U.button({ label: 'Ouvrir le plan', small: true, onClick: function () { T.store.set('plan:open', null); T.nav.go('plan', 'carte'); } }), U.button({ label: 'Mode Live ›', small: true, kind: 'acc', onClick: function () { T.store.set('plan:open', null); T.nav.go('plan', 'live'); } }))); root.appendChild(s2);
    var s3 = U.section('Où vont tes *décisions*', 'tout le journal'); s3.appendChild(decisionsSankey()); s3.appendChild(U.note('Sans dérive, un filtre réduit le nombre d’occasions sans améliorer l’espérance (ALP nº 3, partie III). Le schéma sert à voir ton plan travailler, pas à juger une compétence avant 619 décisions.')); root.appendChild(s3);
    var un1 = T.journal.on(function () { ctx.rerender(); }), un2 = T.day.on(function () { ctx.rerender(); });
    var tick = setInterval(function () { if (document.visibilityState === 'visible') ctx.rerender(); }, 60000);
    return function () { un1(); un2(); clearInterval(tick); };
  }
});
