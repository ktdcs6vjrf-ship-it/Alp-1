// Batterie de scénarios : chaque issue attendue est calculée à la main AVANT
// l'exécution (voir les commentaires). Lancer : node scenarios.mjs
import { lancer, seance, paris, MIN } from './banc.mjs';
import fs from 'node:fs';

let ok = 0, ko = 0;
const echecs = [];
function verifie(nom, cond, detail = '') {
  if (cond) { ok++; console.log('  ok   ' + nom); }
  else { ko++; echecs.push(nom); console.log('  ÉCHEC ' + nom + (detail ? '  →  ' + detail : '')); }
}
const marqueurs = r => r.etiquettes.filter(e => e.style === 'style_circle');
const issues = r => marqueurs(r).map(e => e.tooltip.split('\n')[1].split(' — ')[0]);
const cell = (r, debut) => r.cellules.find(c => c.startsWith(debut)) ?? '';
const msgs = r => r.cellules.join('\n');
const tete = (id, extra = '') =>
  `R id=${id} src=TEST fam=GEX inst=NQ cible=NQ date=2026-11-05 collecte=2026-11-06T00:00 dispo=2026-11-06T00:05 dte=0-0 ech=2026-11-06 ${extra}`;
const J = '2026-11-06';

// ── A. Touches et issues (un seul niveau à chaque fois, tolérance 4 ticks = 1 pt) ──
console.log('A. Touches et issues');
{
  // A1 — résistance rejetée. CW 29300, bande [29299, 29301]. Montée de 29250
  // à 29300 entre 00:10 et 00:30 : touche par en dessous vers 00:29 ; puis
  // baisse à 29265 à 00:45 : 29270 (= 29300 − 30) atteint avant 29320.
  const b = seance(J, '00:00', '02:00', [['00:10', 29250], ['00:30', 29300], ['00:45', 29265], ['01:00', 29250]]);
  const r = await lancer(['ALPZ 1', tete('A1'), 'N CW 29300'].join('\n'), b);
  verifie('A1 une seule touche', marqueurs(r).length === 1, JSON.stringify(issues(r)));
  verifie('A1 rejetée', issues(r)[0] === 'rejetée', issues(r)[0]);
  verifie('A1 venue d\'en bas = résistance', (marqueurs(r)[0]?.tooltip ?? '').includes('test de résistance'));
  verifie('A1 comptée en zone simple', cell(r, 'n 1 · rejet 1').length > 0, cell(r, 'n '));
}
{
  // A2 — support cassé. PS 29100 : descente de 29250 (00:10) à 29070 (01:22)
  // sans rebond : 29080 (= 29100 − 20) atteint, 29130 jamais.
  const b = seance(J, '00:00', '02:00', [['00:10', 29250], ['01:22', 29070], ['02:00', 29070]]);
  const r = await lancer(['ALPZ 1', tete('A2'), 'N PS 29100'].join('\n'), b);
  verifie('A2 cassée', issues(r).length === 1 && issues(r)[0] === 'cassée', JSON.stringify(issues(r)));
  verifie('A2 venue d\'en haut = support', (marqueurs(r)[0]?.tooltip ?? '').includes('test de support'));
}
{
  // A3 — ambiguë dans la bougie de touche : ouverture 29110 au-dessus de la
  // bande, plus haut 29140 (≥ 29130), plus bas 29075 (≤ 29080).
  const b = seance(J, '00:00', '01:30', [['00:10', 29200], ['00:40', 29110], ['01:30', 29110]],
    { '00:41': { o: 29110, h: 29140, l: 29075, c: 29100 } });
  const r = await lancer(['ALPZ 1', tete('A3'), 'N PS 29100'].join('\n'), b);
  verifie('A3 ambiguë (bougie de touche)', issues(r)[0] === 'ambiguë', JSON.stringify(issues(r)));
  verifie('A3 motif écrit', (marqueurs(r)[0]?.tooltip ?? '').includes('ordre inconnu'));
}
{
  // A4 — ambiguë sur la bougie SUIVANTE : touche propre à 00:41, puis 00:42
  // atteint 29135 et 29075.
  const b = seance(J, '00:00', '01:30', [['00:10', 29200], ['00:40', 29110], ['01:30', 29110]],
    { '00:41': { o: 29110, h: 29110.25, l: 29100.5, c: 29101 }, '00:42': { o: 29101, h: 29135, l: 29075, c: 29100 } });
  const r = await lancer(['ALPZ 1', tete('A4'), 'N PS 29100'].join('\n'), b);
  verifie('A4 ambiguë (bougie suivante)', issues(r)[0] === 'ambiguë', JSON.stringify(issues(r)));
  verifie('A4 motif « même bougie »', (marqueurs(r)[0]?.tooltip ?? '').includes('même bougie'));
}
{
  // A5 — réaction peut-être AVANT la touche : ouverture 29135, plus haut
  // 29140, touche à 29100.5, clôture 29110 < 29130 → ambiguë. Variante :
  // clôture 29131 ≥ 29130 → la réaction est certaine après la touche.
  const imp = c => ({ '00:41': { o: 29135, h: 29140, l: 29100.5, c } });
  const b1 = seance(J, '00:00', '01:30', [['00:10', 29200], ['00:40', 29135], ['01:30', 29120]], imp(29110));
  const r1 = await lancer(['ALPZ 1', tete('A5'), 'N PS 29100'].join('\n'), b1);
  verifie('A5 réaction douteuse → ambiguë', issues(r1)[0] === 'ambiguë', JSON.stringify(issues(r1)));
  verifie('A5 motif « peut-être avant la touche »', (marqueurs(r1)[0]?.tooltip ?? '').includes('avant la touche'));
  const b2 = seance(J, '00:00', '01:30', [['00:10', 29200], ['00:40', 29135], ['00:41', 29131], ['01:30', 29131]], imp(29131));
  const r2 = await lancer(['ALPZ 1', tete('A5b'), 'N PS 29100'].join('\n'), b2);
  verifie('A5b clôture au-delà → rejetée', issues(r2)[0] === 'rejetée', JSON.stringify(issues(r2)));
}
{
  // A6 — non résolue : touche à 00:41 puis oscillation 29095–29115 pendant
  // plus de 60 minutes (ni 29130 ni 29080).
  const j = [['00:10', 29200], ['00:40', 29110]];
  for (let m = 45; m <= 175; m += 10) j.push([`0${Math.floor(m / 60)}:${String(m % 60).padStart(2, '0')}`, (m / 10) % 2 ? 29095 : 29115]);
  const b = seance(J, '00:00', '03:00', j);
  const r = await lancer(['ALPZ 1', tete('A6'), 'N PS 29100'].join('\n'), b);
  verifie('A6 première touche non résolue', issues(r).at(-1) === 'non résolue', JSON.stringify(issues(r)));
}
{
  // A7 — une touche par excursion, réarmement après sortie ET délai : la
  // bande est longée 6 minutes (une touche), on sort 4 minutes et on revient
  // (délai de 15 min non écoulé → rien), puis on sort 20 minutes et on
  // revient (deuxième touche).
  const b = seance(J, '00:00', '02:30', [['00:10', 29200], ['00:30', 29105], ['00:31', 29101], ['00:37', 29101],
    ['00:39', 29108], ['00:41', 29108], ['00:43', 29101], ['00:45', 29108], ['01:05', 29108], ['01:07', 29101], ['01:09', 29110], ['02:30', 29110]]);
  const r = await lancer(['ALPZ 1', tete('A7'), 'N PS 29100'].join('\n'), b);
  verifie('A7 deux touches exactement', marqueurs(r).length === 2, String(marqueurs(r).length));
}

