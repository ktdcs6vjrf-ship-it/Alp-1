import { chromium } from 'playwright';
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
for (const W of [360, 390, 430, 768, 1100]) {
  const p = await b.newPage({ viewport: { width: W, height: 900 } });
  await p.goto('file://' + process.cwd() + '/preview_s38.html');
  await p.waitForTimeout(250);
  const r = await p.evaluate(() => {
    const bad = [];
    document.querySelectorAll('*').forEach(el => {
      if (el.scrollWidth - el.clientWidth > 2 && el.clientWidth > 0) {
        const st = getComputedStyle(el);
        if (st.overflowX === 'auto' || st.overflowX === 'scroll' || el === document.documentElement)
          bad.push(el.tagName + '.' + el.className + ' ' + el.scrollWidth + '>' + el.clientWidth);
      }
    });
    return { doc: document.documentElement.scrollWidth, view: document.documentElement.clientWidth, bad };
  });
  console.log(String(W).padStart(5), 'doc', r.doc, 'vue', r.view, '| defilants:', r.bad.length ? r.bad.join(' ; ') : 'aucun');
  await p.close();
}
await b.close();
