/* Desk « Macro » : les rapports transcrits par Claude, le régime croissance × inflation, le calendrier des publications,
   la routine du matin. Aucun chiffre de marché n’est écrit ici : tout nombre affiché vient d’un document partagé
   (collections `macro` et `calendar`), d’un choix de l’utilisateur, ou d’ALP nº 3 avec sa source.
   Sources, contrôlées par test/macro.test.js :
   – ALP nº 3, onzième partie : « À la géométrie déclarée par l’opérateur — un stop de 0,010 % de l’indice — le seuil
     vaut 8,19 points par heure. Le domaine de dérive que le document nº 1 traite comme plausible s’arrête à 3,2. »
   – Domaine plausible [0,6 ; 3,2] pt/h : alp1/seuil.py, PLAUSIBLE_DRIFT_PER_HOUR = (0.6, 3.2).
   – Horaires de publication américains (BLS, BEA, ISM, Fed, Trésor) : calendriers publics, heure de New York,
     marqués « à vérifier ». */
var h = T.h, U = T.ui, C = T.chart, F = T.fmt;
T.lib = T.lib || {};
var L = T.lib.macro = {};
var K = { regime: 'macro:regime', check: 'macro:check:', impact: 'macro:calimpact', span: 'macro:calspan' };
L.KEYS = K;

/* =====================================================================
   1. Fonctions pures — aucun DOM, aucun T.store
   ===================================================================== */
function fin(v) { return typeof v === 'number' && isFinite(v); }
function isObj(v) { return v != null && typeof v === 'object' && !Array.isArray(v); }
function arr(v) { return Array.isArray(v) ? v : []; }
function pad(n) { return String(n).padStart(2, '0'); }
function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }
L.fin = fin;

/* Texte : chaîne propre, espaces réduits, apostrophe droite entre deux lettres → apostrophe typographique. */
var LET = 'A-Za-zÀ-ÖØ-öø-ÿŒœ';
var APOS = new RegExp('([' + LET + '])\'(?=[' + LET + '])', 'g');
L.txt = function (v) {
  if (v == null) return '';
  if (typeof v === 'number') return isFinite(v) ? String(v) : '';
  if (typeof v !== 'string') return '';
  return v.replace(/\s+/g, ' ').trim().replace(APOS, '$1’');
};
/* Nombre : accepte la virgule et le vrai signe moins ; NaN sinon. */
L.num = function (v) { if (fin(v)) return v; if (typeof v !== 'string') return NaN; return F.parse(v); };

/* Abscisse temporelle : 'AAAA-MM', 'AAAA-MM-JJ', 'AAAA-T1' / 'AAAA-Q1', 'AAAA' → millisecondes UTC ; NaN si invalide. */
var MD = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
function leap(y) { return y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0); }
L.parseX = function (v) {
  if (typeof v === 'number') { if (!isFinite(v)) return NaN; return Number.isInteger(v) && v >= 1000 && v <= 9999 ? Date.UTC(v, 0, 1) : v; }
  if (typeof v !== 'string') return NaN;
  var s = v.trim(), m;
  if ((m = /^(\d{4})-(\d{2})(?:-(\d{2}))?$/.exec(s))) {
    var y = +m[1], mo = +m[2], d = m[3] ? +m[3] : 1;
    if (mo < 1 || mo > 12 || d < 1) return NaN;
    if (d > (mo === 2 && leap(y) ? 29 : MD[mo - 1])) return NaN;
    return Date.UTC(y, mo - 1, d);
  }
  if ((m = /^(\d{4})-?[QT]([1-4])$/i.exec(s))) return Date.UTC(+m[1], (+m[2] - 1) * 3, 1);
  if ((m = /^(\d{4})$/.exec(s))) return Date.UTC(+m[1], 0, 1);
  return NaN;
};
L.precision = function (v) {
  if (typeof v === 'number') return Number.isInteger(v) && v >= 1000 && v <= 9999 ? 'year' : 'day';
  var s = typeof v === 'string' ? v.trim() : '';
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return 'day';
  if (/^\d{4}-\d{2}$/.test(s)) return 'month';
  if (/^\d{4}-?[QT][1-4]$/i.test(s)) return 'quarter';
  if (/^\d{4}$/.test(s)) return 'year';
  return null;
};
var PREC_RANK = { year: 0, quarter: 1, month: 2, day: 3 };
L.isDay = function (s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s.trim()) && isFinite(L.parseX(s)); };

var MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
var MOIS_C = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];
var JOURS = ['dimanche', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi'];
L.dateLong = function (key) {
  var t = L.parseX(key); if (!isFinite(t)) return '';
  var d = new Date(t), j = d.getUTCDate();
  return JOURS[d.getUTCDay()] + ' ' + (j === 1 ? '1er' : j) + ' ' + MOIS[d.getUTCMonth()] + ' ' + d.getUTCFullYear();
};
L.dateShort = function (key) {
  var t = L.parseX(key); if (!isFinite(t)) return '';
  var d = new Date(t); return d.getUTCDate() + ' ' + MOIS_C[d.getUTCMonth()] + ' ' + d.getUTCFullYear();
};
L.dayMonth = function (key) { var t = L.parseX(key); if (!isFinite(t)) return ''; var d = new Date(t); return pad(d.getUTCDate()) + '/' + pad(d.getUTCMonth() + 1); };
/* Format d’axe temporel, selon la précision des données et l’étendue couverte. */
L.timeFmt = function (prec, span) {
  return function (t) {
    var d = new Date(t), y = d.getUTCFullYear(), mo = d.getUTCMonth(), yy = String(y).slice(2);
    if (prec === 'year') return String(y);
    if (prec === 'quarter') return 'T' + (Math.floor(mo / 3) + 1) + ' ' + yy;
    if (prec === 'day') return span <= 400 * 864e5 ? pad(d.getUTCDate()) + '/' + pad(mo + 1) : pad(d.getUTCDate()) + '/' + pad(mo + 1) + '/' + yy;
    return MOIS_C[mo] + ' ' + yy;
  };
};

/* Nombres : autant de décimales que la donnée en porte (trois au plus). */
L.decimals = function (v) {
  if (!fin(v)) return 0; var s = String(Math.abs(v)); if (/e/i.test(s)) return 3;
  var i = s.indexOf('.'); return i < 0 ? 0 : Math.min(3, s.length - i - 1);
};
L.maxDecimals = function (vals) { var m = 0; arr(vals).forEach(function (v) { if (fin(v)) m = Math.max(m, L.decimals(v)); }); return m; };
L.trimFmt = function (maxNd) { return function (v) { if (!fin(v)) return '—'; var r = +v.toFixed(maxNd == null ? 3 : maxNd); return F.num(r, L.decimals(r)); }; };
L.fmtValue = function (v, nd) { if (fin(v)) return F.num(v, nd == null ? L.decimals(v) : nd); var s = L.txt(v); return s || '—'; };
/* Cellule : un nombre reste un nombre, un texte reste un texte, le vide devient null. */
function cell(v) { if (fin(v)) return v; var s = L.txt(v); return s === '' ? null : s; }

/* ---------- Blocs d’un rapport ---------- */
var TONES = ['fg', 'violet', 'mute'];
var DEF_TONE = ['violet', 'fg', 'mute'];
function toneOf(t, i) { return TONES.indexOf(t) >= 0 ? t : (i == null ? null : DEF_TONE[Math.min(i, 2)]); }
L.BLOCKS = ['h', 'p', 'kpis', 'line', 'bar', 'table', 'heat', 'callout', 'source'];

function normKpis(b) {
  var items = arr(b.items).filter(isObj).map(function (it) {
    var label = L.txt(it.label), value = fin(it.value) ? it.value : L.txt(it.value);
    if (!label && value === '') return null;
    var dn = L.num(it.delta), dt = fin(dn) ? '' : L.txt(it.delta);
    return { label: label, value: value === '' ? null : value, unit: L.txt(it.unit), delta: fin(dn) ? dn : null, deltaText: dt, deltaUnit: L.txt(it.deltaUnit), hint: L.txt(it.hint) };
  }).filter(Boolean);
  return items.length ? { t: 'kpis', items: items } : null;
}

function rawPoint(p) {
  if (Array.isArray(p) && p.length >= 2) return [p[0], p[1]];
  if (isObj(p) && 'x' in p && 'y' in p) return [p.x, p.y];
  return null;
}
function normLine(b) {
  var raw = arr(b.series).filter(isObj);
  var xt = b.x === 'cat' || b.x === 'time' || b.x === 'num' ? b.x : null;
  if (!xt) { /* déduire le type d’abscisse du premier point lisible */
    var first = null; raw.some(function (s) { return arr(s.points).some(function (p) { var q = rawPoint(p); if (q) { first = q[0]; return true; } return false; }); });
    xt = typeof first === 'string' ? (L.precision(first) ? 'time' : 'cat') : 'num';
  }
  var prec = null;
  var series = raw.map(function (s, i) {
    var pts = arr(s.points).map(function (p) {
      var q = rawPoint(p); if (!q) return null;
      var x = q[0], y = L.num(q[1]);
      if (xt === 'time') { var pr = L.precision(x); x = L.parseX(x); if (!fin(x)) return null; if (pr && (prec == null || PREC_RANK[pr] > PREC_RANK[prec])) prec = pr; }
      else if (xt === 'cat') { x = L.txt(x); if (!x) return null; }
      else { x = L.num(x); if (!fin(x)) return null; }
      return [x, fin(y) ? y : null];
    }).filter(Boolean);
    if (xt !== 'cat') pts.sort(function (a, c) { return a[0] - c[0]; });
    if (!pts.some(function (p) { return p[1] != null; })) return null;
    return { name: L.txt(s.name), tone: TONES.indexOf(s.tone) >= 0 ? s.tone : null, dash: !!s.dash, points: pts };
  }).filter(Boolean);
  if (!series.length) return null;
  series.forEach(function (s, i) { if (!s.name) s.name = 'Série ' + (i + 1); if (!s.tone) s.tone = DEF_TONE[Math.min(i, 2)]; });
  var hl = arr(b.hlines).filter(isObj).map(function (l) { return { y: L.num(l.y), label: L.txt(l.label), tone: toneOf(l.tone) || 'mute' }; }).filter(function (l) { return fin(l.y); });
  var key = function (s) { return s.points.map(function (p) { return String(p[0]); }).join('|'); };
  var aligned = series.every(function (s) { return key(s) === key(series[0]); });
  return { t: 'line', title: L.txt(b.title), unit: L.txt(b.unit), x: xt, prec: prec || (xt === 'time' ? 'day' : null), aligned: aligned, series: series, hlines: hl, note: L.txt(b.note) };
}

function normBar(b) {
  var cats = arr(b.cats).map(function (c) { return L.txt(c) || '·'; });
  if (!cats.length) return null;
  var series = arr(b.series).filter(isObj).map(function (s, i) {
    var vals = cats.map(function (_, k) { var v = L.num(arr(s.values)[k]); return fin(v) ? v : null; });
    if (!vals.some(fin)) return null;
    return { name: L.txt(s.name), tone: TONES.indexOf(s.tone) >= 0 ? s.tone : null, values: vals };
  }).filter(Boolean);
  if (!series.length) return null;
  series.forEach(function (s, i) { if (!s.name) s.name = series.length > 1 ? 'Série ' + (i + 1) : ''; if (!s.tone) s.tone = DEF_TONE[Math.min(i, 2)]; });
  /* une catégorie vide dans toutes les séries est écartée plutôt que dessinée à zéro */
  var keep = cats.map(function (_, k) { return series.some(function (s) { return s.values[k] != null; }); });
  cats = cats.filter(function (_, k) { return keep[k]; });
  series.forEach(function (s) { s.values = s.values.filter(function (_, k) { return keep[k]; }); });
  return { t: 'bar', title: L.txt(b.title), unit: L.txt(b.unit), cats: cats, series: series, horizontal: !!b.horizontal, stacked: !!b.stacked && series.length > 1, note: L.txt(b.note) };
}

function normTable(b) {
  var rows = arr(b.rows);
  var cols = arr(b.cols).map(function (c, i) {
    if (typeof c === 'string' || fin(c)) { var s = L.txt(c); return s ? { k: s, label: s, align: null } : null; }
    if (!isObj(c)) return null;
    var k = c.k != null ? String(c.k) : String(i);
    return { k: k, label: L.txt(c.label != null ? c.label : c.k) || '', align: c.align === 'r' || c.align === 'right' ? 'r' : (c.align === 'l' || c.align === 'left' ? 'l' : null) };
  }).filter(Boolean);
  if (!cols.length) { var fo = rows.filter(isObj)[0]; if (fo) cols = Object.keys(fo).map(function (k) { return { k: k, label: L.txt(k), align: null }; }); }
  if (!cols.length) return null;
  var out = rows.map(function (r) {
    var o = {}, any = false;
    cols.forEach(function (c, i) { var v = Array.isArray(r) ? r[i] : (isObj(r) ? r[c.k] : undefined); o[c.k] = cell(v); if (o[c.k] != null) any = true; });
    return any ? o : null;
  }).filter(Boolean);
  if (!out.length) return null;
  cols.forEach(function (c) {
    var vals = out.map(function (r) { return r[c.k]; }).filter(function (v) { return v != null; });
    var numeric = vals.length > 0 && vals.every(fin);
    c.numeric = numeric; c.nd = numeric ? L.maxDecimals(vals) : 0;
    if (!c.align) c.align = numeric ? 'r' : 'l';
    c.wrap = !numeric && vals.some(function (v) { return String(v).length > 28; });
  });
  return { t: 'table', title: L.txt(b.title), cols: cols, rows: out, note: L.txt(b.note) };
}

function normHeat(b) {
  var rows = arr(b.rows).map(function (r) { return L.txt(r) || '·'; }), cols = arr(b.cols).map(function (c) { return L.txt(c) || '·'; });
  if (!rows.length || !cols.length) return null;
  var values = rows.map(function (_, i) { var r = arr(arr(b.values)[i]); return cols.map(function (_, j) { var v = L.num(r[j]); return fin(v) ? v : NaN; }); });
  if (!values.some(function (r) { return r.some(fin); })) return null;
  return { t: 'heat', title: L.txt(b.title), unit: L.txt(b.unit), rows: rows, cols: cols, values: values, diverging: !!b.diverging, note: L.txt(b.note) };
}

L.normalizeBlock = function (b) {
  if (!isObj(b)) return null;
  try {
    switch (b.t) {
      case 'h': case 'p': case 'callout': case 'source': { var tx = L.txt(b.text); return tx ? { t: b.t, text: tx } : null; }
      case 'kpis': return normKpis(b);
      case 'line': return normLine(b);
      case 'bar': return normBar(b);
      case 'table': return normTable(b);
      case 'heat': return normHeat(b);
      default: return null;
    }
  } catch (e) { return null; }
};
L.normalizeBlocks = function (blocks) { return arr(blocks).map(L.normalizeBlock).filter(Boolean); };

/* Un document de la collection `macro` → rapport propre, ou null. */
L.normalizeReport = function (doc) {
  if (!isObj(doc) || doc.kind !== 'report') return null;
  var date = L.isDay(doc.date) ? doc.date.trim() : '', title = L.txt(doc.title), lede = L.txt(doc.lede);
  var blocks = L.normalizeBlocks(doc.blocks);
  if (!title && !lede && !blocks.length) return null;
  var tags = []; arr(doc.tags).forEach(function (t) { var s = L.txt(t); if (s && tags.indexOf(s) < 0) tags.push(s); });
  var id = L.txt(doc._id) || L.txt(doc.id) || (date + '·' + title);
  return { id: id, kind: 'report', date: date, ts: date ? L.parseX(date) : NaN, title: title || 'Rapport sans titre', source: L.txt(doc.source), lede: lede, tags: tags, blocks: blocks };
};
/* Rapports triés du plus récent au plus ancien ; un rapport sans date passe en dernier. */
L.sortReports = function (docs) {
  return arr(docs).map(L.normalizeReport).filter(Boolean).sort(function (a, b) {
    var ta = fin(a.ts) ? a.ts : -Infinity, tb = fin(b.ts) ? b.ts : -Infinity;
    if (ta !== tb) return tb > ta ? 1 : -1;
    return a.title.localeCompare(b.title, 'fr');
  });
};
L.summary = function (rep) {
  var n = { kpis: 0, chart: 0, table: 0 };
  arr(rep && rep.blocks).forEach(function (b) { if (b.t === 'kpis') n.kpis += b.items.length; else if (b.t === 'line' || b.t === 'bar' || b.t === 'heat') n.chart++; else if (b.t === 'table') n.table++; });
  var out = [];
  if (n.kpis) out.push(n.kpis + ' indicateur' + (n.kpis > 1 ? 's' : ''));
  if (n.chart) out.push(n.chart + ' graphique' + (n.chart > 1 ? 's' : ''));
  if (n.table) out.push(n.table + ' tableau' + (n.table > 1 ? 'x' : ''));
  return out.join(' · ');
};

/* ---------- Régime croissance × inflation ---------- */
L.POS = 0.55; /* position d’un « accélère » sur le quadrant, dans [−1, 1] */
L.SENS = [{ v: 1, label: 'Accélère' }, { v: 0, label: 'Stable' }, { v: -1, label: 'Ralentit' }];
L.REGIMES = [
  { id: 'reflation', label: 'Reflation', g: 1, i: 1, axes: 'croissance ↑ · inflation ↑',
    essence: 'L’activité repart et les prix avec elle.',
    nq: ['Les bénéfices progressent, mais les taux longs montent avec l’inflation attendue, ce qui pèse sur la valorisation des valeurs de croissance.', 'D’ordinaire, le Nasdaq avance moins régulièrement que les indices plus cycliques, et les chiffres d’inflation deviennent des séances de forte amplitude.'],
    plan: ['Autour des chiffres d’inflation et de banque centrale : pas de position ouverte à l’instant de la publication.', 'Un biais de tendance reste possible, mais une hausse rapide du taux 10 ans contredit un biais acheteur : la lire comme un filtre.'] },
  { id: 'goldilocks', label: 'Goldilocks', g: 1, i: -1, axes: 'croissance ↑ · inflation ↓',
    essence: 'La croissance tient, l’inflation reflue.',
    nq: ['Le contexte le plus porteur d’ordinaire pour les valeurs de croissance : bénéfices en hausse, taux stables ou en baisse, volatilité implicite basse.', 'Les replis y sont souvent rachetés, ce qui ne dit rien de la séance suivante.'],
    plan: ['Volatilité plus basse, amplitudes plus courtes : moins de setups atteignent leur objectif dans la séance.', 'Le danger est la complaisance — la taille grossit parce que tout paraît facile. La taille reste celle du plan.'] },
  { id: 'stagflation', label: 'Stagflation', g: -1, i: 1, axes: 'croissance ↓ · inflation ↑',
    essence: 'L’activité fléchit pendant que les prix montent.',
    nq: ['Le contexte le plus hostile d’ordinaire : les bénéfices sont révisés en baisse pendant que les taux restent hauts ou montent.', 'Rebonds courts et ventes brutales ; actions et obligations peuvent baisser ensemble, ce qui retire l’amortisseur habituel.'],
    plan: ['Amplitudes larges et faux départs fréquents : réduire la taille plutôt qu’élargir le risque.', 'Privilégier les setups à invalidation proche, accepter davantage de refus, ne pas vendre en retard un rebond déjà parti.'] },
  { id: 'desinflation', label: 'Désinflation', g: -1, i: -1, axes: 'croissance ↓ · inflation ↓',
    essence: 'Tout ralentit ; on parle de déflation si les prix baissent.',
    nq: ['La baisse des taux soutient la valorisation, mais les bénéfices sont révisés en baisse.', 'D’ordinaire, le marché alterne entre l’espoir d’un assouplissement monétaire et la crainte d’une récession ; les chiffres d’emploi décident.'],
    plan: ['Séances dominées par l’activité et l’emploi, écarts fréquents à l’ouverture : laisser la première demi-heure poser les niveaux.', 'Lire la réaction aux mauvaises nouvelles : si une mauvaise nouvelle fait monter l’indice, le marché joue déjà la baisse des taux.'] }
];
L.regimeById = function (id) { return L.REGIMES.filter(function (r) { return r.id === id; })[0] || null; };
/* Valeur d’axe : nombre dans [−1, 1] (borné), ou un mot ; NaN si illisible. */
L.axisPos = function (v) {
  if (fin(v)) return clamp(v, -1, 1);
  var s = L.txt(v).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  if (!s) return NaN;
  if (/^(accelere|acceleration|hausse|monte|up|\+)/.test(s)) return L.POS;
  if (/^(stable|neutre|flat|=|0$)/.test(s)) return 0;
  if (/^(ralentit|ralentissement|baisse|recule|down|-|−)/.test(s)) return -L.POS;
  var n = L.num(v); return fin(n) ? clamp(n, -1, 1) : NaN;
};
L.sign = function (x, dead) { dead = dead == null ? 0.1 : dead; return !fin(x) ? 0 : x > dead ? 1 : x < -dead ? -1 : 0; };
/* Le régime d’un point (croissance g, inflation i) ; sur un axe, le point est entre deux régimes. */
L.regimeOf = function (g, i) {
  var sg = L.sign(g), si = L.sign(i);
  var find = function (a, b) { return L.REGIMES.filter(function (r) { return r.g === a && r.i === b; })[0]; };
  if (sg && si) { var r = find(sg, si); return { id: r.id, label: r.label, between: [r.id] }; }
  if (!sg && !si) return { id: 'centre', label: 'Au centre', between: L.REGIMES.map(function (r) { return r.id; }) };
  var pair = !sg ? [find(-1, si), find(1, si)] : [find(sg, 1), find(sg, -1)];
  return { id: 'entre', label: 'Entre ' + pair[0].label.toLowerCase() + ' et ' + pair[1].label.toLowerCase(), between: [pair[0].id, pair[1].id] };
};
/* Le plus récent document partagé de type « regime », propre, ou null. */
L.latestRegime = function (docs) {
  var list = arr(docs).filter(function (d) { return isObj(d) && d.kind === 'regime'; }).map(function (d) {
    var g = L.axisPos(d.growth), i = L.axisPos(d.inflation);
    if (!fin(g) || !fin(i)) return null;
    return { date: L.isDay(d.date) ? d.date.trim() : '', growth: g, inflation: i, label: L.txt(d.label), note: L.txt(d.note), source: L.txt(d.source) };
  }).filter(Boolean);
  list.sort(function (a, b) { return (b.date > a.date ? 1 : b.date < a.date ? -1 : 0); });
  return list[0] || null;
};

/* ---------- Calendrier ---------- */
L.normalizeEvent = function (d) {
  if (!isObj(d)) return null;
  var date = L.isDay(d.date) ? d.date.trim() : '', ev = L.txt(d.event);
  if (!date || !ev) return null;
  var tm = /^([01]?\d|2[0-3])\s*[:h]\s*([0-5]\d)$/.exec(L.txt(d.time));
  var imp = Math.round(L.num(d.impact));
  return {
    id: L.txt(d._id) || L.txt(d.id) || (date + ' ' + (tm ? tm[0] : '') + ' ' + ev),
    date: date, time: tm ? pad(+tm[1]) + ':' + tm[2] : '', min: tm ? (+tm[1]) * 60 + (+tm[2]) : null,
    event: ev, country: L.txt(d.country), impact: fin(imp) ? clamp(imp, 1, 3) : 1,
    prev: cell(d.prev), cons: cell(d.cons), actual: cell(d.actual), note: L.txt(d.note)
  };
};
function evOrder(a, b) {
  if (a.date !== b.date) return a.date < b.date ? -1 : 1;
  var ma = a.min == null ? -1 : a.min, mb = b.min == null ? -1 : b.min;
  if (ma !== mb) return ma - mb;
  return b.impact - a.impact;
}
L.events = function (docs) { return arr(docs).map(L.normalizeEvent).filter(Boolean).sort(evOrder); };
/* Groupes par jour : opts.minImpact (1 à 3), opts.upcoming (seulement aujourd’hui et après). */
L.groupByDay = function (docs, today, opts) {
  opts = opts || {}; var min = opts.minImpact || 1, out = [], by = {};
  L.events(docs).forEach(function (e) {
    if (e.impact < min) return;
    if (opts.upcoming && e.date < today) return;
    if (!by[e.date]) { by[e.date] = { date: e.date, isToday: e.date === today, isPast: e.date < today, items: [] }; out.push(by[e.date]); }
    by[e.date].items.push(e);
  });
  return out;
};
/* Prochain événement d’impact ≥ minImpact, à partir de maintenant (heure de Paris). */
L.nextEvent = function (docs, today, nowMin, minImpact) {
  var min = minImpact || 1;
  return L.events(docs).filter(function (e) { return e.impact >= min && (e.date > today || (e.date === today && e.min != null && e.min >= nowMin)); })[0] || null;
};
L.minutesUntil = function (e, today, nowMin) {
  if (!e || e.min == null) return NaN;
  var days = Math.round((L.parseX(e.date) - L.parseX(today)) / 864e5);
  return days * 1440 + e.min - nowMin;
};
/* Dans la fenêtre de trading [from, to[ en heures de Paris (passe minuit si from > to), comme T.time.inWindow. */
L.inWindow = function (min, from, to) {
  if (min == null || !fin(min)) return false; var x = min / 60;
  return from <= to ? (x >= from && x < to) : (x >= from || x < to);
};
L.hhFr = function (hhmm) { var m = /^(\d{1,2}):(\d{2})$/.exec(String(hhmm || '')); return m ? (+m[1]) + ' h ' + m[2] : ''; };
/* Décalage d’un fuseau en minutes à l’instant t (ms). */
L.tzOffset = function (tz, t) {
  var p = T.time.parts(tz, new Date(t));
  return Math.round((Date.UTC(p.y, p.mo - 1, p.d, p.h, p.m, p.s) - Math.floor(t / 1000) * 1000) / 60000);
};
/* Heure de New York 'HH:MM' le jour 'AAAA-MM-JJ' → heure de Paris 'HH:MM'. Les deux passages à l’heure d’été
   n’ont pas lieu le même dimanche : l’écart vaut 6 h la plupart de l’année, 5 h quelques semaines. */
L.nyToParis = function (hhmm, day) {
  var m = /^(\d{1,2}):(\d{2})$/.exec(String(hhmm || '')), base = L.parseX(day);
  if (!m || !isFinite(base)) return '';
  var local = base + ((+m[1]) * 60 + (+m[2])) * 60000, t = local;
  for (var k = 0; k < 3; k++) t = local - L.tzOffset('America/New_York', t) * 60000;
  var p = T.time.parts('Europe/Paris', new Date(t));
  return pad(p.h) + ':' + pad(p.m);
};

/* ---------- Routine du matin et chemin vers le trade ---------- */
L.ROUTINE = [
  { id: 'calendrier', t: 'Calendrier du jour', s: 'Les publications d’impact fort et leur heure de Paris ; celles qui tombent dans ta fenêtre.' },
  { id: 'nuit', t: 'Séance de nuit', s: 'Où le NQ a traité en Asie et en Europe par rapport à la clôture de la veille : haut, bas, écart.' },
  { id: 'taux2', t: 'Taux 2 ans', s: 'Le sens depuis la veille : ce que le marché attend de la Fed.' },
  { id: 'taux10', t: 'Taux 10 ans et pente', s: 'Le prix du temps ; une hausse rapide pèse d’abord sur les valeurs de croissance.' },
  { id: 'dollar', t: 'Dollar', s: 'Un dollar qui monte vite resserre les conditions financières.' },
  { id: 'vol', t: 'Volatilité', s: 'VIX et VXN, niveau et variation : la largeur raisonnable d’un stop en dépend.' },
  { id: 'stress', t: 'Crédit et pétrole', s: 'Un écart de crédit qui s’ouvre, un choc d’énergie : les deux signaux de stress à ne pas manquer.' },
  { id: 'resultats', t: 'Résultats', s: 'Une grosse pondération du Nasdaq-100 publie-t-elle avant l’ouverture ou après la clôture ?' },
  { id: 'regime', t: 'Régime', s: 'Confirmer ou changer le quadrant, en une phrase.' },
  { id: 'biais', t: 'Biais écrit', s: 'Ce qui me ferait acheter, ce qui me ferait vendre, ce qui me ferait rester dehors.' }
];
L.progress = function (checked) { var n = L.ROUTINE.filter(function (it) { return checked && checked[it.id]; }).length; return { n: n, total: L.ROUTINE.length, all: n === L.ROUTINE.length }; };
L.FLOW = [
  { id: 'macro', t: 'Macro', s: 'Rapports, calendrier : ce qui peut bouger le marché aujourd’hui', step: 'macro', desk: 'macro', tab: 'rapports' },
  { id: 'regime', t: 'Régime', s: 'Le quadrant du jour, en une phrase', desk: 'macro', tab: 'regime' },
  { id: 'biais', t: 'Biais du jour', s: 'Acheteur, vendeur ou dehors, écrit avant l’ouverture', step: 'biais', desk: 'nq' },
  { id: 'niveaux', t: 'Niveaux', s: 'Les prix où le plan agit, et nulle part ailleurs', step: 'biais', desk: 'nq' },
  { id: 'fenetre', t: 'Fenêtre', s: 'L’heure, et le bon côté de la VWAP', step: 'fenetre', desk: 'micro' },
  { id: 'declencheur', t: 'Déclencheur', s: 'Un seul signal, écrit d’avance', step: 'declencheur', desk: 'micro' },
  { id: 'risque', t: 'Risque', s: 'Le stop décide de la taille', step: 'risque', desk: 'risk' }
];
/* États des nœuds : fait, actif (le premier non fait), à faire. */
L.flowStates = function (done, regimeToday) {
  done = done || {}; var first = -1;
  var isDone = L.FLOW.map(function (n) { return n.id === 'regime' ? !!regimeToday : !!done[n.step]; });
  isDone.forEach(function (d, i) { if (!d && first < 0) first = i; });
  return isDone.map(function (d, i) { return d ? 'done' : i === first ? 'active' : 'todo'; });
};

/* Ce que suit un desk macro de grand fonds : aucun chiffre, seulement l’objet et son canal vers le Nasdaq. */
L.SUIVI = [
  { fam: 'Activité', items: [
    { id: 'croissance', t: 'Croissance', s: 'PIB, enquêtes ISM, ventes au détail', nq: 'Le moteur des bénéfices attendus. Une croissance qui surprend à la hausse soutient les résultats, mais peut aussi faire monter les taux.' },
    { id: 'inflation', t: 'Inflation', s: 'CPI, PCE, salaires', nq: 'Elle décide de la trajectoire des taux. Une inflation qui surprend à la hausse est d’ordinaire la pire nouvelle pour les valeurs de croissance.' }] },
  { fam: 'Politique monétaire', items: [
    { id: 'banques', t: 'Banques centrales', s: 'Fed d’abord, puis BCE et Banque du Japon', nq: 'Le coût de l’argent et la quantité de liquidité. Le ton d’une conférence de presse compte souvent plus que la décision elle-même.' },
    { id: 'taux2', t: 'Taux 2 ans', s: 'Ce que le marché attend de la Fed', nq: 'Il réagit le premier aux chiffres d’inflation et d’emploi : c’est le thermomètre de la politique monétaire attendue.' },
    { id: 'taux10', t: 'Taux 10 ans', s: 'Le prix du temps', nq: 'Il actualise les bénéfices lointains. Les valeurs de croissance, dont la valeur est loin dans le futur, y sont les plus sensibles.' },
    { id: 'pente', t: 'Pente 2 – 10 ans', s: 'L’écart entre court et long', nq: 'Une courbe inversée a souvent précédé les récessions ; sa repentification dit pourquoi elle se redresse : baisse des taux courts ou hausse des longs.' }] },
  { fam: 'Conditions financières', items: [
    { id: 'dollar', t: 'Dollar', s: 'L’indice dollar contre les grandes devises', nq: 'Un dollar fort resserre les conditions financières mondiales et réduit la valeur des revenus étrangers des grandes multinationales du Nasdaq-100.' },
    { id: 'credit', t: 'Crédit', s: 'L’écart de taux des obligations d’entreprise', nq: 'Quand il s’écarte, le marché réévalue le risque de défaut ; les actions suivent souvent avec retard.' },
    { id: 'liquidite', t: 'Liquidité', s: 'Bilan de la Fed, compte du Trésor, pensions', nq: 'La quantité d’argent disponible pour les actifs risqués. Elle agit lentement et se lit en tendance.' },
    { id: 'petrole', t: 'Pétrole', s: 'Le baril et l’énergie', nq: 'Un choc d’énergie nourrit l’inflation attendue et freine la consommation : il touche les deux axes du régime à la fois.' }] },
  { fam: 'Risque et positionnement', items: [
    { id: 'vol', t: 'Volatilité', s: 'VIX, VXN, structure par terme', nq: 'Le prix de la protection. Elle fixe l’amplitude probable d’une séance, donc la largeur raisonnable d’un stop.' },
    { id: 'positions', t: 'Positionnement', s: 'Rapports COT, exposition des fonds, gamma', nq: 'Qui est déjà dans le trade. Un marché très chargé d’un côté réagit fort à la nouvelle qui le contredit.' }] }
];
/* Familles d’événements qui bougent le NQ, avec leur heure habituelle à New York (calendriers publics, à vérifier). */
L.FAMILLES = [
  { id: 'inflation', t: 'Inflation', s: 'CPI, PCE, PPI', ny: '08:30' },
  { id: 'emploi', t: 'Emploi', s: 'Rapport mensuel sur l’emploi, inscriptions hebdomadaires au chômage ; enquête JOLTS à 10 h 00', ny: '08:30' },
  { id: 'fed', t: 'Banque centrale', s: 'Décision du FOMC, puis conférence de presse à 14 h 30 ; minutes, discours du président de la Fed', ny: '14:00' },
  { id: 'activite', t: 'Activité', s: 'PIB, ventes au détail ; enquêtes ISM à 10 h 00', ny: '08:30' },
  { id: 'resultats', t: 'Résultats', s: 'Les plus grosses pondérations du Nasdaq-100 (Apple, Microsoft, Nvidia, Amazon, Alphabet, Meta, Broadcom, Tesla — la liste change)', ny: null, when: 'avant l’ouverture ou après la clôture de 16 h 00' },
  { id: 'tresor', t: 'Taux', s: 'Adjudications du Trésor à 10 et 30 ans', ny: '13:00' }
];

/* ALP nº 3, onzième partie, et alp1/seuil.py. */
L.ALP = { seuilDeclare: 8.19, stopDeclarePct: 0.010, plausible: [0.6, 3.2] };

/* =====================================================================
   2. Rendu
   ===================================================================== */
var CSS = [
  '.ma-list{display:flex;flex-direction:column;gap:10px}',
  '.ma-rep{display:flex;flex-direction:column;gap:7px;text-align:left;width:100%;border:1px solid var(--line);border-radius:var(--r);background:var(--panel);padding:13px 14px;min-width:0}',
  '.ma-rep:hover{border-color:var(--line-2)}',
  '.ma-rep.first{border-color:var(--violet-b);background:linear-gradient(180deg,var(--violet-a),transparent 70%),var(--panel)}',
  '.ma-rep .d{font:600 10px/1.35 var(--f-mono);letter-spacing:.1em;text-transform:uppercase;color:var(--mute)}',
  '.ma-rep.first .d{color:var(--violet-2)}',
  '.ma-rep b{font-size:16px;line-height:1.25;font-weight:600;color:var(--hi);letter-spacing:-.01em}',
  '.ma-rep p{margin:0;font-size:13px;color:var(--soft);line-height:1.5;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}',
  '.ma-rep .ft{display:flex;align-items:center;justify-content:space-between;gap:8px;font:500 10.5px/1.3 var(--f-mono);color:var(--mute)}',
  '.ma-tags{display:flex;flex-wrap:wrap;gap:5px}',
  '.ma-doc{display:flex;flex-direction:column;gap:16px;min-width:0}',
  '.ma-back{align-self:flex-start}',
  '.ma-dh{display:flex;flex-direction:column;gap:9px;padding-bottom:16px;border-bottom:1px solid var(--line)}',
  '.ma-dh .d{font:600 10.5px/1.35 var(--f-mono);letter-spacing:.1em;text-transform:uppercase;color:var(--violet-2)}',
  '.ma-dh h2{margin:0;font-size:25px;line-height:1.12;font-weight:600;letter-spacing:-.02em;color:var(--hi);text-wrap:balance}',
  '.ma-dh .ld{margin:0;font-family:var(--f-serif);font-style:italic;font-size:18px;line-height:1.4;color:var(--fg);max-width:60ch}',
  '.ma-blocks{display:flex;flex-direction:column;gap:14px;min-width:0}',
  '.ma-h{margin:8px 0 0;display:flex;align-items:baseline;gap:10px;font-size:16px;font-weight:600;letter-spacing:-.01em;color:var(--hi)}',
  '.ma-h i{font:600 11px/1 var(--f-mono);font-style:normal;color:var(--violet-2);flex:none}',
  '.ma-p{margin:0;font-size:14px;color:var(--soft);line-height:1.62;max-width:66ch}',
  '.ma-tt{font-size:13.5px;font-weight:600;color:var(--fg)}',
  '.ma-blk{display:flex;flex-direction:column;gap:8px;min-width:0}',
  '.ma-src{margin:0;font:500 11px/1.5 var(--f-mono);color:var(--mute);border-top:1px solid var(--line);padding-top:10px}',
  '.ma-mini{display:flex;flex-direction:column;gap:2px}',
  '.ma-mini .nm{font:500 11px/1.3 var(--f-mono);color:var(--soft)}',
  '.ma-map{position:relative;display:grid;grid-template-columns:minmax(0,1fr) 96px;column-gap:30px;align-items:center}',
  '.ma-map svg.mw{position:absolute;left:0;top:0;pointer-events:none;overflow:visible}',
  '.ma-col{position:relative;z-index:1;display:flex;flex-direction:column;gap:6px;min-width:0}',
  '.ma-fam{font:600 9.5px/1 var(--f-mono);letter-spacing:.14em;text-transform:uppercase;color:var(--mute);margin:10px 0 1px}',
  '.ma-fam:first-child{margin-top:0}',
  '.ma-nd{display:flex;flex-direction:column;gap:2px;text-align:left;border:1px solid var(--line);border-radius:9px;background:var(--panel);padding:7px 10px;min-width:0}',
  '.ma-nd b{font-size:13px;font-weight:600;color:var(--fg)}',
  '.ma-nd span{font-size:11.5px;color:var(--mute);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
  '.ma-nd[aria-pressed="true"]{border-color:var(--violet);box-shadow:0 0 0 1px var(--violet)}',
  '.ma-nd[aria-pressed="true"] b{color:var(--hi)}',
  '.ma-hub{position:relative;z-index:1;border:1px solid var(--violet-b);border-radius:12px;background:linear-gradient(180deg,var(--violet-a),transparent 80%),var(--panel);padding:14px 6px;text-align:center;display:flex;flex-direction:column;gap:4px;align-items:center}',
  '.ma-hub b{font:600 22px/1 var(--f-mono);color:var(--hi);letter-spacing:-.02em}',
  '.ma-hub span{font:500 9.5px/1.3 var(--f-mono);color:var(--mute);letter-spacing:.04em}',
  '.mw path{fill:none;stroke:var(--line-2);stroke-width:1.1}',
  '.mw path.on{stroke:var(--violet);stroke-width:1.7}',
  '.mw circle{fill:var(--bg);stroke:var(--line-2);stroke-width:1.2}',
  '.mw circle.on{fill:var(--violet);stroke:var(--violet)}',
  '.ma-det{display:flex;flex-direction:column;gap:4px}',
  '.ma-det .k{font:600 10px/1.2 var(--f-mono);letter-spacing:.1em;text-transform:uppercase;color:var(--violet-2)}',
  '.ma-det b{font-size:15px;color:var(--hi);font-weight:600}',
  '.ma-det p{margin:0;font-size:13.5px;color:var(--soft);line-height:1.55}',
  '.ma-axes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}',
  '@media (max-width:520px){.ma-axes{grid-template-columns:minmax(0,1fr)}}',
  '.ma-res{display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap}',
  '.ma-res b{font-size:18px;font-weight:600;color:var(--hi);letter-spacing:-.01em}',
  '.ma-res span{font:500 10.5px/1.3 var(--f-mono);color:var(--mute)}',
  '.ma-leg{display:flex;flex-wrap:wrap;gap:6px 14px;font:500 11px/1.3 var(--f-mono);color:var(--soft)}',
  '.ma-leg span{display:inline-flex;align-items:center;gap:6px}',
  '.ma-leg i{width:9px;height:9px;border-radius:50%;display:inline-block}',
  '.ma-rg{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}',
  '@media (max-width:520px){.ma-rg{grid-template-columns:minmax(0,1fr)}}',
  '.ma-rc{text-align:left;border:1px solid var(--line);border-radius:var(--r);background:var(--panel);padding:12px 13px;display:flex;flex-direction:column;gap:5px;min-width:0}',
  '.ma-rc[aria-pressed="true"]{border-color:var(--violet);box-shadow:0 0 0 1px var(--violet)}',
  '.ma-rc .ax{font:600 10px/1.2 var(--f-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--mute)}',
  '.ma-rc b{font-size:15px;color:var(--hi);font-weight:600}',
  '.ma-rc p{margin:0;font-size:12.5px;color:var(--soft);line-height:1.45}',
  '.ma-two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}',
  '@media (max-width:560px){.ma-two{grid-template-columns:minmax(0,1fr)}}',
  '.ma-two h4{margin:0 0 7px;font:600 10px/1.2 var(--f-mono);letter-spacing:.1em;text-transform:uppercase;color:var(--violet-2)}',
  '.ma-two ul{margin:0;padding-left:16px;display:flex;flex-direction:column;gap:7px;font-size:13px;color:var(--soft);line-height:1.5}',
  '.ma-day{display:flex;flex-direction:column;gap:8px}',
  '.ma-dayh{display:flex;align-items:baseline;justify-content:space-between;gap:8px}',
  '.ma-dayh b{font-size:14px;font-weight:600;color:var(--fg)}',
  '.ma-dayh.today b{color:var(--hi)}',
  '.ma-dayh span{font:500 10.5px/1.3 var(--f-mono);color:var(--mute);white-space:nowrap}',
  '.ma-dayh.today span{color:var(--violet-2)}',
  '.ma-evs{border:1px solid var(--line);border-radius:var(--r);background:var(--panel);overflow:hidden}',
  '.ma-evs.today{border-color:var(--violet-b);box-shadow:0 0 0 1px var(--violet-a)}',
  '.ma-ev{display:grid;grid-template-columns:44px 30px minmax(0,1fr);gap:10px;padding:10px 12px;border-top:1px solid var(--line);align-items:start}',
  '.ma-ev:first-child{border-top:0}',
  '.ma-ev.past{opacity:.6}',
  '.ma-ev .tm{font:600 12.5px/1.35 var(--f-mono);color:var(--hi)}',
  '.ma-ev .tm.no{color:var(--mute);font-weight:500;font-size:11px}',
  '.ma-imp{display:flex;gap:3px;padding-top:5px}',
  '.ma-imp i{width:7px;height:7px;border-radius:50%;border:1px solid var(--line-2)}',
  '.ma-imp i.on{background:var(--soft);border-color:var(--soft)}',
  '.ma-imp.i3 i.on{background:var(--violet);border-color:var(--violet)}',
  '.ma-ev .tx{min-width:0}',
  '.ma-ev .tx b{display:block;font-size:13.5px;font-weight:600;color:var(--fg);line-height:1.35}',
  '.ma-ev .mt{display:flex;flex-wrap:wrap;align-items:center;gap:4px 10px;margin-top:5px;font:500 11px/1.4 var(--f-mono);color:var(--mute)}',
  '.ma-ev .mt em{font-style:normal;color:var(--fg)}',
  '.ma-ev .mt .pill{height:19px;padding:0 6px;font-size:9.5px}',
  '.ma-ev .nt{font-size:12px;color:var(--soft);margin-top:5px;line-height:1.45}',
  '.ma-ctl{display:flex;flex-direction:column;gap:8px}',
  '.ma-fl{display:flex;flex-direction:column;gap:0;border:1px solid var(--line);border-radius:var(--r);background:var(--panel);overflow:hidden}',
  '.ma-fr{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 12px;padding:11px 13px;border-top:1px solid var(--line);align-items:start}',
  '.ma-fr:first-child{border-top:0}',
  '.ma-fr b{font-size:13.5px;font-weight:600;color:var(--fg)}',
  '.ma-fr p{margin:2px 0 0;font-size:12.5px;color:var(--mute);line-height:1.45}',
  '.ma-fr .hr{font:600 11.5px/1.35 var(--f-mono);color:var(--hi);text-align:right;white-space:nowrap}',
  '.ma-fr .hr small{display:block;font-weight:500;font-size:10px;color:var(--mute)}',
  '.ma-fr .pill{margin-top:6px}'
].join('\n');
function injectCss() { if (document.getElementById('macro-css')) return; var s = document.createElement('style'); s.id = 'macro-css'; s.textContent = CSS; document.head.appendChild(s); }
function typo(el) {
  if (!el || typeof document === 'undefined') return;
  var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, { acceptNode: function (n) { var p = n.parentNode; return p && /^(TEXTAREA|SCRIPT|STYLE|INPUT|OPTION)$/.test(p.nodeName) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; } }), n;
  while ((n = w.nextNode())) { var t = n.nodeValue, u = T.typo(t).replace(/nº /g, 'nº '); if (u !== t) n.nodeValue = u; }
}
var UI = { sel: null, tag: null, node: 'inflation' };
function deskExists(id) { return T.desks().some(function (d) { return d.id === id; }); }
function goDesk(id, tab, label) { if (deskExists(id)) T.nav.go(id, tab); else T.toast('Le desk « ' + (label || id) + ' » n’est pas installé dans cette version'); }
function plural(n, s, p) { return n + ' ' + (n > 1 ? (p || s + 's') : s); }

