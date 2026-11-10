// Banc de la synchronisation et de la question à Claude de prop/challenge-option32.html (et suivantes).
// Usage : node tools/challenge-option/synchro.mjs <dossier de rendu.mjs>   (lancer rendu.mjs d'abord : il écrit apercu.html)
// Hors de claude.ai, window.claude n'existe pas : le banc en pose un faux, dont la base est tenue ici, dans Node, et partagée
// entre plusieurs contextes de navigateur — autant d'« appareils » au stockage local distinct. Il vérifie le protocole de la page,
// pas le service : le premier vrai passage se fait après publication (une lecture de la base de l'artefact).
//  1. sans window.claude : la carte de synchronisation et « Demander à Claude » restent cachées, rien ne casse ;
//  2. un appareil écrit, un appareil neuf reprend tout ; le plus récent l'emporte ; un geste fait avant la réponse du nuage ne
//     l'écrase pas ; couper la synchronisation efface la copie en ligne ; un gros historique tient sous 256 Kio ;
//  3. la question à Claude part avec les chiffres de la page, et la réponse s'affiche.
import { createRequire } from "node:module";
import { join } from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const dos = process.argv[2];
if (!dos) { console.error("usage : node synchro.mjs <dossier>"); process.exit(1); }
const U = "file://" + join(dos, "apercu.html");
const b = await chromium.launch();
let ko = 0; const ok = (c, m) => { console.log(`${c ? "ok    " : "DÉFAUT"}  ${m}`); if (!c) ko++; };
const store = {}, demandes = [];
const faux = delai => `(() => {
  const subs = {}, mk = (path, v) => ({ id: path.split("/").pop(), exists: !!v, data: () => v ? JSON.parse(v) : undefined, metadata: { fromCache: false, hasPendingWrites: false } });
  const fire = async path => { const v = await window.__nuageLire(path); for (const f of subs[path] || []) f(mk(path, v)); };
  const db = { doc(path) { if (path.split("/").length % 2) throw new TypeError("chemin de document impair : " + path); return {
    get: async () => mk(path, await window.__nuageLire(path)),
    set: async data => { await window.__nuageEcrire(path, JSON.stringify(data)); fire(path); },
    delete: async () => { await window.__nuageEcrire(path, ""); fire(path); },
    onSnapshot(next) { (subs[path] = subs[path] || []).push(next); setTimeout(() => fire(path), ${delai}); return () => { subs[path] = (subs[path] || []).filter(f => f !== next); }; } }; } };
  const sample = async (input, opt) => { await window.__demande(String(input)); const t = "Réponse d’essai."; if (opt && opt.onText) opt.onText({ text: t, delta: t }); return { text: t, truncated: false, modelTierApplied: "default" }; };
  sample.limits = async () => ({ maxPromptBytes: 262144, modelTiers: ["default", "complex", "quick", "inherit"] });
  window.claude = { use: name => new Promise(res => setTimeout(() => res(name === "db" ? db : name === "user" ? { id: async () => "u_essai0000000000000000" } : name === "sample" ? sample : null), 40)) };
})();`;
async function appareil(delai, avecNuage = true) {
  const ctx = await b.newContext({ viewport: { width: 390, height: 860 } }), p = await ctx.newPage(), errs = [];
  p.on("pageerror", e => errs.push(e.message)); p.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
  if (avecNuage) { await ctx.exposeFunction("__nuageLire", path => store[path] || ""); await ctx.exposeFunction("__nuageEcrire", (path, v) => { if (v) store[path] = v; else delete store[path]; });
    await ctx.exposeFunction("__demande", t => { demandes.push(t); }); await p.addInitScript(faux(delai)); }
  return { ctx, p, errs };
}
const DOC = "data/users/u_essai0000000000000000/main";
const lu = () => store[DOC] ? JSON.parse(store[DOC]) : null;
const regle = (p, v) => p.evaluate(x => { const r = document.querySelector("#r-c"); r.value = String(x); r.dispatchEvent(new Event("input", { bubbles: true })); }, v);
const val = (p, s) => p.evaluate(x => document.querySelector(x).value, s);
const txt = (p, s) => p.evaluate(x => document.querySelector(x).textContent.replace(/\s+/g, " ").trim(), s);