// ── B. Confluences ──
console.log('B. Confluences');
{
  // CW 0D 29300, CW 1D 29305, HVN 29296 → une zone [29296, 29305], étiquette
  // « CW 0D · 1D · HVN ». Chaîne R1 0D 29400, R1 1D 29407, VAH 29414,
  // IV+1σ 29421 : pas de 7 ≤ 8, mais diamètre 21 > 16 → [29400–29414] + [29421].
  // S2 29000 : secondaire, masqué et listé.
  const t = ['ALPZ 1',
    tete('B0'), 'N CW 29300', 'N R1 29400', 'N S2 29000',
    `R id=B1 src=TEST fam=GEX inst=NQ cible=NQ date=2026-11-05 collecte=2026-11-06T00:00 dispo=2026-11-06T00:05 dte=1-1 ech=2026-11-09`, 'N CW 29305', 'N R1 29407',
    `R id=BV src=TEST fam=VP inst=NQ cible=NQ,MNQ date=2026-11-05 collecte=2026-11-06T00:00 dispo=2026-11-06T00:04 seance=2026-11-05`, 'N HVN 29296', 'N VAH 29414',
    `R id=BI src=TEST fam=IV inst=NQ cible=NQ date=2026-11-05 collecte=2026-11-06T00:01 dispo=2026-11-06T00:05 dte=0-0 ech=2026-11-06`, 'N IV+1 29421',
  ].join('\n');
  const b = seance(J, '00:00', '03:00', [['00:00', 29200], ['03:00', 29210]]);
  const r = await lancer(t, b, { 'Détail des zones': true });
  const noms = r.etiquettes.filter(e => e.style === 'style_label_left' && !e.text.startsWith('-')).map(e => e.text.split('  ◦')[0]);
  verifie('B étiquette « CW 0D · 1D · HVN »', noms.includes('CW 0D · 1D · HVN'), JSON.stringify(noms));
  verifie('B diamètre borné : « R1 0D · 1D · VAH »', noms.includes('R1 0D · 1D · VAH'), JSON.stringify(noms));
  verifie('B diamètre borné : « IV+1σ 0D » seule', noms.includes('IV+1σ 0D'), JSON.stringify(noms));
  const bx = r.boites.map(x => [x.bottom, x.top].join('–'));
  verifie('B boîte exacte 29296–29305', bx.includes('29296–29305'), JSON.stringify(bx));
  verifie('B aucun prix déplacé (traits aux prix source)', [29296, 29300, 29305].every(p => r.lignes.some(l => l.y1 === p)));
  verifie('B secondaire S2 non tracé', !r.lignes.some(l => l.y1 === 29000));
  verifie('B secondaire S2 listé au tableau', cell(r, 'S2 29000.00').length > 0 || msgs(r).includes('S2 29000.00'));
}

