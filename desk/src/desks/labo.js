/* Labo de stratégie — le desk (LABO.md §2.4–2.8 et §6).
   Ce fichier tient l’état du Labo : versions de stratégie, registre des essais, coupure et ouvertures hors
   échantillon, cache des résultats, jeu de barres courant et exécuteur du moteur. Les calculs passent tous par
   T.lib.laboEngine.worker() (progression, annulation) ; les statistiques et le verdict viennent de
   T.lib.laboStats ; l’onglet Concevoir est délégué à T.lib.laboBuilder.render(root, ctx, api).
   T.lib.labo publie les parties pures (clés de cache, registre, bornes du document de résultats, format de
   quant:lastBacktest, règles d’ouverture hors échantillon, transitions d’état) : elles sont testées dans
   test/labo.test.js. Aucun prix de marché n’est écrit ici : sans jeu de l’utilisateur, le Labo tourne sur une
   marche sans dérive annoncée comme telle. */
var h = T.h, U = T.ui, C = T.chart, F = T.fmt;
T.lib = T.lib || {};
var LB = T.lib.labo = {};

/* =====================================================================================================
   0. Constantes et outils
   ===================================================================================================== */
var COLL = { strategies: 'labo/strategies', essais: 'labo/essais', oos: 'labo/oos', config: 'labo/config', results: 'labo/results' };
var KEY = { sel: 'labo:sel', ds: 'labo:ds', lignee: 'labo:lignee', val: 'labo:val', prop: 'labo:prop', view: 'labo:vue', go: 'donnees:go', goSeen: 'labo:goSeen' };
var SID_RE = /^s[a-z0-9]{6,20}$/, DAYKEY = /^\d{4}-\d{2}-\d{2}$/;
var MAX_TRADES = 3000, MAX_BYTES = 200000;
var PV = { MNQ: 2, NQ: 20 };
var SYNTH_NOTE = 'Aucun avantage n’existe ici : une stratégie qui y gagne est surajustée.';
LB.COLL = COLL; LB.KEY = KEY; LB.SID_RE = SID_RE; LB.MAX_TRADES = MAX_TRADES; LB.MAX_BYTES = MAX_BYTES; LB.SYNTH_NOTE = SYNTH_NOTE;

function fin(x) { return typeof x === 'number' && isFinite(x); }
function own(o, k) { return o != null && Object.prototype.hasOwnProperty.call(o, k); }
function clone(x) { return x == null ? x : JSON.parse(JSON.stringify(x)); }
function msg(e) { return String(e && e.message || e || 'Erreur inconnue.'); }
function engine() { var L = T.lib.laboEngine; if (!L || typeof L.op !== 'function') throw new Error('Le moteur du Labo n’est pas chargé dans cette page.'); return L; }
function stats() { var L = T.lib.laboStats; if (!L || typeof L.normalize !== 'function') throw new Error('Les statistiques du Labo ne sont pas chargées dans cette page.'); return L; }
function donnees() { var D = T.lib.donnees; return D && typeof D.synthetic === 'function' ? D : null; }
function hasLibs() { return !!(T.lib.laboEngine && T.lib.laboStats); }
function pad2(n) { return (n < 10 ? '0' : '') + n; }
function fmtKey(k) { return k && DAYKEY.test(k) ? k.slice(8, 10) + '/' + k.slice(5, 7) + '/' + k.slice(0, 4) : '—'; }
function fmtKeyShort(k) { return k && DAYKEY.test(k) ? k.slice(8, 10) + '/' + k.slice(5, 7) : '—'; }
function plural(n, s, p) { return F.int(n) + ' ' + (n > 1 ? (p || s + 's') : s); }
function fR(v, nd) { return fin(v) ? F.r(v, nd == null ? 3 : nd) : '—'; }
function fP(p) { return fin(p) ? F.num(p, 3) : '—'; }
function sig6(x) { return fin(x) ? +x.toPrecision(6) : null; }
var MOIS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];
var JOURS = ['', 'lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.'];
function monthLabel(m) { var p = /^(\d{4})-(\d{2})$/.exec(m || ''); return p ? MOIS[+p[2] - 1] + ' ' + p[1].slice(2) : m; }

/* Octets UTF-8 d’une chaîne (la borne de 200 Ko porte sur le document écrit, pas sur le nombre de caractères). */
LB.byteLength = function (s) {
  s = String(s); var n = 0;
  for (var i = 0; i < s.length; i++) {
    var c = s.charCodeAt(i);
    if (c < 0x80) n += 1; else if (c < 0x800) n += 2;
    else if (c >= 0xD800 && c <= 0xDBFF && i + 1 < s.length) { n += 4; i++; } else n += 3;
  }
  return n;
};
/* Copie JSON compacte : nombres non entiers à sept chiffres significatifs (les entiers, dont les horodatages,
   restent exacts), tableaux typés en tableaux, NaN et ±∞ en null. */
LB.compact = function (x, digits) {
  var d = digits || 7;
  function walk(v) {
    if (typeof v === 'number') return !isFinite(v) ? null : (v === Math.floor(v) ? v : +v.toPrecision(d));
    if (v == null || typeof v !== 'object') return v;
    if (ArrayBuffer.isView(v)) { var a = []; for (var i = 0; i < v.length; i++) a.push(walk(v[i])); return a; }
    if (Array.isArray(v)) return v.map(walk);
    var o = {}; for (var k in v) if (own(v, k) && v[k] !== undefined && typeof v[k] !== 'function') o[k] = walk(v[k]); return o;
  }
  return walk(x);
};

/* =====================================================================================================
   1. Versions de stratégie : identifiants et transitions d’état (§2.4)
   ===================================================================================================== */
LB.newSid = function (now, rnd) {
  now = fin(now) ? now : Date.now(); rnd = rnd || Math.random;
  var s = 's' + Math.floor(now).toString(36);
  for (var i = 0; i < 4; i++) s += Math.floor(rnd() * 36).toString(36);
  return s.slice(0, 21);
};
LB.versionId = function (sid, v) { return sid + '_v' + v; };
LB.STATUS = { brouillon: 'Brouillon', scellee: 'Scellée', alteree: 'Altérée' };
/* État affiché : une version scellée dont le hachage recalculé diffère est « altérée » (§2.4). */
LB.statusOf = function (doc) {
  if (!doc) return null;
  if (doc.status !== 'scellee') return 'brouillon';
  var v; try { v = stats().verifySeal(doc); } catch (e) { return 'alteree'; }
  return v && v.ok ? 'scellee' : 'alteree';
};
/* Prochain numéro de version d’un sid : le plus grand vu dans les stratégies, les essais et les ouvertures
   (une version supprimée laisse sa trace dans les registres ; son numéro ne se réutilise jamais). */
LB.nextVersion = function (sid) {
  var mx = 0;
  for (var i = 1; i < arguments.length; i++) (arguments[i] || []).forEach(function (d) { if (d && d.sid === sid && fin(d.version) && d.version > mx) mx = d.version; });
  return mx + 1;
};
function identity(s, sid, root, version, now) {
  s.sid = sid; s.root = root || sid; s.version = version; s.id = LB.versionId(sid, version);
  s.createdAt = now; s.status = 'brouillon'; s.hash = null; s.sealedAt = null;
  return s;
}
function sameSeal(stored, s) { try { return stats().hash(s) === stored.hash; } catch (e) { return false; } }
/* Enregistrer (§2.4) : un brouillon s’écrit à sa place ; une version scellée ne se modifie jamais : la
   modification devient version + 1 en brouillon. o = { stored (document enregistré sous spec.id), lists
   (tableaux de documents pour nextVersion), now, sid (nouveau sid si la spec n’en a pas) }.
   → { id, doc (à écrire, ou null), created, unchanged, errors }. */
LB.planSave = function (spec, o) {
  o = o || {}; var now = fin(o.now) ? o.now : Date.now();
  var n = stats().normalize(spec);
  if (!n.spec) throw new Error('Stratégie illisible : ' + (n.errors[0] || 'document vide.'));
  var s = clone(n.spec);
  if (!SID_RE.test(s.sid || '')) identity(s, o.sid || LB.newSid(now), SID_RE.test(s.root || '') ? s.root : null, 1, now);
  if (!fin(s.version) || s.version < 1) s.version = 1;
  s.id = LB.versionId(s.sid, s.version);
  var stored = o.stored && o.stored.id === s.id ? o.stored : null;
  if (stored && stored.status === 'scellee') {
    if (s.status === 'scellee' && sameSeal(stored, s)) return { id: stored.id, doc: null, created: false, unchanged: true, errors: n.errors };
    var v = LB.nextVersion.apply(null, [s.sid].concat(o.lists || [[stored]]));
    identity(s, s.sid, stored.root || s.root, Math.max(v, stored.version + 1), now);
    s.parent = stored.id;
    s.u = now;
    return { id: s.id, doc: s, created: true, unchanged: false, errors: n.errors };
  }
  s.status = 'brouillon'; s.hash = null; s.sealedAt = null;
  if (!SID_RE.test(s.root || '')) s.root = s.sid;
  if (!fin(s.createdAt)) s.createdAt = now;
  s.u = now;
  return { id: s.id, doc: s, created: !stored, unchanged: false, errors: n.errors };
};
/* Sceller (§2.4, §5) : hypothèse écrite, coupure hors échantillon de l’instrument fixée, aucune erreur.
   o = { stored, commissionRT, oosFrom, now }. → { ok, doc, hash } | { ok:false, why }. */
LB.planSeal = function (spec, o) {
  o = o || {};
  if (!spec) return { ok: false, why: 'Aucune stratégie à sceller.' };
  if (o.stored && o.stored.status === 'scellee') return sameSeal(o.stored, spec) ? { ok: true, doc: null, hash: o.stored.hash, already: true } : { ok: false, why: 'Cette version est déjà scellée : enregistrez d’abord la modification, elle deviendra une nouvelle version.' };
  if (!String(spec.hypothesis || '').trim()) return { ok: false, why: 'Écrivez d’abord l’hypothèse : ce que la règle exploite, et pourquoi.' };
  if (!o.oosFrom) return { ok: false, why: 'La coupure hors échantillon de l’instrument n’est pas fixée : ouvrez un jeu réel de l’instrument, elle y sera proposée.' };
  var n = stats().normalize(spec);
  if (!n.spec) return { ok: false, why: n.errors[0] || 'Stratégie illisible.' };
  if (n.errors.length) return { ok: false, why: n.errors[0] };
  try {
    var d = stats().seal(spec, o.commissionRT, fin(o.now) ? o.now : Date.now());
    ['id', 'sid', 'root', 'version', 'createdAt', 'template', 'parent'].forEach(function (k) { if (spec[k] !== undefined) d[k] = spec[k]; });
    d.u = fin(o.now) ? o.now : Date.now();
    return { ok: true, doc: d, hash: d.hash };
  } catch (e) { return { ok: false, why: msg(e).replace(/^Scellement impossible : /, '') }; }
};
/* Nouvelle version (même sid, numéro suivant) et duplication (nouveau sid, même root) : toujours en brouillon. */
LB.planNewVersion = function (spec, o) {
  o = o || {}; var now = fin(o.now) ? o.now : Date.now(), s = clone(stats().normalize(spec).spec || spec);
  var sid = SID_RE.test(s.sid || '') ? s.sid : (o.sid || LB.newSid(now));
  var v = LB.nextVersion.apply(null, [sid].concat(o.lists || []));
  if (s.id && s.sid === sid) s.parent = s.id;
  identity(s, sid, SID_RE.test(s.root || '') ? s.root : sid, v, now); s.u = now;
  return { id: s.id, doc: s };
};
LB.planDuplicate = function (spec, o) {
  o = o || {}; var now = fin(o.now) ? o.now : Date.now(), s = clone(stats().normalize(spec).spec || spec);
  var root = SID_RE.test(s.root || '') ? s.root : (SID_RE.test(s.sid || '') ? s.sid : null);
  identity(s, o.sid || LB.newSid(now), root, 1, now);
  s.name = String(s.name || 'Stratégie') + ' (copie)'; delete s.parent; s.u = now;
  return { id: s.id, doc: s };
};

/* =====================================================================================================
   2. Hors échantillon (§2.6) : coupure de l’instrument, ouvertures
   ===================================================================================================== */
/* Proposition : la clé qui laisse 30 % des séances après elle (incluse). */
LB.oosProposal = function (keys) {
  var k = (keys || []).filter(function (x) { return DAYKEY.test(x); }).slice().sort();
  if (k.length < 2) return null;
  var i = k.length - Math.max(1, Math.ceil(0.3 * k.length));
  return k[Math.max(1, i)];
};
/* Partage des séances d’un jeu : échantillon (< coupure) et hors échantillon (≥ coupure). */
LB.splitSel = function (keys, oosFrom) {
  var k = (keys || []).slice().sort(), is = [], oos = [];
  k.forEach(function (x) { if (oosFrom && x >= oosFrom) oos.push(x); else is.push(x); });
  function part(a) { return { from: a.length ? a[0] : null, to: a.length ? a[a.length - 1] : null, n: a.length }; }
  return { is: part(is), oos: part(oos), cut: oosFrom || null };
};
function overlaps(a0, a1, b0, b1) { return !((b0 != null && a1 != null && a1 < b0) || (b1 != null && a0 != null && a0 > b1)); }
/* Ouvertures d’une période : « première » si aucun document de même root et même instrument ne la recoupe
   (en excluant o.self) ; total = toutes lignées confondues. o = { root, instrument, from, to, self?, before? }. */
LB.oosOpening = function (rows, o) {
  o = o || {};
  var all = (rows || []).filter(function (d) { return d && !d.deleted && d.instrument === o.instrument && overlaps(d.from, d.to, o.from, o.to) && (!o.self || d.id !== o.self); });
  if (fin(o.before)) all = all.filter(function (d) { return (d.at || 0) < o.before; });
  all.sort(function (a, b) { return (a.at || 0) - (b.at || 0); });
  var lin = all.filter(function (d) { return d.root === o.root; });
  return { first: lin.length === 0, prior: lin.length ? lin[0] : null, lineage: lin.length, total: all.length, docs: lin };
};
/* Choisir la coupure (§2.6) : une fois, et jamais après un lancement réel sur l’instrument. */
LB.canSetOos = function (cfgDoc, essais, instrument, key) {
  if (!DAYKEY.test(key || '')) return { ok: false, why: 'Date de coupure invalide : il faut une clé de séance AAAA-MM-JJ.' };
  if (cfgDoc && cfgDoc.oosFrom) return { ok: false, why: 'La coupure de ' + instrument + ' est déjà fixée au ' + fmtKey(cfgDoc.oosFrom) + ' : elle ne change plus.' };
  if ((essais || []).some(function (e) { return e && !e.deleted && e.instrument === instrument; })) return { ok: false, why: 'Un lancement réel a déjà eu lieu sur ' + instrument + ' : la coupure ne peut plus être choisie.' };
  return { ok: true };
};
/* Ouvrir le hors échantillon : version scellée, non altérée, et des séances au-delà de la coupure. */
LB.canOpenOos = function (o) {
  o = o || {};
  if (!o.status) return { ok: false, why: 'Aucune stratégie choisie.' };
  if (o.status === 'brouillon') return { ok: false, why: 'Scellez d’abord la version (onglet Concevoir) : le hors échantillon ne s’ouvre qu’après scellement.' };
  if (o.status === 'alteree') return { ok: false, why: 'Le hachage ne correspond plus à la version scellée : elle est altérée et ne peut ouvrir le hors échantillon.' };
  if (!o.oosN) return { ok: false, why: 'Ce jeu n’a aucune séance au-delà de la coupure.' };
  if (o.opened) return { ok: false, why: 'Cette version a déjà ouvert le hors échantillon de cette période.' };
  return { ok: true };
};

/* =====================================================================================================
   3. Registre des essais (§2.5) et lignée (§2.0)
   ===================================================================================================== */
/* Documents d’essai à écrire : seulement les configHash jamais vus sur l’instrument et la période.
   o = { sid, root, version, instrument, fingerprint, from, to, op, hashes, sr }. */
LB.essaisToWrite = function (rows, o, now, rnd) {
  var L = stats(), nh = L.newHashes(rows || [], o.instrument, o.from, o.to, o.hashes || []);
  if (!nh.length) return [];
  var srOf = {}; (o.hashes || []).forEach(function (h0, i) { if (!own(srOf, h0)) srOf[h0] = (o.sr || [])[i]; });
  return L.essaiDocs({ sid: o.sid, root: o.root, version: o.version, instrument: o.instrument, fingerprint: o.fingerprint, from: o.from, to: o.to, op: o.op, hashes: nh, sr: nh.map(function (h0) { return srOf[h0]; }) }, now, rnd);
};
/* Lignée : si un compte local est inférieur à celui de la migration, « prête » est bloquée (§2.0). */
LB.lineageCheck = function (lignee, counts) {
  var lg = lignee && (lignee.v || lignee), need = lg && lg.comptes, missing = [];
  if (need && typeof need === 'object') Object.keys(need).forEach(function (k) { var n = need[k], have = counts && counts[k]; if (fin(n) && fin(have) && have < n) missing.push({ coll: k, have: have, need: n }); });
  var text = missing.length ? 'migration incomplète : ' + missing.map(function (m) { return m.coll + ' ' + F.int(m.have) + ' sur ' + F.int(m.need); }).join(', ') + '.' : null;
  return { blocked: missing.length > 0, missing: missing, text: text, sources: lg && Array.isArray(lg.sources) ? lg.sources.length : 0, migreLe: lg ? lg.migreLe : null };
};

/* =====================================================================================================
   4. Cache des résultats (§2.8)
   ===================================================================================================== */
/* Clé de cache : configHash + empreinte + sélection + op (§2.8). */
LB.cacheKey = function (o) { o = o || {}; var s = o.sel || {}; return [o.configHash || '', o.fingerprint || '', (s.from || '') + '..' + (s.to || ''), o.op || ''].join('|'); };
/* Variante : ce que configHash ne couvre pas (coûts, remplissage, taille, réglages, options du calcul). Un
   document dont la variante diffère s’affiche « calculé avec d’autres réglages ». */
LB.variantKey = function (o) { var L = stats(); return 'v' + L.fnv64(L.canonical(o == null ? null : o)); };
function shortFp(fp) {
  var D = donnees(); if (D && typeof D.shortPrint === 'function') { try { return D.shortPrint(fp); } catch (e) {} }
  return stats().fnv64(String(fp)).slice(0, 7);
}
LB.resultId = function (vid, fp, op) { return vid + '__' + shortFp(fp) + '__' + op; };
LB.cacheMatch = function (doc, want) { return !!doc && doc.key === LB.cacheKey(want); };

