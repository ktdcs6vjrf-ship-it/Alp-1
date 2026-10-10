/* Desk « Risque » : le compte de prop firm, les disjoncteurs du jour, l’évaluation simulée, les règles de survie.
   Sources, contrôlées par test/risk.test.js :
   – ALP nº 3, vingtième partie : « a/(a+b) — la toucher avant le stop. C’est le théorème d’arrêt optionnel » ;
     4,76 % à un rapport d’un pour vingt. Ici a = distance à la liquidation, b = distance à l’objectif.
   – ALP nº 3, onzième partie : « à dérive nulle, les quatre droites valent exactement −c/L » : aucune géométrie
     ne crée d’espérance, la friction seule reste.
   – Plancher suiveur continu (baisse de A avant hausse de B) : Taylor (1975), Lehoczky (1977),
     P = exp(−γB), γ = k/(e^{kA} − 1), k = 2µ/σ² ; γ = 1/A à dérive nulle.
   Les règles de prop firm sont des préréglages modifiables, marqués « à vérifier ». */
var h = T.h, U = T.ui, C = T.chart, F = T.fmt;
T.lib = T.lib || {};
var L = T.lib.risk = {};
var K = { acc: 'risk:account', rules: 'risk:rules', sim: 'risk:sim', check: 'risk:rulecheck:', limits: 'risk:daylimits:' };
L.KEYS = K;

/* =====================================================================
   1. Fonctions pures — aucun DOM, aucun T.store
   ===================================================================== */
function fin(v) { return typeof v === 'number' && isFinite(v); }
function posOr(v, d) { return fin(v) && v > 0 ? v : d; }
function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }
L.fin = fin;

/* Prérèglages : des règles courantes du marché des prop firms, aucune firme précise. À vérifier. */
L.PRESETS = {
  '50k': { label: '50 k', size: 50000, target: 3000, maxLoss: 2000, dd: 'eod', lockAt: 52100, dailyLimit: 1000, dailyMode: 'pause', maxContracts: 50, consistency: 50, verify: true },
  '100k': { label: '100 k', size: 100000, target: 6000, maxLoss: 3000, dd: 'eod', lockAt: 103100, dailyLimit: 2000, dailyMode: 'pause', maxContracts: 100, consistency: 50, verify: true },
  '150k': { label: '150 k', size: 150000, target: 9000, maxLoss: 4500, dd: 'eod', lockAt: 154600, dailyLimit: 3000, dailyMode: 'pause', maxContracts: 150, consistency: 50, verify: true }
};
L.PRESET_IDS = ['50k', '100k', '150k'];
L.DD = [
  { v: 'eod', label: 'Fin de jour', long: 'suiveur de fin de journée', hint: 'Le plancher suit ton plus haut solde de clôture, une fois par jour.' },
  { v: 'intraday', label: 'En séance', long: 'suiveur intrajournalier', hint: 'Le plancher suit ton plus haut en séance, gains latents compris.' },
  { v: 'static', label: 'Statique', long: 'statique', hint: 'Le plancher ne bouge jamais : taille − perte maximale.' }
];
L.DD_IDS = ['eod', 'intraday', 'static'];
L.ddLabel = function (v) { var d = L.DD.filter(function (x) { return x.v === v; })[0]; return d ? d.long : v; };

L.normAccount = function (a) {
  a = a || {};
  var known = !!L.PRESETS[a.preset], base = L.PRESETS[a.preset] || L.PRESETS['50k'];
  var size = posOr(a.size, base.size), maxLoss = posOr(a.maxLoss, base.maxLoss), target = posOr(a.target, base.target);
  var o = {
    preset: known || a.preset === 'perso' ? a.preset : (a.preset == null ? '50k' : 'perso'),
    size: size, target: target, maxLoss: maxLoss,
    dd: L.DD_IDS.indexOf(a.dd) >= 0 ? a.dd : base.dd,
    lockAt: fin(a.lockAt) ? Math.max(size, a.lockAt) : size + maxLoss + 100,
    dailyLimit: a.dailyLimit === null ? null : (fin(a.dailyLimit) && a.dailyLimit > 0 ? a.dailyLimit : (a.dailyLimit === undefined ? base.dailyLimit : null)),
    dailyMode: a.dailyMode === 'fail' ? 'fail' : 'pause',
    maxContracts: Math.max(1, Math.round(posOr(a.maxContracts, base.maxContracts))),
    consistency: a.consistency === null ? null : (fin(a.consistency) && a.consistency > 0 ? Math.min(100, a.consistency) : (a.consistency === undefined ? base.consistency : null))
  };
  o.balance = fin(a.balance) ? a.balance : size;
  o.high = Math.max(fin(a.high) ? a.high : size, o.balance, size);
  return o;
};
L.applyPreset = function (id) {
  var p = L.PRESETS[id]; if (!p) return null;
  return { preset: id, size: p.size, target: p.target, maxLoss: p.maxLoss, dd: p.dd, lockAt: p.lockAt, dailyLimit: p.dailyLimit, dailyMode: p.dailyMode, maxContracts: p.maxContracts, consistency: p.consistency, balance: p.size, high: p.size };
};
/* Une modification de taille ou de perte max entraîne le solde, le plus haut et le verrou s’ils étaient à leur valeur de départ. */
L.patchAccount = function (cur, patch) {
  var a = L.normAccount(cur), b = Object.assign({}, a, patch);
  if ('size' in patch && fin(patch.size)) {
    if (a.balance === a.size) b.balance = patch.size;
    if (a.high === a.size) b.high = patch.size;
  }
  if (('size' in patch || 'maxLoss' in patch) && a.lockAt === a.size + a.maxLoss + 100) b.lockAt = posOr(b.size, a.size) + posOr(b.maxLoss, a.maxLoss) + 100;
  return L.normAccount(b);
};

/* Plancher de liquidation : statique = taille − perte max ; suiveur = min(plus haut, verrou) − perte max. */
L.floorOf = function (acc) { var a = L.normAccount(acc); return a.dd === 'static' ? a.size - a.maxLoss : Math.min(a.high, a.lockAt) - a.maxLoss; };

L.distances = function (acc, pointValue, risk, cost) {
  var a = L.normAccount(acc), fl = L.floorOf(a), pv = posOr(pointValue, 2);
  var dl = a.balance - fl, dob = a.size + a.target - a.balance, trailing = a.dd !== 'static', locked = trailing && a.high >= a.lockAt;
  var per = (risk || 0) + (cost || 0);
  return {
    floor: fl, objective: a.size + a.target, distLiq: dl, distObj: dob,
    ratio: dl > 0 && dob > 0 ? dob / dl : NaN,
    ptsLiq: dl / pv, ptsLiqMax: dl / (pv * a.maxContracts),
    trailing: trailing, locked: locked, toLock: trailing && !locked ? a.lockAt - a.high : 0, lockFloor: a.lockAt - a.maxLoss,
    /* pertes pleines encaissables : le plus grand k tel que k·(risque + frais) < distance */
    fullLosses: per > 0 && dl > 0 ? Math.max(0, Math.ceil(dl / per - 1e-9) - 1) : 0,
    dayCap: a.consistency ? a.consistency / 100 * a.target : null,
    pTheorem: dob <= 0 ? 1 : dl <= 0 ? 0 : dl / (dl + dob)
  };
};

/* Marche de dérive µ et de variance σ² par trade : probabilité de monter de B avant de baisser de A.
   P = (1 − e^{−kA}) / (1 − e^{−k(A+B)}), k = 2µ/σ² ; à dérive nulle, A/(A + B). */
L.pObjectif = function (mu, s2, A, B) {
  if (!(A > 0)) return 0; if (!(B > 0)) return 1;
  if (!(s2 > 0)) return mu > 0 ? 1 : mu < 0 ? 0 : A / (A + B);
  var k = 2 * mu / s2;
  if (Math.abs(k * (A + B)) < 1e-10) return A / (A + B);
  if (k > 0) return -Math.expm1(-k * A) / -Math.expm1(-k * (A + B));
  var u = -k;
  return Math.exp(-u * B) * (-Math.expm1(-u * A)) / (-Math.expm1(-u * (A + B)));
};
/* Taux de « hausse avant baisse de A » d’un plancher suiveur continu : γ = k/(e^{kA} − 1), 1/A à dérive nulle. */
L.rallyHazard = function (mu, s2, A) {
  if (!(s2 > 0)) return mu >= 0 ? 0 : Infinity;
  var k = 2 * mu / s2;
  if (Math.abs(k * A) < 1e-10) return 1 / A;
  return k / Math.expm1(k * A);
};
/* Plancher suiveur continu, depuis un solde pnl et un plus haut hwm (relatifs au départ), verrou au plus haut `lock`. */
L.pTrailing = function (mu, s2, A, B, lock, pnl, hwm) {
  pnl = pnl || 0; hwm = Math.max(hwm || 0, pnl); lock = fin(lock) ? lock : Infinity;
  if (pnl >= B) return 1;
  if (hwm >= lock) return L.pObjectif(mu, s2, pnl - (lock - A), B - pnl);
  var floor = hwm - A; if (pnl <= floor) return 0;
  if (hwm >= B) return L.pObjectif(mu, s2, pnl - floor, B - pnl);
  var back = L.pObjectif(mu, s2, pnl - floor, hwm - pnl);
  var top = Math.min(lock, B), climb = Math.exp(-L.rallyHazard(mu, s2, A) * (top - hwm));
  return back * climb * (lock < B ? L.pObjectif(mu, s2, A, B - lock) : 1);
};
L.pStatic = function (mu, s2, A, B, pnl) { pnl = pnl || 0; return L.pObjectif(mu, s2, pnl + A, B - pnl); };
/* La formule d’arrêt optionnel à dérive nulle, sans échéance ni frais, pour un compte neuf.
   Le suiveur de fin de journée n’a pas de forme fermée : il est encadré par le suiveur continu et le plancher statique. */
L.formulaNull = function (A, B, dd, lockRel) {
  var st = A / (A + B);
  if (dd === 'static') return { v: st, lo: st, hi: st };
  var tr = L.pTrailing(0, 1, A, B, lockRel, 0, 0);
  if (dd === 'intraday') return { v: tr, lo: tr, hi: tr };
  return { v: (tr + st) / 2, lo: tr, hi: st };
};

/* Géométrie d’un trade : gain `win` R ou perte `loss` R, risque `risk` $ par R, frais `cost` $. */
L.moments = function (p, win, loss, risk, cost) { return { mu: risk * (p * win - (1 - p) * loss) - (cost || 0), s2: p * (1 - p) * Math.pow((win + loss) * risk, 2) }; };
L.expectancyR = function (p, win, loss, cost, risk) { return p * win - (1 - p) * loss - (cost || 0) / risk; };
/* Taux d’équilibre (loi nulle) : espérance nette nulle. Avec une perte de 1 R : (1 + coût/risque)/(R + 1). */
L.equilibrium = function (win, loss, cost, risk) { return (loss + (cost || 0) / risk) / (win + loss); };
/* Sans avantage : espérance brute nulle, les frais seuls restent. */
L.zeroEdge = function (win, loss) { return loss / (win + loss); };

L.DEF_SIM = { p: 0.45, win: 1.5, loss: 1, risk: null, tpd: null, cost: 5, days: 30, seed: 7 };
L.normSim = function (raw, set) {
  var s = Object.assign({}, L.DEF_SIM, raw || {}); set = set || {};
  return {
    p: clamp(fin(s.p) ? s.p : 0.45, 0, 1), win: clamp(posOr(s.win, 1.5), 0.05, 50), loss: clamp(posOr(s.loss, 1), 0.05, 10),
    risk: posOr(s.risk, posOr(set.riskPerTrade, 150)), tpd: clamp(Math.round(posOr(s.tpd, posOr(set.maxTradesDay, 3))), 1, 20),
    cost: fin(s.cost) && s.cost >= 0 ? s.cost : 5, days: clamp(Math.round(posOr(s.days, 30)), 1, 120), seed: Math.max(1, Math.round(posOr(s.seed, 7)))
  };
};
L.simArgs = function (sp, acc, p, cost, extra) {
  var a = L.normAccount(acc);
  return Object.assign({ p: p, win: sp.win, loss: sp.loss, risk: sp.risk, tpd: sp.tpd, cost: cost, target: a.target, maxLoss: a.maxLoss, dd: a.dd,
    lock: a.lockAt - a.size, daily: a.dailyLimit, dailyMode: a.dailyMode, days: sp.days, n: 5000, seed: sp.seed, fan: true, keep: 14 }, extra || {});
};

