/* Labo de stratégie — le moteur (LABO.md, §3 et §4).
   Une seule fonction autonome, laboEngine(a), exécutée telle quelle dans un Web Worker (Blob de sa source)
   et appelée directement par les tests et les petits calculs. Elle ne lit aucune variable extérieure :
   ni T, ni quantEngine, ni new Function. Les fuseaux se calculent avec Intl (cache par heure), l’aléa
   avec un mulberry32 recopié et une graine explicite.
   Ce fichier n’enregistre aucun desk : il publie T.lib.laboEngine (enveloppes synchrones, exécuteur de
   worker). Aucun prix de marché n’y est écrit : les tests tournent sur des marches synthétiques amorcées. */
T.lib = T.lib || {};

function laboEngine(a) {
  'use strict';
  /* =====================================================================================
     API INTERNE — à lire avant d’ajouter une opération dans ce même corps de fonction.
     -------------------------------------------------------------------------------------
     prepare(a) → ctx
       Lit a.bars (colonnes {t,o,h,l,c,v?,lowFirst?} ou tableau d’objets), a.spec (valeurs par défaut
       de §3.0 complétées, jamais validées), a.sel {from,to} (clés), a.settings {tick, pointValue,
       commissionRT, maxContracts}, a.levels, a.adj, a.news, a.rolls (clés des séances de bascule d’un
       jeu non ajusté). Ne garde que les séances de sel plus a.warmSessions (20) séances d’amorçage.
       ctx = { spec0, anchor, tz, tick, pv, comm, maxC, S, F1, tf, dom, smc, warn, lv, news, off0 }
       S[s] = { key, dn, dow, i0, i1, A (ms de l’ancre nominale), end, exp (barres attendues), sel, roll }
       F1 = cadre d’une minute = { ctx, t,o,h,l,c,v (ou null), lf (lowFirst ou null), n,
            sess (Int32 : séance de la barre), sm (Float64 : minutes depuis l’ancre = sessmin),
            anch (Uint8 : barre ancrée), firstA (Uint8 : première barre ancrée de la séance),
            seg (Int32 : début du segment continu, coupé aux bascules), m (minutes par barre),
            si0/si1 (bornes de chaque séance), sa0/sa1 (bornes ancrées, −1 si aucune), cache {} }
     withBars(ctx, cols) → ctx2 : même structure de temps (séances, sessmin, ancrage, domaine), prix
       neufs (colonnes de longueur ctx.F1.n, déjà découpées), caches vides. Pour les permutations (4.3).
     ev(F, opérande) → Float64Array : série d’un opérande (3.2), mise en cache par clé canonique.
     cv(F, condition) → Uint8Array : 1 vraie, 0 fausse, 2 indéfinie (un opérande non fini) (3.3).
     clsOf(opérande) → 'k' constante | 'n' niveau | 'e' écart | 'o' oscillateur | 'u' neutre ; lève
       une erreur sur un typage refusé (niveau × nombre…).
     resolveSpec(spec, values), mOp / mCond / mSide (miroir 3.4, après résolution).
     config(ctx, values, spec?) → cfg = { spec (résolue, défauts compris), rules: {L, S}, sides: {L, S}
       (côtés négociés), sig: {L, S} (Uint8Array des signaux bruts setup ∧ déclencheur, masqués hors
       ancrage ; null si inutile), dom }. Les séries sont partagées par toutes les configurations d’un
       même ctx : un balayage ne recalcule que ce qui change.
     domain(ctx, spec) → dom = { from, to, flat, end (sessmin par séance), trade (Uint8 par séance :
       dans sel et jour autorisé), cons (Uint8 par barre : un signal y est pris en compte), warm }.
     executable(ctx, cfg) → Uint8Array : barres où un signal aurait été exécutable (3.5) — le tirage
       des entrées au hasard (4.2) s’y fait.
     execute(ctx, cfg, o) → { trades, counts, sessions, fill, costs } : l’exécution de §3.5 à §3.7,
       séance par séance, à partir de signaux. Options o (toutes facultatives) :
         fill          'pessimiste'|'optimiste'|'chemin'|'vrai' (remplace spec.fill)
         slipTicks     ticks par jambe glissée ; commissionRT : $ aller-retour (remplacent les coûts)
         throughTicks  dépassement exigé (ticks) des ordres limites, entrée et objectif (stress 4.7)
         sig           {L, S} : Uint8Array par barre, remplacent cfg.sig (entrées au hasard 4.2)
         sessions      Uint8Array sur ctx.S : 1 = séance jouée (ex. hors échantillon seul)
         fallback      {stop, target} en points : stop ou objectif `level` impossible à la barre → distance
         progress      false pour ne pas publier la progression
       sessions[x] = { key, s (indice dans ctx.S), dow, pnl, n, lo, hi, sig, sumR, sumR2 } pour TOUTES
       les séances jouées ; trade.sx renvoie à cet indice (mat[config][séance] s’en déduit).
     statsOf(trades, pv) → statistiques 4.1.
     lattice(o) → colonnes d’une marche au tick (4.4) ; sigmaOf(ctx, cfg) → σ de 4.4.
     progress(k, n) → transmet l’avancement à a.onProgress (le worker le limite à une fois / 250 ms).
     rng(seed) → mulberry32 ; warn(ctx, message) ; warnList(ctx).
     Les opérations s’enregistrent dans la table OPS, en bas de ce corps, et nulle part ailleurs.
     ===================================================================================== */
  a = a || {};
  var NY = 'America/New_York', PAR = 'Europe/Paris', MIN = 60000, HOUR = 3600000, DAY = 86400000;
  var onProg = typeof a.onProgress === 'function' ? a.onProgress : null;
  function progress(k, n) { if (onProg) onProg(k, n); }
  function fail(m) { throw new Error(m); }
  function isNum(x) { return typeof x === 'number' && x - x === 0; }
  function own(o, k) { return o != null && Object.prototype.hasOwnProperty.call(o, k); }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function clone(x) { return x === undefined ? undefined : JSON.parse(JSON.stringify(x)); }
  function nanArr(n) { var x = new Float64Array(n); x.fill(NaN); return x; }
  function canon(x) {
    if (x === null || x === undefined) return 'null';
    if (typeof x === 'number') return x === 0 ? '0' : String(x);
    if (typeof x !== 'object') return JSON.stringify(x);
    var s, i;
    if (Array.isArray(x)) { s = '['; for (i = 0; i < x.length; i++) s += (i ? ',' : '') + canon(x[i]); return s + ']'; }
    var ks = Object.keys(x).sort(), first = true; s = '{';
    for (i = 0; i < ks.length; i++) { var v = x[ks[i]]; if (v === undefined) continue; s += (first ? '' : ',') + JSON.stringify(ks[i]) + ':' + canon(v); first = false; }
    return s + '}';
  }
  function rng(seed) { var s = seed >>> 0; return function () { s = (s + 0x6D2B79F5) >>> 0; var t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

  /* ---------- Fuseaux : décalage (ms) à ajouter à l’instant UTC pour lire l’heure murale (cache par heure) ---------- */
  var OFF = {}, FMT = {};
  function off(tz, t) {
    if (!tz || tz === 'UTC') return 0;
    var hr = Math.floor(t / HOUR), key = tz + '|' + hr, v = OFF[key];
    if (v !== undefined) return v;
    var f = FMT[tz]; if (!f) f = FMT[tz] = new Intl.DateTimeFormat('en-US', { timeZone: tz, hourCycle: 'h23', year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric', second: 'numeric' });
    var o = {}, ps = f.formatToParts(new Date(hr * HOUR)); for (var i = 0; i < ps.length; i++) o[ps[i].type] = ps[i].value;
    v = Date.UTC(+o.year, +o.month - 1, +o.day, (+o.hour) % 24, +o.minute, +o.second) - hr * HOUR;
    OFF[key] = v; return v;
  }
  function wallToUtc(g, tz) { var t = g - off(tz, g); return g - off(tz, t); }
  function wallAt(dn, mins, tz) { return wallToUtc(dn * DAY + mins * MIN, tz); }
  var DSTR = {};
  function dayStr(dn) { var s = DSTR[dn]; if (s) return s; var d = new Date(dn * DAY); s = d.getUTCFullYear() + '-' + pad(d.getUTCMonth() + 1) + '-' + pad(d.getUTCDate()); DSTR[dn] = s; return s; }
  /* Clé de séance Globex (2.1) : date UTC de t + décalage(New York, t) + 6 h. */
  function keyDn(t) { return Math.floor((t + off(NY, t) + 6 * HOUR) / DAY); }
  function keyOf(t) { return dayStr(keyDn(t)); }
  function dnOfKey(k) { var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(k)); if (!m) fail('Clé de séance invalide : « ' + k + ' ».'); return Math.round(Date.UTC(+m[1], +m[2] - 1, +m[3]) / DAY); }
  function dowOf(dn) { var w = ((dn + 4) % 7 + 7) % 7; return w === 0 ? 7 : w; }
  function hm(s) { var m = /^(\d{1,2}):(\d{2})$/.exec(String(s)); if (!m || +m[2] > 59 || +m[1] > 24) fail('Heure invalide : « ' + s + ' » (attendu HH:MM).'); return +m[1] * 60 + +m[2]; }

  /* ---------- Valeurs par défaut (3.0) : des constantes du code, jamais lues dans les réglages ---------- */
  var DEF = {
    instrument: 'MNQ', anchor: 'globex', side: 'long', mirror: true, short: null,
    session: { tz: PAR, from: '00:00', to: '09:00', flat: '09:00', days: [1, 2, 3, 4, 5], warmup: 15 },
    manage: { breakeven: null, trail: null, maxBars: null, exitOnOpposite: false },
    risk: { mode: 'contracts', contracts: 1, riskUsd: 150, maxQty: null, minStopTicks: 4, maxPerSession: 3, maxLossesPerSession: 2, dailyStopUsd: 400, cooldown: 0 },
    costs: { commissionRT: null, slipTicks: 1 }, fill: 'pessimiste', params: {}
  };
  function sideDefaults(r) {
    if (!r) return r;
    if (!Array.isArray(r.setup)) r.setup = r.setup ? [r.setup] : [];
    if (!r.entry) r.entry = { type: 'market' };
    if (!r.target) r.target = { type: 'none' };
    return r;
  }
  function withDefaults(spec) {
    var s = clone(spec || {}) || {}, k, j;
    for (k in DEF) {
      if (!own(DEF, k)) continue;
      if (s[k] === undefined) s[k] = clone(DEF[k]);
      else if (DEF[k] && typeof DEF[k] === 'object' && !Array.isArray(DEF[k]) && s[k] && typeof s[k] === 'object' && !Array.isArray(s[k])) {
        for (j in DEF[k]) if (own(DEF[k], j) && s[k][j] === undefined) s[k][j] = clone(DEF[k][j]);
      }
    }
    sideDefaults(s.long); sideDefaults(s.short);
    return s;
  }

  /* ---------- Résolution des paramètres ($nom) ---------- */
  function resolveSpec(spec, values) {
    var params = (spec && spec.params) || {}, vals = values || {};
    function look(name) {
      if (own(vals, name) && vals[name] != null) return vals[name];
      var p = params[name];
      if (p && typeof p === 'object' && p.v != null) return p.v;
      if (p != null && typeof p !== 'object') return p;
      return fail('Paramètre « $' + name + ' » sans valeur : déclarez-le dans params.');
    }
    function walk(x) {
      if (typeof x === 'string') {
        if (x.charAt(0) !== '$') return x;
        var v = look(x.slice(1));
        if (typeof v === 'string' && v.charAt(0) === '$') fail('Paramètre « ' + x + ' » défini par un autre paramètre.');
        return v;
      }
      if (Array.isArray(x)) return x.map(walk);
      if (x && typeof x === 'object') { var o = {}; for (var k in x) if (own(x, k)) o[k] = k === 'params' ? clone(x[k]) : walk(x[k]); return o; }
      return x;
    }
    return walk(spec);
  }

  /* ---------- Classes des opérandes (3.2) ---------- */
  var FIELD_N = { close: 1, open: 1, high: 1, low: 1, hl2: 1, hlc3: 1 };
  function clsOf(x) {
    if (typeof x === 'number') return 'k';
    if (typeof x === 'string') { if (x.charAt(0) === '$') return 'k'; fail('Opérande inconnu : « ' + x + ' ».'); }
    if (!x || typeof x !== 'object') fail('Opérande invalide.');
    if (own(x, 'op')) {
      var A = clsOf(x.a), B = clsOf(x.b), op = x.op;
      if (A === 'o' || B === 'o') fail('Opération sur un oscillateur refusée : comparez-le directement.');
      if (op === '+') {
        if (A === 'n' && B === 'n') fail('Niveau + niveau refusé : une somme de prix n’est pas un prix.');
        if (A === 'n' || B === 'n') return 'n';
        if (A === 'e' && (B === 'e' || B === 'k')) return 'e';
        if (B === 'e' && A === 'k') return 'e';
        if (A === 'e' || B === 'e') fail('Écart + neutre refusé.');
        return A === 'k' && B === 'k' ? 'k' : 'u';
      }
      if (op === '-') {
        if (A === 'n' && B === 'n') return 'e';
        if (A === 'n') return 'n';
        if (B === 'n') fail('Soustraire un niveau d’un nombre est refusé.');
        if (A === 'e' && (B === 'e' || B === 'k')) return 'e';
        if (B === 'e' && A === 'k') return 'e';
        if (A === 'e' || B === 'e') fail('Écart − neutre refusé.');
        return A === 'k' && B === 'k' ? 'k' : 'u';
      }
      if (op === '*' || op === '/') {
        if (A === 'n' || B === 'n') fail('Niveau ' + (op === '*' ? '×' : '÷') + ' nombre refusé : le résultat n’est plus un prix.');
        if (A === 'e' && B === 'e') return 'u';
        if (A === 'e') return 'e';
        if (B === 'e') { if (op === '/') fail('Nombre ÷ écart refusé.'); return 'e'; }
        return A === 'k' && B === 'k' ? 'k' : 'u';
      }
      fail('Opération inconnue : « ' + op + ' ».');
    }
    switch (x.f) {
      case 'close': case 'open': case 'high': case 'low': case 'hl2': case 'hlc3': return 'n';
      case 'volume': case 'range': case 'sd': case 'atr': case 'rvol': case 'time': case 'dow': case 'sessmin': return 'u';
      case 'body': case 'dist': return 'e';
      case 'rsi': return 'o';
      case 'vwap': case 'prev': case 'sess': case 'or': case 'at': case 'level': case 'nearest': return 'n';
      case 'sma': case 'ema': case 'tf': return clsOf(x.of == null ? { f: 'close' } : x.of);
      case 'hh': case 'll': return clsOf(x.of == null ? { f: x.f === 'hh' ? 'high' : 'low' } : x.of);
    }
    return fail('Opérande inconnu : « ' + x.f + ' ».');
  }

  /* ---------- Miroir (3.4) : la réflexion des prix p → K − p, après résolution ---------- */
  var FLIP = { '>': '<', '<': '>', '>=': '<=', '<=': '>=' };
  function negK(x) { return typeof x === 'number' ? -x : { op: '-', a: 0, b: x }; }
  function hundredMinus(x) { return typeof x === 'number' ? 100 - x : { op: '-', a: 100, b: x }; }
  function mOp(x) {
    if (typeof x === 'number') return x;
    if (typeof x === 'string') fail(x.charAt(0) === '$' ? 'Miroir avant résolution : « ' + x + ' ».' : 'Opérande inconnu : « ' + x + ' ».');
    if (!x || typeof x !== 'object') fail('Opérande invalide.');
    var c = clsOf(x), o, k;
    if (own(x, 'op')) {
      var A = clsOf(x.a), B = clsOf(x.b);
      if ((x.op === '+' || x.op === '-') && c === 'n') {
        var flipOp = x.op === '+' ? '-' : '+';
        if (A === 'n') return { op: B === 'e' ? x.op : flipOp, a: mOp(x.a), b: mOp(x.b) };
        return { op: A === 'e' ? '+' : '-', a: mOp(x.b), b: mOp(x.a) };   // d + niveau → niveau′ ∓ d
      }
      if ((x.op === '+' || x.op === '-') && c === 'e') return { op: x.op, a: A === 'k' ? negK(x.a) : mOp(x.a), b: B === 'k' ? negK(x.b) : mOp(x.b) };
      return { op: x.op, a: A === 'k' ? x.a : mOp(x.a), b: B === 'k' ? x.b : mOp(x.b) };
    }
    o = {}; for (k in x) if (own(x, k)) o[k] = x[k];
    switch (x.f) {
      case 'high': o.f = 'low'; break;
      case 'low': o.f = 'high'; break;
      case 'vwap': o.k = x.k ? -x.k : 0; break;
      case 'sma': case 'ema': case 'sd': case 'tf': o.of = mOp(x.of == null ? { f: 'close' } : x.of); break;
      case 'hh': case 'll':
        var of = x.of == null ? { f: x.f === 'hh' ? 'high' : 'low' } : x.of, co = clsOf(of);
        o.of = mOp(of); if (co === 'n' || co === 'e' || co === 'o') o.f = x.f === 'hh' ? 'll' : 'hh';
        break;
      case 'prev': case 'sess': case 'or': if (x.of === 'high') o.of = 'low'; else if (x.of === 'low') o.of = 'high'; break;
      case 'nearest': o.side = x.side === 'above' ? 'below' : 'above'; break;
      case 'dist': o.a = mOp(x.a); o.b = mOp(x.b); break;
    }
    return o;
  }
  function mPair(a, b, what) {
    var A = clsOf(a), B = clsOf(b);
    if (A === 'n' || B === 'n') {
      if (A === 'n' && B === 'n') return { a: mOp(a), b: mOp(b), flip: true };
      fail(A === 'k' || B === 'k' ? 'Miroir impossible : ' + what + ' compare un niveau à une constante (déclarez le côté vendeur, ou comparez à un autre niveau).' : 'Miroir impossible : ' + what + ' compare un niveau à une autre classe.');
    }
    if (A === 'e' || B === 'e') {
      if (A === 'e' && B === 'e') return { a: mOp(a), b: mOp(b), flip: true };
      if (A === 'e' && B === 'k') return { a: mOp(a), b: negK(b), flip: true };
      if (A === 'k' && B === 'e') return { a: negK(a), b: mOp(b), flip: true };
      fail('Miroir impossible : ' + what + ' compare un écart à un neutre ou à un niveau.');
    }
    if (A === 'o' || B === 'o') {
      if (A === 'o' && B === 'o') return { a: mOp(a), b: mOp(b), flip: true };
      if (A === 'o' && B === 'k') return { a: mOp(a), b: hundredMinus(b), flip: true };
      if (A === 'k' && B === 'o') return { a: hundredMinus(a), b: mOp(b), flip: true };
      fail('Miroir impossible : ' + what + ' compare un oscillateur à une autre classe.');
    }
    return { a: mOp(a), b: mOp(b), flip: false };
  }
  function needLevel(x, what) { if (clsOf(x) !== 'n') fail(what + ' doit être un niveau (un prix).'); }
  function condKind(c) {
    if (!c || typeof c !== 'object') fail('Condition invalide.');
    var K = ['cmp', 'cross', 'touch', 'reject', 'break', 'bar', 'time', 'news', 'all', 'any', 'not', 'for', 'within'];
    for (var i = 0; i < K.length; i++) if (own(c, K[i])) return K[i];
    return fail('Condition inconnue : ' + JSON.stringify(c).slice(0, 80));
  }
  function mCond(c) {
    var k = condKind(c), p, o;
    switch (k) {
      case 'cmp': p = mPair(c.a, c.b, 'la comparaison'); return { cmp: p.flip ? FLIP[c.cmp] : c.cmp, a: p.a, b: p.b };
      case 'cross': p = mPair(c.a, c.b, 'le croisement'); return { cross: p.flip ? (c.cross === 'up' ? 'down' : 'up') : c.cross, a: p.a, b: p.b };
      case 'touch': needLevel(c.touch, 'Le niveau touché'); return { touch: mOp(c.touch), from: c.from === 'above' ? 'below' : 'above' };
      case 'reject': needLevel(c.reject, 'Le niveau rejeté'); return { reject: mOp(c.reject), from: c.from === 'above' ? 'below' : 'above' };
      case 'break': needLevel(c['break'], 'Le niveau cassé'); o = {}; o['break'] = mOp(c['break']); o.dir = c.dir === 'up' ? 'down' : 'up'; return o;
      case 'bar': return { bar: c.bar === 'up' ? 'down' : 'up' };
      case 'time': case 'news': return clone(c);
      case 'all': return { all: (c.all || []).map(mCond) };
      case 'any': return { any: (c.any || []).map(mCond) };
      case 'not': return { not: mCond(c.not) };
      case 'for': return { 'for': c['for'], cond: mCond(c.cond) };
      case 'within': return { within: c.within, cond: mCond(c.cond) };
    }
    return null;
  }
  function mOrder(x, what) {
    if (!x) return x;
    var o = clone(x);
    if (x.type === 'limit' || x.type === 'stop' || x.type === 'level') { if (x.at == null) fail(what + ' : niveau « at » absent.'); needLevel(x.at, what); o.at = mOp(x.at); }
    return o;
  }
  function mSide(r) {
    if (!r) fail('Règle acheteuse absente : le miroir part du côté acheteur.');
    if (!r.trigger) fail('Déclencheur absent.');
    return { setup: (r.setup || []).map(mCond), trigger: mCond(r.trigger), entry: mOrder(r.entry || { type: 'market' }, 'Entrée'), stop: mOrder(r.stop, 'Stop'), target: mOrder(r.target || { type: 'none' }, 'Objectif') };
  }

  /* ---------- Colonnes et séances ---------- */
  function typed(x) { return ArrayBuffer.isView(x) ? x : new Float64Array(x); }
  function sub(x, i, j) { return x ? (x.subarray ? x.subarray(i, j) : Array.prototype.slice.call(x, i, j)) : null; }
  function columns(b) {
    if (!b) fail('Aucune barre fournie.');
    var t, o, h, l, c, v = null, lf = null, n, i;
    if (Array.isArray(b)) {
      n = b.length; t = new Float64Array(n); o = new Float64Array(n); h = new Float64Array(n); l = new Float64Array(n); c = new Float64Array(n);
      var hv = false, hl = false;
      for (i = 0; i < n; i++) { var x = b[i]; t[i] = x.t; o[i] = x.o; h[i] = x.h; l[i] = x.l; c[i] = x.c; if (isNum(x.v)) hv = true; if (x.lowFirst != null) hl = true; }
      if (hv) { v = new Float64Array(n); for (i = 0; i < n; i++) v[i] = isNum(b[i].v) ? b[i].v : 0; }
      if (hl) { lf = new Uint8Array(n); for (i = 0; i < n; i++) lf[i] = b[i].lowFirst ? 1 : 0; }
    } else {
      if (!b.t) fail('Colonne de temps absente.');
      t = typed(b.t); n = t.length; o = typed(b.o); h = typed(b.h); l = typed(b.l); c = typed(b.c);
      if (b.v && b.v.length === n) v = typed(b.v);
      if (b.lowFirst && b.lowFirst.length === n) lf = b.lowFirst;
    }
    for (i = 1; i < n; i++) if (!(t[i] > t[i - 1])) fail('Barres non triées ou en double (rang ' + i + ').');
    return { t: t, o: o, h: h, l: l, c: c, v: v, lf: lf, n: n };
  }
  /* Deux registres d’avertissements : fwarn suit les caches (séries, domaine) et survit avec eux d’un appel à
     l’autre ; warn appartient à l’appel (exécution). warnList les réunit. */
  function warn(ctx, m) { ctx.fwarn[m] = (ctx.fwarn[m] || 0) + 1; }
  function rwarn(ctx, m) { ctx.warn[m] = (ctx.warn[m] || 0) + 1; }
  function warnList(ctx) {
    var out = [], all = {}, k;
    for (k in ctx.fwarn) if (own(ctx.fwarn, k)) all[k] = ctx.fwarn[k];
    for (k in ctx.warn) if (own(ctx.warn, k)) all[k] = (all[k] || 0) + ctx.warn[k];
    for (k in all) if (own(all, k)) out.push(all[k] > 1 ? k + ' (' + all[k] + ' fois)' : k);
    return out;
  }
  function anchorOf(anchor, dn) {
    if (anchor === 'globex') return wallAt(dn - 1, 18 * 60, NY);
    if (anchor === 'paris') return wallAt(dn, 0, PAR);
    return wallAt(dn, 9 * 60 + 30, NY);
  }
  function frame(ctx, cols, sess, sm, m, seg) {
    var n = sess.length, ns = ctx.S.length, rth = ctx.anchor === 'rth', i;
    var anch = new Uint8Array(n), firstA = new Uint8Array(n), si0 = new Int32Array(ns), si1 = new Int32Array(ns), sa0 = new Int32Array(ns), sa1 = new Int32Array(ns);
    si0.fill(-1); si1.fill(-1); sa0.fill(-1); sa1.fill(-1);
    for (i = 0; i < n; i++) {
      var s = sess[i]; if (si0[s] < 0) si0[s] = i; si1[s] = i;
      var x = sm[i];
      if (x >= 0 && (!rth || x < 390)) { anch[i] = 1; if (sa0[s] < 0) { sa0[s] = i; firstA[i] = 1; } sa1[s] = i; }
    }
    return { ctx: ctx, t: cols.t, o: cols.o, h: cols.h, l: cols.l, c: cols.c, v: cols.v || null, lf: cols.lf || null, n: n, sess: sess, sm: sm, anch: anch, firstA: firstA, seg: seg, m: m, si0: si0, si1: si1, sa0: sa0, sa1: sa1, cache: {}, isTf: m > 1 };
  }
  function prepare(a) {
    var spec0 = withDefaults(a.spec), anchor = spec0.anchor;
    if (anchor !== 'globex' && anchor !== 'paris' && anchor !== 'rth') fail('Ancrage inconnu : « ' + anchor + ' » (globex, paris ou rth).');
    var st = a.settings || {}, i, s, ck = null;
    /* cache d’un appel à l’autre (worker) : même jeu, même ancrage, même sélection → mêmes séries */
    if (a.cache && typeof a.cache === 'object' && a.fp) {
      ck = [a.fp, anchor, (spec0.session && spec0.session.tz) || PAR, canon(a.sel || null), canon(a.warmSessions), canon(a.rolls || null), canon(a.levels || null), canon(a.adj || null), canon(a.news || null), canon(st.tick)].join('|');
      var hc = a.cache.ctx;
      if (hc && a.cache.key === ck) {
        hc.a = a; hc.spec0 = spec0; hc.warn = {};
        hc.pv = isNum(st.pointValue) && st.pointValue > 0 ? st.pointValue : 2; hc.comm = isNum(st.commissionRT) ? st.commissionRT : 0; hc.maxC = isNum(st.maxContracts) && st.maxContracts > 0 ? st.maxContracts : 0;
        return hc;
      }
    }
    var B = columns(a.bars), N = B.n;
    if (!N) fail('Aucune barre fournie.');
    var starts = [], dns = [], prev = null;
    for (i = 0; i < N; i++) { var d = keyDn(B.t[i]); if (d !== prev) { if (prev !== null && d < prev) fail('Barres non triées.'); starts.push(i); dns.push(d); prev = d; } }
    var sel = a.sel || null, s0 = 0, s1 = starts.length - 1;
    if (sel) {
      if (sel.from != null) { s0 = starts.length; for (s = 0; s < starts.length; s++) if (dayStr(dns[s]) >= sel.from) { s0 = s; break; } }
      if (sel.to != null) { s1 = -1; for (s = starts.length - 1; s >= 0; s--) if (dayStr(dns[s]) <= sel.to) { s1 = s; break; } }
    }
    if (s0 > s1) fail('Aucune séance dans la sélection' + (sel ? ' (' + (sel.from || '…') + ' → ' + (sel.to || '…') + ')' : '') + '.');
    var warmN = isNum(a.warmSessions) ? Math.max(0, a.warmSessions | 0) : 20, w0 = Math.max(0, s0 - warmN);
    var i0 = starts[w0], i1 = s1 + 1 < starts.length ? starts[s1 + 1] - 1 : N - 1, n = i1 - i0 + 1;
    var cols = { t: sub(B.t, i0, i1 + 1), o: sub(B.o, i0, i1 + 1), h: sub(B.h, i0, i1 + 1), l: sub(B.l, i0, i1 + 1), c: sub(B.c, i0, i1 + 1), v: sub(B.v, i0, i1 + 1), lf: sub(B.lf, i0, i1 + 1) };
    var rolls = {}, rl = a.rolls;
    if (Array.isArray(rl)) rl.forEach(function (k) { rolls[k] = 1; }); else if (rl && typeof rl === 'object') for (var rk in rl) if (own(rl, rk) && rl[rk]) rolls[rk] = 1;
    var ctx = { a: a, spec0: spec0, anchor: anchor, tz: (spec0.session && spec0.session.tz) || PAR, tick: isNum(st.tick) && st.tick > 0 ? st.tick : 0.25, pv: isNum(st.pointValue) && st.pointValue > 0 ? st.pointValue : 2,
      comm: isNum(st.commissionRT) ? st.commissionRT : 0, maxC: isNum(st.maxContracts) && st.maxContracts > 0 ? st.maxContracts : 0, S: [], tf: {}, dom: {}, smc: {}, warn: {}, off0: i0 };
    var S = ctx.S, sess = new Int32Array(n), sm = new Float64Array(n), seg = new Int32Array(n), segStart = 0;
    for (s = w0; s <= s1; s++) {
      var dn = dns[s], A = anchorOf(anchor, dn), end = wallAt(dn, 17 * 60, NY), key = dayStr(dn);
      var exp = anchor === 'globex' ? 1380 : anchor === 'rth' ? 390 : Math.round((end - A) / MIN);
      var si = S.length, b0 = starts[s] - i0, b1 = (s + 1 < starts.length ? starts[s + 1] - 1 : N - 1) - i0;
      if (rolls[key] && si > 0) segStart = b0;
      S.push({ key: key, dn: dn, dow: dowOf(dn), i0: b0, i1: b1, A: A, end: end, exp: exp, sel: s >= s0, roll: !!rolls[key] });
      for (i = b0; i <= b1; i++) { sess[i] = si; sm[i] = (cols.t[i] - A) / MIN; seg[i] = segStart; }
    }
    ctx.F1 = frame(ctx, cols, sess, sm, 1, seg);
    ctx.n = n;
    /* niveaux nommés (2.2) : niveau + base NDX éventuelle + ajustement de la séance */
    var lv = a.levels || {}, adj = a.adj || {};
    ctx.lv = S.map(function (se) {
      var d = lv[se.key], base = 0, src = d, out = {}, ad = isNum(adj[se.key]) ? adj[se.key] : 0;
      if (!d || typeof d !== 'object') return out;
      if (d.levels && typeof d.levels === 'object') { src = d.levels; if (d.scale === 'NDX') { if (isNum(d.base)) base = d.base; else { warn(ctx, 'niveaux NDX sans base : ignorés'); return out; } } }
      for (var nm in src) if (own(src, nm) && isNum(src[nm])) out[nm] = src[nm] + base + ad;
      return out;
    });
    var nw = (a.news || []).filter(function (x) { return x && isNum(x.t); }).slice().sort(function (x, y) { return x.t - y.t; });
    ctx.news = { t: nw.map(function (x) { return x.t; }), imp: nw.map(function (x) { return isNum(x.impact) ? x.impact : 0; }) };
    return ctx;
  }
  function withBars(ctx, cols) {
    var F = ctx.F1, c2 = {}, k;
    for (k in ctx) if (own(ctx, k)) c2[k] = ctx[k];
    if (!cols || cols.c.length !== F.n) fail('withBars : colonnes de longueur ' + F.n + ' attendues.');
    c2.F1 = frame(c2, { t: F.t, o: cols.o, h: cols.h, l: cols.l, c: cols.c, v: cols.v === undefined ? F.v : cols.v, lf: cols.lowFirst || cols.lf || null }, F.sess, F.sm, 1, F.seg);
    c2.tf = {}; c2.warn = ctx.warn;
    return c2;
  }
  /* Heure HH:MM (fuseau tz) → minutes depuis l’ancre de la séance s : première occurrence à partir de l’ancre. */
  function smAt(ctx, s, str, tz) {
    tz = tz || ctx.tz;
    var k = s + '|' + str + '|' + tz, v = ctx.smc[k];
    if (v !== undefined) return v;
    var A = ctx.S[s].A, w = A + off(tz, A), day = Math.floor(w / DAY) * DAY, cand = day + hm(str) * MIN;
    if (cand < w) cand += DAY;
    v = (wallToUtc(cand, tz) - A) / MIN;
    ctx.smc[k] = v; return v;
  }

  /* ---------- Cadre de m minutes, aligné sur l’ancre (opérande tf) ---------- */
  function tfFrame(F, m) {
    var ctx = F.ctx, G = ctx.tf[m];
    if (G) return G;
    var n = F.n, map = new Int32Array(n), closed = new Int32Array(n), T_ = [], O = [], H = [], L = [], C = [], V = F.v ? [] : null, SS = [], SM = [], SG = [], k = -1, ls = -1, lb = 0, i;
    for (i = 0; i < n; i++) {
      var s = F.sess[i], b = Math.floor(F.sm[i] / m);
      if (s !== ls || b !== lb) {
        k++; ls = s; lb = b;
        T_.push(ctx.S[s].A + b * m * MIN); O.push(F.o[i]); H.push(F.h[i]); L.push(F.l[i]); C.push(F.c[i]); if (V) V.push(F.v[i] > 0 ? F.v[i] : 0); SS.push(s); SM.push(b * m); SG.push(F.seg[i]);
      } else {
        if (F.h[i] > H[k]) H[k] = F.h[i];
        if (F.l[i] < L[k]) L[k] = F.l[i];
        C[k] = F.c[i]; if (V) V[k] += F.v[i] > 0 ? F.v[i] : 0;
      }
      map[i] = k;
      closed[i] = F.sm[i] + 1 === (b + 1) * m ? k : k - 1;
    }
    var nk = k + 1, seg = new Int32Array(nk);
    for (i = 0; i < nk; i++) seg[i] = map[SG[i]];
    G = frame(ctx, { t: new Float64Array(T_), o: new Float64Array(O), h: new Float64Array(H), l: new Float64Array(L), c: new Float64Array(C), v: V ? new Float64Array(V) : null, lf: null }, new Int32Array(SS), new Float64Array(SM), m, seg);
    G.map = map; G.closed = closed;
    ctx.tf[m] = G;
    return G;
  }

  /* ---------- Séries des opérandes (3.2) ---------- */
  function ev(F, x) {
    var key, hit, out;
    if (typeof x === 'number') {
      key = 'k:' + x; hit = F.cache[key]; if (hit) return hit;
      out = new Float64Array(F.n); out.fill(x); F.cache[key] = out; return out;
    }
    if (typeof x === 'string') fail(x.charAt(0) === '$' ? 'Paramètre non résolu : « ' + x + ' ».' : 'Opérande inconnu : « ' + x + ' ».');
    if (!x || typeof x !== 'object') fail('Opérande invalide.');
    key = canon(x); hit = F.cache[key]; if (hit) return hit;
    out = own(x, 'op') ? evOp(F, x) : evF(F, x);
    F.cache[key] = out;
    return out;
  }
  function evOp(F, x) {
    clsOf(x);
    var A = ev(F, x.a), B = ev(F, x.b), n = F.n, out = new Float64Array(n), i;
    switch (x.op) {
      case '+': for (i = 0; i < n; i++) out[i] = A[i] + B[i]; break;
      case '-': for (i = 0; i < n; i++) out[i] = A[i] - B[i]; break;
      case '*': for (i = 0; i < n; i++) out[i] = A[i] * B[i]; break;
      case '/': for (i = 0; i < n; i++) out[i] = A[i] / B[i]; break;
    }
    return out;
  }
  function posInt(v, what, def) {
    if (v == null && def != null) return def;
    if (!isNum(v) || v < 1 || Math.floor(v) !== v) fail(what + ' : un entier ≥ 1 est attendu (reçu ' + v + ').');
    return v;
  }
  function baseField(F, f) {
    var key = 'b:' + f, hit = F.cache[key], n = F.n, i, out;
    if (hit) return hit;
    switch (f) {
      case 'close': return F.c;
      case 'open': return F.o;
      case 'high': return F.h;
      case 'low': return F.l;
      case 'hl2': out = new Float64Array(n); for (i = 0; i < n; i++) out[i] = (F.h[i] + F.l[i]) / 2; break;
      case 'hlc3': out = new Float64Array(n); for (i = 0; i < n; i++) out[i] = (F.h[i] + F.l[i] + F.c[i]) / 3; break;
      case 'range': out = new Float64Array(n); for (i = 0; i < n; i++) out[i] = F.h[i] - F.l[i]; break;
      case 'body': out = new Float64Array(n); for (i = 0; i < n; i++) out[i] = F.c[i] - F.o[i]; break;
      case 'volume': if (F.v) return F.v; out = nanArr(n); break;
    }
    F.cache[key] = out; return out;
  }
  function lagged(F, arr, lag) {
    if (lag == null || lag === 0) return arr;
    if (!isNum(lag) || lag < 0 || Math.floor(lag) !== lag) fail('lag : un entier ≥ 0 est attendu.');
    var n = F.n, out = nanArr(n);
    for (var i = lag; i < n; i++) if (i - lag >= F.seg[i]) out[i] = arr[i - lag];
    return out;
  }
  function rollMean(F, arr, n) {
    var N = F.n, out = nanArr(N), s = 0, k = 0, nn = 0, i, j;
    for (i = 0; i < N; i++) {
      var x = arr[i];
      if (i === F.seg[i]) { k = 0; s = 0; nn = 0; }
      if (!(x - x === 0)) { k = 0; s = 0; nn = 0; continue; }
      if (k < n) { s += x; k++; } else s += x - arr[i - n];
      if (k === n) {
        if (++nn >= n) { nn = 0; s = 0; for (j = i - n + 1; j <= i; j++) s += arr[j]; }
        out[i] = s / n;
      }
    }
    return out;
  }
  function emaOf(F, arr, n) {
    var N = F.n, out = nanArr(N), al = 2 / (n + 1), e = 0, k = 0, s = 0;
    for (var i = 0; i < N; i++) {
      var x = arr[i];
      if (i === F.seg[i]) { k = 0; s = 0; }
      if (!(x - x === 0)) { k = 0; s = 0; continue; }
      if (k < n) { s += x; k++; if (k === n) { e = s / n; out[i] = e; } }
      else { e = e + al * (x - e); out[i] = e; }
    }
    return out;
  }
  /* plus haut (max) ou plus bas de arr sur i−n … i−1, barre courante exclue */
  function rollExt(F, arr, n, isMax) {
    var N = F.n, out = nanArr(N), dq = new Int32Array(N), hd = 0, tl = 0, bad = -1;
    for (var i = 0; i < N; i++) {
      var j = i - 1;
      if (j >= 0) {
        var x = arr[j];
        if (!(x - x === 0)) bad = j;
        else { while (tl > hd && (isMax ? arr[dq[tl - 1]] <= x : arr[dq[tl - 1]] >= x)) tl--; dq[tl++] = j; }
      }
      var lo = i - n;
      while (tl > hd && dq[hd] < lo) hd++;
      if (lo >= 0 && lo >= F.seg[i] && bad < lo && tl > hd) out[i] = arr[dq[hd]];
    }
    return out;
  }
  function rollSd(F, arr, n) {
    var N = F.n, out = nanArr(N), k = 0, i, j;
    for (i = 0; i < N; i++) {
      var x = arr[i];
      if (i === F.seg[i]) k = 0;
      if (!(x - x === 0)) { k = 0; continue; }
      if (k < n) k++;
      if (k === n) {
        var m = 0; for (j = i - n + 1; j <= i; j++) m += arr[j]; m /= n;
        var q = 0; for (j = i - n + 1; j <= i; j++) q += (arr[j] - m) * (arr[j] - m);
        out[i] = Math.sqrt(q / n);
      }
    }
    return out;
  }
  function atrOf(F, n) {
    var key = 'atr:' + n, hit = F.cache[key];
    if (hit) return hit;
    var N = F.n, out = nanArr(N), v = 0, k = 0, s = 0;
    for (var i = 0; i < N; i++) {
      var first = i === F.seg[i];
      if (first) { k = 0; s = 0; }
      var tr = first ? F.h[i] - F.l[i] : Math.max(F.h[i] - F.l[i], Math.abs(F.h[i] - F.c[i - 1]), Math.abs(F.l[i] - F.c[i - 1]));
      if (k < n) { s += tr; k++; if (k === n) { v = s / n; out[i] = v; } }
      else { v = (v * (n - 1) + tr) / n; out[i] = v; }
    }
    F.cache[key] = out; return out;
  }
  function rsiOf(F, n) {
    var N = F.n, out = nanArr(N), ag = 0, al = 0, k = 0, sg = 0, sl = 0;
    function val(g, l) { return g === 0 && l === 0 ? 50 : l === 0 ? 100 : 100 - 100 / (1 + g / l); }
    for (var i = 0; i < N; i++) {
      if (i === F.seg[i]) { k = 0; sg = 0; sl = 0; continue; }
      var d = F.c[i] - F.c[i - 1], g = d > 0 ? d : 0, l = d < 0 ? -d : 0;
      if (k < n) { sg += g; sl += l; k++; if (k === n) { ag = sg / n; al = sl / n; out[i] = val(ag, al); } }
      else { ag = (ag * (n - 1) + g) / n; al = (al * (n - 1) + l) / n; out[i] = val(ag, al); }
    }
    return out;
  }
  function vwapCore(F) {
    var hit = F.cache._vw;
    if (hit) return hit;
    var n = F.n, vw = nanArr(n), sd = nanArr(n), S = F.ctx.S;
    for (var s = 0; s < S.length; s++) {
      var a0 = F.sa0[s], a1 = F.sa1[s], i;
      if (a0 < 0) continue;
      var useV = false;
      if (F.v) for (i = a0; i <= a1; i++) if (F.v[i] > 0) { useV = true; break; }
      var p0 = (F.h[a0] + F.l[a0] + F.c[a0]) / 3, sw = 0, sp = 0, sp2 = 0;
      for (i = a0; i <= a1; i++) {
        var w = useV ? (F.v[i] > 0 ? F.v[i] : 0) : 1, tp = (F.h[i] + F.l[i] + F.c[i]) / 3 - p0;
        sw += w; sp += w * tp; sp2 += w * tp * tp;
        if (sw > 0) { var m1 = sp / sw, va = sp2 / sw - m1 * m1; vw[i] = p0 + m1; sd[i] = va > 1e-12 ? Math.sqrt(va) : 0; }
      }
    }
    hit = F.cache._vw = { vw: vw, sd: sd };
    return hit;
  }
  function sessStats(F) {
    var hit = F.cache._ss;
    if (hit) return hit;
    var ns = F.ctx.S.length, r = { open: nanArr(ns), high: nanArr(ns), low: nanArr(ns), close: nanArr(ns), cnt: new Float64Array(ns) };
    for (var s = 0; s < ns; s++) {
      var a0 = F.sa0[s], a1 = F.sa1[s];
      if (a0 < 0) continue;
      var hi = -Infinity, lo = Infinity;
      for (var i = a0; i <= a1; i++) { if (F.h[i] > hi) hi = F.h[i]; if (F.l[i] < lo) lo = F.l[i]; }
      r.open[s] = F.o[a0]; r.close[s] = F.c[a1]; r.high[s] = hi; r.low[s] = lo; r.cnt[s] = a1 - a0 + 1;
    }
    F.cache._ss = r;
    return r;
  }
  function perSession(F, vals) { var out = new Float64Array(F.n); for (var i = 0; i < F.n; i++) out[i] = vals[F.sess[i]]; return out; }
  function evF(F, x) {
    var ctx = F.ctx, S = ctx.S, n = F.n, out, i, s, arr, of;
    switch (x.f) {
      case 'close': case 'open': case 'high': case 'low': case 'hl2': case 'hlc3': case 'volume': case 'range': case 'body':
        return lagged(F, baseField(F, x.f), x.lag);
      case 'vwap': {
        var core = vwapCore(F), k = isNum(x.k) ? x.k : 0, tick = ctx.tick;
        out = nanArr(n);
        for (i = 0; i < n; i++) { var w = core.vw[i]; if (!(w - w === 0)) continue; if (k === 0) out[i] = w; else if (core.sd[i] >= tick) out[i] = w + k * core.sd[i]; }
        return out;
      }
      case 'sma': return rollMean(F, ev(F, x.of == null ? { f: 'close' } : x.of), posInt(x.n, 'sma n'));
      case 'ema': return emaOf(F, ev(F, x.of == null ? { f: 'close' } : x.of), posInt(x.n, 'ema n'));
      case 'hh': return rollExt(F, ev(F, x.of == null ? { f: 'high' } : x.of), posInt(x.n, 'hh n'), true);
      case 'll': return rollExt(F, ev(F, x.of == null ? { f: 'low' } : x.of), posInt(x.n, 'll n'), false);
      case 'sd': return rollSd(F, ev(F, x.of == null ? { f: 'close' } : x.of), posInt(x.n, 'sd n'));
      case 'atr': return lagged(F, atrOf(F, posInt(x.n, 'atr n', 14)), x.lag);
      case 'rsi': return lagged(F, rsiOf(F, posInt(x.n, 'rsi n', 14)), x.lag);
      case 'rvol': return rvolOf(F, posInt(x.n, 'rvol n'));
      case 'prev': return prevOf(F, x.of || 'close', posInt(x.n, 'prev n', 1));
      case 'sess': {
        of = x.of || 'high'; out = nanArr(n);
        if (of !== 'high' && of !== 'low' && of !== 'open') fail('sess : of vaut high, low ou open.');
        for (s = 0; s < S.length; s++) {
          var b0 = F.sa0[s], b1 = F.sa1[s], hi = -Infinity, lo = Infinity;
          if (b0 < 0) continue;
          for (i = b0; i <= b1; i++) {
            out[i] = of === 'open' ? F.o[b0] : i === b0 ? NaN : of === 'high' ? hi : lo;
            if (F.h[i] > hi) hi = F.h[i];
            if (F.l[i] < lo) lo = F.l[i];
          }
        }
        return out;
      }
      case 'or': return orOf(F, x);
      case 'at': {
        of = x.of || 'close'; out = nanArr(n);
        for (s = 0; s < S.length; s++) {
          var c0 = F.sa0[s], c1 = F.sa1[s]; if (c0 < 0) continue;
          var tm = smAt(ctx, s, x.time, x.tz), want = Math.floor(tm / F.m) * F.m, hitI = -1;
          for (i = c0; i <= c1; i++) if (F.sm[i] === want) { hitI = i; break; }
          if (hitI < 0) { if (S[s].sel && F.m === 1 && tm < F.sm[c1] + 1) warn(ctx, 'at : barre de ' + x.time + ' absente, séance sans valeur'); continue; }
          var val = of === 'open' ? F.o[hitI] : F.c[hitI];
          for (i = hitI; i <= c1; i++) out[i] = val;
        }
        return out;
      }
      case 'tf': {
        if (F.isTf) fail('tf imbriqué : une seule échelle de temps par opérande.');
        var m = x.m;
        if (m !== 5 && m !== 15 && m !== 30 && m !== 60) fail('tf : m vaut 5, 15, 30 ou 60.');
        var G = tfFrame(F, m), g = ev(G, x.of == null ? { f: 'close' } : x.of);
        out = nanArr(n);
        for (i = 0; i < n; i++) { var kk = G.closed[i]; if (kk >= 0 && G.seg[kk] === G.seg[G.map[i]]) out[i] = g[kk]; }
        return out;
      }
      case 'level': {
        var vals = nanArr(S.length);
        for (s = 0; s < S.length; s++) { var lv = ctx.lv[s]; if (lv && isNum(lv[x.name])) vals[s] = lv[x.name]; }
        return perSession(F, vals);
      }
      case 'nearest': {
        var above = x.side !== 'below', names = Array.isArray(x.names) && x.names.length ? x.names : null;
        out = nanArr(n);
        for (s = 0; s < S.length; s++) {
          var L = ctx.lv[s], list = [];
          for (var nm in L) if (own(L, nm) && (!names || names.indexOf(nm) >= 0)) list.push(L[nm]);
          if (!list.length || F.si0[s] < 0) continue;
          for (i = F.si0[s]; i <= F.si1[s]; i++) {
            var p = F.c[i], best = NaN;
            for (var q = 0; q < list.length; q++) { var y = list[q]; if (above ? (y > p && !(best <= y)) : (y < p && !(best >= y))) best = y; }
            out[i] = best;
          }
        }
        return out;
      }
      case 'time': {
        var tz = x.tz || ctx.tz; out = new Float64Array(n);
        for (i = 0; i < n; i++) { var wt = F.t[i] + off(tz, F.t[i]); out[i] = Math.floor((((wt % DAY) + DAY) % DAY) / MIN); }
        return out;
      }
      case 'dow': { var dv = new Float64Array(S.length); for (s = 0; s < S.length; s++) dv[s] = S[s].dow; return perSession(F, dv); }
      case 'sessmin': return F.sm;
      case 'dist': {
        var A = ev(F, x.a), B = ev(F, x.b), unit = x.unit || 'pts', den = null, k2 = 1;
        if (unit === 'ticks') k2 = ctx.tick;
        else if (unit === 'atr') den = atrOf(F, posInt(x.n, 'dist n', 14));
        else if (unit === 'sd') { var cs = vwapCore(F); den = new Float64Array(n); for (i = 0; i < n; i++) den[i] = cs.sd[i] >= ctx.tick ? cs.sd[i] : NaN; }
        else if (unit !== 'pts') fail('dist : unité pts, ticks, atr ou sd.');
        out = new Float64Array(n);
        for (i = 0; i < n; i++) out[i] = den ? (A[i] - B[i]) / den[i] : (A[i] - B[i]) / k2;
        return out;
      }
    }
    return fail('Opérande inconnu : « ' + x.f + ' ».');
  }
  function rvolOf(F, nb) {
    var ctx = F.ctx, S = ctx.S, out = nanArr(F.n), hist = {};
    if (!F.v) return out;
    for (var s = 0; s < S.length; s++) {
      var b0 = F.si0[s], b1 = F.si1[s], sg = F.seg[b0], i;
      if (b0 < 0) continue;
      for (i = b0; i <= b1; i++) {
        var h = hist[F.sm[i]], sum = 0, cnt = 0;
        if (h) for (var q = 0; q < h.length; q += 3) if (h[q] >= s - nb && h[q] < s && h[q + 2] === sg) { sum += h[q + 1]; cnt++; }
        if (cnt && sum > 0) out[i] = F.v[i] / (sum / cnt);
      }
      for (i = b0; i <= b1; i++) {
        var key = F.sm[i], arr = hist[key] || (hist[key] = []);
        arr.push(s, F.v[i] > 0 ? F.v[i] : 0, sg);
        if (arr.length > 3 * nb) arr.splice(0, arr.length - 3 * nb);
      }
    }
    return out;
  }
  function prevOf(F, of, nb) {
    if (of !== 'open' && of !== 'high' && of !== 'low' && of !== 'close') fail('prev : of vaut open, high, low ou close.');
    var ctx = F.ctx, S = ctx.S, ss = sessStats(F), per = nanArr(S.length), skipped = {}, nsk = 0;
    for (var s = 0; s < S.length; s++) {
      if (F.si0[s] < 0) continue;
      var need = nb, k = s - 1, sg = F.seg[F.si0[s]];
      while (k >= 0) {
        if (F.si0[k] < 0 || F.seg[F.si0[k]] !== sg) break;
        if (ss.cnt[k] * F.m >= 0.8 * S[k].exp) { if (--need === 0) { per[s] = ss[of][k]; break; } }
        else if (!skipped[k]) { skipped[k] = 1; nsk++; }
        k--;
      }
    }
    if (nsk) for (var w = 0; w < nsk; w++) warn(ctx, 'prev : séance de moins de 80 % des barres attendues, sautée');
    return perSession(F, per);
  }
  function orOf(F, x) {
    var ctx = F.ctx, S = ctx.S, of = x.of || 'high', out = nanArr(F.n);
    if (['high', 'low', 'mid', 'open', 'close'].indexOf(of) < 0) fail('or : of vaut high, low, mid, open ou close.');
    for (var s = 0; s < S.length; s++) {
      var a0 = F.sa0[s], a1 = F.sa1[s], i;
      if (a0 < 0) continue;
      var f = smAt(ctx, s, x.from, x.tz), t = smAt(ctx, s, x.to, x.tz);
      if (!(f < t)) continue;
      var hi = -Infinity, lo = Infinity, op = NaN, cl = NaN, cnt = 0;
      for (i = a0; i <= a1; i++) {
        var m = F.sm[i];
        if (m < f) continue;
        if (m >= t) break;
        if (!cnt) op = F.o[i];
        cl = F.c[i]; cnt++;
        if (F.h[i] > hi) hi = F.h[i];
        if (F.l[i] < lo) lo = F.l[i];
      }
      if (!cnt) { if (S[s].sel && F.m === 1) warn(ctx, 'or : aucune barre dans le range'); continue; }
      if (F.m === 1 && cnt < t - f && S[s].sel) warn(ctx, 'or : range incomplet');
      var v = of === 'high' ? hi : of === 'low' ? lo : of === 'mid' ? (hi + lo) / 2 : of === 'open' ? op : cl;
      for (i = a0; i <= a1; i++) if (F.sm[i] >= t) out[i] = v;
    }
    return out;
  }

  /* ---------- Conditions (3.3) : 1 vraie, 0 fausse, 2 indéfinie ---------- */
  function cv(F, c) {
    var kind = condKind(c), key = 'c:' + canon(c), hit = F.cache[key];
    if (hit) return hit;
    var n = F.n, out = new Uint8Array(n), i, A, B, C = F.c, x, y, x0, y0;
    function edge(j) { return j === 0 || F.firstA[j] || j - 1 < F.seg[j]; }
    switch (kind) {
      case 'cmp': {
        A = ev(F, c.a); B = ev(F, c.b);
        var op = c.cmp;
        if (!FLIP[op]) fail('Comparaison inconnue : « ' + op + ' ».');
        for (i = 0; i < n; i++) {
          x = A[i]; y = B[i];
          if (!(x - x === 0 && y - y === 0)) { out[i] = 2; continue; }
          out[i] = (op === '>' ? x > y : op === '<' ? x < y : op === '>=' ? x >= y : x <= y) ? 1 : 0;
        }
        break;
      }
      case 'cross': {
        A = ev(F, c.a); B = ev(F, c.b);
        var up = c.cross === 'up';
        if (!up && c.cross !== 'down') fail('cross : up ou down.');
        for (i = 0; i < n; i++) {
          if (edge(i)) continue;
          x0 = A[i - 1]; y0 = B[i - 1]; x = A[i]; y = B[i];
          if (!(x - x === 0 && y - y === 0 && x0 - x0 === 0 && y0 - y0 === 0)) { out[i] = 2; continue; }
          out[i] = (up ? x0 <= y0 && x > y : x0 >= y0 && x < y) ? 1 : 0;
        }
        break;
      }
      case 'touch': case 'reject': {
        A = ev(F, c[kind]);
        var above = c.from === 'above';
        if (!above && c.from !== 'below') fail(kind + ' : from vaut above ou below.');
        for (i = 0; i < n; i++) {
          if (edge(i)) continue;
          x = A[i]; x0 = A[i - 1];
          if (!(x - x === 0 && x0 - x0 === 0)) { out[i] = 2; continue; }
          var tch = above ? F.l[i] <= x && C[i - 1] > x0 : F.h[i] >= x && C[i - 1] < x0;
          if (kind === 'reject') tch = tch && (above ? C[i] > x : C[i] < x);
          out[i] = tch ? 1 : 0;
        }
        break;
      }
      case 'break': {
        A = ev(F, c['break']);
        var bu = c.dir === 'up';
        if (!bu && c.dir !== 'down') fail('break : dir vaut up ou down.');
        for (i = 0; i < n; i++) {
          if (edge(i)) continue;
          x = A[i]; x0 = A[i - 1];
          if (!(x - x === 0 && x0 - x0 === 0)) { out[i] = 2; continue; }
          out[i] = (bu ? C[i] > x && C[i - 1] <= x0 : C[i] < x && C[i - 1] >= x0) ? 1 : 0;
        }
        break;
      }
      case 'bar': {
        var bup = c.bar === 'up';
        if (!bup && c.bar !== 'down') fail('bar : up ou down.');
        for (i = 0; i < n; i++) out[i] = (bup ? C[i] > F.o[i] : C[i] < F.o[i]) ? 1 : 0;
        break;
      }
      case 'time': {
        if (!Array.isArray(c.time) || c.time.length !== 2) fail('time : deux heures HH:MM attendues.');
        var S = F.ctx.S;
        for (var s = 0; s < S.length; s++) {
          if (F.si0[s] < 0) continue;
          var ta = smAt(F.ctx, s, c.time[0], c.tz), tb = smAt(F.ctx, s, c.time[1], c.tz);
          for (i = F.si0[s]; i <= F.si1[s]; i++) { var m = F.sm[i]; out[i] = (ta <= tb ? m >= ta && m < tb : m >= ta || m < tb) ? 1 : 0; }
        }
        break;
      }
      case 'news': {
        var nw = c.news || {}, imp = isNum(nw.impact) ? nw.impact : 1, bf = (isNum(nw.before) ? nw.before : 0) * MIN, af = (isNum(nw.after) ? nw.after : 0) * MIN;
        var NT = F.ctx.news.t, NI = F.ctx.news.imp, ts = [];
        for (i = 0; i < NT.length; i++) if (NI[i] >= imp) ts.push(NT[i]);
        var p = 0;
        for (i = 0; i < n; i++) {
          var T0 = F.t[i] + MIN, lo = T0 - bf, hiT = T0 + af;
          while (p < ts.length && ts[p] < lo) p++;
          out[i] = p < ts.length && ts[p] <= hiT ? 0 : 1;
        }
        break;
      }
      case 'all': case 'any': {
        var list = (c[kind] || []).map(function (z) { return cv(F, z); }), isAll = kind === 'all';
        for (i = 0; i < n; i++) {
          var und = false, res = isAll ? 1 : 0;
          for (var q = 0; q < list.length; q++) {
            var v = list[q][i];
            if (isAll && v === 0) { res = 0; und = false; break; }
            if (!isAll && v === 1) { res = 1; und = false; break; }
            if (v === 2) und = true;
          }
          out[i] = und ? 2 : res;
        }
        break;
      }
      case 'not': { A = cv(F, c.not); for (i = 0; i < n; i++) out[i] = A[i] === 2 ? 2 : 1 - A[i]; break; }
      case 'for': case 'within': {
        var w = posInt(c[kind], kind), X = cv(F, c.cond), isFor = kind === 'for';
        for (i = 0; i < n; i++) {
          var z0 = i - w + 1, nz = 0, n1 = 0, n2 = z0 < F.seg[i] ? 1 : 0;
          for (var j = Math.max(z0, F.seg[i]); j <= i; j++) { var u = X[j]; if (u === 0) nz++; else if (u === 1) n1++; else n2++; }
          out[i] = isFor ? (nz ? 0 : n2 ? 2 : 1) : (n1 ? 1 : n2 ? 2 : 0);
        }
        break;
      }
    }
    F.cache[key] = out;
    return out;
  }

  /* ---------- Configuration : règles, signaux bruts, domaine ---------- */
  function signals(ctx, rule) {
    var F = ctx.F1, n = F.n, out = new Uint8Array(n), conds = (rule.setup || []).slice(), i, k;
    if (!rule.trigger) fail('Déclencheur absent.');
    conds.push(rule.trigger);
    var arrs = conds.map(function (c) { return cv(F, c); }), na = arrs.length;
    for (i = 0; i < n; i++) {
      if (!F.anch[i]) continue;
      var ok = 1;
      for (k = 0; k < na; k++) if (arrs[k][i] !== 1) { ok = 0; break; }
      out[i] = ok;
    }
    return out;
  }
  function domain(ctx, spec) {
    var ses = spec.session || {}, key = canon(ses), d = ctx.dom[key];
    if (d) return d;
    var S = ctx.S, F = ctx.F1, ns = S.length, tz = ses.tz || PAR, s, i;
    var from = new Float64Array(ns), to = new Float64Array(ns), flat = new Float64Array(ns), end = new Float64Array(ns), trade = new Uint8Array(ns), cons = new Uint8Array(F.n);
    var days = null, warm = isNum(ses.warmup) ? ses.warmup : 0;
    if (Array.isArray(ses.days)) { days = {}; ses.days.forEach(function (x) { days[x] = 1; }); }
    for (s = 0; s < ns; s++) {
      from[s] = smAt(ctx, s, ses.from || '00:00', tz);
      to[s] = smAt(ctx, s, ses.to || '09:00', tz);
      flat[s] = smAt(ctx, s, ses.flat || ses.to || '09:00', tz);
      end[s] = Math.min(to[s], flat[s]);
      if (ctx.anchor === 'rth' && (from[s] >= 390 || to[s] > 390 || flat[s] > 390)) fail('Ancrage rth : la fenêtre et la sortie forcée doivent tenir dans 09:30–16:00 (New York).');
      var ok = S[s].sel && (!days || !!days[S[s].dow]);
      if (ok && !(from[s] < end[s])) { warn(ctx, 'fenêtre vide ou à cheval sur l’ancre : séance ignorée'); ok = false; }
      trade[s] = ok ? 1 : 0;
      if (!ok) continue;
      for (i = F.si0[s]; i <= F.si1[s]; i++) { var m = F.sm[i]; if (F.anch[i] && m >= warm && m + 1 >= from[s] && m < end[s]) cons[i] = 1; }
    }
    d = ctx.dom[key] = { from: from, to: to, flat: flat, end: end, trade: trade, cons: cons, warm: warm };
    return d;
  }
  /* 0 exécutable ; 1 expire ; 2 trou de données — pour un ordre parti à la clôture de i */
  function nextStatus(F, i, endS) {
    var j = i + 1;
    if (j >= F.n || F.sess[j] !== F.sess[i]) return 1;
    if (F.t[j] - F.t[i] !== MIN) return 2;
    if (F.sm[j] >= endS) return 1;
    return 0;
  }
  function executable(ctx, cfg) {
    var F = ctx.F1, dom = cfg.dom, out = new Uint8Array(F.n);
    for (var i = 0; i < F.n; i++) if (dom.cons[i] && nextStatus(F, i, dom.end[F.sess[i]]) === 0) out[i] = 1;
    return out;
  }
  function config(ctx, values, specOverride) {
    var spec = withDefaults(resolveSpec(specOverride ? withDefaults(specOverride) : ctx.spec0, values));
    var side = spec.side || 'long';
    if (side !== 'long' && side !== 'short' && side !== 'both') fail('Sens inconnu : « ' + side + ' ».');
    var sides = { L: side !== 'short', S: side !== 'long' }, L = null, Sr = null;
    if (spec.long) L = spec.long;
    if (spec.mirror !== false) { if (!L) fail('Règle acheteuse absente (long).'); if (sides.S || spec.manage.exitOnOpposite) Sr = mSide(L); }
    else if (spec.short) Sr = spec.short;
    if (sides.L && !L) fail('Règle acheteuse absente (long).');
    if (sides.S && !Sr) fail('Côté vendeur absent : short est obligatoire quand mirror vaut false.');
    if (L && !L.stop) fail('Stop absent.');
    if (Sr && !Sr.stop) fail('Stop du côté vendeur absent.');
    var opp = !!spec.manage.exitOnOpposite;
    var sig = { L: L && (sides.L || (opp && sides.S)) ? signals(ctx, L) : null, S: Sr && (sides.S || (opp && sides.L)) ? signals(ctx, Sr) : null };
    return { spec: spec, rules: { L: L, S: Sr }, sides: sides, sig: sig, dom: domain(ctx, spec) };
  }
  function scanRules(rules, fn) {
    var hit = false;
    function op(x) { if (hit || !x || typeof x !== 'object') return; if (fn(x, 'op')) { hit = true; return; } if (own(x, 'op')) { op(x.a); op(x.b); return; } if (x.of && typeof x.of === 'object') op(x.of); if (x.f === 'dist') { op(x.a); op(x.b); } }
    function cd(c) {
      if (hit || !c || typeof c !== 'object') return;
      if (fn(c, 'cond')) { hit = true; return; }
      ['a', 'b', 'touch', 'reject', 'break'].forEach(function (k) { if (own(c, k)) op(c[k]); });
      if (c.all) c.all.forEach(cd); if (c.any) c.any.forEach(cd); if (c.not) cd(c.not); if (c.cond) cd(c.cond);
    }
    [rules.L, rules.S].forEach(function (r) {
      if (!r) return;
      (r.setup || []).forEach(cd); cd(r.trigger);
      [r.entry, r.stop, r.target].forEach(function (o) { if (o && o.at) op(o.at); });
    });
    return hit;
  }
  function usesExternal(cfg) {
    return scanRules(cfg.rules, function (x, kind) { return kind === 'op' ? x.f === 'level' || x.f === 'nearest' : own(x, 'news'); });
  }

  /* ---------- Exécution (3.5 – 3.7) ---------- */
  function execute(ctx, cfg, o) {
    o = o || {};
    var F = ctx.F1, S = ctx.S, spec = cfg.spec, R = spec.risk || {}, M = spec.manage || {}, dom = cfg.dom, tick = ctx.tick, pv = ctx.pv;
    var fill = o.fill || spec.fill || 'pessimiste';
    if (fill !== 'pessimiste' && fill !== 'optimiste' && fill !== 'chemin' && fill !== 'vrai') fail('Remplissage inconnu : « ' + fill + ' ».');
    if (fill === 'vrai' && !F.lf) { warn(ctx, 'remplissage vrai sans ordre intrabarre : lu en chemin'); fill = 'chemin'; }
    var costs = spec.costs || {};
    var slip = isNum(o.slipTicks) ? o.slipTicks : isNum(costs.slipTicks) ? costs.slipTicks : 0;
    var comm = isNum(o.commissionRT) ? o.commissionRT : isNum(costs.commissionRT) ? costs.commissionRT : ctx.comm;
    var xt = isNum(o.throughTicks) ? o.throughTicks : 0, slipT = slip * tick, xtT = xt * tick;
    var sig = o.sig || cfg.sig, sigL = cfg.sides.L ? sig.L : null, sigS = cfg.sides.S ? sig.S : null;
    var opp = !!M.exitOnOpposite, oppL = opp ? cfg.sig.S : null, oppS = opp ? cfg.sig.L : null;
    var cooldown = isNum(R.cooldown) && R.cooldown > 0 ? Math.floor(R.cooldown) : 0;
    var maxPer = isNum(R.maxPerSession) && R.maxPerSession > 0 ? R.maxPerSession : Infinity;
    var maxLoss = isNum(R.maxLossesPerSession) && R.maxLossesPerSession > 0 ? R.maxLossesPerSession : Infinity;
    var dstop = isNum(R.dailyStopUsd) && R.dailyStopUsd > 0 ? R.dailyStopUsd : Infinity;
    var minStop = isNum(R.minStopTicks) && R.minStopTicks > 0 ? R.minStopTicks * tick : 0;
    var maxBars = isNum(M.maxBars) && M.maxBars >= 1 ? Math.floor(M.maxBars) : 0;
    var be = M.breakeven == null || M.breakeven === false ? null : typeof M.breakeven === 'number' ? { r: M.breakeven, off: 0 } : { r: isNum(M.breakeven.r) ? M.breakeven.r : 1, off: (isNum(M.breakeven.offset) ? M.breakeven.offset : 0) * tick };
    var trl = M.trail && typeof M.trail === 'object' ? M.trail : null;
    var only = o.sessions || null, fb = o.fallback || null, lf = F.lf, nS = S.length;
    var counts = { signals: 0, ambigu: 0, taille: 0, stopcourt: 0, ecart: 0, annule: 0, expire: 0, trou: 0, marketable: 0, limite: 0 };
    var trades = [], sessions = [], legsSum = 0;
    function reachT(px, tg, side, through) { return side > 0 ? (through ? px > tg + xtT : px >= tg + xtT) : (through ? px < tg - xtT : px <= tg - xtT); }
    function pathA(j, side) {   /* vrai si la barre se lit « contraire d’abord » (O → extrême adverse → extrême favorable → C) */
      if (fill === 'vrai') return side > 0 ? !!lf[j] : !lf[j];
      var c = F.c[j], op = F.o[j];
      return c === op ? true : side > 0 ? c > op : c < op;
    }
    function stopFrom(sp, side, base, i) {
      var buf = (isNum(sp.buffer) ? sp.buffer : 0) * tick, v;
      switch (sp.type) {
        case 'pts': v = base - side * sp.value; break;
        case 'atr': v = base - side * sp.value * atrOf(F, posInt(sp.n, 'stop atr n', 14))[i]; break;
        case 'swing': {
          var nb = posInt(sp.n, 'stop swing n'), j0 = i - nb + 1;
          if (j0 < F.seg[i]) return NaN;
          v = side > 0 ? Infinity : -Infinity;
          for (var j = j0; j <= i; j++) v = side > 0 ? Math.min(v, F.l[j]) : Math.max(v, F.h[j]);
          break;
        }
        case 'level': v = ev(F, sp.at)[i]; break;
        default: fail('Stop inconnu : « ' + sp.type + ' ».');
      }
      return v - side * buf;
    }
    function targetFrom(tg, side, entry, L, i) {
      switch (tg.type) {
        case 'r': return entry + side * tg.value * L;
        case 'pts': return entry + side * tg.value;
        case 'atr': return entry + side * tg.value * atrOf(F, posInt(tg.n, 'objectif atr n', 14))[i];
        case 'level': return ev(F, tg.at)[i];
        case 'none': case undefined: case null: return NaN;
      }
      return fail('Objectif inconnu : « ' + tg.type + ' ».');
    }
    for (var s = 0; s < nS; s++) {
      if (!dom.trade[s] || (only && !only[s])) continue;
      var sx = sessions.length, endS = dom.end[s], flatS = dom.flat[s], sI1 = F.si1[s];
      var srec = { key: S[s].key, s: s, dow: S[s].dow, pnl: 0, n: 0, lo: 0, hi: 0, sig: 0, sumR: 0, sumR2: 0 }, nLoss = 0, cum = 0;
      sessions.push(srec);
      if (o.progress !== false) progress(sx, nS);
      var i = F.si0[s];
      while (i <= sI1) {
        if (!dom.cons[i]) { i++; continue; }
        var isL = sigL ? sigL[i] : 0, isS = sigS ? sigS[i] : 0;
        if (!isL && !isS) { i++; continue; }
        if (srec.n >= maxPer || nLoss >= maxLoss || -srec.pnl >= dstop) { counts.limite++; i++; continue; }
        counts.signals++; srec.sig++;
        if (isL && isS) { counts.ambigu++; i++; continue; }
        var side = isL ? 1 : -1, rule = side > 0 ? cfg.rules.L : cfg.rules.S, E = rule.entry || { type: 'market' }, type = E.type || 'market';
        var st = nextStatus(F, i, endS);
        if (st) { counts[st === 2 ? 'trou' : 'expire']++; i++; continue; }
        /* l’ordre part à la clôture de i */
        var price = NaN, through = !!E.through;
        if (type === 'limit' || type === 'stop') {
          var atv = ev(F, E.at)[i];
          if (!(atv - atv === 0)) { counts.annule++; i++; continue; }
          var ofs = (isNum(E.offset) ? E.offset : 0) * tick;
          price = type === 'limit' ? atv - side * ofs : atv + side * ofs;
        } else if (type !== 'market') fail('Entrée inconnue : « ' + type + ' ».');
        var qty;
        if (R.mode === 'risk') {
          var ref = type === 'market' ? F.c[i] : price, sref = stopFrom(rule.stop, side, ref, i);
          if (!(sref - sref === 0)) { if (fb && rule.stop.type === 'level') sref = ref - side * fb.stop; else { counts.annule++; i++; continue; } }
          var dist = Math.abs(ref - sref);
          qty = Math.floor(R.riskUsd / (dist * pv + comm) + 1e-9);
          if (isNum(R.maxQty) && R.maxQty > 0) qty = Math.min(qty, Math.floor(R.maxQty));
          if (ctx.maxC) qty = Math.min(qty, ctx.maxC);
        } else qty = isNum(R.contracts) ? Math.floor(R.contracts) : 1;
        if (!(qty >= 1)) { counts.taille++; i++; continue; }
        /* remplissage */
        var e = -1, raw = NaN, kind = 'open', slipped = false, mk = false, next = i + 1, why = null;
        if (type === 'market') { e = i + 1; raw = F.o[e]; slipped = true; }
        else {
          var vb = E.valid == null ? 1 : E.valid, vsm = null;
          if (typeof vb === 'string') { vsm = smAt(ctx, s, vb, E.tz); vb = Infinity; }
          else vb = posInt(vb, 'valid');
          for (var j = i + 1; ; j++) {
            if (j > i + 1) {
              var ps = nextStatus(F, j - 1, endS);
              if (ps) { why = ps === 2 ? 'trou' : 'expire'; next = j - 1; break; }
            }
            if (j > i + vb || (vsm !== null && F.sm[j] >= vsm)) { why = 'expire'; next = j - 1; break; }
            var O = F.o[j];
            if (type === 'limit') {
              if (j === i + 1 && (side > 0 ? price >= O : price <= O)) { e = j; raw = O; slipped = true; mk = true; break; }
              if (side > 0 ? (through ? O < price - xtT : O <= price - xtT) : (through ? O > price + xtT : O >= price + xtT)) { e = j; raw = O; break; }
              if (side > 0 ? (through ? F.l[j] < price - xtT : F.l[j] <= price - xtT) : (through ? F.h[j] > price + xtT : F.h[j] >= price + xtT)) { e = j; raw = price; kind = price === O ? 'open' : 'lim'; break; }
            } else {
              if (side > 0 ? F.h[j] >= price : F.l[j] <= price) { e = j; raw = side > 0 ? Math.max(O, price) : Math.min(O, price); kind = raw === O ? 'open' : 'stp'; slipped = true; break; }
            }
          }
          if (why) { counts[why]++; i = Math.max(i + 1, next); continue; }
          if (mk) counts.marketable++;
        }
        /* stop et objectif fixés à l’exécution */
        var entry = slipped ? raw + side * slipT : raw, useFb = false;
        var stop0 = stopFrom(rule.stop, side, entry, i);
        var beyond = side > 0 ? raw <= stop0 : raw >= stop0;
        if (!(stop0 - stop0 === 0) || beyond) {
          if (fb && rule.stop.type === 'level') { stop0 = entry - side * fb.stop; useFb = true; }
          else { counts[beyond ? 'ecart' : 'annule']++; i = e; continue; }
        }
        var L = Math.abs(entry - stop0);
        if (!(L > 0) || L < minStop - 1e-9) { counts.stopcourt++; i = e; continue; }
        var TG = rule.target || { type: 'none' }, dyn = TG.type === 'level' && !!TG.dynamic, tdyn = dyn ? ev(F, TG.at) : null;
        var tgt0 = dyn ? tdyn[e - 1] : targetFrom(TG, side, entry, L, i), hasT = TG.type && TG.type !== 'none';
        if (hasT && (!(tgt0 - tgt0 === 0) || reachT(raw, tgt0, side, through))) {
          if (fb && TG.type === 'level') { tgt0 = entry + side * fb.target; dyn = false; useFb = true; }
          else { counts.annule++; i = e; continue; }
        }
        /* gestion barre par barre (3.6) */
        var stop = stop0, sKind = 'stop', advX = side > 0 ? Infinity : -Infinity, favX = side > 0 ? -Infinity : Infinity;
        var trDist = NaN, trStart = 0;
        if (trl) {
          trStart = isNum(trl.start) ? trl.start : 0;
          var ttype = trl.type || 'pts', tv = isNum(trl.value) ? trl.value : trl.dist;
          trDist = ttype === 'atr' ? tv * atrOf(F, posInt(trl.n, 'suiveur atr n', 14))[i] : ttype === 'r' ? tv * L : tv;
          if (!(trDist > 0)) trDist = NaN;
        }
        var oppA = side > 0 ? oppL : oppS, xj = -1, xp = NaN, fin = '', xleg = 0, how = '', tgL = tgt0;
        for (var jj = e; ; jj++) {
          var Oj = F.o[jj], Hj = F.h[jj], Lj = F.l[jj], Cj = F.c[jj], tg = dyn ? tdyn[jj - 1] : tgt0, hasTg = hasT && tg - tg === 0;
          tgL = tg;
          if (jj > e) {
            if (F.sm[jj] >= flatS) { xj = jj; xp = Oj - side * slipT; fin = 'flat'; xleg = 1; how = 'open'; break; }
            if (side > 0 ? Oj <= stop : Oj >= stop) { xj = jj; xp = Oj - side * slipT; fin = sKind; xleg = 1; how = 'open'; break; }
            if (hasTg && reachT(Oj, tg, side, through)) { xj = jj; xp = Oj; fin = 'objectif'; how = 'open'; break; }
          }
          var sHit = side > 0 ? Lj <= stop : Hj >= stop, tHit = hasTg && reachT(side > 0 ? Hj : Lj, tg, side, through), ex = 0;
          if (jj === e && kind === 'lim') {
            var cT = hasTg && reachT(Cj, tg, side, through);
            if (fill === 'pessimiste') ex = sHit ? 1 : cT ? 2 : 0;
            else if (fill === 'optimiste') ex = tHit ? 2 : sHit ? 1 : 0;
            else ex = sHit ? 1 : pathA(jj, side) ? (tHit ? 2 : 0) : (cT ? 2 : 0);
          } else if (jj === e && kind === 'stp') {
            var cS = side > 0 ? Cj <= stop : Cj >= stop;
            if (fill === 'pessimiste') ex = sHit ? 1 : tHit ? 2 : 0;
            else if (fill === 'optimiste') ex = tHit ? 2 : cS ? 1 : 0;
            else ex = tHit ? 2 : pathA(jj, side) ? (cS ? 1 : 0) : (sHit ? 1 : 0);
          } else if (sHit && tHit) ex = fill === 'pessimiste' ? 1 : fill === 'optimiste' ? 2 : pathA(jj, side) ? 1 : 2;
          else ex = sHit ? 1 : tHit ? 2 : 0;
          if (ex === 1) { xj = jj; xp = stop - side * slipT; fin = sKind; xleg = 1; how = 'S'; break; }
          if (ex === 2) { xj = jj; xp = tg; fin = 'objectif'; how = 'T'; break; }
          if (maxBars && jj - e + 1 >= maxBars) { xj = jj; xp = Cj - side * slipT; fin = 'temps'; xleg = 1; how = 'C'; break; }
          if (oppA && oppA[jj] && jj + 1 < F.n && F.sess[jj + 1] === s) {
            advX = side > 0 ? Math.min(advX, Lj) : Math.max(advX, Hj); favX = side > 0 ? Math.max(favX, Hj) : Math.min(favX, Lj);
            xj = jj + 1; xp = F.o[jj + 1] - side * slipT; fin = 'oppose'; xleg = 1; how = 'open'; break;
          }
          if (jj >= sI1) { xj = jj; xp = Cj - side * slipT; fin = 'cloche'; xleg = 1; how = 'C'; break; }
          advX = side > 0 ? Math.min(advX, Lj) : Math.max(advX, Hj);
          favX = side > 0 ? Math.max(favX, Hj) : Math.min(favX, Lj);
          if (be && side * ((side > 0 ? Hj : Lj) - entry) >= be.r * L) { var nb_ = entry + side * be.off; if (side * (nb_ - stop) > 0) { stop = nb_; sKind = 'be'; } }
          if (trDist === trDist && side * (favX - entry) >= trStart * L) { var nt = favX - side * trDist; if (side * (nt - stop) > 0) { stop = nt; sKind = 'trail'; } }
        }
        /* excursions : barres avant la sortie entières, barre de sortie bornée par le stop et l’objectif */
        var aX = advX, fX = favX;
        if (how === 'open') { var Ox = F.o[xj]; aX = side > 0 ? Math.min(aX, Ox) : Math.max(aX, Ox); fX = side > 0 ? Math.max(fX, Ox) : Math.min(fX, Ox); }
        else {
          var lo_ = F.l[xj], hi_ = F.h[xj], tOk = hasT && tgL - tgL === 0;
          if (side > 0) { aX = Math.min(aX, how === 'S' ? stop : Math.max(lo_, stop)); fX = Math.max(fX, how === 'T' ? tgL : tOk ? Math.min(hi_, tgL) : hi_); }
          else { aX = Math.max(aX, how === 'S' ? stop : Math.min(hi_, stop)); fX = Math.min(fX, how === 'T' ? tgL : tOk ? Math.max(lo_, tgL) : lo_); }
        }
        var mae = Math.max(0, side > 0 ? entry - aX : aX - entry), mfe = Math.max(0, side > 0 ? fX - entry : entry - fX);
        var legs = (slipped ? 1 : 0) + xleg, pts = side * (xp - entry), pnl = qty * (pts * pv - comm), r = pnl / (qty * L * pv), cst = comm + tick * pv * slip * legs;
        var te = F.t[e], tr = { i: i, e: e, j: xj, t: te, tx: F.t[xj], key: S[s].key, sx: sx, side: side, qty: qty, entry: entry, stop0: stop0, target0: hasT && tgt0 - tgt0 === 0 ? tgt0 : null, exit: xp, fin: fin, pts: pts, pnl: pnl, r: r, risk: L, c: cst, legs: legs, mae: mae, mfe: mfe, bars: xj - e + 1, hour: Math.floor(((((te + off(ctx.tz, te)) % DAY) + DAY) % DAY) / HOUR), dow: S[s].dow };
        if (mk) tr.mk = 1;
        if (useFb) tr.fb = 1;
        trades.push(tr); legsSum += legs;
        srec.lo = Math.min(srec.lo, cum - qty * (mae * pv + comm));
        srec.hi = Math.max(srec.hi, cum + qty * (mfe * pv - comm));
        cum += pnl; srec.pnl = cum; srec.n++; srec.sumR += r; srec.sumR2 += r * r;
        srec.lo = Math.min(srec.lo, cum); srec.hi = Math.max(srec.hi, cum);
        if (pnl < 0) nLoss++;
        i = Math.max(xj + cooldown, i + 1);
      }
    }
    if (o.progress !== false) progress(nS, nS);
    return { trades: trades, counts: counts, sessions: sessions, fill: fill, costs: { commissionRT: comm, slipTicks: slip, throughTicks: xt, tick: tick, pointValue: pv, slipTicksRT: trades.length ? slip * legsSum / trades.length : 0 } };
  }

  /* ---------- Statistiques d’un run (4.1) ---------- */
  function statsOf(tr, pv) {
    pv = isNum(pv) && pv > 0 ? pv : 2;
    var n = tr.length, rs = [], wins = 0, losses = 0, sW = 0, sL = 0, w$ = 0, l$ = 0, net = 0, eq = 0, pk = 0, dd = 0, cR = 0, nC = 0, sRisk = 0, sCost = 0, byFin = {}, i;
    for (i = 0; i < n; i++) {
      var t = tr[i], r = t.r, q = isNum(t.qty) ? t.qty : 1;
      if (isNum(r)) { rs.push(r); if (r > 0) { wins++; sW += r; w$ += t.pnl; } else if (r < 0) { losses++; sL -= r; l$ += t.pnl; } }
      net += t.pnl; eq += t.pnl; if (eq > pk) pk = eq; if (pk - eq > dd) dd = pk - eq;
      if (isNum(t.c) && t.risk > 0) { cR += t.c / (t.risk * pv); nC++; sRisk += q * t.risk * pv; sCost += q * t.c; }
      var b = byFin[t.fin] || (byFin[t.fin] = { n: 0, sumR: 0, net: 0 });
      b.n++; b.net += t.pnl; if (isNum(r)) b.sumR += r;
    }
    for (var k in byFin) if (own(byFin, k)) byFin[k].meanR = byFin[k].n ? byFin[k].sumR / byFin[k].n : NaN;
    var m = rs.length, mean = NaN, sd = NaN, skew = 0, exk = 0;
    if (m) {
      var s1 = 0; for (i = 0; i < m; i++) s1 += rs[i]; mean = s1 / m;
      var m2 = 0, m3 = 0, m4 = 0;
      for (i = 0; i < m; i++) { var d = rs[i] - mean; m2 += d * d; m3 += d * d * d; m4 += d * d * d * d; }
      m2 /= m; m3 /= m; m4 /= m;
      sd = m > 1 ? Math.sqrt(m2 * m / (m - 1)) : NaN;
      skew = m2 > 0 ? m3 / Math.pow(m2, 1.5) : 0; exk = m2 > 0 ? m4 / (m2 * m2) - 3 : 0;
    }
    var Wb = wins ? sW / wins : 0, Lb = losses ? sL / losses : 0;
    return { n: n, nz: wins + losses, wins: wins, losses: losses, winRate: wins + losses ? wins / (wins + losses) : NaN, meanR: mean, sdR: sd, skew: skew, exkurt: exk,
      sharpeTrade: sd > 0 ? mean / sd : NaN, net: net, avgWin: wins ? w$ / wins : NaN, avgLoss: losses ? l$ / losses : NaN,
      pf: l$ < 0 ? w$ / -l$ : (w$ > 0 ? Infinity : NaN), maxDD: dd, expectancy: n ? net / n : NaN,
      equilibrium: Wb + Lb > 0 ? Lb / (Wb + Lb) : NaN, costR: nC ? cR / nC : NaN, rW: sRisk > 0 ? net / sRisk : NaN, rW0: sRisk > 0 ? -sCost / sRisk : NaN, byFin: byFin };
  }
  function equity(tr) { var out = [], c = 0; for (var i = 0; i < tr.length; i++) { c += tr[i].pnl; out.push([tr[i].tx, c]); } return out; }

  /* ---------- Marche sans dérive sur le réseau des ticks (4.4) ---------- */
  function lattice(o) {
    o = o || {};
    var nS = Math.max(1, Math.floor(isNum(o.sessions) ? o.sessions : 20)), tick = isNum(o.tick) && o.tick > 0 ? o.tick : 0.25, sigma = isNum(o.sigma) && o.sigma > 0 ? o.sigma : 2;
    var minutes = Math.max(1, Math.floor(isNum(o.minutes) ? o.minutes : 1380)), k = Math.max(1, Math.round((sigma / tick) * (sigma / tick))), base = isNum(o.base) ? o.base : 20000;
    var r = rng((isNum(o.seed) ? o.seed : 1) >>> 0), N = nS * minutes;
    var t = new Float64Array(N), op = new Float64Array(N), hi = new Float64Array(N), lo = new Float64Array(N), cl = new Float64Array(N), v = new Float64Array(N), lf = new Uint8Array(N);
    var dn = dnOfKey(o.start || '2026-01-05'), made = 0, p = 0, idx = 0, bits = 0, nb = 0, keys = [];
    while (made < nS) {
      if (dowOf(dn) <= 5) {
        var t0 = wallAt(dn - 1, 18 * 60, NY);
        keys.push(dayStr(dn));
        for (var mi = 0; mi < minutes; mi++) {
          var p0 = p, ph = p, pl = p, th = 0, tl = 0;
          for (var st = 1; st <= k; st++) {
            if (nb === 0) { bits = (r() * 4294967296) >>> 0; nb = 32; }
            p += (bits & 1) ? 1 : -1; bits >>>= 1; nb--;
            if (p > ph) { ph = p; th = st; } else if (p < pl) { pl = p; tl = st; }
          }
          t[idx] = t0 + mi * MIN; op[idx] = base + p0 * tick; hi[idx] = base + ph * tick; lo[idx] = base + pl * tick; cl[idx] = base + p * tick;
          v[idx] = 20 + Math.floor(r() * 100); lf[idx] = tl < th ? 1 : 0;
          idx++;
        }
        made++;
      }
      dn++;
    }
    return { t: t, o: op, h: hi, l: lo, c: cl, v: v, lowFirst: lf, k: k, sigma: tick * Math.sqrt(k), keys: keys };
  }
  /* σ de 4.4 : médiane, sur les séances jouées, de l’écart-type des variations de clôture d’une minute dans la fenêtre */
  function sigmaOf(ctx, cfg) {
    var F = ctx.F1, S = ctx.S, dom = cfg.dom, sds = [];
    for (var s = 0; s < S.length; s++) {
      if (!dom.trade[s]) continue;
      var xs = [];
      for (var i = F.si0[s] + 1; i <= F.si1[s]; i++) {
        var m0 = F.sm[i - 1], m1 = F.sm[i];
        if (F.t[i] - F.t[i - 1] !== MIN || m0 < dom.from[s] || m1 >= dom.to[s]) continue;
        xs.push(F.c[i] - F.c[i - 1]);
      }
      if (xs.length < 2) continue;
      var mu = 0, q = 0, j; for (j = 0; j < xs.length; j++) mu += xs[j]; mu /= xs.length;
      for (j = 0; j < xs.length; j++) q += (xs[j] - mu) * (xs[j] - mu);
      sds.push(Math.sqrt(q / (xs.length - 1)));
    }
    if (!sds.length) return NaN;
    sds.sort(function (x, y) { return x - y; });
    var h = sds.length;
    return h % 2 ? sds[(h - 1) / 2] : (sds[h / 2 - 1] + sds[h / 2]) / 2;
  }
  function toList(arr, i0, i1) { var out = []; for (var i = i0; i <= i1; i++) { var x = arr[i]; out.push(x - x === 0 ? x : null); } return out; }

  /* =====================================================================================
     TABLE DES OPÉRATIONS — le seul endroit où une opération s’enregistre.
     À ajouter ici, dans ce même corps : random (4.2), permute et permuteGrid (4.3), sweep (avec la
     matrice mat[config][séance] : {n, sumR, sumR2, net} — voir sessions[x] de execute), wfa (4.5),
     stress (4.7), boot (4.6). Chaque opération lit `a` et rend un objet sérialisable.
     ===================================================================================== */
  var OPS = {
    resolve: function () { return resolveSpec(a.spec, a.values); },
    mirror: function () {
      if (a.rule) return mSide(a.rule);
      if (a.cond) return mCond(a.cond);
      if (a.operand !== undefined) return mOp(a.operand);
      if (a.spec) return mSide(resolveSpec(withDefaults(a.spec), a.values).long);
      return fail('mirror : rule, cond, operand ou spec attendu.');
    },
    key: function () { if (Array.isArray(a.ts)) return a.ts.map(keyOf); return keyOf(a.t); },
    stats: function () { return statsOf(a.trades || [], a.settings && a.settings.pointValue); },
    run: function () {
      var ctx = prepare(a), cfg = config(ctx, a.values), ov = a.override || {};
      var x = execute(ctx, cfg, { fill: ov.fill || a.fill, slipTicks: ov.slipTicks, commissionRT: ov.commissionRT, throughTicks: ov.throughTicks });
      return { trades: x.trades, counts: x.counts, sessions: x.sessions, stats: statsOf(x.trades, ctx.pv), fill: x.fill, costs: x.costs, warnings: warnList(ctx) };
    },
    envelope: function () {
      var ctx = prepare(a), cfg = config(ctx, a.values), ov = a.override || {}, out = {};
      [['pess', 'pessimiste'], ['opt', 'optimiste']].forEach(function (p) {
        var x = execute(ctx, cfg, { fill: p[1], slipTicks: ov.slipTicks, commissionRT: ov.commissionRT, throughTicks: ov.throughTicks });
        out[p[0]] = { stats: statsOf(x.trades, ctx.pv), eq: equity(x.trades), counts: x.counts };
      });
      out.warnings = warnList(ctx);
      return out;
    },
    features: function () {
      var ctx = prepare(a), F = ctx.F1, S = ctx.S, list = [], s;
      for (s = 0; s < S.length; s++) if (S[s].sel) list.push(s);
      if (list.length > 5) { list = list.slice(-5); warn(ctx, 'aperçu limité aux cinq dernières séances'); }
      var i0 = F.si0[list[0]], i1 = F.si1[list[list.length - 1]];
      var series = (a.operands || []).map(function (x) { return toList(ev(F, x), i0, i1); }), sig = null;
      if (a.spec && a.spec.long) {
        var cfg = config(ctx, a.values), cons = cfg.dom.cons;
        var pick = function (g) { if (!g) return null; var o = []; for (var i = i0; i <= i1; i++) o.push(g[i] && cons[i] ? 1 : 0); return o; };
        sig = { L: pick(cfg.sides.L ? cfg.sig.L : null), S: pick(cfg.sides.S ? cfg.sig.S : null) };
      }
      return { t: toList(F.t, i0, i1), o: toList(F.o, i0, i1), h: toList(F.h, i0, i1), l: toList(F.l, i0, i1), c: toList(F.c, i0, i1), v: F.v ? toList(F.v, i0, i1) : null,
        sm: toList(F.sm, i0, i1), keys: list.map(function (q) { return S[q].key; }), series: series, sig: sig, warnings: warnList(ctx) };
    },
    /* séries complètes (tests et aperçus) : opérandes, conditions, signaux bruts et domaine sur toutes les barres découpées */
    series: function () {
      var ctx = prepare(a), F = ctx.F1, out = { n: F.n, t: F.t, sm: F.sm, sess: F.sess, keys: ctx.S.map(function (x) { return x.key; }), ops: [], conds: [] };
      out.ops = (a.operands || []).map(function (x) { return ev(F, x); });
      out.conds = (a.conds || []).map(function (c) { return cv(F, c); });
      if (a.spec && a.spec.long) { var cfg = config(ctx, a.values); out.sig = cfg.sig; out.cons = cfg.dom.cons; out.exec = executable(ctx, cfg); }
      out.warnings = warnList(ctx);
      return out;
    },
    lattice: function () { return lattice(a); },
    synth: function () {
      var ctx = prepare(a), cfg = config(ctx, a.values);
      if (usesExternal(cfg)) return { applicable: false, reason: 'Non applicable : la stratégie lit un niveau nommé ou le calendrier, qu’une marche synthétique ne porte pas.' };
      var sig = sigmaOf(ctx, cfg), nT = 0;
      for (var s = 0; s < ctx.S.length; s++) if (cfg.dom.trade[s]) nT++;
      if (!(sig > 0) || !nT) return { applicable: false, reason: 'Non applicable : aucune séance jouée ne permet de mesurer σ.' };
      var nS = Math.min(120, nT), warmN = 20;
      var lat = lattice({ sessions: nS + warmN, sigma: sig, tick: ctx.tick, seed: isNum(a.seed) ? a.seed : 1, start: a.start || '2026-01-05', base: isNum(a.base) ? a.base : 20000 });
      var b = {}; for (var k in a) if (own(a, k) && k !== 'onProgress') b[k] = a[k];
      b.bars = lat; b.sel = { from: lat.keys[warmN], to: lat.keys[lat.keys.length - 1] }; b.levels = null; b.news = null; b.adj = null; b.rolls = null; b.warmSessions = warmN;
      var c2 = prepare(b), g2 = config(c2, a.values);
      var xv = execute(c2, g2, { fill: 'vrai' }), xd = execute(c2, g2, {});
      var sv = statsOf(xv.trades, c2.pv), sd = statsOf(xd.trades, c2.pv);
      return { applicable: true, sigma: sig, k: lat.k, sessions: nS, theory: -sv.costR, vrai: sv.meanR, declare: sd.meanR, biais: sd.meanR - sv.meanR,
        n: sv.n, nDeclare: sd.n, se: sv.n > 1 ? sv.sdR / Math.sqrt(sv.n) : NaN, costR: sv.costR, fill: xd.fill };
    }
    /* ── opérations à enregistrer ici : random, permute, permuteGrid, sweep, wfa, stress, boot ── */
  };
  var fn = own(OPS, a.op) ? OPS[a.op] : null;
  if (!fn) fail('Opération inconnue : « ' + a.op + ' ».');
  return fn();
}

/* =====================================================================================
   Corps du worker : construit depuis la source de laboEngine (Blob). Garde les colonnes du jeu
   chargé (transférées une seule fois par empreinte), poste la progression au plus toutes les 250 ms.
   Autonome lui aussi : il ne lit que self et laboEngine, défini juste avant lui dans le Blob.
   ===================================================================================== */
function laboWorkerMain() {
  var G = typeof self !== 'undefined' ? self : this, COLS = null, FP = null, CACHE = {};
  function transfers(r) {
    var out = [];
    if (r && typeof r === 'object') for (var k in r) { var x = r[k]; if (x && ArrayBuffer.isView(x) && out.indexOf(x.buffer) < 0) out.push(x.buffer); }
    return out;
  }
  G.onmessage = function (e) {
    var m = e.data || {};
    if (m.type === 'load') { COLS = m.cols; FP = m.fp; CACHE = {}; G.postMessage({ type: 'loaded', id: m.id, fp: FP }); return; }
    if (m.type !== 'call') return;
    var a = m.a || {}, last = Date.now();
    a.op = m.op;
    if (!a.bars && m.op !== 'lattice' && m.op !== 'key' && m.op !== 'stats' && m.op !== 'resolve' && m.op !== 'mirror') {
      if (!COLS || (a.fp && a.fp !== FP)) { G.postMessage({ type: 'error', id: m.id, e: 'Colonnes non chargées pour ce jeu.' }); return; }
      a.bars = COLS; a.fp = FP; a.cache = CACHE;
    }
    a.onProgress = function (k, n) {
      var now = Date.now();
      if (now - last >= 250) { last = now; G.postMessage({ type: 'progress', id: m.id, progress: n > 0 ? k / n : 0 }); }
    };
    var r;
    try { r = laboEngine(a); }
    catch (err) { G.postMessage({ type: 'error', id: m.id, e: String((err && err.message) || err) }); return; }
    var tl = transfers(r);
    try { G.postMessage({ type: 'done', id: m.id, r: r }, tl); } catch (err2) { G.postMessage({ type: 'done', id: m.id, r: r }); }
  };
}

/* =====================================================================================
   T.lib.laboEngine : enveloppes synchrones (tests, petits calculs) et exécuteur de worker.
   ===================================================================================== */
var LE = T.lib.laboEngine = {};
LE.engine = laboEngine;
LE.workerMain = laboWorkerMain;
/* Opérations qui ne tournent jamais dans le fil principal (LABO.md, 4). */
LE.HEAVY = { random: 1, permute: 1, permuteGrid: 1, sweep: 1, wfa: 1, boot: 1 };
LE.op = function (name, a) { var b = {}; for (var k in (a || {})) if (Object.prototype.hasOwnProperty.call(a, k)) b[k] = a[k]; b.op = name; return laboEngine(b); };
LE.run = function (a) { return LE.op('run', a); };
LE.resolve = function (spec, values) { return laboEngine({ op: 'resolve', spec: spec, values: values }); };
LE.mirror = function (rule) { return laboEngine({ op: 'mirror', rule: rule }); };
LE.key = function (t) { return laboEngine({ op: 'key', t: t }); };
LE.stats = function (trades, pointValue) { return laboEngine({ op: 'stats', trades: trades, settings: { pointValue: pointValue } }); };
LE.lattice = function (o) { return LE.op('lattice', o || {}); };
LE.workerSource = function () { return 'var laboEngine = (' + laboEngine.toString() + ');\n(' + laboWorkerMain.toString() + ')();\n'; };

/* Exécuteur : { mode, load(fp, cols) → Promise, call(op, a, onProgress) → { promise, cancel }, close() }.
   Un seul calcul à la fois ; les suivants attendent leur tour. Les colonnes sont copiées puis transférées au
   worker une seule fois par empreinte : la copie gardée ici sert à recharger un worker neuf après une
   annulation (annuler un calcul en cours termine le worker, seul moyen d’interrompre un calcul synchrone).
   Sans Worker (ou opts.local), les opérations légères tournent dans le fil principal et les lourdes
   (LE.HEAVY) sont refusées : « calcul impossible sur cet appareil ». */
LE.worker = function (opts) {
  opts = opts || {};
  var W = null, url = null, seq = 0, cur = null, queue = [], data = null, wfp = null, closed = false, loads = [];
  var ex = { mode: 'local' };
  function canWorker() {
    if (opts.local) return false;
    try { return typeof Worker === 'function' && typeof Blob === 'function' && typeof URL !== 'undefined' && typeof URL.createObjectURL === 'function'; } catch (e) { return false; }
  }
  function spawn() {
    if (W) return true;
    if (!canWorker()) { ex.mode = 'local'; return false; }
    try {
      if (!url) url = URL.createObjectURL(new Blob([LE.workerSource()], { type: 'text/javascript' }));
      W = new Worker(url);
    } catch (e) { W = null; ex.mode = 'local'; return false; }
    ex.mode = 'worker'; wfp = null;
    W.onmessage = onMsg;
    W.onerror = function (e) {
      if (e && e.preventDefault) e.preventDefault();
      kill();
      if (cur) { var j = cur; cur = null; j.reject(new Error('Le calcul a échoué dans le worker' + (e && e.message ? ' : ' + e.message : '.'))); }
      pump();
    };
    return true;
  }
  function kill() { if (W) { try { W.terminate(); } catch (e) {} } W = null; wfp = null; }
  function norm(cols) {
    var o = {};
    ['t', 'o', 'h', 'l', 'c', 'v'].forEach(function (k) { var x = cols[k]; o[k] = x && x.length != null ? (ArrayBuffer.isView(x) ? x : new Float64Array(x)) : null; });
    var lf = cols.lowFirst || cols.lf; o.lowFirst = lf && lf.length != null ? (ArrayBuffer.isView(lf) ? lf : new Uint8Array(lf)) : null;
    return o;
  }
  function sendLoad(id) {
    var cp = {}, tr = [];
    for (var k in data.cols) { var x = data.cols[k]; if (!x) continue; var y = k === 'lowFirst' ? new Uint8Array(x) : new Float64Array(x); cp[k] = y; tr.push(y.buffer); }
    W.postMessage({ type: 'load', id: id, fp: data.fp, cols: cp }, tr);
    wfp = data.fp;
  }
  function onMsg(e) {
    var m = e.data || {};
    if (m.type === 'loaded') { loads = loads.filter(function (l) { if (l.id === m.id) { l.resolve(m.fp); return false; } return true; }); return; }
    if (!cur || m.id !== cur.id) return;
    if (m.type === 'progress') { if (cur.onProgress) { try { cur.onProgress(m.progress); } catch (err) {} } return; }
    var j = cur; cur = null;
    if (m.type === 'done') j.resolve(m.r); else j.reject(new Error(m.e || 'Le calcul a échoué.'));
    pump();
  }
  function cancelled() { var e = new Error('Calcul annulé.'); e.cancelled = true; return e; }
  function pump() {
    if (cur || !queue.length || closed) return;
    var j = cur = queue.shift();
    if (spawn()) {
      if (data && wfp !== data.fp) sendLoad(++seq);
      W.postMessage({ type: 'call', id: j.id, op: j.op, a: j.a });
      return;
    }
    if (LE.HEAVY[j.op]) { cur = null; j.reject(new Error('Calcul impossible sur cet appareil.')); pump(); return; }
    setTimeout(function () {
      if (cur !== j) return;
      var a = {}, k, last = Date.now();
      for (k in j.a) a[k] = j.a[k];
      if (!a.bars && data) a.bars = data.cols;
      a.op = j.op;
      a.onProgress = function (kk, n) { var now = Date.now(); if (j.onProgress && now - last >= 250) { last = now; try { j.onProgress(n > 0 ? kk / n : 0); } catch (err) {} } };
      var r, err = null;
      try { r = laboEngine(a); } catch (e) { err = e; }
      if (cur !== j) return;
      cur = null;
      if (err) j.reject(err); else j.resolve(r);
      pump();
    }, 0);
  }
  ex.load = function (fp, cols) {
    if (closed) return Promise.reject(new Error('Exécuteur fermé.'));
    data = { fp: fp, cols: norm(cols || {}) };
    if (!spawn()) return Promise.resolve(fp);
    if (cur) return Promise.resolve(fp);   /* un calcul tourne : le jeu sera chargé juste avant le suivant */
    var id = ++seq;
    return new Promise(function (resolve, reject) { loads.push({ id: id, resolve: resolve, reject: reject }); sendLoad(id); });
  };
  ex.call = function (op, a, onProgress) {
    var j = { id: ++seq, op: op, a: a || {}, onProgress: onProgress || null };
    j.promise = new Promise(function (resolve, reject) { j.resolve = resolve; j.reject = reject; });
    if (closed) j.reject(new Error('Exécuteur fermé.'));
    else { queue.push(j); pump(); }
    return {
      promise: j.promise,
      cancel: function () {
        var q = queue.indexOf(j);
        if (q >= 0) { queue.splice(q, 1); j.reject(cancelled()); return; }
        if (cur === j) { cur = null; if (ex.mode === 'worker') kill(); j.reject(cancelled()); pump(); }
      }
    };
  };
  ex.close = function () {
    closed = true; kill();
    if (cur) { cur.reject(cancelled()); cur = null; }
    queue.splice(0).forEach(function (j) { j.reject(cancelled()); });
    loads.splice(0).forEach(function (l) { l.reject(cancelled()); });
    if (url) { try { URL.revokeObjectURL(url); } catch (e) {} url = null; }
  };
  return ex;
};
