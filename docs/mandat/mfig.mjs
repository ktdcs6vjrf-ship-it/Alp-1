import { chromium } from 'playwright';
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const p = await b.newPage({ viewport: { width: 390, height: 900 }, deviceScaleFactor: 3 });
const errs = []; p.on('pageerror', e => errs.push(String(e)));
await p.goto('file://' + process.cwd() + '/preview_s38.html');
await p.waitForTimeout(600);
for (const id of process.argv.slice(2)) {
  const e = await p.$('#' + id);
  if (!e) { console.log('absent', id); continue; }
  await e.screenshot({ path: `n_${id}.png` });
}
console.log('errs', errs.length, errs.slice(0,2));
await b.close();
