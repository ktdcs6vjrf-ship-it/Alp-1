// Tests du desk NQ : node test/nq.test.js (sortie non nulle si échec).
const fs = require('fs'), path = require('path');
const { T, lib: L } = require('./harness')('nq');
const ALP = require('./harness').ALP3 + '';
let n = 0, bad = 0;
function ok(cond, msg) { n++; if (!cond) { bad++; console.error('ÉCHEC : ' + msg); } }
function near(a, b, tol, msg) { ok(Math.abs(a - b) <= tol, msg + ' (obtenu ' + a + ', attendu ' + b + ')'); }
function eq(a, b, msg) { ok(JSON.stringify(a) === JSON.stringify(b), msg + ' (obtenu ' + JSON.stringify(a) + ', attendu ' + JSON.stringify(b) + ')'); }
const codes = r => r.niveaux.map(x => x.code + '@' + x.v);

/* ---------------- Lecture : nettoyage, vocabulaire ---------------- */
eq(L.cleanNum('29,280.00'), '29280.00', 'séparateur de milliers retiré');
eq(L.num('** 29,280.00'), 29280, 'gras et milliers retirés');
eq(L.num('-1,234.50'), -1234.5, 'le tiret reste : un niveau négatif reste négatif');
eq(L.num('−15'), -15, 'le vrai signe moins vaut le tiret');
eq(L.num('29 250,5'), 29250.5, 'virgule décimale à la française');
ok(isNaN(L.num('0 dte')), '« 0 dte » ne devient pas 0');
ok(isNaN(L.num('- **flip')), 'une étiquette ne donne pas de nombre');
eq(L.teteNumerique('** 0 dte'), '0', 'préfixe 0'); eq(L.teteNumerique('30 dte'), '30', 'préfixe 30'); eq(L.teteNumerique('plusieurs jours'), '', 'pas de préfixe');
eq(L.codeDe('call wall', '0'), '0CR', 'call wall → CR'); eq(L.codeDe('put wall', '0'), '0PS', 'put wall → PS');
eq(L.codeDe('major wall', '0'), '0GW', 'major wall → GW avant wall'); eq(L.codeDe('gamma flip', ''), 'HVL', 'flip → HVL');
eq(L.codeDe('max pain', '1'), '1MP', 'max pain → MP'); eq(L.codeDe('resistance macro', '30'), 'RM', 'RM exempt de préfixe, avant resistance');
eq(L.codeDe('resistance', '30'), '30CR', 'resistance → CR'); eq(L.codeDe('support', '30'), '30PS', 'support → PS');
eq(L.codeDe('R1', '30'), '30R1', 'R1 gardé tel quel, préfixé'); eq(L.codeDe('0CR', '30'), '0CR', 'un code déjà préfixé garde le sien');
eq(L.codeDe('', '0'), '', 'pas de code sans étiquette');

/* ---------------- Collage 1 : export markdown 0 dte, avec bloc CSV ---------------- */
const EXPORT = [
  '# $NDX watchlist · 0 dte', '## Context', '- **symbol:** NDX', '- **horizon:** 0 dte', '- **chain snapshot:** 2026-09-14T14:45:02-04:00', '- **table rows:** 22',
  '## Levels', '- **flip:** 29,280.00', '- **major wall:** 29,290.00', '- **call wall:** 29,250.00', '- **put wall:** 29,250.00', '- **max pain:** 29,175.00',
  '## Data', '```csv', 'expiration,settlement,call_put,strike,0dte_net,0dte_abs', '2026-09-14,PM,C,29200.00,0,0', '2026-09-14,PM,P,29250.00,-207160033.720062,-207160033.720062', '```'].join('\n');
let r = L.parseGex(EXPORT, 29221, 110.47, {});
eq(codes(r), ['0HVL@29280', '0GW@29290', '0CR/0PS@29250', '0MP@29175', '0S1@29200'], 'export 0 dte : cinq zones, codes joints, S1 tiré du CSV');
eq(r.prefixe, '0', 'échéance lue dans horizon'); eq(r.source, 'horizon', 'source horizon');
near(r.med, 29265, 1e-9, 'médiane des zones nommées (moyenne des deux du milieu)');
near(r.ecartSans, 44, 1e-9, 'écart sans base'); near(r.ecartAvec, 154.47, 1e-6, 'écart avec base');
ok(r.appliquee === false && r.baseApp === 0, 'auto : la base n’est pas appliquée à des niveaux déjà proches du prix');
eq(r.nCalc, 1, 'une zone calculée'); eq(r.csv, 2, 'deux strikes au CSV');
ok(!r.niveaux.some(x => x.v === 22 || x.v === 0), 'le compte de lignes (22) et les zéros ne passent pas');
const forced = L.parseGex(EXPORT, 29221, 110.47, { appliquer: 'toujours' });
near(forced.niveaux[0].nq, 29280 + 110.47, 1e-9, 'base forcée : niveau porté sur le NQ');
eq(forced.decision, 'forcee', 'décision forcée');
const sansBase = L.parseGex(EXPORT, 29221, null, {});
eq(sansBase.decision, 'absente', 'sans base : niveaux tels quels'); near(sansBase.niveaux[0].nq, 29280, 0, 'sans base, NQ = collé');