// ── C. Saisie invalide et données absentes ──
console.log('C. Saisie invalide, données absentes');
{
  const t = ['ALPZ 1',
    'N CW 29300',                                                   // avant toute ligne R
    tete('C1'), 'N CW 29,300', 'N XX 29300', 'N POC 29300', 'N CW 29310', 'N CW 29320', 'N PS 29100',
    tete('C1'),                                                     // id répété
    'R id=C2 src=TEST fam=GEX inst=NQ cible=NQ date=2026-11-05 collecte=2026-11-06 00:00 dispo=2026-11-06T00:05 dte=0-0 ech=2026-11-06',
    'R id=C3 src=TEST fam=GEX inst=NDX cible=NQ date=2026-11-05 collecte=2026-11-06T00:00 dispo=2026-11-06T00:05 dte=0-0 ech=2026-11-06', 'N GF 29000',
    'R id=C4 src=TEST fam=GEX inst=NDX cible=NQ date=2026-11-05 collecte=2026-11-06T00:00 dispo=2026-11-06T00:05 dte=0-0 ech=2026-11-06',
    'B base=150 fut=NQZ2026:29200@2026-11-05T22:00 idx=NDX:29000@2026-11-05T22:00', 'N GF 29001',
    'R id=C5 src=TEST fam=GEX inst=NQ cible=NQ date=2026-11-05 collecte=2026-11-06T00:10 dispo=2026-11-06T00:05 dte=0-0 ech=2026-11-06', 'N PS 29050',
    'R id=C6 src=TEST fam=GEX inst=NQ cible=NQ date=2026-11-05 collecte=2026-11-06T00:00 dispo=2026-11-06T00:05 dte=0-0 ech=2026-11-05', 'N PS 29060',
    'BLA bla',
  ].join('\n');
  const b = seance(J, '00:00', '01:00', [['00:00', 29200], ['01:00', 29200]]);
  const r = await lancer(t, b, { 'Avertissements affichés': 30 });
  const m = msgs(r);
  verifie('C niveau avant R signalé', m.includes('avant toute ligne R'));
  verifie('C « 29,300 » refusé', m.includes('prix invalide « 29,300 »'));
  verifie('C code inconnu', m.includes('code inconnu « XX »'));
  verifie('C famille incompatible', m.includes('POC appartient à la famille VP'));
  verifie('C conflit signalé', m.includes('conflit') && m.includes('29310'));
  verifie('C conflit : aucun CW tracé', !r.lignes.some(l => [29310, 29320].includes(l.y1)));
  verifie('C le reste du relevé vit : PS 29100 tracé', r.lignes.some(l => l.y1 === 29100));
  verifie('C id répété refusé', m.includes('déjà utilisé'));
  verifie('C date-heure sans T refusée', m.includes('champ illisible « 00:00 »'));
  verifie('C base absente → non tracé', m.includes('base absente') && !r.lignes.some(l => l.y1 === 29000 || l.y1 === 29150));
  verifie('C base ≠ fut − idx → refusé', m.includes('≠ fut − idx') && !r.lignes.some(l => l.y1 === 29151));
  verifie('C dispo avant collecte refusée', m.includes('disponibilité antérieure'));
  verifie('C échéance expirée refusée', m.includes('antérieure au jour de séance'));
  verifie('C ligne inconnue signalée', m.includes('ligne non reconnue'));
  const r2 = await lancer('', b);
  verifie('C texte vide : « Aucun relevé lu »', msgs(r2).includes('Aucun relevé lu'));
  verifie('C texte vide : rien tracé', r2.lignes.length === 0 && r2.boites.length === 0);
  const r3 = await lancer('R id=X src=TEST fam=GEX', b);
  verifie('C sans en-tête ALPZ 1 : zone ignorée', msgs(r3).includes('« ALPZ 1 » absent'));
}

// ── D. Doublons et plages cumulatives ──
console.log('D. Doublons');
{
  // « 0-0 » et « 1-1 » demandés au même créneau rendent la même échéance :
  // D1 (DTE demandé 1, réel 0) est le doublon. D10 (0-10) recouvre l'échéance.
  const t = ['ALPZ 1', tete('D0'), 'N CW 29300', 'N CW 29300',
    `R id=D1 src=TEST fam=GEX inst=NQ cible=NQ date=2026-11-05 collecte=2026-11-06T00:01 dispo=2026-11-06T00:05 dte=1-1 ech=2026-11-06`, 'N CW 29300',
    `R id=D10 src=TEST fam=GEX inst=NQ cible=NQ date=2026-11-05 collecte=2026-11-06T00:02 dispo=2026-11-06T00:05 dte=0-10 ech=2026-11-06,2026-11-13`, 'N CW 29350',
  ].join('\n');
  const b = seance(J, '00:00', '01:00', [['00:00', 29200], ['01:00', 29200]]);
  const r = await lancer(t, b, { 'Avertissements affichés': 30 });
  const m = msgs(r);
  verifie('D niveau en double signalé', m.includes('en double'));
  verifie('D même échéance → D1 doublon', m.includes('« D1 » renvoie la même échéance'));
  verifie('D un seul trait à 29300', r.lignes.filter(l => l.y1 === 29300).length === 1);
  verifie('D plage cumulative écartée', m.includes('« D10 » (plage cumulative 0-10)') && !r.lignes.some(l => l.y1 === 29350));
  const r2 = await lancer(t, b, { 'Garder les plages cumulatives recouvrantes': true });
  verifie('D plage cumulative gardée sur demande', r2.lignes.some(l => l.y1 === 29350));
}

// ── E. Quotas d'objets ──
console.log('E. Quotas');
{
  // 25 jours × 25 niveaux = 625 traits > 470 : le script s'arrête avant le
  // quota de TradingView (qui effacerait les plus anciens sans prévenir).
  const lignes = ['ALPZ 1'];
  const bougies = [];
  let d = new Date(Date.UTC(2026, 8, 1));
  let n = 0;
  while (n < 25) {
    const dw = d.getUTCDay();
    if (dw >= 1 && dw <= 5) {
      const jour = d.toISOString().slice(0, 10);
      lignes.push(`R id=E${n} src=TEST fam=VP inst=NQ cible=NQ date=${jour} collecte=${jour}T00:00 dispo=${jour}T00:05 seance=2026-08-28`);
      for (let k = 0; k < 25; k++) lignes.push(`N HVN ${29000 + k * 20}`);
      bougies.push(...seance(jour, '00:00', '23:00', [['00:00', 29250]]).filter((_, i) => i % 15 === 0));
      n++;
    }
    d = new Date(d.getTime() + 86400000);
  }
  const r = await lancer(lignes.join('\n'), bougies, { 'Jours affichés': 30 });
  verifie('E traits ≤ 470', r.lignes.length <= 470, String(r.lignes.length));
  verifie('E quota signalé au tableau', cell(r, 'Quotas').length > 0 && msgs(r).includes('non dessiné'));
  const dernierJour = new Date(bougies.at(-1).openTime).toISOString().slice(0, 10);
  const premierJour = new Date(bougies[0].openTime).toISOString().slice(0, 10);
  verifie('E le jour le plus récent est dessiné en entier', r.lignes.filter(l => l.x1 === paris(dernierJour, '00:05')).length === 25);
  verifie('E sous quota, c\'est le jour le plus ancien qui manque', !r.lignes.some(l => l.x1 === paris(premierJour, '00:05')));
}