/* ---------- Rendu des blocs ---------- */
function yFmtFor(vals) { return L.trimFmt(Math.max(0, Math.min(3, L.maxDecimals(vals)))); }
function marginFor(vals, fmt) { var w = 0; vals.forEach(function (v) { w = Math.max(w, fmt(v).length); }); return clamp(Math.round(14 + 6.3 * w), 34, 84); }
function lineChart(b) {
  var ys = []; b.series.forEach(function (s) { s.points.forEach(function (p) { if (p[1] != null) ys.push(p[1]); }); });
  b.hlines.forEach(function (l) { ys.push(l.y); });
  var fy = yFmtFor(ys), lo = Math.min.apply(null, ys), hi = Math.max.apply(null, ys), ml = marginFor([lo, hi, (lo + hi) / 2], fy);
  function xOpt(series) {
    if (b.x === 'time') { var xs = []; series.forEach(function (s) { s.points.forEach(function (p) { xs.push(p[0]); }); }); var span = Math.max.apply(null, xs) - Math.min.apply(null, xs); return { type: 'time', fmt: L.timeFmt(b.prec, span) }; }
    if (b.x === 'cat') return { type: 'cat', labels: series[0].points.map(function (p) { return p[0]; }) };
    return { type: 'num' };
  }
  function asNum(s) { return b.x === 'cat' ? Object.assign({}, s, { points: s.points.map(function (p, i) { return [i, p[1]]; }) }) : s; }
  if (b.aligned || b.series.length === 1) {
    return C.line({ series: b.series.map(asNum), x: xOpt(b.series), y: { fmt: fy }, hlines: b.hlines, height: 210, ml: ml });
  }
  /* séries non alignées : petits multiples sur une même échelle verticale, pour que l’info-bulle ne mélange jamais deux dates */
  var pd = (hi - lo) * 0.06 || 1, wrap = h('div', { class: 'ma-blk' });
  b.series.forEach(function (s) {
    wrap.appendChild(h('div', { class: 'ma-mini' }, h('span', { class: 'nm' }, s.name),
      C.line({ series: [asNum(s)], x: xOpt([s]), y: { fmt: fy, min: lo - pd, max: hi + pd }, hlines: b.hlines, height: 150, ml: ml })));
  });
  wrap.appendChild(U.note('Les séries ne partagent pas les mêmes dates : une par cadre, sur la même échelle.'));
  return wrap;
}
function barChart(b) {
  var vals = []; b.series.forEach(function (s) { s.values.forEach(function (v) { if (v != null) vals.push(v); }); });
  var f = yFmtFor(vals), unit = b.unit && b.unit.length <= 4 ? b.unit : '';
  if (b.horizontal) {
    var maxLen = 0; b.cats.forEach(function (c) { maxLen = Math.max(maxLen, c.length); });
    var cut = 22, cats = b.cats.map(function (c) { return c.length > cut ? c.slice(0, cut - 1) + '…' : c; });
    var ml = clamp(Math.round(16 + 6.2 * Math.min(cut, maxLen)), 56, 156);
    return C.bar({ cats: cats, series: b.series, horizontal: true, stacked: b.stacked, ml: ml, fmt: function (v) { return f(v) + (unit ? ' ' + unit : ''); } });
  }
  var lo = Math.min(0, Math.min.apply(null, vals)), hi = Math.max(0, Math.max.apply(null, vals));
  return C.bar({ cats: b.cats, series: b.series, stacked: b.stacked, fmt: f, ml: marginFor([lo, hi], f), height: 200 });
}
function tableOf(b) {
  return U.table({ cols: b.cols.map(function (c) {
    return { k: c.k, label: c.label, align: c.align === 'r' ? 'r' : null, cls: c.wrap ? 'wrap' : null, fmt: function (v) { return v == null ? null : (fin(v) ? F.num(v, c.nd) : v); } };
  }), rows: b.rows });
}
function chartCard(b, body) {
  var meta = b.unit ? 'en ' + b.unit : null;
  return U.card({ title: b.title || null, meta: b.title ? meta : null, body: [!b.title && meta ? h('div', { class: 'note' }, meta) : null, body, b.note ? U.note(b.note) : null] });
}
function renderBlock(b, ctr) {
  switch (b.t) {
    case 'h': ctr.h++; return h('h3', { class: 'ma-h' }, h('i', null, pad(ctr.h)), b.text);
    case 'p': return h('p', { class: 'ma-p' }, b.text);
    case 'callout': return U.callout(b.text);
    case 'source': return h('p', { class: 'ma-src' }, /^source/i.test(b.text) ? b.text : 'Source : ' + b.text);
    case 'kpis': return U.kpis(b.items.map(function (it) {
      var d = it.delta != null ? F.num(it.delta, L.decimals(it.delta), it.deltaUnit || null, true) : it.deltaText;
      var hint = [d, it.hint].filter(Boolean).join(' · ');
      return { label: it.label || '—', value: L.fmtValue(it.value), unit: it.unit || null, hint: hint || null };
    }), 3);
    case 'line': return chartCard(b, lineChart(b));
    case 'bar': return chartCard(b, barChart(b));
    case 'heat': return chartCard(b, C.heat({ rows: b.rows, cols: b.cols, values: b.values, diverging: b.diverging, corner: b.unit || '', fmt: yFmtFor([].concat.apply([], b.values)) }));
    case 'table': return h('div', { class: 'ma-blk' }, b.title ? h('div', { class: 'ma-tt' }, b.title) : null, tableOf(b), b.note ? U.note(b.note) : null);
    default: return null;
  }
}
/* Rend une liste de blocs (bruts ou déjà propres) ; un bloc illisible est ignoré, jamais une erreur. */
L.renderBlocks = function (blocks) {
  var wrap = h('div', { class: 'ma-blocks' }), ctr = { h: 0 }, skipped = 0;
  L.normalizeBlocks(blocks).forEach(function (b) {
    try { var el = renderBlock(b, ctr); if (el) wrap.appendChild(el); } catch (e) { skipped++; }
  });
  if (skipped) wrap.appendChild(U.note(plural(skipped, 'bloc illisible ignoré', 'blocs illisibles ignorés') + '.'));
  return wrap;
};

