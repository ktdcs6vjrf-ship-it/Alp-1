// Contrôle de la recherche d'avantage (bloc EDGE de prop/challenge-option32.html et suivantes), calibrée contre son bruit.
// Les blocs MODELE et EDGE de la page sont extraits tels quels : on vérifie le code livré.
// Usage : node tools/challenge-option/controle-edge.mjs [page]   (code de sortie 1 si un contrôle échoue)
//  1. les cases et leur écart réduit, refaits à la main ;
//  2. l'échange en deux temps garde les résultats, séance par séance et strate par strate ;
//  3. taille du test sous la loi nulle (aucune case n'a d'effet) : 5 % de fichiers avec au moins une case « trouvée », y compris
//     quand les journées ont une couleur commune (journées de tendance) — là où une permutation simple en trouve bien plus ;
//  4. puissance : un effet planté sur une heure, ou une dépendance à la perte précédente, sont retrouvés ;
//  5. l'exemple inventé de la page : seul l'effet planté sort ; 6. bootstrap par séances calibré ; 7. reproductibilité.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

const ici = dirname(fileURLToPath(import.meta.url));
const page = process.argv[2] && process.argv[2] !== "-v" ? resolve(process.argv[2]) : join(ici, "../../prop/challenge-option32.html");
const html = readFileSync(page, "utf8");
const cut = (x, y) => { const a = html.indexOf(x), b = html.indexOf(y); return a < 0 || b < 0 ? null : html.slice(a, b); };
const mod = cut("/* MODELE:DEBUT", "/* MODELE:FIN */"), edge = cut("/* EDGE:DEBUT", "/* EDGE:FIN */");
if (!mod) { console.error("bloc MODELE introuvable"); process.exit(1); }
if (!edge) { console.log("page antérieure à la v32 : pas de bloc EDGE"); process.exit(0); }
const M = new Function(mod + "\n" + edge + "\nreturn {mulberry32,graine,quant,edgePrep,edgePerm,edgeFin,edgeShuffle,edgeZ,bootGrp,edgeDemo,EDGE_MIN};")();

let nOk = 0, nKo = 0;
const BAVARD = process.argv.includes("-v");   // -v : chaque contrôle passé s'écrit aussi, avec ses chiffres
const ok = (c, m) => { if (c) { nOk++; if (BAVARD) console.log("ok     " + m); } else { nKo++; console.log("ÉCHEC  " + m); } };
const iso = u => { const d = new Date(u); return d.getUTCFullYear() + "-" + String(d.getUTCMonth() + 1).padStart(2, "0") + "-" + String(d.getUTCDate()).padStart(2, "0"); };
const scan = (P, B, seed) => { const parts = []; for (let c = 0; c < 4; c++) parts.push(M.edgePerm(P, B / 4, seed * 16 + c)); return M.edgeFin(P, parts, 0); };

/* fabrique de fichiers : S séances de nMin à nMax trades ; win(r, ctx) donne la probabilité de gain du trade */
function fichier(g, S, nMin, nMax, win) {
  const rows = []; let day = Date.UTC(2026, 0, 5);
  for (let s = 0; s < S; s++) { while ([0, 6].includes(new Date(day).getUTCDay())) day += 864e5; const t = iso(day), n = nMin + Math.floor(g() * (nMax - nMin + 1)), teinte = g(); let h = 9 * 3600 + Math.floor(g() * 3600), prev = 0;
    for (let k = 0; k < n; k++) { const r = { t, q: 1, h, s: g() < 0.5 ? 1 : -1, d: null }, p = win(r, { teinte, prev, k }); r.v = g() < p ? 3.5 + 2 * g() : -1; prev = r.v; rows.push(r); h += 600 + Math.floor(g() * 3000); }
    day += 864e5; }
  return rows; }

