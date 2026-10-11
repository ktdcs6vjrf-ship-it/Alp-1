/* Labo de stratégie — l’éditeur de stratégie, onglet « Concevoir » (LABO.md §6).
   Ce fichier n’enregistre aucun desk : il publie T.lib.laboBuilder. Le desk Labo (labo.js) possède l’état et
   appelle T.lib.laboBuilder.render(root, ctx, api) dans son onglet Concevoir. Tout formulaire est généré depuis
   T.lib.laboStats.GRAMMAR ; chaque phrase vient de describe() ou du lecteur ; chaque erreur vient de normalize().
   T.lib.laboStats et T.lib.laboEngine ne sont lus qu’à l’appel, jamais au chargement.
   Partie pure (testée en node, sans DOM) : génération des champs, valeurs de départ, parcours de la grammaire,
   paramètres nommés automatiquement, détection des formes trop profondes, messages en clair, cartes, opérandes
   de l’aperçu. Partie interface : liste des versions, pile de cartes, panneau plein écran, JSON, aperçu. */
T.lib = T.lib || {};
var LB = T.lib.laboBuilder = {};
var h = T.h, U = T.ui, F = T.fmt;

/* ================================================================================================
   0. Outils
   ================================================================================================ */
function isNum(x) { return typeof x === 'number' && x - x === 0; }
function isObj(x) { return !!x && typeof x === 'object' && !Array.isArray(x); }
function isRef(x) { return typeof x === 'string' && x.charAt(0) === '$'; }
function own(o, k) { return o != null && Object.prototype.hasOwnProperty.call(o, k); }
function clone(x) { return x === undefined ? undefined : JSON.parse(JSON.stringify(x)); }
function keyPath(k) { return String(k).split('.'); }
function getAt(o, path) { var x = o; for (var i = 0; i < path.length; i++) { if (x == null || typeof x !== 'object') return undefined; x = x[path[i]]; } return x; }
/* setAt(o, path, undefined) retire la clé (ou l’élément d’une liste). */
function setAt(o, path, v) {
  if (!path.length) return v;
  var x = o;
  for (var i = 0; i < path.length - 1; i++) { var k = path[i]; if (x[k] == null || typeof x[k] !== 'object') x[k] = typeof path[i + 1] === 'number' ? [] : {}; x = x[k]; }
  var last = path[path.length - 1];
  if (v === undefined) { if (Array.isArray(x) && typeof last === 'number') x.splice(last, 1); else delete x[last]; }
  else x[last] = v;
  return o;
}
function cap(s) { s = String(s); return s.charAt(0).toUpperCase() + s.slice(1); }
function lowFirst(s) { s = String(s); return /^.[a-zà-ÿ’ ,]/.test(s) || s.length === 1 ? s.charAt(0).toLowerCase() + s.slice(1) : s; }
function plural(n, one, many) { return F.int(n) + ' ' + (Math.abs(n) >= 2 ? (many || one + 's') : one); }
function sentence(t) { t = String(t == null ? '' : t).trim(); if (!t) t = 'Non renseigné'; t = cap(t); if (!/[.!?»…]$/.test(t)) t += '.'; return T.typo ? T.typo(t) : t; }
function fmtV(x) { if (!isNum(x)) return String(x); var s = String(Math.abs(x)), d = s.indexOf('.'), nd = d < 0 || /e/.test(s) ? 0 : Math.min(4, s.length - d - 1); return F.num(x, nd); }
function errMsg(e) { return String(e && e.message || e || 'erreur'); }
function LSx() { var L = T.lib && T.lib.laboStats; if (!L) throw new Error('La bibliothèque labo-stats est absente.'); return L; }
function LEx() { return T.lib && T.lib.laboEngine; }
function GR() { return LSx().GRAMMAR; }
function opDef(f) { var a = GR().operands; for (var i = 0; i < a.length; i++) if (a[i].f === f) return a[i]; return null; }
function condDef(k) { var a = GR().conditions; for (var i = 0; i < a.length; i++) if (a[i].key === k) return a[i]; return null; }
function orderList(kind) { var g = GR(); return kind === 'entry' ? g.entries : kind === 'stop' ? g.stops : g.targets; }
function orderDef(kind, type) { var a = orderList(kind); for (var i = 0; i < a.length; i++) if (a[i].type === type) return a[i]; return null; }

/* ================================================================================================
   1. Formes : clé d’une condition, genre d’un opérande, widgets
   ================================================================================================ */
var SIMPLE = ['cmp', 'cross', 'touch', 'reject', 'break', 'bar', 'time', 'news'];
var WRAP = ['all', 'any', 'not', 'for', 'within'];
LB.SIMPLE = SIMPLE; LB.WRAP = WRAP;
var PNAME = /^[A-Za-z_][A-Za-z0-9_]*$/;
function condKey(c) {
  if (!isObj(c)) return null;
  var ks = LSx().COND_KEYS.filter(function (k) { return own(c, k); });
  return ks.length === 1 ? ks[0] : null;
}
/* Genre d’un opérande : 'const' (nombre ou "$nom"), 'op' ({op, a, b}), sinon la valeur de f ; null si inconnu. */
function opKind(x) {
  if (isNum(x) || isRef(x)) return 'const';
  if (isObj(x)) {
    if (own(x, 'op')) return 'op';
    var d = typeof x.f === 'string' ? opDef(x.f) : null;
    if (d && !d.form) return x.f;
  }
  return null;
}
LB.condKey = condKey; LB.opKind = opKind;

var WIDGETS = ['number', 'time', 'timePair', 'chips', 'select', 'tz', 'operand', 'name', 'names', 'bool', 'cond', 'conds', 'barsOrTime', 'days'];
LB.WIDGETS = WIDGETS;
function widgetOf(a) {
  switch (a.type) {
    case 'int': case 'num': return 'number';
    case 'time': return 'time';
    case 'timePair': return 'timePair';
    case 'enum': return a.free ? 'tz' : ((a.options || []).length <= 6 ? 'chips' : 'select');
    case 'operand': return 'operand';
    case 'names': return a.single ? 'name' : 'names';
    case 'bool': return 'bool';
    case 'cond': return 'cond';
    case 'conds': return 'conds';
    case 'barsOrTime': return 'barsOrTime';
    case 'days': return 'days';
  }
  return 'advanced';
}
LB.widgetOf = widgetOf;
/* Un argument sans effet dans la configuration courante est masqué (il n’est pas retiré pour autant). */
function argHidden(owner, a, obj) {
  obj = obj || {};
  if (owner === 'operand:dist' && a.k === 'n') return obj.unit !== 'atr';
  if (owner === 'trail' && a.k === 'n') return obj.type !== 'atr';
  if ((owner === 'entry:limit' || owner === 'entry:stop') && a.k === 'tz') return !(typeof obj.valid === 'string' && !isRef(obj.valid));
  return false;
}
/* fieldsFor(args, obj, owner) → un descripteur par argument de la grammaire. owner : 'operand:<f>', 'cond:<clé>',
   'entry:<type>', 'stop:<type>', 'target:<type>', 'breakeven', 'trail', 'manage', 'risk', 'costs', 'session'. */
LB.fieldsFor = function (args, obj, owner) {
  return (args || []).map(function (a) {
    var w = widgetOf(a);
    return { k: a.k, path: keyPath(a.k), widget: w, label: a.label, unit: a.unit || null, options: a.options || null,
      min: a.min, max: a.max, gt: a.gt, req: !!a.req, nullable: !!a.nullable, def: a.def, init: a.init, omit: !!a.omit,
      cls: a.cls || null, single: !!a.single, value: getAt(obj, keyPath(a.k)), hidden: argHidden(owner || '', a, obj),
      numeric: w === 'number' || w === 'barsOrTime', arg: a };
  });
};

/* ================================================================================================
   2. Valeurs de départ (init de la grammaire). Un argument requis, ou doté d’un init sans être « omis par
      défaut », est écrit ; les autres sont laissés à normalize.
   ================================================================================================ */
var DEFAULT_COND = { bar: 'up' };
function initArgs(args, out) {
  (args || []).forEach(function (a) {
    var v = a.init;
    if (!(a.req || (v !== undefined && v !== null && !a.omit))) return;
    if (a.type === 'cond' && v === undefined) v = clone(DEFAULT_COND);
    if (a.type === 'conds' && (!Array.isArray(v) || !v.length)) v = [clone(DEFAULT_COND)];
    if (v === undefined) return;
    setAt(out, keyPath(a.k), clone(v));
  });
  return out;
}
LB.initOperand = function (f) {
  var d = opDef(f);
  if (!d) throw new Error('Opérande inconnu : « ' + f + ' ».');
  if (f === 'const') return d.args[0].init == null ? 0 : d.args[0].init;
  if (f === 'op') return initArgs(d.args, {});
  var o = initArgs(d.args, { f: f });
  if (f === 'dist' && o.unit !== 'atr') delete o.n;
  return o;
};
LB.initCond = function (key) {
  var d = condDef(key);
  if (!d) throw new Error('Condition inconnue : « ' + key + ' ».');
  return initArgs(d.args, {});
};
LB.initOrder = function (kind, type) {
  var d = orderDef(kind, type);
  if (!d) throw new Error('Type inconnu : « ' + type + ' ».');
  return initArgs(d.args, { type: type });
};
LB.initManage = function (which) {
  var M = GR().manage, o = initArgs(M[which].args, {});
  if (which === 'trail' && o.type !== 'atr') delete o.n;
  return o;
};
LB.defaultRule = function () { return { setup: [], trigger: clone(DEFAULT_COND), entry: { type: 'market' }, stop: LB.initOrder('stop', 'pts'), target: LB.initOrder('target', 'r') }; };
/* Une page vierge : une règle neutre et ses deux nombres déjà nommés. Aucun avantage n’y est supposé. */
LB.blank = function () {
  return { name: 'Nouvelle stratégie', hypothesis: '', side: 'long', mirror: true,
    long: { setup: [], trigger: { bar: 'up' }, entry: { type: 'market' }, stop: { type: 'pts', value: '$stop' }, target: { type: 'r', value: '$objectif' } },
    params: { stop: { v: 10, label: 'Stop, distance (points)' }, objectif: { v: 2, label: 'Objectif, multiple (R)' } } };
};
/* Changer le genre d’une condition : une condition simple devenue « non », « pour n barres »… est enveloppée,
   et les enfants passent d’un regroupement à l’autre. */
LB.switchCond = function (c, k2) {
  var k = condKey(c);
  if (k === k2) return clone(c);
  var simple = k && SIMPLE.indexOf(k) >= 0, kids = null;
  if (simple) kids = [clone(c)];
  else if (k) { var ch = childrenOf(c, k); kids = ch ? clone(ch.filter(Boolean)) : null; if (kids && !kids.length) kids = null; }
  if (WRAP.indexOf(k2) < 0) return LB.initCond(k2);
  var o = LB.initCond(k2);
  if (kids) { if (k2 === 'all' || k2 === 'any') o[k2] = kids; else if (k2 === 'not') o.not = kids[0]; else o.cond = kids[0]; }
  if ((k === 'for' || k === 'within') && (k2 === 'for' || k2 === 'within')) o[k2] = c[k];
  return o;
};

/* ================================================================================================
   3. Parcours de la grammaire : chaque argument d’un bloc, avec son chemin, sa définition et son porteur.
      fn(path, arg, owner, value) ; un opérande constant (nombre ou "$nom") est visité comme l’argument
      « v » de la forme const, porteur 'const:cond' | 'const:operand' | 'const:order'.
   ================================================================================================ */
function childrenOf(c, key) {
  if (key === 'all' || key === 'any') return Array.isArray(c[key]) ? c[key] : null;
  if (key === 'not') return [c.not];
  if (key === 'for' || key === 'within') return [c.cond];
  return [];
}
function walkOperand(spec, path, fn, parent) {
  var x = getAt(spec, path), k = opKind(x);
  if (k === 'const') { fn(path, opDef('const').args[0], 'const:' + parent, x); return; }
  if (!k) return;
  opDef(k).args.forEach(function (a) {
    var p = path.concat(keyPath(a.k)), v = getAt(spec, p);
    if (v === undefined || v === null) return;
    if (a.type === 'operand') walkOperand(spec, p, fn, 'operand'); else fn(p, a, 'operand:' + k, v);
  });
}
function walkCond(spec, path, fn) {
  var c = getAt(spec, path), key = condKey(c);
  if (!key) return;
  condDef(key).args.forEach(function (a) {
    var p = path.concat(keyPath(a.k)), v = getAt(spec, p);
    if (v === undefined || v === null) return;
    if (a.type === 'operand') walkOperand(spec, p, fn, 'cond');
    else if (a.type === 'cond') walkCond(spec, p, fn);
    else if (a.type === 'conds') { if (Array.isArray(v)) v.forEach(function (_, i) { walkCond(spec, p.concat([i]), fn); }); }
    else fn(p, a, 'cond:' + key, v);
  });
}
function walkOrder(spec, path, kind, fn) {
  var x = getAt(spec, path);
  if (!isObj(x)) return;
  var d = orderDef(kind, x.type);
  if (!d) return;
  d.args.forEach(function (a) {
    var p = path.concat(keyPath(a.k)), v = getAt(spec, p);
    if (v === undefined || v === null) return;
    if (a.type === 'operand') walkOperand(spec, p, fn, 'order'); else fn(p, a, kind + ':' + x.type, v);
  });
}
function walkManage(spec, fn) {
  var M = GR().manage, m = spec.manage;
  if (!isObj(m)) return;
  if (isNum(m.breakeven) || isRef(m.breakeven)) m.breakeven = { r: m.breakeven };
  [['breakeven', M.breakeven.args], ['trail', M.trail.args]].forEach(function (b) {
    if (!isObj(m[b[0]])) return;
    b[1].forEach(function (a) { var p = ['manage', b[0]].concat(keyPath(a.k)), v = getAt(spec, p); if (v !== undefined && v !== null) fn(p, a, b[0], v); });
  });
  M.args.forEach(function (a) { var p = ['manage', a.k], v = getAt(spec, p); if (v !== undefined && v !== null) fn(p, a, 'manage', v); });
}
/* Les blocs d’une règle dont les nombres deviennent des paramètres. */
var PARAM_BLOCKS = { contexte: 1, declencheur: 1, entree: 1, stop: 1, objectif: 1, gestion: 1 };
LB.PARAM_BLOCKS = PARAM_BLOCKS;
LB.walkBlock = function (spec, block, side, fn) {
  side = side || 'long';
  switch (block) {
    case 'contexte': (getAt(spec, [side, 'setup']) || []).forEach(function (_, i) { walkCond(spec, [side, 'setup', i], fn); }); break;
    case 'declencheur': walkCond(spec, [side, 'trigger'], fn); break;
    case 'entree': walkOrder(spec, [side, 'entry'], 'entry', fn); break;
    case 'stop': walkOrder(spec, [side, 'stop'], 'stop', fn); break;
    case 'objectif': walkOrder(spec, [side, 'target'], 'target', fn); break;
    case 'gestion': walkManage(spec, fn); break;
  }
};
LB.walkCond = function (spec, path, fn) { walkCond(spec, path, fn); };

/* ================================================================================================
   4. Paramètres nommés : chaque nombre d’une règle devient "$nom" et params.nom = { v, label }.
      Le nom vient du rôle du nombre (stop, objectif, bande, rsi…), rendu unique par un suffixe _2, _3…
   ================================================================================================ */
