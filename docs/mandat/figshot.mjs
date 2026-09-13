import { chromium } from 'playwright';
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const p = await b.newPage({ viewport: { width: 1200, height: 900 }, deviceScaleFactor: 2 });
await p.goto('file://' + process.cwd() + '/preview_s38.html');
await p.waitForTimeout(600);
for (const id of process.argv.slice(2)) {
  const e = await p.$('#' + id);
  await e.screenshot({ path: `z_${id}.png` });
}
console.log('ok');
await b.close();
