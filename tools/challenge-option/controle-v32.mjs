// Contrôle des ajouts de la v32 au bloc MODELE (prop/challenge-option32.html et suivantes) :
// la taille adaptative (journeeDyn, tailleDyn, pertesFatales, marge passée par simCompte) et la loi exacte de la plus
// longue série de pertes (sansSerie, serieSup). Le bloc MODELE de la page est extrait tel quel : on vérifie le code livré.
// Usage : node tools/challenge-option/controle-v32.mjs [page]   (code de sortie 1 si un contrôle échoue)
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

const ici = dirname(fileURLToPath(import.meta.url));
const page = process.argv[2] && process.argv[2] !== "-v" ? resolve(process.argv[2]) : join(ici, "../../prop/challenge-option32.html");
const html = readFileSync(page, "utf8");
const a = html.indexOf("/* MODELE:DEBUT"), b = html.indexOf("/* MODELE:FIN */");
if (a < 0 || b < 0) { console.error("bloc MODELE introuvable"); process.exit(1); }
const M = new Function(html.slice(a, b) + `
return {mulberry32,graine,tradeStats,journee,journeeDyn:typeof journeeDyn==="function"?journeeDyn:null,tailleDyn,perteContrat,pertesFatales,
        simCompte,lireCompte,sansSerie,serieSup};`)();
if (!M.journeeDyn) { console.log("page antérieure à la v32 : rien à contrôler"); process.exit(0); }

let nOk = 0, nKo = 0;
const BAVARD = process.argv.includes("-v");   // -v : chaque contrôle passé s'écrit aussi, avec ses chiffres
const ok = (c, m) => { if (c) { nOk++; if (BAVARD) console.log("ok     " + m); } else { nKo++; console.log("ÉCHEC  " + m); } };
const close = (x, y, tol, m) => ok(Math.abs(x - y) <= tol, `${m} : ${x} contre ${y}`);
const S0 = { pv: 2, tick: 0.25, c: 4, stop: 20, rr: 1.5, p: 0.45, n: 2, comm: 1, slip: 1, dStop: 0, dTgt: 0 };
const LUCID = { fee: 78.4, D: 2000, lock: 100, obj: 3000, cons: 0.5, minJ: 0, qd: 5, qmin: 150, r: 0.5, wmax: 2000, minReq: 500, split: 0.9,
  maxPay: 5, H: 250, seance: true, lockPay: true, politique: "asap" };

// ---------- taille adaptative ----------
// 1. sans marge connue, journeeDyn rend la journée de journee() (mêmes tirages), pour vingt réglages tirés
{ const r = M.mulberry32(11); let pire = 0, n = 0;
  for (let k = 0; k < 20; k++) {
    const S = { pv: r() < 0.5 ? 2 : 20, tick: 0.25, c: 1 + Math.floor(r() * 12), stop: 4 + Math.floor(r() * 40), rr: 0.5 + r() * 3.5, p: 0.2 + r() * 0.6,
      n: 1 + Math.floor(r() * 6), comm: r() * 4, slip: Math.floor(r() * 4), dStop: r() < 0.3 ? 200 + r() * 800 : 0, dTgt: r() < 0.3 ? 200 + r() * 800 : 0, dyn: 2 + Math.floor(r() * 10) };
    for (let i = 0; i < 200; i++) { const g1 = M.mulberry32(M.graine(k, i, 1)), g2 = M.mulberry32(M.graine(k, i, 1)), o1 = {}, o2 = {};
      M.journee(S, g1, o1); M.journeeDyn(S, g2, o2); n++;
      pire = Math.max(pire, Math.abs(o1.pnl - o2.pnl) / (1 + Math.abs(o1.pnl)), Math.abs(o1.low - o2.low) / (1 + Math.abs(o1.low)));
      if (g1() !== g2()) pire = 1; } }
  ok(pire < 1e-9, `sans marge, journeeDyn = journee sur ${n} journées (écart relatif max ${pire.toExponential(1)}, mêmes tirages consommés)`); }
// 2. une marge assez grande pour que le plafond S.c joue à chaque trade : même journée
{ const S = Object.assign({}, S0, { n: 5, dyn: 5 }); let pire = 0;
  for (let i = 0; i < 300; i++) { const g1 = M.mulberry32(i + 1), g2 = M.mulberry32(i + 1), o1 = {}, o2 = { m: 1e6 }; M.journee(S, g1, o1); M.journeeDyn(S, g2, o2); pire = Math.max(pire, Math.abs(o1.pnl - o2.pnl), Math.abs(o1.low - o2.low)); }
  ok(pire < 1e-9, `grande marge : la taille reste au plafond (écart max ${pire.toExponential(1)} $)`); }
