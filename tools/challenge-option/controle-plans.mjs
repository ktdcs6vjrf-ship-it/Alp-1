// Contrôle des plans de compte (prop/challenge-option26.html et suivantes) : le moteur généralisé (tampon, séances entre deux
// demandes, profit de cycle, meilleur jour du cycle, premier plafond, montant visé) et l'option à tampon.
// Usage : node tools/challenge-option/controle-plans.mjs [page]
//  1. sans les champs nouveaux, demande() rend exactement l'ancienne règle (2 000 états tirés) ;
//  2. les plans modèles, joués par simCompte, redonnent au dollar près le banc indépendant comparer-100k-pro.mjs
//     (même logique réécrite ici), sur les mêmes tirages : LucidPro, Builder, LucidFlex (au plus tôt, au plafond), MFFU Pro
//     (tous les 14 jours, attendre 3 000 $) ;
//  3. cas écrits à la main : tampon, minimum, cadence, consistance du cycle, premier plafond, montant visé ;
//  4. option à tampon : valeur fermée contre intégration numérique, point mort, sommets du payoff.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
const ici = dirname(fileURLToPath(import.meta.url));
const page = process.argv[2] ? resolve(process.argv[2]) : join(ici, "../../prop/challenge-option26.html");
const html = readFileSync(page, "utf8"), a = html.indexOf("/* MODELE:DEBUT"), b = html.indexOf("/* MODELE:FIN */");
const M = new Function(html.slice(a, b) + "\nreturn {mulberry32,graine,journee,tradeStats,simCompte,lireCompte,demande,morceaux,kSat,seuilL,retrait,pointMort,gN,valeur,payoffPts,phi,Q};")();
let nOk = 0, nKo = 0;
const ok = (c, m) => { if (c) nOk++; else { nKo++; console.log("ÉCHEC  " + m); } };
const close = (x, y, tol, m) => ok(Math.abs(x - y) <= tol, `${m} : ${x} contre ${y}`);

// 1. l'ancienne règle, recopiée de la v25
const ancienne = (R, x, f, q, c0) => { if (!(q >= R.qd && x > c0)) return 0; const fA = R.lockPay ? Math.max(f, R.lock) : f, req = Math.min(R.r * x, R.wmax, x - fA - 1);
  return req >= R.minReq && (R.politique !== "cap" || req >= R.wmax - 1e-9) ? req : 0; };
{ const g = M.mulberry32(7); let diff = 0;
  for (let i = 0; i < 2000; i++) {
    const R = { D: 2000, lock: 100, qd: Math.floor(g() * 6), qmin: 150, r: [0.5, 1][i % 2], wmax: 500 + Math.floor(g() * 3000), minReq: Math.floor(g() * 1200), lockPay: g() < 0.5, politique: g() < 0.5 ? "asap" : "cap" };
    const x = -500 + g() * 6000, f = g() < 0.5 ? 100 : -2000 + g() * 2100, q = Math.floor(g() * 8), c0 = g() < 0.5 ? 0 : g() * 3000, dc = Math.floor(g() * 30), bd = g() * 900;
    const n = M.demande(R, x, f, q, c0, dc, bd, i % 3), o = ancienne(R, x, f, q, c0);
    if (Math.abs(n - o) > 1e-9 && !(n === 0 && o <= 0)) diff++; }
  ok(diff === 0, `sans les champs v26, demande() = ancienne règle sur 2 000 états (${diff} écarts)`); }

