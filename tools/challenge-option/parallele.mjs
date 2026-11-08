// Banc du calcul en parallèle de prop/challenge-option20.html (et suivantes) : les Web Workers rendent-ils les mêmes chiffres
// que le fil principal, et le fil principal reste-t-il libre pendant le calcul ?
// Usage : node tools/challenge-option/parallele.mjs <dossier de rendu.mjs> [ralentissement CPU, 4 par défaut]
// Lancer rendu.mjs d'abord : il écrit apercu.html (page + vraies fontes) dans le dossier.
//  1. charge la page sans Worker (repli dans le fil principal), puis avec : tous les chiffres affichés doivent être identiques
//     (le découpage en tranches est fixe et la fusion se fait dans l'ordre) ;
//  2. mesure, au CPU ralenti, le temps du calcul complet et la plus longue image pendant ce calcul, avec et sans workers.
// Code de sortie 1 au premier défaut.
import { createRequire } from "node:module";
import { join } from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const dos = process.argv[2], cpu = +(process.argv[3] || 4);
if (!dos) { console.error("usage : node parallele.mjs <dossier> [ralentissement]"); process.exit(1); }
const page = "file://" + join(dos, "apercu.html");
const b = await chromium.launch();
let ko = 0; const ok = (c, m) => { console.log(`${c ? "ok    " : "DÉFAUT"}  ${m}`); if (!c) ko++; };

async function charge(sansWorker, ralenti, vue) {
  const ctx = await b.newContext({ viewport: { width: 390, height: 860 } }), p = await ctx.newPage(), errs = [];
  p.on("pageerror", e => errs.push(e.message)); p.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
  if (ralenti > 1) { const s = await ctx.newCDPSession(p); await s.send("Emulation.setCPUThrottlingRate", { rate: ralenti }); }
  await p.addInitScript(sw => { if (sw) { window.Worker = undefined; }
    window.__t0 = performance.now(); window.__fr = []; const f = t => { window.__fr.push(t); requestAnimationFrame(f); }; requestAnimationFrame(f);
    addEventListener("load", () => { window.__load = performance.now(); }); }, sansWorker);
  await p.goto(page + "#" + (vue || "resultat"));
  const t = await p.evaluate(() => new Promise(res => { const h = setInterval(() => {
    const pg = document.querySelector("#prog"); if (pg && pg.hidden && !document.querySelector("main .stale") && window.__fr.length > 20) { clearInterval(h);
      /* le chargement (analyse et premier rendu de la page) est hors mesure : on juge le calcul, pas le démarrage */
      const end = performance.now(), deb = (window.__load || 0) + 50, fr = window.__fr.filter(x => x < end && x > deb); let pire = 0; for (let i = 1; i < fr.length; i++) pire = Math.max(pire, fr[i] - fr[i - 1]);
      res({ ms: Math.round(end - window.__t0), pire: Math.round(pire), ips: Math.round(1000 * fr.length / (end - window.__t0)) }); } }, 40); }));
  return { p, ctx, t, errs };
}
// tout ce qui s'écrit en chiffres sur les six onglets (le compte d'aujourd'hui compris)
async function chiffres(p) {
  const out = {};
  for (const v of ["resultat", "compte", "quant", "leviers"]) {
    await p.evaluate(x => { location.hash = x; }, v); await p.waitForTimeout(v === "compte" ? 2500 : 900);
    out[v] = await p.evaluate(() => [...document.querySelectorAll("main section:not([hidden]) :is(.hnum,.kpi .v,.cmp .v,.olist b,.ans,.hint,.lim .v,.act .d b,.strip b)")]
      .map(e => e.textContent.replace(/\s+/g, " ").trim()).filter(t => /\d/.test(t)).join(" | "));
  }
  return out;
}
const A = await charge(true, 1), cA = await chiffres(A.p);
const W = await charge(false, 1), cW = await chiffres(W.p);
const nW = await W.p.evaluate(() => (navigator.hardwareConcurrency || 2));
for (const v of Object.keys(cA)) ok(cA[v] === cW[v] && cA[v].length > 50, `${v} : mêmes chiffres avec et sans workers (${cA[v].length} caractères comparés)`);
if (cA.resultat !== cW.resultat) { console.log("sans :", cA.resultat.slice(0, 300)); console.log("avec :", cW.resultat.slice(0, 300)); }
ok(!A.errs.length && !W.errs.length, A.errs.concat(W.errs).length ? "erreurs : " + A.errs.concat(W.errs).join(" | ") : "aucune erreur, avec ou sans workers");
await A.ctx.close(); await W.ctx.close();
const A4 = await charge(true, cpu), W4 = await charge(false, cpu);
console.log(`CPU ÷${cpu}, ${nW} cœurs annoncés : sans workers ${A4.t.ms} ms (pire image ${A4.t.pire} ms, ${A4.t.ips} images/s) ; avec ${W4.t.ms} ms (pire image ${W4.t.pire} ms, ${W4.t.ips} images/s)`);
ok(W4.t.pire <= 40 * cpu, `pendant le calcul, aucune image ne dépasse ${40 * cpu} ms au CPU ÷${cpu} (pire ${W4.t.pire} ms ; sans workers ${A4.t.pire} ms)`);
ok(nW < 2 || W4.t.ms <= A4.t.ms * 0.7, `les workers raccourcissent le calcul (${W4.t.ms} ms contre ${A4.t.ms} ms)`);
await b.close();
console.log(`\n${ko ? ko + " défaut(s)" : "tout est bon"}`);
process.exit(ko ? 1 : 0);