/* Monte-Carlo d’une évaluation. Fonction AUTONOME (exécutée telle quelle dans un Web Worker) : aucune variable extérieure.
   Chaque trade finit à +gain ou à −perte (frais déduits à la clôture). Pendant le trade, l’excursion contraire d’un
   gagnant et l’excursion favorable d’un perdant suivent la loi d’un mouvement brownien sans dérive conditionné à son
   issue : P(max ≥ m | perte) = S(G − m)/((S + m)G), tirée par inversion. Elle fait monter un suiveur intrajournalier
   sur un trade qui finit perdant, et elle peut toucher le plancher pendant un trade qui aurait gagné.
   Une graine par trajectoire (mêmes tirages d’un scénario à l’autre). */
function riskSimulate(a) {
  function fmix(x) { x ^= x >>> 16; x = Math.imul(x, 0x85ebca6b); x ^= x >>> 13; x = Math.imul(x, 0xc2b2ae35); x ^= x >>> 16; return x >>> 0; }
  function med(arr) { if (!arr.length) return NaN; var s = arr.slice().sort(function (x, y) { return x - y; }), m = (s.length - 1) / 2; return (s[Math.floor(m)] + s[Math.ceil(m)]) / 2; }
  function qt(s, q) { var p = (s.length - 1) * q, lo = Math.floor(p), hi = Math.ceil(p); return s[lo] + (s[hi] - s[lo]) * (p - lo); }
  var n = Math.max(1, Math.floor(a.n || 5000)), D = Math.max(1, Math.floor(a.days || 30)), tpd = Math.max(1, Math.floor(a.tpd || 1));
  var p = Math.max(0, Math.min(1, +a.p || 0)), S = (+a.loss || 1) * (+a.risk), G = (+a.win) * (+a.risk), c = +a.cost || 0;
  var A = +a.maxLoss, B = +a.target, mode = a.dd === 'intraday' || a.dd === 'eod' ? a.dd : 'static';
  var lock = a.lock == null || !isFinite(a.lock) ? Infinity : +a.lock;
  var daily = a.daily != null && +a.daily > 0 ? +a.daily : 0, dfail = a.dailyMode === 'fail';
  var pnl0 = +a.pnl0 || 0, hwm0 = Math.max(+a.hwm0 || 0, pnl0);
  var fan = !!a.fan, keep = fan ? Math.max(0, Math.floor(a.keep || 0)) : 0, W = D + 1;
  var mat = fan ? new Float64Array(n * W) : null, passBy = [], failBy = [], k0;
  for (k0 = 0; k0 < W; k0++) { passBy.push(0); failBy.push(0); }
  var passDays = [], failDays = [], cause = { gain: 0, never: 0, daily: 0 }, trSum = 0, trRes = 0;
  var base = fmix(((a.seed >>> 0) || 1) ^ 0x9e3779b9);
  for (var i = 0; i < n; i++) {
    var s = fmix(base ^ fmix(i + 1)), z, u1, u2;
    var pnl = pnl0, hwm = hwm0, best = pnl0, st = 0, day = 0, last = 0, tr = 0, why = '';
    var fl0 = mode === 'static' ? -A : Math.min(hwm, lock) - A;
    if (pnl >= B) st = 1; else if (pnl <= fl0) { st = 2; why = best > 0 ? 'gain' : 'never'; }
    if (fan) mat[i * W] = pnl;
    for (var d = 1; d <= D && !st; d++) {
      var dayPnl = 0;
      for (var t = 0; t < tpd; t++) {
        var floor = mode === 'static' ? -A : Math.min(hwm, lock) - A;
        s = (s + 0x6D2B79F5) >>> 0; z = s; z = Math.imul(z ^ (z >>> 15), z | 1); z ^= z + Math.imul(z ^ (z >>> 7), z | 61); u1 = ((z ^ (z >>> 14)) >>> 0) / 4294967296;
        s = (s + 0x6D2B79F5) >>> 0; z = s; z = Math.imul(z ^ (z >>> 15), z | 1); z ^= z + Math.imul(z ^ (z >>> 7), z | 61); u2 = ((z ^ (z >>> 14)) >>> 0) / 4294967296;
        var win = u1 < p, low, end;
        if (win) { low = pnl - G * S * (1 - u2) / (u2 * S + G); end = G - c; }
        else {
          if (mode === 'intraday') { var pk = pnl + S * G * (1 - u2) / (u2 * G + S); if (pk > hwm) { hwm = pk; floor = Math.min(hwm, lock) - A; } }
          low = pnl - S; end = -S - c;
        }
        tr++;
        var dl = daily ? pnl - dayPnl - daily : -Infinity;
        if (low <= floor || low <= dl) {
          if (floor >= dl) { pnl = floor - c; st = 2; why = best > 0 ? 'gain' : 'never'; break; }
          pnl = dl - c; dayPnl = -daily - c;
          if (pnl <= floor) { st = 2; why = best > 0 ? 'gain' : 'never'; } else if (dfail) { st = 2; why = 'daily'; }
          break;
        }
        if (win && mode === 'intraday' && pnl + G > hwm) hwm = pnl + G;
        pnl += end; dayPnl += end;
        if (pnl > best) best = pnl;
        if (pnl >= B) { st = 1; break; }
        floor = mode === 'static' ? -A : Math.min(hwm, lock) - A;
        if (pnl <= floor) { st = 2; why = best > 0 ? 'gain' : 'never'; break; }
        if (daily && dayPnl <= -daily) { if (dfail) { st = 2; why = 'daily'; } break; }
      }
      if (!st && mode === 'eod' && pnl > hwm) hwm = pnl;
      if (fan) mat[i * W + d] = pnl;
      last = d;
      if (st) day = d;
    }
    if (fan) for (var e = last + 1; e < W; e++) mat[i * W + e] = pnl;
    trSum += tr;
    if (st === 1) { passBy[day]++; passDays.push(day); trRes += tr; }
    else if (st === 2) { failBy[day]++; failDays.push(day); cause[why]++; trRes += tr; }
  }
  var q = null, paths = [];
  if (fan) {
    q = { p05: [], p25: [], p50: [], p75: [], p95: [] };
    var col = new Float64Array(n);
    for (var dd = 0; dd < W; dd++) {
      for (var j = 0; j < n; j++) col[j] = mat[j * W + dd];
      col.sort();
      q.p05.push(qt(col, 0.05)); q.p25.push(qt(col, 0.25)); q.p50.push(qt(col, 0.5)); q.p75.push(qt(col, 0.75)); q.p95.push(qt(col, 0.95));
    }
    for (var kk = 0; kk < Math.min(keep, n); kk++) paths.push(Array.prototype.slice.call(mat.subarray(kk * W, kk * W + W)));
  }
  var np = passDays.length, nf = failDays.length;
  return {
    n: n, days: D, pass: np, fail: nf, none: n - np - nf, pPass: np / n, pFail: nf / n, pNone: (n - np - nf) / n,
    medPass: med(passDays), medFail: med(failDays), medAll: med(passDays.concat(failDays)),
    passDays: passDays, failDays: failDays, passBy: passBy, failBy: failBy, cause: cause,
    meanTrades: trSum / n, meanTradesRes: np + nf ? trRes / (np + nf) : NaN, q: q, paths: paths
  };
}
L.simulate = riskSimulate;

/* Arguments du théorème appliqué au compte : à avantage nul, depuis le solde courant, sans échéance pratique.
   Le nombre de trajectoires se règle sur le nombre de trades attendu (A·B/σ²) pour tenir le calcul sous la seconde. */
L.theoremArgs = function (acc, sp) {
  var a = L.normAccount(acc), d = L.distances(a);
  var s2 = sp.win * sp.loss * sp.risk * sp.risk, estN = Math.max(1, Math.max(d.distLiq, 1) * Math.max(d.distObj, 1) / s2);
  var n = clamp(Math.floor(1.6e7 / estN), 400, 5000), days = clamp(Math.ceil(12 * estN / sp.tpd) + 5, 30, 20000);
  var b = { p: L.zeroEdge(sp.win, sp.loss), win: sp.win, loss: sp.loss, risk: sp.risk, tpd: sp.tpd, target: a.target, maxLoss: a.maxLoss, dd: a.dd,
    lock: a.lockAt - a.size, daily: a.dailyLimit, dailyMode: a.dailyMode, days: days, n: n, seed: sp.seed, pnl0: a.balance - a.size, hwm0: a.high - a.size, fan: false };
  return { rules: Object.assign({}, b, { cost: 0 }), friction: Object.assign({}, b, { cost: sp.cost }), estN: estN };
};

/* ---------- La journée ---------- */
function pad2(x) { return String(x).padStart(2, '0'); }
L.dayKeyOf = function (at, tz) { var p = T.time.parts(tz || 'Europe/Paris', new Date(at)); return p.y + '-' + pad2(p.mo) + '-' + pad2(p.d); };
L.hhmmOf = function (at, tz) { return T.time.hhmm(tz || 'Europe/Paris', new Date(at)); };
L.todayRows = function (rows, key) { return (rows || []).filter(function (r) { return r && !r.deleted && fin(r.at) && L.dayKeyOf(r.at) === key; }); };
L.LIMIT_KEYS = ['riskPerTrade', 'maxTradesDay', 'maxLossesDay', 'dailyStop'];
/* Une fois confirmées, les limites du jour ne se relâchent plus : la plus stricte des deux s’applique. */
L.effectiveLimits = function (set, snap) {
  var lim = {}, loosened = [];
  L.LIMIT_KEYS.forEach(function (k) { var c = +set[k]; if (snap && fin(snap[k])) { if (c > snap[k]) loosened.push(k); lim[k] = Math.min(c, snap[k]); } else lim[k] = c; });
  return { lim: lim, loosened: loosened };
};
L.COOLDOWN_MIN = 15;
L.dayState = function (rows, set, acc, now, o) {
  o = o || {};
  var key = L.dayKeyOf(now), today = L.todayRows(rows, key), taken = today.filter(function (r) { return r.kind === 'pris'; });
  var closed = taken.filter(function (r) { return fin(r.pnl); }).sort(function (x, y) { return (x.closedAt || x.at) - (y.closedAt || y.at); });
  var pnl = closed.reduce(function (s, r) { return s + r.pnl; }, 0);
  var losses = closed.filter(function (r) { return r.pnl < 0; }).length, wins = closed.filter(function (r) { return r.pnl > 0; }).length;
  var open = taken.filter(function (r) { return !fin(r.pnl) && r.status !== 'clos'; }).length;
  var E = L.effectiveLimits(set, o.snap), lim = E.lim, a = acc ? L.normAccount(acc) : null;
  var stopEff = lim.dailyStop, stopSrc = 'toi';
  if (a && a.dailyLimit && a.dailyLimit < stopEff) { stopEff = a.dailyLimit; stopSrc = 'compte'; }
  var lossSoFar = Math.max(0, -pnl), riskLeft = Math.max(0, stopEff - lossSoFar), lastLoss = -Infinity;
  closed.forEach(function (r) { if (r.pnl < 0) { var t = fin(r.closedAt) ? r.closedAt : r.at; if (t > lastLoss) lastLoss = t; } });
  var cd = Math.max(0, lastLoss + L.COOLDOWN_MIN * 60000 - now);
  var dist = a ? L.distances(a, set.pointValue, lim.riskPerTrade, 0) : null;
  var br = [];
  if (o.confirmed === false || o.confirmed === true) br.push({ id: 'confirm', open: !o.confirmed });
  br.push({ id: 'trades', used: taken.length, max: lim.maxTradesDay, open: taken.length >= lim.maxTradesDay });
  br.push({ id: 'pertes', used: losses, max: lim.maxLossesDay, open: losses >= lim.maxLossesDay });
  br.push({ id: 'stop', used: lossSoFar, max: stopEff, open: lossSoFar >= stopEff });
  br.push({ id: 'prochain', used: lim.riskPerTrade, max: riskLeft, open: riskLeft < lim.riskPerTrade });
  br.push({ id: 'refroid', ms: cd, open: cd > 0 });
  if (o.inWindow === false || o.inWindow === true) br.push({ id: 'fenetre', open: !o.inWindow });
  if (dist) br.push({ id: 'compte', used: lim.riskPerTrade, max: dist.distLiq, open: dist.distLiq <= lim.riskPerTrade });
  return {
    key: key, rows: today, closedRows: closed, taken: taken.length, closed: closed.length, open: open, pnl: pnl, losses: losses, wins: wins,
    stopEff: stopEff, stopSrc: stopSrc, lossSoFar: lossSoFar, riskLeft: riskLeft, lastLoss: lastLoss, cooldownMs: cd,
    limits: lim, loosened: E.loosened, dist: dist, breakers: br, canTrade: !br.some(function (b) { return b.open; })
  };
};
L.fmtClock = function (ms) { var s = Math.max(0, Math.ceil(ms / 1000)); return Math.floor(s / 60) + ':' + pad2(s % 60); };

