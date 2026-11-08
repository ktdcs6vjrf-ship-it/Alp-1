// Banc de rendu de prop/challenge-option.html, avec les vraies fontes.
// Sans elles la relecture se fait dans une police de repli (piège du mandat NQ, docs/mandat/README.md).
// Usage : node tools/challenge-option/rendu.mjs [dossier] [page]   (dossier temporaire et dernière page par défaut)
//  1. récupère Archivo et JetBrains Mono par npm et les injecte dans un aperçu local ;
//  2. charge l'aperçu dans Chromium à six largeurs : erreurs de script, défilement horizontal,
//     éléments hors cadre, animation qui avance, Monte Carlo rendu ;
//  3. écrit une capture de la figure 1 à 390 et à 1 280 px.
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
mkdirSync(dos, { recursive: true });

const fontes = join(dos, "fontes");
if (!existsSync(join(fontes, "archivo"))) {
  mkdirSync(fontes, { recursive: true });
  execSync("npm pack @fontsource/archivo@5 @fontsource/jetbrains-mono@5 --silent", { cwd: fontes, stdio: "pipe" });
  for (const f of readdirSync(fontes).filter(f => f.endsWith(".tgz"))) {
    const d = join(fontes, f.includes("archivo") ? "archivo" : "jetbrains");
    mkdirSync(d, { recursive: true });
    execSync(`tar -xzf "${join(fontes, f)}" -C "${d}"`);
  }
}
const A = w => join(fontes, "archivo/package/files", `archivo-latin-${w}-normal.woff2`);
const J = w => join(fontes, "jetbrains/package/files", `jetbrains-mono-latin-${w}-normal.woff2`);
const faces = [400, 500, 600, 800].map(w => `@font-face{font-family:'Archivo';font-weight:${w};src:url('file://${A(w)}') format('woff2');font-display:block}`)
  .concat([400, 500, 600].map(w => `@font-face{font-family:'JetBrains Mono';font-weight:${w};src:url('file://${J(w)}') format('woff2');font-display:block}`));
const pagePath = process.argv[3] ? process.argv[3] : join(ici, "../../prop/challenge-option2.html");
let src = readFileSync(pagePath, "utf8");
src = src.replace(/<link rel="(?:preconnect|stylesheet)"[^>]*fonts\.(?:googleapis|gstatic)\.com[^>]*>\n?/g, "");
src = src.replace("<style>", "<style>\n" + faces.join("\n") + "\n");
const apercu = join(dos, "apercu.html");
writeFileSync(apercu, '<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">' + src);

const b = await chromium.launch();
let defauts = 0;
for (const W of [360, 390, 430, 768, 1100, 1280]) {
  const p = await b.newPage({ viewport: { width: W, height: 900 } });
  const errs = [];
  p.on("pageerror", e => errs.push(e.message));
  p.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
  await p.goto("file://" + apercu);
  await p.waitForTimeout(4500);
  const r = await p.evaluate(() => {
    const hors = [];
    document.querySelectorAll("body *").forEach(el => {
      const rc = el.getBoundingClientRect();
      if (rc.width > 0 && (rc.right > document.documentElement.clientWidth + 1 || rc.left < -1)) {
        let q = el.parentElement, defile = false;
        while (q) { const st = getComputedStyle(q); if (st.overflowX === "auto" || st.overflowX === "scroll") { defile = true; break; } q = q.parentElement; }
        if (!defile) hors.push(el.tagName + "#" + el.id);
      }
    });
    return { doc: document.documentElement.scrollWidth, vue: document.documentElement.clientWidth, hors,
      jour: "J " + document.querySelector("#o-jour").textContent, mc: document.querySelectorAll("main .pending, main .stale").length === 0 };
  });
  const ok = !errs.length && r.doc <= r.vue && !r.hors.length && r.jour !== "J 0,0" && r.mc;
  if (!ok) defauts++;
  console.log(`${String(W).padStart(5)} px  ${ok ? "ok" : "DÉFAUT"}  doc ${r.doc}/${r.vue}  hors cadre ${r.hors.length ? r.hors.slice(0, 5).join(" ") : "aucun"}  ${r.jour}  Monte Carlo ${r.mc ? "rendu" : "en attente"}${errs.length ? "  erreurs : " + errs.join(" | ") : ""}`);
  if (W === 390 || W === 1280) await (await p.$("main > section")).screenshot({ path: join(dos, `figure1-${W}.png`) });
  await p.close();
}
await b.close();
console.log(`\naperçu et captures : ${dos}`);
process.exit(defauts ? 1 : 0);
