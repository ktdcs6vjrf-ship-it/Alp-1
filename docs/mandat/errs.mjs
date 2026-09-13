import { chromium } from 'playwright';
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
for (const W of [360, 390, 430, 768, 1100, 1400]) {
  const p = await b.newPage({ viewport: { width: W, height: 900 } });
  const e = []; p.on('pageerror', x => e.push(String(x))); p.on('console', m => { if (m.type()==='error') e.push('console: '+m.text()); });
  await p.goto('file://' + process.cwd() + '/preview_s38.html');
  await p.waitForTimeout(500);
  const info = await p.evaluate(() => {
    const svgs = [...document.querySelectorAll('svg.fig')];
    return { figs: svgs.length, vides: svgs.filter(s => s.childElementCount < 3).map(s => s.id),
             sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth };
  });
  console.log(String(W).padStart(5), JSON.stringify(info), 'erreurs', e.length, e.slice(0,2));
  await p.close();
}
await b.close();