/* ---------- Les règles ---------- */
L.MOMENTS = [
  { v: 'avant', label: 'Avant la séance' }, { v: 'entree', label: 'À l’entrée' }, { v: 'pendant', label: 'Pendant le trade' },
  { v: 'perte', label: 'Après une perte' }, { v: 'journee', label: 'Toute la séance' }
];
L.DEFAULT_RULES = [
  { id: 'r-limites', m: 'avant', t: 'Mes limites du jour sont confirmées avant la première entrée', s: 'Risque par trade, nombre de trades, nombre de pertes, stop du jour : écrits et confirmés dans « Aujourd’hui » avant d’ouvrir la plateforme.' },
  { id: 'r-stop', m: 'entree', t: 'Le stop est placé avant l’entrée', s: 'L’ordre stop part avec l’ordre d’entrée. Un stop « dans la tête » n’est pas un stop.' },
  { id: 'r-taille', m: 'entree', t: 'La taille se calcule depuis le stop', s: 'Contrats = risque par trade ÷ (distance du stop en points × valeur du point), arrondi vers le bas. Jamais l’inverse.' },
  { id: 'r-journal', m: 'entree', t: 'Pas de trade sans ligne de journal', s: 'Le setup, le stop et l’objectif sont inscrits au moment de la décision. Un refus aussi.' },
  { id: 'r-moyenne', m: 'pendant', t: 'Jamais de moyenne à la baisse', s: 'On n’ajoute pas à une position perdante. Un renfort ne se fait que sur une position gagnante, stop remonté.' },
  { id: 'r-recul', m: 'pendant', t: 'Le stop ne recule jamais', s: 'Il se rapproche ou passe au point mort. Il ne s’éloigne pas pour « laisser respirer » le trade.' },
  { id: 'r-revanche', m: 'perte', t: 'Pas de revanche après une perte', s: 'Quinze minutes loin de l’exécution. Le trade suivant est un setup écrit d’avance, pas une réponse au marché.' },
  { id: 'r-arret', m: 'perte', t: 'J’arrête au nombre de pertes fixé', s: 'Quand le nombre de pertes du jour est atteint, la séance est finie, quel que soit le P&L.' },
  { id: 'r-fenetre', m: 'journee', t: 'Pas de trade hors de ma fenêtre', s: 'Hors de la fenêtre horaire déclarée, je regarde et je note. Je n’exécute rien.' },
  { id: 'r-annonce', m: 'journee', t: 'Pas de position ouverte pendant une annonce majeure', s: 'Une publication classée majeure au calendrier se traverse à plat. Le setup attendra la bougie suivante.' }
];
L.normRules = function (raw) {
  if (!Array.isArray(raw)) return L.DEFAULT_RULES.map(function (r) { return Object.assign({}, r); });
  var ms = L.MOMENTS.map(function (m) { return m.v; });
  return raw.filter(function (r) { return r && r.id; }).map(function (r) { return { id: String(r.id), m: ms.indexOf(r.m) >= 0 ? r.m : 'journee', t: String(r.t || ''), s: String(r.s || '') }; });
};
L.adherence = function (check, rules) {
  var total = rules.length, kept = rules.filter(function (r) { return check && check[r.id]; }).length;
  return { kept: kept, total: total, pct: total ? kept / total : NaN };
};
/* Les n derniers jours calendaires jusqu’à `key` inclus, par arithmétique de calendrier (aucun piège d’heure d’été). */
L.pastKeys = function (key, n) {
  var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(key || ''); if (!m) return [];
  var out = [];
  for (var i = n - 1; i >= 0; i--) { var d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3] - i, 12)); out.push(d.getUTCFullYear() + '-' + pad2(d.getUTCMonth() + 1) + '-' + pad2(d.getUTCDate())); }
  return out;
};

/* ---------- Le journal comme hypothèse ---------- */
L.fromJournal = function (rows, risk) {
  var rs = (rows || []).filter(function (r) { return r && !r.deleted && r.kind === 'pris' && (fin(r.r) || (fin(r.pnl) && risk > 0)); })
    .map(function (r) { return fin(r.r) ? r.r : r.pnl / risk; });
  var n = rs.length, w = rs.filter(function (x) { return x > 0; }), l = rs.filter(function (x) { return x < 0; });
  if (n < 10 || !w.length || !l.length) return null;
  var p = w.length / n, avg = function (a) { return a.reduce(function (s, x) { return s + x; }, 0) / a.length; };
  return { n: n, p: p, win: avg(w), loss: -avg(l), hw: 1.96 * Math.sqrt(p * (1 - p) / n) };
};

/* Typographie française sur les textes écrits ici : espace fine insécable avant : ; ? ! et devant % $. */
L.typo = function (t) { return String(t).replace(/ ([:;?!»])/g, ' $1').replace(/« /g, '« ').replace(/(\d) (%|\$)/g, '$1 $2').replace(/nº /g, 'nº ').replace(/ — /g, ' — '); };

/* =====================================================================
   2. Présentation
   ===================================================================== */
var CSS = [
  '.rk-state{border:1px solid var(--line);border-radius:var(--r);background:var(--panel);padding:16px 16px 15px;display:flex;flex-direction:column;gap:7px;min-width:0}',
  '.rk-state.go{border-color:var(--violet-b);background:linear-gradient(180deg,var(--violet-a),transparent 78%),var(--panel)}',
  '.rk-state.stop{border-color:var(--line-2);background:var(--hatch),var(--panel)}',
  '.rk-state .k{font:600 10px/1.35 var(--f-mono);letter-spacing:.14em;text-transform:uppercase;color:var(--mute)}',
  '.rk-state.go .k{color:var(--violet-2)}',
  '.rk-state .t{font-size:36px;line-height:1.04;font-weight:600;letter-spacing:-.03em;color:var(--hi)}',
  '.rk-state .t em{font-family:var(--f-serif);font-style:italic;font-weight:400;letter-spacing:-.01em;font-size:1.1em}',
  '.rk-state .s{font-size:13.5px;color:var(--soft);line-height:1.5;max-width:62ch}',
  '.rk-circ{border:1px solid var(--line);border-radius:var(--r);background:var(--panel);overflow:hidden}',
  '.rk-br{display:grid;grid-template-columns:30px minmax(0,1fr) auto;column-gap:10px;padding:0 13px 0 8px;border-top:1px solid var(--line);min-height:62px}',
  '.rk-br:first-child{border-top:0}',
  '.rk-br.cut{background:var(--hatch)}',
  '.rk-sw{display:flex;flex-direction:column;align-items:center}',
  '.rk-sw>i{flex:1;width:1.5px;min-height:8px;background:var(--line-2)}',
  '.rk-sw>span{display:block;line-height:0;flex:none}',
  '.rk-br .tx{padding:11px 0;min-width:0;display:flex;flex-direction:column;justify-content:center;gap:3px}',
  '.rk-br .tx>b{font-size:13.5px;font-weight:600;color:var(--fg)}',
  '.rk-br .tx>span{font-size:12px;color:var(--mute);line-height:1.4}',
  '.rk-br.cut .tx>span{color:var(--soft)}',
  '.rk-br .vl{align-self:center;text-align:right;font:600 14px/1.15 var(--f-mono);color:var(--hi);white-space:nowrap;font-variant-numeric:tabular-nums}',
  '.rk-br .vl small{display:block;margin-top:5px;font:600 9.5px/1 var(--f-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--mute)}',
  '.rk-br.cut .vl small{color:var(--violet-2)}',
  '.rk-mt{height:3px;border-radius:2px;background:var(--line-2);overflow:hidden;margin-top:6px;max-width:220px}',
  '.rk-mt>i{display:block;height:100%;background:var(--soft);border-radius:2px}',
  '.rk-br.cut .rk-mt>i{background:var(--violet)}',
  '.rk-bars{display:flex;flex-direction:column;gap:13px}',
  '.rk-bar{display:grid;grid-template-columns:minmax(0,1fr) 54px;gap:6px 12px;align-items:center}',
  '.rk-bar .lb{grid-column:1/-1;display:flex;flex-wrap:wrap;justify-content:space-between;gap:2px 10px;align-items:baseline;min-width:0}',
  '.rk-bar .lb b{font-size:13px;font-weight:600;color:var(--fg)}',
  '.rk-bar .lb span{font:500 10.5px/1.3 var(--f-mono);color:var(--mute)}',
  '.rk-bar .tr{position:relative;height:10px;border-radius:3px;background:var(--raise-2);overflow:hidden}',
  '.rk-bar .tr::before,.rk-bar .tr::after{content:"";position:absolute;top:0;bottom:0;width:1px;background:var(--bg);z-index:1}',
  '.rk-bar .tr::before{left:25%}.rk-bar .tr::after{left:50%}',
  '.rk-bar .tr>i{position:absolute;left:0;top:0;bottom:0;background:var(--soft);border-radius:3px}',
  '.rk-bar .tr>i.band{background:var(--violet-b);border:1px solid var(--violet);border-radius:3px}',
  '.rk-bar.acc .tr>i{background:var(--violet)}',
  '.rk-bar.fg .tr>i{background:var(--hi)}',
  '.rk-bar.mute .tr>i{background:var(--mute)}',
  '.rk-bar .vv{font:600 14px/1 var(--f-mono);color:var(--hi);text-align:right;white-space:nowrap}',
  '.rk-bar.acc .vv{color:var(--violet-2)}',
  '.rk-lead{margin:0;font-size:14.5px;line-height:1.45;color:var(--soft)}',
  '.rk-lead b{display:block;margin:6px 0 2px;font:600 32px/1.05 var(--f-mono);letter-spacing:-.02em;color:var(--violet-2)}',
  '.rk-f{margin:0;font:500 12px/1.6 var(--f-mono);color:var(--fg);background:var(--raise);border:1px solid var(--line);border-radius:9px;padding:9px 11px;overflow-wrap:anywhere}',
  '.rk-f em{font-style:normal;color:var(--violet-2)}',
  '.rk-prog{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}',
  '.rk-prog b{font:600 34px/1 var(--f-mono);color:var(--hi);letter-spacing:-.02em}',
  '.rk-prog b small{font-size:16px;color:var(--mute);font-weight:500;margin-left:2px}',
  '.rk-prog span{font-size:13px;color:var(--soft)}',
  '.rk-meter{height:6px;border-radius:3px;background:var(--raise-2);overflow:hidden}',
  '.rk-meter>i{display:block;height:100%;background:var(--violet);border-radius:3px}',
  '.rk-ed{border:1px solid var(--line);border-radius:var(--r);background:var(--panel);padding:12px 13px;display:flex;flex-direction:column;gap:10px;min-width:0}',
  '.rk-ed .hd{display:flex;justify-content:space-between;align-items:center;gap:8px;font:600 10px/1.2 var(--f-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--mute)}',
  '.rk-line{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;font:500 11.5px/1.45 var(--f-mono);color:var(--mute)}',
  '.rk-line b{color:var(--fg);font-weight:600}',
  '.rk-ed .fld input{font-family:var(--f-sans);font-size:15px}',
  '.rk-stack{display:flex;flex-direction:column;gap:12px;min-width:0}',
  '.rk-wait{font:500 12px/1.5 var(--f-mono);color:var(--mute);padding:6px 0}'
].join('');
function injectCss() { if (document.getElementById('risk-css')) return; var s = document.createElement('style'); s.id = 'risk-css'; s.textContent = CSS; document.head.appendChild(s); }
function typo(el) {
  if (!el || typeof document === 'undefined') return;
  var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, { acceptNode: function (n) { var p = n.parentNode; return p && /^(TEXTAREA|SCRIPT|STYLE|INPUT|OPTION)$/.test(p.nodeName) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; } }), n;
  while ((n = w.nextNode())) { var t = n.nodeValue, u = L.typo(t); if (u !== t) n.nodeValue = u; }
}
var usd = function (v) { return F.usd(v, 0); };
var pc = function (p) { return F.pct(p, 1); };
var kfmt = function (v) { return F.num(v / 1000, Math.abs(v) >= 1e5 ? 0 : 1) + ' k'; };
var sur100 = function (p) { return F.num(Math.round(100 * p), 0); };
/* « X fois sur 100 », sans écrire zéro pour une fréquence non nulle. */
var fois = function (p) { return p > 0 && p < 0.005 ? 'moins d’une fois sur 100' : sur100(p) + ' fois sur 100'; };
L.fois = fois;
var CACHE = {}, CACHE_KEYS = [];
function cachePut(k, v) { CACHE[k] = v; CACHE_KEYS.push(k); while (CACHE_KEYS.length > 16) delete CACHE[CACHE_KEYS.shift()]; }
var UI = { fan: 'hyp', edit: false, resetArm: false };