var HINTS = {
  'operand:vwap': { k: 'bande' }, 'operand:prev': { n: 'seances' }, 'operand:rvol': { n: 'rvol' }, 'operand:dist': { n: 'atr' },
  'cond:for': { 'for': 'duree' }, 'cond:within': { within: 'fenetre' }, 'cond:news': { 'news.impact': 'impact', 'news.before': 'avant', 'news.after': 'apres' },
  'entry:limit': { offset: 'decalage', valid: 'validite' }, 'entry:stop': { offset: 'decalage', valid: 'validite' },
  'stop:pts': { value: 'stop', buffer: 'marge' }, 'stop:atr': { value: 'stop_atr', n: 'atr', buffer: 'marge' }, 'stop:swing': { n: 'swing', buffer: 'marge' }, 'stop:level': { buffer: 'marge' },
  'target:r': { value: 'objectif' }, 'target:pts': { value: 'objectif' }, 'target:atr': { value: 'objectif_atr', n: 'atr' },
  breakeven: { r: 'be', offset: 'be_decalage' }, trail: { value: 'suiveur', n: 'atr', start: 'suiveur_depart' }, manage: { maxBars: 'duree' }
};
function hintOf(owner, k) {
  var m = HINTS[owner];
  if (m && m[k]) return m[k];
  if (owner === 'const:cond') return 'seuil';
  if (owner === 'const:order') return 'prix';
  if (owner === 'const:operand') return 'nombre';
  var p = String(owner).split(':');
  if (p[0] === 'operand') { if (k === 'lag') return 'decalage'; if (k === 'n') return p[1]; }
  return String(k).replace(/\./g, '_');
}
LB.hintOf = hintOf;
var OWNER_HEAD = { entry: 'Entrée', stop: 'Stop', target: 'Objectif', breakeven: 'Break-even', trail: 'Stop suiveur', manage: 'Gestion' };
function bare(s) { return String(s || '').replace(/\s*\([^)]*\)/g, '').trim(); }
function labelOf(owner, a) {
  var p = String(owner).split(':'), head = '';
  if (p[0] === 'const') return p[1] === 'cond' ? 'Seuil' : p[1] === 'order' ? 'Prix fixe' : 'Nombre';
  if (p[0] === 'operand') { var d = opDef(p[1]); head = d ? bare(d.label) : ''; }
  else if (p[0] === 'cond') { var c = condDef(p[1]); head = c ? bare(c.label) : ''; }
  else head = OWNER_HEAD[p[0]] || '';
  var t = bare(a.label), lab = head && t ? head + ', ' + lowFirst(t) : (head || t || 'Paramètre');
  if (a.unit && lab.indexOf(a.unit) < 0) lab += ' (' + a.unit + ')';
  return lab;
}
LB.labelOf = labelOf;
LB.autoName = function (hint, params) {
  var b = String(hint == null ? 'p' : hint);
  try { b = b.normalize('NFD').replace(/[̀-ͯ]/g, ''); } catch (e) { /* sans normalize : les accents tombent ci-dessous */ }
  b = b.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/__+/g, '_').replace(/^_+|_+$/g, '');
  if (!b) b = 'p';
  if (!/^[a-z_]/.test(b)) b = 'p_' + b;
  if (b.length > 24) b = b.slice(0, 24).replace(/_+$/, '');
  var n = b, i = 2;
  while (params && own(params, n)) n = b + '_' + (i++);
  return n;
};
/* setNumber(spec, path, x, owner, arg) : écrit le nombre x à path. Un "$nom" existant reçoit la valeur (et sa plage
   s’élargit pour la contenir) ; sinon un paramètre est créé et nommé. Rend le nom. */
LB.setNumber = function (spec, path, x, owner, arg) {
  if (!isObj(spec.params)) spec.params = {};
  var cur = getAt(spec, path);
  if (isRef(cur) && own(spec.params, cur.slice(1)) && isObj(spec.params[cur.slice(1)])) {
    var p = spec.params[cur.slice(1)];
    p.v = x;
    if (isNum(p.min) && x < p.min) p.min = x;
    if (isNum(p.max) && x > p.max) p.max = x;
    return cur.slice(1);
  }
  var name = LB.autoName(hintOf(owner, arg && arg.k), spec.params);
  spec.params[name] = { v: x, label: labelOf(owner, arg || {}) };
  setAt(spec, path, '$' + name);
  return name;
};
/* Tous les nombres littéraux d’un bloc deviennent des paramètres. Rend les noms créés. */
LB.parametrize = function (spec, block, side) {
  var out = [];
  if (!PARAM_BLOCKS[block]) return out;
  LB.walkBlock(spec, block, side, function (path, a, owner, v) {
    if (!isNum(v)) return;
    if (a.type !== 'int' && a.type !== 'num' && a.type !== 'barsOrTime') return;
    out.push(LB.setNumber(spec, path, v, owner, a));
  });
  return out;
};
function refsIn(x, acc) {
  if (isRef(x)) acc[x.slice(1)] = (acc[x.slice(1)] || 0) + 1;
  else if (Array.isArray(x)) x.forEach(function (y) { refsIn(y, acc); });
  else if (isObj(x)) for (var k in x) if (own(x, k)) refsIn(x[k], acc);
  return acc;
}
function specRefs(spec) { var c = {}; if (isObj(spec)) for (var k in spec) if (own(spec, k) && k !== 'params') refsIn(spec[k], c); return c; }
LB.refs = specRefs;
LB.useCount = function (spec, name) { return specRefs(spec)[name] || 0; };
/* Retire les paramètres devenus inutiles par une retouche : ceux que la version d’avant employait, et ceux créés
   pendant la retouche, quand plus rien ne les lit. Un paramètre déjà inutilisé avant reste (normalize le signale). */
LB.pruneDropped = function (before, after) {
  var gone = [];
  if (!isObj(after) || !isObj(after.params)) return gone;
  var b = specRefs(before), a = specRefs(after), bp = isObj(before && before.params) ? before.params : {};
  Object.keys(after.params).forEach(function (n) {
    if (a[n]) return;
    if (b[n] || !own(bp, n)) { delete after.params[n]; gone.push(n); }
  });
  return gone;
};
function replaceRefs(x, from, to) {
  if (x === '$' + from) return '$' + to;
  if (Array.isArray(x)) return x.map(function (y) { return replaceRefs(y, from, to); });
  if (isObj(x)) { var o = {}; for (var k in x) if (own(x, k)) o[k] = replaceRefs(x[k], from, to); return o; }
  return x;
}
/* Renomme un paramètre partout. Rend null, ou la raison du refus. */
LB.renameParam = function (spec, from, to) {
  to = String(to == null ? '' : to).trim();
  if (!isObj(spec.params) || !own(spec.params, from)) return 'Paramètre « ' + from + ' » introuvable.';
  if (to === from) return null;
  if (!PNAME.test(to)) return 'Nom invalide : lettres sans accent, chiffres et _, en commençant par une lettre.';
  if (own(spec.params, to)) return 'Le nom « ' + to + ' » est déjà pris.';
  for (var k in spec) if (own(spec, k) && k !== 'params') spec[k] = replaceRefs(spec[k], from, to);
  var np = {};
  Object.keys(spec.params).forEach(function (n) { np[n === from ? to : n] = spec.params[n]; });
  spec.params = np;
  return null;
};

/* ================================================================================================
   5. Formes trop profondes pour l’interface : le contexte est une liste (« et ») dont chaque élément est une
      condition simple ou un seul niveau de regroupement (all, any, not, for, within) sur des conditions simples.
      Au-delà : « bloc avancé — modifiable par Claude ou en JSON », en lecture seule. Les opérandes, eux, se
      modifient à toute profondeur (un panneau par niveau).
   ================================================================================================ */
LB.ADVANCED = 'Bloc avancé — modifiable par Claude ou en JSON.';
LB.editable = function (c, wrapperOk) {
  var key = condKey(c);
  if (!key) return false;
  if (SIMPLE.indexOf(key) >= 0) return true;
  if (!wrapperOk) return false;
  var ch = childrenOf(c, key);
  if (!ch) return false;
  return ch.every(function (x) { return x == null || LB.editable(x, false); });
};
LB.isDeep = function (c) { return !LB.editable(c, true); };
LB.deepItems = function (spec, side) {
  side = side || 'long';
  var r = isObj(spec) ? spec[side] : null, out = [];
  if (!isObj(r)) return out;
  (Array.isArray(r.setup) ? r.setup : []).forEach(function (c, i) { if (LB.isDeep(c)) out.push({ path: [side, 'setup', i], card: 'contexte', text: 'Condition ' + (i + 1) + ' : ' + lowFirst(LB.ADVANCED) }); });
  if (r.trigger != null && LB.isDeep(r.trigger)) out.push({ path: [side, 'trigger'], card: 'declencheur', text: LB.ADVANCED });
  return out;
};

/* ================================================================================================
   6. Messages de normalize en clair : « long.stop.value : … » → carte Stop, « Achat › stop › valeur : … ».
   ================================================================================================ */
var PW = { long: 'achat', short: 'vente', setup: 'contexte', trigger: 'déclencheur', entry: 'entrée', stop: 'stop', target: 'objectif',
  at: 'niveau', a: 'premier terme', b: 'second terme', value: 'valeur', buffer: 'marge', offset: 'décalage', valid: 'validité', through: 'au travers',
  n: 'longueur', k: 'bande', of: 'grandeur', cond: 'condition', not: 'négation', any: 'options', all: 'conditions', 'for': 'durée', within: 'fenêtre',
  touch: 'niveau touché', reject: 'niveau rejeté', 'break': 'niveau cassé', cmp: 'comparaison', cross: 'croisement', time: 'plage horaire', news: 'publications',
  impact: 'impact', before: 'avant', after: 'après', from: 'début', to: 'fin', flat: 'sortie forcée', tz: 'fuseau', days: 'jours', warmup: 'amorçage',
  session: 'séance', anchor: 'ancrage', instrument: 'instrument', side: 'sens', mirror: 'miroir', manage: 'gestion', breakeven: 'break-even', trail: 'suiveur',
  maxBars: 'durée maximale', exitOnOpposite: 'sortie sur signal opposé', risk: 'risque', costs: 'coûts', fill: 'remplissage', params: 'paramètres',
  name: 'nom', hypothesis: 'hypothèse', lag: 'décalage', unit: 'unité', names: 'noms', type: 'type', start: 'départ', r: 'déclenchement',
  mode: 'taille', contracts: 'contrats', riskUsd: 'risque en dollars', maxQty: 'plafond', minStopTicks: 'stop minimal', maxPerSession: 'entrées par séance',
  maxLossesPerSession: 'pertes par séance', dailyStopUsd: 'perte de séance', cooldown: 'pause', commissionRT: 'commission', slipTicks: 'glissement',
  sid: 'identifiant', id: 'identifiant', version: 'version', status: 'état', hash: 'hachage', sealedAt: 'date de scellement', root: 'origine', v: 'valeur',
  min: 'minimum', max: 'maximum', step: 'pas', label: 'libellé', m: 'barres', time2: 'heure', dynamic: 'relecture', dir: 'sens' };