/* ---------- La carte de ce que suit un desk macro ---------- */
function suiviMap() {
  var all = []; L.SUIVI.forEach(function (f) { f.items.forEach(function (it) { all.push(Object.assign({ fam: f.fam }, it)); }); });
  var sel = all.filter(function (it) { return it.id === UI.node; })[0] || all[0];
  var box = h('div', { class: 'ma-blk' });
  var map = h('div', { class: 'ma-map' }), col = h('div', { class: 'ma-col' }), nodes = [];
  var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('class', 'mw');
  var det = h('div', { class: 'ma-det' });
  function paintDet() {
    T.clear(det);
    det.appendChild(h('span', { class: 'k' }, sel.fam));
    det.appendChild(h('b', null, sel.t));
    det.appendChild(h('p', null, sel.s + '.'));
    det.appendChild(h('p', null, h('b', { style: 'font-size:13.5px;color:var(--fg)' }, 'Canal vers le Nasdaq. '), sel.nq));
    typo(det);
  }
  L.SUIVI.forEach(function (f) {
    col.appendChild(h('div', { class: 'ma-fam' }, f.fam));
    f.items.forEach(function (it) {
      var el = h('button', { class: 'ma-nd', type: 'button', 'aria-pressed': String(it.id === sel.id), on: { click: function () {
        UI.node = it.id; sel = Object.assign({ fam: f.fam }, it);
        nodes.forEach(function (n) { n.el.setAttribute('aria-pressed', String(n.id === it.id)); });
        paintDet(); draw();
      } } }, h('b', null, it.t), h('span', null, it.s));
      nodes.push({ id: it.id, el: el }); col.appendChild(el);
    });
  });
  var hub = h('div', { class: 'ma-hub' }, h('span', null, 'NASDAQ-100'), h('b', null, 'NQ'), h('span', null, 'MNQ · CME'));
  map.appendChild(svg); map.appendChild(col); map.appendChild(hub);
  function draw() {
    if (!map.isConnected) return;
    var wr = map.getBoundingClientRect(), hr = hub.getBoundingClientRect(), out = '', onPath = '';
    svg.setAttribute('width', wr.width); svg.setAttribute('height', wr.height);
    var x2 = hr.left - wr.left, top = hr.top - wr.top + 14, span = Math.max(1, hr.height - 28), n = nodes.length;
    nodes.forEach(function (nd, i) {
      var r = nd.el.getBoundingClientRect(), x1 = r.right - wr.left, y1 = r.top - wr.top + r.height / 2, y2 = top + span * i / Math.max(1, n - 1), dx = (x2 - x1) * 0.55;
      var on = nd.id === sel.id, d = 'M' + x1.toFixed(1) + ',' + y1.toFixed(1) + ' C' + (x1 + dx).toFixed(1) + ',' + y1.toFixed(1) + ' ' + (x2 - dx).toFixed(1) + ',' + y2.toFixed(1) + ' ' + x2.toFixed(1) + ',' + y2.toFixed(1);
      var seg = '<path class="' + (on ? 'on' : '') + '" d="' + d + '"/><circle class="' + (on ? 'on' : '') + '" cx="' + x1.toFixed(1) + '" cy="' + y1.toFixed(1) + '" r="2.6"/>';
      if (on) onPath = seg; else out += seg;
    });
    svg.innerHTML = out + onPath;
  }
  T.observe(map, draw);
  paintDet();
  box.appendChild(map);
  box.appendChild(U.card({ body: det, accent: true }));
  return box;
}

