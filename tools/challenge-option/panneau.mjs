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
// v14 : les explications sont repliées au départ ; avant, ouvertes. Le banc vérifie l'aller-retour dans les deux cas.
const g0 = await vu("#g11");
await p.click('[data-guide="g11"]'); await p.waitForTimeout(200); ok((await vu("#g11")) === !g0, "« ? » bascule l'explication");
await p.click('[data-guide="g11"]'); await p.waitForTimeout(200); ok((await vu("#g11")) === g0, "« ? » la remet comme avant");
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
// v10 et suivantes : « Ma journée » met le compte à jour, s'annule, s'efface ; Option et Quant répondent
if (await p.evaluate(() => !!document.querySelector("#f-jr"))) {
  await p.goto("file://" + join(dos, "apercu.html") + "#compte"); await p.waitForTimeout(2500);
  for (const v of ["300", "−200", "150"]) { await p.fill("#f-jr", v); await p.press("#f-jr", "Enter"); await p.waitForTimeout(250); }
  const champs = () => p.evaluate(() => ["#f-ex", "#f-eM", "#f-end", "#f-eb"].map(s => document.querySelector(s).value));
  const c1 = await champs();
  ok(JSON.stringify(c1) === JSON.stringify(["250", "300", "3", "300"]), `trois journées : profit 250, plus haut 300, 3 jours, meilleur 300 (lu ${c1})`);
  await p.waitForTimeout(800); ok(await vu("#s17"), "la courbe du compte réel se dessine");
  await p.screenshot({ path: join(dos, `journee-${W}.png`), fullPage: false });
  await (await p.$("#et-jr")).screenshot({ path: join(dos, `journee-carte-${W}.png`) });
  await p.click("#b-jr-undo"); await p.waitForTimeout(300);
  const c2 = await champs(); ok(JSON.stringify(c2) === JSON.stringify(["100", "300", "2", "300"]), `annuler la dernière : profit 100, 2 jours (lu ${c2})`);
  await p.click("#b-jr-clr"); await p.waitForTimeout(200); ok(await vu("#s17"), "un premier toucher sur Effacer ne fait que demander confirmation");
  await p.click("#b-jr-clr"); await p.waitForTimeout(300); ok(!(await vu("#s17")), "le second efface l'historique");
  await p.goto("file://" + join(dos, "apercu.html") + "#option"); await p.waitForTimeout(2000);
  ok(/vaut/.test(await p.evaluate(() => document.querySelector("#ao1").textContent)), "l'onglet Option répond à sa question");
  await p.goto("file://" + join(dos, "apercu.html") + "#quant"); await p.waitForTimeout(5000);
  ok(await p.evaluate(() => ["#aq1", "#aq2", "#aq3"].every(s => document.querySelector(s).textContent.length > 30)), "l'onglet Quant répond à ses trois questions");
}
// v12 et suivantes : « Que changer dès demain ? » et la limite journalière, avec Appliquer
if (await p.evaluate(() => !!document.querySelector("#lims"))) {
  await p.goto("file://" + join(dos, "apercu.html") + "#leviers"); await p.waitForTimeout(7000);
  const a = await p.evaluate(() => ({ acts: document.querySelectorAll("#acts .act").length, ans: document.querySelector("#act-ans").textContent, lims: document.querySelectorAll("#lims .lim").length, la: document.querySelector("#lim-ans").textContent }));
  ok(a.ans.length > 30 && !/Calcul/.test(a.ans), `la carte des gestes répond (${a.acts} geste(s))`);
  ok(a.lims >= 4 && a.la.length > 30, `la limite journalière compare ${a.lims} règles`);
  await (await p.$(".act-card")).screenshot({ path: join(dos, `gestes-${W}.png`) });
  await (await p.$("#lims")).screenshot({ path: join(dos, `limites-${W}.png`) });
  await p.click('#lims [data-lim="1"]'); await p.waitForTimeout(7000);
  const b = await p.evaluate(() => ({ ds: document.querySelector("#f-dStop").value, cur: (document.querySelector("#lims .lim.cur .t") || {}).textContent }));
  ok(Number(b.ds.replace(/\s/g, "")) > 0 && /1 perte/.test(b.cur || ""), `Appliquer pose la limite (stop journalier ${b.ds} $, ligne « ${b.cur} » marquée actuelle)`);
}
// v15 et suivantes : le Monte Carlo instantané de la vue option
if (await p.evaluate(() => !!document.querySelector("#b-mc"))) {
  await p.goto("file://" + join(dos, "apercu.html") + "#option"); await p.waitForTimeout(2500);
  await p.click('#sg-mcn [data-v="10000"]'); await p.click("#b-mc"); await p.waitForTimeout(1200);
  const m = await p.evaluate(() => ({ t: document.querySelector("#mc-res").textContent, b: document.querySelectorAll("#s1 .mch").length, c: document.querySelectorAll("#s1 .mcpath").length }));
  ok(/10\s000/.test(m.t) && m.b > 10 && m.c === 80, `10 000 comptes simulés d'un coup : ${m.b} barres, ${m.c} trajectoires`);
  await (await p.$("#p1")).screenshot({ path: join(dos, `mc-option-${W}.png`) });
}
// v19 et suivantes : la preuve d'un taux de gain, la sauvegarde qui passe d'une version à l'autre, les journées réelles rejouées
if (await p.evaluate(() => !!document.querySelector("#pf-card"))) {
  const U = "file://" + join(dos, "apercu.html"), lire = s => p.evaluate(x => document.querySelector(x).textContent, s);
  await p.goto(U + "#quant"); await p.waitForTimeout(2500);
  const a = await p.evaluate(() => ({ ans: document.querySelector("#aq6").textContent, l: document.querySelectorAll("#s19 .pf-l").length, d: document.querySelectorAll("#s19 .pf-d").length }));
  ok(/\d trades/.test(a.ans) && a.l === 1 && a.d >= 1, `la preuve répond et trace sa courbe (« ${a.ans.slice(0, 70)}… »)`);
  await p.fill("#f-vt", "120"); await p.fill("#f-vw", "58"); await p.waitForTimeout(500);
  const r1 = await lire("#pf-res");
  ok(/120/.test(r1) && /58/.test(r1) && /Pas encore prouvé/.test(r1), `58 gagnants sur 120 : pas encore prouvé (« ${r1.slice(0, 80)}… »)`);
  ok(await p.evaluate(() => document.querySelectorAll("#s19 > .pf-u").length === 1), "le bilan se marque sur la courbe (hors figure sortante du fondu)");
  await p.evaluate(() => document.querySelector("#pf-card").scrollIntoView({ block: "start" })); await p.waitForTimeout(1300);
  await (await p.$("#pf-card")).screenshot({ path: join(dos, `preuve-${W}.png`) });
  await p.fill("#f-vt", "1000"); await p.fill("#f-vw", "470"); await p.waitForTimeout(400);
  ok(/Prouvé à 95/.test(await lire("#pf-res")), "470 gagnants sur 1 000 contre un seuil de 41 % : prouvé");
  await p.fill("#f-vw", "1200"); await p.waitForTimeout(200);
  ok(/invalid/.test(await p.evaluate(() => document.querySelector("#w-vw").getAttribute("aria-invalid") ? "invalid" : "")) || /plus de gagnants/.test(await lire("#pf-res")), "plus de gagnants que de trades : refusé");
  // sauvegarde : 6 contrats et deux journées, copiés, stockage vidé, puis recollés
  await p.goto(U + "#compte"); await p.waitForTimeout(1500);
  for (const v of ["300", "−120"]) { await p.fill("#f-jr", v); await p.press("#f-jr", "Enter"); await p.waitForTimeout(200); }
  const exAvant = await p.evaluate(() => document.querySelector("#f-ex").value);
  await p.goto(U + "#reglages"); await p.waitForTimeout(1500);
  await p.evaluate(() => { const r = document.querySelector("#r-c"); r.value = "6"; r.dispatchEvent(new Event("input", { bubbles: true })); });
  await p.evaluate(() => document.querySelector("#data-card").scrollIntoView({ block: "center" }));
  await p.click("#b-exp"); await p.waitForTimeout(500);
  let code = await p.evaluate(() => { const t = document.querySelector("#exp-ta"); return t.hidden ? "" : t.value; });
  if (!code) code = await p.evaluate(() => navigator.clipboard.readText().catch(() => ""));
  ok(/^ALPOPT1:[A-Za-z0-9+/=]+$/.test(code), `la sauvegarde se copie (${code.length} caractères)`);
  await (await p.$("#data-card")).screenshot({ path: join(dos, `donnees-${W}.png`) });
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} }); await p.reload(); await p.waitForTimeout(2000);
  ok(await p.evaluate(() => document.querySelector("#r-c").value) === "4", "stockage vidé : retour à l'exemple (4 contrats)");
  await p.evaluate(() => document.querySelector("#data-card").scrollIntoView({ block: "center" }));
  await p.fill("#f-imp", "texte quelconque"); await p.click("#b-imp"); await p.waitForTimeout(200);
  ok(/pas une sauvegarde/.test(await lire("#imp-msg")) && await p.evaluate(() => document.querySelector("#r-c").value) === "4", "un texte quelconque est refusé, rien ne change");
  await p.fill("#f-imp", code.slice(0, 40) + "\n" + code.slice(40)); await p.click("#b-imp"); await p.waitForTimeout(600);
  const back = await p.evaluate(() => ({ c: document.querySelector("#r-c").value, msg: document.querySelector("#imp-msg").textContent, n: document.querySelector("#data-n").textContent }));
  ok(back.c === "6" && /2 journées/.test(back.msg) && /2 journées/.test(back.n), `la sauvegarde recollée (coupée en deux lignes) rend 6 contrats et 2 journées (${back.msg})`);
  await p.goto(U + "#compte"); await p.waitForTimeout(1500);
  const exApres = await p.evaluate(() => document.querySelector("#f-ex").value);
  ok(exApres === exAvant && exAvant !== "0", `le profit du compte revient avec les journées (${exAvant} $ avant, ${exApres} $ après)`);
  // journées réelles → simulation
  for (const v of ["150", "−80", "220", "40", "−60", "310", "90", "−140"]) { await p.fill("#f-jr", v); await p.press("#f-jr", "Enter"); await p.waitForTimeout(120); }
  ok(/Simuler avec mes journées/.test(await lire("#jr-sim")), "dès 10 journées, la simulation propose de rejouer les tiennes");
  await p.click('#jr-sim [data-js="journal"]'); await p.waitForTimeout(7000);
  const j = await p.evaluate(() => ({ mode: document.querySelector('#sg-mode [data-v="journal"]').getAttribute("aria-pressed"), jr: document.querySelector("#f-journal").value.split(/\s+/).length, sub: document.querySelector("#r-sub").textContent, sim: document.querySelector("#jr-sim").textContent }));
  ok(j.mode === "true" && j.jr === 10 && /ton journal/.test(j.sub) && /rejoue/.test(j.sim), `le mode journal rejoue les 10 journées (${j.sub.slice(0, 50)}…)`);
  await p.click('#jr-sim [data-js="trades"]'); await p.waitForTimeout(400);
  ok(await p.evaluate(() => document.querySelector('#sg-mode [data-v="trades"]').getAttribute("aria-pressed")) === "true", "un toucher ramène aux réglages de trades");
  ok(await largeur(), "aucun défilement horizontal après ces essais");
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
}
ok(!errs.length, errs.length ? "erreurs : " + errs.join(" | ") : "aucune erreur de script");
await b.close();
console.log(`\n${ko ? ko + " défaut(s)" : "tout est bon"} ; captures : ${dos}`);
process.exit(ko ? 1 : 0);