// 1. sans window.claude
{ const A = await appareil(0, false); await A.p.goto(U + "#reglages"); await A.p.waitForTimeout(2500);
  ok(await A.p.evaluate(() => document.querySelector("#sync").hidden && document.querySelector("#ask").hidden), "hors de claude.ai : ni synchronisation ni question à Claude, la page tourne seule");
  ok(!A.errs.length, A.errs.length ? "erreurs : " + A.errs.join(" | ") : "aucune erreur sans window.claude"); await A.ctx.close(); }
// 2. premier appareil : rien à envoyer tant que rien n'a changé, puis les changements partent
const A = await appareil(60); await A.p.goto(U + "#reglages"); await A.p.waitForTimeout(2500);
ok(await A.p.evaluate(() => !document.querySelector("#sync").hidden) && /À jour/.test(await txt(A.p, "#sy-chip")) && !lu(), "appareil neuf, nuage vide : carte visible, « À jour », aucun document écrit");
await regle(A.p, 6); await A.p.goto(U + "#compte"); await A.p.waitForTimeout(1500);
for (const v of ["300", "−120"]) { await A.p.fill("#f-jr", v); await A.p.press("#f-jr", "Enter"); await A.p.waitForTimeout(200); }
await A.p.waitForTimeout(2600);
{ const d = lu(); ok(!!d && d.app === "option-challenge" && d.save.P.c === 6 && d.save.H.length === 2 && d.t > 0, `les changements partent en ligne : 6 contrats, 2 séances (document de ${store[DOC] ? store[DOC].length : 0} caractères)`); }
// 3. un appareil neuf reprend tout
const B = await appareil(60); await B.p.goto(U + "#reglages"); await B.p.waitForTimeout(3000);
ok(await val(B.p, "#r-c") === "6" && /2 journées/.test(await txt(B.p, "#data-n")) && /reprises/.test(await txt(B.p, "#sy-t")), `appareil neuf : 6 contrats et 2 séances repris de la copie en ligne (« ${(await txt(B.p, "#sy-t")).slice(0, 50)}… »)`);
await B.p.goto(U + "#compte"); await B.p.waitForTimeout(1500);
ok(await val(B.p, "#f-ex") === "180", `le compte suit : profit ${await val(B.p, "#f-ex")} $`);
// 4. le plus récent l'emporte : B passe à 8 contrats, A rechargé le reprend
await B.p.goto(U + "#reglages"); await B.p.waitForTimeout(1200); await regle(B.p, 8); await B.p.waitForTimeout(2600);
ok(lu().save.P.c === 8, "le second appareil écrit à son tour (8 contrats)");
await A.p.goto(U + "#reglages"); await A.p.reload(); await A.p.waitForTimeout(3000);
ok(await val(A.p, "#r-c") === "8", "le premier, rechargé, reprend la copie la plus récente");
// 5. un état local plus récent que la copie en ligne repart vers elle (la copie est vieillie à la main)
{ const d = lu(); d.t = 1000; d.save.P.c = 3; store[DOC] = JSON.stringify(d); await A.p.reload(); await A.p.waitForTimeout(3500);
  ok(await val(A.p, "#r-c") === "8" && lu().save.P.c === 8 && lu().t > 1000, "copie en ligne plus ancienne : l'appareil garde ses 8 contrats et la remet à jour"); }
// 6. appareil neuf, nuage lent (0,9 s) : un curseur bougé avant la réponse ne remplace pas les données en ligne
{ const C = await appareil(900); await C.p.goto(U + "#reglages"); await C.p.waitForTimeout(350); await regle(C.p, 2); await C.p.waitForTimeout(3600);
  ok(await val(C.p, "#r-c") === "8" && lu().save.P.c === 8 && lu().save.H.length === 2, `geste fait avant la réponse du nuage : les données en ligne l'emportent (curseur à ${await val(C.p, "#r-c")}, 2 séances intactes)`);
  ok(!C.errs.length, C.errs.length ? "erreurs : " + C.errs.join(" | ") : "aucune erreur sur l'appareil lent"); await C.ctx.close(); }
