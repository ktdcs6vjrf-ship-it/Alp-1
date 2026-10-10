/* Desk « NQ futures » : la séance calculée depuis New York, les niveaux GEX collés tels quels, le contrat et sa case, la taille.
   Sources, contrôlées par test/nq.test.js :
   – Lecture des niveaux : portage de pine/alp0-gex.pine et de tools/gex_lecture_sim.py (dépôt ALP). Vocabulaire codeDe,
     préfixe d’échéance lu dans « horizon », titres ## qui commutent, tiret conservé, fenêtre de plausibilité, R1 R2 S1 S2
     tirés du bloc CSV par somme des valeurs absolues des jambes, classés après que la base soit tranchée.
   – ALP nº 3, partie XIX : demi-largeur √(2 ln 2)·σ√T = 1,177 σ√T (26,7 points à deux heures, 93 points à un jour, σ = 25 %,
     indice à 6 000) ; à signe inconnu la bascule occupe 1 219 points, 135 fois le stop élargi, et n’existe pas dans 47,9 %
     des tirages ; sur cinq affirmations, aucune ne donne le sens.
   – ALP nº 3, partie XII, table 24 : case = 60·c/3,2 minutes ; c de référence 0,45 pt (NQ) et 2,25 pt (MNQ), soit 8,4 et
     42,2 minutes (commission 4 $ et un tick de sortie : costs.COST_BASE).
   – ALP nº 3, partie XI : à dérive nulle, E[R] = −c/L pour toute géométrie.
   – Spécifications CME Group : NQ 20 $ par point, MNQ 2 $, tick 0,25 ; Globex du dimanche 18 h au vendredi 17 h (heure de
     New York), pause 17 h–18 h ; mois H M U Z ; dernier jour de cotation : troisième vendredi, 9 h 30 ET. */
var h = T.h, U = T.ui, C = T.chart, F = T.fmt;
T.lib = T.lib || {};
var L = T.lib.nq = {};
var K = { gex: 'nq:gex', bias: 'nq:bias', frais: 'nq:frais', taille: 'nq:taille' };
L.KEYS = K;
var NY = 'America/New_York', PA = 'Europe/Paris', LO = 'Europe/London';

/* =====================================================================
   1. Fonctions pures — aucun DOM, aucun T.store
   ===================================================================== */
function fin(v) { return typeof v === 'number' && isFinite(v); }
function pad(n) { return String(n).padStart(2, '0'); }
L.fin = fin;

/* ---------- Le contrat ---------- */
L.SPEC = {
  NQ: { sym: 'NQ', nom: 'E-mini Nasdaq-100', pv: 20, tick: 0.25 },
  MNQ: { sym: 'MNQ', nom: 'Micro E-mini Nasdaq-100', pv: 2, tick: 0.25 }
};
L.INSTS = ['MNQ', 'NQ'];
L.MOIS = [{ m: 3, c: 'H', n: 'mars' }, { m: 6, c: 'M', n: 'juin' }, { m: 9, c: 'U', n: 'septembre' }, { m: 12, c: 'Z', n: 'décembre' }];
L.PLAFOND = 3.2;                       /* pt/h : borne haute du domaine de dérive plausible (ALP nº 3) */
L.REF = { commission: 4, slipTicks: 1 }; /* friction de référence d’ALP nº 3 : costs.COST_BASE */
L.tickValue = function (inst) { var s = L.SPEC[inst]; return s ? s.pv * s.tick : NaN; };
/* Friction aller-retour en points : commission ÷ valeur du point + glissement en ticks × tick. */
L.friction = function (o) {
  o = o || {};
  if (!(o.pointValue > 0) || !fin(o.commission) || o.commission < 0) return NaN;
  var slip = fin(o.slipTicks) && o.slipTicks >= 0 ? o.slipTicks : 0, tick = fin(o.tick) ? o.tick : 0.25;
  return o.commission / o.pointValue + slip * tick;
};
/* La case : durée de tenue sous laquelle aucune dérive plausible ne couvre la friction. 60·c/3,2 minutes. */
L.caseMin = function (c, plafond) { var p = fin(plafond) && plafond > 0 ? plafond : L.PLAFOND; return fin(c) && c >= 0 ? 60 * c / p : NaN; };
L.refFriction = function (inst) { var s = L.SPEC[inst]; return L.friction({ commission: L.REF.commission, pointValue: s.pv, tick: s.tick, slipTicks: L.REF.slipTicks }); };

/* Taille : contrats = plancher(risque ÷ (stop × valeur du point + commission)). */
L.size = function (o) {
  o = o || {};
  var risk = o.risk, stop = o.stop, pv = o.pointValue, com = fin(o.commission) && o.commission >= 0 ? o.commission : 0;
  if (!fin(risk) || risk <= 0 || !fin(stop) || stop <= 0 || !(pv > 0)) return { ok: false, contracts: 0, perContract: NaN, realRisk: 0, unused: fin(risk) ? risk : NaN };
  var per = stop * pv + com, n = Math.floor(risk / per + 1e-9);
  n = Math.max(0, n);
  return { ok: true, contracts: n, perContract: per, realRisk: n * per, unused: risk - n * per };
};
/* À dérive nulle, chaque trade coûte −c/L en multiples du risque (ALP nº 3, partie XI). */
L.costR = function (c, stop) { return fin(c) && fin(stop) && stop > 0 ? -c / stop : NaN; };

L.thirdFriday = function (y, m) { var wd = new Date(Date.UTC(y, m - 1, 1)).getUTCDay(), first = 1 + ((5 - wd + 7) % 7); return first + 14; };
/* Échéance en cours : le premier mois trimestriel dont le troisième vendredi n’est pas passé (le jour même compte encore). */
L.frontContract = function (y, mo, d) {
  var key = y * 10000 + mo * 100 + d;
  for (var yr2 = y; yr2 <= y + 1; yr2++) {
    for (var j = 0; j < L.MOIS.length; j++) {
      var mm = L.MOIS[j], tf = L.thirdFriday(yr2, mm.m);
      if (yr2 * 10000 + mm.m * 100 + tf >= key) {
        var roll = L.addDays(yr2, mm.m, tf, -8);
        return { code: mm.c, mois: mm.n, y: yr2, m: mm.m, expiry: { y: yr2, mo: mm.m, d: tf }, roll: roll, sym: mm.c + String(yr2 % 10) };
      }
    }
  }
  return null;
};

/* ---------- Le temps : tout se calcule depuis New York ---------- */
var FMTS = {};
function parts(tz, t) {
  var f = FMTS[tz] || (FMTS[tz] = new Intl.DateTimeFormat('en-GB', { timeZone: tz, hour12: false, weekday: 'short', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }));
  var o = {}; f.formatToParts(new Date(t)).forEach(function (p) { o[p.type] = p.value; });
  return { y: +o.year, mo: +o.month, d: +o.day, h: +o.hour % 24, m: +o.minute, s: +o.second, wd: { Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6, Sun: 0 }[o.weekday] };
}
L.parts = parts;
L.offsetMin = function (tz, t) { var p = parts(tz, t); return Math.round((Date.UTC(p.y, p.mo - 1, p.d, p.h, p.m, p.s) - Math.floor(t / 1000) * 1000) / 60000); };
/* L’instant UTC d’une heure murale dans un fuseau : deux passes suffisent, y compris les jours de changement d’heure. */
L.zonedToUtc = function (y, mo, d, hh, mi, tz) {
  var g = Date.UTC(y, mo - 1, d, hh, mi), o1 = L.offsetMin(tz, g), t = g - o1 * 60000, o2 = L.offsetMin(tz, t);
  return o2 === o1 ? t : g - o2 * 60000;
};
L.addDays = function (y, mo, d, k) { var u = new Date(Date.UTC(y, mo - 1, d + k)); return { y: u.getUTCFullYear(), mo: u.getUTCMonth() + 1, d: u.getUTCDate(), wd: u.getUTCDay() }; };
L.hhmm = function (t, tz) { var p = parts(tz, t); return pad(p.h) + ':' + pad(p.m); };
L.hhmmss = function (t, tz) { var p = parts(tz, t); return pad(p.h) + ':' + pad(p.m) + ':' + pad(p.s); };
L.dayKey = function (t, tz) { var p = parts(tz || PA, t); return p.y + '-' + pad(p.mo) + '-' + pad(p.d); };
/* Écart Paris − New York, en heures : 6 la plupart de l’année, 5 quand les deux pays n’ont pas encore changé d’heure ensemble. */
L.gap = function (t) { return (L.offsetMin(PA, t) - L.offsetMin(NY, t)) / 60; };
L.nextGapChange = function (t) {
  var g0 = L.gap(t), p = parts(PA, t);
  for (var k = 1; k <= 400; k++) { var d = L.addDays(p.y, p.mo, p.d, k), tk = Date.UTC(d.y, d.mo - 1, d.d, 12, 0), g = L.gap(tk); if (g !== g0) return { y: d.y, mo: d.mo, d: d.d, gap: g }; }
  return null;
};

/* L’état du marché à un instant. Conventions : Asie = de la réouverture Globex (18 h ET) à l’ouverture de Londres
   (8 h, heure de Londres) ; Europe = de Londres à l’ouverture cash de New York ; cash US 9 h 30–16 h ET ;
   après-cash 16 h–17 h ET ; pause Globex 17 h–18 h ET ; fermé du vendredi 17 h au dimanche 18 h ET. */