/* ---------- Onglet Rapports ---------- */
function reportCard(rep, first) {
  var head = [rep.date ? L.dateShort(rep.date) : 'sans date', rep.source].filter(Boolean).join(' · ');
  var sum = L.summary(rep);
  return h('button', { class: 'ma-rep' + (first ? ' first' : ''), type: 'button', on: { click: function () { UI.sel = rep.id; paintAgain(); scrollTop(); } } },
    h('span', { class: 'd' }, head),
    h('b', null, rep.title),
    rep.lede ? h('p', null, rep.lede) : null,
    rep.tags.length ? h('div', { class: 'ma-tags' }, rep.tags.slice(0, 5).map(function (t) { return U.pill(t); })) : null,
    h('div', { class: 'ft' }, h('span', null, sum || 'texte seul'), h('span', null, 'lire ›')));
}
var REPAINT = null;
function paintAgain() { if (REPAINT) REPAINT(); }
function scrollTop() { var v = document.getElementById('view'); var t = v && v.querySelector('.tabs'); if (t) { var y = t.getBoundingClientRect().top + window.scrollY - 70; if (window.scrollY > y) window.scrollTo(0, Math.max(0, y)); } }

function reportDetail(body, rep) {
  var doc = h('article', { class: 'ma-doc' });
  doc.appendChild(U.button({ label: '‹ Tous les rapports', kind: 'ghost', small: true, onClick: function () { UI.sel = null; paintAgain(); scrollTop(); } }));
  doc.lastChild.classList.add('ma-back');
  var head = [rep.date ? L.dateLong(rep.date) : 'sans date', rep.source].filter(Boolean).join(' · ');
  doc.appendChild(h('header', { class: 'ma-dh' }, h('span', { class: 'd' }, head), h('h2', null, rep.title), rep.lede ? h('p', { class: 'ld' }, rep.lede) : null,
    rep.tags.length ? h('div', { class: 'ma-tags' }, rep.tags.map(function (t) { return U.pill(t); })) : null));
  if (rep.blocks.length) doc.appendChild(L.renderBlocks(rep.blocks));
  else doc.appendChild(U.note('Ce rapport ne porte pas encore de contenu détaillé.'));
  doc.appendChild(U.note('Transcrit par Claude depuis ta capture. Un chiffre qui n’était pas lisible n’est pas recopié ; vérifie toujours la source avant de t’en servir.'));
  body.appendChild(doc);
}