/* Trades du document : [[t, sens, r, pnl, fin]], les 3 000 derniers, sinon tradesOmitted. */
LB.tradeRows = function (trades, max) {
  max = fin(max) ? max : MAX_TRADES; var list = trades || [], from = Math.max(0, list.length - max), rows = [];
  for (var i = from; i < list.length; i++) { var t = list[i]; rows.push([t.t, t.side > 0 ? 1 : -1, fin(t.r) ? +t.r.toFixed(4) : null, fin(t.pnl) ? +t.pnl.toFixed(2) : null, t.fin || null]); }
  return { rows: rows, omitted: from, total: list.length };
};
/* Borne du document (≤ 200 Ko) : nombres compactés, puis trades retirés par les plus anciens, puis vues
   allégées. Le document garde toujours sa clé, ses statistiques et ses lois nulles. */
LB.fitDoc = function (doc, max) {
  max = fin(max) ? max : MAX_BYTES;
  var d = LB.compact(doc), size = function () { return LB.byteLength(JSON.stringify(d)); };
  if (Array.isArray(d.trades) && d.trades.length > MAX_TRADES) { d.tradesOmitted = (d.tradesOmitted || 0) + d.trades.length - MAX_TRADES; d.trades = d.trades.slice(d.trades.length - MAX_TRADES); }
  var s = size();
  while (s > max && Array.isArray(d.trades) && d.trades.length > 0) {
    var keep = Math.max(0, Math.floor(d.trades.length * Math.min(0.9, max / s * 0.95)));
    d.tradesOmitted = (d.tradesOmitted || 0) + d.trades.length - keep; d.trades = d.trades.slice(d.trades.length - keep); s = size();
  }
  if (s > max && d.view) { ['maemfe', 'eq', 'months', 'heat'].forEach(function (k) { if (size() > max && d.view[k]) { delete d.view[k]; d.trimmed = true; } }); s = size(); }
  if (s > max) { ['envelope', 'sweep', 'wfa', 'boot', 'stress'].forEach(function (k) { if (size() > max && d[k]) { d[k] = { omitted: true }; d.trimmed = true; } }); }
  if (s > max && d.nulls) { ['random', 'permute'].forEach(function (k) { if (d.nulls[k] && d.nulls[k].means) { delete d.nulls[k].means; d.trimmed = true; } }); }
  return d;
};

/* quant:lastBacktest au format de quant.js : { label, at, source, trades: [{ at, pnl, r, side }] } ; les 3 000
   derniers trades, truncated = nombre total de trades quand la liste a été coupée (0 sinon). rows : lignes du
   document de résultats ([t, sens, r, pnl, fin]) ou trades du moteur. */
LB.lastBacktest = function (rows, o) {
  o = o || {}; rows = rows || [];
  var total = fin(o.total) ? o.total : rows.length, from = Math.max(0, rows.length - MAX_TRADES), out = [];
  for (var i = from; i < rows.length; i++) {
    var x = rows[i], t = Array.isArray(x) ? { at: x[0], side: x[1], r: x[2], pnl: x[3] } : { at: x.t, side: x.side, r: x.r, pnl: x.pnl };
    out.push({ at: t.at, pnl: fin(t.pnl) ? Math.round(t.pnl * 100) / 100 : null, r: fin(t.r) ? Math.round(t.r * 10000) / 10000 : null, side: t.side > 0 ? 'long' : 'short' });
  }
  var cut = total > out.length;
  return { label: o.label || 'Labo', at: fin(o.at) ? o.at : Date.now(), source: o.source || 'csv', trades: out, truncated: cut ? total : 0 };
};

/* =====================================================================================================
   5. Vues tirées des trades (pures)
   ===================================================================================================== */
LB.eqOf = function (trades) { var s = 0, o = []; (trades || []).forEach(function (t) { if (!fin(t.pnl)) return; s += t.pnl; o.push([fin(t.tx) ? t.tx : t.t, s]); }); return o; };
LB.downsample = function (pts, max) {
  pts = pts || []; max = max || 400; if (pts.length <= max) return pts.slice();
  var o = [], step = (pts.length - 1) / (max - 1); for (var i = 0; i < max; i++) o.push(pts[Math.round(i * step)]); return o;
};
LB.underwater = function (eq) { var pk = 0, o = []; (eq || []).forEach(function (p) { if (p[1] > pk) pk = p[1]; o.push([p[0], p[1] - pk]); }); return o; };
LB.months = function (trades) {
  var by = {}, out = [];
  (trades || []).forEach(function (t) { var k = String(t.key || '').slice(0, 7); if (!/^\d{4}-\d{2}$/.test(k) || !fin(t.r)) return; var m = by[k] || (by[k] = { m: k, n: 0, sumR: 0, net: 0 }); m.n++; m.sumR += t.r; m.net += fin(t.pnl) ? t.pnl : 0; });
  Object.keys(by).sort().forEach(function (k) { var m = by[k]; m.meanR = m.n ? m.sumR / m.n : null; out.push(m); });
  return out;
};
LB.heat = function (trades) {
  var cell = {}, days = {}, hours = {};
  (trades || []).forEach(function (t) { if (!fin(t.hour) || !fin(t.dow) || !fin(t.r)) return; var k = t.dow + ':' + t.hour, c = cell[k] || (cell[k] = { s: 0, n: 0 }); c.s += t.r; c.n++; days[t.dow] = 1; hours[t.hour] = 1; });
  var D = Object.keys(days).map(Number).sort(function (a, b) { return a - b; }), H = Object.keys(hours).map(Number).sort(function (a, b) { return a - b; });
  return { days: D, hours: H, mean: D.map(function (d) { return H.map(function (hh) { var c = cell[d + ':' + hh]; return c ? c.s / c.n : null; }); }), n: D.map(function (d) { return H.map(function (hh) { var c = cell[d + ':' + hh]; return c ? c.n : 0; }); }) };
};
LB.maeMfe = function (trades, max) {
  var pts = []; (trades || []).forEach(function (t) { if (t.risk > 0 && fin(t.mae) && fin(t.mfe) && fin(t.r)) pts.push([t.mae / t.risk, t.mfe / t.risk, t.r]); });
  return LB.downsample(pts, max || 400);
};
/* Sankey des issues : signaux → exécutés / expirés / annulés / ambigus → raisons de sortie. */
LB.sankeyOf = function (counts, byFin, n) {
  counts = counts || {}; byFin = byFin || {};
  var exe = fin(n) ? n : 0, exp = (counts.expire || 0) + (counts.trou || 0), ann = (counts.taille || 0) + (counts.stopcourt || 0) + (counts.ecart || 0) + (counts.annule || 0), amb = counts.ambigu || 0;
  var sigs = Math.max(counts.signals || 0, exe + exp + ann + amb), other = sigs - (exe + exp + ann + amb);
  var FINS = (T.lib.laboStats && T.lib.laboStats.FINS) || {};
  var nodes = [{ id: 'sig', label: 'Signaux', col: 0, tone: 'violet' }, { id: 'exe', label: 'Exécutés', col: 1 }, { id: 'exp', label: 'Expirés', col: 1, tone: 'mute' }, { id: 'ann', label: 'Annulés', col: 1, tone: 'mute' }, { id: 'amb', label: 'Ambigus', col: 1, tone: 'mute' }, { id: 'oth', label: 'Sans suite', col: 1, tone: 'mute' }];
  var links = [{ s: 'sig', t: 'exe', v: exe, tone: 'violet' }, { s: 'sig', t: 'exp', v: exp }, { s: 'sig', t: 'ann', v: ann }, { s: 'sig', t: 'amb', v: amb }, { s: 'sig', t: 'oth', v: other }];
  ['objectif', 'stop', 'be', 'trail', 'temps', 'flat', 'cloche', 'oppose'].forEach(function (f) { var b = byFin[f]; if (b && b.n > 0) { nodes.push({ id: 'f-' + f, label: FINS[f] || f, col: 2, tone: f === 'objectif' ? 'violet' : null }); links.push({ s: 'exe', t: 'f-' + f, v: b.n, tone: f === 'objectif' ? 'violet' : null }); } });
  var used = {}; links.forEach(function (l) { if (l.v > 0) { used[l.s] = 1; used[l.t] = 1; } });
  return { nodes: nodes.filter(function (x) { return used[x.id]; }), links: links.filter(function (l) { return l.v > 0; }) };
};
/* Valeurs d’une grille (comme le moteur) : min + i·pas jusqu’à max, arrondies à 10 décimales. */
LB.gridValues = function (min, max, step) {
  if (!fin(min)) return [];
  if (!fin(max) || max < min || !(step > 0)) return [min];
  var o = []; for (var i = 0; i <= 400; i++) { var x = +(min + i * step).toFixed(10); if (x > max + 1e-9) break; o.push(x); }
  return o;
};
/* Saisie rapide (Suivre) : pnl = qty·(sens·(sortie − entrée)·pv − commission) ; r = pnl / (qty·|entrée − stop|·pv). */
LB.quickTrade = function (o) {
  o = o || {}; var sd = o.side === 'short' ? -1 : 1, q = o.qty, pv = o.pointValue, cm = fin(o.commissionRT) ? o.commissionRT : 0;
  if (!(q >= 1) || Math.floor(q) !== q) return { ok: false, why: 'Quantité : un nombre entier de contrats.' };
  if (!fin(o.entry) || !fin(o.exit)) return { ok: false, why: 'Il faut l’entrée et la sortie.' };
  if (!(pv > 0)) return { ok: false, why: 'Valeur du point inconnue.' };
  var pnl = q * (sd * (o.exit - o.entry) * pv - cm), r = null, L = fin(o.stop) ? Math.abs(o.entry - o.stop) : NaN;
  if (fin(o.stop) && sd * (o.entry - o.stop) <= 0) return { ok: false, why: 'Le stop doit être du côté de la perte : sous l’entrée à l’achat, au-dessus à la vente.' };
  if (L > 0) r = pnl / (q * L * pv);
  var fn = fin(o.target) && sd * (o.exit - o.target) >= 0 ? 'objectif' : fin(o.stop) && sd * (o.exit - o.stop) <= 0 ? 'stop' : 'manuel';
  return { ok: true, pnl: Math.round(pnl * 100) / 100, r: r === null ? null : Math.round(r * 10000) / 10000, fin: fn };
};
/* Écart à l’enveloppe : R cumulé du suivi contre n·meanR pessimiste, optimiste et sans avantage (−costR). */
LB.envelopeGap = function (rs, o) {
  o = o || {}; var cum = 0, real = [[0, 0]], lo = [[0, 0]], hi = [[0, 0]], nul = [[0, 0]], k = 0;
  (rs || []).forEach(function (r) { if (!fin(r)) return; k++; cum += r; real.push([k, cum]); if (fin(o.pess)) lo.push([k, k * o.pess]); if (fin(o.opt)) hi.push([k, k * o.opt]); if (fin(o.costR)) nul.push([k, -k * o.costR]); });
  var gap = k && fin(o.pess) && fin(o.opt) ? (cum < k * Math.min(o.pess, o.opt) ? 'dessous' : cum > k * Math.max(o.pess, o.opt) ? 'dessus' : 'dedans') : null;
  return { real: real, pess: lo.length > 1 ? lo : [], opt: hi.length > 1 ? hi : [], nul: nul.length > 1 ? nul : [], n: k, cum: cum, where: gap };
};
/* Opérandes d’une règle (aperçu) : tout objet { f } ou { op, a, b } rencontré dans les conditions, l’entrée,
   le stop et l’objectif, sans doublon (au plus 8). */
LB.operandsOf = function (rule) {
  var out = [], seen = {};
  function isOp(x) { return x && typeof x === 'object' && !Array.isArray(x) && (typeof x.f === 'string' || (typeof x.op === 'string' && /^[-+*/]$/.test(x.op) && 'a' in x)); }
  function add(x) { var k = JSON.stringify(x); if (!seen[k] && out.length < 8) { seen[k] = 1; out.push(x); } }
  function walk(x, depth) {
    if (!x || typeof x !== 'object' || depth > 8) return;
    if (isOp(x)) { add(x); return; }
    if (Array.isArray(x)) { x.forEach(function (y) { walk(y, depth + 1); }); return; }
    Object.keys(x).forEach(function (k) { if (k !== 'tz' && k !== 'news') walk(x[k], depth + 1); });
  }
  if (rule) { walk(rule.setup, 0); walk(rule.trigger, 0); if (rule.entry) walk(rule.entry.at, 0); if (rule.stop) walk(rule.stop.at, 0); if (rule.target) walk(rule.target.at, 0); }
  return out;
};
/* Publications du calendrier (collection calendar, heure de Paris) → [{ t (ms UTC), impact }]. */
LB.newsFrom = function (docs) {
  var Q = T.lib.quant, out = [];
  (docs || []).forEach(function (d) {
    if (!d || !DAYKEY.test(String(d.date || '').trim())) return;
    var m = /^([01]?\d|2[0-3])\s*[:h]\s*([0-5]\d)$/.exec(String(d.time || '').trim()); if (!m) return;
    var p = d.date.trim().split('-').map(Number), imp = Math.max(1, Math.min(3, Math.round(+d.impact || 1))), t = NaN;
    if (Q && typeof Q.wallToUtc === 'function') { try { t = Q.wallToUtc(p[0], p[1], p[2], +m[1], +m[2], 'Europe/Paris'); } catch (e) { t = NaN; } }
    if (fin(t)) out.push({ t: t, impact: imp });
  });
  return out.sort(function (a, b) { return a.t - b.t; });
};

/* =====================================================================================================
   6. État de la visite : jeu courant, exécuteur, cache mémoire, calculs en cours
   ===================================================================================================== */
var S = { ex: null, exFp: null, exReady: null, synth: null, ds: null, dsId: null, dsErr: null, loading: null, res: {}, jobs: {}, errs: {}, jobEls: {},
  mem: { essais: [], oos: [] }, view: null, builderCleanup: null, confirmOos: null, quick: { side: 'long', entry: null, stop: null, target: null, exit: null, qty: 1 }, timer: 0, vue3d: false };
function coll(name) { return name === 'results' ? T.ucoll(COLL.results, { mirror: false, live: false }) : T.ucoll(COLL[name]); }
function exec() { if (!S.ex) { S.ex = engine().worker(); S.exFp = null; S.exReady = null; } return S.ex; }
function workerOk() { try { return typeof Worker === 'function' && typeof Blob === 'function' && typeof URL !== 'undefined' && typeof URL.createObjectURL === 'function'; } catch (e) { return false; } }
function closeVisit() {
  Object.keys(S.jobs).forEach(function (k) { try { S.jobs[k].cancel(true); } catch (e) {} });
  S.jobs = {}; S.jobEls = {};
  if (S.ex) { try { S.ex.close(); } catch (e) {} }
  S.ex = null; S.exFp = null; S.exReady = null;
}
function isSynth(ds) { return !!ds && (ds.meta.source === 'synthetique' || ds.meta.id === 'synthetique'); }
function fpOf(ds) { return ds ? (ds.meta.fingerprint || ('id:' + ds.meta.id)) : null; }
function account() {
  var R = T.lib.risk; if (!R || typeof R.normAccount !== 'function') return null;
  try { return R.normAccount(T.store.get('risk:account', null)); } catch (e) { return null; }
}
function engineSettings(ds) {
  var s = T.settings.get(), inst = ds && ds.meta && ds.meta.instrument, a = account();
  return { tick: fin(s.tick) && s.tick > 0 ? s.tick : 0.25, pointValue: PV[inst] || (fin(s.pointValue) && s.pointValue > 0 ? s.pointValue : 2), commissionRT: fin(s.commissionRT) ? s.commissionRT : 0, maxContracts: a && fin(a.maxContracts) ? a.maxContracts : 0 };
}

/* ---- Jeu de barres ---- */
function dsOptions(want) {
  var D = donnees(), out = [{ v: 'synthetique', label: 'Marche sans dérive (synthétique)' }];
  if (want && /^ds[a-z0-9]{6,20}$/.test(want) && D && !(D.datasets() || []).some(function (m) { return m.id === want; })) out.push({ v: want, label: 'Jeu du compte (en attente)' });
  if (!D) return out;
  var v = D.visit(); if (v && !isSynth(v)) out.push({ v: 'visite', label: (v.meta.name || 'Fichier local') + ' · visite' });
  (D.datasets() || []).filter(function (m) { return D.usable(m); }).forEach(function (m) { out.push({ v: m.id, label: (m.name || m.id) + ' · ' + (m.instrument || 'MNQ') }); });
  return out;
}
function wantDs() { var id = T.store.get(KEY.ds, 'synthetique'), ok = dsOptions().some(function (o) { return o.v === id; }); return ok ? id : (id === 'visite' || !donnees() || !/^ds[a-z0-9]{6,20}$/.test(id) ? 'synthetique' : id); }
function setDs(ds) {
  S.ds = ds; S.loading = null; S.dsErr = null;
  var fp = fpOf(ds); if (S.exFp === fp) return;
  S.exFp = fp; S.exReady = null;
  var ex; try { ex = exec(); } catch (e) { S.dsErr = msg(e); return; }
  ex.load(fp, ds.bars).then(function () { if (S.exFp === fp) { S.exReady = fp; schedule(); } }, function () {});
}
function ensureDs() {
  var D = donnees(), id = wantDs();
  if (!D || !hasLibs()) return;
  if (S.dsId === id && (S.ds || S.loading || S.dsErr)) { if (S.ds && S.exFp !== fpOf(S.ds)) setDs(S.ds); return; }
  S.dsId = id; S.ds = null; S.dsErr = null; S.loading = null;
  if (id === 'synthetique') {
    var v = D.visit(); if (!S.synth && v && isSynth(v)) S.synth = v;
    if (S.synth) { setDs(S.synth); return; }
    S.loading = 'Préparation de la marche sans dérive (60 séances)…';
    setTimeout(function () {
      try { S.synth = D.synthetic({ seed: 1, sessions: 60, sigma: 2 }); if (S.dsId === 'synthetique') setDs(S.synth); }
      catch (e) { if (S.dsId === 'synthetique') { S.dsErr = msg(e); S.loading = null; } }
      schedule();
    }, 40);
    return;
  }
  if (id === 'visite') { var vv = D.visit(); if (vv) setDs(vv); else S.dsErr = 'Le fichier de la visite n’est plus en mémoire : rechargez-le dans Données.'; return; }
  S.loading = 'Chargement du jeu…';
  D.loadDataset(id).then(function (ds) { if (S.dsId !== id) return; setDs(ds); schedule(); }, function (e) { if (S.dsId !== id) return; S.loading = null; S.dsErr = (D.errorText && e && e.code ? D.errorText(e) : msg(e)); schedule(); });
}