// 1. cases et écart réduit refaits à la main
{ const g = M.mulberry32(3), rows = fichier(g, 40, 1, 4, () => 0.25), P = M.edgePrep(rows, "t"), N = rows.length;
  let m = 0; for (const r of rows) m += r.v; m /= N; let v = 0; for (const r of rows) v += (r.v - m) ** 2; const sd = Math.sqrt(v / N);
  let pire = 0, vus = 0;
  for (let k = 0; k < P.buckets.length; k++) { const b = P.buckets[k]; let n = 0, sum = 0;
    rows.forEach((r, i) => { let dans = false;
      if (b.dim === "Jour") dans = ["lundi", "mardi", "mercredi", "jeudi", "vendredi"][new Date(r.t + "T12:00:00Z").getUTCDay() - 1] === b.lab;
      else if (b.dim === "Heure") dans = Math.floor(r.h / 3600) + " h" === b.lab;
      else if (b.dim === "Sens") dans = (r.s === 1 ? "long" : "short") === b.lab;
      else if (b.dim === "Rang") { let rk = 0; for (let j = i - 1; j >= 0 && rows[j].t === r.t; j--) rk++; dans = ["1er trade de la séance", "2e trade", "3e trade", "4e et suivants"][Math.min(3, rk)] === b.lab; }
      else if (b.dim === "Après") dans = i > 0 && rows[i - 1].t === r.t && (/gagnant/.test(b.lab) ? rows[i - 1].v > 0 : rows[i - 1].v < 0);
      if (dans) { n++; sum += r.v; } });
    const z = (sum - n * m) / (sd * Math.sqrt(n * (N - n) / N)); vus++;
    pire = Math.max(pire, Math.abs(z - P.zobs[k]), Math.abs(n - P.nobs[k]), Math.abs(sum / n - P.mobs[k])); }
  ok(vus >= 12 && pire < 1e-9, `${vus} cases (jour, heure, sens, rang, après) : effectifs, moyennes et écarts réduits refaits à la main (écart max ${pire.toExponential(1)})`);
  ok(P.buckets.every(b => b.n >= M.EDGE_MIN) && !P.buckets.some(b => b.dim === "Durée"), "aucune case de moins de 8 trades ; la durée, connue après coup, n'est pas une case"); }
// 2. l'échange garde les résultats : mêmes valeurs dans chaque strate, et chaque séance reçoit les résultats d'une séance de même taille
{ const g = M.mulberry32(5), rows = fichier(g, 60, 1, 5, () => 0.3), P = M.edgePrep(rows, "t"), y = new Float64Array(P.N), tmp = new Int32Array(P.ng), h = M.mulberry32(9); let bon = true, bouge = 0;
  const cle = (a, j) => Array.from(a.subarray(P.gs[j], P.gs[j] + P.gl[j])).sort((u, v) => u - v).join(",");
  for (let b = 0; b < 50; b++) { M.edgeShuffle(P, h, y, tmp);
    for (const L of P.strata) { const src = Array.from(L, j => cle(P.x, j)).sort().join("|"), dst = Array.from(L, j => cle(y, j)).sort().join("|"); if (src !== dst) bon = false; }
    for (let i = 0; i < P.N; i++) if (y[i] !== P.x[i]) bouge++; }
  ok(bon && bouge > 0.2 * 50 * P.N, `l'échange garde les résultats de chaque séance, séance entière déplacée dans sa strate (${(bouge / 50 / P.N * 100).toFixed(0)} % des trades changent de résultat)`); }
