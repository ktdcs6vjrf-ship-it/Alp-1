// Contrôle du moteur de règles et des métriques de prop/challenge-option2.html (et suivantes).
// Le bloc MODELE de la page est extrait tel quel : on vérifie le code livré.
// Usage : node tools/challenge-option/controle-lucid.mjs [page]   (code de sortie 1 si un contrôle échoue)
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

const ici = dirname(fileURLToPath(import.meta.url));
const page = process.argv[2] ? resolve(process.argv[2]) : join(ici, "../../prop/challenge-option2.html");
const html = readFileSync(page, "utf8");
const a = html.indexOf("/* MODELE:DEBUT"), b = html.indexOf("/* MODELE:FIN */");
const M = new Function(html.slice(a, b) + `
return {mulberry32,graine,Phi,quant,tradeStats,journee,journeeJournal,moments,simCompte,lireCompte,simLibre,lireLibre,psr,minTRL,zinv,
        retrait,pointMort,kSat,seuilL,valeur,resume};`)();

let nOk = 0, nKo = 0;
const ok = (c, m) => { if (c) nOk++; else { nKo++; console.log("ÉCHEC  " + m); } };
const close = (x, y, tol, m) => ok(Math.abs(x - y) <= tol, `${m} : ${x} contre ${y}`);
const LUCID = { fee: 78.4, D: 2000, lock: 100, obj: 3000, cons: 0.5, minJ: 0, qd: 5, qmin: 150, r: 0.5, wmax: 2000, minReq: 500, split: 0.9,
  maxPay: 5, H: 250, seance: true, lockPay: true, politique: "asap" };
const R = o => Object.assign({}, LUCID, o);
const fixe = v => (g, o) => { g(); g(); o.pnl = v; o.low = Math.min(0, v); o.sd = 0; return o; };
const suite = seq => { let k = 0; return (g, o) => { g(); g(); const v = seq[Math.min(k++, seq.length - 1)]; o.pnl = v; o.low = Math.min(0, v); o.sd = 0; return o; }; };
const un = (Rr, day, keep) => M.simCompte(Rr, day, 1, 0, 1, null, keep || 1);

// 1. +200 $ par jour, retrait dès que possible : tout se calcule à la main
{ const A = un(R({}), fixe(200)), s = A.samples[0];
  ok(A.passe === 1 && A.tPass[0] === 15, `évaluation réussie au jour 15 (lu : ${A.tPass[0]})`);
  const ev = A.events[0], jours = [], montants = [];
  for (let i = 0; i < ev.length; i += 2) { jours.push(ev[i]); montants.push(ev[i + 1]); }
  ok(JSON.stringify(jours) === JSON.stringify([20, 25, 30, 35, 40]), `retraits aux jours 20, 25, 30, 35, 40 (lu : ${jours})`);
  const att = [500, 750, 875, 937.5, 968.75].map(x => x * 0.9);
  ok(montants.every((m, i) => Math.abs(m - att[i]) < 1e-9), `montants 90 % de 500, 750, 875, 937,5, 968,75 (lu : ${montants})`);
  close(A.cash[0], -78.4 + 3628.125, 1e-9, "trésorerie finale");
  ok(A.pay[5] === 1 && A.payKo[5] === 0, "cinq retraits, compte vivant");
  ok(s.fu.f[s.fu.f.length - 1] === 100, "plancher bloqué à +100 après la première demande"); }
// 2. même chemin, retrait au plafond seulement : 2 000 $ tous les dix jours
{ const A = un(R({ politique: "cap" }), fixe(200)), ev = A.events[0], jours = [];
  for (let i = 0; i < ev.length; i += 2) jours.push(ev[i]);
  ok(JSON.stringify(jours) === JSON.stringify([35, 45, 55, 65, 75]), `au plafond : jours 35, 45, 55, 65, 75 (lu : ${jours})`);
  close(A.cash[0], -78.4 + 5 * 1800, 1e-9, "au plafond : cinq fois 1 800 $"); }
