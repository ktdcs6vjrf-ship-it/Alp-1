// Contrôle du modèle de prop/challenge-option.html.
// Le bloc MODELE de la page est extrait tel quel et exécuté ici : on vérifie le code livré, pas une copie.
// Usage : node tools/challenge-option/controle.mjs [page]   (code de sortie 1 si un contrôle échoue)
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

const ici = dirname(fileURLToPath(import.meta.url));
const page = process.argv[2] ? resolve(process.argv[2]) : join(ici, "../../prop/challenge-option.html");
const html = readFileSync(page, "utf8");
const a = html.indexOf("/* MODELE:DEBUT"), b = html.indexOf("/* MODELE:FIN */");
if (a < 0 || b < 0) { console.error("bloc MODELE introuvable"); process.exit(1); }
const M = new Function(html.slice(a, b) + `
return {mulberry32,graine,erfc,Q,Phi,phi,pin,kSat,retrait,pointMort,survie,gN,valeur,densite,queue,
        reussite,valeurChallenge,resume,deriveEquilibre,mcRegle,lireMC,trajectoire};`)();

let nOk = 0, nKo = 0;
function ok(cond, msg) { if (cond) { nOk++; } else { nKo++; console.log("ÉCHEC  " + msg); } }
function close(x, y, tol, msg) { ok(Math.abs(x - y) <= tol, `${msg} : ${x} contre ${y} (tolérance ${tol})`); }
const DEF = { F: 150, D: 2000, b: -2000, obj: 3000, cap: 4000, r: 0.5, wmax: 2000, N: 20, sigma: 450, mu: 0 };
const P = o => Object.assign({}, DEF, o);

// 1. erfc : valeurs de référence (précision annoncée 1,2e-7 relative)
for (const [x, v] of [[0, 1], [0.5, 0.4795001221869535], [1, 0.15729920705028513], [2, 0.004677734981047266],
                      [3, 2.209049699858544e-5], [5, 1.5374597944280349e-12], [-1, 1.8427007929497148]])
  ok(Math.abs(M.erfc(x) - v) <= 1.3e-7 * Math.max(v, 1e-300) + 1e-16, `erfc(${x})`);
close(M.Phi(1.959963984540054), 0.975, 2e-8, "Phi(1,96)");
close(M.pin(6, 8), M.Q(6) - M.Q(8), 1e-15, "pin dans la queue");

// 2. payoff : call spread de ratio 0,5, exercices 0 et 4 000
{ const p = P({});
  ok(M.kSat(p) === 4000, "saturation à 4 000");
  for (const [y, r] of [[-500, 0], [0, 0], [300, 150], [1000, 500], [4000, 2000], [9000, 2000]]) close(M.retrait(p, y), r, 1e-9, `retrait(${y})`);
  close(M.pointMort(p), 300, 1e-9, "point mort = 2F");
  ok(M.kSat(P({ cap: 5000 })) === 4000, "retrait max 2 000 lie avant un plafond de 5 000");
  ok(M.kSat(P({ wmax: 3000 })) === 4000, "plafond 4 000 lie avant un retrait max de 3 000");
  ok(M.pointMort(P({ F: 2500 })) === null, "aucun point mort si F dépasse le gain max"); }

// 3. formules fermées contre intégration numérique de la densité (Simpson)
function simpson(f, lo, hi, n) { const h = (hi - lo) / n; let s = f(lo) + f(hi);
  for (let i = 1; i < n; i++) s += f(lo + i * h) * (i % 2 ? 4 : 2); return s * h / 3; }