function getAcc() { return L.normAccount(T.store.get(K.acc, null)); }
function getSim(set) { return L.normSim(T.store.get(K.sim, {}), set || T.settings.get()); }
function setSim(patch) { T.store.set(K.sim, Object.assign({}, T.store.get(K.sim, {}) || {}, patch)); }
function getRules() { return L.normRules(T.store.get(K.rules, null)); }

/* Barres sur une échelle absolue de 0 à 100 : une probabilité ne s’étire pas pour remplir le cadre. */
function bars(items) {
  return h('div', { class: 'rk-bars' }, items.map(function (it) {
    var band = fin(it.lo) && fin(it.hi) && it.hi - it.lo > 1e-6, tr = h('div', { class: 'tr' });
    tr.appendChild(band ? h('i', { class: 'band', style: 'left:' + (100 * clamp(it.lo, 0, 1)) + '%;width:' + (100 * clamp(it.hi - it.lo, 0, 1)) + '%' }) : h('i', { style: 'width:' + (100 * clamp(it.v, 0, 1)) + '%' }));
    return h('div', { class: 'rk-bar' + (it.tone ? ' ' + it.tone : '') },
      h('div', { class: 'lb' }, h('b', null, it.label), it.note ? h('span', null, it.note) : null),
      tr, h('div', { class: 'vv' }, band ? sur100(it.lo) + '–' + sur100(it.hi) : sur100(it.v)));
  }));
}
function switchSvg(open) {
  return open
    ? '<svg width="30" height="28" viewBox="0 0 30 28" aria-hidden="true"><line x1="15" y1="0" x2="15" y2="6" stroke="var(--line-2)" stroke-width="1.5"/><line x1="15" y1="22" x2="15" y2="28" stroke="var(--line-2)" stroke-width="1.5"/><line x1="15" y1="22" x2="26" y2="8" stroke="var(--violet)" stroke-width="2" stroke-linecap="round"/><circle cx="15" cy="6" r="2.8" fill="var(--panel)" stroke="var(--violet)" stroke-width="1.4"/><circle cx="15" cy="22" r="2.8" fill="var(--violet)"/></svg>'
    : '<svg width="30" height="28" viewBox="0 0 30 28" aria-hidden="true"><line x1="15" y1="0" x2="15" y2="28" stroke="var(--line-2)" stroke-width="1.5"/><line x1="15" y1="6" x2="15" y2="22" stroke="var(--fg)" stroke-width="2" stroke-linecap="round"/><circle cx="15" cy="6" r="2.8" fill="var(--panel)" stroke="var(--fg)" stroke-width="1.4"/><circle cx="15" cy="22" r="2.8" fill="var(--fg)"/></svg>';
}
function seg(label, opts, value, onChange, hint) {
  return h('div', { class: 'fld full' }, h('label', null, label), U.seg({ options: opts, value: value, onChange: onChange, aria: label }), hint ? h('span', { class: 'hint' }, hint) : null);
}

/* ---------- Onglet « Compte » ---------- */
function renderCompte(root, ctx) {
  var set = ctx.settings, acc = getAcc(), inst = set.instrument || 'MNQ';
  var out = h('div', { class: 'sec' });
  function save(patch, keepPreset) { var a = L.patchAccount(T.store.get(K.acc, null), patch); if (!keepPreset) a.preset = 'perso'; T.store.set(K.acc, a); }
  function num(label, unit, key, o) {
    o = o || {};
    return Object.assign({ label: label, unit: unit, value: acc[key], onChange: function (v) {
      var before = getAcc(); save((function () { var p = {}; p[key] = v; return p; })(), !!o.keepPreset);
      if (o.structural && (before[key] == null) !== (v == null)) ctx.rerender(); else paint();
    } }, o);
  }

  var s1 = U.section('Prérèglages', 'modifiables');
  s1.appendChild(U.chips({ options: L.PRESET_IDS.map(function (id) { return { v: id, label: L.PRESETS[id].label }; }).concat([{ v: 'perso', label: 'Perso' }]), value: acc.preset,
    onChange: function (v) {
      if (v === 'perso') { save({}, false); ctx.rerender(); return; }
      T.store.set(K.acc, L.applyPreset(v)); T.toast('Prérèglage ' + L.PRESETS[v].label + ' appliqué : à vérifier auprès de ta firme'); ctx.rerender();
    } }));
  s1.appendChild(h('p', { class: 'note warn' }, U.pill('à vérifier', 'acc'), ' Les prérèglages reprennent des règles courantes du marché des prop firms, pas celles d’une firme précise. Elles changent souvent : vérifie chaque chiffre auprès de ta firme, puis corrige-le ici.'));
  root.appendChild(s1);

  var trailing = acc.dd !== 'static', ddDef = L.DD.filter(function (d) { return d.v === acc.dd; })[0];
  var list = [
    num('Taille du compte', '$', 'size', { min: 1000, max: 1e7 }),
    num('Objectif de profit', '$', 'target', { min: 1, max: 1e7 }),
    num('Perte maximale', '$', 'maxLoss', { min: 1, max: 1e7, hint: 'le drawdown autorisé' }),
    num('Contrats maximum', inst, 'maxContracts', { min: 1, max: 10000, hint: 'en contrats ' + inst }),
    seg('Type de drawdown', L.DD.map(function (d) { return { v: d.v, label: d.label }; }), acc.dd, function (v) { save({ dd: v }); ctx.rerender(); }, ddDef.hint),
    trailing ? num('Seuil où le suiveur se fige', '$', 'lockAt', { min: 0, max: 1e7, full: true, hint: 'le plus haut à partir duquel le plancher ne monte plus ; souvent taille + perte max + un petit montant' }) : null,
    num('Limite journalière', '$', 'dailyLimit', { allowEmpty: true, structural: true, min: 1, max: 1e7, placeholder: 'aucune', hint: 'perte max du jour, facultative : vide si ta firme n’en a pas' }),
    num('Règle de consistance', '%', 'consistency', { allowEmpty: true, min: 1, max: 100, placeholder: 'aucune', hint: 'meilleur jour ≤ ce % du profit' }),
    acc.dailyLimit ? seg('Si la limite journalière est touchée', [{ v: 'pause', label: 'La journée s’arrête' }, { v: 'fail', label: 'Le compte échoue' }], acc.dailyMode, function (v) { save({ dailyMode: v }); ctx.rerender(); }) : null
  ].filter(Boolean);
  var s2 = U.section('Les règles du *compte*', acc.preset === 'perso' ? 'personnalisées' : 'prérèglage ' + L.PRESETS[acc.preset].label);
  s2.appendChild(U.card({ body: U.fields(list) }));
  root.appendChild(s2);

  var s3 = U.section('Où tu en es', 'à mettre à jour après chaque séance');
  s3.appendChild(U.card({ body: U.fields([
    num('Solde actuel', '$', 'balance', { keepPreset: true, min: 0, max: 1e8 }),
    num('Plus haut atteint', '$', 'high', { keepPreset: true, min: 0, max: 1e8, hint: acc.dd === 'eod' ? 'plus haut solde de clôture' : acc.dd === 'intraday' ? 'plus haut en séance, latent compris' : 'sans effet en statique' })
  ]) }));
  root.appendChild(s3);
  root.appendChild(out);

  function paint() {
    T.clear(out);
    var set2 = T.settings.get(), a = getAcc(), sp = getSim(set2), d = L.distances(a, set2.pointValue, sp.risk, sp.cost);
    if (d.distLiq <= 0) out.appendChild(U.callout([h('b', null, 'Compte liquidé selon ces règles. '), 'Le solde (' + usd(a.balance) + ') est au plancher ou dessous (' + usd(d.floor) + ').']));
    else if (d.distObj <= 0) out.appendChild(U.callout([h('b', null, 'Objectif atteint. '), 'Le solde (' + usd(a.balance) + ') dépasse l’objectif (' + usd(d.objective) + '). Vérifie la règle de consistance avant de demander le passage.']));
    var sh = h('div', { class: 'sh' }, h('h2', null, U.rich('Les *distances*')), h('span', null, L.ddLabel(a.dd)));
    out.appendChild(sh);
    out.appendChild(U.kpis([
      { label: 'Liquidation à', value: usd(d.floor), hint: d.trailing ? (d.locked ? 'plancher figé' : 'plancher suiveur') : 'plancher statique' },
      { label: 'Distance', value: usd(Math.max(0, d.distLiq)), tone: d.distLiq <= sp.risk ? 'neg' : null, hint: 'soit ' + F.num(Math.max(0, d.ptsLiq), 0) + ' pt ' + inst },
      { label: 'À ' + a.maxContracts + ' contrats', value: F.num(Math.max(0, d.ptsLiqMax), 2), unit: 'pt', hint: 'au plafond du compte' },
      { label: 'Objectif à', value: usd(Math.max(0, d.distObj)), tone: 'acc', hint: 'solde visé ' + usd(d.objective) },
      { label: 'Ratio', value: fin(d.ratio) ? F.num(d.ratio, 2) : '—', unit: fin(d.ratio) ? '×' : null, hint: 'à gagner par $ perdable' },
      { label: 'Pertes pleines', value: F.int(d.fullLosses), hint: 'de ' + usd(sp.risk + sp.cost) + ' chacune' },
      { label: 'Suiveur', value: !d.trailing ? '—' : d.locked ? 'figé' : usd(d.toLock), hint: !d.trailing ? 'drawdown statique' : d.locked ? 'plancher ' + usd(d.lockFloor) : 'à gagner pour le figer' },
      { label: 'Meilleur jour', value: d.dayCap ? usd(d.dayCap) : '—', hint: a.consistency ? '≤ ' + F.num(a.consistency, 0) + ' % du profit' : 'pas de consistance' }
    ], 4));

    var lv = [{ price: d.objective, label: 'Objectif' }, { price: a.size, label: 'Départ', kind: 'mute', dash: true }, { price: d.floor, label: 'Plancher', dash: true }];
    if (d.trailing && a.high > a.size) lv.push({ price: a.high, label: 'Plus haut', kind: 'mute' });
    if (d.trailing && !d.locked) lv.push({ price: a.lockAt, label: 'Verrou', kind: 'mute', dash: true });
    out.appendChild(U.card({ title: 'Le compte, du plancher à l’objectif', meta: 'solde ' + usd(a.balance), body: [
      C.ladder({ levels: lv, price: a.balance, fmt: usd, height: 230 }),
      U.note('Le repère violet est ton solde. Les montants sont des soldes de compte, pas des prix de marché.')
    ] }));

    if (d.trailing) {
      var x0 = a.size, x1 = Math.max(a.size + a.target, a.lockAt + a.maxLoss * 0.25, a.high), pts = [], stp = [];
      for (var i = 0; i <= 48; i++) { var x = x0 + (x1 - x0) * i / 48; pts.push([x, Math.min(x, a.lockAt) - a.maxLoss]); stp.push([x, a.size - a.maxLoss]); }
      out.appendChild(U.card({ title: 'Où est ton plancher', meta: 'selon ton plus haut', body: [
        C.line({ series: [{ name: 'Ton plancher', points: pts, tone: 'violet' }, { name: 'Plancher statique', points: stp, tone: 'mute', dash: true }], x: { fmt: kfmt }, y: { fmt: kfmt },
          vlines: [{ x: a.high }], height: 180, ml: 52 }),
        U.note('Le plancher suit ton plus haut dollar pour dollar, puis se fige quand ce plus haut atteint ' + usd(a.lockAt) + '. Le pointillé vertical marque ton plus haut actuel (' + usd(a.high) + '). Le plancher ne redescend jamais : un gain rendu au marché rapproche la liquidation.')
      ] }));
    }

    var box = h('div', { class: 'rk-stack' });
    out.appendChild(U.card({ title: 'Le théorème, appliqué à ton compte', meta: 'arrêt optionnel', accent: true, body: box }));
    theorem(box, a, sp, ctx, d);
    typo(out);
  }
  paint();
}

