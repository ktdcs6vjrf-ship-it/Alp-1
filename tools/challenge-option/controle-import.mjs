// Contrôle de la lecture d'un fichier de trades (bloc IMPORT de prop/challenge-option23.html et suivantes).
// Le bloc est extrait tel quel : on vérifie le code livré. Usage : node tools/challenge-option/controle-import.mjs [page]
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

const ici = dirname(fileURLToPath(import.meta.url));
const page = process.argv[2] ? resolve(process.argv[2]) : join(ici, "../../prop/challenge-option23.html");
const html = readFileSync(page, "utf8");
const a = html.indexOf("/* IMPORT:DEBUT"), b = html.indexOf("/* IMPORT:FIN */");
if (a < 0 || b < 0) { console.error("bloc IMPORT introuvable"); process.exit(1); }
const M = new Function(html.slice(a, b) + "\nreturn {csvSplit,normH,findCol,lireMontant,lireDate,ordreJM,lireCSV};")();

let nOk = 0, nKo = 0;
const ok = (c, m) => { if (c) nOk++; else { nKo++; console.log("ÉCHEC  " + m); } };
const eq = (x, y, m) => ok(JSON.stringify(x) === JSON.stringify(y), `${m} : ${JSON.stringify(x)} contre ${JSON.stringify(y)}`);
const close = (x, y, m) => ok(Math.abs(x - y) < 1e-9, `${m} : ${x} contre ${y}`);

// 1. découpage d'une ligne : guillemets, séparateur dans un champ, guillemets doublés
eq(M.csvSplit('a,"b,c",d', ","), ["a", "b,c", "d"], "virgule entre guillemets");
eq(M.csvSplit('a,"il dit ""oui""",b', ","), ["a", 'il dit "oui"', "b"], "guillemets doublés");
eq(M.csvSplit("x;y; z ", ";"), ["x", "y", "z"], "point-virgule, espaces retirés");
// 2. montants
for (const [s, v] of [["$1,234.56", 1234.56], ["1.234,56", 1234.56], ["(12.00)", -12], ["$(160.00)", -160], ["-$4.00", -4], ["−5", -5], ["12,5", 12.5], ["1,234", 1234],
  ["1 234,50", 1234.5], ["+80", 80], ["€ 3,10", 3.1], ["0", 0]]) close(M.lireMontant(s), v, `montant « ${s} »`);
for (const s of ["abc", "", "12-3", "$"]) ok(Number.isNaN(M.lireMontant(s)), `« ${s} » n'est pas un montant`);
// 3. dates : formats, validité, rattachement du week-end
eq(M.lireDate("2026-11-03 15:00:00"), "2026-11-03", "ISO avec heure");
eq(M.lireDate("31/12/2026", true), "2026-12-31", "jour d'abord");
eq(M.lireDate("12/31/2026 09:30", false), "2026-12-31", "mois d'abord (US)");
eq(M.lireDate("2026-02-30"), null, "30 février refusé");
eq(M.lireDate("13/13/2026", true), null, "mois 13 refusé");
eq(M.lireDate("2026-11-08"), "2026-11-09", "un dimanche va à la séance du lundi");
eq(M.lireDate("2026-11-07"), "2026-11-06", "un samedi va à la séance du vendredi");
eq(M.lireDate("03/11/26", true), "2026-11-03", "année sur deux chiffres");
eq(M.ordreJM(["03/11/2026", "15/11/2026"]), true, "un 15 en tête : jour d'abord");
eq(M.ordreJM(["11/03/2026", "11/15/2026"]), false, "un 15 en second : mois d'abord");
eq(M.ordreJM(["03/04/2026"]), null, "ambigu");
// 4. un export de type Tradovate (Performance) : mois d'abord, parenthèses, frais déduits par contrat
{ const csv = `symbol,_priceFormat,_priceFormatType,_tickSize,buyFillId,sellFillId,qty,buyPrice,sellPrice,pnl,boughtTimestamp,soldTimestamp,duration
MNQZ6,-2,0,0.25,1,2,4,21000.00,21010.00,$80.00,11/03/2026 09:31:05,11/03/2026 09:35:10,4min 5sec
MNQZ6,-2,0,0.25,3,4,4,21020.00,21000.00,$(160.00),11/03/2026 10:01:00,11/03/2026 10:02:00,1min
MNQZ6,-2,0,0.25,5,6,2,21000.00,21030.00,$120.00,11/04/2026 09:40:00,11/04/2026 09:50:00,10min
MNQZ6,-2,0,0.25,7,8,1,20990.00,21000.00,$20.00,11/08/2026 18:30:00,11/08/2026 18:45:00,15min`;
  const r = M.lireCSV(csv, { comm: 1 });
  ok(!r.err && r.dm === false && r.cols.pnl === "pnl" && r.cols.date === "soldTimestamp" && r.cols.qty === "qty", `colonnes et ordre US reconnus (${JSON.stringify(r.cols)}, dm ${r.dm})`);
  eq(r.days.map(d => [d.t, d.v, d.n, d.w]), [["2026-11-03", -88, 2, 1], ["2026-11-04", 118, 1, 1], ["2026-11-09", 19, 1, 1]], "séances : frais 1 $ par contrat, dimanche soir → lundi");
  ok(r.n === 4 && r.skip === 0 && r.fee === 11, `4 trades, 11 $ de frais (lu ${r.n}, ${r.fee})`);
  const r2 = M.lireCSV(csv, { comm: 0 });
  eq(r2.days.map(d => d.v), [-80, 120, 20], "sans frais réglés, le résultat brut");
  const r3 = M.lireCSV(csv, { comm: 0, dm: true });
  eq(r3.days.map(d => d.t), ["2026-03-11", "2026-04-10", "2026-08-11"], "ordre imposé jour d'abord : 11 mars, 11 avril (un samedi, rattaché au vendredi 10), 11 août"); }
