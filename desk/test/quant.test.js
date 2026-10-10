// Tests du desk « Quant & backtest » : node test/quant.test.js (sortie non nulle si échec).
// Les séries de barres sont construites à la main et leur résultat se calcule à la main (commentaires).
// Les références CSCV, PSR et DSR viennent du dépôt (alp1/overfit.py, alp1/pathstats.py), exécuté en Python.
const fs = require('fs'), path = require('path'), vm = require('vm');
const { T, lib: Q } = require('./harness')('quant');
let fails = 0, passes = 0;
function ok(cond, msg) { if (cond) passes++; else { fails++; console.error('ÉCHEC', msg); } }
function near(a, b, tol, msg) { const good = typeof a === 'number' && typeof b === 'number' && (a === b || Math.abs(a - b) <= tol * Math.max(1, Math.abs(b))); ok(good, msg + ' : ' + a + ' attendu ' + b); }
function section(t) { console.log('· ' + t); }

/* Barres à la main : une séance qui s’ouvre le lundi 5 janvier 2026 à 23:00 UTC = 18:00 New York = 00:00 Paris. */
const T0 = Date.UTC(2026, 0, 5, 23, 0);
const flat = (i, p, v) => ({ t: T0 + i * 60000, o: p, h: p, l: p, c: p, v: v == null ? 1 : v });
const bar = (i, o, h, l, c, v) => ({ t: T0 + i * 60000, o, h, l, c, v: v == null ? 1 : v });
const P0 = { k: 1, stop: 2, mode: 'rejet', from: 0, to: 9, warm: 0, maxPer: 0, comm: 0, slip: 0, tick: 0.25, pv: 2 };
const base = () => [flat(0, 98), flat(1, 102), flat(2, 98), flat(3, 102)];

section('Le moteur est autonome (exécutable dans un worker)');
{
  const fresh = vm.runInNewContext('(' + Q.engine.toString() + ')', {});
  const r = fresh({ op: 'vwap', bars: base(), o: {} });
  ok(Array.isArray(r.vwap) && r.vwap.length === 4, 'le moteur tourne dans un contexte vide, sans T');
  near(r.vwap[3], 100, 1e-12, 'VWAP dans le contexte vide');
}

section('VWAP de séance');
{
  const pre = Q.sessionVwap(base());
  near(pre.vwap[1], 100, 1e-12, 'VWAP après 98, 102');
  near(pre.sd[1], 2, 1e-12, 'σ après 98, 102 : √((4 + 4)/2) = 2');
  near(pre.vwap[2], 298 / 3, 1e-12, 'VWAP après 98, 102, 98');
  near(pre.sd[2], Math.sqrt(32 / 9), 1e-12, 'σ après trois barres : √(32/9)');
  ok(pre.sd[0] === 0, 'σ nul à la première barre');
  ok(pre.parMin[0] === 0 && pre.nyMin[0] === 18 * 60, 'minute de Paris 00:00, de New York 18:00');
  const w = Q.sessionVwap([bar(0, 100, 100, 100, 100, 1), bar(1, 103, 103, 103, 103, 2)]);
  near(w.vwap[1], 102, 1e-12, 'VWAP pondérée : (100·1 + 103·2)/3');
  near(w.sd[1], Math.sqrt(2), 1e-12, 'σ pondéré : √((1·4 + 2·1)/3)');
  const tp = Q.sessionVwap([bar(0, 100, 104, 98, 101, 5)]);
  near(tp.vwap[0], (104 + 98 + 101) / 3, 1e-12, 'prix typique (h + l + c)/3');
  const u = Q.sessionVwap([bar(0, 100, 100, 100, 100, 0), bar(1, 104, 104, 104, 104, 0)]);
  ok(u.uniform && Math.abs(u.vwap[1] - 102) < 1e-12, 'sans volume : poids égaux, VWAP 102');
  const prev = { t: T0 - 2 * 60000, o: 50, h: 50, l: 50, c: 50, v: 9 };
  const s2 = Q.sessionVwap([prev].concat(base()));
  ok(s2.sessions.length === 2 && s2.sess[0] === 0 && s2.sess[1] === 1, '17:58 New York appartient à la séance précédente');
  near(s2.vwap[1], 98, 1e-12, 'la VWAP repart à 18:00 New York, sans la barre de la veille');
  ok(s2.sessions[1].key === '2026-01-06' && s2.sessions[0].key === '2026-01-05', 'clé de séance : date new-yorkaise décalée de six heures');
  // été : 18:00 New York = 22:00 UTC (EDT)
  const ete = Q.sessionVwap([{ t: Date.UTC(2026, 6, 6, 21, 59), o: 1, h: 1, l: 1, c: 1, v: 1 }, { t: Date.UTC(2026, 6, 6, 22, 0), o: 1, h: 1, l: 1, c: 1, v: 1 }]);
  ok(ete.sessions.length === 2, 'heure d’été : la séance change à 22:00 UTC');
  ok(ete.parMin[1] === 0, 'heure d’été : 22:00 UTC = 00:00 Paris (CEST)');
}

