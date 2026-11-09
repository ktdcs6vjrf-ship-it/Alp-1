// MFFU Pro 50K, compte financé neuf : la taille des retraits, sur les journées du moteur de l'app (journee, mulberry32, graine).
// Usage : node tools/challenge-option/mffu-pro-50k.mjs prop/challenge-option25.html (20 000 comptes, environ 2 s).
// Règles (sites tiers + fragments du centre d'aide, 9 novembre 2026 ; le tableau de bord n'a pas été vu) :
//   drawdown 2 000 $ sur le plus haut de clôture, touché en séance ; bloqué à +100 $ dès un plus haut de 2 100 $ ou au 1er retrait ;
//   tampon 2 100 $ : on retire le profit au-dessus ; minimum 1 000 $ ; aucun plafond par demande ; 100 000 $ au total ;
//   une demande tous les 14 jours calendaires (10 séances) ; partage 80 % ; pas de consistance ; 250 séances.
//   Option contestée : un retrait unique de 60 % du profit avant d'avoir franchi le tampon.
import { readFileSync } from "node:fs";
const html = readFileSync(process.argv[2], "utf8"), a = html.indexOf("/* MODELE:DEBUT"), b = html.indexOf("/* MODELE:FIN */");
const M = new Function(html.slice(a, b) + "\nreturn {mulberry32,graine,journee,tradeStats};")();
const D = 2000, BUF = 2100, MIN = 1000, SPLIT = 0.8, TOT = 100000, WIN = 10, H = 250, N = 20000;
const med = v => v.length ? v[v.length >> 1] : NaN, q = (v, p) => v.length ? v[Math.min(v.length - 1, Math.floor(p * v.length))] : NaN;

function run(S, pol) {
  const o = { pnl: 0, low: 0, sd: 0 };
  let sum = 0, any = 0, nPay = 0, alive = 0;
  const sizes = [], cash = [], first = [], biggest = [];
  for (let i = 0; i < N; i++) {
    const g = M.mulberry32(M.graine(2026, i, 3));
    let x = 0, Mx = 0, f = -D, lock = false, t = 0, last = 0, paid = 0, c = 0, pays = 0, early = false, ok = true, big = 0;
    while (t < H) {
      M.journee(S, g, o); g(); t++;
      if (x + o.low <= f) { ok = false; break; }
      x += o.pnl; if (x <= f) { ok = false; break; }
      if (!lock) { if (x > Mx) Mx = x; f = Math.min(Mx - D, 100); if (Mx - D >= 100) lock = true; }
      if (t - last < WIN || paid >= TOT) continue;
      const room = x - BUF; let req = 0;
      if (room >= pol.seuil) req = pol.cap ? Math.min(room, pol.cap) : room;
      else if (pol.early && !early && !pays && room < 0 && 0.6 * x >= MIN) { req = 0.6 * x; early = true; }
      if (req < MIN) continue;
      req = Math.min(req, TOT - paid); x -= req; paid += req; c += SPLIT * req; pays++; sizes.push(req); last = t;
      if (req > big) big = req; if (!lock) { lock = true; f = 100; } if (pays === 1) first.push(t);
    }
    if (ok) alive++; if (pays) { any++; biggest.push(big); } nPay += pays; sum += c; cash.push(c);
  }
  for (const v of [sizes, cash, first, biggest]) v.sort((p, r) => p - r);
  return { E: sum / N, paid: any / N, nPay: nPay / N, alive: alive / N, t1: med(first), sMed: med(sizes), s90: q(sizes, 0.9),
    s3k: sizes.filter(s => s >= 3000).length / Math.max(1, sizes.length), bigMed: med(biggest), c90: q(cash, 0.9) };
}

const base = { pv: 2, tick: 0.25, stop: 20, comm: 1, slip: 1, dStop: 0, dTgt: 0 };
const STY = {
  "4 MNQ, 2 trades/j, 45 %, 1,5 R (l'exemple de l'app)": { ...base, c: 4, rr: 1.5, p: 0.45, n: 2 },
  "6 MNQ, 2 trades/j, 45 %, 1,5 R": { ...base, c: 6, rr: 1.5, p: 0.45, n: 2 },
  "4 MNQ, 1 trade/j, 30 %, 3 R (grosses journées)": { ...base, c: 4, rr: 3, p: 0.30, n: 1 },
};
const POL = {
  "tout au-dessus du tampon, tous les 14 j": { seuil: MIN },
  "attendre 3 000 $ au-dessus du tampon": { seuil: 3000 },
  "attendre 5 000 $ au-dessus du tampon": { seuil: 5000 },
  "avec le retrait anticipé de 60 %": { seuil: MIN, early: true },
  "si un plafond de 2 000 $ par demande existait": { seuil: MIN, cap: 2000 },
};
const $ = v => isNaN(v) ? "–" : Math.round(v).toLocaleString("fr-FR").replace(/ /g, " ");
for (const [nom, S] of Object.entries(STY)) {
  const ts = M.tradeStats(S);
  console.log(`\n${nom} : espérance ${ts.E.toFixed(1)} $ par trade, ${(ts.E * S.n).toFixed(0)} $ par jour ; sans avantage à ${(100 * ts.pBE).toFixed(1)} %`);
  const lignes = Object.entries(POL).map(([p, P]) => [p, run(S, P)]);
  lignes.push(["sans avantage, tout au-dessus du tampon", run({ ...S, p: ts.pBE }, POL["tout au-dessus du tampon, tous les 14 j"])]);
  for (const [p, r] of lignes)
    console.log(`  ${p.padEnd(46)} reçu ${$(r.E).padStart(6)} $ | payés ${(100 * r.paid).toFixed(0).padStart(3)} % | retraits ${r.nPay.toFixed(2)} | 1er J${r.t1} | retrait médian ${$(r.sMed)} $, 1 sur 10 > ${$(r.s90)} $, ≥ 3 000 $ : ${(100 * r.s3k).toFixed(0)} % | plus gros (médian) ${$(r.bigMed)} $ | vivants J250 ${(100 * r.alive).toFixed(0)} % | 9 sur 10 sous ${$(r.c90)} $`);
}