/* ---------------- Collage 2 : deux échéances collées à la suite ---------------- */
const DEUX = EXPORT + '\n' + ['## Context', '- **horizon:** 30 dte', '## Levels', '- **call wall:** 29,600.00', '- **put wall:** 28,900.00', '- **resistance macro:** 29,850.00', '- **R1:** 29,420.00', '- **S1:** 29,050.00'].join('\n');
r = L.parseGex(DEUX, 29221, 110.47, {});
eq(codes(r), ['0HVL@29280', '0GW@29290', '0CR/0PS@29250', '0MP@29175', '30CR@29600', '30PS@28900', 'RM@29850', '30R1@29420', '30S1@29050', '0S1@29200'],
  'deux exports : chacun garde son échéance, RM sans préfixe, S1 calculé avec l’échéance de son CSV');
eq(r.horizons, ['0', '30'], 'deux lignes horizon lues');

/* ---------------- Collage 3 : la liste nue ---------------- */
r = L.parseGex('29250 = 0CR\n29280 : gamma flip\n29175 | max pain\n29290', 29221, null, {});
eq(codes(r), ['0CR@29250', 'HVL@29280', 'MP@29175', '@29290'], 'liste nue : quatre zones, sens de lecture déduit, nombre seul sans code');
ok(r.titres === false, 'liste nue sans titres');

/* ---------------- Collage 4 : niveaux sur l’échelle de l’indice, contexte après les niveaux, refus ---------------- */
const NDX = ['## Levels', '- **call resistance:** 21,400.00', '- **put support:** 20,600.00', '- **gamma flip:** 20,950.00', '- **HVL:** 20,950.00', '- **table rows:** 22', '- 2026 = millésime',
  '## Context', '- **horizon:** 1 dte'].join('\n');
r = L.parseGex(NDX, 21150, 180, { bandePct: 3 });
eq(r.prefixe, '1', 'contexte après les niveaux : la première passe lit l’échéance quand même');
eq(codes(r), ['1CR@21400', '1PS@20600', '1HVL@20950'], 'HVL en double fusionné, préfixe 1');
ok(r.appliquee === true, 'auto : la médiane est plus proche avec la base, elle est appliquée');
near(r.niveaux[2].nq, 21130, 1e-9, 'HVL porté sur le NQ'); near(r.niveaux[2].dist, -20, 1e-9, 'écart au prix');
eq(r.refus.length, 2, 'deux nombres écartés : 22 et 2026');
ok(r.refus.every(x => /fenêtre/.test(x.raison)), 'raison : fenêtre de plausibilité');
const jamais = L.parseGex(NDX, 21150, 180, { appliquer: 'jamais' });
ok(jamais.appliquee === false && jamais.niveaux[0].nq === 21400, 'jamais : niveaux tels quels');

/* ---------------- Collage 5 : tableau seul, échéance lue dans la colonne d’expiration, R/S par valeurs absolues ---------------- */
const CSV = ['expiration,strike,call_put,net_gex', '2026-10-12,21000,C,500', '2026-10-12,21000,P,-450', '2026-10-12,21100,C,800', '2026-10-12,21300,C,-900',
  '2026-10-12,20800,P,-700', '2026-10-12,20900,P,300', '2026-10-12,20900,C,-100'].join('\n');
r = L.parseGex(CSV, 21050, null, { today: '2026-10-09' });
eq(r.prefixe, '3', 'échéance tirée de la colonne d’expiration : 3 jours');
eq(codes(r), ['3R1@21300', '3R2@21100', '3S1@21000', '3S2@20800'], 'R/S : somme des valeurs absolues (21000 vaut 950, pas 50)');
ok(r.niveaux.every(x => x.src === 'calcul'), 'toutes calculées');
const noSec = L.parseGex(CSV, 21050, null, { today: '2026-10-09', secondaires: false });
eq(noSec.n, 0, 'sans secondaires, rien');
const noPrice = L.parseGex(CSV, NaN, null, {});
eq(noPrice.n, 0, 'sans prix, pas de R/S');