section('Backtest : séries construites à la main');
{
  // A — short au rejet. Après b4 : prix typiques 98, 102, 98, 102, 102 → VWAP 100,4, σ = √3,84.
  // Bande haute 100,4 + √3,84 = 102,3596 : b4 la touche (haut 104) et clôture dedans (101), au-dessus de la VWAP.
  // Entrée 101, stop 104,3596, objectif VWAP(b4) = 100,4 touché en b5 (bas 100) : +0,6 pt = +1,20 $.
  const A = base().concat([bar(4, 102, 104, 101, 101), bar(5, 101, 101, 100, 100)]);
  const r = Q.backtest(A, P0), t = r.trades[0], U4 = 100.4 + Math.sqrt(3.84);
  ok(r.trades.length === 1, 'A : un seul trade (aucun signal en b1–b3 : clôture sur la bande, pas dedans)');
  ok(t.side === -1 && t.i === 4 && t.j === 5, 'A : short en b4, sorti en b5');
  near(t.entry, 101, 1e-12, 'A : entrée à la clôture du rejet');
  near(t.stop, U4 + 2, 1e-12, 'A : stop deux points au-delà de la bande');
  near(t.exit, 100.4, 1e-12, 'A : sortie à la VWAP de la barre précédente');
  ok(t.fin === 'objectif', 'A : fin objectif');
  near(t.pts, 0.6, 1e-9, 'A : +0,6 point');
  near(t.pnl, 1.2, 1e-9, 'A : +1,20 $ (2 $ le point, sans frais)');
  near(t.r, 0.6 / (U4 + 2 - 101), 1e-9, 'A : R = 0,6 / 3,3596');
  ok(t.hour === 0, 'A : heure de Paris 0');
  // A avec frais : 1,24 $ + 2 ticks × 0,25 × 2 $ = 2,24 $
  const rc = Q.backtest(A, Object.assign({}, P0, { comm: 1.24, slip: 2 }));
  near(rc.trades[0].pnl, 1.2 - 2.24, 1e-9, 'A : frais 1,24 $ + 2 ticks = 2,24 $');
  near(rc.cost, 2.24, 1e-12, 'coût par trade');
  // A avec échauffement de 5 minutes : b4 est à la quatrième minute, aucun trade
  ok(Q.backtest(A, Object.assign({}, P0, { warm: 5 })).trades.length === 0, 'A : échauffement de 5 min, pas de trade');
  // A avec la barre de la veille : même trade
  const prev = { t: T0 - 2 * 60000, o: 50, h: 50, l: 50, c: 50, v: 9 };
  const ra = Q.backtest([prev].concat(A), P0);
  ok(ra.trades.length === 1 && Math.abs(ra.trades[0].exit - 100.4) < 1e-9, 'A : la séance précédente ne pèse pas sur la VWAP');

  // B — stop : b5 monte à 105, stop touché à 104,3596 : −3,3596 pt, R = −1 exactement sans frais.
  const B = base().concat([bar(4, 102, 104, 101, 101), bar(5, 101, 105, 101, 105)]);
  const b = Q.backtest(B, P0).trades[0];
  ok(b.fin === 'stop', 'B : fin stop');
  near(b.exit, U4 + 2, 1e-12, 'B : sortie au stop');
  near(b.r, -1, 1e-12, 'B : R = −1 sans frais');
  const bc = Q.backtest(B, Object.assign({}, P0, { comm: 1.24, slip: 2 })).trades[0];
  near(bc.pnl, -(U4 + 2 - 101) * 2 - 2.24, 1e-9, 'B : perte du stop plus les frais');
  near(bc.r, (-(U4 + 2 - 101) * 2 - 2.24) / ((U4 + 2 - 101) * 2), 1e-9, 'B : R = −1 − c/L');
  // B’ — stop et objectif dans la même barre : le stop est compté (pire cas)
  const B2 = base().concat([bar(4, 102, 104, 101, 101), bar(5, 101, 105, 99, 100)]);
  ok(Q.backtest(B2, P0).trades[0].fin === 'stop', 'B’ : stop et objectif dans la même barre, stop compté');
  // B’’ — ouverture au-delà du stop : remplissage à l’ouverture
  const B3 = base().concat([bar(4, 102, 104, 101, 101), bar(5, 106, 107, 105.5, 106)]);
  near(Q.backtest(B3, P0).trades[0].exit, 106, 1e-12, 'B’’ : stop sauté, remplissage à l’ouverture 106');

  // C — sortie forcée : fenêtre 00:00–00:06 (0,1 h). b5 (00:05) est la dernière barre de la fenêtre,
  // ni stop (haut 101,5) ni objectif (bas 100,6 > 100,4) : sortie à sa clôture 101,2, soit −0,2 pt.
  const Cb = base().concat([bar(4, 102, 104, 101, 101), bar(5, 101, 101.5, 100.6, 101.2), flat(6, 101.2), bar(7, 101.2, 101.2, 95, 96)]);
  const c = Q.backtest(Cb, Object.assign({}, P0, { to: 0.1 })).trades;
  ok(c.length === 1 && c[0].fin === 'cloche' && c[0].j === 5, 'C : sortie forcée à la dernière barre de la fenêtre');
  near(c[0].pts, -0.2, 1e-9, 'C : −0,2 point');
  ok(Q.backtest(Cb, Object.assign({}, P0, { to: 0.1 })).trades.every(x => x.i <= 5), 'C : aucune entrée hors fenêtre');
  // Fenêtre qui exclut tout : 01:00–02:00 Paris
  ok(Q.backtest(Cb, Object.assign({}, P0, { from: 1, to: 2 })).trades.length === 0, 'fenêtre 01:00–02:00 : aucun trade');
  // Fenêtre qui passe minuit : 23:00–00:10 Paris
  ok(Q.backtest(Cb, Object.assign({}, P0, { from: 23, to: 10 / 60 })).trades.length === 1, 'fenêtre qui passe minuit');

  // D — long en miroir : 102, 98, 102, 98 puis b4 (bas 96, clôture 99) ; prix typique 98, VWAP 99,6.
  // Bande basse 99,6 − √3,84 = 97,6404 : entrée 99, objectif 99,6 touché en b5 (haut 100) : +0,6 pt.
  const D = [flat(0, 102), flat(1, 98), flat(2, 102), flat(3, 98), bar(4, 98, 99, 96, 99), bar(5, 99, 100, 99, 100)];
  const d = Q.backtest(D, P0).trades;
  ok(d.length === 1 && d[0].side === 1, 'D : un long');
  near(d[0].stop, 99.6 - Math.sqrt(3.84) - 2, 1e-12, 'D : stop deux points sous la bande basse');
  near(d[0].exit, 99.6, 1e-12, 'D : sortie à la VWAP');
  near(d[0].pts, 0.6, 1e-9, 'D : +0,6 point');

  // E — au contact, niveaux de la barre précédente (VWAP 100, σ 2, bande haute 102), échauffement 4 min.
  // b4 ouvre à 101 et monte à 103,5 : entrée 102, stop 104. Prix typique b4 = 102,5, VWAP(b4) = 100,5.
  // b5 descend à 99 : sortie 100,5, soit +1,5 point.
  const E = base().concat([bar(4, 101, 103.5, 101, 103), bar(5, 103, 103, 99, 99.5)]);
  const PE = Object.assign({}, P0, { mode: 'contact', warm: 4 });
  const e = Q.backtest(E, PE).trades;
  ok(e.length === 1 && e[0].side === -1, 'E : un short au contact');
  near(e[0].entry, 102, 1e-12, 'E : entrée sur la bande de la barre précédente');
  near(e[0].stop, 104, 1e-12, 'E : stop 104');
  near(e[0].exit, 100.5, 1e-12, 'E : sortie à la VWAP 100,5');
  near(e[0].pts, 1.5, 1e-9, 'E : +1,5 point');
  // E’ — même barre : le haut 104,5 touche le stop 104 dans la barre d’entrée
  const E2 = base().concat([bar(4, 101, 104.5, 101, 103), bar(5, 103, 103, 99, 99.5)]);
  const e2 = Q.backtest(E2, PE).trades[0];
  ok(e2.fin === 'stop' && e2.j === 4, 'E’ : stoppé dans la barre d’entrée');
  near(e2.pts, -2, 1e-12, 'E’ : −2 points');
  // Sans échauffement, le mode contact prend b2 (bas 98 sur la bande basse 98 de b1)
  const e3 = Q.backtest(E, Object.assign({}, PE, { warm: 0 })).trades;
  ok(e3.length >= 1 && e3[0].i === 2 && e3[0].side === 1, 'contact sans échauffement : long en b2 au contact de 98');

  // Limite par séance
  const many = [];
  for (let k = 0; k < 6; k++) { const o = k * 6; many.push(flat(o, 98), flat(o + 1, 102), flat(o + 2, 98), flat(o + 3, 102), bar(o + 4, 102, 104, 101, 101), bar(o + 5, 101, 101, 100, 100)); }
  const mm = many.map((b, i) => Object.assign({}, b, { t: T0 + i * 60000 }));
  const nAll = Q.backtest(mm, P0).trades.length;
  ok(nAll >= 2, 'série répétée : plusieurs trades (' + nAll + ')');
  ok(Q.backtest(mm, Object.assign({}, P0, { maxPer: 1 })).trades.length === 1, 'un trade par séance au plus');
  const tr = Q.backtest(mm, P0).trades;
  ok(tr.every((x, i) => i === 0 || x.i > tr[i - 1].j), 'un trade à la fois');
}

