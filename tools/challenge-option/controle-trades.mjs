// Contrôle du journal de trades en R (bloc MODELE de prop/challenge-option27.html et suivantes).
// Usage : node tools/challenge-option/controle-trades.mjs [page]
//  1. lecture d'une série collée (nombres, virgule décimale, signes, lettres, morceaux illisibles) ;
//  2. statistiques nettes de frais sur une suite calculée à la main ;
//  3. coûts en R cohérents avec tradeStats : même taux sans avantage ;
//  4. loi nulle : l'éventail est calibré (10 % des suites nulles finissent hors de la bande 5–95 %), sa médiane est nulle,
//     et une stratégie à avantage en sort plus souvent qu'une stratégie sans ;
//  5. (v28) bootstrap recentré de l'espérance en R : taille ≈ 5 % sous une loi asymétrique d'espérance nulle, puissance,
//     couverture de l'intervalle à 90 %, déterminisme ; nombre de trades nR.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
const ici = dirname(fileURLToPath(import.meta.url));
const page = process.argv[2] ? resolve(process.argv[2]) : join(ici, "../../prop/challenge-option27.html");
const html = readFileSync(page, "utf8"), a = html.indexOf("/* MODELE:DEBUT"), b = html.indexOf("/* MODELE:FIN */");
const M = new Function(html.slice(a, b) + "\nreturn {mulberry32,graine,tradeStats,lireSerie,netR,statsR,fanR,bootR:typeof bootR===\"function\"?bootR:null,nR:typeof nR===\"function\"?nR:null};")();
let nOk = 0, nKo = 0;
const ok = (c, m) => { if (c) nOk++; else { nKo++; console.log("ÉCHEC  " + m); } };
const close = (x, y, tol, m) => ok(Math.abs(x - y) <= tol, `${m} : ${x} contre ${y}`);
const eq = (x, y, m) => ok(JSON.stringify(x) === JSON.stringify(y), `${m} : ${JSON.stringify(x)} contre ${JSON.stringify(y)}`);

// 1. lecture
eq(M.lireSerie("1,5 -1 −1 + - 0 = 2R be x", 1.5), { r: [1.5, -1, -1, 1.5, -1, 0, 0, 2, 0], bad: 1 }, "série mêlée");
eq(M.lireSerie("w l l w; n|+3", 2), { r: [2, -1, -1, 2, 0, 3], bad: 0 }, "lettres et séparateurs");
eq(M.lireSerie("1.25 -0,5 500 abc", 1.5), { r: [1.25, -0.5], bad: 2 }, "point décimal, valeur hors borne, texte");
eq(M.lireSerie("", 1.5), { r: [], bad: 0 }, "série vide");
// 2. statistiques à la main : cw = 0,02 R, cl = 0,05 R
{ const s = M.statsR([1.5, -1, -1, 1.5, 0, -1, 2], 0.02, 0.05);
  ok(s.n === 7 && s.w === 3 && s.l === 3, `comptes (${s.n}, ${s.w}, ${s.l})`);
  close(s.p, 3 / 7, 1e-12, "taux de gain");
  close(s.cum, 1.77, 1e-9, "cumul net (1,48 − 1,05 − 1,05 + 1,48 − 0,02 − 1,05 + 1,98)");
  close(s.e, 1.77 / 7, 1e-12, "espérance nette par trade");
  close(s.dd, 2.10, 1e-9, "recul maximal (1,48 → −0,62)");
  close(s.pf, 4.94 / 3.17, 1e-12, "facteur de profit net");
  ok(s.mrun === 2, `pertes d'affilée : 2 (lu ${s.mrun})`);
  close(s.gW, 5 / 3, 1e-12, "gain moyen brut"); close(s.gL, -1, 1e-12, "perte moyenne brute");
  const v = [1.48, -1.05, -1.05, 1.48, -0.02, -1.05, 1.98], m = 1.77 / 7, sd = Math.sqrt(v.reduce((q, x) => q + (x - m) ** 2, 0) / 6);
  close(s.sd, sd, 1e-12, "écart-type de l'échantillon"); close(s.t, m / (sd / Math.sqrt(7)), 1e-9, "statistique t"); }
{ const s = M.statsR([], 0.02, 0.05); ok(s.n === 0 && Number.isNaN(s.p) && s.e === 0, "journal vide"); }
// 3. coûts en R : 4 MNQ, stop 20, 1,5 R, commission 1 $, glissement 1 tick
{ const S = { pv: 2, tick: 0.25, c: 4, stop: 20, rr: 1.5, p: 0.45, n: 2, comm: 1, slip: 1, dStop: 0, dTgt: 0 }, ts = M.tradeStats(S);
  const risk = S.stop * S.pv * S.c, cw = S.comm * S.c / risk, cl = (S.comm * S.c + S.slip * S.tick * S.pv * S.c) / risk, wR = S.rr - cw, lR = 1 + cl;
  close(lR / (wR + lR), ts.pBE, 1e-12, `seuil sans avantage en R = celui de tradeStats (${(100 * ts.pBE).toFixed(2)} %)`);
  close(M.netR(1.5, cw, cl) * risk, ts.W, 1e-9, "un gagnant net en dollars"); close(-M.netR(-1, cw, cl) * risk, ts.Lo, 1e-9, "un perdant net en dollars");
  // 4. loi nulle
  const m = 200, q = M.fanR(m, ts.pBE, wR, lR, 400, 1), g = M.mulberry32(99), N = 4000;
  let hors = 0, horsA = 0;
  for (let k = 0; k < N; k++) { let c = 0, cA = 0; for (let j = 0; j < m; j++) { const u = g(); c += u < ts.pBE ? wR : -lR; cA += u < 0.5 ? wR : -lR; }
    if (c < q[m][0] || c > q[m][4]) hors++; if (cA > q[m][4]) horsA++; }
  close(hors / N, 0.10, 0.02, `suites sans avantage hors de la bande 5–95 % au trade ${m}`);
  ok(Math.abs(q[m][2]) < 0.15 * (q[m][4] - q[m][0]), `médiane de l'éventail proche de zéro (${q[m][2].toFixed(2)} R)`);
  ok(horsA / N > 0.5, `à 50 % de gain, la suite sort par le haut dans ${(100 * horsA / N).toFixed(0)} % des cas`);
  ok(q.length === m + 1 && q[0].every(x => x === 0), "l'éventail part de zéro, un point par trade");
  const q2 = M.fanR(m, ts.pBE, wR, lR, 400, 1); ok(JSON.stringify(q2) === JSON.stringify(q), "même graine, même éventail"); }

