// Banc de pine/alp0-zscore-vwap.pine : la heatmap z-score et le VWAP σ seuls.
// Mêmes contrôles que les scénarios M et K du banc d'alp0-zones, sur le
// fichier autonome. Lancer : node zscore-vwap.mjs
import { executer, seance } from './banc.mjs';

const F = 'alp0-zscore-vwap.pine';
const J = '2026-11-06';
let ok = 0, ko = 0;
const echecs = [];
function verifie(nom, cond, detail = '') {
  if (cond) { ok++; console.log('  ok   ' + nom); }
  else { ko++; echecs.push(nom); console.log('  ÉCHEC ' + nom + (detail ? '  →  ' + detail : '')); }
}
const vide = v => v === null || v === undefined || Number.isNaN(v);

console.log('Z-score');
{
  const o4 = x => (x.open + x.high + x.low + x.close) / 4;
  const zRef = (bs, i, n = 50) => {
    if (i < n - 1) return NaN;
    const w = bs.slice(i - n + 1, i + 1).map(o4);
    const m = w.reduce((a, b) => a + b, 0) / n;
    const sd = Math.sqrt(w.reduce((a, b) => a + (b - m) * (b - m), 0) / n);
    return sd === 0 ? NaN : (o4(bs[i]) - m) / sd;
  };
  const b = seance(J, '00:00', '02:30', [['00:00', 29200], ['00:40', 29230], ['01:10', 29190], ['01:40', 29260], ['02:30', 29240]]);
  const r = await executer(F, b);
  const z = r.ctx.plots['Z-Score'].data.map(x => x.value);
  verifie('préchauffage : z = na sur les 49 premières bougies', z.slice(0, 49).every(vide));
  const ecart = Math.max(...b.map((_, i) => i).filter(i => i >= 49).map(i => Math.abs(z[i] - zRef(b, i))));
  verifie('z-score = référence indépendante sur toutes les bougies', ecart < 1e-9, String(ecart));
  const hm = r.ctx.plots['Z-Score Heatmap'].data;
  const canal = (c, k) => c.startsWith('#') ? parseInt(c.slice(1 + 2 * k, 3 + 2 * k), 16) : +c.match(/\d+/g)[k];
  const grad = b.map((_, i) => i).filter(i => i >= 49 && Math.abs(zRef(b, i)) >= 2 && Math.abs(zRef(b, i)) < 3);
  verifie('entre T1 et T2 : dégradé cyan → magenta', grad.length > 0 && grad.every(i => canal(hm[i].options.color, 0) >= 45 && canal(hm[i].options.color, 0) < 229 && canal(hm[i].options.color, 2) >= 173), String(grad.length));
  const neutres = b.map((_, i) => i).filter(i => i >= 49 && Math.abs(zRef(b, i)) < 2);
  verifie('sous T1 : neutre', neutres.length > 0 && neutres.every(i => hm[i].options.color === 'rgb(51, 51, 51)'));
  const plat = seance(J, '00:00', '01:01', [['00:00', 29200]]);
  Object.assign(plat.at(-1), { open: 29200, close: 29230, high: 29230, low: 29200 });
  const rp = await executer(F, plat);
  const zp = rp.ctx.plots['Z-Score'].data.map(x => x.value);
  verifie('prix immobile : z = na', vide(zp.at(-2)));
  verifie('marche isolée après un plat : z = 7', Math.abs(zp.at(-1) - 7) < 1e-9, String(zp.at(-1)));
  verifie('au-delà de T2 : magenta', rp.ctx.plots['Z-Score Heatmap'].data.at(-1).options.color === 'rgb(229, 5, 255)');
  const rc = await executer(F, plat, { 'Custom Wick/Border': true });
  const o = rc.ctx.plots['Z-Score Heatmap'].data.at(-1).options;
  const rgb = c => c.match(/[\d.]+/g).map(Number);
  verifie('mèche +10 %, bordure −20 %', Math.abs(rgb(o.wickcolor)[0] - Math.min(255, 229 * 1.1)) < 1 && Math.abs(rgb(o.bordercolor)[0] - 229 * 0.8) < 1, `${o.wickcolor} ${o.bordercolor}`);
  const ri = await executer(F, b, { 'Threshold T1 (σ)': 3, 'Threshold T2 (σ)': 2 });
  const cols = new Set(b.map((_, i) => i).filter(i => i >= 49).map(i => ri.ctx.plots['Z-Score Heatmap'].data[i].options.color));
  verifie('T2 ≤ T1 : neutre ou magenta seulement', [...cols].every(c => c === 'rgb(51, 51, 51)' || c === 'rgb(229, 5, 255)'), JSON.stringify([...cols]));
  const ro = await executer(F, b, { 'Colorer les bougies (heatmap)': false });
  verifie('heatmap désactivée : aucune bougie tracée', ro.ctx.plots['Z-Score Heatmap'].data.every(x => x.value.every(vide)));
}

