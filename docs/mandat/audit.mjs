import { chromium } from 'playwright';
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
for (const VW of [390, 1100]) {
const p = await b.newPage({ viewport: { width: VW, height: 1000 } });
await p.goto('file://' + process.cwd() + '/preview_s38.html');
await p.waitForTimeout(400);

const res = await p.evaluate(() => {
  const out = { debord: [], chevauch: [], vides: [], contraste: [] };
  document.querySelectorAll('svg.fig').forEach((svg, si) => {
    const sb = svg.getBoundingClientRect();
    const id = svg.id || ('fig' + si);
    // 1. debordement : toute marque hors de la boite du svg
    svg.querySelectorAll('text,rect,path,circle,line,polyline').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) return;
      if (r.left < sb.left - 1 || r.right > sb.right + 1 || r.top < sb.top - 1 || r.bottom > sb.bottom + 1) {
        out.debord.push(id + ' ' + el.tagName + ' "' + (el.textContent || '').slice(0, 26) + '"');
      }
    });
    // 2. chevauchement de textes
    const T = [...svg.querySelectorAll('text')].map(t => ({ t, r: t.getBoundingClientRect() }))
      .filter(o => o.r.width > 0);
    for (let i = 0; i < T.length; i++) for (let j = i + 1; j < T.length; j++) {
      const a = T[i].r, c = T[j].r;
      const ox = Math.min(a.right, c.right) - Math.max(a.left, c.left);
      const oy = Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top);
      if (ox > 2 && oy > 2) {
        out.chevauch.push(id + ' « ' + T[i].t.textContent.slice(0, 22) + ' » × « ' + T[j].t.textContent.slice(0, 22) + ' »');
      }
    }
    // 3. occupation : part de la boite reellement peinte
    let minx = 1e9, maxx = -1e9, miny = 1e9, maxy = -1e9, n = 0;
    svg.querySelectorAll('text,rect,path,circle,line,polyline').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) return;
      if (el.classList.contains('bg')) return;
      minx = Math.min(minx, r.left); maxx = Math.max(maxx, r.right);
      miny = Math.min(miny, r.top); maxy = Math.max(maxy, r.bottom); n++;
    });
    if (n) {
      const fw = (maxx - minx) / sb.width, fh = (maxy - miny) / sb.height;
      if (fw < 0.9 || fh < 0.9) out.vides.push(id + ' occupe ' + (100 * fw).toFixed(0) + '% × ' + (100 * fh).toFixed(0) + '%');
    }
  });
  return out;
});
console.log('\n=== largeur ' + VW + ' px ===');
console.log('— débordements —'); console.log(res.debord.length ? res.debord.join('\n') : 'aucun');
console.log('\n— chevauchements de texte —'); console.log(res.chevauch.length ? res.chevauch.join('\n') : 'aucun');
console.log('\n— occupation faible —'); console.log(res.vides.length ? res.vides.join('\n') : 'toutes pleines');
await p.close();
}
await b.close();