section('Statistiques');
{
  const s = Q.stats([10, -5, -5, 20, -10].map(p => ({ pnl: p, r: p / 10 })));
  ok(s.n === 5 && s.wins === 2 && s.losses === 3, 'compte');
  near(s.winRate, 0.4, 1e-12, 'réussite 2/5');
  near(s.exp, 2, 1e-12, 'espérance 10/5');
  near(s.expR, 0.2, 1e-12, 'espérance en R');
  near(s.pf, 1.5, 1e-12, 'facteur de profit 30/20');
  near(s.maxDD, 10, 1e-12, 'creux maximal 10');
  near(s.sd, Math.sqrt(630 / 4), 1e-12, 'écart-type n − 1');
  near(s.sharpe, 2 / Math.sqrt(157.5), 1e-12, 'Sharpe par trade');
  ok(s.lossStreak === 2, 'plus longue série de pertes 2');
  const m = Q.moments([1, 2, 3, 10]);
  near(m.skew, 45 / Math.pow(12.5, 1.5), 1e-12, 'asymétrie de population : m₃ = 45, m₂ = 12,5');
}

section('Lecture des CSV');
{
  const tv = 'time,open,high,low,close,Volume\n' + (T0 / 1000) + ',100,101,99,100.5,12\n' + (T0 / 1000 + 60) + ',100.5,102,100,101.75,8\n';
  const a = Q.parseCsv(tv);
  ok(!a.error && a.n === 2 && a.sepName === 'virgule' && a.timeKind === 's', 'TradingView : secondes Unix, virgule');
  ok(a.bars[0].t === T0 && a.bars[1].c === 101.75 && a.bars[0].v === 12, 'TradingView : valeurs');
  const ms = Q.parseCsv('timestamp;open;high;low;close;volume\n' + T0 + ';100,5;101;99;100,25;3\n');
  ok(ms.n === 1 && ms.bars[0].t === T0 && ms.bars[0].o === 100.5 && ms.bars[0].c === 100.25 && ms.timeKind === 'ms', 'millisecondes, point-virgule et virgule décimale');
  const iso = Q.parseCsv('Date;Open;High;Low;Close;Volume\n2026-01-05 18:00:00;20 125,50;20 130;20 120;20 128,25;7\n', { tz: 'America/New_York' });
  ok(iso.n === 1 && iso.bars[0].t === T0 && iso.bars[0].o === 20125.5 && iso.timeKind === 'local', 'ISO sans fuseau lu à New York, milliers espacés');
  const isoP = Q.parseCsv('time,open,high,low,close\n2026-01-06T00:00:00,1,2,0.5,1.5\n', { tz: 'Europe/Paris' });
  ok(isoP.bars[0].t === T0, 'fuseau du fichier : Paris');
  const off = Q.parseCsv('time,open,high,low,close,volume\n2026-01-05T18:00:00-05:00,1,2,0.5,1.5,1\n2026-01-05T23:01:00Z,1,2,0.5,1.5,1\n', { tz: 'Europe/Paris' });
  ok(off.bars[0].t === T0 && off.bars[1].t === T0 + 60000 && off.timeKind === 'iso', 'ISO avec fuseau : le réglage est ignoré');
  const tab = Q.parseCsv('Date\tTime\tOpen\tHigh\tLow\tLast\tVolume\n13/01/2026\t18:00\t1\t2\t0.5\t1.5\t4\n13/01/2026\t18:01\t1.5\t2\t1\t1.75\t2\n', { tz: 'America/New_York' });
  ok(tab.n === 2 && tab.sepName === 'tabulation' && tab.bars[0].t === Date.UTC(2026, 0, 13, 23, 0) && tab.bars[1].c === 1.75, 'tabulation, date et heure séparées, jour/mois, « last »');
  const us = Q.parseCsv('date,time,open,high,low,close\n01/13/2026,18:00,1,2,0.5,1.5\n', { tz: 'America/New_York' });
  ok(us.bars[0].t === Date.UTC(2026, 0, 13, 23, 0), 'mois/jour reconnu (13 > 12)');
  const amb = Q.parseCsv('date,time,open,high,low,close\n02/01/2026,18:00,1,2,0.5,1.5\n', { tz: 'America/New_York' });
  ok(amb.warnings.some(w => /ambigu/.test(w)) && amb.bars[0].t === Date.UTC(2026, 0, 2, 23, 0), 'date ambiguë : lue jour/mois, avec un avertissement');
  const pack = Q.parseCsv('time;open;high;low;close;volume\n20260105 180000;1;2;0,5;1,5;1\n', { tz: 'America/New_York' });
  ok(pack.bars[0].t === T0, 'format compact AAAAMMJJ HHMMSS');
  const nohead = Q.parseCsv((T0 / 1000) + ',1,2,0.5,1.5,3\n' + (T0 / 1000 + 60) + ',1.5,2,1,1.75,2\n');
  ok(!nohead.header && nohead.n === 2 && nohead.bars[1].v === 2, 'sans en-tête : time, open, high, low, close, volume');
  const bad = Q.parseCsv('time,open,high,low,close\n' + (T0 / 1000) + ',1,2,0.5,1.5\nnimportequoi,1,2,3,4\n' + (T0 / 1000 - 60) + ',1,1,1,1\n' + (T0 / 1000) + ',9,9,9,9\n');
  ok(bad.skipped === 1 && bad.firstSkip.line === 3, 'ligne illisible ignorée et signalée');
  ok(bad.n === 2 && bad.bars[0].t === T0 - 60000 && bad.bars[1].o === 9 && bad.dup === 1, 'tri chronologique, doublon : la dernière ligne gagne');
  const fix = Q.parseCsv('time,open,high,low,close\n' + (T0 / 1000) + ',10,9,8,11\n');
  ok(fix.bars[0].h === 11 && fix.fixed === 1, 'haut corrigé pour contenir la clôture');
  ok(Q.parseCsv('').error && Q.parseCsv('a b c\n1 2 3').error, 'fichier vide ou sans séparateur : erreur');
  ok(/open, high, low, close/.test(Q.parseCsv('foo,bar\nx,y\n').error), 'colonnes introuvables : erreur claire');
  const step = Q.parseCsv('time,open,high,low,close\n' + (T0 / 1000) + ',1,1,1,1\n' + (T0 / 1000 + 300) + ',1,1,1,1\n' + (T0 / 1000 + 600) + ',1,1,1,1\n');
  ok(step.stepMin === 5 && step.warnings.some(w => /une minute/.test(w)), 'barres de 5 min : avertissement');
  ok(Q.parseCsv(tv.replace(/,12\n/, ',0\n').replace(/,8\n/, ',0\n')).warnings.some(w => /volume/i.test(w)), 'sans volume : avertissement');
  ok(Q.wallToUtc(2026, 3, 8, 18, 0, 'America/New_York') === Date.UTC(2026, 2, 8, 22, 0), 'heure d’été le jour du changement');
}

