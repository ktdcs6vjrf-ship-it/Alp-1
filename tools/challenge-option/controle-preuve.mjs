// Contrôle de la preuve d'un taux de gain (prop/challenge-option19.html et suivantes) : test binomial exact.
// Le bloc MODELE de la page est extrait tel quel : on vérifie le code livré, pas une copie.
// Usage : node tools/challenge-option/controle-preuve.mjs [page]   (code de sortie 1 si un contrôle échoue)
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

const ici = dirname(fileURLToPath(import.meta.url));
const page = process.argv[2] ? resolve(process.argv[2]) : join(ici, "../../prop/challenge-option19.html");
const html = readFileSync(page, "utf8");
const a = html.indexOf("/* MODELE:DEBUT"), b = html.indexOf("/* MODELE:FIN */");
if (a < 0 || b < 0) { console.error("bloc MODELE introuvable"); process.exit(1); }
const M = new Function(html.slice(a, b) + `
return {mulberry32,graine,zinv,tradeStats,lgamma,betaInc,binPmf,binSup,binCrit,puissance,pValeur,postSup,nPreuve};`)();

let nOk = 0, nKo = 0;
const ok = (c, m) => { if (c) nOk++; else { nKo++; console.log("ÉCHEC  " + m); } };
const close = (x, y, tol, m) => ok(Math.abs(x - y) <= tol, `${m} : ${x} contre ${y} (tolérance ${tol})`);
const rel = (x, y, tol, m) => ok(Math.abs(x - y) <= tol * Math.max(Math.abs(y), 1), `${m} : ${x} contre ${y} (relatif ${tol})`);

// 1. lgamma : factorielles, Γ(1/2) = √π, grandes valeurs (Stirling)
for (const n of [1, 2, 5, 10, 20, 50, 170]) { let f = 0; for (let k = 2; k < n; k++) f += Math.log(k); rel(M.lgamma(n), f, 1e-12, `lgamma(${n}) = ln(${n - 1}!)`); }
close(M.lgamma(0.5), 0.5 * Math.log(Math.PI), 1e-13, "lgamma(1/2)");
{ const x = 5000.5, st = (x - 0.5) * Math.log(x) - x + 0.5 * Math.log(2 * Math.PI) + 1 / (12 * x) - 1 / (360 * x ** 3); rel(M.lgamma(x), st, 1e-13, "lgamma(5000,5) contre Stirling"); }

// 2. queue binomiale : somme directe des probabilités, petites et grandes tailles
const somme = (n, k, p) => { let s = 0; for (let j = k; j <= n; j++) s += M.binPmf(n, j, p); return s; };
for (const [n, k, p] of [[10, 3, 0.3], [50, 20, 0.3], [50, 35, 0.6], [200, 95, 0.45], [1000, 450, 0.4125], [3000, 1300, 0.4125], [40, 0, 0.5], [40, 41, 0.5]]) {
  const t = M.binSup(n, k, p), d = k > n ? 0 : somme(n, Math.max(0, k), p);
  ok(Math.abs(t - d) <= 1e-11 + 1e-9 * d, `P(X ≥ ${k}) pour B(${n}, ${p}) : ${t} contre ${d}`);
}
{ let s = 0; for (let k = 0; k <= 300; k++) s += M.binPmf(300, k, 0.37); close(s, 1, 1e-12, "les probabilités de B(300 ; 0,37) somment à 1"); }

// 3. valeurs critiques : la taille du test non randomisé reste sous 5 %, et un gagnant de moins la dépasse
let pire = 0;
for (const p0 of [0.3, 0.4125, 0.5, 0.62]) for (let n = 5; n <= 2000; n += 7) {
  const k = M.binCrit(n, p0, 0.05), t = M.binSup(n, k, p0), t1 = M.binSup(n, k - 1, p0);
  if (!(t <= 0.05 + 1e-12) || !(k === 0 || t1 > 0.05)) { ok(false, `frontière fausse à n = ${n}, p0 = ${p0} : k = ${k}, tailles ${t} et ${t1}`); break; }
  pire = Math.max(pire, t);
}
ok(pire <= 0.05, `taille du test exact jamais au-dessus de 5 % (pire ${pire.toFixed(4)})`);

// 4. le test randomisé a une taille d'exactement 5 % à tout n : c'est sa loi nulle
{ let e = 0; for (let n = 1; n <= 3000; n += 3) e = Math.max(e, Math.abs(M.puissance(n, 0.4125, 0.4125, 0.05) - 0.05));
  ok(e < 1e-10, `sans avantage, le test se déclare convaincu 5 % du temps exactement (écart max ${e.toExponential(1)})`); }

