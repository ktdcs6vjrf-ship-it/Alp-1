// Usage : node tools/challenge-option/comparer-100k.mjs prop/challenge-option25.html   (20 000 challenges par firme et par style, mêmes tirages)
// LucidPro 100K contre MyFundedFutures Builder 100K, sur les mêmes journées (moteur de l'app : journee, mulberry32, graine).
// Règles relevées le 9 novembre 2026 sur les captures des tableaux de bord envoyées par l'utilisateur (dash.lucidtrading.com,
// myfundedfutures.com), complétées par des sources tierces pour ce que les captures ne montrent pas (marqué « tiers »).
// Hypothèses communes : objectif 6 000 $, drawdown 3 000 $ sur le plus haut de clôture (fin de journée), touché en séance,
// bloqué à +100 $ dès un plus haut de 3 100 $ ; pas de consistance en évaluation ; financé neuf à 0 ;
// tampon 3 100 $ : on ne retire que le profit au-dessus de 3 100 $ ; 5 retraits au plus, 250 séances au plus.
// LucidPro (captures) : prix 272 $, 190,40 $ avec coupon ; cycle ≥ 750 $ de profit et 3 jours ; meilleur jour ≤ 40 % du cycle ;
//   limites journalières 1 800 $ puis 60 % du plus haut de clôture (jamais atteintes par les styles testés).
//   Tiers : tampon 3 100 $, retrait 500 $ au moins, 2 500 $ au plus le premier puis 3 000 $, partage 90 %.
// MFFU Builder (captures) : évaluation en 1 jour ; financé : meilleur jour ≤ 50 % du cycle ; cycle de 2 jours ; retrait 1 000 $ à
//   3 000 $ ; partage 80 % ; tampon 3 100 $ ; limite journalière 1 750 $ (jamais atteinte). Prix : 282 $ (tiers, sans coupon).
import { readFileSync } from "node:fs";
const html = readFileSync(process.argv[2], "utf8"), a = html.indexOf("/* MODELE:DEBUT"), b = html.indexOf("/* MODELE:FIN */");
const M = new Function(html.slice(a, b) + "\nreturn {mulberry32,graine,journee,tradeStats};")();
const FIRMS = {
  "Lucid 190": { fee: 190.4, minJ: 1, cyc: 750, days: 3, cons: 0.40, minPay: 500, cap: [2500, 3000], split: 0.90 },
  "Lucid 272": { fee: 272, minJ: 1, cyc: 750, days: 3, cons: 0.40, minPay: 500, cap: [2500, 3000], split: 0.90 },
  "MFFU 282": { fee: 282, minJ: 1, cyc: 1000, days: 2, cons: 0.50, minPay: 1000, cap: [3000, 3000], split: 0.80 }
};
function run(F, S, N, seed) {
  const o = { pnl: 0, low: 0, sd: 0 }, day = (g) => M.journee(S, g, o);
  let sum = 0, pass = 0, paid = 0, nPay = 0, tPay = [], net = [];
  for (let i = 0; i < N; i++) {
    const g = M.mulberry32(M.graine(seed, i, 3));
    let t = 0, x = 0, Mx = 0, f = -3000, lock = false, nd = 0, ok = false, dead = false;
    const step = () => { day(g); const u = g(); t++; if (x + o.low <= f) { dead = true; return false } x += o.pnl; if (x <= f) { dead = true; return false }
      if (!lock) { if (x > Mx) Mx = x; f = Math.min(Mx - 3000, 100); if (Mx - 3000 >= 100) lock = true } return true };
    while (t < 250) { if (!step()) break; nd++; if (x >= 6000 && nd >= Math.max(1, F.minJ)) { ok = true; break } }
    let cash = -F.fee, pays = 0;
    if (ok) { pass++; x = 0; Mx = 0; f = -3000; lock = false; dead = false; let cp = 0, best = 0, nd2 = 0;
      while (t < 250 && pays < 5) { if (!step()) break; cp += o.pnl; if (o.pnl > best) best = o.pnl; nd2++;
        const room = x - 3100, cap = F.cap[pays ? 1 : 0], req = Math.min(room, cap);
        if (req >= F.minPay && cp >= F.cyc && nd2 >= F.days && (!F.cons || best <= F.cons * cp)) {
          cash += F.split * req; x -= req; pays++; cp = 0; best = 0; nd2 = 0; if (pays === 1) tPay.push(t) } } }
    if (pays) paid++; nPay += pays; sum += cash; net.push(cash);
  }
  net.sort((p, q) => p - q); tPay.sort((p, q) => p - q);
  return { E: sum / N, pass: pass / N, paid: paid / N, nPay: nPay / N, t1: tPay.length ? tPay[tPay.length >> 1] : NaN, q90: net[Math.floor(0.9 * N)] };
}
const base = { pv: 2, tick: 0.25, stop: 20, comm: 1, slip: 1, dStop: 0, dTgt: 0 };
const STY = {
  "régulier : 6 MNQ, 2 trades/j, 45 %, 1,5 R": { ...base, c: 6, rr: 1.5, p: 0.45, n: 2 },
  "grosses journées : 6 MNQ, 1 trade/j, 30 %, 3 R": { ...base, c: 6, rr: 3, p: 0.30, n: 1 },
};
for (const [nom, S] of Object.entries(STY)) {
  const ts = M.tradeStats(S), S0 = { ...S, p: ts.pBE };
  console.log(`\n${nom} — espérance ${ts.E.toFixed(1)} $ par trade, taux sans avantage ${(100 * ts.pBE).toFixed(1)} %`);
  for (const [lab, SS] of [["avec avantage", S], ["sans avantage", S0]])
    for (const [f, F] of Object.entries(FIRMS)) { const r = run(F, SS, 20000, 2026);
      console.log(`  ${lab.padEnd(14)} ${f.padEnd(10)} gain net ${r.E.toFixed(0).padStart(6)} $ | réussite ${(100 * r.pass).toFixed(0).padStart(3)} % | payés ${(100 * r.paid).toFixed(0).padStart(3)} % | retraits ${r.nPay.toFixed(2)} | 1er retrait médian J${isNaN(r.t1) ? "–" : r.t1} | 9 sur 10 sous ${r.q90.toFixed(0)} $`); }
}