// ── F. Changements d'heure ──
console.log('F. Changements d\'heure');
{
  const t = ['ALPZ 1',
    'R id=F1 src=TEST fam=GEX inst=NQ cible=NQ date=2026-03-27 collecte=2026-03-29T02:30 dispo=2026-03-29T03:10 dte=0-0 ech=2026-03-30', 'N CW 29300',
    'R id=F2 src=TEST fam=GEX inst=NQ cible=NQ date=2026-10-23 collecte=2026-10-25T02:30 dispo=2026-10-25T03:10 dte=0-0 ech=2026-10-26', 'N CW 29300',
    'R id=F3 src=TEST fam=GEX inst=NQ cible=NQ date=2026-10-22 collecte=2026-10-23T00:00 dispo=2026-10-23T00:05 dte=0-0 ech=2026-10-23', 'N CW 29300',
    'R id=F4 src=TEST fam=GEX inst=NQ cible=NQ date=2026-10-23 collecte=2026-10-26T00:00 dispo=2026-10-26T00:05 dte=0-0 ech=2026-10-26', 'N CW 29310',
    'R id=F5 src=TEST fam=GEX inst=NQ cible=NQ date=2026-10-27 collecte=2026-10-28T00:00 dispo=2026-10-28T00:05 dte=0-0 ech=2026-10-28', 'N CW 29320',
  ].join('\n');
  // Le 28 octobre 2026 tombe dans la semaine où Paris est déjà à l'heure
  // d'hiver et New York pas encore : la pause du CME va de 22 h à 23 h à Paris.
  // Aucune bougie entre 22:00 et 23:00 : le gel est APPLIQUÉ à 23:00 mais
  // POSÉ à 22:00.
  const b = [
    ...seance('2026-10-23', '00:00', '23:00', [['00:00', 29200]]).filter((_, i) => i % 5 === 0),
    ...seance('2026-10-26', '00:00', '23:00', [['00:00', 29200]]).filter((_, i) => i % 5 === 0),
    ...seance('2026-10-28', '00:00', '22:00', [['00:00', 29200]]).filter((_, i) => i % 5 === 0),
    ...seance('2026-10-28', '23:00', '23:30', [['23:00', 29200]]).filter((_, i) => i % 5 === 0),
  ];
  const r = await lancer(t, b, { 'Avertissements affichés': 30 });
  const m = msgs(r);
  verifie('F 02:30 le 29 mars : heure inexistante', m.includes('heure inexistante'));
  verifie('F 02:30 le 25 octobre : heure ambiguë', m.includes('heure ambiguë'));
  const fin = y => r.lignes.find(l => l.y1 === y)?.x2;
  verifie('F gel du 23/10 (heure d\'été) = 20:00 UTC', fin(29300) === Date.UTC(2026, 9, 23, 20, 0), new Date(fin(29300)).toISOString());
  verifie('F gel du 26/10 (heure d\'hiver) = 21:00 UTC', fin(29310) === Date.UTC(2026, 9, 26, 21, 0), new Date(fin(29310)).toISOString());
  verifie('F semaine décalée : gel posé à 22:00 Paris malgré la pause', fin(29320) === Date.UTC(2026, 9, 28, 21, 0), new Date(fin(29320)).toISOString());
  verifie('F segments gelés, non prolongés', r.lignes.filter(l => [29300, 29310, 29320].includes(l.y1)).every(l => l.extend === 'n'));
}

// ── G. Pas d'anticipation, pas de repaint ──
console.log('G. Lookahead et repaint');
{
  // Disponible à 10:00. Touche à 09:30 (avant) : ignorée. Touche à 10:30 : comptée.
  const t = ['ALPZ 1', 'R id=G1 src=TEST fam=GEX inst=NQ cible=NQ date=2026-11-05 collecte=2026-11-06T09:55 dispo=2026-11-06T10:00 dte=0-0 ech=2026-11-06', 'N CW 29300',
    'R id=G2 src=TEST fam=GEX inst=NQ cible=NQ date=2026-11-05 collecte=2026-11-06T11:55 dispo=2026-11-06T12:00 dte=0-0 ech=2026-11-06', 'N PS 35000'].join('\n');
  const jal = [['09:00', 29250], ['09:30', 29300], ['09:45', 29250], ['10:15', 29250], ['10:30', 29300], ['10:50', 29262], ['11:30', 29250]];
  const plein = seance(J, '09:00', '13:00', jal);
  // Relevés hors des créneaux de minuit et de 5 h : on les montre tous.
  const tous = { 'Instantanés affichés': 'Tous' };
  const r = await lancer(t, plein, tous);
  const tips = marqueurs(r).map(e => e.tooltip);
  verifie('G touche d\'avant la disponibilité ignorée', tips.length === 1 && tips[0].includes('06/11 10:'), JSON.stringify(tips));
  verifie('G plausibilité contrôlée à l\'activation : 35000 écarté', msgs(r).includes('PS 35000.00 à plus de'));
  const court = plein.filter(x => x.openTime < paris(J, '11:00'));
  const rc = await lancer(t, court, tous);
  verifie('G mêmes issues avec ou sans les bougies suivantes', JSON.stringify(issues(rc)) === JSON.stringify(issues(r)), `${issues(rc)} / ${issues(r)}`);
  verifie('G relevé futur : à venir, non contrôlé', cell(rc, 'lus 2').includes('à venir 1'), cell(rc, 'lus'));
}

// ── H. Gel à 22 h, vivant avant ──
console.log('H. Gel');
{
  const t = ['ALPZ 1', tete('H1'), 'N CW 29300', 'N GF 29296'].join('\n');
  const avant = seance(J, '00:00', '21:30', [['00:00', 29200]]).filter((_, i) => i % 5 === 0);
  const rv = await lancer(t, avant);
  verifie('H avant 22 h : traits prolongés à droite', rv.lignes.filter(l => [29300, 29296].includes(l.y1)).every(l => l.extend === 'r'));
  verifie('H avant 22 h : étiquette en bout d\'écran (index de barre)', rv.etiquettes.some(e => e.text === 'CW 0D · GF 0D' && e.xloc === 'bi'), JSON.stringify(rv.etiquettes.filter(e => !e.text.startsWith('-')).map(e => [e.text, e.xloc])));
  verifie('H avant 22 h : boîte de confluence prolongée', rv.boites.length === 1 && ['r', 'right'].includes(rv.boites[0].extend), JSON.stringify(rv.boites[0]));
  const apres = seance(J, '00:00', '23:00', [['00:00', 29200]]).filter((_, i) => i % 5 === 0);
  const ra = await lancer(t, apres);
  verifie('H après 22 h : segments arrêtés à 22:00 Paris', ra.lignes.filter(l => [29300, 29296].includes(l.y1)).every(l => l.extend === 'n' && l.x2 === paris(J, '22:00')));
  verifie('H après 22 h : étiquette posée au gel', ra.etiquettes.some(e => e.text === 'CW 0D · GF 0D' && e.xloc === 'bt' && e.x === paris(J, '22:00')));
  verifie('H après 22 h : boîte close au gel', ra.boites.length === 1 && ra.boites[0].right === paris(J, '22:00') && ['n', 'none'].includes(ra.boites[0].extend), JSON.stringify(ra.boites[0]));
}