// 2. les plans modèles contre le banc indépendant
const D = 3000, OBJ = 6000, BUF = 3100, H = 250;
const FIRMS = {
  "LucidPro": { fee: 190.4, minJ: 1, ec: 0, k: "cyc", cyc: 750, days: 3, cons: 0.40, minPay: 500, cap: [2500, 3000], split: 0.90 },
  "Builder": { fee: 282, minJ: 1, ec: 0, k: "cyc", cyc: 1000, days: 2, cons: 0.50, minPay: 1000, cap: [3000, 3000], split: 0.80 },
  "LucidFlex au plus tôt": { fee: 150.5, minJ: 1, ec: 0.5, k: "flex", seuil: 500, split: 0.90 },
  "LucidFlex au plafond": { fee: 150.5, minJ: 1, ec: 0.5, k: "flex", seuil: 2500, split: 0.90 },
  "MFFU Pro tous les 14 j": { fee: 172, minJ: 2, ec: 0.5, k: "pro", seuil: 1000, split: 0.80 },
  "MFFU Pro attendre 3 000 $": { fee: 172, minJ: 2, ec: 0.5, k: "pro", seuil: 3000, split: 0.80 },
};
function reference(F, S, N) {
  const o = { pnl: 0, low: 0, sd: 0 }; let sum = 0;
  for (let i = 0; i < N; i++) {
    const g = M.mulberry32(M.graine(2026, i, 3));
    let t = 0, x = 0, Mx = 0, f = -D, lock = false, nd = 0, ok = false, best = 0;
    const step = () => { M.journee(S, g, o); g(); t++; if (x + o.low <= f) return false; x += o.pnl; if (x <= f) return false;
      if (!lock) { if (x > Mx) Mx = x; f = Math.min(Mx - D, 100); if (Mx - D >= 100) lock = true } return true };
    while (t < H) { if (!step()) break; nd++; if (o.pnl > best) best = o.pnl; if (x >= OBJ && nd >= F.minJ && (!F.ec || best <= F.ec * x)) { ok = true; break } }
    let cash = -F.fee, pays = 0;
    if (ok) { x = 0; Mx = 0; f = -D; lock = false; let cp = 0, bd = 0, nd2 = 0, q = 0, last = t;
      while (t < H && pays < 5) { if (!step()) break; cp += o.pnl; if (o.pnl > bd) bd = o.pnl; nd2++; if (o.pnl >= 200) q++;
        let req = 0;
        if (F.k === "cyc") { const r = Math.min(x - BUF, F.cap[pays ? 1 : 0]); if (r >= F.minPay && cp >= F.cyc && nd2 >= F.days && bd <= F.cons * cp) req = r; }
        else if (F.k === "pro") { if (t - last >= 10 && x - BUF >= F.seuil) req = x - BUF; }
        else { const r = Math.min(0.5 * x, 2500); if (q >= 5 && cp > 0 && r >= F.seuil) req = r; }
        if (!req) continue;
        cash += F.split * req; x -= req; pays++; cp = 0; bd = 0; nd2 = 0; q = 0; last = t; if (!lock) { lock = true; f = 100; } } }
    sum += cash; }
  return sum / N; }
const base = { H, maxPay: 5, D, lock: 100, obj: OBJ, seance: true, lockPay: true };
const PLANS = {
  "LucidPro": { ...base, fee: 190.4, cons: 0, minJ: 1, qd: 0, qmin: 0, r: 1, wmax: 3000, wmax1: 2500, minReq: 500, split: 0.9, buf: 3100, cad: 3, cyc: 750, fcons: 0.4, politique: "asap" },
  "Builder": { ...base, fee: 282, cons: 0, minJ: 1, qd: 0, qmin: 0, r: 1, wmax: 3000, minReq: 1000, split: 0.8, buf: 3100, cad: 2, cyc: 1000, fcons: 0.5, politique: "asap" },
  "LucidFlex au plus tôt": { ...base, fee: 150.5, cons: 0.5, minJ: 1, qd: 5, qmin: 200, r: 0.5, wmax: 2500, minReq: 500, split: 0.9, politique: "asap" },
  "LucidFlex au plafond": { ...base, fee: 150.5, cons: 0.5, minJ: 1, qd: 5, qmin: 200, r: 0.5, wmax: 2500, minReq: 500, split: 0.9, politique: "cap" },
  "MFFU Pro tous les 14 j": { ...base, fee: 172, cons: 0.5, minJ: 2, qd: 0, qmin: 0, r: 1, wmax: 1e9, minReq: 1000, split: 0.8, buf: 3100, cad: 10, politique: "asap" },
  "MFFU Pro attendre 3 000 $": { ...base, fee: 172, cons: 0.5, minJ: 2, qd: 0, qmin: 0, r: 1, wmax: 1e9, minReq: 1000, split: 0.8, buf: 3100, cad: 10, cible: 3000, politique: "cap" },
};
const S6 = { pv: 2, tick: 0.25, stop: 20, comm: 1, slip: 1, dStop: 0, dTgt: 0, c: 6, rr: 1.5, p: 0.45, n: 2 }, NN = 5000;
for (const k of Object.keys(PLANS)) {
  const R = PLANS[k], acc = M.simCompte(R, (g, o) => M.journee(S6, g, o), 2026, 0, NN), E = M.lireCompte(acc, R).E, Eref = reference(FIRMS[k], S6, NN);
  close(E, Eref, 1e-6, `${k} : le moteur de l'app redonne le banc indépendant (${E.toFixed(2)} $ par challenge)`); }