function theorem(box, a, sp, ctx, d) {
  if (d.distLiq <= 0 || d.distObj <= 0) { box.appendChild(U.note(d.distLiq <= 0 ? 'Plus de distance à la liquidation : rien à calculer.' : 'L’objectif est atteint : la probabilité vaut 1.')); return; }
  var args = L.theoremArgs(a, sp), k1 = JSON.stringify(args.rules), k2 = JSON.stringify(args.friction);
  var fresh = a.balance === a.size && a.high === a.size;
  function draw(r1, r2) {
    T.clear(box);
    var hasRules = a.dd !== 'static' || (a.dailyLimit && a.dailyMode === 'fail');
    box.appendChild(h('p', { class: 'rk-lead' }, 'Sans avantage, ce compte se passe environ', h('b', null, fois(r2.pPass) + '.')));
    var items = [{ label: 'Le théorème seul', note: 'plancher fixe, sans frais', v: d.pTheorem, tone: 'fg' }];
    if (hasRules) items.push({ label: 'Avec les règles du compte', note: [a.dd !== 'static' ? L.ddLabel(a.dd) : null, a.dailyLimit && a.dailyMode === 'fail' ? 'limite du jour éliminatoire' : null].filter(Boolean).join(', '), v: r1.pPass });
    items.push({ label: 'Avec la friction', note: usd(sp.cost) + ' par trade', v: r2.pPass, tone: 'acc' });
    box.appendChild(bars(items));
    var A = Math.round(d.distLiq), B = Math.round(d.distObj);
    box.appendChild(h('p', { class: 'rk-f' }, fresh ? 'perte max ÷ (perte max + objectif)' : 'distance à la liquidation ÷ (distance à la liquidation + distance à l’objectif)', h('br'),
      '= ' + usd(A) + ' ÷ (' + usd(A) + ' + ' + usd(B) + ') = ', h('em', null, F.pct(d.pTheorem, 1))));
    var ex = L.expectancyR(L.zeroEdge(sp.win, sp.loss), sp.win, sp.loss, sp.cost, sp.risk), tr = r2.meanTradesRes;
    var lines = [
      '<b>Le théorème.</b> Sans avantage, le solde est une martingale : la probabilité d’atteindre l’objectif avant la liquidation ne dépend ni de la volatilité, ni du setup, ni du rapport gain/risque. Elle vaut la part de la distance qui te sépare du plancher.',
      '<b>La friction.</b> Chaque trade paie ' + T.esc(usd(sp.cost)) + ' : sans avantage, l’espérance par trade vaut −c/L = ' + T.esc(F.num(ex, 3)) + ' R, et elle se paie sur ' + T.esc(fin(tr) ? F.num(tr, 0) : '—') + ' trades en moyenne avant l’issue.'
    ];
    if (a.dd !== 'static') {
      var cont = L.pTrailing(0, 1, a.maxLoss, a.target, a.lockAt - a.size, a.balance - a.size, a.high - a.size);
      lines.push('<b>Le suiveur.</b> Un plancher qui monte avec ton plus haut prend des trajectoires que le plancher fixe aurait laissé vivre. La formule continue du suiveur intrajournalier (Lehoczky, 1977) donne ' + T.esc(sur100(cont)) + ' sur 100 sans frais' + (a.dd === 'eod' ? ' ; un suiveur de fin de journée se place entre ' + T.esc(sur100(cont)) + ' et ' + T.esc(sur100(d.pTheorem)) + '.' : '.'));
    }
    box.appendChild(U.prose(lines));
    box.appendChild(h('div', { class: 'rk-line' }, h('span', null, 'Simulation : ' + F.int(r2.n) + ' trajectoires, ' + usd(sp.risk) + ' de risque, ' + F.num(sp.win, 2) + ' R contre ' + F.num(sp.loss, 2) + ' R, taux sans avantage ' + pc(L.zeroEdge(sp.win, sp.loss)) + ', ' + sp.tpd + ' trades par jour, graine ' + sp.seed + '.'),
      U.button({ label: 'Régler dans Passage', small: true, kind: 'ghost', onClick: function () { ctx.setTab('passage'); } })));
    box.appendChild(U.note('Source : ALP nº 3, vingtième partie — a/(a+b), la probabilité de toucher la cible avant le stop, est le théorème d’arrêt optionnel (ici a = distance à la liquidation, b = distance à l’objectif) ; onzième partie — à dérive nulle, l’espérance vaut −c/L pour toute géométrie.'));
    typo(box);
  }
  if (CACHE[k1] && CACHE[k2]) { draw(CACHE[k1], CACHE[k2]); return; }
  box.appendChild(h('div', { class: 'rk-wait' }, 'Calcul de ' + F.int(args.friction.n) + ' trajectoires sans avantage…'));
  Promise.all([CACHE[k1] ? Promise.resolve(CACHE[k1]) : T.compute(riskSimulate, args.rules), CACHE[k2] ? Promise.resolve(CACHE[k2]) : T.compute(riskSimulate, args.friction)]).then(function (r) {
    cachePut(k1, r[0]); cachePut(k2, r[1]); if (box.isConnected) draw(r[0], r[1]);
  }, function (e) { if (box.isConnected) { T.clear(box); box.appendChild(U.note('Le calcul a échoué : ' + (e && e.message || e), true)); } });
}