// ── I. Créneaux NQ / MNQ ──
console.log('I. Créneaux');
{
  const t = ['ALPZ 1',
    'R id=I-NQ src=TEST fam=GEX inst=NQ cible=NQ date=2026-11-05 collecte=2026-11-06T00:00 dispo=2026-11-06T00:05 dte=0-0 ech=2026-11-06', 'N CW 29300',
    'R id=I-MNQ src=TEST fam=GEX inst=NQ cible=MNQ date=2026-11-05 collecte=2026-11-06T05:00 dispo=2026-11-06T05:05 dte=0-0 ech=2026-11-06', 'N CW 29302',
    'R id=I-VP src=TEST fam=VP inst=NQ cible=NQ,MNQ date=2026-11-05 collecte=2026-11-06T00:00 dispo=2026-11-06T00:04 seance=2026-11-05', 'N POC 29150',
  ].join('\n');
  const b = seance(J, '00:00', '08:00', [['00:00', 29200]]).filter((_, i) => i % 5 === 0);
  const rn = await lancer(t, b, { 'Contrat du graphique (vide = automatique)': 'NQ' });
  const ys = r => r.lignes.map(l => l.y1).sort();
  verifie('I NQ : CW de minuit + POC', JSON.stringify(ys(rn)) === JSON.stringify([29150, 29300]), JSON.stringify(ys(rn)));
  const rm = await lancer(t, b, { 'Contrat du graphique (vide = automatique)': 'MNQ' });
  verifie('I MNQ : CW de 5 h + POC', JSON.stringify(ys(rm)) === JSON.stringify([29150, 29302]), JSON.stringify(ys(rm)));
  const rt = await lancer(t, b, { 'Contrat du graphique (vide = automatique)': 'NQ', 'Instantanés affichés': 'Tous' });
  const zn = rt.etiquettes.filter(e => e.style === 'style_label_left' && e.text.startsWith('CW')).length;
  verifie('I « Tous » : minuit et 5 h jamais fusionnés', zn === 2 && rt.boites.length === 0, `${zn} étiquettes CW, ${rt.boites.length} boîtes`);
}

// ── J. Profil GEX 0DTE à droite ──
console.log('J. Profil');
{
  const base = 'B base=200 fut=NQZ2026:29200@2026-11-05T22:00:00 idx=NDX:29000@2026-11-05T22:00:30';
  const t = ['ALPZ 1',
    'R id=J0 src=GEXBOT fam=GEX inst=NDX cible=NQ date=2026-11-05 collecte=2026-11-06T00:00 dispo=2026-11-06T00:05 dte=0-0 ech=2026-11-06', base,
    'N CW 29100', 'G unite=Mds$ signe=calls+/puts- origine=api net=1.25', 'S 28950:-0.8 29000:-1.6 29050:0.4', 'S 29100:2.0 29150:0.5'].join('\n');
  const b = seance(J, '00:00', '02:00', [['00:00', 29200]]).filter((_, i) => i % 5 === 0);
  const r = await lancer(t, b);
  const prof = r.lignes.filter(l => l.xloc === 'bi' && l.y1 === l.y2);
  const dernier = b.length - 1;
  verifie('J cinq barres de strike', prof.length === 5, String(prof.length));
  verifie('J strikes convertis (+200) sans déplacement', JSON.stringify(prof.map(l => l.y1).sort()) === JSON.stringify([29150, 29200, 29250, 29300, 29350]));
  verifie('J entièrement à droite du prix (6 barres)', prof.every(l => Math.min(l.x1, l.x2) >= dernier + 6), JSON.stringify(prof.map(l => [l.x1, l.x2])));
  const pos = prof.filter(l => l.x2 > l.x1).map(l => l.y1).sort();
  verifie('J positifs à droite de l\'axe, négatifs à gauche', JSON.stringify(pos) === JSON.stringify([29250, 29300, 29350]), JSON.stringify(pos));
  verifie('J longueur ∝ |GEX| (2.0 → 20 barres)', prof.some(l => l.y1 === 29300 && l.x2 - l.x1 === 20));
  const ent = r.etiquettes.find(e => e.text.startsWith('GEX 0DTE'));
  verifie('J en-tête : source, échéance, heure, figé', !!ent && ent.text.includes('éch. 2026-11-06') && ent.text.includes('06/11 00:00') && ent.text.includes('figé'), ent?.text);
  verifie('J régime lu dans le net source', !!ent && ent.text.includes('net source 1.25 Mds$ → positif'));
  const t2 = t.replace('G unite=Mds$ signe=calls+/puts- origine=api net=1.25\n', '');
  const r2 = await lancer(t2, b);
  verifie('J sans unité ni signe : indisponible', cell(r2, '« J0 » : strikes incohérents').length > 0 && !r2.lignes.some(l => l.xloc === 'bi'), cell(r2, '«'));
  const t3 = t.replace('dte=0-0 ech=2026-11-06', 'dte=1-1 ech=2026-11-09');
  const r3 = await lancer(t3, b);
  verifie('J relevé 1DTE : pas de profil 0DTE', cell(r3, 'aucun relevé GEX 0DTE').length > 0);
  verifie('J base à 30 s d\'écart : tolérée', !msgs(r).includes('APPROXIMATIVE'));
  const r4 = await lancer(t.replace('22:00:30', '22:05:00'), b);
  verifie('J base à 5 min d\'écart : APPROXIMATIVE', msgs(r4).includes('base APPROXIMATIVE'));
}