L.STATES = ['asie', 'europe', 'cash', 'apres', 'pause', 'ferme'];
L.classify = function (t) {
  var p = parts(NY, t), mn = p.h * 60 + p.m, wd = p.wd;
  if (wd === 6 || (wd === 0 && mn < 1080) || (wd === 5 && mn >= 1020)) return 'ferme';
  if (mn >= 1020 && mn < 1080) return 'pause';
  if (wd >= 1 && wd <= 5 && mn >= 570 && mn < 960) return 'cash';
  if (wd >= 1 && wd <= 5 && mn >= 960 && mn < 1020) return 'apres';
  if (mn >= 1080) return 'asie';
  var q = parts(LO, t);
  return q.h * 60 + q.m >= 480 ? 'europe' : 'asie';
};
/* La frise du jour de Paris qui contient t : segments [from, to) en minutes murales de Paris. */
L.frieze = function (t, step) {
  step = step || 5;
  var p = parts(PA, t), start = L.zonedToUtc(p.y, p.mo, p.d, 0, 0, PA), segs = [];
  for (var i = 0; i < 1500 / step; i++) {
    var ti = start + i * step * 60000, q = parts(PA, ti);
    if (q.d !== p.d) break;
    var w = q.h * 60 + q.m, st = L.classify(ti), last = segs[segs.length - 1];
    if (last && last.state === st && last.to === w) last.to = w + step; else segs.push({ from: w, to: w + step, state: st, t0: ti });
  }
  return { segs: segs, nowMin: p.h * 60 + p.m + p.s / 60, start: start, date: { y: p.y, mo: p.mo, d: p.d, wd: p.wd } };
};
/* Les repères d’un jour de Paris, calculés depuis New York (et Londres pour l’Europe). */
L.reperes = function (y, mo, d) {
  var veille = L.addDays(y, mo, d, -1), wd = new Date(Date.UTC(y, mo - 1, d)).getUTCDay();
  var at = function (dd, hh, mi, tz) { return L.zonedToUtc(dd.y, dd.mo, dd.d, hh, mi, tz || NY); }, jour = { y: y, mo: mo, d: d };
  return {
    ouvre: wd >= 1 && wd <= 5,
    reouverture: at(veille, 18, 0), londres: at(jour, 8, 0, LO),
    cashOpen: at(jour, 9, 30), cashClose: at(jour, 16, 0), pause: at(jour, 17, 0), reprise: at(jour, 18, 0)
  };
};
/* Les prochaines bascules : cash (ouverture, clôture) et Globex (pause, fermeture du vendredi, réouverture). */
L.events = function (t) {
  var p = parts(NY, t), ev = [];
  for (var k = -1; k <= 8; k++) {
    var dd = L.addDays(p.y, p.mo, p.d, k), at = (function (dd) { return function (hh, mi) { return L.zonedToUtc(dd.y, dd.mo, dd.d, hh, mi, NY); }; })(dd);
    if (dd.wd >= 1 && dd.wd <= 5) { ev.push({ t: at(9, 30), k: 'cashOpen' }); ev.push({ t: at(16, 0), k: 'cashClose' }); ev.push({ t: at(17, 0), k: dd.wd === 5 ? 'weekClose' : 'pause' }); }
    if (dd.wd >= 0 && dd.wd <= 4) ev.push({ t: at(18, 0), k: 'reopen' });
  }
  return ev.filter(function (e) { return e.t > t; }).sort(function (a, b) { return a.t - b.t; });
};
L.etat = function (t) {
  var st = L.classify(t), ev = L.events(t), globex = st !== 'ferme' && st !== 'pause', cash = st === 'cash';
  var nextG = ev.filter(function (e) { return globex ? (e.k === 'pause' || e.k === 'weekClose') : e.k === 'reopen'; })[0] || null;
  var nextC = ev.filter(function (e) { return cash ? e.k === 'cashClose' : e.k === 'cashOpen'; })[0] || null;
  return { state: st, globex: globex, cash: cash, nextGlobex: nextG, nextCash: nextC };
};
/* Fenêtre de l’utilisateur en heures de Paris (from, to) : ouverte ou non, et minutes jusqu’à la prochaine bascule. */
L.windowCountdown = function (p, from, to) {
  var now = p.h * 60 + p.m + (p.s || 0) / 60, fm = from * 60, tm = to * 60, open;
  if (!fin(from) || !fin(to) || from === to) return { open: false, min: NaN };
  open = from < to ? (now >= fm && now < tm) : (now >= fm || now < tm);
  var mod = function (x) { return ((x % 1440) + 1440) % 1440; };
  return { open: open, min: open ? mod(tm - now) : mod(fm - now) };
};
L.fmtCount = function (ms) {
  if (!fin(ms)) return '—';
  var s = Math.max(0, Math.round(ms / 1000)), d = Math.floor(s / 86400), hh = Math.floor((s % 86400) / 3600), mm = Math.floor((s % 3600) / 60), ss = s % 60;
  if (d > 0) return d + ' j ' + pad(hh) + ' h';
  if (hh > 0) return hh + ' h ' + pad(mm);
  if (mm > 0) return mm + ' min ' + pad(ss) + ' s';
  return ss + ' s';
};
L.fmtHour = function (x) { if (!fin(x)) return '—'; var m = Math.round(x * 60); return pad(Math.floor(m / 60) % 24) + ':' + pad(m % 60); };

/* ---------- Lecture d’un export de robot (portage de alp0-gex.pine) ---------- */
L.MINTICK = 0.25; L.MAXN = 20;
/* Un nombre se nettoie de ce qui le décore, jamais de ce qui le signe. Extension sûre : une virgule suivie d’un ou deux
   chiffres est une virgule décimale (un séparateur de milliers en porte toujours trois), et le vrai signe moins vaut le tiret. */