/* ---------- Onglet « Aujourd’hui » ---------- */
var BR_TXT = {
  confirm: function (b, st) { return { t: 'Limites confirmées', s: b.open ? 'pas encore aujourd’hui : confirme-les ci-dessus' : 'confirmées, elles ne se relâchent plus', v: b.open ? 'non' : 'oui' }; },
  trades: function (b) { return { t: 'Trades du jour', s: b.open ? 'plafond atteint' : 'il en reste ' + (b.max - b.used), v: b.used + ' / ' + b.max, m: b.max > 0 ? b.used / b.max : 1 }; },
  pertes: function (b) { return { t: 'Pertes du jour', s: b.open ? 'nombre de pertes atteint : séance finie' : 'il en reste ' + (b.max - b.used) + ' avant l’arrêt', v: b.used + ' / ' + b.max, m: b.max > 0 ? b.used / b.max : 1 }; },
  stop: function (b, st) { return { t: 'Stop du jour', s: (st.stopSrc === 'compte' ? 'limite du compte, plus stricte que la tienne · ' : '') + (b.open ? 'atteint' : 'reste ' + usd(b.max - b.used)), v: usd(b.used) + ' / ' + usd(b.max), m: b.max > 0 ? b.used / b.max : 1 }; },
  prochain: function (b) { return { t: 'Prochain trade', s: b.open ? (b.max > 0 ? 'un stop plein ne tient plus dans les ' + usd(b.max) + ' restants' : 'plus aucun risque disponible') : 'un stop plein tient dans les ' + usd(b.max) + ' restants', v: usd(b.used) }; },
  refroid: function (b, st) { return { t: 'Refroidissement', s: fin(st.lastLoss) ? L.COOLDOWN_MIN + ' min après la perte de ' + L.hhmmOf(st.lastLoss) : L.COOLDOWN_MIN + ' min après chaque perte', v: b.open ? L.fmtClock(b.ms) : '—', cd: b.open }; },
  fenetre: function (b, st, set) { return { t: 'Fenêtre', s: 'de ' + set.winFrom + ' h à ' + set.winTo + ' h, ' + (set.tz === 'Europe/Paris' ? 'heure de Paris' : set.tz), v: b.open ? 'fermée' : 'ouverte' }; },
  compte: function (b, st) { return { t: 'Compte', s: b.open ? 'une perte pleine toucherait le plancher' : 'de marge avant la liquidation (solde saisi dans « Compte »)', v: usd(Math.max(0, b.max)) }; }
};
function reasonOf(b, st, set) {
  return {
    confirm: 'Tes limites du jour ne sont pas confirmées.', trades: 'Plafond de trades atteint.', pertes: 'Nombre de pertes du jour atteint.', stop: 'Stop du jour atteint.',
    prochain: st.riskLeft > 0 ? 'Un stop plein ne tient plus dans le risque restant : réduis la taille à ' + usd(st.riskLeft) + ' ou arrête.' : null,
    refroid: 'Refroidissement après une perte : encore ' + L.fmtClock(b.ms) + '.', fenetre: 'Hors de ta fenêtre (' + set.winFrom + ' h – ' + set.winTo + ' h).',
    compte: 'Une perte pleine toucherait le plancher de liquidation du compte.'
  }[b.id];
}
function renderJour(root, ctx) {
  var set0 = T.settings.get(), cur = null;
  var stateBox = h('div', { class: 'sec' }), confirmBox = h('div', { class: 'sec' }), circBox = h('div', { class: 'rk-stack' }), chartBox = h('div', { class: 'rk-stack' });
  root.appendChild(stateBox);
  var s2 = U.section('Tes limites du *jour*', 'réglages communs');
  var fl = function (label, unit, key, o) { return Object.assign({ label: label, unit: unit, value: set0[key], onChange: function (v) { var p = {}; p[key] = v; T.settings.set(p); } }, o); };
  s2.appendChild(U.card({ body: [U.fields([
    fl('Risque par trade', '$', 'riskPerTrade', { min: 1, max: 1e6, hint: 'un stop plein' }),
    fl('Stop du jour', '$', 'dailyStop', { min: 1, max: 1e7, hint: 'perte maximale de la séance' }),
    fl('Trades par jour', null, 'maxTradesDay', { min: 1, max: 50, hint: 'au plus' }),
    fl('Pertes par jour', null, 'maxLossesDay', { min: 1, max: 50, hint: 'arrêt à ce nombre' })
  ]), confirmBox] }));
  root.appendChild(s2);
  var s3 = U.section('Les *disjoncteurs*', 'un seul qui coupe suffit'); s3.appendChild(circBox); root.appendChild(s3);
  var s4 = U.section('La séance', 'P&L cumulé · heure de Paris'); s4.appendChild(chartBox); root.appendChild(s4);

  function compute() {
    var set = T.settings.get(), key = T.day.key(), snap = T.store.get(K.limits + key, null), done = !!T.day.get().done.risque;
    var st = L.dayState(T.journal.list(), set, getAcc(), Date.now(), { snap: snap, confirmed: done || !!snap, inWindow: T.time.inWindow(set.winFrom, set.winTo, set.tz) });
    st.set = set; st.snap = snap; st.doneAt = T.day.get().done.risque || (snap && snap.at);
    return st;
  }
  function paint() {
    cur = compute(); var st = cur, set = st.set, lim = st.limits;
    T.clear(stateBox);
    var cut = st.breakers.filter(function (b) { return b.open; }), go = st.canTrade;
    var reasons = cut.map(function (b) { return reasonOf(b, st, set); }).filter(Boolean);
    stateBox.appendChild(h('div', { class: 'rk-state ' + (go ? 'go' : 'stop'), role: 'status' },
      h('div', { class: 'k' }, (go ? 'Tous les disjoncteurs passent' : cut.length + ' disjoncteur' + (cut.length > 1 ? 's coupent' : ' coupe')) + ' · ' + T.time.hhmm('Europe/Paris') + ' à Paris'),
      h('div', { class: 't' }, U.rich(go ? 'Tu peux *trader*.' : 'Arrête-*toi*.')),
      h('div', { class: 's' }, go ? 'Il te reste ' + usd(st.riskLeft) + ' de risque, ' + (lim.maxTradesDay - st.taken) + ' trade' + (lim.maxTradesDay - st.taken > 1 ? 's' : '') + ' et ' + (lim.maxLossesDay - st.losses) + ' perte' + (lim.maxLossesDay - st.losses > 1 ? 's' : '') + ' avant l’arrêt. Un seul setup écrit d’avance à la fois.' : reasons.slice(0, 3).join(' '))));
    stateBox.appendChild(U.kpis([
      { label: 'P&L du jour', value: F.usd(st.pnl, 0, true), tone: st.pnl < 0 ? 'neg' : null, hint: st.closed + ' clos · ' + st.open + ' ouvert' + (st.open > 1 ? 's' : '') },
      { label: 'Pertes', value: st.losses + ' / ' + lim.maxLossesDay, tone: st.losses >= lim.maxLossesDay ? 'neg' : null, hint: st.wins + ' gagnant' + (st.wins > 1 ? 's' : '') },
      { label: 'Trades', value: st.taken + ' / ' + lim.maxTradesDay, tone: st.taken >= lim.maxTradesDay ? 'neg' : null, hint: 'pris aujourd’hui' },
      { label: 'Risque restant', value: usd(st.riskLeft), tone: st.riskLeft < lim.riskPerTrade ? 'neg' : 'acc', hint: 'stop ' + usd(st.stopEff) }
    ], 4));

    T.clear(confirmBox);
    if (st.doneAt) {
      confirmBox.appendChild(h('div', { class: 'rk-line' }, U.pill('confirmées', 'acc'), h('span', null, 'à ' + L.hhmmOf(st.doneAt) + '. Jusqu’à minuit (heure de Paris), tu peux les resserrer, pas les relâcher.')));
      if (st.loosened.length) {
        var nm = { riskPerTrade: 'risque par trade', maxTradesDay: 'trades par jour', maxLossesDay: 'pertes par jour', dailyStop: 'stop du jour' };
        confirmBox.appendChild(U.note('Relâché depuis la confirmation : ' + st.loosened.map(function (k) { return nm[k] + ' (' + (k === 'riskPerTrade' || k === 'dailyStop' ? usd(st.snap[k]) + ' → ' + usd(set[k]) : st.snap[k] + ' → ' + set[k]) + ')'; }).join(', ') + '. La valeur confirmée reste appliquée aujourd’hui.', true));
      }
    } else {
      confirmBox.appendChild(U.button({ label: 'Je confirme mes limites du jour', kind: 'acc', onClick: function () {
        var s = T.settings.get(), snap = { at: Date.now() }; L.LIMIT_KEYS.forEach(function (k) { snap[k] = s[k]; });
        T.store.set(K.limits + T.day.key(), snap); T.day.mark('risque'); T.toast('Limites du jour confirmées'); paint();
      } }));
      confirmBox.appendChild(U.note('La confirmation coche l’étape « Risque et taille » de la carte de séance. Ensuite, les limites ne se relâchent plus avant demain.'));
    }

    T.clear(circBox);
    circBox.appendChild(h('div', { class: 'rk-circ' }, st.breakers.map(function (b) {
      var x = BR_TXT[b.id](b, st, set);
      return h('div', { class: 'rk-br' + (b.open ? ' cut' : '') },
        h('div', { class: 'rk-sw' }, h('i'), h('span', { html: switchSvg(b.open) }), h('i')),
        h('div', { class: 'tx' }, h('b', null, x.t), h('span', null, x.s), fin(x.m) ? h('div', { class: 'rk-mt' }, h('i', { style: 'width:' + (100 * clamp(x.m, 0, 1)) + '%' })) : null),
        h('div', { class: 'vl' }, h('span', x.cd ? { 'data-cd': '1' } : null, x.v), h('small', null, b.open ? 'coupe' : 'passe')));
    })));
    circBox.appendChild(U.note('Un disjoncteur coupe le circuit dès que sa limite est atteinte. Le stop du jour retenu est le plus strict de ton stop et de la limite journalière du compte ; le refroidissement de ' + L.COOLDOWN_MIN + ' minutes suit chaque perte inscrite au journal.'));

    T.clear(chartBox);
    if (!st.closedRows.length) {
      chartBox.appendChild(U.empty({ title: 'Aucun trade clos aujourd’hui', text: 'Les trades inscrits au journal avec leur résultat s’ajoutent ici, cumulés, face à ton stop du jour. Les disjoncteurs les lisent au même endroit.', action: U.button({ label: 'Ouvrir le journal', small: true, onClick: function () { T.nav.go('journal'); } }) }));
    } else {
      var cum = 0, pts = [[0, 0]], labs = ['début'];
      st.closedRows.forEach(function (r, i) { cum += r.pnl; pts.push([i + 1, cum]); labs.push(L.hhmmOf(fin(r.closedAt) ? r.closedAt : r.at)); });
      chartBox.appendChild(U.card({ body: [C.line({ series: [{ name: 'P&L cumulé', points: pts, tone: 'violet', area: true }], x: { type: 'cat', labels: labs }, y: { fmt: usd, zero: true },
        hlines: [{ y: -st.stopEff, label: 'stop du jour', tone: 'mute' }], height: 190, ml: 54 }),
        U.note(st.closed + ' trade' + (st.closed > 1 ? 's' : '') + ' clos, ' + F.usd(st.pnl, 0, true) + ' net de frais. La ligne pointillée est le stop retenu (' + usd(st.stopEff) + ').')] }));
    }
    typo(stateBox); typo(confirmBox); typo(circBox); typo(chartBox);
  }
  paint();
  var un = [T.journal.on(paint), T.store.on('settings', paint), T.store.on(K.acc, paint), T.day.on(paint)], ticks = 0;
  var iv = setInterval(function () {
    if (!stateBox.isConnected) return; ticks++;
    if (cur && cur.cooldownMs > 0) {
      var left = cur.lastLoss + L.COOLDOWN_MIN * 60000 - Date.now(), el = circBox.querySelector('[data-cd]');
      if (left <= 0) { paint(); return; }
      if (el) el.textContent = L.fmtClock(left);
    }
    if (ticks % 30 === 0) paint();
  }, 1000);
  return function () { un.forEach(function (f) { f(); }); clearInterval(iv); };
}