section('Données synthétiques');
{
  const s = Q.synth({ seed: 3, sigma: 4, days: 3 });
  ok(s.length === 3 * 1380, '1 380 barres par séance');
  ok(s[0].t === Date.UTC(2026, 0, 4, 23, 0), 'première barre : dimanche 4 janvier 2026, 18:00 New York');
  ok(s[1380].t === Date.UTC(2026, 0, 5, 23, 0), 'deuxième séance : lundi 18:00 New York');
  ok(s.every((b, i) => b.h >= Math.max(b.o, b.c) && b.l <= Math.min(b.o, b.c) && (i === 0 || b.o === s[i - 1].c)), 'barres cohérentes, ouverture = clôture précédente');
  ok(s.every(b => Math.abs(b.c * 4 - Math.round(b.c * 4)) < 1e-9), 'prix au tick de 0,25');
  ok(JSON.stringify(Q.synth({ seed: 3, sigma: 4, days: 3 })) === JSON.stringify(s), 'même graine, mêmes barres');
  ok(Q.synth({ seed: 4, sigma: 4, days: 1 })[100].c !== Q.synth({ seed: 3, sigma: 4, days: 1 })[100].c, 'autre graine, autres barres');
  const ch = []; for (let i = 1; i < s.length; i++) ch.push(s[i].c - s[i - 1].c);
  const sd = Math.sqrt(ch.reduce((a, x) => a + x * x, 0) / ch.length);
  near(sd, 4, 0.06, 'σ par minute ≈ 4 points');
  const fri = Q.synth({ seed: 1, sigma: 1, days: 6 });
  ok(fri[5 * 1380].t === Date.UTC(2026, 0, 11, 23, 0), 'le week-end est sauté : la sixième séance s’ouvre le dimanche 11');
}

