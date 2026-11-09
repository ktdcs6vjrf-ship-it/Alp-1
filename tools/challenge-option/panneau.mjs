// Banc des commandes de la v8 (et suivantes) : panneau Paramètres, cartes repliables, explications « ? », relief ;
// v26 : plans de challenge, feuille de route, paper ; v27 : journal de trades en R et scellement ;
// v28 : la stratégie dans le paper, setups, preuve par l'espérance en R ; v29 : sens de la tendance, défauts non enregistrés.
// Usage : node tools/challenge-option/panneau.mjs <dossier de rendu.mjs> [largeur]   (lancer rendu.mjs d'abord : il écrit apercu.html)
// Vérifie, dans le vrai navigateur, que chaque bouton cache puis rend ce qu'il commande, que le panneau change le résultat
// depuis l'onglet Leviers, et qu'aucune erreur ni aucun défilement horizontal n'apparaît. Écrit des captures. Code de sortie 1 au premier défaut.
import { createRequire } from "node:module";
import { join } from "node:path";
import { writeFileSync } from "node:fs";
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
// v21 et suivantes : séances datées avec leurs trades, calendrier, journées contre réglages, rappel du compte, reprise des trades
if (await p.evaluate(() => !!document.querySelector("#et-cal"))) {
  const U = "file://" + join(dos, "apercu.html"), lire = s => p.evaluate(x => document.querySelector(x).textContent, s);
  await p.goto(U + "#compte"); await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} }); await p.reload(); await p.waitForTimeout(2500);
  ok(await p.evaluate(() => document.querySelector("#acs").hidden && document.querySelector("#et-cal").hidden), "compte neuf : ni rappel du compte ni calendrier");
  const seances = [["2026-10-27", "240", "3", "2"], ["2026-10-28", "−180", "2", "0"], ["2026-10-29", "95", "2", "1"], ["2026-10-30", "410", "3", "3"], ["2026-10-31", "−60", "", ""],
    ["2026-11-03", "120", "2", "1"], ["2026-11-04", "−320", "2", "0"], ["2026-11-05", "60", "2", "1"]];
  for (const [d, v, n, w] of seances) { await p.fill("#f-jd", d); await p.fill("#f-jr", v); await p.fill("#f-jn", n); await p.fill("#f-jw", w); await p.press("#f-jr", "Enter"); await p.waitForTimeout(150); }
  ok(/8 journées/.test(await lire("#jr-n")), "huit séances datées ajoutées");
  ok(/16 trades comptés/.test(await lire("#jr-h")) && /50\s%/.test(await lire("#jr-h")), `trades comptés : 16, dont la moitié gagnants (${(await lire("#jr-h")).slice(-40)})`);
  const cal = await p.evaluate(() => ({ t: document.querySelector("#cal-t").textContent, pos: document.querySelectorAll("#cal .d.pos:not(.out)").length, neg: document.querySelectorAll("#cal .d.neg:not(.out)").length, ans: document.querySelector("#cal-ans").textContent }));
  ok(/Novembre 2026/.test(cal.t) && cal.pos === 2 && cal.neg === 1 && /−140/.test(cal.ans), `calendrier de novembre : 2 séances gagnantes, 1 perdante, total −140 $ (${cal.ans.slice(0, 50)}…)`);
  await p.click("#b-cal-p"); await p.waitForTimeout(200);
  const oct = await p.evaluate(() => ({ t: document.querySelector("#cal-t").textContent, n: document.querySelectorAll("#cal .d.pos:not(.out),#cal .d.neg:not(.out)").length, ans: document.querySelector("#cal-ans").textContent }));
  ok(/Octobre 2026/.test(oct.t) && oct.n === 4 && /\+505/.test(oct.ans), `le mois précédent : octobre, 4 séances (le samedi 31 compte avec le vendredi), +505 $ (${oct.ans.slice(0, 40)}…)`);
  await (await p.$("#et-cal")).screenshot({ path: join(dos, `calendrier-${W}.png`) });
  const chk = await lire("#jr-chk");
  ok(/8 journées/.test(chk) && /(marge du hasard|trop optimiste|trop prudente)/.test(chk), `journées contre réglages : « ${chk.slice(0, 90)}… »`);
  await (await p.$("#et-jr")).screenshot({ path: join(dos, `journee21-${W}.png`) });
  await p.fill("#f-jn", "2"); await p.fill("#f-jw", "5"); await p.fill("#f-jr", "50"); await p.press("#f-jr", "Enter"); await p.waitForTimeout(200);
  ok(/8 journées/.test(await lire("#jr-n")) && /gagnants vont de 0/.test(await lire("#jr-msg")), "5 gagnants sur 2 trades : refusé, rien n'est ajouté");
  await p.fill("#f-jn", ""); await p.fill("#f-jw", ""); await p.fill("#f-jr", "");
  await p.goto(U + "#resultat"); await p.waitForTimeout(2500);
  const acs = await p.evaluate(() => { const e = document.querySelector("#acs"); return { vu: !e.hidden && e.getClientRects().length > 0, t: e.textContent }; });
  ok(acs.vu && /Ton compte/.test(acs.t) && /\+365/.test(acs.t), `le Résultat rappelle le compte réel (« ${acs.t.slice(0, 80)} »)`);
  await p.click("#acs"); await p.waitForTimeout(800);
  ok(await p.evaluate(() => location.hash === "#compte" && !document.querySelector("#v-compte").hidden), "un toucher sur le rappel ouvre l'onglet Compte");
  await p.goto(U + "#quant"); await p.waitForTimeout(2000);
  ok(/16 trades, 8 gagnants/.test(await lire("#pf-take")), "la preuve propose de reprendre les trades des journées");
  await p.click("#b-pf-take"); await p.waitForTimeout(400);
  const pf = await p.evaluate(() => ({ vt: document.querySelector("#f-vt").value, vw: document.querySelector("#f-vw").value, res: document.querySelector("#pf-res").textContent, take: document.querySelector("#pf-take").hidden }));
  ok(pf.vt === "16" && pf.vw === "8" && /Sur 16 trades/.test(pf.res) && pf.take, `reprise : 16 trades, 8 gagnants jugés (${pf.res.slice(0, 60)}…)`);
  ok(await largeur(), "aucun défilement horizontal");
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
}
// v22 et suivantes : le cycle du compte (évaluation réussie, retrait demandé, annulation)
if (await p.evaluate(() => !!document.querySelector("#et-pay"))) {
  const U = "file://" + join(dos, "apercu.html"), lire = s => p.evaluate(x => document.querySelector(x).textContent, s), val = s => p.evaluate(x => document.querySelector(x).value, s);
  await p.goto(U + "#compte"); await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} }); await p.reload(); await p.waitForTimeout(2500);
  ok(await p.evaluate(() => document.querySelector("#et-act").hidden && document.querySelector("#et-pay").hidden), "compte neuf : aucune action de cycle, aucun retrait");
  for (const [f, v] of [["#f-ex", "3100"], ["#f-eM", "3100"], ["#f-end", "12"], ["#f-eb", "600"]]) await p.fill(f, v);
  await p.waitForTimeout(600);
  ok(/réussi l’évaluation/.test(await lire("#et-act")), "objectif atteint : le bouton « J’ai réussi l’évaluation » apparaît");
  await p.click('[data-ev="pass"]'); await p.waitForTimeout(600);
  const f0 = await p.evaluate(() => ({ ph: document.querySelector('#sg-ph [data-v="fund"]').getAttribute("aria-pressed"), ex: document.querySelector("#f-ex").value, eq: document.querySelector("#f-eq").value, ev: document.querySelector("#evl").textContent }));
  ok(f0.ph === "true" && f0.ex === "0" && f0.eq === "0" && /Évaluation réussie/.test(f0.ev), "réussite notée : compte financé à zéro, événement listé");
  for (const v of ["300", "300", "300", "300", "300"]) { await p.fill("#f-jr", v); await p.press("#f-jr", "Enter"); await p.waitForTimeout(150); }
  await p.waitForTimeout(500);
  const a1 = await lire("#et-act");
  ok(/Tu peux demander 750/.test(a1.replace(/\s/g, " ")), `cinq jours qualifiants à 300 $ : 750 $ demandables (« ${a1.slice(0, 60)}… »)`);
  await p.click('[data-ev="pay-open"]'); await p.waitForTimeout(300);
  ok((await val("#f-pay")) === "750", "le montant proposé est la demande possible (750 $)");
  await p.fill("#f-pay", "5000"); await p.click('[data-ev="pay"]'); await p.waitForTimeout(300);
  ok(await p.evaluate(() => document.querySelector("#w-pay").getAttribute("aria-invalid") === "true"), "plus que le profit : refusé");
  await p.fill("#f-pay", "750"); await p.click('[data-ev="pay"]'); await p.waitForTimeout(700);
  const f1 = await p.evaluate(() => ({ ex: document.querySelector("#f-ex").value, eq: document.querySelector("#f-eq").value, lk: document.querySelector('#sg-elk [data-v="1"]').getAttribute("aria-pressed"), ans: document.querySelector("#pay-ans").textContent }));
  ok(f1.ex === "750" && f1.eq === "0" && f1.lk === "true", `retrait noté : profit 750 $, jours qualifiants à 0, plancher bloqué (lu ${f1.ex}, ${f1.eq}, ${f1.lk})`);
  ok(/675/.test(f1.ans.replace(/\s/g, "")) && /\+597/.test(f1.ans.replace(/\s/g, "")), `ta part 675 $, net +597 $ après le prix (« ${f1.ans.slice(0, 70)}… »)`);
  ok(/cycle doit finir au-dessus/.test(await lire("#et-kpis")) || /pas encore/.test(await lire("#et-kpis")), "après le retrait, le cycle repart : pas de nouveau retrait possible");
  await p.waitForTimeout(400); ok(await p.evaluate(() => document.querySelectorAll("#s17 > .mkf").length === 2), "la courbe porte deux repères : financé et retrait");
  await (await p.$("#et-pay")).screenshot({ path: join(dos, `retraits-${W}.png`) });
  await (await p.$("#et-jr")).screenshot({ path: join(dos, `cycle-courbe-${W}.png`) });
  await p.click("#b-ev-undo"); await p.waitForTimeout(500);
  ok((await val("#f-ex")).replace(/\s/g, "") === "1500" && (await val("#f-eq")) === "5", "annuler le retrait rend 1 500 $ et 5 jours qualifiants");
  await p.click("#b-ev-undo"); await p.waitForTimeout(500);
  ok(await p.evaluate(() => document.querySelector('#sg-ph [data-v="eval"]').getAttribute("aria-pressed") === "true" && document.querySelector("#f-ex").value.replace(/\s/g, "") === "3100" && document.querySelector("#et-pay").hidden), "annuler la réussite rend l’évaluation à 3 100 $");
  ok(await largeur(), "aucun défilement horizontal");
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
}
// v23 et suivantes : les nouveautés une fois par version, l'import d'un fichier de trades
if (await p.evaluate(() => !!document.querySelector("#csv-prev"))) {
  const U = "file://" + join(dos, "apercu.html"), lire = s => p.evaluate(x => document.querySelector(x).textContent, s);
  await p.goto(U + "#resultat"); await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} }); await p.reload(); await p.waitForTimeout(2000);
  const nv = (await p.evaluate(() => !!document.querySelector("#news"))) ? "#news" : "#intro";   // v25 : les nouveautés vivent dans l'accueil
  ok(await vu(nv) && (nv === "#news" || /Nouveau/.test(await lire("#intro"))), "première visite de la version : l'accueil dit ce qui est nouveau");
  await (await p.$(nv)).screenshot({ path: join(dos, `nouveautes-${W}.png`) });
  await p.click(nv === "#news" ? "#b-news-x" : "#b-intro-x"); await p.reload(); await p.waitForTimeout(1500);
  ok(!(await vu(nv)), "fermé, il ne revient pas");
  const csv = `symbol,_priceFormat,_priceFormatType,_tickSize,buyFillId,sellFillId,qty,buyPrice,sellPrice,pnl,boughtTimestamp,soldTimestamp,duration
MNQZ6,-2,0,0.25,1,2,4,21000.00,21010.00,$80.00,11/03/2026 09:31:05,11/03/2026 09:35:10,4min
MNQZ6,-2,0,0.25,3,4,4,21020.00,21000.00,$(160.00),11/03/2026 10:01:00,11/03/2026 10:02:00,1min
MNQZ6,-2,0,0.25,5,6,2,21000.00,21030.00,$120.00,11/04/2026 09:40:00,11/04/2026 09:50:00,10min
MNQZ6,-2,0,0.25,7,8,1,20990.00,21000.00,$20.00,11/08/2026 18:30:00,11/08/2026 18:45:00,15min
`;
  const fic = join(dos, "trades-essai.csv"); writeFileSync(fic, csv);
  await p.goto(U + "#compte"); await p.waitForTimeout(1500);
  await p.setInputFiles("#f-csv", fic); await p.waitForTimeout(500);
  const pv = await lire("#csv-prev");
  ok(/4 trades sur 3 séances/.test(pv.replace(/\s+/g, " ")) && /\+49/.test(pv.replace(/\s/g, "")) && /mois \/ jour/.test(pv), `aperçu : 4 trades, 3 séances, +49 $ frais déduits, mois / jour (« ${pv.replace(/\s+/g, " ").slice(0, 90)}… »)`);
  await (await p.$("#csv-prev")).screenshot({ path: join(dos, `import-${W}.png`) });
  await p.click('[data-csv="dm"]'); await p.waitForTimeout(200);
  ok(/jour \/ mois/.test(await lire("#csv-prev")) && /11 mars/.test(await lire("#csv-prev")), "« Lire jour / mois » relit le fichier dans l'autre ordre");
  await p.click('[data-csv="dm"]'); await p.waitForTimeout(200);
  await p.click('[data-csv="ok"]'); await p.waitForTimeout(800);
  const after = await p.evaluate(() => ({ n: document.querySelector("#jr-n").textContent, ex: document.querySelector("#f-ex").value, cal: !document.querySelector("#et-cal").hidden, prev: document.querySelector("#csv-prev").hidden, h: document.querySelector("#jr-h").textContent }));
  ok(/3 journées/.test(after.n) && after.ex === "49" && after.cal && after.prev && /4 trades comptés/.test(after.h), `historique remplacé : 3 séances, profit 49 $, calendrier, 4 trades comptés (lu ${after.n}, ${after.ex})`);
  await p.click("#b-csv-paste"); await p.fill("#f-csv-ta", "Date;Résultat\n03/11/2026;120,50\n15/11/2026;-80\n"); await p.click("#b-csv-read"); await p.waitForTimeout(300);
  const pv2 = await lire("#csv-prev");
  ok(/2 trades sur 2 séances/.test(pv2.replace(/\s+/g, " ")) && /jour \/ mois/.test(pv2) && /remplacent/.test(pv2), "contenu collé : 2 séances, jour d'abord, remplacement annoncé");
  await p.fill("#f-csv-ta", "symbol,qty\nMNQ,1\n"); await p.click("#b-csv-read"); await p.waitForTimeout(200);
  ok(/colonne de résultat/.test(await lire("#csv-prev")), "un fichier sans résultat : message clair, rien ne change");
  ok(/3 journées/.test(await lire("#jr-n")), "l'historique importé est intact");
  ok(await largeur(), "aucun défilement horizontal");
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
}
// v24 et suivantes : « Avant ta séance », et le compte réel dans le résumé copié
if (await p.evaluate(() => !!document.querySelector("#plan"))) {
  const U = "file://" + join(dos, "apercu.html"), lire = s => p.evaluate(x => document.querySelector(x).textContent, s);
  await p.goto(U + "#compte"); await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} }); await p.reload(); await p.waitForTimeout(2500);
  const pl = await p.evaluate(() => ({ n: document.querySelectorAll("#plan-l .kpi").length, t: document.querySelector("#plan").textContent }));
  ok(pl.n === 4 && /Taille max/.test(pl.t) && /Plafond du jour/.test(pl.t) && /séance du/.test(pl.t), `avant ta séance : quatre limites et la date (${pl.t.replace(/\s+/g, " ").slice(0, 80)}…)`);
  await (await p.$("#plan")).screenshot({ path: join(dos, `seance-${W}.png`) });
  await p.fill("#f-ex", "-1600"); await p.waitForTimeout(500);
  ok(/Plancher proche/.test(await lire("#plan-h")), "à −1 600 $, la carte prévient : plancher proche");
  await p.fill("#f-ex", "200"); await p.waitForTimeout(800);
  await p.goto(U + "#resultat"); await p.waitForTimeout(3000);
  await p.click("#b-copy"); await p.waitForTimeout(400);
  let txt = await p.evaluate(() => { const t = document.querySelector("#copy-ta"); return t.hidden ? "" : t.value; });
  if (!txt) txt = await p.evaluate(() => navigator.clipboard.readText().catch(() => ""));
  ok(/Compte réel \(évaluation\) : profit \+200/.test(txt), `le résumé copié porte le compte réel (« ${(txt.split("\n").find(l => /Compte réel/.test(l)) || "").slice(0, 70)} »)`);
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
}
// v25 et suivantes : l'accueil après le chiffre, Compte réordonné, tes séances face à tes réglages, une année en distribution, nuage et relief
if (await p.evaluate(() => !!document.querySelector("#et-ana"))) {
  const U = "file://" + join(dos, "apercu.html"), lire = s => p.evaluate(x => document.querySelector(x).textContent, s);
  await p.goto(U + "#resultat"); await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} }); await p.reload(); await p.waitForTimeout(2500);
  const ord = await p.evaluate(() => { const h = document.querySelector(".hero").getBoundingClientRect().top, i = document.querySelector("#intro").getBoundingClientRect().top; return { h, i, vh: innerHeight }; });
  ok(ord.h < ord.i && ord.h < ord.vh * 0.5, `le chiffre principal vient avant l'accueil, dans la moitié haute de l'écran (héros à ${Math.round(ord.h)} px)`);
  await p.goto(U + "#compte"); await p.waitForTimeout(1500);
  const top = await p.evaluate(() => ({ plan: document.querySelector("#plan").getBoundingClientRect().top, jr: document.querySelector("#et-jr").getBoundingClientRect().top, etat: document.querySelector("#g-etat").getBoundingClientRect().top, ek: !!document.querySelector("#plan #r-ek"), size: !!document.querySelector("#et-size") }));
  ok(top.plan < top.jr && top.jr < top.etat && top.ek && !top.size, "Compte : avant ta séance (avec son curseur), puis la saisie du soir, l'état du compte plus bas, plus de carte Taille en double");
  const S = [["2026-10-20","240","3","2"],["2026-10-21","-180","2","0"],["2026-10-22","95","2","1"],["2026-10-23","410","3","3"],["2026-10-26","-60","2","1"],["2026-10-27","130","2","1"],["2026-10-28","-220","2","0"],["2026-10-29","310","3","2"]];
  for (const [d, v, n, w] of S) { await p.fill("#f-jd", d); await p.fill("#f-jr", v); await p.fill("#f-jn", n); await p.fill("#f-jw", w); await p.press("#f-jr", "Enter"); await p.waitForTimeout(120); }
  await p.waitForTimeout(800);
  const an = await p.evaluate(() => ({ vu: !document.querySelector("#et-ana").hidden, ans: document.querySelector("#ana-ans").textContent, fan: document.querySelectorAll("#s17 > .fanv1").length, rows: document.querySelectorAll("#mt .l").length, dd: document.querySelectorAll("#s20 > .ploss").length, wk: document.querySelectorAll("#s21 > .lb-g,#s21 > .lb-l").length }));
  ok(an.vu && /cumul de \+725/.test(an.ans.replace(/\s/g, " ")) && /bande/.test(an.ans), `tes séances : cumul +725 $ situé dans la bande des réglages (« ${an.ans.slice(0, 80)}… »)`);
  ok(an.fan === 1 && an.rows >= 9 && an.dd === 1 && an.wk === 5, `éventail, tableau (${an.rows} lignes), drawdown réel et cinq jours de semaine dessinés`);
  await p.evaluate(() => document.querySelector("#et-ana").scrollIntoView({ block: "start" })); await p.waitForTimeout(1300);
  await (await p.$("#et-ana")).screenshot({ path: join(dos, `seances-${W}.png`) });
  await (await p.$("#et-cal")).screenshot({ path: join(dos, `cal25-${W}.png`) });
  const cal = await p.evaluate(() => document.querySelectorAll("#cal .w").length);
  ok(cal <= 6, `le calendrier n'empile pas de semaines vides (${cal} semaines)`);
  await p.click("#b-jr-clr"); await p.click("#b-jr-clr"); await p.waitForTimeout(400);
  ok(await p.evaluate(() => document.querySelector("#et-cal").hidden && document.querySelector("#et-ana").hidden), "effacer l'historique cache aussi le calendrier et l'analyse");
  await p.goto(U + "#quant"); await p.waitForTimeout(6000);
  const q = await p.evaluate(() => ({ a7: document.querySelector("#aq7").textContent, bars: document.querySelectorAll("#s22 > .bar-g,#s22 > .bar-l").length, a8: document.querySelector("#aq8").textContent }));
  ok(/9 fois sur 10/.test(q.a7) && q.bars > 15, `une année : distribution (${q.bars} barres) et réponse (« ${q.a7.slice(0, 60)}… »)`);
  const ink = sel => p.evaluate(x => { const c = document.querySelector(x), d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 16) if (d[i] > 0) n++; return n; }, sel);
  await p.evaluate(() => document.querySelector("#p23").scrollIntoView({ block: "center" })); await p.waitForTimeout(600);
  ok(/médiane finit/.test(q.a8) && (await ink("#c23")) > 2000, "nuage de 600 trajectoires dessiné, réponse écrite");
  await (await p.$("#p23")).screenshot({ path: join(dos, `nuage-${W}.png`) });
  await p.click('#sg-tj [data-v="3d"]'); await p.waitForTimeout(1500);
  ok(await vu("#c24") && !(await vu("#c23")) && (await ink("#c24")) > 2000, "le relief remplace le nuage et se dessine");
  await (await p.$("#p24")).screenshot({ path: join(dos, `relief25-${W}.png`) });
  await (await p.$("#p22")).screenshot({ path: join(dos, `annee-${W}.png`) });
  await p.click('#sg-tj [data-v="2d"]');
  ok(await largeur(), "aucun défilement horizontal");
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
}
// v26 : plans de challenge nommés, onglet Stratégie (feuille de route, paper), sauvegarde qui les porte
if (await p.evaluate(() => !!document.querySelector("#plan-card"))) {
  const U = "file://" + join(dos, "apercu.html"), lire = s => p.evaluate(x => { const e = document.querySelector(x); return e ? e.textContent.replace(/\s+/g, " ").trim() : ""; }, s);
  const calc = async () => { await p.waitForTimeout(500); await p.waitForFunction(() => { const g = document.querySelector("#prog"); return g && g.hidden && !document.querySelector("main .stale"); }, null, { timeout: 60000 }); await p.waitForTimeout(300); };
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} }); await p.goto(U + "#reglages"); await p.reload(); await calc();
  const chips = () => p.evaluate(() => [...document.querySelectorAll("#pl-list .chip")].map(c => c.textContent + (c.getAttribute("aria-pressed") === "true" ? "*" : "")).join(" | "));
  ok(await chips() === "LucidFlex 50K* | MFFU Pro 100K" && /LucidFlex 50K/.test(await lire("#acct")), `deux plans au départ, LucidFlex 50K actif (${await chips()})`);
  const heroLF = await lire(".hnum");
  await p.click('#pl-list [data-i="1"]'); await calc();
  const rl = await lire("#rules-line"), lab = await lire('#sg-pol [data-v="cap"]'), heroPro = await lire(".hnum");
  ok(/MFFU Pro 100K/.test(await lire("#acct")) && /tampon de 3 100/.test(rl) && /sans plafond/.test(rl), `MFFU Pro 100K : tampon, sans plafond (« ${rl.slice(0, 90)}… »)`);
  ok(/3\s000/.test(lab) && heroPro !== heroLF && /\d/.test(heroPro), `sans plafond, « attendre » vise un montant (${lab}) ; résultat recalculé (${heroLF} → ${heroPro})`);
  await p.fill("#f-pname", "MFF Pro Plan"); await p.waitForTimeout(500);
  ok(/MFF Pro Plan/.test(await lire("#acct")) && /MFF Pro Plan\*/.test(await chips()), "le titre du plan se modifie, en tête et dans la liste");
  await p.click('#pl-tpl [data-t="2"]'); await calc();
  ok((await chips()).split(" | ").length === 3 && /la première fois/.test(await lire("#rules-line")), "un modèle crée un plan (LucidPro 100K, premier retrait plafonné à part)");
  await p.click("#b-pl-del"); await p.waitForTimeout(200);
  ok((await chips()).split(" | ").length === 3 && /Confirmer/.test(await lire("#b-pl-del")), "supprimer demande une confirmation");
  await p.click("#b-pl-del"); await calc();
  ok((await chips()).split(" | ").length === 2, `le plan est supprimé (${await chips()})`);
  await p.click('#pl-list [data-i="1"]'); await calc(); await p.reload(); await calc();
  ok(/MFF Pro Plan\*/.test(await chips()) && await p.inputValue("#f-pname") === "MFF Pro Plan", "plans, nom et plan actif gardés après rechargement");
  await p.goto(U + "#option"); await calc();
  ok(await lire("#op-plan") === "MFF Pro Plan", "l'onglet Option nomme le plan et sa prime");
  await p.click('#sg-Nopt [data-v="120"]'); await p.waitForTimeout(700);
  ok(await p.evaluate(() => document.querySelector("#r-jour").max) === "120" && /jour 120/.test(await lire("#ao1")), "l'échéance du retrait se règle depuis l'onglet Option");
  // feuille de route
  await p.goto(U + "#strategie"); await p.waitForTimeout(1500);
  const rt = await p.evaluate(() => ({ prog: document.querySelector("#rt-prog").textContent, open: document.querySelectorAll(".rph.op").length, ph: document.querySelectorAll(".rph").length }));
  const tot0 = +((rt.prog.match(/\/ (\d+)/) || [])[1] || 0);
  ok(tot0 >= 21 && rt.ph === 6 && rt.open === 1, `six phases, la phase en cours seule ouverte (${rt.prog.replace(/\s+/g, " ").slice(0, 40)})`);
  await p.click('.rhead[data-ph="d"]'); await p.waitForTimeout(300);
  const man = await p.evaluate(() => { const b = [...document.querySelectorAll('.rph.op .rst:not(.auto) .rck')][0]; return b && b.dataset.ck; });
  await p.click(`[data-ck="${man}"]`); await p.waitForTimeout(300);
  ok(await p.evaluate(id => document.querySelector(`[data-ck="${id}"]`).getAttribute("aria-pressed"), man) === "true", "une étape se valide d'un toucher");
  const aut = await p.evaluate(() => { const b = document.querySelector(".rst.auto:not(.ok) .rck"); return b && b.dataset.ck; });
  await p.click(`[data-ck="${aut}"]`, { force: true }); await p.waitForTimeout(300);
  ok(await p.evaluate(id => document.querySelector(`[data-ck="${id}"]`).getAttribute("aria-pressed"), aut) === "false" && /seule/.test(await lire("#toast")), "une étape vérifiée par les données ne se coche pas à la main");
  await p.click("#b-rt-edit"); await p.waitForTimeout(200); await p.click('[data-add="c"]'); await p.waitForTimeout(200); await p.keyboard.type("Comparer trois plans");
  await p.click("#b-rt-edit"); await p.waitForTimeout(300); await p.reload(); await p.waitForTimeout(1500);
  const apres = await p.evaluate(id => ({ v: document.querySelector(`[data-ck="${id}"]`)?.getAttribute("aria-pressed"), n: document.querySelector("#rt-prog").textContent }), man);
  ok(apres.v === "true" && apres.n.includes("/ " + (tot0 + 1)), "coche et étape ajoutée gardées après rechargement");
  await p.screenshot({ path: join(dos, `route-${W}.png`) });
  // le paper
  await p.click('#sg-sv [data-v="paper"]'); await calc(); await p.waitForTimeout(600);
  const pp = await p.evaluate(() => ({ h2: document.querySelectorAll("#paper h2").length, ph: document.querySelectorAll("#paper .ph").length, fig: document.querySelectorAll("#paper figure svg").length, tab: document.querySelectorAll("#paper table").length }));
  ok(pp.h2 === 10 && pp.ph > 0 && pp.fig >= 2 && pp.tab >= 3, `paper : résumé, huit sections, références ; ${pp.tab} tables, ${pp.fig} figures, ${pp.ph} emplacements à remplir`);
  await p.fill("#x-titre", "Le rebond du VWAP"); await p.fill("#x-nom", "ALP-0"); await p.waitForTimeout(500);
  ok(await lire("#paper h1") === "Le rebond du VWAP" && /l’avantage d’ALP-0/.test(await lire("#paper .pabs")), "le titre et le nom passent dans le paper (élision comprise)");
  await p.click("#b-pp-read"); await p.waitForTimeout(400);
  const rd = await p.evaluate(() => ({ h: getComputedStyle(document.querySelector("header.top")).display, x: getComputedStyle(document.querySelector("#b-pp-x")).display }));
  await p.keyboard.press("Escape"); await p.waitForTimeout(300);
  ok(rd.h === "none" && rd.x !== "none" && !(await p.evaluate(() => document.body.classList.contains("reading"))), "lecture plein écran : l'app s'efface, Échap la rend");
  ok(await largeur(), "aucun défilement horizontal dans l'onglet Stratégie");
  // la sauvegarde porte plans, paper et feuille de route
  await p.goto(U + "#reglages"); await calc(); await p.evaluate(() => document.querySelector("#data-card").scrollIntoView({ block: "center" }));
  await p.click("#b-exp"); await p.waitForTimeout(500);
  let code = await p.evaluate(() => { const t = document.querySelector("#exp-ta"); return t.hidden ? "" : t.value; });
  if (!code) code = await p.evaluate(() => navigator.clipboard.readText().catch(() => ""));
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} }); await p.reload(); await calc();
  ok(await chips() === "LucidFlex 50K* | MFFU Pro 100K", "stockage vidé : plans d'origine");
  await p.evaluate(() => document.querySelector("#data-card").scrollIntoView({ block: "center" }));
  await p.fill("#f-imp", code); await p.click("#b-imp"); await calc();
  ok(/MFF Pro Plan\*/.test(await chips()) && await p.inputValue("#x-titre") === "Le rebond du VWAP", `la sauvegarde rend plans et paper (${await chips()})`);
  await p.goto(U + "#strategie"); await p.click('#sg-sv [data-v="route"]').catch(() => {}); await p.waitForTimeout(1200);
  ok((await lire("#rt-prog")).includes("/ " + (tot0 + 1)), "et la feuille de route, étape ajoutée comprise");
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
}
// v27 : journal de trades en R, scellement, preuve hors échantillon
if (await p.evaluate(() => !!document.querySelector("#tl-card"))) {
  const U = "file://" + join(dos, "apercu.html"), lire = s => p.evaluate(x => { const e = document.querySelector(x); return e ? e.textContent.replace(/\s+/g, " ").trim() : ""; }, s);
  const calc = async () => { await p.waitForTimeout(500); await p.waitForFunction(() => { const g = document.querySelector("#prog"); return g && g.hidden && !document.querySelector("main .stale"); }, null, { timeout: 60000 }); await p.waitForTimeout(300); };
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} }); await p.goto(U + "#strategie"); await p.reload(); await calc();
  await p.click('#sg-sv [data-v="trades"]'); await p.waitForTimeout(400);
  ok(/41,3\s%/.test(await lire("#tl-ans")) && /\+1,5\sR/.test(await lire("#tl-win")), `journal vide : la barre à passer est dite (« ${(await lire("#tl-ans")).slice(0, 70)}… »)`);
  for (const id of ["#tl-win", "#tl-loss", "#tl-loss", "#tl-be"]) await p.click(id);
  await p.fill("#tl-r", "2,25"); await p.press("#tl-r", "Enter"); await p.waitForTimeout(300);
  ok(await p.evaluate(() => document.querySelectorAll("#tl-last .tchip").length) === 5 && /5 trades notés/.test(await lire("#tl-ans")), "cinq trades notés d'un toucher, dont une valeur libre");
  await p.click(".tl-paste summary"); await p.fill("#tl-ta", "+ - - + = 1,5 -1 x"); await p.click("#tl-ta-add"); await p.waitForTimeout(300);
  ok(/12 trades notés/.test(await lire("#tl-ans")), `une série collée ajoute sept trades, le morceau illisible est écarté (${await lire("#tl-pill")})`);
  await p.click("#tl-undo"); await p.waitForTimeout(200);
  ok(/11 trades notés/.test(await lire("#tl-ans")), "annuler retire le dernier trade");
  ok(await p.evaluate(() => document.querySelectorAll("#tl-fig svg path.pq-f1").length) === 1 && (await p.evaluate(() => document.querySelectorAll("#tl-kpis .kpi").length)) === 6, "statistiques et éventail de la loi nulle dessinés");
  await p.click("#b-seal"); await p.waitForTimeout(150);
  ok(/Confirmer/.test(await lire("#b-seal")) && !(await p.evaluate(() => !!document.querySelector(".seal"))), "sceller demande une confirmation");
  await p.click("#b-seal"); await p.waitForTimeout(600);
  const sb = await lire("#seal-box");
  ok(/Scellée le/.test(sb) && /Empreinte [0-9a-f]{4} [0-9a-f]{4} [0-9a-f]{4} [0-9a-f]{4}/.test(sb) && /0 trade depuis/.test(sb), `stratégie scellée avec empreinte (« ${sb.slice(0, 90)}… »)`);
  ok(/Aucun trade depuis/.test(await lire("#tl-ans")), "après le scellement, le compteur des trades jugés repart de zéro");
  for (let i = 0; i < 3; i++) await p.click("#tl-win"); await p.click("#tl-loss"); await p.waitForTimeout(300);
  ok(/4 trades depuis le scellement/.test(await lire("#tl-ans")) && /p-valeur/.test(await lire("#tl-ans")) && await p.evaluate(() => document.querySelectorAll("#tl-last .tchip.oos").length) === 4, "les trades suivants sont jugés seuls, avec leur p-valeur");
  await p.goto(U + "#reglages"); await calc();
  await p.evaluate(() => { const r = document.querySelector("#r-stop"); r.value = "25"; r.dispatchEvent(new Event("input", { bubbles: true })); }); await calc();
  await p.goto(U + "#strategie"); await p.waitForTimeout(1200);
  ok(/Changé depuis : stop \(20 → 25\)/.test(await lire("#seal-box")), "une règle changée après le scellement se voit");
  // la feuille de route et le paper suivent le journal
  await p.click('#sg-sv [data-v="route"]'); await p.waitForTimeout(400);
  const rt = await p.evaluate(() => ({ n: document.querySelector("#rt-prog").textContent, seal: [...document.querySelectorAll(".rhead")].map(h => h.textContent).join("|") }));
  ok(/\/ 23/.test(rt.n), `la feuille de route compte les deux étapes nouvelles (${rt.n.replace(/\s+/g, " ").slice(0, 20)})`);
  await p.click('.rhead[data-ph="s"]').catch(() => {}); await p.waitForTimeout(200);
  if (!(await p.evaluate(() => !!document.querySelector('.rph.op [data-ck="d4"]')))) await p.click('.rhead[data-ph="s"]');
  ok(await p.evaluate(() => document.querySelector('[data-ck="d4"]')?.getAttribute("aria-pressed")) === "true", "« Sceller la stratégie » s'est cochée seule");
  await p.click('#sg-sv [data-v="paper"]'); await calc(); await p.waitForTimeout(500);
  const pp = await p.evaluate(() => ({ t: document.querySelector("#paper").textContent, fig: document.querySelectorAll("#paper figure svg").length, ann: [...document.querySelectorAll("#paper h2")].some(h => /Annexe A/.test(h.textContent)) }));
  ok(/notés après le scellement/.test(pp.t) && /scellés le/.test(pp.t) && pp.ann && /ont changé depuis : stop/.test(pp.t), "le paper juge les trades hors échantillon, cite le scellement, son annexe et le changement");
  // la sauvegarde porte le journal et le scellement
  await p.goto(U + "#reglages"); await calc(); await p.evaluate(() => document.querySelector("#data-card").scrollIntoView({ block: "center" }));
  await p.click("#b-exp"); await p.waitForTimeout(500);
  let code = await p.evaluate(() => { const t = document.querySelector("#exp-ta"); return t.hidden ? "" : t.value; });
  if (!code) code = await p.evaluate(() => navigator.clipboard.readText().catch(() => ""));
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} }); await p.reload(); await calc();
  await p.evaluate(() => document.querySelector("#data-card").scrollIntoView({ block: "center" })); await p.fill("#f-imp", code); await p.click("#b-imp"); await calc();
  await p.goto(U + "#strategie"); await p.click('#sg-sv [data-v="trades"]').catch(() => {}); await p.waitForTimeout(800);
  ok(/4 trades depuis le scellement/.test(await lire("#tl-ans")) && /Scellée le/.test(await lire("#seal-box")), "la sauvegarde rend journal et scellement");
  await p.screenshot({ path: join(dos, `trades-${W}.png`), fullPage: true });
  ok(await largeur(), "aucun défilement horizontal dans le journal de trades");
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
}
// v28 : la stratégie de l'utilisateur dans le paper, setups, preuve par l'espérance en R
if (await p.evaluate(() => !!document.querySelector("#tl-gs"))) {
  const U = "file://" + join(dos, "apercu.html"), lire = s => p.evaluate(x => { const e = document.querySelector(x); return e ? e.textContent.replace(/\s+/g, " ").trim() : ""; }, s);
  const calc = async () => { await p.waitForTimeout(500); await p.waitForFunction(() => { const g = document.querySelector("#prog"); return g && g.hidden && !document.querySelector("main .stale"); }, null, { timeout: 60000 }); await p.waitForTimeout(300); };
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} }); await p.goto(U + "#strategie"); await p.reload(); await calc();
  await p.click('#sg-sv [data-v="paper"]'); await calc(); await p.waitForTimeout(500);
  const pp = await lire("#paper");
  ok(/Identifier la tendance/.test(pp) && /début de la structure/.test(pp) && /max pain/.test(pp) && /trend following/.test(pp), "le paper porte la stratégie en quatre temps, avec ses deux sorties");
  ok(await p.evaluate(() => document.querySelectorAll("#paper .apr li").length) === 7, "sept définitions restent à préciser avant de sceller");
  await p.fill("#x-stop", "Sous le dernier creux de la structure."); await p.waitForTimeout(500);
  ok(await p.evaluate(() => document.querySelectorAll("#paper .apr li").length) === 6, "une règle écrite sort de la liste à préciser");
  await p.click('#sg-sv [data-v="trades"]'); await p.waitForTimeout(400);
  ok(/à préciser/.test(await lire("#seal-box")), "le scellement rappelle ce qui reste flou");
  await p.click('#tl-gs [data-g="Retournement"]');
  ok(await p.inputValue("#tl-g") === "Retournement" && await p.evaluate(() => document.querySelector('#tl-gs [data-g="Retournement"]').getAttribute("aria-pressed")) === "true", "un setup se choisit d'un toucher");
  for (const v of ["4", "-1", "-1", "3,5", "-1", "6"]) { await p.fill("#tl-r", v); await p.press("#tl-r", "Enter"); }
  await p.click('#tl-gs [data-g="Continuation"]');
  for (const v of ["1,2", "-1", "0,8", "1,5", "-1"]) { await p.fill("#tl-r", v); await p.press("#tl-r", "Enter"); }
  await p.waitForTimeout(500);
  const rows = await p.evaluate(() => [...document.querySelectorAll("#tl-setups tbody tr")].map(r => r.firstChild.textContent + ":" + r.children[1].textContent));
  ok(rows.join(" ") === "Retournement:6 Continuation:5", `tableau par setup (${rows.join(", ")})`);
  await p.click("#b-seal"); await p.click("#b-seal"); await p.waitForTimeout(500);
  for (const v of ["5", "-1", "-1", "2", "-1", "4,5", "-1", "1,5"]) { await p.fill("#tl-r", v); await p.press("#tl-r", "Enter"); }
  await p.waitForTimeout(500);
  ok(/p-valeur par bootstrap/.test(await lire("#tl-ans")), "des gains variables passent au test de l'espérance (bootstrap)");
  await p.click('#sg-sv [data-v="paper"]'); await calc(); await p.waitForTimeout(600);
  const pp2 = await p.evaluate(() => ({ t: document.querySelector("#paper").textContent, caps: [...document.querySelectorAll("#paper caption")].map(c => c.textContent).join(" | ") }));
  ok(/espérance nette en R contre zéro/.test(pp2.caps) && /bootstrap recentré/.test(pp2.t) && /setup par setup/.test(pp2.caps) && /Efron/.test(pp2.t), "le paper juge l'espérance en R, setup par setup, et cite Efron (1979)");
  await p.evaluate(() => document.querySelector("#paper .apr")?.scrollIntoView({ block: "start" })); await p.waitForTimeout(300);
  await p.screenshot({ path: join(dos, `paper28-${W}.png`) });
  ok(await largeur(), "aucun défilement horizontal");
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
}
// v29 : trader uniquement dans le sens de la tendance ; les défauts du paper ne s'enregistrent plus
if (await p.evaluate(() => document.documentElement.innerHTML.includes("uniquement dans le sens de la tendance"))) {
  const U = "file://" + join(dos, "apercu.html"), lire = s => p.evaluate(x => { const e = document.querySelector(x); return e ? e.textContent.replace(/\s+/g, " ").trim() : ""; }, s);
  const calc = async () => { await p.waitForTimeout(500); await p.waitForFunction(() => { const g = document.querySelector("#prog"); return g && g.hidden && !document.querySelector("main .stale"); }, null, { timeout: 60000 }); await p.waitForTimeout(300); };
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} }); await p.goto(U + "#reglages"); await p.reload(); await calc();
  // une sauvegarde de la v28 portait l'ancienne entrée par défaut : elle cède la place à la nouvelle
  await p.evaluate(() => document.querySelector("#data-card").scrollIntoView({ block: "center" }));
  await p.fill("#f-imp", JSON.stringify({ v: 1, app: "option-challenge", P: { sv: "paper" }, tx: { entree: "Prendre position au début de la structure.", nom: "Structure et tendance" } }));
  await p.click("#b-imp"); await calc();
  await p.goto(U + "#strategie"); await calc(); await p.waitForTimeout(600);
  const t = await lire("#paper");
  ok(/uniquement dans le sens de la tendance/.test(t) && /la tendance nouvelle qui donne ce sens/.test(t) && /Structure et tendance/.test(t), "la règle de tendance passe dans le paper, l'ancienne entrée par défaut est remplacée");
  ok(await p.evaluate(() => document.querySelectorAll("#paper .apr li").length) === 7, "les sept définitions restent à préciser");
  const st = await p.evaluate(() => JSON.parse(localStorage.getItem("alp-option-challenge-paper-v26") || "{}"));
  ok(st.nom === "Structure et tendance" && !("tend" in st) && !("entree" in st), `seuls les champs écrits s'enregistrent (${Object.keys(st).join(", ")})`);
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
}
ok(!errs.length, errs.length ? "erreurs : " + errs.join(" | ") : "aucune erreur de script");
await b.close();
console.log(`\n${ko ? ko + " défaut(s)" : "tout est bon"} ; captures : ${dos}`);
process.exit(ko ? 1 : 0);