var IDX = { setup: 'condition', any: 'option', all: 'condition', time: 'heure', days: 'jour', names: 'nom' };
LB.pathText = function (path) {
  var toks = String(path || '').match(/\[\d+\]|[^.[\]]+/g) || [], out = [], prev = null;
  toks.forEach(function (t) {
    var m = /^\[(\d+)\]$/.exec(t);
    if (m) { var i = +m[1] + 1; if (prev && IDX[prev] && out.length) out[out.length - 1] = IDX[prev] + ' ' + i; else if (out.length) out[out.length - 1] += ' ' + i; return; }
    if (prev === 'params' && out.length) { out[out.length - 1] = 'paramètre « ' + t + ' »'; prev = '#param'; return; }
    out.push(own(PW, t) ? PW[t] : t); prev = t;
  });
  return out.join(' › ');
};
var CARD_OF = { session: 'seance', anchor: 'seance', instrument: 'seance', side: 'sens', mirror: 'sens', manage: 'gestion', risk: 'risque', costs: 'risque', fill: 'risque', params: 'parametres', name: 'hypothese', hypothesis: 'hypothese' };
var RULE_CARD = { setup: 'contexte', trigger: 'declencheur', entry: 'entree', stop: 'stop', target: 'objectif' };
LB.cardOf = function (path) {
  path = String(path || '');
  var t = path.split(/[.[]/)[0];
  if (t === 'long' || t === 'short') { var m = /^(?:long|short)\.(setup|trigger|entry|stop|target)/.exec(path); return m ? RULE_CARD[m[1]] : 'sens'; }
  return own(CARD_OF, t) ? CARD_OF[t] : 'general';
};
LB.humanize = function (msg) {
  msg = String(msg == null ? '' : msg);
  var i = msg.indexOf(' : '), path = '', rest = msg;
  if (i > 0 && /^[A-Za-z_$][\w$]*(\.[\w$]+|\[\d+\])*$/.test(msg.slice(0, i))) { path = msg.slice(0, i); rest = msg.slice(i + 3); }
  var where = path ? cap(LB.pathText(path)) : '';
  return { path: path, card: LB.cardOf(path), text: T.typo((where ? where + ' : ' : '') + cap(rest)) };
};

/* ================================================================================================
   7. Cartes : une par bloc, dans l’ordre de LABO.md §6, avec la phrase de describe, les erreurs et les
      avertissements de normalize rangés par carte, et les blocs avancés.
   ================================================================================================ */
LB.CARDS = [
  { id: 'seance', title: 'Séance et ancrage', edit: true },
  { id: 'sens', title: 'Sens et miroir', edit: true },
  { id: 'contexte', title: 'Contexte', edit: true, rule: true },
  { id: 'declencheur', title: 'Déclencheur', edit: true, rule: true },
  { id: 'entree', title: 'Entrée', edit: true, rule: true },
  { id: 'stop', title: 'Stop', edit: true, rule: true },
  { id: 'objectif', title: 'Objectif', edit: true, rule: true },
  { id: 'gestion', title: 'Gestion de la position', edit: true },
  { id: 'risque', title: 'Risque et coûts', edit: true },
  { id: 'parametres', title: 'Paramètres', edit: true },
  { id: 'hypothese', title: 'Hypothèse', edit: true },
  { id: 'oos', title: 'Coupure hors échantillon', edit: false }
];
function cardDef(id) { for (var i = 0; i < LB.CARDS.length; i++) if (LB.CARDS[i].id === id) return LB.CARDS[i]; return null; }
/* Phrases d’une règle écrite côté vendeur (mirror false), par le lecteur de labo-stats. */
function shortTexts(spec) {
  var R = LSx().reader(spec.params), r = spec.short, o = {};
  if (!isObj(r)) return o;
  o.contexte = r.setup && r.setup.length ? 'à la vente, un signal n’est retenu que si ' + r.setup.map(R.cond).join(' et si ') : 'à la vente, aucun contexte : le déclencheur suffit';
  o.declencheur = 'à la vente, le signal tombe à la clôture d’une barre où ' + (r.trigger ? R.cond(r.trigger) : 'rien n’est défini') + ' ; rien ne s’exécute avant la barre suivante';
  o.entree = 'Vente ' + R.entry(r.entry, -1);
  o.stop = 'Stop ' + R.stop(r.stop, -1);
  o.objectif = r.target && r.target.type === 'none' ? 'Aucun objectif : la sortie vient du stop, de la gestion ou de la fin de fenêtre' : 'Objectif ' + R.target(r.target, -1);
  return o;
}
function dsCtx(ds) { return ds && isObj(ds) && ds.meta ? { dataset: ds } : undefined; }
/* cards(spec, o) → { list: [{ id, title, edit, texts, errors, warnings, advanced }], general: { errors, warnings },
   errors (nombre), norm (sortie de normalize) }. o = { side: 'long'|'short', dataset ({ meta, adj?, levels? }), values }. */
LB.cards = function (spec, o) {
  o = o || {};
  var L = LSx(), side = o.side === 'short' ? 'short' : 'long';
  var n = L.normalize(spec, dsCtx(o.dataset));
  var d = {};
  try { L.describe(spec, { values: o.values }).forEach(function (b) { d[b.id] = b.text; }); } catch (e) { d = {}; }
  var s = n.spec || (isObj(spec) ? spec : {});
  if (side === 'short') { var st = shortTexts(s); for (var k in st) if (own(st, k)) d[k] = sentence(st[k]); }
  var by = {}, general = { errors: [], warnings: [] };
  LB.CARDS.forEach(function (c) { by[c.id] = { id: c.id, title: c.title, edit: c.edit, rule: !!c.rule, texts: [], errors: [], warnings: [], advanced: [] }; });
  function put(id, t) { if (t) by[id].texts.push(t); }
  put('seance', d.seance); put('sens', d.sens); if (d.vendeur) put('sens', d.vendeur);
  ['contexte', 'declencheur', 'entree', 'stop', 'objectif', 'gestion'].forEach(function (k) { put(k, d[k] || sentence('Non renseigné')); });
  put('risque', d.risque); put('risque', d.couts); put('risque', d.remplissage);
  put('parametres', d.parametres || sentence('Aucun paramètre. Chaque nombre que tu modifies dans une règle devient un paramètre nommé, que l’onglet Valider sait balayer'));
  var nm = typeof s.name === 'string' && s.name.trim() ? s.name.trim() : '';
  put('hypothese', sentence(nm ? 'Nom : « ' + nm + ' »' : 'Sans nom'));
  put('hypothese', sentence(typeof s.hypothesis === 'string' && s.hypothesis.trim() ? s.hypothesis.trim() : 'Aucune hypothèse écrite. Une phrase suffit : pourquoi un avantage existerait ici, et ce qui le réfuterait. Elle est exigée pour sceller'));
  n.errors.forEach(function (m) { var x = LB.humanize(m); if (by[x.card]) by[x.card].errors.push(x.text); else general.errors.push(x.text); });
  n.warnings.forEach(function (m) {
    var x = LB.humanize(m);
    if (x.path === 'sid' || x.path === 'id') return;
    if (by[x.card]) by[x.card].warnings.push(x.text); else general.warnings.push(x.text);
  });
  LB.deepItems(s, side).forEach(function (x) { by[x.card].advanced.push(sentence(x.text)); });
  return { list: LB.CARDS.map(function (c) { return by[c.id]; }), general: general, errors: n.errors.length, norm: n };
};

/* ================================================================================================
   8. Aperçu : les opérandes d’une règle (résolus, côté vendeur reflété compris), leurs noms courts, et la mise
      en forme de la sortie de l’op features du moteur (séance témoin = la dernière qui porte un signal).
   ================================================================================================ */
var BASE_SHORT = { close: 'Clôture', open: 'Ouverture', high: 'Plus haut', low: 'Plus bas', hl2: 'Milieu', hlc3: 'Prix typique', body: 'Corps', range: 'Amplitude', volume: 'Volume' };
var OF_SHORT = { high: 'haut', low: 'bas', open: 'ouverture', close: 'clôture', mid: 'milieu' };
var SYM = { '+': '+', '-': '−', '*': '×', '/': '÷' };
LB.shortName = function (x, params) {
  var P = params || {};
  function num(v) { if (isRef(v)) { var p = P[v.slice(1)]; return p && isNum(p.v) ? fmtV(p.v) : v; } return isNum(v) ? fmtV(v) : '?'; }
  function go(x) {
    var k = opKind(x);
    if (k === 'const') return num(x);
    if (k === 'op') return '(' + go(x.a) + ' ' + (SYM[x.op] || x.op) + ' ' + go(x.b) + ')';
    if (!k) return 'opérande inconnu';
    var lag = x.lag && x.lag !== 0 ? ' [−' + num(x.lag) + ']' : '';
    switch (k) {
      case 'close': case 'open': case 'high': case 'low': case 'hl2': case 'hlc3': case 'body': case 'range': case 'volume': return BASE_SHORT[k] + lag;
      case 'rvol': return 'Volume relatif ' + num(x.n);
      case 'vwap': { var kk = x.k == null ? 0 : x.k; if (isRef(kk)) { var pk = P[kk.slice(1)]; kk = pk && isNum(pk.v) ? pk.v : kk; } return kk === 0 ? 'VWAP' : 'VWAP ' + (isNum(kk) ? (kk > 0 ? '+' : '−') + fmtV(Math.abs(kk)) : kk) + ' σ'; }
      case 'sess': return 'Séance : ' + ({ high: 'plus haut', low: 'plus bas', open: 'ouverture' }[x.of || 'high'] || 'plus haut');
      case 'prev': return (x.n == null || x.n === 1 ? 'Veille' : 'Séance −' + num(x.n)) + ' : ' + (OF_SHORT[x.of || 'close'] || 'clôture');
      case 'or': return 'Range ' + x.from + '–' + x.to + ' : ' + (OF_SHORT[x.of || 'high'] || 'haut');
      case 'at': return 'Barre de ' + x.time + ' : ' + (x.of === 'open' ? 'ouverture' : 'clôture');
      case 'sma': case 'ema': return k.toUpperCase() + ' ' + num(x.n) + (x.of != null && opKind(x.of) !== 'close' ? ' de ' + go(x.of) : '');
      case 'hh': return 'Plus haut ' + num(x.n) + ' b' + (x.of != null ? ' de ' + go(x.of) : '');
      case 'll': return 'Plus bas ' + num(x.n) + ' b' + (x.of != null ? ' de ' + go(x.of) : '');
      case 'sd': return 'Écart-type ' + num(x.n) + (x.of != null ? ' de ' + go(x.of) : '');
      case 'atr': return 'ATR ' + num(x.n == null ? 14 : x.n) + lag;
      case 'rsi': return 'RSI ' + num(x.n == null ? 14 : x.n) + lag;
      case 'tf': return (x.of == null ? 'Clôture' : go(x.of)) + ' en ' + num(x.m) + ' min';
      case 'level': return 'Niveau ' + (x.name || '?');
      case 'nearest': return 'Niveau proche ' + (x.side === 'below' ? 'dessous' : 'dessus');
      case 'time': return 'Heure';
      case 'dow': return 'Jour';
      case 'sessmin': return 'Minutes depuis l’ancre';
      case 'dist': return 'Écart ' + go(x.a) + ' → ' + go(x.b);
    }
    return k;
  }
  return go(x);
};
var NO_SERIES = { time: 1, dow: 1, sessmin: 1 };
/* operandsOf(spec, o) → [{ operand (résolu), name, cls, text }] : les opérandes que lisent contexte, déclencheur et
   niveaux d’ordre, sans doublon, sans constante ni clôture simple (le prix est tracé de toute façon). */
LB.operandsOf = function (spec, o) {
  o = o || {};
  var L = LSx(), out = [], seen = {}, r;
  try { r = L.resolve(L.normalize(spec).spec || spec, o.values || {}); } catch (e) { return out; }
  function add(x) {
    var k = opKind(x);
    if (!k || k === 'const' || NO_SERIES[k]) return;
    if (k === 'close' && !x.lag) return;
    var key = L.canonical(x);
    if (seen[key]) return;
    seen[key] = 1;
    var cls = 'neutre'; try { cls = L.classOf(x); } catch (e) { cls = 'neutre'; }
    out.push({ operand: clone(x), name: LB.shortName(x), cls: cls, text: L.reader({}).op(x) });
  }
  function cond(c) {
    var key = condKey(c);
    if (!key) return;
    condDef(key).args.forEach(function (a) {
      var v = getAt(c, keyPath(a.k));
      if (v == null) return;
      if (a.type === 'operand') add(v); else if (a.type === 'cond') cond(v); else if (a.type === 'conds' && Array.isArray(v)) v.forEach(cond);
    });
  }
  function rule(R) {
    if (!isObj(R)) return;
    (Array.isArray(R.setup) ? R.setup : []).forEach(cond);
    cond(R.trigger);
    ['entry', 'stop', 'target'].forEach(function (k) { var x = R[k]; if (isObj(x) && x.at != null) add(x.at); });
  }
  rule(r.long);
  if (r.side !== 'long') {
    if (r.mirror !== false) { if (r.long) { try { rule(LEx().mirror(r, 'spec', o.values)); } catch (e) { /* miroir refusé : normalize le dit */ } } }
    else rule(r.short);
  }
  return out;
};
/* previewFromFeatures(feat, ops) : feat = sortie de l’op features ({t,o,h,l,c,sm,keys,series,sig}), ops = sortie
   d’operandsOf (même ordre que feat.series). → { key, series:[{name, cls, points:[[t, v]]}], bars:{t,o,h,l,c},
   signals:[{t, side, i}], none (aucune séance de la fenêtre ne porte de signal), sessions }. */
LB.previewFromFeatures = function (feat, ops) {
  if (!feat || !feat.t || !feat.t.length) return { error: 'Aucune barre dans la sélection.' };
  var t = feat.t, n = t.length, sm = feat.sm || [], segs = [0];
  for (var i = 1; i < n; i++) {
    var dec = isNum(sm[i]) && isNum(sm[i - 1]) && sm[i] <= sm[i - 1];
    if (dec || t[i] - t[i - 1] > 50 * 60000) segs.push(i);
  }
  segs.push(n);
  var sig = feat.sig || {}, L = sig.L || [], S = sig.S || [], pick = -1;
  for (var s = segs.length - 2; s >= 0 && pick < 0; s--) for (var j = segs[s]; j < segs[s + 1]; j++) if (L[j] === 1 || S[j] === 1) { pick = s; break; }
  var none = pick < 0;
  if (none) pick = segs.length - 2;
  var a = segs[pick], b = segs[pick + 1], keys = feat.keys || [];
  var key = keys.length === segs.length - 1 ? keys[pick] : keys[keys.length - 1] || null;
  function sl(arr) { return arr ? Array.prototype.slice.call(arr, a, b) : []; }
  var signals = [];
  for (var q = a; q < b; q++) { if (L[q] === 1) signals.push({ t: t[q], side: 'long', i: q - a }); if (S[q] === 1) signals.push({ t: t[q], side: 'short', i: q - a }); }
  var series = (ops || []).map(function (op, k) {
    var v = (feat.series || [])[k] || [], pts = [];
    for (var z = a; z < b; z++) pts.push([t[z], v[z] == null || !isNum(v[z]) ? null : v[z]]);
    return { name: op.name, cls: op.cls, points: pts };
  });
  return { key: key, series: series, bars: { t: sl(t), o: sl(feat.o), h: sl(feat.h), l: sl(feat.l), c: sl(feat.c) }, signals: signals, none: none, sessions: segs.length - 1 };
};

/* ================================================================================================
   9. Versions, JSON, texte pour Claude
   ================================================================================================ */
LB.STATUS = { brouillon: 'Brouillon', scellee: 'Scellée', alteree: 'Altérée' };
LB.versionInfo = function (doc) {
  doc = doc || {};
  var st = 'brouillon';
  if (doc.status === 'scellee') { var v = { ok: false }; try { v = LSx().verifySeal(doc); } catch (e) { v = { ok: false }; } st = v.ok ? 'scellee' : 'alteree'; }
  return { id: doc.id || null, sid: doc.sid || null, root: doc.root || doc.sid || null, version: isNum(doc.version) ? doc.version : 1, name: typeof doc.name === 'string' && doc.name.trim() ? doc.name.trim() : 'Sans nom',
    status: st, hash: doc.hash || null, short: doc.hash ? String(doc.hash).slice(0, 9) : null, u: doc.u || doc.createdAt || 0, sealedAt: doc.sealedAt || null };
};
/* Regroupe les versions par sid : [{ sid, name, versions (la plus récente d’abord), u }], le plus récent d’abord. */
LB.versionGroups = function (docs) {
  var by = {}, order = [];
  (docs || []).forEach(function (d) { if (!d || !d.id || d.deleted) return; var k = d.sid || d.id; if (!by[k]) { by[k] = []; order.push(k); } by[k].push(LB.versionInfo(d)); });
  var gs = order.map(function (k) {
    var vs = by[k].sort(function (a, b) { return (b.version || 0) - (a.version || 0); });
    return { sid: k, name: vs[0].name, versions: vs, u: Math.max.apply(null, vs.map(function (v) { return v.u || 0; })) };
  });
  gs.sort(function (a, b) { return b.u - a.u; });
  return gs;
};
var IDENT = ['id', 'sid', 'root', 'version', 'status', 'hash', 'sealedAt', 'createdAt', 'u'];
/* parseJson(text, cur, dataset?) → { ok, spec (normalisée), raw, errors (bruts), warnings, text }. L’identité de la
   version courante (id, sid, version, état…) est conservée : elle appartient à la page, pas au collage. */
LB.parseJson = function (text, cur, dataset) {
  var raw;
  try { raw = JSON.parse(String(text == null ? '' : text)); } catch (e) { return { ok: false, spec: null, raw: null, errors: ['JSON illisible : ' + e.message], warnings: [], text: text }; }
  if (!isObj(raw)) return { ok: false, spec: null, raw: null, errors: ['Une stratégie est un objet JSON { … }.'], warnings: [], text: text };
  if (cur) IDENT.forEach(function (k) { if (own(cur, k)) raw[k] = clone(cur[k]); else delete raw[k]; });
  var n = LSx().normalize(raw, dsCtx(dataset));
  return { ok: !n.errors.length && !!n.spec, spec: n.spec, raw: raw, errors: n.errors, warnings: n.warnings, text: text };
};
LB.claudeText = function (spec, info) {
  spec = spec || {};
  var name = typeof spec.name === 'string' && spec.name.trim() ? spec.name.trim() : 'sans nom';
  var id = spec.id || '(pas encore enregistrée)', st = info && LB.STATUS[info.status] ? ' (' + LB.STATUS[info.status].toLowerCase() + ')' : '';
  return 'Stratégie « ' + name + ' » — version ' + id + st + '\n\n' +
    'Ce que je veux changer, en mots :\n…\n\n' +
    'Document JSON de la version (Labo de stratégie, ALP Desk) :\n' + JSON.stringify(spec, null, 2) + '\n';
};
/* La spec à écrire : normalisée si elle est valide, telle quelle sinon (normalize retirerait les pièces fautives). */
LB.specForSave = function (draft, dataset) {
  var n = LSx().normalize(draft, dsCtx(dataset));
  return n.errors.length || !n.spec ? clone(draft) : n.spec;
};

/* ================================================================================================
   10. Style (variables du socle seulement)
   ================================================================================================ */
var CSS = '.lb{display:flex;flex-direction:column;gap:22px;min-width:0}' +
  '.lb .chip,.lb-ov .chip{min-height:44px;height:auto;padding:9px 12px;white-space:normal;text-align:left;line-height:1.3;font:600 12px/1.3 var(--f-mono);max-width:100%;overflow-wrap:anywhere}' +
  '.lb .btn.sm,.lb-ov .btn.sm{height:44px;min-width:44px}' +
  '.lb .seg,.lb-ov .seg{min-height:44px}.lb .seg button,.lb-ov .seg button{white-space:normal;line-height:1.2;padding:6px 8px}' +
  '.lb-chips{display:flex;flex-wrap:wrap;gap:6px;min-width:0}' +
  '.lb-lab{font:600 10.5px/1.3 var(--f-mono);color:var(--mute);letter-spacing:.02em}' +
  '.lb-sub{margin:6px 0 0;font:600 10px/1.3 var(--f-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--soft)}' +
  '.lb-vl{display:flex;flex-direction:column;border:1px solid var(--line);border-radius:var(--r);background:var(--panel);overflow:hidden;min-width:0}' +
  '.lb-vi{display:flex;flex-direction:column;gap:8px;padding:12px 13px;border-top:1px solid var(--line);min-width:0}.lb-vi:first-child{border-top:0}' +
  '.lb-vi.on{background:linear-gradient(90deg,var(--violet-a),transparent 75%)}' +
  '.lb-vt{display:flex;align-items:baseline;gap:6px 10px;min-width:0;flex-wrap:wrap}.lb-vt b{font-size:14px;font-weight:600;color:var(--fg);overflow-wrap:anywhere;min-width:0}' +
  '.lb-vm{font:500 11px/1.4 var(--f-mono);color:var(--mute);overflow-wrap:anywhere}' +
  '.lb-say{margin:0;font-size:13.5px;line-height:1.55;color:var(--fg);overflow-wrap:anywhere}.lb-say+.lb-say{color:var(--soft)}' +
  '.lb-big{font-size:14.5px;color:var(--hi)}' +
  '.lb-err{margin:0;font-size:12.5px;line-height:1.5;color:var(--fg);border-left:2px solid var(--violet);padding:2px 0 2px 10px;overflow-wrap:anywhere}' +
  '.lb-wrn{margin:0;font-size:12px;line-height:1.5;color:var(--mute);overflow-wrap:anywhere}' +
  '.lb-adv{margin:0;font:500 11.5px/1.45 var(--f-mono);color:var(--soft);background-image:var(--hatch);border:1px dashed var(--line-2);border-radius:8px;padding:7px 9px;overflow-wrap:anywhere}' +
  '.lb-cf{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap}' +
  '.lb-acts{display:flex;flex-wrap:wrap;gap:8px}' +
  '.lb-hd{display:flex;flex-direction:column;gap:6px;min-width:0}.lb-hd b{font-size:17px;font-weight:600;color:var(--hi);overflow-wrap:anywhere;line-height:1.25}' +
  '.lb-pills{display:flex;flex-wrap:wrap;gap:6px;align-items:center}' +
  '.lb-hash{font:500 11px/1.3 var(--f-mono);color:var(--soft)}' +
  '.lb-item{display:flex;flex-direction:column;gap:8px;border:1px solid var(--line);border-radius:10px;background:var(--raise);padding:10px 11px;min-width:0}' +
  '.lb-itx{margin:0;font-size:13.5px;line-height:1.5;color:var(--fg);overflow-wrap:anywhere}' +
  '.lb-ia{display:flex;flex-wrap:wrap;gap:6px}' +
  '.lb-ic{width:44px;padding:0;font-size:15px}' +
  '.lb-grp{display:flex;flex-direction:column;gap:12px;min-width:0}' +
  '.lb-cls{display:inline-block;font:500 10.5px/1.3 var(--f-mono);color:var(--violet-2);border:1px solid var(--violet-b);border-radius:6px;padding:2px 6px;margin-left:6px;white-space:nowrap}' +
  '.lb-pvh{margin:0;font:500 12px/1.5 var(--f-mono);color:var(--soft);overflow-wrap:anywhere}.lb-pvh b{color:var(--fg);font-weight:600}' +
  '.lb-pvs{margin:6px 0 -4px;font:600 10.5px/1.3 var(--f-mono);color:var(--mute)}' +
  '.lb-pv{display:flex;flex-direction:column;gap:10px;min-width:0}' +
  '.lb-wait{display:flex;align-items:center;gap:10px;padding:14px;border:1px dashed var(--line-2);border-radius:var(--r);font:500 12px/1.4 var(--f-mono);color:var(--mute);background:var(--panel)}' +
  '.lb-wait i{width:8px;height:8px;border-radius:50%;background:var(--violet);flex:none;animation:lbp 1s ease-in-out infinite}@keyframes lbp{50%{opacity:.25}}' +
  '.lb-ta{width:100%;min-height:120px;border:1px solid var(--line-2);border-radius:9px;background:var(--raise);color:var(--fg);font:12px/1.45 var(--f-mono);padding:10px}' +
  'html.lb-lock,html.lb-lock body{overflow:hidden}' +
  '.lb-ov{position:fixed;inset:0;z-index:60;background:var(--bg);display:flex;flex-direction:column}' +
  '.lb-ovh{flex:none;display:flex;align-items:center;gap:10px;min-height:56px;padding:calc(env(safe-area-inset-top,0px) + 6px) max(12px,calc((100% - 736px)/2)) 6px;border-bottom:1px solid var(--line);background:var(--panel)}' +
  '.lb-ovh .t{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}.lb-ovh .t small{font:500 10.5px/1.3 var(--f-mono);color:var(--mute);overflow-wrap:anywhere}.lb-ovh .t b{font-size:15px;font-weight:600;color:var(--hi);overflow-wrap:anywhere;line-height:1.25}' +
  '.lb-ovh .btn{width:44px;padding:0;flex:none;font-size:17px}' +
  '.lb-ovb{flex:1;overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;overscroll-behavior:contain}' +
  '.lb-ovi{max-width:760px;margin:0 auto;padding:16px 16px 28px;display:flex;flex-direction:column;gap:16px;min-width:0}' +
  '.lb-ovf{flex:none;border-top:1px solid var(--line);background:var(--panel);padding:10px max(12px,calc((100% - 736px)/2)) calc(10px + env(safe-area-inset-bottom,0px));display:flex;flex-direction:column;gap:8px}' +
  '.lb-live{max-height:22vh;overflow-y:auto;display:flex;flex-direction:column;gap:6px}.lb-live p{margin:0;font-size:12.5px;line-height:1.5;color:var(--soft);overflow-wrap:anywhere}.lb-live p.lb-err{color:var(--fg)}' +
  '.lb-fb{display:flex;gap:8px}.lb-fb .btn{flex:1;min-width:0}' +
  '.lb-json{width:100%;min-height:46vh;border:1px solid var(--line-2);border-radius:9px;background:var(--raise);color:var(--fg);font:12.5px/1.45 var(--f-mono);padding:10px;resize:vertical;white-space:pre;overflow:auto}' +
  '.lb-chk{display:flex;flex-direction:column;gap:6px;margin:0;padding:0;list-style:none}.lb-chk li{display:flex;gap:8px;font-size:13px;line-height:1.45;color:var(--fg)}.lb-chk li i{flex:none;width:18px;font-style:normal;font-family:var(--f-mono);color:var(--violet)}.lb-chk li.no{color:var(--soft)}.lb-chk li.no i{color:var(--mute)}' +
  '.lb .fld input[type=time],.lb-ov .fld input[type=time],.lb .fld input[type=date]{font-family:var(--f-mono)}';
function injectCss() { if (typeof document === 'undefined' || document.getElementById('labo-builder-css')) return; var s = document.createElement('style'); s.id = 'labo-builder-css'; s.textContent = CSS; document.head.appendChild(s); }
LB.injectCss = injectCss;

/* ================================================================================================
   11. Interface. ST garde le brouillon et le panneau d’un rendu à l’autre (labo.js peut redessiner l’onglet) ;
       le brouillon non enregistré est aussi gardé dans T.store, pour survivre à un rechargement.
   ================================================================================================ */
var DRAFT_KEY = 'labo:concevoir:brouillon';
var ST = { key: null, draft: null, base: null, baseU: null, dirty: false, isNew: false, newLabel: '', side: 'long', panel: null, prev: {}, listAll: false, confirm: null, copy: null, busy: false, restored: false };
var OV = { el: null, body: null, foot: null, say: null, sayFn: null, R: null };
var FID = 0;
function has(api, k) { return !!api && typeof api[k] === 'function'; }
function ac(R, k, args) { if (!has(R.api, k)) return null; try { return R.api[k].apply(R.api, args || []); } catch (e) { if (typeof console !== 'undefined') console.error(e); return null; } }
function toast(m) { try { T.toast(m); } catch (e) { /* hors navigateur */ } }
function storeDraft() {
  try { T.store.set(DRAFT_KEY, ST.isNew ? { id: 'new', spec: ST.draft, label: ST.newLabel, at: Date.now() } : { id: ST.key, u0: ST.baseU, spec: ST.draft, at: Date.now() }); } catch (e) { /* stockage indisponible */ }
}
function clearDraft() { try { T.store.set(DRAFT_KEY, null); } catch (e) { /* idem */ } }
function storedDraft() { try { return T.store.get(DRAFT_KEY, null); } catch (e) { return null; } }
function load(cur) {
  var same = ST.key === cur.id;
  ST.key = cur.id; ST.base = clone(cur); ST.baseU = cur.u || 0; ST.draft = clone(cur); ST.dirty = false; ST.isNew = false;
  if (!same) { ST.side = 'long'; ST.panel = null; ST.confirm = null; ST.copy = null; }
  var sd = storedDraft();
  if (sd && sd.id === cur.id && sd.u0 === ST.baseU && isObj(sd.spec) && cur.status !== 'scellee') { ST.draft = sd.spec; ST.dirty = true; }
}
function sync(R) {
  if (ST.isNew) return;
  var cur = ac(R, 'current');
  if (!cur) {
    if (!ST.restored) { ST.restored = true; var sd = storedDraft(); if (sd && sd.id === 'new' && isObj(sd.spec)) { ST.isNew = true; ST.key = 'new'; ST.draft = sd.spec; ST.dirty = true; ST.newLabel = sd.label || ''; return; } }
    ST.key = null; ST.draft = null; ST.base = null; ST.dirty = false; ST.panel = null;
    return;
  }
  ST.restored = true;
  if (ST.key !== cur.id || (!ST.dirty && (cur.u || 0) !== ST.baseU)) load(cur);
}
function dataset(R) { var d = ac(R, 'dataset'); return d && isObj(d) ? d : null; }
function readOnly() { if (ST.isNew || !ST.base) return false; return ST.base.status === 'scellee'; }
function curInfo() { return LB.versionInfo(ST.isNew ? ST.draft : ST.base); }
function viewSide() {
  var s = ST.draft;
  if (!s) return 'long';
  if (s.mirror === false && isObj(s.short) && !isObj(s.long)) return 'short';
  if (s.mirror === false && isObj(s.short) && s.side !== 'long') return ST.side === 'short' ? 'short' : 'long';
  return 'long';
}

LB.render = function (root, ctx, api) {
  injectCss();
  var alive = true, wrap = h('div', { class: 'lb' });
  root.appendChild(wrap);
  var R = { root: wrap, ctx: ctx || {}, api: api || {}, alive: function () { return alive && wrap.isConnected !== false; } };
  try { paint(R); } catch (e) { if (typeof console !== 'undefined') console.error(e); wrap.appendChild(U.empty({ title: 'L’éditeur a rencontré une erreur', text: errMsg(e) })); }
  if (ST.panel && ST.draft) showOverlay(R);
  return function cleanup() { alive = false; removeOverlay(); };
};

/* ---------- Vue principale ---------- */
function paint(R) {
  sync(R);
  T.clear(R.root);
  R.root.appendChild(listSection(R));
  if (!ST.draft) {
    R.root.appendChild(U.empty({ title: 'Aucune stratégie ouverte', text: 'Choisis une version dans la liste, ou pars d’une page vierge ou d’un gabarit. Tu peux aussi décrire ta stratégie à Claude en mots : il l’écrit, la vérifie, et elle apparaît ici.' }));
    return;
  }
  var C = LB.cards(ST.draft, { side: viewSide(), dataset: dataset(R) });
  R.root.appendChild(headSection(R, C));
  R.root.appendChild(stackSection(R, C));
  R.root.appendChild(previewSection(R, C));
  try { T.typoTree(R.root); } catch (e) { /* hors navigateur */ }
}

function listSection(R) {
  var docs = ac(R, 'versions') || [], groups = LB.versionGroups(docs), cur = ST.isNew ? null : ST.key;
  var s = U.section('Tes *stratégies*', docs.length ? plural(docs.length, 'version') : null);
  if (!groups.length) s.appendChild(U.note('Aucune stratégie enregistrée pour l’instant.'));
  else {
    var list = h('div', { class: 'lb-vl' }), shown = ST.listAll ? groups : groups.slice(0, 5);
    shown.forEach(function (g) {
      var on = g.versions.some(function (v) { return v.id === cur; });
      var chips = h('div', { class: 'lb-chips' }, g.versions.map(function (v) {
        var lab = 'v' + v.version + (v.status === 'scellee' ? ' · scellée' : v.status === 'alteree' ? ' · altérée' : '');
        return h('button', { class: 'chip', type: 'button', 'aria-pressed': String(v.id === cur), title: v.short ? 'hachage ' + v.short : null, on: { click: function () { if (v.id !== cur) selectVersion(R, v.id); } } }, lab);
      }));
      var last = g.versions[0];
      list.appendChild(h('div', { class: 'lb-vi' + (on ? ' on' : '') },
        h('div', { class: 'lb-vt' }, h('b', null, g.name), statusPill(last.status)),
        h('div', { class: 'lb-vm' }, plural(g.versions.length, 'version') + (last.short ? ' · ' + last.short : '') + (last.u ? ' · modifiée le ' + F.dateLong(last.u) : '')),
        chips));
    });
    s.appendChild(list);
    if (groups.length > 5) s.appendChild(h('div', { class: 'row' }, U.button({ label: ST.listAll ? 'Réduire la liste' : 'Afficher les ' + groups.length + ' stratégies', kind: 'ghost', small: true, onClick: function () { ST.listAll = !ST.listAll; paint(R); } })));
  }
  /* Nouvelle : vierge ou gabarit */
  var tpls = []; try { tpls = LSx().TEMPLATES || []; } catch (e) { tpls = []; }
  var opts = [{ v: 'blank', label: 'Page vierge' }].concat(tpls.map(function (t) { return { v: t.id, label: t.label }; }));
  s.appendChild(h('div', { class: 'lb-grp' },
    h('p', { class: 'lb-sub' }, 'Nouvelle stratégie'),
    h('div', { class: 'lb-chips' }, opts.map(function (o) { return h('button', { class: 'chip', type: 'button', 'aria-pressed': String(ST.isNew && ST.newLabel === o.label), on: { click: function () { askNew(R, o.v, o.label); } } }, o.label); })),
    U.note('Les gabarits sont des points de départ : aucun ne prétend à un avantage. Le test, ses lois nulles et le registre des essais le diront.')));
  if (ST.confirm && ST.confirm.kind === 'new') {
    s.appendChild(U.callout([h('b', null, 'Modifications non enregistrées. '), 'Elles seront perdues si tu ouvres une nouvelle stratégie.',
      h('div', { class: 'row', style: 'margin-top:10px' }, U.button({ label: 'Continuer', kind: 'pri', onClick: function () { var c = ST.confirm; ST.confirm = null; startNew(R, c.key, c.label); } }), U.button({ label: 'Garder', kind: 'ghost', onClick: function () { ST.confirm = null; paint(R); } }))]));
  }
  return s;
}
function statusPill(st) { return U.pill(LB.STATUS[st] || st, st === 'scellee' ? 'acc' : st === 'alteree' ? 'no' : null); }
function selectVersion(R, id) {
  if (ST.dirty) { storeDraft(); toast('Brouillon gardé : il reviendra quand tu rouvriras cette version.'); }
  ST.isNew = false; ST.confirm = null;
  if (has(R.api, 'select')) ac(R, 'select', [id]);
  if (R.alive()) paint(R);
}
function askNew(R, key, label) {
  if (ST.dirty && ST.draft) { ST.confirm = { kind: 'new', key: key, label: label }; paint(R); return; }
  startNew(R, key, label);
}
function startNew(R, key, label) {
  var spec = null;
  try {
    if (key === 'blank') spec = has(R.api, 'blank') ? ac(R, 'blank') : LB.blank();
    else spec = has(R.api, 'fromTemplate') ? ac(R, 'fromTemplate', [key]) : LSx().fromTemplate(key);
  } catch (e) { toast(errMsg(e)); return; }
  if (!isObj(spec)) { toast('Impossible de créer cette stratégie.'); return; }
  ST.isNew = true; ST.key = 'new'; ST.draft = clone(spec); ST.base = null; ST.dirty = true; ST.newLabel = label || ''; ST.panel = null; ST.side = 'long'; ST.confirm = null; ST.copy = null;
  storeDraft();
  paint(R);
}

function headSection(R, C) {
  var spec = ST.draft, info = curInfo(), ro = readOnly(), s = U.section('La règle, *bloc par bloc*', ST.isNew ? 'nouvelle' : 'v' + info.version);
  var tpl = null; try { tpl = spec.template ? (LSx().TEMPLATES || []).filter(function (t) { return t.id === spec.template; })[0] : null; } catch (e) { tpl = null; }
  var pills = h('div', { class: 'lb-pills' }, ST.isNew ? U.pill('Non enregistrée', 'no') : statusPill(info.status), !ST.isNew && ST.dirty ? U.pill('Modifiée', 'no') : null,
    info.short ? h('span', { class: 'lb-hash' }, 'hachage ' + info.short) : null, C.errors ? h('span', { class: 'lb-hash' }, plural(C.errors, 'erreur')) : null);
  var body = [h('div', { class: 'lb-hd' }, h('b', null, info.name), pills, h('div', { class: 'lb-vm' }, ST.isNew ? 'Pas encore enregistrée : rien n’est écrit dans ton compte avant « Enregistrer ».' : (spec.id || '') + (info.sealedAt ? ' · scellée le ' + F.dateLong(info.sealedAt) : '')))];
  if (ST.isNew && tpl) body.push(U.note(tpl.description));
  if (ro && info.status === 'scellee') body.push(U.callout([h('b', null, 'Version scellée, en lecture seule. '), 'Sa règle est figée par son hachage. Pour la retoucher, crée la version suivante : elle part en brouillon et garde la lignée.']));
  if (ro && info.status === 'alteree') body.push(U.callout([h('b', null, 'Version altérée. '), 'Son contenu ne correspond plus au hachage écrit au scellement : elle ne peut ni ouvrir le hors échantillon ni prétendre à un verdict. Crée une nouvelle version à partir d’elle.']));
  body.push(actionsRow(R, C, info, ro));
  if (ST.confirm && ST.confirm.kind === 'remove') {
    body.push(U.callout([h('b', null, 'Supprimer la version ' + info.version + ' de « ' + info.name + ' » ? '), 'Elle disparaît de la liste. Les essais qu’elle a déjà comptés restent dans le registre : N ne baisse pas.',
      h('div', { class: 'row', style: 'margin-top:10px' }, U.button({ label: 'Supprimer', kind: 'pri', onClick: function () { doRemove(R); } }), U.button({ label: 'Garder', kind: 'ghost', onClick: function () { ST.confirm = null; paint(R); } }))]));
  }
  if (ST.copy) body.push(copyBox(R));
  s.appendChild(U.card({ body: body, accent: ro ? false : ST.dirty }));
  if (C.general.errors.length) C.general.errors.forEach(function (t) { s.appendChild(h('p', { class: 'lb-err' }, t)); });
  return s;
}
function actionsRow(R, C, info, ro) {
  var b = [];
  if (ro) b.push(U.button({ label: 'Nouvelle version', kind: 'pri', onClick: function () { doVersion(R, 'newVersion'); } }));
  else {
    b.push(U.button({ label: ST.busy ? 'Enregistrement…' : 'Enregistrer', kind: 'pri', disabled: !ST.dirty || ST.busy, onClick: function () { doSave(R); } }));
    if (!ST.isNew) b.push(U.button({ label: 'Sceller', kind: 'ghost', disabled: ST.busy, onClick: function () { openSeal(R); } }));
  }
  if (!ST.isNew && !ro) b.push(U.button({ label: 'Nouvelle version', kind: 'ghost', onClick: function () { doVersion(R, 'newVersion'); } }));
  if (!ST.isNew) b.push(U.button({ label: 'Dupliquer', kind: 'ghost', onClick: function () { doVersion(R, 'duplicate'); } }));
  b.push(U.button({ label: 'JSON', kind: 'ghost', onClick: function () { openJson(R); } }));
  b.push(U.button({ label: 'Décrire à Claude', kind: 'ghost', onClick: function () { copyForClaude(R); } }));
  if (ST.dirty && !ro) b.push(U.button({ label: ST.isNew ? 'Abandonner' : 'Annuler les modifications', kind: 'ghost', onClick: function () { abandon(R); } }));
  if (!ST.isNew) b.push(U.button({ label: 'Supprimer', kind: 'ghost', onClick: function () { ST.confirm = { kind: 'remove' }; paint(R); } }));
  return h('div', { class: 'lb-acts' }, b);
}
function abandon(R) {
  clearDraft();
  if (ST.isNew) { ST.isNew = false; ST.key = null; ST.draft = null; ST.dirty = false; ST.newLabel = ''; }
  else { ST.draft = clone(ST.base); ST.dirty = false; }
  ST.panel = null; ST.confirm = null;
  paint(R);
}
function doSave(R) {
  if (!has(R.api, 'save')) { toast('Enregistrement indisponible ici.'); return; }
  var ds = dataset(R), spec = LB.specForSave(ST.draft, ds), nErr = LSx().normalize(ST.draft, dsCtx(ds)).errors.length;
  ST.busy = true; paint(R);
  Promise.resolve(ac(R, 'save', [spec])).then(function (id) {
    ST.busy = false; clearDraft(); ST.isNew = false; ST.dirty = false; ST.key = null; ST.newLabel = '';
    toast(nErr ? 'Enregistrée, avec ' + plural(nErr, 'erreur') + ' à corriger.' : 'Version enregistrée.');
    if (id && has(R.api, 'select')) ac(R, 'select', [id]);
    if (R.alive()) paint(R);
  }, function (e) { ST.busy = false; toast('Enregistrement impossible : ' + errMsg(e)); if (R.alive()) paint(R); });
}
function doVersion(R, kind) {
  var ds = dataset(R), spec = LB.specForSave(ST.draft, ds);
  Promise.resolve(ac(R, kind, [spec])).then(function (id) {
    clearDraft(); ST.dirty = false; ST.key = null;
    toast(kind === 'duplicate' ? 'Copie créée : nouvelle lignée de travail, même origine.' : 'Nouvelle version créée en brouillon.');
    if (id && has(R.api, 'select')) ac(R, 'select', [id]);
    if (R.alive()) paint(R);
  }, function (e) { toast(errMsg(e)); });
}
function doRemove(R) {
  var id = ST.key;
  Promise.resolve(ac(R, 'remove', [id])).then(function () {
    clearDraft(); ST.confirm = null; ST.key = null; ST.draft = null; ST.dirty = false;
    toast('Version supprimée.');
    if (R.alive()) paint(R);
  }, function (e) { toast(errMsg(e)); });
}
function copyForClaude(R) {
  var txt = LB.claudeText(ST.isNew ? ST.draft : LB.specForSave(ST.draft, dataset(R)), curInfo());
  function done(ok) { ST.copy = { text: txt, ok: ok }; if (R.alive()) paint(R); toast(ok ? 'Copié : identifiant et JSON de la version.' : 'Texte prêt à copier.'); }
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(txt).then(function () { done(true); }, function () { done(false); });
    else done(false);
  } catch (e) { done(false); }
}
function copyBox(R) {
  var c = ST.copy, items = [h('b', null, c.ok ? 'Copié. ' : 'Copie le texte ci-dessous. '), 'Colle-le dans ta conversation avec Claude, avec ce que tu veux changer, en mots. Claude sait écrire une stratégie à partir d’une description : il la vérifie (normalisation, lecture en français) et l’écrit en nouvelle version, qui apparaît dans cette liste.'];
  if (!c.ok) { var ta = h('textarea', { class: 'lb-ta', readonly: true, 'aria-label': 'Texte pour Claude' }); ta.value = c.text; items.push(ta); setTimeout(function () { try { ta.focus(); ta.select(); } catch (e) { /* rien */ } }, 0); }
  items.push(h('div', { class: 'row', style: 'margin-top:8px' }, U.button({ label: 'Fermer', kind: 'ghost', small: true, onClick: function () { ST.copy = null; paint(R); } })));
  return U.callout(items);
}