L.cleanNum = function (s) {
  var t = String(s == null ? '' : s).replace(/−/g, '-').replace(/[\s  *`$_]/g, '');
  if (/^-?\d+,\d{1,2}$/.test(t)) return t.replace(',', '.');
  return t.replace(/,/g, '');
};
L.cleanTag = function (s) { return String(s == null ? '' : s).replace(/[*`#]/g, '').replace(/-/g, ' ').trim(); };
L.toNumber = function (s) { var t = String(s == null ? '' : s); return /^[-+]?(\d+\.?\d*|\.\d+)$/.test(t) ? parseFloat(t) : NaN; };
L.num = function (s) { return L.toNumber(L.cleanNum(s)); };
L.teteNumerique = function (s) {
  var t = L.cleanTag(s), out = '';
  for (var k = 0; k < Math.min(t.length, 3); k++) { var ch = t.charAt(k); if (!fin(L.toNumber(ch))) break; out += ch; }
  return out;
};
/* La table de correspondance : l’ordre des tests porte le sens (« major wall » en GW avant que « wall » ne bascule,
   « resistance macro » en RM avant que « resistance » ne le prenne). RM est exempt de préfixe : « macro » est son échéance. */
L.codeDe = function (tag, pref) {
  var t = String(tag == null ? '' : tag).trim().toLowerCase(), c;
  if (t === '') c = '';
  else if (t.indexOf('macro') >= 0 || t === 'rm') c = 'RM';
  else if (t.indexOf('flip') >= 0 || t.indexOf('hvl') >= 0) c = 'HVL';
  else if (t.indexOf('max pain') >= 0 || t.indexOf('maxpain') >= 0 || t === 'mp') c = 'MP';
  else if (t.indexOf('gamma wall') >= 0 || t.indexOf('major wall') >= 0 || t === 'gw') c = 'GW';
  else if (t.indexOf('call') >= 0 || t.indexOf('resist') >= 0 || t === 'cr') c = 'CR';
  else if (t.indexOf('put') >= 0 || t.indexOf('support') >= 0 || t === 'ps') c = 'PS';
  else c = t.toUpperCase();
  var deja = c !== '' && fin(L.toNumber(c.charAt(0)));
  return c === '' || !pref || deja || c === 'RM' ? c : pref + c;
};
L.NOMS = { PS: 'put support', CR: 'call resistance', MP: 'max pain', GW: 'gamma wall', HVL: 'gamma flip', RM: 'résistance macro' };
L.nomDe = function (code, src) {
  if (src === 'calcul') return 'tirée du CSV';
  if (!code) return 'sans nom';
  return code.split('/').map(function (c) {
    var b = c.replace(/^\d+/, '');
    if (L.NOMS[b]) return L.NOMS[b];
    if (/^[RS]\d$/.test(b)) return (b.charAt(0) === 'R' ? 'résistance ' : 'support ') + b.charAt(1);
    return b ? b.toLowerCase() : 'sans nom';
  }).join(' / ');
};
function sansAccent(s) { return String(s).normalize ? String(s).normalize('NFD').replace(/[̀-ͯ]/g, '') : String(s); }
function median(a) { if (!a.length) return NaN; var s = a.slice().sort(function (x, y) { return x - y; }), n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; }
L.median = median;

/* parseGex(texte, prix NQ, base NQ − NDX, options) → niveaux. Pure.
   options : bandePct (fenêtre, 3 % par défaut comme l’indicateur), appliquer ('auto' | 'toujours' | 'jamais'),
   today ('AAAA-MM-JJ', date de New York, pour lire l’échéance dans la colonne d’expiration), secondaires, nSec. */
L.parseGex = function (texte, prix, base, opts) {
  opts = opts || {};
  var raw = String(texte == null ? '' : texte).replace(/\r\n?/g, '\n');
  var price = fin(prix) ? prix : NaN, basis = fin(base) ? base : NaN;
  var bandePct = fin(opts.bandePct) && opts.bandePct > 0 ? opts.bandePct : 3, bande = fin(price) ? price * bandePct / 100 : NaN;
  var nSec = Math.max(1, Math.min(4, Math.round(fin(opts.nSec) ? opts.nSec : 2))), sec = opts.secondaires !== false;
  var rows = raw.split('\n').map(function (r) { return r.trim(); });
  var titres = raw.indexOf('#') >= 0, section = titres ? 'autre' : 'niveaux';

  /* Première passe : l’échéance seule, avant tout le reste, pour ne pas dépendre de l’ordre des sections. */
  var prefixe = '', source = '', todayUtc = NaN;
  if (typeof opts.today === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(opts.today)) { var td = opts.today.split('-'); todayUtc = Date.UTC(+td[0], +td[1] - 1, +td[2]); }
  rows.forEach(function (ligne) {
    if (prefixe !== '' || !ligne) return;
    if (ligne.toLowerCase().indexOf('horizon') >= 0) {
      var pr = ligne.split(ligne.indexOf(':') >= 0 ? ':' : '=');
      if (pr.length > 1) { prefixe = L.teteNumerique(pr[1]); if (prefixe) source = 'horizon'; }
    } else if (fin(todayUtc)) {
      var dch = ligne.split(',');
      if (dch.length > 3) {
        var dt = dch[0].trim().split('-');
        if (dt.length === 3 && dt.every(function (x) { return fin(L.toNumber(x)); })) {
          var j = Math.round((Date.UTC(+dt[0], +dt[1] - 1, +dt[2]) - todayUtc) / 864e5);
          if (j >= 0 && j <= 999) { prefixe = String(j); source = 'expiration'; }
        }
      }
    }
  });

  /* Seconde passe : les zones, puis le bloc CSV. Une ligne « horizon » rencontrée dans un contexte change l’échéance
     des niveaux qui suivent : deux exports collés à la suite gardent chacun la leur. */
  var cur = prefixe, csvPref = null, lv = [], ech = [], refus = [], csvK = [], csvW = [], iS = -1, iV = -1, horizons = [];
  rows.forEach(function (row) {
    var low = row.toLowerCase(), enteteCsv = low.indexOf('strike') >= 0 && row.indexOf(',') >= 0;
    if (row.charAt(0) === '#') {
      var l = sansAccent(low);
      section = /level|niveau/.test(l) ? 'niveaux' : /context/.test(l) ? 'contexte' : /data|donnee/.test(l) ? 'data' : 'autre';
      return;
    }
    if (enteteCsv || (row && section === 'data')) {
      if (enteteCsv) section = 'data';
      var ch = row.split(','), nc = ch.length;
      if (nc <= 1) return;
      if (low.indexOf('strike') >= 0) {
        iS = -1; iV = -1;
        ch.forEach(function (c, i) { var nom = c.trim().toLowerCase(); if (nom === 'strike') iS = i; if (iV < 0 && (nom.indexOf('net') >= 0 || nom.indexOf('gex') >= 0)) iV = i; });
        if (iV < 0) iV = nc - 1;
        if (csvPref === null) csvPref = cur;
        return;
      }
      if (iS >= 0 && iV >= 0 && nc > Math.max(iS, iV)) {
        var k = L.num(ch[iS]), w = L.num(ch[iV]);
        if (fin(k) && fin(w)) {
          /* Le poids d’un strike : somme des valeurs absolues de ses jambes. Un call et un put au même strike y
             concentrent tous deux du gamma, et leurs signes opposés ne doivent pas s’annuler. */
          var pos = -1; csvK.forEach(function (x, i) { if (Math.abs(x - k) < L.MINTICK) pos = i; });
          if (pos >= 0) csvW[pos] += Math.abs(w); else { csvK.push(k); csvW.push(Math.abs(w)); }
        }
      }
      return;
    }
    if (!row || section === 'autre') return;
    var corps = row.replace(/^-\s+/, '');   /* une puce « - » suivie d’une espace n’est pas un signe */
    var sep = corps.indexOf('=') >= 0 ? '=' : corps.indexOf(':') >= 0 ? ':' : corps.indexOf('|') >= 0 ? '|' : '';
    var pp = sep ? corps.split(sep) : [corps], gauche = pp[0].trim(), droite = pp.length > 1 ? pp[1].trim() : '';
    if (section === 'contexte') {
      if (gauche.toLowerCase().indexOf('horizon') >= 0) { var tn = L.teteNumerique(droite); if (tn) { cur = tn; horizons.push(tn); } }
      return;
    }
    var vG = L.num(gauche), vD = L.num(droite), v = NaN, tg = '';
    if (fin(vG)) { v = vG; tg = L.cleanTag(droite); } else if (fin(vD)) { v = vD; tg = L.cleanTag(gauche); }
    if (!fin(v)) return;
    if (lv.length >= L.MAXN) { refus.push({ ligne: row, v: v, raison: 'au-delà de vingt zones' }); return; }
    var ok = !fin(price) || Math.abs(v - price) <= bande || (fin(basis) && Math.abs(v + basis - price) <= bande);
    if (!ok) { refus.push({ ligne: row, v: v, raison: 'hors de la fenêtre de plausibilité' }); return; }
    var cd = L.codeDe(tg, cur), j2 = -1;
    lv.forEach(function (x, i) { if (Math.abs(x.v - v) < L.MINTICK) j2 = i; });
    if (j2 >= 0) { var anc = lv[j2].code; if (cd && anc.indexOf(cd) < 0) lv[j2].code = anc ? anc + '/' + cd : cd; }
    else { lv.push({ v: v, code: cd, tag: tg, src: 'robot' }); ech.push(v); }
  });

  /* L’échelle des zones collées, mesurée et non supposée. */
  var med = median(ech), ecS = fin(med) && fin(price) ? Math.abs(med - price) : NaN, ecA = fin(med) && fin(price) && fin(basis) ? Math.abs(med + basis - price) : NaN;
  var mode = opts.appliquer === 'toujours' || opts.appliquer === 'jamais' ? opts.appliquer : 'auto', app, decision;
  if (!fin(basis)) { app = false; decision = 'absente'; }
  else if (mode === 'toujours') { app = true; decision = 'forcee'; }
  else if (mode === 'jamais') { app = false; decision = 'refusee'; }
  else if (!fin(med)) { app = true; decision = 'auto'; }
  else if (!fin(price)) { app = false; decision = 'indecidable'; }
  else { app = ecA <= ecS; decision = 'auto'; }
  var baseApp = app ? basis : 0;

  /* Les secondaires se classent après la lecture entière (zones nommées déjà posées, donc exclues) et après que la base
     soit tranchée : « au-dessus du prix » n’a de sens qu’à échelles ramenées à la même. */
  var nCalc = 0;
  if (sec && csvK.length && fin(price)) {
    for (var cote = 0; cote < 2; cote++) {
      for (var rang = 1; rang <= nSec; rang++) {
        var best = NaN, bestW = -1;
        csvK.forEach(function (x, i) {
          var haut = x + baseApp > price, bon = cote === 0 ? haut : !haut;
          var pose = lv.some(function (e) { return Math.abs(e.v - x) < L.MINTICK; });
          if (bon && csvW[i] > bestW && !pose) { best = x; bestW = csvW[i]; }
        });
        if (fin(best) && lv.length < L.MAXN) { lv.push({ v: best, code: (csvPref || '') + (cote === 0 ? 'R' : 'S') + rang, tag: '', src: 'calcul', poids: bestW }); nCalc++; }
      }
    }
  }
  var niveaux = lv.map(function (x) { var nq = x.v + baseApp; return Object.assign({}, x, { nq: nq, dist: fin(price) ? nq - price : NaN }); });
  return {
    niveaux: niveaux, n: niveaux.length, nRobot: niveaux.length - nCalc, nCalc: nCalc, prefixe: prefixe, source: source, horizons: horizons,
    med: med, ecartSans: ecS, ecartAvec: ecA, appliquee: app, baseApp: baseApp, decision: decision, mode: mode,
    csv: csvK.length, refus: refus, bandePct: bandePct, titres: titres
  };
};

/* Demi-largeur d’une zone de gamma, en points : S·(exp(√(2 ln 2)·σ·√(jours/365)) − 1) — niveaux.largeur_gamma. */
L.DEMI = Math.sqrt(2 * Math.log(2));
L.halfWidth = function (S, sigma, jours) { if (!fin(S) || !fin(sigma) || !fin(jours) || S <= 0 || sigma <= 0 || jours <= 0) return NaN; return S * (Math.exp(L.DEMI * sigma * Math.sqrt(jours / 365)) - 1); };
/* Jours calendaires de la capture à l’échéance (16 h ET) : le jour même en 0DTE, le jour ouvré suivant en 1DTE. */
L.daysToExpiry = function (capture, dte) {
  if (!fin(capture)) return NaN;
  var p = parts(NY, capture), d = { y: p.y, mo: p.mo, d: p.d }, n = dte === '1' || dte === 1 ? 1 : 0, k = 0, guard = 0;
  while (n > 0 && guard++ < 10) { k++; var dd = L.addDays(p.y, p.mo, p.d, k); if (dd.wd >= 1 && dd.wd <= 5) { n--; d = dd; } }
  var exp = L.zonedToUtc(d.y, d.mo, d.d, 16, 0, NY);
  return (exp - capture) / 864e5;
};
/* Instant d’une capture saisie en heure de Paris (« HH:MM ») le jour de Paris donné. */
L.captureAt = function (dayKey, hhmm) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dayKey || '') || !/^\d{1,2}:\d{2}/.test(hhmm || '')) return NaN;
  var a = dayKey.split('-'), b = hhmm.split(':');
  return L.zonedToUtc(+a[0], +a[1], +a[2], +b[0], +b[1], PA);
};

/* ---------- Biais et journal ---------- */
L.CHECKS = ['structure', 'niveaux', 'regime'];
L.biasComplete = function (b) { return !!(b && (b.bias === 'long' || b.bias === 'both' || b.bias === 'short') && L.CHECKS.every(function (k) { return b.checks && b.checks[k]; })); };
L.biasToday = function (raw, today) { if (!raw || typeof raw !== 'object' || raw.date !== today) return { date: today, bias: null, checks: {} }; return { date: today, bias: raw.bias || null, checks: Object.assign({}, raw.checks || {}), at: raw.at }; };
/* Durées de tenue (minutes) des trades pris et clos, par instrument. */
L.holdTimes = function (rows, inst, defInst) {
  return (rows || []).filter(function (r) { return r && r.kind === 'pris' && fin(r.at) && fin(r.closedAt) && r.closedAt > r.at && (r.instrument || defInst) === inst; }).map(function (r) { return (r.closedAt - r.at) / 60000; });
};

/* =====================================================================
   2. Rendu
   ===================================================================== */
