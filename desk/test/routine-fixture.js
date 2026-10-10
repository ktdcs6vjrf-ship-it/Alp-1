// Rendu du desk Routine sur un journal FACTICE local (jamais publié).
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const url = process.argv[2], out = process.argv[3];
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(url);
  await p.evaluate(() => {
    localStorage.clear();
    const R = T.lib.routine, today = T.day.key(), rows = [], days = {};
    let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    let d = R.addDays(today, -70);
    while (d < today) {
      const wd = R.weekday(d);
      if (wd && wd !== 6 && rnd() > 0.15) {
        const base = Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10), 6);
        const k = 1 + Math.floor(rnd() * 3);
        for (let i = 0; i < k; i++) { const win = rnd() < 0.45, plan = rnd() < 0.85; rows.push({ id: 'x' + rows.length, at: base + i * 9e5, kind: 'pris', side: 'long', status: 'clos', pnl: win ? 220 : -150, r: win ? 1.5 : -1, plan, u: 1 }); }
        if (rnd() < 0.5) rows.push({ id: 'x' + rows.length, at: base + 4e6, kind: 'refus', stage: 'vwap', u: 1 });
        const g = 'ABBCD'[Math.floor(rnd() * 5)];
        days[d] = { mode: d < R.addDays(today, -40) ? 'replay' : 'sim', review: { grade: g } };
      }
      d = R.addDays(d, 1);
    }
    const t0 = Date.now() - 3 * 36e5;
    [[-150, true], [220, false], [-150, true], [-150, true]].forEach((x, i) => rows.push({ id: 'y' + i, at: t0 + i * 6e5, kind: 'pris', side: 'short', setup: 'Bande VWAP · Rejet', status: 'clos', pnl: x[0], r: x[0] > 0 ? 1.5 : -1, plan: x[1], u: 1 }));
    localStorage.setItem('alpdesk:journal', JSON.stringify(rows));
    localStorage.setItem('alpdesk:s:routine:days', JSON.stringify({ v: days, t: Date.now() }));
  });
  await p.reload(); await p.waitForFunction(() => window.T && document.querySelector('#view').children.length > 0);
  for (const tab of ['pendant', 'apres', 'progression']) {
    await p.evaluate(t => T.nav.go('routine', t), tab); await p.waitForTimeout(700);
    await p.screenshot({ path: `${out}/fx-${tab}.png`, fullPage: true });
  }
  await p.evaluate(() => T.nav.go('home')); await p.waitForTimeout(700); await p.screenshot({ path: `${out}/fx-home.png`, fullPage: true });
  console.log('errors', errs);
  await b.close();
})();