/* ---------------- Collage 6 : puce, signe, plafond ---------------- */
r = L.parseGex('- 29250 = call wall\n-12 = test', NaN, null, {});
eq(codes(r), ['CR@29250', 'TEST@-12'], 'une puce n’est pas un signe ; un tiret collé l’est');
const many = Array.from({ length: 25 }, (_, i) => (20000 + i) + ' = z' + i).join('\n');
r = L.parseGex(many, 20010, null, {});
eq(r.n, 20, 'plafond de vingt zones'); eq(r.refus.length, 5, 'les cinq suivantes signalées');

/* ---------------- Largeur d’un niveau : ALP nº 3, partie XIX ---------------- */
const p19 = fs.readFileSync(path.join(ALP, 'p19.txt'), 'utf8');
near(L.DEMI, 1.1774, 1e-4, '√(2 ln 2) = 1,177');
ok(p19.includes('1,177 σ√T'), 'p19 : 1,177 σ√T');
const w2h = L.halfWidth(6000, 0.25, 2 / 24), w1d = L.halfWidth(6000, 0.25, 1);
eq(T.fmt.num(w2h, 1), '26,7', 'demi-largeur à deux heures'); eq(T.fmt.num(w1d, 0), '93', 'demi-largeur à un jour');
ok(p19.includes('26,7 points') && p19.includes('À un jour, 93 points'), 'p19 : 26,7 points et 93 points');
ok(p19.includes('1 219 points') && p19.includes('135 fois le stop élargi') && p19.includes('47,9 %'), 'p19 : bascule 1 219 points, 135 fois, 47,9 %');
ok(p19.includes('2 déplacent l’horloge, une déplace le risque, 2 ne déplacent rien') && p19.includes('0 ne donne le sens'), 'p19 : le décompte, aucun sens');
ok(isNaN(L.halfWidth(6000, NaN, 1)), 'sans volatilité, pas de largeur');

/* ---------------- La case : ALP nº 3, partie XII ---------------- */
const p12 = fs.readFileSync(path.join(ALP, 'p12.txt'), 'utf8');
const cNQ = L.refFriction('NQ'), cMNQ = L.refFriction('MNQ');
near(cNQ, 0.45, 1e-12, 'c de référence NQ'); near(cMNQ, 2.25, 1e-12, 'c de référence MNQ');
eq(T.fmt.num(L.caseMin(cNQ), 1), '8,4', 'case NQ'); eq(T.fmt.num(L.caseMin(cMNQ), 1), '42,2', 'case MNQ');
ok(p12.includes('| E-mini Nasdaq | 4,2 | 8,4 | 13,1 | 0,45') && p12.includes('| Micro Nasdaq | 21,1 | 42,2 | 46,9 | 2,25'), 'p12 : table 24');
ok(p12.includes('3,2 point par heure'), 'p12 : plafond 3,2');
near(L.friction({ commission: 1.24, pointValue: 2, tick: 0.25, slipTicks: 1 }), 0.87, 1e-12, 'friction MNQ à 1,24 $');
near(L.caseMin(0.87), 16.3125, 1e-12, 'case à 0,87 pt');
ok(isNaN(L.friction({ commission: -1, pointValue: 2 })), 'commission négative refusée');

/* ---------------- Taille ---------------- */
let s = L.size({ risk: 150, stop: 20, pointValue: 2, commission: 1.24 });
eq(s.contracts, 3, '150 $ / (20 pt × 2 $ + 1,24 $) = 3 contrats'); near(s.realRisk, 123.72, 1e-9, 'risque réel'); near(s.unused, 26.28, 1e-9, 'non engagé');
s = L.size({ risk: 100, stop: 49.38, pointValue: 2, commission: 1.24 });
eq(s.contracts, 1, 'division exacte : un contrat, pas zéro');
s = L.size({ risk: 150, stop: 60, pointValue: 20, commission: 4 });
eq(s.contracts, 0, 'NQ à 60 pt : zéro contrat'); near(s.perContract, 1204, 1e-9, 'par contrat NQ');
ok(!L.size({ risk: 150, stop: 0, pointValue: 2 }).ok, 'stop nul refusé');
near(L.costR(0.87, 20), -0.0435, 1e-12, '−c/L');
const p11 = fs.readFileSync(path.join(ALP, 'p11.txt'), 'utf8');
ok(p11.includes('À dérive nulle, les quatre droites valent exactement −c/L'), 'p11 : −c/L à dérive nulle');