var CSS = [
  '.nq-stack{display:flex;flex-direction:column;gap:12px;min-width:0}',
  '.nq-leg{display:flex;flex-wrap:wrap;gap:6px 14px;font:500 11px/1.3 var(--f-mono);color:var(--soft)}',
  '.nq-leg span{display:inline-flex;align-items:center;gap:6px}',
  '.nq-leg i{width:12px;height:10px;border-radius:2px;border:1px solid var(--line-2);display:inline-block}',
  '.nq-lines{display:flex;flex-direction:column;gap:7px;margin:0;padding:0;list-style:none}',
  '.nq-lines li{font-size:13px;color:var(--soft);line-height:1.5;padding-left:14px;position:relative}',
  '.nq-lines li::before{content:"";position:absolute;left:0;top:.62em;width:6px;height:6px;border-radius:50%;background:var(--line-2)}',
  '.nq-lines li.on::before{background:var(--violet)}',
  '.nq-lines li b{color:var(--fg);font-weight:600}',
  '.nq-det{border:1px solid var(--line);border-radius:10px;background:var(--panel);padding:9px 12px;font-size:12.5px;color:var(--mute)}',
  '.nq-det summary{cursor:pointer;color:var(--soft);font:600 11.5px/1.4 var(--f-mono)}',
  '.nq-det ul{margin:8px 0 2px;padding-left:16px;display:flex;flex-direction:column;gap:4px}',
  '.nq-det code{font-family:var(--f-mono);color:var(--fg);word-break:break-all}',
  '.nq-notes{display:flex;flex-direction:column;gap:10px}',
  '.nq-notes p{margin:0;font-size:13.5px;color:var(--soft);line-height:1.55}',
  '.nq-notes p b{color:var(--fg);font-weight:600}',
  '.nq-in-btn{margin-right:4px;flex:none}',
  '.nq-code{font-weight:600;color:var(--hi)}',
  '.nq-calc{color:var(--mute)}',
  '.nq-lv{display:flex;flex-direction:column;gap:2px}',
  '.nq-lv b{font-weight:600}',
  '.nq-lv span{font-family:var(--f-sans);font-size:11px;color:var(--mute)}'
].join('');
function injectCss() { if (document.getElementById('nq-css')) return; var s = document.createElement('style'); s.id = 'nq-css'; s.textContent = CSS; document.head.appendChild(s); }
function typo(el) {
  if (!el || typeof document === 'undefined') return;
  var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, { acceptNode: function (n) { var p = n.parentNode; return p && /^(TEXTAREA|SCRIPT|STYLE|INPUT|OPTION|CODE)$/.test(p.nodeName) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; } }), n;
  while ((n = w.nextNode())) { var t = n.nodeValue, u = T.typo(t).replace(/nº /g, 'nº '); if (u !== t) n.nodeValue = u; }
}
var JOURS = ['dimanche', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi'];
function dmy(o) { return pad(o.d) + '/' + pad(o.mo) + '/' + o.y; }
function hFr(t, tz) { var p = parts(tz, t); return p.h + ' h ' + pad(p.m); }
function pts(v, nd) { return fin(v) ? F.num(v, nd == null ? 2 : nd) : '—'; }
function instOf(set) { return set && L.SPEC[set.instrument] ? set.instrument : 'MNQ'; }
function fld(label, node, hint, full) { return h('div', { class: 'fld' + (full ? ' full' : '') }, h('label', null, label), node, hint ? h('span', { class: 'hint' }, hint) : null); }
function lines(items) { return h('ul', { class: 'nq-lines' }, items.filter(Boolean).map(function (it) { return typeof it === 'string' ? h('li', null, it) : h('li', { class: it.on ? 'on' : null }, it.b ? h('b', null, it.b) : null, it.b ? ' ' : null, it.t); })); }
function getFrais(set) {
  var raw = T.store.get(K.frais, {}) || {}, inst = instOf(set), o = {};
  L.INSTS.forEach(function (i) { o[i] = fin(raw[i]) ? raw[i] : (i === inst && fin(set.commissionRT) ? set.commissionRT : L.REF.commission); o[i + 'Src'] = fin(raw[i]) ? 'saisie' : i === inst && fin(set.commissionRT) ? 'réglages' : 'référence ALP'; });
  o.slip = fin(raw.slip) && raw.slip >= 0 ? raw.slip : L.REF.slipTicks;
  return o;
}
function setFrais(patch) { T.store.set(K.frais, Object.assign({}, T.store.get(K.frais, {}) || {}, patch)); }

/* ---------- Onglet « Séance » ---------- */
var FILL = { asie: 'var(--line-2)', europe: 'var(--soft)', cash: 'var(--hi)', apres: 'var(--mute)', pause: 'url(#nqHatch)', ferme: 'var(--raise-2)' };
var NOM = { asie: 'Asie', europe: 'Europe', cash: 'Cash US', apres: 'Après-cash', pause: 'Pause Globex', ferme: 'Fermé' };
var COURT = { asie: 'Asie', europe: 'Europe', cash: 'Cash US', apres: '', pause: '', ferme: 'Fermé' };
function frieze(set) {
  return C.mount(null, function (W) {
    var fr = L.frieze(Date.now()), H = 96, ml = 6, mr = 6, ty = 24, th = 30, wy = ty + th + 8, wh = 12, g = '';
    var sx = function (mn) { return ml + Math.max(0, Math.min(1440, mn)) / 1440 * (W - ml - mr); }, X = T.esc;
    g += '<defs><pattern id="nqHatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="5" height="5" fill="var(--raise)"/><line x1="0" y1="0" x2="0" y2="5" stroke="var(--soft)" stroke-width="1.4"/></pattern>'
      + '<clipPath id="nqClip"><rect x="' + ml + '" y="' + ty + '" width="' + (W - ml - mr) + '" height="' + th + '" rx="6"/></clipPath></defs>';
    g += '<g clip-path="url(#nqClip)"><rect x="' + ml + '" y="' + ty + '" width="' + (W - ml - mr) + '" height="' + th + '" fill="var(--raise)"/>';
    var xs = [], info = [];
    fr.segs.forEach(function (s) {
      var x1 = sx(s.from), x2 = sx(s.to);
      g += '<rect x="' + x1.toFixed(1) + '" y="' + ty + '" width="' + Math.max(0.5, x2 - x1).toFixed(1) + '" height="' + th + '" fill="' + FILL[s.state] + '"/>';
      xs.push((x1 + x2) / 2); info.push(s);
    });
    fr.segs.forEach(function (s, i) { if (i > 0) g += '<line x1="' + sx(s.from).toFixed(1) + '" x2="' + sx(s.from).toFixed(1) + '" y1="' + ty + '" y2="' + (ty + th) + '" stroke="var(--bg)" stroke-width="1"/>'; });
    g += '</g>';
    fr.segs.forEach(function (s) {
      var lab = COURT[s.state], x1 = sx(s.from), x2 = sx(s.to);
      if (lab && x2 - x1 >= lab.length * 6.2 + 10) g += '<text class="axl" x="' + ((x1 + x2) / 2).toFixed(1) + '" y="' + (ty + th / 2 + 3.5) + '" text-anchor="middle" style="fill:' + (s.state === 'cash' || s.state === 'europe' ? 'var(--ink)' : 'var(--fg)') + '">' + X(lab) + '</text>';
    });
    /* La fenêtre de l’utilisateur, en violet. */
    g += '<rect x="' + ml + '" y="' + (wy + wh / 2 - 0.5) + '" width="' + (W - ml - mr) + '" height="1" fill="var(--line)"/>';
    var f = set.winFrom * 60, t2 = set.winTo * 60, wins = f === t2 ? [] : f < t2 ? [[f, t2]] : [[f, 1440], [0, t2]];
    wins.forEach(function (w) { var x1 = sx(w[0]), x2 = sx(w[1]); if (x2 - x1 < 0.5) return; g += '<rect x="' + x1.toFixed(1) + '" y="' + wy + '" width="' + (x2 - x1).toFixed(1) + '" height="' + wh + '" rx="3" fill="var(--violet)"/>'; if (x2 - x1 > 70) g += '<text x="' + ((x1 + x2) / 2).toFixed(1) + '" y="' + (wy + wh - 2.5) + '" text-anchor="middle" style="font:600 9.5px var(--f-mono)" fill="var(--ink)">ta fenêtre</text>'; });
    for (var hr = 0; hr <= 24; hr += 3) {
      var x = sx(hr * 60), an = hr === 0 ? 'start' : hr === 24 ? 'end' : 'middle';
      g += '<line x1="' + x + '" x2="' + x + '" y1="' + (wy + wh + 3) + '" y2="' + (wy + wh + 7) + '" stroke="var(--line-2)"/><text class="ax" x="' + x + '" y="' + (H - 4) + '" text-anchor="' + an + '">' + hr + (hr === 24 ? ' h' : '') + '</text>';
    }
    var nx = sx(fr.nowMin), lab2 = L.hhmm(Date.now(), PA), an2 = nx < 30 ? 'start' : nx > W - 30 ? 'end' : 'middle';
    g += '<line x1="' + nx.toFixed(1) + '" x2="' + nx.toFixed(1) + '" y1="' + (ty - 5) + '" y2="' + (wy + wh + 3) + '" stroke="var(--hi)" stroke-width="1.5"/><circle cx="' + nx.toFixed(1) + '" cy="' + (ty - 5) + '" r="3" fill="var(--hi)"/>';
    g += '<text class="axl" x="' + (an2 === 'start' ? nx - 3 : an2 === 'end' ? nx + 3 : nx).toFixed(1) + '" y="' + (ty - 11) + '" text-anchor="' + an2 + '" style="fill:var(--hi)">maintenant ' + lab2 + '</text>';
    return {
      svg: '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '" role="img" aria-label="Frise des séances du jour en heure de Paris">' + g + '</svg>',
      hover: { xs: xs, html: function (i) { var s = info[i], a = fr.start + s.from * 60000, b = fr.start + s.to * 60000; return '<b>' + X(NOM[s.state]) + '</b><br>Paris ' + L.fmtHour(s.from / 60) + '–' + L.fmtHour(s.to / 60) + '<br>New York ' + L.hhmm(a, NY) + '–' + L.hhmm(b, NY); } }
    };
  });
}
function legend() {
  var it = [['asie', 'background:var(--line-2)'], ['europe', 'background:var(--soft)'], ['cash', 'background:var(--hi)'], ['apres', 'background:var(--mute)'], ['pause', 'background:var(--hatch),var(--raise)'], ['ferme', 'background:var(--raise-2)']];
  return h('div', { class: 'nq-leg' }, it.map(function (x) { return h('span', null, h('i', { style: x[1] }), NOM[x[0]]); }), h('span', null, h('i', { style: 'background:var(--violet);border-color:var(--violet)' }), 'Ta fenêtre'));
}
function renderSeance(root, ctx) {
  var set = ctx.settings, wl = (Number.isInteger(set.winFrom) && Number.isInteger(set.winTo)) ? pad(set.winFrom) + '–' + pad(set.winTo) + ' h' : L.fmtHour(set.winFrom) + '–' + L.fmtHour(set.winTo);
  var s1 = U.section('Maintenant', 'mis à jour chaque seconde');
  var kp = U.kpis([
    { label: 'Paris', value: '—', hint: '—' }, { label: 'New York', value: '—', hint: '—' },
    { label: 'Globex', value: '—', hint: '—' }, { label: 'Cash US', value: '—', hint: '—' },
    { label: 'Fenêtre ' + wl, value: '—', hint: '—' }, { label: 'Écart Paris – NY', value: '—', hint: '—' }
  ], 3);
  s1.appendChild(kp); root.appendChild(s1);
  var tiles = kp.querySelectorAll('.kpi'), V = [], Hn = [];
  Array.prototype.forEach.call(tiles, function (el) { V.push(el.querySelector('.v')); Hn.push(el.querySelector('.h')); });
  function tone(i, acc) { tiles[i].classList.toggle('acc', !!acc); }
  function tick() {
    var now = Date.now(), pp = parts(PA, now), pn = parts(NY, now), e = L.etat(now), w = L.windowCountdown(pp, set.winFrom, set.winTo), gp = L.gap(now), nx = L.nextGapChange(now);
    V[0].textContent = L.hhmmss(now, PA); Hn[0].textContent = JOURS[pp.wd] + ' ' + pad(pp.d) + '/' + pad(pp.mo);
    V[1].textContent = L.hhmmss(now, NY); Hn[1].textContent = JOURS[pn.wd] + ' ' + pad(pn.d) + '/' + pad(pn.mo);
    V[2].textContent = e.state === 'pause' ? 'pause' : e.globex ? 'ouvert' : 'fermé'; tone(2, e.globex);
    Hn[2].textContent = e.nextGlobex ? (e.globex ? (e.nextGlobex.k === 'weekClose' ? 'week-end dans ' : 'pause dans ') : 'rouvre dans ') + L.fmtCount(e.nextGlobex.t - now) : '—';
    V[3].textContent = e.cash ? 'ouvert' : 'fermé'; tone(3, e.cash);
    Hn[3].textContent = e.nextCash ? (e.cash ? 'clôture dans ' : 'ouverture dans ') + L.fmtCount(e.nextCash.t - now) : '—';
    V[4].textContent = !fin(w.min) ? 'non réglée' : w.open ? 'ouverte' : 'fermée'; tone(4, w.open);
    Hn[4].textContent = !fin(w.min) ? 'règle-la dans tes réglages' : (w.open ? 'ferme dans ' : 'ouvre dans ') + L.fmtCount(w.min * 60000);
    V[5].textContent = F.num(gp, 0) + ' h'; Hn[5].textContent = nx ? 'passe à ' + F.num(nx.gap, 0) + ' h le ' + pad(nx.d) + '/' + pad(nx.mo) : '—';
    typo(kp);
  }
  tick();

  var p = parts(PA, Date.now()), rp = L.reperes(p.y, p.mo, p.d);
  var s2 = U.section('La journée, *heure de Paris*', JOURS[p.wd] + ' ' + dmy(p));
  var fz = frieze(set);
  s2.appendChild(U.card({ body: [fz, legend()] }));
  s2.appendChild(U.note('Touche la frise pour lire chaque séance en heure de Paris et de New York. Le repère blanc est l’heure présente ; la bande violette est ta fenêtre (' + L.fmtHour(set.winFrom) + '–' + L.fmtHour(set.winTo) + ', heure de Paris, réglable dans les réglages).'));
  root.appendChild(s2);

  var s3 = U.section('Les repères *du jour*', 'calculés depuis New York');
  var rows = [
    { k: 'Globex rouvre', pa: L.hhmm(rp.reouverture, PA), ny: L.hhmm(rp.reouverture, NY) },
    { k: 'Londres ouvre', pa: L.hhmm(rp.londres, PA), ny: L.hhmm(rp.londres, NY) },
    { k: 'Cash US ouvre', pa: L.hhmm(rp.cashOpen, PA), ny: L.hhmm(rp.cashOpen, NY) },
    { k: 'Cash US ferme', pa: L.hhmm(rp.cashClose, PA), ny: L.hhmm(rp.cashClose, NY) },
    { k: 'Pause Globex', pa: L.hhmm(rp.pause, PA), ny: L.hhmm(rp.pause, NY) }
  ];
  s3.appendChild(U.table({ cols: [{ k: 'k', label: 'Repère' }, { k: 'pa', label: 'Paris', align: 'r' }, { k: 'ny', label: 'New York', align: 'r' }], rows: rows }));
  s3.appendChild(U.note((rp.ouvre ? '' : 'Pas de séance cash aujourd’hui : les heures ci-dessus sont celles d’un jour ouvré. ') + 'Globex rouvre la veille au soir à New York (18 h) ; la pause dure une heure. Rien n’est écrit en dur : 9 h 30 à New York est converti chaque jour en heure de Paris, et l’écart passe de six à cinq heures pendant les semaines où l’Europe et les États-Unis ne changent pas d’heure ensemble. Les jours fériés américains et les séances écourtées du CME ne sont pas pris en compte : vérifie le calendrier du CME ces jours-là.'));
  s3.appendChild(U.note('Conventions : l’Asie court de la réouverture Globex (18 h à New York) à l’ouverture de Londres (8 h à Londres) ; l’Europe, de Londres à l’ouverture cash de New York. Horaires Globex : spécifications CME Group.'));
  root.appendChild(s3);
  typo(s2); typo(s3);

  var n = 0, iv = setInterval(function () {
    if (!kp.isConnected) return;
    tick(); n++;
    if (n % 30 === 0 && fz.__draw) fz.__draw();
  }, 1000);
  return function () { clearInterval(iv); };
}

/* ---------- Onglet « GEX » ---------- */
var GEX0 = { text: '', price: null, base: null, appliquer: 'auto', dte: '0', capture: '', captureDay: '', vol: null, bande: 3, savedAt: 0, date: '' };
function getGex() { return Object.assign({}, GEX0, T.store.get(K.gex, {}) || {}); }
function nyToday() { var p = parts(NY, Date.now()); return p.y + '-' + pad(p.mo) + '-' + pad(p.d); }
function renderGex(root, ctx) {
  var st = getGex(), today = T.day.key();
  if (!st.captureDay) st.captureDay = today;
  function save(patch) { Object.assign(st, patch, { savedAt: Date.now(), date: today }); T.store.set(K.gex, st); }

  /* --- Le formulaire : jamais redessiné pendant la frappe. --- */
  var s1 = U.section('L’export *du robot*', 'collé tel quel');
  var segBox = h('div', { style: 'grid-column:1/-1;min-width:0' }), dteBox = h('div', { style: 'grid-column:1/-1;min-width:0' });
  function paintSegs() {
    T.clear(segBox); var noBase = !fin(st.base);
    segBox.appendChild(fld('Appliquer la base', U.seg({ aria: 'Appliquer la base', value: noBase ? null : st.appliquer, onChange: function (v) { save({ appliquer: v }); paintSegs(); analyse(); }, options: [{ v: 'auto', label: 'Auto', disabled: noBase }, { v: 'toujours', label: 'Toujours', disabled: noBase }, { v: 'jamais', label: 'Jamais', disabled: noBase }] }),
      noBase ? 'Sans base saisie, les niveaux restent tels que le robot les publie.' : 'Auto compare la médiane des niveaux au prix, avec et sans la base, et retient le plus proche.', true));
    T.clear(dteBox);
    dteBox.appendChild(fld('Échéance des options', U.seg({ aria: 'Échéance', value: st.dte, onChange: function (v) { save({ dte: v }); paintSegs(); analyse(); }, options: [{ v: '0', label: '0DTE' }, { v: '1', label: '1DTE' }] }), st.dte === '1' ? 'Provisoires jusqu’à la mise à jour de l’intérêt ouvert.' : 'Les options qui expirent ce soir.', true));
  }
  paintSegs();
  var fPrix = U.field({ label: 'Prix NQ actuel', unit: 'pt', value: st.price, allowEmpty: true, min: 0, onChange: function (v) { save({ price: v }); analyse(); } });
  var fBase = U.field({ label: 'Base NQ − NDX', unit: 'pt', value: st.base, allowEmpty: true, hint: 'mesurée au même instant, jamais devinée', onChange: function (v) { save({ base: v }); paintSegs(); analyse(); } });
  var fCap = U.field({ type: 'time', label: 'Heure de capture (Paris)', value: st.capture, full: true, onChange: function (v) { save({ capture: v, captureDay: today }); analyse(); } });
  var capIn = fCap.querySelector('input');
  fCap.querySelector('.in').appendChild(U.button({ label: 'maintenant', small: true, kind: 'ghost', onClick: function () { var v = L.hhmm(Date.now(), PA); capIn.value = v; save({ capture: v, captureDay: today }); analyse(); } }));
  fCap.querySelector('.in .btn').classList.add('nq-in-btn');
  var fVol = U.field({ label: 'Volatilité implicite', unit: '%', value: st.vol, allowEmpty: true, min: 0, max: 300, hint: 'facultative : chiffre la largeur d’une zone', onChange: function (v) { save({ vol: v }); analyse(); } });
  var fBande = U.field({ label: 'Fenêtre de plausibilité', unit: '%', value: st.bande, min: 0.05, max: 50, hint: 'écarte millésimes et comptes de lignes', onChange: function (v) { save({ bande: v }); analyse(); } });
  var fTxt = U.field({ type: 'textarea', label: 'Export collé', full: true, value: st.text, placeholder: '## Context\n- **horizon:** 0 dte\n## Levels\n- **call wall:** …\n- **flip:** …', onChange: function (v) { save({ text: v }); analyse(); } });
  var ta = fTxt.querySelector('textarea'); ta.style.minHeight = '150px'; ta.style.fontFamily = 'var(--f-mono)'; ta.style.fontSize = '13px';
  var deb; ta.addEventListener('input', function () { clearTimeout(deb); deb = setTimeout(function () { st.text = ta.value; analyse(); }, 350); });
  var form = h('div', { class: 'fields' }, fPrix, fBase, segBox, dteBox, fCap, fVol, fBande, fTxt);
  var acts = h('div', { class: 'row' },
    U.button({ label: 'Analyser et enregistrer', kind: 'pri', onClick: function () { save({ text: ta.value }); analyse(); T.toast('Niveaux enregistrés'); } }),
    U.button({ label: 'Effacer l’export', kind: 'ghost', onClick: function () { ta.value = ''; save({ text: '' }); analyse(); } }));
  s1.appendChild(U.card({ body: [form, acts] }));
  s1.appendChild(U.note('Formats lus : la liste nue (« 29250 = CR », « gamma flip : 29280 ») ou l’export markdown entier — en-tête, niveaux, bloc CSV. Le préfixe d’échéance se lit dans la ligne « horizon » ; R1, R2, S1 et S2 sont calculés à partir du bloc CSV (portage de l’indicateur alp0-gex du dépôt).'));
  root.appendChild(s1);

  /* --- L’analyse : redessinée à chaque changement. --- */
  var s2 = U.section('Les *niveaux*', ''), out = h('div', { class: 'nq-stack' }); s2.appendChild(out); root.appendChild(s2);
  var s3 = U.section('Ce qu’un niveau gamma *n’est pas*', 'ALP nº 3, partie XIX'), notes = h('div'); s3.appendChild(notes); root.appendChild(s3);
  var s4 = U.section('La règle *du soir*', 'une fois par séance'), soir = h('div'); s4.appendChild(soir); root.appendChild(s4);
  var s5 = U.section('Le biais *du jour*', ''), biasBox = h('div', { class: 'nq-stack' }); s5.appendChild(biasBox); root.appendChild(s5);

  function analyse() {
    var meta = s2.querySelector('.sh span');
    T.clear(out);
    var capT = L.captureAt(st.captureDay || today, st.capture), jours = L.daysToExpiry(fin(capT) ? capT : Date.now(), st.dte);
    var sig = fin(st.vol) && st.vol > 0 ? st.vol / 100 : NaN, half = L.halfWidth(st.price, sig, jours);
    if (!st.text || !st.text.trim()) {
      if (meta) meta.textContent = 'rien de collé';
      out.appendChild(U.empty({ title: 'Colle l’export du robot', text: 'Copie sa réponse entière depuis Discord et colle-la au-dessus, sans la nettoyer. Saisis le prix NQ du moment et, si tu l’as, la base NQ − NDX lue sur ton graphique. Aucun niveau n’est jamais inventé ici.' }));
    } else {
      var r = L.parseGex(st.text, st.price, st.base, { bandePct: st.bande, appliquer: st.appliquer, today: nyToday() });
      if (meta) meta.textContent = r.n + ' zone' + (r.n > 1 ? 's' : '') + (fin(st.base) ? ' · base ' + (r.appliquee ? 'appliquée' : 'non appliquée') : ' · sans base');
      var info = [];
      info.push({ b: r.n + ' zone' + (r.n > 1 ? 's' : '') + ' lue' + (r.n > 1 ? 's' : '') + '.', t: r.nRobot + ' reportée' + (r.nRobot > 1 ? 's' : '') + ' du robot' + (r.nCalc ? ', ' + r.nCalc + ' calculée' + (r.nCalc > 1 ? 's' : '') + ' (R/S) à partir des ' + r.csv + ' strikes du bloc CSV.' : r.csv ? ', aucune R/S calculable.' : '.'), on: r.n > 0 });
      info.push(r.prefixe ? { b: 'Échéance lue : ' + r.prefixe + ' DTE', t: '(' + (r.source === 'horizon' ? 'ligne « horizon »' : 'colonne d’expiration') + ').' + (r.prefixe !== st.dte && r.prefixe.length < 3 && r.horizons.length < 2 ? ' Tu as déclaré ' + st.dte + 'DTE : vérifie lequel est juste.' : ''), on: true } : { b: 'Aucune échéance lue.', t: 'Les codes restent sans préfixe.' });
      if (!fin(st.price)) info.push({ b: 'Prix NQ non saisi.', t: 'Sans lui, pas de fenêtre de plausibilité, pas d’échelle mesurée, pas de R/S.' });
      if (!fin(st.base)) info.push({ b: 'Base non saisie.', t: 'Niveaux affichés tels que le robot les publie : s’il publie des strikes NDX, ils sont sur l’échelle de l’indice, pas sur celle du NQ.' });
      else if (fin(r.ecartSans)) info.push({ b: 'Échelle mesurée.', t: 'Médiane des niveaux collés ' + pts(r.med) + ' ; écart au prix ' + pts(r.ecartSans, 1) + ' pt sans la base, ' + pts(r.ecartAvec, 1) + ' pt avec. Base ' + (r.appliquee ? 'appliquée' : 'non appliquée') + ({ auto: ' (choix automatique).', forcee: ' (forcée).', refusee: ' (refusée).' }[r.decision] || '.'), on: true });
      else info.push({ b: 'Base ' + (r.appliquee ? 'appliquée.' : 'non appliquée.'), t: r.decision === 'indecidable' ? 'Saisis le prix pour que le choix automatique se mesure.' : '' });
      if (fin(half)) info.push({ b: 'Zone de chaque niveau : ± ' + F.num(half, 1) + ' pt', t: '(σ = ' + F.num(st.vol, 1) + ' %, ' + F.num(jours * 24, 1) + ' h avant l’échéance ; partie XIX).', on: true });
      if (r.refus.length) info.push({ b: r.refus.length + ' nombre' + (r.refus.length > 1 ? 's' : '') + ' écarté' + (r.refus.length > 1 ? 's' : '') + '.', t: 'Détail plus bas.' });
      var hvl = r.niveaux.filter(function (x) { return /HVL/.test(x.code); })[0];
      if (hvl && fin(st.price)) info.push({ b: 'Régime selon le robot :', t: 'prix ' + pts(Math.abs(st.price - hvl.nq), 1) + ' pt ' + (st.price >= hvl.nq ? 'au-dessus' : 'au-dessous') + ' du HVL collé. Il règle la taille et la durée attendues, pas le sens.' });
      out.appendChild(U.card({ body: lines(info) }));
      if (r.n) {
        var lad = r.niveaux.map(function (x) { var c = x.code || '·'; return { price: x.nq, label: c.length > 9 ? c.slice(0, 8) + '…' : c, kind: x.src === 'calcul' ? 'mute' : null, dash: x.src === 'calcul' || /HVL/.test(x.code) }; });
        out.appendChild(U.card({ title: 'Échelle des niveaux', meta: fin(st.price) ? 'prix NQ en violet' : 'prix non saisi', body: [C.ladder({ levels: lad, price: st.price, height: Math.max(260, lad.length * 30 + 24), fmt: function (v) { return F.num(v, 2); } }),
          U.note('Trait plein : niveau reporté du robot. Pointillé : HVL, ou R/S calculé depuis le CSV (gris).' + (fin(st.base) && r.appliquee ? ' Niveaux portés sur le NQ (base ' + pts(st.base) + ' pt ajoutée).' : ''))] }));
        var sorted = r.niveaux.slice().sort(function (a, b) { return b.nq - a.nq; }), cols = [
          { k: 'code', label: 'Niveau', fmt: function (v, row) { return h('div', { class: 'nq-lv' }, h('b', { class: row.src === 'calcul' ? 'nq-calc' : 'nq-code' }, v || '—'), h('span', null, L.nomDe(row.code, row.src))); } }];
        if (r.appliquee) cols.push({ k: 'v', label: 'Collé', align: 'r', fmt: function (v) { return pts(v); } });
        cols.push({ k: 'nq', label: r.appliquee ? 'Sur NQ' : 'Prix', align: 'r', fmt: function (v) { return pts(v); } });
        cols.push({ k: 'dist', label: 'Écart', align: 'r', fmt: function (v) { return fin(v) ? F.num(v, 2, null, true) : '—'; } });
        out.appendChild(U.table({ cols: cols, rows: sorted, rowClass: function (row) { return row.src === 'calcul' ? 'neg' : null; } }));
      }
      if (r.refus.length) out.appendChild(h('details', { class: 'nq-det' }, h('summary', null, r.refus.length + ' nombre' + (r.refus.length > 1 ? 's' : '') + ' écarté' + (r.refus.length > 1 ? 's' : '') + ' (fenêtre ± ' + F.num(r.bandePct, 2) + ' %)'),
        h('ul', null, r.refus.slice(0, 30).map(function (x) { return h('li', null, h('code', null, x.ligne), ' — ' + x.raison); }))));
    }
    /* Les notes de la partie XIX, avec la largeur chiffrée quand prix et volatilité sont saisis. */
    T.clear(notes);
    var w1 = 'La courbure d’une option tombe à la moitié de son sommet à √(2 ln 2)·σ√T du strike, soit 1,177 σ√T. À σ = 25 %, sur un indice à 6 000, cette demi-largeur vaut 26,7 points à deux heures de l’échéance et 93 points à un jour.';
    var w2 = fin(half) ? ' Avec ton prix (' + pts(st.price, 0) + ') et σ = ' + F.num(st.vol, 1) + ' %, à ' + F.num(jours * 24, 1) + ' h de l’échéance : ± ' + F.num(half, 1) + ' pt autour de chaque niveau.' : ' Saisis le prix et la volatilité implicite pour chiffrer la tienne.';
    notes.appendChild(h('div', { class: 'nq-notes' },
      h('p', null, h('b', null, 'Un niveau est une zone. '), w1 + w2),
      h('p', null, h('b', null, 'Le HVL n’est pas un prix. '), 'L’intérêt ouvert ne porte aucun signe, et la reconstruction suppose le teneur long les calls et court les puts à tous les strikes. À signe inconnu, la bascule se promène sur 1 219 points — 135 fois le stop élargi du document — et dans 47,9 % des tirages elle n’existe pas du tout.'),
      h('p', null, h('b', null, 'Le gamma règle la taille et la durée, pas le sens. '), 'Sur les cinq affirmations examinées, deux déplacent l’horloge, une le risque, deux rien, et aucune ne donne le sens. Un niveau ne dit pas où le prix ira : il dit où le mouvement risque d’être plus ample ou plus lent.')));
    notes.appendChild(U.note('Source : ALP nº 3, partie XIX (largeur d’un niveau, table 81 pour la bascule). Les niveaux du robot ne sont pas vérifiés ici : ce desk les reporte, il ne les mesure pas.'));

    /* La règle du soir. */
    T.clear(soir);
    var p = parts(PA, Date.now()), rp = L.reperes(p.y, p.mo, p.d), close = rp.cashClose, li = [];
    li.push({ b: 'Une fois, avant ' + hFr(close, PA) + ' (Paris).', t: 'C’est la clôture cash de New York aujourd’hui : l’indice NDX cote encore, la base NQ − NDX se mesure au même instant.', on: true });
    if (!st.capture) li.push({ b: 'Heure de capture non saisie.', t: 'Note-la : un niveau sans heure ne se relit pas.' });
    else if (fin(capT)) li.push(capT < close && capT >= rp.cashOpen ? { b: 'Capture à ' + st.capture.replace(':', ' h ') + ' :', t: 'cash ouvert, base mesurable.', on: true } : { b: 'Capture à ' + st.capture.replace(':', ' h ') + ' :', t: 'cash fermé, la base n’était pas mesurable au même instant. Reprends celle de la clôture.' });
    li.push(st.dte === '1' ? { b: 'Niveaux 1DTE : provisoires.', t: 'Ils s’appuient sur l’intérêt ouvert de la veille, et restent provisoires jusqu’à sa mise à jour.' } : { b: 'Niveaux 0DTE :', t: 'ceux du jour. On ne les repose pas en séance.' });
    if (st.savedAt) li.push({ b: 'Enregistrés', t: (st.date === today ? 'aujourd’hui à ' + L.hhmm(st.savedAt, PA) : 'le ' + F.dateLong(st.savedAt) + ' — pas aujourd’hui') + '.', on: st.date === today });
    soir.appendChild(U.card({ body: lines(li) }));
    paintBias();
    typo(out); typo(notes); typo(soir);
  }

  function paintBias() {
    T.clear(biasBox);
    var b = L.biasToday(T.store.get(K.bias, null), today), meta = s5.querySelector('.sh span');
    if (meta) meta.textContent = JOURS[parts(PA, Date.now()).wd] + ' ' + F.dateLong(Date.now());
    function put(patch) {
      var nb = Object.assign({}, b, patch, { date: today, at: Date.now() }); T.store.set(K.bias, nb);
      if (L.biasComplete(nb) && !T.day.get().done.biais) { T.day.mark('biais'); T.toast('Étape « Biais et niveaux » faite'); }
      paintBias();
    }
    biasBox.appendChild(U.seg({ aria: 'Biais du jour', value: b.bias, onChange: function (v) { put({ bias: v }); }, options: [{ v: 'long', label: 'Acheteur' }, { v: 'both', label: 'Neutre' }, { v: 'short', label: 'Vendeur' }] }));
    var gx = getGex(), posed = gx.date === today && gx.text && gx.text.trim();
    biasBox.appendChild(U.checklist({ checked: b.checks, onToggle: function (id, on) { var c = Object.assign({}, b.checks); c[id] = on; put({ checks: c }); }, items: [
      { id: 'structure', t: 'Structure lue', s: 'Plus haut et plus bas de la veille, sens des derniers balancements : écrits avant l’ouverture.' },
      { id: 'niveaux', t: 'Niveaux posés', s: posed ? 'Export enregistré aujourd’hui à ' + L.hhmm(gx.savedAt, PA) + '.' : 'Aucun export enregistré aujourd’hui.' },
      { id: 'regime', t: 'Régime lu', s: 'Prix contre le HVL du robot : il règle la taille et la durée, pas le sens.' }] }));
    var done = L.biasComplete(b);
    biasBox.appendChild(U.note(done ? 'Biais déclaré et liste complète : l’étape « Biais et niveaux » de la carte de séance est faite. Le desk Micro le relit.' : 'Choisis un biais et coche les trois points : l’étape « Biais et niveaux » de la carte de séance se marque alors seule.', !done));
    typo(biasBox);
  }
  analyse();
  typo(s1);
  var un = T.store.on(K.bias, function () { if (biasBox.isConnected) paintBias(); });
  return function () { clearTimeout(deb); un(); };
}

/* ---------- Onglet « Contrat » ---------- */
function renderContrat(root, ctx) {
  var set = ctx.settings, now = Date.now(), p = parts(NY, now), fc = L.frontContract(p.y, p.mo, p.d), pa = parts(PA, now), rp = L.reperes(pa.y, pa.mo, pa.d);
  var s1 = U.section('NQ et *MNQ*', 'spécifications CME');
  var rows = [
    { k: 'Contrat', a: 'E-mini', b: 'Micro E-mini' },
    { k: 'Valeur du point', a: F.usd(20, 0), b: F.usd(2, 0) },
    { k: 'Tick de 0,25 pt', a: F.usd(L.tickValue('NQ'), 2), b: F.usd(L.tickValue('MNQ'), 2) },
    { k: 'Échéance en cours', a: fc ? 'NQ' + fc.sym : '—', b: fc ? 'MNQ' + fc.sym : '—' },
    { k: 'Équivalence', a: '1 NQ', b: '10 MNQ' }
  ];
  s1.appendChild(U.table({ cols: [{ k: 'k', label: 'Nasdaq-100', cls: 'm' }, { k: 'a', label: 'NQ', align: 'r' }, { k: 'b', label: 'MNQ', align: 'r' }], rows: rows }));
  s1.appendChild(U.card({ title: 'Commun aux deux', meta: 'heures de New York', body: lines([
    { b: 'Mois cotés :', t: 'mars (H), juin (M), septembre (U), décembre (Z).' },
    { b: 'Dernier jour :', t: 'le troisième vendredi du mois, 9 h 30 ET' + (fc ? ' — pour ' + fc.sym + ', le ' + dmy(fc.expiry) + '.' : '.') },
    { b: 'Globex :', t: 'du dimanche 18 h au vendredi 17 h, pause quotidienne de 17 h à 18 h.' },
    { b: 'Aujourd’hui, heure de Paris :', t: 'cash ' + L.hhmm(rp.cashOpen, PA) + '–' + L.hhmm(rp.cashClose, PA) + ', pause Globex ' + L.hhmm(rp.pause, PA) + '–' + L.hhmm(rp.reprise, PA) + '.', on: true }
  ]) }));
  s1.appendChild(U.note('Source : spécifications CME Group (Nasdaq-100 E-mini et Micro E-mini). ' + (fc ? 'Roll d’usage : le jeudi qui précède l’échéance de huit jours, soit le ' + dmy(fc.roll) + ' — à vérifier sur le calendrier du CME.' : '')));
  root.appendChild(s1);

  var s2 = U.section('La friction, puis *la case*', 'ALP nº 3, partie XII'), box = h('div', { class: 'nq-stack' });
  var fr = getFrais(set);
  var flds = U.fields([
    { label: 'Commission A/R NQ', unit: '$', value: fr.NQ, min: 0, hint: fr.NQSrc, onChange: function (v) { setFrais({ NQ: v }); paint(); } },
    { label: 'Commission A/R MNQ', unit: '$', value: fr.MNQ, min: 0, hint: fr.MNQSrc, onChange: function (v) { setFrais({ MNQ: v }); paint(); } },
    { label: 'Glissement', unit: 'tick', value: fr.slip, min: 0, max: 20, hint: 'payé à la sortie, en ticks', onChange: function (v) { setFrais({ slip: v }); paint(); } }
  ]);
  s2.appendChild(U.card({ body: [flds, box] }));
  s2.appendChild(U.note('c = commission aller-retour ÷ valeur du point + glissement × 0,25 pt. Case = 60 × c ÷ 3,2 minutes, où 3,2 pt/h est le plafond du domaine de dérive plausible. Une position tenue moins longtemps que sa case ne peut pas être rentable, quelle que soit la qualité du signal : la friction n’a pas eu le temps d’être couverte. Référence du document : 4 $ de commission et un tick de sortie, soit 0,45 pt et 8,4 min sur NQ, 2,25 pt et 42,2 min sur MNQ (table 24).'));
  root.appendChild(s2);

  var s3 = U.section('Tes positions *contre la case*', 'le contrôle du soir'), jbox = h('div', { class: 'nq-stack' });
  s3.appendChild(jbox); root.appendChild(s3);

  function paint() {
    var f = getFrais(set); T.clear(box);
    var c = {}, cs = {};
    L.INSTS.forEach(function (i) { c[i] = L.friction({ commission: f[i], pointValue: L.SPEC[i].pv, tick: 0.25, slipTicks: f.slip }); cs[i] = L.caseMin(c[i]); });
    box.appendChild(U.kpis([
      { label: 'Case MNQ', value: F.num(cs.MNQ, 1), unit: 'min', hint: 'c = ' + pts(c.MNQ) + ' pt', tone: instOf(set) === 'MNQ' ? 'acc' : null },
      { label: 'Case NQ', value: F.num(cs.NQ, 1), unit: 'min', hint: 'c = ' + pts(c.NQ) + ' pt', tone: instOf(set) === 'NQ' ? 'acc' : null }
    ]));
    box.appendChild(U.table({ cols: [{ k: 'k', label: '', cls: 'm' }, { k: 'nq', label: 'NQ', align: 'r' }, { k: 'mnq', label: 'MNQ', align: 'r' }], rows: [
      { k: 'Commission', nq: F.usd(f.NQ, 2), mnq: F.usd(f.MNQ, 2) },
      { k: 'Glissement', nq: F.usd(f.slip * L.tickValue('NQ'), 2), mnq: F.usd(f.slip * L.tickValue('MNQ'), 2) },
      { k: 'Friction c', nq: pts(c.NQ) + ' pt', mnq: pts(c.MNQ) + ' pt' },
      { k: 'Case', nq: F.num(cs.NQ, 1) + ' min', mnq: F.num(cs.MNQ, 1) + ' min' },
      { k: 'Réf. ALP : c', nq: pts(L.refFriction('NQ')) + ' pt', mnq: pts(L.refFriction('MNQ')) + ' pt' },
      { k: 'Réf. ALP : case', nq: F.num(L.caseMin(L.refFriction('NQ')), 1) + ' min', mnq: F.num(L.caseMin(L.refFriction('MNQ')), 1) + ' min' }
    ] }));
    T.clear(jbox);
    var rows = T.journal.list(), any = false;
    L.INSTS.forEach(function (i) {
      var d = L.holdTimes(rows, i, instOf(set)); if (!d.length) return; any = true;
      var med = T.stats.quantile(T.stats.sorted(d), 0.5), under = d.filter(function (x) { return x < cs[i]; }).length;
      jbox.appendChild(U.card({ title: i + ' · ' + d.length + ' position' + (d.length > 1 ? 's' : '') + ' close' + (d.length > 1 ? 's' : ''), meta: 'case ' + F.num(cs[i], 1) + ' min', body: [
        U.kpis([{ label: 'Tenue médiane', value: F.dur(med), tone: med < cs[i] ? 'neg' : 'acc', hint: med < cs[i] ? 'sous la case' : 'au-dessus de la case' }, { label: 'Sous la case', value: F.pct(under / d.length, 0), hint: under + ' sur ' + d.length }]),
        C.hist({ values: d, refs: [{ x: cs[i], tone: 'violet' }], fmt: function (v) { return F.num(v, 0); }, min: 0, height: 150 }),
        U.note('Durée de tenue en minutes, de la décision à la clôture ; le trait violet est la case. Sous la case, le test réfute ; au-dessus, il ne confirme rien : il rend seulement le reste du protocole digne d’être payé.')] }));
    });
    if (!any) jbox.appendChild(U.empty({ title: 'Aucune position close au journal', text: 'Le contrôle compare la durée de tes positions à la case, sans une donnée de prix. Il demande des trades pris et clos, avec leur heure de clôture.', action: U.button({ label: 'Ouvrir le journal', small: true, onClick: function () { T.nav.go('journal'); } }) }));
    typo(box); typo(jbox);
  }
  paint(); typo(s1); typo(s2);
  var un = T.journal.on(function () { if (jbox.isConnected) paint(); });
  return function () { un(); };
}

/* ---------- Onglet « Taille » ---------- */
function renderTaille(root, ctx) {
  var set = ctx.settings, raw = T.store.get(K.taille, {}) || {};
  var st = { risk: fin(raw.risk) ? raw.risk : set.riskPerTrade, stop: fin(raw.stop) ? raw.stop : 20, inst: L.SPEC[raw.inst] ? raw.inst : instOf(set) };
  function save() { T.store.set(K.taille, st); }
  var s1 = U.section('Le *calcul*', 'le stop d’abord, la taille ensuite'), instBox = h('div', { class: 'fld full' }), res = h('div', { class: 'nq-stack' });
  function paintInst() { T.clear(instBox); instBox.appendChild(h('label', null, 'Instrument')); instBox.appendChild(U.seg({ aria: 'Instrument', value: st.inst, onChange: function (v) { st.inst = v; save(); paintInst(); paint(); }, options: [{ v: 'MNQ', label: 'MNQ · 2 $/pt' }, { v: 'NQ', label: 'NQ · 20 $/pt' }] })); }
  paintInst();
  var form = U.fields([
    { label: 'Risque par trade', unit: '$', value: st.risk, min: 1, hint: 'réglages : ' + F.usd(set.riskPerTrade, 0), onChange: function (v) { st.risk = v; save(); paint(); } },
    { label: 'Stop', unit: 'pt', value: st.stop, min: 0.25, max: 2000, hint: 'distance entrée → invalidation', onChange: function (v) { st.stop = v; save(); paint(); } },
    instBox
  ]);
  s1.appendChild(U.card({ body: [form, res] })); root.appendChild(s1);
  var s2 = U.section('De 5 à *60 points*', ''), tab = h('div', { class: 'nq-stack' }); s2.appendChild(tab); root.appendChild(s2);
  var s3 = U.section('Ce que *la taille* ne corrige pas', 'ALP nº 3, partie XI'); root.appendChild(s3);
  s3.appendChild(h('div', { class: 'nq-notes' },
    h('p', null, h('b', null, 'Le stop vient du marché, la taille vient du stop. '), 'Resserrer le stop pour « rentrer » un contrat de plus fait monter la part de la friction dans chaque perte. À dérive nulle, toute géométrie rend exactement −c/L : la friction divisée par le stop, en multiples du risque.'),
    h('p', null, h('b', null, 'Zéro contrat est une réponse. '), 'Si un seul contrat dépasse ton risque, le trade est trop grand pour ce stop : on passe au MNQ ou on renonce, on ne raccourcit pas le stop.')));
  s3.appendChild(U.note('Le glissement n’entre pas dans le nombre de contrats (formule : plancher du risque ÷ (stop × valeur du point + commission)) ; il entre dans c/L, avec celui de l’onglet Contrat.'));

  function paint() {
    var f = getFrais(set), sp = L.SPEC[st.inst], com = f[st.inst], r = L.size({ risk: st.risk, stop: st.stop, pointValue: sp.pv, commission: com });
    var c = L.friction({ commission: com, pointValue: sp.pv, tick: sp.tick, slipTicks: f.slip }), cr = L.costR(c, st.stop);
    var other = st.inst === 'MNQ' ? 'NQ' : 'MNQ', ro = L.size({ risk: st.risk, stop: st.stop, pointValue: L.SPEC[other].pv, commission: f[other] });
    T.clear(res);
    res.appendChild(U.kpis([
      { label: 'Contrats ' + st.inst, value: F.int(r.contracts), tone: r.contracts > 0 ? 'acc' : 'neg', hint: r.contracts > 0 ? 'en ' + other + ' : ' + ro.contracts : 'aucun : stop trop large' },
      { label: 'Risque réel', value: F.usd(r.realRisk, 2), hint: 'non engagé : ' + F.usd(r.unused, 2) },
      { label: 'Par contrat', value: F.usd(r.perContract, 2), hint: 'dont ' + F.usd(com, 2) + ' de frais' },
      { label: 'Friction / stop', value: F.num(fin(cr) ? -cr : NaN, 3), unit: 'R', tone: 'neg', hint: 'c = ' + pts(c) + ' pt par trade' }
    ], 4));
    res.appendChild(U.note('À dérive nulle, chaque trade de cette géométrie coûte en moyenne ' + F.r(cr, 3) + ' : la friction (' + pts(c) + ' pt) rapportée au stop (' + pts(st.stop) + ' pt).'));
    T.clear(tab);
    var meta = s2.querySelector('.sh span'); if (meta) meta.textContent = st.inst + ' · risque ' + F.usd(st.risk, 0);
    var pts2 = []; for (var s = 3; s <= 60; s += 0.25) { var z = L.size({ risk: st.risk, stop: s, pointValue: sp.pv, commission: com }); pts2.push([s, z.realRisk]); }
    tab.appendChild(U.card({ title: 'Le risque réellement engagé', meta: 'selon le stop', body: [C.line({ series: [{ name: 'Risque réel', points: pts2, tone: 'violet', area: true }], x: { fmt: function (v) { return F.num(v, 0) + ' pt'; } }, y: { fmt: function (v) { return F.usd(v, 0); }, zero: true }, hlines: [{ y: st.risk, label: 'budget ' + F.usd(st.risk, 0), tone: 'mute' }], vlines: [{ x: st.stop }], height: 190, ml: 54, endDots: false }),
      U.note('Le nombre de contrats est entier : le risque engagé tombe en dents de scie sous le budget, et la marge perdue grandit avec le stop.')] }));
    var rows = []; for (var k = 5; k <= 60; k += 5) { var y = L.size({ risk: st.risk, stop: k, pointValue: sp.pv, commission: com }); rows.push({ stop: k, per: y.perContract, n: y.contracts, real: y.realRisk, cl: L.costR(c, k) }); }
    tab.appendChild(U.table({ cols: [
      { k: 'stop', label: 'Stop', fmt: function (v) { return F.num(v, 0) + ' pt'; } },
      { k: 'n', label: 'Contrats', align: 'r', fmt: function (v) { return F.int(v); } },
      { k: 'real', label: 'Risque réel', align: 'r', fmt: function (v) { return F.usd(v, 2); } },
      { k: 'cl', label: '−c/L', align: 'r', fmt: function (v) { return F.num(v, 3); } }], rows: rows, rowClass: function (row) { return Math.abs(row.stop - st.stop) < 1e-9 ? 'sel' : row.n === 0 ? 'neg' : null; } }));
    typo(res); typo(tab);
  }
  paint(); typo(s1); typo(s3);
}

/* =====================================================================
   3. Le desk
   ===================================================================== */
var HEAD = {
  seance: { t: 'La séance, *calculée* depuis New York.', l: 'Paris, New York, Globex et ta fenêtre de trading, à la seconde. Chaque horaire se recalcule depuis New York : rien n’est écrit en dur, pas même 15 h 30.' },
  gex: { t: 'Des niveaux *collés*, jamais devinés.', l: 'Colle l’export du robot tel quel. Le desk le lit comme l’indicateur du dépôt, porte les niveaux sur le NQ si tu donnes la base, puis t’aide à déclarer le biais du jour.' },
  contrat: { t: 'Le contrat, et *sa case*.', l: 'NQ et MNQ côte à côte, la friction de tes frais en points, et la durée de tenue sous laquelle aucune dérive plausible ne la couvre.' },
  taille: { t: 'Le stop décide de *la taille*.', l: 'Un risque en dollars, un stop en points : le nombre de contrats en découle, jamais l’inverse.' }
};
T.desk({
  id: 'nq', label: 'NQ futures', glyph: 'N', group: 'Marché', order: 20,
  tabs: [{ id: 'seance', label: 'Séance' }, { id: 'gex', label: 'Niveaux GEX' }, { id: 'contrat', label: 'Contrat' }, { id: 'taille', label: 'Taille' }],
  render: function (root, ctx) {
    injectCss();
    var tab = HEAD[ctx.tab] ? ctx.tab : 'seance', hd = HEAD[tab];
    var head = U.page({ kicker: 'Marché · NQ futures', title: hd.t, lede: hd.l }); typo(head); root.appendChild(head);
    root.appendChild(U.tabs({ tabs: this.tabs, value: tab, onChange: ctx.setTab }));
    if (tab === 'gex') return renderGex(root, ctx);
    if (tab === 'contrat') return renderContrat(root, ctx);
    if (tab === 'taille') return renderTaille(root, ctx);
    return renderSeance(root, ctx);
  }
});
