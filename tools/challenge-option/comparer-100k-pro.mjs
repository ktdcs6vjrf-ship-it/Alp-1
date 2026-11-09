// Usage : node tools/challenge-option/comparer-100k-pro.mjs prop/challenge-option25.html   (20 000 challenges par ligne, mêmes tirages)
// MFFU Pro 100K face aux trois 100K déjà relevés (LucidPro, MFFU Builder, LucidFlex), sur les mêmes journées et avec les conventions
// de comparer-100k.mjs, dont il redonne les chiffres : objectif 6 000 $, drawdown 3 000 $ sur le plus haut de clôture, touché en séance,
// bloqué à +100 $ dès un plus haut de 3 100 $ ; financé neuf à 0 ; 250 séances au plus, évaluation comprise ; ce qui reste sur le
// compte à la fin n'est pas compté. Deux plafonds de durée : 5 retraits au plus (comme comparer-100k.mjs), ou aucun.
// MFFU Pro 100K (page du plan et centre d'aide, lus par la recherche le 9 novembre 2026 ; tableau de bord non vu) : évaluation
//   en 2 jours au moins, meilleur jour ≤ 50 % du profit ; financé : aucune consistance, tampon 3 100 $, une demande tous les
//   14 jours calendaires (10 séances) de tout ce qui dépasse le tampon, 1 000 $ au moins, aucun plafond par demande, 100 000 $ au
//   total, partage 80 %. Prix non confirmé : 172 $ chez une seule revue, d'où la colonne « reçu » avant prix.
// LucidFlex 100K (captures + tiers) : 150,50 $ avec coupon ; évaluation : meilleur jour ≤ 50 % ; financé : 5 jours ≥ 200 $ et
//   profit > 0 par cycle, demande = 50 % du profit, 500 à 2 500 $, plancher bloqué à +100 $ à la 1re demande, partage 90 %.
import { readFileSync } from "node:fs";
const html = readFileSync(process.argv[2], "utf8"), a = html.indexOf("/* MODELE:DEBUT"), b = html.indexOf("/* MODELE:FIN */");
const M = new Function(html.slice(a, b) + "\nreturn {mulberry32,graine,journee,tradeStats};")();
const D = 3000, OBJ = 6000, BUF = 3100, H = 250, N = 20000;
const FIRMS = {
  "LucidPro, 190 $": { fee: 190.4, minJ: 1, ec: 0, k: "cyc", cyc: 750, days: 3, cons: 0.40, minPay: 500, cap: [2500, 3000], split: 0.90 },
  "Builder, 282 $": { fee: 282, minJ: 1, ec: 0, k: "cyc", cyc: 1000, days: 2, cons: 0.50, minPay: 1000, cap: [3000, 3000], split: 0.80 },
  "LucidFlex, 151 $, au plus tôt": { fee: 150.5, minJ: 1, ec: 0.5, k: "flex", seuil: 500, split: 0.90 },
  "LucidFlex, 151 $, au plafond": { fee: 150.5, minJ: 1, ec: 0.5, k: "flex", seuil: 2500, split: 0.90 },
  "Pro, 172 $ ?, tous les 14 j": { fee: 172, minJ: 2, ec: 0.5, k: "pro", seuil: 1000, split: 0.80 },
  "Pro, 172 $ ?, attendre 3 000 $": { fee: 172, minJ: 2, ec: 0.5, k: "pro", seuil: 3000, split: 0.80 },
};
const med = v => v.length ? v[v.length >> 1] : NaN;
function run(F, S, maxP) {
  const o = { pnl: 0, low: 0, sd: 0 };
  let sum = 0, pass = 0, paid = 0, nPay = 0; const tPass = [], tPay = [], got = [];
  for (let i = 0; i < N; i++) {
    const g = M.mulberry32(M.graine(2026, i, 3));
    let t = 0, x = 0, Mx = 0, f = -D, lock = false, nd = 0, ok = false, best = 0;
    const step = () => { M.journee(S, g, o); g(); t++; if (x + o.low <= f) return false; x += o.pnl; if (x <= f) return false;
      if (!lock) { if (x > Mx) Mx = x; f = Math.min(Mx - D, 100); if (Mx - D >= 100) lock = true } return true };
    while (t < H) { if (!step()) break; nd++; if (o.pnl > best) best = o.pnl;
      if (x >= OBJ && nd >= F.minJ && (!F.ec || best <= F.ec * x)) { ok = true; break } }
    let cash = 0, pays = 0;
    if (ok) { pass++; tPass.push(t); x = 0; Mx = 0; f = -D; lock = false; let cp = 0, bd = 0, nd2 = 0, q = 0, last = t;
      while (t < H && pays < maxP) { if (!step()) break; cp += o.pnl; if (o.pnl > bd) bd = o.pnl; nd2++; if (o.pnl >= 200) q++;
        let req = 0;
        if (F.k === "cyc") { const r = Math.min(x - BUF, F.cap[pays ? 1 : 0]); if (r >= F.minPay && cp >= F.cyc && nd2 >= F.days && bd <= F.cons * cp) req = r; }
        else if (F.k === "pro") { if (t - last >= 10 && x - BUF >= F.seuil) req = x - BUF; }
        else { const r = Math.min(0.5 * x, 2500); if (q >= 5 && cp > 0 && r >= F.seuil) req = r; }
        if (!req) continue;
        cash += F.split * req; x -= req; pays++; cp = 0; bd = 0; nd2 = 0; q = 0; last = t;
        if (!lock) { lock = true; f = 100; } if (pays === 1) tPay.push(t) } }
    if (pays) paid++; nPay += pays; sum += cash; got.push(cash);
  }
  for (const v of [tPass, tPay, got]) v.sort((p, r) => p - r);
  return { G: sum / N, pass: pass / N, paid: paid / N, nPay: nPay / N, tP: med(tPass), t1: med(tPay), g90: got[Math.floor(0.9 * N)] };
}
const base = { pv: 2, tick: 0.25, stop: 20, comm: 1, slip: 1, dStop: 0, dTgt: 0 };
const STY = {
  "régulier : 6 MNQ, 2 trades/j, 45 %, 1,5 R": { ...base, c: 6, rr: 1.5, p: 0.45, n: 2 },
  "grosses journées : 6 MNQ, 1 trade/j, 30 %, 3 R": { ...base, c: 6, rr: 3, p: 0.30, n: 1 },
  "régulier, plus petit : 4 MNQ, 2 trades/j, 45 %, 1,5 R": { ...base, c: 4, rr: 1.5, p: 0.45, n: 2 },
};
const $ = v => isNaN(v) ? "–" : (v < 0 ? "−" : "+") + Math.abs(Math.round(v)).toLocaleString("fr-FR").replace(/ /g, " ");
for (const [nom, S] of Object.entries(STY)) {
  const ts = M.tradeStats(S);
  console.log(`\n${nom} : ${(ts.E * S.n).toFixed(0)} $ par jour en moyenne ; sans avantage à ${(100 * ts.pBE).toFixed(1)} %`);
  for (const [lab, SS] of [["avec avantage", S], ["sans avantage", { ...S, p: ts.pBE }]])
    for (const [f, F] of Object.entries(FIRMS)) {
      const r = run(F, SS, 5), u = run(F, SS, Infinity);
      console.log(`  ${lab.padEnd(14)} ${f.padEnd(31)} reçu ${$(r.G).padStart(7)} $ net ${$(r.G - F.fee).padStart(7)} $ | sans limite : reçu ${$(u.G).padStart(7)} $, net ${$(u.G - F.fee).padStart(7)} $, ${u.nPay.toFixed(2)} retraits | réussite ${(100 * r.pass).toFixed(0).padStart(3)} % (J${r.tP}) | payés ${(100 * r.paid).toFixed(0).padStart(3)} % | 1er retrait J${isNaN(r.t1) ? "–" : r.t1} | 9 sur 10 reçoivent moins de ${$(r.g90)} $`);
    }
}
