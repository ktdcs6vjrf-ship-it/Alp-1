import { chromium } from 'playwright';
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const p = await b.newPage();
const errs = []; p.on('pageerror', e => errs.push(String(e)));
await p.goto('file://' + process.cwd() + '/preview_s38.html');
await p.waitForTimeout(600);
await p.pdf({ path: 'mandat.pdf', format: 'A4', printBackground: true, margin: { top: '13mm', bottom: '13mm', left: '11mm', right: '11mm' } });
console.log('pdf ok, errs', errs.length);
// rendu en media print, pour regarder
await p.emulateMedia({ media: 'print' });
await p.setViewportSize({ width: 794, height: 1123 });
await p.waitForTimeout(300);
const info = await p.evaluate(() => ({ scrollW: document.documentElement.scrollWidth, clientW: document.documentElement.clientWidth, po: getComputedStyle(document.querySelector('.printonly')).display }));
console.log(JSON.stringify(info));
await b.close();