// 3. -300 $ par jour : éteint au jour 7, en séance comme à la clôture
for (const seance of [true, false]) { const A = un(R({ seance }), fixe(-300));
  ok(A.koEval === 1 && A.samples[0].ko === 7, `perte continue : éteint au jour 7 (séance ${seance}, lu ${A.samples[0].ko})`); }
// 4. le plancher suit le plus haut de clôture
{ const A = un(R({}), suite([500, 500, 500, 500, -700, -700, -700, -700]));
  ok(A.koEval === 1 && A.samples[0].ko === 7, `trailing : éteint au jour 7 à -100 $ sous un plancher remonté à 0 (lu ${A.samples[0].ko})`);
  const seq = [700, 700, 700, 700, -1000, -1000, -1000, -1000];
  const Al = un(R({}), suite(seq)), Bf = un(R({ lock: 1e9 }), suite(seq));
  ok(Al.samples[0].ko === 7 && Bf.samples[0].ko === 6, `plus haut 2 800 : bloqué à +100 éteint au jour 7, sans blocage (plancher 800) au jour 6 (lu ${Al.samples[0].ko}, ${Bf.samples[0].ko})`); }
// 5. le blocage à +100
{ const A = un(R({}), suite([700, 700, 700, -1000, -1000, -1000]));
  ok(A.samples[0].ko === 5, `bloqué à +100 dès un plus haut de 2 100 : éteint au jour 5 (lu ${A.samples[0].ko})`); }
// 6. la cohérence d'évaluation : un jour à 3 000 impose 6 000 de profit
{ const A = un(R({}), suite([3000].concat(new Array(60).fill(100))));
  ok(A.tPass[0] === 31, `cohérence 50 % : réussite au jour 31 (lu ${A.tPass[0]})`);
  const B = un(R({ cons: 0 }), suite([3000].concat(new Array(60).fill(100))));
  ok(B.tPass[0] === 1, "sans cohérence : réussite au jour 1"); }
// 7. creux de séance contre clôture
{ const d = (g, o) => { g(); g(); o.pnl = 100; o.low = -2500; o.sd = 0; return o; };
  ok(un(R({ seance: true }), d).samples[0].ko === 1, "creux à -2 500 en séance : éteint");
  ok(un(R({ seance: false, H: 5 }), d).samples[0].ko === null, "le même jour, surveillé à la clôture : vivant"); }
// 8. demande minimale et partage dans la vue option
{ const p = { F: 78.4, D: 2000, b: -2000, cap: 0, r: 0.5, wmax: 2000, minReq: 500, split: 0.9, N: 20, sigma: 283, mu: 30 };
  ok(M.kSat(p) === 4000 && M.seuilL(p) === 1000, "K = 4 000, L = 1 000");
  ok(M.retrait(p, 999) === 0 && Math.abs(M.retrait(p, 1000) - 450) < 1e-9 && Math.abs(M.retrait(p, 9000) - 1800) < 1e-9, "retrait 0 / 450 / 1 800");
  ok(M.pointMort(p) === 1000, "point mort à la marche de 1 000");
  ok(Math.abs(M.valeur(p, 2500, 1e-9) - M.retrait(p, 2500)) < 1e-6, "valeur à l'échéance = retrait"); }
