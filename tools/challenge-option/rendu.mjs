// Banc de rendu des pages prop/challenge-option*.html, avec les vraies fontes.
// Sans elles la relecture se fait dans une police de repli (piège du mandat NQ, docs/mandat/README.md).
// Usage : node tools/challenge-option/rendu.mjs [dossier] [page]   (dossier temporaire et dernière page par défaut)
//  1. lit les familles que la page demande à Google Fonts, les récupère par npm (@fontsource) et les injecte
//     dans un aperçu local ;
//  2. charge l'aperçu dans Chromium à six largeurs : erreurs de script, défilement horizontal, éléments hors
//     cadre, animation qui avance, Monte Carlo rendu ; sur une page à onglets, chaque onglet est balayé ;
//  3. écrit une capture par onglet (ou de la première section) à 390 et à 1 280 px.
// Code de sortie 1 au premier défaut. Ne jamais lancer « playwright install » : Chromium est déjà là.
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, existsSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = createRequire(import.meta.url)("playwright");
const ici = dirname(fileURLToPath(import.meta.url));
const dos = process.argv[2] || mkdtempSync(join(tmpdir(), "option-"));
const pagePath = process.argv[3] || join(ici, "../../prop/challenge-option5.html");
mkdirSync(dos, { recursive: true });
let src = readFileSync(pagePath, "utf8");

// familles demandées : family=Geist:wght@400;500&family=Geist+Mono:wght@400 …
const lien = (src.match(/fonts\.googleapis\.com\/css2\?([^"]+)"/) || [])[1] || "";
// … et l'axe italique : family=Source+Serif+4:ital,wght@0,400;0,600;1,400
const familles = [...lien.matchAll(/family=([^:&]+)(?::(ital,)?wght@([\d;,]+))?/g)].map(m => ({
  nom: decodeURIComponent(m[1].replace(/\+/g, " ")),
  poids: (m[3] || "400").split(";").map(t => m[2] ? { w: +t.split(",")[1], it: t.split(",")[0] === "1" } : { w: +t, it: false }) }));
const paquet = nom => ({ "Geist": "geist-sans", "Geist Mono": "geist-mono" }[nom] || nom.toLowerCase().replace(/\s+/g, "-"));
const fontes = join(dos, "fontes");
mkdirSync(fontes, { recursive: true });
const faces = [];
for (const f of familles) {
  const slug = paquet(f.nom), d = join(fontes, slug);
  if (!existsSync(join(d, "package"))) {
    mkdirSync(d, { recursive: true });
    execSync(`npm pack @fontsource/${slug}@5 --silent`, { cwd: d, stdio: "pipe" });
    const tgz = readdirSync(d).find(x => x.endsWith(".tgz"));
    execSync(`tar -xzf "${join(d, tgz)}" -C "${d}"`);
  }
  for (const { w, it } of f.poids) {
    const fichier = join(d, "package/files", `${slug}-latin-${w}-${it ? "italic" : "normal"}.woff2`);
    if (existsSync(fichier)) faces.push(`@font-face{font-family:'${f.nom}';font-weight:${w};font-style:${it ? "italic" : "normal"};src:url('file://${fichier}') format('woff2');font-display:block}`);
    else console.log(`fonte absente : ${f.nom} ${w}${it ? " italique" : ""}`);
  }
}
src = src.replace(/<link rel="(?:preconnect|stylesheet)"[^>]*fonts\.(?:googleapis|gstatic)\.com[^>]*>\n?/g, "");
src = src.replace("<style>", "<style>\n" + faces.join("\n") + "\n");
const apercu = join(dos, "apercu.html");
writeFileSync(apercu, '<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">' + src);
console.log(`fontes : ${familles.map(f => f.nom + " " + f.poids.map(q => q.w + (q.it ? "i" : "")).join("/")).join(", ")}`);

const mesure = () => {
  const hors = [];
  document.querySelectorAll("body *").forEach(el => {
    const rc = el.getBoundingClientRect();
    if (rc.width > 0 && (rc.right > document.documentElement.clientWidth + 1 || rc.left < -1)) {
      let q = el.parentElement, defile = false;
      while (q) { const st = getComputedStyle(q); if (st.overflowX === "auto" || st.overflowX === "scroll") { defile = true; break; } q = q.parentElement; }
      if (!defile) hors.push(el.tagName + "#" + el.id);
    }
  });
  return { doc: document.documentElement.scrollWidth, vue: document.documentElement.clientWidth, hors };
};
const b = await chromium.launch();
let defauts = 0;
for (const W of [360, 390, 430, 768, 1100, 1280]) {
  const p = await b.newPage({ viewport: { width: W, height: 900 } });
  const errs = [];
  p.on("pageerror", e => errs.push(e.message));
  p.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
  await p.goto("file://" + apercu);
  await p.waitForTimeout(4500);
  const vues = await p.evaluate(() => [...new Set([...document.querySelectorAll("[data-view]")].map(b => b.dataset.view))]);
  const lignes = [];
  let ok = true;
  for (const v of (vues.length ? vues : [null])) {
    if (v) { await p.evaluate(x => { location.hash = x; }, v); await p.waitForTimeout(700); }
    const r = await p.evaluate(mesure);
    const bon = r.doc <= r.vue && !r.hors.length;
    if (!bon) { ok = false; lignes.push(`${v || "page"} : doc ${r.doc}/${r.vue}, hors cadre ${r.hors.slice(0, 5).join(" ")}`); }
    if (W === 390 || W === 1280) {
      const cible = v ? await p.$("#v-" + v) : await p.$("main > section");
      if (cible) await cible.screenshot({ path: join(dos, `${v ? "vue-" + v : "figure1"}-${W}.png`) });
    }
  }
  const fin = await p.evaluate(() => ({ jour: "J " + document.querySelector("#o-jour").textContent, mc: document.querySelectorAll("main .pending, main .stale").length === 0 }));
  ok = ok && !errs.length && fin.jour !== "J 0,0" && fin.mc;
  if (!ok) defauts++;
  console.log(`${String(W).padStart(5)} px  ${ok ? "ok" : "DÉFAUT"}  ${vues.length ? vues.length + " onglets balayés" : "page"}  ${fin.jour}  Monte Carlo ${fin.mc ? "rendu" : "en attente"}${lignes.length ? "  " + lignes.join(" ; ") : ""}${errs.length ? "  erreurs : " + errs.join(" | ") : ""}`);
  await p.close();
}
await b.close();
console.log(`\naperçu et captures : ${dos}`);
process.exit(defauts ? 1 : 0);