// 7. couper : la copie en ligne est effacée, plus rien ne part ; rallumer : tout repart
await A.p.evaluate(() => document.querySelector("#data-card").scrollIntoView({ block: "center" })); await A.p.click('#sg-sy [data-v="0"]'); await A.p.waitForTimeout(800);
ok(!lu() && /Coupée/.test(await txt(A.p, "#sy-chip")), "synchronisation coupée : copie en ligne effacée");
await regle(A.p, 5); await A.p.waitForTimeout(2500); ok(!lu(), "coupée, un changement ne part plus");
await A.p.reload(); await A.p.waitForTimeout(2500); ok(!lu() && await val(A.p, "#r-c") === "5" && /Coupée/.test(await txt(A.p, "#sy-chip")), "le choix est gardé après rechargement, les données locales aussi");
await A.p.evaluate(() => document.querySelector("#data-card").scrollIntoView({ block: "center" })); await A.p.click('#sg-sy [data-v="1"]'); await A.p.waitForTimeout(2500);
ok(!!lu() && lu().save.P.c === 5, "rallumée : l'état local repart en ligne");
// 8. un gros historique tient dans un document (256 Kio au plus)
{ await A.p.goto(U + "#compte"); await A.p.waitForTimeout(1500);
  let csv = "qty,pnl,boughtTimestamp,soldTimestamp\n"; const d0 = Date.UTC(2023, 0, 2);
  for (let i = 0, n = 0; n < 5200; i++) { const d = new Date(d0 + i * 864e5); if ([0, 6].includes(d.getUTCDay())) continue; const j = String(d.getUTCMonth() + 1).padStart(2, "0") + "/" + String(d.getUTCDate()).padStart(2, "0") + "/" + d.getUTCFullYear();
    for (let k = 0; k < 6 && n < 5200; k++, n++) csv += `2,${((n * 37) % 300) - 130},${j} 09:${String(30 + k).padStart(2, "0")}:00,${j} 09:${String(40 + k).padStart(2, "0")}:00\n`; }
  await A.p.evaluate(t => { document.querySelector("#b-csv-paste").click(); document.querySelector("#f-csv-ta").value = t; document.querySelector("#b-csv-read").click(); }, csv);   // posé d'un coup : 180 Ko ne se « tapent » pas
  await A.p.waitForTimeout(900); await A.p.evaluate(() => document.querySelector('[data-csv="ok"]').click()); await A.p.waitForTimeout(5000);
  const d = lu(), ko1 = store[DOC].length;
  ok(d.save.H.length > 800 && d.save.tr.length > 500 && ko1 < 256 * 1024, `${d.save.H.length} séances et ${d.save.tr.length} trades en ligne dans ${Math.round(ko1 / 1024)} Kio (limite 256)`); }
// 9. demander à Claude : visible, la question part avec les chiffres de la page
{ await A.p.goto(U + "#resultat"); await A.p.waitForTimeout(6000);
  ok(await A.p.evaluate(() => !document.querySelector("#ask").hidden), "« Demander à Claude » apparaît quand la capacité répond");
  await A.p.evaluate(() => document.querySelector("#ask").scrollIntoView({ block: "center" })); await A.p.click('#ask-q [data-q]'); await A.p.waitForTimeout(800);
  const rep = await txt(A.p, "#ask-a"), q = demandes[demandes.length - 1] || "", hero = (await txt(A.p, ".hnum")).replace(/\s/g, " ");
  ok(/Réponse d’essai/.test(rep), `la réponse s'affiche (« ${rep} »)`);
  ok(/CHIFFRES DE LA PAGE/.test(q) && /QUESTION/.test(q) && q.replace(/\s/g, " ").includes(hero) && /Règles du plan/.test(q), `la question part avec les chiffres de la page, gain net ${hero} compris (${q.length} caractères)`);
  ok(!/ALPOPT1|localStorage/.test(q) && q.length < 12000, "ni sauvegarde ni donnée brute dans l'envoi");
  await A.p.fill("#f-ask", "Combien de trades pour prouver mon taux ?"); await A.p.press("#f-ask", "Enter"); await A.p.waitForTimeout(600);
  ok(/Combien de trades pour prouver/.test(demandes[demandes.length - 1] || ""), "une question libre part de la même façon"); }
ok(!A.errs.length && !B.errs.length, A.errs.concat(B.errs).length ? "erreurs : " + A.errs.concat(B.errs).join(" | ") : "aucune erreur de script");
await b.close();
console.log(`\n${ko ? ko + " défaut(s)" : "tout est bon"}`);
process.exit(ko ? 1 : 0);