// ── K. VWAP ──
console.log('K. VWAP');
{
  const b = seance(J, '00:00', '03:00', [['00:00', 29200], ['01:00', 29260], ['02:00', 29180], ['03:00', 29230]]);
  b.forEach((x, i) => { x.volume = 50 + (i * 37) % 200; });
  const tp = x => (x.high + x.low + x.close) / 3;
  const cumul = arr => { let sv = 0, spv = 0, sp2v = 0; for (const x of arr) { const p = tp(x); sv += x.volume; spv += p * x.volume; sp2v += p * p * x.volume; }
    const vw = spv / sv; return [vw, Math.sqrt(sp2v / sv - vw * vw)]; };
  // Ancré sur la première bougie : le calcul attendu est exact, sans dépendre
  // de la notion de séance du moteur.
  const ra = await lancer('', b, { 'VWAP and SDev:': 'AVWAP', 'Start Date AVWAP': b[0].openTime });
  const [vw, sd] = cumul(b);
  verifie('K VWAP pondéré par le volume (hlc3)', Math.abs(ra.vwap.at(-1) - vw) < 1e-6, `${ra.vwap.at(-1)} vs ${vw}`);
  const lab = ra.etiquettes.filter(e => e.text.startsWith('---------'));
  verifie('K treize étiquettes (VWAP + 12 bandes)', lab.length === 13, String(lab.length));
  const sd25 = lab.find(e => e.text === '--------- SD +2.5');
  verifie('K bande +2.5σ = VWAP + 2.5·σ (σ pondéré par le volume)', !!sd25 && Math.abs(sd25.y - (vw + 2.5 * sd)) < 1e-6, `${sd25?.y} vs ${vw + 2.5 * sd}`);
  verifie('K étiquettes décalées d\'une barre', lab.every(e => e.x === b.length));
  // « Day » : à la remise à zéro, le VWAP précédent est la valeur finale de
  // la période close, et ses bandes ±1/±2 en découlent.
  const rd = await lancer('', b);
  let k = -1;
  for (let i = 1; i < b.length; i++) if (Math.abs(rd.vwap[i] - tp(b[i])) < 1e-9 && Math.abs(rd.vwap[i - 1] - tp(b[i])) > 1e-9) { k = i; break; }
  const [vwP, sdP] = cumul(b.slice(0, k));
  const prev = (rd.ctx.plots['Previous VWAP']?.data ?? []).map(x => x.value);
  const prev2 = (rd.ctx.plots['Previous VWAP - STDEV +2']?.data ?? []).map(x => x.value);
  verifie('K remise à zéro trouvée', k > 0, String(k));
  verifie('K VWAP précédent = VWAP final de la période close', Math.abs(prev.at(-1) - vwP) < 1e-6, `${prev.at(-1)} vs ${vwP}`);
  verifie('K précédent +2σ', Math.abs(prev2.at(-1) - (vwP + 2 * sdP)) < 1e-6, `${prev2.at(-1)} vs ${vwP + 2 * sdP}`);
  const [vwJ] = cumul(b.slice(k));
  verifie('K VWAP du jour repart de la remise à zéro', Math.abs(rd.vwap.at(-1) - vwJ) < 1e-6, `${rd.vwap.at(-1)} vs ${vwJ}`);
}

// ── L. L'EXEMPLE FICTIF de la documentation, lu dans le fichier ──
console.log('L. Exemple fictif de docs/zones-gamma-format.md');
{
  const doc = fs.readFileSync(new URL('../../docs/zones-gamma-format.md', import.meta.url), 'utf8');
  const ex = doc.split('<!-- EXEMPLE FICTIF : début -->')[1].split('<!-- EXEMPLE FICTIF : fin -->')[0]
    .replace(/^\s*```\s*\n/, '').replace(/\n```\s*$/, '');
  const b = seance(J, '00:00', '08:00', [['00:00', 29300], ['08:00', 29310]]).filter((_, i) => i % 5 === 0);
  const rn = await lancer(ex, b, { 'Contrat du graphique (vide = automatique)': 'NQ' });
  verifie('L en-tête « ⚠ EXEMPLE FICTIF » et version', rn.cellules.some(c => c.startsWith('⚠ EXEMPLE FICTIF · Alp-0 Zones v')), rn.cellules[0]);
  verifie('L ligne « Lecture » : 5 relevés, 20 niveaux (6 + 2 + 4 + 5 + 3), 11 strikes', cell(rn, 'A ').includes('5 relevés · 20 niveaux · 11 strikes'), cell(rn, 'A '));
  verifie('L ligne « Jour affiché » : en cours', cell(rn, '06/11 ·').includes('en cours'), cell(rn, '06/11'));
  verifie('L aucun avertissement sur l\'exemple', !rn.cellules.some(c => c.startsWith('Avertissements')), msgs(rn).split('\n').filter(c => c.includes('—')).join(' | '));
  const noms = rn.etiquettes.filter(e => e.style === 'style_label_left' && !e.text.startsWith('-')).map(e => e.text.split('  ◦')[0]);
  verifie('L NQ : « FICTIF · CW 0D · 1D · VAH · HVN »', noms.includes('FICTIF · CW 0D · 1D · VAH · HVN'), JSON.stringify(noms));
  verifie('L NQ : « FICTIF · R1 0D · POC »', noms.includes('FICTIF · R1 0D · POC'), JSON.stringify(noms));
  verifie('L NQ : boîte 29468.5–29476', rn.boites.some(x => x.bottom === 29468.5 && x.top === 29476), JSON.stringify(rn.boites.map(x => [x.bottom, x.top])));
  verifie('L NQ : profil 0DTE tracé (11 strikes)', rn.lignes.filter(l => l.xloc === 'bi' && l.y1 === l.y2).length === 11);
  verifie('L NQ : rien du relevé de 5 h', !rn.lignes.some(l => l.y1 === 29178.5));
  const rm = await lancer(ex, b, { 'Contrat du graphique (vide = automatique)': 'MNQ' });
  const nm = rm.etiquettes.filter(e => e.style === 'style_label_left' && !e.text.startsWith('-')).map(e => e.text.split('  ◦')[0]);
  verifie('L MNQ : « FICTIF · CW 0D · VAH · HVN » (relevé de 5 h + profil de volume)', nm.includes('FICTIF · CW 0D · VAH · HVN'), JSON.stringify(nm));
  verifie('L MNQ : GF de 5 h (29178.5), pas celui de minuit', rm.lignes.some(l => l.y1 === 29178.5) && !rm.lignes.some(l => l.y1 === 29168.5));
}