function emptyReports(body) {
  var s = U.section('Aucun *rapport* pour l’instant');
  s.appendChild(U.empty({ title: 'Envoie tes captures à Claude', text: 'Prends en photo un rapport macro — une note de banque, une synthèse de recherche, un tableau de bord. Claude en relève chaque chiffre, le traduit en français et le range ici avec sa date et sa source, graphiques et tableaux compris. Rien n’est estimé : ce qui n’est pas sur la capture n’apparaît pas.' }));
  s.appendChild(U.flow({ nodes: [
    { title: 'Capture', sub: 'Le rapport tel que tu le lis, en une ou plusieurs images', state: 'active', ix: '1' },
    { title: 'Transcription', sub: 'Chaque chiffre relevé, sa date, sa source ; en français', state: 'todo', ix: '2' },
    { title: 'Lecture', sub: 'Le rapport apparaît ici, du plus récent au plus ancien', state: 'todo', ix: '3' }
  ] }));
  body.appendChild(s);
}

function renderRapports(body, ctx, data) {
  var reps = L.sortReports(data.macro);
  if (UI.sel) { var rep = reps.filter(function (r) { return r.id === UI.sel; })[0]; if (rep) { reportDetail(body, rep); return; } UI.sel = null; }
  if (!reps.length) emptyReports(body);
  else {
    var s = U.section('Rapports *reçus*', plural(reps.length, 'rapport') + (reps[0].date ? ' · dernier le ' + L.dayMonth(reps[0].date) : ''));
    var tags = []; reps.forEach(function (r) { r.tags.forEach(function (t) { if (tags.indexOf(t) < 0) tags.push(t); }); });
    if (UI.tag && tags.indexOf(UI.tag) < 0) UI.tag = null;
    if (tags.length > 1) s.appendChild(U.chips({ options: [{ v: null, label: 'Tous' }].concat(tags.slice(0, 12).map(function (t) { return { v: t, label: t }; })), value: UI.tag, onChange: function (v) { UI.tag = v; paintAgain(); } }));
    var shown = reps.filter(function (r) { return !UI.tag || r.tags.indexOf(UI.tag) >= 0; });
    s.appendChild(h('div', { class: 'ma-list' }, shown.map(function (r, i) { return reportCard(r, i === 0 && !UI.tag); })));
    body.appendChild(s);
  }
  var s2 = U.section('Ce que suit un desk *macro*', 'touche un nœud');
  s2.appendChild(suiviMap());
  s2.appendChild(U.note('Douze objets, quatre familles, aucun chiffre : la carte dit quoi regarder et par quel canal cela atteint le Nasdaq, pas ce que cela vaut aujourd’hui. Les valeurs viennent des rapports que tu envoies.'));
  body.appendChild(s2);
}