/* ---- Versions ---- */
function versions() { return coll('strategies').list().filter(function (d) { return d && d.id && d.sid; }).sort(function (a, b) { return (b.u || 0) - (a.u || 0); }); }
function currentDoc() {
  var all = versions(), id = T.store.get(KEY.sel, null), d = null;
  for (var i = 0; i < all.length; i++) if (all[i].id === id) { d = all[i]; break; }
  return d || all[0] || null;
}
function specOf(doc) {
  if (!doc) return null;
  var n; try { n = stats().normalize(doc); } catch (e) { n = { spec: null }; }
  var s = n.spec ? n.spec : clone(doc);
  ['id', 'sid', 'root', 'version', 'status', 'hash', 'sealedAt', 'createdAt', 'u', 'template', 'parent'].forEach(function (k) { if (doc[k] !== undefined) s[k] = doc[k]; });
  return s;
}
function selectVersion(id, rerender) { T.store.set(KEY.sel, id); S.confirmOos = null; if (rerender !== false) { if (S.view) S.view.ctx.rerender(); } }
function essaisRows(synth) { return synth ? S.mem.essais.slice() : coll('essais').list(); }
function oosRows(synth) { return synth ? S.mem.oos.slice() : coll('oos').list(); }
function cfgDoc(inst) { return coll('config').get('oos-' + inst); }
function oosInfo(inst, keys) {
  var d = cfgDoc(inst), prop = keys ? LB.oosProposal(keys) : (S.ds && !isSynth(S.ds) && (S.ds.meta.instrument || 'MNQ') === inst ? LB.oosProposal(S.ds.sessions.map(function (s) { return s.key; })) : null);
  return { oosFrom: d && d.oosFrom ? d.oosFrom : prop, fixed: !!(d && d.oosFrom), proposal: prop, at: d ? d.at : null };
}
function setOosFrom(inst, key) {
  var r = LB.canSetOos(cfgDoc(inst), coll('essais').list(), inst, key);
  if (!r.ok) return Promise.resolve(r);
  return Promise.resolve(coll('config').set('oos-' + inst, { oosFrom: key, instrument: inst, at: Date.now() })).then(function () { schedule(); return { ok: true }; });
}
/* Au plus tard au premier lancement réel : la coupure proposée devient la coupure de l’instrument. */
function ensureCut(X) {
  if (X.synth || X.cutFixed || !X.cut) return;
  coll('config').set('oos-' + X.inst, { oosFrom: X.cut, instrument: X.inst, at: Date.now(), auto: true });
  X.cutFixed = true;
}
function localCounts() {
  var c = {};
  ['labo/strategies', 'labo/essais', 'labo/oos', 'labo/config', 'datasets/items', 'levels/items', 'inbox/items'].forEach(function (p) { try { c[p] = T.ucoll(p).list().length; } catch (e) {} });
  try { c['journal/trades'] = T.journal.list().length; } catch (e) {}
  return c;
}

/* ---- Contexte d’un rendu ---- */
function context() {
  var X = { doc: currentDoc(), ds: S.ds };
  X.spec = specOf(X.doc); X.status = LB.statusOf(X.doc);
  if (X.spec) {
    X.vid = X.spec.id;
    try { X.norm = stats().normalize(X.spec); } catch (e) { X.norm = { spec: null, errors: [msg(e)], warnings: [] }; }
    X.errors = X.norm.errors || [];
    try { X.configHash = stats().configHash(X.spec); } catch (e) { X.configHash = null; }
    X.params = X.spec.params && typeof X.spec.params === 'object' ? Object.keys(X.spec.params) : [];
  }
  X.settings = engineSettings(X.ds);
  if (X.ds) {
    X.fp = fpOf(X.ds); X.synth = isSynth(X.ds); X.inst = X.ds.meta.instrument || 'MNQ';
    X.keys = X.ds.sessions.map(function (s) { return s.key; });
    var info = X.synth ? { oosFrom: LB.oosProposal(X.keys), fixed: true, demo: true } : oosInfo(X.inst, X.keys);
    X.cut = info.oosFrom; X.cutFixed = info.fixed; X.cutDemo = !!info.demo;
    X.split = LB.splitSel(X.keys, X.cut);
    X.rolls = X.ds.meta.roll === 'non-ajuste' ? X.ds.sessions.filter(function (s) { return s.roll; }).map(function (s) { return s.key; }) : [];
    X.ready = S.exReady === X.fp || (S.ex && S.ex.mode === 'local' && S.exFp === X.fp);
    X.trials = X.split.is.n ? stats().trials(essaisRows(X.synth), X.inst, X.split.is.from, X.split.is.to, { lignee: T.store.get(KEY.lignee, null) }) : { N: 0, inherited: 0, sdTrials: null };
  }
  X.lineage = LB.lineageCheck(T.store.get(KEY.lignee, null), localCounts());
  return X;
}
function fullHash(X) { try { return stats().hash(X.spec, X.settings.commissionRT); } catch (e) { return null; } }
function baseA(X, sel, extra) {
  var a = { spec: X.norm && X.norm.spec ? X.norm.spec : X.spec, values: {}, settings: X.settings, sel: { from: sel.from, to: sel.to }, adj: X.ds.adj || null, rolls: X.rolls, oosFrom: X.cut || undefined, fp: X.fp, seed: 1 };
  if (!X.synth && X.ds.levels) a.levels = X.ds.levels;
  if (JSON.stringify(a.spec).indexOf('"news"') >= 0) a.news = LB.newsFrom(T.shared.get('calendar'));
  if (extra) for (var k in extra) a[k] = extra[k];
  return a;
}
function floorCosts(X) { return stats().floorCosts(X.spec.costs || {}, X.settings.commissionRT); }
function variantOf(op, X, opts) {
  var base = { h: fullHash(X), s: X.settings, op: op };
  if (op === 'verdict' || op === 'oos') base.floor = floorCosts(X);
  if (opts) base.o = opts;
  return LB.variantKey(base);
}
function keyOf(op, X, sel) { return LB.cacheKey({ configHash: X.configHash, fingerprint: X.fp, sel: sel || X.split.is, op: op }); }
function findDoc(op, X, sel) {
  if (!X.spec || !X.fp || !X.configHash) return null;
  var k = keyOf(op, X, sel), d = S.res[k];
  if (d) return d;
  try { var c = coll('results').get(LB.resultId(X.vid, X.fp, op)); if (c && c.key === k) { S.res[k] = c; return c; } } catch (e) {}
  return null;
}
function baseDoc(X, op, sel, opts) {
  sel = sel || X.split.is;
  return { id: LB.resultId(X.vid, X.fp, op), key: keyOf(op, X, sel), variant: variantOf(op, X, opts), sid: X.spec.sid, version: X.spec.version, hash: X.spec.hash || null, configHash: X.configHash,
    fingerprint: X.fp, ds: X.ds.meta.id, dsName: X.ds.meta.name || null, synthetic: !!X.synth, instrument: X.inst, sel: { from: sel.from, to: sel.to }, op: op, at: Date.now() };
}
function saveResult(doc) {
  var d = LB.fitDoc(doc); S.res[d.key] = d;
  try { coll('results').set(d.id, d); } catch (e) {}
  return d;
}
function recordEssais(X, op, hashes, srs) {
  if (!hashes.length) return [];
  var o = { sid: X.spec.sid, root: X.spec.root || X.spec.sid, version: X.spec.version, instrument: X.inst, fingerprint: X.fp, from: X.split.is.from, to: X.split.is.to, op: op, hashes: hashes, sr: srs };
  var docs = LB.essaisToWrite(essaisRows(X.synth), o);
  docs.forEach(function (d) { if (X.synth) S.mem.essais.push(d); else coll('essais').set(d.id, d); });
  return docs;
}

/* ---- Calculs : un par onglet, le suivant annule le précédent ---- */
function cancelErr() { var e = new Error('Calcul annulé.'); e.cancelled = true; return e; }
function startJob(tab, label, nSteps, body) {
  var prev = S.jobs[tab]; if (prev) prev.cancel(true);
  var job = { tab: tab, label: label, n: Math.max(1, nSteps), k: -1, frac: 0, step: 'En file…', dead: false, handle: null };
  job.call = function (op, a, step) {
    if (job.dead) return Promise.reject(cancelErr());
    job.k = Math.min(job.n - 1, job.k + 1); job.frac = 0; job.step = step; paintJob(job);
    job.handle = exec().call(op, a, function (p) { job.frac = fin(p) ? p : 0; paintJob(job); });
    return job.handle.promise.then(function (r) { if (job.dead) throw cancelErr(); return r; });
  };
  job.cancel = function (silent) { if (job.dead) return; job.dead = true; if (job.handle) { try { job.handle.cancel(); } catch (e) {} } if (S.jobs[tab] === job) delete S.jobs[tab]; if (!silent) schedule(); };
  S.jobs[tab] = job; delete S.errs[tab]; schedule();
  Promise.resolve().then(function () { return body(job); }).then(function () {
    if (S.jobs[tab] === job) delete S.jobs[tab]; job.dead = true; schedule();
  }, function (e) {
    var was = job.dead; if (S.jobs[tab] === job) delete S.jobs[tab]; job.dead = true;
    if (!(e && e.cancelled) && !was) { S.errs[tab] = msg(e); if (typeof console !== 'undefined' && console.warn) console.warn('Labo :', e); }
    schedule();
  });
  return job;
}
function paintJob(job) {
  var el = S.jobEls[job.tab]; if (!el || !el.bar.isConnected) return;
  var p = Math.max(0, Math.min(1, (job.k + job.frac) / job.n));
  el.bar.style.width = (100 * p).toFixed(1) + '%'; el.txt.textContent = 'Étape ' + (job.k + 1 < 1 ? 1 : job.k + 1) + ' sur ' + job.n + ' · ' + job.step;
}
function schedule() { clearTimeout(S.timer); S.timer = setTimeout(repaint, 40); }
function repaint() {
  var v = S.view; if (!v || !v.root.isConnected) return;
  if (v.tab === 'concevoir') { paintHead(); return; }
  var y = window.scrollY; paint(); try { window.scrollTo(0, y); } catch (e) {}
}

/* =====================================================================================================
   7. Composants locaux
   ===================================================================================================== */
var CSS = '.lb-head{display:grid;gap:10px;margin:2px 0 16px;padding:12px;border:1px solid var(--line);border-radius:var(--r);background:var(--panel);min-width:0}' +
  '.lb-tags{display:flex;flex-wrap:wrap;gap:6px}.lb-tag{display:inline-flex;align-items:baseline;gap:5px;max-width:100%;padding:4px 8px;border:1px solid var(--line-2);border-radius:7px;background:var(--raise);font:500 11.5px/1.35 var(--f-mono);color:var(--soft);overflow-wrap:anywhere}.lb-tag b{color:var(--fg);font-weight:600}.lb-tag.acc{border-color:var(--violet-b);background:var(--violet-a)}.lb-tag.no{background-image:var(--hatch);color:var(--fg)}' +
  '.lb-job{display:grid;gap:8px;padding:12px;margin:0 0 14px;border:1px solid var(--violet-b);border-radius:var(--r);background:var(--violet-a)}.lb-job .lb-row{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}.lb-job b{color:var(--fg);font-weight:600;font-size:13.5px}' +
  '.lb-bar{height:6px;border-radius:3px;background:var(--line);overflow:hidden}.lb-bar i{display:block;height:100%;width:0;background:var(--violet);transition:width .25s}' +
  '.lb-step{font:500 11.5px/1.45 var(--f-mono);color:var(--soft);overflow-wrap:anywhere}' +
  '.lb-launch{display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px;margin:0 0 16px}.lb-launch p{margin:0;flex:1 1 220px;min-width:0;color:var(--soft);font-size:13px;line-height:1.5}' +
  '.lb-items{display:grid;gap:8px}.lb-it{display:grid;grid-template-columns:20px minmax(0,1fr) auto;gap:3px 10px;align-items:start;padding:10px 12px;border:1px solid var(--line);border-radius:var(--r);background:var(--panel)}' +
  '.lb-it .ic{font:600 13px/1.35 var(--f-mono);color:var(--mute)}.lb-it[data-p=ok] .ic{color:var(--violet)}.lb-it[data-p=ko]{background-image:var(--hatch)}.lb-it[data-p=ko] .ic{color:var(--fg)}' +
  '.lb-it b{font-weight:600;color:var(--fg);font-size:13.5px}.lb-it .v{font:600 12px/1.35 var(--f-mono);color:var(--fg);text-align:right;max-width:46vw;overflow-wrap:anywhere}.lb-it .nd{display:block;font:500 10.5px/1.3 var(--f-mono);color:var(--mute)}.lb-it .w{grid-column:2/4;color:var(--soft);font-size:12.5px;line-height:1.5}' +
  '.lb-grid{display:grid;gap:14px;min-width:0}@media(min-width:900px){.lb-grid.two{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}}' +
  '.lb-kv{display:grid;grid-template-columns:auto minmax(0,1fr);gap:5px 12px;margin:0;font-size:13px}.lb-kv dt{color:var(--mute)}.lb-kv dd{margin:0;color:var(--fg);text-align:right;font-family:var(--f-mono);font-size:12.5px;overflow-wrap:anywhere}' +
  '.lb-tpl{display:grid;gap:10px}@media(min-width:760px){.lb-tpl{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}}.lb-tpl .card p{margin:0 0 10px;color:var(--soft);font-size:13px;line-height:1.5}' +
  '.lb-read{margin:0;padding:0;list-style:none;display:grid;gap:9px}.lb-read li{font-size:13.5px;line-height:1.55;color:var(--soft)}.lb-read b{display:block;color:var(--fg);font-weight:600;font-size:12.5px;margin-bottom:1px}' +
  '.lb-mono{font:500 11.5px/1.5 var(--f-mono);color:var(--mute);overflow-wrap:anywhere}.lb-acts{display:flex;flex-wrap:wrap;gap:8px;align-items:center}' +
  '.lb-lvl{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 12px}.lb-lvl em{font-family:var(--f-serif);font-style:italic;font-size:28px;line-height:1.1;color:var(--hi)}' +
  '.lb-txt{margin:0;color:var(--soft);font-size:13.5px;line-height:1.55}.lb-txt b{color:var(--fg);font-weight:600}' +
  '.lb-stack{display:grid;gap:12px;min-width:0}.lb-ver{display:grid;gap:4px;width:100%;text-align:left;padding:11px 12px;border:1px solid var(--line);border-radius:var(--r);background:var(--panel);color:var(--fg);cursor:pointer;font:inherit}.lb-ver[aria-current=true]{border-color:var(--violet)}.lb-ver span{color:var(--soft);font-size:12.5px;line-height:1.45}';
