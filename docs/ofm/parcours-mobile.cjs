// Parcours au doigt de la version mobile, avec assertions : sort en erreur si un geste ne mène pas où il doit.
// Usage : node docs/ofm/parcours-mobile.cjs docs/ofm/la-personne-mobile.html
//         node docs/ofm/parcours-mobile.cjs docs/ofm/cahier-2-mobile.html   (profil du cahier nº 2)
// Couvre : espace → tuile → repère → pied (sujet lu) → retour à l'espace (même place) → recherche
// (geste retour, résultat ailleurs, résultat dans le sujet ouvert) → dock Suivant → reprise après
// rechargement → remise à zéro → lien direct vers un sujet → page sans JavaScript.
const { chromium } = require('playwright');
const fs = require('fs');
const os = require('os');
const path = require('path');

const doc = path.resolve(process.argv[2]);
// Les sujets, les mots cherchés et la clé de lecture de chaque cahier : le geste est le même.
const PROFILS = {
  1: { cle: 'ofm-cahier', tuile: 'demander', titre: 'Demander', mot: 'fidele', ou: '07 · Revenir', vueMot: 'revenir',
       tuile2: 'persuader', mot2: 'tactique', ou2: '04 · Persuader', suivant: 'negocier', repNom: 'Négocier',
       direct: 'mesurer', reprise: 'offrir' },
  2: { cle: 'ofm-cahier2', tuile: 'courriel', titre: 'Le courriel', mot: 'fidele', ou: '05 · Garder', vueMot: 'garder',
       tuile2: 'cibler', mot2: 'risque', ou2: '04 · Cibler', suivant: 'garder', repNom: 'Garder',
       direct: 'mesurer', reprise: 'sms' },
};
const P = PROFILS[/cahier-2/.test(doc) ? 2 : 1];
let echecs = 0;
const verifier = (cond, quoi, detail) => {
  console.log((cond ? 'ok   ' : 'ÉCHEC') + ' ' + quoi + (cond ? '' : ' — ' + JSON.stringify(detail)));
  if (!cond) echecs += 1;
};