// ── M. Z-score (heatmap des bougies) ──
console.log('M. Z-score');
{
  // Référence : z = (ohlc4 − SMA50) / σ50, σ « biaisé » (division par N),
  // comme ta.stdev par défaut.
  const o4 = x => (x.open + x.high + x.low + x.close) / 4;
  const zRef = (bs, i, n = 50) => {
    if (i < n - 1) return NaN;
    const w = bs.slice(i - n + 1, i + 1).map(o4);
    const m = w.reduce((a, b) => a + b, 0) / n;
    const sd = Math.sqrt(w.reduce((a, b) => a + (b - m) * (b - m), 0) / n);
    return sd === 0 ? NaN : (o4(bs[i]) - m) / sd;
  };
  const b = seance(J, '00:00', '02:30', [['00:00', 29200], ['00:40', 29230], ['01:10', 29190], ['01:40', 29260], ['02:30', 29240]]);
  const r = await lancer('', b);
  const z = r.ctx.plots['Z-Score'].data.map(x => x.value);
  verifie('M préchauffage : z = na sur les 49 premières bougies (pas de zéro fabriqué)', z.slice(0, 49).every(v => v === null || Number.isNaN(v)), JSON.stringify(z.slice(45, 50)));
  const ecart = Math.max(...b.map((_, i) => i).filter(i => i >= 49).map(i => Math.abs(z[i] - zRef(b, i))));
  verifie('M z-score = référence sur toutes les bougies', ecart < 1e-9, String(ecart));
  // Un plat puis une marche isolée : z = 0,98 / 0,14 = 7 exactement.
  const plat = seance(J, '00:00', '01:01', [['00:00', 29200]]);
  plat.at(-1).open = 29200; plat.at(-1).close = 29230; plat.at(-1).high = 29230; plat.at(-1).low = 29200;
  const rp = await lancer('', plat);
  const zp = rp.ctx.plots['Z-Score'].data.map(x => x.value);
  const hm = rp.ctx.plots['Z-Score Heatmap'].data;
  verifie('M prix immobile : z = na, bougie neutre', (zp.at(-2) === null || Number.isNaN(zp.at(-2))) && hm.at(-2).options.color === 'rgb(51, 51, 51)', `${zp.at(-2)} ${hm.at(-2).options.color}`);
  verifie('M marche isolée : z = 7', Math.abs(zp.at(-1) - 7) < 1e-9, String(zp.at(-1)));
  verifie('M au-delà de T2 : magenta', hm.at(-1).options.color === 'rgb(229, 5, 255)', hm.at(-1).options.color);
  // Entre T1 et T2 : dégradé, rouge strictement entre le cyan (45) et le
  // magenta (229), croissant avec |z|.
  const grad = b.map((_, i) => i).filter(i => i >= 49 && Math.abs(zRef(b, i)) >= 2 && Math.abs(zRef(b, i)) < 3);
  // PineTS écrit une couleur « rgb(r, g, b) » ou « #RRGGBB » selon son origine.
  const canal = c => c.startsWith('#') ? parseInt(c.slice(1, 3), 16) : +c.match(/\d+/)[0];
  const rouge = i => canal(r.ctx.plots['Z-Score Heatmap'].data[i].options.color);
  // Dégradé : rouge de 45 (cyan, à T1) à 229 (magenta, à T2), bleu ≥ 173 ;
  // le neutre (51, 51, 51) a un bleu de 51 : les deux ne se confondent pas.
  const bleu = i => { const c = r.ctx.plots['Z-Score Heatmap'].data[i].options.color; return c.startsWith('#') ? parseInt(c.slice(5, 7), 16) : +c.match(/\d+/g)[2]; };
  const okGrad = grad.length > 0 && grad.every(i => rouge(i) >= 45 && rouge(i) < 229 && bleu(i) >= 173);
  verifie('M entre T1 et T2 : dégradé cyan → magenta', okGrad, `${grad.length} bougies ; ${grad.slice(0, 3).map(i => r.ctx.plots['Z-Score Heatmap'].data[i].options.color)}`);
  const tri = [...grad].sort((i, j) => Math.abs(zRef(b, i)) - Math.abs(zRef(b, j)));
  verifie('M dégradé croissant avec |z|', tri.every((i, k) => k === 0 || rouge(i) >= rouge(tri[k - 1])));
  const neutres = b.map((_, i) => i).filter(i => i >= 49 && Math.abs(zRef(b, i)) < 2);
  verifie('M sous T1 : neutre', neutres.length > 0 && neutres.every(i => r.ctx.plots['Z-Score Heatmap'].data[i].options.color === 'rgb(51, 51, 51)'));
  // Mèche +10 %, bordure −20 % : plus claire, plus sombre que le corps.
  const rc = await lancer('', plat, { 'Custom Wick/Border': true });
  const o = rc.ctx.plots['Z-Score Heatmap'].data.at(-1).options;
  const rgb = c => c.match(/[\d.]+/g).map(Number);
  verifie('M mèche éclaircie de 10 %', Math.abs(rgb(o.wickcolor)[0] - Math.min(255, 229 * 1.1)) < 1 && rgb(o.wickcolor)[1] >= 5, o.wickcolor);
  verifie('M bordure assombrie de 20 %', Math.abs(rgb(o.bordercolor)[0] - 229 * 0.8) < 1, o.bordercolor);
  // T2 ≤ T1 : pas de dégradé dégénéré.
  const ri = await lancer('', b, { 'Threshold T1 (σ)': 3, 'Threshold T2 (σ)': 2 });
  const hi = ri.ctx.plots['Z-Score Heatmap'].data;
  const cols = new Set(b.map((_, i) => i).filter(i => i >= 49).map(i => hi[i].options.color));
  verifie('M T2 ≤ T1 : neutre ou magenta, rien entre les deux', [...cols].every(c => c === 'rgb(51, 51, 51)' || c === 'rgb(229, 5, 255)'), JSON.stringify([...cols]));
  const ro = await lancer('', b, { 'Colorer les bougies (heatmap)': false });
  verifie('M heatmap désactivée : aucune bougie tracée', ro.ctx.plots['Z-Score Heatmap'].data.every(x => x.value.every(v => v === null || Number.isNaN(v))));
}