function injectCss() { if (document.getElementById('labo-css')) return; var s = document.createElement('style'); s.id = 'labo-css'; s.textContent = CSS; document.head.appendChild(s); }
function tag(text, strong, kind) { return h('span', { class: 'lb-tag' + (kind ? ' ' + kind : '') }, text, strong != null ? h('b', null, strong) : null); }
function kv(rows) { return h('dl', { class: 'lb-kv' }, rows.filter(Boolean).map(function (r) { return [h('dt', null, r[0]), h('dd', null, r[1] == null || r[1] === '' ? '—' : r[1])]; })); }
function txt(parts) { return h('p', { class: 'lb-txt' }, parts); }
function sec(root, title, meta) { var s = U.section(title, meta); root.appendChild(s); return s; }
function noData(W, t) { return { svg: '<svg viewBox="0 0 ' + W + ' 60" height="60"><text class="ax" x="' + (W / 2) + '" y="34" text-anchor="middle">' + T.esc(t || 'Pas encore de données') + '</text></svg>' }; }
/* Nuage de points (MAE/MFE) : le socle n’en a pas ; même grammaire que C.line (classes ax, gl, zl). */
function scatter(o) {
  return C.mount(o.legend ? { legend: o.legend } : null, function (W) {
    var pts = (o.points || []).filter(function (p) { return fin(p[0]) && fin(p[1]); }), H = o.height || 230, m = { l: 44, r: 12, t: 12, b: 30 };
    if (!pts.length) return noData(W);
    var xs = pts.map(function (p) { return p[0]; }), ys = pts.map(function (p) { return p[1]; });
    var x0 = Math.min(0, Math.min.apply(null, xs)), x1 = Math.max.apply(null, xs), y0 = Math.min(0, Math.min.apply(null, ys)), y1 = Math.max.apply(null, ys);
    if (x1 <= x0) x1 = x0 + 1; if (y1 <= y0) y1 = y0 + 1; x1 += (x1 - x0) * 0.04; y1 += (y1 - y0) * 0.05;
    var sx = function (v) { return m.l + (v - x0) / (x1 - x0) * (W - m.l - m.r); }, sy = function (v) { return m.t + (1 - (v - y0) / (y1 - y0)) * (H - m.t - m.b); }, g = '', X = T.esc;
    T.ticks(y0, y1, 4).forEach(function (v) { if (v < y0 || v > y1) return; g += '<line class="' + (v === 0 ? 'zl' : 'gl') + '" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + sy(v) + '" y2="' + sy(v) + '"/><text class="ax" x="' + (m.l - 7) + '" y="' + (sy(v) + 3.5) + '" text-anchor="end">' + X(F.num(v, 1)) + '</text>'; });
    T.ticks(x0, x1, Math.max(2, Math.floor((W - m.l - m.r) / 70))).forEach(function (v) { if (v < x0 || v > x1) return; g += '<text class="ax" x="' + sx(v) + '" y="' + (H - 12) + '" text-anchor="middle">' + X(F.num(v, 1)) + '</text>'; });
    (o.vlines || []).forEach(function (l) { if (l.x < x0 || l.x > x1) return; g += '<line x1="' + sx(l.x) + '" x2="' + sx(l.x) + '" y1="' + m.t + '" y2="' + (H - m.b) + '" stroke="var(--line-2)" stroke-dasharray="3 4"/>' + (l.label ? '<text class="axl" x="' + (sx(l.x) + 4) + '" y="' + (m.t + 10) + '">' + X(l.label) + '</text>' : ''); });
    pts.forEach(function (p) { g += '<circle cx="' + sx(p[0]).toFixed(1) + '" cy="' + sy(p[1]).toFixed(1) + '" r="2.6" fill="' + (p[2] > 0 ? 'var(--violet)' : 'var(--soft)') + '" opacity=".75"/>'; });
    g += '<text class="axl" x="' + (W - m.r) + '" y="' + (H - 1) + '" text-anchor="end">' + X(o.xName || '') + ' →</text><text class="axl" x="' + (m.l + 4) + '" y="' + (m.t + 10) + '">↑ ' + X(o.yName || '') + '</text>';
    g += '<line class="hl" x1="0" x2="0" y1="' + m.t + '" y2="' + (H - m.b) + '" stroke="var(--violet)" style="opacity:0"/>';
    return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '">' + g + '</svg>', hover: { xs: pts.map(function (p) { return sx(p[0]); }), html: function (i) { var p = pts[i]; return '<b>' + X(o.fmtTip ? o.fmtTip(p) : F.num(p[0], 2) + ' · ' + F.num(p[1], 2)) + '</b>'; } } };
  });
}
/* Loi nulle en histogramme : tirages, valeur observée, p, p minimal, étiquette. */
function nullHist(r, o) {
  var means = (r.means || []).filter(fin), obs = r.obs, lo = means.length ? Math.min.apply(null, means) : 0, hi = means.length ? Math.max.apply(null, means) : 1;
  if (fin(obs)) { lo = Math.min(lo, obs); hi = Math.max(hi, obs); }
  var pad = (hi - lo) * 0.06 || 0.05, refs = [];
  if (fin(obs)) refs.push({ x: obs, label: 'observé ' + F.num(obs, 3), tone: 'violet' });
  if (o && fin(o.zero)) refs.push({ x: o.zero, label: o.zeroLabel || '', tone: 'mute', dash: true });
  return C.hist({ values: means, refs: refs, min: lo - pad, max: hi + pad, fmt: function (v) { return F.num(v, 2); }, height: 160 });
}
function heatTable(hm) {
  if (!hm || !hm.days || !hm.days.length) return U.note('Pas de trade : pas de carte.');
  return C.heat({ rows: hm.days.map(function (d) { return JOURS[d] || String(d); }), cols: hm.hours.map(function (x) { return pad2(x) + ' h'; }), values: hm.mean.map(function (r) { return r.map(function (v) { return v == null ? NaN : v; }); }), fmt: function (v) { return F.num(v, 2); }, diverging: true, corner: 'R moyen' });
}

/* =====================================================================================================
   8. En-tête commun
   ===================================================================================================== */
var HEAD = {
  concevoir: { k: 'Labo de stratégie · Concevoir', t: 'Écrire la règle, *avant* le résultat.', l: 'Une stratégie se lit bloc par bloc, en français : séance, contexte, déclencheur, entrée, stop, objectif. Chaque nombre devient un paramètre nommé.' },
  tester: { k: 'Labo de stratégie · Tester', t: 'Le résultat, et ce que le *hasard* en ferait.', l: 'Un backtest ne s’affiche jamais seul : à côté, des entrées tirées au hasard, des prix permutés et une marche sans dérive.' },
  valider: { k: 'Labo de stratégie · Valider', t: 'Un sommet, ou un *plateau* ?', l: 'Balayer les réglages, mesurer le surajustement, avancer fenêtre par fenêtre, stresser les coûts, rééchantillonner les séances.' },
  verdict: { k: 'Labo de stratégie · Verdict', t: 'Neuf critères, *aucune* promesse.', l: 'Le verdict se calcule aux coûts planchers, avec des seuils écrits dans le code et justifiés un par un.' },
  suivre: { k: 'Labo de stratégie · Suivre', t: 'Le réel, trade par *trade*.', l: 'Les trades du journal qui portent la stratégie, lus par un test séquentiel et une alarme d’usure.' }
};
function headEl(X) {
  var box = h('div', { class: 'lb-head', role: 'region', 'aria-label': 'Stratégie et jeu courants' });
  var vs = versions();
  var vOpts = vs.length ? vs.map(function (d) { return { v: d.id, label: (d.name || 'Sans nom') + ' · v' + d.version + ' · ' + (LB.STATUS[d.status === 'scellee' ? 'scellee' : 'brouillon']).toLowerCase() }; }) : [{ v: '', label: 'Aucune stratégie' }];
  box.appendChild(U.fields([
    U.field({ label: 'Stratégie', type: 'select', value: X.doc ? X.doc.id : '', options: vOpts, onChange: function (v) { if (v) selectVersion(v); } }),
    U.field({ label: 'Jeu de barres', type: 'select', value: wantDs(), options: dsOptions(wantDs()), onChange: function (v) { T.store.set(KEY.ds, v); S.dsId = null; ensureDs(); if (S.view) S.view.ctx.rerender(); } })
  ]));
  var tags = h('div', { class: 'lb-tags' });
  if (X.spec) {
    var st = X.status;
    tags.appendChild(tag('', LB.STATUS[st], st === 'scellee' ? 'acc' : st === 'alteree' ? 'no' : null));
    if (st !== 'brouillon' && X.spec.hash) tags.appendChild(tag('scellée ', String(X.spec.hash).slice(0, 9)));
    else if (X.configHash) tags.appendChild(tag('config ', X.configHash.slice(0, 9)));
    var nv = vs.filter(function (d) { return d.root === (X.spec.root || X.spec.sid); }).length;
    tags.appendChild(tag('lignée ', (X.spec.root || X.spec.sid) + ' · ' + plural(nv, 'version')));
  }
  if (X.ds && X.trials) {
    var N = X.trials.N || 0;
    tags.appendChild(tag(X.synth ? 'essais de la visite ' : 'N = ', F.int(N) + (X.synth ? '' : ' essai' + (N > 1 ? 's' : '')) + (X.trials.inherited ? ' · dont ' + F.int(X.trials.inherited) + ' hérités' : (X.synth ? '' : ' · dont 0 hérité'))));
    if (X.cut) tags.appendChild(tag(X.cutDemo ? 'coupure de démonstration ' : 'hors échantillon dès le ', fmtKey(X.cut) + (X.cutDemo ? '' : X.cutFixed ? ' · fixée' : ' · proposée')));
  }
  box.appendChild(tags);
  if (X.ds && X.synth) box.appendChild(U.note('Marche sans dérive : ' + SYNTH_NOTE.charAt(0).toLowerCase() + SYNTH_NOTE.slice(1) + ' Rien de ce qui s’y calcule n’entre au registre des essais.', true));
  if (X.ds && X.spec && X.spec.instrument && X.inst && X.spec.instrument !== X.inst) box.appendChild(U.note('La stratégie vise ' + X.spec.instrument + ', le jeu porte sur ' + X.inst + ' : les essais se comptent sur l’instrument du jeu.', true));
  if (S.loading) box.appendChild(U.note(S.loading));
  if (S.dsErr) box.appendChild(U.note(S.dsErr, true));
  if (X.lineage && X.lineage.blocked) box.appendChild(U.note('Lignée : ' + X.lineage.text + ' Le niveau « prête » reste bloqué tant que la migration n’est pas complète.', true));
  if (!workerOk()) box.appendChild(U.note('Cet appareil n’offre pas de calcul en tâche de fond : les calculs lourds (hasard, permutations, balayage, bootstrap) y sont impossibles.', true));
  if (!T.cloudReady() && X.ds && !X.synth) box.appendChild(U.note('Compte non joignable : les essais et ouvertures sont gardés sur cet appareil seulement.'));
  return box;
}
function paintHead() {
  var v = S.view; if (!v || !v.head || !v.head.isConnected) return;
  var X = context(), n = headEl(X); v.head.parentNode.replaceChild(n, v.head); v.head = n;
}

/* =====================================================================================================
   9. Lancement, progression, erreurs
   ===================================================================================================== */
function launchBar(tab, o) {
  var job = S.jobs[tab], wrap = h('div');
  if (job) {
    var bar = h('i'), t = h('span', { class: 'lb-step', role: 'status' }, job.step);
    wrap.appendChild(h('div', { class: 'lb-job' }, h('div', { class: 'lb-row' }, h('b', null, job.label), U.button({ label: 'Annuler', small: true, kind: 'ghost', onClick: function () { job.cancel(); } })), h('div', { class: 'lb-bar', role: 'progressbar', 'aria-label': job.label }, bar), t));
    S.jobEls[tab] = { bar: bar, txt: t }; paintJob(job);
    return wrap;
  }
  if (S.errs[tab]) wrap.appendChild(U.note('Le calcul a échoué : ' + S.errs[tab], true));
  var row = h('div', { class: 'lb-launch' }, U.button({ label: o.label, kind: 'pri', disabled: o.disabled || null, onClick: o.onClick }), h('p', null, o.text));
  wrap.appendChild(row);
  if (o.doc) wrap.appendChild(h('p', { class: 'lb-mono', style: 'margin:-6px 0 14px' }, 'Calculé le ' + F.dateLong(o.doc.at) + ' à ' + F.time(o.doc.at) + ' · ' + (o.doc.dsName || o.doc.ds) + ' · ' + fmtKey(o.doc.sel && o.doc.sel.from) + ' → ' + fmtKey(o.doc.sel && o.doc.sel.to) + (o.fresh === false ? ' · réglages ou coûts modifiés depuis : relancez' : '')));
  return wrap;
}
function useTemplate(id) {
  var L = stats(), doc = L.fromTemplate(id, LB.newSid());
  coll('strategies').set(doc.id, doc);
  T.toast('Brouillon créé depuis le gabarit');
  selectVersion(doc.id);
  return doc.id;
}
function templateCards(compact) {
  var L = T.lib.laboStats; if (!L || !L.TEMPLATES) return h('div');
  return h('div', { class: 'lb-tpl' }, L.TEMPLATES.map(function (t) {
    return U.card({ title: t.label, body: [compact ? null : h('p', null, t.description), U.button({ label: 'Partir de ce gabarit', small: true, onClick: function () { useTemplate(t.id); } })] });
  }));
}
/* Garde commune des onglets de calcul : bibliothèques, stratégie, jeu, échantillon. */
function guard(body, X) {
  if (!hasLibs()) { body.appendChild(U.empty({ title: 'Le moteur du Labo n’est pas chargé', text: 'Cette page a été construite sans labo-engine ou labo-stats.' })); return false; }
  if (!X.spec) {
    body.appendChild(U.empty({ title: 'Aucune stratégie pour l’instant', text: 'Écrivez-en une dans Concevoir, envoyez sa description à Claude, ou partez d’un gabarit. Aucun gabarit ne prétend à un avantage : ce sont des points de départ.' }));
    body.appendChild(templateCards(true));
    return false;
  }
  if (!donnees()) { body.appendChild(U.empty({ title: 'Le desk Données n’est pas chargé', text: 'Sans lui, le Labo ne peut lire aucun jeu, pas même la marche synthétique.' })); return false; }
  if (!X.ds) { body.appendChild(U.empty({ title: S.dsErr ? 'Jeu indisponible' : 'Jeu en préparation', text: S.dsErr || S.loading || 'Le jeu de barres se prépare.' })); return false; }
  if (!X.split.is.n) { body.appendChild(U.empty({ title: 'Aucune séance en échantillon', text: 'Toutes les séances de ce jeu tombent au-delà de la coupure du ' + fmtKey(X.cut) + ' : elles sont hors échantillon.' })); return false; }
  if (X.errors && X.errors.length) { body.appendChild(U.callout([h('b', null, 'La stratégie ne passe pas la validation.'), h('p', null, X.errors.slice(0, 4).join(' · '))])); return false; }
  return true;
}
function sampleLine(X) { return 'Échantillon : ' + plural(X.split.is.n, 'séance') + ', du ' + fmtKey(X.split.is.from) + ' au ' + fmtKey(X.split.is.to) + '.'; }

/* =====================================================================================================
   10. Onglet Tester
   ===================================================================================================== */
function nullLite(r) {
  if (!r) return null;
  var o = {}; ['means', 'obs', 'p', 'pmin', 'lo', 'hi', 'mid', 'draws', 'n', 'nMean', 'label', 'h0', 'cut', 'block', 'fbShare', 'signals', 'pLong', 'ms', 'objective', 'configs'].forEach(function (k) { if (r[k] !== undefined) o[k] = r[k]; });
  return o;
}
function envLite(e) { return e ? { stats: { n: e.stats.n, meanR: e.stats.meanR, net: e.stats.net, winRate: e.stats.winRate, pf: e.stats.pf, maxDD: e.stats.maxDD }, eq: LB.downsample(e.eq || [], 400), counts: e.counts } : null; }
function runTester(X) {
  ensureCut(X);
  var a = baseA(X, X.split.is), N = Math.max(1, (X.trials && X.trials.N) || 0), out = {};
  startJob('tester', 'Test en échantillon', 5, function (job) {
    return job.call('run', a, 'Exécution de la stratégie').then(function (r) {
      out.run = r; recordEssais(X, 'run', X.configHash ? [X.configHash] : [], [r.stats.sharpeTrade]);
      return job.call('envelope', a, 'Enveloppe pessimiste et optimiste');
    }).then(function (r) { out.env = r; return job.call('random', Object.assign({}, a, { draws: 200, N: N + (X.synth ? 0 : 0) }), 'Entrées au hasard (200 tirages)'); })
      .then(function (r) { out.random = r; return job.call('permute', Object.assign({}, a, { draws: 100, minDraws: 50, budgetMs: 60000, N: N }), 'Prix permutés (jusqu’à 100 tirages)'); })
      .then(function (r) { out.permute = r; return job.call('synth', a, 'Marche sans dérive calibrée').catch(function (e) { if (e && e.cancelled) throw e; return { applicable: false, reason: msg(e) }; }); })
      .then(function (r) {
        out.synth = r;
        var run = out.run, doc = baseDoc(X, 'tester'), rows = LB.tradeRows(run.trades, MAX_TRADES);
        doc.costs = run.costs; doc.fill = run.fill; doc.stats = run.stats; doc.counts = run.counts; doc.warnings = (run.warnings || []).slice(0, 12); doc.sessions = run.sessions.length;
        doc.nulls = { random: nullLite(out.random), permute: nullLite(out.permute), synth: out.synth };
        doc.envelope = { pess: envLite(out.env.pess), opt: envLite(out.env.opt) };
        doc.view = { eq: LB.downsample(LB.eqOf(run.trades), 500), maemfe: LB.maeMfe(run.trades, 400), heat: LB.heat(run.trades), months: LB.months(run.trades) };
        doc.trades = rows.rows; if (rows.omitted) doc.tradesOmitted = rows.omitted;
        saveResult(doc);
      });
  });
}
function renderTester(body, X) {
  if (!guard(body, X)) return;
  var doc = findDoc('tester', X), fresh = doc ? doc.variant === variantOf('tester', X) : null;
  body.appendChild(launchBar('tester', { label: doc ? 'Relancer le test' : 'Lancer le test', onClick: function () { runTester(context()); }, disabled: !X.ready && !S.jobs.tester, doc: doc, fresh: fresh,
    text: sampleLine(X) + ' Exécution, enveloppe, 200 entrées au hasard, jusqu’à 100 permutations et une marche sans dérive calibrée.' }));
  if (!doc) { body.appendChild(readingCard(X)); return; }
  var st = doc.stats || {}, nl = doc.nulls || {};
  var s1 = sec(body, 'Ce que la stratégie *a fait*', plural(st.n || 0, 'trade') + ' · ' + plural(doc.sessions || 0, 'séance'));
  s1.appendChild(U.kpis([
    { label: 'Trades', value: F.int(st.n || 0), hint: plural(doc.sessions || 0, 'séance') + ' jouées' },
    { label: 'Réussite', value: fin(st.winRate) ? F.pct(st.winRate, 1) : '—', hint: 'équilibre ' + (fin(st.equilibrium) ? F.pct(st.equilibrium, 1) : '—'), tone: fin(st.winRate) && fin(st.equilibrium) && st.winRate > st.equilibrium ? 'acc' : null },
    { label: 'Espérance', value: fR(st.meanR), hint: 'sans avantage ' + fR(fin(st.costR) ? -st.costR : NaN), tone: st.meanR > 0 ? 'acc' : st.meanR < 0 ? 'neg' : null },
    { label: 'Espérance pondérée', value: fR(st.rW), hint: 'sans avantage ' + fR(st.rW0) },
    { label: 'Net', value: fin(st.net) ? F.usd(st.net, 0, true) : '—', hint: fin(st.expectancy) ? F.usd(st.expectancy, 2, true) + ' par trade' : null, tone: st.net < 0 ? 'neg' : null },
    { label: 'Facteur de profit', value: fin(st.pf) ? F.num(st.pf, 2) : '—', hint: 'gains bruts sur pertes brutes' },
    { label: 'Sharpe par trade', value: fin(st.sharpeTrade) ? F.num(st.sharpeTrade, 3) : '—', hint: 'écart-type ' + (fin(st.sdR) ? F.num(st.sdR, 2) + ' R' : '—') },
    { label: 'Perte maximale', value: fin(st.maxDD) ? F.usd(st.maxDD, 0) : '—', hint: 'creux de l’équité' }
  ], 4));
  var gap = fin(st.meanR) && fin(st.costR) ? st.meanR + st.costR : NaN;
  s1.appendChild(U.callout([txt(['Sans avantage, une stratégie perd son coût : ', h('b', null, fR(-st.costR)), ' par trade ici (commission et glissement rapportés au risque). Celle-ci fait ', h('b', null, fR(st.meanR)), fin(gap) ? ', soit ' + fR(gap) + ' d’écart. ' : '. ', 'Seules les lois nulles plus bas disent si cet écart sort du hasard.'])]));
  if ((doc.warnings || []).length) s1.appendChild(U.note('Avertissements du moteur : ' + doc.warnings.slice(0, 4).join(' · '), true));

  var s2 = sec(body, 'Équité et *enveloppe*', 'pessimiste · déclaré · optimiste');
  var eq = (doc.view && doc.view.eq) || [], env = doc.envelope || {};
  s2.appendChild(C.line({ series: [{ name: 'déclaré (' + (doc.fill || 'pessimiste') + ')', points: eq, tone: 'fg' }, { name: 'pessimiste', points: env.pess ? env.pess.eq : [], tone: 'mute', dash: true }, { name: 'optimiste', points: env.opt ? env.opt.eq : [], tone: 'violet', dash: true }], x: { type: 'time' }, y: { zero: true, fmt: function (v) { return F.usd(v, 0); } }, height: 220 }));
  s2.appendChild(U.note('L’enveloppe rejoue les mêmes ordres quand le stop et l’objectif tombent dans la même barre : le pessimiste prend le stop, l’optimiste l’objectif. La vérité est entre les deux.'));
  s2.appendChild(C.line({ series: [{ name: 'sous l’eau', points: LB.underwater(eq), tone: 'violet', area: true }], x: { type: 'time' }, y: { zero: true, fmt: function (v) { return F.usd(v, 0); } }, height: 140 }));

  var rs = (doc.trades || []).map(function (r) { return r[2]; }).filter(fin);
  var g3 = h('div', { class: 'lb-grid two' });
  var c1 = U.card({ title: 'Distribution des R', meta: plural(rs.length, 'trade'), body: [C.hist({ values: rs, refs: [{ x: st.meanR, label: 'moyenne', tone: 'violet' }, { x: fin(st.costR) ? -st.costR : NaN, label: 'sans avantage', tone: 'fg', dash: true }], fmt: function (v) { return F.num(v, 1); }, height: 170 })] });
  var mm = (doc.view && doc.view.maemfe) || [];
  var c2 = U.card({ title: 'Excursions MAE et MFE', meta: 'en R du risque initial', body: [scatter({ points: mm, xName: 'MAE (R)', yName: 'MFE (R)', vlines: [{ x: 1, label: 'stop' }], fmtTip: function (p) { return 'MAE ' + F.num(p[0], 2) + ' R · MFE ' + F.num(p[1], 2) + ' R · ' + F.r(p[2], 2); } }), U.note('En violet les trades gagnants. Un gagnant loin à droite a frôlé son stop ; un perdant haut placé a laissé filer un gain.')] });
  g3.appendChild(c1); g3.appendChild(c2); body.appendChild(g3);

  var s4 = sec(body, 'Heure et *jour*', 'R moyen par cellule');
  s4.appendChild(heatTable(doc.view && doc.view.heat));
  s4.appendChild(U.note('Heure dans le fuseau de la séance de la stratégie, jour de la clé Globex. Une cellule de quelques trades ne dit rien : c’est une carte, pas un filtre.'));

  var s5 = sec(body, 'Ce que deviennent les *signaux*', 'signaux → exécution → sortie');
  var sk = LB.sankeyOf(doc.counts, st.byFin, st.n);
  s5.appendChild(C.sankey({ nodes: sk.nodes, links: sk.links, height: 250 }));
  if (doc.counts && doc.counts.limite) s5.appendChild(U.note(plural(doc.counts.limite, 'signal refusé', 'signaux refusés') + ' par une limite de séance (entrées, pertes, perte du jour) : non comptés ci-dessus.'));

  var s6 = sec(body, 'Les trois *lois nulles*', 'aucun résultat ne s’affiche seul');
  var g6 = h('div', { class: 'lb-grid two' });
  [['random', 'Entrées au hasard', 'Mêmes ordres, même nombre par séance, posés à des instants tirés au sort.'], ['permute', 'Prix permutés', null]].forEach(function (q) {
    var r = nl[q[0]];
    if (!r) { g6.appendChild(U.card({ title: q[1], body: U.note('Pas calculé.') })); return; }
    g6.appendChild(U.card({ title: q[1], meta: 'p = ' + fP(r.p), body: [nullHist(r, { zero: fin(st.costR) ? -st.costR : NaN, zeroLabel: '−c/L' }), kv([['p', fP(r.p)], ['p minimal atteignable', fP(r.pmin)], ['tirages', F.int(r.draws || (r.means || []).length) + (r.cut ? ' (coupés par le temps)' : '')], ['médiane des tirages', fR(r.mid)], ['90 % des tirages', fR(r.lo) + ' à ' + fR(r.hi)]]), U.note(q[2] || ('Hypothèse nulle : ' + (r.h0 || 'l’ordre des minutes ne porte aucune information') + '.')), U.note(nullLabel(r.label, X))] }));
  });
  var sy = nl.synth;
  if (sy && sy.applicable) {
    var bars = [['Théorie −c/L', sy.theory], ['Ordre vrai', sy.vrai], ['Déclaré', sy.declare], ['Stratégie', st.meanR]];
    g6.appendChild(U.card({ title: 'Marche sans dérive', meta: 'σ ' + F.num(sy.sigma, 2) + ' pt / min', body: [C.bar({ cats: bars.map(function (b) { return b[0]; }), series: [{ name: 'R par trade', values: bars.map(function (b) { return fin(b[1]) ? b[1] : 0; }), tone: 'violet' }], horizontal: true, fmt: function (v) { return F.num(v, 3); }, rowH: 30, ml: 100 }),
      kv([['séances simulées', F.int(sy.sessions)], ['trades (ordre vrai)', F.int(sy.n)], ['erreur-type', fin(sy.se) ? F.num(sy.se, 3) + ' R' : '—'], ['biais du remplissage', fR(sy.biais)]]),
      U.note('Une marche au tick, calibrée sur la volatilité de la fenêtre, où aucun avantage n’existe. C’est le résultat sous le remplissage déclaré, pas −c/L, qui sert de plancher.')] }));
  } else g6.appendChild(U.card({ title: 'Marche sans dérive', body: U.note(sy && sy.reason ? 'Non applicable : ' + sy.reason : 'Non applicable à cette stratégie.') }));
  s6.appendChild(g6);

  var s7 = sec(body, 'Les *trades*', doc.tradesOmitted ? 'les ' + F.int((doc.trades || []).length) + ' derniers sur ' + F.int((doc.trades || []).length + doc.tradesOmitted) : plural((doc.trades || []).length, 'trade'));
  var FINS = stats().FINS, shown = (doc.trades || []).slice(-150).reverse();
  s7.appendChild(U.table({ cols: [
    { k: 0, label: 'Entrée', fmt: function (v) { return F.date(v) + ' ' + F.time(v); } },
    { k: 1, label: 'Sens', fmt: function (v) { return v > 0 ? 'achat' : 'vente'; } },
    { k: 2, label: 'R', align: 'r', fmt: function (v) { return fR(v, 2); } },
    { k: 3, label: 'Net', align: 'r', fmt: function (v) { return fin(v) ? F.usd(v, 2, true) : '—'; } },
    { k: 4, label: 'Sortie', fmt: function (v) { return FINS[v] || v || '—'; } }
  ], rows: shown, rowClass: function (r) { return r[3] < 0 ? 'neg' : null; }, empty: 'Aucun trade.' }));
  if ((doc.trades || []).length > shown.length) s7.appendChild(U.note('Les ' + F.int(shown.length) + ' plus récents sont listés ; tous partent vers Métriques.'));
  s7.appendChild(h('div', { class: 'lb-acts', style: 'margin-top:12px' }, U.button({ label: 'Ouvrir dans Métriques', small: true, kind: 'pri', disabled: !(doc.trades || []).length || null, onClick: function () { openMetrics(X, doc); } }), h('span', { class: 'lb-mono' }, 'Écrit les trades comme source « Backtest » du desk Métriques.')));
}
function nullLabel(label, X) {
  var N = X.trials ? X.trials.N || 0 : 0;
  return String(label || 'configuration isolée').replace(/N = <a\.N>|N( =)? …|N essais|N = \d+ essais/, 'N = ' + F.int(Math.max(1, N)) + ' essais') + (/essais/.test(String(label || '')) ? '' : ', non corrigée des N = ' + F.int(Math.max(1, N)) + ' essais') + '.';
}
function openMetrics(X, doc) {
  var total = (doc.trades || []).length + (doc.tradesOmitted || 0);
  var bt = LB.lastBacktest(doc.trades, { label: (X.spec.name || 'Stratégie') + ' · v' + X.spec.version + ' · ' + (X.synth ? 'synthétique' : (X.ds.meta.name || X.inst)), source: X.synth ? 'synth' : 'csv', total: total });
  T.store.set('quant:lastBacktest', bt);
  T.toast('Trades envoyés au desk Métriques');
  if (T.desks().some(function (d) { return d.id === 'perf'; })) T.nav.go('perf');
}
function readingCard(X) {
  var items = [];
  try { items = stats().describe(X.spec, { values: {} }); } catch (e) { items = []; }
  return U.card({ title: 'La règle, en *français*', meta: X.spec.name || '', body: items.length ? h('ul', { class: 'lb-read' }, items.map(function (b) { return h('li', null, h('b', null, b.title), b.text); })) : U.note('Lecture indisponible.') });
}

/* =====================================================================================================
   11. Onglet Valider
   ===================================================================================================== */
function valState(X) {
  var all = T.store.get(KEY.val, {}) || {}, st = all[X.spec.sid] || {}, names = X.params || [], P = X.spec.params || {};
  var p1 = names.indexOf(st.p1) >= 0 ? st.p1 : (names[0] || null);
  var p2 = st.p2 === '' ? '' : (names.indexOf(st.p2) >= 0 && st.p2 !== p1 ? st.p2 : (names.filter(function (n) { return n !== p1; })[0] || ''));
  var r = {}; names.forEach(function (n) { var p = P[n] || {}, o = (st.r || {})[n] || {}, v = fin(p.v) ? p.v : 0; r[n] = { min: fin(o.min) ? o.min : (fin(p.min) ? p.min : v), max: fin(o.max) ? o.max : (fin(p.max) ? p.max : v), step: fin(o.step) && o.step > 0 ? o.step : (fin(p.step) && p.step > 0 ? p.step : 1) }; });
  var ns = X.split.is.n, isD = Math.max(5, Math.round(ns * 0.5)), ooD = Math.max(2, Math.round(ns * 0.12));
  return { p1: p1, p2: p2, r: r, is: fin(st.is) && st.is >= 1 ? Math.round(st.is) : isD, oos: fin(st.oos) && st.oos >= 1 ? Math.round(st.oos) : ooD, mode: st.mode === 'anchored' ? 'anchored' : 'rolling' };
}
function setVal(X, patch) { var all = T.store.get(KEY.val, {}) || {}; all[X.spec.sid] = Object.assign({}, all[X.spec.sid] || {}, patch); T.store.set(KEY.val, all); }
function gridOf(vs) {
  if (!vs.p1) return null;
  var xs = LB.gridValues(vs.r[vs.p1].min, vs.r[vs.p1].max, vs.r[vs.p1].step), ys = vs.p2 ? LB.gridValues(vs.r[vs.p2].min, vs.r[vs.p2].max, vs.r[vs.p2].step) : null;
  return { p1: vs.p1, p2: vs.p2 || null, xs: xs, ys: ys, cells: xs.length * (ys ? ys.length : 1) };
}
function cscvAsync(mat) {
  if (!Array.isArray(mat) || mat.length < 2 || !T.lib.quant) return Promise.resolve(null);
  var perf = mat.map(function (row) { return (row || []).map(function (c) { return fin(c) ? c : c && fin(c.net) ? c.net : 0; }); });
  if (!perf[0] || perf[0].length < 8) return Promise.resolve({ value: null, error: 'il faut au moins huit séances' });
  /* Même calcul que T.lib.laboStats.pbo (T.lib.quant.cscv), exécuté hors du fil principal. */
  return T.compute(T.lib.quant.engine, { op: 'cscv', perf: perf, nb: 8 }).then(function (r) { r = r || {}; r.value = fin(r.pbo) ? r.pbo : null; delete r.logits; return r; });
}
function dsrOf(X, st) {
  var tr = stats().trials(essaisRows(X.synth), X.inst, X.split.is.from, X.split.is.to, { n: st.n, lignee: T.store.get(KEY.lignee, null) });
  var d = stats().dsr({ sr: st.sharpeTrade, n: st.n, N: Math.max(1, tr.N), skew: st.skew, exkurt: st.exkurt, sdTrials: tr.sdTrials });
  d.inherited = tr.inherited; d.Nreg = tr.N; d.sdSource = tr.sdSource || d.sdSource;
  return d;
}
function runValider(X) {
  var vs = valState(X), grid = gridOf(vs);
  if (grid && grid.cells > 400) { S.errs.valider = 'La grille compte ' + F.int(grid.cells) + ' cellules : le moteur en accepte 400 au plus.'; schedule(); return; }
  ensureCut(X);
  var a = baseA(X, X.split.is), out = {}, n = 3 + (grid ? 2 : 0);
  var opts = { grid: grid ? { p1: grid.p1, p2: grid.p2, xs: grid.xs, ys: grid.ys } : null, wfa: { is: vs.is, oos: vs.oos, mode: vs.mode } };
  startJob('valider', 'Validation en échantillon', n, function (job) {
    return job.call('run', a, 'Exécution de référence').then(function (r) {
      out.run = r; recordEssais(X, 'run', X.configHash ? [X.configHash] : [], [r.stats.sharpeTrade]);
      if (!grid) return null;
      return job.call('sweep', Object.assign({}, a, { p1: grid.p1, p2: grid.p2 || undefined, xs: grid.xs, ys: grid.ys || undefined, objective: 'meanR', minTrades: 1 }), 'Balayage de ' + plural(grid.cells, 'configuration'));
    }).then(function (sw) {
      out.sweep = sw;
      if (sw) {
        var hashes = [], srs = [];
        sw.configs.forEach(function (vals, k) { try { hashes.push(stats().configHash(X.spec, vals)); var c = sw.cells[Math.floor(k / sw.xs.length)][k % sw.xs.length]; srs.push(c ? c.sharpe : null); } catch (e) {} });
        recordEssais(X, 'sweep', hashes, srs);
        if (X.split.is.n < vs.is + 1) { out.wfaErr = 'Analyse en avant : ' + plural(X.split.is.n, 'séance') + ' en échantillon, il en faut au moins ' + (vs.is + 1) + '.'; return null; }
        return job.call('wfa', { mat: sw.mat, keys: sw.keys, configs: sw.configs, sel: a.sel, oosFrom: a.oosFrom, wfa: { is: vs.is, oos: vs.oos, mode: vs.mode, objective: 'meanR', minTrades: 1 } }, 'Analyse en avant').catch(function (e) { if (e && e.cancelled) throw e; out.wfaErr = msg(e); return null; });
      }
      return null;
    }).then(function (w) { out.wfa = w; return job.call('stress', a, 'Stress des coûts'); })
      .then(function (r) { out.stress = r; return job.call('boot', Object.assign({}, a, { draws: 2000, block: 5, horizon: 60 }), 'Bootstrap des séances'); })
      .then(function (r) {
        out.boot = r;
        return out.sweep ? cscvAsync(out.sweep.mat).catch(function () { return null; }) : null;
      }).then(function (pb) {
        var doc = baseDoc(X, 'valider', null, opts), run = out.run, sw = out.sweep;
        doc.costs = run.costs; doc.stats = run.stats; doc.grid = opts.grid;
        if (sw) {
          doc.sweep = { p1: sw.p1, p2: sw.p2, xs: sw.xs, ys: sw.ys, objective: sw.objective, cells: sw.cells.map(function (row) { return row.map(function (c) { return c ? { n: c.n, meanR: c.meanR, sdR: c.sdR, net: c.net, pf: c.pf, sharpe: c.sharpe, maxDD: c.maxDD, winRate: c.winRate, costR: c.costR } : null; }); }), best: sw.best, configs: sw.configs.length, sessions: sw.keys.length, warnings: sw.warnings };
          doc.pbo = sw.configs.length >= 2 ? (pb ? { value: pb.value, error: pb.error || null, n: pb.n || null } : { value: null, error: 'non calculé' }) : 'na';
          try { doc.plateau = stats().plateau(sw.cells, sw.best || undefined); } catch (e) { doc.plateau = null; }
          try { doc.stability = stats().stability(sw.cells); } catch (e) { doc.stability = null; }
          doc.wfa = out.wfa ? { mode: out.wfa.mode, is: out.wfa.is, oos: out.wfa.oos, wfe: out.wfa.wfe, isMeanR: out.wfa.isMeanR, isN: out.wfa.isN, costR: out.wfa.costR, stitched: out.wfa.stitched, eq: LB.downsample(out.wfa.eq || [], 300), windows: (out.wfa.windows || []).slice(0, 80).map(function (w) { return { isFrom: w.isFrom, isTo: w.isTo, oosFrom: w.oosFrom, oosTo: w.oosTo, best: w.best, isMeanR: w.isMeanR, isN: w.isN, oosMeanR: w.oosMeanR, oosN: w.oosN, values: w.values }; }) } : { error: out.wfaErr || 'non calculée' };
        } else { doc.sweep = null; doc.pbo = 'na'; doc.plateau = 'na'; doc.wfa = 'na'; }
        var ss = out.stress; doc.stress = { slips: ss.slips, mults: ss.mults, throughs: ss.throughs, meanR: ss.meanR, n: ss.n, base: ss.base, legs: ss.legs, breakEven: ss.breakEven, beyond: ss.beyond, criterion: ss.criterion, gate: ss.gate, slip: ss.slip, comm: ss.comm };
        var b = out.boot; doc.boot = { meanR: b.meanR, annual: b.annual, fan: { horizon: b.fan.horizon, q: b.fan.q, paths: (b.fan.paths || []).slice(0, 6) }, draws: b.draws, block: b.block, sessions: b.sessions, trades: b.trades, perYear: b.perYear };
        doc.dsr = dsrOf(X, run.stats);
        doc.months = LB.months(run.trades);
        saveResult(doc);
      });
  });
}
function renderValider(body, X) {
  if (!guard(body, X)) return;
  var vs = valState(X), grid = gridOf(vs), doc = findDoc('valider', X);
  var fresh = doc ? doc.variant === variantOf('valider', X, { grid: grid ? { p1: grid.p1, p2: grid.p2, xs: grid.xs, ys: grid.ys } : null, wfa: { is: vs.is, oos: vs.oos, mode: vs.mode } }) : null;
  var sC = sec(body, 'Réglages *balayés*', X.params.length ? plural(X.params.length, 'paramètre déclaré', 'paramètres déclarés') : 'aucun paramètre');
  if (X.params.length) {
    var P = X.spec.params, nameOpt = X.params.map(function (n) { return { v: n, label: (P[n] && P[n].label) || n }; });
    var cellsNote = h('p', { class: 'note' });
    var refreshCells = function () { var g = gridOf(valState(X)); cellsNote.textContent = g ? F.int(g.cells) + ' configuration' + (g.cells > 1 ? 's' : '') + (g.cells > 100 ? ' : au-delà de 100, le calcul dépasse la minute sur un an de données.' : '.') + (g.cells > 400 ? ' Le moteur en accepte 400 au plus.' : '') : ''; };
    var flds = [U.field({ label: 'Premier paramètre', type: 'select', value: vs.p1, options: nameOpt, onChange: function (v) { setVal(X, { p1: v, p2: v === vs.p2 ? '' : vs.p2 }); schedule(); } }),
      U.field({ label: 'Second paramètre', type: 'select', value: vs.p2, options: [{ v: '', label: 'aucun' }].concat(nameOpt.filter(function (o) { return o.v !== vs.p1; })), onChange: function (v) { setVal(X, { p2: v }); schedule(); } })];
    sC.appendChild(U.fields(flds));
    [vs.p1, vs.p2].filter(Boolean).forEach(function (n) {
      var rg = vs.r[n];
      function upd(k) { return function (x) { var all = valState(X).r; all[n] = Object.assign({}, all[n]); all[n][k] = x; setVal(X, { r: all }); refreshCells(); }; }
      sC.appendChild(h('p', { class: 'lb-mono', style: 'margin:12px 0 6px' }, ((P[n] && P[n].label) || n) + ' · $' + n));
      sC.appendChild(U.fields([U.field({ label: 'De', value: rg.min, onChange: upd('min') }), U.field({ label: 'À', value: rg.max, onChange: upd('max') }), U.field({ label: 'Pas', value: rg.step, min: 1e-9, onChange: upd('step') })], 3));
    });
    refreshCells(); sC.appendChild(cellsNote);
    sC.appendChild(h('p', { class: 'lb-mono', style: 'margin:14px 0 6px' }, 'Analyse en avant'));
    sC.appendChild(U.fields([U.field({ label: 'Fenêtre en échantillon', unit: 'séances', value: vs.is, min: 1, onChange: function (x) { setVal(X, { is: Math.round(x) }); } }), U.field({ label: 'Fenêtre hors échantillon', unit: 'séances', value: vs.oos, min: 1, onChange: function (x) { setVal(X, { oos: Math.round(x) }); } })]));
    sC.appendChild(h('div', { style: 'margin-top:10px' }, U.seg({ options: [{ v: 'rolling', label: 'Fenêtre glissante' }, { v: 'anchored', label: 'Fenêtre ancrée' }], value: vs.mode, onChange: function (v) { setVal(X, { mode: v }); schedule(); } })));
  } else sC.appendChild(U.note('Cette stratégie ne déclare aucun paramètre : rien à balayer. PBO, plateau et analyse en avant sont sans objet ; le stress, le bootstrap et le Sharpe déflaté restent calculés.'));
  body.appendChild(launchBar('valider', { label: doc ? 'Relancer la validation' : 'Lancer la validation', onClick: function () { runValider(context()); }, disabled: !X.ready && !S.jobs.valider, doc: doc, fresh: fresh,
    text: sampleLine(X) + (grid ? ' Balayage de ' + plural(grid.cells, 'configuration') + ', analyse en avant, stress des coûts, bootstrap.' : ' Stress des coûts et bootstrap.') }));
  if (!doc) return;
  if (doc.sweep) renderSweep(body, X, doc);
  renderStress(body, doc);
  renderBoot(body, doc);
  renderDsr(body, X, doc);
  var mo = doc.months || [];
  var sM = sec(body, 'Sous-*périodes*', plural(mo.length, 'mois'));
  sM.appendChild(C.bar({ cats: mo.map(function (m) { return monthLabel(m.m); }), series: [{ name: 'R moyen', values: mo.map(function (m) { return fin(m.meanR) ? m.meanR : 0; }), tone: 'violet' }], fmt: function (v) { return F.num(v, 2); }, height: 170 }));
  sM.appendChild(U.table({ cols: [{ k: 'm', label: 'Mois', fmt: monthLabel }, { k: 'n', label: 'Trades', align: 'r', fmt: F.int }, { k: 'meanR', label: 'R moyen', align: 'r', fmt: function (v) { return fR(v); } }, { k: 'net', label: 'Net', align: 'r', fmt: function (v) { return F.usd(v, 0, true); } }], rows: mo, empty: 'Aucun trade.' }));
  sM.appendChild(U.note('Une espérance portée par un ou deux mois n’est pas une espérance : c’est un événement.'));
}
function renderSweep(body, X, doc) {
  var sw = doc.sweep, P = X.spec.params || {}, cells = sw.cells || [], nx = sw.xs.length, ny = (sw.ys || [null]).length;
  var lab = function (n) { return n ? ((P[n] && P[n].label) || n) : ''; }, st = doc.stats || {};
  var s = sec(body, 'Le *balayage*', plural(sw.configs, 'configuration') + ' · espérance par trade');
  var best = sw.best;
  s.appendChild(U.kpis([
    { label: 'Meilleure cellule', value: best ? fR(best.meanR) : '—', hint: best ? Object.keys(best.values || {}).map(function (k) { return k + ' = ' + F.num(best.values[k], 2); }).join(' · ') + ' · ' + plural(best.n, 'trade') : 'aucune configuration jouée', tone: best && best.meanR > 0 ? 'acc' : null },
    { label: 'Plateau', value: doc.plateau === false ? 'aucun' : fin(doc.plateau) ? F.num(doc.plateau, 2) : '—', hint: 'voisins / meilleur · seuil 0,7' },
    { label: 'Stabilité', value: doc.stability && fin(doc.stability.value) ? F.pct(doc.stability.value, 0) : '—', hint: 'cellules au-dessus de zéro' },
    { label: 'PBO', value: doc.pbo === 'na' ? 'sans objet' : doc.pbo && fin(doc.pbo.value) ? F.pct(doc.pbo.value, 0) : '—', hint: doc.pbo && doc.pbo.error ? doc.pbo.error : 'probabilité de surajustement' }
  ], 4));
  if (sw.ys && sw.ys.length > 1 && nx > 1 && T.lib.perf && T.lib.perf.charts) {
    T.lib.perf.injectCss();
    var vals = cells.map(function (row) { return row.map(function (c) { return c && c.n > 0 && fin(c.meanR) ? c.meanR : NaN; }); }), lo = Infinity, hi = -Infinity, am = [0, 0];
    vals.forEach(function (row, j) { row.forEach(function (v, i) { if (!fin(v)) return; if (v < lo) lo = v; if (v > hi) { hi = v; am = [i, j]; } }); });
    if (!fin(lo)) { lo = -1; hi = 0; }
    var dom = function (a) { return a[a.length - 1] > a[0] ? [a[0], a[a.length - 1]] : [a[0] - 0.5, a[0] + 0.5]; };
    var nearest = function (a, v) { var b = 0; for (var i = 1; i < a.length; i++) if (Math.abs(a[i] - v) < Math.abs(a[b] - v)) b = i; return b; };
    var surf = { kind: 'labo', title: 'Espérance par trade', x: { name: lab(sw.p1), dom: dom(sw.xs), fmt: function (v) { return F.num(v, 2); } }, y: { name: lab(sw.p2), dom: dom(sw.ys), fmt: function (v) { return F.num(v, 2); } },
      z: { name: 'espérance', fmt: function (v) { return fin(v) ? F.r(v, 3) : '—'; } }, xs: sw.xs, ys: sw.ys, vals: vals, zmin: lo, zmax: hi > lo ? hi : lo + 1e-9, mid: fin(st.costR) ? -st.costR : 0, midLabel: 'sans avantage', line: [], lineLabel: '',
      fn: function (x, y) { return vals[nearest(sw.ys, y)][nearest(sw.xs, x)]; }, argmax: am };
    s.appendChild(h('div', { style: 'margin:12px 0 10px' }, U.seg({ options: [{ v: '2d', label: 'Carte 2D' }, { v: '3d', label: 'Relief 3D' }], value: S.vue3d ? '3d' : '2d', onChange: function (v) { S.vue3d = v === '3d'; schedule(); } })));
    s.appendChild(S.vue3d ? T.lib.perf.charts.surface3d({ surf: surf }) : T.lib.perf.charts.heatmap2d({ surf: surf }));
  } else if (sw.ys && sw.ys.length > 1) {
    s.appendChild(C.heat({ rows: sw.ys.map(function (y) { return F.num(y, 2); }), cols: sw.xs.map(function (x) { return F.num(x, 2); }), values: cells.map(function (row) { return row.map(function (c) { return c && c.n ? c.meanR : NaN; }); }), fmt: function (v) { return F.num(v, 2); }, diverging: true, corner: lab(sw.p2) + ' \\ ' + lab(sw.p1) }));
  } else {
    var row = cells[0] || [];
    s.appendChild(C.line({ series: [{ name: 'espérance', points: sw.xs.map(function (x, i) { return [x, row[i] && row[i].n ? row[i].meanR : null]; }), tone: 'violet' }], x: { type: 'num', fmt: function (v) { return F.num(v, 2); } }, y: { fmt: function (v) { return F.num(v, 2); } }, hlines: [{ y: fin(st.costR) ? -st.costR : 0, label: 'sans avantage' }], height: 190 }));
  }
  s.appendChild(U.note('Un résultat qui ne vaut qu’en un point de la grille est un artefact : on cherche un plateau, pas un sommet. Le PBO mesure, par validation croisée combinatoire, la probabilité que la meilleure configuration en échantillon tombe sous la médiane hors échantillon.'));
  var w = doc.wfa;
  var sW = sec(body, 'Analyse *en avant*', w && w.windows ? plural(w.windows.length, 'fenêtre') + ' · ' + (w.mode === 'anchored' ? 'ancrée' : 'glissante') : '');
  if (!w || w === 'na' || !w.windows) { sW.appendChild(U.note(w && w.error ? w.error : 'Non calculée.')); return; }
  sW.appendChild(U.kpis([
    { label: 'Efficacité (WFE)', value: fin(w.wfe) ? F.num(w.wfe, 2) : 'indéfinie', hint: 'seuil 0,5', tone: fin(w.wfe) && w.wfe >= 0.5 ? 'acc' : null },
    { label: 'Meilleurs en échantillon', value: fR(w.isMeanR), hint: plural(w.isN || 0, 'trade') },
    { label: 'Hors échantillon cousu', value: fR(w.stitched && w.stitched.meanR), hint: plural((w.stitched && w.stitched.n) || 0, 'trade') },
    { label: 'Net cousu', value: w.stitched && fin(w.stitched.net) ? F.usd(w.stitched.net, 0, true) : '—', hint: 'coût par trade ' + fR(fin(w.costR) ? -w.costR : NaN) }
  ], 4));
  sW.appendChild(C.bar({ cats: w.windows.map(function (x, i) { return 'F' + (i + 1); }), series: [{ name: 'meilleure en échantillon', values: w.windows.map(function (x) { return fin(x.isMeanR) ? x.isMeanR : 0; }), tone: 'mute' }, { name: 'appliquée hors échantillon', values: w.windows.map(function (x) { return fin(x.oosMeanR) ? x.oosMeanR : 0; }), tone: 'violet' }], fmt: function (v) { return F.num(v, 2); }, height: 180 }));
  sW.appendChild(C.line({ series: [{ name: 'hors échantillon cousu', points: (w.eq || []).map(function (p) { return [p[0] && DAYKEY.test(p[0]) ? Date.parse(p[0] + 'T12:00:00Z') : p[0], p[1]]; }), tone: 'violet', area: true }], x: { type: 'time' }, y: { zero: true, fmt: function (v) { return F.usd(v, 0); } }, height: 160 }));
  sW.appendChild(U.note('Chaque fenêtre choisit sa meilleure configuration en échantillon et l’applique telle quelle à la suivante. Le WFE rapporte l’espérance hors échantillon cousue à celle des meilleurs choisis ; il est indéfini quand ces derniers ne dépassent pas le coût.'));
}
function renderStress(body, doc) {
  var ss = doc.stress; if (!ss || ss.omitted) return;
  var s = sec(body, 'Stress des *coûts*', 'glissement × commission');
  var it0 = 0, rows = (ss.slips || []).map(function (sl) { return F.int(sl) + ' tick' + (sl > 1 ? 's' : ''); }), cols = (ss.mults || []).map(function (m) { return 'comm. ×' + F.num(m, m % 1 ? 1 : 0); });
  var vals = (ss.slips || []).map(function (sl, is) { return (ss.mults || []).map(function (m, im) { var v = ss.meanR && ss.meanR[it0] && ss.meanR[it0][im] ? ss.meanR[it0][im][is] : NaN; return fin(v) ? v : NaN; }); });
  s.appendChild(C.heat({ rows: rows, cols: cols, values: vals, fmt: function (v) { return F.num(v, 3); }, diverging: true, corner: 'glissement / jambe' }));
  var be = ss.breakEven;
  s.appendChild(txt(['Glissement d’équilibre : ', h('b', null, be === 'na' ? 'sans objet (aucune jambe ne glisse)' : be === null ? 'au-delà de 4 ticks' : fin(be) ? F.num(be, 2) + ' tick' + (be > 1 ? 's' : '') + ' par jambe' : '—'), '. ', ss.criterion ? 'Critère : espérance ' + fR(ss.criterion.meanR) + (ss.criterion.kind === 'through' ? ' quand les limites exigent un tick de dépassement' : ' à un tick de plus par jambe') + (ss.criterion.pass ? ', positive.' : ', non positive.') : '']));
  s.appendChild(U.note('Rangées : glissement par jambe exécutée au marché ou au stop ; colonnes : commission ×1, ×1,5, ×2 ; dépassement exigé des limites : nul.'));
}
function renderBoot(body, doc) {
  var b = doc.boot; if (!b || b.omitted) return;
  var s = sec(body, 'Bootstrap des *séances*', F.int(b.draws) + ' tirages · bloc moyen ' + F.int(b.block));
  s.appendChild(U.kpis([
    { label: 'Espérance', value: fR(b.meanR && b.meanR.obs), hint: '90 % : ' + fR(b.meanR && b.meanR.lo) + ' à ' + fR(b.meanR && b.meanR.hi) },
    { label: 'Net annuel', value: b.annual && fin(b.annual.obs) ? F.usd(b.annual.obs, 0, true) : '—', hint: b.annual ? '90 % : ' + F.usd(b.annual.lo, 0, true) + ' à ' + F.usd(b.annual.hi, 0, true) : null }
  ]));
  if (b.fan && b.fan.q && b.fan.q.p50 && b.fan.q.p50.length > 1) s.appendChild(C.fan({ q: b.fan.q, paths: b.fan.paths || [], hlines: [{ y: 0, label: 'zéro' }], fmt: function (v) { return F.usd(v, 0); }, xLabel: function (i) { return i === 0 ? 'départ' : i + ' séances'; } }));
  s.appendChild(U.note('Rééchantillonnage stationnaire des séances (Politis et Romano), séances sans trade comprises : la dépendance d’un jour à l’autre est gardée. L’éventail donne 50 % et 90 % des trajectoires sur ' + F.int(b.fan ? b.fan.horizon : 60) + ' séances.'));
}
function renderDsr(body, X, doc) {
  var d = doc.dsr; if (!d) return;
  var s = sec(body, 'Sharpe *déflaté*', 'N compté au registre');
  s.appendChild(U.kpis([
    { label: 'Sharpe par trade', value: fin(d.sr) ? F.num(d.sr, 3) : '—', hint: plural(d.n || 0, 'trade') },
    { label: 'Essais comptés', value: F.int(d.N || 0), hint: X.synth ? 'visite, marche synthétique' : 'dont ' + F.int(d.inherited || 0) + ' hérités' },
    { label: 'Seuil sans avantage', value: fin(d.sr0) ? F.num(d.sr0, 3) : '—', hint: 'maximum attendu de N essais' },
    { label: 'Sharpe déflaté', value: fin(d.dsr) ? F.pct(d.dsr, 1) : '—', hint: 'seuil 95 %', tone: fin(d.dsr) && d.dsr >= 0.95 ? 'acc' : null }
  ], 4));
  s.appendChild(U.note('N compte les configurations distinctes essayées sur l’instrument et la période, toutes stratégies et versions confondues ; la dispersion des essais vient du registre dès dix essais (' + (d.sdSource === 'registre' ? 'c’est le cas' : 'sinon 1/√n') + '). Surcompter coûte peu ; sous-compter rend le test faux.'));
}

/* =====================================================================================================
   12. Onglet Verdict (et ouverture hors échantillon)
   ===================================================================================================== */
function propPrefs() { var p = T.store.get(KEY.prop, {}) || {}; return { minDays: fin(p.minDays) ? Math.max(0, Math.round(p.minDays)) : 0, maxDays: fin(p.maxDays) ? Math.max(1, Math.round(p.maxDays)) : 60 }; }
function anyDoc(op, X) { return findDoc(op, X); }
function myOpening(X) {
  var rows = oosRows(X.synth); if (!X.spec || !X.split.oos.n) return null;
  var mine = rows.filter(function (d) { return d && !d.deleted && d.sid === X.spec.sid && d.version === X.spec.version && d.hash === X.spec.hash && d.instrument === X.inst && overlaps(d.from, d.to, X.split.oos.from, X.split.oos.to); });
  mine.sort(function (a, b) { return (a.at || 0) - (b.at || 0); });
  return mine[0] || null;
}
function oosState(X) {
  if (X.status === 'brouillon') return { sealed: false };
  if (X.status === 'alteree') return { sealed: true, altered: true };
  var op = myOpening(X); if (!op) return null;
  var o = LB.oosOpening(oosRows(X.synth), { root: X.spec.root || X.spec.sid, instrument: X.inst, from: op.from, to: op.to, self: op.id, before: op.at });
  var rd = findDoc('oos', X, X.split.oos), p = rd && rd.oos && rd.oos.random ? rd.oos.random.p : null;
  return { sealed: true, altered: false, first: o.first, p: p, prior: o.prior ? { version: o.prior.version, at: o.prior.at } : null };
}
function verdictOpts(X) {
  var vdoc = anyDoc('valider', X), acc = account();
  return { prop: propPrefs(), acc: acc ? { size: acc.size, target: acc.target, maxLoss: acc.maxLoss, dd: acc.dd, lockAt: acc.lockAt, dailyLimit: acc.dailyLimit, dailyMode: acc.dailyMode, consistency: acc.consistency } : null, grid: vdoc && vdoc.grid && vdoc.sweep ? vdoc.grid : null };
}
function runVerdict(X) {
  ensureCut(X);
  var fl = floorCosts(X), ov = { commissionRT: fl.commissionRT, slipTicks: fl.slipTicks }, a = baseA(X, X.split.is, { override: ov }), out = {};
  var vdoc = anyDoc('valider', X), opts = verdictOpts(X), grid = opts.grid, pp = opts.prop, N = Math.max(1, (X.trials && X.trials.N) || 0);
  startJob('verdict', 'Verdict aux coûts planchers', 5, function (job) {
    return job.call('run', a, 'Exécution aux coûts planchers').then(function (r) {
      out.run = r; return job.call('random', Object.assign({}, a, { draws: 200, N: N }), 'Entrées au hasard (200 tirages)');
    }).then(function (r) {
      out.random = r;
      if (grid) return job.call('permuteGrid', Object.assign({}, a, { p1: grid.p1, p2: grid.p2 || undefined, xs: grid.xs, ys: grid.ys || undefined, objective: 'meanR', minTrades: 1, draws: 100, minDraws: 20, budgetMs: 60000 }), 'Grille rejouée sur prix permutés');
      return job.call('permute', Object.assign({}, a, { draws: 100, minDraws: 50, budgetMs: 60000, N: N }), 'Prix permutés');
    }).then(function (r) { out.permute = r; return job.call('stress', a, 'Stress des coûts'); })
      .then(function (r) {
        out.stress = r;
        if (!opts.acc) return null;
        return job.call('boot', Object.assign({}, a, { draws: 2000, propDraws: 1000, block: 5, horizon: 60, account: opts.acc, minDays: pp.minDays, maxDays: pp.maxDays }), 'Bootstrap et passage du compte');
      }).then(function (b) {
        out.boot = b;
        var st = out.run.stats, has = X.params.length > 0, dsr = dsrOf(X, st);
        var r = { n: st.n, meanR: st.meanR, costR: st.costR, random: out.random ? out.random.p : null, permute: out.permute ? out.permute.p : null, dsr: dsr.dsr, N: dsr.N,
          pbo: !has ? 'na' : vdoc ? (vdoc.pbo === 'na' ? 'na' : vdoc.pbo && fin(vdoc.pbo.value) ? vdoc.pbo.value : null) : null,
          plateau: !has ? 'na' : vdoc ? vdoc.plateau : null,
          costs: out.stress ? out.stress.gate : null,
          wfa: !has ? 'na' : vdoc && vdoc.wfa && vdoc.wfa !== 'na' && vdoc.wfa.windows ? { wfe: vdoc.wfa.wfe } : vdoc && vdoc.wfa === 'na' ? 'na' : null,
          oos: oosState(X), blocked: X.lineage && X.lineage.blocked ? X.lineage.text : null };
        var doc = baseDoc(X, 'verdict', null, opts);
        doc.costs = Object.assign({ raised: fl.raised }, out.run.costs); doc.stats = st; doc.nulls = { random: nullLite(out.random), permute: nullLite(out.permute) };
        doc.stress = { gate: out.stress.gate, criterion: out.stress.criterion, breakEven: out.stress.breakEven, base: out.stress.base };
        doc.dsr = dsr; doc.inputs = r; doc.verdict = stats().verdict(r);
        doc.boot = out.boot ? { meanR: out.boot.meanR, annual: out.boot.annual, sessions: out.boot.sessions } : null;
        doc.prop = out.boot && out.boot.prop ? out.boot.prop : null; doc.account = opts.acc; doc.grid = grid;
        saveResult(doc);
      });
  });
}
function verdictNow(X, doc) {
  /* Le verdict enregistré, recalculé avec l’état courant du hors échantillon et de la lignée (sans relancer). */
  if (!doc || !doc.inputs) return doc ? doc.verdict : null;
  var r = Object.assign({}, doc.inputs, { oos: oosState(X), blocked: X.lineage && X.lineage.blocked ? X.lineage.text : null });
  try { return stats().verdict(r); } catch (e) { return doc.verdict; }
}
function renderVerdict(body, X) {
  if (!guard(body, X)) return;
  var doc = findDoc('verdict', X), fresh = doc ? doc.variant === variantOf('verdict', X, verdictOpts(X)) : null;
  var fl = floorCosts(X);
  body.appendChild(launchBar('verdict', { label: doc ? 'Recalculer le verdict' : 'Calculer le verdict', onClick: function () { runVerdict(context()); }, disabled: !X.ready && !S.jobs.verdict, doc: doc, fresh: fresh,
    text: 'Aux coûts planchers : commission ' + F.usd(fl.commissionRT, 2) + ' aller-retour, glissement ' + F.num(fl.slipTicks, 0) + ' tick par jambe' + (fl.raised ? ' (relevés depuis la stratégie)' : '') + '. Exécution, hasard, permutation, stress, Sharpe déflaté et passage du compte.' }));
  if (doc) {
    var v = verdictNow(X, doc) || doc.verdict, LV = stats().LEVELS;
    var sL = sec(body, 'Le *verdict*', LV[v.level] || v.level);
    sL.appendChild(h('div', { class: 'lb-lvl' }, h('em', null, LV[v.level] || v.level), U.pill(v.level === 'prete-simulateur' ? 'prête' : v.level === 'rejetee' ? 'rejetée' : 'à approfondir', v.level === 'prete-simulateur' ? 'acc' : v.level === 'rejetee' ? 'no' : null)));
    sL.appendChild(txt(v.text));
    if (!doc.grid && X.params.length) sL.appendChild(U.note('Aucun balayage enregistré pour cette version : PBO, plateau et analyse en avant restent à calculer dans Valider.', true));
    sL.appendChild(h('div', { class: 'lb-items', style: 'margin-top:12px' }, v.items.map(function (it) {
      var p = it.pass === true ? 'ok' : it.pass === false ? 'ko' : it.pass === 'na' ? 'na' : 'nul';
      return h('div', { class: 'lb-it', 'data-p': p }, h('span', { class: 'ic', 'aria-hidden': 'true' }, p === 'ok' ? '✓' : p === 'ko' ? '✗' : p === 'na' ? '–' : '?'), h('b', null, it.label), h('span', { class: 'v' }, it.value, h('span', { class: 'nd' }, it.need)), h('span', { class: 'w' }, it.why));
    })));
    sL.appendChild(U.note('Les seuils sont des constantes du code, chacune justifiée ; aucun n’est tiré de ce qu’il évalue. « Prête » veut dire prête pour le simulateur : ce n’est pas une promesse de gain.'));
    renderProp(body, X, doc);
  }
  renderOos(body, X, doc);
}
function renderProp(body, X, doc) {
  var s = sec(body, 'Passage d’un *compte prop*', 'bootstrap des séances');
  var acc = doc.account || null, pp = propPrefs();
  if (!acc) { s.appendChild(U.note('Le desk Risque n’est pas chargé ou aucun compte n’y est réglé : pas de simulation de passage.')); return; }
  s.appendChild(kv([['compte', F.usd(acc.size, 0)], ['objectif', F.usd(acc.target, 0, true)], ['perte maximale', F.usd(acc.maxLoss, 0) + ' · ' + ({ eod: 'fin de journée', intraday: 'intrajournalière', 'static': 'statique' }[acc.dd] || acc.dd)], ['limite du jour', fin(acc.dailyLimit) ? F.usd(acc.dailyLimit, 0) + ' · ' + (acc.dailyMode === 'fail' ? 'échec' : 'pause') : 'aucune'], ['constance', fin(acc.consistency) ? F.num(acc.consistency, 0) + ' %' : 'aucune']]));
  s.appendChild(h('div', { style: 'margin-top:10px' }, U.fields([U.field({ label: 'Jours de trading minimum', value: pp.minDays, min: 0, onChange: function (x) { T.store.set(KEY.prop, Object.assign(propPrefs(), { minDays: Math.round(x) })); } }), U.field({ label: 'Séances maximum', value: pp.maxDays, min: 1, onChange: function (x) { T.store.set(KEY.prop, Object.assign(propPrefs(), { maxDays: Math.round(x) })); } })])));
  var p = doc.prop;
  if (p) {
    s.appendChild(U.kpis([
      { label: 'Réussite', value: F.pct(p.pPass, 1), hint: fin(p.medPass) ? 'en ' + F.int(p.medPass) + ' séances (médiane)' : null, tone: p.pPass > p.pFail ? 'acc' : null },
      { label: 'Échec', value: F.pct(p.pFail, 1), hint: fin(p.medFail) ? 'en ' + F.int(p.medFail) + ' séances (médiane)' : null, tone: p.pFail > 0.5 ? 'neg' : null },
      { label: 'Sans conclusion', value: F.pct(p.pNone, 1), hint: 'après ' + F.int(p.maxDays) + ' séances' },
      { label: 'Tirages', value: F.int(p.n), hint: 'minimum ' + F.int(p.minDays) + ' jours' }
    ], 4));
    s.appendChild(U.note('Règles du desk Risque appliquées séance par séance (plancher qui suit le plus haut, limite du jour, constance) sur des séances rééchantillonnées aux coûts planchers. Les règles d’une prop firm changent : vérifiez-les dans Risque.'));
  } else s.appendChild(U.note('Pas encore calculé avec ces réglages : recalculez le verdict.'));
}
function renderOos(body, X, vdoc) {
  var s = sec(body, 'Le hors *échantillon*', X.cutDemo ? 'démonstration sur la marche' : X.inst);
  var op = myOpening(X), can = LB.canOpenOos({ status: X.status, oosN: X.split.oos.n, opened: !!op });
  s.appendChild(kv([['coupure', fmtKey(X.cut) + (X.cutDemo ? ' (démonstration)' : X.cutFixed ? ' (fixée)' : ' (proposée)')], ['séances hors échantillon', F.int(X.split.oos.n) + (X.split.oos.n ? ' · ' + fmtKey(X.split.oos.from) + ' → ' + fmtKey(X.split.oos.to) : '')]]));
  if (X.cutDemo) s.appendChild(U.note('Sur la marche synthétique, la coupure est une démonstration : l’ouverture est gardée le temps de la visite et n’entre dans aucun registre.'));
  var rows = oosRows(X.synth), lin = X.spec ? LB.oosOpening(rows, { root: X.spec.root || X.spec.sid, instrument: X.inst, from: X.split.oos.from, to: X.split.oos.to }) : null;
  if (lin && X.split.oos.n) s.appendChild(txt(['Ouvertures de cette période : ', h('b', null, F.int(lin.lineage)), ' pour la lignée, ', h('b', null, F.int(lin.total)), ' toutes lignées confondues.' + (lin.prior ? ' Première ouverture de la lignée : version ' + lin.prior.version + ', le ' + F.dateLong(lin.prior.at) + '.' : '')]));
  var ref = vdoc || anyDoc('tester', X), st = ref && ref.stats;
  if (st && X.split.oos.n) {
    var plan = stats().oosPlan({ nIS: st.n, sessionsIS: X.split.is.n, sessionsOOS: X.split.oos.n, meanR: st.meanR, costR: st.costR, sdR: st.sdR });
    s.appendChild(U.callout([txt(['Au rythme de l’échantillon (', F.num(plan.rate, 2), ' trade par séance), on attend ', h('b', null, F.int(Math.round(plan.expected || 0))), ' trades hors échantillon. ',
      plan.required === Infinity ? 'L’espérance en échantillon ne dépasse pas le coût : aucun nombre de trades ne la séparerait de l’absence d’avantage.' : ['Il en faut ', h('b', null, F.int(plan.required)), ' pour séparer ', fR(st.meanR), ' de ', fR(-st.costR), ' (5 % unilatéral, puissance 80 %). ', plan.enough ? 'L’échantillon attendu suffit.' : 'Il en manque : le test ne pourra pas trancher, et une seconde ouverture ne comptera plus.']])]));
  } else if (X.split.oos.n) s.appendChild(U.note('Lancez d’abord le test ou le verdict : le nombre de trades attendus se calcule sur l’échantillon.'));
  if (op) {
    var rd = findDoc('oos', X, X.split.oos), first = LB.oosOpening(rows, { root: op.root, instrument: op.instrument, from: op.from, to: op.to, self: op.id, before: op.at }).first;
    s.appendChild(txt(['Ouvert le ', h('b', null, F.dateLong(op.at) + ' à ' + F.time(op.at)), ' par cette version' + (first ? ' : première ouverture de la lignée.' : ' : la lignée l’avait déjà vu, le critère tombe.')]));
    s.appendChild(launchBar('oos', { label: rd ? 'Rejouer le test hors échantillon' : 'Lancer le test hors échantillon', onClick: function () { runOos(context(), null); }, disabled: !X.ready && !S.jobs.oos, doc: rd, text: 'Entrées au hasard rejouées sur les seules séances hors échantillon, aux coûts planchers. Rejouer n’est pas rouvrir : l’ouverture est déjà comptée.' }));
    if (rd && rd.oos) {
      var r = rd.oos.random || {}, os = rd.oos.stats || {};
      s.appendChild(U.kpis([{ label: 'Trades', value: F.int(os.n || 0), hint: plural(X.split.oos.n, 'séance') }, { label: 'Espérance', value: fR(os.meanR), hint: 'sans avantage ' + fR(fin(os.costR) ? -os.costR : NaN) }, { label: 'p (hasard)', value: fP(r.p), hint: 'p minimal ' + fP(r.pmin), tone: fin(r.p) && r.p < 0.05 ? 'acc' : null }, { label: 'Net', value: fin(os.net) ? F.usd(os.net, 0, true) : '—' }], 4));
      if (r.means) s.appendChild(nullHist(r, { zero: fin(os.costR) ? -os.costR : NaN, zeroLabel: '−c/L' }));
    }
    return;
  }
  if (!can.ok) { s.appendChild(U.note(can.why, X.status === 'alteree')); return; }
  if (S.confirmOos === X.vid) {
    s.appendChild(U.callout([h('b', null, 'Une seule ouverture compte.'), h('p', null, 'L’ouverture est enregistrée pour la lignée ' + (X.spec.root || X.spec.sid) + ' et ne se décompte jamais. Toute ouverture suivante de la même période fera tomber le critère.'), h('div', { class: 'lb-acts' }, U.button({ label: 'Confirmer l’ouverture', kind: 'pri', small: true, onClick: function () { S.confirmOos = null; openOos(context()); } }), U.button({ label: 'Annuler', kind: 'ghost', small: true, onClick: function () { S.confirmOos = null; schedule(); } }))]));
  } else s.appendChild(h('div', { class: 'lb-acts', style: 'margin-top:10px' }, U.button({ label: 'Ouvrir le hors échantillon', kind: 'acc', onClick: function () { S.confirmOos = X.vid; schedule(); } })));
}
function openOos(X) {
  var can = LB.canOpenOos({ status: X.status, oosN: X.split.oos.n, opened: !!myOpening(X) });
  if (!can.ok) { T.toast(can.why); schedule(); return; }
  var now = Date.now(), a = ''; for (var i = 0; i < 6; i++) a += Math.floor(Math.random() * 36).toString(36);
  var d = { id: 'o' + now.toString(36) + a, hash: X.spec.hash, sid: X.spec.sid, root: X.spec.root || X.spec.sid, version: X.spec.version, instrument: X.inst, from: X.split.oos.from, to: X.split.oos.to, at: now, u: now };
  var before = LB.oosOpening(oosRows(X.synth), { root: d.root, instrument: d.instrument, from: d.from, to: d.to });
  if (X.synth) S.mem.oos.push(d); else coll('oos').set(d.id, d);
  runOos(X, { opening: d, first: before.first, prior: before.prior ? { version: before.prior.version, at: before.prior.at } : null, total: before.total + 1 });
}
function runOos(X, info) {
  var fl = floorCosts(X), ov = { commissionRT: fl.commissionRT, slipTicks: fl.slipTicks }, sel = X.split.oos;
  var a = baseA(X, sel, { override: ov, oos: true }), out = {};
  var op = (info && info.opening) || myOpening(X);
  startJob('oos', 'Test hors échantillon', 2, function (job) {
    return job.call('run', a, 'Exécution sur les séances hors échantillon').then(function (r) { out.run = r; return job.call('random', Object.assign({}, a, { draws: 200 }), 'Entrées au hasard sur le hors échantillon'); })
      .then(function (r) {
        var doc = baseDoc(X, 'oos', sel), rows = oosRows(X.synth);
        var o = info || (op ? (function () { var b = LB.oosOpening(rows, { root: op.root, instrument: op.instrument, from: op.from, to: op.to, self: op.id, before: op.at }); return { opening: op, first: b.first, prior: b.prior ? { version: b.prior.version, at: b.prior.at } : null, total: LB.oosOpening(rows, { root: op.root, instrument: op.instrument, from: op.from, to: op.to }).total }; })() : {});
        doc.costs = out.run.costs; doc.stats = out.run.stats;
        doc.oos = { opening: o.opening || null, first: o.first, prior: o.prior || null, total: o.total, random: nullLite(r), stats: out.run.stats, sel: { from: sel.from, to: sel.to } };
        var tr = LB.tradeRows(out.run.trades, MAX_TRADES); doc.trades = tr.rows; if (tr.omitted) doc.tradesOmitted = tr.omitted;
        saveResult(doc);
      });
  });
}

/* =====================================================================================================
   13. Onglet Suivre
   ===================================================================================================== */
function renderSuivre(body, X) {
  if (!hasLibs()) { guard(body, X); return; }
  if (!X.spec) { guard(body, X); return; }
  var all = T.journal.list().filter(function (r) { return r.strat === X.spec.sid; }), sealed = X.status === 'scellee';
  var s1 = sec(body, 'Saisie *rapide*', X.spec.name + ' · v' + X.spec.version);
  var pv = X.settings.pointValue, cm = X.settings.commissionRT, q = S.quick, prev = h('p', { class: 'lb-txt', role: 'status' });
  function upd() { var r = LB.quickTrade(Object.assign({}, q, { pointValue: pv, commissionRT: cm })); T.clear(prev); if (!fin(q.entry) || !fin(q.exit)) prev.appendChild(document.createTextNode('Entrée et sortie donnent le P&L ; le stop donne le R.')); else if (!r.ok) prev.appendChild(document.createTextNode(r.why)); else { prev.appendChild(document.createTextNode('P&L ')); prev.appendChild(h('b', null, F.usd(r.pnl, 2, true))); prev.appendChild(document.createTextNode(' · ' + (r.r === null ? 'R inconnu sans stop' : F.r(r.r, 2)) + ' · sortie : ' + r.fin + '.')); } }
  function set(k) { return function (x) { q[k] = x; upd(); }; }
  s1.appendChild(h('div', { style: 'margin-bottom:10px' }, U.seg({ options: [{ v: 'long', label: 'Achat' }, { v: 'short', label: 'Vente' }], value: q.side, onChange: function (v) { q.side = v; schedule(); } })));
  s1.appendChild(U.fields([U.field({ label: 'Entrée', value: q.entry, allowEmpty: true, onChange: set('entry') }), U.field({ label: 'Stop', value: q.stop, allowEmpty: true, onChange: set('stop') }), U.field({ label: 'Objectif', value: q.target, allowEmpty: true, onChange: set('target') }), U.field({ label: 'Sortie', value: q.exit, allowEmpty: true, onChange: set('exit') }), U.field({ label: 'Quantité', value: q.qty, unit: 'contrats', min: 1, onChange: set('qty') })], 3));
  upd(); s1.appendChild(prev);
  s1.appendChild(h('div', { class: 'lb-acts', style: 'margin-top:10px' }, U.button({ label: 'Écrire dans le journal', kind: 'pri', small: true, onClick: function () {
    var r = LB.quickTrade(Object.assign({}, q, { pointValue: pv, commissionRT: cm }));
    if (!r.ok) { T.toast(r.why); return; }
    var now = Date.now();
    T.journal.add({ at: now, kind: 'pris', side: q.side, setup: (X.spec.name || 'Stratégie') + ' · v' + X.spec.version, entry: q.entry, stop: fin(q.stop) ? q.stop : null, target: fin(q.target) ? q.target : null, exit: q.exit, qty: q.qty, instrument: X.spec.instrument || X.inst || 'MNQ', status: 'clos', closedAt: now, pnl: r.pnl, r: r.r, fin: r.fin, plan: true, strat: X.spec.sid, stratV: X.spec.version });
    S.quick = { side: q.side, entry: null, stop: null, target: null, exit: null, qty: q.qty };
    T.toast('Trade écrit dans le journal'); schedule();
  } }), h('span', { class: 'lb-mono' }, 'Écrit avec strat ' + X.spec.sid + ' et version ' + X.spec.version + '.')));
  if (!sealed) s1.appendChild(U.note('Cette version n’est pas scellée : ses trades sont gardés, mais le test séquentiel ne lit que ceux d’une version scellée, postérieurs à son scellement.', true));

  var follow = sealed ? stats().followTrades(T.journal.list(), { sid: X.spec.sid, version: X.spec.version, sealedAt: X.spec.sealedAt }) : [];
  var rs = follow.map(function (t) { return t.r; });
  var ref = X.ds && X.split && X.split.is.n ? (findDoc('verdict', X) || findDoc('tester', X)) : null, vdoc = X.ds && X.split && X.split.is.n ? findDoc('valider', X) : null;
  var st = ref && ref.stats, bootLo = ref && ref.boot && ref.boot.meanR ? ref.boot.meanR.lo : (vdoc && vdoc.boot && vdoc.boot.meanR ? vdoc.boot.meanR.lo : null);
  var s2 = sec(body, 'Test *séquentiel*', plural(rs.length, 'trade de suivi', 'trades de suivi'));
  if (!st) s2.appendChild(U.note('Lancez le test ou le verdict sur le jeu courant : H0 et H1 se posent sur l’échantillon.'));
  else {
    var plan = stats().sprtPlan(X.spec, st, bootLo), pr = stats().sprt(rs, plan);
    var dec = { 'avantage-confirme': 'Avantage confirmé', 'aucun-avantage': 'Aucun avantage', continuer: 'Continuer', na: 'Sans objet' }[pr.decision] || pr.decision;
    s2.appendChild(U.kpis([{ label: 'Décision', value: dec, tone: pr.decision === 'avantage-confirme' ? 'acc' : pr.decision === 'aucun-avantage' ? 'neg' : null }, { label: 'Forme', value: pr.form === 'binomial' ? 'binomiale exacte' : 'normale', hint: pr.form === 'binomial' ? 'p0 ' + F.pct(pr.p0, 1) + ' · p1 ' + F.pct(pr.p1, 1) : 'H0 ' + fR(pr.mu0) + ' · H1 ' + fR(pr.mu1) }, { label: 'Log-vraisemblance', value: F.num(pr.llr, 2), hint: 'bornes ' + F.num(pr.lower, 2) + ' et ' + F.num(pr.upper, 2) }, { label: 'Trades lus', value: F.int(pr.n), hint: 'α 5 % · β 20 %' }], 4));
    if (pr.decision === 'na') s2.appendChild(U.note(pr.why || 'Le test n’a pas d’objet.', true));
    else s2.appendChild(C.line({ series: [{ name: 'log-vraisemblance', points: [[0, 0]].concat(pr.path.map(function (v, i) { return [i + 1, v]; })), tone: 'violet' }], x: { type: 'num', fmt: function (v) { return F.int(v); } }, y: { fmt: function (v) { return F.num(v, 1); } }, hlines: [{ y: pr.upper, label: 'avantage confirmé', tone: 'fg' }, { y: pr.lower, label: 'aucun avantage', tone: 'mute' }], height: 190 }));
    s2.appendChild(U.note('H0 : aucun avantage (' + (pr.form === 'binomial' ? 'taux d’équilibre' : 'espérance −costR') + '). H1 : ' + (pr.form === 'binomial' ? 'le taux de réussite en échantillon' : 'la borne basse à 90 % du bootstrap en échantillon, jamais la moyenne brute') + '. Le test s’arrête au premier franchissement d’une borne.'));

    var sg = fin(st.sdR) && st.sdR > 0 ? st.sdR : 1, cu = stats().cusum(rs, st.meanR, 0.5 * sg, 4 * sg, sg);
    var s3 = sec(body, 'Alarme d’*usure*', 'CUSUM sous l’espérance en échantillon');
    s3.appendChild(C.line({ series: [{ name: 'chute cumulée', points: cu.neg.map(function (v, i) { return [i + 1, v]; }), tone: 'violet' }, { name: 'hausse cumulée', points: cu.pos.map(function (v, i) { return [i + 1, v]; }), tone: 'mute', dash: true }], x: { type: 'num', fmt: function (v) { return F.int(v); } }, y: { zero: true, fmt: function (v) { return F.num(v, 1); } }, hlines: [{ y: cu.h, label: 'seuil', tone: 'fg' }], height: 170 }));
    s3.appendChild(txt([cu.alarm >= 0 ? h('b', null, 'Alarme au trade ' + (cu.alarm + 1) + '. ') : 'Pas d’alarme. ', 'Référence k = ' + F.num(cu.k, 2) + ' R, seuil h = ' + F.num(cu.h, 2) + ' R ; sans changement, une fausse alarme arrive en moyenne tous les ' + (fin(cu.arl0) ? F.int(cu.arl0) : '—') + ' trades.']));

    var env = ref.envelope || (findDoc('tester', X) || {}).envelope, eg = LB.envelopeGap(rs, { pess: env && env.pess ? env.pess.stats.meanR : NaN, opt: env && env.opt ? env.opt.stats.meanR : NaN, costR: st.costR });
    var s4 = sec(body, 'Écart à l’*enveloppe*', 'R cumulé');
    s4.appendChild(C.line({ series: [{ name: 'suivi réel', points: eg.real, tone: 'violet' }, { name: 'pessimiste', points: eg.pess, tone: 'mute', dash: true }, { name: 'optimiste', points: eg.opt, tone: 'fg', dash: true }, { name: 'sans avantage', points: eg.nul, tone: 'mute' }], x: { type: 'num', fmt: function (v) { return F.int(v); } }, y: { zero: true, fmt: function (v) { return F.num(v, 1); } }, height: 190 }));
    s4.appendChild(U.note(eg.where === 'dessous' ? 'Le suivi passe sous l’enveloppe du backtest : l’exécution réelle coûte plus que prévu, ou l’avantage s’use.' : eg.where === 'dessus' ? 'Le suivi passe au-dessus de l’enveloppe : peu de trades, ou une exécution meilleure que les conventions du moteur.' : eg.where === 'dedans' ? 'Le suivi reste dans l’enveloppe du backtest.' : 'Les droites prolongent l’espérance par trade du backtest, pessimiste et optimiste, et le coût seul.'));
  }
  var s5 = sec(body, 'Trades de la *stratégie*', plural(all.length, 'entrée') + ' au journal');
  s5.appendChild(U.table({ cols: [{ k: 'at', label: 'Date', fmt: function (v) { return F.date(v) + ' ' + F.time(v); } }, { k: 'stratV', label: 'Version', fmt: function (v) { return 'v' + v; } }, { k: 'side', label: 'Sens', fmt: function (v) { return v === 'short' ? 'vente' : 'achat'; } }, { k: 'r', label: 'R', align: 'r', fmt: function (v) { return fR(v, 2); } }, { k: 'pnl', label: 'Net', align: 'r', fmt: function (v) { return fin(v) ? F.usd(v, 2, true) : '—'; } }], rows: all.slice().reverse().slice(0, 200), rowClass: function (r) { return r.pnl < 0 ? 'neg' : null; }, empty: { title: 'Aucun trade ne porte cette stratégie', text: 'La saisie rapide ci-dessus écrit au journal avec la stratégie et sa version. Claude peut aussi importer l’export de votre plateforme.' } }));
}

/* =====================================================================================================
   14. Onglet Concevoir : l’éditeur, ou à défaut la liste et les gabarits
   ===================================================================================================== */
function blankSpec() {
  var sid = LB.newSid(), now = Date.now();
  return stats().normalize({ id: LB.versionId(sid, 1), sid: sid, root: sid, version: 1, status: 'brouillon', hash: null, sealedAt: null, createdAt: now, u: now, name: 'Nouvelle stratégie', hypothesis: '', side: 'long',
    long: { setup: [], trigger: { cross: 'up', a: { f: 'close' }, b: { f: 'vwap' } }, entry: { type: 'market' }, stop: { type: 'pts', value: 10 }, target: { type: 'r', value: 2 } } }).spec;
}
function allLists() { var c = coll('strategies').list(); return [c, coll('essais').list(), coll('oos').list(), S.mem.essais, S.mem.oos]; }
function saveSpec(spec) {
  try {
    var all = versions(), stored = spec && spec.id ? coll('strategies').get(spec.id) : null;
    var p = LB.planSave(spec, { stored: stored, lists: allLists(), now: Date.now() });
    if (p.doc) coll('strategies').set(p.id, p.doc);
    T.store.set(KEY.sel, p.id); void all;
    if (p.created && stored && stored.status === 'scellee') T.toast('Version scellée intacte : modification enregistrée en version ' + p.doc.version);
    paintHead();
    return Promise.resolve(p.id);
  } catch (e) { return Promise.reject(e); }
}
function sealSpec(spec) {
  try {
    var stored = spec && spec.id ? coll('strategies').get(spec.id) : null, inst = (spec && spec.instrument) || 'MNQ', info = oosInfo(inst);
    if (!info.fixed && S.ds && !isSynth(S.ds) && (S.ds.meta.instrument || 'MNQ') === inst && info.proposal) {
      var r0 = LB.canSetOos(cfgDoc(inst), coll('essais').list(), inst, info.proposal);
      if (r0.ok) { coll('config').set('oos-' + inst, { oosFrom: info.proposal, instrument: inst, at: Date.now(), auto: true }); info = oosInfo(inst); }
    }
    var p = LB.planSeal(spec, { stored: stored, commissionRT: T.settings.get().commissionRT, oosFrom: info.fixed ? info.oosFrom : null, now: Date.now() });
    if (!p.ok) return Promise.resolve({ ok: false, why: p.why, hash: null });
    if (p.doc) { coll('strategies').set(p.doc.id, p.doc); T.store.set(KEY.sel, p.doc.id); }
    paintHead();
    return Promise.resolve({ ok: true, why: null, hash: p.hash });
  } catch (e) { return Promise.resolve({ ok: false, why: msg(e), hash: null }); }
}
function newVersionOf(spec) { try { var p = LB.planNewVersion(spec, { lists: allLists() }); coll('strategies').set(p.id, p.doc); T.store.set(KEY.sel, p.id); paintHead(); return Promise.resolve(p.id); } catch (e) { return Promise.reject(e); } }
function duplicateOf(spec) { try { var p = LB.planDuplicate(spec, {}); coll('strategies').set(p.id, p.doc); T.store.set(KEY.sel, p.id); paintHead(); return Promise.resolve(p.id); } catch (e) { return Promise.reject(e); } }
function removeVersion(id) {
  return Promise.resolve(coll('strategies').remove(id)).then(function () { if (T.store.get(KEY.sel, null) === id) { var n = versions()[0]; T.store.set(KEY.sel, n ? n.id : null); } paintHead(); return true; });
}
/* Aperçu (Concevoir) : la dernière séance de l’échantillon portant un signal, avec les séries de la règle. */
function preview(spec) {
  if (!hasLibs()) return Promise.resolve({ error: 'Le moteur du Labo n’est pas chargé.' });
  if (!S.ds) return Promise.resolve({ error: S.loading || S.dsErr || 'Aucun jeu chargé.' });
  var n = stats().normalize(spec); if (!n.spec) return Promise.resolve({ error: n.errors[0] || 'Stratégie illisible.' });
  if (n.errors.length) return Promise.resolve({ error: n.errors[0] });
  var X = context(); if (!X.split || !X.split.is.n) return Promise.resolve({ error: 'Aucune séance en échantillon.' });
  X.spec = n.spec; X.norm = n;
  var a = baseA(X, X.split.is), ex = exec(), res;
  try { res = stats().resolve(n.spec, {}); } catch (e) { res = n.spec; }
  var ops = LB.operandsOf(res.long);
  return ex.call('run', a).promise.then(function (r) {
    var ss = (r.sessions || []).filter(function (x) { return x.sig > 0; });
    if (!ss.length) return { error: 'Aucun signal en échantillon : rien à montrer. Assouplissez le contexte ou le déclencheur.' };
    var key = ss[ss.length - 1].key;
    return ex.call('features', Object.assign({}, a, { operands: ops, sel: { from: key, to: key } })).promise.then(function (f) {
      var t = Array.prototype.slice.call(f.t), pick = function (x) { return x ? Array.prototype.slice.call(x) : null; }, sigs = [];
      if (f.sig) ['L', 'S'].forEach(function (k) { var arr = f.sig[k]; if (!arr) return; for (var i = 0; i < arr.length; i++) if (arr[i] === 1) sigs.push({ t: t[i], side: k === 'L' ? 'long' : 'short' }); });
      return { key: key, series: ops.map(function (o, i) { var cls = null; try { cls = stats().classOf(o); } catch (e) {} return { name: opName(o), cls: cls, points: t.map(function (x, j) { var v = f.series[i] ? f.series[i][j] : null; return [x, v == null || !fin(v) ? null : v]; }) }; }),
        bars: { t: t, o: pick(f.o), h: pick(f.h), l: pick(f.l), c: pick(f.c) }, signals: sigs, warnings: f.warnings || [] };
    });
  }).catch(function (e) { return { error: msg(e) }; });
}
function opName(o) {
  try { var R = stats().reader({}); if (R && typeof R.op === 'function') { var s = R.op(o); if (s) return String(s); } } catch (e) {}
  if (o && o.f) return o.f + (o.n ? ' ' + o.n : '') + (fin(o.k) && o.k ? (o.k > 0 ? ' +' : ' ') + o.k : '');
  return 'opérande';
}
function builderApi(ctx) {
  return {
    versions: function () { return versions(); },
    current: function () { return specOf(currentDoc()); },
    select: function (id) { selectVersion(id); },
    save: saveSpec, seal: sealSpec, newVersion: newVersionOf, duplicate: duplicateOf, remove: removeVersion,
    fromTemplate: function (key) { return stats().fromTemplate(key, LB.newSid()); },
    blank: blankSpec,
    oos: function (inst) { var i = oosInfo(inst || 'MNQ'); return { oosFrom: i.oosFrom, fixed: i.fixed, proposal: i.proposal }; },
    setOosFrom: setOosFrom,
    dataset: function () { return S.ds ? { meta: S.ds.meta, ready: S.exReady === fpOf(S.ds) || (!!S.ex && S.ex.mode === 'local' && S.exFp === fpOf(S.ds)) } : null; },
    preview: preview,
    toast: function (m) { T.toast(m); },
    go: function (desk, tab) { if (desk === 'labo' && tab) ctx.setTab(tab); else T.nav.go(desk, tab); }
  };
}
function renderConcevoir(body, ctx, X) {
  var B = T.lib.laboBuilder;
  if (B && typeof B.render === 'function' && hasLibs()) {
    try { var cl = B.render(body, ctx, builderApi(ctx)); S.builderCleanup = typeof cl === 'function' ? cl : null; return; }
    catch (e) { body.appendChild(U.note('L’éditeur a rencontré une erreur : ' + msg(e), true)); }
  } else body.appendChild(U.empty({ title: 'L’éditeur de stratégie n’est pas chargé', text: 'Cette page a été construite sans l’éditeur. Claude peut écrire une stratégie en JSON dans votre base ; vous pouvez aussi partir d’un gabarit ci-dessous, puis tester.' }));
  if (!hasLibs()) return;
  var vs = versions();
  if (vs.length) {
    var s1 = sec(body, 'Vos *stratégies*', plural(vs.length, 'version'));
    s1.appendChild(h('div', { class: 'lb-stack' }, vs.slice(0, 30).map(function (d) {
      var st = d.status === 'scellee' ? 'scellée' : 'brouillon';
      return h('button', { class: 'lb-ver', type: 'button', 'aria-current': String(X.doc && X.doc.id === d.id), on: { click: function () { selectVersion(d.id); } } }, h('b', null, (d.name || 'Sans nom') + ' · v' + d.version), h('span', null, st + ' · ' + d.id + (d.template ? ' · gabarit ' + d.template : '')));
    })));
  }
  if (X.spec) body.appendChild(h('div', { style: 'margin:16px 0' }, readingCard(X)));
  var s2 = sec(body, 'Partir d’un *gabarit*', 'points de départ, sans avantage supposé');
  s2.appendChild(templateCards(false));
}

/* =====================================================================================================
   15. Le desk
   ===================================================================================================== */
function consumeGo() {
  var g = T.store.get(KEY.go, null), seen = T.store.get(KEY.goSeen, 0);
  if (!g || g.desk !== 'labo' || !fin(g.at) || g.at <= (seen || 0)) return null;
  T.store.set(KEY.goSeen, g.at);
  if (g.sel && /^s[a-z0-9]{6,20}_v\d+$/.test(g.sel) && coll('strategies').get(g.sel)) T.store.set(KEY.sel, g.sel);
  else if (g.sel && /^ds[a-z0-9]{6,20}$/.test(g.sel)) { T.store.set(KEY.ds, g.sel); S.dsId = null; }
  return g.tab || null;
}
var TABS = [{ id: 'concevoir', label: 'Concevoir' }, { id: 'tester', label: 'Tester' }, { id: 'valider', label: 'Valider' }, { id: 'verdict', label: 'Verdict' }, { id: 'suivre', label: 'Suivre' }];
var RENDER = { tester: renderTester, valider: renderValider, verdict: renderVerdict, suivre: renderSuivre };
function paint() {
  var v = S.view; if (!v) return;
  var root = v.root, ctx = v.ctx, tab = v.tab, hd = HEAD[tab];
  if (S.builderCleanup && tab !== 'concevoir') { try { S.builderCleanup(); } catch (e) {} S.builderCleanup = null; }
  T.clear(root);
  root.appendChild(U.page({ kicker: hd.k, title: hd.t, lede: hd.l }));
  root.appendChild(U.tabs({ tabs: TABS, value: tab, onChange: ctx.setTab }));
  var X;
  try { if (hasLibs()) ensureDs(); X = hasLibs() ? context() : { spec: null }; }
  catch (e) { root.appendChild(U.note('État du Labo illisible : ' + msg(e), true)); X = { spec: null }; }
  v.head = hasLibs() ? headEl(X) : h('div');
  root.appendChild(v.head);
  var body = h('div', { class: 'lb-body' }); root.appendChild(body);
  S.jobEls = {};
  if (tab === 'concevoir') renderConcevoir(body, ctx, X);
  else RENDER[tab](body, X);
}
LB.ui = {
  /* Crochets de vérification (banc Playwright) : lancer un calcul, savoir s’il tourne, partir d’un gabarit. */
  launch: function (tab) { var X = context(); if (!X.spec || !X.ds) return false; if (tab === 'tester') runTester(X); else if (tab === 'valider') runValider(X); else if (tab === 'verdict') runVerdict(X); else if (tab === 'oos') { if (myOpening(X)) runOos(X, null); else openOos(X); } else return false; return true; },
  busy: function () { return Object.keys(S.jobs).length > 0 || !!S.loading; },
  ready: function () { var X = context(); return !!(X.ds && X.ready); },
  errors: function () { return clone(S.errs); },
  useTemplate: function (id) { return useTemplate(id); },
  seal: function () { var X = context(); return X.spec ? sealSpec(X.spec) : Promise.resolve({ ok: false, why: 'aucune' }); },
  save: function (spec) { return saveSpec(spec); },
  context: function () { var X = context(); return { vid: X.vid, status: X.status, fp: X.fp, cut: X.cut, is: X.split && X.split.is, oos: X.split && X.split.oos, N: X.trials && X.trials.N }; }
};

T.desk({
  id: 'labo', label: 'Labo de stratégie', glyph: 'L', group: 'Recherche', order: 45,
  tabs: TABS,
  render: function (root, ctx) {
    injectCss();
    var tab = HEAD[ctx.tab] ? ctx.tab : 'concevoir';
    if (hasLibs()) { var g = consumeGo(); if (g && HEAD[g] && g !== tab) { setTimeout(function () { ctx.setTab(g); }, 0); } }
    S.view = { root: root, ctx: ctx, tab: tab, head: null };
    paint();
    var uns = [];
    if (hasLibs()) {
      ['strategies', 'essais', 'oos', 'config'].forEach(function (k) { uns.push(coll(k).on(function () { schedule(); })); });
      if (tab === 'suivre') uns.push(T.journal.on(function () { schedule(); }));
      var D = donnees(); if (D && D.onVisit) uns.push(D.onVisit(function () { schedule(); }));
      uns.push(T.store.on(KEY.lignee, function () { schedule(); }));
    }
    var mine = S.view;
    return function cleanup() {
      uns.forEach(function (f) { try { f(); } catch (e) {} });
      if (S.builderCleanup) { try { S.builderCleanup(); } catch (e) {} S.builderCleanup = null; }
      if (S.view === mine) S.view = null;
      clearTimeout(S.timer);
      /* Un rendu suivant du même desk (onglet, rerender) garde l’exécuteur ; quitter le desk le ferme. */
      setTimeout(function () { if (!S.view && T.nav.current() !== 'labo') closeVisit(); }, 0);
    };
  }
});
