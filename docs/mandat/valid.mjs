import { chromium } from 'playwright';
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const p = await b.newPage({ viewport: { width: 900, height: 900 } });
await p.goto('file://' + process.cwd() + '/preview_s38.html');
await p.waitForTimeout(200);
// controle de structure : un bloc qui deborde de son parent trahit une
// balise non fermee, ce qu'aucun rendu ne signale
const r = await p.evaluate(() => {
  const out = [];
  ['.brief', '.infra', '.offer', '.crit', '.lex', '.cmp', '.terms', '.toc'].forEach(sel => {
    document.querySelectorAll(sel).forEach(el => {
      const h = el.getBoundingClientRect().height;
      out.push(sel + ' h=' + Math.round(h) + (h > 3000 ? '  ← ANORMAL' : ''));
    });
  });
  return out;
});
console.log(r.join('\n'));
await b.close();
