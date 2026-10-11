'use strict';
/* ALP Desk — socle commun. Tout desk passe par T : composants, graphiques, sauvegarde, calcul. */
(function () {
  var T = (window.T = {});
  T.version = '1.0';
  var DESKS = [];

  /* ================= DOM ================= */
  function h(tag, attrs) {
    var el = document.createElement(tag);
    if (attrs) {
      for (var k in attrs) {
        var v = attrs[k];
        if (v == null || v === false) continue;
        if (k === 'class') el.className = v;
        else if (k === 'style') { if (typeof v === 'string') el.style.cssText = v; else for (var s in v) el.style[s] = v[s]; }
        else if (k === 'text') el.textContent = v;
        else if (k === 'html') el.innerHTML = v;
        else if (k === 'on') { for (var ev in v) el.addEventListener(ev, v[ev]); }
        else if (k === 'value' && (tag === 'input' || tag === 'select' || tag === 'textarea')) el.value = v;
        else el.setAttribute(k, v === true ? '' : v);
      }
    }
    for (var i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function add(el, c) {
    if (c == null || c === false) return;
    if (Array.isArray(c)) { c.forEach(function (x) { add(el, x); }); return; }
    if (c instanceof Node) el.appendChild(c); else el.appendChild(document.createTextNode(String(c)));
  }
  T.h = h;
  T.esc = function (t) { return String(t == null ? '' : t).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  T.clear = function (el) { while (el.firstChild) el.removeChild(el.firstChild); return el; };

  /* ================= Format ================= */
  function numFr(value, nd, unit, signed) {
    nd = nd == null ? 2 : nd;
    if (value === Infinity) return '∞';
    if (value === -Infinity) return '−∞';
    if (typeof value !== 'number' || !isFinite(value)) return '—';
    var neg = value < 0 || Object.is(value, -0);
    var ex = Math.abs(value).toFixed(Math.min(100, Math.max(nd + 2, 20))).split('.'), ip = ex[0], fp = ex[1] || '';
    var keep = fp.slice(0, nd), rest = fp.slice(nd);
    var tie = rest[0] === '5' && /^0*$/.test(rest.slice(1));
    var up = rest[0] > '5' || (rest[0] === '5' && !tie) || (tie && ((nd > 0 ? +keep[nd - 1] : +ip[ip.length - 1]) % 2 === 1));
    var d = (ip + keep).split('').map(Number);
    if (up) { var i = d.length - 1; while (i >= 0) { if (d[i] === 9) { d[i] = 0; i--; } else { d[i]++; break; } } if (i < 0) d.unshift(1); }
    var s = d.join(''), cut = s.length - nd, I = s.slice(0, cut) || '0', F = s.slice(cut);
    I = I.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    var zero = /^[0 ]*$/.test(I) && /^0*$/.test(F);
    var sign = neg && !zero ? '−' : (signed && !zero ? '+' : '');
    return sign + I + (nd > 0 ? ',' + F : '') + (unit ? ' ' + unit : '');
  }
  var pad = function (n) { return String(n).padStart(2, '0'); };
  T.fmt = {
    num: numFr,
    int: function (v) { return numFr(v, 0); },
    usd: function (v, nd, signed) { return numFr(v, nd == null ? 0 : nd, '$', signed); },
    pct: function (p, nd, signed) { return numFr(p * 100, nd == null ? 1 : nd, '%', signed); },
    pts: function (v, nd) { return numFr(v, nd == null ? 2 : nd, 'pt'); },
    r: function (v, nd) { return numFr(v, nd == null ? 2 : nd, 'R', true); },
    date: function (t) { var d = new Date(t); return pad(d.getDate()) + '/' + pad(d.getMonth() + 1); },
    dateLong: function (t) { var d = new Date(t); return pad(d.getDate()) + '/' + pad(d.getMonth() + 1) + '/' + d.getFullYear(); },
    time: function (t) { var d = new Date(t); return pad(d.getHours()) + ':' + pad(d.getMinutes()); },
    dur: function (min) { if (!isFinite(min)) return '—'; if (min < 60) return numFr(min, min < 10 ? 1 : 0, 'min'); var hh = Math.floor(min / 60), mm = Math.round(min % 60); return hh + ' h ' + pad(mm); },
    parse: function (v) { v = String(v == null ? '' : v).trim().replace(/[\s  ]/g, '').replace(',', '.').replace('−', '-'); if (v === '') return NaN; var x = parseFloat(v); return isFinite(x) ? x : NaN; }
  };

  /* Typographie : espace insécable avant ; : ! ? » % et après «, pour les textes écrits à la main. */
  T.typo = function (t) { return String(t == null ? '' : t).replace(/ ([;:!?»%])/g, '\u00A0$1').replace(/« /g, '«\u00A0').replace(/(\d) (%|\$|€|pt\b|min\b|h\b)/g, '$1\u00A0$2'); };
  /* Passe typographique sur les nœuds texte d’un sous-arbre : aucune heure ni unité ne se coupe en fin de ligne. */
  var TYPO_SKIP = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, INPUT: 1, svg: 1, SVG: 1, text: 1, tspan: 1 };
  T.typoTree = function (root) {
    if (!root || typeof document === 'undefined' || !document.createTreeWalker) return;
    if (root.nodeType === 3) { fixText(root); return; }
    if (root.nodeType !== 1 || TYPO_SKIP[root.nodeName] || (root.closest && root.closest('svg,textarea,[contenteditable]'))) return;
    var w = document.createTreeWalker(root, 4, { acceptNode: function (n) { var p = n.parentNode; return p && (TYPO_SKIP[p.nodeName] || (p.closest && p.closest('svg,textarea,[contenteditable]'))) ? 2 : 1; } });
    var n; while ((n = w.nextNode())) fixText(n);
  };
  function fixText(n) { var t = n.data; if (!/\d|[;:!?»«]/.test(t)) return; var u = T.typo(t).replace(/(\d)[ \u00A0]h (\d)/g, '$1\u00A0h\u00A0$2'); if (u !== t) n.data = u; }

  /* ================= Temps et séances ================= */
  var DTF = {};
  function partsIn(tz, d) {
    d = d || new Date();
    try {
      var f = DTF[tz] || (DTF[tz] = new Intl.DateTimeFormat('en-GB', { timeZone: tz, hour12: false, weekday: 'short', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }));
      var o = {}; f.formatToParts(d).forEach(function (p) { o[p.type] = p.value; });
      var wd = { Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6, Sun: 0 }[o.weekday];
      return { y: +o.year, mo: +o.month, d: +o.day, h: +o.hour % 24, m: +o.minute, s: +o.second, wd: wd };
    } catch (e) { return { y: d.getFullYear(), mo: d.getMonth() + 1, d: d.getDate(), h: d.getHours(), m: d.getMinutes(), s: d.getSeconds(), wd: d.getDay() }; }
  }
  T.time = {
    parts: partsIn,
    hhmm: function (tz, d) { var p = partsIn(tz, d); return pad(p.h) + ':' + pad(p.m); },
    /* Globex CME : dimanche 18:00 → vendredi 17:00 heure de New York, pause quotidienne 17:00–18:00. */
    globex: function (d) {
      var p = partsIn('America/New_York', d), mins = p.h * 60 + p.m, wd = p.wd, open;
      if (wd === 6) open = false; else if (wd === 0) open = mins >= 18 * 60; else if (wd === 5) open = mins < 17 * 60; else open = !(mins >= 17 * 60 && mins < 18 * 60);
      var cash = wd >= 1 && wd <= 5 && mins >= 9 * 60 + 30 && mins < 16 * 60;
      return { open: open, cash: cash, ny: pad(p.h) + ':' + pad(p.m), wd: wd };
    },
    inWindow: function (from, to, tz, d) { var p = partsIn(tz || 'Europe/Paris', d), x = p.h + p.m / 60; return from <= to ? (x >= from && x < to) : (x >= from || x < to); }
  };

  /* ================= Aléa et statistiques ================= */
  T.rng = function (seed) { var a = seed >>> 0; return function () { a = (a + 0x6D2B79F5) >>> 0; var t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; };
  var S = T.stats = {};
  S.sum = function (a) { var s = 0; for (var i = 0; i < a.length; i++) s += a[i]; return s; };
  S.mean = function (a) { return a.length ? S.sum(a) / a.length : NaN; };
  S.sd = function (a) { if (a.length < 2) return NaN; var m = S.mean(a), s = 0; for (var i = 0; i < a.length; i++) s += (a[i] - m) * (a[i] - m); return Math.sqrt(s / (a.length - 1)); };
  S.quantile = function (sorted, q) { if (!sorted.length) return NaN; var p = (sorted.length - 1) * q, lo = Math.floor(p), hi = Math.ceil(p); return sorted[lo] + (sorted[hi] - sorted[lo]) * (p - lo); };
  S.sorted = function (a) { return a.slice().sort(function (x, y) { return x - y; }); };
  S.erf = function (x) { var s = x < 0 ? -1 : 1; x = Math.abs(x); var t = 1 / (1 + 0.3275911 * x); var y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x); return s * y; };
  S.normCdf = function (x) { return 0.5 * (1 + S.erf(x / Math.SQRT2)); };
  S.normPpf = function (p) {
    var A = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02, 1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00], B = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02, 6.680131188771972e01, -1.328068155288572e01], C = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00, -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00], D = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00, 3.754408661907416e00], pl = 0.02425, q, r;
    if (p <= 0) return -Infinity; if (p >= 1) return Infinity;
    if (p < pl) { q = Math.sqrt(-2 * Math.log(p)); return (((((C[0] * q + C[1]) * q + C[2]) * q + C[3]) * q + C[4]) * q + C[5]) / ((((D[0] * q + D[1]) * q + D[2]) * q + D[3]) * q + 1); }
    if (p > 1 - pl) { q = Math.sqrt(-2 * Math.log(1 - p)); return -(((((C[0] * q + C[1]) * q + C[2]) * q + C[3]) * q + C[4]) * q + C[5]) / ((((D[0] * q + D[1]) * q + D[2]) * q + D[3]) * q + 1); }
    q = p - 0.5; r = q * q; return (((((A[0] * r + A[1]) * r + A[2]) * r + A[3]) * r + A[4]) * r + A[5]) * q / (((((B[0] * r + B[1]) * r + B[2]) * r + B[3]) * r + B[4]) * r + 1);
  };
  S.maxDrawdown = function (eq) { var pk = -Infinity, dd = 0; for (var i = 0; i < eq.length; i++) { if (eq[i] > pk) pk = eq[i]; if (pk - eq[i] > dd) dd = pk - eq[i]; } return dd; };
  S.cumsum = function (a, start) { var s = start || 0, o = []; for (var i = 0; i < a.length; i++) { s += a[i]; o.push(s); } return o; };

  /* ================= Calcul en tâche de fond =================
     T.compute(fn, arg) : fn doit être autonome (aucune variable extérieure), elle reçoit arg et rend un résultat sérialisable. */
  var WCACHE = {};
  T.compute = function (fn, arg) {
    var src = fn.toString();
    return new Promise(function (resolve, reject) {
      var w;
      try {
        if (!WCACHE[src]) {
          var code = 'var F=(' + src + ');onmessage=function(e){try{postMessage({ok:true,r:F(e.data)});}catch(err){postMessage({ok:false,e:String(err&&err.message||err)});}};';
          WCACHE[src] = URL.createObjectURL(new Blob([code], { type: 'text/javascript' }));
        }
        w = new Worker(WCACHE[src]);
      } catch (e) { w = null; }
      if (!w) { setTimeout(function () { try { resolve(fn(arg)); } catch (err) { reject(err); } }, 0); return; }
      w.onmessage = function (m) { w.terminate(); if (m.data.ok) resolve(m.data.r); else reject(new Error(m.data.e)); };
      w.onerror = function (e) { w.terminate(); try { resolve(fn(arg)); } catch (err) { reject(err); } };
      w.postMessage(arg);
    });
  };

  /* ================= Sauvegarde =================
     T.store : réglages et états par utilisateur (base privée data/users/<id>/<clé>, copie locale).
     T.journal : une ligne par décision, base privée data/users/<id>/journal/trades/<id>.
     T.shared : données écrites par Claude (macro, calendrier), lues par la page. */
  var LSK = 'alpdesk:';
  var cloud = { db: null, uid: null, ready: false, status: 'local' };
  function lsGet(k) { try { var r = localStorage.getItem(LSK + k); return r ? JSON.parse(r) : null; } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(LSK + k, JSON.stringify(v)); return true; } catch (e) { return false; } }
  var statusSubs = [];
  function setStatus(s) { cloud.status = s; statusSubs.forEach(function (f) { try { f(s); } catch (e) {} }); }
  T.saveStatus = { get: function () { return cloud.status; }, on: function (f) { statusSubs.push(f); } };

  var store = { mem: {}, subs: {}, timers: {}, writing: {}, dirty: {} };
  function keyOk(k) { return /^[A-Za-z0-9_.~:@+-]{1,120}$/.test(k); }
  T.store = {
    get: function (k, def) {
      if (!keyOk(k)) throw new Error('clé invalide ' + k);
      if (!(k in store.mem)) { var l = lsGet('s:' + k); store.mem[k] = l ? l : { v: def === undefined ? null : JSON.parse(JSON.stringify(def)), t: 0 }; pull(k); }
      var v = store.mem[k].v; return v == null && def !== undefined ? JSON.parse(JSON.stringify(def)) : JSON.parse(JSON.stringify(v));
    },
    set: function (k, v) {
      if (!keyOk(k)) throw new Error('clé invalide ' + k);
      store.mem[k] = { v: JSON.parse(JSON.stringify(v)), t: Date.now() }; lsSet('s:' + k, store.mem[k]);
      (store.subs[k] || []).forEach(function (f) { try { f(T.store.get(k)); } catch (e) {} });
      schedule(k);
    },
    on: function (k, f) { (store.subs[k] = store.subs[k] || []).push(f); return function () { store.subs[k] = (store.subs[k] || []).filter(function (x) { return x !== f; }); }; }
  };
  function schedule(k) { if (!cloud.ready) return; clearTimeout(store.timers[k]); setStatus('saving'); store.timers[k] = setTimeout(function () { push(k); }, 700); }
  function push(k) {
    if (!cloud.ready) return; if (store.writing[k]) { store.dirty[k] = true; return; }
    store.writing[k] = true;
    cloud.db.doc('data/users/' + cloud.uid + '/' + k).set(store.mem[k]).then(function () { setStatus('cloud'); }, function () { setStatus('local'); }).then(function () { store.writing[k] = false; if (store.dirty[k]) { store.dirty[k] = false; push(k); } });
  }
  var pulled = {};
  function pull(k) {
    if (!cloud.ready || pulled[k]) return; pulled[k] = true;
    cloud.db.doc('data/users/' + cloud.uid + '/' + k).get().then(function (s) {
      if (!s.exists) { if (store.mem[k] && store.mem[k].t) push(k); return; }
      var d = s.data(); if (d && (d.t || 0) > ((store.mem[k] && store.mem[k].t) || 0)) { store.mem[k] = { v: d.v, t: d.t }; lsSet('s:' + k, store.mem[k]); (store.subs[k] || []).forEach(function (f) { try { f(T.store.get(k)); } catch (e) {} }); }
      else if (store.mem[k] && store.mem[k].t > ((d && d.t) || 0)) push(k);
    }, function () {});
  }

  var jr = { rows: lsGet('journal') || [], subs: [], ref: null };
  function jSave() { lsSet('journal', jr.rows); jr.subs.forEach(function (f) { try { f(T.journal.list()); } catch (e) {} }); }
  function jId() { return 'j' + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36); }
  T.journal = {
    list: function () { return jr.rows.filter(function (r) { return !r.deleted; }).sort(function (a, b) { return (a.at || 0) - (b.at || 0); }).map(function (r) { return JSON.parse(JSON.stringify(r)); }); },
    add: function (e) { var r = Object.assign({}, e, { id: jId(), at: e.at || Date.now(), u: Date.now() }); jr.rows.push(r); jSave(); jPush(r); return r.id; },
    update: function (id, patch) { var r = jr.rows.find(function (x) { return x.id === id; }); if (!r) return; Object.assign(r, patch, { u: Date.now() }); jSave(); jPush(r); },
    remove: function (id) { var r = jr.rows.find(function (x) { return x.id === id; }); if (!r) return; r.deleted = true; r.u = Date.now(); jSave(); jPush(r); },
    on: function (f) { jr.subs.push(f); return function () { jr.subs = jr.subs.filter(function (x) { return x !== f; }); }; }
  };
  function jPush(r) { if (!jr.ref) return; setStatus('saving'); jr.ref.doc(r.id).set(r).then(function () { setStatus('cloud'); }, function () { setStatus('local'); }); }

  var shared = { data: {}, subs: {} };
  T.shared = {
    watch: function (col, f) {
      (shared.subs[col] = shared.subs[col] || []).push(f);
      var cached = shared.data[col] || lsGet('sh:' + col) || [];
      shared.data[col] = cached; setTimeout(function () { f(cached.slice()); }, 0);
      if (cloud.ready) attachShared(col);
      return function () { shared.subs[col] = (shared.subs[col] || []).filter(function (x) { return x !== f; }); };
    },
    get: function (col) { return (shared.data[col] || lsGet('sh:' + col) || []).slice(); }
  };
  var attached = {};
  function attachShared(col) {
    if (attached[col] || !cloud.ready) return; attached[col] = true;
    try {
      cloud.db.collection(col).onSnapshot(function (snap) {
        var rows = snap.docs.map(function (d) { var x = d.data() || {}; x._id = d.id; return x; });
        shared.data[col] = rows; lsSet('sh:' + col, rows);
        (shared.subs[col] || []).forEach(function (f) { try { f(rows.slice()); } catch (e) {} });
      }, function () {});
    } catch (e) {}
  }

  /* T.ucoll(chemin, {mirror, live}) : une collection privée de l'utilisateur, data/users/<id>/<doc>/<collection>.
     chemin = 'doc/collection' (ex. 'labo/strategies'). Copie locale si mirror !== false (petites collections) ;
     abonnement en direct si live !== false. Fusion par le champ u (dernière écriture), suppression douce
     (deleted: true) pour les copies locales, suppression dure pour les grosses collections (mirror: false).
     Les documents écrits par Claude (ArtifactData) arrivent par le même abonnement. */
  var UC = {};
  function ucId() { return 'd' + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36); }
  T.ucoll = function (path, opt) {
    if (!/^[A-Za-z0-9_.~:@+-]{1,80}\/[A-Za-z0-9_.~:@+-]{1,80}$/.test(path)) throw new Error('chemin de collection invalide ' + path);
    if (UC[path]) return UC[path].api;
    opt = opt || {};
    var mirror = opt.mirror !== false, live = opt.live !== false;
    var st = { rows: mirror ? (lsGet('uc:' + path) || []) : [], subs: [], ref: null, loaded: false, waits: [] };
    function save() { if (mirror) lsSet('uc:' + path, st.rows); var l = api.list(); st.subs.forEach(function (f) { try { f(l); } catch (e) {} }); }
    function pushRow(r) { if (!st.ref) return Promise.resolve(false); setStatus('saving'); return st.ref.doc(r.id).set(r).then(function () { setStatus('cloud'); return true; }, function (e) { setStatus('local'); throw e; }); }
    function merge(docs) {
      var by = {}, changed = false; st.rows.forEach(function (x) { by[x.id] = x; });
      docs.forEach(function (x) { if (!x || !x.id) return; var cur = by[x.id]; if (!cur || (x.u || 0) > (cur.u || 0)) { by[x.id] = x; changed = true; } });
      if (mirror) st.rows.forEach(function (x) { if (!docs.some(function (d) { return d && d.id === x.id; })) pushRow(x).catch(function () {}); });
      else Object.keys(by).forEach(function (k) { if (!docs.some(function (d) { return d && d.id === k; })) { delete by[k]; changed = true; } });
      if (changed || !st.loaded) { st.rows = Object.keys(by).map(function (k) { return by[k]; }); st.loaded = true; save(); }
      st.waits.splice(0).forEach(function (f) { f(); });
    }
    function attach() {
      if (st.ref || !cloud.ready) return;
      var parts = path.split('/');
      st.ref = cloud.db.doc('data/users/' + cloud.uid + '/' + parts[0]).collection(parts[1]);
      var toRows = function (snap) { return snap.docs.map(function (d) { var x = d.data() || {}; if (!x.id) x.id = d.id; return x; }); };
      if (live) st.ref.onSnapshot(function (snap) { merge(toRows(snap)); }, function () {});
      else st.ref.get().then(function (snap) { merge(toRows(snap)); }, function () { st.loaded = true; st.waits.splice(0).forEach(function (f) { f(); }); });
    }
    var api = {
      path: path,
      list: function () { return st.rows.filter(function (r) { return !r.deleted; }).map(function (r) { return JSON.parse(JSON.stringify(r)); }); },
      get: function (id) { var r = st.rows.find(function (x) { return x.id === id && !x.deleted; }); return r ? JSON.parse(JSON.stringify(r)) : null; },
      set: function (id, doc) { var r = Object.assign({}, doc, { id: id, u: Date.now() }); delete r.deleted; var i = st.rows.findIndex(function (x) { return x.id === id; }); if (i >= 0) st.rows[i] = r; else st.rows.push(r); save(); return pushRow(r).catch(function () { return false; }); },
      add: function (doc) { var id = doc.id || ucId(); api.set(id, doc); return id; },
      update: function (id, patch) { var cur = st.rows.find(function (x) { return x.id === id; }); return api.set(id, Object.assign({}, cur || {}, patch)); },
      remove: function (id) {
        var i = st.rows.findIndex(function (x) { return x.id === id; }); if (i < 0) return Promise.resolve(false);
        if (mirror) { st.rows[i] = Object.assign({}, st.rows[i], { deleted: true, u: Date.now() }); save(); return pushRow(st.rows[i]).catch(function () { return false; }); }
        st.rows.splice(i, 1); save(); return st.ref ? st.ref.doc(id).delete().then(function () { return true; }, function () { return false; }) : Promise.resolve(true);
      },
      on: function (f) { st.subs.push(f); return function () { st.subs = st.subs.filter(function (x) { return x !== f; }); }; },
      ready: function () { return new Promise(function (res) { if (st.loaded || !cloud.ready) { if (!cloud.ready) setTimeout(res, 0); else res(); } else st.waits.push(res); }); },
      cloud: function () { return !!st.ref; },
      refresh: function () { if (st.ref && !live) st.ref.get().then(function (snap) { merge(snap.docs.map(function (d) { var x = d.data() || {}; if (!x.id) x.id = d.id; return x; })); }, function () {}); }
    };
    UC[path] = { api: api, attach: attach };
    attach();
    return api;
  };
  T.cloudReady = function () { return cloud.ready; };
  var cloudSubs = [];
  T.onCloud = function (f) { if (cloud.ready) { setTimeout(f, 0); return function () {}; } cloudSubs.push(f); return function () { cloudSubs = cloudSubs.filter(function (x) { return x !== f; }); }; };

  T.cloudInit = function () {
    if (!window.claude || typeof window.claude.use !== 'function') return;
    Promise.all([window.claude.use('db'), window.claude.use('user')]).then(function (r) {
      var db = r[0], user = r[1]; if (!db || !user) return;
      return user.id().then(function (uid) {
        if (!uid) return;
        cloud.db = db; cloud.uid = uid; cloud.ready = true; setStatus('cloud');
        Object.keys(store.mem).forEach(pull);
        Object.keys(shared.subs).forEach(attachShared);
        Object.keys(UC).forEach(function (k) { UC[k].attach(); });
        cloudSubs.splice(0).forEach(function (f) { try { f(); } catch (e) {} });
        jr.ref = db.doc('data/users/' + uid + '/journal').collection('trades');
        jr.ref.onSnapshot(function (snap) {
          var byId = {}; jr.rows.forEach(function (x) { byId[x.id] = x; });
          var changed = false;
          snap.docs.forEach(function (d) { var x = d.data(); if (!x || !x.id) return; var cur = byId[x.id]; if (!cur || (x.u || 0) > (cur.u || 0)) { byId[x.id] = x; changed = true; } });
          jr.rows.forEach(function (x) { if (!snap.docs.some(function (d) { return d.id === x.id; })) jPush(x); });
          if (changed) { jr.rows = Object.keys(byId).map(function (k) { return byId[k]; }); jSave(); }
        }, function () {});
      });
    }).catch(function () { setStatus('local'); });
  };

  /* ================= Réglages communs ================= */
  var SET_DEF = { instrument: 'MNQ', pointValue: 2, tick: 0.25, commissionRT: 1.24, tz: 'Europe/Paris', winFrom: 0, winTo: 24, riskPerTrade: 150, maxTradesDay: 3, maxLossesDay: 2, dailyStop: 400 };
  T.settings = {
    get: function () { return Object.assign({}, SET_DEF, T.store.get('settings', {})); },
    set: function (patch) { T.store.set('settings', Object.assign(T.store.get('settings', {}), patch)); },
    defaults: SET_DEF
  };

  /* ================= Journée : les étapes de la carte de séance =================
     Onze étapes, dans l’ordre du plan de trading (desk Plan). Un desk marque une étape faite avec T.day.mark(id) ;
     le Plan pose en plus un pourcentage d’avancement avec T.day.setPct(id, p). T.day.pct(id) lit 100 si l’étape est
     faite, sinon le pourcentage posé, sinon 0. */
  T.DAY_STEPS = [
    { id: 'macro', t: 'Macro et calendrier', s: 'Ce qui est déjà dans le prix', desk: 'macro' },
    { id: 'biais', t: 'Tendance', s: 'Haussière, neutre ou baissière', desk: 'nq' },
    { id: 'gex', t: 'Niveaux gamma', s: 'Les cibles du jour', desk: 'nq' },
    { id: 'zones', t: 'HVN', s: 'Les nœuds de haut volume de la veille', desk: 'plan' },
    { id: 'setup', t: 'Ta carte', s: 'Le setup existe-t-il sur tes niveaux ?', desk: 'plan' },
    { id: 'fenetre', t: 'VWAP ±1,5σ ou ±2,5σ', s: 'Le bon côté touché', desk: 'micro' },
    { id: 'declencheur', t: 'Flux au contact', s: 'Absorption, épuisement ou continuation', desk: 'micro' },
    { id: 'mur', t: 'Mur et stop', s: 'Un mur ancien, le stop derrière', desk: 'plan' },
    { id: 'risque', t: 'Cible et R:R', s: 'Cible gamma, stop hors du bruit', desk: 'risk' },
    { id: 'journal', t: 'Journal, après', s: 'Compléter les trades pris en live', desk: 'journal' },
    { id: 'revue', t: 'Revue du soir', s: 'Ce que la journée enseigne', desk: 'routine' }
  ];
  function dayKey() { var p = partsIn('Europe/Paris'); return p.y + '-' + pad(p.mo) + '-' + pad(p.d); }
  T.day = {
    key: dayKey,
    get: function () { var d = T.store.get('day', { date: '', done: {} }); if (d.date !== dayKey()) d = { date: dayKey(), done: {} }; if (!d.pct || typeof d.pct !== 'object') d.pct = {}; return d; },
    mark: function (id, on) { var d = T.day.get(); if (on === false) delete d.done[id]; else d.done[id] = Date.now(); T.store.set('day', d); },
    setPct: function (id, p) { var d = T.day.get(), v = Math.max(0, Math.min(100, Math.round(+p || 0))); if (d.pct[id] === v) return; d.pct[id] = v; T.store.set('day', d); },
    pct: function (id, d) { d = d || T.day.get(); return d.done[id] ? 100 : (isFinite(d.pct[id]) ? d.pct[id] : 0); },
    on: function (f) { return T.store.on('day', function () { f(T.day.get()); }); }
  };

  /* ================= Composants ================= */
  var U = T.ui = {};
  function richTitle(t) { /* *mot* → italique serif */ var parts = String(t).split('*'), out = []; parts.forEach(function (p, i) { if (!p) return; out.push(i % 2 ? h('em', null, p) : p); }); return out; }
  U.rich = richTitle;
  U.page = function (o) { return h('header', { class: 'ph' }, o.kicker ? h('div', { class: 'kick' }, o.kicker) : null, h('h1', null, richTitle(o.title)), o.lede ? h('p', null, o.lede) : null); };
  U.section = function (title, meta) { var s = h('section', { class: 'sec' }); if (title) s.appendChild(h('div', { class: 'sh' }, h('h2', null, richTitle(title)), meta ? h('span', null, meta) : null)); return s; };
  U.card = function (o) { var c = h('div', { class: 'card' + (o.flush ? ' flush' : '') + (o.accent ? ' accent' : '') }); if (o.title) c.appendChild(h('div', { class: 'ch' }, h('b', null, o.title), o.meta ? (o.meta instanceof Node ? o.meta : h('span', null, o.meta)) : null)); c.appendChild(h('div', { class: 'cb' }, o.body)); return c; };
  U.kpis = function (items, cols) {
    return h('div', { class: 'kpis' + (cols ? ' k' + cols : '') }, items.map(function (k) {
      return h(k.onClick ? 'button' : 'div', { class: 'kpi' + (k.tone === 'neg' ? ' neg' : k.tone === 'acc' ? ' acc' : ''), on: k.onClick ? { click: k.onClick } : null },
        h('div', { class: 'l' }, k.label), h('div', { class: 'v' }, k.value, k.unit ? h('small', null, k.unit) : null), k.hint ? h('div', { class: 'h' }, k.hint) : null);
    }));
  };
  U.pill = function (text, kind) { return h('span', { class: 'pill' + (kind ? ' ' + kind : '') }, text); };
  U.button = function (o) { return h('button', { class: 'btn' + (o.kind ? ' ' + o.kind : '') + (o.small ? ' sm' : ''), type: 'button', disabled: o.disabled || null, 'aria-label': o.aria || null, on: { click: o.onClick } }, o.label); };
  U.note = function (text, warn) { return h('p', { class: 'note' + (warn ? ' warn' : '') }, text); };
  U.callout = function (children) { return h('div', { class: 'callout' }, children); };
  U.empty = function (o) { return h('div', { class: 'empty' }, h('b', null, o.title), o.text ? h('p', null, o.text) : null, o.action || null); };
  U.prose = function (paras) { return h('div', { class: 'prose' }, paras.map(function (p) { return h('p', { html: p }); })); };
  var fid = 0;
  U.field = function (o) {
    var id = o.id || ('f' + (++fid)), input;
    var wrapCls = 'in' + (o.type === 'textarea' ? ' ta' : '');
    if (o.type === 'select') {
      input = h('select', { id: id, on: { change: function () { o.onChange && o.onChange(input.value); } } }, (o.options || []).map(function (op) { var v = typeof op === 'object' ? op.v : op, l = typeof op === 'object' ? op.label : op; return h('option', { value: v, selected: String(v) === String(o.value) || null }, l); }));
    } else if (o.type === 'textarea') {
      input = h('textarea', { id: id, placeholder: o.placeholder || null, on: { change: function () { o.onChange && o.onChange(input.value); } } }); input.value = o.value == null ? '' : o.value;
    } else {
      var isNum = !o.type || o.type === 'number';
      input = h('input', { id: id, type: isNum ? 'text' : o.type, inputmode: isNum ? 'decimal' : null, placeholder: o.placeholder || null, autocomplete: 'off',
        value: o.value == null ? '' : (isNum && typeof o.value === 'number' ? String(o.value).replace('.', ',') : o.value),
        on: { change: function () { if (!o.onChange) return; if (isNum) { var x = T.fmt.parse(input.value); if (isFinite(x)) { if (o.min != null) x = Math.max(o.min, x); if (o.max != null) x = Math.min(o.max, x); input.value = String(x).replace('.', ','); o.onChange(x); } else if (input.value.trim() === '' && o.allowEmpty) o.onChange(null); else { input.value = o.value == null ? '' : String(o.value).replace('.', ','); } } else o.onChange(input.value); } } });
    }
    return h('div', { class: 'fld' + (o.full ? ' full' : '') }, h('label', { for: id }, o.label), h('div', { class: wrapCls }, input, o.unit ? h('span', { class: 'u' }, o.unit) : null), o.hint ? h('span', { class: 'hint' }, o.hint) : null);
  };
  U.fields = function (list, cols) { return h('div', { class: 'fields' + (cols === 3 ? ' f3' : '') }, list.map(function (f) { return f instanceof Node ? f : U.field(f); })); };
  U.seg = function (o) { var el = h('div', { class: 'seg', role: 'group', 'aria-label': o.aria || null }); o.options.forEach(function (op) { el.appendChild(h('button', { type: 'button', 'aria-pressed': String(op.v === o.value), disabled: op.disabled || null, 'aria-disabled': op.disabled ? 'true' : null, title: op.title || null, on: { click: function () { if (!op.disabled) o.onChange(op.v); } } }, op.label)); }); return el; };
  U.chips = function (o) { return h('div', { class: 'chips' }, o.options.map(function (op) { var on = o.multi ? (o.value || []).indexOf(op.v) >= 0 : op.v === o.value; return h('button', { class: 'chip', type: 'button', 'aria-pressed': String(on), on: { click: function () { o.onChange(op.v); } } }, op.label); })); };
  U.tabs = function (o) { return h('div', { class: 'tabs', role: 'tablist' }, o.tabs.map(function (t) { return h('button', { role: 'tab', type: 'button', 'aria-selected': String(t.id === o.value), on: { click: function () { o.onChange(t.id); } } }, t.label); })); };
  U.checklist = function (o) {
    return h('div', { class: 'checks' }, o.items.map(function (it) {
      var on = !!(o.checked && o.checked[it.id]);
      return h('button', { class: 'ck', type: 'button', role: 'checkbox', 'aria-checked': String(on), on: { click: function () { o.onToggle(it.id, !on); } } }, h('i'), h('div', null, h('b', null, it.t), it.s ? h('span', null, it.s) : null));
    }));
  };
  U.table = function (o) {
    if (!o.rows || !o.rows.length) return o.empty ? U.empty(typeof o.empty === 'string' ? { title: o.empty } : o.empty) : h('div');
    return h('div', { class: 'tbl' }, h('table', null,
      h('thead', null, h('tr', null, o.cols.map(function (c) { return h('th', { class: c.align === 'r' ? 'r' : null }, c.label); }))),
      h('tbody', null, o.rows.map(function (r) { return h('tr', { class: o.rowClass ? o.rowClass(r) : null, on: o.onRow ? { click: function () { o.onRow(r); } } : null, style: o.onRow ? 'cursor:pointer' : null }, o.cols.map(function (c) { var v = c.fmt ? c.fmt(r[c.k], r) : r[c.k]; return h('td', { class: (c.align === 'r' ? 'r' : '') + (c.cls ? ' ' + c.cls : '') || null }, v == null || v === '' ? '—' : (v instanceof Node ? v : String(v))); })); }))));
  };
  U.flow = function (o) {
    var wrap = h('div', { class: 'flow' }), svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('class', 'fw'); wrap.appendChild(svg);
    var els = o.nodes.map(function (n, i) {
      var el = h('button', { class: 'fn', type: 'button', 'data-s': n.state || 'todo', on: n.onClick ? { click: n.onClick } : null }, h('span', { class: 'ix' }, n.ix || String(i + 1)), h('span', { class: 'tx' }, h('b', null, n.title), n.sub ? h('span', null, n.sub) : null, n.pct != null ? h('span', { class: 'pc', role: 'progressbar', 'aria-valuenow': String(n.pct), 'aria-valuemin': '0', 'aria-valuemax': '100' }, h('i', { style: 'width:' + Math.max(0, Math.min(100, n.pct)) + '%' })) : null), n.go ? h('span', { class: 'go' }, n.go) : null);
      wrap.appendChild(el); return el;
    });
    function draw() {
      if (!wrap.isConnected) return; var wr = wrap.getBoundingClientRect(), out = '';
      svg.setAttribute('width', wr.width); svg.setAttribute('height', wr.height);
      for (var i = 0; i < els.length - 1; i++) {
        var a = els[i].getBoundingClientRect(), b = els[i + 1].getBoundingClientRect(), x = a.left - wr.left + 26, y1 = a.bottom - wr.top, y2 = b.top - wr.top;
        var sa = o.nodes[i].state, sb = o.nodes[i + 1].state, on = sa === 'done', go = on && sb === 'active';
        out += '<path class="w' + (go ? ' go' : on ? ' on' : '') + '" d="M' + x + ',' + y1 + ' L' + x + ',' + y2 + '"/><circle class="pt' + (on ? ' on' : '') + '" cx="' + x + '" cy="' + y1 + '" r="3"/><circle class="pt' + (on ? ' on' : '') + '" cx="' + x + '" cy="' + y2 + '" r="3"/>';
      }
      svg.innerHTML = out;
    }
    observe(wrap, draw);
    return wrap;
  };

  /* ================= Graphiques (SVG, rendus à la largeur réelle) ================= */
  var C = T.chart = {};
  var ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(function (es) { es.forEach(function (e) { var f = e.target.__draw; if (f) requestAnimationFrame(f); }); }) : null;
  function observe(el, draw) { el.__draw = draw; if (ro) ro.observe(el); else setTimeout(draw, 0); requestAnimationFrame(function () { requestAnimationFrame(draw); }); }
  T.observe = observe;
  var X = T.esc;
  var TONE = { fg: 'var(--hi)', violet: 'var(--violet)', mute: 'var(--soft)', dim: 'var(--line-2)' };
  function niceStep(span, n) { var raw = span / Math.max(1, n), p = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / p; return (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * p; }
  function ticks(lo, hi, n) { if (!(hi > lo)) { hi = lo + 1; } var st = niceStep(hi - lo, n || 4), a = Math.ceil(lo / st - 1e-9) * st, out = []; for (var v = a; v <= hi + st * 1e-9; v += st) out.push(Math.abs(v) < st * 1e-9 ? 0 : v); return out; }
  T.ticks = ticks;
  function autoFmt(span) { var nd = span >= 50 ? 0 : span >= 5 ? 1 : span >= 0.5 ? 2 : 3; return function (v) { return numFr(v, nd); }; }
  function mount(o, render) {
    var wrap = h('div', { class: 'chart' }), tip = h('div', { class: 'tip' }); var holder = h('div'); wrap.appendChild(holder); wrap.appendChild(tip);
    var hover = null;
    function draw() { if (!wrap.isConnected) return; var w = Math.max(240, Math.round(wrap.clientWidth || 320)); var r = render(w); holder.innerHTML = r.svg; hover = r.hover || null; }
    observe(wrap, draw);
    function move(ev) {
      if (!hover) return; var rc = wrap.getBoundingClientRect(), x = ev.clientX - rc.left, best = -1, bd = Infinity;
      for (var i = 0; i < hover.xs.length; i++) { var d = Math.abs(hover.xs[i] - x); if (d < bd) { bd = d; best = i; } }
      if (best < 0) return; var line = holder.querySelector('.hl'); if (line) { line.setAttribute('x1', hover.xs[best]); line.setAttribute('x2', hover.xs[best]); line.style.opacity = 1; }
      tip.innerHTML = hover.html(best); tip.classList.add('on');
      var tw = tip.offsetWidth, left = hover.xs[best] + 12; if (left + tw > rc.width) left = hover.xs[best] - tw - 12; tip.style.left = Math.max(0, left) + 'px'; tip.style.top = '6px';
    }
    function leave(ev) { if (ev && ev.pointerType && ev.pointerType !== 'mouse') return; tip.classList.remove('on'); var line = holder.querySelector('.hl'); if (line) line.style.opacity = 0; }
    wrap.addEventListener('pointermove', move); wrap.addEventListener('pointerdown', move); wrap.addEventListener('pointerleave', leave);
    if (o && o.legend && o.legend.length) wrap.appendChild(h('div', { class: 'legend' }, o.legend.map(function (l) { return h('span', null, h('i', { class: (l.tone || '') + (l.dash ? ' dash' : '') + (l.box ? ' box' : ''), style: l.box ? 'background:' + l.box : null }), l.label); })));
    return wrap;
  }
  C.mount = mount;

  /* Courbe : series [{name, points:[[x,y]...], tone, dash, area, width}] ; x:{type:'num'|'time'|'cat', labels, fmt} ; y:{fmt, zero, min, max, log} ; hlines [{y,label,tone}] ; bands [{y0,y1}] ; vlines [{x,label}] */
  C.line = function (o) {
    var series = (o.series || []).filter(function (s) { return s.points && s.points.length; });
    var leg = o.legend !== false && series.length > 1 ? series.map(function (s) { return { label: s.name, tone: s.tone || 'fg', dash: !!s.dash }; }) : null;
    return mount({ legend: leg }, function (W) {
      var H = o.height || 210, m = { l: o.ml || 46, r: o.mr || 14, t: 12, b: 26 };
      var xs = [], ys = [];
      series.forEach(function (s) { s.points.forEach(function (p) { if (p[1] != null && isFinite(p[1])) { xs.push(p[0]); ys.push(p[1]); } }); });
      (o.hlines || []).forEach(function (l) { ys.push(l.y); }); (o.bands || []).forEach(function (b) { ys.push(b.y0, b.y1); });
      if (!xs.length) return { svg: '<svg viewBox="0 0 ' + W + ' 60" height="60"><text class="ax" x="' + (W / 2) + '" y="34" text-anchor="middle">Pas encore de données</text></svg>' };
      var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs); if (x1 === x0) x1 = x0 + 1;
      var y0 = o.y && o.y.min != null ? o.y.min : Math.min.apply(null, ys), y1 = o.y && o.y.max != null ? o.y.max : Math.max.apply(null, ys);
      if (o.y && o.y.zero) { y0 = Math.min(0, y0); y1 = Math.max(0, y1); }
      if (y1 === y0) { y1 += 1; y0 -= 1; } var padY = (y1 - y0) * 0.06; if (!(o.y && o.y.min != null)) y0 -= padY; if (!(o.y && o.y.max != null)) y1 += padY;
      var yt = ticks(y0, y1, o.yTicks || 4), fy = (o.y && o.y.fmt) || autoFmt(y1 - y0);
      var sx = function (v) { return m.l + (v - x0) / (x1 - x0) * (W - m.l - m.r); }, sy = function (v) { return m.t + (1 - (v - y0) / (y1 - y0)) * (H - m.t - m.b); };
      var g = '';
      (o.bands || []).forEach(function (b) { g += '<rect x="' + m.l + '" y="' + sy(Math.max(b.y0, b.y1)) + '" width="' + (W - m.l - m.r) + '" height="' + Math.abs(sy(b.y0) - sy(b.y1)) + '" fill="var(--violet-a)"/>'; if (b.label) g += '<text class="axl" x="' + (W - m.r - 4) + '" y="' + (sy(Math.max(b.y0, b.y1)) + 12) + '" text-anchor="end">' + X(b.label) + '</text>'; });
      yt.forEach(function (v) { if (v < y0 || v > y1) return; g += '<line class="' + (v === 0 ? 'zl' : 'gl') + '" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + sy(v) + '" y2="' + sy(v) + '"/><text class="ax" x="' + (m.l - 7) + '" y="' + (sy(v) + 3.5) + '" text-anchor="end">' + X(fy(v)) + '</text>'; });
      var xt = o.x && o.x.type === 'cat' ? null : ticks(x0, x1, Math.max(2, Math.floor((W - m.l - m.r) / 80)));
      var fx = (o.x && o.x.fmt) || (o.x && o.x.type === 'time' ? T.fmt.date : autoFmt(x1 - x0));
      if (o.x && o.x.type === 'time') { xt = []; var n = Math.max(2, Math.floor((W - m.l - m.r) / 84)); for (var i = 0; i <= n; i++) xt.push(x0 + (x1 - x0) * i / n); }
      if (xt) xt.forEach(function (v, i) { if (v < x0 - 1e-9 || v > x1 + 1e-9) return; var anchor = i === 0 && sx(v) - m.l < 20 ? 'start' : (sx(v) > W - m.r - 20 ? 'end' : 'middle'); g += '<text class="ax" x="' + sx(v) + '" y="' + (H - 8) + '" text-anchor="' + anchor + '">' + X(fx(v)) + '</text>'; });
      if (o.x && o.x.type === 'cat' && o.x.labels) { var lab = o.x.labels, step = Math.max(1, Math.ceil(lab.length / Math.max(2, Math.floor((W - m.l - m.r) / 54)))); lab.forEach(function (l, i) { if (i % step && i !== lab.length - 1) return; g += '<text class="ax" x="' + sx(i) + '" y="' + (H - 8) + '" text-anchor="' + (i === 0 ? 'start' : i === lab.length - 1 ? 'end' : 'middle') + '">' + X(l) + '</text>'; }); }
      (o.vlines || []).forEach(function (l) { var x = sx(l.x); g += '<line x1="' + x + '" x2="' + x + '" y1="' + m.t + '" y2="' + (H - m.b) + '" stroke="var(--line-2)" stroke-dasharray="3 4"/>' + (l.label ? '<text class="axl" x="' + (x + 4) + '" y="' + (m.t + 10) + '">' + X(l.label) + '</text>' : ''); });
      series.forEach(function (s) {
        var col = TONE[s.tone || 'fg'] || s.tone, d = '', pen = false, first = null, last = null;
        s.points.forEach(function (p) { if (p[1] == null || !isFinite(p[1])) { pen = false; return; } var px = sx(p[0]), py = sy(p[1]); d += (pen ? 'L' : 'M') + px.toFixed(1) + ',' + py.toFixed(1); pen = true; if (!first) first = [px, py]; last = [px, py, p[1]]; });
        if (s.area && first) { var base = sy(Math.max(y0, Math.min(y1, o.y && o.y.zero ? 0 : y0))); g += '<path d="' + d + 'L' + last[0].toFixed(1) + ',' + base + 'L' + first[0].toFixed(1) + ',' + base + 'Z" fill="' + col + '" opacity=".1"/>'; }
        g += '<path d="' + d + '" fill="none" stroke="' + col + '" stroke-width="' + (s.width || 1.6) + '"' + (s.dash ? ' stroke-dasharray="4 4"' : '') + ' stroke-linejoin="round" stroke-linecap="round"/>';
        if (o.endDots !== false && last) g += '<circle cx="' + last[0] + '" cy="' + last[1] + '" r="3" fill="' + col + '"/>';
      });
      (o.hlines || []).forEach(function (l) { var y = sy(l.y), col = TONE[l.tone || 'mute']; g += '<line x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + y + '" y2="' + y + '" stroke="' + col + '" stroke-dasharray="5 4" stroke-width="1.2"/>' + (l.label ? '<text class="axl" x="' + (m.l + 4) + '" y="' + (y - 5) + '">' + X(l.label) + '</text>' : ''); });
      g += '<line class="hl" x1="0" x2="0" y1="' + m.t + '" y2="' + (H - m.b) + '" stroke="var(--violet)" stroke-width="1" style="opacity:0"/>';
      var ref = series[0], hx = ref.points.map(function (p) { return sx(p[0]); });
      var hover = { xs: hx, html: function (i) { var p = ref.points[i], head = o.x && o.x.type === 'cat' && o.x.labels ? o.x.labels[i] : fx(p[0]); return '<b>' + X(head) + '</b><br>' + series.map(function (s) { var q = s.points[i]; return X(s.name || '') + ' ' + (q && q[1] != null ? X(fy(q[1])) : '—'); }).join('<br>'); } };
      return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '">' + g + '</svg>', hover: hover };
    });
  };

  /* Barres : cats [labels], series [{name, values, tone}], stacked, horizontal, fmt, zero baseline toujours incluse */
  C.bar = function (o) {
    var series = o.series || [], leg = series.length > 1 ? series.map(function (s) { return { label: s.name, box: TONE[s.tone || 'fg'] }; }) : null;
    return mount({ legend: leg }, function (W) {
      var cats = o.cats || [], n = cats.length, fmt = o.fmt || autoFmt(1);
      if (!n) return { svg: '<svg viewBox="0 0 ' + W + ' 60" height="60"><text class="ax" x="' + (W / 2) + '" y="34" text-anchor="middle">Pas encore de données</text></svg>' };
      var vals = []; cats.forEach(function (_, i) { if (o.stacked) { var p = 0, q = 0; series.forEach(function (s) { var v = s.values[i] || 0; if (v >= 0) p += v; else q += v; }); vals.push(p, q); } else series.forEach(function (s) { vals.push(s.values[i] || 0); }); });
      var lo = Math.min(0, Math.min.apply(null, vals)), hi = Math.max(0, Math.max.apply(null, vals)); if (hi === lo) hi = lo + 1;
      var g = '';
      if (o.horizontal) {
        var rowH = o.rowH || 26, m = { l: o.ml || 108, r: 54, t: 6, b: 6 }, H = m.t + m.b + n * rowH;
        var sx = function (v) { return m.l + (v - lo) / (hi - lo) * (W - m.l - m.r); };
        g += '<line class="zl" x1="' + sx(0) + '" x2="' + sx(0) + '" y1="' + m.t + '" y2="' + (H - m.b) + '"/>';
        cats.forEach(function (c, i) {
          var y = m.t + i * rowH, bh = (rowH - 8) / (o.stacked ? 1 : series.length), acc = 0, accN = 0;
          g += '<text class="axl" x="' + (m.l - 8) + '" y="' + (y + rowH / 2 + 3.5) + '" text-anchor="end">' + X(c) + '</text>';
          series.forEach(function (s, k) { var v = s.values[i] || 0, col = TONE[s.tone || (k ? 'violet' : 'fg')]; var a = o.stacked ? (v >= 0 ? acc : accN) : 0, b = a + v; if (o.stacked) { if (v >= 0) acc = b; else accN = b; } var x1 = sx(Math.min(a, b)), x2 = sx(Math.max(a, b)), yy = y + 4 + (o.stacked ? 0 : k * bh); g += '<rect x="' + x1 + '" y="' + yy + '" width="' + Math.max(1, x2 - x1) + '" height="' + (bh - 1) + '" rx="2" fill="' + col + '"' + (v < 0 ? ' opacity=".55"' : '') + '/>'; });
          var tot = series.reduce(function (s2, s) { return s2 + (s.values[i] || 0); }, 0); if (!o.stacked && series.length > 1) tot = series[0].values[i] || 0;
          g += '<text class="axl" x="' + (sx(Math.max(0, tot)) + 6) + '" y="' + (y + rowH / 2 + 3.5) + '">' + X(fmt(tot)) + '</text>';
        });
        return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '">' + g + '</svg>' };
      }
      var H2 = o.height || 200, m2 = { l: o.ml || 44, r: 10, t: 12, b: 26 }, yt = ticks(lo, hi, 4), sy = function (v) { return m2.t + (1 - (v - lo) / (hi - lo)) * (H2 - m2.t - m2.b); };
      yt.forEach(function (v) { g += '<line class="' + (v === 0 ? 'zl' : 'gl') + '" x1="' + m2.l + '" x2="' + (W - m2.r) + '" y1="' + sy(v) + '" y2="' + sy(v) + '"/><text class="ax" x="' + (m2.l - 7) + '" y="' + (sy(v) + 3.5) + '" text-anchor="end">' + X(fmt(v)) + '</text>'; });
      var bw = (W - m2.l - m2.r) / n, step = Math.max(1, Math.ceil(n / Math.max(2, Math.floor((W - m2.l - m2.r) / 46)))), xs = [];
      cats.forEach(function (c, i) {
        var x = m2.l + i * bw, inner = bw * 0.72, each = inner / (o.stacked ? 1 : series.length), acc = 0, accN = 0; xs.push(x + bw / 2);
        series.forEach(function (s, k) { var v = s.values[i] || 0, col = TONE[s.tone || (k ? 'violet' : 'fg')]; var a = o.stacked ? (v >= 0 ? acc : accN) : 0, b = a + v; if (o.stacked) { if (v >= 0) acc = b; else accN = b; } var yy = sy(Math.max(a, b)), hh = Math.max(1, Math.abs(sy(a) - sy(b))); g += '<rect x="' + (x + (bw - inner) / 2 + (o.stacked ? 0 : k * each)) + '" y="' + yy + '" width="' + Math.max(1, each - 1) + '" height="' + hh + '" rx="1.5" fill="' + col + '"' + (v < 0 ? ' opacity=".55"' : '') + '/>'; });
        if (i % step === 0 || i === n - 1) g += '<text class="ax" x="' + (x + bw / 2) + '" y="' + (H2 - 8) + '" text-anchor="middle">' + X(c) + '</text>';
      });
      g += '<line class="hl" x1="0" x2="0" y1="' + m2.t + '" y2="' + (H2 - m2.b) + '" stroke="var(--violet)" style="opacity:0"/>';
      return { svg: '<svg viewBox="0 0 ' + W + ' ' + H2 + '" height="' + H2 + '">' + g + '</svg>', hover: { xs: xs, html: function (i) { return '<b>' + X(cats[i]) + '</b><br>' + series.map(function (s) { return X(s.name || '') + ' ' + X(fmt(s.values[i] || 0)); }).join('<br>'); } } };
    });
  };

  /* Histogramme : values, bins, refs [{x,label,tone}], fmt */
  C.hist = function (o) {
    return mount(null, function (W) {
      var v = (o.values || []).filter(function (x) { return isFinite(x); }), H = o.height || 170, m = { l: 12, r: 12, t: 16, b: 26 };
      if (!v.length) return { svg: '<svg viewBox="0 0 ' + W + ' 60" height="60"><text class="ax" x="' + (W / 2) + '" y="34" text-anchor="middle">Pas encore de données</text></svg>' };
      var lo = o.min != null ? o.min : Math.min.apply(null, v), hi = o.max != null ? o.max : Math.max.apply(null, v); if (hi === lo) { hi = lo + 1; lo -= 1; }
      var nb = o.bins || Math.min(40, Math.max(8, Math.round(Math.sqrt(v.length)))), cnt = new Array(nb).fill(0), bwv = (hi - lo) / nb;
      v.forEach(function (x) { var i = Math.floor((x - lo) / bwv); if (i >= nb) i = nb - 1; if (i < 0) i = 0; cnt[i]++; });
      var mx = Math.max.apply(null, cnt), sx = function (x) { return m.l + (x - lo) / (hi - lo) * (W - m.l - m.r); }, sy = function (c) { return m.t + (1 - c / mx) * (H - m.t - m.b); }, f = o.fmt || autoFmt(hi - lo), g = '';
      cnt.forEach(function (c, i) { var x1 = sx(lo + i * bwv), x2 = sx(lo + (i + 1) * bwv), mid = lo + (i + .5) * bwv, col = o.split != null ? (mid < o.split ? 'var(--line-2)' : 'var(--hi)') : 'var(--hi)'; g += '<rect x="' + (x1 + .5) + '" y="' + sy(c) + '" width="' + Math.max(1, x2 - x1 - 1) + '" height="' + (H - m.b - sy(c)) + '" fill="' + col + '" opacity=".85"/>'; });
      g += '<line class="zl" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + (H - m.b) + '" y2="' + (H - m.b) + '"/>';
      ticks(lo, hi, Math.max(2, Math.floor((W - 24) / 80))).forEach(function (t) { if (t < lo || t > hi) return; g += '<text class="ax" x="' + sx(t) + '" y="' + (H - 8) + '" text-anchor="middle">' + X(f(t)) + '</text>'; });
      (o.refs || []).forEach(function (r, k) { if (!(r.x >= lo && r.x <= hi)) return; var x = sx(r.x); g += '<line x1="' + x + '" x2="' + x + '" y1="' + (m.t - 4) + '" y2="' + (H - m.b) + '" stroke="' + (TONE[r.tone || 'violet']) + '" stroke-width="1.5"' + (r.dash ? ' stroke-dasharray="4 3"' : '') + '/>' + (r.label ? '<text class="axl" x="' + (x + (x > W * 0.7 ? -4 : 4)) + '" y="' + (m.t + 4 + k * 12) + '" text-anchor="' + (x > W * 0.7 ? 'end' : 'start') + '" style="fill:' + TONE[r.tone || 'violet'] + '">' + X(r.label) + '</text>' : ''); });
      return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '">' + g + '</svg>' };
    });
  };

  /* Éventail Monte-Carlo : q {p05,p25,p50,p75,p95} (tableaux de même longueur), paths [[...]], hlines, fmt */
  C.fan = function (o) {
    return mount({ legend: o.legend }, function (W) {
      var q = o.q, n = q.p50.length, H = o.height || 220, m = { l: o.ml || 54, r: 14, t: 12, b: 26 };
      var all = q.p05.concat(q.p95); (o.hlines || []).forEach(function (l) { all.push(l.y); }); (o.paths || []).forEach(function (p) { all = all.concat(p); });
      var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all); var pd = (hi - lo) * 0.05 || 1; lo -= pd; hi += pd;
      var sx = function (i) { return m.l + i / Math.max(1, n - 1) * (W - m.l - m.r); }, sy = function (v) { return m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b); }, f = o.fmt || autoFmt(hi - lo), g = '';
      ticks(lo, hi, 4).forEach(function (v) { g += '<line class="gl" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + sy(v) + '" y2="' + sy(v) + '"/><text class="ax" x="' + (m.l - 7) + '" y="' + (sy(v) + 3.5) + '" text-anchor="end">' + X(f(v)) + '</text>'; });
      function band(a, b, op) { var d = ''; for (var i = 0; i < n; i++) d += (i ? 'L' : 'M') + sx(i).toFixed(1) + ',' + sy(a[i]).toFixed(1); for (var j = n - 1; j >= 0; j--) d += 'L' + sx(j).toFixed(1) + ',' + sy(b[j]).toFixed(1); g += '<path d="' + d + 'Z" fill="var(--violet)" opacity="' + op + '"/>'; }
      band(q.p05, q.p95, 0.13); band(q.p25, q.p75, 0.22);
      (o.paths || []).forEach(function (p) { var d = ''; p.forEach(function (v, i) { d += (i ? 'L' : 'M') + sx(i * (n - 1) / Math.max(1, p.length - 1)).toFixed(1) + ',' + sy(v).toFixed(1); }); g += '<path d="' + d + '" fill="none" stroke="var(--soft)" stroke-width=".8" opacity=".45"/>'; });
      var d2 = ''; q.p50.forEach(function (v, i) { d2 += (i ? 'L' : 'M') + sx(i).toFixed(1) + ',' + sy(v).toFixed(1); }); g += '<path d="' + d2 + '" fill="none" stroke="var(--hi)" stroke-width="1.8"/>';
      (o.hlines || []).forEach(function (l) { var y = sy(l.y); g += '<line x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + y + '" y2="' + y + '" stroke="' + TONE[l.tone || 'mute'] + '" stroke-dasharray="5 4"/><text class="axl" x="' + (W - m.r - 2) + '" y="' + (y - 5) + '" text-anchor="end">' + X(l.label || '') + '</text>'; });
      var xl = o.xLabel || function (i) { return String(i); }; [0, Math.floor((n - 1) / 2), n - 1].forEach(function (i, k) { g += '<text class="ax" x="' + sx(i) + '" y="' + (H - 8) + '" text-anchor="' + (k === 0 ? 'start' : k === 2 ? 'end' : 'middle') + '">' + X(xl(i)) + '</text>'; });
      g += '<line class="hl" x1="0" x2="0" y1="' + m.t + '" y2="' + (H - m.b) + '" stroke="var(--violet)" style="opacity:0"/>';
      var xs = []; for (var i = 0; i < n; i++) xs.push(sx(i));
      return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '">' + g + '</svg>', hover: { xs: xs, html: function (i) { return '<b>' + X(xl(i)) + '</b><br>médiane ' + X(f(q.p50[i])) + '<br>50 % entre ' + X(f(q.p25[i])) + ' et ' + X(f(q.p75[i])) + '<br>90 % entre ' + X(f(q.p05[i])) + ' et ' + X(f(q.p95[i])); } } };
    });
  };

  /* Sankey : nodes [{id,label,col}], links [{s,t,v}], fmt */
  C.sankey = function (o) {
    return mount(null, function (W) {
      var H = o.height || 260, nodes = o.nodes.map(function (n) { return Object.assign({ inV: 0, outV: 0, inOff: 0, outOff: 0 }, n); }), by = {}; nodes.forEach(function (n) { by[n.id] = n; });
      var links = (o.links || []).filter(function (l) { return l.v > 0 && by[l.s] && by[l.t]; });
      links.forEach(function (l) { by[l.s].outV += l.v; by[l.t].inV += l.v; });
      nodes.forEach(function (n) { n.v = Math.max(n.inV, n.outV, n.v0 || 0); });
      var cols = Math.max.apply(null, nodes.map(function (n) { return n.col; })) + 1, nw = 10, gap = 14, m = { l: 4, r: 4, t: 8, b: 8 };
      var colSum = []; nodes.forEach(function (n) { colSum[n.col] = (colSum[n.col] || 0) + n.v; });
      var colCount = []; nodes.forEach(function (n) { colCount[n.col] = (colCount[n.col] || 0) + 1; });
      var k = Infinity; for (var c = 0; c < cols; c++) { if (!colSum[c]) continue; k = Math.min(k, (H - m.t - m.b - gap * ((colCount[c] || 1) - 1)) / colSum[c]); }
      if (!isFinite(k) || k <= 0) return { svg: '<svg viewBox="0 0 ' + W + ' 60" height="60"><text class="ax" x="' + (W / 2) + '" y="34" text-anchor="middle">Pas encore de décisions</text></svg>' };
      var xOf = function (c) { return m.l + c * (W - m.l - m.r - nw) / Math.max(1, cols - 1); }, yCur = [];
      nodes.forEach(function (n) { var y = yCur[n.col] == null ? m.t : yCur[n.col]; n.x = xOf(n.col); n.y = y; n.h = Math.max(2, n.v * k); yCur[n.col] = y + n.h + gap; });
      var g = '', f = o.fmt || function (v) { return numFr(v, 0); };
      links.forEach(function (l) {
        var a = by[l.s], b = by[l.t], th = l.v * k, ya = a.y + a.outOff + th / 2, yb = b.y + b.inOff + th / 2; a.outOff += th; b.inOff += th;
        var x1 = a.x + nw, x2 = b.x, mx = (x1 + x2) / 2, col = l.tone ? TONE[l.tone] : 'var(--soft)';
        g += '<path d="M' + x1 + ',' + ya + ' C' + mx + ',' + ya + ' ' + mx + ',' + yb + ' ' + x2 + ',' + yb + '" fill="none" stroke="' + col + '" stroke-width="' + Math.max(1, th) + '" opacity="' + (l.tone === 'violet' ? '.42' : '.22') + '"/>';
      });
      /* Étiquettes : à droite du nœud, à gauche pour la dernière colonne ; une étiquette qui en heurte une autre
         change de côté (colonnes du milieu), puis descend d'une ligne tant qu'elle heurte. */
      var placed = [], CW = 6.3, LH = 13;
      function box(x, y, w, end) { return { x0: end ? x - w : x, x1: end ? x : x + w, y0: y - 10, y1: y + 3 }; }
      function hits(b) { return placed.some(function (p) { return b.x0 < p.x1 + 4 && b.x1 > p.x0 - 4 && b.y0 < p.y1 && b.y1 > p.y0; }); }
      var order = nodes.slice().sort(function (a, b) { return (b.col === cols - 1) - (a.col === cols - 1) || a.col - b.col || a.y - b.y; });
      order.forEach(function (n) {
        var w = (String(n.label).length + String(f(n.v)).length + 1) * CW, ty = n.y + Math.min(n.h / 2, 18) + 3;
        var end = !(n.col < cols - 1), tx = end ? n.x - 6 : n.x + nw + 6, b = box(tx, ty, w, end);
        if (hits(b) && n.col > 0 && n.col < cols - 1) { var e2 = !end, x2 = e2 ? n.x - 6 : n.x + nw + 6, b2 = box(x2, ty, w, e2); if (!hits(b2)) { end = e2; tx = x2; b = b2; } }
        for (var t = 0; t < 6 && hits(b); t++) { ty += LH; b = box(tx, ty, w, end); }
        placed.push(b); n._t = { x: tx, y: ty, end: end };
      });
      nodes.forEach(function (n) {
        g += '<rect x="' + n.x + '" y="' + n.y + '" width="' + nw + '" height="' + n.h + '" rx="2" fill="' + (n.tone ? TONE[n.tone] : 'var(--hi)') + '"/>';
      });
      nodes.forEach(function (n) {
        g += '<text class="axl" x="' + n._t.x + '" y="' + n._t.y + '" text-anchor="' + (n._t.end ? 'end' : 'start') + '"><tspan style="fill:var(--fg)">' + X(n.label) + '</tspan> <tspan style="fill:var(--mute)">' + X(f(n.v)) + '</tspan></text>';
      });
      return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '">' + g + '</svg>' };
    });
  };

  /* Échelle de niveaux : levels [{price,label,kind}], price (prix courant), fmt */
  C.ladder = function (o) {
    return mount(null, function (W) {
      var lv = (o.levels || []).filter(function (l) { return isFinite(l.price); }).slice().sort(function (a, b) { return b.price - a.price; });
      if (!lv.length) return { svg: '<svg viewBox="0 0 ' + W + ' 60" height="60"><text class="ax" x="' + (W / 2) + '" y="34" text-anchor="middle">Aucun niveau</text></svg>' };
      var ps = lv.map(function (l) { return l.price; }); if (isFinite(o.price)) ps.push(o.price);
      var hi = Math.max.apply(null, ps), lo = Math.min.apply(null, ps); var pd = (hi - lo) * 0.06 || 5; hi += pd; lo -= pd;
      var rowMin = 20, H = Math.max(o.height || 240, lv.length * rowMin + 24), m = { t: 12, b: 12 }, sy = function (p) { return m.t + (hi - p) / (hi - lo) * (H - m.t - m.b); }, f = o.fmt || function (v) { return numFr(v, 2); }, g = '', lastY = -Infinity;
      var ys = lv.map(function (l) { return sy(l.price); }); for (var i = 1; i < ys.length; i++) if (ys[i] - ys[i - 1] < 16) ys[i] = ys[i - 1] + 16;
      lv.forEach(function (l, i) {
        var y = sy(l.price), ly = ys[i], col = l.kind === 'violet' ? 'var(--violet)' : l.kind === 'mute' ? 'var(--line-2)' : 'var(--soft)';
        g += '<line x1="' + 70 + '" x2="' + (W - 92) + '" y1="' + y + '" y2="' + y + '" stroke="' + col + '"' + (l.dash ? ' stroke-dasharray="4 4"' : '') + ' stroke-width="1.3"/>';
        g += '<text class="axl" x="64" y="' + (ly + 3.5) + '" text-anchor="end" style="fill:var(--fg)">' + X(l.label) + '</text><text class="ax" x="' + (W - 4) + '" y="' + (ly + 3.5) + '" text-anchor="end">' + X(f(l.price)) + '</text>';
        if (Math.abs(ly - y) > 1) g += '<line x1="66" x2="70" y1="' + ly + '" y2="' + y + '" stroke="var(--line-2)"/>';
      });
      if (isFinite(o.price)) { var yp = sy(o.price); g += '<rect x="70" y="' + (yp - 1) + '" width="' + (W - 162) + '" height="2" fill="var(--violet)"/><rect x="' + (W - 90) + '" y="' + (yp - 9) + '" width="86" height="18" rx="4" fill="var(--violet)"/><text x="' + (W - 47) + '" y="' + (yp + 4) + '" text-anchor="middle" style="font:600 11px var(--f-mono)" fill="var(--ink)">' + X(f(o.price)) + '</text>'; }
      return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '">' + g + '</svg>' };
    });
  };

  /* Jauge horizontale : value, min, max, log, band [a,b], ticks [[v,label]], fmt */
  C.gauge = function (o) {
    return mount(null, function (W) {
      var H = 46, m = { l: 10, r: 10 }, lg = !!o.log, a = lg ? Math.log10(o.min) : o.min, b = lg ? Math.log10(o.max) : o.max;
      var sx = function (v) { var x = lg ? Math.log10(Math.min(Math.max(v, o.min), o.max)) : Math.min(Math.max(v, o.min), o.max); return m.l + (x - a) / (b - a) * (W - m.l - m.r); }, g = '';
      g += '<line x1="' + m.l + '" x2="' + (W - m.r) + '" y1="16" y2="16" stroke="var(--line-2)"/>';
      if (o.band) g += '<rect x="' + sx(o.band[0]) + '" y="10" width="' + (sx(o.band[1]) - sx(o.band[0])) + '" height="12" rx="3" fill="var(--violet-a)" stroke="var(--violet-b)"/>';
      (o.ticks || []).forEach(function (t) { g += '<text class="ax" x="' + sx(t[0]) + '" y="40" text-anchor="middle">' + X(t[1]) + '</text>'; });
      if (isFinite(o.value)) g += '<rect x="' + (sx(o.value) - 1.5) + '" y="4" width="3" height="24" rx="1.5" fill="var(--hi)"/>';
      return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '">' + g + '</svg>' };
    });
  };

  /* Quadrant : x/y labels, quadrants [tl,tr,bl,br], points [{x,y,label}] dans [-1,1] */
  C.quadrant = function (o) {
    return mount(null, function (W) {
      var S2 = Math.min(W, 420), H = S2, ox = (W - S2) / 2, c = S2 / 2, g = '', q = o.quadrants || ['', '', '', ''];
      var p = function (v) { return Math.max(-1, Math.min(1, v)); };
      g += '<rect x="' + ox + '" y="0" width="' + S2 + '" height="' + H + '" fill="none" stroke="var(--line)"/>';
      g += '<line x1="' + (ox + c) + '" x2="' + (ox + c) + '" y1="0" y2="' + H + '" stroke="var(--line-2)"/><line x1="' + ox + '" x2="' + (ox + S2) + '" y1="' + c + '" y2="' + c + '" stroke="var(--line-2)"/>';
      [[ox + 10, 20, 'start', q[0]], [ox + S2 - 10, 20, 'end', q[1]], [ox + 10, H - 12, 'start', q[2]], [ox + S2 - 10, H - 12, 'end', q[3]]].forEach(function (t) { g += '<text class="axl" x="' + t[0] + '" y="' + t[1] + '" text-anchor="' + t[2] + '" style="fill:var(--fg)">' + X(t[3]) + '</text>'; });
      g += '<text class="ax" x="' + (ox + S2 - 6) + '" y="' + (c - 6) + '" text-anchor="end">' + X(o.xLabel || '') + ' →</text><text class="ax" x="' + (ox + c + 6) + '" y="' + 36 + '">↑ ' + X(o.yLabel || '') + '</text>';
      (o.points || []).forEach(function (pt, i) { var x = ox + c + p(pt.x) * (c - 14), y = c - p(pt.y) * (c - 14); g += '<circle cx="' + x + '" cy="' + y + '" r="' + (i === (o.points.length - 1) ? 6 : 3.5) + '" fill="' + (i === o.points.length - 1 ? 'var(--violet)' : 'var(--soft)') + '"/>' + (pt.label ? '<text class="axl" x="' + (x + 9) + '" y="' + (y + 4) + '" style="fill:var(--fg)">' + X(pt.label) + '</text>' : ''); });
      return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '">' + g + '</svg>' };
    });
  };

  /* Petite courbe */
  C.spark = function (values, o) {
    o = o || {};
    return mount(null, function (W) {
      var v = (values || []).filter(isFinite), H = o.height || 36; if (v.length < 2) return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '"></svg>' };
      var lo = Math.min.apply(null, v), hi = Math.max.apply(null, v); if (hi === lo) hi = lo + 1;
      var d = ''; v.forEach(function (y, i) { d += (i ? 'L' : 'M') + (i / (v.length - 1) * (W - 4) + 2).toFixed(1) + ',' + (2 + (1 - (y - lo) / (hi - lo)) * (H - 4)).toFixed(1); });
      return { svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '"><path d="' + d + '" fill="none" stroke="' + (o.tone ? TONE[o.tone] : 'var(--violet)') + '" stroke-width="1.5"/></svg>' };
    });
  };

  /* Carte de chaleur (tableau) : rows [label], cols [label], values [[...]], fmt, diverging */
  C.heat = function (o) {
    var vals = []; (o.values || []).forEach(function (r) { r.forEach(function (v) { if (isFinite(v)) vals.push(Math.abs(v)); }); });
    var mx = vals.length ? Math.max.apply(null, vals) : 1, f = o.fmt || function (v) { return numFr(v, 1); };
    return h('div', { class: 'heat' }, h('table', null,
      h('thead', null, h('tr', null, h('th', { class: 'rl' }, o.corner || ''), (o.cols || []).map(function (c) { return h('th', null, c); }))),
      h('tbody', null, (o.rows || []).map(function (r, i) { return h('tr', null, h('th', { class: 'rl' }, r), (o.values[i] || []).map(function (v) { var a = isFinite(v) ? Math.abs(v) / (mx || 1) : 0, bg = !isFinite(v) ? 'transparent' : (v < 0 && o.diverging ? 'rgba(163,163,173,' + (0.08 + a * 0.4).toFixed(3) + ')' : 'rgba(155,140,255,' + (0.08 + a * 0.5).toFixed(3) + ')'); return h('td', { style: 'background:' + bg }, isFinite(v) ? f(v) : '—'); })); }))));
  };

  /* ================= Coquille : menu, navigation ================= */
  T.desk = function (def) { DESKS.push(def); DESKS.sort(function (a, b) { return (a.order == null ? 99 : a.order) - (b.order == null ? 99 : b.order); }); };
  T.desks = function () { return DESKS.slice(); };
  var cur = { id: null, tab: null, cleanup: null }, RET = null;
  T.nav = {
    current: function () { return cur.id; },
    /* Retour : un desk ouvert depuis une étape du plan porte en tête un bouton qui y ramène. r = { desk, tab, label: function () → texte, onBack } */
    setReturn: function (r) { RET = r || null; },
    go: function (id, tab, keep) {
      var d = DESKS.find(function (x) { return x.id === id; }) || DESKS[0]; if (!d) return;
      if (cur.cleanup) { try { cur.cleanup(); } catch (e) {} cur.cleanup = null; }
      cur.id = d.id; cur.tab = tab || (T.store.get('tab:' + d.id, null)) || (d.tabs ? d.tabs[0].id : null);
      var view = document.getElementById('view'); var sy0 = window.scrollY; T.clear(view);
      var ctx = { tab: cur.tab, settings: T.settings.get(), setTab: function (t) { T.store.set('tab:' + d.id, t); T.nav.go(d.id, t, true); }, go: T.nav.go, rerender: function () { if (T.nav.current() === d.id) T.nav.go(d.id, cur.tab, true); } };
      view.classList.toggle('still', !!keep); var sy = sy0;
      try { var c = d.render(view, ctx); if (typeof c === 'function') cur.cleanup = c; }
      catch (e) { console.error(e); view.appendChild(U.empty({ title: 'Ce desk a rencontré une erreur', text: String(e && e.message || e) })); }
      if (RET && RET.desk === d.id) RET = null;
      else if (RET) { var rt = RET, lab = ''; try { lab = rt.label(); } catch (e) { lab = 'Revenir au plan'; } view.insertBefore(h('button', { class: 'retbar', type: 'button', on: { click: function () { var r2 = rt; RET = null; if (r2.onBack) r2.onBack(); T.nav.go(r2.desk, r2.tab); } } }, h('span', null, '‹'), h('b', null, lab)), view.firstChild); }
      try { T.typoTree(view); } catch (e) {}
      try { history.replaceState(null, '', '#' + d.id); } catch (e) {}
      lsSet('last', d.id);
      document.querySelectorAll('.side .lk').forEach(function (a) { a.setAttribute('aria-current', a.dataset.id === d.id ? 'page' : 'false'); });
      var sub = document.getElementById('deskName'); if (sub) sub.textContent = d.label;
      if (keep) window.scrollTo(0, sy); else { closeMenu(); window.scrollTo(0, 0); }
    }
  };
  function openMenu() { document.querySelector('.side').classList.add('on'); document.querySelector('.scrim').classList.add('on'); }
  function closeMenu() { var s = document.querySelector('.side'); if (s) s.classList.remove('on'); var c = document.querySelector('.scrim'); if (c) c.classList.remove('on'); }
  T.toast = (function () { var tt; return function (msg) { var t = document.getElementById('toast'); if (!t) return; t.textContent = msg; t.classList.add('on'); clearTimeout(tt); tt = setTimeout(function () { t.classList.remove('on'); }, 1900); }; })();

  T.logo = function (size) {
    return '<svg class="logo" viewBox="0 0 26 26" width="' + (size || 26) + '" height="' + (size || 26) + '" aria-hidden="true"><rect x=".75" y=".75" width="24.5" height="24.5" rx="6.5" fill="none" stroke="var(--hi)" stroke-width="1.5"/><path d="M6 18.5 11 13l3.5 3.5L20 8" fill="none" stroke="var(--hi)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><line x1="5" x2="21" y1="12" y2="12" stroke="var(--violet)" stroke-width="1.4" stroke-dasharray="2 2"/></svg>';
  };

  T.boot = function () {
    var side = document.querySelector('.side nav'); T.clear(side);
    var groups = []; DESKS.forEach(function (d) { var g = d.group || 'Desk'; var G = groups.find(function (x) { return x.n === g; }); if (!G) groups.push(G = { n: g, d: [] }); G.d.push(d); });
    groups.forEach(function (G) { side.appendChild(h('div', { class: 'grp' }, G.n)); G.d.forEach(function (d) { side.appendChild(h('button', { class: 'lk', type: 'button', 'data-id': d.id, on: { click: function () { T.nav.go(d.id); } } }, h('span', { class: 'gl' }, d.glyph || d.label[0]), d.label, d.badge ? h('small', null, d.badge) : null)); }); });
    document.getElementById('menuBtn').addEventListener('click', openMenu);
    document.querySelector('.scrim').addEventListener('click', closeMenu);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeMenu(); });
    var st = document.getElementById('saveSt');
    function paint(s) { st.innerHTML = '<i class="dot ' + (s === 'cloud' ? 'on' : s === 'saving' ? 'hi' : '') + '"></i>' + ({ cloud: 'compte', saving: '…', local: 'appareil' }[s] || 'appareil'); }
    paint(cloud.status); T.saveStatus.on(paint);
    var hash = (location.hash || '').replace('#', ''), start = DESKS.some(function (d) { return d.id === hash; }) ? hash : (lsGet('last') || (DESKS[0] && DESKS[0].id));
    T.nav.go(start);
    try { new MutationObserver(function (ms) { ms.forEach(function (m) { m.addedNodes.forEach(function (n) { T.typoTree(n); }); }); }).observe(document.getElementById('view'), { childList: true, subtree: true }); } catch (e) {}
    T.cloudInit();
    document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') Object.keys(store.mem).forEach(function (k) { if (cloud.ready) push(k); }); });
  };
})();