// 3. chemin calculé à la main : perte 41,5 $ et gain 59 $ par contrat, 5 pertes d'avance, marge 500 $
{ const S = Object.assign({}, S0, { n: 3, p: 0.5, dyn: 5 }), seq = [0.9, 0.3, 0.1, 0.5, 0.7, 0.2]; let k = 0; const g = () => seq[k++], o = { m: 500 };
  close(M.perteContrat(S), 41.5, 1e-12, "perte par contrat");
  M.journeeDyn(S, g, o);
  // trade 1 : 2 contrats (500 / 207,5), perdu : −83 ; trade 2 : 2 contrats (417 / 207,5), gagné +118 après un recul de 0,5 × 40 × 2 ; trade 3 : 2 contrats (535 / 207,5), perdu
  close(o.pnl, -83 + 118 - 83, 1e-9, "P&L de la journée (2, 2 puis 2 contrats)");
  close(o.low, -83 - 0.5 * 40 * 2, 1e-9, "creux de séance");
  const o2 = { m: 100 }; k = 0; M.journeeDyn(S, g, o2);
  close(o2.pnl, -41.5 + 59 - 41.5, 1e-9, "marge de 100 $ : un contrat, le minimum"); }
// 4. tailleDyn : entre 1 et S.c, croissante avec la marge, et la règle des k pertes d'avance
{ const S = Object.assign({}, S0, { c: 9, dyn: 5 }); let mono = true, borne = true, regle = true, prev = 0;
  for (let m = -500; m <= 5000; m += 7) { const c = M.tailleDyn(S, m); if (c < prev) mono = false; prev = c; if (c < 1 || c > S.c) borne = false;
    if (c > 1 && c < S.c && !(c * 5 * 41.5 <= m && (c + 1) * 5 * 41.5 > m)) regle = false; }
  ok(mono && borne && regle, "tailleDyn : bornée entre 1 et le plafond, croissante, et c × k pertes tiennent dans la marge");
  ok(M.tailleDyn(S, 2000) === 9 && M.tailleDyn(S, 1626.5) === 7 && M.tailleDyn(S, 340) === 1, "tailles lues : 9 à 2 000 $, 7 à 1 626,5 $, 1 à 340 $"); }
// 5. pertesFatales : taille fixe = plafond de marge / perte ; adaptative = la suite refaite ici à la main
{ const Sf = Object.assign({}, S0, { c: 4 }), Sd = Object.assign({}, S0, { c: 40, dyn: 5 });
  ok(M.pertesFatales(Sf, 2000) === Math.ceil(2000 / 166), `taille fixe, 4 contrats : ${M.pertesFatales(Sf, 2000)} pertes épuisent 2 000 $`);
  let m = 2000, k = 0; const tailles = []; while (m > 0) { const c = Math.max(1, Math.min(40, Math.floor(m / 207.5))); tailles.push(c); m -= c * 41.5; k++; }
  ok(M.pertesFatales(Sd, 2000) === k && k === 18 && tailles.slice(0, 10).join(",") === "9,7,6,5,4,3,2,2,2,1", `taille adaptative : ${k} pertes, tailles ${tailles.slice(0, 10).join(", ")}, puis 1`); }
// 6. simCompte passe la marge à la journée : une stratégie qui perd tout (p = 0) s'éteint au trade prévu, sur un et deux trades par jour
{ const mk = n => { const S = Object.assign({}, S0, { c: 40, p: 0, n, dyn: 5 }); return (g, o) => M.journeeDyn(S, g, o); };
  const A1 = M.simCompte(LUCID, mk(1), 3, 0, 4, null, 0), A2 = M.simCompte(LUCID, mk(2), 3, 0, 4, null, 0);
  ok(A1.tKo.every(t => t === 18), `1 trade par jour, taille adaptative : extinction au jour 18 (lu ${A1.tKo.join(", ")})`);
  ok(A2.tKo.every(t => t === 9), `2 trades par jour : la taille se recalcule dans la journée, extinction au jour 9 (lu ${A2.tKo.join(", ")})`);
  const Sf = Object.assign({}, S0, { c: 9, p: 0, n: 1 }), Af = M.simCompte(LUCID, (g, o) => M.journee(Sf, g, o), 3, 0, 4, null, 0);
  ok(Af.tKo.every(t => t === 6), `à taille fixe de 9 contrats : extinction au jour 6 (lu ${Af.tKo.join(", ")})`); }
// 7. tirages communs : à 1 contrat, la taille adaptative ne peut rien changer ; les challenges sont identiques un à un
{ const S = Object.assign({}, S0, { c: 1 }), Sd = Object.assign({}, S, { dyn: 5 });
  const A = M.simCompte(LUCID, (g, o) => M.journee(S, g, o), 7, 0, 600, null, 0), B = M.simCompte(LUCID, (g, o) => M.journeeDyn(Sd, g, o), 7, 0, 600, null, 0);
  let diff = 0; for (let i = 0; i < 600; i++) diff = Math.max(diff, Math.abs(A.cash[i] - B.cash[i]));
  ok(diff < 1e-6 && A.passe === B.passe, `plafond d'un contrat : mêmes 600 challenges, au cent près (écart max ${diff.toExponential(1)})`); }