/* ---------- Onglet Régime ---------- */
function renderRegime(body, ctx, data) {
  var mine = T.store.get(K.regime, null), shared = L.latestRegime(data.macro), today = T.day.key();
  var g = mine && fin(mine.growth) ? mine.growth : null, inf = mine && fin(mine.inflation) ? mine.inflation : null;
  var chosen = g != null && inf != null, res = chosen ? L.regimeOf(g, inf) : null;
  function save(patch) {
    var cur = T.store.get(K.regime, null) || {};
    var nx = Object.assign({}, cur, patch, { at: Date.now(), day: today });
    T.store.set(K.regime, nx); ctx.rerender();
  }
  var s1 = U.section('Ta *lecture*', mine && mine.day && mine.day !== today ? 'du ' + L.dayMonth(mine.day) + ' · à confirmer' : (mine && mine.at ? 'choisie à ' + F.time(mine.at) : 'chaque matin'));
  var axes = h('div', { class: 'ma-axes' },
    h('div', { class: 'fld' }, h('label', null, 'Croissance'), U.seg({ aria: 'Croissance', options: L.SENS, value: g, onChange: function (v) { save({ growth: v }); } })),
    h('div', { class: 'fld' }, h('label', null, 'Inflation'), U.seg({ aria: 'Inflation', options: L.SENS, value: inf, onChange: function (v) { save({ inflation: v }); } })));
  var pts = [];
  if (chosen) pts.push({ x: g * L.POS, y: inf * L.POS, label: 'toi' });
  if (shared) pts.push({ x: shared.growth, y: shared.inflation, label: shared.date ? L.dayMonth(shared.date) : 'transcrit' });
  var resLine = chosen ? h('div', { class: 'ma-res' }, h('b', null, res.label), h('span', null, res.id === 'centre' ? 'aucun régime ne domine' : res.id === 'entre' ? 'à la frontière' : L.regimeById(res.id).axes))
    : U.note('Choisis le sens de la croissance et celui de l’inflation : le point se pose sur le quadrant.');
  var leg = h('div', { class: 'ma-leg' },
    chosen ? h('span', null, h('i', { style: 'background:' + (shared ? 'var(--soft)' : 'var(--violet)') }), 'ta lecture') : null,
    shared ? h('span', null, h('i', { style: 'background:var(--violet)' }), 'lecture transcrite' + (shared.date ? ' du ' + L.dayMonth(shared.date) : '') + (shared.source ? ' · ' + shared.source : '')) : null);
  s1.appendChild(U.card({ body: [axes, resLine, C.quadrant({ xLabel: 'croissance', yLabel: 'inflation', quadrants: ['Stagflation', 'Reflation', 'Désinflation', 'Goldilocks'], points: pts }), (chosen || shared) ? leg : null] }));
  s1.appendChild(U.field({ type: 'textarea', label: 'Pourquoi, en une phrase', value: mine && mine.note ? mine.note : '', placeholder: 'Ex. : les chiffres d’emploi ralentissent, l’inflation des services tient.', full: true, onChange: function (v) { var cur = T.store.get(K.regime, null) || {}; T.store.set(K.regime, Object.assign({}, cur, { note: String(v || '').slice(0, 400) })); T.toast('Phrase enregistrée'); } }));
  if (shared && (shared.label || shared.note)) s1.appendChild(U.callout([h('b', null, shared.label || 'Lecture transcrite'), shared.note ? ' — ' + shared.note : '']));
  body.appendChild(s1);

  var ids = chosen ? res.between : (shared ? L.regimeOf(shared.growth, shared.inflation).between : []);
  if (ids.length && ids.length < 4) {
    var s2 = U.section(ids.length === 1 ? 'Ce que ce régime *implique* d’ordinaire' : 'Ce que ces deux régimes *impliquent* d’ordinaire', 'tendances générales');
    ids.forEach(function (id) {
      var r = L.regimeById(id);
      s2.appendChild(U.card({ title: r.label, meta: r.axes, accent: ids.length === 1, body: h('div', { class: 'ma-two' },
        h('div', null, h('h4', null, 'Nasdaq, d’ordinaire'), h('ul', null, r.nq.map(function (t) { return h('li', null, t); }))),
        h('div', null, h('h4', null, 'Plan intraday'), h('ul', null, r.plan.map(function (t) { return h('li', null, t); })))) }));
    });
    body.appendChild(s2);
  } else if (chosen && res.id === 'centre') {
    var s2b = U.section('Au *centre*', 'aucun régime ne domine');
    s2b.appendChild(U.callout('Ni la croissance ni l’inflation ne changent de sens : le contexte ne fournit aucun biais de fond. Le plan s’exécute tel quel, sans taille supplémentaire, et le biais du jour vient du prix seul.'));
    body.appendChild(s2b);
  }

  var s3 = U.section('Les quatre *régimes*', 'touche pour choisir');
  s3.appendChild(h('div', { class: 'ma-rg' }, L.REGIMES.map(function (r) {
    var on = chosen && res.id === r.id;
    return h('button', { class: 'ma-rc', type: 'button', 'aria-pressed': String(on), on: { click: function () { save({ growth: r.g, inflation: r.i }); } } },
      h('span', { class: 'ax' }, r.axes), h('b', null, r.label), h('p', null, r.essence));
  })));
  body.appendChild(s3);
  var A = L.ALP;
  s3.appendChild(U.note('Ces associations sont des tendances générales, observées sur certaines périodes et démenties sur d’autres : jamais une promesse. Un régime est une hypothèse sur la dérive µ, la seule grandeur qui crée une espérance — à dérive nulle, toute géométrie rend −c/L. Et il ne sauve pas une géométrie trop étroite : au stop déclaré de ' + F.num(A.stopDeclarePct, 3, '%') + ' de l’indice, le seuil de rentabilité vaut ' + F.num(A.seuilDeclare, 2) + ' pt/h, au-delà du domaine de dérive jugé plausible (' + F.num(A.plausible[0], 1) + ' à ' + F.num(A.plausible[1], 1) + ' pt/h). Source : ALP nº 3, onzième partie.', true));
}

/* ---------- Onglet Calendrier ---------- */
function impactDots(n) { return h('span', { class: 'ma-imp i' + n, 'aria-label': 'impact ' + n + ' sur 3' }, [1, 2, 3].map(function (k) { return h('i', { class: k <= n ? 'on' : null }); })); }
function eventRow(e, set, past) {
  var vals = [['préc.', e.prev], ['cons.', e.cons], ['réel', e.actual]].filter(function (p) { return p[1] != null; });
  var inWin = L.inWindow(e.min, set.winFrom, set.winTo);
  return h('div', { class: 'ma-ev' + (past ? ' past' : '') },
    h('span', { class: 'tm' + (e.time ? '' : ' no') }, e.time || 'jour'),
    impactDots(e.impact),
    h('div', { class: 'tx' }, h('b', null, e.event),
      h('div', { class: 'mt' }, e.country ? U.pill(e.country) : null, inWin ? U.pill('ta fenêtre', 'acc') : null,
        vals.map(function (p) { return h('span', null, p[0] + ' ', h('em', null, L.fmtValue(p[1]))); })),
      e.note ? h('div', { class: 'nt' }, e.note) : null));
}
function familiesList(set, today) {
  return h('div', { class: 'ma-fl' }, L.FAMILLES.map(function (f) {
    var paris = f.ny ? L.nyToParis(f.ny, today) : '', mins = paris ? (+paris.slice(0, 2)) * 60 + (+paris.slice(3)) : null, inWin = L.inWindow(mins, set.winFrom, set.winTo);
    return h('div', { class: 'ma-fr' },
      h('div', null, h('b', null, f.t), h('p', null, f.s + (f.when ? ', ' + f.when + ' (heure de New York)' : '') + '.'),
        f.ny ? U.pill(inWin ? 'dans ta fenêtre' : 'hors de ta fenêtre', inWin ? 'acc' : null) : null),
      f.ny ? h('div', { class: 'hr' }, L.hhFr(paris), h('small', null, L.hhFr(f.ny) + ' à NY')) : h('div', { class: 'hr' }, '—', h('small', null, 'selon la société')));
  }));
}
function renderCalendrier(body, ctx, data) {
  var set = ctx.settings, today = T.day.key(), p = T.time.parts('Europe/Paris'), nowMin = p.h * 60 + p.m;
  var minImp = T.store.get(K.impact, 1), span = T.store.get(K.span, 'next');
  var evs = L.events(data.calendar);
  if (!evs.length) {
    var s0 = U.section('Le calendrier est *vide*');
    s0.appendChild(U.empty({ title: 'Envoie le calendrier de la semaine à Claude', text: 'Une capture du calendrier économique (celui de ton courtier, d’un site de calendrier, d’une newsletter) suffit. Claude transcrit chaque publication avec son heure de Paris, son pays, son impact de un à trois, le précédent et le consensus ; le chiffre réel s’ajoute après la publication.' }));
    body.appendChild(s0);
  } else {
    var todays = evs.filter(function (e) { return e.date === today; }), strong = todays.filter(function (e) { return e.impact === 3; });
    var nx = L.nextEvent(data.calendar, today, nowMin, 3), mu = L.minutesUntil(nx, today, nowMin);
    var inWin = todays.filter(function (e) { return L.inWindow(e.min, set.winFrom, set.winTo); });
    body.appendChild(U.kpis([
      { label: 'Aujourd’hui', value: String(todays.length), unit: todays.length > 1 ? 'publications' : 'publication', hint: strong.length ? plural(strong.length, 'à impact fort', 'à impact fort') : 'aucune à impact fort' },
      { label: 'Prochain impact fort', value: nx ? (nx.date === today ? nx.time : L.dayMonth(nx.date)) : '—', tone: nx && nx.date === today ? 'acc' : null, hint: nx ? (fin(mu) && mu < 24 * 60 ? 'dans ' + F.dur(mu) : nx.event) : 'rien à venir' },
      { label: 'Dans ta fenêtre', value: String(inWin.length), unit: 'aujourd’hui', hint: pad(set.winFrom) + '–' + pad(set.winTo) + ' h, heure de Paris' }
    ], 3));
    var ctl = h('div', { class: 'ma-ctl' },
      U.seg({ aria: 'Impact', options: [{ v: 1, label: 'Tout impact' }, { v: 2, label: 'Moyen et fort' }, { v: 3, label: 'Fort' }], value: minImp, onChange: function (v) { T.store.set(K.impact, v); paintAgain(); } }),
      U.seg({ aria: 'Période', options: [{ v: 'next', label: 'À venir' }, { v: 'all', label: 'Toute la liste' }], value: span, onChange: function (v) { T.store.set(K.span, v); paintAgain(); } }));
    body.appendChild(ctl);
    var groups = L.groupByDay(data.calendar, today, { minImpact: minImp, upcoming: span === 'next' });
    if (!groups.length) {
      var past = L.groupByDay(data.calendar, today, { minImpact: minImp }).length;
      body.appendChild(U.empty({ title: 'Rien à afficher avec ces filtres', text: span === 'next' && past ? 'Aucune publication à venir à ce niveau d’impact ; la liste complète garde les jours passés.' : 'Aucune publication à ce niveau d’impact.', action: span === 'next' && past ? U.button({ label: 'Voir toute la liste', small: true, onClick: function () { T.store.set(K.span, 'all'); paintAgain(); } }) : null }));
    }
    groups.forEach(function (gp) {
      var d = h('div', { class: 'ma-day' },
        h('div', { class: 'ma-dayh' + (gp.isToday ? ' today' : '') }, h('b', null, (gp.isToday ? 'Aujourd’hui · ' : '') + L.dateLong(gp.date)), h('span', null, plural(gp.items.length, 'publication'))),
        h('div', { class: 'ma-evs' + (gp.isToday ? ' today' : '') }, gp.items.map(function (e) { return eventRow(e, set, gp.isPast || (gp.isToday && e.min != null && e.min < nowMin - 30)); })));
      body.appendChild(d);
    });
    body.appendChild(U.note('Heures de Paris. Pastilles : impact de un à trois ; trois pastilles violettes = impact fort. « Ta fenêtre » suit les réglages (' + pad(set.winFrom) + '–' + pad(set.winTo) + ' h).'));
  }
  var s2 = U.section('Ce qui *bouge* le NQ', 'heure habituelle · à vérifier');
  s2.appendChild(familiesList(set, today));
  s2.appendChild(U.note('Heure de Paris calculée pour aujourd’hui depuis l’heure de New York : les deux pays ne changent pas d’heure le même dimanche, et l’écart passe de six à cinq heures quelques semaines par an. Un horaire de publication peut changer : le calendrier transcrit fait foi.'));
  s2.appendChild(U.callout([h('b', null, 'Autour d’un chiffre fort. '), 'Aucune position ouverte à l’instant de la publication. On laisse la première réaction se faire, puis on attend que le prix revienne à un niveau du plan : le chiffre décide du contexte, pas du point d’entrée.']));
  body.appendChild(s2);
}