for (const [x, tau, mu] of [[0, 20, 0], [0, 20, 40], [0, 20, -40], [-1500, 5, 0], [3000, 12, 25], [500, 0.3, -10], [-1990, 2, 0]]) {
  const p = P({ mu }), s = p.sigma * Math.sqrt(tau), hi = x + mu * tau + 12 * s, n = 200000;
  const S = M.survie(p, x, tau), I = simpson(y => M.densite(p, y, x, tau), p.b, hi, n);
  close(I, S, 2e-7, `∫densité = survie (x=${x}, τ=${tau}, µ=${mu})`);
  const V = M.valeur(p, x, tau), J = simpson(y => M.retrait(p, y) * M.densite(p, y, x, tau), 0, hi, n);
  close(V, J, 2e-4 + 1e-7 * V, `valeur fermée = ∫retrait·densité (x=${x}, τ=${tau}, µ=${mu})`);
  for (const yq of [0, 300, 4000]) {
    const T = M.queue(p, yq, x, tau), U = simpson(y => M.densite(p, y, x, tau), Math.max(yq, p.b), hi, n);
    close(T, U, 2e-7, `queue(${yq}) = ∫ au-delà (x=${x}, τ=${tau})`);
  }
}
// 4. cas fermés exacts à dérive nulle
{ const p = P({}), s = 450 * Math.sqrt(20);
  close(M.survie(p, 0, 20), 2 * M.Phi(2000 / s) - 1, 1e-12, "survie(0) = 2Φ(D/σ√N) − 1 à µ = 0");
  close(M.reussite(p), 2000 / 5000, 1e-12, "réussite = D/(D+a) à µ = 0");
  close(M.reussite(P({ mu: 1e-9 })), 0.4, 1e-6, "réussite continue en µ = 0");
  ok(M.reussite(P({ obj: 0 })) === 1, "pas d'évaluation : réussite 1"); }
// 5. échéance : la valeur rejoint le payoff ; le plancher l'annule
{ const p = P({ mu: 15 });
  for (const x of [-1500, 150, 2000, 3900, 5000]) close(M.valeur(p, x, 1e-7), M.retrait(p, x), 0.05, `valeur(τ→0) = retrait (x=${x})`);
  ok(M.valeur(p, -2000, 10) === 0 && M.survie(p, -2001, 10) === 0, "valeur nulle au plancher");
  let prev = -1, mono = true; for (let x = -1999; x <= 9000; x += 37) { const v = M.valeur(p, x, 8); if (v < prev - 1e-9) mono = false; prev = v; }
  ok(mono, "valeur croissante en x");
  let pv = -1, mm = true; for (let mu = -200; mu <= 200; mu += 5) { const v = M.valeurChallenge(P({ mu })); if (v < pv - 1e-9) mm = false; pv = v; }
  ok(mm, "valeur du challenge croissante en µ"); }
// 6. dérive d'équilibre : la valeur y égale le prix
{ const p = P({}), e = M.deriveEquilibre(p, -225, 225);
  ok(e.cote === 0, "µ* dans la plage");
  close(M.valeurChallenge(P({ mu: e.mu })), 150, 1e-6, "valeur(µ*) = F");
  ok(M.deriveEquilibre(P({ F: 0 }), -225, 225).cote === -1, "F = 0 : couvert sur toute la plage"); }