section('Sans dérive, la stratégie rend −c (ALP nº 3 : −c/a), et les lois nulles aussi');
{
  const bars = Q.synth({ seed: 21, sigma: 4, days: 40 });
  const p = Object.assign({}, P0, { k: 2, stop: 5, warm: 30, from: 0, to: 23.99, comm: 1.24, slip: 2 });
  const r = Q.backtest(bars, p, 40, 5), st = r.stats;
  ok(st.n > 100, 'assez de trades (' + st.n + ')');
  const se = st.sd / Math.sqrt(st.n);
  ok(Math.abs(st.exp + 2.24) < 4 * se, 'espérance ' + st.exp.toFixed(3) + ' $ à moins de 4 erreurs types (' + se.toFixed(3) + ') de −2,24 $');
  const nl = r.nulls;
  ok(nl.rand1.means.length === 40 && nl.rand2.means.length === 40, '40 tirages par loi nulle');
  ok(nl.rand1.first.length === st.n && nl.rand2.first.length === st.n, 'chaque tirage rejoue tous les trades');
  ok(Math.abs(nl.rand1.mean + 2.24) < 4 * se, 'sens au hasard : ' + nl.rand1.mean.toFixed(3) + ' ≈ −2,24 $');
  ok(nl.rand2.mean < 0, 'minutes au hasard : espérance négative (' + nl.rand2.mean.toFixed(3) + ')');
  ok(nl.rand1.lo <= nl.rand1.mean && nl.rand1.mean <= nl.rand1.hi, 'bande à 90 % autour de la moyenne');
  ok(nl.rand2.p > 0 && nl.rand2.p <= 1 && nl.rand1.p > 0 && nl.rand1.p <= 1, 'p-valeurs dans ]0, 1]');
  const r2 = Q.backtest(bars, p, 40, 5);
  ok(JSON.stringify(r2.nulls.rand1.means) === JSON.stringify(nl.rand1.means), 'même graine, mêmes tirages nuls');
  const r3 = Q.backtest(bars, p, 40, 6);
  ok(JSON.stringify(r3.nulls.rand1.means) !== JSON.stringify(nl.rand1.means), 'autre graine, autres tirages');
  ok(r.fins.objectif + r.fins.stop + r.fins.cloche === st.n, 'les fins couvrent tous les trades');
  ok(r.hours.reduce((a, x) => a + x.n, 0) === st.n, 'la répartition horaire couvre tous les trades');
  // Trades longs ET courts
  ok(r.trades.some(t => t.side > 0) && r.trades.some(t => t.side < 0), 'des longs et des shorts');
  ok(r.trades.every(t => (t.side < 0 ? t.entry > t.ref : t.entry < t.ref)), 'short au-dessus de la VWAP, long en dessous');
  // Balayage et CSCV sur du bruit
  const sw = Q.sweep(bars, p, Q.K_GRID, Q.stopGrid(5, 0.25));
  ok(sw.grid.length === 16 && sw.sessions === 40, 'balayage 4 × 4 sur 40 séances');
  ok(!sw.cscv.error && sw.cscv.splits === 70, 'CSCV : C(8, 4) = 70 partitions');
  ok(sw.cscv.pbo >= 0 && sw.cscv.pbo <= 1, 'PBO dans [0, 1] (' + sw.cscv.pbo.toFixed(2) + ')');
  ok(sw.grid.every(g => g.n === 0 || isFinite(g.exp)), 'espérances finies');
  const g2 = sw.grid.find(g => g.k === 2 && g.stop === 5);
  ok(g2 && g2.n === st.n && Math.abs(g2.exp - st.exp) < 1e-9, 'la case du réglage courant reproduit le backtest');
  ok(Q.sweep(bars.slice(0, 1380 * 5), p, [2], [5]).cscv.error, 'moins de huit séances : CSCV refusée');
}