// 9. la stratégie au trade : moments exacts contre simulation
{ const S = { pv: 2, tick: 0.25, c: 4, stop: 20, rr: 1.5, p: 0.45, n: 2, comm: 1, slip: 1, dStop: 0, dTgt: 0 }, ts = M.tradeStats(S);
  close(ts.W, 236, 1e-9, "gain net d'un trade"); close(ts.Lo, 166, 1e-9, "perte nette d'un trade");
  close(ts.E, 0.45 * 236 - 0.55 * 166, 1e-9, "espérance par trade");
  close(ts.pBE, 166 / 402, 1e-12, "taux sans avantage");
  const m = M.moments((g, o) => M.journee(S, g, o), 400000, 3), mu = 2 * ts.E, sd = Math.sqrt(2) * ts.sd;
  ok(Math.abs(m.mean - mu) < 4 * sd / Math.sqrt(400000), `moyenne quotidienne ${m.mean.toFixed(2)} contre ${mu.toFixed(2)}`);
  ok(Math.abs(m.sd / sd - 1) < 0.01, `écart-type quotidien ${m.sd.toFixed(1)} contre ${sd.toFixed(1)}`);
  const S0 = Object.assign({}, S, { p: ts.pBE }), m0 = M.moments((g, o) => M.journee(S0, g, o), 400000, 4);
  ok(Math.abs(m0.mean) < 4 * sd / Math.sqrt(400000), `loi nulle : moyenne ${m0.mean.toFixed(2)} ≈ 0`);
  const Sd = Object.assign({}, S, { p: 0, n: 5, dStop: 300 }), o = {}, g = M.mulberry32(5); M.journee(Sd, g, o);
  close(o.pnl, -332, 1e-9, "stop journalier : deux pertes puis arrêt");
  const Sw = Object.assign({}, S, { p: 1, n: 1 }); let lo = 0, hi = -1e9, s = 0; const gw = M.mulberry32(6);
  for (let i = 0; i < 100000; i++) { M.journee(Sw, gw, o); lo = Math.min(lo, o.low); hi = Math.max(hi, o.low); s += o.low; }
  ok(lo >= -160 && hi <= 0 && Math.abs(s / 100000 + 80) < 1, `recul d'un gagnant uniforme sur le stop (moyenne ${(s / 100000).toFixed(1)}, attendu -80)`); }
// 10. journal rééchantillonné
{ const v = [120, -85, 310, -40, 60, -150, 220, 15, -95, 180], J = { v, sd: 140 }, m = M.moments((g, o) => M.journeeJournal(J, g, o), 200000, 8);
  close(m.mean, v.reduce((x, y) => x + y) / v.length, 1.5, "moyenne du journal rééchantillonné"); }
// 11. les issues se partagent tout l'échantillon, et la simulation est déterministe
{ const S = { pv: 2, tick: 0.25, c: 4, stop: 20, rr: 1.5, p: 0.45, n: 2, comm: 1, slip: 1, dStop: 0, dTgt: 0 }, day = (g, o) => M.journee(S, g, o);
  const A = M.simCompte(R({}), day, 2026, 0, 4000, null, 0), r = M.lireCompte(A, R({}));
  close(r.koEval + r.ncEval + r.ko0 + r.nc0 + r.pay.slice(1).reduce((x, y) => x + y), 1, 1e-12, "les issues somment à 1");
  const B = M.simCompte(R({}), day, 2026, 0, 4000, null, 0);
  ok(A.cash.every((x, i) => x === B.cash[i]), "même graine, mêmes challenges");
  let A2 = M.simCompte(R({}), day, 2026, 0, 2000, null, 0); A2 = M.simCompte(R({}), day, 2026, 2000, 4000, A2, 0);
  ok(A2.cash.every((x, i) => x === A.cash[i]), "découpé en tranches, même résultat");
  console.log(`  exemple : réussite ${(100 * r.pPass).toFixed(1)} %, au moins un retrait ${(100 * r.p1).toFixed(1)} %, espérance ${r.E.toFixed(1)} $ ± ${(2 * r.seE).toFixed(1)}`);
  const S0 = Object.assign({}, S, { p: M.tradeStats(S).pBE }), r0 = M.lireCompte(M.simCompte(R({}), (g, o) => M.journee(S0, g, o), 2026, 0, 4000, null, 0), R({}));
  console.log(`  loi nulle : réussite ${(100 * r0.pPass).toFixed(1)} %, au moins un retrait ${(100 * r0.p1).toFixed(1)} %, espérance ${r0.E.toFixed(1)} $ ± ${(2 * r0.seE).toFixed(1)}`);
  ok(r.E > r0.E, "un avantage vaut plus que la loi nulle"); }