// 5. bootstrap recentré (v28)
if (M.bootR) {
  const g = M.mulberry32(2024), tire = (n, pw, w) => { const x = []; for (let i = 0; i < n; i++) x.push(g() < pw ? w : -1); return x; };
  // loi nulle asymétrique : 25 % à +3 R, 75 % à −1 R, espérance nulle — le cas d'une stratégie à objectif lointain
  let rej = 0, cov = 0; const D = 500;
  for (let d = 0; d < D; d++) { const x = tire(80, 0.25, 3), r = M.bootR(x, 1000, d + 1); if (r.p < 0.05) rej++; if (r.lo <= 0 && 0 <= r.hi) cov++; }
  ok(rej / D >= 0.02 && rej / D <= 0.09, `taille du test sous une espérance nulle asymétrique : ${(100 * rej / D).toFixed(1)} % (attendu ≈ 5 %)`);
  ok(cov / D >= 0.84 && cov / D <= 0.95, `l'intervalle à 90 % couvre la vraie espérance dans ${(100 * cov / D).toFixed(1)} % des cas`);
  // à +0,25 R (25 % à +4 R), l'écart-type vaut 2,17 R : sur 400 trades, z ≈ 2,31 et la puissance normale ≈ 75 %
  let pow = 0; for (let d = 0; d < 200; d++) { const x = tire(400, 0.25, 4), r = M.bootR(x, 1000, d + 7); if (r.p < 0.05) pow++; }
  ok(pow / 200 > 0.6, `à +0,25 R par trade sur 400 trades, l'avantage est prouvé ${(100 * pow / 200).toFixed(0)} fois sur 100 (≈ 75 % attendu)`);
  const x0 = tire(60, 0.3, 2.5), r1 = M.bootR(x0, 2000, 3), r2 = M.bootR(x0, 2000, 3);
  ok(r1.p === r2.p && r1.lo === r2.lo && r1.hi === r2.hi, "même graine, même p-valeur et même intervalle");
  ok(Number.isNaN(M.bootR([1], 100, 1).p), "un seul trade : pas de test");
  const sd = Math.sqrt(0.25 * 0.75) * 5, n50 = M.nR(0.25, sd, 0.5), n80 = M.nR(0.25, sd, 0.8);
  close(n50, Math.ceil((1.6448536 * sd / 0.25) ** 2), 0, `nR à une chance sur deux (${n50} trades)`);
  ok(n80 > n50 && M.nR(0, sd, 0.5) === Infinity && M.nR(-0.1, sd, 0.5) === Infinity, `nR : 4 sur 5 demande plus (${n80}), aucune espérance n'est prouvable`);
  // à n50 trades, la moitié des jeux prouvent l'avantage (test normal approché : tolérance large)
  let h = 0; for (let d = 0; d < 300; d++) { const x = tire(n50, 0.25, 4), r = M.bootR(x, 600, d + 99); if (r.p < 0.05) h++; }
  ok(Math.abs(h / 300 - 0.5) < 0.1, `à ${n50} trades, preuve dans ${(100 * h / 300).toFixed(0)} % des jeux (attendu ≈ 50 %)`);
}

console.log(`\n${nOk} contrôles passés, ${nKo} échecs`);
process.exit(nKo ? 1 : 0);