section('CSCV : portage de alp1/overfit.py');
{
  const perf = []; for (let s = 0; s < 6; s++) { const row = []; for (let t = 0; t < 26; t++) row.push(((s * 7919 + t * 104729) % 211) / 10 - 10); perf.push(row); }
  const r = Q.cscv(perf, 8);
  ok(JSON.stringify(r.edges) === JSON.stringify([0, 3, 6, 10, 13, 16, 20, 23, 26]), 'bornes de blocs en arrondi bancaire (6,5 → 6, 19,5 → 20), comme round() en Python');
  near(r.pbo, 0.8571428571428571, 1e-15, 'PBO = Python');
  ok(r.splits === 70, '70 partitions');
  near(r.medianLogit, -1.791759469228055, 1e-12, 'logit médian = Python');
  near(r.degradation, 1.9178806907378336, 1e-12, 'dégradation = Python');
  const perf2 = []; for (let s = 0; s < 5; s++) { const row = []; for (let t = 0; t < 20; t++) row.push(((s * 31 + t * 17) % 23) / 4 - 2.5 + (s === 2 ? 0.3 : 0)); perf2.push(row); }
  const r2 = Q.cscv(perf2, 4);
  near(r2.pbo, 0.8333333333333334, 1e-15, 'PBO, 4 blocs = Python');
  ok(r2.splits === 6, 'C(4, 2) = 6');
  near(r2.medianLogit, -1.151292546497023, 1e-12, 'logit médian, 4 blocs = Python');
  near(r2.degradation, 0.6708333333333334, 1e-12, 'dégradation, 4 blocs = Python');
  ok(r.omegas.length === 70 && r.omegas.every(w => w > 0 && w < 1), 'rangs relatifs en test : 70 valeurs dans ]0, 1[');
  ok(r.omegas.filter(w => w <= 0.5).length / 70 === r.pbo, 'PBO = part des rangs relatifs sous la médiane');
  const bl = Q.binning([0, 375, 750, 375, 1125]);
  ok(bl.lattice && bl.nb === 4 && bl.lo === -187.5 && bl.hi === 1312.5, 'classes alignées sur un réseau de pas 375');
  const bl2 = Q.binning(Array.from({ length: 400 }, (_, i) => i * 10), 36);
  ok(bl2.lattice && bl2.nb <= 36 && Math.abs((bl2.hi - bl2.lo) / bl2.nb / 10 - Math.round((bl2.hi - bl2.lo) / bl2.nb / 10)) < 1e-9, 'réseau trop fin : classes regroupées par multiples entiers du pas');
  ok(!Q.binning([0.1, 0.37, 0.52, 0.9, 1.3]).lattice, 'valeurs continues : classes égales');
  const mix = []; for (let i = 0; i < 2000; i++) mix.push(375 * (i % 30)); for (let i = 0; i < 100; i++) mix.push(137.3 * i + 0.11);
  const bm = Q.binning(mix, 36), wm = (bm.hi - bm.lo) / bm.nb, cm = new Array(bm.nb).fill(0); mix.forEach(x => cm[Math.min(bm.nb - 1, Math.floor((x - bm.lo) / wm))]++);
  ok(!bm.lattice && cm.slice(1, -1).every(c => c > 0), 'réseau rompu : aucune classe vide au milieu (' + bm.nb + ' classes)');
  const fk = v => (v / 1000).toFixed(1) + ' k$', tk = Q.axisTicks(47700, 58900, 334, fk);
  ok(tk.length >= 2 && (tk[1] - tk[0]) / 11200 * 334 >= 7 * 6.2 + 12, 'graduations espacées d’au moins une étiquette (' + tk.length + ')');
  ok(Q.cscv([[1, 2, 3]], 2).error && Q.cscv([[1, 2], [3, 4]], 3).error && Q.cscv([[1], [2]], 2).error, 'cas refusés comme en Python');
}

section('Sharpe probabiliste et déflaté (Bailey et López de Prado)');
{
  near(Q.psr(0.1, 100, 0, -0.5, 2.0), 0.8330822773316748, 2e-6, 'PSR = pathstats.probabilistic_sharpe');
  near(Q.expectedMaxSharpe(16, 0.05), 0.09002271199792265, 1e-8, 'SR₀ = overfit.expected_max_sharpe(16, 0,05)');
  near(Q.dsr(0.12, 200, 16, -0.3, 1.2, 0.05).dsr, 0.6602620812115645, 2e-6, 'DSR = overfit.deflated_sharpe');
  ok(Q.expectedMaxSharpe(1, 1) === 0, 'un seul essai : rien à déflater');
  near(Q.psr(0, 50, 0, 0, 0), 0.5, 1e-7, 'PSR d’un Sharpe nul : ½');
}