// 12. PSR : formule, et calibration sous la loi nulle
{ close(M.psr(0, 60, 0, 3), 0.5, 1e-7, "PSR d'un Sharpe nul = 0,5 (précision de erfc)");
  const sr = 0.1, n = M.minTRL(sr, -0.3, 5, 0.95);
  close(M.psr(sr, n, -0.3, 5), 0.95, 1e-6, "PSR à la durée MinTRL = 95 %");
  const S = { pv: 2, tick: 0.25, c: 4, stop: 20, rr: 1.5, p: 0.45, n: 2, comm: 1, slip: 1, dStop: 0, dTgt: 0 }, ts = M.tradeStats(S);
  const S0 = Object.assign({}, S, { p: ts.pBE }), A = M.simLibre((g, o) => M.journee(S0, g, o), 0, 2000, 11, 0, 6000, 60, [60], null, 0);
  let fp = 0; for (const x of A.win[60].psr) if (x >= 0.95) fp++;
  const f = fp / 6000, se = Math.sqrt(0.05 * 0.95 / 6000);
  console.log(`  PSR sous la loi nulle, 6 000 fenêtres de 60 jours : ${(100 * f).toFixed(2)} % au-dessus de 95 % (attendu 5 % ± ${(200 * se).toFixed(2)})`);
  ok(Math.abs(f - 0.05) < 4 * se, "PSR calibré sous la loi nulle");
  const L = M.lireLibre(M.simLibre((g, o) => M.journee(S, g, o), 2 * ts.E, 2000, 12, 0, 2000, 252, [60], null, 50000), 252);
  close(L.sharpe, 2 * ts.E / (Math.sqrt(2) * ts.sd) * Math.sqrt(252), 0.06, "Sharpe annualisé du compte libre");
  ok(L.sortino > L.sharpe, "Sortino au-dessus du Sharpe pour une perte bornée");
  console.log(`  compte libre : Sharpe ${L.sharpe.toFixed(2)}, Sortino ${L.sortino.toFixed(2)}, recul médian ${L.ddMed.toFixed(0)} $, MinTRL ${L.minTRL.toFixed(0)} jours`); }

// 13. Repartir d'un compte en cours (e0, v7 et suivantes). Sauté sur les pages plus anciennes, dont le moteur l'ignore.
if (/simCompte\(R,day,seed,i0,i1,acc,keep,e0\)/.test(html)) {
  const un0 = (Rr, day, e0) => M.simCompte(Rr, day, 1, 0, 1, null, 1, e0);
  // a. l'état du jour de l'achat redonne le moteur sans état, prix mis à part
  { const S = { pv: 2, tick: 0.25, c: 4, stop: 20, rr: 1.5, p: 0.45, n: 2, comm: 1, slip: 1, dStop: 0, dTgt: 0 }, day = (g, o) => M.journee(S, g, o);
    const A = M.simCompte(R({}), day, 7, 0, 1500, null, 0), B = M.simCompte(R({}), day, 7, 0, 1500, null, 0, { phase: "eval", x: 0, M: 0, nd: 0, best: 0 });
    ok(A.passe === B.passe && A.koEval === B.koEval && A.tPass.every((t, i) => t === B.tPass[i]), "état de départ : mêmes évaluations que sans état");
    ok(A.cash.every((x, i) => Math.abs(x + 78.4 - B.cash[i]) < 1e-9), "état de départ : même trésorerie, prix déjà payé"); }
  // b. 2 800 $ de profit, +200 $ par jour : réussite le lendemain
  { const A = un0(R({}), fixe(200), { phase: "eval", x: 2800, M: 2800, nd: 14, best: 200 });
    ok(A.passe === 1 && A.tPass[0] === 1, `2 800 $ + 200 $ : réussite au jour 1 (lu ${A.tPass[0]})`); }
  // c. règle du meilleur jour : 1 600 $ en un jour impose 3 200 $ de profit
  { const A = un0(R({}), fixe(200), { phase: "eval", x: 2900, M: 2900, nd: 10, best: 1600 });
    ok(A.passe === 1 && A.tPass[0] === 2, `meilleur jour 1 600 $ : réussite à 3 300 $, au jour 2 (lu ${A.tPass[0]})`); }
  // d. compte financé neuf : les retraits du contrôle 1, décalés de la durée de l'évaluation
  { const A = un0(R({}), fixe(200), { phase: "fund", x: 0, M: 0, q: 0, c0: 0, lock: false }), ev = A.events[0], jours = [];
    for (let i = 0; i < ev.length; i += 2) jours.push(ev[i]);
    ok(JSON.stringify(jours) === JSON.stringify([5, 10, 15, 20, 25]), `financé neuf : retraits aux jours 5…25 (lu ${jours})`);
    close(A.cash[0], 3628.125, 1e-9, "financé neuf : trésorerie sans le prix"); }
  // e. plancher bloqué à +100 contre plancher qui suit le plus haut, à −300 $ par jour depuis 1 500 $
  { const Al = un0(R({}), fixe(-300), { phase: "fund", x: 1500, M: 1500, q: 0, c0: 0, lock: true });
    const An = un0(R({}), fixe(-300), { phase: "fund", x: 1500, M: 1500, q: 0, c0: 0, lock: false });
    ok(Al.samples[0].ko === 5 && An.samples[0].ko === 7, `bloqué à +100 : éteint au jour 5 ; plancher à −500 : au jour 7 (lu ${Al.samples[0].ko}, ${An.samples[0].ko})`); }
}

