// Banc de rendu du desk macro sur un rapport FACTICE (jamais publié) : vérifie chaque type de bloc.
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const url = process.argv[2], out = process.argv[3];
const months = ['2025-01','2025-02','2025-03','2025-04','2025-05','2025-06','2025-07','2025-08'];
const rep = { kind: 'report', date: '2026-10-09', title: 'FIXTURE — test de rendu des blocs', source: 'Banc de test, aucune donnée réelle', lede: 'Rapport factice pour vérifier la mise en page de chaque bloc.', tags: ['Test', 'Rendu'],
  blocks: [
    { t: 'h', text: 'Indicateurs' },
    { t: 'kpis', items: [{ label: 'Série A', value: 1.5, unit: '%', delta: 0.2 }, { label: 'Série B', value: '2,1', unit: '%' }, { label: 'Série C', value: 48.2 }] },
    { t: 'p', text: 'Un paragraphe de test qui n\'a aucune valeur de marché.' },
    { t: 'line', title: 'Deux séries mensuelles', unit: '%', series: [{ name: 'A', points: months.map((m, i) => [m, 2 + Math.sin(i)]) }, { name: 'B', points: months.map((m, i) => [m, 1.5 + Math.cos(i) * 0.5]), dash: true }], hlines: [{ y: 2, label: 'Repère' }] },
    { t: 'bar', title: 'Barres', unit: 'pb', cats: ['Un', 'Deux', 'Trois', 'Quatre'], series: [{ name: 'X', values: [3, -2, 5, 1] }, { name: 'Y', values: [1, 2, -1, 4] }] },
    { t: 'bar', title: 'Barres horizontales', horizontal: true, cats: ['Énergie', 'Technologie', 'Santé'], series: [{ values: [1.2, -0.4, 0.7] }] },
    { t: 'table', title: 'Tableau', cols: ['Ligne', { k: 'v', label: 'Valeur', align: 'r' }, 'Commentaire'], rows: [['Un', 1.25, 'Court'], ['Deux', -0.5, 'Un commentaire assez long pour tester le retour à la ligne dans la cellule']] },
    { t: 'heat', title: 'Carte de chaleur', unit: '%', rows: ['1 m', '3 m', '1 a'], cols: ['A', 'B', 'C', 'D'], values: [[1, -2, 3, 0.5], [0, 1, -1, 2], [2, 2, -3, 1]], diverging: true },
    { t: 'callout', text: 'Encadré de test.' },
    { t: 'source', text: 'Banc de test' }
  ] };
const regime = { kind: 'regime', date: '2026-10-09', growth: 'ralentit', inflation: 'accélère', label: 'FIXTURE', note: 'Test', source: 'Banc' };
const cal = [
  { date: '2026-10-10', time: '14:30', event: 'FIXTURE évènement 1', country: 'US', impact: 3, prev: '0,3 %', cons: '0,2 %', actual: '' },
  { date: '2026-10-10', time: '16:00', event: 'FIXTURE évènement 2', country: 'US', impact: 2, prev: 49.1, cons: 49.5 },
  { date: '2026-10-12', time: '20:00', event: 'FIXTURE évènement 3', country: 'US', impact: 3 }];
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  for (const width of [390, 1280]) {
    const ctx = await b.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: width === 390 ? 2 : 1 });
    const p = await ctx.newPage(); const errs = [];
    p.on('pageerror', e => errs.push(e.message));
    await p.goto(url);
    await p.evaluate(([r, g, c]) => { localStorage.clear(); localStorage.setItem('alpdesk:sh:macro', JSON.stringify([r, g])); localStorage.setItem('alpdesk:sh:calendar', JSON.stringify(c)); }, [rep, regime, cal]);
    await p.reload(); await p.waitForFunction(() => window.T && document.querySelector('#view').children.length > 0);
    for (const tab of ['rapports', 'regime', 'calendrier']) {
      await p.evaluate(t => T.nav.go('macro', t), tab); await p.waitForTimeout(600);
      if (tab === 'rapports') { await p.click('#view .ma-rep'); await p.waitForTimeout(600); }
      const m = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, nan: /NaN|undefined|\[object/.test(document.getElementById('view').innerText) }));
      await p.screenshot({ path: `${out}/fx-${tab}-${width}.png`, fullPage: true });
      console.log(tab, width, JSON.stringify(m), errs.join('|'));
    }
    await ctx.close();
  }
  await b.close();
})();