// 7. Monte Carlo à plancher fixe (pont brownien) contre formules fermées, à 4 erreurs types
for (const mu of [-30, 0, 30]) {
  const p = P({ mu }), r = M.lireMC(M.mcRegle(p, 0, 200000, 7, false)), f = M.resume(p);
  const z = (m, v, se, l) => ok(Math.abs(m - v) <= 4 * se, `${l} µ=${mu} : MC ${m.toFixed(5)} ± ${se.toFixed(5)} contre ${v.toFixed(5)}`);
  z(r.pass, f.pass, r.sePass, "réussite");
  z(r.surv, f.surv, r.seSurv, "survie");
  z(r.E, f.E, r.seE, "retrait moyen");
  const sp = Math.sqrt(f.pProfit * (1 - f.pProfit) / r.n); z(r.pProfit, f.pProfit, sp, "P(profit)");
  const sk = Math.sqrt(f.pPlafond * (1 - f.pPlafond) / r.n); z(r.pPlafond, f.pPlafond, sk, "P(plafond)");
  console.log(`  µ=${String(mu).padStart(3)}  réussite ${f.pass.toFixed(4)} | MC ${r.pass.toFixed(4)}   survie ${f.surv.toFixed(4)} | MC ${r.surv.toFixed(4)}   retrait ${f.E.toFixed(1)} | MC ${r.E.toFixed(1)} ± ${r.seE.toFixed(1)}`);
}
// 8. règle trailing : à graine égale, le plancher qui monte ne peut qu'éteindre plus tôt
{ const p = P({}), fx = M.lireMC(M.mcRegle(p, 0, 50000, 11, false)), tr = M.lireMC(M.mcRegle(p, 0, 50000, 11, true));
  ok(tr.surv <= fx.surv && tr.E <= fx.E, `trailing ≤ fixe sur le compte financé (survie ${tr.surv.toFixed(4)} ≤ ${fx.surv.toFixed(4)}, retrait ${tr.E.toFixed(1)} ≤ ${fx.E.toFixed(1)})`);
  // à µ = 0, trailing sans verrou : P(atteindre a avant un recul de D) = e^{-a/D} ; avec verrou à 0 : e^{-1} · (D/a) pour a = 3 000, D = 2 000,
  // en surveillance continue. Ici l'objectif se constate à la clôture et le plancher suit la clôture : on vérifie seulement l'ordre de grandeur.
  console.log(`  trailing, µ=0 : réussite ${tr.pass.toFixed(4)}, survie ${tr.surv.toFixed(4)}, retrait ${tr.E.toFixed(1)} ; repère continu e^-1·2/3 = ${(Math.exp(-1) * 2 / 3).toFixed(4)}`);
  ok(tr.pass > 0.15 && tr.pass < 0.40, "réussite trailing dans l'ordre de grandeur du repère continu"); }
// 9. trajectoires communes : même graine, même chemin ; la dérive ne change que la pente
{ const p = P({}), t1 = M.trajectoire(p, 3, 12), t2 = M.trajectoire(p, 3, 12);
  ok(t1.xs.every((v, i) => v === t2.xs[i]) && t1.ko === t2.ko, "trajectoire déterministe");
  const q = M.trajectoire(P({ mu: 10 }), 3, 12); let same = true;
  const lim = Math.min(t1.ko ?? 99, q.ko ?? 99) * 12 - 1;
  for (let k = 0; k < lim && k <= t1.n; k++) if (Math.abs(q.xs[k] - t1.xs[k] - 10 * k / 12) > 1e-9) same = false;
  ok(same, "dérive ajoutée à bruit égal");
  let nko = 0; for (let s = 1; s <= 4000; s++) if (M.trajectoire(p, s, 12).ko !== null) nko++;
  const pko = 1 - M.survie(p, 0, 20), se = Math.sqrt(pko * (1 - pko) / 4000);
  ok(Math.abs(nko / 4000 - pko) <= 4 * se, `extinctions des trajectoires affichées : ${(nko / 4000).toFixed(4)} contre ${pko.toFixed(4)}`); }

const r0 = M.resume(P({}));
console.log(`\nExemple (F 150, D 2 000, objectif 3 000, 50 % plafonné à 4 000 / 2 000, N 20, σ 450, µ 0) :`);
console.log(`  survie ${(100 * r0.surv).toFixed(2)} %, retrait moyen ${r0.E.toFixed(1)} $, réussite ${(100 * r0.pass).toFixed(1)} %, valeur du challenge ${r0.V.toFixed(1)} $, µ* ${M.deriveEquilibre(P({}), -225, 225).mu.toFixed(2)} $/j`);
console.log(`\n${nOk} contrôles passés, ${nKo} échecs`);
process.exit(nKo ? 1 : 0);