function stackSection(R, C) {
  var s = h('div', { class: 'lb-grp' }), ro = readOnly(), spec = ST.draft;
  if (spec && spec.mirror === false && isObj(spec.short) && isObj(spec.long) && spec.side !== 'long') {
    s.appendChild(U.seg({ options: [{ v: 'long', label: 'Règle d’achat' }, { v: 'short', label: 'Règle de vente' }], value: viewSide(), onChange: function (v) { ST.side = v; paint(R); } }));
  }
  C.general.warnings.slice(0, 2).forEach(function (t) { s.appendChild(h('p', { class: 'lb-wrn' }, t)); });
  C.list.forEach(function (c) { s.appendChild(cardEl(R, c, ro)); });
  return s;
}
function cardEl(R, c, ro) {
  var body = [];
  c.texts.forEach(function (t) { body.push(h('p', { class: 'lb-say' }, t)); });
  c.advanced.forEach(function (t) { body.push(h('p', { class: 'lb-adv' }, t)); });
  c.errors.forEach(function (t) { body.push(h('p', { class: 'lb-err' }, t)); });
  c.warnings.slice(0, 3).forEach(function (t) { body.push(h('p', { class: 'lb-wrn' }, t)); });
  if (c.warnings.length > 3) body.push(h('p', { class: 'lb-wrn' }, 'Et ' + plural(c.warnings.length - 3, 'autre remarque', 'autres remarques') + ' : voir le JSON.'));
  if (c.id === 'oos') body = body.concat(oosBody(R));
  if (c.edit && !ro) body.push(h('div', { class: 'lb-cf' }, U.button({ label: 'Modifier', kind: 'ghost', aria: 'Modifier : ' + c.title, onClick: function () { openPanel(R, c.id); } })));
  return U.card({ title: c.title, meta: c.errors.length ? plural(c.errors.length, 'erreur') : null, body: body });
}
function oosBody(R) {
  var spec = ST.draft, inst = spec.instrument || 'MNQ', o = ac(R, 'oos', [inst]), out = [];
  if (!o) { out.push(h('p', { class: 'lb-say' }, sentence('La coupure hors échantillon appartient à l’instrument (' + inst + ') : elle se fixe une fois, avec un jeu de données'))); return out; }
  if (o.fixed && o.oosFrom) {
    out.push(h('p', { class: 'lb-say' }, sentence('Coupure de ' + inst + ' fixée au ' + keyText(o.oosFrom) + '. Toutes les séances à partir de cette date sont hors échantillon, celles ajoutées plus tard aussi. Elle ne bouge plus')));
    return out;
  }
  out.push(h('p', { class: 'lb-say' }, sentence('Pas encore fixée pour ' + inst + '. Elle se pose une fois, au plus tard au premier lancement sur données réelles, et ne bouge plus ensuite')));
  if (!o.proposal) { out.push(h('p', { class: 'lb-wrn' }, sentence('Choisis un jeu de données dans l’en-tête pour obtenir une proposition'))); return out; }
  out.push(h('p', { class: 'lb-say' }, sentence('Proposition : ' + keyText(o.proposal) + ', qui laisse 30 % des séances après elle')));
  if (readOnly()) return out;
  var id = 'lbf' + (++FID), input = h('input', { id: id, type: 'date', value: o.proposal, autocomplete: 'off' });
  out.push(h('div', { class: 'fields' }, h('div', { class: 'fld' }, h('label', { for: id }, 'Première séance hors échantillon'), h('div', { class: 'in' }, input))));
  out.push(h('div', { class: 'lb-cf' }, U.button({ label: 'Fixer la coupure', kind: 'ghost', onClick: function () {
    var v = input.value;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) { toast('Date attendue : AAAA-MM-JJ.'); return; }
    Promise.resolve(ac(R, 'setOosFrom', [inst, v])).then(function (r) {
      if (r && r.ok === false) toast(r.why || 'Coupure refusée.'); else toast('Coupure fixée au ' + keyText(v) + '.');
      if (R.alive()) paint(R);
    }, function (e) { toast(errMsg(e)); });
  } })));
  return out;
}
function keyText(k) { var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(k || '')); return m ? m[3] + '/' + m[2] + '/' + m[1] : String(k || '—'); }

