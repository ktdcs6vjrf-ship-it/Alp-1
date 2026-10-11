// Banc de rendu : ouvre chaque desk (et chaque onglet) à 390 px puis 1280 px,
// relève les débordements horizontaux, les erreurs de console, les éléments qui sortent
// de leur conteneur, et enregistre une capture par vue.
// node test/e2e.js <url> [deskId ...] [--shots dossier] [--full]
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const args = process.argv.slice(2);
const url = args[0];
const shotsIdx = args.indexOf('--shots');
const shots = shotsIdx >= 0 ? args[shotsIdx + 1] : null;
const full = args.includes('--full');
const only = args.slice(1).filter((a, i, arr) => !a.startsWith('--') && arr[i - 1] !== '--shots');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const report = [];
  for (const width of [390, 1280]) {
    const ctx = await b.newContext({ viewport: { width, height: width === 390 ? 844 : 900 }, deviceScaleFactor: width === 390 ? 2 : 1 });
    const p = await ctx.newPage();
    const errs = [];
    p.on('pageerror', e => errs.push('PAGEERR ' + e.message));
    p.on('console', m => { if (m.type() === 'error' && !/404|favicon|ERR_CERT|net::/.test(m.text())) errs.push(m.text()); });
    await p.goto(url);
    await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
    await p.reload();
    await p.waitForFunction(() => window.T && document.querySelector('#view').children.length > 0, null, { timeout: 15000 });
    await p.evaluate(() => document.fonts && document.fonts.ready);
    const desks = await p.evaluate(() => T.desks().map(d => ({ id: d.id, tabs: (d.tabs || []).map(t => t.id) })));
    for (const d of desks) {
      if (only.length && !only.includes(d.id)) continue;
      const tabs = d.tabs.length ? d.tabs : [null];
      for (const tab of tabs) {
        const before = errs.length;
        await p.evaluate(([id, tab]) => T.nav.go(id, tab), [d.id, tab]);
        await p.waitForTimeout(700);
        const m = await p.evaluate(() => {
          const sw = document.documentElement.scrollWidth, cw = document.documentElement.clientWidth;
          const view = document.getElementById('view'), vr = view.getBoundingClientRect();
          const out = [];
          view.querySelectorAll('*').forEach(el => {
            if (el.closest('.tbl,.heat,.tabs,svg,.pl-car')) return;
            const r = el.getBoundingClientRect();
            if (r.width === 0) return;
            if (r.right > vr.right + 2 || r.left < vr.left - 2) out.push((el.className && el.className.baseVal === undefined ? el.className : el.tagName) + ' ' + Math.round(r.left) + '→' + Math.round(r.right));
          });
          const text = view.innerText;
          return { sw, cw, out: out.slice(0, 6), nOut: out.length, empty: view.children.length === 0, err: /a rencontré une erreur/.test(text), nan: /NaN|undefined|\[object/.test(text) };
        });
        const name = d.id + (tab ? '-' + tab : '') + '-' + width;
        if (shots) await p.screenshot({ path: `${shots}/${name}.png`, fullPage: full });
        report.push({ view: name, overflow: m.sw > m.cw, outside: m.nOut, sample: m.out, deskError: m.err, nanText: m.nan, errors: errs.slice(before) });
      }
    }
    await ctx.close();
  }
  await b.close();
  const bad = report.filter(r => r.overflow || r.outside || r.deskError || r.nanText || r.errors.length);
  console.log(JSON.stringify({ views: report.length, bad: bad.length, details: bad }, null, 1));
})();