// 3. taille : aucune case n'a d'effet, résultats très asymétriques (25 % de gagnants à 4,5 R)
function taille(K, mk, mode, B, lib, naif) {
  let trouve = 0, cases = 0;
  for (let k = 0; k < K; k++) { const g = M.mulberry32(M.graine(k, 17, lib.length)), rows = mk(g), P = M.edgePrep(rows, mode);
    if (naif) { P.strata = [Int32Array.from({ length: P.N }, (_, i) => i)]; P.gs = Int32Array.from({ length: P.N }, (_, i) => i); P.gl = new Int32Array(P.N).fill(1); }   // permutation simple, trade par trade
    const R = scan(P, B, k + 1); cases += R.rows.length; if (R.rows.some(r => r.padj <= 0.05)) trouve++; }
  return { f: trouve / K, cases: cases / K }; }
{ const K = 400, a = taille(K, g => fichier(g, 110, 1, 4, () => 0.25), "t", 400, "iid"), se = Math.sqrt(0.05 * 0.95 / K);
  ok(Math.abs(a.f - 0.05) <= 3.2 * se, `loi nulle, trades indépendants : au moins une case « trouvée » dans ${(a.f * 100).toFixed(1)} % des ${K} fichiers (5 % attendus ± ${(2 * se * 100).toFixed(1)}, ${a.cases.toFixed(0)} cases fouillées par fichier)`);
  // journées de tendance : un quart des séances gagne 7 fois sur 10, les autres 1 fois sur 20 ; le jour et l'heure n'y sont pour rien
  const mk = g => fichier(g, 90, 3, 6, (r, c) => c.teinte < 0.25 ? 0.7 : 0.05), b = taille(K, mk, "t", 400, "tendance"), n = taille(200, mk, "t", 400, "naif", true);
  ok(Math.abs(b.f - 0.05) <= 3.2 * se, `loi nulle avec journées de tendance : ${(b.f * 100).toFixed(1)} % de fichiers avec une case « trouvée » (5 % attendus)`);
  ok(n.f > 0.15, `la même loi nulle sous une permutation simple, trade par trade : ${(n.f * 100).toFixed(1)} % de fausses trouvailles — d'où l'échange par séances`);
  // séances seules (Ma journée) : jour de semaine et lendemain de gain ou de perte
  const s = taille(K, g => { const r = []; let day = Date.UTC(2026, 0, 5); for (let i = 0; i < 70; i++) { while ([0, 6].includes(new Date(day).getUTCDay())) day += 864e5; r.push({ t: iso(day), v: g() < 0.3 ? 250 + 500 * g() : -160 * (0.4 + g()) }); day += 864e5; } return r; }, "s", 400, "seances");
  ok(Math.abs(s.f - 0.05) <= 3.2 * se, `loi nulle sur des séances seules : ${(s.f * 100).toFixed(1)} % (5 % attendus, ${s.cases.toFixed(0)} cases)`); }
// 4. puissance : un effet planté est retrouvé
/* L'attente se calcule : une case de n trades où l'on gagne 4 fois sur 100 au lieu de 30 s'écarte de z ≈ −0,52·√n (écart de moyenne
   −1,43 R rapporté à l'écart-type d'ensemble 2,5 R, corrigé du poids de la case) ; le seuil du plus grand écart sur une vingtaine de
   cases est proche de 3. À 130 séances la case de 11 h compte une trentaine de trades (z ≈ −2,9) : une chance sur deux à trois sur
   quatre, donnée pour information. À 320 séances elle en compte 75 (z ≈ −4,5) : la détection doit être quasi certaine. */
{ const K = 120; let heure = 0, apres = 0, faux = 0, petit = 0;
  for (let k = 0; k < K; k++) { const g = M.mulberry32(M.graine(k, 23, 1)), R = scan(M.edgePrep(fichier(g, 320, 1, 4, r => r.h >= 11 * 3600 ? 0.04 : 0.3), "t"), 400, k + 1);
    if (R.rows.some(r => r.dim === "Heure" && +r.lab.split(" ")[0] >= 11 && r.padj <= 0.05 && r.z < 0)) heure++;
    if (R.rows.some(r => (r.dim === "Jour" || r.dim === "Sens") && r.padj <= 0.05)) faux++;
    const g2 = M.mulberry32(M.graine(k, 23, 2)), R2 = scan(M.edgePrep(fichier(g2, 130, 1, 4, r => r.h >= 11 * 3600 ? 0.04 : 0.3), "t"), 400, k + 1);
    if (R2.rows.some(r => r.dim === "Heure" && +r.lab.split(" ")[0] >= 11 && r.padj <= 0.05 && r.z < 0)) petit++; }
  ok(heure / K > 0.95, `effet planté sur les entrées de 11 h et plus (4 % de gagnants au lieu de 30 %), 320 séances : retrouvé dans ${(heure / K * 100).toFixed(0)} % des fichiers`);
  console.log(`  pour information : le même effet sur 130 séances (une trentaine de trades dans la case) est retrouvé dans ${(petit / K * 100).toFixed(0)} % des fichiers`);
  ok(faux / K < 0.12, `dans ces mêmes fichiers, le jour et le sens, sans effet, ne sortent que dans ${(faux / K * 100).toFixed(0)} % des cas`);
  for (let k = 0; k < K; k++) { const g = M.mulberry32(M.graine(k, 29, 1)), R = scan(M.edgePrep(fichier(g, 110, 3, 6, (r, c) => c.prev < 0 ? 0.08 : 0.42), "t"), 400, k + 1);
    if (R.rows.some(r => r.dim === "Après" && /perdant/.test(r.lab) && r.padj <= 0.05 && r.z < 0)) apres++; }
  ok(apres / K > 0.8, `dépendance plantée (8 % de gagnants après une perte, 42 % sinon) : « après un trade perdant » retrouvé dans ${(apres / K * 100).toFixed(0)} % des fichiers`); }