section('Monte-Carlo');
{
  const base = { mode: 'param', rr: 2, disp: 0, risk: 100, cost: 0, n: 50, paths: 200, capital: 10000, ruin: 1000, seed: 9 };
  const win = Q.monteCarlo(Object.assign({}, base, { p: 1 }));
  ok(win.alt.finals.every(x => x === 20000) && win.alt.ruin === 0 && win.alt.dd95 === 0 && win.alt.streak95 === 0, 'p = 1 : +2 R à chaque trade, 20 000 $, ni creux ni série');
  const lose = Q.monteCarlo(Object.assign({}, base, { p: 0 }));
  ok(lose.alt.ruin === 1 && lose.alt.finals.every(x => x === 9000), 'p = 0 : ruine à −1 000 $, absorbante');
  ok(lose.alt.dd50 === 1000 && lose.alt.streak50 === 10, 'p = 0 : creux 1 000 $, dix pertes avant l’arrêt');
  const noRuin = Q.monteCarlo(Object.assign({}, base, { p: 0, ruin: 0 }));
  ok(noRuin.alt.finals.every(x => x === 5000) && noRuin.alt.ruin === 0, 'sans seuil de ruine : 50 pertes, 5 000 $');
  near(Q.monteCarlo(Object.assign({}, base, { rr: 1.5, cost: 10, p: 0.5 })).pEq, 0.44, 1e-12, 'taux d’équilibre (1 + 0,1)/(1 + 1,5) = 0,44');
  near(Q.equilibrium(1.5, 0.1), 0.44, 1e-12, 'Q.equilibrium');
  near(Q.expectancyR(0.45, 1.5, 0.1), 0.025, 1e-12, 'espérance 0,45·1,5 − 0,55 − 0,1');
  const big = Q.monteCarlo({ mode: 'param', p: 0.45, rr: 1.5, disp: 0.4, risk: 100, cost: 10, n: 100, paths: 10000, capital: 50000, ruin: 0, seed: 1 });
  const sdT = 100 * 2.5 * Math.sqrt(0.45 * 0.55) * 1.2, se = sdT * Math.sqrt(100) / Math.sqrt(10000);
  ok(Math.abs(big.nul.meanFinal - 50000) < 5 * se, 'loi nulle : capital final moyen ≈ départ (' + big.nul.meanFinal.toFixed(1) + ')');
  ok(Math.abs(big.alt.meanFinal - (50000 + 100 * 2.5)) < 5 * se, 'hypothèse : +2,50 $ par trade (' + (big.alt.meanFinal - 50000).toFixed(1) + ')');
  ok(big.alt.finals.length === 10000 && big.cps.length === 61 && big.cps[60] === 100, '10 000 trajectoires, 61 points d’éventail');
  ok(big.alt.q.p05.every((v, i) => v <= big.alt.q.p25[i] && big.alt.q.p25[i] <= big.alt.q.p50[i] && big.alt.q.p50[i] <= big.alt.q.p75[i] && big.alt.q.p75[i] <= big.alt.q.p95[i]), 'quantiles ordonnés');
  ok(big.alt.q.p50[0] === 50000 && big.alt.paths.length === 14 && big.alt.paths[0].length === 61, 'départ commun, quatorze trajectoires témoins');
  const again = Q.monteCarlo({ mode: 'param', p: 0.45, rr: 1.5, disp: 0.4, risk: 100, cost: 10, n: 100, paths: 10000, capital: 50000, ruin: 0, seed: 1 });
  ok(again.alt.finals[1234] === big.alt.finals[1234] && again.nul.dd95 === big.nul.dd95, 'même graine, mêmes trajectoires');
  // gain lognormal de moyenne R:R : la moyenne des gagnants reste 1,5 R
  const w = Q.monteCarlo({ mode: 'param', p: 1, rr: 1.5, disp: 0.8, risk: 1, cost: 0, n: 1, paths: 20000, capital: 0, ruin: 0, seed: 4 });
  near(w.alt.meanFinal, 1.5, 0.03, 'variabilité du gain : moyenne conservée');
  // Bootstrap
  const smp = [100, -50, -50, 30];
  const bt = Q.monteCarlo({ mode: 'boot', sample: smp, n: 200, paths: 10000, capital: 0, ruin: 0, seed: 2 });
  near(bt.mu, 7.5, 1e-12, 'moyenne de l’échantillon');
  const sdB = Math.sqrt(smp.reduce((a, x) => a + (x - 7.5) * (x - 7.5), 0) / 4), seB = sdB * Math.sqrt(200) / 100;
  ok(Math.abs(bt.alt.meanFinal - 1500) < 5 * seB, 'bootstrap : 200 × 7,5 = 1 500 (' + bt.alt.meanFinal.toFixed(1) + ')');
  ok(Math.abs(bt.nul.meanFinal) < 5 * seB, 'bootstrap recentré : moyenne nulle (' + bt.nul.meanFinal.toFixed(1) + ')');
  // série de pertes : échantillon tout négatif
  const neg = Q.monteCarlo({ mode: 'boot', sample: [-1, -2], n: 30, paths: 50, capital: 0, ruin: 0, seed: 2 });
  ok(neg.alt.streak50 === 30 && neg.alt.pLoss === 1, 'tout perd : série de 30, perte certaine');
}