/* ---------- Aperçu ---------- */
function previewSection(R, C) {
  var ds = dataset(R), s = U.section('Aperçu sur une *séance*', ds && ds.meta && ds.meta.name ? String(ds.meta.name) : null), box = h('div', { class: 'lb-pv' });
  s.appendChild(box);
  if (!has(R.api, 'preview')) { box.appendChild(U.note('Aperçu indisponible ici.')); return s; }
  if (!ds) { box.appendChild(U.note('Choisis un jeu de données dans l’en-tête du Labo : l’aperçu montre la dernière séance de l’échantillon qui porte un signal, avec les séries que lit la règle.')); return s; }
  if (ds.ready === false) { box.appendChild(h('div', { class: 'lb-wait' }, h('i'), 'Le jeu se charge…')); return s; }
  if (C.errors) { box.appendChild(U.note('Corrige ' + (C.errors > 1 ? 'les erreurs' : 'l’erreur') + ' signalée' + (C.errors > 1 ? 's' : '') + ' dans les cartes pour voir l’aperçu.', true)); return s; }
  var spec = C.norm.spec, key = '';
  try { key = LSx().canonical(spec) + '|' + String((ds.meta && (ds.meta.fingerprint || ds.meta.id)) || ''); } catch (e) { key = String(Math.random()); }
  if (ST.prev.key === key && ST.prev.res) { drawPreview(box, ST.prev.res, spec); return s; }
  if (ST.prev.key === key && ST.prev.busy) { box.appendChild(h('div', { class: 'lb-wait' }, h('i'), 'Calcul de l’aperçu…')); return s; }
  ST.prev = { key: key, busy: true, res: null };
  box.appendChild(h('div', { class: 'lb-wait' }, h('i'), 'Calcul de l’aperçu…'));
  var p;
  try { p = Promise.resolve(R.api.preview(spec)); } catch (e) { p = Promise.reject(e); }
  p.then(function (res) {
    if (ST.prev.key !== key) return;
    ST.prev = { key: key, busy: false, res: res || { error: 'Aperçu vide.' } };
    if (box.isConnected) { drawPreview(box, ST.prev.res, spec); try { T.typoTree(box); } catch (e) { /* rien */ } }
  }, function (e) {
    if (ST.prev.key !== key) return;
    ST.prev = { key: key, busy: false, res: { error: errMsg(e) } };
    if (box.isConnected) drawPreview(box, ST.prev.res, spec);
  });
  return s;
}
function drawPreview(box, res, spec) {
  T.clear(box);
  if (!res || res.error) { box.appendChild(U.note(sentence('Aperçu impossible : ' + lowFirst(res && res.error ? String(res.error) : 'réponse vide')), true)); return; }
  var b = res.bars || {}, ts = b.t || [], tz = (spec.session && spec.session.tz) || 'Europe/Paris';
  if (!ts.length) { box.appendChild(U.note('Aucune barre dans la séance témoin.')); return; }
  var sig = res.signals || [], nL = sig.filter(function (x) { return x.side === 'long'; }).length, nS = sig.length - nL;
  var sigText = sig.length ? plural(sig.length, 'signal', 'signaux') + (nL && nS ? ' (' + nL + ' à l’achat, ' + nS + ' à la vente)' : nS ? ' à la vente' : ' à l’achat') : 'aucun signal';
  box.appendChild(h('p', { class: 'lb-pvh' }, h('b', null, 'Séance du ' + keyText(res.key)), ' · ' + sigText + (res.none ? ' dans les dernières séances de l’échantillon' : '')));
  function fmtT(t) { try { return T.time.hhmm(tz, new Date(t)); } catch (e) { return F.time(t); } }
  function ok(s) { return s && s.points && s.points.some(function (p) { return p[1] != null && isFinite(p[1]); }); }
  var lv = (res.series || []).filter(function (x) { return x.cls === 'niveau' && ok(x); }), other = (res.series || []).filter(function (x) { return x.cls !== 'niveau' && ok(x); });
  var TONES = [['violet', false], ['mute', true], ['violet', true], ['mute', false]];
  var series = [{ name: 'Clôture', points: ts.map(function (t, i) { return [t, b.c[i]]; }), tone: 'fg', width: 1.3 }].concat(lv.slice(0, 4).map(function (x, i) { return { name: x.name, points: x.points, tone: TONES[i][0], dash: TONES[i][1], width: 1.4 }; }));
  var span = (ts[ts.length - 1] - ts[0]) || 1, lastX = -Infinity, vl = [];
  sig.slice(0, 40).forEach(function (x) { var lab = x.t - lastX > span * 0.08 ? (x.side === 'long' ? '▲' : '▼') : ''; if (lab) lastX = x.t; vl.push({ x: x.t, label: lab }); });
  box.appendChild(T.chart.line({ series: series, x: { type: 'num', fmt: fmtT }, vlines: vl, height: 240 }));
  other.slice(0, 3).forEach(function (x) {
    box.appendChild(h('p', { class: 'lb-pvs' }, x.name + ' · ' + x.cls));
    box.appendChild(T.chart.line({ series: [{ name: x.name, points: x.points, tone: 'violet', width: 1.4 }], x: { type: 'num', fmt: fmtT }, vlines: vl.map(function (v) { return { x: v.x }; }), height: 120, legend: false }));
  });
  if (lv.length > 4 || other.length > 3) box.appendChild(U.note('Séries supplémentaires masquées : la règle en lit ' + (lv.length + other.length) + '.'));
  box.appendChild(U.note('Séries calculées par le moteur sur la séance témoin : la dernière de l’échantillon qui porte un signal. ▲ achat, ▼ vente, à la clôture de la barre du signal ; rien ne s’exécute avant la barre suivante. Heures : ' + (tz === 'Europe/Paris' ? 'Paris' : tz) + '.'));
  if (sig.length > 40) box.appendChild(U.note('Seuls les 40 premiers signaux sont marqués.'));
}

/* ================================================================================================
   12. Panneau plein écran (une couche fixe de la page, jamais une fenêtre du navigateur). Une pile de vues :
       le bloc, puis une condition, puis un opérande, à toute profondeur pour les opérandes. Les retouches
       portent sur une copie (work) ; « Appliquer » la verse dans le brouillon, « Annuler » la jette.
   ================================================================================================ */