(async () => {
  // L'hébergeur d'artefacts ajoute la balise viewport : un aperçu qui l'oublie mesure une page de 980 px.
  const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'ofm-')), 'apercu.html');
  fs.writeFileSync(tmp, '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">' + fs.readFileSync(doc, 'utf8'));
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  const erreurs = [];
  p.on('pageerror', (e) => erreurs.push(String(e)));
  await p.goto('file://' + tmp);
  const etat = () => p.evaluate(() => ({
    vue: document.documentElement.dataset.vue,
    sections: [...document.querySelectorAll('main > section')].filter((s) => s.getClientRects().length).map((s) => s.id),
    y: Math.round(scrollY),
    titre: document.querySelector('#titre').textContent,
    recherche: !document.querySelector('#cherche').hidden,
    suivant: document.querySelector('#d-suiv span').textContent,
    puces: document.querySelectorAll('#chips button').length,
  }));

  let e = await etat();
  verifier(e.vue === 'sujets' && e.sections.length === 0, 'la page s’ouvre sur l’espace, aucun sujet affiché', e);
  const tuiles = await p.evaluate(() => [...document.querySelectorAll('.tuile')].map((t) => t.dataset.id));
  const sections = await p.evaluate(() => [...document.querySelectorAll('main > section')].map((s) => s.id));
  verifier(JSON.stringify(tuiles) === JSON.stringify(sections), 'une tuile par sujet, dans l’ordre', { tuiles, sections });

  await p.evaluate(() => window.scrollTo(0, 300));
  await p.waitForTimeout(120);
  const yEspace = await p.evaluate(() => Math.round(scrollY));
  await p.tap(`.tuile[data-id="${P.tuile}"]`);
  await p.waitForTimeout(150);
  e = await etat();
  verifier(e.vue === P.tuile && e.sections.join() === P.tuile && e.y === 0, 'une tuile ouvre son seul sujet, en haut', e);
  verifier(await p.evaluate(() => location.hash) === '#' + P.tuile, `l’adresse suit la vue (#${P.tuile}) : le lien copié rouvre ce sujet`, await p.evaluate(() => location.hash));
  verifier(e.titre.includes(P.titre) && e.puces >= 3 && e.suivant === 'Suivant', 'barre du haut, repères et dock du sujet', e);

  await p.tap('#chips button:has-text("Graphique 1")');
  await p.waitForTimeout(900);
  const ecart = await p.evaluate((t) => Math.round(document.querySelector('#' + t + ' figure.viz').getBoundingClientRect().top - document.querySelector('.appbar').getBoundingClientRect().bottom), P.tuile);
  verifier(ecart >= 0 && ecart < 40, 'un repère amène son bloc juste sous la barre', { ecart });

  await p.evaluate((t) => { const f = document.querySelector('#' + t + ' .fin'); window.scrollTo(0, f.getBoundingClientRect().top + scrollY - 300); }, P.tuile);
  await p.waitForTimeout(400);
  const lus = await p.evaluate((c) => JSON.parse(localStorage.getItem(c + '-lus') || '[]'), P.cle);
  verifier(lus.includes(P.tuile), 'arriver au pied marque le sujet comme lu', lus);

  await p.tap('#retour');
  await p.waitForTimeout(200);
  e = await etat();
  const lu = await p.evaluate((t) => document.querySelector(`.tuile[data-id="${t}"]`).classList.contains('est-lu'), P.tuile);
  verifier(e.vue === 'sujets' && Math.abs(e.y - yEspace) < 300 && lu, 'retour : l’espace revient à sa place, la tuile cochée', { e, yEspace, lu });

  await p.tap('#d-cherche');
  await p.waitForTimeout(150);
  verifier((await etat()).recherche && await p.evaluate(() => document.activeElement.id === 'q'), 'la recherche s’ouvre, le curseur dans le champ', await etat());
  await p.goBack();
  await p.waitForTimeout(150);
  e = await etat();
  verifier(!e.recherche && e.vue === 'sujets', 'le geste retour ferme la recherche sans changer de vue', e);

  await p.tap('#d-cherche');
  await p.waitForTimeout(100);
  await p.tap('#fermer');
  await p.waitForTimeout(150);
  e = await etat();
  verifier(!e.recherche && e.vue === 'sujets' && await p.evaluate(() => location.hash !== '#chercher'), 'le bouton Fermer referme la recherche', e);

  await p.tap('#d-cherche');
  await p.fill('#q', P.mot);
  await p.waitForTimeout(150);
  const n = await p.evaluate(() => document.querySelectorAll('.hit').length);
  verifier(n > 0, 'la recherche ignore les accents (« fidele » trouve « fidèle »)', { n });
  await p.tap(`.hit:has(.hit-ou:has-text("${P.ou}"))`);
  await p.waitForTimeout(900);
  e = await etat();
  verifier(!e.recherche && e.vue === P.vueMot && e.y > 0, 'un résultat ouvre son sujet, à l’endroit trouvé', e);
  await p.goBack();
  await p.waitForTimeout(200);
  verifier((await etat()).vue === 'sujets', 'retour après un résultat : l’espace', await etat());

  await p.tap(`.tuile[data-id="${P.tuile2}"]`);
  await p.waitForTimeout(150);
  await p.tap('#d-cherche');
  await p.fill('#q', P.mot2);
  await p.waitForTimeout(150);
  await p.tap(`.hit:has(.hit-ou:has-text("${P.ou2}"))`);
  await p.waitForTimeout(900);
  e = await etat();
  verifier(!e.recherche && e.vue === P.tuile2 && e.y > 0, 'un résultat du sujet ouvert y descend directement', e);

  await p.tap('#d-suiv');
  await p.waitForTimeout(150);
  verifier((await etat()).vue === P.suivant, 'le dock « Suivant » ouvre le sujet suivant', await etat());

  await p.reload();
  await p.waitForTimeout(250);
  const rep = await p.evaluate(() => [document.querySelector('#rep-carte').hidden, document.querySelector('#rep-nom').textContent]);
  await p.tap('#d-sujets');
  await p.waitForTimeout(150);
  const rep2 = await p.evaluate(() => [document.querySelector('#rep-carte').hidden, document.querySelector('#rep-nom').textContent]);
  verifier(!rep2[0] && rep2[1].includes(P.repNom), 'l’espace propose de reprendre le dernier sujet ouvert', { rep, rep2 });

  await p.evaluate(() => document.querySelector('#raz').scrollIntoView());
  await p.tap('#raz');
  await p.waitForTimeout(100);
  const raz = await p.evaluate((c) => [document.querySelector('#rep-carte').hidden, localStorage.getItem(c + '-lus'), document.querySelector('#d-suiv span').textContent], P.cle);
  verifier(raz[0] && raz[1] === null && raz[2] === 'Commencer', 'la remise à zéro efface lecture et reprise', raz);

  await p.goto('about:blank');
  await p.goto('file://' + tmp + '#' + P.direct);
  await p.waitForTimeout(200);
  e = await etat();
  verifier(e.vue === P.direct && e.sections.join() === P.direct, 'un lien direct ouvre son sujet', e);
  await p.goto('about:blank');
  await p.goto('file://' + tmp);
  await p.tap(`.tuile[data-id="${P.reprise}"]`);
  await p.waitForTimeout(150);
  await p.evaluate(() => window.scrollTo(0, 1500));
  await p.waitForTimeout(700);
  await p.goto('about:blank');
  await p.goto('file://' + tmp + '#reprendre');
  await p.waitForTimeout(250);
  e = await etat();
  verifier(e.vue === P.reprise && Math.abs(e.y - 1500) < 40 && await p.evaluate(() => location.hash) === '#' + P.reprise, '#reprendre rouvre le dernier sujet à l’endroit exact', e);

  await p.goto('about:blank');
  await p.goto('file://' + tmp + '#chercher');
  await p.waitForTimeout(200);
  e = await etat();
  verifier(e.recherche && e.vue === 'sujets', 'un lien vers #chercher ouvre la recherche sur l’espace', e);
  await p.tap('#fermer');
  await p.waitForTimeout(150);
  e = await etat();
  verifier(!e.recherche && e.vue === 'sujets' && p.url().startsWith('file://'), 'la fermer ne quitte pas la page', { e, url: p.url() });
  verifier(erreurs.length === 0, 'aucune erreur JavaScript', erreurs);

  const sansJs = await b.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  const q = await sansJs.newPage();
  await q.goto('file://' + tmp);
  const vues = await q.evaluate(() => [...document.querySelectorAll('main > section')].filter((s) => s.getClientRects().length).length);
  verifier(vues === sections.length, 'sans JavaScript, le long document reste lisible en entier', { vues });

  await b.close();
  console.log(echecs ? `${echecs} échec(s)` : 'parcours complet : tout passe');
  process.exit(echecs ? 1 : 0);
})();