// 5. l'exemple inventé de la page : seul l'effet planté (entrées de 11 h et plus) sort du côté des pertes
{ const rows = M.edgeDemo(1), P = M.edgePrep(rows, "t"), parts = []; for (let c = 0; c < 8; c++) parts.push(M.edgePerm(P, 250, c + 1)); const R = M.edgeFin(P, parts, 40);
  const sig = R.rows.filter(r => r.padj <= 0.05), neg = sig.filter(r => r.z < 0);
  ok(rows.length > 250 && rows.every(r => r.h != null && (r.s === 1 || r.s === -1)), `exemple : ${rows.length} trades sur 130 séances, heure et sens connus`);
  ok(neg.length >= 1 && neg.every(r => r.dim === "Heure" && +r.lab.split(" ")[0] >= 11), `exemple : la seule case perdante qui résiste est l'heure plantée (${neg.map(r => r.lab + ", p corrigée " + r.padj.toFixed(3)).join(" ; ")})`);
  ok(!sig.some(r => r.dim === "Jour" || r.dim === "Sens"), `exemple : ni le jour ni le sens ne sortent (cases retenues : ${sig.map(r => r.lab).join(", ")})`);
  ok(R.ghosts.length === 40 && R.ghosts[0].length === R.rows.length && R.rows.every(r => r.lo <= r.hi), "tirages gardés pour l'animation, bandes du hasard ordonnées");
  const R2 = M.edgeFin(P, [0, 1, 2, 3, 4, 5, 6, 7].map(c => M.edgePerm(P, 250, c + 1)), 40);
  ok(JSON.stringify(R2.rows) === JSON.stringify(R.rows), "même graine, mêmes tranches : mêmes p, au chiffre près"); }
// 6. bootstrap par séances studentisé : sous une moyenne EXACTEMENT nulle et des journées de tendance, p ≤ 5 % dans 5 % des cas au plus ;
//    l'intervalle à 90 % couvre 9 fois sur 10. La probabilité de gain des journées ordinaires est calculée pour annuler la moyenne :
//    0,3 × (0,4 × 4,5 − 0,6) + 0,7 × (p × 4,5 − (1 − p)) = 0, soit p = (1 − 0,36 / 0,7) / 5,5. (Une moyenne « à peu près » nulle de
//    +0,03 R suffisait à faire lire 7 % de rejets : l'attente d'un contrôle se calcule.)
{ const K = 1500, p2 = (1 - 0.36 / 0.7) / 5.5; let rej = 0, couv = 0;
  for (let k = 0; k < K; k++) { const g = M.mulberry32(M.graine(k, 31, 1)), rows = fichier(g, 80, 2, 5, (r, c) => c.teinte < 0.3 ? 0.4 : p2);
    const P = M.edgePrep(rows, "t"), bt = M.bootGrp(P, 1000, k + 1);
    if (bt.p <= 0.05) rej++; if (bt.lo <= 0 && 0 <= bt.hi) couv++; }
  const se = Math.sqrt(0.05 * 0.95 / K);
  ok(rej / K <= 0.05 + 3 * se && rej / K >= 0.02, `bootstrap par séances studentisé, moyenne nulle : « avantage prouvé » dans ${(rej / K * 100).toFixed(1)} % des ${K} fichiers (5 % attendus ± ${(2 * se * 100).toFixed(1)})`);
  ok(Math.abs(couv / K - 0.9) <= 3 * Math.sqrt(0.09 / K), `l'intervalle à 90 % couvre la vraie moyenne dans ${(couv / K * 100).toFixed(1)} % des fichiers`); }

console.log(`${nOk} contrôles passés, ${nKo} échecs`);
process.exit(nKo ? 1 : 0);