/* ---------------- Contrat ---------------- */
eq(L.tickValue('NQ'), 5, 'tick NQ = 5 $'); eq(L.tickValue('MNQ'), 0.5, 'tick MNQ = 0,50 $');
eq(L.thirdFriday(2026, 12), 18, 'troisième vendredi de décembre 2026'); eq(L.thirdFriday(2027, 3), 19, 'troisième vendredi de mars 2027');
let fc = L.frontContract(2026, 10, 9); eq(fc.sym, 'Z6', 'échéance en cours le 09/10/2026'); eq(fc.expiry, { y: 2026, mo: 12, d: 18 }, 'expiration');
eq([fc.roll.y, fc.roll.mo, fc.roll.d, fc.roll.wd], [2026, 12, 10, 4], 'roll : un jeudi, huit jours avant');
eq(L.frontContract(2026, 12, 18).sym, 'Z6', 'le jour de l’échéance compte encore'); eq(L.frontContract(2026, 12, 19).sym, 'H7', 'le lendemain : mars 2027');

/* ---------------- Le temps, calculé depuis New York ---------------- */
const U = (y, mo, d, hh, mi) => Date.UTC(y, mo - 1, d, hh, mi);
eq(L.hhmm(L.zonedToUtc(2026, 10, 9, 9, 30, 'America/New_York'), 'Europe/Paris'), '15:30', 'cash 9 h 30 ET = 15 h 30 Paris le 09/10');
eq(L.hhmm(L.zonedToUtc(2026, 10, 27, 9, 30, 'America/New_York'), 'Europe/Paris'), '14:30', 'semaine décalée : 14 h 30 Paris le 27/10');
eq(L.hhmm(L.zonedToUtc(2026, 11, 3, 9, 30, 'America/New_York'), 'Europe/Paris'), '15:30', 'de nouveau 15 h 30 le 03/11');
eq(L.hhmm(L.zonedToUtc(2026, 3, 8, 3, 30, 'America/New_York'), 'America/New_York'), '03:30', 'jour de changement d’heure américain');
eq(L.gap(U(2026, 10, 9, 12, 0)), 6, 'écart 6 h'); eq(L.gap(U(2026, 10, 28, 12, 0)), 5, 'écart 5 h');
eq(L.nextGapChange(U(2026, 10, 9, 12, 0)), { y: 2026, mo: 10, d: 25, gap: 5 }, 'l’écart passe à 5 h le 25/10');
eq(L.classify(U(2026, 10, 9, 14, 0)), 'cash', 'vendredi 10 h ET : cash');
eq(L.classify(U(2026, 10, 9, 21, 30)), 'ferme', 'vendredi 17 h 30 ET : fermé');
eq(L.classify(U(2026, 10, 10, 12, 0)), 'ferme', 'samedi : fermé');
eq(L.classify(U(2026, 10, 7, 21, 30)), 'pause', 'mercredi 17 h 30 ET : pause');
eq(L.classify(U(2026, 10, 7, 5, 0)), 'asie', 'mercredi 1 h ET : Asie'); eq(L.classify(U(2026, 10, 7, 8, 0)), 'europe', 'mercredi 9 h Londres : Europe');
eq(L.classify(U(2026, 10, 7, 20, 30)), 'apres', 'mercredi 16 h 30 ET : après-cash');
eq(L.classify(U(2026, 10, 11, 22, 30)), 'asie', 'dimanche 18 h 30 ET : rouvert');
const fz = L.frieze(U(2026, 10, 7, 10, 0));
eq(fz.segs.map(x => [x.state, x.from, x.to]), [['asie', 0, 540], ['europe', 540, 930], ['cash', 930, 1320], ['apres', 1320, 1380], ['pause', 1380, 1440]], 'frise d’un mercredi en heure de Paris');
const fz2 = L.frieze(U(2026, 10, 28, 10, 0));
eq(fz2.segs.map(x => [x.state, x.from, x.to]), [['asie', 0, 540], ['europe', 540, 870], ['cash', 870, 1260], ['apres', 1260, 1320], ['pause', 1320, 1380], ['asie', 1380, 1440]], 'frise de semaine décalée : le cash glisse d’une heure, Londres non');
eq(L.frieze(U(2026, 10, 10, 10, 0)).segs.map(x => x.state), ['ferme'], 'samedi : fermé toute la journée');
const e1 = L.etat(U(2026, 10, 9, 14, 0));
ok(e1.cash && e1.globex, 'vendredi 10 h ET : cash et Globex ouverts');
eq(e1.nextCash.t, U(2026, 10, 9, 20, 0), 'clôture cash à 16 h ET'); eq(e1.nextGlobex.k, 'weekClose', 'prochaine bascule Globex : fermeture du week-end');
const e2 = L.etat(U(2026, 10, 10, 12, 0));
eq(e2.nextGlobex.t, U(2026, 10, 11, 22, 0), 'samedi : réouverture dimanche 18 h ET'); eq(e2.nextCash.t, U(2026, 10, 12, 13, 30), 'samedi : cash lundi 9 h 30 ET');
const rp = L.reperes(2026, 10, 7);
eq([L.hhmm(rp.reouverture, 'Europe/Paris'), L.hhmm(rp.londres, 'Europe/Paris'), L.hhmm(rp.cashOpen, 'Europe/Paris'), L.hhmm(rp.cashClose, 'Europe/Paris'), L.hhmm(rp.pause, 'Europe/Paris')], ['00:00', '09:00', '15:30', '22:00', '23:00'], 'repères du mercredi');
let w = L.windowCountdown({ h: 8, m: 30, s: 0 }, 0, 9); ok(w.open && w.min === 30, 'fenêtre 0–9 à 8 h 30 : ouverte, 30 min');
w = L.windowCountdown({ h: 10, m: 0, s: 0 }, 0, 9); ok(!w.open && w.min === 840, 'à 10 h : fermée, ouvre dans 14 h');
w = L.windowCountdown({ h: 23, m: 0, s: 0 }, 22, 2); ok(w.open && w.min === 180, 'fenêtre de nuit 22–2 à 23 h : 3 h');
w = L.windowCountdown({ h: 5, m: 0, s: 0 }, 3, 3); ok(!w.open && isNaN(w.min), 'fenêtre vide');
eq(L.fmtCount(3 * 3600e3 + 12 * 60e3), '3 h 12', 'compte à rebours en heures'); eq(L.fmtCount(14 * 60e3 + 5e3), '14 min 05 s', 'en minutes');
eq(L.fmtCount(49 * 3600e3), '2 j 01 h', 'en jours'); eq(L.fmtCount(4e3), '4 s', 'en secondes');
eq(L.fmtHour(15.5), '15:30', 'heure décimale');
near(L.daysToExpiry(U(2026, 10, 9, 14, 0), '0'), 0.25, 1e-9, '0DTE : six heures avant 16 h ET');
near(L.daysToExpiry(U(2026, 10, 9, 14, 0), '1'), 3.25, 1e-9, '1DTE un vendredi : lundi 16 h ET');
eq(L.hhmm(L.captureAt('2026-10-09', '21:12'), 'Europe/Paris'), '21:12', 'capture en heure de Paris');