console.log('VWAP');
{
  const b = seance(J, '00:00', '03:00', [['00:00', 29200], ['01:00', 29260], ['02:00', 29180], ['03:00', 29230]]);
  b.forEach((x, i) => { x.volume = 50 + (i * 37) % 200; });
  const tp = x => (x.high + x.low + x.close) / 3;
  const cumul = arr => { let sv = 0, spv = 0, sp2v = 0; for (const x of arr) { const p = tp(x); sv += x.volume; spv += p * x.volume; sp2v += p * p * x.volume; }
    const vw = spv / sv; return [vw, Math.sqrt(sp2v / sv - vw * vw)]; };
  const ra = await executer(F, b, { 'VWAP and SDev:': 'AVWAP', 'Start Date AVWAP': b[0].openTime });
  const [vw, sd] = cumul(b);
  verifie('VWAP pondéré par le volume (hlc3), ancré', Math.abs(ra.vwap.at(-1) - vw) < 1e-6, `${ra.vwap.at(-1)} vs ${vw}`);
  const lab = ra.etiquettes.filter(e => e.text.startsWith('---------'));
  verifie('treize étiquettes (VWAP + 12 bandes), décalées d\'une barre', lab.length === 13 && lab.every(e => e.x === b.length), String(lab.length));
  const sd25 = lab.find(e => e.text === '--------- SD +2.5');
  verifie('bande +2.5σ = VWAP + 2.5·σ', !!sd25 && Math.abs(sd25.y - (vw + 2.5 * sd)) < 1e-6);
  const rd = await executer(F, b);
  let k = -1;
  for (let i = 1; i < b.length; i++) if (Math.abs(rd.vwap[i] - tp(b[i])) < 1e-9 && Math.abs(rd.vwap[i - 1] - tp(b[i])) > 1e-9) { k = i; break; }
  const [vwP, sdP] = cumul(b.slice(0, k));
  const prev = (rd.ctx.plots['Previous VWAP']?.data ?? []).map(x => x.value);
  const prev2 = (rd.ctx.plots['Previous VWAP - STDEV +2']?.data ?? []).map(x => x.value);
  verifie('« Day » : VWAP précédent = VWAP final de la période close', k > 0 && Math.abs(prev.at(-1) - vwP) < 1e-6, `${prev.at(-1)} vs ${vwP}`);
  verifie('VWAP précédent +2σ', Math.abs(prev2.at(-1) - (vwP + 2 * sdP)) < 1e-6);
  const [vwJ] = cumul(b.slice(k));
  verifie('VWAP du jour repart de la remise à zéro', Math.abs(rd.vwap.at(-1) - vwJ) < 1e-6);
  verifie('aucune ligne ni boîte : seulement des tracés et des étiquettes', rd.lignes.length === 0 && rd.boites.length === 0);
}

console.log(`\n${ok} contrôle(s) réussi(s), ${ko} échec(s)`);
if (ko) { console.log('Échecs : ' + echecs.join(' | ')); process.exitCode = 1; }