/* ---------- Onglet « Passage » ---------- */
function renderPassage(root, ctx) {
  var set = ctx.settings, sp = getSim(set), acc = getAcc(), inst = set.instrument || 'MNQ';
  var der = h('div', { class: 'rk-stack' }), out = h('div', { class: 'sec' }), timer = null, runKey = null;
  function changed() { sp = getSim(T.settings.get()); acc = getAcc(); paintDer(); clearTimeout(timer); timer = setTimeout(run, 280); }
  function sf(label, unit, key, o) {
    o = o || {};
    var val = key === 'p' ? Math.round(sp.p * 10000) / 100 : Math.round(sp[key] * 1000) / 1000;
    return Object.assign({ label: label, unit: unit, value: val, onChange: function (v) { var p = {}; p[key] = key === 'p' ? v / 100 : (o.int ? Math.round(v) : v); setSim(p); changed(); } }, o);
  }
  var s1 = U.section('Ton *hypothèse*', 'valeurs de départ arbitraires');
  s1.appendChild(U.card({ body: [U.fields([
    sf('Taux de réussite', '%', 'p', { min: 0, max: 100 }),
    sf('Gain moyen', 'R', 'win', { min: 0.05, max: 50 }),
    sf('Perte', 'R', 'loss', { min: 0.05, max: 10, hint: 'un stop plein vaut 1 R' }),
    sf('Risque par trade', '$', 'risk', { min: 1, max: 1e6 }),
    sf('Trades par jour', null, 'tpd', { min: 1, max: 20, int: true }),
    sf('Coût par trade', '$', 'cost', { min: 0, max: 1e4, hint: 'commission × contrats + glissement' }),
    sf('Jours max', 'j', 'days', { min: 1, max: 120, int: true, hint: 'durée de l’évaluation' }),
    sf('Graine', null, 'seed', { min: 1, max: 1e9, int: true, hint: 'même graine, mêmes tirages' })
  ]), der] }));
  var jr = L.fromJournal(T.journal.list(), set.riskPerTrade);
  if (jr) {
    s1.appendChild(h('div', { class: 'rk-line' }, h('span', null, 'Ton journal : ', h('b', null, jr.n + ' trades'), ', réussite ' + pc(jr.p) + ' ± ' + F.num(100 * jr.hw, 1) + ' pt, gain ' + F.num(jr.win, 2) + ' R, perte ' + F.num(jr.loss, 2) + ' R.'),
      U.button({ label: 'Reprendre ces chiffres', small: true, onClick: function () { setSim({ p: Math.round(jr.p * 1e4) / 1e4, win: Math.round(jr.win * 100) / 100, loss: Math.round(jr.loss * 100) / 100, cost: 0 }); T.toast('Hypothèse reprise du journal, frais mis à zéro'); ctx.rerender(); } })));
    s1.appendChild(U.note('Tes R sont nets de frais : en les reprenant, le coût par trade passe à zéro pour ne pas le compter deux fois. Avant 619 décisions, un taux de réussite n’établit aucune compétence (ALP nº 3, résumé).'));
  } else s1.appendChild(U.note('Avec au moins dix trades clos au journal, gagnants et perdants, tu pourras reprendre ici tes propres chiffres. En attendant, les valeurs ci-dessus sont des hypothèses, pas des mesures.'));
  root.appendChild(s1);

  var s2 = U.section('Les règles du *compte*', 'les mêmes que dans « Compte »');
  function af(label, unit, key, o) { return Object.assign({ label: label, unit: unit, value: acc[key], onChange: function (v) { var p = {}; p[key] = v; var a = L.patchAccount(T.store.get(K.acc, null), p); a.preset = 'perso'; T.store.set(K.acc, a); if (o && o.structural) ctx.rerender(); else changed(); } }, o || {}); }
  var trailing = acc.dd !== 'static';
  s2.appendChild(U.card({ body: U.fields([
    af('Objectif de profit', '$', 'target', { min: 1, max: 1e7 }),
    af('Perte maximale', '$', 'maxLoss', { min: 1, max: 1e7 }),
    seg('Drawdown', L.DD.map(function (d) { return { v: d.v, label: d.label }; }), acc.dd, function (v) { var a = L.patchAccount(T.store.get(K.acc, null), { dd: v }); a.preset = 'perso'; T.store.set(K.acc, a); ctx.rerender(); }),
    trailing ? af('Verrou du suiveur', '$', 'lockAt', { min: 0, max: 1e7, hint: 'plus haut où il se fige' }) : null,
    af('Limite journalière', '$', 'dailyLimit', { allowEmpty: true, structural: true, min: 1, max: 1e7, placeholder: 'aucune', hint: 'facultative' }),
    acc.dailyLimit ? seg('Si elle est touchée', [{ v: 'pause', label: 'Journée finie' }, { v: 'fail', label: 'Échec' }], acc.dailyMode, function (v) { var a = L.patchAccount(T.store.get(K.acc, null), { dailyMode: v }); a.preset = 'perso'; T.store.set(K.acc, a); ctx.rerender(); }) : null
  ].filter(Boolean)) }));
  s2.appendChild(U.note('La simulation part d’un compte neuf de ' + usd(acc.size) + ' : objectif à ' + usd(acc.size + acc.target) + ', liquidation à ' + usd(acc.size - acc.maxLoss) + (trailing ? ', plancher suiveur figé à ' + usd(acc.lockAt - acc.maxLoss) : '') + '.'));
  root.appendChild(s2);
  root.appendChild(out);

  function paintDer() {
    T.clear(der);
    var ps = L.equilibrium(sp.win, sp.loss, sp.cost, sp.risk), p0 = L.zeroEdge(sp.win, sp.loss), ex = L.expectancyR(sp.p, sp.win, sp.loss, sp.cost, sp.risk);
    der.appendChild(U.kpis([
      { label: 'Espérance', value: F.r(ex, 3), tone: ex > 0 ? 'acc' : 'neg', hint: 'frais compris' },
      { label: 'Équilibre', value: pc(ps), hint: 'la loi nulle' },
      { label: 'Ton écart', value: F.num(100 * (sp.p - ps), 1, 'pt', true), tone: sp.p > ps ? 'acc' : 'neg', hint: 'sur l’équilibre' },
      { label: 'Sans avantage', value: pc(p0), hint: 'gain brut nul' }
    ], 4));
    der.appendChild(h('p', { class: 'rk-f' }, 'équilibre = (perte + coût/risque) ÷ (gain + perte)', h('br'), '= (' + F.num(sp.loss, 2) + ' + ' + F.num(sp.cost / sp.risk, 4) + ') ÷ (' + F.num(sp.win, 2) + ' + ' + F.num(sp.loss, 2) + ') = ', h('em', null, pc(ps))));
    typo(der);
  }
  function run() {
    var ps = L.equilibrium(sp.win, sp.loss, sp.cost, sp.risk), p0 = L.zeroEdge(sp.win, sp.loss);
    var A = [L.simArgs(sp, acc, sp.p, sp.cost), L.simArgs(sp, acc, clamp(ps, 0, 1), sp.cost), L.simArgs(sp, acc, p0, sp.cost, { fan: false, keep: 0 })];
    var keys = A.map(function (x) { return JSON.stringify(x); }), key = keys.join('|'); runKey = key;
    if (keys.every(function (k) { return CACHE[k]; })) { draw(CACHE[keys[0]], CACHE[keys[1]], CACHE[keys[2]]); return; }
    T.clear(out); out.appendChild(U.card({ body: h('div', { class: 'rk-wait' }, 'Simulation de 3 × 5 000 évaluations…') }));
    Promise.all(A.map(function (x, i) { return CACHE[keys[i]] ? Promise.resolve(CACHE[keys[i]]) : T.compute(riskSimulate, x); })).then(function (r) {
      r.forEach(function (x, i) { cachePut(keys[i], x); });
      if (out.isConnected && runKey === key) draw(r[0], r[1], r[2]);
    }, function (e) { if (out.isConnected) { T.clear(out); out.appendChild(U.note('La simulation a échoué : ' + (e && e.message || e), true)); } });
  }
  function draw(hy, nu, sa) {
    T.clear(out);
    var ps = L.equilibrium(sp.win, sp.loss, sp.cost, sp.risk), p0 = L.zeroEdge(sp.win, sp.loss);
    var fm = L.formulaNull(acc.maxLoss, acc.target, acc.dd, acc.lockAt - acc.size);
    out.appendChild(h('div', { class: 'sh' }, h('h2', null, U.rich('Le *verdict* simulé')), h('span', null, F.int(hy.n) + ' trajectoires · graine ' + sp.seed)));
    out.appendChild(U.kpis([
      { label: 'Réussite', value: pc(hy.pPass), tone: 'acc', hint: 'loi nulle ' + pc(nu.pPass) },
      { label: 'Échec', value: pc(hy.pFail), tone: 'neg', hint: 'loi nulle ' + pc(nu.pFail) },
      { label: 'Ni l’un ni l’autre', value: pc(hy.pNone), hint: 'après ' + sp.days + ' jours' },
      { label: 'Jours médians', value: fin(hy.medPass) ? F.num(hy.medPass, 0) : '—', unit: fin(hy.medPass) ? 'j' : null, hint: fin(hy.medFail) ? 'échec : ' + F.num(hy.medFail, 0) + ' j' : 'jusqu’à la réussite' }
    ], 4));
    var dlt = hy.pPass - nu.pPass;
    out.appendChild(U.callout([
      'Avec tes chiffres, l’évaluation se passe ', h('b', null, fois(hy.pPass)), '. Le même compte tradé à espérance nulle (la loi nulle) se passe ', h('b', null, fois(nu.pPass)),
      ', et sans le moindre avantage, frais payés, ', h('b', null, fois(sa.pPass)), '. ',
      Math.abs(sp.p - ps) < 5e-4 ? 'Ton hypothèse est l’équilibre lui-même : elle ne porte aucun avantage, et la simulation le retrouve.' : sp.p < ps ? 'Ton taux est sous l’équilibre : faire moins bien que la loi nulle n’est pas un accident, c’est l’arithmétique.' : 'Ton hypothèse ajoute ' + F.num(100 * dlt, 1) + ' points à la loi nulle ; tout l’écart repose sur un taux de réussite que seul un échantillon peut établir.'
    ]));
    var bx = U.card({ title: 'Probabilité de réussite', meta: 'sur 100 évaluations', body: [bars([
      { label: 'Ton hypothèse', note: 'réussite ' + pc(sp.p), v: hy.pPass, tone: 'acc' },
      { label: 'Loi nulle', note: 'équilibre ' + pc(ps), v: nu.pPass, tone: 'fg' },
      { label: 'Sans avantage', note: pc(p0) + ', frais payés', v: sa.pPass },
      { label: 'Formule d’arrêt optionnel', note: 'sans échéance ni frais', v: fm.v, lo: fm.lo, hi: fm.hi, tone: 'mute' }
    ]), U.note(acc.dd === 'static' ? 'La formule vaut perte max ÷ (perte max + objectif) = ' + usd(acc.maxLoss) + ' ÷ (' + usd(acc.maxLoss) + ' + ' + usd(acc.target) + ').' : acc.dd === 'intraday' ? 'La formule est celle du plancher suiveur continu (Lehoczky, 1977), verrou compris ; sans suiveur elle vaudrait ' + sur100(acc.maxLoss / (acc.maxLoss + acc.target)) + '.' : 'Un suiveur de fin de journée n’a pas de forme fermée : il se place entre le suiveur continu (' + sur100(fm.lo) + ') et le plancher fixe (' + sur100(fm.hi) + ').')] });
    out.appendChild(bx);

    var rowsT = [{ k: 'Ton hypothèse', p: sp.p, r: hy }, { k: 'Loi nulle', p: ps, r: nu }, { k: 'Sans avantage', p: p0, r: sa }];
    out.appendChild(U.table({ cols: [
      { k: 'k', label: 'Scénario' }, { k: 'p', label: 'Taux', align: 'r', fmt: function (v) { return pc(v); } },
      { k: 'r', label: 'Réussite', align: 'r', fmt: function (v) { return pc(v.pPass); } }, { k: 'r', label: 'Échec', align: 'r', fmt: function (v) { return pc(v.pFail); } },
      { k: 'r', label: 'Échéance', align: 'r', fmt: function (v) { return pc(v.pNone); } }, { k: 'r', label: 'Jours méd.', align: 'r', fmt: function (v) { return fin(v.medPass) ? F.num(v.medPass, 0) : '—'; } },
      { k: 'r', label: 'Trades moy.', align: 'r', fmt: function (v) { return F.num(v.meanTrades, 0); } }
    ], rows: rowsT, rowClass: function (r) { return r.k === 'Ton hypothèse' ? 'sel' : null; } }));

    var nodes = [{ id: 'all', label: 'Évaluations', col: 0 }], links = [];
    [['ok', 'Réussite', hy.pass, 'violet'], ['g', 'Échec après un gain', hy.cause.gain, 'mute'], ['nv', 'Échec sans gain', hy.cause.never, 'mute'], ['dl', 'Échec, limite du jour', hy.cause.daily, 'mute'], ['na', 'À l’échéance', hy.none, 'mute']]
      .forEach(function (x) { if (x[2] > 0) { nodes.push({ id: x[0], label: x[1], col: 1, tone: x[3] }); links.push({ s: 'all', t: x[0], v: x[2], tone: x[3] === 'violet' ? 'violet' : null }); } });
    out.appendChild(U.card({ title: 'Où vont tes évaluations', meta: 'ton hypothèse', body: [C.sankey({ nodes: nodes, links: links, height: 230 }),
      U.note(hy.fail ? '« Après un gain » : le solde clos était passé au-dessus du départ avant la liquidation. C’est le cas de ' + pc(hy.cause.gain / hy.fail) + ' des échecs' + (acc.dd !== 'static' ? ' : avec un suiveur, le plancher était monté avec le gain, puis le gain a été rendu.' : ' : en statique, le plancher n’a pas bougé ; le gain a été rendu, puis le reste.') : 'Aucun échec dans cette simulation.')] }));

    var fanBox = h('div', { class: 'rk-stack' });
    out.appendChild(U.card({ title: 'Le solde, jour après jour', meta: '50 % et 90 % des trajectoires', body: [U.seg({ options: [{ v: 'hyp', label: 'Ton hypothèse' }, { v: 'nul', label: 'Loi nulle' }], value: UI.fan, onChange: function (v) { UI.fan = v; drawFan(); }, aria: 'Scénario affiché' }), fanBox] }));
    function drawFan() {
      T.clear(fanBox);
      var r = UI.fan === 'nul' ? nu : hy, add = function (a) { return a.map(function (v) { return v + acc.size; }); };
      var hl = [{ y: acc.size + acc.target, label: 'objectif', tone: 'violet' }, { y: acc.size - acc.maxLoss, label: 'plancher de départ', tone: 'mute' }];
      if (acc.dd !== 'static' && acc.lockAt - acc.maxLoss > acc.size - acc.maxLoss + acc.maxLoss * 0.2) hl.push({ y: acc.lockAt - acc.maxLoss, label: 'plancher figé', tone: 'mute' });
      fanBox.appendChild(C.fan({ q: { p05: add(r.q.p05), p25: add(r.q.p25), p50: add(r.q.p50), p75: add(r.q.p75), p95: add(r.q.p95) }, paths: r.paths.map(add), hlines: hl, fmt: kfmt, ml: 50, height: 230,
        xLabel: function (i) { return i === 0 ? 'départ' : 'jour ' + i; }, legend: [{ label: 'médiane', tone: 'fg' }, { label: '14 trajectoires', tone: 'mute' }] }));
      fanBox.appendChild(U.note('Une trajectoire terminée garde son solde final : réussie au-dessus de l’objectif, échouée au plancher. La bande sombre contient la moitié des comptes, la claire neuf sur dix.'));
    }
    drawFan();

    var cum = function (by, n) { var s = 0; return by.map(function (v, d) { s += v; return [d, s / n]; }); };
    out.appendChild(U.card({ title: 'Quand l’issue tombe', meta: 'part cumulée des évaluations', body: [C.line({ series: [
      { name: 'Réussite · hypothèse', points: cum(hy.passBy, hy.n), tone: 'violet' }, { name: 'Échec · hypothèse', points: cum(hy.failBy, hy.n), tone: 'fg' },
      { name: 'Réussite · loi nulle', points: cum(nu.passBy, nu.n), tone: 'violet', dash: true }, { name: 'Échec · loi nulle', points: cum(nu.failBy, nu.n), tone: 'mute', dash: true }
    ], x: { fmt: function (v) { return F.int(v) + ' j'; } }, y: { fmt: function (v) { return F.pct(v, 0); }, min: 0 }, height: 210, endDots: false })] }));

    var all = hy.passDays.concat(hy.failDays).filter(function (x) { return x > 0; }), refs = [];
    if (fin(hy.medPass)) refs.push({ x: hy.medPass, tone: 'violet' });
    if (fin(hy.medFail)) refs.push({ x: hy.medFail, tone: 'mute', dash: true });
    out.appendChild(U.card({ title: 'Jours jusqu’à l’issue', meta: 'ton hypothèse, médianes', body: [all.length ? C.hist({ values: all, bins: Math.min(sp.days, 40), min: 0.5, max: sp.days + 0.5, refs: refs, fmt: function (v) { return F.int(v); } }) : U.note('Aucune évaluation ne se termine dans le délai.'),
      U.note(F.int(hy.pass + hy.fail) + ' évaluations terminées sur ' + F.int(hy.n) + '. ' + (fin(hy.medPass) ? 'Trait violet : médiane des réussites, ' + F.num(hy.medPass, 0) + ' j. ' : '') + (fin(hy.medFail) ? 'Pointillé : médiane des échecs, ' + F.num(hy.medFail, 0) + ' j. ' : '') + (fin(hy.medPass) && fin(hy.medFail) ? (hy.medFail < hy.medPass ? 'Ici, les échecs tombent plus tôt que les réussites.' : hy.medFail > hy.medPass ? 'Ici, les réussites tombent plus tôt que les échecs.' : 'Les deux médianes coïncident.') : ''))] }));

    out.appendChild(U.note('Modèle : chaque trade finit au stop (−' + F.num(sp.loss, 2) + ' R) ou à l’objectif (+' + F.num(sp.win, 2) + ' R), frais déduits. Pendant un trade, l’excursion contraire d’un gagnant et l’excursion favorable d’un perdant suivent la loi d’un mouvement brownien sans dérive conditionné à son issue : c’est ce qui fait monter un suiveur intrajournalier sur un trade qui finit perdant. L’objectif se compte sur le solde clos. La règle de consistance, les jours minimum et le plafond de contrats ne sont pas simulés.'));
    out.appendChild(U.note('Loi nulle : la même simulation, avec les mêmes tirages, au taux d’équilibre (perte + coût/risque) ÷ (gain + perte) = ' + pc(ps) + ', où l’espérance nette par trade est nulle. Sans avantage : au taux perte ÷ (gain + perte) = ' + pc(p0) + ', où seuls les frais restent. Source : ALP nº 3, vingtième partie (a/(a+b), le théorème d’arrêt optionnel) et onzième partie (−c/L à dérive nulle).'));
    typo(out);
  }
  paintDer();
  run();
  return function () { clearTimeout(timer); };
}