// ── N. Texte collé sans retours à la ligne ──
console.log('N. Collage sans retours à la ligne');
{
  // Certains champs de saisie remplacent les retours à la ligne par des
  // espaces : l'exemple de la doc, aplati, doit rendre exactement les mêmes
  // niveaux que l'exemple d'origine.
  const doc = fs.readFileSync(new URL('../../docs/zones-gamma-format.md', import.meta.url), 'utf8');
  const ex = doc.split('<!-- EXEMPLE FICTIF : début -->')[1].split('<!-- EXEMPLE FICTIF : fin -->')[0]
    .replace(/^\s*```\s*\n/, '').replace(/\n```\s*$/, '');
  const b = seance(J, '00:00', '08:00', [['00:00', 29300], ['08:00', 29310]]).filter((_, i) => i % 5 === 0);
  const ys = r => r.lignes.filter(l => l.xloc === 'bt').map(l => l.y1).sort((a, c) => a - c);
  const r1 = await lancer(ex, b);
  const r2 = await lancer(ex.replace(/\n/g, ' '), b);
  verifie('N mêmes niveaux, aplati ou non', JSON.stringify(ys(r1)) === JSON.stringify(ys(r2)) && ys(r1).length > 0, `${ys(r1).length} / ${ys(r2).length}`);
  verifie('N même profil', r2.lignes.filter(l => l.xloc === 'bi' && l.y1 === l.y2).length === 11);
  verifie('N la ligne « Lecture » le signale', cell(r2, 'A ').includes('relu par marqueurs'), cell(r2, 'A '));
  verifie('N aucun avertissement de lecture', !r2.cellules.some(c => c.startsWith('Avertissements')), msgs(r2).split('\n').filter(c => c.includes('—')).join(' | '));
}

// ── O. La situation de l'utilisateur : l'exemple, NQ1!, vu le week-end ──
console.log('O. Exemple vu le week-end (séance du vendredi close)');
{
  const doc = fs.readFileSync(new URL('../../docs/zones-gamma-format.md', import.meta.url), 'utf8');
  const ex = doc.split('<!-- EXEMPLE FICTIF : début -->')[1].split('<!-- EXEMPLE FICTIF : fin -->')[0]
    .replace(/^\s*```\s*\n/, '').replace(/\n```\s*$/, '');
  const b = seance(J, '00:00', '23:00', [['00:00', 29250], ['10:00', 29420], ['16:00', 29150], ['23:00', 29300]]);
  const r = await lancer(ex, b);
  const traits = r.lignes.filter(l => l.xloc === 'bt');
  // 20 niveaux − 3 du relevé MNQ de 5 h − 4 secondaires masqués (S2, IV+2σ, IV−2σ, LVN) = 13.
  verifie('O 13 niveaux tracés le vendredi, de 00:04 à 22:00', traits.length === 13 && traits.every(l => l.x1 >= paris(J, '00:03') && l.x2 === paris(J, '22:00') && l.extend === 'n'), `${traits.length} traits`);
  verifie('O noms posés à 22:00', r.etiquettes.some(e => e.text === 'FICTIF · CW 0D · 1D · VAH · HVN' && e.x === paris(J, '22:00')));
  const prof = r.lignes.filter(l => l.xloc === 'bi' && l.y1 === l.y2);
  verifie('O profil 0DTE à droite de la dernière bougie', prof.length === 11 && prof.every(l => Math.min(l.x1, l.x2) >= b.length - 1 + 6));
  verifie('O le tableau dit où regarder', cell(r, '06/11 ·').includes('gelé à 22:00 : niveaux à gauche de la dernière bougie'), cell(r, '06/11'));
}

// ── P. L'exemple de la consigne du bot, lu dans docs/consigne-lou-alpz.md ──
console.log('P. Exemple de la consigne du bot');
{
  const doc = fs.readFileSync(new URL('../../docs/consigne-lou-alpz.md', import.meta.url), 'utf8');
  const ex = doc.split('<!-- EXEMPLE CONSIGNE : début -->')[1].split('<!-- EXEMPLE CONSIGNE : fin -->')[0]
    .replace(/^\s*```\s*\n/, '').replace(/\n```\s*$/, '');
  const b = seance('2026-11-04', '00:00', '03:00', [['00:00', 29340], ['03:00', 29360]]).filter((_, i) => i % 5 === 0);
  const r = await lancer(ex, b);
  verifie('P lu sans aucun avertissement', !r.cellules.some(c => c.startsWith('Avertissements')), msgs(r).split('\n').filter(c => c.includes('—')).join(' | '));
  verifie('P « Lecture » : 3 relevés, 10 niveaux', cell(r, 'A ').includes('3 relevés · 10 niveaux · 0 strikes'), cell(r, 'A '));
  const ys = r.lignes.filter(l => l.xloc === 'bt').map(l => l.y1).sort((a, c) => a - c);
  verifie('P prix convertis (NDX + 117.75) et prix VP tels quels', JSON.stringify(ys) === JSON.stringify([29097.75, 29117.75, 29150, 29297.75, 29310, 29317.75, 29380, 29420, 29517.75, 29587.75]), JSON.stringify(ys));
  const noms = r.etiquettes.filter(e => e.style === 'style_label_left' && !e.text.startsWith('-')).map(e => e.text.split('  ◦')[0]);
  verifie('P confluence « MaxPain 0D · POC »', noms.includes('FICTIF · MaxPain 0D · POC'), JSON.stringify(noms));
}

console.log(`\n${ok} contrôle(s) réussi(s), ${ko} échec(s)`);
if (ko) { console.log('Échecs : ' + echecs.join(' | ')); process.exitCode = 1; }
