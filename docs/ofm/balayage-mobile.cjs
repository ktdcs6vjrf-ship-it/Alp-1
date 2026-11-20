// Balayage de la version mobile, vue par vue : l'espace « Tous les sujets », puis chaque sujet.
// Un balayage de la page entière ne verrait plus que l'espace : les sujets fermés sont en display: none.
// Usage : INTER=<dossier des woff2 Inter> node docs/ofm/balayage-mobile.cjs docs/ofm/la-personne-mobile.html <sortie> [largeurs…]
// (INTER : npm install --prefix /tmp/f @fontsource/inter, puis /tmp/f/node_modules/@fontsource/inter/files).
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const doc = process.argv[2], out = process.argv[3];
const largeurs = (process.argv.slice(4).length ? process.argv.slice(4) : ['390']).map(Number);
const F = process.env.INTER || path.join(__dirname, 'fonts/inter');
const fontes = [400, 500, 600, 700, 800, 900].map((w) =>
  `@font-face{font-family:"Inter";src:url("file://${F}/inter-latin-${w}-normal.woff2") format("woff2");font-weight:${w};font-style:normal;}`).join('\n');
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const html = fs.readFileSync(doc, 'utf8').replace(/<link[^>]+fonts\.googleapis[^>]+>/g, '').replace('<style>', `<style>\n${fontes}\n`);
  const squelette = '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">';
  const tmp = path.join(out, 'apercu.html');
  fs.writeFileSync(tmp, squelette + html);
  const browser = await chromium.launch();
  for (const w of largeurs) {
    const page = await browser.newPage({ viewport: { width: w, height: 844 }, deviceScaleFactor: 1, hasTouch: true, isMobile: w < 700 });
    const erreurs = [];
    page.on('pageerror', (e) => erreurs.push(String(e)));
    page.on('console', (m) => { if (m.type() === 'error') erreurs.push(m.text()); });
    await page.goto('file://' + tmp);
    await page.evaluate(() => document.fonts.ready);
    const vues = await page.evaluate(() => ['sujets', ...[...document.querySelectorAll('main > section[id]')].map((s) => s.id)]);
    let total = { hs: 0, deb: 0, chev: 0, svgp: 0, petits: 0, cibles: 0 };
    for (const v of vues) {
      await page.evaluate((id) => { location.hash = id; }, v);
      await page.waitForTimeout(140);
      const r = await page.evaluate(() => {
        const vis = (el) => el.getClientRects().length > 0;
        const res = { vue: document.documentElement.dataset.vue, h: document.documentElement.scrollHeight, hs: document.documentElement.scrollWidth > window.innerWidth + 1, deb: [], chev: [], svgp: [], petits: [], cibles: [] };
        document.querySelectorAll('svg.mv').forEach((svg, k) => {
          if (!vis(svg)) return;
          const sb = svg.getBoundingClientRect();
          const textes = [...svg.querySelectorAll('text')];
          const boites = textes.map((t) => t.getBoundingClientRect());
          textes.forEach((t, i) => {
            const b = boites[i];
            if (b.left < sb.left - 2 || b.right > sb.right + 2 || b.top < sb.top - 2 || b.bottom > sb.bottom + 2) res.deb.push(t.textContent.slice(0, 24));
            const fs = parseFloat(getComputedStyle(t).fontSize) * (sb.width / svg.viewBox.baseVal.width);
            if (fs < 10.4) res.svgp.push(fs.toFixed(1) + ' ' + t.textContent.slice(0, 16));
          });
          for (let i = 0; i < boites.length; i++) for (let j = i + 1; j < boites.length; j++) {
            const a = boites[i], b = boites[j];
            if (Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1.5 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1.5)
              res.chev.push(textes[i].textContent.slice(0, 16) + ' × ' + textes[j].textContent.slice(0, 16));
          }
        });
        document.querySelectorAll('main *, .dock *, .appbar *').forEach((el) => {
          if (!vis(el) || el.closest('svg')) return;
          const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
          if (!own) return;
          const fs = parseFloat(getComputedStyle(el).fontSize);
          if (fs < 12) res.petits.push(el.tagName.toLowerCase() + '.' + el.className + ' ' + fs);
        });
        document.querySelectorAll('a, button, summary').forEach((el) => {
          if (!vis(el) || el.closest('.refs')) return;
          const b = el.getBoundingClientRect();
          if (b.width < 43.5 || b.height < 43.5) res.cibles.push(el.tagName.toLowerCase() + ' « ' + el.textContent.trim().slice(0, 20) + ' » ' + Math.round(b.width) + '×' + Math.round(b.height));
        });
        return res;
      });
      total.hs += r.hs; total.deb += r.deb.length; total.chev += r.chev.length; total.svgp += r.svgp.length; total.petits += r.petits.length; total.cibles += r.cibles.length;
      const pb = [r.hs ? 'DÉFILEMENT H' : '', r.deb.length ? 'hors cadre ' + r.deb.slice(0, 3) : '', r.chev.length ? 'chev ' + r.chev.slice(0, 3) : '', r.svgp.length ? 'svg<10.4 ' + r.svgp.slice(0, 3) : '', r.petits.length ? '<12px ' + [...new Set(r.petits)].slice(0, 4) : '', r.cibles.length ? 'cibles ' + r.cibles.slice(0, 4) : ''].filter(Boolean);
      if (w === largeurs[0] || pb.length) console.log(`${w}px ${v.padEnd(10)} vue=${r.vue} h=${r.h} ${pb.join(' | ')}`);
      if (w === largeurs[0]) { await page.evaluate(() => window.scrollTo(0, 0)); await page.waitForTimeout(60); await page.screenshot({ path: path.join(out, `v-${v}.png`) }); }
    }
    console.log(`== ${w}px total`, JSON.stringify(total), erreurs.length ? 'ERREURS ' + erreurs.slice(0, 5) : 'aucune erreur JS');
    await page.close();
  }
  await browser.close();
})();