// 8. à 4 contrats, les deux règles ne diffèrent que quand la marge passe sous 5 pertes : challenges identiques tant qu'elle n'y passe pas
{ const S = Object.assign({}, S0), Sd = Object.assign({}, S, { dyn: 5 });
  const A = M.simCompte(LUCID, (g, o) => M.journee(S, g, o), 9, 0, 3000, null, 0), B = M.simCompte(LUCID, (g, o) => M.journeeDyn(Sd, g, o), 9, 0, 3000, null, 0);
  let same = 0; for (let i = 0; i < 3000; i++) if (Math.abs(A.cash[i] - B.cash[i]) < 1e-6) same++;
  const ra = M.lireCompte(A, LUCID), rb = M.lireCompte(B, LUCID);
  ok(same > 300 && same < 3000, `4 contrats : ${same} challenges sur 3 000 identiques (la marge n'y est jamais passée sous 5 pertes), les autres diffèrent`);
  ok(rb.koEval + rb.ko0 < ra.koEval + ra.ko0, `réduire la taille près du plancher éteint moins de comptes sans retrait (${((rb.koEval + rb.ko0) * 100).toFixed(1)} % contre ${((ra.koEval + ra.ko0) * 100).toFixed(1)} %)`);
  console.log(`  pour information : gain net ${ra.E.toFixed(0)} $ (fixe) contre ${rb.E.toFixed(0)} $ (5 pertes d'avance), payés ${(ra.p1 * 100).toFixed(1)} % contre ${(rb.p1 * 100).toFixed(1)} %`); }

// ---------- la plus longue série de pertes ----------
// 9. sansSerie contre l'énumération de toutes les suites, n ≤ 14
{ let pire = 0, cas = 0;
  for (const q of [0.2, 0.5, 0.55, 0.8]) for (let n = 1; n <= 14; n++) {
    const P = new Float64Array(n + 2);   // P[L] = probabilité que la plus longue série vaille exactement L
    for (let s = 0; s < (1 << n); s++) { let run = 0, mx = 0, pr = 1; for (let i = 0; i < n; i++) { if (s >> i & 1) { run++; if (run > mx) mx = run; pr *= q; } else { run = 0; pr *= 1 - q; } } P[mx] += pr; }
    for (let m = 1; m <= n + 1; m++) { let lt = 0; for (let L = 0; L < m; L++) lt += P[L]; pire = Math.max(pire, Math.abs(lt - M.sansSerie(n, q, m))); cas++; } }
  ok(pire < 1e-12, `sansSerie = énumération exhaustive sur ${cas} cas (écart max ${pire.toExponential(1)})`); }
// 10. serieSup : part de 1, décroît, et P(au moins une perte) = 1 − p^n
{ const F = M.serieSup(100, 0.55); let dec = true; for (let m = 1; m < F.length; m++) if (F[m] > F[m - 1] + 1e-15) dec = false;
  ok(F[0] === 1 && dec, "serieSup commence à 1 et décroît");
  close(F[1], 1 - Math.pow(0.45, 100), 1e-12, "P(au moins une perte sur 100 trades)");
  close(M.serieSup(10, 0.5)[10], Math.pow(0.5, 10), 1e-15, "dix pertes sur dix trades à pile ou face"); }
// 11. contre un Monte Carlo : 100 trades, 55 % de pertes, série de 8 ou plus ; 250 trades, 80 % de pertes, série de 20 ou plus
for (const [n, q, m] of [[100, 0.55, 8], [250, 0.8, 20], [500, 0.45, 9]]) {
  const g = M.mulberry32(M.graine(n, m, 5)), K = 60000; let hit = 0;
  for (let k = 0; k < K; k++) { let run = 0, mx = 0; for (let i = 0; i < n; i++) { if (g() < q) { run++; if (run > mx) mx = run; } else run = 0; } if (mx >= m) hit++; }
  const mc = hit / K, ex = M.serieSup(n, q)[m], se = Math.sqrt(ex * (1 - ex) / K);
  ok(Math.abs(mc - ex) <= 3.5 * se + 1e-9, `${n} trades, ${q * 100} % de pertes, série ≥ ${m} : exact ${(ex * 100).toFixed(2)} %, Monte Carlo ${(mc * 100).toFixed(2)} % (± ${(2 * se * 100).toFixed(2)})`); }
// 12. bornes : jamais de perte, toujours des pertes
{ ok(M.serieSup(50, 0)[1] === 0, "sans perte possible, aucune série");
  const F = M.serieSup(12, 1); ok(F.length === 13 && F.every(v => v === 1), "à 100 % de pertes, la série fait toute la longueur"); }

console.log(`${nOk} contrôles passés, ${nKo} échecs`);
process.exit(nKo ? 1 : 0);
