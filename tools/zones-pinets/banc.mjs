// Banc d'essai de pine/alp0-zones.pine sous PineTS (runtime Pine v6 de LuxAlgo).
// Ce n'est pas le compilateur de TradingView : il exécute le VRAI script sur
// des bougies synthétiques et lit ce qu'il dessine. Voir README.md.
import { PineTS, Indicator } from 'pinets';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ICI = path.dirname(fileURLToPath(import.meta.url));
export const SRC = fs.readFileSync(path.join(ICI, '..', '..', 'pine', 'alp0-zones.pine'), 'utf8');
export const MIN = 60000;

// Heure de Paris → horodatage UTC, sans table d'heure d'été écrite à la main :
// on essaie les deux décalages possibles et on garde celui qui retombe juste.
const fmt = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Paris', hourCycle: 'h23',
  year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
export function paris(jour, hhmm) {
  const [y, mo, d] = jour.split('-').map(Number);
  const [h, mi] = hhmm.split(':').map(Number);
  for (const off of [1, 2]) {
    const t = Date.UTC(y, mo - 1, d, h - off, mi);
    const p = Object.fromEntries(fmt.formatToParts(new Date(t)).map(x => [x.type, x.value]));
    if (+p.year === y && +p.month === mo && +p.day === d && +p.hour === h && +p.minute === mi) return t;
  }
  throw new Error(`heure inexistante à Paris : ${jour} ${hhmm}`);
}

// Une séance de bougies d'une minute, prix interpolé entre des jalons
// [« HH:MM », prix], avec des bougies imposées { « HH:MM »: {o,h,l,c} }.
export function seance(jour, debut, fin, jalons, imposees = {}) {
  const out = [];
  const t0 = paris(jour, debut), t1 = paris(jour, fin);
  const js = jalons.map(([hm, px]) => [paris(jour, hm), px]);
  const prixA = t => {
    if (t <= js[0][0]) return js[0][1];
    for (let i = 1; i < js.length; i++) if (t <= js[i][0]) {
      const [ta, pa] = js[i - 1], [tb, pb] = js[i];
      return pa + (pb - pa) * (t - ta) / (tb - ta);
    }
    return js[js.length - 1][1];
  };
  const q = x => Math.round(x * 4) / 4;
  for (let t = t0; t < t1; t += MIN) {
    const hm = new Date(t).toISOString();
    const loc = Object.fromEntries(fmt.formatToParts(new Date(t)).map(x => [x.type, x.value]));
    const cle = `${loc.hour}:${loc.minute}`;
    let o = q(prixA(t)), c = q(prixA(t + MIN));
    let h = Math.max(o, c) + 0.25, l = Math.min(o, c) - 0.25;
    if (imposees[cle]) ({ o, h, l, c } = imposees[cle]);
    out.push({ open: o, high: h, low: l, close: c, volume: 100, openTime: t, closeTime: t + MIN });
  }
  return out;
}

// Exécute un fichier Pine quelconque du dossier pine/ (sans entrée imposée).
export async function executer(fichier, bougies, entrees = {}) {
  const source = fs.readFileSync(path.join(ICI, '..', '..', 'pine', fichier), 'utf8');
  const ctx = await new PineTS(bougies, 'NQ1!', '1').run(new Indicator(source, entrees));
  const der = k => ((ctx.plots[k]?.data ?? []).at(-1)?.value ?? []).filter(o => !o._deleted);
  return { ctx, etiquettes: der('__labels__'), lignes: der('__lines__'), boites: der('__boxes__'),
           vwap: (ctx.plots['VWAP']?.data ?? []).map(x => x.value) };
}

export async function lancer(texte, bougies, entrees = {}) {
  const ind = new Indicator(SRC, {
    'Zone A — relevés du jour': texte,
    'Contrat du graphique (vide = automatique)': 'NQ',
    ...entrees,
  });
  const pts = new PineTS(bougies, 'NQ1!', '1');
  const ctx = await pts.run(ind);
  const der = k => {
    const d = ctx.plots[k]?.data ?? [];
    return (d.at(-1)?.value ?? []).filter(o => !o._deleted);
  };
  const tables = der('__tables__');
  const cellules = [];
  for (const tb of tables) for (const ligne of tb.cells ?? []) for (const c of ligne ?? []) if (c && c.text) cellules.push(c.text);
  return { ctx, lignes: der('__lines__'), etiquettes: der('__labels__'), boites: der('__boxes__'), tables, cellules,
           vwap: (ctx.plots['VWAP']?.data ?? []).map(x => x.value) };
}