// 5. puissance : monotone en p, croissante en n (à 1e-3 près), cohérente avec l'approximation normale aux grands n
{ const p0 = 0.4125; let mono = true; for (const n of [50, 300, 1000]) { let last = -1; for (let p = 0.4125; p <= 0.6; p += 0.005) { const w = M.puissance(n, p0, p, 0.05); if (w < last - 1e-12) mono = false; last = w; } }
  ok(mono, "la puissance croît avec le vrai taux de gain");
  let last = 0, chute = 0; for (let n = 1; n <= 3000; n++) { const w = M.puissance(n, p0, 0.45, 0.05); chute = Math.max(chute, last - w); last = Math.max(last, w); }
  ok(chute < 2e-3, `la puissance randomisée ne recule presque jamais quand n croît (recul max ${chute.toFixed(4)})`);
  const n = 2000, z = M.zinv(0.95), q = (p0 - 0.45) / Math.sqrt(0.45 * 0.55 / n) + z * Math.sqrt(p0 * (1 - p0) / (0.45 * 0.55));
  close(M.puissance(n, p0, 0.45, 0.05), 1 - normCdf(q), 0.01, "puissance à 2 000 trades contre la normale"); }
function normCdf(x) { return 0.5 * (1 + erf(x / Math.SQRT2)); }
function erf(x) { const t = 1 / (1 + 0.3275911 * Math.abs(x)), y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x); return x >= 0 ? y : -y; }

// 6. Monte Carlo : la puissance exacte contre 40 000 bilans tirés (graine fixe), à n = 470 et n = 1 100
for (const n of [470, 1100]) {
  const g = M.mulberry32(M.graine(19, n, 6)), p0 = 0.4125, p = 0.45, k = M.binCrit(n, p0, 0.05), t0 = M.binSup(n, k, p0), f0 = M.binPmf(n, k - 1, p0), gam = (0.05 - t0) / f0;
  let s = 0; const N = 40000;
  for (let i = 0; i < N; i++) { let w = 0; for (let j = 0; j < n; j++) if (g() < p) w++; if (w >= k) s++; else if (w === k - 1 && g() < gam) s++; }
  const e = M.puissance(n, p0, p, 0.05), se = Math.sqrt(e * (1 - e) / N);
  ok(Math.abs(s / N - e) <= 4 * se, `n = ${n} : puissance exacte ${e.toFixed(4)}, tirée ${(s / N).toFixed(4)} (± ${(2 * se).toFixed(4)})`);
}

// 7. a posteriori : bêta uniforme contre intégration numérique, symétries, cas simples
{ const w = 58, n = 120, p0 = 0.4125, N = 200000; let num = 0, den = 0;
  for (let i = 0; i < N; i++) { const x = (i + 0.5) / N, f = Math.exp(w * Math.log(x) + (n - w) * Math.log(1 - x) - 0); den += f; if (x > p0) num += f; }
  close(M.postSup(w, n, p0), num / den, 1e-6, "P(p > seuil | 58 sur 120) contre l'intégrale"); }
close(M.postSup(0, 0, 0.3), 0.7, 1e-12, "sans donnée, l'a priori uniforme rend 1 − p0");
close(M.postSup(5, 10, 0.5), 0.5, 1e-12, "5 sur 10 contre 50 % : une chance sur deux");
close(M.betaInc(2, 3, 0.4), 0.5248, 1e-12, "I_0,4(2, 3) = 0,5248");
close(M.pValeur(58, 120, 0.4125), M.binSup(120, 58, 0.4125), 0, "p-valeur = queue de la loi nulle");

// 8. trades nécessaires : à l'exemple (45 % pour un seuil de 41,3 %), une chance sur deux puis quatre sur cinq
{ const S = { pv: 2, tick: 0.25, c: 4, stop: 20, rr: 1.5, p: 0.45, n: 2, comm: 1, slip: 1, dStop: 0, dTgt: 0 }, ts = M.tradeStats(S), p0 = ts.pBE;
  const n50 = M.nPreuve(p0, 0.45, 0.05, 0.5), n80 = M.nPreuve(p0, 0.45, 0.05, 0.8);
  ok(M.puissance(n50, p0, 0.45, 0.05) >= 0.5 && M.puissance(n50 - 1, p0, 0.45, 0.05) < 0.5, `n50 = ${n50} : premier n à une chance sur deux`);
  ok(n50 > 380 && n50 < 560 && n80 > 950 && n80 < 1250, `ordres de grandeur : n50 = ${n50}, n80 = ${n80} (seuil ${(100 * p0).toFixed(2)} %)`);
  ok(M.nPreuve(p0, p0, 0.05, 0.5) === Infinity && M.nPreuve(p0, 0.3, 0.05, 0.5) === Infinity, "sans avantage, aucun nombre de trades ne suffit");
  console.log(`  exemple : seuil ${(100 * p0).toFixed(2)} %, une chance sur deux à ${n50} trades, quatre sur cinq à ${n80}`); }

console.log(`\n${nOk} contrôles passés, ${nKo} échecs`);
process.exit(nKo ? 1 : 0);