// 14. Calendrier de chaque challenge (v9 et suivantes) : jour de réussite, du 1er retrait, de l'extinction, −1 pour jamais.
if (/acc\.tP\.push\(tP\)/.test(html)) {
  { const A = un(R({}), fixe(200));
    ok(A.tP[0] === 15 && A.t1[0] === 20 && A.tKo[0] === -1, `+200 $ par jour : réussite J15, 1er retrait J20, jamais éteint (lu ${A.tP[0]}, ${A.t1[0]}, ${A.tKo[0]})`); }
  { const A = un(R({}), fixe(-300));
    ok(A.tP[0] === -1 && A.t1[0] === -1 && A.tKo[0] === 7, `−300 $ par jour : éteint J7 sans réussite (lu ${A.tP[0]}, ${A.t1[0]}, ${A.tKo[0]})`); }
  { const A = M.simCompte(R({}), fixe(-300), 1, 0, 1, null, 1, { phase: "fund", x: 1500, M: 1500, q: 0, c0: 0, lock: true });
    ok(A.tP[0] === 0 && A.tKo[0] === 5, `financé bloqué : réussite comptée au jour 0, éteint J5 (lu ${A.tP[0]}, ${A.tKo[0]})`); }
  { const S = { pv: 2, tick: 0.25, c: 4, stop: 20, rr: 1.5, p: 0.45, n: 2, comm: 1, slip: 1, dStop: 0, dTgt: 0 }, A = M.simCompte(R({}), (g, o) => M.journee(S, g, o), 3, 0, 2000, null, 0);
    const nP = A.tP.filter(t => t >= 0).length, n1 = A.t1.filter(t => t >= 0).length, nK = A.tKo.filter(t => t >= 0).length;
    ok(A.tP.length === 2000 && nP === A.passe, `autant de jours de réussite que de réussites (${nP} / ${A.passe})`);
    ok(n1 === A.tPay1.length && A.t1.every((t, i) => t < 0 || t > A.tP[i]), "le 1er retrait suit toujours la réussite");
    ok(nK === A.koEval + A.ko0 + A.payKo.reduce((a, b) => a + b, 0), `extinctions comptées une fois (${nK})`); }
}

console.log(`\n${nOk} contrôles passés, ${nKo} échecs`);
process.exit(nKo ? 1 : 0);