/* ---------- Onglet « Règles » ---------- */
/* Treize jours : douze intervalles, divisibles par le pas d’étiquettes du graphique à toutes les largeurs courantes (1, 2, 3, 4, 6). */
var REG_DAYS = 13;
function autosize(ta) { if (!ta) return; var f = function () { ta.style.height = 'auto'; ta.style.height = (ta.scrollHeight + 2) + 'px'; }; ta.addEventListener('input', f); requestAnimationFrame(f); }
function renderRegles(root, ctx) {
  var rules = getRules(), key = K.check + T.day.key(), chk = T.store.get(key, {}) || {}, ad = L.adherence(chk, rules);
  var top = U.card({ accent: true, body: [
    h('div', { class: 'rk-prog' }, h('b', null, String(ad.kept), h('small', null, '/ ' + ad.total)), h('span', null, 'règles tenues aujourd’hui')),
    h('div', { class: 'rk-meter' }, h('i', { style: 'width:' + (ad.total ? 100 * ad.kept / ad.total : 0) + '%' })),
    U.note('Coche une règle quand la séance l’a respectée. Le soir, une case vide dit où regarder : c’est une information, pas une faute à cacher.')
  ] });
  root.appendChild(top);

  if (UI.edit) {
    var s = U.section('Modifier les *règles*', rules.length + ' règle' + (rules.length > 1 ? 's' : ''));
    var save = function (list) { T.store.set(K.rules, list); };
    rules.forEach(function (r, i) {
      var upd = function (patch) { var list = getRules(); list.forEach(function (x) { if (x.id === r.id) Object.assign(x, patch); }); save(list); };
      var ed;
      s.appendChild(ed = h('div', { class: 'rk-ed' },
        h('div', { class: 'hd' }, h('span', null, 'Règle ' + (i + 1)), U.button({ label: 'Supprimer', small: true, kind: 'ghost', onClick: function () { save(getRules().filter(function (x) { return x.id !== r.id; })); ctx.rerender(); } })),
        U.fields([
          { label: 'La règle', type: 'text', value: r.t, full: true, onChange: function (v) { upd({ t: v }); } },
          { label: 'Ce qu’elle veut dire', type: 'textarea', value: r.s, full: true, onChange: function (v) { upd({ s: v }); } },
          { label: 'Moment', type: 'select', value: r.m, full: true, options: L.MOMENTS.map(function (m) { return { v: m.v, label: m.label }; }), onChange: function (v) { upd({ m: v }); } }
        ])));
      autosize(ed.querySelector('textarea'));
    });
    s.appendChild(h('div', { class: 'row' },
      U.button({ label: 'Ajouter une règle', small: true, onClick: function () { var list = getRules(); list.push({ id: 'r' + Date.now().toString(36), m: 'journee', t: 'Nouvelle règle', s: '' }); save(list); ctx.rerender(); } }),
      U.button({ label: 'Terminer', small: true, kind: 'pri', onClick: function () { UI.edit = false; UI.resetArm = false; ctx.rerender(); } }),
      U.button({ label: UI.resetArm ? 'Confirmer : revenir aux ' + L.DEFAULT_RULES.length + ' règles' : 'Revenir aux règles de départ', small: true, kind: 'ghost', onClick: function () { if (!UI.resetArm) { UI.resetArm = true; ctx.rerender(); return; } UI.resetArm = false; save(L.DEFAULT_RULES.map(function (r) { return Object.assign({}, r); })); T.toast('Règles de départ rétablies'); ctx.rerender(); } })));
    root.appendChild(s);
  } else {
    if (!rules.length) root.appendChild(U.empty({ title: 'Aucune règle', text: 'La liste est vide. Ajoute tes règles, ou reviens aux règles de départ.', action: U.button({ label: 'Modifier la liste', small: true, onClick: function () { UI.edit = true; ctx.rerender(); } }) }));
    L.MOMENTS.forEach(function (m) {
      var items = rules.filter(function (r) { return r.m === m.v; }); if (!items.length) return;
      var kept = items.filter(function (r) { return chk[r.id]; }).length, sec = U.section(m.label, kept + ' / ' + items.length);
      sec.appendChild(U.checklist({ items: items.map(function (r) { return { id: r.id, t: r.t, s: r.s }; }), checked: chk, onToggle: function (id, on) {
        var c = T.store.get(key, {}) || {}; if (on) c[id] = true; else delete c[id]; T.store.set(key, c); ctx.rerender();
      } }));
      root.appendChild(sec);
    });
    if (rules.length) root.appendChild(h('div', { class: 'row' }, U.button({ label: 'Modifier la liste', small: true, onClick: function () { UI.edit = true; ctx.rerender(); } })));
  }

  var keys = L.pastKeys(T.day.key(), REG_DAYS), vals = [], seen = 0;
  keys.forEach(function (k, i) { var c = T.store.get(K.check + k, null); if (c && Object.keys(c).length && i < keys.length - 1) seen++; vals.push(c ? 100 * (L.adherence(c, rules).pct || 0) : 0); });
  var s2 = U.section('La *régularité*', 'les ' + REG_DAYS + ' derniers jours');
  if (seen >= 1) {
    s2.appendChild(U.card({ body: [C.bar({ cats: keys.map(function (k) { return k.slice(8) + '/' + k.slice(5, 7); }), series: [{ name: 'règles tenues', values: vals, tone: 'violet' }], fmt: function (v) { return F.num(v, 0) + ' %'; }, height: 170 }),
      U.note('Part des règles cochées chaque jour, rapportée à la liste actuelle. Un jour sans case cochée compte zéro.')] }));
  } else s2.appendChild(U.empty({ title: 'La régularité apparaîtra ici', text: 'Dès qu’un jour précédent porte des cases cochées, la part des règles tenues s’affiche jour par jour, sur les ' + REG_DAYS + ' derniers jours.' }));
  root.appendChild(s2);
  root.appendChild(U.note('Ces règles sont nées de deux comptes cramés, un de 150 k et un de 100 k. Elles ne promettent aucun avantage : elles empêchent qu’une mauvaise journée devienne la dernière.'));
}

/* =====================================================================
   3. Le desk
   ===================================================================== */
var HEAD = {
  compte: { k: 'Risque · Compte', t: 'Le compte, *avant* le marché.', l: 'Les règles de ta prop firm fixent la distance qui te sépare de la liquidation. Le théorème d’arrêt optionnel dit ce que vaut cette distance quand on n’a aucun avantage.' },
  jour: { k: 'Risque · Aujourd’hui', t: 'Aujourd’hui, *les limites*.', l: 'Les disjoncteurs du jour, lus dans ton journal. Un seul qui coupe suffit : la séance s’arrête.' },
  passage: { k: 'Risque · Passage', t: 'L’évaluation, *en probabilités*.', l: '5 000 évaluations simulées avec tes chiffres, comparées à la loi nulle : le même compte, tradé à espérance nulle.' },
  regles: { k: 'Risque · Règles', t: 'Les règles de *survie*.', l: 'Des règles nées de deux comptes cramés. Chacune se coche chaque jour où elle a tenu ; la liste se modifie à volonté.' }
};
var RENDER = { compte: renderCompte, jour: renderJour, passage: renderPassage, regles: renderRegles };
T.desk({
  id: 'risk', label: 'Risque', glyph: 'R', group: 'Exécution', order: 40,
  tabs: [{ id: 'compte', label: 'Compte' }, { id: 'jour', label: 'Aujourd’hui' }, { id: 'passage', label: 'Passage' }, { id: 'regles', label: 'Règles' }],
  render: function (root, ctx) {
    injectCss();
    var tab = HEAD[ctx.tab] ? ctx.tab : 'compte', hd = HEAD[tab];
    root.appendChild(U.page({ kicker: hd.k, title: hd.t, lede: hd.l }));
    root.appendChild(U.tabs({ tabs: this.tabs, value: tab, onChange: ctx.setTab }));
    var cleanup = RENDER[tab](root, ctx);
    typo(root);
    return cleanup;
  }
});