/* ---------------- Biais et journal ---------------- */
ok(L.biasComplete({ bias: 'long', checks: { structure: true, niveaux: true, regime: true } }), 'biais complet');
ok(!L.biasComplete({ bias: 'long', checks: { structure: true, niveaux: true } }), 'biais incomplet');
ok(!L.biasComplete({ bias: null, checks: { structure: true, niveaux: true, regime: true } }), 'biais absent');
eq(L.biasToday({ date: '2026-10-08', bias: 'short' }, '2026-10-09').bias, null, 'biais de la veille ignoré');
const rows = [{ kind: 'pris', at: 0, closedAt: 600000, instrument: 'MNQ' }, { kind: 'pris', at: 0, closedAt: 1200000 }, { kind: 'refus', at: 0, closedAt: 1 }, { kind: 'pris', at: 0, closedAt: 60000, instrument: 'NQ' }];
eq(L.holdTimes(rows, 'MNQ', 'MNQ'), [10, 20], 'durées MNQ'); eq(L.holdTimes(rows, 'NQ', 'MNQ'), [1], 'durées NQ');
eq(L.nomDe('0CR/0PS', 'robot'), 'call resistance / put support', 'noms joints'); eq(L.nomDe('0R1', 'calcul'), 'tirée du CSV', 'nom d’une zone calculée');
eq(L.nomDe('30S1', 'robot'), 'support 1', 'S1 du robot'); eq(L.nomDe('', 'robot'), 'sans nom', 'zone sans code');

console.log(n + ' tests, ' + bad + ' échec' + (bad > 1 ? 's' : ''));
process.exit(bad ? 1 : 0);