// 5. un fichier français : point-virgule, virgule décimale, jour d'abord déduit
{ const csv = "Date;Résultat;Contrats\n03/11/2026;120,50;2\n04/11/2026;-80,25;2\n15/11/2026;1 234,50;1\nligne;cassée\n";
  const r = M.lireCSV(csv, { comm: 0 });
  ok(!r.err && r.sep === ";" && r.dm === true && r.dmSur && r.cols.pnl === "Résultat", `séparateur ; et jour d'abord (${r.sep}, ${r.dm})`);
  eq(r.days.map(d => [d.t, d.v]), [["2026-11-03", 120.5], ["2026-11-04", -80.25], ["2026-11-16", 1234.5]], "montants à virgule ; le dimanche 15 va au lundi 16");
  ok(r.skip === 1, `une ligne illisible ignorée (lu ${r.skip})`); }
// 6. dates ISO, colonne de frais, montants entre guillemets
{ const csv = 'Exit time,Profit,Commission\n2026-11-02 15:00:00,"1,250.00",2.04\n2026-11-02 16:00:00,(45.50),2.04\n';
  const r = M.lireCSV(csv, { comm: 5 });
  ok(r.cols.fee === "Commission", "colonne de frais reconnue, le réglage n'est pas appliqué");
  eq(r.days.map(d => [d.t, d.v, d.n, d.w]), [["2026-11-02", 1200.42, 2, 1]], "frais du fichier déduits trade par trade"); }
// 7. erreurs lisibles
ok(/colonne de résultat/.test(M.lireCSV("date,symbol\n2026-11-02,MNQ").err || ""), "sans colonne de résultat : message clair");
ok(/colonne de date/.test(M.lireCSV("pnl,symbol\n12,MNQ").err || ""), "sans colonne de date : message clair");
ok(/vide/.test(M.lireCSV("pnl,date").err || ""), "en-tête seul : message clair");
ok(/vide/.test(M.lireCSV("").err || ""), "fichier vide : message clair");
// 8. un gros fichier : 20 000 trades lus en moins d'une seconde, et la somme est juste
{ let s = "qty,pnl,date\n", tot = 0; for (let i = 0; i < 20000; i++) { const v = ((i * 37) % 200) - 90; tot += v; s += `1,${v},2026-10-${String(1 + (i % 28)).padStart(2, "0")}\n`; }
  const t0 = Date.now(), r = M.lireCSV(s, { comm: 0 }), ms = Date.now() - t0;
  close(r.days.reduce((x, d) => x + d.v, 0), tot, "somme des séances = somme des trades");
  ok(r.n === 20000 && ms < 1000, `20 000 trades lus en ${ms} ms`); }

console.log(`\n${nOk} contrôles passés, ${nKo} échecs`);
process.exit(nKo ? 1 : 0);
