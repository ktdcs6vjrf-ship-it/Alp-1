// Banc du mouvement de prop/challenge-option5.html (et suivantes) : ce que rendu.mjs ne voit pas.
// Usage : node tools/challenge-option/vivant.mjs <dossier de rendu.mjs> [largeur]
// Lancer rendu.mjs d'abord : il écrit apercu.html (page + vraies fontes) dans le dossier.
//  1. laisse tourner l'animation, puis capture le fond du résultat, l'aperçu des réglages, la carte et le relief ;
//  2. mesure les images par seconde pendant la rotation du relief ;
//  3. recharge chaque onglet en « mouvement réduit » : aucune erreur, et une image fixe déjà remplie.
// Code de sortie 1 au premier défaut.
import { createRequire } from "node:module";
import { join } from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const dos = process.argv[2], W = +(process.argv[3] || 390);
if (!dos) { console.error("usage : node vivant.mjs <dossier> [largeur]"); process.exit(1); }
const page = "file://" + join(dos, "apercu.html");
const b = await chromium.launch();
let defauts = 0;

const p = await b.newPage({ viewport: { width: W, height: 900 } }), errs = [];
p.on("pageerror", e => errs.push(e.message));
await p.goto(page + "#resultat"); await p.waitForTimeout(9000);
await (await p.$(".hero")).screenshot({ path: join(dos, `vivant-hero-${W}.png`) });
await p.evaluate(() => { location.hash = "reglages"; }); await p.waitForTimeout(800);
await p.evaluate(() => document.querySelector("#pvw").scrollIntoView({ block: "center" })); await p.waitForTimeout(6000);
await (await p.$("#pvw")).screenshot({ path: join(dos, `vivant-apercu-${W}.png`) });
const compteur = await p.evaluate(() => document.querySelector("#pv-t").textContent);
await p.evaluate(() => { location.hash = "leviers"; }); await p.waitForTimeout(800);
await p.evaluate(() => document.querySelector("#p8").scrollIntoView({ block: "center" })); await p.waitForTimeout(1500);
await (await p.$("#p8")).screenshot({ path: join(dos, `vivant-carte-${W}.png`) });
await p.evaluate(() => document.querySelector("#p9").scrollIntoView({ block: "center" })); await p.waitForTimeout(2500);
await (await p.$("#p9")).screenshot({ path: join(dos, `vivant-relief-${W}.png`) });
const fps = await p.evaluate(() => new Promise(r => { let n = 0; const t0 = performance.now();
  (function f() { n++; if (performance.now() - t0 < 2000) requestAnimationFrame(f); else r(n / 2); })(); }));
const ok1 = !errs.length && fps >= 45 && /Réussies \d+ sur [1-9]/.test(compteur);
if (!ok1) defauts++;
console.log(`animé       ${ok1 ? "ok" : "DÉFAUT"}  ${fps} images/s, aperçu « ${compteur} »${errs.length ? "  erreurs : " + errs.join(" | ") : ""}`);

const ctx = await b.newContext({ viewport: { width: W, height: 900 }, reducedMotion: "reduce" }), q = await ctx.newPage(), errs2 = [];
q.on("pageerror", e => errs2.push(e.message));
for (const v of ["resultat", "reglages", "option", "quant", "leviers"]) { await q.goto(page + "#" + v); await q.waitForTimeout(3000); }
await q.goto(page + "#resultat"); await q.waitForTimeout(2500);
const encre = await q.evaluate(() => { const c = document.querySelector("#amb"), d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
  let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 0) n++; return n; });
await (await q.$(".hero")).screenshot({ path: join(dos, `calme-hero-${W}.png`) });
const ok2 = !errs2.length && encre > 0;
if (!ok2) defauts++;
console.log(`sans mouvement ${ok2 ? "ok" : "DÉFAUT"}  fond déjà dessiné (${encre} pixels)${errs2.length ? "  erreurs : " + errs2.join(" | ") : ""}`);
await b.close();
console.log(`captures : ${dos}`);
process.exit(defauts ? 1 : 0);