/* ---------- Onglet Méthode ---------- */
function renderMethode(body, ctx) {
  var dk = K.check + T.day.key(), checked = T.store.get(dk, {}), pr = L.progress(checked), day = T.day.get();
  var mine = T.store.get(K.regime, null), regimeToday = !!(mine && mine.day === T.day.key() && fin(mine.growth) && fin(mine.inflation));
  var rg = regimeToday ? L.regimeOf(mine.growth, mine.inflation) : null;
  body.appendChild(U.kpis([
    { label: 'Routine', value: pr.n + ' / ' + pr.total, tone: pr.all ? 'acc' : null, hint: pr.all ? 'complète' : 'points cochés' },
    { label: 'Étape Macro', value: day.done.macro ? 'validée' : 'à faire', tone: day.done.macro ? 'acc' : null, hint: day.done.macro ? 'à ' + F.time(day.done.macro) : 'carte de séance' },
    { label: 'Régime du jour', value: rg ? (rg.id === 'entre' ? 'frontière' : rg.label) : 'à choisir', hint: rg ? (rg.id === 'entre' ? rg.label.toLowerCase() : 'choisi à ' + F.time(mine.at)) : 'onglet Régime', onClick: function () { ctx.setTab('regime'); } }
  ], 3));
  var s1 = U.section('La routine du *matin*', 'cochée chaque jour');
  s1.appendChild(U.checklist({ items: L.ROUTINE, checked: checked, onToggle: function (id, on) {
    var c = T.store.get(dk, {}); if (on) c[id] = Date.now(); else delete c[id]; T.store.set(dk, c);
    var p2 = L.progress(c), d2 = T.day.get();
    if (p2.all && !d2.done.macro) { T.day.mark('macro'); T.toast('Étape Macro validée'); }
    else if (!p2.all && d2.done.macro) T.day.mark('macro', false);
    ctx.rerender();
  } }));
  s1.appendChild(U.note('Rien ici n’est lu automatiquement : tu regardes, tu coches. Le but n’est pas de prévoir la séance mais de ne jamais découvrir à 14 h 29 qu’un chiffre tombe à 14 h 30.'));
  body.appendChild(s1);
  var st = L.flowStates(day.done, regimeToday);
  var s2 = U.section('De la macro *au trade*', 'chaque nœud ouvre son desk');
  s2.appendChild(U.flow({ nodes: L.FLOW.map(function (n, i) {
    var label = { macro: 'Macro', nq: 'Biais & niveaux', micro: 'Stratégie intraday', risk: 'Risque' }[n.desk];
    return { title: n.t, sub: n.s, state: st[i], go: n.desk === 'macro' ? 'onglet ›' : 'ouvrir ›', onClick: function () { if (n.desk === 'macro') ctx.setTab(n.tab); else goDesk(n.desk, null, label); } };
  }) }));
  s2.appendChild(U.note('La macro ne donne ni point d’entrée ni stop. Elle dit dans quel monde le plan s’exécute et quels moments éviter ; le reste du chemin appartient au prix.'));
  body.appendChild(s2);
}

/* ---------- Montage ---------- */
var HEAD = {
  rapports: { k: 'Macro · Rapports', t: 'Le contexte, *transcrit*.', l: 'Les rapports macro que tu envoies à Claude, remis en français avec leurs chiffres, leurs graphiques et leur source. Rien n’y est estimé : ce qui n’est pas sur la capture n’est pas ici.' },
  regime: { k: 'Macro · Régime', t: 'Dans quel *monde* on trade.', l: 'Croissance et inflation, chacune qui accélère ou ralentit : quatre régimes. Le tien se choisit chaque matin, en une phrase, et oriente le plan sans jamais le dicter.' },
  calendrier: { k: 'Macro · Calendrier', t: 'Les heures qui *comptent*.', l: 'Les publications de la semaine à l’heure de Paris, classées par impact. Un chiffre fort se trade mal à l’instant où il tombe : le plan dit d’avance ce qu’on fait autour.' },
  methode: { k: 'Macro · Méthode', t: 'La macro, *chaque* matin.', l: 'Dix points, toujours dans le même ordre, avant d’ouvrir le graphique. Quand tout est coché, l’étape « Macro » de la carte de séance se valide.' }
};
var RENDER = { rapports: renderRapports, regime: renderRegime, calendrier: renderCalendrier, methode: renderMethode };

T.desk({
  id: 'macro', label: 'Macro', glyph: 'M', group: 'Analyse', order: 10,
  tabs: [{ id: 'rapports', label: 'Rapports' }, { id: 'regime', label: 'Régime' }, { id: 'calendrier', label: 'Calendrier' }, { id: 'methode', label: 'Méthode' }],
  render: function (root, ctx) {
    injectCss();
    var tab = HEAD[ctx.tab] ? ctx.tab : 'rapports', hd = HEAD[tab];
    if (tab !== 'rapports') { UI.sel = null; }
    root.appendChild(U.page({ kicker: hd.k, title: hd.t, lede: hd.l }));
    root.appendChild(U.tabs({ tabs: this.tabs, value: tab, onChange: function (t) { UI.sel = null; ctx.setTab(t); } }));
    var body = h('div', { style: 'display:flex;flex-direction:column;gap:22px;min-width:0' });
    root.appendChild(body);
    var data = { macro: T.shared.get('macro'), calendar: T.shared.get('calendar') };
    var sig = { macro: JSON.stringify(data.macro), calendar: JSON.stringify(data.calendar) };
    function paint() {
      T.clear(body);
      try { RENDER[tab](body, ctx, data); }
      catch (e) { console.error(e); body.appendChild(U.empty({ title: 'Cette vue n’a pas pu se dessiner', text: 'Un document reçu est peut-être mal formé. Le reste du terminal fonctionne ; signale-le à Claude.' })); }
      typo(body);
    }
    REPAINT = paint;
    paint();
    typo(root.firstChild);
    var unsubs = [];
    var cols = tab === 'calendrier' ? ['calendar'] : tab === 'methode' ? [] : ['macro'];
    cols.forEach(function (c) {
      unsubs.push(T.shared.watch(c, function (rows) {
        var s = JSON.stringify(rows || []); if (s === sig[c]) return;
        sig[c] = s; data[c] = rows || [];
        var a = document.activeElement; if (a && body.contains(a) && /^(TEXTAREA|INPUT|SELECT)$/.test(a.nodeName)) return;
        paint();
      }));
    });
    var tick = tab === 'calendrier' ? setInterval(function () { if (document.visibilityState === 'visible' && !body.contains(document.activeElement)) paint(); }, 60000) : null;
    return function () { unsubs.forEach(function (u) { u(); }); if (tick) clearInterval(tick); if (REPAINT === paint) REPAINT = null; };
  }
});