var BLOCK_TITLE = { seance: 'Séance et ancrage', sens: 'Sens et miroir', contexte: 'Contexte', declencheur: 'Déclencheur', entree: 'Entrée', stop: 'Stop', objectif: 'Objectif', gestion: 'Gestion de la position', risque: 'Risque et coûts', parametres: 'Paramètres', hypothese: 'Hypothèse', json: 'Document JSON', seal: 'Sceller la version' };
var RULE_BLOCKS = { contexte: 1, declencheur: 1, entree: 1, stop: 1, objectif: 1 };
function openPanel(R, block) {
  if (readOnly()) return;
  var work = clone(ST.draft), side = viewSide();
  if (!isObj(work.params)) work.params = {};
  if (RULE_BLOCKS[block] && !isObj(work[side])) work[side] = LB.defaultRule();
  if (block === 'gestion' && !isObj(work.manage)) work.manage = {};
  if (block === 'seance' && !isObj(work.session)) work.session = {};
  if (block === 'risque') { if (!isObj(work.risk)) work.risk = {}; if (!isObj(work.costs)) work.costs = {}; }
  ST.panel = { block: block, work: work, before: clone(ST.draft), side: side, stack: [{ v: 'block', title: BLOCK_TITLE[block] || block }] };
  showOverlay(R);
}
function openJson(R) {
  ST.panel = { block: 'json', work: clone(ST.draft), before: clone(ST.draft), side: viewSide(), text: JSON.stringify(ST.isNew ? ST.draft : LB.specForSave(ST.draft, dataset(R)), null, 2), check: null, stack: [{ v: 'json', title: BLOCK_TITLE.json }] };
  showOverlay(R);
}
function openSeal(R) {
  ST.panel = { block: 'seal', work: clone(ST.draft), before: clone(ST.draft), side: viewSide(), stack: [{ v: 'seal', title: BLOCK_TITLE.seal }], why: null, busy: false };
  showOverlay(R);
}
function showOverlay(R) {
  if (typeof document === 'undefined') return;
  OV.R = R;
  if (!OV.el) {
    OV.el = h('div', { class: 'lb-ov', role: 'dialog', 'aria-modal': 'true' });
    OV.el.addEventListener('keydown', function (e) { if (e.key !== 'Escape' || !ST.panel || !OV.R) return; e.preventDefault(); if (ST.panel.stack.length > 1) pop(OV.R); else closePanel(OV.R); });
    document.body.appendChild(OV.el);
  }
  document.documentElement.classList.add('lb-lock');
  paintOverlay(R);
}
function removeOverlay() {
  if (OV.el && OV.el.parentNode) OV.el.parentNode.removeChild(OV.el);
  OV.el = null; OV.body = null; OV.foot = null; OV.say = null; OV.sayFn = null;
  if (typeof document !== 'undefined') document.documentElement.classList.remove('lb-lock');
}
function closePanel(R) { ST.panel = null; removeOverlay(); if (R.alive()) paint(R); }
function topView() { var P = ST.panel; return P ? P.stack[P.stack.length - 1] : null; }
function push(R, view) { var top = topView(); if (top && OV.body) top.scroll = OV.body.scrollTop; ST.panel.stack.push(view); paintOverlay(R); }
function pop(R) { if (ST.panel.stack.length > 1) ST.panel.stack.pop(); paintOverlay(R); }
function repaint(R) { var top = topView(); if (top && OV.body) top.scroll = OV.body.scrollTop; paintOverlay(R); }
/* Après une retouche : structurelle (un type a changé) → la vue est redessinée ; sinon seuls la phrase et le pied. */
function edited(R, structural) {
  if (structural) { repaint(R); return; }
  if (OV.say && OV.sayFn) { try { OV.say.textContent = OV.sayFn(); } catch (e) { /* rien */ } }
  paintFoot(R);
}
function paintOverlay(R) {
  var P = ST.panel;
  if (!P || !OV.el) return;
  var top = P.stack[P.stack.length - 1], deep = P.stack.length > 1;
  T.clear(OV.el); OV.say = null; OV.sayFn = null;
  var crumbs = P.stack.map(function (s) { return s.title; }).filter(Boolean);
  OV.el.appendChild(h('div', { class: 'lb-ovh' },
    U.button({ label: deep ? '‹' : '✕', kind: 'ghost', aria: deep ? 'Retour' : 'Fermer sans appliquer', onClick: function () { if (deep) pop(R); else closePanel(R); } }),
    h('div', { class: 't' }, crumbs.length > 1 ? h('small', null, crumbs.slice(0, -1).join(' › ')) : h('small', null, ST.draft && ST.draft.name ? ST.draft.name : 'Stratégie'), h('b', null, top.title || ''))));
  var inner = h('div', { class: 'lb-ovi' });
  OV.body = h('div', { class: 'lb-ovb' }, inner);
  OV.foot = h('div', { class: 'lb-ovf' });
  OV.el.appendChild(OV.body); OV.el.appendChild(OV.foot);
  try { (VIEWS[top.v] || VIEWS.block)(R, P, top, inner); }
  catch (e) { if (typeof console !== 'undefined') console.error(e); inner.appendChild(h('p', { class: 'lb-adv' }, 'Cette forme ne s’édite pas ici : ' + errMsg(e) + ' ' + LB.ADVANCED)); }
  paintFoot(R);
  try { T.typoTree(OV.el); } catch (e) { /* rien */ }
  OV.body.scrollTop = top.scroll || 0;
}
function blockCard(P, ds) {
  var c = null;
  try { c = LB.cards(P.work, { side: P.side, dataset: ds }); } catch (e) { return null; }
  var id = P.block === 'risque' ? 'risque' : P.block;
  for (var i = 0; i < c.list.length; i++) if (c.list[i].id === id) return { card: c.list[i], all: c };
  return null;
}
function paintFoot(R) {
  var P = ST.panel, f = OV.foot;
  if (!P || !f) return;
  T.clear(f);
  var top = topView();
  if (FOOTS[top.v]) { FOOTS[top.v](R, P, f); return; }
  var bc = blockCard(P, dataset(R)), live = h('div', { class: 'lb-live', 'aria-live': 'polite' });
  if (bc) {
    bc.card.texts.forEach(function (t) { live.appendChild(h('p', null, t)); });
    bc.card.errors.forEach(function (t) { live.appendChild(h('p', { class: 'lb-err' }, t)); });
  }
  f.appendChild(live);
  f.appendChild(h('div', { class: 'lb-fb' }, U.button({ label: 'Annuler', kind: 'ghost', onClick: function () { closePanel(R); } }), U.button({ label: 'Appliquer', kind: 'pri', onClick: function () { applyPanel(R); } })));
  try { T.typoTree(f); } catch (e) { /* rien */ }
}
function applyPanel(R) {
  var P = ST.panel, w = P.work;
  if (PARAM_BLOCKS[P.block]) LB.parametrize(w, P.block, P.side);
  LB.pruneDropped(P.before, w);
  var L = LSx(), changed = L.canonical(w) !== L.canonical(ST.draft);
  if (changed) { ST.draft = w; ST.dirty = true; storeDraft(); }
  ST.panel = null; removeOverlay();
  if (changed) toast('Appliqué. Rien n’est écrit avant « Enregistrer ».');
  if (R.alive()) paint(R);
}

/* ---------- Champs ---------- */
function chipGroup(o) {
  var box = h('div', { class: 'lb-chips', role: 'group', 'aria-label': o.label || null });
  (o.options || []).forEach(function (op) {
    var on = o.multi ? (o.value || []).indexOf(op.v) >= 0 : op.v === o.value;
    box.appendChild(h('button', { class: 'chip', type: 'button', 'aria-pressed': String(on), disabled: op.disabled || null, title: op.title || null, on: { click: function () { o.onPick(op.v, !on); } } }, op.label));
  });
  return h('div', { class: 'fld full lb-grp', style: 'gap:6px' }, o.label ? h('span', { class: 'lb-lab' }, o.label) : null, box, o.hint ? h('span', { class: 'hint' }, o.hint) : null);
}
function numText(v) { return v == null || v === '' ? '' : isNum(v) ? String(v).replace('.', ',') : String(v); }
/* Champ numérique : accepte la virgule, « $nom » pour relier un paramètre existant, vide si permis. */
function numField(o) {
  var id = 'lbf' + (++FID);
  function shown() { var v = o.get(); if (isRef(v)) { var p = o.params && o.params()[v.slice(1)]; return p && isNum(p.v) ? numText(p.v) : ''; } return numText(v); }
  var input = h('input', { id: id, type: 'text', inputmode: 'decimal', autocomplete: 'off', placeholder: o.placeholder != null ? numText(o.placeholder) : null, value: shown() });
  var hint = h('span', { class: 'hint' }, o.hint ? o.hint() : '');
  input.addEventListener('change', function () {
    var t = input.value.trim();
    if (t === '') { if (o.allowEmpty) { o.set(null); hint.textContent = o.hint ? o.hint() : ''; } else input.value = shown(); return; }
    if (t.charAt(0) === '$') {
      var nm = t.slice(1);
      if (o.params && own(o.params(), nm)) { o.set('$' + nm); input.value = shown(); hint.textContent = o.hint ? o.hint() : ''; }
      else { input.value = shown(); toast('Paramètre « ' + nm + ' » inconnu.'); }
      return;
    }
    var x = F.parse(t);
    if (!isFinite(x)) { input.value = shown(); toast('Un nombre est attendu.'); return; }
    o.set(x); input.value = shown(); hint.textContent = o.hint ? o.hint() : '';
  });
  return h('div', { class: 'fld' }, h('label', { for: id }, o.label), h('div', { class: 'in' }, input, o.unit ? h('span', { class: 'u' }, o.unit) : null), hint);
}
function textField(o) {
  var id = 'lbf' + (++FID), input = o.area ? h('textarea', { id: id, placeholder: o.placeholder || null }) : h('input', { id: id, type: o.type || 'text', autocomplete: 'off', placeholder: o.placeholder || null });
  input.value = o.value == null ? '' : o.value;
  input.addEventListener('change', function () { o.set(input.value); });
  return h('div', { class: 'fld' + (o.full ? ' full' : '') }, h('label', { for: id }, o.label), h('div', { class: 'in' + (o.area ? ' ta' : '') }, input), o.hint ? h('span', { class: 'hint' }, o.hint) : null);
}
function selectField(o) {
  var id = 'lbf' + (++FID), sel = h('select', { id: id });
  o.options.forEach(function (op) { sel.appendChild(h('option', { value: String(op.v), selected: String(op.v) === String(o.value) || null }, op.label)); });
  sel.addEventListener('change', function () { var op = o.options.filter(function (x) { return String(x.v) === sel.value; })[0]; o.set(op ? op.v : sel.value); });
  return h('div', { class: 'fld' }, h('label', { for: id }, o.label), h('div', { class: 'in' }, sel), o.hint ? h('span', { class: 'hint' }, o.hint) : null);
}
function paramHint(P, path, param, f) {
  return function () {
    var cur = getAt(P.work, path);
    if (isRef(cur)) { var nm = cur.slice(1), n = LB.useCount(P.work, nm); return 'paramètre « ' + nm + ' »' + (n > 1 ? ', partagé par ' + n + ' champs' : ''); }
    if (cur == null) return f && f.def != null ? 'vide : ' + fmtV(f.def) + ' par défaut' : f && f.nullable ? 'vide : aucun' : '';
    return param ? 'deviendra un paramètre nommé' : '';
  };
}
var SMALL = { number: 1, time: 1, select: 1, tz: 1 };
function argsEl(R, P, args, base, owner, param, filter) {
  var obj = getAt(P.work, base) || {}, fs = LB.fieldsFor(args, obj, owner), box = h('div', { class: 'lb-grp' }), grid = null;
  fs.forEach(function (f) {
    if (f.hidden || (filter && !filter(f))) return;
    var el = fieldEl(R, P, f, base, owner, param);
    if (!el) return;
    if (SMALL[f.widget]) { if (!grid) { grid = h('div', { class: 'fields' }); box.appendChild(grid); } grid.appendChild(el); }
    else { grid = null; box.appendChild(el); }
  });
  return box;
}
var TZ_LABEL = { 'Europe/Paris': 'Paris', 'America/New_York': 'New York', 'America/Chicago': 'Chicago', 'Europe/London': 'Londres', UTC: 'UTC' };
var DAY_OPTS = [[1, 'lun'], [2, 'mar'], [3, 'mer'], [4, 'jeu'], [5, 'ven'], [6, 'sam'], [7, 'dim']];
function fieldEl(R, P, f, base, owner, param) {
  var w = P.work, path = base.concat(f.path), v = getAt(w, path);
  function set(x) { setAt(P.work, path, x); }
  switch (f.widget) {
    case 'number':
      return numField({ label: f.label, unit: f.unit, placeholder: f.def, get: function () { return getAt(P.work, path); }, params: function () { return P.work.params || {}; },
        allowEmpty: f.nullable || !f.req, hint: paramHint(P, path, param, f),
        set: function (x) {
          if (x === null) set(f.nullable ? null : undefined);
          else if (typeof x === 'string') set(x);
          else if (param) LB.setNumber(P.work, path, x, owner, f.arg);
          else set(x);
          edited(R, false);
        } });
    case 'time':
      return (function () {
        var id = 'lbf' + (++FID), input = h('input', { id: id, type: 'time', value: typeof v === 'string' ? v : '' });
        input.addEventListener('change', function () { var t = input.value; if (!t) { if (!f.req) set(undefined); else input.value = getAt(P.work, path) || ''; } else set(t.slice(0, 5)); edited(R, false); });
        return h('div', { class: 'fld' }, h('label', { for: id }, f.label), h('div', { class: 'in' }, input), !f.req && f.def ? h('span', { class: 'hint' }, 'vide : ' + f.def) : null);
      })();
    case 'timePair':
      return (function () {
        var cur = Array.isArray(v) ? v.slice() : ['09:30', '10:30'], ids = ['lbf' + (++FID), 'lbf' + (++FID)];
        var ins = [0, 1].map(function (k) { var x = h('input', { id: ids[k], type: 'time', value: cur[k] || '' }); x.addEventListener('change', function () { if (!x.value) { x.value = cur[k]; return; } cur[k] = x.value.slice(0, 5); set(cur.slice()); edited(R, false); }); return x; });
        return h('div', { class: 'fld full lb-grp', style: 'gap:6px' }, h('span', { class: 'lb-lab' }, f.label), h('div', { class: 'fields' },
          h('div', { class: 'fld' }, h('label', { for: ids[0] }, 'De'), h('div', { class: 'in' }, ins[0])), h('div', { class: 'fld' }, h('label', { for: ids[1] }, 'À (exclu)'), h('div', { class: 'in' }, ins[1]))));
      })();
    case 'chips':
      return chipGroup({ label: f.label, options: f.options, value: v === undefined ? (f.def !== undefined ? f.def : f.init) : v, onPick: function (x) { set(x); edited(R, true); } });
    case 'select':
      return selectField({ label: f.label, options: f.options, value: v === undefined ? f.def : v, set: function (x) { set(x); edited(R, true); } });
    case 'tz':
      return (function () {
        var opts = []; if (f.def === null || !f.req) opts.push({ v: '', label: f.def === null ? 'Celui de la séance' : 'Par défaut' });
        (f.options || []).forEach(function (o) { opts.push({ v: o.v, label: o.label }); });
        if (typeof v === 'string' && v && !opts.some(function (o) { return o.v === v; })) opts.push({ v: v, label: v });
        return selectField({ label: f.label, options: opts, value: v == null ? (f.def === null ? '' : f.def) : v, set: function (x) { set(x === '' ? undefined : x); edited(R, false); } });
      })();
    case 'bool':
      return h('div', { class: 'fld full lb-grp', style: 'gap:6px' }, h('span', { class: 'lb-lab' }, f.label), U.seg({ options: [{ v: false, label: 'Non' }, { v: true, label: 'Oui' }], value: v == null ? !!f.def : !!v, onChange: function (x) { set(x); edited(R, true); } }));
    case 'operand':
      return operandRow(R, P, f, path);
    case 'cond':
      return condRow(R, P, path, f.label, null);
    case 'conds':
      return condsList(R, P, path, f.label);
    case 'name':
      return (function () {
        var tf = textField({ label: f.label, value: typeof v === 'string' ? v : '', set: function (x) { x = String(x || '').trim(); set(x || undefined); edited(R, true); } });
        var hints = (f.options || []).map(function (n) { return { v: n, label: n }; });
        return h('div', { class: 'lb-grp' }, tf, chipGroup({ label: 'Noms courants', options: hints, value: v, onPick: function (x) { set(x); edited(R, true); } }));
      })();
    case 'names':
      return (function () {
        var cur = Array.isArray(v) ? v.slice() : [], hints = (f.options || []).slice();
        var extra = cur.filter(function (n) { return hints.indexOf(n) < 0; });
        var chips = chipGroup({ label: f.label, multi: true, options: hints.map(function (n) { return { v: n, label: n }; }), value: cur, hint: cur.length ? null : 'Aucun nom choisi : tous les niveaux de la séance comptent.',
          onPick: function (x, on) { var c = (getAt(P.work, path) || []).slice(); if (on) { if (c.indexOf(x) < 0) c.push(x); } else c = c.filter(function (y) { return y !== x; }); set(c.length ? c : undefined); edited(R, true); } });
        var tf = textField({ label: 'Autres noms, séparés par des virgules', value: extra.join(', '), set: function (txt) {
          var base0 = (getAt(P.work, path) || []).filter(function (n) { return hints.indexOf(n) >= 0; });
          String(txt || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean).forEach(function (n) { if (base0.indexOf(n) < 0) base0.push(n); });
          set(base0.length ? base0 : undefined); edited(R, true);
        } });
        return h('div', { class: 'lb-grp' }, chips, tf);
      })();
    case 'barsOrTime':
      return (function () {
        var isTime = typeof v === 'string' && !isRef(v);
        var seg = U.seg({ options: [{ v: 'bars', label: 'En barres' }, { v: 'time', label: 'Jusqu’à une heure' }], value: isTime ? 'time' : 'bars', onChange: function (m) { set(m === 'time' ? '10:00' : 1); edited(R, true); } });
        var inner = isTime ? fieldEl(R, P, { widget: 'time', path: [], label: 'Heure (fin de validité)', req: true }, path, owner, false)
          : numField({ label: 'Barres', unit: 'barres', get: function () { return getAt(P.work, path); }, params: function () { return P.work.params || {}; }, allowEmpty: false, hint: paramHint(P, path, param, f),
            set: function (x) { if (typeof x === 'string') set(x); else if (param) LB.setNumber(P.work, path, x, owner, f.arg); else set(x); edited(R, false); } });
        return h('div', { class: 'fld full lb-grp', style: 'gap:6px' }, h('span', { class: 'lb-lab' }, f.label), seg, h('div', { class: 'fields' }, inner));
      })();
    case 'days':
      return chipGroup({ label: f.label, multi: true, options: DAY_OPTS.map(function (d) { return { v: d[0], label: d[1] }; }), value: Array.isArray(v) ? v : (f.def || []),
        onPick: function (x, on) { var c = (Array.isArray(getAt(P.work, path)) ? getAt(P.work, path) : (f.def || [])).slice(); if (on) { if (c.indexOf(x) < 0) c.push(x); } else c = c.filter(function (y) { return y !== x; }); if (!c.length) { toast('Garde au moins un jour.'); return; } c.sort(function (a, b) { return a - b; }); set(c); edited(R, true); } });
  }
  return h('p', { class: 'lb-adv' }, f.label + ' : ' + lowFirst(LB.ADVANCED));
}
function itemActions(btns) { return h('div', { class: 'lb-ia' }, btns.filter(Boolean)); }
function operandSay(spec, path) {
  var x = getAt(spec, path), L = LSx(), cls = '';
  try { cls = L.classOf(x); } catch (e) { cls = ''; }
  return sentence(LB.shortName(x, spec.params) + ' — ' + L.reader(spec.params).op(x) + (cls ? ' (classe : ' + cls + ')' : ''));
}
function operandRow(R, P, f, path) {
  var x = getAt(P.work, path), isDef = x === undefined, shown = isDef ? f.def : x, L = LSx(), cls = '';
  try { cls = shown === undefined ? '' : L.classOf(shown); } catch (e) { cls = 'refusé'; }
  var txt = shown === undefined ? 'Non renseigné.' : sentence((isDef ? 'Par défaut : ' : '') + L.reader(P.work.params).op(shown));
  var btns = [U.button({ label: 'Modifier', kind: 'ghost', small: true, onClick: function () { if (getAt(P.work, path) === undefined) setAt(P.work, path, clone(f.def !== undefined ? f.def : f.init)); push(R, { v: 'operand', path: path, title: f.label, cls: f.cls }); } })];
  if (!isDef && f.omit && f.def !== undefined) btns.push(U.button({ label: 'Revenir au défaut', kind: 'ghost', small: true, onClick: function () { setAt(P.work, path, undefined); edited(R, true); } }));
  return h('div', { class: 'lb-item' }, h('span', { class: 'lb-lab' }, f.label, cls ? h('span', { class: 'lb-cls' }, cls) : null), h('p', { class: 'lb-itx' }, txt), itemActions(btns));
}
function condText(spec, c) { try { return sentence(LSx().reader(spec.params).cond(c)); } catch (e) { return 'Condition non reconnue.'; } }
function condRow(R, P, path, label, list) {
  var c = getAt(P.work, path), ok = LB.editable(c, false);
  var btns = [];
  if (list) {
    var i = path[path.length - 1], lp = path.slice(0, -1), arr = getAt(P.work, lp) || [];
    btns.push(U.button({ label: '↑', kind: 'ghost', small: true, aria: 'Monter', disabled: i === 0, onClick: function () { var a = getAt(P.work, lp); var t = a[i - 1]; a[i - 1] = a[i]; a[i] = t; edited(R, true); } }));
    btns.push(U.button({ label: '↓', kind: 'ghost', small: true, aria: 'Descendre', disabled: i >= arr.length - 1, onClick: function () { var a = getAt(P.work, lp); var t = a[i + 1]; a[i + 1] = a[i]; a[i] = t; edited(R, true); } }));
  }
  if (ok) btns.push(U.button({ label: 'Modifier', kind: 'ghost', small: true, onClick: function () { push(R, { v: 'cond', path: path, title: label, simpleOnly: true }); } }));
  if (list && list.removable) btns.push(U.button({ label: 'Supprimer', kind: 'ghost', small: true, onClick: function () { var a = getAt(P.work, path.slice(0, -1)); a.splice(path[path.length - 1], 1); edited(R, true); } }));
  return h('div', { class: 'lb-item' }, h('span', { class: 'lb-lab' }, label), h('p', { class: 'lb-itx' }, condText(P.work, c)), ok ? null : h('p', { class: 'lb-adv' }, LB.ADVANCED), itemActions(btns));
}
function condsList(R, P, path, label) {
  var arr = getAt(P.work, path), box = h('div', { class: 'lb-grp' }, h('span', { class: 'lb-lab' }, label));
  if (!Array.isArray(arr)) { setAt(P.work, path, [clone(DEFAULT_COND)]); arr = getAt(P.work, path); }
  arr.forEach(function (_, i) { box.appendChild(condRow(R, P, path.concat([i]), 'Élément ' + (i + 1), { removable: arr.length > 1 })); });
  box.appendChild(h('div', { class: 'row' }, U.button({ label: 'Ajouter une condition', kind: 'ghost', onClick: function () { var a = getAt(P.work, path); a.push(LB.initCond('cmp')); push(R, { v: 'cond', path: path.concat([a.length - 1]), title: 'Élément ' + a.length, simpleOnly: true }); } })));
  return box;
}