// 3. cas écrits à la main
{ const Pro = PLANS["MFFU Pro tous les 14 j"];
  ok(M.demande(Pro, 4099, 100, 0, 0, 10, 500, 0) === 0, "MFFU Pro : 4 099 $ de profit ne permettent pas 1 000 $ au-dessus du tampon");
  close(M.demande(Pro, 4100, 100, 0, 0, 10, 500, 0), 1000, 1e-9, "MFFU Pro : 4 100 $ donnent 1 000 $");
  ok(M.demande(Pro, 9000, 100, 0, 0, 9, 500, 0) === 0, "MFFU Pro : 9 séances depuis la dernière demande, c'est trop tôt");
  close(M.demande(Pro, 9000, 100, 0, 0, 10, 500, 0), 5900, 1e-9, "MFFU Pro : aucun plafond, tout ce qui dépasse le tampon (5 900 $)");
  const W = PLANS["MFFU Pro attendre 3 000 $"];
  ok(M.demande(W, 6000, 100, 0, 0, 10, 500, 0) === 0, "montant visé : 2 900 $ au-dessus du tampon, on attend");
  close(M.demande(W, 6100, 100, 0, 0, 10, 500, 0), 3000, 1e-9, "montant visé : 3 000 $ atteints, on demande");
  const LP = PLANS["LucidPro"];
  close(M.demande(LP, 6000, 100, 0, 0, 3, 300, 0), 2500, 1e-9, "LucidPro : le premier retrait plafonne à 2 500 $");
  close(M.demande(LP, 7000, 100, 0, 0, 3, 300, 1), 3000, 1e-9, "LucidPro : les suivants à 3 000 $");
  ok(M.demande(LP, 4000, 100, 0, 3200, 3, 400, 1) === 0, "LucidPro : 400 $ de meilleur jour pour 800 $ de cycle dépassent 40 %");
  close(M.demande(LP, 4000, 100, 0, 3200, 3, 320, 1), 900, 1e-9, "LucidPro : 320 $ sur 800 $ passent (900 $ au-dessus du tampon)");
  ok(M.demande(LP, 3800, 100, 0, 3100, 3, 200, 1) === 0, "LucidPro : un cycle de 700 $ est sous les 750 $ demandés");
  ok(M.demande(LP, 3900, 100, 0, 3000, 2, 200, 1) === 0, "LucidPro : deux séances dans le cycle, il en faut trois"); }

// 4. option à tampon : forme fermée contre intégration numérique (Simpson, 40 000 pas)
function simpson(fn, lo, hi, n) { const h = (hi - lo) / n; let s = fn(lo) + fn(hi); for (let i = 1; i < n; i++) s += fn(lo + i * h) * (i % 2 ? 4 : 2); return s * h / 3; }
for (const [nom, p] of [["MFFU Pro, sans plafond", { F: 172, r: 1, buf: 3100, wmax: 1e9, minReq: 1000, split: 0.8, cap: 0 }],
  ["Builder, plafond 3 000 $", { F: 282, r: 1, buf: 3100, wmax: 3000, minReq: 1000, split: 0.8, cap: 0 }],
  ["50 % du profit et tampon 1 000 $", { F: 100, r: 0.5, buf: 1000, wmax: 2000, minReq: 500, split: 0.9, cap: 0 }]]) {
  for (const [m, s] of [[2000, 2500], [5000, 1800], [-500, 3000]]) {
    const L = M.seuilL(p), fn = y => M.retrait(p, y) * M.phi((y - m) / s) / s;
    const num = simpson(fn, L, Math.max(L + 1, m + 12 * s), 40000), fe = M.gN(p, m, s);
    close(fe, num, 1e-6 * Math.max(1, num), `${nom} : valeur fermée à m = ${m}, s = ${s}`); }
  const be = M.pointMort(p);
  ok(be != null && Math.abs(M.retrait(p, be) - p.F) < 1e-6 || be === M.seuilL(p) && M.retrait(p, be) >= p.F, `${nom} : le point mort rembourse le prix (${be && be.toFixed(1)} $)`);
  const V = M.payoffPts(p, -3000, 12000); let bad = 0;
  for (let i = 1; i < V.length; i++) { const [x0, y0] = V[i - 1], [x1, y1] = V[i]; if (x1 - x0 < 1e-9) continue;
    for (const t of [0.25, 0.5, 0.75]) { const x = x0 + t * (x1 - x0); if (Math.abs(M.retrait(p, x) - p.F - (y0 + t * (y1 - y0))) > 1e-6) bad++; } }
  ok(bad === 0, `${nom} : les sommets du payoff suivent le retrait entre deux coudes (${bad} écarts)`); }
{ const p = { F: 150, r: 0.5, wmax: 2000, minReq: 500, split: 0.9, cap: 0 }, V = M.payoffPts(p, -2500, 6000), L = 1000, K = 4000, a = 0.45;
  const att = [[-2500, -150], [L, -150], [L, a * L - 150], [K, a * K - 150], [6000, a * K - 150]];
  ok(JSON.stringify(V.map(v => v.map(z => Math.round(z * 1e6) / 1e6))) === JSON.stringify(att), "sans tampon, les sommets sont ceux de la v25"); }

console.log(`\n${nOk} contrôles passés, ${nKo} échecs`);
process.exit(nKo ? 1 : 0);
