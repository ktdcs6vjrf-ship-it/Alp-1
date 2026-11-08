// Banc des commandes de la v8 (et suivantes) : panneau Paramètres, cartes repliables, explications « ? », relief.
// Usage : node tools/challenge-option/panneau.mjs <dossier de rendu.mjs> [largeur]   (lancer rendu.mjs d'abord : il écrit apercu.html)
// Vérifie, dans le vrai navigateur, que chaque bouton cache puis rend ce qu'il commande, que le panneau change le résultat
// depuis l'onglet Leviers, et qu'aucune erreur ni aucun défilement horizontal n'apparaît. Écrit des captures. Code de sortie 1 au premier défaut.
import { createRequire } from "node:module";
import { join } from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const dos = process.argv[2], W = +(process.argv[3] || 390);
if (!dos) { console.error("usage : node panneau.mjs <dossier> [largeur]"); process.exit(1); }
const b = await chromium.launch(), p = await b.newPage({ viewport: { width: W, height: 860 } }), errs = [];
p.on("pageerror", e => errs.push(e.message)); p.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
let ko = 0; const ok = (c, m) => { console.log(`${c ? "ok    " : "DÉFAUT"}  ${m}`); if (!c) ko++; };
const vu = sel => p.evaluate(s => { const e = document.querySelector(s); return !!e && e.getClientRects().length > 0; }, sel);
const largeur = () => p.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);

await p.goto("file://" + join(dos, "apercu.html") + "#leviers"); await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
await p.goto("file://" + join(dos, "apercu.html") + "#leviers"); await p.waitForTimeout(6000);
// explications : visibles d'abord, cachées puis rendues par « ? »
ok(await vu("#g11"), "l'explication du premier graphique est visible au départ");
await p.click('[data-guide="g11"]'); await p.waitForTimeout(200); ok(!(await vu("#g11")), "« ? » cache l'explication");
await p.click('[data-guide="g11"]'); await p.waitForTimeout(200); ok(await vu("#g11"), "« ? » la rend");
// relief : caché d'abord, affiché par son bouton, dessiné
ok(!(await vu("#c9")), "le relief est replié au départ");
await p.click("#b-relief"); await p.waitForTimeout(400); await p.evaluate(() => document.querySelector("#p9").scrollIntoView({ block: "center" })); await p.waitForTimeout(1200);
const encre = await p.evaluate(() => { const c = document.querySelector("#c9"), d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 40) if (d[i] > 0) n++; return n; });
ok(encre > 100, `le relief s'affiche et se dessine (${encre} points)`);
// réponses écrites au-dessus des graphiques
const rep = await p.evaluate(() => ["#lv-ans", "#tor-ans", "#ca-ans"].map(s => document.querySelector(s).textContent));
ok(rep.every(t => t.length > 30 && !/Calcul en cours/.test(t)), "les trois réponses sont écrites");
// panneau Paramètres depuis Leviers : s'ouvre, change le résultat, se referme
await p.evaluate(() => scrollTo(0, 0)); await p.click("#b-par"); await p.waitForTimeout(600);
ok(await vu("#sheet") && await vu("#q-p"), "le bouton Paramètres ouvre le panneau, curseurs compris");
await p.screenshot({ path: join(dos, `panneau-ouvert-${W}.png`) });
const avant = await p.evaluate(() => document.querySelector("#lv-ans").textContent);
await p.evaluate(() => { const r = document.querySelector("#q-p"); r.value = "50"; r.dispatchEvent(new Event("input", { bubbles: true })); });
await p.waitForTimeout(7000);
const apres = await p.evaluate(() => ({ ans: document.querySelector("#lv-ans").textContent, main: document.querySelector("#r-p").value, out: document.querySelector("#qo-p").textContent, strip: document.querySelector("#sh-strip").textContent }));
ok(apres.main === "50" && /50/.test(apres.out), "le curseur du panneau règle aussi celui des réglages");
ok(apres.ans !== avant, "les leviers se recalculent derrière le panneau");
ok(/Gain net/.test(apres.strip), "le panneau affiche le résultat en direct");
ok(await largeur(), "aucun défilement horizontal, panneau ouvert");
await p.click("#b-sh-x"); await p.waitForTimeout(700); ok(!(await vu("#sheet")), "la croix cache le panneau");
await p.click("#b-par"); await p.waitForTimeout(500); await p.keyboard.press("Escape"); await p.waitForTimeout(700); ok(!(await vu("#sheet")), "Échap cache le panneau");
// cartes de paramètres repliables, avec leur résumé
await p.goto("file://" + join(dos, "apercu.html") + "#reglages"); await p.waitForTimeout(2500);
await p.click('[data-col="st"]'); await p.waitForTimeout(300);
ok(!(await vu("#b-st")) && await vu("#sum-st"), "la flèche replie ta stratégie et montre son résumé");
await p.screenshot({ path: join(dos, `reglages-replie-${W}.png`) });
await p.click("#sum-st"); await p.waitForTimeout(300); ok(await vu("#b-st"), "un toucher sur le résumé déplie la carte");
await p.click('[data-col="rg"]'); await p.waitForTimeout(200); await p.reload(); await p.waitForTimeout(2500);
ok(!(await vu("#b-rg")) && await vu("#sum-rg"), "la carte repliée le reste à la visite suivante");
await p.click('[data-col="rg"]');
await p.goto("file://" + join(dos, "apercu.html") + "#compte"); await p.waitForTimeout(2500);
await p.click('[data-col="et"]'); await p.waitForTimeout(300); ok(!(await vu("#b-et")) && /Évaluation/.test(await p.evaluate(() => document.querySelector("#sum-et").textContent)), "l'état du compte se replie en une ligne");
await p.click('[data-col="et"]');
ok(!errs.length, errs.length ? "erreurs : " + errs.join(" | ") : "aucune erreur de script");
await b.close();
console.log(`\n${ko ? ko + " défaut(s)" : "tout est bon"} ; captures : ${dos}`);
process.exit(ko ? 1 : 0);