section('Mur d’échantillon (ALP nº 3, huitième partie)');
{
  ok(Q.route1(0.10, 0.05, 0.80) === 619, 'route 1 : 619 décisions pour un Sharpe de 0,10');
  ok(Math.round(Q.route2(0.10, 16)) === 555, 'route 2 : 555 décisions à 16 configurations');
  const w = Q.wall(0.10, 16, 0.05, 0.80);
  ok(w.n === 619 && !w.taxe, 'la plus exigeante lie : 619');
  // Table 14, colonnes « Route 1 » et « Route 2 »
  [[0.05, 2474, 2218], [0.075, 1100, 986], [0.10, 619, 555], [0.15, 275, 246]].forEach(([sr, a, b]) => {
    ok(Q.route1(sr, 0.05, 0.8) === a, 'table 14, route 1 à ' + sr + ' : ' + a);
    ok(Math.round(Q.route2(sr, 16)) === b, 'table 14, route 2 à ' + sr + ' : ' + b);
  });
  near(Q.zSum(0.05, 0.8), 2.486475, 1e-6, 'K = z₀,₉₅ + z₀,₈₀ ≈ 2,49');
  near(Math.sqrt(2 * Math.log(16)), 2.3548, 1e-4, 'K = √(2 ln 16) ≈ 2,35');
  const x = Q.configsCrossing(0.05, 0.8);
  ok(x > 22 && x < 23, 'la taxe passe devant au-delà de 22 configurations (' + x.toFixed(2) + ')');
  ok(Q.route2(0.1, 1) === 0, 'une seule configuration : taxe nulle');
  ok(Q.wall(0.10, 64, 0.05, 0.8).taxe, 'à 64 configurations, la taxe lie');
  near(619 / (2 * Q.SESSIONS), 1.228, 1e-3, '619 décisions ≈ 1,2 an à deux par jour');
  ok(Q.route1(0, 0.05, 0.8) === Infinity && Q.route1(-0.1, 0.05, 0.8) === Infinity, 'Sharpe nul ou négatif : mur infini');
  const txt = fs.readFileSync(require('./harness').ALP3 + '/p08.txt', 'utf8');
  ok(txt.includes('| 0,100 | 619 | 555 | 1,1 an | 0,7 an'), 'p08.txt : la ligne 0,100 de la table 14');
  ok(txt.includes('619 décisions, soit 1,2 an à deux décisions par jour'), 'p08.txt : 1,2 an à deux décisions par jour');
  ok(txt.includes('À 16 configurations ces deux constantes valent 2,49 et 2,35'), 'p08.txt : les deux constantes');
  const p11 = fs.readFileSync(require('./harness').ALP3 + '/p11.txt', 'utf8');
  ok(p11.includes('À dérive nulle, les quatre droites valent exactement −c/L'), 'p11.txt : −c/L cité mot pour mot');
  const p14 = fs.readFileSync(require('./harness').ALP3 + '/p14.txt', 'utf8');
  ok(p14.includes('E[R] = −c/a') && p14.includes('quelle que soit la loi des incréments'), 'p14.txt : −c/a quelle que soit la loi');
  const src = fs.readFileSync(path.join(__dirname, '..', 'src', 'desks', 'quant.js'), 'utf8');
  ok(src.includes('« À dérive nulle, les quatre droites valent exactement −c/L »') && src.includes('« E[R] = −c/a, quelle que soit la loi des incréments »'), 'les citations du desk sont celles du texte');
}

section('Wilson, taux d’équilibre, journal');
{
  const wl = Q.wilson(6, 16);
  near(wl.lo, 0.18481232558863642, 1e-8, 'Wilson borne basse (6/16)');
  near(wl.hi, 0.6135895945449727, 1e-8, 'Wilson borne haute (6/16)');
  ok(isNaN(Q.wilson(0, 0).p), 'Wilson sans trade');
  near(Q.breakEven(150, -100), 0.4, 1e-12, 'équilibre 100/(150 + 100)');
  ok(isNaN(Q.breakEven(150, 0)), 'équilibre sans perte : indéfini');
  const rows = [
    { kind: 'pris', status: 'clos', pnl: 120, r: 0.8, at: 3 }, { kind: 'pris', status: 'ouvert', pnl: 50, at: 2 },
    { kind: 'refus', stage: 'macro', at: 1 }, { kind: 'pris', status: 'clos', pnl: -150, at: 1, closedAt: 1.5 }
  ];
  const j = Q.fromJournal(rows, 150);
  ok(j.length === 2 && j[0].pnl === -150 && j[0].r === -1 && j[1].r === 0.8, 'journal : seuls les trades pris et clos, R recalculé si absent');
  ok(JSON.stringify(Q.stopGrid(5, 0.25)) === '[2.5,5,7.5,10]' && JSON.stringify(Q.stopGrid(3, 0.25)) === '[1.5,3,4.5,6]', 'grille de stops autour du réglage');
}

section('Enregistrement du desk');
{
  const d = T.desks().find(x => x.id === 'quant');
  ok(d && d.label === 'Quant & backtest' && d.glyph === 'Q' && d.group === 'Recherche' && d.order === 50, 'id, libellé, glyphe, groupe, rang');
  ok(d && d.tabs.map(t => t.id).join(',') === 'montecarlo,backtest,robustesse,echantillon', 'quatre onglets');
  ok(Object.values(Q.KEYS).every(k => /^quant:/.test(k)), 'clés préfixées quant:');
  ok(Q.KEYS.last === 'quant:lastBacktest', 'clé lue par le desk Métriques');
}

console.log((fails ? 'ÉCHEC' : 'OK') + ' — ' + passes + ' réussis, ' + fails + ' échoués');
process.exit(fails ? 1 : 0);