/* ---------- Vues du panneau ---------- */
var CGROUPS = [
  { label: 'Prix et niveaux', keys: ['cmp', 'cross', 'touch', 'reject', 'break', 'bar'] },
  { label: 'Heure et calendrier', keys: ['time', 'news'] },
  { label: 'Regrouper ou nier (un seul niveau ici)', keys: ['all', 'any', 'not', 'for', 'within'], wrap: true }
];
function condEditor(R, P, el, path, o) {
  var c = getAt(P.work, path), key = condKey(c);
  var say = h('p', { class: 'lb-say lb-big' }, condText(P.work, c));
  OV.say = say; OV.sayFn = function () { return condText(P.work, getAt(P.work, path)); };
  el.appendChild(say);
  if (!key || !LB.editable(c, !o.simpleOnly)) {
    el.appendChild(h('p', { class: 'lb-adv' }, LB.ADVANCED + (o.simpleOnly && key && WRAP.indexOf(key) >= 0 ? ' L’interface n’édite qu’un niveau de regroupement.' : '')));
    el.appendChild(h('div', { class: 'row' }, U.button({ label: 'Remplacer par une condition simple', kind: 'ghost', onClick: function () { setAt(P.work, path, LB.initCond('cmp')); edited(R, true); } })));
    return;
  }
  CGROUPS.forEach(function (g) {
    if (g.wrap && o.simpleOnly) return;
    el.appendChild(chipGroup({ label: g.label, options: g.keys.map(function (k) { return { v: k, label: condDef(k).label }; }), value: key, onPick: function (k2) { if (k2 === key) return; setAt(P.work, path, LB.switchCond(getAt(P.work, path), k2)); edited(R, true); } }));
  });
  el.appendChild(argsEl(R, P, condDef(key).args, path, 'cond:' + key, true));
  if (key === 'news') el.appendChild(U.note('Lit la collection calendar (heure de Paris) que Claude remplit depuis tes captures. Une stratégie qui lit le calendrier n’a pas de marche synthétique de comparaison.'));
}
function allowedFor(o, cls) { return cls !== 'niveau' || o.cls === 'niveau' || o.cls === 'of' || o.cls === 'calcule' || o.cls === 'constante'; }
function slotParent(spec, path) { var par = getAt(spec, path.slice(0, -1)); if (condKey(par)) return 'cond'; if (isObj(par) && typeof par.type === 'string' && !own(par, 'f')) return 'order'; return 'operand'; }
function orderEditor(R, P, el, path, kind) {
  var x = getAt(P.work, path), sgn = P.side === 'short' ? -1 : 1;
  function say() { var y = getAt(P.work, path), Rd = LSx().reader(P.work.params); return sentence(kind === 'entry' ? (sgn > 0 ? 'Achat ' : 'Vente ') + Rd.entry(y, sgn) : kind === 'stop' ? 'Stop ' + Rd.stop(y, sgn) : y && y.type === 'none' ? 'Aucun objectif' : 'Objectif ' + Rd.target(y, sgn)); }
  var sayEl = h('p', { class: 'lb-say lb-big' }, say());
  OV.say = sayEl; OV.sayFn = say;
  el.appendChild(sayEl);
  el.appendChild(chipGroup({ label: 'Type', options: orderList(kind).map(function (o) { return { v: o.type, label: o.label }; }), value: isObj(x) ? x.type : null, onPick: function (t) { if (isObj(x) && x.type === t) return; setAt(P.work, path, LB.initOrder(kind, t)); edited(R, true); } }));
  var d = isObj(x) ? orderDef(kind, x.type) : null;
  if (!d) { el.appendChild(h('p', { class: 'lb-adv' }, 'Type non reconnu. ' + LB.ADVANCED)); return; }
  el.appendChild(argsEl(R, P, d.args, path, kind + ':' + x.type, true));
  if (kind === 'entry') el.appendChild(U.note('Le signal est connu à la clôture de sa barre ; rien ne s’exécute avant la barre suivante. Le glissement s’applique à l’entrée au marché, à l’ordre stop et à la limite déjà franchie (marketable), jamais à une limite remplie.'));
  if (kind === 'stop') el.appendChild(U.note('Le stop est fixé à l’exécution. Plus court que le stop minimal déclaré (carte Risque), le trade est annulé ; une exécution déjà au-delà du stop aussi.'));
  if (kind === 'target') el.appendChild(U.note('Un objectif déjà dépassé à l’exécution annule le trade. Sur une barre qui touche le stop et l’objectif, le remplissage déclaré décide (carte Risque et coûts).'));
}
var VIEWS = {
  block: function (R, P, top, el) {
    var w = P.work, G0 = GR(), side = P.side;
    switch (P.block) {
      case 'seance':
        el.appendChild(chipGroup({ label: 'Instrument', options: G0.instruments.map(function (o) { return { v: o.v, label: o.v + ' — ' + o.label }; }), value: w.instrument || 'MNQ', onPick: function (v) { w.instrument = v; edited(R, true); } }));
        el.appendChild(chipGroup({ label: 'Ancrage des grandeurs de séance', options: G0.anchors, value: w.anchor || 'globex', onPick: function (v) { w.anchor = v; edited(R, true); } }));
        el.appendChild(U.note('La séance est toujours la séance Globex. L’ancrage ne fixe que l’instant où VWAP, σ, range d’ouverture, heures fixes et minutes depuis l’ancre repartent de zéro.'));
        el.appendChild(h('p', { class: 'lb-sub' }, 'Fenêtre d’entrée'));
        el.appendChild(argsEl(R, P, G0.session, ['session'], 'session', false));
        el.appendChild(U.note('Les heures se lisent dans le fuseau choisi, séance par séance. Une fenêtre ou une sortie forcée qui chevauche l’ancre est refusée.'));
        return;
      case 'sens':
        el.appendChild(chipGroup({ label: 'Sens joués', options: G0.sides, value: w.side || 'long', onPick: function (v) { w.side = v; edited(R, true); } }));
        el.appendChild(h('div', { class: 'fld full lb-grp', style: 'gap:6px' }, h('span', { class: 'lb-lab' }, 'Vente en miroir de l’achat'),
          U.seg({ options: [{ v: true, label: 'Oui, en miroir' }, { v: false, label: 'Non, écrite à part' }], value: w.mirror !== false, onChange: function (v) { w.mirror = v; if (v) w.short = null; edited(R, true); } })));
        el.appendChild(U.note('Le miroir reflète les prix (p devient K − p) : les comparaisons s’inversent, un écart change de signe, un oscillateur x devient 100 − x. Un niveau comparé à un nombre fixe n’a pas de miroir.'));
        if (w.mirror === false && w.side !== 'long') {
          if (!isObj(w.short)) {
            el.appendChild(h('p', { class: 'lb-err' }, 'Sans miroir, la règle de vente doit être écrite.'));
            el.appendChild(h('div', { class: 'row' }, U.button({ label: 'Partir du miroir actuel', kind: 'ghost', onClick: function () {
              try { var m = LEx().mirror(Object.assign({}, w, { mirror: true }), 'spec'); w.short = m; edited(R, true); }
              catch (e) { w.short = LB.defaultRule(); toast('Miroir impossible : ' + errMsg(e) + ' Règle de vente neutre posée.'); edited(R, true); }
            } }), U.button({ label: 'Partir d’une règle neutre', kind: 'ghost', onClick: function () { w.short = LB.defaultRule(); edited(R, true); } })));
          } else el.appendChild(U.note('La règle de vente se modifie dans les cartes : choisis « Règle de vente » au-dessus de la pile.'));
        }
        return;
      case 'contexte': {
        if (!Array.isArray(w[side].setup)) w[side].setup = [];
        var list = w[side].setup;
        el.appendChild(U.note('Toutes ces conditions doivent être vraies (« et ») à la clôture de la barre du signal. Une condition peut regrouper des options, être niée ou tenue sur plusieurs barres, sur un seul niveau dans l’interface.'));
        if (!list.length) el.appendChild(h('p', { class: 'lb-say' }, 'Aucune condition : le déclencheur suffit.'));
        list.forEach(function (c, i) {
          var p = [side, 'setup', i], ok = LB.editable(c, true);
          el.appendChild(h('div', { class: 'lb-item' }, h('span', { class: 'lb-lab' }, 'Condition ' + (i + 1)), h('p', { class: 'lb-itx' }, condText(w, c)), ok ? null : h('p', { class: 'lb-adv' }, LB.ADVANCED),
            itemActions([
              U.button({ label: '↑', kind: 'ghost', small: true, aria: 'Monter', disabled: i === 0, onClick: function () { var t = list[i - 1]; list[i - 1] = list[i]; list[i] = t; edited(R, true); } }),
              U.button({ label: '↓', kind: 'ghost', small: true, aria: 'Descendre', disabled: i === list.length - 1, onClick: function () { var t = list[i + 1]; list[i + 1] = list[i]; list[i] = t; edited(R, true); } }),
              ok ? U.button({ label: 'Modifier', kind: 'ghost', small: true, onClick: function () { push(R, { v: 'cond', path: p, title: 'Condition ' + (i + 1), simpleOnly: false }); } }) : null,
              U.button({ label: 'Supprimer', kind: 'ghost', small: true, onClick: function () { list.splice(i, 1); edited(R, true); } })
            ])));
        });
        el.appendChild(h('div', { class: 'row' }, U.button({ label: 'Ajouter une condition', kind: 'ghost', onClick: function () { list.push(LB.initCond('cmp')); push(R, { v: 'cond', path: [side, 'setup', list.length - 1], title: 'Condition ' + list.length, simpleOnly: false }); } })));
        return;
      }
      case 'declencheur':
        if (w[side].trigger == null) w[side].trigger = clone(DEFAULT_COND);
        condEditor(R, P, el, [side, 'trigger'], { simpleOnly: false });
        return;
      case 'entree': orderEditor(R, P, el, [side, 'entry'], 'entry'); return;
      case 'stop': orderEditor(R, P, el, [side, 'stop'], 'stop'); return;
      case 'objectif': orderEditor(R, P, el, [side, 'target'], 'target'); return;
      case 'gestion': {
        var M = G0.manage, m = w.manage;
        if (isNum(m.breakeven) || isRef(m.breakeven)) m.breakeven = { r: m.breakeven };
        el.appendChild(h('div', { class: 'fld full lb-grp', style: 'gap:6px' }, h('span', { class: 'lb-lab' }, M.breakeven.label),
          U.seg({ options: [{ v: false, label: 'Non' }, { v: true, label: 'Oui' }], value: isObj(m.breakeven), onChange: function (v) { m.breakeven = v ? LB.initManage('breakeven') : null; edited(R, true); } })));
        if (isObj(m.breakeven)) el.appendChild(argsEl(R, P, M.breakeven.args, ['manage', 'breakeven'], 'breakeven', true));
        el.appendChild(h('div', { class: 'fld full lb-grp', style: 'gap:6px' }, h('span', { class: 'lb-lab' }, M.trail.label),
          U.seg({ options: [{ v: false, label: 'Non' }, { v: true, label: 'Oui' }], value: isObj(m.trail), onChange: function (v) { m.trail = v ? LB.initManage('trail') : null; edited(R, true); } })));
        if (isObj(m.trail)) el.appendChild(argsEl(R, P, M.trail.args, ['manage', 'trail'], 'trail', true));
        el.appendChild(argsEl(R, P, M.args, ['manage'], 'manage', true));
        el.appendChild(U.note('Les mises à jour valent pour la barre suivante, jamais pour la courante. Break-even et suiveur se lisent sur le plus haut à l’achat, sur le plus bas à la vente.'));
        return;
      }
      case 'risque': {
        var mode = w.risk.mode || 'contracts', set0 = (R.ctx && R.ctx.settings) || {};
        el.appendChild(h('p', { class: 'lb-sub' }, 'Taille'));
        el.appendChild(argsEl(R, P, G0.risk, ['risk'], 'risk', false, function (f) { return f.k === 'mode' || (mode === 'risk' ? f.k === 'riskUsd' || f.k === 'maxQty' : f.k === 'contracts'); }));
        el.appendChild(h('p', { class: 'lb-sub' }, 'Limites par séance'));
        el.appendChild(argsEl(R, P, G0.risk, ['risk'], 'risk', false, function (f) { return ['minStopTicks', 'maxPerSession', 'maxLossesPerSession', 'dailyStopUsd', 'cooldown'].indexOf(f.k) >= 0; }));
        el.appendChild(h('p', { class: 'lb-sub' }, 'Coûts'));
        el.appendChild(argsEl(R, P, G0.costs, ['costs'], 'costs', false));
        if (isNum(set0.commissionRT)) el.appendChild(U.note('Commission de tes réglages : ' + F.num(set0.commissionRT, 2, '$') + ' aller-retour. Laissée vide, c’est elle qui compte, figée au scellement. Le verdict se calcule à des coûts au moins égaux à tes réglages et à 1 tick par jambe glissée.'));
        el.appendChild(h('p', { class: 'lb-sub' }, 'Remplissage'));
        el.appendChild(chipGroup({ label: 'Barre qui touche le stop et l’objectif', options: G0.fills, value: w.fill || 'pessimiste', onPick: function (v) { w.fill = v; edited(R, true); } }));
        return;
      }
      case 'parametres': return viewParams(R, P, el);
      case 'hypothese':
        el.appendChild(textField({ label: 'Nom de la stratégie', value: w.name || '', full: true, set: function (x) { w.name = String(x || ''); edited(R, false); } }));
        el.appendChild(textField({ label: 'Hypothèse', area: true, full: true, value: w.hypothesis || '', placeholder: 'Pourquoi un avantage existerait ici, et ce qui le réfuterait.', set: function (x) { w.hypothesis = String(x || ''); edited(R, false); } }));
        el.appendChild(U.note('Écrite avant les résultats, l’hypothèse dit ce qu’on cherche : un mécanisme, et le résultat qui le réfuterait. Elle est exigée pour sceller et entre dans le document, pas dans le hachage.'));
        return;
    }
    el.appendChild(h('p', { class: 'lb-adv' }, LB.ADVANCED));
  },
  cond: function (R, P, top, el) { condEditor(R, P, el, top.path, { simpleOnly: !!top.simpleOnly }); },
  operand: function (R, P, top, el) {
    var path = top.path, x = getAt(P.work, path), k = opKind(x), d = k ? opDef(k) : null;
    var say = h('p', { class: 'lb-say lb-big' }, operandSay(P.work, path));
    OV.say = say; OV.sayFn = function () { return operandSay(P.work, path); };
    el.appendChild(say);
    if (top.cls === 'niveau' && k) { var c0 = ''; try { c0 = LSx().classOf(x); } catch (e) { c0 = ''; } if (c0 && c0 !== 'niveau' && c0 !== 'constante') el.appendChild(h('p', { class: 'lb-err' }, 'Un niveau (un prix) est attendu ici ; celui-ci est de classe ' + c0 + '.')); }
    var grp = top.grp || (d ? d.group : 'prix');
    el.appendChild(chipGroup({ label: 'Famille', options: GR().groups, value: grp, onPick: function (g) { top.grp = g; repaint(R); } }));
    el.appendChild(chipGroup({ label: 'Opérande', options: GR().operands.filter(function (o) { return o.group === grp && allowedFor(o, top.cls); }).map(function (o) { return { v: o.f, label: o.label }; }), value: k,
      onPick: function (f2) { if (f2 === k) return; setAt(P.work, path, LB.initOperand(f2)); top.grp = opDef(f2).group; edited(R, true); } }));
    if (!k) { el.appendChild(h('p', { class: 'lb-adv' }, 'Opérande non reconnu. ' + LB.ADVANCED)); return; }
    if (k === 'const') {
      var owner = 'const:' + slotParent(P.work, path), arg = opDef('const').args[0];
      el.appendChild(h('div', { class: 'fields' }, numField({ label: 'Valeur', get: function () { return getAt(P.work, path); }, params: function () { return P.work.params || {}; }, allowEmpty: false, hint: paramHint(P, path, true, null),
        set: function (v) { if (typeof v === 'string') setAt(P.work, path, v); else LB.setNumber(P.work, path, v, owner, arg); edited(R, false); } })));
      el.appendChild(U.note('Tape « $nom » pour relier un paramètre existant. Un niveau comparé à un nombre fixe n’a pas de miroir.'));
      return;
    }
    if (d.args.length) el.appendChild(argsEl(R, P, d.args, path, 'operand:' + k, true));
    else el.appendChild(h('p', { class: 'lb-wrn' }, 'Cet opérande n’a pas de réglage.'));
  },
  json: function (R, P, top, el) {
    var ro = readOnly();
    el.appendChild(U.note('Le document complet de la version, celui que Claude lit et écrit. ' + (ro ? 'Version scellée : lecture seule.' : 'Modifie-le ou colle une version reçue, puis « Valider » : les erreurs s’affichent en clair. « Appliquer » remplace ce que montre l’éditeur ; rien n’est enregistré avant « Enregistrer ». L’identité de la version (id, version, état) est gardée.')));
    var ta = h('textarea', { class: 'lb-json', spellcheck: 'false', autocapitalize: 'off', autocomplete: 'off', 'aria-label': 'Document JSON de la stratégie', readonly: ro || null });
    ta.value = P.text;
    ta.addEventListener('input', function () { P.text = ta.value; if (P.check) { P.check = null; paintRes(); paintFoot(R); } });
    el.appendChild(ta);
    var res = h('div', { class: 'lb-grp' });
    function paintRes() {
      T.clear(res);
      var c = P.check;
      if (!c) return;
      if (c.errors.length) { res.appendChild(h('p', { class: 'lb-sub' }, plural(c.errors.length, 'erreur'))); c.errors.forEach(function (m) { res.appendChild(h('p', { class: 'lb-err' }, LB.humanize(m).text)); }); }
      else res.appendChild(h('p', { class: 'lb-say' }, 'Aucune erreur : le document est valide.'));
      var ws = c.warnings.filter(function (m) { return !/^(sid|id) : /.test(m); });
      if (ws.length) { res.appendChild(h('p', { class: 'lb-sub' }, plural(ws.length, 'remarque'))); ws.slice(0, 8).forEach(function (m) { res.appendChild(h('p', { class: 'lb-wrn' }, LB.humanize(m).text)); }); }
      if (c.ok) { res.appendChild(h('p', { class: 'lb-sub' }, 'Lecture')); try { LSx().describe(c.spec).forEach(function (b) { res.appendChild(h('p', { class: 'lb-say' }, b.text)); }); } catch (e) { /* rien */ } }
      try { T.typoTree(res); } catch (e) { /* rien */ }
    }
    var btns = [];
    if (!ro && typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.readText) btns.push(U.button({ label: 'Coller', kind: 'ghost', onClick: function () { navigator.clipboard.readText().then(function (t) { ta.value = t; P.text = t; P.check = null; paintRes(); paintFoot(R); }, function () { toast('Presse-papiers fermé : colle avec le menu du système.'); }); } }));
    btns.push(U.button({ label: 'Copier', kind: 'ghost', onClick: function () { try { navigator.clipboard.writeText(ta.value).then(function () { toast('JSON copié.'); }, function () { ta.focus(); ta.select(); toast('Texte sélectionné.'); }); } catch (e) { ta.focus(); ta.select(); } } }));
    btns.push(U.button({ label: 'Valider', kind: ro ? 'ghost' : 'pri', onClick: function () { P.check = LB.parseJson(ta.value, ST.isNew ? ST.draft : ST.base, dataset(R)); P.check.text = ta.value; paintRes(); paintFoot(R); } }));
    el.appendChild(h('div', { class: 'lb-acts' }, btns));
    el.appendChild(res);
    paintRes();
  },
  seal: function (R, P, top, el) {
    var ds = dataset(R), n = LSx().normalize(ST.draft, dsCtx(ds)), s = n.spec || {}, inst = s.instrument || 'MNQ', o = ac(R, 'oos', [inst]) || {};
    var hyp = typeof s.hypothesis === 'string' && s.hypothesis.trim().length > 0, valid = !n.errors.length, cut = !!(o.fixed && o.oosFrom) || !!o.proposal;
    P.ready = hyp && valid && cut;
    el.appendChild(U.prose([
      'Sceller enregistre l’empreinte exacte de la règle (un hachage) et sa date. Ensuite, cette version ne se modifie plus : toute retouche crée la version suivante, en brouillon.',
      'La commission de tes réglages est figée dans l’empreinte si la stratégie n’en déclare pas.',
      'Seule une version scellée ouvre le hors échantillon de l’instrument, une seule fois par lignée : c’est le seul test qui n’a pas servi à la choisir. Une seconde ouverture est enregistrée et fait tomber ce critère du verdict.'
    ].map(T.esc)));
    var cutText = o.fixed && o.oosFrom ? 'Coupure hors échantillon de ' + inst + ' fixée au ' + keyText(o.oosFrom) + '.' : o.proposal ? 'Coupure hors échantillon de ' + inst + ' : pas encore fixée ; elle le sera au ' + keyText(o.proposal) + ' (30 % des séances après elle), sauf si tu la choisis d’abord dans la carte dédiée.' : 'Coupure hors échantillon de ' + inst + ' : aucune proposition sans jeu de données. Choisis un jeu dans l’en-tête.';
    el.appendChild(h('ul', { class: 'lb-chk' },
      h('li', { class: hyp ? null : 'no' }, h('i', null, hyp ? '✓' : '✗'), hyp ? 'Hypothèse écrite.' : 'Hypothèse vide : écris-la dans la carte Hypothèse.'),
      h('li', { class: valid ? null : 'no' }, h('i', null, valid ? '✓' : '✗'), valid ? 'Aucune erreur de validation.' : plural(n.errors.length, 'erreur') + ' à corriger d’abord.'),
      h('li', { class: cut ? null : 'no' }, h('i', null, cut ? '✓' : '✗'), cutText)));
    if (ST.dirty) el.appendChild(U.note('Les modifications non enregistrées seront scellées avec la version.'));
    if (P.why) el.appendChild(h('p', { class: 'lb-err' }, P.why));
  }
};
var FOOTS = {
  json: function (R, P, f) {
    var ro = readOnly(), okApply = !ro && P.check && P.check.ok && P.check.text === P.text;
    if (P.check && !P.check.ok) f.appendChild(h('p', { class: 'lb-wrn', style: 'margin:0' }, 'Corrige les erreurs listées, puis Valider à nouveau.'));
    else if (!P.check && !ro) f.appendChild(h('p', { class: 'lb-wrn', style: 'margin:0' }, '« Valider » d’abord : « Appliquer » s’ouvre quand le document est sans erreur.'));
    f.appendChild(h('div', { class: 'lb-fb' }, U.button({ label: 'Fermer', kind: 'ghost', onClick: function () { closePanel(R); } }),
      ro ? null : U.button({ label: 'Appliquer', kind: 'pri', disabled: !okApply, onClick: function () {
        var L = LSx(), spec = P.check.spec, changed = L.canonical(spec) !== L.canonical(ST.draft);
        if (changed) { ST.draft = clone(spec); ST.dirty = true; storeDraft(); }
        ST.panel = null; removeOverlay(); toast(changed ? 'JSON appliqué. Rien n’est écrit avant « Enregistrer ».' : 'Aucun changement.');
        if (R.alive()) paint(R);
      } })));
  },
  seal: function (R, P, f) {
    f.appendChild(h('div', { class: 'lb-fb' }, U.button({ label: 'Annuler', kind: 'ghost', onClick: function () { closePanel(R); } }),
      U.button({ label: P.busy ? 'Scellement…' : 'Sceller', kind: 'pri', disabled: !P.ready || P.busy || !has(R.api, 'seal'), onClick: function () {
        var spec = LB.specForSave(ST.draft, dataset(R));
        P.busy = true; paintFoot(R);
        Promise.resolve(ac(R, 'seal', [spec])).then(function (r) {
          P.busy = false;
          if (r && r.ok) { clearDraft(); ST.dirty = false; ST.key = null; ST.panel = null; removeOverlay(); toast('Version scellée' + (r.hash ? ' · ' + String(r.hash).slice(0, 9) : '') + '.'); if (R.alive()) paint(R); }
          else { P.why = (r && r.why) || 'Scellement refusé.'; repaint(R); }
        }, function (e) { P.busy = false; P.why = errMsg(e); repaint(R); });
      } })));
  }
};
function viewParams(R, P, el) {
  var w = P.work, names = Object.keys(w.params || {});
  el.appendChild(U.note('Chaque nombre d’une règle devient un paramètre nommé. Min, max et pas déclarent la grille d’un balayage (onglet Valider) : déclare-la avant de regarder les résultats. Pour qu’un même nombre serve à plusieurs champs, tape « $nom » dans le champ.'));
  if (!names.length) { el.appendChild(h('p', { class: 'lb-say' }, 'Aucun paramètre pour l’instant.')); return; }
  names.forEach(function (name) {
    var p = w.params[name], n = LB.useCount(w, name);
    if (!isObj(p)) return;
    function setK(k) { return function (x) { if (x === null) delete p[k]; else p[k] = x; edited(R, false); }; }
    var nameF = textField({ label: 'Nom', value: name, set: function (x) {
      var why = LB.renameParam(w, name, x);
      if (why) { toast(why); repaint(R); return; }
      edited(R, true);
    } });
    var grid = h('div', { class: 'fields' }, nameF,
      numField({ label: 'Valeur', get: function () { return p.v; }, allowEmpty: false, set: function (x) { if (typeof x === 'number') { p.v = x; edited(R, false); } } }),
      numField({ label: 'Minimum', get: function () { return p.min; }, allowEmpty: true, hint: function () { return p.min == null ? 'vide : pas de balayage' : ''; }, set: setK('min') }),
      numField({ label: 'Maximum', get: function () { return p.max; }, allowEmpty: true, set: setK('max') }),
      numField({ label: 'Pas', get: function () { return p.step; }, allowEmpty: true, set: setK('step') }));
    var lab = textField({ label: 'Libellé', full: true, value: p.label || '', set: function (x) { x = String(x || '').trim(); if (x) p.label = x; else delete p.label; edited(R, false); } });
    el.appendChild(h('div', { class: 'lb-item' }, h('span', { class: 'lb-lab' }, '$' + name + ' · ' + (n ? 'lu par ' + plural(n, 'champ') : 'inutilisé')), grid, lab,
      n ? null : itemActions([U.button({ label: 'Supprimer ce paramètre', kind: 'ghost', small: true, onClick: function () { delete w.params[name]; edited(R, true); } })])));
  });
}
